// Fax via Phaxio (swap the adapter for SRFax/Documo if preferred).
// Secrets: PHAXIO_KEY, PHAXIO_SECRET, PHAXIO_WEBHOOK_TOKEN. Inbound faxes land in fax_inbox for filing to a chart.
const functions = require('firebase-functions/v1');
const admin = require('firebase-admin');
if (!admin.apps.length) admin.initializeApp();
const db = () => admin.firestore();
// Secrets are created with the placeholder 'pending' before vendor credentials exist.
const cfg = name => { const v = process.env[name]; return v && v !== 'pending' ? v : ''; };

exports.sendFax = functions.runWith({ secrets: ['PHAXIO_KEY', 'PHAXIO_SECRET'] }).https.onCall(async (data, context) => {
  if (!context.auth) throw new functions.https.HttpsError('unauthenticated', 'Sign in required');
  const s = await db().doc(`staff/${context.auth.uid}`).get(); if (!s.exists) throw new functions.https.HttpsError('permission-denied', 'Staff only');
  const ref = db().doc(`fax_outbox/${data.faxId}`); const snap = await ref.get(); if (!snap.exists) throw new functions.https.HttpsError('not-found', 'Fax not found');
  const fax = snap.data();
  const key = cfg('PHAXIO_KEY'), secret = cfg('PHAXIO_SECRET');
  if (!key || !secret) { await ref.update({ status: 'queued', lastError: 'PHAXIO_KEY / PHAXIO_SECRET not configured' }); return { queued: true, message: 'Fax vendor not configured yet' }; }
  const form = new FormData(); form.append('to', fax.to); form.append('content_url[]', fax.fileUrl); if (fax.subject) form.append('header_text', fax.subject.slice(0, 50));
  const r = await fetch('https://api.phaxio.com/v2.1/faxes', { method: 'POST', headers: { Authorization: 'Basic ' + Buffer.from(`${key}:${secret}`).toString('base64') }, body: form });
  const j = await r.json().catch(() => ({}));
  if (!r.ok || !j.success) { await ref.update({ status: 'error', lastError: j.message || `HTTP ${r.status}` }); throw new functions.https.HttpsError('internal', j.message || 'Fax send failed'); }
  await ref.update({ status: 'sent', vendorRef: String(j.data?.id || ''), sentAt: admin.firestore.FieldValue.serverTimestamp() });
  return { ok: true, id: j.data?.id };
});

exports.faxInboundWebhook = functions.runWith({ secrets: ['PHAXIO_WEBHOOK_TOKEN'] }).https.onRequest(async (req, res) => {
  if (req.method !== 'POST') return res.status(405).send('POST only');
  const token = req.query.token || req.get('x-webhook-token');
  if (!cfg('PHAXIO_WEBHOOK_TOKEN') || token !== cfg('PHAXIO_WEBHOOK_TOKEN')) return res.status(401).send('bad token');
  const b = req.body || {}; const fax = typeof b.fax === 'string' ? JSON.parse(b.fax) : (b.fax || b);
  // Phaxio posts multipart with the PDF as `filename`; when using content URLs store the file yourself. Here we store metadata plus the URL if provided.
  await db().collection('fax_inbox').add({ vendorRef: String(fax.id || ''), from: fax.from_number || fax.from || '', to: fax.to_number || fax.to || '', pages: fax.num_pages || null, fileUrl: b.fileUrl || fax.fileUrl || '', fileName: `fax-${fax.id || Date.now()}.pdf`, subject: fax.caller_name || '', status: 'new', receivedAt: admin.firestore.FieldValue.serverTimestamp() });
  res.json({ ok: true });
});
