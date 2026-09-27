#!/usr/bin/env python3
"""
diagnose_match.py — traces the Resume Match Engine scoring locally.
Loads the job + every opted-in candidate and prints the exact score
breakdown the deployed matcher would compute, plus every disqualifier.

USAGE
  python diagnose_match.py --key serviceAccount.json --job 2vKQSzWRXJ6qnjQ2DxlG
"""

import argparse

import firebase_admin
from firebase_admin import credentials, firestore


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True)
    ap.add_argument("--job", required=True)
    args = ap.parse_args()

    firebase_admin.initialize_app(credentials.Certificate(args.key))
    db = firestore.client()

    job_snap = db.collection("jobs").document(args.job).get()
    if not job_snap.exists:
        raise SystemExit(f"job {args.job} not found")
    job = job_snap.to_dict()
    print(f"JOB: {job.get('title')}  status={job.get('status')!r}  "
          f"type={job.get('employmentType')}  "
          f"loc={job.get('locationCity')}, {job.get('locationState')}  "
          f"remote={job.get('remote')}")
    if job.get("status") != "active":
        print("  !! status is not exactly 'active' — the matcher only fires on "
              "a transition INTO 'active' (lowercase, no spaces)")
    print()

    title = (job.get("title") or "").lower()
    title_words = set(w for w in title.replace("&", " ").split() if len(w) > 3)
    desc = (job.get("description") or "").lower()

    users = list(db.collection("users").where("matchPrefs.notify", "==", True).stream())
    print(f"CANDIDATES with matchPrefs.notify == True: {len(users)}")
    if not users:
        print("  !! zero — the prefs Save either didn't happen or notify is off")
        return

    for snap in users:
        u = snap.to_dict() or {}
        prefs = u.get("matchPrefs") or {}
        email = u.get("email")
        print(f"\n--- {snap.id}")
        print(f"  email on user doc: {email!r}"
              + ("" if email else "   !! MISSING -> matcher SKIPS this user entirely"))
        print(f"  desiredRoles: {prefs.get('desiredRoles')}")
        print(f"  employmentTypes: {prefs.get('employmentTypes')}  metro: {prefs.get('metro')!r}  remoteOk: {prefs.get('remoteOk')}")

        profile = {}
        pr = (db.collection("users").document(snap.id)
              .collection("profileHistory").document("parsed_resume").get())
        if pr.exists:
            d = pr.to_dict() or {}
            print(f"  parsed_resume status: {d.get('status')!r}"
                  + ("" if d.get("status") == "confirmed"
                     else "   (only 'confirmed' profiles contribute skill/title points)"))
            if d.get("status") == "confirmed":
                profile = d.get("parsed") or {}
        else:
            print("  parsed_resume: none")

        score = 0
        for want in prefs.get("desiredRoles", []) or []:
            want_words = set(w for w in want.lower().split() if len(w) > 3)
            if title_words & want_words:
                score += 40
                print(f"  +40 desired role '{want}' overlaps title")
                break
        else:
            print("   +0 no desiredRoles overlap with title "
                  f"(title words: {sorted(title_words)})")

        for role in profile.get("roles", []):
            held = set(w for w in (role.get("title") or "").lower().split() if len(w) > 3)
            if title_words & held:
                score += 25
                print(f"  +25 held title '{role.get('title')}' overlaps")
                break

        skills = [s.lower() for s in profile.get("skills", [])]
        hits = sum(1 for s in skills if s and s in desc)
        if hits:
            pts = min(hits * 5, 20)
            score += pts
            print(f"  +{pts} {hits} skill(s) found in description")

        loc = f"{job.get('locationCity','')}, {job.get('locationState','')}".lower()
        if job.get("remote") or (prefs.get("metro", "").lower() and
                                 prefs.get("metro", "").lower() in loc):
            score += 15
            print("  +15 location fit")
        else:
            print(f"   +0 metro {prefs.get('metro')!r} not in job location {loc!r}")

        etypes = prefs.get("employmentTypes", []) or []
        if job.get("employmentType") in etypes or not etypes:
            score += 10
            print("  +10 employment type fit")
        else:
            print(f"   +0 job type {job.get('employmentType')} not in {etypes}")

        verdict = "PING (>=50)" if score >= 50 and email else (
            "NO PING — score below 50" if email else "NO PING — no email on user doc")
        print(f"  TOTAL: {score}  ->  {verdict}")

        ping = db.collection("jobPings").document(f"{args.job}_{snap.id}").get()
        if ping.exists:
            print("  NOTE: jobPings record already exists — this pair was already "
                  "pinged once and is deduped forever; delete the record to re-test")


if __name__ == "__main__":
    main()
