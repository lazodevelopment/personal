// ============================================================
// LAZO TEAM — admin user management callables
// Build ID: JC-LAZO-TEAM-0820-002
//
// Paste these three exports into your Lazo functions/index.js
// (they assume firebase-admin is already initialized there, as it
// is for claimApprovedEmail etc.), then deploy just these:
//
//   firebase deploy --only functions:adminCreateUser,functions:adminSetRole,functions:adminRevokeUser --project lazo-513ec
//
// (Check `firebase login:list` first — CLI must be on the account
// that owns lazo-513ec, not the LeaseReputation login.)
//
// Model:
//   - Founder account (custom claim admin:true) = permanent owner.
//   - Employees = admins/{uid} docs, role 'admin' or 'owner'.
//   - Rules' merged isAdmin() already accepts both — no rules change.
//   - Revoke deletes the admins doc + kills refresh tokens. It does
//     NOT disable the Auth account, deliberately: if the email also
//     belongs to a vendor/couple account, disabling would lock them
//     out of Lazo itself, not just the admin panel.
// ============================================================
const { onCall, HttpsError } = require("firebase-functions/v2/https");
const { getAuth } = require("firebase-admin/auth");
const { getFirestore, FieldValue } = require("firebase-admin/firestore");

async function assertOwner(request) {
  if (!request.auth) throw new HttpsError("unauthenticated", "Sign in required.");
  const { uid, token } = request.auth;
  if (token.admin === true) return uid; // founder claim = owner
  const snap = await getFirestore().doc(`admins/${uid}`).get();
  if (snap.exists && snap.data().role === "owner") return uid;
  throw new HttpsError("permission-denied", "Owner access required.");
}

exports.adminCreateUser = onCall(async (request) => {
  const callerUid = await assertOwner(request);
  const { email, password, role, name } = request.data || {};
  if (!email || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email))
    throw new HttpsError("invalid-argument", "Valid email required.");
  if (!password || password.length < 8)
    throw new HttpsError("invalid-argument", "Password must be at least 8 characters.");
  if (!["admin", "owner"].includes(role))
    throw new HttpsError("invalid-argument", "Role must be 'admin' or 'owner'.");

  let user, existed = false;
  try {
    user = await getAuth().createUser({ email, password });
  } catch (e) {
    if (e.code === "auth/email-already-exists") {
      // Existing Lazo account (e.g. a vendor) being granted admin access.
      // We grant via the admins doc and leave their password untouched.
      user = await getAuth().getUserByEmail(email);
      existed = true;
    } else {
      throw new HttpsError("internal", e.message);
    }
  }

  const displayName = (name || "").trim();
  if (displayName) {
    // Set/refresh the Auth profile name so it travels with the account
    // (email templates, future in-app surfaces).
    try { await getAuth().updateUser(user.uid, { displayName }); } catch (e) {}
  }

  await getFirestore().doc(`admins/${user.uid}`).set({
    email,
    role,
    name: displayName || (existed ? (user.displayName || "") : ""),
    createdAt: FieldValue.serverTimestamp(),
    createdBy: callerUid,
  });

  return { uid: user.uid, email, existed };
});

exports.adminSetRole = onCall(async (request) => {
  await assertOwner(request);
  const { uid, role } = request.data || {};
  if (!uid || !["admin", "owner"].includes(role))
    throw new HttpsError("invalid-argument", "uid and a valid role are required.");
  await getFirestore().doc(`admins/${uid}`).update({ role });
  return { ok: true };
});

exports.adminRevokeUser = onCall(async (request) => {
  const callerUid = await assertOwner(request);
  const { uid } = request.data || {};
  if (!uid) throw new HttpsError("invalid-argument", "uid required.");
  if (uid === callerUid) throw new HttpsError("failed-precondition", "You can't revoke yourself.");
  await getFirestore().doc(`admins/${uid}`).delete();
  await getAuth().revokeRefreshTokens(uid); // active sessions die within the hour; gate check fails immediately on next load
  return { ok: true };
});
