#!/usr/bin/env python3
"""JC-FOLLOWUP-1009: inquiry_webhook answers the Gmail follow-up sequence (FollowUps.gs).

Works on both brands' main.py (Atavia and Elizabeth Scott); run it next to main.py:
    python3 patch_inquiry_followup.py
then redeploy inquiry_webhook only.

Two new actions on the existing endpoint, both gated on the couple's email AND the
code from their first auto-reply (so the endpoint cannot be used to look up who booked):
  followup_status {check_email, code, mint?}  -> booked / started flags, the couple's
      details, the first code's expiry, and with mint=true a fresh $200 / 72 h code,
      minted once per inquiry and returned again on retries.
  followup_log {check_email, code, step, state}  -> stamps followups.<step> on the
      inquiry (and followup_stopped when the sequence ends) for the Leads page.
The fields are check_email/code rather than email, so an older deploy answers
"email required" (400) and never stores a stray inquiry.

Anchor-and-assert: every edit must find its anchor exactly once or nothing is written.
"""
import pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent
MAIN = ROOT / "main.py"
src = MAIN.read_text(encoding="utf-8")
if "JC-FOLLOWUP-1009" in src:
    sys.exit("already patched")

HELPER = '''# ======================================================= inquiry follow-ups ==
FOLLOWUP_CODE_AMOUNT = 200   # JC-FOLLOWUP-1009: $ off carried by the day-5 follow-up
FOLLOWUP_CODE_HOURS = 72


def _iso(v):
    return v.isoformat() if hasattr(v, "isoformat") else (str(v) if v else "")


def _inquiry_followup(req, body):
    """JC-FOLLOWUP-1009: the Gmail follow-up sequence (FollowUps.gs) checks here
    before every send and reports after it. The caller proves it knows the couple
    with the code from their first reply; anything else is a 404."""
    from google.cloud.firestore_v1.base_query import FieldFilter
    email = str(body.get("check_email") or "").strip().lower()
    code = str(body.get("code") or "").strip().upper()
    if not email or not code:
        return _json(req, {"error": "check_email and code required"}, 400)
    db = firestore.client()
    snaps = [s for s in db.collection("inquiries")
                          .where(filter=FieldFilter("email", "==", email)).get()
             if str(s.to_dict().get("auto_code") or "").upper() == code]
    if not snaps:
        return _json(req, {"error": "not found"}, 404)
    snap = snaps[0]
    inq = snap.to_dict()
    now = datetime.now(timezone.utc)

    if body.get("action") == "followup_log":
        step = "".join(c for c in str(body.get("step") or "") if c.isalnum())[:8]
        state = str(body.get("state") or "")[:120]
        upd = {}
        if step:
            upd[f"followups.{step}"] = {"state": state, "at": now}
        if body.get("stopped"):
            upd["followup_stopped"] = {"reason": state, "at": now}
        if upd:
            snap.reference.update(upd)
        return _json(req, {"ok": True})

    # followup_status
    booked = [s for s in db.collection("bookings")
                            .where(filter=FieldFilter("email", "==", email)).get()
              if not s.to_dict().get("test_mode")]
    started = db.collection("leads").where(filter=FieldFilter("email", "==", email)).limit(1).get()
    first = db.collection("discount_codes").document(code).get()
    first = first.to_dict() if first.exists else {}
    fresh = inq.get("followup_code")
    if body.get("mint") and not fresh:
        try:
            fresh = _mint_code(db, FOLLOWUP_CODE_AMOUNT, FOLLOWUP_CODE_HOURS,
                               f"day-5 follow-up \\u2014 {email}")
            fresh = {k: fresh[k] for k in ("code", "amount", "expires_at")}
            snap.reference.update({"followup_code": fresh})
        except Exception as e:
            print(f"follow-up code mint failed: {e}")
            fresh = None
    return _json(req, {
        "ok": True,
        "booked": bool(booked),
        "started": bool(started),
        "first_name": inq.get("first_name", ""), "last_name": inq.get("last_name", ""),
        "wedding_date": inq.get("event_date_raw", ""), "venue": inq.get("venue", ""),
        "found_us": inq.get("found_us", ""),
        "code_expires_at": _iso(first.get("expires_at")),
        "code_redeemed": bool(first.get("redeemed_by")),
        "followup_code": fresh,
        "stopped": bool(inq.get("followup_stopped")),
    })


'''

edits = [
    ('''@https_fn.on_request(region=REGION, secrets=[RESEND_API_KEY])
def inquiry_webhook(req: https_fn.Request) -> https_fn.Response:''',
     HELPER + '''@https_fn.on_request(region=REGION, secrets=[RESEND_API_KEY])
def inquiry_webhook(req: https_fn.Request) -> https_fn.Response:'''),
    ('''    if not sub or sub.get("_gotcha"):
        return _json(req, {"ok": True})
    g = lambda *ks: next((str(sub[k]).strip()[:500] for k in ks if sub.get(k)), "")''',
     '''    if not sub or sub.get("_gotcha"):
        return _json(req, {"ok": True})
    if body.get("action") in ("followup_status", "followup_log"):   # JC-FOLLOWUP-1009
        return _inquiry_followup(req, body)
    g = lambda *ks: next((str(sub[k]).strip()[:500] for k in ks if sub.get(k)), "")'''),
]
for old, new in edits:
    n = src.count(old)
    if n != 1:
        sys.exit(f"anchor found {n} times, nothing written:\n{old[:120]}")
    src = src.replace(old, new)

import ast
ast.parse(src)
(ROOT / "main.py.pre-followup.bak").write_text(MAIN.read_text(encoding="utf-8"), encoding="utf-8")
MAIN.write_text(src, encoding="utf-8")
print("patched main.py (backup main.py.pre-followup.bak)")
