"""Generate self-contained Cloud Shell patch scripts (Atavia + ES) for JC-ENGAGE-1012.
Run from C:\\Users\\kurvh. Reads the already-patched local copies for the email + sweep blocks."""
import io, os

HOME = os.path.expanduser("~")

def rd(p):
    return io.open(p, encoding="utf-8").read()

RUNNER = r'''#!/usr/bin/env python3
"""__BRAND__ JC-ENGAGE-1012 - run in Cloud Shell from the live functions folder.
Patches main.py / lib/emails.py / packages json IN PLACE (backups *.pre-engage1012.bak),
compiles, then prints the deploy commands. Idempotent: skips files already patched."""
import io, os, sys, json, py_compile, shutil

EMAILS_BLOCK = __EMAILS__
SWEEP_BLOCK = __SWEEP__
EDITS = __EDITS__
PKG_CANDIDATES = __PKGS__
RULE_DAYS = __DAYS__

def rd(p): return io.open(p, encoding="utf-8").read()
def wr(p, s):
    shutil.copy(p, p + ".pre-engage1012.bak")
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)

e = rd("lib/emails.py")
if "ENGAGE-1012" in e:
    print("lib/emails.py already patched")
else:
    wr("lib/emails.py", e.rstrip("\n") + "\n\n\n" + EMAILS_BLOCK)
    print("lib/emails.py: appended")

m = rd("main.py")
if "ENGAGE-1012" in m:
    print("main.py already patched")
else:
    lazo = "\n# ======================================================== lazo invite =="
    assert lazo in m, "lazo invite header not found in main.py"
    m = m.replace(lazo, "\n" + SWEEP_BLOCK + lazo.lstrip("\n"), 1)
    for old, new in EDITS:
        assert m.count(old) == 1, "expected exactly one match for: " + old[:70]
        m = m.replace(old, new, 1)
    wr("main.py", m)
    print("main.py: sweep + rule + lazo delay")

for pj in PKG_CANDIDATES:
    if os.path.exists(pj):
        d = json.load(io.open(pj, encoding="utf-8"))
        d["pricing_rules"]["pif_required_within_days"] = RULE_DAYS
        wr(pj, json.dumps(d, indent=2, ensure_ascii=False) + "\n")
        print(pj, ": pif_required_within_days =", RULE_DAYS)
        break
else:
    sys.exit("packages json not found: " + str(PKG_CANDIDATES))

for f in ("main.py", "lib/emails.py"):
    py_compile.compile(f, doraise=True)
print("COMPILED OK - now run the deploy line from the -command.txt file")
'''


def gen(brand, bs, emails_marker, sweep_hdr, pkgs, days, edits, cmds, where, pre):
    emails_src = rd(f"{bs}/lib/emails.py")
    emails_block = emails_src[emails_src.index(emails_marker):]
    main_src = rd(f"{bs}/main.py")
    lazo = "# ======================================================== lazo invite =="
    sweep_block = main_src[main_src.index(sweep_hdr):main_src.index(lazo)]
    script = (RUNNER.replace("__BRAND__", brand.upper())
              .replace("__EMAILS__", repr(emails_block))
              .replace("__SWEEP__", repr(sweep_block))
              .replace("__EDITS__", repr(edits))
              .replace("__PKGS__", repr(pkgs))
              .replace("__DAYS__", str(days)))
    out = f"{bs}/cloudshell-engage-1012.py"
    io.open(out, "w", encoding="utf-8", newline="\n").write(script)
    cmd = (f"# {brand.upper()} - Cloud Shell ({where}). Upload cloudshell-engage-1012.py (Cloud Shell menu > Upload file), then:\n"
           f"{pre} && mv ~/cloudshell-engage-1012.py . 2>/dev/null; python3 cloudshell-engage-1012.py && {cmds}\n")
    io.open(f"{bs}/cloudshell-engage-1012-command.txt", "w", encoding="utf-8", newline="\n").write(cmd)
    print("wrote", out)


# ---------------- Atavia (still on Zoho: env vars untouched, no whop_setup redeploy)
at_edits = [
 ('    if days_to_event <= 0:\n        raise ValueError("event date must be in the future")\n    second_shooter = bool(data.get("second_shooter"))',
  '    if days_to_event <= 0:\n        raise ValueError("event date must be in the future")\n    if RULES.get("pif_required_within_days", 0) and days_to_event <= RULES["pif_required_within_days"]:\n        option = "pif"          # JC-ENGAGE-1012: close-in weddings are paid in full at reservation\n    second_shooter = bool(data.get("second_shooter"))'),
 ('        if event_dt.date() <= datetime.now().date():\n            return _res({"error": "event date must be in the future"}, 400)',
  '        if event_dt.date() <= datetime.now().date():\n            return _res({"error": "event date must be in the future"}, 400)\n        _dte = (event_dt.date() - datetime.now().date()).days\n        if RULES.get("pif_required_within_days", 0) and _dte <= RULES["pif_required_within_days"]:\n            data["payment_option"] = "pif"   # JC-ENGAGE-1012: close-in weddings are paid in full'),
 ('LAZO_INVITE_DELAY_DAYS = 3 ', 'LAZO_INVITE_DELAY_DAYS = 7 '),
 ('    _send_lazo_invites(firestore.client(), datetime.now(timezone.utc))   # JC-LZ-INVITE-0928\n    db = firestore.client()',
  '    _send_lazo_invites(firestore.client(), datetime.now(timezone.utc))   # JC-LZ-INVITE-0928\n    try:\n        _send_engagement(firestore.client(), datetime.now(timezone.utc))   # JC-ENGAGE-1012\n    except Exception as e:\n        print(f"engagement sweep failed: {e}")\n    db = firestore.client()'),
]
at_cmds = ('R=us-central1; common="--gen2 --region=$R --runtime=python312 --source=. --allow-unauthenticated"; '
           'zoho="ZOHO_CLIENT_ID=ZOHO_CLIENT_ID:latest,ZOHO_CLIENT_SECRET=ZOHO_CLIENT_SECRET:latest,ZOHO_REFRESH_TOKEN=ZOHO_REFRESH_TOKEN:latest"; '
           'sw="SIGNWELL_API_KEY=SIGNWELL_API_KEY:latest"; mail="RESEND_API_KEY=RESEND_API_KEY:latest,GRATUITY_SECRET=GRATUITY_SECRET:latest"; '
           'gcloud functions deploy book_submit $common --entry-point=book_submit --trigger-http --memory=512MB --set-secrets=$zoho,$sw,RESEND_API_KEY=RESEND_API_KEY:latest 2>&1 | grep -E "^(state|ERROR)"; '
           'gcloud functions deploy charge_balances --gen2 --region=$R --runtime=python312 --source=. --entry-point=charge_balances --set-secrets=$zoho,$mail,$sw 2>&1 | grep -E "^(state|ERROR)"; '
           'echo ATAVIA-ENGAGE-DEPLOY-DONE')
gen("atavia", f"{HOME}/atavia-functions-live/bs",
    "# ============================================================ engagement ==",
    "# ========================================================== engagement ==",
    ["contract/atavia_packages.json", "atavia_packages.json"], 45, at_edits, at_cmds,
    "project atavia-c29cd, account info@ataviaweddings.com", "cd ~/bs && gcloud config set project atavia-c29cd")

# ---------------- ES (live on Whop; whop_setup serves the reservation amount)
es_edits = [
 ('    if days_to_event <= RULES.get("rush_days", 14):\n        option = "pif"                      # rush dates are PIF-only',
  '    if days_to_event <= RULES.get("rush_days", 14):\n        option = "pif"                      # rush dates are PIF-only\n    if RULES.get("pif_required_within_days", 0) and days_to_event <= RULES["pif_required_within_days"]:\n        option = "pif"                      # JC-ES-ENGAGE-1012: close-in weddings are paid in full'),
 ('        if event_dt.date() <= datetime.now().date():\n            return _res({"error": "event date must be in the future"}, 400)',
  '        if event_dt.date() <= datetime.now().date():\n            return _res({"error": "event date must be in the future"}, 400)\n        _dte = (event_dt.date() - datetime.now().date()).days\n        if RULES.get("pif_required_within_days", 0) and _dte <= RULES["pif_required_within_days"]:\n            data["payment_option"] = "pif"   # JC-ES-ENGAGE-1012: close-in weddings are paid in full'),
 ('LAZO_INVITE_DELAY_DAYS = 3 ', 'LAZO_INVITE_DELAY_DAYS = 8 '),
 ('    _send_lazo_invites(firestore.client(), datetime.now(timezone.utc))   # JC-LZ-INVITE-0928\n    db = firestore.client()',
  '    _send_lazo_invites(firestore.client(), datetime.now(timezone.utc))   # JC-LZ-INVITE-0928\n    try:\n        _send_milestones(firestore.client(), datetime.now(timezone.utc))   # JC-ES-ENGAGE-1012\n    except Exception as e:\n        print(f"milestone sweep failed: {e}")\n    db = firestore.client()'),
]
es_cmds = ('P=elizabeth-scott-738e5; R=us-central1; common="--gen2 --region=$R --runtime=python312 --source=. --allow-unauthenticated --project=$P"; '
           'sec="WHOP_API_KEY=WHOP_API_KEY:latest,WHOP_WEBHOOK_SECRET=WHOP_WEBHOOK_SECRET:latest,ZOHO_CLIENT_ID=ZOHO_CLIENT_ID:latest,ZOHO_CLIENT_SECRET=ZOHO_CLIENT_SECRET:latest,ZOHO_REFRESH_TOKEN=ZOHO_REFRESH_TOKEN:latest,SIGNWELL_API_KEY=SIGNWELL_API_KEY:latest,RESEND_API_KEY=RESEND_API_KEY:latest,GRATUITY_SECRET=GRATUITY_SECRET:latest"; '
           'for f in whop_setup book_submit; do gcloud functions deploy $f $common --entry-point=$f --trigger-http --set-secrets=$sec 2>&1 | grep -E "^(state|ERROR)"; done; '
           'gcloud functions deploy charge_balances --gen2 --region=$R --runtime=python312 --source=. --project=$P --entry-point=charge_balances --set-secrets=$sec 2>&1 | grep -E "^(state|ERROR)"; '
           'echo ES-ENGAGE-DEPLOY-DONE')
gen("es", f"{HOME}/es-functions/bs",
    "# ============================================================ milestones ==",
    "# ========================================================== milestones ==",
    ["elizabethscott_packages.json", "contract/elizabethscott_packages.json"], 45, es_edits, es_cmds,
    "project elizabeth-scott-738e5, account danbrenmedia@gmail.com", "cd ~/es-deploy/functions")
