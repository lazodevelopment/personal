/**
 * JARVIS Gmail bridge — paste this into a Google Apps Script project inside the Gmail account
 * you want JARVIS to watch (script.google.com → New project → replace the code → fill the 4 lines below).
 *
 * It runs on Google's servers every 5 minutes, independent of your PC:
 *   sync()   sends the inbox (last 2 days, up to 40 threads) to the hub
 *   doPost() lets the hub archive, mark read, or send a reply you confirmed on the hub
 *
 * Setup (once per account):
 *   1. Fill HUB_KEY (from C:\Users\kurvh\jarvis-hub\.hub-key), BUSINESS, and a long random SECRET.
 *   2. Run the function `setup` once (toolbar ▶). Approve the permissions when Google asks.
 *   3. Deploy → New deployment → type "Web app" → Execute as: Me → Who has access: Anyone → Deploy.
 *   4. Run `setup` once more so the hub learns the web-app URL. Done: the Inbox panel fills within 5 minutes.
 */
const HUB = "https://jarvis-hub.floral-credit-e4f0.workers.dev";
const HUB_KEY = "PASTE_HUB_KEY_HERE";
const BUSINESS = "es";          // atavia | es | lazo | roven | lr | brisk | other
const SECRET = "PASTE_A_LONG_RANDOM_SECRET_HERE";

function setup() {
  ScriptApp.getProjectTriggers().forEach(function (t) { ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger("sync").timeBased().everyMinutes(5).create();
  sync();
}

function me_() {
  var mine = [Session.getEffectiveUser().getEmail()].concat(GmailApp.getAliases()).map(function (a) { return String(a).toLowerCase(); });
  return mine.filter(Boolean);
}

function sync() {
  var mine = me_();
  var threads = GmailApp.search("in:inbox newer_than:2d", 0, 40);
  var items = threads.map(function (t) {
    var msgs = t.getMessages(); var last = msgs[msgs.length - 1];
    var from = last.getFrom() || "";
    var fromEmail = (from.match(/<([^>]+)>/) || [null, from])[1].toLowerCase();
    var body = "";
    try { body = (last.getPlainBody() || "").replace(/\s+/g, " ").trim().slice(0, 400); } catch (e) {}
    return {
      threadId: t.getId(), subject: t.getFirstMessageSubject() || "(no subject)", from: from, fromEmail: fromEmail,
      date: last.getDate().toISOString(), snippet: body, unread: t.isUnread(), count: msgs.length,
      lastFromMe: mine.indexOf(fromEmail) >= 0, starred: t.hasStarredMessages(), important: t.isImportant(),
      labels: t.getLabels().map(function (l) { return l.getName(); }),
      link: "https://mail.google.com/mail/u/0/#all/" + t.getId()
    };
  });
  var hookUrl = ""; try { hookUrl = ScriptApp.getService().getUrl() || ""; } catch (e) {}
  var payload = { account: mine[0], business: BUSINESS, hookUrl: hookUrl, secret: SECRET, items: items, at: new Date().toISOString() };
  var r = UrlFetchApp.fetch(HUB + "/api/inbox", { method: "post", contentType: "application/json", headers: { "x-hub-key": HUB_KEY }, payload: JSON.stringify(payload), muteHttpExceptions: true });
  Logger.log(r.getResponseCode() + " " + r.getContentText().slice(0, 200));
}

function doPost(e) {
  var body = {};
  try { body = JSON.parse(e.postData.contents); } catch (err) { return out_({ error: "bad json" }); }
  if (body.secret !== SECRET) return out_({ error: "bad secret" });
  try {
    if (body.action === "send") { GmailApp.sendEmail(body.to, body.subject, body.body, { htmlBody: String(body.body).replace(/\n/g, "<br>") }); sync(); return out_({ ok: true, did: "sent to " + body.to }); }
    var t = GmailApp.getThreadById(body.threadId);
    if (!t) return out_({ error: "thread not found" });
    if (body.action === "archive") { t.markRead(); t.moveToArchive(); }
    else if (body.action === "read") { t.markRead(); }
    else if (body.action === "reply") { t.reply(body.body, { htmlBody: String(body.body).replace(/\n/g, "<br>") }); t.markRead(); }
    else if (body.action === "star") { t.getMessages()[0].star(); }
    else return out_({ error: "unknown action" });
    sync();
    return out_({ ok: true, did: body.action });
  } catch (err) { return out_({ error: String(err) }); }
}

function doGet() { return out_({ ok: true, bridge: "jarvis", account: me_()[0], business: BUSINESS }); }
function out_(o) { return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON); }
