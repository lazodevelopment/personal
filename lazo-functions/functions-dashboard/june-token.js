// functions-dashboard/june-token.js
// Build ID: JC-LAZO-FNDASH-1005-022
//
// juneToken: the vendor dashboard's "Talk to June" button asks for a short-lived
// Firebase custom token, then opens the June hub with ?t=<token>. The hub
// exchanges it at Identity Toolkit (signInWithCustomToken) so the vendor lands
// signed in, no second password. Custom tokens live one hour and can only be
// exchanged once per sign-in; nothing is stored here.
//
//   juneToken  callable {} -> { token, uid }

'use strict';

const { onCall, HttpsError } = require('firebase-functions/v2/https');
const admin = require('firebase-admin');

const juneToken = onCall({ memory: '256MiB' }, async (request) => {
  const uid = request.auth && request.auth.uid;
  if (!uid) throw new HttpsError('unauthenticated', 'Sign in first.');
  const token = await admin.auth().createCustomToken(uid, { june: true });
  return { token, uid };
});

module.exports = { juneToken };

// END OF FILE - JC-LAZO-FNDASH-1005-022
