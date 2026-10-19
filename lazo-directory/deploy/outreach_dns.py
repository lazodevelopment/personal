r"""outreach_dns.py - JC-LAZO-OUTREACH-1018: DNS for the claim-campaign sending subdomains.

Six subdomains of meetlazo.com carry Google Workspace mailboxes that Smartlead sends from (team, vendors, partners,
listings, studio, hello-from). The apex keeps its own mail (Zoho for support@, Resend for hello@); nothing here
touches an apex record except, with --apex-dmarc, the _dmarc policy's subdomain clause.

Per subdomain:
  MX    sub            smtp.google.com  priority 1        (replies land in the Workspace box)
  TXT   sub            v=spf1 include:_spf.google.com ~all
  TXT   _dmarc.sub     v=DMARC1; p=quarantine; pct=100
  TXT   google._domainkey.sub   <DKIM from Google Admin>  (--dkim sub=value, after Jesse generates it)

    python deploy\outreach_dns.py --plan                     # print the records, change nothing
    python deploy\outreach_dns.py --apply                    # create what is missing (idempotent)
    python deploy\outreach_dns.py --apply --dkim team=v=DKIM1;k=rsa;p=MIIB...
    python deploy\outreach_dns.py --export                   # BIND-format file for the dashboard's "Import records"

Needs a Cloudflare API token with Zone:DNS:Edit on meetlazo.com in CF_DNS_TOKEN (.env or environment). The
tokens already in .env (JARVIS_CF_TOKEN, CF_API_TOKEN) can list the zone but not its records (checked 2026-10-18).
Zone meetlazo.com = 2a3f65b652f805c7a2a4d7dae6213f1b, on the "Info@leasereputation.com" Cloudflare account.
"""
import argparse, os, sys
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass

ZONE = "2a3f65b652f805c7a2a4d7dae6213f1b"
DOMAIN = "meetlazo.com"
SUBS = ["team", "vendors", "partners", "listings", "studio", "hello-from"]
API = "https://api.cloudflare.com/client/v4"
DMARC = "v=DMARC1; p=quarantine; pct=100"
SPF = "v=spf1 include:_spf.google.com ~all"


def wanted(dkim):
    out = []
    for s in SUBS:
        fq = f"{s}.{DOMAIN}"
        out.append({"type": "MX", "name": fq, "content": "smtp.google.com", "priority": 1, "ttl": 1})
        out.append({"type": "TXT", "name": fq, "content": SPF, "ttl": 1})
        out.append({"type": "TXT", "name": f"_dmarc.{fq}", "content": DMARC, "ttl": 1})
        if s in dkim:
            out.append({"type": "TXT", "name": f"google._domainkey.{fq}", "content": dkim[s], "ttl": 1})
    return out


def export_bind(recs):
    lines = [f"; meetlazo.com - claim-campaign sending subdomains (deploy/outreach_dns.py --export)", "$ORIGIN meetlazo.com.", "$TTL 300"]
    for r in recs:
        name = r["name"][: -len(DOMAIN) - 1]
        if r["type"] == "MX":
            lines.append(f"{name}\tIN\tMX\t{r['priority']} {r['content']}.")
        else:
            lines.append(f"{name}\tIN\tTXT\t\"{r['content']}\"")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--export", action="store_true")
    ap.add_argument("--dkim", action="append", default=[], help="sub=<TXT value from Google Admin>, repeatable")
    ap.add_argument("--apex-dmarc", action="store_true", help="also set sp=quarantine on _dmarc.meetlazo.com (prints the current record first)")
    a = ap.parse_args()
    dkim = dict(x.split("=", 1) for x in a.dkim)
    recs = wanted(dkim)
    if a.export:
        p = Path(__file__).resolve().parent / "outreach_dns_import.txt"
        p.write_text(export_bind(recs), encoding="utf-8")
        print(f"wrote {p} ({len(recs)} records) - Cloudflare dashboard > DNS > Records > Import and Export > Import DNS records")
    if a.plan or not (a.apply or a.export):
        for r in recs:
            print(f"{r['type']:<4} {r['name']:<40} {r.get('priority', ''):<3} {r['content']}")
    if not a.apply:
        return
    tok = os.environ.get("CF_DNS_TOKEN")
    if not tok:
        sys.exit("CF_DNS_TOKEN missing: make a token with Zone:DNS:Edit on meetlazo.com (dash.cloudflare.com/profile/api-tokens) and put it in .env")
    h = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
    r = requests.get(f"{API}/zones/{ZONE}/dns_records", headers=h, params={"per_page": 500}).json()
    if not r.get("success"):
        sys.exit(f"cannot list records: {r.get('errors')}")
    have = {(x["type"], x["name"].lower(), x["content"]) for x in r["result"]}
    for x in r["result"]:
        if x["name"].lower() == f"_dmarc.{DOMAIN}":
            print("apex _dmarc now:", x["content"])
            # Cloudflare hands TXT content back wrapped in quotes; strip them or the clause lands outside the string
            cur = x["content"].strip().strip('"')
            if a.apex_dmarc and "sp=" not in cur:
                new = cur.rstrip("; ") + "; sp=quarantine"
                u = requests.patch(f"{API}/zones/{ZONE}/dns_records/{x['id']}", headers=h, json={"content": new}).json()
                print("apex _dmarc ->", new if u.get("success") else u.get("errors"))
    n = 0
    for rec in recs:
        key = (rec["type"], rec["name"].lower(), rec["content"])
        if key in have:
            print("have ", rec["type"], rec["name"])
            continue
        c = requests.post(f"{API}/zones/{ZONE}/dns_records", headers=h, json=rec).json()
        print("added" if c.get("success") else "FAIL ", rec["type"], rec["name"], "" if c.get("success") else c.get("errors"))
        n += bool(c.get("success"))
    print(f"{n} record(s) added")


if __name__ == "__main__":
    main()
