"""indexnow.py - JC-LAZO-SEO-0921-002
Submit changed URLs to IndexNow (Bing, Yandex, DuckDuckGo, Naver, Seznam share
the feed). One POST per 10,000 URLs. Google does not use IndexNow; the sitemap
index covers Google.

  python deploy\\indexnow.py --since 2026-09-21        # every sitemap URL with lastmod >= date
  python deploy\\indexnow.py --prefix rochester        # every URL under meetlazo.com/rochester/
  python deploy\\indexnow.py --prefix rochester --prefix albany
  python deploy\\indexnow.py --urls https://meetlazo.com/ https://meetlazo.com/for-vendors/
  python deploy\\indexnow.py --dry-run --since today

Key: deploy/indexnow.key (created on first run, 32 hex chars). IndexNow verifies
ownership by fetching https://meetlazo.com/<key>.txt, so the key file is written
into dist/ every run and must be uploaded once:
  python deploy\\upload_r2.py --prefix <key>.txt
(the nightly rclone sync carries it too). deploy_site.py runs this with
--since today as step 6/6.
"""
import argparse, datetime as dt, json, re, secrets, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
HOST = "meetlazo.com"
KEY_FILE = ROOT / "deploy" / "indexnow.key"
ENDPOINT = "https://api.indexnow.org/indexnow"


def key():
    if not KEY_FILE.exists():
        KEY_FILE.write_text(secrets.token_hex(16), encoding="utf-8")
        print(f"  new IndexNow key written to {KEY_FILE}")
    k = KEY_FILE.read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"[a-f0-9]{32}", k):
        sys.exit("deploy/indexnow.key must be 32 hex characters")
    (DIST / f"{k}.txt").write_text(k, encoding="utf-8")  # ownership file, served at the root
    return k


def sitemap_urls():
    """(url, lastmod) for every URL in dist/sitemap-*.xml (lastmod may be '')."""
    out = []
    for f in sorted(DIST.glob("sitemap-*.xml")):
        s = f.read_text(encoding="utf-8")
        for m in re.finditer(r"<url>\s*<loc>([^<]+)</loc>(?:\s*<lastmod>([^<]*)</lastmod>)?", s):
            out.append((m.group(1).strip(), (m.group(2) or "").strip()[:10]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help="YYYY-MM-DD or 'today': URLs whose sitemap lastmod is on/after this date")
    ap.add_argument("--prefix", action="append", default=[], help="path prefix under the host, e.g. rochester")
    ap.add_argument("--urls", nargs="*", default=[], help="explicit URLs")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    k = key()
    urls = set(a.urls)
    if a.since or a.prefix:
        since = dt.date.today().isoformat() if a.since == "today" else a.since
        prefixes = [f"https://{HOST}/{p.strip('/')}/" for p in a.prefix]
        for u, lm in sitemap_urls():
            if since and lm and lm >= since:
                urls.add(u)
            if prefixes and any(u.startswith(p) or u == p.rstrip("/") for p in prefixes):
                urls.add(u)
    urls = sorted(u for u in urls if u.startswith(f"https://{HOST}/"))
    if not urls:
        print("  nothing to submit"); return
    print(f"  {len(urls):,} url(s) to submit" + (" (dry run)" if a.dry_run else ""))
    if a.dry_run:
        for u in urls[:12]: print("   ", u)
        if len(urls) > 12: print(f"    ... and {len(urls) - 12:,} more")
        return
    ok = 0
    for i in range(0, len(urls), 10000):
        body = json.dumps({"host": HOST, "key": k, "keyLocation": f"https://{HOST}/{k}.txt",
                           "urlList": urls[i:i + 10000]}).encode("utf-8")
        req = urllib.request.Request(ENDPOINT, data=body, method="POST",
                                     headers={"Content-Type": "application/json; charset=utf-8"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                code = r.status
        except urllib.error.HTTPError as e:
            code = e.code
            print(f"  batch {i // 10000 + 1}: HTTP {code} {e.read()[:200]!r}")
            continue
        except Exception as e:  # noqa: BLE001
            print(f"  batch {i // 10000 + 1}: {type(e).__name__}: {e}")
            continue
        ok += len(urls[i:i + 10000])
        print(f"  batch {i // 10000 + 1}: HTTP {code} ({len(urls[i:i + 10000]):,} urls)")
    print(f"  submitted {ok:,}/{len(urls):,}")


if __name__ == "__main__":
    main()
