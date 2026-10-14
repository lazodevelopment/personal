r"""apply_plus.py - JC-LAZO-WWS-1014-PLUS
What a guest looks for that the templates did not have yet. Every block hides
itself when the couple has not filled it in, and the demos show a sample.
Idempotent: the CSS block and the script are tagged and replaced on re-runs.

  python wedding-websites\apply_plus.py             # the 21 selectable designs
  python wedding-websites\apply_plus.py peony noir  # some

  1. Countdown: hours, minutes and seconds tick under the days in the header
     (the last year before the day only; gone once they are married).
  2. Hashtag: a chip in the header and on the guest-photo wall, tap to copy.
  3. Our story in dates: milestones with a date, a line and a photo, on a rail
     under the story.
  4. The wedding party: names, roles and photos, with a tab for each side.
  5. Gallery: tap any photo for a full-screen viewer (swipe, arrows, Esc);
     when the couple has more photos than the design has frames, "See all"
     opens every one in a masonry wall.
  6. The weekend: events on more than one date sit in day tabs.
  7. Where to stay: hotel cards with Book, the room-block code (tap to copy),
     the book-by date and rate. No hotel listed yet? The best-rated hotels
     near the venue, from /api/stay. Getting there: the nearest airports with
     a rough drive time, and the couple's driving notes.
"""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DESIGNS = ["sage", "noir", "dune", "fete", "tide", "flora", "atelier", "verona", "shore", "summit",
           "ranch", "starlit", "frost", "harvest", "aquarelle", "prism", "meadow", "gilded",
           "marigold", "papel", "peony"]
TAG = "JC-LAZO-WWS-1014-PLUS"

CSS = r"""
/* ---- TAG ---- */
.lzp-tabs{display:flex;flex-wrap:wrap;justify-content:center;gap:8px;margin:26px auto 0;padding:0;list-style:none}
.lzp-tab{font:inherit;font-size:12px;letter-spacing:.16em;text-transform:uppercase;padding:9px 16px;border-radius:999px;border:1px solid var(--line);background:var(--panel);color:var(--ink);cursor:pointer;transition:background-color .2s ease,color .2s ease,border-color .2s ease,transform .26s var(--lz-out,ease)}
.lzp-tab:active{transform:scale(.97);transition-duration:.09s}
.lzp-tab[aria-selected=true]{background:var(--acc);border-color:var(--acc);color:var(--bg)}
.lzp-tab:focus-visible,.lzp-btn:focus-visible,.lzp-chip:focus-visible{outline:2px solid var(--acc);outline-offset:2px}
/* the wedding party */
.lzp-party{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:clamp(18px,3vw,30px);margin-top:clamp(26px,3.4vw,40px)}
.lzp-pc{text-align:center;transition:opacity .35s ease,transform .35s var(--lz-out,ease)}
.lzp-pc[hidden]{display:none}
.lzp-ph{width:min(132px,70%);aspect-ratio:1;margin:0 auto 14px;border-radius:50%;overflow:hidden;background:var(--sand,var(--line));display:flex;align-items:center;justify-content:center;font-size:30px;letter-spacing:.04em;color:var(--acc);box-shadow:0 0 0 1px var(--line),0 14px 30px -18px rgba(0,0,0,.35)}
.lzp-ph img{width:100%;height:100%;object-fit:cover;display:block}
.lzp-pn{display:block;font-size:17px;line-height:1.25}
.lzp-pr{display:block;font-size:10.5px;letter-spacing:.26em;text-transform:uppercase;color:var(--acc);margin-top:6px}
.lzp-pt{display:block;font-size:13px;color:var(--mut);margin-top:8px;line-height:1.5;text-wrap:pretty}
/* our story in dates */
.lzp-ms{position:relative;max-width:760px;margin:clamp(26px,3.4vw,42px) auto 0;padding:0;list-style:none}
.lzp-ms::before{content:"";position:absolute;left:7px;top:6px;bottom:6px;width:1px;background:var(--line)}
.lzp-mi{position:relative;display:grid;grid-template-columns:1fr auto;gap:18px;align-items:start;padding:0 0 clamp(26px,3vw,36px) 38px}
.lzp-mi:last-child{padding-bottom:0}
.lzp-mi::before{content:"";position:absolute;left:0;top:4px;width:15px;height:15px;border-radius:50%;background:var(--bg);border:1px solid var(--acc);box-shadow:inset 0 0 0 3px var(--bg),inset 0 0 0 8px var(--acc)}
.lzp-mw{display:block;font-size:10.5px;letter-spacing:.3em;text-transform:uppercase;color:var(--acc);margin-bottom:6px}
.lzp-mi h3{margin:0;font-size:clamp(19px,2.2vw,23px);line-height:1.25}
.lzp-mi p{margin:8px 0 0;color:var(--mut);line-height:1.6;font-size:14.5px;text-wrap:pretty}
.lzp-mp{width:clamp(96px,16vw,150px);aspect-ratio:4/5;border-radius:3px;overflow:hidden;background:var(--line);cursor:zoom-in}
.lzp-mp img{width:100%;height:100%;object-fit:cover;display:block}
@media(max-width:560px){.lzp-mi{grid-template-columns:1fr}.lzp-mp{width:100%;aspect-ratio:16/10}}
/* gallery */
.gal figure.lzp-z{cursor:zoom-in}
.lzp-allw{text-align:center;margin-top:clamp(20px,2.6vw,30px)}
.lzp-btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;font:inherit;font-size:12px;letter-spacing:.16em;text-transform:uppercase;text-decoration:none;padding:11px 20px;border-radius:999px;border:1px solid var(--acc);background:transparent;color:var(--acc);cursor:pointer;transition:background-color .2s ease,color .2s ease,transform .26s var(--lz-out,ease)}
.lzp-btn:active{transform:scale(.97);transition-duration:.09s}
.lzp-btn.solid{background:var(--acc);color:var(--bg)}
@media(hover:hover) and (pointer:fine){.lzp-btn:hover{background:var(--acc);color:var(--bg)}.lzp-btn.solid:hover{filter:brightness(1.08)}}
.lzp-mz{position:fixed;inset:0;z-index:80;background:var(--bg);overflow-y:auto;-webkit-overflow-scrolling:touch;opacity:0;transition:opacity .3s ease}
.lzp-mz.on{opacity:1}
.lzp-mzh{position:sticky;top:0;z-index:1;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px clamp(16px,4vw,40px);background:var(--bg);border-bottom:1px solid var(--line)}
.lzp-mzh b{font-weight:500;font-size:13px;letter-spacing:.2em;text-transform:uppercase}
.lzp-mzg{columns:3 260px;column-gap:10px;padding:14px clamp(10px,3vw,40px) 60px}
.lzp-mzg button{display:block;width:100%;margin:0 0 10px;padding:0;border:0;background:var(--line);break-inside:avoid;cursor:zoom-in;border-radius:2px;overflow:hidden}
.lzp-mzg img{display:block;width:100%;height:auto;min-height:80px}
@media(max-width:560px){.lzp-mzg{columns:2;column-gap:6px}.lzp-mzg button{margin-bottom:6px}}
.lzp-lb{position:fixed;inset:0;z-index:90;background:rgba(8,8,10,.94);display:flex;align-items:center;justify-content:center;opacity:0;transition:opacity .25s ease;touch-action:pan-y}
.lzp-lb.on{opacity:1}
.lzp-lb img{max-width:94vw;max-height:84vh;object-fit:contain;box-shadow:0 30px 80px -30px rgba(0,0,0,.8);user-select:none;-webkit-user-drag:none;transition:opacity .2s ease}
.lzp-lbx,.lzp-lbp,.lzp-lbn{position:absolute;border:0;background:rgba(255,255,255,.1);color:#fff;width:46px;height:46px;border-radius:50%;font-size:20px;line-height:1;cursor:pointer;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px)}
.lzp-lbx{top:16px;right:16px}
.lzp-lbp{left:16px;top:50%;margin-top:-23px}.lzp-lbn{right:16px;top:50%;margin-top:-23px}
.lzp-lbc{position:absolute;bottom:18px;left:0;right:0;text-align:center;color:rgba(255,255,255,.75);font-size:12px;letter-spacing:.2em}
@media(max-width:640px){.lzp-lbp,.lzp-lbn{display:none}}
/* hashtag */
.lzp-chip{display:inline-flex;align-items:center;gap:8px;font:inherit;font-size:13px;letter-spacing:.06em;padding:8px 14px;border-radius:999px;border:1px solid currentColor;background:transparent;color:inherit;cursor:pointer;opacity:.92;transition:opacity .2s ease,transform .26s var(--lz-out,ease)}
.lzp-chip:active{transform:scale(.97);transition-duration:.09s}
.lzp-chip small{font-size:10px;letter-spacing:.2em;text-transform:uppercase;opacity:.7}
.hero .lzp-chip{margin-top:16px;background:rgba(255,255,255,.08);backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px)}
.lzp-tagw{text-align:center;margin-top:18px;color:var(--acc)}
.lzp-cdx{margin:8px 0 0;font-size:12px;letter-spacing:.24em;text-transform:uppercase;font-variant-numeric:tabular-nums;opacity:.85}
body.married .lzp-cdx{display:none}
/* where to stay, getting there */
.lzp-hg{display:grid;gap:14px;margin-top:clamp(26px,3.4vw,40px)}
@media(min-width:760px){.lzp-hg{grid-template-columns:1fr 1fr}}
.lzp-hc{background:var(--panel);border:1px solid var(--line);padding:clamp(18px,2.4vw,26px);display:flex;flex-direction:column;gap:6px}
.lzp-hc.blk{border-color:var(--acc)}
.lzp-hc h3{margin:0;font-size:clamp(19px,2.2vw,22px);line-height:1.25}
.lzp-hm{font-size:12.5px;color:var(--mut);line-height:1.5}
.lzp-hk{font-size:10.5px;letter-spacing:.28em;text-transform:uppercase;color:var(--acc)}
.lzp-code{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:8px;padding:10px 12px;border:1px dashed var(--acc);font-size:14px;cursor:pointer;background:transparent;color:inherit;font-family:inherit;text-align:left}
.lzp-code b{font-weight:600;letter-spacing:.06em}
.lzp-code small{font-size:10px;letter-spacing:.2em;text-transform:uppercase;color:var(--acc);white-space:nowrap}
.lzp-ha{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.lzp-ha .lzp-btn{padding:9px 16px;font-size:11px}
.lzp-tv{max-width:760px;margin:clamp(30px,4vw,48px) auto 0}
.lzp-ap{display:flex;align-items:center;gap:14px;padding:14px 0;border-top:1px solid var(--line);text-decoration:none;color:inherit}
.lzp-ap:last-of-type{border-bottom:1px solid var(--line)}
.lzp-apc{flex:0 0 auto;min-width:54px;padding:8px 6px;text-align:center;border:1px solid var(--acc);color:var(--acc);font-weight:600;letter-spacing:.12em;font-size:13px}
.lzp-apt{flex:1;min-width:0}.lzp-apt b{display:block;font-weight:500;font-size:15px;line-height:1.3}.lzp-apt span{display:block;font-size:12.5px;color:var(--mut);margin-top:3px}
.lzp-dn{margin:20px 0 0;color:var(--mut);line-height:1.65;white-space:pre-line;text-wrap:pretty}
.lzp-fine{margin-top:16px;font-size:10px;letter-spacing:.24em;text-transform:uppercase;color:var(--mut);text-align:center}
.lzp-toast{position:fixed;left:50%;bottom:24px;z-index:95;transform:translate(-50%,20px);opacity:0;background:var(--ink);color:var(--bg);padding:10px 18px;border-radius:999px;font-size:13px;pointer-events:none;transition:opacity .25s ease,transform .3s var(--lz-out,ease)}
.lzp-toast.on{opacity:1;transform:translate(-50%,0)}
body.framed .lzp-sec,body.framed .lzp-cdx,body.framed .lzp-chip{display:none}
@media(prefers-reduced-motion:reduce){.lzp-mz,.lzp-lb,.lzp-toast,.lzp-pc{transition:none}}
/* ---- /TAG ---- */
""".replace("TAG", TAG)

JS = r"""
<script>
/* TAG: party, gallery viewer, day tabs, stay and travel, hashtag, story in dates, live countdown */
(function(){
 if(document.readyState==="loading"){document.addEventListener("DOMContentLoaded",arguments.callee);return}
 if(document.body.classList.contains("framed"))return;
 var LIVE=window.LAZO_SITE||null,LS=LIVE||{};
 var vName=String(LS.venueName||"").replace(/\s*\([^)]*$/,"").trim();   /* "Willow Creek (" from a clipped autocomplete */
 var esc=function(t){return String(t==null?"":t).replace(/[<>&"]/g,function(c){return{"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"}[c]})};
 var sized=function(u,w){return /^https:\/\//.test(u)&&u.indexOf("wsrv.nl")<0?"https://wsrv.nl/?url="+encodeURIComponent(u)+"&w="+w+"&q=74":u};
 var img=function(u,w,alt){return '<img loading="lazy" decoding="async" alt="'+esc(alt||"")+'" src="'+esc(sized(u,w))+'" data-orig="'+esc(u)+'" onerror="if(this.dataset.orig&&this.src!==this.dataset.orig){this.src=this.dataset.orig}else{this.style.visibility=\'hidden\'}">'};
 var motion=document.documentElement.classList.contains("motion")&&!(window.matchMedia&&matchMedia("(prefers-reduced-motion: reduce)").matches);
 var reveal=function(el){if(!motion)return;el.classList.add("rv");requestAnimationFrame(function(){requestAnimationFrame(function(){el.classList.add("in")})})};
 var n1=(document.querySelector("[data-n1]")||{}).textContent||"",n2=(document.querySelector("[data-n2]")||{}).textContent||"";
 var secOf=function(el){return el?el.closest("section"):null};
 var after=function(ref,el){if(ref&&ref.parentNode){ref.parentNode.insertBefore(el,ref.nextSibling);return true}return false};
 var section=function(k,h,lede){var s=document.createElement("section");s.className="lzp-sec";s.innerHTML='<div class="wrap"><div class="center"><p class="k">'+esc(k)+'</p><h2 style="margin:0 auto">'+esc(h)+'</h2>'+(lede?'<p class="lede">'+esc(lede)+'</p>':'')+'</div></div>';return s};
 var toastEl=null,toastT=0;
 function toast(t){if(!toastEl){toastEl=document.createElement("div");toastEl.className="lzp-toast";toastEl.setAttribute("role","status");document.body.appendChild(toastEl)}toastEl.textContent=t;toastEl.classList.add("on");clearTimeout(toastT);toastT=setTimeout(function(){toastEl.classList.remove("on")},1800)}
 function copy(t,ok){
  var done=function(){toast(ok||"Copied")};
  var old=function(){var a=document.createElement("textarea");a.value=t;a.setAttribute("readonly","");a.style.position="fixed";a.style.opacity="0";document.body.appendChild(a);a.select();try{document.execCommand("copy");done()}catch(_){toast(t)}a.remove()};
  if(navigator.clipboard&&navigator.clipboard.writeText)navigator.clipboard.writeText(t).then(done,old);else old();
 }
 function tabs(labels,onPick,start){
  var ul=document.createElement("div");ul.className="lzp-tabs";ul.setAttribute("role","tablist");
  labels.forEach(function(l,i){var b=document.createElement("button");b.type="button";b.className="lzp-tab";b.setAttribute("role","tab");b.textContent=l;b.setAttribute("aria-selected",i===start?"true":"false");
   b.addEventListener("click",function(){[].forEach.call(ul.children,function(c,j){c.setAttribute("aria-selected",j===i?"true":"false")});onPick(i)});ul.appendChild(b)});
  onPick(start);return ul;
 }

 /* ---- demo samples: the template pages show what a couple can add ---- */
 if(!LIVE){
  var a1=n1||"Clara",a2=n2||"Julian";
  LS={demo:true,hashtag:(a1+"And"+a2).replace(/[^A-Za-z0-9]/g,""),partySides:[a1+"’s side",a2+"’s side"],
   weddingParty:[{name:"Maya Brooks",role:"Maid of honor",side:"a",note:"Roommate, co-conspirator, the first call after the proposal."},{name:"Ella Ruiz",role:"Bridesmaid",side:"a"},{name:"Priya Shah",role:"Bridesmaid",side:"a"},
    {name:"Theo Grant",role:"Best man",side:"b",note:"Brother, and the reason the first date happened at all."},{name:"Sam Okafor",role:"Groomsman",side:"b"},{name:"Luca Moretti",role:"Groomsman",side:"b"},{name:"Rev. Ann Hale",role:"Officiant",side:""}],
   milestones:[{when:"Spring 2021",title:"The wrong number",text:"One digit off on a coffee cup. Found anyway."},{when:"June 2022",title:"First trip",text:"Lisbon, in a rainstorm, with one umbrella between us."},{when:"December 2025",title:"The question",text:"On the pier where it started, with everyone hiding behind the boathouse."}],
   drivingNotes:"From the airport, take I-526 W to I-26 E and follow signs downtown. Allow extra time on Friday evenings.",
   venueName:"demo"};
 }

 /* ---- 0. the header names THEIR venue, not the template's sample ---- */
 (function(){
  var wh=document.querySelector(".hero .where");if(!LIVE||!wh)return;
  var parts=String(LS.venueAddress||"").split(",").map(function(x){return x.trim()}).filter(Boolean);
  if(parts.length>1&&/\d/.test(parts[0]))parts.shift();                    /* the street goes */
  var place=parts.map(function(x){return x.replace(/\s*\d{5}(-\d{4})?$/,"").replace(/^(USA|US|United States)$/i,"")}).filter(Boolean).slice(-2).join(", ");
  var bits=[vName,place].filter(Boolean);
  [].slice.call(wh.childNodes).forEach(function(nd){if(nd.nodeType===3)nd.remove()});
  if(bits.length)wh.appendChild(document.createTextNode(" · "+bits.join(" · ")));
 })();

 /* ---- 0b. headlines: theirs, or neutral. The template's lines name its
    sample venue ("coming to the desert"), which is wrong for most couples ---- */
 var HL=(LIVE&&LS.headlines)||{};
 (function(){
  if(!LIVE)return;
  var set=function(el,t){if(el&&t)el.textContent=t};
  var dayH=document.querySelector(".dayg");dayH=dayH&&secOf(dayH);dayH=dayH&&dayH.querySelector(".center h2");
  set(dayH,HL.day||(vName?"The day, at "+vName+".":"How the day unfolds."));
  set(document.querySelector("#rsvpSec h2"),HL.rsvp||"Will you join us?");
  set(document.querySelector(".mthanks .lede"),HL.thanks||"Thank you for celebrating with us.");
  if(HL.story&&LS.story)set(document.querySelector(".split .txt h2"),HL.story);
  if(HL.gallery)set(document.querySelector(".galhead h2"),HL.gallery);
  /* the header lines, unless the day itself (or after) already rewrote them */
  if(!document.body.classList.contains("married")){
   var eb=document.querySelector("[data-eyebrow]"),cl=document.querySelector("[data-cdlabel]");
   var days={};(LS.events||[]).forEach(function(e){if(e&&e.dateIso)days[e.dateIso]=1});if(LS.dateIso)days[LS.dateIso]=1;
   var nd=Object.keys(days).length;
   var FIX={"Black tie · New Year’s Eve":"Black tie","Black tie · New Year's Eve":"Black tie","days until midnight":"days to go","Three days, one celebration":nd===3?"":(nd>1?nd+" days, one celebration":"One celebration")};
   [[eb,HL.eyebrow],[cl,HL.countdown]].forEach(function(x){var el=x[0];if(!el)return;var t=el.textContent.trim();
    if(/today|married|anniversary/i.test(t))return;
    if(x[1])el.textContent=x[1];else if(FIX[t])el.textContent=FIX[t]});
  }
 })();

 /* ---- 1. countdown: the hours tick too ---- */
 (function(){
  var iso=LIVE?LS.dateIso:"";var cdl=document.querySelector(".hero .cdline");if(!cdl)return;
  var when=null;
  if(/^\d{4}-\d{2}-\d{2}$/.test(iso||"")){
   when=new Date(iso+"T17:00:00");  /* the same moment the days count to */
  } else if(!LIVE){when=new Date(Date.now()+1000*(86400*112+3600*6+60*14))}
  if(!when||document.body.classList.contains("married"))return;
  var p=document.createElement("p");p.className="lzp-cdx";p.setAttribute("aria-hidden","true");after(cdl,p);
  var z=function(n){return String(n).padStart(2,"0")};
  var tickx=function(){var ms=when-Date.now();if(ms<=0){p.textContent=LIVE?"Today’s the day":"";return}
   if(ms>366*864e5){p.remove();return}
   var hh=Math.floor(ms%864e5/36e5),mm=Math.floor(ms%36e5/6e4),ss=Math.floor(ms%6e4/1e3);
   p.textContent=z(hh)+" hrs · "+z(mm)+" min · "+z(ss)+" sec"};
  tickx();setInterval(tickx,1000);
 })();

 /* ---- 2. hashtag ---- */
 var tag=String(LS.hashtag||"").replace(/^#+/,"");
 function chip(where){
  var b=document.createElement("button");b.type="button";b.className="lzp-chip";b.setAttribute("aria-label","Copy our hashtag #"+tag);
  b.innerHTML='<span>#'+esc(tag)+'</span><small>Copy</small>';
  b.addEventListener("click",function(){copy("#"+tag,"#"+tag+" copied — tag away")});
  return b;
 }
 if(tag){
  var hw=document.querySelector(".hero .wrap");
  if(hw){var hp=document.createElement("div");hp.appendChild(chip());hw.appendChild(hp)}
  var addWall=function(){var ph=document.getElementById("photos");if(!ph||ph.querySelector(".lzp-tagw"))return!!ph;
   var w=document.createElement("div");w.className="lzp-tagw";w.appendChild(chip());
   var c=ph.querySelector(".center")||ph.querySelector(".wrap");if(c)c.appendChild(w);return true};
  if(!addWall()){var mo=new MutationObserver(function(){if(addWall())mo.disconnect()});mo.observe(document.body,{childList:true,subtree:true});setTimeout(function(){mo.disconnect()},15000)}
 }

 /* ---- 3. our story in dates ---- */
 var anchor=secOf(document.querySelector(".split"));
 var ms=(LS.milestones||[]).filter(function(m){return m&&m.title});
 if(ms.length){
  var s3=section("Our story in dates","How we got here.");
  var ol=document.createElement("ol");ol.className="lzp-ms";
  ms.forEach(function(m){
   var li=document.createElement("li");li.className="lzp-mi";
   li.innerHTML='<div>'+(m.when?'<span class="lzp-mw">'+esc(m.when)+'</span>':'')+'<h3>'+esc(m.title)+'</h3>'+(m.text?'<p>'+esc(m.text)+'</p>':'')+'</div>'+(m.photo?'<button type="button" class="lzp-mp" aria-label="View photo" style="border:0;padding:0">'+img(m.photo,420,m.title)+'</button>':'');
   if(m.photo){li.querySelector(".lzp-mp").addEventListener("click",function(){viewer([m.photo],0)})}
   ol.appendChild(li);
  });
  s3.querySelector(".wrap").appendChild(ol);
  if(after(anchor,s3)){anchor=s3;reveal(s3)}
 }

 /* ---- 4. the wedding party ---- */
 var party=(LS.weddingParty||[]).filter(function(p){return p&&p.name});
 if(party.length){
  var s4=section("The wedding party",HL.party||"The people standing up with us.");
  var grid=document.createElement("div");grid.className="lzp-party";
  var initials=function(n){return n.replace(/^(rev|dr|mr|mrs|ms)\.?\s+/i,"").split(/\s+/).filter(Boolean).slice(0,2).map(function(w){return w[0]}).join("").toUpperCase()};
  party.forEach(function(p){
   var c=document.createElement("div");c.className="lzp-pc";c.dataset.side=p.side||"";
   c.innerHTML='<div class="lzp-ph">'+(p.photo?img(p.photo,320,p.name):esc(initials(p.name)))+'</div><span class="lzp-pn">'+esc(p.name)+'</span>'+(p.role?'<span class="lzp-pr">'+esc(p.role)+'</span>':'')+(p.note?'<span class="lzp-pt">'+esc(p.note)+'</span>':'');
   grid.appendChild(c);
  });
  var hasA=party.some(function(p){return p.side==="a"}),hasB=party.some(function(p){return p.side==="b"});
  var w4=s4.querySelector(".wrap");
  if(hasA&&hasB){
   var sides=LS.partySides||[];
   var la=sides[0]||(n1?n1+"’s side":"Side one"),lb=sides[1]||(n2?n2+"’s side":"Side two");
   var pick=function(i){var want=["","a","b"][i];[].forEach.call(grid.children,function(c){c.hidden=!!want&&c.dataset.side!==want&&c.dataset.side!==""})};
   w4.appendChild(tabs(["Everyone",la,lb],pick,0));
  }
  w4.appendChild(grid);
  if(after(anchor,s4))reveal(s4);
 }

 /* ---- 5. gallery: full-screen viewer, and every photo ---- */
 var lb=null,lbList=[],lbI=0;
 function viewer(list,i){
  lbList=list;lbI=i;
  if(!lb){
   lb=document.createElement("div");lb.className="lzp-lb";lb.setAttribute("role","dialog");lb.setAttribute("aria-modal","true");lb.setAttribute("aria-label","Photo viewer");
   lb.innerHTML='<img alt=""><button type="button" class="lzp-lbx" aria-label="Close">✕</button><button type="button" class="lzp-lbp" aria-label="Previous">‹</button><button type="button" class="lzp-lbn" aria-label="Next">›</button><p class="lzp-lbc"></p>';
   document.body.appendChild(lb);
   lb.querySelector(".lzp-lbx").addEventListener("click",close);
   lb.querySelector(".lzp-lbp").addEventListener("click",function(e){e.stopPropagation();go(-1)});
   lb.querySelector(".lzp-lbn").addEventListener("click",function(e){e.stopPropagation();go(1)});
   lb.addEventListener("click",function(e){if(e.target===lb)close()});
   var x0=null;lb.addEventListener("pointerdown",function(e){x0=e.clientX});
   lb.addEventListener("pointerup",function(e){if(x0===null)return;var dx=e.clientX-x0;x0=null;if(Math.abs(dx)>45)go(dx<0?1:-1)});
   document.addEventListener("keydown",function(e){if(!lb.classList.contains("on"))return;if(e.key==="Escape")close();else if(e.key==="ArrowRight")go(1);else if(e.key==="ArrowLeft")go(-1)});
  }
  show();lb.style.display="flex";document.documentElement.style.overflow="hidden";
  requestAnimationFrame(function(){lb.classList.add("on")});lb.querySelector(".lzp-lbx").focus({preventScroll:true});
 }
 function show(){var im=lb.querySelector("img"),u=lbList[lbI];im.style.opacity="0";im.onload=function(){im.style.opacity="1"};im.onerror=function(){if(im.src!==u)im.src=u};im.src=sized(u,2000);
  var one=lbList.length<2;lb.querySelector(".lzp-lbp").style.visibility=one?"hidden":"";lb.querySelector(".lzp-lbn").style.visibility=one?"hidden":"";
  lb.querySelector(".lzp-lbc").textContent=one?"":(lbI+1)+" / "+lbList.length}
 function go(d){if(lbList.length<2)return;lbI=(lbI+d+lbList.length)%lbList.length;show()}
 function close(){lb.classList.remove("on");setTimeout(function(){lb.style.display="none"},250);if(!document.querySelector(".lzp-mz.on"))document.documentElement.style.overflow=""}
 var figs=[].slice.call(document.querySelectorAll(".gal figure")).filter(function(f){return f.style.display!=="none"&&f.querySelector("img")});
 var all=LIVE?(LS.siteGallery||[]).filter(function(u){return typeof u==="string"&&/^https?:/.test(u)}):figs.map(function(f){return f.querySelector("img").src});
 if(figs.length&&all.length){
  figs.forEach(function(f,i){f.classList.add("lzp-z");f.setAttribute("tabindex","0");f.setAttribute("role","button");f.setAttribute("aria-label","View photo "+(i+1));
   var open=function(){viewer(all,Math.min(i,all.length-1))};
   f.addEventListener("click",open);f.addEventListener("keydown",function(e){if(e.key==="Enter"||e.key===" "){e.preventDefault();open()}})});
  if(all.length>figs.length){
   var aw=document.createElement("div");aw.className="lzp-allw";
   aw.innerHTML='<button type="button" class="lzp-btn">See all '+all.length+' photos</button>';
   var gal=document.querySelector(".gal");gal.parentNode.insertBefore(aw,gal.nextSibling);
   var mz=null;
   aw.querySelector("button").addEventListener("click",function(){
    if(!mz){
     mz=document.createElement("div");mz.className="lzp-mz";mz.setAttribute("role","dialog");mz.setAttribute("aria-modal","true");mz.setAttribute("aria-label","All photos");
     mz.innerHTML='<div class="lzp-mzh"><b>'+esc([n1,n2].filter(Boolean).join(" & ")||"Our photos")+'</b><button type="button" class="lzp-btn">Close</button></div><div class="lzp-mzg"></div>';
     var g=mz.querySelector(".lzp-mzg");
     all.forEach(function(u,i){var b=document.createElement("button");b.type="button";b.setAttribute("aria-label","Photo "+(i+1));b.innerHTML=img(u,720,"");b.addEventListener("click",function(){viewer(all,i)});g.appendChild(b)});
     mz.querySelector(".lzp-mzh .lzp-btn").addEventListener("click",function(){mz.classList.remove("on");setTimeout(function(){mz.style.display="none"},300);document.documentElement.style.overflow=""});
     document.addEventListener("keydown",function(e){if(e.key==="Escape"&&mz.classList.contains("on")&&!(lb&&lb.classList.contains("on"))){mz.querySelector(".lzp-mzh .lzp-btn").click()}});
     document.body.appendChild(mz);
    }
    mz.style.display="block";mz.scrollTop=0;document.documentElement.style.overflow="hidden";requestAnimationFrame(function(){mz.classList.add("on")});
   });
  }
 }

 /* ---- 6. the weekend in day tabs ---- */
 var evsec=document.getElementById("events"),evg=evsec&&evsec.querySelector(".evg");
 var evs=(LS.events||[]).filter(function(e){return e&&e.name});
 if(evg&&evs.length===evg.children.length){
  var days=[];evs.forEach(function(e){if(e.dateIso&&days.indexOf(e.dateIso)<0)days.push(e.dateIso)});days.sort();
  if(days.length>1){
   [].forEach.call(evg.children,function(c,i){c.dataset.day=evs[i].dateIso||""});
   var today=new Date();var ti=days.indexOf(today.getFullYear()+"-"+String(today.getMonth()+1).padStart(2,"0")+"-"+String(today.getDate()).padStart(2,"0"));
   var lab=function(d){return new Date(d+"T12:00:00").toLocaleDateString("en-US",{weekday:"short",month:"short",day:"numeric"})};
   var pickDay=function(i){[].forEach.call(evg.children,function(c){c.hidden=!!c.dataset.day&&c.dataset.day!==days[i];c.style.display=c.hidden?"none":""})};
   evg.parentNode.insertBefore(tabs(days.map(lab),pickDay,ti<0?0:ti),evg);
   var eh=evsec.querySelector("h2");if(eh)eh.textContent=days.length===2?"Two days to celebrate.":days.length+" days to celebrate.";
  }
 }

 /* ---- 7. where to stay, getting there ---- */
 var hotels=(LS.hotels||[]).filter(function(h){return h&&h.name});
 var airports=(LS.airports||[]).filter(function(a){return a&&a.name});
 var drive=String(LS.drivingNotes||"").trim();
 var hasVenue=!!(LS.venueName||LS.venueAddress);
 var stayAnchor=evsec||secOf(document.querySelector(".dayg"))||anchor;
 function hotelCard(h,auto){
  var c=document.createElement("div");c.className="lzp-hc"+(auto?"":" blk");
  var meta=auto?[h.kind,h.rating?"★ "+Number(h.rating).toFixed(1):"",h.price,h.miles!=null?h.miles+" mi from the venue":""]:[h.rate,h.deadline?"Book by "+h.deadline:""];
  meta=meta.filter(Boolean).join(" · ");
  var dir=h.address||h.name;
  c.innerHTML=(auto?'':'<span class="lzp-hk">'+(h.block!==false?"Room block":"Recommended")+'</span>')+'<h3>'+esc(h.name)+'</h3>'
   +(meta?'<span class="lzp-hm">'+esc(meta)+'</span>':'')+(h.address?'<span class="lzp-hm">'+esc(h.address)+'</span>':'')
   +(h.note?'<span class="lzp-hm">'+esc(h.note)+'</span>':'')
   +(h.code?'<button type="button" class="lzp-code" aria-label="Copy the booking code"><span>Code <b>'+esc(h.code)+'</b></span><small>Tap to copy</small></button>':'')
   +'<div class="lzp-ha"></div>';
  if(h.code)c.querySelector(".lzp-code").addEventListener("click",function(){copy(h.code,"Code copied — paste it when you book")});
  var acts=c.querySelector(".lzp-ha");
  var book=h.url||(auto&&h.maps)||"";
  if(book){var b=document.createElement("a");b.className="lzp-btn solid";b.href=book;b.target="_blank";b.rel="noopener";b.textContent=h.url?"Book":"View";acts.appendChild(b)}
  var d=document.createElement("a");d.className="lzp-btn";d.href="https://www.google.com/maps/search/?api=1&query="+encodeURIComponent(dir);d.target="_blank";d.rel="noopener";d.textContent="Directions";acts.appendChild(d);
  if(h.phone){var t=document.createElement("a");t.className="lzp-btn";t.href="tel:"+h.phone.replace(/[^0-9+]/g,"");t.textContent="Call";acts.appendChild(t)}
  return c;
 }
 function buildStay(autoHotels,autoAirports){
  var hs=hotels.length?hotels:autoHotels,aps=airports.length?airports:autoAirports;
  if(!hs.length&&!aps.length&&!drive)return;
  var s7=section("Where to stay",HL.stay||((LS.events||[]).length?"Rest up. It’s a big weekend.":"Rest up. It’s a big day."),hotels.length?"":(hs.length?"Hotels near the venue that guests rate well.":""));
  if(!hs.length){s7.querySelector(".k").textContent="Getting there";s7.querySelector("h2").textContent="Finding your way to us."}
  var w7=s7.querySelector(".wrap");
  if(hs.length){var hg=document.createElement("div");hg.className="lzp-hg";hs.forEach(function(h){hg.appendChild(hotelCard(h,!hotels.length))});w7.appendChild(hg)}
  if(aps.length||drive){
   var tv=document.createElement("div");tv.className="lzp-tv";
   if(hs.length)tv.innerHTML='<div class="center"><p class="k" style="margin-top:0">Getting there</p></div>';
   aps.forEach(function(a){
    var miles=a.miles!=null?a.miles+" mi from the venue":"";var dr=a.drive?"about "+(a.drive>=90?(Math.round(a.drive/30)/2)+" hr":a.drive+" min")+" by car":"";
    var el=document.createElement("a");el.className="lzp-ap";el.target="_blank";el.rel="noopener";
    el.href=a.maps||("https://www.google.com/maps/dir/?api=1&origin="+encodeURIComponent(a.name)+"&destination="+encodeURIComponent([LS.venueName,LS.venueAddress].filter(Boolean).join(", ")));
    el.innerHTML='<span class="lzp-apc">'+esc(a.code||"✈")+'</span><span class="lzp-apt"><b>'+esc(a.name)+'</b><span>'+esc([miles,dr,a.note].filter(Boolean).join(" · "))+'</span></span>';
    tv.appendChild(el);
   });
   if(drive){var dn=document.createElement("p");dn.className="lzp-dn";dn.textContent=drive;tv.appendChild(dn)}
   w7.appendChild(tv);
  }
  if((!hotels.length&&hs.length)||(!airports.length&&aps.length)){var f=document.createElement("p");f.className="lzp-fine";f.textContent="Places data © Google";w7.appendChild(f)}
  if(after(stayAnchor,s7))reveal(s7);
 }
 var wantAuto=hasVenue&&LS.stayAuto!==false&&(!hotels.length||!airports.length);
 if(wantAuto){
  fetch("https://meetlazo.com/api/stay?slug="+encodeURIComponent(LIVE?LS.slug:"demo")).then(function(r){return r.json()})
   .then(function(j){buildStay((j&&j.hotels)||[],(j&&j.airports)||[])}).catch(function(){buildStay([],[])});
 } else buildStay([],[]);
})();
</script>
""".replace("TAG", TAG)


def patch(name):
    p = ROOT / name / "index.html"
    s = p.read_text(encoding="utf-8")
    s = re.sub(rf"\n/\* ---- {TAG} ---- \*/.*?/\* ---- /{TAG} ---- \*/\n", "", s, flags=re.S)
    s = re.sub(rf"\n<script>\n/\* {TAG}:.*?</script>\n", "", s, flags=re.S)
    k = s.find("</style>")
    if k < 0:
        raise SystemExit(f"{name}: no <style>")
    s = s[:k] + CSS + s[k:]
    k = s.rfind("</body>")
    s = s[:k] + JS + s[k:]
    p.write_text(s, encoding="utf-8", newline="\n")
    print(f"  {name}: plus applied ({len(s):,} bytes)")


if __name__ == "__main__":
    for n in sys.argv[1:] or DESIGNS:
        patch(n)
