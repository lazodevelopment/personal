// JC-LAZO-FN-1007-RESTORE: recovered from the 2026-09-21 production build (the local tree never had it).
// Lazo — closing the gap between claimed and activated (v52)
// A claimed-but-empty profile converts nothing, and the vendor quietly
// concludes Lazo doesn't work. So we nudge - specifically, never generically,
// and we stop the moment they're done or they ask us to.
const { onSchedule } = require("firebase-functions/v2/scheduler");
const { defineSecret } = require("firebase-functions/params");
const admin = require("firebase-admin");
const E = require("./emails");

const RESEND_API_KEY = defineSecret("RESEND_API_KEY");

// Nudge on these days after the claim was approved.
const STEPS = [1, 3, 7, 14, 30];

function gaps(v) {
  const out = [];
  const gallery = Array.isArray(v.gallery) ? v.gallery.length : 0;
  const packages = Array.isArray(v.packages) ? v.packages.length : 0;
  const hasSheet = !!(v.priceSheetUrl && v.priceSheetUrl.toString().trim());
  const hasVideo = !!(v.videoUrl && v.videoUrl.toString().trim()) ||
    (Array.isArray(v.videoSamples) && v.videoSamples.length > 0);
  const bio = (v.bio || "").toString();
  const pricing = !!(v.priceRangeDisplay && v.priceRangeDisplay.toString().trim()) ||
    !!(v.startingPrice && v.startingPrice.toString().trim());
  const metros = Array.isArray(v.serviceMetros) ? v.serviceMetros.length : 1;
  const dates = Array.isArray(v.unavailableDates) ? v.unavailableDates.length : 0;

  if (!(v.coverUrl && v.coverUrl.toString().trim())) {
    out.push({ key: "cover", core: true,
      title: "Add a cover photo",
      line: "The wide banner behind your name is the first thing a couple sees. One landscape frame of your best work does a lot of work." });
  }
  if (gallery < 10) {
    out.push({ key: "gallery", core: gallery < 3,
      title: gallery === 0 ? "Add your photos" : "You're " + (10 - gallery) + " photos from a full gallery",
      line: "Couples decide with their eyes first. Ten or more images gives them enough to fall for you." });
  }
  if (bio.length < 80) {
    out.push({ key: "bio", core: true,
      title: "Tell couples who you are",
      line: "A few honest sentences about how you work beats a paragraph of adjectives. This leads your profile." });
  }
  if (packages === 0 && !hasSheet) {
    out.push({ key: "packages", core: true,
      title: "Show what you offer",
      line: "Packages or a price sheet let couples self-qualify before they write to you - fewer dead-end inquiries, more real ones." });
  }
  if (!pricing) {
    out.push({ key: "pricing", core: true,
      title: "Add a price range",
      line: "Couples who can see pricing inquire more seriously. Vague pricing filters out the ready ones, not the tire-kickers." });
  }
  if (!hasVideo) {
    out.push({ key: "video", core: false,
      title: "Add a film",
      line: "Motion sells emotion. One highlight reel does more than twenty stills for a couple still deciding." });
  }
  if (dates === 0) {
    out.push({ key: "dates", core: false,
      title: "Mark the dates you're already booked",
      line: "Couples self-filter when they can see your calendar, so every inquiry that lands is one you can actually take." });
  }
  if (metros < 2) {
    out.push({ key: "metros", core: false,
      title: "Add the other markets you serve",
      line: "If you travel, say so - you'll appear for couples in those metros too." });
  }
  return out;
}

exports.activationSweep = onSchedule(
  { schedule: "every day 09:30", timeZone: "America/Phoenix",
    region: "us-central1", timeoutSeconds: 540, memory: "512MiB",
    secrets: [RESEND_API_KEY] },
  async () => {
    const db = admin.firestore();
    const now = Date.now();
    const snap = await db.collection("vendors")
      .where("claimStatus", "==", "claimed").get();
    let sent = 0, done = 0, skipped = 0;

    for (const d of snap.docs) {
      const v = d.data();
      if (v.activationEmailsEnabled === false) { skipped++; continue; }

      // When did they become ours? claim approval, else seed time.
      const started = v.claimedAt || v.stripeConnectedAt || v.seededAt ||
        v.profileUpdatedAt;
      const startMs = started && started.toMillis ? started.toMillis() : null;
      if (!startMs) { skipped++; continue; }
      const days = Math.floor((now - startMs) / 86400000);

      const list = gaps(v);
      const core = list.filter((g) => g.core);

      // Fully dressed: congratulate once, then leave them alone.
      if (list.length === 0) {
        if (!v.activationCompleteEmailedAt) {
          const inner = E.h1("Your profile is dressed to book.") +
            "<p>Everything a couple looks for is on your page now. From here it's " +
            "a speed game - the first reply usually wins the booking.</p>" +
            E.button("See your page", E.APP_URL) +
            E.quiet("We won't send you profile reminders again.");
          const ok = await E.send(RESEND_API_KEY.value(),
            (v.publicEmail || v.outreachEmail || "").toString(),
            "Your Lazo profile is complete", E.shell(inner,
              { eyebrow: "PROFILE COMPLETE" }));
          if (ok) {
            await d.ref.set({
              activationCompleteEmailedAt:
                admin.firestore.FieldValue.serverTimestamp(),
            }, { merge: true });
            done++;
          }
        }
        continue;
      }

      const step = Number(v.activationStep || 0);
      if (step >= STEPS.length) { skipped++; continue; }
      if (days < STEPS[step]) { skipped++; continue; }

      const focus = (core.length ? core : list)[0];
      const remaining = list.length;
      const to = (v.publicEmail || v.outreachEmail || "").toString();
      const name = (v.name || "your business").toString();

      const opener = step === 0
        ? "<p>" + name + " is live on Lazo. One thing would make it work harder:</p>"
        : step === STEPS.length - 1
          ? "<p>Last nudge from us about this - promise. Your page is live, and " +
            "this is the piece still missing:</p>"
          : "<p>Your page is out there working. This would help it work better:</p>";

      const inner = E.h1(focus.title) + opener +
        "<p style=\"background:#F1E9E0;border-radius:12px;padding:13px 15px;" +
        "font-size:13.5px;line-height:1.55\">" + focus.line + "</p>" +
        E.button("Finish your profile", E.APP_URL) +
        (remaining > 1
          ? E.quiet(remaining - 1 + " other" + (remaining > 2 ? "s" : "") +
            " to go after this - your dashboard shows the checklist.")
          : "") +
        E.quiet("Free forever, and your ranking is never for sale. " +
          "Reply 'stop' and we'll leave your profile alone.");

      const ok = await E.send(RESEND_API_KEY.value(), to,
        focus.title + " \u2014 " + name, E.shell(inner,
          { eyebrow: "MAKE YOUR PAGE WORK HARDER" }));
      if (ok) {
        await d.ref.set({
          activationStep: step + 1,
          activationLastEmailAt: admin.firestore.FieldValue.serverTimestamp(),
          activationLastFocus: focus.key,
        }, { merge: true });
        sent++;
      } else {
        skipped++;
      }
    }
    console.log("activation sweep:", sent, "nudged,", done, "completed,",
      skipped, "skipped");
  }
);
