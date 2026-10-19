r"""JC-LAZO-MARKETS-1019: Zola's 566 vendor markets as Lazo's markets model.

    python generate\zola_markets.py            # fetch from zola.com, write generate/data/markets.json
    python generate\zola_markets.py raw.json   # build from a saved copy of the list instead

Zola's public list (GET https://www.zola.com/web-marketplace-api/v1/vendor-market/list, no
auth) has id / key / label / marketLevel but no state. Zola numbers its markets in
state-contiguous id runs (3172-3197 is California, 3378-3407 Texas ...), so STATE_BLOCKS
gives the state and STATE_OVERRIDES fixes the handful Zola filed under a neighbour
(St Louis sits in the Illinois run, Jacksonville in Georgia's, Louisville in Indiana's).

Each market also carries the Lazo metros it overlaps (LAZO_TO_ZOLA, hand-built from
config/metros.py): the worker shows a vendor on a metro's pages when that metro maps to
one of the vendor's homeMarkets or travelMarkets. A market with no Lazo metro is still a
valid pick in the vendor app; it just has no page yet.
"""
import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from config.metros import METROS  # noqa: E402

OUT = HERE / "data" / "markets.json"
WORKER_JS = HERE.parent / "worker" / "src" / "markets.js"      # metro -> market keys, for the live lists
DART = HERE.parent / "app-patches" / "v220_parts" / "markets_dart.txt"   # the vendor app's picker list
URL = "https://www.zola.com/web-marketplace-api/v1/vendor-market/list"

STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado",
    "CT": "Connecticut", "DE": "Delaware", "DC": "Washington, D.C.", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts",
    "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
    "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}

# (first id, last id, state) - Zola's id runs, read off the sorted list on 2026-10-19
STATE_BLOCKS = [
    (1062, 1066, "NY"), (3158, 3161, "NJ"), (3162, 3171, "NY"), (3172, 3197, "CA"), (3198, 3214, "IL"),
    (3215, 3228, "PA"), (3229, 3233, "CT"), (3234, 3247, "VA"), (3248, 3262, "GA"), (3263, 3278, "FL"),
    (3279, 3280, "DE"), (3281, 3284, "MD"), (3285, 3290, "WV"), (3291, 3305, "WA"), (3306, 3320, "TN"),
    (3321, 3335, "MN"), (3336, 3352, "MI"), (3353, 3367, "CO"), (3368, 3377, "MA"), (3378, 3407, "TX"),
    (3408, 3415, "AZ"), (3416, 3420, "VT"), (3421, 3424, "NH"), (3425, 3429, "ME"), (3430, 3430, "RI"),
    (3431, 3439, "OR"), (3440, 3452, "OH"), (3453, 3468, "KS"), (3469, 3478, "MO"), (3479, 3493, "NC"),
    (3494, 3503, "UT"), (3504, 3509, "NV"), (3510, 3518, "AL"), (3519, 3530, "SC"), (3531, 3542, "IN"),
    (3543, 3550, "KY"), (3551, 3551, "MN"), (3552, 3553, "ND"), (3554, 3557, "TN"), (3558, 3568, "LA"),
    (3569, 3580, "ID"), (3581, 3592, "OK"), (3593, 3602, "AK"), (3603, 3615, "NM"), (3616, 3629, "AR"),
    (3630, 3642, "IA"), (3643, 3654, "MS"), (3655, 3667, "MT"), (3668, 3673, "ND"), (3674, 3682, "SD"),
    (3683, 3686, "HI"), (3687, 3693, "WY"), (3694, 3709, "NE"), (3710, 3722, "WI"), (3723, 3723, "NY"),
    (3724, 3724, "MN"),
]

# markets Zola filed in a neighbouring state's run (checked one by one against the label)
STATE_OVERRIDES = {
    "st-louis": "MO", "youngstown-warren": "OH", "jacksonville": "FL", "chesapeake-bay": "MD",
    "dc-metropolitan": "DC", "eastern-shore": "MD", "grand-rapids": "MI", "rochester-ny": "NY",
    "green-bay": "WI", "louisville": "KY", "jackson-hole": "WY", "dubuque": "IA", "las-cruces": "NM",
    "vancouver": "WA", "duluth-superior": "WI", "council-bluffs": "IA", "texarkana": "TX",
}

# Lazo metro id -> the Zola markets it overlaps. A Zola market may serve several Lazo metros.
LAZO_TO_ZOLA = {
    # Arizona
    "phoenix": ["phoenix"], "tucson": ["tucson", "southeast-arizona"], "sedona": ["flagstaff-sedona-grand-canyon"],
    "lake-havasu-city": ["mohave-country"], "kingman": ["mohave-country"], "bullhead-city": ["mohave-country"],
    "yuma": ["west-coast-arizona"],
    # Colorado
    "denver": ["denver-metropolitan", "denver-suburban", "boulder", "front-range-foothills", "fort-collins-larimer"],
    "colorado-springs": ["colorado-springs", "pueblo"], "aspen-vail": ["mountain-resorts"],
    "grand-junction": ["grand-junction-western-slope"],
    # Texas
    "dallas-fort-worth": ["dfw-metroplex", "dallas", "fort-worth"],
    "houston": ["houston-metropolitan", "houston-suburban", "galveston"],
    "austin": ["austin-metropolitan", "austin-round-rock"],
    "san-antonio": ["san-antonio-metropolitan", "san-antonio-suburban"],
    "el-paso": ["el-paso", "hudspeth", "las-cruces"], "corpus-christi": ["corpus-christi-coastal-bend"],
    "lubbock": ["lubbock"], "laredo": ["laredo"], "amarillo": ["amarillo-north-panhandle"],
    "brownsville": ["rio-grande-valley"], "mcallen": ["rio-grande-valley"], "killeen": ["killeen-central-texas"],
    "waco": ["waco"], "midland": ["midland-odessa-south-plains"], "abilene": ["abilene-west-central-texas"],
    "college-station": ["bryan-college-station"], "beaumont": ["east-texas"], "tyler": ["east-texas"],
    "longview": ["east-texas"], "lufkin": ["east-texas"], "wichita-falls": ["wichita-falls"],
    "san-angelo": ["san-angelo-concho-valley"], "texarkana": ["texarkana", "texarkana-southwest-arkansas"],
    "victoria": ["victoria-golden-crescent"], "sherman": ["northeast-texas"], "greenville-tx": ["northeast-texas"],
    "del-rio": ["southwest-texas"], "eagle-pass": ["southwest-texas"], "huntsville-tx": ["houston-suburban"],
    "lake-jackson": ["houston-suburban"], "corsicana": ["dallas"],
    # Nevada
    "las-vegas": ["las-vegas", "southwest-nevada"], "lake-tahoe-reno": ["reno-sparks", "carson-city"],
    # Georgia
    "atlanta": ["atlanta-metropolitan", "atlanta-suburban"], "savannah": ["savannah", "st-simons-jekyll-island", "hilton-head"],
    "augusta": ["augusta", "augusta-richmond"], "columbus-ga": ["columbus", "auburn-columbus"], "macon": ["macon"],
    "albany-ga": ["southwest-georgia"], "valdosta": ["southern-georgia"], "rome": ["northwest-georgia"],
    "dalton": ["northwest-georgia", "cleveland-dalton"], "carrollton": ["west-georgia"], "lagrange": ["west-georgia"],
    "statesboro": ["southeast-central-georgia"],
    # Tennessee
    "nashville": ["nashville-metropolitan", "nashville-suburban-north", "nashville-suburban-south"],
    "memphis": ["memphis-metropolitan", "memphis-suburban-northeast", "memphis-suburban-west", "memphis-suburban-south"],
    "knoxville": ["knoxville-metropolitan", "knoxville-suburban"], "chattanooga": ["chattanooga", "cleveland-dalton"],
    "clarksville": ["clarksville"], "johnson-city": ["tri-cities"], "jackson": ["jackson"],
    "cookeville": ["upper-cumberland"], "smoky-mountains": ["smoky-mountains"],
    # Illinois
    "chicago": ["chicago-metropolitan", "northern-chicago-suburbs", "southern-chicago-suburbs", "western-chicago-suburbs"],
    "hammond": ["gary-chicago-suburban"], "rockford": ["rockford"], "champaign": ["champaign-urbana"], "peoria": ["peoria"],
    "springfield-il": ["springfield-il"], "bloomington-il": ["bloomington-normal"], "decatur": ["central-illinois"],
    "davenport": ["quad-cities"], "dekalb": ["north-central-illinois"], "edwardsville": ["st-louis"],
    "quincy": ["west-central-illinois"], "galesburg": ["west-central-illinois"], "danville-il": ["central-illinois"],
    # Missouri
    "st-louis": ["st-louis"], "kansas-city": ["kansas-city-metropolitan", "kansas-city-greater-area"],
    "springfield": ["springfield-metropolitan"], "columbia": ["central-missouri"], "jefferson-city": ["jefferson-city"],
    "joplin": ["southwest-missouri"], "cape-girardeau": ["southeast-missouri"],
    # California
    "los-angeles": ["los-angeles"], "san-diego": ["san-diego"],
    "san-francisco-bay": ["san-francisco-metropolitan", "oakland-east-bay", "san-jose-south-bay"],
    "sacramento": ["sacramento-metropolitan", "sacramento-suburban", "gold-country"], "inland-empire": ["san-bernardino"],
    "palm-springs": ["palm-springs-riverside"], "orange-county": ["orange-county"], "santa-barbara": ["santa-barbara"],
    "napa-sonoma": ["napa-sonoma-north-bay"], "monterey-big-sur": ["monterey-carmel"],
    "fresno": ["fresno", "central-valley", "central-valley-south"], "bakersfield": ["bakersfield"],
    "stockton": ["central-valley-north"], "modesto": ["central-valley-north"], "merced": ["central-valley"],
    "los-banos": ["central-valley"], "santa-maria": ["santa-barbara"], "san-luis-obispo": ["san-luis-obispo"],
    "el-paso-de-robles-paso-robles": ["san-luis-obispo"], "chico": ["far-north-shasta"], "redding": ["far-north-shasta"],
    "yuba-city": ["sacramento-suburban"], "eureka": ["coastal-north"], "el-centro": ["imperial"],
    "lancaster": ["los-angeles"], "ridgecrest": ["eastern-sierra"],
    # Florida
    "miami": ["miami", "broward"], "orlando": ["orlando-kissimmee"], "tampa": ["tampa", "st-petersburg-clearwater"],
    "jacksonville": ["jacksonville"], "fort-myers-naples": ["fort-myers"], "sarasota": ["sarasota-bradenton"],
    "daytona-beach": ["daytona-space-coast"], "palm-bay": ["daytona-space-coast"], "titusville": ["daytona-space-coast"],
    "key-west": ["florida-keys"], "tallahassee": ["tallahassee"], "gainesville": ["gainesville-ocala"],
    "ocala": ["gainesville-ocala"], "fort-pierce": ["vero-beach-port-st-lucie"], "pensacola": ["northwest-florida"],
    "crestview": ["northwest-florida"], "panama-city": ["northwest-florida"],
    # Carolinas
    "charlotte": ["charlotte-metropolitan", "charlotte-suburban"], "raleigh-durham": ["raleigh-durham-chapel-hill"],
    "greensboro": ["greensboro-high-point", "winston-salem"], "asheville": ["asheville", "western-north-carolina"],
    "wilmington-nc": ["wilmington-cape-fear"], "outer-banks": ["outer-banks"], "hickory": ["hickory-lenoir-morganton"],
    "jacksonville-nc": ["jacksonville-nc"], "greenville": ["northeast-north-carolina"],
    "rocky-mount": ["northeast-north-carolina"], "goldsboro": ["southeast-north-carolina"],
    "new-bern": ["southeast-north-carolina"],
    "charleston": ["charleston", "north-charleston-summerville", "lowcountry"], "greenville-sc": ["greenville", "upstate"],
    "columbia-sc": ["columbia"], "florence-sc": ["florence", "pee-dee"],
    # Washington
    "seattle": ["seattle", "tacoma", "north-puget-sound"], "spokane": ["spokane", "northeast-washington"],
    "bellingham": ["northwest-washington"], "kennewick": ["southeast-washington"], "yakima": ["wine-country"],
    "walla-walla": ["walla-walla"], "tumwater": ["olympia-south-puget-sound"],
    "longview-wa": ["southwest-washington", "vancouver"], "pullman": ["southeast-washington"],
    "wenatchee": ["north-central-washington"], "moses-lake": ["north-central-washington"],
    # Utah
    "salt-lake-city": ["salt-lake-city", "ogden-clearfield", "provo-orem", "park-city-ski-areas"],
    "st-george": ["st-george", "southwest-utah"], "logan": ["logan"], "cedar-city": ["southwest-utah"],
    # New York / New Jersey
    "new-york-city": ["new-york-ny", "brooklyn", "queens", "manhattan", "staten-island", "bronx", "north-new-jersey-nj"],
    "hamptons": ["hamptons-ny", "long-island-ny"], "hudson-valley": ["hudson-valley-ny", "westchester-county-ny"],
    "albany": ["albany-ny"], "buffalo": ["western-new-york-ny"], "rochester": ["rochester-ny"], "syracuse": ["syracuse-ny"],
    "ithaca": ["ithaca-binghamton"], "binghamton": ["ithaca-binghamton"], "elmira": ["ithaca-binghamton"],
    "utica": ["syracuse-ny"], "jamestown": ["western-new-york-ny"],
    "trenton": ["central-new-jersey"], "plainfield": ["central-new-jersey"], "atlantic-city": ["jersey-shore"],
    "vineland": ["south-new-jersey-nj"],
    # New England
    "boston": ["boston", "middlesex", "north-shore-ma"], "cape-cod": ["cape-cod", "marthas-vineyard", "nantucket"],
    "springfield-ma": ["western-massachusetts"], "pittsfield": ["berkshires"], "taunton": ["southeast-massachusetts"],
    "providence": ["rhode-island"], "hartford-new-haven": ["hartford", "new-haven"], "norwalk": ["fairfield"],
    "manchester-nh": ["merrimack-valley", "lakes-region", "seacoast"], "burlington-vt": ["burlington"],
    "portland-maine": ["portland", "mid-coast-maine"], "bangor": ["bangor"],
    # Pennsylvania
    "philadelphia": ["philadelphia-metropolitan", "philadelphia-suburban", "south-new-jersey-nj"],
    "pittsburgh": ["pittsburgh-metropolitan", "pittsburgh-suburban"], "lehigh-valley": ["allentown-lehigh-valley"],
    "poconos": ["poconos"], "harrisburg": ["harrisburg-dutch-country"], "erie": ["great-lakes"],
    "state-college": ["central-pennsylvania"], "altoona": ["the-alleghenies"], "williamsport": ["susquehanna-valley"],
    # Mid-Atlantic
    "washington-dc": ["dc-metropolitan", "northern-virginia"], "baltimore": ["baltimore", "annapolis"],
    "salisbury": ["eastern-shore"], "hagerstown": ["western-maryland"], "dover": ["delaware", "wilmington-de"],
    "richmond": ["richmond-va"], "virginia-beach": ["hampton-roads"], "roanoke": ["roanoke"], "lynchburg": ["lynchburg"],
    "blacksburg": ["new-river-valley"], "harrisonburg": ["southern-shenandoah-valley"],
    "winchester": ["northern-shenandoah-valley"], "fredericksburg": ["northern-virginia"],
    "danville": ["south-central-virginia"], "charleston-wv": ["central-west-virginia", "southern-west-virginia"],
    "wheeling": ["northern-west-virginia"],
    # Oregon
    "portland": ["portland-metropolitan", "portland-suburban"], "eugene": ["willamette-valley"],
    "corvallis": ["willamette-valley"], "bend": ["central-oregon"], "medford": ["southern-oregon"],
    "grants-pass": ["southern-oregon"],
    # Minnesota
    "minneapolis": ["minneapolis", "st-paul", "twin-cities-metro"], "duluth": ["duluth", "duluth-superior"],
    "rochester-mn": ["rochester-mn", "southeast-minnesota"], "st-cloud": ["st-cloud"],
    "mankato": ["mankato", "north-mankato"], "austin-mn": ["southeast-minnesota"], "owatonna": ["southeast-minnesota"],
    "winona": ["southeast-minnesota"],
    # Ohio
    "columbus": ["columbus-metropolitan", "columbus-suburban"],
    "cincinnati": ["cincinnati-metropolitan", "cincinnati-greater-area", "northern-kentucky"],
    "cleveland": ["cleveland-metropolitan", "cleveland-suburban", "northeast-oh"], "dayton": ["dayton"],
    "toledo": ["toledo-port-clinton", "northwest-ohio"], "youngstown": ["youngstown-warren"], "canton": ["northeast-oh"],
    "mansfield": ["north-central-ohio"], "lima": ["northwest-ohio"], "wooster": ["northeast-oh"],
    # Louisiana
    "new-orleans": ["new-orleans-metropolitan", "new-orleans-suburban-north", "new-orleans-suburban-south"],
    "baton-rouge": ["baton-rouge", "lafayette"], "shreveport": ["shreveport"],
    "lake-charles": ["lake-charles-southwest-louisiana"], "monroe": ["monroe", "northeast-louisiana"],
    "alexandria": ["alexandria-central-louisiana"], "houma": ["houma"],
    # Indiana
    "indianapolis": ["indianapolis-metropolitan", "indianapolis-suburban"], "fort-wayne": ["fort-wayne"],
    "evansville": ["evansville"], "south-bend": ["south-bend-michiana"], "michigan-city": ["south-bend-michiana"],
    "bloomington": ["bloomington"], "lafayette": ["lafayette-west-lafayette"], "muncie": ["muncie-anderson"],
    "terre-haute": ["terre-haute"], "columbus-in": ["southeast-indiana"], "richmond-in": ["southeast-indiana"],
    "kokomo": ["indianapolis-suburban"], "marion": ["indianapolis-suburban"],
    # Michigan
    "detroit": ["detroit-metropolitan", "detroit-suburban", "ann-arbor"],
    "grand-rapids": ["grand-rapids", "western-michigan", "muskegon"], "lansing": ["lansing"], "flint": ["flint"],
    "saginaw": ["mid-michigan"], "jackson-mi": ["jackson-southern-michigan"], "port-huron": ["the-thumb"],
    # Wisconsin
    "milwaukee": ["milwaukee-metropolitan", "milwaukee-suburban"], "madison": ["madison"],
    "green-bay": ["green-bay", "northeast-wisconsin"], "appleton": ["appleton-oshkosh"],
    "eau-claire": ["eau-claire", "northwest-wisconsin"], "la-crosse": ["la-crosse"], "sheboygan": ["sheboygan"],
    "wausau": ["central-wisconsin"], "stevens-point": ["central-wisconsin"], "fond-du-lac": ["appleton-oshkosh"],
    "manitowoc": ["northeast-wisconsin"],
    # Kentucky
    "louisville": ["louisville"], "lexington": ["lexington"], "bowling-green": ["bowling-green"],
    "owensboro": ["owensboro-henderson"], "paducah": ["western-kentucky"],
    # Oklahoma
    "oklahoma-city": ["oklahoma-city-metropolitan", "eastern-oklahoma-city-suburban", "western-oklahoma-city-suburban", "norman"],
    "tulsa": ["tulsa-metropolitan", "tulsa-suburban"], "lawton": ["southwest-oklahoma"], "enid": ["north-central-oklahoma"],
    "muskogee": ["northeast-oklahoma"], "bartlesville": ["northeast-oklahoma"], "shawnee": ["eastern-oklahoma-city-suburban"],
    # Alabama
    "birmingham": ["birmingham"], "huntsville": ["huntsville"], "montgomery": ["montgomery-mideast-alabama"],
    "mobile": ["mobile-gulf-coast"], "auburn": ["auburn-columbus"], "dothan": ["dothan-southeast-alabama"],
    "enterprise": ["dothan-southeast-alabama"], "florence": ["florence-muscle-shoals"], "gadsden": ["talladega"],
    # Hawaii
    "honolulu": ["honolulu-oahu"], "maui": ["maui"],
    # New Mexico
    "albuquerque": ["albuquerque-metropolitan", "santa-fe-metropolitan", "santa-fe-suburban", "central-new-mexico"],
    "roswell": ["roswell-carlsbad"], "carlsbad": ["roswell-carlsbad"], "farmington": ["four-corners-region"],
    "alamogordo": ["las-cruces"], "hobbs": ["roswell-carlsbad"], "clovis": ["eastern-plains-nm"],
    # Nebraska
    "omaha": ["omaha-metropolitan", "omaha-suburban", "lincoln", "council-bluffs"],
    "grand-island": ["grand-island", "south-central-nebraska"], "kearney": ["south-central-nebraska"],
    "norfolk": ["norfolk", "northeast-nebraska"],
    # Idaho
    "boise": ["boise", "treasure-valley", "nampa"], "idaho-falls": ["idaho-falls-blackfoot"], "rexburg": ["rexburg"],
    "pocatello": ["pocatello-southeast-idaho"], "coeur-d-alene": ["coeur-d-alene-idaho-panhandle"],
    "twin-falls": ["magic-valley"], "lewiston": ["north-central-idaho"],
    # Iowa
    "des-moines": ["des-moines-metropolitan", "des-moines-suburban", "central-iowa"],
    "cedar-rapids": ["cedar-rapids", "iowa-city"], "sioux-city": ["sioux-city", "sioux-city-suburban-nebraska"],
    "waterloo": ["waterloo-cedar-falls"], "dubuque": ["dubuque"], "mason-city": ["northeast-iowa"],
    "ottumwa": ["southeast-iowa"], "marshalltown": ["central-iowa"],
    # Mississippi
    "jackson-ms": ["jackson-metropolitan", "jackson-suburban-east", "jackson-suburban-west"], "gulfport": ["gulf-coast"],
    "tupelo": ["tupelo-north-mississippi"], "meridian": ["meridian"], "oxford": ["tupelo-north-mississippi"],
    "starkville": ["golden-triangle-east-central-mississippi"], "greenville-ms": ["west-central-mississippi"],
    # Mountain / plains
    "billings": ["billings", "bozeman", "big-sky", "south-central-montana"], "great-falls": ["great-falls"],
    "butte-silver-bow": ["southwest-montana"], "fargo": ["fargo", "bismarck"], "minot": ["minot"],
    "williston": ["northwest-north-dakota"], "dickinson": ["southwest-north-dakota"],
    "sioux-falls": ["sioux-falls-metropolitan", "sioux-falls-suburban", "rapid-city"],
    "aberdeen": ["aberdeen-northeast-south-dakota"],
    "jackson-hole": ["jackson-hole", "northwest-wyoming"], "cheyenne": ["cheyenne"], "casper": ["casper"],
    "laramie": ["laramie"], "gillette": ["northeast-wyoming"],
    # Alaska
    "anchorage": ["anchorage", "mat-su", "kenai"], "fairbanks": ["fairbanks", "interior-alaska"],
    "juneau": ["juneau", "southeast-alaska"],
    # Arkansas
    "little-rock": ["little-rock-metropolitan", "little-rock-northern-suburban", "little-rock-southern-suburban", "hot-springs-malvern"],
    "fayetteville": ["fayetteville-northwest-arkansas"], "bella-vista": ["fayetteville-northwest-arkansas"],
    "fort-smith": ["fort-smith"], "jonesboro": ["jonesboro-northeast-arkansas"], "pine-bluff": ["southeast-arkansas"],
    "russellville": ["west-central-arkansas"],
    # Kansas
    "wichita": ["wichita", "south-central-kansas"], "topeka": ["topeka-metropolitan", "topeka-suburban"],
    "manhattan": ["manhattan-kansas"], "salina": ["salina"], "hutchinson": ["central-kansas"],
    "dodge-city": ["southwest-kansas"], "garden-city": ["southwest-kansas"], "gardner": ["kansas-city-greater-area"],
}


def state_for(m):
    k = m["key"]
    if k in STATE_OVERRIDES:
        return STATE_OVERRIDES[k]
    for lo, hi, st in STATE_BLOCKS:
        if lo <= m["id"] <= hi:
            return st
    raise SystemExit(f"no state block for {m['id']} {k} - extend STATE_BLOCKS")


def build(raw):
    lazo_ids = {m["id"] for m in METROS}
    zola_keys = {m["key"] for m in raw}
    bad = [(l, z) for l, zs in LAZO_TO_ZOLA.items() for z in zs if z not in zola_keys]
    if bad:
        raise SystemExit(f"unknown Zola keys in LAZO_TO_ZOLA: {bad}")
    bad = [l for l in LAZO_TO_ZOLA if l not in lazo_ids]
    if bad:
        raise SystemExit(f"unknown Lazo metros in LAZO_TO_ZOLA: {bad}")
    by_zola = {}
    for l, zs in LAZO_TO_ZOLA.items():
        for z in zs:
            by_zola.setdefault(z, []).append(l)
    out = []
    for m in sorted(raw, key=lambda x: x["id"]):
        st = state_for(m)
        out.append({
            "id": m["id"], "key": m["key"], "label": m["label"], "state": st,
            "stateName": STATE_NAMES[st], "level": m["marketLevel"],
            "parentKey": next((p["key"] for p in raw if p["id"] == m["parentId"]), None) if m.get("parentId") else None,
            "lazoMetros": sorted(by_zola.get(m["key"], [])),
        })
    out.sort(key=lambda x: (x["stateName"], x["label"]))
    return out


def main():
    if len(sys.argv) > 1:
        raw = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    else:
        req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
        raw = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))
    markets = build(raw)
    states = sorted({(m["state"], m["stateName"]) for m in markets}, key=lambda s: s[1])
    doc = {
        "source": URL, "fetched": "2026-10-19", "count": len(markets),
        "states": [{"code": c, "name": n, "count": sum(1 for m in markets if m["state"] == c)} for c, n in states],
        "markets": markets,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    # the worker's copy: which Zola markets put a vendor on a Lazo metro's pages
    by_metro = {}
    for m in markets:
        for l in m["lazoMetros"]:
            by_metro.setdefault(l, []).append(m["key"])
    js = ["// JC-LAZO-MARKETS-1019: generated by generate/zola_markets.py from generate/data/markets.json - do not edit.",
          "// Lazo metro id -> the Zola-style market keys that overlap it. A vendor whose homeMarkets or",
          "// travelMarkets holds one of them is shown on that metro's category lists and pages.",
          "export const METRO_MARKETS = {"]
    for l in sorted(by_metro):
        js.append(f'  "{l}": {json.dumps(sorted(by_metro[l]))},')
    js.append("};")
    js.append("export const MARKET_METROS = {")
    for m in markets:
        if m["lazoMetros"]:
            js.append(f'  {json.dumps(m["key"])}: {json.dumps(m["lazoMetros"])},')
    js.append("};")
    js.append("export const MARKET_LABELS = {")
    for m in markets:
        js.append(f'  {json.dumps(m["key"])}: {json.dumps(m["label"] + ", " + m["state"])},')
    js.append("};")
    WORKER_JS.write_text("\n".join(js) + "\n", encoding="utf-8")
    # the vendor app's copy: [state, key, label] rows, pasted in by app-patches/patch_vendor_v220.py
    dq = lambda t: t.replace("\\", "\\\\").replace("'", "\\'")
    dart = ["// JC-LAZO-MARKETS-1019: Zola's vendor markets (generate/data/markets.json) - [state, key, label].",
            "const List<List<String>> kLzMarkets = <List<String>>["]
    for m in markets:
        dart.append(f"  <String>['{m['state']}', '{dq(m['key'])}', '{dq(m['label'])}'],")
    dart.append("];")
    DART.parent.mkdir(parents=True, exist_ok=True)
    DART.write_text("\n".join(dart) + "\n", encoding="utf-8")
    mapped = sum(1 for m in markets if m["lazoMetros"])
    covered = {l for m in markets for l in m["lazoMetros"]}
    print(f"{len(markets)} markets, {len(states)} states, {mapped} map to a Lazo metro; "
          f"{len(covered)}/{len(METROS)} Lazo metros covered -> {OUT}")
    print("Lazo metros with no Zola market:", sorted({m['id'] for m in METROS} - covered))


if __name__ == "__main__":
    main()
