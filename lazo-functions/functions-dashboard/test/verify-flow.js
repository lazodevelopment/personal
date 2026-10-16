// Checks for verify.js (JC-LAZO-FNDASH-1016-027): the six-digit email code and
// the signup domain block. firebase-admin is replaced by a small in-memory
// Firestore + Auth before verify.js loads, fetch() (Resend) is stubbed, and the
// real handlers run through their .run(). The DNS checks use a fake resolver,
// plus a few live lookups (skipped with --offline).
//   node test/verify-flow.js [--offline]      (from functions-dashboard)
'use strict';
const Module = require('module');
const offline = process.argv.includes('--offline');

// ------------------------------------------------------------ fakes
class TS { constructor(ms) { this._ms = ms; } toMillis() { return this._ms; } toDate() { return new Date(this._ms); } static fromMillis(ms) { return new TS(ms); } }
const INC = (n) => ({ __inc: n });
const SERVER = { __server: true };
const store = new Map();
function apply(base, patch) {
  const o = { ...(base || {}) };
  for (const [k, v] of Object.entries(patch)) {
    if (v && v.__inc !== undefined) o[k] = (o[k] || 0) + v.__inc;
    else if (v === SERVER) o[k] = new TS(Date.now());
    else o[k] = v;
  }
  return o;
}
function docRef(p) {
  return {
    path: p,
    get: async () => ({ exists: store.has(p), data: () => store.get(p) }),
    set: async (d, opt) => { store.set(p, apply(opt && opt.merge ? store.get(p) : {}, d)); },
    update: async (d) => { store.set(p, apply(store.get(p), d)); },
    delete: async () => { store.delete(p); },
  };
}
const fs = {
  collection: (c) => ({ doc: (id) => docRef(`${c}/${id}`) }),
  runTransaction: async (fn) => fn({
    get: (r) => r.get(),
    set: (r, d, o) => { r.set(d, o); },
    update: (r, d) => { r.update(d); },
    delete: (r) => { r.delete(); },
  }),
};
const users = new Map();
const fakeAdmin = {
  firestore: Object.assign(() => fs, { FieldValue: { increment: INC, serverTimestamp: () => SERVER }, Timestamp: TS }),
  auth: () => ({
    getUser: async (uid) => { const u = users.get(uid); if (!u) throw new Error('no user'); return { ...u }; },
    updateUser: async (uid, d) => { users.set(uid, { ...users.get(uid), ...d }); },
  }),
};
const origLoad = Module._load;
Module._load = function (req, ...rest) { return req === 'firebase-admin' ? fakeAdmin : origLoad.call(this, req, ...rest); };

const sent = [];
global.fetch = async (url, opt) => { sent.push({ url, body: JSON.parse(opt.body) }); return { ok: true, text: async () => '' }; };

const verify = require('../verify');
const T = verify._test;
const fns = verify({ value: () => 'test-key' });

let pass = 0, fail = 0;
function ok(cond, name) { if (cond) { pass++; console.log('  ok  ' + name); } else { fail++; console.log('  FAIL ' + name); } }
async function throws(p, re, name) {
  try { await p; ok(false, name + ' (did not throw)'); } catch (e) { ok(re.test(e.message), name + (re.test(e.message) ? '' : ' - got: ' + e.message)); }
}
const call = (fn, uid, data) => fn.run({ auth: uid ? { uid } : null, data: data || {} });
const codeFrom = (m) => (m.body.subject.match(/^(\d{6})/) || [])[1];

(async () => {
  console.log('helpers');
  ok(T.isDisposable('mailinator.com') && T.isDisposable('x.mailinator.com') && T.isDisposable('YOPMAIL.COM'), 'blocklist hits domains, subdomains, any case');
  ok(!T.isDisposable('gmail.com') && !T.isDisposable('aol.com') && !T.isDisposable('icloud.com') && !T.isDisposable('meetlazo.com'), 'real providers are not blocked');
  ok(T.mask('jordan@gmail.com') === 'j***@gmail.com', 'mask');
  const codes = new Set(); for (let i = 0; i < 200; i++) codes.add(T.newCode());
  ok([...codes].every((c) => /^\d{6}$/.test(c)) && codes.size > 190, 'codes are six digits and vary');
  ok(T.sameHash(T.hashCode('u', 's', '012345'), T.hashCode('u', 's', ' 012345 ')) && !T.sameHash(T.hashCode('u', 's', '012345'), T.hashCode('u', 's', '012346')) && !T.sameHash('', ''), 'hash compare');
  const m = T.codeEmail('482913', 'a@b.co');
  ok(m.subject === '482913 is your Lazo code' && m.html.includes('482913') && m.text.includes('482913'), 'code email carries the code');

  console.log('domain check (fake DNS)');
  const err = (code) => Object.assign(new Error(code), { code });
  const R = (mx, a4, a6) => ({
    resolveMx: async () => { if (mx instanceof Error) throw mx; return mx; },
    resolve4: async () => { if (a4 instanceof Error) throw a4; return a4; },
    resolve6: async () => { if (a6 instanceof Error) throw a6; return a6; },
  });
  ok(await T.checkDomain('a@mailinator.com', R([{ exchange: 'mx.x', priority: 1 }])) === 'disposable', 'disposable before any lookup');
  ok(await T.checkDomain('a@good.com', R([{ exchange: 'mx.good.com', priority: 10 }])) === 'ok', 'MX -> ok');
  ok(await T.checkDomain('a@nope.com', R(err('ENOTFOUND'), err('ENOTFOUND'), err('ENOTFOUND'))) === 'nomail', 'no such domain -> nomail');
  ok(await T.checkDomain('a@nomx.com', R(err('ENODATA'), ['1.2.3.4'], err('ENODATA'))) === 'ok', 'no MX but an A record -> ok (implicit MX)');
  ok(await T.checkDomain('a@null.com', R([{ exchange: '', priority: 0 }])) === 'nomail', 'null MX -> nomail');
  ok(await T.checkDomain('a@flaky.com', R(err('ESERVFAIL'))) === 'ok', 'DNS failure fails open');
  ok(await T.checkDomain('a@slow.com', { resolveMx: () => new Promise(() => {}), resolve4: async () => [], resolve6: async () => [] }) === 'ok', 'DNS timeout fails open');
  ok(await T.checkDomain('not-an-email', R([])) === 'nomail' && await T.checkDomain('a@localhost', R([])) === 'nomail', 'malformed -> nomail');

  if (!offline) {
    // a local sandbox resolver can refuse everything (which the check treats as a hiccup and lets through);
    // ask public resolvers so these lookups mean something
    require('dns').setServers(['8.8.8.8', '1.1.1.1']);
    console.log('domain check (live DNS)');
    ok(await T.checkDomain('xxy@aol.com') === 'ok', 'aol.com takes mail (this is why the code step exists)');
    ok(await T.checkDomain('someone@gmail.com') === 'ok', 'gmail.com ok');
    ok(await T.checkDomain('a@this-domain-does-not-exist-lazo-1016.com') === 'nomail', 'made-up domain -> nomail');
    ok(await T.checkDomain('a@gmial.con') === 'nomail', 'typo gmial.con -> nomail');
  }

  console.log('blocking function');
  await throws(fns.blockBadSignupEmail.run({ data: { email: 'spam@yopmail.com' } }), /temporary inboxes/, 'disposable signup refused');
  if (!offline) {
    await throws(fns.blockBadSignupEmail.run({ data: { email: 'a@this-domain-does-not-exist-lazo-1016.com' } }), /can.t receive mail/, 'dead domain signup refused');
    ok((await fns.blockBadSignupEmail.run({ data: { email: 'bride@gmail.com' } })) === undefined, 'real domain allowed');
  }
  ok((await fns.blockBadSignupEmail.run({ data: { phoneNumber: '+15550100' } })) === undefined, 'no email (phone) allowed');

  console.log('send + verify');
  users.set('u1', { uid: 'u1', email: 'Bride@Gmail.com', emailVerified: false });
  await throws(call(fns.sendEmailCode, null), /Sign in first/, 'send needs sign-in');
  let r = await call(fns.sendEmailCode, 'u1');
  ok(r.sent === true && r.masked === 'B***@Gmail.com' && sent.length === 1 && sent[0].body.to[0] === 'Bride@Gmail.com', 'code emailed to the account email');
  const c1 = codeFrom(sent[0]);
  const doc = store.get('emailCodes/u1');
  ok(doc && !JSON.stringify(doc).includes(c1) && doc.hash && doc.salt, 'only a salted hash is stored');
  r = await call(fns.sendEmailCode, 'u1');
  ok(r.sent === false && r.retryIn > 0 && sent.length === 1, 'resend inside 45s refused, no email');
  await throws(call(fns.verifyEmailCode, 'u1', { code: '12' }), /six-digit/, 'short code rejected');
  const wrong = c1 === '000000' ? '111111' : '000000';
  r = await call(fns.verifyEmailCode, 'u1', { code: wrong });
  ok(r.ok === false && r.left === 4 && users.get('u1').emailVerified === false, 'wrong code: not verified, 4 left');
  r = await call(fns.verifyEmailCode, 'u1', { code: c1.slice(0, 3) + ' ' + c1.slice(3) });
  ok(r.ok === true && users.get('u1').emailVerified === true, 'right code (spaces ignored) verifies the account');
  ok(!store.has('emailCodes/u1') && store.get('users/u1') && store.get('users/u1').emailVerifiedAt, 'code doc removed, users.emailVerifiedAt stamped');
  r = await call(fns.sendEmailCode, 'u1');
  ok(r.verified === true && sent.length === 1, 'already verified: no more codes');

  console.log('limits');
  users.set('u2', { uid: 'u2', email: 'x@aol.com', emailVerified: false });
  await call(fns.sendEmailCode, 'u2');
  const c2 = codeFrom(sent[sent.length - 1]);
  const bad = c2 === '999999' ? '888888' : '999999';
  for (let i = 0; i < 4; i++) await call(fns.verifyEmailCode, 'u2', { code: bad });
  await throws(call(fns.verifyEmailCode, 'u2', { code: bad }), /Too many tries/, '5th wrong try locks the code');
  await throws(call(fns.verifyEmailCode, 'u2', { code: c2 }), /Too many tries/, 'even the right code after the lock');
  ok(users.get('u2').emailVerified === false, 'still unverified');
  store.get('emailCodes/u2').sentAt = TS.fromMillis(Date.now() - 60 * 1000);
  r = await call(fns.sendEmailCode, 'u2');
  const c3 = codeFrom(sent[sent.length - 1]);
  ok(r.sent === true && (await call(fns.verifyEmailCode, 'u2', { code: c3 })).ok === true, 'a fresh code resets the tries');

  users.set('u3', { uid: 'u3', email: 'y@aol.com', emailVerified: false });
  await call(fns.sendEmailCode, 'u3');
  const c4 = codeFrom(sent[sent.length - 1]);
  store.get('emailCodes/u3').expiresAt = TS.fromMillis(Date.now() - 1);
  await throws(call(fns.verifyEmailCode, 'u3', { code: c4 }), /expired/, 'expired code refused');
  users.set('u3', { ...users.get('u3'), email: 'z@aol.com' });
  store.get('emailCodes/u3').expiresAt = TS.fromMillis(Date.now() + 60000);
  await throws(call(fns.verifyEmailCode, 'u3', { code: c4 }), /expired/, 'code sent to an old email refused after the email changed');

  users.set('u4', { uid: 'u4', email: 'w@aol.com', emailVerified: false });
  let n = 0;
  for (let i = 0; i < 8; i++) {
    const before = sent.length;
    r = await call(fns.sendEmailCode, 'u4');
    if (sent.length > before) n++;
    if (store.has('emailCodes/u4')) store.get('emailCodes/u4').sentAt = TS.fromMillis(Date.now() - 60 * 1000);
  }
  ok(n === 6 && r.sent === false && r.retryIn > 0, '6 codes an hour, then wait');

  console.log('booking claim after the code');
  const joinPath = require.resolve('../join');
  const claims = [];
  const realJoin = require.cache[joinPath];
  require.cache[joinPath] = { id: joinPath, filename: joinPath, loaded: true, exports: { claimLeadThreads: async (uid, opt) => { claims.push({ uid, opt }); return { claimed: 1, status: 'claimed', masked: 'b***@gmail.com', vendorName: 'Golden Hour' }; } } };
  delete process.env.JOIN_CLAIM_ON_VERIFY;
  users.set('u5b', { uid: 'u5b', email: 'e@gmail.com', emailVerified: false });
  await call(fns.sendEmailCode, 'u5b');
  r = await call(fns.verifyEmailCode, 'u5b', { code: codeFrom(sent[sent.length - 1]), inquiryId: 'q9', t: 'tok' });
  ok(r.ok === true && r.claim === null && claims.length === 0, 'switch off (default): verified, no claim attempted');
  process.env.JOIN_CLAIM_ON_VERIFY = 'on';
  users.set('u6', { uid: 'u6', email: 'b@gmail.com', emailVerified: false });
  await call(fns.sendEmailCode, 'u6');
  r = await call(fns.verifyEmailCode, 'u6', { code: codeFrom(sent[sent.length - 1]), inquiryId: 'q9', t: 'tok', step: 'd3' });
  ok(r.ok === true && r.claim && r.claim.status === 'claimed' && r.claim.vendorName === 'Golden Hour', 'verify returns the claim result');
  ok(claims.length === 1 && claims[0].uid === 'u6' && claims[0].opt.inquiryId === 'q9' && claims[0].opt.t === 'tok' && claims[0].opt.step === 'd3', 'join link details passed to claimLeadThreads');
  require.cache[joinPath].exports = { claimLeadThreads: async () => ({ claimed: 0, status: 'none' }) };
  users.set('u7', { uid: 'u7', email: 'c@gmail.com', emailVerified: false });
  await call(fns.sendEmailCode, 'u7');
  r = await call(fns.verifyEmailCode, 'u7', { code: codeFrom(sent[sent.length - 1]) });
  ok(r.ok === true && r.claim === null, 'no booking: claim is null');
  require.cache[joinPath].exports = { claimLeadThreads: async () => { throw new Error('boom'); } };
  users.set('u8', { uid: 'u8', email: 'd@gmail.com', emailVerified: false });
  await call(fns.sendEmailCode, 'u8');
  r = await call(fns.verifyEmailCode, 'u8', { code: codeFrom(sent[sent.length - 1]) });
  ok(r.ok === true && users.get('u8').emailVerified === true, 'a claim failure never blocks verification');
  if (realJoin) require.cache[joinPath] = realJoin; else delete require.cache[joinPath];

  await throws(call(fns.verifyEmailCode, 'u-none', { code: '123456' }), /no user|Sign in/, 'unknown account');
  users.set('u5', { uid: 'u5', email: 'v@aol.com', emailVerified: false });
  await throws(call(fns.verifyEmailCode, 'u5', { code: '123456' }), /Send yourself a code first/, 'verify before any send');

  console.log(`\n${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
