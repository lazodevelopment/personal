// JARVIS hub: Notifications (Pushover, web push), reminders and the wake-up alarm (minute tick, receipts, phone call).
import { webPush } from "./webpush.js";
import { HUB_ORIGIN, kv, uid, tfetch, flushAlerts, healthNote } from "./core.js";

/* ---------------- notifications ---------------- */
export const PUSHOVER_BUILTIN = ["pushover","bike","bugle","cashregister","classical","cosmic","falling","gamelan","incoming","intermission","magic","mechanical","pianobar","siren","spacealarm","tugboat","alien","climb","persistent","echo","updown","vibrate","none"];
export async function notify(env, title, body, { priority = "default", tags = "", url = "", sound = "" } = {}) {
  const out = [];
  if (env.PUSHOVER_TOKEN && env.PUSHOVER_USER) {
    const pr = priority === "alarm" ? "2" : priority === "urgent" || priority === "reminder" ? "1" : priority === "high" ? "0" : "-1";
    // the alarm plays a custom Pushover sound ("baroque" first, else any uploaded one; his is named "Alarm") (Vivaldi clip, jarvis-hub/sounds/baroque.mp3) once it's uploaded to Pushover; spacealarm until then
    let alarmSound = "spacealarm";
    if (priority === "alarm" && !sound) { try { const s = await (await tfetch("https://api.pushover.net/1/sounds.json?token=" + env.PUSHOVER_TOKEN)).json(); alarmSound = s?.sounds?.baroque ? "baroque" : Object.keys(s?.sounds || {}).find((k) => !PUSHOVER_BUILTIN.includes(k)) || alarmSound; } catch {} }
    const form = new URLSearchParams({ token: env.PUSHOVER_TOKEN, user: env.PUSHOVER_USER, title: "JARVIS: " + title, message: body, priority: pr, sound: sound || (priority === "alarm" ? alarmSound :priority === "reminder" ? "incoming" : priority === "urgent" ? "siren" : "pushover"), ...(priority === "alarm" ? { retry: "60", expire: "1800" } : {}), ...(url ? { url, url_title: "Open JARVIS" } : {}) });
    out.push(tfetch("https://api.pushover.net/1/messages.json", { method: "POST", body: form }).then(async (r) => { const t = await r.text(); let j = null; try { j = JSON.parse(t); } catch {} return { pushover: r.status, receipt: j?.receipt, sound: form.get("sound"), detail: r.ok ? undefined : t.slice(0, 200) }; }).catch((e) => ({ pushover: "error", detail: String(e.message || e) })));
  }
  // the phone's own browser (Chrome on Android, etc.) once it has subscribed on the Radio panel: alarms, reminders and anything urgent/high
  // alarms go through Pushover alone when it's configured: the Chrome notification's beep competed with the Vivaldi alarm sound (2026-10-09)
  if (["reminder", "urgent", "high"].includes(priority) || (priority === "alarm" && !(env.PUSHOVER_TOKEN && env.PUSHOVER_USER))) {
    out.push(webPush(env, { title: "JARVIS: " + title, body, url, priority, kind: priority === "alarm" ? "alarm" : "", tag: priority === "alarm" ? "alarm" : "", at: new Date().toISOString() }, { ttl: priority === "alarm" ? 1800 : 3600, urgency: "high", topic: priority === "alarm" ? "alarm" : "" }).then((r) => ({ webpush: r })).catch((e) => ({ webpush: "error", detail: String(e.message || e) })));
  }
  const res = await Promise.all(out);
  // keep the last 40 answers so "did the alarm actually go out?" has an answer (/api/push/log, Radio panel)
  try { const log = (await kv.get(env, "push_log")) || []; log.unshift({ at: new Date().toISOString(), title, priority, res }); await kv.put(env, "push_log", log.slice(0, 40)); } catch {}
  if (priority === "alarm") { try { const po = res.find((r) => r.pushover != null); if (po?.receipt) { const al = (await kv.get(env, "alarm")) || {}; al.receipt = po.receipt; await kv.put(env, "alarm", al); } } catch {} }
  return res;
}

/* ---------------- reminders and the wake-up alarm (server side, every minute) ---------------- */
// "2026-10-05T07:30" in the home zone -> a real instant
function zonedToUtc(local, tz) {
  const m = String(local).match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/); if (!m) return null;
  const guess = Date.UTC(+m[1], m[2] - 1, +m[3], +m[4], +m[5]);
  const offAt = (t) => { const p = new Intl.DateTimeFormat("en-US", { timeZone: tz, hourCycle: "h23", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }).formatToParts(new Date(t)); const g = (k) => +p.find((x) => x.type === k).value; return Date.UTC(g("year"), g("month") - 1, g("day"), g("hour"), g("minute")) - t; };
  let t = guess - offAt(guess); t = guess - offAt(t); return new Date(t);
}
export const localParts = (env, d = new Date()) => { const tz = env.TZ || "America/Chicago"; const p = new Intl.DateTimeFormat("en-US", { timeZone: tz, hourCycle: "h23", weekday: "short", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }).formatToParts(d); const g = (k) => p.find((x) => x.type === k)?.value; return { date: `${g("year")}-${g("month")}-${g("day")}`, hm: `${g("hour")}:${g("minute")}`, dow: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].indexOf(g("weekday")) }; };
const toMin = (hm) => { const m = String(hm || "").match(/^(\d{1,2}):(\d{2})$/); return m ? +m[1] * 60 + +m[2] : null; };
// (re)configuring the alarm after today's time has passed counts today as handled: it neither fires late nor reports "missed" until tomorrow
export function alarmToday(env, al) {
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
export async function addReminder(env, { text, when, repeat = "none" }) {
  const tz = env.TZ || "America/Chicago"; const at = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$/.test(when) ? new Date(when) : zonedToUtc(when, tz);
  if (!text || !at || isNaN(at)) return { error: "need text and a time like 2026-10-05 15:00" };
  const list = (await kv.get(env, "reminders")) || []; const r = { id: uid(), text: String(text).slice(0, 300), at: at.toISOString(), repeat: ["daily", "weekdays", "weekly"].includes(repeat) ? repeat : "none", created: new Date().toISOString() };
  list.push(r); list.sort((a, b) => a.at.localeCompare(b.at)); await kv.put(env, "reminders", list.slice(0, 200));
  return { ...r, local: at.toLocaleString("en-US", { timeZone: tz, weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) };
}
export async function tickMinute(env, fromMinuteCron = false) {
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
export const callConfigured = (env) => !!(env.TWILIO_SID && env.TWILIO_TOKEN && env.TWILIO_FROM && env.ALARM_PHONE);
export async function alarmCall(env, text) {
  if (!callConfigured(env)) return { call: "unconfigured" };
  const say = `<Say voice="Polly.Brian">${xmlEsc(text)}</Say>`; const twiml = `<Response>${say}<Pause length="1"/>${say}<Pause length="1"/>${say}</Response>`;
  try {
    const r = await tfetch(`https://api.twilio.com/2010-04-01/Accounts/${env.TWILIO_SID}/Calls.json`, { method: "POST", headers: { authorization: "Basic " + btoa(env.TWILIO_SID + ":" + env.TWILIO_TOKEN) }, body: new URLSearchParams({ To: env.ALARM_PHONE, From: env.TWILIO_FROM, Twiml: twiml, Timeout: "45" }) });
    const t = await r.text(); let j = null; try { j = JSON.parse(t); } catch {}
    const out = { call: r.status, sid: j?.sid, detail: r.ok ? undefined : t.slice(0, 200) };
    try { const log = (await kv.get(env, "push_log")) || []; log.unshift({ at: new Date().toISOString(), title: "Phone call: " + text.slice(0, 40), priority: "alarm", res: [out] }); await kv.put(env, "push_log", log.slice(0, 40)); } catch {}
    return out;
  } catch (e) { return { call: "error", detail: String(e.message || e) }; }
}
// "I'm up" / snooze live in their own key (alarm_ack, written only by /api/alarm/ack), so alarmWatch's read-modify-write of
// `alarm` can never wipe a tap that landed while it was waiting on Pushover
async function applyAck(env, al, lp) {
  const a = await kv.get(env, "alarm_ack");
  if (a?.date !== lp.date) return al;
  if (a.action === "snooze") { if (!al.snooze || new Date(a.snooze) > new Date(al.snooze)) { al.snooze = a.snooze; delete al.acked; } }
  else { al.acked = lp.date; al.ackedAt = a.at; al.ackedBy = a.by; delete al.snooze; }
  return al;
}
async function alarmWatch(env, lp) {
  if (!env.PUSHOVER_TOKEN) return;
  const al = await applyAck(env, (await kv.get(env, "alarm")) || {}, lp); const now = Date.now();
  if (!(al.enabled && al.lastFired === lp.date && al.firedAt && al.acked !== lp.date && now - new Date(al.firedAt) < 40 * 60e3)) return;
  const mins = Math.round((now - new Date(al.firedAt)) / 60e3); if (mins < 1) return;
  const rc = al.firedReceipt || al.receipt; let d = null;
  if (rc) { try { const r = await (await tfetch(`https://api.pushover.net/1/receipts/${rc}.json?token=${env.PUSHOVER_TOKEN}`)).json(); if (r.status === 1) d = { receipt: rc, acknowledged: !!r.acknowledged, acknowledgedAt: r.acknowledged_at ? new Date(r.acknowledged_at * 1000).toISOString() : null, delivered: !!r.last_delivered_at, deliveredAt: r.last_delivered_at ? new Date(r.last_delivered_at * 1000).toISOString() : null, expired: !!r.expired, device: r.acknowledged_by_device || "", checkedAt: new Date().toISOString() }; } catch {} }
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
  await kv.put(env, "alarm", await applyAck(env, al, lp));
}
