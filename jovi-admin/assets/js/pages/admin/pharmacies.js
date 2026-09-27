import { h, pageHeader, card, table, badge, btn, field, input, checkbox, drawer, closeDrawer, toast, errorToast, textarea } from '../../ui.js';
import { pharmacies, savePharmacy } from '../../data.js';
import { can } from '../../auth.js';

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const addrText = a => typeof a === 'string' ? a : a ? [a.street || a.line1, a.city, [a.state, a.zip || a.postalCode].filter(Boolean).join(' ')].filter(Boolean).join(', ') : '';
const hoursArr = hrs => Array.isArray(hrs) ? hrs : hrs && typeof hrs === 'object' ? DAYS.map(d => { const v = hrs[d] ?? hrs[d.toLowerCase()] ?? hrs[d.slice(0, 3)] ?? ''; return typeof v === 'object' ? (v.closed ? 'Closed' : `${v.open || v.opens || ''} – ${v.close || v.closes || ''}`) : String(v); }) : Array(7).fill('');

export async function render() {
  const wrap = h('div'); const list = h('div');
  wrap.append(pageHeader('Partner pharmacies', 'The list members see under Prescription Refills. Members can also pick any pharmacy near them.', can('writeBusiness') ? [btn('Add pharmacy', () => edit(null), { variant: 'btn-primary' })] : []), list);
  async function load() {
    const rows = (await pharmacies()).sort((a, b) => (a.name || '').localeCompare(b.name || ''));
    list.replaceChildren(card(table([{ label: 'Name', render: r => h('b', null, r.name) }, { label: 'Address', render: r => addrText(r.address) }, { label: 'Phone', key: 'phone' }, { label: 'Today', render: r => hoursArr(r.hours)[(new Date().getDay() + 6) % 7] || '—' }, { label: 'Active', render: r => badge(r.isActive ? 'active' : 'suspended', r.isActive ? 'Listed' : 'Hidden') }, { label: '', render: r => can('writeBusiness') ? btn('Edit', () => edit(r), { size: 'btn-sm' }) : null }], rows, { empty: 'No partner pharmacies yet' })));
  }
  function edit(r) {
    const a = typeof r?.address === 'object' ? r.address : {};
    const f = { name: input({ value: r?.name || '' }), street: input({ value: a.street || a.line1 || (typeof r?.address === 'string' ? r.address : '') }), city: input({ value: a.city || '' }), state: input({ value: a.state || '', maxlength: 2 }), zip: input({ value: a.zip || a.postalCode || '' }), phone: input({ value: r?.phone || '' }), website: input({ value: r?.website || '' }), lat: input({ value: r?.lat ?? a.lat ?? '', type: 'number', step: 'any' }), lng: input({ value: r?.lng ?? a.lng ?? '', type: 'number', step: 'any' }), active: checkbox('Listed in the app', r ? r.isActive !== false : true), hours: hoursArr(r?.hours).map((v, i) => input({ value: v, placeholder: 'e.g. 9:00 AM – 9:00 PM or Closed', dataset: { day: DAYS[i] } })) };
    drawer(r ? `Edit ${r.name}` : 'Add pharmacy', h('div', { class: 'col' }, field('Name', f.name), h('div', { class: 'form-grid' }, field('Street', f.street), field('City', f.city), field('State', f.state), field('ZIP', f.zip), field('Phone', f.phone), field('Website', f.website), field('Latitude', f.lat), field('Longitude', f.lng)), f.active, h('h3', null, 'Hours'), h('div', { class: 'form-grid' }, f.hours.map((inp, i) => field(DAYS[i], inp))),
      h('div', { class: 'row', style: { justifyContent: 'flex-end' } }, btn('Cancel', closeDrawer), btn('Save', async () => {
        try { await savePharmacy(r?.id, { name: f.name.value.trim(), isActive: f.active.querySelector('input').checked, address: { street: f.street.value.trim(), city: f.city.value.trim(), state: f.state.value.trim().toUpperCase(), zip: f.zip.value.trim(), lat: f.lat.value ? Number(f.lat.value) : null, lng: f.lng.value ? Number(f.lng.value) : null }, lat: f.lat.value ? Number(f.lat.value) : null, lng: f.lng.value ? Number(f.lng.value) : null, phone: f.phone.value.trim(), website: f.website.value.trim(), hours: f.hours.map(i => i.value.trim()) }); toast('Saved', 'success'); closeDrawer(); load(); } catch (e) { errorToast(e); }
      }, { variant: 'btn-primary' }))));
  }
  await load();
  return wrap;
}
