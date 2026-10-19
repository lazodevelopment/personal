// functions-dashboard/couples.js
// Build ID: JC-LAZO-FNDASH-1019-COUPLES-001
//
// THE "COME PLAN ON LAZO" COUPLES CAMPAIGN. Couples who inquired through Zola / The Knot to a studio that plans
// with Lazo (Atavia Weddings, Elizabeth Scott Weddings) get ONE email from Lazo through Smartlead. The list lives in
// coupleOutreach/{sha256(email)[:28]} (admin-only: no rule names it), written by lazo-directory/generate/
// couple_outreach.py (backfill) and by coupleIntake (the studios' Gmail intake scripts, LazoCouples.gs). Mirror of
// outreach.js + outreach-daily.js, proxied by the worker like /claim/:
//
//   coupleGo      GET ?t=          meetlazo.com/plan/{token}       logs the click, 302 to app.meetlazo.com/?src=couples&t=
//   coupleStop    GET|POST ?t=     meetlazo.com/plan/{token}/stop  one-click unsubscribe (RFC 8058 POST accepted)
//   coupleIntake  POST json        header x-lazo-key = secret COUPLE_INTAKE_KEY; body {brand, marketplace, names,
//                                  email, wedding_date, venue, inquired_at} -> coupleOutreach doc, status listed with
//                                  holdUntil = now + COUPLE_HOLD_DAYS (3) so the studio's own replies go first; relay
//                                  addresses (@vmkt-message.zola.com, @zola.com, @member.theknot.com) stored as skipped
//   coupleDaily   08:15 Phoenix    sync Smartlead flags (bounced/replied/unsubscribed) -> status; feed every listed
//                                  couple whose hold is over to the couples campaign (SMARTLEAD_COUPLES_CAMPAIGN_ID),
//                                  status queued. coupleDailyNow = admin callable {dryRun, syncOnly}.
//   onUserCreatedCouple            users/{uid} created with an email on the list -> status signedUp (no index: the doc
//                                  id IS the email hash)
//
// Nothing here sends mail. Secrets: COUPLE_INTAKE_KEY, SMARTLEAD_API_KEY.

'use strict';

const crypto = require('crypto');
const { onRequest, onCall, HttpsError } = require('firebase-functions/v2/https');
const { onSchedule } = require('firebase-functions/v2/scheduler');
const { onDocumentCreated } = require('firebase-functions/v2/firestore');
const { defineSecret } = require('firebase-functions/params');
const admin = require('firebase-admin');

const COUPLE_INTAKE_KEY = defineSecret('COUPLE_INTAKE_KEY');
const SMARTLEAD_API_KEY = defineSecret('SMARTLEAD_API_KEY');
const API = 'https://server.smartlead.ai/api/v1';
const CAMPAIGN = Number(process.env.SMARTLEAD_COUPLES_CAMPAIGN_ID || 4183795);
const HOLD_DAYS = Number(process.env.COUPLE_HOLD_DAYS || 3);
const SITE = 'https://meetlazo.com/';
const APP = 'https://app.meetlazo.com/';
const RELAY_RX = /@(vmkt-message\.zola\.com|zola\.com|member\.theknot\.com|theknot\.com|weddingpro\.com)$/i;
const MARKETPLACES = { zola: 'Zola', 'the knot': 'The Knot', theknot: 'The Knot', knot: 'The Knot' };

const db = () => admin.firestore();
const { FieldValue, Timestamp } = admin.firestore;
const str = (v) => (v == null ? '' : String(v));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const tokenOk = (want, t) => !!want && !!t && want.length === t.length && crypto.timingSafeEqual(Buffer.from(want), Buffer.from(t));
const coupleId = (email) => crypto.createHash('sha256').update(str(email).trim().toLowerCase()).digest('hex').slice(0, 28);
const newToken = () => crypto.randomBytes(16).toString('base64url');

const page = (title, body) => `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>${title}</title></head><body style="margin:0;background:#FAF6F0;font-family:Helvetica,Arial,sans-serif;color:#241E2B"><div style="max-width:460px;margin:12vh auto;padding:28px 22px;background:#fff;border:1px solid #EADFCB;border-radius:18px;text-align:center"><p style="font-family:Georgia,serif;font-size:26px;color:#3D1C3B;margin:0 0 10px">${title}</p><p style="font-size:15px;line-height:1.6;color:#5B5363;margin:0">${body}</p></div></body></html>`;

function prettyDate(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(str(iso));
  if (!m) return '';
  return new Date(Date.UTC(+m[1], +m[2] - 1, +m[3])).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
}
const firstName = (names) => (str(names).trim().split(/\s*(?:&|\band\b|\+|\/)\s*/)[0] || '').split(/\s+/)[0] || '';
const stateOf = (venue) => { const m = /,\s*([A-Z]{2})\s*$/.exec(str(venue).trim()); return m ? m[1] : ''; };
const isoDate = (v) => { const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(str(v).trim()); return m ? `${m[1]}-${m[2]}-${m[3]}` : ''; };

async function byToken(t) {
  if (!/^[A-Za-z0-9_-]{16,40}$/.test(t)) return null;
  const q = await db().collection('coupleOutreach').where('token', '==', t).limit(1).get();
  if (q.empty) return null;
  const s = q.docs[0];
  return tokenOk(str(s.get('token')), t) ? s : null;
}
const event = (type, s, extra) => db().collection('coupleOutreachEvents').add({ type, coupleId: s ? s.id : null, at: FieldValue.serverTimestamp(), ...(extra || {}) }).catch(() => {});

// ---------------- Smartlead ----------------
async function sl(key, method, path, { params = {}, body } = {}) {
  const q = new URLSearchParams({ ...params, api_key: key });
  let last;
  for (let attempt = 0; attempt < 4; attempt++) {
    const r = await fetch(`${API}${path}?${q}`, { method, headers: { 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined });
    if ([429, 500, 502, 503, 504].includes(r.status)) { last = r; await sleep(3000 * (attempt + 1)); continue; }
    if (!r.ok) throw new Error(`smartlead ${method} ${path} -> ${r.status}: ${(await r.text()).slice(0, 300)}`);
    return (r.headers.get('content-type') || '').includes('json') ? r.json() : r.text();
  }
  throw new Error(`smartlead ${method} ${path}: gave up (${last && last.status})`);
}

async function campaignLeads(key, emailStatus) {
  const out = [];
  for (let offset = 0; ; offset += 100) {
    const j = await sl(key, 'GET', `/campaigns/${CAMPAIGN}/leads`, { params: { offset, limit: 100, emailStatus } });
    const rows = j.data || [];
    out.push(...rows);
    if (rows.length < 100) return out;
  }
}

// Smartlead lead flags -> coupleOutreach.status (terminal states are never overwritten)
async function sync(key, log, dryRun) {
  const col = db().collection('coupleOutreach');
  const changed = {};
  for (const [status, flag] of [['bounced', 'is_bounced'], ['replied', 'is_replied'], ['unsubscribed', 'is_unsubscribed']]) {
    let rows;
    try { rows = await campaignLeads(key, flag); } catch (e) { log.push(`sync ${flag}: ${e.message}`); continue; }
    const ids = [...new Set(rows.map((r) => str((r.lead || {}).email).toLowerCase()).filter(Boolean))].map(coupleId);
    for (let i = 0; i < ids.length; i += 100) {
      const snaps = await db().getAll(...ids.slice(i, i + 100).map((id) => col.doc(id)));
      for (const d of snaps) {
        if (!d.exists) continue;
        const cur = str(d.get('status'));
        if (cur === status || cur === 'signedUp' || (cur === 'unsubscribed' && status !== 'unsubscribed')) continue;
        changed[status] = (changed[status] || 0) + 1;
        if (!dryRun) await d.ref.set({ status, [`${status}At`]: FieldValue.serverTimestamp(), smartleadFlag: flag }, { merge: true });
      }
    }
  }
  log.push(Object.keys(changed).length ? 'sync: ' + Object.entries(changed).map(([k, v]) => `${k} ${v}`).join(', ') : 'sync: nothing new');
  return changed;
}

// the lead row Smartlead gets; custom fields = the merge tags in generate/couple_email_render.js smartlead()
function toLead(d) {
  const v = d.data();
  const tok = str(v.token);
  const when = prettyDate(v.weddingDate);
  const where = str(v.venue).trim();
  return { email: str(v.email), first_name: str(v.firstName), last_name: '', company_name: '',
    custom_fields: { names: str(v.names), wedding_when: when ? ` on ${when}` : '', wedding_where: where ? ` in ${where}` : '',
      wedding_date: str(v.weddingDate), venue: where, state: str(v.state), brand: (v.brands || []).join('|'),
      plan_url: `${SITE}plan/${tok}`, stop_url: `${SITE}plan/${tok}/stop`, signup_url: `${APP}?src=couples&t=${encodeURIComponent(tok)}`,
      token: tok, couple_id: d.id } };
}

// every listed couple whose hold is over -> the campaign, status queued
async function feed(key, log, dryRun) {
  const now = Timestamp.now();
  const snap = await db().collection('coupleOutreach').where('status', '==', 'listed').get();
  const ready = snap.docs.filter((d) => { const h = d.get('holdUntil'); return !h || h.toMillis() <= now.toMillis(); })
    .filter((d) => str(d.get('email')) && !RELAY_RX.test(str(d.get('email'))));
  log.push(`feed: ${snap.size} listed, ${ready.length} past their hold`);
  if (!ready.length) return { added: 0, skipped: 0 };
  const batchId = `${new Date().toISOString().slice(0, 10)}-auto`;
  let added = 0, skipped = 0;
  for (let i = 0; i < ready.length; i += 400) {
    const chunk = ready.slice(i, i + 400);
    const leads = chunk.map(toLead);
    if (dryRun) { log.push(`feed (dry): would push ${leads.length}`); added += leads.length; continue; }
    const j = await sl(key, 'POST', `/campaigns/${CAMPAIGN}/leads`, { body: { lead_list: leads, settings: {
      ignore_global_block_list: false, ignore_unsubscribe_list: false, ignore_community_bounce_list: false, ignore_duplicate_leads_in_other_campaign: true } } });
    const a = Number(j.added_count || 0), s = Number(j.skipped_count || 0);
    added += a; skipped += s;
    const skippedEmails = new Set((j.skipped_leads || []).map((x) => str(typeof x === 'object' ? x.email : x).toLowerCase()));
    const wb = db().batch();
    for (const d of chunk) {
      if (skippedEmails.has(str(d.get('email')).toLowerCase())) wb.set(d.ref, { status: 'skipped', skipWhy: 'smartlead', batch: batchId }, { merge: true });
      else wb.set(d.ref, { status: 'queued', batch: batchId, queuedAt: FieldValue.serverTimestamp(), provider: 'smartlead', providerCampaignId: CAMPAIGN }, { merge: true });
    }
    await wb.commit();
    log.push(`feed: pushed ${leads.length} -> added ${a}, skipped ${s}`);
  }
  return { added, skipped, batchId };
}

async function run(key, { dryRun = false, syncOnly = false } = {}) {
  const log = [`run start: campaign ${CAMPAIGN}, dry ${dryRun}`];
  const started = new Date();
  const out = { dryRun };
  try {
    if (!CAMPAIGN) throw new Error('SMARTLEAD_COUPLES_CAMPAIGN_ID not set');
    out.sync = await sync(key, log, dryRun);
    if (!syncOnly) out.feed = await feed(key, log, dryRun);
  } catch (e) { log.push(`ERROR: ${e.message}`); out.error = e.message; }
  log.push('run end');
  const id = started.toISOString().replace(/[:T]/g, '-').slice(0, 16);
  await db().collection('coupleOutreachRuns').doc(id).set({ ...out, log, startedAt: started, finishedAt: FieldValue.serverTimestamp() }).catch(() => {});
  console.log(log.join('\n'));
  return out;
}

async function isAdmin(request) {
  const uid = request.auth && request.auth.uid;
  if (!uid) throw new HttpsError('unauthenticated', 'Sign in.');
  const tok = request.auth.token || {};
  const u = await db().collection('users').doc(uid).get();
  if (!(tok.admin === true || (u.exists && (u.get('isAdmin') === true || u.get('role') === 'admin')))) throw new HttpsError('permission-denied', 'Admins only.');
}

module.exports = function couplesModule() {

  // GET ?t=  -> 302 to the app, tagged as a couples-campaign arrival
  const coupleGo = onRequest({ invoker: 'public', memory: '256MiB' }, async (req, res) => {
    res.set('cache-control', 'no-store');
    try {
      const t = str(req.query.t).slice(0, 80);
      const s = await byToken(t);
      if (!s) return res.redirect(302, `${APP}?src=couples`);
      const d = s.data();
      const first = !d.clickedAt;
      await s.ref.set({
        clicks: FieldValue.increment(1), lastClickAt: FieldValue.serverTimestamp(),
        ...(first ? { clickedAt: FieldValue.serverTimestamp() } : {}),
        ...(['listed', 'queued', 'sent'].includes(str(d.status)) ? { status: 'clicked' } : {}),
      }, { merge: true });
      await event('click', s, { first, ua: str(req.get('user-agent')).slice(0, 160) });
      return res.redirect(302, `${APP}?src=couples&t=${encodeURIComponent(t)}`);
    } catch (e) { console.error('coupleGo', e); return res.redirect(302, APP); }
  });

  // GET or POST ?t=  -> unsubscribed (never fed again; Smartlead's own unsubscribe list is synced the other way)
  const coupleStop = onRequest({ invoker: 'public', memory: '256MiB' }, async (req, res) => {
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
      return done('Done.', 'No more email from Lazo. If you ever want to plan with us, meetlazo.com is always open.');
    } catch (e) { console.error('coupleStop', e); return done('Something went wrong', 'Try the link again in a minute.', 500); }
  });

  // POST {brand, marketplace, names, email, wedding_date, venue, inquired_at} from LazoCouples.gs (x-lazo-key)
  const coupleIntake = onRequest({ invoker: 'public', memory: '256MiB', secrets: [COUPLE_INTAKE_KEY] }, async (req, res) => {
    res.set('cache-control', 'no-store');
    if (req.method !== 'POST') return res.status(405).json({ ok: false, error: 'POST only' });
    const want = str(COUPLE_INTAKE_KEY.value()).trim();
    if (!tokenOk(want, str(req.get('x-lazo-key')))) return res.status(401).json({ ok: false, error: 'bad key' });
    try {
      const b = req.body || {};
      const email = str(b.email).trim().toLowerCase();
      if (!email || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return res.status(400).json({ ok: false, error: 'email' });
      const brand = /^(atavia|es)$/.test(str(b.brand)) ? str(b.brand) : 'unknown';
      const marketplace = MARKETPLACES[str(b.marketplace).trim().toLowerCase()] || str(b.marketplace).trim().slice(0, 40);
      const relay = RELAY_RX.test(email);
      const weddingDate = isoDate(b.wedding_date);
      const past = !!weddingDate && weddingDate < new Date().toISOString().slice(0, 10);
      const inquiredAt = isoDate(b.inquired_at) || new Date().toISOString().slice(0, 10);
      const ref = db().collection('coupleOutreach').doc(coupleId(email));
      const old = await ref.get();
      const o = old.exists ? old.data() : {};
      const doc = {
        email, names: str(b.names).trim().slice(0, 120) || str(o.names), firstName: firstName(b.names) || str(o.firstName),
        brands: FieldValue.arrayUnion(brand), marketplaces: FieldValue.arrayUnion(marketplace),
        venue: str(b.venue).trim().slice(0, 120) || str(o.venue), lastInquiry: inquiredAt, inquiries: FieldValue.increment(1),
        refs: FieldValue.arrayUnion(`${brand}:intake/${inquiredAt}`), updatedAt: FieldValue.serverTimestamp(),
      };
      if (weddingDate) doc.weddingDate = weddingDate;
      if (doc.venue) doc.state = stateOf(doc.venue);
      if (!old.exists) {
        Object.assign(doc, { token: newToken(), source: 'intake', firstInquiry: inquiredAt, createdAt: FieldValue.serverTimestamp() });
      }
      // status: a new couple is listed with a hold; relay / past weddings are skipped; a couple already past
      // listed/skipped (queued, sent, unsubscribed...) keeps that state
      if (!old.exists || ['listed', 'skipped'].includes(str(o.status))) {
        if (relay) Object.assign(doc, { status: 'skipped', skipWhy: 'relay_only' });
        else if (past) Object.assign(doc, { status: 'skipped', skipWhy: 'wedding_past' });
        else Object.assign(doc, { status: 'listed', skipWhy: FieldValue.delete(),
          holdUntil: Timestamp.fromMillis(Date.now() + HOLD_DAYS * 86400000) });
      }
      await ref.set(doc, { merge: true });
      await event('intake', { id: ref.id }, { brand, marketplace, relay, existed: old.exists });
      return res.json({ ok: true, id: ref.id, status: doc.status || str(o.status), relay, existed: old.exists });
    } catch (e) { console.error('coupleIntake', e); return res.status(500).json({ ok: false, error: 'server' }); }
  });

  const coupleDaily = onSchedule({ schedule: '15 8 * * *', timeZone: 'America/Phoenix', memory: '512MiB', timeoutSeconds: 540, secrets: [SMARTLEAD_API_KEY] },
    async () => { await run(SMARTLEAD_API_KEY.value()); });

  // admin-only manual trigger: { dryRun?, syncOnly? }
  const coupleDailyNow = onCall({ memory: '512MiB', timeoutSeconds: 540, secrets: [SMARTLEAD_API_KEY] }, async (request) => {
    await isAdmin(request);
    const d = request.data || {};
    return run(SMARTLEAD_API_KEY.value(), { dryRun: d.dryRun === true, syncOnly: d.syncOnly === true });
  });

  // users/{uid} created -> if that email is on the list, the campaign worked
  const onUserCreatedCouple = onDocumentCreated({ document: 'users/{uid}', region: 'us-central1', memory: '256MiB' }, async (event_) => {
    const snap = event_.data;
    if (!snap) return;
    const email = str(snap.get('email')).trim().toLowerCase();
    if (!email) return;
    const ref = db().collection('coupleOutreach').doc(coupleId(email));
    const o = await ref.get();
    if (!o.exists || ['signedUp', 'unsubscribed'].includes(str(o.get('status')))) return;
    await Promise.all([
      ref.set({ status: 'signedUp', signedUpAt: FieldValue.serverTimestamp(), userId: snap.id, signupSource: str(snap.get('signupSource')) }, { merge: true }),
      event('signup', o, { userId: snap.id, viaCampaign: ['clicked', 'sent', 'queued'].includes(str(o.get('status'))) }),
    ]);
  });

  return { coupleGo, coupleStop, coupleIntake, coupleDaily, coupleDailyNow, onUserCreatedCouple, _run: run };
};
