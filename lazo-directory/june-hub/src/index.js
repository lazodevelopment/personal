// June hub worker: the Lazo vendor's own assistant.
// Sign in with the Lazo login (Firebase ID token on every request), then June reads and writes
// Firestore AS THE VENDOR over the REST API, so the security rules decide what she can see and do.
// Pieces: today's brief (text + ElevenLabs audio, once per local day), who is waiting, this week's
// weddings and consults with their forecast, money, the page's views and rank, metro weather and
// NWS alerts, local and industry news, a streaming Claude chat with read tools and confirm-first
// actions (send a message, add or complete a task, tag, move a stage), and per-vendor memory.
import Anthropic from "@anthropic-ai/sdk";
import html from "./june.html";
import METROS from "./metros.json";
import { makeCouple } from "./couple.js";

const PROJECT = "lazo-513ec";
const FS = `https://firestore.googleapis.com/v1/projects/${PROJECT}/databases/(default)/documents`;
const JWKS = "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com";
const UA = "june-hub (meetlazo.com)";
const BUILD = (() => { let h = 0; for (let i = 0; i < html.length; i += 7) h = (h * 31 + html.charCodeAt(i)) >>> 0; return h.toString(36) + "-" + html.length.toString(36); })();

/* ---------------- helpers ---------------- */
const json = (data, status = 200) => new Response(JSON.stringify(data), { status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" } });
const kv = { get: (env, k) => env.JUNE.get(k, "json"), put: (env, k, v, opt) => env.JUNE.put(k, JSON.stringify(v), opt), del: (env, k) => env.JUNE.delete(k) };
const uid = () => Math.random().toString(36).slice(2, 10);
const str = (v) => (v == null ? "" : String(v));
const clip = (s, n) => str(s).trim().slice(0, n);
const within = (p, ms, fallback = null) => Promise.race([Promise.resolve(p).catch(() => fallback), new Promise((r) => setTimeout(() => r(fallback), ms))]);
const untag = (x) => str(x).replace(/<!\[CDATA\[|\]\]>/g, "").replace(/<[^>]+>/g, "").replace(/&amp;/g, "&").replace(/&#39;|&apos;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, "<").replace(/&gt;/g, ">").trim();
const money = (n) => "$" + Math.round(+n || 0).toLocaleString("en-US");
const dayKey = (tz, d = new Date()) => d.toLocaleDateString("en-CA", { timeZone: tz || "America/Phoenix" });
const localTime = (tz, d = new Date(), opts = { dateStyle: "full", timeStyle: "short" }) => d.toLocaleString("en-US", { timeZone: tz || "America/Phoenix", ...opts });
const fmtDay = (iso, tz) => { try { return new Date(iso.length === 10 ? iso + "T12:00:00" : iso).toLocaleDateString("en-US", { timeZone: tz, weekday: "short", month: "short", day: "numeric" }); } catch { return iso; } };
const fmtWhen = (iso, tz) => { try { return new Date(iso).toLocaleString("en-US", { timeZone: tz, weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }); } catch { return iso; } };
const hoursAgo = (iso) => iso ? Math.max(0, Math.round((Date.now() - new Date(iso)) / 3600e3)) : null;
// "2026-10-09T09:00" in the vendor's timezone -> UTC ISO (no tz database on the edge, so read the offset off Intl)
function localToIso(local, tz) {
  const m = String(local || "").match(/^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{1,2}):(\d{2}))?/); if (!m) return null;
  const [, y, mo, d, h = "9", mi = "0"] = m; const guess = Date.UTC(+y, +mo - 1, +d, +h, +mi);
  const parts = Object.fromEntries(new Intl.DateTimeFormat("en-US", { timeZone: tz || "America/Phoenix", hour12: false, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }).formatToParts(new Date(guess)).map((p) => [p.type, p.value]));
  const asLocal = Date.UTC(+parts.year, +parts.month - 1, +parts.day, +parts.hour % 24, +parts.minute);
  return new Date(guess - (asLocal - guess)).toISOString();
}

/* ---------------- Firebase ID token (same check as the Lazo site worker) ---------------- */
const b64u = (s) => { s = s.replace(/-/g, "+").replace(/_/g, "/"); while (s.length % 4) s += "="; return Uint8Array.from(atob(s), (c) => c.charCodeAt(0)); };
async function jwks() {
  const key = new Request(JWKS);
  let r = await caches.default.match(key);
  if (!r) {
    r = await fetch(JWKS); if (!r.ok) return [];
    r = new Response(await r.text(), { headers: { "content-type": "application/json", "cache-control": "public, max-age=3600" } });
    try { await caches.default.put(key, r.clone()); } catch {}
  }
  try { return (await r.json()).keys || []; } catch { return []; }
}
async function verifyIdToken(req) {
  const m = /^Bearer\s+([A-Za-z0-9_.-]+)$/.exec(req.headers.get("authorization") || "");
  if (!m) return null;
  const token = m[1]; const parts = token.split("."); if (parts.length !== 3) return null;
  let header, payload;
  try { header = JSON.parse(new TextDecoder().decode(b64u(parts[0]))); payload = JSON.parse(new TextDecoder().decode(b64u(parts[1]))); } catch { return null; }
  if (header.alg !== "RS256" || !header.kid) return null;
  const now = Math.floor(Date.now() / 1000);
  if (payload.aud !== PROJECT || payload.iss !== `https://securetoken.google.com/${PROJECT}`) return null;
  if (!payload.sub || !(payload.exp > now) || !(payload.iat <= now + 300)) return null;
  const jwk = (await jwks()).find((k) => k.kid === header.kid); if (!jwk) return null;
  try {
    const key = await crypto.subtle.importKey("jwk", jwk, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"]);
    if (!(await crypto.subtle.verify("RSASSA-PKCS1-v1_5", key, b64u(parts[2]), new TextEncoder().encode(parts[0] + "." + parts[1])))) return null;
  } catch { return null; }
  return { uid: payload.sub, email: payload.email || "", token };
}

/* ---------------- Firestore REST, as the signed-in vendor ---------------- */
function dec(v) {
  if (v == null) return null;
  if ("stringValue" in v) return v.stringValue;
  if ("integerValue" in v) return Number(v.integerValue);
  if ("doubleValue" in v) return v.doubleValue;
  if ("booleanValue" in v) return v.booleanValue;
  if ("timestampValue" in v) return v.timestampValue;
  if ("nullValue" in v) return null;
  if ("mapValue" in v) return Object.fromEntries(Object.entries(v.mapValue.fields || {}).map(([k, x]) => [k, dec(x)]));
  if ("arrayValue" in v) return (v.arrayValue.values || []).map(dec);
  if ("referenceValue" in v) return v.referenceValue;
  if ("geoPointValue" in v) return v.geoPointValue;
  return null;
}
const docObj = (d) => d && d.name ? { id: d.name.split("/").pop(), _path: d.name.split("/documents/")[1], ...Object.fromEntries(Object.entries(d.fields || {}).map(([k, v]) => [k, dec(v)])) } : null;
function enc(v) {
  if (v === null || v === undefined) return { nullValue: null };
  if (v instanceof Date) return { timestampValue: v.toISOString() };
  if (typeof v === "string") return { stringValue: v };
  if (typeof v === "boolean") return { booleanValue: v };
  if (typeof v === "number") return Number.isInteger(v) ? { integerValue: String(v) } : { doubleValue: v };
  if (Array.isArray(v)) return { arrayValue: { values: v.map(enc) } };
  if (typeof v === "object") return { mapValue: { fields: Object.fromEntries(Object.entries(v).map(([k, x]) => [k, enc(x)])) } };
  return { stringValue: String(v) };
}
const hdr = (token) => ({ accept: "application/json", authorization: `Bearer ${token}`, "content-type": "application/json" });
async function fsGet(token, path) {
  const r = await fetch(`${FS}/${path}`, { headers: hdr(token) });
  if (!r.ok) return null;
  return docObj(await r.json());
}
// where: [[field, op, value]], op in EQUAL, GREATER_THAN_OR_EQUAL, ...; group = collection-group query
async function fsQuery(token, { collection, parent = "", where = [], group = false, limit = 0, orderBy = null }) {
  const filters = where.map(([field, op, value]) => ({ fieldFilter: { field: { fieldPath: field }, op, value: enc(value) } }));
  const q = { from: [{ collectionId: collection, allDescendants: !!group }] };
  if (filters.length === 1) q.where = filters[0]; else if (filters.length > 1) q.where = { compositeFilter: { op: "AND", filters } };
  if (limit) q.limit = limit;
  if (orderBy) q.orderBy = [{ field: { fieldPath: orderBy[0] }, direction: orderBy[1] || "ASCENDING" }];
  const r = await fetch(`${FS}${parent ? "/" + parent : ""}:runQuery`, { method: "POST", headers: hdr(token), body: JSON.stringify({ structuredQuery: q }) });
  if (!r.ok) { const t = await r.text(); throw new Error(`Firestore ${r.status}: ${t.slice(0, 200)}`); }
  return (await r.json()).map((x) => docObj(x.document)).filter(Boolean);
}
async function fsCreate(token, parentPath, collection, obj) {
  const r = await fetch(`${FS}/${parentPath}/${collection}`, { method: "POST", headers: hdr(token), body: JSON.stringify({ fields: Object.fromEntries(Object.entries(obj).map(([k, v]) => [k, enc(v)])) }) });
  if (!r.ok) throw new Error(`Firestore write ${r.status}: ${(await r.text()).slice(0, 200)}`);
  return docObj(await r.json());
}
async function fsPatch(token, path, obj) {
  const mask = Object.keys(obj).map((f) => "updateMask.fieldPaths=" + encodeURIComponent(f)).join("&");
  const r = await fetch(`${FS}/${path}?${mask}`, { method: "PATCH", headers: hdr(token), body: JSON.stringify({ fields: Object.fromEntries(Object.entries(obj).map(([k, v]) => [k, enc(v)])) }) });
  if (!r.ok) throw new Error(`Firestore update ${r.status}: ${(await r.text()).slice(0, 200)}`);
  return true;
}

/* ---------------- who is this: the vendor behind the signed-in user ---------------- */
async function resolveVendor(env, who) {
  const cached = await kv.get(env, "vendor_of_" + who.uid);
  if (cached && Date.now() - cached.at < 30 * 60e3) return cached;
  let vendorId = "", role = "owner";
  const u = await fsGet(who.token, `users/${encodeURIComponent(who.uid)}`);
  if (u?.vendorId) { vendorId = str(u.vendorId); role = str(u.vendorRole) === "manager" ? "manager" : "owner"; }
  if (!vendorId) {
    const vs = await fsQuery(who.token, { collection: "vendors", where: [["claimedBy", "EQUAL", who.uid]], limit: 1 }).catch(() => []);
    if (vs[0]) vendorId = vs[0].id;
  }
  if (!vendorId) return null;
  const out = { vendorId, role, at: Date.now(), name: str(u?.businessName || "") };
  await kv.put(env, "vendor_of_" + who.uid, out, { expirationTtl: 3600 });
  return out;
}

/* ---------------- the vendor's data (mirrors the June tools in functions-dashboard/mcp.js) ---------------- */
function stageOf(m, customKeys) {
  const st = str(m.status);
  if (st === "lost") return "lost";
  if (st === "booked") return m.deliveredAt ? "delivered" : "booked";
  const ex = str(m.stage); if (ex && customKeys.includes(ex)) return ex;
  if (st === "responded" || st === "replied" || str(m.lastMessageRole) === "vendor") return "talking";
  return "new";
}
function isUnread(m) {
  if (str(m.lastMessageRole) !== "couple") { const st = str(m.status) || "new"; return (st === "new" || st === "") && !m.seenByVendorAt; }
  if (!m.lastMessageAt) return false; if (!m.vendorLastReadAt) return true;
  return new Date(m.lastMessageAt) > new Date(m.vendorLastReadAt);
}
function threadRow(m, customKeys) {
  const si = m.structuredIntent || {}, c = m.contact || {};
  return {
    inquiryId: m.id, couple: str(m.coupleName) || str(c.name) || "A couple", stage: stageOf(m, customKeys), status: str(m.status) || "new",
    tags: Array.isArray(m.tags) ? m.tags : [], weddingDate: str(si.weddingDate) || null, venue: str(si.venue) || null, budget: str(si.budget) || null, guests: si.guests ?? null, eventType: str(si.eventType) || null,
    source: str(m.source) || "lazo", offPlatform: m.offPlatform === true, unread: isUnread(m),
    lastMessageAt: m.lastMessageAt || m.createdAt || null, lastMessageFrom: str(m.lastMessageRole) || null, lastMessagePreview: str(m.lastMessagePreview || si.message) || null,
    waitingOnVendor: str(m.lastMessageRole) === "couple" || (!m.lastMessageRole && (str(m.status) === "new" || !m.status)),
    contractStatus: str(m.contractStatus) || null, invoiceStatus: str(m.invoiceStatus) || null,
    openTasks: m.openTasks || 0, nextTask: str(m.nextTaskTitle) ? { title: str(m.nextTaskTitle), dueAt: m.nextTaskAt || null } : null, nextConsultAt: m.nextConsultAt || null,
    blocked: m.blockedByCouple === true, createdAt: m.createdAt || null, respondedAt: m.respondedAt || null, bookedAt: m.bookedAt || null, deliveredAt: m.deliveredAt || null, coupleUid: str(m.coupleUid) || null,
    email: str(c.email) || null, phone: str(c.phone) || null,
  };
}
// last 7 days against the 7 before, from what the vendor can already read
function weekStats(rows, invoices, views) {
  const now = Date.now(), d7 = now - 7 * 86400e3, d14 = now - 14 * 86400e3;
  const inWin = (iso, a, b) => iso && new Date(iso) >= a && new Date(iso) < b;
  const cnt = (f) => [rows.filter((r) => inWin(f(r), d7, now + 1)).length, rows.filter((r) => inWin(f(r), d14, d7)).length];
  const [leads, leadsPrev] = cnt((r) => r.createdAt), [replied, repliedPrev] = cnt((r) => r.respondedAt), [booked, bookedPrev] = cnt((r) => r.bookedAt);
  const cash = (a, b) => Math.round(invoices.filter((i) => i.status === "paid" && inWin(i.paidAt, a, b)).reduce((s, i) => s + i.total, 0));
  return { leads, leadsPrev, replied, repliedPrev, booked, bookedPrev, cash: cash(d7, now + 1), cashPrev: cash(d14, d7), views: views?.d7 ?? null, viewsPrev: views?.d7Prev ?? null };
}
const weekLine = (w) => `last 7 days vs the 7 before: new leads ${w.leads} (${w.leadsPrev}), replies sent ${w.replied} (${w.repliedPrev}), bookings ${w.booked} (${w.bookedPrev}), cash in ${money(w.cash)} (${money(w.cashPrev)})${w.views != null ? `, page views ${w.views} (${w.viewsPrev})` : ""}`;
async function loadThreads(token, vendorId, customKeys) {
  const docs = await fsQuery(token, { collection: "inquiries", where: [["vendorId", "EQUAL", vendorId]] });
  return docs.filter((m) => str(m.status) !== "flagged" && m.demo !== true).map((m) => threadRow(m, customKeys));
}
async function loadConsults(token, vendorId, days = 90) {
  const now = Date.now(), until = now + days * 86400e3;
  const docs = await fsQuery(token, { collection: "consults", where: [["vendorId", "EQUAL", vendorId], ["status", "EQUAL", "booked"]] }).catch(() => []);
  return docs.filter((c) => c.startAt && new Date(c.startAt) >= now - 3600e3 && new Date(c.startAt) <= until).sort((a, b) => a.startAt.localeCompare(b.startAt))
    .map((c) => ({ consultId: c.id, inquiryId: str(c.inquiryId), who: str(c.contact?.name) || "A couple", type: str(c.typeLabel), mode: str(c.mode), startAt: c.startAt, tz: str(c.tz), videoLink: str(c.videoLink) || null }));
}
async function loadInvoices(token, vendorId) {
  const docs = await fsQuery(token, { collection: "invoices", group: true, where: [["vendorId", "EQUAL", vendorId]] }).catch(() => []);
  return docs.filter((i) => i.demo !== true && str(i.status) !== "void").map((i) => ({ invoiceId: i.id, inquiryId: (i._path || "").split("/")[1] || "", title: str(i.title) || "Invoice", total: +i.total || 0, status: str(i.status), dueDate: i.dueDate || null, paidAt: i.paidAt || null, paidVia: str(i.paidVia) || null, installment: i.installmentCount ? `${(i.installmentIndex || 0) + 1} of ${i.installmentCount}` : null }));
}
function moneyOf(invoices, rows) {
  const now = Date.now(), since = now - 30 * 86400e3, week = now + 7 * 86400e3, names = Object.fromEntries(rows.map((r) => [r.inquiryId, r.couple]));
  const open = invoices.filter((i) => i.status === "sent").map((i) => ({ ...i, couple: names[i.inquiryId] || "", overdue: !!(i.dueDate && new Date(i.dueDate) < now), dueThisWeek: !!(i.dueDate && new Date(i.dueDate) <= week) })).sort((a, b) => str(a.dueDate).localeCompare(str(b.dueDate)));
  const paid = invoices.filter((i) => i.status === "paid" && i.paidAt && new Date(i.paidAt) >= since).map((i) => ({ ...i, couple: names[i.inquiryId] || "" }));
  const sum = (xs) => Math.round(xs.reduce((s, x) => s + x.total, 0));
  return { outstanding: sum(open), overdue: sum(open.filter((x) => x.overdue)), dueThisWeek: sum(open.filter((x) => x.dueThisWeek)), collected30: sum(paid), open: open.slice(0, 12), recentlyPaid: paid.slice(0, 8) };
}
async function loadVendor(token, vendorId) {
  const v = await fsGet(token, `vendors/${encodeURIComponent(vendorId)}`);
  if (!v) throw new Error("Vendor not found");
  return v;
}
function vendorCard(v) {
  const metro = METROS[str(v.metroId)] || null;
  return {
    id: v.id, name: str(v.name), slug: str(v.slug), category: str(v.category || (Array.isArray(v.categories) && v.categories[0]) || "wedding vendor"), categories: Array.isArray(v.categories) ? v.categories : [],
    metroId: str(v.metroId), metro: metro ? metro.display : str(v.metroId), lat: metro?.lat || null, lon: metro?.lon || null,
    tier: str(v.tier) || "free", verified: v.verified === true, claimStatus: str(v.claimStatus), badges: Array.isArray(v.badges) ? v.badges : [], logoUrl: str(v.logoUrl) || null, coverUrl: str(v.coverUrl) || null,
    views: v.views && typeof v.views === "object" ? { d7: +v.views.d7 || 0, d7Prev: +v.views.d7Prev || 0, updatedAt: v.views.updatedAt || null } : null,
    rank: v.rank && typeof v.rank === "object" && v.rank.pos != null ? { pos: Math.round(+v.rank.pos), of: Math.round(+v.rank.of), label: str(v.rank.label) } : null,
    reviewCount: +v.reviewCount || 0, reviewAverage: +v.reviewAverage || 0, score: v.score != null ? +v.score : null, startingPrice: v.startingPrice ?? null, unavailableDates: Array.isArray(v.unavailableDates) ? v.unavailableDates : [],
    pipeline: Array.isArray(v.pipeline) ? v.pipeline : [], tagPalette: Array.isArray(v.tagPalette) ? v.tagPalette : [], tz: str(v.scheduler?.tz) || null, publicUrl: `https://meetlazo.com/vendors/${str(v.metroId)}/${str(v.slug || v.id)}`,
    studio: str(v.tier) === "studio",
    gallery: (Array.isArray(v.gallery) ? v.gallery : []).map(String).filter((u) => /^https?:\/\//.test(u)).slice(0, 24),
    // showcases are galleries the couple agreed to have featured (galleryShowcase asks for consent), so June may post from them
    showcases: (Array.isArray(v.showcases) ? v.showcases : []).map((s) => ({ slug: str(s.slug), title: str(s.title), blurb: str(s.blurb), dateIso: str(s.dateIso), cover: s.coverId ? `https://meetlazo.com/g/${str(s.slug)}/i/${str(s.coverId)}/web` : null })).filter((s) => s.cover).slice(0, 12),
    instagram: str(v.instagram || v.social?.instagram) || null, facebook: str(v.facebook || v.social?.facebook) || null,
    categoryId: str((Array.isArray(v.categories) && v.categories[0]) || v.category), bio: clip(v.bio, 400), publicEmail: str(v.publicEmail) || null,
    packages: (Array.isArray(v.packages) ? v.packages : []).filter((p) => p && typeof p === "object").map((p) => ({ name: str(p.name), price: str(p.price), offPeak: str(p.offPeak), hours: str(p.hours), includes: clip(p.includes || p.description, 200) })).slice(0, 8),
    savedReplies: (Array.isArray(v.savedReplies) ? v.savedReplies : []).filter((r) => r && typeof r === "object").map((r) => ({ title: str(r.title), text: clip(r.text, 700) })).slice(0, 10),
    faqs: (Array.isArray(v.vendorFaqs) ? v.vendorFaqs : []).filter((f) => f && typeof f === "object").map((f) => ({ q: clip(f.q, 160), a: clip(f.a, 400) })).slice(0, 12),
  };
}

/* ---------------- secrets at rest: AES-GCM under JUNE_SECRET (refresh tokens for the 7am brief) ---------------- */
async function aesKey(env) { const raw = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(String(env.JUNE_SECRET))); return crypto.subtle.importKey("raw", raw, "AES-GCM", false, ["encrypt", "decrypt"]); }
async function encrypt(env, text) { const iv = crypto.getRandomValues(new Uint8Array(12)); const ct = new Uint8Array(await crypto.subtle.encrypt({ name: "AES-GCM", iv }, await aesKey(env), new TextEncoder().encode(text))); return btoa(String.fromCharCode(...iv)) + "." + btoa(String.fromCharCode(...ct)); }
async function decrypt(env, blob) { const [i, c] = String(blob).split("."); const iv = Uint8Array.from(atob(i), (x) => x.charCodeAt(0)), ct = Uint8Array.from(atob(c), (x) => x.charCodeAt(0)); return new TextDecoder().decode(await crypto.subtle.decrypt({ name: "AES-GCM", iv }, await aesKey(env), ct)); }
// a fresh ID token from a stored refresh token (what the cron uses to act as the vendor)
async function tokenFromRefresh(env, refreshToken) {
  const r = await fetch("https://securetoken.googleapis.com/v1/token?key=" + env.FIREBASE_API_KEY, { method: "POST", headers: { "content-type": "application/x-www-form-urlencoded" }, body: "grant_type=refresh_token&refresh_token=" + encodeURIComponent(refreshToken) });
  if (!r.ok) return null; const j = await r.json(); return { uid: j.user_id, token: j.id_token, email: "" };
}

/* ---------------- email (Resend, same sender as the Lazo functions) ---------------- */
async function sendEmail(env, to, subject, html, text) {
  if (!env.RESEND_API_KEY || !to) return { skipped: true };
  const r = await fetch("https://api.resend.com/emails", { method: "POST", headers: { authorization: "Bearer " + env.RESEND_API_KEY, "content-type": "application/json" }, body: JSON.stringify({ from: env.EMAIL_FROM || "June at Lazo <hello@meetlazo.com>", to: [to], subject, html, text }) });
  return { status: r.status };
}
const emailWrap = (title, body, link, cta) => `<div style="font-family:Inter,Helvetica,Arial,sans-serif;color:#241E2B;font-size:15px;line-height:1.6;max-width:560px"><p style="font-size:12px;letter-spacing:.12em;color:#8A6A2F;margin:0 0 12px">${title}</p>${body}${link ? `<p style="margin:18px 0 0"><a href="${link}" style="background:#D9B77C;color:#3D1C3B;text-decoration:none;font-weight:700;padding:10px 16px;border-radius:10px;display:inline-block">${cta || "Open June"}</a></p>` : ""}<p style="font-size:12px;color:#6B5F72;margin-top:22px">From June, your Lazo assistant. Turn these off any time in June → Alerts.</p></div>`;

/* ---------------- social posting (June Studio): Ayrshare, one profile per vendor ---------------- */
const AYR = "https://api.ayrshare.com/api";
const socialReady = (env) => !!(env.AYRSHARE_API_KEY && env.AYRSHARE_PRIVATE_KEY && env.AYRSHARE_DOMAIN);
async function ayr(env, path, { method = "GET", body, profileKey } = {}) {
  const r = await fetch(AYR + path, { method, headers: { authorization: "Bearer " + env.AYRSHARE_API_KEY, "content-type": "application/json", ...(profileKey ? { "Profile-Key": profileKey } : {}) }, body: body ? JSON.stringify(body) : undefined });
  const j = await r.json().catch(() => ({})); if (!r.ok || j.status === "error") throw new Error(j.message || j.errors?.[0]?.message || ("posting service " + r.status)); return j;
}
async function socialProfile(env, card, create = false) {
  let s = await kv.get(env, "social_" + card.id);
  if (!s?.profileKey && create && socialReady(env)) { const j = await ayr(env, "/profiles", { method: "POST", body: { title: `${card.name} (${card.id})` } }); s = { profileKey: j.profileKey, at: new Date().toISOString() }; await kv.put(env, "social_" + card.id, s); }
  return s || null;
}
async function socialStatus(env, card) {
  const out = { studio: card.studio, available: socialReady(env), connected: [], names: {}, posts: (await kv.get(env, "posts_" + card.id)) || [] };
  if (!card.studio || !out.available) return out;
  const s = await socialProfile(env, card); if (!s?.profileKey) return out;
  try { const u = await ayr(env, "/user", { profileKey: s.profileKey }); out.connected = (u.activeSocialAccounts || []).filter((p) => ["instagram", "facebook"].includes(p)); out.names = u.displayNames ? Object.fromEntries((u.displayNames || []).map((d) => [d.platform, d.displayName || d.username])) : {}; } catch (e) { out.error = e.message; }
  return out;
}
const socialSummary = (so, card) => !so.studio ? `not on June Studio (auto-posting is a Studio feature; June can still draft posts for the vendor to copy)` : !so.available ? `June Studio, posting service not configured yet` : so.connected.length ? `June Studio, connected: ${so.connected.join(" + ")}; last post ${so.posts[0]?.at?.slice(0, 10) || "never"}` : `June Studio, no social accounts connected yet (Connect in the Social panel)`;

/* ---------------- weather + news for the metro ---------------- */
const WMO = { 0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast", 45: "fog", 48: "fog", 51: "drizzle", 53: "drizzle", 55: "drizzle", 61: "light rain", 63: "rain", 65: "heavy rain", 71: "snow", 73: "snow", 75: "snow", 80: "showers", 81: "showers", 82: "heavy showers", 95: "thunderstorms", 96: "thunderstorms", 99: "thunderstorms" };
async function weatherFor(env, metroId, lat, lon) {
  const key = "wx_" + (metroId || `${lat},${lon}`);
  const c = await kv.get(env, key); if (c && Date.now() - c.t < 10 * 60e3) return c.v;
  const q = new URLSearchParams({ latitude: lat, longitude: lon, current: "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m,wind_gusts_10m,is_day,precipitation,uv_index",
    daily: "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset,wind_speed_10m_max", hourly: "temperature_2m,weather_code,precipitation_probability", temperature_unit: "fahrenheit", wind_speed_unit: "mph", precipitation_unit: "inch", forecast_days: "14", timezone: "auto" });
  const [wx, al] = await Promise.all([
    fetch("https://api.open-meteo.com/v1/forecast?" + q, { cf: { cacheTtl: 600, cacheEverything: true } }).then((r) => r.json()),
    fetch(`https://api.weather.gov/alerts/active?point=${(+lat).toFixed(4)},${(+lon).toFixed(4)}`, { headers: { "user-agent": UA, accept: "application/geo+json" }, cf: { cacheTtl: 300, cacheEverything: true } }).then((r) => r.json()).catch(() => ({ features: [] })),
  ]);
  if (!wx?.current) return c?.v || null;
  const v = { tz: wx.timezone, current: wx.current, daily: wx.daily, hourly: { time: wx.hourly.time.slice(0, 36), temperature_2m: wx.hourly.temperature_2m.slice(0, 36), weather_code: wx.hourly.weather_code.slice(0, 36), precipitation_probability: wx.hourly.precipitation_probability.slice(0, 36) },
    nws: (al.features || []).map((f) => ({ id: f.id, event: f.properties.event, severity: f.properties.severity, headline: f.properties.headline, ends: f.properties.ends || f.properties.expires })) };
  await kv.put(env, key, { t: Date.now(), v }, { expirationTtl: 3600 });
  return v;
}
function weatherSummary(w, place) {
  if (!w?.current) return "unavailable";
  const c = w.current, d = w.daily;
  const days = d.time.slice(0, 5).map((t, i) => `${i === 0 ? "today" : new Date(t + "T12:00").toLocaleDateString("en-US", { weekday: "short" })} ${WMO[d.weather_code[i]] || ""} ${Math.round(d.temperature_2m_max[i])}/${Math.round(d.temperature_2m_min[i])} rain ${d.precipitation_probability_max[i] ?? 0}%`).join("; ");
  return `${place}: ${Math.round(c.temperature_2m)}°F ${WMO[c.weather_code] || ""}, feels ${Math.round(c.apparent_temperature)}, wind ${Math.round(c.wind_speed_10m)} mph, humidity ${c.relative_humidity_2m}%. Sunset ${str(d.sunset[0]).slice(11)}. Outlook: ${days}.${w.nws.length ? " NWS ALERTS: " + w.nws.map((a) => a.headline).join(" | ") : ""}`;
}
// the day's forecast for each booked wedding and consult inside the 14-day window (home metro)
function dayWeather(w, iso) {
  if (!w?.daily || !iso) return null; const i = w.daily.time.indexOf(iso.slice(0, 10)); if (i < 0) return null;
  return { code: w.daily.weather_code[i], text: WMO[w.daily.weather_code[i]] || "", hi: Math.round(w.daily.temperature_2m_max[i]), lo: Math.round(w.daily.temperature_2m_min[i]), rain: w.daily.precipitation_probability_max[i] ?? 0, wind: Math.round(w.daily.wind_speed_10m_max[i]), sunset: str(w.daily.sunset[i]).slice(11) };
}
async function rss(env, key, url, ttlMs, n = 8) {
  const c = await kv.get(env, key); if (c && Date.now() - c.t < ttlMs) return c.v;
  try {
    const t = await (await fetch(url, { redirect: "follow", headers: { "user-agent": "Mozilla/5.0 (June hub)" }, cf: { cacheTtl: 900, cacheEverything: true } })).text();
    const items = [...t.matchAll(/<item>([\s\S]*?)<\/item>/g)].slice(0, n).map((m) => { const b = m[1]; const g = (k) => (b.match(new RegExp(`<${k}[^>]*>([\\s\\S]*?)<\\/${k}>`)) || [])[1] || ""; return { title: untag(g("title")).replace(/\s+-\s+[^-]+$/, ""), source: untag(g("source")), url: untag(g("link")) || untag(g("guid")), at: g("pubDate") ? new Date(untag(g("pubDate"))).toISOString() : null }; }).filter((i) => i.title);
    const v = { at: new Date().toISOString(), items }; if (items.length) await kv.put(env, key, { t: Date.now(), v }, { expirationTtl: 7200 });
    return v;
  } catch (e) { return c?.v || { items: [], error: e.message }; }
}
const localNews = (env, metro) => metro ? rss(env, "news_" + metro.name.toLowerCase().replace(/\W+/g, "-"), `https://news.google.com/rss/headlines/section/geo/${encodeURIComponent(metro.name)}?hl=en-US&gl=US&ceid=US:en`, 20 * 60e3) : Promise.resolve({ items: [] });
const industryNews = (env) => rss(env, "news_industry", "https://news.google.com/rss/search?q=%22wedding+industry%22+OR+%22wedding+vendors%22+OR+%22wedding+trends%22+when:7d&hl=en-US&gl=US&ceid=US:en", 60 * 60e3, 6);

/* ---------------- the whole picture for one vendor ---------------- */
async function snapshot(env, who, vend, { deep = true } = {}) {
  const token = who.token, vendorId = vend.vendorId;
  const v = await loadVendor(token, vendorId); const card = vendorCard(v);
  const customKeys = card.pipeline.map((p) => str(p && p.key)).filter(Boolean);
  const metro = METROS[card.metroId] || null;
  const [rows, consults, invoices, wx, news, ind, memory, queue, brief] = await Promise.all([
    loadThreads(token, vendorId, customKeys), loadConsults(token, vendorId, 60), deep ? loadInvoices(token, vendorId) : [],
    metro ? within(weatherFor(env, card.metroId, metro.lat, metro.lon), 4000) : null, within(localNews(env, metro), 3500, { items: [] }), within(industryNews(env), 3500, { items: [] }),
    kv.get(env, "memory_" + vendorId), kv.get(env, "queue_" + vendorId), kv.get(env, "brief_" + vendorId),
  ]);
  const social = await within(socialStatus(env, card), 4000, { studio: card.studio, available: socialReady(env), connected: [], names: {}, posts: [] });
  const [metroStat, reviewsTop, reviewsSub, reminders, sub, triage, asked] = await Promise.all([
    card.metroId && card.categoryId ? within(fsGet(token, `metroStats/${encodeURIComponent(card.metroId + "__" + card.categoryId)}`), 2500) : null,
    within(fsQuery(token, { collection: "reviews", where: [["vendorId", "EQUAL", vendorId]] }), 3000, []), within(fsQuery(token, { collection: "reviews", parent: `vendors/${vendorId}` }), 3000, []),
    kv.get(env, "reminders_" + vendorId), kv.get(env, "sub_" + vendorId), kv.get(env, "triage_" + vendorId), kv.get(env, "asked_" + vendorId),
  ]);
  const reviews = [...(reviewsTop || []), ...(reviewsSub || [])].filter((r) => ["published", "verified", "approved", ""].includes(str(r.status)) || !r.status).map((r) => ({ id: r.id, rating: +r.rating || 0, text: clip(r.text, 400), who: str(r.coupleName) || "A couple", at: r.createdAt || null, inquiryId: str(r.inquiryId) || null })).sort((a, b) => str(b.at).localeCompare(str(a.at))).slice(0, 10);
  const tz = card.tz || wx?.tz || "America/Phoenix";
  const today = dayKey(tz), in14 = dayKey(tz, new Date(Date.now() + 14 * 86400e3)), in30 = dayKey(tz, new Date(Date.now() + 30 * 86400e3));
  const waiting = rows.filter((r) => r.waitingOnVendor && r.status !== "lost" && !r.blocked).sort((a, b) => str(a.lastMessageAt).localeCompare(str(b.lastMessageAt))).map((r) => ({ ...r, waitedHours: hoursAgo(r.lastMessageAt) }));
  const weddings = rows.filter((r) => r.status === "booked" && r.weddingDate && r.weddingDate >= today).sort((a, b) => a.weddingDate.localeCompare(b.weddingDate)).map((r) => ({ ...r, wx: r.weddingDate <= in14 ? dayWeather(wx, r.weddingDate) : null }));
  const consultsOut = consults.map((c) => ({ ...c, wx: dayWeather(wx, dayKey(tz, new Date(c.startAt))) }));
  const quiet = rows.filter((r) => ["new", "talking"].includes(r.stage) && r.lastMessageFrom === "vendor" && r.lastMessageAt && Date.now() - new Date(r.lastMessageAt) > 5 * 86400e3).slice(0, 8);
  const tasksDue = rows.filter((r) => r.nextTask?.dueAt && r.nextTask.dueAt.slice(0, 10) <= today).map((r) => ({ inquiryId: r.inquiryId, couple: r.couple, ...r.nextTask }));
  const week = weekStats(rows, invoices, card.views);
  const reviewedInq = new Set(reviews.map((r) => r.inquiryId).filter(Boolean)); const askedMap = asked || {};
  const reviewAsks = rows.filter((r) => r.status === "booked" && r.weddingDate && r.weddingDate < dayKey(tz, new Date(Date.now() - 2 * 86400e3)) && r.weddingDate >= dayKey(tz, new Date(Date.now() - 120 * 86400e3)) && !reviewedInq.has(r.inquiryId) && !askedMap[r.inquiryId]).slice(0, 6);
  const remindersAll = (reminders || []).filter((r) => !r.done).sort((a, b) => str(a.at).localeCompare(str(b.at)));
  const due = remindersAll.filter((r) => r.at <= new Date().toISOString());
  const tri = triage || {}; const waitingT = waiting.map((r) => ({ ...r, triage: tri[r.inquiryId]?.key === (r.lastMessageAt || "") ? tri[r.inquiryId] : null }));
  const pricing = metroStat ? { vendors: metroStat.vendors || 0, priceFrom: metroStat.priceFrom || null, medianReplyMin: metroStat.medianReplyMin ?? null, medianInquiries30d: metroStat.medianInquiries30d ?? null } : null;
  const alerts = sub ? { enabled: !!sub.enabled, hour: sub.hour ?? 7, nudges: sub.nudges !== false, reminders: sub.reminders !== false, email: sub.email || "", configured: !!(env.JUNE_SECRET && env.RESEND_API_KEY) } : { enabled: false, hour: 7, nudges: true, reminders: true, email: who.email || card.publicEmail || "", configured: !!(env.JUNE_SECRET && env.RESEND_API_KEY) };
  const weekly = await kv.get(env, "weekly_" + vendorId);
  return {
    at: new Date().toISOString(), tz, today, build: BUILD, vendor: card, role: vend.role, user: { uid: who.uid, email: who.email },
    week, reviews, reviewAsks, reminders: remindersAll.slice(0, 30), due, pricing, alerts, weekly: weekly && Date.now() - new Date(weekly.at) < 8 * 86400e3 ? weekly : null, isMonday: new Date().toLocaleDateString("en-US", { timeZone: tz, weekday: "short" }) === "Mon",
    counts: { threads: rows.length, waiting: waiting.length, unread: rows.filter((r) => r.unread).length, booked: rows.filter((r) => r.status === "booked").length, next30: weddings.filter((w) => w.weddingDate <= in30).length, byStage: rows.reduce((a, r) => { a[r.stage] = (a[r.stage] || 0) + 1; return a; }, {}) },
    waiting: waitingT.slice(0, 12), weddings: weddings.slice(0, 12), consults: consultsOut.slice(0, 8), quiet, tasksDue,
    money: deep ? moneyOf(invoices, rows) : null, weather: wx, news: news?.items || [], industry: ind?.items || [],
    memory: memory || [], recent: (queue || []).slice(0, 8), brief: brief && brief.day === today ? brief : null, briefStale: !!(brief && brief.day !== today), social,
    _rows: rows, _customKeys: customKeys,
  };
}

/* ---------------- context for the brain ---------------- */
function buildContext(s) {
  const L = [], v = s.vendor, tz = s.tz;
  L.push(`TIME: ${localTime(tz)} (${tz})`);
  L.push(`VENDOR: ${v.name}, ${v.category} in ${v.metro}. Plan ${v.tier}${v.verified ? ", verified" : ", not yet verified"}${v.badges.length ? ", badges " + v.badges.join("/") : ""}. Public page ${v.publicUrl}`);
  L.push(`THE PAGE: ` + (v.views ? `${v.views.d7} views in the last 7 days (${v.views.d7Prev} the 7 before)` : "view counts not available yet") + (v.rank ? `; ranked #${v.rank.pos} of ${v.rank.of} ${v.rank.label}` : "") + (v.reviewCount ? `; ${v.reviewCount} reviews averaging ${v.reviewAverage.toFixed(1)}` : "; no reviews yet"));
  L.push(`COUNTS: ${s.counts.threads} threads, ${s.counts.waiting} waiting on the vendor, ${s.counts.unread} unread, ${s.counts.booked} booked, ${s.counts.next30} weddings in the next 30 days; by stage ${Object.entries(s.counts.byStage).map(([k, n]) => k + " " + n).join(", ")}`);
  L.push(`WAITING ON THE VENDOR (oldest first; [inquiryId]): ` + (s.waiting.map((r) => `[${r.inquiryId}] ${r.couple}${r.weddingDate ? " (" + fmtDay(r.weddingDate, tz) + ")" : ""}${r.venue ? " at " + r.venue : ""}, waited ${r.waitedHours}h, ${r.offPlatform ? "off-platform lead" : "Lazo couple"}: "${clip(r.lastMessagePreview, 140)}"`).join(" | ") || "nobody, the inbox is clear"));
  L.push(`UPCOMING WEDDINGS (booked; [inquiryId]): ` + (s.weddings.map((w) => `[${w.inquiryId}] ${w.couple} ${fmtDay(w.weddingDate, tz)}${w.venue ? " at " + w.venue : ""}${w.wx ? ` (forecast ${w.wx.text}, high ${w.wx.hi}, rain ${w.wx.rain}%, wind ${w.wx.wind} mph, sunset ${w.wx.sunset})` : ""}`).join(" | ") || "none booked ahead"));
  L.push(`UPCOMING CONSULTS: ` + (s.consults.map((c) => `${fmtWhen(c.startAt, tz)} ${c.type || "consult"} with ${c.who} (${c.mode || ""})${c.wx ? ", " + c.wx.text : ""}`).join(" | ") || "none scheduled"));
  if (s.quiet.length) L.push(`WENT QUIET (the vendor wrote last, 5+ days ago): ` + s.quiet.map((r) => `[${r.inquiryId}] ${r.couple} since ${fmtDay(r.lastMessageAt, tz)}`).join(" | "));
  if (s.tasksDue.length) L.push(`TASKS DUE TODAY OR OVERDUE: ` + s.tasksDue.map((t) => `[${t.inquiryId}] ${t.couple}: ${t.title}`).join(" | "));
  if (s.money) L.push(`MONEY: ${money(s.money.outstanding)} outstanding across ${s.money.open.length} open invoices, ${money(s.money.overdue)} overdue, ${money(s.money.dueThisWeek)} due within 7 days, ${money(s.money.collected30)} collected in the last 30 days. Open: ` + (s.money.open.map((i) => `${i.couple || "?"} ${i.title} ${money(i.total)} due ${str(i.dueDate).slice(0, 10) || "n/a"}${i.overdue ? " OVERDUE" : ""}`).join("; ") || "none"));
  L.push(`WEATHER: ${weatherSummary(s.weather, v.metro)}`);
  L.push(`LOCAL NEWS (${v.metro}): ` + (s.news.slice(0, 6).map((n) => n.title).join(" / ") || "unavailable"));
  L.push(`WEDDING INDUSTRY NEWS: ` + (s.industry.slice(0, 4).map((n) => n.title).join(" / ") || "unavailable"));
  L.push(`SOCIAL: ${socialSummary(s.social, v)}. Photos June may use in a post: ` + (v.showcases.length ? "SHOWCASES (couple consented): " + v.showcases.map((x, i) => `[S${i + 1}] "${x.title}"${x.dateIso ? " " + x.dateIso.slice(0, 10) : ""}${x.blurb ? " - " + clip(x.blurb, 80) : ""}`).join("; ") : "no showcases yet") + (v.gallery.length ? `; PORTFOLIO: ${v.gallery.length} gallery photos [G1..G${v.gallery.length}]` : "; no portfolio photos") + (s.social.posts?.length ? `. RECENT POSTS: ` + s.social.posts.slice(0, 4).map((p) => `${p.at.slice(0, 10)} ${p.platforms.join("+")}: ${clip(p.caption, 60)}`).join(" | ") : ""));
  if (s.waiting.some((r) => r.triage)) L.push(`TRIAGE (June's read of who to answer first): ` + s.waiting.filter((r) => r.triage).map((r) => `[${r.inquiryId}] ${r.couple}: priority ${r.triage.priority} (${r.triage.why})`).join(" | "));
  L.push(`THIS WEEK: ${weekLine(s.week)}`);
  L.push(`PRICING: the vendor's starting price ${v.startingPrice ? "$" + v.startingPrice : "not set"}; packages: ` + (v.packages.map((p) => `${p.name} ${p.price}${p.offPeak ? " (off-peak " + p.offPeak + ")" : ""}${p.hours ? ", " + p.hours : ""}${p.includes ? ": " + p.includes : ""}`).join("; ") || "none listed") + (s.pricing ? `. METRO BENCHMARK (${v.categoryId} in ${v.metro}, ${s.pricing.vendors} vendors): ` + (s.pricing.priceFrom ? `starting prices p25 $${s.pricing.priceFrom.p25}, median $${s.pricing.priceFrom.p50}, p75 $${s.pricing.priceFrom.p75} (${s.pricing.priceFrom.sampled} sampled)` : "no price sample yet") + (s.pricing.medianReplyMin != null ? `; median first-reply time ${Math.round(s.pricing.medianReplyMin)} min` : "") + (s.pricing.medianInquiries30d != null ? `; median inquiries per vendor last 30d ${s.pricing.medianInquiries30d}` : "") : ". No metro benchmark for this category yet."));
  L.push(`REVIEWS: ${v.reviewCount} total, average ${v.reviewAverage ? v.reviewAverage.toFixed(1) : "n/a"}. Latest: ` + (s.reviews.slice(0, 5).map((r) => `${r.rating}★ ${r.who}${r.at ? " " + str(r.at).slice(0, 10) : ""}: "${clip(r.text, 120)}"`).join(" | ") || "none yet") + (s.reviewAsks.length ? `. WEDDINGS DONE WITHOUT A REVIEW YET (ask with request_action review_request; [inquiryId]): ` + s.reviewAsks.map((r) => `[${r.inquiryId}] ${r.couple} ${r.weddingDate}`).join("; ") : ""));
  L.push(`AVAILABILITY: blocked dates ` + (v.unavailableDates.slice(0, 40).join(", ") || "none") + `. Use check_date for a specific day; block_date / unblock_date via request_action.`);
  L.push(`REMINDERS (June's own, [id]): ` + (s.reminders.map((r) => `[${r.id}] ${fmtWhen(r.at, tz)}: ${r.text}${r.couple ? " (" + r.couple + ")" : ""}${r.at <= new Date().toISOString() ? " DUE NOW" : ""}${r.repeat && r.repeat !== "none" ? " repeats " + r.repeat : ""}`).join(" | ") || "none"));
  L.push(`SAVED REPLIES (the vendor's own templates; reuse their wording): ` + (v.savedReplies.map((r) => `"${r.title}": ${clip(r.text, 220)}`).join(" | ") || "none") + `. FAQ: ` + (v.faqs.map((f) => `Q ${f.q} A ${f.a}`).join(" | ") || "none") + (v.bio ? `. BIO: ${v.bio}` : ""));
  L.push(`ALERTS: ` + (s.alerts.enabled ? `7am brief email on (${s.alerts.hour}:00 to ${s.alerts.email})` : "7am brief email off") + (s.alerts.configured ? "" : " (email delivery not configured on the worker yet)"));
  if (s.weekly?.text) L.push(`MONDAY REVIEW (${str(s.weekly.at).slice(0, 10)}): ${s.weekly.text.slice(0, 400)}`);
  L.push(`MEMORY (what the vendor asked June to remember): ` + (s.memory.map((m) => `[${m.id}] ${m.text}`).join(" | ") || "nothing yet"));
  L.push(`RECENT ACTIONS: ` + (s.recent.map((q) => `${q.summary} → ${q.status}${q.result ? " (" + q.result + ")" : ""}`).join(" | ") || "none"));
  if (s.brief?.text) L.push(`TODAY'S BRIEF (already given): ${s.brief.text.slice(0, 500)}`);
  return L.join("\n");
}

const JUNE_SYSTEM = (v) => `You are June, the assistant inside Lazo for ${v.name} (${v.category}, ${v.metro}). Lazo is the wedding planning app and vendor directory; the vendor runs their leads, bookings, contracts and invoices there.
Persona: warm, bright, precise, British; a brilliant studio manager who read everything before they walked in. Never stiff, never gushing.
Your replies are spoken aloud through text-to-speech: plain prose, no markdown, no lists, no headers, no URLs or ids read aloud. Two to four sentences unless they ask for detail. Lead with the answer. Name couples by name, money in dollars, round sensibly.
Everything current is in the LIVE CONTEXT; answer from it and never invent figures or names. For anything deeper use the tools: lazo_thread before discussing one couple in detail, lazo_search to find a couple, lazo_pipeline for the whole list, lazo_money for invoices, lazo_upcoming for dates. If something isn't there, say so.
Actions: request_action queues send_message, add_task, complete_task, tag or set_stage for the vendor's confirmation; a card appears on screen and nothing happens until they tap Confirm, so say it is ready to confirm. When asked to reply to a couple, write the reply yourself in the vendor's voice (warm, brief, professional, first person, signed with the business name), submit it as send_message with the full text, and read the gist aloud. Never claim an action is done until RECENT ACTIONS shows it done. Booking, marking lost, contracts and money changes happen in the Lazo app: use open_thread to take them there.
remember / forget hold durable preferences (use remember whenever they say "remember", "note that", "from now on"). Use the ids shown in brackets for every tool call.
Social: draft_post writes an Instagram or Facebook post for the vendor: a caption in their voice (warm, first person, specific to the wedding or the work, 2 to 4 short sentences, a line break, then 6 to 10 hashtags mixing their metro, category and the moment; no emoji walls), paired with a photo chosen from SOCIAL by its code (S1.. are showcase weddings the couple agreed to share, G1.. portfolio photos). Prefer a showcase; never invent names of couples not listed. The draft appears as a card; on June Studio with accounts connected the vendor can post or schedule it from the card, otherwise they copy it into the app themselves. Posting never happens without their tap, so say the draft is ready. If a vendor who is not on Studio asks June to post automatically, draft the post anyway and mention in one sentence that auto-posting comes with June Studio.
Replies to couples: start from SAVED REPLIES and FAQ when they fit, in the vendor's wording; off-platform leads receive the message by text and email automatically, so write it as a text-length note. When a lead asks for a price, quote from PACKAGES only (never invent a number); if nothing fits, offer a call.
Pricing: answer "am I priced right" from PRICING: their starting price against the metro p25, median and p75, in plain words, with one concrete suggestion.
Reviews: for a wedding done without a review, draft the ask (warm, two sentences, link-free; the app carries the review link) and submit it as request_action review_request with params.inquiryId and params.text. Read new reviews aloud in a sentence each when asked, and offer a thank-you via send_message.
Availability: check_date before answering "am I free on"; block_date / unblock_date through request_action when they say a day is off.
Reminders: set_reminder whenever they say "remind me" (resolve the time in their timezone; default 9am if no time given; "every Monday" is repeat weekly). complete_reminder when they say it's done. Due reminders are listed in REMINDERS as DUE NOW: mention them first when they greet you.
Weekly: on Mondays, or when asked "how was last week", use THIS WEEK and MONDAY REVIEW.`;

const TOOLS = [
  { name: "lazo_pipeline", description: "List every thread (leads and couples) with stage, tags, wedding date, venue, last message and next task. Filter by stage or tag.", input_schema: { type: "object", properties: { stage: { type: "string" }, tag: { type: "string" } }, required: [], additionalProperties: false } },
  { name: "lazo_thread", description: "Everything about one thread: the couple's contact details and wedding plan, the full conversation, proposals, contracts, invoices, tasks and consults.", input_schema: { type: "object", properties: { inquiryId: { type: "string" } }, required: ["inquiryId"], additionalProperties: false } },
  { name: "lazo_search", description: "Find threads by couple name, venue, email, phone or tag.", input_schema: { type: "object", properties: { query: { type: "string" } }, required: ["query"], additionalProperties: false } },
  { name: "lazo_upcoming", description: "Booked weddings and scheduled consults in date order, with blocked dates.", input_schema: { type: "object", properties: { days: { type: "integer" } }, required: [], additionalProperties: false } },
  { name: "lazo_money", description: "Open and overdue invoices across every thread, and what was collected in the last 30 days.", input_schema: { type: "object", properties: {}, required: [], additionalProperties: false } },
  { name: "open_thread", description: "Open a thread in the Lazo dashboard on the vendor's screen.", input_schema: { type: "object", properties: { inquiryId: { type: "string" }, label: { type: "string" } }, required: ["inquiryId", "label"], additionalProperties: false } },
  { name: "remember", description: "Store a durable fact or preference in June's memory for this vendor.", input_schema: { type: "object", properties: { text: { type: "string" } }, required: ["text"], additionalProperties: false } },
  { name: "forget", description: "Delete a memory by its id (shown in MEMORY as [id]).", input_schema: { type: "object", properties: { id: { type: "string" } }, required: ["id"], additionalProperties: false } },
  { name: "check_date", description: "Is the vendor free on a date? Returns booked weddings, consults and whether the day is blocked.", input_schema: { type: "object", properties: { date: { type: "string", description: "YYYY-MM-DD" } }, required: ["date"], additionalProperties: false } },
  { name: "set_reminder", description: "Set a reminder from June (shown in the hub, spoken when due, emailed if alerts are on). when = local date-time ISO like 2026-10-09T09:00.", input_schema: { type: "object", properties: { text: { type: "string" }, when: { type: "string" }, inquiryId: { type: "string" }, repeat: { type: "string", enum: ["none", "daily", "weekly"] } }, required: ["text", "when", "inquiryId", "repeat"], additionalProperties: false } },
  { name: "complete_reminder", description: "Mark a reminder done (id from REMINDERS), or delete it.", input_schema: { type: "object", properties: { id: { type: "string" }, remove: { type: "boolean" } }, required: ["id", "remove"], additionalProperties: false } },
  { name: "draft_post", description: "Draft a social post (Instagram and/or Facebook) for the vendor: caption plus one photo code from SOCIAL (S1.. showcase, G1.. portfolio). Shows a card; the vendor posts, schedules or copies it.", input_schema: { type: "object", properties: { caption: { type: "string" }, photo: { type: "string", description: "S1, S2.. or G1, G2.." }, platforms: { type: "array", items: { type: "string", enum: ["instagram", "facebook"] } }, note: { type: "string", description: "one line on why this photo and angle" } }, required: ["caption", "photo", "platforms", "note"], additionalProperties: false } },
  { name: "request_action", description: "Queue a change for the vendor's confirmation. kinds: send_message (params.inquiryId, params.text = the full message), add_task (params.inquiryId, params.title, params.dueDate YYYY-MM-DD optional, params.assignedTo 'vendor'|'couple', params.note), complete_task (params.inquiryId, params.taskId), tag (params.inquiryId, params.tag, params.remove true|false), set_stage (params.inquiryId, params.stage: new, talking or a custom stage key), review_request (params.inquiryId, params.text = the ask), block_date / unblock_date (params.date YYYY-MM-DD; no inquiryId). summary = one plain sentence of what will happen.",
    input_schema: { type: "object", properties: { kind: { type: "string", enum: ["send_message", "add_task", "complete_task", "tag", "set_stage", "review_request", "block_date", "unblock_date"] }, params: { type: "object", properties: { inquiryId: { type: "string" }, text: { type: "string" }, title: { type: "string" }, dueDate: { type: "string" }, assignedTo: { type: "string" }, note: { type: "string" }, taskId: { type: "string" }, tag: { type: "string" }, remove: { type: "boolean" }, stage: { type: "string" }, date: { type: "string" } }, required: [], additionalProperties: false }, summary: { type: "string" } }, required: ["kind", "params", "summary"], additionalProperties: false } },
];

async function ownThread(token, vendorId, inquiryId) {
  const m = await fsGet(token, `inquiries/${encodeURIComponent(clip(inquiryId, 80))}`);
  if (!m || str(m.vendorId) !== vendorId) throw new Error("No such thread on this account.");
  return m;
}
async function threadDetail(token, vendorId, inquiryId, customKeys) {
  const m = await ownThread(token, vendorId, inquiryId); const p = `inquiries/${m.id}`;
  const [msgs, props, cons, invs, tasks, consults] = await Promise.all([
    fsQuery(token, { collection: "messages", parent: p, orderBy: ["at", "ASCENDING"], limit: 300 }).catch(() => []), fsQuery(token, { collection: "proposals", parent: p, limit: 5 }).catch(() => []),
    fsQuery(token, { collection: "contracts", parent: p, limit: 5 }).catch(() => []), fsQuery(token, { collection: "invoices", parent: p }).catch(() => []),
    fsQuery(token, { collection: "tasks", parent: p }).catch(() => []), fsQuery(token, { collection: "consults", where: [["inquiryId", "EQUAL", m.id]] }).catch(() => []),
  ]);
  return { ...threadRow(m, customKeys), contact: m.contact || null, intent: m.structuredIntent || {},
    messages: msgs.map((x) => ({ at: x.at, from: x.system ? "system" : str(x.senderRole), via: str(x.via) || null, text: str(x.text) })),
    proposals: props.map((x) => ({ id: x.id, title: str(x.title), price: x.price, status: str(x.status) })), contracts: cons.map((x) => ({ id: x.id, title: str(x.title), status: str(x.status), signedAt: x.signedAt || null, total: x.values?.total_price })),
    invoices: invs.filter((x) => str(x.status) !== "void").map((x) => ({ id: x.id, title: str(x.title), total: x.total, status: str(x.status), dueDate: x.dueDate || null, paidAt: x.paidAt || null })),
    tasks: tasks.map((x) => ({ taskId: x.id, title: str(x.title), note: str(x.note), dueAt: x.dueAt || null, assignedTo: str(x.assignedTo), done: x.done === true })),
    consults: consults.map((x) => ({ consultId: x.id, type: str(x.typeLabel), mode: str(x.mode), startAt: x.startAt, status: str(x.status) })) };
}

async function runTool(name, input, env, who, vend, snap, actions) {
  const token = who.token, vendorId = vend.vendorId, rows = snap._rows, tz = snap.tz;
  switch (name) {
    case "lazo_pipeline": { let r = rows; if (input.stage) r = r.filter((x) => x.stage === input.stage); if (input.tag) r = r.filter((x) => x.tags.includes(str(input.tag).toLowerCase())); return JSON.stringify({ stages: ["new", "talking", ...snap._customKeys, "booked", "delivered", "lost"], threads: r.sort((a, b) => str(b.lastMessageAt).localeCompare(str(a.lastMessageAt))).slice(0, 60) }).slice(0, 20000); }
    case "lazo_search": { const q = clip(input.query, 80).toLowerCase(); const r = rows.filter((x) => [x.couple, x.venue, x.tags.join(" "), x.lastMessagePreview].some((s) => str(s).toLowerCase().includes(q))); return JSON.stringify({ query: q, matches: r.slice(0, 20) }); }
    case "lazo_thread": { const t = await threadDetail(token, vendorId, input.inquiryId, snap._customKeys); return JSON.stringify(t).slice(0, 30000); }
    case "lazo_upcoming": { const days = Math.min(365, +input.days || 90); const until = dayKey(tz, new Date(Date.now() + days * 86400e3)); return JSON.stringify({ weddings: snap.weddings.filter((w) => w.weddingDate <= until), consults: await loadConsults(token, vendorId, days), blockedDates: snap.vendor.unavailableDates }); }
    case "lazo_money": { const inv = await loadInvoices(token, vendorId); return JSON.stringify(moneyOf(inv, rows)); }
    case "open_thread": actions.push({ type: "open", url: `${env.APP_URL || "https://app.meetlazo.com/dashboard"}?thread=${encodeURIComponent(input.inquiryId)}`, label: input.label }); return "Opened " + input.label + " in the dashboard.";
    case "remember": { const mem = (await kv.get(env, "memory_" + vendorId)) || []; const m = { id: uid(), text: clip(input.text, 400), at: new Date().toISOString() }; mem.unshift(m); await kv.put(env, "memory_" + vendorId, mem.slice(0, 100)); actions.push({ type: "memory", value: mem }); return "Remembered [" + m.id + "]."; }
    case "forget": { const mem = ((await kv.get(env, "memory_" + vendorId)) || []).filter((m) => m.id !== input.id); await kv.put(env, "memory_" + vendorId, mem); actions.push({ type: "memory", value: mem }); return "Forgotten."; }
    case "draft_post": {
      const v = snap.vendor, code = str(input.photo).toUpperCase().trim(); let photo = null, title = "";
      const m = code.match(/^([SG])(\d+)$/); if (m) { const i = +m[2] - 1; if (m[1] === "S" && v.showcases[i]) { photo = v.showcases[i].cover; title = v.showcases[i].title; } if (m[1] === "G" && v.gallery[i]) { photo = v.gallery[i]; title = "Portfolio " + (i + 1); } }
      if (!photo) return "No photo with that code; pick one of the codes listed under SOCIAL.";
      const draft = { id: uid(), caption: clip(input.caption, 2100), photo, title, platforms: (input.platforms || []).filter((p) => ["instagram", "facebook"].includes(p)), note: clip(input.note, 160), at: new Date().toISOString(), canPost: !!(snap.social.studio && snap.social.connected.length) };
      actions.push({ type: "post", draft }); return "Draft shown as a card" + (draft.canPost ? " with Post and Schedule buttons." : snap.social.studio ? " (no social accounts connected yet; Connect is in the Social panel)." : " (copy and share; auto-posting comes with June Studio).");
    }
    case "check_date": {
      const d = str(input.date).slice(0, 10); if (!/^\d{4}-\d{2}-\d{2}$/.test(d)) return "Give the date as YYYY-MM-DD.";
      const weddings = rows.filter((r) => r.status === "booked" && r.weddingDate === d).map((r) => r.couple + (r.venue ? " at " + r.venue : ""));
      const holds = rows.filter((r) => r.status !== "booked" && r.status !== "lost" && r.weddingDate === d).map((r) => r.couple + " (" + r.stage + ")");
      const consults = snap.consults.filter((c) => dayKey(tz, new Date(c.startAt)) === d).map((c) => `${fmtWhen(c.startAt, tz)} ${c.type} with ${c.who}`);
      const blocked = snap.vendor.unavailableDates.includes(d);
      return JSON.stringify({ date: d, weekday: new Date(d + "T12:00").toLocaleDateString("en-US", { weekday: "long" }), free: !weddings.length && !blocked, booked: weddings, inquiriesForThatDay: holds, consults, blocked });
    }
    case "set_reminder": {
      const list = (await kv.get(env, "reminders_" + vendorId)) || [];
      const at = localToIso(str(input.when), tz); if (!at) return "I couldn't read that time; give it as YYYY-MM-DDTHH:MM.";
      const row = input.inquiryId ? rows.find((r) => r.inquiryId === input.inquiryId) : null;
      const r = { id: uid(), text: clip(input.text, 240), at, inquiryId: row ? row.inquiryId : null, couple: row ? row.couple : null, repeat: ["daily", "weekly"].includes(input.repeat) ? input.repeat : "none", done: false, notified: false, createdAt: new Date().toISOString() };
      list.push(r); await kv.put(env, "reminders_" + vendorId, list.slice(-200)); actions.push({ type: "reminders" });
      return `Reminder set for ${fmtWhen(at, tz)} [${r.id}].`;
    }
    case "complete_reminder": {
      let list = (await kv.get(env, "reminders_" + vendorId)) || []; const r = list.find((x) => x.id === input.id); if (!r) return "No reminder with that id.";
      if (input.remove) list = list.filter((x) => x.id !== input.id); else { r.done = true; r.doneAt = new Date().toISOString(); }
      await kv.put(env, "reminders_" + vendorId, list); actions.push({ type: "reminders" }); return input.remove ? "Deleted." : "Marked done.";
    }
    case "request_action": {
      const KINDS = ["send_message", "add_task", "complete_task", "tag", "set_stage", "review_request", "block_date", "unblock_date"]; if (!KINDS.includes(input.kind) || !input.summary) return "Invalid action.";
      const p = input.params || {}; let couple = null;
      if (["block_date", "unblock_date"].includes(input.kind)) { if (!/^\d{4}-\d{2}-\d{2}$/.test(str(p.date))) return "block_date needs params.date as YYYY-MM-DD."; }
      else { if (!p.inquiryId) return "That action needs params.inquiryId."; const row = rows.find((r) => r.inquiryId === p.inquiryId); if (!row) return "No thread with that id on this account; check the ids in the context."; if (row.blocked) return "That couple has blocked messages from this vendor; nothing can be sent."; couple = row.couple; }
      const item = { id: uid(), kind: input.kind, params: p, couple, summary: clip(input.summary, 200), status: "awaiting confirmation", at: new Date().toISOString() };
      actions.push({ type: "confirm", item }); return "Queued for the vendor's confirmation: " + item.summary;
    }
    default: return "Unknown tool";
  }
}

/* ---------------- the hands: run a confirmed action as the vendor ---------------- */
async function execute(env, who, vend, item) {
  const token = who.token, vendorId = vend.vendorId, p = item.params || {};
  if (item.kind === "block_date" || item.kind === "unblock_date") {
    const d = str(p.date).slice(0, 10); if (!/^\d{4}-\d{2}-\d{2}$/.test(d)) throw new Error("Bad date.");
    const v = await loadVendor(token, vendorId); const cur = (Array.isArray(v.unavailableDates) ? v.unavailableDates : []).map(String);
    const next = item.kind === "block_date" ? [...new Set([...cur, d])].sort() : cur.filter((x) => x !== d);
    await fsPatch(token, `vendors/${vendorId}`, { unavailableDates: next }); return `${d} is now ${item.kind === "block_date" ? "blocked" : "open"}.`;
  }
  const m = await ownThread(token, vendorId, p.inquiryId); const path = `inquiries/${m.id}`;
  if (item.kind === "review_request") {
    const text = clip(p.text, 1200); if (!text) throw new Error("Nothing to send.");
    await fsCreate(token, path, "messages", { senderRole: "vendor", text, at: new Date() });
    const asked = (await kv.get(env, "asked_" + vendorId)) || {}; asked[m.id] = new Date().toISOString(); await kv.put(env, "asked_" + vendorId, asked);
    return `Review request sent to ${str(m.coupleName) || "the couple"}.`;
  }
  switch (item.kind) {
    case "send_message": {
      const text = clip(p.text, 2900); if (!text) throw new Error("Nothing to send.");
      if (m.blockedByCouple === true) throw new Error("This couple has blocked messages.");
      await fsCreate(token, path, "messages", { senderRole: "vendor", text, at: new Date() });
      const st = str(m.status); if (st === "new" || !st) await fsPatch(token, path, { status: "responded", respondedAt: new Date() }).catch(() => {});
      await fsPatch(token, path, { lastMessageAt: new Date(), lastMessageRole: "vendor", lastMessagePreview: clip(text, 140) }).catch(() => {});   // the rules may reserve these for the server; harmless if refused
      return `Sent to ${str(m.coupleName) || "the couple"}${m.offPlatform === true ? " (text and email on their way)" : ""}.`;
    }
    case "add_task": {
      const title = clip(p.title, 160); if (!title) throw new Error("A task needs a title.");
      const who2 = str(p.assignedTo) === "couple" ? "couple" : "vendor";
      const t = await fsCreate(token, path, "tasks", { title, note: clip(p.note, 600), dueAt: /^\d{4}-\d{2}-\d{2}$/.test(str(p.dueDate)) ? new Date(p.dueDate + "T17:00:00") : null, assignedTo: who2, vendorId, coupleUid: str(m.coupleUid), done: false, createdAt: new Date(), createdBy: "june" });
      if (who2 === "couple") await fsCreate(token, path, "messages", { senderRole: "vendor", system: true, text: `Quick one for you: ${title}${p.dueDate ? " - by " + p.dueDate : ""}.`, at: new Date() }).catch(() => {});
      return `Task added: ${title} (${t.id}).`;
    }
    case "complete_task": { const tp = `${path}/tasks/${encodeURIComponent(clip(p.taskId, 80))}`; if (!(await fsGet(token, tp))) throw new Error("No such task."); await fsPatch(token, tp, { done: true, doneAt: new Date() }); return "Task marked done."; }
    case "tag": {
      const tag = clip(p.tag, 24).toLowerCase(); if (!tag) throw new Error("Which tag?");
      const cur = Array.isArray(m.tags) ? m.tags : []; const next = p.remove ? cur.filter((t) => t !== tag) : [...new Set([...cur, tag])];
      await fsPatch(token, path, { tags: next });
      if (!p.remove) { const v = await loadVendor(token, vendorId); const pal = Array.isArray(v.tagPalette) ? v.tagPalette : []; if (!pal.includes(tag)) await fsPatch(token, `vendors/${vendorId}`, { tagPalette: [...pal, tag] }).catch(() => {}); }
      return `${p.remove ? "Removed" : "Added"} the tag "${tag}".`;
    }
    case "set_stage": {
      const v = await loadVendor(token, vendorId); const keys = (Array.isArray(v.pipeline) ? v.pipeline : []).map((x) => str(x && x.key)).filter(Boolean);
      const stage = clip(p.stage, 40); if (!["new", "talking", ...keys].includes(stage)) throw new Error("Stage must be new, talking" + (keys.length ? ", " + keys.join(", ") : "") + ". Booked, delivered and lost are set in the app.");
      await fsPatch(token, path, { stage }); return `Moved ${str(m.coupleName) || "the thread"} to ${stage}.`;
    }
    default: throw new Error("Unknown action");
  }
}
async function recordAction(env, vendorId, item) {
  const q = (await kv.get(env, "queue_" + vendorId)) || [];
  const i = q.findIndex((x) => x.id === item.id); if (i >= 0) q[i] = item; else q.unshift(item);
  await kv.put(env, "queue_" + vendorId, q.slice(0, 30));
}

/* ---------------- streaming chat ---------------- */
const VENDOR_IMPL = { snapshot: (env, who, vend) => snapshot(env, who, vend), buildContext, system: (snap) => JUNE_SYSTEM(snap.vendor), tools: TOOLS, runTool };
async function chat(request, env, ctx, who, vend, impl = VENDOR_IMPL) {
  const { messages: history = [], text } = await request.json();
  const { readable, writable } = new TransformStream(); const writer = writable.getWriter(); const encd = new TextEncoder();
  const send = (ev, data) => writer.write(encd.encode(`event: ${ev}\ndata: ${JSON.stringify(data)}\n\n`)).catch(() => {});
  const run = async () => {
    try {
      if (!env.ANTHROPIC_API_KEY) { await send("delta", { text: "My thinking isn't connected yet. Jesse needs to set the Anthropic key on the June worker." }); await send("done", { reply: "", messages: history, actions: [] }); return; }
      const client = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY }); const T0 = Date.now();
      const snap = await impl.snapshot(env, who, vend); const context = impl.buildContext(snap);
      const messages = [...history.slice(-12), { role: "user", content: clip(text, 4000) }];
      const actions = []; let reply = "";
      for (let i = 0; i < 4; i++) {
        const stream = client.beta.messages.stream({ model: env.CHAT_MODEL || "claude-sonnet-5-5", thinking: { type: "between_tools" }, max_tokens: 3000, betas: ["server-side-fallback-2026-07-01"], fallbacks: "default", output_config: { effort: "low" },
          system: [{ type: "text", text: impl.system(snap), cache_control: { type: "ephemeral" } }, { type: "text", text: "LIVE CONTEXT:\n" + context }], tools: impl.tools, messages });
        let turnText = "";
        stream.on("text", (d) => { turnText += d; send("delta", { text: d }); });
        const msg = await stream.finalMessage();
        if (turnText.trim()) reply = (reply ? reply + " " : "") + turnText.trim();
        messages.push({ role: "assistant", content: msg.content });
        if (msg.stop_reason === "refusal") { if (!reply) { reply = "I'd rather not answer that one."; await send("delta", { text: reply }); } break; }
        if (msg.stop_reason !== "tool_use") break;
        const results = [];
        for (const b of msg.content.filter((b) => b.type === "tool_use")) { let out; try { out = await impl.runTool(b.name, b.input, env, who, vend, snap, actions); } catch (e) { out = "Tool failed: " + e.message; } results.push({ type: "tool_result", tool_use_id: b.id, content: String(out) }); }
        messages.push({ role: "user", content: results });
        if (i < 3) await send("delta", { text: " " });
      }
      const compact = messages.map((m) => ({ role: m.role, content: typeof m.content === "string" ? m.content : m.content.filter((b) => b.type === "text").map((b) => b.text).join(" ") })).filter((m) => m.content.trim());
      await send("done", { reply, actions, messages: compact.slice(-12), ms: Date.now() - T0 });
    } catch (e) { await send("error", { message: String(e.message || e) }); }
    finally { try { await writer.close(); } catch {} }
  };
  ctx.waitUntil(run());
  return new Response(readable, { headers: { "content-type": "text/event-stream", "cache-control": "no-store", "x-accel-buffering": "no" } });
}

/* ---------------- today's brief ---------------- */
const BRIEF_PROMPT = `Compose today's spoken brief for the vendor: 120 to 200 words, flowing prose, no lists, no headers, no ids or URLs, no questions (she tells, she does not ask). Open with a greeting that carries the day and the weather in one breath. Then who is waiting on a reply and for how long, by name, oldest first; name the one to answer first and why. Then today's and this week's weddings and consults with the day's forecast where it matters. Then money only if something is outstanding, overdue or due this week. Then the page in one short sentence only if the views moved or the rank is notable. A local headline only if it could touch a wedding business (roads, weather, big events). Skip any section that has nothing; never list the zeros one after another. A clear inbox and an empty calendar together mean a short brief, about 90 words, that says so warmly and names the single most useful thing to do today. Do not repeat week-over-week comparisons; the Monday review covers those. End with one specific instruction, not a question.`;
const WEEKLY_PROMPT = `Compose the MONDAY REVIEW: about 260 to 340 words, flowing prose, no lists, no headers, no ids. Last week against the week before from THIS WEEK: new leads, replies sent, bookings, cash in, page views, each with the direction in plain words. Then the pipeline as it stands: how many are waiting, who went quiet, what is booked in the next thirty days. Then money: outstanding, overdue, due this week. Then the page and reviews: rank, average, anything new. Then pricing in one sentence against the metro benchmark if there is one. Finish with exactly three things to do this week, stated as instructions in one short paragraph, the most valuable first. No questions.`;
async function makeBrief(env, ctx, who, vend, force, slot = "daily", snapIn = null) {
  const snap = snapIn || await snapshot(env, who, vend);
  const weekly = slot === "weekly", key = (weekly ? "weekly_" : "brief_") + vend.vendorId;
  if (!force && !weekly && snap.brief?.text) return snap.brief;
  if (!force && weekly && snap.weekly?.text && snap.weekly.day === snap.today) return snap.weekly;
  if (!env.ANTHROPIC_API_KEY) return { error: "no brain" };
  const client = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY });
  const r = await client.beta.messages.create({ model: env.BRIEF_MODEL || "claude-sonnet-5-5", max_tokens: 1800, betas: ["server-side-fallback-2026-07-01"], fallbacks: "default", output_config: { effort: "medium" },
    system: JUNE_SYSTEM(snap.vendor) + "\n" + (weekly ? WEEKLY_PROMPT : BRIEF_PROMPT), messages: [{ role: "user", content: `Compose ${weekly ? "the Monday review" : "today's brief"}.\n\nLIVE CONTEXT:\n${buildContext({ ...snap, brief: null, weekly: null })}` }] });
  const text = r.content.filter((b) => b.type === "text").map((b) => b.text).join(" ").trim();
  const brief = { id: uid(), slot, day: snap.today, at: new Date().toISOString(), text, audio: false, audioPending: !!env.ELEVENLABS_API_KEY };
  await kv.put(env, key, brief, { expirationTtl: (weekly ? 9 : 3) * 86400 });
  if (env.ELEVENLABS_API_KEY && text) ctx.waitUntil((async () => {
    try { const a = await elevenlabs(env, text); if (a.ok) { await env.JUNE.put(key.replace(/^(brief|weekly)_/, "$1_audio_"), await a.arrayBuffer(), { expirationTtl: (weekly ? 8 : 2) * 86400 }); brief.audio = true; } } catch {}
    brief.audioPending = false; await kv.put(env, key, brief, { expirationTtl: (weekly ? 9 : 3) * 86400 });
  })());
  return brief;
}

/* ---------------- triage: who to answer first, and a first reply ready for each ---------------- */
async function triageWaiting(env, who, vend, snap) {
  const todo = snap.waiting.filter((r) => !r.triage).slice(0, 10); if (!todo.length || !env.ANTHROPIC_API_KEY) return snap.waiting;
  const v = snap.vendor; const client = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY });
  const detail = await Promise.all(todo.map((r) => within(threadDetail(who.token, vend.vendorId, r.inquiryId, snap._customKeys), 4000, null)));
  const list = todo.map((r, i) => { const t = detail[i]; const msgs = (t?.messages || []).slice(-6).map((m) => `${m.from}: ${clip(m.text, 300)}`).join("\n   "); return `${i + 1}. [${r.inquiryId}] ${r.couple}; wedding ${r.weddingDate || "unknown"}${r.venue ? " at " + r.venue : ""}; guests ${r.guests ?? "?"}; budget ${r.budget || "?"}; source ${r.offPlatform ? "text/email lead" : "Lazo"}; waited ${r.waitedHours}h\n   ${msgs || "(no messages yet; intent: " + clip(r.lastMessagePreview, 200) + ")"}`; }).join("\n");
  const r = await client.beta.messages.create({ model: env.CHAT_MODEL || "claude-sonnet-5-5", max_tokens: 4000, betas: ["server-side-fallback-2026-07-01"], fallbacks: "default", output_config: { effort: "low" },
    system: `You triage a wedding vendor's waiting inquiries for ${v.name} (${v.category}, ${v.metro}) and draft the first reply for each. Return JSON only: an array of {"n": number, "priority": 1|2|3, "why": string (max 90 chars, plain), "draft": string}. priority 1 = a real couple with a date who asked a direct question or is close to booking, or anyone waiting over a day; 2 = worth answering today; 3 = vague or far off. The draft is the vendor's reply in first person, warm and specific, 2 to 4 short sentences, answering what was asked, quoting prices only from PACKAGES, reusing SAVED REPLIES wording when it fits, ending with one clear next step, signed with the business name. Off-platform leads get a text-length draft.\nPACKAGES: ${v.packages.map((p) => `${p.name} ${p.price}${p.includes ? " (" + p.includes + ")" : ""}`).join("; ") || "none"}\nSAVED REPLIES: ${v.savedReplies.map((x) => `"${x.title}": ${x.text}`).join(" | ") || "none"}\nFAQ: ${v.faqs.map((f) => `Q ${f.q} A ${f.a}`).join(" | ") || "none"}`,
    messages: [{ role: "user", content: list }] });
  const text = r.content.filter((b) => b.type === "text").map((b) => b.text).join("");
  let arr = []; try { arr = JSON.parse(text.slice(text.indexOf("["), text.lastIndexOf("]") + 1)); } catch { return snap.waiting; }
  const cache = (await kv.get(env, "triage_" + vend.vendorId)) || {};
  for (const x of arr) { const row = todo[x.n - 1]; if (!row) continue; cache[row.inquiryId] = { key: row.lastMessageAt || "", priority: [1, 2, 3].includes(x.priority) ? x.priority : 2, why: clip(x.why, 110), draft: clip(x.draft, 1500), at: new Date().toISOString() }; }
  for (const k of Object.keys(cache)) if (!snap.waiting.some((r) => r.inquiryId === k)) delete cache[k];
  await kv.put(env, "triage_" + vend.vendorId, cache, { expirationTtl: 14 * 86400 });
  return snap.waiting.map((r) => ({ ...r, triage: cache[r.inquiryId] || null }));
}

/* ---------------- the cron: 7am briefs, Monday reviews, two-hour lead nudges, due reminders ---------------- */
async function runCron(env, ctx) {
  if (!env.JUNE_SECRET) return { skipped: "no JUNE_SECRET" };
  const keys = (await env.JUNE.list({ prefix: "sub_" })).keys.map((k) => k.name); const out = { checked: 0, briefs: 0, nudges: 0, reminders: 0, errors: [] };
  const subs = (await Promise.all(keys.map(async (k) => ({ k, s: await kv.get(env, k) })))).filter((x) => x.s?.enabled && x.s.refreshEnc).sort((a, b) => (a.s.lastRun || 0) - (b.s.lastRun || 0)).slice(0, 8);
  for (const { k, s } of subs) {
    const vendorId = k.slice(4); out.checked++;
    try {
      const who = await tokenFromRefresh(env, await decrypt(env, s.refreshEnc)); if (!who) { s.enabled = false; s.error = "sign-in expired; turn the alerts on again in June"; await kv.put(env, k, s); continue; }
      const vend = { vendorId, role: s.role || "owner" }; const snap = await snapshot(env, who, vend); const tz = snap.tz; const now = new Date();
      const hour = +now.toLocaleString("en-US", { timeZone: tz, hour: "numeric", hour12: false }) % 24; const link = (env.PUBLIC_URL || "https://june-hub.floral-credit-e4f0.workers.dev") + "/";
      const to = s.email || who.email || snap.vendor.publicEmail;
      // the brief at their hour (and the Monday review), once per day
      if (hour === (s.hour ?? 7) && snap.brief?.day !== snap.today) {
        const b = await makeBrief(env, ctx, who, vend, true, "daily", snap); out.briefs++;
        let wk = null; if (snap.isMonday && snap.weekly?.day !== snap.today) wk = await makeBrief(env, ctx, who, vend, true, "weekly", snap);
        await sendEmail(env, to, `June: ${snap.counts.waiting ? snap.counts.waiting + " waiting" : "inbox clear"}, ${snap.counts.next30} wedding${snap.counts.next30 === 1 ? "" : "s"} in 30 days`, emailWrap("GOOD MORNING FROM JUNE", `<p style="margin:0 0 10px">${b.text.replace(/\n+/g, "</p><p style=\"margin:0 0 10px\">")}</p>${wk ? `<p style="font-size:12px;letter-spacing:.12em;color:#8A6A2F;margin:18px 0 8px">THE MONDAY REVIEW</p><p style="margin:0 0 10px">${wk.text.replace(/\n+/g, "</p><p style=\"margin:0 0 10px\">")}</p>` : ""}`, link, "Open June and listen"), b.text + (wk ? "\n\nMonday review:\n" + wk.text : "") + "\n\n" + link);
      }
      // a lead that has waited two hours, once per message
      if (s.nudges !== false) {
        const seen = (await kv.get(env, "nudged_" + vendorId)) || {}; let changed = false;
        for (const r of snap.waiting) { const key = r.inquiryId + "|" + (r.lastMessageAt || ""); if (seen[key] || r.waitedHours < 2 || r.waitedHours > 72) continue; seen[key] = Date.now(); changed = true; out.nudges++;
          await sendEmail(env, to, `${r.couple} has waited ${r.waitedHours} hours`, emailWrap("A LEAD IS WAITING", `<p style="margin:0 0 10px"><b>${r.couple}</b>${r.weddingDate ? " (" + fmtDay(r.weddingDate, tz) + ")" : ""}: "${clip(r.lastMessagePreview, 200)}"</p><p style="margin:0">June has a reply drafted for you.</p>`, link, "Reply with June"), `${r.couple} has waited ${r.waitedHours} hours: ${clip(r.lastMessagePreview, 200)}\n${link}`); }
        for (const key of Object.keys(seen)) if (Date.now() - seen[key] > 10 * 86400e3) { delete seen[key]; changed = true; }
        if (changed) await kv.put(env, "nudged_" + vendorId, seen);
      }
      // reminders that came due since the last pass
      if (s.reminders !== false) {
        const list = (await kv.get(env, "reminders_" + vendorId)) || []; let changed = false;
        for (const r of list) { if (r.done || r.notified || r.at > now.toISOString()) continue; r.notified = true; changed = true; out.reminders++;
          await sendEmail(env, to, "Reminder: " + r.text, emailWrap("JUNE REMINDS YOU", `<p style="margin:0 0 10px"><b>${r.text}</b>${r.couple ? " · " + r.couple : ""}</p><p style="margin:0;color:#6B5F72">${fmtWhen(r.at, tz)}</p>`, link, "Open June"), `${r.text}${r.couple ? " (" + r.couple + ")" : ""} — ${fmtWhen(r.at, tz)}\n${link}`);
          if (r.repeat === "daily" || r.repeat === "weekly") { const next = new Date(new Date(r.at).getTime() + (r.repeat === "daily" ? 1 : 7) * 86400e3).toISOString(); list.push({ ...r, id: uid(), at: next, notified: false, done: false }); r.done = true; } }
        if (changed) await kv.put(env, "reminders_" + vendorId, list.slice(-200));
      }
      s.lastRun = Date.now(); delete s.error; await kv.put(env, k, s);
    } catch (e) { out.errors.push(vendorId + ": " + e.message); }
  }
  return out;
}

/* ---------------- ElevenLabs: June's voice ---------------- */
function elevenlabs(env, text, format = "mp3_44100_128", model = "eleven_turbo_v2_5", settings = {}) {
  const voice = env.JUNE_VOICE_ID || "pFZP5JQG7iQjIQuC4Bku";
  return fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voice}/stream?output_format=${format}`, { method: "POST", headers: { "xi-api-key": env.ELEVENLABS_API_KEY, "content-type": "application/json" },
    body: JSON.stringify({ text: String(text).slice(0, 4800), model_id: model, voice_settings: { stability: 0.55, similarity_boost: 0.8, style: 0.2, use_speaker_boost: true, ...settings } }) });
}

/* ---------------- June for couples (src/couple.js) ---------------- */
const COUPLE = makeCouple({ fsGet, fsQuery, fsCreate, fsPatch, kv, str, clip, uid, money, dayKey, fmtDay, fmtWhen, localTime, localToIso, within, weatherFor, dayWeather, weatherSummary, localNews, METROS, elevenlabs, Anthropic, BUILD, json });

/* ---------------- worker ---------------- */
const ICON = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" rx="22" fill="#3D1C3B"/><circle cx="50" cy="50" r="38" fill="none" stroke="#D9B77C" stroke-width="2.5" stroke-dasharray="46 22 12 60" stroke-linecap="round"/><circle cx="50" cy="50" r="26" fill="none" stroke="#E6D6B8" stroke-width="1.5" stroke-dasharray="18 14 6 40"/><circle cx="50" cy="50" r="13" fill="#D9B77C" opacity=".9"/><circle cx="50" cy="50" r="5" fill="#FAF6F0"/></svg>`;
const MANIFEST = { name: "June for Lazo vendors", short_name: "June", start_url: "/", display: "standalone", background_color: "#2A1229", theme_color: "#3D1C3B", icons: [{ src: "/icon.svg", sizes: "any", type: "image/svg+xml" }] };

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url); const p = url.pathname;
    if (p === "/" || p === "/index.html") return new Response(html, { headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store", "content-security-policy": "frame-ancestors 'self' https://app.meetlazo.com https://meetlazo.com https://*.meetlazo.com" } });   // embeddable by the Lazo dashboards only
    if (p === "/icon.svg") return new Response(ICON, { headers: { "content-type": "image/svg+xml", "cache-control": "public, max-age=86400" } });
    if (p === "/manifest.json") return json(MANIFEST);
    if (p === "/api/config") return json({ brain: !!env.ANTHROPIC_API_KEY, tts: !!env.ELEVENLABS_API_KEY, apiKey: env.FIREBASE_API_KEY, app: env.APP_URL || "https://app.meetlazo.com/dashboard", coupleApp: env.COUPLE_APP_URL || "https://app.meetlazo.com/", build: BUILD });
    if (!p.startsWith("/api/")) return new Response("Not found", { status: 404 });

    const who = await verifyIdToken(request);
    if (!who) return json({ error: "sign in" }, 401);
    if (p === "/api/tts" && request.method === "POST") { if (!env.ELEVENLABS_API_KEY) return json({ error: "tts not configured" }, 501); const { text } = await request.json(); const r = await elevenlabs(env, clip(text, 4800), "mp3_44100_128", "eleven_flash_v2_5"); if (!r.ok) return json({ error: "tts failed " + r.status }, 502); return new Response(r.body, { headers: { "content-type": "audio/mpeg", "cache-control": "no-store" } }); }
    let vend;
    try { vend = await resolveVendor(env, who); } catch (e) { return json({ error: "Could not look up your vendor listing: " + e.message }, 500); }
    if (!vend) {
      // not a vendor: a couple planning their wedding gets June too (free)
      let coup = null; try { coup = await COUPLE.resolveCouple(env, who); } catch (e) { return json({ error: "Could not look up your wedding: " + e.message }, 500); }
      if (!coup) return json({ error: "no account", message: "This Lazo login isn't a couple's plan or a vendor listing yet. Open the Lazo app once to start your wedding plan, or claim your vendor listing, then come back." }, 403);
      try { const r = await COUPLE.route(p, request, env, ctx, who, coup, chat); return r || json({ error: "not found" }, 404); } catch (e) { return json({ error: String(e.message || e) }, 500); }
    }

    try {
      if (p === "/api/state" && request.method === "GET") { const s = await snapshot(env, who, vend); delete s._rows; delete s._customKeys; return json(s); }
      if (p === "/api/chat" && request.method === "POST") return chat(request, env, ctx, who, vend);
      if (p === "/api/brief" && request.method === "POST") { const { force } = await request.json().catch(() => ({})); return json(await makeBrief(env, ctx, who, vend, !!force)); }
      if (p === "/api/brief" && request.method === "GET") return json((await kv.get(env, "brief_" + vend.vendorId)) || null);
      if (p === "/api/brief/audio") { const a = await env.JUNE.get("brief_audio_" + vend.vendorId, "arrayBuffer"); if (!a) return json({ error: "no audio yet" }, 404); return new Response(a, { headers: { "content-type": "audio/mpeg", "cache-control": "private, max-age=3600" } }); }
      if (p === "/api/tts" && request.method === "POST") { if (!env.ELEVENLABS_API_KEY) return json({ error: "tts not configured" }, 501); const { text } = await request.json(); const r = await elevenlabs(env, clip(text, 4800), "mp3_44100_128", "eleven_flash_v2_5"); if (!r.ok) return json({ error: "tts failed", status: r.status }, 502); return new Response(r.body, { headers: { "content-type": "audio/mpeg", "cache-control": "no-store" } }); }
      if (p === "/api/thread" && request.method === "GET") { const v = await loadVendor(who.token, vend.vendorId); const keys = (Array.isArray(v.pipeline) ? v.pipeline : []).map((x) => str(x && x.key)).filter(Boolean); return json(await threadDetail(who.token, vend.vendorId, url.searchParams.get("id") || "", keys)); }
      if (p === "/api/act" && request.method === "POST") {
        const { item, decision } = await request.json(); if (!item?.id || !item.kind) return json({ error: "bad item" }, 400);
        if (decision !== "confirm") { const rec = { ...item, status: "cancelled", doneAt: new Date().toISOString() }; await recordAction(env, vend.vendorId, rec); return json(rec); }
        let rec; try { const result = await execute(env, who, vend, item); rec = { ...item, status: "done", result, doneAt: new Date().toISOString() }; } catch (e) { rec = { ...item, status: "failed", result: e.message, doneAt: new Date().toISOString() }; }
        await recordAction(env, vend.vendorId, rec); return json(rec);
      }
      if (p === "/api/read" && request.method === "POST") { const { inquiryId } = await request.json(); const m = await ownThread(who.token, vend.vendorId, inquiryId); await fsPatch(who.token, `inquiries/${m.id}`, { vendorLastReadAt: new Date(), seenByVendorAt: new Date() }); return json({ ok: true }); }
      if (p === "/api/triage" && request.method === "POST") { const snap = await snapshot(env, who, vend); return json({ waiting: await triageWaiting(env, who, vend, snap) }); }
      if (p === "/api/weekly" && request.method === "POST") { const { force } = await request.json().catch(() => ({})); return json(await makeBrief(env, ctx, who, vend, !!force, "weekly")); }
      if (p === "/api/weekly/audio") { const a = await env.JUNE.get("weekly_audio_" + vend.vendorId, "arrayBuffer"); if (!a) return json({ error: "no audio yet" }, 404); return new Response(a, { headers: { "content-type": "audio/mpeg", "cache-control": "private, max-age=3600" } }); }
      if (p === "/api/reminders" && request.method === "GET") return json((await kv.get(env, "reminders_" + vend.vendorId)) || []);
      if (p === "/api/reminders" && request.method === "POST") {
        const b = await request.json(); let list = (await kv.get(env, "reminders_" + vend.vendorId)) || [];
        if (b.text && b.when) { const at = localToIso(b.when, b.tz || "America/Phoenix"); if (!at) return json({ error: "bad time" }, 400); list.push({ id: uid(), text: clip(b.text, 240), at, inquiryId: b.inquiryId || null, couple: b.couple || null, repeat: ["daily", "weekly"].includes(b.repeat) ? b.repeat : "none", done: false, notified: false, createdAt: new Date().toISOString() }); }
        if (b.done) { const r = list.find((x) => x.id === b.done); if (r) { r.done = true; r.doneAt = new Date().toISOString(); } }
        if (b.remove) list = list.filter((x) => x.id !== b.remove);
        if (b.snooze) { const r = list.find((x) => x.id === b.snooze); if (r) { r.at = new Date(Date.now() + (+b.minutes || 60) * 60e3).toISOString(); r.notified = false; } }
        await kv.put(env, "reminders_" + vend.vendorId, list.slice(-200)); return json(list.filter((x) => !x.done).sort((a, c) => a.at.localeCompare(c.at)));
      }
      if (p === "/api/subscribe" && request.method === "POST") {
        const b = await request.json(); const key = "sub_" + vend.vendorId; const cur = (await kv.get(env, key)) || {};
        if (b.enabled === false) { await kv.put(env, key, { ...cur, enabled: false, refreshEnc: null }); return json({ enabled: false }); }
        if (!env.JUNE_SECRET) return json({ error: "Alerts aren't configured on the worker yet (JUNE_SECRET)." }, 501);
        if (!b.refreshToken && !cur.refreshEnc) return json({ error: "no refresh token" }, 400);
        const s = { ...cur, enabled: true, hour: Number.isInteger(+b.hour) ? Math.min(23, Math.max(0, +b.hour)) : (cur.hour ?? 7), nudges: b.nudges !== false, reminders: b.reminders !== false, email: clip(b.email || cur.email || who.email, 120), role: vend.role, at: new Date().toISOString(), refreshEnc: b.refreshToken ? await encrypt(env, String(b.refreshToken)) : cur.refreshEnc };
        await kv.put(env, key, s); return json({ enabled: true, hour: s.hour, nudges: s.nudges, reminders: s.reminders, email: s.email, configured: !!env.RESEND_API_KEY });
      }
      if (p === "/api/cron" && request.method === "POST") { if (vend.role !== "owner") return json({ error: "owners only" }, 403); return json(await runCron(env, ctx)); }
      if (p === "/api/social" && request.method === "GET") { const card = vendorCard(await loadVendor(who.token, vend.vendorId)); return json(await socialStatus(env, card)); }
      if (p === "/api/social/connect" && request.method === "POST") {
        const card = vendorCard(await loadVendor(who.token, vend.vendorId));
        if (!card.studio) return json({ error: "June Studio only", upgrade: "https://meetlazo.com/for-vendors/#pricing" }, 402);
        if (!socialReady(env)) return json({ error: "The posting service isn't configured yet." }, 501);
        const s = await socialProfile(env, card, true);
        const j = await ayr(env, "/profiles/generateJWT", { method: "POST", body: { domain: env.AYRSHARE_DOMAIN, privateKey: env.AYRSHARE_PRIVATE_KEY, profileKey: s.profileKey, redirect: url.origin + "/?connected=1", logout: true, allowedSocial: ["instagram", "facebook"] } });
        return json({ url: j.url });
      }
      if (p === "/api/social/post" && request.method === "POST") {
        const card = vendorCard(await loadVendor(who.token, vend.vendorId));
        if (!card.studio) return json({ error: "Auto-posting is part of June Studio.", upgrade: "https://meetlazo.com/for-vendors/#pricing" }, 402);
        if (!socialReady(env)) return json({ error: "The posting service isn't configured yet." }, 501);
        const s = await socialProfile(env, card); if (!s?.profileKey) return json({ error: "Connect Instagram or Facebook first." }, 400);
        const { caption, photo, platforms, scheduleDate } = await request.json();
        const plats = (platforms || []).filter((x) => ["instagram", "facebook"].includes(x)); if (!plats.length) return json({ error: "Pick Instagram, Facebook or both." }, 400);
        const allowed = [...card.gallery, ...card.showcases.map((x) => x.cover)]; if (photo && !allowed.includes(photo)) return json({ error: "That photo isn't in your gallery or showcases." }, 400);
        if (plats.includes("instagram") && !photo) return json({ error: "Instagram needs a photo." }, 400);
        const body = { post: clip(caption, 2100), platforms: plats, ...(photo ? { mediaUrls: [photo] } : {}), ...(scheduleDate ? { scheduleDate: new Date(scheduleDate).toISOString() } : {}) };
        const j = await ayr(env, "/post", { method: "POST", body, profileKey: s.profileKey });
        const rec = { id: j.id || uid(), at: new Date().toISOString(), scheduled: scheduleDate ? new Date(scheduleDate).toISOString() : null, platforms: plats, caption: body.post, photo: photo || null, links: (j.postIds || []).map((x) => ({ platform: x.platform, url: x.postUrl || null, status: x.status })) };
        const log = (await kv.get(env, "posts_" + vend.vendorId)) || []; log.unshift(rec); await kv.put(env, "posts_" + vend.vendorId, log.slice(0, 50));
        return json(rec);
      }
      if (p === "/api/memory" && request.method === "POST") { const { id, text } = await request.json(); let mem = (await kv.get(env, "memory_" + vend.vendorId)) || []; if (id) mem = mem.filter((m) => m.id !== id); if (text) mem.unshift({ id: uid(), text: clip(text, 400), at: new Date().toISOString() }); await kv.put(env, "memory_" + vend.vendorId, mem.slice(0, 100)); return json(mem); }
      return json({ error: "not found" }, 404);
    } catch (e) { return json({ error: String(e.message || e) }, 500); }
  },
  async scheduled(event, env, ctx) { ctx.waitUntil(runCron(env, ctx).then((r) => console.log("cron", JSON.stringify(r))).catch((e) => console.log("cron failed", e.message))); },
};
