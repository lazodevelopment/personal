// Orders & results: e-prescriptions (Surescripts) and lab orders (Labcorp / Quest) plus the results inbox.
import { h, pageHeader, card, cardHead, table, badge, btn, tabs, fmtDateTime, fmtDate, toast, errorToast, prompt, drawer, closeDrawer, kv, textarea, field, checkbox, modal } from '../../ui.js';
import { ordersQueue, transmitOrder, updateOrder, resultsInbox, reviewResult, cachedMembers } from '../../data.js';
import { can } from '../../auth.js';
import { navigate } from '../../router.js';

export async function render() {
  const wrap = h('div'); const body = h('div'); let tab = 'results';
  const members = await cachedMembers(); const nm = uid => members.find(m => m.id === uid)?.name || uid;
  const TABS = [['results', 'Results to review'], ['rx', 'Prescriptions'], ['lab', 'Lab orders'], ['done', 'History']];
  async function draw() {
    body.replaceChildren(tabs(TABS, tab, t => { tab = t; draw(); }), h('div', { class: 'spinner-wrap' }, h('span', { class: 'spinner' })));
    let content;
    if (tab === 'results') {
      let rows = []; try { rows = await resultsInbox(); } catch (e) { content = h('div', { class: 'callout' }, h('div', null, 'Needs a collection-group index on lab_results (reviewed). See the console for the link.')); }
      if (!content) content = card(table([
        { label: 'Resulted', render: r => fmtDateTime(r.resultedAt) }, { label: 'Patient', render: r => h('a', { href: `#/ehr/chart/${r.uid}/vitals`, class: 'lnk' }, nm(r.uid)) }, { label: 'Test', render: r => h('b', null, r.testName) }, { label: 'Result', render: r => `${r.value} ${r.unit || ''}` }, { label: 'Reference', key: 'referenceRange' }, { label: 'Flag', render: r => badge(r.flag === 'critical' ? 'failed' : r.flag === 'abnormal' ? 'pending' : 'active', r.flag || 'normal') }, { label: 'Source', render: r => r.vendor || r.source || 'manual' },
        { label: '', render: r => can('chart') ? btn('Review', () => { const note = textarea({ rows: 3, placeholder: 'Interpretation for the patient (optional)' }); const notify = checkbox('Notify the patient in the app', r.flag !== 'normal'); const m = modal(`Review ${r.testName}`, h('div', { class: 'col' }, kv('Result', `${r.value} ${r.unit || ''} · ${r.flag || 'normal'}`), field('Note', note), notify), [btn('Cancel', () => m.close()), btn('Mark reviewed', async () => { try { await reviewResult(r, { note: note.value.trim(), notify: notify.querySelector('input').checked }); toast('Reviewed', 'success'); m.close(); draw(); } catch (e) { errorToast(e); } }, { variant: 'btn-primary' })]); }, { size: 'btn-sm', variant: r.flag === 'critical' ? 'btn-danger' : 'btn-primary' }) : null },
      ], rows, { rowClass: r => r.flag === 'critical' ? 'urgent' : '', empty: 'No unreviewed results' }));
    } else {
      const statuses = tab === 'done' ? ['transmitted', 'acknowledged', 'resulted', 'cancelled', 'error'] : ['signed', 'queued', 'transmitted', 'error'];
      let rows = await ordersQueue(statuses); if (tab !== 'done') rows = rows.filter(o => o.kind === tab);
      content = card(tab !== 'done' ? h('div', { class: 'callout mint mb' }, h('div', null, h('b', null, tab === 'rx' ? 'Surescripts: ' : 'Labcorp / Quest: '), 'orders are signed here and transmitted by the transmitOrder function. Until vendor credentials are configured they stay queued with the prepared payload, and you can still print or phone them in.')) : null,
        table([
          { label: 'Signed', render: o => fmtDateTime(o.createdAt) }, { label: 'Patient', render: o => h('a', { href: `#/ehr/chart/${o.userId}`, class: 'lnk' }, o.patientName || nm(o.userId)) }, { label: 'Order', render: o => o.kind === 'rx' ? h('div', null, h('b', null, `${o.medication?.medicationName || ''} ${o.medication?.dosage || ''}`), h('div', { class: 'small muted' }, `${o.medication?.instructions || ''} · qty ${o.medication?.quantity || '—'} · ${o.medication?.refills ?? 0} refills · ${o.pharmacy?.name || 'pharmacy on file'}`)) : h('div', null, h('b', null, (o.tests || []).join(', ')), h('div', { class: 'small muted' }, `${o.vendor} · ${o.priority || 'routine'}${o.diagnoses?.length ? ' · ' + o.diagnoses.join(', ') : ''}`)) }, { label: 'Provider', key: 'orderedByName' }, { label: 'Status', render: o => h('div', null, badge(o.status === 'queued' ? 'pending' : o.status === 'error' ? 'failed' : o.status), o.lastMessage ? h('div', { class: 'small muted' }, o.lastMessage) : null) },
          { label: '', render: o => can('chart') ? h('div', { class: 'row' }, ['signed', 'queued', 'error'].includes(o.status) ? btn('Transmit', async () => { try { const r = await transmitOrder(o.id); toast(r.ok ? 'Transmitted' : `Queued: ${r.message || r.error || ''}`, r.ok ? 'success' : 'info', 6000); draw(); } catch (e) { errorToast(e); } }, { size: 'btn-sm', variant: 'btn-primary' }) : null, o.kind === 'lab' && o.status === 'transmitted' ? btn('Collected', () => updateOrder(o.id, { status: 'collected', collectedAt: new Date() }).then(draw), { size: 'btn-sm' }) : null, !['cancelled', 'resulted'].includes(o.status) ? btn('Cancel', async () => { const why = await prompt('Cancel order', 'Reason'); if (why == null) return; await updateOrder(o.id, { status: 'cancelled', cancelReason: why }); draw(); }, { size: 'btn-sm', variant: 'btn-ghost' }) : null, btn('Print', () => printOrder(o, nm), { size: 'btn-sm', variant: 'btn-ghost' })) : null },
        ], rows, { empty: 'No orders' }));
    }
    body.replaceChildren(tabs(TABS, tab, t => { tab = t; draw(); }), content);
  }
  wrap.append(pageHeader('Orders & results', 'E-prescriptions, lab orders, and incoming results. Every result must be reviewed by a provider.'), body);
  await draw();
  return wrap;
}
function printOrder(o, nm) {
  const w = window.open('', '_blank', 'width=720,height=900'); if (!w) return;
  const lines = o.kind === 'rx' ? [`Medication: ${o.medication?.medicationName} ${o.medication?.dosage || ''}`, `Sig: ${o.medication?.instructions || ''}`, `Quantity: ${o.medication?.quantity || ''}   Refills: ${o.medication?.refills ?? 0}   Days supply: ${o.medication?.daysSupply || ''}`, `Substitution permitted: ${o.medication?.substitutionsAllowed === false ? 'No' : 'Yes'}`, `Pharmacy: ${o.pharmacy?.name || 'on file'} ${o.pharmacy?.phone || ''}`] : [`Tests: ${(o.tests || []).join(', ')}`, `Diagnoses: ${(o.diagnoses || []).join(', ') || '—'}`, `Priority: ${o.priority || 'routine'}`, `Lab: ${o.vendor}`];
  w.document.write(`<html><head><title>Jovi order</title><style>body{font-family:Inter,system-ui;padding:40px;color:#131B2E}h1{font-size:20px}p{margin:6px 0}.sig{margin-top:60px;border-top:1px solid #999;width:280px;padding-top:6px;font-size:12px}</style></head><body><h1>Jovi · ${o.kind === 'rx' ? 'Prescription' : 'Laboratory order'}</h1><p><b>Patient:</b> ${o.patientName || nm(o.userId)} &nbsp; <b>DOB:</b> ${o.patient?.dob || '—'}</p><p><b>Date:</b> ${new Date().toLocaleDateString()}</p><hr>${lines.map(l => `<p>${l}</p>`).join('')}<p><b>Notes:</b> ${o.notes || '—'}</p><div class="sig">${o.orderedByName || ''}${o.orderedByNpi ? ' · NPI ' + o.orderedByNpi : ''}<br>Electronically signed ${new Date(o.createdAt?.toDate?.() || Date.now()).toLocaleString()}</div><script>print()</script></body></html>`);
  w.document.close();
}
