// Data layer, part 2: templates, provider scheduling, intake & consent, orders (Rx/lab)
// with vendor hooks, results inbox, fax, care gaps, access log, settlement.
// Re-exported from data.js so pages keep importing from one place.
import {
  db, storage, functions, collection, collectionGroup, doc, getDoc, getDocs, setDoc, addDoc, updateDoc, deleteDoc,
  query, where, orderBy, limit, serverTimestamp, Timestamp, httpsCallable, storageRef, uploadBytes, getDownloadURL,
} from './firebase.js';
import { session, audit } from './auth.js';
import { toDate } from './ui.js';
import { sub, cachedMembers, recentVisitRecords, vaccinationsDue, claimsQueue, notifyMember, deductibleOf, subStatus } from './data.js';

const snapRows = s => s.docs.map(d => ({ id: d.id, ref: d.ref, path: d.ref.path, ...d.data() }));
const slug = s => String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || Math.random().toString(36).slice(2, 10);
const money = n => '$' + Number(n || 0).toLocaleString('en-US', { maximumFractionDigits: 0 });

// ── Note templates & smart phrases ──────────────────────────────────────
export const DEFAULT_TEMPLATES = [
  { id: 'primary', name: 'Primary care visit', visitType: 'Primary Care', hpi: 'Patient presents for {reason}. Onset: . Duration: . Character: . Aggravating/relieving: . Associated symptoms: . Pertinent negatives: .', exam: 'General: well-appearing, NAD.\nHEENT: normocephalic, PERRL, oropharynx clear.\nNeck: supple, no lymphadenopathy.\nCV: RRR, no m/r/g.\nLungs: CTAB.\nAbd: soft, NT/ND.\nExt: no edema.\nSkin: warm, dry.\nNeuro: grossly intact.', plan: 'Assessment and plan discussed. Return precautions reviewed.', edu: 'Patient verbalized understanding.' },
  { id: 'urgent', name: 'Urgent care / sick visit', visitType: 'Urgent Care', hpi: 'Acute {reason} x  days. Fever: . Cough: . Sore throat: . GI sx: . Sick contacts: . Tried: .', exam: 'General: nontoxic.\nHEENT: TMs clear, no exudate, no sinus tenderness.\nNeck: supple.\nLungs: CTAB, no wheeze.\nCV: RRR.\nSkin: no rash.', plan: 'Supportive care. Follow up if not improving in 48 to 72 h or sooner if worsening.', edu: 'Red flags reviewed: difficulty breathing, chest pain, confusion, persistent fever over 3 days.' },
  { id: 'wellness', name: 'Annual wellness / physical', visitType: 'Wellness', hpi: 'Annual physical. No acute complaints. Diet: . Exercise: . Sleep: . Mood: . Tobacco/alcohol: . Screening due: .', exam: 'Complete physical exam performed and documented.', plan: 'Age-appropriate screening ordered. Immunizations reviewed. Lifestyle counseling provided.', edu: 'Preventive care schedule reviewed.' },
  { id: 'telehealth', name: 'Telehealth', visitType: 'Telehealth', hpi: 'Video visit. Patient location: home. Identity verified. Consent to telehealth obtained. {reason}.', exam: 'Limited exam via video: appears , speech clear, no respiratory distress.', plan: 'In-person follow-up if symptoms change.', edu: 'Instructed when to seek in-person or emergency care.' },
  { id: 'followup', name: 'Follow-up', visitType: 'Follow-up', hpi: 'Follow-up for . Interval history: . Adherence: . Side effects: .', exam: 'Focused exam: ', plan: 'Continue current plan. ', edu: '' },
];
export const DEFAULT_PHRASES = [
  { key: '.ros', text: 'ROS: negative except as noted in HPI.' },
  { key: '.rtc', text: 'Return to clinic in 2 weeks or sooner as needed.' },
  { key: '.er', text: 'Go to the nearest emergency department or call 911 for chest pain, shortness of breath, confusion, fainting, or severe worsening.' },
  { key: '.consent', text: 'Risks, benefits, and alternatives discussed. Patient verbalized understanding and consented.' },
  { key: '.nka', text: 'No known drug allergies.' },
  { key: '.smoke', text: 'Tobacco cessation counseled for more than 3 minutes; patient is in the contemplation stage. Resources provided.' },
  { key: '.bp', text: 'Home BP monitoring instructed: twice daily, seated, after 5 minutes rest; log in the Jovi app.' },
];
export async function noteTemplates() { const custom = await getDocs(collection(db, 'note_templates')).then(snapRows).catch(() => []); const ids = new Set(custom.map(c => c.id)); return [...custom, ...DEFAULT_TEMPLATES.filter(d => !ids.has(d.id)).map(d => ({ ...d, builtin: true }))]; }
export async function saveTemplate(id, data) { const k = id || slug(data.name); await setDoc(doc(db, 'note_templates', k), { ...data, updatedAt: serverTimestamp(), updatedBy: session.user.uid }, { merge: true }); await audit('template.save', `note_templates/${k}`, {}); }
export async function smartPhrases() { const custom = await getDocs(collection(db, 'smart_phrases')).then(snapRows).catch(() => []); const keys = new Set(custom.map(c => c.key)); return [...custom, ...DEFAULT_PHRASES.filter(d => !keys.has(d.key)).map(d => ({ ...d, builtin: true }))]; }
export async function savePhrase(key, text) { const k = key.startsWith('.') ? key : '.' + key; await setDoc(doc(db, 'smart_phrases', k.slice(1)), { key: k, text, updatedAt: serverTimestamp(), updatedBy: session.user.uid }); await audit('phrase.save', `smart_phrases/${k}`, {}); }
/** Expands ".key" tokens at the end of typed text in a textarea (call on input). */
export function attachPhrases(textarea, phrases) {
  textarea.addEventListener('input', () => {
    const v = textarea.value; const m = v.match(/(^|\s)(\.[a-z0-9_]+)$/i); if (!m) return;
    const p = phrases.find(x => x.key.toLowerCase() === m[2].toLowerCase()); if (!p) return;
    textarea.value = v.slice(0, v.length - m[2].length) + p.text + ' ';
  });
}

// ── Providers, hours, blocks, waitlist ──────────────────────────────────
export const DEFAULT_HOURS = { 1: ['9:00 AM', '4:30 PM'], 2: ['9:00 AM', '4:30 PM'], 3: ['9:00 AM', '4:30 PM'], 4: ['9:00 AM', '4:30 PM'], 5: ['9:00 AM', '4:30 PM'] };
export async function providers() { const s = await getDocs(collection(db, 'staff')); return snapRows(s).filter(x => x.active !== false && ['clinician', 'superadmin'].includes(x.role)); }
export async function saveProviderSettings(uid, settings) { await updateDoc(doc(db, 'staff', uid), { schedule: settings, updatedAt: serverTimestamp() }); await audit('provider.settings', `staff/${uid}`, {}); }
export async function scheduleBlocks(fromDay, toDay) { const s = await getDocs(query(collection(db, 'schedule_blocks'), where('day', '>=', fromDay), where('day', '<=', toDay), limit(500))); return snapRows(s); }
export async function addBlock(b) { const ref = await addDoc(collection(db, 'schedule_blocks'), { ...b, createdAt: serverTimestamp(), createdBy: session.user.uid }); await audit('schedule.block', ref.path, b); }
export async function removeBlock(id) { await deleteDoc(doc(db, 'schedule_blocks', id)); await audit('schedule.unblock', `schedule_blocks/${id}`, {}); }
export async function waitlist(status = 'waiting') { const s = await getDocs(query(collection(db, 'waitlist'), where('status', '==', status), limit(300))); return snapRows(s).sort((a, b) => (toDate(a.createdAt)?.getTime() || 0) - (toDate(b.createdAt)?.getTime() || 0)); }
export async function addWaitlist(w) { const ref = await addDoc(collection(db, 'waitlist'), { status: 'waiting', ...w, createdAt: serverTimestamp(), createdBy: session.user.uid }); await audit('waitlist.add', ref.path, {}); }
export async function updateWaitlist(id, patch) { await updateDoc(doc(db, 'waitlist', id), { ...patch, updatedAt: serverTimestamp() }); }
export async function offerSlotToWaitlist(w, day, slot, clinic) { await notifyMember(w.userId, { type: 'appointment', title: 'A sooner appointment opened up', body: `${slot} on ${day} at ${clinic || 'Jovi'}. Open the app to book it.`, route: 'requests' }); await updateWaitlist(w.id, { status: 'offered', offeredSlot: `${day} ${slot}`, offeredAt: serverTimestamp() }); }

// ── Intake & consent (clinic-side, tablet) ──────────────────────────────
export const CONSENT_TEXTS = {
  treatment: { title: 'Consent to treatment', text: 'I consent to examination and treatment by Jovi clinicians. I understand I may ask questions and refuse any part of care. I understand Jovi is a healthcare membership and not health insurance.' },
  telehealth: { title: 'Telehealth consent', text: 'I consent to receive care by video or phone. I understand the limits of a remote exam and that I may be asked to come in person.' },
  privacy: { title: 'Notice of privacy practices', text: 'I acknowledge receipt of the Jovi Notice of Privacy Practices describing how my health information may be used and shared.' },
  procedure: { title: 'Procedure consent', text: 'The procedure, its risks, benefits, and alternatives were explained to me and my questions were answered. I consent to the procedure.' },
  financial: { title: 'Financial responsibility', text: 'I understand clinic visits are $0 co-pay for members and that any service outside my membership will be quoted to me before it is performed.' },
};
export const INTAKE_QUESTIONS = [
  ['reason', 'What brings you in today?', 'text'], ['duration', 'How long has this been going on?', 'text'], ['severity', 'How severe is it right now, 0 to 10?', 'scale'],
  ['medsChanged', 'Any changes to your medications since your last visit?', 'yesno'], ['allergiesChanged', 'Any new allergies?', 'yesno'], ['recentCare', 'Have you seen another provider, ER, or urgent care since your last visit?', 'yesno'],
  ['fever', 'Fever in the last 48 hours?', 'yesno'], ['pregnant', 'Any chance of pregnancy?', 'yesno'], ['moodLow', 'Over the last 2 weeks, have you felt down, depressed, or hopeless?', 'yesno'], ['anhedonia', 'Little interest or pleasure in doing things?', 'yesno'],
  ['safety', 'Do you feel safe at home?', 'yesno'], ['questions', 'Anything else you want the provider to know?', 'text'],
];
export const consentsFor = uid => sub(uid, 'consents', orderBy('signedAt', 'desc'));
export async function saveConsent(uid, { type, title, text, signatureDataUrl, signerName, relationship, requestId }) {
  const blob = await (await fetch(signatureDataUrl)).blob();
  const r = storageRef(storage, `users/${uid}/consents/${Date.now()}_${type}.png`); await uploadBytes(r, blob, { contentType: 'image/png' }); const url = await getDownloadURL(r);
  const ref = await addDoc(collection(db, 'users', uid, 'consents'), { type, title, text, signatureUrl: url, signerName, relationship: relationship || 'self', requestId: requestId || null, signedAt: serverTimestamp(), witnessedBy: session.user.uid, witnessedByName: session.staff?.name || '', ua: navigator.userAgent.slice(0, 100) });
  await audit('consent.sign', ref.path, { type }); return ref.id;
}
export const intakeFor = uid => sub(uid, 'intake', orderBy('createdAt', 'desc'), limit(10));
export async function saveIntake(uid, answers, requestId) { const ref = await addDoc(collection(db, 'users', uid, 'intake'), { answers, requestId: requestId || null, createdAt: serverTimestamp(), recordedBy: session.user.uid }); await audit('intake.save', ref.path, {}); return ref.id; }
export async function requestIntake(uid, requestId) { await notifyMember(uid, { type: 'appointment', title: 'Complete your pre-visit check-in', body: 'Answer a few questions before your visit so we can spend the time on you.', route: 'appointments', params: { requestId: requestId || '' } }); }

// ── Orders: e-prescribing and labs (vendor-ready) ───────────────────────
// Status flow: signed → queued → transmitted → acknowledged | error; labs continue → collected → resulted.
export const LAB_VENDORS = [['labcorp', 'Labcorp'], ['quest', 'Quest Diagnostics']];
export const LAB_PANELS = ['CBC with differential', 'Comprehensive metabolic panel', 'Basic metabolic panel', 'Lipid panel', 'Hemoglobin A1c', 'TSH', 'Free T4', 'Urinalysis', 'Vitamin D 25-OH', 'Vitamin B12', 'Ferritin', 'Iron panel', 'PSA', 'HIV 1/2 Ag/Ab', 'Hepatitis panel', 'STI panel (GC/CT NAAT)', 'Rapid strep', 'COVID-19 / Influenza PCR', 'hCG (urine)', 'Urine culture', 'Magnesium', 'Uric acid', 'CRP', 'ESR'];
export async function ordersFor(uid) { const s = await getDocs(query(collection(db, 'orders'), where('userId', '==', uid), limit(300))); return snapRows(s).sort((a, b) => (toDate(b.createdAt)?.getTime() || 0) - (toDate(a.createdAt)?.getTime() || 0)); }
export async function ordersQueue(statuses = ['signed', 'queued', 'transmitted', 'error']) { const s = await getDocs(query(collection(db, 'orders'), where('status', 'in', statuses), limit(500))); return snapRows(s).sort((a, b) => (toDate(a.createdAt)?.getTime() || 0) - (toDate(b.createdAt)?.getTime() || 0)); }
export async function createOrder(o) {
  const ref = await addDoc(collection(db, 'orders'), { status: 'signed', vendor: o.kind === 'rx' ? 'surescripts' : (o.vendor || 'labcorp'), ...o, orderedBy: session.user.uid, orderedByName: session.staff?.name || '', orderedByNpi: session.staff?.npi || '', createdAt: serverTimestamp(), updatedAt: serverTimestamp(), transmitLog: [] });
  await audit('order.sign', ref.path, { kind: o.kind }); return ref.id;
}
export async function transmitOrder(id) {
  try { const fn = httpsCallable(functions, 'transmitOrder'); const res = await fn({ orderId: id }); await audit('order.transmit', `orders/${id}`, res.data || {}); return res.data; }
  catch (e) { await updateDoc(doc(db, 'orders', id), { status: 'queued', updatedAt: serverTimestamp(), lastError: e.message || String(e) }); await audit('order.queue', `orders/${id}`, { error: e.message }); return { queued: true, error: e.message }; }
}
export async function updateOrder(id, patch) { await updateDoc(doc(db, 'orders', id), { ...patch, updatedAt: serverTimestamp() }); await audit('order.update', `orders/${id}`, patch); }

// ── Results inbox ───────────────────────────────────────────────────────
export async function resultsInbox() { const s = await getDocs(query(collectionGroup(db, 'lab_results'), where('reviewed', '==', false), limit(300))); return snapRows(s).map(r => ({ ...r, uid: r.path.split('/')[1] })).sort((a, b) => (toDate(a.resultedAt)?.getTime() || 0) - (toDate(b.resultedAt)?.getTime() || 0)); }
export async function reviewResult(r, { note, notify }) {
  await updateDoc(r.ref, { reviewed: true, reviewedAt: serverTimestamp(), reviewedBy: session.user.uid, reviewedByName: session.staff?.name || '', reviewNote: note || '' });
  if (notify) await notifyMember(r.uid, { type: 'system', title: `Result reviewed: ${r.testName}`, body: note || 'Your provider reviewed this result. Open Care Records for details.', route: 'careRecords' });
  await audit('result.review', r.path, { flag: r.flag, notified: !!notify });
}

// ── Fax (vendor via functions/fax.js) ───────────────────────────────────
export async function faxOutbox(max = 200) { const s = await getDocs(query(collection(db, 'fax_outbox'), orderBy('createdAt', 'desc'), limit(max))); return snapRows(s); }
export async function faxInbox(max = 200) { const s = await getDocs(query(collection(db, 'fax_inbox'), orderBy('receivedAt', 'desc'), limit(max))); return snapRows(s); }
export async function sendFax({ to, toName, subject, fileUrl, fileName, patientUid, patientName }) {
  const ref = await addDoc(collection(db, 'fax_outbox'), { to, toName, subject, fileUrl, fileName, patientUid: patientUid || null, patientName: patientName || null, status: 'queued', createdAt: serverTimestamp(), createdBy: session.user.uid, createdByName: session.staff?.name || '' });
  await audit('fax.send', ref.path, { to });
  try { const fn = httpsCallable(functions, 'sendFax'); await fn({ faxId: ref.id }); } catch (e) { await updateDoc(ref, { lastError: e.message || String(e) }); }
  return ref.id;
}
export async function attachFaxToChart(fax, uid, category = 'other') {
  await addDoc(collection(db, 'users', uid, 'visit_records'), { visitDate: fax.receivedAt || Timestamp.now(), type: 'Inbound fax', patientName: '', providerName: session.staff?.name || '', chiefComplaint: fax.subject || `Fax from ${fax.from || 'unknown'}`, attachments: [{ name: fax.fileName || 'fax.pdf', url: fax.fileUrl, contentType: 'application/pdf', uploadedAt: Timestamp.now(), category }], signedAt: Timestamp.now(), signedBy: session.user.uid, signedByName: session.staff?.name || '', createdAt: serverTimestamp(), source: 'fax' });
  await updateDoc(doc(db, 'fax_inbox', fax.id), { attachedTo: uid, attachedAt: serverTimestamp(), attachedBy: session.user.uid, status: 'filed' }); await audit('fax.file', `fax_inbox/${fax.id}`, { uid });
}

// ── Care gaps / population health ───────────────────────────────────────
export async function careGaps() {
  const members = await cachedMembers(); const now = Date.now(); const day = 86400000;
  const [notes, rx, vax, claims] = await Promise.all([recentVisitRecords(2000).catch(() => []), getDocs(query(collection(db, 'prescriptions'), where('status', '==', 'active'), limit(2000))).then(snapRows).catch(() => []), vaccinationsDue(30).catch(() => []), claimsQueue(1000).catch(() => [])]);
  const lastWellness = {}, lastAny = {};
  for (const n of notes) { const t = toDate(n.visitDate)?.getTime() || 0; if (!lastAny[n.uid] || t > lastAny[n.uid]) lastAny[n.uid] = t; if (/wellness|physical/i.test(n.type || '') && n.signedAt && (!lastWellness[n.uid] || t > lastWellness[n.uid])) lastWellness[n.uid] = t; }
  const gaps = []; const active = members.filter(m => ['active', 'past_due', 'canceling'].includes(m.status));
  for (const m of active) {
    const lw = lastWellness[m.id]; if (!lw || now - lw > 365 * day) gaps.push({ rule: 'annual_wellness', severity: 'routine', uid: m.id, name: m.name, detail: lw ? `Last physical ${Math.round((now - lw) / day)} days ago` : 'No physical on record', action: 'Invite to book an annual wellness visit', route: 'requests' });
    const la = lastAny[m.id]; if (la && now - la > 365 * day) gaps.push({ rule: 'no_visit_12mo', severity: 'low', uid: m.id, name: m.name, detail: `Last visit ${Math.round((now - la) / day)} days ago`, action: 'Outreach: check in', route: 'requests' });
    if ((m.hasTobacco || m.tobacco) && !/former|never/i.test(m.smokingStatus || '')) gaps.push({ rule: 'tobacco_counseling', severity: 'routine', uid: m.id, name: m.name, detail: 'Tobacco use on file', action: 'Offer cessation counseling', route: 'ChatLanding' });
  }
  for (const r of rx) { const nd = toDate(r.nextRefillDate); if (nd && nd.getTime() < now - 7 * day) { const m = members.find(x => x.id === r.userId); gaps.push({ rule: 'refill_overdue', severity: 'medium', uid: r.userId, name: m?.name || r.userId, detail: `${r.medicationName} refill due ${Math.round((now - nd.getTime()) / day)} days ago`, action: 'Check adherence, offer refill', route: 'scriptRefill' }); } }
  for (const v of vax) { const m = members.find(x => x.id === v.uid); gaps.push({ rule: v.kind === 'pet' ? 'pet_booster' : 'booster_due', severity: v.due < new Date() ? 'medium' : 'routine', uid: v.uid, name: m?.name || v.uid, detail: `${v.vaccineName} ${v.due < new Date() ? 'overdue' : 'due ' + v.due.toLocaleDateString()}${v.kind === 'pet' ? ' (pet)' : ''}`, action: 'Schedule booster', route: v.kind === 'pet' ? 'petVaccinations' : 'vaccinations' }); }
  for (const c of claims.filter(c => c.statusL === 'needs_more_info' && c.when && now - c.when.getTime() > 7 * day)) { const m = members.find(x => x.id === c.uid); gaps.push({ rule: 'claim_stalled', severity: 'low', uid: c.uid, name: m?.name || c.uid, detail: `Claim for ${money(c.amount)} waiting on member info`, action: 'Remind member what is missing', route: c.isPet ? 'petFileClaim' : 'FileClaim' }); }
  return gaps;
}

// ── Access log (HIPAA access report) ────────────────────────────────────
export async function logChartView(uid, what = 'chart') { await audit('chart.view', `users/${uid}`, { what }); }
export async function accessReportFor(uid) { const s = await getDocs(query(collection(db, 'audit_logs'), where('target', '==', `users/${uid}`), limit(500))); return snapRows(s).sort((a, b) => (toDate(b.at)?.getTime() || 0) - (toDate(a.at)?.getTime() || 0)); }

// ── Coverage snapshot & settlement ──────────────────────────────────────
export function coverageSnapshot(u) { const ded = deductibleOf(u); const met = Number(u.updateDed) || 0; return { plan: u.planType || u.planTier || 'Individual', deductible: ded, met, remaining: Math.max(0, ded - met), dental: !!(u.hasDental || u.dental), vision: !!(u.hasVision || u.vision), status: subStatus(u) }; }
export async function settleVisit(uid, { visitRecordId, totalCharged, memberShare, description }) {
  await addDoc(collection(db, 'users', uid, 'transactions'), { type: 'clinic_visit', status: memberShare > 0 ? 'pending' : 'succeeded', amount: memberShare, currency: 'USD', description: description || 'Clinic visit', visitRecordId, totalCharged, joviCovered: Math.max(0, totalCharged - memberShare), createdAt: serverTimestamp(), updatedAt: serverTimestamp(), recordedBy: session.user.uid });
  await audit('visit.settle', `users/${uid}/transactions`, { totalCharged, memberShare });
}

// ── Ambient scribe (functions/scribe.js, Claude) ────────────────────────
export async function draftFromTranscript({ transcript, patientName, visitType, reason }) {
  const fn = httpsCallable(functions, 'scribe', { timeout: 120000 }); const res = await fn({ transcript, patientName, visitType, reason });
  await audit('scribe.run', 'scribe', { chars: transcript.length, model: res.data?.model || null }); return res.data;
}

// ── Invoices / receipts (written by functions/billing.js) ───────────────
export async function invoicesAll(max = 1000) { const s = await getDocs(query(collectionGroup(db, 'invoices'), orderBy('issuedAt', 'desc'), limit(max))); return snapRows(s).map(r => ({ ...r, uid: r.path.split('/')[1] })); }
export const invoicesFor = uid => sub(uid, 'invoices', orderBy('issuedAt', 'desc'));
