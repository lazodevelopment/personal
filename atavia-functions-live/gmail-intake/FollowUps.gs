/**
 * Inquiry follow-ups: Day 2, 3, 5 and 10 after the automatic first reply  (JC-FOLLOWUP-1009)
 *
 * Add this as a SECOND FILE (FollowUps.gs) in each intake project, next to the intake script:
 *   'Zola Intake' in ataviaweddings@gmail.com, 'Atavia' in info@ataviaweddings.com,
 *   'Elizabeth Scott' in hello@elizabethscottweddings.com. The same file works in all three:
 *   the brand comes from the intake script's WEBHOOK.
 * Then: Services (+) > Gmail API > Add (so follow-ups land in the same thread), run
 * `previewFollowUps` (sends nothing), `testFollowUpEmails` (sends the four samples to this
 * inbox only), and `setupFollowUps` once to start the hourly trigger.
 *
 * Who: every couple the intake script answered (its 'sent:<email>' memory) in the last 11 days.
 * When: Day 2 = 48 h after the first reply; Day 3 = 64 h, only while their first code still has
 * an hour left; Day 5 = 120 h with a fresh $200 / 72 h code; Day 10 = 240 h, the last one.
 * Sends 9 AM to 6 PM (project time zone), at most one email per couple per run, 18 h apart;
 * when several steps are due (e.g. after a pause) only the latest goes and the rest are skipped.
 * Stops for good when the couple writes back (email, or a Zola / Knot message notice), someone
 * here writes to them by hand, they start or finish a booking, the code is redeemed, or the
 * wedding date passes. Every send and stop is stamped on the inquiry for the Leads page.
 */
var FU_BRAND = '';              // '' = from WEBHOOK; or force 'atavia' / 'es'
var FU_ENABLED = true;          // false pauses sending; previews still work
var FU_START_HOUR = 9, FU_END_HOUR = 18;
var FU_MIN_GAP_HOURS = 18;
var FU_MAX_DAYS = 11;
var FU_STOP_EMAIL = '';         // set to a couple's email and run stopFollowUp to end their sequence
var FU_STEPS = [{ k: 'd2', h: 48 }, { k: 'd3', h: 64 }, { k: 'd5', h: 120 }, { k: 'd10', h: 240 }];

var FU_BRANDS = {
  atavia: { name: 'Atavia Weddings', site: 'https://ataviaweddings.com', host: 'ataviaweddings.com',
            phone: '(336) 537-9590', signer: 'Lauren McKinnon', style: 'letter' },
  es: { name: 'Elizabeth Scott Weddings', site: 'https://elizabethscottweddings.com', host: 'elizabethscottweddings.com',
        email: 'hello@elizabethscottweddings.com', signer: 'The Elizabeth Scott Weddings Team', style: 'card' }
};

function fuBrand() {
  var k = FU_BRAND || (/atavia/i.test(String(WEBHOOK)) ? 'atavia' : 'es');
  return FU_BRANDS[k];
}

function setupFollowUps() {
  ScriptApp.getProjectTriggers().forEach(function (t) { if (t.getHandlerFunction() === 'followUps') ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('followUps').timeBased().everyHours(1).create();
  Logger.log('Hourly follow-up trigger is in place for ' + fuBrand().name + '. Gmail API service: '
    + (typeof Gmail !== 'undefined' ? 'on (follow-ups thread under the first reply)' : 'OFF, add it under Services so follow-ups thread'));
}

/** The hourly trigger. */
function followUps() {
  if (!FU_ENABLED) return;
  var tz = Session.getScriptTimeZone(), hour = +Utilities.formatDate(new Date(), tz, 'H');
  if (hour < FU_START_HOUR || hour >= FU_END_HOUR) return;
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(5000)) return;
  try {
    fuCouples().forEach(function (c) {
      try { var r = fuOne(c, false); if (r) Logger.log(c.email + ': ' + r); }
      catch (e) { Logger.log(c.email + ': error ' + e); }
    });
  } finally { lock.releaseLock(); }
}

/** What the next run would do for every couple in the window. Sends nothing, mints nothing. */
function previewFollowUps() {
  var list = fuCouples();
  if (!list.length) { Logger.log('no couples answered in the last ' + FU_MAX_DAYS + ' days'); return; }
  list.forEach(function (c) {
    var r; try { r = fuOne(c, true); } catch (e) { r = 'error ' + e; }
    Logger.log(c.email + ' (first reply ' + c.at.toISOString().slice(0, 16) + '): ' + r);
  });
}

/** Ends one couple's sequence by hand: set FU_STOP_EMAIL and run. */
function stopFollowUp() {
  var email = String(FU_STOP_EMAIL || '').trim().toLowerCase();
  if (!email) { Logger.log('set FU_STOP_EMAIL first'); return; }
  var st = fuState(email); st.stop = 'stopped by hand'; fuSave(email, st);
  Logger.log('follow-ups stopped for ' + email);
}

/** Sends the four sample emails to this inbox only, so you can see them as couples will. */
function testFollowUpEmails() {
  var me = Session.getEffectiveUser().getEmail(), b = fuBrand(), now = Date.now();
  var c = { first: 'Sarah', date: '2027-06-12', source: 'Zola', firstReplyAt: new Date(now - 48 * 3600e3),
            code: { code: b.style === 'card' ? 'ESW-K7QM-200' : 'ATAVIA-K7QM-200', amount: 200, expires_at: new Date(now + 4 * 3600e3).toISOString() },
            fresh: { code: b.style === 'card' ? 'ESW-P4XR-200' : 'ATAVIA-P4XR-200', amount: 200, expires_at: new Date(now + 72 * 3600e3).toISOString() } };
  FU_STEPS.forEach(function (s) {
    var m = fuEmail(s.k, c);
    GmailApp.sendEmail(me, '[TEST ' + s.k.toUpperCase() + '] Re: Your wedding — ' + b.name, m.text, { htmlBody: m.html, name: b.name });
  });
  Logger.log('sent 4 samples to ' + me);
}

// ------------------------------------------------------------ the sequence --
function fuCouples() {
  var props = PropertiesService.getUserProperties().getProperties(), out = [], oldest = Date.now() - FU_MAX_DAYS * 864e5;
  Object.keys(props).forEach(function (k) {
    if (k.indexOf('sent:') !== 0) return;
    var at = new Date(props[k]);
    if (isNaN(at) || at.getTime() < oldest) return;
    var email = k.slice(5), st = {};
    try { st = JSON.parse(props['fu:' + email] || '{}'); } catch (e) {}
    if (st.stop || (st.done && st.done.d10)) return;
    out.push({ email: email, at: at });
  });
  return out.sort(function (a, b) { return a.at - b.at; });
}

function fuState(email) { try { return JSON.parse(PropertiesService.getUserProperties().getProperty('fu:' + email) || '{}'); } catch (e) { return {}; } }
function fuSave(email, st) { PropertiesService.getUserProperties().setProperty('fu:' + email, JSON.stringify(st)); }

/** One couple: decide, check, send. Returns a line for the log. dry = preview only. */
function fuOne(c, dry) {
  var st = fuState(c.email); st.done = st.done || {};
  var now = new Date();
  var first = fuFirstReply(c.email, c.at);
  if (!first) return fuStop(c, st, null, 'no first reply to them in Sent', dry);
  var ageH = (now - first.msg.getDate()) / 3600e3;
  var due = null;
  FU_STEPS.forEach(function (s) { if (ageH >= s.h && !st.done[s.k]) due = s; });
  if (!due) {
    var next = FU_STEPS.filter(function (s) { return !st.done[s.k]; })[0];
    return next ? 'waiting: ' + next.k + ' in ' + Math.ceil(next.h - ageH) + ' h' : 'sequence finished';
  }
  if (st.last && (now - new Date(st.last)) / 3600e3 < FU_MIN_GAP_HOURS) return 'waiting: ' + due.k + ' (18 h gap after the last follow-up)';

  var code = (first.msg.getPlainBody().match(/\b(?:ATAVIA|ESW)-[A-Z0-9]{4}-\d+\b/) || [])[0];
  if (!code) return fuStop(c, st, null, 'first reply carried no code, nothing to check against', dry);

  var engaged = fuEngaged(c.email, first, st);
  if (engaged) return fuStop(c, st, code, engaged, dry);

  var res = fuCall({ action: 'followup_status', check_email: c.email, code: code, mint: due.k === 'd5' && !dry });
  if (res.status === 404) return fuStop(c, st, null, 'inquiry not found on the site', dry);
  if (!res.ok) return 'site check failed (' + res.status + '), retry next hour';
  var s = res.data;
  if (s.booked) return fuStop(c, st, code, 'booked', dry);
  if (s.started) return fuStop(c, st, code, 'started booking on the site (the booking-page nudges take it from here)', dry);
  if (s.code_redeemed) return fuStop(c, st, code, 'used their code', dry);
  if (s.stopped) return fuStop(c, st, code, 'stopped on the site', dry);
  if (s.wedding_date && new Date(s.wedding_date + 'T23:59:59') < now) return fuStop(c, st, code, 'wedding date has passed', dry);

  var info = { first: s.first_name || '', date: s.wedding_date || '', source: s.found_us || '', firstReplyAt: first.msg.getDate(),
               code: { code: code, amount: 200, expires_at: s.code_expires_at }, fresh: s.followup_code };
  if (due.k === 'd3' && (!s.code_expires_at || new Date(s.code_expires_at) - now < 3600e3)) {
    if (!dry) { fuSkipThrough(st, due.k, true); fuSave(c.email, st); fuLog(c.email, code, 'd3', 'skipped: code already expired', false); }
    return 'd3 skipped: their code has expired (d5 brings a new one)';
  }
  if (due.k === 'd5' && !info.fresh) {
    if (dry) info.fresh = { code: '(new code minted at send)', amount: 200, expires_at: new Date(now.getTime() + 72 * 3600e3).toISOString() };
    else return 'd5 waiting: the site could not mint a code, retry next hour';
  }
  if (due.k !== 'd2' && due.k !== 'd3') info.code = null;              // the first code is spent by Day 5
  else if (info.code.expires_at && new Date(info.code.expires_at) < now) info.code = null;

  var m = fuEmail(due.k, info);
  var skipped = FU_STEPS.filter(function (x) { return x.h < due.h && !st.done[x.k]; }).map(function (x) { return x.k; });
  if (dry) return 'WILL SEND ' + due.k + (skipped.length ? ' (skipping ' + skipped.join(', ') + ')' : '') + ' to ' + c.email
    + '\n----\n' + m.text + '\n----';
  fuSend(first.msg, c.email, m);
  fuSkipThrough(st, due.k, false);
  st.done[due.k] = now.toISOString(); st.last = now.toISOString(); st.sent = (st.sent || 0) + 1;
  fuSave(c.email, st);
  fuLog(c.email, code, due.k, 'sent' + (skipped.length ? ' (skipped ' + skipped.join(', ') + ')' : ''), false);
  return 'sent ' + due.k;
}

function fuSkipThrough(st, k, inclusive) {
  var due = FU_STEPS.filter(function (s) { return s.k === k; })[0];
  FU_STEPS.forEach(function (s) { if ((s.h < due.h || (inclusive && s.k === k)) && !st.done[s.k]) st.done[s.k] = 'skipped'; });
}

function fuStop(c, st, code, why, dry) {
  if (dry) return 'WILL STOP: ' + why;
  st.stop = why; fuSave(c.email, st);
  if (code) fuLog(c.email, code, '', 'stopped: ' + why, true);
  return 'stopped: ' + why;
}

/** Our first reply to this couple: the earliest message we sent them around the time the intake script answered. */
function fuFirstReply(email, at) {
  var mine = fuMine(), best = null;
  GmailApp.search('in:sent to:' + email, 0, 20).forEach(function (t) {
    t.getMessages().forEach(function (m) {
      if (!fuFromMe(m, mine) || String(m.getTo()).toLowerCase().indexOf(email) < 0) return;
      if (m.getDate() < new Date(at.getTime() - 3600e3)) return;
      if (!best || m.getDate() < best.getDate()) best = m;
    });
  });
  return best ? { msg: best } : null;
}

/** Why the sequence should stop because people are already talking, or '' to carry on. */
function fuEngaged(email, first, st) {
  var since = first.msg.getDate(), after = ' after:' + Math.floor(since.getTime() / 1000), mine = fuMine();
  if (GmailApp.search('from:' + email + after, 0, 1).length) return 'they replied by email';
  var replied = false;
  first.msg.getThread().getMessages().forEach(function (m) { if (m.getDate() > since && !fuFromMe(m, mine)) replied = true; });
  if (replied) return 'they replied in the thread';
  // A Zola / Knot "New message from…" notice that names them means they answered on the platform.
  var name = String(fuFirstName(first.msg) || '').replace(/"/g, '');
  if (name.length > 1 && GmailApp.search('from:(zola.com OR theknot.com OR weddingpro.com) (subject:"message from" OR subject:"sent you a new message") "' + name + '"' + after, 0, 1).length)
    return 'they messaged on the platform';
  // Anything we sent them besides the first reply and our own follow-ups means a person took over.
  var ours = 0;
  GmailApp.search('in:sent to:' + email + after, 0, 20).forEach(function (t) {
    t.getMessages().forEach(function (m) {
      if (m.getDate() > since && fuFromMe(m, mine) && String(m.getTo()).toLowerCase().indexOf(email) > -1) ours++;
    });
  });
  if (ours > (st.sent || 0)) return 'someone here wrote to them';
  return '';
}

function fuFirstName(msg) { return (msg.getPlainBody().match(/^\s*Hi ([^,\n]+),/) || [])[1] || ''; }
function fuMine() {
  var list = [Session.getEffectiveUser().getEmail()];
  try { list = list.concat(GmailApp.getAliases()); } catch (e) {}
  return list.map(function (x) { return String(x).toLowerCase(); });
}
function fuFromMe(m, mine) {
  var f = String(m.getFrom()).toLowerCase();
  return mine.some(function (x) { return f.indexOf(x) > -1; }) || /ataviaweddings\.com|elizabethscottweddings\.com/.test(f);
}

// ------------------------------------------------------------- site calls --
function fuCall(payload) {
  try {
    var r = UrlFetchApp.fetch(WEBHOOK, { method: 'post', contentType: 'application/json', payload: JSON.stringify(payload), muteHttpExceptions: true });
    var data = {}; try { data = JSON.parse(r.getContentText()); } catch (e) {}
    return { ok: r.getResponseCode() < 300 && data.ok, status: r.getResponseCode(), data: data };
  } catch (e) { return { ok: false, status: 0, data: {} }; }
}
function fuLog(email, code, step, state, stopped) {
  fuCall({ action: 'followup_log', check_email: email, code: code, step: step, state: state, stopped: !!stopped });
}

// ------------------------------------------------------------------ sending --
/** Replies under our first message so the couple sees one conversation. Falls back to a plain 'Re:' send without the Gmail API service. */
function fuSend(firstMsg, to, m) {
  var subj = firstMsg.getSubject(); if (!/^re:/i.test(subj)) subj = 'Re: ' + subj;
  var b = fuBrand();
  if (typeof Gmail === 'undefined') { GmailApp.sendEmail(to, subj, m.text, { htmlBody: m.html, name: b.name }); return; }
  var mid = firstMsg.getHeader('Message-ID'), refs = (firstMsg.getHeader('References') + ' ' + mid).trim();
  var enc = function (s) { return Utilities.base64Encode(s, Utilities.Charset.UTF_8); };
  var wrap = function (s) { return s.replace(/.{76}/g, '$&\r\n'); };
  var bound = 'fu' + Utilities.getUuid().replace(/-/g, '');
  var mime = [
    'From: ' + firstMsg.getFrom(),
    'To: ' + to,
    'Subject: =?UTF-8?B?' + enc(subj) + '?=',
    'In-Reply-To: ' + mid,
    'References: ' + refs,
    'MIME-Version: 1.0',
    'Content-Type: multipart/alternative; boundary="' + bound + '"',
    '',
    '--' + bound, 'Content-Type: text/plain; charset=UTF-8', 'Content-Transfer-Encoding: base64', '', wrap(enc(m.text)),
    '--' + bound, 'Content-Type: text/html; charset=UTF-8', 'Content-Transfer-Encoding: base64', '', wrap(enc(m.html)),
    '--' + bound + '--', ''
  ].join('\r\n');
  Gmail.Users.Messages.send({ raw: Utilities.base64EncodeWebSafe(mime), threadId: firstMsg.getThread().getId() }, 'me');
}

// ---------------------------------------------------------------- the copy --
function fuEmail(step, c) { return fuBrand().style === 'card' ? fuEs(step, c) : fuAtavia(step, c); }

function fuLink(path, c, step, code) {
  var b = fuBrand(), src = /knot|weddingpro/i.test(c.source || '') ? 'theknot' : 'zola';
  var url = b.site + path + '?utm_source=' + src + '&utm_medium=email&utm_campaign=inquiry-followup-' + step + (code ? '&code=' + code : '');
  return { t: b.host + path + (code ? '?code=' + code : ''), u: url };
}

// Atavia: a personal letter from Lauren, plain Georgia, copper links (same look as the first reply).
function fuAtavia(step, c) {
  var b = fuBrand(), hi = 'Hi ' + (c.first || 'there') + ',';
  var date = c.date ? fuDate(c.date) : '', dateOr = date || 'your date';
  var packages = fuLink('/packages', c, step), sig = b.signer + '\nAtavia Weddings · ' + b.phone + ' · ' + b.host;
  var p;
  if (step === 'd2') {
    p = [hi,
      'Just making sure my note from ' + fuWeekday(c.firstReplyAt) + ' reached you. Emails from wedding sites sometimes land in Promotions.',
      'To help me point you to the right collection: are you leaning toward photography, video, or both?'];
    if (c.code) p.push(['Every collection, with pricing, is here: ', packages, '. Your code ' + c.code.code + ' still takes $' + c.code.amount + ' off any collection through '
      + fuDay(c.code.expires_at) + ', and it is already applied here: ', fuLink('/book/', c, step, c.code.code)]);
    else p.push(['Every collection, with pricing, is here: ', packages]);
    p.push('Just reply to this message or text ' + b.phone + '.');
  } else if (step === 'd3') {
    p = [hi,
      'A quick heads-up: your code ' + c.code.code + ', $' + c.code.amount + ' off any collection, expires ' + fuWhen(c.code.expires_at) + '.',
      ['If you would like to use it, a $500 retainer holds ' + dateOr + ' and takes about two minutes. The code is already applied here: ', fuLink('/book/', c, step, c.code.code)],
      'Not ready yet? That is completely fine. Reply and tell me what you are still weighing, and I will help however I can.'];
  } else if (step === 'd5') {
    p = [hi,
      'I know choosing your team takes time, so I set aside a new code for you: ' + c.fresh.code + ' takes $' + c.fresh.amount + ' off any collection through ' + fuDay(c.fresh.expires_at) + '.',
      ['It is already applied here: ', fuLink('/book/', c, step, c.fresh.code), '. A $500 retainer holds ' + dateOr + ' on our calendar so no one else can book it.'],
      'If a quick call would help, reply with a good time and I will reach out.'];
  } else {
    p = [hi,
      'I do not want to crowd your inbox, so this is my last note.',
      ['If you have found your team, congratulations, and no reply is needed. If you are still deciding, we would love to be there' + (date ? ' on ' + date : '') + '. Every collection is here: ', packages],
      'Reply anytime and I will pick it right back up.'];
  }
  p.push(sig);
  var text = p.map(function (x) { return typeof x === 'string' ? x : x.map(function (y) { return typeof y === 'string' ? y : y.t; }).join(''); }).join('\n\n');
  var html = '<div style="font-family:Georgia,serif;font-size:15px;line-height:1.6;color:#2B2B2B">' + p.map(function (x) {
    var inner = typeof x === 'string' ? fuEsc(x) : x.map(function (y) { return typeof y === 'string' ? fuEsc(y) : '<a href="' + y.u + '" style="color:#B0713F">' + fuEsc(y.t) + '</a>'; }).join('');
    return '<p style="margin:0 0 16px">' + inner + '</p>';
  }).join('') + '</div>';
  return { text: text, html: html };
}

// Elizabeth Scott: the site's navy and champagne card, Playfair headline, "we" from the team.
function fuEs(step, c) {
  var b = fuBrand(), date = c.date ? fuDateShort(c.date) : '';
  var name = c.first ? c.first + ', ' : '';
  var collections = fuLink('/packages', c, step), x;
  if (step === 'd2') {
    x = { h: name + "we're still thinking about " + (date || 'your wedding') + '.',
      p: ['We wanted to be sure our note found you. Messages from wedding sites have a way of slipping into Promotions.',
          'One question helps us tailor everything to you: are you picturing **photography, film, or both?** Whatever you choose, travel is included wherever you celebrate, so the price you see is the price you pay.'],
      code: c.code ? [c.code.code, '$' + c.code.amount + ' off any collection · through ' + fuDay(c.code.expires_at)] : null,
      btn: ['View the collections', collections],
      end: 'Simply reply here. Someone from our team reads every message.' };
  } else if (step === 'd3') {
    x = { h: 'Your $' + c.code.amount + ' thank-you ends ' + fuWhen(c.code.expires_at, true) + '.',
      p: ['A gentle reminder before it slips away: your code is already applied at the link below, and reserving ' + (date || 'your date') + ' takes only a few minutes.'],
      code: [c.code.code, 'expires ' + fuWhen(c.code.expires_at)],
      btn: ['Reserve ' + (date || 'your date'), fuLink('/book/', c, step, c.code.code)],
      end: "Still comparing? We understand completely. Reply with anything you are weighing, whether that's coverage hours, film length or albums, and we will walk you through it." };
  } else if (step === 'd5') {
    x = { h: "We've saved something for you.",
      p: ['Choosing the people who will tell your story deserves time, so we have set aside a fresh thank-you for the two of you. It is good for the next three days.'],
      code: [c.fresh.code, '$' + c.fresh.amount + ' off any collection · through ' + fuDay(c.fresh.expires_at)],
      btn: ['Reserve with your code', fuLink('/book/', c, step, c.fresh.code)],
      end: 'Dates are reserved first-come, and reserving holds ' + (date || 'your date') + ' exclusively for you. If a short call would help you decide, reply with a time that suits you.' };
  } else {
    x = { h: 'Should we keep ' + (date || 'your date') + ' in mind?',
      p: ["We don't want to crowd your inbox, so this will be our last note.",
          "If you've found your team, congratulations, and we wish you a beautiful day. If you are still deciding, we would be honored to be there. Your collections are always one click away."],
      code: null, btn: ['View the collections', collections],
      end: 'Reply anytime and we will pick up right where we left off.' };
  }
  var plain = function (s) { return s.replace(/\*\*/g, ''); };
  var text = [plain(x.h)].concat(x.p.map(plain))
    .concat(x.code ? ['Your code: ' + x.code[0] + ' (' + x.code[1] + ')'] : [])
    .concat([x.btn[0] + ': ' + x.btn[1].u, x.end, b.signer + '\n' + b.email + ' · ' + b.host]).join('\n\n');
  var navy = '#1A2744', champ = '#D8C29A', sans = "Figtree,Helvetica,Arial,sans-serif", serif = "'Playfair Display',Georgia,serif";
  var para = function (s) { return '<p style="margin:0 0 15px">' + fuEsc(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>') + '</p>'; };
  var html = '<div style="background:#F4F7FC;padding:24px 12px">'
    + '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="max-width:560px;margin:0 auto;background:#ffffff;border-radius:6px">'
    + '<tr><td style="background:' + navy + ';text-align:center;padding:22px 16px 18px;border-radius:6px 6px 0 0">'
    + '<div style="font-family:' + serif + ';color:#ffffff;letter-spacing:4px;font-size:15px">ELIZABETH SCOTT</div>'
    + '<div style="width:44px;height:1px;line-height:1px;font-size:1px;background:' + champ + ';margin:10px auto 0">&nbsp;</div></td></tr>'
    + '<tr><td style="padding:26px 28px 8px;font-family:' + sans + ';font-size:15px;line-height:1.65;color:' + navy + '">'
    + '<h1 style="font-family:' + serif + ';font-weight:400;font-style:italic;font-size:23px;line-height:1.3;margin:0 0 16px;color:' + navy + '">' + fuEsc(x.h) + '</h1>'
    + x.p.map(para).join('')
    + (x.code ? '<div style="border:1px solid ' + champ + ';border-radius:4px;text-align:center;padding:12px;margin:4px 0 18px;letter-spacing:2px;font-weight:600">' + fuEsc(x.code[0])
      + '<div style="letter-spacing:0;font-weight:400;color:#5d6880;font-size:13px;margin-top:2px">' + fuEsc(x.code[1]) + '</div></div>' : '')
    + '<div style="text-align:center;margin:6px 0 20px"><a href="' + x.btn[1].u + '" style="display:inline-block;background:' + navy + ';color:' + champ
      + ';text-decoration:none;padding:12px 26px;border-radius:3px;font-size:13px;letter-spacing:1.5px;text-transform:uppercase;font-weight:600">' + fuEsc(x.btn[0]) + '</a></div>'
    + para(x.end)
    + '<div style="border-top:1px solid #e6e9f0;margin-top:8px;padding:16px 0 18px;font-size:13px;color:#5d6880">'
    + '<div style="font-family:' + serif + ';font-size:15px;color:' + navy + '">' + fuEsc(b.signer) + '</div>'
    + '<a href="mailto:' + b.email + '" style="color:#5d6880">' + b.email + '</a> · <a href="' + b.site + '" style="color:#5d6880">' + b.host + '</a></div>'
    + '</td></tr></table></div>';
  return { text: text, html: html };
}

function fuEsc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/\n/g, '<br>'); }
var FU_MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
function fuDate(iso) { var d = new Date(String(iso).slice(0, 10) + 'T12:00:00'); return isNaN(d) ? String(iso) : FU_MONTHS[d.getMonth()] + ' ' + d.getDate() + ', ' + d.getFullYear(); }
function fuDateShort(iso) { var d = new Date(String(iso).slice(0, 10) + 'T12:00:00'); return isNaN(d) ? String(iso) : FU_MONTHS[d.getMonth()] + ' ' + d.getDate(); }
function fuDay(iso) { var d = new Date(iso); return isNaN(d) ? '' : Utilities.formatDate(d, Session.getScriptTimeZone(), 'MMMM d'); }
function fuWeekday(d) { return Utilities.formatDate(new Date(d), Session.getScriptTimeZone(), 'EEEE'); }
/** "today at 2:14 PM" / "tomorrow at 9:00 AM" / "on Sunday at 2:14 PM"; timeFirst gives "at 2:14 PM today". */
function fuWhen(iso, timeFirst) {
  var tz = Session.getScriptTimeZone(), d = new Date(iso), f = function (x, p) { return Utilities.formatDate(x, tz, p); };
  var t = f(d, 'h:mm a'), day = f(d, 'yyyy-MM-dd'), today = f(new Date(), 'yyyy-MM-dd'), tom = f(new Date(Date.now() + 864e5), 'yyyy-MM-dd');
  var w = day === today ? 'today' : day === tom ? 'tomorrow' : 'on ' + f(d, 'EEEE');
  return timeFirst ? 'at ' + t + ' ' + w : w + ' at ' + t;
}
