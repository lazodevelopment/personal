import { h, pageHeader, card, cardHead, stat, table, badge, btn, ago, fmtDateTime, money, avatar } from '../../ui.js';
import { pendingRequests, refillQueue, careRefillQueue, claimsQueue, tickets, vaccinationsDue, cachedMembers, recentVisitRecords } from '../../data.js';
import { navigate } from '../../router.js';
import { openRequest } from './schedule.js';

export async function render() {
  const wrap = h('div');
  const [pending, refills, careRefills, claims, open, vax, members, notes] = await Promise.all([
    pendingRequests().catch(() => []), refillQueue(['requested']).catch(() => []), careRefillQueue().catch(() => []), claimsQueue(500).catch(() => []), tickets('open').catch(() => []), vaccinationsDue(14).catch(() => []), cachedMembers(), recentVisitRecords(50).catch(() => []),
  ]);
  const nm = uid => members.find(m => m.id === uid)?.name || uid;
  const newClaims = claims.filter(c => ['submitted', 'pending', 'processing'].includes(c.statusL)).sort((a, b) => (a.when?.getTime() || 0) - (b.when?.getTime() || 0));
  const unsigned = notes.filter(n => !n.signedAt);
  const now = new Date(); const todayPending = pending.filter(r => r.start && r.start.toDateString() === now.toDateString());
  wrap.append(pageHeader('Clinical inbox', 'Everything waiting on a clinician, oldest first.'),
    h('div', { class: 'grid grid-4 mb' }, stat('Unconfirmed visits', pending.length, `${todayPending.length} today`, pending.length ? 'warn' : ''), stat('Refill requests', refills.length + careRefills.length, `${refills.length} from Rx list · ${careRefills.length} via Request Care`, refills.length ? 'warn' : ''), stat('Claims to review', newClaims.length, money(newClaims.reduce((a, c) => a + (Number(c.amount) || 0), 0), { cents: false })), stat('Unsigned notes', unsigned.length, 'encounters without a signature', unsigned.length ? 'bad' : '')),
    h('div', { class: 'grid grid-2' },
      card(cardHead('Visits awaiting confirmation', btn('Schedule', () => navigate('/ehr/schedule'), { size: 'btn-sm' })), table([{ label: 'When', render: r => r.start ? fmtDateTime(r.start) : '—' }, { label: 'Patient', render: r => h('div', { class: 'who' }, avatar(r.patientName, null, 26), h('div', null, h('b', null, r.patientName), h('span', null, `${r.isPet ? 'Pet · ' : ''}${r.visitType}`))) }, { label: 'Where', render: r => r.visitMode === 'Virtual' ? 'Virtual' : (r.clinic || '').split(' - ')[1] || r.clinic }, { label: 'Pass', render: r => r.priority ? badge('active', '⚡') : '' }], pending.slice(0, 12), { onRow: r => openRequest(r), empty: 'All confirmed' })),
      card(cardHead('Refill requests', btn('Queue', () => navigate('/ehr/refills'), { size: 'btn-sm' })), table([{ label: 'Requested', render: r => ago(r.requestedDate || r.createdAt) }, { label: 'Member', render: r => h('b', null, nm(r.userId)) }, { label: 'Medication', render: r => r.medicationName }, { label: 'Pharmacy', render: r => r.pharmacyName || '—' }], refills.slice(0, 12), { onRow: () => navigate('/ehr/refills'), empty: 'No refill requests' })),
      card(cardHead('New claims', btn('Review', () => navigate('/ehr/claims'), { size: 'btn-sm' })), table([{ label: 'Submitted', render: c => ago(c.when) }, { label: 'Member', render: c => h('b', null, nm(c.uid)) }, { label: 'Kind', render: c => c.isPet ? `Pet · ${c.petName || ''}` : c.type === 'receipt' ? 'Receipt' : 'Provider bill' }, { label: 'Amount', render: c => money(c.amount), align: 'right' }], newClaims.slice(0, 12), { onRow: () => navigate('/ehr/claims'), empty: 'No new claims' })),
      card(cardHead('Boosters due in 14 days', btn('All due', () => navigate('/ehr/vaccinations'), { size: 'btn-sm' })), table([{ label: 'Due', render: v => v.due ? v.due.toLocaleDateString() : '—' }, { label: 'Who', render: v => h('b', null, v.kind === 'pet' ? `${nm(v.uid)}'s pet` : (v.patientName || nm(v.uid))) }, { label: 'Vaccine', render: v => v.vaccineName }], vax.slice(0, 12), { empty: 'Nothing due' })),
      card(cardHead('Open support tickets', btn('Inbox', () => navigate('/ehr/messages'), { size: 'btn-sm' })), table([{ label: 'Opened', render: t => ago(t.createdAt) }, { label: 'Member', render: t => h('b', null, t.userName || nm(t.userId)) }, { label: 'Issue', key: 'issueType' }, { label: 'Priority', render: t => badge(t.priority === 0 ? 'failed' : t.priority === 1 ? 'pending' : 'info', t.priorityLevel || '') }], open.slice(0, 10), { onRow: t => navigate(`/ehr/messages/${t.id}`), empty: 'No open tickets' })),
      card(cardHead('Unsigned encounter notes'), table([{ label: 'Visit', render: n => fmtDateTime(n.visitDate) }, { label: 'Patient', render: n => h('b', null, n.patientName || nm(n.uid)) }, { label: 'Provider', key: 'providerName' }], unsigned.slice(0, 10), { onRow: n => navigate(`/ehr/chart/${n.uid}/note/${n.id}`), empty: 'All notes signed' })),
    ));
  return wrap;
}
