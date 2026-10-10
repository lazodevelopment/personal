// scripts/backfill_missing_users.js - JC-LAZO-USERS-1009 one-off
// Signups between the Sep 29 rules deploy and JC-LAZO-RULES-1009-017 were refused their users/{uid}
// create (signupSource missing from the allowlist). This writes users/{uid} {uid, email, created_time}
// from Firebase Auth for every password/social account without one, plus role 'couple' when a couples
// doc exists. Existing users docs are never touched.
//
//   node scripts/backfill_missing_users.js            dry run
//   node scripts/backfill_missing_users.js --apply    writes
//
// Credentials: gcloud application-default login as a project owner; set GOOGLE_CLOUD_QUOTA_PROJECT=lazo-513ec.
'use strict';
const admin = require('../functions/node_modules/firebase-admin');
admin.initializeApp({ projectId: 'lazo-513ec' });
const db = admin.firestore();
const apply = process.argv.includes('--apply');
const since = Date.parse('2026-09-29T00:00:00Z');

(async () => {
  let page, users = [];
  do { const r = await admin.auth().listUsers(1000, page); users.push(...r.users); page = r.pageToken; } while (page);
  const todo = users.filter(u => u.email && Date.parse(u.metadata.creationTime) >= since);
  for (const u of todo) {
    const ref = db.collection('users').doc(u.uid);
    if ((await ref.get()).exists) continue;
    const isCouple = (await db.collection('couples').doc(u.uid).get()).exists;
    const data = { uid: u.uid, email: u.email, created_time: admin.firestore.Timestamp.fromDate(new Date(u.metadata.creationTime)) };
    if (u.displayName) data.display_name = u.displayName;
    if (isCouple) data.role = 'couple';
    console.log(`${apply ? 'WRITE' : 'would write'} users/${u.uid}  ${u.email}${isCouple ? '  role=couple' : ''}`);
    if (apply) await ref.create(data);
  }
  if (!apply) console.log('\nDry run. Re-run with --apply to write.');
})().catch(e => { console.error(e.message); process.exit(1); });
