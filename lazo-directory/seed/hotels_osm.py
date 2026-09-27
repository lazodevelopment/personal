"""hotels_osm.py - JC-LAZO-HOTELS-0921-001
Hotels near every wedding venue, from OpenStreetMap (ODbL: free, and unlike
Google Places the data may be stored and published indefinitely, with the
"(c) OpenStreetMap contributors" credit the vendor page prints).

One Overpass query per metro: a bounding box around the metro's search grid,
padded 0.45 degrees (~30 mi), for tourism=hotel|motel nodes and ways with a
name. Each metro's answer is cached in data/hotels_cache/<metro>.json so a
re-run only fetches what is missing; --refresh refetches everything. The merged
result is data/hotels_osm.json, which build.py reads to attach the six nearest
hotels (within 15 mi) to every venue page.

  python seed\\hotels_osm.py                # fetch missing metros, merge
  python seed\\hotels_osm.py --metro maui   # one metro
  python seed\\hotels_osm.py --refresh      # refetch all (data ages; yearly is plenty)

Endpoints: the public overpass-api.de instance 504s under load; the VK mirror
answers slowly but reliably, so it goes first. Queries run one at a time with
a pause: these are shared, volunteer-run servers.
"""
import argparse, json, sys, time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config.metros import METROS, BY_ID  # noqa: E402

DATA = ROOT / "data"; CACHE = DATA / "hotels_cache"; OUT = DATA / "hotels_osm.json"
ENDPOINTS = ["https://maps.mail.ru/osm/tools/overpass/api/interpreter",
             "https://overpass-api.de/api/interpreter",
             "https://lz4.overpass-api.de/api/interpreter"]
UA = "Lazo-hotels/1.0 (https://meetlazo.com; info@meetlazo.com)"
PAD = 0.45


def bbox(metro):
    lats = [t[0] for t in metro["grid"]] + [metro["center"][0]]
    lngs = [t[1] for t in metro["grid"]] + [metro["center"][1]]
    return (min(lats) - PAD, min(lngs) - PAD, max(lats) + PAD, max(lngs) + PAD)


def query(metro):
    s, w, n, e = bbox(metro)
    q = (f'[out:json][timeout:170];'
         f'(node["tourism"~"^(hotel|motel)$"]["name"]({s:.4f},{w:.4f},{n:.4f},{e:.4f});'
         f'way["tourism"~"^(hotel|motel)$"]["name"]({s:.4f},{w:.4f},{n:.4f},{e:.4f}););'
         f'out center tags;')
    last = None
    for ep in ENDPOINTS:
        for attempt in (1, 2):
            try:
                r = requests.post(ep, data={"data": q}, headers={"User-Agent": UA}, timeout=200)
                if r.status_code == 200:
                    return r.json().get("elements", [])
                last = f"{ep} HTTP {r.status_code}"
            except Exception as ex:  # noqa: BLE001
                last = f"{ep} {type(ex).__name__}"
            time.sleep(8)
    raise RuntimeError(last or "no endpoint answered")


def compact(el):
    t = el.get("tags", {})
    lat = el.get("lat") or (el.get("center") or {}).get("lat")
    lng = el.get("lon") or (el.get("center") or {}).get("lon")
    if lat is None or lng is None or not t.get("name"):
        return None
    addr = " ".join(x for x in (t.get("addr:housenumber"), t.get("addr:street")) if x)
    city = t.get("addr:city") or ""
    site = t.get("website") or t.get("contact:website") or t.get("brand:website") or ""
    if site and not site.startswith("http"):
        site = "https://" + site
    d = {"id": f'{el["type"][0]}{el["id"]}', "name": t["name"].strip(), "lat": round(float(lat), 5),
         "lng": round(float(lng), 5), "kind": t.get("tourism", "hotel")}
    if addr: d["addr"] = addr
    if city: d["city"] = city
    if site: d["site"] = site[:200]
    if t.get("stars"): d["stars"] = t["stars"][:3]
    if t.get("brand"): d["brand"] = t["brand"][:60]
    if t.get("phone") or t.get("contact:phone"): d["phone"] = (t.get("phone") or t.get("contact:phone"))[:30]
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metro"); ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    targets = [BY_ID[a.metro]] if a.metro else METROS
    fetched = 0
    for m in targets:
        f = CACHE / f'{m["id"]}.json'
        if f.exists() and not a.refresh:
            continue
        t0 = time.time()
        try:
            els = query(m)
        except Exception as ex:  # noqa: BLE001
            print(f'[{m["id"]}] FAILED: {ex}', flush=True); continue
        hotels = [h for h in (compact(e) for e in els) if h]
        f.write_text(json.dumps(hotels, ensure_ascii=False), encoding="utf-8")
        fetched += 1
        print(f'[{m["id"]}] {len(hotels)} hotels in {time.time() - t0:.0f}s', flush=True)
        time.sleep(3)
    # merge, dedupe by osm id
    allh = {}
    for f in sorted(CACHE.glob("*.json")):
        for h in json.loads(f.read_text(encoding="utf-8")):
            allh[h["id"]] = h
    OUT.write_text(json.dumps(list(allh.values()), ensure_ascii=False), encoding="utf-8")
    print(f"fetched {fetched} metro(s); {len(allh):,} unique hotels -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
