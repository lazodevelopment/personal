// JARVIS hub: Sign-in: login and feed keys, signed browser sessions, Google sign-in and the lock page.
import { json, cookies } from "./core.js";

async function hmac(secret, msg) {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(msg));
  return btoa(String.fromCharCode(...new Uint8Array(sig))).replace(/=+$/, "").replace(/\+/g, "-").replace(/\//g, "_");
}
// Two keys (2026-10-16 audit): HUB_KEY is Jesse's login key (the lock page, or the x-hub-key header for full access);
// FEED_KEY is what the feeders, the executor, the Gmail bridges and the intake scripts carry. A feed key reaches only
// FEED_ROUTES, so a leaked script can post data but never send mail, confirm actions or read threads.
// Browser sessions are signed with SESSION_SECRET (never with a key), carry a version (KV sess_ver; /logout?all=1 bumps it).
export async function sameSecret(a, b) {
  if (!a || !b) return false;
  const enc = new TextEncoder(); const [x, y] = await Promise.all([crypto.subtle.digest("SHA-256", enc.encode(a)), crypto.subtle.digest("SHA-256", enc.encode(b))]);
  return crypto.subtle.timingSafeEqual(x, y);
}
export const sessSecret = (env) => env.SESSION_SECRET || null;
export async function makeSession(env, who) { const ver = (await env.HUB.get("sess_ver")) || "1"; const body = `${who}|${Date.now() + 30 * 86400e3}|${ver}`; return `${btoa(body)}.${await hmac(sessSecret(env), body)}`; }
async function readSession(env, token) {
  if (!token || !sessSecret(env)) return null;
  const [b, sig] = token.split(".");
  try { const body = atob(b); if (!(await sameSecret(await hmac(sessSecret(env), body), sig))) return null; const [who, exp, ver] = body.split("|"); if (Date.now() > +exp) return null; if ((ver || "") !== ((await env.HUB.get("sess_ver")) || "1")) return null; return who; } catch { return null; }
}
// routes a feed key may use (method + path); everything else needs Jesse's session or the login key
export const FEED_ROUTES = new Set(["GET /api/config", "GET /api/health", "GET /api/world/want", "GET /api/apps/targets", "GET /api/queue", "POST /api/queue/claim", "POST /api/queue/result", "GET /api/alarm/due", "GET /api/inbox/bridges",
  "POST /api/state", "POST /api/world/feed", "POST /api/world/globalfeed", "POST /api/world/camsfeed", "POST /api/world/placesfeed", "POST /api/world/shipsfeed", "POST /api/inbox", "POST /api/intake", "POST /api/social/posted"]);
export const FEED_STATE_KEYS = ["metrics", "traffic", "sports", "decisions", "watch", "brief"];   // the only /api/state keys a feeder may write
export async function authed(request, env) {
  if (!env.HUB_KEY) return env.DEV === "1" ? "dev" : null;   // fail closed: a missing secret locks the hub instead of opening it
  const hdr = request.headers.get("x-hub-key");
  if (hdr) { if (await sameSecret(hdr, env.HUB_KEY)) return "key"; if (await sameSecret(hdr, env.FEED_KEY)) return "feed"; return null; }
  return readSession(env, cookies(request).sess);
}
export const setCookie = (name, value, maxAge = 31536000) => `${name}=${value}; Path=/; Max-Age=${maxAge}; HttpOnly; Secure; SameSite=Lax`;

/* ---------------- Google sign-in ---------------- */
export async function googleLogin(request, env) {
  const { credential } = await request.json();
  if (!env.GOOGLE_CLIENT_ID) return json({ error: "Google sign-in isn't configured" }, 501);
  const r = await fetch("https://oauth2.googleapis.com/tokeninfo?id_token=" + encodeURIComponent(credential));
  if (!r.ok) return json({ error: "Invalid token" }, 401);
  const info = await r.json();
  const allowed = (env.ALLOWED_EMAILS || "jesse@briskhealth.com").toLowerCase().split(/[,\s]+/).filter(Boolean);
  if (info.aud !== env.GOOGLE_CLIENT_ID || info.email_verified !== "true" || !allowed.includes(String(info.email).toLowerCase())) return json({ error: "That Google account isn't on the list." }, 403);
  return json({ ok: true, email: info.email }, 200, { "set-cookie": setCookie("sess", await makeSession(env, info.email), 30 * 86400) });
}

export const ICON = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" rx="20" fill="#04070d"/><circle cx="50" cy="50" r="40" fill="none" stroke="#19d3ff" stroke-width="3" stroke-dasharray="40 30 10 60"/><circle cx="50" cy="50" r="27" fill="none" stroke="#7be8ff" stroke-width="2" stroke-dasharray="20 15 5 40"/><circle cx="50" cy="50" r="15" fill="#19d3ff" opacity=".8"/><circle cx="50" cy="50" r="6" fill="#fff"/></svg>`;

export function lockPage(env, msg = "") {
  const g = env.GOOGLE_CLIENT_ID ? `<script src="https://accounts.google.com/gsi/client" async defer></script>
<div id="g_id_onload" data-client_id="${env.GOOGLE_CLIENT_ID}" data-callback="onGoogle" data-auto_prompt="false"></div>
<div class="g_id_signin" data-type="standard" data-theme="filled_black" data-size="large" data-text="signin_with" data-shape="rectangular"></div><p class="or">or</p>
<script>async function onGoogle(r){const x=await fetch("/auth/google",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({credential:r.credential})});if(x.ok)location.href="/";else{const d=await x.json().catch(()=>({}));document.getElementById("msg").textContent=d.error||"Sign-in failed.";}}</script>` : "";
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>JARVIS</title><link rel="icon" href="/icon.svg"><link rel="manifest" href="/manifest.webmanifest">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600&family=Share+Tech+Mono&display=swap">
<style>html,body{height:100%;margin:0;background:#04070d;color:#9fd8ff;font:15px/1.5 Rajdhani,"Segoe UI",system-ui,sans-serif;display:grid;place-items:center}body{background:radial-gradient(800px 500px at 50% 30%,rgba(25,211,255,.12),transparent 60%),#04070d}
.box{display:grid;gap:14px;width:min(340px,90vw);text-align:center;justify-items:center}h1{font-weight:600;letter-spacing:.5em;margin:0;color:#fff;font-size:28px;text-shadow:0 0 18px rgba(25,211,255,.55)}form{display:grid;gap:10px;width:100%}
input{background:#070d18;border:1px solid #1e4a6a;color:#e6f6ff;padding:12px 14px;border-radius:2px;font:14px "Share Tech Mono",monospace;text-align:center;letter-spacing:.2em}button{background:#19d3ff;color:#04070d;border:0;padding:12px;border-radius:2px;font:600 14px Rajdhani,sans-serif;letter-spacing:.25em;cursor:pointer}
p{margin:0;opacity:.6;font-size:13px;font-family:"Share Tech Mono",monospace;letter-spacing:.1em}.or{opacity:.4}#msg{color:#ff4d5e;opacity:1;min-height:1em}</style></head>
<body><div class="box"><h1>JARVIS</h1><p>RESTRICTED ACCESS</p>${g}<form method="post" action="/auth"><input name="key" type="password" autocomplete="current-password" placeholder="access key"><button>UNLOCK</button></form><p id="msg">${msg}</p></div></body></html>`;
}
