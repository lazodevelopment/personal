#!/usr/bin/env python3
"""
seed_roven.py — one-time launch seed for the Roven Firebase project
====================================================================
Creates the three founding employer accounts (JC's wedding brands), grants
custom claims, and posts the three seed jobs as ACTIVE. Everything here goes
through the Admin SDK because the security rules (correctly) forbid all of it
from the client.

USAGE
  pip install firebase-admin
  # Service account key: Firebase console -> Project settings ->
  # Service accounts -> Generate new private key
  python seed_roven.py --key serviceAccount.json --email rovenhr@gmail.com

  --email is the Auth account that will own/operate the employer accounts
  (it must exist in Firebase Auth already — sign up once through the app or
  create the user in the console Authentication tab first).

WHAT IT DOES
  1. employers/{id} x3      — Atavia, 52 Eighty, 83 Weddings, marked verified
                              (manual founder verification; Middesk API later),
                              pricingTier "founding", empty billing stub
  2. custom claims          — identityVerified + admin on your account, plus
                              employerId/employerRole owner on the FIRST brand.
                              (One account can hold one employerId claim in the
                              v1 model — see MULTI-BRAND NOTE below.)
  3. jobs/{id} x3           — the photographer / videographer / editor listings,
                              status "active", one per brand
  4. Prints doc IDs for FlutterFlow test bindings.

MULTI-BRAND NOTE
  The claims model is one employerId per account. For launch that's fine: this
  script assigns your login to Atavia, and the OTHER two brands' jobs are still
  created and publicly browsable/applyable — you just manage their pipelines
  via Admin SDK / the admin site until multi-employer membership (an
  employerIds array claim + rules update) lands. Simplest practical option if
  you want console access to all three pipelines now: create three logins
  (info@ of each brand) and re-run with --email per brand after editing
  ASSIGN_BRAND below.

FILL IN THE PAY FIELDS BELOW BEFORE RUNNING (salary markup matters for the
SEO pages and Google for Jobs).
"""

import argparse
from datetime import datetime, timezone

import firebase_admin
from firebase_admin import auth, credentials, firestore

# ---------------------------------------------------------------------------
# EDIT ME — pay ranges per day/gallery/hour before running
# ---------------------------------------------------------------------------
PAY = {
    # Derived from the standing Danbren contractor rate of $50/hr:
    # a wedding day runs 8-10 hours -> $400-$500/day for shooters.
    "photographer": {"salaryMin": 400, "salaryMax": 500, "salaryUnit": "DAY"},     # per wedding day
    "videographer": {"salaryMin": 400, "salaryMax": 500, "salaryUnit": "DAY"},     # per wedding day
    "editor":       {"salaryMin": 35,  "salaryMax": 50,  "salaryUnit": "HOUR"},    # hourly
}
ASSIGN_BRAND = "atavia"   # which brand this --email account operates: atavia | fiftytwo80 | eightythree

EMPLOYERS = {
    "atavia": {
        "name": "Atavia Weddings",
        "metro": "Phoenix",
        "industry": "Wedding media",
    },
    "fiftytwo80": {
        "name": "52 Eighty Weddings",
        "metro": "Phoenix",
        "industry": "Wedding media",
    },
    "eightythree": {
        "name": "83 Weddings",
        "metro": "Phoenix",
        "industry": "Wedding media",
    },
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
    ap.add_argument("--email", required=True, help="Auth account to operate ASSIGN_BRAND")
    args = ap.parse_args()

    firebase_admin.initialize_app(credentials.Certificate(args.key))
    db = firestore.client()
    now = datetime.now(timezone.utc)

    # ---- 1. employers ----
    emp_ids = {}
    for key, e in EMPLOYERS.items():
        ref = db.collection("employers").document()
        ref.set({
            **e,
            "verified": True,
            "middeskVerification": {
                "status": "verified",
                "method": "manual_founder",     # replace with Middesk API result later
                "verifiedAt": now,
            },
            "pricingTier": "founding",
            "billing": {},
            "createdAt": now,
        })
        emp_ids[key] = ref.id
        print(f"employer  {e['name']:24s} -> {ref.id}")

    # ---- 2. claims on the operating account ----
    user = auth.get_user_by_email(args.email)
    auth.set_custom_user_claims(user.uid, {
        "identityVerified": True,
        "admin": True,
        "employerId": emp_ids[ASSIGN_BRAND],
        "employerRole": "owner",
    })
    print(f"\nclaims set on {args.email} (uid {user.uid}):")
    print(f"  identityVerified=True, admin=True, employer={EMPLOYERS[ASSIGN_BRAND]['name']} (owner)")
    print("  NOTE: claims apply on next sign-in — sign out/in in the app to pick them up.")

    # ---- 3. jobs (active — founder-confirmed open roles) ----
    print()
    for j in JOBS:
        brand = j.pop("brand")
        ref = db.collection("jobs").document()
        ref.set({
            **j,
            "employerId": emp_ids[brand],
            "status": "active",
            "confirmedOpen": True,
            "createdAt": now,
        })
        print(f"job       {j['title']:32s} ({EMPLOYERS[brand]['name']}) -> {ref.id}")

    print("\nSeed complete. Next:")
    print("  - Sign out/in on your app account to activate claims")
    print("  - Bind FlutterFlow job list/detail widgets against these docs")
    print("  - python generate_roven_pages.py --key", args.key, "--site ./roven-site  (SEO pages now have inventory)")

if __name__ == "__main__":
    main()
