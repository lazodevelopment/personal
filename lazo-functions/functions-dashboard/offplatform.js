// functions-dashboard/offplatform.js
// Build ID: JC-LAZO-SAFETY-1016-002
//
// "LET'S GET ON A ZOOM CALL" - THE PATTERN.
//
// A sextortion scam is working its way through wedding vendors on Zola and The
// Knot: a fake couple gets the vendor onto an outside video call, plays porn on
// their own camera, screenshots it and demands money. Every version starts the
// same way, with a "couple" asking to move to Zoom / Meet / FaceTime / WhatsApp
// in the first message or two. Lazo has its own in-thread video call, so a
// couple never needs an outside one.
//
// scan(text) sorts a message into:
//   strong   an outside call app or a link to one (zoom.us, "zoom call",
//            Google Meet, FaceTime, WhatsApp, Telegram, Skype, Teams call,
//            Signal, Webex, Whereby, Duo, Discord). Held, and counts as a strike.
//   weak     a generic video request ("video call", "hop on a call"). Held
//            with the nudge, never a strike.
//   contact  a phone number or email address. Held only in a couple's early
//            messages (Jesse, 2026-10-16), never a strike.
// Words that only look alike are left alone: "zoom lens", "zoom in", "our
// teams", "meet in person", "signal".
//
// Jesse's decisions (2026-10-16): auto-block on (a) a strong hit in the first
// message from an account under 7 days old, (b) a second strong hit within 30
// days, (c) strong hits to 2+ vendors within 24 hours. Video requests are held
// with a nudge. Phone numbers and emails are held in early messages. Vendors
// are warned, never filtered or blocked. A blocked couple sees "account under
// review".
//
// RULES_FLOOR is the same "strong" idea as one RE2 regex for firestore.rules,
// so old app versions that write messages directly are refused too. It is
// narrower than scan() (no leetspeak, no spacing tricks); sendThreadMessage
// and safetyPrecheck catch the rest.

'use strict';

const EARLY_MESSAGES = 3;          // a couple's first N messages in a thread are "early"
const NEW_ACCOUNT_DAYS = 7;
const STRIKE_WINDOW_DAYS = 30;
const SPRAY_WINDOW_HOURS = 24;
const SPRAY_VENDORS = 2;

// ------------------------------------------------------------ patterns ----
// Raw text (lowercased). Links first: unambiguous.
const LINK_RX = /\b(?:[a-z0-9-]+\.)*(?:zoom\.us|zoom\.com|zoomgov\.com|meet\.google\.com|g\.co\/meet|duo\.google\.com|teams\.microsoft\.com|teams\.live\.com|wa\.me|chat\.whatsapp\.com|whatsapp\.com|t\.me|telegram\.me|telegram\.org|skype\.com|join\.skype\.com|webex\.com|whereby\.com|signal\.me|signal\.group|facetime\.apple\.com|discord\.gg|discord\.com\/invite)\b/i;

const STRONG_RX = [
  // zoom, only when it is the app: "on/via/over zoom", "zoom call/meeting/link/..."
  /\b(?:on|via|over|through|thru|using|use|do|join|send|a quick)\s+(?:a\s+)?zoom\b(?!\s*(?:lens|lenses|in\b|out\b|shot|shots|level|ed\b))/i,
  /\bzoom\s*(?:call|calls|meeting|meetings|link|links|chat|meet|id|invite|session|room|consult|consultation)\b/i,
  /\bgoogle\s*meet\b|\bg-?meet\b|\bgoogle\s*hangouts?\b|\bhangouts?\s*(?:call|link)\b/i,
  /\bface\s*time\b|\bfacetime\b/i,
  /\bwhats\s*app\b|\bwhatsapp\b|\bwatsapp\b/i,
  /\btelegram\b/i,
  /\bskype\b/i,
  /\b(?:ms|microsoft)\s*teams\b|\bteams\s*(?:call|meeting|link|chat|invite)\b|\bon\s+teams\b/i,
  /\bsignal\s*(?:app|call|video|chat|me)\b|\bon\s+signal\b/i,
  /\bwebex\b|\bwhereby\b|\bgoogle\s*duo\b|\bduo\s*call\b/i,
  /\bdiscord\b/i,
];

const WEAK_RX = [
  /\b(?:video|vid|virtual|online|facetime)\s*(?:call|calls|chat|chats|meeting|meetings|consult|consultation|session)\b/i,
  /\b(?:hop|jump|get|hope)\s+on\s+(?:a\s+)?(?:quick\s+)?(?:video\s+|phone\s+)?call\b/i,
  /\bcam\s*(?:call|chat)\b|\bon\s+camera\b|\bon\s+cam\b/i,
  /\bsee\s+(?:each\s+other|you)\s+on\s+(?:video|camera|screen)\b/i,
];

// Squashed text (letters and digits only, light leetspeak undone) catches
// "z o o m", "z.o.o.m", "zo0m call", "whats-app". Only words that are never
// innocent when glued together belong here.
const SQUASH_STRONG = [
  'zoomus', 'zoomcall', 'zoommeeting', 'zoomlink', 'zoomchat', 'zoomid', 'zoominvite',
  'googlemeet', 'meetgoogle', 'facetime', 'whatsapp', 'telegram', 'skype',
  'teamscall', 'teamsmeeting', 'msteams', 'microsoftteams', 'signalapp', 'webex', 'whereby',
  'googleduo', 'discord',
];

const EMAIL_RX = /[a-z0-9._%+-]+\s*(?:@|\(at\)|\[at\]|\sat\s)\s*[a-z0-9-]+\s*(?:\.|\(dot\)|\[dot\]|\sdot\s)\s*(?:com|net|org|co|us|io|me|edu|gov|info|biz|icloud|gmail)\b/i;
// US-style numbers: (480) 555-1212, 480.555.1212, 480 555 1212, +1 480 555 1212,
// 4805551212. Not dates (slashes) and not prices ($, commas).
const PHONE_RX = /(?<![\d$,.\/])(?:\+?1[\s.-]?)?\(?[2-9]\d{2}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?![\d\/])/;
// "four eight zero five five five ..." - seven or more spelled digits in a row
const SPELLED_DIGITS_RX = /\b(?:(?:zero|oh|one|two|three|four|five|six|seven|eight|nine)[\s,.-]*){7,}/i;

function squash(text) {
  return String(text || '').toLowerCase()
    .replace(/0/g, 'o').replace(/3/g, 'e').replace(/4/g, 'a').replace(/5/g, 's').replace(/\$/g, 's')
    .replace(/[^a-z]/g, '');
}

// scan(text) -> { level: 'strong'|'weak'|'contact'|null, strong:[], weak:[], contact:[] }
function scan(text) {
  const raw = String(text || '');
  const out = { level: null, strong: [], weak: [], contact: [] };
  if (!raw.trim()) return out;
  const m = raw.match(LINK_RX);
  if (m) out.strong.push(m[0].toLowerCase());
  for (const rx of STRONG_RX) { const h = raw.match(rx); if (h) out.strong.push(h[0].toLowerCase().replace(/\s+/g, ' ').trim()); }
  if (!out.strong.length) {
    const sq = squash(raw);
    for (const w of SQUASH_STRONG) if (sq.includes(w)) { out.strong.push(w); break; }
  }
  for (const rx of WEAK_RX) { const h = raw.match(rx); if (h) out.weak.push(h[0].toLowerCase().replace(/\s+/g, ' ').trim()); }
  const em = raw.match(EMAIL_RX); if (em) out.contact.push('email');
  if (PHONE_RX.test(raw) || SPELLED_DIGITS_RX.test(raw)) out.contact.push('phone');
  out.level = out.strong.length ? 'strong' : out.weak.length ? 'weak' : out.contact.length ? 'contact' : null;
  return out;
}

// What a couple's message gets: hold or deliver. `early` = within their first
// EARLY_MESSAGES in this thread.
function verdict(text, { early }) {
  const s = scan(text);
  const video = s.level === 'strong' || s.level === 'weak';
  const hold = video || (!!early && s.contact.length > 0);
  const reason = video ? 'video' : hold ? 'contact' : null;
  return { ...s, hold, reason, strike: s.level === 'strong' };
}

// The couple-facing words. Kept here so the app, the callable and the tests agree.
const NUDGE = {
  video: 'Video calls happen inside Lazo, so you and your vendor are both protected. Tap "Request a Lazo video call" and they’ll get it right in this thread.',
  contact: 'Let’s keep the first few messages inside Lazo. Your vendor can reply right here, and you can request a Lazo video call any time. Once you’re talking, you can share contact details.',
  review: 'Your account is under review. Contact support@meetlazo.com and we’ll sort it out.',
};
const VENDOR_WARNING = 'Outside video links aren’t protected. Lazo has its own video call: the couple’s camera stays off until you allow it, and every call is logged. Use "Start a Lazo video call" instead.';
// What a vendor is told when we block an account that wrote to them.
const VENDOR_BLOCK_NOTICE = 'Lazo safety: we blocked the account that wrote to you here. It tried to move you to an outside video call, which is how a known scam against wedding vendors starts. Please don’t join any call or link from them. Nothing else is needed from you.';

// RE2 for firestore.rules (no lookbehind/lookahead; (?i) is supported).
// Must stay a strict subset of scan() 'strong' - test/offplatform-scan.js checks that.
const RULES_FLOOR = '(?is).*(zoom\\.us|meet\\.google\\.com|teams\\.microsoft\\.com|teams\\.live\\.com|wa\\.me/|chat\\.whatsapp\\.com|t\\.me/|whereby\\.com|webex\\.com|facetime|whats ?app|telegram|skype|google meet|zoom (call|meeting|link|chat|id|invite)|(on|via|over) zoom( |[.,!?]|$)).*';

module.exports = {
  scan, verdict, squash, NUDGE, VENDOR_WARNING, VENDOR_BLOCK_NOTICE, RULES_FLOOR,
  EARLY_MESSAGES, NEW_ACCOUNT_DAYS, STRIKE_WINDOW_DAYS, SPRAY_WINDOW_HOURS, SPRAY_VENDORS,
};

// END OF FILE - JC-LAZO-SAFETY-1016-002
