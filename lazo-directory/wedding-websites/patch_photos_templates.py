"""patch_photos_templates.py - JC-LAZO-WWS-0929-PHOTOS
Two things every live wedding-website template learns (and _base.html, so
make_themes.py rebuilds carry them). Idempotent: each block is tagged and
replaced in place on re-runs.

  python wedding-websites\\patch_photos_templates.py            # base + the 20 live templates
  python wedding-websites\\patch_photos_templates.py sage tide  # some

PHOTOS (CSS in the first <style>, script right after the hero):
  The couple's photos, where they put them. weddingSites.heroPhoto and
  storyPhoto are {url, x, y, zoom}; siteGalleryFocus is one {x, y, zoom} per
  gallery photo. x/y (0..1) is the point of the picture that stays in view,
  zoom (1..3) scales around it - the same maths as the dashboard's
  "Position your photo" sheet, so what the couple sees there is what guests
  get. The header falls back to the couple's home photo (coverUrl +
  coverFocus) and only then to the template's stock picture. A real couple's
  page never shows the demo couple in the story slot.
GUESTPHOTOS (script before </body>):
  "Share the day as you saw it" - from the wedding day on (couples preview it
  earlier with ?photos=1), guests add photos straight from their phone. The
  page shrinks each one to a 2000px JPEG and POSTs it to
  /api/w/{slug}/photos; the wall lists what everyone has shared, newest
  first, with a lightbox. weddingSites.guestPhotosOn turns it off,
  guestPhotosNote replaces the line under the heading. The demo pages show
  a sample wall built from their own pictures.
"""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# the templates the worker serves at /w/{slug} (TEMPLATES in worker/src/index.js)
LIVE = ["sage", "noir", "dune", "fete", "tide", "flora", "atelier", "verona", "shore", "summit",
        "ranch", "starlit", "frost", "harvest", "aquarelle", "prism", "meadow", "gilded", "marigold", "papel"]
TAG = "JC-LAZO-WWS-0929-PHOTOS"
GTAG = "JC-LAZO-WWS-0929-GUESTPHOTOS"

CSS = f"""
/* ---- {TAG}: the couple's photos where they put them; the guests' wall ---- */
.hero .hph{{overflow:hidden}}
.hero .hph>img{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block}}
.pimg .gpwrap{{overflow:hidden;position:relative}}
.gpsec .gpform{{display:flex;gap:10px;justify-content:center;flex-wrap:wrap;margin-top:26px}}
.gpname{{font:inherit;font-size:15px;padding:13px 14px;border:1px solid var(--line);background:var(--panel);color:var(--ink);width:min(100%,260px)}}
.gpbtn{{display:inline-flex;align-items:center;justify-content:center;gap:8px;cursor:pointer;background:var(--ink);color:var(--bg);padding:14px 26px;font-size:12px;letter-spacing:.28em;text-transform:uppercase;font-weight:500;border:1px solid var(--ink);transition:transform .26s var(--lz-out,ease),background-color .2s ease}}
.gpbtn:hover{{background:var(--acc);border-color:var(--acc);color:#fff}}
.gpbtn:active{{transform:scale(.97)}}
.gpbtn input{{display:none}}
.gpbtn.busy{{opacity:.6;pointer-events:none}}
.gpst{{font-size:13.5px;color:var(--acc);min-height:20px;margin-top:12px;text-align:center}}
.gpwall{{columns:2;column-gap:10px;margin-top:clamp(26px,3.4vw,40px)}}
@media(min-width:700px){{.gpwall{{columns:3}}}}
@media(min-width:1000px){{.gpwall{{columns:4}}}}
.gpi{{break-inside:avoid;margin:0 0 10px;cursor:zoom-in;background:var(--panel);border:1px solid var(--line)}}
.gpi img{{width:100%;display:block;filter:none}}
.gpi figcaption{{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--mut);padding:8px 10px}}
.gpempty{{text-align:center;color:var(--mut);margin-top:26px}}
.gplb{{position:fixed;inset:0;z-index:70;background:rgba(0,0,0,.92);display:none;align-items:center;justify-content:center;flex-direction:column;padding:20px;gap:12px}}
.gplb.on{{display:flex}}
.gplb img{{max-width:100%;max-height:82vh;object-fit:contain;border:0}}
.gplb p{{color:#fff;font-size:13px;letter-spacing:.14em;text-transform:uppercase;opacity:.8;text-align:center}}
.gplb .gpx{{position:absolute;top:14px;right:16px;background:none;border:0;color:#fff;font-size:24px;cursor:pointer}}
body.framed .gpsec{{display:none}}
/* ---- /{TAG} ---- */
"""

HERO_JS = f"""
<script>
/* {TAG}: the couple's photos, where they put them */
(function(){{
 var LS=window.LAZO_SITE;if(!LS)return;
 var n=function(v,d,lo,hi){{return(typeof v==="number"&&isFinite(v))?Math.min(hi,Math.max(lo,v)):d}};
 function pos(p){{p=p||{{}};return{{x:n(p.x,.5,0,1),y:n(p.y,.5,0,1),z:n(p.zoom,1,1,3)}}}}
 function place(img,p){{var q=pos(p);img.style.objectFit="cover";img.style.objectPosition=(q.x*100)+"% "+(q.y*100)+"%";img.style.transformOrigin=(q.x*100)+"% "+(q.y*100)+"%";img.style.transform=q.z>1?"scale("+q.z+")":"none";}}
 var sized=function(u,w){{return "https://wsrv.nl/?url="+encodeURIComponent(u)+"&w="+w+"&q=72"}};
 function load(img,u,w){{var tried=false;img.onerror=function(){{if(!tried){{tried=true;img.src=u;}}else if(img.onfail)img.onfail();}};img.src=sized(u,w);}}
 window.lzPlace=place;
 /* header: the photo the couple placed, else their home photo, else the template's */
 var hero=(LS.heroPhoto&&LS.heroPhoto.url)?LS.heroPhoto:(LS.coverUrl?{{url:LS.coverUrl,x:LS.coverFocus?LS.coverFocus.x:.5,y:LS.coverFocus?LS.coverFocus.y:.5,zoom:1}}:null);
 var hph=document.querySelector(".hero .hph");
 if(hero&&hph){{
  var im=new Image();im.alt="";im.decoding="async";
  im.onfail=function(){{im.remove();hph.style.backgroundImage="";hph.style.filter="";}};
  hph.style.backgroundImage="none";hph.style.filter="none";
  place(im,hero);hph.appendChild(im);load(im,hero.url,1900);
 }}
 document.addEventListener("DOMContentLoaded",function(){{
  var fig=document.querySelector(".split .pimg"),sp=LS.storyPhoto;
  if(fig){{var si=fig.querySelector("img");
   if(sp&&sp.url&&si){{
    var w=document.createElement("div");w.className="gpwrap";si.parentNode.insertBefore(w,si);w.appendChild(si);
    si.removeAttribute("onerror");si.style.filter="none";place(si,sp);
    si.onfail=function(){{fig.style.display="none"}};load(si,sp.url,1000);
    var cap=fig.querySelector("figcaption");if(cap)cap.textContent="";
   }} else fig.style.display="none";
  }}
  var gf=LS.siteGalleryFocus||[],gal=LS.siteGallery||[];
  document.querySelectorAll(".gal figure").forEach(function(fg,i){{var im=fg.querySelector("img");if(!im||!gal[i]||!gf[i])return;place(im,gf[i]);fg.style.overflow="hidden";}});
 }});
}})();
</script>
"""

GUEST_JS = f"""
<script>
/* {GTAG}: photos guests share from their phones */
(function(){{
 if(document.body.classList.contains("framed"))return;
 var LS=window.LAZO_SITE||null;
 var q=new URLSearchParams(location.search);
 if(LS&&LS.guestPhotosOn===false)return;
 var live=!!LS,open=true;
 if(live){{var iso=LS.dateIso||"";if(/^\\d{{4}}-\\d{{2}}-\\d{{2}}$/.test(iso)){{open=Date.now()>=new Date(iso+"T00:00:00").getTime()||q.get("photos")==="1";}}}}
 if(live&&!open)return;
 var slug=live?LS.slug:"";
 var API=live?"https://meetlazo.com/api/w/"+encodeURIComponent(slug)+"/photos":"";
 var note=(live&&LS.guestPhotosNote)||"Took a photo we\\u2019d love to see? Add it here straight from your phone \\u2014 it lands on this page for everyone.";
 var sec=document.createElement("section");sec.className="gpsec";sec.id="photos";
 sec.innerHTML='<div class="wrap"><div class="center"><p class="k">Your photos</p><h2 style="margin:0 auto">Share the day as you saw it.</h2><p class="lede" id="gpnote"></p>'
  +'<div class="gpform"><input class="gpname" id="gpname" placeholder="Your name (optional)" maxlength="60" autocomplete="name">'
  +'<label class="gpbtn" id="gpbtn"><input type="file" id="gpfile" accept="image/*" multiple>Add photos from your phone</label></div>'
  +'<p class="gpst" id="gpst"></p></div><div class="gpwall" id="gpwall"></div><p class="gpempty" id="gpempty" hidden>No photos yet \\u2014 yours could be the first.</p></div>';
 sec.querySelector("#gpnote").textContent=note;
 var after=document.querySelector(".gal");after=after?after.closest("section"):null;
 if(!after){{var sp=document.querySelector(".split");after=sp?sp.closest("section"):null;}}
 var foot=document.querySelector("footer");
 if(after&&after.parentNode)after.parentNode.insertBefore(sec,after.nextSibling);else if(foot)foot.parentNode.insertBefore(sec,foot);else return;
 var wall=sec.querySelector("#gpwall"),empty=sec.querySelector("#gpempty"),st=sec.querySelector("#gpst"),nameI=sec.querySelector("#gpname"),fileI=sec.querySelector("#gpfile"),btn=sec.querySelector("#gpbtn");
 try{{nameI.value=localStorage.getItem("lzgpname")||"";}}catch(_){{}}
 var lb=document.createElement("div");lb.className="gplb";lb.innerHTML='<button class="gpx" aria-label="Close">\\u2715</button><img alt=""><p></p>';document.body.appendChild(lb);
 lb.addEventListener("click",function(e){{if(e.target.tagName!=="IMG")lb.classList.remove("on")}});
 document.addEventListener("keydown",function(e){{if(e.key==="Escape")lb.classList.remove("on")}});
 function thumb(u){{return live?"https://wsrv.nl/?url="+encodeURIComponent(u)+"&w=640&q=72":u}}
 function card(p,first){{
  var f=document.createElement("figure");f.className="gpi";
  var im=document.createElement("img");im.alt=p.caption||"";im.loading="lazy";im.src=p.local||thumb(p.url);
  im.onerror=function(){{if(im.src!==p.url)im.src=p.url;else f.remove();}};
  f.appendChild(im);
  var who=[p.name,p.caption].filter(Boolean).join(" \\u00b7 ");
  if(who){{var c=document.createElement("figcaption");c.textContent=who;f.appendChild(c);}}
  f.addEventListener("click",function(){{lb.querySelector("img").src=p.local||p.url;lb.querySelector("p").textContent=who;lb.classList.add("on");}});
  if(first&&wall.firstChild)wall.insertBefore(f,wall.firstChild);else wall.appendChild(f);
 }}
 function render(list){{wall.innerHTML="";list.forEach(function(p){{card(p,false)}});empty.hidden=list.length>0;}}
 if(!live){{
  var sample=[].slice.call(document.querySelectorAll(".gal img,.pimg img")).map(function(i){{return i.getAttribute("src")}}).filter(Boolean).slice(0,4);
  var names=["Aunt Rosa","The Nguyens","Table 7","Dev"];
  render(sample.map(function(u,i){{return{{url:u,name:names[i]||"",caption:""}}}}));
  btn.addEventListener("click",function(e){{e.preventDefault();if(typeof demo==="function")demo();}});
  return;
 }}
 fetch(API).then(function(r){{return r.json()}}).then(function(j){{render((j&&j.photos)||[])}}).catch(function(){{empty.hidden=false}});
 function shrink(file){{
  return new Promise(function(res){{
   var MAX=2000,done=function(b){{res(b||file)}};
   var img=new Image(),url=URL.createObjectURL(file);
   img.onload=function(){{
    try{{
     var w=img.naturalWidth,h=img.naturalHeight,s=Math.min(1,MAX/Math.max(w,h));
     var cv=document.createElement("canvas");cv.width=Math.round(w*s);cv.height=Math.round(h*s);
     cv.getContext("2d").drawImage(img,0,0,cv.width,cv.height);
     URL.revokeObjectURL(url);cv.toBlob(function(b){{done(b)}},"image/jpeg",.86);
    }}catch(_){{done(null)}}
   }};
   img.onerror=function(){{URL.revokeObjectURL(url);done(null)}};
   img.src=url;
  }});
 }}
 fileI.addEventListener("change",async function(){{
  var files=[].slice.call(fileI.files||[]);fileI.value="";
  if(!files.length)return;
  var name=nameI.value.trim().slice(0,60);try{{localStorage.setItem("lzgpname",name)}}catch(_){{}}
  var ok=0,bad=0,why="";btn.classList.add("busy");
  for(var i=0;i<files.length;i++){{
   st.textContent="Adding "+(i+1)+" of "+files.length+"\\u2026";
   try{{
    var blob=await shrink(files[i]);
    var fd=new FormData();fd.append("file",blob,"photo.jpg");fd.append("name",name);
    var r=await fetch(API,{{method:"POST",body:fd}});var j=await r.json();
    if(!r.ok||!j.ok)throw new Error((j&&j.message)||"");
    var p=j.photo;p.local=URL.createObjectURL(blob);card(p,true);empty.hidden=true;ok++;
   }}catch(e){{bad++;if(e&&e.message)why=e.message;}}
  }}
  btn.classList.remove("busy");
  st.textContent=ok?("Added "+ok+" photo"+(ok===1?"":"s")+" \\u2014 thank you! \\u2713"+(bad?" ("+bad+" didn\\u2019t go through)":"")):(why||"That didn\\u2019t send \\u2014 try again?");
 }});
}})();
</script>
"""


def strip(s):
    s = re.sub(rf"\n/\* ---- {TAG}:.*?/\* ---- /{TAG} ---- \*/\n", "\n", s, flags=re.S)
    s = re.sub(rf"\n<script>\n/\* {TAG}:.*?</script>\n", "\n", s, flags=re.S)
    s = re.sub(rf"\n<script>\n/\* {GTAG}:.*?</script>\n", "\n", s, flags=re.S)
    return s


def patch(path, is_base):
    s = strip(path.read_text(encoding="utf-8"))
    k = s.find("</style>")
    if k < 0:
        raise SystemExit(f"{path}: no <style>")
    s = s[:k] + CSS + s[k:]
    anchor = "@@HERO@@\n" if is_base else "</header>\n"
    if s.count(anchor) != 1:
        raise SystemExit(f"{path}: hero anchor {anchor!r} found {s.count(anchor)} times")
    k = s.find(anchor) + len(anchor)
    s = s[:k] + HERO_JS + s[k:]
    k = s.rfind("</body>")
    if k < 0:
        raise SystemExit(f"{path}: no </body>")
    s = s[:k] + GUEST_JS + s[k:]
    path.write_text(s, encoding="utf-8", newline="\n")
    print(f"  {path.relative_to(ROOT)}: photos + guest wall ({len(s):,} bytes)")


if __name__ == "__main__":
    names = sys.argv[1:] or LIVE
    if not sys.argv[1:]:
        patch(ROOT / "_base.html", True)
    for n in names:
        p = ROOT / n / "index.html"
        if not p.exists():
            raise SystemExit(f"no template {n}")
        patch(p, False)
