"""patch_hub_cards.py - JC-LAZO-WWT-0919-004
Adds a hub card (phone preview, name, vibe, palette dots, buttons) for every
theme in themes.json that index.html does not show yet. Palette colours come
from make_themes.THEMES so the dots match the template exactly. Idempotent.

  python wedding-websites\\patch_hub_cards.py
Then: python wedding-websites\\patch_hub_seo.py  (counts + ItemList)
"""
import json, re, sys, html
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from make_themes import THEMES as SPECS  # noqa: E402

P = ROOT / "index.html"
T = json.loads((ROOT / "themes.json").read_text(encoding="utf-8"))
s = P.read_text(encoding="utf-8")
have = set(re.findall(r'<div class="tpl rv" data-t="(\w+)"[^>]*>', s))  # JC-LAZO-WWT-0921-002: cards carry data-styles now


def card(slug):
    t = T[slug]
    spec = SPECS[slug]
    pals = spec["palettes"]
    dots = []
    for i, (k, v) in enumerate(pals.items()):
        # dark palettes read better with the light half first
        acc, bg = v["--acc"], v["--bg"]
        dots.append(f'<button data-p="{k}" title="{html.escape(k.replace("-", " ").title())}" style="background:linear-gradient(135deg,{acc} 55%,{bg} 55%)"{" class=\"on\"" if i == 0 else ""}></button>')
    name = html.escape(t["name"])
    return (f' <div class="tpl rv" data-t="{slug}">\n'
            f'  <div class="phone"><span class="notch"></span><div class="screen"><iframe loading="lazy" title="{name} template preview" data-f src="{slug}/?frame=1"></iframe></div></div>\n'
            f'  <h2>{name}</h2><p class="vibe">{html.escape(t["vibe"])}</p>\n'
            f'  <div class="pals" data-slug="{slug}">{"".join(dots)}</div>\n'
            f'  <div class="btns"><a class="view" data-view href="{slug}/">View demo</a><a class="use" data-use href="#">Use {name}</a></div>\n'
            f' </div>\n')


new = [slug for slug in T if slug not in have]
if not new:
    print("hub already shows every theme")
    sys.exit()
missing = [x for x in new if x not in SPECS]
if missing:
    raise SystemExit(f"themes.json has {missing} but make_themes has no spec for them")
k = s.index("\n</main>")
s = s[:k] + "\n" + "".join(card(x) for x in new) + s[k:]
P.write_text(s, encoding="utf-8", newline="\n")
print(f"added cards: {', '.join(new)}")
