// functions-dashboard/team.js
// Build ID: JC-LAZO-FNDASH-0913-021
//
// THE VENDOR TEAM GRAPH. A booked vendor recommends the pros they actually
// work with, inside the couple's thread; the couple checks a date with one
// tap; the referred vendor sees who sent them; the referrer sees it book.
//
//   teamRecommend  callable {vendorId, inquiryId, memberIds:[vendorId], note}
//     -> posts a 'teamRec' message in the thread (rendered as vendor cards on
//        the couple side), writes couples/{cid}/recs/{memberId} for the vendor
//        team tiles, emails the couple, and stamps vendors/{id}.referralsSent.
//   onReferralBooked  trigger inquiries/{id} updated -> when a thread with
//        referredBy flips to booked: referrer gets a thread note + email and
//        vendors/{referrer}.referralsBooked++; the referred vendor's doc gets
//        referredBookings++.
//   The couple's own inquiry write (client) carries referredBy {vendorId,
//   name} - see couple v123 - so the referred vendor's inbox shows it.
//
// vendors/{id}.team = [{vendorId, name, category, note, weddingsTogether}]
// is curated by the vendor in the dashboard (ordinary vendor-writable).

'use strict';

const { onCall, HttpsError } = require('firebase-functions/v2/https');
const { onDocumentUpdated } = require('firebase-functions/v2/firestore');
const admin = require('firebase-admin');
const { wrap: brandWrap } = require('./brand');

const APP = 'https://app.meetlazo.com/dashboard';
const FROM = 'Lazo <hello@meetlazo.com>';
const db = () => admin.firestore();
const { FieldValue } = admin.firestore;
const str = (v) => (v == null ? '' : String(v));
const emailOk = (e) => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(str(e));
const catLabel = (c) => str(c).replace(/^wedding-/, '').replace(/-/g, ' ');

module.exports = function teamModule(RESEND_API_KEY) {
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
  async function ownerEmail(v) {
    try {
      if (str(v.claimedBy)) { const u = await db().collection('users').doc(str(v.claimedBy)).get(); if (u.exists && emailOk(u.get('email'))) return str(u.get('email')); }
    } catch (e) {}
    return emailOk(v.email) ? str(v.email) : '';
  }

  const teamRecommend = onCall({ memory: '256MiB', secrets: [RESEND_API_KEY] }, async (request) => {
    const uid = request.auth && request.auth.uid;
    if (!uid) throw new HttpsError('unauthenticated', 'Sign in first.');
    const d = request.data || {};
    const vendorId = str(d.vendorId), inquiryId = str(d.inquiryId);
    const memberIds = Array.isArray(d.memberIds) ? d.memberIds.map(str).filter(Boolean).slice(0, 8) : [];
    const note = str(d.note).trim().slice(0, 400);
    if (!vendorId || !inquiryId || !memberIds.length) throw new HttpsError('invalid-argument', 'Pick at least one pro.');
    const v = await vendorFor(uid, vendorId);
    const inqRef = db().collection('inquiries').doc(inquiryId);
    const inqS = await inqRef.get();
    if (!inqS.exists || str(inqS.get('vendorId')) !== vendorId) throw new HttpsError('not-found', 'Thread not found.');
    const inq = inqS.data();
    const coupleUid = str(inq.coupleUid);
    if (!coupleUid || coupleUid.startsWith('lead_') || coupleUid.startsWith('demo_')) throw new HttpsError('failed-precondition', 'Recommend to a couple with a Lazo account (website leads get it once they join).');

    // only members on this vendor's team, and only real listings
    const team = Array.isArray(v.team) ? v.team : [];
    const picks = [];
    for (const id of memberIds) {
      const t = team.find((m) => str(m && m.vendorId) === id);
      const ms = await db().collection('vendors').doc(id).get();
      if (!t || !ms.exists || ms.get('delisted') === true) continue;
      picks.push({
        vendorId: id, name: str(ms.get('name')), category: str(ms.get('category') || (Array.isArray(ms.get('categories')) && ms.get('categories')[0])),
        metroId: str(ms.get('metroId')), slug: str(ms.get('slug')), logoUrl: str(ms.get('logoUrl')), coverUrl: str(ms.get('coverUrl')),
        startingPrice: str(ms.get('startingPrice')), claimed: str(ms.get('claimStatus')) === 'approved' || !!str(ms.get('claimedBy')),
        note: str(t.note).slice(0, 160), weddingsTogether: typeof t.weddingsTogether === 'number' ? t.weddingsTogether : 0,
      });
    }
    if (!picks.length) throw new HttpsError('failed-precondition', 'None of those pros are on your team list.');

    const text = note || `A few pros I trust with my own weddings - ${picks.map((p) => p.name).join(', ')}. Tap any of them to check your date; tell them I sent you.`;
    await inqRef.collection('messages').add({
      senderRole: 'vendor', text, at: FieldValue.serverTimestamp(),
      teamRec: { from: { vendorId, name: str(v.name) }, vendors: picks },
    });
    await inqRef.set({ lastMessageAt: FieldValue.serverTimestamp(), lastMessageRole: 'vendor', lastMessagePreview: `Recommended ${picks.length} pro${picks.length === 1 ? '' : 's'}` }, { merge: true });
    const batch = db().batch();
    for (const p of picks) {
      batch.set(db().collection('couples').doc(coupleUid).collection('recs').doc(p.vendorId), {
        ...p, fromVendorId: vendorId, fromVendorName: str(v.name), inquiryId, at: FieldValue.serverTimestamp(),
      }, { merge: true });
    }
    batch.set(db().collection('vendors').doc(vendorId), { referralsSent: FieldValue.increment(picks.length), referralsSentAt: FieldValue.serverTimestamp() }, { merge: true });
    await batch.commit();

    // couple email
    try {
      const uids = [coupleUid];
      const partners = await db().collection('users').where('coupleUid', '==', coupleUid).get();
      partners.forEach((p) => uids.push(p.id));
      for (const u of [...new Set(uids)]) {
        const us = await db().collection('users').doc(u).get();
        const to = us.exists ? str(us.get('email')) : '';
        if (!emailOk(to)) continue;
        await sendEmail(to, `${str(v.name)} recommends ${picks.length === 1 ? picks[0].name : picks.length + ' pros'} for your day`,
          brandWrap(v, `<p>${text.replace(/</g, '&lt;')}</p><ul>${picks.map((p) => `<li><b>${p.name}</b> - ${catLabel(p.category)}${p.weddingsTogether ? ` \u00b7 ${p.weddingsTogether} weddings together` : ''}${p.note ? `<br><span style="color:#6B5F72">${p.note.replace(/</g, '&lt;')}</span>` : ''}</li>`).join('')}</ul><p><a href="${APP}?thread=${inquiryId}">Check their dates on Lazo</a></p>`),
          `${text}\n${picks.map((p) => `${p.name} - ${catLabel(p.category)}`).join('\n')}\n${APP}?thread=${inquiryId}`);
      }
    } catch (e) { console.warn('teamRecommend email', e.message); }
    return { ok: true, count: picks.length };
  });

  const onReferralBooked = onDocumentUpdated({ document: 'inquiries/{inquiryId}', memory: '256MiB', secrets: [RESEND_API_KEY] }, async (event) => {
    const before = event.data && event.data.before.data(), after = event.data && event.data.after.data();
    if (!before || !after) return;
    if (str(before.status) === 'booked' || str(after.status) !== 'booked') return;
    const ref = after.referredBy && typeof after.referredBy === 'object' ? after.referredBy : null;
    if (!ref || !str(ref.vendorId) || after.referralCredited === true) return;
    const referrerId = str(ref.vendorId), bookedId = str(after.vendorId);
    await event.data.after.ref.set({ referralCredited: true }, { merge: true });
    const batch = db().batch();
    batch.set(db().collection('vendors').doc(referrerId), { referralsBooked: FieldValue.increment(1) }, { merge: true });
    batch.set(db().collection('vendors').doc(bookedId), { referredBookings: FieldValue.increment(1) }, { merge: true });
    await batch.commit();
    // note in the referrer's own thread with this couple, if any
    try {
      const rq = await db().collection('inquiries').where('vendorId', '==', referrerId).where('coupleUid', '==', str(after.coupleUid)).limit(1).get();
      const bookedName = str(after.vendorName);
      if (!rq.empty) {
        await rq.docs[0].ref.collection('messages').add({ senderRole: 'vendor', system: true, text: `${str(after.coupleName) || 'Your couple'} booked ${bookedName} - one of the pros you recommended.`, at: FieldValue.serverTimestamp() });
      }
      const rv = await db().collection('vendors').doc(referrerId).get();
      const to = rv.exists ? await ownerEmail(rv.data()) : '';
      if (to) await sendEmail(to, `${str(after.coupleName) || 'A couple'} booked ${bookedName} on your word`,
        `<p>${str(after.coupleName) || 'A couple'} just booked <b>${bookedName}</b> after you recommended them. That's ${(rv.get('referralsBooked') || 0) + 1} booking${(rv.get('referralsBooked') || 0) + 1 === 1 ? '' : 's'} your team owes you.</p><p><a href="${APP}">Open Lazo</a></p>`,
        `${str(after.coupleName) || 'A couple'} booked ${bookedName} on your recommendation.`);
    } catch (e) { console.warn('onReferralBooked notify', e.message); }
  });

  return { teamRecommend, onReferralBooked };
};

// END OF FILE - JC-LAZO-FNDASH-0913-021
