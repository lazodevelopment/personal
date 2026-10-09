"""gen_venues.py - Elizabeth Scott venue pages   (JC-ESW-VENUES-0910-001)

Reads the Places crawl in _src/city_data.json (the same data the city pages use)
and writes one page per venue for the states in VENUE_STATES, plus a hub per city
and a master hub:

    /venues/                          all states -> cities
    /venues/<city-st>/                the city's venues (links back to the city page)
    /venues/<city-st>/<venue>         the venue page

Run:  python _src/gen_venues.py --report    (dry run: counts only)
      python _src/gen_venues.py && python _src/gen_cities.py && python _src/build.py

Every venue page is built from things that are true and specific to that venue:
its Google rating/review count and address, the sunset/golden-hour numbers at its
own coordinates, its distance from the city center and from the other venues on
the list, a venue-type read of the name (barn, estate, hotel, waterfront...) and
Elizabeth Scott's published pricing. Nothing on the page claims we've shot there
unless the city is in shot_here.txt.

Venues with fewer than MIN_REVIEWS Google reviews are still written (so hubs are
complete) but noindex - Google should only be asked to index venues real couples
actually search for.  lastmod is honest: it moves only when the page changes.
"""
import sys, pathlib, re, json, math, html as H, datetime as dt, hashlib

SRC = pathlib.Path(__file__).resolve().parent
ROOT = SRC.parent
sys.path.insert(0, str(SRC))

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

BASE = B.BASE
OUT = ROOT / "venues"
YEAR = dt.date.today().year + 1

# ---------------------------------------------------------------- scope
VENUE_STATES = {"TX", "MA", "RI", "CT", "ME", "VT", "NH"}     # tranche 1 — widen later
MIN_REVIEWS = 20                                              # below this: page exists, noindex
REPORT_ONLY = "--report" in sys.argv

CITY_DATA = {}
try:
    CITY_DATA = json.loads((SRC / "city_data.json").read_text(encoding="utf-8"))
except Exception:
    print("  ! city_data.json missing — nothing to build"); sys.exit(1)

SHOT_HERE = set()
try:
    for line in (SRC / "shot_here.txt").read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if line: SHOT_HERE.add(line.lower())
except Exception:
    pass

# ES packages (published pricing) — same file the booking pipeline uses
PKGS = []
try:
    _p = json.loads((SRC.parent.parent / "es-deploy" / "functions" / "elizabethscott_packages.json").read_text(encoding="utf-8"))
    PKGS = _p.get("packages", [])
except Exception:
    # Pay-in-full prices from Elizabeth-Scott-Packages-2026.pdf (the "gold" prices); the payment plan adds $500.
    PKGS = [dict(id="portrait", name="The Portrait", service_type="photo", hours=4, price=1500),
            dict(id="vignette", name="The Vignette", service_type="video", hours=4, price=1200),
            dict(id="ensemble", name="The Ensemble", service_type="combined", hours=6, price=3000),
            dict(id="gallery", name="The Gallery", service_type="photo", hours=8, price=2000),
            dict(id="feature", name="The Feature", service_type="video", hours=8, price=1500),
            dict(id="keepsake", name="The Keepsake", service_type="combined", hours=8, price=3500)]

# ---------------------------------------------------------------- helpers
def slug(s):
    s = re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")
    return re.sub(r"-{2,}", "-", s)

def h(s): return H.escape(str(s or ""), quote=True)
def money(n): return "${:,}".format(int(n))

def miles(a_lat, a_lng, b_lat, b_lng):
    r = 3958.8
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    x = math.sin((p2 - p1)/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(math.radians(b_lng - a_lng)/2)**2
    return 2 * r * math.asin(math.sqrt(x))

def fmt_miles(m):
    return "under a mile" if m < 1 else ("about %d mile%s" % (round(m), "" if round(m) == 1 else "s"))

# ------------------------------------------------- venue-type read of the name
TYPES = [
  ("barn",      r"\b(barn|farm|ranch|homestead|orchard|acres|meadow|silo|stables?)\b",
   "Barn and ranch venues reward a photographer who plans for two kinds of light: the wide open-field glow before sunset and the string-light warmth inside afterwards. We schedule portraits for the field first, then move inside with the reception already lit the way it should be filmed."),
  ("vineyard",  r"\b(vineyard|winery|cellars?|estate vineyard|wine)\b",
   "Vineyard rows are the easiest place in the world to make a portrait feel expensive, and the hardest to get to on time. We walk the rows during scouting so the portrait window lands in the vines while the light is still low and gold."),
  ("waterfront",r"\b(beach|harbor|harbour|bay|yacht|marina|lake|waterfront|pier|island|seaside|coast|oceanfront|shore|cove)\b",
   "Water changes everything about a wedding's light: it reflects, it flares, and it turns a plain sunset into a two-color sky. We keep an eye on the tide table and the wind, shoot the ceremony from the side that keeps the water in frame, and stay for the afterglow."),
  ("estate",    r"\b(estate|manor|mansion|hall|house|castle|villa|chateau|ch[âa]teau|plantation|gardens?|conservatory|arboretum|botanical)\b",
   "Estates and gardens give a wedding rooms and grounds in the same afternoon. We map the property during scouting — which lawn holds shade at four, which room has window light for getting ready — and run the timeline so nothing is a long walk from the next photograph."),
  ("hotel",     r"\b(hotel|resort|inn|lodge|spa|club|country club|golf|retreat)\b",
   "Hotels and resorts run on their own clock, and the best coverage respects it: getting-ready in real rooms, a ceremony that starts when the coordinator says so, and portraits slipped into the gap between cocktail hour and dinner. We coordinate with the venue team before the day so nobody is waiting on us."),
  ("ballroom",  r"\b(ballroom|event center|events? center|venue|conference|banquet|pavilion|terrace|plaza|room|space|loft|warehouse|studio|brewery|distillery|rooftop)\b",
   "Indoor venues put the responsibility on the photographer rather than the sun. We light the ceremony and the dance floor deliberately — enough to see faces, never so much you notice it — and we bring the outdoor portraits to wherever the daylight is best nearby."),
  ("historic",  r"\b(historic|museum|library|theater|theatre|chapel|church|cathedral|mission|courthouse|opera|armory|mill)\b",
   "Historic rooms have rules and character in equal measure. We ask about photography restrictions early, shoot the ceremony quietly and without flash where it matters, and treat the architecture as the second subject of the day."),
]
def venue_type(name):
    n = name.lower()
    for key, pat, para in TYPES:
        if re.search(pat, n):
            return key, para
    return "venue", ("Every venue has a best hour and a worst one for photographs. We scout yours before the wedding — where the ceremony light falls, where family formals hold up, where the reception needs a little help — so the plan for the day is built on the room itself, not on a guess.")

# ------------------------------------------------------- light at this venue
def light_para(name, st, lat, lng):
    if not (solar and lat):
        return ""
    try:
        rows = solar.wedding_season(YEAR, lat, lng, st)
    except Exception:
        return ""
    if len(rows) < 3:
        return ""
    jun = next((r for r in rows if r["abbr"] == "Jun"), rows[0])
    oct_ = next((r for r in rows if r["abbr"] == "Oct"), rows[-1])
    sep = next((r for r in rows if r["abbr"] == "Sep"), rows[-2])
    return ('<p style="color:var(--mist);line-height:1.9;margin-top:14px">At %s the sun sets at %s in June and %s in October, '
            'with golden hour opening around %s on a June evening and %s in late September. Start a summer ceremony near %s '
            'and you will still have the good light for portraits; in autumn move it an hour earlier. '
            'The full month-by-month table is on our <a href="%s" style="color:var(--champagne)">%s page</a>.</p>'
            % (h(name), solar.hhmm(jun["sunset"]), solar.hhmm(oct_["sunset"]), solar.hhmm(jun["golden"]), solar.hhmm(sep["golden"]),
               solar.hhmm(jun["ceremony"]), "__CITYURL__", "__CITYNAME__"))

# ---------------------------------------------------------------- blocks
HERO = '''<header class="hero" style="min-height:44vh">
  <div class="hero-bg"><img data-img="%(hk)s" alt=""></div>
  <div class="wrap">
    <span class="hero-badge fade-up d1">%(city)s, %(st)s &middot; Travel Included</span>
    <h1 class="fade-up d2" style="font-family:var(--serif);font-size:clamp(30px,4.4vw,50px)">%(name)s <em>Wedding Photographer &amp; Videographer</em></h1>
    <p class="fade-up d3" style="color:var(--mist);max-width:660px;margin:14px auto 0">%(sub)s</p>
  </div>
</header>'''
CARD = '<div class="glass" style="padding:%s;border-radius:var(--radius)%s">'
DISC = ('<p style="color:var(--mist);font-size:13px;margin-top:26px;opacity:.8;text-align:center;max-width:760px;margin-left:auto;margin-right:auto">'
        'Elizabeth Scott is an independent wedding photography and film studio. We are not affiliated with, endorsed by, or booking on behalf of any venue named on this page; '
        'venue names are used to identify where we work. Ratings and review counts are Google\'s, as of our last check, and can change. Confirm availability and policies with the venue.</p>')

def pricing_block(name, qs):
    pick = {}
    for p in PKGS:
        t = p.get("service_type") or p.get("type")
        hrs = p.get("hours")
        if t == "photo" and hrs == 8: pick["photo"] = p
        if t == "video" and hrs == 8: pick["video"] = p
        if t == "combined" and hrs == 8: pick["combined"] = p
    cards = ""
    for key, label, blurb in (("photo", "Photography", "Several hundred edited photographs, true to color."),
                              ("video", "Film", "A story-first edit built from your real audio."),
                              ("combined", "Photo &amp; Film", "One senior team for both — the smoothest timeline.")):
        p = pick.get(key)
        if not p: continue
        cards += ('<div class="glass" style="padding:22px;border-radius:var(--radius)"><h3 style="font-family:var(--serif)">%s</h3>'
                  '<p style="color:var(--champagne);font-size:22px;font-family:var(--serif);margin-top:6px">%s <span style="color:var(--mist);font-size:13px;font-family:inherit">&middot; %s, %d hours</span></p>'
                  '<p style="color:var(--mist);font-size:14.5px;margin-top:6px">%s</p></div>') % (label, money(p.get("price") or p.get("total") or 0), h(p["name"]), int(p.get("hours") or 0), blurb)
    return ('\n  ' + CARD % ("30px", ";margin-top:20px") + '''
    <h2 style="font-family:var(--serif);font-size:25px">Published pricing for a wedding at %(name)s</h2>
    <p style="color:var(--mist);line-height:1.9;margin-top:12px">Every collection is the same price wherever the wedding is — travel is included, there are no venue surcharges, and the prices below are pay-in-full (the payment plan adds $500, with half down at booking). Eight-hour collections are below; four-, six- and ten-hour versions are on the <a href="/packages" style="color:var(--champagne)">collections page</a>.</p>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-top:18px">%(cards)s</div>
    <p style="text-align:center;margin-top:24px"><a class="btn btn-gold" href="/book/%(qs)s">Reserve Your Date at %(short)s</a></p>
  </div>''') % dict(name=h(name), cards=cards, qs=qs, short=h(name if len(name) <= 28 else name.split(" at ")[0].split(" by ")[0]))

def faq_block(name, city, st, shot, vtype):
    q1 = "Have you photographed a wedding at %s?" % name
    a1 = ("We have worked in and around %s, so we know how the light and timelines behave here. If %s is new to us, we scout it before your date." % (city, name)) if shot \
         else ("Not yet — and we say so. We scout %s before your wedding: ceremony light, where formals hold up, how long the walk between spaces really takes." % name)
    q2 = "Is there a travel fee for a wedding in %s, %s?" % (city, st)
    a2 = "No. Elizabeth Scott is a national studio and travel is built into every collection, so a wedding at %s costs the same as one across the street from us." % name
    q3 = "How far in advance should we book %s photography?" % name
    a3 = ("Most %s couples book eight to twelve months out; peak %s dates go first. A signed agreement and the retainer hold your date, and the balance is due two weeks before the wedding."
          % (city, "summer and autumn" if st in ("MA", "RI", "CT", "ME", "VT", "NH") else "spring and autumn"))
    items = [(q1, a1), (q2, a2), (q3, a3)]
    html = ('\n  ' + CARD % ("30px", ";margin-top:20px") + '<h2 style="font-family:var(--serif);font-size:25px">Questions couples ask about %s</h2>' % h(name)
            + '<div style="margin-top:8px">'
            + "".join('<details style="border-top:1px solid rgba(255,255,255,.1);padding:12px 0"><summary style="cursor:pointer;color:var(--ice);font-size:16px;list-style:none">%s</summary>'
                      '<p style="color:var(--mist);line-height:1.85;margin-top:8px">%s</p></details>' % (h(q), h(a)) for q, a in items)
            + '</div></div>')
    schema = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in items]}
    return html, schema

def photo_block(seed):
    if not gallery: return ""
    try:
        return gallery.strip(seed, k=4, w=640, q=80, alt="Wedding photograph by Elizabeth Scott", heading="Recent work",
                             note="Selected frames from the Elizabeth Scott portfolio — not photographs taken at this venue. Ask and we will send full galleries closest in size and setting to your wedding.")
    except Exception:
        return ""

# ---------------------------------------------------------------- lastmod
def lastmod_for(canon, html):
    # venue pages are new: their first lastmod is the day they were created, not the site's floor date
    return B.lastmod_for(canon, html, floor=dt.date.today().isoformat()) if hasattr(B, "lastmod_for") else dt.date.today().isoformat()

# ---------------------------------------------------------------- build
def main():
    region_of = {"%s|%s" % (n, s): r for n, s, r in CITIES}
    cities = [(k, v) for k, v in CITY_DATA.items() if v.get("st") in VENUE_STATES and v.get("venues")]
    cities.sort(key=lambda kv: (kv[1]["st"], kv[1]["name"]))
    all_rows, indexed, noindex = [], 0, 0
    venue_index = {}                       # "City|ST" -> {venue name: url}   (gen_cities links these)
    if REPORT_ONLY:
        by_state = {}
        for k, c in cities:
            for v in c["venues"]:
                by_state.setdefault(c["st"], [0, 0])
                by_state[c["st"]][0 if (v.get("reviews") or 0) >= MIN_REVIEWS else 1] += 1
        tot_i = sum(a for a, b in by_state.values()); tot_n = sum(b for a, b in by_state.values())
        print("venue pages: %d indexed, %d noindex (fewer than %d reviews) across %d cities" % (tot_i, tot_n, MIN_REVIEWS, len(cities)))
        for st, (a, b) in sorted(by_state.items()):
            print("  %s  %3d indexed  %2d noindex" % (st, a, b))
        return

    OUT.mkdir(exist_ok=True)
    sitemap = []
    for key, cd in cities:
        city, st = cd["name"], cd["st"]
        cslug = slug("%s %s" % (city, st))
        # JC-ESW-JOURNAL-0910-001: the city page is written by gen_cities.py, whose slug drops
        # apostrophes ("Martha's Vineyard MA" -> marthas-vineyard-ma); mirror it here so the
        # back-link resolves. Venue/hub paths keep this file's own slug (already indexed).
        city_url = "/wedding-photographer/%s" % slug(("%s %s" % (city, st)).replace("&", "and").replace("'", ""))
        region = REGIONS.get(region_of.get(key, "ne"), REGIONS["ne"])
        shot = ("%s, %s" % (city, st)).lower() in SHOT_HERE
        vs = [v for v in cd["venues"] if v.get("name")]
        (OUT / cslug).mkdir(exist_ok=True)
        hub_rows = ""
        for v in vs:
            name = v["name"].strip()
            vslug = slug(name)
            canon = "%s/venues/%s/%s" % (BASE, cslug, vslug)
            venue_index.setdefault(key, {})[name] = "/venues/%s/%s" % (cslug, vslug)
            reviews = int(v.get("reviews") or 0); rating = v.get("rating")
            is_indexed = reviews >= MIN_REVIEWS
            vt_key, vt_para = venue_type(name)
            dist_city = miles(cd["lat"], cd["lng"], v["lat"], v["lng"]) if (cd.get("lat") and v.get("lat")) else None
            # nearby venues by real distance from this one
            near = []
            for o in vs:
                if o is v or not (o.get("lat") and v.get("lat")): continue
                near.append((miles(v["lat"], v["lng"], o["lat"], o["lng"]), o))
            near.sort(key=lambda t: t[0])
            near_html = "".join('<a href="/venues/%s/%s" style="display:block;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.08);color:var(--ice);text-decoration:none">%s <span style="color:var(--mist);font-size:13px">&middot; %s away%s</span></a>'
                                % (cslug, slug(o["name"]), h(o["name"]), fmt_miles(m), (" &middot; %.1f &#9733;" % o["rating"]) if o.get("rating") else "")
                                for m, o in near[:5])
            rating_txt = ("%.1f &#9733; from %s Google reviews" % (rating, "{:,}".format(reviews))) if rating and reviews else ""
            where = ("%s sits %s from the center of %s" % (h(name), fmt_miles(dist_city), h(city))) if dist_city is not None else ("%s is in %s, %s" % (h(name), h(city), st))
            sub = "%s%s. Senior photographers and filmmakers, travel included, published pricing." % (where, (" &mdash; " + rating_txt) if rating_txt else "")
            qs = "?venue=%s&amp;city=%s" % (H.escape(name).replace(" ", "%20"), H.escape(city).replace(" ", "%20"))
            scout = (("We have worked in and around %s before, so we know how the light behaves here and which timelines hold up." % h(city)) if shot
                     else ("If we haven&rsquo;t worked %s yet we scout it before your day &mdash; light, timing, logistics &mdash; so nothing about the venue surprises us on the morning of." % h(name)))
            light = light_para(name, st, v.get("lat"), v.get("lng")).replace("__CITYURL__", city_url).replace("__CITYNAME__", h(city))
            faq_html, faq_schema = faq_block(name, city, st, shot, vt_key)
            hk = ["hero", "hero2", "hero3", "hero4"][sum(ord(c) for c in name) % 4]
            hero_html = HERO % dict(hk=hk, city=h(city), st=st, name=h(name), sub=sub)
            tpl = '''
<section class="section"><div class="wrap" style="max-width:860px">
  ''' + (CARD % ("32px", "")) + '''
    <h2 style="font-family:var(--serif);font-size:26px">Photographing a wedding at %(name)s</h2>
    <p style="color:var(--mist);line-height:1.9;margin-top:12px">%(vtpara)s</p>
    <p style="color:var(--mist);line-height:1.9;margin-top:14px">%(flavor)s %(scout)s</p>%(light)s
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-top:20px">
      <div style="padding:14px 16px;border:1px solid rgba(255,255,255,.1);border-radius:12px"><div style="color:var(--mist);font-size:12px;letter-spacing:1px;text-transform:uppercase">Venue</div><div style="color:var(--ice);margin-top:4px">%(name)s</div><div style="color:var(--mist);font-size:13.5px;margin-top:2px">%(addr)s</div></div>
      %(ratingcard)s
      <div style="padding:14px 16px;border:1px solid rgba(255,255,255,.1);border-radius:12px"><div style="color:var(--mist);font-size:12px;letter-spacing:1px;text-transform:uppercase">From us</div><div style="color:var(--ice);margin-top:4px">Travel included</div><div style="color:var(--mist);font-size:13.5px;margin-top:2px">Same price at every venue</div></div>
    </div>
  </div>%(photos)s%(pricing)s%(faq)s
  ''' + (CARD % ("30px", ";margin-top:20px")) + '''
    <h2 style="font-family:var(--serif);font-size:25px">Other venues near %(name)s</h2>
    <div style="margin-top:8px">%(near)s</div>
    <p style="color:var(--mist);font-size:14px;margin-top:16px"><a href="/venues/%(cslug)s/" style="color:var(--champagne)">All %(city)s venues</a> &nbsp;&middot;&nbsp; <a href="%(cityurl)s" style="color:var(--champagne)">%(city)s wedding photography</a> &nbsp;&middot;&nbsp; <a href="/venues/" style="color:var(--champagne)">every venue we cover</a></p>
  </div>
  %(disc)s
</div></section>'''
            body = hero_html + tpl % dict(
                name=h(name), vtpara=vt_para, flavor=h(region["flavor"] % dict(city=city)), scout=scout, light=light,
                addr=h(v.get("addr") or "%s, %s" % (city, st)),
                ratingcard=('<div style="padding:14px 16px;border:1px solid rgba(255,255,255,.1);border-radius:12px"><div style="color:var(--mist);font-size:12px;letter-spacing:1px;text-transform:uppercase">Couples say</div><div style="color:var(--champagne);margin-top:4px;font-size:18px">%.1f &#9733;</div><div style="color:var(--mist);font-size:13.5px;margin-top:2px">%s Google reviews</div></div>' % (rating, "{:,}".format(reviews))) if rating and reviews else "",
                photos=photo_block("%s|%s" % (name, st)), pricing=pricing_block(name, qs), faq=faq_html,
                near=near_html or '<p style="color:var(--mist)">More %s venues are on the way.</p>' % h(city),
                cslug=cslug, city=h(city), cityurl=city_url, disc=DISC)
            place = {"@context": "https://schema.org", "@type": "Service",
                     "name": "Wedding Photography & Videography at %s" % name,
                     "serviceType": "Wedding photography and videography",
                     "provider": {"@type": "Organization", "name": "Elizabeth Scott", "url": BASE + "/"},
                     "areaServed": {"@type": "Place", "name": name, "address": v.get("addr") or ("%s, %s" % (city, st)),
                                    **({"geo": {"@type": "GeoCoordinates", "latitude": v["lat"], "longitude": v["lng"]}} if v.get("lat") else {})},
                     "url": canon}
            crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE + "/"},
                {"@type": "ListItem", "position": 2, "name": "Venues", "item": BASE + "/venues/"},
                {"@type": "ListItem", "position": 3, "name": "%s, %s" % (city, st), "item": "%s/venues/%s/" % (BASE, cslug)},
                {"@type": "ListItem", "position": 4, "name": name, "item": canon}]}
            schema = "".join('<script type="application/ld+json">%s</script>' % json.dumps(x) for x in (place, crumbs, faq_schema))
            title = "%s Weddings &middot; %s, %s &middot; Photo &amp; Film | Elizabeth Scott" % (h(name), h(city), st)
            desc = ("Wedding photography and film at %s in %s, %s. Senior team, travel included, published pricing. %s"
                    % (name, city, st, ("%.1f stars from %s Google reviews." % (rating, "{:,}".format(reviews))) if rating and reviews else ""))[:158]
            html = B.render_page(title, h(desc), canon, body, schema, "index, follow" if is_indexed else "noindex, follow", nav_key="locations")
            (OUT / cslug / (vslug + ".html")).write_text(html, encoding="utf-8")
            if is_indexed:
                sitemap.append((canon, "0.7", lastmod_for(canon, html))); indexed += 1
            else:
                noindex += 1
            hub_rows += ('<a class="glass" style="display:flex;justify-content:space-between;gap:12px;padding:14px 18px;border-radius:14px;color:var(--ice);text-decoration:none" href="/venues/%s/%s"><span>%s</span><span style="color:var(--mist);font-size:13px;white-space:nowrap">%s</span></a>'
                         % (cslug, vslug, h(name), ("%.1f &#9733; &middot; %s" % (rating, "{:,}".format(reviews))) if rating and reviews else ""))

        # ---- city hub
        canon = "%s/venues/%s/" % (BASE, cslug)
        body = (HERO % dict(hk="hero2", city=h(city), st=st, name="%s Wedding Venues" % h(city),
                            sub="The %s venues couples ask us about most, each with its own page: the light, the pricing, the plan. Travel is included wherever you marry." % h(city))) + '''
<section class="section"><div class="wrap" style="max-width:860px">
  <div style="display:grid;gap:10px">%s</div>
  <p style="text-align:center;margin-top:26px"><a class="btn btn-gold" href="%s">%s wedding photography</a> &nbsp;&nbsp;<a class="btn" href="/venues/" style="margin-left:8px">All venues</a></p>
  %s
</div></section>''' % (hub_rows, city_url, h(city), DISC)
        html = B.render_page("%s Wedding Venues &mdash; Photo &amp; Film | Elizabeth Scott" % h(city),
                             h("Wedding photography and film at %d %s, %s venues — pricing, light, and planning notes for each. Travel included." % (len(vs), city, st))[:158],
                             canon, body, '<script type="application/ld+json">%s</script>' % json.dumps(
                                 {"@context": "https://schema.org", "@type": "CollectionPage", "name": "%s Wedding Venues" % city, "url": canon}),
                             "index, follow" if any((x.get("reviews") or 0) >= MIN_REVIEWS for x in vs) else "noindex, follow", nav_key="locations")
        (OUT / cslug / "index.html").write_text(html, encoding="utf-8")
        sitemap.append((canon, "0.8", lastmod_for(canon, html)))

    # ---- master hub
    by_state = {}
    for key, cd in cities:
        by_state.setdefault(cd["st"], []).append(cd)
    names = {"TX": "Texas", "MA": "Massachusetts", "RI": "Rhode Island", "CT": "Connecticut", "ME": "Maine", "VT": "Vermont", "NH": "New Hampshire",
             "NY": "New York", "NJ": "New Jersey", "PA": "Pennsylvania", "AZ": "Arizona", "CA": "California", "CO": "Colorado", "FL": "Florida", "GA": "Georgia"}
    groups = ""
    for st in sorted(by_state, key=lambda s: names.get(s, s)):
        links = "".join('<a class="glass" style="display:block;padding:12px 16px;border-radius:12px;color:var(--ice);text-decoration:none" href="/venues/%s/">%s <span style="color:var(--mist);font-size:13px">&middot; %d venues</span></a>'
                        % (slug("%s %s" % (c["name"], c["st"])), h(c["name"]), len(c["venues"])) for c in by_state[st])
        groups += '<h2 style="font-family:var(--serif);font-size:24px;margin-top:26px">%s</h2><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;margin-top:10px">%s</div>' % (h(names.get(st, st)), links)
    total = sum(len(c["venues"]) for _, c in cities)
    canon = BASE + "/venues/"
    body = (HERO % dict(hk="hero3", city="Venues", st="Travel Included", name="Wedding Venues", sub="Already booked your venue? Find it below. %d venues across %d cities, each with its own page — what the light does there, what we charge, and how we would run the day." % (total, len(cities)))).replace("Venues, Travel Included", "Every venue we cover") + '''
<section class="section"><div class="wrap" style="max-width:960px">%s
  <p style="text-align:center;margin-top:30px"><a class="btn btn-gold" href="/book/">Reserve Your Date</a> &nbsp;&nbsp;<a class="btn" href="/locations/" style="margin-left:8px">All locations</a></p>
  %s
</div></section>''' % (groups, DISC)
    html = B.render_page("Wedding Venues We Photograph &mdash; %d Venues | Elizabeth Scott" % total,
                         "Wedding photography and film at %d venues across Texas and New England. Pricing, light, and planning notes for each venue. Travel included." % total,
                         canon, body, '<script type="application/ld+json">%s</script>' % json.dumps({"@context": "https://schema.org", "@type": "CollectionPage", "name": "Wedding Venues", "url": canon}),
                         nav_key="locations")
    (OUT / "index.html").write_text(html, encoding="utf-8")
    sitemap.insert(0, (canon, "0.8", lastmod_for(canon, html)))

    # ---- sitemap + link index for gen_cities
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u, pr, lm in sitemap:
        xml.append('  <url><loc>%s</loc><lastmod>%s</lastmod><priority>%s</priority></url>' % (u, lm, pr))
    xml.append("</urlset>")
    (ROOT / "sitemap-venues.xml").write_text("\n".join(xml), encoding="utf-8")
    (SRC / "venue_pages.json").write_text(json.dumps(venue_index, indent=0), encoding="utf-8")
    if hasattr(B, "save_lastmod_cache"): B.save_lastmod_cache()
    print("venues: %d pages indexed, %d noindex, %d city hubs + master | sitemap-venues.xml (%d urls) | venue_pages.json for gen_cities"
          % (indexed, noindex, len(cities), len(sitemap)))

if __name__ == "__main__":
    main()
