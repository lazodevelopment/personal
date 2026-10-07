// functions-dashboard/couple-notify.js
// Build ID: JC-LAZO-FNDASH-1007-025 (025: preview couples skipped; base 024)
//
// THE COUPLE HEARS ABOUT EVERYTHING THAT MATTERS. Until now a Lazo couple (one
// with an account, not an off-platform lead) got email only for a contract to
// sign, a payment plan, payment reminders, a task, a consult and a vendor hello.
// Nothing for a vendor's reply, a proposal, a booking, a signed agreement, an
// invoice, a payment received, a questionnaire, a sneak peek, a delivered
// gallery, or a released date. These triggers close that:
//
//   coupleOnMessage        inquiries/{id}/messages created by the vendor ->
//                          "<Vendor> replied" (sneak peek / film teaser get
//                          their own subject and layout). Skipped while the
//                          couple is in the thread (coupleActiveAt < 3 min).
//   coupleOnProposal       proposals created -> "Your proposal from <Vendor>"
//   coupleOnContract       contracts written, status -> signed -> "It's signed."
//   coupleOnInvoice        invoices written: created as sent (not a payment-plan
//                          instalment, those have their own mail) -> "Invoice
//                          from <Vendor>"; status -> paid -> the receipt
//   coupleOnQuestionnaire  questionnaires created -> "<Vendor> has a few questions"
//   coupleOnInquiry        inquiries updated: status -> booked -> "You're booked";
//                          deliveredAt set -> "Your gallery/film is ready";
//                          unbookedAt set -> "<Vendor> released your date"
//
// Vendor-originated mail (reply, proposal, invoice, questionnaire, sneak peek)
// goes out in the vendor's own brand through brand.js, the convention every
// couple-facing email already follows. Milestones Lazo itself is marking
// (booked, signed, paid, delivered, released) use the Lazo frame.
// Recipients: the couple's own login plus any partner on the shared plan
// (users.coupleUid). couples.emailOk === false mutes everything here. Each
// trigger marks what it sent on the document so retries never double-send.
// Practice couples (demo) and off-platform leads are skipped.

'use strict';

const { onDocumentCreated, onDocumentWritten, onDocumentUpdated } = require('firebase-functions/v2/firestore');
const admin = require('firebase-admin');
const { wrap: brandWrap } = require('./brand');
const F = require('./email-frame');

module.exports = function coupleNotify(RESEND_API_KEY) {
  const db = () => admin.firestore();
  const FieldValue = admin.firestore.FieldValue;
  const { str, esc, money, frame, facts, quote, APP, JUNE, SITE } = F;
  const emailOk = (e) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(str(e).trim());
  const FROM = 'Lazo <hello@meetlazo.com>';
  const REPLY = 'hello@meetlazo.com';
  const thread = (id) => `${APP}?thread=${encodeURIComponent(id)}`;
  const toDate = (v) => (v && typeof v.toDate === 'function' ? v.toDate() : v ? new Date(v) : null);
  const fmtDay = (v) => { const d = toDate(v); return d && !isNaN(d) ? d.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC' }) : ''; };
  const fmtShort = (v) => { const d = toDate(v); return d && !isNaN(d) ? d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' }) : ''; };
  const firstName = (s) => { const t = str(s).trim(); return t ? t.split(/\s+/)[0] : ''; };
  const CAT = { 'wedding-photographers': 'photographer', 'wedding-videographers': 'videographer', 'wedding-venues': 'venue', 'wedding-planners': 'planner', 'wedding-djs': 'DJ', 'wedding-florists': 'florist', 'wedding-caterers': 'caterer', 'wedding-cakes': 'baker', 'hair-and-makeup': 'hair and makeup artist', 'wedding-officiants': 'officiant', 'wedding-transportation': 'transportation', 'wedding-rentals': 'rentals', 'wedding-bands': 'band', 'wedding-invitations': 'stationer', 'day-of-coordination': 'day-of coordinator' };

  async function sendEmail(to, subject, html, text, from, replyTo) {
    const r = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${RESEND_API_KEY.value()}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ from: from || FROM, to, reply_to: replyTo || REPLY, subject, html, text }),
    });
    if (!r.ok) throw new Error(`resend ${r.status}: ${await r.text()}`);
  }

  // the couple behind an inquiry: who to write to, what to call them, whether they want mail
  async function coupleOf(inq) {
    const cid = str(inq.coupleUid);
    if (!cid || inq.offPlatform === true || inq.demo === true || cid.startsWith('demo_')) return null;
    const [cs, us, partners] = await Promise.all([
      db().collection('couples').doc(cid).get().catch(() => null),
      db().collection('users').doc(cid).get().catch(() => null),
      db().collection('users').where('coupleUid', '==', cid).limit(3).get().catch(() => null),
    ]);
    const c = cs && cs.exists ? cs.data() : {};
    if (c.emailOk === false || c.preview === true) return null;   // muted, or a vendor previewing the couple side
    const emails = new Set();
    const u = us && us.exists ? us.data() : {};
    if (emailOk(u.email)) emails.add(str(u.email).trim());
    if (partners) partners.forEach((d) => { const e = str(d.get('email')).trim(); if (emailOk(e)) emails.add(e); });
    if (!emails.size) { try { const a = await admin.auth().getUser(cid); if (emailOk(a.email)) emails.add(a.email); } catch (_) {} }
    if (!emails.size) return null;
    const names = str(c.names) || str(inq.coupleName) || firstName(u.display_name) || 'you two';
    return { cid, to: [...emails], names, first: firstName(str(c.names).split(/\s*(&|and)\s*/)[0] || inq.coupleName || u.display_name) || 'there', couple: c };
  }
  async function vendorOf(inq) { const id = str(inq.vendorId); if (!id) return null; const s = await db().collection('vendors').doc(id).get().catch(() => null); return s && s.exists ? { id, ...s.data() } : null; }
  const vendorName = (inq, v) => str(inq.vendorName) || str(v && v.name) || 'Your vendor';
  const vendorEmail = (v) => { const e = str(v && (v.notifyEmail || v.publicEmail || v.email)).trim(); return emailOk(e) ? e : undefined; };
  const vendorKind = (inq, v) => CAT[str(inq.vendorCategory || (v && v.category) || (v && Array.isArray(v.categories) && v.categories[0]))] || 'vendor';

  // claim a flag on a document inside a transaction: true the first time only
  async function once(ref, flag) {
    return db().runTransaction(async (tx) => { const s = await tx.get(ref); if (!s.exists || s.get(flag)) return false; tx.update(ref, { [flag]: FieldValue.serverTimestamp() }); return true; });
  }
  // vendor-branded inner card helpers (brand.js wraps them)
  const vp = (t) => `<p style="margin:0 0 12px">${t}</p>`;
  const vbtn = (label, href, v) => { const b = require('./brand').brandOf(v); return `<p style="margin:20px 0 6px"><a href="${href}" style="display:inline-block;background:${b.accent};color:${b.primary};text-decoration:none;padding:12px 24px;border-radius:999px;font-weight:bold;font-size:14px">${esc(label)}</a></p>`; };
  const vfoot = `<p style="margin:16px 0 0;color:#8A7F90;font-size:12px">Reply in the Lazo app, where this conversation, proposals, agreements and payments live together.</p>`;

  /* ---------------- a vendor's message ---------------- */
  const coupleOnMessage = onDocumentCreated({ document: 'inquiries/{inquiryId}/messages/{messageId}', region: 'us-central1', memory: '256MiB', secrets: [RESEND_API_KEY] }, async (event) => {
    const m = event.data && event.data.data(); if (!m || str(m.senderRole) !== 'vendor' || m.system === true || str(m.via) === 'sms') return;
    const inqRef = db().collection('inquiries').doc(event.params.inquiryId); const is = await inqRef.get(); if (!is.exists) return;
    const inq = is.data(); if (inq.offPlatform === true) return;   // leads.js handles off-platform leads
    const who = await coupleOf(inq); if (!who) return;
    // in the thread right now: the app shows it, no email
    const active = toDate(inq.coupleActiveAt); if (active && Date.now() - active.getTime() < 3 * 60e3 && !m.sneakPeek && !m.teaser) return;
    if (!(await once(event.data.ref, 'coupleNotifiedAt'))) return;
    const v = await vendorOf(inq); const name = vendorName(inq, v); const text = str(m.text).trim();
    const att = m.attachment && typeof m.attachment === 'object' ? str(m.attachment.name || m.attachment.title || 'attachment') : '';
    let subject, inner, plain;
    if (Array.isArray(m.sneakPeek) && m.sneakPeek.length) {
      const pics = m.sneakPeek.filter((p) => p && /^https?:\/\//.test(str(p.url))).slice(0, 4);
      subject = `A sneak peek from ${name}`;
      inner = vp(`Hi ${esc(who.first)},`) + vp(esc(text || 'A first look at your day.')) + (pics.length ? `<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:12px 0"><tr>${pics.map((p, i) => `<td width="${Math.floor(100 / pics.length)}%" style="padding:0 ${i < pics.length - 1 ? '6px' : '0'} 0 0"><a href="${thread(is.id)}"><img src="${esc(p.url)}" width="${Math.floor(500 / pics.length)}" alt="${esc(p.moment || '')}" style="display:block;width:100%;height:auto;border-radius:12px;border:0"></a></td>`).join('')}</tr></table>` : '') + vbtn('See them all', thread(is.id), v) + vfoot;
      plain = `${name}: ${text || 'A first look at your day.'}\n${thread(is.id)}`;
    } else if (m.teaser && typeof m.teaser === 'object' && str(m.teaser.url)) {
      subject = `A first look at your film from ${name}`;
      inner = vp(`Hi ${esc(who.first)},`) + vp(esc(text || 'A first look at your film.')) + vp(`<a href="${esc(m.teaser.url)}" style="color:#52284F;font-weight:bold">Watch it on ${esc(m.teaser.host || 'the web')}</a>`) + vbtn('Open the thread', thread(is.id), v) + vfoot;
      plain = `${name}: ${text || 'A first look at your film.'}\n${m.teaser.url}\n${thread(is.id)}`;
    } else {
      const body = text || (att ? `sent you a file: ${att}` : ''); if (!body) return;
      subject = `${name} replied`;
      inner = vp(`Hi ${esc(who.first)},`) + `<blockquote style="margin:0 0 12px;padding:10px 16px;border-left:3px solid #D9B77C;background:#FAF6F0;border-radius:0 10px 10px 0">${esc(body).replace(/\n/g, '<br>')}</blockquote>` + (att && text ? vp(`Attached: ${esc(att)}`) : '') + vbtn('Reply in Lazo', thread(is.id), v) + vfoot;
      plain = `${name}: ${body}\n\nReply: ${thread(is.id)}`;
    }
    try { await sendEmail(who.to, subject, brandWrap(v, inner), plain, `${name} via Lazo <hello@meetlazo.com>`, vendorEmail(v)); } catch (e) { console.warn('coupleOnMessage', is.id, e.message); }
  });

  /* ---------------- a proposal ---------------- */
  const coupleOnProposal = onDocumentCreated({ document: 'inquiries/{inquiryId}/proposals/{proposalId}', region: 'us-central1', memory: '256MiB', secrets: [RESEND_API_KEY] }, async (event) => {
    const p = event.data && event.data.data(); if (!p || p.demo === true) return;
    const is = await db().collection('inquiries').doc(event.params.inquiryId).get(); if (!is.exists) return; const inq = is.data();
    const who = await coupleOf(inq); if (!who) return;
    if (!(await once(event.data.ref, 'coupleNotifiedAt'))) return;
    const v = await vendorOf(inq); const name = vendorName(inq, v);
    const price = str(p.price).trim(); const priceTxt = price ? (/^\d/.test(price) ? '$' + price.replace(/^\$/, '') : price) : '';
    const inner = vp(`Hi ${esc(who.first)},`) + vp(`${esc(name)} sent you a proposal${p.title ? `: <b>${esc(p.title)}</b>` : ''}${priceTxt ? ` at <b>${esc(priceTxt)}</b>` : ''}.`)
      + (p.includes ? vp(`<b>Includes:</b> ${esc(p.includes)}`) : '') + (p.note ? `<blockquote style="margin:0 0 12px;padding:10px 16px;border-left:3px solid #D9B77C;background:#FAF6F0;border-radius:0 10px 10px 0">${esc(p.note).replace(/\n/g, '<br>')}</blockquote>` : '')
      + (p.validUntil ? vp(`<span style="color:#8A7F90">Good until ${esc(fmtDay(p.validUntil))}.</span>`) : '') + vbtn('Review the proposal', thread(is.id), v) + vp(`<span style="color:#8A7F90;font-size:13px">Accept it in the app and the agreement follows in the same thread. Questions? Reply there; ${esc(name)} sees it straight away.</span>`);
    const plain = `${name} sent you a proposal${p.title ? ': ' + p.title : ''}${priceTxt ? ' at ' + priceTxt : ''}.${p.includes ? '\nIncludes: ' + p.includes : ''}${p.note ? '\n\n' + p.note : ''}\n\nReview: ${thread(is.id)}`;
    try { await sendEmail(who.to, `Your proposal from ${name}${priceTxt ? ': ' + priceTxt : ''}`, brandWrap(v, inner), plain, `${name} via Lazo <hello@meetlazo.com>`, vendorEmail(v)); } catch (e) { console.warn('coupleOnProposal', is.id, e.message); }
  });

  /* ---------------- a questionnaire ---------------- */
  const coupleOnQuestionnaire = onDocumentCreated({ document: 'inquiries/{inquiryId}/questionnaires/{qId}', region: 'us-central1', memory: '256MiB', secrets: [RESEND_API_KEY] }, async (event) => {
    const q = event.data && event.data.data(); if (!q || q.demo === true) return;
    const is = await db().collection('inquiries').doc(event.params.inquiryId).get(); if (!is.exists) return; const inq = is.data();
    const who = await coupleOf(inq); if (!who) return;
    if (!(await once(event.data.ref, 'coupleNotifiedAt'))) return;
    const v = await vendorOf(inq); const name = vendorName(inq, v); const n = Array.isArray(q.questions) ? q.questions.length : 0;
    const inner = vp(`Hi ${esc(who.first)},`) + vp(`${esc(name)} has ${n ? n + ' question' + (n === 1 ? '' : 's') : 'a few questions'} for you${q.title ? `: <b>${esc(q.title)}</b>` : ''}. Your answers help them plan your day properly, and they only take a few minutes.`) + vbtn('Answer in Lazo', thread(is.id), v) + vfoot;
    try { await sendEmail(who.to, `${name} has a few questions for you`, brandWrap(v, inner), `${name} sent you a questionnaire${q.title ? ': ' + q.title : ''}. Answer it here: ${thread(is.id)}`, `${name} via Lazo <hello@meetlazo.com>`, vendorEmail(v)); } catch (e) { console.warn('coupleOnQuestionnaire', is.id, e.message); }
  });

  /* ---------------- an invoice: issued, then paid ---------------- */
  const coupleOnInvoice = onDocumentWritten({ document: 'inquiries/{inquiryId}/invoices/{invoiceId}', region: 'us-central1', memory: '256MiB', secrets: [RESEND_API_KEY] }, async (event) => {
    const after = event.data && event.data.after; if (!after || !after.exists) return;
    const inv = after.data(); const before = event.data.before && event.data.before.exists ? event.data.before.data() : {};
    if (inv.demo === true) return;
    const is = await db().collection('inquiries').doc(event.params.inquiryId).get(); if (!is.exists) return; const inq = is.data();
    const who = await coupleOf(inq); if (!who) return;
    const v = await vendorOf(inq); const name = vendorName(inq, v); const total = +inv.total || 0;
    // issued: a standalone invoice sent by the vendor (plan instalments announce themselves in payments.js)
    if (str(inv.status) === 'sent' && str(before.status) !== 'sent' && !str(inv.planId) && !inv.coupleNotifiedAt) {
      if (!(await once(after.ref, 'coupleNotifiedAt'))) return;
      const due = inv.dueDate ? fmtDay(inv.dueDate) : '';
      const items = Array.isArray(inv.lineItems) ? inv.lineItems.filter((x) => x && (x.label || x.name)).slice(0, 8) : [];
      const inner = vp(`Hi ${esc(who.first)},`) + vp(`${esc(name)} sent an invoice${inv.title ? ` for <b>${esc(inv.title)}</b>` : ''}: <b>${money(total)}</b>${due ? `, due ${esc(due)}` : ''}.`)
        + (items.length ? `<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:0 0 12px;font-size:14px">${items.map((x) => `<tr><td style="padding:5px 0;border-bottom:1px solid #EADFCB">${esc(x.label || x.name)}${x.qty > 1 ? ` <span style="color:#8A7F90">x${esc(x.qty)}</span>` : ''}</td><td align="right" style="padding:5px 0;border-bottom:1px solid #EADFCB">${money(x.amount != null ? x.amount : (x.price || 0) * (x.qty || 1))}</td></tr>`).join('')}</table>` : '')
        + vbtn('View and pay', thread(is.id), v) + vp(`<span style="color:#8A7F90;font-size:13px">Pay by card in the app; the receipt lands in the same thread. If something looks off, reply there first.</span>`);
      try { await sendEmail(who.to, `Invoice from ${name}: ${money(total)}${due ? ', due ' + fmtShort(inv.dueDate) : ''}`, brandWrap(v, inner), `${name} sent an invoice${inv.title ? ' for ' + inv.title : ''}: ${money(total)}${due ? ', due ' + due : ''}.\n\nView and pay: ${thread(is.id)}`, `${name} via Lazo <hello@meetlazo.com>`, vendorEmail(v)); } catch (e) { console.warn('coupleOnInvoice sent', is.id, e.message); }
      return;
    }
    // paid: Lazo's receipt, with what's left on this vendor
    if (str(inv.status) === 'paid' && str(before.status) !== 'paid' && !inv.receiptSentAt) {
      if (!(await once(after.ref, 'receiptSentAt'))) return;
      const all = await after.ref.parent.get().catch(() => null);
      let paidSum = 0, openSum = 0; if (all) all.forEach((d) => { const x = d.data(); if (x.demo === true || str(x.status) === 'void') return; if (str(x.status) === 'paid') paidSum += +x.total || 0; else if (str(x.status) === 'sent') openSum += +x.total || 0; });
      const via = str(inv.paidVia); const viaTxt = via === 'card' || via === 'whop' ? 'by card' : via === 'ach' ? 'by bank transfer' : via === 'cash' || via === 'check' || via === 'manual' ? 'recorded by ' + name : '';
      const body = facts([['Paid', money(total)], ['To', name], [openSum ? 'Still open' : 'Paid to date', money(openSum || paidSum)]]) + `<p style="margin:0;font-family:Helvetica,Arial,sans-serif;font-size:14.5px;line-height:1.6;color:#5B5363">${esc(inv.title || 'Invoice')}${viaTxt ? ', ' + viaTxt : ''}${inv.paidAt ? ', ' + esc(fmtDay(inv.paidAt)) : ''}. ${openSum ? `${money(openSum)} remains on your ${esc(vendorKind(inq, v))}; each payment shows up in the thread when it's due.` : `That settles everything with ${esc(name)}.`}</p>`;
      const html = frame({ preheader: `${money(total)} to ${name}, received.`, kicker: 'Receipt', title: 'Payment received.', lede: `Thank you, ${esc(who.first)}. Your payment to ${esc(name)} went through and is recorded in your thread.`, body, cta: 'Open the thread', ctaHref: thread(is.id), signoff: 'Keep this for your records. Reply if anything about it looks wrong.', footerWhy: 'You’re getting this because you made a payment through Lazo.' });
      try { await sendEmail(who.to, `Receipt: ${money(total)} to ${name}`, html, `Payment received: ${money(total)} to ${name} (${inv.title || 'Invoice'})${viaTxt ? ', ' + viaTxt : ''}.${openSum ? ' ' + money(openSum) + ' remains.' : ' That settles everything with ' + name + '.'}\n\n${thread(is.id)}`); } catch (e) { console.warn('coupleOnInvoice paid', is.id, e.message); }
    }
  });

  /* ---------------- a contract, fully signed ---------------- */
  const coupleOnContract = onDocumentWritten({ document: 'inquiries/{inquiryId}/contracts/{contractId}', region: 'us-central1', memory: '256MiB', secrets: [RESEND_API_KEY] }, async (event) => {
    const after = event.data && event.data.after; if (!after || !after.exists) return;
    const c = after.data(); const before = event.data.before && event.data.before.exists ? event.data.before.data() : {};
    if (str(c.status) !== 'signed' || str(before.status) === 'signed' || c.demo === true) return;
    const is = await db().collection('inquiries').doc(event.params.inquiryId).get(); if (!is.exists) return; const inq = is.data();
    const who = await coupleOf(inq); if (!who) return;
    if (!(await once(after.ref, 'coupleNotifiedAt'))) return;
    const v = await vendorOf(inq); const name = vendorName(inq, v); const total = c.values && c.values.total_price != null ? money(c.values.total_price) : '';
    const wd = inq.structuredIntent && inq.structuredIntent.weddingDate ? str(inq.structuredIntent.weddingDate) : '';
    const body = facts([['Agreement', str(c.title) || 'Service agreement'], ['With', name], total ? ['Total', total] : ['Date', wd ? fmtShort(wd + 'T12:00:00Z') : 'In the thread']]) + `<p style="margin:0;font-family:Helvetica,Arial,sans-serif;font-size:14.5px;line-height:1.6;color:#5B5363">The signed copy is in your thread with ${esc(name)}, where any retainer or payment plan will appear next. Nothing else to do today.</p>`;
    const html = frame({ preheader: `Your agreement with ${name} is signed by both of you.`, kicker: 'Signed', title: 'It’s signed.', lede: `${esc(who.names)}, your agreement with ${esc(name)} is complete and signed by both sides. One more piece of your day, settled.`, body, cta: 'See the agreement', ctaHref: thread(is.id), secondary: 'Ask June what comes next', secondaryHref: JUNE, footerWhy: 'You’re getting this because you signed an agreement through Lazo.' });
    try { await sendEmail(who.to, `Signed: your agreement with ${name}`, html, `Your agreement with ${name} (${c.title || 'service agreement'}) is signed by both sides.${total ? ' Total ' + total + '.' : ''} The copy is in your thread: ${thread(is.id)}`); } catch (e) { console.warn('coupleOnContract', is.id, e.message); }
  });

  /* ---------------- the inquiry itself: booked, delivered, released ---------------- */
  const coupleOnInquiry = onDocumentUpdated({ document: 'inquiries/{inquiryId}', region: 'us-central1', memory: '256MiB', secrets: [RESEND_API_KEY] }, async (event) => {
    const before = event.data && event.data.before.data(), after = event.data && event.data.after.data(); if (!before || !after) return;
    const ref = event.data.after.ref; const id = event.params.inquiryId;
    const booked = str(after.status) === 'booked' && str(before.status) !== 'booked';
    const delivered = !!after.deliveredAt && !before.deliveredAt;
    const released = !!after.unbookedAt && !before.unbookedAt && str(before.status) === 'booked';
    if (!booked && !delivered && !released) return;
    const who = await coupleOf(after); if (!who) return;
    const v = await vendorOf(after); const name = vendorName(after, v); const kind = vendorKind(after, v);
    const wd = after.structuredIntent && after.structuredIntent.weddingDate ? str(after.structuredIntent.weddingDate) : '';
    if (booked && await once(ref, 'bookedEmailAt')) {
      // where the team stands now
      let team = '', done = 0, total = 0;
      try { const plan = await db().collection('couples').doc(who.cid).collection('plan').get(); plan.forEach((d) => { total++; if (str(d.get('status')) === 'booked') done++; }); if (total) team = `${done} of ${total}`; } catch (_) {}
      const days = wd ? Math.round((Date.UTC(+wd.slice(0, 4), +wd.slice(5, 7) - 1, +wd.slice(8, 10)) - Date.UTC(new Date().getUTCFullYear(), new Date().getUTCMonth(), new Date().getUTCDate())) / 86400e3) : null;
      const body = facts([['Booked', name], ['Your team', team || 'Growing'], days != null && days > 0 ? ['Days to go', String(days)] : ['Date', wd ? fmtShort(wd + 'T12:00:00Z') : 'Set it in the app']])
        + `<p style="margin:0 0 10px;font-family:Helvetica,Arial,sans-serif;font-size:15px;line-height:1.65;color:#241E2B"><b style="color:#3D1C3B">What happens next.</b> ${esc(name)} may send an agreement to sign and a retainer or payment plan; both arrive in your thread and you’ll hear from us when they do. Their category is marked booked on your plan, and anything they need from you shows up as a task.</p>`
        + `<p style="margin:0;font-family:Helvetica,Arial,sans-serif;font-size:14.5px;line-height:1.6;color:#5B5363">When the day is done, we’ll ask you for a review. On Lazo only couples who booked can leave one, which is why they mean something.</p>`;
      const html = frame({ preheader: `${name} is booked. ${team ? team + ' of your team in place.' : ''}`, kicker: 'Booked', title: `You’re booked with ${esc(name)}.`, lede: `${esc(who.names)}, your ${esc(kind)} is locked in. That’s a real piece of the day you can stop thinking about.`, body, cta: 'Open your plan', ctaHref: thread(id), secondary: 'Ask June what to book next', secondaryHref: JUNE, hero: 'atmo-toast.jpg', heroAlt: 'A toast', footerWhy: 'You’re getting this because you booked a vendor on Lazo.' });
      try { await sendEmail(who.to, `You’re booked with ${name}`, html, `${who.names}, you're booked with ${name} (${kind}).${team ? ' Your team: ' + team + ' in place.' : ''}\n\nWhat happens next: an agreement and a retainer or payment plan may follow in your thread; their category is marked booked on your plan.\n\n${thread(id)}`); } catch (e) { console.warn('coupleOnInquiry booked', id, e.message); }
    }
    if (delivered && await once(ref, 'deliveredEmailAt')) {
      const film = /video|film/.test(str(after.vendorCategory) + str(v && v.category)); const what = film ? 'film' : /photo/.test(str(after.vendorCategory) + str(v && v.category)) ? 'gallery' : 'delivery';
      const html = frame({ preheader: `${name} has delivered. Your ${what} is ready.`, kicker: 'Delivered', title: `Your ${esc(what)} is ready.`, lede: `${esc(who.names)}, ${esc(name)} marked your ${esc(what)} delivered. It’s waiting in your thread, with everything they sent along the way.`, body: `<p style="margin:0;font-family:Helvetica,Arial,sans-serif;font-size:14.5px;line-height:1.6;color:#5B5363">Take your time with it. In a couple of days we’ll ask how ${esc(name)} did; your review is the one thing on Lazo money can’t buy, and it helps the next couple choose well.</p>`, cta: `Open your ${what}`, ctaHref: thread(id), hero: film ? 'atmo-firstdance.jpg' : 'atmo-veil.jpg', heroAlt: 'Your day', footerWhy: 'You’re getting this because a vendor you booked on Lazo delivered.' });
      try { await sendEmail(who.to, `Your ${what} from ${name} is ready`, html, `${name} marked your ${what} delivered. Open it: ${thread(id)}`); } catch (e) { console.warn('coupleOnInquiry delivered', id, e.message); }
    }
    if (released && await once(ref, 'releasedEmailAt')) {
      const reason = str(after.unbookLabel || after.unbookReason);
      const slug = str(after.vendorCategory || (v && Array.isArray(v.categories) && v.categories[0]) || '');
      const findUrl = who.couple && who.couple.metroId && slug ? `${SITE}vendors/${esc(str(who.couple.metroId))}/${esc(slug)}/` : `${SITE}vendors/`;
      const html = frame({ preheader: `${name} released your date.`, kicker: 'A change', title: `${esc(name)} released your date.`, lede: `${esc(who.names)}, ${esc(name)} is no longer booked for your day${reason ? ` (${esc(reason)})` : ''}. Their category is open again on your plan.`, body: `<p style="margin:0;font-family:Helvetica,Arial,sans-serif;font-size:14.5px;line-height:1.6;color:#5B5363">If a payment was made, the thread has the record and ${esc(name)} is the first to ask about it. We’d start looking again this week; verified ${esc(kind === 'vendor' ? 'vendors' : kind + 's')} in your city are a tap away, and June can shortlist a few.</p>`, cta: 'Find a replacement', ctaHref: findUrl, secondary: 'Ask June for a shortlist', secondaryHref: JUNE, footerWhy: 'You’re getting this because a booking on your Lazo plan changed.' });
      try { await sendEmail(who.to, `${name} released your date`, html, `${name} is no longer booked for your day${reason ? ' (' + reason + ')' : ''}. Find a replacement: ${findUrl}`); } catch (e) { console.warn('coupleOnInquiry released', id, e.message); }
    }
  });

  return { coupleOnMessage, coupleOnProposal, coupleOnQuestionnaire, coupleOnInvoice, coupleOnContract, coupleOnInquiry };
};

// END OF FILE - JC-LAZO-FNDASH-1007-024
