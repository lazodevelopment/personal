#!/usr/bin/env python3
"""
test_match_engine.py — one-command end-to-end test of the Resume Match Engine.

Does, in order:
  1. DIAGNOSE  — scores the candidate exactly as the deployed matcher would
  2. REPAIR    — (--fix) writes the email from Firebase Auth onto the user doc
                 and ensures the desired role is set (both idempotent)
  3. CLEAR     — deletes any jobPings dedupe record so the pair can re-ping
  4. FLIP      — (--flip) pauses then re-activates the job via Admin SDK
  5. VERIFY    — polls jobPings for up to 60s and reports the verdict

USAGE (the full test in one line):
  python test_match_engine.py --key serviceAccount.json ^
      --job 2vKQSzWRXJ6qnjQ2DxlG --user JKIO87gCa5QebJUcbzB9amB8OUG3 ^
      --set-role "Wedding Photographer" --fix --flip
"""

import argparse
import time

import firebase_admin
from firebase_admin import auth, credentials, firestore


def score_breakdown(job, prefs, profile):
    lines, score = [], 0
    title = (job.get("title") or "").lower()
    tw = set(w for w in title.replace("&", " ").split() if len(w) > 3)
    for want in prefs.get("desiredRoles", []) or []:
        if tw & set(w for w in want.lower().split() if len(w) > 3):
            score += 40
            lines.append(f"  +40 desired role '{want}'")
            break
    else:
        lines.append(f"   +0 desiredRoles {prefs.get('desiredRoles')} vs title words {sorted(tw)}")
    for r in (profile or {}).get("roles", []):
        if tw & set(w for w in (r.get("title") or "").lower().split() if len(w) > 3):
            score += 25
            lines.append(f"  +25 held title '{r.get('title')}'")
            break
    desc = (job.get("description") or "").lower()
    hits = sum(1 for s in [x.lower() for x in (profile or {}).get("skills", [])] if s and s in desc)
    if hits:
        score += min(hits * 5, 20)
        lines.append(f"  +{min(hits*5,20)} skills in description")
    loc = f"{job.get('locationCity','')}, {job.get('locationState','')}".lower()
    if job.get("remote") or (prefs.get("metro", "").lower() and prefs.get("metro", "").lower() in loc):
        score += 15
        lines.append("  +15 location")
    if job.get("employmentType") in (prefs.get("employmentTypes") or []) or not prefs.get("employmentTypes"):
        score += 10
        lines.append("  +10 employment type")
    return score, lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True)
    ap.add_argument("--job", required=True)
    ap.add_argument("--user", required=True)
    ap.add_argument("--set-role", default=None)
    ap.add_argument("--fix", action="store_true")
    ap.add_argument("--flip", action="store_true")
    args = ap.parse_args()

    firebase_admin.initialize_app(credentials.Certificate(args.key))
    db = firestore.client()

    job_ref = db.collection("jobs").document(args.job)
    user_ref = db.collection("users").document(args.user)
    job = job_ref.get().to_dict()
    if not job:
        raise SystemExit("job not found")

    # ---------- REPAIR ----------
    if args.fix:
        updates = {}
        udoc = user_ref.get().to_dict() or {}
        if not udoc.get("email"):
            try:
                rec = auth.get_user(args.user)
                if rec.email:
                    updates["email"] = rec.email
                    print(f"[fix] email <- {rec.email} (from Firebase Auth)")
            except Exception as exc:
                print(f"[fix] couldn't read Auth record: {exc}")
        prefs = udoc.get("matchPrefs") or {}
        roles = prefs.get("desiredRoles") or []
        if args.set_role and args.set_role not in roles:
            roles.append(args.set_role)
            updates["matchPrefs.desiredRoles"] = roles
            print(f"[fix] desiredRoles <- {roles}")
        if not prefs.get("notify"):
            updates["matchPrefs.notify"] = True
            print("[fix] notify <- True")
        if updates:
            user_ref.update(updates)
        else:
            print("[fix] nothing to repair")

    # ---------- DIAGNOSE ----------
    udoc = user_ref.get().to_dict() or {}
    prefs = udoc.get("matchPrefs") or {}
    email = udoc.get("email")
    profile = {}
    pr = user_ref.collection("profileHistory").document("parsed_resume").get()
    if pr.exists and (pr.to_dict() or {}).get("status") == "confirmed":
        profile = (pr.to_dict() or {}).get("parsed") or {}
    score, lines = score_breakdown(job, prefs, profile)
    print(f"\nDIAGNOSIS  user={args.user}")
    print(f"  email: {email!r}")
    for ln in lines:
        print(ln)
    print(f"  TOTAL {score}  -> {'WOULD PING' if score >= 50 and email else 'WOULD NOT PING'}")
    if score < 50 or not email:
        print("\nStopping — fix the above first (rerun with --fix / --set-role).")
        return

    # ---------- CLEAR DEDUPE ----------
    ping_ref = db.collection("jobPings").document(f"{args.job}_{args.user}")
    if ping_ref.get().exists:
        ping_ref.delete()
        print("[clear] removed existing jobPings dedupe record")

    # ---------- FLIP ----------
    if not args.flip:
        print("\nAdd --flip to trigger the deployed matcher.")
        return
    print("\n[flip] pausing job...")
    job_ref.update({"status": "paused"})
    time.sleep(3)
    print("[flip] re-activating job...")
    job_ref.update({"status": "active"})

    # ---------- VERIFY ----------
    print("[verify] polling jobPings for up to 60s...")
    for i in range(20):
        time.sleep(3)
        snap = ping_ref.get()
        if snap.exists:
            d = snap.to_dict()
            print(f"\nSUCCESS ✓  pinged (score {d.get('score')}). Resend accepted the "
                  f"send — check the inbox for {email}.")
            return
    print("\nNO PING after 60s despite a passing local score.")
    print("That isolates the failure to the DEPLOYED function's run — check its")
    print("logs for this window (Cloud Run -> on-job-activated -> Logs):")
    print("expect either a python traceback or a 'resend 4xx' line naming the cause.")


if __name__ == "__main__":
    main()
