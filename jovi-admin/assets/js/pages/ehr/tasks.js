import { h, pageHeader, card, cardHead, table, badge, btn, tabs, fmtDate, fmtDateTime, ago, toast, errorToast, input, select, textarea, field, modal, avatar, checkbox } from '../../ui.js';
import { tasks, addTask, updateTask, findMembers, cachedMembers } from '../../data.js';
import { session } from '../../auth.js';
import { navigate } from '../../router.js';
import { db, collection, getDocs, query, orderBy } from '../../firebase.js';

export async function render() {
  const wrap = h('div'); const body = h('div'); let tab = 'mine';
  const staffSnap = await getDocs(query(collection(db, 'staff'), orderBy('name'))).catch(() => ({ docs: [] })); const staff = staffSnap.docs.map(d => ({ id: d.id, ...d.data() })).filter(s => s.active !== false);
  const TABS = [['mine', 'My tasks'], ['all', 'All open'], ['done', 'Completed']];
  const prio = p => badge(p === 'urgent' ? 'failed' : p === 'high' ? 'pending' : 'info', p || 'normal');
  async function draw() {
    body.replaceChildren(tabs(TABS, tab, t => { tab = t; draw(); }), h('div', { class: 'spinner-wrap' }, h('span', { class: 'spinner' })));
    const rows = await tasks(tab === 'mine' ? { mine: true } : tab === 'done' ? { status: 'done' } : {});
    body.replaceChildren(tabs(TABS, tab, t => { tab = t; draw(); }), card(table([
      { label: 'Due', render: t => { const d = t.due?.toDate?.(); return h('span', { class: d && d < new Date() && t.status === 'open' ? 'danger' : '' }, d ? fmtDate(d) : '—'); } },
      { label: 'Task', render: t => h('div', null, h('b', null, t.title), t.notes ? h('div', { class: 'small muted' }, t.notes) : null) },
      { label: 'Patient', render: t => t.patientUid ? h('a', { href: `#/ehr/chart/${t.patientUid}`, class: 'lnk' }, t.patientName || 'Chart') : '—' },
      { label: 'Priority', render: t => prio(t.priority) }, { label: 'Assigned', render: t => t.assignedToName || h('span', { class: 'muted' }, 'Unassigned') }, { label: 'Created', render: t => `${t.createdByName || ''} · ${ago(t.createdAt)}` },
      { label: '', render: t => h('div', { class: 'row' }, t.status === 'open' ? btn('Done', async () => { await updateTask(t.id, { status: 'done', doneAt: new Date(), doneBy: session.user.uid }); toast('Completed', 'success'); draw(); }, { size: 'btn-sm', variant: 'btn-success' }) : btn('Reopen', async () => { await updateTask(t.id, { status: 'open' }); draw(); }, { size: 'btn-sm' }), btn('Edit', () => form(t), { size: 'btn-sm' })) },
    ], rows, { empty: tab === 'mine' ? 'Nothing assigned to you' : 'No tasks' })));
  }
  function form(t) {
    const f = { title: input({ value: t?.title || '', placeholder: 'e.g. Call about lab results' }), notes: textarea({ value: t?.notes || '', rows: 3 }), due: input({ type: 'date', value: t?.due?.toDate ? t.due.toDate().toISOString().slice(0, 10) : '' }), prio: select(['normal', 'high', 'urgent'], t?.priority || 'normal'), who: select([['', 'Unassigned'], ...staff.map(s => [s.id, `${s.name} (${s.role})`])], t?.assignedTo || session.user.uid), patient: input({ value: t?.patientName || '', placeholder: 'Search patient…' }) };
    let patientUid = t?.patientUid || null; const res = h('div', { class: 'list' }); let tm;
    f.patient.addEventListener('input', () => { clearTimeout(tm); tm = setTimeout(async () => { const rows = await findMembers(f.patient.value.trim(), 5); res.replaceChildren(...rows.map(m => h('div', { class: 'list-item', style: { cursor: 'pointer' }, onClick: () => { patientUid = m.id; f.patient.value = m.name; res.replaceChildren(); } }, avatar(m.name, m.photo, 24), h('b', null, m.name)))); }, 200); });
    const m = modal(t ? 'Edit task' : 'New task', h('div', { class: 'col' }, field('Task', f.title), field('Patient (optional)', f.patient), res, h('div', { class: 'form-grid' }, field('Due', f.due), field('Priority', f.prio), field('Assign to', f.who)), field('Notes', f.notes)), [btn('Cancel', () => m.close()), btn('Save', async () => {
      if (!f.title.value.trim()) return; const who = staff.find(s => s.id === f.who.value);
      const data = { title: f.title.value.trim(), notes: f.notes.value.trim(), due: f.due.value ? new Date(f.due.value + 'T09:00:00') : null, priority: f.prio.value, assignedTo: f.who.value || null, assignedToName: who?.name || null, patientUid, patientName: patientUid ? f.patient.value : null };
      try { if (t) await updateTask(t.id, data); else await addTask(data); toast('Saved', 'success'); m.close(); draw(); } catch (e) { errorToast(e); }
    }, { variant: 'btn-primary' })]);
  }
  wrap.append(pageHeader('Tasks', 'Follow-ups, callbacks, and to-dos for the care team.', [btn('New task', () => form(null), { variant: 'btn-primary' })]), body);
  await draw();
  return wrap;
}
export async function quickTask(patientUid, patientName, title = '') {
  const { input, textarea, field, modal, btn, toast, errorToast } = await import('../../ui.js');
  const t = input({ value: title, placeholder: 'Task' }); const due = input({ type: 'date' }); const notes = textarea({ rows: 2 });
  const m = modal(`Task for ${patientName}`, h('div', { class: 'col' }, field('Task', t), field('Due', due), field('Notes', notes)), [btn('Cancel', () => m.close()), btn('Create', async () => { if (!t.value.trim()) return; try { await addTask({ title: t.value.trim(), notes: notes.value.trim(), due: due.value ? new Date(due.value + 'T09:00:00') : null, assignedTo: session.user.uid, assignedToName: session.staff?.name || session.user.email, patientUid, patientName }); toast('Task created', 'success'); m.close(); } catch (e) { errorToast(e); } }, { variant: 'btn-primary' })]);
}
