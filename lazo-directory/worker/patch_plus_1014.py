r"""patch_plus_1014.py - JC-LAZO-WORKER-1014-PLUS
The couple's site gets: the wedding party, hotel cards, airports and driving
notes, a hashtag, and the story told in dated milestones. Plus /api/stay?slug=
which answers with hotels and airports near the venue (Google Places, cached),
for June's site draft and for sites whose couple has not listed a hotel yet.
Idempotent: re-running finds its own tag and stops.
"""
from pathlib import Path

P = Path(__file__).resolve().parent / "src" / "index.js"
s = P.read_text(encoding="utf-8")
TAG = "JC-LAZO-WORKER-1014-PLUS"
if TAG in s:
    raise SystemExit("already patched")


def rep(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"anchor found {n}x (want {count}): {old[:70]!r}")
    s = s.replace(old, new)


# 1. payload fields
rep('''    guestPhotosHold: g("guestPhotosHold") === true,
  };
''', '''    guestPhotosHold: g("guestPhotosHold") === true,
    // JC-LAZO-WORKER-1014-PLUS-001: the wedding party, where to stay, getting
    // there, the hashtag, and the story told in dates
    ...plusFields(g),
  };
''')

# 2. route
rep('''    if (url.pathname === "/api/nearby") return nearbyPlaces(url, env);
''', '''    if (url.pathname === "/api/nearby") return nearbyPlaces(url, env);
    if (url.pathname === "/api/stay") return stayPlaces(url, env);   // JC-LAZO-WORKER-1014-PLUS
''')

# 3. helpers, after photoSlot
rep('''// JC-LAZO-WORKER-0930-SITEFIX: the passcode gate lives here, not in the page (helpers in fsauth.js).
''', r'''// JC-LAZO-WORKER-1014-PLUS-001: everything the couple adds beyond the basics.
// Each list is capped and every string trimmed; a link must be https.
function plusFields(g) {
  const str = (v, n) => String(v == null ? "" : v).trim().slice(0, n);
  const link = (v) => /^https:\/\//.test(String(v || "")) ? String(v).slice(0, 600) : "";
  const list = (k, n) => (Array.isArray(g(k)) ? g(k) : []).filter(x => x && typeof x === "object").slice(0, n);
  const tag = str(g("hashtag"), 60).replace(/^#+/, "").replace(/[^A-Za-z0-9_]/g, "");
  const sides = (Array.isArray(g("partySides")) ? g("partySides") : []).map(x => str(x, 40)).slice(0, 2);
  return {
    weddingParty: list("weddingParty", 40).filter(p => str(p.name, 80)).map(p => ({
      name: str(p.name, 80), role: str(p.role, 60),
      side: p.side === "a" || p.side === "b" ? p.side : "",
      photo: link(p.photo), note: str(p.note, 300) })),
    partySides: sides,
    hotels: list("hotels", 8).filter(h => str(h.name, 100)).map(h => ({
      name: str(h.name, 100), address: str(h.address, 200), url: link(h.url),
      code: str(h.code, 60), deadline: str(h.deadline, 40), rate: str(h.rate, 60),
      phone: str(h.phone, 30), note: str(h.note, 300), block: h.block !== false })),
    airports: list("airports", 4).filter(a => str(a.name, 100)).map(a => ({
      code: str(a.code, 4).toUpperCase().replace(/[^A-Z]/g, ""), name: str(a.name, 100),
      miles: typeof a.miles === "number" && isFinite(a.miles) ? Math.round(a.miles) : null,
      note: str(a.note, 240) })),
    drivingNotes: str(g("drivingNotes"), 1200),
    hashtag: tag.length >= 2 ? tag : "",
    milestones: list("milestones", 16).filter(m => str(m.title, 100)).map(m => ({
      when: str(m.when, 40), title: str(m.title, 100), text: str(m.text, 600), photo: link(m.photo) })),
    stayAuto: g("stayAuto") !== false,
    // the section headlines in the couple's words (June drafts them); the
    // page falls back to neutral lines, never the template's sample venue
    headlines: (() => { const h = g("headlines"); const o = {};
      if (h && typeof h === "object") for (const k of ["story", "day", "rsvp", "thanks", "party", "stay", "gallery", "eyebrow", "countdown"])
        if (h[k]) o[k] = str(h[k], 140);
      return o; })(),
  };
}

// JC-LAZO-WORKER-0930-SITEFIX: the passcode gate lives here, not in the page (helpers in fsauth.js).
''')

# 4. /api/stay, after nearbyPlaces
rep('''  return new Response(JSON.stringify({ groups }), { headers: h });
}
''', r'''  return new Response(JSON.stringify({ groups }), { headers: h });
}

// JC-LAZO-WORKER-1014-PLUS-002: where guests sleep and where they land.
// Hotels within ~10 miles that guests actually rate; the big airports within
// ~120 miles with a rough drive time (miles by road run ~1.25x the crow's).
const STAY_TTL = 25 * 24 * 3600 * 1000;
const STAY_MASK = [
  "places.displayName", "places.formattedAddress", "places.location", "places.rating",
  "places.userRatingCount", "places.priceLevel", "places.googleMapsUri", "places.primaryType",
  "places.primaryTypeDisplayName", "places.websiteUri",
].join(",");
const STAY_TYPES = new Set(["hotel", "resort_hotel", "inn", "bed_and_breakfast", "lodging",
  "extended_stay_hotel", "motel", "guest_house", "cottage", "farmstay"]);
const STAY_DEMO = {
  hotels: [
    { name: "The Dewberry", kind: "Hotel", address: "334 Meeting St, Charleston, SC", rating: 4.7, votes: 1650, price: "$$$$", miles: 1.4, maps: "", url: "" },
    { name: "Harbourview Inn", kind: "Inn", address: "2 Vendue Range, Charleston, SC", rating: 4.6, votes: 1210, price: "$$$", miles: 2.0, maps: "", url: "" },
    { name: "The Spectator", kind: "Boutique hotel", address: "67 State St, Charleston, SC", rating: 4.8, votes: 820, price: "$$$", miles: 2.2, maps: "", url: "" },
  ],
  airports: [
    { code: "CHS", name: "Charleston International Airport", miles: 12, drive: 25, maps: "" },
    { code: "SAV", name: "Savannah/Hilton Head International Airport", miles: 98, drive: 120, maps: "" },
  ],
};

function airportCode(name) {
  const m = /\(([A-Z]{3})\)/.exec(name || "");
  return m ? m[1] : "";
}

const stayWhy = [];   // recent Places failures, for the logs
async function stayPost(path, body, key) {
  const r = await fetch("https://places.googleapis.com/v1/places:" + path, {
    method: "POST",
    headers: { "content-type": "application/json", "X-Goog-Api-Key": key, "X-Goog-FieldMask": STAY_MASK },
    body: JSON.stringify(body),
  });
  if (!r.ok) { const t = path + " " + r.status + " " + (await r.text()).slice(0, 200); stayWhy.push(t); if (stayWhy.length > 20) stayWhy.shift(); console.log("stay:", t); return null; }
  return r.json();
}

async function stayBuild(at, key) {
  const circle = (r) => ({ circle: { center: { latitude: at.lat, longitude: at.lng }, radius: r } });
  const hj = await stayPost("searchNearby", {
    includedTypes: ["hotel", "resort_hotel", "inn", "bed_and_breakfast", "lodging"],
    maxResultCount: 20, rankPreference: "POPULARITY", locationRestriction: circle(16000),
  }, key);
  const seen = new Set();
  const hotels = ((hj && hj.places) || []).map((p) => {
    const o = shapePlace(p, at);
    o.address = p.formattedAddress || "";
    o.url = p.websiteUri || "";
    return o;
  }).filter((p) => p.name && STAY_TYPES.has(p.type) && p.rating >= 3.9 && p.votes >= 60)
    .filter((p) => { const k = nbName(p.name); if (seen.has(k)) return false; seen.add(k); return true; })
    // a guest wants good AND close: every 3 miles costs a tenth of a star
    .sort((a, b) => (nbScore(b) - (b.miles || 0) / 30) - (nbScore(a) - (a.miles || 0) / 30))
    .slice(0, 6)
    .map((p) => { delete p.id; delete p.type; delete p.blurb; return p; });

  const aj = await stayPost("searchText", {
    textQuery: "international airport", pageSize: 10, includedType: "airport",
    locationBias: circle(50000),
  }, key);
  const airports = ((aj && aj.places) || []).map((p) => shapePlace(p, at))
    .filter((p) => p.name && p.miles !== null && p.miles <= 120 && /airport/i.test(p.name)
      && !/\b(heliport|air ?park|airfield|executive|municipal|county)\b/i.test(p.name)
      && p.votes >= 300)
    .sort((a, b) => a.miles - b.miles)
    .slice(0, 3)
    .map((p) => ({ code: airportCode(p.name), name: p.name.replace(/\s*\([A-Z]{3}\)\s*/, " ").trim(),
      miles: Math.round(p.miles), drive: Math.max(10, Math.round(p.miles * 1.25 / 50 * 60 / 5) * 5), maps: p.maps }));
  return { hotels, airports };
}

async function stayPlaces(url, env) {
  const h = { "content-type": "application/json; charset=utf-8", ...CORS,
              "cache-control": "public, max-age=3600, s-maxage=86400" };
  const none = '{"hotels":[],"airports":[]}';
  const slug = (url.searchParams.get("slug") || "").trim().slice(0, 80);
  if (slug === "demo") return new Response(JSON.stringify({ ...STAY_DEMO, demo: true }), { headers: h });
  if (!/^[a-z0-9-]{1,80}$/.test(slug)) return new Response(none, { headers: h });
  const f = await fsDoc("weddingSites", slug);
  if (!f) return new Response(none, { headers: h });
  const g = (k) => fsVal(f[k]);
  const address = (g("venueAddress") || "").toString();
  const vname = (g("venueName") || "").toString();
  if (!address && !vname) return new Response(none, { headers: h });
  const key = env.PLACES_API_KEY;
  if (!key) return new Response(none, { headers: h });

  // the venue point is shared with /api/nearby
  const ptKey = "nearby/v1/pt/" + slug + ".json";
  let at = null;
  try {
    const o = await env.SITE.get(ptKey);
    if (o) { const j = await o.json(); if (j && j.q === address + "|" + vname && j.lat) at = { lat: j.lat, lng: j.lng }; }
  } catch (e) {}
  if (!at) {
    at = await venuePoint(vname, address, key);
    if (!at) return new Response(none, { headers: h });
    try {
      await env.SITE.put(ptKey, JSON.stringify({ q: address + "|" + vname, lat: at.lat, lng: at.lng }),
        { httpMetadata: { contentType: "application/json" } });
    } catch (e) {}
  }
  const cacheKey = `stay/v1/${at.lat.toFixed(3)}_${at.lng.toFixed(3)}.json`;
  let out = null;
  try {
    const o = await env.SITE.get(cacheKey);
    if (o) { const j = await o.json(); if (j && Array.isArray(j.hotels) && Date.now() - (j.at || 0) < ((j.hotels.length || (j.airports || []).length) ? STAY_TTL : 864e5)) out = { hotels: j.hotels, airports: j.airports || [] }; }
  } catch (e) {}
  if (!out) {
    const errs = stayWhy.length;
    out = await stayBuild(at, key);
    // an empty answer is kept a day (a rural venue); a failed lookup is not kept
    if (stayWhy.length === errs) try {
      await env.SITE.put(cacheKey, JSON.stringify({ at: Date.now(), ...out }),
        { httpMetadata: { contentType: "application/json" } });
    } catch (e) {}
  }
  return new Response(JSON.stringify(out), { headers: h });
}
''')

P.write_text(s, encoding="utf-8", newline="\n")
print("patched", P)
