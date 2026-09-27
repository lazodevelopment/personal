#!/usr/bin/env python3
"""crawl_cities.py - one-time data crawl for the Elizabeth Scott location layer.

Pulls real wedding-venue data + city coordinates from the Google Places API and
writes _src/city_data.json. This is the ingredient the ES city pages are missing:
without it every page in a region shares the same two paragraphs.

  python _src/crawl_cities.py --key YOUR_KEY            # full run
  python _src/crawl_cities.py --key YOUR_KEY --limit 5  # smoke test first
  python _src/crawl_cities.py --key YOUR_KEY            # re-run resumes

Resumable: every city is checkpointed the moment it returns, so a crash, a
rate-limit, or Ctrl-C costs you nothing. Re-running skips completed cities.
"""
import sys, os, json, time, pathlib, argparse, urllib.request, urllib.error

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from cities_data import CITIES

SRC = pathlib.Path(__file__).resolve().parent
OUT = SRC / "city_data.json"
ENDPOINT = "https://places.googleapis.com/v1/places:searchText"

# Only these fields are requested - field mask drives Places API billing, so
# asking for less costs less. Do not add fields you will not render.
FIELDS = ("places.displayName,places.formattedAddress,places.location,"
          "places.rating,places.userRatingCount,places.types,places.id")

# Places categories that are plausibly a wedding venue. Anything else is dropped.
GOOD = {"wedding_venue", "event_venue", "banquet_hall", "hotel", "resort_hotel",
        "park", "museum", "art_gallery", "winery", "farm", "country_club",
        "golf_course", "historical_landmark", "church", "botanical_garden"}
# Hard excludes - these pollute "wedding venue" searches badly.
BAD = {"clothing_store", "bridal_shop", "florist", "jewelry_store", "bakery",
       "photographer", "beauty_salon", "hair_care", "store", "travel_agency"}


def post(url, payload, headers, retries=4):
    body = json.dumps(payload).encode()
    for attempt in range(retries):
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:400]
            if e.code in (429, 500, 502, 503):          # transient - back off
                wait = 2 ** attempt
                print(f"      HTTP {e.code}, retry in {wait}s", flush=True)
                time.sleep(wait)
                continue
            if e.code in (401, 403):
                raise SystemExit(
                    f"\nAUTH FAILED (HTTP {e.code}).\n{detail}\n\n"
                    "Check that the key is valid and that 'Places API (New)' is\n"
                    "ENABLED in the Google Cloud console for this project.\n"
                    "The legacy 'Places API' is a different product and will not work here.")
            raise SystemExit(f"\nHTTP {e.code} from Places API:\n{detail}")
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    return {}


def search(key, query, maxn=12):
    return post(ENDPOINT, {"textQuery": query, "maxResultCount": maxn,
                           "languageCode": "en", "regionCode": "US"},
                {"Content-Type": "application/json",
                 "X-Goog-Api-Key": key,
                 "X-Goog-FieldMask": FIELDS})


def clean(places):
    out = []
    for p in places or []:
        types = set(p.get("types", []))
        if types & BAD or not (types & GOOD):
            continue
        loc = p.get("location") or {}
        if "latitude" not in loc:
            continue
        out.append(dict(
            name=(p.get("displayName") or {}).get("text", "").strip(),
            addr=p.get("formattedAddress", "").strip(),
            lat=round(loc["latitude"], 6), lng=round(loc["longitude"], 6),
            rating=p.get("rating"), reviews=p.get("userRatingCount", 0),
            pid=p.get("id", "")))
    # strongest social proof first; unrated venues sink
    out.sort(key=lambda v: (v["rating"] or 0) * min(v["reviews"], 400), reverse=True)
    # de-dupe by name
    seen, uniq = set(), []
    for v in out:
        k = v["name"].lower()
        if k and k not in seen:
            seen.add(k); uniq.append(v)
    return uniq


def centroid(venues):
    """Median venue position. Median, not mean, so one outlier venue two counties
    over cannot drag the coordinate - which would silently corrupt sunset times."""
    if not venues:
        return None, None, None
    lats = sorted(v["lat"] for v in venues)
    lngs = sorted(v["lng"] for v in venues)
    mid = len(lats) // 2
    spread = max(lats[-1] - lats[0], lngs[-1] - lngs[0])
    return lats[mid], lngs[mid], round(spread, 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default=os.environ.get("GOOGLE_PLACES_KEY", ""),
                    help="Places API key (or set GOOGLE_PLACES_KEY)")
    ap.add_argument("--limit", type=int, default=0, help="only crawl first N cities")
    ap.add_argument("--sleep", type=float, default=0.25, help="seconds between calls")
    ap.add_argument("--refresh", action="store_true", help="ignore checkpoint, recrawl all")
    a = ap.parse_args()
    if not a.key:
        raise SystemExit("No API key. Pass --key or set GOOGLE_PLACES_KEY.")

    data = {}
    if OUT.exists() and not a.refresh:
        data = json.loads(OUT.read_text(encoding="utf-8"))
        print(f"resuming - {len(data)} cities already crawled")

    todo = list(CITIES)
    if a.limit:
        todo = todo[:a.limit]

    done = fails = 0
    for i, (name, st, region) in enumerate(todo, 1):
        keyname = f"{name}|{st}"
        if keyname in data and not a.refresh:
            continue
        q = f"wedding venue in {name}, {st}"
        print(f"[{i}/{len(todo)}] {name}, {st}", end=" ", flush=True)
        try:
            res = search(a.key, q)
        except SystemExit:
            raise
        except Exception as e:
            print(f"FAILED ({e})")
            fails += 1
            continue
        venues = clean(res.get("places", []))
        lat, lng, spread = centroid(venues)
        data[keyname] = dict(name=name, st=st, region=region,
                             lat=lat, lng=lng, spread=spread,
                             venues=venues[:8], crawled=int(time.time()))
        # checkpoint every single city - a crash costs nothing
        OUT.write_text(json.dumps(data, indent=1), encoding="utf-8")
        flag = "  <-- venues are scattered, verify" if (spread or 0) > 1.0 else ""
        print(f"{len(venues)} venues{flag}")
        done += 1
        time.sleep(a.sleep)

    empty = [k for k, v in data.items() if not v.get("venues")]
    print(f"\ncrawled {done} cities this run | {fails} failures | "
          f"{len(data)} total in city_data.json")
    if empty:
        print(f"{len(empty)} cities returned no usable venues: "
              f"{', '.join(empty[:8])}{' ...' if len(empty) > 8 else ''}")
        print("  (those pages fall back to the generic template - fine, just thinner)")


if __name__ == "__main__":
    main()
