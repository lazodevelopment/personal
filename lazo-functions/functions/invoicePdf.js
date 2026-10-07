// JC-LAZO-FN-1007-RESTORE: recovered from the 2026-09-21 production build (the local tree never had it).
// Lazo — premium invoice PDF (v45)
// GET /invoicePdf?inquiry=<id>&invoice=<id>
// Streams a branded, downloadable PDF. Opaque Firestore IDs are the access
// secret (same pattern as proIntentInfo). Always reflects live status —
// a paid invoice carries the PAID seal.
const { onRequest } = require("firebase-functions/v2/https");
const admin = require("firebase-admin");
const PDFDocument = require("pdfkit");
const path = require("path");
const fs = require("fs");

const PLUM = "#52284F";
const PLUM_DEEP = "#3D1C3B";
const GOLD = "#D9B77C";
const IVORY = "#FAF6F0";
const INK = "#241E2B";
const MUTED = "#8A7F90";
const GREEN = "#2E8B6B";

function money(n) {
  const v = Number(n || 0);
  return "$" + v.toLocaleString("en-US", {
    minimumFractionDigits: v % 1 ? 2 : 0, maximumFractionDigits: 2 });
}

function fontOr(doc, file, fallback) {
  const p = path.join(__dirname, "fonts", file);
  try { if (fs.existsSync(p)) { return p; } } catch (e) { /* noop */ }
  return fallback;
}

exports.invoicePdf = onRequest(
  { region: "us-central1", timeoutSeconds: 30, memory: "256MiB" },
  async (req, res) => {
    try {
      const db = admin.firestore();
      const inquiryId = (req.query.inquiry || "").toString();
      const invoiceId = (req.query.invoice || "").toString();
      if (!inquiryId || !invoiceId) {
        res.status(400).send("Missing invoice reference."); return;
      }
      const iSnap = await db.collection("inquiries").doc(inquiryId)
        .collection("invoices").doc(invoiceId).get();
      if (!iSnap.exists) { res.status(404).send("Invoice not found."); return; }
      const inv = iSnap.data();
      const iqSnap = await db.collection("inquiries").doc(inquiryId).get();
      const iq = iqSnap.exists ? iqSnap.data() : {};
      let vendorName = "Your vendor";
      if (inv.vendorId) {
        const vSnap = await db.collection("vendors").doc(inv.vendorId).get();
        if (vSnap.exists && vSnap.data().name) { vendorName = vSnap.data().name; }
      }
      const coupleName = (iq.coupleName || iq.names || "").toString();
      const paid = inv.status === "paid";
      const voided = inv.status === "void";
      const created = inv.createdAt && inv.createdAt.toDate
        ? inv.createdAt.toDate() : new Date();
      const paidAt = inv.paidAt && inv.paidAt.toDate ? inv.paidAt.toDate() : null;
      const dateFmt = (d) => d.toLocaleDateString("en-US",
        { month: "long", day: "numeric", year: "numeric" });

      const serif = fontOr(null, "CormorantGaramond-Medium.ttf", "Times-Roman");
      const sans = fontOr(null, "Lato-Regular.ttf", "Helvetica");
      const sansB = fontOr(null, "Lato-Bold.ttf", "Helvetica-Bold");

      const doc = new PDFDocument({ size: "LETTER", margin: 0 });
      res.setHeader("Content-Type", "application/pdf");
      res.setHeader("Content-Disposition",
        'inline; filename="Lazo-Invoice-' + invoiceId.slice(0, 6).toUpperCase() + '.pdf"');
      doc.pipe(res);

      const W = 612, H = 792, M = 56;

      // ---- header band ----
      doc.rect(0, 0, W, 128).fill(PLUM_DEEP);
      doc.rect(0, 124, W, 4).fill(GOLD);
      doc.font(serif).fontSize(26).fillColor(IVORY)
        .text("L A Z O", M, 40, { characterSpacing: 4 });
      doc.font(sans).fontSize(8.5).fillColor(GOLD)
        .text("T I E D   T O G E T H E R", M, 74, { characterSpacing: 2 });
      doc.font(serif).fontSize(30).fillColor(GOLD)
        .text("Invoice", 0, 44, { width: W - M, align: "right" });
      doc.font(sans).fontSize(9.5).fillColor(IVORY)
        .text("No. " + invoiceId.slice(0, 6).toUpperCase() + "   \u00b7   " + dateFmt(created),
          0, 84, { width: W - M, align: "right" });

      // ---- parties ----
      let y = 164;
      doc.font(sans).fontSize(8.5).fillColor(MUTED)
        .text("F R O M", M, y, { characterSpacing: 1.5 });
      doc.font(serif).fontSize(19).fillColor(PLUM).text(vendorName, M, y + 13);
      if (coupleName) {
        doc.font(sans).fontSize(8.5).fillColor(MUTED)
          .text("B I L L E D   T O", 330, y, { characterSpacing: 1.5 });
        doc.font(serif).fontSize(19).fillColor(INK).text(coupleName, 330, y + 13);
      }
      y += 58;
      doc.font(serif).fontSize(14).fillColor(INK)
        .text(inv.title || "Invoice", M, y);
      if (inv.dueNow) {
        doc.font(sans).fontSize(9).fillColor(GOLD)
          .text("Due upon signing", M, y + 20);
      } else if (inv.dueDate && inv.dueDate.toDate) {
        doc.font(sans).fontSize(9).fillColor(MUTED)
          .text("Due " + dateFmt(inv.dueDate.toDate()), M, y + 20);
      }
      y += 46;

      // ---- line items ----
      doc.rect(M, y, W - 2 * M, 0.75).fill(GOLD);
      y += 14;
      const items = Array.isArray(inv.lineItems) ? inv.lineItems : [];
      doc.font(sans).fontSize(11);
      for (const it of items) {
        doc.fillColor(INK).text((it.label || "").toString(), M, y,
          { width: W - 2 * M - 110 });
        doc.fillColor(INK).text(money(it.amount), W - M - 100, y,
          { width: 100, align: "right" });
        const lh = Math.max(
          doc.heightOfString((it.label || "").toString(),
            { width: W - 2 * M - 110 }), 14);
        y += lh + 10;
        doc.rect(M, y - 6, W - 2 * M, 0.4).fillColor("#E4D9CB").fill();
      }
      y += 8;

      // ---- total ----
      doc.rect(M, y, W - 2 * M, 1.2).fill(GOLD);
      y += 12;
      doc.font(serif).fontSize(15).fillColor(PLUM).text("Total", M, y + 2);
      doc.font(serif).fontSize(24).fillColor(PLUM)
        .text(money(inv.total), W - M - 180, y - 4, { width: 180, align: "right" });
      y += 44;

      // ---- status seal ----
      if (paid) {
        doc.save();
        doc.rotate(-8, { origin: [W - 150, y + 24] });
        doc.roundedRect(W - 218, y, 136, 48, 8)
          .lineWidth(2.5).strokeColor(GREEN).stroke();
        doc.font(sansB).fontSize(21).fillColor(GREEN)
          .text("P A I D", W - 218, y + 12, { width: 136, align: "center" });
        doc.restore();
        if (paidAt) {
          doc.font(sans).fontSize(9).fillColor(GREEN)
            .text("Received " + dateFmt(paidAt), W - 218, y + 54,
              { width: 136, align: "center" });
        }
      } else if (voided) {
        doc.font(sansB).fontSize(14).fillColor(MUTED)
          .text("VOID", W - M - 100, y, { width: 100, align: "right" });
      }

      // ---- footer ----
      doc.rect(0, H - 74, W, 74).fill(IVORY);
      doc.rect(0, H - 74, W, 1).fill(GOLD);
      doc.font(sans).fontSize(8.5).fillColor(MUTED)
        .text(vendorName + "   \u00b7   sent with Lazo \u2014 meetlazo.com",
          M, H - 52, { width: W - 2 * M, align: "center" });
      doc.font(sans).fontSize(7.5).fillColor(MUTED)
        .text("This invoice lives in your Lazo thread \u2014 payments, contracts, "
          + "and every promise, kept in one place.",
          M, H - 38, { width: W - 2 * M, align: "center" });

      doc.end();
    } catch (e) {
      console.error("invoicePdf failed", e.message);
      res.status(500).send("Could not render this invoice.");
    }
  }
);
