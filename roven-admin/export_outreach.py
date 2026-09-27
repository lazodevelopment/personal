#!/usr/bin/env python3
"""
export_outreach.py — Roven founding-employer outreach lists
===========================================================
Exports ranked CSVs from the `prospects` collection — one per metro plus a
combined master — ordered by outreach priority: businesses that care most
about public reputation first (high Google rating x high review count),
with a website and phone on file.

Ranking score = (rating - 3.5) * log10(reviews + 1)  ... clamped at 0
  - a 4.9-star business with 400 reviews outranks a 5.0 with 3
  - reputation-proud businesses are the natural first buyers of a public
    accountability badge

Columns include the live Roven profile URL — the strongest line in any
outreach message: "your business already has a page on Roven."

USAGE
  python export_outreach.py --key serviceAccount.json --out C:\\Users\\kurvh\\roven-outreach
"""

import argparse
import csv
import math
import os
import re

import firebase_admin
from firebase_admin import credentials, firestore

SITE = "https://rovenhr.com"


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s[:60] or "business"


def score(p: dict) -> float:
    rating = p.get("googleRating") or 0
    reviews = p.get("googleReviewCount") or 0
    base = max(0.0, (float(rating) - 3.5)) * math.log10(reviews + 1)
    if p.get("website"):
        base += 0.15
    if p.get("phone"):
        base += 0.1
    return round(base, 3)


COLUMNS = [
    "priority", "name", "vertical", "city", "state", "metro",
    "googleRating", "googleReviewCount", "phone", "website",
    "rovenProfileUrl", "claimUrl",
]


def row(p: dict, rank: int) -> dict:
    slug = f"{slugify(p['name'])}-{p['placeId'][:6].lower()}"
    profile = f"{SITE}/business/{p['metroSlug']}/{slug}"
    claim = f"{SITE}/contact.html?claim={p['name'].replace(' ', '%20')}&metro={p['metro'].replace(' ', '%20')}"
    return {
        "priority": rank,
        "name": p.get("name", ""),
        "vertical": p.get("verticalDisplay", ""),
        "city": p.get("city", ""),
        "state": p.get("state", ""),
        "metro": p.get("metro", ""),
        "googleRating": p.get("googleRating", ""),
        "googleReviewCount": p.get("googleReviewCount", ""),
        "phone": p.get("phone", ""),
        "website": p.get("website", ""),
        "rovenProfileUrl": profile,
        "claimUrl": claim,
    }


def write_csv(path: str, plist: list):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for i, p in enumerate(plist, 1):
            w.writerow(row(p, i))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    firebase_admin.initialize_app(credentials.Certificate(args.key))
    db = firestore.client()

    prospects = [s.to_dict() for s in
                 db.collection("prospects").where("status", "==", "unclaimed").stream()]
    prospects = [p for p in prospects if p.get("name") and p.get("placeId")]
    for p in prospects:
        p["_score"] = score(p)
    prospects.sort(key=lambda p: p["_score"], reverse=True)

    os.makedirs(args.out, exist_ok=True)
    write_csv(os.path.join(args.out, "outreach_ALL.csv"), prospects)

    by_metro = {}
    for p in prospects:
        by_metro.setdefault(p["metroSlug"], []).append(p)
    for slug, plist in sorted(by_metro.items()):
        write_csv(os.path.join(args.out, f"outreach_{slug}.csv"), plist)
        print(f"  outreach_{slug}.csv  {len(plist)} businesses")

    print(f"\n{len(prospects)} prospects exported to {args.out}")
    print("Top 10 overall:")
    for p in prospects[:10]:
        print(f"  {p['_score']:5.2f}  {p['name'][:40]:42s} {p.get('metro','')} · {p.get('googleRating','')}★ x {p.get('googleReviewCount','')}")


if __name__ == "__main__":
    main()
