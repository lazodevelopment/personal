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

// JC-LAZO-WORKER-0929-HOLD-001: a moderation queue. With weddingSites.
// guestPhotosHold on, uploads land under guest/{slug}/pending/ and only the
// couple (a Firebase ID token the dashboard sends, see auth.js) can list them
// (?pending=1) and approve them (POST /api/w/{slug}/photos/approve {ids}),
// which copies each object to the live prefix. /w/{slug}/photos/download is
// a page that zips the whole wall in the browser (the list is public anyway).
import { verifyIdToken, ownsSite } from "./auth.js";
import { fsHeaders, siteLocked, lockedResponse } from "./fsauth.js";  // JC-LAZO-WORKER-0930-FSAUTH

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
    + "?mask.fieldPaths=guestPhotosOn&mask.fieldPaths=guestPhotosRemoved&mask.fieldPaths=names&mask.fieldPaths=passcode&mask.fieldPaths=guestPhotosHold&mask.fieldPaths=coupleUid";
  const r = await fetch(u, { headers: await fsHeaders() });
  if (!r.ok) return null;
  const doc = await r.json();
  const f = doc.fields || {};
  const out = {
    passcode: String(fsVal(f.passcode) || "").trim(),
    on: fsVal(f.guestPhotosOn) !== false,
    hold: fsVal(f.guestPhotosHold) === true,
    removed: (fsVal(f.guestPhotosRemoved) || []).map(String),
    names: String(fsVal(f.names) || ""),
    coupleUid: String(fsVal(f.coupleUid) || ""),
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

async function listAll(slug, env, sub = "") {
  const prefix = `guest/${slug}/${sub}`;
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

async function coupleOf(req, slug, site) {
  const who = await verifyIdToken(req);
  if (!who) return null;
  const ok = await ownsSite(who, { coupleUid: site.coupleUid });
  return ok ? who : null;
}

async function listPhotos(slug, env, url, req) {
  const site = await siteDoc(slug);
  if (!site) return json({ ok: false, error: "not_found" }, 404);
  if (url.searchParams.get("pending") === "1") {
    const who = await coupleOf(req, slug, site);
    if (!who) return json({ ok: false, error: "forbidden" }, 403);
    const pend = await listAll(slug, env, "pending/");
    return json({ ok: true, hold: site.hold, count: pend.length, photos: pend.map(p => ({
      id: p.id, name: p.name, caption: p.caption, at: p.at,
      url: `https://meetlazo.com/w/${slug}/photo/pending/${p.id}.${p.ext}` })) });
  }
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
  return json({ ok: true, on: site.on, hold: site.hold, count: photos.length, photos }, 200,
    { "cache-control": "public, max-age=15, s-maxage=15" });
}

// the couple approves (copy to live, drop the pending copy) or declines
async function approvePhotos(slug, req, env) {
  const site = await siteDoc(slug);
  if (!site) return json({ ok: false, error: "not_found" }, 404);
  const who = await coupleOf(req, slug, site);
  if (!who) return json({ ok: false, error: "forbidden" }, 403);
  let b; try { b = await req.json(); } catch (e) { return json({ ok: false }, 400); }
  const ids = (Array.isArray(b.ids) ? b.ids : []).map(String).filter(x => /^[a-z0-9]{15}$/.test(x)).slice(0, 200);
  const decline = b.decline === true;
  const pend = await listAll(slug, env, "pending/");
  let n = 0;
  for (const p of pend) {
    if (!ids.includes(p.id)) continue;
    if (!decline) {
      const o = await env.GALLERIES.get(p.key);
      if (o) await env.GALLERIES.put(`guest/${slug}/${p.id}.${p.ext}`, o.body, {
        httpMetadata: { contentType: MIME[p.ext], cacheControl: "public, max-age=86400" },
        customMetadata: o.customMetadata || {} });
    }
    await env.GALLERIES.delete(p.key);
    n++;
  }
  return json({ ok: true, [decline ? "declined" : "approved"]: n });
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
  const key = `guest/${slug}/${site.hold ? "pending/" : ""}${id}.${ext}`;
  const name = clean(form.get("name"), 60);
  const caption = clean(form.get("caption"), 140);
  await env.GALLERIES.put(key, bytes, {
    httpMetadata: { contentType: MIME[ext], cacheControl: "public, max-age=86400" },
    customMetadata: { name, caption, ip: req.headers.get("cf-connecting-ip") || "" },
  });
  return json({ ok: true, held: site.hold, photo: { id, name, caption, at: new Date().toISOString(),
    url: `https://meetlazo.com/w/${slug}/photo/${site.hold ? "pending/" : ""}${id}.${ext}` } });
}

async function servePhoto(slug, id, ext, env, sub = "") {
  const obj = await env.GALLERIES.get(`guest/${slug}/${sub}${id}.${ext}`);
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
  // JC-LAZO-WORKER-0930-FSAUTH: a passcode site's photos need the passcode cookie (approve is the couple's own, token-checked)
  const any = url.pathname.match(/^\/(?:api\/)?w\/([a-z0-9-]{1,80})\/photo/);
  if (any && req.method !== "OPTIONS" && !/\/photos\/approve\/?$/.test(url.pathname)) {
    const site = await siteDoc(any[1]);
    if (site && site.passcode && await siteLocked(any[1], req, site.passcode)) return lockedResponse();
  }
  const api = url.pathname.match(/^\/api\/w\/([a-z0-9-]{1,80})\/photos\/?$/);
  if (api) {
    if (req.method === "OPTIONS") return new Response(null, { headers: { ...CORS, "access-control-allow-headers": "content-type, authorization" } });
    if (req.method === "GET") return listPhotos(api[1], env, url, req);
    if (req.method === "POST") return uploadPhoto(api[1], req, env);
    return json({ ok: false, error: "method" }, 405);
  }
  const apv = url.pathname.match(/^\/api\/w\/([a-z0-9-]{1,80})\/photos\/approve\/?$/);
  if (apv) {
    if (req.method === "OPTIONS") return new Response(null, { headers: { ...CORS, "access-control-allow-headers": "content-type, authorization" } });
    if (req.method === "POST") return approvePhotos(apv[1], req, env);
    return json({ ok: false, error: "method" }, 405);
  }
  const img = url.pathname.match(/^\/w\/([a-z0-9-]{1,80})\/photo\/(pending\/)?([a-z0-9]{15})\.(jpg|png|webp)$/);
  if (img && req.method === "GET") return servePhoto(img[1], img[3], img[4], env, img[2] || "");
  const dl = url.pathname.match(/^\/w\/([a-z0-9-]{1,80})\/photos\/download\/?$/);
  if (dl && req.method === "GET") return downloadPage(dl[1]);
  return null;
}

// JC-LAZO-WORKER-0929-HOLD-001: "download everything" - the browser fetches
// each photo and packs a zip with fflate, so the worker never spends CPU on a
// gigabyte of JPEGs. The listing is public, so the page needs no login.
function downloadPage(slug) {
  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>Download the photo wall</title>
<style>body{margin:0;background:#FAF6F0;color:#241E2B;font-family:Helvetica,Arial,sans-serif}.wrap{max-width:460px;margin:0 auto;padding:40px 20px}
h1{font-family:Georgia,serif;font-weight:600;font-size:30px;color:#52284F;margin:0 0 6px}p{color:#6B5F72;font-size:14px;line-height:1.5}
button{margin-top:16px;width:100%;border:0;border-radius:12px;padding:14px;background:#52284F;color:#FAF6F0;font-size:15px;font-weight:700;cursor:pointer}button:disabled{opacity:.6}
.bar{height:8px;border-radius:999px;background:rgba(82,40,79,.12);overflow:hidden;margin-top:16px}.bar span{display:block;height:100%;width:0;background:#D9B77C;transition:width .3s}
.st{font-size:13px;color:#6B5F72;margin-top:8px;min-height:18px}</style></head><body><div class="wrap">
<h1>Every photo, one file</h1><p id="n">Counting\u2026</p><button id="go" disabled>Download the zip</button><div class="bar"><span id="b"></span></div><div class="st" id="st"></div></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/fflate/0.8.2/fflate.min.js"></script>
<script>
var API="https://meetlazo.com/api/w/${slug}/photos",list=[];
fetch(API).then(function(r){return r.json()}).then(function(j){list=(j&&j.photos)||[];document.getElementById("n").textContent=list.length?list.length+" photo"+(list.length===1?"":"s")+" on the wall. Stays on your device \u2014 nothing is uploaded.":"Nothing on the wall yet.";document.getElementById("go").disabled=!list.length;});
document.getElementById("go").onclick=async function(){
 var go=this,b=document.getElementById("b"),st=document.getElementById("st");go.disabled=true;
 var files={},done=0;
 for(var i=0;i<list.length;i++){
  var p=list[i];
  try{var r=await fetch(p.url);var buf=new Uint8Array(await r.arrayBuffer());var ext=(p.url.match(/\.(jpg|png|webp)$/)||[0,"jpg"])[1];
   var who=(p.name||"guest").replace(/[^A-Za-z0-9 _-]+/g,"").trim().replace(/\s+/g,"-").slice(0,40)||"guest";
   files[String(i+1).padStart(4,"0")+"-"+who+"."+ext]=[buf,{level:0}];}catch(e){}
  done++;b.style.width=Math.round(done/list.length*100)+"%";st.textContent="Fetched "+done+" of "+list.length;
 }
 st.textContent="Packing\u2026";
 var zip=fflate.zipSync(files);
 var blob=new Blob([zip],{type:"application/zip"}),a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download="${slug}-photos.zip";document.body.appendChild(a);a.click();
 st.textContent="Done \u2014 "+done+" photos in the zip.";go.disabled=false;
};
</script></body></html>`;
  return new Response(html, { headers: { "content-type": "text/html;charset=utf-8", "cache-control": "public, max-age=300", "x-robots-tag": "noindex" } });
}
