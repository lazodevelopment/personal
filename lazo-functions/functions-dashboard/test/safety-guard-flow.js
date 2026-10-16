// Checks safety-guard.js + the vendor side of safety.js (JC-LAZO-SAFETY-1016-003/004)
// end to end with an in-memory Firestore: holds, nudges, Jesse's auto-block
// rules, vendor warnings, admin review, report/block a couple.
//   node test/safety-guard-flow.js      (from functions-dashboard)
'use strict';
const Module = require('module');

// ------------------------------------------------------------ fakes
class TS { constructor(ms) { this._ms = ms; } toMillis() { return this._ms; } toDate() { return new Date(this._ms); } static fromMillis(ms) { return new TS(ms); } }
const SERVER = { __server: true }, DEL = { __del: true };
const store = new Map();   // path -> data
let autoId = 0;
function resolve(v) { return v === SERVER ? new TS(Date.now()) : v; }
function merge(base, patch) {
  const o = { ...(base || {}) };
  for (const [k, v] of Object.entries(patch)) {
    if (v === DEL) delete o[k];
    else if (v && typeof v === 'object' && !Array.isArray(v) && !(v instanceof TS) && v !== SERVER) o[k] = Object.fromEntries(Object.entries(v).map(([a, b]) => [a, resolve(b)]));
    else o[k] = resolve(v);
  }
  return o;
}
function snap(p) { const d = store.get(p); return { id: p.split('/').pop(), ref: docRef(p), exists: !!d, data: () => d && { ...d }, get: (f) => d && f.split('.').reduce((a, k) => (a == null ? a : a[k]), d) }; }
function docRef(p) {
  return {
    id: p.split('/').pop(), path: p,
    get: async () => snap(p),
    set: async (d, opt) => { store.set(p, merge(opt && opt.merge ? store.get(p) : {}, d)); },
    delete: async () => { store.delete(p); },
    collection: (c) => coll(`${p}/${c}`),
  };
}
function coll(p, filters = [], lim = 1e9) {
  const depth = p.split('/').length + 1;
  return {
    doc: (id) => docRef(`${p}/${id || 'auto' + (++autoId)}`),
    add: async (d) => { const r = docRef(`${p}/auto${++autoId}`); await r.set(d); return r; },
    where: (f, op, v) => coll(p, [...filters, [f, op, v]], lim),
    limit: (n) => coll(p, filters, n),
    get: async () => {
      let docs = [...store.keys()].filter((k) => k.startsWith(p + '/') && k.split('/').length === depth).map(snap);
      for (const [f, op, v] of filters) docs = docs.filter((s) => {
        const x = s.get(f);
        if (op === '==') return x === v;
        if (op === '>=') return (x && x.toMillis ? x.toMillis() : x) >= (v && v.toMillis ? v.toMillis() : v);
        throw new Error('op ' + op);
      });
      docs = docs.slice(0, lim);
      return { docs, size: docs.length, empty: !docs.length, forEach: (fn) => docs.forEach(fn) };
    },
  };
}
const fs = { collection: (c) => coll(c) };
const created = new Map();   // uid -> auth creation ms
const fakeAdmin = {
  firestore: Object.assign(() => fs, { FieldValue: { serverTimestamp: () => SERVER, delete: () => DEL }, Timestamp: TS }),
  auth: () => ({ getUser: async (uid) => ({ uid, metadata: { creationTime: new Date(created.get(uid) || Date.now()).toUTCString() } }) }),
};
const origLoad = Module._load;
Module._load = function (req, ...rest) { return req === 'firebase-admin' ? fakeAdmin : origLoad.call(this, req, ...rest); };
const mails = [];
global.fetch = async (url, opt) => { mails.push(JSON.parse(opt.body)); return { ok: true, text: async () => '' }; };

process.env.RESEND_API_KEY = 'test-key';
const KEY = { value: () => 'test-key' };
const G = require('../safety-guard')(KEY);
const S = require('../safety')();
const OP = require('../offplatform');

let pass = 0, fail = 0;
function ok(c, label) { if (c) pass++; else { fail++; console.log('FAIL', label); } }
const call = (fn, uid, data, token = {}) => fn.run({ auth: uid ? { uid, token } : null, data });
async function throws(p, code) { try { await p; return false; } catch (e) { return !code || e.code === code || (e.details && e.details.code === code); } }
const msgs = (inq) => [...store.keys()].filter((k) => k.startsWith(`inquiries/${inq}/messages/`)).map((k) => store.get(k));
const DAY = 86400000;

function seedThread(id, coupleUid, vendorId, intent) {
  store.set(`inquiries/${id}`, { coupleUid, vendorId, vendorName: 'V ' + vendorId, coupleName: 'Avery', structuredIntent: { message: intent || '' } });
}
function seedCouple(uid, ageDays) { store.set(`users/${uid}`, { role: 'couple', email: uid + '@x.com' }); created.set(uid, Date.now() - ageDays * DAY); }

(async () => {
  store.set('vendors/vA', { name: 'Vendor A', claimedBy: 'ownerA' });
  store.set('vendors/vB', { name: 'Vendor B', claimedBy: 'ownerB' });
  store.set('users/ownerA', { role: 'vendor', vendorId: 'vA' });
  store.set('users/ownerB', { role: 'vendor', vendorId: 'vB' });
  store.set('admins/boss', { role: 'owner' });

  // 1. clean couple message is delivered
  seedCouple('c1', 40); seedThread('t1', 'c1', 'vA', 'Hi, is June 14 open?');
  let r = await call(G.sendThreadMessage, 'c1', { inquiryId: 't1', text: 'Great, what does the 8-hour package include?' });
  ok(r.ok && msgs('t1').length === 1, '1 clean delivered');

  // 2. weak "video call" is held with the video nudge, no strike, nothing written
  r = await call(G.sendThreadMessage, 'c1', { inquiryId: 't1', text: 'Could we do a video call this week?' });
  ok(r.held && r.reason === 'video' && r.action === 'request_lazo_call' && !r.blocked && msgs('t1').length === 1, '2 weak held');
  ok(r.nudge === OP.NUDGE.video, '2 nudge text');

  // 3. contact: early (2 couple messages so far: intent + 1) is held; later delivered
  r = await call(G.sendThreadMessage, 'c1', { inquiryId: 't1', text: 'Text me at 480-555-1212' });
  ok(r.held && r.reason === 'contact' && msgs('t1').length === 1, '3 early phone held');
  await call(G.sendThreadMessage, 'c1', { inquiryId: 't1', text: 'Also, do you travel to Sedona?' });
  r = await call(G.sendThreadMessage, 'c1', { inquiryId: 't1', text: 'my email is avery@gmail.com' });
  ok(r.ok && msgs('t1').length === 3, '3 late email delivered');

  // 4. old account, one strong hit: held, a strike, not blocked
  r = await call(G.sendThreadMessage, 'c1', { inquiryId: 't1', text: 'Can we just hop on zoom?' });
  ok(r.held && r.reason === 'video' && !r.blocked, '4 first strike held, not blocked');
  ok(!store.get('users/c1').safetyBlock, '4 no block yet');
  // 5. second strong hit within 30 days: rule (b) blocks
  r = await call(G.sendThreadMessage, 'c1', { inquiryId: 't1', text: 'FaceTime me instead' });
  ok(r.held && r.blocked && r.nudge === OP.NUDGE.review, '5 second strike blocks');
  ok(store.get('users/c1').safetyBlock && /^b:/.test(store.get('users/c1').safetyBlock.reason), '5 rule b recorded');
  ok(store.get('inquiries/t1').coupleSafetyBlocked === true, '5 thread marked');
  ok(msgs('t1').some((m) => m.system && m.text === OP.VENDOR_BLOCK_NOTICE), '5 vendor told in thread');
  ok(store.get('safetyBlocks/c1').status === 'blocked', '5 safetyBlocks doc');
  ok(mails.some((m) => /blocked c1@x.com/.test(m.subject)), '5 support alerted');
  ok(await throws(call(G.sendThreadMessage, 'c1', { inquiryId: 't1', text: 'hello?' }), 'account-under-review'), '5 blocked account refused');
  r = await call(G.safetyPrecheck, 'c1', { text: 'hi', vendorId: 'vB' });
  ok(r.blocked && r.nudge === OP.NUDGE.review, '5 precheck says under review');

  // 6. rule (a): new account, outside call in the FIRST message (precheck before the thread exists)
  seedCouple('c2', 1);
  r = await call(G.safetyPrecheck, 'c2', { text: "Hi! Let's get on a zoom call first", vendorId: 'vB' });
  ok(r.held && r.blocked, '6 new account first-message zoom blocked');
  ok(/^a:/.test(store.get('users/c2').safetyBlock.reason), '6 rule a recorded');

  // 7. same first message from an older account: held, not blocked
  seedCouple('c3', 60);
  r = await call(G.safetyPrecheck, 'c3', { text: "Hi! Let's get on a zoom call first", vendorId: 'vB' });
  ok(r.held && !r.blocked && r.reason === 'video', '7 old account first-message zoom held only');
  r = await call(G.safetyPrecheck, 'c3', { text: 'Hi! Is October 3 open?', vendorId: 'vB' });
  ok(r.ok && !r.held, '7 clean precheck passes');
  r = await call(G.safetyPrecheck, 'c3', { text: 'Hi! call me 480 555 1212', vendorId: 'vB' });
  ok(r.held && r.reason === 'contact', '7 phone in first message held');

  // 8. vendor: outside link -> warning first, confirm sends and logs
  seedCouple('c4', 60); seedThread('t4', 'c4', 'vA', 'Hello!');
  r = await call(G.sendThreadMessage, 'ownerA', { inquiryId: 't4', text: 'Here is my Zoom link: https://zoom.us/j/1' });
  ok(r.warn && r.warning === OP.VENDOR_WARNING && msgs('t4').length === 0, '8 vendor warned, not sent');
  r = await call(G.sendThreadMessage, 'ownerA', { inquiryId: 't4', text: 'Here is my Zoom link: https://zoom.us/j/1', confirm: true });
  ok(r.ok && msgs('t4').length === 1 && msgs('t4')[0].senderRole === 'vendor', '8 vendor confirm sends');
  ok([...store.entries()].some(([k, v]) => k.startsWith('safetyHolds/') && v.role === 'vendor' && v.status === 'warned'), '8 vendor warning logged');
  ok(!store.get('users/ownerA').safetyBlock, '8 vendor never blocked');
  r = await call(G.safetyPrecheck, 'ownerA', { text: 'facetime?', role: 'vendor' });
  ok(r.warn, '8 vendor precheck warns');

  // 9. strangers can't post
  ok(await throws(call(G.sendThreadMessage, 'ownerB', { inquiryId: 't4', text: 'hi' }), 'permission-denied'), '9 other vendor refused');
  ok(await throws(call(G.sendThreadMessage, null, { inquiryId: 't4', text: 'hi' }), 'unauthenticated'), '9 signed out refused');

  // 10. admin review: non-admin refused; release a hold; unblock
  ok(await throws(call(G.safetyReview, 'c3', { action: 'unblock', uid: 'c1' }), 'permission-denied'), '10 non-admin refused');
  const weakHold = [...store.entries()].find(([k, v]) => k.startsWith('safetyHolds/') && v.uid === 'c1' && v.level === 'weak');
  r = await call(G.safetyReview, 'boss', { action: 'release', holdId: weakHold[0].split('/')[1] });
  ok(r.ok && msgs('t1').some((m) => m.releasedHoldId), '10 released into thread');
  r = await call(G.safetyReview, 'boss', { action: 'unblock', uid: 'c1' });
  ok(r.ok && !store.get('users/c1').safetyBlock && !store.get('inquiries/t1').coupleSafetyBlocked && store.get('safetyBlocks/c1').status === 'cleared', '10 unblocked');

  // 11. vendor reports a couple: thread blocked for the couple, support emailed
  r = await call(S.reportCouple, 'ownerA', { inquiryId: 't4', reason: 'extortion', detail: 'Asked for money after a call' });
  ok(r.ok && store.get('inquiries/t4').blockedByVendor === true, '11 report blocks thread');
  ok(mails.some((m) => /URGENT couple extortion/.test(m.subject)), '11 urgent mail');
  ok(await throws(call(G.sendThreadMessage, 'c4', { inquiryId: 't4', text: 'hello?' }), 'failed-precondition'), '11 couple refused on blocked thread');
  ok(await throws(call(S.reportCouple, 'c4', { inquiryId: 't4', reason: 'spam' }), 'permission-denied'), '11 couple cannot use reportCouple');
  r = await call(S.blockCouple, 'ownerA', { inquiryId: 't4', blocked: false });
  ok(r.ok && store.get('inquiries/t4').blockedByVendor === false, '11 vendor can unblock');

  // 13. callRequest: fixed text, never held, flagged; vendors can't send one
  seedCouple('c5', 60); seedThread('t5', 'c5', 'vA', '');
  r = await call(G.sendThreadMessage, 'c5', { inquiryId: 't5', callRequest: true, text: 'zoom zoom' });
  ok(r.ok && msgs('t5').length === 1 && msgs('t5')[0].callRequest === true && !/zoom/.test(msgs('t5')[0].text), '13 call request delivered with fixed text');
  ok(await throws(call(G.sendThreadMessage, 'ownerA', { inquiryId: 't5', callRequest: true }), 'invalid-argument'), '13 vendor cannot send a call request');
  // 14. the app's inquiries.message counts as the first message
  seedCouple('c6', 1); store.set('inquiries/t6', { coupleUid: 'c6', vendorId: 'vB', message: 'Hi! Is May 3 open?', structuredIntent: {} });
  r = await call(G.sendThreadMessage, 'c6', { inquiryId: 't6', text: 'can we zoom call?' });
  ok(r.held && !r.blocked, '14 second message from a new account: held, not rule a');

  // 12. digest runs
  await G.safetyDigest.run({});
  ok(mails.some((m) => /\[lazo\/safety\] daily/.test(m.subject)), '12 digest mailed');

  console.log(`${pass}/${pass + fail} pass`);
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
