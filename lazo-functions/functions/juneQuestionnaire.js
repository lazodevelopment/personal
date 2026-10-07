// JC-LAZO-FN-1007-RESTORE: recovered from the 2026-09-21 production build (the local tree never had it).
// Lazo — June drafts questionnaires (v50)
// The starter sets know the craft. June knows THIS vendor: their packages,
// their attributes, the way they already talk to couples.
const { onCall, HttpsError } = require("firebase-functions/v2/https");
const { defineSecret } = require("firebase-functions/params");
const admin = require("firebase-admin");
const Anthropic = require("@anthropic-ai/sdk");

const ANTHROPIC_API_KEY = defineSecret("ANTHROPIC_API_KEY");

const CAT_LABEL = {
  "wedding-photographers": "wedding photographer",
  "wedding-videographers": "wedding videographer",
  "wedding-venues": "wedding venue",
  "wedding-planners": "wedding planner",
  "wedding-djs": "wedding DJ",
  "wedding-florists": "wedding florist",
  "wedding-caterers": "wedding caterer",
  "wedding-cakes": "wedding cake and dessert maker",
  "hair-and-makeup": "wedding hair and makeup artist",
  "wedding-officiants": "wedding officiant",
  "wedding-transportation": "wedding transportation provider",
  "wedding-rentals": "wedding rental company",
  "wedding-bands": "wedding band",
  "wedding-invitations": "wedding stationer",
  "day-of-coordination": "day-of wedding coordinator",
};

exports.juneQuestionnaire = onCall(
  { region: "us-central1", timeoutSeconds: 120, memory: "512MiB",
    secrets: [ANTHROPIC_API_KEY] },
  async (request) => {
    if (!request.auth) {
      throw new HttpsError("unauthenticated", "Sign in first.");
    }
    const db = admin.firestore();
    const uid = request.auth.uid;
    const vendorId = (request.data && request.data.vendorId || "").toString();
    const mode = (request.data && request.data.mode || "draft").toString();
    const brief = (request.data && request.data.brief || "").toString().slice(0, 400);
    const existing = Array.isArray(request.data && request.data.questions)
      ? request.data.questions.slice(0, 40).map((q) => q.toString().slice(0, 300))
      : [];

    const vSnap = await db.collection("vendors").doc(vendorId).get();
    if (!vSnap.exists || vSnap.data().claimedBy !== uid) {
      throw new HttpsError("permission-denied", "You do not own this profile.");
    }
    const v = vSnap.data();
    const tier = (v.tier || "").toString();
    if (tier !== "studio" && v.foundingPreview !== true) {
      throw new HttpsError("failed-precondition", "studio-required");
    }

    // daily cap shared with the rest of June
    const today = new Date().toISOString().slice(0, 10);
    const used = (v.juneVDay === today) ? Number(v.juneVCount || 0) : 0;
    if (used >= 60) {
      throw new HttpsError("resource-exhausted",
        "June has hit today's limit - she'll be back tomorrow.");
    }

    const cats = Array.isArray(v.categories) ? v.categories : [];
    const craft = CAT_LABEL[cats[0]] || "wedding vendor";
    const packages = Array.isArray(v.packages)
      ? v.packages.map((p) => (p && p.name ? p.name : "")).filter(Boolean).join(", ")
      : "";
    const at = v.attributes || {};
    const traits = [];
    if (at.drone === true) traits.push("offers drone coverage");
    if (at.sameDayEdit === true) traits.push("offers same-day edits");
    if (at.filmCapture === true) traits.push("shoots film");
    if (at.onSiteCatering === true) traits.push("has on-site catering");
    if (at.lodging === true) traits.push("has lodging on site");
    if (at.ceremonyAndReception === true) traits.push("hosts ceremony and reception");
    if (Array.isArray(at.styles) && at.styles.length) {
      traits.push("style: " + at.styles.slice(0, 4).join(", "));
    }

    const profile = [
      "Business: " + (v.name || "this business"),
      "Craft: " + craft,
      packages ? "Packages: " + packages : "",
      (v.servicesNote ? "Services: " + v.servicesNote.toString().slice(0, 300) : ""),
      traits.length ? "Notable: " + traits.join("; ") : "",
    ].filter(Boolean).join("\n");

    const system =
      "You are June, the assistant inside Lazo, a wedding marketplace. You are " +
      "helping a wedding vendor build a client questionnaire they will send to " +
      "couples they have already booked.\n\n" +
      "Rules:\n" +
      "- Ask only what THIS vendor genuinely needs to do their job well on the " +
      "wedding day. A florist never needs a shot list; a DJ never needs bouquet " +
      "styles.\n" +
      "- Order questions the way the day unfolds: logistics and arrival first, " +
      "then ceremony, then reception, then delivery and follow-up.\n" +
      "- Write in plain, warm, human language a couple can answer in one sitting. " +
      "No jargon, no numbering, no markdown.\n" +
      "- Each question stands alone and ends in a question mark.\n" +
      "- Never ask for payment details or anything already in a contract.\n" +
      "- Return ONLY a JSON array of strings. No preamble, no code fences.";

    const user = mode === "tighten"
      ? "Here is my current questionnaire. Tighten it: remove duplicates and " +
        "anything I would already know, sharpen the wording, and put it in the " +
        "order the day actually unfolds. Keep everything genuinely useful; you " +
        "may merge two questions into one.\n\nMy profile:\n" + profile +
        "\n\nCurrent questions:\n" + JSON.stringify(existing)
      : "Draft a questionnaire for me.\n\nMy profile:\n" + profile +
        (brief ? "\n\nWhat this questionnaire is for: " + brief : "") +
        "\n\nGive me 10 to 14 questions.";

    let out = [];
    try {
      const anthropic = new Anthropic({ apiKey: ANTHROPIC_API_KEY.value() });
      const msg = await anthropic.messages.create({
        model: "claude-sonnet-4-6",
        max_tokens: 1600,
        system: system,
        messages: [{ role: "user", content: user }],
      });
      let text = "";
      for (const block of (msg.content || [])) {
        if (block.type === "text") text += block.text;
      }
      text = text.trim().replace(/^```(json)?/i, "").replace(/```$/, "").trim();
      const parsed = JSON.parse(text);
      if (Array.isArray(parsed)) {
        out = parsed.map((q) => q.toString().trim()).filter((q) => q.length > 3);
      }
    } catch (e) {
      console.error("juneQuestionnaire failed", e.message);
      throw new HttpsError("internal", "June could not draft that one - try again.");
    }
    if (!out.length) {
      throw new HttpsError("internal", "June came back empty - try again.");
    }

    await vSnap.ref.set({
      juneVDay: today,
      juneVCount: used + 1,
    }, { merge: true });

    return { questions: out.slice(0, 18) };
  }
);
