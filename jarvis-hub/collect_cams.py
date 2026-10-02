"""JARVIS camera directory: public traffic cameras from every open feed, posted to the hub once a day.

Most of these sources refuse requests from Cloudflare's servers, so the PC builds the list (Task Scheduler "JARVIS cameras",
daily) and the hub serves it by map area. Images are loaded by the browser straight from each agency, except TxDOT,
whose snapshots arrive as JSON and are proxied by the hub.
Entry format: [lat, lon, name, source, image] where image is a URL, or "tx:<district>:<id>" for TxDOT.
"""
import json, os, re, subprocess, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
HUB = "https://jarvis-hub.floral-credit-e4f0.workers.dev"
KEY = open(os.path.join(HERE, ".hub-key")).read().strip()
UA = {"User-Agent": "Mozilla/5.0 (JARVIS hub)"}

# 511 sites on the shared Iteris platform (open camera list + /map/Cctv/<imageId> images)
ITERIS = {"az511.gov": "AZ", "511.idaho.gov": "ID", "511wi.gov": "WI", "www.511pa.com": "PA", "www.511la.org": "LA", "fl511.com": "FL",
          "511.alberta.ca": "AB", "511on.ca": "ON", "511.alaska.gov": "AK", "newengland511.org": "New England", "udottraffic.utah.gov": "UT"}
TX_DISTRICTS = ["ABL", "AMA", "ATL", "AUS", "BMT", "BWD", "BRY", "CHS", "CRP", "DAL", "ELP", "FTW", "HOU", "LRD", "LBB", "LFK", "ODA", "PAR", "PHR", "SJT", "SAT", "TYL", "WAC", "WFS", "YKM"]


def get(url, timeout=60):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout))


def r5(x): return round(float(x), 5)


def iteris(host, label):
    out, start, total = [], 0, None
    while total is None or start < total:
        q = json.dumps({"columns": [{"data": None, "name": ""}, {"name": "sortOrder", "s": True}], "order": [{"column": 1, "dir": "asc"}], "start": start, "length": 100, "search": {"value": ""}})
        d = get(f"https://{host}/List/GetData/Cameras?lang=en-US&query=" + urllib.parse.quote(q), 120)
        total = d.get("recordsTotal") or 0; rows = d.get("data", [])
        if not rows: break
        for x in rows:
            m = re.search(r"POINT \(([-\d.]+) ([-\d.]+)\)", ((x.get("latLng") or {}).get("geography") or {}).get("wellKnownText", ""))
            img = next((i for i in x.get("images", []) if not i.get("disabled") and not i.get("blocked")), None)
            if m and img:
                out.append([r5(m.group(2)), r5(m.group(1)), (img.get("description") or x.get("location") or "")[:90], label, f"https://{host}/map/Cctv/{img['id']}"])
        start += len(rows)
    return out


def txdot(d):
    j = get(f"https://its.txdot.gov/its/DistrictIts/GetCctvStatusListByDistrict?districtCode={d}")
    return [[r5(x["latitude"]), r5(x["longitude"]), x["name"][:90], "TX", f"tx:{d}:{x['icd_Id']}"]
            for lst in (j.get("roadwayCctvStatuses") or {}).values() for x in lst
            if x.get("latitude") and x.get("hasSnapshot") and "online" in (x.get("statusDescription") or "").lower()]


def caltrans(n):
    j = get(f"https://cwwp2.dot.ca.gov/data/d{n}/cctv/cctvStatusD{n:02d}.json", 120)
    out = []
    for row in j.get("data", []):
        c = row.get("cctv", {}); loc = c.get("location", {}); img = (c.get("imageData") or {}).get("static", {}).get("currentImageURL")
        if c.get("inService") == "true" and img and loc.get("latitude"):
            out.append([r5(loc["latitude"]), r5(loc["longitude"]), (loc.get("locationName") or "")[:90], "CA", img])
    return out


def nyc():
    return [[r5(x["latitude"]), r5(x["longitude"]), x["name"][:90], "NYC", x["imageUrl"]] for x in get("https://webcams.nyctmc.org/api/cameras") if x.get("isOnline") == "true" and x.get("imageUrl")]


def london():
    out = []
    for x in get("https://api.tfl.gov.uk/Place/Type/JamCam", 120):
        img = next((p["value"] for p in x.get("additionalProperties", []) if p.get("key") == "imageUrl"), None)
        if img and x.get("lat"):
            out.append([r5(x["lat"]), r5(x["lon"]), x.get("commonName", "")[:90], "London", img])
    return out


def main():
    jobs = [(f"iteris {h}", lambda h=h, l=l: iteris(h, l)) for h, l in ITERIS.items()]
    jobs += [(f"txdot {d}", lambda d=d: txdot(d)) for d in TX_DISTRICTS]
    jobs += [(f"caltrans d{n}", lambda n=n: caltrans(n)) for n in range(1, 13)]
    jobs += [("nyc", nyc), ("london", london)]
    cams, counts = [], {}
    def run(job):
        name, fn = job
        try: return name, fn()
        except Exception as e: print(f"{name}: failed {str(e)[:80]}"); return name, []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for name, rows in ex.map(run, jobs):
            cams += rows
            for r in rows: counts[r[3]] = counts.get(r[3], 0) + 1
    print(f"{len(cams)} cameras:", ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])))
    body = json.dumps({"cams": cams})
    r = subprocess.run(["curl", "-s", "-m", "120", "-X", "POST", "-H", "content-type: application/json", "-H", f"x-hub-key: {KEY}", "--data-binary", "@-", HUB + "/api/world/camsfeed"],
                       input=body, capture_output=True, text=True, timeout=150)
    print("posted:", r.stdout.strip() or r.stderr.strip(), f"({len(body) // 1024} KB)")


if __name__ == "__main__":
    main()
