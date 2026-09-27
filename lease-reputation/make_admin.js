// make_admin.js — one-off: grant the admin custom claim (firebase-admin v13 modular)
// Usage: node make_admin.js leasereputation@gmail.com
const { initializeApp, cert } = require('firebase-admin/app');
const { getAuth } = require('firebase-admin/auth');
const serviceAccount = require('./serviceAccountKey.json');

initializeApp({ credential: cert(serviceAccount) });
const auth = getAuth();

(async () => {
  const email = process.argv[2];
  if (!email) return console.error('Usage: node make_admin.js <email>');
  const user = await auth.getUserByEmail(email);
  await auth.setCustomUserClaims(user.uid, {
    ...(user.customClaims || {}),
    admin: true,
  });
  console.log(`admin:true set for ${email} (${user.uid})`);
  const check = await auth.getUser(user.uid);
  console.log('claims now:', JSON.stringify(check.customClaims));
})().catch((e) => { console.error(e.message); process.exit(1); });