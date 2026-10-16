// End-to-end check of COIs on file (JC-LAZO-FNDASH-1016-COI-001): a vendor uploads a
// certificate -> June reads it -> the vendor sends it to a Lazo venue, a planner, an
// unclaimed listing and a venue not on Lazo -> the venue downloads it -> the sweep
// reminds at 30 / 7 / 0 days with one digest per venue -> the renewal replaces the old
// one everywhere -> a venue asks another vendor for theirs and the share answers it.
// Same in-memory Firestore approach as offplatform-flow.js (no Java for the emulator).
//   node test/coi-flow.js          (from functions-dashboard)
'use strict';
const path = require('path');

// ------------------------------------------------------------ fake Firestore
class TS { constructor(d) { this._d = new Date(d); this._seconds = Math.floor(this._d.getTime() / 1000); } toDate() { return new Date(this._d); } toMillis() { return this._d.getTime(); } static fromDate(d) { return new TS(d); } static now() { return new TS(new Date()); } }
const SERVER = { __server: true }, DEL = { __del: true };
const store = new Map();
let autoId = 0;
const isPlain = (v) => v && typeof v === 'object' && !Array.isArray(v) && !(v instanceof TS) && !(v instanceof Date) && !Buffer.isBuffer(v) && !v.__server && !v.__del;
function resolve(v) { if (v === SERVER) return new TS(new Date()); if (Array.isArray(v)) return v.map(resolve); if (isPlain(v)) { const o = {}; for (const [k, x] of Object.entries(v)) if (x !== DEL) o[k] = resolve(x); return o; } return v; }
function merge(base, patch) { const o = { ...(base || {}) }; for (const [k, v] of Object.entries(patch)) { if (v === DEL) delete o[k]; else if (isPlain(v) && isPlain(o[k])) o[k] = merge(o[k], v); else o[k] = resolve(v); } return o; }
const getPath = (o, p) => p.split('.').reduce((a, k) => (a == null ? undefined : a[k]), o);
const cmpv = (v) => (v instanceof TS ? v.toMillis() : v);
function revive(k, v) { return v && typeof v === 'object' && v._d && v._seconds != null ? new TS(v._d) : v; }
function snapOf(p) { const d = store.get(p); return { exists: d !== undefined, id: p.split('/').pop(), ref: docRef(p), data: () => (d === undefined ? undefined : JSON.parse(JSON.stringify(d), revive)), get: (k) => { const x = getPath(d, k); return x === undefined ? undefined : JSON.parse(JSON.stringify({ x }), revive).x; } }; }
function docRef(p) {
  return {
    id: p.split('/').pop(), path: p,
    collection: (c) => collRef(`${p}/${c}`),
    get: async () => snapOf(p),
    set: async (data, opts) => { store.set(p, opts && opts.merge ? merge(store.get(p), data) : merge({}, data)); },
    update: async (data) => {
      if (!store.has(p)) throw new Error('no doc ' + p);
      const keys = Object.keys(data);
      for (const a of keys) for (const b of keys) if (a !== b && b.startsWith(a + '.')) throw new Error(`field path conflict ${a} / ${b}`);
      // update() semantics: each dotted key replaces exactly that field (a map value replaces the whole map)
      const cur = JSON.parse(JSON.stringify(store.get(p)), revive);
      for (const [k, v] of Object.entries(data)) {
        const ks = k.split('.'); let o = cur;
        for (const x of ks.slice(0, -1)) { if (!isPlain(o[x])) o[x] = {}; o = o[x]; }
        if (v === DEL) delete o[ks[ks.length - 1]]; else o[ks[ks.length - 1]] = resolve(v);
      }
      store.set(p, cur);
    },
    delete: async () => { store.delete(p); },
  };
}
function query(cp, filters, order, lim) {
  return {
    where: (f, op, v) => query(cp, [...filters, [f, op, v]], order, lim),
    orderBy: (f, dir) => query(cp, filters, [f, dir || 'asc'], lim),
    limit: (n) => query(cp, filters, order, n),
    get: async () => {
      const depth = cp.split('/').length + 1;
      let rows = [...store.keys()].filter((k) => k.startsWith(cp + '/') && k.split('/').length === depth).map(snapOf);
      for (const [f, op, v] of filters) rows = rows.filter((s) => { const x = cmpv(getPath(s.data(), f)), y = cmpv(v); return op === '==' ? x === y : op === '>=' ? x >= y : op === '<=' ? x <= y : op === '>' ? x > y : op === '<' ? x < y : op === 'in' ? v.includes(x) : op === 'array-contains' ? (getPath(s.data(), f) || []).includes(v) : false; });
      if (lim) rows = rows.slice(0, lim);
      return { empty: !rows.length, size: rows.length, docs: rows, forEach: (fn) => rows.forEach(fn) };
    },
  };
}
function collRef(cp) { return { id: cp.split('/').pop(), path: cp, doc: (id) => docRef(`${cp}/${id || ('AutoId' + (++autoId)).padEnd(20, 'x')}`), add: async (data) => { const r = docRef(`${cp}/${('AutoId' + (++autoId)).padEnd(20, 'x')}`); await r.set(data); return r; }, ...query(cp, [], null, 0) }; }
const fdb = { collection: (c) => collRef(c), doc: (p) => docRef(p) };
const files = {}; const signed = []; const pushes = [];
const firestore = Object.assign(() => fdb, { FieldValue: { serverTimestamp: () => SERVER, delete: () => DEL, increment: (n) => n, arrayUnion: (...a) => a }, Timestamp: TS });
const fakeAdmin = {
  initializeApp: () => {}, apps: [{}], firestore,
  storage: () => ({ bucket: () => ({ file: (p) => ({ download: async () => [files[p] || Buffer.from('%PDF-1.4 fake')], getSignedUrl: async (o) => { signed.push({ p, o }); return ['https://signed.example/' + p]; } }) }) }),
  messaging: () => ({ sendEachForMulticast: async (m) => { pushes.push(m); return { responses: [], successCount: m.tokens.length }; } }),
};
const base = path.join(__dirname, '..');
const put = (mod, exp) => { const p = require.resolve(mod, { paths: [base] }); require.cache[p] = { id: p, filename: p, loaded: true, exports: exp }; };
put('firebase-admin', fakeAdmin);
const https = require(require.resolve('firebase-functions/v2/https', { paths: [base] }));
const raw = (a, b) => { const fn = typeof a === 'function' ? a : b; return Object.assign((...x) => fn(...x), { run: fn }); };
put('firebase-functions/v2/https', { ...https, onCall: raw, onRequest: raw });
put('firebase-functions/v2/firestore', { onDocumentCreated: raw, onDocumentWritten: raw, onDocumentUpdated: raw, onDocumentDeleted: raw });
put('firebase-functions/v2/scheduler', { onSchedule: raw });

// ------------------------------------------------------------ fake network
const mail = []; const claude = [];
let juneReply = null;
global.fetch = async (url, o = {}) => {
  url = String(url);
  const body = o.body ? JSON.parse(o.body) : null;
  const res = (status, j) => ({ ok: status < 300, status, json: async () => j, text: async () => JSON.stringify(j) });
  if (url.startsWith('https://api.resend.com/')) { mail.push(body); return res(200, { id: 'em' + mail.length }); }
  if (url.startsWith('https://api.anthropic.com/')) { claude.push(body); return res(200, { content: [{ type: 'text', text: '```json\n' + JSON.stringify(juneReply) + '\n```' }] }); }
  throw new Error('unexpected fetch ' + url);
};

// ------------------------------------------------------------ helpers
let pass = 0, fail = 0;
const ok = (cond, what) => { if (cond) { pass++; console.log('  ok   ', what); } else { fail++; console.log('  FAIL ', what); } };
const call = (fn, uid, data) => fn.run({ auth: uid ? { uid, token: {} } : null, data });
const throws = async (p) => { try { await p; return ''; } catch (e) { return e.code || e.message; } };
const http = async (fn, query) => { let status = 200, payload, location; const r = { set() { return this; }, status(s) { status = s; return this; }, send(t) { payload = t; return this; }, redirect(c, l) { status = c; location = l; return this; } }; await fn.run({ query }, r); return { status, body: payload, location }; };
const get = (p) => snapOf(p).data();
const DAY = 86400000;
const ymdIn = (n) => new Date(Date.now() + n * DAY).toLocaleDateString('en-CA', { timeZone: 'America/Phoenix' });
const to = (addr) => mail.filter((m) => m.to.includes(addr));

(async () => {
  // ---- the world
  store.set('vendors/dj', { name: 'Sonoran Sound DJs', category: 'wedding-djs', claimedBy: 'u_dj' });
  store.set('users/u_dj', { role: 'vendor', email: 'dj@sonoran.example', vendorId: 'dj' });
  store.set('users/u_djmgr', { role: 'vendor', email: 'mgr@sonoran.example', vendorId: 'dj', vendorRole: 'manager' });
  store.set('users/u_djmgr/fcm_tokens/t1', { fcm_token: 'tok-mgr' });
  store.set('vendors/ranch', { name: 'The Ranch at Desert Willow', category: 'wedding-venues', claimedBy: 'u_ranch' });
  store.set('users/u_ranch', { role: 'vendor', email: 'events@ranch.example', vendorId: 'ranch' });
  store.set('vendors/plan', { name: 'Saguaro Planning Co', categories: ['wedding-planners'], claimedBy: 'u_plan' });
  store.set('users/u_plan', { role: 'vendor', email: 'hi@saguaroplan.example', vendorId: 'plan' });
  store.set('vendors/barn', { name: 'Old Mill Barn', category: 'wedding-venues', publicEmail: 'book@oldmill.example' });   // listed, unclaimed
  store.set('vendors/flor', { name: 'Petal & Thorn', category: 'wedding-florists', claimedBy: 'u_flor' });
  store.set('users/u_flor', { role: 'vendor', email: 'petal@thorn.example', vendorId: 'flor' });
  store.set('users/stranger', { role: 'vendor', email: 'x@example.com', vendorId: 'zzz' });

  const coi = require('../coi.js')({ value: () => 'test_resend' }, { value: () => 'test_anthropic' });
  const { runSweep, namedOn, daysLeft, keyExpiry } = coi._coi;

  console.log('\n1. helpers');
  ok(namedOn('The Ranch at Desert Willow', { holder: 'Ranch at Desert Willow LLC, 100 Main St, Phoenix AZ' }), 'holder name matches the venue despite "The" and "LLC"');
  ok(!namedOn('Old Mill Barn', { holder: 'Ranch at Desert Willow LLC' }), 'a different holder does not match');
  ok(namedOn('Saguaro Planning Co', { holder: 'To whom it may concern', additionalInsured: { named: ['Saguaro Planning, its officers and employees'] } }), 'additional-insured wording matches');
  ok(keyExpiry([{ line: 'auto', expires: '2027-01-01' }, { line: 'general', expires: '2027-03-01' }]) === '2027-03-01', 'key expiry prefers general liability over auto');
  ok(daysLeft(ymdIn(7)) === 7 && daysLeft(ymdIn(0)) === 0, 'daysLeft counts Phoenix days');

  console.log('\n2. June reads the certificate');
  const P1 = 'vendors/dj/coi/new1/171_acord.pdf';
  files[P1] = Buffer.from('%PDF-1.7 acord 25');
  juneReply = { isCoi: true, insurer: 'Hartford Fire Insurance Co', insured: 'Sonoran Sound LLC', holder: 'The Ranch at Desert Willow, 100 Main St', addlInsdChecked: true, additionalInsured: ['The Ranch at Desert Willow'],
    policies: [{ line: 'general', number: 'GL-123', limit: '$1,000,000', aggregate: 2000000, effective: ymdIn(-300), expires: ymdIn(40) }, { line: 'auto', number: 'AU-9', limit: 1000000, effective: ymdIn(-300), expires: ymdIn(20) }], confidence: 0.92 };
  ok(await throws(call(coi.coiRead, 'stranger', { vendorId: 'dj', path: P1 })) === 'permission-denied', 'someone else cannot have June read it');
  ok(await throws(call(coi.coiRead, 'u_dj', { vendorId: 'dj', path: 'vendors/ranch/coi/x.pdf' })) === 'invalid-argument', "a path outside the vendor's coi folder is refused");
  const read = await call(coi.coiRead, 'u_djmgr', { vendorId: 'dj', path: P1 });
  ok(claude[0].messages[0].content[0].type === 'document', 'the PDF goes to Claude as a document block');
  ok(read.insurer === 'Hartford Fire Insurance Co' && read.policies[0].limit === 1000000, 'June returns the insurer and the GL limit as a number');
  ok(read.expiresAt === ymdIn(40), 'the key expiry is the GL date, not the earlier auto date');
  files['vendors/dj/coi/img/1.jpg'] = Buffer.from([0xff, 0xd8, 0xff, 0xe0]);
  await call(coi.coiRead, 'u_dj', { vendorId: 'dj', path: 'vendors/dj/coi/img/1.jpg' });
  ok(claude[1].messages[0].content[0].type === 'image' && claude[1].messages[0].content[0].source.media_type === 'image/jpeg', 'a photo goes as an image block');

  console.log('\n3. save and send');
  const fields = { insurer: read.insurer, holder: read.holder, additionalInsured: read.additionalInsured, policies: read.policies, expiresAt: read.expiresAt };
  ok(await throws(call(coi.coiSave, 'u_dj', { vendorId: 'dj', ...fields, expiresAt: '', policies: [], file: { path: P1, contentType: 'application/pdf' } })) === 'invalid-argument', 'no expiry date, no save');
  ok(await throws(call(coi.coiSave, 'u_dj', { vendorId: 'dj', ...fields, file: { path: P1, contentType: 'text/html' } })) === 'invalid-argument', 'only a PDF or an image');
  mail.length = 0;
  const s1 = await call(coi.coiSave, 'u_dj', { vendorId: 'dj', ...fields, file: { path: P1, contentType: 'application/pdf', name: 'acord.pdf', size: 12345 }, june: { confidence: 0.92 },
    venueIds: ['ranch', 'plan', 'barn', 'flor', 'dj', 'nope'], offLazo: [{ name: 'Casa Blanca Estate', email: 'Events@CasaBlanca.example' }] });
  const C1 = s1.coiId;
  const c1 = get(`cois/${C1}`);
  ok(c1.status === 'current' && c1.glEach === 1000000 && c1.expiresAt instanceof TS, 'the COI is saved current with the GL limit and a Timestamp expiry');
  ok(JSON.stringify(c1.venueIds.sort()) === JSON.stringify(['barn', 'plan', 'ranch']), 'it went to the venue, the planner and the unclaimed listing only');
  ok(s1.skipped.includes('flor') && s1.skipped.includes('dj') && s1.skipped.includes('nope'), 'a florist, itself and a missing listing are skipped');
  ok(c1.venues.ranch.namedOnCert === true && c1.venues.plan.namedOnCert === false, 'June marks which venues the certificate names');
  const copy = get(`vendors/ranch/coisOnFile/${C1}`);
  ok(copy && copy.vendorName === 'Sonoran Sound DJs' && copy.status === 'current' && copy.namedOnCert === true, "the venue's copy is on file");
  ok(get(`vendors/plan/coisOnFile/${C1}`), "the planner's copy is on file");
  ok(get(`vendors/barn/coisOnFile/${C1}`), "the unclaimed listing's copy waits for the claim");
  ok(to('events@ranch.example').length === 1 && /Sonoran Sound DJs sent you their certificate/.test(to('events@ranch.example')[0].subject), 'the venue owner gets one email');
  ok(/doesn't name Saguaro Planning Co/.test(to('hi@saguaroplan.example')[0].html), 'the planner is told the certificate does not name them');
  ok(snapOf('users/u_ranch').exists && [...store.keys()].some((k) => k.startsWith('users/u_ranch/juneFeed/')), 'the venue gets a bell entry');
  const barnMail = to('book@oldmill.example')[0];
  ok(barnMail && barnMail.html.includes('coiPublic?c=' + C1) && barnMail.html.includes('for-vendors'), 'the unclaimed listing gets a download link and a claim invite');
  const out = get(`cois/${C1}`).offLazo[0];
  ok(out.email === 'events@casablanca.example' && out.token.length > 16, 'the outside venue is stored lowercased with its own token');
  ok(to('events@casablanca.example').length === 1, 'the outside venue gets the email');
  mail.length = 0;
  await call(coi.coiShare, 'u_dj', { coiId: C1, venueIds: ['ranch'], offLazo: [{ email: 'events@casablanca.example' }] });
  ok(mail.length === 0, 're-sending to the same places emails nobody twice');
  ok(await throws(call(coi.coiShare, 'u_ranch', { coiId: C1, venueIds: ['plan'] })) === 'permission-denied', 'a venue cannot re-share a vendor COI');
  ok(await throws(call(coi.coiShare, null, {})) === 'unauthenticated' && await throws(call(coi.coiUnshare, null, {})) === 'unauthenticated', 'signed out: unauthenticated before any lookup');
  ok(await throws(call(coi.coiShare, 'u_dj', { coiId: '' })) === 'not-found' && await throws(call(coi.coiFileLink, 'u_dj', { coiId: '../x' })) === 'not-found', 'an empty or malformed id is not-found, not an internal error');

  console.log('\n4. downloads');
  const l1 = await call(coi.coiFileLink, 'u_ranch', { coiId: C1, venueId: 'ranch' });
  ok(l1.url.endsWith(P1) && signed[signed.length - 1].o.expires - Date.now() <= 10 * 60 * 1000, 'the venue gets a 10-minute signed link');
  ok(get(`cois/${C1}`).venues.ranch.viewedAt && get(`vendors/ranch/coisOnFile/${C1}`).viewedAt, 'the view is recorded on both sides');
  ok(await throws(call(coi.coiFileLink, 'u_flor', { coiId: C1, venueId: 'flor' })) === 'permission-denied', 'a listing it was not sent to cannot download');
  ok(await throws(call(coi.coiFileLink, 'u_flor', { coiId: C1, venueId: 'ranch' })) === 'permission-denied', "nobody can borrow another venue's id");
  ok((await call(coi.coiFileLink, 'u_djmgr', { coiId: C1 })).url, 'the vendor team can download its own');
  const tokOut = get(`cois/${C1}`).offLazo[0].token;
  let r = await http(coi.coiPublic, { c: C1, t: tokOut });
  ok(r.status === 302 && r.location.endsWith(P1), 'the emailed link redirects to a fresh signed URL');
  ok(get(`cois/${C1}`).offLazo[0].openedAt, 'the open is recorded');
  r = await http(coi.coiPublic, { c: C1, t: 'x'.repeat(24) });
  ok(r.status === 200 && /not found/i.test(r.body), 'a wrong token is refused');
  const barnTok = get(`cois/${C1}`).venues.barn.emailed.token;
  ok((await http(coi.coiPublic, { c: C1, t: barnTok })).status === 302, "the unclaimed listing's link works");

  console.log('\n5. remove from one venue');
  await call(coi.coiUnshare, 'u_dj', { coiId: C1, venueId: 'plan' });
  ok(!get(`cois/${C1}`).venues.plan && !get(`cois/${C1}`).venueIds.includes('plan') && !get(`vendors/plan/coisOnFile/${C1}`), "the planner's copy is gone");

  console.log('\n6. reminders');
  mail.length = 0; pushes.length = 0;
  let sw = await runSweep(new Date());
  ok(sw.vendorMails === 0, 'nothing is due 40 days out');
  sw = await runSweep(new Date(Date.now() + 12 * DAY));   // 28 days left
  ok(sw.vendorMails === 1 && to('dj@sonoran.example').length === 1 && /30 days/.test(to('dj@sonoran.example')[0].subject), 'the 30-day reminder goes to the vendor owner');
  ok(sw.venueMails === 1 && to('events@ranch.example').length === 1, 'the venue gets one digest');
  ok(!to('book@oldmill.example').length, 'an unclaimed listing gets no digest');
  ok(pushes.some((p) => p.tokens.includes('tok-mgr')), 'the vendor manager gets the push');
  mail.length = 0;
  sw = await runSweep(new Date(Date.now() + 13 * DAY));
  ok(sw.vendorMails === 0 && mail.length === 0, 'the 30-day step is sent once');
  // a second vendor lapsing at the same venue lands in the same digest
  store.set('vendors/cake', { name: 'Sweet Saguaro Cakes', category: 'wedding-cakes', claimedBy: 'u_cake' });
  store.set('users/u_cake', { role: 'vendor', email: 'cake@saguaro.example', vendorId: 'cake' });
  files['vendors/cake/coi/a/c.pdf'] = Buffer.from('%PDF');
  await call(coi.coiSave, 'u_cake', { vendorId: 'cake', insurer: 'Next Insurance', expiresAt: ymdIn(36), policies: [{ line: 'general', limit: 1000000, expires: ymdIn(36) }], file: { path: 'vendors/cake/coi/a/c.pdf', contentType: 'application/pdf' }, venueIds: ['ranch'] });
  mail.length = 0;
  sw = await runSweep(new Date(Date.now() + 34 * DAY));   // DJ 6 days left (d7), cake 2 days (d30 skipped -> d7)
  ok(sw.vendorMails === 2 && sw.venueMails === 1, 'two vendor reminders, one venue digest');
  const dig = to('events@ranch.example')[0];
  ok(dig && /2 vendor COIs/.test(dig.subject) && dig.html.includes('Sonoran Sound DJs') && dig.html.includes('Sweet Saguaro Cakes'), 'the digest lists both vendors');
  const cakeCoi = [...store.keys()].find((k) => /^cois\/[^/]+$/.test(k) && get(k).vendorId === 'cake');
  ok(get(cakeCoi).remind.d30 && get(cakeCoi).remind.d7, 'jumping straight to 7 days marks the 30-day step too');
  mail.length = 0;
  sw = await runSweep(new Date(Date.now() + 41 * DAY));   // DJ 1 day past
  ok(/has expired/.test((to('dj@sonoran.example')[0] || {}).subject || ''), 'the expiry reminder goes out (a day late here, so it says expired)');
  ok(/expired/i.test((to('events@ranch.example')[0] || {}).html || ''), 'the venue digest says it expired');
  ok(get(`cois/${C1}`).status === 'expired' && get(`vendors/ranch/coisOnFile/${C1}`).status === 'expired', 'a lapsed COI shows Expired on both sides');

  console.log('\n7. the renewal');
  mail.length = 0;
  const P2 = 'vendors/dj/coi/new2/renewal.pdf'; files[P2] = Buffer.from('%PDF renewal');
  const s2 = await call(coi.coiSave, 'u_dj', { vendorId: 'dj', replaces: C1, insurer: 'Hartford Fire Insurance Co', holder: 'The Ranch at Desert Willow', expiresAt: ymdIn(405), policies: [{ line: 'general', limit: 2000000, expires: ymdIn(405) }], file: { path: P2, contentType: 'application/pdf' } });
  const C2 = s2.coiId;
  ok(get(`cois/${C1}`).status === 'replaced' && get(`cois/${C1}`).replacedBy === C2, 'the old COI is marked replaced');
  ok(JSON.stringify(get(`cois/${C2}`).venueIds.sort()) === JSON.stringify(['barn', 'ranch']), 'the renewal goes to every venue that had the old one');
  ok(get(`vendors/ranch/coisOnFile/${C2}`).status === 'current' && get(`vendors/ranch/coisOnFile/${C1}`).status === 'replaced', 'the venue sees the new one current and the old one replaced');
  ok(/renewed COI is on file/.test((to('events@ranch.example')[0] || {}).subject || ''), 'the venue hears about the renewal');
  ok(to('events@casablanca.example').length === 1 && /renewed/.test(to('events@casablanca.example')[0].subject), 'the outside venue gets the renewal emailed');
  ok(to('book@oldmill.example').length === 1, 'the unclaimed listing gets the renewal emailed');
  r = await http(coi.coiPublic, { c: C1, t: tokOut });
  ok(/newer|replaced/i.test(String(r.body)), "the old emailed link points to the newer certificate");
  const newTok = get(`cois/${C2}`).offLazo[0].token;
  r = await http(coi.coiPublic, { c: C2, t: newTok, stop: '1' });
  ok(get(`cois/${C2}`).offLazo[0].stopped === true, 'the stop link stops COI emails');
  mail.length = 0;
  files['vendors/dj/coi/new3/r.pdf'] = Buffer.from('%PDF');
  await call(coi.coiSave, 'u_dj', { vendorId: 'dj', replaces: C2, insurer: 'Hartford', expiresAt: ymdIn(700), policies: [], file: { path: 'vendors/dj/coi/new3/r.pdf', contentType: 'application/pdf' } });
  ok(!to('events@casablanca.example').length, 'a stopped address gets no more renewals');

  console.log('\n8. requests');
  mail.length = 0;
  ok(await throws(call(coi.coiRequest, 'u_flor', { venueId: 'flor', vendorId: 'dj' })) === 'failed-precondition', 'a florist cannot request COIs');
  ok(await throws(call(coi.coiRequest, 'u_dj', { venueId: 'ranch', vendorId: 'flor' })) === 'permission-denied', 'only the venue team can ask for it');
  ok((await call(coi.coiRequest, 'u_ranch', { venueId: 'ranch', vendorId: 'dj' })).already === true, 'a current COI on file means no request');
  const q = await call(coi.coiRequest, 'u_ranch', { venueId: 'ranch', vendorId: 'flor', note: 'Need us as additional insured please' });
  ok(q.open && get('coiRequests/ranch__flor').status === 'open', 'the request is open');
  ok(/asked for your COI/.test((to('petal@thorn.example')[0] || {}).subject || ''), 'the florist is emailed');
  files['vendors/flor/coi/a/f.pdf'] = Buffer.from('%PDF');
  await call(coi.coiSave, 'u_flor', { vendorId: 'flor', insurer: 'Thimble', expiresAt: ymdIn(200), policies: [], file: { path: 'vendors/flor/coi/a/f.pdf', contentType: 'application/pdf' }, venueIds: ['ranch'] });
  ok(get('coiRequests/ranch__flor').status === 'sent', 'sending the COI answers the request');
  mail.length = 0;
  store.set('vendors/photo', { name: 'Lens & Light', category: 'wedding-photographers', email: 'hi@lens.example' });
  await call(coi.coiRequest, 'u_plan', { venueId: 'plan', vendorId: 'photo' });
  ok(/Claim my free listing/.test((to('hi@lens.example')[0] || {}).html || ''), 'an unclaimed vendor is invited to claim to send it');

  console.log(`\n${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
