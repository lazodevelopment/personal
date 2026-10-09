"""billing.js: write a member-facing invoice/receipt record (users/{uid}/invoices) for every charge."""
import pathlib, shutil
p = pathlib.Path("C:/Users/kurvh/jovi-admin/functions/billing.js"); t = p.read_text(encoding="utf-8")
assert "writeInvoice" not in t
def rep(a, b):
    global t
    assert t.count(a) == 1, (a[:70], t.count(a)); t = t.replace(a, b)

rep("function memberName(u) {", r"""const COMPANY = { name: 'Jovi Health LLC', line1: 'Member Support', phone: '(888) 457-JOVI', email: 'support@jovihealth.com', site: 'jovihealth.com', note: 'Jovi is a healthcare membership, not insurance.' };
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
function memberName(u) {""")

# chargeMember: pending (verification) / failed / success
rep("""    if (/PEND/i.test(String(u.billBankStatus))) { await db().doc(`users/${uid}`).update({ billOpenInvoiceId: inv.id, lastChargeStatus: 'pending', lastChargeError: 'Bank account verification pending' }); return { ok: false, pendingVerification: true, invoiceId: inv.id }; }""",
    """    if (/PEND/i.test(String(u.billBankStatus))) { await db().doc(`users/${uid}`).update({ billOpenInvoiceId: inv.id, lastChargeStatus: 'pending', lastChargeError: 'Bank account verification pending' }); await writeInvoice(uid, u, { billInvoiceId: inv.id, kind: 'membership', items, amount, status: 'pending', reason: 'Bank account verification pending' }); return { ok: false, pendingVerification: true, invoiceId: inv.id }; }""")
rep("""    await db().collection('payment_logs').add({ ...logBase, status: 'failed', reason: 'No bank account on file' });""",
    """    await db().collection('payment_logs').add({ ...logBase, status: 'failed', reason: 'No bank account on file' });
    await writeInvoice(uid, u, { billInvoiceId: inv.id, kind: 'membership', items, amount, status: 'failed', reason: 'No bank account on file' });""")
rep("""    await db().collection('payment_logs').add({ ...logBase, status: ok ? 'success' : 'failed', billPaymentId: pay.id, billStatus: pay.status, reason: ok ? null : `BILL status ${pay.status}` });""",
    """    await db().collection('payment_logs').add({ ...logBase, status: ok ? 'success' : 'failed', billPaymentId: pay.id, billStatus: pay.status, reason: ok ? null : `BILL status ${pay.status}` });
    await writeInvoice(uid, u, { billInvoiceId: inv.id, billPaymentId: pay.id, kind: 'membership', items, amount, status: ok ? 'paid' : 'failed', reason: ok ? null : `Payment ${pay.status}`, meta: { billStatus: pay.status } });""")
rep("""    await db().collection('payment_logs').add({ ...logBase, status: 'failed', reason: (e.body && (e.body.message || e.body.error)) || e.message });
    const paused = attemptNumber >= MAX_ATTEMPTS;""",
    """    await db().collection('payment_logs').add({ ...logBase, status: 'failed', reason: (e.body && (e.body.message || e.body.error)) || e.message });
    await writeInvoice(uid, u, { billInvoiceId: inv.id, kind: 'membership', items, amount, status: 'failed', reason: ((e.body && (e.body.message || e.body.error)) || e.message).slice(0, 200) });
    const paused = attemptNumber >= MAX_ATTEMPTS;""")
# one-time charges
rep("""    await db().collection('payment_logs').add({ userId: uid, type: kind, status: ok ? 'success' : 'failed', amount, billInvoiceId: inv.id, billPaymentId: pay.id, billStatus: pay.status, attemptNumber: 1, timestamp: FV.serverTimestamp(), processor: 'bill', ...meta });""",
    """    await db().collection('payment_logs').add({ userId: uid, type: kind, status: ok ? 'success' : 'failed', amount, billInvoiceId: inv.id, billPaymentId: pay.id, billStatus: pay.status, attemptNumber: 1, timestamp: FV.serverTimestamp(), processor: 'bill', ...meta });
    await writeInvoice(uid, u, { billInvoiceId: inv.id, billPaymentId: pay.id, kind, items: [{ description, quantity: 1, price: amount }], amount, status: ok ? 'paid' : 'failed', period: false, reason: ok ? null : `Payment ${pay.status}` });""")
rep("""    await db().collection('payment_logs').add({ userId: uid, type: kind, status: 'failed', amount, billInvoiceId: inv.id, attemptNumber: 1, timestamp: FV.serverTimestamp(), processor: 'bill', reason: (e.body && e.body.message) || e.message, ...meta });""",
    """    await db().collection('payment_logs').add({ userId: uid, type: kind, status: 'failed', amount, billInvoiceId: inv.id, attemptNumber: 1, timestamp: FV.serverTimestamp(), processor: 'bill', reason: (e.body && e.body.message) || e.message, ...meta });
    await writeInvoice(uid, u, { billInvoiceId: inv.id, kind, items: [{ description, quantity: 1, price: amount }], amount, status: 'failed', period: false, reason: ((e.body && e.body.message) || e.message).slice(0, 200) });""")
# reconcile: ACH returns flip the receipt
rep("""      if (['VOID', 'CANCELED', 'ESCHEATED'].includes(st)) { await d.ref.update({ reconciledReturn: true });""",
    """      if (['VOID', 'CANCELED', 'ESCHEATED'].includes(st)) { await d.ref.update({ reconciledReturn: true }); if (p.billInvoiceId) await db().doc(`users/${p.userId}/invoices/${p.billInvoiceId}`).set({ status: 'returned', reason: `ACH ${st}`, amountPaid: 0, updatedAt: FV.serverTimestamp() }, { merge: true });""")
# reconcile: pending invoices whose bank verified → charge via daily job already; also mark BILL-paid invoices
rep("""  // ACH returns: a payment we recorded as success that BILL now reports VOID/CANCELED/ESCHEATED.""",
    """  // Pending receipts (bank verification) whose BILL invoice is now paid → mark paid.
  const pend = await db().collectionGroup('invoices').where('status', '==', 'pending').limit(200).get().catch(() => ({ docs: [] }));
  for (const d of pend.docs) {
    const inv = d.data(); if (!inv.billInvoiceId) continue;
    try { const b = await api('GET', `/invoices/${inv.billInvoiceId}`); const paid = Number(b.amountDue ?? b.dueAmount ?? 1) === 0 || /PAID/i.test(String(b.paymentStatus || b.status || ''));
      if (paid) { const uid = d.ref.path.split('/')[1]; await d.ref.set({ status: 'paid', amountPaid: inv.total, paidAt: FV.serverTimestamp(), updatedAt: FV.serverTimestamp() }, { merge: true }); await notify(uid, 'Payment received', `${money(inv.total)} for ${inv.items?.[0]?.description || 'your Jovi membership'}. Your receipt is in the app.`, 'invoices'); }
    } catch (e) { console.warn('reconcile receipt', d.ref.path, e.message); }
  }
  // ACH returns: a payment we recorded as success that BILL now reports VOID/CANCELED/ESCHEATED.""")
p.write_text(t, encoding="utf-8", newline="\n"); shutil.copy(p, "C:/Users/kurvh/kurv-functions/billing.js"); print("billing invoices ok")
