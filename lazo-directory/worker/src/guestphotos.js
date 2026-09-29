// JC-LAZO-WORKER-0929-GUESTPHOTOS-001: photos guests share from their phones.
//
// A couple's site (/w/{slug}) gets a "Share the day as you saw it" section from
// the wedding day on. Guests pick photos on their phone, the page shrinks them
// to 2000px JPEGs, and they land here:
//
//   POST /api/w/{slug}/photos            multipart: file, name, caption
//   GET  /api/w/{slug}/photos            newest first, JSON
//   GET  /w/{slug}/photo/{id}.{jpg|png|webp}   the bytes, cached a day
//
// Photos live in the lazo-galleries bucket (binding GALLERIES) under
// guest/{slug}/{id}.{ext}, with the guest's name and caption as object
// metadata; there is no manifest to race on, the listing IS the bucket.
// deploy_site.py never touches that bucket, so a prune cannot eat them.
//
// The couple moderates from the dashboard: weddingSites.guestPhotosOn turns
// the wall off, weddingSites.guestPhotosRemoved lists ids to take down. The
// worker has no Firestore credentials, so removal is carried out lazily - the
// next listing deletes any object whose id is on that list. The doc is
// world-readable, which is exactly why "hidden" would not be enough: the ids
// would be public, so the bytes must actually go.
//
// Limits: 10 MB a photo, JPEG / PNG / WebP by magic bytes (never by the
// header the browser sends), 1,000 photos a site.

const MAX_BYTES = 10 * 1024 * 1024;
const MAX_PHOTOS = 1000;   // one R2 list page; the check below is one call
const PROJECT = "lazo-513ec";

const CORS = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "GET, POST, OPTIONS",
  "access-control-allow-headers": "content-type",
};

const json = (obj, status = 200, extra = {}) =>
  new Response(JSON.stringify(obj), { status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", ...CORS, ...extra } });

function fsVal(v) {
  if (v == null) return null;
  if ("stringValue" in v) return v.stringValue;
  if ("integerValue" in v) return Number(v.integerValue);
  if ("doubleValue" in v) return v.doubleValue;
  if ("booleanValue" in v) return v.booleanValue;
  if ("timestampValue" in v) return v.timestampValue;
  if ("arrayValue" in v) return (v.arrayValue.values || []).map(fsVal);
  if ("mapValue" in v) {
    const o = {};
    for (const [k, x] of Object.entries(v.mapValue.fields || {})) o[k] = fsVal(x);
    return o;
  }
  return null;
}

// The site doc, held 30 s at the edge so a burst of uploads at the reception
// does not turn into a burst of Firestore reads.
async function siteDoc(slug) {
  const key = new Request(`https://meetlazo.com/_internal/guestphotos/site/${slug}`);
  const hit = await caches.default.match(key);
  if (hit) { try { return await hit.json(); } catch (e) {} }
  const u = `https://firestore.googleapis.com/v1/projects/${PROJECT}/databases/(default)/documents/weddingSites/${encodeURIComponent(slug)}`
    + "?mask.fieldPaths=guestPhotosOn&mask.fieldPaths=guestPhotosRemoved&mask.fieldPaths=names&mask.fieldPaths=passcode";
  const r = await fetch(u, { headers: { accept: "application/json" } });
  if (!r.ok) return null;
  const doc = await r.json();
  const f = doc.fields || {};
  const out = {
    on: fsVal(f.guestPhotosOn) !== false,
    removed: (fsVal(f.guestPhotosRemoved) || []).map(String),
    names: String(fsVal(f.names) || ""),
  };
  await caches.default.put(key, new Response(JSON.stringify(out), {
    headers: { "content-type": "application/json", "cache-control": "public, max-age=30" } }));
  return out;
}

function sniff(bytes) {
  const b = new Uint8Array(bytes.slice(0, 16));
  if (b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff) return "jpg";
  if (b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47) return "png";
  if (b[0] === 0x52 && b[1] === 0x49 && b[2] === 0x46 && b[3] === 0x46 &&
      b[8] === 0x57 && b[9] === 0x45 && b[10] === 0x42 && b[11] === 0x50) return "webp";
  return "";
}
const MIME = { jpg: "image/jpeg", png: "image/png", webp: "image/webp" };

// ids sort by time as plain strings: fixed-width base-36 clock + 6 random chars
function newId() {
  const t = Date.now().toString(36).padStart(9, "0");
  const a = "abcdefghijklmnopqrstuvwxyz0123456789";
  const r = crypto.getRandomValues(new Uint8Array(6));
  let s = "";
  for (const x of r) s += a[x % 36];
  return t + s;
}

const clean = (s, n) => String(s || "").replace(/[\u0000-\u001f\u007f]/g, " ").replace(/\s+/g, " ").trim().slice(0, n);

async function listAll(slug, env) {
  const prefix = `guest/${slug}/`;
  const out = [];
  let cursor;
  for (let i = 0; i < 3; i++) {
    const page = await env.GALLERIES.list({ prefix, limit: 1000, cursor, include: ["customMetadata"] });
    for (const o of page.objects) {
      const m = o.key.slice(prefix.length).match(/^([a-z0-9]{15})\.(jpg|png|webp)$/);
      if (!m) continue;
      const cm = o.customMetadata || {};
      out.push({ id: m[1], ext: m[2], key: o.key, name: cm.name || "", caption: cm.caption || "",
                 at: o.uploaded ? new Date(o.uploaded).toISOString() : "" });
    }
    if (!page.truncated) break;
    cursor = page.cursor;
  }
  out.sort((a, b) => (a.id < b.id ? 1 : a.id > b.id ? -1 : 0));
  return out;
}

async function listPhotos(slug, env) {
  const site = await siteDoc(slug);
  if (!site) return json({ ok: false, error: "not_found" }, 404);
  let items = await listAll(slug, env);
  // moderation: the couple listed ids to take down - delete them now
  const removed = new Set(site.removed);
  if (removed.size) {
    const gone = items.filter(p => removed.has(p.id));
    if (gone.length) {
      await env.GALLERIES.delete(gone.map(p => p.key));
      items = items.filter(p => !removed.has(p.id));
    }
  }
  const photos = items.map(p => ({
    id: p.id, name: p.name, caption: p.caption, at: p.at,
    url: `https://meetlazo.com/w/${slug}/photo/${p.id}.${p.ext}`,
  }));
  return json({ ok: true, on: site.on, count: photos.length, photos }, 200,
    { "cache-control": "public, max-age=15, s-maxage=15" });
}

async function uploadPhoto(slug, req, env) {
  const site = await siteDoc(slug);
  if (!site) return json({ ok: false, error: "not_found" }, 404);
  if (!site.on) return json({ ok: false, error: "closed", message: "The couple has closed the photo wall." }, 403);
  const len = Number(req.headers.get("content-length") || 0);
  if (len > MAX_BYTES + 4096) return json({ ok: false, error: "too_large", message: "That photo is over 10 MB." }, 413);
  let form;
  try { form = await req.formData(); } catch (e) { return json({ ok: false, error: "bad_request" }, 400); }
  const file = form.get("file");
  if (!file || typeof file === "string" || !file.arrayBuffer) return json({ ok: false, error: "no_file" }, 400);
  if (file.size > MAX_BYTES) return json({ ok: false, error: "too_large", message: "That photo is over 10 MB." }, 413);
  const bytes = await file.arrayBuffer();
  const ext = sniff(bytes);
  if (!ext) return json({ ok: false, error: "not_image", message: "Only JPEG, PNG and WebP photos, please." }, 415);
  // a ceiling per site; one list call is cheap next to a 2 MB upload
  const first = await env.GALLERIES.list({ prefix: `guest/${slug}/`, limit: MAX_PHOTOS });
  if (first.truncated || first.objects.length >= MAX_PHOTOS)
    return json({ ok: false, error: "full", message: "The wall is full - the couple has plenty to look through!" }, 409);
  const id = newId();
  const key = `guest/${slug}/${id}.${ext}`;
  const name = clean(form.get("name"), 60);
  const caption = clean(form.get("caption"), 140);
  await env.GALLERIES.put(key, bytes, {
    httpMetadata: { contentType: MIME[ext], cacheControl: "public, max-age=86400" },
    customMetadata: { name, caption, ip: req.headers.get("cf-connecting-ip") || "" },
  });
  return json({ ok: true, photo: { id, name, caption, at: new Date().toISOString(),
    url: `https://meetlazo.com/w/${slug}/photo/${id}.${ext}` } });
}

async function servePhoto(slug, id, ext, env) {
  const obj = await env.GALLERIES.get(`guest/${slug}/${id}.${ext}`);
  if (!obj) return new Response("Not found", { status: 404, headers: { "cache-control": "public, max-age=60" } });
  return new Response(obj.body, { headers: {
    "content-type": MIME[ext] || "application/octet-stream",
    "cache-control": "public, max-age=86400, s-maxage=604800, immutable",
    "access-control-allow-origin": "*",
    "x-robots-tag": "noindex",
    "x-lazo": "tied-together",
  }});
}

// Returns a Response for the guest-photo routes, else null.
export async function guestPhotosRoute(url, req, env) {
  if (!env.GALLERIES) return null;
  const api = url.pathname.match(/^\/api\/w\/([a-z0-9-]{1,80})\/photos\/?$/);
  if (api) {
    if (req.method === "OPTIONS") return new Response(null, { headers: CORS });
    if (req.method === "GET") return listPhotos(api[1], env);
    if (req.method === "POST") return uploadPhoto(api[1], req, env);
    return json({ ok: false, error: "method" }, 405);
  }
  const img = url.pathname.match(/^\/w\/([a-z0-9-]{1,80})\/photo\/([a-z0-9]{15})\.(jpg|png|webp)$/);
  if (img && req.method === "GET") return servePhoto(img[1], img[2], img[3], env);
  return null;
}
