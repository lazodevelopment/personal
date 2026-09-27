"""Adds problem list, allergy editing, tasks/reminders, lab results, and addenda to chart.js."""
import pathlib
p = pathlib.Path(__file__).resolve().parent.parent / "assets/js/pages/ehr/chart.js"
t = p.read_text(encoding="utf-8")
assert "problemsFor" not in t, "already patched"

def rep(a, b):
    global t
    assert t.count(a) == 1, (a[:80], t.count(a))
    t = t.replace(a, b)

rep("uploadChartFile, getRequest, completeRequest, CLINICS, notifyMember, memberNotes, addMemberNote } from '../../data.js';",
    "uploadChartFile, getRequest, completeRequest, CLINICS, notifyMember, memberNotes, addMemberNote, problemsFor, addProblem, updateProblem, setAllergies, labResultsFor, addLabResult, addAddendum, tasks, updateTask, remindersFor } from '../../data.js';\nimport { quickTask } from './tasks.js';")

rep("      h('div', { class: 'row' }, btn('Business profile', () => navigate(`/admin/member/${uid}`), { size: 'btn-sm' }),",
    "      h('div', { class: 'row' }, btn('Business profile', () => navigate(`/admin/member/${uid}`), { size: 'btn-sm' }), can('chart') ? btn('New task', () => quickTask(uid, name), { size: 'btn-sm' }) : null,")

rep("    const [reqs, claims] = await Promise.all([requestsForUser(uid), humanClaimsFor(uid).catch(() => [])]);",
    "    const [reqs, claims, problems, myTasks, reminders] = await Promise.all([requestsForUser(uid), humanClaimsFor(uid).catch(() => []), problemsFor(uid).catch(() => []), tasks({ patientUid: uid }).catch(() => []), remindersFor(uid).catch(() => [])]);")

SUMMARY_EXTRA = r"""      h('div', { class: 'grid grid-3' },
        card(cardHead('Problem list', can('chart') ? btn('Add', () => { const label = input({ placeholder: 'Problem / diagnosis' }); const code = input({ placeholder: 'ICD-10' }); const onset = input({ type: 'date' }); const m = modal('Add problem', h('div', { class: 'col' }, field('Common', chips(CHIPS.dxCommon, null, v => { const mm = v.match(/^(.*)\s([A-Z]\d{2}[\.\d]*)$/); label.value = mm ? mm[1] : v; code.value = mm ? mm[2] : ''; })), field('Problem', label), h('div', { class: 'form-grid' }, field('ICD-10', code), field('Onset', onset))), [btn('Cancel', () => m.close()), btn('Add', async () => { if (!label.value.trim()) return; try { await addProblem(uid, { label: label.value.trim(), icdCode: code.value.trim(), onset: onset.value || null }); toast('Added', 'success'); m.close(); location.reload(); } catch (e) { errorToast(e); } }, { variant: 'btn-primary' })]); }, { size: 'btn-sm' }) : null),
          problems.filter(p => p.status === 'active').length ? h('div', { class: 'list' }, problems.filter(p => p.status === 'active').map(p => h('div', { class: 'list-item' }, h('div', { class: 'grow' }, h('b', null, p.label), h('span', null, `${p.icdCode || ''}${p.onset ? ' · since ' + p.onset : ''}`)), can('chart') ? btn('Resolve', async () => { await updateProblem(uid, p.id, { status: 'resolved', resolvedAt: Timestamp.now() }); location.reload(); }, { size: 'btn-sm', variant: 'btn-ghost' }) : null))) : h('p', { class: 'muted small' }, u.onboard_conditions ? `Self-reported at signup: ${u.onboard_conditions}` : 'No active problems'),
          problems.filter(p => p.status !== 'active').length ? h('p', { class: 'muted small mt' }, `Resolved: ${problems.filter(p => p.status !== 'active').map(p => p.label).join(', ')}`) : null),
        card(cardHead('Allergies', can('chart') ? btn('Edit', async () => { const cur = Array.isArray(u.allergies) ? u.allergies : (u.allergies ? String(u.allergies).split(/,|;/).map(s => s.trim()).filter(Boolean) : []); const v = await prompt('Allergies', 'Comma separated. Leave empty for no known allergies.', { value: cur.join(', ') }); if (v == null) return; try { await setAllergies(uid, v.split(',').map(s => s.trim()).filter(Boolean)); toast('Saved', 'success'); location.reload(); } catch (e) { errorToast(e); } }, { size: 'btn-sm' }) : null),
          (() => { const cur = Array.isArray(u.allergies) ? u.allergies : (u.allergies ? String(u.allergies).split(/,|;/).map(s => s.trim()).filter(Boolean) : []); return cur.length ? h('div', { class: 'chips' }, cur.map(x => h('span', { class: 'chip', style: { background: 'var(--gold-soft)', color: '#7A5200', fontWeight: 700 } }, x))) : h('p', { class: 'muted small' }, 'No known allergies'); })(),
          h('p', { class: 'muted small mt' }, `Medications (self-reported): ${u.currentMedications || '—'}`), h('p', { class: 'muted small' }, `Surgeries: ${u.previousSurgeries || '—'}`)),
        card(cardHead('Tasks & reminders', can('chart') ? btn('New task', () => quickTask(uid, memberName(u)), { size: 'btn-sm' }) : null),
          myTasks.length ? h('div', { class: 'list' }, myTasks.map(t => h('div', { class: 'list-item' }, h('div', { class: 'grow' }, h('b', null, t.title), h('span', null, `${t.assignedToName || 'Unassigned'}${t.due ? ' · due ' + fmtDate(t.due) : ''}`)), can('chart') ? btn('Done', async () => { await updateTask(t.id, { status: 'done', doneBy: session.user.uid }); location.reload(); }, { size: 'btn-sm', variant: 'btn-success' }) : null))) : h('p', { class: 'muted small' }, 'No open tasks'),
          reminders.filter(r => !r.fired).length ? h('div', { class: 'mt' }, h('div', { class: 'small muted', style: { fontWeight: 700 } }, 'SCHEDULED PUSHES'), reminders.filter(r => !r.fired).map(r => h('div', { class: 'small' }, `${fmtDateTime(r.fireAt)} · ${r.title}`))) : null)),
      card(cardHead('Timeline'),"""
rep("      card(cardHead('Timeline'),", SUMMARY_EXTRA)

rep("  async vitals({ u, uid, vitals }) {\n    const types =",
    "  async vitals({ u, uid, vitals }) {\n    const labs = await labResultsFor(uid).catch(() => []);\n    const types =")

LABS = r"""], vitals, { empty: 'No vitals recorded' })),
      card(cardHead('Lab results', can('chart') ? btn('Enter result', () => { const f = { test: input({ placeholder: 'Test name' }), value: input({ placeholder: 'Value' }), unit: input({ placeholder: 'Unit' }), ref: input({ placeholder: 'Reference range' }), flag: select([['normal', 'Normal'], ['abnormal', 'Abnormal'], ['critical', 'Critical']], 'normal'), collected: input({ type: 'date', value: new Date().toISOString().slice(0, 10) }), notes: textarea({ rows: 2, placeholder: 'Interpretation / notes shared with the patient' }) }; const m = modal('Enter lab result', h('div', { class: 'col' }, field('Common tests', chips(CHIPS.labs, null, v => f.test.value = v)), h('div', { class: 'form-grid' }, field('Test', f.test), field('Value', f.value), field('Unit', f.unit), field('Reference range', f.ref), field('Flag', f.flag), field('Collected', f.collected)), field('Notes', f.notes)), [btn('Cancel', () => m.close()), btn('Save', async () => { if (!f.test.value.trim()) return; try { await addLabResult(uid, { testName: f.test.value.trim(), value: f.value.value.trim(), unit: f.unit.value.trim(), referenceRange: f.ref.value.trim(), flag: f.flag.value, collectedAt: Timestamp.fromDate(new Date(f.collected.value)), notes: f.notes.value.trim() }); if (f.flag.value !== 'normal') await notifyMember(uid, { type: 'system', title: 'New lab result', body: `${f.test.value.trim()} is ready. Your care team will follow up.`, route: 'careRecords' }); toast('Saved', 'success'); m.close(); location.reload(); } catch (e) { errorToast(e); } }, { variant: 'btn-primary' })]); }, { variant: 'btn-primary', size: 'btn-sm' }) : null),
        table([{ label: 'Resulted', render: l => fmtDate(l.resultedAt) }, { label: 'Test', render: l => h('b', null, l.testName) }, { label: 'Result', render: l => `${l.value} ${l.unit || ''}` }, { label: 'Reference', key: 'referenceRange' }, { label: 'Flag', render: l => badge(l.flag === 'critical' ? 'failed' : l.flag === 'abnormal' ? 'pending' : 'active', l.flag || 'normal') }, { label: 'Entered by', key: 'enteredByName' }, { label: 'Notes', key: 'notes' }], labs, { empty: 'No lab results entered. Attach the PDF under Documents and enter key values here.' })));
  },"""
rep("], vitals, { empty: 'No vitals recorded' })));\n  },", LABS)

ADDENDA = r"""    signed ? card(cardHead('Addenda', can('chart') ? btn('Add addendum', async () => { const txt = await prompt('Addendum', 'Appended to the signed note with your name and time', { multiline: true, okLabel: 'Append' }); if (!txt) return; try { await addAddendum(uid, note.id, txt); toast('Addendum added', 'success'); location.reload(); } catch (e) { errorToast(e); } }, { size: 'btn-sm' }) : null), (d.addenda || []).length ? h('div', { class: 'timeline' }, d.addenda.map(a => h('div', { class: 'tl-item blue' }, h('div', { class: 'tl-when' }, `${a.by} · ${fmtDateTime(a.at)}`), h('div', { class: 'tl-body' }, a.text)))) : h('p', { class: 'muted small' }, 'Signed notes are locked. Corrections go here as addenda.')) : null,
    card(cardHead('Visit'), h('div', { class: 'form-grid' }, field('Patient', F.patient),"""
rep("    card(cardHead('Visit'), h('div', { class: 'form-grid' }, field('Patient', F.patient),", ADDENDA)

p.write_text(t, encoding="utf-8", newline="\n")
print("chart patched")
