// functions-dashboard/callsched.js
// Build ID: JC-LAZO-CALLSCHED-1016-001
//
// SCHEDULE A LAZO VIDEO CALL, FROM THE THREAD.
//
// A scheduled call is a consults/{id} doc (the same collection the /book
// scheduler writes), marked lazoCall:true, so the vendor's "Upcoming consults"
// card, the thread's consult strip and the rules (couple + vendor read,
// server write) all already work. The thread gets a message carrying
// callSchedule:{consultId}; both apps draw it as the call card.
//
// Plan rule (Jesse, 2026-10-16): video calls are free for everyone; SCHEDULING
// one is Lazo Pro and Studio. A couple can schedule with a Pro/Studio vendor;
// with a Free vendor they only get "Start a call now".
//
//   scheduleCall    callable {inquiryId, startAt ISO, minutes, tzOffsetMin, tzName, audioOnly?}
//   rescheduleCall  callable {consultId, startAt, minutes, tzOffsetMin, tzName}
//   cancelCall      callable {consultId}
//   setCallPref     callable {inquiryId, audioOnly}  (couple: "I prefer audio only")
//   callIcs         GET ?id=&t=  -> the call as an .ics (Add to calendar)
//   callReminderSweep  every 5 min: push + email to both sides ~24h and ~15 min before.
//
// Every call safety rule still applies when they join: callJoin (calls.js)
// checks the thread, phone verification, blocks; the worker keeps the camera
// off at join and the couple's camera locked until the vendor allows it.

'use strict';

const crypto = require('crypto');
const { onCall, onRequest, HttpsError } = require('firebase-functions/v2/https');
const { onSchedule } = require('firebase-functions/v2/scheduler');
const admin = require('firebase-admin');

const APP = 'https://app.meetlazo.com/dashboard';
const ICS_BASE = 'https://us-central1-lazo-513ec.cloudfunctions.net/callIcs';
const FROM = 'Lazo <hello@meetlazo.com>';
const LENGTHS = [15, 30, 45, 60, 90];
const MIN_LEAD_MIN = 5;
const MAX_DAYS_OUT = 180;

const db = () => admin.firestore();
const FV = () => admin.firestore.FieldValue;
const TS = () => admin.firestore.Timestamp;
const str = (v) => (v == null ? '' : String(v));
const clip = (s, n) => str(s).slice(0, n);
const toDate = (v) => (v && typeof v.toDate === 'function') ? v.toDate() : (v instanceof Date ? v : null);
const emailOk = (e) => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(str(e));
const esc = (s) => str(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

function tierOf(v) {
  const t = str(v && v.tier);
  if (t !== 'pro' && t !== 'studio') return 'free';
  const exp = toDate(v.tierExpiresAt);
  if (exp && exp < new Date()) return 'free';
  return t;
}

// "Saturday, October 18 at 3:00 PM MST" in an IANA zone, or at a fixed UTC offset
function whenIn(date, { tz, offsetMin, name }) {
  const opts = { weekday: 'long', month: 'long', day: 'numeric', hour: 'numeric', minute: '2-digit' };
  try {
    if (tz) {
      const s = new Intl.DateTimeFormat('en-US', { ...opts, timeZone: tz }).format(date);
      const z = new Intl.DateTimeFormat('en-US', { timeZone: tz, timeZoneName: 'short' }).format(date).split(' ').pop();
      return `${s} ${z}`.replace(/, (\d)/, ' at $1');
    }
  } catch (e) {}
  if (typeof offsetMin === 'number' && isFinite(offsetMin)) {
    const shifted = new Date(date.getTime() + offsetMin * 60000);
    const s = new Intl.DateTimeFormat('en-US', { ...opts, timeZone: 'UTC' }).format(shifted);
    const z = name || `UTC${offsetMin >= 0 ? '+' : '-'}${String(Math.floor(Math.abs(offsetMin) / 60)).padStart(2, '0')}:${String(Math.abs(offsetMin) % 60).padStart(2, '0')}`;
    return `${s} ${z}`.replace(/, (\d)/, ' at $1');
  }
  return whenIn(date, { tz: 'America/Phoenix' });
}

function icsText(c, id) {
  const f = (d) => d.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '');
  const start = toDate(c.startAt), end = toDate(c.endAt);
  return ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Lazo//Video calls//EN', 'METHOD:PUBLISH', 'BEGIN:VEVENT',
    `UID:${id}@meetlazo.com`, `DTSTAMP:${f(new Date())}`, `DTSTART:${f(start)}`, `DTEND:${f(end)}`,
    `SUMMARY:Lazo video call: ${str(c.vendorName)} & ${str(c.coupleName)}`.replace(/,/g, '\\,'),
    'DESCRIPTION:Open your Lazo messages and tap Join (it opens 10 minutes before). Calls stay inside Lazo - never join an outside link.',
    'LOCATION:Lazo video call (in your Lazo messages)', `URL:${APP}?thread=${str(c.inquiryId)}`,
    'BEGIN:VALARM', 'TRIGGER:-PT15M', 'ACTION:DISPLAY', 'DESCRIPTION:Lazo video call in 15 minutes', 'END:VALARM',
    'END:VEVENT', 'END:VCALENDAR'].join('\r\n');
}

module.exports = function callSchedModule(RESEND_API_KEY) {

  async function userDoc(uid) {
    const s = await db().collection('users').doc(uid).get();
    return s.exists ? (s.data() || {}) : {};
  }
  async function roleOn(inq, uid, u) {
    const cuid = str(inq.coupleUid);
    if (cuid && !cuid.startsWith('lead_') && (cuid === uid || str(u.coupleUid) === cuid)) return 'couple';
    const vendorId = str(inq.vendorId);
    if (!vendorId) return null;
    const v = await db().collection('vendors').doc(vendorId).get();
    if (v.exists && str(v.get('claimedBy')) === uid) return 'vendor';
    if (str(u.vendorId) === vendorId && str(u.vendorRole) === 'manager') return 'vendor';
    return null;
  }
  async function threadFor(uid, inquiryId) {
    if (!uid) throw new HttpsError('unauthenticated', 'Sign in first.');
    const ref = db().collection('inquiries').doc(clip(inquiryId, 80));
    const s = await ref.get();
    if (!s.exists) throw new HttpsError('not-found', 'Conversation not found.');
    const inq = s.data() || {};
    const u = await userDoc(uid);
    const role = await roleOn(inq, uid, u);
    if (!role) throw new HttpsError('permission-denied', 'Not your conversation.');
    if (u.safetyBlock) throw new HttpsError('permission-denied', 'Your account is under review. Contact support@meetlazo.com.', { code: 'account-under-review' });
    if (inq.coupleSafetyBlocked === true || inq.blockedByCouple === true || inq.blockedByVendor === true) {
      throw new HttpsError('failed-precondition', 'This conversation is closed.', { code: 'closed' });
    }
    if (str(inq.coupleUid).startsWith('lead_') || inq.offPlatform === true) {
      throw new HttpsError('failed-precondition', 'Lazo video calls are for couples with a Lazo account. Send your booking link for a phone call instead.', { code: 'lead-no-video' });
    }
    return { ref, inq, role, u };
  }
  async function vendorOf(inq) {
    const s = await db().collection('vendors').doc(str(inq.vendorId)).get();
    return s.exists ? (s.data() || {}) : {};
  }
  function parseWhen(d) {
    const start = new Date(str(d.startAt));
    if (isNaN(start.getTime())) throw new HttpsError('invalid-argument', 'Pick a date and time.', { code: 'bad-time' });
    if (start.getTime() < Date.now() + MIN_LEAD_MIN * 60000) throw new HttpsError('invalid-argument', 'Pick a time at least a few minutes from now. For right now, start a call instead.', { code: 'too-soon' });
    if (start.getTime() > Date.now() + MAX_DAYS_OUT * 86400000) throw new HttpsError('invalid-argument', 'Pick a time within the next six months.', { code: 'too-far' });
    const minutes = LENGTHS.includes(Number(d.minutes)) ? Number(d.minutes) : 30;
    return { start, end: new Date(start.getTime() + minutes * 60000), minutes };
  }
  function tzOfCaller(d) {
    const off = Number(d.tzOffsetMin);
    return isFinite(off) && Math.abs(off) <= 14 * 60 ? { offsetMin: Math.round(off), name: clip(d.tzName, 8).replace(/[^A-Za-z+\-0-9]/g, '') } : null;
  }
  // both sides' wording, each in their own time zone (couple's only when we know it)
  function whenFor(c, start) {
    const out = { vendor: whenIn(start, { tz: str(c.vendorTz) || 'America/Phoenix' }) };
    if (c.coupleTz && typeof c.coupleTz.offsetMin === 'number') out.couple = whenIn(start, c.coupleTz);
    return out;
  }

  async function mail(to, subject, html, text) {
    if (!emailOk(to)) return;
    try {
      await fetch('https://api.resend.com/emails', {
        method: 'POST', headers: { Authorization: `Bearer ${RESEND_API_KEY.value()}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ from: FROM, to: [to], subject, html, text }),
      });
    } catch (e) { console.warn('[callsched] mail', e.message); }
  }
  async function pushTo(uid, title, body, thread) {
    if (!uid) return 0;
    const snap = await db().collection('users').doc(uid).collection('fcm_tokens').get();
    const toks = [];
    snap.forEach((d) => { const t = str(d.get('fcm_token')); if (t) toks.push(t); });
    if (!toks.length) return 0;
    try {
      const res = await admin.messaging().sendEachForMulticast({
        tokens: toks, notification: { title: clip(title, 80), body: clip(body, 180) },
        data: { thread: str(thread), open: 'thread', tag: 'call-' + str(thread), from: 'lazo' },
        android: { priority: 'high', notification: { channelId: 'june', sound: 'default' } },
        apns: { payload: { aps: { sound: 'default', 'thread-id': 'call-' + str(thread) } } },
      });
      return res.successCount;
    } catch (e) { console.warn('[callsched] push', e.message); return 0; }
  }
  async function people(c) {
    const vendorUids = [];
    const vs = await db().collection('users').where('vendorId', '==', str(c.vendorId)).get();
    vs.forEach((d) => vendorUids.push(d.id));
    const v = await db().collection('vendors').doc(str(c.vendorId)).get();
    const owner = v.exists ? str(v.get('claimedBy')) : '';
    if (owner && !vendorUids.includes(owner)) vendorUids.push(owner);
    const coupleUids = [str(c.coupleUid)];
    const ps = await db().collection('users').where('coupleUid', '==', str(c.coupleUid)).get();
    ps.forEach((d) => { if (!coupleUids.includes(d.id)) coupleUids.push(d.id); });
    const email = async (uid) => str((await userDoc(uid)).email);
    return {
      vendorUids, coupleUids,
      vendorEmail: owner ? await email(owner) : str(v.exists && v.get('email')),
      coupleEmail: await email(str(c.coupleUid)),
    };
  }
  // tell the other side (both, for reminders)
  async function notify(c, id, which, subject, line) {
    const p = await people(c);
    const thread = str(c.inquiryId);
    const link = `${APP}?thread=${thread}`;
    const wf = c.whenFor || {};
    const sides = which === 'both' ? ['vendor', 'couple'] : [which];
    for (const side of sides) {
      const when = side === 'vendor' ? wf.vendor : (wf.couple || wf.vendor);
      const other = side === 'vendor' ? str(c.coupleName) : str(c.vendorName);
      const text = line.replace('{when}', when || '').replace('{other}', other);
      for (const uid of side === 'vendor' ? p.vendorUids : p.coupleUids) await pushTo(uid, subject, text, thread);
      const to = side === 'vendor' ? p.vendorEmail : p.coupleEmail;
      await mail(to, subject,
        `<p>${esc(text)}</p><p><a href="${link}">Open the conversation</a> - Join opens 10 minutes before. <a href="${ICS_BASE}?id=${id}&t=${str(c.icsToken)}">Add to calendar</a>.</p><p style="color:#6B5F72;font-size:12px">Lazo video calls stay inside Lazo. Never join a Zoom, FaceTime or WhatsApp link sent in its place.</p>`,
        `${text}\n${link}`);
    }
  }
  async function threadNote(inqRef, role, text, consultId, extra) {
    await inqRef.collection('messages').add({ senderRole: role, system: true, callSchedule: { consultId }, text, at: FV().serverTimestamp(), ...(extra || {}) });
    await inqRef.set({ lastMessageAt: FV().serverTimestamp(), lastMessageRole: role, lastMessagePreview: text.slice(0, 140) }, { merge: true });
  }

  // ---------------------------------------------------------- scheduleCall ----
  const scheduleCall = onCall({ memory: '256MiB', secrets: [RESEND_API_KEY] }, async (request) => {
    const uid = request.auth && request.auth.uid;
    const d = request.data || {};
    const { ref, inq, role } = await threadFor(uid, d.inquiryId);
    const v = await vendorOf(inq);
    if (tierOf(v) === 'free') {
      throw new HttpsError('permission-denied', role === 'vendor' ? 'Scheduling calls is part of Lazo Pro.' : 'This vendor can’t take scheduled calls yet. Start a call now instead.', { code: 'pro-required' });
    }
    const { start, end, minutes } = parseWhen(d);
    const callerTz = tzOfCaller(d);
    const c = {
      vendorId: str(inq.vendorId), vendorName: str(inq.vendorName) || str(v.name), inquiryId: ref.id, coupleUid: str(inq.coupleUid),
      coupleName: str(inq.coupleName) || 'The couple',
      contact: { name: str(inq.coupleName) || 'The couple' },   // the vendor's Upcoming consults card reads contact.name
      typeKey: 'lazo_call', typeLabel: 'Lazo video call', mode: 'video', minutes, lazoCall: true,
      startAt: TS().fromDate(start), endAt: TS().fromDate(end), tz: str(v.scheduler && v.scheduler.tz) || 'America/Phoenix',
      vendorTz: str(v.scheduler && v.scheduler.tz) || str(v.tz) || 'America/Phoenix',
      status: 'booked', source: 'call', scheduledBy: role, scheduledByUid: uid,
      cancelToken: crypto.randomBytes(12).toString('base64url'), icsToken: crypto.randomBytes(12).toString('base64url'),
      createdAt: FV().serverTimestamp(), reminded: {}, note: '',
    };
    if (role === 'couple' && callerTz) c.coupleTz = callerTz;
    else if (inq.coupleTz) c.coupleTz = inq.coupleTz;
    c.whenFor = whenFor(c, start);
    const cRef = db().collection('consults').doc();
    await cRef.set(c);
    if (role === 'couple') {
      const patch = { nextConsultAt: c.startAt };
      if (callerTz) patch.coupleTz = callerTz;
      if (typeof d.audioOnly === 'boolean') patch.coupleAudioOnly = d.audioOnly;
      await ref.set(patch, { merge: true });
    } else {
      await ref.set({ nextConsultAt: c.startAt }, { merge: true });
    }
    await threadNote(ref, role, 'Scheduled a Lazo video call.', cRef.id);
    const other = role === 'vendor' ? 'couple' : 'vendor';
    await notify(c, cRef.id, other, `Lazo video call: ${role === 'vendor' ? c.vendorName : c.coupleName}`, `${role === 'vendor' ? c.vendorName : c.coupleName} scheduled a Lazo video call for {when}.`);
    return { ok: true, consultId: cRef.id, whenFor: c.whenFor };
  });

  async function consultFor(uid, consultId) {
    if (!uid) throw new HttpsError('unauthenticated', 'Sign in first.');
    const id = clip(consultId, 80);
    if (!id || id.includes('/')) throw new HttpsError('invalid-argument', 'Which call?');
    const cRef = db().collection('consults').doc(id);
    const s = await cRef.get();
    if (!s.exists) throw new HttpsError('not-found', 'Call not found.');
    const c = s.data() || {};
    if (c.lazoCall !== true) throw new HttpsError('failed-precondition', 'That one is managed from the booking page.');
    const t = await threadFor(uid, c.inquiryId);
    return { cRef, c, ...t };
  }

  // -------------------------------------------------------- rescheduleCall ----
  const rescheduleCall = onCall({ memory: '256MiB', secrets: [RESEND_API_KEY] }, async (request) => {
    const uid = request.auth && request.auth.uid;
    const d = request.data || {};
    const { cRef, c, ref, role } = await consultFor(uid, d.consultId);
    if (c.status !== 'booked') throw new HttpsError('failed-precondition', 'This call was cancelled. Schedule a new one.', { code: 'cancelled' });
    const { start, end, minutes } = parseWhen(d);
    const callerTz = tzOfCaller(d);
    const next = { ...c, startAt: TS().fromDate(start), endAt: TS().fromDate(end), minutes };
    if (role === 'couple' && callerTz) next.coupleTz = callerTz;
    next.whenFor = whenFor(next, start);
    await cRef.set({ startAt: next.startAt, endAt: next.endAt, minutes, whenFor: next.whenFor, reminded: {}, ...(next.coupleTz ? { coupleTz: next.coupleTz } : {}),
      rescheduledAt: FV().serverTimestamp(), rescheduledBy: role, reschedules: FV().increment(1) }, { merge: true });
    await ref.set({ nextConsultAt: next.startAt }, { merge: true });
    await threadNote(ref, role, 'Moved the Lazo video call.', cRef.id);
    const other = role === 'vendor' ? 'couple' : 'vendor';
    await notify(next, cRef.id, other, 'Lazo video call moved', `${role === 'vendor' ? c.vendorName : c.coupleName} moved your Lazo video call to {when}.`);
    return { ok: true, whenFor: next.whenFor };
  });

  // ------------------------------------------------------------ cancelCall ----
  const cancelCall = onCall({ memory: '256MiB', secrets: [RESEND_API_KEY] }, async (request) => {
    const uid = request.auth && request.auth.uid;
    const { cRef, c, ref, role } = await consultFor(uid, (request.data || {}).consultId);
    if (c.status === 'cancelled') return { ok: true, already: true };
    await cRef.set({ status: 'cancelled', cancelledAt: FV().serverTimestamp(), cancelledBy: role }, { merge: true });
    await ref.set({ nextConsultAt: null }, { merge: true });
    await threadNote(ref, role, 'Cancelled the Lazo video call.', cRef.id);
    const other = role === 'vendor' ? 'couple' : 'vendor';
    await notify(c, cRef.id, other, 'Lazo video call cancelled', `${role === 'vendor' ? c.vendorName : c.coupleName} cancelled the Lazo video call on {when}.`);
    return { ok: true };
  });

  // ----------------------------------------------------------- setCallPref ----
  const setCallPref = onCall({ memory: '256MiB' }, async (request) => {
    const uid = request.auth && request.auth.uid;
    const d = request.data || {};
    const { ref, role } = await threadFor(uid, d.inquiryId);
    if (role !== 'couple') throw new HttpsError('permission-denied', 'Only the couple sets this.');
    await ref.set({ coupleAudioOnly: d.audioOnly === true }, { merge: true });
    return { ok: true, audioOnly: d.audioOnly === true };
  });

  // --------------------------------------------------------------- callIcs ----
  const callIcs = onRequest({ memory: '256MiB', invoker: 'public' }, async (req, res) => {
    const id = clip(req.query.id, 80), t = clip(req.query.t, 40);
    const s = id ? await db().collection('consults').doc(id).get() : null;
    if (!s || !s.exists || !t || str(s.get('icsToken')) !== t || s.get('lazoCall') !== true) return res.status(404).send('Not found');
    res.set('content-type', 'text/calendar; charset=utf-8');
    res.set('content-disposition', 'attachment; filename="lazo-video-call.ics"');
    res.set('cache-control', 'no-store');
    res.send(icsText(s.data(), id));
  });

  // ----------------------------------------------------- callReminderSweep ----
  const callReminderSweep = onSchedule({ schedule: '*/5 * * * *', timeZone: 'America/Phoenix', memory: '256MiB', timeoutSeconds: 240, secrets: [RESEND_API_KEY] }, async () => {
    const now = Date.now();
    const snap = await db().collection('consults').where('status', '==', 'booked')
      .where('startAt', '>=', TS().fromMillis(now)).where('startAt', '<=', TS().fromMillis(now + 25 * 3600000)).get();
    let sent = 0;
    for (const d of snap.docs) {
      const c = d.data();
      if (c.lazoCall !== true) continue;
      const start = toDate(c.startAt);
      const mins = (start.getTime() - now) / 60000;
      const rem = c.reminded || {};
      let key = null;
      if (mins <= 16 && !rem.m15) key = 'm15';
      else if (mins <= 24 * 60 + 15 && mins > 60 && !rem.h24) key = 'h24';
      if (!key) continue;
      await d.ref.set({ reminded: { ...rem, [key]: FV().serverTimestamp() } }, { merge: true });
      try {
        await notify(c, d.id, 'both', key === 'm15' ? 'Lazo video call in 15 minutes' : 'Lazo video call tomorrow',
          key === 'm15' ? 'Your Lazo video call with {other} starts in about 15 minutes. Open Lazo and tap Join.' : 'Reminder: Lazo video call with {other}, {when}.');
        sent++;
      } catch (e) { console.warn('callReminderSweep', d.id, e.message); }
    }
    console.log(`callReminderSweep: ${snap.size} upcoming, ${sent} reminded`);
  });

  return { scheduleCall, rescheduleCall, cancelCall, setCallPref, callIcs, callReminderSweep };
};

module.exports._test = { tierOf, whenIn, icsText };

// END OF FILE - JC-LAZO-CALLSCHED-1016-001
