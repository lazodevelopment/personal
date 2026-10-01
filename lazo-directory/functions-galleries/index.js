// Lazo — post-wedding client delivery galleries (JC-LAZO-GALLERY-0911-006)
//
// Separate functions codebase: keeps the AWS SDK dependency and gallery deploys
// away from the main 4,800-line index.js (and away from its vCPU quota history).
//
// Exports
//   galleryCreate    vendor starts a gallery        -> { slug }
//   galleryPresign   batch of presigned PUT URLs    -> { urls: [...] }
//   galleryFinalize  writes manifest.json, go live  -> { ok, url, photoCount }
//   gallerySettings  passcode/downloads/store/cover -> { ok }
//   galleryDelete    removes R2 objects + doc       -> { ok, deleted }
//
// Gate: vendors/{id}.claimedBy === uid AND (tier === 'studio' || foundingPreview).
// Photos live in the lazo-galleries R2 bucket; the worker serves them at
// /g/{slug}. Nothing is visible until galleryFinalize sets status: 'live'.
//
// v2 (0912): passcode stored as sha256 hex (the doc is world-readable so the
// worker can hydrate it unauthenticated); ownerUid on the doc for the uploader's
// list query; galleryFinalize gains append:true to merge into a live gallery.
//
// Secrets required (firebase functions:secrets:set ...):
//   R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY

const { onCall, HttpsError } = require("firebase-functions/v2/https");
const { defineSecret } = require("firebase-functions/params");
const { setGlobalOptions } = require("firebase-functions/v2");
const admin = require("firebase-admin");
const crypto = require("crypto");

const { S3Client, PutObjectCommand, GetObjectCommand, DeleteObjectsCommand, ListObjectsV2Command } =
  require("@aws-sdk/client-s3");
const { getSignedUrl } = require("@aws-sdk/s3-request-presigner");

// Same shape as the main codebase: gen-1 CPU share, one request per instance.
setGlobalOptions({ region: "us-central1", cpu: "gcf_gen1", concurrency: 1 });

const R2_ACCOUNT_ID = defineSecret("R2_ACCOUNT_ID");
const R2_ACCESS_KEY_ID = defineSecret("R2_ACCESS_KEY_ID");
const R2_SECRET_ACCESS_KEY = defineSecret("R2_SECRET_ACCESS_KEY");
const R2_SECRETS = [R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY];

admin.initializeApp();
const db = admin.firestore();

const BUCKET = "lazo-galleries";
const VARIANTS = ["full", "web", "thumb"];
const MAX_PHOTOS = 3000;            // per gallery
const MAX_PRESIGN_BATCH = 40;       // photos per presign call (x3 variants = 120 urls)
const PUT_URL_TTL = 60 * 60;        // 1 hour — plenty for one file, short if leaked
const GALLERY_TTL_DAYS = 365;       // guaranteed live for a year (see for-vendors copy)

function r2(env) {
  return new S3Client({
    region: "auto",
    endpoint: `https://${R2_ACCOUNT_ID.value()}.r2.cloudflarestorage.com`,
    credentials: {
      accessKeyId: R2_ACCESS_KEY_ID.value(),
      secretAccessKey: R2_SECRET_ACCESS_KEY.value(),
    },
  });
}

// ---------------------------------------------------------------------------
// shared guards
// ---------------------------------------------------------------------------
async function requireStudioVendor(request) {
  if (!request.auth) throw new HttpsError("unauthenticated", "Sign in first.");
  const uid = request.auth.uid;
  const vendorId = ((request.data && request.data.vendorId) || "").toString();
  if (!vendorId) throw new HttpsError("invalid-argument", "vendorId required.");

  const vSnap = await db.collection("vendors").doc(vendorId).get();
  if (!vSnap.exists || vSnap.data().claimedBy !== uid) {
    throw new HttpsError("permission-denied", "Not your vendor profile.");
  }
  const v = vSnap.data();
  const tierOk = v.tier === "studio" || v.foundingPreview === true;
  if (!tierOk) throw new HttpsError("failed-precondition", "studio-required");
  return { uid, vendorId, v };
}

// Gallery owned by this vendor, for presign/finalize/settings/delete.
async function requireOwnedGallery(request) {
  const { uid, vendorId, v } = await requireStudioVendor(request);
  const slug = ((request.data && request.data.slug) || "").toString().toLowerCase();
  if (!/^[a-z0-9-]{3,80}$/.test(slug)) {
    throw new HttpsError("invalid-argument", "Bad gallery slug.");
  }
  const gRef = db.collection("galleries").doc(slug);
  const gSnap = await gRef.get();
  if (!gSnap.exists) throw new HttpsError("not-found", "Gallery not found.");
  if (gSnap.data().vendorId !== vendorId) {
    throw new HttpsError("permission-denied", "Not your gallery.");
  }
  return { uid, vendorId, v, slug, gRef, g: gSnap.data() };
}

function slugify(s) {
  return String(s || "")
    .toLowerCase()
    .normalize("NFKD").replace(/[\u0300-\u036f]/g, "")
    .replace(/&/g, " and ")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48);
}

// The galleries doc is world-readable (the worker hydrates it over REST with no
// auth, like weddingSites), so the passcode is never stored — only its hash.
// Empty passcode -> empty string (gallery is open).
function passHash(p) {
  const norm = String(p || "").trim().toLowerCase().slice(0, 40);
  return norm ? crypto.createHash("sha256").update(norm).digest("hex") : "";
}

// A gallery URL gets forwarded to relatives, so the slug carries a random tail:
// guessing /g/sarah-and-tom shouldn't land on someone's wedding.
async function uniqueSlug(base) {
  const stem = slugify(base) || "gallery";
  for (let i = 0; i < 6; i++) {
    const slug = `${stem}-${crypto.randomBytes(3).toString("hex")}`;
    const snap = await db.collection("galleries").doc(slug).get();
    if (!snap.exists) return slug;
  }
  throw new HttpsError("internal", "Could not allocate a gallery URL. Try again.");
}

// ---------------------------------------------------------------------------
// galleryCreate — the shell. No photos yet, status 'draft', invisible.
// ---------------------------------------------------------------------------
exports.galleryCreate = onCall(
  { region: "us-central1", timeoutSeconds: 30, memory: "256MiB" },
  async (request) => {
    const { uid, vendorId, v } = await requireStudioVendor(request);
    const d = request.data || {};

    const names = (d.names || "").toString().trim().slice(0, 120);
    if (!names) throw new HttpsError("invalid-argument", "Couple names required.");
    const dateIso = (d.dateIso || "").toString().slice(0, 10);
    if (dateIso && !/^\d{4}-\d{2}-\d{2}$/.test(dateIso)) {
      throw new HttpsError("invalid-argument", "dateIso must be YYYY-MM-DD.");
    }

    const slug = await uniqueSlug(names);
    const now = Date.now();

    await db.collection("galleries").doc(slug).set({
      slug,
      vendorId,
      ownerUid: uid,
      vendorName: v.name || v.businessName || "",
      vendorSlug: v.slug || "",
      names,
      dateIso,
      message: (d.message || "").toString().slice(0, 600),
      passcodeHash: passHash(d.passcode),
      downloadsOn: d.downloadsOn !== false,
      storeOn: d.storeOn !== false,
      coverId: "",
      photoCount: 0,
      status: "draft",
      bytes: 0,
      createdAt: admin.firestore.FieldValue.serverTimestamp(),
      expiresAt: new Date(now + GALLERY_TTL_DAYS * 86400000).toISOString(),
    });

    return { slug, url: `https://meetlazo.com/g/${slug}` };
  }
);

// ---------------------------------------------------------------------------
// galleryPresign — one PUT url per object. The uploader sends photos in
// batches and remembers which ids finished, so a dropped connection resumes
// by re-requesting urls for the ids it never confirmed.
//
// data: { vendorId, slug, photos: [{ id, ext? }] }
// ---------------------------------------------------------------------------
exports.galleryPresign = onCall(
  { region: "us-central1", timeoutSeconds: 120, memory: "256MiB", secrets: R2_SECRETS },
  async (request) => {
    const { slug, g } = await requireOwnedGallery(request);
    const photos = (request.data && request.data.photos) || [];
    if (!Array.isArray(photos) || !photos.length) {
      throw new HttpsError("invalid-argument", "photos[] required.");
    }
    if (photos.length > MAX_PRESIGN_BATCH) {
      throw new HttpsError("invalid-argument",
        `Too many photos in one call (max ${MAX_PRESIGN_BATCH}).`);
    }
    if ((g.photoCount || 0) + photos.length > MAX_PHOTOS) {
      throw new HttpsError("failed-precondition",
        `A gallery holds at most ${MAX_PHOTOS} photos.`);
    }

    const client = r2();
    const out = [];
    for (const p of photos) {
      const id = (p && p.id || "").toString();
      if (!/^[A-Za-z0-9_-]{6,64}$/.test(id)) {
        throw new HttpsError("invalid-argument", `Bad photo id: ${id}`);
      }
      const entry = { id, put: {} };
      for (const variant of VARIANTS) {
        const cmd = new PutObjectCommand({
          Bucket: BUCKET,
          Key: `${slug}/${variant}/${id}.jpg`,
          ContentType: "image/jpeg",
        });
        entry.put[variant] = await getSignedUrl(client, cmd, { expiresIn: PUT_URL_TTL });
      }
      out.push(entry);
    }
    return { urls: out, expiresIn: PUT_URL_TTL };
  }
);

// ---------------------------------------------------------------------------
// galleryFinalize — writes the manifest the worker reads and flips status to
// 'live'. Re-runnable: a vendor adding photos later just finalizes again.
//
// data: { vendorId, slug, photos: [{ id, name, w, h, md5, bytes }], coverId?, append? }
// append:true merges into the existing manifest (dedupe by id) so a vendor can
// add a second batch to a delivered gallery without re-sending the first.
// ---------------------------------------------------------------------------
exports.galleryFinalize = onCall(
  { region: "us-central1", timeoutSeconds: 120, memory: "512MiB", secrets: R2_SECRETS },
  async (request) => {
    const { slug, gRef } = await requireOwnedGallery(request);
    const photos = (request.data && request.data.photos) || [];
    if (!Array.isArray(photos) || !photos.length) {
      throw new HttpsError("invalid-argument", "photos[] required.");
    }
    if (photos.length > MAX_PHOTOS) {
      throw new HttpsError("invalid-argument", `At most ${MAX_PHOTOS} photos.`);
    }

    let bytes = 0;
    let manifest = photos.map((p, i) => {
      const id = (p && p.id || "").toString();
      if (!/^[A-Za-z0-9_-]{6,64}$/.test(id)) {
        throw new HttpsError("invalid-argument", `Bad photo id: ${id}`);
      }
      const w = Number(p.w) || 0, h = Number(p.h) || 0;
      if (!w || !h) {
        // WHCC's editor needs true original dimensions; a zero here means a
        // print order later can't be built. Fail now, not at checkout.
        throw new HttpsError("invalid-argument", `Missing dimensions for ${id}.`);
      }
      const md5 = (p.md5 || "").toString().toLowerCase();
      if (!/^[a-f0-9]{32}$/.test(md5)) {
        // ImageHash in the WHCC order payload. Same reasoning as above.
        throw new HttpsError("invalid-argument", `Missing or bad md5 for ${id}.`);
      }
      bytes += Number(p.bytes) || 0;
      return {
        id,
        name: (p.name || `${id}.jpg`).toString().slice(0, 160),
        w, h, md5,
        bytes: Number(p.bytes) || 0,
        seq: i,
      };
    });

    const client = r2();
    if (request.data.append === true) {
      try {
        const prev = await client.send(new GetObjectCommand({
          Bucket: BUCKET, Key: `${slug}/manifest.json` }));
        const existing = JSON.parse(await prev.Body.transformToString());
        const seen = new Set(manifest.map((p) => p.id));
        const kept = (Array.isArray(existing) ? existing : []).filter((p) => !seen.has(p.id));
        manifest = kept.concat(manifest).map((p, i) => ({ ...p, seq: i }));
        if (manifest.length > MAX_PHOTOS) {
          throw new HttpsError("failed-precondition", `A gallery holds at most ${MAX_PHOTOS} photos.`);
        }
        bytes += kept.reduce((n, p) => n + (Number(p.bytes) || 0), 0);
      } catch (e) {
        if (e instanceof HttpsError) throw e;
        // no previous manifest — append to nothing is just a write
      }
    }

    await client.send(new PutObjectCommand({
      Bucket: BUCKET,
      Key: `${slug}/manifest.json`,
      Body: JSON.stringify(manifest),
      ContentType: "application/json",
    }));

    const coverId = (request.data.coverId || manifest[0].id).toString();
    await gRef.set({
      photoCount: manifest.length,
      coverId: manifest.some((p) => p.id === coverId) ? coverId : manifest[0].id,
      bytes,
      status: "live",
      deliveredAt: admin.firestore.FieldValue.serverTimestamp(),
    }, { merge: true });

    return {
      ok: true,
      photoCount: manifest.length,
      url: `https://meetlazo.com/g/${slug}`,
    };
  }
);

// ---------------------------------------------------------------------------
// gallerySettings — passcode, downloads, store, cover, message, expiry bump.
// ---------------------------------------------------------------------------
exports.gallerySettings = onCall(
  { region: "us-central1", timeoutSeconds: 30, memory: "256MiB" },
  async (request) => {
    const { gRef } = await requireOwnedGallery(request);
    const d = request.data || {};
    const patch = {};

    if ("passcode" in d) patch.passcodeHash = passHash(d.passcode);
    if ("downloadsOn" in d) patch.downloadsOn = !!d.downloadsOn;
    if ("storeOn" in d) patch.storeOn = !!d.storeOn;
    if ("message" in d) patch.message = (d.message || "").toString().slice(0, 600);
    if ("names" in d) patch.names = (d.names || "").toString().trim().slice(0, 120);
    if ("coverId" in d) {
      const c = (d.coverId || "").toString();
      if (!/^[A-Za-z0-9_-]{6,64}$/.test(c)) {
        throw new HttpsError("invalid-argument", "Bad coverId.");
      }
      patch.coverId = c;
    }
    // 'live' | 'hidden' only — a vendor can hide a gallery, not forge one live
    // without finalizing it.
    if ("status" in d) {
      const s = (d.status || "").toString();
      if (!["live", "hidden"].includes(s)) {
        throw new HttpsError("invalid-argument", "status must be live or hidden.");
      }
      patch.status = s;
    }
    if (d.extendYear === true) {
      patch.expiresAt = new Date(Date.now() + GALLERY_TTL_DAYS * 86400000).toISOString();
    }

    if (!Object.keys(patch).length) {
      throw new HttpsError("invalid-argument", "Nothing to update.");
    }
    patch.updatedAt = admin.firestore.FieldValue.serverTimestamp();
    await gRef.set(patch, { merge: true });
    return { ok: true };
  }
);

// ---------------------------------------------------------------------------
// galleryDelete — the vendor's own delete. Clears R2 objects then the doc.
// Requires confirm: true so a misfired click can't erase a wedding.
// ---------------------------------------------------------------------------
exports.galleryDelete = onCall(
  { region: "us-central1", timeoutSeconds: 300, memory: "512MiB", secrets: R2_SECRETS },
  async (request) => {
    const { slug, gRef } = await requireOwnedGallery(request);
    if (request.data.confirm !== true) {
      throw new HttpsError("failed-precondition", "confirm:true required.");
    }

    const client = r2();
    let token, deleted = 0;
    do {
      const list = await client.send(new ListObjectsV2Command({
        Bucket: BUCKET, Prefix: `${slug}/`, ContinuationToken: token,
      }));
      const objs = (list.Contents || []).map((o) => ({ Key: o.Key }));
      if (objs.length) {
        await client.send(new DeleteObjectsCommand({
          Bucket: BUCKET, Delete: { Objects: objs },
        }));
        deleted += objs.length;
      }
      token = list.IsTruncated ? list.NextContinuationToken : undefined;
    } while (token);

    await gRef.delete();
    return { ok: true, deleted };
  }
);

// JC-LAZO-WORKER-0930-FSAUTH: the Cloudflare worker reads couple sites out of
// Firestore. Those docs used to be world-readable so the worker could read
// them anonymously, which also let anyone pull a couple's guest list. Now the
// worker signs in: it presents WORKER_TOKEN_KEY here, gets a custom token for
// the fixed uid "lazo-worker" with the {worker:true} claim, exchanges it for an
// ID token, and the rules grant reads to that claim. Nothing else can mint it.
const { onRequest } = require("firebase-functions/v2/https");
const WORKER_TOKEN_KEY = defineSecret("WORKER_TOKEN_KEY");
exports.workerToken = onRequest({ secrets: [WORKER_TOKEN_KEY], cors: false }, async (req, res) => {
  const given = String(req.get("x-lazo-key") || "").trim();
  const want = String(WORKER_TOKEN_KEY.value() || "").trim();
  if (!want || given.length !== want.length
      || !crypto.timingSafeEqual(Buffer.from(given), Buffer.from(want))) {
    res.status(401).json({ ok: false }); return;
  }
  const token = await admin.auth().createCustomToken("lazo-worker", { worker: true });
  res.set("cache-control", "no-store").json({ ok: true, token });
});
