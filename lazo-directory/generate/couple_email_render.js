// generate/couple_email_render.js - JC-LAZO-COUPLES-1019
//
// The "come plan on Lazo" email for COUPLES who inquired through Zola or The Knot, rendered in Lazo's own frame
// (functions-dashboard/email-frame.js) like every other Lazo email. This file only RENDERS: it writes a sample
// HTML + plain-text pair for approval and exports render(couple) plus the Smartlead body (merge tags) for the
// campaign. Nothing here sends.
//
//   node generate\couple_email_render.js     -> generate/data/couples/_sample-email.html / .txt / _smartlead-body.html
//
// Links: plan   = meetlazo.com/plan/{token}        tracked redirect -> app.meetlazo.com/?src=couples (coupleGo)
//        stop   = meetlazo.com/plan/{token}/stop   one-click unsubscribe (coupleStop; also List-Unsubscribe)
//        learn  = meetlazo.com/couples/            the site's couples page
// Brand names (Atavia / Elizabeth Scott) are NOT mentioned unless NAME_BRANDS is set: Jesse's call.
'use strict';
const path = require('path');
const fs = require('fs');
const F = require(path.join(__dirname, '..', '..', 'lazo-functions', 'functions-dashboard', 'email-frame.js'));
const { frame, esc, str, SITE, APP } = F;

const APP_STORE = 'https://apps.apple.com/us/app/lazo-wedding-planner/id6812863675';
const PLAY_STORE = 'https://play.google.com/store/apps/details?id=com.meetlazo.app';
const POSTAL = process.env.LAZO_POSTAL || 'Lazo Weddings, LLC · 1309 Coffeen Ave, Ste 1200, Sheridan, WY 82801';
const NAME_BRANDS = /^1|true$/i.test(process.env.NAME_BRANDS || '');
const LEARN = `${SITE}couples/`;

function prettyDate(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(str(iso));
  if (!m) return '';
  const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
  return d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
}

// c: { firstName, names, weddingDate (YYYY-MM-DD or a merge tag), venue, token, plan, stop, brandLine }
function render(c) {
  const first = str(c.firstName).trim();
  const plan = c.plan || `${SITE}plan/${c.token}`;
  const stop = c.stop || `${SITE}plan/${c.token}/stop`;
  const when = c.whenText != null ? c.whenText : (prettyDate(c.weddingDate) ? ` on ${prettyDate(c.weddingDate)}` : '');
  const where = c.whereText != null ? c.whereText : (str(c.venue).trim() ? ` in ${esc(str(c.venue).trim())}` : '');
  const hi = first ? `${esc(first)}, ` : '';

  const subject = first ? `${first}, want something better than The Knot or Zola?` : 'Want something better than The Knot or Zola?';
  const preheader = 'Lazo is a free wedding planning app and vendor marketplace, built for couples, not for ad sales.';
  const lede = `${hi}you are planning a wedding${when}${where}, and you have probably noticed how The Knot and Zola work: vendors pay to rank, your inquiry is sold to five of them at once, and every page is pushing something. Lazo is the other way round. It is free for couples, the vendors are verified, and nobody can buy their way to the top.`;

  const points = [
    ['Vendors you can trust', 'Every vendor on Lazo is verified (licence, insurance or tax letter) and ranked only by real reviews, reply speed and bookings. Your message goes to the vendor you chose, and only to them.'],
    ['The whole wedding in one place', 'Guest list and RSVPs with meal choices, a free wedding website, budget, timeline, vendor messages, contracts and payments. Nothing to export, nothing to re-type.'],
    ['June, your planning assistant', 'Ask what is still open, draft a message to a vendor, build the day-of timeline. June knows your wedding and answers in seconds.'],
    ['Free, and your details stay yours', 'No fees for couples, no upsells, and we never sell your name or date to vendors. You decide who hears from you.'],
  ];

  const body = `<p style="margin:22px 0 6px;font-family:Georgia,'Times New Roman',serif;font-size:22px;line-height:1.25;color:#3D1C3B">What changes when you plan on Lazo</p>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:6px 0 6px">${points.map(([h, t]) => `
    <tr><td valign="top" width="26" style="padding:0 0 14px;font-family:Georgia,'Times New Roman',serif;font-size:20px;line-height:1.3;color:#D9B77C">&#10087;</td>
    <td valign="top" style="padding:0 0 14px 6px;font-family:Helvetica,Arial,sans-serif;font-size:15px;line-height:1.6;color:#241E2B"><b style="color:#3D1C3B">${esc(h)}.</b> <span style="color:#5B5363">${t}</span></td></tr>`).join('')}</table>
    <p style="margin:8px 0 0;font-family:Helvetica,Arial,sans-serif;font-size:14px;line-height:1.6;color:#5B5363">Already booked some vendors? Bring them along. Lazo lets you add any vendor, on Lazo or not, so your contracts, payments and messages live in one timeline.</p>`;

  const apps = `<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:22px 0 0"><tr><td align="center" bgcolor="#FAF6F0" style="background:#FAF6F0;border:1px solid #EADFCB;border-radius:14px;padding:18px 16px 14px">
    <p style="margin:0 0 4px;font-family:Georgia,'Times New Roman',serif;font-size:18px;color:#3D1C3B">Lazo is an app.</p>
    <p style="margin:0 0 12px;font-family:Helvetica,Arial,sans-serif;font-size:13.5px;line-height:1.55;color:#5B5363">Plan from your phone, together with your partner, wherever you are.</p>
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:0 auto"><tr>
      <td style="padding:0 6px"><a href="${APP_STORE}" style="text-decoration:none"><img src="${SITE}assets/appstore-badge.png" width="120" height="40" alt="Download on the App Store" style="display:block;width:120px;height:40px;border:0"></a></td>
      <td style="padding:0 6px"><a href="${PLAY_STORE}" style="text-decoration:none"><img src="${SITE}assets/googleplay-badge.png" width="135" height="40" alt="Get it on Google Play" style="display:block;width:135px;height:40px;border:0"></a></td>
    </tr></table></td></tr></table>`;

  const why = NAME_BRANDS
    ? `You're getting this one email because you sent a wedding inquiry to ${esc(c.brandLine || 'Atavia Weddings or Elizabeth Scott Weddings')}, studios that plan with Lazo. We won't write again unless you ask.`
    : `You're getting this one email because you sent a wedding inquiry through The Knot or Zola to a studio that plans with Lazo. We won't write again unless you ask.`;

  const html = frame({
    preheader, kicker: 'For couples', title: 'Want something better than The Knot or Zola?', lede, body,
    cta: 'Start planning on Lazo', ctaHref: plan,
    secondary: 'See how Lazo works first', secondaryHref: LEARN,
    signoff: `It takes a minute to set up and your wedding date, guest list and website are ready the same day. Reply to this email and it reaches a person.</p>${apps}<p style="margin:0;font-size:0;line-height:0">`,
    footerWhy: `${why} <a href="${stop}" style="color:#8C8291">Unsubscribe</a> · ${esc(POSTAL)} ·`,
  });

  const text = `${subject}

${hi}you are planning a wedding${when}${where.replace(/&amp;/g, '&')}, and you have probably noticed how The Knot and Zola work: vendors pay to rank, your inquiry is sold to five of them at once, and every page is pushing something. Lazo is the other way round. It is free for couples, the vendors are verified, and nobody can buy their way to the top.

Start planning on Lazo: ${plan}

What changes when you plan on Lazo
${points.map(([h, t], i) => `${i + 1}. ${h}. ${t}`).join('\n')}

Already booked some vendors? Bring them along. Lazo lets you add any vendor, on Lazo or not, so your contracts, payments and messages live in one timeline.

See how Lazo works first: ${LEARN}

Lazo is an app. Plan from your phone, together with your partner.
iPhone: ${APP_STORE}
Android: ${PLAY_STORE}

It takes a minute to set up and your wedding date, guest list and website are ready the same day. Reply to this email and it reaches a person.

- The Lazo team. Tied together.

${why.replace(/&#39;/g, "'")}
Unsubscribe: ${stop}
${POSTAL}
`;
  return { subject, html, text, headers: { 'List-Unsubscribe': `<${stop}>`, 'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click' } };
}

// The Smartlead version: merge tags instead of values. Custom fields the lead upload must carry:
// first_name (built-in), wedding_when (" on October 2, 2027" or ""), wedding_where (" in Harwinton, CT" or ""),
// plan_url, stop_url.
function smartlead() {
  return render({ firstName: '{{first_name}}', whenText: '{{wedding_when}}', whereText: '{{wedding_where}}',
                  plan: '{{plan_url}}', stop: '{{stop_url}}' });
}

if (require.main === module) {
  const out = path.join(__dirname, 'data', 'couples');
  fs.mkdirSync(out, { recursive: true });
  const m = render({ firstName: 'Cassidy', weddingDate: '2027-10-02', venue: 'Harwinton, CT', token: 'sample-token-2b9Kq8' });
  fs.writeFileSync(path.join(out, '_sample-email.html'), m.html);
  fs.writeFileSync(path.join(out, '_sample-email.txt'), `Subject: ${m.subject}\n\n${m.text}`);
  const s = smartlead();
  fs.writeFileSync(path.join(out, '_smartlead-body.html'), s.html);
  fs.writeFileSync(path.join(out, '_smartlead-body.txt'), `Subject: ${s.subject}\n\n${s.text}`);
  console.log('subject:', m.subject);
  console.log('wrote', out, '_sample-email.html/.txt and _smartlead-body.html/.txt');
}
module.exports = { render, smartlead };
