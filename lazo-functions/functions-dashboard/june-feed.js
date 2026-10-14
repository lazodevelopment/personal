// functions-dashboard/june-feed.js
// Build ID: JC-LAZO-FNDASH-1014-027
//
// JUNE'S NOTICES, EVEN WITH THE APP CLOSED. The dashboards announce what matters
// while they are open; this is the same news from the server, so it reaches the
// phone as a push and waits in June's feed (the bell) for whoever missed it.
//
// Every notice lands in users/{uid}/juneFeed/{id} = {title, text, kind, thread?,
// open?, at, read:false} and is pushed to users/{uid}/fcm_tokens (quiet hours
// 22:00-07:00 Phoenix hold the push, never the feed entry).
//
//   feedInquiryChanged   inquiries/{id} updated: booked -> vendor + couple,
//                        contract sent -> couple, contract signed -> vendor,
//                        invoice sent -> couple
//   feedInvoicePaid      inquiries/{id}/invoices/{inv} updated to paid -> vendor
//   feedReview           reviews/{id} created -> vendor
//   feedConsult          consults/{id} written to booked -> vendor
//   feedRsvp             weddingSites/{slug}/rsvps/{id} created -> couple
//   feedPartner          couples/{cid}/activity/{id} created -> the other partner(s)
//   feedPaymentsDue      09:00 Phoenix daily: invoices due within three days -> couple
//
// june-push.js (new lead, new message, the morning line, the worker's door) writes
// to the same feed through feedTo().
// Practice couples (demo / practice / preview) are skipped everywhere.

'use strict';

const { onDocumentCreated, onDocumentUpdated, onDocumentWritten } = require('firebase-functions/v2/firestore');
const { onSchedule } = require('firebase-functions/v2/scheduler');
const admin = require('firebase-admin');

const db = () => admin.firestore();
const str = (v) => (v == null ? '' : String(v));
const clip = (s, n) => str(s).trim().slice(0, n);
const phoenixHour = () => +new Date().toLocaleString('en-US', { timeZone: 'America/Phoenix', hour: 'numeric', hour12: false }) % 24;
const quiet = () => { const h = phoenixHour(); return h >= 22 || h < 7; };
const practice = (d) => !d || d.demo === true || d.practice === true || d.preview === true;
const money = (n) => (typeof n === 'number' && isFinite(n) ? '$' + Math.round(n).toLocaleString('en-US') : '');
const MO = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const WD = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

function toDate(v) {
  if (!v) return null;
  if (v.toDate) return v.toDate();
  const d = new Date(str(v).length === 10 ? str(v) + 'T12:00:00' : str(v));
  return isNaN(d) ? null : d;
}
function longDate(v) { const d = toDate(v); return d ? `${MO[d.getMonth()]} ${d.getDate()}` : ''; }
function weddingOf(d) { const si = d.structuredIntent || {}; return longDate(si.weddingDate || d.weddingDate); }

async function tokensFor(uid) {
  const snap = await db().collection('users').doc(uid).collection('fcm_tokens').get();
  const out = [];
  snap.forEach((d) => { const t = str(d.get('fcm_token')); if (t) out.push({ ref: d.ref, token: t }); });
  return out;
}

async function pushOnly(uid, { title, text, thread, open, tag }) {
  const toks = await tokensFor(uid);
  if (!toks.length) return 0;
  const data = { from: 'june', tag: tag || '', thread: thread || '', open: open || (thread ? 'thread' : 'june') };
  const res = await admin.messaging().sendEachForMulticast({
    tokens: toks.map((t) => t.token),
    notification: { title: clip(title, 80), body: clip(text, 180) },
    data: Object.fromEntries(Object.entries(data).map(([k, v]) => [k, str(v)])),
    android: { priority: 'high', notification: { channelId: 'june', tag: tag || undefined, sound: 'default' } },
    apns: { payload: { aps: { sound: 'default', 'thread-id': tag || 'june', badge: 1 } } },
  });
  const dead = [];
  res.responses.forEach((r, i) => {
    const code = r.error && r.error.code;
    if (code === 'messaging/registration-token-not-registered' || code === 'messaging/invalid-registration-token') dead.push(toks[i].ref);
  });
  await Promise.all(dead.map((ref) => ref.delete().catch(() => {})));
  return res.successCount;
}

/** the feed entry only (june-push.js pushes on its own) */
async function feedTo(uid, { title, text, kind = 'note', thread = '', open = '' }) {
  if (!uid || !text) return;
  try {
    await db().collection('users').doc(uid).collection('juneFeed').add({
      title: clip(title, 120), text: clip(text, 400), kind, thread: str(thread), open: str(open),
      at: admin.firestore.FieldValue.serverTimestamp(), read: false,
    });
  } catch (e) { console.log('feedTo', uid, e.message); }
}

/** a notice: the feed, and a push unless it is quiet hours (urgent ignores them) */
async function notify(uids, n, { urgent = false } = {}) {
  for (const uid of new Set(uids.filter(Boolean))) {
    await feedTo(uid, n);
    if (quiet() && !urgent) continue;
    try { await pushOnly(uid, n); } catch (e) { console.log('notify push', uid, e.message); }
  }
}

async function vendorPeople(vendorId) {
  if (!vendorId) return [];
  const snap = await db().collection('users').where('vendorId', '==', vendorId).get();
  return snap.docs.map((d) => d.id);
}

async function couplePeople(cid) {
  if (!cid) return [];
  const snap = await db().collection('users').where('coupleUid', '==', cid).get();
  return [cid, ...snap.docs.map((d) => d.id)];
}

module.exports = () => {
  const feedInquiryChanged = onDocumentUpdated({ document: 'inquiries/{id}', region: 'us-central1', memory: '256MiB' }, async (event) => {
    const b = event.data.before.data() || {}, a = event.data.after.data() || {};
    if (practice(a)) return;
    const id = event.params.id;
    const couple = str(a.coupleName) || 'A couple';
    const vendor = str(a.vendorName) || 'Your vendor';
    const date = weddingOf(a);
    if (str(a.status) === 'booked' && str(b.status) !== 'booked') {
      await notify(await vendorPeople(str(a.vendorId)), { title: `${couple} booked you`, text: `${couple} booked you${date ? ' for ' + date : ''}. Congratulations!`, kind: 'booked', thread: id }, { urgent: true });
      await notify(await couplePeople(str(a.coupleUid)), { title: `You booked ${vendor}`, text: `You booked ${vendor}. One more off the list!`, kind: 'booked', thread: id });
    }
    if (str(a.contractStatus) === 'sent' && str(b.contractStatus) !== 'sent') {
      await notify(await couplePeople(str(a.coupleUid)), { title: 'A contract to sign', text: `${vendor} sent you a contract to sign.`, kind: 'contract', thread: id });
    }
    if (str(a.contractStatus) === 'signed' && str(b.contractStatus) !== 'signed') {
      await notify(await vendorPeople(str(a.vendorId)), { title: 'Contract signed', text: `${couple} signed their contract.`, kind: 'signed', thread: id });
    }
    const inv = str(a.invoiceStatus);
    if ((inv === 'sent' || inv === 'due') && str(b.invoiceStatus) !== inv) {
      await notify(await couplePeople(str(a.coupleUid)), { title: `Invoice from ${vendor}`, text: `${vendor} sent you an invoice.`, kind: 'invoice', thread: id });
    }
  });

  const feedInvoicePaid = onDocumentUpdated({ document: 'inquiries/{id}/invoices/{inv}', region: 'us-central1', memory: '256MiB' }, async (event) => {
    const b = event.data.before.data() || {}, a = event.data.after.data() || {};
    if (str(a.status) !== 'paid' || str(b.status) === 'paid' || practice(a)) return;
    const inq = (await db().collection('inquiries').doc(event.params.id).get()).data() || {};
    if (practice(inq)) return;
    const couple = str(inq.coupleName) || 'A couple';
    const what = str(a.title);
    await notify(await vendorPeople(str(a.vendorId || inq.vendorId)), { title: `${couple} paid`, text: `${couple} just paid${money(a.total) ? ' ' + money(a.total) : ''}${what ? ' for ' + what : ''}.`, kind: 'paid', thread: event.params.id });
  });

  const feedReview = onDocumentCreated({ document: 'reviews/{id}', region: 'us-central1', memory: '256MiB' }, async (event) => {
    const r = event.data && event.data.data();
    if (!r || practice(r)) return;
    const stars = Number(r.rating) || 0;
    const who = str(r.coupleName);
    const txt = clip(r.text, 110);
    await notify(await vendorPeople(str(r.vendorId)), { title: stars ? `New ${stars}-star review` : 'New review', text: `New ${stars ? stars + '-star ' : ''}review${who ? ' from ' + who : ''}.${txt ? ' "' + txt + '"' : ''}`, kind: 'review', open: 'reviews' });
  });

  const feedConsult = onDocumentWritten({ document: 'consults/{id}', region: 'us-central1', memory: '256MiB' }, async (event) => {
    const b = event.data.before && event.data.before.exists ? event.data.before.data() : {};
    const a = event.data.after && event.data.after.exists ? event.data.after.data() : null;
    if (!a || str(a.status) !== 'booked' || str(b.status) === 'booked' || practice(a)) return;
    const st = toDate(a.startAt);
    if (!st || st < new Date()) return;
    const who = str(a.coupleName || a.name || a.guestName) || 'Someone';
    const kind = str(a.typeLabel) || 'call';
    const local = new Date(st.toLocaleString('en-US', { timeZone: str(a.tz) || 'America/Phoenix' }));
    const h = local.getHours(), mi = local.getMinutes();
    const time = `${h % 12 || 12}${mi ? ':' + String(mi).padStart(2, '0') : ''} ${h < 12 ? 'am' : 'pm'}`;
    await notify(await vendorPeople(str(a.vendorId)), { title: 'Consult booked', text: `${who} booked ${/^[aeiou]/i.test(kind) ? 'an' : 'a'} ${kind.toLowerCase()} for ${WD[local.getDay()]}, ${MO[local.getMonth()]} ${local.getDate()} at ${time}.`, kind: 'consult', thread: str(a.inquiryId) });
  });

  const feedRsvp = onDocumentCreated({ document: 'weddingSites/{slug}/rsvps/{id}', region: 'us-central1', memory: '256MiB' }, async (event) => {
    const r = event.data && event.data.data();
    if (!r) return;
    const site = (await db().collection('weddingSites').doc(event.params.slug).get()).data() || {};
    const cid = str(site.coupleUid);
    if (!cid) return;
    const who = str(r.name) || 'A guest';
    const yes = str(r.attending || 'yes') === 'yes';
    const plus = Number(r.plusOnes) || 0;
    await notify(await couplePeople(cid), { title: yes ? 'A new RSVP' : 'An RSVP', text: yes ? `${who} RSVP'd yes${plus ? ', plus ' + plus : ''}!` : `${who} sent their regrets.`, kind: 'rsvp', open: 'guests' });
  });

  const feedPartner = onDocumentCreated({ document: 'couples/{cid}/activity/{id}', region: 'us-central1', memory: '256MiB' }, async (event) => {
    const a = event.data && event.data.data();
    if (!a || !a.text) return;
    const by = str(a.by);
    const people = (await couplePeople(event.params.cid)).filter((u) => u !== by);
    await notify(people, { title: str(a.byName) || 'Your partner', text: str(a.text), kind: 'partner', open: str(a.open) });
  });

  const feedPaymentsDue = onSchedule({ schedule: '0 9 * * *', timeZone: 'America/Phoenix', memory: '512MiB', timeoutSeconds: 300 }, async () => {
    const snap = await db().collectionGroup('invoices').where('status', 'in', ['sent', 'due']).get();
    const now = Date.now();
    let n = 0;
    for (const doc of snap.docs) {
      const m = doc.data() || {};
      if (practice(m) || m.dueNudgedAt) continue;
      const due = toDate(m.dueDate);
      if (!due) continue;
      const days = Math.floor((due.getTime() - now) / 86400e3);
      if (days < 0 || days > 3) continue;
      const inqRef = doc.ref.parent.parent;
      const inq = inqRef ? (await inqRef.get()).data() || {} : {};
      if (practice(inq) || !inq.coupleUid) continue;
      const vendor = str(inq.vendorName) || 'your vendor';
      const when = days === 0 ? 'today' : days === 1 ? 'tomorrow' : `on ${WD[due.getDay()]}`;
      await notify(await couplePeople(str(inq.coupleUid)), { title: 'Payment due soon', text: `Your ${money(m.total) ? money(m.total) + ' ' : ''}payment to ${vendor} is due ${when}.`, kind: 'due', thread: inqRef ? inqRef.id : '' });
      await doc.ref.set({ dueNudgedAt: admin.firestore.FieldValue.serverTimestamp() }, { merge: true }).catch(() => {});
      n++;
    }
    console.log('feedPaymentsDue', n);
  });

  return { feedInquiryChanged, feedInvoicePaid, feedReview, feedConsult, feedRsvp, feedPartner, feedPaymentsDue };
};

module.exports.feedTo = feedTo;

// END OF FILE - JC-LAZO-FNDASH-1014-027
