import { h, pageHeader, card, cardHead, stat, table, badge, fmtDateTime, sum, groupBy, select, downloadCsv, btn, money } from '../../ui.js';
import { allRequests, cancelledAppointments, CLINICS, monthKey, lastMonths, JOVI_PASS_PRICE } from '../../data.js';
import { navigate } from '../../router.js';
import { canSide } from '../../auth.js';

// Operations view: volume, utilization, no-shows. Symptoms and details stay on the clinical side.
export async function render() {
  const wrap = h('div');
  const [reqs, cancels] = await Promise.all([allRequests(3000), cancelledAppointments(500).catch(() => [])]);
  const now = new Date(); const d30 = new Date(Date.now() - 30 * 86400000);
  const last30 = reqs.filter(r => r.start && r.start >= d30 && r.start <= now);
  const upcoming = reqs.filter(r => r.start && r.start > now && ['pending', 'confirmed', 'rescheduled'].includes(r.statusL));
  const completed = last30.filter(r => r.statusL === 'completed'); const noShow = last30.filter(r => ['no_show', 'missed'].includes(r.statusL));
  const months = lastMonths(6); const byM = groupBy(reqs, r => monthKey(r.start) || 'unknown'); const maxM = Math.max(1, ...months.map(m => (byM[m.key] || []).length));
  const bars = h('div', { class: 'bars-wrap' }, h('div', { class: 'bars' }, months.map(m => h('div', { class: 'bar', style: { height: `${Math.max(3, (byM[m.key] || []).length / maxM * 100)}%` }, title: `${(byM[m.key] || []).length} visits` }, h('span', null, m.label)))));
  const clinicRows = [...CLINICS.map(c => c.key), 'Virtual'].map(k => { const rows = reqs.filter(r => (k === 'Virtual' ? r.visitMode === 'Virtual' : r.clinic === k)); return { clinic: k, total: rows.length, upcoming: rows.filter(r => upcoming.includes(r)).length, completed: rows.filter(r => r.statusL === 'completed').length, noShow: rows.filter(r => ['no_show', 'missed'].includes(r.statusL)).length, pet: rows.filter(r => r.isPet).length, pass: rows.filter(r => r.priority).length }; });
  let filt = ''; const body = h('div');
  const cols = [{ label: 'When', render: r => r.start ? fmtDateTime(r.start) : '—', csv: r => r.start?.toISOString() || '' }, { label: 'Type', render: r => `${r.isPet ? 'Pet · ' : ''}${r.visitType || ''}`, csv: 'visitType' }, { label: 'Mode', key: 'visitMode', csv: 'visitMode' }, { label: 'Clinic', key: 'clinic', csv: 'clinic' }, { label: 'Status', render: r => badge(r.statusL), csv: 'status' }, { label: 'Jovi Pass', render: r => r.priority ? badge('active', money(JOVI_PASS_PRICE, { cents: false })) : '—', csv: r => r.priority ? 'yes' : '' }, { label: 'Wait est.', key: 'estimatedWaitTime', csv: 'estimatedWaitTime' }];
  const draw = () => { const f = (filt === 'upcoming' ? upcoming : filt === 'last30' ? last30 : reqs).sort((a, b) => (b.start?.getTime() || 0) - (a.start?.getTime() || 0)); body.replaceChildren(table(cols, f.slice(0, 400), { empty: 'No appointments' })); };
  wrap.append(pageHeader('Appointment volume', 'Bookings, utilization, and no-shows by clinic. Patient names and reasons are on the clinical schedule.', [canSide('ehr') ? btn('Clinical schedule', () => navigate('/ehr/schedule'), { variant: 'btn-primary' }) : null, btn('Export CSV', () => downloadCsv('jovi-appointments.csv', cols, reqs))].filter(Boolean)),
    h('div', { class: 'grid grid-4 mb' }, stat('Upcoming', upcoming.length, `${upcoming.filter(r => r.statusL === 'pending').length} unconfirmed`), stat('Visits, last 30 days', last30.length, `${completed.length} completed`, 'good'), stat('No-show rate', `${Math.round(noShow.length / Math.max(1, last30.length) * 100)}%`, `${noShow.length} no-shows`, noShow.length ? 'warn' : ''), stat('Cancellations', cancels.length, `${cancels.filter(c => c.wasPriority).length} forfeited Jovi Pass`)),
    h('div', { class: 'grid grid-2 mb' }, card(cardHead('Visits by month'), bars), card(cardHead('By location'), table([{ label: 'Location', key: 'clinic' }, { label: 'Total', key: 'total' }, { label: 'Upcoming', key: 'upcoming' }, { label: 'Completed', key: 'completed' }, { label: 'No-show', key: 'noShow' }, { label: 'Pet', key: 'pet' }, { label: 'Pass', key: 'pass' }], clinicRows))),
    card(cardHead('Appointments', select([['', 'All'], ['upcoming', 'Upcoming'], ['last30', 'Last 30 days']], '', { onChange: e => { filt = e.target.value; draw(); } })), body));
  draw();
  return wrap;
}
