#!/usr/bin/env python3
"""gen_cities.py - Elizabeth Scott /wedding-photographer/<city> pages + /locations/ hub.

Photographer-intent programmatic layer (deliberately distinct from Atavia's venue
moat - ES pages target "<city> wedding photographer", not "<city> wedding venues",
so the two brands never bid against each other in the same SERP).

Per-city uniqueness comes from three real data sources, never from spun prose:
  1. solar.py        - computed sunset / golden-hour / ceremony timing (exact)
  2. city_data.json  - real venue names from the Places API (crawl_cities.py)
  3. haversine       - true nearest cities with mileage, not alphabetical siblings

If city_data.json is absent the generator still runs and emits the old-style
template pages, so the build never breaks on a missing crawl.

Run: python _src/crawl_cities.py --key KEY   (once)
     python _src/gen_cities.py && python _src/build.py
"""
import sys, pathlib, re, json, math, html as H, datetime as dt

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import build as B
from cities_data import CITIES, REGIONS
try:
    import solar
except ImportError:
    solar = None
try:
    import gallery
except ImportError:
    gallery = None
try:
    from gen_venues import PKGS, money
except Exception:
    PKGS, money = [], (lambda n: "${:,}".format(int(n)))

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "wedding-photographer"
BASE = B.BASE
YEAR = dt.date.today().year + 1          # couples browsing now are booking next season

# ---------------------------------------------------------------- data loading
CITY_DATA = {}
_cd = SRC / "city_data.json"
if _cd.exists():
    CITY_DATA = json.loads(_cd.read_text(encoding="utf-8"))

# Cities you have actually photographed. One "City, ST" per line, # for comments.
# Drives stronger first-person copy - never claim a venue you have not shot.
VENUE_PAGES = {}
try:
    VENUE_PAGES = json.loads((SRC / "venue_pages.json").read_text(encoding="utf-8"))   # written by gen_venues.py
except Exception:
    pass

SHOT_HERE = set()
_sh = SRC / "shot_here.txt"
if _sh.exists():
    for line in _sh.read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if line:
            SHOT_HERE.add(line.lower())


def slug(s):
    s = s.lower().replace("&", "and").replace("'", "")
    return re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", s)).strip("-")


def h(s): return H.escape(str(s or ""), quote=True)


def miles(a_lat, a_lng, b_lat, b_lng):
    r = 3958.8
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp = p2 - p1
    dl = math.radians(b_lng - a_lng)
    x = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return round(2 * r * math.asin(math.sqrt(x)))


HERO_KEYS = ['hero', 'hero2', 'hero3', 'hero4']
HERO = '''<header class="hero" style="min-height:48vh">
  <div class="hero-bg"><img data-img="__HK__" alt=""></div>
  <div class="wrap">
    <span class="hero-badge fade-up d1">Now Booking &middot; Travel Included</span>
    <h1 class="fade-up d2" style="font-family:var(--serif);font-size:clamp(32px,4.6vw,52px)">%s Wedding <em>Photographer &amp; Videographer</em></h1>
    <p class="fade-up d3" style="color:var(--mist);max-width:660px;margin:14px auto 0">%s</p>
  </div>
</header>'''

CARD = '<div class="glass" style="padding:%s;border-radius:var(--radius)%s">'


# ------------------------------------------------------------- content blocks
def light_block(name, st, cd):
    """Computed sunset / golden-hour planning table. Exact astronomy, unique per
    city by latitude and longitude - the single largest source of legitimate
    per-page differentiation on the whole site."""
    if not (solar and cd and cd.get("lat")):
        return ""
    try:
        rows = solar.wedding_season(YEAR, cd["lat"], cd["lng"], st)
    except Exception:
        return ""
    if len(rows) < 3:
        return ""

    jun = next((r for r in rows if r["abbr"] == "Jun"), rows[0])
    oct_ = next((r for r in rows if r["abbr"] == "Oct"), rows[-1])
    swing = int(round((jun["sunset"].hour*60 + jun["sunset"].minute)
                      - (oct_["sunset"].hour*60 + oct_["sunset"].minute)))
    hrs, mins = divmod(max(swing, 0), 60)
    parts = []
    if hrs:  parts.append("%d hour%s" % (hrs, "" if hrs == 1 else "s"))
    if mins: parts.append("%d minute%s" % (mins, "" if mins == 1 else "s"))
    swing_txt = " ".join(parts) or "under a minute"

    trs = ""
    for r in rows:
        trs += ('<tr>'
                '<td style="padding:9px 12px;color:var(--ice)">%s</td>'
                '<td style="padding:9px 12px;color:var(--champagne);white-space:nowrap">%s</td>'
                '<td style="padding:9px 12px;color:var(--mist);white-space:nowrap">%s</td>'
                '<td style="padding:9px 12px;color:var(--mist);white-space:nowrap">%s</td>'
                '<td style="padding:9px 12px;color:var(--mist)">%s h</td>'
                '</tr>') % (r["month"], solar.hhmm(r["ceremony"]), solar.hhmm(r["golden"]),
                            solar.hhmm(r["sunset"]), r["daylight"])

    return ('\n  ' + CARD % ("30px", ";margin-top:20px") + '''
    <h2 style="font-family:var(--serif);font-size:25px">The light in %(name)s</h2>
    <p style="color:var(--mist);line-height:1.9;margin-top:12px">Ceremony time decides how your photographs look, and the answer is different in %(name)s than it is three states over. In June the sun sets here at %(jun_set)s and golden hour opens around %(jun_gold)s; by October sunset has slid back to %(oct_set)s &mdash; a swing of %(swing)s across one wedding season. Start a %(name)s ceremony at roughly the times below and you will finish vows, family formals, and portraits with the good light still in front of you rather than behind you.</p>
    <div style="overflow-x:auto;margin-top:18px">
      <table style="width:100%%;border-collapse:collapse;font-size:15px;min-width:520px">
        <thead><tr style="text-align:left;border-bottom:1px solid rgba(255,255,255,.14)">
          <th style="padding:9px 12px;font-family:var(--serif);font-weight:400;color:var(--ice)">%(year)s</th>
          <th style="padding:9px 12px;font-family:var(--serif);font-weight:400;color:var(--ice)">Start ceremony</th>
          <th style="padding:9px 12px;font-family:var(--serif);font-weight:400;color:var(--ice)">Golden hour</th>
          <th style="padding:9px 12px;font-family:var(--serif);font-weight:400;color:var(--ice)">Sunset</th>
          <th style="padding:9px 12px;font-family:var(--serif);font-weight:400;color:var(--ice)">Daylight</th>
        </tr></thead>
        <tbody>%(trs)s</tbody>
      </table>
    </div>
    <p style="color:var(--mist);font-size:13.5px;margin-top:12px;opacity:.85">Times computed for %(name)s (%(tz)s) on the 15th of each month. An outdoor ceremony in open shade can run 20&ndash;30 minutes later than the figures above; a church or ballroom ceremony is unaffected.</p>
  </div>''') % dict(name=h(name), year=YEAR, trs=trs, swing=swing_txt,
                    jun_set=solar.hhmm(jun["sunset"]), jun_gold=solar.hhmm(jun["golden"]),
                    oct_set=solar.hhmm(oct_["sunset"]),
                    tz=h(solar.tz_for(st, cd["lng"]).key.split("/")[-1].replace("_", " ")))


def venue_block(name, st, cd, shot):
    """Real venue names from the Places crawl. Framed as coverage, never as a
    claim to have shot a venue - that distinction is the whole reason this is
    content rather than a doorway page."""
    vs = (cd or {}).get("venues") or []
    if len(vs) < 3:
        return ""
    top = vs[:6]
    items = ""
    for v in top:
        meta = ""
        if v.get("rating") and v.get("reviews", 0) >= 15:
            meta = ('<span style="color:var(--mist);font-size:13px;display:block;margin-top:3px">'
                    '%.1f &#9733; &middot; %d reviews</span>') % (v["rating"], v["reviews"])
        url = VENUE_PAGES.get("%s|%s" % (name, st), {}).get(v["name"])
        if url:
            label = '<a href="%s" style="color:var(--ice);font-size:15.5px;text-decoration:none;border-bottom:1px solid rgba(255,255,255,.25)">%s</a>' % (url, h(v["name"]))
        else:
            label = '<span style="color:var(--ice);font-size:15.5px">%s</span>' % h(v["name"])
        items += ('<div style="padding:12px 0;border-bottom:1px solid rgba(255,255,255,.08)">%s%s</div>') % (label, meta)

    more = ""
    if VENUE_PAGES.get("%s|%s" % (name, st)):
        more = ('<p style="margin-top:14px"><a href="/venues/%s/" style="color:var(--champagne)">Every %s venue, with pricing and light notes &rarr;</a></p>'
                % (slug("%s %s" % (name, st)), h(name)))
    if shot:
        lead = ("We have worked in and around %s, and these are the rooms and grounds couples "
                "here ask us about most often. If yours is on the list we already know its light, "
                "its timing, and where the day tends to run long." % h(name))
    else:
        lead = ("These are the %s venues couples ask us about most. We have not shot every one of "
                "them &mdash; nobody has &mdash; so when a venue is new to us we scout it before your "
                "date: light through the ceremony hour, where formals hold up, how long the walk "
                "from getting-ready to first look actually takes." % h(name))

    return ('\n  ' + CARD % ("30px", ";margin-top:20px") + '''
    <h2 style="font-family:var(--serif);font-size:25px">Where couples marry in %(name)s</h2>
    <p style="color:var(--mist);line-height:1.9;margin-top:12px">%(lead)s</p>
    <div style="margin-top:16px">%(items)s</div>
    %(more)s<p style="color:var(--mist);font-size:13.5px;margin-top:14px;opacity:.85">Venue list is informational; Elizabeth Scott is not affiliated with, endorsed by, or booking on behalf of any venue named above.</p>
  </div>''') % dict(name=h(name), lead=lead, items=items, more=more)


def nearby_block(name, st, cd, all_geo):
    """True nearest cities with mileage. Replaces the alphabetical-siblings list,
    which had every page in a region pointing at the same four destinations."""
    here = (cd or {})
    picks = []
    if here.get("lat") and all_geo:
        cand = []
        for k, o in all_geo.items():
            if not o.get("lat") or (o["name"] == name and o["st"] == st):
                continue
            cand.append((miles(here["lat"], here["lng"], o["lat"], o["lng"]), o["name"], o["st"]))
        cand.sort()
        picks = [(n, s, d) for d, n, s in cand[:5] if d <= 260]
    if not picks:
        return None
    return " &middot; ".join(
        '<a href="/wedding-photographer/%s" style="color:var(--champagne)">%s, %s</a> '
        '<span style="opacity:.65">%d mi</span>' % (slug("%s %s" % (n, s)), h(n), h(s), d)
        for n, s, d in picks)


def photo_block(name, st):
    """Four portfolio frames, deterministically chosen per city so rebuilds are
    stable. Alt text stays generic on purpose - these are portfolio work, not
    photographs taken in this city, and claiming otherwise would be false."""
    if not gallery:
        return ""
    return gallery.strip(
        "%s|%s" % (name, st), k=4, w=640, q=80,
        alt="Wedding photograph by Elizabeth Scott",
        heading="Recent work",
        note="Selected frames from the Elizabeth Scott portfolio. "
             "Ask and we will send full galleries from weddings closest in size and setting to yours.")


def pricing_block(name, st, qs):
    """Published 8-hour collections. GSC shows price-intent queries ("<city> wedding
    photographer prices", "how much is a wedding photographer in <city>") landing on
    these pages at position 25-30 with nothing on the page that answers them."""
    pick = {}
    for p in PKGS:
        t = p.get("service_type") or p.get("type")
        if p.get("hours") == 8 and t in ("photo", "video", "combined"):
            pick[t] = p
    cards = ""
    for key, label, blurb in (("photo", "Photography", "Several hundred edited photographs, true to color."),
                              ("video", "Film", "A story-first edit built from your real audio."),
                              ("combined", "Photo &amp; Film", "One senior team for both &mdash; the smoothest timeline.")):
        p = pick.get(key)
        if not p:
            continue
        cards += ('<div class="glass" style="padding:22px;border-radius:var(--radius)"><h3 style="font-family:var(--serif)">%s</h3>'
                  '<p style="color:var(--champagne);font-size:22px;font-family:var(--serif);margin-top:6px">%s <span style="color:var(--mist);font-size:13px;font-family:inherit">&middot; %s, %d hours</span></p>'
                  '<p style="color:var(--mist);font-size:14.5px;margin-top:6px">%s</p></div>'
                  % (label, money(p.get("price") or p.get("total") or 0), h(p["name"]), int(p.get("hours") or 0), blurb))
    if not cards:
        return ""
    return ('\n  ' + CARD % ("30px", ";margin-top:20px") + """
    <h2 style="font-family:var(--serif);font-size:25px">How much does a wedding photographer cost in %(name)s?</h2>
    <p style="color:var(--mist);line-height:1.9;margin-top:12px">Our pricing is published and it is the same in %(name)s as everywhere else we work &mdash; travel is included, there are no location surcharges, and the prices below are pay-in-full (the payment plan adds $500, with half down at booking). Photography starts at $1,500 and films at $1,200 for shorter days; the eight-hour collections most %(name)s couples choose are below, and four-, six- and ten-hour versions are on the <a href="/packages" style="color:var(--champagne)">collections page</a>.</p>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-top:18px">%(cards)s</div>
    <p style="text-align:center;margin-top:24px"><a class="btn btn-gold" href="/book/%(qs)s">Reserve Your %(name)s Date</a></p>
  </div>""") % dict(name=h(name), cards=cards, qs=qs)


def faq_block(name, st, shot):
    """Three honest answers + FAQPage schema (same pattern as the venue pages, which
    rank at position ~20 while the city pages sit at ~55)."""
    q1 = "Do you charge a travel fee for weddings in %s, %s?" % (name, st)
    a1 = ("No. Elizabeth Scott is a national studio and travel is built into every collection, so a %s wedding "
          "costs the same as one across the street from us." % name)
    q2 = "Do you offer wedding videography in %s as well as photography?" % name
    a2 = ("Yes. Every collection is available as photography, film, or both from one senior team. Combined coverage "
          "starts at $3,000 and gives you a single timeline instead of two vendors negotiating for the same light.")
    q3 = "Have you photographed weddings in %s before?" % name
    a3 = ("Yes \u2014 we have shot in %s and know how its light and timelines behave." % name) if shot else \
         ("Not every venue in %s, and we say so. When a venue is new to us we scout it before your date: ceremony light, "
          "where formals hold up, how long the walk between spaces really takes." % name)
    items = [(q1, a1), (q2, a2), (q3, a3)]
    html = ('\n  ' + CARD % ("30px", ";margin-top:20px")
            + '<h2 style="font-family:var(--serif);font-size:25px">Questions couples in %s ask us</h2>' % h(name)
            + '<div style="margin-top:8px">'
            + "".join('<details style="border-top:1px solid rgba(255,255,255,.1);padding:12px 0"><summary style="cursor:pointer;color:var(--ice);font-size:16px;list-style:none">%s</summary>'
                      '<p style="color:var(--mist);line-height:1.85;margin-top:8px">%s</p></details>' % (h(q), h(a)) for q, a in items)
            + '</div></div>')
    sch = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in items]}
    return html, '<script type="application/ld+json">%s</script>' % json.dumps(sch)


def city_body(name, st, region, nearby_fallback, cd, all_geo):
    _hk = HERO_KEYS[sum(ord(c) for c in name) % 4]
    r = REGIONS[region]
    shot = ("%s, %s" % (name, st)).lower() in SHOT_HERE
    qs = "?city=%s&amp;from=%s" % (H.escape(name).replace(" ", "%20"),
                                   "%2Fwedding-photographer%2F" + slug("%s %s" % (name, st)))

    near = nearby_block(name, st, cd, all_geo)
    if near is None:
        near = " &middot; ".join(
            '<a href="/wedding-photographer/%s" style="color:var(--champagne)">%s, %s</a>'
            % (slug("%s %s" % (n, s2)), h(n), h(s2)) for n, s2 in nearby_fallback)

    scout = ("Elizabeth Scott is a national studio: senior photographers and filmmakers, travel "
             "already included, and a calendar kept deliberately small so every wedding gets a "
             "first-team crew. If we haven&rsquo;t worked your exact venue yet, we scout it before "
             "your day &mdash; light, timing, logistics &mdash; so nothing about %s surprises us on "
             "the morning of." % h(name))
    if shot:
        scout = ("Elizabeth Scott is a national studio: senior photographers and filmmakers, travel "
                 "already included, and a calendar kept deliberately small so every wedding gets a "
                 "first-team crew. We have shot in %s before &mdash; we know how the light behaves "
                 "here, which timelines hold up, and where the day tends to run long." % h(name))

    return (HERO % ("%s, %s" % (h(name), h(st)), h(r["sub"] % name))).replace("__HK__", _hk) + '''
<section class="section"><div class="wrap" style="max-width:860px">
  ''' + CARD % ("32px", "") + '''
    <h2 style="font-family:var(--serif);font-size:26px">Wedding photographers &amp; videographers in %(name)s</h2>
    <p style="color:var(--mist);line-height:1.9;margin-top:12px">%(flavor)s</p>
    <p style="color:var(--mist);line-height:1.9;margin-top:14px">%(scout)s</p>
  </div>%(photos)s%(light)s%(venues)s%(pricing)s%(faq)s
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:16px;margin-top:20px">
    <div class="glass" style="padding:24px;border-radius:var(--radius)"><h3 style="font-family:var(--serif)">Photography</h3><p style="color:var(--mist);font-size:15px;margin-top:6px">Timeless, true-to-color imagery &mdash; several hundred edited photos per wedding.</p></div>
    <div class="glass" style="padding:24px;border-radius:var(--radius)"><h3 style="font-family:var(--serif)">Films</h3><p style="color:var(--mist);font-size:15px;margin-top:6px">Story-first edits built from your real audio &mdash; vows, letters, laughter.</p></div>
    <div class="glass" style="padding:24px;border-radius:var(--radius)"><h3 style="font-family:var(--serif)">Combined</h3><p style="color:var(--mist);font-size:15px;margin-top:6px">One team for both &mdash; the best value and the smoothest timeline.</p></div>
  </div>
  <p style="text-align:center;margin-top:28px">
    <a class="btn btn-gold" href="/book/%(qs)s">Check Your %(name)s Date</a>
    &nbsp;&nbsp;<a class="btn" href="/packages" style="margin-left:8px">See Collections</a>
  </p>
  <p style="text-align:center;color:var(--mist);font-size:14px;margin-top:26px">Also serving: %(near)s &nbsp;&middot;&nbsp; <a href="/locations/" style="color:var(--champagne)">all locations &rarr;</a></p>
</div></section>''' % dict(name=h(name), flavor=r["flavor"] % dict(city=h(name)),
                           scout=scout, qs=qs, near=near,
                           photos=photo_block(name, st),
                           pricing=pricing_block(name, st, qs),
                           faq=faq_block(name, st, shot)[0],
                           light=light_block(name, st, cd),
                           venues=venue_block(name, st, cd, shot))


def schema(name, st, canon, cd):
    area = {"@type": "City", "name": name,
            "address": {"@type": "PostalAddress", "addressRegion": st, "addressCountry": "US"}}
    if cd and cd.get("lat"):
        area["geo"] = {"@type": "GeoCoordinates",
                       "latitude": cd["lat"], "longitude": cd["lng"]}
    d = {"@context": "https://schema.org", "@type": "Service",
         "name": "Wedding Photography & Videography \u2014 %s, %s" % (name, st),
         "serviceType": "Wedding photography and videography",
         "provider": {"@type": "Organization", "name": "Elizabeth Scott", "url": BASE + "/"},
         "areaServed": area, "url": canon}
    b = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE + "/"},
        {"@type": "ListItem", "position": 2, "name": "Locations", "item": BASE + "/locations/"},
        {"@type": "ListItem", "position": 3, "name": "%s, %s" % (name, st), "item": canon}]}
    return ('<script type="application/ld+json">%s</script><script type="application/ld+json">%s</script>'
            % (json.dumps(d), json.dumps(b)))


def main():
    OUT.mkdir(exist_ok=True)
    (ROOT / "locations").mkdir(exist_ok=True)
    by_region = {}
    for name, st, region in CITIES:
        by_region.setdefault(region, []).append((name, st))

    geo = {k: v for k, v in CITY_DATA.items() if v.get("lat")}
    if not CITY_DATA:
        print("  ! city_data.json missing - emitting template-only pages.")
        print("    Run: python _src/crawl_cities.py --key YOUR_KEY")

    urls, rich = [], 0
    for name, st, region in CITIES:
        sl = slug("%s %s" % (name, st))
        canon = "%s/wedding-photographer/%s" % (BASE, sl)
        cd = CITY_DATA.get("%s|%s" % (name, st))
        sibs = [c for c in by_region[region] if c[0] != name][:4]
        shot = ("%s, %s" % (name, st)).lower() in SHOT_HERE
        body = city_body(name, st, region, sibs, cd, geo)
        if cd and cd.get("lat"):
            rich += 1
        desc = ("%s, %s wedding photographer & videographer with published pricing \u2014 photography from "
                "$1,500, films from $1,200, travel included. Sunset times, venues, limited dates."
                % (name, st))[:158]
        html = B.render_page(
            "%s, %s Wedding Photographer &amp; Videographer | Elizabeth Scott" % (h(name), h(st)),
            desc, canon, body, schema(name, st, canon, cd) + faq_block(name, st, shot)[1], nav_key="locations")
        (OUT / (sl + ".html")).write_text(html, encoding="utf-8")
        urls.append((canon, "0.7", B.lastmod_for(canon, html) if hasattr(B, "lastmod_for") else None))

    # ---- hub
    groups = ""
    for region in REGIONS:
        cities = sorted(by_region.get(region, []))
        if not cities:
            continue
        links = "".join(
            '<a class="glass" style="display:block;padding:14px 18px;border-radius:14px;color:var(--ice);text-decoration:none" href="/wedding-photographer/%s">%s, %s</a>'
            % (slug("%s %s" % (n, s2)), h(n), s2) for n, s2 in cities)
        groups += ('<h2 style="font-family:var(--serif);margin:34px 0 14px">%s</h2>'
                   '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:12px">%s</div>'
                   % (h(REGIONS[region]["label"]), links))
    hub_body = (HERO % ("Every City,",
                        "One studio, %d cities and counting &mdash; travel included everywhere. "
                        "Don&rsquo;t see yours? We still come to you." % len(CITIES))
                ).replace("__HK__", "hero")
    hub_body = hub_body.replace("Wedding <em>Photographer &amp; Filmmaker</em>", "One <em>Signature</em>")
    hub_body += ('<section class="section"><div class="wrap">%s'
                 '<p style="text-align:center;margin-top:34px">'
                 '<a class="btn btn-gold" href="/book/">Check Your Date</a></p></div></section>' % groups)
    html = B.render_page(
        "Wedding Photographers in All 50 States &mdash; Locations | Elizabeth Scott",
        ("Elizabeth Scott photographs and films weddings in %d cities nationwide \u2014 travel "
         "included, senior crews, limited dates. Find your city and check your date."
         % len(CITIES))[:158],
        BASE + "/locations/", hub_body, "", nav_key="locations")
    (ROOT / "locations" / "index.html").write_text(html, encoding="utf-8")
    urls.insert(0, (BASE + "/locations/", "0.8", B.lastmod_for(BASE + "/locations/", html) if hasattr(B, "lastmod_for") else None))

    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u, pr, lm in urls:
        xml.append('  <url><loc>%s</loc>%s<priority>%s</priority></url>' % (u, ("<lastmod>%s</lastmod>" % lm) if lm else "", pr))
    xml.append("</urlset>")
    (ROOT / "sitemap-cities.xml").write_text("\n".join(xml), encoding="utf-8")
    if hasattr(B, "save_lastmod_cache"): B.save_lastmod_cache()
    print("cities: %d pages + hub | %d with real data, %d template-only | sitemap-cities.xml"
          % (len(CITIES), rich, len(CITIES) - rich))


if __name__ == "__main__":
    main()
