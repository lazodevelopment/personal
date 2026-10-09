"""billing.js → ACH only, plus the named callables the widgets already call:
updatePaymentMethod, deletePaymentMethod, retryFailedCharge, chargePetAddon, billChargeOneTime."""
import pathlib, shutil
p = pathlib.Path("C:/Users/kurvh/jovi-admin/functions/billing.js"); t = p.read_text(encoding="utf-8")
assert "billChargeOneTime" not in t
def rep(a, b):
    global t
    assert t.count(a) == 1, (a[:70], t.count(a)); t = t.replace(a, b)

# Header comment
rep("// Cards cannot be charged through the v3 API; card members get a hosted BILL invoice link (2.9%) by email.",
    "// ACH ONLY (decision 2026-10-01): cards are not offered. A member without a verified bank account cannot be charged;\n// they are notified to add one in the app's Billing screen.")

# No hosted-invoice path: without a bank account, log and notify.
rep("""  if (u.paymentMethod === 'card' || !u.billBankAccountId) {
    // Card or no bank on file: send the hosted invoice (customer pays by card/ACH on BILL's page).
    await api('POST', `/invoices/${inv.id}/send`, {}).catch(() => {});
    await db().collection('payment_logs').add({ ...logBase, status: 'invoiced', reason: 'Awaiting payment via emailed BILL invoice' });
    await db().doc(`users/${uid}`).update({ lastChargeStatus: 'pending', lastChargeAttemptAt: FV.serverTimestamp(), lastChargeAmount: amount, billOpenInvoiceId: inv.id });
    return { invoiced: true, invoiceId: inv.id };
  }""",
"""  if (!u.billBankAccountId) {
    await db().collection('payment_logs').add({ ...logBase, status: 'failed', reason: 'No bank account on file' });
    await db().doc(`users/${uid}`).update({ lastChargeStatus: 'failed', lastChargeError: 'No bank account on file', lastChargeAttemptAt: FV.serverTimestamp(), lastChargeAmount: amount, billOpenInvoiceId: inv.id });
    await notify(uid, 'Add a bank account to keep your membership active', 'Your monthly payment could not be collected because there is no bank account on file. Add one under Billing.', 'billing');
    return { ok: false, error: 'no_bank_on_file' };
  }
  if (u.billBankStatus && /PEND|VERIF/i.test(String(u.billBankStatus)) && !/VERIFIED|ACTIVE/i.test(String(u.billBankStatus))) {
    try { const ba = await api('GET', `/customers/${customerId}/bank-accounts/${u.billBankAccountId}`); await db().doc(`users/${uid}`).update({ billBankStatus: ba.status || 'UNKNOWN' }); u.billBankStatus = ba.status || 'UNKNOWN'; } catch (e) { console.warn('bank status check', uid, e.message); }
    if (/PEND/i.test(String(u.billBankStatus))) { await db().doc(`users/${uid}`).update({ billOpenInvoiceId: inv.id, lastChargeStatus: 'pending', lastChargeError: 'Bank account verification pending' }); return { ok: false, pendingVerification: true, invoiceId: inv.id }; }
  }""")

# notify helper + membership activation on bank setup + one-time charges
rep("function memberName(u) {",
    """async function notify(uid, title, body, route) { try { await db().collection(`users/${uid}/notifications`).add({ type: 'payment', title, body, route: route || 'billing', params: {}, refPath: null, read: false, createdAt: FV.serverTimestamp() }); } catch (e) { console.warn('notify', e.message); } }
function memberName(u) {""")

rep("""  await db().doc(`users/${uid}`).update({ billBankAccountId: ba.id, billBankLast4: String(accountNumber).slice(-4), billBankStatus: ba.status || 'PENDING_VERIFICATION', paymentMethod: 'ach', billBankAddedAt: FV.serverTimestamp(), cardLast4: FV.delete(), cardBrand: FV.delete() });
  return { ok: true, bankAccountId: ba.id, status: ba.status || 'PENDING_VERIFICATION', last4: String(accountNumber).slice(-4) };""",
"""  const patch = { billBankAccountId: ba.id, billBankLast4: String(accountNumber).slice(-4), billBankStatus: ba.status || 'PENDING_VERIFICATION', billBankType: (accountType || 'CHECKING').toUpperCase(), paymentMethod: 'ach', billBankAddedAt: FV.serverTimestamp(), cardLast4: FV.delete(), cardBrand: FV.delete(), cardExpMonth: FV.delete(), cardExpYear: FV.delete(), lastChargeError: FV.delete() };
  if (data.activate) {
    // Onboarding: the membership starts now; the first ACH debit runs as soon as BILL verifies the account (daily job).
    const now = new Date(); const renew = new Date(now.getFullYear() + 1, now.getMonth(), now.getDate());
    Object.assign(patch, { paymentProcessed: true, subscriptionStatus: 'active', membershipStatus: 'active', isActive: true, membershipStartDate: u.membershipStartDate || FV.serverTimestamp(), renew: u.renew || admin.firestore.Timestamp.fromDate(renew), nextBillingDate: admin.firestore.Timestamp.fromDate(now), lastChargeStatus: 'pending', billFailedAttempts: 0 });
  }
  await db().doc(`users/${uid}`).update(patch);
  await notify(uid, 'Bank account added', `Your ${(accountType || 'checking').toLowerCase()} account ending in ${String(accountNumber).slice(-4)} will be used for your Jovi membership. Verification can take up to two business days.`, 'billing');
  return { success: true, ok: true, bankAccountId: ba.id, status: ba.status || 'PENDING_VERIFICATION', last4: String(accountNumber).slice(-4), cardLast4: String(accountNumber).slice(-4), cardBrand: 'ach' };""")

t += r"""

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
    return ok ? { success: true, transactionId: pay.id, chargedAmount: amount } : { success: false, error: `Payment ${pay.status}`, errorCode: 'CHARGE_FAILED' };
  } catch (e) {
    await db().collection('payment_logs').add({ userId: uid, type: kind, status: 'failed', amount, billInvoiceId: inv.id, attemptNumber: 1, timestamp: FV.serverTimestamp(), processor: 'bill', reason: (e.body && e.body.message) || e.message, ...meta });
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
"""
p.write_text(t, encoding="utf-8", newline="\n"); shutil.copy(p, "C:/Users/kurvh/kurv-functions/billing.js"); print("billing.js patched")
