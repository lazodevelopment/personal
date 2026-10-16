// End-to-end check of the off-platform client path (JC-LAZO-FNDASH-1016):
// a vendor adds a client by hand -> sends an agreement -> the client gets one
// email with the /f/ page -> signs there -> pays an invoice there -> the
// vendor's thread shows signed and paid -> the client later joins Lazo with a
// verified email (matched to the one her vendor has) and takes the thread
// with them; the link only points at the thread. Plus the join push: the
// signed email doubles as the 'make your free account' email, the claim link,
// days 3/7/14, the stop link, the one text, and the claim through the link.
//
// No Java here, so no Firestore emulator: firebase-admin is replaced by a small
// in-memory Firestore before any module loads, the trigger factories hand back
// their raw handlers, and fetch() is stubbed (Resend, SignWell, Whop, fileView).
// The real handlers from both codebases run unchanged.
//   node test/offplatform-flow.js [outDir]      (from functions-dashboard)
'use strict';
const path = require('path'); const fs = require('fs'); const crypto = require('crypto');
const out = process.argv[2] || path.join(__dirname, 'out-offplatform'); fs.mkdirSync(out, { recursive: true });

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
for (const k of ['RESEND_API_KEY', 'SIGNWELL_API_KEY', 'WHOP_API_KEY', 'TELNYX_API_KEY', 'TELNYX_FROM', 'TELNYX_PUBLIC_KEY', 'ANTHROPIC_API_KEY']) process.env[k] = 'test_' + k;
process.env.WHOP_APP_WEBHOOK_SECRET = 'whsec_' + Buffer.from('webhook-secret-for-tests').toString('base64');
process.env.GCLOUD_PROJECT = 'lazo-513ec';
process.env.FUNCTIONS_EMULATOR = 'true';   // join.js sweeps at any hour
process.env.JOIN_VERIFY_LINK = 'on';      // sections 1-6: before verify.js ships (confirm link); section 6b: after (signup code)

// ------------------------------------------------------------ fake network
const mail = [], signwell = [], whop = [], texts = [], other = [];
let fileViewHandler = null; const fnRoutes = {};
global.fetch = async (url, o = {}) => {
  url = String(url);
  const body = o.body ? JSON.parse(o.body) : null;
  const res = (status, j) => ({ ok: status < 300, status, json: async () => j, text: async () => JSON.stringify(j), arrayBuffer: async () => Buffer.from('%PDF signed') });
  if (url.startsWith('https://api.resend.com/')) { mail.push(body); return res(200, { id: 'em' + mail.length }); }
  if (url.startsWith('https://www.signwell.com/api/v1/documents/') && o.method === 'POST') { signwell.push(body); return res(201, { id: 'sw_doc_1', recipients: [{ id: '1', email: body.recipients[0].email, embedded_signing_url: 'https://www.signwell.com/docs/sw_doc_1/sign/abc123' }] }); }
  if (url.includes('/completed_pdf/')) return res(200, {});
  if (url.startsWith('https://api.whop.com/')) { whop.push({ url, body }); return res(200, { id: 'ch_1', purchase_url: 'https://whop.com/checkout/ch_1' }); }
  if (url.startsWith('https://api.telnyx.com/')) { texts.push(body); return res(200, { data: {} }); }
  const fnName = (url.match(/^https:\/\/us-central1-lazo-513ec\.cloudfunctions\.net\/(join(?:Go|Stop|Done))\?/) || [])[1];
  if (fnName) {
    const r = await http(fnRoutes[fnName], { query: Object.fromEntries(new URL(url).searchParams) });
    return { ok: r.status < 300, status: r.status, headers: { get: (k) => (k === 'location' ? r.location || null : 'text/html') }, text: async () => String(r.body || '') };
  }
  if (url.startsWith('https://us-central1-lazo-513ec.cloudfunctions.net/fileView')) {
    const u = new URL(url); let status = 200, payload = null;
    await fileViewHandler({ query: Object.fromEntries(u.searchParams), get: () => '' }, { set() { return this; }, status(s) { status = s; return this; }, json(j) { payload = j; return this; } });
    return res(status, payload);
  }
  other.push(url); return res(200, {});
};

// ------------------------------------------------------------ helpers
let pass = 0, fail = 0;
const ok = (cond, what) => { if (cond) { pass++; console.log('  ok   ', what); } else { fail++; console.log('  FAIL ', what); } };
const call = (fn, uid, data) => fn.run({ auth: uid ? { uid, token: {} } : null, data });
const http = async (fn, { query = {}, headers = {}, body, method = 'GET' } = {}) => {
  let status = 200, payload, location;
  const req = { method, query, body, headers, rawBody: body ? Buffer.from(JSON.stringify(body)) : undefined, get: (h) => headers[h.toLowerCase()] || '' };
  const r = { set() { return this; }, status(s) { status = s; return this; }, json(j) { payload = j; return this; }, send(t) { payload = t; return this; }, redirect(c, l) { status = c; location = l; return this; } };
  await fn(req, r); return { status, body: payload, location };
};
const throws = async (p) => { try { await p; return ''; } catch (e) { return e.code || e.message; } };
const written = (p, before) => ({ params: paramsOf(p), data: { before: { exists: before !== undefined, data: () => before }, after: { exists: store.has(p), data: () => snapOf(p).data(), ref: docRef(p) } } });
const paramsOf = (p) => { const s = p.split('/'); const o = { inquiryId: s[1] }; if (s[2] === 'contracts') o.contractId = s[3]; if (s[2] === 'invoices') o.invoiceId = s[3]; if (s[0] === 'users') return { uid: s[1] }; return o; };

(async () => {
  // ---- the world
  store.set('vendors/v1', { name: 'Desert Light Films', category: 'wedding-videographers', claimedBy: 'uv', email: 'owner@desertlight.example', publicEmail: 'hello@desertlight.example', tier: 'studio', payments: { processor: 'whop', whopCompanyId: 'biz_desert' }, brand: { primary: '#2B3A55', accent: '#E3B873' } });
  store.set('users/uv', { role: 'vendor', email: 'owner@desertlight.example', vendorId: 'v1' });
  store.set('users/stranger', { role: 'vendor', email: 'x@example.com', vendorId: 'v9' });

  const leads = require('../leads.js')({ value: () => process.env.RESEND_API_KEY });
  const payments = require('../payments.js')({ value: () => process.env.RESEND_API_KEY });
  const cn = require('../couple-notify.js')({ value: () => process.env.RESEND_API_KEY });
  const idx = require('../../functions/index.js');
  const join = require('../join.js')({ value: () => process.env.RESEND_API_KEY });
  fileViewHandler = payments.fileView.run; fnRoutes.joinGo = join.joinGo.run; fnRoutes.joinStop = join.joinStop.run; fnRoutes.joinDone = join.joinDone.run;
  const J = require('../join-copy.js');

  console.log('\n1. vendor adds a client by hand');
  ok(await throws(call(leads.addClient, null, { vendorId: 'v1', name: 'Maya Ortiz', email: 'maya@example.com' })) === 'unauthenticated', 'signed-out caller refused');
  ok(await throws(call(leads.addClient, 'stranger', { vendorId: 'v1', name: 'Maya Ortiz', email: 'maya@example.com' })) === 'permission-denied', 'another vendor refused');
  ok(await throws(call(leads.addClient, 'uv', { vendorId: 'v1', name: 'Maya Ortiz', email: 'not-an-email' })) === 'invalid-argument', 'bad email refused');
  const add = await call(leads.addClient, 'uv', { vendorId: 'v1', name: 'Maya Ortiz', email: 'Maya@Example.com', phone: '(602) 555-0142', weddingDate: '2027-04-17', venue: 'The Wigwam', sendLink: false });
  const I = add.inquiryId, inqP = `inquiries/${I}`;
  const inq0 = snapOf(inqP).data();
  ok(inq0 && inq0.offPlatform === true && inq0.coupleUid === `lead_${I}` && inq0.source === 'manual', 'off-platform thread created in the leadIngest shape');
  ok(inq0.contact.email === 'maya@example.com' && inq0.contact.phone === '+16025550142' && inq0.contact.smsOk === false, 'contact stored, email lowercased, texts off until the client opts in');
  ok(inq0.structuredIntent.weddingDate === '2027-04-17' && inq0.structuredIntent.venue === 'The Wigwam', 'date and venue on structuredIntent');
  ok(add.url === `https://meetlazo.com/f/${I}?t=${inq0.fileToken}`, 'returns the /f/ link');
  ok(mail.length === 0, 'no email when sendLink is off');
  const again = await call(leads.addClient, 'uv', { vendorId: 'v1', name: 'Maya Ortiz', email: 'maya@example.com' });
  ok(again.existing === true && again.inquiryId === I, 'same email again reuses the thread');

  console.log('\n2. vendor sends the agreement');
  store.set(`${inqP}/contracts/k1`, { vendorId: 'v1', coupleUid: `lead_${I}`, status: 'draft', pdfPath: 'vendors/v1/contracts/k1.pdf', templateName: 'Wedding Film Agreement', title: 'Wedding Film Agreement', missingFields: [], values: { total_price: '$4,800', couple_names: 'Maya Ortiz' }, createdAt: new TS(new Date()) });
  const sent = await call(idx.sendContractForSignature, 'uv', { vendorId: 'v1', inquiryId: I, contractId: 'k1' });
  ok(signwell.length === 1 && signwell[0].recipients[0].email === 'maya@example.com' && signwell[0].recipients[0].name === 'Maya Ortiz', 'SignWell signer is the thread contact');
  ok(signwell[0].embedded_signing === true && !signwell[0].recipients[0].send_email, 'embedded signing, SignWell sends no email itself');
  ok(sent.signingUrl && snapOf(`${inqP}/contracts/k1`).data().status === 'sent', 'contract marked sent with its signing URL');
  await cn.coupleOnContract.run(written(`${inqP}/contracts/k1`, { status: 'draft' }));
  const signMail = mail.filter((m) => m.to.includes('maya@example.com'));
  ok(signMail.length === 1 && /sent your agreement to sign/.test(signMail[0].subject), 'client gets ONE email: "' + (signMail[0] && signMail[0].subject) + '"');
  ok(signMail[0] && signMail[0].html.includes(`https://meetlazo.com/f/${encodeURIComponent(I)}?t=${encodeURIComponent(inq0.fileToken)}`), 'the email links to the /f/ page');
  ok(signMail[0] && !signMail[0].html.includes('app.meetlazo.com'), 'no app link in it');
  await cn.coupleOnContract.run(written(`${inqP}/contracts/k1`, { status: 'draft' }));
  ok(mail.filter((m) => m.to.includes('maya@example.com')).length === 1, 'a retried trigger does not send twice');
  if (signMail[0]) fs.writeFileSync(path.join(out, '1-sign-email.html'), signMail[0].html);

  console.log('\n3. the /f/ page');
  const fv = await http(payments.fileView.run, { query: { inquiry: I, t: inq0.fileToken } });
  ok(fv.status === 200 && fv.body.contract.signingUrl === 'https://www.signwell.com/docs/sw_doc_1/sign/abc123', 'fileView returns signingUrl to the token holder');
  ok(fv.body.offPlatform === true, 'fileView says the thread is off-platform');
  ok((await http(payments.fileView.run, { query: { inquiry: I, t: 'x'.repeat(inq0.fileToken.length) } })).status === 403, 'wrong token refused');
  const worker = await import(path.join(__dirname, '..', '..', '..', 'lazo-directory', 'worker', 'src', 'index.js').replace(/\\/g, '/').replace(/^([A-Z]):/, 'file:///$1:'));
  const page = async () => (await worker.default.fetch(new Request(`https://meetlazo.com/f/${I}?t=${inq0.fileToken}`), {}, { waitUntil() {} })).text();
  let html = await page();
  fs.writeFileSync(path.join(out, '2-f-page-to-sign.html'), html);
  ok(html.includes('href="https://www.signwell.com/docs/sw_doc_1/sign/abc123"') && html.includes('Review &amp; sign'), '/f/ shows a Sign button to SignWell');
  ok(!html.includes('app.meetlazo.com/dashboard'), '/f/ has no "sign in to Lazo" links for this client');
  ok(html.includes('&t="+encodeURIComponent(TOK)'), '/f/ sends its token to payCheckout');

  console.log('\n4. client signs (SignWell webhook)');
  await http(idx.signwellWebhook.run, { method: 'POST', body: { event: { type: 'document_completed' }, data: { object: { id: 'sw_doc_1', metadata: { contractId: 'k1', inquiryId: I, vendorId: 'v1' } } } } });
  ok(snapOf(`${inqP}/contracts/k1`).data().status === 'signed' && snapOf(inqP).data().contractStatus === 'signed', 'vendor thread shows signed');
  const nBefore = mail.length;
  await cn.coupleOnContract.run(written(`${inqP}/contracts/k1`, { status: 'sent' }));
  const signedMail = mail.slice(nBefore).find((m) => m.to.includes('maya@example.com'));
  ok(signedMail && /^Signed with Desert Light Films/.test(signedMail.subject) && signedMail.html.includes('meetlazo.com/f/'), 'signed email is the join email: "' + (signedMail && signedMail.subject) + '"');
  ok(mail.slice(nBefore).filter((m) => m.to.includes('maya@example.com')).length === 1, 'one email, not a signed one plus a join one');
  const claimHref = `https://meetlazo.com/join/${I}?t=${encodeURIComponent(inq0.fileToken)}&s=day0`;
  ok(signedMail && signedMail.html.includes(claimHref.replace(/&/g, '&')) && /Create my free account/.test(signedMail.html), 'main button is the claim link');
  ok(signedMail && /Stop these emails/.test(signedMail.html), 'it has a stop link');
  if (signedMail) fs.writeFileSync(path.join(out, '5-day0-signed.html'), signedMail.html);
  let jn = snapOf(inqP).data().joinNudge || {};
  ok(jn.next === 'day3' && jn.nextAt && Math.round((jn.nextAt.toMillis() - Date.now()) / 86400e3) === 3 && jn.sms === 'none', 'follow-ups start: day 3 next, no text (added by hand, no SMS consent)');

  console.log('\n5. invoice, then payment on /f/');
  store.set(`${inqP}/invoices/inv1`, { vendorId: 'v1', coupleUid: `lead_${I}`, title: 'Retainer', total: 1200, status: 'sent', lineItems: [{ label: 'Retainer', amount: 1200 }], createdAt: new TS(new Date()) });
  await cn.coupleOnInvoice.run(written(`${inqP}/invoices/inv1`, undefined));
  const invMail = mail.filter((m) => /Invoice from/.test(m.subject));
  ok(invMail.length === 1 && invMail[0].to.includes('maya@example.com') && invMail[0].html.includes('meetlazo.com/f/'), 'invoice email reaches the client with the /f/ link');
  if (invMail[0]) fs.writeFileSync(path.join(out, '3-invoice-email.html'), invMail[0].html);
  ok((await http(payments.payCheckout.run, { query: { inquiry: I, invoice: 'inv1' } })).status === 403, 'payCheckout without the token: refused');
  ok((await http(payments.payCheckout.run, { query: { inquiry: I, invoice: 'inv1', t: 'nope' } })).status === 403, 'payCheckout with a wrong token: refused');
  ok((await http(payments.payCheckout.run, { query: { inquiry: I, invoice: 'inv1' }, headers: { authorization: 'Bearer idtok_stranger' } })).status === 403, 'payCheckout as an unrelated signed-in user: refused');
  const co = await http(payments.payCheckout.run, { query: { inquiry: I, invoice: 'inv1', t: inq0.fileToken } });
  ok(co.status === 200 && co.body.url === 'https://whop.com/checkout/ch_1', 'payCheckout with the token opens Whop checkout');
  const cfg = whop.find((w) => w.url.includes('/checkout_configurations'));
  ok(cfg && cfg.body.plan.company_id === 'biz_desert' && cfg.body.redirect_url.startsWith(`https://meetlazo.com/f/${I}?t=`), "checkout is on the vendor's Whop company and returns to /f/");
  const vco = await http(payments.payCheckout.run, { query: { inquiry: I, invoice: 'inv1' }, headers: { authorization: 'Bearer idtok_uv' } });
  ok(vco.status === 200, 'the vendor (signed in) can still open it');
  // Whop says paid
  const evt = { type: 'payment.succeeded', data: { id: 'pay_1', company_id: 'biz_desert', total: 1200, metadata: { lazo: 'invoice', inquiryId: I, invoiceId: 'inv1', tip: '0' } } };
  const wid = 'msg_1', wts = String(Math.floor(Date.now() / 1000)), key = Buffer.from(process.env.WHOP_APP_WEBHOOK_SECRET.slice(6), 'base64');
  const wsig = 'v1,' + crypto.createHmac('sha256', key).update(`${wid}.${wts}.${JSON.stringify(evt)}`).digest('base64');
  const wh = await http(payments.whopAppWebhook.run, { method: 'POST', body: evt, headers: { 'webhook-id': wid, 'webhook-timestamp': wts, 'webhook-signature': wsig } });
  ok(wh.status === 200 && snapOf(`${inqP}/invoices/inv1`).data().status === 'paid' && snapOf(inqP).data().invoiceStatus === 'paid', 'vendor thread shows paid');
  const n2 = mail.length;
  await cn.coupleOnInvoice.run(written(`${inqP}/invoices/inv1`, { status: 'sent' }));
  const rcpt = mail.slice(n2).find((m) => /Receipt/.test(m.subject));
  ok(rcpt && rcpt.to.includes('maya@example.com') && rcpt.html.includes('meetlazo.com/f/'), 'client gets a receipt linking to /f/');
  html = await page();
  fs.writeFileSync(path.join(out, '4-f-page-done.html'), html);
  ok(/Signed /.test(html) && /pill ok small">Paid/.test(html), '/f/ now shows signed and paid');
  ok(html.includes(`https://meetlazo.com/join/${I}?t=${encodeURIComponent(inq0.fileToken)}&amp;s=fpage`), '/f/ offers the free account once she has signed');

  console.log('\n5b. the claim link, the follow-ups, the stop link');
  const go = await worker.default.fetch(new Request(`https://meetlazo.com/join/${I}?t=${inq0.fileToken}&s=day0`), {}, { waitUntil() {} });
  const loc = go.headers.get('location') || '';
  const lq = loc ? new URL(loc).searchParams : new URLSearchParams();
  ok(go.status === 302 && loc.startsWith('https://app.meetlazo.com/?'), 'meetlazo.com/join/ redirects to the app signup');
  ok(lq.get('from') === 'welcome-booked' && lq.get('names') === 'Maya Ortiz' && lq.get('date') === '2027-04-17' && lq.get('utm_content') === 'day0', 'name, date and the step ride along (Auth v22 / Couple v144 read them)');
  ok(lq.get('ref') === `lead:${I}.${inq0.fileToken}` && lq.get('ref').length <= 120, 'ref carries the claim (fits the 120-char signupSource limit)');
  ok(!!(snapOf(inqP).data().joinNudge.clicks || {}).day0, 'click recorded on joinNudge.clicks.day0');
  const bad = await worker.default.fetch(new Request(`https://meetlazo.com/join/${I}?t=wrong&s=day0`), {}, { waitUntil() {} });
  ok(bad.headers.get('location') === 'https://app.meetlazo.com/', 'wrong token: plain app link, nothing filled in');
  // day 3 comes due
  await docRef(inqP).set({ joinNudge: { nextAt: new TS(new Date(Date.now() - 60e3)) } }, { merge: true });
  let n4 = mail.length;
  await join.joinSweep.run({});
  const d3 = mail.slice(n4);
  ok(d3.length === 1 && d3[0].to.includes('maya@example.com') && /wedding website is free/.test(d3[0].subject), 'day 3 email: "' + (d3[0] && d3[0].subject) + '"');
  ok(d3[0] && d3[0].html.includes(`s=day3`), 'its button is the day 3 claim link');
  jn = snapOf(inqP).data().joinNudge;
  ok(jn.next === 'day7' && Math.round((jn.nextAt.toMillis() - Date.now()) / 86400e3) === 4, 'day 7 is next, 4 days later');
  n4 = mail.length; await join.joinSweep.run({});
  ok(mail.length === n4, 'nothing due: the sweep sends nothing');
  if (d3[0]) fs.writeFileSync(path.join(out, '6-day3.html'), d3[0].html);
  // render the rest for review
  const v1 = snapOf('vendors/v1').data(), inqNow = snapOf(inqP).data();
  fs.writeFileSync(path.join(out, '7-day7.html'), J.day7(I, inqNow, v1).html);
  fs.writeFileSync(path.join(out, '8-day14.html'), J.day14(I, inqNow, v1).html);
  fs.writeFileSync(path.join(out, '9-day0-paid.html'), J.day0Paid(I, inqNow, v1, { title: 'Retainer', total: 1200 }, 3600, 'by card').html);

  console.log('\n5c. a website lead who agreed to texts, then taps stop');
  store.set('inquiries/LeadSmsThread000001', { vendorId: 'v1', vendorName: 'Desert Light Films', coupleUid: 'lead_LeadSmsThread000001', coupleName: 'Ava Kim', offPlatform: true, source: 'embed', contact: { name: 'Ava Kim', email: 'ava@example.com', phone: '+16025550199', smsOk: true }, structuredIntent: { weddingDate: '2027-06-05' }, status: 'responded', fileToken: 'AvaTokenAvaTokenAvaToken' });
  store.set('inquiries/LeadSmsThread000001/contracts/k2', { vendorId: 'v1', status: 'signed', title: 'Wedding Film Agreement', values: { total_price: '$3,900' } });
  await cn.coupleOnContract.run(written('inquiries/LeadSmsThread000001/contracts/k2', { status: 'sent' }));
  ok(snapOf('inquiries/LeadSmsThread000001').data().joinNudge.sms === 'pending', 'smsOk lead: one text queued');
  await join.joinSweep.run({});
  ok(texts.length === 1 && texts[0].to === '+16025550199' && texts[0].text.includes('meetlazo.com/join/LeadSmsThread000001') && /STOP/.test(texts[0].text), 'one text with the claim link: "' + (texts[0] && texts[0].text) + '"');
  await join.joinSweep.run({});
  ok(texts.length === 1, 'never a second text');
  const stop = await worker.default.fetch(new Request('https://meetlazo.com/join/LeadSmsThread000001/stop?t=AvaTokenAvaTokenAvaToken'), {}, { waitUntil() {} });
  ok(stop.status === 200 && /No more of these emails/.test(await stop.text()), 'stop link confirms');
  await docRef('inquiries/LeadSmsThread000001').set({ joinNudge: { nextAt: new TS(new Date(Date.now() - 60e3)) } }, { merge: true });
  n4 = mail.length; await join.joinSweep.run({});
  ok(mail.length === n4 && snapOf('inquiries/LeadSmsThread000001').data().joinNudge.nextAt === null, 'after stop: no follow-up, schedule cleared');

  console.log('\n6. the client joins Lazo: only her verified email, matched to the one her vendor has, moves the thread');
  const refOk = `lead:${I}.${inq0.fileToken}`;
  const signup = async (uid, email, verified, src, before) => {
    authUsers[uid] = { uid, email, emailVerified: verified };
    store.set(`users/${uid}`, { email, role: 'couple', ...(src ? { signupSource: src } : {}) });
    await join.onUserClaimLeads.run(written(`users/${uid}`, before));
  };
  const mailTo = (addr, from) => mail.slice(from).filter((m) => m.to.includes(addr));
  const still = () => snapOf(inqP).data().coupleUid === `lead_${I}`;
  // pre-fill for the signup screen
  const info = await join.joinInfo.run({ auth: null, data: { inquiryId: I, t: inq0.fileToken } });
  ok(info.open && info.email === 'maya@example.com' && info.masked === 'm***@example.com' && info.vendorName === 'Desert Light Films', 'joinInfo gives the signup screen the email to pre-fill and lock');
  ok((await join.joinInfo.run({ auth: null, data: { inquiryId: I, t: 'nope' } })).open === false, 'joinInfo with a wrong token gives nothing');

  let n6 = mail.length;
  await signup('ucx', 'maya@example.com', false, null);
  ok(still() && mailTo('maya@example.com', n6).length === 0, 'same email, unverified, no join link: nothing moves, nothing sent');

  n6 = mail.length;
  await signup('ucf', 'other@example.com', true, { ref: `lead:${I}.${'x'.repeat(inq0.fileToken.length)}`, utm_content: 'day3' });
  ok(still() && mail.length === n6, 'forged link code: nothing moves, nothing sent');

  n6 = mail.length;
  await signup('ucm', 'Other@Example.com', true, { ref: refOk, utm_content: 'day3' });
  const wrong = mailTo('Other@Example.com', n6)[0];
  ok(still(), 'verified but different email: nothing moves');
  ok(wrong && /still waiting/.test(wrong.subject) && wrong.html.includes('m***@example.com') && !wrong.html.includes('maya@example.com'), 'she is told which address to use, masked: "' + (wrong && wrong.subject) + '"');
  ok(!!(snapOf(inqP).data().joinNudge.mismatch || {}).ucm, 'mismatch recorded');
  const again6 = await join.claimMyLeadThreads.run({ auth: { uid: 'ucm' }, data: { inquiryId: I, t: inq0.fileToken } });
  ok(again6.status === 'mismatch' && again6.masked === 'm***@example.com' && again6.claimed === 0, 'the app gets status mismatch + the masked address to show');
  ok(mailTo('Other@Example.com', n6).length === 1, 'the hint email goes once per account');
  if (wrong) fs.writeFileSync(path.join(out, '11-wrong-email.html'), wrong.html);

  n6 = mail.length;
  await signup('ucr', 'q7x2k9@privaterelay.appleid.com', true, { ref: refOk, utm_content: 'day3' });
  const relay = mailTo('q7x2k9@privaterelay.appleid.com', n6)[0];
  ok(still() && relay && /Apple’s private email/.test(relay.html) && /email and a password or Google/.test(relay.html), 'Apple private relay: nothing moves, told to use email or Google with her vendor address');
  ok((await join.claimMyLeadThreads.run({ auth: { uid: 'ucr' }, data: { inquiryId: I, t: inq0.fileToken } })).status === 'relay', 'the app gets status relay');

  // the right address, typed with capitals and spaces, not yet confirmed (email + password signup)
  n6 = mail.length;
  await signup('uc', '  Maya@Example.COM ', false, null);
  const ucBefore = snapOf('users/uc').data();
  store.set('users/uc', { ...ucBefore, signupSource: { ref: refOk, utm_source: 'lazo', utm_medium: 'email', utm_campaign: 'join', utm_content: 'day3', from: 'welcome-booked' } });
  await join.onUserClaimLeads.run(written('users/uc', ucBefore));   // FlutterFlow wrote the doc first; signupSource lands after
  const verify = mailTo('  Maya@Example.COM ', n6)[0];
  ok(still(), 'same email (any case, spaces), not verified: nothing moves yet');
  ok(verify && /^Confirm your email/.test(verify.subject) && verify.html.includes('https://verify.example/'), 'she gets a confirm link: "' + (verify && verify.subject) + '"');
  ok(verifyLinks.length && verifyLinks[verifyLinks.length - 1].url === `https://meetlazo.com/join/${I}/done?t=${encodeURIComponent(inq0.fileToken)}`, 'the confirm link comes back to meetlazo.com/join/.../done');
  if (verify) fs.writeFileSync(path.join(out, '10-verify-email.html'), verify.html);
  const early = await worker.default.fetch(new Request(`https://meetlazo.com/join/${I}/done?t=${inq0.fileToken}`), {}, { waitUntil() {} });
  ok(early.status === 200 && /Not confirmed yet/.test(await early.text()) && still(), 'opening /done before confirming: "Not confirmed yet", nothing moves');
  authUsers.uc.emailVerified = true;   // she taps Confirm
  const doneR = await worker.default.fetch(new Request(`https://meetlazo.com/join/${I}/done?t=${inq0.fileToken}`), {}, { waitUntil() {} });
  const claimed = snapOf(inqP).data();
  ok(doneR.status === 302 && doneR.headers.get('location') === 'https://app.meetlazo.com/', 'after confirming, /done opens the app');
  ok(claimed.coupleUid === 'uc' && claimed.offPlatform === false && claimed.claimedFromLead === `lead_${I}`, 'verified + matching email: the thread moves to her account');
  ok(snapOf(`${inqP}/contracts/k1`).data().coupleUid === 'uc' && snapOf(`${inqP}/invoices/inv1`).data().coupleUid === 'uc', 'contract and invoice follow');
  ok(claimed.joinNudge.claimedVia === 'join-link' && claimed.joinNudge.claimedStep === 'day3' && claimed.joinNudge.nextAt === null, 'which step converted her is recorded, follow-ups stop');
  const rb = snapOf('users/uc').data().referredBy || {};
  ok(rb.vendorId === 'v1' && rb.inquiryId === I && rb.step === 'day3' && rb.medium === 'email', 'referring vendor recorded on her user doc');
  ok(!snapOf('users/ucm').data().referredBy && !snapOf('users/ucr').data().referredBy, 'the wrong-email accounts got nothing');
  ok((await http(payments.fileView.run, { query: { inquiry: I, t: inq0.fileToken } })).status === 200, 'the /f/ link keeps working');
  const go2 = await worker.default.fetch(new Request(`https://meetlazo.com/join/${I}?t=${inq0.fileToken}&s=day7`), {}, { waitUntil() {} });
  ok(go2.headers.get('location') === 'https://app.meetlazo.com/', 'after joining, an old join link just opens the app');
  ok((await join.joinInfo.run({ auth: null, data: { inquiryId: I, t: inq0.fileToken } })).open === false, 'and the signup screen no longer pre-fills it');
  await docRef(inqP).set({ joinNudge: { next: 'day7', nextAt: new TS(new Date(Date.now() - 60e3)) } }, { merge: true });
  n6 = mail.length; await join.joinSweep.run({});
  ok(mail.length === n6, 'and no more join emails once she is in');

  // Google with the same address counts as verified: claims straight away
  store.set('inquiries/LeadGoogle0000000001', { vendorId: 'v1', vendorName: 'Desert Light Films', coupleUid: 'lead_LeadGoogle0000000001', offPlatform: true, contact: { name: 'Lee', email: 'lee@gmail.example' }, fileToken: 'LeeTokenLeeTokenLeeToken' });
  await signup('ug', 'Lee@Gmail.example', true, { ref: 'lead:LeadGoogle0000000001.LeeTokenLeeTokenLeeToken', utm_content: 'day0', utm_medium: 'email' });
  ok(snapOf('inquiries/LeadGoogle0000000001').data().coupleUid === 'ug' && snapOf('users/ug').data().referredBy.via === 'join-link', 'Google sign-in with the same email (verified): claimed at once');
  // confirmed somewhere else (not our link): the sweep finishes it
  store.set('inquiries/LeadSweep00000000001', { vendorId: 'v1', vendorName: 'Desert Light Films', coupleUid: 'lead_LeadSweep00000000001', offPlatform: true, contact: { name: 'Kai', email: 'kai@example.com' }, fileToken: 'KaiTokenKaiTokenKaiToken' });
  await signup('uk', 'kai@example.com', false, { ref: 'lead:LeadSweep00000000001.KaiTokenKaiTokenKaiToken', utm_content: 'day7' });
  ok(snapOf('inquiries/LeadSweep00000000001').data().coupleUid === 'lead_LeadSweep00000000001', 'unverified: waiting');
  authUsers.uk.emailVerified = true;
  await join.joinSweep.run({});
  ok(snapOf('inquiries/LeadSweep00000000001').data().coupleUid === 'uk' && snapOf('users/uk').data().referredBy.step === 'day7', 'confirmed later: the hourly sweep finishes the claim');
  // a verified email that matches still claims without the link
  store.set('inquiries/LeadVerified00000001', { vendorId: 'v1', vendorName: 'Desert Light Films', coupleUid: 'lead_LeadVerified00000001', offPlatform: true, contact: { name: 'Jo', email: 'jo@example.com' }, fileToken: 'JoTokenJoTokenJoTokenJo' });
  await signup('uj', 'jo@example.com', true, null);
  ok(snapOf('inquiries/LeadVerified00000001').data().coupleUid === 'uj' && snapOf('users/uj').data().referredBy.via === 'email-match', 'verified email match without the link: claimed, referral recorded');

  console.log('\n6b. once verify.js ships: the signup code proves the email, no confirm link from join.js');
  process.env.JOIN_VERIFY_LINK = 'off';
  store.set('inquiries/LeadCode000000000001', { vendorId: 'v1', vendorName: 'Desert Light Films', coupleUid: 'lead_LeadCode000000000001', offPlatform: true, contact: { name: 'Rae', email: 'rae@example.com' }, fileToken: 'RaeTokenRaeTokenRaeToken' });
  const n7 = mail.length; const vl = verifyLinks.length;
  await signup('ur', 'Rae@Example.com', false, { ref: 'lead:LeadCode000000000001.RaeTokenRaeTokenRaeToken', utm_content: 'day3', utm_medium: 'email' });
  ok(snapOf('inquiries/LeadCode000000000001').data().coupleUid === 'lead_LeadCode000000000001' && mail.length === n7 && verifyLinks.length === vl, 'unverified at signup: nothing moves and join.js sends no link (her only email is the code)');
  ok(!!snapOf('inquiries/LeadCode000000000001').data().joinNudge.pending.ur, 'she is remembered as waiting');
  const { claimLeadThreads } = require('../join.js');
  const pre = await claimLeadThreads('ur');
  ok(pre.status === 'verify' && pre.claimed === 0, 'claimLeadThreads before the code: status verify, nothing moves');
  authUsers.ur.emailVerified = true;   // verifyEmailCode: admin.auth().updateUser(uid, { emailVerified: true })
  const post = await claimLeadThreads('ur');
  ok(post.status === 'claimed' && snapOf('inquiries/LeadCode000000000001').data().coupleUid === 'ur', 'claimLeadThreads after the code: the thread moves');
  ok(snapOf('users/ur').data().referredBy.step === 'day3' && snapOf('users/ur').data().referredBy.via === 'join-link', 'referral and converting step recorded');
  store.set('inquiries/LeadCode000000000002', { vendorId: 'v1', vendorName: 'Desert Light Films', coupleUid: 'lead_LeadCode000000000002', offPlatform: true, contact: { name: 'Sol', email: 'sol@example.com' }, fileToken: 'SolTokenSolTokenSolToken' });
  await signup('us2', 'notsol@example.com', true, { ref: 'lead:LeadCode000000000002.SolTokenSolTokenSolToken' });
  ok(snapOf('inquiries/LeadCode000000000002').data().coupleUid === 'lead_LeadCode000000000002', 'a verified but different email still moves nothing');
  process.env.JOIN_VERIFY_LINK = 'on';

  console.log('\n7. Lazo couples are unchanged');
  store.set('inquiries/on1', { vendorId: 'v1', coupleUid: 'uc', coupleName: 'Maya', status: 'responded', fileToken: 'tok_on1' });
  store.set('inquiries/on1/invoices/i9', { vendorId: 'v1', coupleUid: 'uc', title: 'Balance', total: 300, status: 'sent' });
  ok((await http(payments.payCheckout.run, { query: { inquiry: 'on1', invoice: 'i9' } })).status === 200, 'couple app call without a token still works (PAY_REQUIRE_AUTH off)');
  const n3 = mail.length;
  await cn.coupleOnInvoice.run(written('inquiries/on1/invoices/i9', undefined));
  const cm = mail.slice(n3)[0];
  ok(cm && cm.html.includes('https://app.meetlazo.com/?thread=on1') && !cm.html.includes('/f/on1'), 'a Lazo couple still gets the app link');

  console.log(`\n${pass} passed, ${fail} failed. ${mail.length} emails captured; HTML in ${out}`);
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
