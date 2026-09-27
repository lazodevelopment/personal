// Jovi Health — server-side account wipe.
//
// Runs whenever a Firebase Auth user is deleted (the User Profile widget's
// "Delete Account" button, or a deletion from the Firebase console). It is
// the authoritative cleanup: the widget does a best-effort client wipe
// first, this function finishes the job and also clears Storage.
//
// Install (from the functions/ folder of the kurv-health project):
//   npm install firebase-admin@^12 firebase-functions@^5
//   // in index.js:  exports.deleteUserData = require('./deleteUserData').deleteUserData;
//   firebase deploy --only functions:deleteUserData
//
// Requires firebase-admin >= 10 (for Firestore.recursiveDelete).

const functions = require('firebase-functions/v1');
const admin = require('firebase-admin');

if (!admin.apps.length) admin.initializeApp();

// Top-level collections that store records keyed by the member's uid, with
// the field name each one uses. Keep in sync with _topLevelByUser in the
// User Profile widget.
const TOP_LEVEL_BY_USER = {
  appointments: 'userId',
  cancelled_appointments: 'userId',
  helpTickets: 'userId',
  kurv_pass_cancellations: 'userId',
  prescriptionRefills: 'userId',
  prescriptions: 'userId',
  refills: 'userId',
  requests: 'userId',
  security_logs: 'user_id',
};

// Storage folders the widgets write per member. pet_photos/ and
// request_photos/ are keyed by random ids rather than uid and cannot be
// attributed to a member here; the Firestore docs that referenced them are
// gone, so they become unreachable orphans. A scheduled sweep can remove
// them later if storage cost matters.
const STORAGE_PREFIXES = (uid) => [`uploads/${uid}/`, `users/${uid}/`];

const PAGE = 200;

async function deleteWhere(db, collection, field, uid) {
  // Loop until the query is empty: a member can have more than one page.
  for (;;) {
    const snap = await db.collection(collection).where(field, '==', uid).limit(PAGE).get();
    if (snap.empty) return;
    await Promise.all(snap.docs.map((d) => db.recursiveDelete(d.ref)));
    if (snap.size < PAGE) return;
  }
}

exports.deleteUserData = functions
  .runWith({ timeoutSeconds: 540, memory: '512MB' })
  .auth.user()
  .onDelete(async (user) => {
    const uid = user.uid;
    const db = admin.firestore();
    functions.logger.info(`deleteUserData: start uid=${uid}`);

    // 1. users/{uid} and every subcollection beneath it, however deep.
    try {
      await db.recursiveDelete(db.doc(`users/${uid}`));
    } catch (err) {
      functions.logger.error(`deleteUserData: users/${uid} tree failed`, err);
    }

    // 2. Top-level records that reference this member.
    for (const [collection, field] of Object.entries(TOP_LEVEL_BY_USER)) {
      try {
        await deleteWhere(db, collection, field, uid);
      } catch (err) {
        functions.logger.error(`deleteUserData: ${collection} failed`, err);
      }
    }

    // 3. Uploaded files (receipts, pet photos, correspondence).
    const bucket = admin.storage().bucket();
    for (const prefix of STORAGE_PREFIXES(uid)) {
      try {
        await bucket.deleteFiles({ prefix, force: true });
      } catch (err) {
        functions.logger.error(`deleteUserData: storage ${prefix} failed`, err);
      }
    }

    functions.logger.info(`deleteUserData: done uid=${uid}`);
  });
