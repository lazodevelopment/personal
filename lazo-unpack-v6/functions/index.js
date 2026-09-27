// Lazo — AI claim verification pipeline
// Trigger: new doc in claimRequests
// Outcomes: status -> 'approved' (links vendor+user live) | 'needs_review' (human queue)
// Fail-safe: ANY uncertainty or error escalates to human. AI never rejects, never
// approves on weak evidence.

const { onDocumentCreated } = require("firebase-functions/v2/firestore");
const { onSchedule } = require("firebase-functions/v2/scheduler");
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
        "phone match) is true. " +
        "DBA note: many wedding businesses operate as a brand owned by a differently-named " +
        "legal entity. If the claimant declared a legal entity name and the proof document " +
        "names THAT entity, treat the document as naming the business (a positive signal), " +
        "not a mismatch. An undeclared entity mismatch still warrants REVIEW. " +
        "When in doubt: REVIEW. " +
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
          declaredLegalEntityName: claim.legalEntityName || "",
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


// ============================================================
// LAZO ANALYTICS ROLLUP — monthly (plus quarterly/yearly at boundaries)
// Writes analytics/{period} docs + branded HTML to Storage reports/
// ============================================================

function median(nums) {
  if (!nums.length) return null;
  const s = [...nums].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

function fmtMoney(n) {
  if (n === null || n === undefined) return "—";
  return "$" + Math.round(n).toLocaleString("en-US");
}

async function computeRollup(periodLabel, startDate, endDate) {
  const metrics = { period: periodLabel, generatedAt: new Date().toISOString() };

  // ---- Couples ----
  const couplesSnap = await db.collection("couples").get();
  let couplesTotal = 0, couplesNew = 0, withDate = 0;
  const daysToWedding = [];
  couplesSnap.forEach((d) => {
    couplesTotal++;
    const c = d.data();
    const created = c.createdAt && c.createdAt.toDate ? c.createdAt.toDate() : null;
    if (created && created >= startDate && created < endDate) couplesNew++;
    if (c.weddingDate && c.weddingDate.toDate) {
      withDate++;
      if (created) {
        daysToWedding.push(
          (c.weddingDate.toDate() - created) / (1000 * 60 * 60 * 24)
        );
      }
    }
  });
  metrics.couples = {
    total: couplesTotal,
    newInPeriod: couplesNew,
    withWeddingDate: withDate,
    medianDaysToWeddingAtSignup: median(daysToWedding),
  };

  // ---- Bookings + spend (collectionGroup over plan docs) ----
  const planSnap = await db.collectionGroup("plan").get();
  const byCategory = {};
  const coupleDates = {};
  couplesSnap.forEach((d) => {
    const wd = d.data().weddingDate;
    if (wd && wd.toDate) coupleDates[d.id] = wd.toDate();
  });
  planSnap.forEach((d) => {
    const p = d.data();
    const cat = d.id;
    if (!byCategory[cat]) {
      byCategory[cat] = {
        booked: 0, leadTimes: [], planned: [], actual: [],
      };
    }
    const row = byCategory[cat];
    if (typeof p.budgetPlanned === "number") row.planned.push(p.budgetPlanned);
    if (typeof p.budgetActual === "number") row.actual.push(p.budgetActual);
    if (p.status === "booked") {
      row.booked++;
      const coupleUid = d.ref.parent.parent ? d.ref.parent.parent.id : null;
      const wd = coupleUid ? coupleDates[coupleUid] : null;
      const bookedAt =
        p.bookedAt && p.bookedAt.toDate
          ? p.bookedAt.toDate()
          : p.updatedAt && p.updatedAt.toDate
          ? p.updatedAt.toDate()
          : null;
      if (wd && bookedAt && wd > bookedAt) {
        row.leadTimes.push((wd - bookedAt) / (1000 * 60 * 60 * 24 * 30.44));
      }
    }
  });
  metrics.categories = {};
  for (const cat of Object.keys(byCategory)) {
    const r = byCategory[cat];
    metrics.categories[cat] = {
      booked: r.booked,
      medianLeadTimeMonths: median(r.leadTimes),
      leadTimeN: r.leadTimes.length,
      medianPlanned: median(r.planned),
      plannedN: r.planned.length,
      medianActual: median(r.actual),
      actualN: r.actual.length,
    };
  }

  // ---- Inquiry funnel ----
  const inqSnap = await db.collection("inquiries").get();
  let inqTotal = 0, inqNewInPeriod = 0, inqResponded = 0, inqBooked = 0;
  const respondHours = [], bookDays = [];
  inqSnap.forEach((d) => {
    inqTotal++;
    const q = d.data();
    const created = q.createdAt && q.createdAt.toDate ? q.createdAt.toDate() : null;
    if (created && created >= startDate && created < endDate) inqNewInPeriod++;
    if (q.status === "responded" || q.status === "booked") inqResponded++;
    if (q.status === "booked") inqBooked++;
    if (created && q.respondedAt && q.respondedAt.toDate) {
      respondHours.push((q.respondedAt.toDate() - created) / (1000 * 60 * 60));
    }
    if (created && q.bookedAt && q.bookedAt.toDate) {
      bookDays.push((q.bookedAt.toDate() - created) / (1000 * 60 * 60 * 24));
    }
  });
  metrics.inquiries = {
    total: inqTotal,
    newInPeriod: inqNewInPeriod,
    responded: inqResponded,
    booked: inqBooked,
    conversionToBookedPct: inqTotal ? (inqBooked / inqTotal) * 100 : null,
    medianHoursToRespond: median(respondHours),
    medianDaysToBook: median(bookDays),
  };

  // ---- Supply funnel ----
  const claimsSnap = await db.collection("claimRequests").get();
  let cTotal = 0, cApproved = 0, cAI = 0, cReview = 0, cDenied = 0;
  claimsSnap.forEach((d) => {
    cTotal++;
    const c = d.data();
    if (c.status === "approved") {
      cApproved++;
      if (c.approvedBy === "ai") cAI++;
    }
    if (c.status === "needs_review") cReview++;
    if (c.status === "denied") cDenied++;
  });
  const listSnap = await db.collection("listingRequests").get();
  const vendorsAgg = await db.collection("vendors").count().get();
  const claimedAgg = await db
    .collection("vendors")
    .where("claimStatus", "==", "claimed")
    .count()
    .get();
  metrics.supply = {
    claimRequests: cTotal,
    approved: cApproved,
    aiAutoApproved: cAI,
    needsReview: cReview,
    denied: cDenied,
    listingRequests: listSnap.size,
    vendorsTotal: vendorsAgg.data().count,
    vendorsClaimed: claimedAgg.data().count,
  };

  return metrics;
}

function renderReportHtml(m) {
  const catRows = Object.keys(m.categories)
    .sort()
    .map((cat) => {
      const c = m.categories[cat];
      const lead =
        c.leadTimeN >= 5 && c.medianLeadTimeMonths !== null
          ? c.medianLeadTimeMonths.toFixed(1) + " mo"
          : "n<5";
      const planned = c.plannedN >= 5 ? fmtMoney(c.medianPlanned) : "n<5";
      const actual = c.actualN >= 5 ? fmtMoney(c.medianActual) : "n<5";
      return (
        "<tr><td>" + cat + "</td><td>" + c.booked + "</td><td>" + lead +
        "</td><td>" + planned + "</td><td>" + actual + "</td></tr>"
      );
    })
    .join("");
  const i = m.inquiries, s = m.supply, cp = m.couples;
  return (
    "<!doctype html><html><head><meta charset=\"utf-8\"><title>Lazo Report " + m.period + "</title>" +
    "<style>body{font-family:Georgia,serif;background:#FAF6F0;color:#241E2B;margin:0;padding:40px}" +
    "h1{color:#52284F;letter-spacing:1px}h2{color:#52284F;border-bottom:2px solid #D9B77C;padding-bottom:6px;margin-top:36px}" +
    ".k{display:inline-block;background:#fff;border:1px solid #D9B77C;border-radius:14px;padding:14px 20px;margin:6px 8px 6px 0}" +
    ".k b{display:block;font-size:24px;color:#52284F}.k span{font-size:12px;color:#7A6E80}" +
    "table{border-collapse:collapse;width:100%;background:#fff;border:1px solid #D9B77C;border-radius:12px}" +
    "th,td{padding:10px 12px;text-align:left;border-bottom:1px solid #EFE6DA;font-size:14px}th{color:#52284F}" +
    ".foot{margin-top:40px;font-size:11px;color:#7A6E80}</style></head><body>" +
    "<h1>LAZO &middot; " + m.period + " Report</h1>" +
    "<p>Generated " + m.generatedAt + " &middot; Internal &middot; aggregates only (cells under n=5 suppressed)</p>" +
    "<h2>Couples</h2>" +
    "<div class=k><b>" + cp.total + "</b><span>total couples</span></div>" +
    "<div class=k><b>" + cp.newInPeriod + "</b><span>new this period</span></div>" +
    "<div class=k><b>" + cp.withWeddingDate + "</b><span>with a date set</span></div>" +
    "<div class=k><b>" + (cp.medianDaysToWeddingAtSignup === null ? "—" : Math.round(cp.medianDaysToWeddingAtSignup) + "d") + "</b><span>median runway at signup</span></div>" +
    "<h2>Bookings &amp; Spend by Category</h2>" +
    "<table><tr><th>Category</th><th>Booked</th><th>Median lead time</th><th>Median planned</th><th>Median actual</th></tr>" +
    catRows + "</table>" +
    "<h2>Demand Funnel</h2>" +
    "<div class=k><b>" + i.newInPeriod + "</b><span>new inquiries</span></div>" +
    "<div class=k><b>" + i.total + "</b><span>all-time inquiries</span></div>" +
    "<div class=k><b>" + i.booked + "</b><span>booked</span></div>" +
    "<div class=k><b>" + (i.conversionToBookedPct === null ? "—" : i.conversionToBookedPct.toFixed(1) + "%") + "</b><span>inquiry \u2192 booked</span></div>" +
    "<div class=k><b>" + (i.medianHoursToRespond === null ? "—" : i.medianHoursToRespond.toFixed(1) + "h") + "</b><span>median response time</span></div>" +
    "<h2>Supply Funnel</h2>" +
    "<div class=k><b>" + s.vendorsTotal + "</b><span>vendors listed</span></div>" +
    "<div class=k><b>" + s.vendorsClaimed + "</b><span>claimed</span></div>" +
    "<div class=k><b>" + s.claimRequests + "</b><span>claim requests</span></div>" +
    "<div class=k><b>" + s.aiAutoApproved + "</b><span>AI auto-approved</span></div>" +
    "<div class=k><b>" + s.needsReview + "</b><span>awaiting review</span></div>" +
    "<div class=foot>Lazo &middot; rankings can\u2019t be bought &middot; every number above is observed, not surveyed.</div>" +
    "</body></html>"
  );
}

async function runRollup(periodLabel, startDate, endDate) {
  const metrics = await computeRollup(periodLabel, startDate, endDate);
  await db.collection("analytics").doc(periodLabel).set(metrics);
  const html = renderReportHtml(metrics);
  await bucket.file("reports/" + periodLabel + ".html").save(html, {
    contentType: "text/html",
  });
  console.log("Rollup written:", periodLabel);
}

exports.analyticsRollup = onSchedule(
  {
    schedule: "0 9 1 * *",
    timeZone: "America/Phoenix",
    region: "us-central1",
    timeoutSeconds: 300,
    memory: "512MiB",
  },
  async () => {
    const now = new Date();
    // Prior month
    const mStart = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    const mEnd = new Date(now.getFullYear(), now.getMonth(), 1);
    const mLabel =
      mStart.getFullYear() + "-" + String(mStart.getMonth() + 1).padStart(2, "0");
    await runRollup(mLabel, mStart, mEnd);

    // Quarter boundary (Jan/Apr/Jul/Oct): prior quarter
    const month = now.getMonth(); // 0-based; month of run
    if ([0, 3, 6, 9].includes(month)) {
      const qEnd = new Date(now.getFullYear(), month, 1);
      const qStart = new Date(qEnd.getFullYear(), qEnd.getMonth() - 3, 1);
      const qNum = Math.floor(qStart.getMonth() / 3) + 1;
      await runRollup(qStart.getFullYear() + "-Q" + qNum, qStart, qEnd);
    }

    // Year boundary (January): prior year
    if (month === 0) {
      const yStart = new Date(now.getFullYear() - 1, 0, 1);
      const yEnd = new Date(now.getFullYear(), 0, 1);
      await runRollup(String(now.getFullYear() - 1), yStart, yEnd);
    }
  }
);


// ============================================================
// LISTING REQUEST AI PRE-SCREEN
// New-listing spam meets the same robot. AI annotates; approval
// (vendor-doc creation) stays with the admin desk's one tap.
// ============================================================
exports.reviewListingRequest = onDocumentCreated(
  {
    document: "listingRequests/{requestId}",
    secrets: [ANTHROPIC_API_KEY],
    region: "us-central1",
    timeoutSeconds: 120,
    memory: "512MiB",
  },
  async (event) => {
    const snap = event.data;
    if (!snap) return;
    const req = snap.data();
    const ref = snap.ref;
    if (req.status !== "pending") return;

    const escalate = async (notes) => {
      await ref.update({
        status: "needs_review",
        aiDecision: "escalate",
        aiNotes: notes,
        aiReviewedAt: admin.firestore.FieldValue.serverTimestamp(),
      });
    };

    try {
      const emailDomain = domainOf(req.email);
      const siteDomain = domainOf(req.website);
      const domainMatch =
        emailDomain.length > 0 && siteDomain.length > 0 && emailDomain === siteDomain;

      let proofBase64 = null;
      let proofMediaType = "image/jpeg";
      if (req.proofPath) {
        try {
          const [buf] = await bucket.file(req.proofPath).download();
          if (buf && buf.length > 0 && buf.length < 8 * 1024 * 1024) {
            proofBase64 = buf.toString("base64");
            proofMediaType = sniffMediaType(buf);
          }
        } catch (e) {
          console.log("Listing proof download failed:", e.message);
        }
      }
      if (!proofBase64) {
        return escalate("Proof document missing or unreadable.");
      }

      const anthropic = new Anthropic({ apiKey: ANTHROPIC_API_KEY.value() });
      const systemPrompt =
        "You review NEW BUSINESS LISTING requests for Lazo, a verified wedding marketplace. " +
        "A person wants to add a business that is not yet listed. You will see their submitted " +
        "details and a proof-of-ownership document (image or PDF). Decide APPROVE (document is " +
        "plausibly an official business document AND names the submitted business or its declared " +
        "legal entity AND the business is plausibly a real wedding-relevant vendor) or REVIEW " +
        "(anything unclear, mismatched, or suspicious). Never REJECT. " +
        "DBA note: if a declared legal entity name matches the document, that satisfies the naming " +
        "requirement. Respond ONLY with JSON: " +
        "{\"decision\":\"APPROVE\"|\"REVIEW\",\"confidence\":0-100,\"reasons\":\"one or two sentences\"}";

      const facts = {
        submitted: {
          businessName: req.businessName || "",
          declaredLegalEntityName: req.legalEntityName || "",
          phone: req.phone || "",
          website: req.website || "",
          categories: req.categories || [],
          metroId: req.metroId || "",
          accountEmail: req.email || "",
        },
        computedSignals: { emailDomainMatchesWebsite: domainMatch },
      };

      const proofBlock =
        proofMediaType === "application/pdf"
          ? { type: "document", source: { type: "base64", media_type: "application/pdf", data: proofBase64 } }
          : { type: "image", source: { type: "base64", media_type: proofMediaType, data: proofBase64 } };

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
                  "Listing facts:\n" + JSON.stringify(facts, null, 2) +
                  "\n\nAttached: the proof-of-ownership document. Respond with the JSON only.",
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
        return escalate("AI response unparseable. Raw: " + text.slice(0, 300));
      }

      const decision = String(verdict.decision || "").toUpperCase();
      const confidence = Number(verdict.confidence || 0);
      const reasons = String(verdict.reasons || "");

      if (decision === "APPROVE" && confidence >= 80) {
        await ref.update({
          aiDecision: "approve",
          aiConfidence: confidence,
          aiNotes: "AI pre-screen: looks legitimate. " + reasons,
          aiReviewedAt: admin.firestore.FieldValue.serverTimestamp(),
        });
        console.log("Listing pre-approved by AI:", event.params.requestId);
        return;
      }
      return escalate("AI verdict: " + decision + " (confidence " + confidence + "). " + reasons);
    } catch (err) {
      console.error("Listing review error:", err);
      return escalate("Pipeline error. " + String(err.message || err).slice(0, 200));
    }
  }
);


// ============================================================
// DAILY PUBLIC STATS — powers live counts in the app + site
// ============================================================
exports.statsRefresh = onSchedule(
  {
    schedule: "15 4 * * *",
    timeZone: "America/Phoenix",
    region: "us-central1",
    timeoutSeconds: 120,
    memory: "256MiB",
  },
  async () => {
    const agg = await db.collection("vendors").count().get();
    const vendorCount = agg.data().count;
    const floored = Math.floor(vendorCount / 100) * 100;
    const display = floored.toLocaleString("en-US") + "+";
    const metroSnap = await db.collection("metros").get();
    const metroCount = metroSnap.empty ? 31 : metroSnap.size;
    await db.doc("stats/global").set(
      {
        vendorCount: vendorCount,
        vendorTotalDisplay: display,
        metroCount: metroCount,
        updatedAt: admin.firestore.FieldValue.serverTimestamp(),
      },
      { merge: true }
    );
    console.log("Stats refreshed:", display, "vendors,", metroCount, "metros");
  }
);
