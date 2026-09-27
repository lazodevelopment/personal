"""patch_couple_app.py - JC-LAZO-WWT-0919-005
Teaches the couple app (FlutterFlow custom code, exported as one Dart file)
the seven new templates. The file hard-codes the template list in three
places: the `known` list for ?template= deep links, the validation list plus
`tplPals` (palette name, accent, background) in the website dialog, and the
design picker rows (slug, name, vibe, swatch colour). All three are extended
from themes.json + themes_extra.py so the app and the site never disagree.

Anchor-and-assert, same as every other Couple patch: each anchor must match
exactly the expected number of times or nothing is written.

  python wedding-websites\\patch_couple_app.py <Couple_source.txt> [<out.txt>]
Default source: app-patches\\Couple_master.txt; default output alongside it,
suffixed _templates20.txt. Paste the output over the custom code in
FlutterFlow, save, test, publish.
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from themes_extra import EXTRA  # noqa: E402

THEMES = json.loads((ROOT / "themes.json").read_text(encoding="utf-8"))
NEW = list(EXTRA)  # harvest, aquarelle, prism, meadow, gilded, marigold, papel
DARK = {"gilded"}  # swatch shows the background, like starlit

SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "app-patches" / "Couple_master.txt"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else SRC.with_name(SRC.stem + "_templates20.txt")
s = SRC.read_text(encoding="utf-8")
if "'papel'" in s:
    raise SystemExit("already applied: 'papel' is present")


def hexcol(css):
    return "0xFF" + css.lstrip("#").upper()


def swap(old, new, label, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"ABORT [{label}]: anchor matched {n} times, expected {count}")
    s = s.replace(old, new)
    print(f"  ok  {label} (x{count})")


# 1 + 2. the two plain slug lists (deep-link `known`, dialog validation)
old = "      'starlit',\n      'frost'\n    ]"
new = "      'starlit',\n      'frost',\n" + ",\n".join(f"      '{t}'" for t in NEW) + "\n    ]"
swap(old, new, "slug lists", count=2)

# 3. tplPals: palette name, accent, background per template
pals = []
for t in NEW:
    rows = "".join(f"        <dynamic>['{k}', {hexcol(v['--acc'])}, {hexcol(v['--bg'])}],\n" for k, v in EXTRA[t]["palettes"].items())
    pals.append(f"      '{t}': <List<dynamic>>[\n{rows}      ],\n")
old = "        <dynamic>['silver', 0xFF6B7482, 0xFFF6F7F8],\n      ],\n    };"
new = "        <dynamic>['silver', 0xFF6B7482, 0xFFF6F7F8],\n      ],\n" + "".join(pals) + "    };"
swap(old, new, "tplPals")

# 4. the design picker rows
rows = []
for t in NEW:
    first = next(iter(EXTRA[t]["palettes"].values()))
    col = hexcol(first["--bg"] if t in DARK else first["--acc"])
    vibe = " \\u00b7 ".join(THEMES[t]["vibe"].split(" · ")[:2]).replace("'", "\\'")
    rows.append("                            <dynamic>[\n"
                f"                              '{t}',\n"
                f"                              '{THEMES[t]['name']}',\n"
                f"                              '{vibe}',\n"
                f"                              const Color({col})\n"
                "                            ],\n")
old = ("                              'Winter \\u00b7 snow & candlelight',\n"
       "                              const Color(0xFF3F7C9B)\n"
       "                            ],\n"
       "                          ].map((List<dynamic> t) {")
new = ("                              'Winter \\u00b7 snow & candlelight',\n"
       "                              const Color(0xFF3F7C9B)\n"
       "                            ],\n" + "".join(rows) +
       "                          ].map((List<dynamic> t) {")
swap(old, new, "picker rows")

OUT.write_text(s, encoding="utf-8", newline="\n")
print(f"wrote {OUT} ({len(s):,} chars); templates now {13 + len(NEW)}")
