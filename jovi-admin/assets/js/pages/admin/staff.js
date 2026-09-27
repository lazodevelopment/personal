import { h, pageHeader, card, table, badge, btn, field, input, select, checkbox, drawer, closeDrawer, toast, errorToast, fmtDateTime, ago, confirm, avatar } from '../../ui.js';
import { db, collection, getDocs, doc, setDoc, updateDoc, serverTimestamp, query, orderBy } from '../../firebase.js';
import { ROLES, session, audit } from '../../auth.js';

const ROLE_HELP = {
  superadmin: 'Everything, including staff and rules.',
  admin: 'Business side with write access. No clinical charts.',
  exec: 'Business side, read-only dashboards and reports.',
  clinician: 'Clinical workspace: charts, notes, orders, refills, claims review.',
  support: 'Support inbox, refill queue, member lookup. Limited chart view.',
};

export async function render(ctx) {
  const wrap = h('div');
  const list = h('div');
  wrap.append(pageHeader('Staff & roles', 'Who can sign in to this app and what they can see.', [btn('Add staff member', () => edit(null), { variant: 'btn-primary' })]), list);
  async function load() {
    const snap = await getDocs(query(collection(db, 'staff'), orderBy('name')));
    const rows = snap.docs.map(d => ({ id: d.id, ...d.data() }));
    list.replaceChildren(card(table([
      { label: 'Name', render: r => h('div', { class: 'who' }, avatar(r.name, null, 30), h('div', null, h('b', null, r.name || '—'), h('span', null, r.email || ''))) },
      { label: 'Role', render: r => badge(r.role === 'clinician' ? 'active' : r.role === 'exec' ? 'info' : 'pending', r.role) },
      { label: 'Title', key: 'title' },
      { label: 'NPI', key: 'npi' },
      { label: 'Status', render: r => badge(r.active === false ? 'suspended' : 'active') },
      { label: 'Last seen', render: r => r.lastSeenAt ? ago(r.lastSeenAt) : 'never' },
      { label: '', render: r => btn('Edit', () => edit(r), { size: 'btn-sm' }) },
    ], rows, { empty: 'No staff yet' })),
      h('p', { class: 'muted small mt' }, 'The Firestore document id must equal the person\'s Firebase Auth uid. Create their Auth account first (Firebase console → Authentication → Add user), then add them here with that uid.'));
  }
  function edit(r) {
    const isNew = !r;
    const f = {
      uid: input({ name: 'uid', value: r?.id || '', placeholder: 'Firebase Auth uid', disabled: !isNew }),
      name: input({ name: 'name', value: r?.name || '' }),
      email: input({ name: 'email', type: 'email', value: r?.email || '' }),
      role: select(ROLES.map(x => [x, x]), r?.role || 'clinician', { name: 'role' }),
      title: input({ name: 'title', value: r?.title || '', placeholder: 'e.g. Nurse Practitioner' }),
      npi: input({ name: 'npi', value: r?.npi || '', placeholder: 'Providers only' }),
      active: checkbox('Active (can sign in)', r ? r.active !== false : true, { name: 'active' }),
    };
    const help = h('p', { class: 'muted small' }, ROLE_HELP[f.role.value]);
    f.role.addEventListener('change', () => { help.textContent = ROLE_HELP[f.role.value]; });
    const save = btn('Save', async () => {
      const uid = f.uid.value.trim(); if (!uid) return toast('Auth uid is required', 'error');
      if (uid === session.user.uid && f.role.value !== 'superadmin') { if (!(await confirm('Change your own role?', 'You will lose superadmin access immediately.', { danger: true }))) return; }
      const data = { name: f.name.value.trim(), email: f.email.value.trim().toLowerCase(), role: f.role.value, title: f.title.value.trim(), npi: f.npi.value.trim(), active: f.active.querySelector('input').checked, updatedAt: serverTimestamp(), updatedBy: session.user.uid };
      try {
        if (isNew) await setDoc(doc(db, 'staff', uid), { ...data, createdAt: serverTimestamp(), createdBy: session.user.uid });
        else await updateDoc(doc(db, 'staff', uid), data);
        await audit(isNew ? 'staff.create' : 'staff.update', `staff/${uid}`, { role: data.role, active: data.active });
        toast('Saved', 'success'); closeDrawer(); load();
      } catch (e) { errorToast(e); }
    }, { variant: 'btn-primary' });
    drawer(isNew ? 'Add staff member' : `Edit ${r.name || r.id}`, h('div', { class: 'col' },
      field('Auth uid', f.uid, 'From Firebase console → Authentication'), field('Full name', f.name), field('Email', f.email),
      field('Role', f.role), help, field('Title', f.title), field('NPI', f.npi), f.active, h('div', { class: 'row', style: { justifyContent: 'flex-end' } }, btn('Cancel', closeDrawer), save)));
  }
  await load();
  return wrap;
}
