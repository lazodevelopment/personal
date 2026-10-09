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
# Processor flag (v11 · 2026-10-03 — Whop path behind a flag):
#   PAYMENT_PROCESSOR env var: "zoho" (default) | "whop". Decides which
#   processor NEW bookings use. Every booking records its own `processor`,
#   and every later charge / link / refund / cancel reads that field, so
#   flipping the flag never moves an existing booking off the processor that
#   holds its card. Whop mechanics (lib/whop.py):
#     /book page mounts Whop CardElement (mode=setup) -> whop_setup turns the
#       confirmation token into a setup intent -> payment_method + member ids
#     signwell_webhook -> Whop off-session charge; fallback -> Whop hosted
#       checkout link, emailed by US (Whop sends nothing)
#     whop_webhook (payment.succeeded / payment.failed) -> confirms link
#       payments and reconciles charges that were still pending
#
# Secrets (set before deploy):
#   firebase functions:secrets:set SIGNWELL_API_KEY
#   firebase functions:secrets:set ZOHO_CLIENT_ID        (api-console.zoho.com, client type ORG)
#   firebase functions:secrets:set ZOHO_CLIENT_SECRET
#   firebase functions:secrets:set ZOHO_REFRESH_TOKEN    (one-time OAuth dance, access_type=offline)
#   firebase functions:secrets:set RESEND_API_KEY
#   firebase functions:secrets:set PROMO_ADMIN_KEY   (any long random string; used to issue codes)
#   firebase functions:secrets:set GRATUITY_SECRET     (any long random string)
#   firebase functions:secrets:set WHOP_API_KEY        (whop.com/dashboard/developer, account API key)
#   firebase functions:secrets:set WHOP_WEBHOOK_SECRET (same page, webhook "Secret" column, ws_...)
# =============================================================================

import hashlib
import time
import traceback
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
from lib.whop import Whop
from lib import emails
from lib.questionnaire_schema import ALL_FIELD_IDS, SUMMARY_LAYOUT

firebase_admin.initialize_app()

# ----------------------------------------------------------------- config ---
SIGNWELL_API_KEY = SecretParam("SIGNWELL_API_KEY")
ZOHO_CLIENT_ID     = SecretParam("ZOHO_CLIENT_ID")
ZOHO_CLIENT_SECRET = SecretParam("ZOHO_CLIENT_SECRET")
ZOHO_REFRESH_TOKEN = SecretParam("ZOHO_REFRESH_TOKEN")
ZOHO_SECRETS = [ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_REFRESH_TOKEN]
WHOP_API_KEY        = SecretParam("WHOP_API_KEY")
WHOP_WEBHOOK_SECRET = SecretParam("WHOP_WEBHOOK_SECRET")
WHOP_SECRETS = [WHOP_API_KEY, WHOP_WEBHOOK_SECRET]
# Every payment-touching function mounts both sets: a booking made under one
# processor is still charged / refunded under it after the flag flips.
PAY_SECRETS = [*ZOHO_SECRETS, *WHOP_SECRETS]
RESEND_API_KEY   = SecretParam("RESEND_API_KEY")
GRATUITY_SECRET  = SecretParam("GRATUITY_SECRET")
PROMO_ADMIN_KEY  = SecretParam("PROMO_ADMIN_KEY")

TEST_MODE       = False  # PRODUCTION
ZOHO_ACCOUNT_ID  = "937366965"                 # Danbren Media LLC (Zoho Payments)
WHOP_ACCOUNT_ID  = os.environ.get("WHOP_ACCOUNT_ID", "")   # biz_... (Danbren Media on Whop); also in /book page JS
# Which processor NEW bookings use. Existing bookings keep their own
# `processor` field forever. Set with: gcloud functions deploy ... --update-env-vars PAYMENT_PROCESSOR=whop
PAYMENT_PROCESSOR = (os.environ.get("PAYMENT_PROCESSOR") or "zoho").strip().lower()
if PAYMENT_PROCESSOR not in ("zoho", "whop"):
    PAYMENT_PROCESSOR = "zoho"
SITE_HOST = "ataviaweddings.com"
# Whop refuses no-charge card saves from guest buyers on this company (risk
# engine, 2026-10-06), so the Whop flow collects the retainer / PIF total at
# reservation through a paid checkout, which also stores the card for the
# balance. Set False to return to the save-only setup checkout.
WHOP_CHARGE_AT_RESERVATION = True
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
    """Balance is due 14 calendar days after booking/signing (changed from
    business days 2026-10-01). If the Event is sooner than that, the balance
    falls due the day before the Event (never after it), and never earlier than now."""
    from datetime import timezone as _tz
    due = now + timedelta(days=RULES["balance_due_days_from_booking"])
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


def _whop():
    # Read the env directly: SecretParam.value logs a warning when the secret
    # is not mounted, and a Zoho-only deploy legitimately never mounts it.
    key = os.environ.get("WHOP_API_KEY") or ""
    if not (key and WHOP_ACCOUNT_ID):
        raise RuntimeError("Whop is not configured (WHOP_API_KEY / WHOP_ACCOUNT_ID)")
    return Whop(WHOP_ACCOUNT_ID, key)


# ---------------------------------------------------------------------------
# Processor indirection. A booking's `processor` field ("zoho" | "whop") is
# fixed at creation and decides which client handles every later call. The
# two clients share method names and return shapes (see lib/whop.py), so the
# callers only need to pick the client and the right Firestore field names:
#   {proc}_payment_method_id / {proc}_customer_id   card on file
#   {proc}_payment_id                               retainer / PIF payment
#   {proc}_payment_link_id / {proc}_payment_link_url retainer / PIF link
# Balance links / payments keep their processor-neutral names
# (balance_payment_link_id, balance_payment_id) as before.
# ---------------------------------------------------------------------------
def _proc(b):
    p = str((b or {}).get("processor") or "zoho").lower()
    return p if p in ("zoho", "whop") else "zoho"


def _pay(proc_or_booking):
    proc = proc_or_booking if isinstance(proc_or_booking, str) \
        else _proc(proc_or_booking)
    return _whop() if proc == "whop" else _zoho()


def _card_ids(b):
    """(payment_method_id, customer_id) for the booking's own processor, or
    ("", "") when there is no card on file."""
    p = _proc(b)
    return (b.get(f"{p}_payment_method_id") or "",
            b.get(f"{p}_customer_id") or "")


def _k(b, suffix):
    """Processor-prefixed Firestore key, e.g. _k(b, 'payment_link_url')."""
    return f"{_proc(b)}_{suffix}"


def _pm_display(pm, proc="zoho"):
    """(brand, last4) from a payment_method dict, for owner emails."""
    if proc == "whop":
        return Whop.pm_display(pm)
    card = (pm or {}).get("card") or {}
    return (str(card.get("brand") or "card")[:20],
            str(card.get("last_four_digits") or "")[:4])


def _record_lead(req, data, name, email, phone, extra):
    """The only trace of a couple who closes the card step. Shared by
    zoho_session and whop_setup; _chase_leads() nudges, book_submit converts."""
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
            **extra,
            "attr_venue": str(data.get("attr_venue") or "")[:200],
            # JC-ATV-ATTR-0927: same attribution the booking carries, so the
            # leads dashboard can say where each booking start came from.
            "attr_venue_url": str(data.get("attr_venue_url") or "")[:300],
            "attr_landing": str(data.get("attr_landing") or "")[:300],
            "attr_referrer": str(data.get("attr_referrer") or "")[:300],
            "client_ip": req.headers.get("X-Forwarded-For", req.remote_addr),
            "sid": str(data.get("sid") or "")[:32],
        })
    except Exception as e:
        print(f"lead record failed (non-fatal): {e}")
    _link_session(firestore.client(), data.get("sid"), name, email)


def _reservation_due(data):
    """Amount the couple pays at reservation under the Whop flow, priced with
    compute_pricing from the same fields book_submit validates. Raises
    ValueError with a user-facing message on bad input."""
    pkg_id = str(data.get("package_id") or "")
    if pkg_id not in PACKAGES:
        raise ValueError("please choose a collection")
    pkg = PACKAGES[pkg_id]
    option = str(data.get("payment_option") or "pif")
    if option not in ("standard", "pif"):
        raise ValueError("invalid payment option")
    if pkg.get("pif_only"):
        option = "pif"
    try:
        event_dt = datetime.strptime(str(data.get("event_date") or ""), "%Y-%m-%d")
    except ValueError:
        raise ValueError("please enter your wedding date")
    days_to_event = (event_dt.date() - datetime.now(timezone.utc).date()).days
    if days_to_event <= 0:
        raise ValueError("event date must be in the future")
    second_shooter = bool(data.get("second_shooter"))
    try:
        extra_hours = int(data.get("extra_hours") or 0)
    except (TypeError, ValueError):
        raise ValueError("extra_hours must be a whole number")
    discount = 0
    raw_code = str(data.get("discount_code") or "").strip().upper()
    if raw_code:
        snap = firestore.client().collection("discount_codes").document(raw_code).get()
        if snap.exists:
            c = snap.to_dict() or {}
            exp = c.get("expires_at")
            if (c.get("active", False) and not c.get("redeemed_by")
                    and not (exp and exp.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc))):
                discount = int(c.get("amount", 0))
    pricing = compute_pricing(pkg_id, second_shooter, extra_hours, discount,
                              days_to_event=days_to_event)
    total = pricing["total"]
    ev_disp = event_dt.strftime("%B %d, %Y")
    if option == "pif":
        amount = total - RULES["pif_discount"]
        kind, title = "pif", f"Paid in full \u2014 {pkg['name']} \u2014 {ev_disp}"
    else:
        amount = RULES["retainer"]
        kind, title = "retainer", f"Retainer \u2014 {pkg['name']} \u2014 {ev_disp}"
    return {"amount": int(amount), "kind": kind, "title": title,
            "package_id": pkg_id, "payment_option": option, "total": total}


# ============================================================= whop_setup ===
@https_fn.on_request(region=REGION, secrets=WHOP_SECRETS)
def whop_setup(req: https_fn.Request) -> https_fn.Response:
    """Whop twin of zoho_session, but the order is reversed: the page has
    ALREADY collected the card in the Whop CardElement (mode=setup) and holds
    a confirmation token. We turn it into a setup intent here, which is what
    saves the method for off-session use. Nothing is charged.

    Returns the setup intent's settled state. status "requires_action" means
    3-D Secure: the page runs handleNextAction(client_secret) and then posts
    the booking; book_submit re-fetches the intent, so a page that lies about
    the outcome gains nothing."""
    if req.method == "OPTIONS":
        return https_fn.Response("", status=204, headers=_cors(req))
    if req.method != "POST":
        return _json(req, {"error": "POST only"}, 405)
    data = req.get_json(silent=True) or {}
    name = str(data.get("client_names") or "").strip()[:100]
    email = str(data.get("email") or "").strip()
    phone = re.sub(r"[^\d+]", "", str(data.get("phone") or ""))[:20]
    token = str(data.get("confirmation_token") or "").strip()
    if not name or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return _json(req, {"error": "name and a valid email are required"}, 400)
    if not token:
        # -- Checkout-configuration path. With WHOP_CHARGE_AT_RESERVATION the
        #    page mounts a PAID checkout for the amount due now (retainer or
        #    PIF total, priced server-side from the same inputs book_submit
        #    will use); Whop charges it and stores the card. Otherwise a
        #    setup-mode (no charge) checkout. Either way book_submit verifies
        #    the resulting payment / setup intent by id.
        due = None
        if WHOP_CHARGE_AT_RESERVATION:
            try:
                due = _reservation_due(data)
            except ValueError as e:
                return _json(req, {"error": str(e)}, 400)
        try:
            w = _whop()
            if due:
                chk = w.create_payment_checkout(
                    due["amount"], due["title"],
                    meta={"source": "reservation", "kind": due["kind"],
                          "client_names": name, "email": email,
                          "package_id": due["package_id"],
                          "payment_option": due["payment_option"]},
                    descriptor=STATEMENT_DESCRIPTOR)
            else:
                chk = w.create_setup_checkout(
                    email=email,
                    meta={"source": SITE_HOST, "client_names": name,
                          "phone": phone, "kind": "booking_card"})
        except Exception as e:
            print(f"whop_setup checkout failed: {e}")
            return _json(req, {"error": "payment setup unavailable"}, 502)
        _record_lead(req, data, name, email, phone,
                     {"processor": "whop",
                      "whop_checkout_id": chk["checkout_id"],
                      "whop_due_now": due["amount"] if due else None,
                      "whop_due_kind": due["kind"] if due else "setup",
                      # the full form, so whop_webhook can finish the booking
                      # if the browser never submits it
                      "reservation_payload": _clean_booking_payload(
                          data.get("booking") if isinstance(data.get("booking"), dict) else {})})
        print(f"whop_setup checkout {chk['checkout_id']} for {email} "
              f"due={due['amount'] if due else 'setup'}")
        return _json(req, {"checkout_id": chk["checkout_id"],
                           "url": chk["url"],
                           "mode": "payment" if due else "setup",
                           "amount": due["amount"] if due else None,
                           "kind": due["kind"] if due else "setup"})
    if not token.startswith("ctok_"):
        return _json(req, {"error": "confirmation_token required"}, 400)
    try:
        si = _whop().create_setup_intent(
            token, email=email,
            meta={"source": "ataviaweddings.com", "client_names": name,
                  "phone": phone},
            return_url="https://ataviaweddings.com/book")
    except Exception as e:
        print(f"whop_setup failed: {e}")
        return _json(req, {"error": "payment setup unavailable"}, 502)

    member_id, pm_id = Whop.setup_ids(si)
    # Always log the outcome: a canceled / failed intent is a normal 200 with
    # no exception, and the page can only show a generic message without this.
    print(f"whop_setup {si.get('id')} status={si.get('status')} "
          f"member={member_id} pm={pm_id} err={Whop.setup_error(si)} "
          f":: {json.dumps(si)[:700]}")
    _record_lead(req, data, name, email, phone,
                 {"processor": "whop",
                  "whop_setup_intent_id": si.get("id"),
                  "whop_customer_id": member_id})
    brand, last4 = Whop.pm_display(si.get("payment_method"))
    return _json(req, {"setup_intent_id": si.get("id"),
                       "status": si.get("status"),
                       "client_secret": si.get("client_secret"),
                       "customer_id": member_id,
                       "payment_method_id": pm_id,
                       "card_brand": brand, "card_last4": last4,
                       "error_message": Whop.setup_error(si) or None})


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
    _record_lead(req, data, name, email, phone,
                 {"processor": "zoho", "zoho_customer_id": cust["customer_id"]})

    return _json(req, {"customer_id": cust["customer_id"],
                       "payment_method_session_id":
                           sess["payment_method_session_id"]})


# ============================================================ book_submit ===
BOOKING_FIELDS = (REQUIRED_FIELDS + OPTIONAL_FIELDS
                  + ["partner1_name", "partner2_name", "second_shooter",
                     "extra_hours", "discount_code", "attr_venue",
                     "attr_venue_url", "attr_landing", "attr_referrer", "sid"])


def _clean_booking_payload(raw):
    """The booking form as the page submits it, minus anything unexpected.
    Stored on the lead at whop_setup so the webhook can finish the booking."""
    out = {}
    for k in BOOKING_FIELDS:
        if k not in (raw or {}):
            continue
        v = raw[k]
        if k == "second_shooter":
            out[k] = bool(v)
        elif k == "extra_hours":
            try:
                out[k] = int(v or 0)
            except (TypeError, ValueError):
                out[k] = 0
        elif k == "agree_terms":
            out[k] = v is True
        else:
            out[k] = str(v if v is not None else "")[:300]
    return out


def _res(obj, code=200):
    return obj, code


def _book_safely(data, client_ip, source):
    """Run _create_booking; on any failure undo the discount redemption and
    release the reservation lock so a retry (page, webhook, finish link) can
    complete it. Returns (obj, status)."""
    state = {}
    try:
        obj, code = _create_booking(data, client_ip, source, state)
    except Exception as e:
        print(f"BOOKING CRASHED ({source}): {e}\n{traceback.format_exc()[-1500:]}")
        obj, code = ({"error": "We couldn't finish your booking just now. Please "
                               "try again in a minute. If you've already paid, "
                               "you won't be charged again."}, 500)
    if code >= 400:
        db = firestore.client()
        if state.get("code_redeemed") and state.get("booking_id"):
            try:
                cref = db.collection("discount_codes").document(state["code_redeemed"])
                c = (cref.get().to_dict() or {})
                if c.get("redeemed_by") == state["booking_id"]:
                    cref.update({"redeemed_by": None, "redeemed_at": None})
                    print(f"rolled back code {state['code_redeemed']}")
            except Exception as e2:
                print(f"code rollback failed: {e2}")
        if state.get("lock_ref") is not None:
            try:
                state["lock_ref"].delete()
            except Exception as e3:
                print(f"lock release failed: {e3}")
    return obj, code


def _existing_booking_response(b0, whop_pay_id):
    signing_url = None
    try:
        doc0 = SignWell(SIGNWELL_API_KEY.value, test_mode=TEST_MODE).get_document(
            b0.get("signwell_document_id"))
        signing_url = (doc0.get("recipients") or [{}])[0].get("signing_url")
    except Exception as e0:
        print(f"existing booking: signing url fetch failed: {e0}")
    print(f"existing booking for payment {whop_pay_id} -> {b0.get('booking_id')}")
    return _res({"ok": True, "booking_id": b0.get("booking_id"),
                 "signing_url": signing_url, "duplicate": True,
                 "next": "sign_now_or_check_email"})


def _find_booking_by_payment(whop_pay_id):
    from google.cloud.firestore_v1.base_query import FieldFilter as _FFb
    q = (firestore.client().collection("bookings")
         .where(filter=_FFb("whop_payment_id", "==", whop_pay_id)).limit(1).get())
    return q[0].to_dict() if q else None


@https_fn.on_request(region=REGION, secrets=[SIGNWELL_API_KEY, *PAY_SECRETS, RESEND_API_KEY],
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
    if not isinstance(data, dict):
        return _json(req, {"error": "invalid JSON"}, 400)
    obj, code = _book_safely(data, req.headers.get("X-Forwarded-For", req.remote_addr),
                             "page")
    return _json(req, obj, code)


def _create_booking(data, client_ip, source="page", state=None):
    """Validate, price, create the booking + contract. Shared by book_submit
    (the page) and whop_webhook (server-side completion of a paid
    reservation). Returns (obj, status); never touches the request object."""
    state = state if state is not None else {}

    # -- validate -------------------------------------------------------------
    missing = [f for f in REQUIRED_FIELDS if not data.get(f)]
    if missing:
        return _res({"error": "missing fields", "fields": missing}, 400)
    if data["package_id"] not in PACKAGES:
        return _res({"error": "unknown package"}, 400)
    if data["payment_option"] not in ("standard", "pif"):
        return _res({"error": "invalid payment option"}, 400)
    if PACKAGES[data["package_id"]].get("pif_only"):
        data["payment_option"] = "pif"        # The Ceremony: paid in full, no plan
    if data.get("agree_terms") is not True:
        return _res({"error": "terms must be accepted"}, 400)
    try:
        event_dt = datetime.strptime(data["event_date"], "%Y-%m-%d")
        if event_dt.date() <= datetime.now().date():
            return _res({"error": "event date must be in the future"}, 400)
    except ValueError:
        return _res({"error": "event_date must be YYYY-MM-DD"}, 400)

    # -- add-ons (server-side pricing; the client-side total is never trusted) --
    second_shooter = data.get("second_shooter", False)
    if not isinstance(second_shooter, bool):
        return _res({"error": "second_shooter must be true/false"}, 400)
    try:
        extra_hours = int(data.get("extra_hours") or 0)
    except (TypeError, ValueError):
        return _res({"error": "extra_hours must be a whole number"}, 400)
    if not (0 <= extra_hours <= RULES["max_extra_hours"]):
        return _res({"error": f"extra_hours must be 0-"
                                    f"{RULES['max_extra_hours']}"}, 400)

    # -- card on file (tokenized client-side by the Zoho widget; the PAN never
    #    reaches our servers, which keeps us in PCI SAQ-A). All three ids must
    #    be present and the session must really hold that method for that
    #    customer, or we drop it and fall back to the payment-link flow at
    #    signature. ---------------------------------------------------------
    card_brand = str(data.get("card_brand") or "")[:20]
    card_last4 = re.sub(r"\D", "", str(data.get("card_last4") or ""))[:4]
    whop_si_id = str(data.get("whop_setup_intent_id") or "").strip()
    whop_chk_id = str(data.get("whop_checkout_id") or "").strip()
    whop_pay_id = str(data.get("whop_payment_id") or "").strip()
    prepaid = None                      # set when a Whop reservation payment verifies
    if whop_pay_id:
        # -- One booking per payment. The page (onComplete + after the
        #    redirect), the ?finish= link and whop_webhook can all try to
        #    create it; the first to take the lock does, the rest wait for it.
        b0 = _find_booking_by_payment(whop_pay_id)
        if b0:
            return _existing_booking_response(b0, whop_pay_id)
        lock_ref = firestore.client().collection("reservation_locks").document(whop_pay_id)
        got_lock = False
        try:
            lock_ref.create({"at": datetime.now(timezone.utc), "source": source})
            got_lock = True
        except Exception:
            lk = (lock_ref.get().to_dict() or {})
            at = lk.get("at")
            if at and (datetime.now(timezone.utc) - at).total_seconds() > 120:
                lock_ref.set({"at": datetime.now(timezone.utc), "source": source,
                              "took_over_from": lk.get("source")})
                got_lock = True
                print(f"stale reservation lock taken over for {whop_pay_id}")
        if not got_lock:
            for _ in range(10):
                time.sleep(2)
                b0 = _find_booking_by_payment(whop_pay_id)
                if b0:
                    return _existing_booking_response(b0, whop_pay_id)
            print(f"booking for {whop_pay_id} still in progress elsewhere ({source})")
            return _res({"ok": True, "pending": True, "next": "check_email"}, 202)
        state["lock_ref"] = lock_ref
        try:
            live = _whop().get_payment(whop_pay_id)
        except Exception as e:
            print(f"whop payment verification failed: {e}")
            return _res({"error": "We couldn't confirm your payment yet. Please try again in a moment."}, 502)
        if str(live.get("status", "")).lower() != "paid":
            return _res({"error": f"Payment is {live.get('status')}, not paid yet. Please try again in a moment."}, 402)
        live_chk = str(live.get("checkout_configuration_id") or "")
        if whop_chk_id and live_chk and live_chk != whop_chk_id:
            print(f"REJECTED payment {whop_pay_id}: checkout {live_chk} != {whop_chk_id}")
            return _res({"error": "payment does not match this reservation"}, 400)
        pmeta = live.get("metadata") or {}
        if str(pmeta.get("source") or "") == "reservation":
            pm_email = str(pmeta.get("email") or "").strip().lower()
            if pm_email and pm_email != str(data.get("email") or "").strip().lower():
                print(f"REJECTED payment {whop_pay_id}: email {data.get('email')} != {pm_email}")
                return _res({"error": "Please use the same email address you paid with.",
                             "field": "email"}, 400)
            if pmeta.get("package_id") in PACKAGES:
                data["package_id"] = pmeta["package_id"]
            if pmeta.get("payment_option") in ("standard", "pif"):
                data["payment_option"] = pmeta["payment_option"]
        member_id, pm_live = Whop.payment_ids(live)
        prepaid = {"payment_id": whop_pay_id, "amount": Whop.payment_amount(live),
                   "member_id": member_id, "payment_method_id": pm_live,
                   "checkout_id": live_chk or whop_chk_id,
                   "card_brand": str(live.get("card_brand") or "")[:20],
                   "card_last4": str(live.get("card_last4") or "")[:4]}
    if whop_si_id:
        # -- Idempotency: the Whop checkout fires onComplete AND redirects the
        #    page to returnUrl, and both paths submit the booking. A second
        #    submit for the same setup intent returns the existing booking
        #    instead of sending the couple two contracts. -------------------
        try:
            from google.cloud.firestore_v1.base_query import FieldFilter as _FF0
            dup = (firestore.client().collection("bookings")
                   .where(filter=_FF0("whop_setup_intent_id", "==", whop_si_id))
                   .limit(1).get())
            if dup:
                b0 = dup[0].to_dict()
                signing_url = None
                try:
                    doc0 = SignWell(SIGNWELL_API_KEY.value, test_mode=TEST_MODE).get_document(b0.get("signwell_document_id"))
                    signing_url = (doc0.get("recipients") or [{}])[0].get("signing_url")
                except Exception as e0:
                    print(f"duplicate submit: signing url fetch failed: {e0}")
                print(f"duplicate submit for setup intent {whop_si_id} -> {b0.get('booking_id')}")
                return _res({"ok": True, "booking_id": b0.get("booking_id"),
                                   "signing_url": signing_url, "duplicate": True,
                                   "next": "sign_now_or_check_email"})
        except Exception as e:
            print(f"duplicate check failed (continuing): {e}")
        # -- Whop: the page posts the setup intent id; the intent itself is
        #    the source of truth for which method and member it saved. A
        #    whop booking is recorded as such even if verification fails, so
        #    it is never charged through Zoho by mistake. -----------------
        proc = "whop"
        pm_id = cust_id = ""
        try:
            si = _whop().get_setup_intent(whop_si_id)
            member_id, saved = Whop.setup_ids(si)
            if si.get("status") != "succeeded" or not (member_id and saved):
                print(f"REJECTED whop setup {whop_si_id}: status="
                      f"{si.get('status')} member={member_id} pm={saved}")
            else:
                pm_id, cust_id = saved, member_id
                if not (card_brand and card_last4):
                    card_brand, card_last4 = Whop.pm_display(
                        si.get("payment_method"))
        except Exception as e:
            print(f"whop setup verification unavailable: {e}")
    elif prepaid:
        proc = "whop"
        pm_id, cust_id = prepaid["payment_method_id"] or "", prepaid["member_id"] or ""
        card_brand = card_brand or prepaid["card_brand"]
        card_last4 = card_last4 or prepaid["card_last4"]
        whop_chk_id = whop_chk_id or prepaid["checkout_id"]
    else:
        proc = "zoho"
        pm_id = str(data.get("zoho_payment_method_id") or "").strip()
        cust_id = str(data.get("zoho_customer_id") or "").strip()
        sess_id = str(data.get("zoho_pm_session_id") or "").strip()
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
            # No card at all: the booking still belongs to whichever
            # processor is live, so its fallback link goes through it.
            proc = PAYMENT_PROCESSOR

    pkg = PACKAGES[data["package_id"]]
    now = datetime.now(timezone.utc)
    db = firestore.client()
    booking_ref = db.collection("bookings").document()
    booking_id = booking_ref.id
    state["booking_id"] = booking_id

    # -- a card was saved: the zoho_session / whop_setup lead is now a booking --
    lead_key, lead_val = (("whop_checkout_id", whop_chk_id) if whop_chk_id
                          else ("whop_setup_intent_id", whop_si_id) if whop_si_id
                          else ("zoho_customer_id", cust_id))
    if lead_val:
        try:
            from google.cloud.firestore_v1.base_query import FieldFilter as _FF
            for lead in (db.collection("leads")
                           .where(filter=_FF(lead_key, "==", lead_val))
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
        if code_err and prepaid:
            # The payment was priced with this code at the card step; honour
            # it rather than refuse a booking that is already paid for.
            try:
                csnap = code_ref.get()
                amt = int((csnap.to_dict() or {}).get("amount", 0)) if csnap.exists else 0
            except Exception:
                amt = 0
            print(f"prepaid booking keeps code {raw_code} (${amt}) despite: {code_err}")
            code_err = None
        elif not code_err:
            state["code_redeemed"] = raw_code
        if code_err:
            return _res({"error": code_err,
                               "field": "discount_code"}, 400)
        discount, discount_code = amt, raw_code

    p1 = (data.get("partner1_name") or "").strip()
    p2 = (data.get("partner2_name") or "").strip()
    if p2 and p1.lower() == p2.lower():
        return _res({"error": "Partner 1 and Partner 2 names must be different. If you are booking solo, leave Partner 2 blank."}, 400)
    days_to_event = (event_dt.date() - datetime.now(timezone.utc).date()).days
    try:
        pricing = compute_pricing(pkg["id"], second_shooter, extra_hours,
                                  discount, days_to_event=days_to_event)
    except ValueError as e:        # e.g. add-ons on The Ceremony
        return _res({"error": str(e)}, 400)
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
        "processor": proc,
        f"{proc}_payment_method_id": pm_id or None,
        f"{proc}_customer_id": cust_id or None,
        "whop_setup_intent_id": whop_si_id or None,
        "whop_checkout_id": whop_chk_id or None,
        **({"whop_payment_id": prepaid["payment_id"],
            "deposit_paid_at": now,
            "invoice_amount": int(round(prepaid["amount"])),
            "charged_on_file": True,
            "paid_at_reservation": True,
            **({"paid_in_full": True, "balance_paid_at": now}
               if data["payment_option"] == "pif" else {})}
           if prepaid else {}),
        "card_brand": card_brand,
        "card_last4": card_last4,
        "client_ip": client_ip,
        # -- lead attribution: which venue page produced this booking ----------
        "attr_venue": str(data.get("attr_venue") or "")[:200],
        "attr_venue_url": str(data.get("attr_venue_url") or "")[:300],
        "attr_landing": str(data.get("attr_landing") or "")[:300],
        "attr_referrer": str(data.get("attr_referrer") or "")[:300],
        "test_mode": TEST_MODE,
        "created_via": source,
    }

    # -- generate contract + send to SignWell ----------------------------------
    if prepaid:
        expected = (booking["pif_total"] if data["payment_option"] == "pif"
                    else booking["retainer"])
        if abs(prepaid["amount"] - expected) > 0.5:
            booking["paid_amount_mismatch"] = {"paid": prepaid["amount"],
                                               "expected": expected}
            print(f"PAID AMOUNT MISMATCH {booking_id}: paid {prepaid['amount']} "
                  f"expected {expected}")
            try:
                emails.notify_owner(
                    RESEND_API_KEY.value, OWNER_EMAIL,
                    f"CHECK THIS BOOKING \u2014 paid {prepaid['amount']:.2f}, "
                    f"expected {expected} \u2014 {client_merge['client_names']}",
                    [f"Booking {booking_id}: the Whop reservation payment does not "
                     f"match the price computed at booking (code or add-on changed "
                     f"between the card step and submit?). Review in the admin."])
            except Exception as e:
                print(f"mismatch alert failed: {e}")
    pdf = generate_contract(pkg["id"], data["payment_option"],
                            client=client_merge, signwell=True,
                            second_shooter=second_shooter,
                            extra_hours=extra_hours,
                            discount=discount, discount_code=discount_code,
                            days_to_event=days_to_event,
                            prepaid=bool(prepaid))
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
    return _res({"ok": True, "booking_id": booking_id,
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
              "deposit_paid_at": booking.get("deposit_paid_at") or firestore.SERVER_TIMESTAMP,
              _k(booking, "payment_method_id"): payment_method_id,
              _k(booking, "payment_id"): tx_id,
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
                     secrets=[SIGNWELL_API_KEY, *PAY_SECRETS, RESEND_API_KEY,
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

    # -- Paid at reservation (Whop flow): nothing to charge, just confirm -------
    if booking.get("paid_at_reservation") and booking.get("deposit_paid_at") \
            and booking.get("status") != "confirmed":
        pm0, _c0 = _card_ids(booking)
        _confirm_paid(ref, booking, pm0, booking.get("whop_payment_id"),
                      booking.get("invoice_amount") or 0,
                      RESEND_API_KEY.value, GRATUITY_SECRET.value)
        print(f"prepaid booking confirmed on signature: {booking['booking_id']}")
        return https_fn.Response("confirmed (prepaid)", status=200)

    # -- Preferred path: charge the card captured at booking ---------------------
    # Closes the window between signature and payment. If anything about the
    # card fails we fall through to the payment link below, which is exactly
    # the old behaviour — a decline degrades, it does not dead-end.
    proc = _proc(booking)
    zoho = _pay(proc)          # Zoho or Whop client; same method names
    pm_id, cust_id = _card_ids(booking)
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
                     f"A {proc.title()} payment link is being sent instead — "
                     "the couple can pay with a different card. No action "
                     "needed unless that also fails."])
            except Exception as e2:
                print(f"owner notify failed: {e2}")
        else:
            tx_id = (tx or {}).get("payment_id")
            if (tx or {}).get("status") == "pending" and proc == "whop":
                # Whop is still deciding. Keep the claim so a SignWell retry
                # cannot charge twice; whop_webhook (payment.succeeded)
                # confirms the booking when the charge settles.
                ref.update({"whop_pending_payment_id": tx_id,
                            "charge_pending_at": firestore.SERVER_TIMESTAMP})
                print(f"whop charge pending payment={tx_id}; awaiting webhook")
                return https_fn.Response("charge pending", status=200)
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

    # -- Fallback: hosted payment link. Zoho emails its own; Whop sends
    #    nothing, so for Whop our payment_nudge email carries the link. -------
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
                    _k(booking, "payment_link_id"): link["payment_link_id"],
                    _k(booking, "payment_link_url"): link.get("url"),
                    "invoice_amount": amount})
        if proc == "whop":
            booking["invoice_amount"] = amount
            try:
                emails.payment_nudge(RESEND_API_KEY.value, booking,
                                     pay_url=link.get("url"))
            except Exception as e2:
                print(f"whop link email failed: {e2}")
        return https_fn.Response("ok", status=200)
    except Exception as e:
        attempts = booking.get(f"{proc}_setup_attempts", 0) + 1
        ref.update({f"{proc}_setup_attempts": attempts,
                    f"{proc}_setup_last_error": str(e)[:500]})
        print(f"{proc} setup failed (attempt {attempts}): {e}")
        if attempts == 1:                      # alert once, not per retry
            try:
                emails.notify_owner(
                    RESEND_API_KEY.value, OWNER_EMAIL,
                    f"ACTION NEEDED: payment setup failed — "
                    f"{booking['client_names']}",
                    [f"Booking {booking['booking_id']} is SIGNED but the "
                     f"{proc.title()} payment link could not be created.",
                     f"Error: {e}",
                     "SignWell will retry automatically; if this persists, "
                     f"investigate the {proc.title()} secrets/account."])
            except Exception as e2:
                print(f"owner notify failed: {e2}")
        # 500 -> SignWell retries the event, re-attempting setup
        return https_fn.Response(f"{proc} setup failed", status=500)


# ============================================================ zoho_webhook ==
@https_fn.on_request(region=REGION,
                     secrets=[*PAY_SECRETS, RESEND_API_KEY, GRATUITY_SECRET],
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

    return _settle_link_payment("zoho", link_id, kind, payment_id)


def _settle_link_payment(proc, link_id, kind, payment_id, via="link"):
    """Shared tail of zoho_webhook / whop_webhook / the poller: a hosted
    link for `proc` with id `link_id` is verified paid. Mark the booking.

    kind == "balance": balance_paid_at on an already-confirmed booking.
    otherwise         : awaiting_payment -> confirmed, welcome + owner mail.
    """
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
                               "balance_paid_via": via})
        try:
            emails.notify_owner(
                RESEND_API_KEY.value, OWNER_EMAIL,
                f"BALANCE PAID (link) — {b['client_names']} — ${b['balance']:,}",
                [f"Booking {b['booking_id']} balance paid via {proc.title()} link."])
        except Exception as e:
            print(f"owner notify failed: {e}")
        return https_fn.Response("ok", status=200)

    # --- retainer / PIF link (signed booking awaiting payment) ---------------
    q = db.collection("bookings").where(
        filter=FieldFilter(f"{proc}_payment_link_id", "==", link_id)).limit(1).get()
    if not q:
        return https_fn.Response("no booking", status=200)
    ref = q[0].reference
    booking = q[0].to_dict()
    if booking["status"] != "awaiting_payment":     # idempotency guard
        return https_fn.Response("already processed", status=200)
    _confirm_link_paid(ref, booking, payment_id, via)
    return https_fn.Response("ok", status=200)


def _confirm_link_paid(ref, booking, payment_id, via="link"):
    """awaiting_payment -> confirmed for a link-paid booking (no card on
    file), then the welcome email and the owner notification."""
    plan = booking["payment_option"]
    update = {
        "status": "confirmed",
        "deposit_paid_at": firestore.SERVER_TIMESTAMP,
        _k(booking, "payment_id"): payment_id,
        "charged_on_file": False,        # link payments store no card
        "confirmed_via": via,
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
            f"{booking['event_date']}"
            + (" (via poller)" if via == "poller" else ""),
            [f"Booking: {booking['booking_id']}",
             f"Client: {booking['client_names']} ({booking['email']}, "
             f"{booking.get('phone','')})",
             f"Package: {booking['package_name']} ({plan})",
             f"Add-ons: "
             + (", ".join(a['label'] for a in booking.get('addons') or [])
                or "none")
             + (f" | Discount: {booking.get('discount_code')} "
                f"−${booking.get('discount')}"
                if booking.get('discount') else "")
             + (f" — {booking.get('coverage_hours', '?')} hrs total coverage"
                if booking.get('extra_hours') else ""),
             f"Event: {booking['event_date']} — "
             f"{booking.get('ceremony_venue','')}",
             f"Paid now: ${booking.get('invoice_amount') or 0:,}",
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


# ============================================================ whop_webhook ==
@https_fn.on_request(region=REGION,
                     secrets=[*WHOP_SECRETS, RESEND_API_KEY, GRATUITY_SECRET,
                              SIGNWELL_API_KEY, *ZOHO_SECRETS],
                     memory=options.MemoryOption.MB_512)
def whop_webhook(req: https_fn.Request) -> https_fn.Response:
    """Whop webhook. Register (once, whop.com/dashboard/developer > Webhooks)
    for: payment.succeeded, payment.failed. Everything else is ignored.

    Verification: Whop signs every delivery (Standard Webhooks), and the
    signature is checked first. The payment is then re-fetched with the API
    key and must read paid, so the body is never trusted on its own.

    Three payment kinds reach here, told apart by metadata.kind, which we set
    on every charge and every checkout link:
      retainer/pif   link paid          -> awaiting_payment -> confirmed
                     off-session charge that was still pending at signature
                                        -> signed -> confirmed
      balance        link paid          -> balance_paid_at
                     pending charge     -> balance_paid_at
      gratuity       pending charge     -> gratuities subcollection
    """
    raw = req.get_data() or b""
    secret = os.environ.get("WHOP_WEBHOOK_SECRET") or ""
    if not Whop.verify_webhook(req.headers, raw, secret):
        print("whop webhook REJECTED: bad signature")
        return https_fn.Response("bad signature", status=403)
    payload = req.get_json(silent=True) or {}
    event_type = str(payload.get("type") or "")
    data = payload.get("data") or {}
    print(f"whop_webhook: {event_type} {json.dumps(data)[:600]}")
    acct = str(payload.get("account_id") or data.get("account_id")
               or (data.get("company") or {}).get("id") or "")
    if acct and acct != WHOP_ACCOUNT_ID:
        print("whop webhook REJECTED: wrong account")
        return https_fn.Response("wrong account", status=403)
    payment_id = str(data.get("id") or "")
    if event_type == "setup_intent.succeeded":
        # Backstop for the booking card: if the page never posted the
        # setup intent id (tab closed before the redirect), attach the saved
        # method to the booking that owns this checkout configuration.
        member_id, pm_id = Whop.setup_ids(data)
        chk_id = str(data.get("checkout_configuration_id") or "")
        if not (chk_id and member_id and pm_id):
            return https_fn.Response("ignored", status=200)
        from google.cloud.firestore_v1.base_query import FieldFilter as _FF
        db = firestore.client()
        q = db.collection("bookings").where(
            filter=_FF("whop_checkout_id", "==", chk_id)).limit(1).get()
        if not q:
            return https_fn.Response("no booking yet", status=200)
        b = q[0].to_dict()
        if b.get("whop_payment_method_id"):
            return https_fn.Response("already attached", status=200)
        q[0].reference.update({"whop_payment_method_id": pm_id,
                               "whop_customer_id": member_id,
                               "whop_setup_intent_id": data.get("id"),
                               "card_attached_via": "webhook"})
        print(f"setup_intent.succeeded attached {pm_id} to {b['booking_id']}")
        return https_fn.Response("attached", status=200)
    if event_type not in ("payment.succeeded", "payment.failed") \
            or not payment_id.startswith("pay_"):
        return https_fn.Response("ignored", status=200)

    meta = data.get("metadata") or {}
    kind = str(meta.get("kind") or "")
    booking_id = str(meta.get("booking_id") or "")
    db = firestore.client()
    from google.cloud.firestore_v1.base_query import FieldFilter

    if event_type == "payment.failed":
        # Only a charge we left pending needs a hand here; link attempts that
        # fail are simply retried by the couple on the hosted page.
        if booking_id and kind in ("retainer", "pif"):
            ref = db.collection("bookings").document(booking_id)
            b = ref.get().to_dict() or {}
            if b.get("whop_pending_payment_id") == payment_id and \
                    b.get("status") != "confirmed":
                ref.update({"charge_claimed_at": None,
                            "whop_pending_payment_id": None,
                            "charge_failed_at": firestore.SERVER_TIMESTAMP,
                            "charge_last_error":
                                str(data.get("failure_message") or "failed")[:500]})
                try:
                    emails.notify_owner(
                        RESEND_API_KEY.value, OWNER_EMAIL,
                        f"Card declined after signature — {b.get('client_names','')}",
                        [f"Booking {booking_id} is SIGNED but the Whop charge "
                         f"settled as failed: {data.get('failure_message')}",
                         "Send a payment link from the admin dashboard."])
                except Exception as e:
                    print(f"owner notify failed: {e}")
        return https_fn.Response("ok", status=200)

    # --- payment.succeeded: authoritative re-fetch -------------------------
    try:
        live = _whop().get_payment(payment_id)
    except Exception as e:
        print(f"whop verification fetch failed: {e}")
        return https_fn.Response("verification unavailable", status=500)
    if str(live.get("status", "")).lower() != "paid":
        print(f"whop webhook REJECTED: payment {payment_id} status={live.get('status')}")
        return https_fn.Response("verification failed", status=403)
    meta = live.get("metadata") or meta
    kind = str(meta.get("kind") or kind)
    booking_id = str(meta.get("booking_id") or booking_id)
    cfg_id = str(live.get("checkout_configuration_id") or
                 (live.get("checkout_configuration") or {}).get("id") or "")

    # --- reservation payment (paid checkout on the book page) -------------
    if str(meta.get("source") or "") == "reservation":
        q = db.collection("bookings").where(
            filter=FieldFilter("whop_payment_id", "==", payment_id)).limit(1).get()
        if q:
            return https_fn.Response("booking exists", status=200)
        # Finish the booking here from the form stored at whop_setup, so the
        # contract goes out even if the browser never submits. The page may
        # be doing the same thing right now; the payment lock lets one win.
        lead_q = db.collection("leads").where(
            filter=FieldFilter("whop_checkout_id", "==", cfg_id)).limit(1).get() if cfg_id else []
        for ls in lead_q:
            ld = ls.to_dict() or {}
            payload = ld.get("reservation_payload") or {}
            if payload.get("email") and payload.get("event_date"):
                bdata = {**payload, "package_id": payload.get("package_id") or ld.get("package_id"),
                         "payment_option": payload.get("payment_option") or ld.get("payment_option") or "pif",
                         "agree_terms": True, "whop_payment_id": payment_id,
                         "whop_checkout_id": cfg_id}
                obj, code = _book_safely(bdata, ld.get("client_ip") or "", "webhook")
                print(f"webhook booking for {payment_id}: {code} {json.dumps(obj)[:300]}")
                if code < 300:
                    return https_fn.Response("booked", status=200)
                if code >= 500:
                    return https_fn.Response("booking failed, retry", status=500)
                try:
                    emails.notify_owner(
                        RESEND_API_KEY.value, OWNER_EMAIL,
                        f"PAID, BOOKING NEEDS A HAND \u2014 {ld.get('client_names','')}",
                        [f"{ld.get('client_names','')} ({ld.get('email','')}) paid "
                         f"(payment {payment_id}) but the booking was refused: "
                         f"{obj.get('error')}",
                         "Send them the finish link: https://ataviaweddings.com/"
                         f"book/?finish={payment_id}"])
                except Exception as e:
                    print(f"booking-refused alert failed: {e}")
            if ld.get("whop_payment_id") == payment_id:
                return https_fn.Response("already noted", status=200)
            ls.reference.update({"whop_payment_id": payment_id,
                                 "paid_unbooked_at": firestore.SERVER_TIMESTAMP,
                                 "status": "paid_unbooked"})
            try:
                emails.notify_owner(
                    RESEND_API_KEY.value, OWNER_EMAIL,
                    f"PAID BUT NO BOOKING YET \u2014 {ld.get('client_names','')} "
                    f"\u2014 ${Whop.payment_amount(live):,.2f}",
                    [f"{ld.get('client_names','')} ({ld.get('email','')}) paid "
                     f"{meta.get('kind','')} on the book page but the booking "
                     f"did not complete (payment {payment_id}).",
                     "If a booking for them appears in the next few minutes this "
                     "resolves itself; otherwise send them the finish link: "
                     f"https://ataviaweddings.com/book/?finish={payment_id}"])
            except Exception as e:
                print(f"paid-unbooked alert failed: {e}")
        return https_fn.Response("noted", status=200)

    # --- hosted link paid (we know the checkout configuration id) ----------
    if cfg_id:
        return _settle_link_payment("whop", cfg_id, kind, payment_id)

    # --- off-session charge that was pending when we created it -------------
    if not booking_id:
        return https_fn.Response("no booking ref", status=200)
    ref = db.collection("bookings").document(booking_id)
    snap = ref.get()
    if not snap.exists:
        return https_fn.Response("no booking", status=200)
    b = snap.to_dict()
    if kind in ("retainer", "pif"):
        if b.get("status") == "confirmed":
            return https_fn.Response("already processed", status=200)
        amount, memo, _ = _payment_terms(b)
        _confirm_paid(ref, b, b.get("whop_payment_method_id"), payment_id,
                      amount, RESEND_API_KEY.value, GRATUITY_SECRET.value)
        ref.update({"whop_pending_payment_id": None})
        return https_fn.Response("confirmed", status=200)
    if kind == "balance":
        if b.get("balance_paid_at"):
            return https_fn.Response("already processed", status=200)
        ref.update({"balance_paid_at": firestore.SERVER_TIMESTAMP,
                    "balance_payment_id": payment_id,
                    "balance_paid_via": "card"})
        try:
            emails.notify_owner(
                RESEND_API_KEY.value, OWNER_EMAIL,
                f"BALANCE CHARGED — {b['client_names']} — ${b['balance']:,}",
                [f"Booking {booking_id} balance charge settled (Whop webhook)."])
            emails.balance_receipt(RESEND_API_KEY.value, b, b["balance"])
        except Exception as e:
            print(f"balance emails failed: {e}")
        return https_fn.Response("ok", status=200)
    if kind == "gratuity":
        existing = list(ref.collection("gratuities")
                        .where(filter=FieldFilter("payment_id", "==", payment_id))
                        .limit(1).get())
        if existing:
            return https_fn.Response("already processed", status=200)
        amount = float(live.get("total") or live.get("amount") or 0)
        ref.collection("gratuities").add({
            "amount": amount, "at": firestore.SERVER_TIMESTAMP,
            "payment_id": payment_id, "via": "webhook"})
        try:
            emails.gratuity_receipt(RESEND_API_KEY.value, b, amount)
            emails.notify_owner(
                RESEND_API_KEY.value, OWNER_EMAIL,
                f"GRATUITY RECEIVED — ${amount:,.2f} — {b['client_names']}",
                [f"Booking {booking_id} — distribute 100% to event team.",
                 f"Event: {b['event_date']} — {b['package_name']}"])
        except Exception as e:
            print(f"gratuity emails failed: {e}")
        return https_fn.Response("ok", status=200)
    return https_fn.Response("ignored", status=200)



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
    clients = {}
    for snap in stuck:
        b = snap.to_dict()
        link_id = b.get(_k(b, "payment_link_id"))
        if not link_id:
            continue
        proc = _proc(b)
        try:
            if proc not in clients:
                clients[proc] = _pay(proc)
            link = clients[proc].get_payment_link(link_id)
        except Exception as e:
            print(f"poller: link fetch failed for {b['booking_id']}: {e}")
            continue
        if str(link.get("status", "")).lower() != "paid":
            continue
        paid = [p for p in (link.get("payments") or [])
                if p.get("status") == "succeeded"]
        _confirm_link_paid(snap.reference, b,
                           paid[0].get("payment_id") if paid else None,
                           via="poller")
        print(f"poller: confirmed {b['booking_id']}")


NUDGE_CODE_AMOUNT = 200   # JC-ATV-NUDGE-0928: $ off carried by the day-3 nudge
NUDGE_CODE_HOURS = 72


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
                # JC-ATV-NUDGE-0928: the second nudge carries a $200 code good
                # for 72 h - a reason to decide, not just a reminder. Minted
                # once; a failure to mint still sends the plain nudge.
                code = None
                try:
                    code = _mint_code(db, NUDGE_CODE_AMOUNT, NUDGE_CODE_HOURS,
                                      f"day-3 nudge — {lead.get('email','')}")
                    snap.reference.update({"nudge2_code": code["code"]})
                    resume += ("&" if "?" in resume else "?") + "code=" + code["code"]
                except Exception as e:
                    print(f"nudge code mint failed (non-fatal): {e}")
                emails.card_recovery(RESEND_API_KEY.value, lead, resume, second=True, code=code)
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
                # Neither processor has a "resend" call; our nudge carries the link.
                emails.payment_nudge(RESEND_API_KEY.value, b,
                                     pay_url=b.get(_k(b, "payment_link_url")))
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


def _send_balance_heads_up(db, now):
    """Email couples whose card-on-file balance falls due within the next 24 h
    (i.e. it will be charged on tomorrow's 07:00 run). Once per booking, stamped
    in balance_heads_up_sent_at. No-card bookings get a payment link instead of
    a charge, so they are skipped here."""
    from google.cloud.firestore_v1.base_query import FieldFilter
    soon = (db.collection("bookings")
              .where(filter=FieldFilter("status", "==", "confirmed"))
              .where(filter=FieldFilter("payment_option", "==", "standard"))
              .where(filter=FieldFilter("balance_due_at", ">", now))
              .where(filter=FieldFilter("balance_due_at", "<=", now + timedelta(hours=24)))
              .get())
    for snap in soon:
        b = snap.to_dict()
        if (b.get("balance_paid_at") or b.get("balance_heads_up_sent_at")
                or b.get("test_mode")
                or not all(_card_ids(b))):
            continue
        try:
            emails.balance_heads_up(RESEND_API_KEY.value, b, b["balance"])
            snap.reference.update({"balance_heads_up_sent_at": firestore.SERVER_TIMESTAMP})
            emails.notify_owner(
                RESEND_API_KEY.value, OWNER_EMAIL,
                f"BALANCE HEADS-UP SENT \u2014 {b['client_names']} \u2014 ${b['balance']:,}",
                [f"Booking {b['booking_id']}: the couple was told their balance "
                 f"charges tomorrow morning. Charge runs on the next 07:00 job."])
        except Exception as e:
            print(f"balance heads-up failed {b['booking_id']}: {e}")



# ======================================================== lazo invite ==
LAZO_INVITE_DELAY_DAYS = 3    # JC-LZ-INVITE-0928: days after the booking is paid
LAZO_INVITE_PER_RUN = 25      # cap per daily run: the first run reaches existing couples gradually
LAZO_INVITE_RELAY = ("zola.com", "theknot.com", "weddingpro.com", "example.com")


def _send_lazo_invites(db, now):
    """One Lazo recommendation per booked couple, a few days after they pay.
    Skips test bookings, marketplace relay addresses, opted-out couples,
    weddings more than 60 days past, and anyone already sent. Stamps
    lazo_invite_sent_at so it can never repeat. Non-fatal throughout."""
    from google.cloud.firestore_v1.base_query import FieldFilter
    sent = 0
    cutoff = (now - timedelta(days=60)).strftime("%Y-%m-%d")
    since = now - timedelta(days=LAZO_INVITE_DELAY_DAYS)
    try:
        snaps = (db.collection("bookings")
                   .where(filter=FieldFilter("status", "==", "confirmed")).get())
    except Exception as e:
        print(f"lazo invite query failed: {e}"); return
    for snap in snaps:
        if sent >= LAZO_INVITE_PER_RUN:
            break
        b = snap.to_dict() or {}
        email = str(b.get("email") or "").strip().lower()
        paid = b.get("deposit_paid_at") or b.get("created_at")
        if (b.get("test_mode") or b.get("lazo_invite_sent_at") or b.get("marketing_optout")
                or not email or "@" not in email
                or any(email.endswith("@" + r) or ("." + r) in email for r in LAZO_INVITE_RELAY)
                or not paid or paid > since
                or str(b.get("event_date_raw") or "9999") < cutoff):
            continue
        try:
            emails.lazo_invite(RESEND_API_KEY.value, b)
            snap.reference.update({"lazo_invite_sent_at": firestore.SERVER_TIMESTAMP})
            sent += 1
        except Exception as e:
            print(f"lazo invite failed {b.get('booking_id', snap.id)}: {e}")
    print(f"lazo invites: sent {sent}")

# ========================================================= charge_balances ==
@scheduler_fn.on_schedule(schedule="every day 07:00",
                          timezone=scheduler_fn.Timezone("America/Phoenix"),
                          region=REGION,
                          secrets=[*PAY_SECRETS, RESEND_API_KEY,
                                   GRATUITY_SECRET, SIGNWELL_API_KEY])
def charge_balances(event: scheduler_fn.ScheduledEvent) -> None:
    _poll_paid_invoices()      # safety net: catch payments whose webhook dropped
    _send_gratuity_invites()   # post-event thank-you + gratuity link
    _send_questionnaire_reminders()   # nag unsubmitted questionnaires
    _chase_abandoned()                # recover stalled bookings
    _chase_leads()                    # card-window abandons (no booking yet)
    _send_lazo_invites(firestore.client(), datetime.now(timezone.utc))   # JC-LZ-INVITE-0928
    db = firestore.client()
    now = datetime.now(timezone.utc)
    try:
        _send_balance_heads_up(db, now)   # 24 h notice before tomorrow's charge
    except Exception as e:
        print(f"balance heads-up sweep failed: {e}")
    from google.cloud.firestore_v1.base_query import FieldFilter
    due = (db.collection("bookings")
             .where(filter=FieldFilter("status", "==", "confirmed"))
             .where(filter=FieldFilter("payment_option", "==", "standard"))
             .where(filter=FieldFilter("balance_due_at", "<=", now))
             .get())
    clients = {}
    for snap in due:
        b = snap.to_dict()
        if b.get("balance_paid_at") or b.get("balance_attempts", 0) >= 3:
            continue
        if b.get("balance_pending_payment_id"):
            continue      # Whop charge already in flight; webhook settles it
        memo = (f"Remaining balance — {b['package_name']} — "
                f"{b['event_date']}")
        proc = _proc(b)
        try:
            if proc not in clients:
                clients[proc] = _pay(proc)
            zoho = clients[proc]          # this booking's processor client
        except Exception as e:
            print(f"balance: {proc} client unavailable for {b['booking_id']}: {e}")
            continue
        pm_id, cust_id = _card_ids(b)
        if not (pm_id and cust_id):
            # No card on file (link-paid or pre-Zoho booking): send a balance
            # payment link once; the processor webhook marks it paid. Zoho
            # emails its own link; for Whop our balance_link email carries it.
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
                if proc == "whop":
                    try:
                        emails.balance_link(RESEND_API_KEY.value, b,
                                            b["balance"], link.get("url"))
                    except Exception as e2:
                        print(f"balance link email failed {b['booking_id']}: {e2}")
                emails.notify_owner(
                    RESEND_API_KEY.value, OWNER_EMAIL,
                    f"BALANCE LINK SENT — {b['client_names']} — ${b['balance']:,}",
                    [f"Booking {b['booking_id']} has no card on file; a {proc.title()} "
                     f"payment link for the balance was emailed to {b['email']}.",
                     f"Link: {link.get('url')}"])
            except Exception as e:
                attempts = b.get("balance_attempts", 0) + 1
                snap.reference.update({
                    "balance_attempts": attempts,
                    "balance_last_error": str(e)[:500]})
                print(f"balance link failed {b['booking_id']}: {e}")
                # Previously print-only: two unbilled couples sat here for
                # weeks with nobody told (JC-ATV-PAY-0927).
                try:
                    emails.notify_owner(
                        RESEND_API_KEY.value, OWNER_EMAIL,
                        f"BALANCE LINK FAILED (attempt {attempts}/3) \u2014 "
                        f"{b['client_names']} \u2014 ${b['balance']:,}",
                        [f"Booking {b['booking_id']} has no card on file and {proc.title()} "
                         f"refused to create a payment link: {str(e)[:300]}",
                         f"Bill them from the {proc.title()} dashboard by hand." if attempts >= 3
                         else "Will retry tomorrow."])
                except Exception as e2:
                    print(f"balance link owner alert failed: {e2}")
            continue
        try:
            tx = zoho.charge_saved_method(
                cust_id, pm_id, b["balance"], memo,
                meta={"booking_id": b["booking_id"], "kind": "balance"},
                descriptor=STATEMENT_DESCRIPTOR)
            if tx.get("status") == "pending" and proc == "whop":
                # Whop hasn't settled yet. Not a failure: park it and let
                # whop_webhook (payment.succeeded / failed) finish the job.
                snap.reference.update({
                    "balance_pending_payment_id": tx.get("payment_id"),
                    "balance_pending_at": firestore.SERVER_TIMESTAMP})
                print(f"balance charge pending {b['booking_id']} payment={tx.get('payment_id')}")
                continue
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
                     secrets=[*PAY_SECRETS, RESEND_API_KEY, GRATUITY_SECRET])
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
    pm_id, cust_id = _card_ids(b)
    if not (pm_id and cust_id):
        return _json(req, {"error": "no payment method on file"}, 409)

    tx = _pay(b).charge_saved_method(
        cust_id, pm_id, amount,
        f"Team gratuity — {b['package_name']} — {b['event_date']}",
        meta={"booking_id": booking_id, "kind": "gratuity"},
        descriptor=STATEMENT_DESCRIPTOR)
    if tx.get("status") == "pending" and _proc(b) == "whop":
        # Settles in the background; whop_webhook records it and sends the
        # receipt. The couple sees a thank-you either way.
        return _json(req, {"ok": True, "amount": amount, "pending": True})
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
                     secrets=[*PAY_SECRETS, SIGNWELL_API_KEY, RESEND_API_KEY,
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
      delete_lead         {email}: delete that couple's lead docs (not bookings/inquiries)
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

    if action == "reply_inquiry":   # JC-ATV-REPLY-0928: "Write back" on the Leads page
        import html as _html
        iref = db.collection("inquiries").document(str(data.get("inquiry_id") or ""))
        isnap = iref.get()
        if not isnap.exists:
            return _json(req, {"error": "inquiry not found"}, 404)
        inq = isnap.to_dict() or {}
        to = str(inq.get("email") or "").strip()
        subject = str(data.get("subject") or "").strip()[:200]
        body = str(data.get("body") or "").strip()[:5000]
        if not to or "@" not in to:
            return _json(req, {"error": "this inquiry has no email address"}, 400)
        if not subject or not body:
            return _json(req, {"error": "subject and message are required"}, 400)
        paras = [p.strip() for p in body.replace("\r", "").split("\n\n") if p.strip()]
        html_body = "".join("<p style=\"margin:0 0 16px\">%s</p>" % _html.escape(p).replace("\n", "<br>") for p in paras)
        html_doc = ("<div style=\"font-family:Georgia,serif;font-size:15px;line-height:1.6;color:#2B2B2B;max-width:560px\">"
                    + html_body + "</div>")
        try:
            emails._send(RESEND_API_KEY.value, to, subject, html_doc)
        except Exception as e:
            print(f"reply_inquiry send failed: {e}")
            return _json(req, {"error": "the email service refused the message; try again in a minute"}, 502)
        entry = {"at": now.isoformat(), "by": who, "subject": subject, "body": body, "to": to}
        iref.update({"replies": firestore.ArrayUnion([entry]), "last_reply_at": now,
                     "status": "contacted", "status_at": now})
        return _json(req, {"ok": True, "sent_to": to})

    if action == "delete_lead":   # Leads page: remove a couple's card-step attempts
        # The leads table shows one row per email (all attempts merged), so a
        # delete removes every lead doc for that email. Bookings and inquiries
        # are never touched here; a lead that already converted is skipped.
        from google.cloud.firestore_v1.base_query import FieldFilter as _FF2
        email = str(data.get("email") or "").strip().lower()
        if not email or "@" not in email:
            return _json(req, {"error": "email required"}, 400)
        snaps = list(db.collection("leads").where(filter=_FF2("email", "==", email)).get())
        if not snaps:
            # emails are stored as typed; retry case-insensitively over recent rows
            snaps = [s for s in db.collection("leads").limit(2000).get()
                     if str((s.to_dict() or {}).get("email") or "").strip().lower() == email]
        deleted, kept = 0, 0
        for s in snaps:
            d = s.to_dict() or {}
            if d.get("status") == "converted" or d.get("booking_id"):
                kept += 1; continue
            s.reference.delete(); deleted += 1
        print(f"delete_lead {email} by {who}: deleted={deleted} kept={kept}")
        return _json(req, {"ok": True, "deleted": deleted, "kept": kept})

    booking_id = str(data.get("booking_id") or "")
    ref = db.collection("bookings").document(booking_id)
    snap = ref.get()
    if not snap.exists:
        return _json(req, {"error": "booking not found"}, 404)
    b = snap.to_dict()
    log = {"at": now, "by": who, "action": action}

    try:
        if action == "payment_link":
            zoho = _pay(b)                      # this booking's processor
            if b.get("status") in ("awaiting_payment", "signed"):
                amount = b.get("invoice_amount") or (b.get("pif_total") if b.get("payment_option") == "pif" else b.get("retainer"))
                link = zoho.create_payment_link(
                    amount=amount, description=f"Retainer — {b['package_name']} — {b['event_date']}",
                    email=b["email"], reference_id=f"{booking_id}-retainer-{int(now.timestamp())}",
                    phone=b.get("phone", ""), return_url="https://ataviaweddings.com/book/thank-you",
                    meta={"booking_id": booking_id, "kind": "retainer"})
                ref.update({_k(b, "payment_link_id"): link["payment_link_id"],
                            _k(b, "payment_link_url"): link.get("url"),
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
                if _proc(b) == "whop":          # Whop never emails its links
                    emails.balance_link(RESEND_API_KEY.value, b, b["balance"], link.get("url"))
                return _json(req, {"ok": True, "url": link.get("url"), "kind": "balance", "amount": b["balance"]})
            return _json(req, {"error": "nothing is owed on this booking"}, 400)

        if action == "retry_balance":
            if b.get("status") != "confirmed" or b.get("balance_paid_at") or b.get("payment_option") != "standard":
                return _json(req, {"error": "no unpaid balance to charge"}, 400)
            pm_id, cust_id = _card_ids(b)
            if not (pm_id and cust_id):
                return _json(req, {"error": "no card on file — send a payment link instead"}, 400)
            zoho = _pay(b)
            tx = zoho.charge_saved_method(
                cust_id, pm_id, b["balance"],
                f"Remaining balance — {b['package_name']} — {b['event_date']}",
                meta={"booking_id": booking_id, "kind": "balance"}, descriptor=STATEMENT_DESCRIPTOR)
            if tx.get("status") == "pending" and _proc(b) == "whop":
                ref.update({"balance_pending_payment_id": tx.get("payment_id"),
                            "balance_pending_at": firestore.SERVER_TIMESTAMP, "admin_last_action": log})
                return _json(req, {"ok": True, "pending": True, "payment_id": tx.get("payment_id"),
                                   "note": "Whop is still settling this charge; the webhook will mark it paid."})
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
            zoho = _pay(b)
            for key in (_k(b, "payment_link_id"), "balance_payment_link_id"):
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
            pid = b.get("balance_payment_id") if which == "balance" else b.get(_k(b, "payment_id"))
            if not pid or pid == "manual":
                return _json(req, {"error": f"no {_proc(b).title()} payment id on file for the {which}"}, 400)
            if not (1 <= amount <= 10000):
                return _json(req, {"error": "amount out of range"}, 400)
            zoho = _pay(b)
            rf = zoho.refund(pid, amount, description=str(data.get("reason") or f"Refund — {b['client_names']}")[:200])
            entry = {"at": now, "amount": amount, "payment": which, "refund_id": rf.get("refund_id"),
                     "status": rf.get("status"), "by": who, "reason": str(data.get("reason") or "")[:300]}
            ref.update({"refunds": firestore.ArrayUnion([entry]), "admin_last_action": log})
            return _json(req, {"ok": True, "refund_id": rf.get("refund_id"), "status": rf.get("status")})

        if action == "mark_paid":
            # Card was run by hand (processor dashboard, phone, etc.). Record it
            # and void any open link so the couple can't pay twice.
            which = str(data.get("payment") or "balance")
            pid = str(data.get("payment_id") or "").strip()[:80]
            note = str(data.get("note") or "")[:300]
            zoho = _pay(b)
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
                            _k(b, "payment_id"): pid or "manual", "invoice_amount": amount,
                            "charged_on_file": False, "deposit_paid_manually": True, "deposit_manual_note": note})
                if b.get("payment_option") == "pif":
                    upd["balance_paid_at"] = firestore.SERVER_TIMESTAMP
                else:
                    try:
                        upd["balance_due_at"] = _compute_balance_due(
                            datetime.strptime(b["event_date_raw"], "%Y-%m-%d").replace(tzinfo=timezone.utc), now)
                    except Exception:
                        pass
                link_key = _k(b, "payment_link_id")
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
                                 f"{_proc(b).title()} payment: {pid or '(none given)'}", f"Note: {note or '—'}",
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
           "source": "formspree" if "submission" in body else
                     "gmail-intake" if sub.get("auto_code") or sub.get("auto_replied") else "site",
           "status": "contacted" if sub.get("auto_replied") else "new",
           "created_at": firestore.SERVER_TIMESTAMP}
    # JC-ATV-AUTOREPLY-0928: the Gmail intake script answers every marketplace
    # inquiry within minutes and asks for a code to put in that reply.
    code = None
    if sub.get("auto_code"):
        try:
            code = _mint_code(db, NUDGE_CODE_AMOUNT, NUDGE_CODE_HOURS,
                              f"auto-reply — {email}")
            doc["auto_code"] = code["code"]
        except Exception as e:
            print(f"auto-reply code mint failed (non-fatal): {e}")
    if sub.get("auto_replied"):
        doc["auto_replied_at"] = firestore.SERVER_TIMESTAMP
    ref = db.collection("inquiries").add(doc)[1]
    if doc["sid"]:
        _link_session(db, doc["sid"], f"{doc['first_name']} {doc['last_name']}".strip(), email)
    return _json(req, {"ok": True, "id": ref.id, "code": code})


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
