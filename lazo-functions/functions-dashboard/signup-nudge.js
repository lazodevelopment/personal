// functions-dashboard/signup-nudge.js
// Build ID: JC-LAZO-FNDASH-1018-SIGNUPNUDGE
//
// ABANDONED SIGN-UP. Someone creates an account and never finishes: the
// account never picks couple or vendor (no users.role), a couple never reaches "Make it yours"
// (no couples/{uid} doc), a vendor never claims or creates a listing (no
// users.vendorId). Until now nobody heard from Lazo again. One sweep, 10:00
// Phoenix daily:
//
//   users created >= 1 day ago, not finished  -> nudge 1 ("you're one step away")
//   users created >= 4 days ago, still not    -> nudge 2 ("your plan is still here"),
//                                                then nothing more.
//
// Finished means: couple -> couples/{uid} exists; vendor -> users.vendorId set.
// Skipped: demo/preview/test accounts, anyone with no email, accounts older than
// 30 days (they were created before the sweep existed or are long gone).
// Idempotent through users.signupNudge = { n, at }. Branded through email-frame.
// The deep links go back to the app, where the Auth widget routes a signed-in
// user straight to the step they left (verify code, Make it yours, vendor home).

'use strict';

const { onSchedule } = require('firebase-functions/v2/scheduler');
const admin = require('firebase-admin');
const { FieldValue, Timestamp } = require('firebase-admin/firestore');

module.exports = function signupNudge(RESEND_API_KEY) {
  const db = () => admin.firestore();
  const { frame, esc, str, APP, DASH, JUNE } = require('./email-frame');
  const emailOk = (e) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(str(e).trim());
  const FROM = 'The Lazo Team <hello@meetlazo.com>';
  const DAY = 86400e3;

  async function sendEmail(to, subject, html, text) {
    const r = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${RESEND_API_KEY.value()}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ from: FROM, to: [to], reply_to: 'hello@meetlazo.com', subject, html, text }),
    });
    if (!r.ok) throw new Error(`resend ${r.status}: ${await r.text()}`);
  }

  function firstName(s) { const t = str(s).trim(); return t ? t.split(/\s+/)[0] : ''; }

  // what is left for this user, as a word the copy can use
  // No separate "enter the code" stage: the app routes a signed-in user to the code step by itself,
  // and users.emailVerifiedAt only exists for accounts made after the verify flow shipped.
  function stage(u, hasCouple) {
    const role = str(u.role);
    if (role === 'vendor') return u.vendorId ? 'done' : 'listing';
    if (role === 'couple') return hasCouple ? 'done' : 'plan';
    return hasCouple ? 'done' : 'role';   // never said couple or vendor
  }

  function email(u, st, n) {
    const who = firstName(u.display_name || u.displayName);
    const hi = who ? `${esc(who)}, ` : '';
    const vendor = str(u.role) === 'vendor';
    let subject, title, lede, body, cta, ctaHref, preheader;
    if (st === 'role') {
      subject = n === 1 ? 'One step left on your Lazo account' : 'Your Lazo account is still waiting';
      preheader = 'Planning a wedding, or working them? Tell us which and Lazo sets up the right side for you.';
      title = `${hi}your account is almost there.`;
      lede = 'You created a Lazo account but never told us which side you are on. Planning a wedding? Lazo gives you a checklist, a budget, verified vendors near you and June to keep it straight. Working weddings? Claim your listing and leads come to you by text, no pay-to-play.';
      body = `<p style="margin:0 0 18px;font-family:Helvetica,Arial,sans-serif;font-size:15px;line-height:1.65;color:#241E2B">Sign in and pick one. It takes under a minute, and everything after that is built around your answer.</p>`;
      cta = 'Finish signing up'; ctaHref = APP;
    } else if (vendor) {
      subject = n === 1 ? 'Your Lazo listing is one step away' : 'Couples in your area are looking. Your listing is still blank';
      preheader = 'Claim or create your listing and leads come to you by text and email. No pay-to-play.';
      title = `${hi}your listing is one step away.`;
      lede = 'You signed up as a vendor but never claimed or created a listing, so couples cannot find you yet. It takes a few minutes: your name, your category, your city, a few photos and a starting price.';
      body = `<p style="margin:0 0 18px;font-family:Helvetica,Arial,sans-serif;font-size:15px;line-height:1.65;color:#241E2B">Lazo ranks on verified reviews from real bookings, nothing else. Leads reach you by text, every one of them has a wedding date and a budget, and June answers them for you when you are busy.</p>`;
      cta = 'Finish your listing'; ctaHref = DASH;
    } else {
      subject = n === 1 ? 'Your wedding plan is one step away' : 'Your Lazo plan is still here';
      preheader = 'Tell us your date and your city and Lazo builds the plan around them.';
      title = `${hi}your plan is one step away.`;
      lede = 'You created a Lazo account but never told us your wedding date, so there is nothing to plan around yet. Add the date and the city (both can change later) and Lazo gives you a checklist, a budget, verified vendors near you and June to keep it all straight.';
      body = `<p style="margin:0 0 18px;font-family:Helvetica,Arial,sans-serif;font-size:15px;line-height:1.65;color:#241E2B">Every vendor on Lazo is verified and ranked by reviews from real bookings. No one pays for position, so what you see is what couples actually booked.</p>`;
      cta = 'Finish setting up'; ctaHref = APP;
    }
    const signoff = n === 2
      ? 'This is the last note from us about it. If you changed your mind, no reply is needed. If something got in the way, reply to this email; it reaches a person.'
      : 'Stuck on something? Reply to this email. It reaches a person.';
    const html = frame({ preheader, kicker: n === 1 ? 'One step left' : 'Still here', title, lede, body, cta, ctaHref, secondary: 'Ask June anything', secondaryHref: JUNE, signoff, hero: vendor ? 'hero-1.jpg' : 'hero-2.jpg', heroAlt: vendor ? 'A wedding on Lazo' : 'A couple on their wedding day', footerWhy: 'You are getting this because you created a Lazo account and did not finish setting it up.' });
    const text = `${title}\n\n${lede.replace(/<[^>]+>/g, '')}\n\n${cta}: ${ctaHref}\n\n${signoff}`;
    return { subject, html, text };
  }

  const signupNudgeSweep = onSchedule({ schedule: '0 10 * * *', timeZone: 'America/Phoenix', memory: '512MiB', timeoutSeconds: 300, secrets: [RESEND_API_KEY] }, async () => {
    const now = Date.now();
    const oldest = Timestamp.fromMillis(now - 30 * DAY);
    const newest = Timestamp.fromMillis(now - 1 * DAY);
    const snap = await db().collection('users').where('created_time', '>=', oldest).where('created_time', '<=', newest).limit(500).get();
    let sent = 0, done = 0, skipped = 0;
    for (const d of snap.docs) {
      const u = d.data() || {};
      const uid = d.id;
      if (uid.startsWith('demo_') || u.demo === true || u.preview === true || u.test === true) { skipped++; continue; }
      const prev = u.signupNudge && typeof u.signupNudge === 'object' ? u.signupNudge : null;
      if (prev && Number(prev.n) >= 2) { skipped++; continue; }
      const age = now - (u.created_time && u.created_time.toMillis ? u.created_time.toMillis() : now);
      const n = prev ? 2 : 1;
      if (n === 2 && age < 4 * DAY) { skipped++; continue; }
      const hasCouple = str(u.role) !== 'vendor' ? (await db().collection('couples').doc(uid).get()).exists : false;
      const st = stage(u, hasCouple);
      if (st === 'done') { done++; continue; }
      const to = str(u.email).trim();
      if (!emailOk(to)) { skipped++; continue; }
      // claim first so two runs never send twice
      const claimed = await db().runTransaction(async (tx) => {
        const s = await tx.get(d.ref);
        const cur = s.get('signupNudge');
        if (cur && Number(cur.n) >= n) return false;
        tx.update(d.ref, { signupNudge: { n, at: FieldValue.serverTimestamp(), stage: st } });
        return true;
      });
      if (!claimed) continue;
      const m = email(u, st, n);
      try { await sendEmail(to, m.subject, m.html, m.text); sent++; }
      catch (e) { console.error('signupNudge', uid, e.message); await d.ref.update({ signupNudge: prev || FieldValue.delete() }).catch(() => {}); }
    }
    console.log(`signupNudgeSweep: ${snap.size} candidates, ${sent} sent, ${done} finished, ${skipped} skipped`);
  });

  return { signupNudgeSweep, _render: { email, stage } };
};

// END OF FILE - JC-LAZO-FNDASH-1018-SIGNUPNUDGE
