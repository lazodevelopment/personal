// JC-LAZO-FN-1007-RESTORE: recovered from the 2026-09-21 production build (the local tree never had it).
// Lazo — one branded shell for every email we send (v52)
// Written once so the fifth template can't drift from the first.
const APP_URL = "https://app.meetlazo.com";

function shell(inner, opts) {
  const o = opts || {};
  const foot = o.footer ||
    'Lazo Weddings, LLC \u00b7 <a href="https://meetlazo.com" ' +
    'style="color:#8A7F90">meetlazo.com</a>';
  return '<div style="background:#F1EAF0;padding:30px 0;font-family:Lato,' +
    'Helvetica,Arial,sans-serif">' +
    '<div style="max-width:520px;margin:0 auto;background:#FAF6F0;' +
    'border:1px solid rgba(217,183,124,.55);border-radius:20px;overflow:hidden">' +
    '<div style="background:linear-gradient(135deg,#52284F,#3D1C3B);padding:24px 28px">' +
    '<div style="color:#FAF6F0;font-size:21px;letter-spacing:5px;' +
    'font-family:Georgia,serif">L A Z O</div>' +
    (o.eyebrow ? '<div style="color:#D9B77C;font-size:10px;letter-spacing:2.4px;' +
      'margin-top:6px;font-weight:700">' + o.eyebrow + '</div>' : '') +
    '</div>' +
    '<div style="padding:26px 28px;color:#241E2B;font-size:15px;line-height:1.62">' +
    inner + '</div>' +
    '<div style="padding:14px 28px;border-top:1px solid rgba(217,183,124,.4);' +
    'color:#8A7F90;font-size:11px">' + foot + '</div></div></div>';
}

function h1(text) {
  return '<p style="font-family:Georgia,serif;font-size:23px;color:#52284F;' +
    'margin:0 0 10px;line-height:1.3">' + text + '</p>';
}

function button(label, url) {
  return '<div style="margin:22px 0"><a href="' + (url || APP_URL) + '" ' +
    'style="background:#D9B77C;color:#52284F;text-decoration:none;' +
    'padding:13px 24px;border-radius:12px;font-weight:800;font-size:14px;' +
    'display:inline-block">' + label + '</a></div>';
}

function quiet(text) {
  return '<p style="font-size:12.5px;color:#8A7F90;line-height:1.5">' +
    text + '</p>';
}

async function send(key, to, subject, html) {
  if (!key) { console.log("email skipped: no RESEND key"); return false; }
  if (!to) { console.log("email skipped: no recipient"); return false; }
  try {
    const r = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { "Authorization": "Bearer " + key,
                 "Content-Type": "application/json" },
      body: JSON.stringify({
        from: "Lazo <hello@meetlazo.com>",
        to: [to], subject: subject, html: html }),
    });
    if (!r.ok) { console.error("email status", r.status); return false; }
    return true;
  } catch (e) {
    console.error("email failed", e.message);
    return false;
  }
}

module.exports = { shell, h1, button, quiet, send, APP_URL };
