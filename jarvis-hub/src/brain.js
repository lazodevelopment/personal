// JARVIS hub: The brain: live context, system prompt, tools, actions, streaming chat and ElevenLabs voice.
import Anthropic from "@anthropic-ai/sdk";
import { BIZ_NAME, MODEL, json, kv, localTime, uid, BIZ_LABEL, within, cached, fmtUsd, payWhy, siteName } from "./core.js";
import { alarmToday, addReminder } from "./alarm.js";
import { watchMerged, healthReport, healthSummary } from "./watch.js";
import { weatherData, weatherSummary, sportsSummary, markets, marketsSummary, news, newsSummary, wxdaysSummary } from "./feeds.js";
import { fleetStatus, flightsNear, trackFlight, flightRoute, HOMES, addTrip, shipWatch } from "./world.js";
import { mysteriesFor } from "./faith.js";

/* ---------------- context for the brain ---------------- */
export async function buildContext(env, request) {
  const [status, metrics, brief, notes, memory, alerts, place, cal, morning, queue, traffic, wxdays, intakeLog] = await Promise.all(["status", "metrics", "brief", "notes", "memory", "alerts", "place", "calendar", "morning", "queue", "traffic", "wxdays", "intake_log"].map((k) => kv.get(env, k)));
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
    if (metrics.money?.forecast) lines.push(`CASH FORECAST (unpaid balances by due week, next 90 days, total $${Math.round(metrics.money.forecast90 || 0).toLocaleString()}): ` + metrics.money.forecast.filter((w) => w.total).map((w) => `week of ${w.week} $${Math.round(w.total).toLocaleString()} (${w.items.join("; ")})`).join(" | ") + (metrics.money.pastDue?.length ? ` | PAST DUE $${Math.round(metrics.money.pastDueTotal).toLocaleString()}: ` + metrics.money.pastDue.map((x) => `${BIZ_NAME[x.business] || x.business} ${x.who} $${x.amount} due ${x.due}${x.attempts ? " (" + x.attempts + " failed attempts)" : ""}`).join("; ") : ""));
    if (metrics.money?.yoy) lines.push(`YEAR-AGO (same 7 days last year vs the last 7 days): ` + Object.entries(metrics.money.yoy).map(([id, y]) => y.has_history ? `${BIZ_NAME[id]}: revenue $${y.revenue} → $${y.revenue_now}, bookings ${y.bookings} → ${y.bookings_now}, leads ${y.leads} → ${y.leads_now}` : `${BIZ_NAME[id]}: no prior-year data yet`).join(" | "));
    if (metrics.money) lines.push(`MONEY: this month $${Math.round(metrics.money.thisMonth).toLocaleString()} (last month $${Math.round(metrics.money.lastMonth).toLocaleString()}); recent months: ` + metrics.money.months.slice(-6).map((m) => `${m.ym} $${Math.round(m.total)}`).join(", "));
  } else lines.push("METRICS: none collected yet");
  lines.push(`INBOX (${brief?.source === "bridge" ? "live Gmail bridges" : "hourly snapshot"}, ${brief?.at || "none"}): ${brief?.note || ""} ` + (brief?.items || []).slice(0, 20).map((m) => `[${BIZ_LABEL[m.business] || m.business || ""} | ${m.account || ""} | ${m.threadId || "no-id"}] ${m.from}: ${m.subject}${m.needs_reply ? " (NEEDS REPLY)" : ""}${m.intake ? " (AUTO-REPLIED BY THE INTAKE SCRIPT, see INTAKE)" : ""}${m.unread ? " (unread)" : ""} — ${m.snippet || ""}`).join(" | "));
  const il = Object.values(intakeLog || {}).filter((x) => Date.now() - new Date(x.date) < 3 * 86400e3).sort((a, b) => String(b.date).localeCompare(String(a.date))).slice(0, 12);
  lines.push(`INTAKE (Zola and The Knot inquiries for Atavia and Elizabeth Scott get their first reply from the Gmail intake script within minutes, never from JARVIS; this is the check that each reply went out, last 3 days): ` + (il.length ? il.map((x) => `${BIZ_NAME[x.business] || x.business} ${String(x.date).slice(0, 16)} ${x.who || x.subject}: ${x.state === "replied" ? "replied (" + x.detail + ")" : x.state === "pending" ? "not confirmed yet (waiting for the script's report or the Sent check)" : x.state.toUpperCase() + " — " + x.detail}`).join(" | ") : "no marketplace inquiries in the last 3 days"));
  lines.push(`ALERTS (latest): ` + (alerts || []).slice(0, 6).map((a) => `${a.at.slice(0, 16)} ${a.text}`).join(" | "));
  if (cal?.events?.length) lines.push(`CALENDAR (next 60d): ` + cal.events.slice(0, 20).map((e) => `${e.start.slice(0, 16)} ${e.title}${e.location ? " @ " + e.location : ""}`).join("; "));
  else lines.push("CALENDAR: not connected");
  lines.push(`NOTES:\n${notes || "(empty)"}`);
  lines.push(`MEMORY: ` + ((memory || []).map((m) => `[${m.id}] ${m.text}`).join(" | ") || "(nothing remembered yet)"));
  const dec = await kv.get(env, "decisions");
  lines.push(`WAITING ON JESSE (${dec?.at || "none"}): ` + ((dec?.items || []).map((d) => `[${d.id}] ${d.label} (${d.kind}, ${d.at.slice(0, 10)})`).join(" | ") || "nothing pending"));
  const [watch, fups, trips, apps] = await Promise.all([watchMerged(env), ...["followups", "trips", "apps"].map((k) => kv.get(env, k))]);
  if (Array.isArray(watch?.payments)) lines.push(`BALANCE CHARGES (last 7 / next 7 days, ${watch.at}): ` + (watch.payments.filter((p) => p.id).map((p) => `${BIZ_LABEL[p.business]} ${p.names} ${fmtUsd(p.amount)} due ${String(p.due).slice(0, 10)} ${p.state}${p.state === "failed" ? " (attempt " + p.attempts + "/3: " + payWhy(p.error) + ")" : ""}`).join("; ") || "none"));
  if (watch?.social?.brands) lines.push(`SOCIAL POSTS TODAY (${watch.social.day}): ` + watch.social.brands.map((b) => `${b.name} ${b.today ? "posted" : "NOT posted (last " + (b.last || "never") + ")"}`).join(", "));
  if (watch?.search) lines.push(`SEARCH CONSOLE: ` + (watch.search.sites?.length ? watch.search.sites.map((x) => { const d = x.days || []; const sum = (rows, i) => rows.reduce((a, r) => a + r[i], 0); return `${siteName(x.site)} last 7d ${sum(d.slice(-7), 1)} clicks / ${sum(d.slice(-7), 2)} impressions (prior 7d ${sum(d.slice(-14, -7), 1)} / ${sum(d.slice(-14, -7), 2)})`; }).join("; ") : "not connected yet (" + (watch.search.fix || watch.search.error || "") + ")"));
  const compCh = await kv.get(env, "competitor_changes"); const comps = await kv.get(env, "competitors");
  if (comps?.length) lines.push(`COMPETITORS WATCHED: ` + comps.map((c) => `${c.label} (${c.business || "?"}) ${c.url}`).join("; ") + ` | CHANGES (last scan): ` + ((compCh || []).slice(0, 8).map((c) => `${c.at.slice(0, 10)} ${c.label}: ${c.summary}`).join(" | ") || "none detected"));
  try { const todayKey = new Date().toLocaleDateString("en-CA", { timeZone: env.TZ || "America/Chicago" }); const rd = await kv.get(env, "readings_" + todayKey); const st = await kv.get(env, "saint_" + todayKey); const my = mysteriesFor(env);
    lines.push(`FAITH: today's rosary is the ${my.name} (${my.why}; ${my.season}). ` + (st ? `Saint of the day: ${st.name}${st.plain?.title ? ", " + st.plain.title : ""}. ${st.plain?.why || st.blurb || ""} ${st.plain?.today || ""} ` : "") + (rd ?`Mass readings: ${rd.title}: ${rd.parts.map((x) => x.kind + " " + x.ref).join("; ")}. Theme: ${rd.reflection?.theme || ""}. Plain-words conclusion: ${(rd.reflection?.conclusion || "").slice(0, 500)}` : "Mass readings not loaded yet (the Faith panel loads them).")); } catch {}
  try { const sg = await env.HUB.get("ships_global"); if (sg) { const g = JSON.parse(sg); lines.push(`SHIPS: ${g.ships.length} passenger vessels (cruise ships and ferries) tracked worldwide as of ${g.at}; ${g.ships.filter((r) => r[8] >= 200).length} are 200 m or longer (cruise-size).`); } } catch {}
  try { const fs = await fleetStatus(env, "ncl"); if (fs) { const heard = fs.ships.filter((s) => s.seen), never = fs.ships.filter((s) => !s.seen); lines.push(`NORWEGIAN FLEET (${fs.ships.filter((s) => s.live).length} of ${fs.ships.length} in the live feed; the rest are last-known): ` + heard.map((s) => `${s.name}${s.live ? "" : " (" + s.ageMin + " min ago)"} ${s.lat?.toFixed(1)},${s.lon?.toFixed(1)}${s.speed_kt != null ? " " + Math.round(s.speed_kt) + " kt" : ""}${s.destination ? " -> " + s.destination : ""}`).join("; ") + (never.length ? "; never heard: " + never.map((s) => s.name).join(", ") : "")); } } catch {}
  if (apps) lines.push(`APP STORES: ` + Object.values(apps).map((a) => `${a.name} ${a.listed ? "live" + (a.version ? " v" + a.version : "") + (a.released ? " released " + String(a.released).slice(0, 10) : "") : "not listed yet"}`).join("; "));
  const readyF = (fups || []).filter((f) => f.status === "ready");
  if (readyF.length) lines.push(`FOLLOW-UPS DRAFTED, waiting for Jesse to send (Decisions panel): ` + readyF.map((f) => `${BIZ_LABEL[f.business]} ${f.from}: ${f.subject}`).join("; "));
  if (trips?.length) lines.push(`TRIPS: ` + trips.map((t) => `${t.date} ${t.flight}${t.route?.from ? " " + (t.route.from.city || t.route.from.iata) + " to " + (t.route.to?.city || t.route.to?.iata) : ""} ${t.phase || "scheduled"}${t.home ? " (home becomes " + HOMES[t.home]?.label + " on landing)" : ""}`).join("; "));
  try { const hr = await healthReport(env, 7); lines.push(`JARVIS HEALTH (last 7 days): ${healthSummary(hr)}`); } catch {}
  const [rems, alarmCfg] = await Promise.all([kv.get(env, "reminders"), kv.get(env, "alarm")]);
  lines.push(`REMINDERS: ` + ((rems || []).filter((r) => !r.done).slice(0, 12).map((r) => `[${r.id}] ${new Date(r.at).toLocaleString("en-US", { timeZone: env.TZ || "America/Chicago", weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })} ${r.text}${r.repeat !== "none" ? " (" + r.repeat + ")" : ""}`).join(" | ") || "none"));
  lines.push(`WAKE-UP ALARM: ` + (alarmCfg?.enabled ? `${alarmCfg.time} ${!alarmCfg.days?.length ? "every day" : "days " + alarmCfg.days.join(",")}` : "off"));
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
  tools: { cloudflare: "https://dash.cloudflare.com/", zoho: "https://payments.zoho.com/", gmail: "https://mail.google.com/", calendar: "https://calendar.google.com/", gsc: "https://search.google.com/search-console", flutterflow: "https://app.flutterflow.io/", resend: "https://resend.com/emails" },
};

export const BRAIN_SYSTEM = `You are JARVIS, the personal operations assistant for Jesse Clark, who runs five businesses:
Atavia Weddings and Elizabeth Scott Weddings (wedding films), Lazo (wedding planner app + vendor directory), Roven HR (hiring platform), LeaseReputation (apartment reviews).
Persona: calm, dry, precise, British; a trusted chief of staff. Address him sparingly, alternating between "sir" and "Mr. Clark" (never both in one reply; vary from one reply to the next, "Mr. Clark" for greetings and anything formal, "sir" in passing).
Your replies are spoken aloud through text-to-speech: plain prose, no markdown, no lists, no headers, no URLs read aloud. Two to four sentences unless he asks for detail. Lead with the answer. Round numbers sensibly.
Everything about his businesses is in the LIVE CONTEXT; answer from it directly and do not invent figures. For anything outside it (news, facts, prices, places, people, how-to questions, "look up", "search") use the web_search tool, then answer in two to four spoken sentences and name the source in words (no URLs). If something isn't in the context and can't be searched, say so.
Ships: find_ship for "where is the <ship name>" (cruise ships and ferries, from AIS); watch_ship for "tell me when the <ship> shows up"; fleet_status for "where are the Norwegian ships" (the whole Norwegian Cruise Line fleet, live or last known; the World panel lists it too). Coverage is from shore receivers, so mid-ocean and some islands (Bermuda) are blind spots; say so when a ship is not found.
Flights: use track_flight for any question about where a flight is (convert "American 2612" to "AA 2612"), and flights_overhead for "what's flying over me". Say where it is flying from and to (route.from / route.to cities) when known. Report altitude in feet, speed in mph (knots x 1.15) and roughly where it is relative to cities; if not found yet, say you've started tracking it and it will appear on the World globe within a minute if it's airborne.
Actions: open_link opens pages; append_note for the notes board; remember/forget for durable facts about Jesse, his clients or preferences (use remember whenever he says "remember", "note that", "from now on"); draft_reply writes an email reply (shown with an Open-in-Gmail button, nothing is sent); request_action for anything that changes business data (approve a Roven job or employer, approve or reject a Lazo vendor claim or a Lazo listing request, add a booking note, mark a Lazo inquiry responded) AND for email: email_reply (params.account = the exact Gmail address shown in the INBOX line brackets for that thread, e.g. info@ataviaweddings.com, never a business name; params.threadId; params.body: the full reply text you wrote, signed appropriately for that business), email_archive, email_read, email_send (params.account, params.to, params.subject, params.body). When he asks you to reply to an email, write the reply yourself in his voice (warm, brief, professional) and submit it as email_reply; he confirms before anything is sent. request_action only queues it for his confirmation; say it is ready for his confirmation. Never claim an action is done until RECENT ACTIONS shows it done. Use the ids shown in brackets in the context.
Marketplace inquiries: Zola and The Knot inquiry notices for Atavia and Elizabeth Scott are answered automatically by the Gmail intake script in that account within five minutes. Never draft, offer or queue a reply to one of those notices. Your job there is verification: the INTAKE line says whether each notice got its automatic reply. If one says MISSING or REVIEW, tell him plainly that the script did not reply and that he should check that account's Apps Script executions; if it says replied, say the script handled it. A couple's later "New message from" email on Zola is a real conversation and is handled like any other reply.
Reminders and alarm: set_reminder for "remind me…" (compute the local date-time from TIME), cancel_reminder, set_alarm for "wake me at…". Confirm the time back in words.
Faith: he is Catholic. For "what are today's readings / gospel" or "what does it mean", answer from the FAITH line (theme and plain-words conclusion). For "pray the rosary" the page itself leads it; say you're starting it.
Competitors: watch_competitor adds a pricing/packages page to the Sunday scan; changes appear in COMPETITORS and the Monday review.
Trips: when he mentions a flight he is taking ("I fly AA 2612 to Phoenix on Friday"), call add_trip with the flight number, the local date (YYYY-MM-DD) and home 'az' when he is flying to Arizona or 'tx' when flying to Texas. JARVIS then tracks it on the day, pushes wheels-up and landed, and switches home on landing. remove_trip cancels one.
App stores: watch_app adds an app listing to watch (iOS numeric id or bundle id, Android package name), e.g. once Jovi's app exists.`;

const BRAIN_TOOLS = [
  { name: "track_flight", description: "Live position of a flight by flight number or callsign (e.g. 'AA 2612', 'SWA653', 'N123AB'). Returns altitude (ft), ground speed (kt), heading and coordinates. Also shows it on the World globe.", input_schema: { type: "object", properties: { flight: { type: "string" } }, required: ["flight"], additionalProperties: false }, strict: true },
  { name: "fleet_status", description: "Every Norwegian Cruise Line ship: live AIS position, speed, destination, or the last known position with how long ago. For 'where are the Norwegian ships', 'fleet status', 'is the Bliss at sea'.", input_schema: { type: "object", properties: {}, additionalProperties: false }, strict: true },
  { name: "find_ship", description: "Find a cruise ship or ferry by name in the live AIS feed: position, speed, heading, destination. Also centres the World globe on it.", input_schema: { type: "object", properties: { name: { type: "string" } }, required: ["name"], additionalProperties: false }, strict: true },
  { name: "watch_ship", description: "Tell Jesse when a named vessel appears in the AIS feed (push + spoken). Use for 'tell me when the <ship> shows up'. Also lists or clears watches.", input_schema: { type: "object", properties: { name: { type: "string" }, action: { type: "string", enum: ["add", "remove", "list"] } }, required: ["name", "action"], additionalProperties: false }, strict: true },
  { name: "flights_overhead", description: "Aircraft currently within N nautical miles of Jesse's home location (default 25).", input_schema: { type: "object", properties: { nm: { type: "number" } }, required: ["nm"], additionalProperties: false }, strict: true },
  { name: "open_link", description: "Open a URL in a new tab on Jesse's screen.", input_schema: { type: "object", properties: { url: { type: "string" }, label: { type: "string" } }, required: ["url", "label"], additionalProperties: false }, strict: true },
  { name: "append_note", description: "Add a line to the notes board.", input_schema: { type: "object", properties: { text: { type: "string" } }, required: ["text"], additionalProperties: false }, strict: true },
  { name: "remember", description: "Store a durable fact or preference in JARVIS's memory.", input_schema: { type: "object", properties: { text: { type: "string" } }, required: ["text"], additionalProperties: false }, strict: true },
  { name: "forget", description: "Delete a memory by its id (shown in MEMORY as [id]).", input_schema: { type: "object", properties: { id: { type: "string" } }, required: ["id"], additionalProperties: false }, strict: true },
  { name: "draft_reply", description: "Draft an email reply. Shown to Jesse with an Open in Gmail button; nothing is sent automatically.", input_schema: { type: "object", properties: { to: { type: "string" }, subject: { type: "string" }, body: { type: "string" }, business: { type: "string", enum: ["atavia", "es", "lazo", "roven", "lr", "brisk"] } }, required: ["to", "subject", "body", "business"], additionalProperties: false }, strict: true },
  { name: "add_trip", description: "Add a flight Jesse is taking. JARVIS tracks it on the day, pushes wheels-up and landed, and switches home on landing.", input_schema: { type: "object", properties: { flight: { type: "string", description: "e.g. 'AA 2612'" }, date: { type: "string", description: "local departure date YYYY-MM-DD" }, home: { type: "string", enum: ["tx", "az", "none"] }, note: { type: "string" } }, required: ["flight", "date", "home", "note"], additionalProperties: false }, strict: true },
  { name: "remove_trip", description: "Remove a trip by its id (shown in TRIPS or from add_trip).", input_schema: { type: "object", properties: { id: { type: "string" } }, required: ["id"], additionalProperties: false }, strict: true },
  { name: "watch_app", description: "Watch an app store listing and push when it goes live or updates.", input_schema: { type: "object", properties: { name: { type: "string" }, platform: { type: "string", enum: ["ios", "android"] }, id: { type: "string", description: "iOS numeric app id or bundle id; Android package name" } }, required: ["name", "platform", "id"], additionalProperties: false }, strict: true },
  { name: "set_reminder", description: "Set a reminder. JARVIS pushes it to Jesse's phone at that time (and says it aloud if the page is open). Convert relative times ('in 20 minutes', 'tomorrow at 9', 'Friday 3pm') to a local date-time using TIME in the context.", input_schema: { type: "object", properties: { text: { type: "string" }, when: { type: "string", description: "local date-time YYYY-MM-DD HH:MM in the home zone" }, repeat: { type: "string", enum: ["none", "daily", "weekdays", "weekly"] } }, required: ["text", "when", "repeat"], additionalProperties: false }, strict: true },
  { name: "cancel_reminder", description: "Cancel a reminder by its id (shown in REMINDERS as [id]).", input_schema: { type: "object", properties: { id: { type: "string" } }, required: ["id"], additionalProperties: false }, strict: true },
  { name: "set_alarm", description: "Set or change the wake-up alarm (server side: Pushover alarm on the phone playing a Vivaldi clip until he taps; the PC no longer plays). days: 'all', 'weekdays' or 'weekends'.", input_schema: { type: "object", properties: { time: { type: "string", description: "HH:MM 24h local" }, enabled: { type: "boolean" }, days: { type: "string", enum: ["all", "weekdays", "weekends"] } }, required: ["time", "enabled", "days"], additionalProperties: false }, strict: true },
  { name: "watch_competitor", description: "Add a competitor web page (pricing or packages page) to the weekly price-change scan.", input_schema: { type: "object", properties: { url: { type: "string" }, label: { type: "string" }, business: { type: "string", enum: ["atavia", "es", "lazo", "roven", "lr"] } }, required: ["url", "label", "business"], additionalProperties: false }, strict: true },
  { name: "request_action", description: "Queue a business-data change for Jesse's confirmation. kinds: roven_approve_job (params.jobId), roven_reject_job (params.jobId), roven_approve_employer (params.employerId), lazo_claim (params.claimId, params.decision 'approved'|'rejected'), lazo_listing (params.requestId, params.decision 'approved'|'denied': a new vendor asking to be listed), booking_note (params.business 'atavia'|'es', params.bookingId, params.note), lazo_inquiry_responded (params.inquiryId), email_reply (params.account, params.threadId, params.body), email_archive (params.account, params.threadId), email_read (params.account, params.threadId), email_send (params.account, params.to, params.subject, params.body).", input_schema: { type: "object", properties: { kind: { type: "string", enum: ["roven_approve_job", "roven_reject_job", "roven_approve_employer", "lazo_claim", "lazo_listing", "booking_note", "lazo_inquiry_responded", "email_reply", "email_archive", "email_read", "email_send"] }, params: { type: "object", properties: { jobId: { type: "string" }, employerId: { type: "string" }, claimId: { type: "string" }, requestId: { type: "string" }, decision: { type: "string" }, business: { type: "string" }, bookingId: { type: "string" }, note: { type: "string" }, inquiryId: { type: "string" }, account: { type: "string" }, threadId: { type: "string" }, body: { type: "string" }, to: { type: "string" }, subject: { type: "string" } } }, summary: { type: "string", description: "One line Jesse will confirm, e.g. 'Approve Roven job Senior RN at Mercy'" } }, required: ["kind", "params", "summary"], additionalProperties: false } },
];

// what /api/act accepts: the executor's business kinds, email kinds (run now through the Gmail bridge) and local kinds (run here)
export const ACT_KINDS = ["roven_approve_job", "roven_reject_job", "roven_approve_employer", "lazo_claim", "lazo_listing", "booking_note", "lazo_inquiry_responded", "email_reply", "email_archive", "email_read", "email_send", "memory_add", "alarm_off", "competitor_add"];
export const LOCAL_KINDS = ["memory_add", "alarm_off", "competitor_add"];
const safeHttp = (u) => { try { return /^https?:$/.test(new URL(String(u)).protocol); } catch { return false; } };
export async function runLocalAction(env, item) {
  const p = item.params || {};
  if (item.kind === "memory_add") { const mem = (await kv.get(env, "memory")) || []; mem.unshift({ id: uid(), text: String(p.text || "").slice(0, 600), at: new Date().toISOString() }); await kv.put(env, "memory", mem.slice(0, 200)); return { ok: true, message: "remembered" }; }
  if (item.kind === "alarm_off") { const cur = (await kv.get(env, "alarm")) || {}; await kv.put(env, "alarm", { ...cur, enabled: false, at: new Date().toISOString() }); return { ok: true, message: "alarm off" }; }
  if (item.kind === "competitor_add") { if (!safeHttp(p.url)) return { ok: false, message: "not an http(s) page" }; return { ok: true, message: await runTool("watch_competitor_confirmed", p, env, []) }; }
  return { ok: false, message: "unknown kind" };
}

async function runTool(name, input, env, actions, saidRemember = true) {
  switch (name) {
    case "track_flight": { const r = await trackFlight(env, input.flight); r.route = await flightRoute(env, r.callsign); actions.push({ type: "world", flight: r.callsign }); return JSON.stringify(r).slice(0, 3000); }
    case "fleet_status": return JSON.stringify(await fleetStatus(env, "ncl"));
    case "find_ship": { const g = JSON.parse((await env.HUB.get("ships_global")) || '{"ships":[]}'); const q = String(input.name || "").toUpperCase().replace(/\s+/g, " ").trim(); const hits = g.ships.filter((r) => String(r[1]).toUpperCase().includes(q)).slice(0, 5); if (!hits.length) { const last = (await kv.get(env, "fleet_last")) || {}; const k = Object.keys(last).find((n) => n.includes(q)); if (k) { const l = last[k]; actions.push({ type: "ship", mmsi: l.row[0], lat: l.row[2], lon: l.row[3] }); return `${k} is not in the live feed (no shore receiver in range: likely at sea). Last heard ${l.seen}: ${l.row[2]}, ${l.row[3]}${l.row[7] ? ", bound for " + l.row[7] : ""}.`; } } if (!hits.length) return "No vessel called " + input.name + " in the feed right now (it covers passenger ships: cruise ships and ferries; coverage depends on AIS receivers near the ship)."; actions.push({ type: "ship", mmsi: hits[0][0], lat: hits[0][2], lon: hits[0][3] }); return JSON.stringify(hits.map((r) => ({ name: r[1], mmsi: r[0], lat: r[2], lon: r[3], heading: r[4], speed_kt: r[5], destination: r[7], length_m: r[8], reported_s_ago: r[9] }))); }
    case "watch_ship": { let list = (await kv.get(env, "ship_watch")) || []; const q = String(input.name || "").trim(); if (input.action === "list") return list.length ? list.map((w) => `${w.name}${w.lastSeen ? " (last seen " + w.lastSeen.slice(0, 16) + ")" : " (not seen yet)"}`).join("; ") : "No ships on watch."; if (input.action === "remove") { list = list.filter((w) => w.name.toUpperCase() !== q.toUpperCase()); await kv.put(env, "ship_watch", list); return "Removed."; } if (!list.some((w) => w.name.toUpperCase() === q.toUpperCase())) list.push({ name: q, added: new Date().toISOString() }); await kv.put(env, "ship_watch", list); await shipWatch(env); return `Watching for ${q}. I'll push and say so when any receiver hears her.`; }
    case "flights_overhead": { const place = await kv.get(env, "place"); const ac = await flightsNear(env, +(place?.lat || 33.15), +(place?.lon || -96.82), input.nm || 25); actions.push({ type: "world" }); return JSON.stringify({ near: place?.name, count: ac.length, aircraft: ac.slice(0, 25) }); }
    case "open_link": { if (!safeHttp(input.url)) return "Only http(s) links can be opened."; actions.push({ type: "open", url: input.url, label: input.label }); return "Opened " + input.label + "."; }
    case "append_note": { const cur = (await kv.get(env, "notes")) || ""; const next = (cur ? cur.replace(/\s+$/, "") + "\n" : "") + "- " + input.text; await kv.put(env, "notes", next); actions.push({ type: "notes", value: next }); return "Added."; }
    case "remember": if (!saidRemember) { actions.push({ type: "confirm", item: { id: uid(), kind: "memory_add", params: { text: input.text }, summary: "Remember: " + String(input.text).slice(0, 160), status: "awaiting confirmation", at: new Date().toISOString() } }); return "Shown to Jesse to confirm before it is stored."; }
      { const mem = (await kv.get(env, "memory")) || []; const m = { id: uid(), text: input.text, at: new Date().toISOString() }; mem.unshift(m); await kv.put(env, "memory", mem.slice(0, 200)); actions.push({ type: "memory", value: mem }); return "Remembered [" + m.id + "]."; }
    case "forget": { const mem = ((await kv.get(env, "memory")) || []).filter((m) => m.id !== input.id); await kv.put(env, "memory", mem); actions.push({ type: "memory", value: mem }); return "Forgotten."; }
    case "add_trip": { const t = await addTrip(env, input); actions.push({ type: "trips" }); return JSON.stringify(t); }
    case "remove_trip": { const trips = ((await kv.get(env, "trips")) || []).filter((t) => t.id !== input.id); await kv.put(env, "trips", trips); actions.push({ type: "trips" }); return "Removed."; }
    case "watch_app": { const list = (await kv.get(env, "apps_watch")) || []; const key = (input.platform + "_" + input.id).toLowerCase(); if (!list.some((a) => a.key === key)) list.push({ key, name: input.name, ...(input.platform === "ios" ? { ios: /^\d+$/.test(input.id) ? { id: input.id } : { bundle: input.id } } : { android: input.id }) }); await kv.put(env, "apps_watch", list); return "Watching " + input.name + ". The first check lands within 15 minutes."; }
    case "set_reminder": { const r = await addReminder(env, input); actions.push({ type: "reminders" }); return r.error ? r.error : `Reminder [${r.id}] set for ${r.local}${r.repeat !== "none" ? ", repeating " + r.repeat : ""}.`; }
    case "cancel_reminder": { await kv.put(env, "reminders", ((await kv.get(env, "reminders")) || []).filter((r) => r.id !== input.id)); actions.push({ type: "reminders" }); return "Cancelled."; }
    case "set_alarm": if (!input.enabled) { actions.push({ type: "confirm", item: { id: uid(), kind: "alarm_off", params: {}, summary: "Turn the wake-up alarm off", status: "awaiting confirmation", at: new Date().toISOString() } }); return "Shown to Jesse to confirm turning the alarm off."; }
    { const tm = String(input.time || "").match(/^(\d{1,2}):(\d{2})$/); if (!tm || +tm[1] > 23 || +tm[2] > 59) return JSON.stringify({ error: "time must be HH:MM 24h" }); const time = tm[1].padStart(2, "0") + ":" + tm[2]; const cur = (await kv.get(env, "alarm")) || {}; const days = input.days === "weekdays" ? [1, 2, 3, 4, 5] : input.days === "weekends" ? [0, 6] : []; const next = alarmToday(env, { ...cur, enabled: !!input.enabled, time, days, at: new Date().toISOString() }); await kv.put(env, "alarm", next); actions.push({ type: "alarm" }); return `Alarm ${next.enabled ? "set for " + next.time + " " + (input.days === "all" ? "every day" : input.days) : "off"}.`; }
    case "watch_competitor": { if (!safeHttp(input.url)) return "Only http(s) pages can be watched."; actions.push({ type: "confirm", item: { id: uid(), kind: "competitor_add", params: { url: input.url, label: input.label, business: input.business }, summary: `Watch ${input.label} (${input.url}) for price changes`, status: "awaiting confirmation", at: new Date().toISOString() } }); return "Shown to Jesse to confirm."; }
    case "watch_competitor_confirmed": { const list = (await kv.get(env, "competitors")) || []; if (!list.some((c) => c.url === input.url)) list.push({ url: input.url, label: input.label, business: input.business, added: new Date().toISOString() }); await kv.put(env, "competitors", list); actions.push({ type: "competitors" }); return "Watching " + input.label + ". First scan Sunday evening, or say 'scan competitors now'."; }
    case "draft_reply": { actions.push({ type: "draft", ...input }); return "Draft shown to Jesse with an Open in Gmail button."; }
    case "request_action": { const KINDS = ACT_KINDS.filter((k) => !LOCAL_KINDS.includes(k)); if (!KINDS.includes(input.kind) || typeof input.params !== "object" || !input.summary) return "Invalid action: kind must be one of " + KINDS.join(", ") + " with params and summary.";
      const item = { id: uid(), kind: input.kind, params: input.params, summary: input.summary, status: "awaiting confirmation", at: new Date().toISOString() }; actions.push({ type: "confirm", item }); return "Queued for confirmation: " + input.summary; }
    default: return "Unknown tool";
  }
}

/* ---------------- streaming chat ---------------- */
export async function chat(request, env, ctx) {
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
      const saidRemember = /\b(remember|note that|from now on|don'?t forget|keep in mind)\b/i.test(String(text || ""));   // only Jesse's own words store a memory directly; anything else goes to a confirm card
      for (let i = 0; i < 4; i++) {
        const stream = client.beta.messages.stream({
          model: (modelPick || env.CHAT_MODEL) === "sonnet" ? "claude-sonnet-5-5" : MODEL, ...((modelPick || env.CHAT_MODEL) === "sonnet" ? { thinking: { type: "between_tools" } } : {}),
          max_tokens: 4000, betas: ["server-side-fallback-2026-07-01"], fallbacks: "default", output_config: { effort: "low" },
          system: [{ type: "text", text: BRAIN_SYSTEM + "\nKnown links: " + JSON.stringify(LINKS), cache_control: { type: "ephemeral" } }, { type: "text", text: "LIVE CONTEXT:\n" + context, cache_control: { type: "ephemeral" } }],
          ...(noTools ? {} : { tools: [...BRAIN_TOOLS, { type: "web_search_20260209", name: "web_search", max_uses: 3 }] }), messages,
        });
        let turnText = "";
        stream.on("text", (d) => { if (timing.firstText == null) timing.firstText = Date.now() - T0; turnText += d; send("delta", { text: d }); });
        const msg = await stream.finalMessage();
        if (turnText.trim()) reply = (reply ? reply + " " : "") + turnText.trim();
        messages.push({ role: "assistant", content: msg.content });
        if (msg.stop_reason === "refusal") { if (!reply) { reply = "I'd rather not answer that one."; await send("delta", { text: reply }); } break; }
        if (msg.stop_reason !== "tool_use") break;
        const results = [];
        if (!msg.content.some((b) => b.type === "tool_use")) break;
        for (const b of msg.content.filter((b) => b.type === "tool_use")) {
          let out; try { out = await runTool(b.name, b.input, env, actions, saidRemember); } catch (e) { out = "Tool failed: " + e.message; }
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
/* ---------------- ElevenLabs ---------------- */
export function elevenlabs(env, text, format = "mp3_44100_128", model = "eleven_turbo_v2_5", settings = {}) {
  const voice = env.ELEVENLABS_VOICE_ID || "JBFqnCBsd6RMkjVDRZzb";
  return fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voice}/stream?output_format=${format}`, {
    method: "POST", headers: { "xi-api-key": env.ELEVENLABS_API_KEY, "content-type": "application/json" },
    body: JSON.stringify({ text: String(text).slice(0, 4800), model_id: model, voice_settings: { stability: 0.6, similarity_boost: 0.8, style: 0.15, use_speaker_boost: true, ...settings } }),
  });
}
export async function tts(request, env) {
  if (!env.ELEVENLABS_API_KEY) return json({ error: "tts not configured" }, 501);
  const text = request.method === "GET" ? new URL(request.url).searchParams.get("t") || "" : (await request.json()).text;
  const r = await elevenlabs(env, text, "mp3_44100_128", "eleven_flash_v2_5");
  if (!r.ok) return json({ error: "tts failed", status: r.status }, 502);
  return new Response(r.body, { headers: { "content-type": "audio/mpeg", "cache-control": "no-store" } });
}
