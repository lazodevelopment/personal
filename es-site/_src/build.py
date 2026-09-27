#!/usr/bin/env python3
"""Elizabeth Scott — static site builder. Mirrors the Atavia architecture.
Run: python _src/build.py   (after any generator)"""
import pathlib, re, glob, html as H

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "_src"
BASE = "https://elizabethscottweddings.com"

NAV = (SRC / "partials" / "nav.html").read_text(encoding="utf-8")
FOOTER = (SRC / "partials" / "footer.html").read_text(encoding="utf-8")
DEFS = (SRC / "partials" / "wordmark-defs.html").read_text(encoding="utf-8")

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>%%TITLE%%</title>
<meta name="description" content="%%DESC%%">
<meta name="robots" content="%%ROBOTS%%">
<link rel="canonical" href="%%CANON%%">
<meta property="og:type" content="website">
<meta property="og:title" content="%%TITLE%%">
<meta property="og:description" content="%%DESC%%">
<meta property="og:url" content="%%CANON%%">
<meta property="og:image" content="https://elizabethscottweddings.com/og-image.jpg">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon/favicon-32.png" sizes="32x32">
<link rel="icon" href="/favicon/favicon-16.png" sizes="16x16">
<link rel="apple-touch-icon" href="/favicon/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preconnect" href="https://images.weserv.nl">
<link rel="preconnect" href="https://firebasestorage.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;1,400&family=Figtree:wght@300;400;500;600&family=Alex+Brush&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/css/site.css">
%%SCHEMA%%
</head>
<body>
%%DEFS%%
%%NAV%%
%%BODY%%
%%FOOTER%%
<script src="/assets/js/site.js" defer></script>
<script src="/assets/js/esw-track.js" defer></script>
<script src="/assets/js/es-pixel.js" defer></script>
</body>
</html>"""

ORG_SCHEMA = ('<script type="application/ld+json">' + __import__("json").dumps({
  "@context": "https://schema.org", "@type": "Organization",
  "name": "Elizabeth Scott", "alternateName": "Elizabeth Scott Weddings", "url": BASE + "/",
  "logo": BASE + "/favicon/icon-512.png",
  "description": "Wedding photography and videography studio serving all 50 states — travel included.",
  "email": "info@elizabethscottweddings.com",
  "sameAs": ["https://www.instagram.com/elizabethscottweddings",
             "https://www.facebook.com/elizabethscottweddings",
             "https://www.linkedin.com/company/elizabethscottweddings"]}) + '</script>')

PAGES = [
    dict(slug="index", out="index.html", nav="home",
         title="Elizabeth Scott | Wedding Photographer &amp; Videographer",
         desc="Award-caliber wedding photography &amp; videography with travel included in all 50 states. Packages from $1,200 — check your date with Elizabeth Scott.",
         canon=BASE + "/", schema=True),
    dict(slug="about", out="about.html", nav="about",
         title="About Elizabeth Scott — Wedding Photography &amp; Film Studio",
         desc="The story and standard behind Elizabeth Scott — a national wedding studio built on presence, artistry, and a signature client experience.",
         canon=BASE + "/about"),
    dict(slug="packages", out="packages.html", nav="packages",
         title="Wedding Photography &amp; Videography Packages + Prices | Elizabeth Scott",
         desc="Transparent wedding photo &amp; video packages: photography from $1,500, films from $1,200, combined from $3,000. Travel included, $500 reserves your date.",
         canon=BASE + "/packages"),
    dict(slug="portfolio", out="portfolio.html", nav="portfolio",
         title="Wedding Photography Portfolio — 463 Real Frames | Elizabeth Scott",
         desc="Selected wedding photography and film by Elizabeth Scott — moments signed with intention.",
         canon=BASE + "/portfolio"),
    dict(slug="films", out="films.html", nav="films",
         title="Cinematic Wedding Films &amp; Videography | Elizabeth Scott",
         desc="Cinematic wedding films by Elizabeth Scott — story-first edits that let you relive the day exactly as it felt.",
         canon=BASE + "/films"),
    dict(slug="faqs", out="faqs.html", nav="faqs",
         title="Wedding Photographer FAQs — Travel, Pricing, Raw Footage | Elizabeth Scott",
         desc="Answers to the questions couples ask most — travel, timelines, delivery, raw footage, and how to reserve your date with Elizabeth Scott.",
         canon=BASE + "/faqs"),
    dict(slug="contact", out="contact.html", nav="contact",
         title="Check Your Wedding Date | Elizabeth Scott",
         desc="Tell us about your wedding day. Elizabeth Scott books a limited number of dates each year — check yours.",
         canon=BASE + "/book/", robots="noindex, follow"),   # /contact 301s to /book/ at the edge; keep it out of the sitemap
    dict(slug="thank-you", out="thank-you.html", nav="",
         title="Thank You | Elizabeth Scott",
         desc="Your inquiry is in — we&rsquo;ll be in touch within one business day.",
         canon=BASE + "/thank-you", robots="noindex, follow"),
    dict(slug="privacy", out="privacy.html", nav="",
         title="Privacy Policy | Elizabeth Scott",
         desc="Privacy policy for elizabethscottweddings.com.",
         canon=BASE + "/privacy"),
    dict(slug="terms", out="terms.html", nav="",
         title="Terms of Service | Elizabeth Scott",
         desc="Terms of service for elizabethscottweddings.com.",
         canon=BASE + "/terms"),
    dict(slug="404", out="404.html", nav="",
         title="Page Not Found | Elizabeth Scott",
         desc="That page has wandered off.",
         canon=BASE + "/404", robots="noindex"),
]

try:
    from city_pages import CITY_PAGES
except ImportError:
    CITY_PAGES = []
try:
    from guide_pages import GUIDE_PAGES
except ImportError:
    GUIDE_PAGES = []


# ---------------- honest lastmod (JC-ESW-VENUES-0910) ----------------
# A URL's <lastmod> moves only when the page content changes: hash the region between
# the nav and the footer, remember the date the hash last changed.
import json as _json, hashlib as _hashlib, datetime as _dt, re as _re
_LM_PATH = SRC / "lastmod_cache.json"
try:
    LASTMOD = _json.loads(_LM_PATH.read_text(encoding="utf-8"))
except Exception:
    LASTMOD = {}
_TODAY = _dt.date.today().isoformat()
_BODY_RE = _re.compile(r"</nav>(.*?)<footer", _re.S)

def lastmod_for(canon, html, floor="2026-08-16"):
    m = _BODY_RE.search(html or "")
    core = m.group(1) if m else (html or "")
    core = _re.sub(r'\?token=[a-f0-9-]+', "", core)
    digest = _hashlib.sha1(core.encode("utf-8", "ignore")).hexdigest()[:16]
    entry = LASTMOD.get(canon)
    if entry and entry.get("hash") == digest:
        return entry.get("lastmod", floor)
    date = _TODAY if entry else floor
    LASTMOD[canon] = {"hash": digest, "lastmod": date}
    return date

def save_lastmod_cache():
    _LM_PATH.write_text(_json.dumps(LASTMOD, indent=0, sort_keys=True), encoding="utf-8")


def render_page(title, desc, canon, body, schema="", robots="index, follow", nav_key=""):
    nav = NAV.replace('data-nav="%s"' % nav_key, 'data-nav="%s" aria-current="page"' % nav_key) if nav_key else NAV
    return (TEMPLATE
            .replace("%%TITLE%%", title)
            .replace("%%DESC%%", desc)
            .replace("%%ROBOTS%%", robots)
            .replace("%%CANON%%", canon)
            .replace("%%SCHEMA%%", schema)
            .replace("%%DEFS%%", DEFS)
            .replace("%%NAV%%", nav)
            .replace("%%BODY%%", body)
            .replace("%%FOOTER%%", FOOTER))


def main():
    rows = []
    for p in PAGES:
        body = (SRC / "pages" / (p["slug"] + ".html")).read_text(encoding="utf-8")
        schema = ORG_SCHEMA if p.get("schema") else ""
        html = render_page(p["title"], p["desc"], p["canon"], body, schema,
                           p.get("robots", "index, follow"), p["nav"])
        (ROOT / p["out"]).write_text(html, encoding="utf-8")
        if "noindex" not in p.get("robots", ""):
            rows.append((p["canon"], "1.0" if p["slug"] == "index" else "0.8", lastmod_for(p["canon"], html)))
    for canon, prio in GUIDE_PAGES:
        rows.append((canon, prio, None))
    print("wrote %d core pages" % len(PAGES))

    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u, pr, lm in rows:
        xml.append('  <url><loc>%s</loc>%s<priority>%s</priority></url>' % (u, ("<lastmod>%s</lastmod>" % lm) if lm else "", pr))
    xml.append("</urlset>")
    (ROOT / "sitemap-core.xml").write_text("\n".join(xml), encoding="utf-8")
    save_lastmod_cache()
    print("wrote sitemap-core.xml (%d urls)" % len(rows))

    maps = sorted(x.name for x in ROOT.glob("sitemap-*.xml"))
    idx = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for m in maps:
        try:
            dates = _re.findall(r"<lastmod>(\d{4}-\d{2}-\d{2})</lastmod>", (ROOT / m).read_text(encoding="utf-8"))
        except Exception:
            dates = []
        idx.append("  <sitemap><loc>%s/%s</loc>%s</sitemap>" % (BASE, m, ("<lastmod>%s</lastmod>" % max(dates)) if dates else ""))
    idx.append("</sitemapindex>")
    (ROOT / "sitemap.xml").write_text("\n".join(idx), encoding="utf-8")
    print("wrote sitemap.xml (index of %d sitemaps: %s)" % (len(maps), ", ".join(maps)))


if __name__ == "__main__":
    main()
