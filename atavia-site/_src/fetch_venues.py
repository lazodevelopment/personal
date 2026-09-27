#!/usr/bin/env python3
"""
fetch_venues.py — Atavia venue data pipeline (Google Places API)
================================================================
Pulls real wedding venues from Google Places and appends them to
_src/venues_data.py. Run in tranches (same pattern as the LeaseReputation
seeding runs): add cities to TARGETS, run, commit, repeat.

SETUP (once):
    pip install requests
    export GOOGLE_PLACES_API_KEY="your_key_here"     # Windows: set GOOGLE_PLACES_API_KEY=...

    Enable "Places API (New)" in Google Cloud console for your project.

RUN:
    python3 _src/fetch_venues.py                 # fetch TARGETS below
    python3 _src/fetch_venues.py --state TX      # only Texas targets
    python3 _src/fetch_venues.py --dry-run       # show what it'd add, write nothing

Then regenerate the site:
    python3 _src/gen_venues.py && python3 _src/build.py

COST NOTE: Places Text Search is billed per request (~$32/1000 as of writing;
you get a monthly free credit). Each city below = ~3 requests (3 query variants),
each returning up to 20 results. 200 cities ~= 600 requests. Check current
pricing before large runs. The script dedupes by place_id so re-running is cheap
and safe — it will not duplicate venues already in venues_data.py.
"""
import os, sys, json, re, time, pathlib

try:
    import requests
except ImportError:
    sys.exit("pip install requests")

SRC = pathlib.Path(__file__).resolve().parent
DATA = SRC / "venues_data.py"
KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "").strip()
ENDPOINT = "https://places.googleapis.com/v1/places:searchText"

# Query variants per city — more variants = more unique venues found.
QUERIES = [
    "wedding venues in {city}, {state}",
    "wedding reception venues {city}, {state}",
    "wedding barn and estate venues near {city}, {state}",
]

# Only keep places that look like real wedding/event venues.
GOOD_TYPES = {"wedding_venue", "event_venue", "banquet_hall"}
# Reject obvious non-venues that slip through.
BAD_WORDS = re.compile(r"\b(florist|photograph|videograph|bakery|cake|dress|bridal shop|"
                       r"tuxedo|planner|dj|catering only|limo|salon|spa|invitation)\b", re.I)

MIN_RATING = 4.0        # skip poorly reviewed venues
MIN_REVIEWS = 8         # skip venues with too little signal

# ---------------------------------------------------------------------------
# TARGETS — add cities here and re-run. (state, city) using USPS abbreviations.
# This starter list covers major wedding markets in all 50 states. Expand freely:
# adding 500 more cities here is how you get to thousands of pages.
# ---------------------------------------------------------------------------
TARGETS = [
 ("AL","Birmingham"),("AL","Huntsville"),("AL","Montgomery"),("AL","Mobile"),
 ("AL","Tuscaloosa"),("AL","Auburn"),("AL","Florence"),("AK","Anchorage"),
 ("AK","Fairbanks"),("AK","Juneau"),("AZ","Phoenix"),("AZ","Scottsdale"),
 ("AZ","Tucson"),("AZ","Mesa"),("AZ","Sedona"),("AZ","Flagstaff"),
 ("AZ","Chandler"),("AZ","Gilbert"),("AZ","Tempe"),("AZ","Prescott"),
 ("AR","Little Rock"),("AR","Fayetteville"),("AR","Bentonville"),("AR","Hot Springs"),
 ("AR","Rogers"),("CA","Los Angeles"),("CA","San Diego"),("CA","San Francisco"),
 ("CA","Sacramento"),("CA","San Jose"),("CA","Napa"),("CA","Sonoma"),
 ("CA","Santa Barbara"),("CA","Palm Springs"),("CA","Temecula"),("CA","Malibu"),
 ("CA","Pasadena"),("CA","Long Beach"),("CA","Orange County"),("CA","Newport Beach"),
 ("CA","Santa Cruz"),("CA","Monterey"),("CA","Carmel"),("CA","Paso Robles"),
 ("CA","Riverside"),("CA","Fresno"),("CA","Bakersfield"),("CA","Oakland"),
 ("CA","Berkeley"),("CA","Santa Rosa"),("CA","Redlands"),("CA","San Luis Obispo"),
 ("CO","Denver"),("CO","Colorado Springs"),("CO","Boulder"),("CO","Vail"),
 ("CO","Aspen"),("CO","Fort Collins"),("CO","Breckenridge"),("CO","Estes Park"),
 ("CO","Durango"),("CO","Steamboat Springs"),("CO","Grand Junction"),("CT","Hartford"),
 ("CT","New Haven"),("CT","Stamford"),("CT","Mystic"),("CT","Greenwich"),
 ("CT","Bridgeport"),("DE","Wilmington"),("DE","Dover"),("DE","Rehoboth Beach"),
 ("DE","Lewes"),("DC","Washington"),("FL","Miami"),("FL","Orlando"),
 ("FL","Tampa"),("FL","Jacksonville"),("FL","Naples"),("FL","Key West"),
 ("FL","St. Petersburg"),("FL","Sarasota"),("FL","Fort Lauderdale"),("FL","Palm Beach"),
 ("FL","Destin"),("FL","Clearwater"),("FL","St. Augustine"),("FL","Boca Raton"),
 ("FL","Fort Myers"),("FL","Gainesville"),("FL","Tallahassee"),("FL","Ocala"),
 ("FL","Winter Park"),("GA","Atlanta"),("GA","Savannah"),("GA","Athens"),
 ("GA","Augusta"),("GA","Macon"),("GA","Columbus"),("GA","Alpharetta"),
 ("GA","Marietta"),("GA","Blue Ridge"),("HI","Honolulu"),("HI","Maui"),
 ("HI","Kauai"),("HI","Kona"),("ID","Boise"),("ID","Coeur d'Alene"),
 ("ID","Sun Valley"),("ID","Idaho Falls"),("IL","Chicago"),("IL","Naperville"),
 ("IL","Springfield"),("IL","Peoria"),("IL","Rockford"),("IL","Evanston"),
 ("IL","Galena"),("IL","Champaign"),("IN","Indianapolis"),("IN","Fort Wayne"),
 ("IN","Bloomington"),("IN","South Bend"),("IN","Carmel"),("IN","Evansville"),
 ("IA","Des Moines"),("IA","Cedar Rapids"),("IA","Iowa City"),("IA","Davenport"),
 ("KS","Wichita"),("KS","Overland Park"),("KS","Topeka"),("KS","Lawrence"),
 ("KY","Louisville"),("KY","Lexington"),("KY","Bowling Green"),("KY","Covington"),
 ("LA","New Orleans"),("LA","Baton Rouge"),("LA","Lafayette"),("LA","Shreveport"),
 ("ME","Portland"),("ME","Bar Harbor"),("ME","Kennebunkport"),("ME","Camden"),
 ("ME","Bangor"),("MD","Baltimore"),("MD","Annapolis"),("MD","Frederick"),
 ("MD","Bethesda"),("MD","Ocean City"),("MA","Boston"),("MA","Cape Cod"),
 ("MA","Worcester"),("MA","Salem"),("MA","Newburyport"),("MA","Lenox"),
 ("MA","Nantucket"),("MA","Martha's Vineyard"),("MA","Plymouth"),("MA","Springfield"),
 ("MI","Detroit"),("MI","Grand Rapids"),("MI","Traverse City"),("MI","Ann Arbor"),
 ("MI","Petoskey"),("MI","Kalamazoo"),("MI","Lansing"),("MN","Minneapolis"),
 ("MN","Saint Paul"),("MN","Duluth"),("MN","Rochester"),("MN","Stillwater"),
 ("MS","Jackson"),("MS","Gulfport"),("MS","Oxford"),("MS","Biloxi"),
 ("MO","St. Louis"),("MO","Kansas City"),("MO","Springfield"),("MO","Columbia"),
 ("MO","Branson"),("MT","Bozeman"),("MT","Missoula"),("MT","Billings"),
 ("MT","Whitefish"),("MT","Big Sky"),("NE","Omaha"),("NE","Lincoln"),
 ("NE","Grand Island"),("NV","Las Vegas"),("NV","Reno"),("NV","Lake Tahoe"),
 ("NV","Henderson"),("NH","Manchester"),("NH","Portsmouth"),("NH","Concord"),
 ("NH","North Conway"),("NJ","Jersey City"),("NJ","Atlantic City"),("NJ","Princeton"),
 ("NJ","Cape May"),("NJ","Newark"),("NJ","Morristown"),("NJ","Asbury Park"),
 ("NM","Albuquerque"),("NM","Santa Fe"),("NM","Taos"),("NM","Las Cruces"),
 ("NY","New York"),("NY","Brooklyn"),("NY","Buffalo"),("NY","Rochester"),
 ("NY","Syracuse"),("NY","Albany"),("NY","Hudson"),("NY","Saratoga Springs"),
 ("NY","Long Island"),("NY","Westchester"),("NY","Finger Lakes"),("NY","Ithaca"),
 ("NY","Poughkeepsie"),("NC","Charlotte"),("NC","Raleigh"),("NC","Asheville"),
 ("NC","Wilmington"),("NC","Durham"),("NC","Winston-Salem"),("NC","Greensboro"),
 ("NC","Chapel Hill"),("NC","Outer Banks"),("ND","Fargo"),("ND","Bismarck"),
 ("ND","Grand Forks"),("OH","Columbus"),("OH","Cleveland"),("OH","Cincinnati"),
 ("OH","Dayton"),("OH","Toledo"),("OH","Akron"),("OK","Oklahoma City"),
 ("OK","Tulsa"),("OK","Norman"),("OK","Broken Arrow"),("OR","Portland"),
 ("OR","Bend"),("OR","Eugene"),("OR","Hood River"),("OR","Ashland"),
 ("OR","Salem"),("PA","Philadelphia"),("PA","Pittsburgh"),("PA","Lancaster"),
 ("PA","Harrisburg"),("PA","Bethlehem"),("PA","Erie"),("PA","Doylestown"),
 ("PA","Poconos"),("RI","Providence"),("RI","Newport"),("RI","Warwick"),
 ("SC","Charleston"),("SC","Greenville"),("SC","Columbia"),("SC","Myrtle Beach"),
 ("SC","Hilton Head"),("SC","Beaufort"),("SD","Sioux Falls"),("SD","Rapid City"),
 ("SD","Deadwood"),("TN","Nashville"),("TN","Memphis"),("TN","Knoxville"),
 ("TN","Chattanooga"),("TN","Gatlinburg"),("TN","Franklin"),("TX","Dallas"),
 ("TX","Austin"),("TX","Houston"),("TX","San Antonio"),("TX","Fort Worth"),
 ("TX","Fredericksburg"),("TX","McKinney"),("TX","Plano"),("TX","Galveston"),
 ("TX","El Paso"),("TX","Waco"),("TX","Corpus Christi"),("TX","Lubbock"),
 ("TX","Frisco"),("TX","Round Rock"),("TX","New Braunfels"),("TX","Tyler"),
 ("UT","Salt Lake City"),("UT","Park City"),("UT","Moab"),("UT","Provo"),
 ("UT","St. George"),("VT","Burlington"),("VT","Stowe"),("VT","Manchester"),
 ("VT","Woodstock"),("VA","Richmond"),("VA","Virginia Beach"),("VA","Charlottesville"),
 ("VA","Norfolk"),("VA","Alexandria"),("VA","Roanoke"),("VA","Williamsburg"),
 ("VA","Leesburg"),("WA","Seattle"),("WA","Spokane"),("WA","Tacoma"),
 ("WA","Bellingham"),("WA","Woodinville"),("WA","Walla Walla"),("WA","Olympia"),
 ("WA","Vancouver"),("WV","Charleston"),("WV","Morgantown"),("WV","Huntington"),
 ("WI","Milwaukee"),("WI","Madison"),("WI","Green Bay"),("WI","Door County"),
 ("WI","Lake Geneva"),("WI","Appleton"),("WY","Jackson"),("WY","Cheyenne"),
 ("WY","Casper"),("WY","Cody"),
]

FIELDS = ("places.id,places.displayName,places.formattedAddress,places.rating,"
          "places.userRatingCount,places.types,places.editorialSummary,"
          "places.addressComponents")

PAGES_PER_QUERY = 3      # 20 results per page -> up to 60 per query. --pages N to change.

def search(query, pages=PAGES_PER_QUERY):
    """Text Search with pagination. Returns up to pages*20 places."""
    out, token = [], None
    for _ in range(max(1, pages)):
        payload = {"textQuery": query, "pageSize": 20}
        if token:
            payload["pageToken"] = token
        r = requests.post(ENDPOINT,
            headers={"Content-Type": "application/json",
                     "X-Goog-Api-Key": KEY,
                     "X-Goog-FieldMask": FIELDS + ",nextPageToken"},
            json=payload, timeout=30)
        if r.status_code != 200:
            print("   ! %s -> %s %s" % (query, r.status_code, r.text[:140]))
            break
        j = r.json()
        out.extend(j.get("places", []))
        token = j.get("nextPageToken")
        if not token:
            break
        time.sleep(1.2)      # next_page_token needs a moment to become valid
    return out

def city_of(p, fallback):
    for c in p.get("addressComponents", []):
        if "locality" in c.get("types", []):
            return c.get("longText") or fallback
    return fallback

def character_of(p):
    """Short honest descriptor. Uses Google's editorial summary when present,
    otherwise a neutral phrase derived from its types."""
    ed = (p.get("editorialSummary") or {}).get("text", "").strip()
    if ed:
        ed = ed.rstrip(".")
        return ed[0].lower() + ed[1:] if ed else ""
    t = set(p.get("types", []))
    if "banquet_hall" in t: return "a banquet and reception venue"
    if "wedding_venue" in t: return "a dedicated wedding venue"
    return "an event venue"

def load_existing():
    if not DATA.exists():
        return [], set()
    ns = {}
    exec(compile(DATA.read_text(), str(DATA), "exec"), ns)
    rows = ns.get("VENUES", [])
    return rows, {r["place_id"] for r in rows if r.get("place_id")}

def main():
    if not KEY or KEY.lower() in ("your-new-key", "your_key_here", "...", "your-key"):
        sys.exit("Set a REAL GOOGLE_PLACES_API_KEY first.\n"
                 '  PowerShell:  $env:GOOGLE_PLACES_API_KEY = "AIza..."\n'
                 "  Get one: Google Cloud Console -> enable 'Places API (New)' -> Credentials")
    dry = "--dry-run" in sys.argv
    only = None
    pages = PAGES_PER_QUERY
    if "--state" in sys.argv:
        only = sys.argv[sys.argv.index("--state") + 1].upper()
    if "--pages" in sys.argv:
        pages = int(sys.argv[sys.argv.index("--pages") + 1])

    rows, seen = load_existing()
    targets = [t for t in TARGETS if not only or t[0] == only]
    print("existing venues: %d" % len(rows))
    print("plan: %d cities x %d queries x up to %d pages = up to ~%d API requests\n"
          % (len(targets), len(QUERIES), pages, len(targets) * len(QUERIES) * pages))
    added = 0

    for n, (state, city) in enumerate(targets, 1):
        found = 0
        for qt in QUERIES:
            for p in search(qt.format(city=city, state=state), pages):
                pid = p.get("id")
                name = (p.get("displayName") or {}).get("text", "").strip()
                addr = p.get("formattedAddress", "").strip()
                if not pid or pid in seen or not name or not addr:
                    continue
                if not (set(p.get("types", [])) & GOOD_TYPES):
                    continue
                if BAD_WORDS.search(name):
                    continue
                if (p.get("rating") or 0) < MIN_RATING:
                    continue
                if (p.get("userRatingCount") or 0) < MIN_REVIEWS:
                    continue
                seen.add(pid)
                rows.append(dict(place_id=pid, name=name, city=city_of(p, city),
                                 state=state, address=addr,
                                 rating=p.get("rating"), reviews=p.get("userRatingCount"),
                                 character=character_of(p)))
                found += 1
                added += 1
            time.sleep(0.2)
        print("  [%d/%d] %s, %s: +%d   (running total: %d)" % (n, len(targets), city, state, found, len(rows)))
        if not dry and n % 10 == 0:      # checkpoint so a long run can't lose work
            save(rows, quiet=True)

    print("\nadded %d new venues -- total %d" % (added, len(rows)))
    if dry:
        print("(dry run -- nothing written)")
        return
    save(rows)
    print("\nNext:\n  python _src\\gen_venues.py\n  python _src\\build.py")

def save(rows, quiet=False):
    rows.sort(key=lambda r: (r["state"], r["city"], r["name"]))
    with DATA.open("w", encoding="utf-8") as f:
        f.write("# Auto-generated by fetch_venues.py -- real venues from Google Places.\n")
        f.write("# Safe to re-run; dedupes on place_id.\n")
        f.write("VENUES = [\n")
        for r in rows:
            f.write("    %r,\n" % (r,))
        f.write("]\n")
    if not quiet:
        print("wrote %s (%d venues)" % (DATA.name, len(rows)))

if __name__ == "__main__":
    main()
