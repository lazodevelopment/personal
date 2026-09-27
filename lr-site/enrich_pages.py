#!/usr/bin/env python3
"""
LeaseReputation -- enrich_pages.py

Adds a "Contact & details" card (phone, website, Google Maps link, Google's
formatted address) to each community/<slug>.html using the lr-photo-proxy
worker's place-details endpoint:

    https://photos.leasereputation.com/api/place/{place_id}
    -> {"name","address","phone","website","mapsUrl"}   or   {"error":"unavailable"}

Runs AFTER generate_community_pages.py and BEFORE kv_sync.py.

  * Idempotent: a page that already carries <!-- lr-details:start --> is skipped.
  * The generator carries the lr-details block across nightly rebuilds, so a
    page only needs enriching once (details also cached in the ledger, so a
    lost block is re-injected without another API call).
  * Failed / stale place IDs go in the ledger and are skipped for 30 days.
  * Default trickle: 1,000 new API lookups per run (--limit N, --all).

The card is written between DETAILS markers, NOT ENRICH markers: Google data
does not make a page "rich" for indexing (see INDEX TIERING in the generator).
Hand-curated content goes in community/curated/<slug>.html instead.

Usage:  python enrich_pages.py [--limit 1000] [--all] [--dry-run] [--sleep 0.05]
"""

import os
import re
import sys
import json
import time
import html
import argparse
import datetime
import urllib.request
import urllib.error
import urllib.parse

BASE = os.path.dirname(os.path.abspath(__file__))
COMMUNITY_DIR = os.path.join(BASE, "community")
LEDGER_PATH = os.path.join(BASE, "enrich_ledger.json")
API = "https://photos.leasereputation.com/api/place/"

DETAILS_START = "<!-- lr-details:start -->"
DETAILS_END = "<!-- lr-details:end -->"
FAIL_RETRY_DAYS = 30
BREAKER_FAILS = 25      # consecutive failures that mean "the endpoint is down, stop"

PID_RE = re.compile(r"claimCommunity\?communityId=([A-Za-z0-9_\-]+)")
# End of the About card: the facts grid's closing div followed by the card's closing div.
ANCHOR_RE = re.compile(r'(<div class="facts">.*?</div>\s*</div>)', re.S)


def esc(s):
    return html.escape(str(s or ""), quote=True)


def load_ledger():
    try:
        with open(LEDGER_PATH, encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def save_ledger(ledger):
    tmp = LEDGER_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=0, ensure_ascii=False)
    os.replace(tmp, LEDGER_PATH)


def fetch_details(pid):
    """Returns (dict, None) on success, (None, reason) on failure."""
    try:
        req = urllib.request.Request(API + pid, headers={"User-Agent": "lr-enrich/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code in (404, 502):
            return None, "unavailable"
        return None, "http-%d" % e.code
    except Exception as e:
        return None, "error:" + str(e)[:80]
    if not isinstance(data, dict) or data.get("error"):
        return None, str((data or {}).get("error") or "bad-response")
    if not (data.get("phone") or data.get("website") or data.get("mapsUrl")):
        return None, "empty"
    return data, None


def clean_site(url):
    """Google's website URLs carry utm/rccustomid junk -- keep scheme+host+path."""
    try:
        u = urllib.parse.urlsplit(url)
        host = u.netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        path = u.path if u.path not in ("", "/") else ""
        return u.scheme + "://" + u.netloc + path, host
    except Exception:
        return url, url


def card_html(name, d):
    rows = []
    addr = str(d.get("address") or "").strip()
    if addr.endswith(", USA"):
        addr = addr[:-5]
    if addr:
        rows.append('<div class="fact"><div class="k">Address</div><div class="v">'
                    + esc(addr) + "</div></div>")
    phone = str(d.get("phone") or "").strip()
    if phone:
        tel = re.sub(r"[^0-9+]", "", phone)
        rows.append('<div class="fact"><div class="k">Leasing office</div><div class="v">'
                    '<a href="tel:' + esc(tel) + '">' + esc(phone) + "</a></div></div>")
    site = str(d.get("website") or "").strip()
    if site:
        href, host = clean_site(site)
        rows.append('<div class="fact"><div class="k">Website</div><div class="v">'
                    '<a href="' + esc(href) + '" rel="nofollow noopener" target="_blank">'
                    + esc(host) + "</a></div></div>")
    maps = str(d.get("mapsUrl") or "").strip()
    if maps:
        rows.append('<div class="fact"><div class="k">Map</div><div class="v">'
                    '<a href="' + esc(maps) + '" rel="nofollow noopener" target="_blank">'
                    "Open in Google Maps</a></div></div>")
    if not rows:
        return ""
    return (DETAILS_START + '\n  <div class="card"><h2>Contact &amp; details for '
            + esc(name) + '</h2><div class="facts">' + "".join(rows)
            + '</div><p class="vid-cap">Contact details via Google. Reviews and the '
            'Reputation Score come only from verified residents.</p></div>\n  '
            + DETAILS_END)


def page_name(src):
    m = re.search(r"<h2>About (.*?)</h2>", src)
    return html.unescape(m.group(1)) if m else "this community"


def inject(src, card):
    m = ANCHOR_RE.search(src)
    if not m:
        return None
    return src[:m.end()] + "\n\n  " + card + src[m.end():]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=1000, help="max new API lookups this run")
    ap.add_argument("--all", action="store_true", help="no lookup limit")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sleep", type=float, default=0.05, help="seconds between API calls")
    args = ap.parse_args()

    if not os.path.isdir(COMMUNITY_DIR):
        print("! community/ not found next to this script")
        sys.exit(1)

    ledger = load_ledger()
    today = datetime.date.today()
    files = sorted(f for f in os.listdir(COMMUNITY_DIR) if f.endswith(".html")
                   and f != "index.html")

    n_skip_done = n_cached = n_fetched = n_failed = n_skip_failed = n_noanchor = n_nopid = 0
    lookups = 0
    # Circuit breaker: if the endpoint is down (API key rotated, quota,
    # worker error) every lookup comes back "unavailable". Don't burn 30-day
    # failure entries on that -- stop, drop this run's failures, exit 2.
    consecutive_fail = 0
    run_failed_pids = []
    endpoint_down = False
    t0 = time.time()
    for i, fn in enumerate(files):
        path = os.path.join(COMMUNITY_DIR, fn)
        try:
            src = open(path, encoding="utf-8").read()
        except Exception as e:
            print("  ! read failed " + fn + ": " + str(e))
            continue
        if DETAILS_START in src:
            n_skip_done += 1
            continue
        m = PID_RE.search(src)
        if not m:
            n_nopid += 1
            continue
        pid = m.group(1)
        entry = ledger.get(pid) or {}

        details = None
        if entry.get("status") == "ok" and isinstance(entry.get("data"), dict):
            details = entry["data"]
            n_cached += 1
        else:
            if entry.get("status") == "failed":
                try:
                    last = datetime.date.fromisoformat(entry.get("ts", "1970-01-01"))
                except Exception:
                    last = datetime.date(1970, 1, 1)
                if (today - last).days < FAIL_RETRY_DAYS:
                    n_skip_failed += 1
                    continue
            if not args.all and lookups >= args.limit:
                continue
            lookups += 1
            details, why = fetch_details(pid)
            time.sleep(args.sleep)
            if details is None:
                n_failed += 1
                consecutive_fail += 1
                run_failed_pids.append(pid)
                ledger[pid] = {"status": "failed", "ts": today.isoformat(), "why": why}
                if consecutive_fail >= BREAKER_FAILS:
                    endpoint_down = True
                    break
                continue
            consecutive_fail = 0
            n_fetched += 1
            ledger[pid] = {"status": "ok", "ts": today.isoformat(), "data": {
                "address": details.get("address"), "phone": details.get("phone"),
                "website": details.get("website"), "mapsUrl": details.get("mapsUrl")}}

        card = card_html(page_name(src), details)
        if not card:
            continue
        out = inject(src, card)
        if out is None:
            n_noanchor += 1
            continue
        if not args.dry_run:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(out)
        if (n_fetched + n_cached) % 100 == 0:
            print("  .. %d/%d pages, %d lookups, %.0fs" % (i + 1, len(files), lookups, time.time() - t0))
            if not args.dry_run:
                save_ledger(ledger)

    if endpoint_down:
        for pid in run_failed_pids:
            ledger.pop(pid, None)
        n_failed = 0
    if not args.dry_run:
        save_ledger(ledger)
    print("enrich_pages: %d pages scanned" % len(files))
    print("  already enriched: %d | injected from cache: %d | new lookups ok: %d"
          % (n_skip_done, n_cached, n_fetched))
    print("  lookups failed (unavailable/stale id): %d | skipped (failed <%dd ago): %d"
          % (n_failed, FAIL_RETRY_DAYS, n_skip_failed))
    if n_noanchor or n_nopid:
        print("  ! no About-card anchor: %d | no place_id: %d" % (n_noanchor, n_nopid))
    if args.dry_run:
        print("  (dry run -- nothing written)")
    if endpoint_down:
        print("  !! %d consecutive lookups failed -- %s looks DOWN (Places API key rotated? "
              "worker secret stale? quota?). This run's failures were NOT recorded. "
              "Fix the worker, then re-run." % (BREAKER_FAILS, API))
        sys.exit(2)


if __name__ == "__main__":
    main()
