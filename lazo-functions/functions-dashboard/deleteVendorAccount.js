// functions-dashboard/deleteVendorAccount.js
// Build ID: JC-LAZO-DELETE-0924-002
//
// VENDOR ACCOUNT DELETION (App Store 5.1.1(v), Play "Delete account").
//
// A vendor account is a Firebase login (users/{uid}) that has CLAIMED one or
// more public listings (vendors/{id}.claimedBy == uid). The listing itself is
// marketplace data seeded from public sources and stays public and unclaimed,
// exactly as it was before the owner claimed it. Everything the owner ADDED
// goes:
//
//   vendors/{id}      claim fields released; owner-entered fields removed
//                     (bio, gallery, cover, logo, packages, price sheet, FAQs,
//                     announcement, services note, preferred vendors, calendar
//                     token, owner photo/email, service metros, tier)
//   vendors/{id}/*    every subcollection (availability, templates, etc.)
//   contractTemplates, questionnaireTemplates, vendorInvites  where vendorId
//   claimRequests, listingRequests, supportTickets            where uid
//   proSubscriptions/{id}   kept as a billing record, marked account_deleted
//                           (Whop cancels on its own webhook; the record says why)
//   Storage vendors/{id}/** every upload (media, docs, sneak peeks, templates)
//   users/{uid}
//   the Firebase Auth user, LAST - a partial failure leaves a retryable account
//
// Kept on purpose: inquiries and their messages/contracts/invoices - they are
// the couple's record of a booking and the couple may still need them - and
// reviews, which belong to the couples who wrote them.
'use strict';

const { onCall, HttpsError } = require('firebase-functions/v2/https');
const admin = require('firebase-admin');

const db = () => admin.firestore();
const bucket = () => admin.storage().bucket();
const DEL = () => admin.firestore.FieldValue.delete();

// owner-entered fields on vendors/{id}; the seeded listing keeps the rest
const OWNER_FIELDS = [
  'claimedBy', 'claimStatus', 'claimedAt', 'verified', 'verifiedAt', 'ownerName', 'ownerPhotoUrl',
  'publicEmail', 'bio', 'intro', 'gallery', 'coverUrl', 'logoUrl', 'packages', 'startingPrice',
  'priceSheetUrl', 'priceSheetPages', 'addOns', 'vendorFaqs', 'announcement', 'servicesNote',
  'preferredVendors', 'calendarToken', 'serviceMetroNames', 'serviceMetros', 'travelFrom',
  'tier', 'tierExpiresAt', 'fcmTokens', 'notifyPhone', 'notifyEmail', 'autoReply', 'leadFormKey',
  'instantBooking', 'bookingLink', 'payments', 'availabilityNote', 'videoEmbeds', 'videoEmbed',
];

async function deleteWhere(col, field, value, log) {
  const snap = await db().collection(col).where(field, '==', value).get();
  for (const d of snap.docs) await db().recursiveDelete(d.ref);
  if (snap.size) log.push(`${col}: ${snap.size}`);
}

async function deleteStorage(prefix, log) {
  try {
    const [files] = await bucket().getFiles({ prefix });
    if (!files.length) return;
    await Promise.all(files.map((f) => f.delete().catch(() => {})));
    log.push(`storage ${prefix}: ${files.length}`);
  } catch (e) {
    log.push(`storage ${prefix}: FAILED ${e.message}`);
  }
}

async function releaseListing(vendorId, log) {
  const ref = db().collection('vendors').doc(vendorId);
  const snap = await ref.get();
  if (!snap.exists) return;
  // subcollections first (availability, templates, anything the owner made)
  const subs = await ref.listCollections();
  for (const c of subs) await db().recursiveDelete(c);
  const patch = {};
  for (const f of OWNER_FIELDS) patch[f] = DEL();
  patch.claimStatus = 'unclaimed';
  patch.verified = false;
  patch.ownerDeletedAt = admin.firestore.FieldValue.serverTimestamp();
  await ref.set(patch, { merge: true });
  log.push(`vendors/${vendorId}: claim released, ${subs.length} subcollection(s) removed`);
  const sub = db().collection('proSubscriptions').doc(vendorId);
  if ((await sub.get()).exists) {
    await sub.set({ status: 'account_deleted', cancelAtPeriodEnd: true,
      accountDeletedAt: admin.firestore.FieldValue.serverTimestamp() }, { merge: true });
    log.push(`proSubscriptions/${vendorId}: marked account_deleted`);
  }
  await deleteWhere('contractTemplates', 'vendorId', vendorId, log);
  await deleteWhere('questionnaireTemplates', 'vendorId', vendorId, log);
  await deleteWhere('vendorInvites', 'vendorId', vendorId, log);
  await deleteStorage(`vendors/${vendorId}/`, log);
}

module.exports = () => {
  // deleteMyVendorAccount  callable {}  the signed-in vendor deletes themselves.
  const deleteMyVendorAccount = onCall({ memory: '512MiB', timeoutSeconds: 540 }, async (request) => {
    const uid = request.auth && request.auth.uid;
    if (!uid) throw new HttpsError('unauthenticated', 'Sign in first.');
    const log = [];

    // every listing this login claimed, plus the one on the users doc
    const ids = new Set();
    const userSnap = await db().collection('users').doc(uid).get();
    const u = userSnap.exists ? userSnap.data() : {};
    if (u && u.vendorId) ids.add(String(u.vendorId));
    const claimed = await db().collection('vendors').where('claimedBy', '==', uid).get();
    claimed.docs.forEach((d) => ids.add(d.id));

    for (const vendorId of ids) {
      await releaseListing(vendorId, log);
    }
    await deleteWhere('claimRequests', 'uid', uid, log);
    await deleteWhere('listingRequests', 'uid', uid, log);
    await deleteWhere('supportTickets', 'uid', uid, log);
    if (userSnap.exists) {
      await db().recursiveDelete(userSnap.ref);
      log.push('users doc');
    }

    // the login goes last; if anything above threw, the account still exists
    try {
      await admin.auth().deleteUser(uid);
      log.push('auth user');
    } catch (e) {
      throw new HttpsError('internal', `Data removed but the login could not be deleted: ${e.message}. Try again.`);
    }
    return { ok: true, deleted: log, listingsReleased: [...ids] };
  });

  return { deleteMyVendorAccount };
};

// END OF FILE - JC-LAZO-DELETE-0924-002
