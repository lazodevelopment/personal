// functions-dashboard/welcome.js
// Build ID: JC-LAZO-FNDASH-1007-023 (023.2: steps show app-screen tiles from assets/email/tile-*.jpg so they know what to expect; photos stay on the hero and the category strip)
//
// WELCOME EMAILS. Until now nobody heard from Lazo at signup: vendors got an
// email only when a claim was approved, couples never. Two triggers, both
// idempotent (welcomeSentAt is claimed in a transaction before the send):
//
//   welcomeCouple   couples/{uid} created  -> the couple's welcome, personal:
//                   names, countdown, metro, three first moves, June.
//                   (Both "Start planning" and "Skip for now" on the
//                   Make-it-yours step create this doc, so it fires for every
//                   couple who finishes signup.)
//   welcomeVendor   users/{uid} written with role 'vendor' (first time) ->
//                   the vendor's welcome: claim the listing, what verified
//                   means, leads by text, June. The claim-approved email in
//                   functions/index.js is unchanged and still follows later.
//
// Sent through Resend from hello@meetlazo.com (verified domain), reply-to a
// human. Brand: plum #52284F / #3D1C3B, gold #D9B77C, ivory #FAF6F0, ink
// #241E2B; the ivory lockup (meetlazo.com/assets/foot-logo.png) on a plum
// header band, Georgia headings, table layout so it holds in Outlook/Gmail.

'use strict';

const { onDocumentCreated, onDocumentWritten } = require('firebase-functions/v2/firestore');
const admin = require('firebase-admin');

module.exports = function welcome(RESEND_API_KEY) {
  const db = () => admin.firestore();
  const str = (v) => (v == null ? '' : String(v));
  const esc = (s) => str(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const emailOk = (e) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(str(e).trim());
  const FROM = 'The Lazo Team <hello@meetlazo.com>';
  const REPLY = 'hello@meetlazo.com';
  const APP = 'https://app.meetlazo.com/';
  const DASH = 'https://app.meetlazo.com/dashboard';
  const JUNE = 'https://june.meetlazo.com/';
  const SITE = 'https://meetlazo.com/';
  const LOGO = 'https://meetlazo.com/assets/foot-logo.png';
  const PH = 'https://meetlazo.com/assets/photos/';   // the site's own photography (live, 600px wide in the email)
  const TILE = 'https://meetlazo.com/assets/email/';   // 240x320 crops of the app screens (deploy/upload_r2.py --prefix assets/email)
  const METROS = { 'phoenix': 'Phoenix', 'denver': 'Denver', 'dallas-fort-worth': 'Dallas–Fort Worth', 'houston': 'Houston', 'austin': 'Austin', 'san-antonio': 'San Antonio', 'las-vegas': 'Las Vegas', 'atlanta': 'Atlanta', 'nashville': 'Nashville', 'chicago': 'Chicago', 'los-angeles': 'Los Angeles', 'san-diego': 'San Diego', 'miami': 'Miami', 'orlando': 'Orlando', 'tampa': 'Tampa Bay', 'charlotte': 'Charlotte', 'raleigh-durham': 'Raleigh-Durham', 'seattle': 'Seattle', 'salt-lake-city': 'Salt Lake City', 'new-york-city': 'New York City', 'boston': 'Boston', 'philadelphia': 'Philadelphia', 'washington-dc': 'Washington DC', 'san-francisco-bay': 'the San Francisco Bay', 'portland': 'Portland', 'minneapolis': 'Minneapolis', 'st-louis': 'St. Louis', 'kansas-city': 'Kansas City', 'columbus': 'Columbus', 'new-orleans': 'New Orleans', 'indianapolis': 'Indianapolis', 'sacramento': 'Sacramento', 'jacksonville': 'Jacksonville', 'charleston': 'Charleston', 'savannah': 'Savannah', 'detroit': 'Detroit', 'pittsburgh': 'Pittsburgh', 'cincinnati': 'Cincinnati', 'cleveland': 'Cleveland', 'milwaukee': 'Milwaukee', 'richmond': 'Richmond', 'virginia-beach': 'Virginia Beach', 'louisville': 'Louisville', 'memphis': 'Memphis', 'tucson': 'Tucson' };

  async function sendEmail(to, subject, html, text) {
    const r = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${RESEND_API_KEY.value()}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ from: FROM, to: [to], reply_to: REPLY, subject, html, text }),
    });
    if (!r.ok) throw new Error(`resend ${r.status}: ${await r.text()}`);
  }

  // claim the send inside a transaction so two trigger deliveries never send twice
  async function claim(ref) {
    return db().runTransaction(async (tx) => {
      const s = await tx.get(ref);
      if (!s.exists || s.get('welcomeSentAt')) return false;
      tx.update(ref, { welcomeSentAt: admin.firestore.FieldValue.serverTimestamp() });
      return true;
    });
  }

  async function emailFor(uid, userDoc) {
    const e = str(userDoc && userDoc.email).trim();
    if (emailOk(e)) return e;
    try { const u = await admin.auth().getUser(uid); if (emailOk(u.email)) return u.email; } catch (_) {}
    return '';
  }

  function firstName(s) { const t = str(s).trim(); return t ? t.split(/\s+/)[0] : ''; }

  // ---------------- the frame: plum band with the lockup, ivory page, white card, gold button ----------------
  function button(label, href) {
    return `<table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:26px auto 6px"><tr><td align="center" bgcolor="#D9B77C" style="border-radius:999px;background:#D9B77C">
      <a href="${href}" style="display:inline-block;padding:14px 30px;font-family:Helvetica,Arial,sans-serif;font-size:15px;font-weight:bold;color:#3D1C3B;text-decoration:none;border-radius:999px;letter-spacing:.2px">${esc(label)}</a></td></tr></table>`;
  }
  function quietLink(label, href) {
    return `<p style="margin:10px 0 0;text-align:center;font-family:Helvetica,Arial,sans-serif;font-size:13px"><a href="${href}" style="color:#52284F;text-decoration:underline">${esc(label)}</a></p>`;
  }
  // each step: a photo tile with a small gold number, then the words
  function steps(items) {
    return `<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:22px 0 6px">${items.map((it, i) => `
      <tr><td valign="top" width="124" style="padding:0 0 20px">
        <table role="presentation" cellspacing="0" cellpadding="0" border="0"><tr><td style="border-radius:16px;overflow:hidden;background:#3D1C3B;border:2px solid #3D1C3B"><img src="${TILE}tile-${it[2]}.jpg" width="120" height="160" alt="${esc(it[0])} in the Lazo app" style="display:block;width:120px;height:160px;border:0;border-radius:14px"></td></tr>
        <tr><td align="left" style="padding:0"><table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:-16px 0 0 8px"><tr><td align="center" width="28" height="28" bgcolor="#D9B77C" style="border-radius:14px;background:#D9B77C;font-family:Georgia,'Times New Roman',serif;font-size:14px;color:#3D1C3B;font-weight:bold;line-height:28px;border:2px solid #FFFFFF">${i + 1}</td></tr></table></td></tr></table></td>
      <td valign="top" style="padding:2px 0 20px 16px;font-family:Helvetica,Arial,sans-serif;font-size:15px;line-height:1.6;color:#241E2B"><b style="color:#3D1C3B;font-size:16px">${esc(it[0])}</b><br><span style="color:#5B5363">${it[1]}</span></td></tr>`).join('')}</table>`;
  }
  // a row of three photo tiles with captions (categories, moments)
  function tiles(items) {
    return `<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:8px 0 4px"><tr>${items.map((t, i) => `
      <td width="33%" valign="top" style="padding:0 ${i < 2 ? '8px' : '0'} 0 0"><table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"><tr><td style="border-radius:14px;overflow:hidden;background:#EADFCB"><a href="${t[2] || SITE}" style="text-decoration:none"><img src="${PH}${t[0]}" width="170" alt="${esc(t[1])}" style="display:block;width:100%;height:auto;border:0;border-radius:14px"></a></td></tr>
      <tr><td align="center" style="padding:7px 0 0;font-family:Helvetica,Arial,sans-serif;font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;color:#8A6A2F">${esc(t[1])}</td></tr></table></td>`).join('')}</tr></table>`;
  }
  const gap = (px) => `<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"><tr><td height="${px}" style="font-size:0;line-height:0">&nbsp;</td></tr></table>`;
  // a gold flourish between sections
  const flourish = `<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:26px 0 20px"><tr><td style="border-top:1px solid #EADFCB;font-size:0;line-height:0">&nbsp;</td><td width="60" align="center" style="font-family:Georgia,'Times New Roman',serif;font-size:18px;color:#D9B77C;line-height:1">&#10087;</td><td style="border-top:1px solid #EADFCB;font-size:0;line-height:0">&nbsp;</td></tr></table>`;
  function frame({ preheader, kicker, title, lede, body, cta, ctaHref, secondary, secondaryHref, signoff, hero, heroAlt }) {
    return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(title)}</title></head>
<body style="margin:0;padding:0;background:#FAF6F0">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;color:#FAF6F0">${esc(preheader)}${'&zwnj;&nbsp;'.repeat(40)}</div>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" bgcolor="#FAF6F0" style="background:#FAF6F0"><tr><td align="center" style="padding:28px 14px">
<table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" style="max-width:600px;width:100%">
  <tr><td bgcolor="#3D1C3B" align="center" style="background:#3D1C3B;background-image:linear-gradient(180deg,#52284F,#3D1C3B);border-radius:22px 22px 0 0;padding:30px 24px 24px">
    <a href="${SITE}" style="text-decoration:none"><img src="${LOGO}" width="150" alt="Lazo — Tied together" style="display:block;width:150px;height:auto;border:0;margin:0 auto"></a>
    <p style="margin:16px 0 0;font-family:Helvetica,Arial,sans-serif;font-size:11px;letter-spacing:.32em;text-transform:uppercase;color:#D9B77C">${esc(kicker)}</p>
  </td></tr>
  <tr><td bgcolor="#D9B77C" height="3" style="background:#D9B77C;font-size:0;line-height:0">&nbsp;</td></tr>
  ${hero ? `<tr><td bgcolor="#3D1C3B" style="background:#3D1C3B;font-size:0;line-height:0"><img src="${PH}${hero}" width="600" alt="${esc(heroAlt || '')}" style="display:block;width:100%;max-width:600px;height:auto;border:0"></td></tr>` : ''}
  <tr><td bgcolor="#FFFFFF" style="background:#FFFFFF;padding:34px 36px 30px;border-radius:0 0 22px 22px;border:1px solid #EADFCB;border-top:0">
    <h1 style="margin:0 0 14px;font-family:Georgia,'Times New Roman',serif;font-weight:normal;font-size:30px;line-height:1.15;color:#3D1C3B;letter-spacing:-.3px">${title}</h1>
    <p style="margin:0 0 18px;font-family:Helvetica,Arial,sans-serif;font-size:16px;line-height:1.65;color:#241E2B">${lede}</p>
    ${body}
    ${cta ? button(cta, ctaHref) : ''}
    ${secondary ? quietLink(secondary, secondaryHref) : ''}
    ${flourish}
    <p style="margin:0;font-family:Helvetica,Arial,sans-serif;font-size:14px;line-height:1.6;color:#5B5363">${signoff}</p>
    <p style="margin:14px 0 0;font-family:Georgia,'Times New Roman',serif;font-size:15px;color:#52284F">— The Lazo team<br><span style="font-style:italic;color:#8A6A2F">Tied together.</span></p>
  </td></tr>
  <tr><td align="center" style="padding:18px 10px 0;font-family:Helvetica,Arial,sans-serif;font-size:11.5px;line-height:1.7;color:#8C8291">
    Lazo · the verified wedding marketplace · <a href="${SITE}" style="color:#8C8291">meetlazo.com</a><br>
    You're getting this because you created a Lazo account. <a href="${SITE}privacy/" style="color:#8C8291">Privacy</a>
  </td></tr>
</table></td></tr></table></body></html>`;
  }

  // ---------------- the couple's welcome ----------------
  function coupleEmail(c, me) {
    const names = str(c.names).trim();
    const who = names || firstName(me) || 'you two';
    const metro = METROS[str(c.metroId)] || '';
    let days = null, dateLine = '';
    const wd = c.weddingDate && typeof c.weddingDate.toDate === 'function' ? c.weddingDate.toDate() : (c.weddingDate ? new Date(c.weddingDate) : null);
    if (wd && !isNaN(wd)) {
      days = Math.round((Date.UTC(wd.getUTCFullYear(), wd.getUTCMonth(), wd.getUTCDate()) - Date.UTC(new Date().getUTCFullYear(), new Date().getUTCMonth(), new Date().getUTCDate())) / 86400e3);
      dateLine = wd.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
    }
    const countdown = days != null && days > 0 ? `<table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin:4px 0 20px"><tr><td align="center" bgcolor="#FAF6F0" style="background:#FAF6F0;border:1px solid #EADFCB;border-radius:16px;padding:18px">
        <p style="margin:0;font-family:Georgia,'Times New Roman',serif;font-size:44px;line-height:1;color:#52284F">${days}</p>
        <p style="margin:6px 0 0;font-family:Helvetica,Arial,sans-serif;font-size:11px;letter-spacing:.28em;text-transform:uppercase;color:#8A6A2F">days until ${esc(dateLine)}</p></td></tr></table>` : '';
    const lede = metro
      ? `Your wedding plan is open${dateLine ? '' : ' and waiting for a date'}, with vendors across ${esc(metro)} already in it. Every listing on Lazo is verified, every review is from a couple who booked, and no vendor can pay to be ranked above another. Here's how most couples start.`
      : `Your wedding plan is open. Every listing on Lazo is verified, every review is from a couple who booked, and no vendor can pay to be ranked above another. Here's how most couples start.`;
    const vendorsUrl = metro ? `${SITE}vendors/${esc(str(c.metroId))}/` : `${SITE}vendors/`;
    const body = countdown + steps([
      ['Pick your city and date', 'They power vendor search, your budget lines and the weather on your day. Change either any time.', 'home'],
      ['Build your team', 'Venue and planner first, then photographer, caterer, music. Message any vendor from the app; they reply in the same thread, where proposals, contracts and payments live.', 'team'],
      ['Meet June', 'Your planning assistant. She reads your real plan, tells you what to do next, drafts messages to vendors, keeps the budget honest and reads you a daily brief, out loud if you like.', 'june'],
    ]) + flourish + `<p style="margin:0 0 12px;font-family:Georgia,'Times New Roman',serif;font-size:21px;color:#3D1C3B">${metro ? 'Verified in ' + esc(metro) : 'Verified, everywhere we are'}</p>`
      + tiles([['wedding-photographers.jpg', 'Photographers', vendorsUrl + 'wedding-photographers/'], ['wedding-florists.jpg', 'Florists', vendorsUrl + 'wedding-florists/'], ['wedding-cakes.jpg', 'Cakes', vendorsUrl + 'wedding-cakes/']])
      + `<p style="margin:16px 0 0;font-family:Helvetica,Arial,sans-serif;font-size:14.5px;line-height:1.6;color:#5B5363">Planning with someone? Invite your partner from the dashboard and you'll share one plan.</p>`;
    return {
      subject: dateLine ? `Welcome to Lazo, ${who}. ${days > 0 ? days + ' days to go.' : 'Your plan is open.'}` : `Welcome to Lazo, ${who}`,
      html: frame({ preheader: 'Your wedding plan is open. Verified vendors, one thread per vendor, and June to keep it all straight.', kicker: 'Welcome', title: `Welcome, ${esc(who)}.`, lede, body, cta: 'Open your plan', ctaHref: APP, secondary: 'Say hello to June', secondaryHref: JUNE, signoff: 'Questions, ideas, a vendor you wish we listed? Reply to this email. It reaches a person.', hero: 'hero-2.jpg', heroAlt: 'A couple on their wedding day' }),
      text: `Welcome to Lazo, ${who}.\n\n${dateLine ? days + ' days until ' + dateLine + '.\n\n' : ''}Your wedding plan is open${metro ? ', with vendors across ' + metro + ' already in it' : ''}. Every listing is verified, every review is from a couple who booked, and no vendor can pay to be ranked above another.\n\n1. Pick your city and date. 2. Build your team: venue and planner first, then photographer, caterer, music. 3. Meet June, your planning assistant: ${JUNE}\n\nOpen your plan: ${APP}\n\nReply to this email and it reaches a person.\n\n- The Lazo team. Tied together.`,
    };
  }

  // ---------------- the vendor's welcome ----------------
  function vendorEmail(u) {
    const who = firstName(u.display_name || u.displayName) || 'there';
    const claimed = !!str(u.vendorId);
    const lede = claimed
      ? `Your account is attached to your listing. From here on, every inquiry from a Lazo couple lands in your dashboard, and by text the moment you add a phone number.`
      : `Your account is ready. One thing left before couples can find you: claim your listing (or create one) from the dashboard. It takes about two minutes.`;
    const body = steps([
      [claimed ? 'Fill out the profile' : 'Claim your listing', claimed ? 'Photos and packages with prices do most of the work. Profiles with a gallery and visible pricing get several times the inquiries.' : 'Search for your business name in the app. If it is already there, claim it; if not, create it. Add photos and packages with prices: that is what gets inquiries.', 'find'],
      ['Get verified', 'Verification is free and never for sale. It is a badge couples filter by, and verified listings rank above unverified ones at the same score.', 'verified'],
      ['Reply fast, from anywhere', 'Add your phone and new leads reach you by text. Reply in the app: proposals, contracts, invoices and payments all live in the same thread as the conversation.', 'thread'],
      ['Meet June', 'Your studio manager. Who is waiting on you, this week’s weddings with the forecast, money due, a first-reply draft for every lead, and a morning brief read aloud.', 'june'],
    ]) + flourish + `<p style="margin:0 0 12px;font-family:Georgia,'Times New Roman',serif;font-size:21px;color:#3D1C3B">What couples are booking on Lazo</p>`
      + tiles([['wedding-venues.jpg', 'Venues', SITE + 'vendors/'], ['atmo-firstdance.jpg', 'Music', SITE + 'vendors/'], ['wedding-florists.jpg', 'Florals', SITE + 'vendors/']]);
    return {
      subject: claimed ? `Welcome to Lazo, ${who}. Your listing is live.` : `Welcome to Lazo, ${who}. Claim your listing.`,
      html: frame({ preheader: 'Verified leads, no pay-to-play. Claim your listing and add your phone to get them by text.', kicker: 'Welcome, vendor', title: `Welcome, ${esc(who)}.`, lede, body, cta: claimed ? 'Open your dashboard' : 'Claim your listing', ctaHref: DASH, secondary: 'Talk to June', secondaryHref: JUNE, hero: 'hero-1.jpg', heroAlt: 'A wedding on Lazo', signoff: 'We planned our own weddings on the big directories and came away tired of paying for position. Lazo ranks on reviews from real bookings, nothing else. Reply to this email with anything at all; it reaches a person.' }),
      text: `Welcome to Lazo, ${who}.\n\n${claimed ? 'Your account is attached to your listing.' : 'One thing left: claim your listing (or create one) from the dashboard.'}\n\n1. ${claimed ? 'Fill out the profile: photos and packages with prices.' : 'Claim your listing and add photos and packages with prices.'} 2. Get verified: free, never for sale. 3. Add your phone: new leads reach you by text. 4. Meet June, your studio manager: ${JUNE}\n\nDashboard: ${DASH}\n\nReply to this email and it reaches a person.\n\n- The Lazo team. Tied together.`,
    };
  }

  // ---------------- triggers ----------------
  const welcomeCouple = onDocumentCreated({ document: 'couples/{uid}', region: 'us-central1', memory: '256MiB', secrets: [RESEND_API_KEY] }, async (event) => {
    const uid = event.params.uid; const snap = event.data; if (!snap) return;
    const c = snap.data() || {};
    if (c.demo === true || uid.startsWith('demo_')) return;
    const us = await db().collection('users').doc(uid).get().catch(() => null);
    const u = us && us.exists ? us.data() : {};
    if (str(u.role) === 'vendor') return;
    const to = await emailFor(uid, u); if (!to) { console.log('welcomeCouple: no email for', uid); return; }
    if (!(await claim(snap.ref))) return;
    const m = coupleEmail(c, u.display_name || u.displayName);
    try { await sendEmail(to, m.subject, m.html, m.text); console.log('welcomeCouple sent', uid); }
    catch (e) { console.error('welcomeCouple', uid, e.message); await snap.ref.update({ welcomeSentAt: admin.firestore.FieldValue.delete(), welcomeError: String(e.message).slice(0, 200) }).catch(() => {}); }
  });

  const welcomeVendor = onDocumentWritten({ document: 'users/{uid}', region: 'us-central1', memory: '256MiB', secrets: [RESEND_API_KEY] }, async (event) => {
    const after = event.data && event.data.after; if (!after || !after.exists) return;
    const before = event.data.before && event.data.before.exists ? event.data.before.data() : {};
    const u = after.data() || {};
    if (str(u.role) !== 'vendor' || str(before.role) === 'vendor' || u.welcomeSentAt) return;   // first time the role lands
    const uid = event.params.uid;
    const to = await emailFor(uid, u); if (!to) { console.log('welcomeVendor: no email for', uid); return; }
    if (!(await claim(after.ref))) return;
    const m = vendorEmail(u);
    try { await sendEmail(to, m.subject, m.html, m.text); console.log('welcomeVendor sent', uid); }
    catch (e) { console.error('welcomeVendor', uid, e.message); await after.ref.update({ welcomeSentAt: admin.firestore.FieldValue.delete(), welcomeError: String(e.message).slice(0, 200) }).catch(() => {}); }
  });

  return { welcomeCouple, welcomeVendor, _render: { coupleEmail, vendorEmail } };
};

// END OF FILE - JC-LAZO-FNDASH-1007-023
