// functions-dashboard/hello.js
// Build ID: JC-LAZO-FNDASH-0913-020
//
// SAY HELLO. Pro and Studio vendors can reach out first to couples in their
// metro who still need their category and have opted in. Free vendors see
// the count and the upsell, never the couples.
//
//   helloMatches  callable {vendorId}
//     -> { tier, allowed, cap, used, matches:[card] }
//     card = { coupleUid, monthLabel, dateIso, budgetBand, budget, metro,
//              needs:[slug], needsCount, planningDays, name:null }
//     Anonymous by design: no names, no email, no photo - the couple's
//     identity is revealed only if they reply. Cards exclude couples this
//     vendor already has a thread with or already said hello to.
//   helloSend     callable {vendorId, coupleUid, text}
//     -> creates the thread (inquiries doc, source 'hello', hello true) with
//        the vendor's message as the first message, emails the couple, and
//        records hellos/{id} for the weekly cap.
//
// Weekly caps: pro 10, studio 25 (Phoenix week, Mon-Sun). Couples opt out
// with couples.hellosOk = false (default in).

'use strict';

const { onCall, HttpsError } = require('firebase-functions/v2/https');
const admin = require('firebase-admin');
const { wrap: brandWrap } = require('./brand');

const APP = 'https://app.meetlazo.com/dashboard';
const FROM = 'Lazo <hello@meetlazo.com>';
const CAPS = { pro: 10, studio: 25 };
const db = () => admin.firestore();
const { FieldValue, Timestamp } = admin.firestore;
const str = (v) => (v == null ? '' : String(v));
const toDate = (v) => (v && typeof v.toDate === 'function') ? v.toDate() : (v instanceof Date ? v : null);
const emailOk = (e) => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(str(e));
const MO = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function weekKey(d) {
  // ISO-ish week key in Phoenix time: Monday-based
  const p = new Intl.DateTimeFormat('en-US', { timeZone: 'America/Phoenix', year: 'numeric', month: '2-digit', day: '2-digit', weekday: 'short' }).formatToParts(d);
  const o = {}; for (const x of p) o[x.type] = x.value;
  const dt = new Date(Date.UTC(+o.year, +o.month - 1, +o.day));
  const dow = (dt.getUTCDay() + 6) % 7; // Mon=0
  dt.setUTCDate(dt.getUTCDate() - dow);
  return dt.toISOString().slice(0, 10);
}
function band(n) {
  if (!n || n <= 0) return '';
  if (n < 10000) return 'under $10k';
  if (n < 20000) return '$10–20k';
  if (n < 35000) return '$20–35k';
  if (n < 60000) return '$35–60k';
  return '$60k+';
}

module.exports = function helloModule(RESEND_API_KEY) {
  async function sendEmail(to, subject, html, text) {
    if (!emailOk(to)) return;
    const r = await fetch('https://api.resend.com/emails', {
      method: 'POST', headers: { 'Authorization': `Bearer ${RESEND_API_KEY.value()}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ from: FROM, to: [to], subject, html, text }),
    });
    if (!r.ok) console.warn('resend', r.status, await r.text());
  }
  async function vendorFor(uid, vendorId) {
    const [v, u] = await Promise.all([db().collection('vendors').doc(vendorId).get(), db().collection('users').doc(uid).get()]);
    if (!v.exists) throw new HttpsError('not-found', 'Vendor not found.');
    const ok = str(v.get('claimedBy')) === uid || (u.exists && str(u.get('vendorId')) === vendorId && str(u.get('vendorRole')) === 'manager');
    if (!ok) throw new HttpsError('permission-denied', 'Not your vendor.');
    return { id: v.id, ...v.data() };
  }
  function tierOf(v) {
    const t = str(v.tier);
    if (t !== 'pro' && t !== 'studio') return 'free';
    const exp = toDate(v.tierExpiresAt);
    if (exp && exp < new Date()) return 'free';
    return t;
  }
  async function usedThisWeek(vendorId) {
    const wk = weekKey(new Date());
    const q = await db().collection('hellos').where('vendorId', '==', vendorId).where('weekKey', '==', wk).get();
    return q.size;
  }

  // ----------------------------------------------------------- matches ----
  const helloMatches = onCall({ memory: '512MiB', timeoutSeconds: 60 }, async (request) => {
    const uid = request.auth && request.auth.uid;
    if (!uid) throw new HttpsError('unauthenticated', 'Sign in first.');
    const vendorId = str(request.data && request.data.vendorId);
    const v = await vendorFor(uid, vendorId);
    const tier = tierOf(v);
    const metro = str(v.metroId);
    const cat = str(v.category || (Array.isArray(v.categories) && v.categories[0]));
    if (!metro || !cat) return { tier, allowed: tier !== 'free', cap: CAPS[tier] || 0, used: 0, matches: [], count: 0, reason: 'Set your metro and category on your profile first.' };

    // couples in this metro with a future date, opted in
    const today = new Date(); today.setHours(0, 0, 0, 0);
    const cq = await db().collection('couples').where('metroId', '==', metro).where('weddingDate', '>=', Timestamp.fromDate(today)).orderBy('weddingDate').limit(300).get();
    // threads this vendor already has, and hellos already sent
    const [mine, sent] = await Promise.all([
      db().collection('inquiries').where('vendorId', '==', vendorId).get(),
      db().collection('hellos').where('vendorId', '==', vendorId).get(),
    ]);
    const skip = new Set();
    mine.forEach((d) => skip.add(str(d.get('coupleUid'))));
    sent.forEach((d) => skip.add(str(d.get('coupleUid'))));

    const cards = [];
    for (const c of cq.docs) {
      const m = c.data();
      if (m.hellosOk === false) continue;
      if (skip.has(c.id)) continue;
      // needs this category?
      const plan = await c.ref.collection('plan').get();
      const needs = plan.docs.filter((p) => { const st = str(p.get('status')) || 'needed'; return st !== 'booked' && st !== 'skipped'; }).map((p) => p.id);
      if (!needs.includes(cat)) continue;
      const wd = toDate(m.weddingDate);
      const created = toDate(m.createdAt) || toDate(m.setupAt);
      cards.push({
        coupleUid: c.id,
        dateIso: wd ? wd.toISOString().slice(0, 10) : '',
        monthLabel: wd ? `${MO[wd.getMonth()]} ${wd.getFullYear()}` : 'Date TBD',
        dow: wd ? wd.getDay() : null,
        budget: typeof m.budgetTotal === 'number' ? m.budgetTotal : 0,
        budgetBand: band(m.budgetTotal),
        metro,
        needs, needsCount: needs.length,
        planningDays: created ? Math.max(0, Math.round((Date.now() - created.getTime()) / 86400000)) : null,
        hasSite: !!str(m.siteSlug),
      });
    }
    const used = tier === 'free' ? 0 : await usedThisWeek(vendorId);
    return {
      tier, allowed: tier !== 'free', cap: CAPS[tier] || 0, used, count: cards.length,
      matches: tier === 'free' ? [] : cards.slice(0, 60),
    };
  });

  // -------------------------------------------------------------- send ----
  const helloSend = onCall({ memory: '256MiB', secrets: [RESEND_API_KEY] }, async (request) => {
    const uid = request.auth && request.auth.uid;
    if (!uid) throw new HttpsError('unauthenticated', 'Sign in first.');
    const d = request.data || {};
    const vendorId = str(d.vendorId), coupleUid = str(d.coupleUid), text = str(d.text).trim().slice(0, 1200);
    if (!vendorId || !coupleUid || text.length < 20) throw new HttpsError('invalid-argument', 'Write at least a couple of sentences.');
    const v = await vendorFor(uid, vendorId);
    const tier = tierOf(v);
    if (tier === 'free') throw new HttpsError('permission-denied', 'Saying hello is part of Lazo Pro.');
    const used = await usedThisWeek(vendorId);
    if (used >= CAPS[tier]) throw new HttpsError('resource-exhausted', `You've used this week's ${CAPS[tier]} hellos. More on Monday.`);
    const cs = await db().collection('couples').doc(coupleUid).get();
    if (!cs.exists || cs.get('hellosOk') === false) throw new HttpsError('failed-precondition', 'This couple isn\'t taking hellos.');
    const c = cs.data();
    const cat = str(v.category || (Array.isArray(v.categories) && v.categories[0]));
    const dup = await db().collection('inquiries').where('vendorId', '==', vendorId).where('coupleUid', '==', coupleUid).limit(1).get();
    if (!dup.empty) throw new HttpsError('already-exists', 'You already have a thread with this couple.');

    const wd = toDate(c.weddingDate);
    const ref = db().collection('inquiries').doc();
    await ref.set({
      vendorId, vendorName: str(v.name), coupleUid, coupleName: str(c.names) || 'A couple',
      source: 'hello', hello: true, helloAt: FieldValue.serverTimestamp(),
      structuredIntent: {
        weddingDate: wd ? wd.toISOString().slice(0, 10) : '', budget: c.budgetTotal ? `$${Math.round(c.budgetTotal).toLocaleString('en-US')}` : '',
        category: cat, message: '', venue: '',
      },
      status: 'new', createdAt: FieldValue.serverTimestamp(),
      lastMessageAt: FieldValue.serverTimestamp(), lastMessageRole: 'vendor', lastMessagePreview: text.slice(0, 140),
      respondedAt: FieldValue.serverTimestamp(),
    });
    await ref.collection('messages').add({ senderRole: 'vendor', text, at: FieldValue.serverTimestamp(), via: 'hello' });
    await ref.collection('messages').add({ senderRole: 'vendor', system: true, text: `${str(v.name)} said hello first. You can reply, or close this thread any time - nothing is expected.`, at: FieldValue.serverTimestamp() });
    await db().collection('hellos').add({ vendorId, coupleUid, inquiryId: ref.id, weekKey: weekKey(new Date()), at: FieldValue.serverTimestamp() });

    // tell the couple (owner + partner)
    try {
      const uids = [coupleUid];
      const partners = await db().collection('users').where('coupleUid', '==', coupleUid).get();
      partners.forEach((p) => uids.push(p.id));
      for (const u of [...new Set(uids)]) {
        const us = await db().collection('users').doc(u).get();
        const to = us.exists ? str(us.get('email')) : '';
        if (!emailOk(to)) continue;
        await sendEmail(to, `${str(v.name)} said hello`,
          brandWrap(v, `<p>${str(v.name)} - a verified ${cat.replace(/^wedding-/, '').replace(/-/g, ' ')} in your area - reached out on Lazo:</p><blockquote style="margin:12px 0;padding:10px 14px;border-left:3px solid #D9B77C;background:#FAF6F0">${text.replace(/</g, '&lt;').replace(/\n/g, '<br>')}</blockquote><p><a href="${APP}?thread=${ref.id}">Reply on Lazo</a> - or ignore it, no pressure. You can turn hellos off under Account.</p>`),
          `${str(v.name)} said hello on Lazo: "${text}" Reply: ${APP}?thread=${ref.id}`);
      }
    } catch (e) { console.warn('hello email', e.message); }
    return { ok: true, inquiryId: ref.id, used: used + 1, cap: CAPS[tier] };
  });

  return { helloMatches, helloSend };
};

// END OF FILE - JC-LAZO-FNDASH-0913-020
