#!/usr/bin/env python3
"""
seed_roven_finish.py — completes the interrupted seed run.
The three employer docs already exist (created 2026-07-27); this script only
does the two steps that didn't run: custom claims + the three job postings.

PREREQ: rovenhr@gmail.com must exist in Firebase Auth
        (console -> Authentication -> Users -> Add user)

USAGE:  python seed_roven_finish.py --key serviceAccount.json --email rovenhr@gmail.com
Safe to re-run: it checks for existing jobs by title+employer before creating.
"""

import argparse
from datetime import datetime, timezone

import firebase_admin
from firebase_admin import auth, credentials, firestore

# Employer doc IDs from the original seed run (already in Firestore)
EMP = {
    "atavia":      {"id": "j2NJif4a2iUziTueFGZu", "name": "Atavia Weddings"},
    "fiftytwo80":  {"id": "nfhy2s1KYpyzJUNUz0J8", "name": "52 Eighty Weddings"},
    "eightythree": {"id": "rS9CUPVShL52VYYRFNU6", "name": "83 Weddings"},
}
ASSIGN_BRAND = "atavia"

PAY = {
    "photographer": {"salaryMin": 400, "salaryMax": 500, "salaryUnit": "DAY"},
    "videographer": {"salaryMin": 400, "salaryMax": 500, "salaryUnit": "DAY"},
    "editor":       {"salaryMin": 35,  "salaryMax": 50,  "salaryUnit": "HOUR"},
}

JOBS = [
    {
        "brand": "atavia",
        "title": "Wedding Photographer",
        "employmentType": "CONTRACTOR",
        "locationCity": "Phoenix", "locationState": "AZ",
        **PAY["photographer"],
        "description": (
            "We're a Phoenix wedding media company booking a full season, and we need a "
            "photographer who can own a wedding day from getting-ready coverage through the last dance exit.\n"
            "What the work looks like: You'll shoot weddings as the lead or second photographer depending on "
            "the booking — candid-forward documentary coverage with clean, intentional portrait work. Timelines "
            "are planned before you arrive; you'll get a shot brief, venue notes, and a coordinator contact for "
            "every date. Deliver RAW files within 48 hours of the event; editing is handled in-house unless you "
            "want editing work too.\n"
            "What we're looking for: A portfolio of real wedding work (full galleries beat highlight reels). "
            "Comfortable directing family formals quickly and kindly under time pressure. Own professional "
            "full-frame kit with backup body and lighting for dark receptions. Reliable weekend availability "
            "during wedding season. Calm under the specific chaos only a wedding can produce.\n"
            "What you get from us: Consistent bookings through the season, not one-off gigs. Clear rate per "
            "wedding day, paid on a defined schedule — no chasing invoices. Timelines, shot lists, and "
            "coordinator support handled before you arrive.\n"
            "We respond to every application on Roven — usually within two business days. If you apply, you "
            "will hear back. That's not a slogan; it's on our public record."
        ),
    },
    {
        "brand": "fiftytwo80",
        "title": "Wedding Videographer",
        "employmentType": "CONTRACTOR",
        "locationCity": "Phoenix", "locationState": "AZ",
        **PAY["videographer"],
        "description": (
            "We produce wedding films for couples across the Phoenix metro, and we're adding a videographer "
            "for the season — someone who can capture a wedding day cinematically without turning it into a "
            "production the couple has to perform for.\n"
            "What the work looks like: Solo or two-shooter coverage depending on the package: ceremony "
            "multi-cam, clean audio capture (officiant, vows, toasts — lavs and recorders, every time), "
            "reception coverage, and steady gimbal work for couple sessions. You shoot; our editors cut. "
            "Footage and audio delivered within 48 hours via our transfer workflow.\n"
            "What we're looking for: A reel and at least a few full wedding films you shot. Disciplined audio "
            "habits — a beautiful film with unusable vow audio is a failed film. Own mirrorless/cinema kit "
            "with gimbal, audio package, and low-light lenses. Weekend availability through the season. You "
            "know when to be invisible.\n"
            "What you get from us: A steady season of booked dates with pre-built timelines. Defined day rate, "
            "paid on schedule. No client management — we handle the couple, you handle the craft.\n"
            "Every application gets an answer. Our response rate is public on Roven — check it."
        ),
    },
    {
        "brand": "eightythree",
        "title": "Wedding Photo & Video Editor",
        "employmentType": "CONTRACTOR",
        "locationCity": "Phoenix", "locationState": "AZ",
        "remote": True,
        **PAY["editor"],
        "description": (
            "We're bringing on an editor to carry post-production across our wedding brands — photo galleries, "
            "highlight films, or both if you're genuinely strong at both (most people are one; be honest about "
            "which you are).\n"
            "Photo side: Full-gallery culls and edits in Lightroom to an established brand style — "
            "true-to-color, warm, consistent across venues and lighting conditions. You'll work from anchor "
            "edits per venue; turnaround targets are per-gallery with a defined schedule, not \"whenever.\"\n"
            "Video side: Highlight films (3–6 min) and ceremony/toast edits in Premiere or Resolve from "
            "organized multi-cam footage with synced audio. Story sense matters more than effects.\n"
            "What we're looking for: Portfolio of delivered wedding work. Fast, consistent, and honest about "
            "turnaround capacity per week. Comfortable working to an existing style guide. Organized file "
            "hygiene — you'll touch a lot of terabytes.\n"
            "What you get from us: Recurring volume through the season, not a one-off project. Defined "
            "per-deliverable rates and a payment schedule in writing. Organized ingests: synced audio, culled "
            "selects, labeled timelines.\n"
            "Apply through Roven and you'll get an actual answer — our response time is tracked and published."
        ),
    },
]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True)
    ap.add_argument("--email", required=True)
    args = ap.parse_args()

    firebase_admin.initialize_app(credentials.Certificate(args.key))
    db = firestore.client()
    now = datetime.now(timezone.utc)

    # ---- sanity: employers exist ----
    for b, e in EMP.items():
        snap = db.collection("employers").document(e["id"]).get()
        if not snap.exists:
            raise SystemExit(f"ERROR: employer doc {e['id']} ({e['name']}) not found — IDs may not match.")
    print("employers verified: all 3 present")

    # ---- claims ----
    user = auth.get_user_by_email(args.email)
    auth.set_custom_user_claims(user.uid, {
        "identityVerified": True,
        "admin": True,
        "employerId": EMP[ASSIGN_BRAND]["id"],
        "employerRole": "owner",
    })
    print(f"claims set on {args.email} (uid {user.uid}) — operating {EMP[ASSIGN_BRAND]['name']} as owner")
    print("  NOTE: claims apply on next sign-in.")

    # ---- jobs (idempotent: skip if same title already exists for that employer) ----
    print()
    for j in JOBS:
        brand = j.pop("brand")
        emp_id = EMP[brand]["id"]
        existing = list(db.collection("jobs")
                        .where("employerId", "==", emp_id)
                        .where("title", "==", j["title"]).limit(1).stream())
        if existing:
            print(f"job       {j['title']:32s} already exists -> {existing[0].id}  (skipped)")
            continue
        ref = db.collection("jobs").document()
        ref.set({
            **j,
            "employerId": emp_id,
            "status": "active",
            "confirmedOpen": True,
            "createdAt": now,
        })
        print(f"job       {j['title']:32s} ({EMP[brand]['name']}) -> {ref.id}")

    print("\nSeed complete. Next:")
    print("  python generate_roven_pages.py --key", args.key, "--site C:\\Users\\kurvh\\roven-site")

if __name__ == "__main__":
    main()
