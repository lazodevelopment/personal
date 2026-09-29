#!/usr/bin/env python3
"""Assemble Atavia Weddings static pages from shared partials + per-page bodies."""
import os, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "_src"
OG = "https://firebasestorage.googleapis.com/v0/b/atavia-c29cd.firebasestorage.app/o/atavia16.png?alt=media&token=4fff66fd-0144-474e-8fc1-d4ad8b6ab499"
BASE = "https://ataviaweddings.com"

NAV = (SRC / "partials" / "nav.html").read_text(encoding="utf-8")
FOOTER = (SRC / "partials" / "footer.html").read_text(encoding="utf-8")

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<!-- Meta Pixel Code -->
<script>
!function(f,b,e,v,n,t,s)
{if(f.fbq)return;n=f.fbq=function(){n.callMethod?
n.callMethod.apply(n,arguments):n.queue.push(arguments)};
if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
n.queue=[];t=b.createElement(e);t.async=!0;
t.src=v;s=b.getElementsByTagName(e)[0];
s.parentNode.insertBefore(t,s)}(window, document,'script',
'https://connect.facebook.net/en_US/fbevents.js');
fbq('init', '1245257617279907');
fbq('track', 'PageView');
</script>
<noscript><img height="1" width="1" style="display:none"
src="https://www.facebook.com/tr?id=1245257617279907&amp;ev=PageView&amp;noscript=1"
/></noscript>
<!-- End Meta Pixel Code -->
<title>%%TITLE%%</title>
<meta name="description" content="%%DESC%%">
<link rel="canonical" href="%%CANON%%">
<meta name="robots" content="%%ROBOTS%%">
<meta name="google-site-verification" content="g9ebG0m_HPMu0qMDW3vs_NznSM7gqf9brhgms52KZdw">
<meta name="format-detection" content="telephone=no">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Atavia Weddings">
<meta property="og:title" content="%%TITLE%%">
<meta property="og:description" content="%%DESC%%">
<meta property="og:url" content="%%CANON%%">
<meta property="og:image" content="%%OG%%">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="%%TITLE%%">
<meta name="twitter:description" content="%%DESC%%">
<meta name="twitter:image" content="%%OG%%">
<meta name="theme-color" content="#1B1A18">
<link rel="icon" href="/assets/img/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/assets/img/favicon.svg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preconnect" href="https://images.weserv.nl">
<link rel="preconnect" href="https://firebasestorage.googleapis.com">
<link rel="preconnect" href="https://storage.googleapis.com">
<script async src="https://www.googletagmanager.com/gtag/js?id=G-1BKHBFDJVX"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','G-1BKHBFDJVX');</script>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;1,300;1,400;1,500;1,600&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/css/site.css">
%%SCHEMA%%
</head>
<body>
%%NAV%%
<main id="main">
%%BODY%%
</main>
%%FOOTER%%
<script src="/assets/js/site.js"></script>
<script src="/assets/js/atv-track.js" defer></script>
</body>
</html>
"""

ORG_SCHEMA = """<script type="application/ld+json">
{"@context":"https://schema.org","@type":"LocalBusiness","@id":"https://ataviaweddings.com/#business","name":"Atavia Weddings","description":"Wedding photography and videography for couples who value story over spectacle.","url":"https://ataviaweddings.com","telephone":"+1-336-537-9590","email":"info@ataviaweddings.com","image":"%%OG%%","priceRange":"$$-$$$","sameAs":["https://www.instagram.com/ataviaweddings"],"areaServed":"United States"}
</script>"""

PAGES = [
    dict(slug="index", out="index.html", nav="home",
         title="Atavia Weddings | Photo &amp; Video | Now Booking for 2027",
         desc="Wedding photo &amp; video that holds the moment as it happened. Atavia Weddings crafts cinematic films and timeless stills for couples who value story.",
         canon=BASE + "/", schema=True),
    dict(slug="about", out="about.html", nav="about",
         title="About | Atavia Weddings",
         desc="Meet the team behind Atavia Weddings. We're storytellers who believe your day deserves to be remembered exactly as it felt — present, unhurried, and beautifully real.",
         canon=BASE + "/about"),
    dict(slug="packages", out="packages.html", nav="packages",
         title="Packages &amp; Pricing | Atavia Weddings",
         desc="Wedding photography &amp; videography packages from Atavia Weddings. Transparent collections for film, photo, or both — a $500 deposit reserves your date.",
         canon=BASE + "/packages"),
    dict(slug="gallery", out="gallery.html", nav="gallery",
         title="Gallery | Atavia Weddings",
         desc="A gallery of wedding photography by Atavia Weddings. Stills with feeling — light, gesture, and the quiet space between vows, toasts, and the first dance.",
         canon=BASE + "/gallery"),
    dict(slug="films", out="films.html", nav="films",
         title="Our Films | Atavia Weddings",
         desc="Watch a selection of cinematic wedding films from Atavia Weddings. Real vows, real laughter, real moments — preserved in motion exactly as they happened.",
         canon=BASE + "/films", schema_html='<script type="application/ld+json">{"@context":"https://schema.org","@type":"ItemList","itemListElement":[{"@type":"ListItem","position":1,"item":{"@type":"VideoObject","name":"Atavia Weddings — Wedding Film No. I","description":"A cinematic wedding film by Atavia Weddings.","thumbnailUrl":"https://img.youtube.com/vi/uZusVNlqIck/maxresdefault.jpg","embedUrl":"https://www.youtube.com/embed/uZusVNlqIck","contentUrl":"https://www.youtube.com/watch?v=uZusVNlqIck"}},{"@type":"ListItem","position":2,"item":{"@type":"VideoObject","name":"Atavia Weddings — Wedding Film No. II","description":"A cinematic wedding film by Atavia Weddings.","thumbnailUrl":"https://img.youtube.com/vi/7tavgrx_A6g/maxresdefault.jpg","embedUrl":"https://www.youtube.com/embed/7tavgrx_A6g","contentUrl":"https://www.youtube.com/watch?v=7tavgrx_A6g"}},{"@type":"ListItem","position":3,"item":{"@type":"VideoObject","name":"Atavia Weddings — Wedding Film No. III","description":"A cinematic wedding film by Atavia Weddings.","thumbnailUrl":"https://img.youtube.com/vi/Y0MPCdi70j0/maxresdefault.jpg","embedUrl":"https://www.youtube.com/embed/Y0MPCdi70j0","contentUrl":"https://www.youtube.com/watch?v=Y0MPCdi70j0"}},{"@type":"ListItem","position":4,"item":{"@type":"VideoObject","name":"Atavia Weddings — Wedding Film No. IV","description":"A cinematic wedding film by Atavia Weddings.","thumbnailUrl":"https://img.youtube.com/vi/qX5z5E6WWWY/maxresdefault.jpg","embedUrl":"https://www.youtube.com/embed/qX5z5E6WWWY","contentUrl":"https://www.youtube.com/watch?v=qX5z5E6WWWY"}},{"@type":"ListItem","position":5,"item":{"@type":"VideoObject","name":"Atavia Weddings — Wedding Film No. V","description":"A cinematic wedding film by Atavia Weddings.","thumbnailUrl":"https://img.youtube.com/vi/Br4B0CrWFgc/maxresdefault.jpg","embedUrl":"https://www.youtube.com/embed/Br4B0CrWFgc","contentUrl":"https://www.youtube.com/watch?v=Br4B0CrWFgc"}},{"@type":"ListItem","position":6,"item":{"@type":"VideoObject","name":"Atavia Weddings — Wedding Film No. VI","description":"A cinematic wedding film by Atavia Weddings.","thumbnailUrl":"https://img.youtube.com/vi/FHT71US2Dvk/maxresdefault.jpg","embedUrl":"https://www.youtube.com/embed/FHT71US2Dvk","contentUrl":"https://www.youtube.com/watch?v=FHT71US2Dvk"}},{"@type":"ListItem","position":7,"item":{"@type":"VideoObject","name":"Atavia Weddings — Wedding Film No. VII","description":"A cinematic wedding film by Atavia Weddings.","thumbnailUrl":"https://img.youtube.com/vi/0fdcSWEmnF8/maxresdefault.jpg","embedUrl":"https://www.youtube.com/embed/0fdcSWEmnF8","contentUrl":"https://www.youtube.com/watch?v=0fdcSWEmnF8"}},{"@type":"ListItem","position":8,"item":{"@type":"VideoObject","name":"Atavia Weddings — Wedding Film No. VIII","description":"A cinematic wedding film by Atavia Weddings.","thumbnailUrl":"https://img.youtube.com/vi/z_fssLLMiG8/maxresdefault.jpg","embedUrl":"https://www.youtube.com/embed/z_fssLLMiG8","contentUrl":"https://www.youtube.com/watch?v=z_fssLLMiG8"}},{"@type":"ListItem","position":9,"item":{"@type":"VideoObject","name":"Atavia Weddings — Wedding Film No. IX","description":"A cinematic wedding film by Atavia Weddings.","thumbnailUrl":"https://img.youtube.com/vi/HUlVqIskRxw/maxresdefault.jpg","embedUrl":"https://www.youtube.com/embed/HUlVqIskRxw","contentUrl":"https://www.youtube.com/watch?v=HUlVqIskRxw"}},{"@type":"ListItem","position":10,"item":{"@type":"VideoObject","name":"Atavia Weddings — Wedding Film No. X","description":"A cinematic wedding film by Atavia Weddings.","thumbnailUrl":"https://img.youtube.com/vi/OjpHompR_ww/maxresdefault.jpg","embedUrl":"https://www.youtube.com/embed/OjpHompR_ww","contentUrl":"https://www.youtube.com/watch?v=OjpHompR_ww"}}]}</script>'),
    dict(slug="faqs", out="faqs.html", nav="faqs",
         title="FAQs | Atavia Weddings",
         desc="Answers to the questions couples ask most — deposits, travel, turnaround times, raw footage, drone coverage, and how booking with Atavia works.",
         canon=BASE + "/faqs"),
    dict(slug="contact", out="contact.html", nav="contact",
         title="Inquire | Atavia Weddings",
         desc="Inquire with Atavia Weddings about your wedding date. Tell us your venue, vision, and the way you'd like to be remembered — we'll respond within 24 hours.",
         canon=BASE + "/contact"),
    dict(slug="booked", out="booked/index.html", nav="",
         title="You&rsquo;re Booked | Atavia Weddings",
         desc="Your agreement is signed and your wedding date is reserved with Atavia Weddings. Here&rsquo;s what happens next.",
         canon=BASE + "/booked", robots="noindex, follow"),
    dict(slug="thank-you", out="thank-you.html", nav="",
         title="Thank You | Atavia Weddings",
         desc="Your inquiry is in — we&rsquo;ll be in touch within one business day.",
         canon=BASE + "/thank-you", robots="noindex, follow"),
    dict(slug="privacy", out="privacy.html", nav="",
         title="Privacy Policy | Atavia Weddings",
         desc="How Atavia Weddings collects, uses, and protects your information.",
         canon=BASE + "/privacy"),
    dict(slug="terms", out="terms.html", nav="",
         title="Terms of Service | Atavia Weddings",
         desc="The terms that govern use of the Atavia Weddings website and services.",
         canon=BASE + "/terms"),
    dict(slug="404", out="404.html", nav="",
         title="Page Not Found | Atavia Weddings",
         desc="The page you're looking for has moved or no longer exists.",
         canon=BASE + "/404", robots="noindex"),
]

# --- location landing pages (generated by gen_locations.py) ---
import sys
sys.path.insert(0, str(SRC))
try:
    from loc_pages import LOC_PAGES
except Exception:
    LOC_PAGES = []
try:
    from guide_pages import GUIDE_PAGES
except Exception:
    GUIDE_PAGES = []
PAGES = PAGES + LOC_PAGES + GUIDE_PAGES

# fill the footer "Serving Nationwide" strip: metros + hubs
_metros = [p for p in LOC_PAGES if p.get("tier") == "metro"]
_hub = [p for p in LOC_PAGES if p.get("tier") == "hub"]
_loclinks = "".join('<a href="/%s">%s</a>' % (p["slug"], p["footer_label"]) for p in _metros)
if _hub:
    _loclinks += '<a href="/%s" class="footer-locations__all">All 50 states &rarr;</a>' % _hub[0]["slug"]
_loclinks += '<a href="/venues/" class="footer-locations__all">Venue directory &rarr;</a>'
FOOTER = FOOTER.replace("%%LOCLINKS%%", _loclinks)

def set_active(html, nav_key):
    if not nav_key:
        return html
    needle = 'data-nav="%s"' % nav_key
    out = []
    for line in html.splitlines():
        if needle in line:
            if 'class="nav__link"' in line:
                line = line.replace('class="nav__link"', 'class="nav__link is-active"', 1)
            elif 'class="btn btn--copper nav__cta"' in line:
                line = line.replace('class="btn btn--copper nav__cta"', 'class="btn btn--copper nav__cta is-active"', 1)
            elif '<a data-nav="%s"' % nav_key in line:  # mobile menu link
                line = line.replace('<a data-nav', '<a class="is-active" data-nav', 1)
        out.append(line)
    return "\n".join(out)

def render_page(title, desc, canon, body, schema="", robots="index, follow", nav_key=""):
    """Wrap a page body in the shared shell. Used by build() and gen_venues.py."""
    return (TEMPLATE
            .replace("%%TITLE%%", title)
            .replace("%%DESC%%", desc)
            .replace("%%CANON%%", canon)
            .replace("%%ROBOTS%%", robots)
            .replace("%%SCHEMA%%", schema)
            .replace("%%NAV%%", set_active(NAV, nav_key))
            .replace("%%FOOTER%%", FOOTER)
            .replace("%%BODY%%", body)
            .replace("%%OG%%", OG))

def build():
    for p in PAGES:
        body = (SRC / "pages" / (p["slug"] + ".html")).read_text(encoding="utf-8")
        schema = p.get("schema_html") or (ORG_SCHEMA if p.get("schema") else "")
        html = render_page(p["title"], p["desc"], p["canon"], body, schema,
                           p.get("robots", "index, follow"), p["nav"])
        outp = ROOT / p["out"]
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(html, encoding="utf-8")
    print("wrote %d core pages" % len(PAGES))
    write_sitemap()
    write_sitemap_index()

# ---------------- honest lastmod ----------------
# A URL's <lastmod> only moves when the page's content actually changes. We hash the
# rendered body (everything inside <main>, so nav/footer/tracking tweaks don't count)
# and remember the date the hash last changed in _src/lastmod_cache.json.
import json as _json, hashlib as _hashlib, datetime as _dt, re as _re
_LM_PATH = SRC / "lastmod_cache.json"
try:
    LASTMOD = _json.loads(_LM_PATH.read_text(encoding="utf-8"))
except Exception:
    LASTMOD = {}
_TODAY = _dt.date.today().isoformat()
_MAIN_RE = _re.compile(r"<main\b.*?</main>", _re.S)

def lastmod_for(canon, html, floor="2026-07-03"):
    """Return the lastmod date for canon, updating the cache if the content changed."""
    m = _MAIN_RE.search(html or "")
    core = m.group(0) if m else (html or "")
    # ignore per-build noise that isn't content
    core = _re.sub(r'\?token=[a-f0-9-]+', "", core)
    digest = _hashlib.sha1(core.encode("utf-8", "ignore")).hexdigest()[:16]
    entry = LASTMOD.get(canon)
    if entry and entry.get("hash") == digest:
        return entry.get("lastmod", floor)
    date = _TODAY if entry else floor          # first sighting keeps the floor date, not "today"
    LASTMOD[canon] = {"hash": digest, "lastmod": date}
    return date

def save_lastmod_cache():
    _LM_PATH.write_text(_json.dumps(LASTMOD, indent=0, sort_keys=True), encoding="utf-8")

def write_sitemap():
    rows = []
    for p in PAGES:
        if p["slug"] == "404" or str(p.get("robots", "")).startswith("noindex"):
            continue
        slug = p["slug"]
        if slug == "index":
            pr, cf = "1.0", "weekly"
        elif slug in ("privacy", "terms"):
            pr, cf = "0.3", "yearly"
        elif slug in ("packages", "contact"):
            pr, cf = "0.9", "weekly"
        elif p.get("tier") in ("guide", "guidehub"):
            pr, cf = "0.8", "monthly"
        elif p.get("tier") == "venue":
            pr, cf = "0.7", "monthly"
        elif p.get("tier") == "venuehub":
            pr, cf = "0.8", "monthly"
        elif p.get("schema_html"):
            pr, cf = "0.8", "monthly"
        else:
            pr, cf = "0.7", "monthly"
        html_path = ROOT / p["out"]
        try:
            page_html = html_path.read_text(encoding="utf-8")
        except Exception:
            page_html = ""
        lm = lastmod_for(p["canon"], page_html)
        rows.append('  <url>\n    <loc>%s</loc>\n    <lastmod>%s</lastmod>\n    <changefreq>%s</changefreq>\n    <priority>%s</priority>\n  </url>' % (p["canon"], lm, cf, pr))
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(rows) + "\n</urlset>\n")
    (ROOT / "sitemap-core.xml").write_text(xml, encoding="utf-8")
    save_lastmod_cache()
    print("wrote sitemap-core.xml (%d urls)" % len(rows))

def write_sitemap_index():
    """Index every sitemap-*.xml (core + venue chunks written by gen_venues.py)."""
    maps = sorted(p.name for p in ROOT.glob("sitemap-*.xml"))
    def newest(m):
        try:
            dates = _re.findall(r"<lastmod>(\d{4}-\d{2}-\d{2})</lastmod>", (ROOT / m).read_text(encoding="utf-8"))
            return max(dates) if dates else "2026-07-03"
        except Exception:
            return "2026-07-03"
    rows = "\n".join(
        '  <sitemap><loc>%s/%s</loc><lastmod>%s</lastmod></sitemap>' % (BASE, m, newest(m))
        for m in maps)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + rows + "\n</sitemapindex>\n")
    (ROOT / "sitemap.xml").write_text(xml, encoding="utf-8")
    print("wrote sitemap.xml (index of %d sitemaps: %s)" % (len(maps), ", ".join(maps)))

if __name__ == "__main__":
    build()
