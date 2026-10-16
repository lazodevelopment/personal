// JARVIS hub: Inbox: the Gmail bridges, triage, marketplace intake checks, email actions and drafted follow-ups.
import Anthropic from "@anthropic-ai/sdk";
import { BIZ_NAME, MODEL, HUB_ORIGIN, json, kv, uid, tfetch, pushAlert, BIZ_LABEL, onceStore, flushAlerts, healthNote } from "./core.js";
import { notify } from "./alarm.js";

export const isBot = (addr) => /no-?reply|donotreply|do-not-reply|notifications?@|mailer-daemon|postmaster|alerts?@/i.test(String(addr || ""));

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
export async function intakeReport(env, b) {
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

// the combined inbox (KV `inbox`, read by the panel, briefs and hooks) is rebuilt from every account's own key
async function rebuildInbox(env, account, mine) {
  const prev = (await kv.get(env, "inbox")) || { accounts: {} };
  const names = [...new Set([...Object.keys(prev.accounts || {}), ...Object.keys((await kv.get(env, "inbox_hooks")) || {}), account])];
  const accounts = {};
  await Promise.all(names.map(async (a) => { const v = a === account ? mine : (await kv.get(env, "inbox_acct_" + a)) || prev.accounts?.[a]; if (v) accounts[a] = v; }));
  const inbox = { accounts }; await kv.put(env, "inbox", inbox); return inbox;
}

export async function ingestInbox(env, body, ctx) {
  const account = String(body.account || "").toLowerCase(); if (!account) return json({ error: "no account" }, 400);
  const classKey = "inbox_class_" + account;
  const cache = (await kv.get(env, classKey)) || (await kv.get(env, "inbox_class")) || {};   // falls back to the old shared cache once
  const items = (body.items || []).slice(0, 60);
  // a failed triage is cached as {failed, retryAt} so a broken thread is retried every 30 min, not re-sent to Claude on every sync
  const fresh = items.filter((m) => { const c = cache[m.threadId]; if (!c || c.date !== m.date) return true; return c.failed && Date.now() > (c.retryAt || 0); });
  let classes = {}; try { classes = await triage(env, fresh); } catch (e) { console.log("triage failed", e.message); }
  for (const m of fresh) { const c = classes[m.threadId]; cache[m.threadId] = c ? { date: m.date, needs_reply: !!c.needs_reply, summary: c.summary, priority: c.priority, kind: c.kind } : { date: m.date, failed: true, retryAt: Date.now() + 30 * 60e3 }; }
  const keep = Object.fromEntries(Object.entries(cache).filter(([, v]) => Date.now() - new Date(v.date) < 14 * 86400e3)); await kv.put(env, classKey, keep);
  for (const k of Object.keys(keep)) if (keep[k].failed) delete keep[k];   // placeholders carry no labels
  // marketplace inquiry notices (Zola, The Knot) are answered by the intake script: never NEEDS REPLY, flagged `intake` instead
  const mine = { business: body.business || "other", at: new Date().toISOString(), items: items.map((m) => ({ ...m, ...(keep[m.threadId] ? { needs_reply: keep[m.threadId].needs_reply && !m.lastFromMe, summary: keep[m.threadId].summary, priority: keep[m.threadId].priority, kind: keep[m.threadId].kind } : {}), ...(marketLead(m, body.business) ? { needs_reply: false, kind: "lead", intake: true, ...leadSummary(m) } : {}) })) };
  await kv.put(env, "inbox_acct_" + account, mine);
  const inbox = await rebuildInbox(env, account, mine);
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
    // The URL is adopted only when the account has none yet: a sync can never re-point an inbox's actions somewhere else (2026-10-16 audit).
    const hooks = (await kv.get(env, "inbox_hooks")) || {}; const cur = hooks[account] || {};
    const reported = /^https:\/\/script\.google\.com\/macros\/s\/[^/]+\/exec$/.test(body.hookUrl || "") ? body.hookUrl : null;
    hooks[account] = { ...cur, url: cur.url || reported || null, secret: body.secret, business: body.business || "other", at: new Date().toISOString() };
    await kv.put(env, "inbox_hooks", hooks);
  }
  // the Inbox panel, the nudges and the briefs all read `brief`; rebuild it from every bridged account
  const all = Object.entries(inbox.accounts).flatMap(([acct, a]) => a.items.map((m) => ({ business: a.business, account: acct, threadId: m.threadId, from: m.from.replace(/<.*>/, "").trim() || m.fromEmail, fromEmail: m.fromEmail || "", when: new Date(m.date).toLocaleString("en-US", { timeZone: env.TZ || "America/Chicago", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }), received: m.date, subject: m.subject, snippet: m.summary || m.snippet?.slice(0, 120) || "", url: m.link, needs_reply: !!m.needs_reply, unread: !!m.unread, priority: m.priority || 3, kind: m.kind || "", intake: !!m.intake })));
  all.sort((a, b) => (b.needs_reply - a.needs_reply) || (a.priority - b.priority) || b.received.localeCompare(a.received));
  const needs = all.filter((m) => m.needs_reply).length, unread = all.filter((m) => m.unread).length;
  await kv.put(env, "brief", { at: new Date().toISOString(), source: "bridge", accounts: Object.keys(inbox.accounts), note: all.length ? `${unread} unread across ${Object.keys(inbox.accounts).length} inbox${Object.keys(inbox.accounts).length > 1 ? "es" : ""}, ${needs} need${needs === 1 ? "s" : ""} a reply` : "All inboxes clear.", items: all.slice(0, 40) });
  // announce new mail from real people that matters (leads, clients, bookings, payments): push now, and any open page says it
  try {
    const outM = []; const bizName = BIZ_NAME[body.business] || BIZ_LABEL[body.business] || body.business || "";
    for (const m of fresh) { const c = keep[m.threadId]; const key = m.threadId + "|" + m.date;
      if (!c || m.lastFromMe || isBot(m.fromEmail) || !["lead", "client", "booking", "payment"].includes(c.kind) || (c.priority || 3) > 2 || Date.now() - new Date(m.date) > 3 * 3600e3) continue;
      if (await env.HUB.get("told_" + key)) continue; await env.HUB.put("told_" + key, "1", { expirationTtl: 7 * 86400 }); const who = String(m.from || "").replace(/<.*>/, "").trim() || m.fromEmail; const auto = marketLead(m, body.business);
      outM.push({ alert: { kind: "mail", text: `New ${c.kind === "lead" ? "lead" : "email"} for ${bizName} from ${who}: ${m.subject}. ${c.summary || ""}${auto ? " The intake script answers this one; I will confirm the reply went out." : ""}`.trim(), url: m.link }, push: { title: `${bizName}: new ${c.kind}`, body: `${who}: ${m.subject}
${c.summary || m.snippet || ""}`, opts: { priority: c.priority === 1 ? "high" : "default", tags: "email", url: HUB_ORIGIN + "/#mail" } } });
    }
    if (outM.length) await flushAlerts(env, outM);
  } catch (e) { console.log("mail announce", e.message); }
  const quick = fresh.filter((m) => { const c = keep[m.threadId]; return c?.needs_reply && !m.lastFromMe && ["lead", "client", "booking"].includes(c.kind) && !isBot(m.fromEmail) && !marketLead(m, body.business) && Date.now() - new Date(m.date) < 6 * 3600e3; }).map((m) => m.threadId);
  if (quick.length && ctx) ctx.waitUntil(makeFollowups(env, { minAgeH: 0, onlyThreads: quick, first: true }).catch((e) => console.log("first reply", e.message)));
  if (ctx) ctx.waitUntil(prefetchThreads(env, account, mine.items).catch((e) => console.log("prefetch", e.message)));
  if (ctx && INTAKE[body.business]) ctx.waitUntil(verifyIntake(env, account, body.business, mine.items).catch((e) => console.log("intake", e.message)));
  return json({ ok: true, account, items: items.length, triaged: fresh.length, hook: !!body.hookUrl, drafting: quick.length });
}

async function bridgeCall(env, account, payload) {
  const hooks = (await kv.get(env, "inbox_hooks")) || {};
  const hook = hooks[String(account || "").toLowerCase()];
  if (!hook?.url) return { error: "no Gmail bridge with actions for " + account };
  let out;
  for (let attempt = 0; attempt < 3; attempt++) {
    if (attempt) await new Promise((r) => setTimeout(r, 1200 * attempt));
    try { const r = await tfetch(hook.url, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ secret: hook.secret, ...payload }), redirect: "follow" }, 25000); const t = await r.text(); try { out = JSON.parse(t); } catch { out = { error: "bridge returned " + r.status + (t.includes("<") ? " (update the bridge script and deploy a new version)" : ""), transient: true }; } } catch (e) { out = { error: "bridge unreachable: " + e.message, transient: true }; }
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
export async function threadCached(env, account, threadId, date, fresh = false) {
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
export async function emailAction(env, item) {
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
    try { const r = await tfetch(hook.url, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ secret: hook.secret, action, threadId: p.threadId, body: p.body, to: p.to, subject: p.subject, ...(attachments.length ? { attachments } : {}) }), redirect: "follow" }, 25000); status = r.status; const txt = await r.text(); j = {}; try { j = JSON.parse(txt); } catch {} } catch (e) { j = { error: "bridge unreachable: " + e.message }; }
    if (j.ok || (j.error && !/^bridge /.test(j.error))) break;   // a real answer (success or a script-level error) ends the retries; 404/HTML pages do not
    if (!j.error) j = { error: "bridge " + status };
  }
  if (j.error) await healthNote(env, "bridge", { account: hook.url.slice(-24), error: String(j.error).slice(0, 120) });
  if (sends && !j.ok && /^bridge /.test(j.error || "")) return { ok: false, message: "bridge did not confirm the send; check the Sent folder before retrying" };
  return j.ok ? { ok: true, message: j.did || action } : { ok: false, message: j.error || ("bridge " + status) };
}
// a reply goes to someone already in the thread; a new email only to an address Jesse has corresponded with, unless the card's second tap okays a new address
export async function knownCorrespondent(env, to) {
  const want = String(to || "").toLowerCase().match(/[^\s<>"',;]+@[^\s<>"',;]+/g) || []; if (!want.length) return false;
  const brief = (await kv.get(env, "brief")) || {}; const inbox = (await kv.get(env, "inbox")) || { accounts: {} };
  const seen = new Set([...(brief.items || []).map((m) => String(m.fromEmail || "").toLowerCase()), ...Object.values(inbox.accounts).flatMap((a) => (a.items || []).flatMap((m) => [String(m.fromEmail || "").toLowerCase(), ...String(m.to || "").toLowerCase().split(/[,;\s]+/)]))]);
  return want.every((a) => seen.has(a));
}

// leads, clients and bookings left unanswered for a day: JARVIS drafts the reply, Jesse sends it from Decisions
const DEFAULT_PLAYBOOK = { atavia: "Wedding films. Warm and confident. Ask for the date and venue if missing. Offer a 15-minute call. Do not quote prices unless the playbook lists them.", es: "Wedding films. Warm and personal. Ask for the date and venue if missing. Offer a 15-minute call. Do not quote prices unless the playbook lists them.", lazo: "Wedding planner app and vendor directory. Friendly, short. Point couples to the app, vendors to claiming their listing.", roven: "Hiring platform. Professional, concise.", lr: "Apartment reviews. Professional, concise.", brisk: "Professional, concise." };
export async function makeFollowups(env, { minAgeH = 24, dry = false, onlyThreads = null, first = false } = {}) {
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
      model: MODEL, max_tokens: 1500, betas: ["server-side-fallback-2026-07-01"], fallbacks: "default", output_config: { effort: "low" },
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
