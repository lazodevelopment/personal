#!/usr/bin/env python3
r"""
split_sitemap.py - one-time sitemap shard fix for meetlazo.com
Reads dist/sitemap.xml (87k+ URLs), writes:
  dist/sitemap-1.xml, sitemap-2.xml  (<=45,000 URLs each)
  dist/sitemap.xml                   (sitemap index pointing at the shards)
Run from C:\Users\kurvh\lazo-directory:
    python split_sitemap.py
Then sync to R2:
    python deploy\upload_r2.py
No Firestore reads. No rebuild. Safe to run repeatedly.
"""
import re, html, datetime, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
DIST = ROOT / "dist"
BASE_URL = "https://meetlazo.com"
CHUNK = 45000  # headroom under the 50,000 protocol cap

src = (DIST / "sitemap.xml").read_text(encoding="utf-8")
urls = re.findall(r"<loc>(.*?)</loc>", src)
# If already an index (contains <sitemapindex>), pull URLs from existing shards instead
if "<sitemapindex" in src:
    urls = []
    for shard in sorted(DIST.glob("sitemap-*.xml")):
        urls += re.findall(r"<loc>(.*?)</loc>", shard.read_text(encoding="utf-8"))
urls = [html.unescape(u) for u in urls]
print(f"URLs found: {len(urls)}")
assert len(urls) > 50000, "fewer than 50k URLs - splitting not needed?"

today = datetime.date.today().isoformat()
shards = [urls[i:i+CHUNK] for i in range(0, len(urls), CHUNK)]
for n, chunk in enumerate(shards, 1):
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sm += [f"<url><loc>{html.escape(u)}</loc></url>" for u in chunk]
    sm.append("</urlset>")
    (DIST / f"sitemap-{n}.xml").write_text("\n".join(sm), encoding="utf-8")
    print(f"wrote sitemap-{n}.xml ({len(chunk)} URLs)")

idx = ['<?xml version="1.0" encoding="UTF-8"?>',
       '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
idx += [f"<sitemap><loc>{BASE_URL}/sitemap-{n}.xml</loc><lastmod>{today}</lastmod></sitemap>"
        for n in range(1, len(shards)+1)]
idx.append("</sitemapindex>")
(DIST / "sitemap.xml").write_text("\n".join(idx), encoding="utf-8")
print(f"wrote sitemap.xml as index of {len(shards)} shards - done")
