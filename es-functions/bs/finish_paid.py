"""Finish a paid ES reservation server-side (no form): python finish_paid.py PAY CHK [--go] [venue=..]
Dry run prints what it found; --go creates the booking + sends the SignWell contract."""
import os, sys, subprocess, json
P = "elizabeth-scott-738e5"
for k in ("SIGNWELL_API_KEY", "RESEND_API_KEY", "WHOP_API_KEY", "WHOP_WEBHOOK_SECRET", "GRATUITY_SECRET",
          "ZOHO_CLIENT_ID", "ZOHO_CLIENT_SECRET", "ZOHO_REFRESH_TOKEN"):
    os.environ[k] = subprocess.check_output(["gcloud", "secrets", "versions", "access", "latest",
                                             "--secret", k, "--project", P], text=True)
os.environ.update(GOOGLE_CLOUD_PROJECT=P, GCLOUD_PROJECT=P, PAYMENT_PROCESSOR="whop",
                  WHOP_ACCOUNT_ID="biz_FeVrtPXroSleTG")
sys.path.insert(0, os.path.expanduser("~/es-deploy/functions"))
os.chdir(os.path.expanduser("~/es-deploy/functions"))
import main as M
from google.cloud.firestore_v1.base_query import FieldFilter as F
pay, chk = sys.argv[1], sys.argv[2]
extra = dict(a.split("=", 1) for a in sys.argv[3:] if "=" in a)
db = M.firestore.client()
live = M._whop().get_payment(pay)
meta, ba = live.get("metadata") or {}, live.get("billing_address") or {}
email = meta.get("email", "")
print("PAYMENT", live.get("status"), M.Whop.payment_amount(live), json.dumps(meta))
lead = next((s.to_dict() for s in db.collection("leads").where(filter=F("whop_checkout_id", "==", chk)).get()), {})
print("LEAD", json.dumps({k: lead.get(k) for k in ("client_names", "email", "phone", "package_id", "payment_option",
      "event_date_raw", "status", "reservation_payload", "attr_venue")}, default=str))
for s in db.collection("inquiries").where(filter=F("email", "==", email)).get():
    d = s.to_dict(); print("INQUIRY", s.id, json.dumps({k: v for k, v in d.items() if k not in ("replies", "raw", "body")}, default=str)[:600])
for s in db.collection("bookings").where(filter=F("email", "==", email)).get():
    print("BOOKING EXISTS", s.id, s.to_dict().get("status"))
codes = [(s.id, s.to_dict()) for s in db.collection("discount_codes").get()
         if email.lower() in json.dumps(s.to_dict(), default=str).lower()]
for cid, c in codes:
    print("CODE", cid, c.get("amount"), "redeemed_by", c.get("redeemed_by"), "note", c.get("note"))
names = (meta.get("client_names") or lead.get("client_names") or "").split("&")
data = {"package_id": meta.get("package_id") or lead.get("package_id"),
        "payment_option": meta.get("payment_option") or lead.get("payment_option") or "pif",
        "client_names": meta.get("client_names") or lead.get("client_names"),
        "partner1_name": names[0].strip(), "partner2_name": names[1].strip() if len(names) > 1 else "",
        "email": email, "phone": lead.get("phone") or "",
        "mailing_address": ba.get("line1") or "",
        "city_state_zip": "%s, %s %s" % ((ba.get("city") or "").title(), ba.get("state") or "", ba.get("postal_code") or ""),
        "governing_state": ba.get("state") or "", "event_date": lead.get("event_date_raw") or "",
        "ceremony_venue": "", "agree_terms": True, "whop_payment_id": pay, "whop_checkout_id": chk,
        "discount_code": codes[0][0] if len(codes) == 1 else ""}
data.update(extra)
print("PROPOSED", json.dumps(data))
if "--go" in sys.argv:
    obj, code = M._book_safely(data, lead.get("client_ip") or "", "admin")
    print("RESULT", code, json.dumps(obj))
