// verify_admin.js — LeaseReputation admin CLI (firebase-admin v13 modular API)
//
// Usage:
//   node verify_admin.js list
//   node verify_admin.js approve <uid>
//   node verify_admin.js reject <uid> "Reason shown to the user"
//   node verify_admin.js backfill-claims

const { initializeApp, cert } = require('firebase-admin/app');
const { getFirestore, FieldValue } = require('firebase-admin/firestore');
const { getAuth } = require('firebase-admin/auth');
const { getStorage } = require('firebase-admin/storage');
const serviceAccount = require('./serviceAccountKey.json');

initializeApp({
  credential: cert(serviceAccount),
  storageBucket: `${serviceAccount.project_id}.firebasestorage.app`,
});
const db = getFirestore();
const auth = getAuth();
const bucket = getStorage().bucket();

async function deleteVerificationDocs(uid) {
  await bucket
    .deleteFiles({ prefix: `verification-docs/${uid}/` })
    .catch((e) => console.error(`  doc cleanup failed: ${e.message}`));
}

// ── list: the human queue ──────────────────────────────────────
async function list() {
  const snap = await db
    .collection('verifications')
    .where('status', 'in', ['pending', 'needs_review'])
    .get();
  if (snap.empty) {
    console.log('Queue is empty. 🎉');
    return;
  }
  for (const doc of snap.docs) {
    const d = doc.data();
    const user = await db.collection('users').doc(doc.id).get();
    console.log('────────────────────────────────────────');
    console.log(`uid:        ${doc.id}`);
    console.log(`name:       ${(user.data() && user.data().name) || '(none)'}`);
    console.log(`status:     ${d.status}`);
    console.log(`community:  ${d.communityName || ''} (${d.communityId || ''})`);
    console.log(`submitted:  ${d.submittedAt ? d.submittedAt.toDate().toISOString() : ''}`);
    if (d.aiNotes) console.log(`AI notes:   ${d.aiNotes}`);
    if (d.aiChecks) console.log(`AI checks:  ${JSON.stringify(d.aiChecks)}`);
    console.log(
      `docs:       Firebase Console → Storage → verification-docs/${doc.id}/`
    );
  }
  console.log('────────────────────────────────────────');
  console.log(`${snap.size} in queue.`);
}

// ── approve: mirrors the Cloud Function's approveVerification ──
async function approve(uid) {
  const ver = await db.collection('verifications').doc(uid).get();
  if (!ver.exists) return console.error(`No verification doc for ${uid}.`);
  const communityId = ver.data().communityId;
  const communityName = ver.data().communityName || '';
  if (!communityId) return console.error('Verification is missing communityId.');

  const userRecord = await auth.getUser(uid);
  const claims = { ...(userRecord.customClaims || {}) };
  if (!claims.role) claims.role = 'renter';
  claims.identityVerified = true;
  await auth.setCustomUserClaims(uid, claims);

  await db.collection('users').doc(uid).set(
    { identityVerified: true, residencyVerified: true },
    { merge: true }
  );

  await db
    .collection('users')
    .doc(uid)
    .collection('residencies')
    .doc(communityId)
    .set({
      communityId,
      communityName,
      verifiedAt: FieldValue.serverTimestamp(),
      verifiedBy: 'admin',
    });

  await deleteVerificationDocs(uid);

  await db.collection('verifications').doc(uid).set(
    {
      status: 'approved',
      reviewedAt: FieldValue.serverTimestamp(),
      reviewedBy: 'admin',
    },
    { merge: true }
  );

  console.log(`✔ Approved ${uid} @ ${communityName || communityId}. Docs deleted.`);
}

// ── reject ─────────────────────────────────────────────────────
async function reject(uid, reason) {
  if (!reason) return console.error('Provide a reason: reject <uid> "reason"');
  await deleteVerificationDocs(uid);
  await db.collection('verifications').doc(uid).set(
    {
      status: 'rejected',
      rejectionReason: reason.slice(0, 300),
      reviewedAt: FieldValue.serverTimestamp(),
      reviewedBy: 'admin',
    },
    { merge: true }
  );
  console.log(`✔ Rejected ${uid}. Docs deleted. User can resubmit.`);
}

// ── backfill-claims: for accounts created before the trigger ───
async function backfillClaims() {
  let pageToken;
  let stamped = 0;
  let skipped = 0;
  do {
    const page = await auth.listUsers(1000, pageToken);
    for (const u of page.users) {
      const claims = u.customClaims || {};
      if (claims.role) {
        skipped++;
        continue;
      }
      await auth.setCustomUserClaims(u.uid, { ...claims, role: 'renter' });
      stamped++;
      console.log(`  + renter claim → ${u.email || u.uid}`);
    }
    pageToken = page.pageToken;
  } while (pageToken);
  console.log(`✔ Backfill complete: ${stamped} stamped, ${skipped} already had a role.`);
}

// ── dispatch ───────────────────────────────────────────────────
(async () => {
  const [cmd, uid, reason] = process.argv.slice(2);
  try {
    if (cmd === 'list') await list();
    else if (cmd === 'approve' && uid) await approve(uid);
    else if (cmd === 'reject' && uid) await reject(uid, reason);
    else if (cmd === 'backfill-claims') await backfillClaims();
    else {
      console.log('Usage:');
      console.log('  node verify_admin.js list');
      console.log('  node verify_admin.js approve <uid>');
      console.log('  node verify_admin.js reject <uid> "Reason shown to user"');
      console.log('  node verify_admin.js backfill-claims');
    }
  } catch (e) {
    console.error('Error:', e.message || e);
  }
  process.exit(0);
})();