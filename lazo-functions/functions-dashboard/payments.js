// functions-dashboard/payments.js
// Build ID: JC-LAZO-FNDASH-0913-018 (018: the reminder sweep skips practice-couple invoices; 014: couple emails carry the vendor brand; 011: fileLink + fileView - the login-free booking page at meetlazo.com/f/{inquiry}?t=; base 010)
//
// PAYMENT PLANS + THE WHOP VENDOR RAIL (Build A of the HoneyBook gap list).
//
// Design: an installment IS an invoice. Every payment plan is written as N
// invoice docs under inquiries/{id}/invoices, each carrying planId,
// installmentIndex, dueDate, lateFee, tipAllowed and autopay. Nothing that
// already reads invoices changes: the Money card, the one-tap reminder, the
// couple's "Pay" button, invoicePdf and the contract's auto-retainer all keep
// working; they just see more invoices, each with a due date.
//
// Rails:
//   whop    the vendor installs the "Lazo Payments" Whop app on their own
//           Whop business and links its company id here. Every charge is a
//           checkout configuration created ON THEIR company (plan.company_id)
//           so the money lands in their Whop balance; Whop handles their KYC,
//           payouts, tax and disputes. Lazo never holds a cent. The app-level
//           webhook (payment.succeeded) marks the invoice paid.
//   stripe / square / links   unchanged - the legacy invoiceCheckout in the
//           default codebase still serves them; payCheckout passes through.
//
// Functions
//   planCreate           callable (vendor)  build the schedule of invoices
//   planCancel           callable (vendor)  void the unpaid installments
//   payCheckout          GET ?inquiry=&invoice=&tip=   -> {url}
//   whopAppWebhook       POST app-level webhook from Whop
//   whopVendorConnect    callable (vendor)  {companyId} verify + link
//   whopVendorDisconnect callable (vendor)
//   paymentPlanSweep     daily 09:00 America/Phoenix: due-soon reminders,
//                        overdue reminders, late fees, autopay attempts
//   fileLink             callable (vendor)  {inquiryId, vendorId} -> the couple's
//                        login-free link meetlazo.com/f/{inquiry}?t=<token>
//   fileView             GET ?inquiry=&t=   -> JSON the worker renders at /f/
//
// Secrets: WHOP_API_KEY (already set for the default codebase; secrets are
// project-wide), WHOP_APP_WEBHOOK_SECRET (new - the app webhook's secret from
// the developer dashboard, app row -> Webhooks), RESEND_API_KEY.
//
// Wire-up in functions-dashboard/index.js (two lines, see the handoff note):
//   const payments = require('./payments')(RESEND_API_KEY);
//   Object.assign(exports, payments);
//
// Deploy: firebase deploy --only functions:dashboard   (from lazo-functions)

'use strict';

const crypto = require('crypto');
const { onRequest, onCall, HttpsError } = require('firebase-functions/v2/https');
const { onSchedule } = require('firebase-functions/v2/scheduler');
const { defineSecret } = require('firebase-functions/params');
const admin = require('firebase-admin');
const { wrap: brandWrap } = require('./brand');

const WHOP_API_KEY = defineSecret('WHOP_API_KEY');
const WHOP_APP_WEBHOOK_SECRET = defineSecret('WHOP_APP_WEBHOOK_SECRET');

// Whop REST base. Your key is pinned to API version 2026-08-31 at the key
// level; if Whop asks for a version header the constant below is the one
// place to add it.
const WHOP_API = 'https://api.whop.com/api/v1';
const WHOP_VERSION = '2026-08-31';
// The Lazo Payments app id (developer dashboard -> your app -> app_xxx).
// Set it once, here, after you create the app.
const WHOP_APP_ID = 'app_REPLACE_ME';
const WHOP_INSTALL_URL = `https://whop.com/apps/${WHOP_APP_ID}/install/`;

// Legacy checkout (Stripe / Square) in the default codebase - untouched.
const LEGACY_CHECKOUT = 'https://us-central1-lazo-513ec.cloudfunctions.net/invoiceCheckout';
const APP = 'https://app.meetlazo.com/dashboard';
const FROM = 'Lazo <hello@meetlazo.com>';

const db = () => admin.firestore();
const { FieldValue, Timestamp } = admin.firestore;

const str = (v) => (v == null ? '' : String(v));
const num = (v) => (typeof v === 'number' && isFinite(v) ? v : (parseFloat(v) || 0));
const round2 = (n) => Math.round(n * 100) / 100;
const toDate = (v) => (v && typeof v.toDate === 'function') ? v.toDate() : (v instanceof Date ? v : null);
const money = (n) => '$' + round2(num(n)).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
const fmtDate = (d) => d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
const dayStart = (d) => { const x = new Date(d); x.setHours(0, 0, 0, 0); return x; };

module.exports = function paymentsModule(RESEND_API_KEY) {

  async function sendEmail(to, subject, html, text) {
    if (!to) return;
    const r = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${RESEND_API_KEY.value()}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ from: FROM, to: [to], subject, html, text }),
    });
    if (!r.ok) throw new Error(`resend ${r.status}: ${await r.text()}`);
  }

  // ---------------------------------------------------------------- access --
  async function vendorAccess(uid, vendorId) {
    if (!uid || !vendorId) return false;
    const [v, u] = await Promise.all([
      db().collection('vendors').doc(vendorId).get(),
      db().collection('users').doc(uid).get(),
    ]);
    if (!v.exists) return false;
    if (str(v.get('claimedBy')) === uid) return true;
    const ud = u.exists ? u.data() : {};
    return str(ud.vendorId) === vendorId && str(ud.vendorRole) === 'manager';
  }

  async function coupleContact(inq) {
    const cid = str(inq.coupleUid);
    if (!cid) return { email: '', name: str(inq.coupleName) || 'there' };
    const u = await db().collection('users').doc(cid).get();
    const ud = u.exists ? u.data() : {};
    return { email: str(ud.email), name: str(inq.coupleName) || str(ud.display_name) || 'there' };
  }

  async function threadSystem(inquiryId, text, extra) {
    await db().collection('inquiries').doc(inquiryId).collection('messages').add({
      senderRole: 'vendor', system: true, text, at: FieldValue.serverTimestamp(), ...(extra || {}),
    });
  }

  // ------------------------------------------------------------------ whop --
  async function whop(path, method, body, apiKey) {
    const r = await fetch(WHOP_API + path, {
      method: method || 'GET',
      headers: {
        'Authorization': `Bearer ${apiKey || WHOP_API_KEY.value()}`,
        'Content-Type': 'application/json',
        'Whop-Version': WHOP_VERSION,
      },
      body: body ? JSON.stringify(body) : undefined,
    });
    const txt = await r.text();
    let j = null; try { j = txt ? JSON.parse(txt) : null; } catch (e) { j = { raw: txt }; }
    if (!r.ok) {
      const err = new Error(`whop ${r.status} ${path}: ${txt.slice(0, 300)}`);
      err.status = r.status; err.body = j;
      throw err;
    }
    return j;
  }

  // A one-time checkout on the VENDOR's Whop company. Returns purchase_url.
  async function whopCheckoutForInvoice(vendor, inq, inv, inquiryId, invoiceId, tip) {
    const companyId = str(vendor.payments && vendor.payments.whopCompanyId);
    if (!companyId) throw new Error('vendor has no whopCompanyId');
    const amount = round2(num(inv.total) + num(tip));
    if (amount < 1) throw new Error('amount too small');
    const cfg = await whop('/checkout_configurations', 'POST', {
      plan: {
        company_id: companyId,
        initial_price: amount,
        currency: 'usd',
        plan_type: 'one_time',
        title: `${str(inv.title) || 'Invoice'} - ${str(vendor.name) || 'your vendor'}`,
      },
      metadata: {
        lazo: 'invoice', inquiryId, invoiceId,
        vendorId: str(inv.vendorId), coupleUid: str(inq.coupleUid),
        tip: String(round2(num(tip))),
      },
      redirect_url: `${APP}?thread=${encodeURIComponent(inquiryId)}&paid=${encodeURIComponent(invoiceId)}`,
    });
    const url = str(cfg.purchase_url || cfg.url || (cfg.data && cfg.data.purchase_url));
    if (!url) throw new Error('whop returned no purchase_url');
    return { url, checkoutId: str(cfg.id) };
  }

  // Standard-Webhooks style verification (webhook-id / webhook-timestamp /
  // webhook-signature, secret optionally prefixed whsec_ and base64).
  // CHECK on deploy that this matches what whopWebhook in the default codebase
  // does - if that one verifies differently, copy its verifier here.
  function verifyStandardWebhook(req, secret) {
    const id = str(req.get('webhook-id'));
    const ts = str(req.get('webhook-timestamp'));
    const sig = str(req.get('webhook-signature'));
    if (!id || !ts || !sig) return false;
    if (Math.abs(Date.now() / 1000 - Number(ts)) > 300) return false;
    const raw = req.rawBody ? req.rawBody.toString('utf8') : JSON.stringify(req.body || {});
    let key = secret;
    if (key.startsWith('whsec_')) key = key.slice(6);
    let keyBuf;
    try { keyBuf = Buffer.from(key, 'base64'); } catch (e) { keyBuf = Buffer.from(key); }
    if (!keyBuf.length) keyBuf = Buffer.from(key);
    const expected = crypto.createHmac('sha256', keyBuf).update(`${id}.${ts}.${raw}`).digest('base64');
    return sig.split(' ').some((part) => {
      const v = part.includes(',') ? part.split(',')[1] : part;
      try { return crypto.timingSafeEqual(Buffer.from(v), Buffer.from(expected)); } catch (e) { return false; }
    });
  }

  // ------------------------------------------------------- mark an invoice --
  async function markInvoicePaid(inquiryId, invoiceId, via, extra) {
    const invRef = db().collection('inquiries').doc(inquiryId).collection('invoices').doc(invoiceId);
    const res = await db().runTransaction(async (tx) => {
      const s = await tx.get(invRef);
      if (!s.exists) return { ok: false, reason: 'missing' };
      const inv = s.data();
      if (str(inv.status) === 'paid') return { ok: true, already: true, inv };
      tx.set(invRef, {
        status: 'paid', paidAt: FieldValue.serverTimestamp(), paidVia: via, ...(extra || {}),
      }, { merge: true });
      return { ok: true, inv };
    });
    if (!res.ok || res.already) return res;
    const inv = res.inv;
    // roll the plan + inquiry summary
    const planId = str(inv.planId);
    const inqRef = db().collection('inquiries').doc(inquiryId);
    if (planId) {
      const all = await inqRef.collection('invoices').where('planId', '==', planId).get();
      let open = 0, paid = 0, nextDue = null;
      all.forEach((d) => {
        const m = d.data();
        if (d.id === invoiceId || str(m.status) === 'paid') { paid += num(m.total); return; }
        if (str(m.status) === 'void') return;
        open += num(m.total);
        const dd = toDate(m.dueDate);
        if (dd && (!nextDue || dd < nextDue)) nextDue = dd;
      });
      await inqRef.set({
        paymentPlan: {
          planId, paid: round2(paid), outstanding: round2(open),
          nextDue: nextDue ? Timestamp.fromDate(nextDue) : null,
          status: open <= 0 ? 'complete' : 'active',
        },
        invoiceStatus: open <= 0 ? 'paid' : 'partial',
        invoiceUpdatedAt: FieldValue.serverTimestamp(),
      }, { merge: true });
    } else {
      await inqRef.set({ invoiceStatus: 'paid', invoiceUpdatedAt: FieldValue.serverTimestamp() }, { merge: true });
    }
    const tip = num(extra && extra.tip);
    await threadSystem(inquiryId,
      `Payment received - ${str(inv.title) || 'Invoice'} (${money(inv.total)}${tip > 0 ? ` + ${money(tip)} tip` : ''}). Thank you!`,
      { paymentReceipt: { invoiceId, via } });
    return res;
  }

  // ============================================================ FUNCTIONS ==

  // planCreate {inquiryId, vendorId, title, total, schedule:[{label, amount, dueDate:'YYYY-MM-DD'}],
  //             lateFee:{type:'flat'|'pct', amount, graceDays, every:'once'|'weekly'},
  //             tipAllowed:bool, autopay:'off'|'optional'|'required', note}
  // Amounts must sum to total (+/- $1 rounding is fixed on the last installment).
  const planCreate = onCall({ memory: '256MiB' }, async (request) => {
    const uid = request.auth && request.auth.uid;
    if (!uid) throw new HttpsError('unauthenticated', 'Sign in first.');
    const d = request.data || {};
    const inquiryId = str(d.inquiryId), vendorId = str(d.vendorId);
    if (!inquiryId || !vendorId) throw new HttpsError('invalid-argument', 'inquiryId and vendorId required');
    if (!(await vendorAccess(uid, vendorId))) throw new HttpsError('permission-denied', 'Not your vendor.');
    const inqRef = db().collection('inquiries').doc(inquiryId);
    const inqSnap = await inqRef.get();
    if (!inqSnap.exists || str(inqSnap.get('vendorId')) !== vendorId) throw new HttpsError('not-found', 'Thread not found.');
    const inq = inqSnap.data();

    const total = round2(num(d.total));
    const schedule = Array.isArray(d.schedule) ? d.schedule : [];
    if (total <= 0 || schedule.length < 1 || schedule.length > 24) throw new HttpsError('invalid-argument', 'Give a total and 1-24 installments.');
    let sum = 0;
    const rows = schedule.map((s, i) => {
      const amt = round2(num(s.amount));
      const due = new Date(str(s.dueDate).length === 10 ? str(s.dueDate) + 'T12:00:00' : str(s.dueDate));
      if (!(amt > 0) || isNaN(due.getTime())) throw new HttpsError('invalid-argument', `Installment ${i + 1} needs an amount and a date.`);
      sum += amt;
      return { label: str(s.label) || (i === 0 ? 'Retainer' : `Payment ${i + 1}`), amount: amt, due };
    });
    const drift = round2(total - sum);
    if (Math.abs(drift) > 1) throw new HttpsError('invalid-argument', `Installments total ${money(sum)}, not ${money(total)}.`);
    if (drift !== 0) rows[rows.length - 1].amount = round2(rows[rows.length - 1].amount + drift);

    const lf = d.lateFee && typeof d.lateFee === 'object' ? d.lateFee : null;
    const lateFee = lf && num(lf.amount) > 0 ? {
      type: str(lf.type) === 'pct' ? 'pct' : 'flat',
      amount: round2(num(lf.amount)),
      graceDays: Math.max(0, Math.min(30, Math.round(num(lf.graceDays)))),
      every: str(lf.every) === 'weekly' ? 'weekly' : 'once',
    } : null;
    const autopay = ['off', 'optional', 'required'].includes(str(d.autopay)) ? str(d.autopay) : 'off';
    const tipAllowed = d.tipAllowed === true;
    const title = str(d.title).trim() || 'Payment plan';

    const planRef = inqRef.collection('invoices').doc(); // id reused as planId
    const planId = planRef.id;
    const batch = db().batch();
    const ids = [];
    rows.forEach((r, i) => {
      const ref = i === 0 ? planRef : inqRef.collection('invoices').doc();
      ids.push(ref.id);
      batch.set(ref, {
        vendorId, coupleUid: str(inq.coupleUid),
        title: `${title} - ${r.label}`,
        lineItems: [{ label: `${r.label} (${i + 1} of ${rows.length})`, amount: r.amount }],
        total: r.amount, dueDate: Timestamp.fromDate(r.due),
        status: 'sent', createdAt: FieldValue.serverTimestamp(), sentAt: FieldValue.serverTimestamp(),
        planId, installmentIndex: i, installmentCount: rows.length, planTotal: total,
        lateFee, tipAllowed, autopay, note: str(d.note).slice(0, 400),
      });
    });
    const first = rows[0], last = rows[rows.length - 1];
    batch.set(inqRef, {
      paymentPlan: { planId, total, paid: 0, outstanding: total, count: rows.length, nextDue: Timestamp.fromDate(first.due), status: 'active' },
      invoiceStatus: 'sent', invoiceUpdatedAt: FieldValue.serverTimestamp(), lastInvoiceId: ids[0],
    }, { merge: true });
    await batch.commit();

    const lines = rows.map((r) => `${r.label}: ${money(r.amount)} due ${fmtDate(r.due)}`).join(' · ');
    await threadSystem(inquiryId,
      `I've set up your payment plan - ${money(total)} in ${rows.length} payment${rows.length === 1 ? '' : 's'}. ${lines}. Each one is right here in this thread when it's due.${lateFee ? ` (${lateFee.type === 'pct' ? lateFee.amount + '%' : money(lateFee.amount)} late fee after ${lateFee.graceDays} day${lateFee.graceDays === 1 ? '' : 's'}.)` : ''}`,
      { paymentPlan: { planId, count: rows.length, total } });

    try {
      const c = await coupleContact(inq);
      if (c.email) {
        const vS = await db().collection('vendors').doc(vendorId).get();
        await sendEmail(c.email, `Your payment plan from ${str(inq.vendorName) || 'your vendor'} is ready`,
          brandWrap(vS.exists ? vS.data() : null, `<p>Hi ${c.name},</p><p>${str(inq.vendorName) || 'Your vendor'} set up a payment plan on Lazo: <b>${money(total)}</b> in ${rows.length} payment${rows.length === 1 ? '' : 's'}.</p><ul>${rows.map((r) => `<li>${r.label}: ${money(r.amount)} - due ${fmtDate(r.due)}</li>`).join('')}</ul><p>The first one is due ${fmtDate(first.due)} and the last ${fmtDate(last.due)}. Pay each one from your thread: <a href="${APP}?thread=${inquiryId}">open Lazo</a>.</p>`),
          `Your payment plan: ${money(total)} in ${rows.length} payments. ${lines}. Pay from ${APP}?thread=${inquiryId}`);
      }
    } catch (e) { console.warn('planCreate email', e.message); }

    return { planId, invoiceIds: ids };
  });

  // planCancel {inquiryId, vendorId, planId} - voids every unpaid installment.
  const planCancel = onCall({ memory: '256MiB' }, async (request) => {
    const uid = request.auth && request.auth.uid;
    if (!uid) throw new HttpsError('unauthenticated', 'Sign in first.');
    const d = request.data || {};
    const inquiryId = str(d.inquiryId), vendorId = str(d.vendorId), planId = str(d.planId);
    if (!inquiryId || !vendorId || !planId) throw new HttpsError('invalid-argument', 'missing ids');
    if (!(await vendorAccess(uid, vendorId))) throw new HttpsError('permission-denied', 'Not your vendor.');
    const inqRef = db().collection('inquiries').doc(inquiryId);
    const all = await inqRef.collection('invoices').where('planId', '==', planId).get();
    const batch = db().batch();
    let voided = 0, paid = 0;
    all.forEach((s) => {
      const m = s.data();
      if (str(m.status) === 'paid') { paid += num(m.total); return; }
      batch.set(s.ref, { status: 'void', voidedAt: FieldValue.serverTimestamp() }, { merge: true });
      voided++;
    });
    batch.set(inqRef, {
      paymentPlan: { planId, status: 'cancelled', paid: round2(paid), outstanding: 0, nextDue: null },
      invoiceStatus: paid > 0 ? 'partial' : 'void', invoiceUpdatedAt: FieldValue.serverTimestamp(),
    }, { merge: true });
    await batch.commit();
    if (voided) await threadSystem(inquiryId, `The remaining ${voided} scheduled payment${voided === 1 ? '' : 's'} on the plan ${voided === 1 ? 'has' : 'have'} been cancelled.`);
    return { voided };
  });

  // GET ?inquiry=&invoice=&tip=   -> { url }
  // Whop vendors get a Whop checkout on their own company. Everyone else is
  // passed through to the legacy invoiceCheckout (Stripe / Square) untouched.
  const payCheckout = onRequest({ cors: true, invoker: 'public', memory: '256MiB', secrets: [WHOP_API_KEY] }, async (req, res) => {
    try {
      const inquiryId = str(req.query.inquiry), invoiceId = str(req.query.invoice);
      const tip = Math.max(0, Math.min(5000, round2(num(req.query.tip))));
      if (!inquiryId || !invoiceId) return res.status(400).json({ error: 'inquiry and invoice required' });
      const inqRef = db().collection('inquiries').doc(inquiryId);
      const [inqS, invS] = await Promise.all([inqRef.get(), inqRef.collection('invoices').doc(invoiceId).get()]);
      if (!inqS.exists || !invS.exists) return res.status(404).json({ error: 'not found' });
      const inq = inqS.data(), inv = invS.data();
      if (str(inv.status) === 'paid') return res.status(409).json({ error: 'already paid' });
      if (str(inv.status) === 'void') return res.status(410).json({ error: 'cancelled' });
      const vS = await db().collection('vendors').doc(str(inv.vendorId || inq.vendorId)).get();
      const vendor = vS.exists ? vS.data() : {};
      const processor = str(vendor.payments && vendor.payments.processor);
      if (processor === 'whop') {
        const useTip = inv.tipAllowed === true ? tip : 0;
        const out = await whopCheckoutForInvoice(vendor, inq, inv, inquiryId, invoiceId, useTip);
        await invS.ref.set({ lastCheckout: { via: 'whop', id: out.checkoutId, tip: useTip, at: FieldValue.serverTimestamp() } }, { merge: true });
        return res.json({ url: out.url, via: 'whop' });
      }
      // legacy pass-through (Stripe / Square), same query contract
      const r = await fetch(`${LEGACY_CHECKOUT}?inquiry=${encodeURIComponent(inquiryId)}&invoice=${encodeURIComponent(invoiceId)}`);
      const txt = await r.text();
      res.status(r.status).set('content-type', 'application/json').send(txt || '{}');
    } catch (e) {
      console.error('payCheckout', e);
      res.status(500).json({ error: 'checkout failed', detail: e.message });
    }
  });

  // App-level Whop webhook: events on every company that installed the app.
  const whopAppWebhook = onRequest({ invoker: 'public', memory: '256MiB', secrets: [WHOP_APP_WEBHOOK_SECRET] }, async (req, res) => {
    if (req.method !== 'POST') return res.status(405).send('POST only');
    if (!verifyStandardWebhook(req, WHOP_APP_WEBHOOK_SECRET.value())) return res.status(401).send('bad signature');
    const evt = req.body || {};
    const type = str(evt.type || evt.action || evt.event);
    const data = evt.data || evt.payload || {};
    const meta = data.metadata || (data.checkout_configuration && data.checkout_configuration.metadata) || (data.plan && data.plan.metadata) || {};
    try {
      if (type === 'payment.succeeded' && str(meta.lazo) === 'invoice') {
        await markInvoicePaid(str(meta.inquiryId), str(meta.invoiceId), 'whop', {
          whopPaymentId: str(data.id), whopCompanyId: str(data.company_id || (data.company && data.company.id)),
          tip: round2(num(meta.tip)), amountPaid: round2(num(data.total || data.amount || data.final_amount)),
        });
      } else if (type === 'payment.failed' && str(meta.lazo) === 'invoice') {
        const ref = db().collection('inquiries').doc(str(meta.inquiryId)).collection('invoices').doc(str(meta.invoiceId));
        await ref.set({ lastPaymentFailedAt: FieldValue.serverTimestamp(), lastPaymentError: str(data.failure_message || data.status).slice(0, 200) }, { merge: true });
      } else if (/^refund\.|^payment\.refunded/.test(type) && str(meta.lazo) === 'invoice') {
        const ref = db().collection('inquiries').doc(str(meta.inquiryId)).collection('invoices').doc(str(meta.invoiceId));
        await ref.set({ status: 'refunded', refundedAt: FieldValue.serverTimestamp(), refundAmount: round2(num(data.amount || data.total)) }, { merge: true });
      } else if (/dispute/.test(type) && str(meta.lazo) === 'invoice') {
        const ref = db().collection('inquiries').doc(str(meta.inquiryId)).collection('invoices').doc(str(meta.invoiceId));
        await ref.set({ disputed: true, disputedAt: FieldValue.serverTimestamp() }, { merge: true });
      }
      // everything else (installs, memberships on the vendor's other products) is ignored
      res.status(200).json({ ok: true });
    } catch (e) {
      console.error('whopAppWebhook', type, e);
      res.status(500).json({ ok: false });
    }
  });

  // whopVendorConnect {vendorId, companyId}
  // Step 1 (no companyId): returns the install link for the Lazo Payments app.
  // Step 2 (companyId): proves the app is installed on that company by
  // creating a $1 test checkout on it (never shown to anyone), then links it.
  const whopVendorConnect = onCall({ memory: '256MiB', secrets: [WHOP_API_KEY] }, async (request) => {
    const uid = request.auth && request.auth.uid;
    if (!uid) throw new HttpsError('unauthenticated', 'Sign in first.');
    const d = request.data || {};
    const vendorId = str(d.vendorId);
    if (!vendorId) throw new HttpsError('invalid-argument', 'vendorId required');
    if (!(await vendorAccess(uid, vendorId))) throw new HttpsError('permission-denied', 'Not your vendor.');
    const companyId = str(d.companyId).trim();
    if (!companyId) return { installUrl: WHOP_INSTALL_URL, step: 'install' };
    if (!/^biz_[A-Za-z0-9]{6,}$/.test(companyId)) throw new HttpsError('invalid-argument', 'That does not look like a Whop business id (biz_...).');
    try {
      await whop('/checkout_configurations', 'POST', {
        plan: { company_id: companyId, initial_price: 1, currency: 'usd', plan_type: 'one_time', title: 'Lazo link test' },
        metadata: { lazo: 'link-test', vendorId },
      });
    } catch (e) {
      if (e.status === 401 || e.status === 403 || e.status === 404) {
        throw new HttpsError('failed-precondition', 'Whop says the Lazo Payments app is not installed on that business yet. Install it, then try again.');
      }
      throw new HttpsError('unavailable', 'Whop did not answer - try again in a minute.');
    }
    await db().collection('vendors').doc(vendorId).set({
      payments: { processor: 'whop', whopCompanyId: companyId, connectedAt: FieldValue.serverTimestamp(), connectedBy: uid },
    }, { merge: true });
    return { ok: true, processor: 'whop', companyId };
  });

  const whopVendorDisconnect = onCall({ memory: '256MiB' }, async (request) => {
    const uid = request.auth && request.auth.uid;
    if (!uid) throw new HttpsError('unauthenticated', 'Sign in first.');
    const vendorId = str(request.data && request.data.vendorId);
    if (!vendorId || !(await vendorAccess(uid, vendorId))) throw new HttpsError('permission-denied', 'Not your vendor.');
    const vS = await db().collection('vendors').doc(vendorId).get();
    const fallback = vS.get('stripeChargesEnabled') === true ? 'stripe' : (vS.get('squareConnected') === true ? 'square' : 'links');
    await db().collection('vendors').doc(vendorId).set({
      payments: { processor: fallback, whopCompanyId: FieldValue.delete(), disconnectedAt: FieldValue.serverTimestamp() },
    }, { merge: true });
    return { ok: true, processor: fallback };
  });

  // Daily: reminders 3 days before and on the due date, overdue reminders,
  // late fees after the grace period, and autopay attempts.
  //
  // Autopay v1: on a Whop vendor, an installment marked autopay 'required'
  // still needs a card the couple saved - Whop's saved-card charge for a
  // later one-time plan is not something this build calls. Until that call
  // is confirmed, autopay sends the pay link on the due date (email + thread)
  // and the couple taps once. Stripe/Square off-session charges live in the
  // default codebase (stripeWebhook), which is not in this repo yet.
  const paymentPlanSweep = onSchedule({
    schedule: '0 9 * * *', timeZone: 'America/Phoenix', memory: '512MiB', timeoutSeconds: 300, secrets: [RESEND_API_KEY],
  }, async () => {
    const today = dayStart(new Date());
    const in3 = new Date(today); in3.setDate(in3.getDate() + 3);
    const todayKey = today.toISOString().slice(0, 10);
    const snap = await db().collectionGroup('invoices').where('status', '==', 'sent').get();
    let reminded = 0, feed = 0;
    for (const s of snap.docs) {
      const inv = s.data();
      if (inv.demo === true) continue;
      const due = toDate(inv.dueDate);
      if (!due) continue;
      const dueDay = dayStart(due);
      const inquiryId = s.ref.parent.parent.id;
      const daysLate = Math.round((today - dueDay) / 86400000); // negative = not yet due
      const marks = inv.reminders || {};
      let kind = null;
      if (daysLate === -3 && !marks.soon) kind = 'soon';
      else if (daysLate === 0 && !marks.due) kind = 'due';
      else if (daysLate > 0 && daysLate % 7 === 0 && marks.lastOverdue !== todayKey) kind = 'overdue';

      // late fee, once per policy period, after grace
      const lf = inv.lateFee;
      if (lf && daysLate > num(lf.graceDays)) {
        const applied = inv.lateFeeApplied || {};
        const period = lf.every === 'weekly' ? Math.floor((daysLate - num(lf.graceDays) - 1) / 7) : 0;
        const key = `p${period}`;
        if (!applied[key]) {
          const fee = lf.type === 'pct' ? round2(num(inv.planTotal || inv.total) * num(lf.amount) / 100) : round2(num(lf.amount));
          if (fee > 0) {
            const items = Array.isArray(inv.lineItems) ? inv.lineItems.slice() : [];
            items.push({ label: `Late fee (${fmtDate(new Date())})`, amount: fee });
            await s.ref.set({
              lineItems: items, total: round2(num(inv.total) + fee),
              lateFeeApplied: { ...applied, [key]: FieldValue.serverTimestamp() },
            }, { merge: true });
            await threadSystem(inquiryId, `A late fee of ${money(fee)} was added to "${str(inv.title)}" - it was due ${fmtDate(due)}.`);
            inv.total = round2(num(inv.total) + fee);
            feed++;
          }
        }
      }
      if (!kind) continue;

      let inq;
      try { const is = await db().collection('inquiries').doc(inquiryId).get(); inq = is.exists ? is.data() : null; } catch (e) { inq = null; }
      if (!inq) continue;
      const c = await coupleContact(inq);
      const vendorName = str(inq.vendorName) || 'your vendor';
      const link = `${APP}?thread=${inquiryId}`;
      const text = kind === 'soon'
        ? `Heads up - "${str(inv.title)}" (${money(inv.total)}) is due ${fmtDate(due)}.`
        : kind === 'due'
          ? `"${str(inv.title)}" (${money(inv.total)}) is due today.${str(inv.autopay) === 'required' ? ' Pay it here to keep your date.' : ''}`
          : `"${str(inv.title)}" (${money(inv.total)}) was due ${fmtDate(due)} - it's still open.`;
      try {
        await threadSystem(inquiryId, text + ' Pay it right here in the thread.');
        if (c.email) {
          const vS = await db().collection('vendors').doc(str(inv.vendorId || inq.vendorId)).get();
          await sendEmail(c.email, `${vendorName}: ${kind === 'overdue' ? 'payment past due' : 'payment ' + (kind === 'soon' ? 'due in 3 days' : 'due today')}`,
            brandWrap(vS.exists ? vS.data() : null, `<p>Hi ${c.name},</p><p>${text}</p><p><a href="${link}">Open the thread on Lazo</a> and tap Pay.</p>`),
            `${text} Pay at ${link}`);
        }
        const patch = { reminders: { ...marks } };
        if (kind === 'soon') patch.reminders.soon = FieldValue.serverTimestamp();
        if (kind === 'due') patch.reminders.due = FieldValue.serverTimestamp();
        if (kind === 'overdue') patch.reminders.lastOverdue = todayKey;
        await s.ref.set(patch, { merge: true });
        reminded++;
      } catch (e) { console.warn('sweep reminder', inquiryId, e.message); }
    }
    console.log(`paymentPlanSweep: ${snap.size} open, ${reminded} reminded, ${feed} late fees`);
  });

  // ------------------------------------------------ the login-free page --
  // The couple (or a couple who never made a Lazo account - Build B leads)
  // opens meetlazo.com/f/{inquiry}?t=<token>. The token is a random secret
  // on the inquiry doc, minted by fileLink; the worker calls fileView with
  // it and renders. No Firestore reads happen unauthenticated.
  function newToken() { return crypto.randomBytes(18).toString('base64url'); }

  const fileLink = onCall({ memory: '256MiB' }, async (request) => {
    const uid = request.auth && request.auth.uid;
    if (!uid) throw new HttpsError('unauthenticated', 'Sign in first.');
    const d = request.data || {};
    const inquiryId = str(d.inquiryId), vendorId = str(d.vendorId);
    if (!inquiryId || !vendorId || !(await vendorAccess(uid, vendorId))) throw new HttpsError('permission-denied', 'Not your vendor.');
    const ref = db().collection('inquiries').doc(inquiryId);
    const s = await ref.get();
    if (!s.exists || str(s.get('vendorId')) !== vendorId) throw new HttpsError('not-found', 'Thread not found.');
    let t = str(s.get('fileToken'));
    if (!t || d.rotate === true) {
      t = newToken();
      await ref.set({ fileToken: t, fileTokenAt: FieldValue.serverTimestamp() }, { merge: true });
    }
    return { url: `https://meetlazo.com/f/${inquiryId}?t=${t}` };
  });

  const fileView = onRequest({ cors: true, invoker: 'public', memory: '256MiB' }, async (req, res) => {
    try {
      const inquiryId = str(req.query.inquiry), t = str(req.query.t);
      if (!inquiryId || !t) return res.status(400).json({ error: 'bad request' });
      const ref = db().collection('inquiries').doc(inquiryId);
      const s = await ref.get();
      if (!s.exists) return res.status(404).json({ error: 'not found' });
      const inq = s.data();
      const want = str(inq.fileToken);
      if (!want || want.length !== t.length || !crypto.timingSafeEqual(Buffer.from(want), Buffer.from(t))) return res.status(403).json({ error: 'bad token' });
      const [vS, invS, propS, conS] = await Promise.all([
        db().collection('vendors').doc(str(inq.vendorId)).get(),
        ref.collection('invoices').orderBy('createdAt', 'asc').get(),
        ref.collection('proposals').orderBy('createdAt', 'desc').limit(1).get(),
        ref.collection('contracts').orderBy('createdAt', 'desc').limit(1).get(),
      ]);
      const v = vS.exists ? vS.data() : {};
      const ts = (x) => { const d = toDate(x); return d ? d.toISOString() : null; };
      const invoices = invS.docs.map((d) => { const m = d.data(); return {
        id: d.id, title: str(m.title), total: round2(num(m.total)), status: str(m.status) || 'sent',
        dueDate: ts(m.dueDate), paidAt: ts(m.paidAt), lineItems: Array.isArray(m.lineItems) ? m.lineItems : [],
        planId: str(m.planId) || null, installmentIndex: m.installmentIndex ?? null, installmentCount: m.installmentCount ?? null,
        tipAllowed: m.tipAllowed === true, autopay: str(m.autopay) || 'off', lateFee: m.lateFee || null,
      }; }).filter((i) => i.status !== 'void');
      const prop = propS.empty ? null : (() => { const m = propS.docs[0].data(); return { title: str(m.title), price: round2(num(m.price)), includes: m.includes || [], note: str(m.note), status: str(m.status) }; })();
      const con = conS.empty ? null : (() => { const m = conS.docs[0].data(); return { status: str(m.status), signedAt: ts(m.signedAt), title: str(m.title) || 'Service agreement' }; })();
      const paid = invoices.filter((i) => i.status === 'paid').reduce((a, i) => a + i.total, 0);
      const open = invoices.filter((i) => i.status === 'sent').reduce((a, i) => a + i.total, 0);
      const brand = v.brand && typeof v.brand === 'object' ? v.brand : {};
      res.set('cache-control', 'no-store').json({
        inquiryId,
        vendor: { id: str(inq.vendorId), name: str(v.name), logoUrl: str(v.logoUrl), coverUrl: str(v.coverUrl), category: str(v.category || (Array.isArray(v.categories) && v.categories[0])), phone: str(v.phone), email: str(v.email), primary: str(brand.primary), accent: str(brand.accent) },
        couple: { name: str(inq.coupleName), weddingDate: str(inq.structuredIntent && inq.structuredIntent.weddingDate), venue: str(inq.structuredIntent && inq.structuredIntent.venue) },
        status: str(inq.status), contractStatus: str(inq.contractStatus), proposal: prop, contract: con,
        invoices, totals: { paid: round2(paid), open: round2(open) }, paymentPlan: inq.paymentPlan || null,
        processor: str(v.payments && v.payments.processor) || (v.stripeChargesEnabled ? 'stripe' : (v.squareConnected ? 'square' : 'links')),
        paymentLinks: Array.isArray(v.paymentLinks) ? v.paymentLinks : [],
      });
    } catch (e) { console.error('fileView', e); res.status(500).json({ error: 'failed' }); }
  });

  return { planCreate, planCancel, payCheckout, whopAppWebhook, whopVendorConnect, whopVendorDisconnect, paymentPlanSweep, fileLink, fileView };
};

// END OF FILE - JC-LAZO-FNDASH-0913-011
