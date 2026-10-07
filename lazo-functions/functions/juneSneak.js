// JC-LAZO-FN-1007-RESTORE: recovered from the 2026-09-21 production build (the local tree never had it).
// Lazo Studio — June Sneak Peek (v57)
// The day after the wedding, a photographer is exhausted and the couple is
// desperate for something to post. June looks at the take, picks the frames
// that carry the day, and writes the words - into the thread that already
// holds their contract and their invoice.
const { onCall, HttpsError } = require("firebase-functions/v2/https");
const { defineSecret } = require("firebase-functions/params");
const admin = require("firebase-admin");
const Anthropic = require("@anthropic-ai/sdk");

const ANTHROPIC_API_KEY = defineSecret("ANTHROPIC_API_KEY");

const MAX_IMAGES = 60;      // what one sitting can reasonably hold
const BATCH = 12;           // images per vision call

function mediaTypeFor(path) {
  const p = path.toLowerCase();
  if (p.endsWith(".png")) return "image/png";
  if (p.endsWith(".webp")) return "image/webp";
  return "image/jpeg";
}

async function loadImage(bucket, path) {
  const [buf] = await bucket.file(path).download();
  if (buf.length > 4.5 * 1024 * 1024) return null;   // API per-image ceiling
  return {
    type: "image",
    source: {
      type: "base64",
      media_type: mediaTypeFor(path),
      data: buf.toString("base64"),
    },
  };
}

exports.juneSneakPeek = onCall(
  { region: "us-central1", timeoutSeconds: 540, memory: "2GiB",
    secrets: [ANTHROPIC_API_KEY] },
  async (request) => {
    if (!request.auth) {
      throw new HttpsError("unauthenticated", "Sign in first.");
    }
    const db = admin.firestore();
    const uid = request.auth.uid;
    const vendorId = (request.data && request.data.vendorId || "").toString();
    const inquiryId = (request.data && request.data.inquiryId || "").toString();
    const paths = Array.isArray(request.data && request.data.paths)
      ? request.data.paths.slice(0, MAX_IMAGES).map((p) => p.toString())
      : [];
    const want = Math.min(Math.max(
      Number(request.data && request.data.count || 20), 6), 30);

    const vSnap = await db.collection("vendors").doc(vendorId).get();
    if (!vSnap.exists || vSnap.data().claimedBy !== uid) {
      throw new HttpsError("permission-denied", "You do not own this profile.");
    }
    const v = vSnap.data();
    if ((v.tier || "") !== "studio" && v.foundingPreview !== true) {
      throw new HttpsError("failed-precondition", "studio-required");
    }
    if (paths.length < 4) {
      throw new HttpsError("invalid-argument", "Upload a few more frames.");
    }

    const today = new Date().toISOString().slice(0, 10);
    const used = (v.juneVDay === today) ? Number(v.juneVCount || 0) : 0;
    if (used >= 60) {
      throw new HttpsError("resource-exhausted",
        "June has hit today's limit - she'll be back tomorrow.");
    }

    // couple context makes the words specific rather than generic
    let coupleName = "";
    let weddingDate = "";
    let venue = "";
    let metro = "";
    try {
      const iq = await db.collection("inquiries").doc(inquiryId).get();
      if (iq.exists) {
        const d = iq.data();
        coupleName = (d.coupleName || "").toString();
        const si = d.structuredIntent || {};
        weddingDate = (si.weddingDate || "").toString();
        venue = (si.venue || si.venueName || "").toString();
        metro = (si.metroDisplay || si.metro || si.metroId || "").toString();
      }
    } catch (e) { /* context is a bonus */ }
    if (!metro) {
      // fall back to the vendor's own home market, never a guess
      metro = (v.metroDisplay || v.city || v.metroId || "").toString();
    }
    metro = metro.replace(/-/g, " ").trim();

    // What did they actually shoot? A photographer never "filmed" anything.
    const cats = Array.isArray(v.categories) ? v.categories : [];
    const isVideo = cats.indexOf("wedding-videographers") >= 0;
    const isPhoto = cats.indexOf("wedding-photographers") >= 0;
    const craftWord = (isVideo && !isPhoto) ? "filmed"
      : (isPhoto && !isVideo) ? "photographed" : "captured";
    const craftNoun = (isVideo && !isPhoto) ? "wedding videographer"
      : (isPhoto && !isVideo) ? "wedding photographer" : "wedding photographer and videographer";

    const bucket = admin.storage().bucket();
    const anthropic = new Anthropic({ apiKey: ANTHROPIC_API_KEY.value() });

    // ---- pass one: score each batch -------------------------------------
    const scored = [];
    for (let i = 0; i < paths.length; i += BATCH) {
      const slice = paths.slice(i, i + BATCH);
      const content = [];
      const loaded = [];
      for (let k = 0; k < slice.length; k++) {
        try {
          const img = await loadImage(bucket, slice[k]);
          if (!img) continue;
          content.push({ type: "text",
            text: "Image " + (loaded.length + 1) + ":" });
          content.push(img);
          loaded.push(slice[k]);
        } catch (e) { console.warn("skip image", slice[k], e.message); }
      }
      if (!loaded.length) continue;
      content.push({ type: "text", text:
        "Score each image above from 0-100 as a wedding sneak-peek pick.\n" +
        "Reward: genuine emotion, a clear story beat (getting ready, first " +
        "look, ceremony, portraits, reception, dancing), strong light, clean " +
        "composition, the couple clearly visible.\n" +
        "Penalise: blinks, blur, obstructed faces, near-duplicates, backs of " +
        "heads, test frames, empty rooms with nothing happening.\n" +
        "Also tag each with one moment label from: getting ready, details, " +
        "first look, ceremony, portraits, family, reception, dancing, " +
        "send-off, other.\n" +
        "Return ONLY a JSON array like " +
        "[{\"i\":1,\"score\":87,\"moment\":\"ceremony\",\"why\":\"six words\"}]. " +
        "No prose, no code fences." });

      try {
        const msg = await anthropic.messages.create({
          model: "claude-sonnet-4-6",
          max_tokens: 1500,
          messages: [{ role: "user", content: content }],
        });
        let text = "";
        for (const b of (msg.content || [])) {
          if (b.type === "text") text += b.text;
        }
        text = text.trim().replace(/^```(json)?/i, "").replace(/```$/, "").trim();
        const arr = JSON.parse(text);
        for (const row of arr) {
          const idx = Number(row.i) - 1;
          if (idx >= 0 && idx < loaded.length) {
            scored.push({
              path: loaded[idx],
              score: Number(row.score || 0),
              moment: (row.moment || "other").toString(),
              why: (row.why || "").toString(),
            });
          }
        }
      } catch (e) {
        console.error("sneak batch failed", e.message);
      }
    }

    if (!scored.length) {
      throw new HttpsError("internal",
        "June could not read those images - try smaller web-res JPEGs.");
    }

    // ---- spread the picks across the day, not just the prettiest ---------
    scored.sort((a, b) => b.score - a.score);
    const byMoment = {};
    const picks = [];
    for (const s of scored) {
      const n = byMoment[s.moment] || 0;
      const cap = Math.max(2, Math.ceil(want / 5));
      if (n < cap && picks.length < want) {
        byMoment[s.moment] = n + 1;
        picks.push(s);
      }
    }
    for (const s of scored) {
      if (picks.length >= want) break;
      if (picks.indexOf(s) < 0) picks.push(s);
    }

    // ---- pass two: the words --------------------------------------------
    const momentList = picks.map((p) => p.moment).join(", ");
    let caption = "";
    let message = "";
    try {
      const msg2 = await anthropic.messages.create({
        model: "claude-sonnet-4-6",
        max_tokens: 900,
        system:
          "You are June, the assistant inside Lazo. You write for wedding " +
          "vendors in their own voice: warm, specific, never salesy, never " +
          "stuffed with hashtags or cliches like 'magical day' or 'tied the " +
          "knot'.\n\n" +
          "Hard rules:\n" +
          "- NEVER invent a city, region, venue, season or date. Use only " +
          "what you are given. If you were given no location, write no " +
          "location hashtag and no location reference.\n" +
          "- NEVER invent hashtags about places or events you were not told " +
          "about. At most 5 hashtags, and every one must be true.\n" +
          "- Use the exact craft verb you are given. A photographer did not " +
          "film anything; a videographer did not photograph anything.\n" +
          "- Do not name the couple more than once in each piece.\n" +
          "Return ONLY JSON.",
        messages: [{ role: "user", content:
          "A " + craftNoun + " named " + (v.name || "the studio") +
          " just " + craftWord + " a wedding" +
          (coupleName ? " for " + coupleName : "") +
          (venue ? " at " + venue : "") +
          (weddingDate ? " on " + weddingDate : "") + ".\n" +
          (metro ? "Market: " + metro + " (the ONLY place you may name).\n"
                 : "Location: unknown - name no city and use no place hashtag.\n") +
          "The sneak peek covers these moments: " + momentList + ".\n\n" +
          "Write two things:\n" +
          "1. instagram: a caption for the sneak-peek post, 2-4 sentences, " +
          "the vendor's own voice, at most 5 tasteful hashtags at the end.\n" +
          "2. message: a short note (2-3 sentences) from the vendor to the " +
          "couple, delivering these images the day after, warm and personal, " +
          "no hashtags.\n\n" +
          "Return ONLY {\"instagram\":\"...\",\"message\":\"...\"}" }],
      });
      let t2 = "";
      for (const b of (msg2.content || [])) {
        if (b.type === "text") t2 += b.text;
      }
      t2 = t2.trim().replace(/^```(json)?/i, "").replace(/```$/, "").trim();
      const parsed = JSON.parse(t2);
      caption = (parsed.instagram || "").toString();
      message = (parsed.message || "").toString();
    } catch (e) {
      console.error("sneak words failed", e.message);
    }

    // signed urls so the widget can show the picks back
    const out = [];
    for (const p of picks) {
      let url = "";
      try {
        const [signed] = await bucket.file(p.path).getSignedUrl({
          action: "read",
          expires: Date.now() + 30 * 24 * 3600 * 1000,
        });
        url = signed;
      } catch (e) { /* the path still identifies it */ }
      out.push({ path: p.path, url: url, score: p.score,
        moment: p.moment, why: p.why });
    }

    await vSnap.ref.set({
      juneVDay: today,
      juneVCount: used + 1,
    }, { merge: true });

    console.log("sneak peek", vendorId, "scored", scored.length,
      "picked", out.length);
    return { picks: out, caption: caption, message: message,
      considered: scored.length };
  }
);

// ---------------------------------------------------------------- teaser
// A videographer's day-after is a different animal: one film, not sixty
// frames. June cannot watch it - so she does the part they are too tired
// for, which is the words.
exports.juneTeaser = onCall(
  { region: "us-central1", timeoutSeconds: 120, memory: "512MiB",
    secrets: [ANTHROPIC_API_KEY] },
  async (request) => {
    if (!request.auth) {
      throw new HttpsError("unauthenticated", "Sign in first.");
    }
    const db = admin.firestore();
    const uid = request.auth.uid;
    const vendorId = (request.data && request.data.vendorId || "").toString();
    const inquiryId = (request.data && request.data.inquiryId || "").toString();
    const url = (request.data && request.data.url || "").toString().trim();
    const vibe = (request.data && request.data.vibe || "").toString().slice(0, 200);

    const vSnap = await db.collection("vendors").doc(vendorId).get();
    if (!vSnap.exists || vSnap.data().claimedBy !== uid) {
      throw new HttpsError("permission-denied", "You do not own this profile.");
    }
    const v = vSnap.data();
    if ((v.tier || "") !== "studio" && v.foundingPreview !== true) {
      throw new HttpsError("failed-precondition", "studio-required");
    }
    if (!/^https?:\/\//i.test(url)) {
      throw new HttpsError("invalid-argument", "Paste the full link to your film.");
    }

    const today = new Date().toISOString().slice(0, 10);
    const used = (v.juneVDay === today) ? Number(v.juneVCount || 0) : 0;
    if (used >= 60) {
      throw new HttpsError("resource-exhausted",
        "June has hit today's limit - she'll be back tomorrow.");
    }

    let coupleName = "", weddingDate = "", venue = "";
    try {
      const iq = await db.collection("inquiries").doc(inquiryId).get();
      if (iq.exists) {
        const d = iq.data();
        coupleName = (d.coupleName || "").toString();
        const si = d.structuredIntent || {};
        weddingDate = (si.weddingDate || "").toString();
        venue = (si.venue || si.venueName || "").toString();
      }
    } catch (e) { /* context is a bonus */ }

    let caption = "", message = "";
    try {
      const anthropic = new Anthropic({ apiKey: ANTHROPIC_API_KEY.value() });
      const msg = await anthropic.messages.create({
        model: "claude-sonnet-4-6",
        max_tokens: 900,
        system:
          "You are June, the assistant inside Lazo. You write for wedding " +
          "vendors in their own voice: warm, specific, never salesy. Never " +
          "use 'magical day', 'tied the knot', 'said I do' or hashtag " +
          "soup. Return ONLY JSON.",
        messages: [{ role: "user", content:
          "A wedding videographer named " + (v.name || "the studio") +
          " just finished a teaser film" +
          (coupleName ? " for " + coupleName : "") +
          (venue ? " at " + venue : "") +
          (weddingDate ? ", " + weddingDate : "") + ".\n" +
          (vibe ? "What the film feels like, in their words: " + vibe + "\n" : "") +
          "\nWrite two things:\n" +
          "1. instagram: a caption for posting the teaser, 2-4 sentences in " +
          "the videographer's voice, at most 5 tasteful hashtags at the end.\n" +
          "2. message: a short note (2-3 sentences) from the videographer to " +
          "the couple, sending them the teaser the day after, warm and " +
          "personal, no hashtags.\n\n" +
          "Return ONLY {\"instagram\":\"...\",\"message\":\"...\"}" }],
      });
      let txt = "";
      for (const b of (msg.content || [])) {
        if (b.type === "text") txt += b.text;
      }
      txt = txt.trim().replace(/^```(json)?/i, "").replace(/```$/, "").trim();
      const parsed = JSON.parse(txt);
      caption = (parsed.instagram || "").toString();
      message = (parsed.message || "").toString();
    } catch (e) {
      console.error("juneTeaser failed", e.message);
      throw new HttpsError("internal", "June could not write that one - try again.");
    }

    await vSnap.ref.set({ juneVDay: today, juneVCount: used + 1 },
      { merge: true });
    console.log("teaser words", vendorId);
    return { caption: caption, message: message };
  }
);
