r"""local_facts.py - JC-LAZO-LOCAL-1017-001
The local sections on vendor pages, as facts and tables, never city-swapped copy. Every block is computed from data
we hold and is left out of the page when that data is missing:

  months    NOAA 1991-2020 monthly climate normals (generate/data/local/weather.json, fetched once by local_data.py)
            + golden hour and sunset on the 15th of each month (solar.py, computed, no network)
  travel    nearest airports with scheduled service (generate/data/local/airports.json) and the nearest big cities;
            straight-line miles, drive times are labelled estimates
  prices    metroStats/{metro}__{cat}.priceFrom from nightlyVendorStats (needs 5+ priced vendors in the bucket)
  demand    the months couples in the metro marry, from couples.weddingDate (only with 25+ couples; never any one couple)
  spots     photo spots near the metro centre (Google Places, data/local/photo_spots.json, fetched by
            local_data.py photospots - PAID, kept 30 days at most, then left out until refreshed)
  recs      venues whose own preferred-vendor page links to this vendor's website (generate/data/preferred/harvest.json)

build.py calls install(env) at import (template global local_for) and attach(by_metro, db) after build_content.
"""
import calendar, collections, datetime as dt, json, math
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

import solar

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "generate" / "data"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
# the 50 largest US metro areas, as Lazo metro ids (drive-distance targets)
BIG = set("""new-york-city los-angeles chicago dallas-fort-worth houston washington-dc philadelphia miami atlanta boston
phoenix san-francisco-bay detroit seattle minneapolis san-diego tampa denver baltimore st-louis orlando charlotte
san-antonio portland sacramento pittsburgh austin las-vegas cincinnati kansas-city columbus indianapolis cleveland
nashville virginia-beach providence jacksonville milwaukee raleigh-durham oklahoma-city memphis richmond louisville
new-orleans salt-lake-city hartford-new-haven buffalo birmingham""".split())
MIN_COUPLES = 25      # demand is shown only above this many couples in a metro
MAX_SOURCES = 30      # a site linked by more venues than this is a chain or a directory, not a recommendation

_PRICES, _DEMAND = {}, {}


def _mi(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(h))


def _drive(miles, factor=1.25, mph=50):
    """A labelled estimate: straight-line miles x a road factor at an average speed."""
    mins = miles * factor / mph * 60
    if mins < 60:
        return f"{max(5, int(round(mins / 5.0)) * 5)} min"
    h, m = divmod(int(round(mins / 10.0)) * 10, 60)
    return f"{h} hr" + (f" {m} min" if m else "")


@lru_cache(maxsize=1)
def _weather():
    p = DATA / "local" / "weather.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


@lru_cache(maxsize=1)
def _airports():
    p = DATA / "local" / "airports.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


@lru_cache(maxsize=1)
def _spots():
    p = DATA / "local" / "photo_spots.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


@lru_cache(maxsize=1)
def _metros():
    from config.metros import METROS
    return {m["id"]: m for m in METROS}


@lru_cache(maxsize=None)
def for_metro(metro_id):
    """Everything metro-level, computed once per metro per build."""
    m = _metros().get(metro_id)
    if not m:
        return {}
    c = m["center"]
    out = {}
    # month by month: weather normals + light
    w = _weather().get(metro_id)
    year = dt.date.today().year
    rows = []
    for i in range(12):
        r = {"m": MONTHS[i], "full": calendar.month_name[i + 1], "now": i + 1 == dt.date.today().month}
        if w:
            mo = w["months"][i]
            r.update(hi=mo["hi"], lo=mo["lo"], rain=int(round(mo["wet"] / calendar.monthrange(year, i + 1)[1] * 100)))
        try:
            info = solar.day_info(dt.date(year, i + 1, 15), c[0], c[1], m["state"])
            if info.get("sunset") and info.get("golden_start"):
                r.update(golden=solar.hhmm(info["golden_start"]), sunset=solar.hhmm(info["sunset"]))
        except Exception:  # noqa: BLE001
            pass
        rows.append(r)
    if w or any("sunset" in r for r in rows):
        out["months"] = rows
        out["has_weather"] = bool(w)
        out["has_sun"] = any("sunset" in r for r in rows)
        if w:
            out["station"] = {"name": w["name"].rsplit(",", 1)[0].title().replace(" Ap", " Airport").replace(" Intl", " International").replace(" Fld", " Field").replace(" Rgnl", " Regional").replace(" Muni", " Municipal"), "mi": w["mi"]}
            warm = [r for r in rows if 65 <= r["hi"] <= 85]
            out["mild"] = [r["full"] for r in warm]
            dry = sorted(rows, key=lambda r: r["rain"])[:3]
            out["driest"] = [r["full"] for r in sorted(dry, key=lambda r: MONTHS.index(r["m"]))]
    # travel
    aps = sorted(((_mi(c, (a["lat"], a["lng"])), a) for a in _airports()), key=lambda x: x[0])
    pick = [x for x in aps if x[0] <= 120][:3]
    if pick and not any(a["big"] for _, a in pick):
        big = next((x for x in aps if x[1]["big"] and x[0] <= 250), None)
        if big:
            pick = pick[:2] + [big]
    if pick:
        out["airports"] = [{"code": a["code"], "name": a["name"], "mi": int(round(d)), "drive": _drive(d)} for d, a in pick]
    cities = sorted(((_mi(c, mm["center"]), mm) for mid, mm in _metros().items() if mid in BIG and mid != metro_id),
                    key=lambda x: x[0])
    near = [{"id": mm["id"], "name": mm["name"], "mi": int(round(d)), "drive": _drive(d, 1.2, 58)} for d, mm in cities if d <= 320][:4]
    if near:
        out["cities"] = near
    # photo spots (Google Places, JC-LAZO-LOCAL-1017-003): Google allows keeping this content 30 days, so older is dropped
    sp = _spots().get(metro_id)
    if sp and sp.get("spots"):
        try:
            age = (dt.date.today() - dt.date.fromisoformat(sp["fetched"])).days
        except (KeyError, ValueError):
            age = 999
        if age <= 30:
            rows = []
            for x in sp["spots"][:8]:
                parts = [q.strip() for q in (x.get("addr") or "").split(",")]
                area = parts[-3] if len(parts) >= 3 else (parts[0] if parts else "")
                rows.append({"name": x["name"], "area": area, "mi": round(_mi(c, (x["lat"], x["lng"])), 1), "maps": x.get("maps") or "",
                             "kind": (x.get("type") or "").replace("_", " ")})
            out["spots"] = sorted(rows, key=lambda r: r["mi"])
            out["spots_month"] = dt.date.fromisoformat(sp["fetched"]).strftime("%B %Y")
    return out


def prices_for(metro_id, cat_slug):
    return _PRICES.get(f"{metro_id}__{cat_slug}")


def demand_for(metro_id):
    return _DEMAND.get(metro_id)


def install(env):
    env.globals["local_for"] = for_metro
    env.globals["local_prices"] = prices_for
    env.globals["local_demand"] = demand_for


def _domain(u):
    try:
        h = urlparse(u if "://" in u else "https://" + u).hostname or ""
    except ValueError:
        return ""
    return h.lower().removeprefix("www.")


def attach(by_metro, db=None):
    """Per-vendor: the venues that recommend them. Metro-level: prices and demand from Firestore (aggregates only)."""
    # recommendations
    hp = DATA / "preferred" / "harvest.json"
    cands = json.loads(hp.read_text(encoding="utf-8")).get("cands", {}) if hp.exists() else {}
    venues = {}
    for mid, vs in by_metro.items():
        for v in vs:
            if "wedding-venues" in (v.get("categories") or []) and not v.get("travelFrom"):
                venues[v["placeId"]] = {"name": v["name"], "path": f"/{mid}/wedding-venues/{v['slug']}/", "metro": mid}
    n_recs = 0
    for vs in by_metro.values():
        for v in vs:
            d = _domain(v.get("website") or "")
            c = cands.get(d) if d else None
            if not c:
                continue
            src = [s for s in (c.get("sources") or []) if s != v.get("placeId")]
            if not src or len(src) > MAX_SOURCES:
                continue
            recs, seen = [], set()
            for s in src:
                ven = venues.get(s)
                if ven and ven["path"] not in seen and ven["name"] != v.get("name"):
                    seen.add(ven["path"]); recs.append(ven)
            if recs:
                v["recommended_by"] = sorted(recs, key=lambda r: (r["metro"] != v.get("metroId"), r["name"]))[:8]
                n_recs += 1
    print(f"[local] recommended-by lists on {n_recs:,} vendors")
    if db is None:
        return
    # prices: metroStats.priceFrom (written only where 5+ vendors are priced)
    try:
        for d in db.collection("metroStats").stream():
            pf = (d.to_dict() or {}).get("priceFrom")
            if pf and pf.get("p25") and pf.get("p75") and (pf.get("sampled") or 0) >= 5:
                _PRICES[d.id] = {"lo": int(pf["p25"]), "hi": int(pf["p75"]), "mid": int(pf.get("p50") or 0), "n": int(pf["sampled"])}
    except Exception as e:  # noqa: BLE001
        print(f"[local] metroStats read failed: {e}")
    # demand: months couples marry, per metro, only with enough couples that no one is identifiable
    try:
        per = collections.defaultdict(list)
        for d in db.collection("couples").select(["metroId", "weddingDate"]).stream():
            x = d.to_dict() or {}
            wd = x.get("weddingDate")
            if not x.get("metroId") or not wd:
                continue
            try:
                month = wd.month if hasattr(wd, "month") else int(str(wd)[5:7])
            except (ValueError, TypeError):
                continue
            per[x["metroId"]].append(month)
        for mid, months in per.items():
            if len(months) >= MIN_COUPLES:
                cnt = collections.Counter(months)
                top = [(MONTHS[mo - 1], round(n / len(months) * 100)) for mo, n in cnt.most_common(3)]
                _DEMAND[mid] = {"n": len(months), "top": top}
    except Exception as e:  # noqa: BLE001
        print(f"[local] couples read failed: {e}")
    print(f"[local] price ranges for {len(_PRICES)} metro/category buckets, demand for {len(_DEMAND)} metros")
