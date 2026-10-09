// BILL (bill.com) accounts-receivable integration for Jovi memberships.
// ACH-first: a verified customer bank account on file is charged monthly via POST /v3/receivable-payments.
// ACH ONLY (decision 2026-10-01): cards are not offered. A member without a verified bank account cannot be charged;
// they are notified to add one in the app's Billing screen.
// Secrets: BILL_DEV_KEY, BILL_USERNAME, BILL_PASSWORD, BILL_ORG_ID, BILL_ENV ('sandbox' | 'production'), BILL_WEBHOOK_SECRET
// Writes the same documents the app and notification functions already use: payment_logs, users.{subscriptionStatus,nextBillingDate,lastPaymentDate,lastChargeStatus}
const functions = require('firebase-functions/v1');
const admin = require('firebase-admin');
if (!admin.apps.length) admin.initializeApp();
const db = () => admin.firestore();
const FV = admin.firestore.FieldValue;
const SECRETS = ['BILL_DEV_KEY', 'BILL_USERNAME', 'BILL_PASSWORD', 'BILL_ORG_ID', 'BILL_ENV'];
const cfg = n => { const v = process.env[n]; return v && v !== 'pending' ? v : ''; };
const BASE = () => cfg('BILL_ENV') === 'production' ? 'https://gateway.prod.bill.com/connect' : 'https://gateway.stage.bill.com/connect';
const RETRY_DAYS = 3, MAX_ATTEMPTS = 3;

// ── Session ───────────────────────────────────────────────────────────────
let session = { id: null, at: 0 };
async function login() {
  if (session.id && Date.now() - session.at < 30 * 60 * 1000) return session.id;
  const r = await fetch(`${BASE()}/v3/login`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ devKey: cfg('BILL_DEV_KEY'), username: cfg('BILL_USERNAME'), password: cfg('BILL_PASSWORD'), organizationId: cfg('BILL_ORG_ID') }) });
  if (!r.ok) throw new Error(`BILL login failed: ${r.status} ${await r.text()}`);
  const j = await r.json(); session = { id: j.sessionId, at: Date.now() }; return session.id;
}
async function api(method, path, body) {
  const sid = await login();
  const r = await fetch(`${BASE()}/v3${path}`, { method, headers: { 'content-type': 'application/json', devKey: cfg('BILL_DEV_KEY'), sessionId: sid }, body: body ? JSON.stringify(body) : undefined });
  const text = await r.text(); let j = {}; try { j = JSON.parse(text); } catch { }
  if (r.status === 401) { session = { id: null, at: 0 }; }
  if (!r.ok) { const e = new Error(`BILL ${method} ${path} → ${r.status}: ${text.slice(0, 300)}`); e.status = r.status; e.body = j; throw e; }
  return j;
}
function assertConfigured() { for (const k of ['BILL_DEV_KEY', 'BILL_USERNAME', 'BILL_PASSWORD', 'BILL_ORG_ID']) if (!cfg(k)) throw new functions.https.HttpsError('failed-precondition', `${k} is not configured`); }

// ── Membership line items from the user doc (same math as the app) ───────
function parseJsonArr(a) { return (Array.isArray(a) ? a : []).map(x => { try { return typeof x === 'string' ? JSON.parse(x) : x; } catch { return null; } }).filter(Boolean); }
function lineItems(u) {
  const items = [];
  const health = Number(u.totalHealthPremium ?? u.totalPremium) || 0;
  if (health > 0) items.push({ description: `Jovi membership · ${u.planType || u.planTier || 'Individual'}${u.hasDental || u.dental ? ' + dental' : ''}${u.hasVision || u.vision ? ' + vision' : ''}`, quantity: 1, price: Math.round(health * 100) / 100 });
  const pets = parseJsonArr(u.pets);
  const petTotal = Number(u.petTotalPremium) || 0;
  if (petTotal > 0) items.push({ description: `Jovi Pets · ${pets.length || 1} pet${pets.length === 1 ? '' : 's'}`, quantity: 1, price: Math.round(petTotal * 100) / 100 });
  const total = items.reduce((a, x) => a + x.price, 0);
  const grand = Number(u.grandTotal) || 0;
  if (grand > 0 && Math.abs(grand - total) > 0.5) { items.length = 0; items.push({ description: `Jovi membership (monthly)`, quantity: 1, price: Math.round(grand * 100) / 100 }); }
  return items;
}
async function notify(uid, title, body, route) { try { await db().collection(`users/${uid}/notifications`).add({ type: 'payment', title, body, route: route || 'billing', params: {}, refPath: null, read: false, createdAt: FV.serverTimestamp() }); } catch (e) { console.warn('notify', e.message); } }
const COMPANY = { name: 'Jovi Health LLC', line1: 'Member Support', phone: '(888) 457-JOVI', email: 'support@jovihealth.com', site: 'jovihealth.com', note: 'Jovi is a healthcare membership, not insurance.' };
function periodFor(now) { const start = new Date(now); const end = new Date(now); end.setMonth(end.getMonth() + 1); end.setDate(end.getDate() - 1); return { periodStart: admin.firestore.Timestamp.fromDate(start), periodEnd: admin.firestore.Timestamp.fromDate(end) }; }
/** Member-facing receipt. One doc per BILL invoice; status: pending | paid | failed | returned | void. */
async function writeInvoice(uid, u, { billInvoiceId, billPaymentId = null, kind, items, amount, status, reason = null, period = true, meta = {} }) {
  const id = billInvoiceId || `local_${Date.now().toString(36)}`;
  const ref = db().doc(`users/${uid}/invoices/${id}`);
  const existing = await ref.get();
  const now = new Date();
  const doc = {
    number: existing.exists ? existing.data().number : `JOVI-${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}-${id.slice(-6).toUpperCase()}`,
    kind, status, items, subtotal: amount, total: amount, currency: 'USD', amountPaid: status === 'paid' ? amount : 0,
    memberName: memberName(u), memberEmail: u.email || null, memberAddress: [u.address || u.onboard_address, u.city, u.state, u.zip].filter(Boolean).join(', ') || null,
    paymentMethod: { type: 'ach', last4: u.billBankLast4 || null, bankType: u.billBankType || null },
    billInvoiceId: billInvoiceId || null, billPaymentId, company: COMPANY, reason,
    issuedAt: existing.exists ? existing.data().issuedAt : FV.serverTimestamp(), updatedAt: FV.serverTimestamp(),
    ...(status === 'paid' ? { paidAt: FV.serverTimestamp() } : {}), ...(period ? periodFor(now) : {}), ...meta,
  };
  await ref.set(doc, { merge: true });
  if (status === 'paid') await notify(uid, 'Payment received', `${money(amount)} for ${items[0]?.description || 'your Jovi membership'}. Your receipt is in the app.`, 'invoices');
  return id;
}
const money = n => '$' + Number(n || 0).toFixed(2);
function memberName(u) { return u.onboard_fullName || [u.first || u.firstName, u.last || u.lastName].filter(Boolean).join(' ') || u.email || 'Jovi member'; }

// ── Customer + bank account on file ──────────────────────────────────────
async function ensureCustomer(uid, u) {
  if (u.billCustomerId) return u.billCustomerId;
  const c = await api('POST', '/customers', { name: memberName(u), email: u.email || undefined, contactFirstName: u.first || u.firstName || undefined, contactLastName: u.last || u.lastName || undefined, phone: u.phone || u.onboard_phone || undefined, billingAddress: (u.address || u.onboard_address) ? { line1: u.address || u.onboard_address, city: u.city || '', stateOrProvince: u.state || '', zipOrPostalCode: u.zip || '', country: 'US' } : undefined, archived: false });
  await db().doc(`users/${uid}`).update({ billCustomerId: c.id, billCustomerCreatedAt: FV.serverTimestamp() });
  return c.id;
}

/** Called by the app at onboarding (ACH path). Stores only BILL's bank-account id on the user; never the account number. */
exports.billSetupBankAccount = functions.runWith({ secrets: SECRETS }).https.onCall(async (data, context) => {
  if (!context.auth) throw new functions.https.HttpsError('unauthenticated', 'Sign in required');
  assertConfigured();
  const uid = context.auth.uid; const { routingNumber, accountNumber, accountType, nameOnAccount } = data || {};
  if (!/^\d{9}$/.test(String(routingNumber || '')) || !/^\d{4,17}$/.test(String(accountNumber || ''))) throw new functions.https.HttpsError('invalid-argument', 'Routing or account number is invalid');
  const uSnap = await db().doc(`users/${uid}`).get(); const u = uSnap.data() || {};
  const customerId = await ensureCustomer(uid, u);
  const ba = await api('POST', `/customers/${customerId}/bank-accounts`, { nameOnAccount: nameOnAccount || memberName(u), routingNumber: String(routingNumber), accountNumber: String(accountNumber), type: (accountType || 'CHECKING').toUpperCase(), ownerType: 'PERSONAL', authorizedToCharge: true });
  const patch = { billBankAccountId: ba.id, billBankLast4: String(accountNumber).slice(-4), billBankStatus: ba.status || 'PENDING_VERIFICATION', billBankType: (accountType || 'CHECKING').toUpperCase(), paymentMethod: 'ach', billBankAddedAt: FV.serverTimestamp(), cardLast4: FV.delete(), cardBrand: FV.delete(), cardExpMonth: FV.delete(), cardExpYear: FV.delete(), lastChargeError: FV.delete() };
  if (data.activate) {
    // Onboarding: the membership starts now; the first ACH debit runs as soon as BILL verifies the account (daily job).
    const now = new Date(); const renew = new Date(now.getFullYear() + 1, now.getMonth(), now.getDate());
    Object.assign(patch, { paymentProcessed: true, subscriptionStatus: 'active', membershipStatus: 'active', isActive: true, membershipStartDate: u.membershipStartDate || FV.serverTimestamp(), renew: u.renew || admin.firestore.Timestamp.fromDate(renew), nextBillingDate: admin.firestore.Timestamp.fromDate(now), lastChargeStatus: 'pending', billFailedAttempts: 0 });
  }
  await db().doc(`users/${uid}`).update(patch);
  await notify(uid, 'Bank account added', `Your ${(accountType || 'checking').toLowerCase()} account ending in ${String(accountNumber).slice(-4)} will be used for your Jovi membership. Verification can take up to two business days.`, 'billing');
  return { success: true, ok: true, bankAccountId: ba.id, status: ba.status || 'PENDING_VERIFICATION', last4: String(accountNumber).slice(-4), cardLast4: String(accountNumber).slice(-4), cardBrand: 'ach' };
});

// ── Charge one member for one period ─────────────────────────────────────
async function chargeMember(uid, u, { reason = 'monthly', attemptNumber = 1 } = {}) {
  const items = lineItems(u); const amount = items.reduce((a, x) => a + x.price, 0);
  if (!amount) return { skipped: 'no amount' };
  const customerId = await ensureCustomer(uid, u);
  const period = new Date(); const due = period.toISOString().slice(0, 10);
  const inv = await api('POST', '/invoices', { customerId, invoiceNumber: `JOVI-${due.replace(/-/g, '')}-${uid.slice(0, 6).toUpperCase()}`, invoiceDate: due, dueDate: due, invoiceLineItems: items.map(x => ({ description: x.description, quantity: x.quantity, price: x.price })) });
  const logBase = { userId: uid, type: reason === 'retry' ? 'membership_retry' : 'membership_monthly', amount, billInvoiceId: inv.id, attemptNumber, timestamp: FV.serverTimestamp(), processor: 'bill' };
  if (!u.billBankAccountId) {
    await db().collection('payment_logs').add({ ...logBase, status: 'failed', reason: 'No bank account on file' });
    await writeInvoice(uid, u, { billInvoiceId: inv.id, kind: 'membership', items, amount, status: 'failed', reason: 'No bank account on file' });
    await db().doc(`users/${uid}`).update({ lastChargeStatus: 'failed', lastChargeError: 'No bank account on file', lastChargeAttemptAt: FV.serverTimestamp(), lastChargeAmount: amount, billOpenInvoiceId: inv.id });
    await notify(uid, 'Add a bank account to keep your membership active', 'Your monthly payment could not be collected because there is no bank account on file. Add one under Billing.', 'billing');
    return { ok: false, error: 'no_bank_on_file' };
  }
  if (u.billBankStatus && /PEND|VERIF/i.test(String(u.billBankStatus)) && !/VERIFIED|ACTIVE/i.test(String(u.billBankStatus))) {
    try { const ba = await api('GET', `/customers/${customerId}/bank-accounts/${u.billBankAccountId}`); await db().doc(`users/${uid}`).update({ billBankStatus: ba.status || 'UNKNOWN' }); u.billBankStatus = ba.status || 'UNKNOWN'; } catch (e) { console.warn('bank status check', uid, e.message); }
    if (/PEND/i.test(String(u.billBankStatus))) { await db().doc(`users/${uid}`).update({ billOpenInvoiceId: inv.id, lastChargeStatus: 'pending', lastChargeError: 'Bank account verification pending' }); await writeInvoice(uid, u, { billInvoiceId: inv.id, kind: 'membership', items, amount, status: 'pending', reason: 'Bank account verification pending' }); return { ok: false, pendingVerification: true, invoiceId: inv.id }; }
  }
  try {
    const pay = await api('POST', '/receivable-payments', { customerId, fundingAccount: { id: u.billBankAccountId, type: 'BANK_ACCOUNT' }, invoicePayments: [{ invoiceId: inv.id, amount }], description: `Jovi membership ${due}` });
    const ok = ['PAID', 'SCHEDULED'].includes(String(pay.status || '').toUpperCase());
    await db().collection('payment_logs').add({ ...logBase, status: ok ? 'success' : 'failed', billPaymentId: pay.id, billStatus: pay.status, reason: ok ? null : `BILL status ${pay.status}` });
    await writeInvoice(uid, u, { billInvoiceId: inv.id, billPaymentId: pay.id, kind: 'membership', items, amount, status: ok ? 'paid' : 'failed', reason: ok ? null : `Payment ${pay.status}`, meta: { billStatus: pay.status } });
    const next = new Date(); next.setMonth(next.getMonth() + 1);
    await db().doc(`users/${uid}`).update(ok ? { subscriptionStatus: u.subscriptionStatus === 'canceling' ? 'canceling' : 'active', membershipStatus: 'active', lastChargeStatus: 'ok', lastChargeError: FV.delete(), lastChargeAttemptAt: FV.serverTimestamp(), lastChargeAmount: amount, lastPaymentDate: FV.serverTimestamp(), nextBillingDate: admin.firestore.Timestamp.fromDate(next), billLastPaymentId: pay.id, billOpenInvoiceId: FV.delete(), billFailedAttempts: 0 } : { lastChargeStatus: 'failed', lastChargeError: `BILL status ${pay.status}`, lastChargeAttemptAt: FV.serverTimestamp(), billFailedAttempts: attemptNumber });
    return { ok, paymentId: pay.id, status: pay.status };
  } catch (e) {
    await db().collection('payment_logs').add({ ...logBase, status: 'failed', reason: (e.body && (e.body.message || e.body.error)) || e.message });
    await writeInvoice(uid, u, { billInvoiceId: inv.id, kind: 'membership', items, amount, status: 'failed', reason: ((e.body && (e.body.message || e.body.error)) || e.message).slice(0, 200) });
    const paused = attemptNumber >= MAX_ATTEMPTS;
    const retryAt = new Date(Date.now() + RETRY_DAYS * 86400000);
    await db().doc(`users/${uid}`).update({ lastChargeStatus: paused ? 'past_due' : 'failed', lastChargeError: e.message.slice(0, 200), lastChargeAttemptAt: FV.serverTimestamp(), billFailedAttempts: attemptNumber, billRetryAt: paused ? FV.delete() : admin.firestore.Timestamp.fromDate(retryAt), ...(paused ? { subscriptionStatus: 'suspended' } : {}) });
    return { ok: false, error: e.message, paused };
  }
}

/** Staff-triggered charge (retry, first charge after bank verification). */
exports.billChargeNow = functions.runWith({ secrets: SECRETS }).https.onCall(async (data, context) => {
  if (!context.auth) throw new functions.https.HttpsError('unauthenticated', 'Sign in required');
  const s = await db().doc(`staff/${context.auth.uid}`).get();
  if (!s.exists || !['superadmin', 'admin'].includes(s.data().role)) throw new functions.https.HttpsError('permission-denied', 'Admin role required');
  assertConfigured();
  const uid = data.userId; const uSnap = await db().doc(`users/${uid}`).get(); if (!uSnap.exists) throw new functions.https.HttpsError('not-found', 'Member not found');
  const u = uSnap.data(); const res = await chargeMember(uid, u, { reason: data.reason || 'manual', attemptNumber: (u.billFailedAttempts || 0) + 1 });
  await db().collection('audit_logs').add({ action: 'billing.charge', target: `users/${uid}`, staffId: context.auth.uid, role: s.data().role, at: FV.serverTimestamp(), meta: res });
  return res;
});

/** Daily at 06:00 Central: charge members whose nextBillingDate (or renew anniversary) is today, and run retries. */
exports.billDailyCharges = functions.runWith({ secrets: SECRETS, timeoutSeconds: 540 }).pubsub.schedule('0 6 * * *').timeZone('America/Chicago').onRun(async () => {
  if (!cfg('BILL_DEV_KEY')) { console.log('BILL not configured; skipping'); return null; }
  const now = new Date(); const today = now.getDate();
  const snap = await db().collection('users').where('paymentProcessed', '==', true).get();
  let charged = 0, retried = 0;
  for (const d of snap.docs) {
    const u = d.data(); const st = String(u.subscriptionStatus || 'active').toLowerCase();
    if (['canceled', 'cancelled', 'suspended'].includes(st) || u.membershipStatus === 'inactive') continue;
    if (st === 'canceling' && u.willCancelOn && u.willCancelOn.toDate && u.willCancelOn.toDate() < now) continue;
    const retryAt = u.billRetryAt && u.billRetryAt.toDate ? u.billRetryAt.toDate() : null;
    if (retryAt && retryAt <= now) { await chargeMember(d.id, u, { reason: 'retry', attemptNumber: (u.billFailedAttempts || 0) + 1 }); retried++; continue; }
    const nb = u.nextBillingDate && u.nextBillingDate.toDate ? u.nextBillingDate.toDate() : null;
    const renew = u.renew && u.renew.toDate ? u.renew.toDate() : null;
    const dueToday = nb ? nb.toDateString() === now.toDateString() : (renew ? renew.getDate() === today : false);
    const last = u.lastPaymentDate && u.lastPaymentDate.toDate ? u.lastPaymentDate.toDate() : null;
    if (dueToday && !(last && now - last < 20 * 86400000)) { await chargeMember(d.id, u, { reason: 'monthly' }); charged++; }
  }
  console.log(`BILL daily: charged ${charged}, retried ${retried}`); return null;
});

/** Hourly reconciliation: pull recent receivable payments and invoices from BILL and settle returns / hosted-link payments. */
exports.billReconcile = functions.runWith({ secrets: SECRETS, timeoutSeconds: 300 }).pubsub.schedule('15 * * * *').timeZone('America/Chicago').onRun(async () => {
  if (!cfg('BILL_DEV_KEY')) return null;
  // Hosted-link invoices: mark paid when BILL says so.
  const open = await db().collection('users').where('billOpenInvoiceId', '>', '').get();
  for (const d of open.docs) {
    const u = d.data();
    try { const inv = await api('GET', `/invoices/${u.billOpenInvoiceId}`); const paid = Number(inv.amountDue ?? inv.dueAmount ?? 1) === 0 || String(inv.paymentStatus || inv.status || '').toUpperCase().includes('PAID');
      if (paid) { const next = new Date(); next.setMonth(next.getMonth() + 1); await db().collection('payment_logs').add({ userId: d.id, type: 'membership_monthly', status: 'success', amount: Number(inv.totalAmount || inv.amount || 0), billInvoiceId: inv.id, attemptNumber: 1, timestamp: FV.serverTimestamp(), processor: 'bill', reason: 'Paid via BILL invoice link' }); await d.ref.update({ subscriptionStatus: u.subscriptionStatus === 'canceling' ? 'canceling' : 'active', membershipStatus: 'active', lastChargeStatus: 'ok', lastPaymentDate: FV.serverTimestamp(), nextBillingDate: admin.firestore.Timestamp.fromDate(next), billOpenInvoiceId: FV.delete(), billFailedAttempts: 0 }); }
    } catch (e) { console.warn('reconcile invoice', d.id, e.message); }
  }
  // Pending receipts (bank verification) whose BILL invoice is now paid → mark paid.
  const pend = await db().collectionGroup('invoices').where('status', '==', 'pending').limit(200).get().catch(() => ({ docs: [] }));
  for (const d of pend.docs) {
    const inv = d.data(); if (!inv.billInvoiceId) continue;
    try { const b = await api('GET', `/invoices/${inv.billInvoiceId}`); const paid = Number(b.amountDue ?? b.dueAmount ?? 1) === 0 || /PAID/i.test(String(b.paymentStatus || b.status || ''));
      if (paid) { const uid = d.ref.path.split('/')[1]; await d.ref.set({ status: 'paid', amountPaid: inv.total, paidAt: FV.serverTimestamp(), updatedAt: FV.serverTimestamp() }, { merge: true }); await notify(uid, 'Payment received', `${money(inv.total)} for ${inv.items?.[0]?.description || 'your Jovi membership'}. Your receipt is in the app.`, 'invoices'); }
    } catch (e) { console.warn('reconcile receipt', d.ref.path, e.message); }
  }
  // ACH returns: a payment we recorded as success that BILL now reports VOID/CANCELED/ESCHEATED.
  const recent = await db().collection('payment_logs').where('processor', '==', 'bill').where('status', '==', 'success').orderBy('timestamp', 'desc').limit(200).get();
  for (const d of recent.docs) {
    const p = d.data(); if (!p.billPaymentId || p.reconciledReturn) continue;
    try { const pay = await api('GET', `/receivable-payments/${p.billPaymentId}`); const st = String(pay.status || '').toUpperCase();
      if (['VOID', 'CANCELED', 'ESCHEATED'].includes(st)) { await d.ref.update({ reconciledReturn: true }); if (p.billInvoiceId) await db().doc(`users/${p.userId}/invoices/${p.billInvoiceId}`).set({ status: 'returned', reason: `ACH ${st}`, amountPaid: 0, updatedAt: FV.serverTimestamp() }, { merge: true }); await db().collection('payment_logs').add({ userId: p.userId, type: 'membership_return', status: 'failed', amount: p.amount, billPaymentId: p.billPaymentId, attemptNumber: 1, timestamp: FV.serverTimestamp(), processor: 'bill', reason: `ACH payment ${st}` }); await db().doc(`users/${p.userId}`).update({ lastChargeStatus: 'failed', lastChargeError: `ACH ${st}`, billRetryAt: admin.firestore.Timestamp.fromDate(new Date(Date.now() + RETRY_DAYS * 86400000)), billFailedAttempts: 1 }); }
    } catch (e) { if (e.status !== 404) console.warn('reconcile payment', p.billPaymentId, e.message); }
  }
  return null;
});

/** Webhook receiver (subscribe BILL events here). Treated as a trigger only; reconcile does the authoritative read. */
exports.billWebhook = functions.runWith({ secrets: ['BILL_WEBHOOK_SECRET'] }).https.onRequest(async (req, res) => {
  if (req.method !== 'POST') return res.status(405).send('POST only');
  const secret = cfg('BILL_WEBHOOK_SECRET'); const got = req.get('x-bill-signature') || req.get('x-webhook-secret') || req.query.secret;
  if (secret && got !== secret) return res.status(401).send('bad signature');
  await db().collection('bill_webhook_events').add({ receivedAt: FV.serverTimestamp(), headers: { type: req.get('x-bill-event-type') || null }, body: req.body || null });
  res.json({ ok: true });
});


// ── Named callables matching the member app's existing contracts ─────────
/** Billing widget: replaces the card on file with a bank account. Same response keys the widget reads. */
exports.updatePaymentMethod = functions.runWith({ secrets: SECRETS }).https.onCall(async (data, context) => {
  if (!context.auth) throw new functions.https.HttpsError('unauthenticated', 'Sign in required');
  assertConfigured();
  const uid = context.auth.uid; const { routingNumber, accountNumber, accountType, nameOnAccount } = data || {};
  if (!/^\d{9}$/.test(String(routingNumber || '')) || !/^\d{4,17}$/.test(String(accountNumber || ''))) return { success: false, error: 'Routing or account number is invalid', errorCode: 'INVALID_BANK' };
  try {
    const uSnap = await db().doc(`users/${uid}`).get(); const u = uSnap.data() || {};
    const customerId = await ensureCustomer(uid, u);
    if (u.billBankAccountId) { try { await api('POST', `/customers/${customerId}/bank-accounts/${u.billBankAccountId}/archive`, {}); } catch (e) { console.warn('archive old bank', e.message); } }
    const ba = await api('POST', `/customers/${customerId}/bank-accounts`, { nameOnAccount: nameOnAccount || memberName(u), routingNumber: String(routingNumber), accountNumber: String(accountNumber), type: (accountType || 'CHECKING').toUpperCase(), ownerType: 'PERSONAL', authorizedToCharge: true });
    const last4 = String(accountNumber).slice(-4);
    await db().doc(`users/${uid}`).update({ billBankAccountId: ba.id, billBankLast4: last4, billBankStatus: ba.status || 'PENDING_VERIFICATION', billBankType: (accountType || 'CHECKING').toUpperCase(), paymentMethod: 'ach', billBankAddedAt: FV.serverTimestamp(), cardLast4: last4, cardBrand: 'ach', cardExpMonth: FV.delete(), cardExpYear: FV.delete(), cardUpdatedAt: FV.serverTimestamp(), lastChargeError: FV.delete() });
    return { success: true, cardLast4: last4, cardBrand: 'ach', bankAccountId: ba.id, status: ba.status || 'PENDING_VERIFICATION' };
  } catch (e) { return { success: false, error: (e.body && e.body.message) || e.message, errorCode: 'PROCESSOR_ERROR' }; }
});

exports.deletePaymentMethod = functions.runWith({ secrets: SECRETS }).https.onCall(async (data, context) => {
  if (!context.auth) throw new functions.https.HttpsError('unauthenticated', 'Sign in required');
  assertConfigured();
  const uid = context.auth.uid; const uSnap = await db().doc(`users/${uid}`).get(); const u = uSnap.data() || {};
  try {
    if (u.billBankAccountId && u.billCustomerId) { try { await api('POST', `/customers/${u.billCustomerId}/bank-accounts/${u.billBankAccountId}/archive`, {}); } catch (e) { console.warn('archive bank', e.message); } }
    await db().doc(`users/${uid}`).update({ billBankAccountId: FV.delete(), billBankLast4: FV.delete(), billBankStatus: FV.delete(), cardLast4: FV.delete(), cardBrand: FV.delete(), cardExpMonth: FV.delete(), cardExpYear: FV.delete(), paymentMethod: FV.delete() });
    return { success: true };
  } catch (e) { return { success: false, error: e.message, errorCode: 'PROCESSOR_ERROR' }; }
});

exports.retryFailedCharge = functions.runWith({ secrets: SECRETS }).https.onCall(async (data, context) => {
  if (!context.auth) throw new functions.https.HttpsError('unauthenticated', 'Sign in required');
  assertConfigured();
  const uid = context.auth.uid; const uSnap = await db().doc(`users/${uid}`).get(); if (!uSnap.exists) return { success: false, error: 'Member not found', errorCode: 'NOT_FOUND' };
  const u = uSnap.data(); const res = await chargeMember(uid, u, { reason: 'retry', attemptNumber: (u.billFailedAttempts || 0) + 1 });
  if (res.ok) return { success: true, transactionId: res.paymentId, chargedAmount: lineItems(u).reduce((a, x) => a + x.price, 0) };
  return { success: false, error: res.pendingVerification ? 'Your bank account is still being verified. We will charge it automatically once verification completes.' : (res.error || 'Charge failed'), errorCode: res.pendingVerification ? 'BANK_PENDING' : 'CHARGE_FAILED' };
});

/** One-time ACH debit against the bank on file: Jovi Pass ($49) and other add-ons. */
async function chargeOneTime(uid, u, { amount, description, kind, meta = {} }) {
  if (!u.billBankAccountId) return { success: false, error: 'Add a bank account under Billing first.', errorCode: 'NO_BANK' };
  const customerId = await ensureCustomer(uid, u); const due = new Date().toISOString().slice(0, 10);
  const inv = await api('POST', '/invoices', { customerId, invoiceNumber: `JOVI-${kind.toUpperCase()}-${Date.now().toString(36).toUpperCase()}`, invoiceDate: due, dueDate: due, invoiceLineItems: [{ description, quantity: 1, price: Math.round(amount * 100) / 100 }] });
  try {
    const pay = await api('POST', '/receivable-payments', { customerId, fundingAccount: { id: u.billBankAccountId, type: 'BANK_ACCOUNT' }, invoicePayments: [{ invoiceId: inv.id, amount }], description });
    const ok = ['PAID', 'SCHEDULED'].includes(String(pay.status || '').toUpperCase());
    await db().collection('payment_logs').add({ userId: uid, type: kind, status: ok ? 'success' : 'failed', amount, billInvoiceId: inv.id, billPaymentId: pay.id, billStatus: pay.status, attemptNumber: 1, timestamp: FV.serverTimestamp(), processor: 'bill', ...meta });
    await writeInvoice(uid, u, { billInvoiceId: inv.id, billPaymentId: pay.id, kind, items: [{ description, quantity: 1, price: amount }], amount, status: ok ? 'paid' : 'failed', period: false, reason: ok ? null : `Payment ${pay.status}` });
    return ok ? { success: true, transactionId: pay.id, chargedAmount: amount } : { success: false, error: `Payment ${pay.status}`, errorCode: 'CHARGE_FAILED' };
  } catch (e) {
    await db().collection('payment_logs').add({ userId: uid, type: kind, status: 'failed', amount, billInvoiceId: inv.id, attemptNumber: 1, timestamp: FV.serverTimestamp(), processor: 'bill', reason: (e.body && e.body.message) || e.message, ...meta });
    await writeInvoice(uid, u, { billInvoiceId: inv.id, kind, items: [{ description, quantity: 1, price: amount }], amount, status: 'failed', period: false, reason: ((e.body && e.body.message) || e.message).slice(0, 200) });
    return { success: false, error: (e.body && e.body.message) || e.message, errorCode: 'CHARGE_FAILED' };
  }
}
exports.billChargeOneTime = functions.runWith({ secrets: SECRETS }).https.onCall(async (data, context) => {
  if (!context.auth) throw new functions.https.HttpsError('unauthenticated', 'Sign in required');
  assertConfigured();
  const { amount, description, kind } = data || {}; const allowed = { kurvpass: 49 };
  if (!allowed[kind] || Number(amount) !== allowed[kind]) throw new functions.https.HttpsError('invalid-argument', 'Unknown charge');
  const uid = context.auth.uid; const u = (await db().doc(`users/${uid}`).get()).data() || {};
  const res = await chargeOneTime(uid, u, { amount: allowed[kind], description: description || 'Jovi Pass priority visit', kind });
  if (res.success && kind === 'kurvpass') await db().doc(`users/${uid}`).update({ lastKurvPassPurchase: FV.serverTimestamp() });
  return res;
});
/** Pet Profiles contract: prorated add-on when a pet is added mid-cycle. */
exports.chargePetAddon = functions.runWith({ secrets: SECRETS }).https.onCall(async (data, context) => {
  if (!context.auth) throw new functions.https.HttpsError('unauthenticated', 'Sign in required');
  assertConfigured();
  const uid = context.auth.uid; const u = (await db().doc(`users/${uid}`).get()).data() || {};
  const amount = Math.round(Number(data.prorationAmount || 0) * 100) / 100; if (!(amount > 0)) return { success: true, transactionId: null, chargedAmount: 0 };
  return chargeOneTime(uid, u, { amount, description: `Jovi Pets · ${data.petName || 'pet'} · prorated ${data.prorationDays || ''}/${data.cycleDays || ''} days`, kind: 'pet_addon_proration', meta: { petId: data.petId || null, petName: data.petName || null, monthlyPremium: Number(data.monthlyPremium) || null } });
});

/** Staff app: verify credentials and show which environment is live. Admin roles only. */
exports.billStatus = functions.runWith({ secrets: SECRETS }).https.onCall(async (data, context) => {
  if (!context.auth) throw new functions.https.HttpsError('unauthenticated', 'Sign in required');
  const s = await db().doc(`staff/${context.auth.uid}`).get();
  if (!s.exists || !['superadmin', 'admin'].includes(s.data().role)) throw new functions.https.HttpsError('permission-denied', 'Admin role required');
  const out = { env: cfg('BILL_ENV') || 'sandbox', base: BASE(), configured: ['BILL_DEV_KEY', 'BILL_USERNAME', 'BILL_PASSWORD', 'BILL_ORG_ID'].every(k => !!cfg(k)) };
  if (!out.configured) return { ...out, ok: false, message: 'Missing one or more BILL secrets' };
  try {
    session = { id: null, at: 0 }; const sid = await login(); out.ok = !!sid;
    try { const org = await api('GET', `/organizations/${cfg('BILL_ORG_ID')}`); out.orgName = org.name || org.organizationName || null; } catch (e) { out.orgLookup = e.message.slice(0, 160); }
    try { const c = await api('GET', '/customers?max=1'); out.customersReachable = true; out.sampleCount = Array.isArray(c.results) ? c.results.length : (Array.isArray(c) ? c.length : null); } catch (e) { out.customersReachable = false; out.customersError = e.message.slice(0, 160); }
    out.message = 'Signed in to BILL';
  } catch (e) { out.ok = false; out.message = e.message.slice(0, 300); }
  await db().collection('audit_logs').add({ action: 'billing.status', target: 'bill', staffId: context.auth.uid, role: s.data().role, at: FV.serverTimestamp(), meta: { ok: out.ok, env: out.env } });
  return out;
});
