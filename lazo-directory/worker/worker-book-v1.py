# JC-LAZO-WORKER-0913-BOOK-001
# Run from C:\Users\kurvh\lazo-directory\worker:   python worker-book-v1.py
# Then:  npx wrangler deploy
#
#   /book/{vendorId}[?inq=&type=]   the vendor's consult scheduler, in their
#                                   brand: meeting type -> day -> slot -> details
#                                   -> booked. Slots come from consultSlots,
#                                   the booking goes to consultBook. Times shown
#                                   in the visitor's own zone with the vendor's
#                                   zone noted. noindex.
# Requires BRAND-001 already applied.
import io, sys, shutil

p = "src/index.js"
s = io.open(p, encoding="utf-8").read()
if "BOOK-001" in s:
    sys.exit("already patched")
if "BRAND-001" not in s:
    sys.exit("run worker-brand-v1.py first")

anchor = '    const wMatch = url.pathname.match(/^\\/w\\/([a-z0-9\\-]{1,80})\\/?$/);'
if anchor not in s:
    sys.exit("/w/ route line not found")
route = '''    // JC-LAZO-WORKER-0913-BOOK-001: consult scheduler
    const bookMatch = url.pathname.match(/^\\/book\\/([A-Za-z0-9_-]{3,120})\\/?$/);
    if (bookMatch && req.method === "GET") return bookPage(bookMatch[1], url.searchParams.get("inq") || "", url.searchParams.get("type") || "");
'''
s = s.replace(anchor, route + anchor, 1)

fn = r'''
// JC-LAZO-WORKER-0913-BOOK-001 --------------------------------------------
const SLOTS_FN = "https://us-central1-lazo-513ec.cloudfunctions.net/consultSlots";
const BOOK_FN = "https://us-central1-lazo-513ec.cloudfunctions.net/consultBook";

async function bookPage(vendorId, inq, typeKey) {
  const v = await fsDoc("vendors", vendorId);
  const sch = v && v.scheduler ? fsVal(v.scheduler) : null;
  if (!v || !sch || sch.enabled === false) {
    return new Response(`<!doctype html><html><head><meta charset="utf-8"><meta name="robots" content="noindex"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Lazo</title></head><body style="font-family:system-ui;max-width:32rem;margin:4rem auto;padding:0 1rem;color:#241E2B"><h1 style="font-weight:600">Booking isn't open here yet</h1><p>Message the vendor on <a href="https://meetlazo.com" style="color:#52284F">Lazo</a> and they'll find a time with you.</p></body></html>`, { status: 404, headers: { "content-type": TYPES.html, "cache-control": "no-store" } });
  }
  const b = brandOf(v);
  const name = b.name || "your vendor";
  const cover = fsVal(v.coverUrl) || "";
  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow">
<title>Book a time - ${escF(name)}</title>
<style>
:root{--p:${b.primary};--a:${b.accent}}
body{margin:0;background:#FAF6F0;font-family:${b.font === "serif" ? "Georgia,serif" : "Helvetica,Arial,sans-serif"};color:#241E2B;-webkit-font-smoothing:antialiased}
*{box-sizing:border-box}
.hero{background:var(--p) ${cover ? `url('https://wsrv.nl/?url=${encodeURIComponent(cover)}&w=1400&q=70') center/cover` : ""};padding:44px 20px 34px;text-align:center;color:#fff;position:relative}
.hero:before{content:"";position:absolute;inset:0;background:rgba(36,30,43,${cover ? ".45" : "0"})}
.hero>*{position:relative}
.hero img.logo{width:60px;height:60px;border-radius:14px;background:#fff;object-fit:contain;margin-bottom:10px}
.hero h1{font-family:Georgia,serif;font-weight:600;font-size:34px;margin:0;line-height:1.05}.hero p{margin:8px 0 0;opacity:.9;font-size:14px}
main{max-width:560px;margin:-18px auto 60px;padding:0 14px}
.card{background:#FFFDF9;border:1px solid #E6D6B8;border-radius:18px;padding:20px;margin-bottom:12px}
.eyebrow{font-size:10.5px;letter-spacing:2px;text-transform:uppercase;font-weight:800;color:var(--p);margin-bottom:10px}
.types{display:grid;gap:8px}.type{border:1.5px solid #E6D6B8;border-radius:13px;padding:12px 14px;cursor:pointer;background:#fff;text-align:left;font:inherit;color:#241E2B}
.type.on{border-color:var(--p);box-shadow:0 0 0 3px rgba(82,40,79,.12)}.type b{display:block;font-size:15px}.type span{font-size:12px;color:#6B5F72}
.days{display:flex;gap:8px;overflow-x:auto;padding:4px 2px 8px;scrollbar-width:thin}
.day{flex:0 0 auto;border:1.5px solid #E6D6B8;border-radius:13px;padding:8px 10px;min-width:62px;text-align:center;cursor:pointer;background:#fff;font:inherit;color:#241E2B}
.day.on{border-color:var(--p);background:var(--p);color:#fff}.day small{display:block;font-size:10.5px;opacity:.75;text-transform:uppercase;letter-spacing:1px}.day b{font-size:18px;line-height:1.1}
.slots{display:grid;grid-template-columns:repeat(auto-fill,minmax(96px,1fr));gap:8px;margin-top:6px}
.slot{border:1.5px solid #E6D6B8;border-radius:11px;padding:10px 6px;text-align:center;cursor:pointer;background:#fff;font:inherit;font-size:14px;color:#241E2B}
.slot.on{border-color:var(--p);background:var(--p);color:#fff}
.muted{color:#6B5F72;font-size:12.5px;line-height:1.5}
label{display:block;font-size:11px;letter-spacing:1.2px;text-transform:uppercase;font-weight:700;color:var(--p);margin:10px 0 5px}
input,textarea{width:100%;border:1px solid #E6D6B8;border-radius:11px;padding:11px 12px;font-size:15px;background:#fff;color:#241E2B;font-family:inherit}
input:focus,textarea:focus{outline:none;border-color:var(--p)}textarea{min-height:70px}
.row{display:grid;grid-template-columns:1fr 1fr;gap:10px}@media(max-width:480px){.row{grid-template-columns:1fr}}
.ck{display:flex;gap:8px;align-items:flex-start;font-size:12px;color:#6B5F72;margin-top:12px;line-height:1.4}.ck input{width:auto;margin-top:2px}
.btn{width:100%;border:0;border-radius:12px;padding:14px;background:var(--p);color:#fff;font-size:15px;font-weight:700;cursor:pointer;font-family:inherit;margin-top:14px}
.btn[disabled]{opacity:.55}
.err{color:#B04343;font-size:13px;margin-top:8px;display:none}
.hp{position:absolute;left:-9999px;opacity:0}
.ok h2{font-family:Georgia,serif;font-weight:600;font-size:28px;color:var(--p);margin:0 0 6px}
.foot{text-align:center;font-size:11.5px;color:#6B5F72;margin-top:24px}.foot a{color:var(--p)}
.hide{display:none}
</style></head><body>
<header class="hero">${b.logoUrl ? `<img class="logo" src="https://wsrv.nl/?url=${encodeURIComponent(b.logoUrl)}&w=120&h=120&fit=contain" alt="">` : ""}<h1>${escF(name)}</h1><p>Pick a time that works for you.</p></header>
<main>
<section class="card" id="s1"><div class="eyebrow">What kind of chat</div><div class="types" id="types"><p class="muted">Loading\u2026</p></div></section>
<section class="card hide" id="s2"><div class="eyebrow">Pick a day</div><div class="days" id="days"></div><div class="eyebrow" style="margin-top:12px">Then a time <span id="tzn" style="font-weight:400;letter-spacing:0;text-transform:none;color:#6B5F72"></span></div><div class="slots" id="slots"><p class="muted">Choose a day above.</p></div></section>
<section class="card hide" id="s3"><div class="eyebrow">Your details</div>
<div class="row"><div><label>Your name</label><input id="n" maxlength="120" autocomplete="name"></div><div><label>Wedding date (if set)</label><input id="d" type="date"></div></div>
<div class="row"><div><label>Email</label><input id="e" type="email" maxlength="160" autocomplete="email"></div><div><label>Phone</label><input id="p" type="tel" maxlength="30" autocomplete="tel"></div></div>
<label>Anything we should know?</label><textarea id="m" maxlength="600"></textarea>
<input class="hp" id="w" tabindex="-1" autocomplete="off">
<label class="ck" style="text-transform:none;letter-spacing:0;font-weight:400"><input id="sm" type="checkbox" checked> Text me a reminder. Reply STOP anytime.</label>
<button class="btn" id="go" type="button">Book it</button><div class="err" id="x"></div></section>
<section class="card hide ok" id="s4"><h2>You're booked</h2><p id="okt" class="muted"></p><p class="muted">A confirmation and calendar invite are on the way. Need to change it? The cancel link is in that email.</p></section>
<p class="foot">Scheduling by <a href="https://meetlazo.com">Lazo</a></p>
</main>
<script>
const V=${JSON.stringify(vendorId)},INQ=${JSON.stringify(inq)};let TYPES=[],type=${JSON.stringify(typeKey)},day="",start="",TZ="",DAYS=[];
const $=i=>document.getElementById(i);const show=(i,on)=>$(i).classList.toggle("hide",!on);
const localTZ=Intl.DateTimeFormat().resolvedOptions().timeZone;
function fmtT(iso){return new Date(iso).toLocaleTimeString([],{hour:"numeric",minute:"2-digit"})}
fetch(SLOTS+"?v="+encodeURIComponent(V)).then(r=>r.json()).then(j=>{TYPES=j.types||[];TZ=j.tz||"";DAYS=j.days||[];
 if(!type||!TYPES.some(t=>t.key===type))type=TYPES.length?TYPES[0].key:"";
 $("types").innerHTML=TYPES.map(t=>'<button class="type'+(t.key===type?" on":"")+'" data-k="'+t.key+'"><b>'+t.label+'</b><span>'+t.minutes+' min \u00b7 '+(t.mode==="video"?"video call":t.mode==="phone"?"phone call":"in person")+'</span></button>').join("");
 document.querySelectorAll(".type").forEach(el=>el.onclick=()=>{type=el.dataset.k;document.querySelectorAll(".type").forEach(x=>x.classList.toggle("on",x===el));if(day)loadSlots();});
 $("days").innerHTML=DAYS.slice(0,45).map(k=>{const d=new Date(k+"T12:00:00");return '<button class="day" data-k="'+k+'"><small>'+d.toLocaleDateString([],{weekday:"short"})+'</small><b>'+d.getDate()+'</b><small>'+d.toLocaleDateString([],{month:"short"})+'</small></button>'}).join("")||'<p class="muted">No openings right now - message the vendor instead.</p>';
 document.querySelectorAll(".day").forEach(el=>el.onclick=()=>{day=el.dataset.k;document.querySelectorAll(".day").forEach(x=>x.classList.toggle("on",x===el));loadSlots();});
 $("tzn").textContent=localTZ&&TZ&&localTZ!==TZ?"(shown in your time, "+localTZ.replace(/_/g," ")+")":"";
 show("s2",true);}).catch(()=>{$("types").innerHTML='<p class="muted">Could not load times - try again in a moment.</p>'});
function loadSlots(){start="";show("s3",false);$("slots").innerHTML='<p class="muted">Loading\u2026</p>';
 fetch(SLOTS+"?v="+encodeURIComponent(V)+"&d="+day+"&type="+encodeURIComponent(type)).then(r=>r.json()).then(j=>{const s=j.slots||[];
  $("slots").innerHTML=s.length?s.map(iso=>'<button class="slot" data-s="'+iso+'">'+fmtT(iso)+'</button>').join(""):'<p class="muted">Nothing open that day - try another.</p>';
  document.querySelectorAll(".slot").forEach(el=>el.onclick=()=>{start=el.dataset.s;document.querySelectorAll(".slot").forEach(x=>x.classList.toggle("on",x===el));show("s3",true);$("s3").scrollIntoView({behavior:"smooth",block:"start"});});
 }).catch(()=>{$("slots").innerHTML='<p class="muted">Could not load times.</p>'});}
$("go").onclick=()=>{const n=$("n").value.trim(),e=$("e").value.trim(),p=$("p").value.trim(),x=$("x");x.style.display="none";
 if(!start){x.textContent="Pick a time first.";x.style.display="block";return}
 if(!n){x.textContent="What's your name?";x.style.display="block";return}
 if(!e&&!p){x.textContent="An email or phone so we can confirm.";x.style.display="block";return}
 const b=$("go");b.disabled=true;b.textContent="Booking\u2026";
 fetch(BOOK,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({vendorId:V,inquiryId:INQ,type:type,start:start,name:n,email:e,phone:p,weddingDate:$("d").value,note:$("m").value.trim(),smsOk:$("sm").checked,website:$("w").value,page:location.href,referrer:document.referrer})})
 .then(r=>r.json().then(j=>({ok:r.ok,j})))
 .then(({ok,j})=>{if(!ok||!j.ok){if(j&&j.error==="taken"){x.textContent="That time was just taken - pick another.";x.style.display="block";b.disabled=false;b.textContent="Book it";loadSlots();return}throw new Error()}
  try{if(window.fbq)fbq("track","Schedule")}catch(_){}
  $("okt").textContent=(TYPES.find(t=>t.key===type)||{label:"Consult"}).label+" with ${escF(name).replace(/"/g,'\\"')} \u2014 "+j.when;
  show("s1",false);show("s2",false);show("s3",false);show("s4",true);window.scrollTo({top:0,behavior:"smooth"});})
 .catch(()=>{x.textContent="That didn't go through - try again.";x.style.display="block";b.disabled=false;b.textContent="Book it"});};
const SLOTS=${JSON.stringify(SLOTS_FN)},BOOK=${JSON.stringify(BOOK_FN)};
</script></body></html>`;
  return new Response(html, { headers: { "content-type": TYPES.html, "cache-control": "no-store", "x-robots-tag": "noindex" } });
}
'''
shutil.copy(p, p + ".bak-book1")
io.open(p, "w", encoding="utf-8", newline="\n").write(s.rstrip() + "\n" + fn)
print("patched", p, "- now: npx wrangler deploy")
