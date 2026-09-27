"""Scribe: browser speech recognition for the transcript, Claude for the draft."""
import pathlib, shutil
R = pathlib.Path(__file__).resolve().parent.parent

# data2: replace the upload-based call with a transcript-based one
p = R / "assets/js/data2.js"; t = p.read_text(encoding="utf-8")
old_start = t.index("// ── Ambient scribe (functions/scribe.js)")
t = t[:old_start] + """// ── Ambient scribe (functions/scribe.js, Claude) ────────────────────────
export async function draftFromTranscript({ transcript, patientName, visitType, reason }) {
  const fn = httpsCallable(functions, 'scribe', { timeout: 120000 }); const res = await fn({ transcript, patientName, visitType, reason });
  await audit('scribe.run', 'scribe', { chars: transcript.length, model: res.data?.model || null }); return res.data;
}
"""
p.write_text(t, encoding="utf-8", newline="\n"); print("data2 ok")

# chart: swap MediaRecorder flow for SpeechRecognition + transcript box
p = R / "assets/js/pages/ehr/chart.js"; t = p.read_text(encoding="utf-8")
def rep(a, b):
    global t
    assert t.count(a) == 1, (a[:80], t.count(a)); t = t.replace(a, b)
rep("transcribeAndDraft, createOrder", "draftFromTranscript, createOrder")
start = t.index("  // Ambient scribe: record in the browser, transcribe + draft on the server, then fill empty sections.")
end = t.index("  let pain = S.vitals.painScale != null")
NEW = r"""  // Ambient scribe: the browser transcribes live (Web Speech API, nothing leaves the device); Claude drafts the note from the transcript.
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition; let rec = null, recStart = 0, finalText = d.transcript || '';
  const transcriptBox = textarea({ value: finalText, rows: 4, placeholder: SR ? 'Live transcript appears here. You can also paste or type a transcript, then click Draft note.' : 'This browser has no speech recognition (use Chrome, Edge, or Safari). Paste or type the transcript here, then click Draft note.', disabled: ro });
  const scribeBtn = btn(SR ? 'Start listening' : 'No mic transcription here', null, { size: 'btn-sm', variant: 'btn-accent', disabled: ro || !SR });
  const draftBtn = btn('Draft note with Claude', null, { size: 'btn-sm', variant: 'btn-primary', disabled: ro });
  const scribeStatus = h('span', { class: 'muted small' }, 'Tell the patient the visit is being transcribed and get their consent first.');
  const applyDraft = (dr) => {
    const put = (el, v) => { if (v && !el.value.trim()) el.value = v; }; put(F.cc, dr.chiefComplaint); put(F.hpi, dr.hpi); put(F.exam, dr.exam); put(F.plan, dr.plan); put(F.instr, dr.patientInstructions); if (dr.followUp) F.plan.value += (F.plan.value ? '\n' : '') + 'Follow-up: ' + dr.followUp; if (Array.isArray(dr.redFlags) && dr.redFlags.length && !F.redFlags.value) F.redFlags.value = dr.redFlags.join(', ');
    for (const a of dr.assessment || []) if (a.label && !S.diagnoses.find(x => x.label === a.label)) S.diagnoses.push({ label: a.label, icdCode: a.icdCode || '', isPrimary: !S.diagnoses.length, notes: 'scribe' }); drawDx();
    for (const m of dr.medications || []) if (m.medicationName && !S.prescriptions.find(x => x.medicationName === m.medicationName)) S.prescriptions.push({ medicationName: m.medicationName, dosage: m.dosage || '', frequency: m.frequency || '', duration: m.duration || '', refillsRemaining: 0, instructions: m.instructions || '', reason: '', prescribedAt: Timestamp.now(), prescriber: session.staff?.name || '', status: 'draft', _createRx: false }); drawRx();
    for (const l of dr.labs || []) if (!S.labOrders.find(x => x.name === l)) S.labOrders.push({ name: l, status: 'ordered', orderedAt: Timestamp.now(), orderedBy: session.staff?.name || '' }); drawLabs();
    scribeStatus.textContent = 'Draft filled into empty sections. Review every section before signing.' + ((dr.confidenceNotes || []).length ? ' Uncertain: ' + dr.confidenceNotes.join('; ') : '');
  };
  draftBtn.addEventListener('click', async () => { const tx = transcriptBox.value.trim(); if (tx.length < 20) return toast('Transcript is too short', 'error'); draftBtn.disabled = true; draftBtn.replaceChildren('Drafting…'); scribeStatus.textContent = 'Claude is drafting the note…'; try { const res = await draftFromTranscript({ transcript: tx, patientName: F.patient.value, visitType: F.type.value, reason: F.cc.value }); S.transcript = tx; applyDraft(res.draft || {}); toast('Draft ready. Review before signing.', 'success', 6000); } catch (e) { errorToast(e); scribeStatus.textContent = 'Draft failed: ' + (e.message || ''); } draftBtn.disabled = false; draftBtn.replaceChildren('Draft note with Claude'); });
  if (SR) scribeBtn.addEventListener('click', () => {
    if (rec) { rec.stop(); return; }
    rec = new SR(); rec.continuous = true; rec.interimResults = true; rec.lang = 'en-US'; recStart = Date.now(); let interim = '';
    rec.onresult = e => { interim = ''; for (let i = e.resultIndex; i < e.results.length; i++) { const r = e.results[i]; if (r.isFinal) finalText += (finalText.endsWith(' ') || !finalText ? '' : ' ') + r[0].transcript.trim() + ' '; else interim += r[0].transcript; } transcriptBox.value = finalText + (interim ? ' ' + interim : ''); transcriptBox.scrollTop = transcriptBox.scrollHeight; };
    rec.onerror = e => { if (e.error !== 'no-speech') { errorToast(new Error('Speech recognition: ' + e.error)); } };
    rec.onend = () => { if (rec && rec._keep) { try { rec.start(); return; } catch {} } rec = null; scribeBtn.replaceChildren('Start listening'); scribeStatus.textContent = `Stopped after ${Math.round((Date.now() - recStart) / 1000)} s. Click Draft note with Claude when ready.`; S.transcript = finalText; };
    rec._keep = true; rec.start(); scribeBtn.replaceChildren(h('span', { class: 'scribe-rec' }, h('span', { class: 'dot' }), 'Stop listening')); scribeStatus.textContent = 'Listening. Speak naturally; the transcript builds below.';
    scribeBtn.onclick = null;
    scribeBtn.addEventListener('click', () => { if (rec) { rec._keep = false; rec.stop(); } }, { once: true });
  });
"""
t = t[:start] + NEW + t[end:]
rep("    !ro ? card(cardHead('Documentation assist'), h('div', { class: 'row' }, tplSel, scribeBtn, scribeStatus), h('p', { class: 'small muted mt' }, 'Smart phrases: type a key such as .rtc, .er, .ros, .consent at the end of any field.')) : null,",
    "    !ro ? card(cardHead('Documentation assist'), h('div', { class: 'row' }, tplSel, scribeBtn, draftBtn, scribeStatus), h('div', { class: 'mt' }, transcriptBox), h('p', { class: 'small muted mt' }, 'Smart phrases: type a key such as .rtc, .er, .ros, .consent at the end of any field.')) : null,")
p.write_text(t, encoding="utf-8", newline="\n"); print("chart ok")

# README + kurv-functions copy
r = R / "README.md"; s = r.read_text(encoding="utf-8")
s = s.replace("- Ambient scribe: browser records, `functions/scribe.js` transcribes (gpt-4o-transcribe) and drafts SOAP JSON (gpt-4o-mini). Secret: `firebase functions:secrets:set OPENAI_API_KEY`.",
              "- Ambient scribe: the browser transcribes live with the Web Speech API (no audio leaves the device); `functions/scribe.js` drafts SOAP JSON with Claude (`claude-sonnet-5`). Secret: `firebase functions:secrets:set ANTHROPIC_API_KEY`.")
r.write_text(s, encoding="utf-8", newline="\n")
shutil.copy(R / "functions/scribe.js", "C:/Users/kurvh/kurv-functions/scribe.js")
print("readme + functions copy ok")
