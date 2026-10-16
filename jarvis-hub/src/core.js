// JARVIS hub: Shared config and helpers: the business list, KV access, time, fetch with a deadline, caching, the alert list and the health ledger.
import { notify } from "./alarm.js";

export const SITES = [
  { id: "atavia", name: "Atavia Weddings", url: "https://ataviaweddings.com" },
  { id: "es", name: "Elizabeth Scott", url: "https://elizabethscottweddings.com" },
  { id: "lazo", name: "Lazo", url: "https://meetlazo.com" },
  { id: "roven", name: "Roven HR", url: "https://rovenhr.com" },
  { id: "lr", name: "LeaseReputation", url: "https://leasereputation.com" },
];
export const BIZ_NAME = Object.fromEntries(SITES.map((s) => [s.id, s.name]));
export const STATE_KEYS = ["brief", "webcams", "notes", "place", "metrics", "alerts", "memory", "queue", "calendar", "morning", "traffic", "tickers", "wxdays", "sports", "briefs", "stale", "inbox", "decisions", "home", "flights", "watch", "followups", "trips", "apps", "playbook", "competitors", "competitor_changes", "reminders", "alarm", "social_log", "ship_watch"];
export const UA = "jarvis-hub (jesse@briskhealth.com)";
export const MODEL = "claude-opus-5-5";
export const HUB_ORIGIN = "https://jarvis-hub.floral-credit-e4f0.workers.dev";

/* ---------------- helpers ---------------- */
export const json = (data, status = 200, extra = {}) =>
  new Response(JSON.stringify(data), { status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", ...extra } });
export const cookies = (req) => Object.fromEntries((req.headers.get("cookie") || "").split(/;\s*/).filter(Boolean).map((c) => { const i = c.indexOf("="); return [c.slice(0, i), c.slice(i + 1)]; }));
export const kv = { get: (env, k) => env.HUB.get(k, "json"), put: (env, k, v) => env.HUB.put(k, JSON.stringify(v)) };
export const localTime = (env, d = new Date(), opts = { dateStyle: "full", timeStyle: "short" }) => d.toLocaleString("en-US", { timeZone: env.TZ || "America/Chicago", ...opts });
export const localHour = (env) => +new Date().toLocaleString("en-US", { timeZone: env.TZ || "America/Chicago", hour: "numeric", hourCycle: "h23" });
export const uid = () => Math.random().toString(36).slice(2, 10);
// every outside call gets a deadline: one hung provider must not stall the minute cron (alarm path) or a whole tick
export const tfetch = (u, opts = {}, ms = 8000) => fetch(u, { ...opts, signal: opts.signal || AbortSignal.timeout(ms) });

export async function pushAlert(env, alert) {
  const list = (await kv.get(env, "alerts")) || [];
  list.unshift({ ...alert, at: new Date().toISOString(), id: uid() });
  await kv.put(env, "alerts", list.slice(0, 80));
}


/* ---------------- Gmail bridges (Apps Script in each account) ---------------- */
export const BIZ_LABEL = { atavia: "Atavia", es: "Elizabeth Scott", lazo: "Lazo", roven: "Roven", lr: "LeaseReputation", brisk: "Brisk", other: "Other" };

export const within = (p, ms, fallback = null) => Promise.race([p.catch(() => fallback), new Promise((r) => setTimeout(() => r(fallback), ms))]);
export async function cached(env, key, ttlMs, fn) {
  const c = await kv.get(env, "cache_" + key);
  if (c && Date.now() - c.t < ttlMs) return c.v;
  const v = await within(fn(), 3000, c?.v ?? null);
  if (v) await kv.put(env, "cache_" + key, { t: Date.now(), v });
  return v;
}

/* ---------------- watchtower: payments, social, search, app stores, follow-ups, trips ---------------- */
export const fmtUsd = (n) => "$" + Math.round(n || 0).toLocaleString();
export const payWhy = (e) => (String(e || "").match(/"message":"([^"]+)"/) || [])[1] || String(e || "").slice(0, 100);
export const siteName = (s) => String(s || "").replace(/^sc-domain:|^https?:\/\/|\/$/g, "");

// KV is eventually consistent: read-modify-write twice in a row can lose the first write.
// Watchers therefore collect their alerts and "already told him" keys and write each list once.
export async function onceStore(env) {
  const seen = (await kv.get(env, "once")) || {}; let dirty = false;
  return {
    fresh(key, ttlMs) { const now = Date.now(); if (seen[key] && now - seen[key] < ttlMs) return false; seen[key] = now; dirty = true; return true; },
    async save() { if (!dirty) return; const now = Date.now(); for (const k of Object.keys(seen)) if (now - seen[k] > 90 * 86400e3) delete seen[k]; await kv.put(env, "once", seen); },
  };
}
export async function flushAlerts(env, out) {
  if (!out.length) return;
  const list = (await kv.get(env, "alerts")) || [];
  const at = new Date().toISOString();
  list.unshift(...out.map((x) => ({ ...x.alert, at, id: uid() })).reverse());
  await kv.put(env, "alerts", list.slice(0, 80));
  await Promise.all(out.filter((x) => x.push).map((x) => notify(env, x.push.title, x.push.body, x.push.opts || {}).catch(() => null)));
}

/* ---------------- health ledger: JARVIS watching JARVIS ---------------- */
// Three crons can tick in the same second; a shared read-modify-write key lost most of their writes, so each cron
// owns one small key (health_cron_<slug>, single writer) and the other events share health_events (low volume).
export const cronSlug = (c) => String(c || "").replace(/[^a-z0-9]+/gi, "_");
export async function healthNote(env, kind, data) {
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
