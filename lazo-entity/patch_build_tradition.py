"""Adds the /what-is-a-lazo/ page to build.py output + sitemap.
Run once from lazo-directory root:  python patch_build_tradition.py
Then every build (incl. nightly) renders the page automatically."""
from pathlib import Path

bp = Path("generate/build.py")
src = bp.read_text(encoding="utf-8")

MARK = "what-is-a-lazo"
if MARK in src:
    print("Already patched — nothing to do.")
    raise SystemExit

anchor = '    # sitemap + robots'
assert anchor in src, "anchor not found — paste build.py lines around sitemap to Claude"
inject = '''    # standalone pages (entity/content)
    trad_src = ROOT / "generate" / "templates" / "lazo_tradition.html"
    if trad_src.exists():
        pdir = DIST / "what-is-a-lazo"
        pdir.mkdir(exist_ok=True)
        (pdir / "index.html").write_text(trad_src.read_text(encoding="utf-8"), encoding="utf-8")
        urls.append(f"{BASE_URL}/what-is-a-lazo/")

    # sitemap + robots'''
src = src.replace(anchor, inject)
bp.write_text(src, encoding="utf-8")
print("PATCHED: build.py now renders /what-is-a-lazo/ every build.")
