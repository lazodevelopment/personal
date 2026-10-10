// scripts/audit_recent_signups.js - read-only: compares recent Firebase Auth sign-ups with couples/ and users/ docs
'use strict';
const admin = require('../functions/node_modules/firebase-admin');
admin.initializeApp({ projectId: 'lazo-513ec' });
const db = admin.firestore();
const since = Date.now() - 14 * 864e5;
(async () => {
  let page, users = [];
  do { const r = await admin.auth().listUsers(1000, page); users.push(...r.users); page = r.pageToken; } while (page);
  const recent = users.filter(u => Date.parse(u.metadata.creationTime) >= since)
    .sort((a, b) => Date.parse(b.metadata.creationTime) - Date.parse(a.metadata.creationTime));
  for (const u of recent) {
    const [c, ud] = await Promise.all([db.collection('couples').doc(u.uid).get(), db.collection('users').doc(u.uid).get()]);
    const cd = c.exists ? c.data() : null, d = ud.exists ? ud.data() : null;
    console.log(JSON.stringify({
      uid: u.uid, email: u.email, providers: u.providerData.map(p => p.providerId), created: u.metadata.creationTime,
      lastSignIn: u.metadata.lastSignInTime,
      couplesDoc: cd ? { names: cd.names, createdAt: cd.createdAt && cd.createdAt.toDate && cd.createdAt.toDate().toISOString(), preview: cd.preview, weddingDate: !!cd.weddingDate } : null,
      usersDoc: d ? { email: d.email, display_name: d.display_name, role: d.role, vendorId: d.vendorId, keys: Object.keys(d).join(',') } : null,
    }));
  }
  // couples docs created in the window with no matching auth user
  const cs = await db.collection('couples').where('createdAt', '>=', admin.firestore.Timestamp.fromMillis(since)).get();
  const uids = new Set(users.map(u => u.uid));
  cs.forEach(d => { if (!uids.has(d.id)) console.log('COUPLES DOC WITHOUT AUTH USER:', d.id, JSON.stringify(d.data()).slice(0, 300)); });
})().catch(e => { console.error(e.message); process.exit(1); });
