"""Card enrichment: cardCity, bioSnippet, thumbUrl, hasOffer, alsoCats.
Run once from lazo-directory root (after patch_build_saturday.py)."""
from pathlib import Path
bp = Path("generate/build.py")
src = bp.read_text(encoding="utf-8")
if "cardCity" in src:
    print("Already patched.")
    raise SystemExit
anchor = "        # video embed"
assert anchor in src, "enrich anchor missing — run patch_build_saturday.py first"
inject = '''        # card display fields
        addr = str(v.get("address") or "")
        parts = [p.strip() for p in addr.split(",") if p.strip()]
        v["cardCity"] = parts[1] if len(parts) >= 4 else (parts[0] if parts else "")
        bio = str(v.get("bio") or "").strip()
        if bio:
            v["bioSnippet"] = bio if len(bio) <= 110 else bio[:110].rsplit(" ", 1)[0] + "\\u2026"
        cov = v.get("coverUrl") or ""
        gal = v.get("gallery") or []
        v["thumbUrl"] = cov or (gal[0] if gal else None)
        ann = v.get("announcement") or {}
        v["hasOffer"] = bool(isinstance(ann, dict) and ann.get("title"))
        v["alsoCats"] = [BY_SLUG[c]["singular"] for c in (v.get("categories") or []) if c in BY_SLUG]

        # video embed'''
src = src.replace(anchor, inject, 1)
bp.write_text(src, encoding="utf-8")
print("PATCHED: card fields computed at build.")
