"""JARVIS traffic collector: live web traffic for Atavia and Elizabeth Scott.

Both sites log visits to Firestore (sessions with first_seen/last_seen, hits subcollection with t/path).
Every 5 minutes (Task Scheduler "JARVIS traffic") this posts, per site:
  online   real sessions seen in the last 5 minutes
  today    real sessions that started today (local time), page views today, top pages
  hourly   visitors per hour today (24 buckets)
Bots are filtered the same way the admin visitor page and atavia-pulse do.
"""
import json, os, re, sys, subprocess, warnings
import datetime as dt
from collections import defaultdict
from zoneinfo import ZoneInfo
warnings.filterwarnings("ignore", message=".*without a quota project.*")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from collect_metrics import client_for, ts

HUB = "https://jarvis-hub.floral-credit-e4f0.workers.dev"
TZ = ZoneInfo("America/Chicago")
NOW = dt.datetime.now(dt.timezone.utc)
DAY_START = dt.datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(dt.timezone.utc)
ACTIVE = NOW - dt.timedelta(minutes=5)

BOT_RE = re.compile(
    r"bot|crawl|spider|slurp|lighthouse|facebookexternalhit|facebot|meta-externalagent|whatsapp|twitterbot|"
    r"linkedinbot|pinterest|slackbot|discordbot|telegrambot|applebot|bingpreview|headlesschrome|phantomjs|"
    r"petalbot|ahrefs|semrush|mj12|screaming frog|gtmetrix|pingdom|uptimerobot|preview|snapchat|"
    r"skypeuripreview|embedly|google-inspectiontool|yandex|baidu|duckduckbot", re.I)
DC_CITIES = {"Boardman", "Ashburn", "The Dalles", "Council Bluffs", "Prineville", "Umatilla", "Forest City",
             "Altoona", "Hilliard", "Papillion", "Sterling", "Quincy"}
META_UTM = re.compile(r"^(ig|fb|msg|an)$", re.I)


def is_bot(s):
    if s.get("bot") is True or BOT_RE.search(s.get("ua") or ""):
        return True
    try:
        pages = int(s.get("page_count") or 1)
    except (TypeError, ValueError):
        pages = 1
    city = s.get("city")
    if city in DC_CITIES and pages <= 1:
        a, b = ts(s.get("first_seen")), ts(s.get("last_seen"))
        if not (a and b) or (b - a).total_seconds() < 15:
            return True
    no_geo = not city and not isinstance(s.get("lat"), (int, float))
    if not s.get("engaged") and no_geo and META_UTM.match(s.get("utm_source") or "") and pages <= 1:
        return True
    return False


def clean_path(p):
    p = (p or "/").split("?")[0].split("#")[0]
    return p if len(p) <= 60 else p[:57] + "..."


def collect(biz):
    from google.cloud.firestore_v1.base_query import FieldFilter
    db = client_for(biz)
    if db is None:
        return {"error": "needs access"}
    today = {d.id: (d.to_dict() or {}) for d in db.collection("sessions").where(filter=FieldFilter("first_seen", ">=", DAY_START)).stream()}
    active = {d.id: (d.to_dict() or {}) for d in db.collection("sessions").where(filter=FieldFilter("last_seen", ">=", ACTIVE)).stream()}
    real_today = {k: v for k, v in today.items() if not is_bot(v)}
    real_active = {k: v for k, v in active.items() if not is_bot(v)}
    hourly = [0] * 24
    for s in real_today.values():
        t = ts(s.get("first_seen"))
        if t:
            hourly[t.astimezone(TZ).hour] += 1
    pages, views = defaultdict(int), 0
    try:
        for h in db.collection_group("hits").where(filter=FieldFilter("t", ">=", DAY_START)).select(["path"]).stream():
            sid = h.reference.parent.parent.id
            if sid in real_today or sid in real_active:
                views += 1
                pages[clean_path((h.to_dict() or {}).get("path"))] += 1
    except Exception as e:
        print(f"{biz}: hits group query unavailable ({str(e)[:80]}); using page_count")
        views = sum(int(s.get("page_count") or 1) for s in real_today.values())
    now_pages = sorted({clean_path(s.get("last_page") or s.get("landing") or "/") for s in real_active.values()})
    devices = defaultdict(int)
    for s in real_today.values():
        devices[str(s.get("device") or "?")] += 1
    sources = defaultdict(int)
    for s in real_today.values():
        ref = s.get("referrer") or ""
        src = (s.get("utm_source") or "").strip() or ("direct" if not ref else re.sub(r"^https?://(www\.)?", "", ref).split("/")[0])
        sources[src[:30]] += 1
    return {
        "online": len(real_active), "today": len(real_today), "views": views, "bots_today": len(today) - len(real_today),
        "hourly": hourly, "pages": sorted(pages.items(), key=lambda kv: -kv[1])[:6], "now_pages": now_pages[:6],
        "devices": dict(devices), "sources": sorted(sources.items(), key=lambda kv: -kv[1])[:5],
    }


LEAGUES = {"nfl": "football/nfl", "mlb": "baseball/mlb", "nba": "basketball/nba", "nhl": "hockey/nhl"}
FAV = ["DAL", "NE", "TEX", "COL", "BOS", "ARI"]
TEAM_IDS = [("nfl", "DAL", 6, "Cowboys"), ("nfl", "NE", 17, "Patriots"), ("mlb", "TEX", 13, "Rangers"), ("mlb", "COL", 27, "Rockies"), ("mlb", "BOS", 2, "Red Sox"), ("mlb", "ARI", 29, "Diamondbacks")]


def standings(leagues=("nfl", "mlb")):
    """Division tables containing the favourite teams, keyed by team abbreviation."""
    import urllib.request
    out = {}
    for lg in leagues:
        try:
            req = urllib.request.Request(f"https://site.web.api.espn.com/apis/v2/sports/{LEAGUES[lg]}/standings?level=3", headers={"User-Agent": "Mozilla/5.0"})
            j = json.load(urllib.request.urlopen(req, timeout=20))
        except Exception as e:
            print(f"standings {lg}: {e}"); continue
        groups = []
        def walk(n):
            if "standings" in n: groups.append(n)
            for c in n.get("children", []): walk(c)
        walk(j)
        for g in groups:
            rows = []
            for e in g["standings"].get("entries", []):
                st = {x["name"]: x.get("displayValue") for x in e.get("stats", [])}
                rows.append({"abbr": e["team"].get("abbreviation"), "name": e["team"].get("shortDisplayName") or e["team"].get("displayName"), "w": st.get("wins"), "l": st.get("losses"), "pct": st.get("winPercent"), "gb": st.get("gamesBehind"), "streak": st.get("streak"), "seed": st.get("playoffSeed"), "clinch": st.get("clincher") or "", "fav": e["team"].get("abbreviation") in FAV})
            rows.sort(key=lambda r: -float(r["pct"] or 0))
            for i, r in enumerate(rows): r["rank"] = i + 1
            for r in rows:
                if r["fav"]: out[r["abbr"]] = {"league": lg, "division": g["name"].replace("American League", "AL").replace("National League", "NL"), "rank": r["rank"], "rows": rows}
    return out


def team_cards():
    """Record plus next scheduled game and last result for each favourite team."""
    import urllib.request
    cards = []
    for lg, abbr, tid, name in TEAM_IDS:
        card = {"league": lg, "abbr": abbr, "name": name}
        try:
            req = urllib.request.Request(f"https://site.api.espn.com/apis/site/v2/sports/{LEAGUES[lg]}/teams/{tid}/schedule", headers={"User-Agent": "Mozilla/5.0"})
            j = json.load(urllib.request.urlopen(req, timeout=20))
            card["name"] = (j.get("team") or {}).get("displayName") or name
            card["logo"] = ((j.get("team") or {}).get("logo") or "")
            evs = []
            for ev in j.get("events", []):
                c = (ev.get("competitions") or [{}])[0]
                me = next((t for t in c.get("competitors", []) if str(t.get("id")) == str(tid)), None)
                opp = next((t for t in c.get("competitors", []) if str(t.get("id")) != str(tid)), None)
                if not me or not opp: continue
                st = (c.get("status") or ev.get("status") or {}).get("type", {})
                evs.append({"date": ev.get("date"), "state": st.get("state"), "detail": st.get("shortDetail", ""), "opp": (opp.get("team") or {}).get("shortDisplayName") or (opp.get("team") or {}).get("displayName"), "home": me.get("homeAway") == "home",
                            "my": (me.get("score") or {}).get("displayValue") if isinstance(me.get("score"), dict) else me.get("score"), "their": (opp.get("score") or {}).get("displayValue") if isinstance(opp.get("score"), dict) else opp.get("score"), "won": me.get("winner") is True, "tv": ((c.get("broadcasts") or [{}])[0].get("media") or {}).get("shortName", "")})
            evs.sort(key=lambda e: e["date"] or "")
            now = NOW.isoformat()
            done = [e for e in evs if e["state"] == "post"]; upcoming = [e for e in evs if e["state"] in ("pre", "in") and (e["state"] == "in" or (e["date"] or "") >= now)]
            card["last"] = done[-1] if done else None
            card["next"] = upcoming[0] if upcoming else None
            card["upcoming"] = upcoming[:5]
            card["recent"] = done[-3:]
            # record from the schedule's season summary when present
            rec = None
            for ev in reversed(j.get("events", [])):
                c = (ev.get("competitions") or [{}])[0]
                me = next((t for t in c.get("competitors", []) if str(t.get("id")) == str(tid)), None)
                r = ((me or {}).get("record") or [{}])
                if r and isinstance(r, list) and r[0].get("displayValue"): rec = r[0]["displayValue"]; break
            card["record"] = rec
            if not card["next"] and lg == "mlb": card["note"] = "season over"
        except Exception as e:
            card["error"] = str(e)[:80]
        cards.append(card)
    return cards



def sports(leagues=("nfl", "mlb")):
    """ESPN public scoreboard for yesterday/today/tomorrow, compacted the way the hub renders it."""
    import urllib.request
    games, seen = [], set()
    for lg in leagues:
        for n in (-1, 0, 1):
            d = (NOW + dt.timedelta(days=n)).strftime("%Y%m%d")
            try:
                req = urllib.request.Request(f"https://site.api.espn.com/apis/site/v2/sports/{LEAGUES[lg]}/scoreboard?dates={d}", headers={"User-Agent": "Mozilla/5.0"})
                j = json.load(urllib.request.urlopen(req, timeout=20))
            except Exception as e:
                print(f"sports {lg} {d}: {e}"); continue
            for ev in j.get("events", []):
                if ev["id"] in seen: continue
                seen.add(ev["id"])
                c = (ev.get("competitions") or [{}])[0]
                teams = [{"abbr": t["team"]["abbreviation"], "name": t["team"].get("shortDisplayName") or t["team"].get("displayName"), "score": t.get("score"), "home": t.get("homeAway") == "home", "winner": t.get("winner") is True, "record": ((t.get("records") or [{}])[0]).get("summary", "")} for t in c.get("competitors", [])]
                st = ev.get("status", {}).get("type", {})
                games.append({"league": lg, "id": ev["id"], "date": ev.get("date"), "state": st.get("state"), "detail": st.get("shortDetail", ""), "teams": teams, "fav": any(t["abbr"] in FAV for t in teams), "tv": ((c.get("broadcasts") or [{}])[0].get("names") or [""])[0]})
    games.sort(key=lambda g: (not g["fav"], g["state"] != "in", g["date"] or ""))
    st = standings()
    cards = team_cards()
    for c in cards:
        d = st.get(c["abbr"])
        if d:
            c["division"] = d["division"]; c["rank"] = d["rank"]; c["divisionSize"] = len(d["rows"])
            me = next((r for r in d["rows"] if r["abbr"] == c["abbr"]), None)
            if me and me.get("w") is not None: c["record"] = f"{me['w']}-{me['l']}"
    return {"at": NOW.isoformat(), "fav": FAV, "games": games, "teams": cards, "standings": st}


def main():
    out = {"at": NOW.isoformat(), "day": DAY_START.astimezone(TZ).strftime("%Y-%m-%d"), "sites": {}}
    for biz in ("atavia", "es"):
        try:
            out["sites"][biz] = collect(biz)
            r = out["sites"][biz]
            print(f"{biz}: online {r.get('online')} - today {r.get('today')} visitors, {r.get('views')} views")
        except Exception as e:
            out["sites"][biz] = {"error": f"{type(e).__name__}: {str(e)[:120]}"}
            print(f"{biz}: FAILED {e}")
    sp = sports()
    print(f"sports: {len(sp['games'])} games, {sum(1 for g in sp['games'] if g['fav'])} for the favourites")
    if "--dry-run" in sys.argv:
        print(json.dumps(out, indent=1)); return
    key = open(os.path.join(HERE, ".hub-key")).read().strip()
    r = subprocess.run(["curl", "-s", "-X", "POST", "-H", "content-type: application/json", "-H", f"x-hub-key: {key}", "--data-binary", "@-", HUB + "/api/state"],
                       input=json.dumps({"traffic": out, "sports": sp}), capture_output=True, text=True, timeout=60)
    print("posted:", r.stdout.strip() or r.stderr.strip())


if __name__ == "__main__":
    main()
