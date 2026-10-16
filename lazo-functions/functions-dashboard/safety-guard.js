// functions-dashboard/safety-guard.js
// Build ID: JC-LAZO-SAFETY-1016-006 (006: callRequest for the nudge's button; the first message also counts from inquiries.message, where the Couple app keeps it; base 003)
//
// HOLD "LET'S GET ON A ZOOM CALL" BEFORE ANYONE SEES IT.
//
// Couple messages used to be written straight from the app into
// inquiries/{id}/messages. The vendor's inbox reads that collection live, so a
// trigger that checks a message afterwards is always too late: the vendor has
// already seen it. These callables check FIRST and only then write.
//
//   sendThreadMessage  callable {inquiryId, text, attachment?, confirm?}
//       couple: scan -> held (never written, nudge returned) or delivered.
//               A held strong hit is a strike; strikes can block the account.
//       vendor: never filtered. An outside-call link returns {warn} first;
//               resend with confirm:true to send anyway (logged).
//   safetyPrecheck     callable {text, vendorId, inquiryId?}
//       The same check for the FIRST message, before the app creates a new
//       inquiry (structuredIntent.message). Returns the verdict; the app only
//       creates the thread when it is not held.
//   safetyReview       callable (admins) {action, uid?, holdId?}
//       'unblock' an account, 'release' a held message into its thread,
//       'dismiss' a hold. The God Mode review list reads safetyHolds and
//       safetyBlocks (admins already read everything).
//   safetyDigest       daily 7:00 Phoenix: last 24h of holds, blocks and vendor
//       warnings to support@.
//
// The pattern and Jesse's thresholds live in offplatform.js. firestore.rules
// carries the floor for old app versions that still write directly.
//
// Collections (server-only writes):
//   safetyHolds/{id}  = { uid, role, inquiryId, vendorId, text, level, matches,
//                         reason, strike, first, early, accountAgeDays,
//                         status 'held'|'released'|'dismissed'|'warned', createdAt }
//   safetyBlocks/{uid} = { uid, coupleUid, reason, rule, holdIds, threads,
//                         status 'blocked'|'cleared', createdAt, clearedAt, clearedBy }
//   users/{uid}.safetyBlock = { at, reason }    (rules + callables refuse writes)
//   inquiries/{id}.coupleSafetyBlocked = true   (inbox shows the thread closed)

'use strict';

const { onCall, HttpsError } = require('firebase-functions/v2/https');
const { onSchedule } = require('firebase-functions/v2/scheduler');
const admin = require('firebase-admin');
const OP = require('./offplatform');

const db = () => admin.firestore();
const FROM = 'Lazo <hello@meetlazo.com>';
const ALERT_TO = 'support@meetlazo.com';
const str = (v) => (v == null ? '' : String(v));
const clip = (s, n) => str(s).slice(0, n);
const CALL_REQUEST_TEXT = 'We’d love a Lazo video call to talk it through. What times work for you?';
const toMs = (v) => (v && typeof v.toMillis === 'function') ? v.toMillis() : (v instanceof Date ? v.getTime() : 0);

module.exports = function safetyGuardModule(RESEND_API_KEY) {
  const FV = () => admin.firestore.FieldValue;

  async function mail(subject, text) {
    try {
      const key = RESEND_API_KEY.value();
      if (!key) return;
      await fetch('https://api.resend.com/emails', {
        method: 'POST',
        headers: { 'content-type': 'application/json', authorization: `Bearer ${key}` },
        body: JSON.stringify({ from: FROM, to: [ALERT_TO], subject, text }),
      });
    } catch (e) { console.warn('[safety-guard] mail', e.message); }
  }

  // ------------------------------------------------------------ who ----
  async function userDoc(uid) {
    const s = await db().collection('users').doc(uid).get();
    return s.exists ? (s.data() || {}) : {};
  }
  async function vendorRoleFor(uid, vendorId, u) {
    if (!vendorId) return false;
    const v = await db().collection('vendors').doc(vendorId).get();
    if (v.exists && str(v.get('claimedBy')) === uid) return true;
    return str(u.vendorId) === vendorId && str(u.vendorRole) === 'manager';
  }
  // 'couple' | 'vendor' | null for this caller on this thread
  async function roleOn(inq, uid, u) {
    const cuid = str(inq.coupleUid);
    if (cuid && (cuid === uid || str(u.coupleUid) === cuid)) return 'couple';
    if (await vendorRoleFor(uid, str(inq.vendorId), u)) return 'vendor';
    return null;
  }
  // Firebase Auth's creation time, never users.created_time: the app writes
  // that one at signup, so a scammer could backdate it.
  async function accountAgeDays(uid) {
    let ms = 0;
    try { ms = Date.parse((await admin.auth().getUser(uid)).metadata.creationTime) || 0; } catch (e) { ms = 0; }
    return ms ? (Date.now() - ms) / 86400000 : 0;   // unknown age counts as new
  }
  function underReview() {
    return new HttpsError('permission-denied', OP.NUDGE.review, { code: 'account-under-review', nudge: OP.NUDGE.review });
  }

  // couple messages already in the thread, counting the inquiry's own first
  // message when there is one: the Couple app keeps it in inquiries.message,
  // website and booking leads in structuredIntent.message
  async function coupleMessageCount(inqRef, inq) {
    const q = await inqRef.collection('messages').where('senderRole', '==', 'couple').limit(OP.EARLY_MESSAGES + 1).get();
    const real = q.docs.filter((d) => d.get('system') !== true).length;
    const intent = inq && (str(inq.message).trim() || (inq.structuredIntent && str(inq.structuredIntent.message).trim())) ? 1 : 0;
    return real + intent;
  }

  // ------------------------------------------------------ hold + block ----
  async function recordHold(uid, u, { inquiryId, vendorId, text, v, first, early, role, status }) {
    const age = await accountAgeDays(uid);
    const ref = await db().collection('safetyHolds').add({
      uid, role, inquiryId: inquiryId || '', vendorId: vendorId || '', text: clip(text, 2000),
      level: v.level, matches: [...v.strong, ...v.weak, ...v.contact].slice(0, 10), reason: v.reason || (v.level ? 'video' : ''),
      strike: !!v.strike, first: !!first, early: !!early, accountAgeDays: Math.round(age * 10) / 10,
      status: status || 'held', createdAt: FV().serverTimestamp(),
    });
    return { id: ref.id, age };
  }

  // Jesse 2026-10-16: (a) strong in the first message from an account under 7
  // days old, (b) a second strong hit within 30 days, (c) strong hits to 2+
  // vendors within 24 hours.
  async function blockRule(uid, { first, age, vendorId }) {
    if (first && age < OP.NEW_ACCOUNT_DAYS) return 'a: outside call in the first message, new account';
    const since = Date.now() - OP.STRIKE_WINDOW_DAYS * 86400000;
    const q = await db().collection('safetyHolds').where('uid', '==', uid).limit(200).get();
    const strikes = q.docs.map((d) => d.data()).filter((h) => h.strike && h.status !== 'dismissed' && (toMs(h.createdAt) || Date.now()) >= since);
    if (strikes.length >= 2) return `b: ${strikes.length} outside-call attempts in ${OP.STRIKE_WINDOW_DAYS} days`;
    const daySince = Date.now() - OP.SPRAY_WINDOW_HOURS * 3600000;
    const vendors = new Set(strikes.filter((h) => (toMs(h.createdAt) || Date.now()) >= daySince).map((h) => h.vendorId).filter(Boolean));
    if (vendorId) vendors.add(vendorId);
    if (vendors.size >= OP.SPRAY_VENDORS) return `c: outside-call attempts to ${vendors.size} vendors in ${OP.SPRAY_WINDOW_HOURS} hours`;
    return null;
  }

  async function blockCoupleAccount(uid, u, rule, holdIds, by) {
    const cuid = str(u.coupleUid) || uid;
    const now = FV().serverTimestamp();
    await db().collection('users').doc(uid).set({ safetyBlock: { at: now, reason: rule, by: by || 'auto' } }, { merge: true });
    const threads = await db().collection('inquiries').where('coupleUid', '==', cuid).limit(200).get();
    const vendors = new Set();
    for (const t of threads.docs) {
      vendors.add(str(t.get('vendorId')));
      await t.ref.set({ coupleSafetyBlocked: true, coupleSafetyBlockedAt: now }, { merge: true });
      await t.ref.collection('messages').add({ senderRole: 'system', system: true, safety: true, text: OP.VENDOR_BLOCK_NOTICE, at: now });
    }
    await db().collection('safetyBlocks').doc(uid).set({
      uid, coupleUid: cuid, email: str(u.email), reason: rule, rule: rule.slice(0, 1), holdIds: holdIds || [],
      threads: threads.docs.map((d) => d.id), vendors: [...vendors].filter(Boolean),
      status: 'blocked', by: by || 'auto', createdAt: now,
    }, { merge: true });
    await mail(`[lazo/safety] blocked ${str(u.email) || uid} - ${rule}`,
      `Account: ${uid} (${str(u.email) || 'no email'})\nRule:    ${rule}\nThreads: ${threads.size}, vendors told: ${vendors.size}\nHolds:   ${(holdIds || []).join(', ')}\n\nUnblock from God Mode > Safety (safetyReview unblock) if this is a real couple.`);
    console.log(`[safety-guard] blocked ${uid}: ${rule}`);
  }

  // shared by sendThreadMessage and safetyPrecheck for a couple's text
  async function judgeCouple(uid, u, { text, inquiryId, vendorId, priorCount }) {
    const early = priorCount < OP.EARLY_MESSAGES;
    const first = priorCount === 0;
    const v = OP.verdict(text, { early });
    if (!v.hold) return { held: false, v };
    const h = await recordHold(uid, u, { inquiryId, vendorId, text, v, first, early, role: 'couple' });
    let blocked = false;
    if (v.strike) {
      const rule = await blockRule(uid, { first, age: h.age, vendorId });
      if (rule) { await blockCoupleAccount(uid, u, rule, [h.id]); blocked = true; }
    }
    return { held: true, v, holdId: h.id, blocked };
  }
  function heldReply(j) {
    if (j.blocked) return { ok: false, held: true, blocked: true, reason: 'review', nudge: OP.NUDGE.review };
    return { ok: false, held: true, blocked: false, reason: j.v.reason, nudge: OP.NUDGE[j.v.reason] || OP.NUDGE.video, action: j.v.reason === 'video' ? 'request_lazo_call' : null };
  }

  function cleanAttachment(a) {
    if (!a || typeof a !== 'object') return null;
    const out = {};
    for (const k of ['url', 'name', 'type', 'path', 'title']) if (a[k] != null) out[k] = clip(a[k], 1000);
    if (typeof a.size === 'number') out.size = a.size;
    if (out.url && !/^https:\/\//.test(out.url)) return null;
    return Object.keys(out).length ? out : null;
  }

  // ------------------------------------------------- sendThreadMessage ----
  const sendThreadMessage = onCall({ memory: '256MiB', secrets: [RESEND_API_KEY] }, async (request) => {
    const uid = request.auth && request.auth.uid;
    if (!uid) throw new HttpsError('unauthenticated', 'Sign in first.');
    const d = request.data || {};
    const inquiryId = clip(d.inquiryId, 80);
    // callRequest: the nudge's "Request a Lazo video call" button. A fixed
    // text, so it is never held, and a flag the vendor app turns into a reply chip.
    const callRequest = d.callRequest === true;
    const text = callRequest ? CALL_REQUEST_TEXT : clip(d.text, 2999).trim();
    const attachment = callRequest ? null : cleanAttachment(d.attachment);
    if (!inquiryId) throw new HttpsError('invalid-argument', 'inquiryId required.');
    if (!text && !attachment) throw new HttpsError('invalid-argument', 'Empty message.');

    const inqRef = db().collection('inquiries').doc(inquiryId);
    const is = await inqRef.get();
    if (!is.exists) throw new HttpsError('not-found', 'Conversation not found.');
    const inq = is.data() || {};
    const u = await userDoc(uid);
    const role = await roleOn(inq, uid, u);
    if (!role) throw new HttpsError('permission-denied', 'Not your conversation.');
    if (callRequest && role !== 'couple') throw new HttpsError('invalid-argument', 'Only the couple requests a call.');

    if (role === 'couple') {
      if (u.safetyBlock) throw underReview();
      if (inq.blockedByVendor === true) throw new HttpsError('failed-precondition', 'This conversation is closed.');
      if (text && !callRequest) {
        const j = await judgeCouple(uid, u, { text, inquiryId, vendorId: str(inq.vendorId), priorCount: await coupleMessageCount(inqRef, inq) });
        if (j.held) return heldReply(j);
      }
    } else {
      if (inq.blockedByCouple === true) throw new HttpsError('failed-precondition', 'This couple has closed the conversation.');
      const s = OP.scan(text);
      if (s.level === 'strong' || s.level === 'weak') {
        if (d.confirm !== true) return { ok: false, warn: true, warning: OP.VENDOR_WARNING, action: 'start_lazo_call' };
        await recordHold(uid, u, { inquiryId, vendorId: str(inq.vendorId), text, v: { ...s, reason: 'video', strike: false }, first: false, early: false, role: 'vendor', status: 'warned' });
      }
    }

    const msg = { senderRole: role, text, at: FV().serverTimestamp() };
    if (attachment) msg.attachment = attachment;
    if (callRequest) msg.callRequest = true;
    const ref = await inqRef.collection('messages').add(msg);
    return { ok: true, id: ref.id };
  });

  // ---------------------------------------------------- safetyPrecheck ----
  const safetyPrecheck = onCall({ memory: '256MiB', secrets: [RESEND_API_KEY] }, async (request) => {
    const uid = request.auth && request.auth.uid;
    if (!uid) throw new HttpsError('unauthenticated', 'Sign in first.');
    const d = request.data || {};
    const text = clip(d.text, 2999).trim();
    const vendorId = clip(d.vendorId, 120);
    const inquiryId = clip(d.inquiryId, 80);
    const u = await userDoc(uid);
    if (str(d.role) === 'vendor') {
      const s = OP.scan(text);
      const warn = s.level === 'strong' || s.level === 'weak';
      return { ok: true, warn, warning: warn ? OP.VENDOR_WARNING : null, action: warn ? 'start_lazo_call' : null };
    }
    if (u.safetyBlock) return { ok: false, held: true, blocked: true, reason: 'review', nudge: OP.NUDGE.review };
    if (!text) return { ok: true, held: false };
    let priorCount = 0;
    if (inquiryId) {
      const s = await db().collection('inquiries').doc(inquiryId).get();
      if (s.exists && (await roleOn(s.data() || {}, uid, u)) === 'couple') priorCount = await coupleMessageCount(s.ref, s.data());
    }
    const j = await judgeCouple(uid, u, { text, inquiryId, vendorId, priorCount });
    return j.held ? heldReply(j) : { ok: true, held: false };
  });

  // ------------------------------------------------------ safetyReview ----
  async function assertAdmin(request) {
    const uid = request.auth && request.auth.uid;
    if (!uid) throw new HttpsError('unauthenticated', 'Sign in first.');
    if (request.auth.token && request.auth.token.admin === true) return uid;
    const a = await db().collection('admins').doc(uid).get();
    if (!a.exists) throw new HttpsError('permission-denied', 'Admins only.');
    return uid;
  }
  const safetyReview = onCall({ memory: '256MiB' }, async (request) => {
    const by = await assertAdmin(request);
    const d = request.data || {};
    const action = str(d.action);
    const now = FV().serverTimestamp();
    if (action === 'unblock') {
      const uid = clip(d.uid, 128);
      if (!uid) throw new HttpsError('invalid-argument', 'uid required.');
      const u = await userDoc(uid);
      const cuid = str(u.coupleUid) || uid;
      await db().collection('users').doc(uid).set({ safetyBlock: FV().delete() }, { merge: true });
      const threads = await db().collection('inquiries').where('coupleUid', '==', cuid).limit(200).get();
      for (const t of threads.docs) await t.ref.set({ coupleSafetyBlocked: FV().delete(), coupleSafetyBlockedAt: FV().delete() }, { merge: true });
      await db().collection('safetyBlocks').doc(uid).set({ status: 'cleared', clearedAt: now, clearedBy: by }, { merge: true });
      return { ok: true, threads: threads.size };
    }
    if (action === 'release' || action === 'dismiss') {
      const ref = db().collection('safetyHolds').doc(clip(d.holdId, 80));
      const s = await ref.get();
      if (!s.exists) throw new HttpsError('not-found', 'Hold not found.');
      const h = s.data();
      if (action === 'release') {
        if (h.role !== 'couple' || !h.inquiryId) throw new HttpsError('failed-precondition', 'Only a couple message held in a thread can be released.');
        if (h.status === 'released') return { ok: true, already: true };
        await db().collection('inquiries').doc(h.inquiryId).collection('messages').add({ senderRole: 'couple', text: str(h.text), at: now, releasedHoldId: s.id });
      }
      await ref.set({ status: action === 'release' ? 'released' : 'dismissed', reviewedAt: now, reviewedBy: by }, { merge: true });
      return { ok: true };
    }
    throw new HttpsError('invalid-argument', 'action must be unblock, release or dismiss.');
  });

  // ------------------------------------------------------ safetyDigest ----
  const safetyDigest = onSchedule({ schedule: '0 7 * * *', timeZone: 'America/Phoenix', memory: '256MiB', secrets: [RESEND_API_KEY] }, async () => {
    const since = admin.firestore.Timestamp.fromMillis(Date.now() - 86400000);
    const holds = await db().collection('safetyHolds').where('createdAt', '>=', since).limit(500).get();
    const blocks = await db().collection('safetyBlocks').where('createdAt', '>=', since).limit(200).get();
    if (holds.empty && blocks.empty) { console.log('safetyDigest: nothing'); return; }
    const rows = holds.docs.map((x) => x.data());
    const line = (h) => `- [${h.role}/${h.level}${h.strike ? '/strike' : ''}${h.first ? '/first' : ''}] ${h.uid} -> vendor ${h.vendorId || '?'} (${h.accountAgeDays}d old): ${clip(str(h.text).replace(/\s+/g, ' '), 140)}`;
    const text = [
      `Last 24 hours: ${blocks.size} blocked, ${rows.filter((h) => h.role === 'couple').length} couple messages held, ${rows.filter((h) => h.role === 'vendor').length} vendor warnings sent anyway.`, '',
      blocks.size ? 'BLOCKED' : '', ...blocks.docs.map((b) => `- ${b.id} (${str(b.get('email'))}): ${str(b.get('reason'))}, ${(b.get('vendors') || []).length} vendors told`), '',
      'HELD / WARNED', ...rows.map(line), '',
      'Review in God Mode > Safety (safetyHolds, safetyBlocks). Unblock, release or dismiss with safetyReview.',
    ].join('\n');
    await mail(`[lazo/safety] daily: ${blocks.size} blocked, ${rows.length} held/warned`, text);
  });

  return { sendThreadMessage, safetyPrecheck, safetyReview, safetyDigest };
};

// END OF FILE - JC-LAZO-SAFETY-1016-003
