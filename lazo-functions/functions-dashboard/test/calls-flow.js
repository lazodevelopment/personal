// Checks calls.js (JC-LAZO-CALLS-1016-001) with an in-memory Firestore, and the
// worker's CallRoom (lazo-directory/worker/src/rt.js) against a fake SFU:
// tokens minted here must verify in the worker, the couple's camera is refused
// until the vendor allows it, strangers can't join or pull, and the call log
// reaches callEvent with a valid signature.
//   node test/calls-flow.js      (from functions-dashboard)
'use strict';
const Module = require('module');
const path = require('path');
const { pathToFileURL } = require('url');

// ------------------------------------------------------------ fakes
class TS { constructor(ms) { this._ms = ms; } toMillis() { return this._ms; } toDate() { return new Date(this._ms); } static fromMillis(ms) { return new TS(ms); } }
const SERVER = { __server: true }, DEL = { __del: true };
const UNION = (...xs) => ({ __union: xs });
const store = new Map();
let autoId = 0;
function merge(base, patch) {
  const o = { ...(base || {}) };
  for (const [k, v] of Object.entries(patch)) {
    if (v === DEL) delete o[k];
    else if (v === SERVER) o[k] = new TS(Date.now());
    else if (v && v.__union) o[k] = [...(o[k] || []), ...v.__union];
    else o[k] = v;
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
      for (const [f, op, v] of filters) docs = docs.filter((s) => op === '==' && s.get(f) === v);
      docs = docs.slice(0, lim);
      return { docs, size: docs.length, empty: !docs.length };
    },
  };
}
const fakeAdmin = {
  firestore: Object.assign(() => ({ collection: (c) => coll(c) }), { FieldValue: { serverTimestamp: () => SERVER, delete: () => DEL, arrayUnion: UNION }, Timestamp: TS }),
};
const origLoad = Module._load;
Module._load = function (req, ...rest) { return req === 'firebase-admin' ? fakeAdmin : origLoad.call(this, req, ...rest); };
process.env.CALL_TOKEN_SECRET = 'test-call-secret';
process.env.TELNYX_API_KEY = 'k';
process.env.TELNYX_FROM = '+15550000000';

const texts = [];
let sfuSessions = 0;
const sfuCalls = [];
const eventPosts = [];
global.fetch = async (url, opt = {}) => {
  url = String(url);
  if (url.includes('api.telnyx.com')) { texts.push(JSON.parse(opt.body)); return { ok: true, status: 200, text: async () => '', json: async () => ({}) }; }
  if (url.includes('rtc.live.cloudflare.com')) {
    const body = opt.body ? JSON.parse(opt.body) : {};
    sfuCalls.push({ url, method: opt.method, body });
    let data = {};
    if (url.endsWith('/sessions/new')) data = { sessionId: 'sfu' + (++sfuSessions) };
    else if (url.endsWith('/tracks/new')) data = { tracks: body.tracks, sessionDescription: { type: 'answer', sdp: 'v=0' }, requiresImmediateRenegotiation: body.tracks.some((t) => t.location === 'remote') };
    else data = { tracks: body.tracks || [] };
    return { ok: true, status: 200, json: async () => data, text: async () => JSON.stringify(data) };
  }
  if (url.includes('callEvent')) { eventPosts.push({ body: opt.body, sig: opt.headers['x-lazo-sig'] }); return { ok: true, status: 200, json: async () => ({}) }; }
  throw new Error('unexpected fetch ' + url);
};

const calls = require('../calls');
const C = calls();
let pass = 0, fail = 0;
function ok(c, label) { if (c) pass++; else { fail++; console.log('FAIL', label); } }
const call = (fn, uid, data) => fn.run({ auth: uid ? { uid, token: {} } : null, data });
async function err(p) { try { await p; return null; } catch (e) { return (e.details && e.details.code) || e.code || e.message; } }

// a fake Durable Object state
function doState() {
  const m = new Map(); let alarm = null;
  return { storage: { get: async (k) => m.get(k), put: async (k, v) => { m.set(k, JSON.parse(JSON.stringify(v))); }, setAlarm: async (t) => { alarm = t; } }, _alarm: () => alarm };
}
const offer = (mids) => ({ type: 'offer', sdp: ['v=0', ...mids.flatMap(([mid, kind]) => [`m=${kind} 9 UDP/TLS/RTP/SAVPF 111`, `a=mid:${mid}`])].join('\r\n') });

(async () => {
  const rt = await import(pathToFileURL(path.resolve(__dirname, '../../../lazo-directory/worker/src/rt.js')).href);

  store.set('vendors/vA', { name: 'Vendor A', claimedBy: 'ownerA' });
  store.set('users/ownerA', { role: 'vendor', vendorId: 'vA' });
  store.set('users/c1', { role: 'couple' });
  store.set('users/c2', { role: 'couple' });
  store.set('inquiries/t1', { coupleUid: 'c1', vendorId: 'vA', vendorName: 'Vendor A', coupleName: 'Avery & Jordan' });
  store.set('inquiries/lead1', { coupleUid: 'lead_lead1', vendorId: 'vA', offPlatform: true });
  store.set('inquiries/blk', { coupleUid: 'c1', vendorId: 'vA', blockedByVendor: true });

  // ---- callJoin
  ok(await err(call(C.callJoin, null, { inquiryId: 't1' })) === 'unauthenticated', 'join signed out');
  ok(await err(call(C.callJoin, 'c2', { inquiryId: 't1' })) === 'permission-denied', 'join stranger');
  ok(await err(call(C.callJoin, 'ownerA', { inquiryId: 'lead1' })) === 'lead-no-video', 'no video for leads');
  ok(await err(call(C.callJoin, 'ownerA', { inquiryId: 'blk' })) === 'closed', 'blocked thread');
  let r = await call(C.callJoin, 'c1', { inquiryId: 't1' });
  ok(r.needPhone === true && !r.token, 'couple needs a phone first');
  const v = await call(C.callJoin, 'ownerA', { inquiryId: 't1' });
  ok(v.ok && v.role === 'vendor' && v.token && v.callId && v.otherName === 'Avery & Jordan', 'vendor joins');
  const invites = [...store.entries()].filter(([k, d]) => k.startsWith('inquiries/t1/messages/') && d.callInvite);
  ok(invites.length === 1 && invites[0][1].callInvite.callId === v.callId && invites[0][1].senderRole === 'vendor', 'invite posted in the thread');

  // ---- phone verification
  ok(await err(call(C.phoneStart, 'c1', { phone: '12' })) === 'bad-phone', 'bad phone');
  r = await call(C.phoneStart, 'c1', { phone: '(480) 555-1212' });
  ok(r.ok && texts.length === 1 && texts[0].to === '+14805551212', 'code texted');
  const code = /(\d{6})/.exec(texts[0].text)[1];
  ok(await err(call(C.phoneConfirm, 'c1', { code: code === '000000' ? '111111' : '000000' })) === 'wrong-code', 'wrong code');
  r = await call(C.phoneConfirm, 'c1', { code });
  ok(r.ok && store.get('users/c1').phoneVerified === '+14805551212' && !store.has('phoneCodes/c1'), 'phone verified');
  for (let i = 0; i < 5; i++) await call(C.phoneStart, 'c2', { phone: '4805550000' });
  ok(await err(call(C.phoneStart, 'c2', { phone: '4805550000' })) === 'too-many', 'send limit');

  const c = await call(C.callJoin, 'c1', { inquiryId: 't1' });
  ok(c.ok && c.callId === v.callId && c.role === 'couple', 'couple rejoins the same call');
  ok([...store.keys()].filter((k) => k.startsWith('inquiries/t1/messages/')).length === 1, 'no second invite');

  // ---- token: minted here, verified by the worker
  const S = 'test-call-secret';
  const pv = await rt.verifyCallToken(v.token, S);
  ok(pv && pv.c === v.callId && pv.r === 'vendor' && pv.u === 'ownerA', 'worker verifies the token');
  ok(!(await rt.verifyCallToken(v.token, 'other-secret')), 'wrong secret rejected');
  ok(!(await rt.verifyCallToken(v.token.slice(0, -2) + 'xx', S)), 'tampered token rejected');
  const expired = calls._test.signToken({ c: 'x', u: 'u', r: 'vendor', exp: Date.now() - 1 }, S);
  ok(!(await rt.verifyCallToken(expired, S)), 'expired token rejected');
  ok(await rt.verifyCallToken(expired, S, 3600000), 'expired token still works in-call (grace)');

  // ---- CallRoom
  const env = { CF_REALTIME_APP_ID: 'app', CF_REALTIME_APP_SECRET: 'sec', CALL_TOKEN_SECRET: S, CALL_EVENT_URL: 'https://x/callEvent' };
  const state = doState();
  const room = new rt.CallRoom(state, env);
  const send = async (tok, p, method, body) => {
    const pl = await rt.verifyCallToken(tok, S, p === '/join' ? 0 : 3600000);
    const res = await room.fetch(new Request('https://room' + p, { method, body: body ? JSON.stringify(body) : undefined, headers: { 'x-call': JSON.stringify(pl) } }));
    return { status: res.status, data: await res.json() };
  };
  let x = await send(v.token, '/join', 'POST', {});
  ok(x.status === 200 && x.data.sessionId === 'sfu1' && x.data.camAllowed === true, 'vendor joins the room');
  const vs = x.data.sessionId;
  x = await send(c.token, '/join', 'POST', {});
  const cs = x.data.sessionId;
  const csub = x.data.subSessionId;
  ok(csub && csub !== cs, 'couple gets a separate receive session');
  ok(x.status === 200 && x.data.camAllowed === false && x.data.other && x.data.other.name === 'Vendor A', 'couple joins, camera locked');
  // couple publishes audio: fine. Video: refused until allowed.
  x = await send(c.token, `/sessions/${cs}/tracks/new`, 'POST', { sessionDescription: offer([['0', 'audio']]), tracks: [{ location: 'local', mid: '0', trackName: 'whatever' }] });
  ok(x.status === 200, 'couple audio published');
  x = await send(c.token, `/sessions/${cs}/tracks/new`, 'POST', { sessionDescription: offer([['0', 'audio'], ['1', 'video']]), tracks: [{ location: 'local', mid: '1', trackName: 'audio' }] });
  ok(x.status === 403 && x.data.error === 'camera-not-allowed', 'couple video refused before allow (even mislabelled)');
  // a session can't act on the other's session
  x = await send(c.token, `/sessions/${vs}/tracks/new`, 'POST', { sessionDescription: offer([['0', 'audio']]), tracks: [{ location: 'local', mid: '0' }] });
  ok(x.status === 403, 'cannot use the other session');
  // couple can't allow itself
  x = await send(c.token, '/allow', 'POST', { on: true });
  ok(x.status === 403, 'couple cannot allow its own camera');
  // vendor publishes video, couple pulls it
  x = await send(v.token, `/sessions/${vs}/tracks/new`, 'POST', { sessionDescription: offer([['0', 'audio'], ['1', 'video']]), tracks: [{ location: 'local', mid: '0' }, { location: 'local', mid: '1' }] });
  ok(x.status === 200, 'vendor publishes audio+video');
  x = await send(c.token, '/room', 'POST', {});
  const names = x.data.other.tracks.map((t) => t.trackName);
  ok(names.length === 2 && x.data.other.present, 'couple sees vendor tracks');
  x = await send(c.token, `/sessions/${cs}/tracks/new`, 'POST', { tracks: names.map((n) => ({ location: 'remote', sessionId: vs, trackName: n })) });
  ok(x.status === 400, 'no pulling on the send session');
  x = await send(c.token, `/sessions/${csub}/tracks/new`, 'POST', { sessionDescription: offer([['0', 'audio']]), tracks: [{ location: 'local', mid: '0' }] });
  ok(x.status === 400, 'no publishing on the receive session');
  x = await send(c.token, `/sessions/${csub}/tracks/new`, 'POST', { tracks: names.map((n) => ({ location: 'remote', sessionId: vs, trackName: n })) });
  ok(x.status === 200 && x.data.requiresImmediateRenegotiation, 'couple pulls vendor tracks');
  x = await send(c.token, `/sessions/${csub}/tracks/new`, 'POST', { tracks: [{ location: 'remote', sessionId: 'sfu-other', trackName: names[0] }] });
  ok(x.status === 403, 'cannot pull from outside the room');
  // vendor allows the camera; couple video goes through
  x = await send(v.token, '/allow', 'POST', { on: true });
  ok(x.status === 200 && x.data.coupleCamAllowed === true, 'vendor allows the camera');
  x = await send(c.token, `/sessions/${cs}/tracks/new`, 'POST', { sessionDescription: offer([['0', 'audio'], ['1', 'video']]), tracks: [{ location: 'local', mid: '1' }] });
  ok(x.status === 200, 'couple video after allow');
  // vendor takes it back: forced close on the SFU
  const before = sfuCalls.length;
  x = await send(v.token, '/allow', 'POST', { on: false });
  const close = sfuCalls.slice(before).find((k) => k.url.endsWith(`/sessions/${cs}/tracks/close`));
  ok(close && close.body.force === true && close.body.tracks[0].mid === '1', 'revoking force-closes the couple video');
  // leave -> ended
  x = await send(c.token, '/leave', 'POST', {});
  ok(x.status === 200 && !x.data.ended, 'couple leaves');
  x = await send(v.token, '/leave', 'POST', { report: true });
  ok(x.status === 200 && x.data.ended, 'vendor leaves, call ended');
  x = await send(v.token, '/join', 'POST', {});
  ok(x.status === 410, 'ended room refuses joins');

  // ---- the log: every post signed, and callEvent accepts it
  const types = eventPosts.flatMap((e) => JSON.parse(e.body).events.map((ev) => `${ev.role}:${ev.type}`));
  for (const t of ['vendor:join', 'couple:join', 'couple:audio_on', 'vendor:video_on', 'vendor:camera_allowed', 'couple:video_on', 'vendor:camera_revoked', 'couple:video_off', 'couple:leave', 'vendor:leave', ':ended']) ok(types.includes(t), 'logged ' + t);
  ok(!types.some((t) => t === 'couple:video_on' && types.indexOf(t) < types.indexOf('vendor:camera_allowed')), 'no couple video before allow');
  const mkReq = (body, sig) => ({ method: 'POST', rawBody: Buffer.from(body), body: JSON.parse(body), get: (h) => (h === 'x-lazo-sig' ? sig : '') });
  const mkRes = () => { const o = { code: 200 }; o.status = (c) => { o.code = c; return o; }; o.json = (d) => { o.body = d; return o; }; return o; };
  for (const e of eventPosts) { const res = mkRes(); await C.callEvent(mkReq(e.body, e.sig), res); ok(res.code === 200, 'callEvent accepts the worker post'); }
  const bad = mkRes(); await C.callEvent(mkReq(eventPosts[0].body, 'f'.repeat(64)), bad);
  ok(bad.code === 403, 'callEvent refuses a bad signature');
  const log = store.get(`calls/${v.callId}`);
  ok(log.status === 'ended' && log.events.length >= 11 && log.events.some((e) => e.type === 'camera_allowed'), 'calls/{id} has the log and is ended');
  ok(state._alarm() > 0, 'alarm armed');

  console.log(`${pass}/${pass + fail} pass`);
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
