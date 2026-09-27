import { h, pageHeader, card, cardHead, badge, btn, select, input, field, textarea, drawer, closeDrawer, toast, errorToast, confirm, prompt, fmtDateTime, todayStr, avatar, kv, table, modal } from '../../ui.js';
import { requestsBetween, CLINICS, confirmRequest, completeRequest, noShowRequest, cancelRequestByClinic, rescheduleRequest, bookedSlots, HUMAN_SLOTS, PET_SLOTS, createRequestForMember, findMembers, petsFor, memberName, patientNames, updateRequest, getMember, startTelehealth, scheduleReminder, providers, scheduleBlocks, addBlock, removeBlock, waitlist, addWaitlist, updateWaitlist, offerSlotToWaitlist, saveProviderSettings, DEFAULT_HOURS, parseSlot } from '../../data.js';
import { runIntake, captureConsent } from '../../intake.js';
import { navigate } from '../../router.js';
import { can, session } from '../../auth.js';

const DAY = 86400000;
const mondayOf = d => { const x = new Date(d); x.setHours(0, 0, 0, 0); x.setDate(x.getDate() - ((x.getDay() + 6) % 7)); return x; };

export async function render(ctx) {
  const wrap = h('div'); const grid = h('div'); const head = h('div', { class: 'toolbar' });
  let start = mondayOf(new Date()); let clinic = ''; let view = 'week'; let provider = ''; let blocks = [];
  const provs = await providers().catch(() => []);
  const provSel = select([['', 'All providers'], ...provs.map(p => [p.id, p.name || p.email])], '', { onChange: e => { provider = e.target.value; draw(); } });
  const label = h('b');
  const clinicSel = select([['', 'All locations'], ...CLINICS.map(c => [c.key, c.key]), ['Virtual', 'Virtual']], '', { onChange: e => { clinic = e.target.value; draw(); } });
  head.append(btn('‹', () => { start = new Date(start.getTime() - (view === 'week' ? 7 : 1) * DAY); draw(); }), btn('Today', () => { start = view === 'week' ? mondayOf(new Date()) : new Date(new Date().setHours(0, 0, 0, 0)); draw(); }), btn('›', () => { start = new Date(start.getTime() + (view === 'week' ? 7 : 1) * DAY); draw(); }), label, clinicSel,
    select([['week', 'Week'], ['day', 'Day list']], 'week', { onChange: e => { view = e.target.value; start = view === 'week' ? mondayOf(start) : start; draw(); } }),
    provSel, can('chart') ? btn('Block time', () => blockTime(provs, draw), { size: 'btn-sm' }) : null, can('chart') ? btn('Waitlist', () => showWaitlist(draw), { size: 'btn-sm' }) : null, can('chart') ? btn('My hours', () => hoursEditor(provs), { size: 'btn-sm', variant: 'btn-ghost' }) : null,
    can('chart') ? btn('New appointment', () => newAppointment(draw), { variant: 'btn-primary', class: 'right' }) : null);
  wrap.append(pageHeader('Schedule', 'Every request the app created, by clinic. Confirm to lock the slot; the member is notified automatically.'), head, grid);
  async function draw() {
    const days = view === 'week' ? 7 : 1; const end = new Date(start.getTime() + (days - 1) * DAY);
    label.textContent = view === 'week' ? `${start.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} – ${end.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}` : start.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
    grid.replaceChildren(h('div', { class: 'spinner-wrap' }, h('span', { class: 'spinner' })));
    let rows;
    try { rows = await requestsBetween(todayStr(start), todayStr(end), { clinic: clinic && clinic !== 'Virtual' ? clinic : null }); } catch (e) { errorToast(e); rows = []; }
    if (clinic === 'Virtual') rows = rows.filter(r => r.visitMode === 'Virtual');
    if (provider) rows = rows.filter(r => r.providerId === provider || (!r.providerId && provider === 'unassigned'));
    blocks = await scheduleBlocks(todayStr(start), todayStr(end)).catch(() => []);
    rows = rows.filter(r => r.userId); // member-cancelled slots (userId null, status 'available') are not visits
    if (view === 'week') {
      const cols = []; for (let i = 0; i < 7; i++) { const d = new Date(start.getTime() + i * DAY); const ds = todayStr(d); const dayRows = rows.filter(r => String(r.appointmentDate || '').slice(0, 10) === ds); const dayBlocks = blocks.filter(b => b.day === ds && (!provider || b.providerId === provider)); const prov = provs.find(p => p.id === provider); const hrs = prov?.schedule?.hours?.[d.getDay()]; cols.push(h('div', { class: `day ${ds === todayStr() ? 'today' : ''}` }, h('h6', null, d.toLocaleDateString('en-US', { weekday: 'short' }), h('b', null, d.getDate())), prov ? h('div', { class: 'small muted', style: { marginBottom: '4px' } }, hrs ? `${hrs[0]}–${hrs[1]}` : 'Off') : null, dayBlocks.map(b => h('div', { class: 'appt', style: { background: 'var(--line-2)', color: 'var(--ink-3)' }, onClick: async () => { if (can('chart') && await confirm('Remove this block?', b.reason || '')) { await removeBlock(b.id); draw(); } } }, h('b', null, `${b.from}–${b.to}`), `${b.reason || 'Blocked'}${b.providerName ? ' · ' + b.providerName : ''}`)), dayRows.length ? dayRows.map(r => apptChip(r, draw)) : h('p', { class: 'muted small' }, '—'))); }
      grid.replaceChildren(h('div', { class: 'sched' }, cols));
    } else {
      grid.replaceChildren(card(table([{ label: 'Time', render: r => r.appointmentTime || '—' }, { label: 'Patient', render: r => h('div', { class: 'who' }, avatar(r.patientName, r.petPhotoUrl, 28), h('div', null, h('b', null, r.patientName || 'Unknown'), h('span', null, r.isPet ? `${r.petSpecies || 'pet'} · ${r.petBreed || ''}` : r.visitType || ''))) }, { label: 'Reason', render: r => h('span', null, r.symptom || r.reason || '—') }, { label: 'Mode', render: r => `${r.visitMode || 'Clinic'}${r.clinic ? ' · ' + r.clinic.split(' - ')[1] : ''}` }, { label: 'Status', render: r => badge(r.statusL) }, { label: 'Pass', render: r => r.priority ? badge('active', 'Jovi Pass') : '' }, { label: '', render: r => btn('Open', () => openRequest(r, draw), { size: 'btn-sm' }) }], rows, { onRow: r => openRequest(r, draw), empty: 'No visits this day' })));
    }
  }
  await draw();
  return wrap;
}

function apptChip(r, redraw) {
  return h('div', { class: `appt ${r.statusL} ${r.isPet ? 'pet' : ''}`, onClick: () => openRequest(r, redraw), title: r.symptom || '' }, h('b', null, `${r.appointmentTime || ''} ${r.priority ? '⚡' : ''}`), `${r.patientName || 'Unknown'}`, h('div', { class: 'small', style: { opacity: .8 } }, `${r.isPet ? 'Pet · ' : ''}${r.visitType || ''}${r.visitMode === 'Virtual' ? ' · Virtual' : ''}${r.providerName ? ' · ' + r.providerName.split(' ')[0] : ''}${r.room ? ' · Rm ' + r.room : ''}`));
}

export async function openRequest(r, redraw = () => {}) {
  const canEdit = can('chart');
  const u = r.userId ? await getMember(r.userId).catch(() => null) : null;
  const act = [];
  if (canEdit) {
    if (r.statusL === 'pending') act.push(btn('Confirm', async () => { try { await confirmRequest(r.id, { providerName: session.staff?.name || '', clinicName: r.clinic || '' }); toast('Confirmed. Member notified.', 'success'); closeDrawer(); redraw(); } catch (e) { errorToast(e); } }, { variant: 'btn-success', size: 'btn-sm' }));
    if (['pending', 'confirmed', 'rescheduled'].includes(r.statusL)) {
      act.push(btn('Reschedule', () => reschedule(r, redraw), { size: 'btn-sm' }));
      if (r.visitMode === 'Virtual') act.push(btn(r.telehealthUrl ? 'Join video' : 'Start video visit', async () => { try { const url = await startTelehealth(r); window.open(url, '_blank', 'noopener'); toast('Video room ready. Member notified.', 'success'); } catch (e) { errorToast(e); } }, { variant: 'btn-accent', size: 'btn-sm' }));
      act.push(btn('Check in / chart', () => { closeDrawer(); navigate(`/ehr/chart/${r.userId}/encounter/${r.id}`); }, { variant: 'btn-primary', size: 'btn-sm' }));
      act.push(btn('No-show', async () => { if (!(await confirm('Mark as no-show?', 'The member will be notified.'))) return; try { await noShowRequest(r.id); toast('Marked no-show', 'success'); closeDrawer(); redraw(); } catch (e) { errorToast(e); } }, { size: 'btn-sm' }));
      act.push(btn('Cancel', async () => { const reason = await prompt('Cancel this visit', 'Reason sent to the member', { okLabel: 'Cancel visit' }); if (reason == null) return; try { await cancelRequestByClinic(r, reason); toast('Cancelled. Member notified.', 'success'); closeDrawer(); redraw(); offerFreedSlot(r); } catch (e) { errorToast(e); } }, { variant: 'btn-danger', size: 'btn-sm' }));
    }
  }
  drawer(`${r.patientName || 'Visit'} · ${r.appointmentTime || ''}`, h('div', { class: 'col' },
    h('div', { class: 'row' }, badge(r.statusL), r.isPet ? badge('info', 'Pet visit') : null, r.priority ? badge('active', 'Jovi Pass · priority') : null, r.visitMode === 'Virtual' ? badge('telehealth', 'Virtual') : null),
    card(kv('When', `${fmtDateTime(r.start)} (${r.timezone || 'local'})`), kv('Type', r.visitType), kv('Location', r.visitMode === 'Virtual' ? 'Telehealth' : r.clinic), kv('Member', u ? h('a', { href: `#/ehr/chart/${r.userId}`, class: 'lnk' }, memberName(u)) : r.userId || '—'), kv('Patient', r.patientName), r.isPet ? kv('Pet', `${r.petName} · ${r.petSpecies || ''} · ${r.petBreed || ''}${r.petWeightLbs ? ' · ' + r.petWeightLbs + ' lb' : ''}`) : null, kv('Booked', fmtDateTime(r.createdAt)), r.rescheduledAt ? kv('Rescheduled', fmtDateTime(r.rescheduledAt)) : null, kv('Est. wait quoted', r.estimatedWaitTime || '—'), kv('Beverage', [r.selectedBeverage, r.selectedTeaType].filter(Boolean).join(' · ') || '—')),
    card(cardHead('Reason for visit'), h('p', null, h('b', null, r.symptom || '—'), r.symptomDuration ? ` · ${r.symptomDuration}` : ''), r.details ? h('p', { class: 'mt', style: { whiteSpace: 'pre-wrap' } }, r.details) : null, r.medication ? h('p', { class: 'mt' }, h('b', null, 'Medication: '), r.medication) : null, r.photoUrl ? h('a', { href: r.photoUrl, target: '_blank' }, h('img', { src: r.photoUrl, style: { maxWidth: '100%', borderRadius: '10px', marginTop: '10px' } })) : null),
    !r.isPet && (r.currentMedications || r.allergies || r.previousSurgeries || r.familyMedicalHistory) ? card(cardHead('Medical snapshot at booking'), kv('Medications', r.currentMedications || '—'), kv('Allergies', r.allergies || '—'), kv('Surgeries', r.previousSurgeries || '—'), kv('Family history', r.familyMedicalHistory || '—'), kv('Primary physician', r.primaryPhysician || '—'), kv('Smoking', r.smokingStatus || '—'), kv('Alcohol', r.alcoholConsumption || '—'), kv('Exercise', r.exerciseFrequency || '—'), kv('Diet', r.dietaryRestrictions || '—')) : null,
    canEdit ? card(cardHead('Provider, room & check-in'), (() => { const provs2 = []; const ps = select([['', 'Unassigned']], r.providerId || ''); providers().then(list => { list.forEach(p => ps.append(h('option', { value: p.id, selected: p.id === r.providerId ? true : null }, p.name || p.email))); }); const room = input({ value: r.room || '', placeholder: 'Room' }); return h('div', { class: 'col' }, h('div', { class: 'form-grid' }, field('Provider', ps), field('Room', room)), h('div', { class: 'row' }, btn('Save assignment', async () => { const name = ps.selectedOptions[0]?.textContent; try { await updateRequest(r.id, { providerId: ps.value || null, providerName: ps.value ? name : (r.providerName || ''), room: room.value.trim() }, 'appointment.assign'); toast('Saved', 'success'); redraw(); } catch (e) { errorToast(e); } }, { size: 'btn-sm' }), r.userId ? btn('Run intake', () => runIntake(r.userId, r.patientName || 'Patient', r.id), { size: 'btn-sm' }) : null, r.userId ? btn('Consent', () => captureConsent(r.userId, r.patientName || 'Patient', r.id), { size: 'btn-sm' }) : null, r.userId && r.statusL !== 'completed' ? btn('Add to waitlist for sooner', async () => { try { await addWaitlist({ userId: r.userId, patientName: r.patientName, requestId: r.id, clinic: r.clinic || '', visitMode: r.visitMode || 'Clinic', currentSlot: `${String(r.appointmentDate || '').slice(0, 10)} ${r.appointmentTime || ''}`, isPet: !!r.isPet }); toast('Added to waitlist', 'success'); } catch (e) { errorToast(e); } }, { size: 'btn-sm', variant: 'btn-ghost' }) : null)); })()) : null,
    canEdit && r.userId ? card(cardHead('Remind the member'), h('p', { class: 'muted small' }, 'Sends a push at the chosen time through the app’s reminder pipeline, on top of the automatic 24 h and 1 h reminders.'), (() => { const when = input({ type: 'datetime-local' }); const msg = input({ value: `Reminder: ${r.visitType || 'visit'} ${r.appointmentTime || ''} at Jovi`, placeholder: 'Message' }); return h('div', { class: 'col' }, h('div', { class: 'form-grid' }, field('Send at', when), field('Message', msg)), h('div', { class: 'row', style: { justifyContent: 'flex-end' } }, btn('Schedule reminder', async () => { if (!when.value) return toast('Pick a time', 'error'); try { await scheduleReminder(r.userId, { title: 'Upcoming visit', body: msg.value.trim(), fireAt: new Date(when.value), route: 'appointments', params: { requestId: r.id } }); toast('Reminder scheduled', 'success'); } catch (e) { errorToast(e); } }, { size: 'btn-sm' }))); })()) : null,
    canEdit ? card(cardHead('Staff notes on this visit'), (() => { const ta = textarea({ value: r.notes || '', placeholder: 'Internal notes (visible to the member in Care Records as "notes")' }); return h('div', { class: 'col' }, ta, h('div', { class: 'row', style: { justifyContent: 'flex-end' } }, btn('Save notes', async () => { try { await updateRequest(r.id, { notes: ta.value.trim() }, 'appointment.notes'); toast('Saved', 'success'); } catch (e) { errorToast(e); } }, { size: 'btn-sm' }))); })()) : null,
  ), { wide: false, actions: act });
}

async function reschedule(r, redraw) {
  const day = input({ type: 'date', value: String(r.appointmentDate || '').slice(0, 10) || todayStr() });
  const slot = select((r.isPet ? PET_SLOTS : HUMAN_SLOTS).map(s => [s, s]), r.appointmentTime || HUMAN_SLOTS[0]);
  const note = h('p', { class: 'muted small' });
  const refresh = async () => { try { const taken = await bookedSlots(day.value, { clinic: r.clinic, visitMode: r.visitMode || 'Clinic', pet: r.isPet }); taken.delete(r.appointmentTime); [...slot.options].forEach(o => { o.disabled = taken.has(o.value); o.textContent = taken.has(o.value) ? `${o.value} · booked` : o.value; }); note.textContent = `${taken.size} slot(s) already booked at this location.`; } catch { } };
  day.addEventListener('change', refresh); await refresh();
  const m = modal('Reschedule visit', h('div', { class: 'col' }, field('Date', day), field('Time', slot), note), [btn('Cancel', () => m.close()), btn('Reschedule', async () => { try { await rescheduleRequest(r.id, day.value, slot.value); toast('Rescheduled. Member notified.', 'success'); m.close(); closeDrawer(); redraw(); } catch (e) { errorToast(e); } }, { variant: 'btn-primary' })]);
}

async function newAppointment(redraw) {
  const q = input({ placeholder: 'Search member by name or email…' }); const results = h('div', { class: 'list' }); let member = null, pets = [];
  const patient = select([], ''); const petSel = select([], ''); const kind = select([['human', 'Human visit'], ['pet', 'Pet visit']], 'human');
  const vtype = select(['Urgent Care', 'Primary Care', 'Wellness'].map(x => [x, x]), 'Primary Care'); const mode = select([['Clinic', 'Clinic'], ['Virtual', 'Virtual']], 'Clinic'); const clinicSel = select(CLINICS.map(c => [c.key, c.key]), CLINICS[0].key);
  const day = input({ type: 'date', value: todayStr() }); const slot = select(HUMAN_SLOTS.map(s => [s, s]), HUMAN_SLOTS[0]); const reason = input({ placeholder: 'Reason for visit' }); const details = textarea({ placeholder: 'Details (optional)', rows: 2 });
  const petRow = field('Pet', petSel); petRow.classList.add('hidden');
  const patientRow = field('Patient', patient);
  kind.addEventListener('change', () => { const pet = kind.value === 'pet'; petRow.classList.toggle('hidden', !pet); patientRow.classList.toggle('hidden', pet); vtype.replaceChildren(...(pet ? ['Wellness', 'Sick or Injured'] : ['Urgent Care', 'Primary Care', 'Wellness']).map(x => h('option', { value: x }, x))); slot.replaceChildren(...(pet ? PET_SLOTS : HUMAN_SLOTS).map(s => h('option', { value: s }, s))); refreshSlots(); });
  const refreshSlots = async () => { try { const taken = await bookedSlots(day.value, { clinic: clinicSel.value, visitMode: mode.value, pet: kind.value === 'pet' }); [...slot.options].forEach(o => { o.disabled = taken.has(o.value); o.textContent = taken.has(o.value) ? `${o.value} · booked` : o.value; }); } catch { } };
  [day, clinicSel, mode].forEach(el => el.addEventListener('change', refreshSlots)); refreshSlots();
  let tm; q.addEventListener('input', () => { clearTimeout(tm); tm = setTimeout(async () => { const rows = await findMembers(q.value.trim(), 6); results.replaceChildren(...rows.map(m => h('div', { class: 'list-item', style: { cursor: 'pointer' }, onClick: async () => { member = m; q.value = m.name; results.replaceChildren(); patient.replaceChildren(...patientNames(m).map(n => h('option', { value: n }, n))); pets = await petsFor(m.id); petSel.replaceChildren(...pets.map(p => h('option', { value: p.id }, `${p.name} (${p.type || 'pet'})`))); } }, avatar(m.name, m.photo, 26), h('div', { class: 'grow' }, h('b', null, m.name), h('span', null, m.email || ''))))); }, 200); });
  drawer('New appointment', h('div', { class: 'col' }, field('Member', q), results, field('Visit for', kind), patientRow, petRow, h('div', { class: 'form-grid' }, field('Visit type', vtype), field('Mode', mode), field('Clinic', clinicSel), field('Date', day), field('Time', slot)), field('Reason', reason), field('Details', details),
    h('div', { class: 'row', style: { justifyContent: 'flex-end' } }, btn('Cancel', closeDrawer), btn('Book & confirm', async () => {
      if (!member) return toast('Pick a member first', 'error'); const isPet = kind.value === 'pet'; const pet = isPet ? pets.find(p => p.id === petSel.value) : null; if (isPet && !pet) return toast('Pick a pet', 'error');
      try { await createRequestForMember(member, { day: day.value, slot: slot.value, visitType: vtype.value, visitMode: mode.value, clinic: clinicSel.value, patientName: isPet ? pet.name : patient.value, symptom: reason.value.trim(), details: details.value.trim(), isPet, pet }); toast('Booked. Member notified.', 'success'); closeDrawer(); redraw(); } catch (e) { errorToast(e); }
    }, { variant: 'btn-primary' }))));
}


// ── Provider hours, blocks, waitlist ────────────────────────────────────
const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
async function hoursEditor(provs) {
  const me = provs.find(p => p.id === session.user.uid) || provs[0]; if (!me) return toast('No provider record for you', 'error');
  const who = select(provs.map(p => [p.id, p.name || p.email]), me.id); let cur = { ...(me.schedule || {}) };
  const grid = h('div', { class: 'col' });
  const draw = () => { const p = provs.find(x => x.id === who.value); cur = { hours: { ...DEFAULT_HOURS, ...(p?.schedule?.hours || {}) }, clinics: p?.schedule?.clinics || CLINICS.map(c => c.key), slotMinutes: p?.schedule?.slotMinutes || 30, telehealth: p?.schedule?.telehealth !== false };
    grid.replaceChildren(...DAYS.map((d, i) => { const on = !!cur.hours[i]; const from = select(HUMAN_SLOTS.map(s => [s, s]), cur.hours[i]?.[0] || '9:00 AM'); const to = select([...HUMAN_SLOTS, '5:00 PM', '5:30 PM', '6:00 PM'].map(s => [s, s]), cur.hours[i]?.[1] || '4:30 PM'); const cb = h('input', { type: 'checkbox', checked: on ? true : null, onChange: () => { if (cb.checked) cur.hours[i] = [from.value, to.value]; else delete cur.hours[i]; } }); from.addEventListener('change', () => { if (cb.checked) cur.hours[i] = [from.value, to.value]; }); to.addEventListener('change', () => { if (cb.checked) cur.hours[i] = [from.value, to.value]; }); return h('div', { class: 'row' }, h('label', { class: 'check', style: { width: '120px' } }, cb, h('span', null, d)), from, h('span', { class: 'muted' }, 'to'), to); }),
      h('div', { class: 'form-grid mt' }, field('Slot length (min)', select([[15, '15'], [20, '20'], [30, '30'], [45, '45'], [60, '60']], cur.slotMinutes, { onChange: e => cur.slotMinutes = Number(e.target.value) })), field('Telehealth', select([['yes', 'Offers video visits'], ['no', 'In person only']], cur.telehealth ? 'yes' : 'no', { onChange: e => cur.telehealth = e.target.value === 'yes' }))),
      field('Clinics', h('div', { class: 'chips' }, CLINICS.map(c => h('button', { type: 'button', class: `chip ${cur.clinics.includes(c.key) ? 'on' : ''}`, onClick: e => { const i = cur.clinics.indexOf(c.key); if (i >= 0) cur.clinics.splice(i, 1); else cur.clinics.push(c.key); e.target.classList.toggle('on'); } }, c.short))))); };
  who.addEventListener('change', draw); draw();
  drawer('Provider hours', h('div', { class: 'col' }, field('Provider', who), grid, h('div', { class: 'row', style: { justifyContent: 'flex-end' } }, btn('Cancel', closeDrawer), btn('Save', async () => { try { await saveProviderSettings(who.value, cur); const p = provs.find(x => x.id === who.value); if (p) p.schedule = cur; toast('Saved', 'success'); closeDrawer(); } catch (e) { errorToast(e); } }, { variant: 'btn-primary' }))));
}
async function blockTime(provs, redraw) {
  const who = select([['', 'Whole clinic'], ...provs.map(p => [p.id, p.name || p.email])], session.user.uid); const day = input({ type: 'date', value: todayStr() }); const from = select(HUMAN_SLOTS.map(s => [s, s]), '9:00 AM'); const to = select([...HUMAN_SLOTS, '5:00 PM', '5:30 PM'].map(s => [s, s]), '12:00 PM'); const reason = input({ placeholder: 'Lunch, admin, out of office…' }); const clinicSel = select([['', 'All clinics'], ...CLINICS.map(c => [c.key, c.key])], '');
  const m = modal('Block time', h('div', { class: 'col' }, h('div', { class: 'form-grid' }, field('Provider', who), field('Clinic', clinicSel), field('Day', day), field('Reason', reason), field('From', from), field('To', to))), [btn('Cancel', () => m.close()), btn('Block', async () => { try { await addBlock({ providerId: who.value || null, providerName: who.value ? who.selectedOptions[0].textContent : null, clinic: clinicSel.value || null, day: day.value, from: from.value, to: to.value, reason: reason.value.trim() }); toast('Blocked', 'success'); m.close(); redraw(); } catch (e) { errorToast(e); } }, { variant: 'btn-primary' })]);
}
async function showWaitlist(redraw) {
  const rows = await waitlist('waiting').catch(() => []);
  drawer(`Waitlist (${rows.length})`, h('div', { class: 'col' }, h('p', { class: 'muted small' }, 'Members who want something sooner. When a slot frees up you are prompted to offer it; you can also offer one manually.'), rows.length ? h('div', { class: 'list' }, rows.map(w => h('div', { class: 'list-item' }, h('div', { class: 'grow' }, h('b', null, w.patientName || w.userId), h('span', null, `${w.isPet ? 'Pet · ' : ''}${w.clinic || w.visitMode} · currently ${w.currentSlot || '—'} · waiting since ${fmtDateTime(w.createdAt)}`)), btn('Offer a slot', async () => { const day = await prompt('Offer slot', 'Date and time, e.g. 2026-09-25 10:30 AM'); if (!day) return; const [dd, ...rest] = day.split(' '); try { await offerSlotToWaitlist(w, dd, rest.join(' '), w.clinic); toast('Offer sent', 'success'); closeDrawer(); } catch (e) { errorToast(e); } }, { size: 'btn-sm', variant: 'btn-primary' }), btn('Remove', async () => { await updateWaitlist(w.id, { status: 'removed' }); closeDrawer(); showWaitlist(redraw); }, { size: 'btn-sm', variant: 'btn-ghost' })))) : h('p', { class: 'muted' }, 'Nobody waiting.')));
}
async function offerFreedSlot(r) {
  try { const rows = (await waitlist('waiting')).filter(w => (w.isPet === !!r.isPet) && (!w.clinic || w.clinic === r.clinic)); if (!rows.length) return;
    const w = rows[0]; if (!(await confirm('Offer the freed slot?', `${w.patientName || 'A waitlisted member'} is waiting for ${r.clinic || r.visitMode}. Offer ${r.appointmentTime} on ${String(r.appointmentDate || '').slice(0, 10)}?`))) return;
    await offerSlotToWaitlist(w, String(r.appointmentDate || '').slice(0, 10), r.appointmentTime, r.clinic); toast('Offer sent', 'success'); } catch (e) { console.warn(e); }
}
