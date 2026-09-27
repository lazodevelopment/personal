// Staff auth + roles. A staff member is a Firebase Auth user with a document at
// staff/{uid} = { role, name, email, active, npi?, clinicId?, createdAt }.
// Roles:
//   superadmin  everything, incl. staff management
//   admin       business side (no PHI) + operations queues
//   exec        business side, read-only
//   clinician   EHR (PHI) — providers, nurses, care team
//   support     support inbox + refills + member lookup (limited PHI)
// Bootstrap: create the first staff doc by hand in the Firebase console.
import { auth, db, doc, getDoc, setDoc, onAuthStateChanged, signInWithEmailAndPassword, signOut, serverTimestamp, updateDoc, sendPasswordResetEmail } from './firebase.js';

export const ROLES = ['superadmin', 'admin', 'exec', 'clinician', 'support'];
// Emails allowed to self-provision as superadmin on first sign-in (mirrored in firestore.rules).
const BOOTSTRAP_SUPERADMINS = ['jesse@briskhealth.com'];
export const SIDES = {
  admin: ['superadmin', 'admin', 'exec', 'support'],   // business workspace (#/admin/...)
  ehr: ['superadmin', 'clinician', 'support'],
};
export const CAN = {
  manageStaff: r => r === 'superadmin',
  writeBusiness: r => ['superadmin', 'admin'].includes(r),
  chart: r => ['superadmin', 'clinician'].includes(r),          // write clinical notes / orders
  viewPhi: r => ['superadmin', 'clinician', 'support'].includes(r),
  decideClaims: r => ['superadmin', 'admin', 'clinician'].includes(r),
  refills: r => ['superadmin', 'clinician', 'support'].includes(r),
};

export const session = { user: null, staff: null, role: null, ready: false };
const listeners = new Set();
export const onSession = fn => { listeners.add(fn); if (session.ready) fn(session); return () => listeners.delete(fn); };
const emit = () => listeners.forEach(fn => fn(session));

onAuthStateChanged(auth, async user => {
  session.user = user; session.staff = null; session.role = null;
  if (user) {
    try {
      let snap = await getDoc(doc(db, 'staff', user.uid));
      if (!snap.exists() && BOOTSTRAP_SUPERADMINS.includes((user.email || '').toLowerCase())) {
        await setDoc(doc(db, 'staff', user.uid), { role: 'superadmin', name: user.displayName || user.email.split('@')[0], email: user.email.toLowerCase(), active: true, title: 'Founder', createdAt: serverTimestamp(), createdBy: 'bootstrap' });
        snap = await getDoc(doc(db, 'staff', user.uid));
      }
      if (snap.exists() && snap.data().active !== false) {
        session.staff = { id: snap.id, ...snap.data() };
        session.role = session.staff.role;
        updateDoc(doc(db, 'staff', user.uid), { lastSeenAt: serverTimestamp(), lastEmail: user.email }).catch(() => {});
      }
    } catch (e) { console.warn('staff lookup failed', e); session.error = e; }
  }
  session.ready = true; emit();
});

export const signIn = (email, password) => signInWithEmailAndPassword(auth, email, password);
export const logOut = () => signOut(auth);
export const resetPassword = email => sendPasswordResetEmail(auth, email);
export const can = (perm) => !!session.role && CAN[perm](session.role);
export const canSide = (side) => !!session.role && !!SIDES[side] && SIDES[side].includes(session.role);

// Audit trail: every staff mutation of member data lands in audit_logs so the
// business side can review access without touching PHI content.
export async function audit(action, target, meta = {}) {
  try {
    const { addDoc, collection } = await import('./firebase.js');
    await addDoc(collection(db, 'audit_logs'), {
      action, target: target || null, meta,
      staffId: session.user?.uid || null, staffEmail: session.user?.email || null, role: session.role || null,
      at: serverTimestamp(), ua: navigator.userAgent.slice(0, 120),
    });
  } catch (e) { console.warn('audit failed', e); }
}
