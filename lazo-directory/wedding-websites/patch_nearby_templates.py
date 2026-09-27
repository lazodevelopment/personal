"""patch_nearby_templates.py - JC-LAZO-WWS-0915-NEARBY
Teaches apply_feel.py to add the "While you're in town" section to every
template, then re-applies it. Idempotent; safe to re-run.
"""
from pathlib import Path

P = Path(__file__).resolve().parent / "apply_feel.py"
s = P.read_text(encoding="utf-8")
if "NEARBY_TAG" in s:
    raise SystemExit("[patch] already applied")

CSS = """/* things to do around the venue */
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
"""

JS = """
<script>
/* NEARBY_TAG: things for guests to do around the venue */
(function(){
 if(document.body.classList.contains("framed"))return;
 var LS=window.LAZO_SITE||null;
 var slug=LS?LS.slug:"demo";                         /* the demos show a sample */
 if(LS&&LS.nearbyOn===false)return;
 if(LS&&!LS.venueAddress&&!LS.venueName)return;
 var esc=function(t){return String(t||"").replace(/[<>&"]/g,function(c){return{"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"}[c]})};
 var mapsFor=function(p){return p.maps||("https://www.google.com/maps/search/?api=1&query="+encodeURIComponent(p.name+" "+((LS&&LS.venueAddress)||"")))};
 function card(p,pick){
  var meta=[p.kind,p.price,p.blurb].filter(Boolean).join(" \\u00b7 ");
  var right="";
  if(p.rating)right+="\\u2605 "+p.rating.toFixed(1);
  if(p.miles!==null&&p.miles!==undefined)right+="<small>"+p.miles+" mi</small>";
  return '<a class="nbc'+(pick?" nbpick":"")+'" href="'+esc(mapsFor(p))+'" target="_blank" rel="noopener">'
   +'<span class="nbtx"><span class="nbn">'+esc(p.name)+'</span>'+(meta?'<span class="nbm">'+esc(meta)+'</span>':'')+'</span>'
   +(right?'<span class="nbr">'+right+'</span>':'')+'</a>';
 }
 function group(label,cards){return '<div class="nbgroup"><p class="nbh">'+esc(label)+'</p><div class="nbg">'+cards+'</div></div>'}
 fetch("https://meetlazo.com/api/nearby?slug="+encodeURIComponent(slug))
  .then(function(r){return r.json()})
  .then(function(j){
   var groups=(j&&j.groups)||[];
   var picks=((LS&&LS.nearbyPicks)||[]).filter(function(p){return p&&p.name});
   if(!groups.length&&!picks.length)return;
   var body="";
   if(picks.length)body+=group("Our favorites",picks.map(function(p){
     return card({name:p.name,kind:"",blurb:p.note||"",price:"",rating:0,miles:null,maps:p.url||""},true)}).join(""));
   groups.forEach(function(g){
    if(!g.items||!g.items.length)return;
    body+=group(g.label,g.items.map(function(p){return card(p,false)}).join(""));
   });
   if(!body)return;
   var note=(LS&&LS.nearbyNote||"").trim();
   var sec=document.createElement("section");
   sec.className="nbsec";
   sec.innerHTML='<div class="wrap"><div class="center"><p class="k">While you\\u2019re in town</p>'
    +'<h2 style="margin:0 auto">Come early, stay late.</h2>'
    +'<p class="lede">'+esc(note||"A few places near the venue, for the hours that aren\\u2019t on the schedule.")+'</p></div>'
    +body+'<p class="nbf">Places data \\u00a9 Google</p></div>';
   var foot=document.querySelector("footer");
   var thanks=document.querySelector(".vtg");
   var before=thanks?thanks.closest("section"):foot;
   if(!before||!before.parentNode)return;
   before.parentNode.insertBefore(sec,before);
   if(document.documentElement.classList.contains("motion")&&!matchMedia("(prefers-reduced-motion: reduce)").matches){
    sec.classList.add("rv");requestAnimationFrame(function(){requestAnimationFrame(function(){sec.classList.add("in")})});
   }
  }).catch(function(){});
})();
</script>
"""

s = s.replace('FEEL_TAG = "JC-LAZO-WWS-0915-FEEL"',
              'FEEL_TAG = "JC-LAZO-WWS-0915-FEEL"\nNEARBY_TAG = "JC-LAZO-WWS-0915-NEARBY"', 1)
s = s.replace("/* ---- /{FEEL_TAG} ---- */", CSS + "/* ---- /{FEEL_TAG} ---- */", 1)
s = s.replace('LAZY_JS = f"""', "NEARBY_JS = JS.replace(\"NEARBY_TAG\", NEARBY_TAG)\n\nLAZY_JS = f\"\"\"", 1)
s = s.replace("JS = \"\"\"\n<script>\n/* NEARBY_TAG", "JS = \"\"\"\n<script>\n/* NEARBY_TAG")  # no-op guard
# put the JS constant in before it is used
s = s.replace("NEARBY_JS = JS.replace", "JS = " + repr(JS) + "\nNEARBY_JS = JS.replace", 1)
# strip old copies + emit the new script alongside the others
s = s.replace('    s = re.sub(rf"\\n<script>\\n/\\* {FEEL_TAG}: photos.*?</script>\\n", "\\n", s, flags=re.S)',
              '    s = re.sub(rf"\\n<script>\\n/\\* {FEEL_TAG}: photos.*?</script>\\n", "\\n", s, flags=re.S)\n'
              '    s = re.sub(rf"\\n<script>\\n/\\* {NEARBY_TAG}.*?</script>\\n", "\\n", s, flags=re.S)', 1)
s = s.replace("    s = s[:k] + LAZY_JS + SONG_JS + s[k:]",
              "    s = s[:k] + LAZY_JS + NEARBY_JS + SONG_JS + s[k:]", 1)
s = s.replace("  - the June button breathes once when it appears; honours Reduce Motion",
              "  - the June button breathes once when it appears; honours Reduce Motion\n"
              "NEARBY (script): a \"While you're in town\" section built from\n"
              "/api/nearby?slug= - eat & drink, coffee, things to do around the\n"
              "venue, the couple's own favourites first. Demos show a sample.", 1)
P.write_text(s, encoding="utf-8", newline="\n")
print(f"apply_feel.py taught the nearby section ({len(s):,} bytes)")
