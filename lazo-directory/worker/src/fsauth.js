// JC-LAZO-WORKER-0930-FSAUTH: the worker reads Firestore as a signed-in user.
//
// weddingSites/{slug} and its subcollections are no longer world-readable.
// The worker asks the workerToken function (functions-galleries) for a custom
// token, proving itself with WORKER_TOKEN_KEY, exchanges it at Identity Toolkit
// for an hour-long ID token (uid "lazo-worker", claim worker:true) and sends
// that as a Bearer on every Firestore read. The token is held in this isolate
// and in the edge cache so a page view costs no extra round trips.
//
// Needs (wrangler): vars FIREBASE_API_KEY, WORKER_TOKEN_URL; secret WORKER_TOKEN_KEY.
// Without them every read falls back to anonymous, exactly as before.

let ENV = null;
let memo = { token: "", exp: 0 };

export function setWorkerEnv(env) { ENV = env; }

async function mint() {
  if (!ENV || !ENV.WORKER_TOKEN_KEY || !ENV.WORKER_TOKEN_URL || !ENV.FIREBASE_API_KEY) return "";
  const c = await fetch(ENV.WORKER_TOKEN_URL, { headers: { "x-lazo-key": String(ENV.WORKER_TOKEN_KEY).trim() } });
  if (!c.ok) return "";
  const { token } = await c.json();
  if (!token) return "";
  const r = await fetch(`https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key=${ENV.FIREBASE_API_KEY}`, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ token, returnSecureToken: true }),
  });
  if (!r.ok) return "";
  const j = await r.json();
  return String(j.idToken || "");
}

export async function workerToken() {
  const now = Date.now();
  if (memo.token && memo.exp > now) return memo.token;
  const key = new Request("https://meetlazo.com/_internal/fsauth/token");
  try {
    const hit = await caches.default.match(key);
    if (hit) {
      const j = await hit.json();
      if (j.token && j.exp > now + 60e3) { memo = j; return j.token; }
    }
  } catch (e) {}
  const token = await mint();
  if (!token) return "";
  memo = { token, exp: now + 50 * 60e3 };
  try {
    await caches.default.put(key, new Response(JSON.stringify(memo), {
      headers: { "content-type": "application/json", "cache-control": "public, max-age=2700" } }));
  } catch (e) {}
  return token;
}

// Headers for a Firestore REST read: anonymous until the token is configured.
export async function fsHeaders() {
  const t = await workerToken();
  return t ? { accept: "application/json", authorization: `Bearer ${t}` } : { accept: "application/json" };
}

// ---- the passcode, checked at the edge ------------------------------------
export async function pcToken(slug, code) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(`lazo|${slug}|${code}`));
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("");
}
export function cookieVal(req, name) {
  const m = (req && req.headers.get("cookie") || "").match(new RegExp("(?:^|;\\s*)" + name + "=([^;]*)"));
  return m ? decodeURIComponent(m[1]) : "";
}
// The site's passcode (trimmed, "" when public), held 30 s at the edge.
export async function siteCode(slug) {
  const key = new Request(`https://meetlazo.com/_internal/fsauth/code/${slug}`);
  try { const hit = await caches.default.match(key); if (hit) return (await hit.json()).code || ""; } catch (e) {}
  const u = `https://firestore.googleapis.com/v1/projects/lazo-513ec/databases/(default)/documents/weddingSites/${encodeURIComponent(slug)}?mask.fieldPaths=passcode`;
  const r = await fetch(u, { headers: await fsHeaders() });
  if (!r.ok) return "";
  const j = await r.json();
  const code = String((j.fields && j.fields.passcode && j.fields.passcode.stringValue) || "").trim();
  try { await caches.default.put(key, new Response(JSON.stringify({ code }), { headers: { "content-type": "application/json", "cache-control": "public, max-age=30" } })); } catch (e) {}
  return code;
}
// true when the site has a passcode and this request has not proven it
export async function siteLocked(slug, req, code) {
  if (code === undefined) code = await siteCode(slug);
  if (!code) return false;
  return cookieVal(req, "lzw_" + slug) !== await pcToken(slug, code);
}
export const lockedResponse = () => new Response(JSON.stringify({ ok: false, error: "locked" }), {
  status: 401, headers: { "content-type": "application/json", "cache-control": "no-store", "access-control-allow-origin": "*" } });
