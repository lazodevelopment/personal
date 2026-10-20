// JARVIS hub: Watchfulness: site checks, metric/decision/watch-feed alerts, app stores, stale feeds, health report, competitors.
import { SITES, BIZ_NAME, UA, HUB_ORIGIN, kv, localHour, pushAlert, within, fmtUsd, payWhy, siteName, onceStore, flushAlerts, cronSlug, healthNote } from "./core.js";
import { notify } from "./alarm.js";
import { isBot } from "./inbox.js";

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
export async function runChecks(env) {
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
export async function watchMetrics(env, next) {
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
export async function watchDecisions(env, dec) {
  const seen = (await kv.get(env, "decisions_seen")) || {}; const now = Date.now(); let changed = false;
  for (const it of dec.items || []) {
    if (seen[it.id]) continue; seen[it.id] = now; changed = true;
    const title = it.kind === "lazo_claim" ? "Lazo claim to review" : it.kind === "lazo_listing" ? "Lazo listing request to review" : it.kind === "roven_approve_job" ? "Roven job to review" : "Roven employer to review";
    const label = String(it.label || "").replace(/^[^:]+:\s*/, "");
    await pushAlert(env, { kind: "watch", text: `${title}: ${label}` });
    await notify(env, title, label + "\nOpen JARVIS → Decisions to approve or reject.", { priority: "high", tags: "ballot_box_with_check", url: HUB_ORIGIN + "/#decisions" });
  }
  for (const id of Object.keys(seen)) if (now - seen[id] > 30 * 86400e3) { delete seen[id]; changed = true; }
  if (changed) await kv.put(env, "decisions_seen", seen);
}

/* ---------------- staleness: PC-fed feeds that stopped arriving ---------------- */
export async function checkStale(env) {
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
// `watch` is posted by the PC; the social section lives under its own key (socialFromLog) and is merged in when read
export async function watchMerged(env) {
  const [w, s] = await Promise.all([kv.get(env, "watch"), kv.get(env, "watch_social")]);
  if (!w && !s?.social) return w; const out = w || {}; if (s?.social) out.social = s.social; return out;
}

// the PC posts `watch` every 15 minutes: balance charges, social posting logs, Search Console, iOS listings
export async function watchWatch(env, w) {
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
export const APPS = [
  { key: "lazo_ios", name: "Lazo · iOS", ios: { id: "6812863675" } },
  { key: "lazo_android", name: "Lazo · Android", android: "com.meetlazo.app" },
  { key: "jovi_ios", name: "Jovi · iOS", ios: { search: "Jovi Health" } },
];
export async function appStores(env) {
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
const SOCIAL_BRANDS = [["jovi", "Jovi Health"], ["atavia", "Atavia"], ["elizabethscott", "Elizabeth Scott"], ["olivialayne", "Olivia Layne"], ["trylazo", "Lazo"], ["lazovendors", "Lazo Vendors"], ["roven", "Roven"], ["leasereputation", "LeaseReputation"]];
export async function socialFromLog(env) {
  const log = (await kv.get(env, "social_log")) || {}; const today = new Date().toLocaleDateString("en-CA", { timeZone: env.TZ || "America/Chicago" });
  const days = Object.keys(log).sort();
  const brands = SOCIAL_BRANDS.map(([key, name]) => { const last = [...days].reverse().find((d) => log[d][key]); return { brand: key, name, today: !!log[today]?.[key], last, total: days.filter((d) => log[d][key]).length, linkedin: !!log[today]?.[key]?.linkedin_urn, slug: log[today]?.[key]?.day || "" }; });
  const social = { day: today, brands, source: "hub" }; await kv.put(env, "watch_social", { social, at: new Date().toISOString() });   // never the shared `watch` key: the PC posts that one
  return social;
}
const CRON_EXPECT = { "* * * * *": 1440, "*/5 * * * *": 288, "0 * * * *": 24 };
export async function healthReport(env, days = 7) {
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
export const healthSummary = (r) => `cron minute ${r.cron[0].pct ?? "?"}%, five-minute ${r.cron[1].pct ?? "?"}%, hourly ${r.cron[2].pct ?? "?"}% of expected runs; ${r.stale.length} feed stalls${r.stale.length ? " (" + r.stale.slice(0, 4).join("; ") + ")" : ""}; bridge errors ${Object.entries(r.bridgeErrors).map(([a, n]) => a + " ×" + n).join(", ") || "none"}${r.bridgeSamples.length ? " e.g. " + r.bridgeSamples[0] : ""}; brief failures ${r.briefFailures}; page script errors ${r.clientErrors}; inbox syncs ${r.syncAge.map((x) => x.account.split("@")[0] + " " + x.minutes + "m ago").join(", ") || "none"}`;

/* ---------------- competitors: weekly price/package scan ---------------- */
const pageText = (h) => h.replace(/<script[\s\S]*?<\/script>|<style[\s\S]*?<\/style>|<!--[\s\S]*?-->/gi, " ").replace(/<[^>]+>/g, " ").replace(/&nbsp;|&#160;/g, " ").replace(/&amp;/g, "&").replace(/\s+/g, " ").trim();
function priceLines(t) {
  const out = new Set(); const re = /\$\s?\d[\d,]*(?:\.\d{2})?(?:\s?(?:k|K|\+|per\s+\w+|\/\s?\w+))?/g; let m;
  while ((m = re.exec(t))) { const a = Math.max(0, m.index - 70), b = Math.min(t.length, m.index + m[0].length + 50); out.add(t.slice(a, b).trim()); if (out.size > 60) break; }
  return [...out];
}
export async function scanCompetitors(env) {
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
