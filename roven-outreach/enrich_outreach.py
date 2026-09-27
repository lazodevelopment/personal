#!/usr/bin/env python3
# ============================================================================
# ROVEN - enrich_outreach.py
# Build ID: JC-ROVEN-ENRICH-0817-002  (regenerated; supersedes 0730-001)
#
# Turns outreach_{metro}.csv (from roven_targets.py) into Instantly-ready
# lists with the merge fields the sequences use.
#
# WHAT IT DOES
#   1. Reads outreach_{metro}.csv from --in
#   2. Extracts each prospect's domain from their website
#   3. Queries Hunter.io domain-search for the best contact
#      (prefers a named decision-maker; falls back to generic info@/office@)
#   4. Builds merge fields: email, firstName, companyName, city, roleGuess
#   5. Writes:
#        {out}\instantly_{metro}.csv   - rows WITH an email (import these)
#        {out}\phone_list_{metro}.csv  - rows WITHOUT one   (calls/SMS later)
#
# COST CONTROL
#   - --dry-run costs NOTHING: parses, builds all non-email fields, writes
#     CSVs with a blank email column so you can inspect quality first.
#   - Results cached in enrich_cache.json; re-runs never re-bill a domain.
#   - --limit caps paid lookups per run.
#
# HUNTER PLANS: free 25/mo · Starter $49 = 500 · Growth $149 = 5,000
#
# USAGE
#   python enrich_outreach.py --in . --out .\instantly --metros phoenix --dry-run
#   python enrich_outreach.py --in . --out .\instantly --metros phoenix --limit 20
#   python enrich_outreach.py --in . --out .\instantly --metros phoenix dallas houston atlanta nashville
#   (prompts for the Hunter API key unless --hunter-key is passed)
# ============================================================================

import argparse
import csv
import getpass
import json
import os
import re
import sys
import time
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    sys.exit("Missing dependency. Run:  pip install requests")

GENERIC_LOCALPARTS = {"info", "office", "contact", "hello", "admin",
                      "service", "sales", "support", "team", "frontdesk"}
SKIP_DOMAINS = {"facebook.com", "instagram.com", "yelp.com", "google.com",
                "linkedin.com", "angieslist.com", "homeadvisor.com",
                "yellowpages.com", "wixsite.com", "squarespace.com"}

ROLE_BY_CATEGORY = {
    "hvac": "service techs", "plumb": "plumbers",
    "electric": "electricians", "roof": "roofers",
    "auto": "mechanics", "dental": "front-office and hygienists",
    "veterinary": "vet techs", "home health": "caregivers",
    "landscap": "crew members", "contractor": "skilled tradespeople",
    "manufactur": "machine operators", "physical therapy": "PT staff",
}


def domain_of(url):
    if not url:
        return ""
    try:
        host = urlparse(url if "://" in url else "https://" + url).netloc.lower()
    except Exception:
        return ""
    host = re.sub(r"^www\.", "", host)
    root = ".".join(host.split(".")[-2:]) if host.count(".") >= 1 else host
    return "" if any(root.endswith(s) for s in SKIP_DOMAINS) else host


def role_guess(category):
    c = (category or "").lower()
    for k, v in ROLE_BY_CATEGORY.items():
        if k in c:
            return v
    return "great people"


def hunter_best(key, domain, cache):
    if domain in cache:
        return cache[domain]
    r = requests.get("https://api.hunter.io/v2/domain-search",
                     params={"domain": domain, "api_key": key, "limit": 10},
                     timeout=30)
    if r.status_code == 429:
        print("    rate-limited; sleeping 15s"); time.sleep(15)
        return hunter_best(key, domain, cache)
    out = {"email": "", "first": ""}
    if r.status_code == 200:
        emails = (r.json().get("data") or {}).get("emails") or []
        named = [e for e in emails
                 if e.get("first_name") and e.get("confidence", 0) >= 60]
        generic = [e for e in emails
                   if (e.get("value", "").split("@")[0].lower()
                       in GENERIC_LOCALPARTS)]
        pick = (sorted(named, key=lambda e: -e.get("confidence", 0)) or
                generic or [None])[0]
        if pick:
            out = {"email": pick.get("value", ""),
                   "first": (pick.get("first_name") or "").title()}
    else:
        print(f"    !! hunter {r.status_code} for {domain}: {r.text[:100]}")
    cache[domain] = out
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="indir", default=".")
    ap.add_argument("--out", default="./instantly")
    ap.add_argument("--metros", nargs="+", required=True)
    ap.add_argument("--hunter-key")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    cache_path = os.path.join(a.out, "enrich_cache.json")
    cache = json.load(open(cache_path, encoding="utf-8")) \
        if os.path.exists(cache_path) else {}

    key = None
    if not a.dry_run:
        key = a.hunter_key or getpass.getpass("Hunter API key: ").strip()
        if not key:
            sys.exit("No key. (Use --dry-run to preview free.)")

    spent = 0
    for m in a.metros:
        src = os.path.join(a.indir, f"outreach_{m}.csv")
        if not os.path.exists(src):
            print(f"skip {m}: {src} not found"); continue
        rows = list(csv.DictReader(open(src, encoding="utf-8")))
        good, phones = [], []
        print(f"[{m}] {len(rows)} businesses")
        for r in rows:
            dom = domain_of(r.get("website", ""))
            rec = {
                "email": "",
                "firstName": "",
                "companyName": r.get("name", "").strip(),
                "city": r.get("city", ""),
                "roleGuess": role_guess(r.get("category", "")),
                "category": r.get("category", ""),
                "website": r.get("website", ""),
                "phone": r.get("phone", ""),
            }
            if dom and not a.dry_run:
                if a.limit and spent >= a.limit:
                    phones.append(rec); continue
                hit = hunter_best(key, dom, cache)
                spent += 1
                if spent % 25 == 0:
                    json.dump(cache, open(cache_path, "w", encoding="utf-8"))
                rec["email"], rec["firstName"] = hit["email"], hit["first"]
            if rec["email"] or a.dry_run:
                good.append(rec)
            else:
                phones.append(rec)
        json.dump(cache, open(cache_path, "w", encoding="utf-8"))

        fn = ["email", "firstName", "companyName", "city", "roleGuess",
              "category", "website", "phone"]
        p1 = os.path.join(a.out, f"instantly_{m}.csv")
        with open(p1, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fn)
            w.writeheader(); w.writerows(good)
        p2 = os.path.join(a.out, f"phone_list_{m}.csv")
        with open(p2, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fn)
            w.writeheader(); w.writerows(phones)
        tag = "(dry run - emails blank)" if a.dry_run else \
              f"({len(good)} with email, {len(phones)} phone-only)"
        print(f"  -> {p1} + {p2} {tag}")

    if not a.dry_run:
        print(f"\nHunter lookups spent this run: {spent}")
    print("Import instantly_*.csv into Instantly WITH its verification "
          "pass enabled - bounces on fresh domains are self-inflicted wounds.")


if __name__ == "__main__":
    main()
