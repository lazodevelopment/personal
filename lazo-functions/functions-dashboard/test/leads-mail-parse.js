// Local check of the leads@ parser: three forwarded inquiries (Knot, Zola, a plain email) and one
// non-inquiry. Needs ANTHROPIC_API_KEY in the environment; prints only what June extracted.
//   ANTHROPIC_API_KEY=... node test/leads-mail-parse.js
'use strict';
const lm = require('../leads-mail');

const KNOT = `---------- Forwarded message ---------
From: The Knot <noreply@theknot.com>
Date: Sat, Oct 18, 2026 at 9:02 AM
Subject: New inquiry: Maya Chen is interested in Golden Hour Studio
To: riley@goldenhourstudio.com

You have a new inquiry on The Knot!
Maya Chen
Wedding date: March 7, 2027
Guest count: 120
Event location: The Farm at South Mountain, Phoenix, AZ
Message: Hi Riley! We love your warm, candid style - are you free on our date? We'd like 8 hours of coverage and an engagement session if possible.
Reply to Maya: maya.chen88@gmail.com | (602) 555-0142
Manage your leads in your Knot Vendor dashboard. Unsubscribe.`;

const ZOLA = `Fwd: Zola inquiry from Priya & Sam
From: Zola Vendors <vendors@zola.com>
Priya & Sam sent you a message on Zola
"We're planning a May 6, 2027 wedding at Hotel Valley Ho for about 90 guests. Budget around $4,500 for photography. Could we set up a call?"
Email: priya.s@outlook.com
Respond within 24 hours to keep your response rate high.`;

const PLAIN = `Subject: Photography availability
Hi there, my name is Nora Eli and my fiance and I are getting married on 2026-11-05 at Desert Botanical Garden. Are you available? You can reach me at 480-555-0199. Thanks, Nora`;

const NOTINQ = `Fwd: Your Knot invoice for October
Thank you for your payment of $249.00 for Storefront Plus. View your receipt in your dashboard.`;

(async () => {
  const key = process.env.ANTHROPIC_API_KEY;
  if (!key) { console.error('set ANTHROPIC_API_KEY'); process.exit(1); }
  const cases = [['knot', 'New inquiry: Maya Chen', KNOT], ['zola', 'Fwd: Zola inquiry from Priya & Sam', ZOLA], ['plain', 'Photography availability', PLAIN], ['not-an-inquiry', 'Fwd: Your Knot invoice', NOTINQ]];
  let ok = 0;
  for (const [label, subject, body] of cases) {
    const p = await lm.parseInquiry(key, 'Golden Hour Studio', 'riley@goldenhourstudio.com', subject, lm.stripHtml(body));
    const platform = lm.platformOf(body, subject);
    const accepted = p.name && p.confidence >= 0.4 && (p.email || p.phone || p.message);
    const expectAccept = label !== 'not-an-inquiry';
    const pass = !!accepted === expectAccept;
    ok += pass ? 1 : 0;
    console.log((pass ? 'pass' : 'FAIL'), label, '| platform', platform, '| name', JSON.stringify(p.name), '| email', p.email, '| phone', p.phone, '| date', p.weddingDate, '| venue', p.venue, '| guests', p.guests, '| budget', p.budget, '| conf', p.confidence);
    if (accepted) console.log('      message:', p.message.slice(0, 120));
  }
  console.log(`${ok}/${cases.length} passed`);
  process.exit(ok === cases.length ? 0 : 1);
})();
