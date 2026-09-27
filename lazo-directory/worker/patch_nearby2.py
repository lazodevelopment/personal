"""patch_nearby2.py - JC-LAZO-WORKER-0915-NEARBY-002
First run against a real venue returned a hotel and a shopping mall under
"Eat & drink" and Walmart under "Coffee", because Google tags big places with
every type they contain, and because ranking by review count hands the list to
chains. Two fixes:
  1. judge a place by its PRIMARY type, and deny the categories no wedding
     guest means when they ask where to eat (hotels, malls, supermarkets).
  2. rank by rating, with review count worth at most +0.16 - enough to break a
     tie, not enough for a 4.4 with 7,000 reviews to beat a 4.8 with 300.
Also raises the credibility floor to 80 reviews, de-duplicates across groups,
and bumps the cache key to v2 so the first answers are recomputed.
"""
import shutil
from pathlib import Path

P = Path(__file__).resolve().parent / "src" / "index.js"
s = P.read_text(encoding="utf-8")
TAG = "JC-LAZO-WORKER-0915-NEARBY-002"
if TAG in s:
    raise SystemExit("[patch] already applied")
shutil.copy(P, P.with_name("index.js.bak-20260915-nearby2"))


def rep(old, new, cnt=1):
    global s
    n = s.count(old)
    assert n == cnt, (n, old[:70])
    s = s.replace(old, new)


rep("""// JC-LAZO-WORKER-0915-NEARBY-001: /api/nearby?slug= answers with things for guests""",
    f"""// {TAG}: places are judged by their primary type, so a
//   hotel with a restaurant inside is not "somewhere to eat", and ranked by
//   rating with review count worth at most +0.16, so the best local place beats
//   the busiest chain. Cache key bumped to v2.
// JC-LAZO-WORKER-0915-NEARBY-001: /api/nearby?slug= answers with things for guests""")

# the primary type is the one that decides
rep('''  "places.googleMapsUri", "places.primaryTypeDisplayName", "places.editorialSummary",''',
    '''  "places.googleMapsUri", "places.primaryType", "places.primaryTypeDisplayName",
  "places.editorialSummary",''')

rep("""function milesBetween(a, b) {""",
    """// What a place mainly IS. Google lists every type a place contains, so a resort
// is also a "restaurant" and a supermarket is also a "bakery"; only the primary
// type answers the question a guest is actually asking.
const NB_DENY = new Set(["lodging", "hotel", "motel", "resort_hotel", "extended_stay_hotel",
  "bed_and_breakfast", "inn", "guest_house", "shopping_mall", "department_store", "supermarket",
  "grocery_store", "convenience_store", "gas_station", "parking", "hospital", "pharmacy",
  "school", "bank", "atm", "store", "gym", "hair_salon", "car_dealer", "real_estate_agency",
  "wholesaler", "home_improvement_store", "airport", "transit_station"]);
const NB_EAT = new Set(["restaurant", "bar", "wine_bar", "pub", "brewery", "bar_and_grill",
  "steak_house", "fine_dining_restaurant", "diner", "deli", "delicatessen"]);
// these are breakfast, not dinner - they belong in the coffee group
const NB_NOT_EAT = new Set(["breakfast_restaurant", "brunch_restaurant", "coffee_shop", "cafe",
  "bakery", "donut_shop", "bagel_shop", "ice_cream_shop", "fast_food_restaurant",
  "hamburger_restaurant", "meal_takeaway", "meal_delivery"]);
const NB_COFFEE = new Set(["cafe", "coffee_shop", "bakery", "breakfast_restaurant",
  "brunch_restaurant", "tea_house", "donut_shop", "bagel_shop"]);
const NB_DO = new Set(["tourist_attraction", "museum", "art_gallery", "park", "national_park",
  "state_park", "hiking_area", "historical_landmark", "historical_place", "cultural_landmark",
  "monument", "performing_arts_theater", "zoo", "aquarium", "botanical_garden", "garden",
  "observation_deck", "planetarium", "wildlife_park", "amusement_park", "water_park",
  "winery", "distillery", "beach"]);

function nbFits(groupKey, t) {
  if (!t || NB_DENY.has(t)) return false;
  if (groupKey === "eat") return (NB_EAT.has(t) || /_restaurant$/.test(t)) && !NB_NOT_EAT.has(t);
  if (groupKey === "coffee") return NB_COFFEE.has(t);
  return NB_DO.has(t);
}

// Rating first. Review count is credibility, not a popularity contest: it is
// worth at most +0.16, so it breaks ties and nothing more.
function nbScore(p) {
  return p.rating + Math.min(Math.log10(Math.max(p.votes, 1)), 4) * 0.04;
}

function milesBetween(a, b) {""")

rep("""  return {
    name: (p.displayName && p.displayName.text) || "",
    kind: (p.primaryTypeDisplayName && p.primaryTypeDisplayName.text) || "",""",
    """  return {
    id: p.id || "",
    type: p.primaryType || "",
    name: (p.displayName && p.displayName.text) || "",
    kind: (p.primaryTypeDisplayName && p.primaryTypeDisplayName.text) || "",""")

rep("""async function nearbyBuild(at, key) {
  const groups = [];
  for (const g of NEARBY_GROUPS) {""",
    """async function nearbyBuild(at, key) {
  const groups = [];
  const seen = new Set();            // no place appears in two groups
  for (const g of NEARBY_GROUPS) {""")

rep("""    const items = raw
      .map((p) => shapePlace(p, at))
      .filter((p) => p.name && p.rating >= 4.1 && p.votes >= 40)
      // well-liked first, but a lot of people must have liked it
      .sort((a, b) => (b.rating * Math.log10(b.votes + 10)) - (a.rating * Math.log10(a.votes + 10)))
      .slice(0, g.take);""",
    """    const items = raw
      .map((p) => shapePlace(p, at))
      .filter((p) => p.name && p.rating >= 4.2 && p.votes >= 80 && nbFits(g.key, p.type))
      .filter((p) => (p.id && seen.has(p.id) ? false : (seen.add(p.id), true)))
      .sort((a, b) => nbScore(b) - nbScore(a))
      .slice(0, g.take);
    for (const p of items) { delete p.id; delete p.type; }""")

rep("""  const cacheKey = `nearby/v1/${at.lat.toFixed(3)}_${at.lng.toFixed(3)}.json`;""",
    """  const cacheKey = `nearby/v2/${at.lat.toFixed(3)}_${at.lng.toFixed(3)}.json`;""")

P.write_text(s, encoding="utf-8", newline="\n")
print(f"worker patched ({len(s):,} bytes)")
