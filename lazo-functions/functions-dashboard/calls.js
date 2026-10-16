// functions-dashboard/calls.js
// Build ID: JC-LAZO-CALLS-1016-002 (002: audio-only preference on join; base 001)
//
// LAZO VIDEO CALLS, PHASE 1 - the Firebase half.
//
// Consults stay inside Lazo instead of going out to Zoom / FaceTime / Meet
// links, and the call itself is built against the sextortion scam hitting
// wedding vendors (a fake couple plays porn on camera, screenshots the call,
// demands money):
//   - only the thread's own vendor and couple can join, with a short-lived
//     token minted here and checked by the worker;
//   - couples confirm a phone number by text code before their first video
//     call; accounts without a Lazo login (website / booking leads) get no
//     video at all;
//   - the couple's camera stays locked until the vendor allows it - enforced
//     by the worker, which refuses the couple's video track until then;
//   - every join, leave and camera on/off is logged server side in calls/{id}
//     (the worker reports it here), so a vendor who is extorted has a record.
//
// The media goes through Cloudflare Realtime (SFU) via the lazo-site worker
// (lazo-directory/worker/src/rt.js, Durable Object CallRoom). The worker and
// these functions share CALL_TOKEN_SECRET (HMAC-SHA256).
//
//   callJoin      callable {inquiryId} -> {callId, token, role, myName, otherName, workerBase}
//                 or {needPhone:true} for a couple without a verified phone.
//   callEvent     POST from the worker, body signed (x-lazo-sig): appends to calls/{id}.
//   phoneStart    callable {phone}  -> texts a 6-digit code (Telnyx)
//   phoneConfirm  callable {code}   -> users/{uid}.phoneVerified / phoneVerifiedAt (server-only)
//
// calls/{callId} = { inquiryId, vendorId, coupleUid, vendorName, coupleName,
//   status 'open'|'ended', createdAt, createdBy, startedByRole, endedAt,
//   events:[{type, role, uid, at, detail}], lastEventAt }

'use strict';

const crypto = require('crypto');
const { onCall, onRequest, HttpsError } = require('firebase-functions/v2/https');
const { defineSecret } = require('firebase-functions/params');
const admin = require('firebase-admin');

const CALL_TOKEN_SECRET = defineSecret('CALL_TOKEN_SECRET');
const TELNYX_API_KEY = defineSecret('TELNYX_API_KEY');
const TELNYX_FROM = defineSecret('TELNYX_FROM');

const WORKER_BASE = 'https://meetlazo.com';
const TOKEN_MINUTES = 10;
const CALL_REUSE_HOURS = 3;          // an open call on the thread is rejoined within this window
const MAX_EVENTS = 400;
const CODE_MINUTES = 10;
const CODE_TRIES = 5;
const SENDS_PER_DAY = 5;
const ACCOUNTS_PER_PHONE = 3;

const db = () => admin.firestore();
const FV = () => admin.firestore.FieldValue;
const str = (v) => (v == null ? '' : String(v));
const clip = (s, n) => str(s).slice(0, n);
const toMs = (v) => (v && typeof v.toMillis === 'function') ? v.toMillis() : 0;
const e164 = (raw) => { const d = str(raw).replace(/[^\d]/g, ''); return d.length === 10 ? '+1' + d : (d.length === 11 && d.startsWith('1')) ? '+' + d : ''; };
const b64u = (buf) => Buffer.from(buf).toString('base64url');

// token = base64url(JSON payload) + '.' + base64url(HMAC-SHA256(payload part))
function signToken(payload, secret) {
  const body = b64u(JSON.stringify(payload));
  const sig = b64u(crypto.createHmac('sha256', secret).update(body).digest());
  return `${body}.${sig}`;
}
function verifySig(raw, sig, secret) {
  const want = crypto.createHmac('sha256', secret).update(raw).digest('hex');
  const a = Buffer.from(want), b = Buffer.from(str(sig));
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

module.exports = function callsModule() {

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

  // ------------------------------------------------------------ callJoin ----
  const callJoin = onCall({ memory: '256MiB', secrets: [CALL_TOKEN_SECRET] }, async (request) => {
    const uid = request.auth && request.auth.uid;
    if (!uid) throw new HttpsError('unauthenticated', 'Sign in first.');
    const inquiryId = clip((request.data || {}).inquiryId, 80);
    if (!inquiryId) throw new HttpsError('invalid-argument', 'inquiryId required.');
    const inqRef = db().collection('inquiries').doc(inquiryId);
    const is = await inqRef.get();
    if (!is.exists) throw new HttpsError('not-found', 'Conversation not found.');
    const inq = is.data() || {};
    const u = await userDoc(uid);
    const role = await roleOn(inq, uid, u);
    if (!role) throw new HttpsError('permission-denied', 'Not your conversation.');

    if (u.safetyBlock) throw new HttpsError('permission-denied', 'Your account is under review. Contact support@meetlazo.com.', { code: 'account-under-review' });
    if (inq.coupleSafetyBlocked === true) throw new HttpsError('failed-precondition', 'Lazo blocked this account for safety.', { code: 'blocked' });
    if (inq.blockedByCouple === true || inq.blockedByVendor === true) throw new HttpsError('failed-precondition', 'This conversation is closed.', { code: 'closed' });
    if (str(inq.coupleUid).startsWith('lead_') || inq.offPlatform === true) {
      // Jesse 2026-10-16: no account, no video. They can still book a phone or in-person consult.
      throw new HttpsError('failed-precondition', 'Video calls are for couples with a Lazo account. Send them your booking link for a phone call instead.', { code: 'lead-no-video' });
    }
    if (role === 'couple' && !str(u.phoneVerified)) return { ok: false, needPhone: true };

    // JC-LAZO-CALLS-1016-002: "Join with audio only" sets the couple's preference; the vendor
    // then sees "Prefers audio only" and isn't prompted to allow their camera.
    let audioOnly = inq.coupleAudioOnly === true;
    if (role === 'couple' && typeof (request.data || {}).audioOnly === 'boolean') {
      audioOnly = request.data.audioOnly === true;
      await inqRef.set({ coupleAudioOnly: audioOnly }, { merge: true });
    }

    // reuse the open call on this thread, or start one
    const now = Date.now();
    let callRef = null;
    const open = await db().collection('calls').where('inquiryId', '==', inquiryId).where('status', '==', 'open').limit(5).get();
    for (const d of open.docs) if (now - (toMs(d.get('createdAt')) || now) < CALL_REUSE_HOURS * 3600000) { callRef = d.ref; break; }
    const vendorName = str(inq.vendorName) || 'Your vendor';
    const coupleName = str(inq.coupleName) || 'The couple';
    if (!callRef) {
      callRef = db().collection('calls').doc();
      await callRef.set({
        inquiryId, vendorId: str(inq.vendorId), coupleUid: str(inq.coupleUid), vendorName, coupleName,
        status: 'open', createdAt: FV().serverTimestamp(), createdBy: uid, startedByRole: role, events: [],
      });
      // In the thread: the other side gets the push (messageArrived) and a Join chip.
      await inqRef.collection('messages').add({
        senderRole: role, system: true, callInvite: { callId: callRef.id },
        text: 'Started a Lazo video call.', at: FV().serverTimestamp(),
      });
    }
    const token = signToken({
      c: callRef.id, i: inquiryId, u: uid, r: role,
      n: role === 'vendor' ? vendorName : coupleName,
      o: role === 'vendor' ? coupleName : vendorName,
      ao: audioOnly,
      exp: now + TOKEN_MINUTES * 60000,
    }, CALL_TOKEN_SECRET.value());
    return {
      ok: true, callId: callRef.id, token, role, workerBase: WORKER_BASE,
      myName: role === 'vendor' ? vendorName : coupleName,
      otherName: role === 'vendor' ? coupleName : vendorName,
      coupleAudioOnly: audioOnly,
    };
  });

  // ----------------------------------------------------------- callEvent ----
  const callEvent = onRequest({ memory: '256MiB', invoker: 'public', secrets: [CALL_TOKEN_SECRET] }, async (req, res) => {
    if (req.method !== 'POST') return res.status(405).json({ ok: false });
    const raw = req.rawBody ? req.rawBody.toString('utf8') : JSON.stringify(req.body || {});
    if (!verifySig(raw, req.get('x-lazo-sig'), CALL_TOKEN_SECRET.value())) return res.status(403).json({ ok: false });
    let b;
    try { b = JSON.parse(raw); } catch (e) { return res.status(400).json({ ok: false }); }
    const callId = clip(b.callId, 80);
    const events = (Array.isArray(b.events) ? b.events : []).slice(0, 50).map((e) => ({
      type: clip(e.type, 30), role: clip(e.role, 10), uid: clip(e.uid, 128), at: Number(e.at) || Date.now(), detail: clip(e.detail, 200),
    }));
    if (!callId || !events.length) return res.status(400).json({ ok: false });
    const ref = db().collection('calls').doc(callId);
    const s = await ref.get();
    if (!s.exists) return res.status(404).json({ ok: false });
    const have = (s.get('events') || []).length;
    const patch = { lastEventAt: FV().serverTimestamp() };
    if (have < MAX_EVENTS) patch.events = FV().arrayUnion(...events.slice(0, MAX_EVENTS - have));
    const end = events.find((e) => e.type === 'ended');
    if (end) {
      patch.status = 'ended';
      patch.endedAt = admin.firestore.Timestamp.fromMillis(end.at);
      const started = toMs(s.get('createdAt'));
      if (started) patch.durationSec = Math.max(0, Math.round((end.at - started) / 1000));
    }
    await ref.set(patch, { merge: true });
    res.json({ ok: true });
  });

  // ---------------------------------------------------------- phoneStart ----
  async function sendSms(to, text) {
    const r = await fetch('https://api.telnyx.com/v2/messages', {
      method: 'POST', headers: { Authorization: `Bearer ${TELNYX_API_KEY.value()}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ from: TELNYX_FROM.value(), to, text }),
    });
    if (!r.ok) { console.warn('phoneStart telnyx', r.status, await r.text()); return false; }
    return true;
  }
  const hashCode = (uid, code) => crypto.createHash('sha256').update(`${uid}:${code}`).digest('hex');

  const phoneStart = onCall({ memory: '256MiB', secrets: [TELNYX_API_KEY, TELNYX_FROM] }, async (request) => {
    const uid = request.auth && request.auth.uid;
    if (!uid) throw new HttpsError('unauthenticated', 'Sign in first.');
    const phone = e164((request.data || {}).phone);
    if (!phone) throw new HttpsError('invalid-argument', 'Enter a US mobile number.', { code: 'bad-phone' });
    const u = await userDoc(uid);
    if (u.safetyBlock) throw new HttpsError('permission-denied', 'Your account is under review. Contact support@meetlazo.com.', { code: 'account-under-review' });
    const others = await db().collection('users').where('phoneVerified', '==', phone).limit(ACCOUNTS_PER_PHONE + 1).get();
    if (others.docs.filter((d) => d.id !== uid).length >= ACCOUNTS_PER_PHONE) {
      throw new HttpsError('failed-precondition', 'That number is already on too many Lazo accounts. Contact support@meetlazo.com.', { code: 'phone-in-use' });
    }
    const ref = db().collection('phoneCodes').doc(uid);
    const prev = await ref.get();
    const day = Date.now() - 86400000;
    const sends = ((prev.exists && prev.get('sends')) || []).filter((t) => t > day);
    if (sends.length >= SENDS_PER_DAY) throw new HttpsError('resource-exhausted', 'Too many codes today. Try again tomorrow.', { code: 'too-many' });
    const code = String(crypto.randomInt(0, 1000000)).padStart(6, '0');
    await ref.set({ phone, hash: hashCode(uid, code), exp: Date.now() + CODE_MINUTES * 60000, tries: 0, sends: [...sends, Date.now()] });
    const ok = await sendSms(phone, `Lazo: your code is ${code}. It expires in ${CODE_MINUTES} minutes. Don't share it with anyone.`);
    if (!ok) throw new HttpsError('unavailable', 'Could not text that number. Check it and try again.', { code: 'sms-failed' });
    return { ok: true, sentTo: phone.replace(/^(\+1)(\d{3})(\d{3})(\d{4})$/, '($2) ***-$4') };
  });

  // -------------------------------------------------------- phoneConfirm ----
  const phoneConfirm = onCall({ memory: '256MiB' }, async (request) => {
    const uid = request.auth && request.auth.uid;
    if (!uid) throw new HttpsError('unauthenticated', 'Sign in first.');
    const code = str((request.data || {}).code).replace(/\D/g, '');
    const ref = db().collection('phoneCodes').doc(uid);
    const s = await ref.get();
    if (!s.exists) throw new HttpsError('failed-precondition', 'Ask for a new code.', { code: 'no-code' });
    const c = s.data();
    if (Date.now() > c.exp) throw new HttpsError('deadline-exceeded', 'That code expired. Ask for a new one.', { code: 'expired' });
    if ((c.tries || 0) >= CODE_TRIES) throw new HttpsError('resource-exhausted', 'Too many tries. Ask for a new code.', { code: 'too-many-tries' });
    if (code.length !== 6 || hashCode(uid, code) !== c.hash) {
      await ref.set({ tries: (c.tries || 0) + 1 }, { merge: true });
      throw new HttpsError('invalid-argument', 'That code doesn’t match.', { code: 'wrong-code' });
    }
    await db().collection('users').doc(uid).set({ phoneVerified: c.phone, phoneVerifiedAt: FV().serverTimestamp() }, { merge: true });
    await ref.delete();
    return { ok: true, phone: c.phone };
  });

  return { callJoin, callEvent, phoneStart, phoneConfirm };
};

module.exports._test = { signToken, verifySig };

// END OF FILE - JC-LAZO-CALLS-1016-001
