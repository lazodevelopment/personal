import { h, pageHeader, card, table, badge, fmtDateTime, searchBox } from '../../ui.js';
import { recentVisitRecords, cachedMembers } from '../../data.js';
import { navigate } from '../../router.js';

export async function render() {
  const wrap = h('div'); const body = h('div'); let q = '';
  const members = await cachedMembers(); const nm = uid => members.find(m => m.id === uid)?.name || uid;
  let rows = []; try { rows = await recentVisitRecords(300); } catch (e) { wrap.append(pageHeader('Care records'), h('div', { class: 'callout' }, h('div', null, 'Needs a collection-group index on visit_records (visitDate desc). See the console for the link.'))); return wrap; }
  const draw = () => { const f = rows.filter(r => !q || `${r.patientName} ${nm(r.uid)} ${r.chiefComplaint} ${r.providerName} ${(r.diagnoses || []).map(d => d.label).join(' ')}`.toLowerCase().includes(q.toLowerCase())); body.replaceChildren(card(table([
    { label: 'Visit', render: r => fmtDateTime(r.visitDate) }, { label: 'Patient', render: r => h('div', null, h('b', null, r.patientName || nm(r.uid)), h('div', { class: 'small muted' }, nm(r.uid))) }, { label: 'Type', key: 'type' }, { label: 'Chief complaint', render: r => r.chiefComplaint || '—' }, { label: 'Diagnoses', render: r => (r.diagnoses || []).map(d => d.label).join(', ') || '—' }, { label: 'Provider', key: 'providerName' }, { label: 'Signed', render: r => r.signedAt ? badge('active', 'Signed') : badge('pending', 'Draft') },
  ], f, { onRow: r => navigate(`/ehr/chart/${r.uid}/note/${r.id}`), empty: 'No encounters yet' }))); };
  wrap.append(pageHeader('Care records', 'All encounter notes written in this app, newest first. Members see signed notes in Care Records.'), h('div', { class: 'toolbar' }, searchBox('Patient, complaint, diagnosis, provider…', v => { q = v; draw(); })), body);
  draw();
  return wrap;
}
