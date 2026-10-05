"""JARVIS ships feed: passenger vessels (cruise ships and ferries) worldwide from the AIS network via aisstream.io.

Runs on the cloud feeder as a long-lived process (cron tries to start it every minute under flock; it exits at once if
there is no key). Subscribes to the global AIS stream, keeps the latest position of every vessel whose static data says
"passenger" (AIS ship types 60-69), and posts a compact snapshot to the hub every 90 seconds:
  [mmsi, name, lat, lon, cog, sog, type, destination, length_m, age_s]
Key: put your aisstream.io API key in ~/jarvis/.ais-key (one line). Free tier is enough.
"""
import asyncio, json, os, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
HUB = "https://jarvis-hub.floral-credit-e4f0.workers.dev"
KEY = open(os.path.join(HERE, ".hub-key")).read().strip()
AIS_KEY_FILE = os.path.join(HERE, ".ais-key")
POST_EVERY = 90
STALE = 3 * 3600          # drop a vessel not heard from in 3 h

types = {}                # mmsi -> (type, name, dest, length)
pos = {}                  # mmsi -> (lat, lon, cog, sog, t)
stats = {"msgs": 0, "pos": 0, "static": 0}


def post(snapshot):
    body = json.dumps(snapshot).encode()
    req = urllib.request.Request(HUB + "/api/world/shipsfeed", data=body, headers={"content-type": "application/json", "x-hub-key": KEY}, method="POST")
    try:
        r = urllib.request.urlopen(req, timeout=60).read().decode()[:120]
    except Exception as e:
        r = f"post failed: {e}"
    return r


def snapshot():
    now = time.time(); rows = []
    for mmsi, (lat, lon, cog, sog, t) in list(pos.items()):
        if now - t > STALE:
            pos.pop(mmsi, None); continue
        tp, name, dest, length = types.get(mmsi, (0, "", "", 0))
        if not (60 <= tp <= 69):
            continue
        rows.append([mmsi, name, round(lat, 4), round(lon, 4), cog, sog, tp, dest, length, int(now - t)])
    return {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "ships": rows, "known": len(pos), "stats": dict(stats)}


async def run(ais_key):
    import websockets
    sub = {"APIKey": ais_key, "BoundingBoxes": [[[-90, -180], [90, 180]]], "FilterMessageTypes": ["PositionReport", "ShipStaticData"]}
    last_post = time.time()
    async with websockets.connect("wss://stream.aisstream.io/v0/stream", max_size=2 ** 20, ping_interval=20) as ws:
        await ws.send(json.dumps(sub))
        async for raw in ws:
            stats["msgs"] += 1
            try:
                m = json.loads(raw)
            except Exception:
                continue
            md = m.get("MetaData") or {}; mmsi = md.get("MMSI")
            if not mmsi:
                continue
            msg = m.get("Message") or {}
            if "PositionReport" in msg:
                pr = msg["PositionReport"]
                # keep positions only for vessels we know are passenger ships, plus a cheap first position for unknown ones
                tp = types.get(mmsi, (0,))[0]
                if 60 <= tp <= 69 or mmsi not in pos:
                    pos[mmsi] = (pr.get("Latitude"), pr.get("Longitude"), pr.get("Cog"), pr.get("Sog"), time.time())
                    stats["pos"] += 1
            elif "ShipStaticData" in msg:
                sd = msg["ShipStaticData"]; dim = sd.get("Dimension") or {}
                types[mmsi] = (int(sd.get("Type") or 0), (sd.get("Name") or md.get("ShipName") or "").strip(), (sd.get("Destination") or "").strip(), int((dim.get("A") or 0) + (dim.get("B") or 0)))
                stats["static"] += 1
            if time.time() - last_post >= POST_EVERY:
                last_post = time.time()
                # positions for vessels that turned out not to be passenger ships are dead weight: shed them
                for k in [k for k, (lat, lon, cog, sog, t) in pos.items() if not (60 <= types.get(k, (0,))[0] <= 69) and time.time() - t > 600]:
                    pos.pop(k, None)
                snap = snapshot()
                print(time.strftime("%H:%M:%S"), f"{len(snap['ships'])} passenger vessels, {stats['msgs']} msgs ->", post(snap), flush=True)


def main():
    if not os.path.exists(AIS_KEY_FILE):
        return   # no key yet: nothing to do, quietly
    ais_key = open(AIS_KEY_FILE).read().strip()
    while True:
        try:
            asyncio.run(run(ais_key))
        except Exception as e:
            print(time.strftime("%H:%M:%S"), "stream dropped:", str(e)[:120], flush=True)
            time.sleep(15)


if __name__ == "__main__":
    main()
