"""Put every vendor in the metro it is actually closest to.  JC-LAZO-FIXMETRO-0916-001

Google Places' locationBias is a BIAS, not a fence: a Baltimore search happily
returns businesses in Washington, Philadelphia and Lancaster. Vendors are keyed by
placeId globally and written with merge=True, so whichever metro seeded LAST won -
seeding Baltimore on 2026-09-16 claimed 309 Washington businesses and 74
Philadelphia ones, including a limo company on K St NW.

The seeder now refuses foreign results (nearest_metro guard), but that only helps
future seeds. This repairs what is already in Firestore: for every vendor, find the
metro whose grid it sits closest to, and move it there if it is somewhere else.

    python seed\\fix_metro_assignment.py --audit              # report only
    python seed\\fix_metro_assignment.py --audit --metro baltimore
    python seed\\fix_metro_assignment.py --apply              # write the moves
    python seed\\fix_metro_assignment.py --apply --metro baltimore

A vendor with no coordinates is left alone - there is nothing to measure. Run a
build afterwards: the redirect layer turns each move into a 301, and a page that
moves back where it started drops out of the map rather than redirecting to itself.
"""
import argparse
import collections
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.metros import METROS

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass


def _mi(a, b):
    la1, lo1, la2, lo2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(h))


def nearest_metro(lat, lng):
    if lat is None or lng is None:
        return None, None
    d, mid = min(((min(_mi((lat, lng), g) for g in m["grid"]), m["id"]) for m in METROS))
    return mid, d


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--audit", action="store_true", help="report only, write nothing")
    g.add_argument("--apply", action="store_true", help="write the corrected metroId")
    ap.add_argument("--metro", help="limit to vendors currently in this metro")
    a = ap.parse_args()

    import firebase_admin
    from firebase_admin import credentials, firestore
    firebase_admin.initialize_app(
        credentials.Certificate(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]))
    db = firestore.client()

    metro_ids = [a.metro] if a.metro else [m["id"] for m in METROS]
    moves = collections.Counter()
    no_coords = 0
    checked = 0
    pending = []

    for mid in metro_ids:
        for doc in db.collection("vendors").where("metroId", "==", mid).stream():
            v = doc.to_dict()
            checked += 1
            want, dist = nearest_metro(v.get("lat"), v.get("lng"))
            if want is None:
                no_coords += 1
                continue
            if want != mid:
                moves[f"{mid} -> {want}"] += 1
                pending.append((doc.id, mid, want, round(dist or 0), v.get("name", "")[:40]))

    print(f"checked {checked:,} vendors across {len(metro_ids)} metro(s)")
    print(f"  no coordinates, left alone : {no_coords:,}")
    print(f"  in the wrong metro         : {len(pending):,}")
    for k, n in moves.most_common(25):
        print(f"      {k:<42} {n:5,}")
    if len(moves) > 25:
        print(f"      ... and {len(moves) - 25} more pairs")

    if pending[:8]:
        print("\n  examples:")
        for pid, was, want, d, nm in pending[:8]:
            print(f"    {nm:<40} {was} -> {want} ({d} mi)")

    if a.audit:
        print("\n--audit: nothing written. Re-run with --apply to move them.")
        return

    if not pending:
        print("\nnothing to do.")
        return

    batch = db.batch()
    n = 0
    for pid, _was, want, _d, _nm in pending:
        batch.update(db.collection("vendors").document(pid), {"metroId": want})
        n += 1
        if n % 400 == 0:
            batch.commit()
            batch = db.batch()
            print(f"  committed {n:,}/{len(pending):,}", flush=True)
    batch.commit()
    print(f"\nmoved {n:,} vendors. Run a build next - the redirect layer will 301 the "
          f"pages that changed URL.")


if __name__ == "__main__":
    main()
