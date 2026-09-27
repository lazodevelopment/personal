# JC-LAZO-LEAD-0903: Meta Pixel conversion events on the static-site forms.
#   early-access form success  -> fbq('track', 'Lead', {content_name: 'early-access'})
#   claim-interest form success -> fbq('track', 'Lead', {content_name: 'claim-interest', ...})
# Guarded with window.fbq check so an ad blocker can't break the form.
#
# Run:  python patch_lead.py
# Then: cd C:\Users\kurvh\lazo-directory ; python deploy\deploy_site.py
import shutil, sys
from pathlib import Path

p = Path(r"C:\Users\kurvh\lazo-directory\generate\static\lazo.js")
TAG = "JC-LAZO-LEAD-0903"
if not p.exists():
    sys.exit(f"[patch] not found: {p}")
src = p.read_text(encoding="utf-8")
if TAG in src:
    sys.exit("[patch] already applied")

edits = [
    # early-access success
    (
        "      if (d.ok) {\n"
        "        f.style.display = 'none';\n"
        "        note.textContent = 'You\\u2019re on the list",
        "      if (d.ok) {\n"
        f"        if (window.fbq) fbq('track', 'Lead', {{ content_name: 'early-access' }}); /* {TAG} */\n"
        "        f.style.display = 'none';\n"
        "        note.textContent = 'You\\u2019re on the list",
    ),
    # claim-interest success
    (
        "      if (d.ok) {\n"
        "        f.style.display = 'none';\n"
        "        note.textContent = 'You\\u2019re on the founding-vendor list",
        "      if (d.ok) {\n"
        f"        if (window.fbq) fbq('track', 'Lead', {{ content_name: 'claim-interest', content_ids: [params.get('vendor') || ''] }}); /* {TAG} */\n"
        "        f.style.display = 'none';\n"
        "        note.textContent = 'You\\u2019re on the founding-vendor list",
    ),
]

out = src
for label, (old, new) in zip(("early-access", "claim-interest"), edits):
    n = out.count(old)
    if n != 1:
        sys.exit(f"[patch] ANCHOR FAIL ({label}): matched {n} times, need 1. Nothing written.")
    out = out.replace(old, new)

shutil.copy(p, p.with_name(p.name + ".bak-lead0903"))
p.write_text(out, encoding="utf-8")
print(f"[patch] lazo.js: Lead events added to early-access + claim-interest; backup lazo.js.bak-lead0903")