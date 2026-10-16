// functions-dashboard/join-copy.js
// Build ID: JC-LAZO-FNDASH-1016-JOIN-001
//
// THE "MAKE YOUR FREE ACCOUNT" EMAILS for a client who signed or paid with a
// Lazo vendor without an account (website lead, added by hand). One place for
// the words, so they can be read and changed together. Used by
// couple-notify.js (day 0 rides on the signed / receipt email, so she never
// gets two at once) and join.js (days 3, 7 and 14, and the one text).
//
// Every main button is the claim link: meetlazo.com/join/{inquiry}?t=&s=<step>
// -> join.js joinGo (logs the click) -> app.meetlazo.com signup with her name,
// date and metro filled in and ref=lead:<inquiry>.<token>, which moves this
// thread into her new account (leads.js claimLeadThreads).

'use strict';

const F = require('./email-frame');
const { esc, str, money, frame, facts, steps, tiles, flourish, SITE } = F;

const CAT = { 'wedding-photographers': 'photographer', 'wedding-videographers': 'videographer', 'wedding-venues': 'venue', 'wedding-planners': 'planner', 'wedding-djs': 'DJ', 'wedding-florists': 'florist', 'wedding-caterers': 'caterer', 'wedding-cakes': 'baker', 'hair-and-makeup': 'hair and makeup artist', 'wedding-officiants': 'officiant', 'wedding-bands': 'band', 'wedding-invitations': 'stationer' };

// the links every email needs
function links(inquiryId, inq, step) {
  const id = encodeURIComponent(inquiryId), t = encodeURIComponent(str(inq.fileToken));
  return {
    claim: `${SITE}join/${id}?t=${t}&s=${encodeURIComponent(step)}`,
    stop: `${SITE}join/${id}/stop?t=${t}`,
    page: `${SITE}f/${id}?t=${t}`,
  };
}

// where the claim link finally lands: the app's own signup, pre-filled. The
// keys are the ones Auth v22 / Couple v144+ already read (welcome funnels).
function appUrl(inquiryId, inq, vendor, step, medium) {
  const c = inq.contact || {}, si = inq.structuredIntent || {};
  const q = new URLSearchParams({
    from: 'welcome-booked', intent: 'booked',
    ...(str(c.name || inq.coupleName) ? { names: str(c.name || inq.coupleName).slice(0, 80) } : {}),
    ...(/^\d{4}-\d{2}-\d{2}$/.test(str(si.weddingDate)) ? { date: str(si.weddingDate) } : {}),
    ...(str(vendor && vendor.metroId) ? { metro: str(vendor.metroId) } : {}),
    ref: `lead:${inquiryId}.${str(inq.fileToken)}`,
    utm_source: 'lazo', utm_medium: medium || 'email', utm_campaign: 'join', utm_content: step,
  });
  return `https://app.meetlazo.com/?${q.toString()}`;
}

function ctxOf(inquiryId, inq, vendor, step) {
  const c = inq.contact || {};
  const names = str(c.name || inq.coupleName).trim() || 'there';
  const first = names.split(/\s+/)[0] || 'there';
  const vendorName = str(inq.vendorName || (vendor && vendor.name)) || 'your vendor';
  const slug = str((vendor && (vendor.category || (Array.isArray(vendor.categories) && vendor.categories[0]))) || (inq.structuredIntent && inq.structuredIntent.category));
  const metroId = str(vendor && vendor.metroId);
  const metroName = metroId ? metroId.replace(/-/g, ' ').replace(/\b\w/g, (m) => m.toUpperCase()) : '';
  return { names, first, vendorName, slug, kind: CAT[slug] || 'vendor', metroId, metroName, ...links(inquiryId, inq, step) };
}

const p = (t) => `<p style="margin:0 0 12px;font-family:Helvetica,Arial,sans-serif;font-size:15px;line-height:1.65;color:#241E2B">${t}</p>`;
const h = (t) => `<p style="margin:0 0 4px;font-family:Georgia,'Times New Roman',serif;font-size:22px;line-height:1.25;color:#3D1C3B">${t}</p>`;
const foot = (x, why) => `${why} <a href="${x.stop}" style="color:#8C8291">Stop these emails</a> ·`;

// the pitch: what a free account gives her, this vendor first
function pitch(x) {
  return flourish + h('Keep it all in one free account')
    + p(`Make a free Lazo account and everything with ${esc(x.vendorName)} moves into it. Your name and date are already filled in; it takes about a minute.`)
    + steps([
      [`Everything with ${x.vendorName}`, 'Your signed agreement, every invoice and due date, and your messages in one thread. No more hunting for the link.', 'thread'],
      ['A free wedding website', 'Your story, schedule and registry, with RSVPs that land straight in your guest list. Pick a design and share one link.', 'home'],
      ['June, your planning assistant', 'She reads your real plan and tells you what to do next, drafts messages to vendors and keeps the budget honest.', 'june'],
      [`The rest of your team${x.metroName ? ' in ' + x.metroName : ''}`, 'Verified vendors for everything you still need. Couples message them free, and nobody can buy a better ranking.', 'team'],
    ]);
}

// day 0, after she signs: replaces the plain "It's signed" email
function day0Signed(inquiryId, inq, vendor, contract) {
  const x = ctxOf(inquiryId, inq, vendor, 'day0');
  const total = contract && contract.values && contract.values.total_price != null ? str(contract.values.total_price).replace(/^(?!\$)/, '$') : '';
  const body = facts([['Agreement', str(contract && contract.title) || 'Service agreement'], ['With', x.vendorName], total ? ['Total', total] : ['Signed', 'Both sides']])
    + p(`The signed copy is on <a href="${x.page}" style="color:#52284F">your booking page</a>, where any retainer or payment plan will show up next.`) + pitch(x);
  return {
    subject: `Signed with ${x.vendorName}. Keep it all in one place`,
    html: frame({ preheader: `Your agreement with ${x.vendorName} is signed. Save it to a free Lazo account.`, kicker: 'Signed', title: 'It’s signed.', lede: `${esc(x.first)}, your agreement with ${esc(x.vendorName)} is complete and signed by both sides. One more piece of your day, settled.`, body, cta: 'Create my free account', ctaHref: x.claim, secondary: 'View your booking page', secondaryHref: x.page, footerWhy: foot(x, `You’re getting this because you signed an agreement with ${esc(x.vendorName)} through Lazo.`) }),
    text: `${x.first}, your agreement with ${x.vendorName} is signed by both sides. The copy is on your booking page: ${x.page}\n\nMake a free Lazo account and it all moves in with you: your agreement, invoices and messages with ${x.vendorName}, a free wedding website with RSVPs, June your planning assistant, and verified vendors for the rest of your team. Your name and date are filled in: ${x.claim}\n\nStop these emails: ${x.stop}`,
  };
}

// day 0, after her first payment (when nothing was signed first): the receipt itself
function day0Paid(inquiryId, inq, vendor, inv, openSum, viaTxt) {
  const x = ctxOf(inquiryId, inq, vendor, 'day0');
  const total = +inv.total || 0;
  const body = facts([['Paid', money(total)], ['To', x.vendorName], [openSum ? 'Still open' : 'Paid to date', money(openSum || total)]])
    + p(`${esc(str(inv.title) || 'Invoice')}${viaTxt ? ', ' + esc(viaTxt) : ''}. ${openSum ? `${money(openSum)} remains; each payment shows up on <a href="${x.page}" style="color:#52284F">your booking page</a> when it’s due.` : `It’s recorded on <a href="${x.page}" style="color:#52284F">your booking page</a>.`}`) + pitch(x);
  return {
    subject: `Receipt: ${money(total)} to ${x.vendorName}`,
    html: frame({ preheader: `${money(total)} to ${x.vendorName}, received. Keep your receipts in a free Lazo account.`, kicker: 'Receipt', title: 'Payment received.', lede: `Thank you, ${esc(x.first)}. Your payment to ${esc(x.vendorName)} went through.`, body, cta: 'Create my free account', ctaHref: x.claim, secondary: 'View your booking page', secondaryHref: x.page, signoff: 'Keep this for your records.', footerWhy: foot(x, 'You’re getting this because you made a payment through Lazo.') }),
    text: `Payment received: ${money(total)} to ${x.vendorName} (${str(inv.title) || 'Invoice'}).${openSum ? ' ' + money(openSum) + ' remains.' : ''} Booking page: ${x.page}\n\nKeep every receipt, your agreement and your messages with ${x.vendorName} in a free Lazo account, with a free wedding website, RSVPs and June: ${x.claim}\n\nStop these emails: ${x.stop}`,
  };
}

// day 3: the website
function day3(inquiryId, inq, vendor) {
  const x = ctxOf(inquiryId, inq, vendor, 'day3');
  const body = p(`With ${esc(x.vendorName)} booked, most couples need a website next: where to be, when, what to wear, and a way to RSVP. On Lazo it’s free, and it’s ready in minutes.`)
    + tiles([['atmo-veil.jpg', 'Your story', x.claim], ['atmo-toast.jpg', 'The schedule', x.claim], ['atmo-firstdance.jpg', 'RSVPs', x.claim]])
    + p('Pick a design, add your story and the day’s schedule, and share one link. RSVPs land straight in your guest list, and a passcode keeps it private if you want.')
    + p(`Your booking with ${esc(x.vendorName)} comes with you when you join.`);
  return {
    subject: `${x.first}, your wedding website is free on Lazo`,
    html: frame({ preheader: 'A free wedding website, RSVPs included, ready in minutes.', kicker: 'Your website', title: 'Your wedding website, free.', lede: `${esc(x.first)}, one link for your guests: the story, the schedule and the RSVP.`, body, cta: 'Make my free account', ctaHref: x.claim, secondary: 'Your booking page', secondaryHref: x.page, footerWhy: foot(x, `You’re getting this because you booked ${esc(x.vendorName)} through Lazo.`) }),
    text: `${x.first}, with ${x.vendorName} booked, most couples need a website next. On Lazo it's free: your story, the schedule, and RSVPs that land in your guest list. Your booking comes with you: ${x.claim}\n\nStop these emails: ${x.stop}`,
  };
}

// day 7: June and the guest list
function day7(inquiryId, inq, vendor) {
  const x = ctxOf(inquiryId, inq, vendor, 'day7');
  const body = p('June is the planning assistant inside Lazo. She works from your actual plan, not a generic checklist:')
    + steps([
      ['What to do next', `She knows ${x.vendorName} is booked and what’s still open, and tells you the next thing worth doing this week.`, 'june'],
      ['Guests without the spreadsheet', 'Your guest list, RSVPs, meals and seating in one place. Guests answer from your website and the list updates itself.', 'home'],
      ['Every vendor in one inbox', 'Messages, proposals, agreements and payments for your whole team, side by side.', 'thread'],
    ])
    + p('All of it is free for couples.');
  return {
    subject: 'Meet June, the planner who reads your actual plan',
    html: frame({ preheader: 'June knows what you’ve booked and what’s next. Free for couples.', kicker: 'Meet June', title: 'Planning, with help.', lede: `${esc(x.first)}, you’ve got ${esc(x.vendorName)}. June can help with everything after that.`, body, cta: 'Make my free account', ctaHref: x.claim, secondary: 'Your booking page', secondaryHref: x.page, footerWhy: foot(x, `You’re getting this because you booked ${esc(x.vendorName)} through Lazo.`) }),
    text: `${x.first}, June is the free planning assistant inside Lazo. She knows ${x.vendorName} is booked and what's still open, keeps your guest list and RSVPs, and puts every vendor in one inbox: ${x.claim}\n\nStop these emails: ${x.stop}`,
  };
}

// day 14: the rest of the team, in her city
function day14(inquiryId, inq, vendor) {
  const x = ctxOf(inquiryId, inq, vendor, 'day14');
  const base = x.metroId ? `${SITE}vendors/${encodeURIComponent(x.metroId)}/` : `${SITE}vendors/`;
  const all = [['wedding-photographers', 'wedding-photographers.jpg', 'Photographers'], ['wedding-florists', 'wedding-florists.jpg', 'Florists'], ['wedding-cakes', 'wedding-cakes.jpg', 'Cakes'], ['wedding-venues', 'wedding-venues.jpg', 'Venues']];
  const pick = all.filter((c) => c[0] !== x.slug).slice(0, 3).map((c) => [c[1], c[2], base + c[0] + '/']);
  const body = p(`You’ve got your ${esc(x.kind)}. On Lazo you can find the rest of your team${x.metroName ? ' in ' + esc(x.metroName) : ''}: verified vendors, real starting prices, and messages that sit next to your booking with ${esc(x.vendorName)}.`)
    + tiles(pick)
    + p('Verification is free and never for sale, so the vendors at the top earned it. Message as many as you like; it costs couples nothing.');
  return {
    subject: `${x.first}, who’s still on your list?`,
    html: frame({ preheader: `Verified vendors${x.metroName ? ' in ' + x.metroName : ''} for everything you still need.`, kicker: 'Your team', title: 'Who’s still on the list?', lede: `${esc(x.first)}, ${esc(x.vendorName)} is one piece. Here’s the rest.`, body, cta: 'Make my free account', ctaHref: x.claim, secondary: 'Browse vendors', secondaryHref: base, footerWhy: foot(x, `You’re getting this because you booked ${esc(x.vendorName)} through Lazo. This is the last one.`) }),
    text: `${x.first}, you've got your ${x.kind}. Find the rest of your team${x.metroName ? ' in ' + x.metroName : ''} on Lazo - verified vendors, free for couples to message: ${x.claim}\n\nThis is the last of these emails.`,
  };
}

// she signed up with the right email but hasn't confirmed it: one tap finishes the claim
function verifyEmail(inquiryId, inq, vendor, link) {
  const x = ctxOf(inquiryId, inq, vendor, 'verify');
  const body = p(`Tap the button to confirm this is your email. Your agreement, payments and messages with ${esc(x.vendorName)} then move into your new Lazo account.`)
    + p(`<span style="color:#8A7F90;font-size:13px">Didn’t make a Lazo account? Ignore this email and nothing changes.</span>`);
  return {
    subject: `Confirm your email to bring your booking with ${x.vendorName} into Lazo`,
    html: frame({ preheader: `One tap and your booking with ${x.vendorName} is in your account.`, kicker: 'One more step', title: 'Confirm your email.', lede: `${esc(x.first)}, your Lazo account is ready.`, body, cta: 'Confirm my email', ctaHref: link, footerWhy: 'You’re getting this because someone made a Lazo account with this email.' }),
    text: `${x.first}, confirm your email and your booking with ${x.vendorName} moves into your new Lazo account: ${link}\n\nDidn't make a Lazo account? Ignore this email and nothing changes.`,
  };
}

// she signed up with a different address (or an Apple private relay): nothing moved
function wrongEmail(inquiryId, inq, vendor, masked, relay) {
  const x = ctxOf(inquiryId, inq, vendor, 'retry');
  const why = relay
    ? `You signed up with Apple’s private email, so we can’t match your account to your booking with ${esc(x.vendorName)}.`
    : `Your new Lazo account uses a different email from the one ${esc(x.vendorName)} has for you, so your booking stayed where it is.`;
  const body = p(why)
    + p(`Make your account with <b>${esc(masked)}</b>, the email ${esc(x.vendorName)} has for you${relay ? ', using email and a password or Google' : ''}. Your booking moves in as soon as that email is confirmed.`)
    + p(`<span style="color:#8A7F90;font-size:13px">Your booking page still works in the meantime.</span>`);
  return {
    subject: `Your booking with ${x.vendorName} is still waiting`,
    html: frame({ preheader: `Use the email ${x.vendorName} has for you: ${masked}`, kicker: 'Almost there', title: 'Use the email your vendor has.', lede: `Hi ${esc(x.first)}, one thing before your booking can move in.`, body, cta: 'Try again', ctaHref: x.claim, secondary: 'Your booking page', secondaryHref: x.page, footerWhy: 'You’re getting this because you made a Lazo account from a booking link.' }),
    text: `${relay ? `You signed up with Apple's private email, so we can't match your account to your booking with ${x.vendorName}.` : `Your new Lazo account uses a different email from the one ${x.vendorName} has for you, so your booking stayed where it is.`} Make your account with ${masked}, the email ${x.vendorName} has for you: ${x.claim}`,
  };
}

// the one text, only where the lead form recorded consent
function sms(inquiryId, inq, vendor) {
  const x = ctxOf(inquiryId, inq, vendor, 'sms');
  return `Lazo: you're all set with ${x.vendorName}! Keep your agreement, payments and wedding plans in one free account: ${x.claim} Reply STOP to opt out.`;
}

const NEXT = { day0: ['day3', 3], day3: ['day7', 4], day7: ['day14', 7] };
module.exports = { appUrl, links, day0Signed, day0Paid, day3, day7, day14, verifyEmail, wrongEmail, sms, NEXT, STEPS: { day3, day7, day14 } };
