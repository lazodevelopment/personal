#!/usr/bin/env python3
"""
fix_employer_danbren.py — consolidates the three wedding-brand employer docs
into one parent employer: Danbren Media.

Strategy (claim-preserving):
  - RENAME employer j2NJif4a2iUziTueFGZu (currently "Atavia Weddings") to
    "Danbren Media" — your account's employerId claim already points at this
    doc, so no claim change is needed.
  - REPOINT the videographer + editor jobs' employerId to that doc.
  - DELETE the two now-orphaned employer docs (52 Eighty, 83 Weddings).

USAGE:  python fix_employer_danbren.py --key serviceAccount.json
Then:   python generate_roven_pages.py --key serviceAccount.json --site C:\\Users\\kurvh\\roven-site
        (regenerates the SEO pages — old brand company pages get replaced)
        NOTE: delete the old files first:
        C:\\Users\\kurvh\\roven-site\\company\\52-eighty-weddings-nfhy2s.html
        C:\\Users\\kurvh\\roven-site\\company\\83-weddings-rs9cup.html
Then redeploy the site.
"""

import argparse

import firebase_admin
from firebase_admin import credentials, firestore

KEEP_ID = "j2NJif4a2iUziTueFGZu"      # becomes Danbren Media (claim points here)
DROP_IDS = [
    "nfhy2s1KYpyzJUNUz0J8",           # 52 Eighty Weddings
    "rS9CUPVShL52VYYRFNU6",           # 83 Weddings
]
NEW_NAME = "Danbren Media"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True)
    args = ap.parse_args()

    firebase_admin.initialize_app(credentials.Certificate(args.key))
    db = firestore.client()

    keep_ref = db.collection("employers").document(KEEP_ID)
    keep = keep_ref.get()
    if not keep.exists:
        raise SystemExit(f"ERROR: employer {KEEP_ID} not found — aborting.")

    # 1) rename the kept employer
    keep_ref.update({"name": NEW_NAME, "industry": "Wedding media"})
    print(f"renamed employer {KEEP_ID} -> '{NEW_NAME}'")

    # 2) repoint all jobs currently under the drop IDs
    for drop_id in DROP_IDS:
        jobs = db.collection("jobs").where("employerId", "==", drop_id).stream()
        for j in jobs:
            j.reference.update({"employerId": KEEP_ID})
            print(f"repointed job '{j.to_dict().get('title')}' ({j.id}) -> {KEEP_ID}")

    # 3) delete orphaned employer docs
    for drop_id in DROP_IDS:
        snap = db.collection("employers").document(drop_id).get()
        if snap.exists:
            db.collection("employers").document(drop_id).delete()
            print(f"deleted orphan employer {drop_id} ({snap.to_dict().get('name')})")
        else:
            print(f"orphan {drop_id} already gone")

    # 4) verify
    print("\nverification:")
    for j in db.collection("jobs").where("status", "==", "active").stream():
        d = j.to_dict()
        print(f"  {d.get('title'):34s} employerId={d.get('employerId')}")
    print(f"\nDone. All active jobs should show employerId={KEEP_ID}.")
    print("Claims unchanged — your account already operates this employer.")

if __name__ == "__main__":
    main()
