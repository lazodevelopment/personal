"""sync_dist.py - JC-LAZO-WWSEO-0919-006
Between nightly builds: copy wedding-websites/ (hub, 13 template demos, style
and intent pages) into dist/, put every URL in dist/sitemap-templates.xml, point the
sitemap index at /sitemap-couples.xml, and seed generate/lastmod_cache.json so
tonight's build keeps today's lastmod. Then upload:

  python wedding-websites\\sync_dist.py
  python deploy\\upload_r2.py --prefix wedding-websites
  python deploy\\upload_r2.py --prefix sitemap

build.py does the same copy on every full build (JC-LAZO-WWSEO-0919-004).
"""
import datetime, hashlib, json, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST, SRC = ROOT / "dist", ROOT / "wedding-websites"
BASE = "https://meetlazo.com"

dst = DIST / "wedding-websites"
dst.mkdir(exist_ok=True)
shutil.copy2(SRC / "index.html", dst / "index.html")
slugs = sorted(p.name for p in SRC.iterdir() if p.is_dir() and not p.name.startswith("_") and (p / "index.html").exists())
for s in slugs:
    (dst / s).mkdir(exist_ok=True)
    shutil.copy2(SRC / s / "index.html", dst / s / "index.html")
urls = [f"{BASE}/wedding-websites/"] + [f"{BASE}/wedding-websites/{s}/" for s in slugs]

today = datetime.date.today().isoformat()
cache_file = ROOT / "generate" / "lastmod_cache.json"
try:
    cache = json.loads(cache_file.read_text(encoding="utf-8"))
except Exception:
    cache = {}

sm = DIST / "sitemap-templates.xml"
# JC-LAZO-WWS-0929-PHOTOS: a fresh dist (before tonight's build) has no templates sitemap - start one
if not sm.exists():
    sm.write_text('<?xml version="1.0" encoding="UTF-8"?>' + chr(10) + '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + chr(10) + '</urlset>' + chr(10), encoding="utf-8")
t = sm.read_text(encoding="utf-8")
old = dict(re.findall(r"<url><loc>(https://meetlazo.com/wedding-websites/[^<]*)</loc><lastmod>([^<]*)</lastmod></url>\n", t))
t = re.sub(r"<url><loc>https://meetlazo.com/wedding-websites/[^<]*</loc>.*?</url>\n", "", t)
lines = []
for u in urls:
    rel = u[len(BASE) + 1:].strip("/")
    h = hashlib.sha1((DIST / rel / "index.html").read_bytes()).hexdigest()
    prev = cache.get(u)
    lm = prev[1] if prev and prev[0] == h else today   # unchanged file keeps its date
    cache[u] = [h, lm]
    lines.append(f"<url><loc>{u}</loc><lastmod>{lm}</lastmod></url>\n")
t = t.replace("</urlset>", "".join(lines) + "</urlset>")
sm.write_text(t, encoding="utf-8")
cache_file.write_text(json.dumps(cache), encoding="utf-8")

newest = max(cache[u][1] for u in urls)   # (was defined after its first use below)
idx = DIST / "sitemap.xml"
i = idx.read_text(encoding="utf-8")
if "sitemap-templates.xml" not in i:  # JC-LAZO-SEO-0922-001: tiered sitemaps; templates get their own
    i = i.replace("</sitemapindex>", f"<sitemap><loc>{BASE}/sitemap-templates.xml</loc><lastmod>{newest}</lastmod></sitemap>\n</sitemapindex>")
if "sitemap-couples" not in i:
    i = i.replace("</sitemapindex>", f"<sitemap><loc>{BASE}/sitemap-couples.xml</loc></sitemap>\n</sitemapindex>")
i = re.sub(r"(sitemap-3\.xml</loc><lastmod>)([^<]*)", lambda m: m.group(1) + max(m.group(2), newest), i)
idx.write_text(i, encoding="utf-8")
print(f"{len(slugs)} pages + hub copied to dist; {len(urls)} URLs in sitemap-templates.xml")
