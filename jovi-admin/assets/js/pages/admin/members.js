import { h, pageHeader, card, table, badge, money, fmtDate, searchBox, select, downloadCsv, btn, avatar, sortBy } from '../../ui.js';
import { cachedMembers, nextBilling } from '../../data.js';
import { navigate } from '../../router.js';

export async function render() {
  const wrap = h('div'); const body = h('div');
  let rows = await cachedMembers(); let q = '', status = '', plan = '', state = '', sort = 'name';
  const states = [...new Set(rows.map(m => m.state).filter(Boolean))].sort();
  const cols = [
    { label: 'Member', render: m => h('div', { class: 'who' }, avatar(m.name, m.photo, 30), h('div', null, h('b', null, m.name), h('span', null, m.email || ''))), csv: 'name' },
    { label: 'Email', key: 'email', csv: 'email', render: () => null },
    { label: 'Status', render: m => badge(m.status), csv: 'status' },
    { label: 'Plan', render: m => `${m.planType || m.planTier || 'Individual'}${m.hasDental || m.dental ? ' · Dental' : ''}${m.hasVision || m.vision ? ' · Vision' : ''}`, csv: m => m.planType || m.planTier || '' },
    { label: 'Household', render: m => `${1 + (m.hasSpouse || m.spouse ? 1 : 0) + (Number(m.numDependents ?? m.numDeps) || 0)} people · ${Number(m.numPets) || 0} pets`, csv: m => Number(m.numPets) || 0 },
    { label: 'State', key: 'state', csv: 'state' },
    { label: 'Monthly', render: m => money(m.monthly), align: 'right', csv: 'monthly' },
    { label: 'Next bill', render: m => fmtDate(nextBilling(m)), csv: m => nextBilling(m)?.toISOString().slice(0, 10) || '' },
    { label: 'Joined', render: m => fmtDate(m.created_time || m.membershipStartDate), csv: m => (m.created_time?.toDate?.() || '').toString() },
  ];
  cols.splice(1, 1); // email is inside the member cell; keep csv via name/email columns below
  const draw = () => {
    let f = rows.filter(m => (!q || `${m.name} ${m.email} ${m.phone || ''} ${m.onboard_phone || ''}`.toLowerCase().includes(q.toLowerCase())) && (!status || m.status === status) && (!plan || (m.planType || m.planTier || 'Individual') === plan) && (!state || m.state === state));
    f = sort === 'name' ? sortBy(f, 'name') : sort === 'monthly' ? sortBy(f, 'monthly', true) : sort === 'joined' ? sortBy(f, m => m.created_time?.toMillis?.() || 0, true) : f;
    body.replaceChildren(card(h('p', { class: 'muted small mb' }, `${f.length} of ${rows.length} members`), table(cols, f, { onRow: m => navigate(`/admin/member/${m.id}`), empty: 'No members match' })));
  };
  wrap.append(pageHeader('Members', 'Membership, plan, and billing standing. Clinical detail lives on the clinical side.', [btn('Export CSV', () => downloadCsv('jovi-members.csv', [{ label: 'Name', csv: 'name' }, { label: 'Email', csv: 'email' }, ...cols.slice(1)], rows))]),
    h('div', { class: 'toolbar' },
      searchBox('Name, email, phone…', v => { q = v; draw(); }),
      select([['', 'All statuses'], 'active', 'canceling', 'canceled', 'past_due', 'suspended', 'inactive'], '', { onChange: e => { status = e.target.value; draw(); } }),
      select([['', 'All plans'], 'Individual', 'Family'], '', { onChange: e => { plan = e.target.value; draw(); } }),
      select([['', 'All states'], ...states], '', { onChange: e => { state = e.target.value; draw(); } }),
      select([['name', 'Sort: name'], ['monthly', 'Sort: monthly'], ['joined', 'Sort: newest']], 'name', { onChange: e => { sort = e.target.value; draw(); } })),
    body);
  draw();
  return wrap;
}
