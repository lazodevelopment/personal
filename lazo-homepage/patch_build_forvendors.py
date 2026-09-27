"""Adds /for-vendors/ to build.py output + sitemap. Run once from lazo-directory root."""
from pathlib import Path
bp = Path("generate/build.py")
src = bp.read_text(encoding="utf-8")
if "for-vendors" in src:
    print("Already patched.")
    raise SystemExit
anchor = '    # sitemap + robots'
assert anchor in src, "anchor missing — send Claude the lines around the sitemap section"
inject = '''    # vendor landing page
    fv = env.get_template("for_vendors.html")
    fvdir = DIST / "for-vendors"
    fvdir.mkdir(exist_ok=True)
    (fvdir / "index.html").write_text(
        fv.render(base=BASE_URL,
                  vendor_total_display=vendor_total_display if "vendor_total_display" in dir() else "43,000",
                  metro_count=len(live_metros)),
        encoding="utf-8")
    urls.append(f"{BASE_URL}/for-vendors/")

    # sitemap + robots'''
src = src.replace(anchor, inject)
bp.write_text(src, encoding="utf-8")
print("PATCHED: /for-vendors/ renders every build.")
