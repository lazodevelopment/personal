/**
 * JARVIS Gmail bridge — paste this into a Google Apps Script project inside the Gmail account
 * you want JARVIS to watch (script.google.com → New project → replace the code → fill the 4 lines below).
 *
 * Version 3.2 (quota-light). Google allows a limited number of Gmail calls per day from Apps Script; v2 re-read every
 * thread's body every 5 minutes and could exhaust that by mid-afternoon ("Service invoked too many times for one day").
 * v3 only reads a thread when its last message changed, remembers thread bodies for a few hours, and syncs every 10 min.
 * v3.1 adds find_sent, which the hub uses to confirm the Zola / Knot intake script really sent its first reply.
 * v3.2 sends attachments: reply and send accept attachments [{name, type, data}] (base64) from the hub.
 *   sync()   sends the inbox (last 2 days, up to 40 threads) to the hub
 *   doPost() lets the hub read a thread, archive, mark read, star, reply, send a message you confirmed on the hub,
 *            or look in Sent for a message to an address (find_sent)
 *
 * Setup (once per account):
 *   1. Fill HUB_KEY (from C:\Users\kurvh\jarvis-hub\.hub-key), BUSINESS, and a long random SECRET.
 *   2. Run the function `setup` once (toolbar ▶). Approve the permissions when Google asks.
 *   3. Deploy → New deployment → type "Web app" → Execute as: Me → Who has access: Anyone → Deploy.
 *   4. Run `setup` once more so the hub learns the web-app URL. Done: the Inbox panel fills within 10 minutes.
 *   Upgrading from v2: paste over the code, run `setup`, then Deploy → Manage deployments → edit → New version → Deploy.
 */
const HUB = "https://jarvis-hub.floral-credit-e4f0.workers.dev";
const HUB_KEY = "PASTE_HUB_KEY_HERE";
const BUSINESS = "es";          // atavia | es | lazo | roven | lr | brisk | other
const SECRET = "PASTE_A_LONG_RANDOM_SECRET_HERE";

function setup() {
  ScriptApp.getProjectTriggers().forEach(function (t) { ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger("sync").timeBased().everyMinutes(10).create();
  sync();
}

function me_() {
  var mine = [Session.getEffectiveUser().getEmail()].concat(GmailApp.getAliases()).map(function (a) { return String(a).toLowerCase(); });
  return mine.filter(Boolean);
}

// per-thread summaries survive between runs (6 h), so unchanged threads cost one Gmail call instead of ten
function sync() {
  var mine = me_(), cache = CacheService.getScriptCache();
  var threads = GmailApp.search("in:inbox newer_than:2d", 0, 40);
  var items = [], reads = 0;
  for (var i = 0; i < threads.length; i++) {
    var t = threads[i], id = t.getId(), lastDate = t.getLastMessageDate().toISOString();
    var hit = cache.get("s:" + id);
    if (hit) { var cached = JSON.parse(hit); if (cached.date === lastDate) { cached.unread = t.isUnread(); items.push(cached); continue; } }
    reads++;
    var msgs = t.getMessages(); var last = msgs[msgs.length - 1];
    var from = last.getFrom() || "";
    var fromEmail = (from.match(/<([^>]+)>/) || [null, from])[1].toLowerCase();
    var body = "";
    try { body = (last.getPlainBody() || "").replace(/\s+/g, " ").trim().slice(0, 400); } catch (e) {}
    var item = {
      threadId: id, subject: t.getFirstMessageSubject() || "(no subject)", from: from, fromEmail: fromEmail,
      date: lastDate, snippet: body, unread: t.isUnread(), count: msgs.length,
      lastFromMe: mine.indexOf(fromEmail) >= 0, starred: t.hasStarredMessages(), important: t.isImportant(),
      labels: t.getLabels().map(function (l) { return l.getName(); }),
      link: "https://mail.google.com/mail/u/0/#all/" + id
    };
    try { cache.put("s:" + id, JSON.stringify(item), 21600); } catch (e) {}
    items.push(item);
  }
  var hookUrl = ""; try { hookUrl = ScriptApp.getService().getUrl() || ""; } catch (e) {}
  var payload = { account: mine[0], business: BUSINESS, hookUrl: hookUrl, secret: SECRET, items: items, at: new Date().toISOString(), bridge: 3.2, reads: reads };
  var r = UrlFetchApp.fetch(HUB + "/api/inbox", { method: "post", contentType: "application/json", headers: { "x-hub-key": HUB_KEY }, payload: JSON.stringify(payload), muteHttpExceptions: true });
  Logger.log(r.getResponseCode() + " reads=" + reads + " " + r.getContentText().slice(0, 160));
}

function doPost(e) {
  var body = {};
  try { body = JSON.parse(e.postData.contents); } catch (err) { return out_({ error: "bad json" }); }
  if (body.secret !== SECRET) return out_({ error: "bad secret" });
  var cache = CacheService.getScriptCache();
  try {
    var att = blobs_(body.attachments), attNote = att.length ? " with " + att.length + " attachment" + (att.length > 1 ? "s" : "") : "";
    if (body.action === "send") { GmailApp.sendEmail(body.to, body.subject, body.body, { htmlBody: String(body.body).replace(/\n/g, "<br>"), attachments: att }); return out_({ ok: true, did: "sent to " + body.to + attNote }); }
    if (body.action === "find_sent") {   // did this account send anything to an address recently? (the hub verifies intake auto-replies)
      var to = String(body.to || "").trim(); if (!/^[^\s@]+@[^\s@]+$/.test(to)) return out_({ error: "bad address" });
      var hits = GmailApp.search("in:sent to:" + to + " newer_than:" + (parseInt(body.newerThanDays, 10) || 3) + "d", 0, 5), latest = null;
      hits.forEach(function (t) { t.getMessages().forEach(function (m) { if (!latest || m.getDate() > latest.getDate()) latest = m; }); });
      return out_({ ok: true, found: !!latest, count: hits.length, date: latest ? latest.getDate().toISOString() : null, subject: latest ? latest.getSubject() : null });
    }
    var t = GmailApp.getThreadById(body.threadId);
    if (!t) return out_({ error: "thread not found" });
    if (body.action === "get") {
      var key = "t:" + body.threadId + ":" + t.getLastMessageDate().getTime();
      var hit = cache.get(key); if (hit) return out_(JSON.parse(hit));
      var msgs = t.getMessages().slice(-12).map(function (m) {
        var txt = ""; try { txt = m.getPlainBody() || ""; } catch (e) {}
        return { id: m.getId(), from: m.getFrom(), to: m.getTo(), cc: m.getCc(), date: m.getDate().toISOString(), subject: m.getSubject(), body: txt.slice(0, 20000), unread: m.isUnread(),
                 attachments: m.getAttachments().map(function (a) { return a.getName(); }) };
      });
      var res = { ok: true, subject: t.getFirstMessageSubject(), messages: msgs, link: "https://mail.google.com/mail/u/0/#all/" + t.getId() };
      try { var s = JSON.stringify(res); if (s.length < 95000) cache.put(key, s, 21600); } catch (e) {}
      return out_(res);
    }
    if (body.action === "archive") { t.markRead(); t.moveToArchive(); }
    else if (body.action === "read") { t.markRead(); }
    else if (body.action === "reply") { t.reply(body.body, { htmlBody: String(body.body).replace(/\n/g, "<br>"), attachments: att }); t.markRead(); }
    else if (body.action === "star") { t.getMessages()[0].star(); }
    else return out_({ error: "unknown action" });
    cache.remove("s:" + body.threadId);
    return out_({ ok: true, did: body.action + attNote });
  } catch (err) { return out_({ error: String(err) }); }
}

// attachments arrive as [{name, type, data (base64)}] from the hub; Gmail takes them as blobs (25 MB per message)
function blobs_(list) {
  if (!list || !list.length) return [];
  return list.slice(0, 10).map(function (a) { return Utilities.newBlob(Utilities.base64Decode(String(a.data || "")), a.type || "application/octet-stream", a.name || "attachment"); });
}

function doGet() { return out_({ ok: true, bridge: 3.2, account: me_()[0], business: BUSINESS }); }
function out_(o) { return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON); }
