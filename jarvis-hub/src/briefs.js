// JARVIS hub: Briefs (morning / afternoon / evening / weekly) and the hourly observer.
import Anthropic from "@anthropic-ai/sdk";
import { MODEL, HUB_ORIGIN, kv, localHour, uid, pushAlert, flushAlerts, healthNote } from "./core.js";
import { notify } from "./alarm.js";
import { buildContext, BRAIN_SYSTEM, elevenlabs } from "./brain.js";

/* ---------------- briefs: morning / afternoon / evening ---------------- */
export const SLOT_PROMPTS = {
  morning: "This is the MORNING brief. About 220 to 300 words, two minutes read aloud. Greeting with the date and today's weather in one breath; what needs his attention today (unanswered leads, alerts, anything slow or down, anything JARVIS noticed); each business in a sentence or two with the numbers that matter and the week-over-week direction; today's and this week's weddings with their venue weather; his teams' games today and last night's results; one line on the markets and the top local headline if it matters; finish with one dry, encouraging line.",
  afternoon: "This is the AFTERNOON brief. About 150 to 220 words. Only what is NEW since the morning brief: fresh leads or bookings, web traffic so far today across the sites, actions completed, alerts, any site that got slow, scores of games in progress or finished today, markets at midday, and anything that changed in the forecast for tonight or this week's weddings. Do not repeat the morning numbers or re-describe the day's weather unless it changed. If genuinely nothing changed, say so in two sentences.",
  weekly: "This is the MONDAY WEEKLY REVIEW. About 350 to 450 words, five minutes read aloud. For each business in turn: last week against the week before (revenue or cash in, bookings or sign-ups, leads, web traffic, search clicks), and against the same week last year where YEAR-AGO figures exist (say plainly when there is no prior year yet). Then the money picture: the 90-day cash forecast by week, any thin weeks, and anything past due. Then the competitor changes from the last scan, if any. Then one short paragraph on JARVIS's own reliability from the JARVIS HEALTH line: missed cron runs, feed stalls, bridge errors, failed briefs; say plainly if it was a clean week. Finish with exactly one thing to fix this week for each business, stated as an instruction. Flowing prose, no lists, no headers.",
  evening: "This is the EVENING brief. About 180 to 250 words. Wrap the day: what came in today across the businesses (leads, bookings, sign-ups, revenue if any), today's final web traffic, final scores and tomorrow's games, how the markets closed; then look ahead: tomorrow's weather, tomorrow's and the weekend's weddings with venue weather, balances due, anything still unresolved that he should sleep on or handle first thing. Do not repeat what the morning or afternoon brief already said unless it resolved.",
};
export const SLOT_HOURS = (env) => Object.fromEntries((env.BRIEF_HOURS || "5:morning,12:afternoon,18:evening").split(",").map((x) => { const [h, slot] = x.split(":"); return [+h, slot || "morning"]; }));
const slotNow = (env) => { const h = localHour(env); return h < 11 ? "morning" : h < 17 ? "afternoon" : "evening"; };

// the slot's brief, once: the hourly tick runs it, and the 5-minute cron catches up if that tick was skipped or failed
export async function briefIfDue(env) {
  const slot = SLOT_HOURS(env)[localHour(env)]; if (!slot) return;
  const recent = ((await kv.get(env, "briefs")) || []).some((b) => b.slot === slot && Date.now() - new Date(b.at) < 3 * 3600e3); // never two of the same brief in one morning
  if (recent || (await env.HUB.get("brief_lock_" + slot))) return;
  await env.HUB.put("brief_lock_" + slot, new Date().toISOString(), { expirationTtl: 1800 });
  const fake = new Request(HUB_ORIGIN + "/", { cf: {} });
  await makeMorning(env, fake, slot).catch(async (e) => { await healthNote(env, "brief", { slot, error: String(e.message).slice(0, 120) }); await pushAlert(env, { kind: "watch", text: slot + " brief failed: " + e.message }); });
}
export async function makeMorning(env, request, slot) {
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

/* ---------------- the observer: one unprompted remark an hour, only when something deserves it ---------------- */
export async function observe(env, request, { force = false } = {}) {
  if (!env.ANTHROPIC_API_KEY) return null;
  const h = localHour(env); if (!force && (h < 8 || h > 20)) return null;
  const prev = (await kv.get(env, "observations")) || [];
  const client = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY });
  const context = await buildContext(env, request);
  const said = prev.filter((o) => Date.now() - new Date(o.at) < 36 * 3600e3).map((o) => `${o.at.slice(5, 16)}: ${o.text}`).join("\n");
  const r = await client.beta.messages.create({
    model: MODEL, max_tokens: 2000, betas: ["server-side-fallback-2026-07-01"], fallbacks: "default", output_config: { effort: "medium" },
    system: BRAIN_SYSTEM + `\nYou are keeping an eye on things between conversations. Decide whether there is ONE thing worth saying to Jesse right now that he has not been told (see ALREADY SAID). Worth saying: a lead or client email that arrived and is still unanswered; a payment that failed or came in; a site down or slow; a feed that stopped; weather turning bad before this week's wedding; a final score for one of his teams; a competitor change; a reminder of something he said he would do (NOTES, MEMORY); an app review result; a search traffic jump or drop; the Cox or any balance retry outcome. Not worth saying: routine numbers, anything in ALREADY SAID or the latest brief, generic encouragement, weather small talk. If nothing qualifies reply with exactly NOTHING. Otherwise reply with one or two spoken sentences, specific, with the number or name, no preamble.`,
    messages: [{ role: "user", content: `ALREADY SAID (last 36 h):\n${said || "(nothing yet today)"}\n\nLIVE CONTEXT:\n${context}` }],
  });
  const text = r.content.filter((b) => b.type === "text").map((b) => b.text).join("").trim();
  if (!text || /^nothing\b/i.test(text)) return null;
  const o = { at: new Date().toISOString(), text: text.slice(0, 500) }; prev.unshift(o); await kv.put(env, "observations", prev.slice(0, 40));
  await flushAlerts(env, [{ alert: { kind: "obs", text: o.text }, push: { title: "JARVIS", body: o.text, opts: { priority: "default", tags: "speech_balloon", sound: "none" } } }]);
  return o;
}
