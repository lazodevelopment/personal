"""Serve resized image variants (Resize Images extension) on the site.
Rewrites cover/gallery URLs to tokenless _1600x1600 variants (public-read rules
make tokens unnecessary). Run once from lazo-directory root AFTER installing
the extension."""
from pathlib import Path
bp = Path("generate/build.py")
src = bp.read_text(encoding="utf-8")
if "def _img_variant" in src:
    print("Already patched.")
    raise SystemExit

anchor = "def saturday_enrich(vendors):"
assert anchor in src, "run repair/saturday patches first"
helper = '''from urllib.parse import unquote as _uq, quote as _q

def _img_variant(u, size="1600x1600"):
    """Firebase Storage download URL -> tokenless resized-variant URL."""
    try:
        if not u or "/o/" not in u:
            return u
        base, rest = u.split("/o/", 1)
        enc = rest.split("?", 1)[0]
        path = _uq(enc)
        tail = path.rsplit("/", 1)[-1]
        if "." in tail:
            stem, ext = path.rsplit(".", 1)
            newp = f"{stem}_{size}.{ext}"
        else:
            newp = f"{path}_{size}"
        return f"{base}/o/{_q(newp, safe='')}?alt=media"
    except Exception:
        return u

def saturday_enrich(vendors):'''
src = src.replace(anchor, helper, 1)

anchor2 = "        # card display fields"
assert anchor2 in src, "cards patch missing - run patch_build_cards.py first"
inject = '''        # serve resized variants, keep originals for lightbox links
        if v.get("coverUrl"):
            v["coverUrlFull"] = v["coverUrl"]
            v["coverUrl"] = _img_variant(v["coverUrl"])
        if v.get("gallery"):
            v["galleryFull"] = list(v["gallery"])
            v["gallery"] = [_img_variant(g) for g in v["gallery"]]

        # card display fields'''
src = src.replace(anchor2, inject, 1)
bp.write_text(src, encoding="utf-8")
print("PATCHED: site serves 1600px variants; originals preserved as *Full.")
