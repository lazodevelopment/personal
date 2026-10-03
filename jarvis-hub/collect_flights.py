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


GLOBAL_EVERY = 15 * 60  # OpenSky's anonymous allowance is ~100 worldwide pulls a day
STAMP = os.path.join(HERE, ".global_flights_at")


def global_flights():
    """Every aircraft OpenSky sees worldwide, compacted to [hex, callsign, lat, lon, alt_ft, track, speed_kt, on_ground]."""
    j = json.load(urllib.request.urlopen(urllib.request.Request("https://opensky-network.org/api/states/all", headers={"User-Agent": "Mozilla/5.0 (JARVIS hub)"}), timeout=60))
    out = []
    for s in j.get("states") or []:
        if s[5] is None or s[6] is None: continue
        alt = s[13] if s[13] is not None else s[7]
        out.append([s[0], (s[1] or "").strip(), round(s[6], 3), round(s[5], 3), round(alt * 3.28084) if alt is not None else None, round(s[10]) if s[10] is not None else None, round(s[9] * 1.94384) if s[9] is not None else None, 1 if s[8] else 0])
    return {"at": datetime.fromtimestamp(j.get("time", 0), timezone.utc).isoformat(), "ac": out}


def main():
    import time, sys
    # --global-only: the PC (OpenSky refuses Google Cloud)   --local-only: the cloud feeder (adsb.lol/adsb.fi are fine from there)
    do_global, do_local = "--local-only" not in sys.argv, "--global-only" not in sys.argv
    try:
        last = float(open(STAMP).read()) if os.path.exists(STAMP) else 0
        if do_global and time.time() - last >= GLOBAL_EVERY:
            g = global_flights()
            r = hub("/api/world/globalfeed", g)
            open(STAMP, "w").write(str(time.time()))
            print(datetime.now().strftime("%H:%M:%S"), f"global: {len(g['ac'])} aircraft ->", r)
    except Exception as e:
        print("global flights failed:", str(e)[:120])
    if not do_local: return
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
