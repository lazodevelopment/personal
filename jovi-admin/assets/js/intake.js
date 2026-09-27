// Clinic-side intake questionnaire and consent capture with a signature pad (tablet friendly).
import { h, btn, input, select, field, modal, drawer, closeDrawer, toast, errorToast, kv, badge, fmtDateTime } from './ui.js';
import { CONSENT_TEXTS, INTAKE_QUESTIONS, saveConsent, saveIntake, consentsFor, intakeFor, requestIntake } from './data.js';

export function signaturePad({ width = 520, height = 180 } = {}) {
  const c = h('canvas', { width, height, style: { width: '100%', maxWidth: width + 'px', height: height + 'px', border: '1px dashed var(--ink-4)', borderRadius: '12px', background: '#fff', touchAction: 'none' } });
  const ctx = c.getContext('2d'); ctx.lineWidth = 2.4; ctx.lineCap = 'round'; ctx.strokeStyle = '#131B2E'; let drawing = false, empty = true;
  const pos = e => { const r = c.getBoundingClientRect(); return [(e.clientX - r.left) * (c.width / r.width), (e.clientY - r.top) * (c.height / r.height)]; };
  c.addEventListener('pointerdown', e => { drawing = true; c.setPointerCapture(e.pointerId); const [x, y] = pos(e); ctx.beginPath(); ctx.moveTo(x, y); });
  c.addEventListener('pointermove', e => { if (!drawing) return; const [x, y] = pos(e); ctx.lineTo(x, y); ctx.stroke(); empty = false; });
  c.addEventListener('pointerup', () => { drawing = false; }); c.addEventListener('pointercancel', () => { drawing = false; });
  const wrap = h('div', { class: 'col' }, c, h('div', { class: 'row' }, btn('Clear', () => { ctx.clearRect(0, 0, c.width, c.height); empty = true; }, { size: 'btn-sm' }), h('span', { class: 'muted small' }, 'Sign with a finger, stylus, or mouse')));
  wrap.isEmpty = () => empty; wrap.dataUrl = () => c.toDataURL('image/png');
  return wrap;
}

export async function captureConsent(uid, patientName, requestId = null) {
  const type = select(Object.entries(CONSENT_TEXTS).map(([k, v]) => [k, v.title]), 'treatment'); const text = h('p', { class: 'small', style: { background: 'var(--surface-2)', padding: '12px', borderRadius: '10px', lineHeight: 1.6 } }, CONSENT_TEXTS.treatment.text);
  type.addEventListener('change', () => { text.textContent = CONSENT_TEXTS[type.value].text; });
  const signer = input({ value: patientName }); const rel = select([['self', 'Self'], ['parent', 'Parent / guardian'], ['spouse', 'Spouse'], ['other', 'Other']], 'self'); const pad = signaturePad();
  const m = modal('Consent', h('div', { class: 'col' }, field('Document', type), text, h('div', { class: 'form-grid' }, field('Signer', signer), field('Relationship', rel)), field('Signature', pad)), [btn('Cancel', () => m.close()), btn('Save signed consent', async () => { if (pad.isEmpty()) return toast('Signature is required', 'error'); try { await saveConsent(uid, { type: type.value, title: CONSENT_TEXTS[type.value].title, text: CONSENT_TEXTS[type.value].text, signatureDataUrl: pad.dataUrl(), signerName: signer.value.trim(), relationship: rel.value, requestId }); toast('Consent saved', 'success'); m.close(); } catch (e) { errorToast(e); } }, { variant: 'btn-primary' })]);
  m.querySelector('.modal').style.width = 'min(640px,96vw)';
}

export async function runIntake(uid, patientName, requestId = null) {
  const answers = {}; const rows = INTAKE_QUESTIONS.map(([k, q, kind]) => { let el; if (kind === 'yesno') el = h('div', { class: 'chips' }, ['Yes', 'No'].map(v => h('button', { type: 'button', class: 'chip', onClick: e => { answers[k] = v; e.target.parentElement.querySelectorAll('.chip').forEach(c => c.classList.remove('on')); e.target.classList.add('on'); } }, v))); else if (kind === 'scale') el = h('div', { class: 'chips' }, Array.from({ length: 11 }, (_, i) => h('button', { type: 'button', class: 'chip', onClick: e => { answers[k] = i; e.target.parentElement.querySelectorAll('.chip').forEach(c => c.classList.remove('on')); e.target.classList.add('on'); } }, String(i)))); else { el = input({ placeholder: 'Type answer…', onInput: e => answers[k] = e.target.value }); } return field(q, el); });
  drawer(`Check-in · ${patientName}`, h('div', { class: 'col' }, h('p', { class: 'muted small' }, 'Hand the tablet to the patient or ask the questions aloud. PHQ-2 questions are included.'), ...rows, h('div', { class: 'row', style: { justifyContent: 'flex-end' } }, btn('Cancel', closeDrawer), btn('Save intake', async () => { try { await saveIntake(uid, answers, requestId); if (answers.moodLow === 'Yes' || answers.anhedonia === 'Yes') toast('PHQ-2 positive: consider PHQ-9', 'info', 6000); if (answers.safety === 'No') toast('Safety concern flagged: follow protocol', 'error', 8000); toast('Intake saved', 'success'); closeDrawer(); } catch (e) { errorToast(e); } }, { variant: 'btn-primary' }))));
}

export async function intakeSummaryCard(uid, patientName, requestId, canWrite) {
  const [consents, intakes] = await Promise.all([consentsFor(uid).catch(() => []), intakeFor(uid).catch(() => [])]);
  const latest = intakes[0];
  return h('div', { class: 'card' }, h('div', { class: 'card-head' }, h('h3', null, 'Check-in & consents'), canWrite ? h('div', { class: 'row' }, btn('Run intake', () => runIntake(uid, patientName, requestId), { size: 'btn-sm' }), btn('Capture consent', () => captureConsent(uid, patientName, requestId), { size: 'btn-sm' }), btn('Send to app', async () => { try { await requestIntake(uid, requestId); toast('Pre-visit check-in sent', 'success'); } catch (e) { errorToast(e); } }, { size: 'btn-sm', variant: 'btn-ghost' })) : null),
    latest ? h('div', { class: 'small' }, h('div', { class: 'muted' }, `Latest intake ${fmtDateTime(latest.createdAt)}`), ...Object.entries(latest.answers || {}).filter(([, v]) => v !== '' && v != null).map(([k, v]) => { const q = INTAKE_QUESTIONS.find(x => x[0] === k); return kv(q ? q[1] : k, String(v)); })) : h('p', { class: 'muted small' }, 'No intake on file'),
    h('div', { class: 'chips mt' }, consents.length ? consents.map(c => h('span', { class: 'chip on', title: `${c.signerName} · ${fmtDateTime(c.signedAt)}` }, c.title)) : h('span', { class: 'muted small' }, 'No signed consents')));
}
