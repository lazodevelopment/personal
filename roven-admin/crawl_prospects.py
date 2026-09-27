#!/usr/bin/env python3
"""
crawl_prospects.py — Roven prospect crawler (wave one: CA / TX / FL + Phoenix)
==============================================================================
Discovers real businesses via Google Places across 13 metros x 3 verticals and
seeds the Firestore `prospects` collection — the raw material for:
  - unclaimed employer-profile SEO pages ("Not yet on Roven - Claim this business")
  - ranked founding-employer outreach lists

ARCHITECTURE RULE: prospects NEVER touch the `employers` collection. Verified
employers are born only through provisioning (concierge or, later, Middesk).
Claiming a prospect routes through you; the crawler only fills the top of the
funnel.

USAGE
  python crawl_prospects.py --key serviceAccount.json --places-key YOUR_PLACES_KEY
  optional:
    --cap 75            businesses per metro x vertical (default 75)
    --metros phoenix la  limit to specific metro slugs for a test run
    --verticals wedding_events   limit verticals
    --dry-run           print what would be written, write nothing

NOTES
  - Idempotent: doc id = Google place_id; re-runs update, never duplicate.
  - Uses Places API (New) Text Search. Cost at full run (~39 cells x ~4 pages):
    roughly 150-250 requests — a few dollars. Use a KEY RESTRICTED to the
    Places API, not an unrestricted key.
  - Rate-limited politely; full run takes ~10-15 minutes.
"""

import argparse
import sys
import time
from datetime import datetime, timezone

import requests
import firebase_admin
from firebase_admin import credentials, firestore

PLACES_URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.addressComponents",
    "places.websiteUri",
    "places.nationalPhoneNumber",
    "places.rating",
    "places.userRatingCount",
    "places.businessStatus",
    "nextPageToken",
])

METROS = {
    # slug: (query locality, metro display, state)
    "phoenix":      ("Phoenix, AZ",        "Phoenix",        "AZ"),
    "la":           ("Los Angeles, CA",    "Los Angeles",    "CA"),
    "sf":           ("San Francisco, CA",  "San Francisco",  "CA"),
    "san_diego":    ("San Diego, CA",      "San Diego",      "CA"),
    "sacramento":   ("Sacramento, CA",     "Sacramento",     "CA"),
    "dfw":          ("Dallas, TX",         "Dallas–Fort Worth", "TX"),
    "houston":      ("Houston, TX",        "Houston",        "TX"),
    "austin":       ("Austin, TX",         "Austin",         "TX"),
    "san_antonio":  ("San Antonio, TX",    "San Antonio",    "TX"),
    "miami":        ("Miami, FL",          "Miami",          "FL"),
    "tampa":        ("Tampa, FL",          "Tampa",          "FL"),
    "orlando":      ("Orlando, FL",        "Orlando",        "FL"),
    "jacksonville": ("Jacksonville, FL",   "Jacksonville",   "FL"),
}

VERTICALS = {
    "wedding_events": [
        "wedding photographer",
        "wedding videographer",
        "wedding planner",
        "wedding venue",
        "wedding DJ",
        "florist",
    ],
    "dental_medical": [
        "dental office",
        "orthodontist",
        "medical clinic",
    ],
    "home_services": [
        "HVAC contractor",
        "plumbing company",
        "electrician",
        "roofing contractor",
    ],
}

VERTICAL_DISPLAY = {
    "wedding_events": "Wedding & Events",
    "dental_medical": "Dental & Medical",
    "home_services": "Home Services",
}


def search_places(places_key: str, query: str, page_token: str | None = None):
    body = {"textQuery": query, "pageSize": 20}
    if page_token:
        body["pageToken"] = page_token
    resp = requests.post(
        PLACES_URL,
        json=body,
        headers={
            "X-Goog-Api-Key": places_key,
            "X-Goog-FieldMask": FIELD_MASK,
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Places error {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def extract_city(place: dict, fallback: str) -> str:
    for comp in place.get("addressComponents", []):
        if "locality" in comp.get("types", []):
            return comp.get("longText", fallback)
    return fallback


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True)
    ap.add_argument("--places-key", required=True)
    ap.add_argument("--cap", type=int, default=75)
    ap.add_argument("--metros", nargs="*", default=list(METROS.keys()))
    ap.add_argument("--verticals", nargs="*", default=list(VERTICALS.keys()))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    for m in args.metros:
        if m not in METROS:
            sys.exit(f"Unknown metro slug: {m}. Valid: {', '.join(METROS)}")
    for v in args.verticals:
        if v not in VERTICALS:
            sys.exit(f"Unknown vertical: {v}. Valid: {', '.join(VERTICALS)}")

    db = None
    if not args.dry_run:
        firebase_admin.initialize_app(credentials.Certificate(args.key))
        db = firestore.client()

    now = datetime.now(timezone.utc)
    grand_total = 0
    new_total = 0

    for metro_slug in args.metros:
        locality, metro_display, state = METROS[metro_slug]
        for vertical in args.verticals:
            seen: set[str] = set()
            cell_count = 0
            for term in VERTICALS[vertical]:
                if cell_count >= args.cap:
                    break
                query = f"{term} in {locality}"
                page_token = None
                pages = 0
                while cell_count < args.cap and pages < 3:
                    try:
                        data = search_places(args.places_key, query, page_token)
                    except Exception as exc:
                        print(f"  [warn] {query}: {exc}")
                        break
                    for place in data.get("places", []):
                        pid = place.get("id")
                        if not pid or pid in seen:
                            continue
                        if place.get("businessStatus") not in (None, "OPERATIONAL"):
                            continue
                        seen.add(pid)
                        cell_count += 1
                        grand_total += 1
                        doc = {
                            "name": place.get("displayName", {}).get("text", ""),
                            "placeId": pid,
                            "metroSlug": metro_slug,
                            "metro": metro_display,
                            "state": state,
                            "city": extract_city(place, metro_display),
                            "vertical": vertical,
                            "verticalDisplay": VERTICAL_DISPLAY[vertical],
                            "address": place.get("formattedAddress", ""),
                            "website": place.get("websiteUri", ""),
                            "phone": place.get("nationalPhoneNumber", ""),
                            "googleRating": place.get("rating"),
                            "googleReviewCount": place.get("userRatingCount"),
                            "status": "unclaimed",
                            "source": "places_crawl_v1",
                            "crawledAt": now,
                        }
                        if args.dry_run:
                            print(f"  [dry] {metro_slug}/{vertical}: {doc['name']}")
                        else:
                            db.collection("prospects").document(pid).set(
                                doc, merge=True
                            )
                            new_total += 1
                        if cell_count >= args.cap:
                            break
                    page_token = data.get("nextPageToken")
                    pages += 1
                    if not page_token:
                        break
                    time.sleep(0.4)
                time.sleep(0.3)
            print(f"{metro_slug:14s} {vertical:16s} -> {cell_count} businesses")

    print(f"\nDone. {grand_total} businesses discovered"
          + ("" if args.dry_run else f", {new_total} written to prospects."))
    print("Next: extend generate_roven_pages.py for unclaimed profile pages,")
    print("      then export the outreach list.")


if __name__ == "__main__":
    main()
