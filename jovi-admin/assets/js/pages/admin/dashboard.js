import { h, pageHeader, card, cardHead, stat, table, badge, money, fmtDate, ago, sum, groupBy, avatar, btn } from '../../ui.js';
import { cachedMembers, allRequests, paymentLogs, claimsQueue, refillQueue, tickets, monthKey, lastMonths, CLINICS } from '../../data.js';
import { navigate } from '../../router.js';

export async function render() {
  const wrap = h('div');
  wrap.append(pageHeader('Dashboard', 'Membership, revenue, and operations at a glance. No clinical detail on this side.'));
  const [members, requests, pays, claims, refills, open] = await Promise.all([
    cachedMembers(), allRequests(), paymentLogs(400).catch(() => []), claimsQueue(400).catch(() => []), refillQueue().catch(() => []), tickets('open').catch(() => []),
  ]);
  const active = members.filter(m => ['active', 'canceling', 'past_due'].includes(m.status));
  const mrr = sum(active, 'monthly');
  const pets = sum(members, m => Number(m.numPets) || 0);
  const now = new Date(); const in30 = new Date(Date.now() + 30 * 86400000);
  const newThisMonth = members.filter(m => monthKey(m.created_time || m.membershipStartDate) === monthKey(now)).length;
  const churnRisk = members.filter(m => ['past_due', 'suspended', 'canceling'].includes(m.status));
  const upcoming = requests.filter(r => r.start && r.start >= now && r.start <= in30 && ['pending', 'confirmed'].includes(r.statusL));
  const pendingClaims = claims.filter(c => ['submitted', 'pending', 'processing', 'under_review', 'needs_more_info'].includes(c.statusL));
  const failed = pays.filter(p => String(p.status).toLowerCase() !== 'success' && String(p.status).toLowerCase() !== 'succeeded');

  const months = lastMonths(6);
  const byMonth = groupBy(members, m => monthKey(m.created_time || m.membershipStartDate) || 'unknown');
  const maxM = Math.max(1, ...months.map(m => (byMonth[m.key] || []).length));
  const bars = h('div', { class: 'bars-wrap' }, h('div', { class: 'bars' }, months.map(m => h('div', { class: 'bar coral', style: { height: `${Math.max(3, ((byMonth[m.key] || []).length / maxM) * 100)}%` }, title: `${(byMonth[m.key] || []).length} joined` }, h('span', null, m.label)))));

  const byClinic = groupBy(upcoming, r => r.clinic || (r.visitMode === 'Virtual' ? 'Virtual' : 'Unassigned'));

  wrap.append(
    h('div', { class: 'grid grid-4 mb' },
      stat('Active members', active.length, `${newThisMonth} joined this month`, 'good'),
      stat('Monthly recurring revenue', money(mrr, { cents: false }), `${money(mrr * 12, { cents: false })} annualized`, 'brand'),
      stat('Pets covered', pets, `${members.filter(m => m.hasPetInsurance).length} households`),
      stat('At-risk memberships', churnRisk.length, 'past due, suspended, or canceling', churnRisk.length ? 'bad' : ''),
    ),
    h('div', { class: 'grid grid-4 mb' },
      stat('Appointments next 30 days', upcoming.length, `${requests.filter(r => r.statusL === 'pending').length} awaiting confirmation`),
      stat('Claims to review', pendingClaims.length, `${money(sum(pendingClaims, 'amount'), { cents: false })} requested`, pendingClaims.length ? 'warn' : ''),
      stat('Refills in queue', refills.length, `${refills.filter(r => r.status === 'requested').length} new`),
      stat('Open support tickets', open.length, `${open.filter(t => (t.priority ?? 3) <= 1).length} high priority`, open.some(t => t.priority === 0) ? 'bad' : ''),
    ),
    h('div', { class: 'grid grid-2' },
      card(cardHead('New members, last 6 months'), bars),
      card(cardHead('Upcoming visits by clinic'), h('div', { class: 'list' }, Object.entries(byClinic).sort((a, b) => b[1].length - a[1].length).map(([k, v]) => h('div', { class: 'list-item' }, h('div', { class: 'grow' }, h('b', null, k), h('span', null, `${v.filter(r => r.isPet).length} pet · ${v.filter(r => !r.isPet).length} human`)), badge('info', v.length))), !upcoming.length ? h('p', { class: 'muted' }, 'No upcoming visits.') : null)),
      card(cardHead('Recent failed payments', btn('Billing', () => navigate('/admin/billing'), { size: 'btn-sm' })), table([
        { label: 'Member', render: p => memberCell(members, p.userId) },
        { label: 'Amount', render: p => money(p.amount) },
        { label: 'Attempt', key: 'attemptNumber' },
        { label: 'Reason', render: p => h('span', { class: 'small muted' }, p.reason || '—') },
        { label: 'When', render: p => ago(p.timestamp) },
      ], failed.slice(0, 8), { empty: 'No failed payments' })),
      card(cardHead('Memberships needing attention', btn('Members', () => navigate('/admin/members'), { size: 'btn-sm' })), table([
        { label: 'Member', render: m => h('div', { class: 'who' }, avatar(m.name, m.photo, 28), h('div', null, h('b', null, m.name), h('span', null, m.email || ''))) },
        { label: 'Status', render: m => badge(m.status) },
        { label: 'Monthly', render: m => money(m.monthly) },
        { label: 'Flag', render: m => m.pendingBillingReview ? badge('pending', 'Billing review') : m.lastChargeStatus && m.lastChargeStatus !== 'ok' ? badge('failed', m.lastChargeStatus) : '—' },
      ], [...churnRisk, ...members.filter(m => m.pendingBillingReview && !churnRisk.includes(m))].slice(0, 8), { onRow: m => navigate(`/admin/member/${m.id}`), empty: 'Everyone is in good standing' })),
    ),
  );
  return wrap;
}
export function memberCell(members, uid) { const m = members.find(x => x.id === uid); return m ? h('a', { href: `#/admin/member/${uid}`, class: 'who' }, avatar(m.name, m.photo, 26), h('div', null, h('b', null, m.name))) : h('span', { class: 'mono small' }, uid || '—'); }
