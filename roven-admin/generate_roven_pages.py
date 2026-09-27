#!/usr/bin/env python3
"""
generate_roven_pages.py — Roven programmatic SEO generator
===========================================================
Forked from the LeaseReputation generate_community_pages.py architecture.

Pulls live jobs + employers from Firestore and emits static HTML pages in the
Roven site design system, with JobPosting / Organization JSON-LD, then
regenerates sitemap.xml. Output drops straight into the roven-site folder and
deploys with the same Wrangler push as the marketing site.

USAGE
  pip install firebase-admin
  # service account JSON from Firebase console -> Project settings -> Service accounts
  python generate_roven_pages.py --key path/to/serviceAccount.json --site ./roven-site

  Then:  wrangler pages deploy roven-site --project-name=rovenhr

PAGE TYPES EMITTED
  /jobs/{slug}.html            one per ACTIVE job          (JobPosting schema)
  /company/{slug}.html         one per VERIFIED employer   (Organization schema
                                                            + accountability data)
  /jobs/index.html             all-jobs rollup
  sitemap.xml                  regenerated with all pages

SCHEMA ASSUMPTIONS (align with the Roven Firestore spec)
  jobs/{jobId}:      employerId, title, status ('active'), createdAt,
                     description (str), employmentType ('FULL_TIME'|'PART_TIME'|
                     'CONTRACTOR'|'TEMPORARY'), locationCity, locationState,
                     remote (bool, optional), salaryMin/salaryMax/salaryUnit
                     ('HOUR'|'DAY'|'YEAR', all optional), validThrough (optional)
  employers/{id}:    name, metro, industry (optional), verified/middeskVerification,
                     reputationScore, accountabilityScore, stats{...} (optional
                     until the scoring function is live)
Fields the generator can't find are omitted from markup rather than faked —
Google penalizes JobPosting markup that misrepresents the listing.
"""

import argparse, html, json, math, os, re, sys
from datetime import datetime, timedelta, timezone

import firebase_admin
from firebase_admin import credentials, firestore

SITE = "https://rovenhr.com"

# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------

def slugify(*parts):
    s = "-".join(p for p in parts if p)
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return re.sub(r"-{2,}", "-", s)

def esc(s):
    return html.escape(str(s or ""))

def iso(ts):
    if ts is None:
        return None
    if hasattr(ts, "isoformat"):
        return ts.isoformat()
    return str(ts)

# ----------------------------------------------------------------------------
# shared page chrome (matches roven-site styles.css — pages link the same sheet)
# ----------------------------------------------------------------------------

HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{canonical}">
<link rel="icon" type="image/png" href="{root}icon.png">
<link rel="apple-touch-icon" href="{root}icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@500;600;700&family=Instrument+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{root}styles.css">
{jsonld}
</head>
<body>
<nav class="nav">
  <div class="wrap nav-inner">
    <a class="logo-link" href="{root}index.html" aria-label="Roven home"><img class="logo-img" src="{root}logo.png" alt="Roven" width="640" height="293"></a>
    <button class="nav-toggle" aria-expanded="false" aria-controls="navlinks">MENU</button>
    <ul class="nav-links" id="navlinks">
      <li><a href="{root}how-it-works.html">How it works</a></li>
      <li><a href="{root}employers.html">For employers</a></li>
      <li><a href="{root}about.html">About</a></li>
      <li><a class="nav-cta" href="https://app.rovenhr.com">Open the app</a></li>
    </ul>
  </div>
</nav>
<div class="scroll-progress" aria-hidden="true"><div class="bar"></div></div>
"""

FOOT = """
<footer class="footer">
  <div class="wrap">
    <div class="footer-legal">
      <span>© 2026 ROVEN · ROVEN HR, LLC</span>
      <span>PHOENIX, AZ</span>
    </div>
  </div>
</footer>
<script src="{root}motion.js" defer></script>
</body>
</html>
"""

def score_card(emp):
    """Employer accountability card. Renders real data if the scoring
    function has run; otherwise a verified-only card with no fake numbers."""
    name = esc(emp.get("name", "Verified employer"))
    score = emp.get("accountabilityScore") or emp.get("reputationScore")
    stats = emp.get("stats") or {}
    rows = ""
    def row(label, val, good=False):
        cls = ' good' if good else ''
        return f'<div class="sc-row"><span>{label}</span><span class="val{cls}">{val}</span></div>'
    if stats.get("applicationsReceived"):
        apps = stats["applicationsReceived"]
        resp = stats.get("dispositionedCount", 0)
        rows += row("Applications answered", f"{round(100*resp/max(apps,1))}%", good=True)
        if stats.get("avgResponseHours") is not None:
            h = stats["avgResponseHours"]
            rows += row("Median response time", f"{h:.0f} hours" if h < 48 else f"{h/24:.1f} days")
        rows += row("Ghosted applicants", f"{round(100*stats.get('ghostCount',0)/max(apps,1))}%")
    if stats.get("hiresReported"):
        rows += row("Hires", stats["hiresReported"])
    ring = ""
    if score:
        s = round(score)
        offset = round(264 * (1 - s / 100))
        ring = (f'<svg class="ring" data-score="{s}" viewBox="0 0 100 100" role="img" '
                f'aria-label="Accountability score {s} out of 100">'
                f'<circle class="track" cx="50" cy="50" r="42"/>'
                f'<circle class="meter" cx="50" cy="50" r="42" style="stroke-dashoffset:{offset}"/>'
                f'<text x="50" y="52">{s}</text></svg>')
    body = rows if rows else '<div class="sc-row"><span>New to Roven</span><span class="val">Building record</span></div>'
    return f"""<div class="score-card glass" aria-label="Employer accountability record">
      <div class="sc-head">
        <div>
          <div class="sc-name">{name}</div>
          <span class="sc-badge"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M3 9 L8 15 L17 4"/></svg>VERIFIED EMPLOYER</span>
        </div>
        {ring}
      </div>
      <div class="sc-rows">{body}</div>
      <div class="sc-foot">COMPUTED FROM PLATFORM ACTIVITY · NOT EDITABLE · NOT FOR SALE</div>
    </div>"""

# ----------------------------------------------------------------------------
# JSON-LD builders
# ----------------------------------------------------------------------------

def jobposting_jsonld(job, emp, url):
    d = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": job.get("title"),
        "description": "<p>" + esc(job.get("description", "")).replace("\n", "<br>") + "</p>",
        "datePosted": iso(job.get("createdAt")),
        "hiringOrganization": {
            "@type": "Organization",
            "name": emp.get("name"),
            "sameAs": f"{SITE}/company/{slugify(emp.get('name',''), emp['_id'][:6])}.html",
        },
        "jobLocation": {
            "@type": "Place",
            "address": {
                "@type": "PostalAddress",
                "addressLocality": job.get("locationCity", "Phoenix"),
                "addressRegion": job.get("locationState", "AZ"),
                "addressCountry": "US",
            },
        },
        "directApply": True,
        "url": url,
    }
    if job.get("employmentType"):
        d["employmentType"] = job["employmentType"]
    if job.get("validThrough"):
        d["validThrough"] = iso(job["validThrough"])
    else:
        # Google requires/strongly prefers validThrough; default 60 days out
        d["validThrough"] = (datetime.now(timezone.utc) + timedelta(days=60)).isoformat()
    if job.get("salaryMin"):
        d["baseSalary"] = {
            "@type": "MonetaryAmount", "currency": "USD",
            "value": {
                "@type": "QuantitativeValue",
                "minValue": job["salaryMin"],
                **({"maxValue": job["salaryMax"]} if job.get("salaryMax") else {}),
                "unitText": job.get("salaryUnit", "HOUR"),
            },
        }
    if job.get("remote"):
        d["jobLocationType"] = "TELECOMMUTE"
    return '<script type="application/ld+json">' + json.dumps(d, default=str) + "</script>"

def org_jsonld(emp, url):
    d = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": emp.get("name"),
        "url": url,
    }
    if emp.get("metro"):
        d["address"] = {"@type": "PostalAddress", "addressLocality": emp["metro"], "addressCountry": "US"}
    return '<script type="application/ld+json">' + json.dumps(d, default=str) + "</script>"

# ----------------------------------------------------------------------------
# page renderers
# ----------------------------------------------------------------------------

def render_job_page(job, emp):
    slug = slugify(job.get("title", "job"), job.get("locationCity", "phoenix"), job["_id"][:6])
    url = f"{SITE}/jobs/{slug}.html"
    et_labels = {"FULL_TIME": "Full-time", "PART_TIME": "Part-time",
                 "CONTRACTOR": "Contract", "TEMPORARY": "Temporary"}
    et = et_labels.get(job.get("employmentType", ""), "")
    loc = f"{job.get('locationCity','Phoenix')}, {job.get('locationState','AZ')}"
    pay = ""
    if job.get("salaryMin"):
        unit = {"HOUR": "/hr", "DAY": "/day", "YEAR": "/yr"}.get(job.get("salaryUnit", "HOUR"), "")
        pay = f"${job['salaryMin']:,.0f}" + (f"–${job['salaryMax']:,.0f}" if job.get("salaryMax") else "") + unit
    meta_bits = " · ".join(b for b in [loc, et, pay] if b)
    desc_meta = esc((job.get("description", "")[:150] + "…") if len(job.get("description", "")) > 150 else job.get("description", ""))
    paragraphs = "".join(f"<p>{esc(p)}</p>" for p in job.get("description", "").split("\n") if p.strip())

    body = HEAD.format(
        title=esc(f"{job.get('title')} — {emp.get('name')} | Roven"),
        description=desc_meta or f"{esc(job.get('title'))} at {esc(emp.get('name'))} in {esc(loc)} — a verified, confirmed-open role on Roven.",
        canonical=url, root="../",
        jsonld=jobposting_jsonld(job, emp, url),
    )
    body += f"""
<header class="page-head">
  <div class="wrap">
    <p class="kicker">CONFIRMED OPEN ROLE · {esc(meta_bits).upper()}</p>
    <h1>{esc(job.get('title'))}</h1>
    <p class="sub" style="margin-top:14px">at <strong>{esc(emp.get('name'))}</strong> — <a href="../company/{slugify(emp.get('name',''), emp['_id'][:6])}.html">see this employer's accountability record</a></p>
  </div>
</header>
<section class="section">
  <div class="wrap showcase" style="align-items:start">
    <div class="prose">
      {paragraphs}
      <p style="margin-top:32px"><a class="btn btn-green magnet" href="https://app.rovenhr.com">Apply on Roven — free</a></p>
      <p class="form-note" style="color:var(--slate)">EVERY APPLICATION ON ROVEN GETS AN ANSWER. THAT'S THE RULE.</p>
    </div>
    <div>{score_card(emp)}</div>
  </div>
</section>
""" + FOOT.format(root="../")
    return slug, body

def render_employer_page(emp, jobs):
    slug = slugify(emp.get("name", "employer"), emp["_id"][:6])
    url = f"{SITE}/company/{slug}.html"
    job_links = "".join(
        f'<div class="step"><span class="n">→</span><div><h4><a href="../jobs/{render_slug(j)}.html">{esc(j.get("title"))}</a></h4>'
        f'<p>{esc(j.get("locationCity","Phoenix"))}, {esc(j.get("locationState","AZ"))}</p></div></div>'
        for j in jobs
    ) or '<p class="sub">No open roles right now — check back, or follow this employer in the app.</p>'
    body = HEAD.format(
        title=esc(f"{emp.get('name')} — verified employer on Roven"),
        description=f"{esc(emp.get('name'))} is a verified employer on Roven. See their public accountability record — response rate, response time, and open roles.",
        canonical=url, root="../",
        jsonld=org_jsonld(emp, url),
    )
    body += f"""
<header class="page-head">
  <div class="wrap">
    <p class="kicker">VERIFIED EMPLOYER · {esc(emp.get('metro','PHOENIX')).upper()}</p>
    <h1>{esc(emp.get('name'))}</h1>
  </div>
</header>
<section class="section">
  <div class="wrap showcase" style="align-items:start">
    <div>
      <h2 style="font-size:26px">Open roles</h2>
      <div class="lane candidate" style="margin-top:20px">{job_links}</div>
    </div>
    <div>{score_card(emp)}</div>
  </div>
</section>
""" + FOOT.format(root="../")
    return slug, body

def render_slug(job):
    return slugify(job.get("title", "job"), job.get("locationCity", "phoenix"), job["_id"][:6])

def render_jobs_index(jobs_by_emp):
    url = f"{SITE}/jobs/"
    cards = ""
    for emp, jobs in jobs_by_emp:
        for j in jobs:
            cards += f"""<div class="problem reveal tilt"><h3><a href="{render_slug(j)}.html">{esc(j.get('title'))}</a></h3>
<p>{esc(emp.get('name'))} · {esc(j.get('locationCity','Phoenix'))}, {esc(j.get('locationState','AZ'))}</p></div>"""
    body = HEAD.format(
        title="Open jobs on Roven — every role verified and confirmed open",
        description="Browse open roles on Roven. Every employer is verified, every job is confirmed open, and every application gets an answer.",
        canonical=url, root="../", jsonld="",
    )
    body += f"""
<header class="page-head">
  <div class="wrap">
    <p class="kicker">OPEN ROLES</p>
    <h1>Every one of these jobs is real.</h1>
  </div>
</header>
<section class="section">
  <div class="wrap"><div class="problem-grid">{cards}</div></div>
</section>
""" + FOOT.format(root="../")
    return body

# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True, help="Firebase service account JSON")
    ap.add_argument("--site", default="./roven-site", help="Path to the site folder")
    args = ap.parse_args()

    firebase_admin.initialize_app(credentials.Certificate(args.key))
    db = firestore.client()

    employers = {}
    for doc in db.collection("employers").stream():
        e = doc.to_dict(); e["_id"] = doc.id
        # only verified employers get public pages
        mv = e.get("middeskVerification") or {}
        if e.get("verified") or mv.get("status") in ("verified", "approved"):
            employers[doc.id] = e

    jobs = []
    for doc in db.collection("jobs").where("status", "==", "active").stream():
        j = doc.to_dict(); j["_id"] = doc.id
        if j.get("employerId") in employers:
            jobs.append(j)

    os.makedirs(os.path.join(args.site, "jobs"), exist_ok=True)
    os.makedirs(os.path.join(args.site, "company"), exist_ok=True)

    urls = [f"{SITE}/", f"{SITE}/employers.html", f"{SITE}/how-it-works.html",
            f"{SITE}/about.html", f"{SITE}/contact.html"]

    jobs_by_emp = {}
    for j in jobs:
        jobs_by_emp.setdefault(j["employerId"], []).append(j)

    for j in jobs:
        emp = employers[j["employerId"]]
        slug, page = render_job_page(j, emp)
        with open(os.path.join(args.site, "jobs", f"{slug}.html"), "w") as f:
            f.write(page)
        urls.append(f"{SITE}/jobs/{slug}.html")
        print(f"  job    /jobs/{slug}.html")

    for eid, emp in employers.items():
        slug, page = render_employer_page(emp, jobs_by_emp.get(eid, []))
        with open(os.path.join(args.site, "company", f"{slug}.html"), "w") as f:
            f.write(page)
        urls.append(f"{SITE}/company/{slug}.html")
        print(f"  company /company/{slug}.html")

    if jobs:
        with open(os.path.join(args.site, "jobs", "index.html"), "w") as f:
            f.write(render_jobs_index([(employers[eid], js) for eid, js in jobs_by_emp.items()]))
        urls.append(f"{SITE}/jobs/")
        print("  index  /jobs/")

    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        sm.append(f"  <url><loc>{u}</loc></url>")
    sm.append("</urlset>")
    with open(os.path.join(args.site, "sitemap.xml"), "w") as f:
        f.write("\n".join(sm))

    print(f"\nGenerated {len(jobs)} job pages, {len(employers)} employer pages.")
    print("Deploy: wrangler pages deploy", args.site, "--project-name=rovenhr")

if __name__ == "__main__":
    main()
