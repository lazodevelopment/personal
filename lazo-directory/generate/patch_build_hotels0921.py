"""patch_build_hotels0921.py - JC-LAZO-HOTELS-0921-002
"Hotels near this venue" on every wedding-venue page, from data/hotels_osm.json
(seed/hotels_osm.py, OpenStreetMap). build.py buckets the hotels into a 0.1
degree grid once, then gives each venue with coordinates its six nearest named
hotels within 15 mi (hotels first, motels only if there is nothing closer).
vendor.html prints them as a section with distance, address, website and a
directions link, plus an ItemList of LodgingBusiness in JSON-LD and the ODbL
credit. No data file = no section, so the build never depends on it.
Idempotent (asserts on anchors, refuses to re-apply).

  python generate\\patch_build_hotels0921.py
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def rep(s, old, new, label, count=1):
    n = s.count(old)
    if n != count:
        raise SystemExit(f"{label}: anchor found {n}x, wanted {count}: {old[:70]!r}")
    return s.replace(old, new)

# ---------------------------------------------------------------- build.py
bp = ROOT / "generate" / "build.py"; b = bp.read_text(encoding="utf-8")
if "HOTELS-0921-002" in b:
    print("build.py: already patched")
else:
    helpers = '''
# JC-LAZO-HOTELS-0921-002: hotels near each venue, from data/hotels_osm.json
# (OpenStreetMap via seed/hotels_osm.py). Bucketed once into a 0.1-degree grid so
# 17,000 venues x 60,000 hotels stays a few seconds, not minutes.
_HOTELS = None
def _hotel_grid():
    global _HOTELS
    if _HOTELS is not None:
        return _HOTELS
    _HOTELS = {}
    f = ROOT / "data" / "hotels_osm.json"
    if not f.exists():
        print("[build] hotels: data/hotels_osm.json missing, venue pages get no hotel section")
        return _HOTELS
    import json as _hj
    rows = _hj.loads(f.read_text(encoding="utf-8"))
    for h in rows:
        _HOTELS.setdefault((int(h["lat"] * 10), int(h["lng"] * 10)), []).append(h)
    print(f"[build] hotels: {len(rows):,} from OpenStreetMap")
    return _HOTELS

def _hotels_near(v, n=6, max_mi=15.0):
    if v.get("lat") is None or v.get("lng") is None:
        return []
    grid = _hotel_grid()
    if not grid:
        return []
    a = {"lat": v["lat"], "lng": v["lng"]}
    ky, kx = int(v["lat"] * 10), int(v["lng"] * 10)
    cands = []
    for dy in (-2, -1, 0, 1, 2):
        for dx in (-2, -1, 0, 1, 2):
            for h in grid.get((ky + dy, kx + dx), ()):
                d = _dist_mi(a, h)
                if d is not None and d <= max_mi and d >= 0.02:
                    cands.append((d, h))
    cands.sort(key=lambda t: (t[0] + (2.0 if t[1].get("kind") == "motel" else 0.0)))
    out, seen = [], set()
    for d, h in cands:
        key = h["name"].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(dict(h, miles=round(d, 1)))
        if len(out) >= n:
            break
    return out

'''
    b = rep(b, "\ndef build(vendors: list[dict]):\n", helpers + "\ndef build(vendors: list[dict]):\n", "helpers")
    b = rep(b, "                    t_vendor.render(metro=metro, cat=cat, v=v, base=BASE_URL,\n",
            "                    t_vendor.render(metro=metro, cat=cat, v=v, base=BASE_URL,\n"
            "                                    hotels=(_hotels_near(v) if cat[\"slug\"] == \"wedding-venues\" else []),\n", "vendor render")
    bp.write_text(b, encoding="utf-8", newline="\n"); print("build.py: hotels near venues")

# ---------------------------------------------------------------- vendor.html
vp = ROOT / "generate" / "templates" / "vendor.html"; v = vp.read_text(encoding="utf-8")
if "lz-hotels" in v:
    print("vendor.html: already patched")
else:
    jsonld = '''{% if hotels %}
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"ItemList","name":{{ ("Hotels near " ~ v.name)|tojson }},"itemListElement":[
{%- for h in hotels -%}
{"@type":"ListItem","position":{{ loop.index }},"item":{"@type":"LodgingBusiness","name":{{ h.name|tojson }}{% if h.addr or h.city %},"address":{"@type":"PostalAddress"{% if h.addr %},"streetAddress":{{ h.addr|tojson }}{% endif %}{% if h.city %},"addressLocality":{{ h.city|tojson }}{% endif %}}{% endif %},"geo":{"@type":"GeoCoordinates","latitude":{{ h.lat }},"longitude":{{ h.lng }}}{% if h.site %},"url":{{ h.site|tojson }}{% endif %}}}{{ "," if not loop.last }}
{%- endfor -%}
]}
</script>
{% endif %}
{% endblock %}
{% block main %}'''
    v = rep(v, "{% endblock %}\n{% block main %}", jsonld, "jsonld")
    section = '''
      <!-- lz-hotels -->
      {% if hotels %}
      <div class="v-hotels" id="hotels">
        <h2 class="vp-h2">Hotels near {{ v.name }}</h2>
        <p class="v-hotels-sub">The closest places for out-of-town guests to stay{% if v.locality %} around {{ v.locality }}{% endif %}, nearest first. Ask the venue which ones offer a room block.</p>
        <ul class="v-hotel-list">
          {%- for h in hotels %}
          <li><div><b>{{ h.name }}</b>{% if h.stars %} <span class="v-hotel-stars">{{ h.stars }}-star</span>{% endif %}<span class="v-hotel-meta">{{ h.miles }} mi{% if h.addr %} &middot; {{ h.addr }}{% endif %}{% if h.city %}, {{ h.city }}{% endif %}</span></div>
            <div class="v-hotel-links">{% if h.site %}<a href="{{ h.site }}" rel="nofollow noopener" target="_blank">Website</a>{% endif %}<a href="https://www.google.com/maps/dir/?api=1&amp;origin={{ v.lat }},{{ v.lng }}&amp;destination={{ h.lat }},{{ h.lng }}" rel="nofollow noopener" target="_blank">Directions</a></div></li>
          {%- endfor %}
        </ul>
        <p class="v-hotels-credit">Hotel data &copy; <a href="https://www.openstreetmap.org/copyright" rel="noopener" target="_blank">OpenStreetMap contributors</a>. Distances are straight-line from the venue.</p>
      </div>
      {% endif %}
      <!-- /lz-hotels -->
'''
    v = rep(v, '''      <div id="hy-attrs-wrap" {% if not chips.list %}style="display:none"{% endif %}>''',
            section + '''      <div id="hy-attrs-wrap" {% if not chips.list %}style="display:none"{% endif %}>''', "section anchor")
    css = '''
/* JC-LAZO-HOTELS-0921-002: hotels near the venue */
.v-hotels{margin-top:34px}
.v-hotels-sub{color:var(--muted);font-size:15px;margin:6px 0 14px}
.v-hotel-list{list-style:none;margin:0;padding:0;border-top:1px solid var(--gold-line)}
.v-hotel-list li{display:flex;justify-content:space-between;gap:18px;align-items:baseline;padding:12px 0;border-bottom:1px solid var(--gold-line);font-size:15px}
.v-hotel-list b{font-weight:600;color:var(--ink)}
.v-hotel-stars{font-size:12px;color:var(--gold-ink);font-weight:700;margin-left:8px}
.v-hotel-meta{display:block;color:var(--muted);font-size:13.5px;margin-top:2px}
.v-hotel-links{display:flex;gap:14px;white-space:nowrap;font-size:13.5px}
.v-hotel-links a{color:var(--plum);font-weight:600;text-decoration:none;border-bottom:1px solid var(--gold)}
.v-hotels-credit{font-size:12px;color:var(--muted);margin:12px 0 0}
@media(max-width:640px){.v-hotel-list li{flex-direction:column;gap:6px}}
'''
    vp.write_text(v, encoding="utf-8", newline="\n"); print("vendor.html: hotels section + JSON-LD")
    # the vendor page's CSS lives in the site stylesheet
    cp = ROOT / "generate" / "static" / "lazo.css"; c = cp.read_text(encoding="utf-8")
    if "HOTELS-0921-002" not in c:
        cp.write_text(c.rstrip("\n") + "\n" + css, encoding="utf-8", newline="\n"); print("lazo.css: hotel section styles")
