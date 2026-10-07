// functions-dashboard/email-frame.js
// Build ID: JC-LAZO-FNDASH-1007-024
//
// THE LAZO EMAIL FRAME, shared by welcome.js and couple-notify.js: plum band
// with the ivory lockup, optional hero photo, ivory page, white card, Georgia
// headings, gold pill button, "Tied together." sign-off. Table layout with
// inline styles so it holds in Gmail, Apple Mail and Outlook. Vendor-originated
// mail (a reply, a proposal, an invoice) uses brand.js instead, in the vendor's
// own colours with a "sent through Lazo" footer; this frame is Lazo speaking.

'use strict';

const str = (v) => (v == null ? '' : String(v));
const esc = (s) => str(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const SITE = 'https://meetlazo.com/';
const APP = 'https://app.meetlazo.com/';
const DASH = 'https://app.meetlazo.com/dashboard';
const JUNE = 'https://june.meetlazo.com/';
const LOGO = 'https://meetlazo.com/assets/foot-logo.png';
const PH = 'https://meetlazo.com/assets/photos/';   // the site's own photography
const TILE = 'https://meetlazo.com/assets/email/';  // 240x320 crops of the app screens (deploy/upload_r2.py --prefix assets/email)
const money = (n) => '$' + Math.round(+n || 0).toLocaleString('en-US');

function button(label, href) {
  return `<table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:26px auto 6px"><tr><td align="center" bgcolor="#D9B77C" style="border-radius:999px;background:#D9B77C">
    <a href="${href}" style="display:inline-block;padding:14px 30px;font-family:Helvetica,Arial,sans-serif;font-size:15px;font-weight:bold;color:#3D1C3B;text-decoration:none;border-radius:999px;letter-spacing:.2px">${esc(label)}</a></td></tr></table>`;
}
function quietLink(label, href) {
  return `<p style="margin:10px 0 0;text-align:center;font-family:Helvetica,Arial,sans-serif;font-size:13px"><a href="${href}" style="color:#52284F;text-decoration:underline">${esc(label)}</a></p>`;
}
// each step: a phone-screen tile (assets/email/tile-<key>.jpg), then the words
function steps(items) {
  return `<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:22px 0 6px">${items.map((it) => `
    <tr><td valign="top" width="124" style="padding:0 0 20px">
      <table role="presentation" cellspacing="0" cellpadding="0" border="0"><tr><td style="border-radius:16px;overflow:hidden;background:#3D1C3B;border:2px solid #3D1C3B"><img src="${TILE}tile-${it[2]}.jpg" width="120" height="160" alt="${esc(it[0])} in the Lazo app" style="display:block;width:120px;height:160px;border:0;border-radius:14px"></td></tr></table></td>
    <td valign="top" style="padding:2px 0 20px 16px;font-family:Helvetica,Arial,sans-serif;font-size:15px;line-height:1.6;color:#241E2B"><b style="color:#3D1C3B;font-size:16px">${esc(it[0])}</b><br><span style="color:#5B5363">${it[1]}</span></td></tr>`).join('')}</table>`;
}
// a row of three photo tiles with captions
function tiles(items) {
  return `<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:8px 0 4px"><tr>${items.map((t, i) => `
    <td width="33%" valign="top" style="padding:0 ${i < 2 ? '8px' : '0'} 0 0"><table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"><tr><td style="border-radius:14px;overflow:hidden;background:#EADFCB"><a href="${t[2] || SITE}" style="text-decoration:none"><img src="${t[0].startsWith('http') ? t[0] : PH + t[0]}" width="170" alt="${esc(t[1])}" style="display:block;width:100%;height:auto;border:0;border-radius:14px"></a></td></tr>
    <tr><td align="center" style="padding:7px 0 0;font-family:Helvetica,Arial,sans-serif;font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;color:#8A6A2F">${esc(t[1])}</td></tr></table></td>`).join('')}</tr></table>`;
}
// a quiet fact box: label over value, used for amounts, dates, counts
function facts(items) {
  return `<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:6px 0 18px"><tr>${items.map((f, i) => `
    <td width="${Math.floor(100 / items.length)}%" valign="top" style="padding:0 ${i < items.length - 1 ? '8px' : '0'} 0 0"><table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"><tr><td bgcolor="#FAF6F0" style="background:#FAF6F0;border:1px solid #EADFCB;border-radius:14px;padding:14px 12px;text-align:center">
      <p style="margin:0;font-family:Georgia,'Times New Roman',serif;font-size:${f[1] && String(f[1]).length > 14 ? 17 : 24}px;line-height:1.15;color:#52284F">${esc(f[1])}</p>
      <p style="margin:6px 0 0;font-family:Helvetica,Arial,sans-serif;font-size:10.5px;letter-spacing:.22em;text-transform:uppercase;color:#8A6A2F">${esc(f[0])}</p></td></tr></table></td>`).join('')}</tr></table>`;
}
// a big centred number with a caption (the countdown)
function count(n, caption) {
  return `<table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin:4px 0 20px"><tr><td align="center" bgcolor="#FAF6F0" style="background:#FAF6F0;border:1px solid #EADFCB;border-radius:16px;padding:18px">
    <p style="margin:0;font-family:Georgia,'Times New Roman',serif;font-size:44px;line-height:1;color:#52284F">${esc(n)}</p>
    <p style="margin:6px 0 0;font-family:Helvetica,Arial,sans-serif;font-size:11px;letter-spacing:.28em;text-transform:uppercase;color:#8A6A2F">${esc(caption)}</p></td></tr></table>`;
}
// a quoted message from a vendor
function quote(text, who) {
  return `<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:6px 0 18px"><tr><td style="border-left:3px solid #D9B77C;padding:4px 0 4px 16px;font-family:Georgia,'Times New Roman',serif;font-size:17px;line-height:1.5;color:#241E2B;font-style:italic">${esc(text).replace(/\n/g, '<br>')}</td></tr>${who ? `<tr><td style="padding:8px 0 0 19px;font-family:Helvetica,Arial,sans-serif;font-size:12.5px;color:#8A6A2F">— ${esc(who)}</td></tr>` : ''}</table>`;
}
const flourish = `<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:26px 0 20px"><tr><td style="border-top:1px solid #EADFCB;font-size:0;line-height:0">&nbsp;</td><td width="60" align="center" style="font-family:Georgia,'Times New Roman',serif;font-size:18px;color:#D9B77C;line-height:1">&#10087;</td><td style="border-top:1px solid #EADFCB;font-size:0;line-height:0">&nbsp;</td></tr></table>`;

function frame({ preheader, kicker, title, lede, body = '', cta, ctaHref, secondary, secondaryHref, signoff, hero, heroAlt, footerWhy }) {
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(title)}</title></head>
<body style="margin:0;padding:0;background:#FAF6F0">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;color:#FAF6F0">${esc(preheader || '')}${'&zwnj;&nbsp;'.repeat(40)}</div>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" bgcolor="#FAF6F0" style="background:#FAF6F0"><tr><td align="center" style="padding:28px 14px">
<table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" style="max-width:600px;width:100%">
  <tr><td bgcolor="#3D1C3B" align="center" style="background:#3D1C3B;background-image:linear-gradient(180deg,#52284F,#3D1C3B);border-radius:22px 22px 0 0;padding:30px 24px 24px">
    <a href="${SITE}" style="text-decoration:none"><img src="${LOGO}" width="150" alt="Lazo — Tied together" style="display:block;width:150px;height:auto;border:0;margin:0 auto"></a>
    <p style="margin:16px 0 0;font-family:Helvetica,Arial,sans-serif;font-size:11px;letter-spacing:.32em;text-transform:uppercase;color:#D9B77C">${esc(kicker || '')}</p>
  </td></tr>
  <tr><td bgcolor="#D9B77C" height="3" style="background:#D9B77C;font-size:0;line-height:0">&nbsp;</td></tr>
  ${hero ? `<tr><td bgcolor="#3D1C3B" style="background:#3D1C3B;font-size:0;line-height:0"><img src="${hero.startsWith('http') ? hero : PH + hero}" width="600" alt="${esc(heroAlt || '')}" style="display:block;width:100%;max-width:600px;height:auto;border:0"></td></tr>` : ''}
  <tr><td bgcolor="#FFFFFF" style="background:#FFFFFF;padding:34px 36px 30px;border-radius:0 0 22px 22px;border:1px solid #EADFCB;border-top:0">
    <h1 style="margin:0 0 14px;font-family:Georgia,'Times New Roman',serif;font-weight:normal;font-size:30px;line-height:1.15;color:#3D1C3B;letter-spacing:-.3px">${title}</h1>
    ${lede ? `<p style="margin:0 0 18px;font-family:Helvetica,Arial,sans-serif;font-size:16px;line-height:1.65;color:#241E2B">${lede}</p>` : ''}
    ${body}
    ${cta ? button(cta, ctaHref) : ''}
    ${secondary ? quietLink(secondary, secondaryHref) : ''}
    ${flourish}
    <p style="margin:0;font-family:Helvetica,Arial,sans-serif;font-size:14px;line-height:1.6;color:#5B5363">${signoff || 'Questions? Reply to this email. It reaches a person.'}</p>
    <p style="margin:14px 0 0;font-family:Georgia,'Times New Roman',serif;font-size:15px;color:#52284F">— The Lazo team<br><span style="font-style:italic;color:#8A6A2F">Tied together.</span></p>
  </td></tr>
  <tr><td align="center" style="padding:18px 10px 0;font-family:Helvetica,Arial,sans-serif;font-size:11.5px;line-height:1.7;color:#8C8291">
    Lazo · the verified wedding marketplace · <a href="${SITE}" style="color:#8C8291">meetlazo.com</a><br>
    ${footerWhy || "You're getting this because you created a Lazo account."} <a href="${SITE}privacy/" style="color:#8C8291">Privacy</a>
  </td></tr>
</table></td></tr></table></body></html>`;
}

module.exports = { frame, button, quietLink, steps, tiles, facts, count, quote, flourish, esc, str, money, SITE, APP, DASH, JUNE, LOGO, PH, TILE };

// END OF FILE - JC-LAZO-FNDASH-1007-024
