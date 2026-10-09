"""patch_seo_appbanner1005.py - JC-LAZO-SEO-1005-APPBANNER
Search listing fixes after the 2026-10-05 Google / Bing / DuckDuckGo check:
Google indexes only the homepage, Bing and DDG rank lazo.wedding above us for
"lazo wedding app", and the app never shows under the brand result.

  1. Homepage <title> says what we are searched for: the app, free, planner,
     verified vendors. Was "Lazo - Wedding Vendors You Can Actually Trust"
     (the H1 keeps that line). og:title / twitter:title follow the title block.
  2. iOS Smart App Banner gets app-argument=<canonical URL> so Safari's banner
     opens the app on the page the visitor was reading, not just the store.
  3. The site manifest is finally linked from <head> (it was copied to
     /assets/site.webmanifest but nothing referenced it), its icon paths are
     fixed (/icon-*.png never existed; they live under /assets/), and it gains
     related_applications + prefer_related_applications so Chrome on Android
     offers the Play listing as the install banner and Google can tie the Play
     app to the domain.

Applies to generate/templates/home.html, generate/templates/base.html,
generate/static/site.webmanifest (tonight's build) and dist/index.html,
dist/app/index.html, dist/assets/site.webmanifest (live now). Idempotent.
  python generate\\patch_seo_appbanner1005.py
Then:
  python deploy\\upload_r2.py --prefix index.html --prefix app/index.html --prefix assets/site.webmanifest

Still manual (needs values only the consoles hold): /.well-known/assetlinks.json
wants the Play App Signing SHA-256 fingerprint (Play Console > Setup > App
signing) and /.well-known/apple-app-site-association wants the Apple Team ID.
Add both to config/ and this script can emit the files on the next pass.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "generate" / "templates"
STATIC = ROOT / "generate" / "static"
DIST = ROOT / "dist"

OLD_TITLE = "Lazo &mdash; Wedding Vendors You Can Actually Trust"
NEW_TITLE = "Lazo: Best Free Wedding Websites, Registry &amp; Planning Tools"  # JC-LAZO-SEO-1008

APP_ID = "6812863675"
PLAY_ID = "com.meetlazo.app"
OLD_LINK = '<link rel="manifest" href="/assets/site.webmanifest">'
# served as .json: the worker types .json as application/json today, while
# .webmanifest needs the TYPES entry added in this same change (worker redeploy).
MANIFEST_LINK = '<link rel="manifest" href="/assets/manifest.json">'


def patch(path: Path, fn):
    s = path.read_text(encoding="utf-8")
    t = fn(s)
    if t != s:
        path.write_text(t, encoding="utf-8", newline="\n")
        print(f"  patched {path.relative_to(ROOT)}")
    else:
        print(f"  ok      {path.relative_to(ROOT)}")


# -- 1. homepage title -------------------------------------------------------
def home_template(s):
    return s.replace("{% block title %}" + OLD_TITLE + "{% endblock %}",
                     "{% block title %}" + NEW_TITLE + "{% endblock %}")


def home_dist(s):
    s = s.replace("<title>" + OLD_TITLE + "</title>", "<title>" + NEW_TITLE + "</title>")
    for attr in ('property="og:title"', 'name="twitter:title"'):
        s = s.replace(f'<meta {attr} content="{OLD_TITLE}">', f'<meta {attr} content="{NEW_TITLE}">')
    return s


# -- 2 + 3. head: banner argument, manifest link ------------------------------
def head_template(s):
    s = s.replace(f'<meta name="apple-itunes-app" content="app-id={APP_ID}">',
                  f'<meta name="apple-itunes-app" content="app-id={APP_ID}, app-argument={{{{ self.canonical() }}}}">')
    s = s.replace(OLD_LINK, MANIFEST_LINK)
    if MANIFEST_LINK not in s:
        s = s.replace('<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">',
                      '<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">\n' + MANIFEST_LINK)
    return s


def head_dist(s):
    m = re.search(r'<link rel="canonical" href="([^"]+)">', s)
    if not m:
        sys.exit("no canonical link found; refusing to guess the banner argument")
    canonical = m.group(1)
    s = s.replace(f'<meta name="apple-itunes-app" content="app-id={APP_ID}">',
                  f'<meta name="apple-itunes-app" content="app-id={APP_ID}, app-argument={canonical}">')
    s = s.replace(OLD_LINK, MANIFEST_LINK)
    if MANIFEST_LINK not in s:
        s = s.replace('<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">',
                      '<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">\n' + MANIFEST_LINK)
    return s


# -- 3. manifest -------------------------------------------------------------
def manifest(s):
    m = json.loads(s)
    m["name"] = "Lazo: Wedding Planner"
    m["short_name"] = "Lazo"
    m["description"] = ("Free wedding planner app with verified vendors, real reviews from couples who booked, "
                        "and June, an AI planner. Guest list, budget, seating and a wedding website.")
    m["id"] = "/"
    m["start_url"] = "/"
    m["scope"] = "/"
    m["icons"] = [
        {"src": "/assets/icon-192.png", "sizes": "192x192", "type": "image/png"},
        {"src": "/assets/icon-512.png", "sizes": "512x512", "type": "image/png"},
    ]
    m["related_applications"] = [
        {"platform": "play", "id": PLAY_ID,
         "url": f"https://play.google.com/store/apps/details?id={PLAY_ID}"},
        {"platform": "itunes", "id": APP_ID,
         "url": f"https://apps.apple.com/us/app/lazo-wedding-planner/id{APP_ID}"},
    ]
    m["prefer_related_applications"] = True
    return json.dumps(m, indent=2) + "\n"


def main():
    print("templates")
    patch(TPL / "home.html", home_template)
    patch(TPL / "base.html", head_template)
    patch(STATIC / "site.webmanifest", manifest)
    write_json_copy(STATIC / "manifest.json")
    print("dist (live)")
    patch(DIST / "index.html", lambda s: head_dist(home_dist(s)))
    patch(DIST / "app" / "index.html", head_dist)
    patch(DIST / "assets" / "site.webmanifest", manifest)
    write_json_copy(DIST / "assets" / "manifest.json")


def write_json_copy(path: Path):
    """The linked copy. Same content as site.webmanifest, .json extension so the
    worker serves it as application/json without a redeploy."""
    body = manifest("{}")
    if path.exists() and path.read_text(encoding="utf-8") == body:
        print(f"  ok      {path.relative_to(ROOT)}")
        return
    path.write_text(body, encoding="utf-8", newline="\n")
    print(f"  wrote   {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
