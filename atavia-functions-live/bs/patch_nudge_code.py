#!/usr/bin/env python3
"""JC-ATV-NUDGE-0928: the day-3 "still want your date?" nudge now carries a $200 code, good 72 hours.

Run from ~/bs:  python3 patch_nudge_code.py   then deploy charge_balances (the daily job that runs _chase_leads):
  gcloud functions deploy charge_balances --gen2 --region=us-central1 --runtime=python312 --source=. --entry-point=charge_balances \
    --set-secrets=ZOHO_CLIENT_ID=ZOHO_CLIENT_ID:latest,ZOHO_CLIENT_SECRET=ZOHO_CLIENT_SECRET:latest,ZOHO_REFRESH_TOKEN=ZOHO_REFRESH_TOKEN:latest,RESEND_API_KEY=RESEND_API_KEY:latest,GRATUITY_SECRET=GRATUITY_SECRET:latest,SIGNWELL_API_KEY=SIGNWELL_API_KEY:latest
(no trigger flag, so the Cloud Scheduler trigger survives - same as deploy-functions.sh)

Anchor-and-assert: every edit must find its anchor exactly once or nothing is written.
1. main.py      - _chase_leads nudge 2 mints a code via _mint_code (same codes the admin issues by hand),
                  stamps nudge2_code on the lead, and puts ?code= on the resume link (book page auto-applies it).
2. lib/emails.py - card_recovery(..., code=None) mentions the code and its expiry.
"""
import pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent
edits = []

edits.append((ROOT / "main.py",
'''            elif not lead.get("nudge2_sent_at") and age_h >= 24 * 3:
                emails.card_recovery(RESEND_API_KEY.value, lead, resume, second=True)''',
'''            elif not lead.get("nudge2_sent_at") and age_h >= 24 * 3:
                # JC-ATV-NUDGE-0928: the second nudge carries a $200 code good
                # for 72 h - a reason to decide, not just a reminder. Minted
                # once; a failure to mint still sends the plain nudge.
                code = None
                try:
                    code = _mint_code(db, NUDGE_CODE_AMOUNT, NUDGE_CODE_HOURS,
                                      f"day-3 nudge \u2014 {lead.get('email','')}")
                    snap.reference.update({"nudge2_code": code["code"]})
                    resume += ("&" if "?" in resume else "?") + "code=" + code["code"]
                except Exception as e:
                    print(f"nudge code mint failed (non-fatal): {e}")
                emails.card_recovery(RESEND_API_KEY.value, lead, resume, second=True, code=code)'''))

edits.append((ROOT / "main.py",
'''def _chase_leads():
    """Card-window abandons.''',
'''NUDGE_CODE_AMOUNT = 200   # JC-ATV-NUDGE-0928: $ off carried by the day-3 nudge
NUDGE_CODE_HOURS = 72


def _chase_leads():
    """Card-window abandons.'''))

edits.append((ROOT / "lib" / "emails.py",
'''def card_recovery(api_key, lead, resume_url, second=False):''',
'''def card_recovery(api_key, lead, resume_url, second=False, code=None):'''))

edits.append((ROOT / "lib" / "emails.py",
'''        subject = f"Still want {date}?" if date else "Still want your date?"
    html = f"""''',
'''        subject = f"Still want {date}?" if date else "Still want your date?"
        if code:   # JC-ATV-NUDGE-0928
            from datetime import datetime as _dt
            try:
                exp = _dt.fromisoformat(code["expires_at"]).strftime("%A, %B %d")
            except Exception:
                exp = "3 days"
            lead_in += (f"<p>To make it easy: code <b>{code['code']}</b> takes "
                        f"<b>${code['amount']}</b> off any collection if you finish before "
                        f"<b>{exp}</b>. It is already applied on the link below.</p>")
            subject = (f"${code['amount']} off {date} \u2014 this week only" if date
                       else f"${code['amount']} off your date \u2014 this week only")
    html = f"""'''))

if "JC-ATV-NUDGE-0928" in (ROOT / "main.py").read_text(encoding="utf-8"):
    print("already applied"); sys.exit(0)
changed = {}
for path, anchor, new in edits:
    src = changed.get(path, path.read_text(encoding="utf-8"))
    if src.count(anchor) != 1:
        print(f"{path.name}: anchor found {src.count(anchor)} times, expected 1 - nothing written:\n{anchor[:80]}"); sys.exit(1)
    changed[path] = src.replace(anchor, new)
for path, src in changed.items():
    (path.parent / (path.name + ".bak-nudge0928")).write_text(path.read_text(encoding="utf-8"), encoding="utf-8", newline="")
    path.write_text(src, encoding="utf-8", newline="")
    print(f"{path.relative_to(ROOT)} patched")
print("done" if changed else "already applied")
