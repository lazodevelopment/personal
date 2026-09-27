#!/usr/bin/env python3
"""
LeaseReputation - directory-scale community photo fetcher (Places API New).

Fetches one hero photo per community into community/images/<place_id>.jpg.
Images are keyed by PLACE_ID (stable), not slug - slugs renumber when
collisions dedupe, so at 19.5K scale slug keys would mismatch across builds.
The generator checks slug.jpg first (legacy curated photos keep working),
then place_id.jpg.

Built for the full directory:
  * Reads every community from Firestore (same service account as the
    generator). No hand-written list dependency.
  * RESUMABLE: skips any place_id whose jpg already exists, AND any
    place_id in the no-photo ledger (photos_nophoto.txt) - confirmed
    photo-less communities are never re-queried on later runs.
  * TRANCHED: --states AZ,TX runs one tranche; --limit N caps a run.
  * COST-AWARE: --dry-run prints exactly how many billable calls a run
    would make (and detects stored photo refs on the docs, which skip the
    Place Details call entirely) before you spend anything.
  * THROTTLED: a global cross-thread rate limiter paces ALL API requests
    (Details + media) to --rps requests/sec (default 4.5). Small retry
    runs no longer burst into 429s.
  * Failures overwrite photos_failed.log fresh each run (the log is a
    snapshot of THIS run, not an append-forever history) and never stop
    the run.

USAGE:
  python fetch_community_photos.py --dry-run              # count + cost, no calls
  python fetch_community_photos.py --states AZ --limit 50 # small paid pilot
  python fetch_community_photos.py --states AZ,TX         # tranche
  python fetch_community_photos.py --all                  # full directory
Then:  python generate_community_pages.py   (photos flip pages into the
rich sitemap tier at the next build)  ->  kv_sync.

Key: reads PLACES_API_KEY env var first (same convention as the seeder),
falls back to the constant below.
"""

import os
import re
import sys
import json
import time
import argparse
import threading
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

# Env var first (seeder convention), constant fallback.
PLACES_KEY = os.environ.get("PLACES_API_KEY") or "REPLACE_WITH_ROTATED_KEY"

BASE = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE, "community", "images")
FAIL_LOG = os.path.join(BASE, "photos_failed.log")
NOPHOTO_LEDGER = os.path.join(BASE, "photos_nophoto.txt")

SERVICE_ACCOUNT_CANDIDATES = [
    os.path.join(BASE, "serviceAccountKey.json"),
    r"C:\Users\kurvh\lease-reputation\serviceAccountKey.json",
]

# 800px covers the hero at typical viewport widths and keeps files ~50-120KB.
# (The old curated script used 1600 for retina; at 19.5K images that would
# roughly triple the site payload for marginal visual gain.)
MAX_WIDTH = 800

ADDR_STATE_RE = re.compile(r",\s*([A-Z]{2})\s+\d{5}")

_print_lock = threading.Lock()


def log(msg):
    with _print_lock:
        print(msg, flush=True)


# ---------------------------------------------------------------------------
# Global rate limiter - shared across ALL worker threads and BOTH request
# types (Place Details + photo media). Google rate-limits per project, not
# per endpoint, so every outbound call takes a slot.
# ---------------------------------------------------------------------------
class RateLimiter:
    def __init__(self, rps):
        self.interval = 1.0 / max(rps, 0.1)
        self.lock = threading.Lock()
        self.next_at = 0.0

    def wait(self):
        with self.lock:
            now = time.monotonic()
            if now < self.next_at:
                sleep_for = self.next_at - now
                self.next_at += self.interval
            else:
                sleep_for = 0.0
                self.next_at = now + self.interval
        if sleep_for > 0:
            time.sleep(sleep_for)


_limiter = None  # set in main() from --rps


# ---------------------------------------------------------------------------
# No-photo ledger - place_ids confirmed to have zero Places photos. One id
# per line. Loaded at start and merged into the skip set; appended during
# the run under a lock. This is what stops --all from re-buying Details
# calls for the ~770 photo-less communities on every pass.
# ---------------------------------------------------------------------------
_ledger_lock = threading.Lock()


def load_nophoto_ledger():
    if not os.path.exists(NOPHOTO_LEDGER):
        return set()
    with open(NOPHOTO_LEDGER, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def record_nophoto(pid):
    with _ledger_lock:
        with open(NOPHOTO_LEDGER, "a", encoding="utf-8") as f:
            f.write(pid + "\n")


def _doc_photo_ref(d):
    """If the seeder stored a Places photo resource name on the doc, use it
    and skip the (billable) Place Details call. Checks the likely fields."""
    for k in ("photoName", "photoRef", "photo"):
        v = d.get(k)
        if isinstance(v, str) and "/photos/" in v:
            return v
    v = d.get("photos")
    if isinstance(v, list) and v:
        first = v[0]
        if isinstance(first, str) and "/photos/" in first:
            return first
        if isinstance(first, dict) and "/photos/" in str(first.get("name", "")):
            return first["name"]
    return None


def _doc_state(d):
    m = ADDR_STATE_RE.search(str(d.get("address") or ""))
    return m.group(1) if m else None


def load_directory():
    key_path = next((p for p in SERVICE_ACCOUNT_CANDIDATES if os.path.exists(p)), None)
    if key_path is None:
        sys.exit("ERROR: serviceAccountKey.json not found.")
    import firebase_admin
    from firebase_admin import credentials, firestore
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(key_path))
    db = firestore.client()
    out = []
    for doc in db.collection("communities").stream():
        d = doc.to_dict() or {}
        out.append({
            "pid": doc.id,
            "name": str(d.get("name") or "").strip(),
            "state": _doc_state(d),
            "stored_ref": _doc_photo_ref(d),
        })
    return out


def get_place_photo_name(place_id):
    """Place Details (New), photos field only -> first photo resource name."""
    _limiter.wait()
    url = f"https://places.googleapis.com/v1/places/{place_id}"
    req = urllib.request.Request(url, headers={
        "X-Goog-Api-Key": PLACES_KEY,
        "X-Goog-FieldMask": "photos",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    photos = data.get("photos", [])
    return photos[0]["name"] if photos else None


def download_photo(photo_name, dest_path):
    _limiter.wait()
    url = (f"https://places.googleapis.com/v1/{photo_name}/media"
           f"?maxWidthPx={MAX_WIDTH}&key={urllib.parse.quote(PLACES_KEY)}")
    with urllib.request.urlopen(urllib.request.Request(url), timeout=60) as r:
        data = r.read()
    tmp = dest_path + ".part"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, dest_path)   # atomic: no half-written jpgs on kill
    return len(data)


def fetch_one(item):
    """Returns (pid, status, detail). status: ok|okfb|nophoto|fail
    okfb = succeeded via fallback (stored ref was stale -> fresh Details)."""
    pid = item["pid"]
    dest = os.path.join(IMG_DIR, pid + ".jpg")
    used_stored = bool(item["stored_ref"])
    try:
        photo_name = item["stored_ref"] or get_place_photo_name(pid)
        if not photo_name:
            record_nophoto(pid)
            return pid, "nophoto", item["name"]
        try:
            size = download_photo(photo_name, dest)
            return pid, "ok", f"{item['name']} ({size // 1024} KB)"
        except Exception:
            if not used_stored:
                raise
            # Stored ref stale/expired -> refresh via Details, retry once.
            photo_name = get_place_photo_name(pid)
            if not photo_name:
                record_nophoto(pid)
                return pid, "nophoto", item["name"] + " (ref stale, no photos now)"
            size = download_photo(photo_name, dest)
            return pid, "okfb", f"{item['name']} ({size // 1024} KB, refreshed ref)"
    except Exception as e:
        return pid, "fail", f"{item['name']} - {e}"


def main():
    global _limiter

    ap = argparse.ArgumentParser()
    ap.add_argument("--states", help="comma-separated, e.g. AZ,TX")
    ap.add_argument("--limit", type=int, default=0, help="cap this run at N fetches")
    ap.add_argument("--all", action="store_true", help="run the full directory")
    ap.add_argument("--dry-run", action="store_true", help="count + cost only, no API calls")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--rps", type=float, default=4.5,
                    help="max API requests/sec across all workers (default 4.5; "
                         "the 80-min full run averaged ~4/sec and never 429'd)")
    ap.add_argument("--retry-nophoto", action="store_true",
                    help="ignore the no-photo ledger and re-check those "
                         "communities (use sparingly - each costs a Details call)")
    ap.add_argument("--ignore-stored-refs", action="store_true",
                    help="skip stored photo refs entirely (use when a pilot "
                         "showed them all stale) - goes straight to Details")
    args = ap.parse_args()

    if not args.dry_run and not args.states and not args.limit and not args.all:
        sys.exit("Pick a scope: --states / --limit / --all  (or --dry-run first). "
                 "Refusing to accidentally run 19.5K paid calls.")

    _limiter = RateLimiter(args.rps)

    os.makedirs(IMG_DIR, exist_ok=True)
    print("loading directory from Firestore...")
    items = load_directory()
    if args.ignore_stored_refs:
        for i in items:
            i["stored_ref"] = None
        print("  --ignore-stored-refs: all fetches go straight to Details")
    print(f"  {len(items)} communities in directory")

    if args.states:
        want = {s.strip().upper() for s in args.states.split(",")}
        items = [i for i in items if i["state"] in want]
        print(f"  {len(items)} after state filter ({','.join(sorted(want))})")

    have = {f[:-4] for f in os.listdir(IMG_DIR) if f.endswith(".jpg")}
    nophoto_known = set() if args.retry_nophoto else load_nophoto_ledger()
    if nophoto_known:
        print(f"  {len(nophoto_known)} in no-photo ledger (skipped; "
              f"--retry-nophoto to re-check)")
    skip = have | nophoto_known
    todo = [i for i in items if i["pid"] not in skip]
    print(f"  {len(items) - len(todo)} already resolved (photo on disk or "
          f"confirmed no-photo), {len(todo)} to fetch")

    if args.limit:
        todo = todo[: args.limit]
        print(f"  capped at {len(todo)} this run (--limit)")

    with_ref = sum(1 for i in todo if i["stored_ref"])
    details_calls = len(todo) - with_ref
    print(f"\n  billable shape: {details_calls} Place Details calls "
          f"(photos fieldmask) + up to {len(todo)} photo media fetches")
    if with_ref:
        print(f"  {with_ref} docs carry a stored photo ref -> Details call skipped for those")
    est_lo = details_calls / 1000 * 17 + len(todo) / 1000 * 7
    est_hi = details_calls / 1000 * 20 + len(todo) / 1000 * 10
    print(f"  rough list-price estimate: ${est_lo:,.0f}-${est_hi:,.0f} "
          f"(before per-SKU free tiers; verify SKU rates in Cloud Billing)")
    eta_min = len(todo) / max(args.rps, 0.1) / 60
    print(f"  pacing: {args.rps} req/sec -> ~{eta_min:.0f} min minimum for this scope")

    if args.dry_run:
        print("\ndry run - no API calls made.")
        return

    # Fresh failure log every run: it's a snapshot of THIS run, not history.
    open(FAIL_LOG, "w", encoding="utf-8").close()

    ok = nophoto = failed = refreshed = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = [ex.submit(fetch_one, i) for i in todo]
        for n, fut in enumerate(as_completed(futures), 1):
            pid, status, detail = fut.result()
            if status == "ok":
                ok += 1
                log(f"  + [{n}/{len(todo)}] {detail}")
            elif status == "okfb":
                ok += 1
                refreshed += 1
                log(f"  + [{n}/{len(todo)}] {detail}")
            elif status == "nophoto":
                nophoto += 1
                log(f"  - [{n}/{len(todo)}] no photo: {detail}")
            else:
                failed += 1
                log(f"  ! [{n}/{len(todo)}] FAILED: {detail}")
                with open(FAIL_LOG, "a", encoding="utf-8") as f:
                    f.write(pid + "\t" + detail + "\n")

    mins = (time.time() - t0) / 60
    print(f"\nDone in {mins:.1f} min: {ok} downloaded, {nophoto} without photos, "
          f"{failed} failed (see photos_failed.log).")
    if refreshed:
        print(f"  NOTE: {refreshed} of {ok} needed a fresh Details lookup (stored "
              f"ref was stale) - expect the full run to cost the Details-included "
              f"estimate, not the discounted one.")
    print("Next: python generate_community_pages.py  (photos join the rich "
          "sitemap tier)  ->  kv_sync.")
    if ok:
        print("\nATTRIBUTION: Google requires attribution when displaying Places "
              "photos - keep the photo credit on pages that use them.")


if __name__ == "__main__":
    main()
