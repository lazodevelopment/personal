// JC-LAZO-FNDASH-1016-ENGAGE-001 test: June's engagement-shoot spots.
// In-memory Firestore (copied from offplatform-flow.js), stubbed Anthropic and
// Places. The real june-engagement.js handlers run unchanged.
//   node test/engagement-spots.js        (from functions-dashboard)
'use strict';
const path = require('path');
// ------------------------------------------------------------ fake Firestore
class TS { constructor(d) { this._d = new Date(d); this._seconds = Math.floor(this._d.getTime() / 1000); } toDate() { return new Date(this._d); } toMillis() { return this._d.getTime(); } static fromDate(d) { return new TS(d); } static now() { return new TS(new Date()); } }
const SERVER = { __server: true }, DEL = { __del: true };
const store = new Map();   // doc path -> data
let autoId = 0;
const isPlain = (v) => v && typeof v === 'object' && !Array.isArray(v) && !(v instanceof TS) && !(v instanceof Date) && !Buffer.isBuffer(v) && !v.__server && !v.__del;
function resolve(v) { if (v === SERVER) return new TS(new Date()); if (isPlain(v)) { const o = {}; for (const [k, x] of Object.entries(v)) if (x !== DEL) o[k] = resolve(x); return o; } return v; }
function merge(base, patch) { const o = { ...(base || {}) }; for (const [k, v] of Object.entries(patch)) { if (v === DEL) delete o[k]; else if (isPlain(v) && isPlain(o[k])) o[k] = merge(o[k], v); else o[k] = resolve(v); } return o; }
const getPath = (o, p) => p.split('.').reduce((a, k) => (a == null ? undefined : a[k]), o);
const cmpv = (v) => (v instanceof TS ? v.toMillis() : v);
function snapOf(p) { const d = store.get(p); return { exists: d !== undefined, id: p.split('/').pop(), ref: docRef(p), data: () => (d === undefined ? undefined : JSON.parse(JSON.stringify(d), revive)), get: (k) => getPath(d, k) }; }
function revive(k, v) { return v && typeof v === 'object' && v._d && v._seconds != null ? new TS(v._d) : v; }
function docRef(p) {
  return {
    id: p.split('/').pop(), path: p, parent: collRef(p.split('/').slice(0, -1).join('/')),
    collection: (c) => collRef(`${p}/${c}`),
    get: async () => snapOf(p),
    set: async (data, opts) => { store.set(p, opts && opts.merge ? merge(store.get(p), data) : merge({}, data)); },
    update: async (data) => { if (!store.has(p)) throw new Error('no doc ' + p); const flat = {}; for (const [k, v] of Object.entries(data)) { const ks = k.split('.'); let o = flat; ks.slice(0, -1).forEach((x) => { o = o[x] = o[x] || {}; }); o[ks[ks.length - 1]] = v; } store.set(p, merge(store.get(p), flat)); },
    delete: async () => { store.delete(p); },
  };
}
function query(cp, filters, order, lim) {
  const q = {
    where: (f, op, v) => query(cp, [...filters, [f, op, v]], order, lim),
    orderBy: (f, dir) => query(cp, filters, [f, dir || 'asc'], lim),
    limit: (n) => query(cp, filters, order, n),
    get: async () => {
      const depth = cp.split('/').length + 1;
      let rows = [...store.keys()].filter((k) => k.startsWith(cp + '/') && k.split('/').length === depth).map(snapOf);
      for (const [f, op, v] of filters) rows = rows.filter((s) => { const x = cmpv(getPath(s.data(), f)), y = cmpv(v); return op === '==' ? x === y : op === '>=' ? x >= y : op === '<=' ? x <= y : op === '>' ? x > y : op === '<' ? x < y : op === 'in' ? v.includes(x) : false; });
      if (order) rows.sort((a, b) => { const x = cmpv(getPath(a.data(), order[0])), y = cmpv(getPath(b.data(), order[0])); return (x > y ? 1 : x < y ? -1 : 0) * (order[1] === 'desc' ? -1 : 1); });
      if (lim) rows = rows.slice(0, lim);
      return { empty: !rows.length, size: rows.length, docs: rows, forEach: (fn) => rows.forEach(fn) };
    },
  };
  return q;
}
function collRef(cp) { return { id: cp.split('/').pop(), path: cp, doc: (id) => docRef(`${cp}/${id || ('AutoId' + (++autoId)).padEnd(20, 'x')}`), add: async (data) => { const r = docRef(`${cp}/${('AutoId' + (++autoId)).padEnd(20, 'x')}`); await r.set(data); return r; }, ...query(cp, [], null, 0) }; }
const fdb = {
  collection: (c) => collRef(c), doc: (p) => docRef(p),
  batch: () => { const ops = []; return { set: (r, d, o) => ops.push(() => r.set(d, o)), update: (r, d) => ops.push(() => r.update(d)), delete: (r) => ops.push(() => r.delete()), commit: async () => { for (const op of ops) await op(); } }; },
  runTransaction: async (fn) => fn({ get: (r) => r.get(), set: (r, d, o) => r.set(d, o), update: (r, d) => r.update(d) }),
};
const authUsers = {}; const verifyLinks = [];
const files = {};
const firestore = Object.assign(() => fdb, { FieldValue: { serverTimestamp: () => SERVER, delete: () => DEL, increment: (n) => n, arrayUnion: (...a) => a }, Timestamp: TS });
const fakeAdmin = {
  initializeApp: () => {}, apps: [{}], firestore,
  auth: () => ({ getUser: async (uid) => { if (!authUsers[uid]) throw new Error('no user'); return { ...authUsers[uid] }; }, verifyIdToken: async (t) => { if (!t.startsWith('idtok_')) throw new Error('bad token'); return { uid: t.slice(6) }; }, generateEmailVerificationLink: async (email, settings) => { verifyLinks.push({ email, url: settings && settings.url }); return 'https://verify.example/' + encodeURIComponent(email); } }),
  storage: () => ({ bucket: () => ({ file: (p) => ({ download: async () => [files[p] || Buffer.from('%PDF-1.4 fake')], save: async (b) => { files[p] = b; }, getSignedUrl: async () => ['https://signed.example/' + p] }) }) }),
  messaging: () => ({ send: async () => 'ok', sendEachForMulticast: async () => ({ responses: [] }) }),
};
for (const dir of ['functions', 'functions-dashboard']) {
  const base = path.join(__dirname, '..', '..', dir);
  const put = (mod, exp) => { try { const p = require.resolve(mod, { paths: [base] }); require.cache[p] = { id: p, filename: p, loaded: true, exports: exp }; } catch (e) {} };
  put('firebase-admin', fakeAdmin);
  // trigger factories return { run } with the raw handler; onCall keeps HttpsError semantics
  const https = require(require.resolve('firebase-functions/v2/https', { paths: [base] }));
  const raw = (a, b) => { const fn = typeof a === 'function' ? a : b; return Object.assign((...x) => fn(...x), { run: fn }); };
  put('firebase-functions/v2/https', { ...https, onCall: raw, onRequest: raw });
  put('firebase-functions/v2/firestore', { onDocumentCreated: raw, onDocumentWritten: raw, onDocumentUpdated: raw, onDocumentDeleted: raw });
  put('firebase-functions/v2/scheduler', { onSchedule: raw });
}

// ------------------------------------------------------------ fake network
const PHX = { lat: 33.4484, lng: -112.074 };
const TEMPE = { lat: 33.4255, lng: -111.94 };
const PIN = {
  'phoenix': PHX, 'tempe, az': TEMPE,
  'papago park': { lat: 33.4545, lng: -111.948 },
  'desert botanical garden': { lat: 33.4618, lng: -111.9446 },
  'roosevelt row': { lat: 33.4588, lng: -112.0717 },
  'tempe town lake': { lat: 33.4324, lng: -111.9298 },
  'south mountain park': { lat: 33.341, lng: -112.06 },
  'heritage square': { lat: 33.4497, lng: -112.0662 },
  'central park': { lat: 40.7829, lng: -73.9654 },          // far away: dropped
  'hole in the rock': { lat: 33.4527, lng: -111.9461 },
  'camelback mountain': { lat: 33.5151, lng: -111.9617 },
  'wrigley mansion': { lat: 33.5081, lng: -112.0305 },
};
const SPOTS = (names) => names.map((n) => ({ name: n, area: 'Phoenix', why: 'Fits their desert vibe.', bestTime: 'Golden hour, about 5 pm in November.', permit: 'No permit for small portrait sessions', fee: 'Free', crowds: 'Quiet on weekdays', pets: 'Leashed dogs allowed', source: 'https://example.gov/rules' }));
const DEFAULT8 = ['Papago Park', 'Ghost Spot Nobody Knows', 'Desert Botanical Garden', 'Central Park', 'Roosevelt Row', 'Tempe Town Lake', 'South Mountain Park', 'Heritage Square'];
const claudeCalls = []; const placesCalls = [];
let claudeQueue = [];
global.fetch = async (url, o = {}) => {
  url = String(url);
  const body = o.body ? JSON.parse(o.body) : null;
  const res = (status, j) => ({ ok: status < 300, status, json: async () => j, text: async () => JSON.stringify(j) });
  if (url === 'https://api.anthropic.com/v1/messages') {
    claudeCalls.push({ headers: o.headers, body });
    const next = claudeQueue.shift();
    if (next) return next;
    return res(200, { stop_reason: 'end_turn', usage: { input_tokens: 4000, output_tokens: 2500, server_tool_use: { web_search_requests: 3 } }, content: [{ type: 'text', text: 'Here you go:\n```json\n' + JSON.stringify({ spots: SPOTS(DEFAULT8), note: 'November is mild.' }) + '\n```' }] });
  }
  if (url === 'https://places.googleapis.com/v1/places:searchText') {
    placesCalls.push({ mask: o.headers['X-Goog-FieldMask'], body });
    const q = body.textQuery.toLowerCase();
    const k = Object.keys(PIN).sort((a, b) => b.length - a.length).find((n) => q.startsWith(n));
    if (!k) return res(200, {});
    const p = PIN[k];
    return res(200, { places: [{ id: 'pid_' + k.replace(/[^a-z]/g, ''), displayName: { text: k }, formattedAddress: k + ', AZ', location: { latitude: p.lat, longitude: p.lng }, googleMapsUri: 'https://maps.google.com/?cid=' + k.length }] });
  }
  throw new Error('unexpected fetch ' + url);
};

// ------------------------------------------------------------ helpers
let pass = 0, fail = 0;
const ok = (cond, what) => { if (cond) { pass++; console.log('  ok   ', what); } else { fail++; console.log('  FAIL ', what); } };
const call = (fn, uid, data) => fn.run({ auth: uid ? { uid, token: {} } : null, data });
const err = async (p) => { try { await p; return null; } catch (e) { return e; } };
const secret = (v) => ({ value: () => v });

const mod = require('../june-engagement');
const fns = mod(secret('sk-test'), secret('places-test'));
const { qaOf, radiusOf, parseJson } = mod._test;

(async () => {
  console.log('helpers');
  ok(radiusOf('Stay local (15 mi or less)') === 15 && radiusOf('Up to 30 miles') === 30 && radiusOf('Happy to road-trip') === 150 && radiusOf('') === 60, 'travel answer -> radius');
  const qa = qaOf({ questions: ['Where do you live?', 'Vibe?', 'Own question?'], spec: [{ key: 'home' }, { key: 'vibe' }, {}], answers: { 0: 'Tempe, AZ', 2: 'We love tacos' } });
  ok(qa.byKey.home === 'Tempe, AZ' && !qa.byKey.vibe && qa.pairs.length === 2 && qa.pairs[1].q === 'Own question?', 'questionnaire pairs + spec keys (own questions kept)');
  ok(parseJson('text ```json\n{"spots":[1]}\n``` more').spots[0] === 1, 'JSON out of prose + fences');

  // ---------------------------------------------------- seed
  store.set('vendors/v1', { name: 'Golden Hour Co', claimedBy: 'owner1', categories: ['wedding-photographers'] });
  store.set('users/mgr1', { vendorId: 'v1', vendorRole: 'manager' });
  store.set('users/stranger', { vendorId: 'v2', vendorRole: 'manager' });
  store.set('couples/c1', { names: 'Ava & Sam', metroId: 'phoenix', town: '' });
  store.set('inquiries/i1', { vendorId: 'v1', coupleUid: 'c1', structuredIntent: { metroId: 'phoenix' } });
  store.set('inquiries/lead1', { vendorId: 'v1', coupleUid: 'lead_abc', contact: { name: 'Mia' }, structuredIntent: { metroId: 'phoenix' } });

  console.log('auth');
  ok((await err(call(fns.juneEngagementSpots, null, { inquiryId: 'i1' }))).code === 'unauthenticated', 'signed out -> unauthenticated');
  ok((await err(call(fns.juneEngagementSpots, 'stranger', { inquiryId: 'i1' }))).code === 'permission-denied', 'another vendor -> permission-denied');
  ok((await err(call(fns.juneEngagementSpots, 'owner1', { inquiryId: 'nope' }))).code === 'not-found', 'missing thread -> not-found');

  console.log('first set, before answers (wedding city)');
  const r1 = await call(fns.juneEngagementSpots, 'owner1', { inquiryId: 'i1' });
  const c1 = claudeCalls[0];
  ok(c1.body.model === 'claude-sonnet-5-5' && c1.body.fallbacks === 'default' && c1.headers['anthropic-beta'] === 'server-side-fallback-2026-07-01', 'Sonnet 5.5 with the default refusal fallback');
  ok(c1.body.tools[0].type === 'web_search_20260209' && c1.body.tools[0].max_uses === 4, 'web search, at most 4');
  ok(/lives in: phoenix/.test(c1.body.messages[0].content) && /not answered the questionnaire yet/.test(c1.body.messages[0].content), 'prompt: wedding metro as home, no answers yet');
  ok(placesCalls.every((p) => p.mask === 'places.id,places.displayName,places.formattedAddress,places.location,places.googleMapsUri'), 'Places: Pro fields only, no Enterprise');
  ok(placesCalls.length === 9, 'Places calls: 1 home + 8 spots (' + placesCalls.length + ')');
  const names1 = r1.spots.map((s) => s.name);
  ok(r1.spots.length === 6, 'kept 6 (' + r1.spots.length + ')');
  ok(!names1.includes('Ghost Spot Nobody Knows'), 'spot Places cannot find is dropped');
  ok(!names1.includes('Central Park'), 'spot 2,000 miles away is dropped');
  ok(r1.spots.every((s) => s.verified && s.placeId && s.mapsUrl && typeof s.milesFromHome === 'number'), 'every spot has a pin, Maps link and distance');
  const set1 = store.get('inquiries/i1/engagementIdeas/' + r1.setId);
  ok(set1 && set1.trigger === 'vendor' && set1.by === 'owner1' && set1.placesCalls === 9 && set1.estCost === Math.round((4000 * 2e-6 + 2500 * 10e-6 + 3 * 0.01 + 9 * 0.046) * 100) / 100, 'set written with calls + estimated cost ($' + (set1 && set1.estCost) + ')');
  ok(store.get('vendors/v1').engSpotsCount === 1, 'vendor daily count');

  console.log('second set: cache + more like this');
  placesCalls.length = 0;
  claudeQueue.push({ ok: true, status: 200, json: async () => ({ stop_reason: 'end_turn', usage: {}, content: [{ type: 'text', text: JSON.stringify({ spots: SPOTS(['Papago Park', 'Hole in the Rock', 'Camelback Mountain', 'Wrigley Mansion', 'Desert Botanical Garden']) }) }] }) });
  const r2 = await call(fns.juneEngagementSpots, 'mgr1', { inquiryId: 'i1', more: true });
  const c2 = claudeCalls[1].body.messages[0].content;
  ok(/do not repeat: .*Papago Park/.test(c2), 'more: already-shown names go in the prompt');
  ok(!r2.spots.some((s) => s.name === 'Papago Park' || s.name === 'Desert Botanical Garden'), 'more: repeats are dropped');
  ok(placesCalls.length === 3, 'cached home + spots cost nothing; 3 new spots looked up (' + placesCalls.length + ')');
  ok(store.get('inquiries/i1/engagementIdeas/' + r2.setId).cacheHits >= 1, 'cache hits recorded');

  console.log('caps');
  await call(fns.juneEngagementSpots, 'owner1', { inquiryId: 'i1' });
  const e4 = await err(call(fns.juneEngagementSpots, 'owner1', { inquiryId: 'i1' }));
  ok(e4 && e4.code === 'resource-exhausted', '4th set on one thread today -> resource-exhausted');
  store.set('vendors/v1', { ...store.get('vendors/v1'), engSpotsCount: 20 });
  const e5 = await err(call(fns.juneEngagementSpots, 'owner1', { inquiryId: 'lead1' }));
  ok(e5 && e5.code === 'resource-exhausted', 'vendor at 20 today -> resource-exhausted');
  store.set('vendors/v1', { ...store.get('vendors/v1'), engSpotsCount: 0 });

  console.log('off-platform client (no couple doc)');
  const r6 = await call(fns.juneEngagementSpots, 'owner1', { inquiryId: 'lead1' });
  ok(r6.home.label === 'phoenix' && /\(Mia\)/.test(claudeCalls[claudeCalls.length - 1].body.messages[0].content), 'lead_ thread: metro from the thread, name from contact');

  console.log('auto when answers come back');
  const q = { type: 'engagement', title: 'Engagement Session', vendorName: 'Golden Hour Co', status: 'completed',
    questions: ['Where do you live?', 'The vibe', 'How far will you travel for the shoot?', 'Do you have a dog?'],
    spec: [{ key: 'home', kind: 'text' }, { key: 'vibe', kind: 'chips' }, { key: 'travel', kind: 'choice' }, { kind: 'text' }],
    answers: { 0: 'Tempe, AZ', 1: 'Desert, Golden hour', 2: 'Up to 30 miles', 3: 'Yes, Biscuit the corgi' } };
  store.set('inquiries/i1/questionnaires/q1', q);
  const ev = (b, a) => ({ params: { inquiryId: 'i1', qId: 'q1' }, data: { before: { data: () => b }, after: { data: () => a } } });
  const nClaude = claudeCalls.length;
  await fns.engagementSpotsAuto.run(ev({ ...q, status: 'sent', answers: {} }, q));
  const auto = store.get('inquiries/i1/engagementIdeas/auto_q1');
  ok(auto && auto.trigger === 'auto' && auto.home.label === 'Tempe, AZ' && auto.radius === 30 && auto.answered, 'auto set: home from the answer, 30-mile radius');
  const pa = claudeCalls[claudeCalls.length - 1].body.messages[0].content;
  ok(/Biscuit the corgi/.test(pa) && /Desert, Golden hour/.test(pa) && /Their wedding is in phoenix/.test(pa), 'prompt carries their answers (own questions too) and the wedding city');
  ok(auto.spots.every((s) => s.milesFromHome <= 30 * 1.5 + 10), 'every auto spot inside the radius');
  await fns.engagementSpotsAuto.run(ev({ ...q, status: 'sent' }, q));
  ok(claudeCalls.length === nClaude + 1, 'second completion event: no second set');
  await fns.engagementSpotsAuto.run(ev(q, { ...q, answers: { 0: 'Mesa' } }));
  await fns.engagementSpotsAuto.run({ params: { inquiryId: 'i1', qId: 'q2' }, data: { before: { data: () => ({ type: 'custom', status: 'sent' }) }, after: { data: () => ({ type: 'custom', status: 'completed' }) } } });
  ok(claudeCalls.length === nClaude + 1, 'edits after completion and wedding-day questionnaires never trigger');

  console.log('pause_turn + bad output');
  store.set('inquiries/i2', { vendorId: 'v1', coupleUid: 'c1' });
  claudeQueue.push({ ok: true, status: 200, json: async () => ({ stop_reason: 'pause_turn', usage: {}, content: [{ type: 'server_tool_use', id: 's1', name: 'web_search', input: { query: 'papago park photo permit' } }] }) });
  const before = claudeCalls.length;
  const r7 = await call(fns.juneEngagementSpots, 'owner1', { inquiryId: 'i2' });
  ok(claudeCalls.length === before + 2 && claudeCalls[before + 1].body.messages.length === 2 && r7.spots.length > 0, 'pause_turn: resumes with the paused turn and finishes');
  store.set('inquiries/i3', { vendorId: 'v1', coupleUid: 'c1' });
  claudeQueue.push({ ok: true, status: 200, json: async () => ({ stop_reason: 'end_turn', usage: {}, content: [{ type: 'text', text: JSON.stringify({ spots: SPOTS(['Ghost Spot Nobody Knows', 'Central Park']) }) }] }) });
  const e8 = await err(call(fns.juneEngagementSpots, 'owner1', { inquiryId: 'i3' }));
  ok(e8 && e8.code === 'not-found' && !store.get('inquiries/i3/engagementIdeas'), 'nothing verifiable -> clear error, nothing written');
  claudeQueue.push({ ok: false, status: 400, text: async () => '{"error":{"message":"Your credit balance is too low"}}' });
  const e9 = await err(call(fns.juneEngagementSpots, 'owner1', { inquiryId: 'i3' }));
  ok(e9 && /out of credit/.test(e9.message), 'out of Anthropic credit -> says so');

  console.log(`\n${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
