"""patch_directory0930.py - JC-LAZO-DIR-0930-001
The vendor directory, as a premium brand would ship it. From the 2026-09-30
audit of metro, category and vendor pages. Idempotent, anchor-asserted;
rides into dist on the nightly build (build.py renders every page).

build.py
  - category cards finally get their fields: thumbUrl (cover, gallery[0],
    logo), bioSnippet, cardCity (locality), hasOffer - the template read them
    but nothing set them, so every card wore the category stock photo
  - ranking within a score tie: claimed first, then verified, then with a
    photo, then name - and the intro says so honestly ("baseline score of
    65" is gone)
  - the stub intro no longer repeats the distance-from-downtown sentence
    that the Where row and the Around block already carry; the Around block
    drops the downtown row, zero counts and the venues-within-10 row on a
    venue page
  - hotels: extended-stay / airport / motel names sink below real hotels
category.html
  - NEW TO LAZO never sits next to LAZO VERIFIED; the ranking copy is true
    whether or not anyone has reviews yet
vendor.html
  - JSON-LD: the second areaServed is gone (invalid duplicate key); the
    description says what is actually on the page
  - og:type / twitter:card / og:title / og:description duplicates removed
    (base.html emits them); og:image goes through base's block
  - the rail and the mobile bar tell the truth for an unclaimed vendor and
    use one label ("Check your date")
  - "Vendors who work here" is "Nearby vendors" and excludes venues
metro.html
  - "2162 vendors" -> "2,162 vendors"; the hero copy no longer claims a
    review-driven order that does not exist yet
base.html
  - og:type is a block; Find vendors goes to the finder on the home page,
    not hard-coded Phoenix; phones keep Find vendors + Wedding websites in
    the nav instead of hiding every link
lazo.css
  - the mobile CTA bar no longer covers the footer (padding on body, only
    on pages that have the bar)
  python generate\\patch_directory0930.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "generate" / "templates"


def edit(path, pairs, label):
    s = path.read_text(encoding="utf-8")
    n = 0
    for old, new in pairs:
        if new in s:
            continue  # already applied
        if s.count(old) != 1:
            raise SystemExit(f"ABORT {label}: anchor x{s.count(old)}: {old[:70]!r}")
        s = s.replace(old, new)
        n += 1
    path.write_text(s, encoding="utf-8", newline="\n")
    print(f"  {path.name}: {n} edit(s) applied ({label})")


# ---------------------------------------------------------------- build.py
B = ROOT / "generate" / "build.py"
edit(B, [
    # ranking within a tie + honest intro
    ("""            cvs.sort(key=lambda v: (-v["score"], -v["reviewCount"], v["name"].lower()))
""", """            # JC-LAZO-DIR-0930-001: within a score tie, the vendors who showed up
            # (claimed, verified, with a photo) come first - then the name.
            cvs.sort(key=lambda v: (-v["score"], -v["reviewCount"], not v.get("claimedBy"), not v.get("verified"),
                                    not (v.get("coverUrl") or v.get("gallery") or v.get("logoUrl")), v["name"].lower()))
            for v in cvs:
                v["thumbUrl"] = v.get("coverUrl") or ((v.get("gallery") or [None])[0]) or v.get("logoUrl") or ""
                _bio = re.sub(r"\\s+", " ", str(v.get("bio") or "")).strip()
                v["bioSnippet"] = (_bio[:137].rsplit(" ", 1)[0] + "\\u2026") if len(_bio) > 140 else _bio
                v["cardCity"] = _locality(v, metro) or ""
                _ann = v.get("announcement") or {}
                v["hasOffer"] = bool(isinstance(_ann, dict) and _ann.get("title"))
"""),
    ("""                         + ". Every ranking below comes from verified couple reviews \\u2014 never from ad spend. "
                         + "Vendors without verified reviews yet hold the community baseline score of 65 and are ordered alphabetically until couples weigh in.")
""", """                         + ". Verified couple reviews decide the order \\u2014 never ad spend. "
                         + "Until reviews arrive, vendors who have claimed and verified their profile come first, then everyone else by name.")
"""),
    # the stub intro: no third copy of the distance sentence
    ("""    _pc = v.get("ctx") or {}  # JC-LAZO-CONTENT-0922-001
    if _pc.get("centre_mi") is not None and _pc.get("venues_10"):
        _where = (f"{_pc['centre_mi']} miles {_pc['centre_dir']} of downtown {metro.get('name')}" if _pc.get("centre_dir")
                  else f"in central {metro.get('name')}")
        mids.append(f"{name} is {_where}, with {_pc['venues_10']} wedding venue{'s' if _pc['venues_10'] != 1 else ''} within ten miles.")
""", """    _pc = v.get("ctx") or {}  # JC-LAZO-CONTENT-0922-001
    # JC-LAZO-DIR-0930-001: the Where row and the Around block already say
    # where this is; a third copy read as filler (and Search Console agreed).
"""),
    # the Around block: no downtown row, no zeros, no venue count on a venue page
    ("""            if _pc.get("centre_mi") is not None:
                _around.append(("From downtown", (f"{_pc['centre_mi']} miles {_pc['centre_dir']} of central {metro['name']}" if _pc.get("centre_dir") else f"Central {metro['name']}")))
            if v.get("near_venues") and primary != "wedding-venues":
""", """            if v.get("near_venues") and primary != "wedding-venues":
"""),
    ("""            if _pc.get("venues_10"):
                _around.append(("Venues within 10 mi", f"{_pc['venues_10']:,} wedding venue{'s' if _pc['venues_10'] != 1 else ''}"))
            if _pc.get("peers_10") is not None and primary in BY_SLUG:
                _around.append((f"{BY_SLUG[primary]['label']} nearby", f"{v['near_3mi']} within 3 mi, {_pc['peers_10']} within 10"))
""", """            if _pc.get("venues_10") and primary != "wedding-venues":
                _around.append(("Venues within 10 mi", f"{_pc['venues_10']:,} wedding venue{'s' if _pc['venues_10'] != 1 else ''}"))
            if _pc.get("peers_10") and primary in BY_SLUG:
                _around.append((f"{BY_SLUG[primary]['label']} nearby",
                                (f"{v['near_3mi']} within 3 mi, " if v.get("near_3mi") else "") + f"{_pc['peers_10']} within 10"))
"""),
    # hotels: the airport extended-stay is not where the aunts want to stay
    ("""    cands.sort(key=lambda t: (t[0] + (2.0 if t[1].get("kind") == "motel" else 0.0)))
""", """    _lowend = re.compile(r"extended|airport|motel|econo|budget|super 8|days inn|travelodge|studio 6|suites only", re.I)
    cands.sort(key=lambda t: (t[0] + (2.0 if t[1].get("kind") == "motel" else 0.0) + (3.0 if _lowend.search(t[1].get("name", "")) else 0.0)))
"""),
], "cards, ranking, stub copy, hotels")

# ---------------------------------------------------------------- category.html
C = T / "category.html"
edit(C, [
    ("""          {% if not v.reviewCount %}<span class="ch-new">NEW TO LAZO</span>{% endif %}
""", """          {% if not v.reviewCount and not v.verified and not v.claimedBy %}<span class="ch-new">NEW TO LAZO</span>{% endif %}
"""),
    ("""  <p class="no-ads"><b>No sponsored results.</b> This is every
    {{ cat.singular|lower }} we list in {{ metro.name }}, ordered by what booked
    couples said &mdash; nobody can pay to move up.</p>
""", """  {%- set any_reviews = vendors|selectattr('reviewCount')|list|length > 0 %}
  <p class="no-ads"><b>No sponsored results.</b> This is every
    {{ cat.singular|lower }} we list in {{ metro.name }}{% if any_reviews %}, ordered by what booked
    couples said{% else %} &mdash; verified vendors first, then by name{% endif %}. Nobody can pay to move up.</p>
"""),
    ("""    <p class="hero-sub">Ranked by verified reputation &mdash; never by who paid. <span class="rank-note">New vendors start at the community baseline until verified reviews arrive.</span></p>
""", """    <p class="hero-sub">Ranked by verified reputation &mdash; never by who paid. <span class="rank-note">Verified vendors first; reviews from couples who booked move the rest.</span></p>
"""),
], "badges, honest ranking copy")

# ---------------------------------------------------------------- vendor.html
V = T / "vendor.html"
vs = V.read_text(encoding="utf-8")
vs2 = vs.replace(',"areaServed":"{{ metro.display }}"', "", 1)
edit(V, [
    (vs, vs2) if vs != vs2 else ("__noop__", "__noop__"),
] if vs != vs2 else [], "schema areaServed")
edit(V, [
    ("""{% block desc %}{{ v.name }}, {{ cat.singular|lower }} in {{ metro.display }}. Verified reviews and Lazo Score on the wedding marketplace where rankings are never for sale.{% endblock %}
""", """{% block desc %}{{ v.name }}, {{ cat.singular|lower }} {% if v.locality %}in {{ v.locality }}, {{ metro.name }}{% else %}in {{ metro.display }}{% endif %}. {% if v.reviewCount %}{{ v.reviewCount }} verified review{{ '' if v.reviewCount == 1 else 's' }} from couples who booked, plus prices and availability.{% elif v.bio %}{{ v.bio|striptags|truncate(120) }}{% else %}Prices, availability and reviews from couples who booked, on the marketplace where rankings are never for sale.{% endif %}{% endblock %}
"""),
    ("""<meta property="og:type" content="business.business">
<meta property="og:title" content="{{ v.name }} &mdash; {{ cat.singular }} in {{ metro.display }}">
<meta property="og:description" content="{{ (v.bio or v.intro or (v.name ~ ', ' ~ cat.singular|lower ~ ' in ' ~ metro.display ~ '. Verified reviews and Lazo Score.'))|striptags|truncate(180) }}">
<meta property="og:url" content="{{ base }}/{{ metro.id }}/{{ cat.slug }}/{{ v.slug }}/">
{% if v.coverUrl or v.gallery %}<meta property="og:image" content="{{ v.coverUrl or v.gallery[0] }}">{% endif %}
<meta name="twitter:card" content="summary_large_image">
""", """<meta property="og:url" content="{{ base }}/{{ metro.id }}/{{ cat.slug }}/{{ v.slug }}/">
"""),
    ("""{% block canonical %}{% if v.homeCanonical %}{{ v.homeCanonical }}{% else %}{{ base }}/{{ metro.id }}/{{ cat.slug }}/{{ v.slug }}/{% endif %}{% endblock %}
""", """{% block canonical %}{% if v.homeCanonical %}{{ v.homeCanonical }}{% else %}{{ base }}/{{ metro.id }}/{{ cat.slug }}/{{ v.slug }}/{% endif %}{% endblock %}
{% block ogtype %}business.business{% endblock %}
{% block ogimage %}{% if v.coverUrl or v.gallery %}{{ v.coverUrl or v.gallery[0] }}{% else %}{{ base }}/assets/photos/{{ cat.slug }}.jpg{% endif %}{% endblock %}
"""),
    # the rail: honest for an unclaimed vendor
    ("""        <p class="vp-card-h">Is your date open?</p>
        <p class="vp-card-p">Ask {{ v.name }} directly. Verified couples inquire free &mdash; and are never charged for your message.</p>
""", """        {%- if v.claimedBy %}
        <p class="vp-card-h">Is your date open?</p>
        <p class="vp-card-p">Ask {{ v.name }} directly. Verified couples inquire free &mdash; and are never charged for your message.</p>
        {%- else %}
        <p class="vp-card-h">Want to check their date?</p>
        <p class="vp-card-p">{{ v.name }} hasn’t joined Lazo yet. Send your date and we’ll reach out on your behalf{% if v.phone %} &mdash; or call {{ v.phone }}{% endif %}.</p>
        {%- endif %}
"""),
    ("""  <a class="btn-gold" href="https://app.meetlazo.com/?vendor={{ v.placeId }}">Check availability</a>
</div>
""", """  <a class="btn-gold" href="https://app.meetlazo.com/?vendor={{ v.placeId }}">Check your date</a>
</div>
"""),
    ("""      {% if v.near_vendors %}
      <h2 class="vp-h2">Vendors who work here</h2>
      <div class="geo-list">
        {% for nv in v.near_vendors %}<a href="/{{ metro.id }}/{{ nv.cat }}/{{ nv.slug }}/">{{ nv.name }}<span>{{ nv.mi }} mi</span></a>{% endfor %}
      </div>
      {% endif %}
""", """      {%- set near_pros = (v.near_vendors or [])|rejectattr('cat', 'equalto', 'wedding-venues')|list %}
      {% if near_pros %}
      <h2 class="vp-h2">Nearby vendors</h2>
      <div class="geo-list">
        {% for nv in near_pros %}<a href="/{{ metro.id }}/{{ nv.cat }}/{{ nv.slug }}/">{{ nv.name }}<span>{{ nv.mi }} mi</span></a>{% endfor %}
      </div>
      {% endif %}
"""),
], "meta, og blocks, rail copy, nearby vendors")

# ---------------------------------------------------------------- metro.html
M = T / "metro.html"
edit(M, [
    ("""    <p class="hero-sub">Every wedding professional in {{ metro.name }} we could find, in the order couples who booked them put them. Never in the order anyone paid for.</p>
    <div class="mt-facts"><span><b>{{ total }}</b>vendors</span>""", """    <p class="hero-sub">Every wedding professional in {{ metro.name }} we could find. Verified vendors first, then reviews from couples who booked them &mdash; never who paid.</p>
    <div class="mt-facts"><span><b>{{ '{:,}'.format(total) }}</b>vendors</span>"""),
], "formatted total, honest hero copy")

# ---------------------------------------------------------------- base.html
Bh = T / "base.html"
edit(Bh, [
    ("""<meta property="og:type" content="website">
""", """<meta property="og:type" content="{% block ogtype %}website{% endblock %}">
"""),
    ("""    <a href="/phoenix/"{% if self.nav_key() == 'find' %} class="on"{% endif %}>Find vendors</a>
""", """    <a href="/#find"{% if self.nav_key() == 'find' %} class="on"{% endif %}>Find vendors</a>
"""),
    ("""  .site-nav a:not(.nav-cta){display:none}
""", """  .site-nav a:not(.nav-cta){font-size:13px}
  .site-nav a:nth-child(2),.site-nav a:nth-child(4){display:none}
"""),
], "og block, nav")

# ---------------------------------------------------------------- lazo.css
S = ROOT / "generate" / "static" / "lazo.css"
edit(S, [
    ("""  main .vp{padding:14px 16px 96px}
""", """  main .vp{padding:14px 16px 24px}
"""),
    ("""@media (max-width:720px){
  .v-ctabar{display:flex;""", """@media (max-width:720px){
  body:has(.v-ctabar){padding-bottom:96px}
  .v-ctabar{display:flex;"""),
], "mobile CTA bar padding")

# the home finder gets the id the nav points at
H = T / "home.html"
edit(H, [
    ("""    <form class="finder" onsubmit=""", """    <form class="finder" id="find" onsubmit="""),
], "finder id")
print("done")
