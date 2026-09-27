# JC-LAZO-WORKER-0913-LEAD-001
# Run from C:\Users\kurvh\lazo-directory\worker:   python worker-lead-v1.py
# Then:  npx wrangler deploy
#
#   /embed/lead.js          the embeddable lead form. One tag on the vendor's
#                           own site:
#     <script src="https://meetlazo.com/embed/lead.js"
#             data-vendor="VENDOR_ID" data-key="FORM_KEY"></script>
#                           Renders in a shadow root (their CSS can't break it),
#                           carries page URL, referrer and UTMs, honeypot,
#                           posts to leadIngest, then shows the thank-you or
#                           redirects. Optional: data-redirect, data-accent,
#                           data-heading, data-button.
#   /lead/{vendorId}?k=     the same form as a hosted page - for vendors who
#                           can only add a link (Squarespace buttons, Instagram
#                           bio, a QR code at a bridal show).
# Requires PAY-001 (restore) already applied - refuses otherwise.
import io, sys, shutil

p = "src/index.js"
s = io.open(p, encoding="utf-8").read()
if "LEAD-001" in s:
    sys.exit("already patched")
if "PAY-001" not in s:
    sys.exit("run worker-restore-v1.py first")

anchor = '    const wMatch = url.pathname.match(/^\\/w\\/([a-z0-9\\-]{1,80})\\/?$/);'
if anchor not in s:
    sys.exit("/w/ route line not found")

route = '''    // JC-LAZO-WORKER-0913-LEAD-001: embeddable lead form + hosted lead page
    if (url.pathname === "/embed/lead.js") return new Response(LEAD_JS, { headers: { "content-type": TYPES.js, "cache-control": "public, max-age=3600, s-maxage=86400", "access-control-allow-origin": "*" } });
    const leadMatch = url.pathname.match(/^\\/lead\\/([A-Za-z0-9_-]{3,120})\\/?$/);
    if (leadMatch && req.method === "GET") return leadPage(leadMatch[1], url.searchParams.get("k") || "");
'''
s = s.replace(anchor, route + anchor, 1)

fn = r'''
// JC-LAZO-WORKER-0913-LEAD-001 --------------------------------------------
const LEAD_INGEST = "https://us-central1-lazo-513ec.cloudfunctions.net/leadIngest";

async function leadPage(vendorId, key) {
  const v = await fsDoc("vendors", vendorId);
  const name = v ? (fsVal(v.name) || "this vendor") : "this vendor";
  const form = v && v.leadForm ? fsVal(v.leadForm) : null;
  if (!v || !form || !key || form.key !== key || form.enabled === false) {
    return new Response(`<!doctype html><html><head><meta charset="utf-8"><meta name="robots" content="noindex"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Lazo</title></head><body style="font-family:system-ui;max-width:32rem;margin:4rem auto;padding:0 1rem;color:#241E2B"><h1 style="font-weight:600">This form isn't live</h1><p>Ask the vendor for their current link, or find them on <a href="https://meetlazo.com" style="color:#52284F">Lazo</a>.</p></body></html>`, { status: 404, headers: { "content-type": TYPES.html, "cache-control": "no-store" } });
  }
  const cover = fsVal(v.coverUrl) || "";
  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow">
<title>Inquire - ${escF(name)}</title>
<style>body{margin:0;background:#FAF6F0;font-family:Helvetica,Arial,sans-serif;color:#241E2B}
.hero{background:#52284F ${cover ? `url('https://wsrv.nl/?url=${encodeURIComponent(cover)}&w=1400&q=70') center/cover` : ""};padding:52px 20px 40px;text-align:center;color:#fff}
.hero h1{font-family:Georgia,serif;font-weight:600;font-size:38px;margin:0;line-height:1.05}.hero p{margin:8px 0 0;opacity:.85;font-size:14px}
main{max-width:520px;margin:-18px auto 60px;padding:0 14px}.foot{text-align:center;font-size:11.5px;color:#6B5F72;margin-top:24px}.foot a{color:#52284F}</style></head>
<body><header class="hero"><h1>${escF(name)}</h1><p>Tell us about your day - we'll get right back to you.</p></header>
<main><script src="https://meetlazo.com/embed/lead.js" data-vendor="${escF(vendorId)}" data-key="${escF(key)}" data-heading=" "></script>
<p class="foot">Powered by <a href="https://meetlazo.com">Lazo</a></p></main></body></html>`;
  return new Response(html, { headers: { "content-type": TYPES.html, "cache-control": "no-store", "x-robots-tag": "noindex" } });
}

const LEAD_JS = `(function(){
var s=document.currentScript;if(!s)return;var V=s.getAttribute("data-vendor")||"",K=s.getAttribute("data-key")||"";if(!V||!K)return;
var accent=s.getAttribute("data-accent")||"#52284F",heading=s.getAttribute("data-heading"),btn=s.getAttribute("data-button")||"Send inquiry",redirect=s.getAttribute("data-redirect")||"";
var host=document.createElement("div");host.className="lazo-lead";s.parentNode.insertBefore(host,s);var r=host.attachShadow({mode:"open"});
var q=new URLSearchParams(location.search),utm={source:q.get("utm_source")||"",medium:q.get("utm_medium")||"",campaign:q.get("utm_campaign")||"",content:q.get("utm_content")||"",term:q.get("utm_term")||""};
r.innerHTML='<style>:host{all:initial;display:block;font-family:-apple-system,Helvetica,Arial,sans-serif;color:#241E2B}*{box-sizing:border-box}.c{background:#FFFDF9;border:1px solid #E6D6B8;border-radius:18px;padding:22px;max-width:520px}h3{margin:0 0 4px;font:600 22px Georgia,serif;color:'+accent+'}p{margin:0 0 14px;font-size:13px;color:#6B5F72;line-height:1.45}label{display:block;font-size:11px;letter-spacing:1.2px;text-transform:uppercase;font-weight:700;color:'+accent+';margin:10px 0 5px}input,textarea,select{width:100%;border:1px solid #E6D6B8;border-radius:11px;padding:11px 12px;font-size:15px;background:#fff;color:#241E2B;font-family:inherit}input:focus,textarea:focus{outline:none;border-color:'+accent+';box-shadow:0 0 0 3px rgba(82,40,79,.15)}textarea{min-height:88px;resize:vertical}.row{display:grid;grid-template-columns:1fr 1fr;gap:10px}@media(max-width:480px){.row{grid-template-columns:1fr}}.ck{display:flex;gap:8px;align-items:flex-start;font-size:12px;color:#6B5F72;margin-top:12px;line-height:1.4}.ck input{width:auto;margin-top:2px}button{margin-top:16px;width:100%;border:0;border-radius:12px;padding:14px;background:'+accent+';color:#fff;font-size:15px;font-weight:700;cursor:pointer}button:disabled{opacity:.6}.err{color:#B04343;font-size:13px;margin-top:8px;display:none}.ok{display:none;text-align:center;padding:26px 0}.ok h3{font-size:26px}.hp{position:absolute;left:-9999px;opacity:0}.pw{margin-top:12px;text-align:center;font-size:10.5px;color:#9A8FA0}.pw a{color:#9A8FA0}</style>'+
'<div class="c"><div id="f">'+(heading===" "?"":'<h3>'+(heading||"Check your date")+'</h3><p>A few details and we\\'ll get right back to you.</p>')+
'<div class="row"><div><label>Your name</label><input id="n" maxlength="120" autocomplete="name" required></div><div><label>Wedding date</label><input id="d" type="date"></div></div>'+
'<div class="row"><div><label>Email</label><input id="e" type="email" maxlength="160" autocomplete="email"></div><div><label>Phone</label><input id="p" type="tel" maxlength="30" autocomplete="tel"></div></div>'+
'<div class="row"><div><label>Venue (if you have one)</label><input id="v" maxlength="160"></div><div><label>Guests</label><input id="g" inputmode="numeric" maxlength="6" placeholder="About how many?"></div></div>'+
'<label>Tell us about your day</label><textarea id="m" maxlength="2000"></textarea>'+
'<input class="hp" id="w" tabindex="-1" autocomplete="off">'+
'<label class="ck" style="text-transform:none;letter-spacing:0;font-weight:400"><input id="s" type="checkbox" checked> Text me back - it\\'s the fastest way to hear from us. Reply STOP anytime.</label>'+
'<button id="b" type="button">'+btn+'</button><div class="err" id="x"></div></div>'+
'<div class="ok" id="ok"><h3>Sent!</h3><p id="okt">We\\'ll be in touch shortly.</p></div>'+
'<div class="pw">Secure inquiry via <a href="https://meetlazo.com" target="_blank" rel="noopener">Lazo</a></div></div>';
function $(i){return r.getElementById(i)}
$("b").onclick=function(){var n=$("n").value.trim(),e=$("e").value.trim(),p=$("p").value.trim(),x=$("x");x.style.display="none";
if(!n){x.textContent="What's your name?";x.style.display="block";return}if(!e&&!p){x.textContent="An email or a phone number so they can reach you.";x.style.display="block";return}
var b=$("b");b.disabled=true;var t=b.textContent;b.textContent="Sending\\u2026";
fetch("${LEAD_INGEST}",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({vendorId:V,key:K,name:n,email:e,phone:p,weddingDate:$("d").value,venue:$("v").value.trim(),guests:$("g").value.trim(),message:$("m").value.trim(),smsOk:$("s").checked,website:$("w").value,page:location.href,referrer:document.referrer,utm:utm})})
.then(function(res){return res.json().then(function(j){if(!res.ok||!j.ok)throw new Error(j&&j.error||"x");return j})})
.then(function(j){try{if(window.fbq)fbq("track","Lead");if(window.gtag)gtag("event","generate_lead")}catch(_){}
var to=redirect||j.redirect;if(to){location.href=to;return}if(j.thanks)$("okt").textContent=j.thanks;$("f").style.display="none";$("ok").style.display="block"})
.catch(function(){b.disabled=false;b.textContent=t;x.textContent="That didn't go through - try again in a moment.";x.style.display="block"})};
})();`;
'''
shutil.copy(p, p + ".bak-lead1")
io.open(p, "w", encoding="utf-8", newline="\n").write(s.rstrip() + "\n" + fn)
print("patched", p, "- now: npx wrangler deploy")
