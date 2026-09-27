// Ambient scribe: drafts a SOAP note from a visit transcript with Claude.
// Transcription happens in the browser (Web Speech API), so no audio reaches the server.
// Set the key once: firebase functions:secrets:set ANTHROPIC_API_KEY
const functions = require('firebase-functions/v1');
const admin = require('firebase-admin');
if (!admin.apps.length) admin.initializeApp();

const MODEL = 'claude-sonnet-5';

async function assertStaff(context) {
  if (!context.auth) throw new functions.https.HttpsError('unauthenticated', 'Sign in required');
  const s = await admin.firestore().doc(`staff/${context.auth.uid}`).get();
  if (!s.exists || s.data().active === false || !['superadmin', 'clinician'].includes(s.data().role)) throw new functions.https.HttpsError('permission-denied', 'Clinician role required');
  return s.data();
}

const SYSTEM = `You are a clinical documentation assistant for a primary and urgent care clinic. From a visit transcript, produce a concise, factual SOAP note.
Rules: never invent findings, vitals, or history that were not stated; if something is unclear, say so in confidenceNotes. Use plain clinical language. Do not include the patient's name in any field.
Respond with ONLY a JSON object, no prose, with these keys:
chiefComplaint (string), hpi (string), exam (string), assessment (array of {label, icdCode}), plan (string), patientInstructions (string, written to the patient in plain English), redFlags (array of strings), followUp (string), medications (array of {medicationName, dosage, frequency, duration, instructions}), labs (array of strings), confidenceNotes (array of strings).`;

exports.scribe = functions.runWith({ timeoutSeconds: 120, memory: '512MB', secrets: ['ANTHROPIC_API_KEY'] }).https.onCall(async (data, context) => {
  const staff = await assertStaff(context);
  const key = process.env.ANTHROPIC_API_KEY; if (!key) throw new functions.https.HttpsError('failed-precondition', 'ANTHROPIC_API_KEY secret is not set');
  const { transcript, patientName, visitType, reason } = data || {};
  if (!transcript || String(transcript).trim().length < 20) throw new functions.https.HttpsError('invalid-argument', 'Transcript is too short');
  const user = `Visit type: ${visitType || 'unknown'}. Stated reason for visit: ${reason || 'unknown'}.\n\nTranscript (clinician and patient, unlabeled):\n${String(transcript).slice(0, 60000)}`;
  const r = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: { 'x-api-key': key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json' },
    body: JSON.stringify({ model: MODEL, max_tokens: 2500, temperature: 0.2, system: SYSTEM, messages: [{ role: 'user', content: user }] }),
  });
  if (!r.ok) throw new functions.https.HttpsError('internal', `Claude request failed: ${r.status} ${await r.text()}`);
  const j = await r.json();
  const text = (j.content || []).map(c => c.text || '').join('');
  let draft = {};
  try { draft = JSON.parse(text.slice(text.indexOf('{'), text.lastIndexOf('}') + 1)); } catch (e) { throw new functions.https.HttpsError('internal', 'Could not parse the draft'); }
  await admin.firestore().collection('audit_logs').add({ action: 'scribe.server', target: 'scribe', staffId: context.auth.uid, staffEmail: context.auth.token.email || null, role: staff.role, at: admin.firestore.FieldValue.serverTimestamp(), meta: { chars: String(transcript).length, model: MODEL, inputTokens: j.usage?.input_tokens || null, outputTokens: j.usage?.output_tokens || null } });
  return { draft, model: MODEL };
});
