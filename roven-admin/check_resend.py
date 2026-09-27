#!/usr/bin/env python3
"""
check_resend.py — asks Resend directly whether the email layer can work.
  1. Lists your Resend domains and their verification status
  2. Attempts a real test send from alerts@notify.rovenhr.com
  3. Prints the raw API responses — the exact truth, no log spelunking

USAGE
  python check_resend.py
  (prompts for the Resend API key — paste it; it isn't stored anywhere)
"""

import getpass

import requests

key = getpass.getpass("Paste your Resend API key (input hidden): ").strip()
H = {"Authorization": f"Bearer {key}"}

print("\n--- 1. Domains on this Resend account ---")
r = requests.get("https://api.resend.com/domains", headers=H, timeout=20)
print(f"HTTP {r.status_code}")
if r.status_code == 200:
    domains = r.json().get("data", [])
    if not domains:
        print("  NO DOMAINS — notify.rovenhr.com was never added to Resend.")
    for d in domains:
        print(f"  {d.get('name'):28s} status: {d.get('status')}")
        if d.get("status") != "verified":
            print("    ^^ not verified — sends from it will be REJECTED")
else:
    print(f"  {r.text[:300]}")
    print("  (401 here = wrong API key)")

print("\n--- 2. Test send from alerts@notify.rovenhr.com ---")
r = requests.post(
    "https://api.resend.com/emails",
    headers=H,
    json={
        "from": "Roven <alerts@notify.rovenhr.com>",
        "to": ["rovenhr@gmail.com"],
        "subject": "Roven email layer test",
        "html": "<p>If you're reading this, the match engine's email layer works.</p>",
    },
    timeout=20,
)
print(f"HTTP {r.status_code}")
print(f"  {r.text[:400]}")
if r.status_code in (200, 201):
    print("\nVERDICT: email layer WORKS — check rovenhr@gmail.com. If this sent")
    print("but the matcher doesn't, the deployed RESEND_API_KEY secret differs")
    print("from the key you just pasted.")
else:
    print("\nVERDICT: this is the match engine's blocker. The error above names it")
    print("(403 domain not verified -> finish the DNS records; 401 -> key).")
