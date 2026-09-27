// Data layer: the ONLY module that knows Firestore paths and field names.
// Mirrors the member app (see SCHEMA.md). Every staff mutation goes through
// here so it can be audited and so app-side triggers fire with the right fields.
import {
  db, storage, functions, collection, collectionGroup, doc, getDoc, getDocs, setDoc, addDoc, updateDoc, deleteDoc,
  query, where, orderBy, limit, startAfter, onSnapshot, writeBatch, serverTimestamp, Timestamp, deleteField, increment,
  httpsCallable, storageRef, uploadBytes, getDownloadURL,
} from './firebase.js';
import { session, audit } from './auth.js';
import { toDate, todayStr, apptWhen } from './ui.js';

// ── Constants shared with the app ───────────────────────────────────────
export const CLINICS = [
  { key: 'Littleton - Dakota Ridge', short: 'Dakota Ridge', city: 'Littleton', state: 'CO', tz: 'America/Denver' },
  { key: 'Scottsdale - Scottsdale Gateway', short: 'Scottsdale Gateway', city: 'Scottsdale', state: 'AZ', tz: 'America/Phoenix' },
  { key: 'Dallas - Medical City Campus', short: 'Medical City Campus', city: 'Dallas', state: 'TX', tz: 'America/Chicago' },
];
export const REQUEST_STATUSES = ['pending', 'confirmed', 'rescheduled', 'completed', 'no_show', 'cancelled', 'declined'];
export const REFILL_STATUSES = ['requested', 'approved', 'processing', 'ready', 'filled', 'completed', 'denied', 'cancelled'];
export const CLAIM_STATUSES = ['submitted', 'under_review', 'needs_more_info', 'approved', 'paid', 'rejected'];
export const VISIT_TYPES = ['Urgent Care', 'Primary Care', 'Wellness', 'Sick or Injured'];
export const JOVI_PASS_PRICE = 49;
export const HUMAN_SLOTS = (() => { const out = []; for (let h = 9; h <= 16; h++) for (const m of [0, 30]) { if (h === 16 && m === 30) { out.push('4:30 PM'); continue; } out.push(fmtSlot(h, m)); } return out; })();
export const PET_SLOTS = (() => { const out = []; for (let h = 8; h <= 17; h++) for (const m of [0, 30]) out.push(fmtSlot(h, m)); return out; })();
function fmtSlot(h, m) { const ap = h >= 12 ? 'PM' : 'AM'; const hh = h % 12 === 0 ? 12 : h % 12; return `${hh}:${String(m).padStart(2, '0')} ${ap}`; }

/** Parse the app's 'h:mm AM/PM' (or 'HH:mm') into {h,m}. */
export function parseSlot(t) {
  if (!t) return null; const s = String(t).trim();
  const m = s.match(/^(\d{1,2}):(\d{2})\s*(AM|PM)?$/i); if (!m) return null;
  let h = +m[1]; const mm = +m[2]; const ap = (m[3] || '').toUpperCase();
  if (ap === 'PM' && h < 12) h += 12; if (ap === 'AM' && h === 12) h = 0;
  return { h, m: mm };
}
/** Date object for a request's local wall-clock start (AM/PM aware). */
export function requestStart(r) {
  if (r.startAt) return toDate(r.startAt);
  const p = parseSlot(r.appointmentTime); const day = String(r.appointmentDate || '').slice(0, 10);
  if (!day) return null; const d = new Date(`${day}T00:00:00`); if (isNaN(d)) return null;
  if (p) d.setHours(p.h, p.m, 0, 0); return d;
}
export const appointmentDateStr = (d) => `${todayStr(d)}T00:00:00`;

// ── Helpers ─────────────────────────────────────────────────────────────
const snapRows = s => s.docs.map(d => ({ id: d.id, ref: d.ref, path: d.ref.path, ...d.data() }));
export const parseJsonArr = arr => (Array.isArray(arr) ? arr : []).map(x => { if (typeof x === 'string') { try { return JSON.parse(x); } catch { return null; } } return x; }).filter(Boolean);
export function memberName(u = {}) { return u.onboard_fullName || [u.first || u.firstName, u.last || u.lastName].filter(Boolean).join(' ') || u.display_name || u.email || 'Member'; }
export function memberPhoto(u = {}) { return u.photo_url || u.profilePhotoUrl || u.image_path || null; }
export function memberDob(u = {}) { return u.onboard_birth || u.birth || u.dob || u.birth_date || null; }
export function parseDob(s) { if (!s) return null; if (typeof s !== 'string') return toDate(s); const m = s.match(/^(\d{1,2})[\/-](\d{1,2})[\/-](\d{4})$/); if (m) return new Date(+m[3], +m[1] - 1, +m[2]); const d = new Date(s); return isNaN(d) ? null : d; }
export function monthlyTotal(u = {}) { const g = Number(u.grandTotal); if (g > 0) return g; return (Number(u.totalHealthPremium ?? u.totalPremium) || 0) + (Number(u.petTotalPremium) || 0); }
export function deductibleOf(u = {}) { const m = parseJsonArr(u.members); return Number(m[0]?.deductible ?? u.healthDeductible ?? u.deductible) || 1500; }
export function subStatus(u = {}) { const s = String(u.subscriptionStatus || (u.membershipStatus === 'inactive' ? 'inactive' : '') || (u.isActive === false ? 'inactive' : 'active')).toLowerCase(); return s === 'cancelled' ? 'canceled' : s; }
export function nextBilling(u = {}) {
  const nb = toDate(u.nextBillingDate); if (nb && nb > new Date()) return nb;
  const renew = toDate(u.renew); if (!renew) return null;
  const now = new Date(); const d = new Date(now.getFullYear(), now.getMonth(), renew.getDate()); if (d <= now) d.setMonth(d.getMonth() + 1); return d;
}
export function dependentsOf(u = {}) {
  const a = parseJsonArr(u.dependents).map(d => ({ memberId: d.memberId, firstName: d.firstName, lastName: d.lastName, dob: d.dob, gender: d.gender, relationship: d.relationship, photo: d.photo_url }));
  if (a.length) return a;
  return parseJsonArr(u.deps).map(d => ({ memberId: d.memberId, firstName: d.first, lastName: d.last, dob: d.birth, photo: d.photo_url }));
}
export function spouseOf(u = {}) { if (u.hasSpouse || u.spouse) return { firstName: u.spouseFirstName || u.sFirst, lastName: u.spouseLastName || u.sLast, dob: u.spouseDob || u.sBirth, photo: u.spousePhotoUrl || u.sPhoto_url }; return null; }
export function patientNames(u = {}) { const names = [memberName(u)]; const s = spouseOf(u); if (s) names.push([s.firstName, s.lastName].filter(Boolean).join(' ')); for (const d of dependentsOf(u)) names.push([d.firstName, d.lastName].filter(Boolean).join(' ')); return names.filter(Boolean); }

// ── Members ─────────────────────────────────────────────────────────────
export async function getMember(uid) { const s = await getDoc(doc(db, 'users', uid)); return s.exists() ? { id: s.id, ...s.data() } : null; }
export async function listMembers({ max = 500 } = {}) {
  const s = await getDocs(query(collection(db, 'users'), limit(max)));
  return snapRows(s).map(u => ({ ...u, name: memberName(u), photo: memberPhoto(u), status: subStatus(u), monthly: monthlyTotal(u) }));
}
let memberCache = null, memberCacheAt = 0;
export async function cachedMembers(force = false) { if (!force && memberCache && Date.now() - memberCacheAt < 60000) return memberCache; memberCache = await listMembers({ max: 2000 }); memberCacheAt = Date.now(); return memberCache; }
export async function findMembers(q, max = 10) {
  const all = await cachedMembers(); const s = q.toLowerCase();
  return all.filter(u => (u.name || '').toLowerCase().includes(s) || (u.email || '').toLowerCase().includes(s) || (u.phone || u.onboard_phone || u.phone_number || '').replace(/\D/g, '').includes(s.replace(/\D/g, '') || '#')).slice(0, max);
}
export async function updateMember(uid, patch, action = 'member.update') { await updateDoc(doc(db, 'users', uid), { ...patch, staffUpdatedAt: serverTimestamp(), staffUpdatedBy: session.user.uid }); await audit(action, `users/${uid}`, { keys: Object.keys(patch) }); }
export const sub = (uid, name, ...q) => getDocs(query(collection(db, 'users', uid, name), ...q)).then(snapRows);
export async function memberNotes(uid) { return sub(uid, 'staff_notes', orderBy('createdAt', 'desc')); }
export async function addMemberNote(uid, text, kind = 'general') { await addDoc(collection(db, 'users', uid, 'staff_notes'), { text, kind, by: session.user.email, byId: session.user.uid, createdAt: serverTimestamp() }); await audit('member.note', `users/${uid}`, { kind }); }
export async function notifyMember(uid, { type = 'system', title, body, route = null, params = {}, refPath = null }) {
  await addDoc(collection(db, 'users', uid, 'notifications'), { type, title, body, route, params, refPath, read: false, createdAt: serverTimestamp(), sentBy: session.user.uid });
  await audit('member.notify', `users/${uid}`, { type, title });
}
export async function cancelMembershipViaBackend(reason, uid) {
  // The app's callable acts on the caller; for staff we set the same fields the function sets and log it.
  const now = new Date(); const u = await getMember(uid); const end = nextBilling(u) || now;
  await updateMember(uid, { subscriptionStatus: 'canceling', willCancelOn: Timestamp.fromDate(end), finalBillingDate: Timestamp.fromDate(end), canceledAt: serverTimestamp(), cancelReason: reason, canceledByStaff: session.user.email }, 'membership.cancel');
}
export async function reactivateMembership(uid) { await updateMember(uid, { subscriptionStatus: 'active', membershipStatus: 'active', willCancelOn: deleteField(), finalBillingDate: deleteField(), canceledAt: deleteField(), cancelReason: deleteField(), cancellationReversedAt: serverTimestamp() }, 'membership.reactivate'); }
export async function memberDependentsSub(uid) { return sub(uid, 'dependents'); }

// ── Appointments (requests) ─────────────────────────────────────────────
export async function requestsBetween(fromDay, toDay, { clinic = null } = {}) {
  // appointmentDate is a string 'yyyy-MM-ddT00:00:00'; string range works because of the fixed format.
  const parts = [where('appointmentDate', '>=', `${fromDay}T00:00:00`), where('appointmentDate', '<=', `${toDay}T23:59:59`)];
  if (clinic) parts.push(where('clinic', '==', clinic));
  const s = await getDocs(query(collection(db, 'requests'), ...parts, limit(1000)));
  return snapRows(s).map(decorateRequest).sort((a, b) => (a.start?.getTime() || 0) - (b.start?.getTime() || 0));
}
export async function requestsForUser(uid) { const s = await getDocs(query(collection(db, 'requests'), where('userId', '==', uid), limit(300))); return snapRows(s).map(decorateRequest).sort((a, b) => (b.start?.getTime() || 0) - (a.start?.getTime() || 0)); }
export async function pendingRequests() { const s = await getDocs(query(collection(db, 'requests'), where('status', '==', 'pending'), limit(300))); return snapRows(s).map(decorateRequest).sort((a, b) => (a.start?.getTime() || 0) - (b.start?.getTime() || 0)); }
export async function allRequests(max = 2000) { const s = await getDocs(query(collection(db, 'requests'), limit(max))); return snapRows(s).map(decorateRequest); }
export function decorateRequest(r) { return { ...r, start: requestStart(r), isPet: r.audience === 'Pet', statusL: String(r.status || '').toLowerCase() }; }
export async function getRequest(id) { const s = await getDoc(doc(db, 'requests', id)); return s.exists() ? decorateRequest({ id: s.id, ...s.data() }) : null; }
export async function updateRequest(id, patch, action = 'appointment.update') { await updateDoc(doc(db, 'requests', id), { ...patch, updatedAt: serverTimestamp(), updatedBy: session.user.uid }); await audit(action, `requests/${id}`, { keys: Object.keys(patch), status: patch.status }); }
export const confirmRequest = (id, extra = {}) => updateRequest(id, { status: 'confirmed', ...extra }, 'appointment.confirm');
export const completeRequest = (id, extra = {}) => updateRequest(id, { status: 'completed', ...extra }, 'appointment.complete');
export const noShowRequest = (id) => updateRequest(id, { status: 'no_show' }, 'appointment.no_show');
export async function rescheduleRequest(id, day, slot, extra = {}) { await updateRequest(id, { appointmentDate: `${day}T00:00:00`, appointmentTime: slot, status: 'confirmed', rescheduledAt: serverTimestamp(), rescheduledBy: 'clinic', reminders: deleteField(), ...extra }, 'appointment.reschedule'); }
export async function cancelRequestByClinic(r, reason) {
  const b = writeBatch(db);
  b.update(doc(db, 'requests', r.id), { status: 'cancelled', cancelledAt: serverTimestamp(), cancelledBy: 'clinic', cancelledReason: reason, updatedAt: serverTimestamp() });
  b.set(doc(collection(db, 'cancelled_appointments')), { originalAppointmentId: r.id, userId: r.userId, patientName: r.patientName || null, appointmentDate: r.appointmentDate || null, appointmentTime: r.appointmentTime || null, visitType: r.visitType || null, visitMode: r.visitMode || null, clinic: r.clinic || null, symptom: r.symptom || null, wasPriority: !!r.priority, cancelledAt: serverTimestamp(), cancelledBy: 'clinic', cancelledReason: reason, source: 'staff_app', timezone: r.timezone || null });
  await b.commit(); await audit('appointment.cancel', `requests/${r.id}`, { reason });
}
export async function bookedSlots(day, { clinic, visitMode = 'Clinic', pet = false } = {}) {
  const rows = await requestsBetween(day, day, { clinic: visitMode === 'Clinic' ? clinic : null });
  return new Set(rows.filter(r => ['pending', 'confirmed'].includes(r.statusL) && (r.visitMode || 'Clinic') === visitMode && r.isPet === pet).map(r => r.appointmentTime));
}
export async function createRequestForMember(u, { day, slot, visitType, visitMode, clinic, patientName, symptom, details, isPet = false, pet = null }) {
  const data = {
    id: crypto.randomUUID(), userId: u.id, timezone: u.timezone || CLINICS.find(c => c.key === clinic)?.tz || 'America/Chicago',
    visitType, visitMode, clinic: visitMode === 'Clinic' ? clinic : '', patientName, symptom: symptom || 'Staff-scheduled visit', symptomDuration: '', details: details || '', medication: '',
    appointmentDate: `${day}T00:00:00`, appointmentTime: slot, status: 'confirmed', priority: false, kurvPassPurchased: false, estimatedWaitTime: '15-30 minutes',
    createdAt: serverTimestamp(), createdBy: 'staff', createdByStaff: session.user.uid, photoUrl: '',
  };
  if (isPet && pet) Object.assign(data, { audience: 'Pet', petId: pet.id, petName: pet.name, petSpecies: String(pet.type || 'other').toLowerCase(), petBreed: pet.breed || '', petWeightLbs: pet.weightLbs || null, petPhotoUrl: pet.photoUrl || '' });
  const ref = await addDoc(collection(db, 'requests'), data); await audit('appointment.create', `requests/${ref.id}`, { visitType, clinic }); return ref.id;
}
export async function cancelledAppointments(max = 300) { const s = await getDocs(query(collection(db, 'cancelled_appointments'), orderBy('cancelledAt', 'desc'), limit(max))); return snapRows(s); }

// ── Clinical: visit records (encounters) ────────────────────────────────
export const visitRecords = uid => sub(uid, 'visit_records', orderBy('visitDate', 'desc'));
export async function saveVisitRecord(uid, id, data) {
  const ref = id ? doc(db, 'users', uid, 'visit_records', id) : doc(collection(db, 'users', uid, 'visit_records'));
  await setDoc(ref, { ...data, updatedAt: serverTimestamp(), ...(id ? {} : { createdAt: serverTimestamp(), createdBy: session.user.uid }) }, { merge: true });
  if (data.appointmentId) updateDoc(doc(db, 'requests', data.appointmentId), { linkedVisitRecordId: ref.id, updatedAt: serverTimestamp() }).catch(() => {});
  await audit(id ? 'chart.note.update' : 'chart.note.create', ref.path, { signed: !!data.signedAt });
  return ref.id;
}
export async function recentVisitRecords(max = 100) { const s = await getDocs(query(collectionGroup(db, 'visit_records'), orderBy('visitDate', 'desc'), limit(max))); return snapRows(s).map(r => ({ ...r, uid: r.path.split('/')[1] })); }

// ── Clinical: prescriptions & refills ───────────────────────────────────
export async function prescriptionsFor(uid) { const s = await getDocs(query(collection(db, 'prescriptions'), where('userId', '==', uid))); return snapRows(s).sort((a, b) => (toDate(b.createdAt)?.getTime() || 0) - (toDate(a.createdAt)?.getTime() || 0)); }
export async function addPrescription(uid, rx) {
  const data = { userId: uid, status: 'active', daysSupply: 30, refillsRemaining: rx.totalRefills ?? 0, urgent: false, prescribedAt: serverTimestamp(), createdAt: serverTimestamp(), updatedAt: serverTimestamp(), prescribedBy: session.staff?.name || session.user.email, ...rx };
  data.nextRefillDate = Timestamp.fromDate(new Date(Date.now() + (data.daysSupply || 30) * 86400000));
  const ref = await addDoc(collection(db, 'prescriptions'), data); await audit('rx.create', ref.path, { medicationName: rx.medicationName }); return ref.id;
}
export async function updatePrescription(id, patch, action = 'rx.update') { await updateDoc(doc(db, 'prescriptions', id), { ...patch, updatedAt: serverTimestamp() }); await audit(action, `prescriptions/${id}`, { keys: Object.keys(patch), status: patch.status }); }
export async function refillQueue(statuses = ['requested', 'approved', 'processing', 'in_progress']) {
  const s = await getDocs(query(collection(db, 'prescriptionRefills'), where('status', 'in', statuses), limit(500)));
  return snapRows(s).sort((a, b) => (toDate(a.requestedDate)?.getTime() || 0) - (toDate(b.requestedDate)?.getTime() || 0));
}
export const refillsFor = uid => getDocs(query(collection(db, 'prescriptionRefills'), where('userId', '==', uid))).then(snapRows);
export async function updateRefill(id, status, extra = {}) { await updateDoc(doc(db, 'prescriptionRefills', id), { status, ...extra, updatedAt: Timestamp.now(), handledBy: session.user.uid, handledByName: session.staff?.name || session.user.email }); await audit('refill.' + status, `prescriptionRefills/${id}`, extra); }
export async function careRefillQueue() { const s = await getDocs(query(collection(db, 'refills'), where('status', '==', 'pending'), limit(300))); return snapRows(s); }
export async function updateCareRefill(id, status, extra = {}) { await updateDoc(doc(db, 'refills', id), { status, ...extra, updatedAt: serverTimestamp(), handledBy: session.user.uid }); await audit('carerefill.' + status, `refills/${id}`, extra); }

// ── Clinical: vitals, vaccinations, meds list, symptom checks ───────────
export const vitalsFor = uid => sub(uid, 'vital_signs', orderBy('timestamp', 'desc'), limit(200));
export async function addVital(uid, v) { await addDoc(collection(db, 'users', uid, 'vital_signs'), { ...v, timestamp: v.timestamp || Timestamp.now(), source: 'Clinic', recordedBy: session.staff?.name || session.user.email, createdAt: serverTimestamp() }); await audit('chart.vital', `users/${uid}/vital_signs`, { type: v.type }); }
export const vaccinationsFor = uid => sub(uid, 'vaccinations', orderBy('administeredAt', 'desc'));
export async function addVaccination(uid, v) { await addDoc(collection(db, 'users', uid, 'vaccinations'), { ...v, source: 'clinic', createdAt: serverTimestamp(), updatedAt: serverTimestamp(), recordedBy: session.user.uid }); await audit('chart.vaccination', `users/${uid}/vaccinations`, { vaccineName: v.vaccineName }); }
export const homeMedsFor = uid => getDocs(collection(db, 'users', uid, 'members', 'self', 'medications')).then(snapRows);
export const sideEffectsFor = uid => sub(uid, 'side_effects', orderBy('reportedAt', 'desc'));
export const symptomChecksFor = uid => sub(uid, 'symptom_checks', orderBy('createdAt', 'desc'), limit(50));
export const vaccinationsDue = async (days = 45) => {
  const until = Timestamp.fromDate(new Date(Date.now() + days * 86400000));
  const [h, p] = await Promise.all([
    getDocs(query(collectionGroup(db, 'vaccinations'), where('expiresAt', '<=', until), orderBy('expiresAt'), limit(300))),
    getDocs(query(collectionGroup(db, 'vaccinations'), where('expirationDate', '<=', until), orderBy('expirationDate'), limit(300))),
  ]);
  return [...snapRows(h).map(r => ({ ...r, kind: 'human', uid: r.path.split('/')[1], due: toDate(r.expiresAt) })), ...snapRows(p).map(r => ({ ...r, kind: 'pet', uid: r.path.split('/')[1], petId: r.path.split('/')[3], due: toDate(r.expirationDate) }))].sort((a, b) => a.due - b.due);
};

// ── Claims (human under users/{uid}/claims, pet under pets) ─────────────
export const humanClaimsFor = uid => sub(uid, 'claims');
export async function claimsQueue(max = 500) {
  const s = await getDocs(query(collectionGroup(db, 'claims'), limit(max)));
  return snapRows(s).map(c => { const p = c.path.split('/'); return { ...c, uid: p[1], isPet: p.includes('pets'), petId: p.includes('pets') ? p[3] : null, statusL: String(c.status || '').toLowerCase(), when: toDate(c.submittedAt || c.date || c.dateOfService) }; });
}
export async function decideClaim(c, status, extra = {}) {
  const ref = doc(db, c.path);
  await updateDoc(ref, { status, ...extra, updatedAt: serverTimestamp(), reviewedBy: session.user.uid, reviewedByName: session.staff?.name || session.user.email, reviewedAt: serverTimestamp() });
  await audit('claim.' + status, c.path, { amount: c.amount, isPet: !!c.isPet, ...extra });
}

// ── Pets ────────────────────────────────────────────────────────────────
export const petsFor = uid => sub(uid, 'pets');
export async function getPet(uid, petId) { const s = await getDoc(doc(db, 'users', uid, 'pets', petId)); return s.exists() ? { id: s.id, uid, ...s.data() } : null; }
export const petSub = (uid, petId, name, ...q) => getDocs(query(collection(db, 'users', uid, 'pets', petId, name), ...q)).then(snapRows);
export async function addPetWeight(uid, petId, w) { await addDoc(collection(db, 'users', uid, 'pets', petId, 'vet_weight_logs'), { petId, weightLbs: w.weightLbs, recordedAt: w.recordedAt || Timestamp.now(), recordedBy: session.user.uid, providerName: session.staff?.name || session.user.email, clinicName: w.clinicName || '', source: 'vet_visit', bodyConditionScore: w.bodyConditionScore ?? null, notes: w.notes || '', createdAt: serverTimestamp() }); await audit('pet.weight', `users/${uid}/pets/${petId}`, { weightLbs: w.weightLbs }); }
export async function addPetVaccination(uid, petId, v) { const ref = doc(collection(db, 'users', uid, 'pets', petId, 'vaccinations')); await setDoc(ref, { vaccinationId: ref.id, species: String(v.species || 'dog').toLowerCase(), ...v, createdAt: serverTimestamp(), updatedAt: serverTimestamp(), recordedBy: session.user.uid }); await audit('pet.vaccination', ref.path, { vaccineName: v.vaccineName }); }
export async function updatePet(uid, petId, patch) { await updateDoc(doc(db, 'users', uid, 'pets', petId), { ...patch, updatedAt: serverTimestamp() }); await audit('pet.update', `users/${uid}/pets/${petId}`, { keys: Object.keys(patch) }); }

// ── Support ─────────────────────────────────────────────────────────────
export async function tickets(status = 'open', max = 300) { const s = await getDocs(query(collection(db, 'helpTickets'), where('status', '==', status), limit(max))); return snapRows(s).sort((a, b) => (a.priority ?? 9) - (b.priority ?? 9) || (toDate(a.createdAt)?.getTime() || 0) - (toDate(b.createdAt)?.getTime() || 0)); }
export const ticketsFor = uid => getDocs(query(collection(db, 'helpTickets'), where('userId', '==', uid))).then(snapRows);
export function watchMessages(ticketId, cb) { return onSnapshot(query(collection(db, 'helpTickets', ticketId, 'messages'), orderBy('timestamp')), s => cb(snapRows(s))); }
export async function sendMessage(ticketId, text) { await addDoc(collection(db, 'helpTickets', ticketId, 'messages'), { senderId: session.user.uid, senderName: session.staff?.name || 'Jovi', text, timestamp: serverTimestamp(), readByUser: false, readByTeam: true }); }
export async function updateTicket(id, patch) { await updateDoc(doc(db, 'helpTickets', id), patch); await audit('ticket.update', `helpTickets/${id}`, patch); }
export async function markTicketRead(ticketId, msgs) { const b = writeBatch(db); let n = 0; for (const m of msgs) if (m.readByTeam === false) { b.update(m.ref, { readByTeam: true }); n++; } if (n) await b.commit(); }

// ── Billing / payments ──────────────────────────────────────────────────
export async function paymentLogs(max = 500) { const s = await getDocs(query(collection(db, 'payment_logs'), orderBy('timestamp', 'desc'), limit(max))); return snapRows(s); }
export const paymentLogsFor = uid => getDocs(query(collection(db, 'payment_logs'), where('userId', '==', uid))).then(snapRows);
export const transactionsFor = uid => sub(uid, 'transactions', orderBy('createdAt', 'desc'));
export const billingHistoryFor = uid => sub(uid, 'billing_history');
export async function kurvPassCancellations(max = 200) { const s = await getDocs(query(collection(db, 'kurv_pass_cancellations'), limit(max))); return snapRows(s); }

// ── Pharmacies / clinics / promos / broadcasts ──────────────────────────
export const pharmacies = () => getDocs(collection(db, 'pharmacies')).then(snapRows);
export async function savePharmacy(id, data) { const ref = id ? doc(db, 'pharmacies', id) : doc(collection(db, 'pharmacies')); await setDoc(ref, { ...data, updatedAt: serverTimestamp() }, { merge: true }); await audit('pharmacy.save', ref.path, { name: data.name }); return ref.id; }
export const promoCodes = () => getDocs(collection(db, 'promo_codes')).then(snapRows);
export async function savePromo(code, data) { await setDoc(doc(db, 'promo_codes', code.toUpperCase()), { ...data, code: code.toUpperCase(), updatedAt: serverTimestamp() }, { merge: true }); await audit('promo.save', `promo_codes/${code}`, data); }
export const broadcasts = () => getDocs(query(collection(db, 'broadcasts'), orderBy('createdAt', 'desc'), limit(50))).then(snapRows);
export async function sendBroadcast({ title, body, route, audience, uids }) {
  const ref = await addDoc(collection(db, 'broadcasts'), { title, body, route: route || null, audience, count: uids.length, createdAt: serverTimestamp(), by: session.user.email });
  // Inbox docs in chunks of 400 (batch limit 500).
  for (let i = 0; i < uids.length; i += 400) {
    const b = writeBatch(db);
    for (const uid of uids.slice(i, i + 400)) b.set(doc(collection(db, 'users', uid, 'notifications')), { type: 'system', title, body, route: route || null, params: {}, refPath: `broadcasts/${ref.id}`, read: false, createdAt: serverTimestamp() });
    await b.commit();
  }
  // FlutterFlow push trigger collection (the app's sendPushNotificationsTrigger listens here).
  await addDoc(collection(db, 'ff_push_notifications'), { notification_title: title, notification_text: body, notification_sound: 'default', initial_page_name: route || '', parameter_data: '{}', user_refs: uids.map(u => `users/${u}`).join(','), sender: doc(db, 'users', session.user.uid), timestamp: serverTimestamp(), status: 'pending' }).catch(e => console.warn('push trigger write failed', e));
  await audit('broadcast.send', ref.path, { audience, count: uids.length });
  return ref.id;
}

// ── Security logs ───────────────────────────────────────────────────────
export const securityLogsFor = uid => getDocs(query(collection(db, 'security_logs'), where('user_id', '==', uid), limit(100))).then(snapRows);

// ── Storage ─────────────────────────────────────────────────────────────
export async function uploadChartFile(uid, file, folder = 'documents') {
  const r = storageRef(storage, `users/${uid}/${folder}/${Date.now()}_${file.name.replace(/[^\w.\-]/g, '_')}`);
  await uploadBytes(r, file, { contentType: file.type }); return getDownloadURL(r);
}

// ── Aggregates for dashboards ───────────────────────────────────────────
export function monthKey(d) { const x = toDate(d); return x ? `${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, '0')}` : null; }
export function lastMonths(n) { const out = []; const d = new Date(); d.setDate(1); for (let i = n - 1; i >= 0; i--) { const x = new Date(d.getFullYear(), d.getMonth() - i, 1); out.push({ key: `${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, '0')}`, label: x.toLocaleDateString('en-US', { month: 'short' }) }); } return out; }

// ── Problem list, allergies, lab results, addenda, tasks, telehealth, reminders ──
export const problemsFor = uid => sub(uid, 'problems');
export async function addProblem(uid, p) { await addDoc(collection(db, 'users', uid, 'problems'), { ...p, status: 'active', createdAt: serverTimestamp(), createdBy: session.user.uid, createdByName: session.staff?.name || '' }); await audit('chart.problem.add', `users/${uid}/problems`, { label: p.label }); }
export async function updateProblem(uid, id, patch) { await updateDoc(doc(db, 'users', uid, 'problems', id), { ...patch, updatedAt: serverTimestamp() }); await audit('chart.problem.update', `users/${uid}/problems/${id}`, patch); }
export async function setAllergies(uid, list) { await updateDoc(doc(db, 'users', uid), { allergies: list, allergiesUpdatedAt: serverTimestamp(), allergiesUpdatedBy: session.user.uid }); await audit('chart.allergies', `users/${uid}`, { count: list.length }); }
export const labResultsFor = uid => sub(uid, 'lab_results', orderBy('resultedAt', 'desc'));
export async function addLabResult(uid, r) { await addDoc(collection(db, 'users', uid, 'lab_results'), { ...r, resultedAt: r.resultedAt || Timestamp.now(), enteredBy: session.user.uid, enteredByName: session.staff?.name || '', createdAt: serverTimestamp() }); await audit('chart.lab', `users/${uid}/lab_results`, { test: r.testName, flag: r.flag }); }
export async function addAddendum(uid, noteId, text) { const ref = doc(db, 'users', uid, 'visit_records', noteId); const snap = await getDoc(ref); const list = (snap.data()?.addenda) || []; list.push({ text, by: session.staff?.name || session.user.email, byId: session.user.uid, at: Timestamp.now() }); await updateDoc(ref, { addenda: list, updatedAt: serverTimestamp() }); await audit('chart.note.addendum', ref.path, {}); }
export async function tasks({ mine = false, status = 'open', patientUid = null } = {}) { const parts = [where('status', '==', status)]; if (mine) parts.push(where('assignedTo', '==', session.user.uid)); if (patientUid) parts.push(where('patientUid', '==', patientUid)); const s = await getDocs(query(collection(db, 'clinical_tasks'), ...parts, limit(500))); return snapRows(s).sort((a, b) => (toDate(a.due)?.getTime() || 9e15) - (toDate(b.due)?.getTime() || 9e15)); }
export async function addTask(t) { const ref = await addDoc(collection(db, 'clinical_tasks'), { status: 'open', priority: 'normal', ...t, createdAt: serverTimestamp(), createdBy: session.user.uid, createdByName: session.staff?.name || session.user.email }); await audit('task.create', ref.path, { title: t.title }); return ref.id; }
export async function updateTask(id, patch) { await updateDoc(doc(db, 'clinical_tasks', id), { ...patch, updatedAt: serverTimestamp() }); await audit('task.update', `clinical_tasks/${id}`, patch); }
export async function startTelehealth(r) { const url = r.telehealthUrl || `https://meet.jit.si/jovi-${r.id}`; await updateRequest(r.id, { telehealthUrl: url, isTelehealth: true, status: r.statusL === 'pending' ? 'confirmed' : r.status }, 'appointment.telehealth'); if (r.userId) await notifyMember(r.userId, { type: 'appointment', title: 'Your video visit is ready', body: 'Tap to join your Jovi provider now.', route: 'appointments', params: { requestId: r.id }, refPath: `requests/${r.id}` }); return url; }
export async function scheduleReminder(uid, { title, body, fireAt, route = 'appointments', params = {} }) { const ref = await addDoc(collection(db, 'users', uid, 'scheduled_reminders'), { title, body, fireAt: Timestamp.fromDate(fireAt), fired: false, type: 'appointment', route, params, source: 'clinic', createdAt: serverTimestamp(), createdBy: session.user.uid }); await audit('member.reminder', ref.path, { title, fireAt: fireAt.toISOString() }); }
export const remindersFor = uid => sub(uid, 'scheduled_reminders');
export function watchCounts(cb) {
  const out = { pending: 0, refills: 0, tickets: 0, claims: 0 }; const unsubs = [];
  const push = () => cb({ ...out });
  unsubs.push(onSnapshot(query(collection(db, 'requests'), where('status', '==', 'pending'), limit(500)), s => { out.pending = s.size; push(); }, () => {}));
  unsubs.push(onSnapshot(query(collection(db, 'prescriptionRefills'), where('status', '==', 'requested'), limit(500)), s => { out.refills = s.size; push(); }, () => {}));
  unsubs.push(onSnapshot(query(collection(db, 'helpTickets'), where('status', '==', 'open'), limit(500)), s => { out.tickets = s.size; push(); }, () => {}));
  return () => unsubs.forEach(u => u());
}

export * from './data2.js';
