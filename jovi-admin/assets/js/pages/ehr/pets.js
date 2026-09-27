import { h, pageHeader, card, table, badge, searchBox, avatar, fmtDate } from '../../ui.js';
import { cachedMembers } from '../../data.js';
import { navigate } from '../../router.js';
import { db, collectionGroup, getDocs, query, limit } from '../../firebase.js';

export async function render() {
  const wrap = h('div'); const body = h('div'); let q = '';
  const members = await cachedMembers(); const nm = uid => members.find(m => m.id === uid)?.name || uid;
  let rows = []; try { const s = await getDocs(query(collectionGroup(db, 'pets'), limit(2000))); rows = s.docs.map(d => ({ id: d.id, uid: d.ref.path.split('/')[1], ...d.data() })); } catch (e) { wrap.append(pageHeader('Pets'), h('div', { class: 'callout' }, h('div', null, 'Needs a collection-group index on pets. See the console for the link.'))); return wrap; }
  const draw = () => { const f = rows.filter(p => !q || `${p.name} ${p.breed} ${p.type} ${nm(p.uid)}`.toLowerCase().includes(q.toLowerCase())).sort((a, b) => (a.name || '').localeCompare(b.name || '')); body.replaceChildren(card(h('p', { class: 'muted small mb' }, `${f.length} pets`), table([
    { label: 'Pet', render: p => h('div', { class: 'who' }, avatar(p.name, p.photoUrl, 32), h('div', null, h('b', null, p.name), h('span', null, `${p.type || ''} · ${p.breed || ''}`))) }, { label: 'Owner', render: p => h('a', { href: `#/ehr/chart/${p.uid}`, class: 'lnk' }, nm(p.uid)) }, { label: 'Sex', render: p => p.sex || p.gender || '—' }, { label: 'Born', render: p => p.dateOfBirth ? fmtDate(p.dateOfBirth) : p.birthdate || '—' }, { label: 'Weight', render: p => p.weightLbs ? `${p.weightLbs} lb` : '—' }, { label: 'Status', render: p => badge(p.archived ? 'suspended' : 'active', p.archived ? 'Archived' : 'Covered') },
  ], f, { onRow: p => navigate(`/ehr/pet/${p.uid}/${p.id}`), empty: 'No pets' }))); };
  wrap.append(pageHeader('Pets', 'Every pet on a Jovi plan.'), h('div', { class: 'toolbar' }, searchBox('Pet, breed, owner…', v => { q = v; draw(); })), body);
  draw();
  return wrap;
}
