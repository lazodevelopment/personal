"""Zoho Payments (US) API client — Atavia / Elizabeth Scott booking flow.

Base: https://payments.zoho.com/api/v1  ·  Auth: OAuth2 refresh token
Docs: https://www.zoho.com/us/payments/api/v1/introduction/

Flow (mirrors lib/stax.py so main.py changes are swaps, not a rewrite):
  1. zoho_session (HTTPS)        -> create_customer() + create_pm_session();
                                    the /book page opens the Zoho widget in
                                    transaction_type="add" mode with both ids
  2. widget returns payment_method_id -> posted with the booking; book_submit
                                    verifies it via get_pm_session()
  3. signwell_webhook            -> charge_saved_method() (retainer / PIF)
  4. fallback                    -> create_payment_link() emailed by Zoho;
                                    zoho_webhook confirms on payment_link.paid
  5. charge_balances / gratuity  -> charge_saved_method() again

Every request needs ?account_id=. Access tokens live 1h; we mint one per
client instance from the refresh token (a Cloud Function instance rarely
lives longer than that, and a stale token just fails closed with a 401).
"""

import time
import requests

BASE = "https://payments.zoho.com/api/v1"
ACCOUNTS = "https://accounts.zoho.com/oauth/v2/token"


class ZohoError(requests.HTTPError):
    pass


def _raise_with_body(r):
    """raise_for_status, but include Zoho's body — their errors name the
    offending field, and a bare 400 tells you nothing."""
    if r.status_code >= 400:
        raise ZohoError(f"{r.status_code} {r.reason} for {r.url} :: "
                        f"{r.text[:600]}", response=r)
    # Zoho also signals failures inside a 200 with code != 0
    try:
        body = r.json()
    except ValueError:
        raise ZohoError(f"non-JSON response from {r.url}: {r.text[:300]}",
                        response=r)
    if isinstance(body, dict) and str(body.get("code", 0)) not in ("0",):
        raise ZohoError(f"Zoho code={body.get('code')} :: "
                        f"{body.get('message')} ({r.url})", response=r)
    return body


class Zoho:
    def __init__(self, account_id, client_id, client_secret, refresh_token):
        self.account_id = str(account_id)
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self._token = None
        self._token_exp = 0

    # ------------------------------------------------------------- auth ---
    def _access_token(self):
        if self._token and time.time() < self._token_exp - 60:
            return self._token
        r = requests.post(ACCOUNTS, params={
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
        }, timeout=30)
        if r.status_code >= 400 or "access_token" not in r.json():
            raise ZohoError(f"OAuth refresh failed: {r.status_code} "
                            f"{r.text[:300]}", response=r)
        j = r.json()
        self._token = j["access_token"]
        self._token_exp = time.time() + int(j.get("expires_in", 3600))
        return self._token

    def _headers(self):
        return {"Authorization": f"Zoho-oauthtoken {self._access_token()}",
                "Content-Type": "application/json",
                "Accept": "application/json"}

    def _req(self, method, path, **kw):
        params = {"account_id": self.account_id, **kw.pop("params", {})}
        r = requests.request(method, f"{BASE}{path}", params=params,
                             headers=self._headers(), timeout=30, **kw)
        return _raise_with_body(r)

    @staticmethod
    def _money(x):
        return round(float(x), 2)

    @staticmethod
    def _meta(d):
        """Zoho meta_data is a list of {key,value}; max 5, key <= 20 chars."""
        return [{"key": str(k)[:20], "value": str(v)[:100]}
                for k, v in list((d or {}).items())[:5]]

    # -------------------------------------------------------- customers ---
    def create_customer(self, name, email, phone="", meta=None):
        payload = {"name": name[:100], "email": email}
        if phone:
            payload["phone"] = phone
        if meta:
            payload["meta_data"] = self._meta(meta)
        return self._req("POST", "/customers", json=payload)["customer"]

    def get_customer(self, customer_id):
        return self._req("GET", f"/customers/{customer_id}")["customer"]

    # ------------------------------------------ payment method sessions ---
    def create_pm_session(self, customer_id, description=""):
        """A session the widget uses to tokenize a card WITHOUT charging it."""
        payload = {"customer_id": customer_id}
        if description:
            payload["description"] = description[:100]
        return self._req("POST", "/paymentmethodsessions",
                         json=payload)["payment_method_session"]

    def get_pm_session(self, session_id):
        """Authoritative check that the widget really saved a method on this
        session (status + payment_method.payment_method_id)."""
        return self._req("GET", f"/paymentmethodsessions/{session_id}"
                         )["payment_method_session"]

    def get_payment_method(self, payment_method_id):
        return self._req("GET", f"/paymentmethods/{payment_method_id}"
                         )["payment_method"]

    # ---------------------------------------------------------- charges ---
    def charge_saved_method(self, customer_id, payment_method_id, amount,
                            description, meta=None, descriptor=None):
        """Merchant-initiated (off-session) charge to a stored method:
        retainer at signature, 14-day balance, gratuity.

        Returns the payment dict. Caller MUST check payment["status"] ==
        "succeeded" — Zoho can return a 200 with status "failed"/"pending".
        """
        payload = {
            "customer_id": customer_id,
            "payment_method_id": payment_method_id,
            "amount": self._money(amount),
            "currency": "USD",
            "customer_on_session": False,
            "description": description[:200],
        }
        if descriptor:
            payload["statement_descriptor"] = descriptor[:22]
        if meta:
            payload["meta_data"] = self._meta(meta)
        return self._req("POST", "/payments", json=payload)["payment"]

    def get_payment(self, payment_id):
        return self._req("GET", f"/payments/{payment_id}")["payment"]

    def refund(self, payment_id, amount, description="",
               reason="requested_by_customer"):
        payload = {"amount": self._money(amount), "reason": reason,
                   "type": "initiated_by_merchant"}
        if description:
            payload["description"] = description[:200]
        return self._req("POST", f"/payments/{payment_id}/refunds",
                         json=payload)["refund"]

    # ---------------------------------------------------- payment links ---
    def create_payment_link(self, amount, description, email, reference_id,
                            phone="", expires_at=None, return_url=None,
                            meta=None, send_email=True):
        """Hosted-page fallback (replaces the Stax hosted invoice). Zoho
        emails the link when notify_customer.email is true.

        NOTE: a link payment does NOT store a payment method on the
        customer, so link-paid bookings have no card on file — the balance
        is collected with a second link (see charge_balances).
        """
        payload = {
            "amount": self._money(amount),
            "currency": "USD",
            "description": description[:200],
            "email": email,
            "reference_id": str(reference_id)[:100],
            "notify_customer": {"email": bool(send_email)},
            "configurations": {"allowed_payment_methods": ["card"]},
        }
        if phone:
            payload["phone"] = phone
        if expires_at:
            payload["expires_at"] = expires_at        # yyyy-MM-dd
        if return_url:
            payload["return_url"] = return_url
        if meta:
            payload["meta_data"] = self._meta(meta)
        return self._req("POST", "/paymentlinks", json=payload)["payment_links"]

    def get_payment_link(self, payment_link_id):
        """Authoritative link fetch (webhook verification + safety poller).
        status: active | paid | canceled | expired"""
        return self._req("GET", f"/paymentlinks/{payment_link_id}"
                         )["payment_links"]

    def cancel_payment_link(self, payment_link_id):
        return self._req("PUT", f"/paymentlinks/{payment_link_id}/cancel")
