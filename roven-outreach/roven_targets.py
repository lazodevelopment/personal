#!/usr/bin/env python3
# ============================================================================
# ROVEN - roven_targets.py
# Build ID: JC-ROVEN-TARGETS-0817-001
#
# Builds the cold-outreach TARGET list from Google Places: small businesses
# in Roven's launch verticals (the same trades/healthcare niches the resume
# pages target), across the launch metros.
#
# OUTPUT:  outreach_{metro}.csv  (name, category, website, phone, address, city)
#          -> feed these to enrich_outreach.py for Hunter email discovery.
#
# COST:    Places Text Search. ~180 searches total at default settings —
#          well inside Google's monthly free allotment for most accounts.
#          --dry-run prints the query plan and estimated request count, free.
#
# USAGE:
#   python roven_targets.py --dry-run
#   python roven_targets.py --key YOUR_PLACES_KEY
#   python roven_targets.py --key YOUR_KEY --metros phoenix dallas
#   (no --key -> prompts, input hidden)
#
# Resume-safe: caches raw results in targets_cache.json; re-runs skip
# already-fetched queries. Dedupes by place_id across all queries.
# ============================================================================

import argparse
import csv
import getpass
import json
import os
import re
import sys
import time

try:
    import requests
except ImportError:
    sys.exit("Missing dependency. Run:  pip install requests")

METROS = {
    "phoenix":     "Phoenix, AZ",
    "dallas":      "Dallas-Fort Worth, TX",
    "houston":     "Houston, TX",
    "atlanta":     "Atlanta, GA",
    "nashville":   "Nashville, TN",
}

# Launch verticals — matches the resume-example pages' trades/healthcare focus.
TRADES = [
    "HVAC company",
    "plumbing company",
    "electrical contractor",
    "roofing company",
    "auto repair shop",
    "dental office",
    "veterinary clinic",
    "home health agency",
    "landscaping company",
    "general contractor",
    "manufacturing company",
    "physical therapy clinic",
]

API = "https://places.googleapis.com/v1/places:searchText"
FIELDS = ("places.id,places.displayName,places.websiteUri,"
          "places.nationalPhoneNumber,places.formattedAddress,"
          "places.businessStatus,nextPageToken")


def search(key, query, page_token=None):
    body = {"textQuery": query, "pageSize": 20}
    if page_token:
        body["pageToken"] = page_token
    r = requests.post(API, json=body, timeout=30, headers={
        "Content-Type": "application/json",
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": FIELDS,
    })
    if r.status_code != 200:
        print(f"    !! {r.status_code}: {r.text[:160]}")
        return None
    return r.json()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key")
    ap.add_argument("--metros", nargs="*", default=list(METROS))
    ap.add_argument("--pages", type=int, default=3,
                    help="pages per query (20 results/page, default 3)")
    ap.add_argument("--out", default=".")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    metros = [m for m in a.metros if m in METROS]
    if not metros:
        sys.exit(f"No valid metros. Choose from: {', '.join(METROS)}")

    n_queries = len(metros) * len(TRADES)
    print(f"Plan: {len(TRADES)} trades x {len(metros)} metros = "
          f"{n_queries} queries x up to {a.pages} pages "
          f"= <= {n_queries * a.pages} requests, "
          f"<= {n_queries * a.pages * 20} raw results before dedupe")
    if a.dry_run:
        for m in metros:
            for t in TRADES:
                print(f"  {t} in {METROS[m]}")
        print("\nDry run - no requests made, no cost.")
        return

    key = a.key or getpass.getpass("Google Places API key: ").strip()
    if not key:
        sys.exit("No key.")

    cache_path = os.path.join(a.out, "targets_cache.json")
    cache = {}
    if os.path.exists(cache_path):
        cache = json.load(open(cache_path, encoding="utf-8"))

    for m in metros:
        seen = {}
        for t in TRADES:
            q = f"{t} in {METROS[m]}"
            ck = q.lower()
            if ck in cache:
                pages = cache[ck]
                print(f"[cache] {q} ({sum(len(p) for p in pages)} rows)")
            else:
                print(f"[fetch] {q}")
                pages, token = [], None
                for _ in range(a.pages):
                    j = search(key, q, token)
                    if not j:
                        break
                    pages.append(j.get("places", []))
                    token = j.get("nextPageToken")
                    if not token:
                        break
                    time.sleep(1.2)
                cache[ck] = pages
                json.dump(cache, open(cache_path, "w", encoding="utf-8"))
            for page in pages:
                for p in page:
                    pid = p.get("id")
                    if not pid or pid in seen:
                        continue
                    if p.get("businessStatus") not in (None, "OPERATIONAL"):
                        continue
                    seen[pid] = {
                        "name": (p.get("displayName") or {}).get("text", ""),
                        "category": t,
                        "website": p.get("websiteUri", ""),
                        "phone": p.get("nationalPhoneNumber", ""),
                        "address": p.get("formattedAddress", ""),
                        "city": METROS[m],
                    }
        rows = [r for r in seen.values() if r["name"]]
        with_site = sum(1 for r in rows if r["website"])
        out = os.path.join(a.out, f"outreach_{m}.csv")
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=[
                "name", "category", "website", "phone", "address", "city"])
            w.writeheader()
            w.writerows(rows)
        print(f"  -> {out}: {len(rows)} businesses "
              f"({with_site} with websites = enrichable)")

    print("\nNext: python enrich_outreach.py --in . --out .\\instantly "
          f"--metros {' '.join(metros)} --dry-run")


if __name__ == "__main__":
    main()
