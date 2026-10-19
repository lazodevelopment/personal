"""outreach_daily.py - JC-LAZO-OUTREACH-1019: the claim campaign, every day, by itself.

Runs from Task Scheduler each morning (deploy/lazo-outreach-daily.bat). One Smartlead campaign (4176335) keeps
sending; this script feeds it and reads it back:

  1. sync   GET /campaigns/{id}/leads with emailStatus filters -> outreach/{vendorId}.status becomes
            bounced / replied / unsubscribed (those never get a second email); replies also go to a daily log
            so Jesse sees who answered.
  2. feed   pick the next slice of vendors from Firestore (status listed, focus states in order, score>=75,
            wedding sites only, one per website) and POST them to the campaign (<=400 per call), then mark
            them sent with today's batch id. Size = --per-day (default 1,500 = 30 boxes x 50).
  3. guard  stop feeding if the campaign's bounce rate since launch passes --max-bounce (3%) or the reply
            rate's share of "take it down" grows; it only logs, Smartlead's own auto-pause does the halting.

    python generate\\outreach_daily.py                 # sync + feed
    python generate\\outreach_daily.py --dry-run       # show what it would push, change nothing
    python generate\\outreach_daily.py --sync-only
    python generate\\outreach_daily.py --raise-limits  # once: every mailbox to 50/day, 10 min apart

Needs SMARTLEAD_API_KEY in lazo-directory/.env (Smartlead > Settings > API). Log: generate/data/outreach/_daily.log.
Order of states (Jesse, 2026-10-19): CO, TX, CA, FL, PA, IL, then New England; within a state, bigger metros first.
"""
import argparse, json, os, sys, time
from collections import defaultdict
from datetime import datetime, date
from pathlib import Path

import requests
from firebase_admin import firestore

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "generate"))
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass
from config.metros import METROS  # noqa: E402
import outreach_export as X  # noqa: E402  (pick(), CAT_* tables, client())

API = "https://server.smartlead.ai/api/v1"
CAMPAIGN = int(os.environ.get("SMARTLEAD_CAMPAIGN_ID") or 4176335)
KEY = os.environ.get("SMARTLEAD_API_KEY", "")
LOG = ROOT / "generate" / "data" / "outreach" / "_daily.log"
STATE_ORDER = ["CO", "TX", "CA", "FL", "PA", "IL", "MA", "CT", "ME", "NH", "VT", "RI"]
METRO_NAME = {m["id"]: m["name"] for m in METROS}
SITE, APP = "https://meetlazo.com/", "https://app.meetlazo.com/"


def log(msg):
    line = f"{datetime.now().isoformat(timespec='seconds')} {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def sl(method, path, **kw):
    """One Smartlead call; retries 429/5xx a few times."""
    url = f"{API}{path}"
    params = dict(kw.pop("params", {}) or {}); params["api_key"] = KEY
    for attempt in range(4):
        r = requests.request(method, url, params=params, timeout=60, **kw)
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(3 * (attempt + 1)); continue
        if not r.ok:
            raise RuntimeError(f"smartlead {method} {path} -> {r.status_code}: {r.text[:300]}")
        return r.json() if "json" in r.headers.get("content-type", "") else r.text
    raise RuntimeError(f"smartlead {method} {path}: gave up after retries ({r.status_code})")


# ---- 1. sync -----------------------------------------------------------------------------------------------------
def campaign_leads(email_status):
    out, offset = [], 0
    while True:
        j = sl("GET", f"/campaigns/{CAMPAIGN}/leads", params={"offset": offset, "limit": 100, "emailStatus": email_status})
        rows = j.get("data") or []
        out.extend(rows)
        if len(rows) < 100:
            return out
        offset += 100


def sync(db, dry):
    col = db.collection("outreach")
    changed = defaultdict(int)
    # terminal states win in this order; a reply after a bounce is impossible, an unsubscribe after a reply is honoured
    for status, flag in (("bounced", "is_bounced"), ("replied", "is_replied"), ("unsubscribed", "is_unsubscribed")):
        try:
            rows = campaign_leads(flag)
        except Exception as e:
            log(f"sync {flag}: {e}"); continue
        emails = {(r.get("lead") or {}).get("email", "").lower() for r in rows} - {""}
        if not emails:
            continue
        # outreach docs are keyed by vendorId; sendTo holds the address we mailed
        for chunk in [list(emails)[i:i + 30] for i in range(0, len(emails), 30)]:
            for d in col.where("sendTo", "in", chunk).stream():
                cur = d.get("status")
                if cur == status or cur in ("claimed", "removed") or (cur == "unsubscribed" and status != "unsubscribed"):
                    continue
                changed[status] += 1
                if not dry:
                    d.reference.set({"status": status, f"{status}At": firestore.SERVER_TIMESTAMP, "smartleadFlag": flag}, merge=True)
    if changed:
        log("sync: " + ", ".join(f"{k} {v}" for k, v in changed.items()))
    else:
        log("sync: nothing new")
    return changed


# ---- 2. feed -----------------------------------------------------------------------------------------------------
def next_slice(db, n, a):
    """[(doc, data, best-email)] - next vendors to mail, in state order, bigger metros first."""
    by_state = defaultdict(list)
    for m in METROS:
        by_state[m["state"]].append(m["id"])
    picked = []
    for st in STATE_ORDER:
        if len(picked) >= n:
            break
        metros = by_state.get(st, [])
        docs = []
        for mid in metros:
            docs += [(d, d.to_dict()) for d in db.collection("outreach").where("metroId", "==", mid).where("status", "==", "listed").stream()]
        if not docs:
            continue
        rows, _shared = X.pick(docs, a)
        # bigger metros first within the state
        size = defaultdict(int)
        for _, v, _ in rows:
            size[v["metroId"]] += 1
        rows.sort(key=lambda x: (-size[x[1]["metroId"]], -int(x[2].get("score") or 0)))
        take = rows[: n - len(picked)]
        picked += take
        log(f"feed: {st} has {len(rows):,} ready, taking {len(take)}")
    return picked[:n]


def to_lead(d, v, em):
    cat = (v.get("categories") or [""])[0]
    sing = X.CAT_SINGULAR.get(cat, "wedding vendor")
    tok = v["token"]
    return {"email": em["addr"], "first_name": "", "last_name": "", "company_name": v.get("name", ""), "website": v.get("website", ""),
            "custom_fields": {"metro": METRO_NAME.get(v.get("metroId"), v.get("metroId")), "category": cat, "category_singular": sing,
                              "category_singular_cap": sing[0].upper() + sing[1:], "category_plural": X.CAT_PLURAL.get(cat, "vendors"),
                              "site_host": v.get("siteHost") or "", "page_url": v.get("pageUrl", ""), "claim_url": f"{SITE}claim/{tok}",
                              "stop_url": f"{SITE}claim/{tok}/stop", "signup_url": f"{APP}?claim={d.id}", "vendor_id": d.id, "token": tok}}


def feed(db, n, a, dry):
    rows = next_slice(db, n, a)
    if not rows:
        log("feed: nothing left to send in the focus states"); return 0
    batch_id = f"{date.today().isoformat()}-auto"
    added = skipped = 0
    for i in range(0, len(rows), 400):
        chunk = rows[i:i + 400]
        leads = [to_lead(d, v, em) for d, v, em in chunk]
        if dry:
            log(f"feed (dry): would push {len(leads)} leads, first {leads[0]['email']} ({leads[0]['company_name']})"); added += len(leads); continue
        j = sl("POST", f"/campaigns/{CAMPAIGN}/leads", json={"lead_list": leads, "settings": {
            "ignore_global_block_list": False, "ignore_unsubscribe_list": False, "ignore_community_bounce_list": False,
            "ignore_duplicate_leads_in_other_campaign": False}})
        a_n, s_n = int(j.get("added_count") or 0), int(j.get("skipped_count") or 0)
        added += a_n; skipped += s_n
        skipped_emails = {str(x.get("email") if isinstance(x, dict) else x).lower() for x in (j.get("skipped_leads") or [])}
        wb = db.batch()
        for d, v, em in chunk:
            if em["addr"] in skipped_emails:
                wb.set(d.reference, {"status": "skipped", "skipWhy": "smartlead", "batch": batch_id}, merge=True)
            else:
                wb.set(d.reference, {"status": "sent", "batch": batch_id, "sendTo": em["addr"], "sentAt": firestore.SERVER_TIMESTAMP,
                                     "provider": "smartlead", "providerCampaignId": CAMPAIGN}, merge=True)
        wb.commit()
        log(f"feed: pushed {len(leads)} -> added {a_n}, skipped {s_n}")
    log(f"feed: batch {batch_id} done, {added} added, {skipped} skipped")
    return added


# ---- 3. guard ----------------------------------------------------------------------------------------------------
def guard(max_bounce):
    try:
        j = sl("GET", f"/campaigns/{CAMPAIGN}/analytics")
    except Exception as e:
        log(f"guard: analytics unavailable ({e}); feeding anyway"); return True
    sent = int(j.get("sent_count") or j.get("sent") or 0)
    bounced = int(j.get("bounce_count") or j.get("bounced") or 0)
    replied = int(j.get("reply_count") or j.get("replied") or 0)
    rate = bounced / sent if sent else 0
    log(f"guard: sent {sent:,}, bounced {bounced:,} ({rate:.1%}), replied {replied:,}")
    if sent >= 200 and rate > max_bounce:
        log(f"guard: bounce rate over {max_bounce:.0%}, NOT feeding today"); return False
    return True


def raise_limits(per_box, gap):
    j = sl("GET", "/email-accounts/", params={"offset": 0, "limit": 100})
    accts = j if isinstance(j, list) else (j.get("data") or j.get("email_accounts") or [])
    n = 0
    for a in accts:
        if str(a.get("from_email", "")).endswith("@meetlazo.com"):
            sl("POST", f"/email-accounts/{a['id']}", json={"max_email_per_day": per_box, "time_to_wait_in_mins": gap}); n += 1
    log(f"limits: {n} mailboxes set to {per_box}/day, {gap} min apart")
    try:
        j = sl("POST", f"/campaigns/{CAMPAIGN}/schedule", json={"schedule": {"timezone": "America/Phoenix", "days": [1, 2, 3, 4, 5],
              "start_hour": "08:00", "end_hour": "19:00", "min_time_btw_emails": gap, "max_new_leads_per_day": per_box * max(n, 1)}})
        log(f"limits: schedule updated: {str(j)[:160]}")
    except Exception as e:
        log(f"limits: schedule update failed ({e}); set New Leads/Day by hand in Smartlead > Settings > Schedule")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--per-day", type=int, default=1500)
    ap.add_argument("--min-score", type=int, default=75)
    ap.add_argument("--kind", action="append", choices=["own-domain", "free-mail", "other-domain"])
    ap.add_argument("--include-nowedding", action="store_true")
    ap.add_argument("--limit", type=int, default=0)   # X.pick signature
    ap.add_argument("--max-bounce", type=float, default=0.03)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sync-only", action="store_true")
    ap.add_argument("--raise-limits", action="store_true")
    ap.add_argument("--per-box", type=int, default=50)
    ap.add_argument("--gap", type=int, default=10)
    a = ap.parse_args()
    if not KEY:
        sys.exit("SMARTLEAD_API_KEY missing in .env (Smartlead > Settings > API Key)")
    log(f"--- run start (campaign {CAMPAIGN}, per-day {a.per_day}, dry={a.dry_run})")
    if a.raise_limits:
        raise_limits(a.per_box, a.gap); return
    db = X.client()
    sync(db, a.dry_run)
    if a.sync_only:
        return
    # Jesse switched the campaign to all seven days on 2026-10-19, so the feed runs every day too
    if guard(a.max_bounce):
        feed(db, a.per_day, a, a.dry_run)
    log("--- run end")


if __name__ == "__main__":
    main()
