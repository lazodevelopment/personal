/**
 * Elizabeth Scott: answer inquiries the intake script skipped  (JC-FOLLOWUP-1009)
 *
 * Second file in the 'Elizabeth Scott' project (hello@). Put the couples' emails in
 * MISSED_LIST and run replyMissedList once. For each one it finds their Zola notice in the
 * last 7 days and does exactly what sync() does: posts the lead to the site (fresh code),
 * sends the normal first reply, remembers the address (which also starts their follow-ups)
 * and tells JARVIS. It refuses any couple that already has a message from us in Sent.
 */
var MISSED_LIST = [];

function replyMissedList() {
  var label = GmailApp.getUserLabelByName(LABEL) || GmailApp.createLabel(LABEL);
  var review = GmailApp.getUserLabelByName(REVIEW) || GmailApp.createLabel(REVIEW);
  var seen = PropertiesService.getUserProperties();
  MISSED_LIST.forEach(function (raw) {
    var email = String(raw || '').trim().toLowerCase();
    if (!email) return;
    if (GmailApp.search('in:sent to:' + email, 0, 1).length) { Logger.log(email + ': already in Sent, nothing sent'); return; }
    var hit = null;
    GmailApp.search(QUERY, 0, 50).forEach(function (thread) {
      thread.getMessages().forEach(function (msg) {
        var inq = parseInquiry(msg.getSubject(), msg.getPlainBody(), msg.getFrom(), msg.getReplyTo());
        if (inq && inq.email === email && (!hit || msg.getDate() > hit.msg.getDate())) hit = { thread: thread, msg: msg, inq: inq };
      });
    });
    if (!hit) { Logger.log(email + ': no inquiry notice in the last 7 days'); return; }
    var res = UrlFetchApp.fetch(WEBHOOK, { method: 'post', contentType: 'application/json',
      payload: JSON.stringify(Object.assign({ auto_code: true, auto_replied: true }, hit.inq)), muteHttpExceptions: true });
    if (res.getResponseCode() >= 300) { Logger.log(email + ': site said ' + res.getResponseCode() + ', nothing sent'); return; }
    var code = null; try { code = JSON.parse(res.getContentText()).code || null; } catch (e) {}
    try {
      var how = sendAutoReply(hit.msg, hit.inq, code);
      seen.setProperty('sent:' + email, new Date().toISOString()); seen.setProperty('msg:' + hit.msg.getId(), 'sent');
      hit.thread.addLabel(label);
      tellHub(hit.thread, hit.msg, hit.inq, 'replied', 'replyMissedList: ' + how);
      Logger.log(email + ': replied ' + how);
    } catch (e) {
      hit.thread.addLabel(review); tellHub(hit.thread, hit.msg, hit.inq, 'reply_failed', String(e));
      Logger.log(email + ': reply FAILED ' + e);
    }
  });
}
