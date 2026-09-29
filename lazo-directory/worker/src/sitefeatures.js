// JC-LAZO-WORKER-0929-LIVE-001: the couple site, live.
//
//   GET  /api/w/{slug}/weather   the wedding-day forecast for the venue, inside
//                                Open-Meteo's 16-day window; nothing further out
//   POST /api/translate          {lang, texts[]} -> {texts[]} via Workers AI
//                                (m2m100), each string cached at the edge a month
//   GET  /w/{slug}/cards         printable table cards with a QR to the site's
//                                photo wall (and the song-request page)
//   GET  /w/{slug}/playlist      the DJ's page: song requests + RSVP songs, from
//                                weddingSites/{slug}/playlist/main (the dashboard
//                                mirrors them there - the source collections are
//                                couple-private and the worker has no credentials)
//
// The venue point comes from the nearby feature's cache (nearby/v1/pt/{slug}),
// then Google Places when PLACES_API_KEY is set, then Open-Meteo's free
// geocoder on the "City, ST" in the address.

const PROJECT = "lazo-513ec";
const CORS = { "access-control-allow-origin": "*", "access-control-allow-methods": "GET, POST, OPTIONS",
               "access-control-allow-headers": "content-type" };
const json = (obj, status = 200, extra = {}) =>
  new Response(JSON.stringify(obj), { status, headers: { "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store", ...CORS, ...extra } });
const esc = (t) => String(t == null ? "" : t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function fsVal(v) {
  if (v == null) return null;
  if ("stringValue" in v) return v.stringValue;
  if ("integerValue" in v) return Number(v.integerValue);
  if ("doubleValue" in v) return v.doubleValue;
  if ("booleanValue" in v) return v.booleanValue;
  if ("timestampValue" in v) return v.timestampValue;
  if ("arrayValue" in v) return (v.arrayValue.values || []).map(fsVal);
  if ("mapValue" in v) { const o = {}; for (const [k, x] of Object.entries(v.mapValue.fields || {})) o[k] = fsVal(x); return o; }
  return null;
}
async function fsDoc(path) {
  const r = await fetch(`https://firestore.googleapis.com/v1/projects/${PROJECT}/databases/(default)/documents/${path}`,
    { headers: { accept: "application/json" } });
  if (!r.ok) return null;
  const d = await r.json();
  const out = {};
  for (const [k, v] of Object.entries(d.fields || {})) out[k] = fsVal(v);
  return out;
}

// ---------------------------------------------------------------- weather
async function venueLatLng(slug, site, env, placesPoint) {
  try {
    const o = await env.SITE.get("nearby/v1/pt/" + slug + ".json");
    if (o) { const j = await o.json(); if (j && j.lat) return { lat: j.lat, lng: j.lng }; }
  } catch (e) {}
  const address = String(site.venueAddress || ""), vname = String(site.venueName || "");
  if (env.PLACES_API_KEY && placesPoint) {
    try { const p = await placesPoint(vname, address, env.PLACES_API_KEY); if (p) return p; } catch (e) {}
  }
  // "…, Sedona, AZ 86336" -> Sedona (state as a hint)
  const m = address.match(/,\s*([^,]+?),\s*([A-Za-z]{2})\b/);
  const city = m ? m[1].trim() : address.split(",").slice(-3, -2)[0];
  if (!city) return null;
  try {
    const r = await fetch("https://geocoding-api.open-meteo.com/v1/search?count=5&language=en&format=json&name=" + encodeURIComponent(city));
    const j = await r.json();
    const hits = (j.results || []).filter(x => x.country_code === "US");
    const st = m ? m[2].toUpperCase() : "";
    const hit = hits.find(x => st && String(x.admin1_code || "").toUpperCase().endsWith(st)) || hits[0];
    if (hit) return { lat: hit.latitude, lng: hit.longitude };
  } catch (e) {}
  return null;
}

const WMO = (c) => c === 0 ? "clear" : c <= 2 ? "mostly clear" : c === 3 ? "overcast" : c <= 48 ? "foggy"
  : c <= 57 ? "drizzle" : c <= 67 ? "rain" : c <= 77 ? "snow" : c <= 82 ? "showers" : c <= 86 ? "snow showers" : "thunderstorms";

function weatherLine(d) {
  const bits = [];
  if (d.rain >= 60) bits.push("rain is likely — plan on the indoor option");
  else if (d.rain >= 35) bits.push("a fair chance of rain — a wrap or umbrella won’t hurt");
  if (d.hi >= 88) bits.push("it will be hot — water and shade before the ceremony");
  if (d.lo <= 58) bits.push("bring a layer for the evening");
  if (!bits.length) bits.push(d.hi >= 70 ? "a lovely day for it" : "cool and pleasant");
  return bits[0][0].toUpperCase() + bits[0].slice(1) + ".";
}

export async function weatherRoute(slug, env, placesPoint) {
  const h = { "cache-control": "public, max-age=1800, s-maxage=3600" };
  const key = new Request("https://meetlazo.com/_internal/weather/" + slug);
  const hit = await caches.default.match(key);
  if (hit) return hit;
  const site = await fsDoc("weddingSites/" + encodeURIComponent(slug));
  if (!site) return json({ ok: false, error: "not_found" }, 404);
  const iso = String(site.dateIso || "");
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso)) return json({ ok: true, day: null, reason: "no_date" }, 200, h);
  const days = Math.round((Date.parse(iso + "T12:00:00Z") - Date.now()) / 864e5);
  if (days < -1 || days > 15) return json({ ok: true, day: null, reason: days > 15 ? "too_far" : "past", daysOut: days }, 200, h);
  const at = await venueLatLng(slug, site, env, placesPoint);
  if (!at) return json({ ok: true, day: null, reason: "no_venue" }, 200, h);
  const u = `https://api.open-meteo.com/v1/forecast?latitude=${at.lat}&longitude=${at.lng}&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunset&temperature_unit=fahrenheit&timezone=auto&start_date=${iso}&end_date=${iso}`;
  let day = null;
  try {
    const r = await fetch(u); const j = await r.json(); const d = j.daily;
    if (d && d.time && d.time[0] === iso) {
      day = { date: iso, hi: Math.round(d.temperature_2m_max[0]), lo: Math.round(d.temperature_2m_min[0]),
              rain: Math.round(d.precipitation_probability_max[0] || 0), code: d.weather_code[0],
              sky: WMO(d.weather_code[0]), sunset: String(d.sunset[0] || "").slice(11, 16), tz: j.timezone };
      day.line = weatherLine(day);
    }
  } catch (e) {}
  const resp = json({ ok: true, day, daysOut: days }, 200, h);
  try { await caches.default.put(key, resp.clone()); } catch (e) {}
  return resp;
}

// ---------------------------------------------------------------- translate
const LANGS = new Set(["es", "fr", "pt", "de", "it", "hi", "zh", "ja", "ko", "vi", "tl", "ar", "ru", "pl", "he", "el", "tr", "nl", "sv", "uk"]);
async function sha1(s) {
  const b = await crypto.subtle.digest("SHA-1", new TextEncoder().encode(s));
  return [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, "0")).join("");
}
export async function translateRoute(req, env) {
  if (req.method === "OPTIONS") return new Response(null, { headers: CORS });
  if (!env.AI) return json({ ok: false, error: "no_ai" }, 503);
  let b; try { b = await req.json(); } catch (e) { return json({ ok: false }, 400); }
  const lang = String(b.lang || "").toLowerCase().slice(0, 2);
  if (!LANGS.has(lang)) return json({ ok: false, error: "lang" }, 400);
  const texts = Array.isArray(b.texts) ? b.texts.slice(0, 220).map(t => String(t || "").slice(0, 600)) : [];
  const out = new Array(texts.length).fill("");
  const todo = [];
  await Promise.all(texts.map(async (t, i) => {
    if (!t.trim() || !/[a-z]/i.test(t)) { out[i] = t; return; }
    const k = new Request(`https://meetlazo.com/_internal/tr/${lang}/${await sha1(t)}`);
    const hit = await caches.default.match(k);
    if (hit) { out[i] = await hit.text(); return; }
    todo.push([i, t, k]);
  }));
  // a few at a time; the model is quick but not free
  for (let n = 0; n < todo.length; n += 8) {
    await Promise.all(todo.slice(n, n + 8).map(async ([i, t, k]) => {
      try {
        const r = await env.AI.run("@cf/meta/m2m100-1.2b", { text: t, source_lang: "en", target_lang: lang });
        const tr = String((r && r.translated_text) || "").trim() || t;
        out[i] = tr;
        await caches.default.put(k, new Response(tr, { headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "public, max-age=2592000" } }));
      } catch (e) { out[i] = t; }
    }));
  }
  return json({ ok: true, lang, texts: out });
}

// ---------------------------------------------------------------- table cards
export async function cardsPage(slug) {
  const site = await fsDoc("weddingSites/" + encodeURIComponent(slug));
  if (!site) return new Response("Not found", { status: 404 });
  const names = esc(site.names || "the couple");
  const url = `https://meetlazo.com/w/${slug}/`;
  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>Table cards — ${names}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500&family=Jost:wght@300;400;500&display=swap" rel="stylesheet">
<style>
body{margin:0;background:#EFE9E0;color:#241E2B;font:300 15px/1.5 "Jost",sans-serif}
.bar{background:#52284F;color:#FAF6F0;padding:14px 20px;display:flex;gap:14px;align-items:center;flex-wrap:wrap}
.bar b{font-family:"Cormorant Garamond",serif;font-size:20px;font-weight:600}
.bar label{font-size:13px;display:inline-flex;gap:6px;align-items:center}
.bar button{margin-left:auto;background:#D9B77C;color:#3D1C3B;border:0;border-radius:999px;padding:9px 18px;font:500 13px "Jost",sans-serif;cursor:pointer}
.sheet{display:grid;grid-template-columns:1fr 1fr;gap:0;max-width:8.5in;margin:24px auto;background:#fff;padding:.5in .5in}
.card{border:1px dashed #D9B77C;padding:.35in .3in;text-align:center;height:3.6in;box-sizing:border-box;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px}
.card .k{font-size:10px;letter-spacing:.34em;text-transform:uppercase;color:#8A6A2F}
.card h2{font:600 26px/1.05 "Cormorant Garamond",serif;color:#52284F;margin:0;text-wrap:balance}
.card p{margin:0;font-size:12.5px;color:#6B5F72;max-width:24ch}
.card .qr{width:1.35in;height:1.35in;margin:4px 0}
.card .qr img,.card .qr canvas{width:100%;height:100%}
.card small{font-size:10.5px;color:#8A6A2F;letter-spacing:.04em}
@media print{body{background:#fff}.bar{display:none}.sheet{margin:0;padding:.4in;page-break-after:always}.card{border-color:#ddd}}
</style></head><body>
<div class="bar"><b>Table cards · ${names}</b>
<label><input type="radio" name="k" value="photos" checked> Share your photos</label>
<label><input type="radio" name="k" value="song"> Request a song</label>
<label><input type="radio" name="k" value="both"> Both on one card</label>
<button onclick="print()">Print</button></div>
<div class="sheet" id="sheet"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
<script>
var SITE=${JSON.stringify(url)},NAMES=${JSON.stringify(String(site.names || ""))};
var KINDS={
 photos:{k:"Share your photos",h:"Took one we\\u2019d love to see?",p:"Scan, tap \\u201cAdd photos from your phone\\u201d, and it lands on our site for everyone.",u:SITE+"?photos=1#photos"},
 song:{k:"Request a song",h:"Get us on the dance floor.",p:"Scan and tell the DJ what you need to hear tonight.",u:SITE+"requests"},
 both:{k:"Tonight",h:"Share a photo, request a song.",p:"Scan for our site \\u2014 add your photos from your phone, and tell the DJ what to play.",u:SITE+"?photos=1#photos"}};
function build(){
 var kind=document.querySelector('input[name=k]:checked').value,K=KINDS[kind],s=document.getElementById("sheet");s.innerHTML="";
 for(var i=0;i<6;i++){
  var c=document.createElement("div");c.className="card";
  c.innerHTML='<span class="k">'+K.k+'</span><h2>'+K.h+'</h2><p>'+K.p+'</p><div class="qr"></div><small>'+SITE.replace("https://","")+'</small>';
  s.appendChild(c);
  new QRCode(c.querySelector(".qr"),{text:K.u,width:260,height:260,correctLevel:QRCode.CorrectLevel.M,colorDark:"#3D1C3B",colorLight:"#ffffff"});
 }
}
document.querySelectorAll('input[name=k]').forEach(function(r){r.addEventListener("change",build)});build();
</script></body></html>`;
  return new Response(html, { headers: { "content-type": "text/html;charset=utf-8", "cache-control": "public, max-age=300", "x-robots-tag": "noindex" } });
}

// ---------------------------------------------------------------- the DJ's page
export async function playlistPage(slug) {
  const site = await fsDoc("weddingSites/" + encodeURIComponent(slug));
  if (!site) return new Response("Not found", { status: 404 });
  const pl = await fsDoc(`weddingSites/${encodeURIComponent(slug)}/playlist/main`);
  const songs = (pl && Array.isArray(pl.songs)) ? pl.songs : [];
  const names = esc(site.names || "the couple");
  const updated = pl && pl.updatedAt ? new Date(pl.updatedAt).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : "";
  const rows = songs.map(s => `<li><b>${esc(s.song)}</b>${s.artist ? ` <span class="a">${esc(s.artist)}</span>` : ""}${s.guest ? `<span class="g">— ${esc(s.guest)}</span>` : ""}${s.note ? `<div class="n">${esc(s.note)}</div>` : ""}${s.must ? '<span class="m">must-play</span>' : ""}</li>`).join("");
  const plain = songs.map(s => [s.song, s.artist].filter(Boolean).join(" — ")).join("\n");
  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>Playlist — ${names}</title>
<style>
body{margin:0;background:#FAF6F0;color:#241E2B;font-family:Helvetica,Arial,sans-serif}
.wrap{max-width:560px;margin:0 auto;padding:36px 20px 60px}
h1{font-family:Georgia,serif;font-weight:600;font-size:32px;color:#52284F;margin:0 0 4px;line-height:1.05}
p{color:#6B5F72;font-size:14px;line-height:1.5;margin:0 0 18px}
ul{list-style:none;padding:0;margin:0}li{background:#FFFDF9;border:1px solid #E6D6B8;border-radius:12px;padding:12px 14px;margin-bottom:8px;font-size:15px;position:relative}
.a{color:#6B5F72}.g{display:block;font-size:12px;color:#8A6A2F;margin-top:2px}.n{font-size:12.5px;color:#6B5F72;margin-top:4px}
.m{position:absolute;right:12px;top:12px;font-size:10px;letter-spacing:1px;text-transform:uppercase;background:#D9B77C;color:#3D1C3B;border-radius:999px;padding:3px 8px;font-weight:700}
.tools{display:flex;gap:8px;margin:0 0 18px}.tools button{border:1px solid #D9B77C;background:#fff;color:#52284F;border-radius:999px;padding:8px 14px;font-size:13px;cursor:pointer}
.foot{margin-top:34px;text-align:center;font-size:11px;color:#6B5F72}.foot a{color:#52284F}
</style></head><body><div class="wrap">
<h1>Requests for ${names}</h1><p>${songs.length} song${songs.length === 1 ? "" : "s"} from the guests and the RSVP form${updated ? " · updated " + esc(updated) : ""}. This page refreshes itself.</p>
<div class="tools"><button onclick="navigator.clipboard.writeText(document.getElementById('plain').textContent).then(function(){this.textContent='Copied ✓'}.bind(this))">Copy as text</button><button onclick="location.reload()">Refresh</button></div>
<ul>${rows || '<li style="color:#6B5F72">Nothing yet — requests land here as guests send them.</li>'}</ul>
<pre id="plain" hidden>${esc(plain)}</pre>
<div class="foot">Planned on <a href="https://meetlazo.com">Lazo</a> · guests request songs at meetlazo.com/w/${esc(slug)}/requests</div></div>
<script>setTimeout(function(){location.reload()},120000)</script></body></html>`;
  return new Response(html, { headers: { "content-type": "text/html;charset=utf-8", "cache-control": "public, max-age=60", "x-robots-tag": "noindex" } });
}
