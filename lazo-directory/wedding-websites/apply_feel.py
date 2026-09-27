"""apply_feel.py - JC-LAZO-WWS-0915-FEEL
Gives every wedding-website template the v4 feel and the couple's song.
Idempotent: each block is marked and replaced in place on re-runs.

  python wedding-websites\\apply_feel.py            # all templates
  python wedding-websites\\apply_feel.py shore tide # some

FEEL (CSS, appended to the template's first <style>):
  - everything pressable answers on pointer-down and settles on release
  - reveals use one critically-damped easing, siblings a beat apart
  - headlines balance their line breaks; photos fade in as they load
  - the June button breathes once when it appears; honours Reduce Motion
NEARBY (script): a "While you're in town" section built from
/api/nearby?slug= - eat & drink, coffee, things to do around the
venue, the couple's own favourites first. Demos show a sample.
SONG (script before </body>): if the site doc carries `song`, a small
player rides in the bottom-left corner: the artwork turns like a record
while it plays, the title and artist beside it. Browsers will not start
sound without a gesture, so it tries once and otherwise waits for the
guest's first tap or key anywhere on the page, then fades the song in.
The guest can pause it; that choice is remembered for the visit.
"""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALL = [p.name for p in ROOT.iterdir() if p.is_dir() and (p / "index.html").exists() and not p.name.startswith("_")]

FEEL_TAG = "JC-LAZO-WWS-0915-FEEL"
NEARBY_TAG = "JC-LAZO-WWS-0915-NEARBY"
SONG_TAG = "JC-LAZO-WWS-0915-SONG"

FEEL_CSS = f"""
/* ---- {FEEL_TAG}: the feel ---- */
:root{{--lz-out:cubic-bezier(.16,1,.3,1)}}
h1,h2,h3{{text-wrap:balance}}
.lede,.faq p,.chap p,.ven p{{text-wrap:pretty}}
button.go,.reg a.r,.reg-link,.addcal,.demo-bar a.solid,.gbf button,.radio label,.ocard a,.junebtn,.junep .jf button,.faq summary,.demo-bar button{{transition:transform .26s var(--lz-out),background-color .2s ease,color .2s ease,border-color .2s ease,box-shadow .26s var(--lz-out)}}
button.go:active,.reg a.r:active,.reg-link:active,.addcal:active,.demo-bar a.solid:active,.gbf button:active,.ocard a:active,.junep .jf button:active{{transform:scale(.97);transition-duration:.09s}}
.radio label:active,.faq summary:active{{transform:scale(.985);transition-duration:.09s}}
.junebtn:active{{transform:scale(.92);transition-duration:.09s}}
.ven,.chap,.vt,.gbn,.mthanks .card,form,.ocard{{transition:transform .3s var(--lz-out),box-shadow .3s var(--lz-out),border-color .2s ease}}
@media(hover:hover) and (pointer:fine){{
 .ven:hover,.chap:hover,.vt:hover{{transform:translateY(-2px);box-shadow:0 18px 40px -22px rgba(0,0,0,.28)}}
 .junebtn:hover{{transform:translateY(-2px)}}
}}
.rv{{transition:opacity .9s var(--lz-out),transform .9s var(--lz-out)}}
.gal figure:nth-child(2).rv{{transition-delay:.08s}}.gal figure:nth-child(3).rv{{transition-delay:.16s}}
img[loading=lazy]{{transition:opacity .5s ease}}img[loading=lazy][data-lzf]{{opacity:0}}
@keyframes lzbreathe{{0%{{transform:scale(.6);opacity:0}}60%{{transform:scale(1.04);opacity:1}}100%{{transform:none}}}}
.junebtn{{animation:lzbreathe .7s var(--lz-out) both;animation-delay:1.2s}}
@media(prefers-reduced-motion:reduce){{.junebtn{{animation:none}}img[loading=lazy][data-lzf]{{opacity:1}}.rv{{transition:none}}}}
/* the couple's song */
.oursong{{position:fixed;left:16px;bottom:16px;z-index:45;display:flex;align-items:center;gap:10px;max-width:min(78vw,300px);padding:6px 14px 6px 6px;border-radius:999px;background:var(--panel,#fff);color:var(--ink,#222);border:1px solid var(--line,#ddd);box-shadow:0 14px 34px -14px rgba(0,0,0,.35),0 1px 2px rgba(0,0,0,.08);cursor:pointer;font-family:inherit;text-align:left;transition:transform .26s var(--lz-out),box-shadow .26s var(--lz-out),opacity .4s ease;animation:lzbreathe .7s var(--lz-out) both;animation-delay:.9s}}
.oursong:active{{transform:scale(.97);transition-duration:.09s}}
.oursong .disc{{position:relative;width:42px;height:42px;border-radius:50%;flex:0 0 auto;background:#1a1a1a center/cover;box-shadow:inset 0 0 0 1px rgba(255,255,255,.15),0 2px 6px rgba(0,0,0,.25);overflow:hidden}}
.oursong .disc::after{{content:"";position:absolute;left:50%;top:50%;width:8px;height:8px;margin:-4px 0 0 -4px;border-radius:50%;background:var(--panel,#fff);box-shadow:0 0 0 2px rgba(0,0,0,.35)}}
.oursong.playing .disc{{animation:lzspin 3.2s linear infinite}}
@keyframes lzspin{{to{{transform:rotate(360deg)}}}}
.oursong .tx{{min-width:0;line-height:1.2}}
.oursong .t{{display:block;font-size:12.5px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.oursong .a{{display:block;font-size:11px;color:var(--mut,#777);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.oursong .h{{display:block;font-size:10px;letter-spacing:.18em;text-transform:uppercase;color:var(--acc,#555);margin-top:2px}}
.oursong .pp{{width:28px;height:28px;border-radius:50%;flex:0 0 auto;border:1px solid var(--line,#ddd);display:flex;align-items:center;justify-content:center;color:var(--acc,#555);font-size:11px}}
.oursong.playing .pp::before{{content:"\\2016"}}.oursong:not(.playing) .pp::before{{content:"\\25B6";margin-left:2px}}
.oursong.off{{opacity:.7}}
@media(prefers-reduced-motion:reduce){{.oursong,.oursong.playing .disc{{animation:none}}}}
body.framed .oursong{{display:none}}
@media(max-width:640px){{.oursong{{bottom:14px;left:12px;max-width:min(70vw,260px)}}.eyebrow{{letter-spacing:.28em;font-size:10.5px}}.where{{letter-spacing:.12em;font-size:11.5px}}.cdline{{letter-spacing:.22em;font-size:11.5px}}}}
/* things to do around the venue */
.nbsec .nbgroup{{margin-top:clamp(26px,3.4vw,42px)}}
.nbh{{font-size:10.5px;letter-spacing:.34em;text-transform:uppercase;color:var(--acc);margin:0 0 14px}}
.nbg{{display:grid;gap:12px}}
@media(min-width:760px){{.nbg{{grid-template-columns:1fr 1fr}}}}
.nbc{{display:flex;gap:16px;align-items:flex-start;justify-content:space-between;background:var(--panel);border:1px solid var(--line);padding:16px 18px;text-decoration:none;color:inherit;transition:transform .3s var(--lz-out),box-shadow .3s var(--lz-out),border-color .2s ease}}
.nbc:active{{transform:scale(.985);transition-duration:.09s}}
@media(hover:hover) and (pointer:fine){{.nbc:hover{{transform:translateY(-2px);border-color:var(--acc);box-shadow:0 18px 40px -22px rgba(0,0,0,.28)}}}}
.nbtx{{min-width:0}}
.nbn{{display:block;font-size:15.5px;font-weight:500;line-height:1.25}}
.nbm{{display:block;font-size:12.5px;color:var(--mut);margin-top:4px;line-height:1.45}}
.nbr{{flex:0 0 auto;text-align:right;font-size:12.5px;color:var(--acc);white-space:nowrap;font-weight:500}}
.nbr small{{display:block;color:var(--mut);font-weight:400;font-size:11.5px;margin-top:3px}}
.nbc.nbpick{{border-color:var(--acc)}}
.nbf{{margin-top:22px;font-size:10px;letter-spacing:.24em;text-transform:uppercase;color:var(--mut);text-align:center}}
/* ---- /{FEEL_TAG} ---- */
"""

SONG_JS = f"""
<script>
/* {SONG_TAG}: the couple's song */
(function(){{
 var LS=window.LAZO_SITE;if(!LS||!LS.song||!LS.song.src)return;
 if(document.body.classList.contains("framed"))return;
 var S=LS.song,reduce=false;try{{reduce=matchMedia("(prefers-reduced-motion: reduce)").matches;}}catch(e){{}}
 var a=new Audio();a.preload="auto";a.src=S.src;a.loop=!!S.loop;a.volume=0;
 var el=document.createElement("button");el.type="button";el.className="oursong";el.setAttribute("aria-label","Our song");
 var esc=function(s){{return String(s||"").replace(/[<>&"]/g,function(c){{return{{"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"}}[c]}})}};
 el.innerHTML='<span class="disc"'+(S.art?' style="background-image:url(&quot;'+esc(S.art)+'&quot;)"':'')+'></span><span class="tx"><span class="t">'+esc(S.title||"Our song")+'</span><span class="a">'+esc(S.artist||"")+'</span><span class="h" data-h>Tap for our song</span></span><span class="pp" aria-hidden="true"></span>';
 document.body.appendChild(el);
 var hint=el.querySelector("[data-h]"),fade=null,armed=false,started=false;
 function setHint(t){{if(hint)hint.textContent=t;}}
 function fadeTo(v,ms){{clearInterval(fade);var steps=Math.max(1,Math.round(ms/40)),i=0,from=a.volume;fade=setInterval(function(){{i++;a.volume=Math.max(0,Math.min(1,from+(v-from)*(i/steps)));if(i>=steps)clearInterval(fade);}},40);}}
 function play(){{var p=a.play();if(p&&p.then)p.then(function(){{started=true;el.classList.add("playing");setHint("Our song");fadeTo(.9,reduce?0:1400);try{{sessionStorage.removeItem("lzsongoff");}}catch(e){{}}}}).catch(function(){{arm();}});}}
 function pause(){{fadeTo(0,reduce?0:500);setTimeout(function(){{a.pause();}},reduce?0:520);el.classList.remove("playing");el.classList.add("off");setHint("Paused \\u00b7 tap to play");try{{sessionStorage.setItem("lzsongoff","1");}}catch(e){{}}}}
 function arm(){{if(armed)return;armed=true;setHint("Tap anywhere for our song");
  var go=function(){{document.removeEventListener("pointerdown",go,true);document.removeEventListener("keydown",go,true);if(!el.classList.contains("playing"))play();}};
  document.addEventListener("pointerdown",go,true);document.addEventListener("keydown",go,true);}}
 el.addEventListener("click",function(e){{e.stopPropagation();if(el.classList.contains("playing"))pause();else{{el.classList.remove("off");play();}}}});
 a.addEventListener("ended",function(){{el.classList.remove("playing");setHint("Play it again");}});
 a.addEventListener("error",function(){{el.remove();}});
 var off=false;try{{off=sessionStorage.getItem("lzsongoff")==="1";}}catch(e){{}}
 if(off){{el.classList.add("off");setHint("Tap to play");}}
 else if(S.autoplay!==false){{play();}}
 else{{setHint("Tap for our song");}}
}})();
</script>
"""

JS = '\n<script>\n/* NEARBY_TAG: things for guests to do around the venue */\n(function(){\n if(document.body.classList.contains("framed"))return;\n var LS=window.LAZO_SITE||null;\n var slug=LS?LS.slug:"demo";                         /* the demos show a sample */\n if(LS&&LS.nearbyOn===false)return;\n if(LS&&!LS.venueAddress&&!LS.venueName)return;\n var esc=function(t){return String(t||"").replace(/[<>&"]/g,function(c){return{"<":"&lt;",">":"&gt;","&":"&amp;",\'"\':"&quot;"}[c]})};\n var mapsFor=function(p){return p.maps||("https://www.google.com/maps/search/?api=1&query="+encodeURIComponent(p.name+" "+((LS&&LS.venueAddress)||"")))};\n function card(p,pick){\n  var meta=[p.kind,p.price,p.blurb].filter(Boolean).join(" \\u00b7 ");\n  var right="";\n  if(p.rating)right+="\\u2605 "+p.rating.toFixed(1);\n  if(p.miles!==null&&p.miles!==undefined)right+="<small>"+p.miles+" mi</small>";\n  return \'<a class="nbc\'+(pick?" nbpick":"")+\'" href="\'+esc(mapsFor(p))+\'" target="_blank" rel="noopener">\'\n   +\'<span class="nbtx"><span class="nbn">\'+esc(p.name)+\'</span>\'+(meta?\'<span class="nbm">\'+esc(meta)+\'</span>\':\'\')+\'</span>\'\n   +(right?\'<span class="nbr">\'+right+\'</span>\':\'\')+\'</a>\';\n }\n function group(label,cards){return \'<div class="nbgroup"><p class="nbh">\'+esc(label)+\'</p><div class="nbg">\'+cards+\'</div></div>\'}\n fetch("https://meetlazo.com/api/nearby?slug="+encodeURIComponent(slug))\n  .then(function(r){return r.json()})\n  .then(function(j){\n   var groups=(j&&j.groups)||[];\n   var picks=((LS&&LS.nearbyPicks)||[]).filter(function(p){return p&&p.name});\n   if(!groups.length&&!picks.length)return;\n   var body="";\n   if(picks.length)body+=group("Our favorites",picks.map(function(p){\n     return card({name:p.name,kind:"",blurb:p.note||"",price:"",rating:0,miles:null,maps:p.url||""},true)}).join(""));\n   groups.forEach(function(g){\n    if(!g.items||!g.items.length)return;\n    body+=group(g.label,g.items.map(function(p){return card(p,false)}).join(""));\n   });\n   if(!body)return;\n   var note=(LS&&LS.nearbyNote||"").trim();\n   var sec=document.createElement("section");\n   sec.className="nbsec";\n   sec.innerHTML=\'<div class="wrap"><div class="center"><p class="k">While you\\u2019re in town</p>\'\n    +\'<h2 style="margin:0 auto">Come early, stay late.</h2>\'\n    +\'<p class="lede">\'+esc(note||"A few places near the venue, for the hours that aren\\u2019t on the schedule.")+\'</p></div>\'\n    +body+\'<p class="nbf">Places data \\u00a9 Google</p></div>\';\n   var foot=document.querySelector("footer");\n   var thanks=document.querySelector(".vtg");\n   var before=thanks?thanks.closest("section"):foot;\n   if(!before||!before.parentNode)return;\n   before.parentNode.insertBefore(sec,before);\n   if(document.documentElement.classList.contains("motion")&&!matchMedia("(prefers-reduced-motion: reduce)").matches){\n    sec.classList.add("rv");requestAnimationFrame(function(){requestAnimationFrame(function(){sec.classList.add("in")})});\n   }\n  }).catch(function(){});\n})();\n</script>\n'
NEARBY_JS = JS.replace("NEARBY_TAG", NEARBY_TAG)

LAZY_JS = f"""
<script>
/* {FEEL_TAG}: photos fade in as they arrive */
(function(){{var imgs=document.querySelectorAll("img[loading=lazy]");imgs.forEach(function(im){{if(im.complete&&im.naturalWidth)return;im.setAttribute("data-lzf","");var done=function(){{im.removeAttribute("data-lzf");}};im.addEventListener("load",done,{{once:true}});im.addEventListener("error",done,{{once:true}});}});setTimeout(function(){{imgs.forEach(function(im){{im.removeAttribute("data-lzf");}});}},4000);}})();
</script>
"""


def strip_block(s, tag_open, tag_close):
    i = s.find(tag_open)
    if i < 0:
        return s
    j = s.find(tag_close, i)
    if j < 0:
        return s
    return s[:i] + s[j + len(tag_close):]


def patch(name):
    p = ROOT / name / "index.html"
    s = p.read_text(encoding="utf-8")
    # remove earlier copies
    s = strip_block(s, f"\n/* ---- {FEEL_TAG}: the feel ---- */", f"/* ---- /{FEEL_TAG} ---- */\n")
    s = re.sub(rf"\n<script>\n/\* {SONG_TAG}.*?</script>\n", "\n", s, flags=re.S)
    s = re.sub(rf"\n<script>\n/\* {FEEL_TAG}: photos.*?</script>\n", "\n", s, flags=re.S)
    s = re.sub(rf"\n<script>\n/\* {NEARBY_TAG}.*?</script>\n", "\n", s, flags=re.S)
    # feel css into the first stylesheet
    k = s.find("</style>")
    if k < 0:
        raise SystemExit(f"{name}: no <style>")
    s = s[:k] + FEEL_CSS + s[k:]
    # scripts before </body>
    k = s.rfind("</body>")
    s = s[:k] + LAZY_JS + NEARBY_JS + SONG_JS + s[k:]
    p.write_text(s, encoding="utf-8", newline="\n")
    print(f"  {name}: feel + song applied ({len(s):,} bytes)")


if __name__ == "__main__":
    names = sys.argv[1:] or ALL
    for n in names:
        patch(n)
