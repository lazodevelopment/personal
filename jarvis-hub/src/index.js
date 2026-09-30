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
const STATE_KEYS = ["brief", "webcams", "notes", "place", "metrics", "alerts", "memory", "queue", "calendar", "morning", "traffic"];
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

/* ---------------- context for the brain ---------------- */
async function buildContext(env, request) {
  const [status, metrics, brief, notes, memory, alerts, place, cal, morning, queue, traffic] = await Promise.all(["status", "metrics", "brief", "notes", "memory", "alerts", "place", "calendar", "morning", "queue", "traffic"].map((k) => kv.get(env, k)));
  const wx = await weatherData(request, env, place).catch(() => null);
  const lines = [];
  lines.push(`TIME: ${localTime(env)} (${env.TZ || "America/Chicago"})`);
  lines.push(`SITES: ` + (status?.sites || []).map((s) => `${s.name} ${s.ok ? "up" : "DOWN"} ${s.ms}ms`).join(", "));
  lines.push(`WEATHER: ${weatherSummary(wx)}`);
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
  lines.push(`INBOX BRIEF (${brief?.at || "none"}): ${brief?.note || ""} ` + (brief?.items || []).slice(0, 12).map((m) => `[${m.business || m.account || ""}] ${m.from}: ${m.subject}${m.needs_reply ? " (NEEDS REPLY)" : ""} — ${m.snippet || ""}`).join(" | "));
  lines.push(`ALERTS (latest): ` + (alerts || []).slice(0, 6).map((a) => `${a.at.slice(0, 16)} ${a.text}`).join(" | "));
  if (cal?.events?.length) lines.push(`CALENDAR (next 60d): ` + cal.events.slice(0, 20).map((e) => `${e.start.slice(0, 16)} ${e.title}${e.location ? " @ " + e.location : ""}`).join("; "));
  else lines.push("CALENDAR: not connected");
  lines.push(`NOTES:\n${notes || "(empty)"}`);
  lines.push(`MEMORY: ` + ((memory || []).map((m) => `[${m.id}] ${m.text}`).join(" | ") || "(nothing remembered yet)"));
  if (queue?.length) lines.push(`RECENT ACTIONS: ` + queue.slice(0, 5).map((q) => `${q.summary} → ${q.status}${q.result ? " (" + q.result + ")" : ""}`).join(" | "));
  if (morning?.at) lines.push(`MORNING BRIEF exists from ${morning.at}.`);
  return lines.join("\n");
}

const LINKS = {
  atavia: { site: "https://ataviaweddings.com", admin: "https://atavia-admin.pages.dev", firebase: "https://console.firebase.google.com/project/atavia-c29cd/overview" },
  es: { site: "https://elizabethscottweddings.com", admin: "https://admin.elizabethscottweddings.com", firebase: "https://console.firebase.google.com/project/elizabeth-scott-738e5/overview" },
  lazo: { site: "https://meetlazo.com", appstore: "https://apps.apple.com/us/app/lazo-wedding-planner/id6812863675", firebase: "https://console.firebase.google.com/project/lazo-513ec/overview", asc: "https://appstoreconnect.apple.com/apps" },
  roven: { site: "https://rovenhr.com", app: "https://app.rovenhr.com" },
  lr: { site: "https://leasereputation.com", app: "https://app.leasereputation.com", firebase: "https://console.firebase.google.com/project/lease-reputation/overview" },
  tools: { cloudflare: "https://dash.cloudflare.com/", stripe: "https://dashboard.stripe.com/", zoho: "https://payments.zoho.com/", gmail: "https://mail.google.com/", calendar: "https://calendar.google.com/", gsc: "https://search.google.com/search-console", flutterflow: "https://app.flutterflow.io/", resend: "https://resend.com/emails" },
};

const BRAIN_SYSTEM = `You are JARVIS, the personal operations assistant for Jesse Clark, who runs five businesses:
Atavia Weddings and Elizabeth Scott Weddings (wedding films), Lazo (wedding planner app + vendor directory), Roven HR (hiring platform), LeaseReputation (apartment reviews).
Persona: calm, dry, precise, British; a trusted chief of staff. "Sir" sparingly.
Your replies are spoken aloud through text-to-speech: plain prose, no markdown, no lists, no headers, no URLs read aloud. Two to four sentences unless he asks for detail. Lead with the answer. Round numbers sensibly.
Everything you need is in the LIVE CONTEXT; answer from it directly and do not invent figures. If something isn't there, say so.
Actions: open_link opens pages; append_note for the notes board; remember/forget for durable facts about Jesse, his clients or preferences (use remember whenever he says "remember", "note that", "from now on"); draft_reply writes an email reply (shown with an Open-in-Gmail button, nothing is sent); request_action for anything that changes business data (approve a Roven job or employer, approve or reject a Lazo vendor claim, add a booking note, mark a Lazo inquiry responded). request_action only queues it for his confirmation; say it is ready for his confirmation. Never claim an action is done until RECENT ACTIONS shows it done. Use the ids shown in brackets in the context.`;

const BRAIN_TOOLS = [
  { name: "open_link", description: "Open a URL in a new tab on Jesse's screen.", input_schema: { type: "object", properties: { url: { type: "string" }, label: { type: "string" } }, required: ["url", "label"], additionalProperties: false }, strict: true },
  { name: "append_note", description: "Add a line to the notes board.", input_schema: { type: "object", properties: { text: { type: "string" } }, required: ["text"], additionalProperties: false }, strict: true },
  { name: "remember", description: "Store a durable fact or preference in JARVIS's memory.", input_schema: { type: "object", properties: { text: { type: "string" } }, required: ["text"], additionalProperties: false }, strict: true },
  { name: "forget", description: "Delete a memory by its id (shown in MEMORY as [id]).", input_schema: { type: "object", properties: { id: { type: "string" } }, required: ["id"], additionalProperties: false }, strict: true },
  { name: "draft_reply", description: "Draft an email reply. Shown to Jesse with an Open in Gmail button; nothing is sent automatically.", input_schema: { type: "object", properties: { to: { type: "string" }, subject: { type: "string" }, body: { type: "string" }, business: { type: "string", enum: ["atavia", "es", "lazo", "roven", "lr", "brisk"] } }, required: ["to", "subject", "body", "business"], additionalProperties: false }, strict: true },
  { name: "request_action", description: "Queue a business-data change for Jesse's confirmation. kinds: roven_approve_job (params.jobId), roven_reject_job (params.jobId), roven_approve_employer (params.employerId), lazo_claim (params.claimId, params.decision 'approved'|'rejected'), booking_note (params.business 'atavia'|'es', params.bookingId, params.note), lazo_inquiry_responded (params.inquiryId).", input_schema: { type: "object", properties: { kind: { type: "string", enum: ["roven_approve_job", "roven_reject_job", "roven_approve_employer", "lazo_claim", "booking_note", "lazo_inquiry_responded"] }, params: { type: "object", properties: { jobId: { type: "string" }, employerId: { type: "string" }, claimId: { type: "string" }, decision: { type: "string" }, business: { type: "string" }, bookingId: { type: "string" }, note: { type: "string" }, inquiryId: { type: "string" } }, additionalProperties: false }, summary: { type: "string", description: "One line Jesse will confirm, e.g. 'Approve Roven job Senior RN at Mercy'" } }, required: ["kind", "params", "summary"], additionalProperties: false }, strict: true },
];

async function runTool(name, input, env, actions) {
  switch (name) {
    case "open_link": actions.push({ type: "open", url: input.url, label: input.label }); return "Opened " + input.label + ".";
    case "append_note": { const cur = (await kv.get(env, "notes")) || ""; const next = (cur ? cur.replace(/\s+$/, "") + "\n" : "") + "- " + input.text; await kv.put(env, "notes", next); actions.push({ type: "notes", value: next }); return "Added."; }
    case "remember": { const mem = (await kv.get(env, "memory")) || []; const m = { id: uid(), text: input.text, at: new Date().toISOString() }; mem.unshift(m); await kv.put(env, "memory", mem.slice(0, 200)); actions.push({ type: "memory", value: mem }); return "Remembered [" + m.id + "]."; }
    case "forget": { const mem = ((await kv.get(env, "memory")) || []).filter((m) => m.id !== input.id); await kv.put(env, "memory", mem); actions.push({ type: "memory", value: mem }); return "Forgotten."; }
    case "draft_reply": { actions.push({ type: "draft", ...input }); return "Draft shown to Jesse with an Open in Gmail button."; }
    case "request_action": { const item = { id: uid(), kind: input.kind, params: input.params, summary: input.summary, status: "awaiting confirmation", at: new Date().toISOString() }; actions.push({ type: "confirm", item }); return "Queued for confirmation: " + input.summary; }
    default: return "Unknown tool";
  }
}

/* ---------------- streaming chat ---------------- */
async function chat(request, env, ctx) {
  const { messages: history = [], text } = await request.json();
  const { readable, writable } = new TransformStream();
  const writer = writable.getWriter(); const enc = new TextEncoder();
  const send = (ev, data) => writer.write(enc.encode(`event: ${ev}\ndata: ${JSON.stringify(data)}\n\n`)).catch(() => {});
  const run = async () => {
    try {
      if (!env.ANTHROPIC_API_KEY) { await send("delta", { text: "My reasoning core isn't connected. Set the Anthropic key on the worker." }); await send("done", { reply: "", messages: history, actions: [] }); return; }
      const client = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY });
      const context = await buildContext(env, request);
      const messages = [...history.slice(-12), { role: "user", content: text }];
      const actions = []; let reply = "";
      for (let i = 0; i < 4; i++) {
        const stream = client.beta.messages.stream({
          model: MODEL, max_tokens: 800, betas: ["server-side-fallback-2026-07-01"], fallbacks: "default", output_config: { effort: "low" },
          system: [{ type: "text", text: BRAIN_SYSTEM + "\nKnown links: " + JSON.stringify(LINKS), cache_control: { type: "ephemeral" } }, { type: "text", text: "LIVE CONTEXT:\n" + context }],
          tools: BRAIN_TOOLS, messages,
        });
        let turnText = "";
        stream.on("text", (d) => { turnText += d; send("delta", { text: d }); });
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
      await send("done", { reply, actions, messages: compact.slice(-12) });
    } catch (e) { await send("error", { message: String(e.message || e) }); }
    finally { try { await writer.close(); } catch {} }
  };
  ctx.waitUntil(run());
  return new Response(readable, { headers: { "content-type": "text/event-stream", "cache-control": "no-store", "x-accel-buffering": "no" } });
}

/* ---------------- morning brief ---------------- */
async function makeMorning(env, request) {
  if (!env.ANTHROPIC_API_KEY) return { error: "no brain" };
  const client = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY });
  const context = await buildContext(env, request);
  const r = await client.beta.messages.create({
    model: MODEL, max_tokens: 1200, betas: ["server-side-fallback-2026-07-01"], fallbacks: "default", output_config: { effort: "medium" },
    system: BRAIN_SYSTEM + "\nYou are composing Jesse's spoken MORNING BRIEF. About 220 to 300 words, roughly two minutes read aloud. Structure as flowing prose: greeting with the date and weather in one breath; then what needs his attention today (unanswered leads and inquiries, alerts, anything slow or down, anything JARVIS noticed); then each business in a sentence or two with the numbers that matter and the week-over-week direction; then upcoming weddings, calendar items and any note or memory relevant to today; finish with one dry, encouraging line. No lists, no headers.",
    messages: [{ role: "user", content: "Compose this morning's brief.\n\nLIVE CONTEXT:\n" + context }],
  });
  const text = r.content.filter((b) => b.type === "text").map((b) => b.text).join(" ").trim();
  const morning = { at: new Date().toISOString(), text, audio: false };
  if (env.ELEVENLABS_API_KEY && text) {
    try { const a = await elevenlabs(env, text); if (a.ok) { await env.HUB.put("morning_audio", await a.arrayBuffer()); morning.audio = true; } } catch {}
  }
  await kv.put(env, "morning", morning);
  const headline = text.split(/(?<=[.!?])\s/).slice(0, 2).join(" ");
  await notify(env, "Morning brief", headline, { tags: "sunrise", url: new URL(request.url).origin + "/#morning" });
  return morning;
}

/* ---------------- ElevenLabs ---------------- */
function elevenlabs(env, text, format = "mp3_44100_64") {
  const voice = env.ELEVENLABS_VOICE_ID || "JBFqnCBsd6RMkjVDRZzb";
  return fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voice}/stream?output_format=${format}`, {
    method: "POST", headers: { "xi-api-key": env.ELEVENLABS_API_KEY, "content-type": "application/json" },
    body: JSON.stringify({ text: String(text).slice(0, 2500), model_id: "eleven_turbo_v2_5", voice_settings: { stability: 0.5, similarity_boost: 0.8, style: 0.2 } }),
  });
}
async function tts(request, env) {
  if (!env.ELEVENLABS_API_KEY) return json({ error: "tts not configured" }, 501);
  const { text } = await request.json();
  const r = await elevenlabs(env, text);
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

/* ---------------- worker ---------------- */
export default {
  async scheduled(event, env, ctx) {
    const cron = event.cron || "";
    if (cron.startsWith("*/5")) ctx.waitUntil(runChecks(env));
    else ctx.waitUntil((async () => {
      await loadCalendar(env, true).catch(() => null);
      if (localHour(env) === 7) {
        const fake = new Request("https://jarvis-hub.floral-credit-e4f0.workers.dev/", { cf: {} });
        await makeMorning(env, fake).catch((e) => pushAlert(env, { kind: "watch", text: "Morning brief failed: " + e.message }));
      }
    })());
  },

  async fetch(request, env, ctx) {
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

    if (p === "/api/config") return json({ user: who, google: !!env.GOOGLE_CLIENT_ID, brain: !!env.ANTHROPIC_API_KEY, tts: !!env.ELEVENLABS_API_KEY, pushover: !!(env.PUSHOVER_TOKEN && env.PUSHOVER_USER), ntfy: env.NTFY_TOPIC || null, email: !!(env.RESEND_API_KEY && env.ALERT_EMAIL), calendar: !!env.CAL_ICS_URL, tz: env.TZ || "America/Chicago" });
    if (p === "/api/status") {
      const cached = url.searchParams.get("fresh") ? null : await kv.get(env, "status");
      if (cached && Date.now() - new Date(cached.checkedAt) < 6 * 60000) return json({ ...cached, uptime: await kv.get(env, "uptime"), history: await kv.get(env, "rt_history") });
      const sites = await runChecks(env);
      return json({ checkedAt: new Date().toISOString(), sites, uptime: await kv.get(env, "uptime"), history: await kv.get(env, "rt_history") });
    }
    if (p === "/api/weather") { const place = url.searchParams.get("lat") ? { lat: url.searchParams.get("lat"), lon: url.searchParams.get("lon"), name: url.searchParams.get("place") } : await kv.get(env, "place"); const w = await weatherData(request, env, place); return json(w, w.error ? 400 : 200, { "cache-control": "public, max-age=300" }); }
    if (p === "/api/calendar") return json((await loadCalendar(env, !!url.searchParams.get("fresh"))) || { events: [], off: true });
    if (p === "/api/chat" && request.method === "POST") return chat(request, env, ctx);
    if (p === "/api/tts" && request.method === "POST") return tts(request, env);
    if (p === "/api/morning") return json((await kv.get(env, "morning")) || { none: true });
    if (p === "/api/morning/audio") { const a = await env.HUB.get("morning_audio", "arrayBuffer"); return a ? new Response(a, { headers: { "content-type": "audio/mpeg", "cache-control": "no-store" } }) : new Response("no audio", { status: 404 }); }
    if (p === "/api/morning/run" && request.method === "POST") return json(await makeMorning(env, request));
    if (p === "/api/test-alert" && request.method === "POST") return json({ ok: true, results: await notify(env, "JARVIS test", "Push notifications are wired up.", { tags: "robot" }) });

    // action queue: confirmed by Jesse on the page, executed by the hands script on his PC
    if (p === "/api/act" && request.method === "POST") {
      const item = await request.json(); const q = (await kv.get(env, "queue")) || [];
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
        for (const k of STATE_KEYS) if (k in body) { await kv.put(env, k, body[k]); saved.push(k); }
        if (body.metrics) ctx.waitUntil(watchMetrics(env, body.metrics));
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
