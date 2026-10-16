// functions-dashboard/join.js
// Build ID: JC-LAZO-FNDASH-1016-JOIN-001
//
// GETTING AN OFF-PLATFORM CLIENT TO MAKE HER LAZO ACCOUNT. She signed or paid
// with a Lazo vendor from the login-free /f/ page; she never has to join to do
// that. Joining is the next step, sold by email:
//   day 0   rides on the signed / receipt email (couple-notify.js), which also
//           starts inquiries.joinNudge = { day0At, next:'day3', nextAt, sms }
//   day 3   the free wedding website            } joinSweep, 9am-8pm Phoenix,
//   day 7   June, the guest list, one inbox      } stops the moment she joins
//   day 14  the rest of her team in her metro    } or taps "Stop these emails"
//   + one text, only where the lead form recorded smsOk
// Words: join-copy.js. The claim (thread -> her new account, referring vendor
// recorded on her user doc) is below: it needs her VERIFIED email to match the
// one her vendor has; the link only says which thread.
//
// Functions
//   joinGo     GET ?i=&t=&s=   logs the click, 302 to the pre-filled signup
//              (the worker serves it at meetlazo.com/join/{inquiry}?t=&s=)
//   joinStop   GET ?i=&t=      no more join emails or texts for that thread
//              (meetlazo.com/join/{inquiry}/stop?t=)
//   joinSweep  every hour       sends the due step and the pending text, and
//              finishes claims waiting on a confirmed email
//   joinDone   GET ?i=&t=      where the "confirm your email" link lands
//              (meetlazo.com/join/{inquiry}/done?t=) - claims, then opens the app
//   joinInfo   callable {inquiryId, t} -> the email the signup screen pre-fills and locks
//   onUserClaimLeads   users/{uid} written (signup) -> claimLeadThreads
//   claimMyLeadThreads callable {inquiryId?, t?} -> { claimed, status, masked }
//
// Tracking: joinNudge.clicks.<step> (first click per step), joinNudge.claimedAt
// / claimedStep / claimedVia, joinNudge.mismatch.<uid>, and one joinEvents doc per
// click / send / stop / verify-sent / mismatch / relay / claim.

'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { onRequest, onCall, HttpsError } = require('firebase-functions/v2/https');
const { onDocumentWritten } = require('firebase-functions/v2/firestore');
const { onSchedule } = require('firebase-functions/v2/scheduler');
const { defineSecret } = require('firebase-functions/params');
const admin = require('firebase-admin');
const C = require('./join-copy');

const TELNYX_API_KEY = defineSecret('TELNYX_API_KEY');
const TELNYX_FROM = defineSecret('TELNYX_FROM');
const FROM = 'Lazo <hello@meetlazo.com>';
const APP = 'https://app.meetlazo.com/';

const db = () => admin.firestore();
const { FieldValue, Timestamp } = admin.firestore;
const str = (v) => (v == null ? '' : String(v));
const emailOk = (e) => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(str(e).trim());
const e164 = (raw) => { const d = str(raw).replace(/[^\d]/g, ''); return d.length === 10 ? '+1' + d : d.length === 11 && d.startsWith('1') ? '+' + d : d.length > 11 && d.length < 16 ? '+' + d : ''; };
const tokenOk = (want, t) => !!want && !!t && want.length === t.length && crypto.timingSafeEqual(Buffer.from(want), Buffer.from(t));
// still hers to claim: an off-platform thread nobody has taken
const open = (inq) => inq.offPlatform === true && str(inq.coupleUid).startsWith('lead_');
// Who proves her email. Once verify.js ships (signup's 6-digit code: sendEmailCode /
// verifyEmailCode set emailVerified through the Admin SDK and then call
// claimLeadThreads below), this file sends no confirm link of its own, so she never
// gets two emails at signup. Until then, the confirm link below does the job.
// JOIN_VERIFY_LINK=on|off overrides (tests).
const codeVerifyLive = () => process.env.JOIN_VERIFY_LINK === 'off' || (process.env.JOIN_VERIFY_LINK !== 'on' && fs.existsSync(path.join(__dirname, 'verify.js')));
const phoenixHour = (d) => Number(new Intl.DateTimeFormat('en-US', { timeZone: 'America/Phoenix', hour: 'numeric', hourCycle: 'h23' }).format(d));

module.exports = function joinModule(RESEND_API_KEY) {

  async function sendEmail(to, m, replyTo) {
    const r = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${RESEND_API_KEY.value()}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ from: FROM, to: [to], reply_to: replyTo || 'hello@meetlazo.com', subject: m.subject, html: m.html, text: m.text }),
    });
    if (!r.ok) throw new Error(`resend ${r.status}: ${await r.text()}`);
  }
  async function sendSms(to, text) {
    const t = e164(to); if (!t) return false;
    const r = await fetch('https://api.telnyx.com/v2/messages', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${TELNYX_API_KEY.value()}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ from: TELNYX_FROM.value(), to: t, text: text.slice(0, 1500) }),
    });
    if (!r.ok) { console.warn('telnyx join', r.status, await r.text()); return false; }
    return true;
  }
  const event = (type, inquiryId, inq, extra) => db().collection('joinEvents').add({ type, inquiryId, vendorId: str(inq.vendorId), at: FieldValue.serverTimestamp(), ...(extra || {}) }).catch(() => {});
  async function vendorOf(inq) { const s = await db().collection('vendors').doc(str(inq.vendorId) || '_').get().catch(() => null); return s && s.exists ? { id: s.id, ...s.data() } : {}; }

  const page = (title, body) => `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>${title}</title></head><body style="margin:0;background:#FAF6F0;font-family:Helvetica,Arial,sans-serif;color:#241E2B"><div style="max-width:460px;margin:12vh auto;padding:28px 22px;background:#fff;border:1px solid #EADFCB;border-radius:18px;text-align:center"><p style="font-family:Georgia,serif;font-size:26px;color:#3D1C3B;margin:0 0 10px">${title}</p><p style="font-size:15px;line-height:1.6;color:#5B5363;margin:0">${body}</p></div></body></html>`;

  // GET ?i=&t=&s=  -> 302 to the pre-filled signup (or the app, once she has joined)
  const joinGo = onRequest({ invoker: 'public', memory: '256MiB' }, async (req, res) => {
    try {
      const i = str(req.query.i).slice(0, 80), t = str(req.query.t).slice(0, 80);
      const step = /^[a-z0-9_-]{1,16}$/i.test(str(req.query.s)) ? str(req.query.s) : 'link';
      const ref = db().collection('inquiries').doc(i || '_');
      const s = await ref.get();
      if (!s.exists || !tokenOk(str(s.get('fileToken')), t)) return res.redirect(302, APP);
      const inq = s.data();
      if (!open(inq)) return res.redirect(302, APP);   // already joined: just sign in
      const clicks = (inq.joinNudge && inq.joinNudge.clicks) || {};
      await ref.set({ joinNudge: { lastClickAt: FieldValue.serverTimestamp(), lastClickStep: step, ...(clicks[step] ? {} : { clicks: { [step]: FieldValue.serverTimestamp() } }) } }, { merge: true });
      await event('click', s.id, inq, { step });
      const medium = step === 'sms' ? 'sms' : step === 'fpage' ? 'page' : 'email';
      res.set('cache-control', 'no-store').redirect(302, C.appUrl(s.id, inq, await vendorOf(inq), step, medium));
    } catch (e) { console.error('joinGo', e); res.redirect(302, APP); }
  });

  // GET ?i=&t=  -> stop the join emails and text for this thread
  const joinStop = onRequest({ invoker: 'public', memory: '256MiB' }, async (req, res) => {
    const done = (title, body) => res.set('content-type', 'text/html; charset=utf-8').set('cache-control', 'no-store').send(page(title, body));
    try {
      const i = str(req.query.i).slice(0, 80), t = str(req.query.t).slice(0, 80);
      const ref = db().collection('inquiries').doc(i || '_');
      const s = await ref.get();
      if (!s.exists || !tokenOk(str(s.get('fileToken')), t)) return done('Link not recognised', 'This link has expired. Reply to any of our emails and we’ll take you off the list.');
      await ref.set({ joinNudge: { stopped: true, stoppedAt: FieldValue.serverTimestamp(), nextAt: null, sms: str(s.get('joinNudge.sms')) === 'pending' ? 'stopped' : (s.get('joinNudge.sms') || 'none') } }, { merge: true });
      await event('stop', s.id, s.data());
      return done('Done.', `No more of these emails. You’ll still hear from ${str(s.get('vendorName')) || 'your vendor'} about your booking, and your booking page keeps working.`);
    } catch (e) { console.error('joinStop', e); return done('Something went wrong', 'Try the link again in a minute.'); }
  });

  // ========================================================= CLAIMING ==
  // Her thread moves into her Lazo account ONLY when the account's VERIFIED
  // email is the one her vendor has for her (inquiries.contact.email, compared
  // trimmed and lowercased). The join link's ref=lead:<inquiry>.<token> only
  // says WHICH thread she came for; it proves nothing on its own.
  //   verified + same email     -> claimed (Google sign-in counts as verified)
  //   same email, not verified  -> a "confirm your email" link from Lazo; the
  //                                 link lands on joinDone, which claims
  //   different email           -> nothing moves; she is told which address to
  //   Apple private relay          use (masked: j***@gmail.com)
  // A verified email that matches still claims without the link, too.
  // Each claim records the referring vendor on users/{uid}.referredBy and the
  // step that converted her on joinNudge.
  const LEAD_REF = /^lead:([A-Za-z0-9]{10,40})\.([A-Za-z0-9_-]{16,64})$/;
  const norm = (e) => str(e).trim().toLowerCase();
  const isRelay = (e) => /@privaterelay\.appleid\.com$/.test(norm(e));
  const mask = (e) => { const [u, d] = norm(e).split('@'); return u && d ? `${u[0]}***@${d}` : ''; };
  const asked = (inq, kind, uid) => !!(inq.joinNudge && inq.joinNudge.asked && inq.joinNudge.asked[`${kind}_${uid}`]);

  async function threadFor(inquiryId, t) {
    if (!inquiryId || !t) return null;
    const s = await db().collection('inquiries').doc(str(inquiryId).slice(0, 80)).get();
    return s.exists && tokenOk(str(s.get('fileToken')), str(t)) ? s : null;
  }

  async function claimOne(s, coupleUid, uid, u, via, step, medium) {
    const was = str(s.get('coupleUid'));
    if (!was.startsWith('lead_') || s.get('offPlatform') !== true) return false;
    await s.ref.set({ coupleUid, offPlatform: false, claimedFromLead: was, leadClaimedAt: FieldValue.serverTimestamp(), joinNudge: { claimedAt: FieldValue.serverTimestamp(), claimedVia: via, claimedStep: step || '', nextAt: null, pendingOpen: false } }, { merge: true });
    const subs = await Promise.all(['contracts', 'invoices'].map((c) => s.ref.collection(c).where('coupleUid', '==', was).get()));
    const batch = db().batch(); let k = 0;
    subs.forEach((ss) => ss.forEach((x) => { batch.set(x.ref, { coupleUid }, { merge: true }); k++; }));
    if (k) await batch.commit();
    await s.ref.collection('messages').add({ senderRole: 'couple', system: true, text: `${str(s.get('coupleName')) || 'Your client'} joined Lazo - this thread is in their app now.`, at: FieldValue.serverTimestamp() });
    if (!u.referredBy) {
      u.referredBy = { vendorId: str(s.get('vendorId')), vendorName: str(s.get('vendorName')), inquiryId: s.id, via, step: step || '', medium: medium || '', at: FieldValue.serverTimestamp() };
      await db().collection('users').doc(uid).set({ referredBy: u.referredBy }, { merge: true });
    }
    await event('claim', s.id, s.data(), { uid, via, step: step || '', medium: medium || '' });
    return true;
  }

  // same email, not verified yet: remember who is waiting; send Lazo's own confirm
  // link only while the signup code (verify.js) isn't live, and once per account per day
  async function askVerify(s, au) {
    const inq = s.data();
    await s.ref.set({ joinNudge: { pending: { [au.uid]: FieldValue.serverTimestamp() }, pendingOpen: true } }, { merge: true });
    if (codeVerifyLive()) return;   // the code screen proves the email; verifyEmailCode calls claimLeadThreads
    const last = inq.joinNudge && inq.joinNudge.asked && inq.joinNudge.asked[`verify_${au.uid}`];
    if (last && typeof last.toMillis === 'function' && Date.now() - last.toMillis() < 86400e3) return;
    await s.ref.set({ joinNudge: { asked: { [`verify_${au.uid}`]: FieldValue.serverTimestamp() } } }, { merge: true });
    const done = `https://meetlazo.com/join/${encodeURIComponent(s.id)}/done?t=${encodeURIComponent(str(inq.fileToken))}`;
    let link;
    // continueUrl needs meetlazo.com on Firebase Auth's authorized domains; without it the
    // plain link still verifies and joinSweep / the next sign-in finishes the claim
    try { link = await admin.auth().generateEmailVerificationLink(au.email, { url: done }); }
    catch (e) { console.warn('verify link with continueUrl', e.message); link = await admin.auth().generateEmailVerificationLink(au.email); }
    await sendEmail(au.email, C.verifyEmail(s.id, inq, await vendorOf(inq), link));
    await event('verify-sent', s.id, inq, { uid: au.uid });
  }

  // a different address (or an Apple private relay): nothing moves, say which address
  async function tellWrong(s, au, kind) {
    const inq = s.data();
    await s.ref.set({ joinNudge: { mismatch: { [au.uid]: { kind, at: FieldValue.serverTimestamp() } } } }, { merge: true });
    await event(kind, s.id, inq, { uid: au.uid });
    if (asked(inq, kind, au.uid) || !emailOk(au.email)) return;
    await s.ref.set({ joinNudge: { asked: { [`${kind}_${au.uid}`]: FieldValue.serverTimestamp() } } }, { merge: true });
    await sendEmail(au.email, C.wrongEmail(s.id, inq, await vendorOf(inq), mask(inq.contact && inq.contact.email), kind === 'relay'));
  }

  // -> { claimed, status: claimed | verify | mismatch | relay | none, masked, vendorName }
  async function claimLeadThreads(uid, opt) {
    const us = await db().collection('users').doc(uid).get();
    const u = us.exists ? { ...us.data() } : {};
    const out = { claimed: 0, status: 'none', masked: '', vendorName: '' };
    if (str(u.role) === 'vendor' || str(u.vendorId)) return out;
    const coupleUid = str(u.coupleUid) || uid;   // a partner joins the shared plan
    let au = null; try { au = await admin.auth().getUser(uid); } catch (e) { return out; }
    const have = norm(au.email), verified = au.emailVerified === true;
    const src = u.signupSource && typeof u.signupSource === 'object' ? u.signupSource : {};
    const m = opt && opt.inquiryId ? [null, opt.inquiryId, opt.t] : LEAD_REF.exec(str(src.ref));
    const step = str((opt && opt.step) || src.utm_content), medium = str((opt && opt.medium) || src.utm_medium);
    // 1. the thread she came for
    const s = m ? await threadFor(m[1], m[2]) : null;
    if (s && open(s.data())) {
      const want = norm(s.get('contact.email'));
      out.masked = mask(want); out.vendorName = str(s.get('vendorName'));
      if (want && have === want && verified) {
        if (await claimOne(s, coupleUid, uid, u, 'join-link', step, medium)) out.claimed++;
        out.status = 'claimed';
      } else if (want && have === want) {
        out.status = 'verify';
        await askVerify(s, au);
      } else {
        out.status = isRelay(have) ? 'relay' : 'mismatch';
        await tellWrong(s, au, out.status);
      }
    }
    // 2. any other thread with her verified email
    if (verified && emailOk(have)) {
      const q = await db().collection('inquiries').where('contact.email', '==', have).where('offPlatform', '==', true).get();
      for (const x of q.docs) if (await claimOne(x, coupleUid, uid, u, 'email-match', '', '')) { out.claimed++; out.status = 'claimed'; }
    }
    if (out.claimed) console.log('claimLeadThreads', uid, out.claimed);
    return out;
  }

  // she confirmed her email (verify link) -> claim for whichever pending account now qualifies
  async function finishPending(s) {
    const inq = s.data(), want = norm(inq.contact && inq.contact.email);
    if (!open(inq)) { await s.ref.set({ joinNudge: { pendingOpen: false } }, { merge: true }); return 'joined'; }
    for (const uid of Object.keys((inq.joinNudge && inq.joinNudge.pending) || {})) {
      let au = null; try { au = await admin.auth().getUser(uid); } catch (e) { continue; }
      if (au.emailVerified !== true || norm(au.email) !== want) continue;
      const us = await db().collection('users').doc(uid).get();
      const u = us.exists ? { ...us.data() } : {};
      const src = u.signupSource || {};
      if (await claimOne(s, str(u.coupleUid) || uid, uid, u, 'join-link', str(src.utm_content), str(src.utm_medium))) return 'claimed';
    }
    return 'waiting';
  }

  const onUserClaimLeads = onDocumentWritten({ document: 'users/{uid}', memory: '256MiB', secrets: [RESEND_API_KEY] }, async (event) => {
    const after = event.data && event.data.after && event.data.after.exists ? event.data.after.data() : null;
    if (!after) return;
    const before = event.data.before && event.data.before.exists ? event.data.before.data() : {};
    const ref = (d) => str(d && d.signupSource && d.signupSource.ref);
    // one try per signup, not per profile edit: when the email first appears or
    // changes, or when a join link's ref lands (FlutterFlow can write the doc first)
    const newEmail = emailOk(after.email) && norm(before.email) !== norm(after.email);
    const newRef = ref(after).startsWith('lead:') && ref(after) !== ref(before);
    if (!newEmail && !newRef) return;
    try { await claimLeadThreads(event.params.uid); } catch (e) { console.warn('onUserClaimLeads', e.message); }
  });

  // the app, after sign-in or sign-up from a join link: {inquiryId?, t?, step?}
  const claimMyLeadThreads = onCall({ memory: '256MiB', secrets: [RESEND_API_KEY] }, async (request) => {
    const uid = request.auth && request.auth.uid;
    if (!uid) throw new HttpsError('unauthenticated', 'Sign in first.');
    const d = request.data || {};
    return claimLeadThreads(uid, d.inquiryId ? { inquiryId: str(d.inquiryId), t: str(d.t), step: str(d.step), medium: 'app' } : null);
  });

  // the signup screen asks which email to pre-fill and lock: {inquiryId, t}
  const joinInfo = onCall({ memory: '256MiB' }, async (request) => {
    const d = request.data || {};
    const s = await threadFor(str(d.inquiryId), str(d.t));
    if (!s || !open(s.data())) return { open: false };
    const email = norm(s.get('contact.email'));
    return { open: true, email, masked: mask(email), vendorName: str(s.get('vendorName')) || 'your vendor' };
  });

  // GET ?i=&t=   where the confirm link lands (meetlazo.com/join/{inquiry}/done)
  const joinDone = onRequest({ invoker: 'public', memory: '256MiB' }, async (req, res) => {
    try {
      const s = await threadFor(str(req.query.i), str(req.query.t));
      if (!s) return res.redirect(302, APP);
      const r = await finishPending(s);
      if (r !== 'waiting') return res.redirect(302, APP);
      return res.set('content-type', 'text/html; charset=utf-8').set('cache-control', 'no-store').send(page('Not confirmed yet', `Tap <b>Confirm my email</b> in the email from Lazo, then come back to this link. Your booking with ${str(s.get('vendorName')) || 'your vendor'} moves in as soon as your email is confirmed.`));
    } catch (e) { console.error('joinDone', e); res.redirect(302, APP); }
  });

  // hourly: the due follow-up email and the one pending text, daytime only
  const joinSweep = onSchedule({ schedule: 'every 60 minutes', timeZone: 'America/Phoenix', memory: '256MiB', timeoutSeconds: 300, secrets: [RESEND_API_KEY, TELNYX_API_KEY, TELNYX_FROM] }, async () => {
    const now = new Date();
    const hr = phoenixHour(now);
    if ((hr < 9 || hr >= 20) && process.env.FUNCTIONS_EMULATOR !== 'true') return;   // the emulator and tests run any hour
    let mailed = 0, texted = 0, closed = 0;
    const due = await db().collection('inquiries').where('joinNudge.nextAt', '<=', Timestamp.fromDate(now)).limit(200).get();
    for (const s of due.docs) {
      const inq = s.data(), jn = inq.joinNudge || {}, step = str(jn.next);
      const to = str(inq.contact && inq.contact.email).trim();
      if (!open(inq) || jn.stopped === true || !C.STEPS[step] || !emailOk(to) || !str(inq.fileToken)) {
        await s.ref.set({ joinNudge: { nextAt: null } }, { merge: true }); closed++; continue;
      }
      // claim the step first so an overlapping run never sends it twice
      const nx = C.NEXT[step];
      const won = await db().runTransaction(async (tx) => {
        const cur = await tx.get(s.ref); const j = cur.get('joinNudge') || {};
        if (str(j.next) !== step || (j.sent && j.sent[step])) return false;
        tx.set(s.ref, { joinNudge: { sent: { [step]: FieldValue.serverTimestamp() }, next: nx ? nx[0] : null, nextAt: nx ? Timestamp.fromDate(new Date(now.getTime() + nx[1] * 86400e3)) : null } }, { merge: true });
        return true;
      });
      if (!won) continue;
      try {
        await sendEmail(to, C.STEPS[step](s.id, inq, await vendorOf(inq)));
        await event('send', s.id, inq, { step });
        mailed++;
      } catch (e) { console.warn('joinSweep mail', s.id, step, e.message); }
    }
    const texts = await db().collection('inquiries').where('joinNudge.sms', '==', 'pending').limit(100).get();
    for (const s of texts.docs) {
      const inq = s.data(), c = inq.contact || {};
      const ok = open(inq) && !(inq.joinNudge && inq.joinNudge.stopped) && c.smsOk === true && e164(c.phone);
      await s.ref.set({ joinNudge: { sms: ok ? 'sent' : 'none', smsAt: FieldValue.serverTimestamp() } }, { merge: true });
      if (!ok) continue;
      if (await sendSms(c.phone, C.sms(s.id, inq, await vendorOf(inq)))) { texted++; await event('send', s.id, inq, { step: 'sms' }); }
    }
    // she confirmed her email somewhere other than our link: finish those claims
    let finished = 0;
    const pend = await db().collection('inquiries').where('joinNudge.pendingOpen', '==', true).limit(100).get();
    for (const s of pend.docs) { try { if (await finishPending(s) === 'claimed') finished++; } catch (e) { console.warn('joinSweep pending', s.id, e.message); } }
    console.log(`joinSweep: ${mailed} emails, ${texted} texts, ${closed} closed, ${finished} claims finished`);
  });

  const out = { joinGo, joinStop, joinSweep, joinDone, joinInfo, onUserClaimLeads, claimMyLeadThreads };
  // not enumerable: Object.assign(exports, ...) in index.js never sees it as a function to deploy
  Object.defineProperty(out, 'claimLeadThreads', { value: claimLeadThreads, enumerable: false });
  return out;
};

// For verify.js: call after verifyEmailCode sets emailVerified true.
//   const { claimLeadThreads } = require('./join');
//   const r = await claimLeadThreads(uid);              // or (uid, { inquiryId, t, step })
//   -> { claimed, status: claimed | verify | mismatch | relay | none, masked, vendorName }
// It moves her thread only if the verified email matches inquiries.contact.email. The
// calling function must list RESEND_API_KEY in its secrets (mismatch / relay emails).
let _claim = null;
module.exports.claimLeadThreads = (uid, opt) => {
  if (!_claim) _claim = module.exports(defineSecret('RESEND_API_KEY')).claimLeadThreads;
  return _claim(uid, opt);
};

// END OF FILE - JC-LAZO-FNDASH-1016-JOIN-001
