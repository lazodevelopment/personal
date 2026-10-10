"""JARVIS ships feed: passenger vessels (cruise ships and ferries) worldwide from the AIS network via aisstream.io.

Runs on the cloud feeder as a long-lived process (cron tries to start it every minute under flock; it exits at once if
there is no key). Subscribes to the global AIS stream, keeps the latest position of every vessel that is a passenger
ship (AIS type 60-69 from its static data) or carries a cruise-line name, and posts a compact snapshot to the hub every
90 seconds:  [mmsi, name, lat, lon, cog, sog, type, destination, length_m, age_s]
Identities (type, name, destination, length) are remembered in ships_types.json between runs, because a ship's static
broadcast only comes every six minutes and coverage near some islands is patchy.
Key: put your aisstream.io API key in ~/jarvis/.ais-key (one line). Free tier is enough.
"""
import asyncio, json, os, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
HUB = "https://jarvis-hub.floral-credit-e4f0.workers.dev"
KEY = open(os.path.join(HERE, ".hub-key")).read().strip()
AIS_KEY_FILE = os.path.join(HERE, ".ais-key")
TYPES_FILE = os.path.join(HERE, "ships_types.json")
POST_EVERY = 90
STALE = 3 * 3600          # drop a vessel not heard from in 3 h
CRUISE_WORDS = ("OF THE SEAS", "CARNIVAL", "NORWEGIAN", "PRIDE OF AMERICA", "MSC ", "CELEBRITY", "PRINCESS", "DISNEY", "HOLLAND", "CUNARD", "QUEEN MARY",
                "QUEEN ELIZABETH", "QUEEN ANNE", "VIRGIN", "SCARLET LADY", "VALIANT LADY", "RESILIENT LADY", "AIDA", "COSTA", "OCEANIA",
                "REGENT", "SEABOURN", "SILVER ", "VIKING", "AZAMARA", "MARELLA", "P&O", "ARCADIA", "VENTURA", "BRITANNIA", "IONA",
                "ARVIA", "AURORA", "CRYSTAL", "RITZ-CARLTON", "EXPLORA", "AMBIENCE", "AMBITION", "MEIN SCHIFF", "WORLD AMERICA",
                "WORLD EUROPA", "HURTIGRUTEN", "PONANT", "WINDSTAR", "LINDBLAD", "SEADREAM", "RIVIERA", "MARINA", "NAUTICA", "INSIGNIA")

types = {}                # mmsi -> [type, name, dest, length]
pos = {}                  # mmsi -> (lat, lon, cog, sog, t)
stats = {"msgs": 0, "pos": 0, "static": 0}


def load_types():
    try:
        d = json.load(open(TYPES_FILE)); types.update({int(k): v for k, v in d.items()})
    except Exception:
        pass


def save_types():
    try:
        tmp = TYPES_FILE + ".tmp"; json.dump(types, open(tmp, "w")); os.replace(tmp, TYPES_FILE)
    except Exception:
        pass


def looks_cruise(name):
    n = (name or "").upper()
    return any(w in n for w in CRUISE_WORDS)


def is_passenger(mmsi):
    tp = types.get(mmsi, [0])[0]
    return 60 <= tp <= 69


def post(snapshot):
    body = json.dumps(snapshot).encode()
    req = urllib.request.Request(HUB + "/api/world/shipsfeed", data=body, headers={"content-type": "application/json", "x-hub-key": KEY, "User-Agent": "Mozilla/5.0 (JARVIS feeder)"}, method="POST")
    try:
        return urllib.request.urlopen(req, timeout=60).read().decode()[:120]
    except Exception as e:
        return f"post failed: {e}"


def snapshot():
    now = time.time(); rows = []
    for mmsi, (lat, lon, cog, sog, t) in list(pos.items()):
        if now - t > STALE:
            pos.pop(mmsi, None); continue
        if not is_passenger(mmsi):
            continue
        tp, name, dest, length = types.get(mmsi, [0, "", "", 0])
        rows.append([mmsi, name, round(lat, 4), round(lon, 4), cog, sog, tp, dest, length, int(now - t)])
    return {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "ships": rows, "known": len(pos), "identities": len(types), "stats": dict(stats)}


async def run(ais_key):
    import websockets
    sub = {"APIKey": ais_key, "BoundingBoxes": [[[-90, -180], [90, 180]]], "FilterMessageTypes": ["PositionReport", "ShipStaticData"]}
    last_post = time.time(); last_save = time.time()
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
                # a cruise-line name on the position report is enough to count the ship before its static data arrives
                if mmsi not in types and looks_cruise(md.get("ShipName")):
                    types[mmsi] = [69, (md.get("ShipName") or "").strip(), "", 0]
                pos[mmsi] = (pr.get("Latitude"), pr.get("Longitude"), pr.get("Cog"), pr.get("Sog"), time.time())
                stats["pos"] += 1
            elif "ShipStaticData" in msg:
                sd = msg["ShipStaticData"]; dim = sd.get("Dimension") or {}
                types[mmsi] = [int(sd.get("Type") or 0), (sd.get("Name") or md.get("ShipName") or "").strip(), (sd.get("Destination") or "").strip(), int((dim.get("A") or 0) + (dim.get("B") or 0))]
                stats["static"] += 1
            now = time.time()
            if now - last_post >= POST_EVERY:
                last_post = now
                for k in [k for k, v in pos.items() if now - v[4] > STALE]:
                    pos.pop(k, None)
                snap = snapshot()
                print(time.strftime("%H:%M:%S"), f"{len(snap['ships'])} passenger vessels of {len(pos)} positions, {len(types)} identities, {stats['msgs']} msgs ->", post(snap), flush=True)
            if now - last_save >= 600:
                last_save = now; save_types()


def main():
    if not os.path.exists(AIS_KEY_FILE):
        return   # no key yet: nothing to do, quietly
    ais_key = open(AIS_KEY_FILE).read().strip()
    load_types()
    while True:
        try:
            asyncio.run(run(ais_key))
        except Exception as e:
            print(time.strftime("%H:%M:%S"), "stream dropped:", str(e)[:120], flush=True)
            save_types(); time.sleep(15)


if __name__ == "__main__":
    main()
