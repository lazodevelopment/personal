r"""apply_sitefoot.py - JC-LAZO-WWS-1014-FOOT
The wedding-website hub and its 31 style/intent pages were hand-built before
the site footer moved to generate/templates/_footer.html, so they kept a
short four-column footer of their own. This gives them the real one:

  - the markup is rendered from _footer.html exactly as deploy/swap_footer.py
    does (Phoenix context, every built city), so it can never drift;
  - the footer's own rules are lifted from dist/assets/lazo.css (only rules
    whose selector mentions the footer, with their @media wrappers) and the
    variables they use are set on .site-foot, so nothing on the page changes;
  - the phone accordion from lazo.js comes along.

The 21 couple designs are left alone: a couple's site has its own small
"Made with Lazo" footer on purpose. Idempotent (tagged blocks are replaced).

  python wedding-websites\apply_sitefoot.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "wedding-websites"
sys.path.insert(0, str(ROOT / "deploy"))
sys.path.insert(0, str(ROOT))
from swap_footer import renderer  # noqa: E402

TAG = "JC-LAZO-WWS-1014-FOOT"
VARS = {"--gold": "#D9B77C", "--night": "#2E1530", "--plum-deep": "#3D1C3B",
        "--sans": "Inter,system-ui,sans-serif", "--serif": '"Cormorant Garamond",Georgia,serif',
        "--ease-out": "cubic-bezier(.16,1,.3,1)", "--ease-std": "cubic-bezier(.4,0,.2,1)",
        "--t-hover": "220ms", "--t-press": "90ms", "--t-release": "260ms"}


def footer_css():
    css = (ROOT / "dist" / "assets" / "lazo.css").read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out, i, n = [], 0, len(css)
    while i < n:
        j = css.find("{", i)
        if j < 0:
            break
        head = css[i:j].strip()
        if head.startswith("@media") or head.startswith("@supports"):
            depth, k = 1, j + 1
            while k < n and depth:
                depth += {"{": 1, "}": -1}.get(css[k], 0)
                k += 1
            inner = css[j + 1:k - 1]
            rules = re.findall(r"([^{}]+)\{([^{}]*)\}", inner)
            keep = [f"{s.strip()}{{{b.strip()}}}" for s, b in rules if "foot" in s]
            if keep:
                out.append(f"{head}{{{''.join(keep)}}}")
            i = k
        else:
            k = css.find("}", j)
            if "foot" in head and not head.startswith("@"):
                out.append(f"{head}{{{css[j + 1:k].strip()}}}")
            i = k + 1
    root = ".site-foot{" + ";".join(f"{k}:{v}" for k, v in VARS.items()) + "}"
    return root + "\n" + "\n".join(out)


def accordion_js():
    js = (ROOT / "dist" / "assets" / "lazo.js").read_text(encoding="utf-8")
    a = js.index("/* ---- footer accordions (phones only) ---- */")
    b = js.index("(function () {", a)
    depth, k = 0, b
    while True:   # the IIFE ends at the matching "})();"
        c = js[k]
        depth += {"{": 1, "}": -1}.get(c, 0)
        k += 1
        if depth == 0 and c == "}":
            break
    end = js.index(")();", k) + 4
    return "(function(){var d=document;" + js[b:end] + "})();"


def main():
    footer = renderer()(None)
    css, js = footer_css(), accordion_js()
    block_css = f"\n<style id=\"lzfoot\">/* {TAG} */\n{css}\n</style>\n"
    block_js = f"\n<script>/* {TAG} */\n{js}\n</script>\n"
    pages = [SRC / "index.html"] + sorted(p for p in SRC.glob("*/index.html") if not p.parent.name.startswith("_"))
    done = 0
    for p in pages:
        s = p.read_text(encoding="utf-8")
        if 'class="fcopy"' not in s and 'class="site-foot"' not in s:
            continue   # a couple design, not a guide page
        s = re.sub(r'\n<style id="lzfoot">.*?</style>\n', "", s, flags=re.S)
        s = re.sub(rf"\n<script>/\* {TAG} \*/.*?</script>\n", "", s, flags=re.S)
        s, k = re.subn(r'<footer>\s*<div class="fin">.*?</footer>|<footer class="site-foot">.*?</footer>', lambda m: footer, s, count=1, flags=re.S)
        if not k:
            print("  no footer:", p.parent.name)
            continue
        h = s.find("</head>")
        s = s[:h] + block_css + s[h:]
        b = s.rfind("</body>")
        s = s[:b] + block_js + s[b:]
        p.write_text(s, encoding="utf-8", newline="\n")
        done += 1
    print(f"site footer on {done} pages")


if __name__ == "__main__":
    main()
