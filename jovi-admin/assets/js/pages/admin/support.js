import { h, pageHeader, card, cardHead, table, badge, fmtDateTime, ago, btn, avatar, tabs, textarea, select, toast, errorToast, confirm, clear } from '../../ui.js';
import { tickets, watchMessages, sendMessage, updateTicket, markTicketRead, cachedMembers, getMember, memberName } from '../../data.js';
import { session, can } from '../../auth.js';
import { navigate } from '../../router.js';
import { db, doc, getDoc } from '../../firebase.js';

// Support inbox: shared by the business and clinical sides (registered under both).
export async function render(ctx) {
  const wrap = h('div'); const listEl = h('div'); const chatEl = h('div');
  let status = 'open', selected = ctx.param || null, unsub = null;
  ctx.setTeardown(() => unsub && unsub());
  const members = await cachedMembers().catch(() => []);
  const prio = t => t.priority === 0 ? badge('failed', 'Critical') : t.priority === 1 ? badge('pending', 'High') : t.priority === 2 ? badge('info', 'Medium') : badge('info', 'Low');
  async function loadList() {
    const rows = await tickets(status);
    listEl.replaceChildren(table([
      { label: 'Member', render: t => h('div', { class: 'who' }, avatar(t.userName, members.find(m => m.id === t.userId)?.photo, 28), h('div', null, h('b', null, t.userName || '—'), h('span', null, t.issueType || ''))) },
      { label: 'Priority', render: prio }, { label: 'Via', key: 'contactMethod' }, { label: 'Opened', render: t => ago(t.createdAt) }, { label: 'Assigned', render: t => t.assignedTo ? (t.assignedTo === session.user.uid ? 'You' : t.assignedToName || 'Staff') : h('span', { class: 'muted' }, 'Unassigned') },
    ], rows, { onRow: t => open(t.id), rowClass: t => (t.id === selected ? 'urgent' : ''), empty: `No ${status} tickets` }));
  }
  async function open(id) {
    selected = id; if (unsub) unsub();
    const snap = await getDoc(doc(db, 'helpTickets', id)); if (!snap.exists()) return; const t = { id, ...snap.data() };
    const msgs = h('div', { class: 'col', style: { maxHeight: '52vh', overflow: 'auto', padding: '4px' } });
    const ta = textarea({ placeholder: 'Reply to the member… (they get a push and an inbox item)', rows: 3 });
    const send = btn('Send reply', async () => { const text = ta.value.trim(); if (!text) return; try { await sendMessage(id, text); ta.value = ''; if (!t.assignedTo) await updateTicket(id, { assignedTo: session.user.uid, assignedToName: session.staff?.name || session.user.email, assignedAt: new Date() }); } catch (e) { errorToast(e); } }, { variant: 'btn-primary' });
    const closeBtn = btn(t.status === 'open' ? 'Close ticket' : 'Reopen', async () => { if (t.status === 'open' && !(await confirm('Close this ticket?', 'The member can still open a new one from the app.'))) return; await updateTicket(id, { status: t.status === 'open' ? 'closed' : 'open', closedAt: new Date(), closedBy: session.user.uid }); toast('Updated', 'success'); loadList(); open(id); });
    const assign = btn(t.assignedTo === session.user.uid ? 'Assigned to you' : 'Assign to me', async () => { await updateTicket(id, { assignedTo: session.user.uid, assignedToName: session.staff?.name || session.user.email, assignedAt: new Date() }); toast('Assigned', 'success'); loadList(); open(id); }, { disabled: t.assignedTo === session.user.uid });
    chatEl.replaceChildren(card(
      h('div', { class: 'row between mb' }, h('div', null, h('h3', null, `${t.userName || 'Member'} · ${t.issueType || 'Ticket'}`), h('div', { class: 'muted small' }, `${t.contactMethod || ''} · opened ${fmtDateTime(t.createdAt)} · response target ${t.responseTime || '—'}`)), h('div', { class: 'row' }, prio(t), badge(t.status), t.hasKurvPass ? badge('active', 'Jovi Pass') : null)),
      t.issueDescription ? h('div', { class: 'callout mint mb' }, h('div', null, h('b', null, 'Member wrote: '), t.issueDescription)) : null,
      h('div', { class: 'row mb' }, btn('Member profile', () => navigate(`/admin/member/${t.userId}`), { size: 'btn-sm' }), can('viewPhi') ? btn('Open chart', () => navigate(`/ehr/chart/${t.userId}`), { size: 'btn-sm' }) : null, assign, closeBtn),
      msgs, h('div', { class: 'col mt' }, ta, h('div', { class: 'row', style: { justifyContent: 'flex-end' } }, send))));
    unsub = watchMessages(id, list => {
      clear(msgs); markTicketRead(id, list).catch(() => {});
      if (!list.length) msgs.append(h('p', { class: 'muted' }, 'No messages yet. Your first reply starts the conversation.'));
      for (const m of list) {
        const mine = m.senderId !== t.userId;
        msgs.append(h('div', { style: { alignSelf: mine ? 'flex-end' : 'flex-start', maxWidth: '78%', background: mine ? 'var(--navy)' : 'var(--line-2)', color: mine ? '#fff' : 'var(--ink)', padding: '9px 12px', borderRadius: '14px' } },
          m.text ? h('div', { style: { whiteSpace: 'pre-wrap' } }, m.text) : null, m.imageUrl ? h('a', { href: m.imageUrl, target: '_blank' }, h('img', { src: m.imageUrl, style: { maxWidth: '240px', borderRadius: '8px', marginTop: '6px' } })) : null, m.fileUrl ? h('a', { href: m.fileUrl, target: '_blank', style: { textDecoration: 'underline' } }, m.fileName || 'Attachment') : null,
          h('div', { class: 'small', style: { opacity: .7, marginTop: '3px' } }, `${mine ? (m.senderName || 'Jovi') : t.userName || 'Member'} · ${fmtDateTime(m.timestamp)}`)));
      }
      msgs.scrollTop = msgs.scrollHeight;
    });
    listEl.querySelectorAll('tr').forEach(tr => tr.classList.remove('urgent'));
  }
  wrap.append(pageHeader('Support inbox', 'Live chat with members. Replies trigger a push notification through the app\'s existing function.'),
    tabs([['open', 'Open'], ['closed', 'Closed']], status, s => { status = s; loadList(); }),
    h('div', { class: 'grid', style: { gridTemplateColumns: 'minmax(320px,1fr) minmax(360px,1.3fr)' } }, card(h('div', { class: 'card-head' }, h('h3', null, 'Tickets')), listEl), chatEl));
  await loadList();
  if (selected) open(selected); else chatEl.append(card(h('div', { class: 'empty' }, h('b', null, 'Pick a ticket'), h('span', null, 'Critical and high priority sort to the top.'))));
  return wrap;
}
