import { h, pageHeader, card, cardHead, table, badge, btn, tabs, fmtDateTime, toast, errorToast, input, select, field, modal, avatar } from '../../ui.js';
import { faxOutbox, faxInbox, sendFax, attachFaxToChart, findMembers, cachedMembers, recentVisitRecords } from '../../data.js';
import { can } from '../../auth.js';

export async function render() {
  const wrap = h('div'); const body = h('div'); let tab = 'inbox';
  const members = await cachedMembers(); const nm = uid => members.find(m => m.id === uid)?.name || uid;
  const TABS = [['inbox', 'Inbox'], ['outbox', 'Sent']];
  async function draw() {
    body.replaceChildren(tabs(TABS, tab, t => { tab = t; draw(); }), h('div', { class: 'spinner-wrap' }, h('span', { class: 'spinner' })));
    let content;
    if (tab === 'inbox') {
      const rows = await faxInbox().catch(() => []);
      content = card(table([{ label: 'Received', render: f => fmtDateTime(f.receivedAt) }, { label: 'From', render: f => h('div', null, h('b', null, f.subject || f.from || 'Unknown'), h('div', { class: 'small muted' }, `${f.from || ''} · ${f.pages || '?'} pages`)) }, { label: 'Status', render: f => badge(f.status === 'filed' ? 'completed' : 'new', f.status === 'filed' ? `Filed · ${nm(f.attachedTo)}` : 'New') }, { label: 'File', render: f => f.fileUrl ? h('a', { href: f.fileUrl, target: '_blank', class: 'lnk' }, 'Open PDF') : '—' }, { label: '', render: f => f.status !== 'filed' && can('chart') ? btn('File to chart', () => fileFax(f, draw), { size: 'btn-sm', variant: 'btn-primary' }) : null }], rows, { empty: 'No inbound faxes. Point your fax vendor’s webhook at faxInboundWebhook to receive them here.' }));
    } else {
      const rows = await faxOutbox().catch(() => []);
      content = card(table([{ label: 'Sent', render: f => fmtDateTime(f.createdAt) }, { label: 'To', render: f => h('div', null, h('b', null, f.toName || f.to), h('div', { class: 'small muted' }, f.to)) }, { label: 'Subject', key: 'subject' }, { label: 'Patient', render: f => f.patientUid ? h('a', { href: `#/ehr/chart/${f.patientUid}`, class: 'lnk' }, f.patientName || nm(f.patientUid)) : '—' }, { label: 'By', key: 'createdByName' }, { label: 'Status', render: f => h('div', null, badge(f.status === 'sent' ? 'completed' : f.status === 'error' ? 'failed' : 'pending', f.status), f.lastError ? h('div', { class: 'small muted' }, f.lastError) : null) }, { label: 'File', render: f => h('a', { href: f.fileUrl, target: '_blank', class: 'lnk' }, f.fileName || 'file') }], rows, { empty: 'Nothing sent yet' }));
    }
    body.replaceChildren(tabs(TABS, tab, t => { tab = t; draw(); }), content);
  }
  wrap.append(pageHeader('Fax', 'Referrals and records still move by fax. Outbound goes through the fax vendor once it is configured; inbound faxes are filed to a chart.', can('chart') ? [btn('Send a fax', () => compose(draw), { variant: 'btn-primary' })] : []), body);
  await draw();
  return wrap;
}
async function fileFax(f, redraw) {
  const q = input({ placeholder: 'Search patient…' }); const res = h('div', { class: 'list' }); let uid = null; const cat = select([['referral', 'Referral'], ['lab', 'Lab report'], ['imaging', 'Imaging'], ['discharge', 'Discharge summary'], ['other', 'Outside records']], 'referral');
  let tm; q.addEventListener('input', () => { clearTimeout(tm); tm = setTimeout(async () => { const rows = await findMembers(q.value.trim(), 6); res.replaceChildren(...rows.map(m => h('div', { class: 'list-item', style: { cursor: 'pointer' }, onClick: () => { uid = m.id; q.value = m.name; res.replaceChildren(); } }, avatar(m.name, m.photo, 24), h('b', null, m.name)))); }, 200); });
  const m = modal('File fax to a chart', h('div', { class: 'col' }, field('Patient', q), res, field('Category', cat)), [btn('Cancel', () => m.close()), btn('File', async () => { if (!uid) return toast('Pick a patient', 'error'); try { await attachFaxToChart(f, uid, cat.value); toast('Filed', 'success'); m.close(); redraw(); } catch (e) { errorToast(e); } }, { variant: 'btn-primary' })]);
}
async function compose(redraw) {
  const to = input({ placeholder: 'Fax number, e.g. 3035551234' }); const toName = input({ placeholder: 'Recipient (clinic or provider)' }); const subject = input({ placeholder: 'Subject / cover note' }); const q = input({ placeholder: 'Patient (optional)' }); const res = h('div', { class: 'list' }); let uid = null, pname = null; const fileSel = select([['', 'Pick a document…']], ''); const upload = h('input', { type: 'file', accept: 'application/pdf,image/*' }); let uploadedUrl = null, uploadedName = null;
  let tm; q.addEventListener('input', () => { clearTimeout(tm); tm = setTimeout(async () => { const rows = await findMembers(q.value.trim(), 6); res.replaceChildren(...rows.map(mm => h('div', { class: 'list-item', style: { cursor: 'pointer' }, onClick: async () => { uid = mm.id; pname = mm.name; q.value = mm.name; res.replaceChildren(); const { visitRecords } = await import('../../data.js'); const notes = await visitRecords(uid).catch(() => []); const docs = notes.flatMap(n => (n.attachments || []).map(a => [a.url, `${a.name} (${new Date(n.visitDate?.toDate?.() || Date.now()).toLocaleDateString()})`])); fileSel.replaceChildren(h('option', { value: '' }, docs.length ? 'Pick a chart document…' : 'No chart documents; upload below'), ...docs.map(([v, l]) => h('option', { value: v }, l))); } }, avatar(mm.name, mm.photo, 24), h('b', null, mm.name)))); }, 200); });
  upload.addEventListener('change', async () => { const f = upload.files[0]; if (!f) return; try { const { uploadChartFile } = await import('../../data.js'); uploadedUrl = await uploadChartFile(uid || 'shared', f, 'fax'); uploadedName = f.name; toast('Uploaded', 'success'); } catch (e) { errorToast(e); } });
  const m = modal('Send a fax', h('div', { class: 'col' }, h('div', { class: 'form-grid' }, field('To number', to), field('Recipient', toName)), field('Subject', subject), field('Patient', q), res, field('Chart document', fileSel), field('Or upload a file', upload)), [btn('Cancel', () => m.close()), btn('Send', async () => { const url = uploadedUrl || fileSel.value; if (!to.value.trim() || !url) return toast('Number and a document are required', 'error'); try { await sendFax({ to: to.value.replace(/\D/g, ''), toName: toName.value.trim(), subject: subject.value.trim(), fileUrl: url, fileName: uploadedName || fileSel.selectedOptions[0]?.textContent || 'document', patientUid: uid, patientName: pname }); toast('Queued for sending', 'success'); m.close(); redraw(); } catch (e) { errorToast(e); } }, { variant: 'btn-primary' })]);
}
