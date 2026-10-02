"""JARVIS flights feed: aircraft near home plus any flights you've asked JARVIS to track.

The community ADS-B networks refuse requests from Cloudflare's servers, so this runs on the PC every minute
(Task Scheduler "JARVIS flights") and posts the result to the hub, which serves it to the World globe and the brain.
"""
import json, os, subprocess, urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
HUB = "https://jarvis-hub.floral-credit-e4f0.workers.dev"
KEY = open(os.path.join(HERE, ".hub-key")).read().strip()
SOURCES = ["https://api.adsb.lol/v2", "https://opendata.adsb.fi/api/v2"]


def hub(path, body=None):
    args = ["curl", "-s", "-m", "30", "-H", f"x-hub-key: {KEY}", HUB + path]
    if body is not None:
        args += ["-X", "POST", "-H", "content-type: application/json", "--data-binary", "@-"]
    r = subprocess.run(args, input=json.dumps(body) if body is not None else None, capture_output=True, text=True, timeout=40)
    return json.loads(r.stdout) if r.stdout.strip() else None


def adsb(path):
    last = None
    for base in SOURCES:
        try:
            req = urllib.request.Request(base + path, headers={"User-Agent": "Mozilla/5.0 (JARVIS hub)"})
            j = json.load(urllib.request.urlopen(req, timeout=15))
            return j.get("ac") or j.get("aircraft") or []
        except Exception as e:
            last = e
    raise RuntimeError(f"all ADS-B sources failed: {last}")


def slim(a):
    alt = a.get("alt_baro")
    return {"hex": a.get("hex"), "flight": (a.get("flight") or "").strip(), "reg": a.get("r") or "", "type": a.get("t") or "",
            "lat": a.get("lat"), "lon": a.get("lon"), "alt": 0 if alt == "ground" else (alt if alt is not None else a.get("alt_geom")),
            "gs": round(a["gs"]) if a.get("gs") is not None else None, "track": a.get("track"), "squawk": a.get("squawk") or "",
            "emergency": a.get("emergency") if a.get("emergency") not in (None, "none") else "", "desc": a.get("desc") or "", "ownOp": a.get("ownOp") or ""}


def main():
    want = hub("/api/world/want") or {}
    lat, lon, nm = want.get("lat", 33.15), want.get("lon", -96.82), want.get("nm", 80)
    near = [slim(a) for a in adsb(f"/lat/{lat:.3f}/lon/{lon:.3f}/dist/{nm}") if a.get("lat") is not None]
    tracks = {}
    for cs in want.get("track", [])[:6]:
        try:
            path = f"/reg/{cs}" if cs[:1] == "N" and cs[1:2].isdigit() else f"/callsign/{cs}"
            tracks[cs] = [slim(a) for a in adsb(path) if a.get("lat") is not None]
        except Exception as e:
            tracks[cs] = []
    r = hub("/api/world/feed", {"at": datetime.now(timezone.utc).isoformat(), "center": {"lat": lat, "lon": lon}, "ac": near, "tracks": tracks})
    print(datetime.now().strftime("%H:%M:%S"), f"{len(near)} aircraft, tracks {list(tracks)} ->", r)


if __name__ == "__main__":
    main()
