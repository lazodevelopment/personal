// JC-LAZO-WORKER-0929-AUTH-001: who is asking?
//
// The couple's dashboard signs its requests with the signed-in partner's
// Firebase ID token (Authorization: Bearer <token>). We verify it here with
// Google's published JWKs (RS256), then confirm the caller owns the site:
// weddingSites.coupleUid equals their uid, or users/{uid}.coupleUid does (a
// partner on the shared plan). Reads that need the couple's rights go to
// Firestore REST WITH that same token, so the security rules decide - the
// worker never holds a credential of its own.

const PROJECT = "lazo-513ec";
const JWKS = "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com";

const b64u = (s) => { s = s.replace(/-/g, "+").replace(/_/g, "/"); while (s.length % 4) s += "="; return Uint8Array.from(atob(s), c => c.charCodeAt(0)); };

async function jwks() {
  const key = new Request(JWKS);
  let r = await caches.default.match(key);
  if (!r) {
    r = await fetch(JWKS);
    if (!r.ok) return [];
    r = new Response(await r.text(), { headers: { "content-type": "application/json", "cache-control": "public, max-age=3600" } });
    try { await caches.default.put(key, r.clone()); } catch (e) {}
  }
  try { return (await r.json()).keys || []; } catch (e) { return []; }
}

// -> { uid, email, token } or null
export async function verifyIdToken(req) {
  const m = /^Bearer\s+([A-Za-z0-9_.-]+)$/.exec(req.headers.get("authorization") || "");
  if (!m) return null;
  const token = m[1];
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  let header, payload;
  try {
    header = JSON.parse(new TextDecoder().decode(b64u(parts[0])));
    payload = JSON.parse(new TextDecoder().decode(b64u(parts[1])));
  } catch (e) { return null; }
  if (header.alg !== "RS256" || !header.kid) return null;
  const now = Math.floor(Date.now() / 1000);
  if (payload.aud !== PROJECT || payload.iss !== `https://securetoken.google.com/${PROJECT}`) return null;
  if (!payload.sub || !(payload.exp > now) || !(payload.iat <= now + 300)) return null;
  const jwk = (await jwks()).find(k => k.kid === header.kid);
  if (!jwk) return null;
  try {
    const key = await crypto.subtle.importKey("jwk", jwk, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"]);
    const ok = await crypto.subtle.verify("RSASSA-PKCS1-v1_5", key, b64u(parts[2]), new TextEncoder().encode(parts[0] + "." + parts[1]));
    if (!ok) return null;
  } catch (e) { return null; }
  return { uid: payload.sub, email: payload.email || "", token };
}

export async function fsGetAs(token, path, mask) {
  const u = `https://firestore.googleapis.com/v1/projects/${PROJECT}/databases/(default)/documents/${path}`
    + (mask ? "?" + mask.map(f => "mask.fieldPaths=" + encodeURIComponent(f)).join("&") : "");
  const r = await fetch(u, { headers: { accept: "application/json", authorization: `Bearer ${token}` } });
  if (!r.ok) return null;
  return r.json();
}

export async function fsListAs(token, path, pageSize = 300) {
  const out = [];
  let pageToken = "";
  for (let i = 0; i < 10; i++) {
    const u = `https://firestore.googleapis.com/v1/projects/${PROJECT}/databases/(default)/documents/${path}?pageSize=${pageSize}`
      + (pageToken ? `&pageToken=${encodeURIComponent(pageToken)}` : "");
    const r = await fetch(u, { headers: { accept: "application/json", authorization: `Bearer ${token}` } });
    if (!r.ok) break;
    const j = await r.json();
    out.push(...(j.documents || []));
    if (!j.nextPageToken) break;
    pageToken = j.nextPageToken;
  }
  return out;
}

export async function fsPatchAs(token, path, fields, updateMask) {
  const u = `https://firestore.googleapis.com/v1/projects/${PROJECT}/databases/(default)/documents/${path}`
    + "?" + updateMask.map(f => "updateMask.fieldPaths=" + encodeURIComponent(f)).join("&");
  const r = await fetch(u, { method: "PATCH", headers: { "content-type": "application/json", authorization: `Bearer ${token}` }, body: JSON.stringify({ fields }) });
  return r.ok;
}

// Does this signed-in user own the site? (the doc is public; the users doc
// is read as them, so the rules answer)
export async function ownsSite(who, siteFields) {
  const coupleUid = siteFields && siteFields.coupleUid && (siteFields.coupleUid.stringValue || siteFields.coupleUid);
  if (!coupleUid) return false;
  if (coupleUid === who.uid) return true;
  const u = await fsGetAs(who.token, `users/${encodeURIComponent(who.uid)}`, ["coupleUid"]);
  const cu = u && u.fields && u.fields.coupleUid && u.fields.coupleUid.stringValue;
  return cu === coupleUid;
}
