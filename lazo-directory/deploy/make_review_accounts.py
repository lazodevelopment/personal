r"""Provision the App Store review demo account.  JC-LAZO-REVIEW-0917-002

ONE LOGIN, BOTH SIDES. The earlier version of this script created two accounts,
because users/{uid}.role is a single write-once value and it decides which home
the app routes to. That was right about routing and wrong about access.

firestore.rules grants vendor-side permission through vendorAccess():

    function vendorAccess(vendorId) {
      return signedIn()
        && (get(.../vendors/$(vendorId)).data.claimedBy == request.auth.uid
            || (get(.../users/$(uid)).data.vendorId == vendorId
                && ....vendorRole == 'manager'));
    }

That checks claimedBy. It never looks at role. So one account can hold
role: 'couple' - which is all the FlutterFlow LazoRouter widget reads, and which
sends it to CoupleHome on login - while ALSO being claimedBy on a vendor, which
gives it full vendor-side read and write. role decides where you land; claimedBy
decides what you may touch.

The app reaches the other side with a custom action calling
context.goNamed('VendorHome') - the same page name LazoRouter already uses. No
firestore.rules change, no role flip, nothing write-once is touched.

CAVEAT worth keeping in mind: if the VendorHome page gains an On Page Load action
that re-reads role and bounces non-vendors, that guard will fight this. The entry
router does not do it today.

WHAT THIS CREATES

  auth  demo@meetlazo.com            the single reviewer login
  doc   users/{uid}                  role: 'couple', vendorId -> demo vendor
  doc   couples/{uid}                wedding date, June brief
  doc   vendors/demo-vendor-appreview  claimedBy -> the same uid
  doc   inquiries/{id}               that account on BOTH sides of one thread

  A second, vendor-only account is still created as a fallback, so a reviewer
  always has a way in if the in-app toggle misbehaves. Delete it once the button
  is confirmed.

WHY THE DEMO VENDOR IS INVISIBLE TO THE PUBLIC SITE

generate/build.py loads vendors with

    db.collection("vendors").where("metroId", "==", mid)

for the metros in config/metros.py only. metroId 'demo' is not one of them, so
this record is never queried: no public page, no sitemap entry, and - unlike
delisted:true - no _gone.json tombstone and no effect on the delist-receipt gate
that deploy_site.py asserts against Firestore.

WHY THE SEEDED INQUIRY DOES NOT SPAM ANYONE

  outreachOnInquiry returns early when the vendor has claimedBy set, so no
  recruitment email fires. The vendor record carries no phone, so the SMS path
  has nothing to send to. demo: true matches the wall used by
  functions-dashboard/demo.js.

Run:
    python deploy\make_review_accounts.py              # create or update
    python deploy\make_review_accounts.py --show       # print credentials again
    python deploy\make_review_accounts.py --delete     # remove everything

Idempotent: re-running updates in place and re-uses the existing passwords
recorded in ~/secrets/lazo-review-accounts.json. That file holds real passwords, so
it lives beside the Firebase key rather than in this Dropbox-synced tree.
"""
import argparse
import json
import os
import secrets
import string
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

import firebase_admin
from firebase_admin import auth as fb_auth, credentials, firestore

PROJECT = "lazo-513ec"
# NOT inside the repo: this tree is Dropbox-synced, so a password file here would
# sync off this machine. .dbxignore is Dropbox-managed and read-only, so instead we
# keep it beside the Firebase service-account key, which is already the established
# home for secrets in this setup (GOOGLE_APPLICATION_CREDENTIALS points there).
STORE = Path.home() / "secrets" / "lazo-review-accounts.json"

MAIN_EMAIL = "demo@meetlazo.com"          # the one login the reviewer uses
FALLBACK_EMAIL = "demo-vendor@meetlazo.com"  # vendor-only backup, delete once confirmed
DEMO_VENDOR_ID = "demo-vendor-appreview"


def strong_password() -> str:
    """Readable but strong: App Store reviewers type these by hand."""
    words = ["Harbor", "Lantern", "Meadow", "Compass", "Willow", "Anchor", "Cedar", "Ember"]
    return (secrets.choice(words) + secrets.choice(words)
            + str(secrets.randbelow(90) + 10)
            + secrets.choice("!@#$%&*"))


def init():
    path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not path or not Path(path).is_file():
        sys.exit("GOOGLE_APPLICATION_CREDENTIALS is not set or the file is missing")
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(path), {"projectId": PROJECT})
    return firestore.client()


def load_store() -> dict:
    try:
        return json.loads(STORE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_store(d: dict):
    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps(d, indent=2), encoding="utf-8")


def ensure_user(email: str, name: str, store: dict) -> tuple:
    """Create the auth user, or reuse it and reset to the recorded password."""
    pw = store.get(email, {}).get("password") or strong_password()
    try:
        u = fb_auth.get_user_by_email(email)
        fb_auth.update_user(u.uid, password=pw, display_name=name, email_verified=True)
        action = "updated"
    except fb_auth.UserNotFoundError:
        u = fb_auth.create_user(email=email, password=pw, display_name=name,
                                email_verified=True)
        action = "created"
    store[email] = {"uid": u.uid, "password": pw}
    return u.uid, pw, action


def seed(db, uid, fallback_uid):
    """One account on both sides, plus a vendor-only fallback."""
    now = firestore.SERVER_TIMESTAMP
    wedding = datetime.now(timezone.utc) + timedelta(days=210)

    # role 'couple' is what LazoRouter reads, so login lands on CoupleHome.
    # vendorId is set too - the vendor dashboard resolves the business from it,
    # and vendorAccess() in the rules grants write access via claimedBy below.
    db.collection("users").document(uid).set({
        "uid": uid, "email": MAIN_EMAIL, "display_name": "Demo Account",
        "role": "couple", "vendorId": DEMO_VENDOR_ID,
        "created_time": now, "tosAcceptedAt": now,
    }, merge=True)

    db.collection("users").document(fallback_uid).set({
        "uid": fallback_uid, "email": FALLBACK_EMAIL, "display_name": "Demo Studio",
        "role": "vendor", "vendorId": DEMO_VENDOR_ID,
        "created_time": now, "tosAcceptedAt": now,
    }, merge=True)

    # Not an empty shell - an empty account is a real Guideline 2.1 rejection risk.
    # These are the fields the couple dashboard checks for its "finish the
    # one-minute setup" prompt. Seeding weddingDate alone left a reviewer looking
    # at a half-onboarded account: budget "Not set yet", "Tell June your city",
    # "Still missing: your names, the city, a rough budget". Field names taken
    # from the live couples collection.
    db.collection("couples").document(uid).set({
        "names": "Alex & Sam",
        "metroId": "phoenix",
        "budgetTotal": 32000,
        "weddingDate": wedding,
        "createdAt": now,
        "updatedAt": now,
        "setupDoneAt": now,      # clears the setup banner
        "tourCompleted": True,   # clears the tour prompt
        "tourDoneAt": now,
        "hellosOk": True,
        "juneBrief": ("Demo account for store review. Wedding in about seven months "
                      "in Phoenix, 120 guests, budget around $32,000."),
        "celebratedBookings": [],
    }, merge=True)

    # claimedBy is the MAIN uid: that single field is what gives the one login
    # vendor-side access, independent of its 'couple' role.
    db.collection("vendors").document(DEMO_VENDOR_ID).set({
        "name": "Demo Studio Photography",
        "categories": ["wedding-photographers", "wedding-videographers"],
        "metroId": "demo",
        "address": "Phoenix, Arizona",
        "claimStatus": "claimed",
        "claimedBy": uid,
        "verified": True,
        "demo": True,
        "source": "app-review",
        "seededAt": now,
    }, merge=True)

    # The same account is the couple on this thread AND the vendor receiving it,
    # so the toggle demonstrably shows two views of one conversation.
    inq = db.collection("inquiries").document("demo-appreview-inquiry")
    inq.set({
        "coupleUid": uid,
        "coupleName": "Demo Account",
        "coupleEmail": MAIN_EMAIL,
        "vendorId": DEMO_VENDOR_ID,
        "vendorName": "Demo Studio Photography",
        "message": ("Hi! We're getting married next spring in Phoenix and love your "
                    "work. Are you available, and what do your packages include?"),
        "status": "new",
        "demo": True,
        "offPlatform": False,
        "createdAt": now,
        "structuredIntent": {"guests": 120, "budget": 32000, "metro": "phoenix"},
    }, merge=True)
    inq.collection("messages").document("m1").set({
        "senderRole": "couple",
        "text": ("Hi! We're getting married next spring in Phoenix and love your work. "
                 "Are you available, and what do your packages include?"),
        "at": now, "demo": True,
    }, merge=True)


def delete(db):
    for email in (MAIN_EMAIL, FALLBACK_EMAIL):
        try:
            u = fb_auth.get_user_by_email(email)
            db.collection("users").document(u.uid).delete()
            db.collection("couples").document(u.uid).delete()
            fb_auth.delete_user(u.uid)
            print(f"  deleted {email}")
        except fb_auth.UserNotFoundError:
            print(f"  {email} not present")
    inq = db.collection("inquiries").document("demo-appreview-inquiry")
    for m in inq.collection("messages").stream():
        m.reference.delete()
    inq.delete()
    db.collection("vendors").document(DEMO_VENDOR_ID).delete()
    print("  deleted demo vendor and inquiry")
    if STORE.exists():
        STORE.unlink()
        print("  removed stored credentials")


def notes(store):
    m = store.get(MAIN_EMAIL, {})
    f = store.get(FALLBACK_EMAIL, {})
    return f"""Lazo serves two audiences - couples planning a wedding, and the wedding
businesses they hire. This single demo account can see both.

  Email:    {MAIN_EMAIL}
  Password: {m.get('password','?')}

1. Sign in. You will land on the couple dashboard: wedding countdown, vendor
   search, and a message thread with "Demo Studio Photography".
2. To see the business side, use "Switch to vendor view" on the Account screen.
   The same account owns that vendor, so you will see the same conversation from
   the business's point of view, plus the vendor dashboard and profile tools.
3. For the full booking flow - proposal, contract, invoice - start the practice
   lead from the prompt on the vendor dashboard. It is a built-in guided demo.

This is a demo account created for review. It contains no real customer data,
and the demo business is not listed publicly.

If the vendor toggle does not appear in this build, this vendor-only login
reaches the same dashboard directly:
  Email:    {FALLBACK_EMAIL}
  Password: {f.get('password','?')}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true", help="print stored credentials and notes")
    ap.add_argument("--delete", action="store_true", help="remove the accounts and demo data")
    a = ap.parse_args()

    db = init()
    store = load_store()

    if a.delete:
        delete(db)
        return
    if a.show:
        if not store:
            sys.exit("no stored credentials - run without --show first")
        print(notes(store))
        return

    uid, _, act = ensure_user(MAIN_EMAIL, "Demo Account", store)
    fuid, _, fact = ensure_user(FALLBACK_EMAIL, "Demo Studio", store)
    save_store(store)
    seed(db, uid, fuid)

    print(f"  main      {MAIN_EMAIL}  {act}  uid={uid}")
    print(f"  fallback  {FALLBACK_EMAIL}  {fact}  uid={fuid}")
    print(f"  seeded    users, couples/, vendors/{DEMO_VENDOR_ID} (claimedBy=main), one inquiry")
    print(f"\n  credentials stored in {STORE}\n")
    print("=" * 68)
    print(notes(store))
    print("=" * 68)


if __name__ == "__main__":
    main()
