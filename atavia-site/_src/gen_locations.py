#!/usr/bin/env python3
"""Generate SEO location pages for Atavia Weddings: metro pages, 50 state pages,
and a nationwide hub. Edit METROS / STATES and re-run, then run build.py."""
import pathlib
import re as _re, json as _json

SRC = pathlib.Path(__file__).resolve().parent
BASE = "https://ataviaweddings.com"

HERO = "https://firebasestorage.googleapis.com/v0/b/atavia-c29cd.firebasestorage.app/o/DSC_4772.jpg?alt=media&token=5182d7b9-096f-4902-a8b6-7ef2cd2e865a"
CTA  = "https://firebasestorage.googleapis.com/v0/b/atavia-c29cd.firebasestorage.app/o/atavia16.png?alt=media&token=4fff66fd-0144-474e-8fc1-d4ad8b6ab499"
OG   = CTA
KNOT = "https://firebasestorage.googleapis.com/v0/b/atavia-c29cd.firebasestorage.app/o/The-Knot-vendor-badge.webp?alt=media&token=f928d4da-e25e-4594-8098-57e56aebbfc0"
ZOLA = "https://firebasestorage.googleapis.com/v0/b/atavia-c29cd.firebasestorage.app/o/Zola-Vendor-Badge-Utah-Live-Bands.png?alt=media&token=4e2c2497-f24d-4ede-b543-ac3e8196eb31"
KNOT_URL = "https://www.theknot.com/marketplace/atavia-weddings-boston-ma-2104981"
ZOLA_URL = "https://www.zola.com/wedding-vendors/wedding-videographers/atavia-weddings--2"

def esc(u): return u.replace("&", "&amp;")

REVIEWS = [
    ("Our wedding film completely exceeded our expectations — it felt like watching a movie of our own love story.", "Emily &amp; Sean"),
    ("They captured every moment so beautifully, from the big emotional highlights to the quiet details we didn't even notice.", "Kate &amp; Zach"),
    ("One team for photo and video was the best decision we made — the style is so consistent, and it captured our day exactly how it felt.", "David &amp; Elizabeth"),
    ("The photos are absolutely stunning. They made us feel so comfortable, and it shows in how natural everything looks.", "Ben &amp; Sarah"),
]

# ---- shared body ----
BODY = """<!-- ===== HERO ===== -->
<section class="page-hero">
  <div class="page-hero__bg" aria-hidden="true">
    <img src="{HEROIMG}" alt="" onerror="this.onerror=null;this.src='{HERORAW}'">
  </div>
  <span class="page-hero__watermark" aria-hidden="true">A</span>
  <div class="wrap">
    <div class="eyebrow center rules reveal">{EYEBROW}</div>
    <h1 class="page-hero__title reveal d1">{PLACE} Wedding<br><em>Videographer &amp; Photographer</em></h1>
    <p class="page-hero__sub reveal d2">{HEROSUB}</p>
    <div style="margin-top:clamp(26px,4vw,36px)" class="reveal d3">
      <a href="/book/" class="btn btn--copper">Check Availability <span class="arr">&#8599;</span></a>
    </div>
  </div>
</section>

<!-- ===== LOCAL PITCH ===== -->
<section class="sec">
  <div class="wrap" style="text-align:center;max-width:760px">
    <div class="sec__head reveal" style="margin-bottom:0">
      <div class="sec__roman">{LOCALHEAD}</div>
      <h2 class="sec__title">A local crew &mdash; <em>no travel fees.</em></h2>
      <div class="rule"></div>
    </div>
    <p class="reveal d1" style="margin-top:26px;color:var(--ivory-dim);font-size:clamp(15px,1.7vw,17px);line-height:1.85">{INTRO}</p>
    <p class="reveal d1" style="margin-top:18px;color:var(--ivory-dim);font-size:clamp(15px,1.7vw,17px);line-height:1.85">{INTRO2}</p>
  </div>
</section>

<!-- ===== COVERAGE ===== -->
<section class="sec sec--tight">
  <div class="wrap" style="text-align:center;max-width:840px">
    <div class="eyebrow center rules reveal">{COVEYE}</div>
    <h2 class="sec__title reveal d1" style="margin-top:14px;font-size:clamp(28px,4vw,50px)">{COVH2}</h2>
    <p class="reveal d2" style="color:var(--ivory-dim);margin-top:22px;font-size:clamp(15px,1.7vw,17px);line-height:1.85">{COVP}</p>
  </div>
</section>

<!-- ===== OFFERINGS ===== -->
<section class="sec">
  <div class="wrap">
    <div class="sec__head reveal">
      <div class="sec__roman">What We Offer</div>
      <h2 class="sec__title">Film, photo, or <em>both.</em></h2>
      <div class="rule"></div>
    </div>
    <div class="cards cards--3">
      <a href="/packages" class="fcard reveal" style="text-decoration:none">
        <div class="fcard__idx">01</div><h3>Photography</h3>
        <div class="fcard__rule" aria-hidden="true"></div>
        <p>Genuine emotion, refined details, and timeless stills of your day.</p>
        <span class="fcard__link">See packages &#8599;</span>
      </a>
      <a href="/packages" class="fcard reveal d1" style="text-decoration:none">
        <div class="fcard__idx">02</div><h3>Videography</h3>
        <div class="fcard__rule" aria-hidden="true"></div>
        <p>A cinematic film of the day &mdash; vows, laughter, and the moments between.</p>
        <span class="fcard__link">See packages &#8599;</span>
      </a>
      <a href="/packages" class="fcard reveal d2" style="text-decoration:none">
        <div class="fcard__idx">03</div><h3>Photo &amp; Film</h3>
        <div class="fcard__rule" aria-hidden="true"></div>
        <p>One team, one vision &mdash; your day held in both stillness and motion.</p>
        <span class="fcard__link">See packages &#8599;</span>
      </a>
    </div>
    <div style="text-align:center;margin-top:44px" class="reveal">
      <a href="/films" class="btn btn--ghost" style="margin-right:12px">Watch Our Films <span class="arr">&#8599;</span></a>
      <a href="/gallery" class="btn btn--ghost">View the Gallery <span class="arr">&#8599;</span></a>
    </div>
  </div>
</section>

{AREA}
{FAQ}
<!-- ===== SOCIAL PROOF ===== -->
<section class="sec sec--tight">
  <div class="wrap" style="text-align:center;max-width:760px">
    <div class="quote-mark reveal">&ldquo;</div>
    <p class="reveal" style="font-family:var(--display);font-style:italic;font-size:clamp(21px,2.7vw,28px);color:var(--ivory);line-height:1.55;margin-top:-10px">{REVIEW}</p>
    <p class="reveal" style="color:var(--copper);letter-spacing:.2em;text-transform:uppercase;font-size:12px;margin-top:20px">{COUPLE}</p>
    <div class="badges-row reveal">
      <span class="lbl">As Featured On</span>
      <a class="badge-logo" href="{KNOTURL}" target="_blank" rel="noopener" aria-label="View Atavia Weddings on The Knot"><img src="{KNOTIMG}" alt="As seen on The Knot" loading="lazy"></a>
      <a class="badge-logo" href="{ZOLAURL}" target="_blank" rel="noopener" aria-label="View Atavia Weddings on Zola"><img src="{ZOLAIMG}" alt="Featured on Zola" loading="lazy"></a>
    </div>
  </div>
</section>

<!-- ===== CTA ===== -->
<section class="cta-band cta-band--img" aria-label="Book Atavia Weddings">
  <img src="{CTAIMG}" alt="" loading="lazy" onerror="this.onerror=null;this.src='{CTARAW}'">
  <div class="wrap reveal">
    <span class="eyebrow center rules">{CTAEYE}</span>
    <h2 class="cta-band__title" style="font-size:clamp(30px,4.6vw,58px);margin-top:20px">{CTAH2}</h2>
    <a href="/book/" class="btn btn--copper" style="margin-top:26px">Reserve Your Date <span class="arr">&#8599;</span></a>
  </div>
</section>
"""

def render_body(fields):
    b = BODY
    consts = dict(HEROIMG=esc(HERO), HERORAW=HERO, CTAIMG=esc(CTA), CTARAW=CTA,
                  KNOTIMG=esc(KNOT), ZOLAIMG=esc(ZOLA), KNOTURL=KNOT_URL, ZOLAURL=ZOLA_URL)
    for k, v in {**consts, **fields}.items():
        b = b.replace("{" + k + "}", v)
    return b

def schema_for(name, canon, area_type="City"):
    return ('<script type="application/ld+json">'
            '{"@context":"https://schema.org","@type":"LocalBusiness","name":"Atavia Weddings",'
            '"description":"Wedding videography and photography serving %s. Local team, no travel fees.",'
            '"url":"%s","telephone":"+1-336-537-9590","email":"info@ataviaweddings.com",'
            '"image":"%s","priceRange":"$$-$$$","areaServed":{"@type":"%s","name":"%s"},'
            '"sameAs":["https://www.instagram.com/ataviaweddings"]}</script>'
            ) % (name, canon, OG, area_type, name)

def metro_extra_schema(city, state, canon):
    """JC-ATV-SEO-0927: breadcrumbs (Home > Nationwide > City) and a Service with real starting prices."""
    plain = city.replace("&amp;", "&")   # JSON-LD is not HTML: no entities inside the script
    crumbs = ('<script type="application/ld+json">{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":['
              '{"@type":"ListItem","position":1,"name":"Home","item":"%s/"},'
              '{"@type":"ListItem","position":2,"name":"Nationwide","item":"%s/nationwide-wedding-videographer"},'
              '{"@type":"ListItem","position":3,"name":"%s","item":"%s"}]}</script>') % (BASE, BASE, _json.dumps(plain)[1:-1], canon)
    offers = [("Wedding Videography", "Cinematic wedding films, 4 to 10 hours of coverage, raw footage included.", 1200),
              ("Wedding Photography", "Wedding photography, 4 to 10 hours of coverage, engagement session included.", 1500),
              ("Photo & Film", "One team for photography and videography, 6 to 10 hours of coverage.", 3000)]
    service = ('<script type="application/ld+json">{"@context":"https://schema.org","@type":"Service","name":"Wedding Videography & Photography in %s",'
               '"serviceType":"Wedding videography and photography","provider":{"@id":"https://ataviaweddings.com/#business"},'
               '"areaServed":{"@type":"City","name":"%s","containedInPlace":{"@type":"State","name":"%s"}},"url":"%s",'
               '"hasOfferCatalog":{"@type":"OfferCatalog","name":"Collections","itemListElement":[%s]}}</script>') % (
               plain, plain, state, canon,
               ",".join('{"@type":"Offer","itemOffered":{"@type":"Service","name":"%s","description":"%s"},'
                        '"priceSpecification":{"@type":"PriceSpecification","price":%d,"priceCurrency":"USD","minPrice":%d}}' % (n, d, pr, pr)
                        for n, d, pr in offers))
    return crumbs + service

manifest = []
ri = 0
def next_review():
    global ri
    r = REVIEWS[ri % len(REVIEWS)]; ri += 1; return r

# ============ METRO PAGES ============
# slug, display, state, region, intro, [venues], venue_tail
METROS = [
 ("minneapolis-wedding-videographer","Minneapolis","Minnesota","the Twin Cities",
  "The Twin Cities do weddings with a quiet confidence — lakeside vows in summer, candlelit warehouses when the snow comes. Our dedicated Minnesota team already knows the golden hour on Nicollet Island and how to move through a winter wedding without missing a beat.",
  ["The Depot","Nicollet Island Pavilion","Aria"],"a lakeside estate on Lake Minnetonka, or a downtown loft"),
 ("boston-wedding-videographer","Boston","Massachusetts","Greater Boston &amp; New England",
  "From the brownstones of Back Bay to the coastline north of the city, a Boston wedding carries real history — and deserves to be filmed like it. Our New England crew knows these rooms, this light, and how a fall afternoon turns on a dime.",
  ["the Boston Public Library","the Fairmont Copley Plaza","the State Room"],"a North Shore seaside estate, or a historic Beacon Hill townhouse"),
 ("phoenix-wedding-videographer","Phoenix &amp; Scottsdale","Arizona","the Valley of the Sun",
  "Desert light is unlike anything else — long, warm, and forgiving, with mountain backdrops that make golden hour feel endless. Our Arizona team lives for Scottsdale and Paradise Valley weddings and knows exactly when that light turns.",
  ["the Wrigley Mansion","El Chorro","the Desert Botanical Garden"],"a Paradise Valley resort, or a private desert estate"),
 ("los-angeles-wedding-videographer","Los Angeles","California","Greater Los Angeles",
  "From the coast to the canyons, Los Angeles weddings run the full range — rooftop city lights, ranch sunsets, and everything between. Our Southern California team knows how to shoot them all and beat the traffic doing it.",
  ["Vibiana","the Ebell of Los Angeles","Calamigos Ranch"],"a Malibu coastline, or a Hollywood Hills estate"),
 ("new-york-wedding-videographer","New York City","New York","the New York metro",
  "A New York wedding moves fast and looks like nowhere else — rooftops against the skyline, industrial lofts, ballrooms with a century of stories. Our NYC team knows how to work the city's tight timelines and tighter spaces.",
  ["The Plaza","Tribeca Rooftop","The Bowery Hotel"],"a Brooklyn waterfront loft, or a Hudson Valley estate"),
 ("chicago-wedding-videographer","Chicago","Illinois","Chicagoland",
  "Chicago pairs lakefront skyline views with some of the country's most beautiful historic architecture. Our Chicago team knows the city's landmark rooms and how to make a lakeside ceremony feel as cinematic as it looks.",
  ["the Rookery","Salvage One","Galleria Marchetti"],"a Gold Coast ballroom, or a lakefront terrace"),
 ("miami-wedding-videographer","Miami","Florida","South Florida",
  "Miami weddings are made of warm light, water, and color — art-deco glamour one weekend, tropical garden the next. Our South Florida team knows the coast, the estates, and how to chase that late-day glow.",
  ["Vizcaya","the Biltmore","Villa Woodbine"],"a Miami Beach rooftop, or a waterfront estate"),
 ("atlanta-wedding-videographer","Atlanta","Georgia","metro Atlanta",
  "Atlanta blends Southern warmth with historic estates and green, garden-draped venues. Our Georgia team knows the city's landmark homes and how to hold onto that soft Southern light.",
  ["the Swan House","Summerour Studio","the Georgian Terrace"],"a garden estate, or a downtown skyline venue"),
 ("dallas-wedding-videographer","Dallas","Texas","the Dallas-Fort Worth metroplex",
  "Dallas does weddings on a grand scale — sleek downtown skylines, sprawling garden estates, and that unmistakable Texas hospitality. Our North Texas team knows the metroplex's landmark venues and how to work the big-sky light from ceremony through the last dance.",
  ["the Adolphus","the Dallas Arboretum","Marie Gabrielle"],"a ranch estate, or a downtown high-rise"),
 ("denver-wedding-videographer","Denver","Colorado","the Front Range",
  "Denver weddings come with a backdrop few places can match — Rocky Mountain peaks, foothill vistas, and that crisp, high-altitude light. Our Colorado team knows the Front Range's landmark venues and the mountain towns beyond, from a downtown ballroom to a lodge above the treeline.",
  ["the Brown Palace","Denver Botanic Gardens","the Manor House"],"a mountain lodge in the Rockies, or a foothills estate"),
 ("las-vegas-wedding-videographer","Las Vegas","Nevada","the Las Vegas valley",
  "Las Vegas weddings run every direction at once — a chapel on the Strip, a country-club ballroom, a red-rock ceremony at sunset. Our Nevada team knows the valley's venues and how to work that famous desert light before the city switches on.",
  ["Stallion Mountain","the Neon Museum","Red Rock Canyon"],"a Strip resort, or a desert overlook"),
]
# JC-ATV-SEO-0924: metro pages sat at position 40-60 for "<city> wedding videographer" with
# ~420 words of copy and no links into the venue directory. Each one now lists the directory
# venues around the metro (grouped by town, linking the venue pages and city hubs) and ends
# with a short pricing FAQ carrying FAQPage schema.
import re as _re, json as _json
from venues_data import VENUES
from venue_photos import PHOTOS
_ST_NAME = {"MN":"Minnesota","MA":"Massachusetts","AZ":"Arizona","CA":"California","NY":"New York",
            "IL":"Illinois","FL":"Florida","GA":"Georgia","TX":"Texas","CO":"Colorado","NV":"Nevada"}
METRO_AREA = {   # metro slug -> (state, towns in display order)
 "minneapolis-wedding-videographer": ("MN", ["Minneapolis","St. Paul","Saint Paul","Stillwater","Wayzata","Excelsior","Bloomington","Minnetonka","Edina","Anoka","Hastings","Chaska"]),
 "boston-wedding-videographer": ("MA", ["Boston","Cambridge","Newton","Brookline","Quincy","Salem","Beverly","Plymouth","Concord","Somerville","Waltham","Ipswich"]),
 "phoenix-wedding-videographer": ("AZ", ["Phoenix","Scottsdale","Paradise Valley","Mesa","Tempe","Chandler","Gilbert","Cave Creek","Glendale","Peoria","Queen Creek","Carefree"]),
 "los-angeles-wedding-videographer": ("CA", ["Los Angeles","Malibu","Pasadena","Santa Monica","Long Beach","Beverly Hills","Burbank","Glendale","Calabasas","Agoura Hills","Torrance","Santa Clarita"]),
 "new-york-wedding-videographer": ("NY", ["New York","Brooklyn","Manhattan","Queens","Bronx","Staten Island","Long Island City","Yonkers","White Plains","Tarrytown"]),
 "chicago-wedding-videographer": ("IL", ["Chicago","Evanston","Oak Park","Naperville","Schaumburg","Rosemont","Lemont","Oak Brook","Highland Park","St. Charles","Plainfield"]),
 "miami-wedding-videographer": ("FL", ["Miami","Miami Beach","Coral Gables","Key Biscayne","Homestead","Hialeah","Fort Lauderdale","Hollywood","Boca Raton"]),
 "atlanta-wedding-videographer": ("GA", ["Atlanta","Decatur","Marietta","Roswell","Alpharetta","Duluth","Buford","Canton","Cumming","Newnan","Peachtree City","Dahlonega"]),
 "dallas-wedding-videographer": ("TX", ["Dallas","Fort Worth","Plano","Frisco","McKinney","Arlington","Irving","Grapevine","Denton","Aubrey","Weatherford","Royse City"]),
 "denver-wedding-videographer": ("CO", ["Denver","Boulder","Golden","Morrison","Evergreen","Littleton","Lakewood","Castle Rock","Westminster","Longmont","Parker","Broomfield"]),
 "las-vegas-wedding-videographer": ("NV", ["Las Vegas","Henderson","Boulder City","North Las Vegas"]),
}
def _slug(s):   # must match gen_venues.slug
    s = s.replace("&amp;", "and").replace("&", "and").lower()
    s = _re.sub(r"[’']", "", s)
    return _re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "x"
def _h(s): return (s or "").replace("&amp;", "&").replace("&", "&amp;")
_BY_TOWN = {}
for _v in VENUES:
    _BY_TOWN.setdefault((_v["state"].upper(), _v["city"]), []).append(_v)
def _rank(v):   # venues we can say something real about come first
    return (not v.get("filmed_here"), not PHOTOS.get(_slug(v["name"])), not (v.get("character") or "").strip(),
            -(v.get("reviews") or 0), v["name"])
def area_html(mslug, city):
    st, towns = METRO_AREA[mslug]
    sslug = _slug(_ST_NAME[st])
    groups, total = [], 0
    for i, town in enumerate(towns):
        vs = sorted(_BY_TOWN.get((st, town), []), key=_rank)
        if not vs:
            continue
        cap = 12 if i == 0 else 6
        cslug = _slug(town)
        links = "".join('<a href="/venues/%s/%s/%s">%s</a>' % (sslug, cslug, _slug(v["name"]), _h(v["name"])) for v in vs[:cap])
        more = ('<a href="/venues/%s/%s/">All %d %s venues &rarr;</a>' % (sslug, cslug, len(vs), _h(town))) if len(vs) > cap else ""
        groups.append('<div class="venue-group reveal"><h3 class="venue-group__city"><a href="/venues/%s/%s/">%s</a> '
                      '<span class="venue-group__count">%d %s</span></h3><div class="loc-grid">%s%s</div></div>'
                      % (sslug, cslug, _h(town), len(vs), "venue" if len(vs) == 1 else "venues", links, more))
        total += len(vs)
    if not groups:
        return ""
    return ('<!-- ===== AREA VENUES ===== -->\n<section class="sec sec--tight"><div class="wrap" style="max-width:1040px">'
            '<div class="sec__head reveal"><div class="sec__roman">Venues Around %s</div>'
            '<h2 class="sec__title">%d venues we photograph &amp; film <em>near %s.</em></h2><div class="rule"></div></div>'
            '<p class="reveal" style="text-align:center;color:var(--ivory-dim);max-width:640px;margin:0 auto 30px;font-size:16px;line-height:1.8">'
            'Already booked your venue? Find it below for venue-specific details &mdash; or '
            '<a href="/venues/%s/" style="color:var(--copper)">browse every %s venue</a>.</p>%s</div></section>'
            % (city, total, city, sslug, _ST_NAME[st], "".join(groups)))
def faq_parts(city, region):
    items = [
        ("How much does a wedding videographer cost in %s?" % city,
         "Atavia film collections start at $1,200 and photography at $1,500, with no travel fees anywhere in %s. "
         "A $500 deposit reserves your date, and every collection includes your raw footage." % region),
        ("Do you charge travel fees for %s weddings?" % city,
         "No. A local Atavia team covers %s, so there is no out-of-town crew and no travel line on your invoice." % region),
        ("Can one team cover both photo and video?",
         "Yes. Our Photo &amp; Film collections put your photographer and filmmaker on one team with one plan for the day, "
         "so nobody is in the other&rsquo;s shot. See <a href=\"/packages\" style=\"color:var(--copper)\">packages</a>."),
        ("Will we get the raw footage?",
         "Yes. Every collection includes complimentary access to your raw footage alongside the edited film."),
        ("How many hours of coverage does a %s wedding need?" % city,
         "Collections run 4, 6, 8 or 10 hours. Eight hours is the most popular: it covers the end of getting ready, the ceremony, "
         "portraits, and the reception through the first dances. Add hours &agrave; la carte when you book if your timeline runs longer."),
        ("Is a second shooter worth it?",
         "For weddings of eight hours or more, or with a large wedding party, usually yes. A second photographer or videographer "
         "is in two places at once &mdash; both of you getting ready, key reactions during the vows, wide and intimate angles together &mdash; "
         "and brings backup gear. It is a $500 add-on on any collection."),
        ("How does booking work?",
         "Choose your collection on our <a href=\"/book/\" style=\"color:var(--copper)\">booking page</a>, sign the agreement online, and a $500 retainer "
         "is charged the moment you sign. Your remaining balance is charged automatically 14 business days after signing, or you can pay in full up front."),
        ("Are you insured?",
         "Fully insured, for your peace of mind and your venue&rsquo;s, and we carry backup cameras and audio on every wedding."),
    ]
    html = ('<!-- ===== FAQ ===== -->\n<section class="sec sec--tight"><div class="wrap" style="max-width:760px">'
            '<div class="sec__head reveal"><div class="sec__roman">Good to Know</div>'
            '<h2 class="sec__title">%s wedding videography <em>questions.</em></h2><div class="rule"></div></div>'
            '<div class="reveal d1">%s</div></div></section>'
            % (city, "".join('<h3 style="font-family:var(--display);font-size:clamp(19px,2.3vw,23px);color:var(--ivory);margin:26px 0 8px">%s</h3>'
                             '<p style="color:var(--ivory-dim);line-height:1.8;font-size:15.5px;margin:0">%s</p>' % (q, a) for q, a in items)))
    txt = lambda t: _re.sub(r"<[^>]+>", "", t).replace("&amp;", "&").replace("&rsquo;", "’")
    schema = ('<script type="application/ld+json">{"@context":"https://schema.org","@type":"FAQPage","mainEntity":['
              + ",".join('{"@type":"Question","name":%s,"acceptedAnswer":{"@type":"Answer","text":%s}}'
                         % (_json.dumps(txt(q)), _json.dumps(txt(a))) for q, a in items) + ']}</script>')
    return html, schema

for slug, city, state, region, intro, venues, tail in METROS:
    review, couple = next_review()
    faq_block, faq_schema = faq_parts(city, region)
    vlist = ", ".join(venues[:-1]) + ", " + venues[-1]
    fields = dict(
        PLACE=city, EYEBROW="%s Weddings" % state,
        HEROSUB="Cinematic films and timeless photography for %s couples &mdash; with a local team and <strong>no travel fees</strong>." % city,
        LOCALHEAD="Local to %s" % region,
        INTRO=intro,
        INTRO2="Because we keep a dedicated team in your area, %s couples get photographers and filmmakers who already know the venues and the light &mdash; without the travel fees most out-of-town studios add. You also get complimentary access to your raw footage, and a <strong>$500 deposit</strong> reserves your date." % city,
        COVEYE="Where We Shoot in %s" % city,
        COVH2="From %s to %s" % (venues[0], venues[1]),
        COVP="Whether you're celebrating at %s, %s, we'll capture %s exactly as your day feels &mdash; from the first look to the last dance." % (vlist, tail, city),
        AREA=area_html(slug, city), FAQ=faq_block,
        REVIEW=review, COUPLE=couple,
        CTAEYE="%s Weddings" % city, CTAH2="Let's capture your<br><em>%s wedding.</em>" % city)
    (SRC / "pages" / (slug + ".html")).write_text(render_body(fields))
    canon = BASE + "/" + slug
    manifest.append(dict(slug=slug, out=slug + ".html", nav="", tier="metro", footer_label=city,
        title="%s Wedding Videographer &amp; Photographer | Films from $1,200 | Atavia" % city,
        desc="%s wedding videographers &amp; photographers with a local team &mdash; no travel fees, raw footage included. Films from $1,200, photos from $1,500. See the venues we shoot across %s." % (city, region),
        canon=canon, schema_html=schema_for(city.replace("&amp;","&") + ", " + state, canon, "City") + faq_schema + metro_extra_schema(city, state, canon)))

# ============ 50 STATE PAGES ============
# state, abbr, [city1, city2, city3], character phrase
STATES = [
 ("Alabama","AL",["Birmingham","Huntsville","Mobile"],"Southern gardens, antebellum estates, and Gulf Coast shores"),
 ("Alaska","AK",["Anchorage","Fairbanks","Juneau"],"glaciers, mountain lodges, and long summer light"),
 ("Arizona","AZ",["Phoenix","Tucson","Sedona"],"red-rock canyons, desert sunsets, and saguaro-dotted vistas"),
 ("Arkansas","AR",["Little Rock","Fayetteville","Hot Springs"],"Ozark hills, spring-fed valleys, and historic town squares"),
 ("California","CA",["Los Angeles","San Francisco","San Diego"],"the Pacific coast, wine-country vineyards, and canyon ranches"),
 ("Colorado","CO",["Denver","Boulder","Colorado Springs"],"Rocky Mountain peaks, alpine meadows, and mountain-town views"),
 ("Connecticut","CT",["Hartford","New Haven","Stamford"],"coastal New England, historic estates, and autumn color"),
 ("Delaware","DE",["Wilmington","Dover","Rehoboth Beach"],"the Brandywine Valley, grand estates, and Atlantic beaches"),
 ("Florida","FL",["Miami","Orlando","Tampa"],"warm coastlines, tropical gardens, and art-deco glamour"),
 ("Georgia","GA",["Atlanta","Savannah","Athens"],"Southern charm, historic homes, and moss-draped gardens"),
 ("Hawaii","HI",["Honolulu","Maui","Kauai"],"ocean cliffs, tropical shores, and island sunsets"),
 ("Idaho","ID",["Boise","Coeur d'Alene","Sun Valley"],"mountain lakes, river valleys, and wide-open country"),
 ("Illinois","IL",["Chicago","Naperville","Springfield"],"lakefront skylines, historic architecture, and prairie estates"),
 ("Indiana","IN",["Indianapolis","Fort Wayne","Bloomington"],"rolling farmland, historic downtowns, and covered-bridge country"),
 ("Iowa","IA",["Des Moines","Cedar Rapids","Iowa City"],"rolling prairie, rustic barns, and river towns"),
 ("Kansas","KS",["Wichita","Kansas City","Overland Park"],"wide prairie skies, historic barns, and open plains"),
 ("Kentucky","KY",["Louisville","Lexington","Bowling Green"],"bluegrass horse country, rolling estates, and bourbon-trail charm"),
 ("Louisiana","LA",["New Orleans","Baton Rouge","Lafayette"],"French Quarter romance, oak-lined avenues, and bayou country"),
 ("Maine","ME",["Portland","Bar Harbor","Bangor"],"rocky coastlines, lighthouse views, and seaside inns"),
 ("Maryland","MD",["Baltimore","Annapolis","Frederick"],"Chesapeake Bay shores, waterfront estates, and historic harbors"),
 ("Massachusetts","MA",["Boston","Cape Cod","the Berkshires"],"coastal New England, historic estates, and Cape shorelines"),
 ("Michigan","MI",["Detroit","Grand Rapids","Traverse City"],"Great Lakes shorelines, vineyard country, and northern woods"),
 ("Minnesota","MN",["Minneapolis","Saint Paul","Duluth"],"ten-thousand lakes, North Shore views, and city lofts"),
 ("Mississippi","MS",["Jackson","Gulfport","Oxford"],"Southern estates, magnolia gardens, and Gulf shores"),
 ("Missouri","MO",["St. Louis","Kansas City","Springfield"],"river bluffs, historic estates, and Ozark country"),
 ("Montana","MT",["Billings","Missoula","Bozeman"],"big-sky ranches, mountain backdrops, and river valleys"),
 ("Nebraska","NE",["Omaha","Lincoln","Grand Island"],"prairie sunsets, historic barns, and wide plains"),
 ("Nevada","NV",["Las Vegas","Reno","Lake Tahoe"],"desert glamour, Tahoe shorelines, and mountain vistas"),
 ("New Hampshire","NH",["Manchester","Portsmouth","Concord"],"White Mountain views, lake country, and autumn color"),
 ("New Jersey","NJ",["Newark","Jersey City","Atlantic City"],"shore towns, garden estates, and skyline views"),
 ("New Mexico","NM",["Albuquerque","Santa Fe","Taos"],"adobe architecture, high-desert light, and mountain sunsets"),
 ("New York","NY",["New York City","Buffalo","the Hudson Valley"],"skyline rooftops, Hudson Valley estates, and Finger Lakes vineyards"),
 ("North Carolina","NC",["Charlotte","Raleigh","Asheville"],"Blue Ridge mountains, coastal shores, and garden estates"),
 ("North Dakota","ND",["Fargo","Bismarck","Grand Forks"],"wide prairie, rustic barns, and open-sky country"),
 ("Ohio","OH",["Columbus","Cleveland","Cincinnati"],"lakefront cities, historic estates, and rolling countryside"),
 ("Oklahoma","OK",["Oklahoma City","Tulsa","Norman"],"prairie sunsets, historic venues, and wide-open country"),
 ("Oregon","OR",["Portland","Bend","Eugene"],"evergreen forests, coastline cliffs, and wine-country valleys"),
 ("Pennsylvania","PA",["Philadelphia","Pittsburgh","Lancaster"],"historic estates, rolling farmland, and city landmarks"),
 ("Rhode Island","RI",["Providence","Newport","Warwick"],"Newport mansions, coastal estates, and harbor views"),
 ("South Carolina","SC",["Charleston","Columbia","Greenville"],"Lowcountry charm, oak-lined avenues, and coastal estates"),
 ("South Dakota","SD",["Sioux Falls","Rapid City","the Black Hills"],"Black Hills backdrops, prairie skies, and rustic country"),
 ("Tennessee","TN",["Nashville","Memphis","Knoxville"],"Smoky Mountain views, music-city charm, and rolling estates"),
 ("Texas","TX",["Austin","Dallas","Houston"],"Hill Country vineyards, ranch sunsets, and city skylines"),
 ("Utah","UT",["Salt Lake City","Park City","Moab"],"red-rock canyons, mountain resorts, and alpine vistas"),
 ("Vermont","VT",["Burlington","Montpelier","Stowe"],"Green Mountain views, covered bridges, and autumn color"),
 ("Virginia","VA",["Richmond","Virginia Beach","Charlottesville"],"Blue Ridge vineyards, historic estates, and coastal shores"),
 ("Washington","WA",["Seattle","Spokane","Tacoma"],"evergreen forests, mountain backdrops, and Puget Sound views"),
 ("West Virginia","WV",["Charleston","Morgantown","Huntington"],"Appalachian mountains, river valleys, and country estates"),
 ("Wisconsin","WI",["Milwaukee","Madison","Green Bay"],"lakeside towns, rustic barns, and northern woods"),
 ("Wyoming","WY",["Cheyenne","Jackson","Casper"],"Teton backdrops, mountain ranches, and wide-open country"),
]
# (Individual state pages intentionally NOT generated — the nationwide hub below
# covers all 50 states in one strong page, avoiding thin doorway pages.)


# ============ NATIONWIDE HUB ============
STATE_TO_METRO = {
 "California":"los-angeles-wedding-videographer", "New York":"new-york-wedding-videographer",
 "Massachusetts":"boston-wedding-videographer", "Arizona":"phoenix-wedding-videographer",
 "Illinois":"chicago-wedding-videographer", "Florida":"miami-wedding-videographer",
 "Georgia":"atlanta-wedding-videographer", "Minnesota":"minneapolis-wedding-videographer",
 "Texas":"dallas-wedding-videographer", "Colorado":"denver-wedding-videographer", "Nevada":"las-vegas-wedding-videographer",
}
def _state_link(name):
    slug = STATE_TO_METRO.get(name)
    return ('<a href="/%s">%s</a>' % (slug, name)) if slug else ('<span>%s</span>' % name)
state_links = "".join(_state_link(s[0]) for s in STATES)
metro_links = "".join('<a href="/%s">%s</a>' % (m[0], m[1]) for m in METROS)
hub_review, hub_couple = next_review()
hub_body = """<!-- ===== HERO ===== -->
<section class="page-hero">
  <div class="page-hero__bg" aria-hidden="true">
    <img src="{HEROIMG}" alt="" onerror="this.onerror=null;this.src='{HERORAW}'">
  </div>
  <span class="page-hero__watermark" aria-hidden="true">A</span>
  <div class="wrap">
    <div class="eyebrow center rules reveal">Serving All 50 States</div>
    <h1 class="page-hero__title reveal d1">A Nationwide Wedding<br><em>Videographer &amp; Photographer</em></h1>
    <p class="page-hero__sub reveal d2">Based nationwide, with local teams in every market and <strong>no travel fees</strong> &mdash; wherever you're getting married, we'll be there.</p>
    <div style="margin-top:clamp(26px,4vw,36px)" class="reveal d3">
      <a href="/book/" class="btn btn--copper">Check Your Date <span class="arr">&#8599;</span></a>
    </div>
  </div>
</section>

<section class="sec">
  <div class="wrap" style="text-align:center;max-width:760px">
    <div class="sec__head reveal" style="margin-bottom:0">
      <div class="sec__roman">Coast to Coast</div>
      <h2 class="sec__title">Local everywhere &mdash; <em>no travel fees.</em></h2>
      <div class="rule"></div>
    </div>
    <p class="reveal d1" style="margin-top:26px;color:var(--ivory-dim);font-size:clamp(15px,1.7vw,17px);line-height:1.85">Most studios add a travel fee the moment your wedding is more than an hour away. We don't. We keep dedicated photography and film teams positioned across the country, so no matter which state you're marrying in, you get a local crew that already knows the venues and the light &mdash; at no extra travel cost. You also get complimentary access to your raw footage, and a <strong>$500 deposit</strong> reserves your date.</p>
  </div>
</section>

<section class="sec sec--tight">
  <div class="wrap" style="max-width:940px">
    <div style="text-align:center" class="reveal">
      <div class="eyebrow center rules">Featured Metros</div>
      <h2 class="sec__title" style="margin-top:14px;font-size:clamp(26px,3.6vw,44px)">Where We Shoot Most</h2>
    </div>
    <div class="loc-grid loc-grid--metro reveal d1">{METROLINKS}</div>
  </div>
</section>

<section class="sec sec--tight">
  <div class="wrap" style="max-width:940px">
    <div style="text-align:center" class="reveal">
      <div class="eyebrow center rules">All 50 States</div>
      <h2 class="sec__title" style="margin-top:14px;font-size:clamp(26px,3.6vw,44px)">Find Your State</h2>
      <p class="reveal d1" style="color:var(--ivory-dim);margin-top:18px;font-size:15px">Serving couples in every state in the country.</p>
    </div>
    <div class="loc-grid reveal d1">{STATELINKS}</div>
  </div>
</section>

<section class="cta-band cta-band--img" aria-label="Book Atavia Weddings">
  <img src="{CTAIMG}" alt="" loading="lazy" onerror="this.onerror=null;this.src='{CTARAW}'">
  <div class="wrap reveal">
    <span class="eyebrow center rules">Wherever You Are</span>
    <h2 class="cta-band__title" style="font-size:clamp(30px,4.6vw,58px);margin-top:20px">Let's capture your<br><em>wedding day.</em></h2>
    <a href="/book/" class="btn btn--copper" style="margin-top:26px">Reserve Your Date <span class="arr">&#8599;</span></a>
  </div>
</section>
"""
hub_body = (hub_body.replace("{HEROIMG}", esc(HERO)).replace("{HERORAW}", HERO)
            .replace("{CTAIMG}", esc(CTA)).replace("{CTARAW}", CTA)
            .replace("{METROLINKS}", metro_links).replace("{STATELINKS}", state_links))
HUB_SLUG = "nationwide-wedding-videographer"
(SRC / "pages" / (HUB_SLUG + ".html")).write_text(hub_body)
hub_canon = BASE + "/" + HUB_SLUG
manifest.append(dict(slug=HUB_SLUG, out=HUB_SLUG + ".html", nav="", tier="hub", footer_label="All 50 States",
    title="Nationwide Wedding Videographer &amp; Photographer | All 50 States | Atavia Weddings",
    desc="Atavia Weddings serves couples in all 50 states — local teams nationwide, no travel fees. Cinematic wedding films and timeless photography wherever you're getting married.",
    canon=hub_canon, schema_html=schema_for("United States", hub_canon, "Country")))

(SRC / "loc_pages.py").write_text("LOC_PAGES = " + repr(manifest) + "\n")
metros_n = sum(1 for m in manifest if m["tier"]=="metro")
states_n = sum(1 for m in manifest if m["tier"]=="state")
print("generated %d pages: %d metros, %d states, 1 hub" % (len(manifest), metros_n, states_n))
