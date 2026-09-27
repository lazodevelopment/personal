// Order transmission: e-prescriptions to Surescripts (via the certified vendor account) and
// lab orders to Labcorp / Quest. Each adapter is a thin function; wire real credentials with
// firebase functions:secrets:set and the vendor's endpoint. Until then orders queue with a clear reason.
const functions = require('firebase-functions/v1');
const admin = require('firebase-admin');
if (!admin.apps.length) admin.initializeApp();
const db = () => admin.firestore();
// Secrets are created with the placeholder 'pending' before vendor credentials exist.
const cfg = name => { const v = process.env[name]; return v && v !== 'pending' ? v : ''; };

const SECRETS = ['SURESCRIPTS_CLIENT_ID', 'SURESCRIPTS_CLIENT_SECRET', 'LABCORP_API_KEY', 'QUEST_API_KEY'];

async function assertStaff(context, roles = ['superadmin', 'clinician']) {
  if (!context.auth) throw new functions.https.HttpsError('unauthenticated', 'Sign in required');
  const s = await db().doc(`staff/${context.auth.uid}`).get();
  if (!s.exists || s.data().active === false || !roles.includes(s.data().role)) throw new functions.https.HttpsError('permission-denied', 'Clinician role required');
  return { id: s.id, ...s.data() };
}

// ── Adapters ────────────────────────────────────────────────────────────
// Each returns { ok, vendorRef?, message } and must never throw for a config gap.
const adapters = {
  async surescripts(order) {
    const id = cfg('SURESCRIPTS_CLIENT_ID'), secret = cfg('SURESCRIPTS_CLIENT_SECRET');
    if (!id || !secret) return { ok: false, message: 'Surescripts credentials not configured (SURESCRIPTS_CLIENT_ID / SURESCRIPTS_CLIENT_SECRET). Order queued.' };
    // NCPDP SCRIPT NewRx goes through the certified intermediary (e.g. DoseSpot / Veradigm). Build the message here:
    const payload = { messageType: 'NewRx', patient: order.patient, prescriber: { npi: order.orderedByNpi, name: order.orderedByName }, pharmacy: order.pharmacy, medication: order.medication, sig: order.medication?.instructions, quantity: order.medication?.quantity, refills: order.medication?.refills, daysSupply: order.medication?.daysSupply, substitutionsAllowed: order.medication?.substitutionsAllowed !== false, notes: order.notes || '' };
    // const res = await fetch(process.env.SURESCRIPTS_ENDPOINT, { method: 'POST', headers: {...}, body: JSON.stringify(payload) });
    return { ok: false, message: 'Surescripts endpoint not wired yet. Payload prepared.', payload };
  },
  async labcorp(order) {
    const key = cfg('LABCORP_API_KEY'); if (!key) return { ok: false, message: 'LABCORP_API_KEY not configured. Order queued.' };
    const payload = { orderingProvider: { npi: order.orderedByNpi, name: order.orderedByName }, patient: order.patient, tests: order.tests, diagnoses: order.diagnoses || [], specimen: order.specimen || 'to be collected', priority: order.priority || 'routine', accountNumber: process.env.LABCORP_ACCOUNT || '' };
    // HL7 v2 ORM^O01 or the Labcorp Link API; return the requisition id as vendorRef.
    return { ok: false, message: 'Labcorp endpoint not wired yet. Payload prepared.', payload };
  },
  async quest(order) {
    const key = cfg('QUEST_API_KEY'); if (!key) return { ok: false, message: 'QUEST_API_KEY not configured. Order queued.' };
    const payload = { orderingProvider: { npi: order.orderedByNpi, name: order.orderedByName }, patient: order.patient, tests: order.tests, diagnoses: order.diagnoses || [], priority: order.priority || 'routine', accountNumber: process.env.QUEST_ACCOUNT || '' };
    // Quest Quanum / Care360 order API or HL7 ORM; return the requisition id as vendorRef.
    return { ok: false, message: 'Quest endpoint not wired yet. Payload prepared.', payload };
  },
};

exports.transmitOrder = functions.runWith({ secrets: SECRETS }).https.onCall(async (data, context) => {
  const staff = await assertStaff(context);
  const ref = db().doc(`orders/${data.orderId}`); const snap = await ref.get();
  if (!snap.exists) throw new functions.https.HttpsError('not-found', 'Order not found');
  const order = { id: snap.id, ...snap.data() };
  const adapter = adapters[order.vendor] || adapters[order.kind === 'rx' ? 'surescripts' : 'labcorp'];
  const result = await adapter(order);
  const entry = { at: new Date().toISOString(), by: staff.id, ok: result.ok, message: result.message, vendorRef: result.vendorRef || null };
  await ref.update({ status: result.ok ? 'transmitted' : 'queued', vendorRef: result.vendorRef || order.vendorRef || null, lastMessage: result.message, transmitLog: admin.firestore.FieldValue.arrayUnion(entry), updatedAt: admin.firestore.FieldValue.serverTimestamp() });
  return { ok: result.ok, queued: !result.ok, message: result.message, vendorRef: result.vendorRef || null };
});

// Inbound results webhook (Labcorp / Quest post HL7 ORU or JSON here once configured).
// Writes a structured users/{uid}/lab_results doc with reviewed:false so it lands in the results inbox.
exports.labResultsWebhook = functions.runWith({ secrets: ['LAB_WEBHOOK_TOKEN'] }).https.onRequest(async (req, res) => {
  if (req.method !== 'POST') return res.status(405).send('POST only');
  const token = req.get('x-webhook-token') || req.query.token;
  if (!cfg('LAB_WEBHOOK_TOKEN') || token !== cfg('LAB_WEBHOOK_TOKEN')) return res.status(401).send('bad token');
  const body = req.body || {};
  // Expected normalized shape (map vendor formats to this in the vendor's transform): { orderId, vendor, results: [{ testName, value, unit, referenceRange, flag, collectedAt, resultedAt, notes }] }
  const order = body.orderId ? await db().doc(`orders/${body.orderId}`).get() : null;
  const uid = body.userId || (order && order.exists ? order.data().userId : null);
  if (!uid) return res.status(400).send('userId or a known orderId is required');
  const batch = db().batch();
  for (const r of body.results || []) {
    batch.set(db().collection(`users/${uid}/lab_results`).doc(), { testName: r.testName, value: String(r.value ?? ''), unit: r.unit || '', referenceRange: r.referenceRange || '', flag: (r.flag || 'normal').toLowerCase(), collectedAt: r.collectedAt ? admin.firestore.Timestamp.fromDate(new Date(r.collectedAt)) : null, resultedAt: r.resultedAt ? admin.firestore.Timestamp.fromDate(new Date(r.resultedAt)) : admin.firestore.FieldValue.serverTimestamp(), notes: r.notes || '', orderId: body.orderId || null, vendor: body.vendor || null, reviewed: false, createdAt: admin.firestore.FieldValue.serverTimestamp(), source: 'vendor' });
  }
  if (order && order.exists) batch.update(order.ref, { status: 'resulted', resultedAt: admin.firestore.FieldValue.serverTimestamp() });
  await batch.commit();
  res.json({ ok: true, count: (body.results || []).length });
});
