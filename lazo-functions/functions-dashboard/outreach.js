// functions-dashboard/outreach.js
// Build ID: JC-LAZO-FNDASH-1018-OUTREACH-001
//
// THE "CLAIM YOUR PROFILE" CAMPAIGN'S LINKS. generate/outreach_emails.py (lazo-directory) writes one
// outreach/{vendorId} doc per unclaimed vendor with a scraped address and a per-vendor token; Smartlead
// sends the email. Every link in that email that is ours comes back through here, proxied by the worker
// exactly like the /join/ links (worker/src/index.js, JC-LAZO-WORKER-1018-CLAIM):
//
//   outreachGo    GET ?t=        meetlazo.com/claim/{token}        logs the click, 302 to the app's claim
//                                                                  screen (app.meetlazo.com/?claim={vendorId})
//   outreachStop  GET ?t=        meetlazo.com/claim/{token}/stop   one-click unsubscribe (also the
//                                                                  List-Unsubscribe target; POST accepted)
//   onClaimRequestOutreach       claimRequests/{id} created        when the vendor came from the campaign,
//                                                                  stamps claimRequests.claimedVia='outreach'
//                                                                  and outreach.status='claimed'
//
// The outreach collection is admin-only (no rule names it); everything here runs on the Admin SDK, so the
// token in the URL is the only credential and it is compared in constant time. Nothing here sends mail.

'use strict';

const crypto = require('crypto');
const { onRequest } = require('firebase-functions/v2/https');
const { onDocumentCreated } = require('firebase-functions/v2/firestore');
const admin = require('firebase-admin');

const APP = 'https://app.meetlazo.com/';
const db = () => admin.firestore();
const { FieldValue } = admin.firestore;
const str = (v) => (v == null ? '' : String(v));
const tokenOk = (want, t) => !!want && !!t && want.length === t.length && crypto.timingSafeEqual(Buffer.from(want), Buffer.from(t));

const page = (title, body) => `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>${title}</title></head><body style="margin:0;background:#FAF6F0;font-family:Helvetica,Arial,sans-serif;color:#241E2B"><div style="max-width:460px;margin:12vh auto;padding:28px 22px;background:#fff;border:1px solid #EADFCB;border-radius:18px;text-align:center"><p style="font-family:Georgia,serif;font-size:26px;color:#3D1C3B;margin:0 0 10px">${title}</p><p style="font-size:15px;line-height:1.6;color:#5B5363;margin:0">${body}</p></div></body></html>`;

// the token is the doc's own field, so the lookup is a single-field query (index-free: equality on one field)
async function byToken(t) {
  if (!/^[A-Za-z0-9_-]{16,40}$/.test(t)) return null;
  const q = await db().collection('outreach').where('token', '==', t).limit(1).get();
  if (q.empty) return null;
  const s = q.docs[0];
  return tokenOk(str(s.get('token')), t) ? s : null;
}
const event = (type, s, extra) => db().collection('outreachEvents').add({ type, vendorId: s ? s.id : null, at: FieldValue.serverTimestamp(), ...(extra || {}) }).catch(() => {});

module.exports = function outreachModule() {

  // GET ?t=  -> 302 to the app's claim screen for this vendor
  const outreachGo = onRequest({ invoker: 'public', memory: '256MiB' }, async (req, res) => {
    res.set('cache-control', 'no-store');
    try {
      const t = str(req.query.t).slice(0, 80);
      const s = await byToken(t);
      if (!s) return res.redirect(302, APP);
      const d = s.data();
      const first = !d.clickedAt;
      await s.ref.set({
        clicks: FieldValue.increment(1), lastClickAt: FieldValue.serverTimestamp(),
        ...(first ? { clickedAt: FieldValue.serverTimestamp() } : {}),
        // a click moves 'sent' forward; it never overwrites a terminal state
        ...(['listed', 'queued', 'sent'].includes(str(d.status)) ? { status: 'clicked' } : {}),
      }, { merge: true });
      await event('click', s, { first, ua: str(req.get('user-agent')).slice(0, 160) });
      return res.redirect(302, `${APP}?claim=${encodeURIComponent(s.id)}&src=outreach`);
    } catch (e) { console.error('outreachGo', e); return res.redirect(302, APP); }
  });

  // GET or POST ?t=  -> unsubscribed: suppressed in every later export (status != listed)
  const outreachStop = onRequest({ invoker: 'public', memory: '256MiB' }, async (req, res) => {
    const done = (title, body, code) => res.status(code || 200).set('content-type', 'text/html; charset=utf-8').set('cache-control', 'no-store').send(page(title, body));
    try {
      const t = str(req.query.t || (req.body && req.body.t)).slice(0, 80);
      const s = await byToken(t);
      if (!s) return done('Link not recognised', 'This link has expired. Reply to the email and we will take you off the list by hand.', 404);
      if (str(s.get('status')) !== 'unsubscribed') {
        await s.ref.set({ status: 'unsubscribed', unsubscribedAt: FieldValue.serverTimestamp(), unsubscribedVia: req.method === 'POST' ? 'header' : 'link' }, { merge: true });
        await event('unsubscribe', s, { via: req.method });
      }
      if (req.method === 'POST') return res.status(200).set('cache-control', 'no-store').send('ok');   // RFC 8058 one-click
      return done('Done.', `No more email from Lazo about ${str(s.get('name')) || 'this listing'}. The page itself stays up; reply to the email if you would rather it came down too.`);
    } catch (e) { console.error('outreachStop', e); return done('Something went wrong', 'Try the link again in a minute.', 500); }
  });

  // claimRequests/{id} created -> if this vendor was emailed, say so on both sides
  const onClaimRequestOutreach = onDocumentCreated({ document: 'claimRequests/{reqId}', region: 'us-central1', memory: '256MiB' }, async (event_) => {
    const snap = event_.data;
    if (!snap) return;
    const vendorId = str(snap.get('vendorId'));
    if (!vendorId) return;
    const o = await db().collection('outreach').doc(vendorId).get();
    if (!o.exists || !['sent', 'clicked'].includes(str(o.get('status')))) return;
    await Promise.all([
      snap.ref.set({ claimedVia: 'outreach', outreachToken: str(o.get('token')) }, { merge: true }),
      o.ref.set({ status: 'claimed', claimedAt: FieldValue.serverTimestamp(), claimRequestId: snap.id }, { merge: true }),
      event('claim', o, { claimRequestId: snap.id }),
    ]);
  });

  return { outreachGo, outreachStop, onClaimRequestOutreach };
};
