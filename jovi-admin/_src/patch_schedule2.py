"""Schedule: provider filter and assignment, working hours, blocks, room, waitlist, intake from the drawer."""
import pathlib
p = pathlib.Path(__file__).resolve().parent.parent / "assets/js/pages/ehr/schedule.js"
t = p.read_text(encoding="utf-8")
assert "providers()" not in t, "already patched"
def rep(a, b):
    global t
    assert t.count(a) == 1, (a[:80], t.count(a)); t = t.replace(a, b)

rep("updateRequest, getMember, startTelehealth, scheduleReminder } from '../../data.js';",
    "updateRequest, getMember, startTelehealth, scheduleReminder, providers, scheduleBlocks, addBlock, removeBlock, waitlist, addWaitlist, updateWaitlist, offerSlotToWaitlist, saveProviderSettings, DEFAULT_HOURS, parseSlot } from '../../data.js';\nimport { runIntake, captureConsent } from '../../intake.js';")

# toolbar: provider filter, blocks, waitlist, hours
rep("  let start = mondayOf(new Date()); let clinic = ''; let view = 'week';",
    "  let start = mondayOf(new Date()); let clinic = ''; let view = 'week'; let provider = ''; let blocks = [];\n  const provs = await providers().catch(() => []);\n  const provSel = select([['', 'All providers'], ...provs.map(p => [p.id, p.name || p.email])], '', { onChange: e => { provider = e.target.value; draw(); } });")
rep("    can('chart') ? btn('New appointment', () => newAppointment(draw), { variant: 'btn-primary', class: 'right' }) : null);",
    "    provSel, can('chart') ? btn('Block time', () => blockTime(provs, draw), { size: 'btn-sm' }) : null, can('chart') ? btn('Waitlist', () => showWaitlist(draw), { size: 'btn-sm' }) : null, can('chart') ? btn('My hours', () => hoursEditor(provs), { size: 'btn-sm', variant: 'btn-ghost' }) : null,\n    can('chart') ? btn('New appointment', () => newAppointment(draw), { variant: 'btn-primary', class: 'right' }) : null);")
rep("    if (clinic === 'Virtual') rows = rows.filter(r => r.visitMode === 'Virtual');",
    "    if (clinic === 'Virtual') rows = rows.filter(r => r.visitMode === 'Virtual');\n    if (provider) rows = rows.filter(r => r.providerId === provider || (!r.providerId && provider === 'unassigned'));\n    blocks = await scheduleBlocks(todayStr(start), todayStr(end)).catch(() => []);")
# week view: show blocks + off-hours shading per provider
rep("cols.push(h('div', { class: `day ${ds === todayStr() ? 'today' : ''}` }, h('h6', null, d.toLocaleDateString('en-US', { weekday: 'short' }), h('b', null, d.getDate())), dayRows.length ? dayRows.map(r => apptChip(r, draw)) : h('p', { class: 'muted small' }, '—'))); }",
    "const dayBlocks = blocks.filter(b => b.day === ds && (!provider || b.providerId === provider)); const prov = provs.find(p => p.id === provider); const hrs = prov?.schedule?.hours?.[d.getDay()]; cols.push(h('div', { class: `day ${ds === todayStr() ? 'today' : ''}` }, h('h6', null, d.toLocaleDateString('en-US', { weekday: 'short' }), h('b', null, d.getDate())), prov ? h('div', { class: 'small muted', style: { marginBottom: '4px' } }, hrs ? `${hrs[0]}–${hrs[1]}` : 'Off') : null, dayBlocks.map(b => h('div', { class: 'appt', style: { background: 'var(--line-2)', color: 'var(--ink-3)' }, onClick: async () => { if (can('chart') && await confirm('Remove this block?', b.reason || '')) { await removeBlock(b.id); draw(); } } }, h('b', null, `${b.from}–${b.to}`), `${b.reason || 'Blocked'}${b.providerName ? ' · ' + b.providerName : ''}`)), dayRows.length ? dayRows.map(r => apptChip(r, draw)) : h('p', { class: 'muted small' }, '—'))); }")
# chip shows provider + room
rep("h('div', { class: 'small', style: { opacity: .8 } }, `${r.isPet ? 'Pet · ' : ''}${r.visitType || ''}${r.visitMode === 'Virtual' ? ' · Virtual' : ''}`));",
    "h('div', { class: 'small', style: { opacity: .8 } }, `${r.isPet ? 'Pet · ' : ''}${r.visitType || ''}${r.visitMode === 'Virtual' ? ' · Virtual' : ''}${r.providerName ? ' · ' + r.providerName.split(' ')[0] : ''}${r.room ? ' · Rm ' + r.room : ''}`));")

# drawer: assign provider/room, intake, consent
rep("    canEdit && r.userId ? card(cardHead('Remind the member'),",
    """    canEdit ? card(cardHead('Provider, room & check-in'), (() => { const provs2 = []; const ps = select([['', 'Unassigned']], r.providerId || ''); providers().then(list => { list.forEach(p => ps.append(h('option', { value: p.id, selected: p.id === r.providerId ? true : null }, p.name || p.email))); }); const room = input({ value: r.room || '', placeholder: 'Room' }); return h('div', { class: 'col' }, h('div', { class: 'form-grid' }, field('Provider', ps), field('Room', room)), h('div', { class: 'row' }, btn('Save assignment', async () => { const name = ps.selectedOptions[0]?.textContent; try { await updateRequest(r.id, { providerId: ps.value || null, providerName: ps.value ? name : (r.providerName || ''), room: room.value.trim() }, 'appointment.assign'); toast('Saved', 'success'); redraw(); } catch (e) { errorToast(e); } }, { size: 'btn-sm' }), r.userId ? btn('Run intake', () => runIntake(r.userId, r.patientName || 'Patient', r.id), { size: 'btn-sm' }) : null, r.userId ? btn('Consent', () => captureConsent(r.userId, r.patientName || 'Patient', r.id), { size: 'btn-sm' }) : null, r.userId && r.statusL !== 'completed' ? btn('Add to waitlist for sooner', async () => { try { await addWaitlist({ userId: r.userId, patientName: r.patientName, requestId: r.id, clinic: r.clinic || '', visitMode: r.visitMode || 'Clinic', currentSlot: `${String(r.appointmentDate || '').slice(0, 10)} ${r.appointmentTime || ''}`, isPet: !!r.isPet }); toast('Added to waitlist', 'success'); } catch (e) { errorToast(e); } }, { size: 'btn-sm', variant: 'btn-ghost' }) : null)); })()) : null,
    canEdit && r.userId ? card(cardHead('Remind the member'),""")

# cancel: offer freed slot to the waitlist
rep("try { await cancelRequestByClinic(r, reason); toast('Cancelled. Member notified.', 'success'); closeDrawer(); redraw(); } catch (e) { errorToast(e); }",
    "try { await cancelRequestByClinic(r, reason); toast('Cancelled. Member notified.', 'success'); closeDrawer(); redraw(); offerFreedSlot(r); } catch (e) { errorToast(e); }")

t += r"""

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
"""
p.write_text(t, encoding="utf-8", newline="\n")
print("schedule patched")
