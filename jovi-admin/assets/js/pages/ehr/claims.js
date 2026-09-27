import { h, pageHeader, card, cardHead, table, badge, btn, tabs, ago, fmtDate, fmtDateTime, money, toast, errorToast, prompt, kv, drawer, closeDrawer, input, field, textarea, avatar } from '../../ui.js';
import { claimsQueue, decideClaim, cachedMembers, deductibleOf, getMember } from '../../data.js';
import { can } from '../../auth.js';
import { navigate } from '../../router.js';

const OPEN = ['submitted', 'pending', 'processing', 'under_review', 'needs_more_info'];
export async function render() {
  const wrap = h('div'); const body = h('div'); let tab = 'open';
  const members = await cachedMembers(); const nm = uid => members.find(m => m.id === uid)?.name || uid;
  const TABS = [['open', 'Open'], ['approved', 'Approved / paid'], ['rejected', 'Rejected'], ['all', 'All']];
  async function draw() {
    body.replaceChildren(tabs(TABS, tab, t => { tab = t; draw(); }), h('div', { class: 'spinner-wrap' }, h('span', { class: 'spinner' })));
    const all = (await claimsQueue(2000)).sort((a, b) => (a.when?.getTime() || 0) - (b.when?.getTime() || 0));
    const rows = tab === 'open' ? all.filter(c => OPEN.includes(c.statusL)) : tab === 'approved' ? all.filter(c => ['approved', 'paid'].includes(c.statusL)) : tab === 'rejected' ? all.filter(c => ['rejected', 'denied'].includes(c.statusL)) : all;
    body.replaceChildren(tabs(TABS, tab, t => { tab = t; draw(); }), card(table([
      { label: 'Submitted', render: c => ago(c.when) }, { label: 'Member', render: c => h('a', { href: `#/ehr/chart/${c.uid}`, class: 'lnk' }, nm(c.uid)) }, { label: 'Kind', render: c => c.isPet ? badge('info', `Pet · ${c.petName || ''}`) : c.type === 'receipt' ? 'Reimburse member' : 'Pay provider' }, { label: 'Provider', render: c => c.provider || c.providerClinic || '—' }, { label: 'Service date', render: c => fmtDate(c.date || c.dateOfService) }, { label: 'Amount', render: c => money(c.amount), align: 'right' }, { label: 'Status', render: c => badge(c.statusL) }, { label: 'Receipt', render: c => c.photoUrl ? h('a', { href: c.photoUrl, target: '_blank', class: 'lnk' }, 'View') : h('span', { class: 'muted' }, 'none') }, { label: '', render: c => btn('Review', () => review(c, draw), { size: 'btn-sm', variant: OPEN.includes(c.statusL) ? 'btn-primary' : 'btn-secondary' }) },
    ], rows, { empty: 'No claims' })));
  }
  wrap.append(pageHeader('Claims review', 'Receipts and provider bills from members, plus pet claims at 90% after the $500 pet deductible. Decisions notify the member.'), body);
  await draw();
  return wrap;
}

export async function review(c, redraw = () => {}) {
  const u = await getMember(c.uid).catch(() => null);
  const ded = u ? deductibleOf(u) : null; const met = Number(u?.updateDed) || 0;
  const est = c.isPet ? (c.finalReimbursement ?? c.estimatedReimbursement ?? Math.max(0, (Number(c.amount) - 500) * 0.9)) : Math.max(0, Number(c.amount) - Math.max(0, (ded || 0) - met));
  const payout = input({ type: 'number', step: '0.01', value: (c.finalReimbursement ?? c.paidAmount ?? est).toFixed(2) });
  const note = textarea({ placeholder: 'Reviewer note (internal)', rows: 2, value: c.reviewNote || '' });
  const canDecide = can('decideClaims') && !['paid'].includes(c.statusL);
  const decide = async (status, extra = {}) => { try { await decideClaim(c, status, { reviewNote: note.value.trim(), ...extra }); toast(`Claim ${status.replace('_', ' ')}. Member notified.`, 'success'); closeDrawer(); redraw(); } catch (e) { errorToast(e); } };
  drawer(`${c.isPet ? 'Pet claim' : 'Claim'} · ${money(c.amount)}`, h('div', { class: 'col' },
    h('div', { class: 'row' }, badge(c.statusL), c.isPet ? badge('info', `${c.petName} · ${c.petType || ''}`) : badge('info', c.type === 'receipt' ? 'Reimburse member' : 'Pay provider'), c.payWithGoodRx ? badge('pending', 'GoodRx') : null),
    card(kv('Member', h('a', { href: `#/ehr/chart/${c.uid}`, class: 'lnk' }, u ? (u.onboard_fullName || u.email) : c.uid)), kv('For', c.isPet ? c.petName : c.memberId === 'primary' ? 'Primary member' : c.memberId === 'spouse' ? 'Spouse' : `Dependent ${c.memberId || ''}`), kv('Provider', c.provider || c.providerClinic || '—'), kv('Service date', fmtDate(c.date || c.dateOfService)), kv('Reason', c.reason || '—'), kv('Submitted', fmtDateTime(c.submittedAt || c.date)), kv('Amount claimed', money(c.amount)), c.isPet ? kv('Pet coverage', `90% after $500 · est. ${money(c.estimatedReimbursement ?? est)}`) : kv('Member deductible', `${money(ded, { cents: false })} · ${money(met)} met so far`), c.memberAcknowledgedExclusions != null ? kv('Exclusions acknowledged', c.memberAcknowledgedExclusions ? 'Yes' : 'No') : null),
    c.photoUrl ? card(cardHead('Receipt', h('a', { href: c.photoUrl, target: '_blank', class: 'lnk' }, 'Open full size')), h('img', { src: c.photoUrl, style: { maxWidth: '100%', borderRadius: '10px' } })) : h('div', { class: 'callout' }, h('div', null, 'No receipt image was attached.')),
    (c.correspondences || []).length ? card(cardHead('Additional documents'), h('div', { class: 'list' }, c.correspondences.map(x => h('a', { class: 'list-item', href: x.url, target: '_blank' }, h('div', { class: 'grow' }, h('b', null, x.description || x.type || 'Document'), h('span', null, fmtDateTime(x.uploadedAt))))))) : null,
    canDecide ? card(cardHead('Decision'), field('Payout amount', payout, c.isPet ? 'Final reimbursement stored on the claim' : 'Amount Jovi will pay'), field('Reviewer note', note), h('div', { class: 'row' },
      btn('Approve', () => decide('approved', c.isPet ? { finalReimbursement: Number(payout.value) } : { paidAmount: Number(payout.value) }), { variant: 'btn-success' }),
      btn('Mark paid', () => decide('paid', c.isPet ? { finalReimbursement: Number(payout.value) } : { paidAmount: Number(payout.value), paymentProcessed: true }), { variant: 'btn-primary' }),
      btn('Needs more info', async () => { const why = await prompt('What is missing?', 'Message to the member'); if (why == null) return; decide('needs_more_info', { infoRequested: why }); }),
      btn('Reject', async () => { const why = await prompt('Reject claim', 'Reason (sent to the member)'); if (why == null) return; decide('rejected', { rejectionReason: why }); }, { variant: 'btn-danger' }))) : null,
    c.reviewedByName ? h('p', { class: 'muted small' }, `Last reviewed by ${c.reviewedByName} · ${fmtDateTime(c.reviewedAt)}${c.reviewNote ? ' · ' + c.reviewNote : ''}`) : null,
  ), { wide: true });
}
