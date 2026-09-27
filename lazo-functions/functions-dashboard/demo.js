// functions-dashboard/demo.js
// Build ID: JC-LAZO-FNDASH-0913-018
//
// THE PRACTICE COUPLE. When a vendor finishes (or skips) the tour, "Jordan &
// Sam" send an inquiry. It is labelled a practice couple everywhere - in the
// first message, in a pinned system note, in the thread chip, in the alert
// email and text - and June plays them: every vendor action in that thread
// gets an in-character reply, plus a short coaching line, until the vendor
// has done the whole booking. Nothing in it counts.
//
//   demoStart      callable {vendorId}  create the thread (once per vendor;
//                  again after demoEnd) + the "your practice lead is here" alert
//   demoEnd        callable {vendorId}  delete the thread and everything under it
//   onDemoActivity trigger inquiries/{id}/{sub}/{doc} created - reacts when
//                  the parent inquiry has demo == true:
//                    messages (vendor)  -> reply as Jordan (Claude) + coach note
//                    proposals          -> accepted + reply
//                    contracts          -> signed + reply (retainer invoice
//                                          follows through the normal path)
//                    invoices           -> paid via 'demo' + reply
//                    questionnaires     -> answered + reply
//                    tasks (couple)     -> done + reply
//   demoSweep      daily: threads older than 14 days are deleted
//
// Walls: demo: true on the inquiry and on every doc June writes; coupleUid is
// demo_<vendorId> (no user can match it); offPlatform is false so the lead
// SMS/email path never fires to a "couple"; source 'demo'. Money card, sweeps,
// June-for-vendors and the MCP filter on demo. Marking the practice couple
// booked is allowed (it is part of the lesson); demoEnd cleans up.

'use strict';

const { onCall, HttpsError } = require('firebase-functions/v2/https');
const { onDocumentCreated } = require('firebase-functions/v2/firestore');
const { onSchedule } = require('firebase-functions/v2/scheduler');
const { defineSecret } = require('firebase-functions/params');
const admin = require('firebase-admin');

const TELNYX_API_KEY = defineSecret('TELNYX_API_KEY');
const TELNYX_FROM = defineSecret('TELNYX_FROM');
const APP = 'https://app.meetlazo.com/dashboard';
const FROM = 'Lazo <hello@meetlazo.com>';
const MODEL = 'claude-sonnet-4-6';

const db = () => admin.firestore();
const { FieldValue, Timestamp } = admin.firestore;
const str = (v) => (v == null ? '' : String(v));
const emailOk = (e) => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(str(e));
const e164 = (raw) => { const d = str(raw).replace(/[^\d]/g, ''); return d.length === 10 ? '+1' + d : (d.length === 11 && d.startsWith('1')) ? '+' + d : ''; };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const COUPLE = 'Jordan & Sam';
const PRACTICE_NOTE = 'PRACTICE COUPLE - not a real inquiry. Jordan & Sam are played by June so you can try every part of the dashboard: reply, send a proposal, a contract, an invoice or payment plan, a questionnaire, a booking link, mark them booked. Nothing in this thread counts toward your stats or money. Delete it any time from the banner at the top.';

const VENUES = {
  'phoenix': 'The Farm at South Mountain', 'tucson': 'Hacienda del Sol', 'denver': 'Blanc Denver', 'dallas-fort-worth': 'The Grand Ivory',
  'houston': 'The Astorian', 'austin': 'Camp Lucy', 'san-antonio': 'The Veranda', 'las-vegas': 'Red Rock Resort', 'atlanta': 'Summerour Studio',
  'nashville': 'The Cordelle', 'chicago': 'Salvage One', 'los-angeles': 'Calamigos Ranch', 'san-diego': 'The Lodge at Torrey Pines',
  'miami': 'The Deering Estate', 'orlando': 'Bella Collina', 'tampa': 'The Orlo', 'charlotte': 'The Ivy Place', 'raleigh-durham': 'The Meadows at Firefly Farm',
  'seattle': 'Sodo Park', 'salt-lake-city': 'Log Haven', 'new-york-city': 'The Foundry', 'boston': 'The Liberty Hotel', 'philadelphia': 'Cescaphe Ballroom',
  'washington-dc': 'Dock 5', 'san-francisco-bay': 'Nestldown', 'portland': 'The Evergreen', 'minneapolis': 'Machine Shop', 'st-louis': 'The Jewel Box',
  'kansas-city': 'The Guild', 'columbus': 'The Vue', 'new-orleans': 'Il Mercato', 'indianapolis': 'The Biltwell', 'sacramento': 'The Maples',
  'jacksonville': 'The Glass Factory', 'charleston': 'Magnolia Plantation', 'savannah': 'The Kehoe House', 'detroit': 'The Eastern', 'pittsburgh': 'The Pennsylvanian',
  'cincinnati': 'Rhinegeist Brewery', 'cleveland': 'The Madison', 'milwaukee': 'The Ivy House', 'richmond': 'The Estate at River Run', 'virginia-beach': 'The Cavalier',
  'louisville': 'The Speed Art Museum', 'memphis': 'The Cadre Building',
};
const CAT_LINE = {
  'wedding-photographers': 'We love candid, warm photos - not too posed.', 'wedding-videographers': 'We mostly want a short highlight film we will actually rewatch.',
  'wedding-venues': 'Around 120 guests, ceremony and reception in one place if possible.', 'wedding-planners': 'We need help mostly with month-of coordination.',
  'wedding-djs': 'We want a dance floor that never empties - and no chicken dance.', 'wedding-florists': 'Garden-style, lots of greenery, nothing too stiff.',
  'wedding-caterers': 'Family-style dinner if that works, and a great late-night snack.', 'wedding-cakes': 'A small cutting cake plus a dessert table.',
  'hair-and-makeup': 'Bride plus five bridesmaids, natural glam.', 'wedding-officiants': 'A short, personal, non-religious ceremony.',
  'wedding-transportation': 'Shuttles for about 80 guests from two hotels.', 'wedding-rentals': 'Farm tables and mismatched vintage chairs.',
  'wedding-bands': 'Motown, some 90s, and one country song for Sam\'s dad.', 'wedding-invitations': 'Letterpress if the budget allows, digital RSVPs.',
  'day-of-coordination': 'We have planned most of it and need someone to run the day.',
};

function nextSaturday(monthsOut) {
  const d = new Date(); d.setMonth(d.getMonth() + monthsOut);
  while (d.getDay() !== 6) d.setDate(d.getDate() + 1);
  return d.toISOString().slice(0, 10);
}

module.exports = function demoModule(RESEND_API_KEY, ANTHROPIC_API_KEY) {

  async function sendEmail(to, subject, html, text) {
    if (!emailOk(to)) return;
    const r = await fetch('https://api.resend.com/emails', {
      method: 'POST', headers: { 'Authorization': `Bearer ${RESEND_API_KEY.value()}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ from: FROM, to: [to], subject, html, text }),
    });
    if (!r.ok) console.warn('resend', r.status, await r.text());
  }
  async function sendSms(to, text) {
    const t = e164(to); if (!t) return;
    const r = await fetch('https://api.telnyx.com/v2/messages', {
      method: 'POST', headers: { 'Authorization': `Bearer ${TELNYX_API_KEY.value()}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ from: TELNYX_FROM.value(), to: t, text: str(text).slice(0, 1500) }),
    });
    if (!r.ok) console.warn('telnyx', r.status, await r.text());
  }
  async function vendorAccess(uid, vendorId) {
    const [v, u] = await Promise.all([db().collection('vendors').doc(vendorId).get(), db().collection('users').doc(uid).get()]);
    if (!v.exists) return null;
    const ok = str(v.get('claimedBy')) === uid || (u.exists && str(u.get('vendorId')) === vendorId && str(u.get('vendorRole')) === 'manager');
    return ok ? { id: v.id, ...v.data() } : null;
  }

  // ------------------------------------------------------------- start ----
  const demoStart = onCall({ memory: '256MiB', secrets: [RESEND_API_KEY, TELNYX_API_KEY, TELNYX_FROM] }, async (request) => {
    const uid = request.auth && request.auth.uid;
    if (!uid) throw new HttpsError('unauthenticated', 'Sign in first.');
    const vendorId = str(request.data && request.data.vendorId);
    const v = await vendorAccess(uid, vendorId);
    if (!v) throw new HttpsError('permission-denied', 'Not your vendor.');
    const existing = await db().collection('inquiries').where('vendorId', '==', vendorId).where('demo', '==', true).limit(1).get();
    if (!existing.empty) return { inquiryId: existing.docs[0].id, existed: true };

    const metro = str(v.metroId) || 'phoenix';
    const cat = str(v.category || (Array.isArray(v.categories) && v.categories[0])) || 'wedding-photographers';
    const venue = VENUES[metro] || 'a garden venue nearby';
    const weddingDate = nextSaturday(8);
    const budget = str(v.startingPrice) && +v.startingPrice > 0 ? `$${Math.round(+v.startingPrice * 1.35).toLocaleString('en-US')}` : '$4,500';
    const intro = `Hi! We're Jordan and Sam - getting married ${new Date(weddingDate + 'T12:00:00').toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })} at ${venue}. ${CAT_LINE[cat] || 'We loved your work.'} Our budget for this is around ${budget}. Are you free that day, and what would you suggest for us?`;

    const ref = db().collection('inquiries').doc();
    const coupleUid = `demo_${vendorId}`;
    await ref.set({
      vendorId, vendorName: str(v.name), coupleUid, coupleName: `${COUPLE} (practice couple)`,
      demo: true, source: 'demo', offPlatform: false, tags: ['practice'],
      structuredIntent: { weddingDate, venue, guests: '120', budget, message: intro, category: cat },
      status: 'new', createdAt: FieldValue.serverTimestamp(),
      lastMessageAt: FieldValue.serverTimestamp(), lastMessageRole: 'couple', lastMessagePreview: intro.slice(0, 140),
      demoStartedAt: FieldValue.serverTimestamp(), demoStep: 'inquiry',
    });
    await ref.collection('messages').add({ senderRole: 'vendor', system: true, text: PRACTICE_NOTE, at: FieldValue.serverTimestamp(), demo: true, pinned: true });
    await ref.collection('messages').add({ senderRole: 'couple', text: intro, at: FieldValue.serverTimestamp(), demo: true });
    await db().collection('vendors').doc(vendorId).set({ demoStartedAt: FieldValue.serverTimestamp() }, { merge: true });

    // the alert - explicitly practice
    try {
      let to = str(v.email);
      if (str(v.claimedBy)) { const u = await db().collection('users').doc(str(v.claimedBy)).get(); if (u.exists && emailOk(u.get('email'))) to = str(u.get('email')); }
      const link = `${APP}?thread=${ref.id}`;
      if (to) await sendEmail(to, 'Your practice lead is here (not a real couple)',
        `<p>Jordan &amp; Sam just inquired - <b>they are a practice couple, played by June</b>, so you can try the whole Lazo flow with no stakes: reply, send a proposal, a contract, an invoice, a booking link, mark them booked.</p><p>This is exactly what a real lead alert looks like.</p><p><a href="${link}">Open the thread</a></p>`,
        `Your practice lead (Jordan & Sam, played by June - not a real couple) is in your inbox: ${link}`);
      if (e164(v.phone) && v.leadSmsOff !== true) await sendSms(v.phone, `Lazo: your PRACTICE lead is here - Jordan & Sam (played by June, not a real couple). Real lead texts look just like this. ${link}`);
    } catch (e) { console.warn('demo alert', e.message); }
    return { inquiryId: ref.id, existed: false };
  });

  // --------------------------------------------------------------- end ----
  const demoEnd = onCall({ memory: '256MiB' }, async (request) => {
    const uid = request.auth && request.auth.uid;
    if (!uid) throw new HttpsError('unauthenticated', 'Sign in first.');
    const vendorId = str(request.data && request.data.vendorId);
    if (!(await vendorAccess(uid, vendorId))) throw new HttpsError('permission-denied', 'Not your vendor.');
    const q = await db().collection('inquiries').where('vendorId', '==', vendorId).where('demo', '==', true).get();
    let n = 0;
    for (const d of q.docs) {
      const cons = await db().collection('consults').where('inquiryId', '==', d.id).get();
      for (const c of cons.docs) await c.ref.delete();
      await db().recursiveDelete(d.ref);
      n++;
    }
    await db().collection('vendors').doc(vendorId).set({ demoEndedAt: FieldValue.serverTimestamp() }, { merge: true });
    return { deleted: n };
  });

  // ------------------------------------------------------------ react ----
  async function june(v, inq, history, situation) {
    const system = `You are playing Jordan, one half of a couple (Jordan & Sam) planning a wedding, chatting with a wedding vendor on Lazo. This is a PRACTICE conversation the vendor knows is not real; stay in character as a warm, slightly busy, excited couple - never mention being an AI or a practice couple in Jordan's own words.
Wedding: ${str(inq.structuredIntent && inq.structuredIntent.weddingDate)} at ${str(inq.structuredIntent && inq.structuredIntent.venue)}, about 120 guests, budget around ${str(inq.structuredIntent && inq.structuredIntent.budget)}. Vendor: ${str(v.name)} (${str(inq.structuredIntent && inq.structuredIntent.category)}).
Keep replies to 1-3 short sentences, texting tone, first names. Ask exactly one realistic question every second or third message (second shooter, travel fees, how many hours, what happens if it rains, when the balance is due). Be easy to book - say yes to reasonable things.
Output JSON only: {"reply":"<Jordan's message>","coach":"<one plain sentence to the vendor about what just happened in Lazo and what to try next, or empty string>"}.
Situation right now: ${situation}`;
    const r = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: { 'x-api-key': ANTHROPIC_API_KEY.value(), 'anthropic-version': '2023-06-01', 'content-type': 'application/json' },
      body: JSON.stringify({ model: MODEL, max_tokens: 400, system, messages: history.length ? history : [{ role: 'user', content: '(start)' }] }),
    });
    if (!r.ok) throw new Error(`anthropic ${r.status}`);
    const j = await r.json();
    const text = (j.content || []).filter((c) => c.type === 'text').map((c) => c.text).join('').trim();
    try { return JSON.parse(text.replace(/```json|```/g, '').trim()); } catch (e) { return { reply: text.slice(0, 400), coach: '' }; }
  }

  async function post(inqRef, reply, coach) {
    if (reply) {
      await inqRef.collection('messages').add({ senderRole: 'couple', text: reply, at: FieldValue.serverTimestamp(), demo: true });
      await inqRef.set({ lastMessageAt: FieldValue.serverTimestamp(), lastMessageRole: 'couple', lastMessagePreview: reply.slice(0, 140), coupleLastReadAt: FieldValue.serverTimestamp() }, { merge: true });
    }
    if (coach) await inqRef.collection('messages').add({ senderRole: 'vendor', system: true, text: `June: ${coach}`, at: FieldValue.serverTimestamp(), demo: true, coach: true });
  }

  const onDemoActivity = onDocumentCreated({ document: 'inquiries/{inquiryId}/{sub}/{docId}', memory: '512MiB', timeoutSeconds: 120, secrets: [ANTHROPIC_API_KEY] }, async (event) => {
    const sub = event.params.sub;
    if (!['messages', 'proposals', 'contracts', 'invoices', 'questionnaires', 'tasks'].includes(sub)) return;
    const doc = event.data && event.data.data(); if (!doc) return;
    if (doc.demo === true || doc.system === true) return; // June's own writes, notes
    const inqRef = db().collection('inquiries').doc(event.params.inquiryId);
    const inqS = await inqRef.get();
    if (!inqS.exists || inqS.get('demo') !== true) return;
    const inq = inqS.data();
    const vS = await db().collection('vendors').doc(str(inq.vendorId)).get();
    const v = vS.exists ? vS.data() : {};

    // conversation so far, for Jordan's memory
    const msgs = await inqRef.collection('messages').orderBy('at').limit(40).get();
    const history = [];
    msgs.forEach((m) => { const x = m.data(); if (x.system) return; const role = str(x.senderRole) === 'vendor' ? 'user' : 'assistant'; const t = str(x.text).trim(); if (!t) return; if (history.length && history[history.length - 1].role === role) history[history.length - 1].content += '\n' + t; else history.push({ role, content: t }); });
    if (history.length && history[history.length - 1].role === 'assistant') history.push({ role: 'user', content: '(the vendor did something in Lazo - see situation)' });

    await sleep(8000 + Math.random() * 12000); // feel like a person
    try {
      if (sub === 'messages') {
        if (str(doc.senderRole) !== 'vendor') return;
        const first = str(inq.demoStep) === 'inquiry';
        const out = await june(v, inq, history, first ? 'The vendor just replied to our first inquiry. Answer warmly, confirm the date matters to us, ask one question.' : 'The vendor sent a message. Respond to it.');
        await post(inqRef, out.reply, first ? 'That reply went out like a real one would. Now tap + beside the reply box and send Jordan a proposal.' : out.coach);
        if (first) await inqRef.set({ demoStep: 'replied' }, { merge: true });
      } else if (sub === 'proposals') {
        const out = await june(v, inq, history, `The vendor sent a proposal: "${str(doc.title)}" for $${doc.price}. We like it. Accept it in one or two sentences and ask what happens next.`);
        await event.data.ref.set({ status: 'accepted', respondedAt: FieldValue.serverTimestamp() }, { merge: true });
        await post(inqRef, out.reply, 'Jordan accepted the proposal - couples do that from their own dashboard. Next: + → Send a contract. June prefills it from this proposal.');
        await inqRef.set({ demoStep: 'proposal' }, { merge: true });
      } else if (sub === 'contracts') {
        await event.data.ref.set({ status: 'signed', signedAt: FieldValue.serverTimestamp(), signedBy: COUPLE, signedIp: 'practice' }, { merge: true });
        await inqRef.set({ contractStatus: 'signed', contractUpdatedAt: FieldValue.serverTimestamp() }, { merge: true });
        const out = await june(v, inq, history, 'We just signed the contract. Say so happily in one sentence.');
        await post(inqRef, out.reply, 'Signed. If you have a retainer set under Account → Get paid, the invoice goes out by itself - otherwise send one now with + → Send an invoice, or set up a payment plan.');
        await inqRef.set({ demoStep: 'contract' }, { merge: true });
      } else if (sub === 'invoices') {
        await event.data.ref.set({ status: 'paid', paidAt: FieldValue.serverTimestamp(), paidVia: 'demo', demo: true }, { merge: true });
        const plan = str(doc.planId);
        if (plan) {
          const open = await inqRef.collection('invoices').where('planId', '==', plan).where('status', '==', 'sent').get();
          await inqRef.set({ invoiceStatus: open.size <= 1 ? 'paid' : 'partial', invoiceUpdatedAt: FieldValue.serverTimestamp() }, { merge: true });
        } else {
          await inqRef.set({ invoiceStatus: 'paid', invoiceUpdatedAt: FieldValue.serverTimestamp() }, { merge: true });
        }
        const out = await june(v, inq, history, `We just paid the invoice "${str(doc.title)}" for $${doc.total}. One relieved sentence.`);
        await post(inqRef, out.reply, 'Paid - a real payment lands in your own Whop, Stripe or Square account and shows on the Money card. Try marking them Booked from the pill at the top of the thread, then Done practicing when you are ready.');
        await inqRef.set({ demoStep: 'paid' }, { merge: true });
      } else if (sub === 'questionnaires') {
        const qs = Array.isArray(doc.questions) ? doc.questions : [];
        const answers = {};
        qs.forEach((q, i) => { const k = str(q && (q.id || q.key)) || `q${i}`; answers[k] = ['Ceremony at 4, dinner around 6.', 'About 120 guests.', 'Sam\'s parents, my grandmother, our dog Biscuit.', 'Nothing too posed - candid is our style.', 'We have a first look planned.'][i % 5]; });
        await event.data.ref.set({ answers, status: 'completed', completedAt: FieldValue.serverTimestamp() }, { merge: true });
        await inqRef.set({ questionnaireStatus: 'completed', questionnaireUpdatedAt: FieldValue.serverTimestamp() }, { merge: true });
        await post(inqRef, 'Filled that out - let us know if you need anything else!', 'Questionnaire answered. Answers sit in the thread for the day-of.');
      } else if (sub === 'tasks') {
        if (str(doc.assignedTo) !== 'couple') return;
        await event.data.ref.set({ done: true, doneAt: FieldValue.serverTimestamp() }, { merge: true });
        await post(inqRef, `Done - ${str(doc.title).toLowerCase()}.`, 'Couple tasks show in their dashboard and get a reminder the morning they are due.');
      }
    } catch (e) { console.error('onDemoActivity', sub, e.message); }
  });

  const demoSweep = onSchedule({ schedule: '15 4 * * *', timeZone: 'America/Phoenix', memory: '256MiB' }, async () => {
    const cutoff = Timestamp.fromDate(new Date(Date.now() - 14 * 86400000));
    const q = await db().collection('inquiries').where('demo', '==', true).where('demoStartedAt', '<=', cutoff).get();
    for (const d of q.docs) { await db().recursiveDelete(d.ref); }
    console.log(`demoSweep: removed ${q.size}`);
  });

  return { demoStart, demoEnd, onDemoActivity, demoSweep };
};

// END OF FILE - JC-LAZO-FNDASH-0913-018
