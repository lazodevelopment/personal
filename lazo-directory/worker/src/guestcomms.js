// JC-LAZO-GUESTCOMMS-1019: two things Zola's couple side has that Lazo lacked.
//
//  1. The contact collector - GET /w/{slug}/contact?k={key} is a small form a guest
//     fills in (name, email, phone, mailing address, plus-one); POST writes the guest
//     into couples/{coupleUid}/guests as the worker (rules 1019-COLLECT: create only,
//     source 'collector'). The couple turns it on from the Website screen, which writes
//     collectorOn + collectorKey on the weddingSites doc (public, so the edge can check
//     the key without reading the couple's private doc).
//  2. Message your guests - POST /api/w/{slug}/guest-message, signed with the couple's
//     Firebase ID token like the day-before note: subject + message + audience
//     (all | yes | pending | no | group:<name>), sent through Resend to every guest in
//     the audience with an email; {test: true} sends only to the caller. A copy lands in
//     couples/{coupleUid}/guestMessages (written as the couple, so the rules decide).
import { verifyIdToken, fsListAs, fsPatchAs, ownsSite } from "./auth.js";
import { fsHeaders } from "./fsauth.js";

const PROJECT = "lazo-513ec";
const CORS = { "access-control-allow-origin": "*", "access-control-allow-methods": "GET, POST, OPTIONS",
  "access-control-allow-headers": "content-type, authorization" };
const json = (obj, status = 200) => new Response(JSON.stringify(obj), { status,
  headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", ...CORS } });
const esc = (t) => String(t == null ? "" : t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
function fsVal(v) {
  if (v == null) return null;
  if ("stringValue" in v) return v.stringValue;
  if ("integerValue" in v) return Number(v.integerValue);
  if ("doubleValue" in v) return v.doubleValue;
  if ("booleanValue" in v) return v.booleanValue;
  if ("timestampValue" in v) return v.timestampValue;
  if ("arrayValue" in v) return (v.arrayValue.values || []).map(fsVal);
  if ("mapValue" in v) { const o = {}; for (const [k, x] of Object.entries(v.mapValue.fields || {})) o[k] = fsVal(x); return o; }
  return null;
}
const fsFields = (doc) => { const out = {}; for (const [k, v] of Object.entries((doc && doc.fields) || {})) out[k] = fsVal(v); return out; };
async function site(slug) {
  const r = await fetch(`https://firestore.googleapis.com/v1/projects/${PROJECT}/databases/(default)/documents/weddingSites/${encodeURIComponent(slug)}`,
    { headers: await fsHeaders() });
  return r.ok ? fsFields(await r.json()) : null;
}
const okSlug = (s) => /^[a-z0-9-]{1,80}$/.test(s || "");
const okEmail = (e) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(e || "");

// ---------------------------------------------------------------- the contact collector
const P = "#52284F", G = "#D9B77C", M = "#6B5F72";
function page(title, inner, names) {
  return new Response(`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>${esc(title)}</title>
<style>body{margin:0;background:#FAF6F0;color:#241E2B;font-family:Helvetica,Arial,sans-serif}.g{max-width:520px;margin:0 auto;padding:34px 20px 60px}
.k{font-size:11px;letter-spacing:3px;text-transform:uppercase;color:${G};margin:0 0 6px}h1{font-family:Georgia,serif;font-weight:600;font-size:30px;color:${P};margin:0 0 6px;line-height:1.1}
p{line-height:1.5}label{display:block;font-size:12px;color:${M};margin:14px 0 4px;letter-spacing:.5px}
input,textarea{width:100%;box-sizing:border-box;border:1px solid #E6D6B8;border-radius:10px;padding:12px;font-size:16px;background:#fff;font-family:inherit}
button{margin-top:20px;width:100%;background:${P};color:#FAF6F0;border:0;border-radius:10px;padding:14px;font-size:15px;font-weight:700;cursor:pointer}
.f{color:${M};font-size:12px;margin-top:26px}a{color:${P}}.ok{background:#fff;border:1px solid #E6D6B8;border-radius:14px;padding:22px;margin-top:18px}</style></head>
<body><div class="g"><p class="k">${esc(names || "A wedding")}</p>${inner}
<p class="f">Your details go only to ${esc(names || "the couple")}, through <a href="https://meetlazo.com">Lazo</a>.</p></div></body></html>`,
    { headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store", "x-robots-tag": "noindex" } });
}

export async function contactRoute(slug, req, url) {
  if (!okSlug(slug)) return null;
  const s = await site(slug);
  if (!s) return page("Not found", `<h1>Hmm, nothing here.</h1><p>Ask the couple for their current link.</p>`);
  const names = String(s.names || "the couple");
  const key = String(url.searchParams.get("k") || "");
  const live = s.collectorOn === true && s.collectorKey && key === String(s.collectorKey);
  if (!live) return page("Link closed", `<h1>This link isn’t open right now.</h1><p>${esc(names)} may have closed it. Ask them for the current one.</p>`, names);
  if (req.method === "GET") {
    return page(`${names} would love your address`, `<h1>Can you share your details?</h1>
<p>${esc(names)} are putting their guest list together. Tap in your name and mailing address so the invitation finds you.</p>
<form method="post" action="/w/${encodeURIComponent(slug)}/contact?k=${encodeURIComponent(key)}">
<input type="text" name="website" value="" style="display:none" tabindex="-1" autocomplete="off">
<label>Your full name</label><input name="name" required maxlength="80" autocomplete="name">
<label>Plus one or family coming with you (optional)</label><input name="party" maxlength="120">
<label>Mailing address</label><textarea name="address" rows="3" maxlength="300" autocomplete="street-address"></textarea>
<label>Email</label><input name="email" type="email" maxlength="120" autocomplete="email">
<label>Mobile (optional)</label><input name="phone" type="tel" maxlength="30" autocomplete="tel">
<button type="submit">Send to ${esc(names)}</button></form>`, names);
  }
  if (req.method !== "POST") return json({ ok: false, error: "method" }, 405);
  let b = {};
  try {
    const ct = req.headers.get("content-type") || "";
    if (ct.includes("application/json")) b = await req.json();
    else { const fd = await req.formData(); for (const [k, v] of fd.entries()) b[k] = String(v); }
  } catch (e) { return json({ ok: false, error: "body" }, 400); }
  if (b.website) return page("Thank you", `<div class="ok"><h1>Thank you!</h1></div>`, names); // honeypot
  const name = String(b.name || "").trim().slice(0, 80);
  if (!name) return page("Missing name", `<h1>We need your name.</h1><p><a href="javascript:history.back()">Go back</a> and add it.</p>`, names);
  const email = String(b.email || "").trim().toLowerCase().slice(0, 120);
  const cid = String(s.coupleUid || "");
  if (!cid) return json({ ok: false, error: "no_couple" }, 404);
  const str = (k, n) => ({ stringValue: String(b[k] || "").trim().slice(0, n) });
  const fields = {
    name: { stringValue: name }, email: { stringValue: okEmail(email) ? email : "" }, phone: str("phone", 30),
    address: str("address", 300), party: str("party", 120), plusOnes: { integerValue: "0" },
    rsvp: { stringValue: "pending" }, group: { stringValue: "" }, source: { stringValue: "collector" },
    createdAt: { timestampValue: new Date().toISOString() },
  };
  const r = await fetch(`https://firestore.googleapis.com/v1/projects/${PROJECT}/databases/(default)/documents/couples/${encodeURIComponent(cid)}/guests`,
    { method: "POST", headers: { ...(await fsHeaders()), "content-type": "application/json" }, body: JSON.stringify({ fields }) });
  if (!r.ok) return page("Try again", `<h1>That didn’t save.</h1><p>Please <a href="javascript:history.back()">go back</a> and try once more.</p>`, names);
  return page("Thank you", `<div class="ok"><h1>Got it, ${esc(name.split(" ")[0])}.</h1><p>${esc(names)} have your details. Watch the mail.</p>
${s.published !== false ? `<p><a href="https://meetlazo.com/w/${encodeURIComponent(slug)}/">See their wedding site</a></p>` : ""}</div>`, names);
}

// ---------------------------------------------------------------- message your guests
export async function guestMessageRoute(slug, req, env) {
  if (req.method === "OPTIONS") return new Response(null, { headers: CORS });
  if (req.method !== "POST") return json({ ok: false, error: "method" }, 405);
  if (!env.RESEND_API_KEY) return json({ ok: false, error: "no_mailer", message: "Email isn’t set up on the server yet." }, 503);
  const who = await verifyIdToken(req);
  if (!who) return json({ ok: false, error: "unauthenticated" }, 401);
  const s = await site(slug);
  if (!s) return json({ ok: false, error: "not_found" }, 404);
  if (!(await ownsSite(who, { coupleUid: s.coupleUid }))) return json({ ok: false, error: "forbidden" }, 403);
  let b = {}; try { b = await req.json(); } catch (e) {}
  const test = b.test === true;
  const subject = String(b.subject || "").trim().slice(0, 140);
  const message = String(b.message || "").trim().slice(0, 4000);
  if (!subject || !message) return json({ ok: false, error: "empty", message: "Give it a subject and a message." }, 400);
  const audience = String(b.audience || "all").slice(0, 80);
  const replyTo = okEmail(String(b.replyTo || "")) ? String(b.replyTo) : (who.email || "");
  const names = String(s.names || "the couple");
  const cid = String(s.coupleUid || "");

  const seen = new Set(); const to = [];
  const add = (name, email) => { email = String(email || "").trim().toLowerCase(); if (!okEmail(email) || seen.has(email)) return; seen.add(email); to.push({ name: String(name || "").trim(), email }); };
  let pool = 0;
  if (test) add(who.email, who.email);
  else {
    for (const d of await fsListAs(who.token, `couples/${encodeURIComponent(cid)}/guests`)) {
      const g = fsFields(d); pool++;
      const r = String(g.rsvp || "pending");
      const ok = audience === "all" || (audience === "yes" && r === "yes") || (audience === "no" && r === "no")
        || (audience === "pending" && r !== "yes" && r !== "no")
        || (audience.startsWith("group:") && String(g.group || "") === audience.slice(6));
      if (ok) add(g.name, g.email);
    }
  }
  if (!to.length) return json({ ok: false, error: "no_recipients", message: pool ? "Nobody in that group has an email on file." : "Add guests with emails first." }, 400);

  const siteUrl = `https://meetlazo.com/w/${encodeURIComponent(slug)}/`;
  const html = (g) => `<div style="max-width:560px;margin:0 auto;font-family:Helvetica,Arial,sans-serif;color:#241E2B;background:#FAF6F0;padding:28px 22px">
<p style="font-size:11px;letter-spacing:3px;text-transform:uppercase;color:${G};margin:0 0 6px">${esc(names)}</p>
<h1 style="font-family:Georgia,serif;font-weight:600;font-size:26px;color:${P};margin:0 0 14px;line-height:1.15">${esc(subject)}</h1>
${g.name ? `<p style="color:${M};font-size:14px;margin:0 0 14px">Hi ${esc(g.name.split(" ")[0])},</p>` : ""}
<p style="font-size:15px;line-height:1.6;margin:0 0 18px;white-space:pre-line">${esc(message)}</p>
${s.published !== false ? `<p style="margin:22px 0 0"><a href="${siteUrl}" style="display:inline-block;background:${P};color:#FAF6F0;text-decoration:none;padding:12px 20px;border-radius:10px;font-weight:700;font-size:14px">Our wedding site</a></p>` : ""}
<p style="color:${M};font-size:12px;margin-top:22px">Sent by ${esc(names)} through <a href="https://meetlazo.com" style="color:${P}">Lazo</a>. Reply and it reaches them.</p></div>`;
  const from = env.DAYB4_FROM || env.CONTACT_FROM || "Lazo <noreply@meetlazo.com>";
  let sent = 0, failed = 0;
  for (let i = 0; i < to.length; i += 5) {
    await Promise.all(to.slice(i, i + 5).map(async (g) => {
      try {
        const r = await fetch("https://api.resend.com/emails", { method: "POST",
          headers: { "content-type": "application/json", authorization: `Bearer ${env.RESEND_API_KEY}` },
          body: JSON.stringify({ from, to: [g.email], reply_to: replyTo || undefined, subject: `${test ? "[test] " : ""}${subject}`, html: html(g) }) });
        if (r.ok) sent++; else failed++;
      } catch (e) { failed++; }
    }));
  }
  if (!test && sent) {
    const id = Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
    await fsPatchAs(who.token, `couples/${encodeURIComponent(cid)}/guestMessages/${id}`, {
      subject: { stringValue: subject }, message: { stringValue: message }, audience: { stringValue: audience },
      sent: { integerValue: String(sent) }, failed: { integerValue: String(failed) },
      sentAt: { timestampValue: new Date().toISOString() }, by: { stringValue: who.uid },
    }, ["subject", "message", "audience", "sent", "failed", "sentAt", "by"]);
  }
  return json({ ok: true, sent, failed, recipients: to.length, test });
}
