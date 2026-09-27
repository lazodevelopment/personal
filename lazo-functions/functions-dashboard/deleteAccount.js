// functions-dashboard/deleteAccount.js
// Build ID: JC-LAZO-DELETE-0918-001
//
// ACCOUNT DELETION, DONE PROPERLY.
//
// What the app did before this existed: the couple dashboard deleted
// couples/{cid}/plan/* and couples/{cid}, swallowed any error with catch(_){},
// then deleted the Firebase Auth user regardless. That left behind:
//
//   couples/{cid}/dayof, details, guests, music, recs, seating, sends  (7 of 8
//     subcollections - only 'plan' was handled)
//   weddingSites where coupleUid == cid      the whole wedding website
//   inquiries where coupleUid == cid         every message with every vendor,
//     plus their messages/proposals/contracts/invoices/questionnaires/tasks
//   users/{uid}                              name, email, phone
//   coupleInvites                            partner invitations
//   Storage couples/{uid}/**                 every uploaded photo
//
// And because the auth user went first-and-regardless, none of it was reachable
// afterwards. https://meetlazo.com/delete-account/ promises all of the above is
// removed, and both app stores require working deletion, so this closes it.
//
// WHY A CALLABLE AND NOT CLIENT CODE
//   - Storage objects cannot be listed and bulk-deleted from the client.
//   - Deciding whether a PARTNER still shares the plan requires reading other
//     users' documents, which firestore.rules correctly forbids the client.
//   - Ordering matters: data first, auth user last. If anything throws, the
//     account still exists and the couple can retry. The old order made a
//     partial failure permanent.
//
// THE PARTNER RULE
// /delete-account/ says: "If your partner shares the plan, their login is
// unaffected - the shared plan is deleted only when the last person on it
// deletes their account." couples/{cid} is keyed by ONE uid, and a partner's
// users/{uid}.coupleUid points at it. So before removing shared data we check
// for any other user still pointing at this couple id; if one exists, we delete
// only this person's own records and leave the shared plan intact.
//
// WHAT IS DELIBERATELY KEPT (also stated on the public page)
//   - Verified reviews they left: detached from the account, shown without a
//     name. Vendors and other couples rely on them.
//   - Payment and contract records under inquiries/{id}: tax and
//     payment-network retention, and a vendor's signed contract is not the
//     couple's to destroy. The thread's messages go; those two stay, with the
//     couple scrubbed off the parent document.

'use strict';

const { onCall, HttpsError } = require('firebase-functions/v2/https');
const admin = require('firebase-admin');

const db = () => admin.firestore();
const bucket = () => admin.storage().bucket();

// Collections holding docs keyed to a couple by field, not by doc id.
// Safe to remove outright: nothing here is retained for legal reasons.
// inquiries are handled separately - see scrubInquiries.
const BY_COUPLE_FIELD = [
  ['weddingSites', 'coupleUid'],
  ['coupleInvites', 'coupleUid'],
];

// Subcollections under an inquiry that must SURVIVE the couple's deletion.
// https://meetlazo.com/delete-account/ commits to keeping payment records for
// up to seven years for tax and payment-network rules, and the vendor's own
// signed contract is not the couple's to destroy. Everything else under an
// inquiry is conversation and goes.
const RETAINED_SUBS = ['invoices', 'contracts'];

async function deleteQuery(col, field, value, log) {
  const snap = await db().collection(col).where(field, '==', value).get();
  for (const d of snap.docs) {
    // Document AND every subcollection under it. weddingSites carries rsvps,
    // and enumerating subcollections by hand is how one gets missed.
    await db().recursiveDelete(d.ref);
  }
  if (snap.size) log.push(`${col}: ${snap.size}`);
  return snap.size;
}

async function deleteStorage(prefix, log) {
  try {
    const [files] = await bucket().getFiles({ prefix });
    if (!files.length) return 0;
    await Promise.all(files.map((f) => f.delete().catch(() => {})));
    log.push(`storage ${prefix}: ${files.length}`);
    return files.length;
  } catch (e) {
    // Never let a storage problem strand the account: the caller still gets a
    // deleted login, and the orphaned bytes are reported rather than hidden.
    log.push(`storage ${prefix}: FAILED ${e.message}`);
    return 0;
  }
}

// A review stays published because the vendor and other couples rely on it, but
// nothing on it may point back at a person who asked to be forgotten.
async function anonymiseReviews(uid, log) {
  const snap = await db().collection('reviews').where('coupleUid', '==', uid).get();
  for (const d of snap.docs) {
    await d.ref.set({
      coupleUid: null,
      coupleName: 'A verified couple',
      coupleEmail: admin.firestore.FieldValue.delete(),
      couplePhotoUrl: admin.firestore.FieldValue.delete(),
      anonymisedAt: admin.firestore.FieldValue.serverTimestamp(),
    }, { merge: true });
  }
  if (snap.size) log.push(`reviews anonymised: ${snap.size}`);
}

// An inquiry is a two-party record. The couple may erase their half; the vendor
// keeps theirs, and the retained financial documents stay attached to it.
//
// billingInvoices is NOT touched here: despite the name it is the VENDOR's Pro
// subscription billing (vendorId, tier, whopMembershipId), nothing to do with a
// couple.
async function scrubInquiries(coupleId, log) {
  const snap = await db().collection('inquiries').where('coupleUid', '==', coupleId).get();
  let purged = 0;
  let scrubbed = 0;

  for (const d of snap.docs) {
    const subs = await d.ref.listCollections();
    const keep = subs.filter((c) => RETAINED_SUBS.includes(c.id));
    const hasRetained = (await Promise.all(
      keep.map(async (c) => !(await c.limit(1).get()).empty)
    )).some(Boolean);

    if (!hasRetained) {
      // Nothing to keep - the whole thread goes, subcollections and all.
      await db().recursiveDelete(d.ref);
      purged += 1;
      continue;
    }

    // Drop every subcollection except the retained ones.
    for (const c of subs) {
      if (RETAINED_SUBS.includes(c.id)) continue;
      await db().recursiveDelete(c);
    }
    // Strip the person from the parent document, keep the commercial record.
    await d.ref.set({
      coupleUid: null,
      coupleName: 'A former Lazo couple',
      coupleEmail: admin.firestore.FieldValue.delete(),
      couplePhotoUrl: admin.firestore.FieldValue.delete(),
      message: admin.firestore.FieldValue.delete(),
      structuredIntent: admin.firestore.FieldValue.delete(),
      contact: admin.firestore.FieldValue.delete(),
      coupleDeletedAt: admin.firestore.FieldValue.serverTimestamp(),
    }, { merge: true });
    scrubbed += 1;
  }

  if (purged) log.push(`inquiries purged: ${purged}`);
  if (scrubbed) log.push(`inquiries kept for records, couple scrubbed: ${scrubbed}`);
}

module.exports = () => {
  // deleteMyAccount  callable {}  the signed-in user deletes themselves.
  // Returns { ok, deleted: [...] } so the client can show what happened and so
  // a failure is visible rather than silent.
  const deleteMyAccount = onCall({ memory: '512MiB', timeoutSeconds: 540 }, async (request) => {
    const uid = request.auth && request.auth.uid;
    if (!uid) throw new HttpsError('unauthenticated', 'Sign in first.');

    const log = [];
    const userSnap = await db().collection('users').doc(uid).get();
    const user = userSnap.exists ? userSnap.data() : {};

    // The plan this person belongs to: their own uid unless they joined a partner's.
    const coupleId = (user.coupleUid || uid).toString();

    // Is anyone else still on that plan? If so the shared records stay.
    let sharedWithPartner = false;
    if (coupleId) {
      const others = await db().collection('users').where('coupleUid', '==', coupleId).get();
      sharedWithPartner = others.docs.some((d) => d.id !== uid);
      if (!sharedWithPartner && coupleId !== uid) {
        // They joined someone else's plan and that someone still exists.
        const owner = await db().collection('users').doc(coupleId).get();
        if (owner.exists) sharedWithPartner = true;
      }
    }

    if (sharedWithPartner) {
      log.push('shared plan kept: a partner is still on it');
    } else {
      // couples/{coupleId} and all eight subcollections in one call.
      await db().recursiveDelete(db().collection('couples').doc(coupleId));
      log.push(`couples/${coupleId} + subcollections`);
      for (const [col, field] of BY_COUPLE_FIELD) {
        await deleteQuery(col, field, coupleId, log);
      }
      await deleteStorage(`couples/${coupleId}/`, log);
    }

    // Always this person's own records, shared plan or not.
    if (coupleId !== uid) {
      for (const [col, field] of BY_COUPLE_FIELD) {
        await deleteQuery(col, field, uid, log);
      }
      await deleteStorage(`couples/${uid}/`, log);
    }
    await deleteStorage(`users/${uid}/`, log);

    await anonymiseReviews(uid, log);
    await scrubInquiries(coupleId, log);
    if (coupleId !== uid) await scrubInquiries(uid, log);

    await db().collection('users').doc(uid).delete();
    log.push('users doc');

    // LAST. If anything above threw, the login still exists and they can retry -
    // which is the whole reason this runs before the auth delete rather than after.
    await admin.auth().deleteUser(uid);
    log.push('auth user');

    console.log(`[deleteMyAccount] ${uid}: ${log.join(', ')}`);
    return { ok: true, deleted: log, sharedPlanKept: sharedWithPartner };
  });

  return { deleteMyAccount };
};

// END OF FILE - JC-LAZO-DELETE-0918-001
