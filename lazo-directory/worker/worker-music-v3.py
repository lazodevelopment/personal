# JC-LAZO-WORKER-0912-MUSIC-003
# Run from C:\Users\kurvh\lazo-directory\worker:   python worker-music-v3.py
# Patches src/index.js (backup at src/index.js.bak3):
#   /music/search       now carries an explicit flag per song (Deezer + iTunes)
#   /music/preview?u=   relays a Deezer/Apple preview clip with CORS so the
#                       widget's Web Audio equalizer can read the signal
#   /w/{slug}/requests  guest-facing "Request a song" page for a couple's site
#   /api/song-request   POST -> couples/{cid}/musicRequests (Firestore REST,
#                       rules allow a validated public create)
import io, sys, shutil

p = "src/index.js"
s = io.open(p, encoding="utf-8").read()
if "MUSIC-003" in s:
    sys.exit("already patched")
if "async function musicSearch(url)" not in s:
    sys.exit("musicSearch not found - run the 002 patch first")

# 1. explicit flag in search results
old = 'previewUrl: t.preview || "", trackTimeMillis: (t.duration || 0) * 1000, trackViewUrl: t.link || "" }));'
new = 'previewUrl: t.preview || "", trackTimeMillis: (t.duration || 0) * 1000, trackViewUrl: t.link || "", explicit: !!t.explicit_lyrics }));'
if old not in s:
    sys.exit("deezer map line not found")
s = s.replace(old, new, 1)
old = 'if (a.ok) { const j = await a.json(); if (Array.isArray(j.results)) results = j.results; }'
new = 'if (a.ok) { const j = await a.json(); if (Array.isArray(j.results)) results = j.results.map(r => ({ ...r, explicit: r.trackExplicitness === "explicit" })); }'
if old not in s:
    sys.exit("itunes map line not found")
s = s.replace(old, new, 1)

# 2. routes, ahead of the search route
anchor = '    if (url.pathname === "/music/search") return musicSearch(url);'
if anchor not in s:
    sys.exit("search route line not found")
routes = '''    if (url.pathname === "/music/preview") return musicPreview(url, req);
    if (url.pathname === "/api/song-request" && req.method === "OPTIONS") return new Response(null, { headers: CORS });
    if (url.pathname === "/api/song-request" && req.method === "POST") return songRequest(req);
    const rqMatch = url.pathname.match(/^\\/w\\/([a-z0-9-]{1,80})\\/requests\\/?$/);
    if (rqMatch) return requestPage(rqMatch[1]);
'''
s = s.replace(anchor, routes + anchor, 1)

fn = r'''
// JC-LAZO-WORKER-0912-MUSIC-003: preview relay, guest song requests.
const PREVIEW_HOSTS = [/\.dzcdn\.net$/i, /\.apple\.com$/i, /\.mzstatic\.com$/i];
async function musicPreview(url, req) {
  const u = url.searchParams.get("u") || "";
  let target;
  try { target = new URL(u); } catch (e) { return new Response("bad url", { status: 400 }); }
  if (target.protocol !== "https:" || !PREVIEW_HOSTS.some(rx => rx.test(target.hostname))) {
    return new Response("host not allowed", { status: 403 });
  }
  const h = { "access-control-allow-origin": "*", "access-control-expose-headers": "content-length, content-range, accept-ranges", "cache-control": "public, max-age=604800" };
  const range = req.headers.get("range");
  const up = await fetch(target.toString(), { headers: range ? { range } : {}, cf: { cacheEverything: true, cacheTtl: 604800 } });
  if (!up.ok && up.status !== 206) return new Response("upstream " + up.status, { status: 502, headers: h });
  const out = new Headers(h);
  for (const k of ["content-type", "content-length", "content-range", "accept-ranges"]) {
    const v = up.headers.get(k); if (v) out.set(k, v);
  }
  return new Response(up.body, { status: up.status, headers: out });
}

function esc(x) { return String(x || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }

async function requestPage(slug) {
  const site = await fsDoc("weddingSites", slug);
  if (!site) return new Response("Not found", { status: 404 });
  const names = site.names || site.coupleNames || "the couple";
  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>Request a song - ${esc(names)}</title>
<style>
body{margin:0;background:#FAF6F0;color:#241E2B;font-family:Helvetica,Arial,sans-serif}
.wrap{max-width:460px;margin:0 auto;padding:36px 20px 60px}
h1{font-family:Georgia,serif;font-weight:600;font-size:34px;color:#52284F;margin:0 0 6px;line-height:1.05}
p{color:#6B5F72;font-size:14px;line-height:1.5;margin:0 0 22px}
label{display:block;font-size:11px;letter-spacing:1.5px;text-transform:uppercase;color:#52284F;font-weight:700;margin:14px 0 6px}
input,textarea{width:100%;box-sizing:border-box;border:1px solid #E6D6B8;border-radius:12px;padding:12px 13px;font-size:15px;background:#FFFDF9;color:#241E2B;font-family:inherit}
input:focus,textarea:focus{outline:none;border-color:#D9B77C;box-shadow:0 0 0 3px rgba(217,183,124,.25)}
textarea{min-height:70px;resize:vertical}
button{margin-top:20px;width:100%;border:0;border-radius:12px;padding:14px;background:#52284F;color:#FAF6F0;font-size:15px;font-weight:700;cursor:pointer}
button:disabled{opacity:.6}
.ok{display:none;text-align:center;padding:30px 0}
.ok h2{font-family:Georgia,serif;color:#52284F;font-weight:600;font-size:28px;margin:0 0 8px}
.err{color:#B04343;font-size:13px;margin-top:10px;display:none}
.hp{position:absolute;left:-9999px}
.foot{margin-top:34px;text-align:center;font-size:11px;color:#6B5F72}.foot a{color:#52284F}
</style></head><body><div class="wrap">
<div id="form"><h1>Request a song</h1><p>What gets you on the dance floor? ${esc(names)} will pass the good ones to the DJ.</p>
<label>Your name</label><input id="guest" maxlength="80" placeholder="Aunt May">
<label>Song</label><input id="song" maxlength="200" placeholder="September" required>
<label>Artist</label><input id="artist" maxlength="120" placeholder="Earth, Wind &amp; Fire">
<label>Why this one? (optional)</label><textarea id="note" maxlength="300" placeholder="It was playing when we met them."></textarea>
<input class="hp" id="website" tabindex="-1" autocomplete="off">
<button id="go">Send the request</button><div class="err" id="err"></div></div>
<div class="ok" id="ok"><h2>Sent!</h2><p>Want to request another? <a href="#" id="again" style="color:#52284F">Add one more</a></p></div>
<div class="foot">Planned on <a href="https://meetlazo.com">Lazo</a></div></div>
<script>
const $=id=>document.getElementById(id);
$("go").onclick=async()=>{const song=$("song").value.trim();if(!song){$("err").style.display="block";$("err").textContent="Which song?";return}
$("go").disabled=true;$("err").style.display="none";
try{const r=await fetch("/api/song-request",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({slug:${JSON.stringify(slug)},guest:$("guest").value.trim(),song,artist:$("artist").value.trim(),note:$("note").value.trim(),website:$("website").value})});
if(!r.ok)throw new Error("x");$("form").style.display="none";$("ok").style.display="block";}
catch(e){$("err").style.display="block";$("err").textContent="That didn't go through - try again in a moment.";$("go").disabled=false}};
$("again").onclick=e=>{e.preventDefault();$("song").value="";$("artist").value="";$("note").value="";$("ok").style.display="none";$("form").style.display="block";$("go").disabled=false};
</script></body></html>`;
  return new Response(html, { headers: { "content-type": TYPES.html, "cache-control": "public, max-age=300" } });
}

async function songRequest(req) {
  let b;
  try { b = await req.json(); } catch (e) { return json({ ok: false }, 400); }
  if (b.website) return json({ ok: true }); // honeypot: pretend
  const slug = String(b.slug || "").toLowerCase();
  if (!/^[a-z0-9-]{1,80}$/.test(slug)) return json({ ok: false }, 400);
  const song = String(b.song || "").trim().slice(0, 200);
  if (!song) return json({ ok: false, error: "song" }, 400);
  const site = await fsDoc("weddingSites", slug);
  const cid = site && (site.coupleUid || site.ownerUid);
  if (!cid) return json({ ok: false }, 404);
  const fields = {
    guest: { stringValue: String(b.guest || "").trim().slice(0, 80) },
    song: { stringValue: song },
    artist: { stringValue: String(b.artist || "").trim().slice(0, 120) },
    note: { stringValue: String(b.note || "").trim().slice(0, 300) },
    status: { stringValue: "new" },
    source: { stringValue: "site" },
    createdAt: { timestampValue: new Date().toISOString() },
  };
  const r = await fetch(`https://firestore.googleapis.com/v1/projects/${PROJECT}/databases/(default)/documents/couples/${encodeURIComponent(cid)}/musicRequests`, {
    method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ fields }),
  });
  if (!r.ok) return json({ ok: false, upstream: r.status }, 502);
  return json({ ok: true });
}
'''
shutil.copy(p, p + ".bak3")
io.open(p, "w", encoding="utf-8", newline="\n").write(s.rstrip() + "\n" + fn)
print("patched", p, "- now: npx wrangler deploy")
