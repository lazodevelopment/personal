"""patch_meals_rsvp_1016.py - JC-LAZO-WWS-1016-MEALS
A meal for every person coming, on the couple's site RSVP.

Before: one radio row of the couple's mealOptions with the FIRST option
pre-checked, so a guest who skipped the question silently counted as entree #1;
plus-ones had no meal; no allergies, no kid's meal.

After (in the personal-RSVP block that patch_live_templates.py owns):
  - one row per person coming: the guest, then each plus-one they say they're
    bringing (the #plusn select redraws the rows, keeping what was typed);
  - per person: a meal select starting on "Choose a meal..." (nothing
    pre-picked), a Kid's meal tick, an Allergies / dietary line, and a name for
    each plus-one (optional);
  - rows hide when the guest says No;
  - the RSVP carries meals:[{name,meal,kid,allergies}] (max 10), plus the
    first person's pick in `meal` (older dashboards read that) and a joined
    `allergies` line.

NEEDS the firestore.rules RSVP allowlist change (meals, allergies) LIVE FIRST:
the rules refuse unknown keys, so these templates must not go to R2 before
the rules deploy, or every RSVP with a meal row fails.

Patches _base.html, the 21 live templates, and patch_live_templates.py itself
(so a later re-run of that script does not bring the old block back).

  python wedding-websites\\patch_meals_rsvp_1016.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIVE = ["sage", "noir", "dune", "fete", "tide", "flora", "atelier", "verona", "shore", "summit",
        "ranch", "starlit", "frost", "harvest", "aquarelle", "prism", "meadow", "gilded", "marigold", "papel", "peony"]

OLD_ROW = """  var mealRow=function(opts){
   if(!opts.length||rform.querySelector(".meals"))return;
   var wrap=document.createElement("div");wrap.className="meals";wrap.innerHTML='<span class="mealk">Dinner</span>';
   opts.forEach(function(o,i){var l=document.createElement("label");var r=document.createElement("input");r.type="radio";r.name="meal";r.value=o;if(i===0)r.checked=true;var s=document.createElement("span");s.textContent=o;l.appendChild(r);l.appendChild(s);wrap.appendChild(l)});
   var song=rform.querySelector("[data-song]");rform.insertBefore(wrap,song||rform.querySelector("textarea"));
  };
  mealRow((LS.mealOptions||[]).filter(Boolean));
"""

NEW_ROW = """  /* JC-LAZO-WWS-1016-MEALS: a meal, kid's meal and allergies for every person coming; nothing pre-picked */
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
    if(MO.length){var s=document.createElement("select");s.setAttribute("aria-label","Meal");var o0=document.createElement("option");o0.value="";o0.textContent="Choose a meal\\u2026";s.appendChild(o0);MO.forEach(function(o){var op=document.createElement("option");op.value=o;op.textContent=o;s.appendChild(op)});s.value=pv.m;b.appendChild(s);}
    var kl=document.createElement("label");var kc=document.createElement("input");kc.type="checkbox";kc.setAttribute("data-k","");kc.checked=pv.k;var ks=document.createElement("span");ks.textContent="Kid\\u2019s meal";kl.appendChild(kc);kl.appendChild(ks);b.appendChild(kl);
    var ai=document.createElement("input");ai.type="text";ai.setAttribute("data-a","");ai.setAttribute("aria-label","Allergies or dietary needs");ai.placeholder="Allergies / dietary (optional)";ai.maxLength=120;ai.value=pv.a;b.appendChild(ai);
    w.appendChild(b);
   }
   var yes=rform.querySelector(".radio label:first-child input");w.style.display=!yes||yes.checked?"":"none";
  };
  var mealRow=function(opts){if(opts.length)MO=opts.slice(0,8);drawMeals();};
  mealRow((LS.mealOptions||[]).filter(Boolean));
  [].slice.call(rform.querySelectorAll(".radio input")).forEach(function(r){r.addEventListener("change",drawMeals)});
"""

OLD_PLUS = """     rform.insertBefore(pr,rform.querySelector(".meals")||rform.querySelector("[data-song]")||rform.querySelector("textarea"));
"""
NEW_PLUS = """     rform.insertBefore(pr,rform.querySelector(".meals")||rform.querySelector("[data-song]")||rform.querySelector("textarea"));
     pr.querySelector("select").addEventListener("change",drawMeals);
"""

OLD_SEND = """     var meal=rform.querySelector("input[name=meal]:checked");if(meal)b.fields.meal={stringValue:meal.value.slice(0,80)};
"""
NEW_SEND = """     var mps=[].slice.call(rform.querySelectorAll(".meals .mp"));
     if(mps.length&&b.fields.attending&&b.fields.attending.stringValue==="yes"){
      var ppl=mps.slice(0,10).map(function(m,i){var nn=i===0?((b.fields.name||{}).stringValue||""):((m.querySelector("[data-n]")||{}).value||"").trim();return{mapValue:{fields:{name:{stringValue:nn.slice(0,80)},meal:{stringValue:((m.querySelector("select")||{}).value||"").slice(0,80)},kid:{booleanValue:!!(m.querySelector("[data-k]")||{}).checked},allergies:{stringValue:((m.querySelector("[data-a]")||{}).value||"").trim().slice(0,120)}}}}});
      b.fields.meals={arrayValue:{values:ppl}};
      var m0=ppl[0].mapValue.fields.meal.stringValue;if(m0)b.fields.meal={stringValue:m0};
      var al=ppl.map(function(p,i){var f=p.mapValue.fields,a=f.allergies.stringValue;return a?(f.name.stringValue||(i?"Guest "+i:"Guest"))+": "+a:""}).filter(Boolean).join("; ");
      if(al)b.fields.allergies={stringValue:al.slice(0,290)};
     }
"""


def patch_text(s, name, py=False):
    pairs = [(OLD_ROW, NEW_ROW), (OLD_PLUS, NEW_PLUS), (OLD_SEND, NEW_SEND)]
    for old, new in pairs:
        old_, new_ = old, new   # \u escapes stay escapes in the HTML and in the raw JS string of patch_live_templates.py
        c = s.count(old_)
        assert c == 1, f"{name}: expected 1 match, found {c}: {old_[:70]!r}"
        s = s.replace(old_, new_)
    return s


targets = [ROOT / "_base.html"] + [ROOT / t / "index.html" for t in LIVE]
for f in targets:
    raw = f.read_text(encoding="utf-8")
    crlf = "\r\n" in raw
    s = raw.replace("\r\n", "\n")
    if "JC-LAZO-WWS-1016-MEALS" in s:
        print(f"skip {f.relative_to(ROOT)} (already patched)")
        continue
    s = patch_text(s, str(f.relative_to(ROOT)))
    if crlf:
        s = s.replace("\n", "\r\n")
    f.write_text(s, encoding="utf-8", newline="")
    print(f"patched {f.relative_to(ROOT)}")

pf = ROOT / "patch_live_templates.py"
raw = pf.read_text(encoding="utf-8")
crlf = "\r\n" in raw
s = raw.replace("\r\n", "\n")
if "JC-LAZO-WWS-1016-MEALS" not in s:
    s = patch_text(s, pf.name, py=True)
    if crlf:
        s = s.replace("\n", "\r\n")
    pf.write_text(s, encoding="utf-8", newline="")
    print(f"patched {pf.name}")
