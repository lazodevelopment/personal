import { h, pageHeader, card, cardHead, stat, table, badge, btn, select, searchBox, toast, errorToast, downloadCsv, confirm } from '../../ui.js';
import { careGaps, notifyMember, addTask } from '../../data.js';
import { session } from '../../auth.js';
import { navigate } from '../../router.js';

const RULES = { annual_wellness: 'Annual wellness overdue', no_visit_12mo: 'No visit in 12 months', tobacco_counseling: 'Tobacco counseling', refill_overdue: 'Refill overdue', booster_due: 'Booster due', pet_booster: 'Pet booster due', claim_stalled: 'Claim stalled' };
export async function render() {
  const wrap = h('div'); const body = h('div'); let rule = '', q = '';
  wrap.append(pageHeader('Care gaps', 'Rules run across the whole membership. Close a gap with a message or a task.'), h('div', { class: 'spinner-wrap' }, h('span', { class: 'spinner' }), h('span', { class: 'muted' }, 'Evaluating rules…')));
  let gaps = []; try { gaps = await careGaps(); } catch (e) { errorToast(e); }
  const byRule = {}; for (const g of gaps) byRule[g.rule] = (byRule[g.rule] || 0) + 1;
  const cols = [
    { label: 'Severity', render: g => badge(g.severity === 'medium' ? 'pending' : g.severity === 'low' ? 'info' : 'active', g.severity), csv: 'severity' },
    { label: 'Gap', render: g => RULES[g.rule] || g.rule, csv: g => RULES[g.rule] || g.rule },
    { label: 'Patient', render: g => h('a', { href: `#/ehr/chart/${g.uid}`, class: 'lnk' }, g.name), csv: 'name' },
    { label: 'Detail', key: 'detail', csv: 'detail' }, { label: 'Suggested action', key: 'action', csv: 'action' },
    { label: '', render: g => h('div', { class: 'row' }, btn('Message', async () => { try { await notifyMember(g.uid, { type: 'system', title: 'A note from your Jovi care team', body: `${g.action}. Open the app to get started.`, route: g.route }); toast('Sent', 'success'); } catch (e) { errorToast(e); } }, { size: 'btn-sm' }), btn('Task', async () => { try { await addTask({ title: `${RULES[g.rule] || g.rule}: ${g.action}`, notes: g.detail, patientUid: g.uid, patientName: g.name, assignedTo: session.user.uid, assignedToName: session.staff?.name || '', priority: g.severity === 'medium' ? 'high' : 'normal' }); toast('Task created', 'success'); } catch (e) { errorToast(e); } }, { size: 'btn-sm' })) },
  ];
  const draw = () => { const f = gaps.filter(g => (!rule || g.rule === rule) && (!q || `${g.name} ${g.detail}`.toLowerCase().includes(q.toLowerCase()))); body.replaceChildren(card(table(cols, f, { empty: 'No open gaps. Nice.' }))); };
  wrap.replaceChildren(pageHeader('Care gaps', 'Rules run across the whole membership. Close a gap with a message or a task.', [btn('Export CSV', () => downloadCsv('jovi-care-gaps.csv', cols, gaps)), btn('Message all in view', async () => { const f = gaps.filter(g => (!rule || g.rule === rule)); if (!f.length) return; if (!(await confirm(`Message ${f.length} members?`, 'Each gets one in-app notification with the suggested action.'))) return; let n = 0; for (const g of f) { try { await notifyMember(g.uid, { type: 'system', title: 'A note from your Jovi care team', body: `${g.action}. Open the app to get started.`, route: g.route }); n++; } catch {} } toast(`Sent ${n}`, 'success'); }, { variant: 'btn-primary' })]),
    h('div', { class: 'grid grid-4 mb' }, Object.entries(byRule).sort((a, b) => b[1] - a[1]).slice(0, 4).map(([k, v]) => stat(RULES[k] || k, v, 'members', v ? 'warn' : ''))),
    h('div', { class: 'toolbar' }, searchBox('Patient or detail…', v => { q = v; draw(); }), select([['', 'All rules'], ...Object.entries(RULES).map(([k, l]) => [k, `${l} (${byRule[k] || 0})`])], '', { onChange: e => { rule = e.target.value; draw(); } })), body);
  draw();
  return wrap;
}
