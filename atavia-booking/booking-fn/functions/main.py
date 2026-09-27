# =============================================================================
# ATAVIA WEDDINGS — AUTOMATED BOOKING CLOUD FUNCTIONS  (v9 · 2026-07-20 — add-ons: second shooter + extra hours)
# Project: atavia-c29cd · Python 3.12 runtime · Region: us-central1
# =============================================================================
# Flow:
#   /book page POST -> book_submit
#     -> Firestore bookings/{id}  (status: pending_signature)
#     -> generate contract PDF (ReportLab, SignWell text tags)
#     -> SignWell send for e-signature
#   SignWell webhook (document completed) -> signwell_webhook
#     -> archive signed PDF to Storage
#     -> Stax: create customer + hosted invoice (deposit $500 or PIF total)
#     -> status: awaiting_payment
#   Stax webhook (payment) -> stax_webhook
#     -> capture payment_method_id (card on file)
#     -> status: confirmed · welcome email (Resend) · notify JC
#   charge_balances (daily scheduler, America/Phoenix)
#     -> standard-plan bookings past balance_due_at -> charge card on file
#   gratuity (HTTPS) -> tokenized post-event gratuity charge to card on file
#
# Secrets (set before deploy):
#   firebase functions:secrets:set SIGNWELL_API_KEY
#   firebase functions:secrets:set STAX_API_KEY
#   firebase functions:secrets:set RESEND_API_KEY
#   firebase functions:secrets:set PROMO_ADMIN_KEY   (any long random string; used to issue codes)
#   firebase functions:secrets:set GRATUITY_SECRET     (any long random string)
# =============================================================================

import hashlib
import hmac
import json
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
from lib.stax import Stax
from lib import emails
from lib.questionnaire_schema import ALL_FIELD_IDS, SUMMARY_LAYOUT

firebase_admin.initialize_app()

# ----------------------------------------------------------------- config ---
SIGNWELL_API_KEY = SecretParam("SIGNWELL_API_KEY")
STAX_API_KEY     = SecretParam("STAX_API_KEY")
RESEND_API_KEY   = SecretParam("RESEND_API_KEY")
GRATUITY_SECRET  = SecretParam("GRATUITY_SECRET")
PROMO_ADMIN_KEY  = SecretParam("PROMO_ADMIN_KEY")

TEST_MODE       = False  # PRODUCTION
STAX_MERCHANT_ID = "e3353e14-4c9d-4f9b-81b4-442a173b0442"  # Danbren Media LLC
OWNER_EMAIL     = "info@ataviaweddings.com"   # JC notification target
ALLOWED_ORIGINS = ["https://ataviaweddings.com", "https://www.ataviaweddings.com"]
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
    allow = origin if origin in ALLOWED_ORIGINS else ALLOWED_ORIGINS[0]
    return {
        "Access-Control-Allow-Origin": allow,
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
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


# ============================================================ book_submit ===
@https_fn.on_request(region=REGION, secrets=[SIGNWELL_API_KEY],
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

    pkg = PACKAGES[data["package_id"]]
    now = datetime.now(timezone.utc)
    db = firestore.client()
    booking_ref = db.collection("bookings").document()
    booking_id = booking_ref.id

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
        "client_ip": req.headers.get("X-Forwarded-For", req.remote_addr),
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

    booking_ref.set(booking)
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


# ======================================================== signwell_webhook ==
@https_fn.on_request(region=REGION,
                     secrets=[SIGNWELL_API_KEY, STAX_API_KEY, RESEND_API_KEY],
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
    # awaiting_payment (Stax invoice out). "signed" re-enters here so a Stax
    # failure is retried on SignWell's webhook retries.
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

    # -- Stax: customer + hosted invoice (resilient) -----------------------------
    try:
        stax = Stax(STAX_API_KEY.value)
        names = booking["client_names"].replace("&", " ").split()
        first, last = names[0], names[-1] if len(names) > 1 else names[0]
        customer = stax.create_customer(
            first=first, last=last, email=booking["email"],
            phone=booking.get("phone", ""))
        addons = booking.get("addons") or []   # pre-addon bookings lack key
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
                           "price": booking.get("base_total",
                                                booking["total"])}]
            line_items += [{"id": a["id"], "item": a["label"],
                            "details": "Add-on", "quantity": 1,
                            "price": a["amount"]} for a in addons]
            if disc:
                line_items.append({"id": "inquiry_discount",
                                   "item": f"Inquiry Discount ({disc_code})",
                                   "details": "", "quantity": 1,
                                   "price": -disc})
            line_items.append({"id": "pif_discount",
                               "item": "Paid-in-Full Discount",
                               "details": "", "quantity": 1,
                               "price": -RULES["pif_discount"]})
        invoice = stax.create_invoice(
            customer_id=customer["id"], total=amount, memo=memo,
            line_items=line_items)
        ref.update({"status": "awaiting_payment",
                    "stax_customer_id": customer["id"],
                    "stax_invoice_id": invoice["id"],
                    "invoice_amount": amount})
        return https_fn.Response("ok", status=200)
    except Exception as e:
        attempts = booking.get("stax_setup_attempts", 0) + 1
        ref.update({"stax_setup_attempts": attempts,
                    "stax_setup_last_error": str(e)[:500]})
        print(f"stax setup failed (attempt {attempts}): {e}")
        if attempts == 1:                      # alert once, not per retry
            try:
                emails.notify_owner(
                    RESEND_API_KEY.value, OWNER_EMAIL,
                    f"ACTION NEEDED: payment setup failed — "
                    f"{booking['client_names']}",
                    [f"Booking {booking['booking_id']} is SIGNED but the "
                     f"Stax invoice could not be created.",
                     f"Error: {e}",
                     "SignWell will retry automatically; if this persists, "
                     "investigate the Stax key/config."])
            except Exception as e2:
                print(f"owner notify failed: {e2}")
        # 500 -> SignWell retries the event, re-attempting Stax setup
        return https_fn.Response("stax setup failed", status=500)


# ============================================================ stax_webhook ==
@https_fn.on_request(region=REGION,
                     secrets=[STAX_API_KEY, RESEND_API_KEY, GRATUITY_SECRET],
                     memory=options.MemoryOption.MB_512)
def stax_webhook(req: https_fn.Request) -> https_fn.Response:
    payload = req.get_json(silent=True) or {}
    # TODO[first-test-event]: confirm Stax webhook envelope (event key names,
    # signature header) against a sandbox transaction, then enforce
    # verification before production go-live.
    print(f"stax_webhook: {json.dumps(payload)[:800]}")

    tx = payload.get("transaction") or payload
    tx_id = tx.get("id")
    invoice_id = tx.get("invoice_id") or (tx.get("invoice") or {}).get("id")
    success = tx.get("success", tx.get("is_captured", False))
    payment_method_id = tx.get("payment_method_id")
    if not invoice_id or not success:
        return https_fn.Response("ignored", status=200)

    # --- Webhook verification (authoritative, mirrors SignWell pattern) ---
    # Re-fetch the transaction with our API key; require success + our
    # merchant + matching invoice. A forged POST cannot pass this.
    if tx_id:
        try:
            live_tx = Stax(STAX_API_KEY.value).get_transaction(tx_id)
        except Exception as e:
            print(f"stax verification fetch failed: {e}")
            return https_fn.Response("verification unavailable", status=500)
        if (not live_tx.get("success")
                or live_tx.get("merchant_id") != STAX_MERCHANT_ID
                or live_tx.get("invoice_id") != invoice_id):
            print(f"stax webhook verification REJECTED tx={tx_id}")
            return https_fn.Response("verification failed", status=403)
        payment_method_id = live_tx.get("payment_method_id") or payment_method_id
    else:
        # No transaction id in payload: fall back to invoice-status check
        try:
            live_inv = Stax(STAX_API_KEY.value).get_invoice(invoice_id)
        except Exception as e:
            print(f"stax invoice verification failed: {e}")
            return https_fn.Response("verification unavailable", status=500)
        if live_inv.get("status") not in ("PAID", "paid"):
            print(f"stax webhook REJECTED: invoice {invoice_id} not paid")
            return https_fn.Response("verification failed", status=403)

    db = firestore.client()
    from google.cloud.firestore_v1.base_query import FieldFilter
    q = db.collection("bookings").where(
        filter=FieldFilter("stax_invoice_id", "==", invoice_id)).limit(1).get()
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
        "stax_payment_method_id": payment_method_id,
        "stax_transaction_id": tx.get("id"),
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
                f" auto-charges {booking['balance_due_date']}"),
             f"Gratuity link: https://ataviaweddings.com/gratuity"
             f"?b={booking['booking_id']}&t={g_token}"])
    except Exception as e:
        print(f"owner notify failed: {e}")
    return https_fn.Response("ok", status=200)


def _poll_paid_invoices():
    """Safety net: any booking stuck at awaiting_payment whose Stax invoice
    is actually PAID gets confirmed here, so a dropped webhook can never
    strand a paying client. Runs inside the daily scheduler."""
    from google.cloud.firestore_v1.base_query import FieldFilter
    db = firestore.client()
    stuck = (db.collection("bookings")
               .where(filter=FieldFilter("status", "==", "awaiting_payment"))
               .get())
    if not stuck:
        return
    stax = Stax(STAX_API_KEY.value)
    for snap in stuck:
        b = snap.to_dict()
        try:
            inv = stax.get_invoice(b["stax_invoice_id"])
        except Exception as e:
            print(f"poller: invoice fetch failed for {b['booking_id']}: {e}")
            continue
        if str(inv.get("status", "")).upper() != "PAID":
            continue
        pm = None
        for t in (inv.get("transactions") or []):
            if t.get("success"):
                pm = t.get("payment_method_id")
                break
        update = {"status": "confirmed",
                  "deposit_paid_at": firestore.SERVER_TIMESTAMP,
                  "stax_payment_method_id": pm,
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
                 f"but the invoice is paid. Confirmed automatically.",
                 f"Client: {b['client_names']} ({b['email']})"])
        except Exception as e:
            print(f"poller emails failed: {e}")
        print(f"poller: confirmed {b['booking_id']}")


def _chase_abandoned():
    """Abandoned-cart recovery. Two stall points:
    pending_signature (submitted, never signed) -> nudges at day 2 and 5 with
    the signing link (on top of SignWell's own 3/6/10 reminders), owner alert
    at day 7, marked abandoned at day 30 (SignWell doc expiry).
    awaiting_payment (signed, never paid) -> Stax invoice re-sent + urgency
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
                try:
                    Stax(STAX_API_KEY.value).send_invoice_email(
                        b["stax_invoice_id"])   # re-send the payment link
                except Exception as e2:
                    print(f"invoice resend failed {b['booking_id']}: {e2}")
                emails.payment_nudge(RESEND_API_KEY.value, b)
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
@scheduler_fn.on_schedule(schedule="every day 09:00",
                          timezone=scheduler_fn.Timezone("America/Phoenix"),
                          region=REGION,
                          secrets=[STAX_API_KEY, RESEND_API_KEY,
                                   GRATUITY_SECRET, SIGNWELL_API_KEY])
def charge_balances(event: scheduler_fn.ScheduledEvent) -> None:
    _poll_paid_invoices()      # safety net: catch payments whose webhook dropped
    _send_gratuity_invites()   # post-event thank-you + gratuity link
    _send_questionnaire_reminders()   # nag unsubmitted questionnaires
    _chase_abandoned()                # recover stalled bookings
    db = firestore.client()
    now = datetime.now(timezone.utc)
    from google.cloud.firestore_v1.base_query import FieldFilter
    due = (db.collection("bookings")
             .where(filter=FieldFilter("status", "==", "confirmed"))
             .where(filter=FieldFilter("payment_option", "==", "standard"))
             .where(filter=FieldFilter("balance_due_at", "<=", now))
             .get())
    stax = Stax(STAX_API_KEY.value)
    for snap in due:
        b = snap.to_dict()
        if b.get("balance_paid_at") or b.get("balance_attempts", 0) >= 3:
            continue
        try:
            tx = stax.charge_card_on_file(
                b["stax_payment_method_id"], b["balance"],
                memo=f"Remaining balance — {b['package_name']} — "
                     f"{b['event_date']}")
            snap.reference.update({
                "balance_paid_at": firestore.SERVER_TIMESTAMP,
                "balance_transaction_id": tx.get("id"),
            })
            emails.notify_owner(
                RESEND_API_KEY.value, OWNER_EMAIL,
                f"BALANCE CHARGED — {b['client_names']} — ${b['balance']:,}",
                [f"Booking {b['booking_id']} balance charged successfully."])
        except Exception as e:
            attempts = b.get("balance_attempts", 0) + 1
            snap.reference.update({
                "balance_attempts": attempts,
                "balance_last_error": str(e)[:500],
            })
            emails.notify_owner(
                RESEND_API_KEY.value, OWNER_EMAIL,
                f"BALANCE CHARGE FAILED (attempt {attempts}/3) — "
                f"{b['client_names']}",
                [f"Booking {b['booking_id']}: {e}",
                 "Will retry tomorrow." if attempts < 3 else
                 "MAX ATTEMPTS REACHED — manual follow-up needed."])


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
                     secrets=[STAX_API_KEY, RESEND_API_KEY, GRATUITY_SECRET])
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
    if not b.get("stax_payment_method_id"):
        return _json(req, {"error": "no payment method on file"}, 409)

    stax = Stax(STAX_API_KEY.value)
    tx = stax.charge_card_on_file(
        b["stax_payment_method_id"], amount,
        memo=f"Team gratuity — {b['package_name']} — {b['event_date']}")
    snap.reference.collection("gratuities").add({
        "amount": amount, "at": firestore.SERVER_TIMESTAMP,
        "transaction_id": tx.get("id"),
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
