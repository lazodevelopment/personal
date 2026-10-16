// JARVIS hub worker.
// Dashboard + API: Google sign-in (one allowed email) or access key, site checks, weather/radar/alerts,
// a streaming Claude "brain" with pre-loaded context and confirm-first actions, ElevenLabs voice,
// morning brief, memory, calendar (private ICS), watchfulness (anomalies), and push via Pushover.
import html from "./hub.html";
import hubCss from "./hub.css";
import hubJs from "./hub.js";
import manifest from "./manifest.json";
import icon192 from "./icon-192.png";
import baroqueMp3 from "../sounds/baroque.mp3";   // the wake-up clip (Vivaldi, Spring); the open page rings with it, Pushover plays its own uploaded copy
import { vapidKeys, listSubs, saveSub, dropSub, SW_JS } from "./webpush.js";
import { STATE_KEYS, HUB_ORIGIN, json, kv, localHour, tfetch, pushAlert, within, healthNote } from "./core.js";
import { sameSecret, sessSecret, makeSession, FEED_ROUTES, FEED_STATE_KEYS, authed, setCookie, googleLogin, ICON, lockPage } from "./auth.js";
import { PUSHOVER_BUILTIN, notify, localParts, alarmToday, addReminder, tickMinute, callConfigured, alarmCall } from "./alarm.js";
import { intakeReport, ingestInbox, threadCached, emailAction, knownCorrespondent, makeFollowups } from "./inbox.js";
import { runChecks, watchMetrics, watchDecisions, checkStale, watchMerged, watchWatch, APPS, appStores, socialFromLog, healthReport, scanCompetitors } from "./watch.js";
import { weatherData, loadCalendar, sports, markets, radioNow, wxRadio, audacyNow, news, weddingWeather } from "./feeds.js";
import { fleetRemember, fleetStatus, toCallsign, trackFlight, worldEvents, satTles, windyNear, txSnapshot, flightRoute, applyHome, setHome, addTrip, tripWatch, shipWatch } from "./world.js";
import { mysteriesFor, rosaryScript, stripHtml, fetchReadingsPage, dailyReadings, saintOfDay, rosaryAudio } from "./faith.js";
import { ACT_KINDS, LOCAL_KINDS, runLocalAction, chat, tts } from "./brain.js";
import { SLOT_PROMPTS, SLOT_HOURS, briefIfDue, makeMorning, observe } from "./briefs.js";

const BUILD = (() => { const page = html + hubCss + hubJs; let h = 0; for (let i = 0; i < page.length; i += 7) h = (h * 31 + page.charCodeAt(i)) >>> 0; return h.toString(36) + "-" + page.length.toString(36); })();   // changes with every deploy of the page (markup, styles or script)


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

/* ---------------- worker ---------------- */
export default {
  async scheduled(event, env, ctx) {
    await applyHome(env);
    const cron = event.cron || ""; ctx.waitUntil(healthNote(env, "cron", cron));
    if (cron === "* * * * *") { ctx.waitUntil(tickMinute(env, true).catch((e) => console.log("minute", e.message))); return; }
    if (cron.startsWith("*/5") && new Date().getUTCMinutes() >= 10) ctx.waitUntil(briefIfDue(env).catch((e) => console.log("brief catch-up", e.message)));   // a skipped hourly tick still gets its brief
    if (cron.startsWith("*/5")) ctx.waitUntil(runChecks(env).then(() => checkStale(env)).then(() => tripWatch(env)).then(async () => { const t = await kv.get(env, "tick_at"); if (!t || Date.now() - new Date(t) > 90e3) await tickMinute(env); }).then(() => shipWatch(env)).then(() => socialFromLog(env)).then(() => watchMerged(env)).then((w) => w && watchWatch(env, { social: w.social, at: w.at })).catch((e) => console.log("5-min cron", e.message)));   // tickMinute here is only a backstop for a skipped minute cron
    else ctx.waitUntil((async () => {
      await loadCalendar(env, true).catch(() => null);
      await weddingWeather(env).catch(() => null);
      await briefIfDue(env);   // the brief goes before the slower jobs, so a long follow-up or observer run can't push it out of the tick
      await appStores(env).catch((e) => console.log("app stores", e.message));
      if (localHour(env) === 4) { await dailyReadings(env).catch((e) => console.log("readings", e.message)); await saintOfDay(env).catch((e) => console.log("saint", e.message)); const dowF = new Date().toLocaleDateString("en-US", { timeZone: env.TZ || "America/Chicago", weekday: "short" }); if (dowF === "Sat") { const sun = new Date(Date.now() + 86400e3).toLocaleDateString("en-CA", { timeZone: env.TZ || "America/Chicago" }); await dailyReadings(env, { date: sun }).catch((e) => console.log("vigil readings", e.message)); } }   // ready before the morning brief; Sunday's for the vigil
      await makeFollowups(env).catch((e) => console.log("follow-ups", e.message));
      await observe(env, new Request(HUB_ORIGIN + "/", { cf: {} })).catch((e) => console.log("observe", e.message));
      const dow = new Date().toLocaleDateString("en-US", { timeZone: env.TZ || "America/Chicago", weekday: "short" }), hr = localHour(env);
      if (dow === "Sun" && hr === 20) await scanCompetitors(env).catch((e) => console.log("competitors", e.message));
      if (dow === "Mon" && hr === 6) { const hadWeekly = ((await kv.get(env, "briefs")) || []).some((b) => b.slot === "weekly" && Date.now() - new Date(b.at) < 3 * 86400e3); if (!hadWeekly) { const fake = new Request(HUB_ORIGIN + "/", { cf: {} }); await makeMorning(env, fake, "weekly").catch((e) => pushAlert(env, { kind: "watch", text: "weekly review failed: " + e.message })); } }
    })());
  },

  async fetch(request, env, ctx) {
    await applyHome(env);
    const url = new URL(request.url); const p = url.pathname;
    if (p === "/auth" && request.method === "POST") {
      const form = await request.formData(); const key = String(form.get("key") || "");
      if (!env.HUB_KEY || !sessSecret(env) || !(await sameSecret(key, env.HUB_KEY))) return new Response(lockPage(env, "Wrong key."), { status: 403, headers: { "content-type": "text/html; charset=utf-8" } });
      return new Response(null, { status: 303, headers: [["location", "/"], ["set-cookie", setCookie("sess", await makeSession(env, "key"), 30 * 86400)], ["set-cookie", setCookie("hub", "", 0)]] });
    }
    if (p === "/auth/google" && request.method === "POST") return googleLogin(request, env);
    if (p === "/logout" && url.searchParams.get("all") && (await authed(request, env)) && (await authed(request, env)) !== "feed") await env.HUB.put("sess_ver", String(Date.now()));   // sign every device out
    if (p === "/logout") return new Response(null, { status: 303, headers: [["location", "/"], ["set-cookie", setCookie("hub", "", 0)], ["set-cookie", setCookie("sess", "", 0)]] });
    if (p === "/manifest.webmanifest") return new Response(manifest, { headers: { "content-type": "application/manifest+json" } });
    if (p === "/sw.js") return new Response(SW_JS, { headers: { "content-type": "application/javascript; charset=utf-8", "cache-control": "no-cache", "service-worker-allowed": "/" } });
    if (p === "/sounds/baroque.mp3") return new Response(baroqueMp3, { headers: { "content-type": "audio/mpeg", "cache-control": "public, max-age=604800" } });
    if (p === "/icon-192.png") return new Response(icon192, { headers: { "content-type": "image/png", "cache-control": "public, max-age=86400" } });
    if (p === "/icon.svg") return new Response(ICON, { headers: { "content-type": "image/svg+xml", "cache-control": "public, max-age=86400" } });

    const who = await authed(request, env);
    if (!who) {
      if (p.startsWith("/api/")) return json({ error: "unauthorized" }, 401);
      return new Response(lockPage(env), { status: 401, headers: { "content-type": "text/html; charset=utf-8" } });
    }
    if (who === "feed" && !FEED_ROUTES.has(request.method + " " + p)) return json({ error: "this key can only post feeds" }, 403);
    if (p === "/" || p === "/index.html" || p === "/wall") return new Response(html, { headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" } });
    if (p === "/hub.css") return new Response(hubCss, { headers: { "content-type": "text/css; charset=utf-8", "cache-control": "no-store" } });
    if (p === "/hub.js") return new Response(hubJs, { headers: { "content-type": "application/javascript; charset=utf-8", "cache-control": "no-store" } });

    if (p === "/api/config") return json({ user: who, google: !!env.GOOGLE_CLIENT_ID, brain: !!env.ANTHROPIC_API_KEY, tts: !!env.ELEVENLABS_API_KEY, windy: !!env.WINDY_KEY, pushover: !!(env.PUSHOVER_TOKEN && env.PUSHOVER_USER), call: callConfigured(env) ? (env.ALARM_CALL === "always" ? "always" : "fallback") : false, calendar: !!env.CAL_ICS_URL, home: (await kv.get(env, "home")) || { mode: "auto", key: "tx", tz: env.TZ || "America/Chicago", label: "Texas" }, teams: env.TEAMS || "DAL,NE,TEX,COL,BOS,ARI", tz: env.TZ || "America/Chicago", briefHours: SLOT_HOURS(env), build: BUILD });
    if (p === "/api/status") {
      const cached = url.searchParams.get("fresh") ? null : await kv.get(env, "status");
      if (cached && Date.now() - new Date(cached.checkedAt) < 6 * 60000) return json({ ...cached, uptime: await kv.get(env, "uptime"), history: await kv.get(env, "rt_history") });
      const sites = await runChecks(env);
      return json({ checkedAt: new Date().toISOString(), sites, uptime: await kv.get(env, "uptime"), history: await kv.get(env, "rt_history") });
    }
    if (p === "/api/weather") { const place = url.searchParams.get("lat") ? { lat: url.searchParams.get("lat"), lon: url.searchParams.get("lon"), name: url.searchParams.get("place") } : await kv.get(env, "place"); const w = await weatherData(request, env, place); return json(w, w.error ? 400 : 200, { "cache-control": "public, max-age=300" }); }
    if (p === "/api/sports") return json(await sports(env));
    if (p === "/api/markets") return json(await markets(env));
    if (p === "/api/radio/wx") return json(await wxRadio(request, env, +url.searchParams.get("lat") || 0, +url.searchParams.get("lon") || 0), 200, { "cache-control": "private, max-age=120" });
    if (p === "/api/radio/now") return json(url.searchParams.get("audacy") ? await audacyNow(url.searchParams.get("audacy")) : await radioNow(url.searchParams.get("u") || ""), 200, { "cache-control": "no-store" });
    if (p === "/api/news") return json(await news(env));
    if (p === "/api/wxdays") return json(url.searchParams.get("fresh") ? { days: await weddingWeather(env) } : ((await kv.get(env, "wxdays")) || { days: {} }));
    if (p === "/api/calendar") return json((await loadCalendar(env, !!url.searchParams.get("fresh"))) || { events: [], off: true });
    if (p === "/api/chat" && request.method === "POST") return chat(request, env, ctx);
    if (p === "/api/tts" && (request.method === "POST" || (request.method === "GET" && request.headers.get("sec-fetch-site") === "same-origin"))) return tts(request, env);   // GET streams into the page's <audio>; a link from another site must not spend ElevenLabs credit
    if (p === "/api/morning") return json({ latest: (await kv.get(env, "morning")) || null, history: (await kv.get(env, "briefs")) || [], stale: (await kv.get(env, "stale")) || {} });
    if (p === "/api/morning/audio") { const id = url.searchParams.get("id"); const a = await env.HUB.get(id ? "brief_audio_" + id : "brief_audio_" + ((await kv.get(env, "morning"))?.id || ""), "arrayBuffer"); return a ? new Response(a, { headers: { "content-type": "audio/mpeg", "cache-control": "no-store" } }) : new Response("no audio", { status: 404 }); }
    if (p === "/api/morning/run" && request.method === "POST") { const slotQ = url.searchParams.get("slot") || undefined; if (slotQ && !SLOT_PROMPTS[slotQ]) return json({ error: "slot must be one of " + Object.keys(SLOT_PROMPTS).join(", ") }, 400); return json(await makeMorning(env, request, slotQ)); }
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
    if (p === "/api/world/shipsfeed" && request.method === "POST") { const body = await request.json(); await env.HUB.put("ships_global", JSON.stringify(body)); await fleetRemember(env, body).catch((e) => console.log("fleet", e.message)); return json({ ok: true, ships: (body.ships || []).length }); }
    if (p === "/api/world/fleet") { const fs = await fleetStatus(env, url.searchParams.get("line") || "ncl"); return fs ? json(fs) : json({ error: "unknown fleet" }, 404); }
    if (p === "/api/world/ships") { const g = await env.HUB.get("ships_global"); return new Response(g || '{"ships":[]}', { headers: { "content-type": "application/json", "cache-control": "public, max-age=60" } }); }
    if (p === "/api/world/globalfeed" && request.method === "POST") { const body = await request.json(); await env.HUB.put("flights_global", JSON.stringify(body)); return json({ ok: true, ac: (body.ac || []).length }); }
    if (p === "/api/world/global") { const g = await env.HUB.get("flights_global"); return new Response(g || '{"ac":[]}', { headers: { "content-type": "application/json", "cache-control": "public, max-age=60" } }); }
    if (p === "/api/world/route") return json((await flightRoute(env, url.searchParams.get("cs"))) || { none: true });
    if (p === "/api/world/sats") return json(await satTles(env), 200, { "cache-control": "public, max-age=3600" });
    if (p === "/api/faith") { const m = mysteriesFor(env); const want = (url.searchParams.get("date") || "").match(/^\d{4}-\d{2}-\d{2}$/) ? url.searchParams.get("date") : null; let readings = null, err = null, saint = null, saintErr = null; try { readings = await dailyReadings(env, { fresh: !!url.searchParams.get("fresh"), date: want }); } catch (e) { err = e.message; } try { saint = await saintOfDay(env, { fresh: !!url.searchParams.get("fresh"), date: want }); } catch (e) { saintErr = e.message; } return json({ mysteries: m, rosary: rosaryScript(url.searchParams.get("set") || m.key), readings, error: err, saint, saintError: saintErr }); }
    if (p === "/api/observe" && request.method === "POST") return json((await observe(env, request, { force: true })) || { nothing: true });
    if (p === "/api/observations") return json((await kv.get(env, "observations")) || []);
    if (p === "/api/ships/watch" && request.method === "POST") { const b = await request.json(); let list = (await kv.get(env, "ship_watch")) || []; if (b.remove) list = list.filter((w) => w.name.toUpperCase() !== String(b.remove).toUpperCase()); if (b.name && !list.some((w) => w.name.toUpperCase() === String(b.name).toUpperCase())) list.push({ name: String(b.name).trim(), added: new Date().toISOString() }); await kv.put(env, "ship_watch", list); await shipWatch(env); return json(list); }
    if (p === "/api/health") return json(await healthReport(env, +url.searchParams.get("days") || 7));
    if (p === "/api/social/posted" && request.method === "POST") { const b = await request.json(); const log = (await kv.get(env, "social_log")) || {}; const day = /^\d{4}-\d{2}-\d{2}$/.test(b.at || "") ? b.at : new Date().toLocaleDateString("en-CA", { timeZone: env.TZ || "America/Chicago" }); (log[day] ||= {})[String(b.brand || "").toLowerCase()] = { day: b.day, media_id: b.media_id, linkedin_urn: b.linkedin_urn || null, at: new Date().toISOString() }; for (const k of Object.keys(log)) if (Date.now() - new Date(k) > 40 * 86400e3) delete log[k]; await kv.put(env, "social_log", log); await socialFromLog(env); return json({ ok: true, day, brand: b.brand }); }
    if (p === "/api/reminders" && request.method === "GET") return json(((await kv.get(env, "reminders")) || []).filter((r) => !r.done));
    if (p === "/api/reminders" && request.method === "POST") { const r = await addReminder(env, await request.json()); return json(r, r.error ? 400 : 200); }
    if (p === "/api/reminders/delete" && request.method === "POST") { const { id } = await request.json(); await kv.put(env, "reminders", ((await kv.get(env, "reminders")) || []).filter((r) => r.id !== id)); return json({ ok: true }); }
    if (p === "/api/alarm" && request.method === "GET") return json((await kv.get(env, "alarm")) || { enabled: false, time: "05:00", days: [] });
    if (p === "/api/alarm" && request.method === "POST") { const b = await request.json(); const cur = (await kv.get(env, "alarm")) || {}; const tm = String(b.time || "").match(/^(\d{1,2}):(\d{2})$/); const next = alarmToday(env, { ...cur, enabled: !!b.enabled, time: tm && +tm[1] <= 23 && +tm[2] <= 59 ? tm[1].padStart(2, "0") + ":" + tm[2] : (cur.time || "05:00"), days: Array.isArray(b.days) ? b.days.map(Number).filter((d) => d >= 0 && d <= 6) : (cur.days || []), station: b.station ?? cur.station ?? 0, at: new Date().toISOString() }); await kv.put(env, "alarm", next); return json(next); }
    if (p === "/api/alarm/ack" && request.method === "POST") {
      const b = await request.json().catch(() => ({})); const al = (await kv.get(env, "alarm")) || {}; const lp = localParts(env);
      if (b.action === "snooze") { al.snooze = new Date(Date.now() + 5 * 60e3).toISOString(); delete al.acked; }
      else { al.acked = lp.date; al.ackedAt = new Date().toISOString(); al.ackedBy = b.action === "wake" ? "page" : b.action || "page"; delete al.snooze; for (const rc of new Set([al.receipt, al.firedReceipt].filter(Boolean))) if (env.PUSHOVER_TOKEN) ctx.waitUntil(tfetch(`https://api.pushover.net/1/receipts/${rc}/cancel.json`, { method: "POST", body: new URLSearchParams({ token: env.PUSHOVER_TOKEN }) }).catch(() => null)); delete al.receipt; }
      await kv.put(env, "alarm_ack", { date: lp.date, action: b.action === "snooze" ? "snooze" : "ack", snooze: al.snooze || null, at: new Date().toISOString(), by: al.ackedBy || null });
      await kv.put(env, "alarm", al); return json({ ok: true, acked: al.acked || null, snooze: al.snooze || null });
    }
    if (p === "/api/push/vapid") return json({ key: (await vapidKeys(env)).pub, subs: (await listSubs(env)).map((s) => ({ ua: s.ua, label: s.label, at: s.at, endpoint: s.endpoint.slice(0, 48) })) });
    if (p === "/api/push/subscribe" && request.method === "POST") { const b = await request.json(); try { const n = await saveSub(env, b.subscription, { ua: request.headers.get("user-agent"), label: b.label }); return json({ ok: true, subs: n }); } catch (e) { return json({ error: e.message }, 400); } }
    if (p === "/api/push/unsubscribe" && request.method === "POST") { const b = await request.json(); return json({ ok: true, subs: await dropSub(env, b.endpoint) }); }
    if (p === "/api/push/log") return json((await kv.get(env, "push_log")) || []);
    if (p === "/api/alarm/call" && request.method === "POST") { const r = await alarmCall(env, "This is JARVIS. This is a test of the wake-up call. Good morning, sir."); return json(r, r.call === "unconfigured" ? 404 : 200); }
    if (p === "/api/alarm/receipt") { const al = (await kv.get(env, "alarm")) || {}; const id = url.searchParams.get("id") || al.firedReceipt || al.receipt; if (!id || !/^[a-z0-9]{10,40}$/i.test(id) || !env.PUSHOVER_TOKEN) return json({ error: "no receipt" }, 404); try { const r = await (await tfetch(`https://api.pushover.net/1/receipts/${id}.json?token=${env.PUSHOVER_TOKEN}`)).json(); const t = (s) => s ? new Date(s * 1000).toISOString() : null; return json({ id, ...r, acknowledged_at: t(r.acknowledged_at), last_delivered_at: t(r.last_delivered_at), expires_at: t(r.expires_at), delivery: al.delivery || null }); } catch (e) { return json({ error: e.message }, 502); } }
    if (p === "/api/push/sounds") { try { const s = await (await tfetch("https://api.pushover.net/1/sounds.json?token=" + env.PUSHOVER_TOKEN)).json(); return json({ baroque: !!s?.sounds?.baroque, custom: Object.keys(s?.sounds || {}).filter((k) => !PUSHOVER_BUILTIN.includes(k)) }); } catch (e) { return json({ error: String(e.message || e) }, 502); } }
    if (p === "/api/push/test" && request.method === "POST") {
      // what each channel says right now: Pushover's registered devices, and a real test push to every channel
      const b = await request.json().catch(() => ({})); const out = {};
      if (env.PUSHOVER_TOKEN && env.PUSHOVER_USER) { try { const r = await tfetch("https://api.pushover.net/1/users/validate.json", { method: "POST", body: new URLSearchParams({ token: env.PUSHOVER_TOKEN, user: env.PUSHOVER_USER }) }); out.pushoverDevices = await r.json(); } catch (e) { out.pushoverDevices = { error: e.message }; } }
      out.subs = (await listSubs(env)).map((s) => ({ ua: s.ua, label: s.label, at: s.at }));
      out.sent = await notify(env, b.alarm ? "test alarm" : "test", b.alarm ? "This is how the wake-up alarm arrives. Tap I'm up to stop it." : "Test push from the Radio panel at " + localParts(env).hm + ".", { priority: b.alarm ? "alarm" : "high", tags: "bell", url: HUB_ORIGIN + (b.alarm ? "/#wake" : "/") });
      if (b.alarm) { const al = (await kv.get(env, "alarm")) || {}; const po = out.sent.find((r) => r.pushover != null); if (po?.receipt) { al.receipt = po.receipt; await kv.put(env, "alarm", al); } }
      return json(out);
    }
    if (p === "/api/alarm/due") { const al = (await kv.get(env, "alarm")) || {}; const lp = localParts(env); const due = !!al.pcDue && al.pcDue === lp.date; if (due) { delete al.pcDue; await kv.put(env, "alarm", al); } return json({ due, time: al.time || null, station: al.station || 0 }); }
    if (p === "/api/faith/page") { try { const r = await fetchReadingsPage(env, url.searchParams.get("date")); return json({ title: r.title, parts: r.parts.map((x) => [x.kind, x.ref, x.text.length]) }); } catch (e) { return json({ error: e.message }, 502); } }
    if (p === "/api/faith/rosary/audio") return rosaryAudio(env, url.searchParams.get("set") || "glorious", url.searchParams.get("seg") || "open");
    if (p === "/api/competitors/scan" && request.method === "POST") return json({ changes: await scanCompetitors(env), competitors: (await kv.get(env, "competitors")) || [] });
    if (p === "/api/apps/targets") return json([...APPS, ...((await kv.get(env, "apps_watch")) || [])].filter((a) => a.ios));
    if (p === "/api/apps") return json(url.searchParams.get("fresh") ? await appStores(env) : ((await kv.get(env, "apps")) || {}));
    if (p === "/api/followups/run" && request.method === "POST") { if (url.searchParams.get("dry")) return json(await makeFollowups(env, { minAgeH: +url.searchParams.get("minAge") || 0, dry: true })); await makeFollowups(env); return json((await kv.get(env, "followups")) || []); }
    if (p === "/api/followups/skip" && request.method === "POST") { const { id } = await request.json(); const list = ((await kv.get(env, "followups")) || []).map((f) => f.id === id ? { ...f, status: "skipped" } : f); await kv.put(env, "followups", list); return json({ ok: true }); }
    if (p === "/api/trips" && request.method === "POST") return json(await addTrip(env, await request.json()));
    if (p === "/api/trips/delete" && request.method === "POST") { const { id } = await request.json(); await kv.put(env, "trips", ((await kv.get(env, "trips")) || []).filter((t) => t.id !== id)); return json({ ok: true }); }
    if (p === "/api/yt/resolve") {   // a channel page or any YouTube URL -> the live (or latest) video id; any other page -> an embeddable player found inside it
      try {
        let u = String(url.searchParams.get("u") || "").trim(); if (!/^https?:\/\//i.test(u)) u = "https://" + u;
        const x = new URL(u);
        if (!/(^|\.)youtube\.com$/.test(x.hostname)) {
          const r0 = await within(fetch(u, { headers: { "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36", "accept-language": "en-US,en;q=0.9" }, redirect: "follow" }), 10000, null);
          if (!r0 || !r0.ok) return json({ error: "page didn't answer (" + (r0?.status || "timeout") + ")" }, 502);
          const h0 = await r0.text(); const title = stripHtml((h0.match(/<title>([^<]*)<\/title>/) || [])[1] || "").split(/[|\-–]/)[0].trim();
          const ang = h0.match(/v\.angelcam\.com\/iframe\?v=([\w-]+)/) || h0.match(/angelcam\.com\/[^"'\s]*[?&]v=([\w-]+)/); if (ang) return json({ embed: `https://v.angelcam.com/iframe?v=${ang[1]}&autoplay=1`, title, kind: "angelcam" });
          const ytv = h0.match(/youtube(?:-nocookie)?\.com\/embed\/([\w-]{11})/) || h0.match(/youtube\.com\/watch\?v=([\w-]{11})/) || h0.match(/youtu\.be\/([\w-]{11})/); if (ytv) return json({ videoId: ytv[1], title, live: true });
          const vim = h0.match(/player\.vimeo\.com\/video\/(\d+)/); if (vim) return json({ embed: `https://player.vimeo.com/video/${vim[1]}?autoplay=1&muted=1`, title, kind: "vimeo" });
          const m3u = h0.match(/https?:\/\/[^"'\s]+\.m3u8[^"'\s]*/); if (m3u) return json({ error: "that page streams HLS video directly (" + m3u[0].slice(0, 60) + "…); it can't be framed, open it in a tab", title });
          return json({ error: "no player found", title });
        }
        const handle = (x.pathname.match(/^\/(@[\w.-]+|channel\/UC[\w-]+|c\/[\w.-]+|user\/[\w.-]+)/) || [])[1];
        const page = handle ? `https://www.youtube.com/${handle}/live` : u;
        const r = await within(fetch(page, { headers: { "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36", "accept-language": "en-US,en;q=0.9", cookie: "CONSENT=YES+1; SOCS=CAI" }, redirect: "follow" }), 9000, null);
        if (!r || !r.ok) return json({ error: "YouTube didn't answer (" + (r?.status || "timeout") + ")" }, 502);
        const h = await r.text();
        const id = (h.match(/"videoId":"([\w-]{11})"/) || [])[1] || (h.match(/<link rel="canonical" href="https:\/\/www\.youtube\.com\/watch\?v=([\w-]{11})/) || [])[1];
        if (!id) return json({ error: "no video found on that page" }, 404);
        const title = (h.match(/<title>([^<]*)<\/title>/) || [])[1]?.replace(/ - YouTube$/, "") || "";
        return json({ videoId: id, live: /"isLiveNow":true/.test(h), title, channel: handle || null });
      } catch (e) { return json({ error: String(e.message || e) }, 500); }
    }
    if (p === "/api/err") {   // the page reports its own script errors here, so a broken device can be diagnosed without its console
      if (request.method === "POST") { const e = await request.json().catch(() => ({})); const list = (await kv.get(env, "client_errors")) || []; list.unshift({ at: new Date().toISOString(), who, ua: String(request.headers.get("user-agent") || "").slice(0, 160), ...Object.fromEntries(Object.entries(e).map(([k, v]) => [k, String(v ?? "").slice(0, 400)])) }); await kv.put(env, "client_errors", list.slice(0, 40)); return json({ ok: true }); }
      return json((await kv.get(env, "client_errors")) || []);
    }
    if (p === "/api/home" && request.method === "POST") return json(await setHome(env, await request.json()));
    if (p === "/api/inbox" && request.method === "POST") return ingestInbox(env, await request.json(), ctx);
    if (p === "/api/intake" && request.method === "POST") { const r = await intakeReport(env, await request.json().catch(() => ({}))); return json(r, r.error ? 400 : 200); }
    if (p === "/api/intake") return json((await kv.get(env, "intake_log")) || {});
    if (p === "/api/inbox/thread") { const r = await threadCached(env, url.searchParams.get("account"), url.searchParams.get("t"), url.searchParams.get("d") || "", !!url.searchParams.get("fresh")); return json(r, r.error ? 502 : 200); }
    if (p === "/api/inbox/bridges") { const hooks = (await kv.get(env, "inbox_hooks")) || {}; const inbox = (await kv.get(env, "inbox")) || { accounts: {} }; return json(Object.entries(inbox.accounts).map(([a, v]) => ({ account: a, business: v.business, at: v.at, items: v.items.length, actions: !!hooks[a]?.url }))); }
    // action queue: confirmed by Jesse on the page. Email kinds run right now through the Gmail bridge; the rest wait for the hands script on his PC
    if (p === "/api/act" && request.method === "POST") {
      const raw = await request.json();
      if (!ACT_KINDS.includes(raw.kind)) return json({ ok: false, error: "unknown action kind" }, 400);
      if (raw.kind === "email_send" && !raw.newRecipientOk && !(await knownCorrespondent(env, raw.params?.to))) return json({ ok: false, needsNewOk: true, to: raw.params?.to || "", result: "new address: confirm the recipient" });
      if (LOCAL_KINDS.includes(raw.kind)) { const res = await runLocalAction(env, raw); const q = (await kv.get(env, "queue")) || []; q.unshift({ ...raw, status: res.ok ? "done" : "failed", result: res.message, confirmedAt: new Date().toISOString(), doneAt: new Date().toISOString() }); await kv.put(env, "queue", q.slice(0, 50)); return json({ ok: res.ok, id: raw.id, executed: true, result: res.message }); }
      const q = (await kv.get(env, "queue")) || [];
      // the queue (KV) keeps only the attachment names, never the bytes
      const item = Array.isArray(raw.params?.attachments) ? { ...raw, params: { ...raw.params, attachments: raw.params.attachments.map((a) => ({ name: a?.name, size: a?.size || Math.round(String(a?.data || "").length * 0.75) })) } } : raw;
      if (String(item.kind || "").startsWith("email_")) {
        const res = await emailAction(env, raw);
        if (res.ok && item.params?.followupId) { const fl = ((await kv.get(env, "followups")) || []).map((f) => f.id === item.params.followupId ? { ...f, status: "sent", sentAt: new Date().toISOString() } : f); await kv.put(env, "followups", fl); }
        q.unshift({ ...item, status: res.ok ? "done" : "failed", result: res.message, confirmedAt: new Date().toISOString(), doneAt: new Date().toISOString() });
        await kv.put(env, "queue", q.slice(0, 50)); await pushAlert(env, { kind: res.ok ? "done" : "failed", text: (res.ok ? "Done: " : "Failed: ") + item.summary + (res.message ? " — " + res.message : "") });
        return json({ ok: res.ok, id: item.id, executed: true, result: res.message });
      }
      q.unshift({ ...item, status: "pending", confirmedAt: new Date().toISOString() });
      await kv.put(env, "queue", q.slice(0, 50)); return json({ ok: true, id: item.id });
    }
    if (p === "/api/queue" && request.method === "GET") return json(((await kv.get(env, "queue")) || []).filter((q) => q.status === "pending"));
    if (p === "/api/queue/claim" && request.method === "POST") { const { id } = await request.json(); const q = (await kv.get(env, "queue")) || []; const it = q.find((x) => x.id === id); if (!it || it.status !== "pending") return json({ ok: false, status: it?.status || "missing" }); it.status = "running"; it.claimedAt = new Date().toISOString(); await kv.put(env, "queue", q); return json({ ok: true }); }
    if (p === "/api/queue/result" && request.method === "POST") {
      const { id, ok, message } = await request.json(); const q = (await kv.get(env, "queue")) || [];
      const it = q.find((x) => x.id === id); if (it) { it.status = ok ? "done" : "failed"; it.result = message; it.doneAt = new Date().toISOString(); }
      await kv.put(env, "queue", q); if (it) await pushAlert(env, { kind: ok ? "done" : "failed", text: (ok ? "Done: " : "Failed: ") + it.summary + (message ? " — " + message : "") });
      return json({ ok: true });
    }
    if (p === "/api/queue/cancel" && request.method === "POST") { const { id } = await request.json(); const q = ((await kv.get(env, "queue")) || []).map((x) => x.id === id && x.status === "pending" ? { ...x, status: "cancelled" } : x); await kv.put(env, "queue", q); return json({ ok: true }); }

    if (p === "/api/state") {
      if (request.method === "GET") { const out = {}; await Promise.all(STATE_KEYS.map(async (k) => { const v = k === "watch" ? await watchMerged(env) : await kv.get(env, k); if (v != null) out[k] = v; })); return json(out); }
      if (request.method === "POST" || request.method === "PUT") {
        const body = await request.json(); const saved = [];
        if (who === "feed") for (const k of Object.keys(body)) if (!FEED_STATE_KEYS.includes(k)) delete body[k];
        // two feeders (PC and cloud) may post the same snapshot; a feeder that cannot read a business must not wipe the other's good numbers
        if (body.metrics?.businesses) { const cur = await kv.get(env, "metrics"); for (const [id, b] of Object.entries(body.metrics.businesses)) { const prev = cur?.businesses?.[id]; if (b?.error && prev && !prev.error && Date.now() - new Date(cur.collectedAt) < 6 * 3600e3) body.metrics.businesses[id] = prev; } }
        if (body.traffic?.sites) { const cur = await kv.get(env, "traffic"); for (const [id, t] of Object.entries(body.traffic.sites)) { const prev = cur?.sites?.[id]; if (t?.error && prev && !prev.error && Date.now() - new Date(cur.at) < 30 * 60e3) body.traffic.sites[id] = prev; } }
        for (const k of STATE_KEYS) if (k in body) {
          if (k === "brief" && body.brief?.source !== "bridge" && !body.brief?.force) { const cur = await kv.get(env, "brief"); if (cur?.source === "bridge") continue; } // live bridges outrank the hourly snapshot
          if (k === "watch" && body.watch && !Array.isArray(body.watch)) { const cur = (await kv.get(env, "watch")) || {}; const inPay = body.watch.payments, curPay = cur.payments; if (Array.isArray(inPay) && Array.isArray(curPay) && !inPay.some((x) => x.id) && curPay.some((x) => x.id) && Date.now() - new Date(cur.at || 0) < 2 * 3600e3) body.watch.payments = curPay; body.watch = { ...cur, ...body.watch }; } // PC and cloud feeder each post their own sections; a feeder that cannot read the bookings keeps the other's list
          await kv.put(env, k, body[k]); saved.push(k);
        }
        if (body.metrics) ctx.waitUntil(Promise.all([watchMetrics(env, body.metrics), weddingWeather(env)]).catch((e) => console.log("metrics watch", e.message)));
        if (body.decisions) ctx.waitUntil(watchDecisions(env, body.decisions).catch((e) => console.log("decisions", e.message)));
        if (body.watch) ctx.waitUntil(watchWatch(env, body.watch).catch((e) => console.log("watch", e.message)));
        return json({ saved, at: new Date().toISOString() });
      }
    }
    return new Response("Not found", { status: 404 });
  },
};
