"""Lazo Places seeder v2 — metro-agnostic, resumable, ToS-aware.
v2 fixes (2026-07-23): per-tile progress output; bounded 429 retries with loud
warnings; harvested vendors persist in the checkpoint so Ctrl+C loses nothing.

Usage (PowerShell):
  python seed\\places_seeder.py --tranche 4 --dry-run
  python seed\\places_seeder.py --metro miami
  python seed\\places_seeder.py --tranche 4
"""
import argparse, json, math, os, sys, threading, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.taxonomy import CATEGORIES
from config.metros import METROS, BY_ID, metros_for_tranche

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass

import requests

# JC-LAZO-SEED-0916-004: this machine resolves AAAA records for googleapis.com but
# cannot reach them. curl survives it (Happy Eyeballs falls back to IPv4 in
# milliseconds); urllib3 picks the v6 address and blocks forever, which is what
# froze the 2026-09-16 runs - measured: dual-stack hung past 25s, forced IPv4
# answered in 0.6s. Pin the resolver to IPv4 unless LAZO_ALLOW_IPV6 says otherwise.
if not os.environ.get("LAZO_ALLOW_IPV6"):
    import socket as _socket
    import urllib3.util.connection as _u3c
    _u3c.allowed_gai_family = lambda: _socket.AF_INET

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.location",
    "places.websiteUri",
    "places.nationalPhoneNumber",
    "places.businessStatus",
    "nextPageToken",
])
CHECKPOINT_DIR = Path(__file__).resolve().parent / ".checkpoints"


def _mi(a, b):
    la1, lo1, la2, lo2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(h))


def nearest_metro(lat, lng):
    """The metro whose grid this place actually sits closest to.

    JC-LAZO-SEED-0916-005: Places' locationBias is a BIAS, not a fence - a Baltimore
    search returns businesses in Washington, Philadelphia and Lancaster. Because
    vendors are keyed by placeId globally with merge=True, whichever metro seeded
    LAST used to win, so seeding Baltimore claimed 309 Washington businesses and 74
    Philadelphia ones, including a limo company on K St NW. Distance decides now,
    not running order.
    """
    if lat is None or lng is None:
        return None
    return min(((min(_mi((lat, lng), g) for g in m["grid"]), m["id"]) for m in METROS))[1]
COST_PER_CALL = 0.032
MAX_RETRIES = 5
HANG_SECONDS = 45   # wall-clock budget for one Places call (see _post_with_deadline)


class _Hung(Exception):
    """The request did not answer inside its wall-clock budget."""


def _post_with_deadline(body, api_key, seconds):
    """POST on a DAEMON thread so a wedged socket cannot stall the job.

    A plain ThreadPoolExecutor is no good here: its context manager shuts down with
    wait=True, and concurrent.futures joins its workers at interpreter exit - either
    would re-introduce the hang this exists to prevent. A daemon thread is abandoned
    cleanly and never holds up exit.
    """
    out = {}

    def _run():
        try:
            out["r"] = requests.post(
                SEARCH_URL, json=body,
                headers={"X-Goog-Api-Key": api_key, "X-Goog-FieldMask": FIELD_MASK},
                timeout=30,
            )
        except BaseException as e:   # noqa: BLE001 - reported on the calling thread
            out["e"] = e

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(seconds)
    if t.is_alive():
        raise _Hung(f"no answer in {seconds}s")
    if "e" in out:
        raise out["e"]
    return out["r"]


def places_search(api_key: str, query: str, lat: float, lng: float, radius_m: int, page_token):
    body = {
        "textQuery": query,
        "locationBias": {"circle": {"center": {"latitude": lat, "longitude": lng}, "radius": float(radius_m)}},
        "pageSize": 20,
    }
    if page_token:
        body["pageToken"] = page_token
    delay = 3.0
    for attempt in range(1, MAX_RETRIES + 1):
        # JC-LAZO-SEED-0916-003: requests' timeout= does NOT bound DNS resolution or
        # a half-open socket, and on 2026-09-16 two separate runs froze mid-job with an
        # idle CPU and no exception - one at 0 tile-queries, one at 2. A wall-clock
        # watchdog is the only thing that actually bounds it: run the call on a worker
        # thread and abandon it if it has not answered in 45s. The orphaned thread dies
        # with the process; the job keeps moving and the checkpoint keeps advancing.
        try:
            r = _post_with_deadline(body, api_key, HANG_SECONDS)
        except _Hung:
            print(f"    ! request hung >{HANG_SECONDS}s, attempt {attempt}/{MAX_RETRIES}, retrying", flush=True)
            continue
        except requests.RequestException as e:
            print(f"    ! {type(e).__name__}, attempt {attempt}/{MAX_RETRIES}, sleeping {delay:.0f}s", flush=True)
            time.sleep(delay); delay *= 2
            continue
        if r.status_code == 429 or r.status_code >= 500:
            # JC-LAZO-SEED-0921-001: a single Google-side 500 killed the 2026-09-21
            # tranche-7 run 23 metros in. 5xx is transient; retry it like a 429.
            what = "rate-limited (429)" if r.status_code == 429 else f"server error ({r.status_code})"
            print(f"    ! {what}, attempt {attempt}/{MAX_RETRIES}, sleeping {delay:.0f}s", flush=True)
            time.sleep(delay)
            delay *= 2
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("Places API did not answer after retries — check quotas/billing/network.")


def load_ckpt(metro_id: str):
    p = CHECKPOINT_DIR / f"{metro_id}.json"
    if not p.exists():
        return set(), {}
    data = json.loads(p.read_text())
    return set(data.get("done", [])), data.get("vendors", {})


def save_ckpt(metro_id: str, done: set, vendors: dict):
    p = CHECKPOINT_DIR / f"{metro_id}.json"
    p.write_text(json.dumps({"done": sorted(done), "vendors": vendors}))


def seed_metro(metro: dict, db, api_key: str, dry_run: bool) -> dict:
    stats = {"calls": 0, "found": 0, "written": 0, "merged": 0, "foreign": 0}
    CHECKPOINT_DIR.mkdir(exist_ok=True)
    done, vendors = load_ckpt(metro["id"])

    tasks = [
        (cat, q, tile)
        for cat in CATEGORIES
        for q in cat["places_queries"]
        for tile in metro["grid"]
    ]
    remaining = [t for t in tasks if f"{t[0]['slug']}|{t[1]}|{t[2][0]:.4f},{t[2][1]:.4f}" not in done]
    print(f"[{metro['id']}] {len(tasks)} tile-queries total, {len(remaining)} remaining, "
          f"{len(vendors)} vendors carried from checkpoint", flush=True)

    if dry_run:
        est_calls = len(remaining) * 2.2
        print(f"[dry-run] est. API calls ~{est_calls:.0f}  est. cost ~${est_calls * COST_PER_CALL:.2f}", flush=True)
        stats["calls"] = int(est_calls)
        return stats

    completed = 0
    for cat, q, (lat, lng) in tasks:
        task_key = f"{cat['slug']}|{q}|{lat:.4f},{lng:.4f}"
        if task_key in done:
            continue
        token = None
        for _page in range(3):
            data = places_search(api_key, f"{q} near me", lat, lng, metro["radius_m"], token)
            stats["calls"] += 1
            for p in data.get("places", []):
                if p.get("businessStatus") == "CLOSED_PERMANENTLY":
                    continue
                pid = p["id"]
                _lat = (p.get("location") or {}).get("latitude")
                _lng = (p.get("location") or {}).get("longitude")
                # a result this metro is not the closest to belongs to someone else
                if nearest_metro(_lat, _lng) != metro["id"]:
                    stats["foreign"] = stats.get("foreign", 0) + 1
                    continue
                stats["found"] += 1
                if pid in vendors:
                    if cat["slug"] not in vendors[pid]["categories"]:
                        vendors[pid]["categories"].append(cat["slug"])
                        stats["merged"] += 1
                else:
                    vendors[pid] = {
                        "placeId": pid,
                        "name": (p.get("displayName") or {}).get("text", "").strip(),
                        "address": p.get("formattedAddress", ""),
                        "lat": (p.get("location") or {}).get("latitude"),
                        "lng": (p.get("location") or {}).get("longitude"),
                        "website": p.get("websiteUri", ""),
                        "phone": p.get("nationalPhoneNumber", ""),
                        "categories": [cat["slug"]],
                        "metroId": metro["id"],
                        "claimStatus": "unclaimed",
                        "verified": False,
                        "priceRangeVerified": None,
                        "source": "places_seed_v1",
                    }
            token = data.get("nextPageToken")
            if not token:
                break
            time.sleep(0.3)
        done.add(task_key)
        completed += 1
        save_ckpt(metro["id"], done, vendors)
        if completed % 10 == 0 or completed == len(remaining):
            print(f"  [{metro['id']}] {completed}/{len(remaining)} tile-queries done, "
                  f"{len(vendors)} vendors, {stats['calls']} calls", flush=True)

    from google.cloud import firestore as fs
    batch = db.batch()
    n = 0
    for pid, v in vendors.items():
        ref = db.collection("vendors").document(pid)
        v = dict(v)
        v["seededAt"] = fs.SERVER_TIMESTAMP
        batch.set(ref, v, merge=True)
        n += 1
        if n % 400 == 0:
            batch.commit()
            batch = db.batch()
    batch.commit()
    stats["written"] = n
    print(f"[{metro['id']}] DONE calls={stats['calls']} unique_vendors={n} "
          f"merges={stats['merged']} skipped_nearer_other_metro={stats['foreign']}", flush=True)
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metro")
    ap.add_argument("--tranche", type=int)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    targets = [BY_ID[args.metro]] if args.metro else metros_for_tranche(args.tranche or 1)

    api_key = os.environ.get("PLACES_API_KEY")
    if not api_key and not args.dry_run:
        sys.exit("PLACES_API_KEY not set.")

    db = None
    if not args.dry_run:
        import firebase_admin
        from firebase_admin import credentials, firestore
        cred = credentials.Certificate(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
        firebase_admin.initialize_app(cred)
        db = firestore.client()

    totals = {"calls": 0, "written": 0}
    for m in targets:
        s = seed_metro(m, db, api_key, args.dry_run)
        totals["calls"] += s["calls"]
        totals["written"] += s["written"]
    print(f"TOTAL calls={totals['calls']} vendors_written={totals['written']} "
          f"est_cost=${totals['calls'] * COST_PER_CALL:.2f}", flush=True)


if __name__ == "__main__":
    main()
