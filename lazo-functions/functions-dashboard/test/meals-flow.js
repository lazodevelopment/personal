// Check of meals.js mealCountReminders (JC-LAZO-FNDASH-1016-MEALS) with no
// emulator: firebase-admin and the scheduler are replaced by small fakes
// before the module loads, fetch (Resend) is stubbed, the real handler runs.
//   node test/meals-flow.js        (from functions-dashboard)
'use strict';
const path = require('path');
const Module = require('module');

const DAY = 864e5;
const store = new Map();   // path -> data
class TS { constructor(d) { this.d = new Date(d); } toDate() { return new Date(this.d); } }
const ts = (d) => new TS(d);

function docRef(p) {
  const parts = p.split('/');
  return {
    id: parts[parts.length - 1], path: p,
    get parent() { return { parent: parts.length > 2 ? docRef(parts.slice(0, -2).join('/')) : null }; },
    async get() { const d = store.get(p); return { exists: d !== undefined, id: parts[parts.length - 1], data: () => d, get: (k) => (d || {})[k] }; },
    async set(v, o) { store.set(p, o && o.merge ? { ...(store.get(p) || {}), ...v } : v); },
    collection: (c) => colRef(`${p}/${c}`),
  };
}
function docsUnder(prefix, filter) {
  const out = [];
  for (const [p, d] of store) {
    if (!filter(p)) continue;
    out.push({ id: p.split('/').pop(), ref: docRef(p), data: () => d, get: (k) => d[k] });
  }
  return out;
}
function colRef(c) {
  const depth = c.split('/').length + 1;
  const q = (preds) => ({
    where: (f, op, v) => q([...preds, (d) => d[f] === v]),
    limit: () => q(preds),
    async get() {
      const docs = docsUnder(c, (p) => p.startsWith(c + '/') && p.split('/').length === depth).filter((s) => preds.every((f) => f(s.data())));
      return { docs, forEach: (fn) => docs.forEach(fn), size: docs.length };
    },
  });
  return { doc: (id) => docRef(`${c}/${id}`), async add(v) { const id = 'a' + store.size; store.set(`${c}/${id}`, v); return docRef(`${c}/${id}`); }, ...q([]) };
}
const fs = {
  collection: (c) => colRef(c),
  collectionGroup: (g) => ({ async get() { const docs = docsUnder('', (p) => { const s = p.split('/'); return s.length % 2 === 0 && s[s.length - 2] === g; }); return { docs }; } }),
};
const admin = { firestore: Object.assign(() => fs, { FieldValue: { serverTimestamp: () => ts(new Date()) } }), messaging: () => ({ sendEachForMulticast: async () => ({ responses: [], successCount: 0 }) }) };

const origLoad = Module._load;
Module._load = function (req, parent, isMain) {
  if (req === 'firebase-admin') return admin;
  if (req === 'firebase-functions/v2/scheduler') return { onSchedule: (opts, fn) => fn };
  if (req === 'firebase-functions/v2/firestore') return { onDocumentCreated: (o, f) => f, onDocumentUpdated: (o, f) => f, onDocumentWritten: (o, f) => f };
  return origLoad.apply(this, arguments);
};
const mails = [];
global.fetch = async (url, o) => { mails.push(JSON.parse(o.body)); return { ok: true, text: async () => '' }; };

const meals = require(path.join(__dirname, '..', 'meals.js'))({ value: () => 'test-key' });

let fails = 0;
const ok = (c, msg) => { console.log(`${c ? 'ok  ' : 'FAIL'} ${msg}`); if (!c) fails++; };

(async () => {
  const now = Date.now();
  // A: vendor set the date 7 days out -> couple reminded once
  store.set('inquiries/A', { coupleUid: 'c1', vendorId: 'v1', vendorName: 'Harvest Catering', coupleName: 'Sam & Alex' });
  store.set('inquiries/A/shared/meals', { kind: 'meals', finalDue: ts(now + 7 * DAY), sentAt: ts(now - 10 * DAY) });
  store.set('couples/c1', { names: 'Sam & Alex' });
  store.set('users/c1', { email: 'sam@example.com' });
  store.set('couples/c1/guests/g1', { rsvp: 'yes', meal: 'Chicken', plusOnes: 1 });   // plus-one has no meal
  store.set('couples/c1/guests/g2', { rsvp: 'pending', plusOnes: 2 });
  // B: no date set, wedding in 16 days -> default due in 2 days -> reminded
  store.set('inquiries/B', { coupleUid: 'c2', vendorId: 'v2', vendorName: 'The Barn' });
  store.set('inquiries/B/shared/meals', { kind: 'meals', weddingDate: ts(now + 16 * DAY), sentAt: ts(now - 3 * DAY) });
  store.set('users/c2', { email: 'jo@example.com' });
  // C: vendor date was yesterday, last send 9 days before -> vendor told
  store.set('inquiries/C', { coupleUid: 'c3', vendorId: 'v3', vendorName: 'Fig Kitchen', coupleName: 'Jo & Lee' });
  store.set('inquiries/C/shared/meals', { kind: 'meals', finalDue: ts(now - DAY), sentAt: ts(now - 10 * DAY) });
  store.set('users/u3', { vendorId: 'v3' });
  // D: practice couple -> skipped; E: off-platform lead -> skipped
  store.set('inquiries/D', { coupleUid: 'c4', demo: true });
  store.set('inquiries/D/shared/meals', { kind: 'meals', finalDue: ts(now + 7 * DAY) });
  store.set('inquiries/E', { coupleUid: 'lead_x' });
  store.set('inquiries/E/shared/meals', { kind: 'meals', finalDue: ts(now + 7 * DAY) });

  await meals.mealCountReminders();
  const feedOf = (uid) => docsUnder('', (p) => p.startsWith(`users/${uid}/juneFeed/`)).map((s) => s.data());
  ok(feedOf('c1').length === 1 && /Harvest Catering needs your final meal count/.test(feedOf('c1')[0].text), 'A: couple feed item');
  ok(/3 guests haven’t replied and 1 guest hasn’t picked a meal/.test(feedOf('c1')[0].text), 'A: live gaps from the guest list: ' + (feedOf('c1')[0] || {}).text);
  ok(mails.some((m) => m.to.includes('sam@example.com') && /Harvest Catering/.test(m.subject)), 'A: couple email');
  ok(store.get('inquiries/A/shared/meals').remind7At, 'A: stamped remind7At');
  ok(feedOf('c2').length === 1 && /in two days/.test(feedOf('c2')[0].text), 'B: default date (wedding - 14) reminds at 2 days');
  ok(feedOf('u3').length === 1 && /was due/.test(feedOf('u3')[0].text), 'C: vendor told the day after');
  ok(feedOf('c4').length === 0 && feedOf('lead_x').length === 0, 'D/E: practice and lead skipped');

  const before = mails.length;
  await meals.mealCountReminders();
  ok(mails.length === before && feedOf('c1').length === 1, 'second run sends nothing new');

  // the vendor moves A's date 2 days out -> re-arms
  store.set('inquiries/A/shared/meals', { ...store.get('inquiries/A/shared/meals'), finalDue: ts(now + 2 * DAY) });
  await meals.mealCountReminders();
  ok(feedOf('c1').length === 2, 'moved date re-arms the reminder');

  console.log(fails ? `\n${fails} FAILED` : '\nall passed');
  process.exit(fails ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
