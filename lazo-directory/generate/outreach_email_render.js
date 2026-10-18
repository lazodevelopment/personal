// generate/outreach_email_render.js - JC-LAZO-OUTREACH-1018
//
// The "claim your profile" email, rendered in Lazo's own frame (functions-dashboard/email-frame.js) so it
// matches every other email Lazo sends. This file only RENDERS: it writes a sample HTML + plain-text pair
// for approval, and exports render(vendor) for whatever sends it later. Nothing here sends.
//
//   node generate\outreach_email_render.js            -> generate/data/outreach/_sample-email.html / .txt
//
// Links: claim  = meetlazo.com/claim/{token}         tracked redirect -> app.meetlazo.com/?claim={vendorId}
//        page   = the vendor's own page on meetlazo.com
//        signup = app.meetlazo.com/?claim={vendorId}  the app's claim screen, pre-filled after signup
//        stop   = meetlazo.com/claim/{token}/stop     one-click unsubscribe (also the List-Unsubscribe header)
'use strict';
const path = require('path');
const fs = require('fs');
const F = require(path.join(__dirname, '..', '..', 'lazo-functions', 'functions-dashboard', 'email-frame.js'));
const { frame, esc, str, SITE, APP } = F;

// CAN-SPAM needs a real postal address. Lazo publishes only "Lazo Weddings, LLC, Phoenix, Arizona"; Jesse
// supplies the street or PO Box before the first send.
const APP_STORE = 'https://apps.apple.com/us/app/lazo-wedding-planner/id6812863675';
const PLAY_STORE = 'https://play.google.com/store/apps/details?id=com.meetlazo.app';
const POSTAL = process.env.LAZO_POSTAL || 'Lazo Weddings, LLC · [street or PO Box], Phoenix, AZ [zip]';
const SINGULAR = {
  'wedding-photographers': 'wedding photographer', 'wedding-videographers': 'wedding videographer', 'wedding-venues': 'wedding venue',
  'wedding-planners': 'wedding planner', 'wedding-djs': 'wedding DJ', 'wedding-florists': 'wedding florist', 'wedding-caterers': 'wedding caterer',
  'wedding-cakes': 'wedding cake baker', 'hair-and-makeup': 'bridal hair and makeup artist', 'wedding-officiants': 'wedding officiant',
  'wedding-transportation': 'wedding transportation company', 'wedding-rentals': 'wedding rental company', 'wedding-bands': 'wedding band',
  'wedding-invitations': 'wedding stationer', 'day-of-coordination': 'day-of coordinator',
};
const PLURAL = {
  'wedding-photographers': 'photographers', 'wedding-videographers': 'videographers', 'wedding-venues': 'venues', 'wedding-planners': 'planners',
  'wedding-djs': 'DJs', 'wedding-florists': 'florists', 'wedding-caterers': 'caterers', 'wedding-cakes': 'cake bakers', 'hair-and-makeup': 'hair and makeup artists',
  'wedding-officiants': 'officiants', 'wedding-transportation': 'transportation', 'wedding-rentals': 'rentals', 'wedding-bands': 'bands',
  'wedding-invitations': 'stationers', 'day-of-coordination': 'day-of coordinators',
};

function render(v) {
  // v: { name, metroName, category, pageUrl, vendorId, token, siteHost, email }
  const name = str(v.name).trim();
  const metro = str(v.metroName).trim();
  const cat = SINGULAR[v.category] || 'wedding vendor';
  const plural = PLURAL[v.category] || 'vendors';
  const claim = `${SITE}claim/${v.token}`;
  const stop = `${SITE}claim/${v.token}/stop`;
  const signup = `${APP}?claim=${encodeURIComponent(v.vendorId)}`;
  const page = str(v.pageUrl);
  const shortPage = page.replace(/^https?:\/\//, '').replace(/\/$/, '');

  const subject = `${name}, your page on Lazo is live in ${metro}`;
  const preheader = `Couples in ${metro} can already see it. Claiming it is free and takes two minutes.`;
  const lede = `Couples planning weddings in ${esc(metro)} can already find <b>${esc(name)}</b> in Lazo's list of ${esc(plural)}. The page was built from public business information, so right now it has your name, address and website and not much else. It is yours to claim, free, and that takes about two minutes.`;

  const pageCard = `<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:6px 0 20px"><tr><td bgcolor="#FAF6F0" style="background:#FAF6F0;border:1px solid #EADFCB;border-radius:14px;padding:16px 18px">
    <p style="margin:0;font-family:Helvetica,Arial,sans-serif;font-size:10.5px;letter-spacing:.22em;text-transform:uppercase;color:#8A6A2F">Your page</p>
    <p style="margin:6px 0 2px;font-family:Georgia,'Times New Roman',serif;font-size:20px;line-height:1.2;color:#52284F">${esc(name)}</p>
    <p style="margin:0 0 8px;font-family:Helvetica,Arial,sans-serif;font-size:14px;color:#5B5363">${esc(cat.charAt(0).toUpperCase() + cat.slice(1))} · ${esc(metro)}</p>
    <p style="margin:0;font-family:Helvetica,Arial,sans-serif;font-size:13.5px"><a href="${page}" style="color:#52284F;text-decoration:underline">${esc(shortPage)}</a></p></td></tr></table>`;

  const points = [
    ['Claim it', 'Confirm the business is yours (a license, insurance certificate or EIN letter does it). Verified pages carry a badge and, until reviews arrive, come first in their list.'],
    ['Make it yours', 'Add photos, your packages and a price range. On Lazo, pages with a gallery and visible pricing get several times the inquiries.'],
    ['Hear from couples', 'Inquiries land in your inbox and, if you add a phone, by text. Every lead is yours alone. Lazo takes 0% of what couples pay you, and ranking can’t be bought.'],
  ];
  const body = pageCard
    + `<p style="margin:22px 0 6px;font-family:Georgia,'Times New Roman',serif;font-size:22px;line-height:1.25;color:#3D1C3B">Want something better than The Knot or Zola?</p>
    <p style="margin:0 0 16px;font-family:Helvetica,Arial,sans-serif;font-size:15px;line-height:1.6;color:#5B5363">No paying for position. No lead sold to five vendors at once. No cut of your bookings. On Lazo a page rises on verified reviews, reply speed and real bookings, and nothing else.</p>`
    + `<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:0 0 6px">${points.map(([h, t]) => `
    <tr><td valign="top" width="26" style="padding:0 0 14px;font-family:Georgia,'Times New Roman',serif;font-size:20px;line-height:1.3;color:#D9B77C">&#10087;</td>
    <td valign="top" style="padding:0 0 14px 6px;font-family:Helvetica,Arial,sans-serif;font-size:15px;line-height:1.6;color:#241E2B"><b style="color:#3D1C3B">${esc(h)}.</b> <span style="color:#5B5363">${t}</span></td></tr>`).join('')}</table>
    <p style="margin:8px 0 0;font-family:Helvetica,Arial,sans-serif;font-size:14px;line-height:1.6;color:#5B5363">Not the right fit, or you would rather the page did not exist? Reply with one word and we will take it down.</p>`;

  // the app, with the same store badges the site uses (PNG: email clients do not render SVG)
  const apps = `<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:22px 0 0"><tr><td align="center" bgcolor="#FAF6F0" style="background:#FAF6F0;border:1px solid #EADFCB;border-radius:14px;padding:18px 16px 14px">
    <p style="margin:0 0 4px;font-family:Georgia,'Times New Roman',serif;font-size:18px;color:#3D1C3B">Lazo is also an app.</p>
    <p style="margin:0 0 12px;font-family:Helvetica,Arial,sans-serif;font-size:13.5px;line-height:1.55;color:#5B5363">Claim your page, answer couples and send proposals from your phone.</p>
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:0 auto"><tr>
      <td style="padding:0 6px"><a href="${APP_STORE}" style="text-decoration:none"><img src="${SITE}assets/appstore-badge.png" width="120" height="40" alt="Download on the App Store" style="display:block;width:120px;height:40px;border:0"></a></td>
      <td style="padding:0 6px"><a href="${PLAY_STORE}" style="text-decoration:none"><img src="${SITE}assets/googleplay-badge.png" width="135" height="40" alt="Get it on Google Play" style="display:block;width:135px;height:40px;border:0"></a></td>
    </tr></table></td></tr></table>`;

  const html = frame({
    preheader, kicker: 'Your listing', title: `${esc(name)} is already on Lazo.`, lede, body,
    cta: 'Claim your page', ctaHref: claim,
    secondary: 'See your page first', secondaryHref: page,
    // the frame wraps signoff in a <p>; closing it lets the app block sit below the button, above the sign-off name
    signoff: `New here? <a href="${signup}" style="color:#52284F">Create your free vendor account</a> and the claim is waiting for you. Reply to this email and it reaches a person.</p>${apps}<p style="margin:0;font-size:0;line-height:0">`,
    footerWhy: `You're getting this one email because ${esc(name)} is listed on meetlazo.com and ${esc(v.siteHost || 'your website')} publishes this address. We won't write again unless you ask. <a href="${stop}" style="color:#8C8291">Unsubscribe</a> · ${esc(POSTAL)} ·`,
  });

  const text = `${name}, your page on Lazo is live in ${metro}.

Couples planning weddings in ${metro} can already find ${name} in Lazo's list of ${plural}:
${page}

The page was built from public business information, so right now it has your name, address and website and not much else. It is yours to claim, free, and that takes about two minutes.

Claim your page: ${claim}

Want something better than The Knot or Zola? No paying for position. No lead sold to five vendors at once. No cut of your bookings. On Lazo a page rises on verified reviews, reply speed and real bookings, and nothing else.

1. Claim it. Confirm the business is yours (a license, insurance certificate or EIN letter). Verified pages carry a badge and, until reviews arrive, come first in their list.
2. Make it yours. Add photos, your packages and a price range. Pages with a gallery and visible pricing get several times the inquiries.
3. Hear from couples. Inquiries land in your inbox and, if you add a phone, by text. Every lead is yours alone. Lazo takes 0% of what couples pay you, and ranking can't be bought.

New to Lazo? Create your free vendor account and the claim is waiting for you: ${signup}

Not the right fit, or you would rather the page did not exist? Reply with one word and we will take it down.

Lazo is also an app. Claim your page, answer couples and send proposals from your phone.
iPhone: ${APP_STORE}
Android: ${PLAY_STORE}

Reply to this email and it reaches a person.

- The Lazo team. Tied together.

You're getting this one email because ${name} is listed on meetlazo.com and ${v.siteHost || 'your website'} publishes this address. We won't write again unless you ask.
Unsubscribe: ${stop}
${POSTAL}
`;
  return { subject, html, text, headers: { 'List-Unsubscribe': `<${stop}>`, 'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click' } };
}

if (require.main === module) {
  const sample = { name: 'Hazel & Violet', metroName: 'Phoenix', category: 'wedding-florists', vendorId: 'ChIJExampleSample0001', token: 'sample-token-2b9Kq8',
                   pageUrl: 'https://meetlazo.com/phoenix/wedding-florists/hazel-violet/', siteHost: 'hazelandviolet.com' };
  const out = path.join(__dirname, 'data', 'outreach');
  fs.mkdirSync(out, { recursive: true });
  const m = render(sample);
  fs.writeFileSync(path.join(out, '_sample-email.html'), m.html);
  fs.writeFileSync(path.join(out, '_sample-email.txt'), `Subject: ${m.subject}\n\n${m.text}`);
  console.log('subject:', m.subject);
  console.log('wrote', path.join(out, '_sample-email.html'), 'and .txt');
}
module.exports = { render, SINGULAR, PLURAL };
