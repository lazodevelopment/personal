import { h, pageHeader, card, cardHead, table, badge, kv, stat } from '../../ui.js';
import { CLINICS, allRequests, HUMAN_SLOTS, PET_SLOTS } from '../../data.js';

export async function render() {
  const wrap = h('div');
  const reqs = await allRequests(3000);
  const now = new Date(); const week = new Date(Date.now() + 7 * 86400000);
  wrap.append(pageHeader('Clinics', 'Locations are defined in the member app today (Request Care and Clinic Locator). Changing them means a FlutterFlow update, so this page is read-only.'),
    h('div', { class: 'callout mb' }, h('div', null, h('b', null, 'Heads up: '), 'Request Care saves the full name (for example "Littleton - Dakota Ridge") while Clinic Locator looks up the short name ("Dakota Ridge"), so the app\'s availability view never sees bookings. The staff schedule uses the full name, which is what the data holds.')),
    h('div', { class: 'grid grid-3' }, CLINICS.map(c => { const rows = reqs.filter(r => r.clinic === c.key); const up = rows.filter(r => r.start && r.start >= now && r.start <= week && ['pending', 'confirmed'].includes(r.statusL)); return card(cardHead(c.key, badge('active', c.state)), kv('City', `${c.city}, ${c.state}`), kv('Timezone', c.tz), kv('Human slots', `${HUMAN_SLOTS[0]} – ${HUMAN_SLOTS[HUMAN_SLOTS.length - 1]}, every 30 min`), kv('Pet slots', `${PET_SLOTS[0]} – ${PET_SLOTS[PET_SLOTS.length - 1]}`), kv('Visits booked, next 7 days', up.length), kv('All-time visits', rows.length), kv('Completed', rows.filter(r => r.statusL === 'completed').length)); }), card(cardHead('Virtual', badge('info', 'Telehealth')), kv('Visits booked, next 7 days', reqs.filter(r => r.visitMode === 'Virtual' && r.start && r.start >= now && r.start <= week && ['pending', 'confirmed'].includes(r.statusL)).length), kv('All-time', reqs.filter(r => r.visitMode === 'Virtual').length))));
  return wrap;
}
