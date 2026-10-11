// functions-dashboard/june-push.js
// Build ID: JC-LAZO-FNDASH-1011-026
//
// PUSH, FROM JUNE. The reasons to open the app that arrive on the phone:
//
//   junePush            POST (x-june-key) {uid, title, body, data?, tag?} -> sends to every
//                       token under users/{uid}/fcm_tokens and prunes the dead ones. The June
//                       worker calls this for the morning brief, the waiting-lead alarm and
//                       due reminders; it never holds a Firebase admin credential itself.
//   leadArrived         inquiries/{id} created -> the vendor's people: "New lead: Maya & Leo.
//                       June has a first reply ready." Opens the thread.
//   messageArrived      inquiries/{id}/messages/{mid} created -> the other side: a couple's
//                       message pushes the vendor, a vendor's reply pushes the couple.
//   coupleMorning       08:00 America/Phoenix -> every couple with a date: the countdown and
//                       what is waiting on them, one line, opens June on the deck.
//
// Tokens live where FlutterFlow puts them: users/{uid}/fcm_tokens/{doc}.fcm_token.
// Quiet hours: nothing pushes between 22:00 and 07:00 Phoenix except a real lead.

'use strict';

const { onRequest } = require('firebase-functions/v2/https');
const { onDocumentCreated } = require('firebase-functions/v2/firestore');
const { onSchedule } = require('firebase-functions/v2/scheduler');
const admin = require('firebase-admin');

module.exports = (JUNE_PUSH_KEY) => {
  const db = () => admin.firestore();
  const str = (v) => (v == null ? '' : String(v));
  const clip = (s, n) => str(s).trim().slice(0, n);
  const JUNE_URL = 'https://june.meetlazo.com/';

  const phoenixHour = () => +new Date().toLocaleString('en-US', { timeZone: 'America/Phoenix', hour: 'numeric', hour12: false }) % 24;
  const quiet = () => { const h = phoenixHour(); return h >= 22 || h < 7; };

  async function tokensFor(uid) {
    const snap = await db().collection('users').doc(uid).collection('fcm_tokens').get();
    const out = [];
    snap.forEach((d) => { const t = str(d.get('fcm_token')); if (t) out.push({ ref: d.ref, token: t }); });
    return out;
  }

  // one push to one person; returns how many devices took it
  async function pushTo(uid, { title, body, data = {}, tag = '' }) {
    if (!uid) return 0;
    const toks = await tokensFor(uid);
    if (!toks.length) return 0;
    const msg = {
      tokens: toks.map((t) => t.token),
      notification: { title: clip(title, 80), body: clip(body, 180) },
      data: Object.fromEntries(Object.entries({ ...data, tag, from: 'june' }).map(([k, v]) => [k, str(v)])),
      android: { priority: 'high', notification: { channelId: 'june', tag: tag || undefined, sound: 'default' } },
      apns: { payload: { aps: { sound: 'default', 'thread-id': tag || 'june', badge: 1 } } },
    };
    const res = await admin.messaging().sendEachForMulticast(msg);
    const dead = [];
    res.responses.forEach((r, i) => {
      const code = r.error && r.error.code;
      if (code === 'messaging/registration-token-not-registered' || code === 'messaging/invalid-registration-token') dead.push(toks[i].ref);
    });
    await Promise.all(dead.map((ref) => ref.delete().catch(() => {})));
    return res.successCount;
  }

  // everyone who runs this vendor (owner + team) - users.vendorId
  async function vendorPeople(vendorId) {
    const snap = await db().collection('users').where('vendorId', '==', vendorId).get();
    const uids = [];
    snap.forEach((d) => uids.push(d.id));
    return uids;
  }

  // ---------------------------------------------------------------- the worker's door
  const junePush = onRequest({ cors: false, invoker: 'public', memory: '256MiB', secrets: [JUNE_PUSH_KEY] }, async (req, res) => {
    if (req.method !== 'POST') return res.status(405).send('POST');
    // trimmed on both sides: a secret set through a shell pipe carries a newline
    const want = str(JUNE_PUSH_KEY.value()).trim();
    if (!want || str(req.get('x-june-key')).trim() !== want) return res.status(401).json({ error: 'no' });
    const b = req.body || {};
    const uids = Array.isArray(b.uids) ? b.uids.map(String) : b.uid ? [String(b.uid)] : [];
    if (!uids.length || !b.title) return res.status(400).json({ error: 'uid and title' });
    if (quiet() && !b.urgent) return res.json({ sent: 0, quiet: true });
    let sent = 0;
    for (const uid of uids) { try { sent += await pushTo(uid, { title: b.title, body: b.body || '', data: b.data || {}, tag: b.tag || '' }); } catch (e) { console.log('junePush', uid, e.message); } }
    res.json({ sent });
  });

  // ---------------------------------------------------------------- a lead lands: the reply-first alarm
  const leadArrived = onDocumentCreated({ document: 'inquiries/{inquiryId}', region: 'us-central1', memory: '256MiB' }, async (event) => {
    const d = event.data && event.data.data();
    if (!d || d.preview === true || d.practice === true) return;
    const vendorId = str(d.vendorId);
    if (!vendorId) return;
    const who = str(d.coupleName) || 'A verified couple';
    const when = str(d.weddingDate || d.weddingDateIso).slice(0, 10);
    const uids = await vendorPeople(vendorId);
    for (const uid of uids) {
      try {
        await pushTo(uid, {
          title: `New lead: ${who}`,
          body: `${when ? when + ' · ' : ''}June has a first reply ready. Couples book whoever answers first.`,
          data: { thread: event.params.inquiryId, open: 'thread' },
          tag: 'lead-' + event.params.inquiryId,
        });
      } catch (e) { console.log('leadArrived', uid, e.message); }
    }
  });

  // ---------------------------------------------------------------- a message lands: push the other side
  const messageArrived = onDocumentCreated({ document: 'inquiries/{inquiryId}/messages/{messageId}', region: 'us-central1', memory: '256MiB' }, async (event) => {
    const m = event.data && event.data.data();
    if (!m) return;
    const role = str(m.senderRole || m.from);
    if (!role || role === 'system' || role === 'june') return;
    const inq = await db().collection('inquiries').doc(event.params.inquiryId).get();
    const d = inq.data() || {};
    if (d.preview === true || d.practice === true) return;
    const text = clip(m.text || m.body || (m.attachment ? 'Sent an attachment' : ''), 140) || 'New message';
    if (role === 'couple') {
      const uids = await vendorPeople(str(d.vendorId));
      for (const uid of uids) {
        if (quiet()) break;
        try { await pushTo(uid, { title: `${str(d.coupleName) || 'A couple'} wrote back`, body: text, data: { thread: event.params.inquiryId, open: 'thread' }, tag: 'thread-' + event.params.inquiryId }); } catch (e) { console.log('messageArrived', uid, e.message); }
      }
    } else if (role === 'vendor') {
      const cuid = str(d.coupleUid);
      if (!cuid || quiet()) return;
      // the couple and any partner on the same plan
      const partners = await db().collection('users').where('coupleUid', '==', cuid).get();
      const uids = new Set([cuid]);
      partners.forEach((p) => uids.add(p.id));
      for (const uid of uids) {
        try { await pushTo(uid, { title: `${str(d.vendorName) || 'Your vendor'} replied`, body: text, data: { thread: event.params.inquiryId, open: 'thread' }, tag: 'thread-' + event.params.inquiryId }); } catch (e) { console.log('messageArrived couple', uid, e.message); }
      }
    }
  });

  // ---------------------------------------------------------------- couples: the morning line
  const coupleMorning = onSchedule({ schedule: '0 8 * * *', timeZone: 'America/Phoenix', memory: '512MiB', timeoutSeconds: 540 }, async () => {
    const today = new Date().toLocaleDateString('en-CA', { timeZone: 'America/Phoenix' });
    const snap = await db().collection('couples').where('weddingDate', '>=', admin.firestore.Timestamp.fromDate(new Date(today + 'T00:00:00Z'))).get();
    let sent = 0;
    for (const doc of snap.docs) {
      const c = doc.data() || {};
      if (c.preview === true || c.pushBrief === false) continue;
      const wd = c.weddingDate && c.weddingDate.toDate ? c.weddingDate.toDate() : null;
      if (!wd) continue;
      const days = Math.round((Date.UTC(wd.getUTCFullYear(), wd.getUTCMonth(), wd.getUTCDate()) - Date.parse(today + 'T00:00:00Z')) / 86400e3);
      if (days < 0 || days > 540) continue;
      // what is waiting on them: unread vendor replies + pending RSVPs
      let waiting = 0, pending = 0, gaps = 0;
      try {
        const inqs = await db().collection('inquiries').where('coupleUid', '==', doc.id).get();
        inqs.forEach((i) => { const x = i.data(); if (x.lastMessageRole === 'vendor' &&(!x.coupleLastReadAt || (x.lastMessageAt && x.lastMessageAt.toMillis && x.coupleLastReadAt.toMillis && x.lastMessageAt.toMillis() > x.coupleLastReadAt.toMillis()))) waiting++; });
        const gs = await doc.ref.collection('guests').get();
        gs.forEach((g) => { const x = g.data(); if (x.rsvp == null || x.rsvp === 'pending' || x.rsvp === '') pending++; });
        const plan = await doc.ref.collection('plan').get();
        plan.forEach((p) => { if (str(p.get('status')) === 'needed') gaps++; });
      } catch (e) { console.log('coupleMorning count', doc.id, e.message); }
      const bits = [];
      if (waiting) bits.push(`${waiting} vendor repl${waiting === 1 ? 'y' : 'ies'} to read`);
      if (gaps) bits.push(`${gaps} vendor${gaps === 1 ? '' : 's'} still to book`);
      if (pending && days <= 120) bits.push(`${pending} RSVP${pending === 1 ? '' : 's'} pending`);
      const milestone = days === 100 ? '100 days today. ' : days === 50 ? '50 days today. ' : days === 30 ? 'One month today. ' : days === 7 ? 'One week. ' : days === 1 ? 'Tomorrow. ' : days === 0 ? 'Today is the day. ' : '';
      const title = days === 0 ? 'It’s your wedding day' : `${days} day${days === 1 ? '' : 's'} to go`;
      const body = milestone + (bits.length ? bits.join(' · ') + '. ' : '') + (days === 0 ? 'Have the best day. June is here if anyone needs anything.' : 'June has your day ready.');
      const partners = await db().collection('users').where('coupleUid', '==', doc.id).get();
      const uids = new Set([doc.id]);
      partners.forEach((p) => uids.add(p.id));
      for (const uid of uids) { try { sent += await pushTo(uid, { title, body, data: { open: 'june' }, tag: 'morning' }); } catch (e) { console.log('coupleMorning', uid, e.message); } }
    }
    console.log('coupleMorning sent', sent);
  });

  return { junePush, leadArrived, messageArrived, coupleMorning };
};

// END OF FILE - JC-LAZO-FNDASH-1011-026
