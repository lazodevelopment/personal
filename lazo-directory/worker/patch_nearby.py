"""patch_nearby.py - JC-LAZO-WORKER-0915-NEARBY-001
Adds /api/nearby to the site worker: things for wedding guests to do around a
couple's venue, from Google Places, cached in R2 for under Google's 30-day
limit and attributed on the page. Idempotent.
"""
import shutil
from pathlib import Path

P = Path(__file__).resolve().parent / "src" / "index.js"
s = P.read_text(encoding="utf-8")
TAG = "JC-LAZO-WORKER-0915-NEARBY-001"
if TAG in s:
    raise SystemExit("[patch] already applied")
shutil.copy(P, P.with_name("index.js.bak-20260915-nearby"))


def rep(old, new, cnt=1):
    global s
    n = s.count(old)
    assert n == cnt, (n, old[:70])
    s = s.replace(old, new)


# ---- header note ----
rep("""// JC-LAZO-WORKER-0915-THEMES-001:""", f"""// {TAG}: /api/nearby?slug= answers with things for guests
//   to do around the couple's venue - eat & drink, coffee, things to do - from
//   Google Places, ranked by rating and review count, with the distance from the
//   venue. The venue is geocoded once; the answer is cached in R2 under
//   nearby/v1/ for 25 days (inside Google's 30-day caching limit) and keyed by
//   rounded coordinates, so couples at the same venue share one lookup. Needs the
//   PLACES_API_KEY secret; without it the endpoint answers empty and the section
//   never appears. deploy_site.py excludes nearby/** from --prune.
// JC-LAZO-WORKER-0915-THEMES-001:""")

# ---- payload: the couple's own picks ride along ----
rep("""    song: await siteSong(g("song")),
  };
""", """    song: await siteSong(g("song")),
    nearbyOn: g("nearbyOn") !== false,
    nearbyNote: g("nearbyNote") || "",
    nearbyPicks: g("nearbyPicks") || [],
  };
""")

# ---- route ----
rep("""    if (url.pathname === "/music/search") return musicSearch(url);""",
    """    if (url.pathname === "/music/search") return musicSearch(url);
    if (url.pathname === "/api/nearby") return nearbyPlaces(url, env);""")

# ---- implementation, next to the music helpers ----
rep("""// JC-LAZO-WORKER-0912-MUSIC-002: song search for the couple app's Music page.""",
    f"""// {TAG}: things to do around the venue.
// Three groups a wedding guest actually needs, in the order they need them.
const NEARBY_GROUPS = [
  {{ key: "eat", label: "Eat & drink", types: ["restaurant"], take: 6, radius: 8000 }},
  {{ key: "coffee", label: "Coffee & breakfast", types: ["cafe", "bakery", "breakfast_restaurant"], take: 4, radius: 6000 }},
  {{ key: "do", label: "Things to do", types: ["tourist_attraction", "museum", "park", "art_gallery", "hiking_area"], take: 6, radius: 16000 }},
];
const NEARBY_TTL = 25 * 24 * 3600 * 1000;   // Google allows 30 days; stay under it
const NEARBY_MASK = [
  "places.id", "places.displayName", "places.formattedAddress", "places.location",
  "places.rating", "places.userRatingCount", "places.priceLevel",
  "places.googleMapsUri", "places.primaryTypeDisplayName", "places.editorialSummary",
].join(",");

function milesBetween(a, b) {{
  const R = 3958.8, rad = (d) => d * Math.PI / 180;
  const dLat = rad(b.lat - a.lat), dLng = rad(b.lng - a.lng);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.min(1, Math.sqrt(h)));
}}

async function placesPost(path, body, key, mask) {{
  const r = await fetch("https://places.googleapis.com/v1/places:" + path, {{
    method: "POST",
    headers: {{ "content-type": "application/json", "X-Goog-Api-Key": key, "X-Goog-FieldMask": mask }},
    body: JSON.stringify(body),
  }});
  if (!r.ok) return null;
  return r.json();
}}

// The venue, as a point. One text search, and only when we have no cache.
async function venuePoint(name, address, key) {{
  const q = [name, address].filter(Boolean).join(", ").trim();
  if (q.length < 6) return null;
  const j = await placesPost("searchText", {{ textQuery: q, pageSize: 1 }}, key,
    "places.location,places.formattedAddress");
  const p = j && j.places && j.places[0];
  if (!p || !p.location) return null;
  return {{ lat: p.location.latitude, lng: p.location.longitude }};
}}

function shapePlace(p, at) {{
  const loc = p.location ? {{ lat: p.location.latitude, lng: p.location.longitude }} : null;
  const PRICE = {{ PRICE_LEVEL_INEXPENSIVE: "$", PRICE_LEVEL_MODERATE: "$$",
                  PRICE_LEVEL_EXPENSIVE: "$$$", PRICE_LEVEL_VERY_EXPENSIVE: "$$$$" }};
  return {{
    name: (p.displayName && p.displayName.text) || "",
    kind: (p.primaryTypeDisplayName && p.primaryTypeDisplayName.text) || "",
    blurb: (p.editorialSummary && p.editorialSummary.text) || "",
    rating: p.rating || 0,
    votes: p.userRatingCount || 0,
    price: PRICE[p.priceLevel] || "",
    miles: loc && at ? Math.round(milesBetween(at, loc) * 10) / 10 : null,
    maps: p.googleMapsUri || "",
  }};
}}

async function nearbyBuild(at, key) {{
  const groups = [];
  for (const g of NEARBY_GROUPS) {{
    const j = await placesPost("searchNearby", {{
      includedTypes: g.types,
      maxResultCount: 20,
      rankPreference: "POPULARITY",
      locationRestriction: {{ circle: {{ center: {{ latitude: at.lat, longitude: at.lng }}, radius: g.radius }} }},
    }}, key, NEARBY_MASK);
    const raw = (j && j.places) || [];
    const items = raw
      .map((p) => shapePlace(p, at))
      .filter((p) => p.name && p.rating >= 4.1 && p.votes >= 40)
      // well-liked first, but a lot of people must have liked it
      .sort((a, b) => (b.rating * Math.log10(b.votes + 10)) - (a.rating * Math.log10(a.votes + 10)))
      .slice(0, g.take);
    if (items.length) groups.push({{ key: g.key, label: g.label, items }});
  }}
  return groups;
}}

const NEARBY_DEMO = [
  {{ key: "eat", label: "Eat & drink", items: [
    {{ name: "The Harbor Table", kind: "Seafood", blurb: "Oysters and a long wine list, two streets back from the water.", rating: 4.7, votes: 1240, price: "$$$", miles: 1.2, maps: "" }},
    {{ name: "Casa Verde", kind: "Mexican", blurb: "", rating: 4.6, votes: 860, price: "$$", miles: 2.1, maps: "" }},
    {{ name: "Bar Lucia", kind: "Wine bar", blurb: "", rating: 4.5, votes: 410, price: "$$", miles: 0.8, maps: "" }},
  ] }},
  {{ key: "coffee", label: "Coffee & breakfast", items: [
    {{ name: "Morning Glory Coffee", kind: "Coffee shop", blurb: "", rating: 4.8, votes: 930, price: "$", miles: 0.6, maps: "" }},
    {{ name: "The Flour Room", kind: "Bakery", blurb: "", rating: 4.7, votes: 520, price: "$", miles: 1.4, maps: "" }},
  ] }},
  {{ key: "do", label: "Things to do", items: [
    {{ name: "Old Town Walk", kind: "Historic district", blurb: "An hour on foot, best before the heat.", rating: 4.6, votes: 2100, price: "", miles: 1.9, maps: "" }},
    {{ name: "Ridgeline Trail", kind: "Hiking area", blurb: "", rating: 4.8, votes: 640, price: "", miles: 5.3, maps: "" }},
    {{ name: "The Shelby Museum", kind: "Art museum", blurb: "", rating: 4.5, votes: 380, price: "", miles: 2.7, maps: "" }},
  ] }},
];

async function nearbyPlaces(url, env) {{
  const h = {{ "content-type": "application/json; charset=utf-8", ...CORS,
              "cache-control": "public, max-age=3600, s-maxage=86400" }};
  const slug = (url.searchParams.get("slug") || "").trim().slice(0, 80);
  if (slug === "demo") return new Response(JSON.stringify({{ groups: NEARBY_DEMO, demo: true }}), {{ headers: h }});
  if (!/^[a-z0-9-]{{1,80}}$/.test(slug)) return new Response('{{"groups":[]}}', {{ headers: h }});

  const f = await fsDoc("weddingSites", slug);
  if (!f) return new Response('{{"groups":[]}}', {{ headers: h }});
  const g = (k) => fsVal(f[k]);
  if (g("nearbyOn") === false) return new Response('{{"groups":[]}}', {{ headers: h }});
  const address = (g("venueAddress") || "").toString();
  const vname = (g("venueName") || "").toString();
  if (!address && !vname) return new Response('{{"groups":[]}}', {{ headers: h }});

  const key = env.PLACES_API_KEY;
  if (!key) return new Response('{{"groups":[]}}', {{ headers: h }});

  // The venue point, remembered per site so we geocode an address once.
  const ptKey = "nearby/v1/pt/" + slug + ".json";
  let at = null, ptFresh = false;
  try {{
    const o = await env.SITE.get(ptKey);
    if (o) {{
      const j = await o.json();
      if (j && j.q === address + "|" + vname && j.lat) {{ at = {{ lat: j.lat, lng: j.lng }}; ptFresh = true; }}
    }}
  }} catch (e) {{}}
  if (!at) {{
    at = await venuePoint(vname, address, key);
    if (!at) return new Response('{{"groups":[]}}', {{ headers: h }});
  }}
  if (!ptFresh) {{
    try {{
      await env.SITE.put(ptKey, JSON.stringify({{ q: address + "|" + vname, lat: at.lat, lng: at.lng }}),
        {{ httpMetadata: {{ contentType: "application/json" }} }});
    }} catch (e) {{}}
  }}

  // Couples at the same venue share one lookup: ~110m of rounding.
  const cacheKey = `nearby/v1/${{at.lat.toFixed(3)}}_${{at.lng.toFixed(3)}}.json`;
  let groups = null;
  try {{
    const o = await env.SITE.get(cacheKey);
    if (o) {{
      const j = await o.json();
      if (j && Array.isArray(j.groups) && Date.now() - (j.at || 0) < NEARBY_TTL) groups = j.groups;
    }}
  }} catch (e) {{}}
  if (!groups) {{
    groups = await nearbyBuild(at, key);
    try {{
      await env.SITE.put(cacheKey, JSON.stringify({{ at: Date.now(), groups }}),
        {{ httpMetadata: {{ contentType: "application/json" }} }});
    }} catch (e) {{}}
  }}
  return new Response(JSON.stringify({{ groups }}), {{ headers: h }});
}}

// JC-LAZO-WORKER-0912-MUSIC-002: song search for the couple app's Music page.""")

P.write_text(s, encoding="utf-8", newline="\n")
print(f"worker patched ({len(s):,} bytes)")

# deploy prune must never delete the nearby cache
d = Path(__file__).resolve().parents[1] / "deploy" / "deploy_site.py"
t = d.read_text(encoding="utf-8")
old = '"seating/**", "showcase/**")'
assert t.count(old) == 1
t = t.replace(old, '"seating/**", "showcase/**", "nearby/**")')
d.write_text(t, encoding="utf-8", newline="\n")
print("deploy_site.py: nearby/** excluded from prune")
