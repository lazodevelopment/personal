// JARVIS hub worker.
// Dashboard + API: Google sign-in (one allowed email) or access key, site checks, weather/radar/alerts,
// a streaming Claude "brain" with pre-loaded context and confirm-first actions, ElevenLabs voice,
// morning brief, memory, calendar (private ICS), watchfulness (anomalies), and push via Pushover.
import Anthropic from "@anthropic-ai/sdk";
import html from "./hub.html";
import manifest from "./manifest.json";

export const SITES = [
  { id: "atavia", name: "Atavia Weddings", url: "https://ataviaweddings.com" },
  { id: "es", name: "Elizabeth Scott", url: "https://elizabethscottweddings.com" },
  { id: "lazo", name: "Lazo", url: "https://meetlazo.com" },
  { id: "roven", name: "Roven HR", url: "https://rovenhr.com" },
  { id: "lr", name: "LeaseReputation", url: "https://leasereputation.com" },
];
const BIZ_NAME = Object.fromEntries(SITES.map((s) => [s.id, s.name]));
const STATE_KEYS = ["brief", "webcams", "notes", "place", "metrics", "alerts", "memory", "queue", "calendar", "morning", "traffic", "tickers", "wxdays", "sports", "briefs", "stale", "inbox", "decisions", "home", "flights"];
const UA = "jarvis-hub (jesse@briskhealth.com)";
const MODEL = "claude-opus-5-5";

/* ---------------- helpers ---------------- */
const json = (data, status = 200, extra = {}) =>
  new Response(JSON.stringify(data), { status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", ...extra } });
const cookies = (req) => Object.fromEntries((req.headers.get("cookie") || "").split(/;\s*/).filter(Boolean).map((c) => { const i = c.indexOf("="); return [c.slice(0, i), c.slice(i + 1)]; }));
const kv = { get: (env, k) => env.HUB.get(k, "json"), put: (env, k, v) => env.HUB.put(k, JSON.stringify(v)) };
const localTime = (env, d = new Date(), opts = { dateStyle: "full", timeStyle: "short" }) => d.toLocaleString("en-US", { timeZone: env.TZ || "America/Chicago", ...opts });
const localHour = (env) => +new Date().toLocaleString("en-US", { timeZone: env.TZ || "America/Chicago", hour: "numeric", hour12: false });
const uid = () => Math.random().toString(36).slice(2, 10);

async function hmac(secret, msg) {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(msg));
  return btoa(String.fromCharCode(...new Uint8Array(sig))).replace(/=+$/, "").replace(/\+/g, "-").replace(/\//g, "_");
}
async function makeSession(env, email) { const body = `${email}|${Date.now() + 30 * 86400e3}`; return `${btoa(body)}.${await hmac(env.HUB_KEY, body)}`; }
async function readSession(env, token) {
  if (!token || !env.HUB_KEY) return null;
  const [b, sig] = token.split(".");
  try { const body = atob(b); if ((await hmac(env.HUB_KEY, body)) !== sig) return null; const [email, exp] = body.split("|"); return Date.now() > +exp ? null : email; } catch { return null; }
}
async function authed(request, env) {
  if (!env.HUB_KEY) return "dev";
  const hdr = request.headers.get("x-hub-key");
  if (hdr && hdr === env.HUB_KEY) return "key";
  const c = cookies(request);
  if (c.hub === env.HUB_KEY) return "key";
  return readSession(env, c.sess);
}
const setCookie = (name, value, maxAge = 31536000) => `${name}=${value}; Path=/; Max-Age=${maxAge}; HttpOnly; Secure; SameSite=Lax`;

/* ---------------- site checks + watchfulness ---------------- */
async function checkSite(site) {
  const t0 = Date.now();
  try {
    const ctl = new AbortController(); const timer = setTimeout(() => ctl.abort(), 8000);
    const r = await fetch(site.url, { redirect: "follow", signal: ctl.signal, cf: { cacheTtl: 0 }, headers: { "user-agent": UA } });
    clearTimeout(timer);
    return { ...site, ok: r.ok, status: r.status, ms: Date.now() - t0 };
  } catch (e) { return { ...site, ok: false, status: 0, ms: Date.now() - t0, error: String(e.message || e) }; }
}

async function pushAlert(env, alert) {
  const list = (await kv.get(env, "alerts")) || [];
  list.unshift({ ...alert, at: new Date().toISOString(), id: uid() });
  await kv.put(env, "alerts", list.slice(0, 80));
}

async function runChecks(env) {
  const results = await Promise.all(SITES.map(checkSite));
  const prev = (await kv.get(env, "uptime")) || {};
  const hist = (await kv.get(env, "rt_history")) || {};
  const now = {}; const nowIso = new Date().toISOString();
  for (const s of results) {
    const was = prev[s.id]?.ok;
    const fails = s.ok ? 0 : (prev[s.id]?.fails || 0) + 1;
    now[s.id] = { ok: s.ok, status: s.status, ms: s.ms, fails, since: was === s.ok ? prev[s.id]?.since : nowIso, slow: prev[s.id]?.slow || false };
    if (!s.ok && fails === 2) {
      await pushAlert(env, { kind: "down", site: s.id, text: `${s.name} is DOWN (${s.status || s.error || "no response"})` });
      await notify(env, `${s.name} is down`, `${s.url} returned ${s.status || s.error || "no response"} on two checks in a row.`, { priority: "urgent", tags: "rotating_light", url: s.url });
    }
    if (s.ok && was === false && (prev[s.id]?.fails || 0) >= 2) {
      await pushAlert(env, { kind: "up", site: s.id, text: `${s.name} is back up` });
      await notify(env, `${s.name} is back`, `${s.url} is responding again (${s.ms} ms).`, { tags: "white_check_mark", url: s.url });
    }
    // response-time history (5-minute samples, 24h) and slowness watch
    const h = hist[s.id] || []; if (s.ok) h.push([Date.now(), s.ms]); hist[s.id] = h.slice(-288);
    if (h.length >= 40) {
      const recent = h.slice(-6).map((x) => x[1]), base = h.slice(0, -6).map((x) => x[1]).sort((a, b) => a - b);
      const med = base[Math.floor(base.length / 2)], avg = recent.reduce((a, b) => a + b, 0) / recent.length;
      if (!now[s.id].slow && avg > 1500 && avg > 2.5 * med) {
        now[s.id].slow = true;
        await pushAlert(env, { kind: "slow", site: s.id, text: `${s.name} is slow: ${Math.round(avg)} ms vs ${med} ms typical` });
        await notify(env, `${s.name} is slow`, `Averaging ${Math.round(avg)} ms over the last 30 min, typical is ${med} ms.`, { priority: "high", tags: "hourglass", url: s.url });
      } else if (now[s.id].slow && avg < 1.5 * med) now[s.id].slow = false;
    }
  }
  await kv.put(env, "uptime", now); await kv.put(env, "rt_history", hist);
  await kv.put(env, "status", { checkedAt: nowIso, sites: results });

  const brief = await kv.get(env, "brief");
  if (brief?.items?.length) {
    const seen = (await kv.get(env, "nudged")) || {}; let changed = false;
    for (const m of brief.items) {
      if (!m.needs_reply || !m.url || seen[m.url]) continue;
      const age = m.received ? Date.now() - new Date(m.received) : 0;
      if (age > 2 * 3600e3) {
        seen[m.url] = Date.now(); changed = true;
        await pushAlert(env, { kind: "lead", text: `Unanswered for ${Math.round(age / 3600e3)}h: ${m.from} — ${m.subject}`, url: m.url });
        await notify(env, "Lead waiting on you", `${m.from}: ${m.subject}\n${m.snippet || ""}`, { priority: "high", tags: "envelope", url: m.url });
      }
    }
    if (changed) await kv.put(env, "nudged", seen);
  }
  return results;
}

// called when the collector posts fresh metrics: compare with the previous snapshot
async function watchMetrics(env, next) {
  const prev = await kv.get(env, "metrics_prev");
  await kv.put(env, "metrics_prev", next);
  const expired = Object.entries(next.businesses || {}).filter(([, b]) => /sign-in expired|Reauthentication/i.test(b.error || "")).map(([id]) => BIZ_NAME[id]);
  const wasExpired = Object.values(prev?.businesses || {}).some((b) => /sign-in expired|Reauthentication/i.test(b.error || ""));
  if (expired.length && !wasExpired) {
    await pushAlert(env, { kind: "watch", text: `Google sign-in on the PC expired: no data for ${expired.join(", ")} until you run gcloud auth application-default login` });
    await notify(env, "Google sign-in expired", `${expired.join(", ")} metrics are paused. On the PC run: gcloud auth application-default login`, { priority: "high", tags: "key" });
  }
  if (!prev?.businesses) return;
  const notes = [];
  for (const [id, b] of Object.entries(next.businesses || {})) {
    const p = prev.businesses?.[id]; if (!p?.headline || !b?.headline) continue;
    for (const k of b.headline) {
      const pk = p.headline.find((x) => x.label === k.label); if (!pk || typeof k.value !== "number" || typeof pk.value !== "number") continue;
      if (/leads|inquir|applications|reviews|couples|users/i.test(k.label) && pk.value >= 5 && k.value <= pk.value * 0.4) notes.push(`${BIZ_NAME[id]}: ${k.label} fell from ${pk.value} to ${k.value}`);
      if (/pending|due|unanswered/i.test(k.label) && k.value >= pk.value + 5) notes.push(`${BIZ_NAME[id]}: ${k.label} jumped to ${k.value}`);
    }
    const bc = b.counts || {}, pc = p.counts || {};
    if ((bc.inquiries_unanswered || 0) >= 5 && (bc.inquiries_unanswered || 0) > (pc.inquiries_unanswered || 0)) notes.push(`${BIZ_NAME[id]}: ${bc.inquiries_unanswered} vendor inquiries unanswered`);
  }
  const seen = (await kv.get(env, "watch_seen")) || {};
  for (const n of notes) {
    const key = n.replace(/\d+/g, "#"); if (seen[key] && Date.now() - seen[key] < 6 * 3600e3) continue;
    seen[key] = Date.now();
    await pushAlert(env, { kind: "watch", text: n });
    await notify(env, "JARVIS noticed", n, { tags: "eyes" });
  }
  await kv.put(env, "watch_seen", seen);
}

// new items waiting on Jesse (Lazo claims, Roven reviews): push once per item
async function watchDecisions(env, dec) {
  const seen = (await kv.get(env, "decisions_seen")) || {}; const now = Date.now(); let changed = false;
  for (const it of dec.items || []) {
    if (seen[it.id]) continue; seen[it.id] = now; changed = true;
    const title = it.kind === "lazo_claim" ? "Lazo claim to review" : it.kind === "roven_approve_job" ? "Roven job to review" : "Roven employer to review";
    await pushAlert(env, { kind: "watch", text: `${title}: ${it.label.replace(/^[^:]+:\s*/, "")}` });
    await notify(env, title, it.label.replace(/^[^:]+:\s*/, "") + "\nOpen JARVIS → Decisions to approve or reject.", { priority: "high", tags: "ballot_box_with_check", url: "https://jarvis-hub.floral-credit-e4f0.workers.dev/#decisions" });
  }
  for (const id of Object.keys(seen)) if (now - seen[id] > 30 * 86400e3) { delete seen[id]; changed = true; }
  if (changed) await kv.put(env, "decisions_seen", seen);
}

/* ---------------- notifications ---------------- */
async function notify(env, title, body, { priority = "default", tags = "", url = "" } = {}) {
  const out = [];
  if (env.PUSHOVER_TOKEN && env.PUSHOVER_USER) {
    const form = new URLSearchParams({ token: env.PUSHOVER_TOKEN, user: env.PUSHOVER_USER, title: "JARVIS: " + title, message: body, priority: priority === "urgent" ? "1" : priority === "high" ? "0" : "-1", sound: priority === "urgent" ? "siren" : "pushover", ...(url ? { url } : {}) });
    out.push(fetch("https://api.pushover.net/1/messages.json", { method: "POST", body: form }).then(async (r) => ({ pushover: r.status, detail: r.ok ? undefined : (await r.text()).slice(0, 200) })).catch((e) => ({ pushover: "error", detail: String(e.message || e) })));
  }
  if (env.NTFY_TOPIC) {
    out.push(fetch("https://ntfy.sh/" + env.NTFY_TOPIC, { method: "POST", body, headers: { "user-agent": UA, Title: title, Priority: priority, ...(tags ? { Tags: tags } : {}), ...(url ? { Click: url } : {}) } }).then((r) => ({ ntfy: r.status })).catch((e) => ({ ntfy: "error", detail: String(e.message || e) })));
  }
  if (env.RESEND_API_KEY && env.ALERT_EMAIL) {
    out.push(fetch("https://api.resend.com/emails", { method: "POST", headers: { authorization: "Bearer " + env.RESEND_API_KEY, "content-type": "application/json" },
      body: JSON.stringify({ from: env.ALERT_FROM || "JARVIS <onboarding@resend.dev>", to: [env.ALERT_EMAIL], subject: "JARVIS: " + title, text: body + (url ? "\n\n" + url : "") }) }).then((r) => ({ email: r.status })).catch((e) => ({ email: "error", detail: String(e.message || e) })));
  }
  return Promise.all(out);
}

/* ---------------- weather ---------------- */
async function weatherData(request, env, place) {
  const cf = request.cf || {};
  const lat = place?.lat || cf.latitude, lon = place?.lon || cf.longitude;
  if (!lat || !lon) return { error: "no location" };
  const q = new URLSearchParams({ latitude: lat, longitude: lon,
    current: "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m,wind_gusts_10m,is_day,precipitation,uv_index,pressure_msl,visibility",
    daily: "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,sunrise,sunset,uv_index_max,wind_speed_10m_max",
    hourly: "temperature_2m,weather_code,precipitation_probability,precipitation,wind_speed_10m,relative_humidity_2m",
    temperature_unit: "fahrenheit", wind_speed_unit: "mph", precipitation_unit: "inch", forecast_days: "7", timezone: "auto" });
  const [wx, aq, al] = await Promise.all([
    fetch("https://api.open-meteo.com/v1/forecast?" + q, { cf: { cacheTtl: 600, cacheEverything: true } }).then((r) => r.json()),
    fetch(`https://air-quality-api.open-meteo.com/v1/air-quality?latitude=${lat}&longitude=${lon}&current=us_aqi,pm2_5&timezone=auto`, { cf: { cacheTtl: 1800, cacheEverything: true } }).then((r) => r.json()).catch(() => null),
    fetch(`https://api.weather.gov/alerts/active?point=${(+lat).toFixed(4)},${(+lon).toFixed(4)}`, { headers: { "user-agent": UA, accept: "application/geo+json" }, cf: { cacheTtl: 300, cacheEverything: true } }).then((r) => r.json()).catch(() => ({ features: [] })),
  ]);
  wx.aqi = aq?.current || null; wx.lat = +lat; wx.lon = +lon;
  wx.place = place?.name || [cf.city, cf.regionCode].filter(Boolean).join(", ") || "Your location";
  wx.nws = (al.features || []).map((f) => ({ id: f.id, event: f.properties.event, severity: f.properties.severity, headline: f.properties.headline, ends: f.properties.ends || f.properties.expires }));
  return wx;
}
const WMO = { 0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast", 45: "fog", 48: "fog", 51: "drizzle", 53: "drizzle", 55: "drizzle", 61: "light rain", 63: "rain", 65: "heavy rain", 71: "snow", 73: "snow", 75: "snow", 80: "showers", 81: "showers", 82: "heavy showers", 95: "thunderstorms", 96: "thunderstorms", 99: "thunderstorms" };
function weatherSummary(w) {
  if (!w || w.error) return "unavailable";
  const c = w.current, d = w.daily;
  const days = d.time.slice(0, 4).map((t, i) => `${i === 0 ? "today" : new Date(t + "T12:00").toLocaleDateString("en-US", { weekday: "short" })} ${WMO[d.weather_code[i]] || ""} ${Math.round(d.temperature_2m_max[i])}/${Math.round(d.temperature_2m_min[i])} rain ${d.precipitation_probability_max[i] ?? 0}%`).join("; ");
  return `${w.place}: ${Math.round(c.temperature_2m)}°F ${WMO[c.weather_code] || ""}, feels ${Math.round(c.apparent_temperature)}, wind ${Math.round(c.wind_speed_10m)} mph gusting ${Math.round(c.wind_gusts_10m)}, humidity ${c.relative_humidity_2m}%, UV ${c.uv_index}, AQI ${w.aqi?.us_aqi ?? "n/a"}. Sunrise ${d.sunrise[0].slice(11)} sunset ${d.sunset[0].slice(11)}. Outlook: ${days}.${w.nws.length ? " NWS ALERTS: " + w.nws.map((a) => a.headline).join(" | ") : ""}`;
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
async function loadCalendar(env, force) {
  if (!env.CAL_ICS_URL) return null;
  const cached = await kv.get(env, "calendar");
  if (cached && !force && Date.now() - new Date(cached.at) < 30 * 60000) return cached;
  try {
    const text = await (await fetch(env.CAL_ICS_URL, { headers: { "user-agent": UA } })).text();
    const from = Date.now() - 86400e3, to = Date.now() + 60 * 86400e3;
    const events = parseICS(text).filter((e) => !e.recurring && new Date(e.start) >= from && new Date(e.start) <= to).sort((a, b) => a.start.localeCompare(b.start)).slice(0, 60);
    const cal = { at: new Date().toISOString(), events }; await kv.put(env, "calendar", cal); return cal;
  } catch (e) { return cached || { at: new Date().toISOString(), events: [], error: e.message }; }
}


/* ---------------- sports (ESPN public scoreboard), markets (Yahoo chart meta), news (RSS) ---------------- */
const LEAGUES = { nfl: "football/nfl", mlb: "baseball/mlb", nba: "basketball/nba", nhl: "hockey/nhl" };
const ymd = (d) => d.toISOString().slice(0, 10).replace(/-/g, "");
async function sports(env) {
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
function sportsSummary(sp) {
  if (!sp?.games) return "unavailable";
  if (sp.teams?.length) { const t = sp.teams.map((t) => `${t.name} (${t.record || "?"}${t.division ? `, ${t.rank}${["th","st","nd","rd"][t.rank] || "th"} in the ${t.division}` : ""}): ` + (t.next ? (t.next.state === "in" ? `LIVE ${t.next.my}-${t.next.their} vs ${t.next.opp} ${t.next.detail}` : `next ${t.next.home ? "vs" : "at"} ${t.next.opp} ${new Date(t.next.date).toLocaleString("en-US", { timeZone: "America/Chicago", weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}${t.next.tv ? " on " + t.next.tv : ""}`) : (t.note || "no game scheduled")) + (t.last ? `; last ${t.last.won ? "won" : "lost"} ${t.last.my}-${t.last.their} ${t.last.home ? "vs" : "at"} ${t.last.opp}` : "") + ((t.upcoming || []).length > 1 ? `; then ` + t.upcoming.slice(1, 4).map((g) => `${g.home ? "vs" : "at"} ${g.opp} ${new Date(g.date).toLocaleDateString("en-US", { timeZone: "America/Chicago", month: "short", day: "numeric" })}`).join(", ") : "")).join(" | "); return t; }
  const f = sp.games.filter((g) => g.fav);
  if (!f.length) return "no games for the favourite teams yesterday, today or tomorrow";
  return f.map((g) => { const [a, b] = g.teams; const who = g.teams.find((t) => sp.fav.includes(t.abbr)); const opp = g.teams.find((t) => t !== who);
    if (g.state === "in") return `${who.name} ${who.score}-${opp.score} ${opp.name} LIVE (${g.detail})`;
    if (g.state === "post") return `${who.name} ${who.winner ? "beat" : "lost to"} ${opp.name} ${who.score}-${opp.score}`;
    return `${who.name} vs ${opp.name} ${new Date(g.date).toLocaleString("en-US", { timeZone: "America/Chicago", weekday: "short", hour: "numeric", minute: "2-digit" })}${g.tv ? " on " + g.tv : ""}`; }).join("; ");
}

const INDEXES = [["^GSPC", "S&P 500"], ["^DJI", "Dow"], ["^IXIC", "Nasdaq"]];
async function markets(env) {
  const user = (await kv.get(env, "tickers")) || [];
  const syms = [...INDEXES.map(([s]) => s), ...user.map((t) => String(t).toUpperCase())];
  const rows = await Promise.all(syms.map(async (sym) => {
    try {
      const r = await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(sym)}?range=1d&interval=5m`, { headers: { "user-agent": "Mozilla/5.0" }, cf: { cacheTtl: 120, cacheEverything: true } });
      const m = (await r.json()).chart?.result?.[0]?.meta; if (!m) return { sym, error: "no data" };
      const price = m.regularMarketPrice, prev = m.chartPreviousClose ?? m.previousClose;
      return { sym, name: INDEXES.find(([s]) => s === sym)?.[1] || m.shortName || sym, price, prev, change: price - prev, pct: prev ? (price - prev) / prev * 100 : 0, state: m.marketState || "", time: m.regularMarketTime };
    } catch (e) { return { sym, error: e.message }; }
  }));
  return { at: new Date().toISOString(), rows };
}
const marketsSummary = (mk) => (mk?.rows || []).filter((r) => !r.error).map((r) => `${r.name} ${r.price >= 1000 ? Math.round(r.price).toLocaleString() : r.price.toFixed(2)} (${r.pct >= 0 ? "+" : ""}${r.pct.toFixed(2)}%)`).join(", ") || "unavailable";

const NEWS_FEEDS = [
  ["Phoenix", "FOX 10", "https://www.fox10phoenix.com/rss/category/local-news"],
  ["Dallas", "FOX 4", "https://www.fox4news.com/rss/category/local-news"],
  ["Boston", "Boston 25", "https://www.boston25news.com/arc/outboundfeeds/rss/category/news/local/?outputType=xml"],
];
const untag = (x) => x.replace(/<!\[CDATA\[|\]\]>/g, "").replace(/<[^>]+>/g, "").replace(/&amp;/g, "&").replace(/&#39;|&apos;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, "<").replace(/&gt;/g, ">").trim();
async function news(env) {
  const cities = await Promise.all(NEWS_FEEDS.map(async ([city, station, url]) => {
    try {
      const t = await (await fetch(url, { headers: { "user-agent": "Mozilla/5.0 (JARVIS hub)" }, cf: { cacheTtl: 900, cacheEverything: true } })).text();
      const items = [...t.matchAll(/<item>([\s\S]*?)<\/item>/g)].slice(0, 8).map((m) => { const b = m[1]; const g = (k) => (b.match(new RegExp(`<${k}[^>]*>([\\s\\S]*?)<\\/${k}>`)) || [])[1] || ""; return { title: untag(g("title")), url: untag(g("link")) || untag(g("guid")), at: g("pubDate") ? new Date(untag(g("pubDate"))).toISOString() : null }; }).filter((i) => i.title);
      return { city, station, items };
    } catch (e) { return { city, station, items: [], error: e.message }; }
  }));
  return { at: new Date().toISOString(), cities };
}
const newsSummary = (nw) => (nw?.cities || []).map((c) => `${c.city} (${c.station}): ` + c.items.slice(0, 4).map((i) => i.title).join(" / ")).join(" | ") || "unavailable";

/* wedding-day weather: forecast at the venue's city for every booked wedding in the next 10 days */
async function weddingWeather(env) {
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
const wxdaysSummary = (wd) => Object.values(wd?.days || {}).sort((a, b) => a.date.localeCompare(b.date)).map((d) => `${d.date} ${d.title} at ${d.where}: ${WMO[d.code] || "code " + d.code}, high ${d.hi} low ${d.lo}, rain ${d.rain}%, wind ${d.wind} mph, sunset ${d.sunset}`).join("; ") || "no booked weddings in the next 10 days with a known venue";


/* ---------------- Gmail bridges (Apps Script in each account) ---------------- */
const BIZ_LABEL = { atavia: "Atavia", es: "Elizabeth Scott", lazo: "Lazo", roven: "Roven", lr: "LeaseReputation", brisk: "Brisk", other: "Other" };

// Claude triages new threads: needs a reply? one-line summary, priority. Cached per thread+last message.
async function triage(env, items) {
  if (!env.ANTHROPIC_API_KEY || !items.length) return {};
  const client = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY });
  const list = items.map((m, i) => `${i + 1}. from: ${m.from} | subject: ${m.subject} | last message from us: ${m.lastFromMe} | messages: ${m.count} | text: ${(m.snippet || "").slice(0, 300)}`).join("\n");
  const r = await client.beta.messages.create({
    model: MODEL, max_tokens: 3000, betas: ["server-side-fallback-2026-07-01"], fallbacks: "default", output_config: { effort: "low" },
    system: "You triage a small business owner's inbox (wedding films, a wedding-planner app, a hiring platform, apartment reviews). For each numbered thread return JSON only: an array of objects {\"n\": number, \"needs_reply\": boolean, \"summary\": string (max 110 chars, plain, what it is or asks), \"priority\": 1|2|3, \"kind\": \"lead\"|\"client\"|\"booking\"|\"payment\"|\"vendor\"|\"notification\"|\"newsletter\"|\"other\"}. needs_reply is true only when a real person is asking the business something and the last message is not from us. priority 1 = money or a client waiting, 2 = worth reading today, 3 = noise.",
    messages: [{ role: "user", content: list }],
  });
  const text = r.content.filter((b) => b.type === "text").map((b) => b.text).join("");
  try { const arr = JSON.parse(text.slice(text.indexOf("["), text.lastIndexOf("]") + 1)); return Object.fromEntries(arr.map((x) => [items[x.n - 1]?.threadId, x]).filter(([k]) => k)); } catch { return {}; }
}

async function ingestInbox(env, body, ctx) {
  const account = String(body.account || "").toLowerCase(); if (!account) return json({ error: "no account" }, 400);
  const inbox = (await kv.get(env, "inbox")) || { accounts: {} };
  const cache = (await kv.get(env, "inbox_class")) || {};
  const items = (body.items || []).slice(0, 60);
  const fresh = items.filter((m) => !cache[m.threadId] || cache[m.threadId].date !== m.date);
  let classes = {}; try { classes = await triage(env, fresh); } catch (e) { console.log("triage failed", e.message); }
  for (const m of fresh) { const c = classes[m.threadId]; if (c) cache[m.threadId] = { date: m.date, needs_reply: !!c.needs_reply, summary: c.summary, priority: c.priority, kind: c.kind }; }
  const keep = Object.fromEntries(Object.entries(cache).filter(([, v]) => Date.now() - new Date(v.date) < 14 * 86400e3)); await kv.put(env, "inbox_class", keep);
  inbox.accounts[account] = { business: body.business || "other", at: new Date().toISOString(), items: items.map((m) => ({ ...m, ...(keep[m.threadId] ? { needs_reply: keep[m.threadId].needs_reply && !m.lastFromMe, summary: keep[m.threadId].summary, priority: keep[m.threadId].priority, kind: keep[m.threadId].kind } : {}) })) };
  await kv.put(env, "inbox", inbox);
  if (body.secret) {
    // Apps Script reports its signed-in test URL (/a/<domain>/macros/...); only a public /macros/s/.../exec deployment URL works for the hub.
    const hooks = (await kv.get(env, "inbox_hooks")) || {}; const cur = hooks[account] || {};
    const reported = /^https:\/\/script\.google\.com\/macros\/s\/[^/]+\/exec$/.test(body.hookUrl || "") ? body.hookUrl : null;
    hooks[account] = { ...cur, url: cur.pinned ? cur.url : (reported || cur.url || null), secret: body.secret, business: body.business || "other", at: new Date().toISOString() };
    await kv.put(env, "inbox_hooks", hooks);
  }
  // the Inbox panel, the nudges and the briefs all read `brief`; rebuild it from every bridged account
  const all = Object.entries(inbox.accounts).flatMap(([acct, a]) => a.items.map((m) => ({ business: a.business, account: acct, threadId: m.threadId, from: m.from.replace(/<.*>/, "").trim() || m.fromEmail, when: new Date(m.date).toLocaleString("en-US", { timeZone: env.TZ || "America/Chicago", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }), received: m.date, subject: m.subject, snippet: m.summary || m.snippet?.slice(0, 120) || "", url: m.link, needs_reply: !!m.needs_reply, unread: !!m.unread, priority: m.priority || 3, kind: m.kind || "" })));
  all.sort((a, b) => (b.needs_reply - a.needs_reply) || (a.priority - b.priority) || b.received.localeCompare(a.received));
  const needs = all.filter((m) => m.needs_reply).length, unread = all.filter((m) => m.unread).length;
  await kv.put(env, "brief", { at: new Date().toISOString(), source: "bridge", accounts: Object.keys(inbox.accounts), note: all.length ? `${unread} unread across ${Object.keys(inbox.accounts).length} inbox${Object.keys(inbox.accounts).length > 1 ? "es" : ""}, ${needs} need${needs === 1 ? "s" : ""} a reply` : "All inboxes clear.", items: all.slice(0, 40) });
  return json({ ok: true, account, items: items.length, triaged: fresh.length, hook: !!body.hookUrl });
}

async function bridgeCall(env, account, payload) {
  const hooks = (await kv.get(env, "inbox_hooks")) || {};
  const hook = hooks[String(account || "").toLowerCase()];
  if (!hook?.url) return { error: "no Gmail bridge with actions for " + account };
  const r = await fetch(hook.url, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ secret: hook.secret, ...payload }), redirect: "follow" });
  const t = await r.text(); try { return JSON.parse(t); } catch { return { error: "bridge returned " + r.status + (t.includes("<") ? " (update the bridge script and deploy a new version)" : "") }; }
}

async function emailAction(env, item) {
  const hooks = (await kv.get(env, "inbox_hooks")) || {}; const p = item.params || {};
  const hook = hooks[String(p.account || "").toLowerCase()] || Object.values(hooks).find((h) => h.business === p.business);
  if (!hook?.url) return { ok: false, message: "no Gmail bridge for " + (p.account || p.business || "that account") };
  const action = item.kind.replace("email_", "");
  const r = await fetch(hook.url, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ secret: hook.secret, action, threadId: p.threadId, body: p.body, to: p.to, subject: p.subject }), redirect: "follow" });
  const txt = await r.text(); let j = {}; try { j = JSON.parse(txt); } catch {}
  return j.ok ? { ok: true, message: j.did || action } : { ok: false, message: j.error || ("bridge " + r.status) };
}

const within = (p, ms, fallback = null) => Promise.race([p.catch(() => fallback), new Promise((r) => setTimeout(() => r(fallback), ms))]);
async function cached(env, key, ttlMs, fn) {
  const c = await kv.get(env, "cache_" + key);
  if (c && Date.now() - c.t < ttlMs) return c.v;
  const v = await within(fn(), 3000, c?.v ?? null);
  if (v) await kv.put(env, "cache_" + key, { t: Date.now(), v });
  return v;
}


/* ---------------- World: flights, satellites, quakes, wildfires ---------------- */
const AIRLINES = { AA: "AAL", UA: "UAL", DL: "DAL", WN: "SWA", AS: "ASA", B6: "JBU", NK: "NKS", F9: "FFT", G4: "AAY", HA: "HAL", SY: "SCX", AC: "ACA", WS: "WJA", MX: "MXY", QX: "QXE", OO: "SKW", YX: "RPA", MQ: "ENY", "9E": "EDV", BA: "BAW", LH: "DLH", AF: "AFR", KL: "KLM", AM: "AMX", Y4: "VOI" };
function toCallsign(q) {
  const t = String(q || "").toUpperCase().replace(/[\s-]+/g, "");
  const m = t.match(/^([A-Z0-9]{2})(\d{1,4}[A-Z]?)$/); if (m && AIRLINES[m[1]]) return AIRLINES[m[1]] + m[2];
  return t;
}
const acOut = (a) => ({ hex: a.hex, flight: (a.flight || "").trim(), reg: a.r || "", type: a.t || "", lat: a.lat, lon: a.lon, alt: a.alt_baro === "ground" ? 0 : (a.alt_baro ?? a.alt_geom ?? null), gs: a.gs != null ? Math.round(a.gs) : null, track: a.track ?? null, squawk: a.squawk || "", emergency: a.emergency && a.emergency !== "none" ? a.emergency : "", desc: a.desc || "", ownOp: a.ownOp || "" });
async function flightsNear(env, lat, lon, nm = 40) {
  const f = await kv.get(env, "flights"); if (!f?.ac) return [];
  const R = 3440.065, toR = Math.PI / 180;
  const dist = (a) => 2 * R * Math.asin(Math.sqrt(Math.sin((a.lat - lat) * toR / 2) ** 2 + Math.cos(lat * toR) * Math.cos(a.lat * toR) * Math.sin((a.lon - lon) * toR / 2) ** 2));
  return f.ac.filter((a) => dist(a) <= nm);
}
async function trackFlight(env, q) {
  const cs = toCallsign(q);
  const want = (await kv.get(env, "track_req")) || {}; want[cs] = Date.now(); await kv.put(env, "track_req", want);
  const f = await kv.get(env, "flights");
  const ac = f?.tracks?.[cs] || (f?.ac || []).filter((a) => a.flight === cs || a.reg === cs);
  return { query: q, callsign: cs, found: ac.length > 0, aircraft: ac, asOf: f?.at || null, note: ac.length ? undefined : "Tracking requested; the PC feed checks it within a minute." };
}
async function worldEvents(env) {
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
async function satTles(env) {
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


/* ---------------- cameras (directory from the PC), global flights, routes ---------------- */
let camMem = null; // per-isolate cache of the camera directory
let placeMem = null;
async function placesAll(env) {
  if (placeMem && Date.now() - placeMem.t < 5 * 60e3) return placeMem.v;
  const v = (await env.HUB.get("places", "json")) || []; placeMem = { t: Date.now(), v }; return v;
}
async function camsAll(env) {
  if (camMem && Date.now() - camMem.t < 10 * 60e3) return camMem.v;
  const v = (await env.HUB.get("cams", "json")) || []; camMem = { t: Date.now(), v }; return v;
}
// Windy webcams: search near the view centre (radius km, max 250). Free-tier image URLs carry a token that expires in 10 min.
async function windyNear(env, lat, lon, km) {
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

async function txSnapshot(d, id) {
  const j = await (await fetch(`https://its.txdot.gov/its/DistrictIts/GetCctvSnapshotByIcdId?districtCode=${encodeURIComponent(d)}&icdId=${encodeURIComponent(id)}`, { headers: { "user-agent": "Mozilla/5.0 (JARVIS hub)" }, cf: { cacheTtl: 30, cacheEverything: true } })).json();
  if (!j.snippet) return null;
  return new Response(Uint8Array.from(atob(j.snippet), (c) => c.charCodeAt(0)), { headers: { "content-type": "image/jpeg", "cache-control": "public, max-age=30" } });
}
async function flightRoute(env, cs) {
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

/* ---------------- context for the brain ---------------- */
async function buildContext(env, request) {
  const [status, metrics, brief, notes, memory, alerts, place, cal, morning, queue, traffic, wxdays] = await Promise.all(["status", "metrics", "brief", "notes", "memory", "alerts", "place", "calendar", "morning", "queue", "traffic", "wxdays"].map((k) => kv.get(env, k)));
  const [wx, sp, mk, nw] = await Promise.all([within(weatherData(request, env, place), 3000), kv.get(env, "sports"), cached(env, "markets", 5 * 60e3, () => markets(env)), cached(env, "news", 15 * 60e3, () => news(env))]);
  const lines = [];
  lines.push(`TIME: ${localTime(env)} (${env.TZ || "America/Chicago"})`);
  lines.push(`SITES: ` + (status?.sites || []).map((s) => `${s.name} ${s.ok ? "up" : "DOWN"} ${s.ms}ms`).join(", "));
  lines.push(`WEATHER: ${weatherSummary(wx)}`);
  const we = await kv.get(env, "cache_world_events");
  if (we?.v) lines.push(`WORLD: ${we.v.quakes.filter((q) => q.mag >= 4.5).length} quakes M4.5+ in the last day${we.v.quakes.length ? ", largest M" + Math.max(...we.v.quakes.map((q) => q.mag)).toFixed(1) + " " + (we.v.quakes.sort((a, b) => b.mag - a.mag)[0]?.place || "") : ""}; ${we.v.fires.length} active US wildfires over 100 acres${we.v.fires[0] ? ", largest " + we.v.fires[0].name + " (" + we.v.fires[0].state + ") " + we.v.fires[0].acres.toLocaleString() + " acres " + (we.v.fires[0].contained ?? "?") + "% contained" : ""}; ISS at ${we.v.iss ? we.v.iss.lat.toFixed(1) + "," + we.v.iss.lon.toFixed(1) : "?"}`);
  lines.push(`WEDDING-DAY WEATHER (next 10 days): ${wxdaysSummary(wxdays)}`);
  lines.push(`SPORTS (his teams: Cowboys, Patriots, Rangers, Rockies, Red Sox, Diamondbacks): ${sportsSummary(sp)}`);
  lines.push(`MARKETS: ${marketsSummary(mk)}`);
  lines.push(`LOCAL NEWS: ${newsSummary(nw)}`);
  if (traffic?.sites) lines.push(`WEB TRAFFIC (as of ${traffic.at}, day ${traffic.day}): ` + Object.entries(traffic.sites).map(([id, t]) => t.error ? `${BIZ_NAME[id]} ${t.error}` : `${BIZ_NAME[id]}: ${t.online} online now, ${t.today} visitors today, ${t.views} page views, top pages ${(t.pages || []).slice(0, 3).map((p) => p[0] + " " + p[1]).join(", ")}, sources ${(t.sources || []).map((p) => p[0] + " " + p[1]).join(", ")}`).join(" | "));
  if (metrics?.businesses) {
    lines.push(`METRICS (collected ${metrics.collectedAt}):`);
    for (const [id, b] of Object.entries(metrics.businesses)) {
      if (b.error) { lines.push(`- ${BIZ_NAME[id]}: ${b.error}`); continue; }
      lines.push(`- ${BIZ_NAME[id]}: ` + b.headline.map((k) => `${k.label}=${k.money ? "$" + Math.round(k.value).toLocaleString() : k.value}${k.delta != null ? ` (${k.delta >= 0 ? "+" : ""}${k.deltaUnit === "$" ? "$" : ""}${k.delta}${k.deltaUnit && k.deltaUnit !== "$" ? k.deltaUnit : ""} ${k.deltaLabel ?? "vs prior"})` : ""}`).join(", ") + (b.counts ? " | " + Object.entries(b.counts).map(([k, v]) => `${k}=${v}`).join(", ") : ""));
      if (b.upcoming?.length) lines.push(`  upcoming: ` + b.upcoming.slice(0, 6).map((e) => `${e.date} ${e.title}`).join("; "));
      if (b.detail?.recent?.length) lines.push(`  recent bookings/items: ` + b.detail.recent.slice(0, 8).map((e) => `${e.id ? "[" + e.id + "] " : ""}${e.names} ${e.date || ""} ${e.package || ""} ${e.total != null ? "$" + e.total : ""} ${e.status || ""}`.replace(/\s+/g, " ").trim()).join("; "));
      if (b.detail?.pending?.length) lines.push(`  pending items (ids for actions): ` + b.detail.pending.slice(0, 10).map((e) => `[${e.id}] ${e.label}`).join("; "));
      if (b.detail?.leadsBySource) lines.push(`  leads by source (90d): ` + Object.entries(b.detail.leadsBySource).map(([k, v]) => `${k} ${v}`).join(", "));
    }
    if (metrics.money) lines.push(`MONEY: this month $${Math.round(metrics.money.thisMonth).toLocaleString()} (last month $${Math.round(metrics.money.lastMonth).toLocaleString()}); recent months: ` + metrics.money.months.slice(-6).map((m) => `${m.ym} $${Math.round(m.total)}`).join(", "));
  } else lines.push("METRICS: none collected yet");
  lines.push(`INBOX (${brief?.source === "bridge" ? "live Gmail bridges" : "hourly snapshot"}, ${brief?.at || "none"}): ${brief?.note || ""} ` + (brief?.items || []).slice(0, 20).map((m) => `[${BIZ_LABEL[m.business] || m.business || ""} | ${m.account || ""} | ${m.threadId || "no-id"}] ${m.from}: ${m.subject}${m.needs_reply ? " (NEEDS REPLY)" : ""}${m.unread ? " (unread)" : ""} — ${m.snippet || ""}`).join(" | "));
  lines.push(`ALERTS (latest): ` + (alerts || []).slice(0, 6).map((a) => `${a.at.slice(0, 16)} ${a.text}`).join(" | "));
  if (cal?.events?.length) lines.push(`CALENDAR (next 60d): ` + cal.events.slice(0, 20).map((e) => `${e.start.slice(0, 16)} ${e.title}${e.location ? " @ " + e.location : ""}`).join("; "));
  else lines.push("CALENDAR: not connected");
  lines.push(`NOTES:\n${notes || "(empty)"}`);
  lines.push(`MEMORY: ` + ((memory || []).map((m) => `[${m.id}] ${m.text}`).join(" | ") || "(nothing remembered yet)"));
  const dec = await kv.get(env, "decisions");
  lines.push(`WAITING ON JESSE (${dec?.at || "none"}): ` + ((dec?.items || []).map((d) => `[${d.id}] ${d.label} (${d.kind}, ${d.at.slice(0, 10)})`).join(" | ") || "nothing pending"));
  if (queue?.length) lines.push(`RECENT ACTIONS: ` + queue.slice(0, 5).map((q) => `${q.summary} → ${q.status}${q.result ? " (" + q.result + ")" : ""}`).join(" | "));
  if (morning?.at) lines.push(`LATEST BRIEF (${morning.slot || "morning"}, ${morning.at}): ${(morning.text || "").slice(0, 600)}`);
  return lines.join("\n");
}

const LINKS = {
  atavia: { site: "https://ataviaweddings.com", admin: "https://atavia-admin.pages.dev", firebase: "https://console.firebase.google.com/project/atavia-c29cd/overview" },
  es: { site: "https://elizabethscottweddings.com", admin: "https://admin.elizabethscottweddings.com", firebase: "https://console.firebase.google.com/project/elizabeth-scott-738e5/overview" },
  lazo: { site: "https://meetlazo.com", appstore: "https://apps.apple.com/us/app/lazo-wedding-planner/id6812863675", firebase: "https://console.firebase.google.com/project/lazo-513ec/overview", asc: "https://appstoreconnect.apple.com/apps" },
  roven: { site: "https://rovenhr.com", app: "https://app.rovenhr.com" },
  lr: { site: "https://leasereputation.com", app: "https://app.leasereputation.com", firebase: "https://console.firebase.google.com/project/lease-reputation/overview" },
  scanner: { frisco_calls: "https://www.broadcastify.com/calls/playlists/?a=view&uuid=8bf99044-c41f-11ee-a225-0e676e2c8629", frisco_fire: "https://www.broadcastify.com/listen/feed/39916", collin_county: "https://www.broadcastify.com/listen/feed/22147", phoenix_police: "https://www.broadcastify.com/listen/feed/12145", az_dps_metro: "https://www.broadcastify.com/listen/feed/20741", phoenix_fire: "https://www.broadcastify.com/listen/feed/14875", east_valley_fire: "https://www.broadcastify.com/listen/feed/43570", note: "Scottsdale, Mesa and Tempe police are encrypted; nothing to hear." },
  tools: { cloudflare: "https://dash.cloudflare.com/", stripe: "https://dashboard.stripe.com/", zoho: "https://payments.zoho.com/", gmail: "https://mail.google.com/", calendar: "https://calendar.google.com/", gsc: "https://search.google.com/search-console", flutterflow: "https://app.flutterflow.io/", resend: "https://resend.com/emails" },
};

const BRAIN_SYSTEM = `You are JARVIS, the personal operations assistant for Jesse Clark, who runs five businesses:
Atavia Weddings and Elizabeth Scott Weddings (wedding films), Lazo (wedding planner app + vendor directory), Roven HR (hiring platform), LeaseReputation (apartment reviews).
Persona: calm, dry, precise, British; a trusted chief of staff. "Sir" sparingly.
Your replies are spoken aloud through text-to-speech: plain prose, no markdown, no lists, no headers, no URLs read aloud. Two to four sentences unless he asks for detail. Lead with the answer. Round numbers sensibly.
Everything you need is in the LIVE CONTEXT; answer from it directly and do not invent figures. If something isn't there, say so.
Flights: use track_flight for any question about where a flight is (convert "American 2612" to "AA 2612"), and flights_overhead for "what's flying over me". Say where it is flying from and to (route.from / route.to cities) when known. Report altitude in feet, speed in mph (knots x 1.15) and roughly where it is relative to cities; if not found yet, say you've started tracking it and it will appear on the World globe within a minute if it's airborne.
Actions: open_link opens pages; append_note for the notes board; remember/forget for durable facts about Jesse, his clients or preferences (use remember whenever he says "remember", "note that", "from now on"); draft_reply writes an email reply (shown with an Open-in-Gmail button, nothing is sent); request_action for anything that changes business data (approve a Roven job or employer, approve or reject a Lazo vendor claim, add a booking note, mark a Lazo inquiry responded) AND for email: email_reply (params.account, params.threadId, params.body: the full reply text you wrote, signed appropriately for that business), email_archive, email_read, email_send (params.account, params.to, params.subject, params.body). When he asks you to reply to an email, write the reply yourself in his voice (warm, brief, professional) and submit it as email_reply; he confirms before anything is sent. request_action only queues it for his confirmation; say it is ready for his confirmation. Never claim an action is done until RECENT ACTIONS shows it done. Use the ids shown in brackets in the context.`;

const BRAIN_TOOLS = [
  { name: "track_flight", description: "Live position of a flight by flight number or callsign (e.g. 'AA 2612', 'SWA653', 'N123AB'). Returns altitude (ft), ground speed (kt), heading and coordinates. Also shows it on the World globe.", input_schema: { type: "object", properties: { flight: { type: "string" } }, required: ["flight"], additionalProperties: false }, strict: true },
  { name: "flights_overhead", description: "Aircraft currently within N nautical miles of Jesse's home location (default 25).", input_schema: { type: "object", properties: { nm: { type: "number" } }, required: ["nm"], additionalProperties: false }, strict: true },
  { name: "open_link", description: "Open a URL in a new tab on Jesse's screen.", input_schema: { type: "object", properties: { url: { type: "string" }, label: { type: "string" } }, required: ["url", "label"], additionalProperties: false }, strict: true },
  { name: "append_note", description: "Add a line to the notes board.", input_schema: { type: "object", properties: { text: { type: "string" } }, required: ["text"], additionalProperties: false }, strict: true },
  { name: "remember", description: "Store a durable fact or preference in JARVIS's memory.", input_schema: { type: "object", properties: { text: { type: "string" } }, required: ["text"], additionalProperties: false }, strict: true },
  { name: "forget", description: "Delete a memory by its id (shown in MEMORY as [id]).", input_schema: { type: "object", properties: { id: { type: "string" } }, required: ["id"], additionalProperties: false }, strict: true },
  { name: "draft_reply", description: "Draft an email reply. Shown to Jesse with an Open in Gmail button; nothing is sent automatically.", input_schema: { type: "object", properties: { to: { type: "string" }, subject: { type: "string" }, body: { type: "string" }, business: { type: "string", enum: ["atavia", "es", "lazo", "roven", "lr", "brisk"] } }, required: ["to", "subject", "body", "business"], additionalProperties: false }, strict: true },
  { name: "request_action", description: "Queue a business-data change for Jesse's confirmation. kinds: roven_approve_job (params.jobId), roven_reject_job (params.jobId), roven_approve_employer (params.employerId), lazo_claim (params.claimId, params.decision 'approved'|'rejected'), booking_note (params.business 'atavia'|'es', params.bookingId, params.note), lazo_inquiry_responded (params.inquiryId), email_reply (params.account, params.threadId, params.body), email_archive (params.account, params.threadId), email_read (params.account, params.threadId), email_send (params.account, params.to, params.subject, params.body).", input_schema: { type: "object", properties: { kind: { type: "string", enum: ["roven_approve_job", "roven_reject_job", "roven_approve_employer", "lazo_claim", "booking_note", "lazo_inquiry_responded", "email_reply", "email_archive", "email_read", "email_send"] }, params: { type: "object", properties: { jobId: { type: "string" }, employerId: { type: "string" }, claimId: { type: "string" }, decision: { type: "string" }, business: { type: "string" }, bookingId: { type: "string" }, note: { type: "string" }, inquiryId: { type: "string" }, account: { type: "string" }, threadId: { type: "string" }, body: { type: "string" }, to: { type: "string" }, subject: { type: "string" } } }, summary: { type: "string", description: "One line Jesse will confirm, e.g. 'Approve Roven job Senior RN at Mercy'" } }, required: ["kind", "params", "summary"], additionalProperties: false } },
];

async function runTool(name, input, env, actions) {
  switch (name) {
    case "track_flight": { const r = await trackFlight(env, input.flight); r.route = await flightRoute(env, r.callsign); actions.push({ type: "world", flight: r.callsign }); return JSON.stringify(r).slice(0, 3000); }
    case "flights_overhead": { const place = await kv.get(env, "place"); const ac = await flightsNear(env, +(place?.lat || 33.15), +(place?.lon || -96.82), input.nm || 25); actions.push({ type: "world" }); return JSON.stringify({ near: place?.name, count: ac.length, aircraft: ac.slice(0, 25) }); }
    case "open_link": actions.push({ type: "open", url: input.url, label: input.label }); return "Opened " + input.label + ".";
    case "append_note": { const cur = (await kv.get(env, "notes")) || ""; const next = (cur ? cur.replace(/\s+$/, "") + "\n" : "") + "- " + input.text; await kv.put(env, "notes", next); actions.push({ type: "notes", value: next }); return "Added."; }
    case "remember": { const mem = (await kv.get(env, "memory")) || []; const m = { id: uid(), text: input.text, at: new Date().toISOString() }; mem.unshift(m); await kv.put(env, "memory", mem.slice(0, 200)); actions.push({ type: "memory", value: mem }); return "Remembered [" + m.id + "]."; }
    case "forget": { const mem = ((await kv.get(env, "memory")) || []).filter((m) => m.id !== input.id); await kv.put(env, "memory", mem); actions.push({ type: "memory", value: mem }); return "Forgotten."; }
    case "draft_reply": { actions.push({ type: "draft", ...input }); return "Draft shown to Jesse with an Open in Gmail button."; }
    case "request_action": { const KINDS = ["roven_approve_job", "roven_reject_job", "roven_approve_employer", "lazo_claim", "booking_note", "lazo_inquiry_responded", "email_reply", "email_archive", "email_read", "email_send"]; if (!KINDS.includes(input.kind) || typeof input.params !== "object" || !input.summary) return "Invalid action: kind must be one of " + KINDS.join(", ") + " with params and summary.";
      const item = { id: uid(), kind: input.kind, params: input.params, summary: input.summary, status: "awaiting confirmation", at: new Date().toISOString() }; actions.push({ type: "confirm", item }); return "Queued for confirmation: " + input.summary; }
    default: return "Unknown tool";
  }
}

/* ---------------- streaming chat ---------------- */
async function chat(request, env, ctx) {
  const { messages: history = [], text, model: modelPick, noTools } = await request.json();
  const { readable, writable } = new TransformStream();
  const writer = writable.getWriter(); const enc = new TextEncoder();
  const send = (ev, data) => writer.write(enc.encode(`event: ${ev}\ndata: ${JSON.stringify(data)}\n\n`)).catch(() => {});
  const run = async () => {
    try {
      if (!env.ANTHROPIC_API_KEY) { await send("delta", { text: "My reasoning core isn't connected. Set the Anthropic key on the worker." }); await send("done", { reply: "", messages: history, actions: [] }); return; }
      const client = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY });
      const T0 = Date.now(); const timing = {};
      const context = await buildContext(env, request); timing.context = Date.now() - T0;
      const messages = [...history.slice(-12), { role: "user", content: text }];
      const actions = []; let reply = "";
      for (let i = 0; i < 4; i++) {
        const stream = client.beta.messages.stream({
          model: (modelPick || env.CHAT_MODEL) === "sonnet" ? "claude-sonnet-5-5" : MODEL, ...((modelPick || env.CHAT_MODEL) === "sonnet" ? { thinking: { type: "between_tools" } } : {}),
          max_tokens: 4000, betas: ["server-side-fallback-2026-07-01"], fallbacks: "default", output_config: { effort: "low" },
          system: [{ type: "text", text: BRAIN_SYSTEM + "\nKnown links: " + JSON.stringify(LINKS), cache_control: { type: "ephemeral" } }, { type: "text", text: "LIVE CONTEXT:\n" + context }],
          ...(noTools ? {} : { tools: BRAIN_TOOLS }), messages,
        });
        let turnText = "";
        stream.on("text", (d) => { if (timing.firstText == null) timing.firstText = Date.now() - T0; turnText += d; send("delta", { text: d }); });
        const msg = await stream.finalMessage();
        if (turnText.trim()) reply = (reply ? reply + " " : "") + turnText.trim();
        messages.push({ role: "assistant", content: msg.content });
        if (msg.stop_reason === "refusal") { if (!reply) { reply = "I'd rather not answer that one."; await send("delta", { text: reply }); } break; }
        if (msg.stop_reason !== "tool_use") break;
        const results = [];
        for (const b of msg.content.filter((b) => b.type === "tool_use")) {
          let out; try { out = await runTool(b.name, b.input, env, actions); } catch (e) { out = "Tool failed: " + e.message; }
          results.push({ type: "tool_result", tool_use_id: b.id, content: String(out) });
        }
        messages.push({ role: "user", content: results });
        if (i < 3) await send("delta", { text: " " });
      }
      const compact = messages.map((m) => ({ role: m.role, content: typeof m.content === "string" ? m.content : m.content.filter((b) => b.type === "text").map((b) => b.text).join(" ") })).filter((m) => m.content.trim());
      timing.total = Date.now() - T0; timing.ctxChars = context.length;
      await send("done", { reply, actions, messages: compact.slice(-12), timing });
    } catch (e) { await send("error", { message: String(e.message || e) }); }
    finally { try { await writer.close(); } catch {} }
  };
  ctx.waitUntil(run());
  return new Response(readable, { headers: { "content-type": "text/event-stream", "cache-control": "no-store", "x-accel-buffering": "no" } });
}

/* ---------------- briefs: morning / afternoon / evening ---------------- */
const SLOT_PROMPTS = {
  morning: "This is the MORNING brief. About 220 to 300 words, two minutes read aloud. Greeting with the date and today's weather in one breath; what needs his attention today (unanswered leads, alerts, anything slow or down, anything JARVIS noticed); each business in a sentence or two with the numbers that matter and the week-over-week direction; today's and this week's weddings with their venue weather; his teams' games today and last night's results; one line on the markets and the top local headline if it matters; finish with one dry, encouraging line.",
  afternoon: "This is the AFTERNOON brief. About 150 to 220 words. Only what is NEW since the morning brief: fresh leads or bookings, web traffic so far today for Atavia and Elizabeth Scott, actions completed, alerts, any site that got slow, scores of games in progress or finished today, markets at midday, and anything that changed in the forecast for tonight or this week's weddings. Do not repeat the morning numbers or re-describe the day's weather unless it changed. If genuinely nothing changed, say so in two sentences.",
  evening: "This is the EVENING brief. About 180 to 250 words. Wrap the day: what came in today across the businesses (leads, bookings, sign-ups, revenue if any), today's final web traffic, final scores and tomorrow's games, how the markets closed; then look ahead: tomorrow's weather, tomorrow's and the weekend's weddings with venue weather, balances due, anything still unresolved that he should sleep on or handle first thing. Do not repeat what the morning or afternoon brief already said unless it resolved.",
};
const SLOT_HOURS = (env) => Object.fromEntries((env.BRIEF_HOURS || "5:morning,12:afternoon,18:evening").split(",").map((x) => { const [h, slot] = x.split(":"); return [+h, slot || "morning"]; }));
const slotNow = (env) => { const h = localHour(env); return h < 11 ? "morning" : h < 17 ? "afternoon" : "evening"; };

async function makeMorning(env, request, slot) {
  if (!env.ANTHROPIC_API_KEY) return { error: "no brain" };
  slot = slot || slotNow(env);
  const client = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY });
  const context = await buildContext(env, request);
  const history = (await kv.get(env, "briefs")) || [];
  const prevToday = history.filter((b) => b.at.slice(0, 10) === new Date().toISOString().slice(0, 10) && b.slot !== slot).map((b) => `${b.slot.toUpperCase()} (${b.at}): ${b.text}`).join("\n\n");
  const params = {
    model: MODEL, max_tokens: 6000, betas: ["server-side-fallback-2026-07-01"], fallbacks: "default", output_config: { effort: "medium" },
    system: BRAIN_SYSTEM + "\nYou are composing one of Jesse's three daily spoken briefs. " + SLOT_PROMPTS[slot] + " Flowing prose, no lists, no headers. For Lazo, report ONLY sign-ups (new couples, new vendor claims); never mention unanswered vendor inquiries in a brief.",
    messages: [{ role: "user", content: `Compose the ${slot} brief.\n\n${prevToday ? "EARLIER BRIEFS TODAY (do not repeat their content):\n" + prevToday + "\n\n" : ""}LIVE CONTEXT:\n${context}` }],
  };
  let text = "", r;
  for (let i = 0; i < 3; i++) {
    r = await client.beta.messages.create(params);
    text = (text + " " + r.content.filter((b) => b.type === "text").map((b) => b.text).join(" ").trim()).trim();
    if (r.stop_reason !== "max_tokens") break;
    params.messages = [...params.messages, { role: "assistant", content: r.content }, { role: "user", content: "You were cut off. Continue exactly where you stopped and finish the brief; do not restart or repeat anything." }];
  }
  const brief = { id: uid(), slot, at: new Date().toISOString(), text, audio: false, debug: { stop: r?.stop_reason, details: r?.stop_details || null, out: r?.usage?.output_tokens, blocks: (r?.content || []).map((b) => b.type + (b.type === "text" ? ":" + b.text.length : "")), model: r?.model } };
  if (env.ELEVENLABS_API_KEY && text) {
    try { const a = await elevenlabs(env, text); if (a.ok) { await env.HUB.put("brief_audio_" + brief.id, await a.arrayBuffer(), { expirationTtl: 8 * 86400 }); brief.audio = true; } } catch {}
  }
  const list = [brief, ...history].slice(0, 7);
  await kv.put(env, "briefs", list); await kv.put(env, "morning", brief);
  const headline = text.split(/(?<=[.!?])\s/).slice(0, 2).join(" ");
  await notify(env, `${slot[0].toUpperCase() + slot.slice(1)} brief`, headline, { tags: slot === "morning" ? "sunrise" : slot === "evening" ? "city_sunset" : "sun", url: new URL(request.url).origin + "/#morning" });
  return brief;
}

/* ---------------- staleness: PC-fed feeds that stopped arriving ---------------- */
async function checkStale(env) {
  const feeds = [["metrics", "metrics", 2 * 3600e3, (m) => m?.collectedAt], ["traffic", "traffic", 25 * 60e3, (t) => t?.at], ["sports", "scores", 25 * 60e3, (s) => s?.at], ["flights", "flights", 10 * 60e3, (f) => f?.at], ["brief", "inbox brief", 3 * 3600e3, (b) => b?.at]];
  const flags = (await kv.get(env, "stale")) || {}; const h = localHour(env); let changed = false;
  for (const [key, label, maxAge, getAt] of feeds) {
    const at = getAt(await kv.get(env, key)); if (!at) continue;
    if (key === "brief" && (h < 8 || h > 21)) continue; // the inbox routine only runs 7am-9pm while the Claude app is open
    const age = Date.now() - new Date(at); const stale = age > maxAge;
    if (stale && !flags[key]) { flags[key] = Date.now(); changed = true; await pushAlert(env, { kind: "watch", text: `${label} feed is ${Math.round(age / 60000)} min old: is the PC awake and signed in?` }); await notify(env, "Feed stopped", `${label} last arrived ${Math.round(age / 60000)} min ago. Check the PC (collectors / Claude app).`, { priority: "high", tags: "warning" }); }
    if (!stale && flags[key]) { delete flags[key]; changed = true; await pushAlert(env, { kind: "up", text: `${label} feed is back` }); }
  }
  if (changed) await kv.put(env, "stale", flags);
  return flags;
}
/* ---------------- ElevenLabs ---------------- */
function elevenlabs(env, text, format = "mp3_44100_128", model = "eleven_turbo_v2_5") {
  const voice = env.ELEVENLABS_VOICE_ID || "JBFqnCBsd6RMkjVDRZzb";
  return fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voice}/stream?output_format=${format}`, {
    method: "POST", headers: { "xi-api-key": env.ELEVENLABS_API_KEY, "content-type": "application/json" },
    body: JSON.stringify({ text: String(text).slice(0, 4800), model_id: model, voice_settings: { stability: 0.6, similarity_boost: 0.8, style: 0.15, use_speaker_boost: true } }),
  });
}
async function tts(request, env) {
  if (!env.ELEVENLABS_API_KEY) return json({ error: "tts not configured" }, 501);
  const text = request.method === "GET" ? new URL(request.url).searchParams.get("t") || "" : (await request.json()).text;
  const r = await elevenlabs(env, text, "mp3_44100_128", "eleven_flash_v2_5");
  if (!r.ok) return json({ error: "tts failed", status: r.status }, 502);
  return new Response(r.body, { headers: { "content-type": "audio/mpeg", "cache-control": "no-store" } });
}

/* ---------------- Google sign-in ---------------- */
async function googleLogin(request, env) {
  const { credential } = await request.json();
  if (!env.GOOGLE_CLIENT_ID) return json({ error: "Google sign-in isn't configured" }, 501);
  const r = await fetch("https://oauth2.googleapis.com/tokeninfo?id_token=" + encodeURIComponent(credential));
  if (!r.ok) return json({ error: "Invalid token" }, 401);
  const info = await r.json();
  const allowed = (env.ALLOWED_EMAILS || "jesse@briskhealth.com").toLowerCase().split(/[,\s]+/).filter(Boolean);
  if (info.aud !== env.GOOGLE_CLIENT_ID || info.email_verified !== "true" || !allowed.includes(String(info.email).toLowerCase())) return json({ error: "That Google account isn't on the list." }, 403);
  return json({ ok: true, email: info.email }, 200, { "set-cookie": setCookie("sess", await makeSession(env, info.email), 30 * 86400) });
}

/* ---------------- home location: Texas or Arizona ---------------- */
const HOMES = {
  tx: { tz: "America/Chicago", place: { name: "Frisco, Texas", lat: 33.1507, lon: -96.8236 }, label: "Texas" },
  az: { tz: "America/Phoenix", place: { name: "Phoenix, Arizona", lat: 33.4484, lon: -112.074 }, label: "Arizona" },
};
async function applyHome(env) { try { const h = await kv.get(env, "home"); if (h?.tz) env.TZ = h.tz; } catch {} }
async function setHome(env, body) {
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

/* ---------------- worker ---------------- */
export default {
  async scheduled(event, env, ctx) {
    await applyHome(env);
    const cron = event.cron || "";
    if (cron.startsWith("*/5")) ctx.waitUntil(runChecks(env).then(() => checkStale(env)));
    else ctx.waitUntil((async () => {
      await loadCalendar(env, true).catch(() => null);
      await weddingWeather(env).catch(() => null);
      const slot = SLOT_HOURS(env)[localHour(env)];
      if (slot) {
        const fake = new Request("https://jarvis-hub.floral-credit-e4f0.workers.dev/", { cf: {} });
        await makeMorning(env, fake, slot).catch((e) => pushAlert(env, { kind: "watch", text: slot + " brief failed: " + e.message }));
      }
    })());
  },

  async fetch(request, env, ctx) {
    await applyHome(env);
    const url = new URL(request.url); const p = url.pathname;
    if (p === "/auth" && request.method === "POST") {
      const form = await request.formData(); const key = String(form.get("key") || "");
      if (env.HUB_KEY && key !== env.HUB_KEY) return new Response(lockPage(env, "Wrong key."), { status: 403, headers: { "content-type": "text/html; charset=utf-8" } });
      return new Response(null, { status: 303, headers: { location: "/", "set-cookie": setCookie("hub", key) } });
    }
    if (p === "/auth/google" && request.method === "POST") return googleLogin(request, env);
    if (p === "/logout") return new Response(null, { status: 303, headers: [["location", "/"], ["set-cookie", setCookie("hub", "", 0)], ["set-cookie", setCookie("sess", "", 0)]] });
    if (p === "/manifest.webmanifest") return new Response(manifest, { headers: { "content-type": "application/manifest+json" } });
    if (p === "/icon.svg") return new Response(ICON, { headers: { "content-type": "image/svg+xml", "cache-control": "public, max-age=86400" } });

    const who = await authed(request, env);
    if (!who) {
      if (p.startsWith("/api/")) return json({ error: "unauthorized" }, 401);
      return new Response(lockPage(env), { status: 401, headers: { "content-type": "text/html; charset=utf-8" } });
    }
    if (p === "/" || p === "/index.html" || p === "/wall") return new Response(html, { headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" } });

    if (p === "/api/config") return json({ user: who, google: !!env.GOOGLE_CLIENT_ID, brain: !!env.ANTHROPIC_API_KEY, tts: !!env.ELEVENLABS_API_KEY, windy: !!env.WINDY_KEY, pushover: !!(env.PUSHOVER_TOKEN && env.PUSHOVER_USER), ntfy: env.NTFY_TOPIC || null, email: !!(env.RESEND_API_KEY && env.ALERT_EMAIL), calendar: !!env.CAL_ICS_URL, home: (await kv.get(env, "home")) || { mode: "auto", key: "tx", tz: env.TZ || "America/Chicago", label: "Texas" }, teams: env.TEAMS || "DAL,NE,TEX,COL,BOS,ARI", tz: env.TZ || "America/Chicago" });
    if (p === "/api/status") {
      const cached = url.searchParams.get("fresh") ? null : await kv.get(env, "status");
      if (cached && Date.now() - new Date(cached.checkedAt) < 6 * 60000) return json({ ...cached, uptime: await kv.get(env, "uptime"), history: await kv.get(env, "rt_history") });
      const sites = await runChecks(env);
      return json({ checkedAt: new Date().toISOString(), sites, uptime: await kv.get(env, "uptime"), history: await kv.get(env, "rt_history") });
    }
    if (p === "/api/weather") { const place = url.searchParams.get("lat") ? { lat: url.searchParams.get("lat"), lon: url.searchParams.get("lon"), name: url.searchParams.get("place") } : await kv.get(env, "place"); const w = await weatherData(request, env, place); return json(w, w.error ? 400 : 200, { "cache-control": "public, max-age=300" }); }
    if (p === "/api/sports") return json(await sports(env));
    if (p === "/api/markets") return json(await markets(env));
    if (p === "/api/news") return json(await news(env));
    if (p === "/api/wxdays") return json(url.searchParams.get("fresh") ? { days: await weddingWeather(env) } : ((await kv.get(env, "wxdays")) || { days: {} }));
    if (p === "/api/calendar") return json((await loadCalendar(env, !!url.searchParams.get("fresh"))) || { events: [], off: true });
    if (p === "/api/chat" && request.method === "POST") return chat(request, env, ctx);
    if (p === "/api/tts" && (request.method === "POST" || request.method === "GET")) return tts(request, env);
    if (p === "/api/morning") return json({ latest: (await kv.get(env, "morning")) || null, history: (await kv.get(env, "briefs")) || [], stale: (await kv.get(env, "stale")) || {} });
    if (p === "/api/morning/audio") { const id = url.searchParams.get("id"); const a = await env.HUB.get(id ? "brief_audio_" + id : "brief_audio_" + ((await kv.get(env, "morning"))?.id || ""), "arrayBuffer"); return a ? new Response(a, { headers: { "content-type": "audio/mpeg", "cache-control": "no-store" } }) : new Response("no audio", { status: 404 }); }
    if (p === "/api/morning/run" && request.method === "POST") return json(await makeMorning(env, request, url.searchParams.get("slot") || undefined));
    if (p === "/api/test-alert" && request.method === "POST") return json({ ok: true, results: await notify(env, "JARVIS test", "Push notifications are wired up.", { tags: "robot" }) });

    if (p === "/api/world/flights") { const f = (await kv.get(env, "flights")) || {}; return json({ at: f.at || null, center: f.center || null, ac: f.ac || [], tracks: f.tracks || {} }); }
    if (p === "/api/world/track") return json(await trackFlight(env, url.searchParams.get("q") || ""));
    if (p === "/api/world/want") { const place = await kv.get(env, "place"); const want = (await kv.get(env, "track_req")) || {}; const live = Object.fromEntries(Object.entries(want).filter(([, t]) => Date.now() - t < 6 * 3600e3)); if (Object.keys(live).length !== Object.keys(want).length) await kv.put(env, "track_req", live); return json({ lat: +(place?.lat || 33.15), lon: +(place?.lon || -96.82), nm: 80, track: Object.keys(live) }); }
    if (p === "/api/world/feed" && request.method === "POST") { const body = await request.json(); await kv.put(env, "flights", body); return json({ ok: true, ac: (body.ac || []).length }); }
    if (p === "/api/world/untrack" && request.method === "POST") { const { q } = await request.json(); const want = (await kv.get(env, "track_req")) || {}; delete want[toCallsign(q)]; await kv.put(env, "track_req", want); return json({ ok: true }); }
    if (p === "/api/world/events") return json((await worldEvents(env)) || { quakes: [], fires: [], iss: null });
    if (p === "/api/world/camsfeed" && request.method === "POST") { const { cams } = await request.json(); await env.HUB.put("cams", JSON.stringify(cams || [])); camMem = null; return json({ ok: true, cams: (cams || []).length }); }
    if (p === "/api/world/cams") {
      const all = await camsAll(env); const lat = +url.searchParams.get("lat"), lon = +url.searchParams.get("lon"), r = Math.min(30, +url.searchParams.get("r") || 2);
      if (!url.searchParams.get("lat")) return json({ total: all.length, cams: [] });
      const kx = Math.max(0.2, Math.cos(lat * Math.PI / 180));
      const near = all.filter((c) => Math.abs(c[0] - lat) < r && Math.abs(c[1] - lon) * kx < r * 1.6);
      // nearest to the view centre first, so zooming into a city shows that city's cameras
      near.sort((a, b) => ((a[0] - lat) ** 2 + ((a[1] - lon) * kx) ** 2) - ((b[0] - lat) ** 2 + ((b[1] - lon) * kx) ** 2));
      return json({ total: all.length, inView: near.length, cams: near.slice(0, 500) }, 200, { "cache-control": "public, max-age=300" });
    }
    if (p === "/api/world/placesfeed" && request.method === "POST") { const { places } = await request.json(); await env.HUB.put("places", JSON.stringify(places || [])); placeMem = null; return json({ ok: true, places: (places || []).length }); }
    if (p === "/api/world/places") {
      const all = await placesAll(env); const lat = +url.searchParams.get("lat"), lon = +url.searchParams.get("lon"), r = +url.searchParams.get("r") || 5, n = Math.min(120, +url.searchParams.get("n") || 50);
      const kx = Math.max(0.2, Math.cos(lat * Math.PI / 180)); const out = [];
      for (const pl of all) { if (Math.abs(pl[1] - lat) < r && Math.abs(pl[2] - lon) * kx < r * 1.6) { out.push(pl); if (out.length >= n) break; } } // list is sorted by rank, so the first hits are the most important
      return json(out, 200, { "cache-control": "public, max-age=600" });
    }
    if (p === "/api/world/windy") { const v = await windyNear(env, +url.searchParams.get("lat"), +url.searchParams.get("lon"), +url.searchParams.get("km") || 50); return json(v, v.error ? 502 : 200); }
    if (p === "/api/world/cam") { try { const r = await txSnapshot(url.searchParams.get("d"), url.searchParams.get("id")); return r || new Response("no image", { status: 404 }); } catch (e) { return new Response("camera error: " + e.message, { status: 502 }); } }
    if (p === "/api/world/globalfeed" && request.method === "POST") { const body = await request.json(); await env.HUB.put("flights_global", JSON.stringify(body)); return json({ ok: true, ac: (body.ac || []).length }); }
    if (p === "/api/world/global") { const g = await env.HUB.get("flights_global"); return new Response(g || '{"ac":[]}', { headers: { "content-type": "application/json", "cache-control": "public, max-age=60" } }); }
    if (p === "/api/world/route") return json((await flightRoute(env, url.searchParams.get("cs"))) || { none: true });
    if (p === "/api/world/sats") return json(await satTles(env), 200, { "cache-control": "public, max-age=3600" });
    if (p === "/api/home" && request.method === "POST") return json(await setHome(env, await request.json()));
    if (p === "/api/inbox" && request.method === "POST") return ingestInbox(env, await request.json(), ctx);
    if (p === "/api/inbox/thread") { const r = await bridgeCall(env, url.searchParams.get("account"), { action: "get", threadId: url.searchParams.get("t") }); if (r.error === "unknown action") r.error = "This inbox's bridge script is the older version. Paste the updated script and deploy a new version to read full emails."; return json(r, r.error ? 502 : 200); }
    if (p === "/api/inbox/bridges") { const hooks = (await kv.get(env, "inbox_hooks")) || {}; const inbox = (await kv.get(env, "inbox")) || { accounts: {} }; return json(Object.entries(inbox.accounts).map(([a, v]) => ({ account: a, business: v.business, at: v.at, items: v.items.length, actions: !!hooks[a]?.url }))); }
    // action queue: confirmed by Jesse on the page. Email kinds run right now through the Gmail bridge; the rest wait for the hands script on his PC
    if (p === "/api/act" && request.method === "POST") {
      const item = await request.json(); const q = (await kv.get(env, "queue")) || [];
      if (String(item.kind || "").startsWith("email_")) {
        const res = await emailAction(env, item);
        q.unshift({ ...item, status: res.ok ? "done" : "failed", result: res.message, confirmedAt: new Date().toISOString(), doneAt: new Date().toISOString() });
        await kv.put(env, "queue", q.slice(0, 50)); await pushAlert(env, { kind: res.ok ? "done" : "failed", text: (res.ok ? "Done: " : "Failed: ") + item.summary + (res.message ? " — " + res.message : "") });
        return json({ ok: res.ok, id: item.id, executed: true, result: res.message });
      }
      q.unshift({ ...item, status: "pending", confirmedAt: new Date().toISOString() });
      await kv.put(env, "queue", q.slice(0, 50)); return json({ ok: true, id: item.id });
    }
    if (p === "/api/queue" && request.method === "GET") return json(((await kv.get(env, "queue")) || []).filter((q) => q.status === "pending"));
    if (p === "/api/queue/result" && request.method === "POST") {
      const { id, ok, message } = await request.json(); const q = (await kv.get(env, "queue")) || [];
      const it = q.find((x) => x.id === id); if (it) { it.status = ok ? "done" : "failed"; it.result = message; it.doneAt = new Date().toISOString(); }
      await kv.put(env, "queue", q); if (it) await pushAlert(env, { kind: ok ? "done" : "failed", text: (ok ? "Done: " : "Failed: ") + it.summary + (message ? " — " + message : "") });
      return json({ ok: true });
    }
    if (p === "/api/queue/cancel" && request.method === "POST") { const { id } = await request.json(); const q = ((await kv.get(env, "queue")) || []).map((x) => x.id === id && x.status === "pending" ? { ...x, status: "cancelled" } : x); await kv.put(env, "queue", q); return json({ ok: true }); }

    if (p === "/api/state") {
      if (request.method === "GET") { const out = {}; await Promise.all(STATE_KEYS.map(async (k) => { const v = await kv.get(env, k); if (v != null) out[k] = v; })); return json(out); }
      if (request.method === "POST" || request.method === "PUT") {
        const body = await request.json(); const saved = [];
        for (const k of STATE_KEYS) if (k in body) {
          if (k === "brief" && body.brief?.source !== "bridge" && !body.brief?.force) { const cur = await kv.get(env, "brief"); if (cur?.source === "bridge") continue; } // live bridges outrank the hourly snapshot
          await kv.put(env, k, body[k]); saved.push(k);
        }
        if (body.metrics) ctx.waitUntil(Promise.all([watchMetrics(env, body.metrics), weddingWeather(env)]));
        if (body.decisions) ctx.waitUntil(watchDecisions(env, body.decisions));
        return json({ saved, at: new Date().toISOString() });
      }
    }
    return new Response("Not found", { status: 404 });
  },
};

const ICON = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" rx="20" fill="#04070d"/><circle cx="50" cy="50" r="40" fill="none" stroke="#19d3ff" stroke-width="3" stroke-dasharray="40 30 10 60"/><circle cx="50" cy="50" r="27" fill="none" stroke="#7be8ff" stroke-width="2" stroke-dasharray="20 15 5 40"/><circle cx="50" cy="50" r="15" fill="#19d3ff" opacity=".8"/><circle cx="50" cy="50" r="6" fill="#fff"/></svg>`;

function lockPage(env, msg = "") {
  const g = env.GOOGLE_CLIENT_ID ? `<script src="https://accounts.google.com/gsi/client" async defer></script>
<div id="g_id_onload" data-client_id="${env.GOOGLE_CLIENT_ID}" data-callback="onGoogle" data-auto_prompt="false"></div>
<div class="g_id_signin" data-type="standard" data-theme="filled_black" data-size="large" data-text="signin_with" data-shape="rectangular"></div><p class="or">or</p>
<script>async function onGoogle(r){const x=await fetch("/auth/google",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({credential:r.credential})});if(x.ok)location.href="/";else{const d=await x.json().catch(()=>({}));document.getElementById("msg").textContent=d.error||"Sign-in failed.";}}</script>` : "";
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>JARVIS</title><link rel="icon" href="/icon.svg"><link rel="manifest" href="/manifest.webmanifest">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600&family=Share+Tech+Mono&display=swap">
<style>html,body{height:100%;margin:0;background:#04070d;color:#9fd8ff;font:15px/1.5 Rajdhani,"Segoe UI",system-ui,sans-serif;display:grid;place-items:center}body{background:radial-gradient(800px 500px at 50% 30%,rgba(25,211,255,.12),transparent 60%),#04070d}
.box{display:grid;gap:14px;width:min(340px,90vw);text-align:center;justify-items:center}h1{font-weight:600;letter-spacing:.5em;margin:0;color:#fff;font-size:28px;text-shadow:0 0 18px rgba(25,211,255,.55)}form{display:grid;gap:10px;width:100%}
input{background:#070d18;border:1px solid #1e4a6a;color:#e6f6ff;padding:12px 14px;border-radius:2px;font:14px "Share Tech Mono",monospace;text-align:center;letter-spacing:.2em}button{background:#19d3ff;color:#04070d;border:0;padding:12px;border-radius:2px;font:600 14px Rajdhani,sans-serif;letter-spacing:.25em;cursor:pointer}
p{margin:0;opacity:.6;font-size:13px;font-family:"Share Tech Mono",monospace;letter-spacing:.1em}.or{opacity:.4}#msg{color:#ff4d5e;opacity:1;min-height:1em}</style></head>
<body><div class="box"><h1>JARVIS</h1><p>RESTRICTED ACCESS</p>${g}<form method="post" action="/auth"><input name="key" type="password" autocomplete="current-password" placeholder="access key"><button>UNLOCK</button></form><p id="msg">${msg}</p></div></body></html>`;
}
