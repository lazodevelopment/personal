# probe_places.py — one query, full visibility
import requests, json

import os as _os
def _env(name):
    v = _os.environ.get(name)
    if not v:
        p = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '.env')
        if _os.path.exists(p):
            for line in open(p, encoding='utf-8'):
                if line.startswith(name + '='): v = line.split('=', 1)[1].strip()
    if not v: raise SystemExit(name + ' is not set (put it in .env next to this script)')
    return v
KEY = _env("PLACES_API_KEY")
r = requests.post(
    "https://places.googleapis.com/v1/places:searchText",
    json={"textQuery": "apartment complexes in Frisco, TX", "pageSize": 20},
    headers={
        "X-Goog-Api-Key": KEY,
        "X-Goog-FieldMask": "places.id,places.displayName,places.types",
        "Content-Type": "application/json",
    },
    timeout=30,
)
print("HTTP", r.status_code)
data = r.json()
places = data.get("places", [])
print(len(places), "places returned")
for p in places:
    print("  ", (p.get("displayName") or {}).get("text", "?"), "->", p.get("types"))
if r.status_code != 200:
    print(json.dumps(data, indent=2)[:1200])