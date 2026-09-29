/**
 * Atavia Weddings — marketplace inquiry intake  (JC-ATV-INTAKE-0928)
 *
 * Runs inside Gmail (Google Apps Script) every 5 minutes. Finds new inquiry
 * notifications from The Knot / WeddingPro and Zola, pulls out the couple's
 * details, and posts them to the site's inquiry_webhook so they appear in the
 * admin Leads page credited to the platform. Each thread is labelled once it is
 * synced, and each couple's email is remembered, so nothing is sent twice.
 *
 * Install once per inbox (info@ataviaweddings.com for The Knot,
 * ataviaweddings@gmail.com for Zola): script.google.com -> New project -> paste
 * this file -> Run `setup` once (approve Gmail access) -> done. `setup` creates
 * the label and the 5-minute trigger. Run `testParse` to see what the parser
 * makes of the latest inquiry without sending anything.
 */
var WEBHOOK = 'https://us-central1-atavia-c29cd.cloudfunctions.net/inquiry_webhook';
var LABEL = 'atavia-synced';
var BACKFILL_HOURS = 24;          // on first run, inquiries older than this are marked handled without a reply
var ALREADY_ANSWERED = [];        // lowercase couple emails you answered by hand, so the script never doubles up
var REVIEW = 'atavia-needs-review';   // parse or send failed: fix, remove this label, and it is retried
var QUERY = 'newer_than:7d (from:member.theknot.com OR from:theknot.com OR from:weddingpro.com OR from:zola.com)';

function setup() {
  GmailApp.getUserLabelByName(LABEL) || GmailApp.createLabel(LABEL);
  GmailApp.getUserLabelByName(REVIEW) || GmailApp.createLabel(REVIEW);
  ScriptApp.getProjectTriggers().forEach(function (t) { if (t.getHandlerFunction() === 'sync') ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('sync').timeBased().everyMinutes(5).create();
  Logger.log('Label and 5-minute trigger are in place. First sync runs within 5 minutes.');
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

  // name: "Celia Murphy sent you a new message" / "Celia Murphy wants to learn more" / "New inquiry from Celia Murphy"
  var name = (subject.match(/^(?:\S+\s)?(.+?)\s+(?:sent you|wants to|is interested|would like)/i) || [])[1]
          || (subject.match(/(?:inquiry|message|lead)\s+from\s+(.+?)(?:\s*[-–|]|$)/i) || [])[1]
          || (body.match(/^(.+?)\s+wants to learn more/m) || [])[1]
          || (body.match(/^Respond to\s+(.+?)\s*$/m) || [])[1]
          || (body.match(/^(.+?)\s+sent you an inquiry/im) || [])[1] || '';
  name = name.replace(/\s+for\s+Atavia\s+Weddings.*$/i, '').replace(/^[^A-Za-z]+/, '').trim();
  var parts = name.split(/\s+/); out.first_name = parts.shift() || ''; out.last_name = parts.join(' ');

  // email: The Knot gives "Personal email:" and a relay inbox; Zola gives the couple's address. Never the platform's own.
  var personal = (body.match(/(?:Personal email|Couple email):\s*\n?\s*([^\s@]+@[^\s@]+\.[a-z]{2,})/i) || [])[1];
  var relay = (body.match(/The Knot inbox:\s*\n?\s*([^\s@]+@[^\s@]+\.[a-z]{2,})/i) || [])[1];
  var any = (body.match(/[^\s@<>"']+@[^\s@<>"']+\.[a-z]{2,}/gi) || []).filter(function (e) {
    return !/theknot\.com|weddingpro\.com|zola\.com|ataviaweddings\.com|google\.com/i.test(e); });
  // Zola never includes the couple's address: the notification's reply-to is the channel that reaches them.
  var replyAddr = (replyTo.match(/[^\s@<>"']+@[^\s@<>"']+\.[a-z]{2,}/i) || [])[0] || '';
  if (/ataviaweddings\.com|gmail\.com/i.test(replyAddr) && !isZola) replyAddr = '';
  // Only a per-couple relay (msg-…@vmkt-message.zola.com) reaches the couple; Zola's own mailboxes never do.
  if (/zola\.com/i.test(replyAddr) && !/vmkt-message|^msg-/i.test(replyAddr)) replyAddr = '';
  out.email = (personal || any[0] || (isZola && replyAddr) || relay || replyAddr || '').toLowerCase();

  out.phone = (body.match(/(?:phone|tel)[^\d\n(]*(\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})/i) || [])[1] || '';

  // date: "Wedding date:\nFri 6/4/2027" or "June 4, 2027" or "6/4/2027" anywhere -> YYYY-MM-DD
  var dateLine = (body.match(/(?:wedding\s*date|event\s*date|desired\s*day)[^\n]*\n?\s*([^\n]+)/i) || [])[1] || body;
  out.wedding_date = isoDate(dateLine) || isoDate(body) || '';

  out.venue = ((body.match(/(?:wedding location|venue|location)[^\n]*:\s*\n?\s*([^\n]+)/i) || [])[1] || '').trim();
  var guests = (body.match(/guest count[^\n]*:\s*\n?\s*([^\n]+)/i) || [])[1];
  var budget = (body.match(/wedding budget of[ \t]*([^\s][^\n]*?)[ \t]*$/im) || [])[1];

  // message: The Knot puts the couple's note between the headline and "For: Atavia Weddings"; otherwise keep the body head.
  var note = (body.match(/^From:\s*[^\n]*?:\s*\n([\s\S]*?)\n\s*(?:\n|By replying)/im) || [])[1]
          || (body.match(/Their note to you\s*\n+\s*[\u201c"]?\s*([\s\S]*?)\s*[\u201d"]?\s*\n\s*(?:\n|Connect with)/i) || [])[1]
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
