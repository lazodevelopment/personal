"""patch_live_templates.py - JC-LAZO-WWS-0929-LIVE
The couple site, live. One CSS block and one script (tagged, replaced on
re-runs) for _base.html and the 20 live templates:

  1. HOUR BY HOUR   weddingSites.timeline [{time,label,note,dur}] (mirrored
                    from the Day-of timeline by the dashboard) as a list after
                    "The day"; on the wedding day the current moment is marked
                    Now, the next one Next, and it re-checks every 30 s.
  2. THE FORECAST   inside 16 days, /api/w/{slug}/weather adds a card to the
                    venue list: high, sky, low, rain odds, sunset, one line.
  3. FIND YOUR SEAT weddingSites/{slug}/seating/main {guests:[{n,p,t,s}]}:
                    type a name, get the table, the seat and the tablemates.
  4. PERSONAL RSVP  ?i={guestId} reads weddingSites/{slug}/invites/{id} and
                    prefills the form (name, plus-ones allowed, meals); the
                    couple's mealOptions show as a dinner choice for everyone.
                    The RSVP carries meal / plusOnes / invite, so the dashboard
                    matches it to the guest instead of by name.
  5. THE TEAM       vendor credits link to the vendor's Lazo page and carry a
                    "Check your date" lead link when the publish found the id.
  6. THE GALLERY    weddingSites.galleryUrl replaces "Photos are coming" with
                    See the photos (+ Order prints for a Lazo gallery).
  7. TRANSLATION    a language pill (live sites only); text nodes go through
                    /api/translate in batches; English restores instantly.
  8. THE SLIDESHOW  ?wall=1 turns the page into a full-screen slideshow of the
                    guests' photos for a TV at the reception; refreshes itself.

  python wedding-websites\\patch_live_templates.py            # base + 20
  python wedding-websites\\patch_live_templates.py sage tide  # some
"""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIVE = ["sage", "noir", "dune", "fete", "tide", "flora", "atelier", "verona", "shore", "summit",
        "ranch", "starlit", "frost", "harvest", "aquarelle", "prism", "meadow", "gilded", "marigold", "papel", "peony"]
TAG = "JC-LAZO-WWS-0929-LIVE"

CSS = """
/* ---- JC-LAZO-WWS-0929-LIVE: hour by hour, forecast, seats, personal RSVP, team links, gallery, translation, slideshow ---- */
.tlx{list-style:none;padding:0;margin:clamp(26px,3.4vw,40px) auto 0;max-width:640px}
.tlx li{display:grid;grid-template-columns:96px 1fr;gap:4px 14px;padding:14px 12px;border-left:2px solid var(--line);position:relative}
.tlx li b{font-weight:500;color:var(--acc);letter-spacing:.06em;font-size:14px}
.tlx .tll{font-size:16px}.tlx .tln{grid-column:2;font-size:13.5px;color:var(--mut)}
.tlx li.done{opacity:.55}.tlx li.now{border-left-color:var(--acc);background:var(--panel)}
.tlx li.now::after,.tlx li.next::after{position:absolute;right:12px;top:12px;font-size:10px;letter-spacing:.3em;text-transform:uppercase}
.tlx li.now::after{content:"Now";color:var(--acc)}.tlx li.next::after{content:"Next";color:var(--mut)}
.seatf{max-width:420px;margin:22px auto 0}.seatf input{font:inherit;font-size:16px;padding:14px;border:1px solid var(--line);background:var(--panel);color:var(--ink);width:100%;text-align:center}
.seatr{display:grid;gap:10px;max-width:520px;margin:14px auto 0}
.seatc{background:var(--panel);border:1px solid var(--acc);padding:16px 18px;text-align:left}
.seatc b{display:block;font-size:16px;font-weight:500}.seatt{display:block;font-size:22px;line-height:1.2;color:var(--acc);margin-top:4px}.seatm{display:block;font-size:13px;color:var(--mut);margin-top:6px}
.meals,.plusrow{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.mealk{flex:0 0 100%;font-size:10.5px;letter-spacing:.3em;text-transform:uppercase;color:var(--acc)}
.meals label{border:1px solid var(--line);padding:10px 12px;font-size:13px;cursor:pointer}
.meals input{display:none}.meals label:has(input:checked){border-color:var(--acc);color:var(--acc)}
.plusrow label{font-size:14px}.plusrow select{font:inherit;padding:6px 8px;border:1px solid var(--line);background:var(--panel);color:var(--ink);margin-left:6px}
.vt a.vtn{text-decoration:none;border-bottom:1px solid var(--line)}.vt a.vtn:hover{border-color:var(--acc);color:var(--acc)}
.vtb{display:block;margin-top:8px;font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:var(--acc);text-decoration:none}
.galx{margin-top:22px}.galx a.r{display:inline-block;margin:6px 6px 0;border:1px solid var(--ink);padding:12px 24px;text-decoration:none;font-size:12px;letter-spacing:.3em;text-transform:uppercase}
.lzlang{position:fixed;top:12px;right:12px;z-index:45}
.lzlang label{display:inline-flex;align-items:center;gap:6px;background:var(--panel);border:1px solid var(--line);border-radius:999px;padding:6px 10px;font-size:13px;box-shadow:0 6px 18px rgba(0,0,0,.12)}
.lzlang select{border:0;background:transparent;font:inherit;color:var(--ink);outline:none;max-width:120px}
.lzlang.busy{opacity:.6}
body:not(.live) .lzlang{display:none}
html.lzwall,html.lzwall body{height:100%;overflow:hidden;background:#000}
html.lzwall body>*:not(.wallx){display:none!important}
.wallx{position:fixed;inset:0;background:#000}
.wallx .wa,.wallx .wb{position:absolute;inset:0;background:center/contain no-repeat #000;opacity:0;transition:opacity 1.2s ease}
.wallx .on{opacity:1;animation:wkb 8s ease-out forwards}
@keyframes wkb{from{transform:scale(1)}to{transform:scale(1.04)}}
.wallx .wcap{position:absolute;left:32px;bottom:28px;color:#fff;font-size:20px;letter-spacing:.1em;text-shadow:0 2px 12px rgba(0,0,0,.7)}
.wallx .wqr{position:absolute;right:32px;bottom:28px;color:#fff;text-align:right;text-shadow:0 2px 12px rgba(0,0,0,.7)}
.wallx .wqr b{display:block;font-size:14px;letter-spacing:.3em;text-transform:uppercase;opacity:.8}.wallx .wqr span{font-size:18px}
/* ---- /JC-LAZO-WWS-0929-LIVE ---- */
"""

JS = r"""
<script>
/* JC-LAZO-WWS-0929-LIVE: hour by hour, the forecast, find your seat, personal RSVPs, the team with links, the gallery hand-off, translation, the slideshow */
(function(){
 var LS=window.LAZO_SITE;if(!LS)return;
 var q=new URLSearchParams(location.search);
 var esc=function(t){return String(t||"").replace(/[<>&"]/g,function(c){return{"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"}[c]})};
 var FSB="https://firestore.googleapis.com/v1/projects/lazo-513ec/databases/(default)/documents/weddingSites/"+encodeURIComponent(LS.slug);
 var iso=LS.dateIso||"",hasDate=/^\d{4}-\d{2}-\d{2}$/.test(iso);
 var todayIs=hasDate&&new Date().toDateString()===new Date(iso+"T12:00:00").toDateString();
 var married=q.get("married")==="1"||(hasDate&&Date.now()>new Date(iso+"T17:00:00").getTime()+864e5);
 var framed=document.body.classList.contains("framed");
 function sec(html,cls){var s=document.createElement("section");if(cls)s.className=cls;s.innerHTML='<div class="wrap">'+html+'</div>';return s;}
 function before(el,node){if(node&&node.parentNode)node.parentNode.insertBefore(el,node);else{var f=document.querySelector("footer");f.parentNode.insertBefore(el,f);}}
 function after(el,node){if(node&&node.parentNode)node.parentNode.insertBefore(el,node.nextSibling);else before(el,null);}
 var daySec=(function(){var d=document.querySelector(".dayg");return d?d.closest("section"):null})();
 var rsvpSec=document.getElementById("rsvpSec");
 function hhmm(t){var m=/^(\d{1,2}):(\d{2})/.exec(t||"");if(!m)return null;return parseInt(m[1],10)*60+parseInt(m[2],10)}
 function pretty(t){var mm=hhmm(t);if(mm===null)return t||"";var h=Math.floor(mm/60),m=mm%60,ap=h>=12?"pm":"am";h=h%12||12;return h+":"+(m<10?"0":"")+m+" "+ap}

 /* ---- 1. the day, hour by hour ---- */
 if(!framed&&LS.timelineOn!==false&&LS.timeline&&LS.timeline.length&&!married){
  var tl=LS.timeline.slice().sort(function(a,b){return (hhmm(a.time)||0)-(hhmm(b.time)||0)});
  var s1=sec('<div class="center"><p class="k">Hour by hour</p><h2 style="margin:0 auto">'+(todayIs?"Today, as it happens.":"How the day will go.")+'</h2></div><ol class="tlx" id="tlx"></ol>',"tlsec");
  var ol=s1.querySelector("#tlx");
  tl.forEach(function(m){var li=document.createElement("li");li.innerHTML='<b></b><span class="tll"></span>'+(m.note?'<span class="tln"></span>':'');li.querySelector("b").textContent=pretty(m.time);li.querySelector(".tll").textContent=m.label;if(m.note)li.querySelector(".tln").textContent=m.note;ol.appendChild(li)});
  if(daySec)after(s1,daySec);else before(s1,rsvpSec);
  var mark=function(){
   if(!todayIs)return;
   var now=new Date(),cur=now.getHours()*60+now.getMinutes(),lis=ol.children,ci=-1;
   for(var i=0;i<tl.length;i++){var st=hhmm(tl[i].time);if(st!==null&&st<=cur)ci=i}
   for(var j=0;j<lis.length;j++){lis[j].classList.remove("now","next","done");if(j<ci)lis[j].classList.add("done");if(j===ci)lis[j].classList.add("now");if(j===ci+1)lis[j].classList.add("next")}
  };
  mark();if(todayIs)setInterval(mark,30000);
 }

 /* ---- 2. the forecast ---- */
 if(!framed&&hasDate&&daySec&&daySec.style.display!=="none"){
  var dOut=Math.round((new Date(iso+"T12:00:00").getTime()-Date.now())/864e5);
  if(dOut>=-1&&dOut<=15){
   fetch("https://meetlazo.com/api/w/"+encodeURIComponent(LS.slug)+"/weather").then(function(r){return r.json()}).then(function(j){
    var d=j&&j.day;if(!d)return;
    var vl=daySec.querySelector(".venlist");if(!vl)return;
    var card=document.createElement("div");card.className="ven wx";
    var ss=d.sunset?(function(t){var p=t.split(":"),h=parseInt(p[0],10),ap=h>=12?"pm":"am";return (h%12||12)+":"+p[1]+" "+ap})(d.sunset):"";
    card.innerHTML='<p class="k">The forecast</p><h3></h3><p></p><p class="dim"></p>';
    card.querySelector("h3").textContent=d.hi+"° and "+d.sky;card.querySelector("h3").style.textTransform="none";
    card.querySelectorAll("p")[1].textContent="Low of "+d.lo+"°"+(d.rain?" · "+d.rain+"% chance of rain":"")+(ss?" · sunset "+ss:"");
    card.querySelector(".dim").textContent=d.line||"";
    vl.appendChild(card);
   }).catch(function(){});
  }
 }

 /* ---- 3. find your seat ---- */
 if(!framed&&LS.seatingOn&&!married){
  var s3=sec('<div class="center"><p class="k">Your seat</p><h2 style="margin:0 auto">Find your table.</h2><p class="lede">Type your name as it was on the invitation.</p><div class="seatf"><input id="seatq" placeholder="Your name" autocomplete="name" maxlength="80"></div><div class="seatr" id="seatr"></div></div>',"seatsec");
  before(s3,rsvpSec);
  var seatP=null;
  var loadSeats=function(){if(seatP)return seatP;seatP=fetch(FSB+"/seating/main").then(function(r){return r.json()}).then(function(j){var f=j&&j.fields;if(!f||!f.guests)return[];return ((f.guests.arrayValue||{}).values||[]).map(function(v){var m=(v.mapValue||{}).fields||{};return{n:(m.n||{}).stringValue||"",p:(m.p||{}).stringValue||"",t:(m.t||{}).stringValue||"",s:(m.s&&m.s.integerValue!=null)?Number(m.s.integerValue):null}})}).catch(function(){return[]});return seatP};
  var seatq=s3.querySelector("#seatq"),seatr=s3.querySelector("#seatr");
  var norm=function(x){return String(x||"").toLowerCase().replace(/[^a-z0-9 ]+/g," ").replace(/\s+/g," ").trim()};
  var seatT;
  seatq.addEventListener("input",function(){clearTimeout(seatT);seatT=setTimeout(function(){
   var v=norm(seatq.value);if(v.length<2){seatr.innerHTML="";return}
   loadSeats().then(function(list){
    var words=v.split(" ");
    var hits=list.filter(function(g){var n=norm(g.n),p=norm(g.p);return words.every(function(w){return n.indexOf(w)>=0})||(p&&words.every(function(w){return p.indexOf(w)>=0}))}).slice(0,4);
    if(!hits.length){seatr.innerHTML='<p class="lede" style="margin:14px auto 0">We couldn’t find that name — try just your first or last name, or ask at the door.</p>';return}
    seatr.innerHTML="";
    hits.forEach(function(g){
     var mates=list.filter(function(o){return o.t&&o.t===g.t&&o!==g}).map(function(o){return o.n}).slice(0,12);
     var c=document.createElement("div");c.className="seatc";c.innerHTML='<b></b><span class="seatt"></span>'+(mates.length?'<span class="seatm"></span>':'');
     c.querySelector("b").textContent=g.n;
     c.querySelector(".seatt").textContent=g.t?(g.t+(g.s!=null&&g.s>=0?" · seat "+(g.s+1):"")):"No table yet — ask at the door";
     if(mates.length)c.querySelector(".seatm").textContent="With "+mates.join(", ");
     seatr.appendChild(c);
    });
   });
  },220)});
 }

 /* ---- 4. personal RSVP: ?i=token prefills; meals from the couple ---- */
 var rform=document.getElementById("rform");
 if(rform&&LS.rsvpOpen!==false){
  var token=q.get("i")||"";try{if(token)sessionStorage.setItem("lzinv",token);else token=sessionStorage.getItem("lzinv")||"";}catch(_){}
  if(!/^[A-Za-z0-9_-]{6,64}$/.test(token))token="";
  /* JC-LAZO-WWS-1016-MEALS: a meal, kid's meal and allergies for every person coming; nothing pre-picked */
  var MO=[];
  var mealBox=function(){
   var w=rform.querySelector(".meals");
   if(!w){w=document.createElement("div");w.className="meals";var song=rform.querySelector("[data-song]");rform.insertBefore(w,song||rform.querySelector("textarea"));}
   if(!document.getElementById("lzmp")){var st=document.createElement("style");st.id="lzmp";st.textContent=".meals .mp{flex:0 0 100%;display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding:8px 0 10px;border-top:1px solid var(--line)}.meals .mealk+.mp{border-top:0}.meals .mp .mpk{flex:0 0 100%;font-size:12px;opacity:.8}.meals .mp select,.meals .mp input[type=text]{display:block;flex:1 1 200px;min-width:0;margin:0}.meals .mp select{padding:12px 10px;border:1px solid var(--line);border-radius:0;background:transparent;color:inherit;font:inherit;font-size:13px}.meals .mp [data-a]{flex:1 1 100%}.meals .mp label{display:inline-flex;gap:6px;align-items:center;border:0;padding:4px 2px;font-size:13px}.meals .mp label input{display:inline-block;width:auto;margin:0}";document.head.appendChild(st);}
   return w;
  };
  var drawMeals=function(){
   var w=mealBox();
   var prev=[].slice.call(w.querySelectorAll(".mp")).map(function(b){return{n:(b.querySelector("[data-n]")||{}).value||"",m:(b.querySelector("select")||{}).value||"",k:!!(b.querySelector("[data-k]")||{}).checked,a:(b.querySelector("[data-a]")||{}).value||""}});
   var pn=rform.querySelector("#plusn");var n=1+(pn?(parseInt(pn.value,10)||0):0);
   w.innerHTML='<span class="mealk">'+(MO.length?'Dinner':'Dietary needs')+'</span>';
   for(var p=0;p<n;p++){
    var pv=prev[p]||{n:"",m:"",k:false,a:""};
    var b=document.createElement("div");b.className="mp";
    var k=document.createElement("span");k.className="mpk";k.textContent=p===0?(n>1?"You":"For you"):"Your guest"+(n>2?" "+p:"");b.appendChild(k);
    if(p>0){var ni=document.createElement("input");ni.type="text";ni.setAttribute("data-n","");ni.setAttribute("aria-label","Guest name");ni.placeholder="Their name (optional)";ni.maxLength=80;ni.value=pv.n;b.appendChild(ni);}
    if(MO.length){var s=document.createElement("select");s.setAttribute("aria-label","Meal");var o0=document.createElement("option");o0.value="";o0.textContent="Choose a meal\u2026";s.appendChild(o0);MO.forEach(function(o){var op=document.createElement("option");op.value=o;op.textContent=o;s.appendChild(op)});s.value=pv.m;b.appendChild(s);}
    var kl=document.createElement("label");var kc=document.createElement("input");kc.type="checkbox";kc.setAttribute("data-k","");kc.checked=pv.k;var ks=document.createElement("span");ks.textContent="Kid\u2019s meal";kl.appendChild(kc);kl.appendChild(ks);b.appendChild(kl);
    var ai=document.createElement("input");ai.type="text";ai.setAttribute("data-a","");ai.setAttribute("aria-label","Allergies or dietary needs");ai.placeholder="Allergies / dietary (optional)";ai.maxLength=120;ai.value=pv.a;b.appendChild(ai);
    w.appendChild(b);
   }
   var yes=rform.querySelector(".radio label:first-child input");w.style.display=!yes||yes.checked?"":"none";
  };
  var mealRow=function(opts){if(opts.length)MO=opts.slice(0,8);drawMeals();};
  mealRow((LS.mealOptions||[]).filter(Boolean));
  [].slice.call(rform.querySelectorAll(".radio input")).forEach(function(r){r.addEventListener("change",drawMeals)});
  if(token){
   fetch(FSB+"/invites/"+encodeURIComponent(token)).then(function(r){return r.ok?r.json():null}).then(function(j){
    var f=j&&j.fields;if(!f)return;
    var inv={name:(f.name||{}).stringValue||"",party:(f.party||{}).stringValue||"",plus:Number((f.plusOnes||{}).integerValue||0),meals:(((f.meals||{}).arrayValue||{}).values||[]).map(function(v){return v.stringValue||""}).filter(Boolean)};
    var ins=rform.querySelectorAll("input");
    if(inv.name&&ins[0]&&!ins[0].value)ins[0].value=inv.party&&inv.party!==inv.name?inv.party:inv.name;
    if(inv.meals.length)mealRow(inv.meals);
    if(inv.plus>0&&!rform.querySelector(".plusrow")){
     var pr=document.createElement("div");pr.className="plusrow";var opts="";for(var i=0;i<=inv.plus;i++)opts+='<option value="'+i+'">'+i+'</option>';
     pr.innerHTML='<span class="mealk">Guests</span><label>You may bring '+inv.plus+' guest'+(inv.plus===1?'':'s')+' — how many are coming with you? <select id="plusn">'+opts+'</select></label>';
     rform.insertBefore(pr,rform.querySelector(".meals")||rform.querySelector("[data-song]")||rform.querySelector("textarea"));
     pr.querySelector("select").addEventListener("change",drawMeals);
    }
    var hello=document.querySelector("#rsvpSec .lede");if(hello&&inv.name)hello.textContent="Hi "+inv.name.split(" ")[0]+" — "+hello.textContent.charAt(0).toLowerCase()+hello.textContent.slice(1);
   }).catch(function(){});
  }
  var _fetch=window.fetch;
  window.fetch=function(u,o){
   try{
    if(typeof u==="string"&&u.indexOf("/rsvps")>0&&o&&o.method==="POST"){
     var b=JSON.parse(o.body);
     var mps=[].slice.call(rform.querySelectorAll(".meals .mp"));
     if(mps.length&&b.fields.attending&&b.fields.attending.stringValue==="yes"){
      var ppl=mps.slice(0,10).map(function(m,i){var nn=i===0?((b.fields.name||{}).stringValue||""):((m.querySelector("[data-n]")||{}).value||"").trim();return{mapValue:{fields:{name:{stringValue:nn.slice(0,80)},meal:{stringValue:((m.querySelector("select")||{}).value||"").slice(0,80)},kid:{booleanValue:!!(m.querySelector("[data-k]")||{}).checked},allergies:{stringValue:((m.querySelector("[data-a]")||{}).value||"").trim().slice(0,120)}}}}});
      b.fields.meals={arrayValue:{values:ppl}};
      var m0=ppl[0].mapValue.fields.meal.stringValue;if(m0)b.fields.meal={stringValue:m0};
      var al=ppl.map(function(p,i){var f=p.mapValue.fields,a=f.allergies.stringValue;return a?(f.name.stringValue||(i?"Guest "+i:"Guest"))+": "+a:""}).filter(Boolean).join("; ");
      if(al)b.fields.allergies={stringValue:al.slice(0,290)};
     }
     var pn=rform.querySelector("#plusn");if(pn)b.fields.plusOnes={integerValue:String(parseInt(pn.value,10)||0)};
     if(token)b.fields.invite={stringValue:token};
     o.body=JSON.stringify(b);
    }
   }catch(_){}
   return _fetch.apply(this,arguments);
  };
 }

 /* ---- 5. the team, with links; 6. the gallery hand-off ---- */
 document.addEventListener("DOMContentLoaded",function(){
  var vt=(LS.vendorTeam||[]).filter(function(v){return v&&v.name});
  var grid=document.querySelector(".vtg");
  if(grid&&vt.some(function(v){return v.url||v.vendorId})){
   grid.innerHTML="";
   vt.forEach(function(v){
    var d=document.createElement("div");d.className="vt";
    var k=document.createElement("span");k.className="vtk";k.textContent=v.category||"";d.appendChild(k);
    var n=document.createElement(v.url?"a":"span");n.className="vtn";n.textContent=v.name;if(v.url){n.href=v.url;n.target="_blank";n.rel="noopener"}d.appendChild(n);
    if(v.vendorId&&/^[A-Za-z0-9_-]{3,120}$/.test(v.vendorId)){var b=document.createElement("a");b.className="vtb";b.href="https://meetlazo.com/lead/"+v.vendorId+"?src=site";b.target="_blank";b.rel="noopener";b.textContent="Check your date →";d.appendChild(b)}
    grid.appendChild(d);
   });
   var vtc=grid.parentNode.querySelector(".vtc");if(vtc)vtc.textContent="Found & booked on Lazo · planning your own? They’re a tap away";
  }
  if(LS.galleryUrl){
   var th=document.querySelector(".mthanks .card");
   if(th){var ps=th.querySelectorAll("p.lede");var last=ps[ps.length-1];
    var isLazo=/^https:\/\/meetlazo\.com\/g\/[a-z0-9-]+\/?$/.test(LS.galleryUrl);
    var box=document.createElement("p");box.className="galx";
    var a=document.createElement("a");a.className="r";a.href=LS.galleryUrl;a.target="_blank";a.rel="noopener";a.textContent="See the photos";box.appendChild(a);
    if(isLazo){var s=document.createElement("a");s.className="r";s.href=LS.galleryUrl.replace(/\/?$/,"/store/");s.target="_blank";s.rel="noopener";s.textContent="Order prints";box.appendChild(s)}
    if(last){last.textContent="The photos are in.";last.parentNode.insertBefore(box,last.nextSibling)}else th.appendChild(box);
   }
  }
 });

 /* ---- 7. translation ---- */
 if(!framed&&LS.translateOn!==false){
  var LN={es:"Español",fr:"Français",pt:"Português",de:"Deutsch",it:"Italiano",hi:"हिन्दी",zh:"中文",ja:"日本語",ko:"한국어",vi:"Tiếng Việt",tl:"Tagalog",ar:"العربية",ru:"Русский",pl:"Polski",he:"עברית",el:"Ελληνικά",tr:"Türkçe",nl:"Nederlands",sv:"Svenska",uk:"Українська"};
  var pill=document.createElement("div");pill.className="lzlang";
  var opts='<option value="en">English</option>';Object.keys(LN).forEach(function(k){opts+='<option value="'+k+'">'+LN[k]+'</option>'});
  pill.innerHTML='<label><span aria-hidden="true">🌐</span><select aria-label="Language">'+opts+'</select></label>';
  document.body.appendChild(pill);
  var sel=pill.querySelector("select"),orig=new Map();
  var nodes=function(){var out=[],w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT,{acceptNode:function(n){var p=n.parentNode;if(!p||/^(SCRIPT|STYLE|SELECT|OPTION|TEXTAREA|CODE|PRE)$/.test(p.nodeName))return NodeFilter.FILTER_REJECT;if(p.closest&&p.closest(".lzlang,.junep,.demo-bar,.cd,h1,.wallx,.lzsong,.seatr"))return NodeFilter.FILTER_REJECT;if(!/[A-Za-z]{2}/.test(n.nodeValue))return NodeFilter.FILTER_REJECT;return NodeFilter.FILTER_ACCEPT}});var n;while((n=w.nextNode()))out.push(n);
   document.querySelectorAll("input[placeholder],textarea[placeholder]").forEach(function(i){out.push({ph:i})});return out};
  var apply=function(lang){
   var list=nodes();
   if(lang==="en"){list.forEach(function(n){if(n.ph){if(orig.has(n.ph))n.ph.placeholder=orig.get(n.ph)}else if(orig.has(n))n.nodeValue=orig.get(n)});document.documentElement.lang="en";return}
   var texts=[],refs=[];
   list.forEach(function(n){var t=n.ph?(orig.get(n.ph)||n.ph.placeholder):(orig.get(n)||n.nodeValue);var tt=t.trim();if(!tt)return;if(n.ph){if(!orig.has(n.ph))orig.set(n.ph,n.ph.placeholder)}else if(!orig.has(n))orig.set(n,n.nodeValue);texts.push(tt);refs.push([n,t])});
   var uniq=[],idx={};texts.forEach(function(t){if(idx[t]==null){idx[t]=uniq.length;uniq.push(t)}});
   pill.classList.add("busy");
   var batches=[];for(var i=0;i<uniq.length;i+=200)batches.push(uniq.slice(i,i+200));
   Promise.all(batches.map(function(b){return fetch("https://meetlazo.com/api/translate",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({lang:lang,texts:b})}).then(function(r){return r.json()}).then(function(j){return (j&&j.texts)||b}).catch(function(){return b})})).then(function(parts){
    var tr=[].concat.apply([],parts);
    refs.forEach(function(p,k){var n=p[0],raw=p[1],t=tr[idx[texts[k]]]||texts[k];var lead=raw.match(/^\s*/)[0],tail=raw.match(/\s*$/)[0];if(n.ph)n.ph.placeholder=t;else n.nodeValue=lead+t+tail});
    document.documentElement.lang=lang;
   }).then(function(){pill.classList.remove("busy")},function(){pill.classList.remove("busy")});
  };
  sel.addEventListener("change",function(){var l=sel.value;try{localStorage.setItem("lzlang",l)}catch(_){}apply(l);setTimeout(function(){if(sel.value===l&&l!=="en")apply(l)},2500)});
  var saved="";try{saved=localStorage.getItem("lzlang")||""}catch(_){}
  if(saved&&LN[saved]){sel.value=saved;setTimeout(function(){apply(saved)},900)}
 }

 /* ---- 8. the slideshow: ?wall=1 on a TV at the reception ---- */
 if(q.get("wall")==="1"){
  document.documentElement.classList.add("lzwall");
  var W=document.createElement("div");W.className="wallx";W.innerHTML='<div class="wa"></div><div class="wb"></div><div class="wcap"></div><div class="wqr"><b>Add yours</b><span></span></div>';
  W.querySelector(".wqr span").textContent="meetlazo.com/w/"+LS.slug;
  document.body.appendChild(W);
  var list=[],i=-1,front=true,API="https://meetlazo.com/api/w/"+encodeURIComponent(LS.slug)+"/photos";
  var load=function(){return fetch(API).then(function(r){return r.json()}).then(function(j){var n=(j&&j.photos)||[];if(n.length!==list.length){var seen=list.length;list=n;if(seen)i=-1;}}).catch(function(){})};
  var show=function(){
   if(!list.length){W.querySelector(".wcap").textContent="Waiting for the first photo — scan the card on your table.";return}
   i=(i+1)%list.length;var p=list[i];
   var el=W.querySelector(front?".wb":".wa");el.style.backgroundImage='url("'+p.url.replace(/"/g,"")+'")';el.classList.add("on");W.querySelector(front?".wa":".wb").classList.remove("on");front=!front;
   W.querySelector(".wcap").textContent=[p.name,p.caption].filter(Boolean).join(" · ");
  };
  load().then(function(){show();setInterval(show,7000);setInterval(load,45000)});
 }
})();
</script>
"""


def strip(s):
    s = re.sub(rf"\n/\* ---- {TAG}:.*?/\* ---- /{TAG} ---- \*/\n", "\n", s, flags=re.S)
    s = re.sub(rf"\n<script>\n/\* {TAG}:.*?</script>\n", "\n", s, flags=re.S)
    return s


def patch(path):
    s = strip(path.read_text(encoding="utf-8"))
    k = s.find("</style>")
    if k < 0:
        raise SystemExit(f"{path}: no <style>")
    s = s[:k] + CSS + s[k:]
    k = s.rfind("</body>")
    s = s[:k] + JS + s[k:]
    path.write_text(s, encoding="utf-8", newline="\n")
    print(f"  {path.relative_to(ROOT)}: live ({len(s):,} bytes)")


if __name__ == "__main__":
    names = sys.argv[1:] or LIVE
    if not sys.argv[1:]:
        patch(ROOT / "_base.html")
    for n in names:
        p = ROOT / n / "index.html"
        if not p.exists():
            raise SystemExit(f"no template {n}")
        patch(p)
