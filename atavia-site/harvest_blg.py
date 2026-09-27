"""Harvest all BabyLoveGrowth articles -> _src/posts/*.md + _blg_archive/*.json
Usage:  python harvest_blg.py YOUR_API_KEY     (run from the atavia-site folder)
Stdlib only - no pip installs needed."""
import sys, json, re, pathlib, urllib.request, time

if len(sys.argv) < 2:
    sys.exit("usage: python harvest_blg.py YOUR_API_KEY")
KEY = sys.argv[1].strip()
BASE = "https://api.babylovegrowth.ai/api/integrations/v1/articles"

def get(url):
    req = urllib.request.Request(url, headers={
        "X-API-Key": KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))

posts_dir = pathlib.Path("_src/posts"); posts_dir.mkdir(parents=True, exist_ok=True)
raw_dir = pathlib.Path("_blg_archive"); raw_dir.mkdir(exist_ok=True)

def slugsafe(s):
    s = re.sub(r"[^a-z0-9-]", "-", (s or "post").lower())
    return re.sub(r"-{2,}", "-", s).strip("-") or "post"

# 1) list everything (paginated)
articles, offset = [], 0
while True:
    batch = get("%s?limit=50&offset=%d" % (BASE, offset))
    if not batch: break
    articles.extend(batch)
    if len(batch) < 50: break
    offset += 50
print("found %d articles" % len(articles))

# 2) fetch full content for each, archive + convert
manifest = []
for i, a in enumerate(articles, 1):
    try:
        full = get("%s/%s" % (BASE, a["id"]))
    except Exception as e:
        print("  !! id %s failed: %s" % (a.get("id"), e)); continue
    slug = slugsafe(full.get("slug") or full.get("title"))
    date = (full.get("created_at") or "")[:10] or "undated"
    (raw_dir / ("%s-%s.json" % (date, slug))).write_text(
        json.dumps(full, indent=2), encoding="utf-8")
    md = full.get("content_markdown") or ""
    fm = "\n".join([
        "---",
        "title: %s" % json.dumps(full.get("title") or slug),
        "slug: %s" % slug,
        "date: %s" % date,
        "description: %s" % json.dumps(full.get("meta_description") or ""),
        "hero: %s" % (full.get("hero_image_url") or ""),
        "seed: %s" % json.dumps(full.get("seedKeyword") or ""),
        "keywords: %s" % json.dumps(full.get("keywords") or []),
        "source: babylovegrowth",
        "status: review   # change to publish after your edit pass",
        "---", "", ""])
    (posts_dir / ("%s-%s.md" % (date, slug))).write_text(fm + md, encoding="utf-8")
    manifest.append((date, slug, (full.get("title") or "")[:60]))
    print("  [%2d/%d] %s  %s" % (i, len(articles), date, slug))
    time.sleep(0.4)  # be polite, avoid rate limits

print("\n=== MANIFEST (%d saved) ===" % len(manifest))
for d, s, t in sorted(manifest):
    print("  %s  /blog/%s  %s" % (d, s, t))
print("\nmarkdown -> _src/posts/   raw json -> _blg_archive/")
