"""SignWell API client — Elizabeth Scott Weddings booking flow.
Build: JC-ES-SIGNWELL-0818-005 (v1 · 2026-08-18 · derived from Atavia)

Docs: https://developers.signwell.com (verified 2026-07-15)
- POST /api/v1/documents        create + send document (text_tags: true)
- GET  /api/v1/documents/{id}/completed_pdf?url_only=true
- POST /api/v1/hooks            register webhook callback

Auth: X-Api-Key header. Same Danbren SignWell account as Atavia.
"""

import base64
import requests

BASE = "https://www.signwell.com/api/v1"


class SignWell:
    def __init__(self, api_key, test_mode=True):
        self.key = api_key
        self.test_mode = test_mode

    def _headers(self):
        return {"X-Api-Key": self.key, "Content-Type": "application/json"}

    def send_contract(self, pdf_bytes, booking_id, client_name, client_email,
                      redirect_url=None):
        """Create + send the contract for signature. Returns SignWell response.

        The PDF carries invisible text tags ({{s:1:y:...}}, {{af_d_s:1}})
        placed by the contract generator, so text_tags=True does all field
        placement — no coordinates needed.
        """
        payload = {
            "test_mode": self.test_mode,
            "text_tags": True,
            "files": [{
                "name": f"Elizabeth-Scott-Weddings-Agreement-{booking_id}.pdf",
                "file_base64": base64.b64encode(pdf_bytes).decode(),
            }],
            "name": f"Elizabeth Scott Weddings Service Agreement — {client_name}",
            "subject": "Your Elizabeth Scott Weddings Service Agreement",
            "message": (
                "Hi {name},\n\nYour Elizabeth Scott Weddings service agreement "
                "is ready to sign. Once signed, you'll receive a secure link to "
                "pay your retainer and officially reserve your date.\n\nWe "
                "can't wait to celebrate with you!\n\n— The Elizabeth Scott "
                "Weddings Team"
            ).format(name=client_name.split("&")[0].strip()),
            "recipients": [{
                "id": "1",
                "name": client_name,
                "email": client_email,
            }],
            "custom_requester_name": "Elizabeth Scott Weddings",
            "custom_requester_email": "hello@elizabethscottweddings.com",
            "allow_decline": True,
            "allow_reassign": False,
            "reminders": True,
            "metadata": {"booking_id": booking_id},
        }
        if redirect_url:
            payload["redirect_url"] = redirect_url
        r = requests.post(f"{BASE}/documents", json=payload,
                          headers=self._headers(), timeout=30)
        r.raise_for_status()
        return r.json()

    def get_document(self, document_id):
        """Fetch authoritative document state (used for webhook verification)."""
        r = requests.get(f"{BASE}/documents/{document_id}",
                         headers=self._headers(), timeout=30)
        r.raise_for_status()
        return r.json()

    def completed_pdf_url(self, document_id):
        r = requests.get(
            f"{BASE}/documents/{document_id}/completed_pdf",
            params={"url_only": "true"},
            headers=self._headers(), timeout=30)
        r.raise_for_status()
        return r.json().get("file_url")

    def download_completed_pdf(self, document_id):
        url = self.completed_pdf_url(document_id)
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        return r.content

    def register_webhook(self, callback_url):
        r = requests.post(f"{BASE}/hooks", json={"callback_url": callback_url},
                          headers=self._headers(), timeout=30)
        r.raise_for_status()
        return r.json()

    def list_webhooks(self):
        r = requests.get(f"{BASE}/hooks", headers=self._headers(), timeout=30)
        r.raise_for_status()
        return r.json()
