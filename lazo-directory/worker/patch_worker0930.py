"""patch_worker0930.py - JC-LAZO-WORKER-0930-SITEFIX
Couple-site fixes from the 2026-09-30 audit, applied to worker/src/index.js.
  1. The passcode is checked on the server. A passcode site serves a gate page
     until the browser carries a cookie proving it knew the code; the payload
     shipped to the page never contains the passcode. (It used to sit in
     window.LAZO_SITE for anyone to read.) POST /w/{slug}/unlock sets the cookie.
  2. The canonical tag was written twice (once in og, once in seo).
  3. The template's own <meta name="description"> ("Peony is a ...") survived
     hydration, so every couple site carried two descriptions.
  4. Passcode pages are private, no-store (they vary by cookie).
Idempotent.  python worker\\patch_worker0930.py; cd worker; npx wrangler deploy
"""
from pathlib import Path

P = Path(__file__).resolve().parent / "src" / "index.js"
s = P.read_text(encoding="utf-8")
orig = s
TAG = "JC-LAZO-WORKER-0930-SITEFIX"


def rep(old, new, must=True):
    global s
    if new in s:
        return
    if old not in s:
        if must:
            raise SystemExit("anchor not found: " + old[:70])
        return
    s = s.replace(old, new, 1)


# --- 1. server-side passcode -------------------------------------------------
rep("async function renderCoupleSite(slug, env) {",
    f"""// {TAG}: the passcode gate lives here, not in the page.
async function pcToken(slug, code) {{
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(`lazo|${{slug}}|${{code}}`));
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("");
}}
function cookieVal(req, name) {{
  const m = (req && req.headers.get("cookie") || "").match(new RegExp("(?:^|;\\\\s*)" + name + "=([^;]*)"));
  return m ? decodeURIComponent(m[1]) : "";
}}
function gatePage(slug, names, wrong) {{
  const who = names ? esc(names) : "A private celebration";
  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex, nofollow"><title>${{who}} — enter the passcode</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600&family=Inter:wght@400;500&display=swap" rel="stylesheet">
<style>body{{margin:0;min-height:100vh;display:grid;place-items:center;background:#FBF7F0;color:#241E2B;font:15px/1.5 Inter,system-ui,sans-serif}}
.g{{width:min(92vw,360px);text-align:center;padding:36px 28px;background:#fff;border:1px solid #E6D6B8;border-radius:22px;box-shadow:0 30px 60px -40px rgba(36,30,43,.5)}}
.k{{letter-spacing:.18em;text-transform:uppercase;font-size:11px;color:#8A6A2F;font-weight:600;margin:0 0 8px}}
h1{{font:500 30px/1.15 "Cormorant Garamond",serif;margin:0 0 18px;color:#52284F}}
input{{font:inherit;padding:13px;width:100%;box-sizing:border-box;border:1px solid #E6D6B8;border-radius:10px;text-align:center;letter-spacing:.12em}}
button{{font:inherit;font-weight:600;margin-top:12px;width:100%;padding:13px;border:0;border-radius:999px;background:#52284F;color:#fff;cursor:pointer}}
p.e{{color:#B23B3B;margin:12px 0 0;font-size:14px}}p.h{{color:#7A6E85;margin:14px 0 0;font-size:13px}}</style></head>
<body><form class="g" method="post" action="/w/${{encodeURIComponent(slug)}}/unlock"><p class="k">A private celebration</p><h1>${{who}}</h1>
<input name="code" aria-label="Passcode" autocomplete="one-time-code" autofocus required><button type="submit">Open the site</button>
${{wrong ? '<p class="e">That passcode didn\\'t match. Try again?</p>' : ''}}<p class="h">The passcode is on your invitation.</p></form></body></html>`;
  return new Response(html, {{ status: wrong ? 403 : 401, headers: {{
    "content-type": TYPES.html, "cache-control": "private, no-store", "x-robots-tag": "noindex, nofollow" }} }});
}}
async function unlockRoute(slug, req) {{
  const f = await fsDoc("weddingSites", slug);
  const code = String(fsVal(f && f.passcode) || "").trim();
  let given = "";
  try {{ given = String((await req.formData()).get("code") || "").trim(); }} catch (e) {{ given = ""; }}
  const back = `/w/${{encodeURIComponent(slug)}}/`;
  if (!code || given !== code) return new Response(null, {{ status: 303, headers: {{ location: back + "?wrong=1", "cache-control": "no-store" }} }});
  const tok = await pcToken(slug, code);
  return new Response(null, {{ status: 303, headers: {{
    location: back, "cache-control": "no-store",
    "set-cookie": `lzw_${{slug}}=${{tok}}; Path=${{back}}; Max-Age=2592000; Secure; HttpOnly; SameSite=Lax` }} }});
}}

async function renderCoupleSite(slug, env, req) {{""")

rep("""  const priv = !!payload.passcode;
  let inject = `<script>window.LAZO_SITE=${JSON.stringify(payload)""",
    f"""  const priv = !!payload.passcode;
  // {TAG}: the browser only ever sees a passcode site after proving the code
  if (priv) {{
    const want = await pcToken(slug, String(payload.passcode).trim());
    if (cookieVal(req, "lzw_" + slug) !== want) {{
      const wrong = !!(req && new URL(req.url).searchParams.get("wrong"));
      return gatePage(slug, payload.names, wrong);
    }}
    payload.passcode = "";
    payload.locked = true;
  }}
  let inject = `<script>window.LAZO_SITE=${{JSON.stringify(payload)""")

# --- 2/3. one canonical, one description -------------------------------------
rep("""<meta name="description" content="${esc(desc)}">\\n<link rel="canonical" href="${pageUrl}">\\n`;""",
    """<meta name="description" content="${esc(desc)}">\\n`;""")
rep("""  html = html.replace(/<title>[^<]*<\\/title>/, `<title>${esc(title)}</title>`);""",
    f"""  html = html.replace(/<title>[^<]*<\\/title>/, `<title>${{esc(title)}}</title>`);
  // {TAG}: the template's own description describes the design, not the couple
  html = html.replace(/<meta name="description" content="[^"]*">\\n?/, "");""")

# --- 4. private pages are not cacheable ---------------------------------------
rep("""  if (priv) headers["x-robots-tag"] = "noindex, nofollow";
  return new Response(html, { headers });""",
    """  if (priv) { headers["x-robots-tag"] = "noindex, nofollow"; headers["cache-control"] = "private, no-store"; }
  return new Response(html, { headers });""")

# --- routes -------------------------------------------------------------------
rep("""    const wMatch = url.pathname.match(/^\\/w\\/([a-z0-9\\-]{1,80})\\/?$/);
    if (wMatch && req.method === "GET") {
      const resp = await renderCoupleSite(wMatch[1], env);""",
    f"""    // {TAG}
    const unMatch = url.pathname.match(/^\\/w\\/([a-z0-9\\-]{{1,80}})\\/unlock\\/?$/);
    if (unMatch && req.method === "POST") return unlockRoute(unMatch[1], req);
    const wMatch = url.pathname.match(/^\\/w\\/([a-z0-9\\-]{{1,80}})\\/?$/);
    if (wMatch && req.method === "GET") {{
      const resp = await renderCoupleSite(wMatch[1], env, req);""")

if s != orig:
    P.write_text(s, encoding="utf-8", newline="\n")
    print("patched worker/src/index.js")
else:
    print("already patched")
