#!/usr/bin/env python3
# ============================================================================
# ROVEN — approve_employer.py
# Build ID: JC-ROVEN-APPROVEEMP-0729-001
#
# The other half of self-serve intake. Lists pending employerApplications;
# --approve converts one into a real employer: creates the employers doc
# (verified, notifyEmail set for the freshness sweep), grants the applicant
# uid the employerId + email_verified-independent claims, marks the
# application approved. Client code can never do any of this — Admin SDK
# only, which is the entire security model.
#
# Usage:
#   python approve_employer.py --key serviceAccount.json                # list
#   python approve_employer.py --key serviceAccount.json --approve <id> # approve
#   python approve_employer.py --key serviceAccount.json --reject <id>  # reject
# ============================================================================
import argparse
import sys

import firebase_admin
from firebase_admin import auth, credentials, firestore


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--key", required=True)
    p.add_argument("--approve")
    p.add_argument("--reject")
    args = p.parse_args()

    firebase_admin.initialize_app(credentials.Certificate(args.key))
    db = firestore.client()

    if args.approve:
        ref = db.collection("employerApplications").document(args.approve)
        snap = ref.get()
        if not snap.exists:
            sys.exit(f"No application {args.approve}")
        a = snap.to_dict()
        if a.get("status") == "approved":
            sys.exit("Already approved.")

        emp_ref = db.collection("employers").document()
        emp_ref.set({
            "name": a.get("companyName", ""),
            "website": a.get("website", ""),
            "industry": a.get("industry", ""),
            "metro": a.get("metro", ""),
            "verified": True,
            "verificationMethod": "manual_founder",
            "notifyEmail": a.get("email", ""),
            "members": [a.get("uid")],
            "createdAt": firestore.SERVER_TIMESTAMP,
            "stats": {
                "applicationsReceived": 0,
                "dispositionedCount": 0,
                "hiresReported": 0,
            },
        })

        uid = a.get("uid")
        user = auth.get_user(uid)
        claims = dict(user.custom_claims or {})
        claims["employerId"] = emp_ref.id
        auth.set_custom_user_claims(uid, claims)

        ref.update({
            "status": "approved",
            "employerId": emp_ref.id,
            "approvedAt": firestore.SERVER_TIMESTAMP,
        })
        print(f"APPROVED: {a.get('companyName')} -> employer {emp_ref.id}")
        print(f"  uid {uid} granted employerId claim")
        print(f"  notifyEmail: {a.get('email')}")
        print("  They must sign out/in (or wait <1h) for the claim to load.")
        return

    if args.reject:
        db.collection("employerApplications").document(args.reject).update(
            {"status": "rejected", "rejectedAt": firestore.SERVER_TIMESTAMP})
        print(f"Rejected {args.reject}")
        return

    docs = list(db.collection("employerApplications")
                .where("status", "==", "pending").stream())
    if not docs:
        print("No pending employer applications.")
        return
    print(f"{len(docs)} pending:")
    for d in docs:
        a = d.to_dict()
        print(f"  {d.id}")
        print(f"    {a.get('companyName')}  ·  {a.get('industry')}  ·  {a.get('metro')}")
        print(f"    {a.get('contactName')} ({a.get('contactRole')})  ·  {a.get('email')}")
        print(f"    site: {a.get('website') or '—'}")
    print("\nApprove with:  python approve_employer.py --key serviceAccount.json --approve <id>")


if __name__ == "__main__":
    main()
