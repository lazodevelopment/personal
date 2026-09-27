# seed_metros.py — LeaseReputation directory seeder (Dallas + Massachusetts)
#
# Seeds apartment communities into Firestore for new metros, matching the
# exact schema createCommunityFromPlace writes (doc id == placeId, so the
# in-app "Add community" flow dedupes against these automatically).
# Existing docs are NEVER touched — safe to re-run anytime.
#
# Setup (same folder as serviceAccountKey.json):
#   pip install firebase-admin requests
#
# IMPORTANT — API key: use the SERVER-SIDE Places key (the one in Secret
# Manager with API-only restriction). The browser key is referrer-restricted
# and will 403 from a script.
#
# Usage:
#   python seed_metros.py dallas
#   python seed_metros.py boston
#   python seed_metros.py worcester
#   python seed_metros.py springfield
#   python seed_metros.py all

import re
import sys
import time
import requests
import firebase_admin
from firebase_admin import credentials, firestore

# ── paste your SERVER Places API key here ──
import os as _os
def _env(name):
    v = _os.environ.get(name)
    if not v:
        p = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '.env')
        if _os.path.exists(p):
            for line in open(p, encoding='utf-8'):
                if line.startswith(name + '='): v = line.split('=', 1)[1].strip()
    if not v: raise SystemExit(name + ' is not set (put it in .env next to this script)')
    return v
PLACES_API_KEY = _env("PLACES_API_KEY")
METROS = {
    # ── already seeded (safe to re-run; existing docs are skipped) ──
    "dallas": ["Dallas, TX", "Frisco, TX", "Plano, TX", "McKinney, TX", "Allen, TX",
               "Richardson, TX", "Irving, TX", "Carrollton, TX", "Uptown Dallas, TX"],
    "boston": ["Boston, MA", "Cambridge, MA", "Somerville, MA", "Brookline, MA", "Quincy, MA",
               "Medford, MA", "Waltham, MA", "Allston Boston, MA", "Dorchester Boston, MA"],
    "worcester": ["Worcester, MA", "Shrewsbury, MA", "Westborough, MA"],
    "springfield": ["Springfield, MA", "Chicopee, MA", "West Springfield, MA", "Holyoke, MA"],
    "phoenix": ["Phoenix, AZ", "Scottsdale, AZ", "Tempe, AZ", "Chandler, AZ", "Gilbert, AZ",
                "Mesa, AZ", "Glendale, AZ", "Peoria, AZ"],

    # ── Texas ──
    "houston": ["Houston, TX", "Katy, TX", "Sugar Land, TX", "The Woodlands, TX",
                "Pearland, TX", "Spring, TX", "Cypress, TX", "Midtown Houston, TX"],
    "austin": ["Austin, TX", "Round Rock, TX", "Cedar Park, TX", "Pflugerville, TX",
               "South Austin, TX", "North Austin, TX"],
    "sanantonio": ["San Antonio, TX", "New Braunfels, TX", "Stone Oak San Antonio, TX"],

    # ── Southeast ──
    "atlanta": ["Atlanta, GA", "Sandy Springs, GA", "Marietta, GA", "Alpharetta, GA",
                "Decatur, GA", "Smyrna, GA", "Midtown Atlanta, GA", "Buckhead Atlanta, GA"],
    "charlotte": ["Charlotte, NC", "Concord, NC", "Huntersville, NC", "South End Charlotte, NC"],
    "raleigh": ["Raleigh, NC", "Durham, NC", "Cary, NC", "Chapel Hill, NC"],
    "nashville": ["Nashville, TN", "Franklin, TN", "Murfreesboro, TN", "East Nashville, TN"],

    # ── Florida ──
    "miami": ["Miami, FL", "Fort Lauderdale, FL", "Miami Beach, FL", "Doral, FL",
              "Coral Gables, FL", "Boca Raton, FL", "West Palm Beach, FL", "Brickell Miami, FL"],
    "tampa": ["Tampa, FL", "St. Petersburg, FL", "Brandon, FL", "Clearwater, FL"],
    "orlando": ["Orlando, FL", "Kissimmee, FL", "Winter Park, FL", "Lake Nona Orlando, FL"],
    "jacksonville": ["Jacksonville, FL", "St. Johns, FL", "Jacksonville Beach, FL"],

    # ── Mountain / Southwest ──
    "vegas": ["Las Vegas, NV", "Henderson, NV", "North Las Vegas, NV", "Summerlin Las Vegas, NV"],
    "denver": ["Denver, CO", "Aurora, CO", "Lakewood, CO", "Littleton, CO",
               "Boulder, CO", "Westminster, CO"],
    "saltlake": ["Salt Lake City, UT", "Sandy, UT", "Lehi, UT", "Provo, UT"],
    "albuquerque": ["Albuquerque, NM", "Rio Rancho, NM"],
    "tucson": ["Tucson, AZ", "Oro Valley, AZ"],
    "boise": ["Boise, ID", "Meridian, ID", "Nampa, ID"],

    # ── California ──
    "losangeles": ["Los Angeles, CA", "Santa Monica, CA", "Pasadena, CA", "Glendale, CA",
                   "Long Beach, CA", "Woodland Hills, CA", "Downtown Los Angeles, CA",
                   "Sherman Oaks, CA"],
    "orangecounty": ["Irvine, CA", "Anaheim, CA", "Costa Mesa, CA", "Fullerton, CA",
                     "Huntington Beach, CA"],
    "sandiego": ["San Diego, CA", "Chula Vista, CA", "Carlsbad, CA", "Escondido, CA"],
    "bayarea": ["San Francisco, CA", "Oakland, CA", "San Jose, CA", "Sunnyvale, CA",
                "Mountain View, CA", "Fremont, CA", "Walnut Creek, CA"],
    "sacramento": ["Sacramento, CA", "Roseville, CA", "Folsom, CA", "Elk Grove, CA"],

    # ── Pacific Northwest ──
    "seattle": ["Seattle, WA", "Bellevue, WA", "Redmond, WA", "Kirkland, WA",
                "Tacoma, WA", "Renton, WA", "Capitol Hill Seattle, WA"],
    "portland": ["Portland, OR", "Beaverton, OR", "Hillsboro, OR", "Gresham, OR"],

    # ── Midwest ──
    "chicago": ["Chicago, IL", "Evanston, IL", "Naperville, IL", "Schaumburg, IL",
                "Oak Park, IL", "Arlington Heights, IL", "Lincoln Park Chicago, IL"],
    "minneapolis": ["Minneapolis, MN", "St. Paul, MN", "Bloomington, MN", "Edina, MN"],
    "columbus": ["Columbus, OH", "Dublin, OH", "Westerville, OH", "Short North Columbus, OH"],
    "indianapolis": ["Indianapolis, IN", "Carmel, IN", "Fishers, IN"],
    "kansascity": ["Kansas City, MO", "Overland Park, KS", "Lee's Summit, MO"],
    "detroit": ["Detroit, MI", "Royal Oak, MI", "Troy, MI", "Ann Arbor, MI"],
    "cleveland": ["Cleveland, OH", "Lakewood, OH", "Beachwood, OH"],
    "cincinnati": ["Cincinnati, OH", "Mason, OH", "Covington, KY"],
    "stlouis": ["St. Louis, MO", "Clayton, MO", "Chesterfield, MO"],
    "milwaukee": ["Milwaukee, WI", "Wauwatosa, WI"],
    "omaha": ["Omaha, NE", "Bellevue, NE"],
    "desmoines": ["Des Moines, IA", "West Des Moines, IA"],
    "wichita": ["Wichita, KS"],
    "fargo": ["Fargo, ND", "Bismarck, ND"],
    "siouxfalls": ["Sioux Falls, SD", "Rapid City, SD"],

    # ── Northeast / Mid-Atlantic ──
    "nyc": ["Manhattan, NY", "Brooklyn, NY", "Queens, NY", "Bronx, NY",
            "Jersey City, NJ", "Hoboken, NJ", "Long Island City, NY", "White Plains, NY"],
    "philadelphia": ["Philadelphia, PA", "King of Prussia, PA", "Conshohocken, PA",
                     "Cherry Hill, NJ"],
    "dc": ["Washington, DC", "Arlington, VA", "Alexandria, VA", "Silver Spring, MD",
           "Bethesda, MD", "Tysons, VA", "Rockville, MD"],
    "baltimore": ["Baltimore, MD", "Towson, MD", "Columbia, MD"],
    "pittsburgh": ["Pittsburgh, PA", "Cranberry Township, PA"],
    "hartford": ["Hartford, CT", "West Hartford, CT", "Stamford, CT", "New Haven, CT"],
    "providence": ["Providence, RI", "Warwick, RI"],
    "buffalo": ["Buffalo, NY", "Amherst, NY", "Rochester, NY"],
    "virginia": ["Virginia Beach, VA", "Norfolk, VA", "Richmond, VA", "Glen Allen, VA"],
    "newengland_north": ["Burlington, VT", "Portland, ME", "Manchester, NH", "Nashua, NH"],
    "delaware": ["Wilmington, DE", "Newark, DE"],

    # ── South ──
    "memphis": ["Memphis, TN", "Germantown, TN"],
    "neworleans": ["New Orleans, LA", "Metairie, LA", "Baton Rouge, LA"],
    "okc": ["Oklahoma City, OK", "Edmond, OK", "Norman, OK", "Tulsa, OK"],
    "birmingham": ["Birmingham, AL", "Hoover, AL", "Huntsville, AL"],
    "louisville": ["Louisville, KY", "Lexington, KY"],
    "littlerock": ["Little Rock, AR", "Fayetteville, AR"],
    "jackson": ["Jackson, MS", "Gulfport, MS"],
    "charleston_sc": ["Charleston, SC", "Mount Pleasant, SC", "Columbia, SC", "Greenville, SC"],
    "westvirginia": ["Charleston, WV", "Morgantown, WV"],

    # ── Non-contiguous / Mountain West ──
    "hawaii": ["Honolulu, HI"],
    "alaska": ["Anchorage, AK"],
    "montana_wyoming": ["Billings, MT", "Missoula, MT", "Cheyenne, WY", "Casper, WY"],
}

# ── Tranches: run one per day-ish, in this order. Every state covered. ──
TRANCHES = {
    "t1_texas":       ["houston", "austin", "sanantonio"],
    "t2_southeast":   ["atlanta", "charlotte", "raleigh", "nashville"],
    "t3_florida":     ["miami", "tampa", "orlando", "jacksonville"],
    "t4_mountain":    ["vegas", "denver", "saltlake", "albuquerque", "tucson", "boise"],
    "t5_pnw":         ["seattle", "portland", "sacramento"],
    "t6_california":  ["losangeles", "orangecounty", "sandiego", "bayarea"],
    "t7_midwest1":    ["chicago", "minneapolis", "columbus", "indianapolis", "kansascity"],
    "t8_midwest2":    ["detroit", "cleveland", "cincinnati", "stlouis", "milwaukee",
                       "omaha", "desmoines", "wichita", "fargo", "siouxfalls"],
    "t9_northeast1":  ["nyc", "philadelphia", "dc", "baltimore", "pittsburgh"],
    "t10_northeast2": ["hartford", "providence", "buffalo", "virginia",
                       "newengland_north", "delaware"],
    "t11_south":      ["memphis", "neworleans", "okc", "birmingham", "louisville",
                       "littlerock", "jackson", "charleston_sc", "westvirginia"],
    "t12_frontier":   ["hawaii", "alaska", "montana_wyoming"],
}

# Query phrasings per locality — different phrasings surface different results.
QUERY_TEMPLATES = [
    "apartment complexes in {loc}",
    "apartment communities in {loc}",
    "luxury apartments in {loc}",
]

ALLOWED_TYPES = {"apartment_building", "apartment_complex", "condominium_complex"}

# Major operators (Avalon, Camden, ...) are often typed ONLY as
# real_estate_agency — accept those too, unless the name reads like an
# actual brokerage or management office.
AGENCY_BLOCKLIST = re.compile(
    r"realty|realtor|real estate|broker|property (management|mgmt)"
    r"|management (co|company|group|llc)|leasing office|homes for sale",
    re.I,
)


def looks_residential(name, types):
    t = set(types or [])
    if t & ALLOWED_TYPES:
        return True
    return "real_estate_agency" in t and not AGENCY_BLOCKLIST.search(name)

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,"
    "places.location,places.photos,places.types,nextPageToken"
)


def search_pages(query):
    """Yield place dicts for a text query, following pagination (max 60)."""
    page_token = None
    for _ in range(3):  # up to 3 pages of 20
        body = {"textQuery": query, "pageSize": 20}
        if page_token:
            body["pageToken"] = page_token
        r = requests.post(
            SEARCH_URL,
            json=body,
            headers={
                "X-Goog-Api-Key": PLACES_API_KEY,
                "X-Goog-FieldMask": FIELD_MASK,
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        if r.status_code != 200:
            print(f"    ! {r.status_code} for '{query}': {r.text[:200]}")
            return
        data = r.json()
        for p in data.get("places", []):
            yield p
        page_token = data.get("nextPageToken")
        if not page_token:
            return
        time.sleep(1.2)  # let the token settle


def main():
    arg = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    if arg == "list" or arg not in list(METROS) + list(TRANCHES) + ["all"]:
        print("Usage: python seed_metros.py <metro|tranche|list>")
        print("\nTranches (run one per day, in order):")
        for t, ms in TRANCHES.items():
            print(f"  {t}: {', '.join(ms)}")
        print("\nIndividual metros:", ", ".join(sorted(METROS)))
        sys.exit(0 if arg == "list" else 1)
    if PLACES_API_KEY.startswith("PASTE"):
        print("Paste your SERVER Places API key into PLACES_API_KEY first.")
        sys.exit(1)

    if arg == "all":
        print("Running ALL metros in one shot is deliberately discouraged —")
        print("Google indexing and Places billing both prefer tranches.")
        confirm = input("Type YES to proceed anyway: ")
        if confirm.strip() != "YES":
            sys.exit(0)
        metros = list(METROS)
    elif arg in TRANCHES:
        metros = TRANCHES[arg]
    else:
        metros = [arg]

    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()

    # One pass to learn every existing community id — never overwrite.
    print("Loading existing community ids…")
    existing = {d.id for d in db.collection("communities").select([]).stream()}
    print(f"  {len(existing)} already in the directory.")

    grand_total = 0
    for metro in metros:
        print(f"\n=== {metro.upper()} ===")
        found, added, batch, batch_n = {}, 0, db.batch(), 0
        for loc in METROS[metro]:
            loc_new = 0
            for tmpl in QUERY_TEMPLATES:
                for p in search_pages(tmpl.format(loc=loc)):
                    pid = p.get("id", "")
                    if not pid or pid in found or pid in existing:
                        continue
                    name = (p.get("displayName") or {}).get("text", "").strip()
                    if not name:
                        continue
                    if not looks_residential(name, p.get("types")):
                        continue
                    found[pid] = True
                    loc_new += 1
                    location = p.get("location") or {}
                    photos = p.get("photos") or []
                    batch.set(
                        db.collection("communities").document(pid),
                        {
                            "name": name,
                            "nameLower": name.lower(),
                            "address": p.get("formattedAddress", ""),
                            "placeId": pid,
                            "location": firestore.GeoPoint(
                                location.get("latitude", 0.0),
                                location.get("longitude", 0.0),
                            )
                            if location
                            else None,
                            "photoRef": (photos[0].get("name", "") if photos else ""),
                            "reviewCount": 0,
                            "createdAt": firestore.SERVER_TIMESTAMP,
                            "source": f"seed-{metro}",
                        },
                    )
                    batch_n += 1
                    added += 1
                    if batch_n >= 400:
                        batch.commit()
                        batch, batch_n = db.batch(), 0
                time.sleep(0.25)
            print(f"  {loc}: +{loc_new}")
        if batch_n:
            batch.commit()
        grand_total += added
        print(f"  {metro}: {added} new communities seeded.")

    print(f"\nDone. {grand_total} new communities across {len(metros)} metro(s).")
    print("They appear in the app immediately (nameLower ordering).")


if __name__ == "__main__":
    main()