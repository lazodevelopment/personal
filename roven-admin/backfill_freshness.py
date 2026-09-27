#!/usr/bin/env python3
# ============================================================================
# ROVEN — backfill_freshness.py  (one-time)
# Build ID: JC-ROVEN-BACKFILL-0729-001
#
# Arms the freshness contract on pre-existing data:
#   1. Every active job without confirmedOpenAt gets it set to now — the
#      30-day clock starts today, honestly.
#   2. The Danbren employer doc gets notifyEmail so the sweep can reach you.
#
# Usage: python backfill_freshness.py --key serviceAccount.json
# ============================================================================
import argparse

import firebase_admin
from firebase_admin import credentials, firestore

DANBREN_EMPLOYER_ID = "j2NJif4a2iUziTueFGZu"
DANBREN_NOTIFY = "rovenhr@gmail.com"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--key", required=True)
    args = p.parse_args()
    firebase_admin.initialize_app(credentials.Certificate(args.key))
    db = firestore.client()

    n = 0
    for snap in db.collection("jobs").stream():
        j = snap.to_dict() or {}
        if j.get("status") in ("active", "pending_review") and not j.get("confirmedOpenAt"):
            snap.reference.update({
                "confirmedOpenAt": firestore.SERVER_TIMESTAMP,
                "confirmedOpen": True,
            })
            n += 1
            print(f"  armed: {j.get('title')} ({snap.id})")
    print(f"{n} jobs armed with confirmedOpenAt")

    db.collection("employers").document(DANBREN_EMPLOYER_ID).update(
        {"notifyEmail": DANBREN_NOTIFY})
    print(f"Danbren notifyEmail -> {DANBREN_NOTIFY}")


if __name__ == "__main__":
    main()
