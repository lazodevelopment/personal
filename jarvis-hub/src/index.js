// JARVIS hub worker.
// Dashboard + API: Google sign-in (one allowed email) or access key, site checks, weather/radar/alerts,
// a streaming Claude "brain" with pre-loaded context and confirm-first actions, ElevenLabs voice,
// morning brief, memory, calendar (private ICS), watchfulness (anomalies), and push via Pushover.
import Anthropic from "@anthropic-ai/sdk";
import html from "./hub.html";
import manifest from "./manifest.json";
import icon192 from "./icon-192.png";
import baroqueMp3 from "../sounds/baroque.mp3";   // the wake-up clip (Vivaldi, Spring); the open page rings with it, Pushover plays its own uploaded copy
import { vapidKeys, listSubs, saveSub, dropSub, webPush, SW_JS } from "./webpush.js";

export const SITES = [
  { id: "atavia", name: "Atavia Weddings", url: "https://ataviaweddings.com" },
  { id: "es", name: "Elizabeth Scott", url: "https://elizabethscottweddings.com" },
  { id: "lazo", name: "Lazo", url: "https://meetlazo.com" },
  { id: "roven", name: "Roven HR", url: "https://rovenhr.com" },
  { id: "lr", name: "LeaseReputation", url: "https://leasereputation.com" },
];
const BIZ_NAME = Object.fromEntries(SITES.map((s) => [s.id, s.name]));
const STATE_KEYS = ["brief", "webcams", "notes", "place", "metrics", "alerts", "memory", "queue", "calendar", "morning", "traffic", "tickers", "wxdays", "sports", "briefs", "stale", "inbox", "decisions", "home", "flights", "watch", "followups", "trips", "apps", "playbook", "competitors", "competitor_changes", "reminders", "alarm", "social_log", "ship_watch"];
const UA = "jarvis-hub (jesse@briskhealth.com)";
const BUILD = (() => { let h = 0; for (let i = 0; i < html.length; i += 7) h = (h * 31 + html.charCodeAt(i)) >>> 0; return h.toString(36) + "-" + html.length.toString(36); })();   // changes with every deploy of the page
const MODEL = "claude-opus-5-5";
const HUB_ORIGIN = "https://jarvis-hub.floral-credit-e4f0.workers.dev";

/* ---------------- helpers ---------------- */
const json = (data, status = 200, extra = {}) =>
  new Response(JSON.stringify(data), { status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", ...extra } });
const cookies = (req) => Object.fromEntries((req.headers.get("cookie") || "").split(/;\s*/).filter(Boolean).map((c) => { const i = c.indexOf("="); return [c.slice(0, i), c.slice(i + 1)]; }));
const kv = { get: (env, k) => env.HUB.get(k, "json"), put: (env, k, v) => env.HUB.put(k, JSON.stringify(v)) };
const localTime = (env, d = new Date(), opts = { dateStyle: "full", timeStyle: "short" }) => d.toLocaleString("en-US", { timeZone: env.TZ || "America/Chicago", ...opts });
const localHour = (env) => +new Date().toLocaleString("en-US", { timeZone: env.TZ || "America/Chicago", hour: "numeric", hourCycle: "h23" });
const uid = () => Math.random().toString(36).slice(2, 10);

/* ---------------- cruise fleets tracked by name (AIS ship names are upper case, 20 chars max) ---------------- */
const FLEETS = { ncl: { name: "Norwegian Cruise Line", ships: ["NORWEGIAN AQUA", "NORWEGIAN VIVA", "NORWEGIAN PRIMA", "NORWEGIAN LUNA", "NORWEGIAN ENCORE", "NORWEGIAN BLISS", "NORWEGIAN JOY", "NORWEGIAN ESCAPE", "NORWEGIAN GETAWAY", "NORWEGIAN BREAKAWAY", "NORWEGIAN EPIC", "NORWEGIAN GEM", "NORWEGIAN JADE", "NORWEGIAN PEARL", "NORWEGIAN JEWEL", "NORWEGIAN DAWN", "NORWEGIAN STAR", "NORWEGIAN SUN", "NORWEGIAN SKY", "NORWEGIAN SPIRIT", "PRIDE OF AMERICA"] } };
const shipKey = (n) => String(n || "").toUpperCase().replace(/[^A-Z0-9 ]/g, "").replace(/\s+/g, " ").trim();
function fleetOf(name) { const k = shipKey(name); for (const [id, f] of Object.entries(FLEETS)) if (f.ships.includes(k)) return id; return null; }
// every feed snapshot refreshes KV fleet_last, so a fleet ship keeps her last known position after the feeder drops her (3 h without a shore receiver: mid-ocean legs)
async function fleetRemember(env, snap) {
  const last = (await kv.get(env, "fleet_last")) || {}; let changed = false; const at = snap.at ? new Date(snap.at).getTime() : Date.now();
  for (const r of snap.ships || []) { const id = fleetOf(r[1]); if (!id) continue; const k = shipKey(r[1]); const seen = new Date(at - (r[9] || 0) * 1000).toISOString(); if (last[k]?.seen === seen) continue; last[k] = { fleet: id, row: r.slice(0, 9), seen }; changed = true; }
  if (changed) await kv.put(env, "fleet_last", last);
  return last;
}
async function fleetStatus(env, id = "ncl") {
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

const isBot = (addr) => /no-?reply|donotreply|do-not-reply|notifications?@|mailer-daemon|postmaster|alerts?@/i.test(String(addr || ""));

// Zola and The Knot inquiry notices for the film brands are answered by the Gmail intake script (Apps Script in that
// account, 5-minute trigger: atavia-functions-live/gmail-intake, es-site/_src/gmail-intake). JARVIS never drafts a
// reply to those notices; instead it checks that the script's first reply went out (verifyIntake).
const MARKET_FROM = /zola\.com|theknot\.com|weddingpro\.com/i;
const INTAKE = { atavia: { synced: "atavia-synced", review: "atavia-needs-review" }, es: { synced: "esw-synced", review: "esw-needs-review" } };
// true for a first-contact notice the script answers; false for a couple's follow-up, which is a real conversation JARVIS should flag
function marketLead(m, business) {
  if (!INTAKE[business] || !MARKET_FROM.test(m.fromEmail || "")) return false;
  const s = String(m.subject || "");
  if (/zola\.com/i.test(m.fromEmail)) return /new zola inquiry/i.test(s);   // Zola: only the inquiry notice; "New message from…" is a conversation
  // The Knot / WeddingPro: the first message in the thread (or one we already answered on the thread)
  return /sent you a new message|sent you an inquiry|wants to learn more|new (?:message|inquiry|lead) from|new lead/i.test(s) && (m.count || 1) === 1;
}
// a plain summary for an inquiry notice, from the "<names> sent you an inquiry!" line, so triage can't call it a reminder
function leadSummary(m) {
  const who = (String(m.snippet || "").match(/([^.!?]{3,80}?) sent you an inquiry/i) || [])[1]?.trim();
  return who ? { summary: `New ${/zola\.com/i.test(m.fromEmail) ? "Zola" : "The Knot"} inquiry from ${who}; the intake script sends the first reply` } : {};
}
const coupleEmail = (body) => (String(body || "").match(/(?:Personal email|Couple email):\s*\n?\s*([^\s@<>"']+@[^\s@<>"']+\.[a-z]{2,})/i) || [])[1]?.toLowerCase() || null;

// The intake scripts (Combined-zola.gs, Combined-info.gs, es Code.gs) report every inquiry they handle straight to
// POST /api/intake: {business, account, threadId, messageId, date, state, detail, couple, name, subject, source}.
// That is the authoritative answer; verifyIntake below only has to guess (labels, Sent) for scripts that don't report.
const INTAKE_STATES = { replied: ["replied", ""], duplicate: ["replied", "this couple was answered earlier; no second reply"], manual: ["missing", "AUTO_REPLY is switched off in the script, so nobody replied"], reply_failed: ["missing", "the auto-reply threw an error"], webhook_failed: ["missing", "the site webhook rejected the lead, so no code and no reply"], no_email: ["review", "no couple email in the notice"] };
async function intakeReport(env, b) {
  const business = String(b.business || "").toLowerCase(); if (!INTAKE[business]) return { error: "unknown business" };
  if (!b.threadId || !b.date || !INTAKE_STATES[b.state]) return { error: "need threadId, date and a known state" };
  const [state, fallback] = INTAKE_STATES[b.state]; const detail = `${state === "replied" ? "the intake script reported the reply" : "the intake script reported: " + b.state.replace("_", " ")}${b.detail ? " — " + String(b.detail).slice(0, 200) : fallback ? " — " + fallback : ""}`;
  const log = (await kv.get(env, "intake_log")) || {}; const key = b.threadId + "|" + b.date;
  const who = [b.name, b.couple].filter(Boolean).join(" ") || b.subject || "";
  log[key] = { state, detail, business, account: String(b.account || "").toLowerCase(), threadId: b.threadId, messageId: b.messageId || "", subject: b.subject || "", date: b.date, who, source: b.source || "", script: true, at: new Date().toISOString() };
  for (const k of Object.keys(log)) if (Date.now() - new Date(log[k].date) > 14 * 86400e3) delete log[k];
  await kv.put(env, "intake_log", log);
  if (state !== "replied") {
    const biz = BIZ_NAME[business] || business;
    await flushAlerts(env, [{ alert: { kind: "failed", text: `${biz} intake: ${state === "review" ? "needs review" : "no automatic reply"} for ${who} (${b.subject || b.source || "inquiry"}): ${detail}. Check Apps Script executions in ${b.account || "that account"}.` },
      push: { title: `${biz}: lead not auto-replied`, body: `${who}\n${b.subject || ""}\n${detail}`, opts: { priority: "high", tags: "warning" } } }]);
  }
  return { ok: true, state };
}

// Did the intake script answer each marketplace inquiry? The script labels the thread <synced> once the webhook took
// the lead and sends the reply (to the couple's own address for Zola, on the thread for a Knot relay), or labels it
// <review> when it could not parse the notice. Zola threads every notice under one subject, so the label alone is
// weak there: when the bridge can search Sent (find_sent, bridge v3.1+) we look for a message to the couple's address.
async function verifyIntake(env, account, business, items) {
  const cfg = INTAKE[business]; if (!cfg) return;
  const log = (await kv.get(env, "intake_log")) || {}; const out = []; let dirty = false; const touched = new Set();
  const has = (m, name) => (m.labels || []).includes(name);
  for (const m of items.filter((m) => marketLead(m, business))) {
    const key = m.threadId + "|" + m.date; const cur = log[key]; const ageMin = (Date.now() - new Date(m.date)) / 60e3;
    if (cur && cur.state !== "pending") continue;   // settled; a newer notice in the thread changes m.date and gets its own entry
    if (ageMin > 3 * 1440) continue;
    if (ageMin < 12) { if (!cur) { log[key] = { state: "pending", business, account, threadId: m.threadId, subject: m.subject, date: m.date, who: m.summary || "", at: new Date().toISOString() }; dirty = true; touched.add(key); } continue; }   // the script runs every 5 min; give it two runs
    let state, detail, who = m.summary || m.subject;
    const t = await threadCached(env, account, m.threadId, m.date).catch(() => null);
    const last = t?.messages?.[t.messages.length - 1];
    const couple = coupleEmail(last?.body);
    if (couple) who = couple;
    if (has(m, cfg.review)) { state = "review"; detail = `the intake script could not parse the notice (label ${cfg.review}); fix it in Apps Script and it retries on the next run`; }
    else if (!has(m, cfg.synced)) { state = "missing"; detail = `no ${cfg.synced} label ${Math.round(ageMin)} min after the notice; the script did not pick it up`; }
    else if (couple) {
      const r = await bridgeCall(env, account, { action: "find_sent", to: couple, newerThanDays: 3 });
      if (r.ok && r.found) { state = "replied"; detail = `reply to ${couple} is in Sent (${String(r.date || "").slice(0, 16)})`; }
      else if (r.ok) { state = "missing"; detail = `thread is labelled ${cfg.synced} but nothing to ${couple} is in Sent; the auto-reply failed`; }
      else { state = "replied"; detail = `label ${cfg.synced} (Sent not checked: ${r.error || "bridge"}; update the bridge script for the Sent check)`; }
    }
    else if (t?.messages?.some((x) => String(x.from || "").toLowerCase().includes(account))) { state = "replied"; detail = "our reply is on the thread"; }
    else { state = "replied"; detail = `label ${cfg.synced}`; }
    log[key] = { state, detail: detail + " (inferred; the script did not report)", business, account, threadId: m.threadId, subject: m.subject, date: m.date, who, link: m.link, at: new Date().toISOString() }; dirty = true; touched.add(key);
    if (state !== "replied") {
      const biz = BIZ_NAME[business] || business;
      out.push({ alert: { kind: "failed", text: `${biz} intake: ${state === "review" ? "needs review" : "no automatic reply"} for ${who} (${m.subject}). ${detail}. Check Apps Script executions in ${account}.`, url: m.link },
        push: { title: `${biz}: lead not auto-replied`, body: `${who}\n${m.subject}\n${detail}\nCheck the intake script's executions in ${account}.`, opts: { priority: "high", tags: "warning", url: m.link || "" } } });
    }
  }
  // A notice first seen under 12 min old is parked as "pending" for a later sync to settle, but the sync only carries
  // in:inbox threads keyed by their newest message: once the thread is archived or Zola threads another notice onto it,
  // that key never comes back. Settle those here from the thread itself plus the Sent check, a few per run.
  const orphans = Object.entries(log).filter(([k, e]) => e.state === "pending" && !e.script && e.business === business && e.account === account && !touched.has(k)
    && Date.now() - new Date(e.date) > 12 * 60e3 && Date.now() - new Date(e.date) < 3 * 86400e3).slice(0, 4);
  for (const [key, e] of orphans) {
    const t = await threadCached(env, account, e.threadId, null, true).catch(() => null);
    if (!t?.messages) continue;   // bridge down: try again next sync
    const msg = t.messages.find((x) => x.date === e.date); const couple = coupleEmail(msg?.body);
    let state, detail;
    if (!msg) { state = "gone"; detail = "the notice is no longer in the thread (deleted), so there is nothing to check"; }
    else if (!couple) { state = "review"; detail = "no couple email in the notice"; }
    else {
      const r = await bridgeCall(env, account, { action: "find_sent", to: couple, newerThanDays: 4 });
      if (!r.ok) continue;
      if (r.found && new Date(r.date) >= new Date(e.date)) { state = "replied"; detail = `reply to ${couple} is in Sent (${String(r.date).slice(0, 16)})`; }
      else { state = "missing"; detail = `nothing to ${couple} is in Sent after the notice; the auto-reply failed`; }
    }
    const who = couple || e.who;
    log[key] = { ...e, state, detail: detail + " (inferred; the script did not report)", who, link: e.link || t.link, at: new Date().toISOString() }; dirty = true; touched.add(key);
    if (state === "missing" || state === "review") {
      const biz = BIZ_NAME[business] || business;
      out.push({ alert: { kind: "failed", text: `${biz} intake: ${state === "review" ? "needs review" : "no automatic reply"} for ${who} (${e.subject}). ${detail}. Check Apps Script executions in ${account}.`, url: log[key].link },
        push: { title: `${biz}: lead not auto-replied`, body: `${who}\n${e.subject}\n${detail}\nCheck the intake script's executions in ${account}.`, opts: { priority: "high", tags: "warning", url: log[key].link || "" } } });
    }
  }
  if (dirty) {
    // the intake script may have reported (POST /api/intake) while we were guessing: re-read and never overwrite an entry it settled
    const latest = (await kv.get(env, "intake_log")) || {};
    for (const k of touched) { const cur = latest[k]; if (!cur || (cur.state === "pending" && !cur.script)) latest[k] = log[k]; }
    for (const k of Object.keys(latest)) if (Date.now() - new Date(latest[k].date) > 14 * 86400e3) delete latest[k];
    await kv.put(env, "intake_log", latest);
  }
  await flushAlerts(env, out);
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
        const bot = isBot(m.fromEmail || m.from); // an automated notice (missed call, form): name what it is about, not the no-reply address
        await pushAlert(env, { kind: "lead", text: `Waiting ${Math.round(age / 3600e3)}h: ${bot ? (m.snippet || m.subject) : m.from + " — " + m.subject}`, url: m.url });
        await notify(env, bot ? "Lead waiting on you" : "Reply waiting on you", `${bot ? m.subject : m.from + ": " + m.subject}\n${m.snippet || ""}`, { priority: "high", tags: "envelope", url: m.url });
      }
    }
    if (changed) await kv.put(env, "nudged", seen);
  }
  // approved actions the PC executor hasn't picked up: it isn't running
  const q = (await kv.get(env, "queue")) || []; const once = await onceStore(env);
  for (const x of q.filter((x) => x.status === "pending" && Date.now() - new Date(x.confirmedAt || x.at) > 10 * 60e3)) {
    if (!once.fresh("stuck:" + x.id, 7 * 86400e3)) continue;
    await pushAlert(env, { kind: "failed", text: `Approved but not done yet: ${x.summary}. The JARVIS hands script on the PC isn't picking up actions.` });
    await notify(env, "Approved action is stuck", `${x.summary}\nThe JARVIS hands script on the PC isn't running. It starts at sign-in; double-click jarvis_hands.bat to start it now.`, { priority: "high", tags: "warning" });
  }
  await once.save();
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
  // Lazo sign-up health (collector counts): a stall against the 7-day average, couples without users docs (the rules break of Sep 29 2026), and recovery
  const lz = next.businesses?.lazo?.counts, lzp = prev.businesses?.lazo?.counts || {};
  // stalled = quiet for 3x the typical gap between sign-ups (never under 48 h), so the rule scales with volume: at one sign-up every two days that is six days, at ten a day it is seven hours
  const stalled = (c) => typeof c?.hours_since_signup === "number" && c.signup_gap_hours && c.hours_since_signup >= Math.max(48, 3 * c.signup_gap_hours);
  if (lz) {
    if (stalled(lz)) notes.push(`Lazo: no new user sign-ups for ${Math.round(lz.hours_since_signup / 24)} days (lately one every ${lz.signup_gap_hours < 48 ? Math.round(lz.signup_gap_hours) + " hours" : Math.round(lz.signup_gap_hours / 24) + " days"}). Check the app's sign-up flow and the Firestore users rule.`);
    else if (stalled(lzp)) notes.push(`Lazo: sign-ups resumed (${lz.users_24h} in the last 24 hours)`);
    if ((lz.couples_24h || 0) >= 2 && !lz.users_24h) notes.push(`Lazo: ${lz.couples_24h} couples signed up in the last 24 hours but no users docs were written. The users create rule is probably broken again.`);
  }
  const seen = (await kv.get(env, "watch_seen")) || {};
  for (const n of notes) {
    const signup = /sign-ups|users docs/.test(n);
    const key = n.replace(/\d+(\.\d+)?/g, "#"); if (seen[key] && Date.now() - seen[key] < (signup ? 20 : 6) * 3600e3) continue;
    seen[key] = Date.now();
    await pushAlert(env, { kind: signup && !/resumed/.test(n) ? "failed" : "watch", text: n });
    await notify(env, signup ? "Lazo sign-ups" : "JARVIS noticed", n, signup && !/resumed/.test(n) ? { priority: "high", tags: "rotating_light" } : { tags: "eyes" });
  }
  await kv.put(env, "watch_seen", seen);
}

// new items waiting on Jesse (Lazo claims, Roven reviews): push once per item
async function watchDecisions(env, dec) {
  const seen = (await kv.get(env, "decisions_seen")) || {}; const now = Date.now(); let changed = false;
  for (const it of dec.items || []) {
    if (seen[it.id]) continue; seen[it.id] = now; changed = true;
    const title = it.kind === "lazo_claim" ? "Lazo claim to review" : it.kind === "roven_approve_job" ? "Roven job to review" : "Roven employer to review";
    const label = String(it.label || "").replace(/^[^:]+:\s*/, "");
    await pushAlert(env, { kind: "watch", text: `${title}: ${label}` });
    await notify(env, title, label + "\nOpen JARVIS → Decisions to approve or reject.", { priority: "high", tags: "ballot_box_with_check", url: HUB_ORIGIN + "/#decisions" });
  }
  for (const id of Object.keys(seen)) if (now - seen[id] > 30 * 86400e3) { delete seen[id]; changed = true; }
  if (changed) await kv.put(env, "decisions_seen", seen);
}

/* ---------------- notifications ---------------- */
const PUSHOVER_BUILTIN = ["pushover","bike","bugle","cashregister","classical","cosmic","falling","gamelan","incoming","intermission","magic","mechanical","pianobar","siren","spacealarm","tugboat","alien","climb","persistent","echo","updown","vibrate","none"];
async function notify(env, title, body, { priority = "default", tags = "", url = "", sound = "" } = {}) {
  const out = [];
  if (env.PUSHOVER_TOKEN && env.PUSHOVER_USER) {
    const pr = priority === "alarm" ? "2" : priority === "urgent" || priority === "reminder" ? "1" : priority === "high" ? "0" : "-1";
    // the alarm plays a custom Pushover sound ("baroque" first, else any uploaded one; his is named "Alarm") (Vivaldi clip, jarvis-hub/sounds/baroque.mp3) once it's uploaded to Pushover; spacealarm until then
    let alarmSound = "spacealarm";
    if (priority === "alarm" && !sound) { try { const s = await (await fetch("https://api.pushover.net/1/sounds.json?token=" + env.PUSHOVER_TOKEN)).json(); alarmSound = s?.sounds?.baroque ? "baroque" : Object.keys(s?.sounds || {}).find((k) => !PUSHOVER_BUILTIN.includes(k)) || alarmSound; } catch {} }
    const form = new URLSearchParams({ token: env.PUSHOVER_TOKEN, user: env.PUSHOVER_USER, title: "JARVIS: " + title, message: body, priority: pr, sound: sound || (priority === "alarm" ? alarmSound :priority === "reminder" ? "incoming" : priority === "urgent" ? "siren" : "pushover"), ...(priority === "alarm" ? { retry: "60", expire: "1800" } : {}), ...(url ? { url, url_title: "Open JARVIS" } : {}) });
    out.push(fetch("https://api.pushover.net/1/messages.json", { method: "POST", body: form }).then(async (r) => { const t = await r.text(); let j = null; try { j = JSON.parse(t); } catch {} return { pushover: r.status, receipt: j?.receipt, sound: form.get("sound"), detail: r.ok ? undefined : t.slice(0, 200) }; }).catch((e) => ({ pushover: "error", detail: String(e.message || e) })));
  }
  if (env.NTFY_TOPIC) {
    out.push(fetch("https://ntfy.sh/" + env.NTFY_TOPIC, { method: "POST", body, headers: { "user-agent": UA, Title: title, Priority: priority, ...(tags ? { Tags: tags } : {}), ...(url ? { Click: url } : {}) } }).then((r) => ({ ntfy: r.status })).catch((e) => ({ ntfy: "error", detail: String(e.message || e) })));
  }
  // the phone's own browser (Chrome on Android, etc.) once it has subscribed on the Radio panel: alarms, reminders and anything urgent/high
  // alarms go through Pushover alone when it's configured: the Chrome notification's beep competed with the Vivaldi alarm sound (2026-10-09)
  if (["reminder", "urgent", "high"].includes(priority) || (priority === "alarm" && !(env.PUSHOVER_TOKEN && env.PUSHOVER_USER))) {
    out.push(webPush(env, { title: "JARVIS: " + title, body, url, priority, kind: priority === "alarm" ? "alarm" : "", tag: priority === "alarm" ? "alarm" : "", at: new Date().toISOString() }, { ttl: priority === "alarm" ? 1800 : 3600, urgency: "high", topic: priority === "alarm" ? "alarm" : "" }).then((r) => ({ webpush: r })).catch((e) => ({ webpush: "error", detail: String(e.message || e) })));
  }
  if (env.RESEND_API_KEY && env.ALERT_EMAIL) {
    out.push(fetch("https://api.resend.com/emails", { method: "POST", headers: { authorization: "Bearer " + env.RESEND_API_KEY, "content-type": "application/json" },
      body: JSON.stringify({ from: env.ALERT_FROM || "JARVIS <onboarding@resend.dev>", to: [env.ALERT_EMAIL], subject: "JARVIS: " + title, text: body + (url ? "\n\n" + url : "") }) }).then((r) => ({ email: r.status })).catch((e) => ({ email: "error", detail: String(e.message || e) })));
  }
  const res = await Promise.all(out);
  // keep the last 40 answers so "did the alarm actually go out?" has an answer (/api/push/log, Radio panel)
  try { const log = (await kv.get(env, "push_log")) || []; log.unshift({ at: new Date().toISOString(), title, priority, res }); await kv.put(env, "push_log", log.slice(0, 40)); } catch {}
  if (priority === "alarm") { try { const po = res.find((r) => r.pushover != null); if (po?.receipt) { const al = (await kv.get(env, "alarm")) || {}; al.receipt = po.receipt; await kv.put(env, "alarm", al); } } catch {} }
  return res;
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

const INDEXES = [["^GSPC", "S&P 500"], ["^DJI", "Dow"], ["^IXIC", "Nasdaq"], ["CL=F", "Oil (WTI)"], ["BTC-USD", "Bitcoin"]];   // oil is the front-month WTI future in $/barrel; bitcoin in USD
async function markets(env) {
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
async function radioNow(u) {
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
async function wxRadio(request, env, lat, lon) {
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

async function audacyNow(id) {
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
const marketsSummary = (mk) => (mk?.rows || []).filter((r) => !r.error && Number.isFinite(r.price)).map((r) => `${r.name} ${r.price >= 1000 ? Math.round(r.price).toLocaleString() : r.price.toFixed(2)} (${r.pct >= 0 ? "+" : ""}${r.pct.toFixed(2)}%)`).join(", ") || "unavailable";

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
    system: "You triage a small business owner's inbox (wedding films, a wedding-planner app, a hiring platform, apartment reviews). For each numbered thread return JSON only: an array of objects {\"n\": number, \"needs_reply\": boolean, \"summary\": string (max 110 chars, plain, what it is or asks), \"priority\": 1|2|3, \"kind\": \"lead\"|\"client\"|\"booking\"|\"payment\"|\"vendor\"|\"notification\"|\"newsletter\"|\"other\"}. needs_reply is true only when a real person is asking the business something and the last message is not from us. priority 1 = money or a client waiting, 2 = worth reading today, 3 = noise. A Zola email titled 'New Zola inquiry' is a NEW couple inquiry even though it opens with 'The clock is ticking!'; never call it a reminder: summarize it as 'New Zola inquiry from <couple names>'.",
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
  // marketplace inquiry notices (Zola, The Knot) are answered by the intake script: never NEEDS REPLY, flagged `intake` instead
  inbox.accounts[account] = { business: body.business || "other", at: new Date().toISOString(), items: items.map((m) => ({ ...m, ...(keep[m.threadId] ? { needs_reply: keep[m.threadId].needs_reply && !m.lastFromMe, summary: keep[m.threadId].summary, priority: keep[m.threadId].priority, kind: keep[m.threadId].kind } : {}), ...(marketLead(m, body.business) ? { needs_reply: false, kind: "lead", intake: true, ...leadSummary(m) } : {}) })) };
  await kv.put(env, "inbox", inbox);
  const once = await onceStore(env);
  for (const m of fresh) {
    if (!/apple\.com|googleplay|play-console|google-play|android-developer/i.test(m.fromEmail || "") || !/review|submission|rejected|approved|ready for|status|policy|removed|suspend/i.test(m.subject || "")) continue;
    if (!once.fresh("store_mail:" + m.threadId + ":" + m.date, 30 * 86400e3)) continue;
    await pushAlert(env, { kind: "watch", text: `App store: ${m.subject}`, url: m.link });
    await notify(env, "App store update", `${m.subject}\n${(m.snippet || "").slice(0, 200)}`, { priority: "high", tags: "iphone", url: m.link });
  }
  await once.save();
  if (body.secret) {
    // Apps Script reports its signed-in test URL (/a/<domain>/macros/...); only a public /macros/s/.../exec deployment URL works for the hub.
    const hooks = (await kv.get(env, "inbox_hooks")) || {}; const cur = hooks[account] || {};
    const reported = /^https:\/\/script\.google\.com\/macros\/s\/[^/]+\/exec$/.test(body.hookUrl || "") ? body.hookUrl : null;
    hooks[account] = { ...cur, url: cur.pinned ? cur.url : (reported || cur.url || null), secret: body.secret, business: body.business || "other", at: new Date().toISOString() };
    await kv.put(env, "inbox_hooks", hooks);
  }
  // the Inbox panel, the nudges and the briefs all read `brief`; rebuild it from every bridged account
  const all = Object.entries(inbox.accounts).flatMap(([acct, a]) => a.items.map((m) => ({ business: a.business, account: acct, threadId: m.threadId, from: m.from.replace(/<.*>/, "").trim() || m.fromEmail, fromEmail: m.fromEmail || "", when: new Date(m.date).toLocaleString("en-US", { timeZone: env.TZ || "America/Chicago", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }), received: m.date, subject: m.subject, snippet: m.summary || m.snippet?.slice(0, 120) || "", url: m.link, needs_reply: !!m.needs_reply, unread: !!m.unread, priority: m.priority || 3, kind: m.kind || "", intake: !!m.intake })));
  all.sort((a, b) => (b.needs_reply - a.needs_reply) || (a.priority - b.priority) || b.received.localeCompare(a.received));
  const needs = all.filter((m) => m.needs_reply).length, unread = all.filter((m) => m.unread).length;
  await kv.put(env, "brief", { at: new Date().toISOString(), source: "bridge", accounts: Object.keys(inbox.accounts), note: all.length ? `${unread} unread across ${Object.keys(inbox.accounts).length} inbox${Object.keys(inbox.accounts).length > 1 ? "es" : ""}, ${needs} need${needs === 1 ? "s" : ""} a reply` : "All inboxes clear.", items: all.slice(0, 40) });
  // announce new mail from real people that matters (leads, clients, bookings, payments): push now, and any open page says it
  try {
    const told = (await kv.get(env, "mail_told")) || {}; const outM = []; const bizName = BIZ_NAME[body.business] || BIZ_LABEL[body.business] || body.business || "";
    for (const m of fresh) { const c = keep[m.threadId]; const key = m.threadId + "|" + m.date;
      if (!c || told[key] || m.lastFromMe || isBot(m.fromEmail) || !["lead", "client", "booking", "payment"].includes(c.kind) || (c.priority || 3) > 2 || Date.now() - new Date(m.date) > 3 * 3600e3) continue;
      told[key] = Date.now(); const who = String(m.from || "").replace(/<.*>/, "").trim() || m.fromEmail; const auto = marketLead(m, body.business);
      outM.push({ alert: { kind: "mail", text: `New ${c.kind === "lead" ? "lead" : "email"} for ${bizName} from ${who}: ${m.subject}. ${c.summary || ""}${auto ? " The intake script answers this one; I will confirm the reply went out." : ""}`.trim(), url: m.link }, push: { title: `${bizName}: new ${c.kind}`, body: `${who}: ${m.subject}
${c.summary || m.snippet || ""}`, opts: { priority: c.priority === 1 ? "high" : "default", tags: "email", url: HUB_ORIGIN + "/#mail" } } });
    }
    for (const k of Object.keys(told)) if (Date.now() - told[k] > 7 * 86400e3) delete told[k];
    if (outM.length) { await kv.put(env, "mail_told", told); await flushAlerts(env, outM); }
  } catch (e) { console.log("mail announce", e.message); }
  const quick = fresh.filter((m) => { const c = keep[m.threadId]; return c?.needs_reply && !m.lastFromMe && ["lead", "client", "booking"].includes(c.kind) && !isBot(m.fromEmail) && !marketLead(m, body.business) && Date.now() - new Date(m.date) < 6 * 3600e3; }).map((m) => m.threadId);
  if (quick.length && ctx) ctx.waitUntil(makeFollowups(env, { minAgeH: 0, onlyThreads: quick, first: true }).catch((e) => console.log("first reply", e.message)));
  if (ctx) ctx.waitUntil(prefetchThreads(env, account, inbox.accounts[account].items).catch((e) => console.log("prefetch", e.message)));
  if (ctx && INTAKE[body.business]) ctx.waitUntil(verifyIntake(env, account, body.business, inbox.accounts[account].items).catch((e) => console.log("intake", e.message)));
  return json({ ok: true, account, items: items.length, triaged: fresh.length, hook: !!body.hookUrl, drafting: quick.length });
}

async function bridgeCall(env, account, payload) {
  const hooks = (await kv.get(env, "inbox_hooks")) || {};
  const hook = hooks[String(account || "").toLowerCase()];
  if (!hook?.url) return { error: "no Gmail bridge with actions for " + account };
  let out;
  for (let attempt = 0; attempt < 3; attempt++) {
    if (attempt) await new Promise((r) => setTimeout(r, 1200 * attempt));
    try { const r = await fetch(hook.url, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ secret: hook.secret, ...payload }), redirect: "follow" }); const t = await r.text(); try { out = JSON.parse(t); } catch { out = { error: "bridge returned " + r.status + (t.includes("<") ? " (update the bridge script and deploy a new version)" : ""), transient: true }; } } catch (e) { out = { error: "bridge unreachable: " + e.message, transient: true }; }
    if (!out.transient) break;
  }
  delete out.transient;
  if (out.error && !/thread not found|unknown action/i.test(out.error)) await healthNote(env, "bridge", { account: String(account || "").toLowerCase(), error: String(out.error).slice(0, 120) });   // "unknown action" = an older bridge script, not an outage
  return out;
}

// which Gmail bridge should carry this action: the exact address, else the inbox that holds the thread, else the business by id or name
async function resolveHook(env, p) {
  const hooks = (await kv.get(env, "inbox_hooks")) || {}; const want = String(p.account || "").toLowerCase().trim();
  if (hooks[want]?.url) return hooks[want];
  if (p.threadId) { const inbox = (await kv.get(env, "inbox")) || { accounts: {} }; const acct = Object.entries(inbox.accounts).find(([, a]) => (a.items || []).some((m) => m.threadId === p.threadId))?.[0]; if (acct && hooks[acct]?.url) return hooks[acct]; }
  const bizId = Object.entries(BIZ_LABEL).find(([id, name]) => [id, name.toLowerCase(), (BIZ_NAME[id] || "").toLowerCase()].includes(want) || [id, name.toLowerCase()].includes(String(p.business || "").toLowerCase()))?.[0];
  const byBiz = Object.values(hooks).find((h) => h.url && h.business === (bizId || p.business));
  if (byBiz) return byBiz;
  const partial = Object.entries(hooks).find(([a, h]) => h.url && want && (a.includes(want) || want.includes(a.split("@")[1] || "~")));
  return partial ? partial[1] : null;
}
async function threadCached(env, account, threadId, date, fresh = false) {
  const key = "thread_" + threadId; const c = fresh ? null : await kv.get(env, key);
  if (c && (!date || c.date === date) && c.data?.messages) return { ...c.data, cached: true };
  const r = await bridgeCall(env, account, { action: "get", threadId });
  if (r.error === "unknown action") r.error = "This inbox's bridge script is the older version. Paste the updated script and deploy a new version to read full emails.";
  if (!r.error && r.messages) await env.HUB.put(key, JSON.stringify({ date: date || r.messages[r.messages.length - 1]?.date || "", data: r, at: Date.now() }), { expirationTtl: 3 * 86400 });
  return r;
}
async function prefetchThreads(env, account, items) {
  const want = items.filter((m) => m.needs_reply || m.unread || m.priority === 1).slice(0, 4);   // a few Gmail reads per sync, never a flood
  const cache = await Promise.all(want.map((m) => kv.get(env, "thread_" + m.threadId)));
  const todo = want.filter((m, i) => !(cache[i]?.date === m.date && cache[i]?.data?.messages));
  await Promise.allSettled(todo.map((m) => threadCached(env, account, m.threadId, m.date)));
  return todo.length;
}
async function emailAction(env, item) {
  const p = item.params || {}; const hook = await resolveHook(env, p);
  if (!hook?.url) { const have = Object.keys((await kv.get(env, "inbox_hooks")) || {}); return { ok: false, message: `no Gmail bridge for ${p.account || p.business || "that account"}; connected inboxes: ${have.join(", ") || "none"}. Connect the others with the scripts in secrets/bridges.` }; }
  const action = item.kind.replace("email_", ""); if (p.threadId) try { await env.HUB.delete("thread_" + p.threadId); } catch {}
  // attachments ride along as base64 {name, type, data}; the bridge turns them into Gmail blobs (bridge v3.2+)
  const attachments = (Array.isArray(p.attachments) ? p.attachments : []).filter((a) => a && typeof a.data === "string" && a.data.length).slice(0, 10).map((a) => ({ name: String(a.name || "attachment").slice(0, 120), type: String(a.type || "application/octet-stream").slice(0, 80), data: a.data }));
  const bytes = attachments.reduce((n, a) => n + a.data.length * 0.75, 0);
  if (bytes > 22 * 1048576) return { ok: false, message: `attachments total ${(bytes / 1048576).toFixed(1)} MB; Gmail's limit is 25 MB` };
  let j = {}, status = 0;
  const sends = action === "reply" || action === "send";   // not idempotent: Apps Script may have sent the mail and then answered with an HTML/404 page, so one attempt only
  for (let attempt = 0; attempt < (sends ? 1 : 3); attempt++) {
    if (attempt) await new Promise((r) => setTimeout(r, 1500 * attempt));
    try { const r = await fetch(hook.url, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ secret: hook.secret, action, threadId: p.threadId, body: p.body, to: p.to, subject: p.subject, ...(attachments.length ? { attachments } : {}) }), redirect: "follow" }); status = r.status; const txt = await r.text(); j = {}; try { j = JSON.parse(txt); } catch {} } catch (e) { j = { error: "bridge unreachable: " + e.message }; }
    if (j.ok || (j.error && !/^bridge /.test(j.error))) break;   // a real answer (success or a script-level error) ends the retries; 404/HTML pages do not
    if (!j.error) j = { error: "bridge " + status };
  }
  if (j.error) await healthNote(env, "bridge", { account: hook.url.slice(-24), error: String(j.error).slice(0, 120) });
  if (sends && !j.ok && /^bridge /.test(j.error || "")) return { ok: false, message: "bridge did not confirm the send; check the Sent folder before retrying" };
  return j.ok ? { ok: true, message: j.did || action } : { ok: false, message: j.error || ("bridge " + status) };
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

const BRAIN_SYSTEM = `You are JARVIS, the personal operations assistant for Jesse Clark, who runs five businesses:
Atavia Weddings and Elizabeth Scott Weddings (wedding films), Lazo (wedding planner app + vendor directory), Roven HR (hiring platform), LeaseReputation (apartment reviews).
Persona: calm, dry, precise, British; a trusted chief of staff. Address him sparingly, alternating between "sir" and "Mr. Clark" (never both in one reply; vary from one reply to the next, "Mr. Clark" for greetings and anything formal, "sir" in passing).
Your replies are spoken aloud through text-to-speech: plain prose, no markdown, no lists, no headers, no URLs read aloud. Two to four sentences unless he asks for detail. Lead with the answer. Round numbers sensibly.
Everything about his businesses is in the LIVE CONTEXT; answer from it directly and do not invent figures. For anything outside it (news, facts, prices, places, people, how-to questions, "look up", "search") use the web_search tool, then answer in two to four spoken sentences and name the source in words (no URLs). If something isn't in the context and can't be searched, say so.
Ships: find_ship for "where is the <ship name>" (cruise ships and ferries, from AIS); watch_ship for "tell me when the <ship> shows up"; fleet_status for "where are the Norwegian ships" (the whole Norwegian Cruise Line fleet, live or last known; the World panel lists it too). Coverage is from shore receivers, so mid-ocean and some islands (Bermuda) are blind spots; say so when a ship is not found.
Flights: use track_flight for any question about where a flight is (convert "American 2612" to "AA 2612"), and flights_overhead for "what's flying over me". Say where it is flying from and to (route.from / route.to cities) when known. Report altitude in feet, speed in mph (knots x 1.15) and roughly where it is relative to cities; if not found yet, say you've started tracking it and it will appear on the World globe within a minute if it's airborne.
Actions: open_link opens pages; append_note for the notes board; remember/forget for durable facts about Jesse, his clients or preferences (use remember whenever he says "remember", "note that", "from now on"); draft_reply writes an email reply (shown with an Open-in-Gmail button, nothing is sent); request_action for anything that changes business data (approve a Roven job or employer, approve or reject a Lazo vendor claim, add a booking note, mark a Lazo inquiry responded) AND for email: email_reply (params.account = the exact Gmail address shown in the INBOX line brackets for that thread, e.g. info@ataviaweddings.com, never a business name; params.threadId; params.body: the full reply text you wrote, signed appropriately for that business), email_archive, email_read, email_send (params.account, params.to, params.subject, params.body). When he asks you to reply to an email, write the reply yourself in his voice (warm, brief, professional) and submit it as email_reply; he confirms before anything is sent. request_action only queues it for his confirmation; say it is ready for his confirmation. Never claim an action is done until RECENT ACTIONS shows it done. Use the ids shown in brackets in the context.
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
  { name: "request_action", description: "Queue a business-data change for Jesse's confirmation. kinds: roven_approve_job (params.jobId), roven_reject_job (params.jobId), roven_approve_employer (params.employerId), lazo_claim (params.claimId, params.decision 'approved'|'rejected'), booking_note (params.business 'atavia'|'es', params.bookingId, params.note), lazo_inquiry_responded (params.inquiryId), email_reply (params.account, params.threadId, params.body), email_archive (params.account, params.threadId), email_read (params.account, params.threadId), email_send (params.account, params.to, params.subject, params.body).", input_schema: { type: "object", properties: { kind: { type: "string", enum: ["roven_approve_job", "roven_reject_job", "roven_approve_employer", "lazo_claim", "booking_note", "lazo_inquiry_responded", "email_reply", "email_archive", "email_read", "email_send"] }, params: { type: "object", properties: { jobId: { type: "string" }, employerId: { type: "string" }, claimId: { type: "string" }, decision: { type: "string" }, business: { type: "string" }, bookingId: { type: "string" }, note: { type: "string" }, inquiryId: { type: "string" }, account: { type: "string" }, threadId: { type: "string" }, body: { type: "string" }, to: { type: "string" }, subject: { type: "string" } } }, summary: { type: "string", description: "One line Jesse will confirm, e.g. 'Approve Roven job Senior RN at Mercy'" } }, required: ["kind", "params", "summary"], additionalProperties: false } },
];

async function runTool(name, input, env, actions) {
  switch (name) {
    case "track_flight": { const r = await trackFlight(env, input.flight); r.route = await flightRoute(env, r.callsign); actions.push({ type: "world", flight: r.callsign }); return JSON.stringify(r).slice(0, 3000); }
    case "fleet_status": return JSON.stringify(await fleetStatus(env, "ncl"));
    case "find_ship": { const g = JSON.parse((await env.HUB.get("ships_global")) || '{"ships":[]}'); const q = String(input.name || "").toUpperCase().replace(/\s+/g, " ").trim(); const hits = g.ships.filter((r) => String(r[1]).toUpperCase().includes(q)).slice(0, 5); if (!hits.length) { const last = (await kv.get(env, "fleet_last")) || {}; const k = Object.keys(last).find((n) => n.includes(q)); if (k) { const l = last[k]; actions.push({ type: "ship", mmsi: l.row[0], lat: l.row[2], lon: l.row[3] }); return `${k} is not in the live feed (no shore receiver in range: likely at sea). Last heard ${l.seen}: ${l.row[2]}, ${l.row[3]}${l.row[7] ? ", bound for " + l.row[7] : ""}.`; } } if (!hits.length) return "No vessel called " + input.name + " in the feed right now (it covers passenger ships: cruise ships and ferries; coverage depends on AIS receivers near the ship)."; actions.push({ type: "ship", mmsi: hits[0][0], lat: hits[0][2], lon: hits[0][3] }); return JSON.stringify(hits.map((r) => ({ name: r[1], mmsi: r[0], lat: r[2], lon: r[3], heading: r[4], speed_kt: r[5], destination: r[7], length_m: r[8], reported_s_ago: r[9] }))); }
    case "watch_ship": { let list = (await kv.get(env, "ship_watch")) || []; const q = String(input.name || "").trim(); if (input.action === "list") return list.length ? list.map((w) => `${w.name}${w.lastSeen ? " (last seen " + w.lastSeen.slice(0, 16) + ")" : " (not seen yet)"}`).join("; ") : "No ships on watch."; if (input.action === "remove") { list = list.filter((w) => w.name.toUpperCase() !== q.toUpperCase()); await kv.put(env, "ship_watch", list); return "Removed."; } if (!list.some((w) => w.name.toUpperCase() === q.toUpperCase())) list.push({ name: q, added: new Date().toISOString() }); await kv.put(env, "ship_watch", list); await shipWatch(env); return `Watching for ${q}. I'll push and say so when any receiver hears her.`; }
    case "flights_overhead": { const place = await kv.get(env, "place"); const ac = await flightsNear(env, +(place?.lat || 33.15), +(place?.lon || -96.82), input.nm || 25); actions.push({ type: "world" }); return JSON.stringify({ near: place?.name, count: ac.length, aircraft: ac.slice(0, 25) }); }
    case "open_link": actions.push({ type: "open", url: input.url, label: input.label }); return "Opened " + input.label + ".";
    case "append_note": { const cur = (await kv.get(env, "notes")) || ""; const next = (cur ? cur.replace(/\s+$/, "") + "\n" : "") + "- " + input.text; await kv.put(env, "notes", next); actions.push({ type: "notes", value: next }); return "Added."; }
    case "remember": { const mem = (await kv.get(env, "memory")) || []; const m = { id: uid(), text: input.text, at: new Date().toISOString() }; mem.unshift(m); await kv.put(env, "memory", mem.slice(0, 200)); actions.push({ type: "memory", value: mem }); return "Remembered [" + m.id + "]."; }
    case "forget": { const mem = ((await kv.get(env, "memory")) || []).filter((m) => m.id !== input.id); await kv.put(env, "memory", mem); actions.push({ type: "memory", value: mem }); return "Forgotten."; }
    case "add_trip": { const t = await addTrip(env, input); actions.push({ type: "trips" }); return JSON.stringify(t); }
    case "remove_trip": { const trips = ((await kv.get(env, "trips")) || []).filter((t) => t.id !== input.id); await kv.put(env, "trips", trips); actions.push({ type: "trips" }); return "Removed."; }
    case "watch_app": { const list = (await kv.get(env, "apps_watch")) || []; const key = (input.platform + "_" + input.id).toLowerCase(); if (!list.some((a) => a.key === key)) list.push({ key, name: input.name, ...(input.platform === "ios" ? { ios: /^\d+$/.test(input.id) ? { id: input.id } : { bundle: input.id } } : { android: input.id }) }); await kv.put(env, "apps_watch", list); return "Watching " + input.name + ". The first check lands within 15 minutes."; }
    case "set_reminder": { const r = await addReminder(env, input); actions.push({ type: "reminders" }); return r.error ? r.error : `Reminder [${r.id}] set for ${r.local}${r.repeat !== "none" ? ", repeating " + r.repeat : ""}.`; }
    case "cancel_reminder": { await kv.put(env, "reminders", ((await kv.get(env, "reminders")) || []).filter((r) => r.id !== input.id)); actions.push({ type: "reminders" }); return "Cancelled."; }
    case "set_alarm": { const tm = String(input.time || "").match(/^(\d{1,2}):(\d{2})$/); if (!tm || +tm[1] > 23 || +tm[2] > 59) return JSON.stringify({ error: "time must be HH:MM 24h" }); const time = tm[1].padStart(2, "0") + ":" + tm[2]; const cur = (await kv.get(env, "alarm")) || {}; const days = input.days === "weekdays" ? [1, 2, 3, 4, 5] : input.days === "weekends" ? [0, 6] : []; const next = alarmToday(env, { ...cur, enabled: !!input.enabled, time, days, at: new Date().toISOString() }); await kv.put(env, "alarm", next); actions.push({ type: "alarm" }); return `Alarm ${next.enabled ? "set for " + next.time + " " + (input.days === "all" ? "every day" : input.days) : "off"}.`; }
    case "watch_competitor": { const list = (await kv.get(env, "competitors")) || []; if (!list.some((c) => c.url === input.url)) list.push({ url: input.url, label: input.label, business: input.business, added: new Date().toISOString() }); await kv.put(env, "competitors", list); actions.push({ type: "competitors" }); return "Watching " + input.label + ". First scan Sunday evening, or say 'scan competitors now'."; }
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
          ...(noTools ? {} : { tools: [...BRAIN_TOOLS, { type: "web_search_20250305", name: "web_search", max_uses: 3 }] }), messages,
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
  afternoon: "This is the AFTERNOON brief. About 150 to 220 words. Only what is NEW since the morning brief: fresh leads or bookings, web traffic so far today across the sites, actions completed, alerts, any site that got slow, scores of games in progress or finished today, markets at midday, and anything that changed in the forecast for tonight or this week's weddings. Do not repeat the morning numbers or re-describe the day's weather unless it changed. If genuinely nothing changed, say so in two sentences.",
  weekly: "This is the MONDAY WEEKLY REVIEW. About 350 to 450 words, five minutes read aloud. For each business in turn: last week against the week before (revenue or cash in, bookings or sign-ups, leads, web traffic, search clicks), and against the same week last year where YEAR-AGO figures exist (say plainly when there is no prior year yet). Then the money picture: the 90-day cash forecast by week, any thin weeks, and anything past due. Then the competitor changes from the last scan, if any. Then one short paragraph on JARVIS's own reliability from the JARVIS HEALTH line: missed cron runs, feed stalls, bridge errors, failed briefs; say plainly if it was a clean week. Finish with exactly one thing to fix this week for each business, stated as an instruction. Flowing prose, no lists, no headers.",
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
  const tzL = env.TZ || "America/Chicago", todayL = new Date().toLocaleDateString("en-CA", { timeZone: tzL });
  const prevToday = history.filter((b) => new Date(b.at).toLocaleDateString("en-CA", { timeZone: tzL }) === todayL && b.slot !== slot).map((b) => `${b.slot.toUpperCase()} (${b.at}): ${b.text}`).join("\n\n");
  const params = {
    model: MODEL, max_tokens: 6000, betas: ["server-side-fallback-2026-07-01"], fallbacks: "default", output_config: { effort: "medium" },
    system: BRAIN_SYSTEM + "\nYou are composing one of Jesse's three daily spoken briefs. " + SLOT_PROMPTS[slot] + " Flowing prose, no lists, no headers. When they apply, also cover: any balance charge that was declined (name, amount, attempt) and charges due in the next day; follow-up drafts waiting for him to send; a trip today (flight, route, and that JARVIS is tracking it); a brand that missed today's social post (evening only); a new app version that went live; a search traffic drop. For Lazo, report ONLY sign-ups (new couples, new vendor claims); never mention unanswered vendor inquiries in a brief.",
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
  const list = [brief, ...history].slice(0, 10);
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
    if (stale && !flags[key]) { flags[key] = Date.now(); changed = true; await healthNote(env, "stale", { feed: label, minutes: Math.round(age / 60000) }); await pushAlert(env, { kind: "watch", text: `${label} feed is ${Math.round(age / 60000)} min old: is the PC awake and signed in?` }); await notify(env, "Feed stopped", `${label} last arrived ${Math.round(age / 60000)} min ago. Check the PC (collectors / Claude app).`, { priority: "high", tags: "warning" }); }
    if (!stale && flags[key]) { delete flags[key]; changed = true; await pushAlert(env, { kind: "up", text: `${label} feed is back` }); }
  }
  if (changed) await kv.put(env, "stale", flags);
  return flags;
}
/* ---------------- ElevenLabs ---------------- */
function elevenlabs(env, text, format = "mp3_44100_128", model = "eleven_turbo_v2_5", settings = {}) {
  const voice = env.ELEVENLABS_VOICE_ID || "JBFqnCBsd6RMkjVDRZzb";
  return fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voice}/stream?output_format=${format}`, {
    method: "POST", headers: { "xi-api-key": env.ELEVENLABS_API_KEY, "content-type": "application/json" },
    body: JSON.stringify({ text: String(text).slice(0, 4800), model_id: model, voice_settings: { stability: 0.6, similarity_boost: 0.8, style: 0.15, use_speaker_boost: true, ...settings } }),
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

/* ---------------- watchtower: payments, social, search, app stores, follow-ups, trips ---------------- */
const fmtUsd = (n) => "$" + Math.round(n || 0).toLocaleString();
const payWhy = (e) => (String(e || "").match(/"message":"([^"]+)"/) || [])[1] || String(e || "").slice(0, 100);
const siteName = (s) => String(s || "").replace(/^sc-domain:|^https?:\/\/|\/$/g, "");
// `watch` is posted by the PC; the social section lives under its own key (socialFromLog) and is merged in when read
async function watchMerged(env) {
  const [w, s] = await Promise.all([kv.get(env, "watch"), kv.get(env, "watch_social")]);
  if (!w && !s?.social) return w; const out = w || {}; if (s?.social) out.social = s.social; return out;
}

// KV is eventually consistent: read-modify-write twice in a row can lose the first write.
// Watchers therefore collect their alerts and "already told him" keys and write each list once.
async function onceStore(env) {
  const seen = (await kv.get(env, "once")) || {}; let dirty = false;
  return {
    fresh(key, ttlMs) { const now = Date.now(); if (seen[key] && now - seen[key] < ttlMs) return false; seen[key] = now; dirty = true; return true; },
    async save() { if (!dirty) return; const now = Date.now(); for (const k of Object.keys(seen)) if (now - seen[k] > 90 * 86400e3) delete seen[k]; await kv.put(env, "once", seen); },
  };
}
async function flushAlerts(env, out) {
  if (!out.length) return;
  const list = (await kv.get(env, "alerts")) || [];
  const at = new Date().toISOString();
  list.unshift(...out.map((x) => ({ ...x.alert, at, id: uid() })).reverse());
  await kv.put(env, "alerts", list.slice(0, 80));
  await Promise.all(out.filter((x) => x.push).map((x) => notify(env, x.push.title, x.push.body, x.push.opts || {}).catch(() => null)));
}

// the PC posts `watch` every 15 minutes: balance charges, social posting logs, Search Console, iOS listings
async function watchWatch(env, w) {
  const once = await onceStore(env); const out = [];
  for (const p of Array.isArray(w.payments) ? w.payments : []) {
    if (!p.id) continue; /* collector error row, not a booking */ const biz = BIZ_NAME[p.business] || p.business;
    if (p.state === "failed" && once.fresh(`payfail:${p.id}:${p.attempts}`, 90 * 86400e3)) {
      const text = `${biz} balance declined: ${p.names} ${fmtUsd(p.amount)}, attempt ${p.attempts} of 3 (${payWhy(p.error)})${p.attempts < 3 ? ". Zoho retries tomorrow morning" : ". Retries are over; the couple was emailed a pay link"}`;
      out.push({ alert: { kind: "failed", text }, push: { title: "Balance charge declined", body: text, opts: { priority: "high", tags: "credit_card" } } });
    }
    if (p.state === "charged" && p.paid && Date.now() - new Date(p.paid) < 3 * 86400e3 && once.fresh(`paid:${p.id}`, 90 * 86400e3)) {
      const text = `${biz} balance charged: ${p.names} ${fmtUsd(p.amount)}`;
      out.push({ alert: { kind: "done", text }, push: { title: "Balance charged", body: text, opts: { tags: "moneybag" } } });
    }
  }
  const brands = w.social?.brands || [];
  if (brands.length && localHour(env) >= 19) {
    const missed = brands.filter((b) => !b.today).map((b) => b.name);
    if (missed.length && once.fresh("social:" + w.social.day, 20 * 3600e3)) {
      const text = `Not posted today: ${missed.join(", ")}`;
      out.push({ alert: { kind: "watch", text }, push: { title: "Social posts missing", body: text + ". The daily posting tasks run from the Claude app on the PC; check it's awake and open.", opts: { priority: "high", tags: "camera" } } });
    }
  }
  const sc = w.search || {};
  if (sc.fix && once.fresh("gsc_setup", 7 * 86400e3)) out.push({ alert: { kind: "watch", text: "Search Console isn't connected yet. " + sc.fix } });
  for (const site of sc.sites || []) {
    const d = site.days || []; if (d.length < 20) continue;
    const avg = (rows, i) => rows.reduce((a, r) => a + r[i], 0) / Math.max(1, rows.length);
    const recent = d.slice(-3), base = d.slice(-31, -3);
    const ri = avg(recent, 2), bi = avg(base, 2), rc = avg(recent, 1), bc = avg(base, 1);
    if (bi >= 20 && ri < bi * 0.5 && once.fresh("gsc_drop:" + site.site, 3 * 86400e3)) {
      const text = `${siteName(site.site)} search impressions fell to ${Math.round(ri)} a day from ${Math.round(bi)} (clicks ${rc.toFixed(1)} vs ${bc.toFixed(1)}), last 3 days vs the 4 weeks before`;
      out.push({ alert: { kind: "watch", text }, push: { title: "Search traffic drop", body: text + ". Check Search Console for manual actions, coverage and crawl errors.", opts: { priority: "high", tags: "chart_with_downwards_trend", url: "https://search.google.com/search-console" } } });
    }
  }
  await once.save(); await flushAlerts(env, out);
  if (w.ios && Object.keys(w.ios).length) { await kv.put(env, "ios_results", { at: w.at || new Date().toISOString(), v: w.ios }); await appStores(env); }
}

// App Store / Google Play listings: push when an app first goes live or a new version ships.
// Google Play is read from here; Apple's lookup API refuses Cloudflare, so the PC collector reads iOS and posts it in `watch.ios`.
const APPS = [
  { key: "lazo_ios", name: "Lazo · iOS", ios: { id: "6812863675" } },
  { key: "lazo_android", name: "Lazo · Android", android: "com.meetlazo.app" },
  { key: "jovi_ios", name: "Jovi · iOS", ios: { search: "Jovi Health" } },
];
async function appStores(env) {
  const extra = (await kv.get(env, "apps_watch")) || [];
  const prev = (await kv.get(env, "apps")) || {}; const out = {}; const ios = await kv.get(env, "ios_results");
  const once = await onceStore(env); const alerts = [];
  for (const a of [...APPS, ...extra]) {
    const p = prev[a.key]; let cur = null;
    try {
      if (a.ios) {
        const r = ios?.v?.[a.key];
        if (!r || Date.now() - new Date(ios.at) > 3 * 3600e3) { out[a.key] = p || { name: a.name, store: "ios", listed: false, pending: true }; continue; }
        if (r.error) throw new Error(r.error);
        cur = { name: a.name, store: "ios", listed: !!r.listed, version: r.version || null, released: r.released || null, url: r.url || null };
      } else if (a.android) {
        const url = `https://play.google.com/store/apps/details?id=${encodeURIComponent(a.android)}&hl=en_US&gl=US`;
        const r = await within(fetch(url, { headers: { "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36", "accept-language": "en-US" } }), 10000, null);
        if (!r) throw new Error("Play timeout");
        if (r.status === 404) cur = { name: a.name, store: "android", listed: false };
        else if (!r.ok) throw new Error("Play " + r.status);
        else { const h = await r.text(); cur = { name: a.name, store: "android", listed: true, version: (h.match(/\[\[\["(\d+\.\d+(?:\.\d+)?)"\]\]/) || [])[1] || null, released: (h.match(/Updated on<\/div><div[^>]*>([^<]+)</) || [])[1] || null, url }; }
      }
    } catch (e) { out[a.key] = { ...(p || { name: a.name, listed: false }), error: String(e.message || e).slice(0, 120) }; continue; }
    cur.checkedAt = new Date().toISOString(); out[a.key] = cur;
    if (!p || p.pending || p.error || p.listed === undefined) continue; // first real look (or the last look failed): just record
    let msg = null;
    if (cur.listed && !p.listed) msg = `${a.name} is live on the ${cur.store === "ios" ? "App Store" : "Play Store"}${cur.version ? " (v" + cur.version + ")" : ""}`;
    else if (cur.listed && p.listed && cur.version && p.version && cur.version !== p.version) msg = `${a.name} v${cur.version} is live (was v${p.version})`;
    else if (cur.listed && p.listed && !cur.version && cur.released && p.released && cur.released !== p.released) msg = `${a.name} update is live (${cur.released})`;
    else if (!cur.listed && p.listed) msg = `${a.name} is no longer listed in the store`;
    if (msg && once.fresh("store:" + msg, 7 * 86400e3)) alerts.push({ alert: { kind: cur.listed ? "done" : "failed", text: msg, url: cur.url }, push: { title: "App store", body: msg, opts: { priority: cur.listed ? "default" : "urgent", tags: "iphone", url: cur.url || "" } } });
  }
  await kv.put(env, "apps", out); await once.save(); await flushAlerts(env, alerts);
  return out;
}

// leads, clients and bookings left unanswered for a day: JARVIS drafts the reply, Jesse sends it from Decisions
const DEFAULT_PLAYBOOK = { atavia: "Wedding films. Warm and confident. Ask for the date and venue if missing. Offer a 15-minute call. Do not quote prices unless the playbook lists them.", es: "Wedding films. Warm and personal. Ask for the date and venue if missing. Offer a 15-minute call. Do not quote prices unless the playbook lists them.", lazo: "Wedding planner app and vendor directory. Friendly, short. Point couples to the app, vendors to claiming their listing.", roven: "Hiring platform. Professional, concise.", lr: "Apartment reviews. Professional, concise.", brisk: "Professional, concise." };
async function makeFollowups(env, { minAgeH = 24, dry = false, onlyThreads = null, first = false } = {}) {
  if (!env.ANTHROPIC_API_KEY) return;
  const brief = await kv.get(env, "brief"); const list = (await kv.get(env, "followups")) || [];
  const items = brief?.items || [];
  const have = new Set(list.map((f) => f.threadId + "|" + f.received));
  const due = items.filter((m) => m.needs_reply && m.threadId && m.account && !isBot(m.fromEmail) && ["lead", "client", "booking"].includes(m.kind) && Date.now() - new Date(m.received) > minAgeH * 3600e3 && (!onlyThreads || onlyThreads.includes(m.threadId)) && !have.has(m.threadId + "|" + m.received)).slice(0, 3);
  const playbook = (await kv.get(env, "playbook")) || {}; const metrics = await kv.get(env, "metrics");
  if (dry && !due.length) return [{ skip: "none due", candidates: items.filter((m) => m.needs_reply).map((m) => ({ kind: m.kind, ageH: Math.round((Date.now() - new Date(m.received)) / 3600e3), acct: !!m.account, thread: !!m.threadId })) }];
  const client = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY }); const out = [];
  for (const m of due) {
    const t = await bridgeCall(env, m.account, { action: "get", threadId: m.threadId }).catch(() => ({ error: "bridge" }));
    if (t.error || !t.messages?.length) { if (dry) out.push({ skip: "bridge", error: t.error || "no messages" }); continue; }
    const last = t.messages[t.messages.length - 1];
    const thread = t.messages.slice(-6).map((x) => `FROM: ${x.from}\nDATE: ${x.date}\n${String(x.body || "").slice(0, 3000)}`).join("\n---\n");
    const r = await client.beta.messages.create({
      model: "claude-sonnet-5-5", max_tokens: 1500, betas: ["server-side-fallback-2026-07-01"], fallbacks: "default", output_config: { effort: "low" },
      system: `You write email replies for ${BIZ_NAME[m.business] || BIZ_LABEL[m.business] || "the business"}, owned by Jesse Clark.
HOW THIS BUSINESS REPLIES (Jesse's playbook; follow it, it may include prices and packages you are allowed to quote):
${playbook[m.business] || DEFAULT_PLAYBOOK[m.business] || DEFAULT_PLAYBOOK.brisk}
${(metrics?.businesses?.[m.business]?.upcoming || []).length ? "DATES ALREADY BOOKED (if the inquiry asks for one of these, say the date is taken and offer to check nearby dates): " + metrics.businesses[m.business].upcoming.map((u) => u.date).join(", ") : ""}
Warm, brief, specific to what they asked, professional. ${first ? "This is the FIRST reply to a new inquiry: thank them, answer what you can from the playbook, ask the one or two things needed to quote or hold a date, and propose a quick call." : "Apologise briefly for the slow reply only if it reads naturally."} Never invent prices, availability or facts that are not in the thread or the playbook; where something must be confirmed, offer a quick call or say you'll confirm. End with a clear next step. Sign off as "${BIZ_NAME[m.business] || "the team"}". Output only the email body, no subject line, no commentary.`,
      messages: [{ role: "user", content: `This ${m.kind} has waited more than a day for a reply. Write the reply to the latest message.\n\nTHREAD (oldest first):\n${thread}` }],
    });
    const body = r.content.filter((b) => b.type === "text").map((b) => b.text).join("").trim(); if (!body) continue;
    const f = { id: uid(), first, business: m.business, account: m.account, threadId: m.threadId, received: m.received, from: m.from, to: (String(last.from).match(/<([^>]+)>/) || [null, last.from])[1], subject: m.subject, body, status: "ready", at: new Date().toISOString() };
    if (dry) { out.push({ dry: true, business: f.business, kind: m.kind, chars: f.body.length, signoff: f.body.split(/\n/).slice(-2).join(" / ") }); continue; }
    list.unshift(f);
    out.push({ alert: { kind: "lead", text: `${first ? "Reply" : "Follow-up"} drafted for ${m.from}: ${m.subject}. Review and send it from Decisions.` }, push: { title: first ? "New lead: reply drafted" : "Follow-up ready to send", body: `${m.from}: ${m.subject}\nWaited ${Math.round((Date.now() - new Date(m.received)) / 3600e3)}h. Open JARVIS → Decisions to review and send.`, opts: { priority: "high", tags: "envelope_with_arrow", url: HUB_ORIGIN + "/#decisions" } } });
  }
  if (dry) return out;
  await flushAlerts(env, out);
  // drafts whose thread got a reply in Gmail are no longer needed
  const byThread = Object.fromEntries(items.map((m) => [m.threadId, m]));
  for (const f of list) if (f.status === "ready" && byThread[f.threadId] && !byThread[f.threadId].needs_reply) f.status = "answered";
  await kv.put(env, "followups", list.filter((f) => Date.now() - new Date(f.at) < 14 * 86400e3).slice(0, 30));
}

// trips: track Jesse's own flights on the day, push wheels-up / landed, switch home on landing
async function addTrip(env, input) {
  const trips = (await kv.get(env, "trips")) || [];
  const t = { id: uid(), flight: String(input.flight || "").toUpperCase().trim(), date: String(input.date || "").slice(0, 10), home: HOMES[input.home] ? input.home : null, note: input.note || "", phase: "scheduled", at: new Date().toISOString() };
  if (!t.flight || !/^\d{4}-\d{2}-\d{2}$/.test(t.date)) return { error: "need a flight number and a YYYY-MM-DD date" };
  const r = await flightRoute(env, toCallsign(t.flight)).catch(() => null); if (r?.from) t.route = { from: r.from, to: r.to, airline: r.airline };
  trips.push(t); trips.sort((a, b) => a.date.localeCompare(b.date));
  await kv.put(env, "trips", trips);
  return t;
}
const place = (a) => a ? (a.city || a.iata || a.name) : "?";
async function tripWatch(env) {
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


/* ---------------- faith: the rosary (led aloud) and the daily Mass readings with a plain-words reading ---------------- */
const PRAYERS = {
  sign: "In the name of the Father, and of the Son, and of the Holy Spirit. Amen.",
  creed: "I believe in God, the Father almighty, Creator of heaven and earth, and in Jesus Christ, his only Son, our Lord, who was conceived by the Holy Spirit, born of the Virgin Mary, suffered under Pontius Pilate, was crucified, died and was buried; he descended into hell; on the third day he rose again from the dead; he ascended into heaven, and is seated at the right hand of God the Father almighty; from there he will come to judge the living and the dead. I believe in the Holy Spirit, the holy catholic Church, the communion of saints, the forgiveness of sins, the resurrection of the body, and life everlasting. Amen.",
  our: "Our Father, who art in heaven, hallowed be thy name; thy kingdom come, thy will be done on earth as it is in heaven. Give us this day our daily bread, and forgive us our trespasses, as we forgive those who trespass against us; and lead us not into temptation, but deliver us from evil. Amen.",
  hail: "Hail Mary, full of grace, the Lord is with thee. Blessed art thou among women, and blessed is the fruit of thy womb, Jesus. Holy Mary, Mother of God, pray for us sinners, now and at the hour of our death. Amen.",
  glory: "Glory be to the Father, and to the Son, and to the Holy Spirit, as it was in the beginning, is now, and ever shall be, world without end. Amen.",
  fatima: "O my Jesus, forgive us our sins, save us from the fires of hell, and lead all souls to heaven, especially those in most need of thy mercy.",
  salve: "Hail, holy Queen, Mother of mercy, our life, our sweetness and our hope. To thee do we cry, poor banished children of Eve; to thee do we send up our sighs, mourning and weeping in this valley of tears. Turn then, most gracious advocate, thine eyes of mercy toward us, and after this our exile show unto us the blessed fruit of thy womb, Jesus. O clement, O loving, O sweet Virgin Mary. Pray for us, O holy Mother of God, that we may be made worthy of the promises of Christ.",
  closing: "Let us pray. O God, whose only begotten Son, by his life, death and resurrection, has purchased for us the rewards of eternal life: grant, we beseech thee, that by meditating upon these mysteries of the most holy Rosary of the Blessed Virgin Mary, we may imitate what they contain and obtain what they promise, through the same Christ our Lord. Amen.",
};
const MYSTERIES = {
  joyful: { name: "Joyful Mysteries", days: "Mondays and Saturdays", list: [
    ["The Annunciation", "Luke 1:26-38", "humility", "The angel Gabriel tells Mary she will bear the Son of God, and she answers: let it be done to me according to your word."],
    ["The Visitation", "Luke 1:39-56", "love of neighbour", "Mary hurries to help her cousin Elizabeth, and the child in Elizabeth's womb leaps for joy."],
    ["The Nativity", "Luke 2:1-20", "poverty of spirit", "Jesus is born in a stable at Bethlehem, and shepherds are the first to find him."],
    ["The Presentation in the Temple", "Luke 2:22-38", "obedience", "Mary and Joseph bring the child to the Temple, where old Simeon holds him and calls him a light for all nations."],
    ["The Finding in the Temple", "Luke 2:41-52", "joy in finding Jesus", "After three days of searching, Mary and Joseph find the twelve-year-old Jesus among the teachers, about his Father's business."] ] },
  sorrowful: { name: "Sorrowful Mysteries", days: "Tuesdays and Fridays", list: [
    ["The Agony in the Garden", "Matthew 26:36-46", "sorrow for sin", "In Gethsemane Jesus sweats blood and prays: not my will, but yours be done."],
    ["The Scourging at the Pillar", "John 19:1", "purity", "Pilate has Jesus scourged; he bears it in silence for us."],
    ["The Crowning with Thorns", "Matthew 27:27-31", "courage", "Soldiers press a crown of thorns onto his head and mock him as a king."],
    ["The Carrying of the Cross", "John 19:17", "patience", "Jesus carries his cross to Calvary, falling and rising, helped by Simon of Cyrene."],
    ["The Crucifixion", "Luke 23:33-46", "perseverance", "Jesus forgives his executioners, entrusts his mother to John, and gives up his spirit."] ] },
  glorious: { name: "Glorious Mysteries", days: "Wednesdays and Sundays", list: [
    ["The Resurrection", "Matthew 28:1-10", "faith", "On the third day the tomb is empty; death has lost."],
    ["The Ascension", "Acts 1:6-11", "hope", "Forty days later Jesus is taken up to heaven, promising to be with us always."],
    ["The Descent of the Holy Spirit", "Acts 2:1-4", "love of God", "At Pentecost the Spirit comes as wind and fire, and frightened disciples become apostles."],
    ["The Assumption of Mary", "Revelation 12:1", "the grace of a happy death", "At the end of her life Mary is taken body and soul into heaven."],
    ["The Coronation of Mary", "Revelation 12:1", "trust in Mary's intercession", "Mary is crowned Queen of heaven and earth, and prays for us still."] ] },
  luminous: { name: "Luminous Mysteries", days: "Thursdays", list: [
    ["The Baptism in the Jordan", "Matthew 3:13-17", "openness to the Holy Spirit", "John baptises Jesus; the heavens open and the Father says: this is my beloved Son."],
    ["The Wedding at Cana", "John 2:1-11", "to Jesus through Mary", "At Mary's word, do whatever he tells you, Jesus turns water into wine, his first sign."],
    ["The Proclamation of the Kingdom", "Mark 1:14-15", "repentance and trust", "Jesus preaches: the kingdom of God is at hand; repent and believe the good news."],
    ["The Transfiguration", "Matthew 17:1-8", "desire for holiness", "On the mountain Jesus shines like the sun, with Moses and Elijah beside him."],
    ["The Institution of the Eucharist", "Matthew 26:26-28", "adoration", "At the Last Supper Jesus takes bread and wine: this is my body, this is my blood, given for you."] ] },
};
function easter(y) { const a = y % 19, b = Math.floor(y / 100), c = y % 100, d = Math.floor(b / 4), e = b % 4, f = Math.floor((b + 8) / 25), g = Math.floor((b - f + 1) / 3), h = (19 * a + b - d - g + 15) % 30, i = Math.floor(c / 4), k = c % 4, l = (32 + 2 * e + 2 * i - h - k) % 7, m = Math.floor((a + 11 * h + 22 * l) / 451), mo = Math.floor((h + l - 7 * m + 114) / 31), da = ((h + l - 7 * m + 114) % 31) + 1; return new Date(Date.UTC(y, mo - 1, da)); }
function liturgicalSeason(d) {   // d: UTC midnight of the local date
  const y = d.getUTCFullYear(), E = easter(y), day = 86400e3;
  if (d >= new Date(E - 46 * day) && d < E) return "Lent";
  if (d >= E && d < new Date(+E + 50 * day)) return "Easter";
  const xmas = new Date(Date.UTC(y, 11, 25)), adv = new Date(xmas - ((xmas.getUTCDay() || 7) + 21) * day);
  if (d >= adv && d < xmas) return "Advent";
  if (d >= xmas || d < new Date(Date.UTC(y, 0, 13))) return "Christmas";
  return "Ordinary Time";
}
function mysteriesFor(env, when = new Date()) {
  const local = new Date(when.toLocaleString("en-US", { timeZone: env.TZ || "America/Chicago" })); const dow = local.getDay();
  const d = new Date(Date.UTC(local.getFullYear(), local.getMonth(), local.getDate())); const season = liturgicalSeason(d);
  let key = ["glorious", "joyful", "sorrowful", "glorious", "luminous", "sorrowful", "joyful"][dow], why = MYSTERIES[key].days;
  if (dow === 0 && (season === "Advent" || season === "Christmas")) { key = "joyful"; why = "Sundays of Advent and Christmas"; }
  if (dow === 0 && season === "Lent") { key = "sorrowful"; why = "Sundays of Lent"; }
  return { key, season, why, date: d.toISOString().slice(0, 10), ...MYSTERIES[key] };
}
function rosaryScript(key) {
  const M = MYSTERIES[key] || MYSTERIES.glorious, hail10 = Array(10).fill(PRAYERS.hail).join(" "), segs = [];
  segs.push({ id: "open", label: "Opening prayers", text: `${PRAYERS.sign} ${PRAYERS.creed} ${PRAYERS.our} For faith: ${PRAYERS.hail} For hope: ${PRAYERS.hail} For charity: ${PRAYERS.hail} ${PRAYERS.glory}` });
  M.list.forEach(([name, ref, fruit, med], i) => segs.push({ id: "d" + (i + 1), label: `${i + 1}. ${name}`, ref, fruit, med, text: `The ${["first", "second", "third", "fourth", "fifth"][i]} ${M.name.replace(" Mysteries", "").toLowerCase()} mystery: ${name}. ${med} We ask for the grace of ${fruit}. ${PRAYERS.our} ${hail10} ${PRAYERS.glory} ${PRAYERS.fatima}` }));
  segs.push({ id: "close", label: "Closing prayers", text: `${PRAYERS.salve} ${PRAYERS.closing} ${PRAYERS.sign}` });
  return { key, name: M.name, segments: segs };
}
const stripHtml = (h) => String(h || "").replace(/<br\s*\/?>/gi, "\n").replace(/<\/p>/gi, "\n\n").replace(/<[^>]+>/g, "").replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/&#8217;|&rsquo;/g, "’").replace(/&#8220;|&ldquo;/g, "“").replace(/&#8221;|&rdquo;/g, "”").replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/[ \t]+\n/g, "\n").replace(/\n{3,}/g, "\n\n").trim();
const unesc = (t) => String(t || "").replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&#039;/g, "'").replace(/&amp;/g, "&");
async function fetchReadings(env, dateStr) {
  const r = await within(fetch("https://bible.usccb.org/readings.rss", { headers: { "user-agent": "Mozilla/5.0 (JARVIS hub; personal dashboard)" } }), 10000, null);
  if (!r || !r.ok) throw new Error("USCCB feed " + (r?.status || "timeout"));
  const xml = await r.text(); const want = dateStr.slice(5, 7) + dateStr.slice(8, 10) + dateStr.slice(2, 4);   // MMDDYY in the link
  const items = [...xml.matchAll(/<item>([\s\S]*?)<\/item>/g)].map((m) => m[1]);
  const item = items.find((it) => it.includes(`/readings/${want}.cfm`)); if (!item) throw new Error("feed has no readings for " + dateStr);
  const title = stripHtml(unesc((item.match(/<title>([\s\S]*?)<\/title>/) || [])[1])), link = ((item.match(/<link>([\s\S]*?)<\/link>/) || [])[1] || "").trim();
  const desc = unesc((item.match(/<description>([\s\S]*?)<\/description>/) || [])[1]);
  const parts = []; const re = /<h4>\s*([^<]+?)\s*(?:<a[^>]*>([\s\S]*?)<\/a>)?\s*<\/h4>([\s\S]*?)(?=<h4>|$)/g; let m;
  while ((m = re.exec(desc))) { const kind = m[1].trim(), ref = stripHtml(m[2] || ""), text = stripHtml(m[3]); if (text.length > 20) parts.push({ kind, ref, text }); }
  return { date: dateStr, title, link, parts };
}
async function fetchReadingsPage(env, dateStr) {
  const mmddyy = dateStr.slice(5, 7) + dateStr.slice(8, 10) + dateStr.slice(2, 4), link = `https://bible.usccb.org/bible/readings/${mmddyy}.cfm`;
  const r = await within(fetch(link, { headers: { "user-agent": "Mozilla/5.0 (JARVIS hub; personal dashboard)" } }), 10000, null);
  if (!r || !r.ok) throw new Error("USCCB page " + (r?.status || "timeout"));
  const h = await r.text(); const title = stripHtml((h.match(/<title>([^<|]+)/) || [])[1] || "").trim();
  const parts = []; const re = /<h3 class="name">([\s\S]*?)<\/h3>\s*<div class="address">([\s\S]*?)<\/div>\s*<\/div>\s*<div class="content-body">([\s\S]*?)<\/div>/g; let m;
  while ((m = re.exec(h))) { const kind = stripHtml(m[1]), ref = stripHtml(m[2]), text = stripHtml(m[3]); if (text.length > 20) parts.push({ kind, ref, text }); }
  if (!parts.length) throw new Error("no readings on that page");
  return { date: dateStr, title, link, parts };
}
async function dailyReadings(env, { fresh = false, date = null } = {}) {
  const today = new Date().toLocaleDateString("en-CA", { timeZone: env.TZ || "America/Chicago" }); const dateStr = date || today;
  const cached = await kv.get(env, "readings_" + dateStr); if (cached?.reflection && !fresh) return cached;
  let base, firstErr; try { base = dateStr === today ? await fetchReadings(env, dateStr) : await fetchReadingsPage(env, dateStr); } catch (e) { firstErr = e.message; try { base = dateStr === today ? await fetchReadingsPage(env, dateStr) : await fetchReadings(env, dateStr); } catch (e2) { throw new Error(firstErr + " / " + e2.message); } }
  if (base.date !== dateStr && !base.link.includes(dateStr.slice(5, 7) + dateStr.slice(8, 10) + dateStr.slice(2, 4))) throw new Error("readings for " + dateStr + " not published yet");
  let reflection = null;
  if (env.ANTHROPIC_API_KEY) {
    const client = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY });
    const params_rd = {
      model: MODEL, max_tokens: 6000, betas: ["server-side-fallback-2026-07-01"], fallbacks: "default", output_config: { effort: "medium" },
      system: "You explain the Catholic daily Mass readings to a busy layman in plain, warm, modern English, faithful to Catholic teaching. No jargon, no sermon voice, no headers or markdown. Return JSON only: {\"theme\": one short line tying the day together, \"parts\": [{\"kind\": the reading's kind exactly as given, \"plain\": 2-4 sentences on what this passage is saying and why it is here today}], \"conclusion\": 90-140 words: what the readings and gospel together mean for an ordinary person's day, ending with one concrete thing to do or notice today}. Keep the parts in the same order as given; include every part.",
      messages: [{ role: "user", content: `${base.title} (${base.date})\n\n` + base.parts.map((p) => `${p.kind} ${p.ref}\n${p.text}`).join("\n\n---\n\n") }],
    };
    const r = await client.beta.messages.create(params_rd);
    const txt = await finishText(client, r, params_rd);
    reflection = parseJsonLoose(txt) || { theme: "", parts: [], conclusion: txt.replace(/[{}"]/g, " ").slice(0, 900) };
  }
  const out = { ...base, reflection, at: new Date().toISOString() };
  await env.HUB.put("readings_" + dateStr, JSON.stringify(out), { expirationTtl: 3 * 86400 });
  return out;
}
const parseJsonLoose = (txt) => {
  const cut = txt.slice(txt.indexOf("{"), txt.lastIndexOf("}") + 1);
  const clean = cut.replace(/[\u0000-\u001f]+/g, " ")                 // raw newlines inside strings
    .replace(/\\(?!["\\\/bfnrtu])/g, "")                                 // invalid escapes such as \' or \-
    .replace(/,\s*([}\]])/g, "$1");                                      // trailing commas
  for (const c of [cut, clean]) { try { return JSON.parse(c); } catch {} }
  return null;
};
// saint of the day: Vatican News keeps a page per calendar date, with a story page per saint
async function fetchSaint(env, dateStr) {
  const mm = dateStr.slice(5, 7), dd = dateStr.slice(8, 10), base = "https://www.vaticannews.va";
  const hdr = { "user-agent": "Mozilla/5.0 (JARVIS hub; personal dashboard)", "accept-language": "en-US,en;q=0.9" };
  const r = await within(fetch(`${base}/en/saints/${mm}/${dd}.html`, { headers: hdr }), 10000, null);
  if (!r || !r.ok) throw new Error("Vatican News " + (r?.status || "timeout"));
  const h = await r.text(); const entries = [];
  const chunksRe = /([\s\S]*?)<a class="saintReadMore" href="([^"]+)"/g; let m, last = 0;
  while ((m = chunksRe.exec(h))) {
    const before = m[1]; const h2s = [...before.matchAll(/<h2[^>]*>([\s\S]*?)<\/h2>/g)]; const name = stripHtml((h2s.pop() || [])[1] || "").replace(/\s+/g, " ").trim();
    const ps = [...before.matchAll(/<p[^>]*>([\s\S]*?)<\/p>/g)]; const blurb = stripHtml((ps.pop() || [])[1] || "").replace(/\s+/g, " ").trim();
    const img = (before.match(/data-original="([^"]+)"/g) || []).pop(); const image = img ? base + img.match(/data-original="([^"]+)"/)[1] : null;
    if (name && !/^(menu|search)$/i.test(name)) entries.push({ name, blurb, link: base + m[2], image });
  }
  if (!entries.length) throw new Error("no saint listed for " + dateStr);
  const main = entries[0]; let story = "";
  try {
    const d = await within(fetch(main.link, { headers: hdr }), 10000, null);
    if (d && d.ok) { const dh = await d.text(); const i = dh.indexOf('class="section__content'); const seg = dh.slice(i, i + 60000); story = [...seg.matchAll(/<p[^>]*>([\s\S]*?)<\/p>/g)].map((x) => stripHtml(x[1]).replace(/\s+/g, " ").trim()).filter((t) => t.length > 40 && !/©/.test(t)).join("\n\n").slice(0, 6000); }
  } catch {}
  return { date: dateStr, name: main.name, blurb: main.blurb, link: main.link, image: main.image, story, others: entries.slice(1).map((e) => ({ name: e.name, link: e.link })) };
}
async function finishText(client, r, params) {
  let txt = r.content.filter((b) => b.type === "text").map((b) => b.text).join("");
  if (r.stop_reason === "max_tokens" && params) {
    try { const r2 = await client.beta.messages.create({ ...params, messages: [...params.messages, { role: "assistant", content: r.content }, { role: "user", content: "You were cut off. Continue exactly where you stopped; output only the remainder." }] }); txt += r2.content.filter((b) => b.type === "text").map((b) => b.text).join(""); } catch {}
  }
  return txt;
}
async function saintOfDay(env, { fresh = false, date = null } = {}) {
  const dateStr = date || new Date().toLocaleDateString("en-CA", { timeZone: env.TZ || "America/Chicago" });
  const cached = await kv.get(env, "saint_" + dateStr); if (cached?.plain && !fresh) return cached;
  const base = await fetchSaint(env, dateStr); let plain = null;
  if (env.ANTHROPIC_API_KEY) {
    const client = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY });
    const params_saint_marker = {
      model: MODEL, max_tokens: 5000, betas: ["server-side-fallback-2026-07-01"], fallbacks: "default", output_config: { effort: "medium" },
      system: "You introduce the Catholic saint of the day to a busy layman in plain, warm, modern English, faithful to Catholic teaching and to the source text; do not invent dates or facts that are not in the source. Return JSON only: {\"title\": the saint's role in a few words (e.g. 'Founder of the Franciscans, patron of Italy'), \"life\": 110-150 words telling the life story simply, \"why\": 2-3 sentences on why this saint still matters, \"today\": one sentence, a concrete thing to carry into today inspired by this saint, \"patron\": what they are patron of if known from the source or well established, else \"\"}.",
      messages: [{ role: "user", content: `${base.name}\n\n${base.blurb}\n\n${base.story || "(no longer story available; use what is above and well-established facts only)"}` }],
    };
    const r = await client.beta.messages.create(params_saint_marker);
    const txt = await finishText(client, r, params_saint_marker);
    plain = parseJsonLoose(txt) || { title: "", life: txt.replace(/[{}"`]/g, " ").replace(/^\s*json\s*/i, "").slice(0, 800), why: "", today: "", patron: "", raw: txt.slice(0, 3000), stop: r.stop_reason, out: r.usage?.output_tokens, blocks: r.content.map((b) => b.type) };
  }
  const out = { ...base, plain, at: new Date().toISOString() };
  await env.HUB.put("saint_" + dateStr, JSON.stringify(out), { expirationTtl: 3 * 86400 });
  return out;
}
async function rosaryAudio(env, key, segId) {
  const kvKey = `rosary_audio_${key}_${segId}`; const have = await env.HUB.get(kvKey, "arrayBuffer");
  if (have) return new Response(have, { headers: { "content-type": "audio/mpeg", "cache-control": "private, max-age=86400" } });
  const seg = rosaryScript(key).segments.find((x) => x.id === segId); if (!seg) return json({ error: "no such segment" }, 404);
  let r = await elevenlabs(env, seg.text, "mp3_44100_128", "eleven_turbo_v2_5", { speed: 0.92, stability: 0.7, style: 0 });
  if (!r.ok) r = await elevenlabs(env, seg.text, "mp3_44100_128", "eleven_turbo_v2_5");
  if (!r.ok) return json({ error: "voice failed", status: r.status }, 502);
  const buf = await r.arrayBuffer(); await env.HUB.put(kvKey, buf, { expirationTtl: 60 * 86400 });
  return new Response(buf, { headers: { "content-type": "audio/mpeg", "cache-control": "private, max-age=86400" } });
}

/* ---------------- the observer: one unprompted remark an hour, only when something deserves it ---------------- */
async function observe(env, request, { force = false } = {}) {
  if (!env.ANTHROPIC_API_KEY) return null;
  const h = localHour(env); if (!force && (h < 8 || h > 20)) return null;
  const prev = (await kv.get(env, "observations")) || [];
  const client = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY });
  const context = await buildContext(env, request);
  const said = prev.filter((o) => Date.now() - new Date(o.at) < 36 * 3600e3).map((o) => `${o.at.slice(5, 16)}: ${o.text}`).join("\n");
  const r = await client.beta.messages.create({
    model: "claude-sonnet-5-5", max_tokens: 2000, betas: ["server-side-fallback-2026-07-01"], fallbacks: "default", output_config: { effort: "medium" },
    system: BRAIN_SYSTEM + `\nYou are keeping an eye on things between conversations. Decide whether there is ONE thing worth saying to Jesse right now that he has not been told (see ALREADY SAID). Worth saying: a lead or client email that arrived and is still unanswered; a payment that failed or came in; a site down or slow; a feed that stopped; weather turning bad before this week's wedding; a final score for one of his teams; a competitor change; a reminder of something he said he would do (NOTES, MEMORY); an app review result; a search traffic jump or drop; the Cox or any balance retry outcome. Not worth saying: routine numbers, anything in ALREADY SAID or the latest brief, generic encouragement, weather small talk. If nothing qualifies reply with exactly NOTHING. Otherwise reply with one or two spoken sentences, specific, with the number or name, no preamble.`,
    messages: [{ role: "user", content: `ALREADY SAID (last 36 h):\n${said || "(nothing yet today)"}\n\nLIVE CONTEXT:\n${context}` }],
  });
  const text = r.content.filter((b) => b.type === "text").map((b) => b.text).join("").trim();
  if (!text || /^nothing\b/i.test(text)) return null;
  const o = { at: new Date().toISOString(), text: text.slice(0, 500) }; prev.unshift(o); await kv.put(env, "observations", prev.slice(0, 40));
  await flushAlerts(env, [{ alert: { kind: "obs", text: o.text }, push: { title: "JARVIS", body: o.text, opts: { priority: "default", tags: "speech_balloon", sound: "none" } } }]);
  return o;
}

/* ---------------- named-ship watch: push when a watched vessel appears in the AIS feed ---------------- */
async function shipWatch(env) {
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

/* ---------------- health ledger: JARVIS watching JARVIS ---------------- */
// Three crons can tick in the same second; a shared read-modify-write key lost most of their writes, so each cron
// owns one small key (health_cron_<slug>, single writer) and the other events share health_events (low volume).
const cronSlug = (c) => String(c || "").replace(/[^a-z0-9]+/gi, "_");
async function healthNote(env, kind, data) {
  try {
    const iso = new Date().toISOString();
    if (kind === "cron") {
      const key = "health_cron_" + cronSlug(data); const c = (await kv.get(env, key)) || {};
      const hits = [...(c.hits || []).filter((t) => Date.now() - new Date(t) < 86400e3), iso].slice(-300);
      await kv.put(env, key, { cron: data, lastAt: iso, hits }); return;
    }
    const ev = (await kv.get(env, "health_events")) || []; ev.unshift({ at: iso, kind, ...data });
    await kv.put(env, "health_events", ev.filter((e) => Date.now() - new Date(e.at) < 8 * 86400e3).slice(0, 300));
  } catch {}
}
const SOCIAL_BRANDS = [["jovi", "Jovi Health"], ["atavia", "Atavia"], ["elizabethscott", "Elizabeth Scott"], ["trylazo", "Lazo"], ["lazovendors", "Lazo Vendors"], ["roven", "Roven"], ["leasereputation", "LeaseReputation"]];
async function socialFromLog(env) {
  const log = (await kv.get(env, "social_log")) || {}; const today = new Date().toLocaleDateString("en-CA", { timeZone: env.TZ || "America/Chicago" });
  const days = Object.keys(log).sort();
  const brands = SOCIAL_BRANDS.map(([key, name]) => { const last = [...days].reverse().find((d) => log[d][key]); return { brand: key, name, today: !!log[today]?.[key], last, total: days.filter((d) => log[d][key]).length, linkedin: !!log[today]?.[key]?.linkedin_urn, slug: log[today]?.[key]?.day || "" }; });
  const social = { day: today, brands, source: "hub" }; await kv.put(env, "watch_social", { social, at: new Date().toISOString() });   // never the shared `watch` key: the PC posts that one
  return social;
}
const CRON_EXPECT = { "* * * * *": 1440, "*/5 * * * *": 288, "0 * * * *": 24 };
async function healthReport(env, days = 7) {
  const since = Date.now() - days * 86400e3, dayAgo = Date.now() - 86400e3;
  const cron = await Promise.all(Object.entries(CRON_EXPECT).map(async ([c, expected]) => { const h = (await kv.get(env, "health_cron_" + cronSlug(c))) || {}; const hits = (h.hits || []).filter((t) => new Date(t) >= dayAgo); const runs = hits.length; const lastAt = h.lastAt || null; const span = hits.length ? Math.min(86400e3, Date.now() - Math.min(...hits.map((t) => +new Date(t)))) : 0; const exp = Math.max(1, Math.round(expected * span / 86400e3)); return { cron: c, runs, expected: exp, pct: Math.min(100, Math.round(runs / exp * 100)), lastAt, minutesAgo: lastAt ? Math.round((Date.now() - new Date(lastAt)) / 60000) : null }; }));   // runs in the last 24 h
  const ev = ((await kv.get(env, "health_events")) || []).filter((e) => new Date(e.at) >= since);
  const count = (k) => ev.filter((e) => e.kind === k).length;
  const byAcct = {}; for (const e of ev.filter((e) => e.kind === "bridge")) byAcct[e.account] = (byAcct[e.account] || 0) + 1;
  const errs = (await kv.get(env, "client_errors")) || [];
  const inbox = (await kv.get(env, "inbox")) || { accounts: {} };
  const syncAge = Object.entries(inbox.accounts).map(([a, v]) => ({ account: a, minutes: Math.round((Date.now() - new Date(v.at)) / 60000) }));
  return { days, cron, stale: ev.filter((e) => e.kind === "stale").map((e) => `${e.at.slice(5, 16)} ${e.feed} ${e.minutes}m`), bridgeErrors: byAcct, bridgeSamples: ev.filter((e) => e.kind === "bridge").slice(0, 5).map((e) => `${e.at.slice(5, 16)} ${e.account}: ${e.error}`), briefFailures: count("brief"), alarms: count("alarm"), clientErrors: errs.filter((e) => new Date(e.at) >= since).length, syncAge, issues: cron.filter((c) => c.pct != null && c.pct < 90).length + (count("stale") > 3 ? 1 : 0) + (Object.keys(byAcct).length ? 1 : 0) + (count("brief") ? 1 : 0) };
}
const healthSummary = (r) => `cron minute ${r.cron[0].pct ?? "?"}%, five-minute ${r.cron[1].pct ?? "?"}%, hourly ${r.cron[2].pct ?? "?"}% of expected runs; ${r.stale.length} feed stalls${r.stale.length ? " (" + r.stale.slice(0, 4).join("; ") + ")" : ""}; bridge errors ${Object.entries(r.bridgeErrors).map(([a, n]) => a + " ×" + n).join(", ") || "none"}${r.bridgeSamples.length ? " e.g. " + r.bridgeSamples[0] : ""}; brief failures ${r.briefFailures}; page script errors ${r.clientErrors}; inbox syncs ${r.syncAge.map((x) => x.account.split("@")[0] + " " + x.minutes + "m ago").join(", ") || "none"}`;

/* ---------------- reminders and the wake-up alarm (server side, every minute) ---------------- */
// "2026-10-05T07:30" in the home zone -> a real instant
function zonedToUtc(local, tz) {
  const m = String(local).match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/); if (!m) return null;
  const guess = Date.UTC(+m[1], m[2] - 1, +m[3], +m[4], +m[5]);
  const offAt = (t) => { const p = new Intl.DateTimeFormat("en-US", { timeZone: tz, hourCycle: "h23", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }).formatToParts(new Date(t)); const g = (k) => +p.find((x) => x.type === k).value; return Date.UTC(g("year"), g("month") - 1, g("day"), g("hour"), g("minute")) - t; };
  let t = guess - offAt(guess); t = guess - offAt(t); return new Date(t);
}
const localParts = (env, d = new Date()) => { const tz = env.TZ || "America/Chicago"; const p = new Intl.DateTimeFormat("en-US", { timeZone: tz, hourCycle: "h23", weekday: "short", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }).formatToParts(d); const g = (k) => p.find((x) => x.type === k)?.value; return { date: `${g("year")}-${g("month")}-${g("day")}`, hm: `${g("hour")}:${g("minute")}`, dow: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].indexOf(g("weekday")) }; };
const toMin = (hm) => { const m = String(hm || "").match(/^(\d{1,2}):(\d{2})$/); return m ? +m[1] * 60 + +m[2] : null; };
// (re)configuring the alarm after today's time has passed counts today as handled: it neither fires late nor reports "missed" until tomorrow
function alarmToday(env, al) {
  if (!al.enabled) return al; const lp = localParts(env), a = toMin(al.time), b = toMin(lp.hm); if (a == null || b == null) return al;
  if (b >= a) al.lastFired = lp.date; else { if (al.lastFired === lp.date) delete al.lastFired; if (al.missed === lp.date) delete al.missed; }
  return al;
}
function nextRepeat(at, repeat, tz) {
  const d = new Date(at); const lp = (x) => new Intl.DateTimeFormat("en-US", { timeZone: tz, weekday: "short" }).format(x);
  if (repeat === "weekly") return new Date(+d + 7 * 86400e3);
  let n = new Date(+d + 86400e3); if (repeat === "weekdays") while (["Sat", "Sun"].includes(lp(n))) n = new Date(+n + 86400e3);
  return n;
}
async function addReminder(env, { text, when, repeat = "none" }) {
  const tz = env.TZ || "America/Chicago"; const at = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$/.test(when) ? new Date(when) : zonedToUtc(when, tz);
  if (!text || !at || isNaN(at)) return { error: "need text and a time like 2026-10-05 15:00" };
  const list = (await kv.get(env, "reminders")) || []; const r = { id: uid(), text: String(text).slice(0, 300), at: at.toISOString(), repeat: ["daily", "weekdays", "weekly"].includes(repeat) ? repeat : "none", created: new Date().toISOString() };
  list.push(r); list.sort((a, b) => a.at.localeCompare(b.at)); await kv.put(env, "reminders", list.slice(0, 200));
  return { ...r, local: at.toLocaleString("en-US", { timeZone: tz, weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) };
}
async function tickMinute(env, fromMinuteCron = false) {
  const now = Date.now(); const tz = env.TZ || "America/Chicago"; const lp = localParts(env);
  if (fromMinuteCron) await kv.put(env, "tick_at", new Date(now).toISOString());   // the 5-minute backstop skips its own tick when this is fresh
  // reminders
  const list = (await kv.get(env, "reminders")) || []; const out = []; let changed = false;
  for (const r of list) {
    if (r.done || new Date(r.at) > now) continue;
    out.push({ alert: { kind: "watch", text: "Reminder: " + r.text }, push: { title: "Reminder", body: r.text, opts: { priority: "reminder", tags: "alarm_clock", url: HUB_ORIGIN + "/#reminders" } } });
    r.fired = new Date().toISOString(); changed = true;
    if (r.repeat && r.repeat !== "none") { let n = r.at; while (new Date(n) <= now) n = nextRepeat(n, r.repeat, tz).toISOString(); r.at = n; } else r.done = true;   // a reminder that slept through several periods lands in the future, not on the next tick again
  }
  if (changed) await kv.put(env, "reminders", list.filter((r) => !r.done || now - new Date(r.fired || r.at) < 7 * 86400e3));
  // the wake-up alarm
  // Cloudflare's minute cron skips or runs late now and then (2026-10-06 the 05:00 tick never came and the alarm
  // stayed silent), so never require an exact minute: fire at the first tick at or after the set time, within an hour.
  const al = (await kv.get(env, "alarm")) || {};
  const a = toMin(al.time), b = toMin(lp.hm); let late = (a == null || b == null) ? null : b - a;
  // the minute before: wait inside this run until hh:mm:00 and fire then, so a skipped or late tick at the set minute can't make it late
  if (fromMinuteCron && late === -1 && al.enabled && al.lastFired !== lp.date && (!al.days?.length || al.days.includes(lp.dow))) { await new Promise((ok) => setTimeout(ok, Math.max(0, 60e3 - (Date.now() % 60e3)) + 300)); late = 0; }
  // the set minute's own tick leaves it to the pre-armed run (KV reads can lag a minute, so both firing would double the alarm); backup from +2 min
  else if (fromMinuteCron && late !== null && late >= 0 && late < 2) late = null;
  if (al.enabled && late !== null && late >= 0 && late < 60 && al.lastFired !== lp.date && al.missed !== lp.date && (!al.days?.length || al.days.includes(lp.dow))) {
    const m = await kv.get(env, "morning"); const fresh = m?.slot === "morning" && now - new Date(m.at) < 3 * 3600e3;
    const headline = fresh ? m.text.split(/(?<=[.!?])\s/).slice(0, 2).join(" ") : "Your morning brief is on its way. Tap to open JARVIS.";
    out.push({ alert: { kind: "watch", text: "Wake-up alarm fired (" + al.time + (late > 1 ? ", " + late + " min late: the minute cron skipped" : "") + ")" }, push: { title: "Good morning, Mr. Clark", body: headline.slice(0, 500), opts: { priority: "alarm", tags: "sunrise", url: HUB_ORIGIN + "/#wake" } } });
    al.lastFired = lp.date; al.firedAt = new Date().toISOString(); al.pcDue = lp.date; for (const k of ["receipt", "firedReceipt", "delivery", "fallbackAt", "resent", "ackedBy", "called", "callRes"]) delete al[k];
    if (env.ALARM_CALL === "always" && callConfigured(env)) { al.called = new Date().toISOString(); al.callRes = await alarmCall(env, `Good morning, Mr. Clark. This is JARVIS. It is ${al.time}. Time to get up.`); }
    await kv.put(env, "alarm", al);
    if (late > 1) await healthNote(env, "alarm", { late, time: al.time }).catch(() => null);
  } else if (!(env.PUSHOVER_TOKEN && env.PUSHOVER_USER) && al.enabled && al.lastFired === lp.date && al.firedAt && al.acked !== lp.date && now - new Date(al.firedAt) < 45 * 60e3 && (!al.snooze || now >= new Date(al.snooze))) {
    // fired, not yet acknowledged from a phone: ring the browser again (Chrome's notification sound plays once per push)
    const mins = Math.round((now - new Date(al.firedAt)) / 60e3);
    await webPush(env, { title: "JARVIS: wake up", body: `It's ${lp.hm}. Alarm was ${al.time}${mins ? ", " + mins + " min ago" : ""}. Tap I'm up.`, url: HUB_ORIGIN + "/#wake", priority: "alarm", kind: "alarm", tag: "alarm", at: new Date().toISOString() }, { ttl: 120, urgency: "high", topic: "alarm" }).catch(() => null);
  } else if (al.enabled && late !== null && late >= 60 && al.lastFired !== lp.date && al.missed !== lp.date && (!al.days?.length || al.days.includes(lp.dow))) {
    // more than an hour past: too late to wake him, but say so instead of staying silent
    al.missed = lp.date; await kv.put(env, "alarm", al);
    out.push({ alert: { kind: "failed", text: `Wake-up alarm for ${al.time} did not fire today (the hub's minute cron was down for over an hour).` }, push: { title: "Alarm missed", body: `The ${al.time} alarm did not fire: the hub's minute cron was down for over an hour.`, opts: { priority: "high", tags: "warning" } } });
    await healthNote(env, "alarm", { missed: true, time: al.time }).catch(() => null);
  }
  await flushAlerts(env, out);
  await alarmWatch(env, lp).catch((e) => console.log("alarmWatch", e.message));
  return out.length;
}
// After the alarm fires: ask Pushover for the receipt (did the phone get it, was it acknowledged in the app), take an
// in-app acknowledgement as "I'm up", and escalate when the phone stays silent: ring the browser every minute and send one
// more Pushover alarm with a BUILT-IN sound (the custom Vivaldi clip can fail on the device while the API says 200).
// 2026-10-10: a week of Pushover 200s and a phone that never rang; the receipt is the only evidence of what the phone did.
// A real phone call wakes a phone whose push connection is asleep (2026-10-10: Pushover accepted the 05:00 alarm but could
// not deliver it until 05:08, when the phone woke on its own). Secrets: TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM (+1...), ALARM_PHONE (+1...).
// Var ALARM_CALL="always" calls at fire time as well; otherwise the call is the fallback when Pushover has not reached the phone in 2 min.
const xmlEsc = (s) => String(s).replace(/[<>&"']/g, (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;", "'": "&apos;" }[c]));
const callConfigured = (env) => !!(env.TWILIO_SID && env.TWILIO_TOKEN && env.TWILIO_FROM && env.ALARM_PHONE);
async function alarmCall(env, text) {
  if (!callConfigured(env)) return { call: "unconfigured" };
  const say = `<Say voice="Polly.Brian">${xmlEsc(text)}</Say>`; const twiml = `<Response>${say}<Pause length="1"/>${say}<Pause length="1"/>${say}</Response>`;
  try {
    const r = await fetch(`https://api.twilio.com/2010-04-01/Accounts/${env.TWILIO_SID}/Calls.json`, { method: "POST", headers: { authorization: "Basic " + btoa(env.TWILIO_SID + ":" + env.TWILIO_TOKEN) }, body: new URLSearchParams({ To: env.ALARM_PHONE, From: env.TWILIO_FROM, Twiml: twiml, Timeout: "45" }) });
    const t = await r.text(); let j = null; try { j = JSON.parse(t); } catch {}
    const out = { call: r.status, sid: j?.sid, detail: r.ok ? undefined : t.slice(0, 200) };
    try { const log = (await kv.get(env, "push_log")) || []; log.unshift({ at: new Date().toISOString(), title: "Phone call: " + text.slice(0, 40), priority: "alarm", res: [out] }); await kv.put(env, "push_log", log.slice(0, 40)); } catch {}
    return out;
  } catch (e) { return { call: "error", detail: String(e.message || e) }; }
}
async function alarmWatch(env, lp) {
  if (!env.PUSHOVER_TOKEN) return;
  const al = (await kv.get(env, "alarm")) || {}; const now = Date.now();
  if (!(al.enabled && al.lastFired === lp.date && al.firedAt && al.acked !== lp.date && now - new Date(al.firedAt) < 40 * 60e3)) return;
  const mins = Math.round((now - new Date(al.firedAt)) / 60e3); if (mins < 1) return;
  const rc = al.firedReceipt || al.receipt; let d = null;
  if (rc) { try { const r = await (await fetch(`https://api.pushover.net/1/receipts/${rc}.json?token=${env.PUSHOVER_TOKEN}`)).json(); if (r.status === 1) d = { receipt: rc, acknowledged: !!r.acknowledged, acknowledgedAt: r.acknowledged_at ? new Date(r.acknowledged_at * 1000).toISOString() : null, delivered: !!r.last_delivered_at, deliveredAt: r.last_delivered_at ? new Date(r.last_delivered_at * 1000).toISOString() : null, expired: !!r.expired, device: r.acknowledged_by_device || "", checkedAt: new Date().toISOString() }; } catch {} }
  if (d) { al.delivery = d; if (!al.firedReceipt) al.firedReceipt = rc; }
  if (d?.acknowledged) { al.acked = lp.date; al.ackedAt = d.acknowledgedAt || new Date().toISOString(); al.ackedBy = "pushover"; delete al.snooze; await kv.put(env, "alarm", al); return; }
  if (al.snooze && now < new Date(al.snooze)) { await kv.put(env, "alarm", al); return; }
  const undelivered = d ? !d.delivered : !rc; const stuck = !!d?.delivered && mins >= 5;
  if ((undelivered && mins >= 2) || stuck) {
    if (!al.fallbackAt) { al.fallbackAt = new Date().toISOString(); await healthNote(env, "alarm", { fallback: undelivered ? "undelivered" : "unacknowledged", mins, time: al.time }).catch(() => null); }
    if (!al.called && callConfigured(env)) { al.called = new Date().toISOString(); al.callRes = await alarmCall(env, `Good morning, sir. This is JARVIS. It is ${lp.hm} and your ${al.time} alarm did not reach your phone. Time to get up.`); }
    await webPush(env, { title: "JARVIS: wake up", body: `It's ${lp.hm}. Alarm was ${al.time}, ${mins} min ago${undelivered ? ", and Pushover has not reached the phone" : ""}. Tap I'm up.`, url: HUB_ORIGIN + "/#wake", priority: "alarm", kind: "alarm", tag: "alarm", at: new Date().toISOString() }, { ttl: 120, urgency: "high", topic: "alarm" }).catch(() => null);
    if (!al.resent) {
      al.resent = new Date().toISOString();
      const res = await notify(env, "Wake up", `It's ${lp.hm}. The ${al.time} alarm ${undelivered ? "did not reach this phone" : "is still waiting"}. Tap I'm up.`, { priority: "alarm", tags: "sunrise", url: HUB_ORIGIN + "/#wake", sound: "siren" }).catch(() => []);
      const po = res.find?.((r) => r.pushover != null); if (po?.receipt) al.receipt = po.receipt;
    }
  }
  await kv.put(env, "alarm", al);
}

/* ---------------- competitors: weekly price/package scan ---------------- */
const pageText = (h) => h.replace(/<script[\s\S]*?<\/script>|<style[\s\S]*?<\/style>|<!--[\s\S]*?-->/gi, " ").replace(/<[^>]+>/g, " ").replace(/&nbsp;|&#160;/g, " ").replace(/&amp;/g, "&").replace(/\s+/g, " ").trim();
function priceLines(t) {
  const out = new Set(); const re = /\$\s?\d[\d,]*(?:\.\d{2})?(?:\s?(?:k|K|\+|per\s+\w+|\/\s?\w+))?/g; let m;
  while ((m = re.exec(t))) { const a = Math.max(0, m.index - 70), b = Math.min(t.length, m.index + m[0].length + 50); out.add(t.slice(a, b).trim()); if (out.size > 60) break; }
  return [...out];
}
async function scanCompetitors(env) {
  const comps = (await kv.get(env, "competitors")) || []; if (!comps.length) return [];
  const snaps = (await kv.get(env, "competitor_snaps")) || {}; const changes = (await kv.get(env, "competitor_changes")) || []; const fresh = [];
  for (const c of comps) {
    try {
      const r = await within(fetch(c.url, { headers: { "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36", "accept-language": "en-US,en;q=0.9" }, redirect: "follow" }), 12000, null);
      if (!r || !r.ok) { c.lastError = "HTTP " + (r?.status || "timeout"); continue; }
      const text = pageText(await r.text()); const prices = priceLines(text); const key = c.url;
      const prev = snaps[key]; const now = { at: new Date().toISOString(), prices, words: text.split(" ").length };
      if (prev) {
        const added = prices.filter((x) => !prev.prices.includes(x)), removed = prev.prices.filter((x) => !prices.includes(x));
        const amt = (x) => (x.match(/\$\s?\d[\d,]*/) || [""])[0];
        const addedAmts = added.map(amt), removedAmts = removed.map(amt);
        const realAdded = added.filter((x) => !removedAmts.includes(amt(x))), realRemoved = removed.filter((x) => !addedAmts.includes(amt(x)));
        if (realAdded.length || realRemoved.length) {
          const summary = [realAdded.length ? "new/changed prices: " + realAdded.slice(0, 4).map((x) => "“" + x.slice(0, 90) + "”").join("; ") : "", realRemoved.length ? "no longer shown: " + realRemoved.slice(0, 3).map(amt).join(", ") : ""].filter(Boolean).join(" · ");
          const ch = { at: now.at, label: c.label, url: c.url, business: c.business || "", summary }; changes.unshift(ch); fresh.push(ch);
        }
      }
      snaps[key] = now; c.lastScan = now.at; c.priceCount = prices.length; delete c.lastError;
    } catch (e) { c.lastError = String(e.message || e).slice(0, 80); }
  }
  await kv.put(env, "competitor_snaps", snaps); await kv.put(env, "competitors", comps); await kv.put(env, "competitor_changes", changes.slice(0, 30));
  if (fresh.length) { await flushAlerts(env, fresh.map((ch) => ({ alert: { kind: "watch", text: `Competitor change: ${ch.label}: ${ch.summary}`.slice(0, 300), url: ch.url }, push: { title: "Competitor change: " + ch.label, body: ch.summary.slice(0, 400), opts: { tags: "eyes", url: ch.url } } }))); }
  return fresh;
}

/* ---------------- worker ---------------- */
export default {
  async scheduled(event, env, ctx) {
    await applyHome(env);
    const cron = event.cron || ""; ctx.waitUntil(healthNote(env, "cron", cron));
    if (cron === "* * * * *") { ctx.waitUntil(tickMinute(env, true).catch((e) => console.log("minute", e.message))); return; }
    if (cron.startsWith("*/5")) ctx.waitUntil(runChecks(env).then(() => checkStale(env)).then(() => tripWatch(env)).then(async () => { const t = await kv.get(env, "tick_at"); if (!t || Date.now() - new Date(t) > 90e3) await tickMinute(env); }).then(() => shipWatch(env)).then(() => socialFromLog(env)).then(() => watchMerged(env)).then((w) => w && watchWatch(env, { social: w.social, at: w.at })).catch((e) => console.log("5-min cron", e.message)));   // tickMinute here is only a backstop for a skipped minute cron
    else ctx.waitUntil((async () => {
      await loadCalendar(env, true).catch(() => null);
      await weddingWeather(env).catch(() => null);
      await appStores(env).catch((e) => console.log("app stores", e.message));
      if (localHour(env) === 4) { await dailyReadings(env).catch((e) => console.log("readings", e.message)); await saintOfDay(env).catch((e) => console.log("saint", e.message)); const dowF = new Date().toLocaleDateString("en-US", { timeZone: env.TZ || "America/Chicago", weekday: "short" }); if (dowF === "Sat") { const sun = new Date(Date.now() + 86400e3).toLocaleDateString("en-CA", { timeZone: env.TZ || "America/Chicago" }); await dailyReadings(env, { date: sun }).catch((e) => console.log("vigil readings", e.message)); } }   // ready before the morning brief; Sunday's for the vigil
      await makeFollowups(env).catch((e) => console.log("follow-ups", e.message));
      await observe(env, new Request(HUB_ORIGIN + "/", { cf: {} })).catch((e) => console.log("observe", e.message));
      const dow = new Date().toLocaleDateString("en-US", { timeZone: env.TZ || "America/Chicago", weekday: "short" }), hr = localHour(env);
      if (dow === "Sun" && hr === 20) await scanCompetitors(env).catch((e) => console.log("competitors", e.message));
      if (dow === "Mon" && hr === 6) { const hadWeekly = ((await kv.get(env, "briefs")) || []).some((b) => b.slot === "weekly" && Date.now() - new Date(b.at) < 3 * 86400e3); if (!hadWeekly) { const fake = new Request(HUB_ORIGIN + "/", { cf: {} }); await makeMorning(env, fake, "weekly").catch((e) => pushAlert(env, { kind: "watch", text: "weekly review failed: " + e.message })); } }
      const slot = SLOT_HOURS(env)[localHour(env)];
      const recent = ((await kv.get(env, "briefs")) || []).some((b) => b.slot === slot && Date.now() - new Date(b.at) < 3 * 3600e3); // never two of the same brief in one morning
      if (slot && !recent) {
        const fake = new Request(HUB_ORIGIN + "/", { cf: {} });
        await makeMorning(env, fake, slot).catch(async (e) => { await healthNote(env, "brief", { slot, error: String(e.message).slice(0, 120) }); await pushAlert(env, { kind: "watch", text: slot + " brief failed: " + e.message }); });
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
    if (p === "/sw.js") return new Response(SW_JS, { headers: { "content-type": "application/javascript; charset=utf-8", "cache-control": "no-cache", "service-worker-allowed": "/" } });
    if (p === "/sounds/baroque.mp3") return new Response(baroqueMp3, { headers: { "content-type": "audio/mpeg", "cache-control": "public, max-age=604800" } });
    if (p === "/icon-192.png") return new Response(icon192, { headers: { "content-type": "image/png", "cache-control": "public, max-age=86400" } });
    if (p === "/icon.svg") return new Response(ICON, { headers: { "content-type": "image/svg+xml", "cache-control": "public, max-age=86400" } });

    const who = await authed(request, env);
    if (!who) {
      if (p.startsWith("/api/")) return json({ error: "unauthorized" }, 401);
      return new Response(lockPage(env), { status: 401, headers: { "content-type": "text/html; charset=utf-8" } });
    }
    if (p === "/" || p === "/index.html" || p === "/wall") return new Response(html, { headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" } });

    if (p === "/api/config") return json({ user: who, google: !!env.GOOGLE_CLIENT_ID, brain: !!env.ANTHROPIC_API_KEY, tts: !!env.ELEVENLABS_API_KEY, windy: !!env.WINDY_KEY, pushover: !!(env.PUSHOVER_TOKEN && env.PUSHOVER_USER), call: callConfigured(env) ? (env.ALARM_CALL === "always" ? "always" : "fallback") : false, ntfy: env.NTFY_TOPIC || null, email: !!(env.RESEND_API_KEY && env.ALERT_EMAIL), calendar: !!env.CAL_ICS_URL, home: (await kv.get(env, "home")) || { mode: "auto", key: "tx", tz: env.TZ || "America/Chicago", label: "Texas" }, teams: env.TEAMS || "DAL,NE,TEX,COL,BOS,ARI", tz: env.TZ || "America/Chicago", briefHours: SLOT_HOURS(env), build: BUILD });
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
    if (p === "/api/tts" && (request.method === "POST" || request.method === "GET")) return tts(request, env);
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
      else { al.acked = lp.date; al.ackedAt = new Date().toISOString(); al.ackedBy = b.action === "wake" ? "page" : b.action || "page"; delete al.snooze; for (const rc of new Set([al.receipt, al.firedReceipt].filter(Boolean))) if (env.PUSHOVER_TOKEN) ctx.waitUntil(fetch(`https://api.pushover.net/1/receipts/${rc}/cancel.json`, { method: "POST", body: new URLSearchParams({ token: env.PUSHOVER_TOKEN }) }).catch(() => null)); delete al.receipt; }
      await kv.put(env, "alarm", al); return json({ ok: true, acked: al.acked || null, snooze: al.snooze || null });
    }
    if (p === "/api/push/vapid") return json({ key: (await vapidKeys(env)).pub, subs: (await listSubs(env)).map((s) => ({ ua: s.ua, label: s.label, at: s.at, endpoint: s.endpoint.slice(0, 48) })) });
    if (p === "/api/push/subscribe" && request.method === "POST") { const b = await request.json(); try { const n = await saveSub(env, b.subscription, { ua: request.headers.get("user-agent"), label: b.label }); return json({ ok: true, subs: n }); } catch (e) { return json({ error: e.message }, 400); } }
    if (p === "/api/push/unsubscribe" && request.method === "POST") { const b = await request.json(); return json({ ok: true, subs: await dropSub(env, b.endpoint) }); }
    if (p === "/api/push/log") return json((await kv.get(env, "push_log")) || []);
    if (p === "/api/alarm/call" && request.method === "POST") { const r = await alarmCall(env, "This is JARVIS. This is a test of the wake-up call. Good morning, sir."); return json(r, r.call === "unconfigured" ? 404 : 200); }
    if (p === "/api/alarm/receipt") { const al = (await kv.get(env, "alarm")) || {}; const id = url.searchParams.get("id") || al.firedReceipt || al.receipt; if (!id || !env.PUSHOVER_TOKEN) return json({ error: "no receipt" }, 404); try { const r = await (await fetch(`https://api.pushover.net/1/receipts/${id}.json?token=${env.PUSHOVER_TOKEN}`)).json(); const t = (s) => s ? new Date(s * 1000).toISOString() : null; return json({ id, ...r, acknowledged_at: t(r.acknowledged_at), last_delivered_at: t(r.last_delivered_at), expires_at: t(r.expires_at), delivery: al.delivery || null }); } catch (e) { return json({ error: e.message }, 502); } }
    if (p === "/api/push/sounds") { try { const s = await (await fetch("https://api.pushover.net/1/sounds.json?token=" + env.PUSHOVER_TOKEN)).json(); return json({ baroque: !!s?.sounds?.baroque, custom: Object.keys(s?.sounds || {}).filter((k) => !PUSHOVER_BUILTIN.includes(k)) }); } catch (e) { return json({ error: String(e.message || e) }, 502); } }
    if (p === "/api/push/test" && request.method === "POST") {
      // what each channel says right now: Pushover's registered devices, and a real test push to every channel
      const b = await request.json().catch(() => ({})); const out = {};
      if (env.PUSHOVER_TOKEN && env.PUSHOVER_USER) { try { const r = await fetch("https://api.pushover.net/1/users/validate.json", { method: "POST", body: new URLSearchParams({ token: env.PUSHOVER_TOKEN, user: env.PUSHOVER_USER }) }); out.pushoverDevices = await r.json(); } catch (e) { out.pushoverDevices = { error: e.message }; } }
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
      const raw = await request.json(); const q = (await kv.get(env, "queue")) || [];
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
