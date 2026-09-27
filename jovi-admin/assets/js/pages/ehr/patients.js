import { h, pageHeader, card, table, badge, searchBox, select, avatar, age, phone, sortBy, fmtDate } from '../../ui.js';
import { cachedMembers, parseDob, memberDob, patientNames } from '../../data.js';
import { navigate } from '../../router.js';

export async function render() {
  const wrap = h('div'); const body = h('div');
  const rows = await cachedMembers(); let q = '', st = '';
  const draw = () => {
    const f = sortBy(rows.filter(m => (!q || `${m.name} ${m.email} ${patientNames(m).join(' ')} ${m.phone || m.onboard_phone || ''}`.toLowerCase().includes(q.toLowerCase())) && (!st || m.state === st)), 'name');
    body.replaceChildren(card(h('p', { class: 'muted small mb' }, `${f.length} households · search matches dependents too`), table([
      { label: 'Patient', render: m => h('div', { class: 'who' }, avatar(m.name, m.photo, 32), h('div', null, h('b', null, m.name), h('span', null, `${m.email || ''}`))) },
      { label: 'Age / sex', render: m => { const a = age(parseDob(memberDob(m))); return `${a ?? '—'}${m.gender || m.onboard_gender ? ' · ' + (m.gender || m.onboard_gender) : ''}`; } },
      { label: 'Phone', render: m => phone(m.phone || m.onboard_phone || m.phone_number) },
      { label: 'Household', render: m => patientNames(m).length > 1 ? `${patientNames(m).length} people` : 'Individual' },
      { label: 'Pets', render: m => Number(m.numPets) || 0 },
      { label: 'State', key: 'state' },
      { label: 'Membership', render: m => badge(m.status) },
      { label: 'Last visit', render: m => m.lastVisitAt ? fmtDate(m.lastVisitAt) : '—' },
    ], f, { onRow: m => navigate(`/ehr/chart/${m.id}`), empty: 'No patients match' })));
  };
  wrap.append(pageHeader('Patients', 'One chart per membership, with dependents and pets inside it.'), h('div', { class: 'toolbar' }, searchBox('Name, dependent, email, phone…', v => { q = v; draw(); }), select([['', 'All states'], ...[...new Set(rows.map(m => m.state).filter(Boolean))].sort()], '', { onChange: e => { st = e.target.value; draw(); } })), body);
  draw();
  return wrap;
}
