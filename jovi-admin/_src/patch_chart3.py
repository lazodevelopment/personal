"""Chart: templates + smart phrases, ambient scribe, orders (Rx/lab), coverage & settle, AVS on sign,
intake/consent card, chart-view audit, access report tab."""
import pathlib
p = pathlib.Path(__file__).resolve().parent.parent / "assets/js/pages/ehr/chart.js"
t = p.read_text(encoding="utf-8")
assert "transcribeAndDraft" not in t, "already patched"
def rep(a, b):
    global t
    assert t.count(a) == 1, (a[:80], t.count(a)); t = t.replace(a, b)

rep("problemsFor, addProblem, updateProblem, setAllergies, labResultsFor, addLabResult, addAddendum, tasks, updateTask, remindersFor } from '../../data.js';",
    "problemsFor, addProblem, updateProblem, setAllergies, labResultsFor, addLabResult, addAddendum, tasks, updateTask, remindersFor, noteTemplates, smartPhrases, attachPhrases, transcribeAndDraft, createOrder, transmitOrder, ordersFor, LAB_PANELS, LAB_VENDORS, coverageSnapshot, settleVisit, logChartView, accessReportFor, pharmacies } from '../../data.js';\nimport { intakeSummaryCard, captureConsent } from '../../intake.js';")

# audit every chart open + access report tab
rep("  const wrap = h('div', { class: 'chart-grid' }); const main = h('div'); let tab = sub === 'encounter' || sub === 'note' ? 'encounters' : (sub || 'summary');",
    "  logChartView(uid, sub || 'summary');\n  const wrap = h('div', { class: 'chart-grid' }); const main = h('div'); let tab = sub === 'encounter' || sub === 'note' ? 'encounters' : (sub || 'summary');")
rep("['symptom', 'Symptom checks'], ['documents', 'Documents']];",
    "['symptom', 'Symptom checks'], ['documents', 'Documents'], ['orders', 'Orders'], ['access', 'Access log']];")

# Orders tab + access report tab
rep("  async documents({ uid, notes }) {",
    """  async orders({ uid }) {
    const rows = await ordersFor(uid);
    return card(cardHead('Orders for this patient', can('chart') ? h('div', { class: 'row' }, btn('Lab order', () => navigate(`/ehr/chart/${uid}/encounter/new`), { size: 'btn-sm' }), btn('Queue', () => navigate('/ehr/orders'), { size: 'btn-sm', variant: 'btn-ghost' })) : null),
      table([{ label: 'Signed', render: o => fmtDateTime(o.createdAt) }, { label: 'Kind', render: o => badge('info', o.kind === 'rx' ? 'Rx · Surescripts' : `Lab · ${o.vendor}`) }, { label: 'Order', render: o => o.kind === 'rx' ? `${o.medication?.medicationName || ''} ${o.medication?.dosage || ''} · ${o.medication?.instructions || ''}` : (o.tests || []).join(', ') }, { label: 'Status', render: o => h('div', null, badge(o.status === 'queued' ? 'pending' : o.status === 'error' ? 'failed' : o.status), o.lastMessage ? h('div', { class: 'small muted' }, o.lastMessage) : null) }, { label: 'By', key: 'orderedByName' }], rows, { empty: 'No electronic orders yet. Orders are created from an encounter note.' }));
  },
  async access({ uid }) {
    const rows = await accessReportFor(uid);
    return card(cardHead('Who accessed this chart'), h('p', { class: 'muted small mb' }, 'Every open, edit, and order on this record. Give this report to the patient on request.'), table([{ label: 'When', render: r => fmtDateTime(r.at) }, { label: 'Staff', render: r => `${r.staffEmail || r.staffId} · ${r.role || ''}` }, { label: 'Action', render: r => badge(/view/.test(r.action) ? 'info' : /delete|deny|reject/.test(r.action) ? 'failed' : 'active', r.action) }, { label: 'Detail', render: r => h('span', { class: 'small muted' }, Object.entries(r.meta || {}).map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : v}`).join(' · ')) }], rows, { empty: 'No access recorded yet' }));
  },
  async documents({ uid, notes }) {""")

# ── Note editor upgrades ─────────────────────────────────────────────
rep("  const d = note || {};\n  const signed = !!d.signedAt; const ro = signed || !can('chart');",
    "  const d = note || {};\n  const signed = !!d.signedAt; const ro = signed || !can('chart');\n  const [templates, phrases, partnerPharmacies] = await Promise.all([noteTemplates().catch(() => []), smartPhrases().catch(() => []), pharmacies().catch(() => [])]);\n  const cov = coverageSnapshot(u);")

# smart phrases on all textareas + template picker + scribe
rep("  let pain = S.vitals.painScale != null ? String(S.vitals.painScale) : null, dispo = S.followUp.nextAppointmentRecommendation || null;",
    """  [F.hpi, F.exam, F.edu, F.plan, F.instr].forEach(ta => attachPhrases(ta, phrases));
  const tplSel = select([['', 'Apply a template…'], ...templates.map(x => [x.id, `${x.name} (${x.visitType})`])], '', { disabled: ro });
  tplSel.addEventListener('change', () => { const x = templates.find(z => z.id === tplSel.value); if (!x) return; const fill = (el, v) => { if (!el.value.trim() || confirm('Replace existing text in this section?')) el.value = String(v || '').replace('{reason}', F.cc.value.trim() || 'the stated reason'); }; fill(F.hpi, x.hpi); fill(F.exam, x.exam); fill(F.plan, x.plan); fill(F.edu, x.edu); if (x.visitType && [...F.type.options].some(o => o.value === x.visitType)) F.type.value = x.visitType; tplSel.value = ''; });
  // Ambient scribe: record in the browser, transcribe + draft on the server, then fill empty sections.
  let rec = null, chunks = [], recStart = 0; const scribeBtn = btn('Start ambient scribe', null, { size: 'btn-sm', variant: 'btn-accent', disabled: ro }); const scribeStatus = h('span', { class: 'muted small' }, 'Records the visit with the patient\\u2019s consent and drafts the note.');
  scribeBtn.addEventListener('click', async () => {
    if (rec && rec.state === 'recording') { rec.stop(); return; }
    try { const stream = await navigator.mediaDevices.getUserMedia({ audio: true }); chunks = []; rec = new MediaRecorder(stream, { mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/webm' }); recStart = Date.now();
      rec.ondataavailable = e => { if (e.data.size) chunks.push(e.data); };
      rec.onstop = async () => { stream.getTracks().forEach(tr => tr.stop()); scribeBtn.replaceChildren('Transcribing…'); scribeBtn.disabled = true; scribeStatus.textContent = 'Uploading and drafting. This takes about as long as a third of the recording.';
        try { const blob = new Blob(chunks, { type: 'audio/webm' }); const res = await transcribeAndDraft({ audioBlob: blob, patientName: F.patient.value, visitType: F.type.value, reason: F.cc.value }); const dr = res.draft || {};
          const put = (el, v) => { if (v && !el.value.trim()) el.value = v; }; put(F.cc, dr.chiefComplaint); put(F.hpi, dr.hpi); put(F.exam, dr.exam); put(F.plan, dr.plan); put(F.instr, dr.patientInstructions); if (dr.followUp) F.plan.value += (F.plan.value ? '\\n' : '') + 'Follow-up: ' + dr.followUp; if (Array.isArray(dr.redFlags) && dr.redFlags.length && !F.redFlags.value) F.redFlags.value = dr.redFlags.join(', ');
          for (const a of dr.assessment || []) if (a.label && !S.diagnoses.find(x => x.label === a.label)) S.diagnoses.push({ label: a.label, icdCode: a.icdCode || '', isPrimary: !S.diagnoses.length, notes: 'scribe' }); drawDx();
          for (const m of dr.medications || []) if (m.medicationName) S.prescriptions.push({ medicationName: m.medicationName, dosage: m.dosage || '', frequency: m.frequency || '', duration: m.duration || '', refillsRemaining: 0, instructions: m.instructions || '', reason: '', prescribedAt: Timestamp.now(), prescriber: session.staff?.name || '', status: 'draft', _createRx: false }); drawRx();
          for (const l of dr.labs || []) if (!S.labOrders.find(x => x.name === l)) S.labOrders.push({ name: l, status: 'ordered', orderedAt: Timestamp.now(), orderedBy: session.staff?.name || '' }); drawLabs();
          S.transcript = res.transcript || ''; scribeStatus.textContent = `Draft filled from ${Math.round((Date.now() - recStart) / 1000)} s of audio. Review every section before signing.` + ((dr.confidenceNotes || []).length ? ' Uncertain: ' + dr.confidenceNotes.join('; ') : ''); toast('Draft ready. Review before signing.', 'success', 6000);
        } catch (e) { errorToast(e); scribeStatus.textContent = 'Scribe failed: ' + (e.message || ''); }
        scribeBtn.replaceChildren('Start ambient scribe'); scribeBtn.disabled = false; };
      rec.start(1000); scribeBtn.replaceChildren(h('span', { class: 'scribe-rec' }, h('span', { class: 'dot' }), 'Stop recording')); scribeStatus.textContent = 'Recording. Say the patient consented on the recording.';
    } catch (e) { errorToast(e, 'Microphone access is required'); }
  });
  let pain = S.vitals.painScale != null ? String(S.vitals.painScale) : null, dispo = S.followUp.nextAppointmentRecommendation || null;""")

# prescriptions: option to send electronically; labs: vendor + sign order
rep("instr: input({ placeholder: 'Sig / instructions' }), reason: input({ placeholder: 'Indication' }), send: checkbox('Also create a prescription the member can refill from the app', true) };",
    "instr: input({ placeholder: 'Sig / instructions' }), reason: input({ placeholder: 'Indication' }), qty: input({ type: 'number', placeholder: 'Qty', value: 30 }), send: checkbox('Also create a prescription the member can refill from the app', true), erx: checkbox('Send electronically to the pharmacy (Surescripts)', true), subs: checkbox('Substitutions allowed', true), pharm: select([['', u.preferredPharmacyName || u.preferredPharmacyPlace?.name ? `Patient\\u2019s pharmacy: ${u.preferredPharmacyName || u.preferredPharmacyPlace?.name}` : 'Pharmacy on file'], ...partnerPharmacies.map(x => [x.id, x.name])], '') };")
rep("field('Frequency shortcuts', chips(CHIPS.rxFreq, null, v => f.freq.value = v)), field('Instructions', f.instr), f.send), [",
    "field('Frequency shortcuts', chips(CHIPS.rxFreq, null, v => f.freq.value = v)), field('Instructions', f.instr), h('div', { class: 'form-grid' }, field('Quantity', f.qty), field('Pharmacy', f.pharm)), f.subs, f.erx, f.send), [")
rep("instructions: f.instr.value.trim(), reason: f.reason.value.trim(), prescribedAt: Timestamp.now(), prescriber: session.staff?.name || '', status: 'active', _createRx: f.send.querySelector('input').checked }); drawRx(); m.close(); }, { variant: 'btn-primary' })]); };",
    "instructions: f.instr.value.trim(), reason: f.reason.value.trim(), prescribedAt: Timestamp.now(), prescriber: session.staff?.name || '', status: 'active', _createRx: f.send.querySelector('input').checked, _erx: f.erx.querySelector('input').checked, _qty: Number(f.qty.value) || null, _subs: f.subs.querySelector('input').checked, _pharmacyId: f.pharm.value || null }); drawRx(); m.close(); }, { variant: 'btn-primary' })]); };")
rep("  const drawLabs = () => labList.replaceChildren(...CHIPS.labs.map(",
    "  const labVendor = select(LAB_VENDORS, d.labVendor || 'labcorp', { disabled: ro }); const labPriority = select([['routine', 'Routine'], ['stat', 'STAT']], 'routine', { disabled: ro }); const labMore = select([['', 'Add a panel…'], ...LAB_PANELS.map(x => [x, x])], '', { disabled: ro }); labMore.addEventListener('change', () => { if (labMore.value && !S.labOrders.find(x => x.name === labMore.value)) S.labOrders.push({ name: labMore.value, status: 'ordered', orderedAt: Timestamp.now(), orderedBy: session.staff?.name || '' }); labMore.value = ''; drawLabs(); });\n  const drawLabs = () => labList.replaceChildren(...[...new Set([...CHIPS.labs, ...S.labOrders.map(x => x.name)])].map(")
rep("    card(cardHead('Orders · labs'), labList, S.labOrders.some(l => l.status !== 'ordered') ? h('p', { class: 'small muted mt' }, 'Result summaries can be added after signing by attaching the lab report under Documents.') : null),",
    "    card(cardHead('Orders · labs', h('div', { class: 'row' }, labVendor, labPriority)), labList, h('div', { class: 'mt' }, labMore), h('p', { class: 'small muted mt' }, 'Selected tests become one electronic lab order to the chosen lab when you sign. Results come back to Orders & results for review.')),")

# collect: persist transcript, lab vendor
rep("attachments: S.attachments, bodyMarks: bodyMarks.map(m => ({ ...m })) }; };",
    "attachments: S.attachments, bodyMarks: bodyMarks.map(m => ({ ...m })), labVendor: labVendor.value, labPriority: labPriority.value, transcript: S.transcript || d.transcript || null }; };")

# save: on sign create orders (rx + lab), AVS notification, settle visit
rep("      if (sign && req && req.statusL !== 'completed') await completeRequest(req.id, { linkedVisitRecordId: id, providerName: data.providerName });",
    """      if (sign) {
        const patient = { name: data.patientName, dob: memberDob(u) || null, sex: u.gender || u.onboard_gender || null, phone: u.phone || u.onboard_phone || null, address: [u.address || u.onboard_address, u.city, u.state, u.zip].filter(Boolean).join(', ') };
        for (const p of S.prescriptions) if (p._erx) { const ph = partnerPharmacies.find(x => x.id === p._pharmacyId); const oid = await createOrder({ kind: 'rx', userId: uid, patientName: data.patientName, patient, visitRecordId: id, medication: { medicationName: p.medicationName, dosage: p.dosage, form: p.form || '', frequency: p.frequency, duration: p.duration, instructions: p.instructions, quantity: p._qty, refills: p.refillsRemaining, daysSupply: 30, substitutionsAllowed: p._subs !== false }, pharmacy: ph ? { id: ph.id, name: ph.name, phone: ph.phone || '', address: typeof ph.address === 'string' ? ph.address : '' } : (u.preferredPharmacyPlace ? { name: u.preferredPharmacyPlace.name, phone: u.preferredPharmacyPlace.phone || '', address: u.preferredPharmacyPlace.address || '' } : { name: u.preferredPharmacyName || '', id: u.preferredPharmacy || null }), notes: '' }); transmitOrder(oid).catch(() => {}); p._erx = false; }
        if (S.labOrders.length && !d.labOrderId) { const oid = await createOrder({ kind: 'lab', vendor: labVendor.value, userId: uid, patientName: data.patientName, patient, visitRecordId: id, tests: S.labOrders.map(l => l.name), diagnoses: S.diagnoses.map(x => x.icdCode || x.label).filter(Boolean), priority: labPriority.value, notes: '' }); transmitOrder(oid).catch(() => {}); saveVisitRecord(uid, id, { labOrderId: oid }).catch(() => {}); }
        await settleVisit(uid, { visitRecordId: id, totalCharged: data.billing.totalCharged, memberShare: data.billing.memberShare, description: `${data.type} visit · ${data.providerName}` }).catch(() => {});
        await notifyMember(uid, { type: 'appointment', title: 'Your visit summary is ready', body: `${data.providerName} signed your note${data.followUp.summary ? ': ' + data.followUp.summary.slice(0, 100) : ''}. Open Care Records for your plan and instructions.`, route: 'careRecords', refPath: `users/${uid}/visit_records/${id}` }).catch(() => {});
      }
      if (sign && req && req.statusL !== 'completed') await completeRequest(req.id, { linkedVisitRecordId: id, providerName: data.providerName });""")

# header: template + scribe row; intake card; coverage in billing
rep("    card(cardHead('Visit'), h('div', { class: 'form-grid' }, field('Patient', F.patient),",
    "    !ro ? card(cardHead('Documentation assist'), h('div', { class: 'row' }, tplSel, scribeBtn, scribeStatus), h('p', { class: 'small muted mt' }, 'Smart phrases: type a key such as .rtc, .er, .ros, .consent at the end of any field.')) : null,\n    await intakeSummaryCard(uid, F.patient.value, req?.id || d.appointmentId || null, !ro),\n    card(cardHead('Visit'), h('div', { class: 'form-grid' }, field('Patient', F.patient),")
rep("card(cardHead('Billing for this visit'), h('div', { class: 'form-grid' }, field('Total charged', F.charge), field('Member share ($0 at Jovi Clinics)', F.share)))),",
    "card(cardHead('Billing & coverage', badge(cov.status)), h('div', { class: 'grid grid-3 mb' }, kv('Plan', `${cov.plan}${cov.dental ? ' · Dental' : ''}${cov.vision ? ' · Vision' : ''}`), kv('Deductible', `${money(cov.met)} of ${money(cov.deductible, { cents: false })} met`), kv('Remaining', money(cov.remaining))), h('div', { class: 'form-grid' }, field('Total charged', F.charge), field('Member share ($0 at Jovi Clinics)', F.share)), h('p', { class: 'small muted mt' }, 'Signing records the visit on the member\\u2019s statement and settles it instantly: no claim, no clearinghouse. Outside services are quoted before they happen.'))),")

p.write_text(t, encoding="utf-8", newline="\n")
print("chart patched")
