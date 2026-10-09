import { h, pageHeader, card, cardHead, stat, table, badge, money, fmtDate, fmtDateTime, sum, groupBy, select, searchBox, downloadCsv, btn, avatar, toast, errorToast, confirm } from '../../ui.js';
import { cachedMembers, paymentLogs, kurvPassCancellations, nextBilling, monthKey, lastMonths, JOVI_PASS_PRICE, allRequests } from '../../data.js';
import { navigate } from '../../router.js';
import { functions, httpsCallable } from '../../firebase.js';
import { can } from '../../auth.js';

export async function render() {
  const wrap = h('div');
  const [members, logs, passCancels, requests] = await Promise.all([cachedMembers(), paymentLogs(1000).catch(() => []), kurvPassCancellations().catch(() => []), allRequests().catch(() => [])]);
  const active = members.filter(m => ['active', 'canceling', 'past_due'].includes(m.status));
  const mrr = sum(active, 'monthly'); const health = sum(active, m => Number(m.totalHealthPremium ?? m.totalPremium) || 0); const petRev = sum(active, m => Number(m.petTotalPremium) || 0);
  const dental = active.filter(m => m.hasDental || m.dental).length, vision = active.filter(m => m.hasVision || m.vision).length;
  const passSales = requests.filter(r => r.priority || r.kurvPassPurchased).length;
  const months = lastMonths(6);
  const ok = p => ['success', 'succeeded', 'ok'].includes(String(p.status).toLowerCase());
  const byM = groupBy(logs, p => monthKey(p.timestamp) || 'unknown');
  const maxM = Math.max(1, ...months.map(m => sum((byM[m.key] || []).filter(ok), 'amount')));
  const bars = h('div', { class: 'bars-wrap' }, h('div', { class: 'bars' }, months.map(m => { const v = sum((byM[m.key] || []).filter(ok), 'amount'); return h('div', { class: 'bar mint', style: { height: `${Math.max(3, v / maxM * 100)}%` }, title: money(v) }, h('span', null, m.label)); })));
  const next7 = new Date(Date.now() + 7 * 86400000);
  const dueSoon = active.filter(m => { const d = nextBilling(m); return d && d <= next7; });
  let q = '', st = ''; const logBody = h('div');
  const cols = [
    { label: 'When', render: p => fmtDateTime(p.timestamp), csv: p => p.timestamp?.toDate?.().toISOString() || '' },
    { label: 'Member', render: p => { const m = members.find(x => x.id === p.userId); return m ? h('a', { href: `#/admin/member/${p.userId}`, class: 'who' }, avatar(m.name, m.photo, 26), h('b', null, m.name)) : h('span', { class: 'mono small' }, p.userId); }, csv: p => members.find(x => x.id === p.userId)?.name || p.userId },
    { label: 'Type', key: 'type', csv: 'type' }, { label: 'Amount', render: p => money(p.amount), csv: 'amount', align: 'right' }, { label: 'Status', render: p => badge(ok(p) ? 'success' : 'failed', p.status), csv: 'status' }, { label: 'Attempt', key: 'attemptNumber', csv: 'attemptNumber' }, { label: 'Reason', render: p => h('span', { class: 'small muted' }, p.reason || ''), csv: 'reason' },
  ];
  const drawLogs = () => { const f = logs.filter(p => (!st || (st === 'ok' ? ok(p) : !ok(p))) && (!q || JSON.stringify(p).toLowerCase().includes(q.toLowerCase()))); logBody.replaceChildren(table(cols, f.slice(0, 300), { empty: 'No payment events' })); };
  const billPanel = h('div', { class: 'callout mint mb' }, h('div', { class: 'grow' }, h('b', null, 'BILL (ACH) processor'), h('div', { class: 'small', id: 'billStatusLine' }, 'Not checked yet.')), can('writeBusiness') ? btn('Test connection', async () => { const line = billPanel.querySelector('#billStatusLine'); line.textContent = 'Checking…'; try { const r = (await httpsCallable(functions, 'billStatus')({})).data; line.textContent = `${r.ok ? '✓' : '✕'} ${r.message} · env ${r.env}${r.orgName ? ' · ' + r.orgName : ''}${r.customersReachable === false ? ' · customers: ' + r.customersError : r.customersReachable ? ' · customers API reachable' : ''}${r.orgLookup ? ' · org lookup: ' + r.orgLookup : ''}`; toast(r.ok ? 'BILL connection OK' : 'BILL connection failed', r.ok ? 'success' : 'error', 6000); } catch (e) { line.textContent = 'Error: ' + (e.message || e); errorToast(e); } }, { size: 'btn-sm', variant: 'btn-primary' }) : null);
  wrap.append(pageHeader('Billing & revenue', 'Recurring revenue from plan data plus processor events. Bank and card numbers are never stored here.', [btn('Export payments CSV', () => downloadCsv('jovi-payments.csv', cols, logs))]), billPanel,
    h('div', { class: 'grid grid-4 mb' }, stat('MRR', money(mrr, { cents: false }), `${active.length} paying memberships`, 'brand'), stat('Health premiums', money(health, { cents: false }), `${money(health / Math.max(1, active.length))} avg per membership`), stat('Pet premiums', money(petRev, { cents: false }), `${active.filter(m => m.hasPetInsurance).length} households`), stat('Add-ons', `${dental} / ${vision}`, 'dental / vision memberships')),
    h('div', { class: 'grid grid-4 mb' }, stat('Collected, last 30 days', money(sum(logs.filter(p => ok(p) && (p.timestamp?.toMillis?.() || 0) > Date.now() - 30 * 86400000), 'amount'), { cents: false }), 'from webhook events', 'good'), stat('Failed, last 30 days', logs.filter(p => !ok(p) && (p.timestamp?.toMillis?.() || 0) > Date.now() - 30 * 86400000).length, 'attempts', 'bad'), stat('Jovi Pass sales', passSales, `${money(passSales * JOVI_PASS_PRICE, { cents: false })} · ${passCancels.length} non-refundable cancels`), stat('Due in 7 days', dueSoon.length, money(sum(dueSoon, 'monthly'), { cents: false }))),
    h('div', { class: 'grid grid-2 mb' },
      card(cardHead('Collected by month'), bars),
      card(cardHead('Billing in the next 7 days'), table([{ label: 'Member', render: m => h('a', { href: `#/admin/member/${m.id}`, class: 'who' }, avatar(m.name, m.photo, 26), h('b', null, m.name)) }, { label: 'Date', render: m => fmtDate(nextBilling(m)) }, { label: 'Amount', render: m => money(m.monthly), align: 'right' }, { label: 'Card', render: m => m.cardLast4 ? `•••• ${m.cardLast4}` : '—' }], dueSoon.sort((a, b) => nextBilling(a) - nextBilling(b)).slice(0, 12), { onRow: m => navigate(`/admin/member/${m.id}`), empty: 'Nothing due this week' }))),
    card(cardHead('Payment events', h('div', { class: 'row' }, searchBox('Search…', v => { q = v; drawLogs(); }), select([['', 'All'], ['ok', 'Succeeded'], ['fail', 'Failed']], '', { onChange: e => { st = e.target.value; drawLogs(); } }))), logBody));
  drawLogs();
  return wrap;
}
