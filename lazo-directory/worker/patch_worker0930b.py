"""patch_worker0930b.py - JC-LAZO-WORKER-0930-FSAUTH
The worker reads Firestore as "lazo-worker" (src/fsauth.js) so weddingSites can
stop being world-readable, guest-facing reads move behind /api/w/{slug}/...,
and every guest route honours the passcode cookie. Idempotent.
  python worker\\patch_worker0930b.py; cd worker; npx wrangler deploy
"""
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"
TAG = "JC-LAZO-WORKER-0930-FSAUTH"


def patch(name, pairs):
    p = SRC / name
    s = p.read_text(encoding="utf-8")
    orig = s
    for old, new in pairs:
        if new in s:
            continue
        if old not in s:
            raise SystemExit(f"{name}: anchor not found: {old[:70]!r}")
        s = s.replace(old, new, 1)
    if s != orig:
        p.write_text(s, encoding="utf-8", newline="\n")
        print("patched", name)
    else:
        print("already", name)


# ---------------------------------------------------------------- index.js
patch("index.js", [
    ('import { weatherRoute, translateRoute, cardsPage, playlistPage, dayBeforeRoute } from "./sitefeatures.js";',
     'import { weatherRoute, translateRoute, cardsPage, playlistPage, dayBeforeRoute } from "./sitefeatures.js";\n'
     f'// {TAG}\nimport {{ setWorkerEnv, fsHeaders, pcToken, cookieVal, siteLocked, lockedResponse }} from "./fsauth.js";'),
    # every anonymous read carries the worker's token
    ('  const r = await fetch(docUrl, { headers: { accept: "application/json" } });',
     '  const r = await fetch(docUrl, { headers: await fsHeaders() });'),
    ('      const rr = await fetch(u, { headers: { accept: "application/json" } });',
     '      const rr = await fetch(u, { headers: await fsHeaders() });'),
    # the local copies of the two helpers give way to the shared module
    ('''// JC-LAZO-WORKER-0930-SITEFIX: the passcode gate lives here, not in the page.
async function pcToken(slug, code) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(`lazo|${slug}|${code}`));
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("");
}
function cookieVal(req, name) {
  const m = (req && req.headers.get("cookie") || "").match(new RegExp("(?:^|;\\\\s*)" + name + "=([^;]*)"));
  return m ? decodeURIComponent(m[1]) : "";
}
''', '// JC-LAZO-WORKER-0930-SITEFIX: the passcode gate lives here, not in the page (helpers in fsauth.js).\n'),
    # guest-facing data reads, filtered and gated
    ('async function renderCoupleSite(slug, env, req) {',
     f'''// {TAG}: what the page reads after it loads - the guestbook, chapters, the
// seat finder (only the matches, never the list), the room map (tables, no
// names) and a personal invite. Each honours the passcode cookie.
async function siteDataRoute(slug, what, url, req) {{
  const f = await fsDoc("weddingSites", slug);
  if (!f) return json({{ ok: false, error: "not_found" }}, 404);
  const code = String(fsVal(f.passcode) || "").trim();
  if (await siteLocked(slug, req, code)) return lockedResponse();
  const h = {{ "content-type": "application/json", "access-control-allow-origin": "*",
    "cache-control": code ? "private, no-store" : "public, max-age=0, s-maxage=20" }};
  const base = `https://firestore.googleapis.com/v1/projects/${{PROJECT}}/databases/(default)/documents/weddingSites/${{encodeURIComponent(slug)}}`;
  const pick = (fields, keep) => {{ const o = {{}}; for (const k of keep) if (fields && fields[k]) o[k] = fields[k]; return o; }};
  const listOf = async (sub, n, keep) => {{
    const r = await fetch(`${{base}}/${{sub}}?pageSize=${{n}}`, {{ headers: await fsHeaders() }});
    if (!r.ok) return {{ documents: [] }};
    const j = await r.json();
    return {{ documents: (j.documents || []).map(d => ({{ name: d.name, fields: pick(d.fields, keep) }})) }};
  }};
  if (what === "guestbook") return new Response(JSON.stringify(await listOf("guestbook", 60, ["name", "message", "createdAt"])), {{ headers: h }});
  if (what === "chapters") return new Response(JSON.stringify(await listOf("chapters", 40, ["title", "text", "dateIso", "photos"])), {{ headers: h }});
  if (what.startsWith("invite/")) {{
    const r = await fetch(`${{base}}/invites/${{encodeURIComponent(what.slice(7))}}`, {{ headers: await fsHeaders() }});
    if (!r.ok) return json({{ ok: false, error: "not_found" }}, 404);
    const d = await r.json();
    return new Response(JSON.stringify({{ fields: pick(d.fields, ["name", "party", "plusOnes", "meals"]) }}), {{ headers: {{ ...h, "cache-control": "private, no-store" }} }});
  }}
  // seating/main, held 30 s so the finder's keystrokes don't each cost a read
  const key = new Request(`https://meetlazo.com/_internal/seating/${{slug}}`);
  let sd = null;
  try {{ const hit = await caches.default.match(key); if (hit) sd = await hit.json(); }} catch (e) {{}}
  if (!sd) {{
    const r = await fetch(`${{base}}/seating/main`, {{ headers: await fsHeaders() }});
    sd = r.ok ? ((await r.json()).fields || {{}}) : {{}};
    try {{ await caches.default.put(key, new Response(JSON.stringify(sd), {{ headers: {{ "content-type": "application/json", "cache-control": "public, max-age=30" }} }})); }} catch (e) {{}}
  }}
  if (what === "room") return new Response(JSON.stringify({{ fields: pick(sd, ["tables", "canvas"]) }}), {{ headers: h }});
  // seat: the same matching the page used to do on the whole list
  const norm = (x) => String(x || "").toLowerCase().replace(/[^a-z0-9 ]+/g, " ").replace(/\\s+/g, " ").trim();
  const q = norm(url.searchParams.get("q"));
  if (q.length < 2) return new Response(JSON.stringify({{ fields: {{ guests: {{ arrayValue: {{ values: [] }} }} }} }}), {{ headers: {{ ...h, "cache-control": "no-store" }} }});
  const words = q.split(" ");
  const vals = ((sd.guests && sd.guests.arrayValue && sd.guests.arrayValue.values) || []);
  const str = (v, k) => norm(v.mapValue && v.mapValue.fields && v.mapValue.fields[k] && v.mapValue.fields[k].stringValue);
  const hits = vals.filter(v => {{ const n = str(v, "n"), p = str(v, "p");
    return words.every(w => n.includes(w)) || (p && words.every(w => p.includes(w))); }}).slice(0, 6);
  return new Response(JSON.stringify({{ fields: {{ guests: {{ arrayValue: {{ values: hits }} }} }} }}), {{ headers: {{ ...h, "cache-control": "no-store" }} }});
}}

async function renderCoupleSite(slug, env, req) {{'''),
    ('  async fetch(req, env) {\n    const url = new URL(req.url);',
     f'  async fetch(req, env) {{\n    const url = new URL(req.url);\n    setWorkerEnv(env);  // {TAG}'),
    # the routes: data reads, and the passcode on cards + playlist
    ('    const cardsMatch = url.pathname.match(/^\\/w\\/([a-z0-9-]{1,80})\\/cards\\/?$/);\n    if (cardsMatch && req.method === "GET") return cardsPage(cardsMatch[1]);\n'
     '    const plMatch = url.pathname.match(/^\\/w\\/([a-z0-9-]{1,80})\\/playlist\\/?$/);\n    if (plMatch && req.method === "GET") return playlistPage(plMatch[1]);',
     f'    // {TAG}\n'
     '    const gdMatch = url.pathname.match(/^\\/api\\/w\\/([a-z0-9-]{1,80})\\/(guestbook|chapters|seat|room|invite\\/[A-Za-z0-9_-]{4,120})\\/?$/);\n'
     '    if (gdMatch && req.method === "GET") return siteDataRoute(gdMatch[1], gdMatch[2], url, req);\n'
     '    const cardsMatch = url.pathname.match(/^\\/w\\/([a-z0-9-]{1,80})\\/cards\\/?$/);\n'
     '    if (cardsMatch && req.method === "GET") return (await siteLocked(cardsMatch[1], req)) ? lockedResponse() : cardsPage(cardsMatch[1]);\n'
     '    const plMatch = url.pathname.match(/^\\/w\\/([a-z0-9-]{1,80})\\/playlist\\/?$/);\n'
     '    if (plMatch && req.method === "GET") return (await siteLocked(plMatch[1], req)) ? lockedResponse() : playlistPage(plMatch[1]);'),
])

# ---------------------------------------------------------- sitefeatures.js
patch("sitefeatures.js", [
    ('import { verifyIdToken, ownsSite, fsListAs, fsPatchAs } from "./auth.js";',
     f'import {{ verifyIdToken, ownsSite, fsListAs, fsPatchAs }} from "./auth.js";\nimport {{ fsHeaders }} from "./fsauth.js";  // {TAG}'),
    ('  const r = await fetch(`https://firestore.googleapis.com/v1/projects/${PROJECT}/databases/(default)/documents/${path}`,\n    { headers: { accept: "application/json" } });',
     '  const r = await fetch(`https://firestore.googleapis.com/v1/projects/${PROJECT}/databases/(default)/documents/${path}`,\n    { headers: await fsHeaders() });'),
])

# ----------------------------------------------------------- guestphotos.js
patch("guestphotos.js", [
    ('import { verifyIdToken, ownsSite } from "./auth.js";',
     f'import {{ verifyIdToken, ownsSite }} from "./auth.js";\nimport {{ fsHeaders, siteLocked, lockedResponse }} from "./fsauth.js";  // {TAG}'),
    ('  const r = await fetch(u, { headers: { accept: "application/json" } });\n  if (!r.ok) return null;\n  const doc = await r.json();\n  const f = doc.fields || {};\n  const out = {',
     '  const r = await fetch(u, { headers: await fsHeaders() });\n  if (!r.ok) return null;\n  const doc = await r.json();\n  const f = doc.fields || {};\n  const out = {\n    passcode: String(fsVal(f.passcode) || "").trim(),'),
    ('export async function guestPhotosRoute(url, req, env) {\n  if (!env.GALLERIES) return null;',
     f'''export async function guestPhotosRoute(url, req, env) {{
  if (!env.GALLERIES) return null;
  // {TAG}: a passcode site's photos need the passcode cookie (approve is the couple's own, token-checked)
  const any = url.pathname.match(/^\\/(?:api\\/)?w\\/([a-z0-9-]{{1,80}})\\/photo/);
  if (any && req.method !== "OPTIONS" && !/\\/photos\\/approve\\/?$/.test(url.pathname)) {{
    const site = await siteDoc(any[1]);
    if (site && site.passcode && await siteLocked(any[1], req, site.passcode)) return lockedResponse();
  }}'''),
])
print("done")
