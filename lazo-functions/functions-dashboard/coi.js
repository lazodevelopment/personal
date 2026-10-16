// functions-dashboard/coi.js
// Build ID: JC-LAZO-FNDASH-1016-COI-001
//
// CERTIFICATES OF INSURANCE ON FILE. A vendor uploads a COI once, June reads it,
// and the vendor sends it to the Lazo venues and planners they work with. The
// venue keeps it on file; when it lapses both sides hear about it, and when the
// vendor uploads the renewal every venue that had the old one gets the new one.
//
//   coiRead      callable {vendorId, path}             -> June's read of the file (fields to confirm)
//   coiSave      callable {vendorId, ...fields, venueIds?, offLazo?, replaces?} -> {coiId}
//                  new COI, or the renewal of `replaces` (it inherits every venue)
//   coiShare     callable {coiId, venueIds?, offLazo?}  -> sends it to more venues
//   coiUnshare   callable {coiId, venueId}              -> takes it back from one venue
//   coiFileLink  callable {coiId, venueId?}             -> 10-minute signed URL (vendor or a venue it went to)
//   coiRequest   callable {venueId, vendorId, note?}    -> a venue or planner asks a vendor for their COI
//   coiPublic    GET ?c=&t=[&stop=1]                    -> the emailed download link (venues not on Lazo,
//                                                          or listed but unclaimed); 30 days per send
//   coiSweep     09:00 Phoenix: 30 / 7 / 0 days before expiry -> the vendor; one digest per venue
//
// Data
//   cois/{coiId}                      the vendor's record (vendor owner + managers read; callables write)
//   vendors/{venueId}/coisOnFile/{id} the venue's copy (venue owner + managers read; callables write)
//   coiRequests/{venueId}__{vendorId} a venue's open ask (either side reads)
//   Storage vendors/{vendorId}/coi/{coiId}/{file}  the certificate (vendor writes; venues get signed URLs)
//
// "Venue" here is any Lazo listing in RECEIVERS (venues and planners).

'use strict';

const { onCall, onRequest, HttpsError } = require('firebase-functions/v2/https');
const { onSchedule } = require('firebase-functions/v2/scheduler');
const admin = require('firebase-admin');
const crypto = require('crypto');
const { frame, esc, facts, quietLink } = require('./email-frame');
const { feedTo } = require('./june-feed');

const db = () => admin.firestore();
const FV = () => admin.firestore.FieldValue;
const TS = () => admin.firestore.Timestamp;
const str = (v) => (v == null ? '' : String(v));
const clip = (s, n) => str(s).trim().slice(0, n);
const emailOk = (e) => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(str(e));
const FROM = 'Lazo <hello@meetlazo.com>';
const REPLY = 'hello@meetlazo.com';
const DASH = 'https://app.meetlazo.com/dashboard';
const FOR_VENDORS = 'https://meetlazo.com/for-vendors/';
const PUBLIC_URL = 'https://us-central1-lazo-513ec.cloudfunctions.net/coiPublic';
const MODEL = 'claude-sonnet-5-5';
const DAY = 86400000;
const LINK_DAYS = 30;
const RECEIVERS = ['wedding-venues', 'wedding-planners'];
const LINES = ['general', 'auto', 'umbrella', 'workers', 'liquor', 'professional', 'other'];
const LINE_NAMES = { general: 'General liability', auto: 'Auto', umbrella: 'Umbrella', workers: "Workers' comp", liquor: 'Liquor liability', professional: 'Professional', other: 'Other' };
const MO = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const practice = (d) => !d || d.demo === true || d.practice === true || d.preview === true;

// ------------------------------------------------------------------ helpers --
const catsOf = (v) => [...new Set([str(v.category), ...(Array.isArray(v.categories) ? v.categories.map(str) : [])].filter(Boolean))];
const isReceiver = (v) => catsOf(v).some((c) => RECEIVERS.includes(c));
const kindOf = (v) => (catsOf(v).includes('wedding-venues') ? 'venue' : 'planner');

function toDate(v) {
  if (!v) return null;
  if (v.toDate) return v.toDate();
  const s = str(v);
  const d = new Date(/^\d{4}-\d{2}-\d{2}$/.test(s) ? s + 'T12:00:00-07:00' : s);
  return isNaN(d) ? null : d;
}
const ymd = (v) => { const d = toDate(v); return d ? d.toLocaleDateString('en-CA', { timeZone: 'America/Phoenix' }) : ''; };
const nice = (v) => { const d = toDate(v); if (!d) return ''; const [y, m, dd] = ymd(d).split('-').map(Number); return `${MO[m - 1]} ${dd}, ${y}`; };
const money = (n) => (typeof n === 'number' && isFinite(n) && n > 0 ? '$' + Math.round(n).toLocaleString('en-US') : '');
const num = (v) => { const n = typeof v === 'number' ? v : Number(str(v).replace(/[^0-9.]/g, '')); return isFinite(n) && n > 0 ? Math.round(n) : null; };
/** whole days from today (Phoenix) to the expiry day; 0 = expires today, negative = lapsed */
function daysLeft(exp, now = new Date()) {
  const a = ymd(now), b = ymd(exp);
  if (!a || !b) return null;
  return Math.round((Date.parse(b + 'T00:00:00Z') - Date.parse(a + 'T00:00:00Z')) / DAY);
}

// "The Ranch at Desert Willow, LLC" ~ "Ranch at Desert Willow": the words that carry the name
const STOP = new Set(['the', 'a', 'an', 'and', 'of', 'at', 'llc', 'inc', 'co', 'company', 'ltd', 'corp', 'venue', 'venues', 'events', 'event', 'weddings', 'wedding', 'its', 'their', 'all', 'as', 'additional', 'insured', 'insureds', 'certificate', 'holder']);
const words = (s) => str(s).toLowerCase().replace(/&/g, ' and ').replace(/[^a-z0-9 ]+/g, ' ').split(/\s+/).filter((w) => w && !STOP.has(w));
/** is this venue named on the certificate (holder or additional insured)? */
function namedOn(venueName, cert) {
  const want = words(venueName);
  if (!want.length) return false;
  const texts = [str(cert.holder), ...((cert.additionalInsured && cert.additionalInsured.named) || []).map(str)];
  return texts.some((t) => { const have = new Set(words(t)); const hit = want.filter((w) => have.has(w)).length; return hit / want.length >= 0.6; });
}

async function vendorDoc(id) {
  if (!id) return null;
  const s = await db().collection('vendors').doc(str(id)).get();
  return s.exists ? { id: s.id, ...s.data() } : null;
}
async function hasAccess(uid, vendorId) {
  if (!uid || !vendorId) return false;
  const v = await vendorDoc(vendorId);
  if (!v) return false;
  if (str(v.claimedBy) === uid) return true;
  const u = await db().collection('users').doc(uid).get();
  return u.exists && str(u.get('vendorId')) === str(vendorId) && str(u.get('vendorRole')) === 'manager';
}
async function mustAccess(request, vendorId) {
  const uid = request.auth && request.auth.uid;
  if (!uid) throw new HttpsError('unauthenticated', 'Sign in first.');
  if (!(await hasAccess(uid, vendorId))) throw new HttpsError('permission-denied', 'Not your listing.');
  return uid;
}
async function peopleOf(vendorId) {
  const snap = await db().collection('users').where('vendorId', '==', str(vendorId)).get();
  return snap.docs.map((d) => d.id);
}
async function ownerEmail(v) {
  try {
    if (str(v.claimedBy)) {
      const u = await db().collection('users').doc(str(v.claimedBy)).get();
      if (u.exists && emailOk(u.get('email'))) return str(u.get('email'));
    }
  } catch (e) {}
  return '';
}
const listedEmail = (v) => [v.notifyEmail, v.publicEmail, v.email].map(str).find(emailOk) || '';

// ------------------------------------------------------------ June's read --
const PROMPT = `This is a certificate of insurance (usually an ACORD 25) from a wedding vendor. Read it and reply with JSON only:
{"insurer": "main insurer name",
 "insured": "the named insured (the vendor's business)",
 "holder": "certificate holder name and address, as one line",
 "addlInsdChecked": true|false,   // any ADDL INSD box marked
 "additionalInsured": ["each party the description of operations names as additional insured"],
 "policies": [{"line": "general|auto|umbrella|workers|liquor|professional|other",
               "number": "policy number",
               "limit": 1000000,        // each occurrence / per accident / each claim, in dollars
               "aggregate": 2000000,    // general aggregate if shown, else null
               "effective": "YYYY-MM-DD", "expires": "YYYY-MM-DD"}],
 "confidence": 0.0-1.0,
 "isCoi": true|false}            // false when the file is not a certificate of insurance
Use null for anything you cannot read. Dates as YYYY-MM-DD.`;

function parseJson(text) {
  const t = str(text).trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '');
  const a = t.indexOf('{'), b = t.lastIndexOf('}');
  if (a < 0 || b < a) throw new Error('no JSON in model reply');
  return JSON.parse(t.slice(a, b + 1));
}

/** the model's JSON -> the fields the app shows for confirming */
function normalizeRead(j) {
  const policies = (Array.isArray(j.policies) ? j.policies : []).slice(0, 10).map((p) => ({
    line: LINES.includes(str(p.line)) ? str(p.line) : 'other',
    number: clip(p.number, 60),
    limit: num(p.limit), aggregate: num(p.aggregate),
    effective: ymd(p.effective), expires: ymd(p.expires),
  }));
  return {
    isCoi: j.isCoi !== false,
    insurer: clip(j.insurer, 120), insured: clip(j.insured, 120), holder: clip(j.holder, 240),
    additionalInsured: { checked: j.addlInsdChecked === true, named: (Array.isArray(j.additionalInsured) ? j.additionalInsured : []).map((s) => clip(s, 160)).filter(Boolean).slice(0, 10) },
    policies,
    expiresAt: keyExpiry(policies),
    confidence: typeof j.confidence === 'number' ? Math.max(0, Math.min(1, j.confidence)) : null,
  };
}
/** the date that matters to a venue: the earliest of general / umbrella / liquor, else the earliest of any */
function keyExpiry(policies) {
  const pick = (ps) => ps.map((p) => p.expires).filter(Boolean).sort()[0] || '';
  return pick(policies.filter((p) => ['general', 'umbrella', 'liquor'].includes(p.line))) || pick(policies);
}

// ------------------------------------------------------------------ module --
module.exports = function coiModule(RESEND_API_KEY, ANTHROPIC_API_KEY) {

  async function sendEmail(to, subject, html, text) {
    if (!emailOk(to)) return false;
    const r = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${RESEND_API_KEY.value()}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ from: FROM, to: [to], subject, html, text, reply_to: REPLY }),
    });
    if (!r.ok) { console.warn('coi resend', r.status, await r.text()); return false; }
    return true;
  }

  async function pushTo(uid, n) {
    const snap = await db().collection('users').doc(uid).collection('fcm_tokens').get();
    const toks = []; snap.forEach((d) => { const t = str(d.get('fcm_token')); if (t) toks.push(t); });
    if (!toks.length) return;
    await admin.messaging().sendEachForMulticast({
      tokens: toks,
      notification: { title: clip(n.title, 80), body: clip(n.text, 180) },
      data: { from: 'june', tag: 'coi', thread: '', open: 'coi' },
      android: { priority: 'high', notification: { channelId: 'june', tag: 'coi', sound: 'default' } },
      apns: { payload: { aps: { sound: 'default', 'thread-id': 'coi', badge: 1 } } },
    });
  }
  const phoenixHour = () => +new Date().toLocaleString('en-US', { timeZone: 'America/Phoenix', hour: 'numeric', hour12: false }) % 24;
  /** bell for every person on the listing, push outside quiet hours, email to the owner */
  async function tell(v, n, mail) {
    const uids = await peopleOf(v.id);
    const h = phoenixHour(); const quiet = h >= 22 || h < 7;
    for (const uid of uids) {
      await feedTo(uid, { title: n.title, text: n.text, kind: 'coi', open: 'coi' });
      if (!quiet) { try { await pushTo(uid, n); } catch (e) { console.log('coi push', uid, e.message); } }
    }
    if (mail) { const to = await ownerEmail(v); if (to) await sendEmail(to, mail.subject, mail.html, mail.text); }
  }

  // ---------------------------------------------------------------- emails --
  const coiFacts = (c) => facts([
    ['Insurer', c.insurer || '—'],
    ['General liability', money(c.glEach) || '—'],
    ['Expires', nice(c.expiresAt) || '—'],
  ].slice(0, 3));

  function mailShared(venue, vendor, c, renewed) {
    const vn = str(vendor.name);
    const subject = renewed ? `${vn}'s renewed COI is on file` : `${vn} sent you their certificate of insurance`;
    return {
      subject,
      html: frame({
        preheader: renewed ? `Now current to ${nice(c.expiresAt)}.` : `On file in Lazo, current to ${nice(c.expiresAt)}.`,
        kicker: 'Certificate of insurance',
        title: renewed ? `${esc(vn)} renewed their COI` : `${esc(vn)}'s COI is on file`,
        lede: renewed
          ? `The old certificate has been replaced. The new one is current to <b>${esc(nice(c.expiresAt))}</b>.`
          : `It's saved under COIs on file in your Lazo dashboard. We'll tell you before it expires.`,
        body: coiFacts(c) + (c.namedFor ? '' : `<p style="margin:0 0 10px;font-family:Helvetica,Arial,sans-serif;font-size:14px;color:#8A6A2F">This certificate doesn't name ${esc(venue.name)} as holder or additional insured. If you need that, ask ${esc(vn)} for one made out to you.</p>`),
        cta: 'Open COIs on file', ctaHref: DASH,
        footerWhy: `You're getting this because ${esc(vn)} sent their certificate to ${esc(venue.name)} on Lazo.`,
      }),
      text: `${subject}\n\nInsurer: ${c.insurer || '-'}\nExpires: ${nice(c.expiresAt)}\n\nOpen COIs on file: ${DASH}`,
    };
  }

  function mailOutside(toName, vendor, c, href, stopHref, renewed) {
    const vn = str(vendor.name);
    const subject = renewed ? `${vn}'s renewed certificate of insurance` : `${vn} sent you their certificate of insurance`;
    return {
      subject,
      html: frame({
        preheader: `Current to ${nice(c.expiresAt)}. The download link works for ${LINK_DAYS} days.`,
        kicker: 'Certificate of insurance',
        title: renewed ? `${esc(vn)} renewed their COI` : `${esc(vn)}'s COI`,
        lede: `${esc(vn)} sent ${toName ? esc(toName) : 'you'} their certificate of insurance through Lazo.`,
        body: coiFacts(c),
        cta: 'Download the certificate', ctaHref: href,
        secondary: 'Keep every vendor\'s COI on file in Lazo, free', secondaryHref: FOR_VENDORS,
        signoff: `On Lazo, renewals arrive on their own and you hear before a COI lapses. <a href="${stopHref}" style="color:#5B5363">Stop COI emails from ${esc(vn)}</a>.`,
        footerWhy: `You're getting this because ${esc(vn)} entered this address for ${toName ? esc(toName) : 'your venue'}.`,
      }),
      text: `${subject}\n\nInsurer: ${c.insurer || '-'}\nExpires: ${nice(c.expiresAt)}\n\nDownload (works for ${LINK_DAYS} days): ${href}\n\nStop these emails: ${stopHref}`,
    };
  }

  function mailVendorStep(vendor, c, step, n, left) {
    const when = left < 0 ? `expired ${nice(c.expiresAt)}` : step === 'd0' ? 'expires today' : `expires ${nice(c.expiresAt)}`;
    const subject = left < 0 ? 'Your COI has expired' : step === 'd0' ? 'Your COI expires today' : `Your COI expires in ${step === 'd7' ? 'a week' : '30 days'}`;
    return {
      n: { title: subject, text: `Your certificate from ${c.insurer || 'your insurer'} ${when}. Upload the renewal and Lazo sends it to ${n ? `the ${n} venue${n === 1 ? '' : 's'} that have it` : 'your venues'}.` },
      mail: {
        subject,
        html: frame({
          preheader: `Upload the renewal and every venue gets it.`,
          kicker: 'Certificate of insurance',
          title: esc(subject),
          lede: `Your certificate from <b>${esc(c.insurer || 'your insurer')}</b> ${esc(when)}. ${n ? `${n} venue${n === 1 ? ' has' : 's have'} it on file.` : ''} Ask your agent for the renewal, then upload it in Lazo: every venue that had this one gets the new one.`,
          cta: 'Upload the renewal', ctaHref: DASH,
          footerWhy: `You're getting this because your certificate of insurance is on file in Lazo.`,
        }),
        text: `${subject}\n\nUpload the renewal in Lazo and every venue that had this one gets the new one: ${DASH}`,
      },
    };
  }

  function mailDigest(venue, rows) {
    const lapsed = rows.filter((r) => r.left <= 0).length;
    const subject = rows.length === 1 ? `${rows[0].vendorName}'s COI ${rows[0].left <= 0 ? 'expired' : 'expires ' + nice(rows[0].expiresAt)}` : `${rows.length} vendor COIs on file are lapsing`;
    const list = rows.map((r) => `<tr><td style="padding:8px 0;border-bottom:1px solid #EADFCB;font-family:Helvetica,Arial,sans-serif;font-size:15px;color:#241E2B"><b>${esc(r.vendorName)}</b></td><td align="right" style="padding:8px 0;border-bottom:1px solid #EADFCB;font-family:Helvetica,Arial,sans-serif;font-size:14px;color:${r.left <= 0 ? '#A23B3B' : '#8A6A2F'}">${r.left <= 0 ? 'Expired ' : 'Expires '}${esc(nice(r.expiresAt))}</td></tr>`).join('');
    return {
      n: { title: subject, text: rows.map((r) => `${r.vendorName} (${r.left <= 0 ? 'expired' : nice(r.expiresAt)})`).join(', ').slice(0, 300) },
      mail: {
        subject,
        html: frame({
          preheader: lapsed ? `${lapsed} already expired.` : 'We have asked each vendor for their renewal.',
          kicker: 'COIs on file',
          title: rows.length === 1 ? 'A COI on file is lapsing' : 'COIs on file are lapsing',
          lede: `We've reminded each vendor to upload their renewal. When they do, it replaces the old one in your COIs on file.`,
          body: `<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:4px 0 14px">${list}</table>`,
          cta: 'Open COIs on file', ctaHref: DASH,
          footerWhy: `You're getting this because vendors keep their certificates on file with ${esc(venue.name)} on Lazo.`,
        }),
        text: `${subject}\n\n${rows.map((r) => `${r.vendorName}: ${r.left <= 0 ? 'expired' : 'expires'} ${nice(r.expiresAt)}`).join('\n')}\n\n${DASH}`,
      },
    };
  }

  // ------------------------------------------------------------- shapes --
  function cleanFields(d) {
    const policies = (Array.isArray(d.policies) ? d.policies : []).slice(0, 10).map((p) => ({
      line: LINES.includes(str(p.line)) ? str(p.line) : 'other', number: clip(p.number, 60),
      limit: num(p.limit), aggregate: num(p.aggregate), effective: ymd(p.effective), expires: ymd(p.expires),
    }));
    const exp = toDate(d.expiresAt || keyExpiry(policies));
    if (!exp) throw new HttpsError('invalid-argument', 'Add the date the certificate expires.');
    if (exp.getTime() > Date.now() + 3 * 366 * DAY) throw new HttpsError('invalid-argument', 'That expiry date is more than three years out.');
    const gl = policies.find((p) => p.line === 'general') || {};
    const ai = d.additionalInsured || {};
    return {
      insurer: clip(d.insurer, 120), holder: clip(d.holder, 240),
      additionalInsured: { checked: ai.checked === true, named: (Array.isArray(ai.named) ? ai.named : []).map((s) => clip(s, 160)).filter(Boolean).slice(0, 10) },
      policies, glEach: gl.limit || null, glAgg: gl.aggregate || null,
      expiresAt: TS().fromDate(exp),
    };
  }
  function cleanFile(vendorId, f) {
    f = f || {};
    const p = str(f.path);
    if (!p.startsWith(`vendors/${vendorId}/coi/`) || p.includes('..')) throw new HttpsError('invalid-argument', 'Upload the certificate first.');
    const ct = str(f.contentType);
    if (!(ct === 'application/pdf' || ct.startsWith('image/'))) throw new HttpsError('invalid-argument', 'A PDF or a photo, please.');
    return { path: p, contentType: ct, name: clip(f.name, 120), size: num(f.size) || 0 };
  }
  /** the venue's copy */
  function copyFor(c, coiId, venueId, vendor, status) {
    const ent = (c.venues || {})[venueId] || {};
    return {
      coiId, vendorId: c.vendorId, vendorName: str(vendor.name), vendorCategory: str(vendor.category || (vendor.categories || [])[0]),
      insurer: c.insurer || '', glEach: c.glEach || null, glAgg: c.glAgg || null, expiresAt: c.expiresAt,
      status: status || c.status, namedOnCert: ent.namedOnCert === true, fileType: (c.file || {}).contentType || '',
      sharedAt: ent.sharedAt || FV().serverTimestamp(), updatedAt: FV().serverTimestamp(),
    };
  }

  // -------------------------------------------------- sending to venues --
  /** sends coi to each Lazo venue id and each outside {name,email}; returns what changed */
  async function shareOut(coiRef, c, vendor, venueIds, offLazo, renewed) {
    const coiId = coiRef.id;
    const patch = {}; const added = []; const skipped = [];
    for (const vid of [...new Set((venueIds || []).map(str).filter(Boolean))].slice(0, 25)) {
      if (vid === c.vendorId) { skipped.push(vid); continue; }
      const venue = await vendorDoc(vid);
      if (!venue || venue.delisted === true || !isReceiver(venue)) { skipped.push(vid); continue; }
      const already = (c.venues || {})[vid];
      const ent = { ...(already && !renewed ? already : {}), name: str(venue.name), kind: kindOf(venue), sharedAt: already && already.sharedAt ? already.sharedAt : TS().now(), namedOnCert: namedOn(venue.name, c), claimed: !!str(venue.claimedBy) };
      c.venues = { ...(c.venues || {}), [vid]: ent };
      await db().collection('vendors').doc(vid).collection('coisOnFile').doc(coiId).set(copyFor(c, coiId, vid, vendor));
      // an open request from this venue is answered
      const rq = db().collection('coiRequests').doc(`${vid}__${c.vendorId}`);
      const rs = await rq.get();
      if (rs.exists && rs.get('status') === 'open') await rq.set({ status: 'sent', coiId, answeredAt: FV().serverTimestamp() }, { merge: true });
      if (already && !renewed) { patch[`venues.${vid}`] = ent; continue; }   // re-sharing the same COI tells nobody twice
      added.push(vid);
      const m = mailShared(venue, vendor, { ...c, namedFor: ent.namedOnCert }, renewed);
      if (ent.claimed) {
        await tell(venue, { title: m.subject, text: renewed ? `Now current to ${nice(c.expiresAt)}.` : `On file, current to ${nice(c.expiresAt)}.` }, m);
      } else {
        // listed but unclaimed: the listing's own email gets a download link, and the copy waits for the claim
        const to = listedEmail(venue);
        const stopped = already && already.emailed && already.emailed.stopped;
        if (to && !stopped) {
          const tok = crypto.randomBytes(18).toString('base64url');
          ent.emailed = { email: to, token: tok, sentAt: TS().now() };
          const href = `${PUBLIC_URL}?c=${coiId}&t=${tok}`;
          const mo = mailOutside(venue.name, vendor, c, href, href + '&stop=1', renewed);
          await sendEmail(to, mo.subject, mo.html, mo.text);
        }
      }
      patch[`venues.${vid}`] = ent;
    }
    const outs = [...(c.offLazo || [])];
    for (const o of (offLazo || []).slice(0, 10)) {
      const email = str(o.email).trim().toLowerCase();
      if (!emailOk(email)) continue;
      let ent = outs.find((x) => x.email === email);
      if (ent && ent.stopped) continue;
      if (ent && !renewed) continue;
      if (!ent) { ent = { name: clip(o.name, 120), email }; outs.push(ent); }
      ent.token = crypto.randomBytes(18).toString('base64url');
      ent.sentAt = TS().now();
      const href = `${PUBLIC_URL}?c=${coiId}&t=${ent.token}`;
      const mo = mailOutside(ent.name, vendor, c, href, href + '&stop=1', renewed);
      if (await sendEmail(email, mo.subject, mo.html, mo.text)) added.push(email);
    }
    if (offLazo && offLazo.length) { patch.offLazo = outs; c.offLazo = outs; }
    patch.venueIds = Object.keys(c.venues || {});
    c.venueIds = patch.venueIds;
    patch.updatedAt = FV().serverTimestamp();
    await coiRef.update(patch);
    return { added, skipped };
  }

  // ------------------------------------------------------------ callables --
  /** signed in, and a well-formed COI id - checked before any lookup */
  function coiRefOf(request, d) {
    if (!(request.auth && request.auth.uid)) throw new HttpsError('unauthenticated', 'Sign in first.');
    const id = str(d.coiId);
    if (!/^[A-Za-z0-9]{10,40}$/.test(id)) throw new HttpsError('not-found', 'No such COI.');
    return db().collection('cois').doc(id);
  }

  const coiRead = onCall({ memory: '512MiB', timeoutSeconds: 120, secrets: [ANTHROPIC_API_KEY] }, async (request) => {
    const d = request.data || {};
    const vendorId = str(d.vendorId);
    await mustAccess(request, vendorId);
    const f = cleanFile(vendorId, { path: d.path, contentType: str(d.path).toLowerCase().endsWith('.pdf') ? 'application/pdf' : 'image/jpeg' });
    const [buf] = await admin.storage().bucket().file(f.path).download();
    if (buf.length > 15 * 1024 * 1024) throw new HttpsError('invalid-argument', 'That file is over 15MB.');
    const isPdf = buf.slice(0, 5).toString() === '%PDF-';
    const mt = isPdf ? 'application/pdf' : buf[0] === 0x89 ? 'image/png' : buf.slice(8, 12).toString() === 'WEBP' ? 'image/webp' : 'image/jpeg';
    const block = isPdf
      ? { type: 'document', source: { type: 'base64', media_type: 'application/pdf', data: buf.toString('base64') } }
      : { type: 'image', source: { type: 'base64', media_type: mt, data: buf.toString('base64') } };
    const res = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: { 'x-api-key': ANTHROPIC_API_KEY.value(), 'anthropic-version': '2023-06-01', 'content-type': 'application/json' },
      body: JSON.stringify({ model: MODEL, max_tokens: 2000, messages: [{ role: 'user', content: [block, { type: 'text', text: PROMPT }] }] }),
    });
    if (!res.ok) { console.warn('coiRead anthropic', res.status, (await res.text()).slice(0, 300)); throw new HttpsError('unavailable', "June couldn't read it just now. Type the details in, or try again."); }
    const data = await res.json();
    const text = (data.content || []).filter((c) => c.type === 'text').map((c) => c.text).join('\n');
    let out;
    try { out = normalizeRead(parseJson(text)); } catch (e) { throw new HttpsError('unavailable', "June couldn't read it. Type the details in."); }
    return { ...out, contentType: mt };
  });

  const coiSave = onCall({ memory: '256MiB', timeoutSeconds: 120, secrets: [RESEND_API_KEY] }, async (request) => {
    const d = request.data || {};
    const vendorId = str(d.vendorId);
    const uid = await mustAccess(request, vendorId);
    const vendor = await vendorDoc(vendorId);
    const fields = cleanFields(d);
    const file = cleanFile(vendorId, d.file);
    const june = d.june && typeof d.june === 'object' ? { confidence: typeof d.june.confidence === 'number' ? d.june.confidence : null, readAt: TS().now() } : null;

    // edit in place (same certificate, fixed fields)
    if (str(d.coiId)) {
      const ref = db().collection('cois').doc(str(d.coiId));
      const s = await ref.get();
      if (!s.exists || str(s.get('vendorId')) !== vendorId) throw new HttpsError('not-found', 'No such COI.');
      const c = { ...s.data(), ...fields, file };
      for (const vid of Object.keys(c.venues || {})) c.venues[vid].namedOnCert = namedOn(c.venues[vid].name, c);
      const status = daysLeft(c.expiresAt) < 0 ? 'expired' : (c.status === 'expired' ? 'current' : c.status);
      await ref.update({ ...fields, file, status, venues: c.venues || {}, remind: daysLeft(c.expiresAt) > 30 ? {} : (c.remind || {}), updatedAt: FV().serverTimestamp() });
      c.status = status;
      for (const vid of Object.keys(c.venues || {})) await db().collection('vendors').doc(vid).collection('coisOnFile').doc(ref.id).set(copyFor(c, ref.id, vid, vendor), { merge: true });
      await shareOut(ref, c, vendor, d.venueIds, d.offLazo, false);
      return { coiId: ref.id };
    }

    const ref = db().collection('cois').doc();
    const c = {
      vendorId, vendorName: str(vendor.name), status: daysLeft(fields.expiresAt) < 0 ? 'expired' : 'current', ...fields, file,
      june, venues: {}, venueIds: [], offLazo: [], remind: {}, createdBy: uid, createdAt: FV().serverTimestamp(),
    };
    let inherit = [], inheritOut = [];
    const replaces = str(d.replaces);
    if (replaces) {
      const oldRef = db().collection('cois').doc(replaces);
      const os = await oldRef.get();
      if (!os.exists || str(os.get('vendorId')) !== vendorId) throw new HttpsError('not-found', 'No such COI to renew.');
      const old = os.data();
      c.replaces = replaces;
      inherit = Object.keys(old.venues || {});
      inheritOut = (old.offLazo || []).filter((o) => !o.stopped).map((o) => ({ name: o.name, email: o.email }));
      c.offLazo = (old.offLazo || []).filter((o) => o.stopped);
      await oldRef.update({ status: 'replaced', replacedBy: ref.id, updatedAt: FV().serverTimestamp() });
      for (const vid of inherit) {
        const copy = db().collection('vendors').doc(vid).collection('coisOnFile').doc(replaces);
        if ((await copy.get()).exists) await copy.set({ status: 'replaced', replacedBy: ref.id, updatedAt: FV().serverTimestamp() }, { merge: true });
      }
    }
    await ref.set(c);
    if (replaces) {   // a listing that stopped our emails stays stopped on the renewal
      const old = (await db().collection('cois').doc(replaces).get()).data();
      for (const vid of inherit) if (((old.venues[vid] || {}).emailed || {}).stopped) c.venues[vid] = { emailed: { stopped: true } };
    }
    let res = { added: [], skipped: [] };
    if (inherit.length || inheritOut.length) res = await shareOut(ref, c, vendor, inherit, inheritOut, true);
    const more = await shareOut(ref, c, vendor, d.venueIds, d.offLazo, false);
    return { coiId: ref.id, sent: [...res.added, ...more.added], skipped: [...res.skipped, ...more.skipped] };
  });

  const coiShare = onCall({ memory: '256MiB', timeoutSeconds: 120, secrets: [RESEND_API_KEY] }, async (request) => {
    const d = request.data || {};
    const ref = coiRefOf(request, d);
    const s = await ref.get();
    if (!s.exists) throw new HttpsError('not-found', 'No such COI.');
    const c = s.data();
    await mustAccess(request, c.vendorId);
    if (c.status === 'replaced' || c.status === 'removed') throw new HttpsError('failed-precondition', 'Send the current certificate instead.');
    const vendor = await vendorDoc(c.vendorId);
    const r = await shareOut(ref, c, vendor, d.venueIds, d.offLazo, false);
    return { sent: r.added, skipped: r.skipped };
  });

  const coiUnshare = onCall({ memory: '256MiB' }, async (request) => {
    const d = request.data || {};
    const ref = coiRefOf(request, d);
    const s = await ref.get();
    if (!s.exists) throw new HttpsError('not-found', 'No such COI.');
    const c = s.data();
    await mustAccess(request, c.vendorId);
    const vid = str(d.venueId);
    if (d.email) {
      const outs = (c.offLazo || []).filter((o) => o.email !== str(d.email).trim().toLowerCase());
      await ref.update({ offLazo: outs, updatedAt: FV().serverTimestamp() });
      return { ok: true };
    }
    if (!vid || !(c.venues || {})[vid]) return { ok: true };
    await ref.update({ [`venues.${vid}`]: FV().delete(), venueIds: (c.venueIds || []).filter((x) => x !== vid), updatedAt: FV().serverTimestamp() });
    await db().collection('vendors').doc(vid).collection('coisOnFile').doc(ref.id).delete();
    return { ok: true };
  });

  const coiFileLink = onCall({ memory: '256MiB' }, async (request) => {
    const uid = request.auth && request.auth.uid;
    if (!uid) throw new HttpsError('unauthenticated', 'Sign in first.');
    const d = request.data || {};
    const ref = coiRefOf(request, d);
    const s = await ref.get();
    if (!s.exists) throw new HttpsError('not-found', 'No such COI.');
    const c = s.data();
    const vid = str(d.venueId);
    let asVenue = false;
    if (!(await hasAccess(uid, c.vendorId))) {
      if (!vid || !(c.venues || {})[vid] || !(await hasAccess(uid, vid))) throw new HttpsError('permission-denied', 'This certificate was not sent to you.');
      asVenue = true;
    }
    const [url] = await admin.storage().bucket().file(c.file.path).getSignedUrl({ action: 'read', expires: Date.now() + 10 * 60 * 1000 });
    if (asVenue) {
      await ref.update({ [`venues.${vid}.viewedAt`]: FV().serverTimestamp() });
      await db().collection('vendors').doc(vid).collection('coisOnFile').doc(ref.id).set({ viewedAt: FV().serverTimestamp() }, { merge: true });
    }
    return { url };
  });

  const coiRequest = onCall({ memory: '256MiB', secrets: [RESEND_API_KEY] }, async (request) => {
    const d = request.data || {};
    const venueId = str(d.venueId), vendorId = str(d.vendorId);
    const uid = await mustAccess(request, venueId);
    const venue = await vendorDoc(venueId);
    if (!isReceiver(venue)) throw new HttpsError('failed-precondition', 'COI requests are for venues and planners.');
    const vendor = await vendorDoc(vendorId);
    if (!vendor || vendorId === venueId) throw new HttpsError('not-found', 'No such vendor.');
    // a current one is already on file: nothing to ask for
    const have = await db().collection('vendors').doc(venueId).collection('coisOnFile').where('vendorId', '==', vendorId).get();
    if (have.docs.some((x) => x.get('status') === 'current' && daysLeft(x.get('expiresAt')) > 30)) return { already: true };
    const ref = db().collection('coiRequests').doc(`${venueId}__${vendorId}`);
    const prev = await ref.get();
    if (prev.exists && prev.get('status') === 'open') {
      const at = toDate(prev.get('at'));
      if (at && Date.now() - at.getTime() < 3 * DAY) return { open: true, repeated: false };
    }
    await ref.set({ venueId, venueName: str(venue.name), venueKind: kindOf(venue), vendorId, vendorName: str(vendor.name), note: clip(d.note, 300), status: 'open', by: uid, at: FV().serverTimestamp() });
    const title = `${venue.name} asked for your COI`;
    const text = `${venue.name} would like your certificate of insurance on file${d.note ? ': "' + clip(d.note, 120) + '"' : '.'} Send it from Profile > Insurance.`;
    if (str(vendor.claimedBy)) {
      await tell(vendor, { title, text }, {
        subject: title,
        html: frame({
          preheader: 'Send it once; renewals go to them on their own.',
          kicker: 'Certificate of insurance',
          title: `${esc(venue.name)} asked for your COI`,
          lede: `${esc(venue.name)} would like your certificate of insurance on file. Upload it in Lazo once and send it; when you upload a renewal, they get that too.`,
          body: d.note ? `<p style="margin:0 0 14px;font-family:Georgia,serif;font-size:16px;font-style:italic;color:#241E2B">"${esc(clip(d.note, 300))}"</p>` : '',
          cta: 'Send my COI', ctaHref: DASH,
          footerWhy: `You're getting this because ${esc(venue.name)} asked for your certificate on Lazo.`,
        }),
        text: `${text}\n\n${DASH}`,
      });
    } else {
      const to = listedEmail(vendor);
      if (to) await sendEmail(to, title, frame({
        preheader: 'Claim your free Lazo listing to send it.',
        kicker: 'Certificate of insurance',
        title: `${esc(venue.name)} asked for your COI`,
        lede: `${esc(venue.name)} keeps vendor certificates of insurance on file in Lazo and asked for yours. Claim your free listing, upload it once, and renewals reach them on their own.`,
        cta: 'Claim my free listing', ctaHref: FOR_VENDORS,
        footerWhy: `You're getting this because ${esc(venue.name)} asked for your certificate on Lazo.`,
      }), `${text}\n\nClaim your free listing: ${FOR_VENDORS}`);
    }
    return { open: true };
  });

  const coiPublic = onRequest({ memory: '256MiB' }, async (req, res) => {
    const coiId = str(req.query.c), tok = str(req.query.t);
    const page = (title, body) => res.status(200).set('Content-Type', 'text/html; charset=utf-8').send(`<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(title)}</title><body style="font-family:Helvetica,Arial,sans-serif;background:#FAF6F0;color:#241E2B;padding:40px 18px;text-align:center"><h1 style="font-family:Georgia,serif;font-weight:normal;color:#3D1C3B">${esc(title)}</h1><p>${body}</p><p><a href="${FOR_VENDORS}" style="color:#52284F">Lazo</a></p></body>`);
    if (!coiId || tok.length < 16) return page('Link not found', 'This link is incomplete.');
    const ref = db().collection('cois').doc(coiId);
    const s = await ref.get();
    if (!s.exists) return page('Link not found', 'This certificate is no longer on file.');
    const c = s.data();
    const outs = c.offLazo || [];
    const oi = outs.findIndex((o) => o.token === tok);
    const vid = Object.keys(c.venues || {}).find((k) => ((c.venues[k] || {}).emailed || {}).token === tok);
    if (oi < 0 && !vid) return page('Link not found', 'This link has been replaced by a newer one.');
    if (req.query.stop) {
      if (oi >= 0) { outs[oi].stopped = true; outs[oi].token = ''; await ref.update({ offLazo: outs }); }
      else await ref.update({ [`venues.${vid}.emailed.stopped`]: true });
      return page('Done', `You won't get more COI emails from ${esc(c.vendorName)}.`);
    }
    const sent = toDate(oi >= 0 ? outs[oi].sentAt : c.venues[vid].emailed.sentAt);
    if (!sent || Date.now() - sent.getTime() > LINK_DAYS * DAY) return page('This link has expired', `Ask ${esc(c.vendorName)} to send it again, or keep COIs on file in Lazo for free.`);
    if (c.status === 'replaced' && c.replacedBy) return page('There is a newer certificate', `${esc(c.vendorName)} renewed this COI. The renewal was emailed to you.`);
    const [url] = await admin.storage().bucket().file(c.file.path).getSignedUrl({ action: 'read', expires: Date.now() + 10 * 60 * 1000 });
    if (oi >= 0) { outs[oi].openedAt = TS().now(); await ref.update({ offLazo: outs }); }
    else await ref.update({ [`venues.${vid}.emailed.openedAt`]: TS().now() });
    return res.redirect(302, url);
  });

  // ---------------------------------------------------------------- sweep --
  const STEPS = [['d0', 0], ['d7', 7], ['d30', 30]];
  async function runSweep(now = new Date()) {
    const horizon = TS().fromDate(new Date(now.getTime() + 31 * DAY));
    const snap = await db().collection('cois').where('status', 'in', ['current', 'expired']).where('expiresAt', '<=', horizon).get();
    const digests = {};   // venueId -> rows
    let vendorMails = 0;
    for (const doc of snap.docs) {
      const c = doc.data();
      if (c.replacedBy) continue;
      const left = daysLeft(c.expiresAt, now);
      if (left == null || left > 30) continue;
      const step = STEPS.find(([, n]) => left <= n)[0];
      const remind = c.remind || {};
      if (remind[step]) continue;
      if (left < -14) continue;   // a lapse we never caught up on: don't start nagging two weeks late
      const vendor = await vendorDoc(c.vendorId);
      if (!vendor || practice(vendor)) continue;
      const nVenues = (c.venueIds || []).length + (c.offLazo || []).filter((o) => !o.stopped).length;
      const m = mailVendorStep(vendor, c, step, nVenues, left);
      await tell(vendor, m.n, m.mail);
      vendorMails++;
      const patch = { [`remind.${step}`]: TS().fromDate(now) };
      for (const [s] of STEPS) if (s !== step && !remind[s] && STEPS.findIndex((x) => x[0] === s) > STEPS.findIndex((x) => x[0] === step)) patch[`remind.${s}`] = TS().fromDate(now);
      if (left < 0 && c.status !== 'expired') patch.status = 'expired';
      await doc.ref.update(patch);
      for (const vid of c.venueIds || []) {
        if (left < 0) await db().collection('vendors').doc(vid).collection('coisOnFile').doc(doc.id).set({ status: 'expired', updatedAt: FV().serverTimestamp() }, { merge: true });
        (digests[vid] = digests[vid] || []).push({ vendorName: c.vendorName || vendor.name, expiresAt: c.expiresAt, left });
      }
    }
    let venueMails = 0;
    for (const [vid, rows] of Object.entries(digests)) {
      const venue = await vendorDoc(vid);
      if (!venue || !str(venue.claimedBy)) continue;
      rows.sort((a, b) => a.left - b.left);
      const m = mailDigest(venue, rows);
      await tell(venue, m.n, m.mail);
      venueMails++;
    }
    // lapsed with no reminder due (edited dates, missed runs): keep the status honest
    const late = await db().collection('cois').where('status', '==', 'current').where('expiresAt', '<', TS().fromDate(new Date(now.getTime() - DAY))).get();
    for (const doc of late.docs) {
      if (daysLeft(doc.get('expiresAt'), now) >= 0) continue;
      await doc.ref.update({ status: 'expired' });
      for (const vid of doc.get('venueIds') || []) await db().collection('vendors').doc(vid).collection('coisOnFile').doc(doc.id).set({ status: 'expired' }, { merge: true });
    }
    return { vendorMails, venueMails };
  }

  const coiSweep = onSchedule({ schedule: '0 9 * * *', timeZone: 'America/Phoenix', memory: '512MiB', timeoutSeconds: 300, secrets: [RESEND_API_KEY] }, async () => {
    const r = await runSweep();
    console.log('coiSweep', JSON.stringify(r));
  });

  return { coiRead, coiSave, coiShare, coiUnshare, coiFileLink, coiRequest, coiPublic, coiSweep, _coi: { runSweep, namedOn, normalizeRead, daysLeft, keyExpiry } };
};

// END OF FILE - JC-LAZO-FNDASH-1016-COI-001
