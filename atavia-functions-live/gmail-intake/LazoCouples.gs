/**
 * Lazo couples capture (JC-LAZO-COUPLES-1019)
 *
 * Add this as a THIRD FILE (LazoCouples.gs) in each intake project, next to the intake script and FollowUps.gs:
 *   'Zola Intake' in ataviaweddings@gmail.com, 'Atavia' in info@ataviaweddings.com,
 *   'Elizabeth Scott' in hello@elizabethscottweddings.com.
 * Then add ONE line to the intake script's handleMessage(), right after the webhook POST succeeds
 * (where tellHub(...) is called):
 *     tellLazo(inq, msg);
 * and paste the key from the Lazo Secret Manager secret COUPLE_INTAKE_KEY into LAZO_KEY below (never commit it).
 *
 * What it does: every NEW Zola / Knot inquiry the intake script parses is also POSTed to Lazo's coupleIntake
 * function, which stores the couple in coupleOutreach (admin-only) and, after a hold of a few days so this
 * studio's own replies and follow-ups go first, adds them to the "plan on Lazo" couples email campaign.
 * Relay addresses (msg-...@vmkt-message.zola.com, @member.theknot.com) are recorded but never mailed.
 * Fails silently: a Lazo outage never affects the auto-reply.
 *
 * exportInquiries(): one-off backfill. Scans this mailbox's whole Zola / Knot history (no date limit), parses
 * every inquiry notice with the intake script's own parseInquiry(), and writes a CSV to this account's Drive
 * ("lazo-couples-<brand>-<date>.csv": names, email, wedding_date, venue, marketplace, inquired_at, relay).
 * Run it once from the Apps Script editor; share the file with Jesse's Lazo session to load the history.
 */
var LAZO_INTAKE = 'https://us-central1-lazo-513ec.cloudfunctions.net/coupleIntake';
var LAZO_KEY = '';   // COUPLE_INTAKE_KEY
var LAZO_BRAND = '';  // '' = from WEBHOOK (atavia / es)

function lazoBrand() {
  return LAZO_BRAND || (/atavia/i.test(String(typeof WEBHOOK === 'undefined' ? '' : WEBHOOK)) ? 'atavia' : 'es');
}

function tellLazo(inq, msg) {
  if (!LAZO_KEY || !inq || !inq.email) return;
  try {
    var body = { brand: lazoBrand(), marketplace: inq.found_us || '', names: ((inq.first_name || '') + ' ' + (inq.last_name || '')).trim(),
                 email: inq.email, wedding_date: inq.wedding_date || '', venue: inq.venue || '',
                 inquired_at: msg ? Utilities.formatDate(msg.getDate(), 'UTC', 'yyyy-MM-dd') : '' };
    UrlFetchApp.fetch(LAZO_INTAKE, { method: 'post', contentType: 'application/json', headers: { 'x-lazo-key': LAZO_KEY },
                                     payload: JSON.stringify(body), muteHttpExceptions: true });
  } catch (e) { Logger.log('tellLazo failed (ignored): ' + e); }
}

function testLazo() {
  var r = UrlFetchApp.fetch(LAZO_INTAKE, { method: 'post', contentType: 'application/json', headers: { 'x-lazo-key': LAZO_KEY },
    payload: JSON.stringify({ brand: lazoBrand(), marketplace: 'Zola', names: 'Test Couple & Lazo Test', email: 'msg-test@vmkt-message.zola.com',
                              wedding_date: '2099-01-01', venue: 'Phoenix, AZ', inquired_at: '2026-10-19' }), muteHttpExceptions: true });
  Logger.log(r.getResponseCode() + ' ' + r.getContentText());   // expect 200 {"ok":true,...,"relay":true}
}

function exportInquiries() {
  var q = 'in:anywhere (from:zola.com OR from:theknot.com OR from:member.theknot.com OR from:weddingpro.com)';   // in:anywhere = Inbox + Archive + Trash + Spam (Jesse deleted some notices)
  var rows = [['names', 'email', 'wedding_date', 'venue', 'marketplace', 'inquired_at', 'relay', 'subject']];
  var seen = {};
  var start = 0, batch;
  do {
    batch = GmailApp.search(q, start, 100);
    batch.forEach(function (t) {
      t.getMessages().forEach(function (m) {
        var inq;
        try { inq = parseInquiry(m.getSubject(), m.getPlainBody(), m.getFrom(), m.getReplyTo()); } catch (e) { inq = null; }
        if (!inq) return;
        var key = (inq.email || '') + '|' + (inq.first_name || '') + '|' + (inq.last_name || '') + '|' + m.getId();
        if (seen[key]) return; seen[key] = 1;
        var relay = /vmkt-message\.zola\.com|@zola\.com|theknot\.com|weddingpro\.com/i.test(inq.email || '') || !inq.email;
        rows.push([((inq.first_name || '') + ' ' + (inq.last_name || '')).trim(), inq.email || '', inq.wedding_date || '', inq.venue || '',
                   inq.found_us || '', Utilities.formatDate(m.getDate(), 'UTC', 'yyyy-MM-dd'), relay ? '1' : '0', m.getSubject()]);
      });
    });
    start += 100;
  } while (batch.length === 100);
  var csv = rows.map(function (r) { return r.map(function (c) { return '"' + String(c).replace(/"/g, '""') + '"'; }).join(','); }).join('\n');
  var name = 'lazo-couples-' + lazoBrand() + '-' + Utilities.formatDate(new Date(), 'UTC', 'yyyyMMdd') + '.csv';
  var f = DriveApp.createFile(name, csv, 'text/csv');
  Logger.log((rows.length - 1) + ' inquiries -> ' + f.getUrl());
}
