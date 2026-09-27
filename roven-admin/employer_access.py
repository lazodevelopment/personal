#!/usr/bin/env python3
"""
employer_access.py — who can operate which employer, and grant access.

USAGE
  # see every account and its claims (find your employer account):
  python employer_access.py --key serviceAccount.json --list

  # attach an account to the EXISTING Danbren employer doc:
  python employer_access.py --key serviceAccount.json \
      --email you@example.com --attach j2NJif4a2iUziTueFGZu

Attach merges claims (identityVerified/admin preserved) and sets
employerRole=owner. Sign out/in once afterward to pick up the claim —
the PIPELINE button and PostJob access appear on next sign-in.
"""

import argparse

import firebase_admin
from firebase_admin import auth, credentials, firestore


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--email", default=None)
    ap.add_argument("--attach", default=None, help="existing employer doc id")
    args = ap.parse_args()

    firebase_admin.initialize_app(credentials.Certificate(args.key))

    if args.list:
        db = firestore.client()
        emp_names = {e.id: (e.to_dict() or {}).get("name", "")
                     for e in db.collection("employers").stream()}
        print("AUTH ACCOUNTS AND CLAIMS:\n")
        for user in auth.list_users().iterate_all():
            claims = user.custom_claims or {}
            emp = claims.get("employerId")
            tag = ""
            if emp:
                tag = f"  EMPLOYER: {emp_names.get(emp, '?')} ({emp}) as {claims.get('employerRole')}"
            admin_tag = "  [admin]" if claims.get("admin") else ""
            print(f"  {user.email or '(no email)':40s} uid={user.uid}{admin_tag}{tag}")
        print("\nEMPLOYER DOCS:")
        for eid, name in emp_names.items():
            print(f"  {eid}  {name}")
        return

    if not (args.email and args.attach):
        raise SystemExit("Use --list, or --email + --attach")

    db = firestore.client()
    emp = db.collection("employers").document(args.attach).get()
    if not emp.exists:
        raise SystemExit(f"employer doc {args.attach} not found")
    user = auth.get_user_by_email(args.email)
    merged = dict(user.custom_claims or {})
    merged["employerId"] = args.attach
    merged["employerRole"] = "owner"
    merged.setdefault("identityVerified", True)
    auth.set_custom_user_claims(user.uid, merged)
    print(f"ATTACHED: {args.email} -> {(emp.to_dict() or {}).get('name')} ({args.attach})")
    print("Sign out and back in on that account to pick up the claim.")


if __name__ == "__main__":
    main()
