import { h, pageHeader, card, cardHead, stat, table, badge, money, fmtDate, fmtDateTime, sum, select, searchBox, downloadCsv, btn, avatar, drawer, kv, toast, errorToast } from '../../ui.js';
import { cachedMembers, invoicesAll, notifyMember } from '../../data.js';
import { can } from '../../auth.js';

export const KIND = { membership: 'Monthly membership', membership_retry: 'Monthly membership (retry)', kurvpass: 'Jovi Pass', pet_addon_proration: 'Jovi Pets add-on' };
export async function render() {
  const wrap = h('div'); const body = h('div'); let q = '', st = '';
  const [members, rows] = await Promise.all([cachedMembers(), invoicesAll(1000)]);
  const nm = uid => members.find(m => m.id === uid)?.name || uid;
  const paid = rows.filter(r => r.status === 'paid'); const open = rows.filter(r => ['pending', 'failed', 'returned'].includes(r.status));
  const cols = [
    { label: 'Number', render: r => h('span', { class: 'mono' }, r.number), csv: 'number' },
    { label: 'Member', render: r => h('a', { href: `#/admin/member/${r.uid}`, class: 'who' }, avatar(nm(r.uid), members.find(m => m.id === r.uid)?.photo, 26), h('b', null, r.memberName || nm(r.uid))), csv: r => r.memberName || nm(r.uid) },
    { label: 'For', render: r => KIND[r.kind] || r.kind, csv: 'kind' },
    { label: 'Period', render: r => r.periodStart ? `${fmtDate(r.periodStart)} – ${fmtDate(r.periodEnd)}` : '—', csv: r => r.periodStart ? fmtDate(r.periodStart) : '' },
    { label: 'Total', render: r => money(r.total), align: 'right', csv: 'total' },
    { label: 'Status', render: r => badge(r.status === 'paid' ? 'paid' : r.status === 'pending' ? 'pending' : 'failed', r.status), csv: 'status' },
    { label: 'Paid', render: r => r.paidAt ? fmtDate(r.paidAt) : '—', csv: r => r.paidAt?.toDate?.().toISOString().slice(0, 10) || '' },
    { label: 'Method', render: r => r.paymentMethod?.last4 ? `ACH •••• ${r.paymentMethod.last4}` : 'ACH', csv: r => r.paymentMethod?.last4 || '' },
    { label: '', render: r => btn('Open', () => openInvoice(r, nm(r.uid)), { size: 'btn-sm' }) },
  ];
  const draw = () => { const f = rows.filter(r => (!st || r.status === st) && (!q || `${r.number} ${r.memberName} ${nm(r.uid)} ${KIND[r.kind] || ''}`.toLowerCase().includes(q.toLowerCase()))); body.replaceChildren(card(table(cols, f.slice(0, 500), { empty: 'No invoices yet. One is created for every membership debit, Jovi Pass purchase, and pet add-on.' }))); };
  wrap.append(pageHeader('Invoices & receipts', 'Every charge issued through BILL, mirrored to the member’s app. Print or resend from here.', [btn('Export CSV', () => downloadCsv('jovi-invoices.csv', cols, rows))]),
    h('div', { class: 'grid grid-4 mb' }, stat('Collected', money(sum(paid, 'amountPaid'), { cents: false }), `${paid.length} paid receipts`, 'good'), stat('Last 30 days', money(sum(paid.filter(r => (r.paidAt?.toMillis?.() || 0) > Date.now() - 30 * 86400000), 'amountPaid'), { cents: false }), 'paid'), stat('Open', open.length, `${money(sum(open, 'total'), { cents: false })} pending, failed, or returned`, open.length ? 'warn' : ''), stat('Receipts', rows.length, 'all time')),
    h('div', { class: 'toolbar' }, searchBox('Number, member…', v => { q = v; draw(); }), select([['', 'All statuses'], 'paid', 'pending', 'failed', 'returned', 'void'], '', { onChange: e => { st = e.target.value; draw(); } })), body);
  draw();
  return wrap;
}

export function openInvoice(r, memberLabel) {
  const c = r.company || {};
  const html = `<!doctype html><html><head><title>${r.number}</title><style>
    body{font-family:Inter,system-ui,sans-serif;color:#131B2E;margin:0;padding:48px;max-width:760px}
    .top{display:flex;justify-content:space-between;align-items:flex-start} .logo{font-size:30px;font-weight:800;color:#1A2744;letter-spacing:-1px} .muted{color:#6B7590;font-size:12px}
    .tag{font-size:18px;font-weight:800;color:#FF6B4A;text-align:right} h4{margin:28px 0 4px;font-size:10px;letter-spacing:.14em;color:#6B7590;text-transform:uppercase}
    table{width:100%;border-collapse:collapse;margin-top:18px} th{text-align:left;font-size:10px;letter-spacing:.12em;color:#6B7590;text-transform:uppercase;border-bottom:1px solid #ccc;padding:6px 0} td{padding:8px 0;font-size:13px;border-bottom:1px solid #eee} td:last-child,th:last-child{text-align:right}
    .tot td{border:0;font-weight:700;font-size:15px} .foot{margin-top:40px;color:#6B7590;font-size:11px} .status{display:inline-block;padding:3px 10px;border-radius:999px;font-weight:700;font-size:11px;background:${r.status === 'paid' ? '#DDF6EF;color:#0B7A62' : r.status === 'pending' ? '#FFF4D6;color:#8A5D00' : '#FBE4E4;color:#A12C2C'}}
    @media print{body{padding:24px}}</style></head><body>
    <div class="top"><div><div class="logo">jovi</div><div class="muted">${c.name || 'Jovi Health LLC'}<br>${c.site || 'jovihealth.com'}<br>${c.phone || ''}</div></div>
    <div><div class="tag">${r.status === 'paid' ? 'RECEIPT' : 'INVOICE'}</div><div class="muted" style="text-align:right">${r.number}<br>Issued ${fmtDate(r.issuedAt)}${r.paidAt ? '<br>Paid ' + fmtDate(r.paidAt) : ''}</div></div></div>
    <h4>Billed to</h4><div><b>${r.memberName || memberLabel}</b><br>${r.memberEmail || ''}<br>${r.memberAddress || ''}</div>
    <table><tr><th>Description</th><th>Amount</th></tr>${(r.items || []).map(i => `<tr><td>${i.description}</td><td>${money(i.price)}</td></tr>`).join('')}${r.periodStart ? `<tr><td class="muted" colspan="2">Service period ${fmtDate(r.periodStart)} to ${fmtDate(r.periodEnd)}</td></tr>` : ''}
    <tr class="tot"><td>Total</td><td>${money(r.total)}</td></tr><tr><td>Amount paid</td><td>${money(r.amountPaid || 0)}</td></tr><tr><td>Balance</td><td>${money((r.total || 0) - (r.amountPaid || 0))}</td></tr></table>
    <p style="margin-top:18px;font-size:13px">Payment method: Bank account (ACH)${r.paymentMethod?.last4 ? ' ending in ' + r.paymentMethod.last4 : ''} &nbsp; <span class="status">${r.status}</span>${r.reason && r.status !== 'paid' ? '<br><span class="muted">' + r.reason + '</span>' : ''}</p>
    <div class="foot">${c.note || 'Jovi is a healthcare membership, not insurance.'}<br>Questions? ${c.email || 'support@jovihealth.com'} · ${c.phone || ''}<br>BILL invoice ${r.billInvoiceId || '—'}${r.billPaymentId ? ' · payment ' + r.billPaymentId : ''}</div></body></html>`;
  drawer(`${r.number} · ${money(r.total)}`, h('div', { class: 'col' },
    h('div', { class: 'row' }, badge(r.status === 'paid' ? 'paid' : r.status === 'pending' ? 'pending' : 'failed', r.status), h('span', { class: 'muted' }, KIND[r.kind] || r.kind)),
    card(kv('Member', h('a', { href: `#/admin/member/${r.uid}`, class: 'lnk' }, r.memberName || memberLabel)), kv('Issued', fmtDateTime(r.issuedAt)), kv('Paid', r.paidAt ? fmtDateTime(r.paidAt) : '—'), kv('Period', r.periodStart ? `${fmtDate(r.periodStart)} – ${fmtDate(r.periodEnd)}` : '—'), kv('Method', r.paymentMethod?.last4 ? `ACH •••• ${r.paymentMethod.last4}` : 'ACH'), kv('BILL invoice', h('span', { class: 'mono' }, r.billInvoiceId || '—')), kv('BILL payment', h('span', { class: 'mono' }, r.billPaymentId || '—')), r.reason ? kv('Note', r.reason) : null),
    card(cardHead('Line items'), table([{ label: 'Description', key: 'description' }, { label: 'Amount', render: i => money(i.price), align: 'right' }], r.items || []), h('div', { class: 'kv' }, h('span', { class: 'k' }, 'Total'), h('b', { class: 'v' }, money(r.total)))),
    h('div', { class: 'row' }, btn('Print / save PDF', () => { const w = window.open('', '_blank', 'width=820,height=980'); if (!w) return; w.document.write(html + '<script>setTimeout(function(){print()},300)</script>'); w.document.close(); }, { variant: 'btn-primary' }),
      can('writeBusiness') ? btn('Resend to app', async () => { try { await notifyMember(r.uid, { type: 'payment', title: `${r.status === 'paid' ? 'Receipt' : 'Invoice'} ${r.number}`, body: `${money(r.total)} · ${KIND[r.kind] || r.kind}. Open Invoices & receipts to view, share, or print.`, route: 'invoices' }); toast('Sent to the member’s inbox', 'success'); } catch (e) { errorToast(e); } }) : null)));
}
