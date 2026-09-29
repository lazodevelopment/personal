#!/usr/bin/env python3
"""JC-ATV-ATTR-0927: record landing page + referrer on the lead written at the card step.

Run from ~/bs:  python3 patch_lead_attribution.py   then deploy zoho_session:
  gcloud functions deploy zoho_session --gen2 --region=us-central1 --runtime=python312 --source=. \
    --entry-point=zoho_session --trigger-http --allow-unauthenticated \
    --set-secrets=ZOHO_CLIENT_ID=ZOHO_CLIENT_ID:latest,ZOHO_CLIENT_SECRET=ZOHO_CLIENT_SECRET:latest,ZOHO_REFRESH_TOKEN=ZOHO_REFRESH_TOKEN:latest

Anchor-and-assert: the edit must find its anchor exactly once or nothing is written.
book/index.html already sends attr_venue_url / attr_landing / attr_referrer with the
zoho_session call (deployed with the site); bookings have carried the same fields since
book_submit was written. The admin leads page reads them from either record.
"""
import pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent
ANCHOR = '''            "attr_venue": str(data.get("attr_venue") or "")[:200],
            "client_ip": req.headers.get("X-Forwarded-For", req.remote_addr),
            "sid": str(data.get("sid") or "")[:32],
        })'''
NEW = '''            "attr_venue": str(data.get("attr_venue") or "")[:200],
            # JC-ATV-ATTR-0927: same attribution the booking carries, so the
            # leads dashboard can say where each booking start came from.
            "attr_venue_url": str(data.get("attr_venue_url") or "")[:300],
            "attr_landing": str(data.get("attr_landing") or "")[:300],
            "attr_referrer": str(data.get("attr_referrer") or "")[:300],
            "client_ip": req.headers.get("X-Forwarded-For", req.remote_addr),
            "sid": str(data.get("sid") or "")[:32],
        })'''

p = ROOT / "main.py"
src = p.read_text(encoding="utf-8")
if "JC-ATV-ATTR-0927" in src:
    print("already applied"); sys.exit(0)
if src.count(ANCHOR) != 1:
    print("anchor found %d times, expected 1 - nothing written" % src.count(ANCHOR)); sys.exit(1)
(ROOT / "main.py.bak-attr0927").write_text(src, encoding="utf-8", newline="")
p.write_text(src.replace(ANCHOR, NEW), encoding="utf-8", newline="")
print("main.py patched (backup main.py.bak-attr0927)")
