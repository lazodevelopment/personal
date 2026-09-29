// ---------------------------------------------------- automatic first reply --
// Sent from this Gmail account within five minutes of the inquiry, on the same
// thread, so The Knot's and Zola's relays deliver it to the couple. The webhook
// mints a fresh $200 / 72-hour code for them; if that fails the paragraph is left
// out and the reply still goes. Links read clean in the email; tracking tags sit
// only behind the words in the HTML version. If a file named PRICE_SHEET is in
// this Google account's Drive it is attached. Edit the wording in replyLines() freely.
var AUTO_REPLY = true;
var REPLY_FROM_NAME = 'Atavia Weddings';
var REPLY_SIGNATURE = 'Lauren McKinnon\nAtavia Weddings · (336) 537-9590 · ataviaweddings.com';
var CODE_AMOUNT = 200;   // display only; the webhook decides the real amount
var SITE = 'https://ataviaweddings.com';
var PRICE_SHEET = 'Atavia-Weddings-Packages-2026.pdf';   // upload this to Google Drive to have it attached; leave missing to skip
var UTM = '?utm_source=SRC&utm_medium=email&utm_campaign=inquiry-reply';

function sendAutoReply(msg, inq, code) {
  if (!AUTO_REPLY) return;
  var text = replyText(inq, code), html = replyHtml(inq, code);
  var opts = { htmlBody: html, name: REPLY_FROM_NAME };
  try {
    var files = DriveApp.getFilesByName(PRICE_SHEET);
    if (files.hasNext()) opts.attachments = [files.next().getAs('application/pdf')];
  } catch (e) { Logger.log('price sheet not attached: ' + e); }
  // A marketplace relay address (Zola message threads, The Knot inbox) must be answered on the thread;
  // a real address (Zola's 'New Zola inquiry' notice, a Knot personal email) is answered directly.
  if (/zola\.com|theknot\.com|weddingpro\.com/i.test(inq.email)) msg.reply(text, opts);
  else GmailApp.sendEmail(inq.email, replySubject(inq), text, opts);
  Logger.log('auto-replied to ' + inq.email + (code ? ' with ' + code.code : ' (no code)') + (opts.attachments ? ' + price sheet' : ''));
}

function replySubject(inq) {
  return (inq.wedding_date ? 'Your wedding on ' + prettyDate(inq.wedding_date) : 'Your wedding') + ' \u2014 ' + REPLY_FROM_NAME;
}

// Each paragraph is a string, or an array of strings and {t: visible text, u: url} links.
function replyLines(inq, code) {
  var first = inq.first_name || 'there';
  var when = inq.wedding_date ? prettyDate(inq.wedding_date) : 'your date';
  var where = inq.venue ? ' in ' + inq.venue : '';
  var src = inq.found_us === 'Zola' ? 'zola' : 'theknot';
  var tag = UTM.replace('SRC', src);
  var packages = { t: 'ataviaweddings.com/packages', u: SITE + '/packages' + tag };
  var book = { t: 'ataviaweddings.com/book' + (code ? '/?code=' + code.code : ''), u: SITE + '/book/' + tag + (code ? '&code=' + code.code : '') };
  var out = [
    'Hi ' + first + ',',
    'Congratulations, and thank you for reaching out about your wedding on ' + when + where + '.',
    'We would love to be there. We keep a local team in your area, so there are no travel fees, and a $500 retainer is all it takes to hold ' + when + ' on our calendar.',
    ['Every collection, with pricing, is here: ', packages, '. Our price sheet is attached as well.']
  ];
  if (code) out.push(['If it feels right, you can reserve the date in about two minutes. Code ' + code.code + ' takes $' + (code.amount || CODE_AMOUNT) + ' off any collection through ' + prettyDate(code.expires_at) + ', and it is already applied here: ', book]);
  else out.push(['If it feels right, you can reserve the date in about two minutes here: ', book]);
  out.push('Happy to answer anything first. Just reply to this message or text (336) 537-9590.');
  out.push(REPLY_SIGNATURE);
  return out;
}

function replyText(inq, code) {
  return replyLines(inq, code).map(function (p) {
    return typeof p === 'string' ? p : p.map(function (x) { return typeof x === 'string' ? x : x.t; }).join('');
  }).join('\n\n');
}

function replyHtml(inq, code) {
  var esc = function (s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/\n/g, '<br>'); };
  var body = replyLines(inq, code).map(function (p) {
    var inner = typeof p === 'string' ? esc(p)
      : p.map(function (x) { return typeof x === 'string' ? esc(x) : '<a href="' + x.u + '" style="color:#B0713F">' + esc(x.t) + '</a>'; }).join('');
    return '<p style="margin:0 0 16px">' + inner + '</p>';
  }).join('');
  return '<div style="font-family:Georgia,serif;font-size:15px;line-height:1.6;color:#2B2B2B">' + body + '</div>';
}

function prettyDate(iso) {
  var d = new Date(String(iso).slice(0, 10) + 'T12:00:00');
  if (isNaN(d)) return String(iso);
  return ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'][d.getMonth()]
    + ' ' + d.getDate() + ', ' + d.getFullYear();
}

/** Preview the reply for the newest inquiry in the log. Sends nothing. */
function previewReply() {
  var m = latestInquiry();
  if (!m) { Logger.log('no inquiries in the last 7 days (newsletters and notices are ignored)'); return; }
  var inq = parseInquiry(m.getSubject(), m.getPlainBody(), m.getFrom(), m.getReplyTo());
  var sheet = false; try { sheet = DriveApp.getFilesByName(PRICE_SHEET).hasNext(); } catch (e) {}
  Logger.log(replyText(inq, { code: 'ATAVIA-XXXX-200', amount: 200, expires_at: new Date(Date.now() + 72 * 3600e3).toISOString() })
    + '\n\n[price sheet ' + (sheet ? 'found in Drive, will be attached' : 'NOT in Drive, will not be attached') + ']');
}

/** Confirms Drive access and that the price sheet is where the script expects. Sends nothing. */
function checkDrive() {
  var it = DriveApp.getFilesByName(PRICE_SHEET);
  Logger.log(it.hasNext() ? 'found: ' + it.next().getName() : 'not found by that name');
  var f = DriveApp.getFiles(), n = 0;
  while (f.hasNext() && n < 10) { Logger.log(' - ' + f.next().getName()); n++; }
}
