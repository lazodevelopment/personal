// Checks offplatform.js (JC-LAZO-SAFETY-1016-002): real wedding messages that
// must go through, scam openers that must be held, and the firestore.rules
// floor regex staying a strict subset of scan() 'strong'.
//   node test/offplatform-scan.js      (from functions-dashboard)
'use strict';
const { scan, verdict, RULES_FLOOR } = require('../offplatform');

let pass = 0, fail = 0;
function ok(cond, label) { if (cond) pass++; else { fail++; console.log('FAIL', label); } }

// ---- must pass untouched (not early, so contact rules don't apply)
const CLEAN = [
  'Hi! We love your work. Do you have June 14, 2027 open?',
  'Do you shoot with a zoom lens for the ceremony?',
  'Can you zoom in on the rings during the vows?',
  'We want a mix of wide and zoom shots.',
  'Our teams of bridesmaids will be getting ready at the hotel.',
  'Could we meet in person at the venue next week?',
  'Happy to meet at the venue for a walkthrough.',
  'What is your package price? Our budget is $4,500.',
  'The date is 10/16/2027 and we expect 140 guests.',
  'Is the $12,000 package all-inclusive?',
  'We saw a signal from the universe that you are the one!',
  'Our wedding hashtag is #AveryAndJordan2027',
  'Can you do drone footage? Our venue is on a lake.',
  'We are flying in from Telluride on Thursday.',
  'Do you face timing issues with sunset ceremonies?',
];
for (const t of CLEAN) {
  const v = verdict(t, { early: false });
  ok(!v.hold, `clean held: "${t}" -> ${JSON.stringify(v.strong.concat(v.weak))}`);
}

// ---- strong (outside app) - held and a strike
const STRONG = [
  "Hi, let's get on a zoom call first to discuss",
  'Can we do a Zoom meeting tomorrow?',
  'Here is my link https://us02web.zoom.us/j/8123456789',
  'Join me on zoom at 3pm',
  'Lets hop on Google Meet',
  'meet.google.com/abc-defg-hij',
  'Can you FaceTime me?',
  'Text me on WhatsApp please',
  'Message me on whats app',
  'my telegram is @bride2027',
  'add me on skype',
  'can we do a teams call',
  'Lets talk on Signal',
  'z o o m call?',
  'zo0m call tomorrow?',
  'wa.me/14805551212',
  'add me on discord',
  'Can we set up a webex',
];
for (const t of STRONG) {
  const v = verdict(t, { early: false });
  ok(v.hold && v.strike && v.reason === 'video', `strong missed: "${t}" -> ${JSON.stringify(v)}`);
}

// ---- weak (generic video) - held, no strike
const WEAK = [
  'Can we do a video call this week?',
  'Would love to hop on a quick call',
  'Could we have a virtual meeting first?',
  'Is a video chat possible?',
];
for (const t of WEAK) {
  const v = verdict(t, { early: false });
  ok(v.hold && !v.strike && v.reason === 'video', `weak missed: "${t}" -> ${JSON.stringify(v)}`);
}

// ---- contact - held only early, never a strike
const CONTACT = [
  'Call me at (480) 555-1212',
  'my number is 480.555.1212',
  'text 4805551212',
  'reach me at +1 480 555 1212',
  'email me avery.j@gmail.com',
  'avery at gmail dot com',
  'four eight zero five five five one two one two',
];
for (const t of CONTACT) {
  const early = verdict(t, { early: true });
  const late = verdict(t, { early: false });
  ok(early.hold && !early.strike && early.reason === 'contact', `contact early missed: "${t}" -> ${JSON.stringify(early)}`);
  ok(!late.hold, `contact late held: "${t}"`);
}

// ---- rules floor: catches the plain cases, never fires on clean text, and
// everything it catches scan() also calls strong
const floor = new RegExp(RULES_FLOOR.replace(/^\(\?is\)/, ''), 'is');
const FLOOR_MUST = [
  "let's get on a zoom call", 'https://us02web.zoom.us/j/1', 'meet.google.com/x', 'facetime me', 'whatsapp me',
  'add me on skype', 'telegram?', 'join on zoom.', 'google meet tomorrow',
];
for (const t of FLOOR_MUST) ok(floor.test(t.toLowerCase()), `floor missed: "${t}"`);
for (const t of CLEAN.concat(WEAK, CONTACT)) ok(!floor.test(t.toLowerCase()), `floor false hit: "${t}"`);
for (const t of STRONG.concat(FLOOR_MUST)) if (floor.test(t.toLowerCase())) ok(scan(t).level === 'strong', `floor hit not strong in scan: "${t}"`);
ok(!/\(\?<|\(\?[=!]/.test(RULES_FLOOR), 'floor uses lookaround (RE2 has none)');

console.log(`${pass}/${pass + fail} pass`);
process.exit(fail ? 1 : 0);
