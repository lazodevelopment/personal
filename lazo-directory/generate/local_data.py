r"""local_data.py - JC-LAZO-LOCAL-1017-001
Fetches the public, key-less data behind the vendor pages' local sections ONCE, into generate/data/local/.
Nothing here runs per page view or per build: the build reads the cached JSON (generate/local_facts.py).

    python generate\local_data.py weather     # NOAA 1991-2020 monthly climate normals, nearest first-order station per metro
    python generate\local_data.py airports    # OurAirports: US airports with scheduled passenger service
    python generate\local_data.py all

Sources
  NOAA NCEI U.S. Climate Normals 1991-2020 (public domain): https://www.ncei.noaa.gov/data/normals-monthly/1991-2020/
  OurAirports (public domain): https://ourairports.com/data/
"""
import csv, io, json, math, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config.metros import METROS  # noqa: E402

OUT = ROOT / "generate" / "data" / "local"
NOAA = "https://www.ncei.noaa.gov/data/normals-monthly/1991-2020"
UA = {"User-Agent": "Lazo/1.0 (meetlazo.com; support@meetlazo.com)"}


def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(2 + i * 3)


def mi(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(h))


def weather():
    """Nearest station with all three normals we use, within 60 miles of the metro centre."""
    cache = OUT / "noaa"
    cache.mkdir(parents=True, exist_ok=True)
    inv = get(f"{NOAA}/doc/inventory_30yr.txt").decode("latin-1").splitlines()
    stations = []
    for ln in inv:
        p = ln.split()
        if len(p) < 4 or not p[0].startswith("US"):
            continue
        try:
            stations.append((p[0], float(p[1]), float(p[2])))
        except ValueError:
            continue
    # first-order (USW) stations carry temperature and precipitation-day normals; co-op (USC) ones often lack days
    stations.sort(key=lambda s: 0 if s[0].startswith("USW") else 1)
    out = {}
    for m in METROS:
        c = m["center"]
        near = sorted(((mi(c, (s[1], s[2])), s) for s in stations if abs(s[1] - c[0]) < 1.2 and abs(s[2] - c[1]) < 1.5),
                      key=lambda x: (x[0] > 25, 0 if x[1][0].startswith("USW") else 1, x[0]))
        got = None
        for d, s in near[:8]:
            if d > 60:
                continue
            f = cache / f"{s[0]}.csv"
            if not f.exists():
                try:
                    f.write_bytes(get(f"{NOAA}/access/{s[0]}.csv"))
                    time.sleep(0.3)
                except Exception as e:  # noqa: BLE001
                    print(f"  {m['id']}: {s[0]} fetch failed: {e}")
                    continue
            rows = list(csv.DictReader(io.StringIO(f.read_text(encoding="latin-1"))))
            months = []
            for r in rows:
                try:
                    hi = float(r["MLY-TMAX-NORMAL"]); lo = float(r["MLY-TMIN-NORMAL"])
                    wet = float(r["MLY-PRCP-AVGNDS-GE010HI"]); inch = float(r["MLY-PRCP-NORMAL"])
                except (KeyError, ValueError, TypeError):
                    months = []
                    break
                months.append({"hi": round(hi), "lo": round(lo), "wet": round(wet, 1), "in": round(inch, 2)})
            if len(months) == 12:
                got = {"station": s[0], "name": rows[0]["NAME"].strip(), "mi": round(d, 1), "months": months}
                break
        if got:
            out[m["id"]] = got
        else:
            print(f"  {m['id']}: no station with full normals within 60 mi")
    (OUT / "weather.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print(f"[weather] {len(out)}/{len(METROS)} metros -> {OUT / 'weather.json'}")


def airports():
    raw = get("https://davidmegginson.github.io/ourairports-data/airports.csv").decode("utf-8")
    out = []
    for r in csv.DictReader(io.StringIO(raw)):
        if r["iso_country"] != "US" or r["scheduled_service"] != "yes" or not r["iata_code"]:
            continue
        if r["type"] not in ("large_airport", "medium_airport"):
            continue
        out.append({"code": r["iata_code"], "name": r["name"], "city": r["municipality"], "st": r["iso_region"].split("-")[-1],
                    "lat": round(float(r["latitude_deg"]), 4), "lng": round(float(r["longitude_deg"]), 4),
                    "big": r["type"] == "large_airport"})
    (OUT / "airports.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print(f"[airports] {len(out)} US airports with scheduled service -> {OUT / 'airports.json'}")


SPOT_TYPES = {"park", "botanical_garden", "garden", "tourist_attraction", "historical_landmark", "historical_place",
              "cultural_landmark", "national_park", "state_park", "hiking_area", "beach", "plaza", "monument",
              "observation_deck", "scenic_spot", "marina", "lake", "river", "natural_feature", "art_museum", "museum"}
SPOT_SKIP = {"wedding_venue", "event_venue", "banquet_hall", "photographer", "lodging", "restaurant", "store", "bar"}


def photospots(max_calls=48):
    """JC-LAZO-LOCAL-1017-003: PAID. One Places Text Search (Pro fields only, ~$0.046) per big metro - 48 calls.
    Google's terms allow keeping Places content up to 30 days: each metro carries its fetch date, local_facts drops
    anything older, and a metro fetched in the last 25 days is not fetched again."""
    import datetime as dt, os
    # .env directly: a stale Windows-user PLACES_API_KEY (a dead key) shadows it in os.environ
    key = next((ln.split("=", 1)[1].strip().strip('"') for ln in (ROOT / ".env").read_text().splitlines()
                if ln.startswith("PLACES_API_KEY=")), "") or sys.exit("PLACES_API_KEY not in .env")
    sys.path.insert(0, str(ROOT / "generate"))
    from local_facts import BIG
    path = OUT / "photo_spots.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    today = dt.date.today()
    todo = [m for m in METROS if m["id"] in BIG and not (
        m["id"] in data and (today - dt.date.fromisoformat(data[m["id"]]["fetched"])).days < 25)]
    print(f"[photospots] {len(todo)} metros to fetch, cap {max_calls} calls (~${len(todo[:max_calls]) * 0.046:.2f})")
    mask = "places.id,places.displayName,places.formattedAddress,places.location,places.googleMapsUri,places.types,places.primaryType"
    calls = 0
    for m in todo[:max_calls]:
        body = json.dumps({"textQuery": f"scenic parks, gardens and landmarks for photos in {m['display']}", "pageSize": 20,
                           "locationBias": {"circle": {"center": {"latitude": m["center"][0], "longitude": m["center"][1]}, "radius": 40000.0}}}).encode()
        req = urllib.request.Request("https://places.googleapis.com/v1/places:searchText", data=body, method="POST",
                                     headers={"Content-Type": "application/json", "X-Goog-Api-Key": key, "X-Goog-FieldMask": mask})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                res = json.loads(r.read())
        except Exception as e:  # noqa: BLE001
            print(f"  {m['id']}: failed {e}"); calls += 1; continue
        calls += 1
        spots = []
        for p in res.get("places", []):
            types = set(p.get("types") or [])
            if not (types & SPOT_TYPES) or (types & SPOT_SKIP):
                continue
            loc = p.get("location") or {}
            if "latitude" not in loc or mi(m["center"], (loc["latitude"], loc["longitude"])) > 45:
                continue
            spots.append({"id": p["id"], "name": (p.get("displayName") or {}).get("text", ""), "addr": p.get("formattedAddress", ""),
                          "lat": round(loc["latitude"], 5), "lng": round(loc["longitude"], 5), "maps": p.get("googleMapsUri", ""),
                          "type": p.get("primaryType", "")})
        data[m["id"]] = {"fetched": today.isoformat(), "spots": spots[:10]}
        print(f"  {m['id']}: {len(spots)} spots")
        time.sleep(0.2)
    path.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    print(f"[photospots] {calls} paid calls made -> {path}")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what == "photospots":
        photospots()
        sys.exit(0)
    if what in ("airports", "all"):
        airports()
    if what in ("weather", "all"):
        weather()
