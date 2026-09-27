// functions-dashboard/safety.js
// Build ID: JC-LAZO-SAFETY-0918-001
//
// REPORT AND BLOCK A VENDOR, FROM THE THREAD.
//
// Nothing like this existed. A couple who was harassed, pressured or spammed by
// a vendor had no way to stop it and no way to tell us - the only escape was to
// stop opening the app.
//
// WHAT BLOCKING DOES (all four, per the product decision)
//   1. The vendor cannot write to that thread again. Enforced in
//      firestore.rules, not merely hidden in the UI, so it holds against a
//      direct API call.
//   2. The thread leaves the couple's inbox, into a "Blocked" section. NOT
//      deleted - if they later report, the conversation is the evidence.
//   3. The vendor disappears from that couple's browse, search and June
//      suggestions, via couples/{cid}/blockedVendors/{vendorId}.
//   4. The vendor is told the conversation was closed.
//
// ON (4): the wording here is deliberately neutral. The couple asked for this
// to be visible to the vendor, and it is - but "this couple blocked and
// reported you" is the version that invites retaliation against someone who
// just told us they feel unsafe. The vendor learns the conversation is closed
// and that they should not contact the couple again. That is the actionable
// part; the accusation is not.
//
// REPORTING queues to reports/{id} for review in God Mode, emails an alert, and
// blocks the thread immediately - a couple should not have to wait on a human
// before the messages stop.

'use strict';

const { onCall, HttpsError } = require('firebase-functions/v2/https');
const { defineSecret } = require('firebase-functions/params');
const admin = require('firebase-admin');

const RESEND_API_KEY = defineSecret('RESEND_API_KEY');
const db = () => admin.firestore();
const FROM = 'Lazo <hello@meetlazo.com>';
// support@ rather than trust@: the public site stopped publishing trust@ when
// the mailboxes were replaced with the contact form, and a report that alerts
// an address nobody reads is worse than no alert at all.
const ALERT_TO = 'support@meetlazo.com';

const REASONS = [
  'harassment',        // abusive, threatening or persistent unwanted contact
  'inappropriate',     // sexual, discriminatory or otherwise inappropriate
  'spam',              // off-platform soliciting, repeated sales pressure
  'scam',              // payment fraud, bait and switch, fake identity
  'noshow',            // took money or a booking and vanished
  'other',
];

// The couple must actually be on the thread they are acting on. Without this a
// signed-in user could block or report any vendor on anyone's behalf.
async function assertOwnsThread(inquiryId, uid) {
  const snap = await db().collection('inquiries').doc(inquiryId).get();
  if (!snap.exists) throw new HttpsError('not-found', 'Conversation not found.');
  const inq = snap.data() || {};
  if (inq.coupleUid !== uid) {
    throw new HttpsError('permission-denied', 'Not your conversation.');
  }
  return inq;
}

async function sendMail(key, to, subject, text) {
  if (!key) return;
  try {
    await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { 'content-type': 'application/json', authorization: `Bearer ${key}` },
      body: JSON.stringify({ from: FROM, to: [to], subject, text }),
    });
  } catch (e) {
    console.error('[safety] mail failed:', e.message);
  }
}

module.exports = () => {
  // blockVendor  callable {inquiryId, blocked}
  // Reversible on purpose: a couple who blocks in anger should be able to undo it.
  const blockVendor = onCall({ memory: '256MiB' }, async (request) => {
    const uid = request.auth && request.auth.uid;
    if (!uid) throw new HttpsError('unauthenticated', 'Sign in first.');
    const inquiryId = String((request.data || {}).inquiryId || '');
    const blocked = (request.data || {}).blocked !== false;
    if (!inquiryId) throw new HttpsError('invalid-argument', 'inquiryId required.');

    const inq = await assertOwnsThread(inquiryId, uid);
    const vendorId = String(inq.vendorId || '');
    const now = admin.firestore.FieldValue.serverTimestamp();

    // (1) and (2): the rules read blockedByCouple to refuse vendor writes, and
    // the inbox filters on it.
    await db().collection('inquiries').doc(inquiryId).set({
      blockedByCouple: blocked,
      blockedAt: blocked ? now : admin.firestore.FieldValue.delete(),
    }, { merge: true });

    // (3): hide the business from this couple everywhere else in the app.
    if (vendorId) {
      const ref = db().collection('couples').doc(uid)
        .collection('blockedVendors').doc(vendorId);
      if (blocked) {
        await ref.set({
          vendorId,
          vendorName: inq.vendorName || '',
          inquiryId,
          at: now,
        });
      } else {
        await ref.delete();
      }
    }

    // (4): tell the vendor, neutrally. A system message keeps it inside the
    // thread they already have rather than arriving as an accusation by email.
    if (blocked) {
      await db().collection('inquiries').doc(inquiryId)
        .collection('messages').add({
          senderRole: 'system',
          system: true,
          text: 'This couple has closed the conversation. Please do not contact them again about this enquiry.',
          at: now,
        });
    }

    console.log(`[blockVendor] ${uid} ${blocked ? 'blocked' : 'unblocked'} ${vendorId} on ${inquiryId}`);
    return { ok: true, blocked };
  });

  // reportVendor  callable {inquiryId, reason, detail}
  // Queues for review AND blocks immediately - protection should not wait on us.
  const reportVendor = onCall({ memory: '256MiB', secrets: [RESEND_API_KEY] }, async (request) => {
    const uid = request.auth && request.auth.uid;
    if (!uid) throw new HttpsError('unauthenticated', 'Sign in first.');
    const d = request.data || {};
    const inquiryId = String(d.inquiryId || '');
    const reason = REASONS.includes(String(d.reason)) ? String(d.reason) : 'other';
    const detail = String(d.detail || '').slice(0, 4000);
    if (!inquiryId) throw new HttpsError('invalid-argument', 'inquiryId required.');

    const inq = await assertOwnsThread(inquiryId, uid);
    const vendorId = String(inq.vendorId || '');
    const now = admin.firestore.FieldValue.serverTimestamp();

    const report = await db().collection('reports').add({
      type: 'vendor',
      status: 'open',
      reason,
      detail,
      inquiryId,
      vendorId,
      vendorName: inq.vendorName || '',
      reportedByUid: uid,
      createdAt: now,
    });

    // Block the thread straight away. The conversation itself is preserved -
    // it is the evidence, and deleting it would destroy the case.
    await db().collection('inquiries').doc(inquiryId).set({
      blockedByCouple: true,
      blockedAt: now,
      reportedAt: now,
      reportId: report.id,
    }, { merge: true });

    if (vendorId) {
      await db().collection('couples').doc(uid)
        .collection('blockedVendors').doc(vendorId)
        .set({ vendorId, vendorName: inq.vendorName || '', inquiryId, at: now, reported: true });
    }

    await db().collection('inquiries').doc(inquiryId).collection('messages').add({
      senderRole: 'system',
      system: true,
      text: 'This couple has closed the conversation. Please do not contact them again about this enquiry.',
      at: now,
    });

    // How many distinct couples have reported this vendor? Not an automatic
    // suspension - the product decision was review, not auto-action - but a
    // pattern is exactly what a human reviewer needs to see first.
    let distinct = 0;
    if (vendorId) {
      const prior = await db().collection('reports')
        .where('vendorId', '==', vendorId).get();
      distinct = new Set(prior.docs.map((x) => x.get('reportedByUid'))).size;
    }

    await sendMail(
      RESEND_API_KEY.value(), ALERT_TO,
      `[lazo/report] ${reason} - ${inq.vendorName || vendorId}${distinct > 1 ? ` (${distinct} couples)` : ''}`,
      `Reason:  ${reason}\nVendor:  ${inq.vendorName || ''} (${vendorId})\n` +
      `Thread:  ${inquiryId}\nReport:  ${report.id}\n` +
      `Distinct couples who have reported this vendor: ${distinct}\n\n` +
      `${detail || '(no detail given)'}\n\n` +
      `The thread is blocked and preserved. Review in God Mode.`
    );

    console.log(`[reportVendor] ${uid} reported ${vendorId} (${reason}), ${distinct} distinct reporters`);
    return { ok: true, reportId: report.id };
  });

  return { blockVendor, reportVendor };
};

// END OF FILE - JC-LAZO-SAFETY-0918-001
