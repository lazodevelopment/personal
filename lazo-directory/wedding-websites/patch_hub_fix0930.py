"""patch_hub_fix0930.py - JC-LAZO-HUB-0930-FIX
Hub fixes from the 2026-09-30 audit (wedding-websites/index.html). Idempotent.
  1. Palette dots and the name/date inputs share one URL builder, so picking a
     palette keeps the names and typing a name keeps the palette.
  2. "New" stays on the first sales card only.
  3. aria-labels on the name inputs and palette dots; aria-pressed follows the
     selected dot; the comparison table scrolls sideways on small phones.
Also edits make_styles.py (strip the sales block from style pages) and
make_features.py (the comparison table lands on the vs page; new palette line).
  python wedding-websites\\patch_hub_fix0930.py
Then: python wedding-websites\\make_styles.py; python wedding-websites\\make_features.py;
      python wedding-websites\\sync_dist.py; python deploy\\upload_r2.py --prefix wedding-websites
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def edit(path, pairs, regex=False):
    s = path.read_text(encoding="utf-8")
    orig = s
    for old, new in pairs:
        if new and new in s and old not in new:
            continue
        if regex:
            s = re.sub(old, new, s)
        elif old in s:
            s = s.replace(old, new)
        else:
            raise SystemExit(f"{path.name}: anchor not found: {old[:60]}")
    if s != orig:
        path.write_text(s, encoding="utf-8", newline="\n")
        print(f"  patched {path.name}")
    else:
        print(f"  already  {path.name}")


HUB = HERE / "index.html"
edit(HUB, [
    # 1. one URL builder
    ('  const fp=new URLSearchParams(p);fp.set("frame","1");\n   card.querySelector("[data-f]").src=id+"/?"+fp.toString();\n   card.querySelector("[data-view]").href=id+"/"+(qs?"?"+qs:"");',
     '  const cp=new URLSearchParams(p);const on=card.querySelector(".pals button.on");if(on&&on.dataset.p)cp.set("palette",on.dataset.p);const cqs=cp.toString();\n'
     '   const fp=new URLSearchParams(cp);fp.set("frame","1");\n   card.querySelector("[data-f]").src=id+"/?"+fp.toString();\n   card.querySelector("[data-view]").href=id+"/"+(cqs?"?"+cqs:"");'),
    ('   row.querySelectorAll("button").forEach(function(x){x.classList.remove("on")});\n   b.classList.add("on");\n   var k=b.dataset.p;\n   var base=frame.getAttribute("src").split("?")[0];\n   frame.setAttribute("src",base+"?frame=1&palette="+k);\n   view.href=slug+"/?palette="+k;',
     '   row.querySelectorAll("button").forEach(function(x){x.classList.remove("on");x.setAttribute("aria-pressed","false")});\n   b.classList.add("on");b.setAttribute("aria-pressed","true");\n   var k=b.dataset.p;\n'
     '   var p=(typeof params==="function")?params():new URLSearchParams();p.set("palette",k);\n   var fp=new URLSearchParams(p);fp.set("frame","1");\n'
     '   var base=frame.getAttribute("src").split("?")[0];\n   frame.setAttribute("src",base+"?"+fp.toString());\n   view.href=slug+"/?"+p.toString();'),
    # 3. labels
    ('<input id="pn1" placeholder="Your name" autocomplete="off">', '<input id="pn1" aria-label="Your name" placeholder="Your name" autocomplete="off">'),
    ('<input id="pn2" placeholder="Partner&#39;s name" autocomplete="off">', '<input id="pn2" aria-label="Partner&#39;s name" placeholder="Partner&#39;s name" autocomplete="off">'),
    ('  <div class="cmp">\n   <h3>What you get here', '  <div class="cmp" style="overflow-x:auto;-webkit-overflow-scrolling:touch">\n   <h3>What you get here'),
])
edit(HUB, [
    (r'<button data-p="([a-z0-9-]+)" title="([^"]+)" style="([^"]*)" class="on">', r'<button data-p="\1" title="\2" aria-label="\2 palette" aria-pressed="true" style="\3" class="on">'),
    (r'<button data-p="([a-z0-9-]+)" title="([^"]+)" style="([^"]*)">', r'<button data-p="\1" title="\2" aria-label="\2 palette" aria-pressed="false" style="\3">'),
], regex=True)
# 2. one "New" badge
s = HUB.read_text(encoding="utf-8")
badge = '<span class="new">New</span>'
n = s.count(badge)
if n > 1:
    first = s.index(badge) + len(badge)
    s = s[:first] + s[first:].replace(badge, "")
    HUB.write_text(s, encoding="utf-8", newline="\n")
    print(f"  index.html: {n - 1} 'New' badge(s) removed")

# style pages never carry the sales block (its relative links would 404 from /floral/)
edit(HERE / "make_styles.py", [
    ('    s = re.sub(r"<!-- lz-filters -->.*?<!-- /lz-filters -->\\n", "", s, flags=re.S)\n',
     '    s = re.sub(r"<!-- lz-filters -->.*?<!-- /lz-filters -->\\n", "", s, flags=re.S)\n'
     '    s = re.sub(r"<!-- lz-sell -->.*?<!-- /lz-sell -->\\n?", "", s, flags=re.S)  # JC-LAZO-HUB-0930-FIX\n'),
])
# feature pages: the new palette line, and the comparison table on the vs page
edit(HERE / "make_features.py", [
    ("""    s = s.replace('view.href=slug+"/?palette="+k;', 'view.href="../"+slug+"/?palette="+k;', 1)\n""",
     """    s = s.replace('view.href=slug+"/?"+p.toString();', 'view.href="../"+slug+"/?"+p.toString();', 1)\n"""),
    ("""    s = re.sub(r"<!-- lz-sell -->.*?<!-- /lz-sell -->\\n?", "", s, flags=re.S)\n    s = re.sub(r'<section class="beyond rv">""",
     """    # JC-LAZO-HUB-0930-FIX: the vs page keeps the Knot/Zola table the sales block holds
    cmp_m = re.search(r'  <div class="cmp"[^>]*>\\n.*?</table>\\n\\s*<p class="fine">[^\\n]*\\n', s, flags=re.S)
    cmp_html = (cmp_m.group(0) + "  </div>\\n") if cmp_m else ""
    s = re.sub(r"<!-- lz-sell -->.*?<!-- /lz-sell -->\\n?", "", s, flags=re.S)
    s = re.sub(r'<section class="beyond rv">"""),
    ("""    story += ['  </div>',\n              '  <div class="scta">""",
     """    story += ['  </div>']\n    if slug == "vs-zola-the-knot" and cmp_html:\n        story += ['  <div style="margin-top:36px">', cmp_html, '  </div>']\n    story += ['  <div class="scta">"""),
])
print("done")
