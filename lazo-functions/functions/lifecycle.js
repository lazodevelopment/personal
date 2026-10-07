// JC-LAZO-FN-1007-RESTORE: recovered from the 2026-09-21 production build (the local tree never had it);
// couple-facing branches removed here because functions-dashboard/couple-notify.js now sends them.
// Lazo — lifecycle emails (v54)
// The product has to keep working when nobody has the tab open. Leads are
// instant because speed wins bookings; messages are digested because nobody
// should be punished for a conversation.
const { onDocumentCreated, onDocumentUpdated } =
  require("firebase-functions/v2/firestore");
const { onSchedule } = require("firebase-functions/v2/scheduler");
const { defineSecret } = require("firebase-functions/params");
const admin = require("firebase-admin");
const E = require("./emails");

const RESEND_API_KEY = defineSecret("RESEND_API_KEY");

// ---------------------------------------------------------------- helpers
async function vendorEmail(db, vendorId) {
  try {
    const v = await db.collection("vendors").doc(vendorId).get();
    if (!v.exists) return { to: "", name: "", vd: {} };
    const vd = v.data();
    let to = (vd.publicEmail || vd.notifyEmail || vd.outreachEmail || "")
      .toString();
    if (!to && vd.claimedBy) {
      const u = await db.collection("users").doc(vd.claimedBy).get();
      if (u.exists) to = (u.data().email || "").toString();
    }
    return { to: to, name: (vd.name || "your business").toString(), vd: vd };
  } catch (e) { return { to: "", name: "", vd: {} }; }
}

async function coupleEmail(db, uid) {
  try {
    if (!uid) return { to: "", name: "" };
    const u = await db.collection("users").doc(uid).get();
    if (!u.exists) return { to: "", name: "" };
    return { to: (u.data().email || "").toString(),
      name: (u.data().display_name || "").toString() };
  } catch (e) { return { to: "", name: "" }; }
}

function firstName(s) {
  const t = (s || "").toString().split("&")[0].trim();
  return t ? t.split(" ")[0] : "there";
}

function money(n) {
  const v = Number(n || 0);
  return "$" + v.toLocaleString("en-US",
    { minimumFractionDigits: v % 1 ? 2 : 0, maximumFractionDigits: 2 });
}

// ------------------------------------------------- a lead just came in
exports.onLeadEmail = onDocumentCreated(
  { region: "us-central1", document: "inquiries/{inquiryId}",
    timeoutSeconds: 60, memory: "256MiB", secrets: [RESEND_API_KEY] },
  async (event) => {
    try {
      const db = admin.firestore();
      const inq = event.data ? event.data.data() : null;
      if (!inq || !inq.vendorId) return;
      const v = await vendorEmail(db, inq.vendorId);
      // unclaimed vendors already get the recruitment email from outreach
      if (!v.vd.claimedBy) return;
      if (v.vd.leadEmailsEnabled === false) return;
      if (!v.to) return;

      // v55: never advertise a blank. If we don't know the couple's name or
      // date, say less rather than saying "A couple" and "Date TBD".
      const rawCouple = (inq.coupleName || "").toString().trim();
      let couple = rawCouple;
      if (!couple && inq.coupleUid) {
        try {
          const u = await db.collection("users").doc(inq.coupleUid).get();
          if (u.exists) {
            couple = (u.data().display_name || "").toString().trim();
          }
        } catch (e) { /* fall through to the generic */ }
      }
      const hasCouple = couple.length > 0;
      if (!hasCouple) { couple = "A couple"; }
      const si = inq.structuredIntent || {};
      const rawDate = (si.weddingDate || "").toString().trim();
      const realDate = (rawDate && !/tbd|unknown|n\/a/i.test(rawDate))
        ? rawDate : "";
      const date = realDate;
      const venue = (si.venue || si.venueName || "").toString();
      const msg = (inq.message || "").toString();

      const inner = E.h1("A couple is asking about your date.") +
        "<p><b>" + couple + "</b> just inquired" +
        (date ? " about <b>" + date + "</b>" : "") +
        (venue ? " at " + venue : "") + "." +
        (date ? "" : " They haven\u2019t locked a date yet \u2014 " +
          "worth asking.") + "</p>" +
        (msg ? '<p style="background:#F1E9E0;border-radius:12px;' +
          'padding:13px 15px;font-size:13.5px;font-style:italic">' +
          msg.slice(0, 400) + "</p>" : "") +
        E.button("Reply in Lazo", E.APP_URL) +
        E.quiet("First reply usually wins the booking. This inquiry is free " +
          "\u2014 Lazo never charges you for a lead.");
      const subject = hasCouple
        ? (date ? "New inquiry \u00b7 " + date + " \u2014 " + couple
                : "New inquiry from " + couple)
        : (date ? "New inquiry for " + date : "A couple is asking about your date");
      await E.send(RESEND_API_KEY.value(), v.to, subject,
        E.shell(inner, { eyebrow: "VERIFIED LEAD" }));
      await event.data.ref.set({
        leadEmailedAt: admin.firestore.FieldValue.serverTimestamp(),
      }, { merge: true });
      console.log("lead email sent", inq.vendorId, v.to);
    } catch (e) { console.error("onLeadEmail", e.message); }
  }
);

// ------------------------------------- contract + invoice state changes
exports.onThreadStateEmail = onDocumentUpdated(
  { region: "us-central1", document: "inquiries/{inquiryId}",
    timeoutSeconds: 60, memory: "256MiB", secrets: [RESEND_API_KEY] },
  async (event) => {
    try {
      const db = admin.firestore();
      const b = event.data.before.data() || {};
      const a = event.data.after.data() || {};
      const key = RESEND_API_KEY.value();
      const v = await vendorEmail(db, a.vendorId || "");
      const c = await coupleEmail(db, a.coupleUid || "");

      // contract sent -> the couple: SignWell's own signing email plus functions-dashboard/couple-notify (JC-LAZO-FN-1007-RESTORE)
      // contract signed -> tell both
      if (b.contractStatus !== "signed" && a.contractStatus === "signed") {
        if (v.to && v.vd.docEmailsEnabled !== false) {
          const inner = E.h1((a.coupleName || "Your couple") + " signed.") +
            "<p>The agreement is executed and filed in their thread. If you " +
            "have automatic retainers on, their invoice has already gone " +
            "out.</p>" + E.button("Open the thread", E.APP_URL);
          await E.send(key, v.to,
            "Signed \u2014 " + (a.coupleName || "your couple"),
            E.shell(inner, { eyebrow: "CONTRACT SIGNED" }));
        }
        // the couple's "signed" and "booked" mail comes from couple-notify (JC-LAZO-FN-1007-RESTORE)
      }
      // invoice due -> the couple hears from couple-notify when the invoice doc is created (JC-LAZO-FN-1007-RESTORE)
      // invoice paid -> tell the vendor
      if (b.invoiceStatus !== "paid" && a.invoiceStatus === "paid" && v.to) {
        let amt = "";
        try {
          const inv = await db.collection("inquiries").doc(event.params.inquiryId)
            .collection("invoices").where("status", "==", "paid").get();
          let total = 0;
          inv.forEach((d) => { total += Number(d.data().total || 0); });
          if (total > 0) amt = money(total);
        } catch (e) { /* amount is a nicety */ }
        const inner = E.h1("You got paid." + (amt ? " " + amt + "." : "")) +
          "<p><b>" + (a.coupleName || "Your couple") + "</b> settled their " +
          "invoice. The money is on its way to your own account \u2014 Lazo " +
          "never touched it.</p>" + E.button("See the thread", E.APP_URL);
        await E.send(key, v.to,
          "Paid" + (amt ? " \u00b7 " + amt : "") + " \u2014 " +
          (a.coupleName || "your couple"),
          E.shell(inner, { eyebrow: "PAYMENT RECEIVED" }));
      }
    } catch (e) { console.error("onThreadStateEmail", e.message); }
  }
);

// ------------------------------------------- unanswered messages, digested
exports.messageDigestSweep = onSchedule(
  { schedule: "every 20 minutes", timeZone: "America/Phoenix",
    region: "us-central1", timeoutSeconds: 300, memory: "256MiB",
    secrets: [RESEND_API_KEY] },
  async () => {
    const db = admin.firestore();
    const key = RESEND_API_KEY.value();
    const now = Date.now();
    const QUIET_MS = 20 * 60 * 1000;   // let them reply in-app first
    const snap = await db.collection("inquiries")
      .orderBy("lastMessageAt", "desc").limit(400).get();
    let sent = 0;
    for (const d of snap.docs) {
      const m = d.data();
      const last = m.lastMessageAt;
      if (!last || !last.toMillis) continue;
      const age = now - last.toMillis();
      if (age < QUIET_MS || age > 6 * 3600 * 1000) continue;
      const notified = m.digestEmailedAt && m.digestEmailedAt.toMillis
        ? m.digestEmailedAt.toMillis() : 0;
      if (notified >= last.toMillis()) continue;

      const role = (m.lastMessageRole || "").toString();
      const preview = (m.lastMessagePreview || "").toString();
      if (role === "couple") {
        const v = await vendorEmail(db, m.vendorId || "");
        if (!v.to || v.vd.messageEmailsEnabled === false) continue;
        const read = m.vendorLastReadAt && m.vendorLastReadAt.toMillis
          ? m.vendorLastReadAt.toMillis() : 0;
        if (read >= last.toMillis()) continue;
        const inner = E.h1((m.coupleName || "A couple") + " wrote to you.") +
          (preview ? '<p style="background:#F1E9E0;border-radius:12px;' +
            'padding:13px 15px;font-size:13.5px;font-style:italic">' +
            preview + "</p>" : "") +
          E.button("Reply in Lazo", E.APP_URL) +
          E.quiet("We only email once per conversation, and never while " +
            "you're already replying.");
        await E.send(key, v.to,
          (m.coupleName || "A couple") + " sent you a message",
          E.shell(inner, { eyebrow: "NEW MESSAGE" }));
        await d.ref.set({
          digestEmailedAt: admin.firestore.FieldValue.serverTimestamp(),
        }, { merge: true });
        sent++;
      }
      // vendor -> couple: instant, from functions-dashboard/couple-notify.js (JC-LAZO-FN-1007-RESTORE)
    }
    console.log("message digest:", sent, "sent");
  }
);
