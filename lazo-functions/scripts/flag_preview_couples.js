// scripts/flag_preview_couples.js - JC-LAZO-COUPLE-1007-V146 one-off
// Vendors who tapped "Couple view" before dashboard v146 left a real couples/{uid} plan behind, counted
// as a couple by analytics. This marks every couples doc whose login is a vendor (users.role == 'vendor',
// or users.vendorId set, or a vendors doc with claimedBy == uid) with preview: true, plus its plan rows,
// so analytics, the welcome email and the milestone emails skip it. Nothing is deleted.
//
//   node scripts/flag_preview_couples.js            dry run: prints what would change
//   node scripts/flag_preview_couples.js --apply    writes the flags
//
// Credentials: GOOGLE_APPLICATION_CREDENTIALS=<service account json with Firestore write on lazo-513ec>,
// or gcloud application-default login as a project owner.
'use strict';
const admin = require('../functions/node_modules/firebase-admin');
admin.initializeApp({ projectId: 'lazo-513ec' });
const db = admin.firestore();
const apply = process.argv.includes('--apply');
const str = (v) => (v == null ? '' : String(v));

(async () => {
  const couples = await db.collection('couples').get();
  const rows = [];
  for (const d of couples.docs) {
    const c = d.data();
    if (c.preview === true) continue;
    if (d.id.startsWith('demo_')) continue;
    let why = '';
    const u = await db.collection('users').doc(d.id).get();
    const ud = u.exists ? u.data() : {};
    if (str(ud.role) === 'vendor') why = 'users.role=vendor';
    else if (str(ud.vendorId)) why = 'users.vendorId=' + ud.vendorId;
    else {
      const q = await db.collection('vendors').where('claimedBy', '==', d.id).limit(1).get();
      if (!q.empty) why = 'claimedBy -> ' + q.docs[0].id;
    }
    if (!why) continue;
    rows.push({ id: d.id, why, names: str(c.names), email: str(ud.email), plan: (await d.ref.collection('plan').get()).size });
  }
  console.log(`${couples.size} couples scanned; ${rows.length} belong to vendor logins:`);
  for (const r of rows) console.log(`  ${r.id}  ${r.email || '-'}  ${r.names || '-'}  (${r.why}, ${r.plan} plan rows)`);
  if (!apply) { console.log('\nDry run. Re-run with --apply to flag them.'); return; }
  let n = 0;
  for (const r of rows) {
    const ref = db.collection('couples').doc(r.id);
    const batch = db.batch();
    batch.set(ref, { preview: true, previewFlaggedAt: admin.firestore.FieldValue.serverTimestamp(), previewWhy: r.why }, { merge: true });
    const plan = await ref.collection('plan').get();
    plan.forEach((p) => batch.set(p.ref, { preview: true }, { merge: true }));
    await batch.commit(); n++;
  }
  console.log(`Flagged ${n} couples as preview.`);
})().catch((e) => { console.error(e.message); process.exit(1); });
