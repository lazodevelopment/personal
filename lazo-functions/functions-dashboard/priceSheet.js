// functions-dashboard/priceSheet.js -- JC-LAZO-FNDASH-0910-009
//
// A vendor uploads a price sheet PDF from the dashboard (it lands in Storage at
// vendors/{vendorId}/docs/<name>.pdf and the dashboard writes vendors.priceSheetUrl).
// This module turns that PDF into two things the public vendor page shows:
//
//   1. page images  -> vendors.priceSheetPages  (JPEGs in vendors/{id}/docs/pages/, 1200px wide)
//   2. package cards -> vendors.packages / vendors.addOns / vendors.startingPrice
//      (Claude reads the PDF and returns the packages as JSON, grouped by the sheet's
//      own sections: The Videography Collection, The Photography Collection, ...)
//
// Package maps carry the fields the vendor page and the dashboard editor already use
// (name, hours, price, offPeak, includes) plus group, payInFull and tag.
//
// Hand edits win: what the sheet wrote last time is kept in vendors.packagesFromSheet. If the
// live packages no longer match it (the vendor edited them in the dashboard), a new sheet only
// refreshes packagesFromSheet/addOnsFromSheet and the page images; it does not touch packages.
//
// Wire-up in index.js (two lines):
//   const priceSheet = require('./priceSheet');
//   exports.priceSheetExtract = priceSheet.priceSheetExtract;
//   exports.priceSheetRerun   = priceSheet.priceSheetRerun;
// package.json: "pdfjs-dist": "^4.10.38", "@napi-rs/canvas": "^0.1.65"
// Secret: ANTHROPIC_API_KEY (already used by juneImport) -- bound here by name.

'use strict';

const { onObjectFinalized } = require('firebase-functions/v2/storage');
const { onCall, HttpsError } = require('firebase-functions/v2/https');
const { logger } = require('firebase-functions/v2');
const { getFirestore, FieldValue } = require('firebase-admin/firestore');
const { getStorage } = require('firebase-admin/storage');
const crypto = require('node:crypto');
const path = require('node:path');

const BUCKET = 'lazo-513ec.firebasestorage.app';
const REGION = 'us-central1';
const PAGE_WIDTH = 1200;        // px; the page shows them at 220px wide and opens the full image on tap
const JPEG_QUALITY = 82;
const MAX_PAGES = 12;
const MODEL = 'claude-sonnet-4-6';
// Who may call priceSheetRerun besides the vendor's own claimant.
const ADMIN_EMAILS = ['john@meetlazo.com', 'vendors@meetlazo.com', 'support@meetlazo.com'];

const RUNTIME = { region: REGION, memory: '1GiB', timeoutSeconds: 300, secrets: ['ANTHROPIC_API_KEY'] };

// ---------------------------------------------------------------------------------------------
// Trigger: a PDF lands under vendors/{id}/docs/
// ---------------------------------------------------------------------------------------------
exports.priceSheetExtract = onObjectFinalized({ ...RUNTIME, bucket: BUCKET }, async (event) => {
  const name = event.data.name || '';
  const m = /^vendors\/([^/]+)\/docs\/[^/]+\.pdf$/i.exec(name);
  if (!m) return;
  const ct = (event.data.contentType || '').toLowerCase();
  if (ct && ct !== 'application/pdf' && ct !== 'application/octet-stream') {
    logger.warn('priceSheet: not a PDF', { name, ct });
    return;
  }
  await processSheet(m[1], event.data.bucket || BUCKET, name, 'upload');
});

// ---------------------------------------------------------------------------------------------
// Callable: re-run for a vendor whose sheet is already in Storage (backfill, or after an edit).
// data: { vendorId }
// ---------------------------------------------------------------------------------------------
exports.priceSheetRerun = onCall(RUNTIME, async (req) => {
  if (!req.auth) throw new HttpsError('unauthenticated', 'Sign in first.');
  const vendorId = String((req.data && req.data.vendorId) || '').trim();
  if (!/^[A-Za-z0-9_-]{3,120}$/.test(vendorId)) throw new HttpsError('invalid-argument', 'vendorId');

  const snap = await getFirestore().collection('vendors').doc(vendorId).get();
  if (!snap.exists) throw new HttpsError('not-found', 'No such vendor.');
  const v = snap.data() || {};
  const email = String((req.auth.token && req.auth.token.email) || '').toLowerCase();
  const isAdmin = req.auth.token && (req.auth.token.admin === true || ADMIN_EMAILS.includes(email));
  if (!isAdmin && v.claimedBy !== req.auth.uid) throw new HttpsError('permission-denied', 'Not your listing.');

  const [files] = await getStorage().bucket(BUCKET).getFiles({ prefix: `vendors/${vendorId}/docs/` });
  const pdfs = files.filter((f) => /\.pdf$/i.test(f.name) && !f.name.includes('/docs/pages/'));
  if (!pdfs.length) throw new HttpsError('failed-precondition', 'No price sheet PDF in Storage for this vendor.');
  pdfs.sort((a, b) => new Date(b.metadata.updated || 0) - new Date(a.metadata.updated || 0));
  const result = await processSheet(vendorId, BUCKET, pdfs[0].name, 'rerun');
  return result;
});

// ---------------------------------------------------------------------------------------------
// The pipeline
// ---------------------------------------------------------------------------------------------
async function processSheet(vendorId, bucketName, objectName, why) {
  const db = getFirestore();
  const bucket = getStorage().bucket(bucketName);
  const ref = db.collection('vendors').doc(vendorId);
  const t0 = Date.now();

  const [buf] = await bucket.file(objectName).download();
  const hash = crypto.createHash('sha1').update(buf).digest('hex').slice(0, 10);
  logger.info('priceSheet: start', { vendorId, objectName, bytes: buf.length, hash, why });

  const before = (await ref.get()).data() || {};
  if (before.priceSheetHash === hash && why === 'upload' && Array.isArray(before.priceSheetPages) && before.priceSheetPages.length) {
    logger.info('priceSheet: same file already processed', { vendorId, hash });
    return { vendorId, hash, skipped: true };
  }

  // 1. pages -> images
  let pages = [];
  try {
    pages = await renderPages(buf, vendorId, hash, bucket);
  } catch (e) {
    logger.error('priceSheet: render failed', { vendorId, err: String(e && e.stack || e) });
  }

  // 2. packages -> JSON
  let extracted = null, extractError = null;
  try {
    extracted = await extractPackages(buf);
  } catch (e) {
    extractError = String(e && e.message || e);
    logger.error('priceSheet: extract failed', { vendorId, err: extractError });
  }

  // 3. write, hand edits winning
  const update = {
    priceSheetHash: hash,
    priceSheetObject: objectName,
    priceSheetProcessedAt: FieldValue.serverTimestamp(),
    priceSheetError: extractError || FieldValue.delete(),
  };
  if (pages.length) {
    update.priceSheetPages = pages;
    update.priceSheetPageCount = pages.length;
  }
  let wrotePackages = false;
  if (extracted && extracted.packages.length) {
    const prev = Array.isArray(before.packages) ? before.packages : [];
    const fromSheet = Array.isArray(before.packagesFromSheet) ? before.packagesFromSheet : [];
    const handEdited = prev.length > 0 && !samePackages(prev, fromSheet);
    update.packagesFromSheet = extracted.packages;
    update.addOnsFromSheet = extracted.addOns;
    if (!handEdited) {
      update.packages = extracted.packages;
      update.addOns = extracted.addOns;
      update.packagesSource = 'pricesheet';
      update.packagesExtractedAt = FieldValue.serverTimestamp();
      wrotePackages = true;
    }
    if (extracted.startingPrice && (!before.startingPrice || !handEdited)) update.startingPrice = extracted.startingPrice;
  }
  await ref.set(update, { merge: true });

  // 4. old page images from an earlier sheet
  try {
    const [files] = await bucket.getFiles({ prefix: `vendors/${vendorId}/docs/pages/` });
    await Promise.all(files.filter((f) => !f.name.includes(`/pages/${hash}-`)).map((f) => f.delete().catch(() => {})));
  } catch (e) { /* cleanup only */ }

  const result = { vendorId, hash, pages: pages.length, packages: extracted ? extracted.packages.length : 0, wrotePackages, ms: Date.now() - t0, error: extractError || null };
  logger.info('priceSheet: done', result);
  return result;
}

// ---------------------------------------------------------------------------------------------
// PDF -> JPEG pages (pdfjs draws glyphs as paths onto a napi canvas; no fonts to install)
// ---------------------------------------------------------------------------------------------
async function renderPages(buf, vendorId, hash, bucket) {
  const { createCanvas } = require('@napi-rs/canvas');
  const pdfjs = await import('pdfjs-dist/legacy/build/pdf.mjs');
  const fontsDir = path.join(path.dirname(require.resolve('pdfjs-dist/package.json')), 'standard_fonts') + path.sep;
  const doc = await pdfjs.getDocument({ data: new Uint8Array(buf), disableFontFace: true, standardFontDataUrl: fontsDir, verbosity: 0 }).promise;
  const n = Math.min(doc.numPages, MAX_PAGES);
  const canvasFactory = {
    create: (w, h) => { const c = createCanvas(w, h); return { canvas: c, context: c.getContext('2d') }; },
    reset: (o, w, h) => { o.canvas.width = w; o.canvas.height = h; },
    destroy: () => {},
  };
  const urls = [];
  for (let i = 1; i <= n; i++) {
    const page = await doc.getPage(i);
    const vp0 = page.getViewport({ scale: 1 });
    const vp = page.getViewport({ scale: PAGE_WIDTH / vp0.width });
    const canvas = createCanvas(Math.round(vp.width), Math.round(vp.height));
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#ffffff'; ctx.fillRect(0, 0, canvas.width, canvas.height);
    await page.render({ canvasContext: ctx, viewport: vp, canvasFactory }).promise;
    const jpg = await canvas.encode('jpeg', JPEG_QUALITY);
    const objectPath = `vendors/${vendorId}/docs/pages/${hash}-p${i}.jpg`;
    const token = crypto.randomUUID();
    await bucket.file(objectPath).save(jpg, {
      resumable: false,
      metadata: { contentType: 'image/jpeg', cacheControl: 'public, max-age=31536000, immutable', metadata: { firebaseStorageDownloadTokens: token } },
    });
    urls.push(`https://firebasestorage.googleapis.com/v0/b/${bucket.name}/o/${encodeURIComponent(objectPath)}?alt=media&token=${token}`);
    page.cleanup();
  }
  await doc.destroy();
  return urls;
}

// ---------------------------------------------------------------------------------------------
// PDF -> packages JSON via Claude (document input; the model reads the PDF directly)
// ---------------------------------------------------------------------------------------------
const PROMPT = `This is a wedding vendor's price sheet. Return ONLY a JSON object -- no prose, no code fences -- with exactly this shape:
{"groups":[{"name":"","tagline":"","packages":[{"name":"","hours":"","price":"","payInFull":"","includes":[""],"tag":""}],"addOns":[{"name":"","price":""}]}]}
Rules:
- One group per section or collection on the sheet, using the sheet's own heading (e.g. "The Videography Collection"). If the sheet has no sections, return one group with name "".
- Keep the sheet's order for groups and packages.
- price: the package's main or standard price exactly as printed, e.g. "$1,700". If the sheet prints a plan price and a discounted pay-in-full price, price is the plan price and payInFull is the pay-in-full price; otherwise payInFull is "".
- hours: the coverage length in words, e.g. "6 hours of coverage"; "" if none is printed.
- includes: the package's listed items in order, plain text, one item per entry, without prices. Leave out an item that only restates the hours.
- tag: a label printed on the package such as "Most popular" or "Best value"; "" if none.
- addOns: a la carte extras, enhancements or upgrades printed for that section, each with its price as printed.
- Never invent a package, price or item that is not on the sheet. Never put currency amounts anywhere except price, payInFull and addOns[].price.`;

async function extractPackages(buf) {
  const key = process.env.ANTHROPIC_API_KEY;
  if (!key) throw new Error('ANTHROPIC_API_KEY is not set');
  const res = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: { 'x-api-key': key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json' },
    body: JSON.stringify({
      model: MODEL,
      max_tokens: 6000,
      messages: [{ role: 'user', content: [
        { type: 'document', source: { type: 'base64', media_type: 'application/pdf', data: buf.toString('base64') } },
        { type: 'text', text: PROMPT },
      ] }],
    }),
  });
  if (!res.ok) throw new Error(`anthropic ${res.status}: ${(await res.text()).slice(0, 300)}`);
  const data = await res.json();
  const text = (data.content || []).filter((c) => c.type === 'text').map((c) => c.text).join('\n');
  return normalize(parseJson(text));
}

function parseJson(text) {
  const t = String(text || '').trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '');
  const a = t.indexOf('{'), b = t.lastIndexOf('}');
  if (a < 0 || b < a) throw new Error('no JSON in model reply');
  return JSON.parse(t.slice(a, b + 1));
}

// The model's JSON -> the maps the page renders. Flat packages, each tagged with its group.
function normalize(j) {
  const str = (x) => (x == null ? '' : String(x)).replace(/\s+/g, ' ').trim();
  const money = (x) => {
    const s = str(x); const m = /\$?\s*(\d[\d,]*)(?:\.(\d+))?/.exec(s);
    if (!m) return s;
    const n = parseInt(m[1].replace(/,/g, ''), 10);
    return Number.isFinite(n) ? '$' + n.toLocaleString('en-US') : s;
  };
  const packages = [], addOns = [];
  const groups = Array.isArray(j && j.groups) ? j.groups : [];
  for (const g of groups) {
    const group = str(g && g.name);
    for (const p of (Array.isArray(g && g.packages) ? g.packages : [])) {
      const name = str(p && p.name); if (!name) continue;
      const inc = Array.isArray(p.includes) ? p.includes.map(str).filter(Boolean) : String(p.includes || '').split(/\n|;/).map(str).filter(Boolean);
      const pk = { name, group, price: money(p.price), hours: str(p.hours), includes: inc.join('\n') };
      if (str(p.payInFull)) pk.payInFull = money(p.payInFull);
      if (str(p.offPeak)) pk.offPeak = money(p.offPeak);
      if (str(p.tag)) pk.tag = str(p.tag);
      packages.push(pk);
    }
    for (const a of (Array.isArray(g && g.addOns) ? g.addOns : [])) {
      const name = str(a && a.name); if (!name) continue;
      addOns.push({ name, group, price: money(a.price) });
    }
  }
  let low = Infinity;
  for (const p of packages) for (const s of [p.price, p.payInFull]) {
    const n = parseInt(String(s || '').replace(/[^\d]/g, ''), 10);
    if (Number.isFinite(n) && n > 0 && n < low) low = n;
  }
  return { packages, addOns, startingPrice: Number.isFinite(low) ? '$' + low.toLocaleString('en-US') : '' };
}

// Same packages? name + price in order is enough to tell a dashboard edit from an untouched set.
function samePackages(a, b) {
  if (!Array.isArray(a) || !Array.isArray(b) || a.length !== b.length) return false;
  const k = (p) => [p && p.name, p && p.price].map((x) => String(x || '').replace(/\s+/g, ' ').trim().toLowerCase()).join('|');
  return a.every((p, i) => k(p) === k(b[i]));
}

exports._internal = { normalize, samePackages, parseJson, renderPages };
