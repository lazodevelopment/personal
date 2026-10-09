// Lazo static site worker — serves the generated directory from R2,
// and renders live couple wedding sites at /w/{slug} by hydrating the
// couple's chosen template with their weddingSites doc. (v3)
// JC-LAZO-WORKER-0929-GUESTPHOTOS-001: guests' photos from the day (guestphotos.js:
//   POST/GET /api/w/{slug}/photos, GET /w/{slug}/photo/{id}.jpg, lazo-galleries
//   bucket under guest/{slug}/). The payload gains heroPhoto / storyPhoto /
//   coverFocus / siteGalleryFocus ({url, x, y, zoom}) and guestPhotosOn / Note;
//   the share image prefers heroPhoto.
// JC-LAZO-WORKER-0915-NEARBY-003: one branch per business (the closest), at most
//   two of any one type per group, and a penalty for places Google itself
//   describes as a chain. Cache key bumped to v3.
// JC-LAZO-WORKER-0915-NEARBY-002: places are judged by their primary type, so a
//   hotel with a restaurant inside is not "somewhere to eat", and ranked by
//   rating with review count worth at most +0.16, so the best local place beats
//   the busiest chain. Cache key bumped to v2.
// JC-LAZO-WORKER-0915-NEARBY-001: /api/nearby?slug= answers with things for guests
//   to do around the couple's venue - eat & drink, coffee, things to do - from
//   Google Places, ranked by rating and review count, with the distance from the
//   venue. The venue is geocoded once; the answer is cached in R2 under
//   nearby/v1/ for 25 days (inside Google's 30-day caching limit) and keyed by
//   rounded coordinates, so couples at the same venue share one lookup. Needs the
//   PLACES_API_KEY secret; without it the endpoint answers empty and the section
//   never appears. deploy_site.py excludes nearby/** from --prune.
// JC-LAZO-WORKER-0915-THEMES-001: five themed templates (shore, summit, ranch,
//   starlit, frost) and the couple's song. weddingSites.song {title, artist,
//   art, trackId, preview, autoplay} rides into the payload as `song`; a Deezer
//   track id (dz…) is refreshed to a live preview URL at render time (their
//   preview links expire) and every clip is served through /music/preview so
//   it carries CORS and edge caching. No song, no player.
// JC-LAZO-GALLERY-0912-006: passcode compared as sha256 (doc is world-readable).
// JC-LAZO-GALLERY-0911-005: post-wedding client delivery galleries (Pro Studio).
//   + /g/{slug}           couple-facing gallery, hydrated from galleries/{slug}
//                         + R2 manifest; always noindex; optional passcode
//   + /api/gallery-auth   passcode → HMAC cookie (so image GETs aren't re-checked)
//   + /g/{slug}/i/{id}/{variant}  thumb|web|full bytes from the lazo-galleries bucket
//   + /p/{exp}/{sig}/{slug}/{id}.jpg  expiring signed URL for WHCC's AssetPath
//                         (WHCC fetches server-side and cannot carry a cookie)
//   Needs: R2 binding GALLERIES → lazo-galleries, secret GALLERY_SECRET.
// JC-LAZO-WORKER-0908-004: /icon/<host> relays a store's favicon (via Google's endpoint) with
//   CORS + a week of cache, so the Flutter app can show registry store icons.
// JC-LAZO-WORKER-0907-003:
//   + share previews for couple sites: <title>, og:title/description/image,
//     twitter:card injected server-side so iMessage/WhatsApp/Facebook show the
//     couple's names, date, venue and photo (never the photo of a passcode site)
//   + registryNote, rsvpBy and vendorTeam passed to the templates (v2 reads them)
//   + the home page follows the visitor: geo.js picks the nearest metro from
//     request.cf and injects window.LAZO_GEO (home template JC-LAZO-HOME-0907-005)
import { withGeo, withRegion } from "./geo.js";
// JC-LAZO-TRACK-0916-001: first-party visitor analytics, injected at the edge
// so the built site never has to be rebuilt to change it.
import { geoResponse, trackerResponse, withTracker } from "./track.js";
// JC-LAZO-PRINTS-0920-001: the print store (WHCC editor + Stripe)
import { printsRoute } from "./prints.js";
// JC-LAZO-WORKER-0929-GUESTPHOTOS-001: guests' photos from the day, into the
// lazo-galleries bucket; couple's positioned photos (heroPhoto / storyPhoto /
// siteGalleryFocus) ride into the payload below.
import { guestPhotosRoute } from "./guestphotos.js";
// JC-LAZO-WORKER-0929-LIVE-001: weather, translation, table cards, the DJ page
import { weatherRoute, translateRoute, cardsPage, playlistPage, dayBeforeRoute } from "./sitefeatures.js";
// JC-LAZO-WORKER-0930-FSAUTH
import { setWorkerEnv, fsHeaders, workerToken, pcToken, cookieVal, siteLocked, lockedResponse } from "./fsauth.js";

const CORS = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "GET, POST, OPTIONS",
  "access-control-allow-headers": "content-type",
};

const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), { status,
    headers: { "content-type": "application/json", "cache-control": "no-store", ...CORS } });

const TYPES = { html:"text/html;charset=utf-8", css:"text/css", js:"text/javascript",
  svg:"image/svg+xml", xml:"application/xml", txt:"text/plain", png:"image/png",
  jpg:"image/jpeg", webp:"image/webp", ico:"image/x-icon", json:"application/json", webmanifest:"application/manifest+json" };

// JC-LAZO-WWSEO-0919-010: harvest, aquarelle, prism, meadow, gilded, marigold, papel
const TEMPLATES = ["sage","noir","dune","fete","tide","flora","atelier","verona","shore","summit","ranch","starlit","frost",
                   "harvest","aquarelle","prism","meadow","gilded","marigold","papel","peony"];
const PROJECT = "lazo-513ec";

// Unwrap Firestore REST typed values into plain JS
function fsVal(v) {
  if (v == null) return null;
  if ("stringValue" in v) return v.stringValue;
  if ("integerValue" in v) return Number(v.integerValue);
  if ("doubleValue" in v) return v.doubleValue;
  if ("booleanValue" in v) return v.booleanValue;
  if ("timestampValue" in v) return v.timestampValue;
  if ("arrayValue" in v) return (v.arrayValue.values || []).map(fsVal);
  if ("mapValue" in v) {
    const o = {};
    for (const [k, x] of Object.entries(v.mapValue.fields || {})) o[k] = fsVal(x);
    return o;
  }
  return null;
}

async function fsDoc(collection, id) {
  const docUrl = `https://firestore.googleapis.com/v1/projects/${PROJECT}/databases/(default)/documents/${collection}/${encodeURIComponent(id)}`;
  const r = await fetch(docUrl, { headers: await fsHeaders() });
  if (!r.ok) return null;
  const doc = await r.json();
  return doc.fields || null;
}

// The couple's song: a live preview URL through the relay, or nothing.
async function siteSong(song) {
  if (!song || typeof song !== "object") return null;
  if (song.autoplay === false && !song.preview && !song.trackId) return null;
  let preview = String(song.preview || "");
  const id = String(song.trackId || "");
  if (/^dz\d+$/.test(id)) {
    try {
      const key = new Request("https://meetlazo.com/music/track/" + id, { method: "GET" });
      let r = await caches.default.match(key);
      if (!r) {
        r = await fetch("https://api.deezer.com/track/" + id.slice(2), { headers: { accept: "application/json" } });
        if (r.ok) { r = new Response(await r.text(), { headers: { "content-type": "application/json", "cache-control": "public, max-age=21600" } }); await caches.default.put(key, r.clone()); }
      }
      if (r && r.ok) { const j = await r.json(); if (j && j.preview) preview = j.preview; }
    } catch (e) {}
  }
  if (!preview) return null;
  let src = preview;
  try {
    const h = new URL(preview).hostname;
    if (PREVIEW_HOSTS.some(rx => rx.test(h))) src = "https://meetlazo.com/music/preview?u=" + encodeURIComponent(preview);
  } catch (e) { return null; }
  return { title: String(song.title || ""), artist: String(song.artist || ""), art: String(song.art || ""),
           src, autoplay: song.autoplay !== false, loop: !!song.loop };
}

const esc = (t) => String(t || "").replace(/[&<>"]/g,
  (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// JC-LAZO-WWSEO-0919-010: every public couple site (no passcode, has names),
// fetched once from Firestore and cached six hours. Feeds the couples sitemap
// and the /couples/ search. Sites with a passcode never appear anywhere.
async function listPublicCouples() {
  const key = new Request("https://meetlazo.com/_internal/public-couples.json");
  const hit = await caches.default.match(key);
  if (hit) { try { return await hit.json(); } catch (e) {} }
  const out = [];
  let pageToken = "";
  for (let i = 0; i < 40; i++) {
    const u = `https://firestore.googleapis.com/v1/projects/${PROJECT}/databases/(default)/documents/weddingSites`
      + "?pageSize=300&mask.fieldPaths=passcode&mask.fieldPaths=names&mask.fieldPaths=dateIso"
      + (pageToken ? `&pageToken=${encodeURIComponent(pageToken)}` : "");
    let j;
    try {
      const rr = await fetch(u, { headers: await fsHeaders() });
      if (!rr.ok) break;
      j = await rr.json();
    } catch (e) { break; }
    for (const d of (j.documents || [])) {
      const slug = String(d.name || "").split("/").pop();
      if (!/^[a-z0-9\-]{1,80}$/.test(slug)) continue;
      const f = d.fields || {};
      if (fsVal(f.passcode)) continue;
      const names = String(fsVal(f.names) || "").trim();
      if (!names) continue;
      out.push({ slug, names, dateIso: String(fsVal(f.dateIso) || ""), lm: String(d.updateTime || "").slice(0, 10) });
    }
    pageToken = j.nextPageToken || "";
    if (!pageToken) break;
  }
  await caches.default.put(key, new Response(JSON.stringify(out), {
    headers: { "content-type": "application/json", "cache-control": "public, max-age=21600" } }));
  return out;
}

// JC-LAZO-WWSEO-0919-002: every public couple site, one sitemap.
async function couplesSitemap() {
  const list = await listPublicCouples();
  const locs = list.map(c => `<url><loc>https://meetlazo.com/w/${c.slug}/</loc>${c.lm ? `<lastmod>${c.lm}</lastmod>` : ""}</url>`);
  const xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + locs.join("\n") + "\n</urlset>";
  return new Response(xml, { headers: { "content-type": "application/xml; charset=utf-8",
    "cache-control": "public, max-age=3600, s-maxage=21600", "x-lazo-couples": String(locs.length) } });
}

// JC-LAZO-UNFURL-0920-001: a page URL -> its picture and title, for the dream board.
const UNFURL_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36";
async function unfurl(url) {
  const headers = { "content-type": "application/json", "access-control-allow-origin": "*", "cache-control": "public, max-age=86400" };
  const raw = String(url.searchParams.get("u") || "").trim();
  let target;
  try { target = new URL(raw); } catch (e) { return new Response(JSON.stringify({ error: "bad url" }), { status: 400, headers }); }
  if (target.protocol !== "https:" && target.protocol !== "http:") return new Response(JSON.stringify({ error: "bad url" }), { status: 400, headers });
  if (/^(localhost|127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/.test(target.hostname)) return new Response(JSON.stringify({ error: "bad url" }), { status: 400, headers });
  const key = new Request("https://meetlazo.com/_unfurl/" + encodeURIComponent(target.href));
  const hit = await caches.default.match(key);
  if (hit) return hit;
  // A direct image needs no page.
  if (/\.(jpe?g|png|webp|gif|avif)(\?|$)/i.test(target.pathname + target.search)) {
    const r = new Response(JSON.stringify({ image: target.href, title: "", site: target.hostname.replace(/^www\./, ""), url: target.href }), { headers });
    await caches.default.put(key, r.clone());
    return r;
  }
  let html = "";
  let finalUrl = target.href;
  try {
    const rr = await fetch(target.href, { headers: { "user-agent": UNFURL_UA, accept: "text/html,*/*" }, redirect: "follow", cf: { cacheTtl: 3600 } });
    finalUrl = rr.url || finalUrl;
    const ct = rr.headers.get("content-type") || "";
    if (/^image\//i.test(ct)) {
      const r = new Response(JSON.stringify({ image: finalUrl, title: "", site: target.hostname.replace(/^www\./, ""), url: finalUrl }), { headers });
      await caches.default.put(key, r.clone());
      return r;
    }
    html = (await rr.text()).slice(0, 400000);
  } catch (e) {
    return new Response(JSON.stringify({ error: "fetch failed" }), { status: 502, headers });
  }
  const meta = (names) => {
    for (const n of names) {
      const m = html.match(new RegExp(`<meta[^>]+(?:property|name)=["']${n}["'][^>]*content=["']([^"']+)["']`, "i"))
        || html.match(new RegExp(`<meta[^>]+content=["']([^"']+)["'][^>]*(?:property|name)=["']${n}["']`, "i"));
      if (m && m[1]) return m[1].replace(/&amp;/g, "&").replace(/&#x27;|&#39;/g, "'").replace(/&quot;/g, '"').trim();
    }
    return "";
  };
  let image = meta(["og:image:secure_url", "og:image", "twitter:image", "twitter:image:src"]);
  if (!image) {
    const m = html.match(/<link[^>]+rel=["']image_src["'][^>]*href=["']([^"']+)["']/i);
    if (m) image = m[1];
  }
  if (image && !/^https?:/i.test(image)) { try { image = new URL(image, finalUrl).href; } catch (e) { image = ""; } }
  // Pinterest serves pin pages without og:image to anything it doesn't trust,
  // but the pin's own picture is in the body as an i.pinimg.com URL.
  if (!image) {
    const pm = html.match(/https:\/\/i\.pinimg\.com\/(?:originals|736x|564x|474x)\/[A-Za-z0-9\/._-]+\.(?:jpe?g|png|webp|gif)/);
    if (pm) image = pm[0];
  }
  // Last resort on any page: the first sizeable <img> with an absolute src.
  if (!image) {
    const im = html.match(/<img[^>]+src=["'](https?:\/\/[^"']+\.(?:jpe?g|png|webp)(?:\?[^"']*)?)["']/i);
    if (im) image = im[1];
  }
  let title = meta(["og:title", "twitter:title"]);
  if (!title) { const m = html.match(/<title[^>]*>([^<]{1,200})<\/title>/i); if (m) title = m[1].trim(); }
  title = title.replace(/\s+/g, " ").slice(0, 140);
  title = title.replace(/\s*[|–-]\s*Pinterest\s*$/i, "").replace(/^Pinterest$/i, "");
  const site = meta(["og:site_name"]) || target.hostname.replace(/^www\./, "");
  const r = new Response(JSON.stringify({ image, title, site, url: finalUrl }), { headers });
  await caches.default.put(key, r.clone());
  return r;
}

// JC-LAZO-WWSEO-0919-010: /api/couples?q=<name> for the /couples/ search page.
async function couplesSearch(url) {
  const q = String(url.searchParams.get("q") || "").trim().toLowerCase().replace(/\s+/g, " ");
  const headers = { "content-type": "application/json", "cache-control": "public, max-age=300", "access-control-allow-origin": "*" };
  if (q.length < 2 || q.length > 60) return new Response("[]", { headers });
  const list = await listPublicCouples();
  const words = q.split(" ").filter(Boolean);
  const hits = list.filter(c => { const n = c.names.toLowerCase(); return words.every(w => n.includes(w)); })
    .sort((a, b) => (b.dateIso || "").localeCompare(a.dateIso || ""))
    .slice(0, 20)
    .map(c => ({ slug: c.slug, names: c.names, dateIso: c.dateIso }));
  return new Response(JSON.stringify(hits), { headers });
}

// JC-LAZO-WORKER-0929-GUESTPHOTOS-001: a positioned photo, or null.
function photoSlot(v) {
  if (!v || typeof v !== "object") return null;
  const num = (x, d, lo, hi) => (typeof x === "number" && isFinite(x)) ? Math.min(hi, Math.max(lo, x)) : d;
  const out = { x: num(v.x, .5, 0, 1), y: num(v.y, .5, 0, 1), zoom: num(v.zoom, 1, 1, 3) };
  if (typeof v.url === "string" && /^https:\/\//.test(v.url)) out.url = v.url;
  return out;
}

// JC-LAZO-WORKER-0930-SITEFIX: the passcode gate lives here, not in the page (helpers in fsauth.js).
function gatePage(slug, names, wrong) {
  const who = names ? esc(names) : "A private celebration";
  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex, nofollow"><title>${who} — enter the passcode</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600&family=Inter:wght@400;500&display=swap" rel="stylesheet">
<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#FBF7F0;color:#241E2B;font:15px/1.5 Inter,system-ui,sans-serif}
.g{width:min(92vw,360px);text-align:center;padding:36px 28px;background:#fff;border:1px solid #E6D6B8;border-radius:22px;box-shadow:0 30px 60px -40px rgba(36,30,43,.5)}
.k{letter-spacing:.18em;text-transform:uppercase;font-size:11px;color:#8A6A2F;font-weight:600;margin:0 0 8px}
h1{font:500 30px/1.15 "Cormorant Garamond",serif;margin:0 0 18px;color:#52284F}
input{font:inherit;padding:13px;width:100%;box-sizing:border-box;border:1px solid #E6D6B8;border-radius:10px;text-align:center;letter-spacing:.12em}
button{font:inherit;font-weight:600;margin-top:12px;width:100%;padding:13px;border:0;border-radius:999px;background:#52284F;color:#fff;cursor:pointer}
p.e{color:#B23B3B;margin:12px 0 0;font-size:14px}p.h{color:#7A6E85;margin:14px 0 0;font-size:13px}</style></head>
<body><form class="g" method="post" action="/w/${encodeURIComponent(slug)}/unlock"><p class="k">A private celebration</p><h1>${who}</h1>
<input name="code" aria-label="Passcode" autocomplete="one-time-code" autofocus required><button type="submit">Open the site</button>
${wrong ? '<p class="e">That passcode didn\'t match. Try again?</p>' : ''}<p class="h">The passcode is on your invitation.</p></form></body></html>`;
  return new Response(html, { status: wrong ? 403 : 401, headers: {
    "content-type": TYPES.html, "cache-control": "private, no-store", "x-robots-tag": "noindex, nofollow" } });
}
async function unlockRoute(slug, req) {
  const f = await fsDoc("weddingSites", slug);
  const code = String(fsVal(f && f.passcode) || "").trim();
  let given = "";
  try { given = String((await req.formData()).get("code") || "").trim(); } catch (e) { given = ""; }
  const back = `/w/${encodeURIComponent(slug)}/`;
  if (!code || given !== code) return new Response(null, { status: 303, headers: { location: back + "?wrong=1", "cache-control": "no-store" } });
  const tok = await pcToken(slug, code);
  return new Response(null, { status: 303, headers: {
    location: back, "cache-control": "no-store",
    "set-cookie": `lzw_${slug}=${tok}; Path=${back}; Max-Age=2592000; Secure; HttpOnly; SameSite=Lax` } });
}

// JC-LAZO-WORKER-0930-FSAUTH: what the page reads after it loads - the guestbook, chapters, the
// seat finder (only the matches, never the list), the room map (tables, no
// names) and a personal invite. Each honours the passcode cookie.
async function siteDataRoute(slug, what, url, req) {
  const f = await fsDoc("weddingSites", slug);
  if (!f) return json({ ok: false, error: "not_found" }, 404);
  const code = String(fsVal(f.passcode) || "").trim();
  if (await siteLocked(slug, req, code)) return lockedResponse();
  const h = { "content-type": "application/json", "access-control-allow-origin": "*",
    "cache-control": code ? "private, no-store" : "public, max-age=0, s-maxage=20" };
  const base = `https://firestore.googleapis.com/v1/projects/${PROJECT}/databases/(default)/documents/weddingSites/${encodeURIComponent(slug)}`;
  const pick = (fields, keep) => { const o = {}; for (const k of keep) if (fields && fields[k]) o[k] = fields[k]; return o; };
  const listOf = async (sub, n, keep) => {
    const r = await fetch(`${base}/${sub}?pageSize=${n}`, { headers: await fsHeaders() });
    if (!r.ok) return { documents: [] };
    const j = await r.json();
    return { documents: (j.documents || []).map(d => ({ name: d.name, fields: pick(d.fields, keep) })) };
  };
  if (what === "guestbook") return new Response(JSON.stringify(await listOf("guestbook", 60, ["name", "message", "createdAt"])), { headers: h });
  if (what === "chapters") return new Response(JSON.stringify(await listOf("chapters", 40, ["title", "text", "dateIso", "photos"])), { headers: h });
  if (what.startsWith("invite/")) {
    const r = await fetch(`${base}/invites/${encodeURIComponent(what.slice(7))}`, { headers: await fsHeaders() });
    if (!r.ok) return json({ ok: false, error: "not_found" }, 404);
    const d = await r.json();
    return new Response(JSON.stringify({ fields: pick(d.fields, ["name", "party", "plusOnes", "meals"]) }), { headers: { ...h, "cache-control": "private, no-store" } });
  }
  // seating/main, held 30 s so the finder's keystrokes don't each cost a read
  const key = new Request(`https://meetlazo.com/_internal/seating/${slug}`);
  let sd = null;
  try { const hit = await caches.default.match(key); if (hit) sd = await hit.json(); } catch (e) {}
  if (!sd) {
    const r = await fetch(`${base}/seating/main`, { headers: await fsHeaders() });
    sd = r.ok ? ((await r.json()).fields || {}) : {};
    try { await caches.default.put(key, new Response(JSON.stringify(sd), { headers: { "content-type": "application/json", "cache-control": "public, max-age=30" } })); } catch (e) {}
  }
  if (what === "room") return new Response(JSON.stringify({ fields: pick(sd, ["tables", "canvas"]) }), { headers: h });
  // seat: the same matching the page used to do on the whole list
  const norm = (x) => String(x || "").toLowerCase().replace(/[^a-z0-9 ]+/g, " ").replace(/\s+/g, " ").trim();
  const q = norm(url.searchParams.get("q"));
  if (q.length < 2) return new Response(JSON.stringify({ fields: { guests: { arrayValue: { values: [] } } } }), { headers: { ...h, "cache-control": "no-store" } });
  const words = q.split(" ");
  const vals = ((sd.guests && sd.guests.arrayValue && sd.guests.arrayValue.values) || []);
  const str = (v, k) => norm(v.mapValue && v.mapValue.fields && v.mapValue.fields[k] && v.mapValue.fields[k].stringValue);
  const hits = vals.filter(v => { const n = str(v, "n"), p = str(v, "p");
    return words.every(w => n.includes(w)) || (p && words.every(w => p.includes(w))); }).slice(0, 6);
  return new Response(JSON.stringify({ fields: { guests: { arrayValue: { values: hits } } } }), { headers: { ...h, "cache-control": "no-store" } });
}

async function renderCoupleSite(slug, env, req) {
  // 1. the couple's site doc
  const f = await fsDoc("weddingSites", slug);
  if (!f) return null;
  const g = (k) => fsVal(f[k]);

  // 2. their chosen template, from the same bucket the demos live in
  // JC-LAZO-WWT-0929-PEONY: Peony is the default design (was Fete)
  let tpl = (g("template") || "peony").toString();
  if (!TEMPLATES.includes(tpl)) tpl = "peony";
  let asset = await env.SITE.get(`wedding-websites/${tpl}/index.html`);
  if (!asset) asset = await env.SITE.get(`wedding-websites/peony/index.html`);
  if (!asset) return null;
  let html = await asset.text();
  // JC-LAZO-WWSEO-0919-002: the demo page's canonical, share tags and JSON-LD
  // describe the TEMPLATE. A couple's site gets its own below.
  html = html.replace(/<!-- lz-seo -->[\s\S]*?<!-- \/lz-seo -->\n?/, "");

  // 3. the payload the template's hydration layer consumes
  const payload = {
    slug,
    names: g("names") || "",
    dateIso: g("dateIso") || "",
    story: g("story") || "",
    venueName: g("venueName") || "",
    venueAddress: g("venueAddress") || "",
    ceremonyTime: g("ceremonyTime") || "",
    cocktailTime: g("cocktailTime") || "",
    receptionTime: g("receptionTime") || "",
    sendOffTime: g("sendOffTime") || "",
    dressCode: g("dressCode") || "",
    hotelBlock: g("hotelBlock") || "",
    transport: g("transport") || "",
    parking: g("parking") || "",
    travelNotes: g("travelNotes") || "",
    registryLinks: g("registryLinks") || [],
    registryNote: g("registryNote") || "",
    rsvpBy: g("rsvpBy") || "",
    vendorTeam: g("vendorTeam") || [],
    siteGallery: g("siteGallery") || [],
    passcode: g("passcode") || "",
    rsvpOpen: g("rsvpOpen") !== false,
    coverUrl: g("coverUrl") || "",
    palette: g("palette") || "",
    song: await siteSong(g("song")),
    nearbyOn: g("nearbyOn") !== false,
    nearbyNote: g("nearbyNote") || "",
    nearbyPicks: g("nearbyPicks") || [],
    // JC-LAZO-WORKER-0929-GUESTPHOTOS-001: photos where the couple put them.
    // {url, x, y, zoom}: x/y 0..1 is the point that stays in view, zoom 1..3.
    heroPhoto: photoSlot(g("heroPhoto")),
    storyPhoto: photoSlot(g("storyPhoto")),
    coverFocus: photoSlot(g("coverFocus")) || null,
    siteGalleryFocus: (g("siteGalleryFocus") || []).map(photoSlot),
    guestPhotosOn: g("guestPhotosOn") !== false,
    guestPhotosNote: g("guestPhotosNote") || "",
    // JC-LAZO-WORKER-0929-LIVE-001: the day hour by hour, seating lookup, meals
    // on the RSVP form, the photographer's gallery, translation
    timelineOn: g("timelineOn") !== false,
    timeline: (g("timeline") || []).filter(m => m && typeof m === "object" && m.label).slice(0, 40)
      .map(m => ({ time: String(m.time || ""), label: String(m.label || ""), note: String(m.note || ""), dur: Number(m.dur) || 0 })),
    seatingOn: g("seatingOn") === true,
    mealOptions: (g("mealOptions") || []).map(String).filter(Boolean).slice(0, 8),
    galleryUrl: /^https:\/\//.test(String(g("galleryUrl") || "")) ? String(g("galleryUrl")) : "",
    translateOn: g("translateOn") !== false,
    // JC-LAZO-WORKER-0929-MORE-001: the weekend's events, the hotel, the hold
    events: (g("events") || []).filter(e => e && typeof e === "object" && e.name).slice(0, 12).map(e => ({
      name: String(e.name || ""), dateIso: /^\d{4}-\d{2}-\d{2}$/.test(String(e.dateIso || "")) ? String(e.dateIso) : "",
      time: String(e.time || ""), venueName: String(e.venueName || ""), venueAddress: String(e.venueAddress || ""),
      note: String(e.note || ""), rsvp: e.rsvp === true, dress: String(e.dress || "") })),
    hotelAddress: g("hotelAddress") || "",
    guestPhotosHold: g("guestPhotosHold") === true,
  };

  const priv = !!payload.passcode;
  // JC-LAZO-WORKER-0930-SITEFIX: the browser only ever sees a passcode site after proving the code
  if (priv) {
    const want = await pcToken(slug, String(payload.passcode).trim());
    if (cookieVal(req, "lzw_" + slug) !== want) {
      const wrong = !!(req && new URL(req.url).searchParams.get("wrong"));
      return gatePage(slug, payload.names, wrong);
    }
    payload.passcode = "";
    payload.locked = true;
  }
  let inject = `<script>window.LAZO_SITE=${JSON.stringify(payload)
    .replace(/</g, "\\u003c")};</script>`;
  if (priv) inject = '<meta name="robots" content="noindex, nofollow">\n' + inject;

  // Share preview: scrapers don't run the page's JavaScript, so the couple's
  // names, date, venue and photo go into the head here. A passcode site gets
  // the names and nothing else - no photo, no venue.
  const title = payload.names ? `${payload.names} — wedding` : "You're invited";
  let dateNice = "";
  if (/^\d{4}-\d{2}-\d{2}$/.test(payload.dateIso)) {
    const d = new Date(payload.dateIso + "T12:00:00");
    dateNice = d.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
  }
  const desc = priv
    ? "A private celebration - the passcode is on the invitation."
    : [dateNice, payload.venueName, payload.venueAddress].filter(Boolean).join(" · ") || "Save the date - details, schedule and RSVP.";
  const image = priv ? "" : ((payload.heroPhoto && payload.heroPhoto.url) || payload.coverUrl || (payload.siteGallery || [])[0] || "");
  const pageUrl = `https://meetlazo.com/w/${encodeURIComponent(slug)}/`;
  let og = `<meta property="og:type" content="website">\n<meta property="og:site_name" content="Lazo">\n<meta property="og:title" content="${esc(title)}">\n<meta property="og:description" content="${esc(desc)}">\n<meta property="og:url" content="${pageUrl}">\n<meta name="description" content="${esc(desc)}">\n`;
  if (image) og += `<meta property="og:image" content="${esc(image)}">\n<meta name="twitter:card" content="summary_large_image">\n<meta name="twitter:image" content="${esc(image)}">\n`;
  else og += `<meta name="twitter:card" content="summary">\n`;
  html = html.replace(/<title>[^<]*<\/title>/, `<title>${esc(title)}</title>`);
  // JC-LAZO-WORKER-0930-SITEFIX: the template's own description describes the design, not the couple
  html = html.replace(/<meta name="description" content="[^"]*">\n?/, "");
  // JC-LAZO-WWSEO-0919-002: a public couple site is a page worth finding - guests
  // search "<names> wedding". Canonical (the /w/ URL takes ?palette etc.) and an
  // Event when the date is known, else a plain WebPage. Passcode sites get nothing.
  let seo = "";
  if (!priv) {
    seo += `<link rel="canonical" href="${pageUrl}">\n`;
    const ld = { "@context": "https://schema.org", "@type": "WebPage", name: title, url: pageUrl, description: desc };
    if (/^\d{4}-\d{2}-\d{2}$/.test(payload.dateIso)) {
      ld["@type"] = "Event";
      ld.startDate = payload.dateIso;
      ld.eventStatus = "https://schema.org/EventScheduled";
      ld.eventAttendanceMode = "https://schema.org/OfflineEventAttendanceMode";
      if (payload.venueName || payload.venueAddress) {
        ld.location = { "@type": "Place", name: payload.venueName || payload.venueAddress };
        if (payload.venueAddress) ld.location.address = payload.venueAddress;
      }
      if (payload.names) ld.organizer = { "@type": "Person", name: payload.names };
    }
    if (image) ld.image = image;
    seo += `<script type="application/ld+json">${JSON.stringify(ld).replace(/</g, "\\u003c")}</script>\n`;
  }
  html = html.replace("</head>", seo + og + inject + "\n</head>");
  // DIRECTIONS-001: tap the venue, open the phone's navigation
  html = html.replace(/<\/body>/i, DIRECTIONS_JS + "\n</body>");

  const headers = {
    "content-type": TYPES.html,
    "cache-control": "public, max-age=60, s-maxage=120",
    "access-control-allow-origin": "*",
    "x-lazo": "tied-together",
  };
  if (priv) { headers["x-robots-tag"] = "noindex, nofollow"; headers["cache-control"] = "private, no-store"; }
  headers["x-lazo-fs"] = (await workerToken()) ? "signed-in" : "anonymous";  // JC-LAZO-WORKER-0930-FSAUTH: visible proof of the sign-in
  return new Response(html, { headers });
}

// ─────────────────────────────────────────────────────────────────────────────
// JC-LAZO-GALLERY-0911-005: post-wedding delivery galleries
// ─────────────────────────────────────────────────────────────────────────────
const GAL_VARIANTS = { thumb: 86400, web: 86400, full: 3600 };
const PASS_TTL_MS = 1000 * 60 * 60 * 24 * 30;  // passcode cookie lives 30 days

const b64url = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf)))
  .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");

async function hmac(env, msg) {
  const key = await crypto.subtle.importKey("raw",
    new TextEncoder().encode(env.GALLERY_SECRET || "dev-only-not-a-secret"),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return b64url(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(msg)));
}

// Constant-time-ish compare; both sides are our own base64url of fixed length.
function safeEq(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) return false;
  let out = 0;
  for (let i = 0; i < a.length; i++) out |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return out === 0;
}

async function loadGallery(slug, env) {
  const f = await fsDoc("galleries", slug);
  if (!f) return null;
  const g = (k) => fsVal(f[k]);
  // status is set by the finalize callable and flipped by the tier trigger.
  // Anything not explicitly live is a 404 to the outside world.
  if (g("status") !== "live") return null;
  const expiresAt = g("expiresAt") || "";
  if (expiresAt && Date.parse(expiresAt) < Date.now()) return null;
  return {
    slug,
    vendorId: g("vendorId") || "",
    vendorName: g("vendorName") || "",
    vendorSlug: g("vendorSlug") || "",
    names: g("names") || "",
    dateIso: g("dateIso") || "",
    message: g("message") || "",
    coverId: g("coverId") || "",
    photoCount: g("photoCount") || 0,
    downloadsOn: g("downloadsOn") !== false,
    storeOn: g("storeOn") !== false,
    passcodeHash: (g("passcodeHash") || "").toString(),
    expiresAt,
    showcase: g("showcase") === true,
    showcaseTitle: g("showcaseTitle") || "",
    showcaseBlurb: g("showcaseBlurb") || "",
  };
}

async function galleryManifest(slug, env) {
  try {
    const o = await env.GALLERIES.get(`${slug}/manifest.json`);
    if (!o) return [];
    const m = await o.json();
    return Array.isArray(m) ? m : (m.photos || []);
  } catch { return []; }
}

async function hasPass(req, slug, env) {
  const cookie = req.headers.get("cookie") || "";
  const m = cookie.match(new RegExp(`lazo_g_${slug.replace(/[^a-z0-9-]/gi, "")}=([^;]+)`));
  if (!m) return false;
  const [exp, sig] = decodeURIComponent(m[1]).split(".");
  if (!exp || !sig || Number(exp) < Date.now()) return false;
  return safeEq(sig, await hmac(env, `pass:${slug}:${exp}`));
}

async function renderGallery(slug, req, env) {
  const gal = await loadGallery(slug, env);
  if (!gal) return null;

  const asset = await env.SITE.get("gallery/index.html");
  if (!asset) return null;
  let html = await asset.text();

  const locked = !!gal.passcodeHash && !(await hasPass(req, slug, env));
  const photos = locked ? [] : await galleryManifest(slug, env);

  // BRAND-001: the vendor's colors and logo ride along with the gallery.
  const brand = await vendorBrand(gal.vendorId);
  const payload = {
    slug,
    brand,
    names: gal.names,
    dateIso: gal.dateIso,
    message: gal.message,
    vendorName: gal.vendorName,
    vendorSlug: gal.vendorSlug,
    coverId: gal.coverId,
    photoCount: gal.photoCount,
    downloadsOn: gal.downloadsOn,
    storeOn: gal.storeOn,
    expiresAt: gal.expiresAt,
    locked,
    // [{id, name, w, h}] — md5 stays server-side, it's only for WHCC
    photos: photos.map((p) => ({ id: p.id, name: p.name, w: p.w, h: p.h })),
  };

  const title = gal.names ? `${gal.names} — photos` : "Your wedding photos";
  const inject =
    `<script>window.LAZO_GALLERY=${JSON.stringify(payload).replace(/</g, "\\u003c")};</script>`;
  // Wedding photos are never public: no og:image, no indexing, ever.
  const head =
    `<meta name="robots" content="noindex, nofollow">\n` +
    `<meta property="og:type" content="website">\n` +
    `<meta property="og:site_name" content="Lazo">\n` +
    `<meta property="og:title" content="${esc(title)}">\n` +
    `<meta property="og:description" content="A private gallery from Lazo.">\n` +
    `<meta name="twitter:card" content="summary">\n`;
  html = html.replace(/<title>[^<]*<\/title>/, `<title>${esc(title)}</title>`);
  html = html.replace("</head>", head + inject + brandHead(brand) + "\n</head>");
  if (brand.logoUrl || brand.name) html = html.replace(/<body([^>]*)>/, (m) => m + brandStrip(brand));

  return new Response(html, { headers: {
    "content-type": TYPES.html,
    "cache-control": "private, no-store",
    "x-robots-tag": "noindex, nofollow",
    "x-lazo": "tied-together",
  }});
}

async function serveGalleryImage(slug, id, variant, req, env) {
  if (!(variant in GAL_VARIANTS)) return new Response("Not found", { status: 404 });
  const gal = await loadGallery(slug, env);
  if (!gal) return new Response("Not found", { status: 404 });
  const showcasePublic = gal.showcase && variant !== "full";
  if (gal.passcodeHash && !showcasePublic && !(await hasPass(req, slug, env)))
    return new Response("Locked", { status: 403 });
  if (variant === "full" && !gal.downloadsOn)
    return new Response("Downloads are turned off for this gallery", { status: 403 });

  const obj = await env.GALLERIES.get(`${slug}/${variant}/${id}.jpg`);
  if (!obj) return new Response("Not found", { status: 404 });

  const headers = {
    "content-type": TYPES.jpg,
    "cache-control": `private, max-age=${GAL_VARIANTS[variant]}`,
    "x-robots-tag": "noindex, nofollow",
    "x-lazo": "tied-together",
  };
  if (variant === "full") {
    const name = (new URL(req.url).searchParams.get("name") || `${id}.jpg`)
      .replace(/[^A-Za-z0-9._-]/g, "_").slice(0, 120);
    headers["content-disposition"] = `attachment; filename="${name}"`;
  }
  if (obj.httpEtag) headers.etag = obj.httpEtag;
  return new Response(obj.body, { headers });
}

// WHCC fetches AssetPath server-side, so it needs a URL with no cookie and no
// passcode — but one that expires and can't be guessed or walked.
async function serveSignedAsset(exp, sig, slug, id, env) {
  if (Number(exp) < Date.now()) return new Response("Expired", { status: 410 });
  if (!safeEq(sig, await hmac(env, `asset:${slug}:${id}:${exp}`)))
    return new Response("Bad signature", { status: 403 });
  const obj = await env.GALLERIES.get(`${slug}/full/${id}.jpg`);
  if (!obj) return new Response("Not found", { status: 404 });
  return new Response(obj.body, { headers: {
    "content-type": TYPES.jpg,
    "cache-control": "private, max-age=3600",
    "x-robots-tag": "noindex, nofollow",
  }});
}

// JC-LAZO-GONE-0903: delisted vendor pages answer 410 Gone.
// build.py writes dist/_gone.json = [{"metro": "...", "slug": "..."}]; the sync
// puts it in R2; we cache it 5 min per isolate and match /{metro}/{cat}/{slug}/.
let _goneSet = null, _goneAt = 0;
async function loadGone(env) {
  if (_goneSet && Date.now() - _goneAt < 300000) return _goneSet;
  const s = new Set();
  try {
    const o = await env.SITE.get("_gone.json");
    if (o) for (const g of await o.json()) if (g.metro && g.slug) s.add(`${g.metro}|${g.slug}`);
  } catch {}
  _goneSet = s; _goneAt = Date.now();
  return s;
}
// JC-LAZO-MOVED-0916-001: a vendor page's URL changes when a new metro takes the
// business off a neighbouring grid, when it is re-categorised, or when a duplicate
// slug shifts. build.py writes dist/_moved.json = {oldPath: newPath}; without this
// the old page is orphaned in R2 and competes with the new one for the same query.
// Cached 5 min per isolate, same as _gone.json.
let _movedMap = null, _movedAt = 0;
async function loadMoved(env) {
  if (_movedMap && Date.now() - _movedAt < 300000) return _movedMap;
  let m = {};
  try {
    const o = await env.SITE.get("_moved.json");
    if (o) m = await o.json();
  } catch {}
  _movedMap = m; _movedAt = Date.now();
  return m;
}

// JC-LAZO-CFORM-0916-001: the page a reader without JavaScript lands on after
// posting the contact form. Same palette as the site; noindex; one way back.
const contactShell = (ok, headline, body) => `<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>${esc(headline)} - Lazo</title>
<link rel="stylesheet" href="/assets/lazo.css">
<link rel="icon" href="/assets/favicon-32.png" sizes="32x32" type="image/png"></head>
<body><header class="site-head"><a class="brand" href="/"><img src="/assets/brand.png" alt="Lazo - Tied together" class="brand-lockup"></a></header>
<main><section class="band prose doc" style="padding-top:64px">
<p class="eyebrow" style="color:${ok ? "#2E8B6B" : "#B4453F"}">${ok ? "Sent" : "Not sent"}</p>
<h1 style="font-size:36px">${esc(headline)}</h1><p class="lede">${esc(body)}</p>
<p class="page-back" style="margin-top:32px"><a href="/contact/">Back to Contact</a></p>
</section></main></body></html>`;

const GONE_HTML = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="robots" content="noindex"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Listing removed - Lazo</title></head><body style="font-family:system-ui,sans-serif;margin:4rem auto;max-width:36rem;padding:0 1rem;color:#222"><h1 style="font-weight:600">This listing has been removed</h1><p>The vendor asked us to take it down. <a href="/">Browse Lazo</a> for other wedding pros in your area.</p></body></html>`;

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    setWorkerEnv(env);  // JC-LAZO-WORKER-0930-FSAUTH

    // JC-LAZO-LAUNCH-0921-001: one canonical host. Plain http and www both 301 to
    // https://meetlazo.com so search engines see a single origin, and /favicon.ico
    // (which browsers and Google request regardless of <link rel=icon>) serves the
    // real icon instead of a 404. GET/HEAD only; API posts are never redirected.
    if ((req.method === "GET" || req.method === "HEAD")
        && (url.protocol === "http:" || url.hostname === "www.meetlazo.com")) {
      url.protocol = "https:"; url.hostname = "meetlazo.com";
      return Response.redirect(url.toString(), 301);
    }
    if (url.pathname === "/favicon.ico") {
      const ico = await env.SITE.get("assets/favicon.ico");
      if (ico) return new Response(ico.body, { headers: { "content-type": "image/x-icon", "cache-control": "public, max-age=604800" } });
    }

    // JC-LAZO-PRINTS-0920-001: /api/prints/*, /prints/*, /g/{slug}/store/*
    const printsResp = await printsRoute(req, url, env);
    if (printsResp) return printsResp;

    if (req.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: CORS });
    }

    // Vendor claim-interest endpoint (founding-vendor waitlist)
    if (url.pathname === "/api/claim-interest" && req.method === "POST") {
      try {
        const body = await req.json();
        const email = (body.email || "").trim().toLowerCase();
        if (body.website) return json({ ok: true });
        if (!/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(email) || email.length > 254)
          return json({ ok: false, error: "invalid" }, 400);
        const key = `signups/claim-${Date.now()}-${crypto.randomUUID().slice(0, 8)}.json`;
        await env.SITE.put(key, JSON.stringify({
          type: "claim",
          email,
          business: (body.business || "").slice(0, 120),
          vendorId: (body.vendorId || "").slice(0, 80),
          ts: new Date().toISOString(),
        }));
        return json({ ok: true });
      } catch {
        return json({ ok: false, error: "bad_request" }, 400);
      }
    }

    // Early-access signup endpoint (bride waitlist)
    if (url.pathname === "/api/early-access" && req.method === "POST") {
      try {
        const body = await req.json();
        const email = (body.email || "").trim().toLowerCase();
        if (body.website) return json({ ok: true });
        if (!/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(email) || email.length > 254)
          return json({ ok: false, error: "invalid" }, 400);
        const key = `signups/${Date.now()}-${crypto.randomUUID().slice(0, 8)}.json`;
        await env.SITE.put(key, JSON.stringify({
          email,
          metro: (body.metro || "").slice(0, 40),
          ts: new Date().toISOString(),
          ua: (req.headers.get("user-agent") || "").slice(0, 200),
        }));
        return json({ ok: true });
      } catch {
        return json({ ok: false, error: "bad_request" }, 400);
      }
    }

    // JC-LAZO-CFORM-0916-001 - the site's one contact endpoint.
    // Replaces five published mailboxes (hello@ / vendors@ / press@ / trust@ /
    // privacy@) with one form and one topic field. Submissions land in R2 under
    // contact/ exactly like signups/, and `python deploy\list_contacts.py` reads
    // them. Accepts JSON (lazo.js) and form-encoded (the no-JS fallback), and
    // answers the no-JS case with a real page rather than a blob of JSON.
    if (url.pathname === "/api/contact" && req.method === "POST") {
      const wantsHtml = !(req.headers.get("content-type") || "").includes("application/json");
      const reply = (ok, status, headline, body) =>
        wantsHtml
          ? new Response(contactShell(ok, headline, body), { status, headers: { "content-type": TYPES.html, "cache-control": "no-store", "x-robots-tag": "noindex" } })
          : json({ ok, error: ok ? undefined : headline }, status);
      try {
        let body;
        if (wantsHtml) {
          const fd = await req.formData();
          body = Object.fromEntries([...fd.entries()].map(([k, v]) => [k, typeof v === "string" ? v : ""]));
        } else {
          body = await req.json();
        }

        // Honeypot: a bot that fills the hidden field gets the same thank-you a
        // human gets, and nothing is written. Never tell a bot it was caught.
        if ((body.website || "").trim())
          return reply(true, 200, "Thank you", "We have your message.");

        const str = (v, n) => (v == null ? "" : String(v)).trim().slice(0, n);
        const email = str(body.email, 254).toLowerCase();
        const message = str(body.message, 4000);
        if (!/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(email))
          return reply(false, 400, "That email address doesn't look right",
            "Check the address you typed and send it again \u2014 it's how we reply to you.");
        if (message.length < 5)
          return reply(false, 400, "Your message came through empty",
            "Tell us what you need and send it again.");

        const TOPICS = ["general", "vendor", "trust", "privacy", "press", "delete", "legal", "other"];
        const topic = TOPICS.includes(str(body.topic, 20)) ? str(body.topic, 20) : "general";

        const key = `_inbox/contact/${Date.now()}-${crypto.randomUUID().slice(0, 8)}.json`;
        await env.SITE.put(key, JSON.stringify({
          type: "contact",
          topic,
          name: str(body.name, 120),
          email,
          accountEmail: str(body.accountEmail, 254).toLowerCase(),
          message,
          page: str(body.page, 200),
          referrer: str(body.referrer, 300),
          ts: new Date().toISOString(),
          country: req.headers.get("cf-ipcountry") || "",
          ua: (req.headers.get("user-agent") || "").slice(0, 200),
        }));

        // Optional: forward to a real inbox the moment RESEND_API_KEY exists as a
        // worker secret. Until it does, this is skipped and the R2 copy - which is
        // written first, above - remains the record of truth. A failure here never
        // fails the submission: the reader already gave us their message.
        if (env.RESEND_API_KEY && env.CONTACT_TO) {
          try {
            await fetch("https://api.resend.com/emails", {
              method: "POST",
              headers: { "content-type": "application/json", authorization: `Bearer ${env.RESEND_API_KEY}` },
              body: JSON.stringify({
                from: env.CONTACT_FROM || "Lazo site <noreply@meetlazo.com>",
                to: [env.CONTACT_TO],
                reply_to: email,
                subject: `[lazo/${topic}] ${str(body.name, 60) || email}`,
                text: `${message}\n\n--\nfrom: ${str(body.name, 120)} <${email}>\ntopic: ${topic}\npage: ${str(body.page, 200)}\nstored: ${key}`,
              }),
            });
          } catch { /* the R2 record is already written */ }
        }

        return reply(true, 200, "Thank you \u2014 that's with us",
          "A person reads every one of these. You'll hear back at the address you gave us, usually the same business day and always within two.");
      } catch {
        return reply(false, 400, "Something went wrong sending that",
          "Give it another try in a moment.");
      }
    }

    // JC-LAZO-GALLERY-0911-005: passcode → signed cookie
    if (url.pathname === "/api/gallery-auth" && req.method === "POST") {
      try {
        const body = await req.json();
        const slug = (body.slug || "").toString().toLowerCase();
        if (!/^[a-z0-9-]{1,80}$/.test(slug)) return json({ ok: false, error: "bad_request" }, 400);
        const gal = await loadGallery(slug, env);
        if (!gal) return json({ ok: false, error: "not_found" }, 404);
        // Doc is world-readable, so it holds sha256(passcode) — never the passcode.
        const given = (body.passcode || "").toString().trim().toLowerCase().slice(0, 40);
        const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(given));
        const hex = [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
        if (!gal.passcodeHash || !safeEq(hex, gal.passcodeHash))
          return json({ ok: false, error: "wrong_passcode" }, 401);
        const exp = Date.now() + PASS_TTL_MS;
        const sig = await hmac(env, `pass:${slug}:${exp}`);
        return new Response(JSON.stringify({ ok: true }), { status: 200, headers: {
          "content-type": "application/json",
          "cache-control": "no-store",
          "set-cookie": `lazo_g_${slug}=${encodeURIComponent(`${exp}.${sig}`)}; Path=/g/${slug}; Max-Age=${Math.floor(PASS_TTL_MS / 1000)}; HttpOnly; Secure; SameSite=Lax`,
          ...CORS,
        }});
      } catch {
        return json({ ok: false, error: "bad_request" }, 400);
      }
    }

    // JC-LAZO-GALLERY-0911-005: gallery image bytes
    const giMatch = url.pathname.match(/^\/g\/([a-z0-9-]{1,80})\/i\/([A-Za-z0-9_-]{1,64})\/(thumb|web|full)$/);
    if (giMatch && req.method === "GET") {
      return serveGalleryImage(giMatch[1], giMatch[2], giMatch[3], req, env);
    }

    // JC-LAZO-GALLERY-0911-005: expiring signed asset for WHCC's AssetPath
    const pMatch = url.pathname.match(/^\/p\/(\d{10,16})\/([A-Za-z0-9_-]{20,64})\/([a-z0-9-]{1,80})\/([A-Za-z0-9_-]{1,64})\.jpg$/);
    if (pMatch && req.method === "GET") {
      return serveSignedAsset(pMatch[1], pMatch[2], pMatch[3], pMatch[4], env);
    }

    // JC-LAZO-GALLERY-0911-005: couple-facing gallery page
    // JC-LAZO-WORKER-0913-SHOWCASE-001: public real-wedding pages
    const realMatch = url.pathname.match(/^\/real\/([a-z0-9-]{1,80})\/?$/);
    if (realMatch && req.method === "GET") {
      const resp = await renderShowcase(realMatch[1], req, env);
      if (resp) return resp;
      return new Response("Not found", { status: 404, headers: { "content-type": TYPES.html } });
    }
    const gMatch = url.pathname.match(/^\/g\/([a-z0-9-]{1,80})\/?$/);
    if (gMatch && req.method === "GET") {
      const resp = await renderGallery(gMatch[1], req, env);
      if (resp) return resp;
      const nf = await env.SITE.get("404.html");
      return new Response(nf ? nf.body : "Gallery not found", {
        status: 404, headers: { "content-type": TYPES.html, "x-robots-tag": "noindex, nofollow" } });
    }

    // MUSIC SEARCH: /music/search?q= -> Deezer/iTunes, cached a day, with CORS (JC-LAZO-WORKER-0912-MUSIC-001)
    if (url.pathname === "/music/preview") return musicPreview(url, req);
    if (url.pathname === "/api/song-request" && req.method === "OPTIONS") return new Response(null, { headers: CORS });
    if (url.pathname === "/api/song-request" && req.method === "POST") return songRequest(req);
    const rqMatch = url.pathname.match(/^\/w\/([a-z0-9-]{1,80})\/requests\/?$/);
    if (rqMatch) return requestPage(rqMatch[1]);
    if (url.pathname === "/music/search") return musicSearch(url);
    if (url.pathname === "/api/unfurl" && req.method === "GET") return unfurl(url);
    if (url.pathname === "/api/nearby") return nearbyPlaces(url, env);

    // JC-LAZO-TRACK-0916-001 — visitor analytics
    if (url.pathname === "/api/geo") return geoResponse(req);
    if (url.pathname === "/assets/lazo-track.js") return trackerResponse();

    // STORE ICONS: /icon/{host} → the store's own favicon, with CORS so Flutter web can draw it
    const iMatch = url.pathname.match(/^\/icon\/([a-z0-9.-]{3,80})$/i);
    if (iMatch && req.method === "GET") {
      const host = iMatch[1].toLowerCase();
      const cacheKey = new Request(`https://meetlazo.com/icon/${host}`, { method: "GET" });
      const cached = await caches.default.match(cacheKey);
      if (cached) return cached;
      const up = await fetch(`https://www.google.com/s2/favicons?domain=${encodeURIComponent(host)}&sz=128`, { redirect: "follow" });
      if (!up.ok) return new Response("", { status: 404, headers: { "cache-control": "public, max-age=3600", "access-control-allow-origin": "*" } });
      const body = await up.arrayBuffer();
      const resp = new Response(body, { headers: {
        "content-type": up.headers.get("content-type") || "image/png",
        "cache-control": "public, max-age=604800, s-maxage=2592000",
        "access-control-allow-origin": "*",
        "x-lazo": "tied-together",
      }});
      await caches.default.put(cacheKey, resp.clone());
      return resp;
    }

    // LIVE COUPLE SITES: /w/{slug} → hydrated template (shadows any old static files)
    // JC-LAZO-WORKER-0913-PAY-001: the couple's booking page, no login
    const fMatch = url.pathname.match(/^\/f\/([A-Za-z0-9_-]{6,80})\/?$/);
    if (fMatch && req.method === "GET") return bookingPage(fMatch[1], url.searchParams.get("t") || "");
    // JC-LAZO-WORKER-0913-LEAD-001: embeddable lead form + hosted lead page
    if (url.pathname === "/embed/lead.js") return new Response(LEAD_JS, { headers: { "content-type": TYPES.js, "cache-control": "public, max-age=3600, s-maxage=86400", "access-control-allow-origin": "*" } });
    const leadMatch = url.pathname.match(/^\/lead\/([A-Za-z0-9_-]{3,120})\/?$/);
    if (leadMatch && req.method === "GET") return leadPage(leadMatch[1], url.searchParams.get("k") || "");
    // JC-LAZO-WORKER-0913-BOOK-001: consult scheduler
    const bookMatch = url.pathname.match(/^\/book\/([A-Za-z0-9_-]{3,120})\/?$/);
    if (bookMatch && req.method === "GET") return bookPage(bookMatch[1], url.searchParams.get("inq") || "", url.searchParams.get("type") || "");
    if (url.pathname === "/sitemap-couples.xml" && req.method === "GET") return couplesSitemap();
    if (url.pathname === "/api/couples" && req.method === "GET") return couplesSearch(url);
    // JC-LAZO-WORKER-0929-GUESTPHOTOS-001
    const gp = await guestPhotosRoute(url, req, env);
    if (gp) return gp;
    // JC-LAZO-WORKER-0929-LIVE-001
    const wxMatch = url.pathname.match(/^\/api\/w\/([a-z0-9-]{1,80})\/weather\/?$/);
    if (wxMatch && req.method === "GET") return weatherRoute(wxMatch[1], env, venuePoint);
    if (url.pathname === "/api/translate") return translateRoute(req, env);
    const dbMatch = url.pathname.match(/^\/api\/w\/([a-z0-9-]{1,80})\/day-before\/?$/);
    if (dbMatch) return dayBeforeRoute(dbMatch[1], req, env, venuePoint);
    // JC-LAZO-WORKER-0930-FSAUTH
    const gdMatch = url.pathname.match(/^\/api\/w\/([a-z0-9-]{1,80})\/(guestbook|chapters|seat|room|invite\/[A-Za-z0-9_-]{4,120})\/?$/);
    if (gdMatch && req.method === "GET") return siteDataRoute(gdMatch[1], gdMatch[2], url, req);
    const cardsMatch = url.pathname.match(/^\/w\/([a-z0-9-]{1,80})\/cards\/?$/);
    if (cardsMatch && req.method === "GET") return (await siteLocked(cardsMatch[1], req)) ? lockedResponse() : cardsPage(cardsMatch[1]);
    const plMatch = url.pathname.match(/^\/w\/([a-z0-9-]{1,80})\/playlist\/?$/);
    if (plMatch && req.method === "GET") return (await siteLocked(plMatch[1], req)) ? lockedResponse() : playlistPage(plMatch[1]);
    // JC-LAZO-WORKER-0930-SITEFIX
    const unMatch = url.pathname.match(/^\/w\/([a-z0-9\-]{1,80})\/unlock\/?$/);
    if (unMatch && req.method === "POST") return unlockRoute(unMatch[1], req);
    const wMatch = url.pathname.match(/^\/w\/([a-z0-9\-]{1,80})\/?$/);
    if (wMatch && req.method === "GET") {
      const resp = await renderCoupleSite(wMatch[1], env, req);
      if (resp) return resp;
      const nf = await env.SITE.get("404.html");
      return new Response(nf ? nf.body : "Site not found", {
        status: 404, headers: { "content-type": TYPES.html } });
    }

    let key = decodeURIComponent(url.pathname).replace(/^\/+/, "");
    if (key === "" ) key = "index.html";
    else if (key.endsWith("/")) key += "index.html";
    else if (!key.includes(".")) key += "/index.html";

    // JC-LAZO-INBOX-0916-003: nothing under a private prefix is EVER servable.
    // Everything below turns a URL path straight into a bucket key, so anything
    // written into this bucket is a public URL unless something stops it first.
    // Form submissions live in the same bucket as the site, which made
    // /contact/<id>.json a readable file containing a real person's name, email
    // and message. This is the general rule that `_gone.json` and `_moved.json`
    // were one-off special cases of:
    //   _*        our own manifests and the form inbox (_inbox/)
    //   signups/  the early-access and claim-interest endpoints write here
    // Both 404 exactly as a missing key would, so nothing confirms they exist.
    // JC-LAZO-GONE-0903 / JC-LAZO-MOVED-0916-001 relied on the two checks this
    // replaces: the manifests must not be served as duplicate content either.
    if (key.startsWith("_") || key.startsWith("signups/"))
      return new Response("Not found", { status: 404, headers: { "x-robots-tag": "noindex, nofollow" } });
    if (key.endsWith("/index.html")) {
      const moved = await loadMoved(env);
      const from = "/" + key.slice(0, -"index.html".length);
      const to = moved[from];
      if (to && to !== from) {
        return new Response(null, { status: 301, headers: {
          "location": to,
          "cache-control": "public, max-age=3600, s-maxage=86400",
          "x-lazo": "moved" } });
      }
    }
    const gm = key.match(/^([a-z0-9-]+)\/[a-z0-9-]+\/([a-z0-9-]+)\/index\.html$/);
    if (gm) {
      const gone = await loadGone(env);
      if (gone.has(`${gm[1]}|${gm[2]}`))
        return new Response(GONE_HTML, { status: 410,
          headers: { "content-type": TYPES.html, "cache-control": "public, max-age=3600" } });
    }
    let obj = await env.SITE.get(key);
    if (!obj) {
      obj = await env.SITE.get("404.html");
      if (!obj) return new Response("Not found", { status: 404 });
      return new Response(obj.body, { status: 404, headers: { "content-type": TYPES.html } });
    }
    const ext = key.split(".").pop();
    const cache = key.startsWith("assets/")
      ? "public, max-age=86400, s-maxage=604800"
      : "public, max-age=300, s-maxage=3600";
    const resp = new Response(obj.body, { headers: {
      "content-type": TYPES[ext] || "application/octet-stream",
      "cache-control": cache,
      "access-control-allow-origin": "*",
      // JC-LAZO-MKT-0930: the headers every scanner asks for on a public site
      "strict-transport-security": "max-age=31536000; includeSubDomains",
      "x-content-type-options": "nosniff",
      "referrer-policy": "strict-origin-when-cross-origin",
      "permissions-policy": "camera=(), microphone=(), payment=()",
      "x-lazo": "tied-together",
    }});
    // The home page follows the visitor (no-op for anyone far from a live metro).
    // Every HTML page then gets the tracker tag appended to <head>.
    // JC-LAZO-CONSENT-1004: the country/region hint goes on every page (pixel consent gate).
    return withTracker(req, withRegion(req, key === "index.html" ? withGeo(req, resp) : resp));
  }
};

// JC-LAZO-WORKER-0915-NEARBY-001: things to do around the venue.
// Three groups a wedding guest actually needs, in the order they need them.
const NEARBY_GROUPS = [
  { key: "eat", label: "Eat & drink", types: ["restaurant"], take: 6, radius: 8000 },
  { key: "coffee", label: "Coffee & breakfast", types: ["cafe", "bakery", "breakfast_restaurant"], take: 4, radius: 6000 },
  { key: "do", label: "Things to do", types: ["tourist_attraction", "museum", "park", "art_gallery", "hiking_area"], take: 6, radius: 16000 },
];
const NEARBY_TTL = 25 * 24 * 3600 * 1000;   // Google allows 30 days; stay under it
const NEARBY_MASK = [
  "places.id", "places.displayName", "places.formattedAddress", "places.location",
  "places.rating", "places.userRatingCount", "places.priceLevel",
  "places.googleMapsUri", "places.primaryType", "places.primaryTypeDisplayName",
  "places.editorialSummary",
].join(",");

// What a place mainly IS. Google lists every type a place contains, so a resort
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
// worth at most +0.16, so it breaks ties and nothing more. Google's editorial
// summary says "chain" when a place is one, and a guest who flew in wants the
// place they cannot get at home.
function nbScore(p) {
  const chain = /\bchains?\b/i.test(p.blurb || "") ? 0.3 : 0;
  return p.rating + Math.min(Math.log10(Math.max(p.votes, 1)), 4) * 0.04 - chain;
}

// "Butters Pancakes & Cafe" and "Butters Pancakes and Cafe #2" are one business.
function nbName(n) {
  return String(n || "").toLowerCase()
    .replace(/\b(the|a|an|and)\b/g, " ")
    .replace(/[^a-z0-9]+/g, " ").trim();
}

// One clause is enough under a name; Google's summaries run long.
function nbTrim(t) {
  t = String(t || "").trim();
  if (t.length <= 98) return t;
  const cut = t.slice(0, 98);
  return cut.slice(0, Math.max(cut.lastIndexOf(" "), 60)).replace(/[,;:]$/, "") + "\u2026";
}

function milesBetween(a, b) {
  const R = 3958.8, rad = (d) => d * Math.PI / 180;
  const dLat = rad(b.lat - a.lat), dLng = rad(b.lng - a.lng);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.min(1, Math.sqrt(h)));
}

async function placesPost(path, body, key, mask) {
  const r = await fetch("https://places.googleapis.com/v1/places:" + path, {
    method: "POST",
    headers: { "content-type": "application/json", "X-Goog-Api-Key": key, "X-Goog-FieldMask": mask },
    body: JSON.stringify(body),
  });
  if (!r.ok) return null;
  return r.json();
}

// The venue, as a point. One text search, and only when we have no cache.
async function venuePoint(name, address, key) {
  const q = [name, address].filter(Boolean).join(", ").trim();
  if (q.length < 6) return null;
  const j = await placesPost("searchText", { textQuery: q, pageSize: 1 }, key,
    "places.location,places.formattedAddress");
  const p = j && j.places && j.places[0];
  if (!p || !p.location) return null;
  return { lat: p.location.latitude, lng: p.location.longitude };
}

function shapePlace(p, at) {
  const loc = p.location ? { lat: p.location.latitude, lng: p.location.longitude } : null;
  const PRICE = { PRICE_LEVEL_INEXPENSIVE: "$", PRICE_LEVEL_MODERATE: "$$",
                  PRICE_LEVEL_EXPENSIVE: "$$$", PRICE_LEVEL_VERY_EXPENSIVE: "$$$$" };
  return {
    id: p.id || "",
    type: p.primaryType || "",
    name: (p.displayName && p.displayName.text) || "",
    kind: (p.primaryTypeDisplayName && p.primaryTypeDisplayName.text) || "",
    blurb: (p.editorialSummary && p.editorialSummary.text) || "",
    rating: p.rating || 0,
    votes: p.userRatingCount || 0,
    price: PRICE[p.priceLevel] || "",
    miles: loc && at ? Math.round(milesBetween(at, loc) * 10) / 10 : null,
    maps: p.googleMapsUri || "",
  };
}

async function nearbyBuild(at, key) {
  const groups = [];
  const seen = new Set();            // no place appears in two groups
  for (const g of NEARBY_GROUPS) {
    const j = await placesPost("searchNearby", {
      includedTypes: g.types,
      maxResultCount: 20,
      rankPreference: "POPULARITY",
      locationRestriction: { circle: { center: { latitude: at.lat, longitude: at.lng }, radius: g.radius } },
    }, key, NEARBY_MASK);
    const raw = (j && j.places) || [];
    const ok = raw
      .map((p) => shapePlace(p, at))
      .filter((p) => p.name && p.rating >= 4.2 && p.votes >= 80 && nbFits(g.key, p.type))
      .filter((p) => !seen.has(nbName(p.name)));
    // one branch per business: the one a guest can walk to
    const byName = new Map();
    for (const p of ok) {
      const k = nbName(p.name);
      const had = byName.get(k);
      if (!had || (p.miles ?? 99) < (had.miles ?? 99)) byName.set(k, p);
    }
    const items = [];
    const perType = new Map();
    for (const p of [...byName.values()].sort((a, b) => nbScore(b) - nbScore(a))) {
      const used = perType.get(p.type) || 0;
      if (used >= 2) continue;            // never six steakhouses
      perType.set(p.type, used + 1);
      p.blurb = nbTrim(p.blurb);
      seen.add(nbName(p.name));
      items.push(p);
      if (items.length >= g.take) break;
    }
    for (const p of items) { delete p.id; delete p.type; }
    if (items.length) groups.push({ key: g.key, label: g.label, items });
  }
  return groups;
}

const NEARBY_DEMO = [
  { key: "eat", label: "Eat & drink", items: [
    { name: "The Harbor Table", kind: "Seafood", blurb: "Oysters and a long wine list, two streets back from the water.", rating: 4.7, votes: 1240, price: "$$$", miles: 1.2, maps: "" },
    { name: "Casa Verde", kind: "Mexican", blurb: "", rating: 4.6, votes: 860, price: "$$", miles: 2.1, maps: "" },
    { name: "Bar Lucia", kind: "Wine bar", blurb: "", rating: 4.5, votes: 410, price: "$$", miles: 0.8, maps: "" },
  ] },
  { key: "coffee", label: "Coffee & breakfast", items: [
    { name: "Morning Glory Coffee", kind: "Coffee shop", blurb: "", rating: 4.8, votes: 930, price: "$", miles: 0.6, maps: "" },
    { name: "The Flour Room", kind: "Bakery", blurb: "", rating: 4.7, votes: 520, price: "$", miles: 1.4, maps: "" },
  ] },
  { key: "do", label: "Things to do", items: [
    { name: "Old Town Walk", kind: "Historic district", blurb: "An hour on foot, best before the heat.", rating: 4.6, votes: 2100, price: "", miles: 1.9, maps: "" },
    { name: "Ridgeline Trail", kind: "Hiking area", blurb: "", rating: 4.8, votes: 640, price: "", miles: 5.3, maps: "" },
    { name: "The Shelby Museum", kind: "Art museum", blurb: "", rating: 4.5, votes: 380, price: "", miles: 2.7, maps: "" },
  ] },
];

async function nearbyPlaces(url, env) {
  const h = { "content-type": "application/json; charset=utf-8", ...CORS,
              "cache-control": "public, max-age=3600, s-maxage=86400" };
  const slug = (url.searchParams.get("slug") || "").trim().slice(0, 80);
  if (slug === "demo") return new Response(JSON.stringify({ groups: NEARBY_DEMO, demo: true }), { headers: h });
  if (!/^[a-z0-9-]{1,80}$/.test(slug)) return new Response('{"groups":[]}', { headers: h });

  const f = await fsDoc("weddingSites", slug);
  if (!f) return new Response('{"groups":[]}', { headers: h });
  const g = (k) => fsVal(f[k]);
  if (g("nearbyOn") === false) return new Response('{"groups":[]}', { headers: h });
  const address = (g("venueAddress") || "").toString();
  const vname = (g("venueName") || "").toString();
  if (!address && !vname) return new Response('{"groups":[]}', { headers: h });

  const key = env.PLACES_API_KEY;
  if (!key) return new Response('{"groups":[]}', { headers: h });

  // The venue point, remembered per site so we geocode an address once.
  const ptKey = "nearby/v1/pt/" + slug + ".json";
  let at = null, ptFresh = false;
  try {
    const o = await env.SITE.get(ptKey);
    if (o) {
      const j = await o.json();
      if (j && j.q === address + "|" + vname && j.lat) { at = { lat: j.lat, lng: j.lng }; ptFresh = true; }
    }
  } catch (e) {}
  if (!at) {
    at = await venuePoint(vname, address, key);
    if (!at) return new Response('{"groups":[]}', { headers: h });
  }
  if (!ptFresh) {
    try {
      await env.SITE.put(ptKey, JSON.stringify({ q: address + "|" + vname, lat: at.lat, lng: at.lng }),
        { httpMetadata: { contentType: "application/json" } });
    } catch (e) {}
  }

  // Couples at the same venue share one lookup: ~110m of rounding.
  const cacheKey = `nearby/v3/${at.lat.toFixed(3)}_${at.lng.toFixed(3)}.json`;
  let groups = null;
  try {
    const o = await env.SITE.get(cacheKey);
    if (o) {
      const j = await o.json();
      if (j && Array.isArray(j.groups) && Date.now() - (j.at || 0) < NEARBY_TTL) groups = j.groups;
    }
  } catch (e) {}
  if (!groups) {
    groups = await nearbyBuild(at, key);
    try {
      await env.SITE.put(cacheKey, JSON.stringify({ at: Date.now(), groups }),
        { httpMetadata: { contentType: "application/json" } });
    } catch (e) {}
  }
  return new Response(JSON.stringify({ groups }), { headers: h });
}

// JC-LAZO-WORKER-0912-MUSIC-002: song search for the couple app's Music page.
// Deezer first (shared-IP friendly, 30s MP3 previews), iTunes second (429s from
// Workers' shared egress). Both are reshaped to the iTunes field names the
// widget reads, so the app never knows which one answered.
async function musicSearch(url) {
  const q = (url.searchParams.get("q") || "").trim().slice(0, 120);
  const h = { "content-type": "application/json; charset=utf-8", "access-control-allow-origin": "*", "cache-control": "public, max-age=86400" };
  if (q.length < 2) return new Response('{"results":[]}', { headers: h });
  const cache = caches.default;
  const key = new Request("https://meetlazo.com/music/search?q=" + encodeURIComponent(q.toLowerCase()), { method: "GET" });
  const hit = await cache.match(key);
  if (hit) return hit;
  const ua = { accept: "application/json", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36" };
  let results = null, upstream = 0;
  try {
    const d = await fetch("https://api.deezer.com/search?q=" + encodeURIComponent(q) + "&limit=25", { headers: ua });
    upstream = d.status;
    if (d.ok) {
      const j = await d.json();
      if (Array.isArray(j.data)) results = j.data.map(t => ({
        trackId: "dz" + t.id, trackName: t.title, artistName: t.artist && t.artist.name || "",
        collectionName: t.album && t.album.title || "", artworkUrl100: t.album && (t.album.cover_medium || t.album.cover) || "",
        previewUrl: t.preview || "", trackTimeMillis: (t.duration || 0) * 1000, trackViewUrl: t.link || "", explicit: !!t.explicit_lyrics }));
    }
  } catch (e) {}
  if (!results || !results.length) {
    try {
      const a = await fetch("https://itunes.apple.com/search?term=" + encodeURIComponent(q) + "&entity=song&limit=25&country=US", { headers: ua, redirect: "follow" });
      upstream = a.status;
      if (a.ok) { const j = await a.json(); if (Array.isArray(j.results)) results = j.results.map(r => ({ ...r, explicit: r.trackExplicitness === "explicit" })); }
    } catch (e) {}
  }
  if (!results) return new Response(JSON.stringify({ results: [], upstream }), { status: 502, headers: { ...h, "cache-control": "no-store" } });
  const res = new Response(JSON.stringify({ results }), { headers: h });
  await cache.put(key, res.clone());
  return res;
}
// JC-LAZO-WORKER-0912-MUSIC-003: preview relay, guest song requests.
const PREVIEW_HOSTS = [/\.dzcdn\.net$/i, /\.apple\.com$/i, /\.mzstatic\.com$/i];
async function musicPreview(url, req) {
  const u = url.searchParams.get("u") || "";
  let target;
  try { target = new URL(u); } catch (e) { return new Response("bad url", { status: 400 }); }
  if (target.protocol !== "https:" || !PREVIEW_HOSTS.some(rx => rx.test(target.hostname))) {
    return new Response("host not allowed", { status: 403 });
  }
  const h = { "access-control-allow-origin": "*", "access-control-expose-headers": "content-length, content-range, accept-ranges", "cache-control": "public, max-age=604800" };
  const range = req.headers.get("range");
  const up = await fetch(target.toString(), { headers: range ? { range } : {}, cf: { cacheEverything: true, cacheTtl: 604800 } });
  if (!up.ok && up.status !== 206) return new Response("upstream " + up.status, { status: 502, headers: h });
  const out = new Headers(h);
  for (const k of ["content-type", "content-length", "content-range", "accept-ranges"]) {
    const v = up.headers.get(k); if (v) out.set(k, v);
  }
  return new Response(up.body, { status: up.status, headers: out });
}

function escM(x) { return String(x || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }

async function requestPage(slug) {
  const site = await fsDoc("weddingSites", slug);
  if (!site) return new Response("Not found", { status: 404 });
  const names = site.names || site.coupleNames || "the couple";
  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>Request a song - ${escM(names)}</title>
<style>
body{margin:0;background:#FAF6F0;color:#241E2B;font-family:Helvetica,Arial,sans-serif}
.wrap{max-width:460px;margin:0 auto;padding:36px 20px 60px}
h1{font-family:Georgia,serif;font-weight:600;font-size:34px;color:#52284F;margin:0 0 6px;line-height:1.05}
p{color:#6B5F72;font-size:14px;line-height:1.5;margin:0 0 22px}
label{display:block;font-size:11px;letter-spacing:1.5px;text-transform:uppercase;color:#52284F;font-weight:700;margin:14px 0 6px}
input,textarea{width:100%;box-sizing:border-box;border:1px solid #E6D6B8;border-radius:12px;padding:12px 13px;font-size:15px;background:#FFFDF9;color:#241E2B;font-family:inherit}
input:focus,textarea:focus{outline:none;border-color:#D9B77C;box-shadow:0 0 0 3px rgba(217,183,124,.25)}
textarea{min-height:70px;resize:vertical}
button{margin-top:20px;width:100%;border:0;border-radius:12px;padding:14px;background:#52284F;color:#FAF6F0;font-size:15px;font-weight:700;cursor:pointer}
button:disabled{opacity:.6}
.ok{display:none;text-align:center;padding:30px 0}
.ok h2{font-family:Georgia,serif;color:#52284F;font-weight:600;font-size:28px;margin:0 0 8px}
.err{color:#B04343;font-size:13px;margin-top:10px;display:none}
.hp{position:absolute;left:-9999px}
.foot{margin-top:34px;text-align:center;font-size:11px;color:#6B5F72}.foot a{color:#52284F}
</style></head><body><div class="wrap">
<div id="form"><h1>Request a song</h1><p>What gets you on the dance floor? ${escM(names)} will pass the good ones to the DJ.</p>
<label>Your name</label><input id="guest" maxlength="80" placeholder="Aunt May">
<label>Song</label><input id="song" maxlength="200" placeholder="September" required>
<label>Artist</label><input id="artist" maxlength="120" placeholder="Earth, Wind &amp; Fire">
<label>Why this one? (optional)</label><textarea id="note" maxlength="300" placeholder="It was playing when we met them."></textarea>
<input class="hp" id="website" tabindex="-1" autocomplete="off">
<button id="go">Send the request</button><div class="err" id="err"></div></div>
<div class="ok" id="ok"><h2>Sent!</h2><p>Want to request another? <a href="#" id="again" style="color:#52284F">Add one more</a></p></div>
<div class="foot">Planned on <a href="https://meetlazo.com">Lazo</a></div></div>
<script>
const $=id=>document.getElementById(id);
$("go").onclick=async()=>{const song=$("song").value.trim();if(!song){$("err").style.display="block";$("err").textContent="Which song?";return}
$("go").disabled=true;$("err").style.display="none";
try{const r=await fetch("/api/song-request",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({slug:${JSON.stringify(slug)},guest:$("guest").value.trim(),song,artist:$("artist").value.trim(),note:$("note").value.trim(),website:$("website").value})});
if(!r.ok)throw new Error("x");$("form").style.display="none";$("ok").style.display="block";}
catch(e){$("err").style.display="block";$("err").textContent="That didn't go through - try again in a moment.";$("go").disabled=false}};
$("again").onclick=e=>{e.preventDefault();$("song").value="";$("artist").value="";$("note").value="";$("ok").style.display="none";$("form").style.display="block";$("go").disabled=false};
</script></body></html>`;
  return new Response(html, { headers: { "content-type": TYPES.html, "cache-control": "public, max-age=300" } });
}

async function songRequest(req) {
  let b;
  try { b = await req.json(); } catch (e) { return json({ ok: false }, 400); }
  if (b.website) return json({ ok: true }); // honeypot: pretend
  const slug = String(b.slug || "").toLowerCase();
  if (!/^[a-z0-9-]{1,80}$/.test(slug)) return json({ ok: false }, 400);
  const song = String(b.song || "").trim().slice(0, 200);
  if (!song) return json({ ok: false, error: "song" }, 400);
  const site = await fsDoc("weddingSites", slug);
  const cid = site && (site.coupleUid || site.ownerUid);
  if (!cid) return json({ ok: false }, 404);
  const fields = {
    guest: { stringValue: String(b.guest || "").trim().slice(0, 80) },
    song: { stringValue: song },
    artist: { stringValue: String(b.artist || "").trim().slice(0, 120) },
    note: { stringValue: String(b.note || "").trim().slice(0, 300) },
    status: { stringValue: "new" },
    source: { stringValue: "site" },
    createdAt: { timestampValue: new Date().toISOString() },
  };
  const r = await fetch(`https://firestore.googleapis.com/v1/projects/${PROJECT}/databases/(default)/documents/couples/${encodeURIComponent(cid)}/musicRequests`, {
    method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ fields }),
  });
  if (!r.ok) return json({ ok: false, upstream: r.status }, 502);
  return json({ ok: true });
}

// JC-LAZO-WORKER-0913-PAY-001 ---------------------------------------------
const FILE_VIEW = "https://us-central1-lazo-513ec.cloudfunctions.net/fileView";
const PAY_CHECKOUT = "https://us-central1-lazo-513ec.cloudfunctions.net/payCheckout";
const escF = (t) => String(t == null ? "" : t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const moneyF = (n) => "$" + (Math.round((Number(n) || 0) * 100) / 100).toLocaleString("en-US", { maximumFractionDigits: 2 });
const dateF = (iso) => { if (!iso) return ""; const d = new Date(iso); return isNaN(d) ? "" : d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }); };

async function bookingPage(inquiryId, token) {
  const noindex = { "content-type": TYPES.html, "cache-control": "no-store", "x-robots-tag": "noindex" };
  if (!token) return new Response(shell("This link is missing its key", "<p>Ask your vendor to resend the booking link from Lazo.</p>"), { status: 400, headers: noindex });
  let r;
  try { r = await fetch(`${FILE_VIEW}?inquiry=${encodeURIComponent(inquiryId)}&t=${encodeURIComponent(token)}`, { headers: { accept: "application/json" } }); }
  catch (e) { return new Response(shell("Lazo is catching its breath", "<p>Try again in a minute.</p>"), { status: 502, headers: noindex }); }
  if (r.status === 403) return new Response(shell("This link has expired", "<p>Your vendor may have sent a newer one - check your messages, or ask them to resend it.</p>"), { status: 403, headers: noindex });
  if (!r.ok) return new Response(shell("Booking not found", "<p>Ask your vendor to resend the booking link from Lazo.</p>"), { status: 404, headers: noindex });
  const d = await r.json();
  const v = d.vendor || {}, c = d.couple || {};
  const primary = /^#[0-9a-f]{6}$/i.test(v.primary || "") ? v.primary : "#52284F";
  const accent = /^#[0-9a-f]{6}$/i.test(v.accent || "") ? v.accent : "#D9B77C";
  const invoices = Array.isArray(d.invoices) ? d.invoices : [];
  const open = invoices.filter((i) => i.status === "sent");
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const plan = d.paymentPlan;

  const proposal = d.proposal ? `
  <section class="card">
    <div class="eyebrow">Your proposal</div>
    <h2>${escF(d.proposal.title || "Proposal")}</h2>
    <div class="big">${moneyF(d.proposal.price)}</div>
    ${Array.isArray(d.proposal.includes) && d.proposal.includes.length ? `<ul class="inc">${d.proposal.includes.map((x) => `<li>${escF(typeof x === "string" ? x : (x && x.label) || "")}</li>`).join("")}</ul>` : ""}
    ${d.proposal.note ? `<p class="note">${escF(d.proposal.note)}</p>` : ""}
    <div class="pill ${d.proposal.status === "accepted" ? "ok" : ""}">${d.proposal.status === "accepted" ? "Accepted" : d.proposal.status === "declined" ? "Declined" : "Awaiting your answer - reply in Lazo"}</div>
  </section>` : "";

  const contract = d.contract ? `
  <section class="card">
    <div class="eyebrow">Agreement</div>
    <h2>${escF(d.contract.title)}</h2>
    ${d.contract.status === "signed"
      ? `<div class="pill ok">Signed ${escF(dateF(d.contract.signedAt))}</div>`
      : `<p class="note">Your agreement is ready to sign. Signing happens inside Lazo so it's stored with your booking.</p><a class="btn ghost" href="https://app.meetlazo.com/dashboard?thread=${escF(inquiryId)}">Review &amp; sign in Lazo</a>`}
  </section>` : "";

  const invRows = invoices.map((i) => {
    const due = i.dueDate ? new Date(i.dueDate) : null;
    const late = i.status === "sent" && due && due < today;
    const idx = i.installmentCount ? ` <span class="muted">${(i.installmentIndex || 0) + 1} of ${i.installmentCount}</span>` : "";
    const when = i.status === "paid" ? `Paid ${dateF(i.paidAt)}` : due ? `${late ? "Was due" : "Due"} ${dateF(i.dueDate)}` : "Due on receipt";
    const pay = i.status === "sent" ? `
      <form class="pay" data-inv="${escF(i.id)}" data-tip="${i.tipAllowed ? "1" : "0"}">
        ${i.tipAllowed ? `<label class="tip">Add a tip <span class="muted">(optional)</span><input name="tip" type="number" min="0" step="1" placeholder="0"></label>` : ""}
        <button class="btn" type="submit">Pay ${moneyF(i.total)}</button>
      </form>` : "";
    return `<div class="inv ${i.status} ${late ? "late" : ""}">
      <div class="inv-l"><div class="inv-t">${escF(i.title)}${idx}</div><div class="inv-w">${when}</div>
        ${Array.isArray(i.lineItems) && i.lineItems.length > 1 ? `<div class="lines">${i.lineItems.map((l) => `<span>${escF(l.label)} - ${moneyF(l.amount)}</span>`).join("")}</div>` : ""}</div>
      <div class="inv-r"><div class="inv-a">${moneyF(i.total)}</div>${i.status === "paid" ? `<div class="pill ok small">Paid</div>` : i.status === "refunded" ? `<div class="pill small">Refunded</div>` : ""}</div>
      ${pay}
    </div>`;
  }).join("");

  const links = (Array.isArray(d.paymentLinks) ? d.paymentLinks : []).filter((l) => l && l.url).map((l) => `<a class="btn ghost small" href="${escF(l.url)}" target="_blank" rel="noopener">${escF(l.label || "Pay")}</a>`).join("");

  const money = `
  <section class="card">
    <div class="eyebrow">Payments</div>
    ${plan && plan.total ? `<div class="prog"><div class="bar"><span style="width:${Math.min(100, Math.round(((plan.paid || 0) / plan.total) * 100))}%"></span></div><div class="prog-t">${moneyF(plan.paid || 0)} of ${moneyF(plan.total)} paid${plan.nextDue ? ` · next ${dateF(plan.nextDue._seconds ? new Date(plan.nextDue._seconds * 1000).toISOString() : plan.nextDue)}` : ""}</div></div>` : ""}
    ${invoices.length ? invRows : `<p class="note">Nothing to pay yet.</p>`}
    ${links ? `<div class="links"><div class="muted">Other ways to pay</div>${links}</div>` : ""}
    ${open.length ? `<p class="fine">Card payments go straight to ${escF(v.name || "your vendor")}${d.processor === "whop" ? " through Whop" : d.processor === "stripe" ? " through Stripe" : d.processor === "square" ? " through Square" : ""}. Lazo never holds your money.</p>` : ""}
  </section>`;

  const body = `
  <header class="hero" ${v.coverUrl ? `style="background-image:linear-gradient(rgba(36,30,43,.35),rgba(36,30,43,.75)),url('https://wsrv.nl/?url=${encodeURIComponent(v.coverUrl)}&w=1400&q=70')"` : ""}>
    ${v.logoUrl ? `<img class="logo" src="https://wsrv.nl/?url=${encodeURIComponent(v.logoUrl)}&w=160&h=160&fit=contain" alt="">` : ""}
    <div class="eyebrow light">${escF(v.category || "Your booking")}</div>
    <h1>${escF(v.name || "Your vendor")}</h1>
    <p class="light">${escF(c.name ? `For ${c.name}` : "Your booking")}${c.weddingDate ? ` · ${escF(dateF(c.weddingDate))}` : ""}${c.venue ? ` · ${escF(c.venue)}` : ""}</p>
  </header>
  <main>${proposal}${contract}${money}
  <p class="foot">Questions? <a href="https://app.meetlazo.com/dashboard?thread=${escF(inquiryId)}">Message ${escF(v.name || "your vendor")} on Lazo</a>${v.email ? ` or email <a href="mailto:${escF(v.email)}">${escF(v.email)}</a>` : ""}.</p>
  </main>
  <script>
  const INQ=${JSON.stringify(inquiryId)};
  document.querySelectorAll("form.pay").forEach(f=>{f.addEventListener("submit",async e=>{e.preventDefault();const b=f.querySelector("button");b.disabled=true;const t=b.textContent;b.textContent="Opening checkout…";
    const tip=f.dataset.tip==="1"?Math.max(0,Number((f.querySelector("input[name=tip]")||{}).value||0)):0;
    try{const r=await fetch(PAY+"?inquiry="+encodeURIComponent(INQ)+"&invoice="+encodeURIComponent(f.dataset.inv)+"&tip="+tip);const j=await r.json();if(j&&j.url){location.href=j.url;return;}throw new Error(j&&j.error||"x");}
    catch(err){b.disabled=false;b.textContent=t;alert("Couldn't open checkout - try again in a moment.");}});});
  </script>`;
  return new Response(shell(`${v.name || "Your booking"} - Lazo`, body, primary, accent, true), { headers: noindex });
}

function shell(title, inner, primary = "#52284F", accent = "#D9B77C", full = false) {
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>${escF(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500&display=swap" rel="stylesheet">
<style>
:root{--p:${primary};--a:${accent};--ink:#241E2B;--muted:#6B5F72;--ivory:#FAF6F0;--card:#FFFDF9;--line:#E6D6B8}
*{box-sizing:border-box}body{margin:0;background:var(--ivory);color:var(--ink);font-family:Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}
h1,h2{font-family:"Cormorant Garamond",Georgia,serif;font-weight:600;margin:0}
h1{font-size:44px;line-height:1;color:#fff}h2{font-size:26px;color:var(--p);margin-bottom:4px}
.hero{background:var(--p);background-size:cover;background-position:center;padding:46px 22px 34px;text-align:center}
.logo{width:72px;height:72px;border-radius:16px;background:#fff;object-fit:contain;margin-bottom:14px;box-shadow:0 6px 24px rgba(0,0,0,.25)}
.eyebrow{font-size:10.5px;letter-spacing:2px;text-transform:uppercase;font-weight:800;color:var(--p);margin-bottom:8px}.eyebrow.light{color:var(--a)}
.light{color:rgba(255,255,255,.85);margin:8px 0 0;font-size:14px}
main{max-width:560px;margin:-18px auto 60px;padding:0 14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:20px;margin-bottom:14px}
.big{font-size:32px;font-weight:800;color:var(--ink);margin:6px 0 10px}
.inc{margin:0 0 10px;padding-left:18px;color:var(--ink);font-size:14px;line-height:1.55}
.note{color:var(--muted);font-size:14px;line-height:1.5;margin:6px 0 10px}
.fine{color:var(--muted);font-size:12px;line-height:1.5;margin:12px 0 0}
.pill{display:inline-block;padding:5px 11px;border-radius:999px;font-size:11px;font-weight:800;letter-spacing:1px;text-transform:uppercase;background:rgba(82,40,79,.08);color:var(--p)}
.pill.ok{background:rgba(46,139,107,.14);color:#2E8B6B}.pill.small{padding:3px 8px;font-size:9.5px}
.btn{display:inline-block;border:0;border-radius:12px;padding:13px 18px;background:var(--p);color:#fff;font-weight:800;font-size:15px;cursor:pointer;text-decoration:none;text-align:center}
.btn.ghost{background:transparent;color:var(--p);border:1.5px solid var(--p)}.btn.small{padding:8px 12px;font-size:13px;margin:6px 6px 0 0}
.btn[disabled]{opacity:.6}
.inv{display:grid;grid-template-columns:1fr auto;gap:6px 12px;padding:14px 0;border-top:1px solid var(--line)}.inv:first-of-type{border-top:0}
.inv-t{font-weight:700;font-size:15px}.inv-w{color:var(--muted);font-size:12.5px;margin-top:2px}.inv.late .inv-w{color:#B04343;font-weight:700}
.inv-a{font-weight:800;font-size:17px;text-align:right}.inv-r{text-align:right}.inv.paid .inv-t{color:var(--muted)}
.lines{margin-top:6px;font-size:12px;color:var(--muted)}.lines span{display:block}
.pay{grid-column:1/-1;display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap;margin-top:4px}.pay .btn{flex:1;min-width:160px}
.tip{font-size:12px;color:var(--muted);display:flex;flex-direction:column;gap:4px}.tip input{width:110px;border:1px solid var(--line);border-radius:10px;padding:10px;font-size:15px;background:#fff}
.prog{margin:4px 0 14px}.bar{height:8px;border-radius:999px;background:rgba(82,40,79,.1);overflow:hidden}.bar span{display:block;height:100%;background:var(--p)}.prog-t{font-size:12.5px;color:var(--muted);margin-top:6px}
.links{margin-top:12px}.muted{color:var(--muted);font-size:12px}
.foot{text-align:center;color:var(--muted);font-size:12.5px;line-height:1.6}.foot a{color:var(--p)}
${full ? "" : "main{margin-top:40px}"}
</style></head><body>${full ? inner : `<main><section class="card"><h2>${escF(title)}</h2>${inner}</section><p class="foot"><a href="https://meetlazo.com">Lazo</a></p></main>`}<script>const PAY=${JSON.stringify(PAY_CHECKOUT)};</script></body></html>`;
}

// JC-LAZO-WORKER-0913-LEAD-001 --------------------------------------------
const LEAD_INGEST = "https://us-central1-lazo-513ec.cloudfunctions.net/leadIngest";

async function leadPage(vendorId, key) {
  const v = await fsDoc("vendors", vendorId);
  const name = v ? (fsVal(v.name) || "this vendor") : "this vendor";
  const form = v && v.leadForm ? fsVal(v.leadForm) : null;
  if (!v || !form || !key || form.key !== key || form.enabled === false) {
    return new Response(`<!doctype html><html><head><meta charset="utf-8"><meta name="robots" content="noindex"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Lazo</title></head><body style="font-family:system-ui;max-width:32rem;margin:4rem auto;padding:0 1rem;color:#241E2B"><h1 style="font-weight:600">This form isn't live</h1><p>Ask the vendor for their current link, or find them on <a href="https://meetlazo.com" style="color:#52284F">Lazo</a>.</p></body></html>`, { status: 404, headers: { "content-type": TYPES.html, "cache-control": "no-store" } });
  }
  const cover = fsVal(v.coverUrl) || "";
  const b = brandOf(v);
  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow">
<title>Inquire - ${escF(name)}</title>
<style>body{margin:0;background:#FAF6F0;font-family:${b.font === "serif" ? "Georgia,serif" : "Helvetica,Arial,sans-serif"};color:#241E2B}
.hero{background:${b.primary} ${cover ? `url('https://wsrv.nl/?url=${encodeURIComponent(cover)}&w=1400&q=70') center/cover` : ""};padding:52px 20px 40px;text-align:center;color:#fff}
.hero img.logo{width:64px;height:64px;border-radius:14px;background:#fff;object-fit:contain;margin-bottom:12px}
.hero h1{font-family:Georgia,serif;font-weight:600;font-size:38px;margin:0;line-height:1.05}.hero p{margin:8px 0 0;opacity:.85;font-size:14px}
main{max-width:520px;margin:-18px auto 60px;padding:0 14px}.foot{text-align:center;font-size:11.5px;color:#6B5F72;margin-top:24px}.foot a{color:#52284F}</style></head>
<body><header class="hero">${b.logoUrl ? `<img class="logo" src="https://wsrv.nl/?url=${encodeURIComponent(b.logoUrl)}&w=128&h=128&fit=contain" alt="">` : ""}<h1>${escF(name)}</h1><p>Tell us about your day - we'll get right back to you.</p></header>
<main><script src="https://meetlazo.com/embed/lead.js" data-vendor="${escF(vendorId)}" data-key="${escF(key)}" data-heading=" " data-accent="${b.primary}"></script>
<p class="foot">Powered by <a href="https://meetlazo.com">Lazo</a></p></main></body></html>`;
  return new Response(html, { headers: { "content-type": TYPES.html, "cache-control": "no-store", "x-robots-tag": "noindex" } });
}

const LEAD_JS = `(function(){
var s=document.currentScript;if(!s)return;var V=s.getAttribute("data-vendor")||"",K=s.getAttribute("data-key")||"";if(!V||!K)return;
var accent=s.getAttribute("data-accent")||"#52284F",heading=s.getAttribute("data-heading"),btn=s.getAttribute("data-button")||"Send inquiry",redirect=s.getAttribute("data-redirect")||"";
var host=document.createElement("div");host.className="lazo-lead";s.parentNode.insertBefore(host,s);var r=host.attachShadow({mode:"open"});
var q=new URLSearchParams(location.search),utm={source:q.get("utm_source")||"",medium:q.get("utm_medium")||"",campaign:q.get("utm_campaign")||"",content:q.get("utm_content")||"",term:q.get("utm_term")||""};
r.innerHTML='<style>:host{all:initial;display:block;font-family:-apple-system,Helvetica,Arial,sans-serif;color:#241E2B}*{box-sizing:border-box}.c{background:#FFFDF9;border:1px solid #E6D6B8;border-radius:18px;padding:22px;max-width:520px}h3{margin:0 0 4px;font:600 22px Georgia,serif;color:'+accent+'}p{margin:0 0 14px;font-size:13px;color:#6B5F72;line-height:1.45}label{display:block;font-size:11px;letter-spacing:1.2px;text-transform:uppercase;font-weight:700;color:'+accent+';margin:10px 0 5px}input,textarea,select{width:100%;border:1px solid #E6D6B8;border-radius:11px;padding:11px 12px;font-size:15px;background:#fff;color:#241E2B;font-family:inherit}input:focus,textarea:focus{outline:none;border-color:'+accent+';box-shadow:0 0 0 3px rgba(82,40,79,.15)}textarea{min-height:88px;resize:vertical}.row{display:grid;grid-template-columns:1fr 1fr;gap:10px}@media(max-width:480px){.row{grid-template-columns:1fr}}.ck{display:flex;gap:8px;align-items:flex-start;font-size:12px;color:#6B5F72;margin-top:12px;line-height:1.4}.ck input{width:auto;margin-top:2px}button{margin-top:16px;width:100%;border:0;border-radius:12px;padding:14px;background:'+accent+';color:#fff;font-size:15px;font-weight:700;cursor:pointer}button:disabled{opacity:.6}.err{color:#B04343;font-size:13px;margin-top:8px;display:none}.ok{display:none;text-align:center;padding:26px 0}.ok h3{font-size:26px}.hp{position:absolute;left:-9999px;opacity:0}.pw{margin-top:12px;text-align:center;font-size:10.5px;color:#9A8FA0}.pw a{color:#9A8FA0}</style>'+
'<div class="c"><div id="f">'+(heading===" "?"":'<h3>'+(heading||"Check your date")+'</h3><p>A few details and we\\'ll get right back to you.</p>')+
'<div class="row"><div><label>Your name</label><input id="n" maxlength="120" autocomplete="name" required></div><div><label>Wedding date</label><input id="d" type="date"></div></div>'+
'<div class="row"><div><label>Email</label><input id="e" type="email" maxlength="160" autocomplete="email"></div><div><label>Phone</label><input id="p" type="tel" maxlength="30" autocomplete="tel"></div></div>'+
'<div class="row"><div><label>Venue (if you have one)</label><input id="v" maxlength="160"></div><div><label>Guests</label><input id="g" inputmode="numeric" maxlength="6" placeholder="About how many?"></div></div>'+
'<label>Tell us about your day</label><textarea id="m" maxlength="2000"></textarea>'+
'<input class="hp" id="w" tabindex="-1" autocomplete="off">'+
'<label class="ck" style="text-transform:none;letter-spacing:0;font-weight:400"><input id="s" type="checkbox" checked> Text me back - it\\'s the fastest way to hear from us. Reply STOP anytime.</label>'+
'<button id="b" type="button">'+btn+'</button><div class="err" id="x"></div></div>'+
'<div class="ok" id="ok"><h3>Sent!</h3><p id="okt">We\\'ll be in touch shortly.</p></div>'+
'<div class="pw">Secure inquiry via <a href="https://meetlazo.com" target="_blank" rel="noopener">Lazo</a></div></div>';
function $(i){return r.getElementById(i)}
$("b").onclick=function(){var n=$("n").value.trim(),e=$("e").value.trim(),p=$("p").value.trim(),x=$("x");x.style.display="none";
if(!n){x.textContent="What's your name?";x.style.display="block";return}if(!e&&!p){x.textContent="An email or a phone number so they can reach you.";x.style.display="block";return}
var b=$("b");b.disabled=true;var t=b.textContent;b.textContent="Sending\\u2026";
fetch("${LEAD_INGEST}",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({vendorId:V,key:K,name:n,email:e,phone:p,weddingDate:$("d").value,venue:$("v").value.trim(),guests:$("g").value.trim(),message:$("m").value.trim(),smsOk:$("s").checked,website:$("w").value,page:location.href,referrer:document.referrer,utm:utm})})
.then(function(res){return res.json().then(function(j){if(!res.ok||!j.ok)throw new Error(j&&j.error||"x");return j})})
.then(function(j){try{if(window.fbq)fbq("track","Lead");if(window.gtag)gtag("event","generate_lead")}catch(_){}
var to=redirect||j.redirect;if(to){location.href=to;return}if(j.thanks)$("okt").textContent=j.thanks;$("f").style.display="none";$("ok").style.display="block"})
.catch(function(){b.disabled=false;b.textContent=t;x.textContent="That didn't go through - try again in a moment.";x.style.display="block"})};
})();`;

// JC-LAZO-WORKER-0913-BRAND-001 -------------------------------------------
const HEX = /^#[0-9a-f]{6}$/i;
function brandOf(v) {
  const raw = v && v.brand ? fsVal(v.brand) : null;
  const b = raw && typeof raw === "object" ? raw : {};
  return {
    name: v ? (fsVal(v.name) || "") : "",
    logoUrl: v ? (fsVal(v.logoUrl) || "") : "",
    primary: HEX.test(b.primary || "") ? b.primary : "#52284F",
    accent: HEX.test(b.accent || "") ? b.accent : "#D9B77C",
    font: b.font === "serif" ? "serif" : "sans",
  };
}
async function vendorBrand(vendorId) {
  if (!vendorId) return brandOf(null);
  const v = await fsDoc("vendors", vendorId);
  return brandOf(v);
}
function brandHead(b) {
  return `\n<style>:root{--brand-primary:${b.primary};--brand-accent:${b.accent};--brand-font:${b.font === "serif" ? "Georgia,serif" : "Helvetica,Arial,sans-serif"}}` +
    `.lazo-brand{display:flex;align-items:center;gap:12px;padding:12px 18px;background:${b.primary};color:#fff;font-family:var(--brand-font);font-size:14px}` +
    `.lazo-brand img{width:36px;height:36px;border-radius:9px;background:#fff;object-fit:contain}.lazo-brand b{font-weight:600;letter-spacing:.2px}</style>`;
}
function brandStrip(b) {
  return `\n<div class="lazo-brand">${b.logoUrl ? `<img src="https://wsrv.nl/?url=${encodeURIComponent(b.logoUrl)}&w=72&h=72&fit=contain" alt="">` : ""}<b>${esc(b.name)}</b></div>`;
}

// JC-LAZO-WORKER-0913-BOOK-001 --------------------------------------------
const SLOTS_FN = "https://us-central1-lazo-513ec.cloudfunctions.net/consultSlots";
const BOOK_FN = "https://us-central1-lazo-513ec.cloudfunctions.net/consultBook";

async function bookPage(vendorId, inq, typeKey) {
  const v = await fsDoc("vendors", vendorId);
  const sch = v && v.scheduler ? fsVal(v.scheduler) : null;
  if (!v || !sch || sch.enabled === false) {
    return new Response(`<!doctype html><html><head><meta charset="utf-8"><meta name="robots" content="noindex"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Lazo</title></head><body style="font-family:system-ui;max-width:32rem;margin:4rem auto;padding:0 1rem;color:#241E2B"><h1 style="font-weight:600">Booking isn't open here yet</h1><p>Message the vendor on <a href="https://meetlazo.com" style="color:#52284F">Lazo</a> and they'll find a time with you.</p></body></html>`, { status: 404, headers: { "content-type": TYPES.html, "cache-control": "no-store" } });
  }
  const b = brandOf(v);
  const name = b.name || "your vendor";
  const cover = fsVal(v.coverUrl) || "";
  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow">
<title>Book a time - ${escF(name)}</title>
<style>
:root{--p:${b.primary};--a:${b.accent}}
body{margin:0;background:#FAF6F0;font-family:${b.font === "serif" ? "Georgia,serif" : "Helvetica,Arial,sans-serif"};color:#241E2B;-webkit-font-smoothing:antialiased}
*{box-sizing:border-box}
.hero{background:var(--p) ${cover ? `url('https://wsrv.nl/?url=${encodeURIComponent(cover)}&w=1400&q=70') center/cover` : ""};padding:44px 20px 34px;text-align:center;color:#fff;position:relative}
.hero:before{content:"";position:absolute;inset:0;background:rgba(36,30,43,${cover ? ".45" : "0"})}
.hero>*{position:relative}
.hero img.logo{width:60px;height:60px;border-radius:14px;background:#fff;object-fit:contain;margin-bottom:10px}
.hero h1{font-family:Georgia,serif;font-weight:600;font-size:34px;margin:0;line-height:1.05}.hero p{margin:8px 0 0;opacity:.9;font-size:14px}
main{max-width:560px;margin:-18px auto 60px;padding:0 14px}
.card{background:#FFFDF9;border:1px solid #E6D6B8;border-radius:18px;padding:20px;margin-bottom:12px}
.eyebrow{font-size:10.5px;letter-spacing:2px;text-transform:uppercase;font-weight:800;color:var(--p);margin-bottom:10px}
.types{display:grid;gap:8px}.type{border:1.5px solid #E6D6B8;border-radius:13px;padding:12px 14px;cursor:pointer;background:#fff;text-align:left;font:inherit;color:#241E2B}
.type.on{border-color:var(--p);box-shadow:0 0 0 3px rgba(82,40,79,.12)}.type b{display:block;font-size:15px}.type span{font-size:12px;color:#6B5F72}
.days{display:flex;gap:8px;overflow-x:auto;padding:4px 2px 8px;scrollbar-width:thin}
.day{flex:0 0 auto;border:1.5px solid #E6D6B8;border-radius:13px;padding:8px 10px;min-width:62px;text-align:center;cursor:pointer;background:#fff;font:inherit;color:#241E2B}
.day.on{border-color:var(--p);background:var(--p);color:#fff}.day small{display:block;font-size:10.5px;opacity:.75;text-transform:uppercase;letter-spacing:1px}.day b{font-size:18px;line-height:1.1}
.slots{display:grid;grid-template-columns:repeat(auto-fill,minmax(96px,1fr));gap:8px;margin-top:6px}
.slot{border:1.5px solid #E6D6B8;border-radius:11px;padding:10px 6px;text-align:center;cursor:pointer;background:#fff;font:inherit;font-size:14px;color:#241E2B}
.slot.on{border-color:var(--p);background:var(--p);color:#fff}
.muted{color:#6B5F72;font-size:12.5px;line-height:1.5}
label{display:block;font-size:11px;letter-spacing:1.2px;text-transform:uppercase;font-weight:700;color:var(--p);margin:10px 0 5px}
input,textarea{width:100%;border:1px solid #E6D6B8;border-radius:11px;padding:11px 12px;font-size:15px;background:#fff;color:#241E2B;font-family:inherit}
input:focus,textarea:focus{outline:none;border-color:var(--p)}textarea{min-height:70px}
.row{display:grid;grid-template-columns:1fr 1fr;gap:10px}@media(max-width:480px){.row{grid-template-columns:1fr}}
.ck{display:flex;gap:8px;align-items:flex-start;font-size:12px;color:#6B5F72;margin-top:12px;line-height:1.4}.ck input{width:auto;margin-top:2px}
.btn{width:100%;border:0;border-radius:12px;padding:14px;background:var(--p);color:#fff;font-size:15px;font-weight:700;cursor:pointer;font-family:inherit;margin-top:14px}
.btn[disabled]{opacity:.55}
.err{color:#B04343;font-size:13px;margin-top:8px;display:none}
.hp{position:absolute;left:-9999px;opacity:0}
.ok h2{font-family:Georgia,serif;font-weight:600;font-size:28px;color:var(--p);margin:0 0 6px}
.foot{text-align:center;font-size:11.5px;color:#6B5F72;margin-top:24px}.foot a{color:var(--p)}
.hide{display:none}
</style></head><body>
<header class="hero">${b.logoUrl ? `<img class="logo" src="https://wsrv.nl/?url=${encodeURIComponent(b.logoUrl)}&w=120&h=120&fit=contain" alt="">` : ""}<h1>${escF(name)}</h1><p>Pick a time that works for you.</p></header>
<main>
<section class="card" id="s1"><div class="eyebrow">What kind of chat</div><div class="types" id="types"><p class="muted">Loading\u2026</p></div></section>
<section class="card hide" id="s2"><div class="eyebrow">Pick a day</div><div class="days" id="days"></div><div class="eyebrow" style="margin-top:12px">Then a time <span id="tzn" style="font-weight:400;letter-spacing:0;text-transform:none;color:#6B5F72"></span></div><div class="slots" id="slots"><p class="muted">Choose a day above.</p></div></section>
<section class="card hide" id="s3"><div class="eyebrow">Your details</div>
<div class="row"><div><label>Your name</label><input id="n" maxlength="120" autocomplete="name"></div><div><label>Wedding date (if set)</label><input id="d" type="date"></div></div>
<div class="row"><div><label>Email</label><input id="e" type="email" maxlength="160" autocomplete="email"></div><div><label>Phone</label><input id="p" type="tel" maxlength="30" autocomplete="tel"></div></div>
<label>Anything we should know?</label><textarea id="m" maxlength="600"></textarea>
<input class="hp" id="w" tabindex="-1" autocomplete="off">
<label class="ck" style="text-transform:none;letter-spacing:0;font-weight:400"><input id="sm" type="checkbox" checked> Text me a reminder. Reply STOP anytime.</label>
<button class="btn" id="go" type="button">Book it</button><div class="err" id="x"></div></section>
<section class="card hide ok" id="s4"><h2>You're booked</h2><p id="okt" class="muted"></p><p class="muted">A confirmation and calendar invite are on the way. Need to change it? The cancel link is in that email.</p></section>
<p class="foot">Scheduling by <a href="https://meetlazo.com">Lazo</a></p>
</main>
<script>
const V=${JSON.stringify(vendorId)},INQ=${JSON.stringify(inq)};let TYPES=[],type=${JSON.stringify(typeKey)},day="",start="",TZ="",DAYS=[];
const $=i=>document.getElementById(i);const show=(i,on)=>$(i).classList.toggle("hide",!on);
const localTZ=Intl.DateTimeFormat().resolvedOptions().timeZone;
function fmtT(iso){return new Date(iso).toLocaleTimeString([],{hour:"numeric",minute:"2-digit"})}
fetch(SLOTS+"?v="+encodeURIComponent(V)).then(r=>r.json()).then(j=>{TYPES=j.types||[];TZ=j.tz||"";DAYS=j.days||[];
 if(!type||!TYPES.some(t=>t.key===type))type=TYPES.length?TYPES[0].key:"";
 $("types").innerHTML=TYPES.map(t=>'<button class="type'+(t.key===type?" on":"")+'" data-k="'+t.key+'"><b>'+t.label+'</b><span>'+t.minutes+' min \u00b7 '+(t.mode==="video"?"video call":t.mode==="phone"?"phone call":"in person")+'</span></button>').join("");
 document.querySelectorAll(".type").forEach(el=>el.onclick=()=>{type=el.dataset.k;document.querySelectorAll(".type").forEach(x=>x.classList.toggle("on",x===el));if(day)loadSlots();});
 $("days").innerHTML=DAYS.slice(0,45).map(k=>{const d=new Date(k+"T12:00:00");return '<button class="day" data-k="'+k+'"><small>'+d.toLocaleDateString([],{weekday:"short"})+'</small><b>'+d.getDate()+'</b><small>'+d.toLocaleDateString([],{month:"short"})+'</small></button>'}).join("")||'<p class="muted">No openings right now - message the vendor instead.</p>';
 document.querySelectorAll(".day").forEach(el=>el.onclick=()=>{day=el.dataset.k;document.querySelectorAll(".day").forEach(x=>x.classList.toggle("on",x===el));loadSlots();});
 $("tzn").textContent=localTZ&&TZ&&localTZ!==TZ?"(shown in your time, "+localTZ.replace(/_/g," ")+")":"";
 show("s2",true);}).catch(()=>{$("types").innerHTML='<p class="muted">Could not load times - try again in a moment.</p>'});
function loadSlots(){start="";show("s3",false);$("slots").innerHTML='<p class="muted">Loading\u2026</p>';
 fetch(SLOTS+"?v="+encodeURIComponent(V)+"&d="+day+"&type="+encodeURIComponent(type)).then(r=>r.json()).then(j=>{const s=j.slots||[];
  $("slots").innerHTML=s.length?s.map(iso=>'<button class="slot" data-s="'+iso+'">'+fmtT(iso)+'</button>').join(""):'<p class="muted">Nothing open that day - try another.</p>';
  document.querySelectorAll(".slot").forEach(el=>el.onclick=()=>{start=el.dataset.s;document.querySelectorAll(".slot").forEach(x=>x.classList.toggle("on",x===el));show("s3",true);$("s3").scrollIntoView({behavior:"smooth",block:"start"});});
 }).catch(()=>{$("slots").innerHTML='<p class="muted">Could not load times.</p>'});}
$("go").onclick=()=>{const n=$("n").value.trim(),e=$("e").value.trim(),p=$("p").value.trim(),x=$("x");x.style.display="none";
 if(!start){x.textContent="Pick a time first.";x.style.display="block";return}
 if(!n){x.textContent="What's your name?";x.style.display="block";return}
 if(!e&&!p){x.textContent="An email or phone so we can confirm.";x.style.display="block";return}
 const b=$("go");b.disabled=true;b.textContent="Booking\u2026";
 fetch(BOOK,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({vendorId:V,inquiryId:INQ,type:type,start:start,name:n,email:e,phone:p,weddingDate:$("d").value,note:$("m").value.trim(),smsOk:$("sm").checked,website:$("w").value,page:location.href,referrer:document.referrer})})
 .then(r=>r.json().then(j=>({ok:r.ok,j})))
 .then(({ok,j})=>{if(!ok||!j.ok){if(j&&j.error==="taken"){x.textContent="That time was just taken - pick another.";x.style.display="block";b.disabled=false;b.textContent="Book it";loadSlots();return}throw new Error()}
  try{if(window.fbq)fbq("track","Schedule")}catch(_){}
  $("okt").textContent=(TYPES.find(t=>t.key===type)||{label:"Consult"}).label+" with ${escF(name).replace(/"/g,'\\"')} \u2014 "+j.when;
  show("s1",false);show("s2",false);show("s3",false);show("s4",true);window.scrollTo({top:0,behavior:"smooth"});})
 .catch(()=>{x.textContent="That didn't go through - try again.";x.style.display="block";b.disabled=false;b.textContent="Book it"});};
const SLOTS=${JSON.stringify(SLOTS_FN)},BOOK=${JSON.stringify(BOOK_FN)};
</script></body></html>`;
  return new Response(html, { headers: { "content-type": TYPES.html, "cache-control": "no-store", "x-robots-tag": "noindex" } });
}

// JC-LAZO-WORKER-0913-DIRECTIONS-001 --------------------------------------
const DIRECTIONS_JS = `<script>(function(){
var S=window.LAZO_SITE||{};var addr=(S.venueAddress||"").trim(),name=(S.venueName||"").trim();var q=addr||name;if(!q)return;
var ua=navigator.userAgent||"";var ios=/iPad|iPhone|iPod/.test(ua)||(navigator.platform==="MacIntel"&&navigator.maxTouchPoints>1);var android=/Android/i.test(ua);
var enc=encodeURIComponent(q);
var url=ios?"maps://?daddr="+enc+"&dirflg=d":android?"google.navigation:q="+enc:"https://www.google.com/maps/dir/?api=1&destination="+enc;
var web="https://www.google.com/maps/dir/?api=1&destination="+enc;
function go(e){if(e)e.preventDefault();var t=Date.now();window.location.href=url;
 if(ios||android){setTimeout(function(){if(Date.now()-t<1500&&!document.hidden)window.location.href=web;},1200);}}
window.lazoDirections=go;
var done=false;
function norm(t){return (t||"").replace(/\\s+/g," ").trim().toLowerCase();}
function findAddr(){var want=norm(addr||name);if(!want)return null;
 var walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT,null);var n,best=null;
 while((n=walker.nextNode())){var tx=norm(n.nodeValue);if(!tx||tx.length>200)continue;if(tx===want||(tx.indexOf(want)>=0&&tx.length<want.length+40)){best=n;break;}}
 if(!best&&addr&&name){var w2=norm(name);walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT,null);while((n=walker.nextNode())){var t2=norm(n.nodeValue);if(t2===w2){best=n;break;}}}
 return best?best.parentElement:null;}
function inject(){if(done)return;var el=findAddr();if(!el)return;if(el.closest("a"))el=el.closest("a");done=true;
 el.style.cursor="pointer";el.setAttribute("role","link");el.setAttribute("aria-label","Get directions to "+q);el.addEventListener("click",go);
 var css=getComputedStyle(el);
 var b=document.createElement("a");b.href=web;b.className="lazo-directions";b.setAttribute("aria-label","Get directions");
 b.innerHTML='<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-2px;margin-right:6px"><path d="M12 2l9 9-9 9-9-9z"/><path d="M9.5 12.5h4l-1.5 1.5"/><path d="M13.5 12.5l-1.5-1.5"/></svg>Get directions';
 b.style.cssText="display:inline-flex;align-items:center;margin-top:10px;padding:8px 14px;border-radius:999px;font:600 13px/1 -apple-system,BlinkMacSystemFont,Helvetica,Arial,sans-serif;letter-spacing:.2px;text-decoration:none;color:"+css.color+";border:1.5px solid currentColor;opacity:.92";
 b.addEventListener("click",go);
 var host=el.tagName==="A"?el:el;var block=host.closest("p,div,li,address,section")||host;
 if(block&&block!==host&&block.children.length<=3){block.appendChild(document.createElement("br"));block.appendChild(b);}else{host.insertAdjacentElement("afterend",b);}}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",inject);else inject();
var tries=0;var iv=setInterval(function(){inject();if(done||++tries>40)clearInterval(iv);},250);
if(window.MutationObserver){var mo=new MutationObserver(function(){inject();if(done)mo.disconnect();});mo.observe(document.documentElement,{childList:true,subtree:true,characterData:true});setTimeout(function(){mo.disconnect();},15000);}
})();</script>`;

// JC-LAZO-WORKER-0913-SHOWCASE-001 ----------------------------------------
async function renderShowcase(slug, req, env) {
  const gal = await loadGallery(slug, env);
  if (!gal || !gal.showcase) return null;
  const asset = await env.SITE.get("gallery/index.html");
  if (!asset) return null;
  let html = await asset.text();
  const photos = await galleryManifest(slug, env);
  const brand = await vendorBrand(gal.vendorId);
  const v = gal.vendorId ? await fsDoc("vendors", gal.vendorId) : null;
  const vendorSlug = v ? (fsVal(v.slug) || gal.vendorSlug) : gal.vendorSlug;
  const metro = v ? (fsVal(v.metroId) || "") : "";
  const cat = v ? (fsVal(v.category) || "") : "";
  const vendorUrl = metro && cat && vendorSlug ? `https://meetlazo.com/${metro}/${cat}/${vendorSlug}/` : "https://meetlazo.com/";
  const title = gal.showcaseTitle || gal.names || "A real wedding";
  const payload = {
    slug, brand, names: gal.names, dateIso: gal.dateIso, message: gal.showcaseBlurb || gal.message,
    vendorName: gal.vendorName, vendorSlug, vendorUrl, coverId: gal.coverId, photoCount: gal.photoCount,
    downloadsOn: false, storeOn: false, expiresAt: "", locked: false, showcase: true,
    photos: photos.map((p) => ({ id: p.id, name: p.name, w: p.w, h: p.h })),
  };
  const cover = gal.coverId ? `https://meetlazo.com/g/${slug}/i/${gal.coverId}/web` : (photos[0] ? `https://meetlazo.com/g/${slug}/i/${photos[0].id}/web` : "");
  const pageUrl = `https://meetlazo.com/real/${slug}`;
  const desc = `${title}${gal.dateIso ? " \u00b7 " + gal.dateIso : ""} \u00b7 photographed by ${gal.vendorName}`;
  const head =
    `<meta property="og:type" content="article">\n<meta property="og:site_name" content="Lazo">\n<meta property="og:title" content="${esc(title + " \u2014 " + gal.vendorName)}">\n<meta property="og:description" content="${esc(desc)}">\n<meta property="og:url" content="${pageUrl}">\n<link rel="canonical" href="${pageUrl}">\n<meta name="description" content="${esc(desc)}">\n` +
    (cover ? `<meta property="og:image" content="${esc(cover)}">\n<meta name="twitter:card" content="summary_large_image">\n<meta name="twitter:image" content="${esc(cover)}">\n` : `<meta name="twitter:card" content="summary">\n`) +
    `<script type="application/ld+json">${JSON.stringify({ "@context": "https://schema.org", "@type": "ImageGallery", name: title, description: desc, url: pageUrl, author: { "@type": "Organization", name: gal.vendorName, url: vendorUrl } })}</script>\n`;
  const inject = `<script>window.LAZO_GALLERY=${JSON.stringify(payload).replace(/</g, "\\u003c")};</script>`;
  html = html.replace(/<meta name="robots"[^>]*>/gi, "");
  html = html.replace(/<title>[^<]*<\/title>/, `<title>${esc(title)} \u2014 ${esc(gal.vendorName)} | Lazo</title>`);
  html = html.replace("</head>", head + inject + brandHead(brand) + "\n</head>");
  html = html.replace(/<body([^>]*)>/, (m) => m + `\n<div class="lazo-brand"><a href="${esc(vendorUrl)}" style="color:inherit;text-decoration:none;display:flex;align-items:center;gap:12px">${brand.logoUrl ? `<img src="https://wsrv.nl/?url=${encodeURIComponent(brand.logoUrl)}&w=72&h=72&fit=contain" alt="">` : ""}<b>${esc(gal.vendorName)}</b><span style="opacity:.8;font-size:12px">\u00b7 real wedding \u00b7 see more &rarr;</span></a></div>`);
  return new Response(html, { headers: {
    "content-type": TYPES.html,
    "cache-control": "public, max-age=300, s-maxage=3600",
    "x-lazo": "tied-together",
  }});
}
