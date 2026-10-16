// functions-dashboard/verify.js
// Build ID: JC-LAZO-FNDASH-1016-027 (027: email verification at signup - six-digit code + disposable / dead domain block)
//
// PROVE THE EMAIL IS REAL. Until now anyone could sign up with any address
// (xxy@aol.com, a password, and they were in). Now:
//
//   blockBadSignupEmail  beforeUserCreated (Identity Platform blocking function)
//                        -> refuses throwaway domains (disposable-domains.txt,
//                           the disposable-email-domains/disposable-email-domains
//                           blocklist) and domains that cannot receive mail
//                           (no MX and no A/AAAA, or a null MX). A DNS lookup
//                           that times out or errors lets the signup through:
//                           the code below still has to arrive.
//   sendEmailCode        callable {} -> { verified } | { sent, masked, retryIn }
//                        emails a six-digit code to the signed-in account's own
//                        email. 45s between sends, 6 sends an hour.
//   verifyEmailCode      callable {code, inquiryId?, t?, step?} -> { ok, left?, claim? } ;
//                        on a match the account's emailVerified is set true
//                        (Admin SDK), users/{uid}.emailVerifiedAt stamped, and
//                        join.js claimLeadThreads moves in a vendor booking whose
//                        email matches (claim = its status/masked/vendorName).
//                        15 minutes to use a code, 5 wrong tries and a fresh one
//                        is needed.
//
// emailCodes/{uid} holds only a salted hash of the code and is server-only
// (the rules' catch-all denies clients). firestore.rules requires a verified
// email (or the legacy claim on accounts that predate this - see
// scripts/mark-legacy-users.js) for everything except the user's own users doc.

'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const dns = require('dns').promises;
const { onCall, HttpsError } = require('firebase-functions/v2/https');
const identity = require('firebase-functions/v2/identity');
const admin = require('firebase-admin');
const { frame, esc } = require('./email-frame');

const FROM = 'Lazo <hello@meetlazo.com>';
const TTL_MS = 15 * 60 * 1000;
const GAP_MS = 45 * 1000;
const PER_HOUR = 6;
const MAX_TRIES = 5;

const str = (v) => (v == null ? '' : String(v));
const norm = (e) => str(e).trim().toLowerCase();
const emailOk = (e) => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(str(e).trim());
const ms = (t) => (t && typeof t.toMillis === 'function') ? t.toMillis() : (typeof t === 'number' ? t : 0);

let _blocked = null;
function blocked() {
  if (_blocked) return _blocked;
  const raw = fs.readFileSync(path.join(__dirname, 'disposable-domains.txt'), 'utf8');
  _blocked = new Set(raw.split(/\r?\n/).map((l) => l.trim().toLowerCase()).filter((l) => l && !l.startsWith('#')));
  return _blocked;
}

// a subdomain of a blocked domain is blocked too (x.mailinator.com)
function isDisposable(domain) {
  const set = blocked();
  const parts = norm(domain).split('.');
  for (let i = 0; i < parts.length - 1; i++) {
    if (set.has(parts.slice(i).join('.'))) return true;
  }
  return false;
}

function withTimeout(p, ms) {
  return Promise.race([p, new Promise((_, rej) => setTimeout(() => rej(Object.assign(new Error('timeout'), { code: 'ETIMEOUT' })), ms))]);
}

const GONE = new Set(['ENOTFOUND', 'ENODATA', 'NXDOMAIN']);

// 'ok' | 'disposable' | 'nomail' ; r is injectable for tests ({ resolveMx, resolve4, resolve6 })
async function checkDomain(email, r = dns) {
  const at = str(email).lastIndexOf('@');
  if (at < 1) return 'nomail';
  const domain = norm(email.slice(at + 1));
  if (!domain.includes('.')) return 'nomail';
  if (isDisposable(domain)) return 'disposable';
  try {
    const mx = await withTimeout(r.resolveMx(domain), 2500);
    if (Array.isArray(mx) && mx.length) {
      // RFC 7505 null MX: the domain says it takes no mail
      if (mx.length === 1 && (mx[0].exchange === '' || mx[0].exchange === '.')) return 'nomail';
      return 'ok';
    }
  } catch (e) {
    if (!GONE.has(e.code)) return 'ok'; // a DNS hiccup is not the user's fault
  }
  // no MX: mail falls back to the A / AAAA record
  for (const f of [r.resolve4, r.resolve6]) {
    try {
      const a = await withTimeout(f.call(r, domain), 2000);
      if (Array.isArray(a) && a.length) return 'ok';
    } catch (e) {
      if (!GONE.has(e.code)) return 'ok';
    }
  }
  return 'nomail';
}

const newCode = () => String(crypto.randomInt(0, 1000000)).padStart(6, '0');
const hashCode = (uid, salt, code) => crypto.createHash('sha256').update(`${uid}:${salt}:${str(code).trim()}`).digest('hex');
function sameHash(a, b) {
  const x = Buffer.from(str(a), 'hex');
  const y = Buffer.from(str(b), 'hex');
  return x.length === y.length && x.length > 0 && crypto.timingSafeEqual(x, y);
}
function mask(email) {
  const e = str(email).trim();
  const at = e.indexOf('@');
  if (at < 1) return e;
  return e[0] + '***' + e.slice(at);
}

function codeEmail(code, email) {
  const big = `<p style="margin:22px 0 6px;text-align:center;font-family:'Courier New',Courier,monospace;font-size:38px;letter-spacing:10px;font-weight:bold;color:#3D1C3B">${esc(code)}</p>
<p style="margin:0;text-align:center;font-family:Helvetica,Arial,sans-serif;font-size:13px;color:#8C8291">It works for 15 minutes.</p>`;
  return {
    subject: `${code} is your Lazo code`,
    html: frame({
      preheader: `Your Lazo code is ${code}. It works for 15 minutes.`,
      kicker: 'Confirm your email',
      title: 'Here’s your code',
      lede: 'Type this into Lazo to finish making your account.',
      body: big,
      signoff: 'Didn’t try to join Lazo? You can ignore this email; nothing happens without the code.',
      footerWhy: `You're getting this because someone used ${esc(email)} to make a Lazo account.`,
    }),
    text: `Your Lazo code is ${code}\n\nType it into Lazo to finish making your account. It works for 15 minutes.\n\nDidn't try to join Lazo? Ignore this email; nothing happens without the code.`,
  };
}

module.exports = function verifyModule(RESEND_API_KEY) {
  const db = () => admin.firestore();
  const { FieldValue, Timestamp } = admin.firestore;

  async function sendEmail(to, m) {
    const r = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { Authorization: `Bearer ${RESEND_API_KEY.value()}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ from: FROM, to: [to], subject: m.subject, html: m.html, text: m.text }),
    });
    if (!r.ok) throw new Error(`resend ${r.status}: ${(await r.text()).slice(0, 200)}`);
  }

  async function signedInUser(request) {
    const uid = request.auth && request.auth.uid;
    if (!uid) throw new HttpsError('unauthenticated', 'Sign in first.');
    const u = await admin.auth().getUser(uid);
    return u;
  }

  const sendEmailCode = onCall({ memory: '256MiB', secrets: [RESEND_API_KEY] }, async (request) => {
    const u = await signedInUser(request);
    if (u.emailVerified) return { verified: true };
    if (!emailOk(u.email)) throw new HttpsError('failed-precondition', 'This account has no email address to confirm.');
    const ref = db().collection('emailCodes').doc(u.uid);
    const now = Date.now();
    const code = newCode();
    const salt = crypto.randomBytes(12).toString('hex');
    const retryIn = await db().runTransaction(async (tx) => {
      const s = await tx.get(ref);
      const d = s.exists ? s.data() : {};
      const last = ms(d.sentAt);
      if (last && now - last < GAP_MS) return Math.ceil((GAP_MS - (now - last)) / 1000);
      const hourStart = ms(d.hourStart);
      const inHour = hourStart && now - hourStart < 3600 * 1000;
      const count = inHour ? (d.hourCount || 0) : 0;
      if (count >= PER_HOUR) return Math.ceil((3600 * 1000 - (now - hourStart)) / 1000);
      tx.set(ref, {
        uid: u.uid,
        email: norm(u.email),
        salt,
        hash: hashCode(u.uid, salt, code),
        tries: 0,
        sentAt: Timestamp.fromMillis(now),
        expiresAt: Timestamp.fromMillis(now + TTL_MS),
        hourStart: inHour ? d.hourStart : Timestamp.fromMillis(now),
        hourCount: count + 1,
      });
      return 0;
    });
    if (retryIn > 0) return { sent: false, retryIn, masked: mask(u.email) };
    await sendEmail(u.email, codeEmail(code, u.email));
    return { sent: true, retryIn: Math.ceil(GAP_MS / 1000), masked: mask(u.email) };
  });

  const verifyEmailCode = onCall({ memory: '256MiB', secrets: [RESEND_API_KEY] }, async (request) => {
    const u = await signedInUser(request);
    if (u.emailVerified) return { ok: true };
    const code = str(request.data && request.data.code).replace(/\D/g, '');
    if (code.length !== 6) throw new HttpsError('invalid-argument', 'Enter the six-digit code from the email.');
    const ref = db().collection('emailCodes').doc(u.uid);
    const res = await db().runTransaction(async (tx) => {
      const s = await tx.get(ref);
      if (!s.exists) return { ok: false, reason: 'none' };
      const d = s.data();
      if (ms(d.expiresAt) < Date.now()) return { ok: false, reason: 'expired' };
      if (d.email !== norm(u.email)) return { ok: false, reason: 'expired' }; // the account's email changed since
      if ((d.tries || 0) >= MAX_TRIES) return { ok: false, reason: 'tries' };
      if (!sameHash(hashCode(u.uid, d.salt, code), d.hash)) {
        tx.update(ref, { tries: FieldValue.increment(1) });
        return { ok: false, reason: 'wrong', left: MAX_TRIES - (d.tries || 0) - 1 };
      }
      tx.delete(ref);
      return { ok: true };
    });
    if (!res.ok) {
      if (res.reason === 'wrong' && res.left > 0) return { ok: false, left: res.left };
      if (res.reason === 'none') throw new HttpsError('failed-precondition', 'Send yourself a code first.');
      throw new HttpsError('deadline-exceeded', res.reason === 'expired' ? 'That code has expired. Send a new one.' : 'Too many tries. Send a new code.');
    }
    await admin.auth().updateUser(u.uid, { emailVerified: true });
    await db().collection('users').doc(u.uid).set({ emailVerifiedAt: FieldValue.serverTimestamp() }, { merge: true });
    // a booking from a vendor's join link moves in now that the email is proven (join.js); the app shows the
    // result instead of calling claimMyLeadThreads itself, so a mismatch hint is never emailed twice
    // off until the off-platform deploy (worker + join.js + default functions) goes out together: it sets
    // JOIN_CLAIM_ON_VERIFY=on in functions-dashboard/.env, so a code alone never moves a real lead's thread first
    let claim = null;
    if (process.env.JOIN_CLAIM_ON_VERIFY === 'on') try {
      const d = request.data || {};
      const opt = str(d.inquiryId) ? { inquiryId: str(d.inquiryId), t: str(d.t), step: str(d.step), medium: 'app' } : undefined;
      const r = await require('./join').claimLeadThreads(u.uid, opt);
      if (r && r.status && r.status !== 'none') claim = { status: r.status, claimed: r.claimed || 0, masked: str(r.masked), vendorName: str(r.vendorName) };
    } catch (e) {
      console.warn('verifyEmailCode claim', e.message);
    }
    return { ok: true, claim };
  });

  const blockBadSignupEmail = identity.beforeUserCreated({ memory: '256MiB', timeoutSeconds: 7 }, async (event) => {
    const email = event.data && event.data.email;
    if (!email) return; // phone or anonymous: nothing to check
    const v = await checkDomain(email);
    if (v === 'disposable') throw new identity.HttpsError('invalid-argument', 'Please use your own email address - temporary inboxes can’t be used for Lazo.');
    if (v === 'nomail') throw new identity.HttpsError('invalid-argument', 'That email address can’t receive mail. Check it for typos.');
  });

  return { sendEmailCode, verifyEmailCode, blockBadSignupEmail };
};

module.exports._test = { checkDomain, isDisposable, hashCode, sameHash, mask, newCode, codeEmail };
