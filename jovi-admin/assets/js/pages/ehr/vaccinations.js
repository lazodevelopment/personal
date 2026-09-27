import { h, pageHeader, card, table, badge, select, fmtDate, btn } from '../../ui.js';
import { vaccinationsDue, cachedMembers } from '../../data.js';
import { navigate } from '../../router.js';

export async function render() {
  const wrap = h('div'); const body = h('div'); let days = 45;
  const members = await cachedMembers(); const nm = uid => members.find(m => m.id === uid)?.name || uid;
  async function draw() {
    body.replaceChildren(h('div', { class: 'spinner-wrap' }, h('span', { class: 'spinner' })));
    let rows = []; try { rows = await vaccinationsDue(days); } catch (e) { body.replaceChildren(h('div', { class: 'callout' }, h('div', null, 'This list needs two collection-group indexes on vaccinations (expiresAt and expirationDate). Open the console for the create-index links.'))); return; }
    body.replaceChildren(card(table([
      { label: 'Due', render: v => { const late = v.due && v.due < new Date(); return h('span', { class: late ? 'danger' : '' }, fmtDate(v.due), late ? ' · overdue' : ''); } },
      { label: 'Patient', render: v => h('div', null, h('b', null, v.kind === 'pet' ? `Pet of ${nm(v.uid)}` : (v.patientName || nm(v.uid))), h('div', { class: 'small muted' }, v.kind === 'pet' ? `${v.species || ''}` : 'Household: ' + nm(v.uid))) },
      { label: 'Vaccine', render: v => `${v.vaccineName}${v.doseLabel ? ' · ' + v.doseLabel : ''}${v.vaccineType ? ' · ' + v.vaccineType : ''}` },
      { label: 'Last given', render: v => fmtDate(v.administeredAt || v.administeredDate) }, { label: 'By', render: v => v.provider || v.administeredBy || v.clinicName || '—' },
      { label: '', render: v => btn('Open chart', () => navigate(v.kind === 'pet' ? `/ehr/pet/${v.uid}/${v.petId}` : `/ehr/chart/${v.uid}`), { size: 'btn-sm' }) },
    ], rows, { empty: 'No boosters due in this window' })));
  }
  wrap.append(pageHeader('Vaccinations due', 'Human and pet boosters expiring soon. The app already sends 30, 7, and 0 day reminders; this is the outreach list.'), h('div', { class: 'toolbar' }, select([[14, 'Next 14 days'], [45, 'Next 45 days'], [90, 'Next 90 days'], [365, 'Next year']], 45, { onChange: e => { days = Number(e.target.value); draw(); } })), body);
  await draw();
  return wrap;
}
