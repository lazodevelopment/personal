"""JARVIS watch collector: balance charges, social posting, Search Console.

Every 15 minutes (Task Scheduler "JARVIS watch") this posts one `watch` snapshot to the hub:
  payments  Atavia and Elizabeth Scott balance charges due in the last 7 / next 7 days, with outcome
            (charged, failed with the error, payment link sent, due soon), read from each booking.
  social    whether each of the seven brands posted today, from the posting logs the daily
            social tasks write (jovi-social/posted.json, brand-social/<brand>/posted.json).
  search    Google Search Console daily clicks and impressions for every property the
            LeaseReputation service account can read (refreshed every 3 hours, cached between runs).
The hub turns these into alerts and push notifications (failed charge, missed post, search drop).
"""
import json, os, sys, subprocess, time, warnings
import datetime as dt
from zoneinfo import ZoneInfo
warnings.filterwarnings("ignore", message=".*without a quota project.*")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from collect_metrics import client_for, ts, num

HUB = "https://jarvis-hub.floral-credit-e4f0.workers.dev"
KEY = open(os.path.join(HERE, ".hub-key")).read().strip()


def hub_tz():
    try:
        r = subprocess.run(["curl", "-s", "-m", "15", "-H", f"x-hub-key: {KEY}", HUB + "/api/config"], capture_output=True, text=True, timeout=20)
        return json.loads(r.stdout).get("tz") or "America/Chicago"
    except Exception:
        return "America/Chicago"


TZ = ZoneInfo(hub_tz())
NOW = dt.datetime.now(dt.timezone.utc)
TODAY = dt.datetime.now(TZ).date()


# ---------------- balance charges ----------------
def payments():
    out = []
    for biz in ("atavia", "es"):
        try:
            db = client_for(biz)
            from google.cloud.firestore_v1.base_query import FieldFilter
            q = (db.collection("bookings")
                 .where(filter=FieldFilter("balance_due_at", ">=", NOW - dt.timedelta(days=7)))
                 .where(filter=FieldFilter("balance_due_at", "<=", NOW + dt.timedelta(days=7))))
            for s in q.stream():
                b = s.to_dict() or {}
                if b.get("test_mode") or str(b.get("status", "")).startswith(("abandoned", "cancel")):
                    continue
                due, paid = ts(b.get("balance_due_at")), ts(b.get("balance_paid_at"))
                attempts = int(b.get("balance_attempts") or 0)
                if paid: state = "charged"
                elif attempts and b.get("balance_last_error"): state = "failed"
                elif b.get("balance_payment_link_id"): state = "link_sent"
                elif due and due <= NOW: state = "due_now"
                else: state = "upcoming"
                out.append({"business": biz, "id": b.get("booking_id") or s.id, "names": b.get("client_names") or b.get("email") or s.id,
                            "amount": num(b.get("balance")), "due": due.isoformat() if due else None, "paid": paid.isoformat() if paid else None,
                            "state": state, "attempts": attempts, "error": str(b.get("balance_last_error") or "")[:200],
                            "card": bool(b.get("zoho_payment_method_id")), "event": str(b.get("event_date") or "")})
        except Exception as e:
            out.append({"business": biz, "error": str(e)[:160]})
            print(f"payments {biz}: {str(e)[:160]}")
    out.sort(key=lambda x: x.get("due") or "")
    return out


# ---------------- social posting ----------------
SOCIAL = [
    ("jovi", "Jovi Health", r"C:\Users\kurvh\jovi-social\posted.json"),
    ("atavia", "Atavia", r"C:\Users\kurvh\brand-social\atavia\posted.json"),
    ("elizabethscott", "Elizabeth Scott", r"C:\Users\kurvh\brand-social\elizabethscott\posted.json"),
    ("trylazo", "Lazo", r"C:\Users\kurvh\brand-social\trylazo\posted.json"),
    ("lazovendors", "Lazo Vendors", r"C:\Users\kurvh\brand-social\lazovendors\posted.json"),
    ("roven", "Roven", r"C:\Users\kurvh\brand-social\roven\posted.json"),
    ("leasereputation", "LeaseReputation", r"C:\Users\kurvh\brand-social\leasereputation\posted.json"),
]


def social():
    out = []
    for key, name, path in SOCIAL:
        try:
            d = json.load(open(path, encoding="utf-8"))
            rows = d.get("posted", []) if isinstance(d, dict) else d
            last = rows[-1] if rows else {}
            days = sorted({str(r.get("at", ""))[:10] for r in rows if r.get("at")})
            out.append({"brand": key, "name": name, "last": str(last.get("at", ""))[:10] or None, "today": str(TODAY) in days,
                        "total": len(rows), "linkedin": bool(last.get("linkedin_urn")), "slug": last.get("slug") or last.get("image") or ""})
        except FileNotFoundError:
            out.append({"brand": key, "name": name, "last": None, "today": False, "total": 0, "error": "no posting log yet"})
        except Exception as e:
            out.append({"brand": key, "name": name, "last": None, "today": False, "total": 0, "error": str(e)[:120]})
    return {"day": str(TODAY), "brands": out}


# ---------------- Search Console ----------------
GSC_KEY = r"C:\Users\kurvh\lease-reputation\serviceAccountKey.json"
GSC_CACHE = os.path.join(HERE, ".gsc_cache.json")
GSC_EVERY = 3 * 3600


def search():
    try:
        cache = json.load(open(GSC_CACHE))
        if time.time() - cache.get("t", 0) < GSC_EVERY: return cache["v"]
    except Exception:
        cache = {}
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    scopes = ["https://www.googleapis.com/auth/webmasters.readonly"]
    if os.path.exists(GSC_KEY):
        creds = service_account.Credentials.from_service_account_file(GSC_KEY, scopes=scopes)
    else:  # cloud feeder: the VM's own service account (its access scopes include webmasters.readonly)
        import google.auth
        from google.auth.transport.requests import Request
        creds, _ = google.auth.default(scopes=scopes); creds.refresh(Request())
    who = getattr(creds, "service_account_email", "this machine's account")
    s = AuthorizedSession(creds)
    v = {"at": NOW.isoformat(), "account": who, "sites": []}
    r = s.get("https://searchconsole.googleapis.com/webmasters/v3/sites", timeout=30)
    if r.status_code != 200:
        msg = r.json().get("error", {}).get("message", r.text[:200]) if r.headers.get("content-type", "").startswith("application/json") else r.text[:200]
        v["error"] = msg[:300]
        link = (__import__("re").search(r"https://console\.developers\.google\.com/apis/api/searchconsole\.googleapis\.com/overview\?project=\d+", msg) or [None])[0]
        v["fix"] = (f"Turn on the Search Console API for {who.split('@')[-1].split('.')[0]}: {link or 'https://console.cloud.google.com/apis/library/searchconsole.googleapis.com'}"
                    if "has not been used" in msg or "disabled" in msg else f"Add {who} as a user (Restricted is enough) in Search Console, Settings, Users and permissions, for each property.")
    else:
        sites = [x["siteUrl"] for x in r.json().get("siteEntry", []) if x.get("permissionLevel") != "siteUnverifiedUser"]
        if not sites:
            v["fix"] = f"Add {who} as a user (Restricted is enough) in Search Console, Settings, Users and permissions, for leasereputation.com and ataviaweddings.com."
        end = dt.date.today() - dt.timedelta(days=1); start = end - dt.timedelta(days=41)
        for site in sites:
            try:
                q = s.post(f"https://searchconsole.googleapis.com/webmasters/v3/sites/{__import__('urllib.parse').parse.quote(site, safe='')}/searchAnalytics/query",
                           json={"startDate": str(start), "endDate": str(end), "dimensions": ["date"], "rowLimit": 100}, timeout=60)
                rows = [[x["keys"][0], int(x["clicks"]), int(x["impressions"])] for x in q.json().get("rows", [])]
                tq = s.post(f"https://searchconsole.googleapis.com/webmasters/v3/sites/{__import__('urllib.parse').parse.quote(site, safe='')}/searchAnalytics/query",
                            json={"startDate": str(end - dt.timedelta(days=6)), "endDate": str(end), "dimensions": ["query"], "rowLimit": 5}, timeout=60)
                top = [[x["keys"][0], int(x["clicks"]), int(x["impressions"])] for x in tq.json().get("rows", [])]
                v["sites"].append({"site": site, "days": rows, "top": top})
            except Exception as e:
                v["sites"].append({"site": site, "error": str(e)[:160]})
    if not v.get("error") and v["sites"]: json.dump({"t": time.time(), "v": v}, open(GSC_CACHE, "w"))  # retry setup problems every run
    return v


def ios_listings():
    """App Store listings the hub watches (Apple's lookup API refuses Cloudflare, so the PC reads them)."""
    import urllib.request, urllib.parse
    r = subprocess.run(["curl", "-s", "-m", "20", "-H", f"x-hub-key: {KEY}", HUB + "/api/apps/targets"], capture_output=True, text=True, timeout=30)
    out = {}
    for a in json.loads(r.stdout or "[]"):
        ios = a.get("ios") or {}
        try:
            if ios.get("id"): u = f"https://itunes.apple.com/lookup?id={ios['id']}&country=us"
            elif ios.get("bundle"): u = f"https://itunes.apple.com/lookup?bundleId={urllib.parse.quote(ios['bundle'])}&country=us"
            else: u = f"https://itunes.apple.com/search?term={urllib.parse.quote(ios['search'])}&entity=software&country=us&limit=25"
            j = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (JARVIS hub)"}), timeout=20))
            want = (ios.get("search") or "").lower()
            hit = next((x for x in j.get("results", []) if not want or want in (x.get("trackName", "") + " " + x.get("sellerName", "")).lower()), None)
            out[a["key"]] = {"listed": True, "version": hit.get("version"), "released": hit.get("currentVersionReleaseDate"), "url": hit.get("trackViewUrl")} if hit else {"listed": False}
        except Exception as e:
            out[a["key"]] = {"error": str(e)[:120]}
    return out


def main():
    out = {"at": NOW.isoformat(), "day": str(TODAY)}
    # --only social   (the PC, where the posting logs live)   --only payments,search,ios   (the cloud feeder)
    only = next((a.split("=", 1)[1] if "=" in a else sys.argv[sys.argv.index(a) + 1] for a in sys.argv if a.startswith("--only")), "")
    parts = (("payments", payments), ("social", social), ("search", search), ("ios", ios_listings))
    if only: parts = tuple(x for x in parts if x[0] in only.split(","))
    for name, fn in parts:
        try:
            out[name] = fn()
        except Exception as e:
            out[name] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
    pay = out.get("payments") if isinstance(out.get("payments"), list) else []
    soc = out.get("social") if isinstance(out.get("social"), dict) else {}
    sc = out.get("search") if isinstance(out.get("search"), dict) else {}
    print(NOW.isoformat()[:16], f"payments {len(pay)}", "social", sum(1 for b in soc.get("brands", []) if b.get("today")), "/ 7 today",
          "search", len(sc.get("sites", [])), sc.get("error", "")[:80])
    if "--dry-run" in sys.argv:
        print(json.dumps(out, indent=1)[:4000]); return
    r = subprocess.run(["curl", "-s", "-m", "60", "-X", "POST", "-H", "content-type: application/json", "-H", f"x-hub-key: {KEY}", "--data-binary", "@-", HUB + "/api/state"],
                       input=json.dumps({"watch": out}), capture_output=True, text=True, timeout=70)
    print("posted:", r.stdout.strip() or r.stderr.strip())


if __name__ == "__main__":
    main()
