// functions-dashboard/brand.js
// Build ID: JC-LAZO-FNDASH-0913-014
// The vendor's brand on every couple-facing email: logo + name header in
// their primary color, their font, a quiet "sent through Lazo" footer.
// Vendor-facing emails (digests, alerts) stay Lazo-branded - not wrapped.
'use strict';
const HEX = /^#[0-9a-f]{6}$/i;
const str = (v) => (v == null ? '' : String(v));
const esc = (t) => str(t).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

function brandOf(v) {
  const b = v && v.brand && typeof v.brand === 'object' ? v.brand : {};
  return {
    name: str(v && v.name), logoUrl: str(v && v.logoUrl),
    primary: HEX.test(str(b.primary)) ? b.primary : '#52284F',
    accent: HEX.test(str(b.accent)) ? b.accent : '#D9B77C',
    font: b.font === 'serif' ? 'Georgia, serif' : 'Helvetica, Arial, sans-serif',
  };
}

// wrap(vendorDoc, innerHtml) -> full email html
function wrap(v, inner) {
  const b = brandOf(v);
  const logo = b.logoUrl ? `<img src="https://wsrv.nl/?url=${encodeURIComponent(b.logoUrl)}&w=96&h=96&fit=contain" width="48" height="48" style="display:block;border-radius:10px;background:#fff" alt="">` : '';
  return `<!doctype html><html><body style="margin:0;background:#FAF6F0;font-family:${b.font};color:#241E2B">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%">
<tr><td style="background:${b.primary};border-radius:16px 16px 0 0;padding:18px 22px;color:#fff">
  <table role="presentation" cellpadding="0" cellspacing="0"><tr>${logo ? `<td style="padding-right:12px">${logo}</td>` : ''}<td style="font-size:18px;font-weight:600;letter-spacing:.2px">${esc(b.name || 'Your vendor')}</td></tr></table>
</td></tr>
<tr><td style="background:#FFFDF9;border:1px solid #E6D6B8;border-top:0;border-radius:0 0 16px 16px;padding:22px;font-size:15px;line-height:1.55">${inner}</td></tr>
<tr><td style="padding:14px 6px;font-size:11px;color:#8A7F90;text-align:center">Sent through <a href="https://meetlazo.com" style="color:#8A7F90">Lazo</a> on behalf of ${esc(b.name || 'your vendor')}. Reply STOP to any text to stop texts.</td></tr>
</table></td></tr></table></body></html>`;
}

module.exports = { brandOf, wrap };
