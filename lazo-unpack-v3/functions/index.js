// Lazo — AI claim verification pipeline
// Trigger: new doc in claimRequests
// Outcomes: status -> 'approved' (links vendor+user live) | 'needs_review' (human queue)
// Fail-safe: ANY uncertainty or error escalates to human. AI never rejects, never
// approves on weak evidence.

const { onDocumentCreated } = require("firebase-functions/v2/firestore");
const { defineSecret } = require("firebase-functions/params");
const admin = require("firebase-admin");
const Anthropic = require("@anthropic-ai/sdk");

admin.initializeApp();
const db = admin.firestore();
const bucket = admin.storage().bucket();

const ANTHROPIC_API_KEY = defineSecret("ANTHROPIC_API_KEY");

function domainOf(s) {
  if (!s) return "";
  try {
    let x = String(s).toLowerCase().trim();
    if (x.includes("@")) x = x.split("@")[1];
    x = x.replace(/^https?:\/\//, "").replace(/^www\./, "");
    x = x.split("/")[0];
    return x;
  } catch (e) {
    return "";
  }
}

function digitsOf(s) {
  return String(s || "").replace(/\D/g, "").slice(-10);
}

function sniffMediaType(buf) {
  if (!buf || buf.length < 12) return "image/jpeg";
  if (buf[0] === 0x25 && buf[1] === 0x50 && buf[2] === 0x44 && buf[3] === 0x46)
    return "application/pdf";
  if (buf[0] === 0xff && buf[1] === 0xd8) return "image/jpeg";
  if (buf[0] === 0x89 && buf[1] === 0x50 && buf[2] === 0x4e && buf[3] === 0x47)
    return "image/png";
  if (buf[0] === 0x47 && buf[1] === 0x49 && buf[2] === 0x46) return "image/gif";
  if (
    buf[0] === 0x52 && buf[1] === 0x49 && buf[2] === 0x46 && buf[3] === 0x46 &&
    buf[8] === 0x57 && buf[9] === 0x45 && buf[10] === 0x42 && buf[11] === 0x50
  )
    return "image/webp";
  return "image/jpeg";
}

exports.reviewClaimRequest = onDocumentCreated(
  {
    document: "claimRequests/{requestId}",
    secrets: [ANTHROPIC_API_KEY],
    region: "us-central1",
    timeoutSeconds: 120,
    memory: "512MiB",
  },
  async (event) => {
    const snap = event.data;
    if (!snap) return;
    const claim = snap.data();
    const requestRef = snap.ref;

    // Only process fresh pending claims
    if (claim.status !== "pending") return;

    const escalate = async (notes) => {
      await requestRef.update({
        status: "needs_review",
        aiDecision: "escalate",
        aiNotes: notes,
        aiReviewedAt: admin.firestore.FieldValue.serverTimestamp(),
      });
    };

    try {
      const vendorId = claim.vendorId;
      if (!vendorId) return escalate("Claim has no vendorId.");

      // Load the vendor listing being claimed
      const vendorSnap = await db.collection("vendors").doc(vendorId).get();
      if (!vendorSnap.exists) return escalate("Vendor doc not found.");
      const vendor = vendorSnap.data();

      // Already claimed? Always human.
      if (vendor.claimedBy) {
        return escalate("Vendor already claimed by another account — possible dispute.");
      }

      // ---------- Deterministic signals (computed, not guessed) ----------
      const emailDomain = domainOf(claim.businessEmail);
      const siteDomain = domainOf(vendor.website);
      const domainMatch =
        emailDomain.length > 0 && siteDomain.length > 0 && emailDomain === siteDomain;

      const claimPhone = digitsOf(claim.businessPhone);
      const listingPhone = digitsOf(vendor.phone);
      const phoneMatch =
        claimPhone.length === 10 && listingPhone.length === 10 && claimPhone === listingPhone;

      // ---------- Proof document ----------
      let proofBase64 = null;
      let proofMediaType = "image/jpeg";
      if (claim.proofPath) {
        try {
          const [buf] = await bucket.file(claim.proofPath).download();
          if (buf && buf.length > 0 && buf.length < 8 * 1024 * 1024) {
            proofBase64 = buf.toString("base64");
            proofMediaType = sniffMediaType(buf);
          }
        } catch (e) {
          console.log("Proof download failed:", e.message);
        }
      }
      if (!proofBase64) {
        return escalate("Proof document missing or unreadable — human review required.");
      }

      // ---------- Claude review ----------
      const anthropic = new Anthropic({ apiKey: ANTHROPIC_API_KEY.value() });

      const systemPrompt =
        "You are the claim-verification reviewer for Lazo, a wedding vendor marketplace " +
        "where trust is the entire product. A person is claiming ownership of a business " +
        "listing. You will see the listing data, the claimant's submitted details, " +
        "pre-computed match signals, and a photo of their ownership proof document. " +
        "Decide one of: APPROVE (only if evidence strongly supports ownership), " +
        "REVIEW (any doubt, unclear document, partial matches, or anything unusual). " +
        "You may NEVER output REJECT — humans handle all negative outcomes. " +
        "APPROVE requires: the proof document plausibly is an official document " +
        "(license, insurance, tax, utility, registration) AND it names this business or " +
        "its owner, AND at least one of the deterministic signals (email-domain match or " +
        "phone match) is true. When in doubt: REVIEW. " +
        "Respond ONLY with JSON: {\"decision\":\"APPROVE\"|\"REVIEW\",\"confidence\":0-100," +
        "\"reasons\":\"one or two sentences\"}";

      const facts = {
        listing: {
          name: vendor.name,
          website: vendor.website || "",
          phone: vendor.phone || "",
          address: vendor.address || "",
          metroId: vendor.metroId || "",
          source: vendor.source || "seed",
        },
        claimant: {
          accountEmail: claim.email || "",
          businessEmail: claim.businessEmail || "",
          businessPhone: claim.businessPhone || "",
          statedRole: claim.claimantRole || "",
        },
        computedSignals: {
          emailDomainMatchesWebsite: domainMatch,
          phoneMatchesListing: phoneMatch,
        },
      };

      const proofBlock =
        proofMediaType === "application/pdf"
          ? {
              type: "document",
              source: {
                type: "base64",
                media_type: "application/pdf",
                data: proofBase64,
              },
            }
          : {
              type: "image",
              source: {
                type: "base64",
                media_type: proofMediaType,
                data: proofBase64,
              },
            };

      const msg = await anthropic.messages.create({
        model: "claude-sonnet-4-6",
        max_tokens: 400,
        system: systemPrompt,
        messages: [
          {
            role: "user",
            content: [
              {
                type: "text",
                text:
                  "Claim facts:\n" +
                  JSON.stringify(facts, null, 2) +
                  "\n\nThe attached file is the claimant's proof-of-ownership document " +
                  "(may be an image or a PDF such as an EIN letter or license). " +
                  "Evaluate and respond with the JSON only.",
              },
              proofBlock,
            ],
          },
        ],
      });

      let text = "";
      for (const block of msg.content) {
        if (block.type === "text") text += block.text;
      }
      text = text.replace(/```json|```/g, "").trim();

      let verdict;
      try {
        verdict = JSON.parse(text);
      } catch (e) {
        return escalate("AI response unparseable — human review. Raw: " + text.slice(0, 300));
      }

      const decision = String(verdict.decision || "").toUpperCase();
      const confidence = Number(verdict.confidence || 0);
      const reasons = String(verdict.reasons || "");

      // ---------- Hard gate: belt-and-suspenders over the model ----------
      const strongSignals = domainMatch || phoneMatch;
      if (decision === "APPROVE" && confidence >= 85 && strongSignals) {
        const batch = db.batch();
        batch.update(db.collection("vendors").doc(vendorId), {
          claimedBy: claim.uid,
          claimStatus: "claimed",
        });
        batch.update(db.collection("users").doc(claim.uid), {
          vendorId: vendorId,
        });
        batch.update(requestRef, {
          status: "approved",
          aiDecision: "approve",
          aiConfidence: confidence,
          aiNotes: reasons,
          approvedBy: "ai",
          aiReviewedAt: admin.firestore.FieldValue.serverTimestamp(),
        });
        await batch.commit();
        console.log("AI-approved claim", event.params.requestId, "for", vendor.name);
        return;
      }

      return escalate(
        "AI verdict: " + decision + " (confidence " + confidence + "). " + reasons
      );
    } catch (err) {
      console.error("Claim review error:", err);
      return escalate("Pipeline error — human review. " + String(err.message || err).slice(0, 200));
    }
  }
);
