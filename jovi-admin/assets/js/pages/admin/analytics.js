import { h, pageHeader, card, cardHead, stat, table, money, sum, groupBy, pct } from '../../ui.js';
import { cachedMembers, allRequests, claimsQueue, paymentLogs, parseDob, memberDob, monthKey, lastMonths, CLINICS } from '../../data.js';
import { age } from '../../ui.js';

export async function render() {
  const wrap = h('div');
  const [members, reqs, claims, pays] = await Promise.all([cachedMembers(), allRequests(3000), claimsQueue(2000).catch(() => []), paymentLogs(1000).catch(() => [])]);
  const active = members.filter(m => ['active', 'canceling', 'past_due'].includes(m.status));
  const months = lastMonths(12);
  // Cohort: joins vs cancels per month
  const joins = groupBy(members, m => monthKey(m.created_time || m.membershipStartDate));
  const cancels = groupBy(members.filter(m => m.canceledAt), m => monthKey(m.canceledAt));
  const rows = months.map(m => ({ month: m.label, joined: (joins[m.key] || []).length, canceled: (cancels[m.key] || []).length, net: (joins[m.key] || []).length - (cancels[m.key] || []).length }));
  // Age bands + pricing mix
  const bands = { '18–29': 0, '30–39': 0, '40–49': 0, '50–59': 0, '60+': 0, 'unknown': 0 };
  for (const m of members) { const a = age(parseDob(memberDob(m))); if (a == null) bands.unknown++; else if (a <= 29) bands['18–29']++; else if (a <= 39) bands['30–39']++; else if (a <= 49) bands['40–49']++; else if (a <= 59) bands['50–59']++; else bands['60+']++; }
  const byState = groupBy(active, m => m.state || 'unknown');
  const family = active.filter(m => (m.planType || m.planTier) === 'Family').length;
  const arpu = sum(active, 'monthly') / Math.max(1, active.length);
  const ltvMonths = 18; // assumption; show as such
  const lossRatio = (() => { const paid = sum(claims.filter(c => ['approved', 'paid'].includes(c.statusL)), c => c.finalReimbursement ?? c.paidAmount ?? c.amount); const collected = sum(pays.filter(p => ['success', 'succeeded'].includes(String(p.status).toLowerCase())), 'amount'); return collected ? paid / collected : null; })();
  const utilization = active.length ? reqs.filter(r => r.start && r.start > new Date(Date.now() - 90 * 86400000)).length / active.length : 0;
  const barsOf = (data, key, cls = '') => { const max = Math.max(1, ...data.map(d => d[key])); return h('div', { class: 'bars-wrap' }, h('div', { class: 'bars' }, data.map(d => h('div', { class: `bar ${cls}`, style: { height: `${Math.max(3, d[key] / max * 100)}%` }, title: `${d.month}: ${d[key]}` }, h('span', null, d.month))))); };
  wrap.append(pageHeader('Analytics', 'Growth, mix, and unit economics from live data. Assumptions are labeled.'),
    h('div', { class: 'grid grid-4 mb' }, stat('ARPU', money(arpu), 'monthly, active memberships', 'brand'), stat('Family plan share', `${pct(family, active.length)}%`, `${family} of ${active.length}`), stat('Claims loss ratio', lossRatio == null ? '—' : `${Math.round(lossRatio * 100)}%`, 'paid claims ÷ collected premiums (webhook data)'), stat('Visits per member, 90d', utilization.toFixed(2), 'all visit types')),
    h('div', { class: 'grid grid-2 mb' }, card(cardHead('Joins by month'), barsOf(rows, 'joined', 'mint')), card(cardHead('Cancellations by month'), barsOf(rows, 'canceled', 'coral'))),
    h('div', { class: 'grid grid-3 mb' },
      card(cardHead('Members by age band'), h('div', { class: 'list' }, Object.entries(bands).map(([k, v]) => h('div', { class: 'list-item' }, h('div', { class: 'grow' }, h('b', null, k)), h('span', null, `${v} · ${pct(v, members.length)}%`))))),
      card(cardHead('Active by state'), h('div', { class: 'list' }, Object.entries(byState).sort((a, b) => b[1].length - a[1].length).map(([k, v]) => h('div', { class: 'list-item' }, h('div', { class: 'grow' }, h('b', null, k)), h('span', null, `${v.length} · ${money(sum(v, 'monthly'), { cents: false })}/mo`))))),
      card(cardHead('Add-on attach rates'), h('div', { class: 'list' }, [['Dental', active.filter(m => m.hasDental || m.dental).length], ['Vision', active.filter(m => m.hasVision || m.vision).length], ['Pets', active.filter(m => m.hasPetInsurance).length], ['Tobacco surcharge', active.filter(m => m.hasTobacco || m.tobacco).length], ['Jovi Pass buyers', members.filter(m => m.lastKurvPassPurchase).length]].map(([k, v]) => h('div', { class: 'list-item' }, h('div', { class: 'grow' }, h('b', null, k)), h('span', null, `${v} · ${pct(v, active.length)}%`)))))),
    card(cardHead('Monthly cohort table'), table([{ label: 'Month', key: 'month' }, { label: 'Joined', key: 'joined' }, { label: 'Canceled', key: 'canceled' }, { label: 'Net', render: r => h('b', { class: r.net < 0 ? 'danger' : '' }, r.net) }], rows)),
    h('p', { class: 'muted small mt' }, `Lifetime value estimate at ${ltvMonths} months average tenure: ${money(arpu * ltvMonths, { cents: false })} per membership. Tenure is an assumption until there is a year of churn data.`));
  return wrap;
}
