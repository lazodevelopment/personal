#!/usr/bin/env python3
"""
approve_jobs.py — your job review desk.
Lists pending_review jobs; approving flips status -> active, which fires
on_job_activated and pings matching candidates automatically.

USAGE
  python approve_jobs.py --key serviceAccount.json                 # list pending
  python approve_jobs.py --key serviceAccount.json --approve JOBID # activate one
  python approve_jobs.py --key serviceAccount.json --approve-all   # activate all
  python approve_jobs.py --key serviceAccount.json --reject JOBID  # -> rejected
"""

import argparse

import firebase_admin
from firebase_admin import credentials, firestore


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True)
    ap.add_argument("--approve", default=None)
    ap.add_argument("--approve-all", action="store_true")
    ap.add_argument("--reject", default=None)
    args = ap.parse_args()

    firebase_admin.initialize_app(credentials.Certificate(args.key))
    db = firestore.client()

    if args.approve:
        db.collection("jobs").document(args.approve).update({"status": "active"})
        print(f"APPROVED -> active: {args.approve} (match engine firing)")
        return
    if args.reject:
        db.collection("jobs").document(args.reject).update({"status": "rejected"})
        print(f"REJECTED: {args.reject}")
        return

    pending = list(db.collection("jobs")
                   .where("status", "==", "pending_review").stream())
    if args.approve_all:
        for s in pending:
            s.reference.update({"status": "active"})
            print(f"APPROVED -> active: {s.id}  {s.to_dict().get('title','')}")
        print(f"\n{len(pending)} activated.")
        return

    if not pending:
        print("No jobs pending review.")
        return
    print(f"{len(pending)} pending review:\n")
    for s in pending:
        j = s.to_dict()
        emp = ""
        try:
            e = db.collection("employers").document(j.get("employerId", "")).get()
            emp = (e.to_dict() or {}).get("name", "")
        except Exception:
            pass
        pay = f"${j.get('salaryMin','?')}"
        if j.get("salaryMax") and j.get("salaryMax") != j.get("salaryMin"):
            pay += f"-${j['salaryMax']}"
        pay += {"HOUR": "/hr", "DAY": "/day", "YEAR": "/yr"}.get(j.get("salaryUnit", ""), "")
        print(f"  {s.id}")
        print(f"    {j.get('title','')}  ·  {emp}")
        print(f"    {j.get('employmentType','')}  ·  "
              f"{j.get('locationCity','')}, {j.get('locationState','')}  ·  {pay}")
        desc = (j.get("description") or "").replace("\n", " ")
        print(f"    {desc[:110]}{'...' if len(desc) > 110 else ''}\n")
    print("Approve with:  python approve_jobs.py --key serviceAccount.json --approve <id>")


if __name__ == "__main__":
    main()
