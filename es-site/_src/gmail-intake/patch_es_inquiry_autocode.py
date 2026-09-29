#!/usr/bin/env python3
"""JC-ESW-AUTOREPLY-0928: Elizabeth Scott inquiry_webhook mints a $200 / 72 h inquiry code for the
automatic Zola reply. Same change as Atavia's patch_inquiry_autocode.py, but self-contained (the
ES backend has no NUDGE_CODE_* constants).

Run in the Cloud Shell that holds the elizabeth-scott-738e5 functions, from the folder with main.py:
  python3 patch_es_inquiry_autocode.py
then deploy:
  gcloud functions deploy inquiry_webhook --gen2 --region=us-central1 --runtime=python312 --source=. \
    --entry-point=inquiry_webhook --trigger-http --allow-unauthenticated --set-secrets=RESEND_API_KEY=RESEND_API_KEY:latest

Anchor-and-assert: nothing is written unless the anchor is found exactly once. If it prints
"anchor found 0 times", paste the inquiry_webhook function back and the anchor will be adjusted.
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
    # JC-ESW-AUTOREPLY-0928: the Gmail intake script answers every Zola inquiry
    # within minutes and asks for an inquiry code to put in that reply.
    code = None
    if sub.get("auto_code"):
        try:
            code = _mint_code(db, AUTO_CODE_AMOUNT, AUTO_CODE_HOURS,
                              f"auto-reply — {email}")
            doc["auto_code"] = code["code"]
        except Exception as e:
            print(f"auto-reply code mint failed (non-fatal): {e}")
    if sub.get("auto_replied"):
        doc["auto_replied_at"] = firestore.SERVER_TIMESTAMP
    ref = db.collection("inquiries").add(doc)[1]
    if doc["sid"]:
        _link_session(db, doc["sid"], f"{doc['first_name']} {doc['last_name']}".strip(), email)
    return _json(req, {"ok": True, "id": ref.id, "code": code})'''
CONST_ANCHOR = "def inquiry_webhook("
CONST_NEW = '''AUTO_CODE_AMOUNT = 200   # JC-ESW-AUTOREPLY-0928: $ off carried by the automatic Zola reply
AUTO_CODE_HOURS = 72


'''

p = ROOT / "main.py"
src = p.read_text(encoding="utf-8")
if "JC-ESW-AUTOREPLY-0928" in src:
    print("already applied"); sys.exit(0)
if "def _mint_code(" not in src:
    print("_mint_code missing from this main.py - this is not the file the admin's Issue code button runs from; nothing written"); sys.exit(1)
for a in (ANCHOR, CONST_ANCHOR):
    if src.count(a) != 1:
        print("anchor found %d times, expected 1 - nothing written:\n%s" % (src.count(a), a[:80])); sys.exit(1)
# the decorator line sits right above "def inquiry_webhook(": put the constants above the decorator
i = src.index(CONST_ANCHOR)
deco = src.rfind("\n@", 0, i)
out = src[:deco + 1] + CONST_NEW + src[deco + 1:]
out = out.replace(ANCHOR, NEW)
(ROOT / "main.py.bak-autocode0928").write_text(src, encoding="utf-8", newline="")
p.write_text(out, encoding="utf-8", newline="")
print("main.py patched (backup main.py.bak-autocode0928)")
