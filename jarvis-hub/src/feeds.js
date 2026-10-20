// JARVIS hub: Information feeds: weather, calendar, sports, markets, radio, news and wedding-day weather.
import { UA, kv, tfetch } from "./core.js";

/* ---------------- weather ---------------- */
export async function weatherData(request, env, place) {
  const cf = request.cf || {};
  const lat = place?.lat || cf.latitude, lon = place?.lon || cf.longitude;
  if (!lat || !lon) return { error: "no location" };
  const q = new URLSearchParams({ latitude: lat, longitude: lon,
    current: "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m,wind_gusts_10m,is_day,precipitation,uv_index,pressure_msl,visibility",
    daily: "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,sunrise,sunset,uv_index_max,wind_speed_10m_max",
    hourly: "temperature_2m,weather_code,precipitation_probability,precipitation,wind_speed_10m,relative_humidity_2m",
    temperature_unit: "fahrenheit", wind_speed_unit: "mph", precipitation_unit: "inch", forecast_days: "7", timezone: "auto" });
  // The forecast is the part that matters: per-call timeouts, one retry, and the last good reading (KV wx_last_<lat,lon>) when Open-Meteo
  // is slow or rate-limits Cloudflare's shared IPs, which is what left the 5am brief saying "weather unavailable". AQI and NWS are extras.
  const forecast = async () => { const r = await tfetch("https://api.open-meteo.com/v1/forecast?" + q, { cf: { cacheTtl: 600, cacheEverything: true } }, 5000); const j = await r.json(); if (!r.ok || j.error || !j.current) throw new Error(`open-meteo ${r.status} ${j.reason || ""}`.trim()); return j; };
  const lastKey = `wx_last_${(+lat).toFixed(2)},${(+lon).toFixed(2)}`;
  const [wx, aq, al] = await Promise.all([
    forecast().catch(() => forecast()).catch(async (e) => { console.log("weather", e.message); const last = await kv.get(env, lastKey); return last && Date.now() - new Date(last.fetchedAt) < 12 * 3600e3 ? { ...last, stale: true } : { error: "weather " + e.message }; }),
    tfetch(`https://air-quality-api.open-meteo.com/v1/air-quality?latitude=${lat}&longitude=${lon}&current=us_aqi,pm2_5&timezone=auto`, { cf: { cacheTtl: 1800, cacheEverything: true } }, 3000).then((r) => r.json()).catch(() => null),
    tfetch(`https://api.weather.gov/alerts/active?point=${(+lat).toFixed(4)},${(+lon).toFixed(4)}`, { headers: { "user-agent": UA, accept: "application/geo+json" }, cf: { cacheTtl: 300, cacheEverything: true } }, 3000).then((r) => r.json()).catch(() => ({ features: [] })),
  ]);
  if (wx.error) return wx;
  if (!wx.stale) { wx.fetchedAt = new Date().toISOString(); await kv.put(env, lastKey, wx).catch(() => null); }
  wx.aqi = aq?.current || wx.aqi || null; wx.lat = +lat; wx.lon = +lon;
  wx.place = place?.name || [cf.city, cf.regionCode].filter(Boolean).join(", ") || "Your location";
  wx.nws = (al?.features || []).map((f) => ({ id: f.id, event: f.properties.event, severity: f.properties.severity, headline: f.properties.headline, ends: f.properties.ends || f.properties.expires }));
  return wx;
}
const WMO = { 0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast", 45: "fog", 48: "fog", 51: "drizzle", 53: "drizzle", 55: "drizzle", 61: "light rain", 63: "rain", 65: "heavy rain", 71: "snow", 73: "snow", 75: "snow", 80: "showers", 81: "showers", 82: "heavy showers", 95: "thunderstorms", 96: "thunderstorms", 99: "thunderstorms" };
export function weatherSummary(w) {
  if (!w || w.error) return "unavailable";
  const c = w.current, d = w.daily;
  const days = d.time.slice(0, 4).map((t, i) => `${i === 0 ? "today" : new Date(t + "T12:00").toLocaleDateString("en-US", { weekday: "short" })} ${WMO[d.weather_code[i]] || ""} ${Math.round(d.temperature_2m_max[i])}/${Math.round(d.temperature_2m_min[i])} rain ${d.precipitation_probability_max[i] ?? 0}%`).join("; ");
  return `${w.place}${w.stale ? ` (last reading ${new Date(w.fetchedAt).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", timeZone: w.timezone || "America/Chicago" })}, live feed slow)` : ""}: ${Math.round(c.temperature_2m)}°F ${WMO[c.weather_code] || ""}, feels ${Math.round(c.apparent_temperature)}, wind ${Math.round(c.wind_speed_10m)} mph gusting ${Math.round(c.wind_gusts_10m)}, humidity ${c.relative_humidity_2m}%, UV ${c.uv_index}, AQI ${w.aqi?.us_aqi ?? "n/a"}. Sunrise ${d.sunrise[0].slice(11)} sunset ${d.sunset[0].slice(11)}. Outlook: ${days}.${w.nws.length ? " NWS ALERTS: " + w.nws.map((a) => a.headline).join(" | ") : ""}`;
}

/* ---------------- calendar (private ICS link) ---------------- */
function parseICS(text) {
  const events = []; const blocks = text.split("BEGIN:VEVENT").slice(1);
  const unfold = (s) => s.replace(/\r?\n[ \t]/g, "");
  for (const raw of blocks) {
    const b = unfold(raw.split("END:VEVENT")[0]);
    const get = (k) => { const m = b.match(new RegExp("^" + k + "[^:\\n]*:(.*)$", "m")); return m ? m[1].trim() : ""; };
    const ds = get("DTSTART"), de = get("DTEND");
    if (!ds) continue;
    const toIso = (v) => v.length === 8 ? `${v.slice(0, 4)}-${v.slice(4, 6)}-${v.slice(6, 8)}` : `${v.slice(0, 4)}-${v.slice(4, 6)}-${v.slice(6, 8)}T${v.slice(9, 11)}:${v.slice(11, 13)}:00${v.endsWith("Z") ? "Z" : ""}`;
    events.push({ start: toIso(ds), end: de ? toIso(de) : null, allDay: ds.length === 8, title: get("SUMMARY").replace(/\\,/g, ","), location: get("LOCATION").replace(/\\,/g, ","), recurring: !!get("RRULE") });
  }
  return events;
}
export async function loadCalendar(env, force) {
  if (!env.CAL_ICS_URL) return null;
  const cached = await kv.get(env, "calendar");
  if (cached && !force && Date.now() - new Date(cached.at) < 30 * 60000) return cached;
  try {
    const text = await (await tfetch(env.CAL_ICS_URL, { headers: { "user-agent": UA } }, 10000)).text();
    const from = Date.now() - 86400e3, to = Date.now() + 60 * 86400e3;
    const events = parseICS(text).filter((e) => !e.recurring && new Date(e.start) >= from && new Date(e.start) <= to).sort((a, b) => a.start.localeCompare(b.start)).slice(0, 60);
    const cal = { at: new Date().toISOString(), events }; await kv.put(env, "calendar", cal); return cal;
  } catch (e) { return cached || { at: new Date().toISOString(), events: [], error: e.message }; }
}


/* ---------------- sports (ESPN public scoreboard), markets (Yahoo chart meta), news (RSS) ---------------- */
const LEAGUES = { nfl: "football/nfl", mlb: "baseball/mlb", nba: "basketball/nba", nhl: "hockey/nhl" };
const ymd = (d) => d.toISOString().slice(0, 10).replace(/-/g, "");
export async function sports(env) {
  const fav = (env.TEAMS || "DAL,NE,TEX,COL,BOS,ARI").split(/[,\s|]+/).filter(Boolean);
  const leagues = (env.LEAGUES || "nfl,mlb").split(/[,\s]+/).filter((l) => LEAGUES[l]);
  const days = [-1, 0, 1].map((n) => ymd(new Date(Date.now() + n * 86400e3)));
  const games = []; const errors = [];
  await Promise.all(leagues.flatMap((lg) => days.map(async (d) => {
    try {
      const r = await fetch(`https://site.api.espn.com/apis/site/v2/sports/${LEAGUES[lg]}/scoreboard?dates=${d}`, { headers: { "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36", accept: "application/json" }, cf: { cacheTtl: 60, cacheEverything: true } });
      const j = await r.json();
      for (const ev of j.events || []) {
        const c = ev.competitions?.[0]; if (!c) continue;
        const teams = c.competitors.map((t) => ({ abbr: t.team.abbreviation, name: t.team.shortDisplayName || t.team.displayName, score: t.score, home: t.homeAway === "home", winner: t.winner === true, record: t.records?.[0]?.summary || "" }));
        games.push({ league: lg, id: ev.id, date: ev.date, state: ev.status?.type?.state, detail: ev.status?.type?.shortDetail || "", period: ev.status?.period, clock: ev.status?.displayClock, teams, fav: teams.some((t) => fav.includes(t.abbr)), tv: c.broadcasts?.[0]?.names?.[0] || "" });
      }
    } catch (e) { errors.push(`${lg} ${d}: ${e.message}`); }
  })));
  const seen = new Set(); const out = games.filter((g) => !seen.has(g.id) && seen.add(g.id));
  out.sort((a, b) => (b.fav - a.fav) || ((a.state === "in") - (b.state === "in")) * -1 || a.date.localeCompare(b.date));
  if (!out.length) { const fromPc = await kv.get(env, "sports"); if (fromPc?.games?.length) return { ...fromPc, source: "pc", errors }; }
  return { at: new Date().toISOString(), fav, games: out, errors };
}
export function sportsSummary(sp) {
  if (!sp?.games) return "unavailable";
  if (sp.teams?.length) { const t = sp.teams.map((t) => `${t.name} (${t.record || "?"}${t.division ? `, ${t.rank}${["th","st","nd","rd"][t.rank] || "th"} in the ${t.division}` : ""}): ` + (t.next ? (t.next.state === "in" ? `LIVE ${t.next.my}-${t.next.their} vs ${t.next.opp} ${t.next.detail}` : `next ${t.next.home ? "vs" : "at"} ${t.next.opp} ${new Date(t.next.date).toLocaleString("en-US", { timeZone: "America/Chicago", weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}${t.next.tv ? " on " + t.next.tv : ""}`) : (t.note || "no game scheduled")) + (t.last ? `; last ${t.last.won ? "won" : "lost"} ${t.last.my}-${t.last.their} ${t.last.home ? "vs" : "at"} ${t.last.opp}` : "") + ((t.upcoming || []).length > 1 ? `; then ` + t.upcoming.slice(1, 4).map((g) => `${g.home ? "vs" : "at"} ${g.opp} ${new Date(g.date).toLocaleDateString("en-US", { timeZone: "America/Chicago", month: "short", day: "numeric" })}`).join(", ") : "")).join(" | "); return t; }
  const f = sp.games.filter((g) => g.fav);
  if (!f.length) return "no games for the favourite teams yesterday, today or tomorrow";
  return f.map((g) => { const [a, b] = g.teams; const who = g.teams.find((t) => sp.fav.includes(t.abbr)); const opp = g.teams.find((t) => t !== who);
    if (g.state === "in") return `${who.name} ${who.score}-${opp.score} ${opp.name} LIVE (${g.detail})`;
    if (g.state === "post") return `${who.name} ${who.winner ? "beat" : "lost to"} ${opp.name} ${who.score}-${opp.score}`;
    return `${who.name} vs ${opp.name} ${new Date(g.date).toLocaleString("en-US", { timeZone: "America/Chicago", weekday: "short", hour: "numeric", minute: "2-digit" })}${g.tv ? " on " + g.tv : ""}`; }).join("; ");
}

const INDEXES = [["^GSPC", "S&P 500"], ["^DJI", "Dow"], ["^IXIC", "Nasdaq"], ["CL=F", "Oil (WTI)"], ["BTC-USD", "Bitcoin"]];   // oil is the front-month WTI future in $/barrel; bitcoin in USD
export async function markets(env) {
  const user = (await kv.get(env, "tickers")) || [];
  const syms = [...INDEXES.map(([s]) => s), ...user.map((t) => String(t).toUpperCase())];
  const rows = await Promise.all(syms.map(async (sym) => {
    try {
      const r = await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(sym)}?range=1d&interval=5m`, { headers: { "user-agent": "Mozilla/5.0" }, cf: { cacheTtl: 120, cacheEverything: true } });
      const m = (await r.json()).chart?.result?.[0]?.meta; if (!m) return { sym, error: "no data" };
      const price = m.regularMarketPrice, prev = m.chartPreviousClose ?? m.previousClose;
      if (!Number.isFinite(price)) return { sym, error: "no price" };
      return { sym, name: INDEXES.find(([s]) => s === sym)?.[1] || m.shortName || sym, price, prev, change: price - prev, pct: prev ? (price - prev) / prev * 100 : 0, state: m.marketState || "", time: m.regularMarketTime };
    } catch (e) { return { sym, error: e.message }; }
  }));
  return { at: new Date().toISOString(), rows };
}
// "Now playing" for the Radio panel: Shoutcast/Icecast streams interleave a metadata block every icy-metaint bytes
// (StreamTitle='Artist - Title'). Browsers cannot read it from <audio>, so the worker opens the stream with
// Icy-MetaData: 1, reads until the first non-empty block (at most 8 blocks, ~16-64 KB) and hangs up.
const RADIO_HOSTS = /^(media-ssl\.musicradio\.com|[a-z0-9.-]+\.amperwave\.net)$/i;
export async function radioNow(u) {
  let url; try { url = new URL(u); } catch { return { error: "bad url" }; }
  if (!RADIO_HOSTS.test(url.hostname)) return { error: "host not allowed" };
  const ctl = new AbortController(); const timer = setTimeout(() => ctl.abort(), 8000);
  try {
    // AmperWave answers the /direct/ URL with a redirect to a session host; follow it by hand so the Icy-MetaData header survives
    let r = await fetch(url, { headers: { "Icy-MetaData": "1", "user-agent": "Mozilla/5.0" }, signal: ctl.signal, redirect: "manual" }); let cur = url;
    for (let hop = 0; hop < 4 && r.status >= 300 && r.status < 400 && r.headers.get("location"); hop++) {
      const next = new URL(r.headers.get("location"), cur); cur = next; if (!RADIO_HOSTS.test(next.hostname)) return { error: "redirected off-host" };
      try { await r.body?.cancel(); } catch {}
      r = await fetch(next, { headers: { "Icy-MetaData": "1", "user-agent": "Mozilla/5.0" }, signal: ctl.signal, redirect: "manual" });
    }
    const metaint = +(r.headers.get("icy-metaint") || 0); const name = r.headers.get("icy-name") || "";
    if (!metaint || !r.body) { ctl.abort(); return { name, title: null, note: "no in-stream metadata", status: r.status, ct: r.headers.get("content-type") }; }
    const reader = r.body.getReader(); let buf = new Uint8Array(0); let title = null, blocks = 0;
    const need = async (n) => { while (buf.length < n) { const { value, done } = await reader.read(); if (done) return false; const nb = new Uint8Array(buf.length + value.length); nb.set(buf); nb.set(value, buf.length); buf = nb; } return true; };
    while (blocks < 8 && title === null) {
      if (!(await need(metaint + 1))) break;
      const len = buf[metaint] * 16;
      if (!(await need(metaint + 1 + len))) break;
      if (len) { const txt = new TextDecoder().decode(buf.slice(metaint + 1, metaint + 1 + len)).replace(/\0+$/, ""); const m = txt.match(/StreamTitle='(.*?)';/); if (m && m[1].trim()) title = m[1].trim(); }
      buf = buf.slice(metaint + 1 + len); blocks++;
    }
    ctl.abort();
    return { name, title, blocks };
  } catch (e) { return { error: String(e.message || e) }; } finally { clearTimeout(timer); }
}
// Audacy stations publish their song history separately (the AmperWave stream has no ICY titles, and AmperWave
// refuses Cloudflare anyway): experience/v2/stations/<id>/nowplaying -> { performances: [{ artist, title, ... }] }
/* NOAA Weather Radio: volunteer SSL streams on wxradio.org (Icecast, CORS *); station sites + coordinates from noaaweatherradio.org's map data */
async function nwrSites(env) {
  const hit = await env.HUB.get("nwr_sites", "json"); if (hit) return hit;
  const js = await (await fetch("https://noaaweatherradio.org/java/NWR-player-radios.js", { headers: { "user-agent": "Mozilla/5.0 (JARVIS hub)" } })).text();
  const sites = {};
  for (const m of js.matchAll(/"lat":'(-?[\d.]+)',\s*"lng":'(-?[\d.]+)',\s*"description":'Station (?:&starf;)?([A-Z0-9]+) on ([\d.]+)MHz from ([^,]+), ([A-Z]{2})/g)) sites[m[3]] = { lat: +m[1], lon: +m[2], call: m[3], freq: m[4], city: m[5].trim(), st: m[6] };
  if (Object.keys(sites).length) await env.HUB.put("nwr_sites", JSON.stringify(sites), { expirationTtl: 86400 });
  return sites;
}
export async function wxRadio(request, env, lat, lon) {
  if (!(lat && lon)) { const place = await kv.get(env, "place"); lat = place?.lat || request.cf?.latitude; lon = place?.lon || request.cf?.longitude; }
  const [sites, stats] = await Promise.all([nwrSites(env), fetch("https://wxradio.org/status-json.xsl", { headers: { "user-agent": "Mozilla/5.0 (JARVIS hub)" } }).then((r) => r.json()).catch(() => null)]);
  const src = [].concat(stats?.icestats?.source || []);
  const live = {};
  for (const s of src) { const mount = String(s.listenurl || "").split("/").pop(); const call = mount.split("-").find((x) => sites[x]); if (call && (!live[call] || !/-alt\d*$/.test(mount) && /-alt\d*$/.test(live[call]))) live[call] = mount; }
  const R = 3958.8, rad = (d) => d * Math.PI / 180;
  const miles = (a) => Math.round(2 * R * Math.asin(Math.sqrt(Math.sin(rad(a.lat - lat) / 2) ** 2 + Math.cos(rad(lat)) * Math.cos(rad(a.lat)) * Math.sin(rad(a.lon - lon) / 2) ** 2)));
  const near = Object.entries(live).map(([call, mount]) => ({ ...sites[call], url: "https://wxradio.org/" + mount, miles: miles(sites[call]) })).sort((a, b) => a.miles - b.miles).slice(0, 6);
  return { lat: +lat, lon: +lon, stations: near, live: Object.keys(live).length };
}

export async function audacyNow(id) {
  if (!/^[\w-]{1,20}$/.test(id)) return { error: "bad station id" };
  try {
    const r = await fetch(`https://api.audacy.com/experience/v2/stations/${id}/nowplaying?count=3`, { headers: { "user-agent": "Mozilla/5.0", accept: "application/json" }, cf: { cacheTtl: 20, cacheEverything: true } });
    if (!r.ok) return { title: null, status: r.status };
    const j = await r.json(); const p = (j.performances || [])[0];
    if (!p) return { title: null, note: "station publishes no song data" };
    const title = [p.artist, p.title].filter(Boolean).join(" - ");
    return { title: title || null, artist: p.artist || "", song: p.title || "", at: p.time || null, image: p.mediumimage || null, history: (j.performances || []).slice(0, 3).map((x) => [x.artist, x.title].filter(Boolean).join(" - ")) };
  } catch (e) { return { error: String(e.message || e) }; }
}
export const marketsSummary = (mk) => (mk?.rows || []).filter((r) => !r.error && Number.isFinite(r.price)).map((r) => `${r.name} ${r.price >= 1000 ? Math.round(r.price).toLocaleString() : r.price.toFixed(2)} (${r.pct >= 0 ? "+" : ""}${r.pct.toFixed(2)}%)`).join(", ") || "unavailable";

const NEWS_FEEDS = [
  ["Phoenix", "FOX 10", "https://www.fox10phoenix.com/rss/category/local-news"],
  ["Dallas", "FOX 4", "https://www.fox4news.com/rss/category/local-news"],
  ["Boston", "Boston 25", "https://www.boston25news.com/arc/outboundfeeds/rss/category/news/local/?outputType=xml"],
];
const untag = (x) => x.replace(/<!\[CDATA\[|\]\]>/g, "").replace(/<[^>]+>/g, "").replace(/&amp;/g, "&").replace(/&#39;|&apos;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, "<").replace(/&gt;/g, ">").trim();
export async function news(env) {
  const cities = await Promise.all(NEWS_FEEDS.map(async ([city, station, url]) => {
    try {
      const t = await (await fetch(url, { headers: { "user-agent": "Mozilla/5.0 (JARVIS hub)" }, cf: { cacheTtl: 900, cacheEverything: true } })).text();
      const items = [...t.matchAll(/<item>([\s\S]*?)<\/item>/g)].slice(0, 8).map((m) => { const b = m[1]; const g = (k) => (b.match(new RegExp(`<${k}[^>]*>([\\s\\S]*?)<\\/${k}>`)) || [])[1] || ""; return { title: untag(g("title")), url: untag(g("link")) || untag(g("guid")), at: g("pubDate") ? new Date(untag(g("pubDate"))).toISOString() : null }; }).filter((i) => i.title);
      return { city, station, items };
    } catch (e) { return { city, station, items: [], error: e.message }; }
  }));
  return { at: new Date().toISOString(), cities };
}
export const newsSummary = (nw) => (nw?.cities || []).map((c) => `${c.city} (${c.station}): ` + c.items.slice(0, 4).map((i) => i.title).join(" / ")).join(" | ") || "unavailable";

/* wedding-day weather: forecast at the venue's city for every booked wedding in the next 10 days */
export async function weddingWeather(env) {
  const metrics = await kv.get(env, "metrics"); if (!metrics?.businesses) return {};
  const geo = (await kv.get(env, "geo")) || {}; const out = {}; const today = new Date(); today.setHours(0, 0, 0, 0);
  for (const [id, b] of Object.entries(metrics.businesses)) for (const e of b.upcoming || []) {
    if (!e.where) continue; const days = Math.floor((new Date(e.date + "T12:00") - today) / 86400e3); if (days < 0 || days > 10) continue;
    try {
      if (!geo[e.where]) { const g = await (await fetch("https://geocoding-api.open-meteo.com/v1/search?count=1&name=" + encodeURIComponent(e.where.split(",")[0]) + "&countryCode=US")).json(); const hit = (g.results || []).find((r) => !e.where.includes(",") || String(r.admin1 || "").toLowerCase().startsWith(stateName(e.where.split(",").pop().trim()).toLowerCase())) || g.results?.[0]; if (!hit) continue; geo[e.where] = { lat: hit.latitude, lon: hit.longitude, name: [hit.name, hit.admin1].filter(Boolean).join(", ") }; }
      const loc = geo[e.where];
      const w = await (await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${loc.lat}&longitude=${loc.lon}&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max,sunset&temperature_unit=fahrenheit&wind_speed_unit=mph&forecast_days=14&timezone=auto`, { cf: { cacheTtl: 1800, cacheEverything: true } })).json();
      const i = (w.daily?.time || []).indexOf(e.date); if (i < 0) continue;
      out[`${id}:${e.id || e.date}`] = { biz: id, date: e.date, title: e.title, where: loc.name, code: w.daily.weather_code[i], hi: Math.round(w.daily.temperature_2m_max[i]), lo: Math.round(w.daily.temperature_2m_min[i]), rain: w.daily.precipitation_probability_max[i] ?? 0, wind: Math.round(w.daily.wind_speed_10m_max[i]), sunset: (w.daily.sunset[i] || "").slice(11) };
    } catch {}
  }
  await kv.put(env, "geo", geo); await kv.put(env, "wxdays", { at: new Date().toISOString(), days: out });
  return out;
}
const STATES = { AL: "Alabama", AK: "Alaska", AZ: "Arizona", AR: "Arkansas", CA: "California", CO: "Colorado", CT: "Connecticut", DE: "Delaware", FL: "Florida", GA: "Georgia", HI: "Hawaii", ID: "Idaho", IL: "Illinois", IN: "Indiana", IA: "Iowa", KS: "Kansas", KY: "Kentucky", LA: "Louisiana", ME: "Maine", MD: "Maryland", MA: "Massachusetts", MI: "Michigan", MN: "Minnesota", MS: "Mississippi", MO: "Missouri", MT: "Montana", NE: "Nebraska", NV: "Nevada", NH: "New Hampshire", NJ: "New Jersey", NM: "New Mexico", NY: "New York", NC: "North Carolina", ND: "North Dakota", OH: "Ohio", OK: "Oklahoma", OR: "Oregon", PA: "Pennsylvania", RI: "Rhode Island", SC: "South Carolina", SD: "South Dakota", TN: "Tennessee", TX: "Texas", UT: "Utah", VT: "Vermont", VA: "Virginia", WA: "Washington", WV: "West Virginia", WI: "Wisconsin", WY: "Wyoming", DC: "District of Columbia" };
const stateName = (ab) => STATES[ab.toUpperCase()] || ab;
export const wxdaysSummary = (wd) => Object.values(wd?.days || {}).sort((a, b) => a.date.localeCompare(b.date)).map((d) => `${d.date} ${d.title} at ${d.where}: ${WMO[d.code] || "code " + d.code}, high ${d.hi} low ${d.lo}, rain ${d.rain}%, wind ${d.wind} mph, sunset ${d.sunset}`).join("; ") || "no booked weddings in the next 10 days with a known venue";
