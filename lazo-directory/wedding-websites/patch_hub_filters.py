"""patch_hub_filters.py - JC-LAZO-WWI-0920-FILTERS
Two things on the templates hub:
  1. A style filter above the grid - All, Floral, Beach, Rustic, Black tie,
     Modern, Boho, Winter, Cultural... - built from themes.json. Each card
     gets data-styles; a chip hides the cards that don't match. Twenty cards
     is a wall; six is a choice.
  2. "Show me the morning after" on the live-names box: a switch that flips
     every preview into married mode (?married=1), the thing no other builder
     has. The View demo links follow.
Idempotent: markers <!-- lz-filters --> / <!-- /lz-filters --> and the css /
js blocks are replaced on re-run. make_styles.py strips the filter row from
the style pages (they are already one style).
  python wedding-websites\\patch_hub_filters.py
"""
import json, re, html
from pathlib import Path

ROOT = Path(__file__).resolve().parent
P = ROOT / "index.html"
THEMES = json.loads((ROOT / "themes.json").read_text(encoding="utf-8"))
s = P.read_text(encoding="utf-8")

# the chips, in the order they should read; each maps to style tags
CHIPS = [
    ("all", "All", []),
    ("floral", "Floral & garden", ["floral", "garden", "greenery", "watercolor"]),
    ("beach", "Beach & destination", ["beach", "coastal", "destination"]),
    ("rustic", "Rustic & outdoor", ["rustic", "barn", "western", "mountain", "vineyard", "fall", "outdoor"]),
    ("formal", "Classic & black tie", ["classic", "elegant", "black-tie", "vintage", "art-deco"]),
    ("modern", "Modern & minimal", ["modern", "minimalist", "geometric", "small-wedding", "elopement"]),
    ("boho", "Boho & desert", ["boho", "desert"]),
    ("evening", "Celestial & winter", ["celestial", "winter", "evening", "holiday"]),
    ("cultural", "Cultural", ["cultural", "south-asian", "indian", "latin", "mexican"]),
]

# 1. data-styles on every card
for slug, t in THEMES.items():
    keys = [c[0] for c in CHIPS[1:] if set(c[2]) & set(t["styles"])]
    attr = ' data-styles="' + " ".join(keys) + '"'
    s = re.sub(r'<div class="tpl rv" data-t="' + slug + r'"( data-styles="[^"]*")?>',
               '<div class="tpl rv" data-t="' + slug + '"' + attr + '>', s, count=1)

# 2. the filter row + married switch
s = re.sub(r"<!-- lz-filters -->.*?<!-- /lz-filters -->\n", "", s, flags=re.S)
row = ['<!-- lz-filters -->', '<div class="filt" role="group" aria-label="Filter designs by style">']
row += [f' <button type="button" data-fk="{k}"{" class=\"on\"" if k == "all" else ""}>{html.escape(label)}</button>' for k, label, _ in CHIPS]
row += [' <span class="fn" id="filtN"></span>', '</div>', '<!-- /lz-filters -->', '']
anchor = '<main class="grid" id="grid">'
assert s.count(anchor) == 1
s = s.replace(anchor, "\n".join(row) + anchor)

s = re.sub(r"\s*<!-- lz-married -->.*?<!-- /lz-married -->", "", s, flags=re.S)
sw = ('\n  <!-- lz-married -->\n  <label class="mar"><input type="checkbox" id="pmar"><span class="tog" aria-hidden="true"></span>'
      '<span>Show me the morning after <small>every design flips to “We’re married” on its own</small></span></label>\n  <!-- /lz-married -->')
anchor = '  <p class="live"><span class="dot"></span>'
assert s.count(anchor) == 1
s = s.replace(anchor, sw + "\n" + anchor)

# 3. css + js
s = re.sub(r"/\* lz-filters-css \*/.*?/\* /lz-filters-css \*/\n", "", s, flags=re.S)
css = """/* lz-filters-css */
.filt{max-width:1180px;margin:34px auto 0;padding:0 22px;display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:center}
.filt button{font:inherit;font-size:13.5px;color:var(--plum);background:#fff;border:1px solid var(--goldSoft);border-radius:999px;padding:8px 15px;cursor:pointer;transition:background .2s,color .2s,border-color .2s}
.filt button:hover{background:var(--wash)}
.filt button.on{background:var(--plum);color:var(--ivory);border-color:var(--plum)}
.filt .fn{font-size:12.5px;color:var(--muted);margin-left:6px}
.tpl.hide{display:none}
.mar{display:flex;align-items:center;gap:10px;justify-content:center;margin:12px auto 2px;font-size:13.5px;color:var(--ink);cursor:pointer;max-width:420px;text-align:left}
.mar input{position:absolute;opacity:0;width:0;height:0}
.mar .tog{flex:none;width:38px;height:22px;border-radius:999px;background:#E6D6B8;position:relative;transition:background .2s}
.mar .tog::after{content:"";position:absolute;top:3px;left:3px;width:16px;height:16px;border-radius:50%;background:#fff;transition:transform .2s;box-shadow:0 1px 3px rgba(0,0,0,.2)}
.mar input:checked + .tog{background:var(--plum)}
.mar input:checked + .tog::after{transform:translateX(16px)}
.mar small{display:block;color:var(--muted);font-size:11.5px}
/* /lz-filters-css */
"""
anchor = "</style>\n</head>"
assert s.count(anchor) == 1
s = s.replace(anchor, css + anchor)

s = re.sub(r"\n<script>\n/\* lz-filters-js \*/.*?/\* /lz-filters-js \*/\n</script>", "", s, flags=re.S)
js = """
<script>
/* lz-filters-js */
(function(){
 var btns=document.querySelectorAll('.filt button'),cards=document.querySelectorAll('.tpl'),n=document.getElementById('filtN');
 function pick(k){var c=0;cards.forEach(function(card){var ok=k==='all'||(card.dataset.styles||'').split(' ').indexOf(k)>-1;card.classList.toggle('hide',!ok);if(ok)c++;});
  btns.forEach(function(b){b.classList.toggle('on',b.dataset.fk===k)});n.textContent=k==='all'?'':c+' design'+(c===1?'':'s');
  try{history.replaceState(null,'',k==='all'?location.pathname:location.pathname+'#'+k)}catch(e){}}
 btns.forEach(function(b){b.addEventListener('click',function(){pick(b.dataset.fk)})});
 var h=(location.hash||'').slice(1);if(h&&document.querySelector('.filt button[data-fk="'+h+'"]'))pick(h);
 /* the morning after: every preview flips to married mode */
 var m=document.getElementById('pmar');if(m){m.addEventListener('change',function(){
  cards.forEach(function(card){var f=card.querySelector('[data-f]'),v=card.querySelector('[data-view]');
   var src=new URL(f.getAttribute('src'),location.href);var vv=new URL(v.getAttribute('href'),location.href);
   if(m.checked){src.searchParams.set('married','1');vv.searchParams.set('married','1')}else{src.searchParams.delete('married');vv.searchParams.delete('married')}
   f.setAttribute('src',src.pathname+src.search);v.setAttribute('href',vv.pathname+vv.search)});});}
})();
/* /lz-filters-js */
</script>"""
anchor = "\n</body>"
assert s.count(anchor) == 1
s = s.replace(anchor, js + anchor)

# 4. the live-names updater keeps the married state when it rebuilds the preview URLs
old = ' const p=new URLSearchParams();\n const a=n1.value.trim(),b=n2.value.trim();\n if(a&&b)p.set("names",a+" & "+b);\n if(pd.value)p.set("date",pd.value);\n return p;'
new = ' const p=new URLSearchParams();\n const a=n1.value.trim(),b=n2.value.trim();\n if(a&&b)p.set("names",a+" & "+b);\n if(pd.value)p.set("date",pd.value);\n var pm=document.getElementById("pmar");if(pm&&pm.checked)p.set("married","1");\n return p;'
if old in s:
    s = s.replace(old, new, 1)
elif new not in s:
    raise SystemExit("params() anchor not found")

P.write_text(s, encoding="utf-8", newline="\n")
print(f"hub: filters + married switch ({len(THEMES)} cards tagged)")
