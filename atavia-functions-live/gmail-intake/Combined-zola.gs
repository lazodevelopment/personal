/**
 * Atavia Weddings — marketplace inquiry intake + automatic first reply  (JC-ATV-INTAKE-0928 / JC-ATV-AUTOREPLY-0928)
 *
 * Runs inside Gmail (Google Apps Script) every 5 minutes. Finds new inquiry
 * notifications from The Knot / WeddingPro and Zola, pulls out the couple's
 * details, posts them to the site's inquiry_webhook so they appear in the admin
 * Leads page credited to the platform, then replies with a fresh $200 / 72-hour
 * code. Zola sends every inquiry notice with the same subject, so Gmail threads
 * them together: the script walks every message in every thread and remembers
 * each one it has handled by id. Threads touched get the label atavia-synced; a
 * message that cannot be parsed gets atavia-needs-review on its thread.
 * Newsletters, invitations and account notices from the platforms are ignored.
 *
 * Run `setup` once per inbox (approve Gmail access). `listInquiries` shows every
 * inquiry from the last week and what the script did or will do with it;
 * `previewReply` shows the reply it would send; `checkDrive` confirms the price
 * sheet. None of them send anything. `replyMissed` (with MISSED set) answers one inquiry the
 * script skipped, and is the only helper that sends.
 */
var WEBHOOK = 'https://us-central1-atavia-c29cd.cloudfunctions.net/inquiry_webhook';
var LABEL = 'atavia-synced';
var BACKFILL_HOURS = 24;          // on first run, inquiries older than this are marked handled without a reply
var ALREADY_ANSWERED = [];        // lowercase couple emails you answered by hand, so the script never doubles up
var REVIEW = 'atavia-needs-review';   // parse failed: fix, and it is retried on the next run
// ZOLA COPY for ataviaweddings@gmail.com. The Knot / WeddingPro is handled by the copy in info@ataviaweddings.com.
// Only Zola's first-contact notice ('New Zola inquiry for Atavia Weddings', which carries the couple's own email)
// is answered here; follow-up 'New message from…' emails are conversations, never a first reply.
var QUERY = 'newer_than:7d from:zola.com subject:"New Zola inquiry"';

// JARVIS: after every inquiry the script tells the hub what it did (replied, duplicate, failed…), so JARVIS can
// confirm each lead got its first reply, and shout when one did not, instead of guessing from labels.
// HUB_KEY is the access key in C:\Users\kurvh\jarvis-hub\.hub-key (same value the Gmail bridge scripts use).
// Leave it blank to skip reporting; a hub outage never blocks a reply.
var HUB = 'https://jarvis-hub.floral-credit-e4f0.workers.dev';
var HUB_KEY = '';
var HUB_BUSINESS = 'atavia';

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
    thread.getMessages().forEach(function (msg) { handleMessage(thread, msg, label, review, seen, cutoff, false); });
  });
}

/**
 * One inquiry notice: parse, post to the site, reply, remember. `force` ignores the
 * seen-store and the backfill cutoff (used by replyMissed for a notice the script skipped).
 */
function handleMessage(thread, msg, label, review, seen, cutoff, force) {
  var key = 'msg:' + msg.getId();
  if (!force && seen.getProperty(key)) return;
  if (!force && msg.getDate() < cutoff) { seen.setProperty(key, 'old'); Logger.log('skipped (older than backfill window): ' + msg.getDate()); return; }   // predates this script: never auto-answer
  var inq = parseInquiry(msg.getSubject(), msg.getPlainBody(), msg.getFrom(), msg.getReplyTo());
  if (!inq) { seen.setProperty(key, 'skip'); return; }                          // newsletter, notice, or our own reply
  if (!inq.email) { thread.addLabel(review); seen.setProperty(key, 'noemail'); Logger.log('needs review (no email found): ' + msg.getSubject()); tellHub(thread, msg, inq, 'no_email', 'could not find the couple\'s email in the notice'); return; }
  if (!force && (seen.getProperty('sent:' + inq.email) || ALREADY_ANSWERED.indexOf(inq.email) > -1)) {
    seen.setProperty(key, 'dup'); Logger.log('skipped (already answered): ' + inq.email); tellHub(thread, msg, inq, 'duplicate', 'already answered ' + inq.email); return; }
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
      try {
        var how = sendAutoReply(msg, inq, code);
        tellHub(thread, msg, inq, 'replied', how);
      } catch (e) {
        // the lead is on the site but the couple heard nothing: flag the thread and tell JARVIS right away
        Logger.log('auto-reply failed: ' + e); thread.addLabel(review); tellHub(thread, msg, inq, 'reply_failed', String(e));
      }
    } else tellHub(thread, msg, inq, 'manual', 'AUTO_REPLY is off');
  } else { thread.addLabel(review); Logger.log('needs review, webhook ' + res.getResponseCode() + ': ' + res.getContentText()); tellHub(thread, msg, inq, 'webhook_failed', 'webhook ' + res.getResponseCode() + ': ' + res.getContentText().slice(0, 160)); }
}

/**
 * Answers one inquiry the script skipped (older than the backfill window, or marked handled by mistake).
 * Set MISSED to the couple's email, run it once, and check Sent. It posts the lead to the site and
 * sends the normal first reply exactly as sync() would, then remembers the address so nothing doubles up.
 */
var MISSED = '';
function replyMissed() {
  var email = String(MISSED || '').trim().toLowerCase();
  if (!email) { Logger.log('set MISSED to the couple\'s email first'); return; }
  var label = GmailApp.getUserLabelByName(LABEL) || GmailApp.createLabel(LABEL);
  var review = GmailApp.getUserLabelByName(REVIEW) || GmailApp.createLabel(REVIEW);
  var seen = PropertiesService.getUserProperties(), done = false;
  if (GmailApp.search('in:sent to:' + email, 0, 1).length) { Logger.log('already in Sent: a message to ' + email + ' exists; nothing sent'); return; }
  GmailApp.search(QUERY, 0, 50).forEach(function (thread) { thread.getMessages().forEach(function (msg) {
    if (done) return;
    var inq = parseInquiry(msg.getSubject(), msg.getPlainBody(), msg.getFrom(), msg.getReplyTo());
    if (inq && inq.email === email) { done = true; handleMessage(thread, msg, label, review, seen, new Date(0), true); }
  }); });
  Logger.log(done ? 'done; check Sent for ' + email : 'no inquiry notice for ' + email + ' in the last 7 days');
}

/** Tells the JARVIS hub what happened to one inquiry. Never throws; does nothing without HUB_KEY. */
function tellHub(thread, msg, inq, state, detail) {
  if (!HUB_KEY) return;
  try {
    var payload = { business: HUB_BUSINESS, account: Session.getEffectiveUser().getEmail(), threadId: thread.getId(), messageId: msg.getId(),
      date: msg.getDate().toISOString(), subject: msg.getSubject(), state: state, detail: String(detail || '').slice(0, 300),
      source: inq ? inq.found_us : '', couple: inq ? inq.email : '', name: inq ? (inq.first_name + ' ' + inq.last_name).trim() : '', wedding_date: inq ? inq.wedding_date : '' };
    var r = UrlFetchApp.fetch(HUB + '/api/intake', { method: 'post', contentType: 'application/json', headers: { 'x-hub-key': HUB_KEY },
      payload: JSON.stringify(payload), muteHttpExceptions: true });
    if (r.getResponseCode() >= 300) Logger.log('hub not told (' + r.getResponseCode() + '): ' + r.getContentText().slice(0, 120));
  } catch (e) { Logger.log('hub not told: ' + e); }
}

/** Sends a test report to the hub so you can see it land (JARVIS Inbox → ask "did the intake script reply?"). */
function testHub() {
  if (!HUB_KEY) { Logger.log('fill HUB_KEY first'); return; }
  var m = latestInquiry(); if (!m) { Logger.log('no inquiry in the last 7 days to report'); return; }
  var inq = parseInquiry(m.getSubject(), m.getPlainBody(), m.getFrom(), m.getReplyTo());
  tellHub(m.getThread(), m, inq, 'replied', 'test from testHub()'); Logger.log('reported ' + (inq && inq.email) + ' to the hub as replied');
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
  var m = latestInquiry() || GmailApp.search(QUERY, 0, 1)[0].getMessages()[0];
  Logger.log('Subject: ' + m.getSubject() + '\nReply-To: ' + m.getReplyTo() + '\n' + m.getPlainBody().slice(0, 3000));
}

// ---------------------------------------------------------------- parsing --
function parseInquiry(subject, body, from, replyTo) {
  subject = String(subject || ''); body = String(body || '').replace(/\r/g, ''); from = String(from || ''); replyTo = String(replyTo || '');
  var isKnot = /theknot\.com|weddingpro\.com/i.test(from), isZola = /zola\.com/i.test(from);
  if (!isKnot && !isZola) return null;
  // Only real inquiries: the platforms also send newsletters, invitations and account notices.
  var isInquiry = /sent you a new message|wants to learn more|new (?:message|inquiry|lead) from|new lead|new zola inquiry/i.test(subject)
               || /^Respond to\s+\S/m.test(body) || /^New Lead for /m.test(body) || /Personal email:/i.test(body) || /sent you an inquiry/i.test(body);
  if (!isInquiry) return null;
  var out = { found_us: isKnot ? 'The Knot' : 'Zola', referrer: isKnot ? 'https://www.theknot.com/' : 'https://www.zola.com/',
              landing_page: isKnot ? 'theknot inquiry' : 'zola inquiry' };

  // name: "Celia Murphy sent you a new message" / "New message from Taylor S & Forrest P for Atavia Weddings" / "Claire Olson & Ryan Osterberg sent you an inquiry!"
  var name = (subject.match(/^(?:\S+\s)?(.+?)\s+(?:sent you|wants to|is interested|would like)/i) || [])[1]
          || (subject.match(/(?:inquiry|message|lead)\s+from\s+(.+?)(?:\s*[-–|]|$)/i) || [])[1]
          || (body.match(/^(.+?)\s+wants to learn more/m) || [])[1]
          || (body.match(/^Respond to\s+(.+?)\s*$/m) || [])[1]
          || (body.match(/^(.+?)\s+sent you an inquiry/im) || [])[1] || '';
  name = name.replace(/\s+for\s+Atavia\s+Weddings.*$/i, '').replace(/^[^A-Za-z]+/, '').trim();
  var parts = name.split(/\s+/); out.first_name = parts.shift() || ''; out.last_name = parts.join(' ');

  // email: The Knot gives "Personal email:", Zola's inquiry notice gives "Couple email:"; message threads only give a relay.
  var personal = (body.match(/(?:Personal email|Couple email):\s*\n?\s*([^\s@]+@[^\s@]+\.[a-z]{2,})/i) || [])[1];
  var relay = (body.match(/The Knot inbox:\s*\n?\s*([^\s@]+@[^\s@]+\.[a-z]{2,})/i) || [])[1];
  var any = (body.match(/[^\s@<>"']+@[^\s@<>"']+\.[a-z]{2,}/gi) || []).filter(function (e) {
    return !/theknot\.com|weddingpro\.com|zola\.com|ataviaweddings\.com|google\.com/i.test(e); });
  var replyAddr = (replyTo.match(/[^\s@<>"']+@[^\s@<>"']+\.[a-z]{2,}/i) || [])[0] || '';
  if (/ataviaweddings\.com|gmail\.com/i.test(replyAddr) && !isZola) replyAddr = '';
  // Only a per-couple relay (msg-…@vmkt-message.zola.com) reaches the couple; Zola's own mailboxes never do.
  if (/zola\.com/i.test(replyAddr) && !/vmkt-message|^msg-/i.test(replyAddr)) replyAddr = '';
  out.email = (personal || any[0] || (isZola && replyAddr) || relay || replyAddr || '').toLowerCase();

  out.phone = (body.match(/(?:phone|tel)[^\d\n(]*(\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})/i) || [])[1] || '';

  // date: "Wedding Date: Fri 6/4/2027", "Getting married on October 1, 2027", "Desired day: August 21, 2027" -> YYYY-MM-DD
  var dateLine = (body.match(/(?:wedding\s*date|event\s*date|desired\s*day)[^\n]*\n?\s*([^\n]+)/i) || [])[1] || body;
  out.wedding_date = isoDate(dateLine) || isoDate(body) || '';

  out.venue = ((body.match(/(?:wedding location|venue|location)[^\n]*:\s*\n?\s*([^\n]+)/i) || [])[1] || '').trim();
  var guests = (body.match(/guest count[^\n]*:\s*\n?\s*([^\n]+)/i) || [])[1];
  var budget = (body.match(/wedding budget of[ \t]*([^\s][^\n]*?)[ \t]*$/im) || [])[1];

  // message: The Knot puts the note under "From: <name>:"; Zola under "Their note to you" or "<name>'s message".
  var note = (body.match(/^From:\s*[^\n]*?:\s*\n([\s\S]*?)\n\s*(?:\n|By replying)/im) || [])[1]
          || (body.match(/Their note to you\s*\n+\s*[“"]?\s*([\s\S]*?)\s*[”"]?\s*\n\s*(?:\n|Connect with)/i) || [])[1]
          || (body.match(/'s message\s*\n+\s*"?\s*([\s\S]*?)\s*"?\s*\n\s*(?:\n|-{5,})/i) || [])[1]
          || (body.match(/(?:learn more about your offerings!?|says:|sent you a new message)\s*([\s\S]*?)\s*(?:For:\s*Atavia|By replying|Reply directly|view on WeddingPro)/i) || [])[1]
          || (body.match(/(?:says|wrote|message):\s*\n?([\s\S]{0,1500}?)(?:\n\s*\n|$)/i) || [])[1] || '';
  note = note.replace(/^\s*(?:\[[^\]]*\]|<?https?:\/\/\S+>?)\s*/g, '');   // drop a leading link or image placeholder
  note = note.replace(/\s+/g, ' ').trim();
  out.message = (note ? note + '\n' : '') + (guests ? 'Guests: ' + guests.trim() + '\n' : '') + (budget ? 'Budget: ' + budget.trim() + '\n' : '') + '— via ' + out.found_us + ': ' + subject.trim();
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
// Sent from this Gmail account within five minutes of the inquiry. A Zola message
// thread or Knot relay is answered on the thread so the platform delivers it; a real
// couple address (Zola's inquiry notice) is answered directly. The webhook mints a
// fresh $200 / 72-hour code; if that fails the paragraph is left out and the reply
// still goes. Links read clean; tracking tags sit only behind the words in the HTML
// version. If a file named PRICE_SHEET is in this account's Drive it is attached.
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
  var how = 'to ' + inq.email + (code ? ' with ' + code.code : ' (no code)') + (opts.attachments ? ' + price sheet' : '');
  Logger.log('auto-replied ' + how);
  return how;
}

function replySubject(inq) {
  return (inq.wedding_date ? 'Your wedding on ' + prettyDate(inq.wedding_date) : 'Your wedding') + ' — ' + REPLY_FROM_NAME;
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
  Logger.log('To: ' + inq.email + '\nSubject: ' + replySubject(inq) + '\n\n' + replyText(inq, { code: 'ATAVIA-XXXX-200', amount: 200, expires_at: new Date(Date.now() + 72 * 3600e3).toISOString() })
    + '\n\n[price sheet ' + (sheet ? 'found in Drive, will be attached' : 'NOT in Drive, will not be attached') + ']');
}

/** Confirms Drive access and that the price sheet is where the script expects. Sends nothing. */
function checkDrive() {
  var it = DriveApp.getFilesByName(PRICE_SHEET);
  Logger.log(it.hasNext() ? 'found: ' + it.next().getName() : 'not found by that name');
  var f = DriveApp.getFiles(), n = 0;
  while (f.hasNext() && n < 10) { Logger.log(' - ' + f.next().getName()); n++; }
}
