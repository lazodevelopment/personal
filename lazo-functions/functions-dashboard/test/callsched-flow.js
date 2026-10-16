// Checks callsched.js (JC-LAZO-CALLSCHED-1016-001): Pro-only scheduling, the
// thread card message, reschedule / cancel from either side, the couple's
// audio-only preference, the .ics, and the 24h / 15 min reminders.
//   node test/callsched-flow.js      (from functions-dashboard)
'use strict';
const Module = require('module');

class TS { constructor(ms) { this._ms = ms; } toMillis() { return this._ms; } toDate() { return new Date(this._ms); } static fromMillis(ms) { return new TS(ms); } static fromDate(d) { return new TS(d.getTime()); } }
const SERVER = { __server: true }, DEL = { __del: true };
const INC = (n) => ({ __inc: n });
const store = new Map();
let autoId = 0;
function merge(base, patch) {
  const o = { ...(base || {}) };
  for (const [k, v] of Object.entries(patch)) {
    if (v === DEL) delete o[k];
    else if (v === SERVER) o[k] = new TS(Date.now());
    else if (v && v.__inc !== undefined) o[k] = (o[k] || 0) + v.__inc;
    else o[k] = v;
  }
  return o;
}
function snap(p) { const d = store.get(p); return { id: p.split('/').pop(), ref: docRef(p), exists: !!d, data: () => d && { ...d }, get: (f) => d && f.split('.').reduce((a, k) => (a == null ? a : a[k]), d) }; }
function docRef(p) {
  return { id: p.split('/').pop(), path: p, get: async () => snap(p),
    set: async (d, opt) => { store.set(p, merge(opt && opt.merge ? store.get(p) : {}, d)); },
    delete: async () => { store.delete(p); }, collection: (c) => coll(`${p}/${c}`) };
}
const ms = (x) => (x && x.toMillis ? x.toMillis() : x);
function coll(p, filters = []) {
  const depth = p.split('/').length + 1;
  return {
    doc: (id) => docRef(`${p}/${id || 'auto' + (++autoId)}`),
    add: async (d) => { const r = docRef(`${p}/auto${++autoId}`); await r.set(d); return r; },
    where: (f, op, v) => coll(p, [...filters, [f, op, v]]),
    limit: () => coll(p, filters),
    get: async () => {
      let docs = [...store.keys()].filter((k) => k.startsWith(p + '/') && k.split('/').length === depth).map(snap);
      for (const [f, op, v] of filters) docs = docs.filter((s) => {
        const x = s.get(f);
        return op === '==' ? x === v : op === '>=' ? ms(x) >= ms(v) : op === '<=' ? ms(x) <= ms(v) : false;
      });
      return { docs, size: docs.length, empty: !docs.length, forEach: (fn) => docs.forEach(fn) };
    },
  };
}
const pushes = [];
const fakeAdmin = {
  firestore: Object.assign(() => ({ collection: (c) => coll(c) }), { FieldValue: { serverTimestamp: () => SERVER, delete: () => DEL, increment: INC }, Timestamp: TS }),
  messaging: () => ({ sendEachForMulticast: async (m) => { pushes.push(m); return { successCount: m.tokens.length, responses: [] }; } }),
};
const origLoad = Module._load;
Module._load = function (req, ...rest) { return req === 'firebase-admin' ? fakeAdmin : origLoad.call(this, req, ...rest); };
const mails = [];
global.fetch = async (url, opt) => { mails.push(JSON.parse(opt.body)); return { ok: true, text: async () => '' }; };

const S = require('../callsched')({ value: () => 'k' });
const T = require('../callsched')._test;
let pass = 0, fail = 0;
function ok(c, label) { if (c) pass++; else { fail++; console.log('FAIL', label); } }
const call = (fn, uid, data) => fn.run({ auth: uid ? { uid, token: {} } : null, data });
async function err(p) { try { await p; return null; } catch (e) { return (e.details && e.details.code) || e.code; } }
const msgs = (t) => [...store.entries()].filter(([k]) => k.startsWith(`inquiries/${t}/messages/`)).map(([, v]) => v);
const inH = (h) => new Date(Date.now() + h * 3600000).toISOString();

(async () => {
  // ---- helpers
  ok(T.tierOf({ tier: 'pro' }) === 'pro' && T.tierOf({ tier: 'studio' }) === 'studio' && T.tierOf({}) === 'free', 'tierOf');
  ok(T.tierOf({ tier: 'pro', tierExpiresAt: new TS(Date.now() - 1000) }) === 'free', 'expired Pro is free');
  const d = new Date('2026-11-14T22:00:00Z');
  ok(/Saturday, November 14 at 3:00 PM MST/.test(T.whenIn(d, { tz: 'America/Phoenix' })), 'whenIn IANA: ' + T.whenIn(d, { tz: 'America/Phoenix' }));
  ok(/Saturday, November 14 at 5:00 PM EST/.test(T.whenIn(d, { offsetMin: -300, name: 'EST' })), 'whenIn offset: ' + T.whenIn(d, { offsetMin: -300, name: 'EST' }));

  store.set('vendors/vFree', { name: 'Free Florals', claimedBy: 'ownF', tier: 'free' });
  store.set('vendors/vPro', { name: 'Golden Hour Studio', claimedBy: 'ownP', tier: 'pro', scheduler: { tz: 'America/Phoenix' } });
  store.set('users/ownF', { role: 'vendor', vendorId: 'vFree', email: 'f@v.com' });
  store.set('users/ownP', { role: 'vendor', vendorId: 'vPro', email: 'p@v.com' });
  store.set('users/ownP/fcm_tokens/t1', { fcm_token: 'tokV' });
  store.set('users/c1', { role: 'couple', email: 'c1@x.com' });
  store.set('users/c1/fcm_tokens/t1', { fcm_token: 'tokC' });
  store.set('inquiries/tf', { coupleUid: 'c1', vendorId: 'vFree', vendorName: 'Free Florals', coupleName: 'Avery & Jordan' });
  store.set('inquiries/tp', { coupleUid: 'c1', vendorId: 'vPro', vendorName: 'Golden Hour Studio', coupleName: 'Avery & Jordan' });
  store.set('inquiries/tl', { coupleUid: 'lead_tl', vendorId: 'vPro', offPlatform: true });
  store.set('inquiries/tb', { coupleUid: 'c1', vendorId: 'vPro', blockedByVendor: true });

  // ---- plan rule
  ok(await err(call(S.scheduleCall, 'ownF', { inquiryId: 'tf', startAt: inH(30) })) === 'pro-required', 'free vendor cannot schedule');
  ok(await err(call(S.scheduleCall, 'c1', { inquiryId: 'tf', startAt: inH(30) })) === 'pro-required', 'couple cannot schedule with a free vendor');
  // ---- guards
  ok(await err(call(S.scheduleCall, null, { inquiryId: 'tp', startAt: inH(30) })) === 'unauthenticated', 'signed out');
  ok(await err(call(S.scheduleCall, 'stranger', { inquiryId: 'tp', startAt: inH(30) })) === 'permission-denied', 'stranger');
  ok(await err(call(S.scheduleCall, 'ownP', { inquiryId: 'tl', startAt: inH(30) })) === 'lead-no-video', 'no Lazo call for leads');
  ok(await err(call(S.scheduleCall, 'ownP', { inquiryId: 'tb', startAt: inH(30) })) === 'closed', 'blocked thread');
  ok(await err(call(S.scheduleCall, 'ownP', { inquiryId: 'tp', startAt: new Date(Date.now() + 60000).toISOString() })) === 'too-soon', 'too soon');
  ok(await err(call(S.scheduleCall, 'ownP', { inquiryId: 'tp', startAt: 'nope' })) === 'bad-time', 'bad time');

  // ---- vendor schedules
  let r = await call(S.scheduleCall, 'ownP', { inquiryId: 'tp', startAt: inH(30), minutes: 45 });
  ok(r.ok && r.consultId && r.whenFor.vendor, 'vendor schedules');
  let c = store.get(`consults/${r.consultId}`);
  ok(c.lazoCall === true && c.mode === 'video' && c.minutes === 45 && c.status === 'booked' && c.icsToken && c.scheduledBy === 'vendor', 'consult doc');
  ok(msgs('tp').some((m) => m.callSchedule && m.callSchedule.consultId === r.consultId && m.senderRole === 'vendor'), 'thread card message');
  ok(mails.some((m) => m.to[0] === 'c1@x.com' && /scheduled a Lazo video call/.test(m.text)) && pushes.some((p) => p.tokens.includes('tokC')), 'couple told (email + push)');
  ok(!mails.some((m) => m.to[0] === 'p@v.com'), 'vendor not told about their own action');
  const first = r.consultId;
  ok((await call(S.scheduleCall, 'ownP', { inquiryId: 'tp', startAt: inH(30), minutes: 7 })).ok, 'odd length falls back');
  ok(store.get(`consults/${[...store.keys()].filter((k) => k.startsWith('consults/')).pop().split('/')[1]}`).minutes === 30, 'default 30 minutes');

  // ---- couple schedules, with their time zone and audio-only
  r = await call(S.scheduleCall, 'c1', { inquiryId: 'tp', startAt: inH(50), tzOffsetMin: -300, tzName: 'EST', audioOnly: true });
  c = store.get(`consults/${r.consultId}`);
  ok(r.ok && c.coupleTz.offsetMin === -300 && /EST/.test(c.whenFor.couple) && /MST|MDT/.test(c.whenFor.vendor), 'both time zones: ' + JSON.stringify(c.whenFor));
  ok(store.get('inquiries/tp').coupleAudioOnly === true, 'audio-only preference saved');
  ok(mails.some((m) => m.to[0] === 'p@v.com' && /Avery & Jordan scheduled/.test(m.text)), 'vendor told');

  // ---- reschedule (couple moves the vendor's call)
  store.set(`consults/${first}`, merge(store.get(`consults/${first}`), { reminded: { h24: new TS(1) } }));
  r = await call(S.rescheduleCall, 'c1', { consultId: first, startAt: inH(72), minutes: 60, tzOffsetMin: -300, tzName: 'EST' });
  c = store.get(`consults/${first}`);
  ok(r.ok && c.minutes === 60 && c.reschedules === 1 && Object.keys(c.reminded).length === 0 && c.whenFor.couple, 'rescheduled, reminders reset');
  ok(msgs('tp').some((m) => m.text === 'Moved the Lazo video call.' && m.senderRole === 'couple'), 'reschedule note');

  // ---- cancel (vendor)
  r = await call(S.cancelCall, 'ownP', { consultId: first });
  ok(r.ok && store.get(`consults/${first}`).status === 'cancelled' && store.get(`consults/${first}`).cancelledBy === 'vendor', 'cancelled');
  ok((await call(S.cancelCall, 'c1', { consultId: first })).already, 'cancel twice is fine');
  ok(await err(call(S.rescheduleCall, 'ownP', { consultId: first, startAt: inH(80) })) === 'cancelled', 'cannot move a cancelled call');
  ok(await err(call(S.cancelCall, 'stranger', { consultId: first })) === 'permission-denied', 'stranger cannot cancel');

  // ---- preference
  ok((await call(S.setCallPref, 'c1', { inquiryId: 'tp', audioOnly: false })).audioOnly === false && store.get('inquiries/tp').coupleAudioOnly === false, 'couple clears audio-only');
  ok(await err(call(S.setCallPref, 'ownP', { inquiryId: 'tp', audioOnly: true })) === 'permission-denied', 'vendor cannot set it');

  // ---- .ics
  const live = [...store.entries()].find(([k, v]) => k.startsWith('consults/') && v.status === 'booked');
  const mkRes = () => { const o = { code: 200, headers: {} }; o.status = (x) => { o.code = x; return o; }; o.set = (k, v) => { o.headers[k] = v; return o; }; o.send = (b) => { o.body = b; return o; }; return o; };
  let res = mkRes(); await S.callIcs({ query: { id: live[0].split('/')[1], t: live[1].icsToken } }, res);
  ok(res.code === 200 && /text\/calendar/.test(res.headers['content-type']) && /DTSTART:\d{8}T\d{6}Z/.test(res.body) && /TRIGGER:-PT15M/.test(res.body), '.ics served');
  res = mkRes(); await S.callIcs({ query: { id: live[0].split('/')[1], t: 'wrong' } }, res);
  ok(res.code === 404, '.ics needs its token');

  // ---- reminders
  store.set('consults/soon', { lazoCall: true, status: 'booked', vendorId: 'vPro', vendorName: 'Golden Hour Studio', coupleUid: 'c1', coupleName: 'Avery & Jordan', inquiryId: 'tp',
    startAt: TS.fromMillis(Date.now() + 10 * 60000), endAt: TS.fromMillis(Date.now() + 40 * 60000), reminded: {}, whenFor: { vendor: 'today at 3:00 PM MST' }, icsToken: 'x' });
  store.set('consults/tomorrow', { lazoCall: true, status: 'booked', vendorId: 'vPro', vendorName: 'Golden Hour Studio', coupleUid: 'c1', coupleName: 'Avery & Jordan', inquiryId: 'tp',
    startAt: TS.fromMillis(Date.now() + 23.5 * 3600000), endAt: TS.fromMillis(Date.now() + 24 * 3600000), reminded: {}, whenFor: { vendor: 'tomorrow at 3:00 PM MST' }, icsToken: 'y' });
  store.set('consults/book', { status: 'booked', mode: 'phone', vendorId: 'vPro', startAt: TS.fromMillis(Date.now() + 10 * 60000), reminded: {} });
  const m0 = mails.length, p0 = pushes.length;
  await S.callReminderSweep.run({});
  const newMails = mails.slice(m0);
  ok(newMails.filter((m) => /15 minutes/.test(m.subject)).length === 2, '15-minute reminder to both');
  ok(newMails.filter((m) => /tomorrow/.test(m.subject)).length === 2, '24h reminder to both');
  ok(pushes.length - p0 === 4, 'pushes to both, twice');
  ok(!store.get('consults/book').reminded.m15, 'non-Lazo consult untouched');
  const m1 = mails.length;
  await S.callReminderSweep.run({});
  ok(mails.length === m1, 'no duplicate reminders');

  console.log(`${pass}/${pass + fail} pass`);
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
