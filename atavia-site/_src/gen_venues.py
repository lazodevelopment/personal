#!/usr/bin/env python3
"""
gen_venues.py — Atavia venue directory generator (scales to thousands of pages).

Reads _src/venues_data.py (seeded/extended by fetch_venues.py) and emits a
4-level hierarchy, plus split sitemaps:

    /venues/                                  master hub  — all states
    /venues/<state>/                          state hub   — all cities in state
    /venues/<state>/<city>/                   city hub    — all venues in city
    /venues/<state>/<city>/<venue>            venue page  — the money page

Run:  python3 _src/gen_venues.py && python3 _src/build.py
(gen_venues writes sitemap-venues-N.xml; build.py then writes the sitemap index.)

Every venue page carries a nominative-fair-use disclaimer — Atavia is not
affiliated with these venues.
"""
import re, sys, math, pathlib

SRC = pathlib.Path(__file__).resolve().parent
ROOT = SRC.parent
sys.path.insert(0, str(SRC))

import build as B
import urllib.parse as _up
from venue_photos import PHOTOS

_FB = "https://firebasestorage.googleapis.com/v0/b/atavia-c29cd.firebasestorage.app/o/"
def _vp_direct(slug_, n):
    return _FB + _up.quote("venue-photos/%s-%d.jpg" % (slug_, n), safe="") + "?alt=media"
def _vp_weserv(slug_, n, params):
    return "https://images.weserv.nl/?url=" + _up.quote(_vp_direct(slug_, n), safe="") + params

_VP_LIGHTBOX = ('<div class="glb" id="galleryLightbox" role="dialog" aria-modal="true" aria-label="Photo viewer">'
    '<button class="glb__close" aria-label="Close">&times;</button>'
    '<button class="glb__nav glb__prev" aria-label="Previous photo">&larr;</button>'
    '<img class="glb__img" src="" alt="Atavia wedding photograph">'
    '<button class="glb__nav glb__next" aria-label="Next photo">&rarr;</button>'
    '<div class="glb__count"></div></div>')

def venue_photos_html(slug_, name_h):
    count = PHOTOS.get(slug_, 0)
    if not count:
        return ""
    cells = []
    for n in range(1, count + 1):
        thumb = _vp_weserv(slug_, n, "&amp;w=700&amp;q=80&amp;output=webp")
        full  = _vp_weserv(slug_, n, "&amp;w=1920&amp;q=82&amp;output=webp")
        cells.append('<div class="venue-photos__item" data-glb="%s" data-glb-full="%s">'
                     '<img src="%s" alt="Wedding at %s photographed by Atavia Weddings" loading="lazy" decoding="async"></div>'
                     % (thumb, full, thumb, name_h))
    return ('<div class="venue-photos reveal d2"><div class="venue-photos__label">Our work at this venue</div>'
            '<div class="venue-photos__grid">%s</div></div>%s' % ("".join(cells), _VP_LIGHTBOX))
                      # shared shell: render_page(), BASE
from venues_data import VENUES

# ---------------- indexing tiers (JC-ATV-SEO-0910) ----------------
# Google will not index 18K near-identical pages on a site this size, and a sitemap it
# ignores 95% of costs trust. So each venue page earns its place in the index:
#   A  filmed_here / has photos / already earns Google impressions   -> index, sitemap
#   B  has a written `character` line (page has something venue-specific) -> index, sitemap (up to the cap)
#   C  nothing specific yet                                          -> noindex,follow, not in sitemap
# City hubs with no indexable venue are noindexed too. Everything still exists and still
# links, so couples can navigate — we just stop asking Google to index thin pages.
import json as _json
MAX_INDEX = 2500                                  # sitemap budget for venue pages (A always kept)
_GSC = {}                                         # canon -> impressions, from _src/gsc_pages*.csv (optional)
# Every Search Console "Pages" export dropped in _src as gsc_pages*.csv counts; www and
# apex rows fold together (www 301s to apex). Keep the highest figure seen per URL.
import csv as _csv
for _path in sorted(SRC.glob("gsc_pages*.csv")):
    with open(_path, newline="", encoding="utf-8") as _f:
        for _row in _csv.DictReader(_f):
            _u = (_row.get("Top pages") or _row.get("Page") or _row.get("URL") or "").strip()
            _u = _u.replace("://www.", "://").rstrip("/")
            try:
                _GSC[_u] = max(_GSC.get(_u, 0), int(float((_row.get("Impressions") or "0").replace(",", ""))))
            except ValueError:
                pass
_GENERIC = {"", "a wedding and event venue", "a wedding venue", "an event venue", "a venue"}
def venue_tier(v, canon):
    ch = (v.get("character") or "").strip().lower().rstrip(".")
    if v.get("filmed_here") or PHOTOS.get(slug(v["name"])) or _GSC.get(canon.rstrip("/"), 0) > 0:
        return "A"
    if ch and ch not in _GENERIC and len(ch) > 24:
        return "B"
    return "C"

REPORT_ONLY = "--report" in sys.argv

BASE = B.BASE
OUT = ROOT / "venues"
CHUNK = 2000                            # urls per sitemap chunk

STATES = {
 "AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California","CO":"Colorado",
 "CT":"Connecticut","DE":"Delaware","FL":"Florida","GA":"Georgia","HI":"Hawaii","ID":"Idaho",
 "IL":"Illinois","IN":"Indiana","IA":"Iowa","KS":"Kansas","KY":"Kentucky","LA":"Louisiana",
 "ME":"Maine","MD":"Maryland","MA":"Massachusetts","MI":"Michigan","MN":"Minnesota",
 "MS":"Mississippi","MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada",
 "NH":"New Hampshire","NJ":"New Jersey","NM":"New Mexico","NY":"New York",
 "NC":"North Carolina","ND":"North Dakota","OH":"Ohio","OK":"Oklahoma","OR":"Oregon",
 "PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota",
 "TN":"Tennessee","TX":"Texas","UT":"Utah","VT":"Vermont","VA":"Virginia","WA":"Washington",
 "WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming","DC":"District of Columbia",
}
# city -> metro landing page (links the directory into the metro pages)
METRO_PAGE = {
 "Dallas":"dallas-wedding-videographer","Denver":"denver-wedding-videographer",
 "Phoenix":"phoenix-wedding-videographer","Scottsdale":"phoenix-wedding-videographer",
 "Minneapolis":"minneapolis-wedding-videographer","Boston":"boston-wedding-videographer",
 "Chicago":"chicago-wedding-videographer","Los Angeles":"los-angeles-wedding-videographer",
 "New York":"new-york-wedding-videographer","Miami":"miami-wedding-videographer",
 "Atlanta":"atlanta-wedding-videographer","Las Vegas":"las-vegas-wedding-videographer",
}

HERO = "https://firebasestorage.googleapis.com/v0/b/atavia-c29cd.firebasestorage.app/o/DSC_4772.jpg?alt=media&token=5182d7b9-096f-4902-a8b6-7ef2cd2e865a"
CTA  = "https://firebasestorage.googleapis.com/v0/b/atavia-c29cd.firebasestorage.app/o/atavia16.png?alt=media&token=4fff66fd-0144-474e-8fc1-d4ad8b6ab499"
KNOT = "https://firebasestorage.googleapis.com/v0/b/atavia-c29cd.firebasestorage.app/o/The-Knot-vendor-badge.webp?alt=media&token=f928d4da-e25e-4594-8098-57e56aebbfc0"
ZOLA = "https://firebasestorage.googleapis.com/v0/b/atavia-c29cd.firebasestorage.app/o/Zola-Vendor-Badge-Utah-Live-Bands.png?alt=media&token=4e2c2497-f24d-4ede-b543-ac3e8196eb31"
KNOT_URL = "https://www.theknot.com/marketplace/atavia-weddings-boston-ma-2104981"
ZOLA_URL = "https://www.zola.com/wedding-vendors/wedding-videographers/atavia-weddings--2"
LAZO = "https://meetlazo.com/badges/lazo-verified-plum.png"
LAZO_URL = "https://meetlazo.com/phoenix/wedding-videographers/atavia-weddings/?utm_source=ataviaweddings&utm_medium=badge&utm_campaign=featured-on"
def e(u): return u.replace("&", "&amp;")
def h(s): return (s or "").replace("&", "&amp;")

def slug(s):
    s = s.replace("&amp;", "and").replace("&", "and").lower()
    s = re.sub(r"[\u2019']", "", s)  # apostrophes vanish: river's -> rivers
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "x"

# normalize any HTML entities baked into the source data (names come from the
# API raw; the seed rows had &amp; in them). Store plain text; escape at render.
for _v in VENUES:
    for _k in ("name", "city", "address", "character"):
        if _v.get(_k):
            _v[_k] = _v[_k].replace("&amp;", "&").replace("&#39;", "'")

DISC = ('<section class="sec sec--tight"><div class="wrap" style="max-width:820px">'
        '<p class="venue-note">Atavia Weddings is an independent wedding photography and videography '
        'company. We are not affiliated with, endorsed by, or sponsored by any venue listed here. Venue '
        'names and trademarks are the property of their respective owners and are used for identification '
        'purposes only. Please confirm details, availability, and vendor policies directly with the venue.'
        '</p></div></section>')

def hero(eyebrow, title, sub, crumbs=""):
    return ('<section class="page-hero">'
      '<div class="page-hero__bg" aria-hidden="true"><img src="%s" alt="" onerror="this.onerror=null;this.src=\'%s\'"></div>'
      '<span class="page-hero__watermark" aria-hidden="true">A</span><div class="wrap">%s'
      '<div class="eyebrow center rules reveal">%s</div>'
      '<h1 class="page-hero__title reveal d1">%s</h1>'
      '<p class="page-hero__sub reveal d2">%s</p>'
      '<div style="margin-top:clamp(26px,4vw,36px)" class="reveal d3">'
      '<a href="/contact__CTAQS__" class="btn btn--copper">Check Your Date <span class="arr">&#8599;</span></a></div>'
      '</div></section>') % (e(HERO), HERO, crumbs, eyebrow, title, sub)

def cta(eyebrow, title):
    return ('<section class="cta-band cta-band--img" aria-label="Book Atavia Weddings">'
      '<img src="%s" alt="" loading="lazy" onerror="this.onerror=null;this.src=\'%s\'">'
      '<div class="wrap reveal"><span class="eyebrow center rules">%s</span>'
      '<h2 class="cta-band__title" style="font-size:clamp(28px,4.4vw,54px);margin-top:20px">%s</h2>'
      '<a href="/contact__CTAQS__" class="btn btn--copper" style="margin-top:26px">Reserve Your Date <span class="arr">&#8599;</span></a>'
      '</div></section>') % (e(CTA), CTA, eyebrow, title)

BADGES = ('<div class="badges-row reveal"><span class="lbl">As Featured On</span>'
  '<a class="badge-logo" href="%s" target="_blank" rel="noopener" aria-label="Atavia Weddings on The Knot"><img src="%s" alt="As seen on The Knot" loading="lazy"></a>'
  '<a class="badge-logo" href="%s" target="_blank" rel="noopener" aria-label="Atavia Weddings on Zola"><img src="%s" alt="Featured on Zola" loading="lazy"></a>'
  '<a class="badge-logo" href="%s" target="_blank" rel="noopener" aria-label="View Atavia Weddings on Lazo" title="Atavia Weddings on Lazo"><img src="%s" alt="Lazo Verified &mdash; Atavia Weddings" width="140" height="140" loading="lazy"></a></div>'
  ) % (KNOT_URL, e(KNOT), ZOLA_URL, e(ZOLA), e(LAZO_URL), LAZO)

def crumbs(*parts):
    bits = []
    for i, (label, href) in enumerate(parts):
        bits.append('<a href="%s">%s</a>' % (href, label) if href else '<span>%s</span>' % label)
    return '<nav class="crumbs" aria-label="Breadcrumb">%s</nav>' % ' <span>/</span> '.join(bits)

# ---------------- index the dataset ----------------
tree = {}      # state_abbr -> city -> [venue,...]
for v in VENUES:
    st = v["state"].upper()
    if st not in STATES:
        continue
    tree.setdefault(st, {}).setdefault(v["city"], []).append(v)

urls = []      # (loc, priority)
def write(path, html, prio):
    p = OUT / path if path else OUT / "index.html"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")

# ---------------- decide who gets indexed ----------------
TIER = {}          # canon -> "A" | "B" | "C"
_cands = []
for st, cities in tree.items():
    sname, sslug = STATES[st], slug(STATES[st])
    for city, vs in cities.items():
        cslug = slug(city)
        for v in vs:
            canon = "%s/venues/%s/%s/%s" % (BASE, sslug, cslug, slug(v["name"]))
            t = venue_tier(v, canon)
            TIER[canon] = t
            # B pages compete for the remaining budget: metro cities first, then bigger cities
            _cands.append((t, 0 if city in METRO_PAGE else 1, -len(vs), canon))
_a = [c for c in _cands if c[0] == "A"]
_b = sorted([c for c in _cands if c[0] == "B"])[:max(0, MAX_INDEX - len(_a))]
INDEX_SET = {c[3] for c in _a} | {c[3] for c in _b}
_counts = {"A": len(_a), "B": sum(1 for c in _cands if c[0] == "B"), "C": sum(1 for c in _cands if c[0] == "C")}
print("tiers: A=%d (always indexed)  B=%d (%d fit the %d budget)  C=%d (noindex)  -> %d venue pages in the index"
      % (_counts["A"], _counts["B"], len(_b), MAX_INDEX, _counts["C"], len(INDEX_SET)))
if REPORT_ONLY:
    import collections as _c
    by_state = _c.Counter()
    for st, cities in tree.items():
        for city, vs in cities.items():
            for v in vs:
                canon = "%s/venues/%s/%s/%s" % (BASE, slug(STATES[st]), slug(city), slug(v["name"]))
                if canon in INDEX_SET: by_state[STATES[st]] += 1
    for k, c in sorted(by_state.items(), key=lambda kv: -kv[1]):
        print("  %-22s %5d indexed" % (k, c))
    sys.exit(0)

def faq_html(name, city, sname, filmed):
    q1 = "Have you filmed a wedding at %s?" % name
    a1 = ("Yes &mdash; we&rsquo;ve worked at %s before, so we already know the light, the sound, and the timeline." % name) if filmed \
         else ("Not yet &mdash; and that&rsquo;s fine. We scout %s before your wedding so the light, the sound, and the timeline are planned, not discovered." % name)
    q2 = "Do you charge travel fees for weddings in %s, %s?" % (city, sname)
    a2 = "No. A local Atavia team covers %s, so there are no travel fees and no out-of-town crew." % city
    q3 = "What does it cost to book you for a wedding at %s?" % name
    a3 = "Collections start at $1,200 for film and $1,400 for photography; a $500 deposit reserves your date and every collection includes your raw footage."
    items = [(q1, a1), (q2, a2), (q3, a3)]
    html = ('<style>.venue-faq details{border-top:1px solid rgba(242,238,232,.12);padding:14px 0}.venue-faq details:last-child{border-bottom:1px solid rgba(242,238,232,.12)}'
            '.venue-faq summary{cursor:pointer;font-family:"Cormorant Garamond",serif;font-size:clamp(18px,2.2vw,22px);color:var(--ivory,#F2EEE8);list-style:none;display:flex;justify-content:space-between;gap:16px}'
            '.venue-faq summary::-webkit-details-marker{display:none}.venue-faq summary::after{content:"+";color:var(--copper);font-family:Inter,sans-serif;font-size:20px;flex:none}'
            '.venue-faq details[open] summary::after{content:"\\2013"}.venue-faq p{margin:10px 0 0;color:var(--ivory-dim);line-height:1.8;font-size:15.5px}</style>'
            '<section class="sec sec--tight"><div class="wrap" style="max-width:760px">'
            '<div class="sec__head reveal"><div class="sec__roman">Good to know</div>'
            '<h2 class="sec__title">Questions couples ask about <em>%s</em></h2><div class="rule"></div></div>'
            '<div class="venue-faq reveal d1">%s</div></div></section>') % (h(name),
            "".join('<details><summary>%s</summary><p>%s</p></details>' % (h(q), a) for q, a in items))
    import re as _r
    strip = lambda t: _r.sub(r"<[^>]+>", "", t).replace("&mdash;", "—").replace("&rsquo;", "’")
    schema = ('<script type="application/ld+json">{"@context":"https://schema.org","@type":"FAQPage","mainEntity":['
              + ",".join('{"@type":"Question","name":%s,"acceptedAnswer":{"@type":"Answer","text":%s}}' % (_json.dumps(strip(q)), _json.dumps(strip(a))) for q, a in items)
              + ']}</script>')
    return html, schema

# ---------------- venue pages ----------------
n_venue = 0
n_noindex = 0
for st, cities in tree.items():
    sname, sslug = STATES[st], slug(STATES[st])
    for city, vs in cities.items():
        cslug = slug(city)
        for v in vs:
            name, vslug = v["name"], slug(v["name"])
            canon = "%s/venues/%s/%s/%s" % (BASE, sslug, cslug, vslug)
            sibs = [x for x in vs if x["name"] != name][:6]
            sib_html = ""
            if sibs:
                links = "".join('<a href="/venues/%s/%s/%s">%s</a>' % (sslug, cslug, slug(x["name"]), h(x["name"])) for x in sibs)
                sib_html = ('<section class="sec sec--tight"><div class="wrap" style="max-width:940px">'
                  '<div style="text-align:center" class="reveal"><div class="eyebrow center rules">Other %s Venues</div>'
                  '<h2 class="sec__title" style="margin-top:14px;font-size:clamp(24px,3.2vw,38px)">We also shoot at</h2></div>'
                  '<div class="loc-grid reveal d1">%s</div>'
                  '<div style="text-align:center;margin-top:24px"><a href="/venues/%s/%s/" class="link-arrow">All %s venues <span aria-hidden="true">&rarr;</span></a></div>'
                  '</div></section>') % (h(city), links, sslug, cslug, h(city))
            metro = METRO_PAGE.get(city)
            metro_line = (' We shoot across <a href="/%s" style="color:var(--copper)">%s</a> regularly.' % (metro, h(city))) if metro else ""
            # Two-tier honesty: only venues explicitly confirmed by JC (from booking
            # records) get the first-person claim. Everything else gets the true
            # 16-years/1,300-weddings framing. NEVER default filmed_here to True.
            if v.get("filmed_here"):
                exp_html = ('<div class="venue-exp reveal d1"><strong>We&rsquo;ve filmed at %s.</strong> '
                    'We know where the light falls, where the audio gets tricky, and where the best portraits hide '
                    '&mdash; ask to see our work from this venue when you inquire.</div>' % h(name))
            else:
                exp_html = ('<div class="venue-exp reveal d1"><strong>Sixteen years and 1,300+ weddings</strong> '
                    'have taken our teams through ballrooms, barns, beaches, and vineyards. If we haven&rsquo;t filmed at %s yet, '
                    'we scout it before your wedding &mdash; the light, the sound, the timeline &mdash; so nothing about the room '
                    'surprises us on the day.</div>' % h(name))
            photos_html = venue_photos_html(vslug, h(name))
            _qs = "?venue=%s&amp;from=%s" % (_up.quote(name, safe=""), _up.quote("/venues/%s/%s/%s" % (sslug, cslug, vslug), safe=""))
            schema_img = _vp_direct(vslug, 1) if PHOTOS.get(vslug) else CTA
            body = (
              hero("Getting married at %s?" % h(name),
                   "%s<br><em>Wedding Photo &amp; Film</em>" % h(name),
                   "Cinematic films and timeless photography for couples marrying at %s in %s, %s &mdash; with a local team and <strong>no travel fees</strong>."
                     % (h(name), h(city), sname),
                   crumbs(("Venues", "/venues/"), (sname, "/venues/%s/" % sslug), (h(city), "/venues/%s/%s/" % (sslug, cslug)), (h(name), None)))
              + '<section class="sec"><div class="wrap" style="text-align:center;max-width:760px">'
                '<div class="sec__head reveal" style="margin-bottom:0"><div class="sec__roman">%s, %s</div>'
                '<h2 class="sec__title">Your day at <em>%s.</em></h2><div class="rule"></div></div>'
                '<p class="reveal d1" style="margin-top:26px;color:var(--ivory-dim);font-size:clamp(15px,1.7vw,17px);line-height:1.85">%s is %s. It is the kind of place that gives a wedding film and a photo gallery real atmosphere &mdash; and we would love to capture yours there.%s</p>'
                '<p class="reveal d1" style="margin-top:18px;color:var(--ivory-dim);font-size:clamp(15px,1.7vw,17px);line-height:1.85">You get a local photography and film team &mdash; no travel fees, no out-of-town crew flying in. Every collection includes complimentary access to your raw footage, and a <strong>$500 deposit</strong> reserves your date.</p>%s%s'
                '<div class="venue-card reveal d2"><div class="venue-card__label">Venue</div>'
                '<div class="venue-card__name">%s</div><div class="venue-card__addr">%s</div></div>'
                '</div></section>' % (h(city), sname, h(name), h(name), h(v.get("character") or "a wedding and event venue"), metro_line, exp_html, photos_html, h(name), h(v.get("address","")))
              + '<section class="sec sec--tight"><div class="wrap"><div class="sec__head reveal">'
                '<div class="sec__roman">What We Offer</div><h2 class="sec__title">Film, photo, or <em>both.</em></h2><div class="rule"></div></div>'
                '<div class="cards cards--3">'
                '<a href="/packages" class="fcard reveal" style="text-decoration:none"><div class="fcard__idx">01</div><h3>Photography</h3><div class="fcard__rule"></div><p>Timeless stills of your day at %s.</p><span class="fcard__link">See packages &#8599;</span></a>'
                '<a href="/packages" class="fcard reveal d1" style="text-decoration:none"><div class="fcard__idx">02</div><h3>Videography</h3><div class="fcard__rule"></div><p>A cinematic film &mdash; vows, laughter, everything between.</p><span class="fcard__link">See packages &#8599;</span></a>'
                '<a href="/packages" class="fcard reveal d2" style="text-decoration:none"><div class="fcard__idx">03</div><h3>Photo &amp; Film</h3><div class="fcard__rule"></div><p>One team, one vision.</p><span class="fcard__link">See packages &#8599;</span></a>'
                '</div><div style="text-align:center;margin-top:40px" class="reveal">'
                '<a href="/films" class="btn btn--ghost" style="margin-right:12px">Watch Our Films <span class="arr">&#8599;</span></a>'
                '<a href="/gallery" class="btn btn--ghost">View the Gallery <span class="arr">&#8599;</span></a></div></div></section>' % h(name)
              + '<section class="sec sec--tight"><div class="wrap" style="text-align:center;max-width:760px">%s</div></section>' % BADGES
              + sib_html
              + cta("%s Weddings" % h(city), "Let's capture your day<br><em>at %s.</em>" % h(name))
              + DISC)
            schema = ('<script type="application/ld+json">'
              '{"@context":"https://schema.org","@type":"LocalBusiness","name":"Atavia Weddings",'
              '"description":"Wedding photography and videography for couples marrying at %s in %s, %s.",'
              '"url":"%s","telephone":"+1-336-537-9590","email":"info@ataviaweddings.com","image":"%s",'
              '"priceRange":"$$-$$$","areaServed":{"@type":"City","name":"%s, %s"}}</script>'
              '<script type="application/ld+json">{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":['
              '{"@type":"ListItem","position":1,"name":"Venues","item":"%s/venues/"},'
              '{"@type":"ListItem","position":2,"name":"%s","item":"%s/venues/%s/"},'
              '{"@type":"ListItem","position":3,"name":"%s","item":"%s/venues/%s/%s/"},'
              '{"@type":"ListItem","position":4,"name":"%s","item":"%s"}]}</script>'
              ) % (name, city, sname, canon, schema_img, city, sname,
                   BASE, sname, BASE, sslug, city, BASE, sslug, cslug, name, canon)
            indexed = canon in INDEX_SET
            if indexed:
                faq_block, faq_schema = faq_html(name, city, sname, bool(v.get("filmed_here")))
                body = body.replace(sib_html + cta("%s Weddings" % h(city), "Let's capture your day<br><em>at %s.</em>" % h(name)),
                                    faq_block + sib_html + cta("%s Weddings" % h(city), "Let's capture your day<br><em>at %s.</em>" % h(name)), 1)
                schema += faq_schema
            schema = ('<meta name="atv-venue" content="%s">' % h(name)) + schema
            # JC-ATV-SEO-0924: people reach these pages by searching the venue's own name
            # ("meadow mint farm", "coleman barn burlington nc", "... photos"), so the title
            # leads with the name + town and the snippet leads with the address.
            # JC-ATV-SEO-1008: GSC showed venue-name searches at pos 6-10 with 0 clicks on the
            # "Wedding Photographer & Videographer" title, so lead with "<Venue> Weddings" (the venue intent).
            has_photos = bool(PHOTOS.get(vslug))
            title = ("%s Wedding Photos &amp; Video &middot; %s, %s | Atavia Weddings" if has_photos else
                     "%s Weddings &middot; %s, %s &middot; Photo &amp; Film | Atavia Weddings") % (h(name), h(city), st)
            addr = (v.get("address") or "").replace(", USA", "")
            desc = ((h(addr) + ". ") if addr else "%s, %s. " % (h(city), sname))
            if v.get("filmed_here"):
                desc += "We&rsquo;ve filmed weddings at %s &mdash; see our work. " % h(name)
            elif has_photos:
                desc += "See our wedding photos from %s. " % h(name)
            desc += "Local photo &amp; film team, no travel fees, raw footage included."
            html = B.render_page(
                title, desc,
                canon, body, schema, nav_key="venues",
                robots="index, follow" if indexed else "noindex, follow")
            html = html.replace("__CTAQS__", _qs)
            write("%s/%s/%s.html" % (sslug, cslug, vslug), html, "0.7")
            if indexed:
                urls.append((canon, "0.7", B.lastmod_for(canon, html)))
            else:
                n_noindex += 1
            n_venue += 1

# ---------------- city hubs ----------------
n_city = 0
for st, cities in tree.items():
    sname, sslug = STATES[st], slug(STATES[st])
    for city, vs in cities.items():
        cslug = slug(city)
        canon = "%s/venues/%s/%s/" % (BASE, sslug, cslug)
        links = "".join('<a href="/venues/%s/%s/%s">%s</a>' % (sslug, cslug, slug(x["name"]), h(x["name"])) for x in sorted(vs, key=lambda z: z["name"]))
        metro = METRO_PAGE.get(city)
        metro_cta = ('<div style="text-align:center;margin-top:30px"><a href="/%s" class="btn btn--ghost">%s wedding coverage <span class="arr">&#8599;</span></a></div>' % (metro, h(city))) if metro else ""
        body = (hero("%s, %s" % (h(city), sname),
                     "%s Wedding<br><em>Venues We Shoot</em>" % h(city),
                     "We photograph and film weddings at %d %s %s &mdash; with a local team and <strong>no travel fees</strong>."
                       % (len(vs), h(city), "venue" if len(vs) == 1 else "venues"),
                     crumbs(("Venues", "/venues/"), (sname, "/venues/%s/" % sslug), (h(city), None)))
          + '<section class="sec"><div class="wrap" style="max-width:1000px">'
            '<div style="text-align:center" class="reveal"><div class="eyebrow center rules">Find Your Venue</div>'
            '<h2 class="sec__title" style="margin-top:14px">Venues in <em>%s</em></h2><div class="rule" style="margin:16px auto 0"></div></div>'
            '<div class="loc-grid reveal d1">%s</div>%s'
            '<p class="reveal" style="text-align:center;color:var(--ivory-dim);margin-top:30px;font-size:15px">Don\'t see your venue? We shoot nationwide &mdash; <a href="/book/" style="color:var(--copper)">just ask</a>.</p>'
            '</div></section>' % (h(city), links, metro_cta)
          + cta("%s Weddings" % h(city), "Let's capture your<br><em>%s wedding.</em>" % h(city))
          + DISC)
        schema = ('<script type="application/ld+json">{"@context":"https://schema.org","@type":"CollectionPage",'
                  '"name":"%s Wedding Venues","url":"%s"}</script>') % (city, canon)
        # A hub Google already shows (e.g. /venues/missouri/branson/) stays indexed even if
        # none of its venues made the cut.
        hub_indexed = (_GSC.get(canon.rstrip("/"), 0) > 0 or
                       any(("%s/venues/%s/%s/%s" % (BASE, sslug, cslug, slug(x["name"]))) in INDEX_SET for x in vs))
        html = B.render_page(
            "%s, %s Wedding Venues &mdash; %d We Photograph &amp; Film | Atavia Weddings" % (h(city), st, len(vs)),
            "%s wedding venues in %s, %s: %s. Photo and film from a local team, no travel fees."
              % (h(city), h(city), sname, ", ".join(h(x["name"]) for x in sorted(vs, key=lambda z: z["name"])[:6])
                 + (" and %d more" % (len(vs) - 6) if len(vs) > 6 else "")),
            canon, body, schema, nav_key="venues",
            robots="index, follow" if hub_indexed else "noindex, follow")
        html = html.replace("__CTAQS__", "")
        write("%s/%s/index.html" % (sslug, cslug), html, "0.8")
        if hub_indexed:
            urls.append((canon, "0.8", B.lastmod_for(canon, html)))
        n_city += 1

# ---------------- state hubs ----------------
n_state = 0
for st, cities in tree.items():
    sname, sslug = STATES[st], slug(STATES[st])
    total = sum(len(v) for v in cities.values())
    canon = "%s/venues/%s/" % (BASE, sslug)
    links = "".join('<a href="/venues/%s/%s/">%s (%d)</a>' % (sslug, slug(c), h(c), len(v))
                    for c, v in sorted(cities.items()))
    body = (hero("%s" % sname,
                 "%s Wedding<br><em>Venues</em>" % sname,
                 "We photograph and film weddings at %d %s across %d %s in %s &mdash; local team, <strong>no travel fees</strong>."
                   % (total, "venue" if total == 1 else "venues", len(cities), "city" if len(cities) == 1 else "cities", sname),
                 crumbs(("Venues", "/venues/"), (sname, None)))
      + '<section class="sec"><div class="wrap" style="max-width:1000px">'
        '<div style="text-align:center" class="reveal"><div class="eyebrow center rules">By City</div>'
        '<h2 class="sec__title" style="margin-top:14px">Cities in <em>%s</em></h2><div class="rule" style="margin:16px auto 0"></div></div>'
        '<div class="loc-grid reveal d1">%s</div></div></section>' % (sname, links)
      + cta("%s Weddings" % sname, "Let's capture your<br><em>%s wedding.</em>" % sname)
      + DISC)
    schema = ('<script type="application/ld+json">{"@context":"https://schema.org","@type":"CollectionPage",'
              '"name":"%s Wedding Venues","url":"%s"}</script>') % (sname, canon)
    html = B.render_page(
        "%s Wedding Venues &mdash; Photo &amp; Video | Atavia Weddings" % sname,
        "Wedding photography and videography at wedding venues across %s. Local team, no travel fees, raw footage included." % sname,
        canon, body, schema, nav_key="venues")
    html = html.replace("__CTAQS__", "")
    write("%s/index.html" % sslug, html, "0.8")
    urls.append((canon, "0.8", B.lastmod_for(canon, html)))
    n_state += 1

# ---------------- master hub ----------------
rows = ""
for st in sorted(tree, key=lambda x: STATES[x]):
    sname, sslug = STATES[st], slug(STATES[st])
    cities = tree[st]
    total = sum(len(v) for v in cities.values())
    top = "".join('<a href="/venues/%s/%s/">%s (%d)</a>' % (sslug, slug(c), h(c), len(v))
                  for c, v in sorted(cities.items(), key=lambda kv: -len(kv[1]))[:12])
    rows += ('<div class="venue-group reveal"><h3 class="venue-group__city">'
             '<a href="/venues/%s/">%s &rarr;</a> <span class="venue-group__count">%d venues &middot; %d %s</span></h3>'
             '<div class="loc-grid">%s</div></div>') % (sslug, sname, total, len(cities), "city" if len(cities)==1 else "cities", top)

grand = sum(sum(len(v) for v in c.values()) for c in tree.values())
ncities = sum(len(c) for c in tree.values())
body = (hero("Wedding Venue Directory",
             "Venues <em>We Shoot</em>",
             "Already booked your venue? Find it below. We cover <strong>%d venues</strong> across <strong>%d cities</strong> in <strong>%d states</strong> &mdash; local teams, <strong>no travel fees</strong>."
               % (grand, ncities, len(tree)),
             crumbs(("Venues", None)))
  + '<section class="sec"><div class="wrap" style="max-width:1040px">'
    '<p class="reveal" style="text-align:center;color:var(--ivory-dim);max-width:640px;margin:0 auto clamp(30px,4vw,44px);font-size:16px;line-height:1.8">'
    'Browse by state, then city. Don\'t see your venue? We shoot nationwide &mdash; <a href="/book/" style="color:var(--copper)">just ask</a>.</p>'
    '%s</div></section>' % rows
  + cta("Wherever You're Marrying", "Let's capture your<br><em>wedding day.</em>")
  + DISC)
schema = ('<script type="application/ld+json">{"@context":"https://schema.org","@type":"CollectionPage",'
          '"name":"Wedding Venue Directory","url":"%s/venues/"}</script>') % BASE
html = B.render_page(
    "Wedding Venue Directory &mdash; Photo &amp; Video at %d Venues | Atavia Weddings" % grand,
    "Browse wedding venues by state and city. Atavia Weddings shoots photo and video at venues nationwide — local teams, no travel fees.",
    BASE + "/venues/", body, schema, nav_key="venues")
html = html.replace("__CTAQS__", "")
write("", html, "0.9")
urls.append((BASE + "/venues/", "0.9", B.lastmod_for(BASE + "/venues/", html)))

# ---------------- sitemap chunks ----------------
for old in ROOT.glob("sitemap-venues-*.xml"):
    old.unlink()
nchunks = max(1, math.ceil(len(urls) / CHUNK))
for i in range(nchunks):
    part = urls[i*CHUNK:(i+1)*CHUNK]
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join('  <url><loc>%s</loc><lastmod>%s</lastmod><changefreq>monthly</changefreq><priority>%s</priority></url>' % (u, lm, p)
                       for u, p, lm in part)
           + "\n</urlset>\n")
    (ROOT / ("sitemap-venues-%d.xml" % (i+1))).write_text(xml, encoding="utf-8")

B.save_lastmod_cache()
print("venue directory: %d venues (%d noindex) | %d city hubs | %d state hubs | 1 master hub" % (n_venue, n_noindex, n_city, n_state))
print("sitemap URLs: %d  ->  %d sitemap chunk(s)" % (len(urls), nchunks))
