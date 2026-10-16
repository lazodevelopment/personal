// functions-dashboard/meals.js
// Build ID: JC-LAZO-FNDASH-1016-MEALS
//
// FINAL MEAL COUNTS, ON TIME. A couple sends meal choices from the Guests screen
// (Couple v161) into the caterer's / venue's thread, which writes
// inquiries/{id}/shared/meals. The vendor sets the final-count date there
// (Vendor v202, finalDue); until they do, it is two weeks before the wedding.
//
//   mealCountReminders   09:00 Phoenix daily, over every shared/meals doc:
//     7 and 2 days before the due date -> the couple (and partner): June feed +
//       push + one email, with today's numbers from their live guest list
//       ("12 guests haven't replied, 5 haven't picked a meal").
//     the day after a date the VENDOR set, when the couple's last send is older
//       than three days before it -> the vendor: June feed + push.
//   Each step is stamped with the due date it was for (remind7At / remind2At /
//   lateAt = 'YYYY-MM-DD'), so a moved date re-arms it and a retry never repeats.
//   Practice couples and off-platform leads (no account) are skipped.
//
// No index needed: a collection-group read of 'shared' with no filter.

'use strict';

const { onSchedule } = require('firebase-functions/v2/scheduler');
const admin = require('firebase-admin');
const F = require('./email-frame');
const feed = require('./june-feed');

const DAY = 86400e3;
const str = (v) => (v == null ? '' : String(v));
const practice = (d) => !d || d.demo === true || d.practice === true || d.preview === true;
const phxDay = (d) => d.toLocaleDateString('en-CA', { timeZone: 'America/Phoenix' });   // YYYY-MM-DD
const fmtDay = (d) => d.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', timeZone: 'America/Phoenix' });
const fmtShort = (d) => d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'America/Phoenix' });
const toDate = (v) => (v && typeof v.toDate === 'function' ? v.toDate() : null);
const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;

/** the date the final count is due: the vendor's, or two weeks before the wedding */
function dueOf(m) {
  const set = toDate(m.finalDue);
  if (set) return { due: set, set: true };
  const wd = toDate(m.weddingDate);
  return wd ? { due: new Date(wd.getTime() - 14 * DAY), set: false } : null;
}

/** whole days from today (Phoenix) to d (Phoenix) */
function daysUntil(d, now = new Date()) {
  return Math.round((new Date(phxDay(d) + 'T12:00:00Z') - new Date(phxDay(now) + 'T12:00:00Z')) / DAY);
}

/** what is still missing on the couple's live guest list, counted like the app does */
function gapsOf(guests) {
  let awaiting = 0, noChoice = 0, heads = 0;
  for (const g of guests) {
    const r = str(g.rsvp || 'pending');
    if (r === 'no') continue;
    const plus = Number(g.plusOnes) || 0;
    if (r !== 'yes') { awaiting += 1 + plus; continue; }
    heads += 1 + plus;
    if (g.kid !== true && !str(g.meal).trim()) noChoice++;
    const pa = g.plusAssign && typeof g.plusAssign === 'object' ? g.plusAssign : {};
    for (let k = 1; k <= plus; k++) {
      const a = pa[String(k)] || {};
      if (a.kid !== true && !str(a.meal).trim()) noChoice++;
    }
  }
  return { awaiting, noChoice, heads };
}

module.exports = function meals(RESEND_API_KEY) {
  const db = () => admin.firestore();
  const { esc, frame, APP } = F;
  const emailOk = (e) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(str(e).trim());

  async function sendEmail(to, subject, html, text) {
    const r = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${RESEND_API_KEY.value()}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ from: 'Lazo <hello@meetlazo.com>', to, reply_to: 'hello@meetlazo.com', subject, html, text }),
    });
    if (!r.ok) throw new Error(`resend ${r.status}: ${await r.text()}`);
  }

  /** the couple's addresses (login + partners), or [] when they muted email */
  async function coupleEmails(cid) {
    const [cs, us, partners] = await Promise.all([
      db().collection('couples').doc(cid).get().catch(() => null),
      db().collection('users').doc(cid).get().catch(() => null),
      db().collection('users').where('coupleUid', '==', cid).limit(3).get().catch(() => null),
    ]);
    const c = cs && cs.exists ? cs.data() : {};
    if (c.emailOk === false || c.preview === true) return { to: [], couple: c };
    const out = new Set();
    const u = us && us.exists ? us.data() : {};
    if (emailOk(u.email)) out.add(str(u.email).trim());
    if (partners) partners.forEach((d) => { const e = str(d.get('email')).trim(); if (emailOk(e)) out.add(e); });
    return { to: [...out], couple: c };
  }

  async function remindCouple(doc, m, inq, inqId, due, days) {
    const cid = str(inq.coupleUid);
    const vendor = str(inq.vendorName) || 'Your caterer';
    const gs = await db().collection('couples').doc(cid).collection('guests').get();
    const g = gapsOf(gs.docs.map((d) => d.data() || {}));
    const missing = [
      g.awaiting ? `${plural(g.awaiting, 'guest hasn’t', 'guests haven’t')} replied` : '',
      g.noChoice ? `${plural(g.noChoice, 'guest hasn’t', 'guests haven’t')} picked a meal` : '',
    ].filter(Boolean);
    const when = days === 2 ? 'in two days' : 'in a week';
    const text = `${vendor} needs your final meal count by ${fmtShort(due)} (${when}). ` +
      (missing.length ? `${missing.join(' and ')}. ` : 'Every guest has a meal. ') + 'Send them the update from Guests.';
    await feed.notify(await feed.couplePeople(cid), { title: 'Final meal count due', text, kind: 'meals', thread: inqId, open: 'guests' });
    const { to, couple } = await coupleEmails(cid);
    if (!to.length) return;
    const names = str(couple.names) || str(inq.coupleName) || 'you two';
    const body = `<p style="margin:0 0 12px;font-family:Helvetica,Arial,sans-serif;font-size:14.5px;line-height:1.6;color:#5B5363">` +
      `${g.heads} guests are confirmed so far.${missing.length ? ' ' + esc(missing.join(' and ')) + '. A quick nudge to them now saves a guess on the day.' : ' Every one of them has a meal.'}</p>` +
      `<p style="margin:0;font-family:Helvetica,Arial,sans-serif;font-size:14.5px;line-height:1.6;color:#5B5363">` +
      `When you’re ready, open <b>Guests › Meal choices › Send update</b>. ${esc(vendor)} gets the counts, allergies, tables and vendor meals in your thread, with a printable sheet.</p>`;
    const html = frame({
      preheader: `${vendor} needs your final meal count by ${fmtShort(due)}.`,
      kicker: 'Meal count', title: `Final meal count due ${fmtDay(due)}.`,
      lede: `${esc(names)}, ${esc(vendor)} needs your final numbers ${when}.`,
      body, cta: 'Open your guest list', ctaHref: APP,
      footerWhy: 'You’re getting this because you sent meal choices to a vendor on Lazo.',
    });
    try {
      await sendEmail(to, `Final meal count for ${vendor} is due ${fmtShort(due)}`, html, `${text}\n\n${APP}`);
    } catch (e) { console.log('meals email', inqId, e.message); }
  }

  async function tellVendorLate(m, inq, inqId, due) {
    const couple = str(inq.coupleName) || str(m.coupleName) || 'The couple';
    const last = toDate(m.sentAt);
    await feed.notify(await feed.vendorPeople(str(inq.vendorId)), {
      title: 'Final meal count',
      text: `${couple}’s final meal count was due ${fmtShort(due)}.${last ? ` Their last update was ${fmtShort(last)}.` : ''} Ask them for an update from the thread.`,
      kind: 'meals', thread: inqId,
    });
  }

  const mealCountReminders = onSchedule({ schedule: '0 9 * * *', timeZone: 'America/Phoenix', memory: '512MiB', timeoutSeconds: 300, secrets: [RESEND_API_KEY] }, async () => {
    const snap = await db().collectionGroup('shared').get();
    let reminded = 0, late = 0;
    for (const doc of snap.docs) {
      if (doc.id !== 'meals') continue;
      const m = doc.data() || {};
      if (m.kind !== 'meals') continue;
      const d = dueOf(m);
      if (!d) continue;
      const key = phxDay(d.due);
      const days = daysUntil(d.due);
      const step = days === 7 ? 'remind7At' : days === 2 ? 'remind2At' : days === -1 && d.set ? 'lateAt' : '';
      if (!step || m[step] === key) continue;
      const inqRef = doc.ref.parent.parent;
      if (!inqRef) continue;
      const inq = (await inqRef.get()).data();
      if (practice(inq) || !str(inq.coupleUid) || str(inq.coupleUid).startsWith('lead_')) continue;
      try {
        if (step === 'lateAt') {
          const last = toDate(m.sentAt);
          if (last && last.getTime() >= d.due.getTime() - 3 * DAY) {
            await doc.ref.set({ lateAt: key }, { merge: true });
            continue;   // they sent close enough to the date
          }
          await tellVendorLate(m, inq, inqRef.id, d.due);
          late++;
        } else {
          await remindCouple(doc, m, inq, inqRef.id, d.due, days);
          reminded++;
        }
        await doc.ref.set({ [step]: key }, { merge: true });
      } catch (e) { console.log('mealCountReminders', inqRef.id, e.message); }
    }
    console.log('mealCountReminders', { reminded, late });
  });

  return { mealCountReminders };
};

module.exports.dueOf = dueOf;
module.exports.daysUntil = daysUntil;
module.exports.gapsOf = gapsOf;

// END OF FILE - JC-LAZO-FNDASH-1016-MEALS
