// functions/index.js — LeaseReputation Cloud Functions (complete backend)
//
// Functions in this file:
//   1. createCommunityFromPlace  — user-driven directory growth (callable)
//   2. onUserCreated             — stamps the `renter` custom claim on signup
//   3. onVerificationSubmitted   — AI document review pipeline (Claude vision)
//   4. onReviewWritten           — reputation scoring engine
//   5. onUserDeleted             — account-deletion cleanup + review handling
//   6. adminDecideVerification   — admin dashboard approve/reject (callable)
//   7. adminListUsers            — admin dashboard user directory (callable)
//   8. recordSignupGeo           — signup location capture (callable)
//   9. onUserProfileCreated      — welcome text on profile creation
//  10. opportunityScout          — Reddit thread finder + reply drafts (scheduled)
//  11. onReportCreated           — review-report email alert
//
// User emails (Resend, from info@leasereputation.com):
//   welcome (signup) · closer-look (human-queue escalation) ·
//   approved · rejected — all built on one shared emailShell template.
//
// Secrets required (firebase functions:secrets:set <NAME>):
//   PLACES_API_KEY      — Google Places API (New)
//   ANTHROPIC_API_KEY   — console.anthropic.com API key
//   RESEND_API_KEY      — resend.com API key (user + admin email)
//   TELNYX_API_KEY / TELNYX_FROM — SMS via Telnyx v2
//     (TELNYX_FROM: the toll-free +1 number; 'PENDING' disables sends)
//
// Design invariants:
//   • Clients never write communities, scores, claims, or residencies —
//     everything here runs on the Admin SDK. Reputation is not for sale.
//   • Verification docs are DELETED from Storage on approval and rejection,
//     per the in-app privacy promise. Only needs_review keeps them, and only
//     until a human decides.
//   • AI never approves on partial confidence: any mismatch or doubt routes
//     to the human queue (status: needs_review) — it can speed things up,
//     never lower the bar.

const { onCall, HttpsError } = require('firebase-functions/v2/https');
const { onDocumentWritten, onDocumentCreated } = require('firebase-functions/v2/firestore');
const { onSchedule } = require('firebase-functions/v2/scheduler');
const { defineSecret } = require('firebase-functions/params');
const functionsV1 = require('firebase-functions/v1');
const admin = require('firebase-admin');

admin.initializeApp();

const PLACES_API_KEY = defineSecret('PLACES_API_KEY');
const ANTHROPIC_API_KEY = defineSecret('ANTHROPIC_API_KEY');
const RESEND_API_KEY = defineSecret('RESEND_API_KEY');
const TELNYX_API_KEY = defineSecret('TELNYX_API_KEY');
const TELNYX_FROM = defineSecret('TELNYX_FROM');
const REDDIT_CLIENT_ID = defineSecret('REDDIT_CLIENT_ID');
const REDDIT_CLIENT_SECRET = defineSecret('REDDIT_CLIENT_SECRET');

// Where human-queue alerts go.
const ADMIN_EMAIL = 'info@leasereputation.com';

async function notifyAdmin(subject, body) {
  try {
    await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${RESEND_API_KEY.value()}`,
      },
      body: JSON.stringify({
        from: 'LeaseReputation <info@leasereputation.com>',
        to: [ADMIN_EMAIL],
        subject,
        text: body,
      }),
    });
  } catch (e) {
    console.error('admin notification failed', e);
  }
}

// ── User-facing email system ────────────────────────────────────
// One shared shell, four messages. Light background on purpose:
// dark-theme HTML renders unpredictably across email clients.
// To use a design built in Resend's editor instead, copy its HTML
// and swap it in at the call site — the sender doesn't care.

const APP_URL = 'https://app.leasereputation.com';

function emailShell({ heading, bodyHtml, ctaText, ctaUrl }) {
  return `<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#F4F4FB;font-family:Arial,Helvetica,sans-serif;">
  <div style="max-width:560px;margin:0 auto;padding:32px 20px;">
    <div style="text-align:center;padding-bottom:22px;font-size:20px;font-weight:800;color:#1B1B2F;">
      Lease<span style="color:#4C4FE6;">Reputation</span>
    </div>
    <div style="background:#FFFFFF;border-radius:16px;padding:32px 30px;border:1px solid #E7E7F4;">
      <h1 style="margin:0 0 14px;font-size:21px;color:#1B1B2F;">${heading}</h1>
      <div style="font-size:15px;line-height:1.6;color:#4A4A66;">${bodyHtml}</div>
      ${
        ctaText
          ? `<div style="text-align:center;margin-top:26px;">
        <a href="${ctaUrl}" style="display:inline-block;background:#4C4FE6;color:#FFFFFF;text-decoration:none;font-weight:700;font-size:15px;padding:13px 30px;border-radius:12px;">${ctaText}</a>
      </div>`
          : ''
      }
    </div>
    <div style="text-align:center;padding-top:20px;font-size:12px;color:#9A9AB8;">
      Verified apartment reviews — reputation that can't be bought.<br/>
      Lease Reputation LLC
    </div>
  </div>
</body></html>`;
}

async function sendUserEmail(to, subject, html) {
  if (!to) return;
  try {
    await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${RESEND_API_KEY.value()}`,
      },
      body: JSON.stringify({
        from: 'LeaseReputation <info@leasereputation.com>',
        to: [to],
        subject,
        html,
      }),
    });
  } catch (e) {
    console.error(`user email failed ("${subject}") for ${to}`, e);
  }
}

async function userEmailFor(uid) {
  try {
    return (await admin.auth().getUser(uid)).email || null;
  } catch (_) {
    return null;
  }
}

async function userFirstNameFor(uid) {
  try {
    const d = await admin.firestore().collection('users').doc(uid).get();
    const name = ((d.data() && d.data().name) || '').trim();
    return name ? name.split(/\s+/)[0] : '';
  } catch (_) {
    return '';
  }
}

const greet = (first) => (first ? `Hi ${first}, ` : '');

async function sendApprovedEmail(uid, communityName) {
  const [to, first] = await Promise.all([userEmailFor(uid), userFirstNameFor(uid)]);
  await sendUserEmail(
    to,
    "You're verified ✓",
    emailShell({
      heading: "You're verified",
      bodyHtml: `<p style="margin:0 0 12px;">${greet(first)}your residency${
        communityName ? ` at <b>${communityName}</b>` : ''
      } is confirmed. Your reviews now carry the verified badge — the one that can't be bought.</p>
        <p style="margin:0;">And as promised: your documents have already been deleted. We keep the badge, never the paperwork.</p>`,
      ctaText: 'Write your review',
      ctaUrl: APP_URL,
    })
  );
}

async function sendRejectedEmail(uid, reason) {
  const [to, first] = await Promise.all([userEmailFor(uid), userFirstNameFor(uid)]);
  await sendUserEmail(
    to,
    "We couldn't verify your documents",
    emailShell({
      heading: "We couldn't verify your documents",
      bodyHtml: `<p style="margin:0 0 12px;">${greet(first)}here's what went wrong:</p>
        <p style="margin:0 0 12px;padding:12px 14px;background:#FFF3F3;border-left:3px solid #E85D5D;border-radius:0 8px 8px 0;color:#8A3A3A;">${
          reason || 'The documents could not be read clearly.'
        }</p>
        <p style="margin:0;">Fix the issue and resubmit — it only takes a minute, and nothing is held against your account. Your documents were deleted either way.</p>`,
      ctaText: 'Resubmit now',
      ctaUrl: APP_URL,
    })
  );
}

async function sendCloserLookEmail(uid) {
  const [to, first] = await Promise.all([userEmailFor(uid), userFirstNameFor(uid)]);
  await sendUserEmail(
    to,
    "We're taking a closer look at your verification",
    emailShell({
      heading: "We're taking a closer look",
      bodyHtml: `<p style="margin:0 0 12px;">${greet(first)}your documents cleared the automated checks — a member of our team is double-checking one detail before your verified badge goes live.</p>
        <p style="margin:0;">This usually completes the same day. There's nothing to resubmit and nothing you need to do — we'll email you the moment it's decided.</p>`,
      ctaText: null,
      ctaUrl: null,
    })
  );
}

// ── Coffee-card program (first 1,000 verified reviewers) ────────
// $5 thank-you card mailed to verified reviewers. NEVER conditioned on
// review content — offered on publish regardless of stars or sentiment
// (FTC-clean), disclosed on the site, capped by a transactional counter.

const COFFEE_CARD_CAP = 1000;
const COFFEE_META_REF = () =>
  admin.firestore().collection('meta').doc('coffeeCard');

async function userHasPublishedReview(uid) {
  const db = admin.firestore();
  const res = await db
    .collection('users')
    .doc(uid)
    .collection('residencies')
    .limit(10)
    .get();
  for (const r of res.docs) {
    const rev = await db
      .collection('communities')
      .doc(r.id)
      .collection('reviews')
      .doc(uid)
      .get();
    if (rev.exists && rev.data().status === 'published') return true;
  }
  return false;
}

async function sendCoffeeOfferEmail(uid, communityName) {
  const [to, first] = await Promise.all([userEmailFor(uid), userFirstNameFor(uid)]);
  await sendUserEmail(
    to,
    'Your coffee\u2019s on us \u2615',
    emailShell({
      heading: 'Your coffee\u2019s on us',
      bodyHtml: `<p style="margin:0 0 12px;">${greet(first)}your verified review${
        communityName ? ` of <b>${communityName}</b>` : ''
      } is live — and you\u2019re among the first 1,000 verified reviewers, which means a <b>$5 coffee card</b> is yours. Our treat, mailed to you.</p>
        <p style="margin:0 0 12px;">Claim it in the app — takes 30 seconds. We only need where to send it.</p>
        <p style="margin:0;font-size:13px;color:#9A9AB8;">The thank-you gift is the same for every verified reviewer — it\u2019s never conditioned on what your review says. One per reviewer, while the first-1,000 program lasts.</p>`,
      ctaText: 'Claim my coffee card',
      ctaUrl: APP_URL,
    })
  );
}

async function sendCoffeeApprovedEmail(uid, number) {
  const [to, first] = await Promise.all([userEmailFor(uid), userFirstNameFor(uid)]);
  await sendUserEmail(
    to,
    'Your coffee card is on its way \u2615',
    emailShell({
      heading: 'Your coffee card is on its way',
      bodyHtml: `<p style="margin:0 0 12px;">${greet(first)}claim confirmed — you\u2019re verified reviewer <b>#${number}</b> of the first 1,000. Your $5 coffee card goes in the mail shortly.</p>
        <p style="margin:0;">Thanks for making the next renter\u2019s decision an informed one. That\u2019s the whole point of this place.</p>`,
      ctaText: null,
      ctaUrl: null,
    })
  );
}

async function sendCoffeeIneligibleEmail(uid, reason) {
  const [to, first] = await Promise.all([userEmailFor(uid), userFirstNameFor(uid)]);
  await sendUserEmail(
    to,
    'About your coffee card claim',
    emailShell({
      heading: 'About your coffee card claim',
      bodyHtml: `<p style="margin:0 0 12px;">${greet(first)}we couldn\u2019t approve your coffee card claim:</p>
        <p style="margin:0 0 12px;padding:12px 14px;background:#F4F4FB;border-left:3px solid #4C4FE6;border-radius:0 8px 8px 0;color:#4A4A66;">${reason}</p>
        <p style="margin:0;">If a published verified review lands on your account later, just reopen the claim screen and resubmit.</p>`,
      ctaText: null,
      ctaUrl: null,
    })
  );
}


// Every message is prefixed with the brand name and account-related
// only (transactional, not marketing). Telnyx's built-in US opt-out
// handling honors STOP replies automatically on toll-free numbers.

function toE164(raw) {
  const s = String(raw || '').trim();
  const digits = s.replace(/\D/g, '');
  if (digits.length === 10) return `+1${digits}`; // bare US number
  if (digits.length === 11 && digits.startsWith('1')) return `+${digits}`;
  if (s.startsWith('+') && digits.length >= 8 && digits.length <= 15)
    return `+${digits}`;
  return null; // unparseable — skip silently
}

async function sendUserText(rawPhone, body) {
  const to = toE164(rawPhone);
  if (!to) return;
  try {
    const from = TELNYX_FROM.value();
    if (!from || from.startsWith('PENDING')) return; // sends off until verified
    const res = await fetch('https://api.telnyx.com/v2/messages', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${TELNYX_API_KEY.value()}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ from: from, to: to, text: body }),
    });
    if (!res.ok) {
      console.error(`sms send failed to ${to}`, res.status, await res.text());
    }
  } catch (e) {
    console.error(`sms send failed to ${to}`, e);
  }
}

async function userPhoneFor(uid) {
  try {
    const d = await admin.firestore().collection('users').doc(uid).get();
    return (d.data() && d.data().phone) || null;
  } catch (_) {
    return null;
  }
}

// ── Policy toggle ──
// When a user deletes their account, their reviews are ANONYMIZED (kept in
// the score, author becomes "Former resident") rather than deleted. This
// prevents review-then-delete gaming of scores. Flip to true to hard-delete
// reviews instead.
const DELETE_REVIEWS_ON_ACCOUNT_DELETE = false;

// ════════════════════════════════════════════════════════════════
// 1. CREATE COMMUNITY FROM PLACE (callable)
// ════════════════════════════════════════════════════════════════

const ALLOWED_PLACE_TYPES = new Set([
  'apartment_building',
  'apartment_complex',
  'condominium_complex',
]);

// Major operators (Avalon, Camden, ...) are often typed ONLY as
// real_estate_agency by Places — accept those unless the name reads like
// an actual brokerage or management office.
const AGENCY_BLOCKLIST =
  /realty|realtor|real estate|broker|property (management|mgmt)|management (co|company|group|llc)|leasing office|homes for sale/i;

function looksResidential(name, types) {
  const t = Array.isArray(types) ? types : [];
  if (t.some((x) => ALLOWED_PLACE_TYPES.has(x))) return true;
  return t.includes('real_estate_agency') && !AGENCY_BLOCKLIST.test(name || '');
}

exports.createCommunityFromPlace = onCall(
  { region: 'us-central1', secrets: [PLACES_API_KEY] },
  async (request) => {
    if (!request.auth) {
      throw new HttpsError('unauthenticated', 'Sign in to add a community.');
    }
    const placeId = String((request.data && request.data.placeId) || '').trim();
    if (!/^[A-Za-z0-9_-]{10,300}$/.test(placeId)) {
      throw new HttpsError('invalid-argument', 'A valid placeId is required.');
    }

    const db = admin.firestore();
    const docRef = db.collection('communities').doc(placeId);
    const existing = await docRef.get();
    if (existing.exists) {
      return {
        communityId: placeId,
        existed: true,
        name: (existing.data() && existing.data().name) || '',
      };
    }

    const res = await fetch(
      `https://places.googleapis.com/v1/places/${encodeURIComponent(placeId)}`,
      {
        headers: {
          'X-Goog-Api-Key': PLACES_API_KEY.value(),
          'X-Goog-FieldMask':
            'id,displayName,formattedAddress,location,photos,types',
        },
      }
    );
    if (!res.ok) {
      console.error('Places lookup failed', res.status, await res.text());
      throw new HttpsError('not-found', 'Could not look up that place.');
    }
    const p = await res.json();

    const name = (p.displayName && p.displayName.text) || 'Unnamed community';
    if (!looksResidential(name, p.types)) {
      throw new HttpsError(
        'failed-precondition',
        "That place doesn't look like a residential community. If you think this is wrong, contact support."
      );
    }

    await docRef.set({
      name,
      nameLower: name.toLowerCase(),
      address: p.formattedAddress || '',
      placeId: p.id || placeId,
      location: p.location
        ? new admin.firestore.GeoPoint(p.location.latitude, p.location.longitude)
        : null,
      photoRef: (p.photos && p.photos[0] && p.photos[0].name) || '',
      reviewCount: 0,
      createdAt: admin.firestore.FieldValue.serverTimestamp(),
      source: 'user-added',
      addedBy: request.auth.uid,
    });

    return { communityId: placeId, existed: false, name };
  }
);

// ════════════════════════════════════════════════════════════════
// 2. RENTER CLAIM ON SIGNUP (v1 auth trigger)
// ════════════════════════════════════════════════════════════════
// The Firestore rules gate review creation on request.auth.token.role ==
// 'renter'. Every new account gets that claim here. (Note: the claim lands
// on the token at the next refresh — automatic within an hour, or forced
// via getIdToken(true) client-side.)

exports.onUserCreated = functionsV1
  .runWith({ secrets: ['RESEND_API_KEY'] })
  .auth.user()
  .onCreate(async (user) => {
    try {
      await admin.auth().setCustomUserClaims(user.uid, { role: 'renter' });
      console.log(`renter claim set for ${user.uid}`);
    } catch (e) {
      console.error(`failed to set renter claim for ${user.uid}`, e);
    }
    // Welcome email — sent after the claim so an email failure can
    // never block account setup. To use the welcome design built in
    // Resend's editor, copy its HTML and replace this emailShell call.
    await sendUserEmail(
      user.email,
      'Welcome to LeaseReputation',
      emailShell({
        heading: 'Welcome to LeaseReputation',
        bodyHtml: `<p style="margin:0 0 12px;">You've joined the review platform where every single review comes from a verified resident — no bought ratings, no buried complaints.</p>
          <p style="margin:0;">One step unlocks everything: verify your residency (two quick uploads, usually done in minutes) and your reviews carry the badge that can't be bought.</p>`,
        ctaText: 'Get verified',
        ctaUrl: APP_URL,
      })
    );
  });

// ════════════════════════════════════════════════════════════════
// 3. AI VERIFICATION PIPELINE
// ════════════════════════════════════════════════════════════════
// Fires when verifications/{uid} is written with status 'pending'.
// Downloads the two docs, has Claude cross-check them against the account
// name and the claimed community's address, then:
//   approve      → full approval (claims, flags, residency, doc deletion)
//   needs_review → human queue; docs retained until a human decides
//   reject       → user-safe reason written back; docs deleted; user can
//                  resubmit immediately (the form reappears in the app)
// Any pipeline error → needs_review, never silently stuck, never auto-pass.

const VERIFY_PROMPT = (accountName, communityName, communityAddress, today) => `
You are the document verification reviewer for LeaseReputation, a platform where only verified apartment residents can post reviews. You will see two documents uploaded by a user:
1. A government photo ID (driver's license, state ID, or passport)
2. A proof of residency (lease, utility bill, or mail)

Account holder name: "${accountName}"
Claimed community: "${communityName}"
Community address: "${communityAddress}"
Today's date: ${today}

Check the following:
- ID_NAME: The name on the photo ID matches the account holder name. Minor variations (middle names, common nicknames like Mike/Michael) count as a match ONLY if clearly the same person; otherwise mark false.
- RES_NAME: The name on the residency document matches the name on the ID.
- RES_ADDRESS: The address on the residency document refers to the same physical location as the community address. Treat it as a MATCH when the street NUMBER and street NAME and city all match, even if the street-type suffix differs (Blvd vs Ln vs St vs Dr vs Ave vs Rd), a directional prefix/suffix differs or is absent (E, W, N, S, NE, etc.), abbreviations differ (Street vs St), or unit/apartment numbers differ or are absent — leasing offices and mapping data routinely disagree on these. Mark FALSE only when the street number differs, the street name itself differs, or the city differs.
- RES_CURRENT: The residency document is plausibly current — a lease whose term includes today, or a bill/mail dated within the last 12 months. If undated, mark false.
- LEGIBLE: Both documents are legible photographs of real documents (not blank, not screenshots of unrelated content, not obviously AI-generated or heavily edited).

Decision rules — apply strictly:
- "approve" ONLY if every check above is confidently TRUE.
- "reject" when EITHER uploaded document is clearly not what it must be: the ID slot contains something that is definitively not a government photo ID (a logo, a random photo, a screenshot, a blank image), or the residency slot contains something definitively not a lease/bill/mail. One clearly-invalid document is sufficient grounds to reject even if the other document is perfect — the user simply needs to re-upload the invalid one, and your userMessage should tell them exactly which document to fix.
- "needs_review" for genuine ambiguity only — documents that ARE the right type but have a mismatch (names, addresses, dates), illegibility that might be a real document photographed badly, or signs of tampering. When torn between approve and needs_review, choose needs_review. You must never approve on partial confidence.

Respond with ONLY a JSON object, no markdown fences, in exactly this shape:
{
  "decision": "approve" | "needs_review" | "reject",
  "checks": { "idName": bool, "resName": bool, "resAddress": bool, "resCurrent": bool, "legible": bool },
  "internalNotes": "concise notes for the human reviewer, may reference document contents",
  "userMessage": "one or two sentences shown to the user if rejected; actionable and polite; MUST NOT contain any names, addresses, or document contents"
}`.trim();

async function downloadDocBlock(path) {
  const file = admin.storage().bucket().file(path);
  const [exists] = await file.exists();
  if (!exists) return null;
  const [meta] = await file.getMetadata();
  const [buf] = await file.download();
  const contentType = (meta.contentType || 'image/jpeg').toLowerCase();
  if (contentType === 'application/pdf') {
    return {
      type: 'document',
      source: { type: 'base64', media_type: 'application/pdf', data: buf.toString('base64') },
    };
  }
  // Normalize images before sending to the AI: full-resolution phone photos
  // exceed the API's ~5MB per-image limit (HTTP 400). Downscale to 2000px
  // max and re-encode as JPEG — plenty of detail for document reading, and
  // guarantees no client upload can ever break the reviewer.
  let imageBuf = buf;
  let mediaType = contentType.startsWith('image/') ? contentType : 'image/jpeg';
  try {
    // Lazy require: sharp only loads in the Cloud Functions runtime (Linux),
    // never during local deploy analysis on Windows.
    const sharp = require('sharp');
    imageBuf = await sharp(buf)
      .rotate() // respect EXIF orientation so documents aren't sideways
      .resize({ width: 2000, height: 2000, fit: 'inside', withoutEnlargement: true })
      .jpeg({ quality: 80 })
      .toBuffer();
    mediaType = 'image/jpeg';
  } catch (e) {
    console.error(`image normalization failed for ${path}, sending original`, e);
  }
  return {
    type: 'image',
    source: { type: 'base64', media_type: mediaType, data: imageBuf.toString('base64') },
  };
}

async function deleteVerificationDocs(uid) {
  await admin
    .storage()
    .bucket()
    .deleteFiles({ prefix: `verification-docs/${uid}/` })
    .catch((e) => console.error(`doc cleanup failed for ${uid}`, e));
}

async function approveVerification(uid, communityId, communityName, reviewedBy) {
  const db = admin.firestore();

  // Custom claims — MERGE with existing (setCustomUserClaims replaces all).
  const userRecord = await admin.auth().getUser(uid);
  const claims = { ...(userRecord.customClaims || {}) };
  if (!claims.role) claims.role = 'renter';
  claims.identityVerified = true;
  await admin.auth().setCustomUserClaims(uid, claims);

  // User doc flags (drive the app UI).
  await db.collection('users').doc(uid).set(
    { identityVerified: true, residencyVerified: true },
    { merge: true }
  );

  // Residency record — the rules' residencyConfirmed() gate for reviews.
  await db
    .collection('users')
    .doc(uid)
    .collection('residencies')
    .doc(communityId)
    .set({
      communityId,
      communityName: communityName || '',
      verifiedAt: admin.firestore.FieldValue.serverTimestamp(),
      verifiedBy: reviewedBy,
    });

  // Privacy promise: the paperwork does not outlive the decision.
  await deleteVerificationDocs(uid);

  // ── Review-first: publish the review they already wrote ──
  // If this user reviewed this community before verifying (status
  // 'pending_verification', or 'expired' if they took longer than the
  // sweep window), verification is the moment it goes live. The status
  // flip fires onReviewWritten, which rescores the community and
  // notifies fellow residents — no double-counting is possible because
  // scoring always recomputes from a full scan of published reviews.
  let reviewWentLive = false;
  try {
    const revRef = db
      .collection('communities')
      .doc(communityId)
      .collection('reviews')
      .doc(uid);
    const revSnap = await revRef.get();
    const revStatus = revSnap.exists ? revSnap.data().status : null;
    if (revStatus === 'pending_verification' || revStatus === 'expired') {
      await revRef.update({
        status: 'published',
        publishedAt: admin.firestore.FieldValue.serverTimestamp(),
      });
      reviewWentLive = true;
      console.log(`published pending review for ${uid} @ ${communityId}`);
    }
  } catch (e) {
    // Never let the review flip sink the approval itself.
    console.error(`pending-review publish failed for ${uid} @ ${communityId}`, e);
  }

  await db.collection('verifications').doc(uid).set(
    {
      status: 'approved',
      reviewedAt: admin.firestore.FieldValue.serverTimestamp(),
      reviewedBy,
    },
    { merge: true }
  );

  // Tell the user — they may have left the app long ago.
  await sendApprovedEmail(uid, communityName);
  await sendUserText(
    await userPhoneFor(uid),
    reviewWentLive
      ? `LeaseReputation: You're verified ✓ Your review of ${
          communityName || 'your community'
        } is now LIVE with the verified badge — and your documents have been deleted, as promised. See it: https://app.leasereputation.com`
      : `LeaseReputation: You're verified ✓ Your residency at ${
          communityName || 'your community'
        } is confirmed — and your documents have been deleted, as promised. Write your review: https://app.leasereputation.com`
  );
}

exports.onVerificationSubmitted = onDocumentWritten(
  {
    document: 'verifications/{uid}',
    region: 'us-central1',
    secrets: [
      ANTHROPIC_API_KEY,
      RESEND_API_KEY,
      TELNYX_API_KEY,
      TELNYX_FROM,
    ],
    timeoutSeconds: 120,
    memory: '512MiB',
  },
  async (event) => {
    const after = event.data && event.data.after.exists ? event.data.after.data() : null;
    const before = event.data && event.data.before.exists ? event.data.before.data() : null;
    if (!after || after.status !== 'pending') return;
    if (before && before.status === 'pending') return; // already processing / no-op write

    const uid = event.params.uid;
    const db = admin.firestore();
    const verRef = db.collection('verifications').doc(uid);

    const toNeedsReview = async (note) => {
      await verRef.set(
        {
          status: 'needs_review',
          aiNotes: note,
          aiReviewedAt: admin.firestore.FieldValue.serverTimestamp(),
        },
        { merge: true }
      );
      await notifyAdmin(
        'LeaseReputation: verification needs review',
        `A verification hit the human queue.\n\nuid: ${uid}\nreason: ${note}\n\nRun: node verify_admin.js list`
      );
      await sendCloserLookEmail(uid);
    };

    try {
      const communityId = String(after.communityId || '');
      if (!communityId) return toNeedsReview('Submission missing communityId.');

      // ── Gather context ──
      const [userDoc, communityDoc, userRecord] = await Promise.all([
        db.collection('users').doc(uid).get(),
        db.collection('communities').doc(communityId).get(),
        admin.auth().getUser(uid),
      ]);
      const accountName = (
        (userDoc.data() && userDoc.data().name) ||
        userRecord.displayName ||
        ''
      ).trim();
      if (!accountName) {
        return toNeedsReview('No account name on file to match against.');
      }
      const community = communityDoc.data() || {};
      const communityName = community.name || after.communityName || '';
      const communityAddress = community.address || '';

      // ── Download the documents ──
      const [idBlock, resBlock] = await Promise.all([
        downloadDocBlock(`verification-docs/${uid}/id.jpg`),
        downloadDocBlock(`verification-docs/${uid}/residency.jpg`),
      ]);
      if (!idBlock || !resBlock) {
        return toNeedsReview('One or both documents missing from storage.');
      }

      // ── Ask Claude ──
      const today = new Date().toISOString().slice(0, 10);
      const apiRes = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': ANTHROPIC_API_KEY.value(),
          'anthropic-version': '2023-06-01',
        },
        body: JSON.stringify({
          model: 'claude-sonnet-4-6',
          max_tokens: 1024,
          messages: [
            {
              role: 'user',
              content: [
                { type: 'text', text: 'Document 1 — photo ID:' },
                idBlock,
                { type: 'text', text: 'Document 2 — proof of residency:' },
                resBlock,
                {
                  type: 'text',
                  text: VERIFY_PROMPT(accountName, communityName, communityAddress, today),
                },
              ],
            },
          ],
        }),
      });
      if (!apiRes.ok) {
        console.error('Anthropic API error', apiRes.status, await apiRes.text());
        return toNeedsReview(`AI reviewer unavailable (HTTP ${apiRes.status}).`);
      }
      const apiData = await apiRes.json();
      const rawText = (apiData.content || [])
        .filter((b) => b.type === 'text')
        .map((b) => b.text)
        .join('\n');
      let verdict;
      try {
        verdict = JSON.parse(rawText.replace(/```json|```/g, '').trim());
      } catch (_) {
        console.error('Unparseable AI response:', rawText);
        return toNeedsReview('AI response was not valid JSON.');
      }

      const checks = verdict.checks || {};
      const allPass =
        checks.idName === true &&
        checks.resName === true &&
        checks.resAddress === true &&
        checks.resCurrent === true &&
        checks.legible === true;

      // ── Act on the decision ──
      // Belt AND suspenders: approval requires BOTH the decision string and
      // every individual check to be true.
      if (verdict.decision === 'approve' && allPass) {
        await approveVerification(uid, communityId, communityName, 'ai');
        console.log(`AI-approved verification for ${uid} @ ${communityId}`);
        return;
      }

      if (verdict.decision === 'reject') {
        await deleteVerificationDocs(uid); // rejected docs are not retained
        await verRef.set(
          {
            status: 'rejected',
            rejectionReason:
              String(verdict.userMessage || '').slice(0, 300) ||
              'We couldn\'t verify those documents. Please retake clear photos and try again.',
            aiNotes: String(verdict.internalNotes || '').slice(0, 1000),
            aiChecks: checks,
            reviewedAt: admin.firestore.FieldValue.serverTimestamp(),
            reviewedBy: 'ai',
          },
          { merge: true }
        );
        console.log(`AI-rejected verification for ${uid}`);
        await sendRejectedEmail(
          uid,
          String(verdict.userMessage || '').slice(0, 300) ||
            "We couldn't verify those documents. Please retake clear photos and try again."
        );
        await sendUserText(
          await userPhoneFor(uid),
          "LeaseReputation: We couldn't verify your documents — the reason is in your email. Fix it and resubmit in the app; nothing is held against your account."
        );
        return;
      }

      // Everything else — including approve-with-failing-checks — goes human.
      await verRef.set(
        {
          status: 'needs_review',
          aiNotes: String(verdict.internalNotes || '').slice(0, 1000),
          aiChecks: checks,
          aiReviewedAt: admin.firestore.FieldValue.serverTimestamp(),
        },
        { merge: true }
      );
      await notifyAdmin(
        'LeaseReputation: verification needs review',
        `A verification was escalated to the human queue.\n\nuid: ${uid}\nname: ${accountName}\ncommunity: ${communityName}\n\nAI notes: ${String(verdict.internalNotes || '')}\n\nRun: node verify_admin.js list`
      );
      await sendCloserLookEmail(uid);
      console.log(`Verification for ${uid} routed to human review`);
    } catch (e) {
      console.error(`verification pipeline error for ${uid}`, e);
      await toNeedsReview(`Pipeline error: ${String(e).slice(0, 300)}`);
    }
  }
);

// ════════════════════════════════════════════════════════════════
// 4. REPUTATION SCORING ENGINE
// ════════════════════════════════════════════════════════════════
// Recomputes a community's reputationScore, dimensionScores, reviewCount,
// and lastReviewAt whenever any review under it is created, edited, or
// deleted. Recent experiences weigh more: 18-month half-life.
//
// Bayesian shrinkage: scores are pulled toward a neutral prior of 65
// ("Good" boundary) with prior strength m=8. With one review the raw
// average only contributes ~1/9 of the score, so a single harsh (or
// glowing) review can't set a community's public number; as verified
// reviews accumulate, the score converges to the true weighted average.
// score = (m·PRIOR + Σw·raw) / (m + Σw)

const HALF_LIFE_DAYS = 548;
const SCORE_PRIOR = 65;
const SCORE_PRIOR_STRENGTH = 8;

const shrink = (weightedSum, weightSum) =>
  (SCORE_PRIOR_STRENGTH * SCORE_PRIOR + weightedSum) /
  (SCORE_PRIOR_STRENGTH + weightSum);

exports.onReviewWritten = onDocumentWritten(
  {
    document: 'communities/{communityId}/reviews/{reviewId}',
    region: 'us-central1',
    secrets: [TELNYX_API_KEY, TELNYX_FROM],
  },
  async (event) => {
    const communityId = event.params.communityId;
    const db = admin.firestore();

    // A brand-new published review — or a review-first pending review
    // flipping to published on verification — notifies fellow residents.
    // Edits, rescores, and deletions stay silent.
    const isNewReview =
      event.data && !event.data.before.exists && event.data.after.exists;
    const becamePublished =
      event.data &&
      event.data.before.exists &&
      event.data.after.exists &&
      event.data.before.data().status !== 'published' &&
      event.data.after.data().status === 'published';
    const newReview =
      isNewReview || becamePublished ? event.data.after.data() : null;

    const snap = await db
      .collection('communities')
      .doc(communityId)
      .collection('reviews')
      .get();

    const now = Date.now();
    let weightSum = 0;
    let scoreSum = 0;
    let count = 0;
    let lastReviewAt = null;
    const dimSums = {}; // key -> { sum, weight }

    snap.forEach((doc) => {
      const r = doc.data();
      if (r.status !== 'published' || r.hidden === true) return;
      const ratings = r.ratings || {};
      const keys = Object.keys(ratings).filter((k) => typeof ratings[k] === 'number');
      if (keys.length === 0) return;

      count++;
      const createdAt =
        r.createdAt && r.createdAt.toDate ? r.createdAt.toDate() : new Date();
      if (!lastReviewAt || createdAt > lastReviewAt) lastReviewAt = createdAt;

      const ageDays = Math.max(0, (now - createdAt.getTime()) / 86400000);
      const weight = Math.pow(0.5, ageDays / HALF_LIFE_DAYS);

      // Per-review overall: mean of its star dimensions, mapped 1–5 → 0–100.
      const avgStars = keys.reduce((s, k) => s + ratings[k], 0) / keys.length;
      const overall = ((avgStars - 1) / 4) * 100;
      scoreSum += overall * weight;
      weightSum += weight;

      for (const k of keys) {
        const d = ((ratings[k] - 1) / 4) * 100;
        if (!dimSums[k]) dimSums[k] = { sum: 0, weight: 0 };
        dimSums[k].sum += d * weight;
        dimSums[k].weight += weight;
      }
    });

    const update = { reviewCount: count };
    if (count > 0 && weightSum > 0) {
      update.reputationScore =
        Math.round(shrink(scoreSum, weightSum) * 10) / 10;
      update.dimensionScores = {};
      for (const k of Object.keys(dimSums)) {
        update.dimensionScores[k] =
          Math.round(shrink(dimSums[k].sum, dimSums[k].weight) * 10) / 10;
      }
      update.lastReviewAt = admin.firestore.Timestamp.fromDate(lastReviewAt);
    } else {
      update.reputationScore = admin.firestore.FieldValue.delete();
      update.dimensionScores = admin.firestore.FieldValue.delete();
      update.lastReviewAt = admin.firestore.FieldValue.delete();
    }

    await db.collection('communities').doc(communityId).set(update, { merge: true });
    console.log(`rescored ${communityId}: ${count} reviews`);

    // ── Resident notification ──
    // Verified residents of this community get a heads-up when a fellow
    // resident posts. Residency docs come from approveVerification, so
    // every recipient is verified. Author excluded; no review content in
    // the text; send failures never affect scoring (already committed).
    if (newReview && newReview.status === 'published') {
      // ── Coffee-card offer ──
      // The offer goes to every author whose review goes live (fresh
      // publish or review-first flip), regardless of review content,
      // while the first-1,000 program has room and they haven't claimed.
      try {
        const authorId = newReview.authorId || event.params.reviewId;
        const [metaSnap, claimSnap] = await Promise.all([
          COFFEE_META_REF().get(),
          db.collection('coffeeClaims').doc(authorId).get(),
        ]);
        const claimed = (metaSnap.data() && metaSnap.data().claimed) || 0;
        if (claimed < COFFEE_CARD_CAP && !claimSnap.exists) {
          const cDoc = await db.collection('communities').doc(communityId).get();
          await sendCoffeeOfferEmail(
            authorId,
            (cDoc.data() && cDoc.data().name) || ''
          );
        }
      } catch (e) {
        console.error(`coffee offer failed for ${communityId}`, e);
      }

      try {
        const communityDoc = await db
          .collection('communities')
          .doc(communityId)
          .get();
        const cname =
          (communityDoc.data() && communityDoc.data().name) || 'your community';
        const residents = await db
          .collectionGroup('residencies')
          .where('communityId', '==', communityId)
          .limit(500)
          .get();
        const authorId = newReview.authorId || event.params.reviewId;
        await Promise.all(
          residents.docs.map(async (r) => {
            const uid = r.ref.parent.parent.id;
            if (uid === authorId) return;
            const phone = await userPhoneFor(uid);
            if (!phone) return;
            await sendUserText(
              phone,
              `LeaseReputation: A verified resident just reviewed ${cname}. See what they said: https://app.leasereputation.com`
            );
          })
        );
      } catch (e) {
        console.error(`review notification failed for ${communityId}`, e);
      }
    }
  }
);

// ════════════════════════════════════════════════════════════════
// 4c. COFFEE-CARD CLAIMS
// ════════════════════════════════════════════════════════════════
// Client writes coffeeClaims/{uid} with status 'received' + mailing
// address (rules enforce shape; doc id = uid enforces one per user).
// This validates eligibility server-side, takes a numbered slot in a
// transaction against meta/coffeeCard, and notifies admin with the
// address for fulfillment. Resubmission after 'ineligible' is handled
// (same pattern as verifications).

exports.onCoffeeClaimWritten = onDocumentWritten(
  {
    document: 'coffeeClaims/{uid}',
    region: 'us-central1',
    secrets: [RESEND_API_KEY],
  },
  async (event) => {
    const after =
      event.data && event.data.after.exists ? event.data.after.data() : null;
    const before =
      event.data && event.data.before.exists ? event.data.before.data() : null;
    if (!after || after.status !== 'received') return;
    if (before && before.status === 'received') return; // no-op / processing

    const uid = event.params.uid;
    const db = admin.firestore();
    const claimRef = db.collection('coffeeClaims').doc(uid);

    const toIneligible = async (reason) => {
      await claimRef.set(
        {
          status: 'ineligible',
          ineligibleReason: reason,
          decidedAt: admin.firestore.FieldValue.serverTimestamp(),
        },
        { merge: true }
      );
      await sendCoffeeIneligibleEmail(uid, reason);
    };

    try {
      // Eligibility: at least one published verified review.
      if (!(await userHasPublishedReview(uid))) {
        return toIneligible(
          'We couldn\u2019t find a published verified review on your account yet. Finish verification (or publish your pending review) and resubmit.'
        );
      }

      // Take a numbered slot — transactional, so the cap can't be raced.
      const number = await db.runTransaction(async (tx) => {
        const meta = await tx.get(COFFEE_META_REF());
        const claimed = (meta.data() && meta.data().claimed) || 0;
        if (claimed >= COFFEE_CARD_CAP) return null;
        tx.set(
          COFFEE_META_REF(),
          {
            claimed: claimed + 1,
            cap: COFFEE_CARD_CAP,
            updatedAt: admin.firestore.FieldValue.serverTimestamp(),
          },
          { merge: true }
        );
        return claimed + 1;
      });

      if (number === null) {
        return toIneligible(
          'The first-1,000 coffee card program is complete. Your review still carries the verified badge — thank you for being part of this.'
        );
      }

      await claimRef.set(
        {
          status: 'approved',
          number,
          approvedAt: admin.firestore.FieldValue.serverTimestamp(),
        },
        { merge: true }
      );

      await sendCoffeeApprovedEmail(uid, number);
      await notifyAdmin(
        `LeaseReputation: coffee card #${number} to mail`,
        `Coffee card claim approved.\n\n#${number} of ${COFFEE_CARD_CAP}\nuid: ${uid}\n\nMail to:\n${after.name}\n${after.street1}${
          after.street2 ? '\n' + after.street2 : ''
        }\n${after.city}, ${after.state} ${after.zip}\n\nAfter mailing, set coffeeClaims/${uid}.status = 'sent'.`
      );
      console.log(`coffee claim approved #${number} for ${uid}`);
    } catch (e) {
      console.error(`coffee claim pipeline error for ${uid}`, e);
      // Leave status 'received' — safe to retry by admin nudge or resubmit.
    }
  }
);

// ════════════════════════════════════════════════════════════════
// 4b. PENDING-REVIEW EXPIRY SWEEP
// ════════════════════════════════════════════════════════════════
// Review-first writes reviews as 'pending_verification'. Ones whose
// authors never complete verification are archived after 14 days —
// protecting the "verified residents only" promise without deleting
// anyone's words. If the author verifies later anyway,
// approveVerification resurrects 'expired' reviews to published.
//
// NOTE: requires a collection-group composite index on reviews
// (status ASC, createdAt ASC). First run logs a click-to-create link
// if it's missing.

const PENDING_REVIEW_TTL_DAYS = 14;

exports.expirePendingReviews = onSchedule(
  {
    schedule: 'every day 04:15',
    timeZone: 'America/Phoenix',
    region: 'us-central1',
  },
  async () => {
    const db = admin.firestore();
    const cutoff = admin.firestore.Timestamp.fromMillis(
      Date.now() - PENDING_REVIEW_TTL_DAYS * 86400000
    );
    const snap = await db
      .collectionGroup('reviews')
      .where('status', '==', 'pending_verification')
      .where('createdAt', '<', cutoff)
      .limit(400)
      .get();
    if (snap.empty) {
      console.log('expirePendingReviews: nothing to expire');
      return;
    }
    const batch = db.batch();
    snap.docs.forEach((doc) => {
      batch.update(doc.ref, {
        status: 'expired',
        expiredAt: admin.firestore.FieldValue.serverTimestamp(),
      });
    });
    await batch.commit();
    console.log(`expirePendingReviews: expired ${snap.size} review(s)`);
  }
);

// ════════════════════════════════════════════════════════════════
// 5. ACCOUNT DELETION CLEANUP (v1 auth trigger)
// ════════════════════════════════════════════════════════════════
// When an auth account is deleted (user-initiated from Manage Account, or
// admin-initiated), purge their data. Reviews are anonymized by default —
// see DELETE_REVIEWS_ON_ACCOUNT_DELETE at the top of this file.

exports.onUserDeleted = functionsV1.auth.user().onDelete(async (user) => {
  const uid = user.uid;
  const db = admin.firestore();
  try {
    // 1. Reviews first — their locations come from the residencies
    //    subcollection, which we're about to delete. One review per
    //    community, doc id == uid.
    const residencies = await db
      .collection('users')
      .doc(uid)
      .collection('residencies')
      .get();
    for (const res of residencies.docs) {
      const reviewRef = db
        .collection('communities')
        .doc(res.id)
        .collection('reviews')
        .doc(uid);
      const review = await reviewRef.get();
      if (!review.exists) continue;
      if (DELETE_REVIEWS_ON_ACCOUNT_DELETE) {
        await db.recursiveDelete(reviewRef); // includes helpfulVotes
        // Hard delete removes the photo evidence too. (Anonymized reviews
        // keep their photos — the evidence stays with the kept review.)
        await admin
          .storage()
          .bucket()
          .deleteFiles({ prefix: `review-photos/${res.id}/${uid}/` })
          .catch(() => {});
      } else {
        await reviewRef.set(
          { authorName: 'Former resident', authorDeleted: true },
          { merge: true }
        );
      }
    }

    // 2. User doc + all subcollections (residencies, private, ...).
    await db.recursiveDelete(db.collection('users').doc(uid));

    // 3. Verification record.
    await db.collection('verifications').doc(uid).delete().catch(() => {});

    // 4. Storage: verification docs (if any lingered) + avatar.
    await deleteVerificationDocs(uid);
    await admin
      .storage()
      .bucket()
      .file(`profile-photos/${uid}.jpg`)
      .delete()
      .catch(() => {});

    console.log(`cleanup complete for deleted user ${uid}`);
  } catch (e) {
    console.error(`cleanup failed for deleted user ${uid}`, e);
  }
});

// ════════════════════════════════════════════════════════════════
// 6. ADMIN DECISION (callable) — powers admin.leasereputation.com
// ════════════════════════════════════════════════════════════════
// Approve/reject from the admin dashboard. Requires the `admin` custom
// claim (set via: node verify_admin.js make-admin <email>). Approval
// reuses approveVerification() — identical semantics to the AI pipeline
// and the CLI, including doc deletion per the privacy promise.
// data: { uid: string, decision: 'approve' | 'reject', reason?: string }

exports.adminDecideVerification = onCall(
  {
    region: 'us-central1',
    secrets: [RESEND_API_KEY, TELNYX_API_KEY, TELNYX_FROM],
  },
  async (request) => {
    const token = request.auth && request.auth.token;
    if (!token || (token.admin !== true && token.role !== 'admin')) {
      throw new HttpsError('permission-denied', 'Admin only.');
    }

    const { uid, decision, reason } = request.data || {};
    if (typeof uid !== 'string' || !uid || !['approve', 'reject'].includes(decision)) {
      throw new HttpsError(
        'invalid-argument',
        "Expected { uid, decision: 'approve' | 'reject', reason? }."
      );
    }

    const db = admin.firestore();
    const verRef = db.collection('verifications').doc(uid);
    const snap = await verRef.get();
    if (!snap.exists) {
      throw new HttpsError('not-found', `No verification doc for ${uid}.`);
    }
    const v = snap.data();
    if (!['pending', 'needs_review'].includes(v.status)) {
      throw new HttpsError('failed-precondition', `Verification is already '${v.status}'.`);
    }

    if (decision === 'approve') {
      if (!v.communityId) {
        throw new HttpsError('failed-precondition', 'Verification is missing communityId.');
      }
      await approveVerification(uid, v.communityId, v.communityName || '', request.auth.uid);
      console.log(`admin ${request.auth.uid} approved verification for ${uid}`);
    } else {
      await deleteVerificationDocs(uid); // rejected docs are not retained
      await verRef.set(
        {
          status: 'rejected',
          rejectionReason:
            (typeof reason === 'string' && reason.trim().slice(0, 300)) ||
            'Your documents could not be verified. Please retake clear photos and try again.',
          reviewedAt: admin.firestore.FieldValue.serverTimestamp(),
          reviewedBy: request.auth.uid,
        },
        { merge: true }
      );
      console.log(`admin ${request.auth.uid} rejected verification for ${uid}`);
      await sendRejectedEmail(
        uid,
        (typeof reason === 'string' && reason.trim().slice(0, 300)) ||
          'Your documents could not be verified. Please retake clear photos and try again.'
      );
      await sendUserText(
        await userPhoneFor(uid),
        "LeaseReputation: We couldn't verify your documents — the reason is in your email. Fix it and resubmit in the app; nothing is held against your account."
      );
    }

    return { ok: true, uid, decision };
  }
);

// ════════════════════════════════════════════════════════════════
// 9. WELCOME TEXT (Firestore trigger on profile creation)
// ════════════════════════════════════════════════════════════════
// The welcome EMAIL fires from the auth trigger, but the phone number
// only exists once the client writes users/{uid} — so the welcome TEXT
// fires here, when the profile doc (with phone) is created.

exports.onUserProfileCreated = onDocumentCreated(
  {
    document: 'users/{uid}',
    region: 'us-central1',
    secrets: [TELNYX_API_KEY, TELNYX_FROM],
  },
  async (event) => {
    const d = event.data ? event.data.data() : null;
    if (!d || !d.phone) return;
    const first = (d.name || '').trim().split(/\s+/)[0] || 'there';
    await sendUserText(
      d.phone,
      `LeaseReputation: Welcome, ${first}! You're one verification away from posting reviews that can't be bought. Get verified: https://app.leasereputation.com — Reply STOP to opt out.`
    );
  }
);

// ════════════════════════════════════════════════════════════════
// 8. SIGNUP GEO CAPTURE (callable) — where accounts are created from
// ════════════════════════════════════════════════════════════════
// The app calls this once per account (fire-and-forget). The IP is
// read server-side from the request — the client can't spoof it — and
// geolocated via ipwho.is (keyless). Result lands in the user's
// PRIVATE subcollection (owner/admin readable only, never public),
// and only ever writes once per user. For accounts that predate this
// function, the first dashboard open after the app update captures
// their current location instead — "first seen" semantics.

exports.recordSignupGeo = onCall(
  { region: 'us-central1' },
  async (request) => {
    if (!request.auth) {
      throw new HttpsError('unauthenticated', 'Sign in first.');
    }
    const uid = request.auth.uid;
    const db = admin.firestore();
    const ref = db
      .collection('users')
      .doc(uid)
      .collection('private')
      .doc('signupGeo');
    if ((await ref.get()).exists) return { ok: true, existed: true };

    const fwd = String(request.rawRequest.headers['x-forwarded-for'] || '')
      .split(',')[0]
      .trim();
    const ip = fwd || request.rawRequest.ip || '';

    let geo = {};
    try {
      if (ip) {
        const res = await fetch(`https://ipwho.is/${encodeURIComponent(ip)}`);
        const j = await res.json();
        if (j && j.success !== false) {
          geo = {
            city: j.city || '',
            region: j.region || '',
            regionCode: j.region_code || '',
            country: j.country || '',
            countryCode: j.country_code || '',
          };
        }
      }
    } catch (e) {
      console.error(`geo lookup failed for ${uid}`, e);
    }

    await ref.set(
      { ...geo, capturedAt: admin.firestore.FieldValue.serverTimestamp() },
      { merge: true }
    );
    return { ok: true, existed: false, region: geo.regionCode || null };
  }
);

// ════════════════════════════════════════════════════════════════
// 7. ADMIN USER LIST (callable) — powers the dashboard's Users tab
// ════════════════════════════════════════════════════════════════
// Returns every account with Auth data (email, verification, claims,
// created / last sign-in) merged with the Firestore profile doc.
// Admin-claim gated; read-only.

exports.adminListUsers = onCall(
  { region: 'us-central1' },
  async (request) => {
    const token = request.auth && request.auth.token;
    if (!token || (token.admin !== true && token.role !== 'admin')) {
      throw new HttpsError('permission-denied', 'Admin only.');
    }

    // Page through Auth (1000/page; capped generously for now).
    const authUsers = [];
    let pageToken = undefined;
    do {
      const page = await admin.auth().listUsers(1000, pageToken);
      authUsers.push(...page.users);
      pageToken = page.pageToken;
    } while (pageToken && authUsers.length < 10000);

    // Merge in Firestore profile docs, signup geo, and verifications.
    const db = admin.firestore();
    const profiles = {};
    const geos = {};
    const vers = {};
    if (authUsers.length) {
      const profileRefs = authUsers.map((u) => db.collection('users').doc(u.uid));
      const geoRefs = authUsers.map((u) =>
        db.doc(`users/${u.uid}/private/signupGeo`)
      );
      const verRefs = authUsers.map((u) => db.doc(`verifications/${u.uid}`));
      const [profileDocs, geoDocs, verDocs] = await Promise.all([
        db.getAll(...profileRefs),
        db.getAll(...geoRefs),
        db.getAll(...verRefs),
      ]);
      profileDocs.forEach((d) => {
        if (d.exists) profiles[d.id] = d.data();
      });
      geoDocs.forEach((d) => {
        if (d.exists) geos[d.ref.parent.parent.id] = d.data();
      });
      verDocs.forEach((d) => {
        if (d.exists) vers[d.id] = d.data();
      });
    }

    return {
      users: authUsers.map((u) => {
        const p = profiles[u.uid] || {};
        const g = geos[u.uid] || null;
        const v = vers[u.uid] || null;
        return {
          uid: u.uid,
          email: u.email || null,
          emailVerified: u.emailVerified === true,
          disabled: u.disabled === true,
          name: p.name || u.displayName || null,
          phone: p.phone || u.phoneNumber || null,
          photoUrl: p.photoUrl || u.photoURL || null,
          identityVerified: p.identityVerified === true,
          residencyVerified: p.residencyVerified === true,
          reviewsPublished:
            typeof p.reviewsPublished === 'number' ? p.reviewsPublished : 0,
          claims: u.customClaims || {},
          createdAt: u.metadata.creationTime || null,
          lastSignInAt: u.metadata.lastSignInTime || null,
          signupGeo: g
            ? {
                city: g.city || '',
                region: g.region || '',
                regionCode: g.regionCode || '',
                country: g.country || '',
                countryCode: g.countryCode || '',
              }
            : null,
          verification: v
            ? { status: v.status || '', communityName: v.communityName || '' }
            : null,
        };
      }),
    };
  }
);

// ════════════════════════════════════════════════════════════════
// 10. OPPORTUNITY SCOUT (scheduled) — Reddit thread finder + drafts
// ════════════════════════════════════════════════════════════════
// Every 6 hours: reads recent posts from configured subreddits via
// Reddit's public JSON (READ ONLY — this agent never posts anywhere),
// prefilters for renter/apartment talk, has Claude score genuine
// opportunities and draft a transparent, thread-specific reply, then
// emails JC a digest of new hits with copy-paste-ready drafts.
//
// Config lives at Firestore agent/scout (created with defaults on the
// first run) so subs/keywords/threshold can be tuned without a deploy:
//   { enabled, subreddits: [...], minScore, userAgent }
//
// State: agent_seen/{postId} (dedupe) · agent_opportunities/{postId}.

const SCOUT_DEFAULTS = {
  enabled: true,
  subreddits: [
    'phoenix',
    'Scottsdale',
    'Tempe',
    'Dallas',
    'frisco',
    'plano',
    'boston',
    'WorcesterMA',
    'springfieldMA',
    'Apartmentliving',
    'renters',
  ],
  minScore: 60,
  userAgent: 'LeaseReputationScout/1.0 (opportunity reader; contact leasereputation@gmail.com)',
};

const SCOUT_PREFILTER =
  /(apartment|renting|renter|lease|leasing|landlord|complex|deposit|tenant|property manage|where to live|good area to rent)/i;

const SCOUT_PROMPT = (posts) => `
You are the community scout for LeaseReputation (leasereputation.com), a new platform where only verified residents can review apartment communities — scores can't be bought, negative reviews don't get deleted. Live metros: Phoenix/Scottsdale AZ, Dallas/Frisco TX, Boston MA. The founder (JC) will personally read your drafts and post the good ones from his own account.

Below are recent Reddit posts. For each, decide whether replying would be GENUINELY HELPFUL to the poster — someone asking about specific apartment communities, where to find trustworthy reviews, apartment hunting in a covered metro, landlord/deposit problems where verified reviews are relevant, or venting about fake reviews. NOT relevant: homebuying, roommate searches, short-term/hotel stays, generic city questions, posts merely containing the word "apartment".

For relevant posts, draft the reply JC would post:
- Reddit-native tone: helpful first, conversational, 2-5 sentences, no emojis, no marketing language, no exclamation-heavy hype.
- Transparent: naturally works in that he built the site ("I actually built a site for exactly this...", "full disclosure, this is my project...").
- Tailored to THEIR post — reference their specific situation. Never a generic pitch.
- Mention leasereputation.com at most once. If the metro isn't covered yet, the reply can honestly say it's live in Phoenix/Dallas/Boston and invite them to add their community.
- If the best reply wouldn't mention the site at all, that's allowed — pure helpfulness builds the account's standing.

Respond with ONLY a JSON array, no markdown fences:
[{"id": "<post id>", "relevant": true|false, "score": 0-100, "reason": "one line for JC", "reply": "the draft (empty string if not relevant)"}]

Posts:
${posts
  .map(
    (p) =>
      `---\nid: ${p.id}\nsubreddit: r/${p.sub}\ntitle: ${p.title}\nbody: ${p.body}`
  )
  .join('\n')}
`.trim();

// Reddit blocks anonymous JSON requests from datacenter IPs, so the scout
// authenticates with Reddit's official (free) OAuth API — app-only
// client_credentials token, read-only scope over public listings.
async function redditToken(userAgent) {
  try {
    const auth = Buffer.from(
      `${REDDIT_CLIENT_ID.value()}:${REDDIT_CLIENT_SECRET.value()}`
    ).toString('base64');
    const res = await fetch('https://www.reddit.com/api/v1/access_token', {
      method: 'POST',
      headers: {
        Authorization: `Basic ${auth}`,
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': userAgent,
      },
      body: 'grant_type=client_credentials',
    });
    if (!res.ok) {
      console.error('reddit token failed', res.status, await res.text());
      return null;
    }
    const j = await res.json();
    return j.access_token || null;
  } catch (e) {
    console.error('reddit token failed', e);
    return null;
  }
}

exports.opportunityScout = onSchedule(
  {
    schedule: 'every 6 hours',
    region: 'us-central1',
    secrets: [ANTHROPIC_API_KEY, RESEND_API_KEY, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET],
    timeoutSeconds: 300,
    memory: '512MiB',
  },
  async () => {
    const db = admin.firestore();

    // ── Config (self-seeding) ──
    const cfgRef = db.collection('agent').doc('scout');
    const cfgSnap = await cfgRef.get();
    let cfg = SCOUT_DEFAULTS;
    if (cfgSnap.exists) {
      cfg = { ...SCOUT_DEFAULTS, ...cfgSnap.data() };
    } else {
      await cfgRef.set(SCOUT_DEFAULTS);
    }
    if (cfg.enabled === false) {
      console.log('scout disabled via agent/scout config');
      return;
    }

    // ── Gather candidates from Reddit (read-only, official OAuth API) ──
    const token = await redditToken(cfg.userAgent);
    if (!token) {
      console.log('scout: no Reddit token this run — will retry next cycle');
      return;
    }
    const candidates = [];
    for (const sub of cfg.subreddits.slice(0, 15)) {
      try {
        const res = await fetch(
          `https://oauth.reddit.com/r/${encodeURIComponent(sub)}/new?limit=40`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
              'User-Agent': cfg.userAgent,
            },
          }
        );
        if (!res.ok) {
          console.log(`reddit r/${sub} responded ${res.status} — skipping`);
          continue;
        }
        const json = await res.json();
        const children = (json.data && json.data.children) || [];
        for (const c of children) {
          const p = c.data || {};
          const title = p.title || '';
          const body = p.selftext || '';
          if (!SCOUT_PREFILTER.test(`${title} ${body}`)) continue;
          candidates.push({
            id: p.id,
            sub,
            title: title.slice(0, 300),
            body: body.slice(0, 900),
            url: `https://www.reddit.com${p.permalink || ''}`,
            createdUtc: p.created_utc || 0,
          });
        }
      } catch (e) {
        console.error(`reddit fetch failed for r/${sub}`, e);
      }
    }
    if (!candidates.length) {
      console.log('scout: no prefilter matches this run');
      return;
    }

    // ── Dedupe against already-seen posts ──
    const fresh = [];
    for (const c of candidates) {
      const seen = await db.collection('agent_seen').doc(c.id).get();
      if (!seen.exists) fresh.push(c);
    }
    if (!fresh.length) {
      console.log('scout: nothing new since last run');
      return;
    }
    // Newest first, keep the Claude call bounded.
    fresh.sort((a, b) => b.createdUtc - a.createdUtc);
    const batch = fresh.slice(0, 25);

    // ── Score + draft with Claude (one call for the whole batch) ──
    let verdicts = [];
    try {
      const apiRes = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': ANTHROPIC_API_KEY.value(),
          'anthropic-version': '2023-06-01',
        },
        body: JSON.stringify({
          model: 'claude-sonnet-4-6',
          max_tokens: 4000,
          messages: [{ role: 'user', content: SCOUT_PROMPT(batch) }],
        }),
      });
      if (!apiRes.ok) {
        console.error('scout: Anthropic API error', apiRes.status, await apiRes.text());
        return; // leave posts unseen — retried next run
      }
      const apiData = await apiRes.json();
      const rawText = (apiData.content || [])
        .filter((b) => b.type === 'text')
        .map((b) => b.text)
        .join('\n');
      verdicts = JSON.parse(rawText.replace(/```json|```/g, '').trim());
      if (!Array.isArray(verdicts)) throw new Error('not an array');
    } catch (e) {
      console.error('scout: could not parse verdicts', e);
      return; // leave posts unseen — retried next run
    }

    // ── Persist results + mark seen ──
    const byId = {};
    batch.forEach((c) => (byId[c.id] = c));
    const hits = [];
    for (const v of verdicts) {
      const c = byId[v.id];
      if (!c) continue;
      await db.collection('agent_seen').doc(c.id).set({
        sub: c.sub,
        seenAt: admin.firestore.FieldValue.serverTimestamp(),
      });
      const score = typeof v.score === 'number' ? v.score : 0;
      if (v.relevant === true && score >= cfg.minScore && v.reply) {
        const hit = {
          sub: c.sub,
          title: c.title,
          url: c.url,
          score,
          reason: String(v.reason || '').slice(0, 300),
          draftReply: String(v.reply).slice(0, 2000),
          foundAt: admin.firestore.FieldValue.serverTimestamp(),
          status: 'new',
        };
        await db.collection('agent_opportunities').doc(c.id).set(hit);
        hits.push(hit);
      }
    }
    // Also mark the overflow (not sent to Claude this run) as unseen — they
    // stay eligible for the next run automatically since we never wrote them.

    console.log(
      `scout: ${batch.length} scored, ${hits.length} opportunities found`
    );
    if (!hits.length) return;

    // ── Morning digest ──
    hits.sort((a, b) => b.score - a.score);
    const rows = hits
      .slice(0, 10)
      .map(
        (h) => `
      <div style="margin:0 0 22px;padding:16px;background:#F7F7FC;border-radius:12px;border:1px solid #E7E7F4;">
        <div style="font-size:12px;color:#6E6E92;font-weight:700;">r/${h.sub} · relevance ${h.score}/100</div>
        <div style="font-size:15px;font-weight:700;margin:4px 0 6px;"><a href="${h.url}" style="color:#4C4FE6;text-decoration:none;">${h.title.replace(/</g, '&lt;')}</a></div>
        <div style="font-size:12.5px;color:#6E6E92;margin-bottom:10px;">${String(h.reason).replace(/</g, '&lt;')}</div>
        <div style="font-size:13.5px;line-height:1.55;color:#33334D;background:#FFFFFF;border:1px dashed #C9C9E8;border-radius:8px;padding:12px;white-space:pre-wrap;">${String(h.draftReply).replace(/</g, '&lt;')}</div>
      </div>`
      )
      .join('');
    await sendUserEmail(
      ADMIN_EMAIL,
      `Scout: ${hits.length} Reddit ${hits.length === 1 ? 'opportunity' : 'opportunities'} found`,
      emailShell({
        heading: `${hits.length} ${hits.length === 1 ? 'thread' : 'threads'} worth replying to`,
        bodyHtml: `<p style="margin:0 0 16px;">Fresh threads where a reply from you would genuinely help. Open each, read the room, tweak the draft to taste, post from your account.</p>${rows}<p style="margin:8px 0 0;font-size:12px;color:#9A9AB8;">Tune the scout anytime: Firestore → agent/scout (subreddits, minScore, enabled).</p>`,
        ctaText: null,
        ctaUrl: null,
      })
    );
  }
);

// ════════════════════════════════════════════════════════════════
// 11. REPORT ALERT (Firestore trigger) — new review reports → email
// ════════════════════════════════════════════════════════════════

exports.onReportCreated = onDocumentCreated(
  {
    document: 'reports/{reportId}',
    region: 'us-central1',
    secrets: [RESEND_API_KEY],
  },
  async (event) => {
    const r = event.data ? event.data.data() : null;
    if (!r) return;
    let communityName = r.communityId || '';
    let reviewAuthor = '';
    try {
      const db = admin.firestore();
      const [community, review] = await Promise.all([
        db.collection('communities').doc(r.communityId).get(),
        db
          .collection('communities')
          .doc(r.communityId)
          .collection('reviews')
          .doc(r.reviewId)
          .get(),
      ]);
      communityName =
        (community.data() && community.data().name) || communityName;
      reviewAuthor = (review.data() && review.data().authorName) || '';
    } catch (_) {}
    await notifyAdmin(
      `LeaseReputation: review reported (${r.reason})`,
      `A review was reported.\n\ncommunity: ${communityName}\nreview by: ${reviewAuthor}\nreason: ${r.reason}\ndetail: ${r.detail || '(none)'}\nreported by: ${r.reportedBy}\n\nHandle it: https://admin.leasereputation.com (Reports tab)`
    );
  }
);

// ═══════════════════════════════════════════════════════════════════════════
// COMMUNITY CLAIM PIPELINE — v2, with automated screening
// Replaces the entire previous claim pipeline block in functions/index.js.
//
// What the trigger now does on every new claim request:
//   1. DOMAIN CHECK (deterministic): fetches the community's website from
//      Places, compares its domain to the claimant's work-email domain.
//      Free-mail providers (gmail etc.) are auto-flagged as no-match.
//   2. AI DOCUMENT READ: sends the uploaded evidence to Claude, which
//      reports whether it plausibly ties the claimant to the property,
//      with a confidence level and findings.
//   3. Stamps the full screening result onto the claimRequest doc and
//      emails the admin a pre-analyzed summary.
// The DECISION stays human (adminDecideClaim, unchanged below) — AI
// screens, you decide. Flip AUTO_APPROVE_DOMAIN_MATCH to true later if
// domain-verified claims should skip the queue entirely.
//
// Requires at the top of index.js (add to existing requires if missing):
//   const { onCall, HttpsError } = require('firebase-functions/v2/https');
//   const { onDocumentCreated } = require('firebase-functions/v2/firestore');
//   const { defineSecret } = require('firebase-functions/params');
//   const admin = require('firebase-admin');
//   const RESEND_API_KEY = defineSecret('RESEND_API_KEY');
//   const PLACES_API_KEY = defineSecret('PLACES_API_KEY');
//   const ANTHROPIC_API_KEY = defineSecret('ANTHROPIC_API_KEY');
// (All three secrets already exist in Secret Manager. If the earlier
//  ANTHROPIC placeholder was never replaced with a real sk-ant- key, do
//  that before deploying: firebase functions:secrets:set ANTHROPIC_API_KEY)
// ═══════════════════════════════════════════════════════════════════════════

const CLAIM_ADMIN_EMAIL = 'info@leasereputation.com';
const CLAIM_FROM = 'LeaseReputation <info@leasereputation.com>';
const AUTO_APPROVE_DOMAIN_MATCH = false; // human decides everything for now

const FREE_MAIL = new Set([
  'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'icloud.com',
  'aol.com', 'live.com', 'msn.com', 'proton.me', 'protonmail.com',
  'mail.com', 'gmx.com', 'yandex.com',
]);

function claimDomainOf(input) {
  if (!input) return '';
  let s = String(input).trim().toLowerCase();
  if (s.includes('@')) s = s.split('@').pop();
  s = s.replace(/^https?:\/\//, '').split('/')[0].split(':')[0];
  return s.replace(/^www\./, '');
}

function claimDomainsMatch(a, b) {
  if (!a || !b) return false;
  return a === b || a.endsWith('.' + b) || b.endsWith('.' + a);
}

async function claimSendEmail(apiKey, to, subject, html) {
  try {
    await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({ from: CLAIM_FROM, to: [to], subject, html }),
    });
  } catch (e) {
    console.error('claim email send failed:', e);
  }
}

async function claimDeleteEvidence(path) {
  if (!path) return;
  try {
    await admin.storage().bucket().file(path).delete();
  } catch (e) {
    console.warn('claim evidence delete failed (may already be gone):', path);
  }
}

// ── Screening step A: community website via Places, domain compare ─────────
async function claimDomainScreen(placesKey, communityId, workEmail) {
  const out = {
    emailDomain: claimDomainOf(workEmail),
    freeEmail: false,
    communityWebsite: '',
    communityDomain: '',
    domainMatch: false,
  };
  out.freeEmail = FREE_MAIL.has(out.emailDomain);
  try {
    const comm = await admin
      .firestore()
      .collection('communities')
      .doc(communityId)
      .get();
    const placeId = (comm.data() || {}).placeId || communityId;
    const res = await fetch(
      `https://places.googleapis.com/v1/places/${placeId}`,
      {
        headers: {
          'X-Goog-Api-Key': placesKey,
          'X-Goog-FieldMask': 'websiteUri',
        },
      }
    );
    if (res.ok) {
      const data = await res.json();
      out.communityWebsite = data.websiteUri || '';
      out.communityDomain = claimDomainOf(out.communityWebsite);
      out.domainMatch =
        !out.freeEmail &&
        claimDomainsMatch(out.emailDomain, out.communityDomain);
    }
  } catch (e) {
    console.warn('domain screen failed:', e);
  }
  return out;
}

// ── Screening step B: Claude reads the evidence document ───────────────────
async function claimAiScreen(anthropicKey, d) {
  const out = {
    ran: false,
    confidence: 'unknown',
    findings: '',
    error: '',
  };
  if (!anthropicKey || !anthropicKey.startsWith('sk-ant-')) {
    out.error = 'ANTHROPIC_API_KEY not configured';
    return out;
  }
  if (!d.evidencePath) {
    out.error = 'no evidence file';
    return out;
  }
  try {
    const file = admin.storage().bucket().file(d.evidencePath);
    const [meta] = await file.getMetadata();
    const contentType = meta.contentType || 'image/jpeg';
    const size = parseInt(meta.size || '0', 10);
    if (size > 4_500_000) {
      out.error = 'evidence too large for automated read';
      return out;
    }
    const [bytes] = await file.download();
    const b64 = bytes.toString('base64');

    const block =
      contentType === 'application/pdf'
        ? {
            type: 'document',
            source: {
              type: 'base64',
              media_type: 'application/pdf',
              data: b64,
            },
          }
        : {
            type: 'image',
            source: { type: 'base64', media_type: contentType, data: b64 },
          };

    const prompt = `You are screening a property-manager claim for an apartment review platform. Someone named "${d.claimantName}" ("${d.role}") at company "${d.company}" (work email ${d.workEmail}) claims to manage the community "${d.communityName}" at ${d.communityAddress}. The attached file is their evidence.

Assess: does this document plausibly tie THIS person and/or THIS company to THIS property? Look for matching names, company names, the property name or address, letterhead, badges, or management-agreement language. Note anything suspicious (editing artifacts, mismatched names, generic templates).

Reply with ONLY a JSON object, no markdown fences: {"confidence": "high"|"medium"|"low"|"reject", "findings": "<2-3 sentences: what the document is, what matches, what doesn't>"}`;

    const res = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': anthropicKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-6',
        max_tokens: 500,
        messages: [
          { role: 'user', content: [block, { type: 'text', text: prompt }] },
        ],
      }),
    });
    if (!res.ok) {
      out.error = `anthropic ${res.status}: ${(await res.text()).slice(0, 200)}`;
      return out;
    }
    const data = await res.json();
    const text = (data.content || [])
      .filter((c) => c.type === 'text')
      .map((c) => c.text)
      .join('');
    const parsed = JSON.parse(text.replace(/```json|```/g, '').trim());
    out.ran = true;
    out.confidence = ['high', 'medium', 'low', 'reject'].includes(
      parsed.confidence
    )
      ? parsed.confidence
      : 'unknown';
    out.findings = String(parsed.findings || '').slice(0, 1000);
  } catch (e) {
    out.error = String(e).slice(0, 300);
    console.warn('ai screen failed:', e);
  }
  return out;
}

// ── 1. New claim request → screen, stamp, notify ───────────────────────────
exports.onClaimRequestSubmitted = onDocumentCreated(
  {
    document: 'claimRequests/{requestId}',
    secrets: [RESEND_API_KEY, PLACES_API_KEY, ANTHROPIC_API_KEY],
    timeoutSeconds: 120,
    memory: '512MiB',
  },
  async (event) => {
    const d = event.data?.data();
    if (!d) return;
    const requestId = event.params.requestId;

    const [domain, ai] = await Promise.all([
      claimDomainScreen(PLACES_API_KEY.value(), d.communityId, d.workEmail),
      claimAiScreen(ANTHROPIC_API_KEY.value(), d),
    ]);

    const screening = {
      ...domain,
      ai,
      screenedAt: admin.firestore.FieldValue.serverTimestamp(),
      recommendation:
        domain.domainMatch && ['high', 'medium'].includes(ai.confidence)
          ? 'approve'
          : domain.domainMatch || ai.confidence === 'high'
            ? 'lean-approve'
            : ai.confidence === 'reject' || domain.freeEmail
              ? 'lean-reject'
              : 'review',
    };

    try {
      await event.data.ref.update({ screening });
    } catch (e) {
      console.error('failed to stamp screening:', e);
    }

    const badge = (ok, label) => (ok ? `✅ ${label}` : `⚠️ ${label}`);
    const html = `
      <h2>New community claim request — ${screening.recommendation.toUpperCase()}</h2>
      <p><b>${d.communityName || d.communityId}</b><br/>${d.communityAddress || ''}</p>
      <p><b>Claimant:</b> ${d.claimantName || '?'} — ${d.role || '?'}<br/>
      <b>Company:</b> ${d.company || '?'}<br/>
      <b>Work email:</b> ${d.workEmail || '?'} ${
        domain.freeEmail ? '(free-mail provider ⚠️)' : ''
      }<br/>
      <b>Phone:</b> ${d.phone || '—'}</p>
      <h3>Automated screening</h3>
      <p>${badge(
        domain.domainMatch,
        `Domain match: ${domain.emailDomain || '?'} vs ${
          domain.communityDomain || 'no website found'
        }`
      )}<br/>
      ${
        ai.ran
          ? `${badge(
              ['high', 'medium'].includes(ai.confidence),
              `Document read: confidence ${ai.confidence}`
            )}<br/><i>${ai.findings}</i>`
          : `⚠️ Document not auto-read (${ai.error || 'unknown'})`
      }</p>
      <p>Decide with adminDecideClaim, requestId: <code>${requestId}</code></p>`;

    await claimSendEmail(
      RESEND_API_KEY.value(),
      CLAIM_ADMIN_EMAIL,
      `Claim [${screening.recommendation}]: ${d.communityName || d.communityId} (${
        d.company || '?'
      })`,
      html
    );

    if (AUTO_APPROVE_DOMAIN_MATCH && screening.recommendation === 'approve') {
      console.log(
        `AUTO_APPROVE would fire for ${requestId} — flag is documented but approval remains manual by design.`
      );
    }
  }
);

// ── 2. Admin decision: approve / reject (unchanged from v1) ────────────────
exports.adminDecideClaim = onCall(
  { secrets: [RESEND_API_KEY] },
  async (request) => {
    const auth = request.auth;
    const isAdmin =
      auth && (auth.token.admin === true || auth.token.role === 'admin');
    if (!isAdmin) {
      throw new HttpsError('permission-denied', 'Admin only.');
    }

    const { requestId, decision, note } = request.data || {};
    if (!requestId || !['approve', 'reject'].includes(decision)) {
      throw new HttpsError(
        'invalid-argument',
        'Need requestId and decision ("approve" | "reject").'
      );
    }

    const db = admin.firestore();
    const reqRef = db.collection('claimRequests').doc(requestId);
    const snap = await reqRef.get();
    if (!snap.exists) {
      throw new HttpsError('not-found', `No claim request ${requestId}.`);
    }
    const d = snap.data();
    if (d.status !== 'pending') {
      throw new HttpsError(
        'failed-precondition',
        `Request already ${d.status}.`
      );
    }

    const uid = d.uid;
    const communityId = d.communityId;

    if (decision === 'approve') {
      const userRecord = await admin.auth().getUser(uid);
      const existing = userRecord.customClaims || {};
      if (existing.role === 'renter') {
        throw new HttpsError(
          'failed-precondition',
          'Claimant account has the renter role (verified reviewer). ' +
            'Operators must use a separate business account — ask them to ' +
            'resubmit from one.'
        );
      }

      const commRef = db.collection('communities').doc(communityId);
      const comm = await commRef.get();
      const claimedBy = (comm.data() || {}).claimedBy || '';
      if (claimedBy && claimedBy !== uid) {
        throw new HttpsError(
          'failed-precondition',
          'Community is already claimed by another account.'
        );
      }

      const batch = db.batch();
      batch.set(
        db
          .collection('communities')
          .doc(communityId)
          .collection('claims')
          .doc(uid),
        {
          grantedAt: admin.firestore.FieldValue.serverTimestamp(),
          claimantName: d.claimantName || '',
          company: d.company || '',
          workEmail: d.workEmail || '',
          requestId,
        }
      );
      batch.update(commRef, {
        claimedBy: uid,
        managerInfo: {
          company: d.company || '',
          name: d.claimantName || '',
          claimedAt: admin.firestore.FieldValue.serverTimestamp(),
        },
      });
      batch.update(reqRef, {
        status: 'approved',
        decidedAt: admin.firestore.FieldValue.serverTimestamp(),
        decidedBy: auth.uid,
        ...(note ? { decisionNote: note } : {}),
      });
      await batch.commit();

      await admin
        .auth()
        .setCustomUserClaims(uid, { ...existing, role: 'operator' });

      await claimDeleteEvidence(d.evidencePath);

      await claimSendEmail(
        RESEND_API_KEY.value(),
        d.workEmail,
        `You now manage ${d.communityName} on LeaseReputation`,
        `<h2>Claim approved</h2>
         <p>Your claim for <b>${d.communityName}</b> is verified. Sign out
         and back in to activate your management access. You can now keep
         your community's details accurate and post management responses to
         reviews.</p>
         <p>A reminder of what claiming never does: change your Reputation
         Score, remove reviews, or reveal reviewer identities. Scores are
         computed only from verified residents — that integrity is what
         makes a good score worth having.</p>
         <p>— LeaseReputation</p>`
      );
      return { ok: true, decision: 'approved', communityId, uid };
    }

    await reqRef.update({
      status: 'rejected',
      decidedAt: admin.firestore.FieldValue.serverTimestamp(),
      decidedBy: auth.uid,
      ...(note ? { decisionNote: note } : {}),
    });
    await claimDeleteEvidence(d.evidencePath);
    await claimSendEmail(
      RESEND_API_KEY.value(),
      d.workEmail,
      `About your LeaseReputation claim for ${d.communityName}`,
      `<h2>We couldn't verify this claim</h2>
       <p>Your claim for <b>${d.communityName}</b> wasn't approved.${
         note ? ` Note from our team: ${note}` : ''
       }</p>
       <p>The fastest path to approval is a work email on your management
       company's domain plus clear evidence tying you to the property
       (letterhead, a management agreement page, or a business card). You're
       welcome to resubmit.</p>
       <p>— LeaseReputation</p>`
    );
    return { ok: true, decision: 'rejected' };
  }
);