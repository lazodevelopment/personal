// JC-LAZO-FN-1007-RESTORE: recovered from the 2026-09-21 production build (the local tree never had it).
// Lazo — automatic review requests (v49)
// Three days after the wedding, we ask. Twice more if they're busy, then we
// stop. Vendors can switch it off; couples can decline once and never hear
// about it again.
const { onSchedule } = require("firebase-functions/v2/scheduler");
const { onDocumentCreated } = require("firebase-functions/v2/firestore");
const { defineSecret } = require("firebase-functions/params");
const admin = require("firebase-admin");

const RESEND_API_KEY = defineSecret("RESEND_API_KEY");

// Most crafts have finished the moment the reception ends. Photographers and
// videographers have not - the couple has nothing to review until the gallery
// lands. Asking early reads as a vendor who doesn't understand the work.
const STAGES = [
  { stage: 1, days: 3 },
  { stage: 2, days: 10 },
  { stage: 3, days: 21 },
];

// For these, the clock starts at DELIVERY, not at the wedding.
const DELIVERY_CRAFTS = [
  "wedding-photographers",
  "wedding-videographers",
];
const DELIVERY_STAGES = [
  { stage: 1, days: 2 },
  { stage: 2, days: 9 },
  { stage: 3, days: 20 },
];
// If a delivery vendor never marks it delivered, we wait this long after the
// wedding and then ask gently whether the gallery has arrived at all.
const DELIVERY_FALLBACK_DAYS = 60;

function parseWeddingDate(inq) {
  try {
    const si = inq.structuredIntent || {};
    const raw = (si.weddingDate || "").toString();
    if (!raw) return null;
    const d = new Date(raw);
    if (isNaN(d.getTime())) return null;
    return d;
  } catch (e) { return null; }
}

async function emailCouple(key, to, coupleName, vendorName, stage, waiting) {
  if (!key || !to) return;
  const first = (coupleName || "").split("&")[0].trim() || "there";
  if (waiting) {
    const wSub = "Has your gallery from " + vendorName + " arrived?";
    const wBody = "<p>Hi " + (coupleName || "").split("&")[0].trim() +
      ",</p><p>It has been a little while since your wedding. Once <b>" +
      vendorName + "</b> has delivered your gallery, we would love your " +
      "review - it is the most useful thing the next couple can read.</p>" +
      "<p>No rush at all if you are still waiting.</p>" +
      "<p><a href=\"https://app.meetlazo.com\">Open Lazo</a></p>" +
      "<p>\u2014 Lazo</p>";
    try {
      await fetch("https://api.resend.com/emails", {
        method: "POST",
        headers: { "Authorization": "Bearer " + key,
                   "Content-Type": "application/json" },
        body: JSON.stringify({
          from: "Lazo <hello@meetlazo.com>",
          to: [to], subject: wSub, html: wBody }),
      });
    } catch (e) { console.error("review email failed", e.message); }
    return;
  }
  const subject = stage === 1
    ? "How was " + vendorName + "?"
    : stage === 2
      ? "A quick word about " + vendorName + "?"
      : "Last ask - your " + vendorName + " review";
  const body = stage === 1
    ? "<p>Hi " + first + ",</p><p>Congratulations again. Now that the day has passed, would you share a few words about working with <b>" + vendorName + "</b>?</p><p>Reviews on Lazo come only from couples who actually booked - which is why they matter. Yours helps the next couple choose well.</p><p><a href=\"https://app.meetlazo.com\">Leave your review</a></p><p>\u2014 Lazo</p>"
    : stage === 2
      ? "<p>Hi " + first + ",</p><p>No rush at all - but if you have two minutes, <b>" + vendorName + "</b> would love your review.</p><p><a href=\"https://app.meetlazo.com\">Leave your review</a></p><p>\u2014 Lazo</p>"
      : "<p>Hi " + first + ",</p><p>This is our last note about it - promise. If you'd like to leave <b>" + vendorName + "</b> a review, it takes a minute:</p><p><a href=\"https://app.meetlazo.com\">Leave your review</a></p><p>Either way, congratulations on the wedding.</p><p>\u2014 Lazo</p>";
  try {
    await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { "Authorization": "Bearer " + key,
                 "Content-Type": "application/json" },
      body: JSON.stringify({
        from: "Lazo <hello@meetlazo.com>",
        to: [to], subject: subject, html: body }),
    });
  } catch (e) { console.error("review email failed", e.message); }
}

exports.reviewRequestSweep = onSchedule(
  { schedule: "every day 10:00", timeZone: "America/Phoenix",
    region: "us-central1", timeoutSeconds: 540, memory: "512MiB",
    secrets: [RESEND_API_KEY] },
  async () => {
    const db = admin.firestore();
    const now = Date.now();
    const snap = await db.collection("inquiries")
      .where("status", "==", "booked").get();
    let asked = 0, skipped = 0;
    for (const d of snap.docs) {
      const inq = d.data();
      if (inq.reviewSubmittedAt) { skipped++; continue; }
      if (inq.reviewOptOut === true) { skipped++; continue; }
      const wd = parseWeddingDate(inq);
      if (!wd) { skipped++; continue; }
      const daysSince = Math.floor((now - wd.getTime()) / 86400000);

      // vendor can switch the whole thing off; craft decides the clock
      let vendorName = "your vendor";
      let isDelivery = false;
      try {
        const v = await db.collection("vendors").doc(inq.vendorId).get();
        if (v.exists) {
          if (v.data().reviewRequestsEnabled === false) { skipped++; continue; }
          vendorName = (v.data().name || vendorName).toString();
          const cats = Array.isArray(v.data().categories)
            ? v.data().categories : [];
          for (const c of cats) {
            if (DELIVERY_CRAFTS.indexOf(c.toString()) >= 0) isDelivery = true;
          }
        }
      } catch (e) { /* keep going with defaults */ }

      const done = Number(inq.reviewRequestStage || 0);
      let stages = STAGES;
      let clockStart = wd.getTime();
      let waiting = false;

      if (isDelivery) {
        const del = inq.deliveredAt;
        if (del && del.toMillis) {
          stages = DELIVERY_STAGES;
          clockStart = del.toMillis();
        } else {
          // nothing delivered yet: one gentle check-in, then wait
          if (daysSince < DELIVERY_FALLBACK_DAYS) { skipped++; continue; }
          if (inq.reviewWaitingAskedAt) { skipped++; continue; }
          waiting = true;
        }
      }

      if (!waiting) {
        if (done >= stages.length) { skipped++; continue; }
        const elapsed = Math.floor((now - clockStart) / 86400000);
        if (elapsed < stages[done].days) { skipped++; continue; }
      }
      const next = waiting ? { stage: done } : stages[done];

      if (waiting) {
        await d.ref.set({
          reviewWaitingAskedAt: admin.firestore.FieldValue.serverTimestamp(),
          reviewRequestVendorName: vendorName,
        }, { merge: true });
      } else {
        await d.ref.set({
          reviewRequestStage: next.stage,
          reviewRequestedAt: admin.firestore.FieldValue.serverTimestamp(),
          reviewRequestVendorName: vendorName,
        }, { merge: true });
      }

      let email = "";
      try {
        if (inq.coupleUid) {
          const u = await db.collection("users").doc(inq.coupleUid).get();
          if (u.exists) email = (u.data().email || "").toString();
        }
      } catch (e) { /* the in-app card still lands */ }
      await emailCouple(RESEND_API_KEY.value(), email,
        (inq.coupleName || "").toString(), vendorName, next.stage, waiting);
      asked++;
    }
    console.log("review sweep:", asked, "asked,", skipped, "skipped");
  }
);

// A review lands: keep the vendor's public numbers honest.
exports.onReviewCreated = onDocumentCreated(
  { region: "us-central1", document: "reviews/{reviewId}",
    timeoutSeconds: 60, memory: "256MiB" },
  async (event) => {
    try {
      const db = admin.firestore();
      const r = event.data ? event.data.data() : null;
      if (!r || !r.vendorId) return;
      const vRef = db.collection("vendors").doc(r.vendorId);
      const all = await db.collection("reviews")
        .where("vendorId", "==", r.vendorId)
        .where("status", "==", "published").get();
      let sum = 0, n = 0;
      for (const d of all.docs) {
        const v = Number(d.data().rating || 0);
        if (v > 0) { sum += v; n++; }
      }
      const avg = n > 0 ? Math.round((sum / n) * 10) / 10 : 0;
      await vRef.set({
        reviewCount: n,
        reviewAverage: avg,
        lastReviewAt: admin.firestore.FieldValue.serverTimestamp(),
      }, { merge: true });
      if (r.inquiryId) {
        await db.collection("inquiries").doc(r.inquiryId).set({
          reviewSubmittedAt: admin.firestore.FieldValue.serverTimestamp(),
        }, { merge: true });
      }
      console.log("review recorded", r.vendorId, n, avg);
    } catch (e) {
      console.error("onReviewCreated failed", e.message);
    }
  }
);
