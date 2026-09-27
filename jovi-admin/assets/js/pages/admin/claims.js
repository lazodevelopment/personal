import { h, pageHeader, card, cardHead, stat, table, badge, money, fmtDate, sum, groupBy, select, searchBox, downloadCsv, btn, avatar } from '../../ui.js';
import { cachedMembers, claimsQueue, monthKey, lastMonths } from '../../data.js';
import { navigate } from '../../router.js';
import { can, canSide } from '../../auth.js';

// Business view of claims: amounts, statuses, turnaround. No receipts, reasons, or providers.
export async function render() {
  const wrap = h('div');
  const [members, claims] = await Promise.all([cachedMembers(), claimsQueue(2000)]);
  const openS = ['submitted', 'pending', 'processing', 'under_review', 'needs_more_info'];
  const open = claims.filter(c => openS.includes(c.statusL)); const approved = claims.filter(c => ['approved', 'paid'].includes(c.statusL)); const rejected = claims.filter(c => ['rejected', 'denied'].includes(c.statusL));
  const months = lastMonths(6); const byM = groupBy(claims, c => monthKey(c.when) || 'unknown');
  const maxM = Math.max(1, ...months.map(m => sum(byM[m.key] || [], 'amount')));
  const bars = h('div', { class: 'bars-wrap' }, h('div', { class: 'bars' }, months.map(m => h('div', { class: 'bar', style: { height: `${Math.max(3, sum(byM[m.key] || [], 'amount') / maxM * 100)}%` }, title: `${(byM[m.key] || []).length} claims · ${money(sum(byM[m.key] || [], 'amount'))}` }, h('span', null, m.label)))));
  const turnaround = approved.map(c => { const a = c.reviewedAt?.toMillis?.() || c.updatedAt?.toMillis?.(); const s = c.when?.getTime(); return a && s ? (a - s) / 86400000 : null; }).filter(x => x != null);
  let q = '', st = '', kind = ''; const body = h('div');
  const cols = [
    { label: 'Submitted', render: c => fmtDate(c.when), csv: c => c.when?.toISOString().slice(0, 10) || '' },
    { label: 'Member', render: c => { const m = members.find(x => x.id === c.uid); return m ? h('a', { href: `#/admin/member/${c.uid}`, class: 'who' }, avatar(m.name, m.photo, 26), h('b', null, m.name)) : h('span', { class: 'mono small' }, c.uid); }, csv: c => members.find(x => x.id === c.uid)?.name || c.uid },
    { label: 'Kind', render: c => c.isPet ? badge('info', `Pet · ${c.petName || ''}`) : (c.type === 'receipt' ? 'Reimburse member' : 'Pay provider'), csv: c => c.isPet ? 'pet' : c.type },
    { label: 'Amount', render: c => money(c.amount), align: 'right', csv: 'amount' },
    { label: 'Est. payout', render: c => c.isPet ? money(c.finalReimbursement ?? c.estimatedReimbursement ?? c.amount * 0.9) : c.paidAmount != null ? money(c.paidAmount) : '—', align: 'right', csv: c => c.finalReimbursement ?? c.estimatedReimbursement ?? c.paidAmount ?? '' },
    { label: 'Status', render: c => badge(c.statusL), csv: 'status' },
    { label: 'Reviewed by', render: c => c.reviewedByName || '—', csv: 'reviewedByName' },
  ];
  const draw = () => { const f = claims.filter(c => (!st || (st === 'open' ? openS.includes(c.statusL) : c.statusL === st)) && (!kind || (kind === 'pet') === c.isPet) && (!q || (members.find(x => x.id === c.uid)?.name || '').toLowerCase().includes(q.toLowerCase()))).sort((a, b) => (b.when?.getTime() || 0) - (a.when?.getTime() || 0)); body.replaceChildren(table(cols, f.slice(0, 400), { empty: 'No claims match' })); };
  wrap.append(pageHeader('Claims (financial)', 'Volume, exposure, and turnaround. Receipts and reasons are reviewed on the clinical side.', [can('decideClaims') && canSide('ehr') ? btn('Review queue', () => navigate('/ehr/claims'), { variant: 'btn-primary' }) : null, btn('Export CSV', () => downloadCsv('jovi-claims.csv', cols, claims))].filter(Boolean)),
    h('div', { class: 'grid grid-4 mb' }, stat('Open claims', open.length, `${money(sum(open, 'amount'), { cents: false })} requested`, open.length ? 'warn' : ''), stat('Approved / paid', approved.length, money(sum(approved, c => c.finalReimbursement ?? c.paidAmount ?? c.amount), { cents: false }), 'good'), stat('Rejected', rejected.length, `${Math.round(rejected.length / Math.max(1, claims.length) * 100)}% of all claims`), stat('Avg turnaround', turnaround.length ? `${(sum(turnaround, x => x) / turnaround.length).toFixed(1)} d` : '—', 'submitted to decision')),
    h('div', { class: 'grid grid-2 mb' }, card(cardHead('Claimed amount by month'), bars), card(cardHead('By status'), h('div', { class: 'list' }, Object.entries(groupBy(claims, 'statusL')).sort((a, b) => b[1].length - a[1].length).map(([k, v]) => h('div', { class: 'list-item' }, badge(k), h('div', { class: 'grow' }, h('b', null, `${v.length} claims`), h('span', null, money(sum(v, 'amount'))))))))),
    card(cardHead('All claims', h('div', { class: 'row' }, searchBox('Member…', v => { q = v; draw(); }), select([['', 'All statuses'], ['open', 'Open'], 'approved', 'paid', 'rejected', 'needs_more_info'], '', { onChange: e => { st = e.target.value; draw(); } }), select([['', 'Human + pet'], ['human', 'Human'], ['pet', 'Pet']], '', { onChange: e => { kind = e.target.value; draw(); } }))), body));
  draw();
  return wrap;
}
