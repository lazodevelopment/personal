"""patch_build_content0922.py - JC-LAZO-CONTENT-0922-001
The content pass for stub vendor pages. Search Console's rejected-URL exports
(2026-09-22) are 99% vendor pages across every category: pages that are not
short (~400 words of main content) but say the same things with a different
name on top (62% shared vocabulary between two random pages). This pass adds
facts that differ page to page, all computed from data already in the build:

  around block   miles and compass direction from downtown; the nearest venue
                 by name; wedding venues within ten miles; same-category peers
                 within three and ten miles; hotels within five miles (from
                 data/hotels_osm.json); the communities the business sits among
                 (the localities of every vendor within six miles, most common
                 first) - which also feeds LocalBusiness.areaServed in JSON-LD
  intro          one more candidate sentence built from those numbers
  related list   the nearest same-category peers now show their distance

Nothing here is prose spun from a template; every value is a number or a name
that only this page has. Idempotent (asserts on anchors, refuses to re-apply).

  python generate\\patch_build_content0922.py
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
if "CONTENT-0922-001" in b:
    print("build.py: already patched")
else:
    helpers = '''
# JC-LAZO-CONTENT-0922-001: per-page facts for the stub content pass.
_COMPASS = ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"]
def _compass(a, b):
    """Direction from a to b as a word."""
    la1, la2 = math.radians(a["lat"]), math.radians(b["lat"])
    dlo = math.radians(b["lng"] - a["lng"])
    x = math.sin(dlo) * math.cos(la2)
    y = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(dlo)
    brg = (math.degrees(math.atan2(x, y)) + 360) % 360
    return _COMPASS[int((brg + 22.5) // 45) % 8]

def _grid_index(rows, cell=0.1):
    g = {}
    for r in rows:
        if r.get("lat") is None or r.get("lng") is None:
            continue
        g.setdefault((int(r["lat"] / cell), int(r["lng"] / cell)), []).append(r)
    return g

def _grid_near(grid, v, max_mi, cell=0.1):
    """(row, miles) for every row in grid within max_mi of v (cells around v)."""
    if v.get("lat") is None or v.get("lng") is None:
        return []
    ky, kx = int(v["lat"] / cell), int(v["lng"] / cell)
    span = int(max_mi / 6.9 / cell) + 1  # ~6.9 mi per 0.1 degree of latitude
    out = []
    for dy in range(-span, span + 1):
        for dx in range(-span, span + 1):
            for r in grid.get((ky + dy, kx + dx), ()):
                d = _dist_mi(v, r)
                if d is not None and d <= max_mi:
                    out.append((r, d))
    return out

def _place_context(v, metro, vgrid, cat_slug):
    """The facts only this page has. Returns a dict; empty when no coordinates."""
    if v.get("lat") is None or v.get("lng") is None:
        return {}
    centre = {"lat": metro["center"][0], "lng": metro["center"][1]}
    d_centre = _dist_mi(v, centre)
    near = _grid_near(vgrid, v, 10.0)
    venues_10 = sum(1 for r, d in near if "wedding-venues" in r["categories"] and r["placeId"] != v["placeId"])
    peers_10 = sum(1 for r, d in near if cat_slug in r["categories"] and r["placeId"] != v["placeId"])
    own = _locality(v, metro)
    comm = {}
    for r, d in near:
        if d <= 6.0 and r["placeId"] != v["placeId"]:
            loc = _locality(r, metro)
            if loc and loc != own and loc != metro["name"]:
                comm[loc] = comm.get(loc, 0) + 1
    communities = [k for k, _ in sorted(comm.items(), key=lambda t: -t[1])[:4]]
    hotels_5 = 0
    hg = _hotel_grid()
    if hg:
        hotels_5 = sum(1 for _h, d in _grid_near(hg, v, 5.0))
    return {"centre_mi": round(d_centre) if d_centre is not None else None,
            "centre_dir": _compass(centre, v) if d_centre is not None and d_centre >= 1.5 else "",
            "venues_10": venues_10, "peers_10": peers_10, "communities": communities, "hotels_5": hotels_5}

'''
    b = rep(b, "\ndef compose_intro(v, cat, metro, near_venues):\n", helpers + "\ndef compose_intro(v, cat, metro, near_venues):\n", "helpers")
    # one more intro candidate built from the numbers
    b = rep(b, '''    if cat["slug"] == "wedding-venues" and near_venues:
        vn = ", ".join(x["name"] for x in near_venues[:2])
        mids.append(f"Couples touring this venue often compare it with nearby options such as {vn}.")
''', '''    if cat["slug"] == "wedding-venues" and near_venues:
        vn = ", ".join(x["name"] for x in near_venues[:2])
        mids.append(f"Couples touring this venue often compare it with nearby options such as {vn}.")
    _pc = v.get("ctx") or {}  # JC-LAZO-CONTENT-0922-001
    if _pc.get("centre_mi") is not None and _pc.get("venues_10"):
        _where = (f"{_pc['centre_mi']} miles {_pc['centre_dir']} of downtown {metro.get('name')}" if _pc.get("centre_dir")
                  else f"in central {metro.get('name')}")
        mids.append(f"{name} is {_where}, with {_pc['venues_10']} wedding venue{'s' if _pc['venues_10'] != 1 else ''} within ten miles.")
''', "intro fact")
    # compute the context in the first per-metro loop, before the intro is composed
    b = rep(b, '''        venues = [v for v in vs if "wedding-venues" in v["categories"] and v.get("lat")]
        for v in vs:
            pool = [x for x in venues if x["placeId"] != v["placeId"]]
''', '''        venues = [v for v in vs if "wedding-venues" in v["categories"] and v.get("lat")]
        _vgrid = _grid_index(vs)  # JC-LAZO-CONTENT-0922-001
        for v in vs:
            v["ctx"] = _place_context(v, metro, _vgrid, v["categories"][0] if v.get("categories") else "")
            pool = [x for x in venues if x["placeId"] != v["placeId"]]
''', "context compute")
    # related peers carry their distance
    b = rep(b, '''            v["related"] = [{"name": x["name"], "slug": x["slug"], "cat": primary} for x, _ in near_peers]''',
            '''            v["related"] = [{"name": x["name"], "slug": x["slug"], "cat": primary, "mi": round(_d, 1)} for x, _d in near_peers]  # JC-LAZO-CONTENT-0922-001''', "related mi")
    # the around block + areaServed, after locality is known
    b = rep(b, '''            v["near_3mi"] = sum(1 for d in (_dist_mi(v, x) for x in peers)
                                if d is not None and d <= 3)
''', '''            v["near_3mi"] = sum(1 for d in (_dist_mi(v, x) for x in peers)
                                if d is not None and d <= 3)
            # JC-LAZO-CONTENT-0922-001: the around block, facts only this page has
            _pc = v.get("ctx") or {}
            _around = []
            if _pc.get("centre_mi") is not None:
                _around.append(("From downtown", (f"{_pc['centre_mi']} miles {_pc['centre_dir']} of central {metro['name']}" if _pc.get("centre_dir") else f"Central {metro['name']}")))
            if v.get("near_venues") and primary != "wedding-venues":
                _nv = v["near_venues"][0]
                _around.append(("Nearest venue", f"{_nv['name']}, {_nv['mi']} mi"))
            if _pc.get("venues_10"):
                _around.append(("Venues within 10 mi", f"{_pc['venues_10']:,} wedding venue{'s' if _pc['venues_10'] != 1 else ''}"))
            if _pc.get("peers_10") is not None and primary in BY_SLUG:
                _around.append((f"{BY_SLUG[primary]['label']} nearby", f"{v['near_3mi']} within 3 mi, {_pc['peers_10']} within 10"))
            if _pc.get("hotels_5"):
                _around.append(("Guest hotels", f"{_pc['hotels_5']} within 5 mi"))
            if _pc.get("communities"):
                _around.append(("Communities served", ", ".join(_pc["communities"])))
            v["around"] = _around
            v["areaServed"] = [v["locality"]] + [c for c in _pc.get("communities", []) if c != v["locality"]] if v.get("locality") else []
''', "around block")
    bp.write_text(b, encoding="utf-8", newline="\n"); print("build.py: content pass (around block, intro fact, related distances, areaServed)")

# ---------------------------------------------------------------- vendor.html
vp = ROOT / "generate" / "templates" / "vendor.html"; v = vp.read_text(encoding="utf-8")
if "lz-around" in v:
    print("vendor.html: already patched")
else:
    v = rep(v, '''"name":{{ v.name|tojson }},"address":''',
            '''"name":{{ v.name|tojson }},{% if v.areaServed %}"areaServed":[{% for a in v.areaServed %}{"@type":"Place","name":{{ a|tojson }}}{{ "," if not loop.last }}{% endfor %}],{% endif %}"address":''', "areaServed")
    v = rep(v, '''      </dl>

      <div id="hy-serves-wrap" {% if not v.serviceMetroNames %}style="display:none"{% endif %}>''',
            '''      </dl>

      <!-- lz-around -->
      {% if v.around %}
      <h2 class="vp-h2">Around {{ v.locality or metro.name }}</h2>
      <dl class="v-facts v-around">
        {%- for label, value in v.around %}
        <div><dt>{{ label }}</dt><dd>{{ value }}</dd></div>
        {%- endfor %}
      </dl>
      <p class="geo-note">Distances are straight-line from {{ v.name }}; counts come from the businesses and venues Lazo lists around {{ metro.name }}.</p>
      {% endif %}
      <!-- /lz-around -->

      <div id="hy-serves-wrap" {% if not v.serviceMetroNames %}style="display:none"{% endif %}>''', "around section")
    v = rep(v, '''      <div class="geo-list geo-plain">
        {% for r in v.related %}<a href="/{{ metro.id }}/{{ r.cat }}/{{ r.slug }}/">{{ r.name }}</a>{% endfor %}
      </div>''',
            '''      <div class="geo-list">
        {% for r in v.related %}<a href="/{{ metro.id }}/{{ r.cat }}/{{ r.slug }}/">{{ r.name }}{% if r.mi is defined %}<span>{{ r.mi }} mi</span>{% endif %}</a>{% endfor %}
      </div>''', "related distances")
    vp.write_text(v, encoding="utf-8", newline="\n"); print("vendor.html: around block, areaServed, related distances")
