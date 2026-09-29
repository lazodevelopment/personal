#!/usr/bin/env python3
"""JC-ATV-AUTOREPLY-0928: inquiry_webhook can mint a $200 / 72 h code for the automatic first reply.

Run from ~/bs:  python3 patch_inquiry_autocode.py   then deploy inquiry_webhook:
  gcloud functions deploy inquiry_webhook --gen2 --region=us-central1 --runtime=python312 --source=. \
    --entry-point=inquiry_webhook --trigger-http --allow-unauthenticated --set-secrets=RESEND_API_KEY=RESEND_API_KEY:latest

A POST with "auto_code": true (only the Gmail intake script sends it) gets {"code": {...}} back
and the inquiry is stored with the code; "auto_replied": true stores it as status "contacted"
since the couple has already been answered. Site-form posts are unchanged.
"""
import pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent
ANCHOR = '''           "source": "formspree" if "submission" in body else "site",
           "status": "new", "created_at": firestore.SERVER_TIMESTAMP}
    ref = db.collection("inquiries").add(doc)[1]
    if doc["sid"]:
        _link_session(db, doc["sid"], f"{doc['first_name']} {doc['last_name']}".strip(), email)
    return _json(req, {"ok": True, "id": ref.id})'''
NEW = '''           "source": "formspree" if "submission" in body else
                     "gmail-intake" if sub.get("auto_code") or sub.get("auto_replied") else "site",
           "status": "contacted" if sub.get("auto_replied") else "new",
           "created_at": firestore.SERVER_TIMESTAMP}
    # JC-ATV-AUTOREPLY-0928: the Gmail intake script answers every marketplace
    # inquiry within minutes and asks for a code to put in that reply.
    code = None
    if sub.get("auto_code"):
        try:
            code = _mint_code(db, NUDGE_CODE_AMOUNT, NUDGE_CODE_HOURS,
                              f"auto-reply \u2014 {email}")
            doc["auto_code"] = code["code"]
        except Exception as e:
            print(f"auto-reply code mint failed (non-fatal): {e}")
    if sub.get("auto_replied"):
        doc["auto_replied_at"] = firestore.SERVER_TIMESTAMP
    ref = db.collection("inquiries").add(doc)[1]
    if doc["sid"]:
        _link_session(db, doc["sid"], f"{doc['first_name']} {doc['last_name']}".strip(), email)
    return _json(req, {"ok": True, "id": ref.id, "code": code})'''

p = ROOT / "main.py"
src = p.read_text(encoding="utf-8")
if "JC-ATV-AUTOREPLY-0928" in src:
    print("already applied"); sys.exit(0)
if "NUDGE_CODE_AMOUNT" not in src:
    print("patch_nudge_code.py must be applied first (NUDGE_CODE_AMOUNT missing) - nothing written"); sys.exit(1)
if src.count(ANCHOR) != 1:
    print("anchor found %d times, expected 1 - nothing written" % src.count(ANCHOR)); sys.exit(1)
(ROOT / "main.py.bak-autocode0928").write_text(src, encoding="utf-8", newline="")
p.write_text(src.replace(ANCHOR, NEW), encoding="utf-8", newline="")
print("main.py patched (backup main.py.bak-autocode0928)")
