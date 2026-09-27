# JC-LAZO-WORKER-0913-RESTORE-001
# Run from C:\Users\kurvh\lazo-directory\worker:   python worker-restore-v1.py
# Then:  npx wrangler deploy
#
# Rebuilds src/index.js from the GALLERY-0912-006 file that is live now
# (22,702 bytes, no music routes) by re-applying, in order:
#   MUSIC-002  /music/search (Deezer first, iTunes second) - lifted from index.js.bak3
#   MUSIC-003  explicit flags, /music/preview relay, /w/{slug}/requests page,
#              POST /api/song-request   (its `function esc` renamed escM - the
#              file already has `const esc`, and a second declaration is a
#              SyntaxError that would have broken the whole worker)
#   PAY-001    /f/{inquiry}?t=  the couple's login-free booking page
# Backup at src/index.js.bak-restore1. Refuses to run on a file that is not
# gallery-006, or that already has any of the three markers.
import io, sys, shutil

p = "src/index.js"
s = io.open(p, encoding="utf-8").read()
if "GALLERY-0912-006" not in s:
    sys.exit("this is not the gallery-006 file - stop")
for m in ("MUSIC-002", "MUSIC-003", "PAY-001"):
    if m in s:
        sys.exit(m + " already present - stop")

def need(anchor, what):
    if anchor not in s:
        sys.exit(what + " anchor not found")

# ---- MUSIC-002 ----------------------------------------------------------
a002 = '    // STORE ICONS: /icon/{host}'
need(a002, "MUSIC-002 route")
s = s.replace(a002, '''    // MUSIC SEARCH: /music/search?q= -> Deezer/iTunes, cached a day, with CORS (JC-LAZO-WORKER-0912-MUSIC-001)
    if (url.pathname === "/music/search") return musicSearch(url);

''' + a002, 1)
fn002 = r'''
// JC-LAZO-WORKER-0912-MUSIC-002: song search for the couple app's Music page.
// Deezer first (shared-IP friendly, 30s MP3 previews), iTunes second (429s from
// Workers' shared egress). Both are reshaped to the iTunes field names the
// widget reads, so the app never knows which one answered.
async function musicSearch(url) {
  const q = (url.searchParams.get("q") || "").trim().slice(0, 120);
  const h = { "content-type": "application/json; charset=utf-8", "access-control-allow-origin": "*", "cache-control": "public, max-age=86400" };
  if (q.length < 2) return new Response('{"results":[]}', { headers: h });
  const cache = caches.default;
  const key = new Request("https://meetlazo.com/music/search?q=" + encodeURIComponent(q.toLowerCase()), { method: "GET" });
  const hit = await cache.match(key);
  if (hit) return hit;
  const ua = { accept: "application/json", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36" };
  let results = null, upstream = 0;
  try {
    const d = await fetch("https://api.deezer.com/search?q=" + encodeURIComponent(q) + "&limit=25", { headers: ua });
    upstream = d.status;
    if (d.ok) {
      const j = await d.json();
      if (Array.isArray(j.data)) results = j.data.map(t => ({
        trackId: "dz" + t.id, trackName: t.title, artistName: t.artist && t.artist.name || "",
        collectionName: t.album && t.album.title || "", artworkUrl100: t.album && (t.album.cover_medium || t.album.cover) || "",
        previewUrl: t.preview || "", trackTimeMillis: (t.duration || 0) * 1000, trackViewUrl: t.link || "" }));
    }
  } catch (e) {}
  if (!results || !results.length) {
    try {
      const a = await fetch("https://itunes.apple.com/search?term=" + encodeURIComponent(q) + "&entity=song&limit=25&country=US", { headers: ua, redirect: "follow" });
      upstream = a.status;
      if (a.ok) { const j = await a.json(); if (Array.isArray(j.results)) results = j.results; }
    } catch (e) {}
  }
  if (!results) return new Response(JSON.stringify({ results: [], upstream }), { status: 502, headers: { ...h, "cache-control": "no-store" } });
  const res = new Response(JSON.stringify({ results }), { headers: h });
  await cache.put(key, res.clone());
  return res;
}'''

# ---- MUSIC-003 ----------------------------------------------------------
old = 'previewUrl: t.preview || "", trackTimeMillis: (t.duration || 0) * 1000, trackViewUrl: t.link || "" }));'
new = 'previewUrl: t.preview || "", trackTimeMillis: (t.duration || 0) * 1000, trackViewUrl: t.link || "", explicit: !!t.explicit_lyrics }));'
if old not in fn002: sys.exit("deezer map line not found")
fn002 = fn002.replace(old, new, 1)
old = 'if (a.ok) { const j = await a.json(); if (Array.isArray(j.results)) results = j.results; }'
new = 'if (a.ok) { const j = await a.json(); if (Array.isArray(j.results)) results = j.results.map(r => ({ ...r, explicit: r.trackExplicitness === "explicit" })); }'
if old not in fn002: sys.exit("itunes map line not found")
fn002 = fn002.replace(old, new, 1)
anchor = '    if (url.pathname === "/music/search") return musicSearch(url);'
routes003 = '''    if (url.pathname === "/music/preview") return musicPreview(url, req);
    if (url.pathname === "/api/song-request" && req.method === "OPTIONS") return new Response(null, { headers: CORS });
    if (url.pathname === "/api/song-request" && req.method === "POST") return songRequest(req);
    const rqMatch = url.pathname.match(/^\\/w\\/([a-z0-9-]{1,80})\\/requests\\/?$/);
    if (rqMatch) return requestPage(rqMatch[1]);
'''
s = s.replace(anchor, routes003 + anchor, 1)
fn003 = r'''
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

function escM(x) { return String(x || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }

async function requestPage(slug) {
  const site = await fsDoc("weddingSites", slug);
  if (!site) return new Response("Not found", { status: 404 });
  const names = site.names || site.coupleNames || "the couple";
  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>Request a song - ${escM(names)}</title>
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
<div id="form"><h1>Request a song</h1><p>What gets you on the dance floor? ${escM(names)} will pass the good ones to the DJ.</p>
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

# ---- PAY-001 ------------------------------------------------------------
aw = '    const wMatch = url.pathname.match(/^\\/w\\/([a-z0-9\\-]{1,80})\\/?$/);'
need(aw, "/w/ route")
routep = '''    // JC-LAZO-WORKER-0913-PAY-001: the couple's booking page, no login
    const fMatch = url.pathname.match(/^\\/f\\/([A-Za-z0-9_-]{6,80})\\/?$/);
    if (fMatch && req.method === "GET") return bookingPage(fMatch[1], url.searchParams.get("t") || "");
'''
s = s.replace(aw, routep + aw, 1)
fnp = r'''
// JC-LAZO-WORKER-0913-PAY-001 ---------------------------------------------
const FILE_VIEW = "https://us-central1-lazo-513ec.cloudfunctions.net/fileView";
const PAY_CHECKOUT = "https://us-central1-lazo-513ec.cloudfunctions.net/payCheckout";
const escF = (t) => String(t == null ? "" : t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const moneyF = (n) => "$" + (Math.round((Number(n) || 0) * 100) / 100).toLocaleString("en-US", { maximumFractionDigits: 2 });
const dateF = (iso) => { if (!iso) return ""; const d = new Date(iso); return isNaN(d) ? "" : d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }); };

async function bookingPage(inquiryId, token) {
  const noindex = { "content-type": TYPES.html, "cache-control": "no-store", "x-robots-tag": "noindex" };
  if (!token) return new Response(shell("This link is missing its key", "<p>Ask your vendor to resend the booking link from Lazo.</p>"), { status: 400, headers: noindex });
  let r;
  try { r = await fetch(`${FILE_VIEW}?inquiry=${encodeURIComponent(inquiryId)}&t=${encodeURIComponent(token)}`, { headers: { accept: "application/json" } }); }
  catch (e) { return new Response(shell("Lazo is catching its breath", "<p>Try again in a minute.</p>"), { status: 502, headers: noindex }); }
  if (r.status === 403) return new Response(shell("This link has expired", "<p>Your vendor may have sent a newer one - check your messages, or ask them to resend it.</p>"), { status: 403, headers: noindex });
  if (!r.ok) return new Response(shell("Booking not found", "<p>Ask your vendor to resend the booking link from Lazo.</p>"), { status: 404, headers: noindex });
  const d = await r.json();
  const v = d.vendor || {}, c = d.couple || {};
  const primary = /^#[0-9a-f]{6}$/i.test(v.primary || "") ? v.primary : "#52284F";
  const accent = /^#[0-9a-f]{6}$/i.test(v.accent || "") ? v.accent : "#D9B77C";
  const invoices = Array.isArray(d.invoices) ? d.invoices : [];
  const open = invoices.filter((i) => i.status === "sent");
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const plan = d.paymentPlan;

  const proposal = d.proposal ? `
  <section class="card">
    <div class="eyebrow">Your proposal</div>
    <h2>${escF(d.proposal.title || "Proposal")}</h2>
    <div class="big">${moneyF(d.proposal.price)}</div>
    ${Array.isArray(d.proposal.includes) && d.proposal.includes.length ? `<ul class="inc">${d.proposal.includes.map((x) => `<li>${escF(typeof x === "string" ? x : (x && x.label) || "")}</li>`).join("")}</ul>` : ""}
    ${d.proposal.note ? `<p class="note">${escF(d.proposal.note)}</p>` : ""}
    <div class="pill ${d.proposal.status === "accepted" ? "ok" : ""}">${d.proposal.status === "accepted" ? "Accepted" : d.proposal.status === "declined" ? "Declined" : "Awaiting your answer - reply in Lazo"}</div>
  </section>` : "";

  const contract = d.contract ? `
  <section class="card">
    <div class="eyebrow">Agreement</div>
    <h2>${escF(d.contract.title)}</h2>
    ${d.contract.status === "signed"
      ? `<div class="pill ok">Signed ${escF(dateF(d.contract.signedAt))}</div>`
      : `<p class="note">Your agreement is ready to sign. Signing happens inside Lazo so it's stored with your booking.</p><a class="btn ghost" href="https://app.meetlazo.com/dashboard?thread=${escF(inquiryId)}">Review &amp; sign in Lazo</a>`}
  </section>` : "";

  const invRows = invoices.map((i) => {
    const due = i.dueDate ? new Date(i.dueDate) : null;
    const late = i.status === "sent" && due && due < today;
    const idx = i.installmentCount ? ` <span class="muted">${(i.installmentIndex || 0) + 1} of ${i.installmentCount}</span>` : "";
    const when = i.status === "paid" ? `Paid ${dateF(i.paidAt)}` : due ? `${late ? "Was due" : "Due"} ${dateF(i.dueDate)}` : "Due on receipt";
    const pay = i.status === "sent" ? `
      <form class="pay" data-inv="${escF(i.id)}" data-tip="${i.tipAllowed ? "1" : "0"}">
        ${i.tipAllowed ? `<label class="tip">Add a tip <span class="muted">(optional)</span><input name="tip" type="number" min="0" step="1" placeholder="0"></label>` : ""}
        <button class="btn" type="submit">Pay ${moneyF(i.total)}</button>
      </form>` : "";
    return `<div class="inv ${i.status} ${late ? "late" : ""}">
      <div class="inv-l"><div class="inv-t">${escF(i.title)}${idx}</div><div class="inv-w">${when}</div>
        ${Array.isArray(i.lineItems) && i.lineItems.length > 1 ? `<div class="lines">${i.lineItems.map((l) => `<span>${escF(l.label)} - ${moneyF(l.amount)}</span>`).join("")}</div>` : ""}</div>
      <div class="inv-r"><div class="inv-a">${moneyF(i.total)}</div>${i.status === "paid" ? `<div class="pill ok small">Paid</div>` : i.status === "refunded" ? `<div class="pill small">Refunded</div>` : ""}</div>
      ${pay}
    </div>`;
  }).join("");

  const links = (Array.isArray(d.paymentLinks) ? d.paymentLinks : []).filter((l) => l && l.url).map((l) => `<a class="btn ghost small" href="${escF(l.url)}" target="_blank" rel="noopener">${escF(l.label || "Pay")}</a>`).join("");

  const money = `
  <section class="card">
    <div class="eyebrow">Payments</div>
    ${plan && plan.total ? `<div class="prog"><div class="bar"><span style="width:${Math.min(100, Math.round(((plan.paid || 0) / plan.total) * 100))}%"></span></div><div class="prog-t">${moneyF(plan.paid || 0)} of ${moneyF(plan.total)} paid${plan.nextDue ? ` · next ${dateF(plan.nextDue._seconds ? new Date(plan.nextDue._seconds * 1000).toISOString() : plan.nextDue)}` : ""}</div></div>` : ""}
    ${invoices.length ? invRows : `<p class="note">Nothing to pay yet.</p>`}
    ${links ? `<div class="links"><div class="muted">Other ways to pay</div>${links}</div>` : ""}
    ${open.length ? `<p class="fine">Card payments go straight to ${escF(v.name || "your vendor")}${d.processor === "whop" ? " through Whop" : d.processor === "stripe" ? " through Stripe" : d.processor === "square" ? " through Square" : ""}. Lazo never holds your money.</p>` : ""}
  </section>`;

  const body = `
  <header class="hero" ${v.coverUrl ? `style="background-image:linear-gradient(rgba(36,30,43,.35),rgba(36,30,43,.75)),url('https://wsrv.nl/?url=${encodeURIComponent(v.coverUrl)}&w=1400&q=70')"` : ""}>
    ${v.logoUrl ? `<img class="logo" src="https://wsrv.nl/?url=${encodeURIComponent(v.logoUrl)}&w=160&h=160&fit=contain" alt="">` : ""}
    <div class="eyebrow light">${escF(v.category || "Your booking")}</div>
    <h1>${escF(v.name || "Your vendor")}</h1>
    <p class="light">${escF(c.name ? `For ${c.name}` : "Your booking")}${c.weddingDate ? ` · ${escF(dateF(c.weddingDate))}` : ""}${c.venue ? ` · ${escF(c.venue)}` : ""}</p>
  </header>
  <main>${proposal}${contract}${money}
  <p class="foot">Questions? <a href="https://app.meetlazo.com/dashboard?thread=${escF(inquiryId)}">Message ${escF(v.name || "your vendor")} on Lazo</a>${v.email ? ` or email <a href="mailto:${escF(v.email)}">${escF(v.email)}</a>` : ""}.</p>
  </main>
  <script>
  const INQ=${JSON.stringify(inquiryId)};
  document.querySelectorAll("form.pay").forEach(f=>{f.addEventListener("submit",async e=>{e.preventDefault();const b=f.querySelector("button");b.disabled=true;const t=b.textContent;b.textContent="Opening checkout…";
    const tip=f.dataset.tip==="1"?Math.max(0,Number((f.querySelector("input[name=tip]")||{}).value||0)):0;
    try{const r=await fetch(PAY+"?inquiry="+encodeURIComponent(INQ)+"&invoice="+encodeURIComponent(f.dataset.inv)+"&tip="+tip);const j=await r.json();if(j&&j.url){location.href=j.url;return;}throw new Error(j&&j.error||"x");}
    catch(err){b.disabled=false;b.textContent=t;alert("Couldn't open checkout - try again in a moment.");}});});
  </script>`;
  return new Response(shell(`${v.name || "Your booking"} - Lazo`, body, primary, accent, true), { headers: noindex });
}

function shell(title, inner, primary = "#52284F", accent = "#D9B77C", full = false) {
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>${escF(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500&display=swap" rel="stylesheet">
<style>
:root{--p:${primary};--a:${accent};--ink:#241E2B;--muted:#6B5F72;--ivory:#FAF6F0;--card:#FFFDF9;--line:#E6D6B8}
*{box-sizing:border-box}body{margin:0;background:var(--ivory);color:var(--ink);font-family:Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}
h1,h2{font-family:"Cormorant Garamond",Georgia,serif;font-weight:600;margin:0}
h1{font-size:44px;line-height:1;color:#fff}h2{font-size:26px;color:var(--p);margin-bottom:4px}
.hero{background:var(--p);background-size:cover;background-position:center;padding:46px 22px 34px;text-align:center}
.logo{width:72px;height:72px;border-radius:16px;background:#fff;object-fit:contain;margin-bottom:14px;box-shadow:0 6px 24px rgba(0,0,0,.25)}
.eyebrow{font-size:10.5px;letter-spacing:2px;text-transform:uppercase;font-weight:800;color:var(--p);margin-bottom:8px}.eyebrow.light{color:var(--a)}
.light{color:rgba(255,255,255,.85);margin:8px 0 0;font-size:14px}
main{max-width:560px;margin:-18px auto 60px;padding:0 14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:20px;margin-bottom:14px}
.big{font-size:32px;font-weight:800;color:var(--ink);margin:6px 0 10px}
.inc{margin:0 0 10px;padding-left:18px;color:var(--ink);font-size:14px;line-height:1.55}
.note{color:var(--muted);font-size:14px;line-height:1.5;margin:6px 0 10px}
.fine{color:var(--muted);font-size:12px;line-height:1.5;margin:12px 0 0}
.pill{display:inline-block;padding:5px 11px;border-radius:999px;font-size:11px;font-weight:800;letter-spacing:1px;text-transform:uppercase;background:rgba(82,40,79,.08);color:var(--p)}
.pill.ok{background:rgba(46,139,107,.14);color:#2E8B6B}.pill.small{padding:3px 8px;font-size:9.5px}
.btn{display:inline-block;border:0;border-radius:12px;padding:13px 18px;background:var(--p);color:#fff;font-weight:800;font-size:15px;cursor:pointer;text-decoration:none;text-align:center}
.btn.ghost{background:transparent;color:var(--p);border:1.5px solid var(--p)}.btn.small{padding:8px 12px;font-size:13px;margin:6px 6px 0 0}
.btn[disabled]{opacity:.6}
.inv{display:grid;grid-template-columns:1fr auto;gap:6px 12px;padding:14px 0;border-top:1px solid var(--line)}.inv:first-of-type{border-top:0}
.inv-t{font-weight:700;font-size:15px}.inv-w{color:var(--muted);font-size:12.5px;margin-top:2px}.inv.late .inv-w{color:#B04343;font-weight:700}
.inv-a{font-weight:800;font-size:17px;text-align:right}.inv-r{text-align:right}.inv.paid .inv-t{color:var(--muted)}
.lines{margin-top:6px;font-size:12px;color:var(--muted)}.lines span{display:block}
.pay{grid-column:1/-1;display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap;margin-top:4px}.pay .btn{flex:1;min-width:160px}
.tip{font-size:12px;color:var(--muted);display:flex;flex-direction:column;gap:4px}.tip input{width:110px;border:1px solid var(--line);border-radius:10px;padding:10px;font-size:15px;background:#fff}
.prog{margin:4px 0 14px}.bar{height:8px;border-radius:999px;background:rgba(82,40,79,.1);overflow:hidden}.bar span{display:block;height:100%;background:var(--p)}.prog-t{font-size:12.5px;color:var(--muted);margin-top:6px}
.links{margin-top:12px}.muted{color:var(--muted);font-size:12px}
.foot{text-align:center;color:var(--muted);font-size:12.5px;line-height:1.6}.foot a{color:var(--p)}
${full ? "" : "main{margin-top:40px}"}
</style></head><body>${full ? inner : `<main><section class="card"><h2>${escF(title)}</h2>${inner}</section><p class="foot"><a href="https://meetlazo.com">Lazo</a></p></main>`}<script>const PAY=${JSON.stringify(PAY_CHECKOUT)};</script></body></html>`;
}
'''

out = s.rstrip() + "\n" + fn002 + fn003 + fnp
for m in ("GALLERY-0912-006", "MUSIC-002", "MUSIC-003", "PAY-001", "async function musicSearch", "async function musicPreview", "async function songRequest", "async function bookingPage"):
    if m not in out:
        sys.exit("post-check failed: " + m)
if out.count("function esc(") or out.count("function escM(") != 1:
    sys.exit("esc collision check failed")
shutil.copy(p, p + ".bak-restore1")
io.open(p, "w", encoding="utf-8", newline="\n").write(out)
print("rebuilt", p, "-", len(out.encode("utf-8")), "bytes - now: npx wrangler deploy")
