# =============================================================================
# ATAVIA WEDDINGS — AUTOMATED BOOKING CLOUD FUNCTIONS  (v10 · 2026-09-02 — Zoho Payments replaces Stax)
# Project: atavia-c29cd · Python 3.12 runtime · Region: us-central1
# =============================================================================
# Flow:
#   /book page POST -> zoho_session   (Zoho customer + payment-method session;
#                                        the page then opens the Zoho widget
#                                        in "add" mode and gets a payment_method_id)
#   /book page POST -> book_submit
#     -> Firestore bookings/{id}  (status: pending_signature)
#     -> generate contract PDF (ReportLab, SignWell text tags)
#     -> SignWell send for e-signature
#   SignWell webhook (document completed) -> signwell_webhook
#     -> archive signed PDF to Storage
#     -> Zoho: charge the card saved at booking (deposit $500 or PIF total)
#        -> status: confirmed · welcome email (Resend) · notify JC
#     -> fallback (no card / declined): Zoho payment link emailed
#        -> status: awaiting_payment
#   Zoho webhook (payment_link.paid) -> zoho_webhook
#     -> status: confirmed (no card on file; balance collected by link)
#   charge_balances (daily scheduler, America/Phoenix)
#     -> standard-plan bookings past balance_due_at -> charge card on file
#   gratuity (HTTPS) -> tokenized post-event gratuity charge to card on file
#
# Secrets (set before deploy):
#   firebase functions:secrets:set SIGNWELL_API_KEY
#   firebase functions:secrets:set ZOHO_CLIENT_ID        (api-console.zoho.com, client type ORG)
#   firebase functions:secrets:set ZOHO_CLIENT_SECRET
#   firebase functions:secrets:set ZOHO_REFRESH_TOKEN    (one-time OAuth dance, access_type=offline)
#   firebase functions:secrets:set RESEND_API_KEY
#   firebase functions:secrets:set PROMO_ADMIN_KEY   (any long random string; used to issue codes)
#   firebase functions:secrets:set GRATUITY_SECRET     (any long random string)
# =============================================================================

import hashlib
import hmac
import json
import re
import sys
import os
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "contract"))
sys.path.insert(0, os.path.dirname(__file__))

from firebase_functions import https_fn, scheduler_fn, options
from firebase_functions.params import SecretParam
import firebase_admin
from firebase_admin import firestore, storage

from atavia_contract_generator import (generate_contract, compute_pricing,
                                       PACKAGES, RULES)
from lib.signwell import SignWell
from lib.zoho import Zoho
from lib import emails
from lib.questionnaire_schema import ALL_FIELD_IDS, SUMMARY_LAYOUT

firebase_admin.initialize_app()

# ----------------------------------------------------------------- config ---
SIGNWELL_API_KEY = SecretParam("SIGNWELL_API_KEY")
ZOHO_CLIENT_ID     = SecretParam("ZOHO_CLIENT_ID")
ZOHO_CLIENT_SECRET = SecretParam("ZOHO_CLIENT_SECRET")
ZOHO_REFRESH_TOKEN = SecretParam("ZOHO_REFRESH_TOKEN")
ZOHO_SECRETS = [ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_REFRESH_TOKEN]
RESEND_API_KEY   = SecretParam("RESEND_API_KEY")
GRATUITY_SECRET  = SecretParam("GRATUITY_SECRET")
PROMO_ADMIN_KEY  = SecretParam("PROMO_ADMIN_KEY")

TEST_MODE       = False  # PRODUCTION
ZOHO_ACCOUNT_ID  = "937366965"                 # Danbren Media LLC (Zoho Payments)
STATEMENT_DESCRIPTOR = "ATAVIA WEDDINGS"       # <=22 chars; what the couple sees on their statement
OWNER_EMAIL     = "info@ataviaweddings.com"   # JC notification target
ALLOWED_ORIGINS = ["https://ataviaweddings.com", "https://www.ataviaweddings.com"]
ADMIN_ORIGINS   = ["https://admin.ataviaweddings.com", "https://atavia-admin.pages.dev"]
ADMIN_EMAILS    = ["info@ataviaweddings.com"]       # who may call admin_action / see the dashboard
if TEST_MODE:
    ALLOWED_ORIGINS.append("http://localhost:8000")
REGION = options.SupportedRegion.US_CENTRAL1
# Newer Firebase projects provision the default bucket as .firebasestorage.app;
# older ones as .appspot.com. Try in order.
BUCKET_CANDIDATES = ["atavia-c29cd.firebasestorage.app",
                     "atavia-c29cd.appspot.com"]

REQUIRED_FIELDS = [
    "package_id", "payment_option", "client_names", "email", "phone",
    "mailing_address", "city_state_zip", "governing_state", "event_date",
    "ceremony_venue", "agree_terms",
]
OPTIONAL_FIELDS = ["guest_count", "reception_venue", "start_time", "end_time"]


def _compute_balance_due(event_dt, now):
    """Balance is due 14 business days (Mon-Fri) after booking/signing. If the
    Event is sooner than that, the balance falls due the day before the Event
    (never after it), and never earlier than now."""
    from datetime import timezone as _tz
    due = now
    added = 0
    while added < RULES["balance_due_days_from_booking"]:
        due = due + timedelta(days=1)
        if due.weekday() < 5:
            added += 1
    event_utc = event_dt.replace(tzinfo=_tz.utc)
    return due if due < event_utc else max(now, event_utc - timedelta(days=1))


def _cors(req):
    origin = req.headers.get("Origin", "")
    allow = origin if origin in ALLOWED_ORIGINS + ADMIN_ORIGINS else ALLOWED_ORIGINS[0]
    return {
        "Access-Control-Allow-Origin": allow,
        "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Max-Age": "3600",
    }


def _json(req, data, status=200):
    return https_fn.Response(json.dumps(data), status=status,
                             headers={**_cors(req),
                                      "Content-Type": "application/json"})


def _archive_signed_pdf(pdf_bytes, booking_id):
    """Upload signed contract, trying bucket candidates in order."""
    last_err = None
    for bname in BUCKET_CANDIDATES:
        try:
            blob = storage.bucket(bname).blob(
                f"contracts/{booking_id}-signed.pdf")
            blob.upload_from_string(pdf_bytes,
                                    content_type="application/pdf")
            return f"gs://{bname}/{blob.name}"
        except Exception as e:
            last_err = e
    raise last_err


def _q_link(booking_id, secret):
    return ("https://ataviaweddings.com/questionnaire"
            f"?b={booking_id}&t={_gratuity_token(booking_id, secret)}")


def _gratuity_token(booking_id, secret):
    return hmac.new(secret.encode(), booking_id.encode(),
                    hashlib.sha256).hexdigest()[:32]


# -- visitor sessions (written by /assets/js/atv-track.js; see admin /visitors) --
_SID_RE = re.compile(r"^[a-f0-9]{24}$")

def _link_session(db, sid, name, email, booking_id=None):
    """Attach a couple's name to the anonymous visitor session so the admin
    map shows who they are. Non-fatal: tracking must never block a booking."""
    try:
        sid = str(sid or "")
        if not _SID_RE.match(sid):
            return
        patch = {"lead_name": name, "lead_email": email,
                 "lead_at": firestore.SERVER_TIMESTAMP}
        if booking_id:
            patch["booking_id"] = booking_id
        db.collection("sessions").document(sid).set(patch, merge=True)
    except Exception as e:
        print(f"session link failed (non-fatal): {e}")


def _purge_old_sessions(db, days=90):
    """Delete visitor sessions (and their hits) not seen in `days` that never
    became a lead or booking. Runs daily from charge_balances."""
    from google.cloud.firestore_v1.base_query import FieldFilter
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    deleted = 0
    try:
        while True:
            docs = list(db.collection("sessions")
                          .where(filter=FieldFilter("last_seen", "<", cutoff))
                          .order_by("last_seen").limit(200).stream())
            if not docs:
                break
            batch = db.batch(); ops = 0; progressed = False
            for snap in docs:
                d = snap.to_dict() or {}
                if d.get("lead_name") or d.get("booking_id"):
                    continue
                for hit in snap.reference.collection("hits").stream():
                    batch.delete(hit.reference); ops += 1
                    if ops >= 400:
                        batch.commit(); batch = db.batch(); ops = 0
                batch.delete(snap.reference); ops += 1; deleted += 1
                progressed = True
                if ops >= 400:
                    batch.commit(); batch = db.batch(); ops = 0
            if ops:
                batch.commit()
            if not progressed:
                break  # remaining page is all keepers
    except Exception as e:
        print(f"session purge failed (non-fatal): {e}")
    print(f"purge_old_sessions: deleted {deleted} sessions older than {days}d")



def _zoho():
    return Zoho(ZOHO_ACCOUNT_ID, ZOHO_CLIENT_ID.value,
                ZOHO_CLIENT_SECRET.value, ZOHO_REFRESH_TOKEN.value)


def _pm_display(pm):
    """(brand, last4) from a Zoho payment_method dict, for owner emails."""
    card = (pm or {}).get("card") or {}
    return (str(card.get("brand") or "card")[:20],
            str(card.get("last_four_digits") or "")[:4])


# =========================================================== zoho_session ===
@https_fn.on_request(region=REGION, secrets=ZOHO_SECRETS)
def zoho_session(req: https_fn.Request) -> https_fn.Response:
    """Step 0 of /book: the Zoho widget needs a customer_id and a
    payment_method_session_id BEFORE it can tokenize a card, so the page
    calls this first, opens the widget, then POSTs the booking with the
    resulting payment_method_id. Nothing is charged here."""
    if req.method == "OPTIONS":
        return https_fn.Response("", status=204, headers=_cors(req))
    if req.method != "POST":
        return _json(req, {"error": "POST only"}, 405)
    data = req.get_json(silent=True) or {}
    name = str(data.get("client_names") or "").strip()[:100]
    email = str(data.get("email") or "").strip()
    phone = re.sub(r"[^\d+]", "", str(data.get("phone") or ""))[:20]
    if not name or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return _json(req, {"error": "name and a valid email are required"}, 400)
    try:
        z = _zoho()
        cust = z.create_customer(name, email, phone,
                                 meta={"source": "ataviaweddings.com"})
        sess = z.create_pm_session(cust["customer_id"],
                                   description="Card on file for booking")
    except Exception as e:
        print(f"zoho_session failed: {e}")
        return _json(req, {"error": "payment setup unavailable"}, 502)

    # -- record the lead. If the couple closes the card window, this is the
    #    only trace of them; _chase_leads() emails a "finish your booking"
    #    nudge and book_submit marks it converted on success. ---------------
    try:
        pkg_id = str(data.get("package_id") or "")
        pkg = PACKAGES.get(pkg_id) or {}
        ev_raw = str(data.get("event_date") or "")
        try:
            ev_disp = datetime.strptime(ev_raw, "%Y-%m-%d").strftime("%B %d, %Y")
        except ValueError:
            ev_disp = ""
        firestore.client().collection("leads").add({
            "status": "card_pending",
            "created_at": firestore.SERVER_TIMESTAMP,
            "client_names": name, "email": email, "phone": phone,
            "package_id": pkg_id, "package_name": pkg.get("name", ""),
            "payment_option": str(data.get("payment_option") or "")[:10],
            "event_date_raw": ev_raw[:10], "event_date_display": ev_disp,
            "zoho_customer_id": cust["customer_id"],
            "attr_venue": str(data.get("attr_venue") or "")[:200],
            "client_ip": req.headers.get("X-Forwarded-For", req.remote_addr),
            "sid": str(data.get("sid") or "")[:32],
        })
    except Exception as e:
        print(f"lead record failed (non-fatal): {e}")
    _link_session(firestore.client(), data.get("sid"), name, email)

    return _json(req, {"customer_id": cust["customer_id"],
                       "payment_method_session_id":
                           sess["payment_method_session_id"]})


# ============================================================ book_submit ===
@https_fn.on_request(region=REGION, secrets=[SIGNWELL_API_KEY, *ZOHO_SECRETS],
                     memory=options.MemoryOption.MB_512)
def book_submit(req: https_fn.Request) -> https_fn.Response:
    if req.method == "OPTIONS":
        return https_fn.Response("", status=204, headers=_cors(req))
    if req.method != "POST":
        return _json(req, {"error": "POST only"}, 405)

    try:
        data = req.get_json(silent=True) or {}
    except Exception:
        return _json(req, {"error": "invalid JSON"}, 400)

    # -- validate -------------------------------------------------------------
    missing = [f for f in REQUIRED_FIELDS if not data.get(f)]
    if missing:
        return _json(req, {"error": "missing fields", "fields": missing}, 400)
    if data["package_id"] not in PACKAGES:
        return _json(req, {"error": "unknown package"}, 400)
    if data["payment_option"] not in ("standard", "pif"):
        return _json(req, {"error": "invalid payment option"}, 400)
    if data.get("agree_terms") is not True:
        return _json(req, {"error": "terms must be accepted"}, 400)
    try:
        event_dt = datetime.strptime(data["event_date"], "%Y-%m-%d")
        if event_dt.date() <= datetime.now().date():
            return _json(req, {"error": "event date must be in the future"}, 400)
    except ValueError:
        return _json(req, {"error": "event_date must be YYYY-MM-DD"}, 400)

    # -- add-ons (server-side pricing; the client-side total is never trusted) --
    second_shooter = data.get("second_shooter", False)
    if not isinstance(second_shooter, bool):
        return _json(req, {"error": "second_shooter must be true/false"}, 400)
    try:
        extra_hours = int(data.get("extra_hours") or 0)
    except (TypeError, ValueError):
        return _json(req, {"error": "extra_hours must be a whole number"}, 400)
    if not (0 <= extra_hours <= RULES["max_extra_hours"]):
        return _json(req, {"error": f"extra_hours must be 0-"
                                    f"{RULES['max_extra_hours']}"}, 400)

    # -- card on file (tokenized client-side by the Zoho widget; the PAN never
    #    reaches our servers, which keeps us in PCI SAQ-A). All three ids must
    #    be present and the session must really hold that method for that
    #    customer, or we drop it and fall back to the payment-link flow at
    #    signature. ---------------------------------------------------------
    pm_id = str(data.get("zoho_payment_method_id") or "").strip()
    cust_id = str(data.get("zoho_customer_id") or "").strip()
    sess_id = str(data.get("zoho_pm_session_id") or "").strip()
    card_brand = str(data.get("card_brand") or "")[:20]
    card_last4 = re.sub(r"\D", "", str(data.get("card_last4") or ""))[:4]
    if pm_id and cust_id and sess_id:
        try:
            z = _zoho()
            sess = z.get_pm_session(sess_id)
            saved = (sess.get("payment_method") or {}).get("payment_method_id")
            if (str(sess.get("customer_id")) != cust_id or saved != pm_id):
                print(f"REJECTED payment method {pm_id}: session {sess_id} "
                      f"holds {saved} for customer {sess.get('customer_id')}")
                pm_id = cust_id = ""
            elif not (card_brand and card_last4):
                card_brand, card_last4 = _pm_display(
                    z.get_payment_method(pm_id))
        except Exception as e:
            # Verification unavailable is not fatal: a bad token simply fails
            # at charge time and degrades to the payment-link path.
            print(f"payment method verification unavailable: {e}")
    else:
        pm_id = cust_id = ""

    pkg = PACKAGES[data["package_id"]]
    now = datetime.now(timezone.utc)
    db = firestore.client()
    booking_ref = db.collection("bookings").document()
    booking_id = booking_ref.id

    # -- a card was saved: the zoho_session lead is now a booking -------------
    if cust_id:
        try:
            from google.cloud.firestore_v1.base_query import FieldFilter as _FF
            for lead in (db.collection("leads")
                           .where(filter=_FF("zoho_customer_id", "==", cust_id))
                           .limit(1).get()):
                lead.reference.update({"status": "converted",
                                       "booking_id": booking_id,
                                       "converted_at": now})
        except Exception as e:
            print(f"lead convert failed (non-fatal): {e}")

    # -- inquiry discount code (optional; validated + redeemed atomically) ----
    discount, discount_code = 0, ""
    raw_code = str(data.get("discount_code") or "").strip().upper()
    if raw_code:
        code_ref = db.collection("discount_codes").document(raw_code)

        @firestore.transactional
        def _redeem(txn):
            snap = code_ref.get(transaction=txn)
            if not snap.exists:
                return None, "That code isn't valid."
            c = snap.to_dict()
            if not c.get("active", False):
                return None, "That code is no longer active."
            if c.get("redeemed_by"):
                return None, "That code has already been used."
            exp = c.get("expires_at")
            if exp and exp.replace(tzinfo=timezone.utc) < now:
                return None, "That code has expired."
            txn.update(code_ref, {"redeemed_by": booking_id,
                                  "redeemed_at": now})
            return int(c.get("amount", 0)), None

        try:
            amt, code_err = _redeem(db.transaction())
        except Exception as e:
            print(f"code redemption error: {e}")
            amt, code_err = None, "Code could not be verified. Try again."
        if code_err:
            return _json(req, {"error": code_err,
                               "field": "discount_code"}, 400)
        discount, discount_code = amt, raw_code

    p1 = (data.get("partner1_name") or "").strip()
    p2 = (data.get("partner2_name") or "").strip()
    if p2 and p1.lower() == p2.lower():
        return _json(req, {"error": "Partner 1 and Partner 2 names must be different. If you are booking solo, leave Partner 2 blank."}, 400)
    days_to_event = (event_dt.date() - datetime.now(timezone.utc).date()).days
    pricing = compute_pricing(pkg["id"], second_shooter, extra_hours,
                              discount, days_to_event=days_to_event)
    total = pricing["total"]

    client_merge = {k: str(data.get(k, "")).strip()
                    for k in REQUIRED_FIELDS + OPTIONAL_FIELDS
                    if k not in ("package_id", "payment_option", "agree_terms")}
    # display date on the contract
    client_merge["event_date"] = event_dt.strftime("%B %-d, %Y") \
        if os.name != "nt" else event_dt.strftime("%B %d, %Y")

    booking = {
        "booking_id": booking_id,
        "status": "pending_signature",
        "created_at": now,
        "package_id": pkg["id"],
        "package_name": pkg["name"],
        "service_type": pkg["service_type"],
        "payment_option": data["payment_option"],
        "second_shooter": second_shooter,
        "extra_hours": extra_hours,
        "base_total": pricing["base_total"],
        "addons_total": pricing["addons_total"],
        "addons": pricing["addons"],           # [{id,label,amount}]
        "discount": discount,
        "discount_code": discount_code,
        "coverage_hours": pricing["coverage_hours"],
        "total": total,
        "retainer": RULES["retainer"],
        "balance": total - RULES["retainer"],
        "pif_total": total - RULES["pif_discount"],
        "balance_due_at": _compute_balance_due(event_dt, now)
                          if data["payment_option"] == "standard" else None,
        "event_date_raw": data["event_date"],
        **client_merge,
        "agree_terms_at": now,
        "processor": "zoho",
        "zoho_payment_method_id": pm_id or None,
        "zoho_customer_id": cust_id or None,
        "card_brand": card_brand,
        "card_last4": card_last4,
        "client_ip": req.headers.get("X-Forwarded-For", req.remote_addr),
        # -- lead attribution: which venue page produced this booking ----------
        "attr_venue": str(data.get("attr_venue") or "")[:200],
        "attr_venue_url": str(data.get("attr_venue_url") or "")[:300],
        "attr_landing": str(data.get("attr_landing") or "")[:300],
        "attr_referrer": str(data.get("attr_referrer") or "")[:300],
        "test_mode": TEST_MODE,
    }

    # -- generate contract + send to SignWell ----------------------------------
    pdf = generate_contract(pkg["id"], data["payment_option"],
                            client=client_merge, signwell=True,
                            second_shooter=second_shooter,
                            extra_hours=extra_hours,
                            discount=discount, discount_code=discount_code)
    sw = SignWell(SIGNWELL_API_KEY.value, test_mode=TEST_MODE)
    doc = sw.send_contract(
        pdf, booking_id, client_merge["client_names"], client_merge["email"],
        redirect_url="https://ataviaweddings.com/booked")
    booking["signwell_document_id"] = doc.get("id")
    signing_url = (doc.get("recipients") or [{}])[0].get("signing_url")

    booking["sid"] = str(data.get("sid") or "")[:32]
    booking_ref.set(booking)
    _link_session(db, data.get("sid"), client_merge["client_names"],
                  client_merge["email"], booking_id)
    return _json(req, {"ok": True, "booking_id": booking_id,
                       "signing_url": signing_url,
                       "next": "sign_now_or_check_email"})


# ============================================================== issue_code ==
@https_fn.on_request(region=REGION, secrets=[PROMO_ADMIN_KEY])
def issue_code(req: https_fn.Request) -> https_fn.Response:
    """Admin: mint a single-use inquiry discount code with a real expiry.

    Usage (browser or curl):
      .../issue_code?key=ADMIN_KEY&note=jane@example.com&amount=200&hours=48
    note   : who/what the code is for (stored in Firestore, your eyes only)
    amount : dollars off (default 200)
    hours  : validity window from now (default 48)
    """
    import hmac as _hmac
    supplied = str(req.args.get("key") or "")
    if not _hmac.compare_digest(supplied, PROMO_ADMIN_KEY.value):
        return https_fn.Response("forbidden", status=403)
    try:
        amount = int(req.args.get("amount") or 200)
        hours = int(req.args.get("hours") or 48)
    except ValueError:
        return https_fn.Response("amount/hours must be integers", status=400)
    if not (1 <= amount <= 500) or not (1 <= hours <= 24 * 14):
        return https_fn.Response("amount 1-500, hours 1-336", status=400)
    note = str(req.args.get("note") or "")[:200]

    import secrets as _secrets
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"   # no 0/O/1/I/L lookalikes
    now = datetime.now(timezone.utc)
    db = firestore.client()
    for _ in range(5):                              # collision-proof retry
        code = "ATAVIA-" + "".join(_secrets.choice(alphabet)
                                   for _ in range(4)) + f"-{amount}"
        ref = db.collection("discount_codes").document(code)
        if not ref.get().exists:
            break
    else:
        return https_fn.Response("could not allocate code", status=500)
    expires = now + timedelta(hours=hours)
    ref.set({"code": code, "amount": amount, "active": True,
             "created_at": now, "expires_at": expires,
             "note": note, "redeemed_by": None, "redeemed_at": None})
    pretty = expires.strftime("%B %d at %I:%M %p UTC")
    return _json(req, {
        "code": code, "amount": amount, "expires_at": expires.isoformat(),
        "paste_ready": (
            f"As a thank-you for reaching out, code {code} takes ${amount} "
            f"off any collection if you book at ataviaweddings.com/book "
            f"before {pretty}. Enter it under Payment Plan and the "
            f"discount will appear on your agreement automatically."),
    })


# ============================================================== check_code ==
@https_fn.on_request(region=REGION)
def check_code(req: https_fn.Request) -> https_fn.Response:
    """Public: preview whether a code is currently valid (no redemption)."""
    if req.method == "OPTIONS":
        return https_fn.Response("", status=204, headers=_cors(req))
    if req.method != "POST":
        return _json(req, {"error": "POST only"}, 405)
    data = req.get_json(silent=True) or {}
    code = str(data.get("code") or "").strip().upper()
    if not code:
        return _json(req, {"valid": False, "reason": "Enter a code."})
    snap = firestore.client().collection("discount_codes") \
                            .document(code).get()
    if not snap.exists:
        return _json(req, {"valid": False,
                           "reason": "That code isn't valid."})
    c = snap.to_dict()
    now = datetime.now(timezone.utc)
    if not c.get("active", False):
        return _json(req, {"valid": False,
                           "reason": "That code is no longer active."})
    if c.get("redeemed_by"):
        return _json(req, {"valid": False,
                           "reason": "That code has already been used."})
    exp = c.get("expires_at")
    if exp and exp.replace(tzinfo=timezone.utc) < now:
        return _json(req, {"valid": False,
                           "reason": "That code has expired."})
    return _json(req, {"valid": True, "amount": int(c.get("amount", 0)),
                       "expires_at": exp.isoformat() if exp else None})


def _payment_terms(booking):
    """(amount, memo, line_items) for the retainer or PIF payment.

    Shared by the card-on-file charge and the hosted-invoice fallback so the
    two can never quote different numbers for the same booking.
    """
    addons = booking.get("addons") or []       # pre-addon bookings lack key
    disc = int(booking.get("discount") or 0)
    disc_code = booking.get("discount_code") or ""
    addons_desc = ", ".join(a["label"] for a in addons)
    if disc:
        addons_desc += (", " if addons_desc else "") + \
            f"Inquiry Discount {disc_code} \u2212${disc}"
    pkg_details = booking["package_name"] + (
        f" + {addons_desc}" if addons_desc else "")
    if booking["payment_option"] == "standard":
        amount = booking["retainer"]
        memo = (f"Retainer deposit — {booking['package_name']} — "
                f"{booking['event_date']}")
        line_items = [{"id": booking["package_id"],
                       "item": "Retainer Deposit",
                       "details": pkg_details, "quantity": 1,
                       "price": amount}]
    else:
        amount = booking["pif_total"]
        memo = (f"Paid-in-full — {booking['package_name']} — "
                f"{booking['event_date']}")
        line_items = [{"id": booking["package_id"],
                       "item": booking["package_name"],
                       "details": "Collection (Paid in Full)",
                       "quantity": 1,
                       "price": booking.get("base_total", booking["total"])}]
        line_items += [{"id": a["id"], "item": a["label"],
                        "details": "Add-on", "quantity": 1,
                        "price": a["amount"]} for a in addons]
        if disc:
            line_items.append({"id": "inquiry_discount",
                               "item": f"Inquiry Discount ({disc_code})",
                               "details": "", "quantity": 1, "price": -disc})
        line_items.append({"id": "pif_discount",
                           "item": "Paid-in-Full Discount",
                           "details": "", "quantity": 1,
                           "price": -RULES["pif_discount"]})
    return amount, memo, line_items


@firestore.transactional
def _claim_charge(txn, ref):
    """Atomically claim the right to charge this booking exactly once.

    SignWell retries webhooks, and a double-charged couple is a far worse
    conversation than a missed one. Returns False if anyone already claimed.
    """
    b = ref.get(transaction=txn).to_dict() or {}
    if b.get("charge_claimed_at") or b.get("deposit_paid_at"):
        return False
    txn.update(ref, {"charge_claimed_at": datetime.now(timezone.utc)})
    return True


def _confirm_paid(ref, booking, payment_method_id, tx_id, amount,
                  resend_key, gratuity_secret):
    """Mark a booking confirmed and send the welcome + owner emails.

    NOTE: zoho_webhook still carries its own copy of this logic for the
    payment-link path. Consolidating the two is a safe follow-up, but is
    deliberately not done here to keep this change off the working path.
    """
    plan = booking["payment_option"]
    update = {"status": "confirmed",
              "deposit_paid_at": firestore.SERVER_TIMESTAMP,
              "zoho_payment_method_id": payment_method_id,
              "zoho_payment_id": tx_id,
              "invoice_amount": amount,
              "charged_on_file": True}
    if plan == "pif":
        update["paid_in_full"] = True
        update["balance_paid_at"] = firestore.SERVER_TIMESTAMP
    ref.update(update)
    booking.update(update)

    bd = booking.get("balance_due_at")
    booking["balance_due_date"] = (
        bd.strftime("%B %d, %Y") if hasattr(bd, "strftime") else str(bd or ""))
    try:
        emails.welcome_email(resend_key, booking,
                             q_link=_q_link(booking["booking_id"],
                                            gratuity_secret))
    except Exception as e:
        print(f"welcome email failed: {e}")
    try:
        g_token = _gratuity_token(booking["booking_id"], gratuity_secret)
        emails.notify_owner(
            resend_key, OWNER_EMAIL,
            f"NEW BOOKING CONFIRMED — {booking['package_name']} — "
            f"{booking['event_date']}",
            [f"Booking: {booking['booking_id']}",
             f"Client: {booking['client_names']} ({booking['email']}, "
             f"{booking.get('phone','')})",
             f"Package: {booking['package_name']} ({plan})",
             f"Card charged at signature: ${amount:,} "
             f"({booking.get('card_brand','card')} "
             f"\u2022\u2022\u2022\u2022{booking.get('card_last4','')})",
             f"Event: {booking['event_date']} — "
             f"{booking.get('ceremony_venue','')}",
             f"Balance: ${0 if plan=='pif' else booking['balance']:,}"
             + ("" if plan == "pif" else
                (f" auto-charges {booking['balance_due_date']}"
                 if booking.get("charged_on_file") else
                 f" — NO CARD ON FILE; a balance payment link goes out "
                 f"{booking['balance_due_date']}")),
             ("Source: " + booking["attr_venue"]
              + (f" ({booking['attr_venue_url']})"
                 if booking.get("attr_venue_url") else ""))
             if booking.get("attr_venue")
             else "Source: " + (booking.get("attr_referrer") or "direct"),
             f"Gratuity link: https://ataviaweddings.com/gratuity"
             f"?b={booking['booking_id']}&t={g_token}"])
    except Exception as e:
        print(f"owner notify failed: {e}")


# ======================================================== signwell_webhook ==
@https_fn.on_request(region=REGION,
                     secrets=[SIGNWELL_API_KEY, *ZOHO_SECRETS, RESEND_API_KEY,
                              GRATUITY_SECRET],
                     memory=options.MemoryOption.MB_512)
def signwell_webhook(req: https_fn.Request) -> https_fn.Response:
    raw_body = req.get_data() or b""
    payload = req.get_json(silent=True) or {}
    event = payload.get("event", {})
    event_type = event.get("type") or payload.get("event_type") or ""
    doc = payload.get("data", {}).get("object", {}) or payload.get("document", {})
    doc_id = doc.get("id") or payload.get("document_id")
    print(f"signwell_webhook event={event_type} doc={doc_id}")

    if event_type not in ("document_completed", "document.completed", "completed"):
        return https_fn.Response("ignored", status=200)
    if not doc_id:
        return https_fn.Response("no document id", status=200)

    db = firestore.client()
    from google.cloud.firestore_v1.base_query import FieldFilter
    q = db.collection("bookings").where(
        filter=FieldFilter("signwell_document_id", "==", doc_id)).limit(1).get()
    if not q:
        print(f"no booking for signwell doc {doc_id}")
        return https_fn.Response("no booking", status=200)
    ref = q[0].reference
    booking = q[0].to_dict()

    # --- Webhook verification (authoritative, stronger than payload HMAC) ---
    # SignWell's event.hash scheme is not publicly documented, so instead of
    # trusting the POSTed payload we re-fetch the document from SignWell with
    # our API key and require: status Completed + booking_id match. A forged
    # webhook cannot pass this without also compromising the API key.
    sw = SignWell(SIGNWELL_API_KEY.value, test_mode=TEST_MODE)
    try:
        live = sw.get_document(doc_id)
    except Exception as e:
        print(f"verification fetch failed: {e}")
        return https_fn.Response("verification unavailable", status=500)
    if (live.get("status") != "Completed"
            or (live.get("metadata") or {}).get("booking_id")
            != booking["booking_id"]):
        print(f"webhook verification REJECTED for doc {doc_id}: "
              f"status={live.get('status')}")
        return https_fn.Response("verification failed", status=403)

    # Status model: pending_signature -> signed (signature persisted) ->
    # awaiting_payment (Zoho payment link out). "signed" re-enters here so a
    # Zoho failure is retried on SignWell's webhook retries.
    if booking["status"] not in ("pending_signature", "signed"):
        return https_fn.Response("already processed", status=200)

    # -- persist signature + archive BEFORE any payment-provider call -----------
    if booking["status"] == "pending_signature":
        signed_path = None
        try:
            signed_path = _archive_signed_pdf(
                sw.download_completed_pdf(doc_id), booking["booking_id"])
        except Exception as e:
            print(f"signed pdf archive failed: {e}")
        ref.update({"status": "signed",
                    "signed_at": firestore.SERVER_TIMESTAMP,
                    "signed_contract_path": signed_path})
        booking["status"] = "signed"

    # -- Preferred path: charge the card captured at booking ---------------------
    # Closes the window between signature and payment. If anything about the
    # card fails we fall through to the payment link below, which is exactly
    # the old behaviour — a decline degrades, it does not dead-end.
    zoho = _zoho()
    pm_id = booking.get("zoho_payment_method_id")
    cust_id = booking.get("zoho_customer_id")
    if pm_id and cust_id and booking.get("status") != "confirmed":
        amount, memo, line_items = _payment_terms(booking)
        db_client = firestore.client()
        if not _claim_charge(db_client.transaction(), ref):
            return https_fn.Response("charge already claimed", status=200)
        try:
            tx = zoho.charge_saved_method(
                cust_id, pm_id, amount, memo,
                meta={"booking_id": booking["booking_id"],
                      "kind": "retainer" if booking["payment_option"]
                              == "standard" else "pif"},
                descriptor=STATEMENT_DESCRIPTOR)
        except Exception as e:
            # Release the claim so a genuine retry can try again, then fall
            # through to the invoice path below.
            ref.update({"charge_claimed_at": None,
                        "charge_failed_at": firestore.SERVER_TIMESTAMP,
                        "charge_last_error": str(e)[:500]})
            print(f"card-on-file charge failed, falling back to link: {e}")
            try:
                emails.notify_owner(
                    RESEND_API_KEY.value, OWNER_EMAIL,
                    f"Card declined at signature — {booking['client_names']}",
                    [f"Booking {booking['booking_id']} is SIGNED but the card "
                     f"on file did not go through.",
                     f"Error: {e}",
                     "A Zoho payment link is being sent instead — the couple "
                     "can pay with a different card. No action needed unless "
                     "that also fails."])
            except Exception as e2:
                print(f"owner notify failed: {e2}")
        else:
            tx_id = (tx or {}).get("payment_id")
            if (tx or {}).get("status") != "succeeded":
                ref.update({"charge_claimed_at": None,
                            "charge_failed_at": firestore.SERVER_TIMESTAMP,
                            "charge_last_error":
                                f"status={(tx or {}).get('status')} "
                                f"{(tx or {}).get('failure_code','')} "
                                f"payment={tx_id}"[:500]})
                print(f"card declined payment={tx_id}, falling back to link")
            else:
                _confirm_paid(ref, booking, pm_id, tx_id, amount,
                              RESEND_API_KEY.value, GRATUITY_SECRET.value)
                print(f"retainer charged on file: {booking['booking_id']} "
                      f"${amount} tx={tx_id}")
                return https_fn.Response("charged", status=200)

    # -- Fallback: Zoho payment link, emailed by Zoho (hosted-page path) --------
    try:
        amount, memo, line_items = _payment_terms(booking)
        link = zoho.create_payment_link(
            amount=amount, description=memo, email=booking["email"],
            reference_id=booking["booking_id"],
            phone=booking.get("phone", ""),
            expires_at=(datetime.now(timezone.utc)
                        + timedelta(days=14)).strftime("%Y-%m-%d"),
            return_url="https://ataviaweddings.com/book/thank-you",
            meta={"booking_id": booking["booking_id"], "kind": "retainer"})
        ref.update({"status": "awaiting_payment",
                    "zoho_payment_link_id": link["payment_link_id"],
                    "zoho_payment_link_url": link.get("url"),
                    "invoice_amount": amount})
        return https_fn.Response("ok", status=200)
    except Exception as e:
        attempts = booking.get("zoho_setup_attempts", 0) + 1
        ref.update({"zoho_setup_attempts": attempts,
                    "zoho_setup_last_error": str(e)[:500]})
        print(f"zoho setup failed (attempt {attempts}): {e}")
        if attempts == 1:                      # alert once, not per retry
            try:
                emails.notify_owner(
                    RESEND_API_KEY.value, OWNER_EMAIL,
                    f"ACTION NEEDED: payment setup failed — "
                    f"{booking['client_names']}",
                    [f"Booking {booking['booking_id']} is SIGNED but the "
                     f"Zoho payment link could not be created.",
                     f"Error: {e}",
                     "SignWell will retry automatically; if this persists, "
                     "investigate the Zoho OAuth secrets/account."])
            except Exception as e2:
                print(f"owner notify failed: {e2}")
        # 500 -> SignWell retries the event, re-attempting Zoho setup
        return https_fn.Response("zoho setup failed", status=500)


# ============================================================ zoho_webhook ==
@https_fn.on_request(region=REGION,
                     secrets=[*ZOHO_SECRETS, RESEND_API_KEY, GRATUITY_SECRET],
                     memory=options.MemoryOption.MB_512)
def zoho_webhook(req: https_fn.Request) -> https_fn.Response:
    """Zoho Payments webhook. Register (once, Settings > Developer Space or the
    Webhooks API) for: payment_link.paid. Everything else is ignored.

    Two link kinds reach here, told apart by meta_data.kind on the link:
      retainer/pif  -> booking goes awaiting_payment -> confirmed
      balance       -> balance_paid_at set on an already-confirmed booking
    """
    payload = req.get_json(silent=True) or {}
    event_type = payload.get("event_type", "")
    print(f"zoho_webhook: {event_type} {json.dumps(payload)[:600]}")
    if event_type != "payment_link.paid":
        return https_fn.Response("ignored", status=200)
    if str(payload.get("account_id", "")) != ZOHO_ACCOUNT_ID:
        print("zoho webhook REJECTED: wrong account_id")
        return https_fn.Response("wrong account", status=403)
    link = (payload.get("event_object") or {}).get("payment_links") or {}
    link_id = str(link.get("payment_link_id") or "")
    if not link_id:
        return https_fn.Response("no link id", status=200)

    # --- Webhook verification (authoritative, mirrors SignWell pattern) ---
    # Zoho webhooks carry no HMAC we can check here, so re-fetch the link
    # with our OAuth token and require status=paid. A forged POST cannot
    # pass this without also compromising the refresh token.
    try:
        live = _zoho().get_payment_link(link_id)
    except Exception as e:
        print(f"zoho verification fetch failed: {e}")
        return https_fn.Response("verification unavailable", status=500)
    if str(live.get("status", "")).lower() != "paid":
        print(f"zoho webhook REJECTED: link {link_id} status={live.get('status')}")
        return https_fn.Response("verification failed", status=403)
    paid = [p for p in (live.get("payments") or [])
            if p.get("status") == "succeeded"]
    payment_id = paid[0].get("payment_id") if paid else None
    meta = {m.get("key"): m.get("value") for m in (live.get("meta_data") or [])}
    kind = meta.get("kind") or "retainer"

    db = firestore.client()
    from google.cloud.firestore_v1.base_query import FieldFilter

    # --- balance link (confirmed booking, card not on file) -----------------
    if kind == "balance":
        q = db.collection("bookings").where(
            filter=FieldFilter("balance_payment_link_id", "==", link_id)
        ).limit(1).get()
        if not q:
            return https_fn.Response("no booking", status=200)
        b = q[0].to_dict()
        if b.get("balance_paid_at"):
            return https_fn.Response("already processed", status=200)
        q[0].reference.update({"balance_paid_at": firestore.SERVER_TIMESTAMP,
                               "balance_payment_id": payment_id,
                               "balance_paid_via": "link"})
        try:
            emails.notify_owner(
                RESEND_API_KEY.value, OWNER_EMAIL,
                f"BALANCE PAID (link) — {b['client_names']} — ${b['balance']:,}",
                [f"Booking {b['booking_id']} balance paid via Zoho link."])
        except Exception as e:
            print(f"owner notify failed: {e}")
        return https_fn.Response("ok", status=200)

    # --- retainer / PIF link (signed booking awaiting payment) ---------------
    q = db.collection("bookings").where(
        filter=FieldFilter("zoho_payment_link_id", "==", link_id)).limit(1).get()
    if not q:
        return https_fn.Response("no booking", status=200)
    ref = q[0].reference
    booking = q[0].to_dict()
    if booking["status"] != "awaiting_payment":     # idempotency guard
        return https_fn.Response("already processed", status=200)

    plan = booking["payment_option"]
    update = {
        "status": "confirmed",
        "deposit_paid_at": firestore.SERVER_TIMESTAMP,
        "zoho_payment_id": payment_id,
        "charged_on_file": False,        # link payments store no card
        "confirmed_via": "link",
    }
    if plan == "pif":
        update["paid_in_full"] = True
        update["balance_paid_at"] = firestore.SERVER_TIMESTAMP
    ref.update(update)
    booking.update(update)

    # -- welcome email + owner notification -------------------------------------
    bd = booking.get("balance_due_at")
    booking["balance_due_date"] = (
        bd.strftime("%B %d, %Y") if hasattr(bd, "strftime") else str(bd or ""))
    try:
        emails.welcome_email(RESEND_API_KEY.value, booking,
                             q_link=_q_link(booking["booking_id"],
                                            GRATUITY_SECRET.value))
    except Exception as e:
        print(f"welcome email failed: {e}")
    try:
        g_token = _gratuity_token(booking["booking_id"], GRATUITY_SECRET.value)
        emails.notify_owner(
            RESEND_API_KEY.value, OWNER_EMAIL,
            f"NEW BOOKING CONFIRMED — {booking['package_name']} — "
            f"{booking['event_date']}",
            [f"Booking: {booking['booking_id']}",
             f"Client: {booking['client_names']} ({booking['email']}, "
             f"{booking.get('phone','')})",
             f"Package: {booking['package_name']} ({plan})",
             f"Add-ons: "
             + (", ".join(a['label'] for a in booking.get('addons') or [])
                or "none")
             + (f" | Discount: {booking.get('discount_code')} "
                f"\u2212${booking.get('discount')}"
                if booking.get('discount') else "")
             + (f" — {booking.get('coverage_hours', '?')} hrs total coverage"
                if booking.get('extra_hours') else ""),
             f"Event: {booking['event_date']} — "
             f"{booking.get('ceremony_venue','')}",
             f"Paid now: ${booking['invoice_amount']:,}",
             f"Balance: ${0 if plan=='pif' else booking['balance']:,}"
             + ("" if plan == "pif" else
                (f" auto-charges {booking['balance_due_date']}"
                 if booking.get("charged_on_file") else
                 f" — NO CARD ON FILE; a balance payment link goes out "
                 f"{booking['balance_due_date']}")),
             ("Source: " + booking["attr_venue"]
              + (f" ({booking['attr_venue_url']})"
                 if booking.get("attr_venue_url") else ""))
             if booking.get("attr_venue")
             else "Source: " + (booking.get("attr_referrer") or "direct"),
             f"Gratuity link: https://ataviaweddings.com/gratuity"
             f"?b={booking['booking_id']}&t={g_token}"])
    except Exception as e:
        print(f"owner notify failed: {e}")
    return https_fn.Response("ok", status=200)


def _poll_paid_invoices():
    """Safety net: any booking stuck at awaiting_payment whose Zoho payment
    link is actually PAID gets confirmed here, so a dropped webhook can never
    strand a paying client. Runs inside the daily scheduler."""
    from google.cloud.firestore_v1.base_query import FieldFilter
    db = firestore.client()
    stuck = (db.collection("bookings")
               .where(filter=FieldFilter("status", "==", "awaiting_payment"))
               .get())
    if not stuck:
        return
    zoho = _zoho()
    for snap in stuck:
        b = snap.to_dict()
        link_id = b.get("zoho_payment_link_id")
        if not link_id:
            continue
        try:
            link = zoho.get_payment_link(link_id)
        except Exception as e:
            print(f"poller: link fetch failed for {b['booking_id']}: {e}")
            continue
        if str(link.get("status", "")).lower() != "paid":
            continue
        paid = [p for p in (link.get("payments") or [])
                if p.get("status") == "succeeded"]
        update = {"status": "confirmed",
                  "deposit_paid_at": firestore.SERVER_TIMESTAMP,
                  "zoho_payment_id": paid[0].get("payment_id") if paid else None,
                  "charged_on_file": False,
                  "confirmed_via": "poller"}
        if b["payment_option"] == "pif":
            update["paid_in_full"] = True
            update["balance_paid_at"] = firestore.SERVER_TIMESTAMP
        snap.reference.update(update)
        b.update(update)
        bd = b.get("balance_due_at")
        b["balance_due_date"] = (bd.strftime("%B %d, %Y")
                                 if hasattr(bd, "strftime") else str(bd or ""))
        try:
            emails.welcome_email(RESEND_API_KEY.value, b,
                                 q_link=_q_link(b["booking_id"],
                                                GRATUITY_SECRET.value))
            emails.notify_owner(
                RESEND_API_KEY.value, OWNER_EMAIL,
                f"BOOKING CONFIRMED (via poller) — {b['package_name']} — "
                f"{b['event_date']}",
                [f"Booking {b['booking_id']} — the payment webhook was missed "
                 f"but the payment link is paid. Confirmed automatically.",
                 f"Client: {b['client_names']} ({b['email']})"])
        except Exception as e:
            print(f"poller emails failed: {e}")
        print(f"poller: confirmed {b['booking_id']}")


def _chase_leads():
    """Card-window abandons. zoho_session recorded a lead; no booking exists.
    Nudge 1 the first morning after (>= 3h old), nudge 2 three days later,
    owner alert with nudge 1, marked expired after 14 days. Never nudges a
    lead whose email has since booked."""
    from google.cloud.firestore_v1.base_query import FieldFilter
    db = firestore.client()
    now = datetime.now(timezone.utc)
    pending = (db.collection("leads")
                 .where(filter=FieldFilter("status", "==", "card_pending")).get())
    for snap in pending:
        lead = snap.to_dict()
        created = lead.get("created_at")
        if not created:
            continue
        age_h = (now - created).total_seconds() / 3600
        if age_h < 3:
            continue                       # still might be finishing right now
        # converted under a different session (e.g. retried from a new tab)?
        booked = (db.collection("bookings")
                    .where(filter=FieldFilter("email", "==", lead.get("email", "")))
                    .limit(1).get())
        if booked:
            snap.reference.update({"status": "converted",
                                   "booking_id": booked[0].id,
                                   "converted_at": now})
            continue
        if age_h > 24 * 14:
            snap.reference.update({"status": "expired"})
            continue
        resume = "https://ataviaweddings.com/book/"
        if lead.get("package_id"):
            resume += f"?pkg={lead['package_id']}"
        try:
            if not lead.get("nudge1_sent_at"):
                emails.card_recovery(RESEND_API_KEY.value, lead, resume)
                snap.reference.update({"nudge1_sent_at": now})
                emails.notify_owner(
                    RESEND_API_KEY.value, OWNER_EMAIL,
                    f"ABANDONED AT CARD STEP \u2014 {lead.get('client_names','')} "
                    f"\u2014 {lead.get('event_date_display') or 'no date'}",
                    [f"{lead.get('client_names','')} ({lead.get('email','')}, "
                     f"{lead.get('phone','')}) filled the booking form for "
                     f"{lead.get('package_name') or 'a collection'} and closed the "
                     f"card window.",
                     "A finish-your-booking email just went out; a second goes "
                     "in 3 days. Worth a personal text if it's a strong date.",
                     f"Source: {lead.get('attr_venue') or 'direct'}"])
            elif not lead.get("nudge2_sent_at") and age_h >= 24 * 3:
                emails.card_recovery(RESEND_API_KEY.value, lead, resume, second=True)
                snap.reference.update({"nudge2_sent_at": now})
        except Exception as e:
            print(f"lead chase failed {snap.id}: {e}")


def _chase_abandoned():
    """Abandoned-cart recovery. Two stall points:
    pending_signature (submitted, never signed) -> nudges at day 2 and 5 with
    the signing link (on top of SignWell's own 3/6/10 reminders), owner alert
    at day 7, marked abandoned at day 30 (SignWell doc expiry).
    awaiting_payment (signed, never paid) -> Zoho link re-sent + urgency
    nudge at day 1 and 4, owner alert at day 6."""
    from google.cloud.firestore_v1.base_query import FieldFilter
    db = firestore.client()
    now = datetime.now(timezone.utc)

    # --- unsigned ------------------------------------------------------------
    for snap in (db.collection("bookings")
                   .where(filter=FieldFilter("status", "==",
                                             "pending_signature")).get()):
        b = snap.to_dict()
        created = b.get("created_at")
        if not created:
            continue
        age = (now - created).days
        try:
            if age >= 30 and not b.get("abandoned_at"):
                snap.reference.update({"status": "abandoned_unsigned",
                                       "abandoned_at": firestore.SERVER_TIMESTAMP})
                emails.notify_owner(
                    RESEND_API_KEY.value, OWNER_EMAIL,
                    f"BOOKING ABANDONED (never signed) — {b['client_names']}",
                    [f"Booking {b['booking_id']} for {b['event_date']} expired "
                     f"unsigned after 30 days. Date is free again."])
            elif age >= 7 and not b.get("sig_owner_alerted"):
                emails.notify_owner(
                    RESEND_API_KEY.value, OWNER_EMAIL,
                    f"UNSIGNED 7 DAYS — {b['client_names']} — {b['event_date']}",
                    [f"Booking {b['booking_id']}: submitted but contract unsigned "
                     f"for a week despite reminders. Worth a personal call: "
                     f"{b.get('phone','')} / {b['email']}"])
                snap.reference.update({"sig_owner_alerted": True})
            elif (age >= 5 and not b.get("sig_nudge2_sent")) or \
                 (age >= 2 and not b.get("sig_nudge1_sent")):
                sw = SignWell(SIGNWELL_API_KEY.value, test_mode=TEST_MODE)
                doc = sw.get_document(b["signwell_document_id"])
                url = (doc.get("recipients") or [{}])[0].get("signing_url")
                if url:
                    emails.signature_nudge(RESEND_API_KEY.value, b, url)
                    snap.reference.update(
                        {"sig_nudge2_sent" if age >= 5 else "sig_nudge1_sent": True})
        except Exception as e:
            print(f"unsigned chase failed {b['booking_id']}: {e}")

    # --- signed but unpaid -----------------------------------------------------
    for snap in (db.collection("bookings")
                   .where(filter=FieldFilter("status", "==",
                                             "awaiting_payment")).get()):
        b = snap.to_dict()
        signed = b.get("signed_at")
        if not signed:
            continue
        age = (now - signed).days
        try:
            if age >= 6 and not b.get("pay_owner_alerted"):
                emails.notify_owner(
                    RESEND_API_KEY.value, OWNER_EMAIL,
                    f"SIGNED BUT UNPAID 6 DAYS — {b['client_names']} — "
                    f"{b['event_date']}",
                    [f"Booking {b['booking_id']}: contract signed, retainer "
                     f"invoice unpaid for 6 days despite nudges. Personal "
                     f"follow-up recommended: {b.get('phone','')} / {b['email']}"])
                snap.reference.update({"pay_owner_alerted": True})
            elif (age >= 4 and not b.get("pay_nudge2_sent")) or \
                 (age >= 1 and not b.get("pay_nudge1_sent")):
                # Zoho has no "resend" call; our nudge carries the link.
                emails.payment_nudge(RESEND_API_KEY.value, b,
                                     pay_url=b.get("zoho_payment_link_url"))
                snap.reference.update(
                    {"pay_nudge2_sent" if age >= 4 else "pay_nudge1_sent": True})
        except Exception as e:
            print(f"unpaid chase failed {b['booking_id']}: {e}")


def _send_questionnaire_reminders():
    """Confirmed bookings without a submitted questionnaire get a reminder at
    30 and 15 days before the event; the owner gets an alert at 13 days
    (contract requires the timeline 14 days out)."""
    from google.cloud.firestore_v1.base_query import FieldFilter
    db = firestore.client()
    today = datetime.now(timezone.utc).date()
    booked = (db.collection("bookings")
                .where(filter=FieldFilter("status", "==", "confirmed"))
                .get())
    for snap in booked:
        b = snap.to_dict()
        if b.get("questionnaire_submitted_at"):
            continue
        try:
            ev = datetime.strptime(b.get("event_date_raw", ""), "%Y-%m-%d").date()
        except ValueError:
            continue
        days = (ev - today).days
        if days < 0:
            continue
        link = _q_link(b["booking_id"], GRATUITY_SECRET.value)
        try:
            if days <= 13 and not b.get("q_owner_alerted"):
                emails.notify_owner(
                    RESEND_API_KEY.value, OWNER_EMAIL,
                    f"QUESTIONNAIRE MISSING — {b['client_names']} — "
                    f"{b['event_date']} ({days} days out)",
                    [f"Booking {b['booking_id']}: contract requires day-of "
                     f"details 14 days out and nothing has been submitted.",
                     "Reach out personally; automated reminders were sent at "
                     "30 and 15 days."])
                snap.reference.update({"q_owner_alerted": True})
            elif days <= 15 and not b.get("q_reminder2_sent"):
                emails.questionnaire_reminder(RESEND_API_KEY.value, b, link, days)
                snap.reference.update({"q_reminder2_sent": True})
            elif days <= 30 and not b.get("q_reminder1_sent"):
                emails.questionnaire_reminder(RESEND_API_KEY.value, b, link, days)
                snap.reference.update({"q_reminder1_sent": True})
        except Exception as e:
            print(f"questionnaire reminder failed {b['booking_id']}: {e}")


def _send_gratuity_invites():
    """3 days after the event, email fully-paid clients a one-time thank-you
    with their tokenized gratuity link. Never sent to bookings with an
    outstanding balance; never sent twice."""
    from google.cloud.firestore_v1.base_query import FieldFilter
    db = firestore.client()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%d")
    booked = (db.collection("bookings")
                .where(filter=FieldFilter("status", "==", "confirmed"))
                .get())
    for snap in booked:
        b = snap.to_dict()
        if b.get("gratuity_invite_sent_at"):
            continue
        if (b.get("event_date_raw") or "9999") > cutoff:
            continue                       # event not yet 3 days past
        fully_paid = (b.get("payment_option") == "pif"
                      or b.get("balance_paid_at") is not None)
        if not fully_paid:
            continue                       # never ask for tips over an unpaid balance
        link = ("https://ataviaweddings.com/gratuity"
                f"?b={b['booking_id']}"
                f"&t={_gratuity_token(b['booking_id'], GRATUITY_SECRET.value)}")
        try:
            emails.gratuity_invite(RESEND_API_KEY.value, b, link)
            snap.reference.update(
                {"gratuity_invite_sent_at": firestore.SERVER_TIMESTAMP})
            print(f"gratuity invite sent: {b['booking_id']}")
        except Exception as e:
            print(f"gratuity invite failed for {b['booking_id']}: {e}")


# ========================================================= charge_balances ==
@scheduler_fn.on_schedule(schedule="every day 07:00",
                          timezone=scheduler_fn.Timezone("America/Phoenix"),
                          region=REGION,
                          secrets=[*ZOHO_SECRETS, RESEND_API_KEY,
                                   GRATUITY_SECRET, SIGNWELL_API_KEY])
def charge_balances(event: scheduler_fn.ScheduledEvent) -> None:
    _poll_paid_invoices()      # safety net: catch payments whose webhook dropped
    _send_gratuity_invites()   # post-event thank-you + gratuity link
    _send_questionnaire_reminders()   # nag unsubmitted questionnaires
    _chase_abandoned()                # recover stalled bookings
    _chase_leads()                    # card-window abandons (no booking yet)
    db = firestore.client()
    now = datetime.now(timezone.utc)
    from google.cloud.firestore_v1.base_query import FieldFilter
    due = (db.collection("bookings")
             .where(filter=FieldFilter("status", "==", "confirmed"))
             .where(filter=FieldFilter("payment_option", "==", "standard"))
             .where(filter=FieldFilter("balance_due_at", "<=", now))
             .get())
    zoho = _zoho()
    for snap in due:
        b = snap.to_dict()
        if b.get("balance_paid_at") or b.get("balance_attempts", 0) >= 3:
            continue
        memo = (f"Remaining balance — {b['package_name']} — "
                f"{b['event_date']}")
        pm_id, cust_id = b.get("zoho_payment_method_id"), b.get("zoho_customer_id")
        if not (pm_id and cust_id):
            # No card on file (link-paid or pre-Zoho booking): send a balance
            # payment link once; zoho_webhook marks it paid.
            if b.get("balance_payment_link_id"):
                continue
            try:
                link = zoho.create_payment_link(
                    amount=b["balance"], description=memo, email=b["email"],
                    reference_id=f"{b['booking_id']}-balance",
                    phone=b.get("phone", ""),
                    return_url="https://ataviaweddings.com/book/thank-you",
                    meta={"booking_id": b["booking_id"], "kind": "balance"})
                snap.reference.update({
                    "balance_payment_link_id": link["payment_link_id"],
                    "balance_payment_link_url": link.get("url"),
                    "balance_link_sent_at": firestore.SERVER_TIMESTAMP})
                emails.notify_owner(
                    RESEND_API_KEY.value, OWNER_EMAIL,
                    f"BALANCE LINK SENT — {b['client_names']} — ${b['balance']:,}",
                    [f"Booking {b['booking_id']} has no card on file; a Zoho "
                     f"payment link for the balance was emailed to {b['email']}.",
                     f"Link: {link.get('url')}"])
            except Exception as e:
                snap.reference.update({
                    "balance_attempts": b.get("balance_attempts", 0) + 1,
                    "balance_last_error": str(e)[:500]})
                print(f"balance link failed {b['booking_id']}: {e}")
            continue
        try:
            tx = zoho.charge_saved_method(
                cust_id, pm_id, b["balance"], memo,
                meta={"booking_id": b["booking_id"], "kind": "balance"},
                descriptor=STATEMENT_DESCRIPTOR)
            if tx.get("status") != "succeeded":
                raise RuntimeError(f"status={tx.get('status')} "
                                   f"{tx.get('failure_code','')} "
                                   f"payment={tx.get('payment_id')}")
            snap.reference.update({
                "balance_paid_at": firestore.SERVER_TIMESTAMP,
                "balance_payment_id": tx.get("payment_id"),
            })
            emails.notify_owner(
                RESEND_API_KEY.value, OWNER_EMAIL,
                f"BALANCE CHARGED — {b['client_names']} — ${b['balance']:,}",
                [f"Booking {b['booking_id']} balance charged successfully."])
            # welcome_email promised this charge on this date, so it must not
            # land on their statement unannounced.
            try:
                emails.balance_receipt(RESEND_API_KEY.value, b, b["balance"])
            except Exception as e2:
                print(f"balance receipt failed {b['booking_id']}: {e2}")
        except Exception as e:
            attempts = b.get("balance_attempts", 0) + 1
            upd = {"balance_attempts": attempts,
                   "balance_last_error": str(e)[:500]}
            # On the LAST attempt only, mint a hosted link so they can pay with
            # another card. Deliberately not sooner: while retries are still
            # scheduled, a link the couple pays could race the next morning's
            # charge and take the money twice. Once attempts stop, that race is
            # gone. send_email=False because the link goes out in our own
            # branded email below rather than a bare Zoho one.
            pay_url = b.get("balance_payment_link_url")
            if attempts >= 3 and not pay_url:
                try:
                    link = zoho.create_payment_link(
                        amount=b["balance"], description=memo, email=b["email"],
                        reference_id=f"{b['booking_id']}-balance",
                        phone=b.get("phone", ""),
                        return_url="https://ataviaweddings.com/book/thank-you",
                        meta={"booking_id": b["booking_id"], "kind": "balance"},
                        send_email=False)
                    pay_url = link.get("url")
                    upd["balance_payment_link_id"] = link["payment_link_id"]
                    upd["balance_payment_link_url"] = pay_url
                except Exception as e3:
                    print(f"balance link failed {b['booking_id']}: {e3}")
            snap.reference.update(upd)
            emails.notify_owner(
                RESEND_API_KEY.value, OWNER_EMAIL,
                f"BALANCE CHARGE FAILED (attempt {attempts}/3) — "
                f"{b['client_names']}",
                [f"Booking {b['booking_id']}: {e}",
                 "Will retry tomorrow." if attempts < 3 else
                 "MAX ATTEMPTS REACHED — manual follow-up needed.",
                 f"Couple emailed a payment link: {pay_url}" if pay_url else
                 "Couple emailed a heads-up (no link; retries still pending)."])
            # The couple hears about it too. Previously only the studio was
            # told, so an expired card stayed invisible to them until someone
            # phoned.
            try:
                emails.balance_charge_failed(
                    RESEND_API_KEY.value, b, b["balance"], attempts, 3,
                    pay_url=pay_url)
            except Exception as e4:
                print(f"balance failure email failed {b['booking_id']}: {e4}")
    _purge_old_sessions(db)
    try:
        _send_daily_digest(db)
    except Exception as e:
        print(f"daily digest failed: {e}")


# ==================================================== questionnaire_prefill =
@https_fn.on_request(region=REGION, secrets=[GRATUITY_SECRET])
def questionnaire_prefill(req: https_fn.Request) -> https_fn.Response:
    """Returns booking basics for form pre-fill, gated by the link token."""
    if req.method == "OPTIONS":
        return https_fn.Response("", status=204, headers=_cors(req))
    booking_id = req.args.get("b", "")
    token = req.args.get("t", "")
    if not hmac.compare_digest(
            token, _gratuity_token(booking_id, GRATUITY_SECRET.value)):
        return _json(req, {"error": "invalid link"}, 403)
    snap = firestore.client().collection("bookings").document(booking_id).get()
    if not snap.exists:
        return _json(req, {"error": "booking not found"}, 404)
    b = snap.to_dict()
    return _json(req, {"ok": True, "prefill": {
        "client_names": b.get("client_names", ""),
        "contact_email": b.get("email", ""),
        "contact_phone": b.get("phone", ""),
        "wedding_date": b.get("event_date_raw", ""),
        "cer_venue": b.get("ceremony_venue", ""),
        "rec_venue": b.get("reception_venue", ""),
    }, "submitted": bool(b.get("questionnaire_submitted_at")),
       "answers": b.get("questionnaire") or {}})


# ===================================================== questionnaire_submit =
@https_fn.on_request(region=REGION,
                     secrets=[GRATUITY_SECRET, RESEND_API_KEY])
def questionnaire_submit(req: https_fn.Request) -> https_fn.Response:
    if req.method == "OPTIONS":
        return https_fn.Response("", status=204, headers=_cors(req))
    if req.method != "POST":
        return _json(req, {"error": "POST only"}, 405)
    data = req.get_json(silent=True) or {}
    booking_id = data.get("booking_id", "")
    token = data.get("token", "")
    if not hmac.compare_digest(
            token, _gratuity_token(booking_id, GRATUITY_SECRET.value)):
        return _json(req, {"error": "invalid link"}, 403)
    db = firestore.client()
    ref = db.collection("bookings").document(booking_id)
    snap = ref.get()
    if not snap.exists:
        return _json(req, {"error": "booking not found"}, 404)
    b = snap.to_dict()

    raw = data.get("answers") or {}
    answers = {k: str(raw.get(k, ""))[:2000] for k in ALL_FIELD_IDS}
    if not any(v.strip() for v in answers.values()):
        return _json(req, {"error": "questionnaire is empty"}, 400)

    first_time = not b.get("questionnaire_submitted_at")
    ref.update({
        "questionnaire": answers,
        "questionnaire_submitted_at": b.get("questionnaire_submitted_at")
                                      or firestore.SERVER_TIMESTAMP,
        "questionnaire_updated_at": firestore.SERVER_TIMESTAMP,
    })
    try:
        emails.questionnaire_summary(
            RESEND_API_KEY.value, OWNER_EMAIL, b, answers, SUMMARY_LAYOUT)
    except Exception as e:
        print(f"questionnaire summary email failed: {e}")
    return _json(req, {"ok": True, "updated": not first_time})


# ================================================================ gratuity ==
@https_fn.on_request(region=REGION,
                     secrets=[*ZOHO_SECRETS, RESEND_API_KEY, GRATUITY_SECRET])
def gratuity(req: https_fn.Request) -> https_fn.Response:
    if req.method == "OPTIONS":
        return https_fn.Response("", status=204, headers=_cors(req))
    if req.method != "POST":
        return _json(req, {"error": "POST only"}, 405)
    data = req.get_json(silent=True) or {}
    booking_id, token = data.get("booking_id", ""), data.get("token", "")
    try:
        amount = round(float(data.get("amount", 0)), 2)
    except (TypeError, ValueError):
        return _json(req, {"error": "invalid amount"}, 400)
    if not (5 <= amount <= 2000):
        return _json(req, {"error": "amount must be between $5 and $2000"}, 400)
    if not hmac.compare_digest(
            token, _gratuity_token(booking_id, GRATUITY_SECRET.value)):
        return _json(req, {"error": "invalid link"}, 403)

    db = firestore.client()
    snap = db.collection("bookings").document(booking_id).get()
    if not snap.exists:
        return _json(req, {"error": "booking not found"}, 404)
    b = snap.to_dict()
    if not (b.get("zoho_payment_method_id") and b.get("zoho_customer_id")):
        return _json(req, {"error": "no payment method on file"}, 409)

    tx = _zoho().charge_saved_method(
        b["zoho_customer_id"], b["zoho_payment_method_id"], amount,
        f"Team gratuity — {b['package_name']} — {b['event_date']}",
        meta={"booking_id": booking_id, "kind": "gratuity"},
        descriptor=STATEMENT_DESCRIPTOR)
    if tx.get("status") != "succeeded":
        return _json(req, {"error": "card declined"}, 402)
    snap.reference.collection("gratuities").add({
        "amount": amount, "at": firestore.SERVER_TIMESTAMP,
        "payment_id": tx.get("payment_id"),
    })
    try:
        emails.gratuity_receipt(RESEND_API_KEY.value, b, amount)
        emails.notify_owner(
            RESEND_API_KEY.value, OWNER_EMAIL,
            f"GRATUITY RECEIVED — ${amount:,.2f} — {b['client_names']}",
            [f"Booking {b['booking_id']} — distribute 100% to event team.",
             f"Event: {b['event_date']} — {b['package_name']}"])
    except Exception as e:
        print(f"gratuity emails failed: {e}")
    return _json(req, {"ok": True, "amount": amount})


# ============================================================ admin block ==
# Everything below serves admin.ataviaweddings.com. Callers must present a
# Firebase ID token (Authorization: Bearer ...) for an ADMIN_EMAILS account.

def _admin_user(req):
    """Return the verified admin email, or None."""
    from firebase_admin import auth as fb_auth
    hdr = req.headers.get("Authorization", "")
    if not hdr.startswith("Bearer "):
        return None
    try:
        claims = fb_auth.verify_id_token(hdr[7:])
    except Exception as e:
        print(f"admin token rejected: {e}")
        return None
    email = (claims.get("email") or "").lower()
    if claims.get("email_verified") and email in ADMIN_EMAILS:
        return email
    return None


def _mint_code(db, amount, hours, note):
    import secrets as _secrets
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    now = datetime.now(timezone.utc)
    for _ in range(5):
        code = "ATAVIA-" + "".join(_secrets.choice(alphabet) for _ in range(4)) + f"-{amount}"
        ref = db.collection("discount_codes").document(code)
        if not ref.get().exists:
            break
    else:
        raise RuntimeError("could not allocate code")
    expires = now + timedelta(hours=hours)
    ref.set({"code": code, "amount": amount, "active": True,
             "created_at": now, "expires_at": expires,
             "note": note, "redeemed_by": None, "redeemed_at": None})
    pretty = expires.strftime("%B %d at %I:%M %p UTC")
    return {"code": code, "amount": amount, "expires_at": expires.isoformat(),
            "paste_ready": (
                f"As a thank-you for reaching out, code {code} takes ${amount} "
                f"off any collection if you book at ataviaweddings.com/book "
                f"before {pretty}. Enter it under Payment Plan and the "
                f"discount will appear on your agreement automatically.")}


@https_fn.on_request(region=REGION,
                     secrets=[*ZOHO_SECRETS, SIGNWELL_API_KEY, RESEND_API_KEY,
                              GRATUITY_SECRET])
def admin_action(req: https_fn.Request) -> https_fn.Response:
    """One endpoint for every button on the admin dashboard.

    POST JSON {action, booking_id?, ...}. Actions:
      payment_link        retainer link (awaiting_payment) or balance link (confirmed, unpaid)
      retry_balance       charge the saved card for the balance right now
      resend_contract     re-email the SignWell signing link
      resend_questionnaire re-email the questionnaire link
      send_gratuity       send the post-wedding thank-you + gratuity link now
      mark_paid           card was run by hand: record {payment: balance|retainer, payment_id, note}, void open link
      cancel              mark cancelled, void open payment links
      refund              refund {amount} of the retainer/PIF payment
      issue_code          mint a discount code {amount, hours, note}
      ical_url            return the private calendar-subscription URL
    """
    if req.method == "OPTIONS":
        return https_fn.Response("", status=204, headers=_cors(req))
    who = _admin_user(req)
    if not who:
        return _json(req, {"error": "not authorised"}, 401)
    data = req.get_json(silent=True) or {}
    action = str(data.get("action") or "")
    db = firestore.client()
    now = datetime.now(timezone.utc)

    if action == "ical_url":
        tok = hmac.new(GRATUITY_SECRET.value.encode(), b"ical-feed",
                       hashlib.sha256).hexdigest()[:32]
        return _json(req, {"url": f"https://us-central1-atavia-c29cd.cloudfunctions.net/ical_feed?t={tok}"})

    if action == "issue_code":
        try:
            amount = int(data.get("amount") or 200); hours = int(data.get("hours") or 48)
        except ValueError:
            return _json(req, {"error": "amount/hours must be integers"}, 400)
        if not (1 <= amount <= 500) or not (1 <= hours <= 24 * 14):
            return _json(req, {"error": "amount 1-500, hours 1-336"}, 400)
        out = _mint_code(db, amount, hours, str(data.get("note") or "")[:200])
        return _json(req, out)

    booking_id = str(data.get("booking_id") or "")
    ref = db.collection("bookings").document(booking_id)
    snap = ref.get()
    if not snap.exists:
        return _json(req, {"error": "booking not found"}, 404)
    b = snap.to_dict()
    log = {"at": now, "by": who, "action": action}

    try:
        if action == "payment_link":
            zoho = _zoho()
            if b.get("status") in ("awaiting_payment", "signed"):
                amount = b.get("invoice_amount") or (b.get("pif_total") if b.get("payment_option") == "pif" else b.get("retainer"))
                link = zoho.create_payment_link(
                    amount=amount, description=f"Retainer — {b['package_name']} — {b['event_date']}",
                    email=b["email"], reference_id=f"{booking_id}-retainer-{int(now.timestamp())}",
                    phone=b.get("phone", ""), return_url="https://ataviaweddings.com/book/thank-you",
                    meta={"booking_id": booking_id, "kind": "retainer"})
                ref.update({"zoho_payment_link_id": link["payment_link_id"],
                            "zoho_payment_link_url": link.get("url"),
                            "status": "awaiting_payment",
                            "admin_last_action": log})
                emails.payment_nudge(RESEND_API_KEY.value, b, pay_url=link.get("url"))
                return _json(req, {"ok": True, "url": link.get("url"), "kind": "retainer", "amount": amount})
            if b.get("status") == "confirmed" and not b.get("balance_paid_at") and b.get("payment_option") == "standard":
                link = zoho.create_payment_link(
                    amount=b["balance"], description=f"Remaining balance — {b['package_name']} — {b['event_date']}",
                    email=b["email"], reference_id=f"{booking_id}-balance-{int(now.timestamp())}",
                    phone=b.get("phone", ""), return_url="https://ataviaweddings.com/book/thank-you",
                    meta={"booking_id": booking_id, "kind": "balance"})
                ref.update({"balance_payment_link_id": link["payment_link_id"],
                            "balance_payment_link_url": link.get("url"),
                            "balance_link_sent_at": firestore.SERVER_TIMESTAMP,
                            "admin_last_action": log})
                return _json(req, {"ok": True, "url": link.get("url"), "kind": "balance", "amount": b["balance"]})
            return _json(req, {"error": "nothing is owed on this booking"}, 400)

        if action == "retry_balance":
            if b.get("status") != "confirmed" or b.get("balance_paid_at") or b.get("payment_option") != "standard":
                return _json(req, {"error": "no unpaid balance to charge"}, 400)
            pm_id, cust_id = b.get("zoho_payment_method_id"), b.get("zoho_customer_id")
            if not (pm_id and cust_id):
                return _json(req, {"error": "no card on file — send a payment link instead"}, 400)
            zoho = _zoho()
            tx = zoho.charge_saved_method(
                cust_id, pm_id, b["balance"],
                f"Remaining balance — {b['package_name']} — {b['event_date']}",
                meta={"booking_id": booking_id, "kind": "balance"}, descriptor=STATEMENT_DESCRIPTOR)
            if tx.get("status") != "succeeded":
                attempts = b.get("balance_attempts", 0) + 1
                err = f"status={tx.get('status')} {tx.get('failure_code', '')}"
                ref.update({"balance_attempts": attempts, "balance_last_error": err, "admin_last_action": log})
                return _json(req, {"error": err, "attempts": attempts}, 402)
            ref.update({"balance_paid_at": firestore.SERVER_TIMESTAMP,
                        "balance_payment_id": tx.get("payment_id"), "admin_last_action": log})
            return _json(req, {"ok": True, "payment_id": tx.get("payment_id"), "amount": b["balance"]})

        if action == "resend_contract":
            if not b.get("signwell_document_id") or b.get("signed_at"):
                return _json(req, {"error": "nothing to sign"}, 400)
            sw = SignWell(SIGNWELL_API_KEY.value, test_mode=TEST_MODE)
            doc = sw.get_document(b["signwell_document_id"])
            url = (doc.get("recipients") or [{}])[0].get("signing_url")
            if not url:
                return _json(req, {"error": "SignWell returned no signing link"}, 502)
            emails.signature_nudge(RESEND_API_KEY.value, b, url)
            ref.update({"admin_last_action": log, "sig_resent_at": firestore.SERVER_TIMESTAMP})
            return _json(req, {"ok": True, "url": url})

        if action == "resend_questionnaire":
            link = _q_link(booking_id, GRATUITY_SECRET.value)
            days = None
            try:
                ev = datetime.strptime(b["event_date_raw"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                days = max(0, (ev - now).days)
            except Exception:
                pass
            emails.questionnaire_reminder(RESEND_API_KEY.value, b, link, days if days is not None else 30)
            ref.update({"admin_last_action": log, "q_resent_at": firestore.SERVER_TIMESTAMP})
            return _json(req, {"ok": True, "url": link})

        if action == "send_gratuity":
            link = ("https://ataviaweddings.com/gratuity"
                    f"?b={booking_id}&t={_gratuity_token(booking_id, GRATUITY_SECRET.value)}")
            emails.gratuity_invite(RESEND_API_KEY.value, b, link)
            ref.update({"gratuity_invite_sent_at": firestore.SERVER_TIMESTAMP, "admin_last_action": log})
            return _json(req, {"ok": True, "url": link})

        if action == "cancel":
            reason = str(data.get("reason") or "")[:300]
            zoho = _zoho()
            for key in ("zoho_payment_link_id", "balance_payment_link_id"):
                if b.get(key):
                    try:
                        zoho.cancel_payment_link(b[key])
                    except Exception as e:
                        print(f"cancel link {b[key]}: {e}")
            ref.update({"status": "cancelled", "cancelled_at": firestore.SERVER_TIMESTAMP,
                        "cancel_reason": reason, "status_before_cancel": b.get("status"),
                        "admin_last_action": log})
            return _json(req, {"ok": True})

        if action == "refund":
            try:
                amount = round(float(data.get("amount") or 0), 2)
            except ValueError:
                return _json(req, {"error": "bad amount"}, 400)
            which = str(data.get("payment") or "retainer")
            pid = b.get("balance_payment_id") if which == "balance" else b.get("zoho_payment_id")
            if not pid:
                return _json(req, {"error": f"no Zoho payment id on file for the {which}"}, 400)
            if not (1 <= amount <= 10000):
                return _json(req, {"error": "amount out of range"}, 400)
            zoho = _zoho()
            rf = zoho.refund(pid, amount, description=str(data.get("reason") or f"Refund — {b['client_names']}")[:200])
            entry = {"at": now, "amount": amount, "payment": which, "refund_id": rf.get("refund_id"),
                     "status": rf.get("status"), "by": who, "reason": str(data.get("reason") or "")[:300]}
            ref.update({"refunds": firestore.ArrayUnion([entry]), "admin_last_action": log})
            return _json(req, {"ok": True, "refund_id": rf.get("refund_id"), "status": rf.get("status")})

        if action == "mark_paid":
            # Card was run by hand (Zoho dashboard, phone, etc.). Record it and
            # void any open link so the couple can't pay twice.
            which = str(data.get("payment") or "balance")
            pid = str(data.get("payment_id") or "").strip()[:80]
            note = str(data.get("note") or "")[:300]
            zoho = _zoho()
            upd = {"admin_last_action": log}
            if which == "balance":
                if b.get("balance_paid_at"):
                    return _json(req, {"error": "balance is already marked paid"}, 400)
                if b.get("payment_option") == "pif" or b.get("status") != "confirmed":
                    return _json(req, {"error": "no balance is due on this booking"}, 400)
                upd.update({"balance_paid_at": firestore.SERVER_TIMESTAMP,
                            "balance_payment_id": pid or "manual",
                            "balance_paid_manually": True, "balance_manual_note": note})
                link_key = "balance_payment_link_id"
            else:
                if b.get("deposit_paid_at") or b.get("status") == "confirmed":
                    return _json(req, {"error": "retainer is already marked paid"}, 400)
                if not b.get("signed_at"):
                    return _json(req, {"error": "contract isn't signed yet"}, 400)
                amount = b.get("invoice_amount") or (b.get("pif_total") if b.get("payment_option") == "pif" else b.get("retainer"))
                upd.update({"status": "confirmed", "deposit_paid_at": firestore.SERVER_TIMESTAMP,
                            "zoho_payment_id": pid or "manual", "invoice_amount": amount,
                            "charged_on_file": False, "deposit_paid_manually": True, "deposit_manual_note": note})
                if b.get("payment_option") == "pif":
                    upd["balance_paid_at"] = firestore.SERVER_TIMESTAMP
                else:
                    try:
                        upd["balance_due_at"] = _compute_balance_due(
                            datetime.strptime(b["event_date_raw"], "%Y-%m-%d").replace(tzinfo=timezone.utc), now)
                    except Exception:
                        pass
                link_key = "zoho_payment_link_id"
            voided = False
            if b.get(link_key):
                try:
                    zoho.cancel_payment_link(b[link_key]); voided = True
                except Exception as e:
                    print(f"cancel link {b[link_key]}: {e}")
            ref.update(upd)
            if which != "balance" and b.get("payment_option") != "pif":
                pass
            emails.notify_owner(RESEND_API_KEY.value, OWNER_EMAIL,
                                f"MARKED PAID MANUALLY — {b['client_names']} — {which}",
                                [f"Booking {booking_id} {which} marked paid by {who}.",
                                 f"Zoho payment: {pid or '(none given)'}", f"Note: {note or '—'}",
                                 "Open payment link voided." if voided else "No open payment link."])
            return _json(req, {"ok": True, "voided_link": voided})

        return _json(req, {"error": f"unknown action {action}"}, 400)
    except Exception as e:
        print(f"admin_action {action} {booking_id}: {e}")
        return _json(req, {"error": str(e)[:400]}, 500)


# =============================================================== ical_feed ==
def _ics_escape(t):
    return str(t or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


@https_fn.on_request(region=REGION, secrets=[GRATUITY_SECRET])
def ical_feed(req: https_fn.Request) -> https_fn.Response:
    """Private calendar subscription (Google/Apple Calendar). URL carries a
    token derived from GRATUITY_SECRET; get it from the dashboard's
    'Subscribe in calendar' button. Weddings only; times are the coverage
    window, floating in the venue's local time."""
    tok = hmac.new(GRATUITY_SECRET.value.encode(), b"ical-feed", hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(str(req.args.get("t") or ""), tok):
        return https_fn.Response("forbidden", status=403)
    db = firestore.client()
    from google.cloud.firestore_v1.base_query import FieldFilter
    rows = (db.collection("bookings")
              .where(filter=FieldFilter("status", "in", ["confirmed", "awaiting_payment", "pending_signature"]))
              .get())
    out = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Atavia Weddings//Bookings//EN",
           "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "X-WR-CALNAME:Atavia Weddings",
           "X-WR-CALDESC:Booked weddings from the Atavia dashboard"]
    for snap in rows:
        b = snap.to_dict()
        if b.get("test_mode") or not b.get("event_date_raw"):
            continue
        d = b["event_date_raw"].replace("-", "")
        def hm(v, default):
            v = (v or "").strip()
            return v.replace(":", "")[:4] if re.match(r"^\d{2}:\d{2}$", v) else default
        start, end = hm(b.get("start_time"), "1200"), hm(b.get("end_time"), "2200")
        status = {"confirmed": "", "awaiting_payment": "[RETAINER UNPAID] ", "pending_signature": "[UNSIGNED] "}[b["status"]]
        q = "questionnaire in" if b.get("questionnaire_submitted_at") else "NO questionnaire"
        addons = []
        if b.get("second_shooter"): addons.append("second shooter")
        if b.get("extra_hours"): addons.append(f"+{b['extra_hours']}h")
        desc = (f"{b.get('package_name','')} · {b.get('coverage_hours','?')}h {b.get('service_type','')}"
                f"{' · ' + ', '.join(addons) if addons else ''}\n"
                f"{b.get('email','')} · {b.get('phone','')}\n"
                f"Ceremony: {b.get('ceremony_venue','')}\n"
                f"Reception: {b.get('reception_venue','') or 'same / not given'}\n"
                f"Guests: {b.get('guest_count','')} · {q}\n"
                f"https://admin.ataviaweddings.com/?open={snap.id}")
        out += ["BEGIN:VEVENT", f"UID:{snap.id}@ataviaweddings.com",
                f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
                f"DTSTART:{d}T{start}00", f"DTEND:{d}T{end}00",
                f"SUMMARY:{_ics_escape(status + b.get('client_names','Wedding') + ' — ' + b.get('package_name',''))}",
                f"LOCATION:{_ics_escape(b.get('ceremony_venue',''))}",
                f"DESCRIPTION:{_ics_escape(desc)}",
                "END:VEVENT"]
    out.append("END:VCALENDAR")
    return https_fn.Response("\r\n".join(out) + "\r\n", status=200,
                             headers={"Content-Type": "text/calendar; charset=utf-8",
                                      "Cache-Control": "no-cache"})


# ========================================================= inquiry_webhook ==
@https_fn.on_request(region=REGION, secrets=[RESEND_API_KEY])
def inquiry_webhook(req: https_fn.Request) -> https_fn.Response:
    """Stores /contact inquiries in Firestore `inquiries` so the dashboard's
    leads funnel sees them. Accepts either Formspree's webhook JSON
    ({"submission": {...}}) or a direct JSON/form POST from contact.html."""
    if req.method == "OPTIONS":
        return https_fn.Response("", status=204, headers=_cors(req))
    if req.method != "POST":
        return https_fn.Response("POST only", status=405)
    body = req.get_json(silent=True) or {}
    sub = body.get("submission") if isinstance(body.get("submission"), dict) else (body or req.form.to_dict())
    if not sub or sub.get("_gotcha"):
        return _json(req, {"ok": True})
    g = lambda *ks: next((str(sub[k]).strip()[:500] for k in ks if sub.get(k)), "")
    email = g("email", "Email").lower()
    if not email or "@" not in email:
        return _json(req, {"error": "email required"}, 400)
    db = firestore.client()
    doc = {"first_name": g("first_name", "First Name", "firstName"),
           "last_name": g("last_name", "Last Name", "lastName"),
           "email": email, "phone": g("phone", "Phone"),
           "event_date_raw": g("wedding_date", "Wedding Date", "date"),
           "found_us": g("found_us", "Where did you find us", "source"),
           "package": g("package", "Package"),
           "venue": g("venue", "Venue"), "venue_page": g("venue_page", "Venue Page"),
           "landing": g("landing_page", "Landing Page"), "referrer": g("referrer", "Referrer"),
           "message": g("message", "Message", "notes")[:2000],
           "sid": g("sid") if _SID_RE.match(g("sid") or "") else "",
           "source": "formspree" if "submission" in body else "site",
           "status": "new", "created_at": firestore.SERVER_TIMESTAMP}
    ref = db.collection("inquiries").add(doc)[1]
    if doc["sid"]:
        _link_session(db, doc["sid"], f"{doc['first_name']} {doc['last_name']}".strip(), email)
    return _json(req, {"ok": True, "id": ref.id})


# ============================================================ daily digest ==
def _send_daily_digest(db):
    """7 AM owner email: this week's weddings, money due, overdue questionnaires,
    stalled bookings, and what came in overnight."""
    now = datetime.now(timezone.utc)
    today = now.date()
    bookings = [s.to_dict() | {"_id": s.id} for s in db.collection("bookings").get()]
    live = [b for b in bookings if not b.get("test_mode") and b.get("event_date_raw")]
    def ev(b):
        try: return datetime.strptime(b["event_date_raw"], "%Y-%m-%d").date()
        except Exception: return None
    week = sorted([b for b in live if b["status"] == "confirmed" and ev(b) and 0 <= (ev(b) - today).days <= 7], key=ev)
    charging = [b for b in live if b["status"] == "confirmed" and b.get("payment_option") == "standard"
                and not b.get("balance_paid_at") and b.get("balance_due_at") and b["balance_due_at"].date() <= today]
    declined = [b for b in charging if b.get("balance_attempts", 0) > 0]
    q_late = [b for b in live if b["status"] == "confirmed" and not b.get("questionnaire_submitted_at")
              and ev(b) and 0 <= (ev(b) - today).days <= 21]
    unsigned = [b for b in live if b["status"] == "pending_signature"]
    unpaid = [b for b in live if b["status"] == "awaiting_payment"]
    since = now - timedelta(hours=24)
    new_book = [b for b in live if b.get("created_at") and b["created_at"] >= since]
    try:
        from google.cloud.firestore_v1.base_query import FieldFilter
        new_inq = [s.to_dict() for s in db.collection("inquiries").where(filter=FieldFilter("created_at", ">=", since)).get()]
        new_leads = [s.to_dict() for s in db.collection("leads").where(filter=FieldFilter("created_at", ">=", since)).get()]
    except Exception as e:
        print(f"digest queries: {e}"); new_inq, new_leads = [], []
    post = [b for b in live if b["status"] == "confirmed" and ev(b) and ev(b) < today
            and (b.get("production") or {}).get("stage") not in ("gallery_sent", "delivered")]

    def line(b, extra=""):
        return f"{b.get('event_date','')} — {b.get('client_names','')} — {b.get('package_name','')}{(' — ' + extra) if extra else ''}"
    lines = []
    lines.append(f"<b>Weddings in the next 7 days ({len(week)})</b>")
    lines += [line(b, ("questionnaire in" if b.get("questionnaire_submitted_at") else "NO QUESTIONNAIRE")) for b in week] or ["none"]
    lines.append(f"<b>Balances charging today / overdue ({len(charging)})</b>")
    lines += [line(b, f"${b.get('balance',0):,}" + (f" — DECLINED ×{b.get('balance_attempts')}" if b.get("balance_attempts") else "")) for b in charging] or ["none"]
    lines.append(f"<b>Questionnaires overdue — wedding within 21 days ({len(q_late)})</b>")
    lines += [line(b) for b in q_late] or ["none"]
    lines.append(f"<b>Stalled — unsigned {len(unsigned)}, retainer unpaid {len(unpaid)}</b>")
    lines += [line(b, "unsigned") for b in unsigned] + [line(b, "retainer unpaid") for b in unpaid] or ["none"]
    lines.append(f"<b>Post-production open ({len(post)})</b>")
    lines += [line(b, ((b.get("production") or {}).get("stage") or "awaiting footage").replace("_", " ")) for b in post[:10]] or ["none"]
    lines.append(f"<b>Overnight</b>")
    lines.append(f"{len(new_book)} new booking(s), {len(new_leads)} started booking, {len(new_inq)} inquiry(ies)")
    lines += [line(b) for b in new_book]
    lines += [f"inquiry — {i.get('first_name','')} {i.get('last_name','')} — {i.get('email','')} — {i.get('package','')} — {i.get('event_date_raw','')}" for i in new_inq]
    lines.append('<a href="https://admin.ataviaweddings.com/">Open the dashboard</a>')
    attention = len(declined) + len(q_late) + len(unsigned) + len(unpaid)
    emails.notify_owner(RESEND_API_KEY.value, OWNER_EMAIL,
                        f"Atavia today — {len(week)} wedding(s) this week, {attention} need attention",
                        lines)
