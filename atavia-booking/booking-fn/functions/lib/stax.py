"""Stax (Fattmerchant) API client — Atavia booking flow.

Base: https://apiprod.fattlabs.com  ·  Auth: Bearer <API key>

Flow:
  1. create_customer()             -> customer_id stored on booking
  2. create_invoice() + send email -> hosted payment page (zero PCI on our
                                      stack); Stax stores card on file after
                                      first payment
  3. webhook (create_transaction)  -> confirms deposit / PIF payment;
                                      payment_method_id captured for later
  4. charge_card_on_file()         -> 14-day balance auto-charge, overtime,
                                      gratuity

⚠ VERIFY-ON-TEST-KEY: endpoint paths and payload shapes below follow Stax's
public Fattmerchant API docs and must be smoke-tested against the sandbox the
moment JC's test key arrives. Marked [VERIFY] inline.
"""

import re
import requests

BASE = "https://apiprod.fattlabs.com"


def _raise_with_body(r):
    """raise_for_status, but include Stax's response body (their 422s name
    the exact invalid fields)."""
    if r.status_code >= 400:
        raise requests.HTTPError(
            f"{r.status_code} {r.reason} for {r.url} :: {r.text[:600]}",
            response=r)


class Stax:
    def __init__(self, api_key):
        self.key = api_key

    def _headers(self):
        return {"Authorization": f"Bearer {self.key}",
                "Content-Type": "application/json",
                "Accept": "application/json"}

    @staticmethod
    def _clean_phone(phone):
        """Stax requires bare digits (10, or 11 with leading 1)."""
        d = re.sub(r"\D", "", phone or "")
        if len(d) == 11 and d.startswith("1"):
            d = d[1:]
        return d if len(d) == 10 else ""

    def create_customer(self, first, last, email, phone="", address_1="",
                        city="", state="", zip_code=""):
        phone = self._clean_phone(phone)
        payload = {
            "firstname": first, "lastname": last, "email": email,
            "phone": phone, "address_1": address_1, "address_city": city,
            "address_state": state, "address_zip": zip_code,
            "allow_invoice_credit_card_payments": True,
        }
        r = requests.post(f"{BASE}/customer", json=payload,
                          headers=self._headers(), timeout=30)  # [VERIFY]
        _raise_with_body(r)
        return r.json()

    def create_invoice(self, customer_id, total, memo, line_items,
                       send_now=True):
        """Create a hosted invoice and email it to the customer.

        line_items: [{"id": "...", "item": "...", "details": "...",
                      "quantity": 1, "price": 500.00}]
        """
        payload = {
            "customer_id": customer_id,
            "total": round(float(total), 2),
            "meta": {"lineItems": line_items, "memo": memo,
                     "subtotal": round(float(total), 2), "tax": 0},
            "url": "https://app.staxpayments.com/#/bill/",  # hosted payment page
        }
        r = requests.post(f"{BASE}/invoice", json=payload,
                          headers=self._headers(), timeout=30)
        _raise_with_body(r)
        inv = r.json()
        if send_now:
            self.send_invoice_email(inv["id"])
        return inv

    def send_invoice_email(self, invoice_id):
        r = requests.put(f"{BASE}/invoice/{invoice_id}/send/email",
                         json={}, headers=self._headers(), timeout=30)  # [VERIFY]
        _raise_with_body(r)
        return r.json()

    def get_transaction(self, transaction_id):
        """Authoritative transaction fetch (webhook verification)."""
        r = requests.get(f"{BASE}/transaction/{transaction_id}",
                         headers=self._headers(), timeout=30)
        _raise_with_body(r)
        return r.json()

    def get_invoice(self, invoice_id):
        """Authoritative invoice fetch (safety poller)."""
        r = requests.get(f"{BASE}/invoice/{invoice_id}",
                         headers=self._headers(), timeout=30)
        _raise_with_body(r)
        return r.json()

    def get_customer_payment_methods(self, customer_id):
        r = requests.get(f"{BASE}/customer/{customer_id}/payment-method",
                         headers=self._headers(), timeout=30)  # [VERIFY]
        _raise_with_body(r)
        return r.json()

    def charge_card_on_file(self, payment_method_id, total, memo,
                            line_items=None):
        """Charge a stored payment method (balance, overtime, gratuity)."""
        payload = {
            "payment_method_id": payment_method_id,
            "total": round(float(total), 2),
            "pre_auth": False,
            "meta": {"memo": memo, "subtotal": round(float(total), 2),
                     "tax": 0, "lineItems": line_items or []},
        }
        r = requests.post(f"{BASE}/charge", json=payload,
                          headers=self._headers(), timeout=30)  # [VERIFY]
        _raise_with_body(r)
        return r.json()
