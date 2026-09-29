/**
 * Elizabeth Scott Weddings — Zola inquiry intake + automatic first reply  (JC-ESW-INTAKE-0928)
 * Ported from the Atavia intake (atavia-functions-live/gmail-intake). Zola only: that is the
 * one marketplace this brand advertises on.
 *
 * Runs inside Gmail (Google Apps Script) every 5 minutes. Finds new Zola inquiry
 * notifications, pulls out the couple's details, posts them to the site's
 * inquiry_webhook so they appear in the admin Leads page credited to Zola, then
 * replies on the thread. If the webhook returns an inquiry code, the reply carries it
 * with a booking link that applies it; otherwise the reply goes without one.
 * Synced threads get the label esw-synced. If a thread cannot be parsed or sent it
 * gets esw-needs-review instead; remove that label and it is retried on the next run.
 *
 * Install in the Gmail account that receives Zola's notifications: script.google.com
 * -> New project -> paste this file -> Run `setup` once (approve Gmail access) -> done.
 * `testParse` shows what the parser makes of the latest inquiry and `previewReply` the
 * reply it would send. Neither sends anything.
 */
var WEBHOOK = 'https://us-central1-elizabeth-scott-738e5.cloudfunctions.net/inquiry_webhook';
var LABEL = 'esw-synced';
var BACKFILL_HOURS = 24;          // on first run, inquiries older than this are marked handled without a reply
var ALREADY_ANSWERED = [];        // lowercase couple emails you answered by hand, so the script never doubles up
var REVIEW = 'esw-needs-review';   // parse or send failed: fix, remove this label, and it is retried
var QUERY = 'newer_than:7d from:zola.com';

var SITE = 'https://elizabethscottweddings.com';
var BRAND = 'Elizabeth Scott Weddings';
var STUDIO_NAME = 'Elizabeth Scott';   // what "for <studio>" looks like in Zola's subject lines

function setup() {
  GmailApp.getUserLabelByName(LABEL) || GmailApp.createLabel(LABEL);
  GmailApp.getUserLabelByName(REVIEW) || GmailApp.createLabel(REVIEW);
  ScriptApp.getProjectTriggers().forEach(function (t) { if (t.getHandlerFunction() === 'sync') ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('sync').timeBased().everyMinutes(5).create();
  Logger.log('Labels and 5-minute trigger are in place. First sync runs within 5 minutes.');
}

function sync() {
  var label = GmailApp.getUserLabelByName(LABEL) || GmailApp.createLabel(LABEL);
  var review = GmailApp.getUserLabelByName(REVIEW) || GmailApp.createLabel(REVIEW);
  var seen = PropertiesService.getUserProperties();
  var cutoff = new Date(Date.now() - BACKFILL_HOURS * 3600e3);
  // Zola sends every inquiry notice with the same subject, so Gmail threads them together:
  // walk every message in every thread and remember each one by id.
  GmailApp.search(QUERY, 0, 50).forEach(function (thread) {
    thread.getMessages().forEach(function (msg) {
      var key = 'msg:' + msg.getId();
      if (seen.getProperty(key)) return;
      if (msg.getDate() < cutoff) { seen.setProperty(key, 'old'); return; }          // predates this script: never auto-answer
      var inq = parseInquiry(msg.getSubject(), msg.getPlainBody(), msg.getFrom(), msg.getReplyTo());
      if (!inq) { seen.setProperty(key, 'skip'); return; }                          // newsletter, notice, or our own reply
      if (!inq.email) { thread.addLabel(review); seen.setProperty(key, 'noemail'); Logger.log('needs review (no email found): ' + msg.getSubject()); return; }
      if (seen.getProperty('sent:' + inq.email) || ALREADY_ANSWERED.indexOf(inq.email) > -1) {
        seen.setProperty(key, 'dup'); Logger.log('skipped (already answered): ' + inq.email); return; }
      var auto = (typeof AUTO_REPLY !== 'undefined' && AUTO_REPLY);
      var payload = auto ? Object.assign({ auto_code: true, auto_replied: true }, inq) : inq;
      var res = UrlFetchApp.fetch(WEBHOOK, { method: 'post', contentType: 'application/json',
        payload: JSON.stringify(payload), muteHttpExceptions: true });
      if (res.getResponseCode() < 300) {
        seen.setProperty('sent:' + inq.email, new Date().toISOString()); seen.setProperty(key, 'sent');
        thread.addLabel(label);
        Logger.log('sent: ' + inq.email + ' (' + inq.found_us + ')');
        if (auto) {
          var code = null; try { code = JSON.parse(res.getContentText()).code || null; } catch (e) {}
          try { sendAutoReply(msg, inq, code); } catch (e) { Logger.log('auto-reply failed: ' + e); }
        }
      } else { thread.addLabel(review); Logger.log('needs review, webhook ' + res.getResponseCode() + ': ' + res.getContentText()); }
    });
  });
}

function testParse() {
  var m = latestInquiry();
  if (!m) { Logger.log('no inquiries in the last 7 days (newsletters and notices are ignored)'); return; }
  Logger.log(JSON.stringify(parseInquiry(m.getSubject(), m.getPlainBody(), m.getFrom(), m.getReplyTo()), null, 2));
}

/** The newest message that parses as a real inquiry, or null. */
function latestInquiry() {
  var threads = GmailApp.search(QUERY, 0, 10), best = null;
  threads.forEach(function (t) { t.getMessages().forEach(function (m) {
    if ((!best || m.getDate() > best.getDate()) && parseInquiry(m.getSubject(), m.getPlainBody(), m.getFrom(), m.getReplyTo())) best = m;
  }); });
  return best;
}

/** Lists every inquiry message from the last 7 days and what sync() would do with it. Sends nothing. */
function listInquiries() {
  var seen = PropertiesService.getUserProperties(), cutoff = new Date(Date.now() - BACKFILL_HOURS * 3600e3);
  GmailApp.search(QUERY, 0, 20).forEach(function (t) { t.getMessages().forEach(function (m) {
    var inq = parseInquiry(m.getSubject(), m.getPlainBody(), m.getFrom(), m.getReplyTo());
    if (!inq) return;
    var state = seen.getProperty('msg:' + m.getId()) || (m.getDate() < cutoff ? 'WILL SKIP (older than backfill window)'
              : (seen.getProperty('sent:' + inq.email) || ALREADY_ANSWERED.indexOf(inq.email) > -1) ? 'WILL SKIP (already answered)' : 'WILL REPLY');
    Logger.log(m.getDate() + ' | ' + inq.first_name + ' ' + inq.last_name + ' <' + inq.email + '> | ' + state);
  }); });
}


function dumpBody() {
  var m = GmailApp.search(QUERY, 0, 1)[0].getMessages()[0];
  Logger.log('Reply-To: ' + m.getReplyTo() + '\n' + m.getPlainBody().slice(0, 3000));
}

// ---------------------------------------------------------------- parsing --
function parseInquiry(subject, body, from, replyTo) {
  subject = String(subject || ''); body = String(body || '').replace(/\r/g, ''); from = String(from || ''); replyTo = String(replyTo || '');
  var isZola = /zola\.com/i.test(from);
  if (!isZola) return null;
  // Only real inquiries: Zola also sends newsletters, invitations and account notices.
  var isInquiry = /new (?:message|inquiry|lead) from|new zola inquiry/i.test(subject) || /^Respond to\s+\S/m.test(body) || /sent you an inquiry/i.test(body);
  if (!isInquiry) return null;
  var out = { found_us: 'Zola', referrer: 'https://www.zola.com/', landing_page: 'zola inquiry' };

  // name: "New message from Taylor S & Forrest P for Elizabeth Scott" / "Respond to Taylor S & Forrest P"
  var name = (subject.match(/(?:inquiry|message|lead)\s+from\s+(.+?)(?:\s*[-–|]|$)/i) || [])[1]
          || (subject.match(/^(?:\S+\s)?(.+?)\s+(?:sent you|wants to|is interested|would like)/i) || [])[1]
          || (body.match(/^Respond to\s+(.+?)\s*$/m) || [])[1]
          || (body.match(/^(.+?)\s+sent you an inquiry/im) || [])[1] || '';
  name = name.replace(new RegExp('\\s+for\\s+' + STUDIO_NAME.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '.*$', 'i'), '')
             .replace(/\s+for\s+(?:Elizabeth|Atavia).*$/i, '').replace(/^[^A-Za-z]+/, '').trim();
  var parts = name.split(/\s+/); out.first_name = parts.shift() || ''; out.last_name = parts.join(' ');

  // email: Zola never includes the couple's address; the notification's reply-to relay is the channel that reaches them.
  var any = (body.match(/[^\s@<>"']+@[^\s@<>"']+\.[a-z]{2,}/gi) || []).filter(function (e) {
    return !/zola\.com|elizabethscottweddings\.com|gmail\.com|google\.com/i.test(e); });
  var couple = (body.match(/Couple email:\s*\n?\s*([^\s@]+@[^\s@]+\.[a-z]{2,})/i) || [])[1];
  var replyAddr = (replyTo.match(/[^\s@<>"']+@[^\s@<>"']+\.[a-z]{2,}/i) || [])[0] || '';
  // Only a per-couple relay (msg-…@vmkt-message.zola.com) reaches the couple; Zola's own mailboxes never do.
  if (/zola\.com/i.test(replyAddr) && !/vmkt-message|^msg-/i.test(replyAddr)) replyAddr = '';
  out.email = (couple || any[0] || replyAddr || '').toLowerCase();

  out.phone = (body.match(/(?:phone|tel)[^\d\n(]*(\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})/i) || [])[1] || '';

  // date: "Getting married on October 1, 2027" -> YYYY-MM-DD
  var dateLine = (body.match(/(?:wedding\s*date|event\s*date|desired\s*day)[^\n]*\n?\s*([^\n]+)/i) || [])[1] || body;
  out.wedding_date = isoDate(dateLine) || isoDate(body) || '';

  out.venue = ((body.match(/(?:wedding location|venue|location)[^\n]*:\s*\n?\s*([^\n]+)/i) || [])[1] || '').trim();
  var guests = (body.match(/guest count[^\n]*:\s*\n?\s*([^\n]+)/i) || [])[1];
  var budget = (body.match(/wedding budget of[ \t]*([^\s][^\n]*?)[ \t]*$/im) || [])[1];

  // message: Zola quotes the note under "<name>'s message".
  var note = (body.match(/Their note to you\s*\n+\s*[\u201c"]?\s*([\s\S]*?)\s*[\u201d"]?\s*\n\s*(?:\n|Connect with)/i) || [])[1]
          || (body.match(/'s message\s*\n+\s*"?\s*([\s\S]*?)\s*"?\s*\n\s*(?:\n|-{5,})/i) || [])[1]
          || (body.match(/(?:says|wrote|message):\s*\n?([\s\S]{0,1500}?)(?:\n\s*\n|$)/i) || [])[1] || '';
  note = note.replace(/^\s*(?:\[[^\]]*\]|<?https?:\/\/\S+>?)\s*/g, '');
  note = note.replace(/\s+/g, ' ').trim();
  out.message = (note ? note + '\n' : '') + (guests ? 'Guests: ' + guests.trim() + '\n' : '') + (budget ? 'Budget: ' + budget.trim() + '\n' : '') + '— via Zola: ' + subject.trim();
  out.message = out.message.slice(0, 2000);
  return out;
}

function isoDate(s) {
  s = String(s || '');
  var m = s.match(/\b(\d{1,2})\/(\d{1,2})\/(\d{4})\b/);
  if (m) return m[3] + '-' + pad(m[1]) + '-' + pad(m[2]);
  m = s.match(/\b(\d{4})-(\d{2})-(\d{2})\b/);
  if (m) return m[0];
  var months = { january:1, february:2, march:3, april:4, may:5, june:6, july:7, august:8, september:9, october:10, november:11, december:12,
                 jan:1, feb:2, mar:3, apr:4, jun:6, jul:7, aug:8, sep:9, sept:9, oct:10, nov:11, dec:12 };
  m = s.match(/\b([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b/);
  if (m && months[m[1].toLowerCase()]) return m[3] + '-' + pad(months[m[1].toLowerCase()]) + '-' + pad(m[2]);
  return '';
}
function pad(n) { n = String(n); return n.length < 2 ? '0' + n : n; }

// ---------------------------------------------------- automatic first reply --
// Sent from this Gmail account within five minutes of the inquiry, on the same
// thread, so Zola's relay delivers it to the couple. The webhook
// mints a fresh $200 / 72-hour code for them; if that fails the paragraph is left
// out and the reply still goes. Links read clean in the email; tracking tags sit
// only behind the words in the HTML version. If a file named PRICE_SHEET is in
// this Google account's Drive it is attached. Edit the wording in replyLines() freely.
var AUTO_REPLY = true;
var REPLY_FROM_NAME = BRAND;
var REPLY_SIGNATURE = BRAND + '\nhello@elizabethscottweddings.com · elizabethscottweddings.com';
var CODE_AMOUNT = 200;   // display only; the webhook decides the real amount
var PRICE_SHEET = 'Elizabeth-Scott-Packages-2026.pdf';   // upload this to Google Drive to have it attached; leave missing to skip
var UTM = '?utm_source=SRC&utm_medium=email&utm_campaign=inquiry-reply';

function sendAutoReply(msg, inq, code) {
  if (!AUTO_REPLY) return;
  var text = replyText(inq, code), html = replyHtml(inq, code);
  var opts = { htmlBody: html, name: REPLY_FROM_NAME };
  try {
    var files = DriveApp.getFilesByName(PRICE_SHEET);
    if (files.hasNext()) opts.attachments = [files.next().getAs('application/pdf')];
  } catch (e) { Logger.log('price sheet not attached: ' + e); }
  // A Zola relay address (message threads) must be answered on the thread; a real couple address is answered directly.
  if (/zola\.com/i.test(inq.email)) msg.reply(text, opts);
  else GmailApp.sendEmail(inq.email, replySubject(inq), text, opts);
  Logger.log('auto-replied to ' + inq.email + (code ? ' with ' + code.code : ' (no code)') + (opts.attachments ? ' + price sheet' : ''));
}

function replySubject(inq) {
  return (inq.wedding_date ? 'Your wedding on ' + prettyDate(inq.wedding_date) : 'Your wedding') + ' \u2014 ' + BRAND;
}

// Each paragraph is a string, or an array of strings and {t: visible text, u: url} links.
function replyLines(inq, code) {
  var first = inq.first_name || 'there';
  var when = inq.wedding_date ? prettyDate(inq.wedding_date) : 'your date';
  var where = inq.venue ? ' in ' + inq.venue : '';
  var src = 'zola';
  var tag = UTM.replace('SRC', src);
  var packages = { t: 'elizabethscottweddings.com/packages', u: SITE + '/packages' + tag };
  var book = { t: 'elizabethscottweddings.com/book' + (code ? '/?code=' + code.code : ''), u: SITE + '/book/' + tag + (code ? '&code=' + code.code : '') };
  var out = [
    'Hi ' + first + ',',
    'Congratulations, and thank you for reaching out about your wedding on ' + when + where + '.',
    'We would love to be there. We keep a local team in your area, so there are no travel fees. Reserve with the pay-in-full price, or our standard plan: 50% down at booking and the balance two weeks before your wedding.',
    ['Every collection, with pricing, is here: ', packages, '. Our price sheet is attached as well.']
  ];
  if (code) out.push(['If it feels right, you can reserve the date in about two minutes. Inquiry code ' + code.code + ' takes $' + (code.amount || CODE_AMOUNT) + ' off any collection through ' + prettyDate(code.expires_at) + ', and it is already applied here: ', book]);
  else out.push(['If it feels right, you can reserve the date in about two minutes here: ', book]);
  out.push('Happy to answer anything first. Just reply to this message.');
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
      : p.map(function (x) { return typeof x === 'string' ? esc(x) : '<a href="' + x.u + '" style="color:#B08D57">' + esc(x.t) + '</a>'; }).join('');
    return '<p style="margin:0 0 16px">' + inner + '</p>';
  }).join('');
  return '<div style="font-family:Georgia,serif;font-size:15px;line-height:1.6;color:#1F2A44">' + body + '</div>';
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
  Logger.log(replyText(inq, { code: 'ESW-XXXX-200', amount: 200, expires_at: new Date(Date.now() + 72 * 3600e3).toISOString() })
    + '\n\n[price sheet ' + (sheet ? 'found in Drive, will be attached' : 'NOT in Drive, will not be attached') + ']');
}

/** Confirms Drive access and that the price sheet is where the script expects. Sends nothing. */
function checkDrive() {
  var it = DriveApp.getFilesByName(PRICE_SHEET);
  Logger.log(it.hasNext() ? 'found: ' + it.next().getName() : 'not found by that name');
  var f = DriveApp.getFiles(), n = 0;
  while (f.hasNext() && n < 10) { Logger.log(' - ' + f.next().getName()); n++; }
}
