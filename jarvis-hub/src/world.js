// JARVIS hub: World: cruise fleets and ships, flights and routes, satellites, events, webcams, home location and trips.
import { HUB_ORIGIN, kv, uid, pushAlert, within, cached, flushAlerts } from "./core.js";
import { notify } from "./alarm.js";

/* ---------------- cruise fleets tracked by name (AIS ship names are upper case, 20 chars max) ---------------- */
const FLEETS = { ncl: { name: "Norwegian Cruise Line", ships: ["NORWEGIAN AQUA", "NORWEGIAN VIVA", "NORWEGIAN PRIMA", "NORWEGIAN LUNA", "NORWEGIAN ENCORE", "NORWEGIAN BLISS", "NORWEGIAN JOY", "NORWEGIAN ESCAPE", "NORWEGIAN GETAWAY", "NORWEGIAN BREAKAWAY", "NORWEGIAN EPIC", "NORWEGIAN GEM", "NORWEGIAN JADE", "NORWEGIAN PEARL", "NORWEGIAN JEWEL", "NORWEGIAN DAWN", "NORWEGIAN STAR", "NORWEGIAN SUN", "NORWEGIAN SKY", "NORWEGIAN SPIRIT", "PRIDE OF AMERICA"] } };
const shipKey = (n) => String(n || "").toUpperCase().replace(/[^A-Z0-9 ]/g, "").replace(/\s+/g, " ").trim();
function fleetOf(name) { const k = shipKey(name); for (const [id, f] of Object.entries(FLEETS)) if (f.ships.includes(k)) return id; return null; }
// every feed snapshot refreshes KV fleet_last, so a fleet ship keeps her last known position after the feeder drops her (3 h without a shore receiver: mid-ocean legs)
export async function fleetRemember(env, snap) {
  const last = (await kv.get(env, "fleet_last")) || {}; let changed = false; const at = snap.at ? new Date(snap.at).getTime() : Date.now();
  for (const r of snap.ships || []) { const id = fleetOf(r[1]); if (!id) continue; const k = shipKey(r[1]); const seen = new Date(at - (r[9] || 0) * 1000).toISOString(); if (last[k]?.seen === seen) continue; last[k] = { fleet: id, row: r.slice(0, 9), seen }; changed = true; }
  if (changed) await kv.put(env, "fleet_last", last);
  return last;
}
export async function fleetStatus(env, id = "ncl") {
  const f = FLEETS[id]; if (!f) return null;
  const [g, last] = await Promise.all([env.HUB.get("ships_global", "json"), kv.get(env, "fleet_last")]);
  const live = new Map(); for (const r of g?.ships || []) { const k = shipKey(r[1]); if (f.ships.includes(k)) live.set(k, r); }
  const now = Date.now(); const feedAt = g?.at ? new Date(g.at).getTime() : now;
  const ships = f.ships.map((k) => {
    const r = live.get(k) || last?.[k]?.row; const seen = live.has(k) ? new Date(feedAt - (live.get(k)[9] || 0) * 1000).toISOString() : last?.[k]?.seen || null;
    return { name: k, live: live.has(k), mmsi: r?.[0] ?? null, lat: r?.[2] ?? null, lon: r?.[3] ?? null, heading: r?.[4] ?? null, speed_kt: r?.[5] ?? null, destination: r?.[7] || "", length_m: r?.[8] || null, seen, ageMin: seen ? Math.round((now - new Date(seen)) / 60e3) : null };
  });
  return { id, name: f.name, at: g?.at || null, ships };
}


/* ---------------- World: flights, satellites, quakes, wildfires ---------------- */
const AIRLINES = { AA: "AAL", UA: "UAL", DL: "DAL", WN: "SWA", AS: "ASA", B6: "JBU", NK: "NKS", F9: "FFT", G4: "AAY", HA: "HAL", SY: "SCX", AC: "ACA", WS: "WJA", MX: "MXY", QX: "QXE", OO: "SKW", YX: "RPA", MQ: "ENY", "9E": "EDV", BA: "BAW", LH: "DLH", AF: "AFR", KL: "KLM", AM: "AMX", Y4: "VOI" };
export function toCallsign(q) {
  const t = String(q || "").toUpperCase().replace(/[\s-]+/g, "");
  const m = t.match(/^([A-Z0-9]{2})(\d{1,4}[A-Z]?)$/); if (m && AIRLINES[m[1]]) return AIRLINES[m[1]] + m[2];
  return t;
}
const acOut = (a) => ({ hex: a.hex, flight: (a.flight || "").trim(), reg: a.r || "", type: a.t || "", lat: a.lat, lon: a.lon, alt: a.alt_baro === "ground" ? 0 : (a.alt_baro ?? a.alt_geom ?? null), gs: a.gs != null ? Math.round(a.gs) : null, track: a.track ?? null, squawk: a.squawk || "", emergency: a.emergency && a.emergency !== "none" ? a.emergency : "", desc: a.desc || "", ownOp: a.ownOp || "" });
export async function flightsNear(env, lat, lon, nm = 40) {
  const f = await kv.get(env, "flights"); if (!f?.ac) return [];
  const R = 3440.065, toR = Math.PI / 180;
  const dist = (a) => 2 * R * Math.asin(Math.sqrt(Math.sin((a.lat - lat) * toR / 2) ** 2 + Math.cos(lat * toR) * Math.cos(a.lat * toR) * Math.sin((a.lon - lon) * toR / 2) ** 2));
  return f.ac.filter((a) => dist(a) <= nm);
}
export async function trackFlight(env, q) {
  const cs = toCallsign(q);
  const want = (await kv.get(env, "track_req")) || {}; want[cs] = Date.now(); await kv.put(env, "track_req", want);
  const f = await kv.get(env, "flights");
  const ac = f?.tracks?.[cs] || (f?.ac || []).filter((a) => a.flight === cs || a.reg === cs);
  return { query: q, callsign: cs, found: ac.length > 0, aircraft: ac, asOf: f?.at || null, note: ac.length ? undefined : "Tracking requested; the PC feed checks it within a minute." };
}
export async function worldEvents(env) {
  return cached(env, "world_events", 5 * 60e3, async () => {
    const [q, f, iss] = await Promise.all([
      fetch("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson").then((r) => r.json()).catch(() => ({ features: [] })),
      fetch("https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/WFIGS_Incident_Locations_Current/FeatureServer/0/query?where=IncidentSize%3E%3D100&outFields=IncidentName,IncidentSize,PercentContained,POOState,FireDiscoveryDateTime&orderByFields=IncidentSize%20DESC&resultRecordCount=150&f=geojson").then((r) => r.json()).catch(() => ({ features: [] })),
      fetch("https://api.wheretheiss.at/v1/satellites/25544").then((r) => r.json()).catch(() => null),
    ]);
    return {
      at: new Date().toISOString(),
      quakes: (q.features || []).map((x) => ({ mag: x.properties.mag, place: x.properties.place, time: x.properties.time, url: x.properties.url, lon: x.geometry.coordinates[0], lat: x.geometry.coordinates[1], depth: x.geometry.coordinates[2], tsunami: !!x.properties.tsunami })),
      fires: (f.features || []).filter((x) => x.geometry).map((x) => ({ name: x.properties.IncidentName, acres: Math.round(x.properties.IncidentSize || 0), contained: x.properties.PercentContained, state: (x.properties.POOState || "").replace("US-", ""), lon: x.geometry.coordinates[0], lat: x.geometry.coordinates[1] })),
      iss: iss ? { lat: iss.latitude, lon: iss.longitude, alt: Math.round(iss.altitude), vel: Math.round(iss.velocity) } : null,
    };
  });
}
export async function satTles(env) {
  const c = await kv.get(env, "cache_tles");
  if (c && Date.now() - c.t < 12 * 3600e3) return c.v;
  try {
    const txt = await (await fetch("https://celestrak.org/NORAD/elements/gp.php?GROUP=visual&FORMAT=tle", { headers: { "user-agent": "Mozilla/5.0 (JARVIS hub)" } })).text();
    const L = txt.split(/\r?\n/).map((x) => x.trimEnd()).filter(Boolean); const out = [];
    for (let i = 0; i + 2 < L.length + 1; i += 3) if (L[i + 1]?.startsWith("1 ") && L[i + 2]?.startsWith("2 ")) out.push([L[i].trim(), L[i + 1], L[i + 2]]);
    if (out.length) await kv.put(env, "cache_tles", { t: Date.now(), v: out });
    return out.length ? out : c?.v || [];
  } catch { return c?.v || []; }
}
// Windy webcams: search near the view centre (radius km, max 250). Free-tier image URLs carry a token that expires in 10 min.
export async function windyNear(env, lat, lon, km) {
  if (!env.WINDY_KEY) return { off: true, cams: [] };
  const key = `${lat.toFixed(1)},${lon.toFixed(1)},${Math.round(km)}`;
  const mem = (windyMem.get(key)); if (mem && Date.now() - mem.t < 8 * 60e3) return mem.v;
  const u = `https://api.windy.com/webcams/api/v3/webcams?nearby=${lat.toFixed(4)},${lon.toFixed(4)},${Math.min(250, Math.max(5, Math.round(km)))}&include=images,location,player,urls&limit=50`;
  const r = await within(fetch(u, { headers: { "x-windy-api-key": env.WINDY_KEY, accept: "application/json" } }), 8000, null);
  if (!r) return { error: "Windy timed out", cams: [] };
  const t = await r.text(); let j; try { j = JSON.parse(t); } catch { return { error: "Windy " + r.status + ": " + t.slice(0, 120), cams: [] }; }
  if (!r.ok) return { error: "Windy " + r.status + ": " + (j.message || j.error || ""), cams: [] };
  const cams = (j.webcams || j.result?.webcams || []).map((w) => {
    const loc = w.location || {}, im = w.images?.current || w.image?.current || {}, day = w.images?.daylight || {};
    return { id: String(w.webcamId || w.id), n: w.title || loc.city || "Webcam", lat: +loc.latitude, lon: +loc.longitude, img: im.preview || im.thumbnail || day.preview || "", thumb: im.thumbnail || im.icon || "",
      live: w.player?.live || w.player?.day || "", page: w.urls?.detail || (w.webcamId ? `https://www.windy.com/webcams/${w.webcamId}` : ""), city: [loc.city, loc.region, loc.country].filter(Boolean).join(", ") };
  }).filter((c) => Number.isFinite(c.lat) && Number.isFinite(c.lon));
  const v = { total: j.total ?? cams.length, cams }; windyMem.set(key, { t: Date.now(), v }); if (windyMem.size > 300) windyMem.clear();
  return v;
}
const windyMem = new Map();

export async function txSnapshot(d, id) {
  const j = await (await fetch(`https://its.txdot.gov/its/DistrictIts/GetCctvSnapshotByIcdId?districtCode=${encodeURIComponent(d)}&icdId=${encodeURIComponent(id)}`, { headers: { "user-agent": "Mozilla/5.0 (JARVIS hub)" }, cf: { cacheTtl: 30, cacheEverything: true } })).json();
  if (!j.snippet) return null;
  return new Response(Uint8Array.from(atob(j.snippet), (c) => c.charCodeAt(0)), { headers: { "content-type": "image/jpeg", "cache-control": "public, max-age=30" } });
}
export async function flightRoute(env, cs) {
  cs = String(cs || "").toUpperCase().replace(/\s+/g, ""); if (!cs) return null;
  const cache = (await kv.get(env, "routes")) || {};
  if (cache[cs] && Date.now() - cache[cs].t < 24 * 3600e3) return cache[cs].v;
  let v = null;
  try {
    const r = await within(fetch(`https://api.adsbdb.com/v0/callsign/${encodeURIComponent(cs)}`, { headers: { "user-agent": "Mozilla/5.0 (JARVIS hub)" } }), 5000, null);
    const j = r && r.ok ? await r.json() : null; const fr = j?.response?.flightroute;
    if (fr) { const ap = (a) => a && { iata: a.iata_code, icao: a.icao_code, name: a.name, city: a.municipality, country: a.country_name, lat: a.latitude, lon: a.longitude };
      v = { callsign: cs, flight: fr.callsign_iata || cs, airline: fr.airline?.name || "", from: ap(fr.origin), to: ap(fr.destination), via: ap(fr.midpoint) }; }
  } catch {}
  cache[cs] = { t: Date.now(), v };
  const keys = Object.keys(cache); if (keys.length > 600) for (const k of keys.sort((a, b) => cache[a].t - cache[b].t).slice(0, 200)) delete cache[k];
  await kv.put(env, "routes", cache);
  return v;
}

/* ---------------- home location: Texas or Arizona ---------------- */
export const HOMES = {
  tx: { tz: "America/Chicago", place: { name: "Frisco, Texas", lat: 33.1507, lon: -96.8236 }, label: "Texas" },
  az: { tz: "America/Phoenix", place: { name: "Phoenix, Arizona", lat: 33.4484, lon: -112.074 }, label: "Arizona" },
};
export async function applyHome(env) { try { const h = await kv.get(env, "home"); if (h?.tz) env.TZ = h.tz; } catch {} }
export async function setHome(env, body) {
  const cur = (await kv.get(env, "home")) || { mode: "auto", key: "tx", tz: HOMES.tx.tz };
  let key = cur.key, mode = body.mode || cur.mode;
  if (body.key && HOMES[body.key]) { key = body.key; mode = body.mode || "manual"; }
  else if (body.deviceTz && mode === "auto") { const hit = Object.entries(HOMES).find(([, v]) => v.tz === body.deviceTz) || (body.deviceTz === "America/Denver" ? ["az"] : null); if (hit) key = hit[0]; }
  const next = { mode, key, tz: HOMES[key].tz, label: HOMES[key].label, at: new Date().toISOString() };
  if (next.key !== cur.key) {
    const place = await kv.get(env, "place");
    if (!place || Object.values(HOMES).some((h) => h.place.name === place.name)) await kv.put(env, "place", HOMES[key].place);
    await pushAlert(env, { kind: "watch", text: `Home set to ${next.label} (${next.tz}); briefs follow ${next.label} time` });
  }
  await kv.put(env, "home", next);
  return next;
}

// trips: track Jesse's own flights on the day, push wheels-up / landed, switch home on landing
export async function addTrip(env, input) {
  const trips = (await kv.get(env, "trips")) || [];
  const t = { id: uid(), flight: String(input.flight || "").toUpperCase().trim(), date: String(input.date || "").slice(0, 10), home: HOMES[input.home] ? input.home : null, note: input.note || "", phase: "scheduled", at: new Date().toISOString() };
  if (!t.flight || !/^\d{4}-\d{2}-\d{2}$/.test(t.date)) return { error: "need a flight number and a YYYY-MM-DD date" };
  const r = await flightRoute(env, toCallsign(t.flight)).catch(() => null); if (r?.from) t.route = { from: r.from, to: r.to, airline: r.airline };
  trips.push(t); trips.sort((a, b) => a.date.localeCompare(b.date));
  await kv.put(env, "trips", trips);
  return t;
}
const place = (a) => a ? (a.city || a.iata || a.name) : "?";
export async function tripWatch(env) {
  const trips = (await kv.get(env, "trips")) || []; if (!trips.length) return;
  const tz = env.TZ || "America/Chicago";
  const today = new Date().toLocaleDateString("en-CA", { timeZone: tz }), yday = new Date(Date.now() - 86400e3).toLocaleDateString("en-CA", { timeZone: tz });
  const f = await kv.get(env, "flights"); const want = (await kv.get(env, "track_req")) || {}; let changed = false;
  for (const t of trips) {
    if (t.phase === "landed") continue;
    if (t.date !== today && !(t.date === yday && t.phase === "airborne")) continue;
    const cs = toCallsign(t.flight); want[cs] = Date.now(); changed = true;
    if (!t.route) { const r = await flightRoute(env, cs).catch(() => null); if (r?.from) t.route = { from: r.from, to: r.to, airline: r.airline }; }
    const ac = (f?.tracks?.[cs] || []).find((a) => a.lat != null);
    const up = ac && (ac.alt || 0) > 300 && (ac.gs || 0) > 80;
    const leg = t.route?.from ? `${place(t.route.from)} → ${place(t.route.to)}` : "";
    if (up) {
      t.last = { lat: ac.lat, lon: ac.lon, alt: ac.alt, gs: ac.gs, at: f.at }; t.miss = 0;
      if (t.phase !== "airborne") { t.phase = "airborne"; t.upAt = new Date().toISOString(); const text = `Wheels up: ${t.flight} ${leg}`.trim(); await pushAlert(env, { kind: "watch", text }); await notify(env, "Wheels up", text + ". Tracking on the World globe.", { tags: "airplane_departure", url: HUB_ORIGIN + "/" }); }
    } else if (t.phase === "airborne") {
      const ground = ac && ((ac.alt || 0) <= 300 || (ac.gs || 0) < 80);
      t.miss = (t.miss || 0) + 1;
      if (ground || (t.miss >= 3 && (t.last?.alt || 0) < 15000)) {
        t.phase = "landed"; t.landedAt = new Date().toISOString();
        const text = `Landed: ${t.flight}${t.route?.to ? " in " + place(t.route.to) : ""}`;
        await pushAlert(env, { kind: "done", text }); await notify(env, "Landed", text + (t.home ? `. Home is now ${HOMES[t.home].label}.` : "."), { tags: "airplane_arriving" });
        if (t.home) await setHome(env, { key: t.home, mode: "auto" });
      }
    }
  }
  if (changed) await kv.put(env, "track_req", want);
  const keep = trips.filter((t) => t.date >= new Date(Date.now() - 3 * 86400e3).toLocaleDateString("en-CA", { timeZone: tz }));
  await kv.put(env, "trips", keep);
}

/* ---------------- named-ship watch: push when a watched vessel appears in the AIS feed ---------------- */
export async function shipWatch(env) {
  const watch = (await kv.get(env, "ship_watch")) || []; if (!watch.length) return;
  const g = JSON.parse((await env.HUB.get("ships_global")) || '{"ships":[]}'); const out = []; let changed = false;
  for (const w of watch) {
    const q = w.name.toUpperCase(); const hit = g.ships.find((r) => String(r[1]).toUpperCase().includes(q)); if (!hit) continue;
    if (w.lastSeen && Date.now() - new Date(w.lastSeen) < 12 * 3600e3) { w.lastSeen = new Date().toISOString(); changed = true; continue; }
    w.lastSeen = new Date().toISOString(); w.last = { lat: hit[2], lon: hit[3], dest: hit[7] }; changed = true;
    const text = `${hit[1]} is in the feed: ${Number.isFinite(hit[2]) && Number.isFinite(hit[3]) ? hit[2].toFixed(2) + ", " + hit[3].toFixed(2) : "position unknown"}, ${hit[5] != null ? Math.round(hit[5] * 1.15) + " mph" : "speed unknown"}${hit[7] ? ", bound for " + hit[7] : ""}.`;
    out.push({ alert: { kind: "obs", text }, push: { title: "Ship spotted: " + hit[1], body: text, opts: { tags: "ship", url: HUB_ORIGIN + "/" } } });
  }
  if (changed) await kv.put(env, "ship_watch", watch);
  await flushAlerts(env, out);
}
