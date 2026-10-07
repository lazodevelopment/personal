// JC-LAZO-FN-1007-RESTORE: recovered from the 2026-09-21 production build; approval branch disabled (index.js sends it).
// Lazo — tell them when their claim is decided (v51)
// Someone uploaded a legal document and waited. Silence is the wrong answer
// in both directions: approved deserves a welcome, denied deserves a reason.
const { onDocumentUpdated } = require("firebase-functions/v2/firestore");
const { defineSecret } = require("firebase-functions/params");
const admin = require("firebase-admin");

const RESEND_API_KEY = defineSecret("RESEND_API_KEY");

const APP_URL = "https://app.meetlazo.com";

function shell(inner) {
  return '<div style="background:#F7F3EC;padding:32px 0;font-family:Lato,' +
    'Helvetica,Arial,sans-serif">' +
    '<div style="max-width:520px;margin:0 auto;background:#FAF6F0;' +
    'border:1px solid rgba(217,183,124,.55);border-radius:20px;overflow:hidden">' +
    '<div style="background:linear-gradient(135deg,#52284F,#3D1C3B);' +
    'padding:26px 28px">' +
    '<div style="color:#FAF6F0;font-size:22px;letter-spacing:5px;' +
    'font-family:Georgia,serif">L A Z O</div></div>' +
    '<div style="padding:26px 28px;color:#241E2B;font-size:15px;line-height:1.6">' +
    inner + '</div>' +
    '<div style="padding:16px 28px;border-top:1px solid rgba(217,183,124,.4);' +
    'color:#8A7F90;font-size:11.5px">Lazo Weddings, LLC \u00b7 meetlazo.com</div>' +
    '</div></div>';
}

function button(label, url) {
  return '<div style="margin:22px 0"><a href="' + url + '" ' +
    'style="background:#D9B77C;color:#52284F;text-decoration:none;' +
    'padding:13px 24px;border-radius:12px;font-weight:800;font-size:14px;' +
    'display:inline-block">' + label + '</a></div>';
}

async function send(key, to, subject, html) {
  if (!key || !to) { console.log("claim email skipped: missing key/to"); return; }
  try {
    const r = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { "Authorization": "Bearer " + key,
                 "Content-Type": "application/json" },
      body: JSON.stringify({
        from: "Lazo <hello@meetlazo.com>",
        to: [to], subject: subject, html: html }),
    });
    if (!r.ok) console.error("claim email status", r.status);
  } catch (e) { console.error("claim email failed", e.message); }
}

async function handle(event) {
  const before = event.data.before.data() || {};
  const after = event.data.after.data() || {};
  const was = (before.status || "").toString();
  const now = (after.status || "").toString();
  if (was === now) return;
  if (now !== "approved" && now !== "denied") return;

  const db = admin.firestore();
  const biz = (after.businessName || "your business").toString();
  let to = (after.businessEmail || after.email || "").toString();
  if (!to && after.uid) {
    try {
      const u = await db.collection("users").doc(after.uid).get();
      if (u.exists) to = (u.data().email || "").toString();
    } catch (e) { /* fall through */ }
  }

  if (now === "approved") {
    // JC-LAZO-FN-1007-RESTORE: the founding-vendor welcome in index.js (claimApprovedEmail) covers approvals
    return;
    // eslint-disable-next-line no-unreachable
    const inner =
      "<p style=\"font-family:Georgia,serif;font-size:22px;color:#52284F;" +
      "margin:0 0 8px\">You\u2019re verified.</p>" +
      "<p><b>" + biz + "</b> is now yours on Lazo. Your dashboard is open, " +
      "your page is live, and every inquiry that comes through it is a real " +
      "couple with a real date \u2014 and it\u2019s free, forever.</p>" +
      button("Open your dashboard", APP_URL) +
      "<p style=\"font-size:13.5px\"><b>Worth ten minutes today:</b></p>" +
      "<ul style=\"font-size:13.5px;padding-left:18px;line-height:1.7\">" +
      "<li>Add ten photos \u2014 couples decide with their eyes first.</li>" +
      "<li>Show your packages or a price range. Couples who can see pricing " +
      "inquire more seriously.</li>" +
      "<li>Mark the dates you\u2019re already booked so every inquiry is one " +
      "you can actually take.</li></ul>" +
      "<p style=\"font-size:13.5px;color:#8A7F90\">Reply to this email if " +
      "anything is confusing \u2014 a real person reads it.</p>";
    await send(RESEND_API_KEY.value(), to,
      "You\u2019re verified on Lazo \u2014 " + biz, shell(inner));
    await event.data.after.ref.set({
      decisionEmailedAt: admin.firestore.FieldValue.serverTimestamp(),
      decisionEmailTo: to,
    }, { merge: true });
    console.log("claim approved email sent", biz, to);
    return;
  }

  const reason = (after.denyReason || "").toString();
  const inner =
    "<p style=\"font-family:Georgia,serif;font-size:22px;color:#52284F;" +
    "margin:0 0 8px\">About your claim</p>" +
    "<p>We weren\u2019t able to approve the claim on <b>" + biz + "</b> " +
    "with the information provided.</p>" +
    (reason ? "<p style=\"background:#F1E9E0;border-radius:12px;padding:12px 14px;" +
      "font-size:13.5px\">" + reason + "</p>" : "") +
    "<p>If we\u2019ve got it wrong \u2014 and sometimes we do \u2014 reply " +
    "to this email with anything that shows the business is yours, and a " +
    "person will look again.</p>" +
    button("Try again", APP_URL);
  await send(RESEND_API_KEY.value(), to,
    "About your Lazo claim \u2014 " + biz, shell(inner));
  await event.data.after.ref.set({
    decisionEmailedAt: admin.firestore.FieldValue.serverTimestamp(),
    decisionEmailTo: to,
  }, { merge: true });
  console.log("claim denied email sent", biz, to);
}

exports.onClaimDecided = onDocumentUpdated(
  { region: "us-central1", document: "claimRequests/{requestId}",
    timeoutSeconds: 60, memory: "256MiB", secrets: [RESEND_API_KEY] },
  handle
);

exports.onListingDecided = onDocumentUpdated(
  { region: "us-central1", document: "listingRequests/{requestId}",
    timeoutSeconds: 60, memory: "256MiB", secrets: [RESEND_API_KEY] },
  handle
);
