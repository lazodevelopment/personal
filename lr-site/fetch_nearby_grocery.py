#!/usr/bin/env python3
"""
LeaseReputation — closest-grocery fetcher (Places Nearby Search, New).

For each community, finds the nearest grocery store / supermarket and writes
it to the Firestore doc as:

    nearestGrocery: { name, distanceMi, fetchedAt }

The page generator renders it as a "Closest grocery" tile in the About card.
ONE-TIME cost per community: the answer lives on the doc, so rebuilds are
free forever. Same operating pattern as the photo fetcher:

  * RESUMABLE: docs that already have nearestGrocery are skipped
    (--refresh overrides).
  * TRANCHED: --states AZ,TX / --limit N / --all.
  * COST-AWARE: --dry-run prints the billable call count first.
    Nearby Search bills on a higher SKU than photo media — VERIFY the
    current rate in Cloud Billing before an --all run.

Needs each community's coordinates. The seeder stored these on the docs;
the loader checks the common field shapes (location/geopoint/lat+lng) and
the dry-run reports any docs without coords (those are skipped, logged).

USAGE:
  python fetch_nearby_grocery.py --dry-run
  python fetch_nearby_grocery.py --states AZ --limit 50     # pilot
  python fetch_nearby_grocery.py --all
Then:  python generate_community_pages.py  ->  kv_sync.

Key: PLACES_API_KEY env var (same session var as the photo run).
"""

import os
import sys
import json
import math
import time
import argparse
import datetime
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

PLACES_KEY = os.environ.get("PLACES_API_KEY") or ""

BASE = os.path.dirname(os.path.abspath(__file__))
FAIL_LOG = os.path.join(BASE, "grocery_failed.log")

SERVICE_ACCOUNT_CANDIDATES = [
    os.path.join(BASE, "serviceAccountKey.json"),
    r"C:\Users\kurvh\lease-reputation\serviceAccountKey.json",
]

SEARCH_RADIUS_M = 8000  # 8 km — covers suburban communities; nearest wins anyway

import re
ADDR_STATE_RE = re.compile(r",\s*([A-Z]{2})\s+\d{5}")

_print_lock = threading.Lock()


def log(msg):
    with _print_lock:
        print(msg, flush=True)


def _doc_coords(d):
    """Find lat/lng on the doc across the shapes the seeder may have used."""
    loc = d.get("location")
    # Firestore GeoPoint
    if loc is not None and hasattr(loc, "latitude"):
        return float(loc.latitude), float(loc.longitude)
    if isinstance(loc, dict):
        la = loc.get("lat", loc.get("latitude"))
        ln = loc.get("lng", loc.get("longitude"))
        if la is not None and ln is not None:
            return float(la), float(ln)
    la = d.get("lat", d.get("latitude"))
    ln = d.get("lng", d.get("longitude"))
    if la is not None and ln is not None:
        return float(la), float(ln)
    gp = d.get("geopoint")
    if gp is not None and hasattr(gp, "latitude"):
        return float(gp.latitude), float(gp.longitude)
    return None


def haversine_mi(lat1, lng1, lat2, lng2):
    r = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def load_directory(db):
    from firebase_admin import firestore  # noqa: F401
    out = []
    for doc in db.collection("communities").stream():
        d = doc.to_dict() or {}
        m = ADDR_STATE_RE.search(str(d.get("address") or ""))
        out.append({
            "pid": doc.id,
            "name": str(d.get("name") or "").strip(),
            "state": m.group(1) if m else None,
            "coords": _doc_coords(d),
            "have": isinstance(d.get("nearestGrocery"), dict),
        })
    return out


def nearby_grocery(lat, lng):
    """Nearest grocery via Places Nearby Search (New), distance-ranked."""
    body = json.dumps({
        "includedTypes": ["grocery_store", "supermarket"],
        "maxResultCount": 3,
        "rankPreference": "DISTANCE",
        "languageCode": "en",
        "regionCode": "US",
        "locationRestriction": {
            "circle": {"center": {"latitude": lat, "longitude": lng},
                       "radius": SEARCH_RADIUS_M},
        },
    }).encode()
    req = urllib.request.Request(
        "https://places.googleapis.com/v1/places:searchNearby",
        data=body, method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": PLACES_KEY,
            "X-Goog-FieldMask": "places.displayName,places.location",
        })
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    for p in data.get("places", []):
        dn = p.get("displayName") or {}
        name = (dn.get("text") or "").strip()
        ploc = p.get("location") or {}
        if not name or "latitude" not in ploc:
            continue
        # Spam guard: fake listings pinned at arbitrary coords tend to carry
        # non-Latin names/foreign language codes; a real US grocer resolves
        # to an ASCII-dominant English name. Skip anything that doesn't.
        if dn.get("languageCode") not in (None, "en"):
            continue
        if sum(1 for ch in name if ord(ch) < 128) < max(1, int(len(name) * 0.7)):
            continue
        dist = haversine_mi(lat, lng, ploc["latitude"], ploc["longitude"])
        return {"name": name, "distanceMi": round(dist, 1)}
    return None


def get_place_location(pid):
    """Place Details, location field ONLY -> Essentials SKU (cheap, 10K/mo
    free tier). Used to backfill docs the seeder left without coordinates."""
    req = urllib.request.Request(
        f"https://places.googleapis.com/v1/places/{pid}",
        headers={"X-Goog-Api-Key": PLACES_KEY,
                 "X-Goog-FieldMask": "location"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    loc = data.get("location") or {}
    if "latitude" in loc:
        return float(loc["latitude"]), float(loc["longitude"])
    return None


def fetch_one(db, item):
    pid = item["pid"]
    try:
        coords = item["coords"]
        backfilled = False
        if not coords:
            coords = get_place_location(pid)
            if not coords:
                return pid, "fail", f"{item['name']} — no location on doc or Places"
            db.collection("communities").document(pid).update(
                {"location": {"lat": coords[0], "lng": coords[1]}})
            backfilled = True
        lat, lng = coords
        g = nearby_grocery(lat, lng)
        if not g:
            return pid, "none", item["name"]
        g["fetchedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        db.collection("communities").document(pid).update({"nearestGrocery": g})
        tag = " (coords backfilled)" if backfilled else ""
        return pid, "ok", f"{item['name']}: {g['name']} · {g['distanceMi']} mi{tag}"
    except Exception as e:
        return pid, "fail", f"{item['name']} — {e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--states")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--refresh", action="store_true",
                    help="re-fetch even for docs that already have nearestGrocery")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    if not args.dry_run and not PLACES_KEY:
        sys.exit("ERROR: set $env:PLACES_API_KEY first (session env var).")
    if not args.dry_run and not args.states and not args.limit and not args.all:
        sys.exit("Pick a scope: --states / --limit / --all  (or --dry-run first).")

    key_path = next((p for p in SERVICE_ACCOUNT_CANDIDATES if os.path.exists(p)), None)
    if key_path is None:
        sys.exit("ERROR: serviceAccountKey.json not found.")
    import firebase_admin
    from firebase_admin import credentials, firestore
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(key_path))
    db = firestore.client()

    print("loading directory from Firestore...")
    items = load_directory(db)
    print(f"  {len(items)} communities in directory")

    if args.states:
        want = {s.strip().upper() for s in args.states.split(",")}
        items = [i for i in items if i["state"] in want]
        print(f"  {len(items)} after state filter ({','.join(sorted(want))})")

    n_backfill = sum(1 for i in items if not i["coords"])
    if n_backfill:
        print(f"  {n_backfill} docs lack coordinates -> backfilled in-run via "
              f"Place Details (location only, Essentials SKU: cheap, 10K/mo free)")

    if not args.refresh:
        done = sum(1 for i in items if i["have"])
        items = [i for i in items if not i["have"]]
        print(f"  {done} already have nearestGrocery (skipped), {len(items)} to fetch")

    if args.limit:
        items = items[: args.limit]
        print(f"  capped at {len(items)} this run (--limit)")

    print(f"\n  billable shape: {len(items)} Nearby Search calls"
          + (f" + {n_backfill} Essentials location lookups" if n_backfill else ""))
    print("  VERIFY the Nearby Search SKU rate in Cloud Billing before an "
          "--all run — it bills higher than photo media.")

    if args.dry_run:
        print("\ndry run — no API calls made.")
        return

    ok = none = failed = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = [ex.submit(fetch_one, db, i) for i in items]
        for n, fut in enumerate(as_completed(futures), 1):
            pid, status, detail = fut.result()
            if status == "ok":
                ok += 1
                log(f"  + [{n}/{len(items)}] {detail}")
            elif status == "none":
                none += 1
                log(f"  - [{n}/{len(items)}] none within {SEARCH_RADIUS_M//1000}km: {detail}")
            else:
                failed += 1
                log(f"  ! [{n}/{len(items)}] FAILED: {detail}")
                with open(FAIL_LOG, "a", encoding="utf-8") as f:
                    f.write(pid + "\t" + detail + "\n")

    mins = (time.time() - t0) / 60
    print(f"\nDone in {mins:.1f} min: {ok} written, {none} with no grocery "
          f"nearby, {failed} failed (see grocery_failed.log).")
    print("Next: python generate_community_pages.py  ->  kv_sync.")


if __name__ == "__main__":
    main()
