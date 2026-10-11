/**
 * Elizabeth Scott: text the couple as well as emailing them  (JC-ESW-TEXT-1010)
 *
 * Fourth file (Texting) in the 'Elizabeth Scott' project in hello@. Pilot for Elizabeth Scott only;
 * Atavia keeps email-only until this proves itself. Two texts at most per couple, from an Elizabeth
 * Scott number on the Telnyx account Lazo already uses (same API as lazo-functions leads.js):
 *   1. First touch, right after the automatic first reply, when Zola's notice carried a phone number
 *      ("Couple phone: Not provided" means no text). Says who we are, that the collections and pricing
 *      just went to their email, and that they can text back here.
 *   2. The Day 5 nudge, sent by FollowUps.gs next to the Day 5 email, with the fresh code.
 * Nothing else is ever texted. Texts go out 10 AM to 8 PM Eastern (SMS_TZ); an inquiry that lands
 * outside that window is queued and goes at the next sync inside it. A couple who texts back gets no
 * more automatic texts and no more follow-up emails: a person takes it from there. STOP is honoured by
 * Telnyx itself and also recorded here; a send Telnyx refuses because they opted out is recorded the
 * same way.
 *
 * Replies: deploy this project as a web app (Deploy > New deployment > Web app, execute as me, anyone
 * can access). In Telnyx, give the Elizabeth Scott number its OWN messaging profile (the Lazo profile's
 * webhook goes to the Lazo Cloud Function, which ignores other numbers) and set that profile's inbound
 * webhook URL to the web app URL with ?k=<SMS_INBOUND_KEY>, API v2. Each incoming text is emailed to
 * this inbox ("Text from <name>"), stamped on the inquiry for the Leads page, and ends the couple's
 * follow-up sequence. Apps Script cannot check Telnyx's Ed25519 signature, so the key in the URL is
 * what keeps strangers out.
 *
 * Script properties (Project Settings > Script properties): TELNYX_API_KEY (the Lazo account's key, or
 * a new key on that account), TELNYX_FROM (the Elizabeth Scott number, E.164, e.g. +18885550123),
 * SMS_INBOUND_KEY (any long random string; the same one in the webhook URL). Without the first two
 * nothing is sent and the email reply is unaffected.
 *
 * Helpers (none sends to a couple): `smsCheck` confirms the settings, the number and the window;
 * `previewText` shows the first text for the newest inquiry; `testText` sends that text to SMS_TEST_TO
 * (your own mobile); `smsReport` lists every couple texted in the last 11 days; `smsStopFor` ends one
 * couple's texts.
 */
var SMS_ENABLED = true;              // false pauses every text; previews still work
var SMS_TZ = 'America/New_York';     // the window is kept in Eastern time: the project runs on Phoenix time and the couples are mostly East Coast
var SMS_START_HOUR = 10, SMS_END_HOUR = 20;   // 10 AM to 8 PM Eastern (7 AM to 5 PM Pacific), so no early mornings or late nights anywhere
var SMS_TEST_TO = '';                // your own mobile, E.164, for testText
var SMS_STOP_EMAIL = '';             // set and run smsStopFor to end one couple's texts
var SMS_MAX_DAYS = 11;
var TELNYX_API = 'https://api.telnyx.com/v2';

// ------------------------------------------------------------------ config --
function smsConfig() {
  var p = PropertiesService.getScriptProperties();
  return { key: p.getProperty('TELNYX_API_KEY') || '', from: smsNormalize(p.getProperty('TELNYX_FROM') || ''),
           inboundKey: p.getProperty('SMS_INBOUND_KEY') || '' };
}
function smsReady() { var c = smsConfig(); return !!(SMS_ENABLED && c.key && c.from); }
function smsInWindow() {
  var h = +Utilities.formatDate(new Date(), SMS_TZ, 'H');
  return h >= SMS_START_HOUR && h < SMS_END_HOUR;
}
/** US number as +1XXXXXXXXXX, or '' when the notice had none (Zola writes "Not provided"). */
function smsNormalize(raw) {
  var d = String(raw || '').replace(/\D/g, '');
  if (d.length === 11 && d.charAt(0) === '1') d = d.slice(1);
  if (d.length !== 10 || /^[01]/.test(d) || /^\d{3}[01]/.test(d)) return '';
  return '+1' + d;
}

// ----------------------------------------------------------------- records --
// One record per couple, keyed by email like the intake script's own memory: sms:<email> =
// {phone, first, code, date, venue, threadId, at, sid, pending, pendingStep, d5At, optout, replies, lastReply, failed}
function smsRecord(email) { try { return JSON.parse(PropertiesService.getUserProperties().getProperty('sms:' + email) || '{}'); } catch (e) { return {}; } }
function smsSave(email, rec) { PropertiesService.getUserProperties().setProperty('sms:' + email, JSON.stringify(rec)); }
function smsAll() {
  var props = PropertiesService.getUserProperties().getProperties(), out = [];
  Object.keys(props).forEach(function (k) {
    if (k.indexOf('sms:') !== 0) return;
    var rec = {}; try { rec = JSON.parse(props[k]); } catch (e) {}
    rec.email = k.slice(4); out.push(rec);
  });
  return out;
}
function smsByPhone(phone) {
  var hit = null;
  smsAll().forEach(function (r) { if (r.phone === phone && (!hit || String(r.created || '') > String(hit.created || ''))) hit = r; });
  return hit;
}

// ----------------------------------------------------------------- sending --
/** One Telnyx send (POST /v2/messages, as lazo-functions does). Returns {ok, sid, status, optout, error}; never throws. */
function smsSend(to, body) {
  var c = smsConfig();
  try {
    var r = UrlFetchApp.fetch(TELNYX_API + '/messages', {
      method: 'post', contentType: 'application/json', headers: { Authorization: 'Bearer ' + c.key },
      payload: JSON.stringify({ from: c.from, to: to, text: body }), muteHttpExceptions: true });
    var j = {}; try { j = JSON.parse(r.getContentText()); } catch (e) {}
    var ok = r.getResponseCode() < 300, d = (j && j.data) || {}, err = (j && j.errors && j.errors[0]) || {};
    var error = ok ? '' : ((err.code ? err.code + ' ' : '') + (err.title || '') + (err.detail ? ': ' + err.detail : '')).trim() || r.getContentText().slice(0, 200);
    return { ok: ok, sid: d.id || '', status: (d.to && d.to[0] && d.to[0].status) || '',
             optout: !ok && /opt.?out|opted|unsubscrib|blocked.*stop|stop.*blocked/i.test(error), error: error };
  } catch (e) { return { ok: false, sid: '', status: '', optout: false, error: String(e) }; }
}

/**
 * Called by sync() right after sendAutoReply. Returns a short note that is appended to the reply's
 * log line and the JARVIS report (" + text to +1…", " (no text: no phone)", " (text queued…)").
 */
function sendFirstText(thread, msg, inq, code) {
  if (!SMS_ENABLED) return '';
  var to = smsNormalize(inq.phone);
  if (!to) return ' (no text: no phone in the notice)';
  if (!smsReady()) return ' (no text: Telnyx not configured)';
  var rec = smsRecord(inq.email);
  if (rec.at || rec.pending) return ' (text already sent)';
  rec = { phone: to, first: inq.first_name || '', code: code ? code.code : '', date: inq.wedding_date || '', venue: inq.venue || '',
          threadId: thread ? thread.getId() : '', created: new Date().toISOString() };
  var body = smsFirstBody(inq, code);
  if (!smsInWindow()) {
    rec.pending = body; rec.pendingStep = 'sms1'; smsSave(inq.email, rec);
    return ' (text queued for ' + SMS_START_HOUR + ':00 ' + SMS_TZ + ')';
  }
  return smsDeliver(inq.email, rec, 'sms1', body);
}

/** Sends one text for a couple and records the outcome. step is sms1 or sms5. */
function smsDeliver(email, rec, step, body) {
  var r = smsSend(rec.phone, body), now = new Date().toISOString();
  delete rec.pending; delete rec.pendingStep;
  if (r.ok) {
    if (step === 'sms1') { rec.at = now; rec.sid = r.sid; } else { rec.d5At = now; rec.d5Sid = r.sid; }
    smsSave(email, rec); smsLog(email, rec.code, step, 'sent to ' + rec.phone);
    Logger.log('texted ' + email + ' (' + step + ') at ' + rec.phone);
    return ' + text to ' + rec.phone;
  }
  if (r.optout) rec.optout = now;           // they replied STOP to this number before
  rec.failed = (step + ': ' + r.error).slice(0, 200);
  smsSave(email, rec); smsLog(email, rec.code, step, 'failed: ' + r.error);
  Logger.log('text FAILED for ' + email + ': ' + r.error);
  return ' (text failed: ' + r.error.slice(0, 80) + ')';
}

/** Sends texts that were queued outside the window. Called at the start of every sync(). */
function smsSendPending() {
  if (!SMS_ENABLED || !smsReady() || !smsInWindow()) return;
  smsAll().forEach(function (rec) {
    if (!rec.pending || rec.optout) return;
    var email = rec.email, step = rec.pendingStep || 'sms1', body = rec.pending; delete rec.email;
    if (step === 'sms5' && rec.replies) { delete rec.pending; delete rec.pendingStep; smsSave(email, rec); return; }   // they wrote back meanwhile
    Logger.log('sending queued text (' + step + ') to ' + email + ': ' + smsDeliver(email, rec, step, body));
  });
}

/**
 * Called by FollowUps.gs after it sends a follow-up email. Only the Day 5 email gets a text, and only
 * for a couple who got the first text and has not replied or opted out.
 */
function fuText(email, step, info) {
  if (!SMS_ENABLED || step !== 'd5' || !smsReady()) return;
  var rec = smsRecord(email);
  if (!rec.at || rec.optout || rec.replies || rec.d5At || rec.pending) return;
  if (!info || !info.fresh || !info.fresh.code) return;
  var body = smsD5Body(rec, info.fresh);
  if (!smsInWindow()) { rec.pending = body; rec.pendingStep = 'sms5'; smsSave(email, rec); Logger.log('day-5 text queued for ' + email); return; }
  Logger.log('day-5 text for ' + email + ':' + smsDeliver(email, rec, 'sms5', body));
}

// -------------------------------------------------------------------- copy --
function smsFirstBody(inq, code) {
  var first = inq.first_name || 'there';
  var when = inq.wedding_date ? ' on ' + prettyDate(inq.wedding_date) : '';
  var where = inq.venue ? ' in ' + inq.venue : '';
  return 'Hi ' + first + ', this is the Elizabeth Scott Weddings team. Thank you for your Zola inquiry about your wedding' + when + where
    + '. We just emailed our collections and pricing to ' + inq.email + ' (check Promotions if it is not in your inbox).'
    + ' Happy to answer anything here by text. Reply STOP to opt out.';
}
function smsD5Body(rec, fresh) {
  var first = rec.first || 'there';
  return 'Hi ' + first + ', Elizabeth Scott Weddings here. If you are still deciding, we set aside code ' + fresh.code + ': $' + (fresh.amount || 200)
    + ' off any collection through ' + prettyDate(fresh.expires_at) + '. It is already applied at elizabethscottweddings.com/book/?code=' + fresh.code
    + ' and a quick reply here reaches our team. Reply STOP to opt out.';
}

// --------------------------------------------------------------- site log --
/** Stamps the text on the inquiry for the Leads page (followups.sms1 / sms5 / smsreply). Needs the first reply's code. */
function smsLog(email, code, step, state) {
  if (!code) return;
  try {
    UrlFetchApp.fetch(WEBHOOK, { method: 'post', contentType: 'application/json', muteHttpExceptions: true,
      payload: JSON.stringify({ action: 'followup_log', check_email: email, code: code, step: step, state: state }) });
  } catch (e) { Logger.log('site not told about ' + step + ': ' + e); }
}

// ----------------------------------------------------------- replies (web app) --
/**
 * Telnyx posts every event for the Elizabeth Scott messaging profile here (JSON, API v2). Only
 * message.received to our number is acted on; delivery receipts and other numbers are ignored.
 * Always answers 200 so Telnyx does not retry.
 */
function doPost(e) {
  var p = (e && e.parameter) || {}, c = smsConfig();
  var out = ContentService.createTextOutput('ok').setMimeType(ContentService.MimeType.TEXT);
  if (!c.inboundKey || p.k !== c.inboundKey) return out;       // not our webhook
  var evt = {}; try { evt = JSON.parse((e.postData && e.postData.contents) || '{}').data || {}; } catch (x) { return out; }
  if (evt.event_type !== 'message.received') return out;
  var pl = evt.payload || {};
  var toNums = (pl.to || []).map(function (t) { return smsNormalize(t && t.phone_number); });
  if (c.from && toNums.indexOf(c.from) < 0) return out;          // a text to some other number on the profile
  var from = smsNormalize(pl.from && pl.from.phone_number), body = String(pl.text || '').trim(), now = new Date().toISOString();
  var media = (pl.media || []).map(function (m) { return m && m.url; }).filter(Boolean);
  if (!from) return out;
  var rec = smsByPhone(from), email = rec ? rec.email : '';
  if (rec) delete rec.email;
  if (/^\s*(stop|stopall|unsubscribe|cancel|end|quit)\b/i.test(body)) {
    if (rec) { rec.optout = now; delete rec.pending; smsSave(email, rec); smsLog(email, rec.code, 'smsstop', 'opted out by text'); }
    return out;
  }
  if (/^\s*(start|unstop|yes)\s*$/i.test(body) && rec) { delete rec.optout; smsSave(email, rec); return out; }
  if (rec) {
    rec.replies = (rec.replies || 0) + 1; rec.lastReply = now; delete rec.pending; smsSave(email, rec);
    smsLog(email, rec.code, 'smsreply', body.slice(0, 100));
    try { if (typeof fuState === 'function') { var st = fuState(email); if (!st.stop) { st.stop = 'they replied by text'; fuSave(email, st); if (rec.code) fuLog(email, rec.code, '', 'stopped: they replied by text', true); } } } catch (x) {}
  }
  var who = rec ? ((rec.first || '') + ' <' + email + '>').trim() : 'unknown number';
  var me = Session.getEffectiveUser().getEmail();
  var subject = 'Text from ' + (rec && rec.first ? rec.first : from) + (rec && rec.date ? ' (wedding ' + rec.date + ')' : '');
  var text = (body || (media.length ? '(photo)' : '(empty)')) + (media.length ? '\n' + media.join('\n') : '')
    + '\n\n— ' + who + ', ' + from + '\nReply by text from the Telnyx portal (Messaging > Send a message) or call them; the follow-up emails for this couple have stopped.';
  try { GmailApp.sendEmail(me, subject, text, { name: 'Elizabeth Scott texts' }); } catch (x) { Logger.log('reply email failed: ' + x); }
  return out;
}
function doGet() { return ContentService.createTextOutput('Elizabeth Scott texting webhook is up.'); }

// ----------------------------------------------------------------- helpers --
/** Settings, number and window check. Sends nothing. */
function smsCheck() {
  var c = smsConfig(), raw = PropertiesService.getScriptProperties().getProperty('TELNYX_FROM') || '';
  Logger.log('SMS_ENABLED: ' + SMS_ENABLED + '\nTELNYX_API_KEY: ' + (c.key ? 'set' : 'MISSING') + '\nTELNYX_FROM: ' + (c.from || (raw ? 'INVALID (' + raw + ')' : 'MISSING'))
    + '\nSMS_INBOUND_KEY: ' + (c.inboundKey ? 'set' : 'missing (replies will be ignored)')
    + '\nwindow: ' + SMS_START_HOUR + ':00-' + SMS_END_HOUR + ':00 ' + SMS_TZ + ', now ' + (smsInWindow() ? 'INSIDE' : 'outside') + ' (project time zone ' + Session.getScriptTimeZone() + ')'
    + '\nready to send: ' + smsReady());
  if (c.key) {
    var r = UrlFetchApp.fetch(TELNYX_API + '/phone_numbers?filter[phone_number]=' + encodeURIComponent(c.from || '+10000000000'), { headers: { Authorization: 'Bearer ' + c.key }, muteHttpExceptions: true });
    var j = {}; try { j = JSON.parse(r.getContentText()); } catch (e) {}
    var n = (j.data || [])[0];
    Logger.log('Telnyx check: HTTP ' + r.getResponseCode() + (r.getResponseCode() >= 300 ? ' ' + r.getContentText().slice(0, 150)
      : n ? ' — ' + n.phone_number + ' is on this account (' + (n.status || '') + ', messaging profile ' + (n.messaging_profile_id || 'NONE: assign one in Telnyx') + ')'
      : ' — key works but ' + (c.from || 'TELNYX_FROM') + ' is not a number on this account'));
  }
}
/** The first text for the newest inquiry. Sends nothing. */
function previewText() {
  var m = latestInquiry();
  if (!m) { Logger.log('no inquiries in the last 7 days'); return; }
  var inq = parseInquiry(m.getSubject(), m.getPlainBody(), m.getFrom(), m.getReplyTo());
  var to = smsNormalize(inq.phone), body = smsFirstBody(inq, { code: 'ESW-XXXX-200', amount: 200, expires_at: new Date(Date.now() + 72 * 3600e3).toISOString() });
  Logger.log('To: ' + (to || '(no phone: "' + inq.phone + '", no text would go)') + '\n' + body + '\n[' + body.length + ' characters]'
    + '\nDay 5 would be:\n' + smsD5Body({ first: inq.first_name }, { code: 'ESW-YYYY-200', amount: 200, expires_at: new Date(Date.now() + 72 * 3600e3).toISOString() }));
}
/** Sends the newest inquiry's first text to SMS_TEST_TO (you), never to the couple. */
function testText() {
  var to = smsNormalize(SMS_TEST_TO);
  if (!to) { Logger.log('set SMS_TEST_TO to your own mobile first'); return; }
  if (!smsReady()) { Logger.log('Telnyx is not configured (run smsCheck)'); return; }
  var m = latestInquiry(), inq = m ? parseInquiry(m.getSubject(), m.getPlainBody(), m.getFrom(), m.getReplyTo()) : { first_name: 'Sarah', wedding_date: '2027-06-12', venue: 'Boston, MA', email: 'sample@example.com' };
  var r = smsSend(to, '[TEST] ' + smsFirstBody(inq, null));
  Logger.log(r.ok ? 'sent to ' + to + ' (' + r.sid + ', ' + r.status + ')' : 'FAILED: ' + r.error);
}
/** Every couple texted in the last SMS_MAX_DAYS days and where they stand. */
function smsReport() {
  var oldest = Date.now() - SMS_MAX_DAYS * 864e5, n = 0;
  smsAll().forEach(function (r) {
    if (new Date(r.created || 0).getTime() < oldest) return;
    n++;
    Logger.log(r.email + ' ' + r.phone + ': ' + (r.at ? 'first text ' + r.at.slice(0, 16) : r.pending ? 'queued (' + (r.pendingStep || 'sms1') + ')' : 'no first text')
      + (r.d5At ? ', day-5 text ' + r.d5At.slice(0, 16) : '') + (r.replies ? ', replied ' + r.replies + 'x (last ' + String(r.lastReply).slice(0, 16) + ')' : '')
      + (r.optout ? ', OPTED OUT' : '') + (r.failed ? ', failed: ' + r.failed : ''));
  });
  if (!n) Logger.log('no couples texted in the last ' + SMS_MAX_DAYS + ' days');
}
/** Ends one couple's texts by hand: set SMS_STOP_EMAIL and run. */
function smsStopFor() {
  var email = String(SMS_STOP_EMAIL || '').trim().toLowerCase();
  if (!email) { Logger.log('set SMS_STOP_EMAIL first'); return; }
  var rec = smsRecord(email); rec.optout = new Date().toISOString(); delete rec.pending; smsSave(email, rec);
  Logger.log('texts stopped for ' + email);
}
