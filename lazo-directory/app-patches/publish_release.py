"""Publish the Lazo release notice: writes stats/appRelease (JC-LAZO-RELEASE-1020).

The Couple (v180+) and Vendor (v222+) dashboards read this doc on start.

    python publish_release.py                       # notes, key, title, links from release_notes.json
    python publish_release.py --couple 180 --vendor 222   # ...and the builds now LIVE IN THE STORES
    python publish_release.py --show                # print the doc as it is

Two separate things live in the doc:
  * key / title / notes / ios / android  - publish these the moment the web
    build is live; web users and up-to-date phones see What's new once.
  * couple / vendor (store builds)       - bump these ONLY after that build is
    approved in the App Store and Play Store. A phone whose widget is older than
    this number gets the "Lazo has been updated" popup with an Update button, so
    a number ahead of the stores sends people to a store page that has nothing
    new yet.

Needs GOOGLE_APPLICATION_CREDENTIALS in ../.env (the same service account as
add_vendor.py); stats/* is public-read, write false, so only admin SDK writes.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")

import firebase_admin  # noqa: E402
from firebase_admin import credentials, firestore  # noqa: E402

VALID_COUPLE_OPEN = {"hub", "vendors", "registry", "checklist", "browse", "account", "guests",
                     "website", "june", "messages", "dayof", "shopping", "board"}
VALID_VENDOR_OPEN = {"", "leads", "profile", "studio", "pipeline", "money"}


def load_notes(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    for k in ("key", "title", "ios", "android", "notes"):
        if k not in data:
            raise SystemExit(f"release_notes.json is missing '{k}'")
    for n in data["notes"]:
        who = n.get("for", "both")
        if who not in ("couple", "vendor", "both"):
            raise SystemExit(f"bad 'for' on note {n.get('title')!r}: {who}")
        op = n.get("open", "")
        if who in ("couple", "both") and op not in VALID_COUPLE_OPEN:
            raise SystemExit(f"note {n.get('title')!r}: open={op!r} is not a couple view")
        if who in ("vendor", "both") and op not in VALID_VENDOR_OPEN:
            raise SystemExit(f"note {n.get('title')!r}: open={op!r} is not a vendor mode")
        for k in ("title", "line1", "line2"):
            if not str(n.get(k, "")).strip():
                raise SystemExit(f"note {n.get('title')!r}: '{k}' is empty")
    return data


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--notes", default=str(HERE / "release_notes.json"))
    ap.add_argument("--couple", type=int, help="Couple widget build now live in the stores (e.g. 180)")
    ap.add_argument("--vendor", type=int, help="Vendor widget build now live in the stores (e.g. 222)")
    ap.add_argument("--show", action="store_true", help="print the current doc and exit")
    ap.add_argument("--dry-run", action="store_true", help="print what would be written, write nothing")
    args = ap.parse_args()

    cred = credentials.Certificate(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    ref = db.collection("stats").document("appRelease")

    if args.show:
        snap = ref.get()
        print(json.dumps(snap.to_dict() or {}, indent=2, default=str))
        return

    data = load_notes(Path(args.notes))
    doc = {
        "key": data["key"],
        "title": data["title"],
        "ios": data["ios"],
        "android": data["android"],
        "notes": data["notes"],
        "publishedAt": datetime.now(timezone.utc),
    }
    if args.couple is not None:
        doc["couple"] = args.couple
    if args.vendor is not None:
        doc["vendor"] = args.vendor

    couple_n = sum(1 for n in data["notes"] if n.get("for", "both") in ("couple", "both"))
    vendor_n = sum(1 for n in data["notes"] if n.get("for", "both") in ("vendor", "both"))
    print(f"release {data['key']} ({data['title']}): {couple_n} couple notes, {vendor_n} vendor notes")
    if args.couple is None and args.vendor is None:
        print("store builds untouched (pass --couple / --vendor once the store build is approved)")
    else:
        print(f"store builds -> couple={args.couple} vendor={args.vendor}")
    if args.dry_run:
        print(json.dumps(doc, indent=2, default=str))
        return
    ref.set(doc, merge=True)
    print("written: stats/appRelease")


if __name__ == "__main__":
    main()
