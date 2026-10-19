// functions-dashboard/outreach-daily.js
// Build ID: JC-LAZO-FNDASH-1019-OUTREACH-DAILY-001
//
// THE CLAIM CAMPAIGN, FED FROM THE CLOUD. The Python version (lazo-directory/generate/outreach_daily.py) ran from
// Jesse's PC through Task Scheduler and so only while he was logged in; this is the same job as a scheduled
// function, so it runs whether the PC is on or not. Every morning at 07:45 Phoenix:
//   1. sync   Smartlead lead flags (bounced / replied / unsubscribed) -> outreach/{vendorId}.status, so nobody is
//             mailed twice and Jesse's reports are right.
//   2. guard  the campaign's bounce rate since launch; over 3% (after 200 sent) = no feed that day.
//   3. feed   the next slice of outreach docs (status listed, Jesse's focus states in order, score >= 75,
//             wedding sites only, one per website, no address twice) -> POST to the Smartlead campaign
//             (400 per call) -> status sent with batch "<date>-auto". Slice size PER_DAY (1,500 = 30 boxes x 50).
// outreachDailyNow (callable, admin only) runs the same thing on demand, with dryRun.
// Secrets: SMARTLEAD_API_KEY. Campaign id: SMARTLEAD_CAMPAIGN_ID env, default 4176335.
// Log: one doc per run in outreachRuns/{yyyy-mm-dd-HHMM}.

'use strict';

const { onSchedule } = require('firebase-functions/v2/scheduler');
const { onCall, HttpsError } = require('firebase-functions/v2/https');
const { defineSecret } = require('firebase-functions/params');
const admin = require('firebase-admin');
const METROS = require('./outreach-metros.json');

const SMARTLEAD_API_KEY = defineSecret('SMARTLEAD_API_KEY');
const API = 'https://server.smartlead.ai/api/v1';
const CAMPAIGN = Number(process.env.SMARTLEAD_CAMPAIGN_ID || 4176335);
const PER_DAY = Number(process.env.OUTREACH_PER_DAY || 1500);
const MIN_SCORE = 75;
const MAX_BOUNCE = 0.03;
const STATE_ORDER = ['CO', 'TX', 'CA', 'FL', 'PA', 'IL', 'MA', 'CT', 'ME', 'NH', 'VT', 'RI'];
const SITE = 'https://meetlazo.com/';
const APP = 'https://app.meetlazo.com/';
const CAT_SINGULAR = {
  'wedding-photographers': 'wedding photographer', 'wedding-videographers': 'wedding videographer', 'wedding-venues': 'wedding venue',
  'wedding-planners': 'wedding planner', 'wedding-djs': 'wedding DJ', 'wedding-florists': 'wedding florist', 'wedding-caterers': 'wedding caterer',
  'wedding-cakes': 'wedding cake baker', 'hair-and-makeup': 'bridal hair and makeup artist', 'wedding-officiants': 'wedding officiant',
  'wedding-transportation': 'wedding transportation company', 'wedding-rentals': 'wedding rental company', 'wedding-bands': 'wedding band',
  'wedding-invitations': 'wedding stationer', 'day-of-coordination': 'day-of coordinator',
};
const CAT_PLURAL = {
  'wedding-photographers': 'photographers', 'wedding-videographers': 'videographers', 'wedding-venues': 'venues', 'wedding-planners': 'planners',
  'wedding-djs': 'DJs', 'wedding-florists': 'florists', 'wedding-caterers': 'caterers', 'wedding-cakes': 'cake bakers', 'hair-and-makeup': 'hair and makeup artists',
  'wedding-officiants': 'officiants', 'wedding-transportation': 'transportation', 'wedding-rentals': 'rentals', 'wedding-bands': 'bands',
  'wedding-invitations': 'stationers', 'day-of-coordination': 'day-of coordinators',
};

const db = () => admin.firestore();
const { FieldValue } = admin.firestore;
const str = (v) => (v == null ? '' : String(v));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

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

// ---------------- 1. sync ----------------
async function campaignLeads(key, emailStatus) {
  const out = [];
  for (let offset = 0; ; offset += 100) {
    const j = await sl(key, 'GET', `/campaigns/${CAMPAIGN}/leads`, { params: { offset, limit: 100, emailStatus } });
    const rows = j.data || [];
    out.push(...rows);
    if (rows.length < 100) return out;
  }
}

async function sync(key, log, dryRun) {
  const col = db().collection('outreach');
  const changed = {};
  for (const [status, flag] of [['bounced', 'is_bounced'], ['replied', 'is_replied'], ['unsubscribed', 'is_unsubscribed']]) {
    let rows;
    try { rows = await campaignLeads(key, flag); } catch (e) { log.push(`sync ${flag}: ${e.message}`); continue; }
    const emails = [...new Set(rows.map((r) => str((r.lead || {}).email).toLowerCase()).filter(Boolean))];
    for (let i = 0; i < emails.length; i += 30) {
      const snap = await col.where('sendTo', 'in', emails.slice(i, i + 30)).get();
      for (const d of snap.docs) {
        const cur = str(d.get('status'));
        if (cur === status || cur === 'claimed' || cur === 'removed' || (cur === 'unsubscribed' && status !== 'unsubscribed')) continue;
        changed[status] = (changed[status] || 0) + 1;
        if (!dryRun) await d.ref.set({ status, [`${status}At`]: FieldValue.serverTimestamp(), smartleadFlag: flag }, { merge: true });
      }
    }
  }
  log.push(Object.keys(changed).length ? 'sync: ' + Object.entries(changed).map(([k, v]) => `${k} ${v}`).join(', ') : 'sync: nothing new');
  return changed;
}

// ---------------- 2. guard ----------------
async function guard(key, log) {
  let j;
  try { j = await sl(key, 'GET', `/campaigns/${CAMPAIGN}/analytics`); } catch (e) { log.push(`guard: analytics unavailable (${e.message}); feeding anyway`); return { ok: true }; }
  const sent = Number(j.sent_count || j.sent || 0), bounced = Number(j.bounce_count || j.bounced || 0), replied = Number(j.reply_count || j.replied || 0);
  const rate = sent ? bounced / sent : 0;
  log.push(`guard: sent ${sent}, bounced ${bounced} (${(rate * 100).toFixed(1)}%), replied ${replied}`);
  if (sent >= 200 && rate > MAX_BOUNCE) { log.push(`guard: bounce rate over ${MAX_BOUNCE * 100}%, NOT feeding today`); return { ok: false, sent, bounced, replied }; }
  return { ok: true, sent, bounced, replied };
}

// ---------------- 3. feed ----------------
// same rules as outreach_export.pick(): listed, site ok, best address, score >= 75, wedding site, one per website, no address twice
function pick(docs, seenAddr) {
  const bySite = new Map();
  for (const d of docs) {
    const v = d.data();
    if (v.status !== 'listed' || v.site !== 'ok' || !v.best) continue;
    const fl = v.flags || {};
    if (fl.noWedding || fl.parked || fl.hijacked) continue;
    const em = (v.emails || [])[0] || {};
    if (Number(em.score || 0) < MIN_SCORE) continue;
    const list = bySite.get(v.website) || [];
    list.push({ d, v, em });
    bySite.set(v.website, list);
  }
  const rows = [], shared = [];
  for (const group of bySite.values()) {
    group.sort((a, b) => Number(b.em.score || 0) - Number(a.em.score || 0));
    const [best, ...rest] = group;
    shared.push(...rest.map((x) => x.d));
    if (seenAddr.has(best.em.addr)) { shared.push(best.d); continue; }
    seenAddr.add(best.em.addr);
    rows.push(best);
  }
  return { rows, shared };
}

async function nextSlice(n, log) {
  const byState = {};
  for (const [id, m] of Object.entries(METROS)) (byState[m.state] = byState[m.state] || []).push(id);
  const picked = [], sharedAll = [], seenAddr = new Set();
  for (const st of STATE_ORDER) {
    if (picked.length >= n) break;
    const docs = [];
    for (const mid of byState[st] || []) {
      const snap = await db().collection('outreach').where('metroId', '==', mid).where('status', '==', 'listed').get();
      docs.push(...snap.docs);
    }
    if (!docs.length) continue;
    const { rows, shared } = pick(docs, seenAddr);
    sharedAll.push(...shared);
    const size = {};
    for (const r of rows) size[r.v.metroId] = (size[r.v.metroId] || 0) + 1;
    rows.sort((a, b) => (size[b.v.metroId] - size[a.v.metroId]) || (Number(b.em.score || 0) - Number(a.em.score || 0)));
    const take = rows.slice(0, n - picked.length);
    picked.push(...take);
    log.push(`feed: ${st} has ${rows.length} ready, taking ${take.length}`);
  }
  return { picked, shared: sharedAll };
}

function toLead({ d, v, em }) {
  const cat = (v.categories || [''])[0];
  const sing = CAT_SINGULAR[cat] || 'wedding vendor';
  const tok = str(v.token);
  const metro = METROS[v.metroId] ? METROS[v.metroId].name : str(v.metroId);
  return { email: em.addr, first_name: '', last_name: '', company_name: str(v.name), website: str(v.website),
    custom_fields: { metro, category: cat, category_singular: sing, category_singular_cap: sing.charAt(0).toUpperCase() + sing.slice(1),
      category_plural: CAT_PLURAL[cat] || 'vendors', site_host: str(v.siteHost), page_url: str(v.pageUrl), claim_url: `${SITE}claim/${tok}`,
      stop_url: `${SITE}claim/${tok}/stop`, signup_url: `${APP}?claim=${encodeURIComponent(d.id)}`, vendor_id: d.id, token: tok } };
}

async function feed(key, n, log, dryRun) {
  const { picked, shared } = await nextSlice(n, log);
  if (!picked.length) { log.push('feed: nothing left to send in the focus states'); return { added: 0, skipped: 0 }; }
  const batchId = `${new Date().toISOString().slice(0, 10)}-auto`;
  let added = 0, skipped = 0;
  // vendors sharing a website with one we are mailing never get their own email
  if (!dryRun) {
    for (let i = 0; i < shared.length; i += 400) {
      const wb = db().batch();
      for (const d of shared.slice(i, i + 400)) wb.set(d.ref, { status: 'skipped', skipWhy: 'shared-website', batch: batchId }, { merge: true });
      await wb.commit();
    }
  }
  for (let i = 0; i < picked.length; i += 400) {
    const chunk = picked.slice(i, i + 400);
    const leads = chunk.map(toLead);
    if (dryRun) { log.push(`feed (dry): would push ${leads.length}, first ${leads[0].email} (${leads[0].company_name})`); added += leads.length; continue; }
    const j = await sl(key, 'POST', `/campaigns/${CAMPAIGN}/leads`, { body: { lead_list: leads, settings: {
      ignore_global_block_list: false, ignore_unsubscribe_list: false, ignore_community_bounce_list: false, ignore_duplicate_leads_in_other_campaign: false } } });
    const a = Number(j.added_count || 0), s = Number(j.skipped_count || 0);
    added += a; skipped += s;
    const skippedEmails = new Set((j.skipped_leads || []).map((x) => str(typeof x === 'object' ? x.email : x).toLowerCase()));
    const wb = db().batch();
    for (const { d, em } of chunk) {
      if (skippedEmails.has(em.addr)) wb.set(d.ref, { status: 'skipped', skipWhy: 'smartlead', batch: batchId }, { merge: true });
      else wb.set(d.ref, { status: 'sent', batch: batchId, sendTo: em.addr, sentAt: FieldValue.serverTimestamp(), provider: 'smartlead', providerCampaignId: CAMPAIGN }, { merge: true });
    }
    await wb.commit();
    log.push(`feed: pushed ${leads.length} -> added ${a}, skipped ${s}`);
  }
  log.push(`feed: batch ${batchId} done, ${added} added, ${skipped} skipped, ${shared.length} shared-site vendors marked skipped`);
  return { added, skipped, batchId };
}

async function run(key, { dryRun = false, perDay = PER_DAY, syncOnly = false } = {}) {
  const log = [`run start: campaign ${CAMPAIGN}, perDay ${perDay}, dry ${dryRun}`];
  const started = new Date();
  const out = { dryRun, perDay };
  try {
    out.sync = await sync(key, log, dryRun);
    if (!syncOnly) {
      const g = await guard(key, log);
      out.guard = g;
      if (g.ok) out.feed = await feed(key, perDay, log, dryRun);
    }
  } catch (e) {
    log.push(`ERROR: ${e.message}`);
    out.error = e.message;
  }
  log.push('run end');
  const id = started.toISOString().replace(/[:T]/g, '-').slice(0, 16);
  await db().collection('outreachRuns').doc(id).set({ ...out, log, startedAt: started, finishedAt: FieldValue.serverTimestamp() }).catch(() => {});
  console.log(log.join('\n'));
  return out;
}

module.exports = function outreachDailyModule() {
  const outreachDaily = onSchedule({ schedule: '45 7 * * *', timeZone: 'America/Phoenix', memory: '512MiB', timeoutSeconds: 540, secrets: [SMARTLEAD_API_KEY] },
    async () => { await run(SMARTLEAD_API_KEY.value()); });

  // admin-only manual trigger: { dryRun?, perDay?, syncOnly? }
  const outreachDailyNow = onCall({ memory: '512MiB', timeoutSeconds: 540, secrets: [SMARTLEAD_API_KEY] }, async (request) => {
    const uid = request.auth && request.auth.uid;
    if (!uid) throw new HttpsError('unauthenticated', 'Sign in.');
    const tok = request.auth.token || {};
    const u = await db().collection('users').doc(uid).get();
    const isAdmin = tok.admin === true || (u.exists && (u.get('isAdmin') === true || u.get('role') === 'admin'));
    if (!isAdmin) throw new HttpsError('permission-denied', 'Admins only.');
    const d = request.data || {};
    return run(SMARTLEAD_API_KEY.value(), { dryRun: d.dryRun === true, perDay: Number(d.perDay) || PER_DAY, syncOnly: d.syncOnly === true });
  });

  return { outreachDaily, outreachDailyNow, _run: run };
};
