// scripts/mark_legacy_users.js - JC-LAZO-FNDASH-1016-027: grandfather the accounts that predate email verification.
//
// firestore.rules now wants a verified email (token.email_verified) for everything but the user's own users doc.
// Nobody was ever asked to verify before, so every existing account gets the custom claim legacy:true, which the
// rules accept in place of a verified email. Only accounts created BEFORE --before are marked: anyone who signs up
// after Auth v24 is published goes through the code step instead (and an abandoned signup stays locked).
// Existing custom claims (admin, worker, ...) are kept. Tokens pick the claim up on their next hourly refresh, so
// run this at least an hour before deploying the rules.
//
//   node scripts/mark_legacy_users.js --before 2026-10-17T15:00:00Z           # dry run: counts + a sample
//   node scripts/mark_legacy_users.js --before 2026-10-17T15:00:00Z --apply   # writes the claims
//
// Needs Application Default Credentials for lazo-513ec (gcloud auth application-default login as the project owner).
'use strict';
const admin = require('../functions/node_modules/firebase-admin');
admin.initializeApp({ projectId: 'lazo-513ec' });

const arg = (k) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : null; };
const before = Date.parse(arg('--before') || '');
const apply = process.argv.includes('--apply');
if (!before) { console.error('usage: --before <ISO time of the Auth v24 publish> [--apply]'); process.exit(2); }

(async () => {
  let page, users = [];
  do { const r = await admin.auth().listUsers(1000, page); users.push(...r.users); page = r.pageToken; } while (page);
  const old = users.filter((u) => Date.parse(u.metadata.creationTime) < before);
  const need = old.filter((u) => !u.emailVerified && !(u.customClaims && u.customClaims.legacy === true));
  console.log(JSON.stringify({
    totalAccounts: users.length,
    createdBefore: old.length,
    alreadyVerified: old.filter((u) => u.emailVerified).length,
    alreadyLegacy: old.filter((u) => u.customClaims && u.customClaims.legacy === true).length,
    toMark: need.length,
    createdAfter: users.length - old.length,
    mode: apply ? 'APPLY' : 'dry run',
  }, null, 1));
  need.slice(0, 10).forEach((u) => console.log('  e.g.', u.uid, u.email || '(no email)', u.metadata.creationTime, JSON.stringify(u.customClaims || {})));
  if (!apply) return;
  let done = 0;
  for (const u of need) {
    await admin.auth().setCustomUserClaims(u.uid, { ...(u.customClaims || {}), legacy: true });
    if (++done % 200 === 0) console.log('  marked', done);
  }
  console.log('marked', done);
})().catch((e) => { console.error(e); process.exit(1); });
