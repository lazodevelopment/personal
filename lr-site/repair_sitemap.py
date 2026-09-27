# repair_sitemap.py — rebuilds sitemap.xml from the page files already on
# disk (community/, apartments/, management/) and restores the homepage
# community counter. Needs NO Google access — pure local file operations.
#
# Run from the marketing site folder:
#   python repair_sitemap.py
# then deploy:
#   wrangler pages deploy . --project-name=leasereputation

import os
import re
import datetime

SITE = "https://leasereputation.com"
base = os.path.dirname(os.path.abspath(__file__))
today = datetime.date.today().isoformat()

urls = []
core = ["", "privacy.html", "terms.html", "cookies.html",
        "community-guidelines.html", "contact.html", "accessibility.html",
        "community/"]
for p in core:
    urls.append((f"{SITE}/{p}", "monthly"))

# Community pages from disk
comm = os.path.join(base, "community")
n_comm = 0
for f in sorted(os.listdir(comm)):
    if f.endswith(".html") and f != "index.html":
        urls.append((f"{SITE}/community/{f}", "weekly"))
        n_comm += 1

# Guides (flat .html files in guides/)
g = os.path.join(base, "guides")
extra = 0
if os.path.isdir(g):
    if os.path.exists(os.path.join(g, "index.html")):
        urls.append((f"{SITE}/guides/", "monthly"))
        extra += 1
    for f in sorted(os.listdir(g)):
        if f.endswith(".html") and f != "index.html":
            urls.append((f"{SITE}/guides/{f}", "monthly"))
            extra += 1

# City + management pages from disk (directory-per-page layout)
for section in ["apartments", "management"]:
    d = os.path.join(base, section)
    if not os.path.isdir(d):
        continue
    if os.path.exists(os.path.join(d, "index.html")):
        urls.append((f"{SITE}/{section}/", "weekly"))
        extra += 1
    for sub in sorted(os.listdir(d)):
        if os.path.isdir(os.path.join(d, sub)) and \
           os.path.exists(os.path.join(d, sub, "index.html")):
            urls.append((f"{SITE}/{section}/{sub}/", "weekly"))
            extra += 1

body = "\n".join(
    f"  <url><loc>{loc}</loc><lastmod>{today}</lastmod>"
    f"<changefreq>{freq}</changefreq></url>"
    for loc, freq in urls)
sitemap = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + body + "\n</urlset>\n")
with open(os.path.join(base, "sitemap.xml"), "w", encoding="utf-8") as f:
    f.write(sitemap)
print(f"sitemap.xml rebuilt: {len(urls)} urls "
      f"({n_comm} community pages, {extra} city/management pages)")

# Homepage counter: restore from the real page count (community pages ==
# communities, minus nothing meaningful at this scale)
idx = os.path.join(base, "index.html")
if os.path.exists(idx):
    html = open(idx, encoding="utf-8").read()
    counter = "{:,}+".format((n_comm // 100) * 100)
    new_html, subs = re.subn(
        r'(<span id="community-count">)[^<]*(</span>)',
        r"\g<1>" + counter + r"\g<2>", html)
    if subs:
        open(idx, "w", encoding="utf-8").write(new_html)
        print(f"index.html counter restored -> {counter}")

print("\nNow deploy: wrangler pages deploy . --project-name=leasereputation")
