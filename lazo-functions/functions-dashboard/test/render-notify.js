// Renders every couple-notify email with fake Firestore data, writing HTML to an output folder.
// No network, no Firebase: firebase-admin and the trigger factories are stubbed before the module loads.
//   node test/render-notify.js <outDir>
'use strict';
const path = require('path'); const fs = require('fs');
const out = process.argv[2] || path.join(__dirname, 'out'); fs.mkdirSync(out, { recursive: true });

// ---- fakes
const docs = {};  // path -> data
const sub = {};   // parent path -> { id: data }
const TS = (d) => ({ toDate: () => d });
const now = new Date(); const wd = new Date(Date.now() + 148 * 86400e3);
docs['couples/c1'] = { names: 'Jordan & Sam', metroId: 'phoenix', weddingDate: TS(wd) };
docs['users/c1'] = { email: 'jordan@example.com', display_name: 'Jordan Rivera', role: 'couple' };
docs['vendors/v1'] = { name: 'Desert Light Photography', category: 'wedding-photographers', categories: ['wedding-photographers'], publicEmail: 'hello@desertlight.example', brand: { primary: '#2B3A55', accent: '#E3B873' }, logoUrl: '' };
docs['inquiries/i1'] = { coupleUid: 'c1', vendorId: 'v1', vendorName: 'Desert Light Photography', vendorCategory: 'wedding-photographers', coupleName: 'Jordan & Sam', status: 'responded', structuredIntent: { weddingDate: wd.toISOString().slice(0, 10) } };
sub['couples/c1/plan'] = { 'wedding-photographers': { status: 'booked' }, 'wedding-venues': { status: 'booked' }, 'wedding-djs': { status: 'needed' }, 'wedding-florists': { status: 'researching' } };
sub['inquiries/i1/invoices'] = { inv1: { title: 'Retainer', total: 1200, status: 'paid' }, inv2: { title: 'Balance', total: 2300, status: 'sent' } };
const snap = (p, data, id) => ({ exists: data != null, id: id || p.split('/').pop(), data: () => data, get: (k) => data && data[k], ref: refOf(p) });
function refOf(p) { return { path: p, id: p.split('/').pop(), parent: { get: async () => ({ forEach: (f) => Object.entries(sub[p.split('/').slice(0, -1).join('/')] || {}).forEach(([id, d]) => f(snap(id, d, id))) }) }, update: async () => {}, set: async () => {} }; }
const col = (p) => ({ doc: (id) => ({ get: async () => snap(`${p}/${id}`, docs[`${p}/${id}`] || null, id), collection: (c) => col(`${p}/${id}/${c}`) }), where: () => ({ limit: () => ({ get: async () => ({ empty: true, forEach: () => {} }) }), get: async () => ({ forEach: () => {} }) }), get: async () => ({ forEach: (f) => Object.entries(sub[p] || {}).forEach(([id, d]) => f(snap(`${p}/${id}`, d, id))) }) });
const fakeAdmin = { firestore: Object.assign(() => ({ collection: (c) => col(c), runTransaction: async (fn) => fn({ get: async (r) => ({ exists: true, get: () => undefined }), update: () => {} }) }), { FieldValue: { serverTimestamp: () => 'ts', delete: () => 'del' } }), auth: () => ({ getUser: async () => ({ email: '' }) }) };
require.cache[require.resolve('firebase-admin')] = { id: 'firebase-admin', filename: 'firebase-admin', loaded: true, exports: fakeAdmin };
const handlers = {}; const mk = (kind) => (opts, fn) => { handlers[opts.document + '|' + kind] = fn; return { _doc: opts.document, _kind: kind, run: fn }; };
require.cache[require.resolve('firebase-functions/v2/firestore')] = { id: 'ff', filename: 'ff', loaded: true, exports: { onDocumentCreated: mk('created'), onDocumentWritten: mk('written'), onDocumentUpdated: mk('updated') } };
const sent = []; global.fetch = async (url, o) => { const b = JSON.parse(o.body); sent.push(b); return { ok: true, text: async () => '' }; };

const cn = require('../couple-notify.js')({ value: () => 'test' });
const ev = (params, data, before) => ({ params, data: before === undefined ? { data: () => data, ref: refOf(subPath(params)) } : { before: { exists: !!before, data: () => before }, after: { exists: true, data: () => data, ref: refOf(subPath(params)) } } });
const subPath = (params) => { const k = Object.keys(params); const sub = k[1]; const col = sub === 'invoiceId' ? 'invoices' : sub === 'contractId' ? 'contracts' : sub === 'proposalId' ? 'proposals' : sub === 'qId' ? 'questionnaires' : 'messages'; return `inquiries/${params.inquiryId}/${col}/${params[sub]}`; };
const evUpd = (params, before, after) => ({ params, data: { before: { data: () => before }, after: { data: () => after, ref: refOf('inquiries/' + params.inquiryId) } } });

(async () => {
  const P = { inquiryId: 'i1' };
  await cn.coupleOnMessage.run(ev({ ...P, messageId: 'm1' }, { senderRole: 'vendor', text: 'Jordan, Sam - we loved meeting you both. I held October 3 for you and sent the proposal over; shout if you want the second shooter added.' }));
  await cn.coupleOnMessage.run(ev({ ...P, messageId: 'm2' }, { senderRole: 'vendor', text: 'A first look at your day', sneakPeek: [{ url: 'https://meetlazo.com/assets/photos/atmo-veil.jpg', moment: 'Getting ready' }, { url: 'https://meetlazo.com/assets/photos/atmo-rings.jpg', moment: 'Rings' }, { url: 'https://meetlazo.com/assets/photos/atmo-firstdance.jpg', moment: 'First dance' }] }));
  await cn.coupleOnMessage.run(ev({ ...P, messageId: 'm3' }, { senderRole: 'vendor', text: '', teaser: { url: 'https://vimeo.com/123', host: 'Vimeo' } }));
  await cn.coupleOnProposal.run(ev({ ...P, proposalId: 'p1' }, { title: 'Full Day Collection', price: '4,200', includes: '8 hours, two photographers, online gallery, 400+ edited images', note: 'This is the collection most of our October couples choose. Happy to tailor it.', validUntil: TS(new Date(Date.now() + 14 * 86400e3)) }));
  await cn.coupleOnQuestionnaire.run(ev({ ...P, qId: 'q1' }, { title: 'Your day, in detail', questions: [1, 2, 3, 4, 5, 6, 7] }));
  await cn.coupleOnInvoice.run(ev({ ...P, invoiceId: 'inv2' }, { title: 'Balance', total: 2300, status: 'sent', dueDate: TS(new Date(Date.now() + 30 * 86400e3)), lineItems: [{ label: 'Full Day Collection balance', amount: 2100 }, { label: 'Second photographer', amount: 200 }] }, {}));
  await cn.coupleOnInvoice.run(ev({ ...P, invoiceId: 'inv1' }, { title: 'Retainer', total: 1200, status: 'paid', paidVia: 'card', paidAt: TS(now) }, { status: 'sent' }));
  await cn.coupleOnContract.run(ev({ ...P, contractId: 'k1' }, { title: 'Wedding Photography Service Agreement', status: 'signed', values: { total_price: 3500 } }, { status: 'sent' }));
  await cn.coupleOnInquiry.run(evUpd(P, { status: 'responded' }, { ...docs['inquiries/i1'], status: 'booked' }));
  await cn.coupleOnInquiry.run(evUpd(P, { status: 'booked' }, { ...docs['inquiries/i1'], status: 'booked', deliveredAt: TS(now) }));
  await cn.coupleOnInquiry.run(evUpd(P, { status: 'booked' }, { ...docs['inquiries/i1'], status: 'responded', unbookedAt: TS(now), unbookLabel: 'Scheduling conflict' }));
  const names = ['reply', 'sneakpeek', 'teaser', 'proposal', 'questionnaire', 'invoice', 'receipt', 'signed', 'booked', 'delivered', 'released'];
  sent.forEach((m, i) => { fs.writeFileSync(path.join(out, `notify_${names[i] || i}.html`), m.html); console.log((names[i] || i).padEnd(14), '|', m.from.padEnd(44), '|', m.subject); });
  console.log(sent.length, 'emails rendered to', out);
})().catch((e) => { console.error(e); process.exit(1); });
