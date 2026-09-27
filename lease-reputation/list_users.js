const { initializeApp, cert } = require('firebase-admin/app');
const { getAuth } = require('firebase-admin/auth');
initializeApp({ credential: cert(require('./serviceAccountKey.json')) });
getAuth().listUsers(50).then((r) => {
  r.users.forEach((u) =>
    console.log(`${u.email || '(no email)'}  uid=${u.uid}  claims=${JSON.stringify(u.customClaims || {})}`)
  );
});