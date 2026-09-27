"""patch_seo.py - JC-LAZO-WWSEO-0919-001
Gives every wedding-website template (and _base.html) a canonical URL, share
tags and JSON-LD, and a keyword-carrying title/description from themes.json.
Idempotent: the block sits between <!-- lz-seo --> and <!-- /lz-seo --> and is
replaced on re-runs. The worker strips this block when it hydrates a couple's
site at /w/{slug}, so demo-page SEO never leaks onto a real couple's page.

  python wedding-websites\\patch_seo.py            # all templates + _base.html
  python wedding-websites\\patch_seo.py fete sage  # some
"""
import json, re, sys, html
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE_URL = "https://meetlazo.com/wedding-websites"
THEMES = json.loads((ROOT / "themes.json").read_text(encoding="utf-8"))
HERO_RX = re.compile(r'https://images\.unsplash\.com/photo-[A-Za-z0-9_-]+\?[^"\' )]*')


def block(slug, name, title, desc, image):
    url = f"{BASE_URL}/{slug}/"
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Lazo", "item": "https://meetlazo.com/"},
            {"@type": "ListItem", "position": 2, "name": "Wedding websites", "item": BASE_URL + "/"},
            {"@type": "ListItem", "position": 3, "name": name, "item": url}]},
        {"@type": "WebPage", "@id": url, "url": url, "name": title, "description": desc,
         "isPartOf": {"@type": "WebSite", "name": "Lazo", "url": "https://meetlazo.com/"},
         "primaryImageOfPage": image,
         "mainEntity": {"@type": "CreativeWork", "name": f"{name} wedding website template",
                        "isAccessibleForFree": True, "genre": "wedding website template",
                        "provider": {"@type": "Organization", "name": "Lazo", "url": "https://meetlazo.com/"}}}]}
    e = html.escape
    ldjson = json.dumps(ld, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return ("<!-- lz-seo -->\n"
            f'<link rel="canonical" href="{url}">\n'
            '<meta property="og:type" content="website">\n<meta property="og:site_name" content="Lazo">\n'
            f'<meta property="og:url" content="{url}">\n<meta property="og:title" content="{e(title)}">\n'
            f'<meta property="og:description" content="{e(desc)}">\n<meta property="og:image" content="{e(image)}">\n'
            '<meta name="twitter:card" content="summary_large_image">\n'
            f'<meta name="twitter:title" content="{e(title)}">\n<meta name="twitter:image" content="{e(image)}">\n'
            '<script type="application/ld+json">' + ldjson + "</script>\n"
            "<!-- /lz-seo -->\n")


def patch(path, slug, name, title, desc):
    s = path.read_text(encoding="utf-8")
    s = re.sub(r"<!-- lz-seo -->.*?<!-- /lz-seo -->\n", "", s, flags=re.S)
    m = HERO_RX.search(s)
    image = "@@HERO_IMG@@" if slug.startswith("@@") else (m.group(0) if m else "https://meetlazo.com/assets/brand.png")
    if not slug.startswith("@@"):
        s = re.sub(r"<title>[^<]*</title>", "<title>" + html.escape(title) + "</title>", s, count=1)
        s = re.sub(r'<meta name="description" content="[^"]*">',
                   '<meta name="description" content="' + html.escape(desc, quote=True) + '">', s, count=1)
    anchor = '<meta name="theme-color" content="#52284F">\n'
    if anchor not in s:
        raise SystemExit(f"{path}: theme-color anchor missing")
    s = s.replace(anchor, anchor + block(slug, name, title, desc, image), 1)
    path.write_text(s, encoding="utf-8", newline="\n")
    print(f"  {slug}: seo block written")


if __name__ == "__main__":
    want = sys.argv[1:] or list(THEMES)
    for slug in want:
        t = THEMES[slug]
        patch(ROOT / slug / "index.html", slug, t["name"], t["title"], t["desc"])
    if not sys.argv[1:]:
        # the tokenised base: make_themes.py fills @@TITLE@@/@@DESC@@; the block carries tokens too
        patch(ROOT / "_base.html", "@@SLUG@@", "@@NAME@@", "@@TITLE@@", "@@DESC@@")
