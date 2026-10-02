"""JARVIS place names for the World globe: world cities (Natural Earth) + every US city and town (Census gazetteer).

Run once (and yearly if you like). Posts [name, lat, lon, rank] rows to the hub; the hub serves the most important names in
view so the map labels get denser as you zoom in. Rank: population for world cities; land area for US towns.
"""
import csv, io, json, os, subprocess, urllib.request, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
HUB = "https://jarvis-hub.floral-credit-e4f0.workers.dev"
KEY = open(os.path.join(HERE, ".hub-key")).read().strip()
UA = {"User-Agent": "Mozilla/5.0 (JARVIS hub)"}


def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()


def norm(n):
    n = " ".join(n.split(",")[0].lower().split())
    for a, b in (("ft. ", "fort "), ("st. ", "saint "), ("mt. ", "mount ")): n = n.replace(a, b)
    return n


def main():
    rows, seen = [], []
    ne = json.loads(fetch("https://cdn.jsdelivr.net/gh/nvkelso/natural-earth-vector@master/geojson/ne_10m_populated_places_simple.geojson"))
    for f in ne["features"]:
        p = f["properties"]; lon, lat = f["geometry"]["coordinates"][:2]
        name = " ".join((p.get("name") or p.get("nameascii")).replace("Ft. ", "Fort ").split()); pop = p.get("pop_max") or 0
        if any(k == norm(name) and abs(la - lat) < 0.25 and abs(lo - lon) < 0.25 for k, la, lo, _ in seen): continue
        rows.append([name, round(lat, 4), round(lon, 4), int(pop)])
        seen.append((norm(name), lat, lon, len(rows) - 1))
    ne_near = {}
    for k, la, lo, i in seen: ne_near.setdefault((round(la), round(lo)), {})[k] = i
    z = zipfile.ZipFile(io.BytesIO(fetch("https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_place_national.zip")))
    txt = z.read(z.namelist()[0]).decode("latin-1")
    for r in csv.DictReader(io.StringIO(txt), delimiter="\t"):
        r = {k.strip(): v for k, v in r.items()}
        name = r["NAME"]
        for suffix in (" city", " town", " village", " CDP", " borough", " municipality", " (balance)", " city and borough"):
            if name.endswith(suffix): name = name[: -len(suffix)]
        lat, lon = float(r["INTPTLAT"]), float(r["INTPTLONG"])
        # land area (m^2) as a stand-in for size (~population-sized numbers); CDPs rank lower than incorporated places
        rank = int(float(r["ALAND"]) / 4000) // (4 if r["NAME"].endswith(" CDP") else 1)
        hit = next((cell[norm(name)] for a in (-1, 0, 1) for b in (-1, 0, 1) if norm(name) in (cell := ne_near.get((round(lat) + a, round(lon) + b), {}))), None)
        if hit is not None: rows[hit][3] = max(rows[hit][3], rank); continue  # already listed: keep the larger importance
        rows.append([f"{name}, {r['USPS']}", round(lat, 4), round(lon, 4), rank])
    rows.sort(key=lambda x: -x[3])
    body = json.dumps({"places": rows})
    out = subprocess.run(["curl", "-s", "-m", "120", "-X", "POST", "-H", "content-type: application/json", "-H", f"x-hub-key: {KEY}", "--data-binary", "@-", HUB + "/api/world/placesfeed"], input=body, capture_output=True, text=True, timeout=150)
    print(f"{len(rows)} places ({len(body) // 1024} KB) ->", out.stdout.strip() or out.stderr.strip())


if __name__ == "__main__":
    main()
