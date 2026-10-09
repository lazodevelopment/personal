"""Whop Payments API client — Atavia booking flow, behind PAYMENT_PROCESSOR=whop.

Base: https://api.whop.com/api/v1  ·  Auth: Bearer <account API key>
Docs: https://docs.whop.com/developer/guides/save-payment-methods

Mirrors lib/zoho.py method-for-method so main.py can pick a client by the
booking's `processor` field and call the same names with the same shapes.
Return dicts are NORMALISED to Zoho's vocabulary so the callers' status
checks ("succeeded", "paid") keep working unchanged:

  charge_saved_method()  -> {"payment_id", "status": succeeded|pending|failed,
                             "failure_code", "raw"}
  create_payment_link()  -> {"payment_link_id", "url", "plan_id"}
  get_payment_link()     -> {"status": paid|active, "payments": [...], "meta_data"}
  refund()               -> {"refund_id", "status"}

Flow (same four steps as Zoho, different mechanics):
  1. /book page mounts the Whop CardElement in mode="setup", collects a
     confirmation token client-side (PAN never touches us: PCI SAQ-A)
  2. whop_setup (HTTPS) turns the token into a SETUP INTENT -> payment_method
     id + member id, which the page then posts with the booking
  3. signwell_webhook -> charge_saved_method() (retainer / PIF), off-session
  4. fallback -> create_payment_link(): a hosted checkout configuration we
     email ourselves (Whop does not email it); whop_webhook confirms on
     payment.succeeded, and the daily poller lists payments by checkout id
  5. charge_balances / gratuity -> charge_saved_method() again

Whop processes off-session charges asynchronously: POST /payments returns
immediately, usually "pending". charge_saved_method() polls the payment for
a few seconds so the synchronous callers get a settled answer in the normal
case; if it is still pending at the deadline the caller treats it as a
failure for retry purposes and whop_webhook reconciles payment.succeeded.
"""

import base64
import hashlib
import hmac
import time
import requests

BASE = "https://api.whop.com/api/v1"
SANDBOX_BASE = "https://sandbox-api.whop.com/api/v1"
CHECKOUT_HOST = "https://whop.com"

# Whop payment statuses -> Zoho-style words the rest of main.py already checks
_PAID = ("paid",)
_FAILED = ("failed", "void", "uncollectible", "unresolved", "canceled")
_PENDING = ("pending", "open", "draft", "authorized", "processing")


class WhopError(requests.HTTPError):
    pass


def _raise_with_body(r):
    if r.status_code >= 400:
        raise WhopError(f"{r.status_code} {r.reason} for {r.url} :: "
                        f"{r.text[:600]}", response=r)
    if r.status_code == 204 or not r.content:
        return {}
    try:
        return r.json()
    except ValueError:
        raise WhopError(f"non-JSON response from {r.url}: {r.text[:300]}",
                        response=r)


def normalise_status(s):
    s = str(s or "").lower()
    if s in _PAID:
        return "succeeded"
    if s in _FAILED:
        return "failed"
    return "pending"


class Whop:
    def __init__(self, account_id, api_key, sandbox=False,
                 charge_poll_seconds=20):
        self.account_id = str(account_id)          # biz_xxxxxxxxxxxxxx
        self.api_key = api_key
        self.base = SANDBOX_BASE if sandbox else BASE
        self.charge_poll_seconds = charge_poll_seconds

    # ------------------------------------------------------------- http ---
    def _headers(self):
        return {"Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"}

    def _req(self, method, path, **kw):
        r = requests.request(method, f"{self.base}{path}",
                             headers=self._headers(), timeout=30, **kw)
        return _raise_with_body(r)

    @staticmethod
    def _money(x):
        return round(float(x), 2)

    @staticmethod
    def _descriptor(d):
        """Whop only accepts custom statement descriptors that start with
        "WHOP*" (API: 'Custom statement descriptor must start with WHOP*'),
        max 22 chars. "ELIZABETH SCOTT WED" -> "WHOP* ELIZABETH SCOTT"."""
        d = str(d or "").strip()
        if not d:
            return None
        if not d.upper().startswith("WHOP*"):
            d = "WHOP* " + d
        return d[:22].rstrip()

    @staticmethod
    def _meta(d):
        """Whop metadata is a flat object. Keep values short strings."""
        return {str(k)[:40]: str(v)[:200] for k, v in (d or {}).items()}

    # ------------------------------------------------- setup intents -------
    def create_setup_intent(self, confirmation_token, email="", meta=None,
                            return_url=None):
        """Turn the CardElement's confirmation token into a saved payment
        method. status: processing | succeeded | canceled | requires_action.
        requires_action -> hand client_secret back to the page for
        handleNextAction(), then re-check with get_setup_intent()."""
        payload = {"account_id": self.account_id,
                   "confirmation_token": confirmation_token,
                   "currency": "usd"}
        if email:
            payload["email"] = email
        if meta:
            payload["metadata"] = self._meta(meta)
        if return_url:
            payload["return_url"] = return_url
        return self._req("POST", "/setup_intents", json=payload)

    def create_setup_checkout(self, email="", meta=None, redirect_url=None,
                              card_only=True):
        """Setup-MODE checkout configuration: the hosted / embedded Whop
        checkout saves a card and charges nothing ("No charge today").

        This is the path that actually works on the live account. Direct
        setup intents from an Elements confirmation token were refused with
        a generic "could not be processed right now" (2026-10-06, five
        attempts, hosted setup succeeded immediately), so the book page
        mounts the CheckoutElement with this configuration instead and gets
        the setup intent id back from onComplete / the returnUrl.
        Returns {"checkout_id", "url", "raw"}."""
        payload = {"mode": "setup", "account_id": self.account_id,
                   "currency": "usd"}
        if meta:
            payload["metadata"] = self._meta(meta)
        if redirect_url:
            payload["redirect_url"] = redirect_url
        if card_only:
            payload["payment_method_configuration"] = {
                "enabled": ["card"], "disabled": [],
                "include_platform_defaults": False}
        raw = self._req("POST", "/checkout_configurations", json=payload)
        url = raw.get("purchase_url") or ""
        if url.startswith("/"):
            url = CHECKOUT_HOST + url
        return {"checkout_id": raw.get("id"), "url": url, "raw": raw}

    def create_payment_checkout(self, amount, title, meta=None, redirect_url=None,
                                card_only=True, descriptor=None):
        """PAYMENT-mode checkout configuration for the embedded CheckoutElement:
        the buyer pays `amount` now and Whop keeps the card on file for later
        off-session charges (the balance, gratuity). This is the reservation
        flow since 2026-10-06: Whop refuses setup-mode (no-charge) card saves
        from guest buyers on this company, but paid checkouts go through.
        Returns {"checkout_id", "url", "plan_id", "raw"}."""
        meta = dict(meta or {})
        payload = {
            "mode": "payment",
            "plan": {
                "company_id": self.account_id,
                "currency": "usd",
                "plan_type": "one_time",   # plan title max 30 chars (Whop validation); product title may be longer
                "initial_price": self._money(amount),
                "renewal_price": 0,
                "title": title[:30],
                "force_create_new_plan": True,
                "product": {
                    "external_identifier": self._charge_ref(meta, amount),
                    "title": title[:100],
                    "visibility": "hidden",
                },
            },
            "metadata": self._meta(meta),
        }
        if descriptor:
            payload["plan"]["product"]["custom_statement_descriptor"] = self._descriptor(descriptor)
        if redirect_url:
            payload["redirect_url"] = redirect_url
        if card_only:
            payload["payment_method_configuration"] = {
                "enabled": ["card"], "disabled": [],
                "include_platform_defaults": False}
        raw = self._req("POST", "/checkout_configurations", json=payload)
        url = raw.get("purchase_url") or ""
        if url.startswith("/"):
            url = CHECKOUT_HOST + url
        return {"checkout_id": raw.get("id"), "url": url,
                "plan_id": (raw.get("plan") or {}).get("id"), "raw": raw}

    @staticmethod
    def payment_ids(pay):
        """(member_id, payment_method_id) from a payment dict; flat live
        shape first, nested docs shape second."""
        pay = pay or {}
        member = pay.get("member") or {}
        pm = pay.get("payment_method") or {}
        return (pay.get("member_id") or member.get("id") or None,
                pay.get("payment_method_id") or pm.get("id") or None)

    @staticmethod
    def payment_amount(pay):
        """Settled amount in dollars from a payment dict (total may be a
        money object {amount:"500.00"} or a plain number)."""
        pay = pay or {}
        for k in ("total", "amount", "subtotal"):
            v = pay.get(k)
            if isinstance(v, dict) and v.get("amount") is not None:
                try:
                    return float(v["amount"])
                except (TypeError, ValueError):
                    pass
            elif v is not None:
                try:
                    return float(v)
                except (TypeError, ValueError):
                    pass
        return 0.0

    def get_setup_intent(self, setup_intent_id):
        """Authoritative check that the setup really saved a method:
        status == succeeded and payment_method.id present."""
        return self._req("GET", f"/setup_intents/{setup_intent_id}")

    @staticmethod
    def setup_ids(si):
        """(member_id, payment_method_id) from a setup-intent dict, either
        of which may be None while the intent is unsettled.

        The live API (2026-09-29 version) returns FLAT ids (member_id,
        payment_method_id); the docs show nested objects (member.id,
        payment_method.id). Accept both."""
        si = si or {}
        member = si.get("member") or {}
        pm = si.get("payment_method") or {}
        return (si.get("member_id") or member.get("id") or None,
                si.get("payment_method_id") or pm.get("id") or None)

    @staticmethod
    def setup_error(si):
        """Human-readable failure reason from a setup intent, or ''. Live
        responses carry last_setup_error.message; docs say error_message."""
        si = si or {}
        err = si.get("last_setup_error") or {}
        return str(si.get("error_message") or err.get("message")
                   or err.get("code") or "")

    def get_payment_method(self, payment_method_id):
        return self._req("GET", f"/payment_methods/{payment_method_id}")

    @staticmethod
    def pm_display(pm):
        """(brand, last4) from a Whop payment_method dict, for owner emails.
        Same tuple _pm_display() builds for Zoho."""
        card = (pm or {}).get("card") or {}
        return (str(card.get("brand") or "card")[:20],
                str(card.get("last4") or "")[:4])

    # ---------------------------------------------------------- charges ---
    def charge_saved_method(self, customer_id, payment_method_id, amount,
                            description, meta=None, descriptor=None):
        """Merchant-initiated (off-session) charge to a stored method.
        `customer_id` is the Whop MEMBER id (mber_...), stored in the
        booking as whop_customer_id so the field name lines up with Zoho's.

        Returns {"payment_id", "status", "failure_code", "raw"} with status
        already normalised; callers check status == "succeeded".
        """
        meta = dict(meta or {})
        plan = {"currency": "usd",
                "plan_type": "one_time",
                "initial_price": self._money(amount),
                "renewal_price": 0,
                "title": description[:30],
                "force_create_new_plan": True,
                "product": {
                    # one hidden product per charge keeps Whop's catalogue
                    # from exposing a "Retainer deposit" page to the public
                    "external_identifier": self._charge_ref(meta, amount),
                    "title": description[:100],
                    "visibility": "hidden",
                }}
        if descriptor:
            plan["product"]["custom_statement_descriptor"] = self._descriptor(descriptor)
        payload = {"account_id": self.account_id,
                   "member_id": customer_id,
                   "payment_method_id": payment_method_id,
                   "plan": plan,
                   "capture": True,
                   "metadata": self._meta(meta)}
        raw = self._req("POST", "/payments", json=payload)
        return self._settle(raw)

    @staticmethod
    def _charge_ref(meta, amount):
        bits = [str(meta.get("booking_id") or "booking"),
                str(meta.get("kind") or "charge"),
                str(int(time.time()))]
        return "-".join(bits)[:100]

    def _settle(self, raw):
        """Poll a freshly created payment until it leaves pending, or until
        charge_poll_seconds elapse. Whop settles card charges in well under
        that in practice; the deadline only matters on a slow issuer."""
        pid = (raw or {}).get("id")
        status = normalise_status((raw or {}).get("status"))
        deadline = time.time() + self.charge_poll_seconds
        wait = 1.0
        while status == "pending" and pid and time.time() < deadline:
            time.sleep(wait)
            wait = min(wait * 1.5, 4.0)
            try:
                raw = self.get_payment(pid)
            except WhopError as e:
                print(f"whop: poll {pid} failed: {e}")
                break
            status = normalise_status(raw.get("status"))
        return {"payment_id": pid, "status": status,
                "failure_code": (raw or {}).get("failure_message") or "",
                "raw": raw}

    def get_payment(self, payment_id):
        return self._req("GET", f"/payments/{payment_id}")

    def refund(self, payment_id, amount, description="",
               reason="requested_by_customer"):
        payload = {}
        if amount:
            payload["partial_amount"] = self._money(amount)
        raw = self._req("POST", f"/payments/{payment_id}/refund", json=payload)
        refunds = raw.get("refunds") or []
        last = refunds[-1] if refunds else {}
        return {"refund_id": last.get("id"),
                "status": last.get("status") or "succeeded",
                "raw": raw}

    # ---------------------------------------------------- payment links ---
    def create_payment_link(self, amount, description, email, reference_id,
                            phone="", expires_at=None, return_url=None,
                            meta=None, send_email=True):
        """Hosted-checkout fallback. Whop does NOT email the link; the caller
        sends it (emails.payment_nudge / balance_charge_failed), so
        send_email is accepted for signature parity and ignored.

        NOTE: like a Zoho link, a hosted-checkout payment stores no
        payment method we can reuse, so link-paid bookings have no card on
        file and the balance is collected with a second link.
        """
        meta = dict(meta or {})
        meta.setdefault("reference_id", str(reference_id))
        payload = {
            "mode": "payment",
            "plan": {
                "company_id": self.account_id,
                "currency": "usd",
                "plan_type": "one_time",
                "initial_price": self._money(amount),
                "renewal_price": 0,
                "title": description[:30],
                "force_create_new_plan": True,
                "product": {
                    "external_identifier": str(reference_id)[:100],
                    "title": description[:100],
                    "visibility": "hidden",
                },
            },
            "metadata": self._meta(meta),
        }
        if return_url:
            payload["redirect_url"] = return_url
        raw = self._req("POST", "/checkout_configurations", json=payload)
        url = raw.get("purchase_url") or ""
        if url.startswith("/"):
            url = CHECKOUT_HOST + url
        return {"payment_link_id": raw.get("id"), "url": url,
                "plan_id": (raw.get("plan") or {}).get("id"), "raw": raw}

    def get_payment_link(self, payment_link_id):
        """Zoho-shaped view of a checkout configuration: status paid|active
        plus the succeeded payments against it. Whop has no status on the
        configuration itself, so we list payments filtered by it."""
        cfg = self._req("GET", f"/checkout_configurations/{payment_link_id}")
        page = self._req("GET", "/payments", params={
            "account_id": self.account_id,
            "checkout_configuration_ids[]": [payment_link_id],
            "first": 10})
        items = page.get("data") if isinstance(page, dict) else page
        paid = [{"payment_id": p.get("id"),
                 "status": normalise_status(p.get("status")),
                 "raw": p}
                for p in (items or []) if normalise_status(p.get("status")) == "succeeded"]
        return {"payment_link_id": payment_link_id,
                "status": "paid" if paid else "active",
                "payments": paid,
                "url": CHECKOUT_HOST + cfg.get("purchase_url", "")
                if str(cfg.get("purchase_url", "")).startswith("/")
                else cfg.get("purchase_url"),
                "meta_data": [{"key": k, "value": v}
                              for k, v in (cfg.get("metadata") or {}).items()],
                "plan_id": (cfg.get("plan") or {}).get("id")}

    def cancel_payment_link(self, payment_link_id):
        """Best effort: Whop has no cancel for a checkout configuration, so
        archive its plan instead, which stops the hosted page from selling."""
        cfg = self._req("GET", f"/checkout_configurations/{payment_link_id}")
        plan_id = (cfg.get("plan") or {}).get("id")
        if not plan_id:
            return {}
        return self._req("PATCH", f"/plans/{plan_id}",
                         json={"visibility": "archived"})

    # --------------------------------------------------------- webhooks ---
    @staticmethod
    def verify_webhook(headers, raw_body, secret, tolerance=300):
        """Standard Webhooks verification (webhook-id / -timestamp /
        -signature headers; HMAC-SHA256 over "id.timestamp.body").
        Whop secrets are `ws_...`; the spec's `whsec_` form is base64. Try the
        raw string first (Whop's documented form), then the decoded form,
        so a dashboard copy in either shape verifies. Returns True/False;
        never raises."""
        try:
            h = {k.lower(): v for k, v in dict(headers).items()}
            mid = h.get("webhook-id", "")
            ts = h.get("webhook-timestamp", "")
            sigs = h.get("webhook-signature", "")
            if not (mid and ts and sigs and secret):
                return False
            if abs(time.time() - int(ts)) > tolerance:
                return False
            body = raw_body if isinstance(raw_body, bytes) else str(raw_body).encode()
            signed = f"{mid}.{ts}.".encode() + body
            keys = [secret.encode()]
            for prefix in ("ws_", "whsec_"):
                if secret.startswith(prefix):
                    try:
                        keys.append(base64.b64decode(secret[len(prefix):] + "=="))
                    except Exception:
                        pass
            expected = {base64.b64encode(hmac.new(k, signed, hashlib.sha256)
                                         .digest()).decode() for k in keys}
            for part in sigs.split():
                v, _, sig = part.partition(",")
                if v == "v1" and any(hmac.compare_digest(sig, e) for e in expected):
                    return True
            return False
        except Exception:
            return False
