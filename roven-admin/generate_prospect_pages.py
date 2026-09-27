#!/usr/bin/env python3
"""
generate_prospect_pages.py — Roven unclaimed business profile generator
=======================================================================
Reads the `prospects` collection and generates:

  /business/{metro_slug}/{name-slug}-{id6}.html   one page per business
  /business/{metro_slug}/index.html               metro directory
  /business/index.html                            metro hub
  /sitemap-business.xml                           sitemap for the whole layer

Pages are honest by design: real public facts (name, city, vertical, Google
rating with attribution), a clear NOT-YET-ON-ROVEN status, an educational
panel on what an accountability record shows, and a Claim CTA that prefills
the contact form. No accountability numbers are shown or implied for
unclaimed businesses.

USAGE
  python generate_prospect_pages.py --key serviceAccount.json --site C:\\Users\\kurvh\\roven-site
Then deploy the site as usual. Submit https://rovenhr.com/sitemap-business.xml
in Search Console once live.
"""

import argparse
import html
import os
import re
from datetime import datetime, timezone

import firebase_admin
from firebase_admin import credentials, firestore

SITE = "https://rovenhr.com"

HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canonical}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@500;600;700&family=Instrument+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="icon" type="image/x-icon" href="{root}favicon.ico">
<link rel="icon" type="image/png" sizes="32x32" href="{root}favicon-32.png">
<link rel="apple-touch-icon" href="{root}apple-touch-icon.png">
<link rel="stylesheet" href="{root}styles.css">
{jsonld}
</head>
<body>
<nav class="nav">
  <div class="wrap nav-inner">
    <a class="logo-link" href="{root}index.html" aria-label="Roven home"><img class="logo-img" src="{root}logo.png" alt="Roven" width="640" height="293"></a>
    <ul class="nav-links" id="navlinks" style="display:flex">
      <li><a href="{root}how-it-works.html">How it works</a></li>
      <li><a href="{root}employers.html">For employers</a></li>
      <li><a href="{root}about.html">About</a></li>
    </ul>
  </div>
</nav>
"""

FOOT = """<footer class="footer">
  <div class="wrap">
    <div class="footer-legal">
      <span>© 2026 ROVEN · ROVEN HR, LLC</span>
      <span>HIRING, PROVEN.</span>
    </div>
  </div>
</footer>
</body>
</html>"""


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s[:60] or "business"


def esc(s) -> str:
    return html.escape(str(s or ""))


def business_page(p: dict, root: str, siblings: list) -> str:
    name = esc(p["name"])
    metro = esc(p["metro"])
    state = esc(p["state"])
    city = esc(p.get("city") or p["metro"])
    vert = esc(p.get("verticalDisplay", ""))
    canonical = f"{SITE}/business/{p['metroSlug']}/{p['slug']}"
    rating = p.get("googleRating")
    reviews = p.get("googleReviewCount")

    jsonld = f"""<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "LocalBusiness",
  "name": "{name}",
  "address": {{"@type": "PostalAddress", "addressLocality": "{city}", "addressRegion": "{state}"}},
  "url": "{canonical}"
}}
</script>"""

    google_line = ""
    if rating:
        stars = f"{float(rating):.1f} ★"
        count = f" · {int(reviews):,} Google reviews" if reviews else ""
        google_line = f'<p class="biz-google">{stars}{count} <span style="opacity:.6">(rating on Google)</span></p>'

    claim_href = f"{root}contact.html?claim={html.escape(p['name'])}&metro={metro}"

    sib_cards = ""
    for s in siblings[:6]:
        sib_cards += f"""      <a class="biz-card" href="{s['slug']}.html"><h3>{esc(s['name'])}</h3><p>{esc(s.get('verticalDisplay',''))} · {esc(s.get('city') or s['metro'])}</p></a>\n"""

    body = f"""<header class="page-head">
  <div class="wrap">
    <p class="kicker">{vert} · {metro}, {state}</p>
    <h1>{name}</h1>
    <p class="biz-meta">{city}, {state}</p>
    {google_line}
    <span class="biz-status">⏳ NOT YET ON ROVEN — NO ACCOUNTABILITY RECORD</span>
  </div>
</header>
<section class="section">
  <div class="wrap prose">
    <h2>Hiring at {name}</h2>
    <p>{name} is a {vert.lower()} business in {city}, {state}. It has not yet joined Roven, the hiring marketplace where employers are identity-verified, every listing is a confirmed open role, and how applicants are treated is published as a public accountability record.</p>
    <p>Because {name} hasn't joined yet, there is no accountability record to show: no verified response rate, no median response time, no confirmed-open listings. That isn't a mark against them — it simply means their hiring behavior isn't measured anywhere yet. On the boards where most hiring happens today, it never is.</p>
    <h2>What a Roven record would show</h2>
    <p>When an employer joins Roven, their profile displays metrics computed automatically from real platform activity — the share of applications that get an answer, how fast, how many are left in silence, and confirmed hires. Nothing written by anonymous strangers; nothing an employer (or Roven) can edit or sell.</p>
  </div>
</section>
<section class="section cta-band">
  <div class="wrap">
    <p class="kicker" style="text-align:center">Is this your business?</p>
    <h2 style="max-width:none">Claim {name} on Roven.</h2>
    <p class="sub">Verification takes minutes. Founding employers post free, pay no placement fees now or for 12 months after pricing activates, and keep 50% off for life.</p>
    <div class="hero-ctas" style="justify-content:center">
      <a class="btn btn-green magnet" href="{claim_href}">Claim this business</a>
      <a class="btn btn-ghost-dark magnet" href="{root}employers.html">How Roven works for employers</a>
    </div>
  </div>
</section>
<section class="section">
  <div class="wrap">
    <p class="kicker">Nearby</p>
    <h2>More {vert.lower()} businesses in {metro}</h2>
    <div class="biz-grid">
{sib_cards}    </div>
    <p style="margin-top:18px"><a href="index.html">← All {metro} businesses on Roven</a></p>
  </div>
</section>
"""
    head = HEAD.format(
        title=f"{name} — Hiring & Careers | {metro}, {state} | Roven",
        desc=f"Is {p['name']} hiring? {p['name']} ({vert}, {city}, {state}) has not yet joined Roven, the verified hiring marketplace with public employer accountability records.",
        canonical=canonical,
        root=root,
        jsonld=jsonld,
    )
    return head + body + FOOT


def metro_index(metro_slug, metro, state, businesses, root) -> str:
    by_vert = {}
    for b in businesses:
        by_vert.setdefault(b.get("verticalDisplay", "Other"), []).append(b)
    sections = ""
    for vert in sorted(by_vert):
        cards = "".join(
            f'      <a class="biz-card" href="{b["slug"]}.html"><h3>{esc(b["name"])}</h3><p>{esc(b.get("city") or metro)}</p></a>\n'
            for b in sorted(by_vert[vert], key=lambda x: x["name"])
        )
        sections += f'    <h2 style="margin-top:34px">{esc(vert)}</h2>\n    <div class="biz-grid">\n{cards}    </div>\n'
    head = HEAD.format(
        title=f"Businesses hiring in {metro}, {state} | Roven",
        desc=f"{len(businesses)} {metro} businesses on Roven's radar. See which employers have joined the verified hiring marketplace — and which haven't yet.",
        canonical=f"{SITE}/business/{metro_slug}/",
        root=root,
        jsonld="",
    )
    body = f"""<header class="page-head">
  <div class="wrap">
    <p class="kicker">Employer directory</p>
    <h1>{esc(metro)}, {esc(state)}</h1>
    <p class="biz-meta">{len(businesses)} businesses · updated {datetime.now(timezone.utc).strftime('%B %Y')}</p>
  </div>
</header>
<section class="section">
  <div class="wrap">
{sections}
    <p style="margin-top:22px"><a href="../index.html">← All metros</a></p>
  </div>
</section>
"""
    return head + body + FOOT


def hub_index(metros_summary, root) -> str:
    cards = "".join(
        f'      <a class="biz-card" href="{slug}/index.html"><h3>{esc(m)}, {esc(st)}</h3><p>{n} businesses</p></a>\n'
        for slug, m, st, n in metros_summary
    )
    head = HEAD.format(
        title="Employer directory — who's hiring, and who's accountable | Roven",
        desc="Roven's directory of businesses across Arizona, California, Texas, and Florida — verified employers with public accountability records, and the businesses that haven't joined yet.",
        canonical=f"{SITE}/business/",
        root=root,
        jsonld="",
    )
    body = f"""<header class="page-head">
  <div class="wrap">
    <p class="kicker">Employer directory</p>
    <h1>Who's hiring — and who's accountable.</h1>
  </div>
</header>
<section class="section">
  <div class="wrap">
    <div class="biz-grid">
{cards}    </div>
  </div>
</section>
"""
    return head + body + FOOT


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True)
    ap.add_argument("--site", required=True)
    args = ap.parse_args()

    firebase_admin.initialize_app(credentials.Certificate(args.key))
    db = firestore.client()

    print("loading prospects...")
    prospects = []
    for snap in db.collection("prospects").where("status", "==", "unclaimed").stream():
        p = snap.to_dict()
        if not p.get("name"):
            continue
        p["slug"] = f"{slugify(p['name'])}-{snap.id[:6].lower()}"
        prospects.append(p)
    print(f"  {len(prospects)} unclaimed prospects")

    by_metro = {}
    for p in prospects:
        by_metro.setdefault(p["metroSlug"], []).append(p)

    base = os.path.join(args.site, "business")
    os.makedirs(base, exist_ok=True)
    urls = [f"{SITE}/business/"]
    metros_summary = []
    total_pages = 0

    for metro_slug, blist in sorted(by_metro.items()):
        metro, state = blist[0]["metro"], blist[0]["state"]
        mdir = os.path.join(base, metro_slug)
        os.makedirs(mdir, exist_ok=True)
        root = "../../"

        for p in blist:
            siblings = [s for s in blist
                        if s["vertical"] == p["vertical"] and s["slug"] != p["slug"]]
            page = business_page(p, root, siblings)
            with open(os.path.join(mdir, p["slug"] + ".html"), "w", encoding="utf-8") as f:
                f.write(page)
            urls.append(f"{SITE}/business/{metro_slug}/{p['slug']}")
            total_pages += 1

        with open(os.path.join(mdir, "index.html"), "w", encoding="utf-8") as f:
            f.write(metro_index(metro_slug, metro, state, blist, root))
        urls.append(f"{SITE}/business/{metro_slug}/")
        metros_summary.append((metro_slug, metro, state, len(blist)))
        print(f"  {metro_slug:14s} {len(blist)} pages")

    with open(os.path.join(base, "index.html"), "w", encoding="utf-8") as f:
        f.write(hub_index(metros_summary, "../"))

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        sm.append(f"  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>")
    sm.append("</urlset>")
    with open(os.path.join(args.site, "sitemap-business.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(sm))

    print(f"\nGenerated {total_pages} business pages + {len(metros_summary)} metro indexes + hub + sitemap-business.xml ({len(urls)} URLs).")
    print("Deploy the site, then submit sitemap-business.xml in Search Console.")


if __name__ == "__main__":
    main()
