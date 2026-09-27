#!/usr/bin/env python3
"""
provision_employer.py — Roven concierge employer onboarding
============================================================
Creates a verified employer account and grants the operating user their
claims — the manual counterpart to future Middesk-automated self-serve.
One command per founding employer.

USAGE
  python provision_employer.py --key serviceAccount.json \
      --name "Acme Dental Group" \
      --email owner@acmedental.com \
      [--metro Phoenix] [--industry "Dental"] \
      [--role owner]              # owner | recruiter

REQUIREMENTS
  - The --email account must already exist in Firebase Auth (they sign up
    through the app first, which also grants them identityVerified).
  - You have verified the business yourself (this script records
    middeskVerification.method = "manual_founder" until the Middesk API
    is wired).

WHAT IT DOES
  1. employers/{new id}: name/metro/industry, verified=True,
     pricingTier="founding", empty billing stub
  2. Custom claims on the user: employerId + employerRole
     (PRESERVES existing claims — identityVerified/admin stay intact)
  3. Prints the employer doc id for your records

NOTE  One employerId per account in the v1 claims model. Running this on a
      user who already has an employerId claim will REPLACE it — the script
      warns and asks before doing so.
"""

import argparse
import sys
from datetime import datetime, timezone

import firebase_admin
from firebase_admin import auth, credentials, firestore


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True)
    ap.add_argument("--name", required=True, help="Legal/display business name")
    ap.add_argument("--email", required=True, help="Operating user's account email")
    ap.add_argument("--metro", default="Phoenix")
    ap.add_argument("--industry", default="")
    ap.add_argument("--role", default="owner", choices=["owner", "recruiter"])
    args = ap.parse_args()

    firebase_admin.initialize_app(credentials.Certificate(args.key))
    db = firestore.client()
    now = datetime.now(timezone.utc)

    # ---- user must exist ----
    try:
        user = auth.get_user_by_email(args.email)
    except Exception:
        sys.exit(
            f"ERROR: no Auth user for {args.email}. Have them sign up in the "
            "app first (that also grants identityVerified), then rerun."
        )

    # ---- existing-claim guard ----
    existing = user.custom_claims or {}
    if existing.get("employerId"):
        print(
            f"WARNING: {args.email} already operates employer "
            f"{existing['employerId']} as {existing.get('employerRole')}."
        )
        answer = input("Replace with the new employer? [y/N] ").strip().lower()
        if answer != "y":
            sys.exit("Aborted — claims unchanged.")

    # ---- 1. employer doc ----
    ref = db.collection("employers").document()
    ref.set(
        {
            "name": args.name,
            "metro": args.metro,
            "industry": args.industry,
            "verified": True,
            "middeskVerification": {
                "status": "verified",
                "method": "manual_founder",
                "verifiedAt": now,
            },
            "pricingTier": "founding",
            "billing": {},
            "createdAt": now,
        }
    )

    # ---- 2. claims (merge, don't clobber) ----
    merged = dict(existing)
    merged["employerId"] = ref.id
    merged["employerRole"] = args.role
    merged.setdefault("identityVerified", True)
    auth.set_custom_user_claims(user.uid, merged)

    print(f"\nemployer  {args.name} -> {ref.id}")
    print(f"claims    {args.email} (uid {user.uid}): employerRole={args.role}")
    print("          existing claims preserved:", {k: v for k, v in existing.items() if k not in ('employerId','employerRole')} or "none")
    print("\nDone. Remind them: sign out/in once to pick up the claims.")
    print("Their PIPELINE button appears in the app on next sign-in.")
    print("\nWhen they have jobs to post (until the posting form ships),")
    print("use seed-style Admin SDK inserts or wait for the JobPost widget.")


if __name__ == "__main__":
    main()
