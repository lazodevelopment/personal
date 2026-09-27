import { h, pageHeader, card, table, badge, fmtDateTime, searchBox, select, downloadCsv, btn } from '../../ui.js';
import { db, collection, getDocs, query, orderBy, limit } from '../../firebase.js';

export async function render() {
  const wrap = h('div');
  const body = h('div');
  let rows = [], q = '', action = '';
  const snap = await getDocs(query(collection(db, 'audit_logs'), orderBy('at', 'desc'), limit(500)));
  rows = snap.docs.map(d => ({ id: d.id, ...d.data() }));
  const actions = [...new Set(rows.map(r => r.action))].sort();
  const cols = [
    { label: 'When', render: r => fmtDateTime(r.at), csv: r => r.at?.toDate?.().toISOString() },
    { label: 'Staff', render: r => h('div', null, h('b', null, r.staffEmail || r.staffId), h('div', { class: 'muted small' }, r.role)), csv: r => r.staffEmail },
    { label: 'Action', render: r => badge(r.action?.includes('delete') || r.action?.includes('deny') ? 'denied' : r.action?.includes('create') || r.action?.includes('approve') ? 'approved' : 'info', r.action), csv: 'action' },
    { label: 'Target', render: r => h('span', { class: 'mono' }, r.target || '—'), csv: 'target' },
    { label: 'Details', render: r => h('span', { class: 'small muted' }, Object.entries(r.meta || {}).map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : v}`).join(' · ')), csv: r => JSON.stringify(r.meta || {}) },
  ];
  const draw = () => {
    const f = rows.filter(r => (!action || r.action === action) && (!q || JSON.stringify(r).toLowerCase().includes(q.toLowerCase())));
    body.replaceChildren(card(table(cols, f, { empty: 'No audit entries' })));
  };
  wrap.append(pageHeader('Audit log', 'Every staff action on member data. Business roles see the who and what, never the clinical content.', [btn('Export CSV', () => downloadCsv('jovi-audit.csv', cols, rows))]),
    h('div', { class: 'toolbar' }, searchBox('Search staff, target, details…', v => { q = v; draw(); }), select([['', 'All actions'], ...actions.map(a => [a, a])], '', { onChange: e => { action = e.target.value; draw(); } })),
    body);
  draw();
  return wrap;
}
