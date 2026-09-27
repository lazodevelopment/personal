import { h, pageHeader, card, cardHead, kv, badge, money, fmtDate, fmtDateTime, ago, btn, avatar, tabs, table, prompt, confirm, toast, errorToast, textarea, field, input, select, phone, age } from '../../ui.js';
import { getMember, memberName, memberPhoto, memberDob, parseDob, monthlyTotal, deductibleOf, subStatus, nextBilling, dependentsOf, spouseOf, petsFor, requestsForUser, paymentLogsFor, transactionsFor, billingHistoryFor, memberNotes, addMemberNote, notifyMember, cancelMembershipViaBackend, reactivateMembership, updateMember, ticketsFor, securityLogsFor, parseJsonArr, humanClaimsFor, refillsFor } from '../../data.js';
import { can, canSide, session } from '../../auth.js';
import { navigate } from '../../router.js';

export async function render({ param: uid }) {
  const u = await getMember(uid);
  if (!u) return h('div', { class: 'empty' }, h('b', null, 'Member not found'));
  const wrap = h('div'); const body = h('div'); let tab = 'overview';
  const name = memberName(u), status = subStatus(u), dob = parseDob(memberDob(u));
  const actions = [];
  if (canSide('ehr') && can('viewPhi')) actions.push(btn('Open chart', () => navigate(`/ehr/chart/${uid}`), { variant: 'btn-primary' }));
  if (can('writeBusiness')) {
    actions.push(btn('Send notification', () => sendNote(uid), { variant: 'btn-secondary' }));
    if (['active', 'past_due'].includes(status)) actions.push(btn('Cancel membership', async () => { const r = await prompt('Cancel membership', 'Reason (shown in the audit log)', { okLabel: 'Schedule cancellation' }); if (r == null) return; try { await cancelMembershipViaBackend(r, uid); toast('Cancellation scheduled for the end of the billing period', 'success'); location.reload(); } catch (e) { errorToast(e); } }, { variant: 'btn-danger' }));
    if (['canceling', 'canceled', 'suspended', 'inactive'].includes(status)) actions.push(btn('Reactivate', async () => { if (!(await confirm('Reactivate membership?', 'Sets the subscription back to active. Billing resumes on the next anniversary.'))) return; try { await reactivateMembership(uid); toast('Reactivated', 'success'); location.reload(); } catch (e) { errorToast(e); } }, { variant: 'btn-success' }));
  }
  wrap.append(h('div', { class: 'chart-banner' }, avatar(name, memberPhoto(u), 52), h('div', null, h('h1', null, name), h('div', { class: 'meta' },
    h('span', null, u.email || '—'), h('span', null, phone(u.phone || u.onboard_phone || u.phone_number)), dob ? h('span', null, `Age ${age(dob)}`) : null, h('span', null, `${u.city || ''}${u.city && u.state ? ', ' : ''}${u.state || u.onboard_address || ''}`),
    h('span', null, 'Member since ', h('b', null, fmtDate(u.membershipStartDate || u.created_time))), h('span', { class: 'mono' }, uid))),
    h('div', { class: 'alerts' }, badge(status), u.pendingBillingReview ? h('span', { class: 'alert' }, 'Pending billing review') : null, u.lastChargeStatus && u.lastChargeStatus !== 'ok' ? h('span', { class: 'alert' }, `Charge ${u.lastChargeStatus}`) : null, u.hasKurvPass || u.lastKurvPassPurchase ? h('span', { class: 'alert', style: { background: 'rgba(0,184,148,.25)', borderColor: 'rgba(0,184,148,.6)' } }, 'Jovi Pass user') : null)),
    h('div', { class: 'page-actions mb' }, actions), body);

  const TABS = [['overview', 'Overview'], ['household', 'Household & pets'], ['billing', 'Billing'], ['appointments', 'Appointments'], ['claims', 'Claims (financial)'], ['support', 'Support'], ['notes', 'Staff notes'], ['security', 'Security']];
  const draw = async () => {
    body.replaceChildren(tabs(TABS, tab, t => { tab = t; draw(); }), h('div', { class: 'spinner-wrap' }, h('span', { class: 'spinner' })));
    let content;
    try { content = await ({ overview, household, billing, appointments, claims, support, notes, security })[tab](u, uid); } catch (e) { errorToast(e); content = h('div', { class: 'empty' }, h('b', null, 'Could not load'), h('span', null, e.message)); }
    body.replaceChildren(tabs(TABS, tab, t => { tab = t; draw(); }), content);
  };
  await draw();
  return wrap;
}

function overview(u, uid) {
  const members = parseJsonArr(u.members);
  return h('div', { class: 'grid grid-3' },
    card(cardHead('Plan'), kv('Plan type', u.planType || u.planTier || 'Individual'), kv('Subscription', badge(subStatus(u))), kv('Monthly total', money(monthlyTotal(u))), kv('Health premium', money(u.totalHealthPremium ?? u.totalPremium ?? 0)), kv('Pet premium', money(u.petTotalPremium || 0)), kv('Dental', u.hasDental || u.dental ? 'Yes' : 'No'), kv('Vision', u.hasVision || u.vision ? 'Yes' : 'No'), kv('Tobacco surcharge', u.hasTobacco || u.tobacco ? 'Yes' : 'No'), kv('Deductible', money(deductibleOf(u), { cents: false })), kv('Deductible met', money(u.updateDed || 0)), kv('Promo', u.promoCodeApplied || '—'), kv('Referral', u.referral || '—')),
    card(cardHead('Billing'), kv('Next bill', fmtDate(nextBilling(u))), kv('Renewal (annual)', fmtDate(u.renew)), kv('Last payment', fmtDate(u.lastPaymentDate)), kv('Last charge status', u.lastChargeStatus || '—'), kv('Card', u.cardLast4 ? `${(u.cardBrand || 'card').toUpperCase()} •••• ${u.cardLast4}` : u.paymentCard ? `•••• ${String(u.paymentCard).slice(-4)}` : '—'), kv('Processor id', h('span', { class: 'mono' }, u.payarcCustomerId || '—')), kv('Will cancel on', fmtDate(u.willCancelOn)), kv('Cancel reason', u.cancelReason || '—')),
    card(cardHead('Profile'), kv('Gender', u.gender || u.onboard_gender || '—'), kv('Date of birth', memberDob(u) || '—'), kv('Address', [u.address || u.onboard_address, u.city, u.state, u.zip].filter(Boolean).join(', ') || '—'), kv('Emergency contact', u.onboard_emName ? `${u.onboard_emName} · ${phone(u.onboard_emPhone)}` : '—'), kv('Timezone', u.timezone || '—'), kv('Preferred pharmacy', u.preferredPharmacyName || u.preferredPharmacyPlace?.name || u.onboard_pharmacy || '—'), kv('Pays with GoodRx', u.payWithGoodRx ? 'Yes' : 'No'), kv('2FA', u.two_fa_enabled ? 'On' : 'Off'), kv('Last login', fmtDateTime(u.last_login))),
    members.length ? card(cardHead('Quote at signup'), table([{ label: 'Member', key: 'name' }, { label: 'Age', key: 'age' }, { label: 'Base', render: m => money(m.basePremium) }, { label: 'Contribution', render: m => money(m.contribution) }, { label: 'Deductible', render: m => money(m.deductible, { cents: false }) }], members)) : null,
  );
}
async function household(u, uid) {
  const pets = await petsFor(uid); const sp = spouseOf(u); const deps = dependentsOf(u);
  const person = (p, rel) => h('div', { class: 'list-item' }, avatar(`${p.firstName} ${p.lastName}`, p.photo, 34), h('div', { class: 'grow' }, h('b', null, `${p.firstName || ''} ${p.lastName || ''}`), h('span', null, `${rel}${p.dob ? ' · born ' + p.dob : ''}${p.gender ? ' · ' + p.gender : ''}`)));
  return h('div', { class: 'grid grid-2' },
    card(cardHead('People on the plan'), h('div', { class: 'list' }, person({ firstName: memberName(u), lastName: '', photo: memberPhoto(u), dob: memberDob(u) }, 'Primary'), sp ? person(sp, 'Spouse') : null, deps.map(d => person(d, d.relationship || 'Dependent'))), u.pendingBillingReview ? h('div', { class: 'phi-banner mt' }, 'Household changed in the app. Review premium and clear the flag once billing is updated.', can('writeBusiness') ? btn('Clear flag', async () => { await updateMember(uid, { pendingBillingReview: false }, 'member.billing_review_cleared'); toast('Cleared', 'success'); location.reload(); }, { size: 'btn-sm' }) : null) : null),
    card(cardHead('Pets'), pets.length ? h('div', { class: 'list' }, pets.map(p => h('div', { class: 'list-item' }, avatar(p.name, p.photoUrl, 34), h('div', { class: 'grow' }, h('b', null, p.name), h('span', null, `${p.type || ''} · ${p.breed || ''}${p.archived ? ' · archived' : ''}`)), can('viewPhi') && canSide('ehr') ? btn('Chart', () => navigate(`/ehr/pet/${uid}/${p.id}`), { size: 'btn-sm' }) : null))) : h('p', { class: 'muted' }, 'No pets on the plan.')),
  );
}
async function billing(u, uid) {
  const [logs, tx, hist] = await Promise.all([paymentLogsFor(uid).catch(() => []), transactionsFor(uid).catch(() => []), billingHistoryFor(uid).catch(() => [])]);
  return h('div', { class: 'col' },
    card(cardHead('Payment attempts (processor webhook)'), table([{ label: 'When', render: p => fmtDateTime(p.timestamp) }, { label: 'Type', key: 'type' }, { label: 'Amount', render: p => money(p.amount) }, { label: 'Status', render: p => badge(p.status) }, { label: 'Attempt', key: 'attemptNumber' }, { label: 'Reason', key: 'reason' }], logs.sort((a, b) => (b.timestamp?.toMillis?.() || 0) - (a.timestamp?.toMillis?.() || 0)), { empty: 'No payment events recorded' })),
    card(cardHead('Transactions'), table([{ label: 'When', render: t => fmtDateTime(t.createdAt) }, { label: 'Type', key: 'type' }, { label: 'Description', key: 'description' }, { label: 'Amount', render: t => money(t.amount) }, { label: 'Status', render: t => badge(t.status) }], tx, { empty: 'No transactions' })),
    hist.length ? card(cardHead('Pet add-on charges'), table([{ label: 'When', render: t => fmtDateTime(t.createdAt) }, { label: 'Pet', key: 'petName' }, { label: 'Monthly', render: t => money(t.monthlyPremium) }, { label: 'Charged', render: t => money(t.chargedAmount) }, { label: 'Proration', render: t => `${t.prorationDays}/${t.cycleDays} days` }], hist)) : null,
  );
}
async function appointments(u, uid) {
  const rows = await requestsForUser(uid);
  return card(cardHead('Appointment history (no clinical reasons on this side)'), table([{ label: 'When', render: r => r.start ? fmtDateTime(r.start) : `${r.appointmentDate || ''} ${r.appointmentTime || ''}` }, { label: 'Patient', key: 'patientName' }, { label: 'Type', render: r => `${r.isPet ? 'Pet · ' : ''}${r.visitType || ''}` }, { label: 'Mode', key: 'visitMode' }, { label: 'Clinic', key: 'clinic' }, { label: 'Status', render: r => badge(r.statusL) }, { label: 'Jovi Pass', render: r => r.priority ? badge('active', '$49') : '—' }], rows, { empty: 'No appointments' }));
}
async function claims(u, uid) {
  const rows = await humanClaimsFor(uid);
  return card(cardHead('Human claims (amounts and status only)'), table([{ label: 'Submitted', render: c => fmtDate(c.submittedAt || c.date) }, { label: 'Type', render: c => c.type === 'receipt' ? 'Reimburse member' : 'Pay provider' }, { label: 'Amount', render: c => money(c.amount) }, { label: 'Status', render: c => badge(String(c.status).toLowerCase()) }, { label: 'Paid', render: c => c.paidAmount != null ? money(c.paidAmount) : c.paymentProcessed ? 'Yes' : '—' }], rows, { empty: 'No claims' }));
}
async function support(u, uid) {
  const rows = await ticketsFor(uid);
  return card(cardHead('Support tickets'), table([{ label: 'Opened', render: t => fmtDateTime(t.createdAt) }, { label: 'Issue', key: 'issueType' }, { label: 'Priority', render: t => badge(t.priority === 0 ? 'failed' : t.priority === 1 ? 'pending' : 'info', t.priorityLevel || '—') }, { label: 'Status', render: t => badge(t.status) }, { label: '', render: t => btn('Open', () => navigate(`/admin/support/${t.id}`), { size: 'btn-sm' }) }], rows, { empty: 'No tickets' }));
}
async function notes(u, uid) {
  const rows = await memberNotes(uid);
  const ta = textarea({ placeholder: 'Internal note (not visible to the member). No clinical detail here.' });
  const kind = select(['general', 'billing', 'account', 'complaint', 'retention'], 'general');
  const list = h('div', { class: 'timeline' }, rows.map(n => h('div', { class: `tl-item ${n.kind === 'billing' ? 'blue' : n.kind === 'complaint' ? '' : 'gray'}` }, h('div', { class: 'tl-when' }, `${n.by} · ${ago(n.createdAt)} · ${n.kind}`), h('div', { class: 'tl-body' }, n.text))));
  return h('div', { class: 'grid grid-2' }, card(cardHead('Add note'), field('Category', kind), field('Note', ta), btn('Save note', async () => { if (!ta.value.trim()) return; await addMemberNote(uid, ta.value.trim(), kind.value); toast('Saved', 'success'); location.reload(); }, { variant: 'btn-primary' })), card(cardHead(`Notes (${rows.length})`), rows.length ? list : h('p', { class: 'muted' }, 'No notes yet.')));
}
async function security(u, uid) {
  const rows = await securityLogsFor(uid);
  return card(cardHead('Sign-in and security events'), table([{ label: 'When', render: r => fmtDateTime(r.timestamp) }, { label: 'Event', render: r => badge(r.success === false || /lock|fail/.test(r.event) ? 'failed' : 'active', r.event) }, { label: 'Method', key: 'authentication_method' }, { label: 'Reason', key: 'reason' }], rows.sort((a, b) => (b.timestamp?.toMillis?.() || 0) - (a.timestamp?.toMillis?.() || 0)), { empty: 'No security events' }));
}
async function sendNote(uid) {
  const t = input({ placeholder: 'Title' }); const b = textarea({ placeholder: 'Message shown in the member\'s inbox' });
  const route = select([['', 'No link'], ['billing', 'Billing'], ['planDetails', 'Plan details'], ['appointments', 'Appointments'], ['scriptRefill', 'Prescription refills'], ['ChatLanding', 'Help center']], '');
  const { modal } = await import('../../ui.js');
  const m = modal('Send in-app notification', h('div', { class: 'col' }, field('Title', t), field('Message', b), field('Opens page', route)), [btn('Cancel', () => m.close()), btn('Send', async () => { if (!t.value.trim() || !b.value.trim()) return; try { await notifyMember(uid, { type: 'system', title: t.value.trim(), body: b.value.trim(), route: route.value || null }); toast('Sent to inbox', 'success'); m.close(); } catch (e) { errorToast(e); } }, { variant: 'btn-primary' })]);
}
