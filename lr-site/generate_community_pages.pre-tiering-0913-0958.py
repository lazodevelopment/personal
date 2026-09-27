#!/usr/bin/env python3
"""
LeaseReputation — community SEO page generator.

Produces one static, SEO-optimized landing page per apartment community under
/community/<slug>.html, plus a /community/index.html hub linking them all, and
regenerates the tiered sitemap (rich pages submitted; thin long tail
noindex,follow and held back — see INDEX TIERING below).

Each page targets searches for that community's name ("Broadstone Waterfront
reviews", "The Beverly Scottsdale reviews") and funnels visitors into the app.

To add a community: append a dict to COMMUNITIES and re-run:  python3 generate_community_pages.py
"""

import os
import re
import html
import datetime
import json

APP_URL = "https://app.leasereputation.com"
SITE_URL = "https://leasereputation.com"

# ─────────────────────────────────────────────────────────────────────────
# LIVE DATA (Firestore) — pages render each community's real Reputation
# Score, dimension bars, and verified review excerpts at build time, plus
# schema.org AggregateRating/Review markup (star ratings in Google results).
# Uses the Admin SDK service account; if it (or firebase_admin) is missing,
# generation falls back to static pages and prints a warning — the build
# never breaks. Firestore doc id == place_id, so the join is exact.
# ─────────────────────────────────────────────────────────────────────────
SERVICE_ACCOUNT_CANDIDATES = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "serviceAccountKey.json"),
    r"C:\Users\kurvh\lease-reputation\serviceAccountKey.json",
]

# Also auto-generate pages for communities that have verified reviews in the
# app but no hand-written entry below (name/city parsed from their address).
AUTO_INCLUDE_REVIEWED = True

# PHASE 1 — full-directory mode: generate a page for EVERY community in the
# Firestore directory (parseable US address required), not just curated or
# reviewed ones. Each page targets its community's "[name] reviews" search.
INCLUDE_FULL_DIRECTORY = True

STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "DC": "Washington, D.C.", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii",
    "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine",
    "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska",
    "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
    "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island",
    "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}

ADDR_RE = re.compile(r"^(.*?),\s*([^,]+),\s*([A-Z]{2})\s+(\d{5})")


def synthesize_entry(pid, d):
    """Directory doc -> page entry, or None if the address won't parse."""
    name = str(d.get("name") or "").strip()
    addr = str(d.get("address") or "")
    m = ADDR_RE.match(addr)
    if not name or not m:
        return None
    street, city, state, zc = (m.group(1).strip(), m.group(2).strip(),
                               m.group(3), m.group(4))
    if state not in STATE_NAMES:
        return None
    return {
        "name": name, "city": city, "state": state, "zip": zc,
        "address": street, "area": city,
        "metro": STATE_METROS.get(state, STATE_NAMES[state]),
        "developer": "",
        "place_id": pid,
        "blurb": (name + " is an apartment community at " + street + " in "
                  + city + ", " + state + ". Its LeaseReputation Reputation "
                  "Score is built only from verified residents — people who "
                  "proved they actually lived there — so the reviews can't be "
                  "bought, planted, or quietly deleted."),
    }

MAX_REVIEW_EXCERPTS = 5
EXCERPT_CHARS = 320

# ── MONETIZATION GATE ────────────────────────────────────────────────
# True  = Carfax model: pages show that a score exists (review count +
#         tier word) but the number, dimension bars, review excerpts, and
#         rating schema are withheld behind "See the full Reputation
#         Report" CTAs into the app.
# False = growth mode: full scores, excerpts, and AggregateRating schema
#         on every page (maximum SEO, zero scarcity).
# One flag, fully reversible at the next regeneration.
GATE_SCORES = False

# ── INDEX TIERING (GSC fix, Sep 2026) ────────────────────────────────
# GSC Sep 13: 20.1K discovered, 1.25K indexed, 18.2K "Discovered –
# currently not indexed". Cause: the "rich" tier counted a Google photo
# as richness, so 18.5K near-identical synthesized pages landed in
# sitemap-rich.xml and Google read the whole site as a doorway pattern
# (impressions collapsed mid-Aug, right after the mass submission).
#
# New rule — a community page is RICH only if it has something Google
# can't get from Maps: a verified review, a hand-curated entry, or a
# carried-over enrichment block (see ENRICH_START). A photo alone is NOT
# rich. Thin pages stay live and internally linked (city/state hubs) so
# they're discoverable, but are noindex,follow and out of the submitted
# sitemap until they earn a review or enrichment — then they flip to
# indexable automatically on the next build.
NOINDEX_THIN = True            # thin pages get <meta name="robots" content="noindex,follow">
DIRECTORY_IN_SITEMAP = False   # False = sitemap-directory.xml is written but NOT listed in the index
MIN_RICH_REVIEWS = 1           # reviews needed for a synthesized page to count as rich

# enrich_pages.py runs AFTER this generator and injects a block into each
# page. This generator rewrites every page nightly, which wipes that
# block unless we carry it over from the previous build. Set these two
# strings to EXACTLY the markers enrich_pages.py writes around its block.
ENRICH_START = "<!-- lr-enrich:start -->"
ENRICH_END = "<!-- lr-enrich:end -->"

# Optional per-state facts for the "Renting in {State}" card:
# guides/tenant-rights/facts.json  ->  {"TX": ["...", "..."], "AZ": [...]}
# 2–4 short, sourced facts per state (deposit return window, notice
# period, late-fee cap...). Missing file = card just links to the guide.
TENANT_FACTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "guides", "tenant-rights", "facts.json")
try:
    TENANT_FACTS = json.load(open(TENANT_FACTS_PATH, encoding="utf-8"))
    if not isinstance(TENANT_FACTS, dict):
        TENANT_FACTS = {}
except Exception:
    TENANT_FACTS = {}


def carry_enrichment(prev_path):
    """Return the enrichment block (markers included) from the previous
    build of this page, or '' if none. Keeps enrich_pages.py output alive
    across nightly regenerations."""
    try:
        if not os.path.exists(prev_path):
            return ""
        src = open(prev_path, encoding="utf-8").read()
        a = src.find(ENRICH_START)
        if a < 0:
            return ""
        b = src.find(ENRICH_END, a)
        if b < 0:
            return ""
        return src[a:b + len(ENRICH_END)]
    except Exception:
        return ""


def state_rights_html(st):
    """'Renting in {State}' card: links every community page to its state
    tenant-rights guide (unique per state, real internal path into the
    guide system) and lists per-state facts when facts.json has them."""
    st_name = STATE_NAMES.get(st, st)
    guide = f"{SITE_URL}/guides/tenant-rights/{st.lower()}/"
    facts = [f for f in TENANT_FACTS.get(st, []) if isinstance(f, str) and f.strip()][:4]
    items = "".join(f"<li>{esc(f)}</li>" for f in facts)
    body = (f"<ul class=\"facts-list\">{items}</ul>" if items else
            f"<p>Know your rights before you sign or move out.</p>")
    return (f'<div class="card"><h2>Renting in {esc(st_name)}</h2>{body}'
            f'<p><a class="chip" href="{guide}">{esc(st_name)} tenant rights guide &rarr;</a></p></div>')

STATE_METROS = {"AZ": "Phoenix & Scottsdale", "TX": "Dallas & Frisco", "MA": "Massachusetts"}


def _score_color(s):
    if s >= 80:
        return "#3DDC97"
    if s >= 65:
        return "#C4B5FD"
    if s >= 50:
        return "#FFC862"
    return "#FF8B8B"


def _score_label(s):
    if s >= 80:
        return "Excellent"
    if s >= 65:
        return "Good"
    if s >= 50:
        return "Mixed"
    return "Poor"


DIM_LABELS = [("management", "Management"), ("maintenance", "Maintenance"),
              ("value", "Value"), ("noise", "Noise"), ("safety", "Safety"),
              ("moveout", "Move-out & deposit")]


def _ts_date(ts):
    """Firestore timestamp/datetime -> 'YYYY-MM-DD', else ''."""
    try:
        if hasattr(ts, "date"):
            return ts.date().isoformat()
    except Exception:
        pass
    return ""


def load_live_data():
    """Returns (data: {place_id: {...}}, extras: [community dicts]) or ({}, [])."""
    key_path = next((p for p in SERVICE_ACCOUNT_CANDIDATES if os.path.exists(p)), None)
    if key_path is None:
        print("  ! serviceAccountKey.json not found -- building static pages (no live scores)")
        return {}, []
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
    except ImportError:
        print("  ! firebase_admin not installed (pip install firebase-admin) -- static pages")
        return {}, []
    try:
        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.Certificate(key_path))
        db = firestore.client()
    except Exception as e:
        print("  ! Firestore init failed (" + str(e) + ") -- building static pages")
        return {}, []

    known_ids = {c.get("place_id") for c in COMMUNITIES if c.get("place_id")}
    data, extras = {}, []

    docs_by_id = {}
    if INCLUDE_FULL_DIRECTORY:
        # One streaming pass over the whole directory.
        try:
            for doc in db.collection("communities").stream():
                docs_by_id[doc.id] = doc.to_dict() or {}
        except Exception as e:
            print("  ! directory stream failed: " + str(e))
    else:
        try:
            for doc in db.collection("communities").where("reviewCount", ">", 0).stream():
                docs_by_id[doc.id] = doc.to_dict() or {}
        except Exception as e:
            print("  ! reviewed-communities query failed: " + str(e))
        for pid in known_ids - set(docs_by_id):
            try:
                snap = db.collection("communities").document(pid).get()
                if snap.exists:
                    docs_by_id[pid] = snap.to_dict() or {}
            except Exception:
                pass

    for pid, d in docs_by_id.items():
        entry = {
            "score": float(d.get("reputationScore") or 0),
            "reviewCount": int(d.get("reviewCount") or 0),
            "dims": {k: float(v) for k, v in (d.get("dimensionScores") or {}).items()
                     if isinstance(v, (int, float))},
            "reviews": [],
            "renewYes": 0, "renewTotal": 0, "photoCount": 0,
            "rentStats": d.get("rentStats") if isinstance(d.get("rentStats"), dict) else None,
            "mgmtResponse": None,
            # Real change dates for sitemap lastmod (never the build date).
            "docUpdated": _ts_date(d.get("updatedAt") or d.get("createdAt")),
            "latestReview": "",
            "grocery": d.get("nearestGrocery") if isinstance(d.get("nearestGrocery"), dict) else None,
        }
        if entry["reviewCount"] > 0:
            try:
                q = (db.collection("communities").document(pid).collection("reviews")
                     .order_by("createdAt", direction=firestore.Query.DESCENDING).limit(25))
                for r in q.stream():
                    rv = r.to_dict() or {}
                    if rv.get("status") != "published" or rv.get("hidden") is True:
                        continue
                    # Stats run over every published review fetched (up to
                    # 25), independent of the excerpt cap below.
                    entry["renewTotal"] += 1
                    if rv.get("wouldRenew") is True:
                        entry["renewYes"] += 1
                    if not entry["latestReview"]:
                        entry["latestReview"] = _ts_date(rv.get("createdAt"))
                    photos = rv.get("photos") if isinstance(rv.get("photos"), list) else []
                    entry["photoCount"] += len(photos)
                    if len(entry["reviews"]) >= MAX_REVIEW_EXCERPTS:
                        continue
                    ratings = {k: v for k, v in (rv.get("ratings") or {}).items()
                               if isinstance(v, (int, float))}
                    stars = round(sum(ratings.values()) / len(ratings), 1) if ratings else 0
                    created = rv.get("createdAt")
                    entry["reviews"].append({
                        "author": str(rv.get("authorName") or "Verified resident")[:120],
                        "stars": stars,
                        "status": ("Former resident" if rv.get("residentStatus") == "former"
                                   else "Current resident"),
                        "wouldRenew": rv.get("wouldRenew") is True,
                        "text": str(rv.get("text") or "").strip(),
                        "photos": [str(p) for p in photos][:3],
                        "date": created.date().isoformat() if hasattr(created, "date") else "",
                    })
            except Exception as e:
                print("  ! review fetch failed for " + pid + ": " + str(e))
            # Management response (operator claim flow): render when present.
            try:
                for resp in (db.collection("communities").document(pid)
                             .collection("operatorResponses").limit(1).stream()):
                    txt = str((resp.to_dict() or {}).get("text") or "").strip()
                    if txt:
                        entry["mgmtResponse"] = txt[:1200]
            except Exception:
                pass
        data[pid] = entry

        # Not in the hand-written list -> synthesize a page entry.
        wants_page = INCLUDE_FULL_DIRECTORY or (
            AUTO_INCLUDE_REVIEWED and entry["reviewCount"] > 0)
        if wants_page and pid not in known_ids:
            e = synthesize_entry(pid, d)
            if e is not None:
                extras.append(e)
    with_reviews = sum(1 for v in data.values() if v["reviewCount"] > 0)
    print("  - live data: " + str(len(data)) + " communities, "
          + str(with_reviews) + " with reviews, " + str(len(extras)) + " auto-added pages")
    return data, extras


def score_band_html(name, live):
    """The live Reputation Score card: SVG ring + dimension bars."""
    if not live:
        return ""
    score = live["score"]
    count = live["reviewCount"]
    if count <= 0 or score <= 0:
        return ('<div class="card" id="score">\n'
                '    <h2>' + esc(name) + ' Reputation Score</h2>\n'
                '    <p>No verified reviews yet — ' + esc(name) + '\'s score appears with its '
                'first verified resident review. Lived here? Yours would be the one that puts '
                'it on the board.</p>\n'
                '    <div class="cta-row"><a class="btn" href="' + APP_URL + '">Write the first '
                'verified review</a></div>\n  </div>')
    col = _score_color(score)
    label = _score_label(score)
    if GATE_SCORES:
        plural = "review" if count == 1 else "reviews"
        return ('<div class="card" id="score">\n'
                '    <h2>' + esc(name) + ' Reputation Score</h2>\n'
                '    <p style="margin-bottom:14px">Rated <strong style="color:' + col + '">'
                + label + '</strong> by verified residents — computed from <strong '
                'style="color:var(--text)">' + str(count) + ' verified resident '
                + plural + '</strong>. Never sponsored, boosted, or for sale.</p>\n'
                '    <div class="lockband">\n'
                '      <div class="lockring"><svg viewBox="0 0 120 120">'
                '<circle cx="60" cy="60" r="52" fill="none" stroke="rgba(255,255,255,.08)" stroke-width="10"/>'
                '<circle cx="60" cy="60" r="52" fill="none" stroke="' + col + '" stroke-width="10" '
                'stroke-linecap="round" stroke-dasharray="82 327" transform="rotate(-90 60 60)" opacity=".45"/>'
                '<text x="60" y="72" text-anchor="middle" fill="' + col + '" font-size="34" '
                'font-weight="800" font-family="Plus Jakarta Sans,sans-serif">?</text></svg>'
                '<div class="lockglyph">&#128274;</div></div>\n'
                '      <div class="lockcopy"><strong>The exact score, category breakdown, and '
                'full verified reviews are in the Reputation Report.</strong>'
                '<span>See how ' + esc(name) + ' really scores on management, maintenance, '
                'value, noise, safety, and move-out before you sign.</span></div>\n'
                '    </div>\n'
                + renew_line_html(live) + METHODOLOGY_LINE +
                '    <div class="cta-row" style="margin-top:16px"><a class="btn" href="'
                + APP_URL + '">See the full Reputation Report</a></div>\n  </div>')
    frac = max(0.0, min(score / 100.0, 1.0))
    circumference = 2 * 3.14159 * 52
    dash = "%.1f %.1f" % (frac * circumference, circumference)
    ring = (
        '<svg class="ring" viewBox="0 0 120 120" role="img" aria-label="Reputation Score '
        + "%.0f" % score + ' out of 100">'
        '<circle cx="60" cy="60" r="52" fill="none" stroke="rgba(255,255,255,.08)" stroke-width="10"/>'
        '<circle cx="60" cy="60" r="52" fill="none" stroke="' + col + '" stroke-width="10" '
        'stroke-linecap="round" stroke-dasharray="' + dash + '" transform="rotate(-90 60 60)"/>'
        '<text x="60" y="58" text-anchor="middle" fill="' + col + '" font-size="30" '
        'font-weight="800" font-family="Plus Jakarta Sans,sans-serif">' + "%.0f" % score + '</text>'
        '<text x="60" y="80" text-anchor="middle" fill="' + col + '" font-size="12" '
        'font-weight="700" font-family="Plus Jakarta Sans,sans-serif">' + label + '</text></svg>')
    bars = ""
    for key, lbl in DIM_LABELS:
        if key not in live["dims"]:
            continue
        v = live["dims"][key]
        bc = _score_color(v)
        width = "%.0f" % max(2.0, min(v, 100.0))
        bars += ('<div class="dimrow"><div class="dimtop"><span>' + esc(lbl) + '</span>'
                 '<b style="color:' + bc + '">' + "%.0f" % v + '</b></div>'
                 '<div class="dimtrack"><div class="dimfill" style="width:' + width + '%;'
                 'background:' + bc + '"></div></div></div>')
    updated = datetime.date.today().strftime("%B %d, %Y").replace(" 0", " ")
    plural = "review" if count == 1 else "reviews"
    return ('<div class="card" id="score">\n'
            '    <h2>' + esc(name) + ' Reputation Score</h2>\n'
            '    <p style="margin-bottom:4px">From <strong style="color:var(--text)">'
            + str(count) + ' verified resident ' + plural + '</strong> — never sponsored, '
            'boosted, or for sale. Updated ' + updated + '.</p>\n'
            '    <div class="scoregrid">\n'
            '      <div class="ringwrap">' + ring + '</div>\n'
            '      <div class="dims">' + (bars if bars else '<p>Dimension scores appear as reviews accumulate.</p>') + '</div>\n'
            '    </div>\n' + renew_line_html(live) + METHODOLOGY_LINE + '  </div>')


def glance_chips_html(c, live):
    """At-a-glance strip under the hero: the should-I-keep-reading row."""
    chips = ['<span class="chip">&#128205; ' + esc(c["city"]) + ", " + c["state"] + '</span>']
    n = live.get("reviewCount", 0) if live else 0
    if n > 0:
        chips.append('<span class="chip"><strong>' + str(n) + '</strong>&nbsp;verified '
                     + ('review' if n == 1 else 'reviews') + '</span>')
        total, yes = live.get("renewTotal", 0), live.get("renewYes", 0)
        if total >= 5:
            chips.append('<span class="chip"><strong>'
                         + str(int(round(100.0 * yes / total)))
                         + '%</strong>&nbsp;would renew</span>')
        rs = live.get("rentStats")
        if rs and isinstance(rs.get("count"), int) and rs["count"] >= 2:
            if GATE_SCORES:
                chips.append('<span class="chip">&#128181; Real rents reported by '
                             + str(rs["count"]) + ' residents</span>')
            elif isinstance(rs.get("min"), int) and isinstance(rs.get("max"), int):
                chips.append('<span class="chip">&#128181; Residents report ${:,}&ndash;${:,}</span>'
                             .format(rs["min"], rs["max"]))
    else:
        chips.append('<span class="chip">Be the first verified review</span>')
    return '<div class="glance">' + "".join(chips) + '</div>'


def breadcrumbs(c, slug, city_pages):
    """Visible crumbs + BreadcrumbList schema. City crumb links to the city
    page only when that page exists (3+ community threshold)."""
    city_label = c["city"] + ", " + c["state"]
    cslug = city_slug(c["city"], c["state"])
    city_href = (SITE_URL + "/apartments/" + cslug + "/") if cslug in city_pages else None
    crumb_city = ('<a href="' + city_href + '">' + esc(city_label) + '</a>'
                  if city_href else esc(city_label))
    html_out = ('<nav class="crumbs" aria-label="Breadcrumb"><a href="' + SITE_URL
                + '/">Home</a> / <a href="' + SITE_URL + '/community/">Communities</a> / '
                + crumb_city + ' / <span>' + esc(c["name"]) + '</span></nav>')
    items = [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE_URL + "/"},
        {"@type": "ListItem", "position": 2, "name": "Communities",
         "item": SITE_URL + "/community/"},
    ]
    pos = 3
    if city_href:
        items.append({"@type": "ListItem", "position": pos, "name": city_label,
                      "item": city_href})
        pos += 1
    items.append({"@type": "ListItem", "position": pos, "name": c["name"],
                  "item": SITE_URL + "/community/" + slug + ".html"})
    schema = ('<script type="application/ld+json">'
              + json.dumps({"@context": "https://schema.org",
                            "@type": "BreadcrumbList", "itemListElement": items})
              + '</script>')
    return html_out, schema


def claim_strip_html(name, place_id):
    """Operator acquisition surface — on every community page."""
    claim_url = "https://app.leasereputation.com/claimCommunity?communityId=" + place_id
    return ('<div class="claimstrip"><div><strong>Manage ' + esc(name) + '?</strong>'
            '<span>Claim this community to respond publicly to verified reviews '
            '&mdash; free. Reputation Scores are never for sale and can\'t be '
            'changed by anyone, including us.</span></div>'
            '<a class="btn btn-ghost" href="'
            + claim_url + '">Claim this community</a></div>')


def sticky_bar_html():
    """Mobile-only persistent conversion bar."""
    return ('<div class="stickybar"><span>Lived here?</span>'
            '<a class="btn" href="' + APP_URL + '">Write a verified review</a></div>')


def mgmt_response_html(name, live):
    if not live or not live.get("mgmtResponse"):
        return ""
    return ('<div class="mgmtresp"><div class="mghead">Response from management'
            '<span class="mgbadge">Claimed community</span></div><p>'
            + esc(live["mgmtResponse"]) + '</p></div>')


def renew_line_html(live):
    """ITEM 3: would-renew stat — free on every reviewed page (teaser-safe:
    it strengthens trust without revealing the gated score)."""
    if not live:
        return ""
    total, yes = live.get("renewTotal", 0), live.get("renewYes", 0)
    if total <= 0:
        return ""
    if total >= 5:
        pct = int(round(100.0 * yes / total))
        inner = ('<strong style="color:' + ("var(--mint)" if pct >= 50 else "var(--warn)")
                 + '">' + str(pct) + '%</strong> of verified residents would renew their lease')
    else:
        inner = ('<strong style="color:' + ("var(--mint)" if yes * 2 >= total else "var(--warn)")
                 + '">' + str(yes) + ' of ' + str(total)
                 + '</strong> verified residents would renew their lease')
    return '<p class="renewline">' + inner + '</p>'


METHODOLOGY_LINE = (
    '<p class="methodline">Recent experience counts more: reviews fade on an '
    '18-month half-life, so this reflects how the community operates '
    '<em>now</em> — and a single review can never swing the score. '
    'Never sponsored. Never for sale.</p>')


def reviews_section_html(name, live):
    if not live or not live.get("reviews"):
        return ""
    if GATE_SCORES:
        n = live.get("reviewCount", len(live["reviews"]))
        plural = "review" if n == 1 else "reviews"
        return ('<div class="card" id="reviews">\n'
                '    <h2>What verified residents say about ' + esc(name) + '</h2>\n'
                '    <p><strong style="color:var(--text)">' + str(n) + ' verified resident '
                + plural + '</strong> from people who proved they actually lived here — '
                'the honest version of ' + esc(name) + ' that marketing pages leave out'
                + ((' — including <strong style="color:var(--text)">'
                    + str(live.get("photoCount", 0))
                    + ' resident photo' + ('' if live.get("photoCount", 0) == 1 else 's')
                    + '</strong> of what the units really look like')
                   if live.get("photoCount", 0) > 0 else '')
                + '. Read every review in the full Reputation Report.</p>\n'
                '    <div class="cta-row" style="margin-top:14px"><a class="btn" href="'
                + APP_URL + '">Unlock the full report</a></div>\n  </div>')
    cards = ""
    for r in live["reviews"]:
        stars_full = int(round(r["stars"]))
        stars = "★" * stars_full + "☆" * (5 - stars_full)
        text = r["text"]
        if len(text) > EXCERPT_CHARS:
            text = text[:EXCERPT_CHARS].rsplit(" ", 1)[0] + "…"
        body = ('<p class="rtext">&ldquo;' + esc(text) + '&rdquo;</p>') if text else ""
        if r.get("photos"):
            body += ('<div class="rphotos">'
                     + "".join('<img src="' + esc(p) + '" alt="Resident photo of '
                               + esc(name) + '" loading="lazy" />'
                               for p in r["photos"])
                     + '</div>')
        renew = ('<span class="renew yes">Would renew</span>' if r["wouldRenew"]
                 else '<span class="renew no">Would not renew</span>')
        date_bit = (" &middot; " + esc(r["date"])) if r["date"] else ""
        cards += ('<div class="review">'
                  '<div class="rhead"><strong>' + esc(r["author"]) + '</strong>'
                  '<span class="rstars">' + stars + '</span></div>'
                  '<div class="rmeta">' + esc(r["status"]) + ' &middot; verified resident'
                  + date_bit + '</div>' + body
                  + '<div class="rfoot">' + renew + '</div></div>')
    return ('<div class="card" id="reviews">\n'
            '    <h2>What verified residents say about ' + esc(name) + '</h2>\n'
            '    <p>Excerpts from verified resident reviews — read them all, with photos, in the app.</p>\n'
            '    ' + cards + '\n'
            '    <div class="cta-row" style="margin-top:18px"><a class="btn" href="'
            + APP_URL + '">Read all verified reviews</a></div>\n  </div>')


def aggregate_schema(c, live):
    """AggregateRating + Review JSON-LD fragments for the ApartmentComplex node."""
    if GATE_SCORES:
        return ""  # marked-up ratings must be visible on-page per Google policy
    if not live or live["reviewCount"] <= 0 or live["score"] <= 0:
        return ""
    parts = (',"aggregateRating":{"@type":"AggregateRating","ratingValue":"'
             + "%.1f" % live["score"] + '","bestRating":"100","worstRating":"0",'
             '"ratingCount":"' + str(live["reviewCount"]) + '"}')
    reviews_json = []
    for r in live["reviews"]:
        if not r["text"]:
            continue
        body = esc(r["text"][:EXCERPT_CHARS].replace('"', "'"))
        rj = ('{"@type":"Review","author":{"@type":"Person","name":"' + esc(r["author"]) + '"},'
              '"reviewRating":{"@type":"Rating","ratingValue":"' + str(r["stars"])
              + '","bestRating":"5","worstRating":"1"},'
              + ('"datePublished":"' + r["date"] + '",' if r["date"] else "")
              + '"reviewBody":"' + body + '"}')
        reviews_json.append(rj)
    if reviews_json:
        parts += ',"review":[' + ",".join(reviews_json) + "]"
    return parts


# ─────────────────────────────────────────────────────────────────────────
# Community data. Add entries here; addresses verified from public listings.
# `manager`/`developer` are optional. `blurb` is a 1–2 sentence neutral
# description used in the page body (kept factual, not marketing hype).
# ─────────────────────────────────────────────────────────────────────────
COMMUNITIES = [
    # ═══════════════════ PHOENIX / SCOTTSDALE METRO ═══════════════════
    # ---- Still Broadstone-branded (Alliance Residential) ----
    {
        "name": "Broadstone Waterfront",
        "city": "Scottsdale", "state": "AZ", "zip": "85251",
        "address": "7025 E Via Soleri Dr",
        "area": "Old Town / Waterfront", "metro": "Phoenix & Scottsdale",
        "developer": "Alliance Residential",
        "place_id": "ChIJnbxgMZYLK4cRBNCQThjA2fY",
        "blurb": "A luxury waterfront community near Scottsdale Fashion Square and Old Town, known for its infinity-edge pool, rooftop lounge, and walkable access to Old Town's dining and nightlife.",
    },
    {
        "name": "Broadstone Scottsdale Quarter",
        "city": "Scottsdale", "state": "AZ", "zip": "85254",
        "address": "15345 N Scottsdale Rd",
        "area": "North Scottsdale", "metro": "Phoenix & Scottsdale",
        "developer": "Alliance Residential",
        "place_id": "ChIJSzNYmD50K4cRlNYk87o_sgo",
        "blurb": "A North Scottsdale community offering studio, one, and two bedroom apartments steps from Scottsdale Quarter's shopping and dining, with a two-story fitness center and saltwater pool.",
    },
    {
        "name": "Broadstone 7th Street",
        "city": "Phoenix", "state": "AZ", "zip": "85014",
        "address": "5727 N 7th St",
        "area": "7th Street Corridor", "metro": "Phoenix & Scottsdale",
        "developer": "Alliance Residential",
        "place_id": "ChIJJxOl20ATK4cRgdp9-ThtinQ",
        "blurb": "A community along the 7th Street Corridor in north-central Phoenix, featuring a resident clubhouse, two-story fitness center, resort-style pool and spa, and an on-site yoga studio.",
    },
    # ---- Formerly Broadstone, since sold and rebranded (current names used) ----
    {
        "name": "Onyx Uptown PHX",
        "city": "Phoenix", "state": "AZ", "zip": "85013",
        "address": "500 W Camelback Rd",
        "area": "Uptown Phoenix", "metro": "Phoenix & Scottsdale",
        "developer": "Chamberlin & Associates",
        "place_id": "ChIJZxzR4pMTK4cREryn8KBS5Mk",
        "blurb": "A central Phoenix community in the Uptown corridor (formerly Broadstone Uptown), within walking distance of Camelback-area dining, with a resort-style pool and fitness amenities.",
    },
    {
        "name": "Arts District Apartments",
        "city": "Phoenix", "state": "AZ", "zip": "85004",
        "address": "222 E McDowell Rd",
        "area": "Roosevelt Row / Arts District", "metro": "Phoenix & Scottsdale",
        "developer": "Mark-Taylor",
        "place_id": "ChIJc5VJrWoSK4cR_GpUYoJdd4E",
        "blurb": "A downtown Phoenix community adjacent to the Phoenix Art Museum and steps from Roosevelt Row (formerly Broadstone Arts District), with gallery flex spaces and a resort-style pool.",
    },
    {
        "name": "Avant at Fashion Center",
        "city": "Chandler", "state": "AZ", "zip": "85226",
        "address": "555 S Galleria Way",
        "area": "Chandler Fashion District", "metro": "Phoenix & Scottsdale",
        "developer": "",
        "place_id": "ChIJQ3DP_dkAK4cRZ0XBl5JNZEA",
        "blurb": "A community within walking distance of Chandler Fashion Center, Costco, and Target (formerly Broadstone Fashion Center), featuring social lounges, a resort-style pool, and upgraded gas-stove units.",
    },
    # ---- The Beverly (StreetLights Residential / managed by Greystar) ----
    {
        "name": "The Beverly",
        "city": "Scottsdale", "state": "AZ", "zip": "85255",
        "address": "7395 E Legacy Ln",
        "area": "One Scottsdale / North Scottsdale", "metro": "Phoenix & Scottsdale",
        "developer": "StreetLights Residential", "manager": "Greystar",
        "place_id": "ChIJkRLzhWN3K4cRh7juZ9aQzK0",
        "blurb": "A 314-unit luxury community at the One Scottsdale masterplan near Scottsdale Road and Loop 101, with Spanish Colonial-style architecture, a resort pool courtyard, and a resident bar with coworking lounge.",
    },

    # ═══════════════════ DALLAS / FRISCO METRO ═══════════════════
    # ---- Frisco ----
    {
        "name": "Greenway Village at The Link",
        "city": "Frisco", "state": "TX", "zip": "75033",
        "address": "15991 Bear Trap Wy",
        "area": "The Link / PGA Frisco", "metro": "Dallas & Frisco",
        "developer": "",
        "place_id": "ChIJR35YQ6c_TIYRSk4hJJ_cK-c",
        "blurb": "A community at The Link development in Frisco, close to PGA Frisco and Fields West, offering a resort-style setting in one of Frisco's fastest-growing corridors.",
    },
    {
        "name": "The Links on PGA Parkway",
        "city": "Frisco", "state": "TX", "zip": "75033",
        "address": "15950 Paramount Wy",
        "area": "PGA Parkway", "metro": "Dallas & Frisco",
        "developer": "",
        "place_id": "ChIJLX_p5gw_TIYRWy_Ffr721Eo",
        "blurb": "A large luxury community near PGA Parkway with an exceptional amenity set — eight clubhouses, two gyms, two pools, valet trash, and monthly resident events including Saturday yoga.",
    },
    {
        "name": "Avalon Frisco",
        "city": "Frisco", "state": "TX", "zip": "75033",
        "address": "11900 Research Rd",
        "area": "Research Row / Frisco", "metro": "Dallas & Frisco",
        "developer": "",
        "place_id": "ChIJVTKROa4-TIYRE-7uSa4IqK0",
        "blurb": "A highly-rated luxury community in Frisco known for responsive maintenance, a professional leasing team, and well-maintained grounds — a longtime favorite among Frisco renters.",
    },
    {
        "name": "Avalon Frisco North",
        "city": "Frisco", "state": "TX", "zip": "75033",
        "address": "12050 Research Rd",
        "area": "Research Row / Frisco", "metro": "Dallas & Frisco",
        "developer": "",
        "place_id": "ChIJec6Aw2o_TIYRxCi3S8VNbBA",
        "blurb": "The sister community to Avalon Frisco, offering the same well-run, amenity-rich luxury living in Frisco's Research Row area with a friendly, responsive management team.",
    },
    {
        "name": "Stonebriar Pines",
        "city": "Frisco", "state": "TX", "zip": "75034",
        "address": "5250 Town and Country Blvd",
        "area": "Stonebriar / Frisco", "metro": "Dallas & Frisco",
        "developer": "",
        "place_id": "ChIJjaAoj1w7TIYR4QJoxBnW6EM",
        "blurb": "A top-rated, family-friendly Frisco community near Stonebriar Centre, praised for its spotless pool and gym, quick-turnaround maintenance, and welcoming, cared-for feel.",
    },
    # ---- Dallas (Uptown / Downtown) ----
    {
        "name": "Selene Luxury Residences",
        "city": "Dallas", "state": "TX", "zip": "75201",
        "address": "2620 Maple Ave",
        "area": "Uptown Dallas", "metro": "Dallas & Frisco",
        "developer": "",
        "place_id": "ChIJ2Tyk71-ZToYRY3UCtEPr83I",
        "blurb": "A highly-rated luxury residence in Uptown Dallas with an attentive concierge and management team, a smoke-free environment, and a strong sense of community.",
    },
    {
        "name": "One Uptown",
        "city": "Dallas", "state": "TX", "zip": "75204",
        "address": "2619 McKinney Ave",
        "area": "Uptown Dallas", "metro": "Dallas & Frisco",
        "developer": "",
        "place_id": "ChIJjXt_Pi6ZToYRCCF63aUQyCw",
        "blurb": "A modern high-rise on McKinney Avenue in Uptown Dallas known for incredible views, soundproof units, top-tier amenities, and a standout concierge and maintenance team.",
    },
    {
        "name": "Maple Terrace Residences",
        "city": "Dallas", "state": "TX", "zip": "75201",
        "address": "3003 Maple Ave",
        "area": "Uptown Dallas", "metro": "Dallas & Frisco",
        "developer": "",
        "place_id": "ChIJ6ffNVzGZToYRycFFnl6DDJc",
        "blurb": "A resort-like luxury community in the heart of Uptown Dallas steps from the Katy Trail, with striking architecture, extensive amenities, and valet service.",
    },
    {
        "name": "Peridot Residences",
        "city": "Dallas", "state": "TX", "zip": "75201",
        "address": "1601 Elm St",
        "area": "Downtown Dallas", "metro": "Dallas & Frisco",
        "developer": "",
        "place_id": "ChIJpxbxU4yZToYRu9Kk6uoVuac",
        "blurb": "A high-end downtown Dallas high-rise on Elm Street with top-notch building security, high-end finishes, unbeatable views, and on-site restaurants.",
    },
]


def slugify_entry(c):
    return c.get("_slug") or slugify(c["name"], c["city"])


def slugify(name, city):
    s = f"{name} {city}".lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def esc(s):
    return html.escape(s, quote=True)


# ─────────────────────────────────────────────────────────────────────────
PAGE_CSS = """
  :root{
    --indigo:#4C4FE6; --indigo-bright:#6E72F0; --deep:#1E1A5C; --ink:#15102E; --ink-deep:#0E0A20;
    --lilac:#C4B5FD; --white:#FFFFFF; --warn:#FF8B8B; --mint:#3DDC97;
    --text:#EFEDFB; --text-dim:rgba(233,231,251,.64); --text-faint:rgba(233,231,251,.42);
    --glass:rgba(255,255,255,.055); --glass-2:rgba(255,255,255,.09); --border:rgba(255,255,255,.12);
    --maxw:1160px; --pad:clamp(20px,5vw,24px);
  }
  *{box-sizing:border-box;margin:0;padding:0}
  html{scroll-behavior:smooth}
  body{font-family:'Plus Jakarta Sans',system-ui,sans-serif;background:
    radial-gradient(circle at 50% -8%, var(--deep) 0%, var(--ink-deep) 55%), var(--ink-deep);
    color:var(--text);line-height:1.6;-webkit-font-smoothing:antialiased;overflow-x:hidden}
  body::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;
    background-image:radial-gradient(rgba(196,181,253,.05) 1.1px,transparent 1.1px);background-size:30px 30px}
  img,svg{display:block;max-width:100%}
  a{color:inherit;text-decoration:none}
  .wrap{position:relative;z-index:1;max-width:var(--maxw);margin:0 auto;padding:0 var(--pad);width:100%}
  h1,h2,h3{line-height:1.1;letter-spacing:-.02em;font-weight:800}

  header{position:sticky;top:0;z-index:50;backdrop-filter:blur(14px);
    background:rgba(14,10,32,.72);border-bottom:1px solid var(--border)}
  .nav{display:flex;align-items:center;justify-content:space-between;height:66px}
  .logo{display:inline-flex;align-items:center;gap:10px}
  .logo .wm{font-weight:800;font-size:1.15rem;letter-spacing:-.01em}
  .logo .wm .l{color:rgba(255,255,255,.6);font-weight:500}
  .logo .wm .r{color:#fff;font-weight:800}
  .shield{width:30px;height:30px;border-radius:9px;flex:none;display:flex;align-items:center;justify-content:center;
    background:linear-gradient(180deg,#1E1A5C,#4C4FE6)}
  .btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;font-weight:700;font-size:.95rem;
    padding:12px 22px;border-radius:12px;background:var(--indigo);color:#fff;transition:.18s;border:1px solid transparent}
  .btn:hover{background:var(--indigo-bright);transform:translateY(-2px)}
  .btn-ghost{background:transparent;color:var(--text);border:1px solid var(--border)}
  .btn-ghost:hover{background:var(--glass-2);border-color:var(--lilac)}

  .hero{padding:64px 0 40px;position:relative}
  .hero.has-photo{padding:0}
  /* Content-driven height: the photo is a backdrop, the text defines the
     box — so long community names can never clip out the top on mobile. */
  .hero-photo{position:relative;min-height:clamp(320px,42vw,460px);overflow:hidden;border-radius:0 0 28px 28px;display:flex;flex-direction:column;justify-content:flex-end}
  .hero-photo img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
  .photo-credit{position:absolute;right:10px;bottom:8px;z-index:3;font-size:.68rem;
    color:rgba(255,255,255,.75);background:rgba(0,0,0,.35);border-radius:6px;
    padding:2px 8px;letter-spacing:.02em}
  .hero-photo::after{content:"";position:absolute;inset:0;
    background:linear-gradient(180deg,rgba(14,10,32,.35) 0%,rgba(14,10,32,.55) 45%,rgba(14,10,32,.96) 100%)}
  .hero-photo .hero-inner{position:relative;z-index:2;
    padding:clamp(96px,20vw,150px) var(--pad) 34px}
  .hero-photo .hero-inner .wrap-inner{max-width:var(--maxw);margin:0 auto;width:100%}
  .eyebrow{font-size:.78rem;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:var(--lilac);
    margin-bottom:16px;display:flex;align-items:center;gap:10px}
  .eyebrow::before{content:"";width:22px;height:2px;border-radius:2px;background:linear-gradient(90deg,var(--indigo),var(--lilac))}
  h1{font-size:clamp(2rem,5.5vw,3.3rem);margin-bottom:14px}
  h1 .accent{color:var(--lilac)}
  .sub{font-size:clamp(1.05rem,2.3vw,1.25rem);color:var(--text-dim);max-width:640px;margin-bottom:14px}
  .meta{color:var(--text-faint);font-size:.95rem;margin-bottom:30px}
  .cta-row{display:flex;gap:12px;flex-wrap:wrap}

  .card{background:var(--glass);border:1px solid var(--border);border-radius:20px;padding:28px;margin:20px 0}
  .card h2{font-size:1.5rem;margin-bottom:12px}
  .card h3{font-size:1.12rem;margin:18px 0 8px}
  .card p{color:var(--text-dim);margin-bottom:14px}
  .card p:last-child{margin-bottom:0}
  .facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin-top:8px}
  .fact{background:var(--glass-2);border:1px solid var(--border);border-radius:14px;padding:16px}
  .fact .k{font-size:.72rem;text-transform:uppercase;letter-spacing:.12em;color:var(--text-faint);margin-bottom:6px}
  .fact .v{font-weight:700;font-size:1.02rem}

  .facts-list{margin:8px 0 0 18px;padding:0;line-height:1.6}
  .why{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px;margin-top:8px}
  .vid{position:relative;margin-top:20px;border-radius:12px;overflow:hidden;cursor:pointer;
    aspect-ratio:16/9;background:#000;border:1px solid rgba(255,255,255,.08)}
  .vid img{width:100%;height:100%;object-fit:cover;display:block;opacity:.82;transition:opacity .2s}
  .vid:hover img{opacity:1}
  .vid-play{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:64px;height:64px;
    border-radius:50%;background:rgba(99,91,255,.92);color:#fff;display:flex;align-items:center;
    justify-content:center;font-size:1.4rem;padding-left:5px;box-shadow:0 8px 30px rgba(0,0,0,.45)}
  .vid-cap{margin-top:10px;font-size:.85rem;color:var(--muted)}
  .vid-frame{width:100%;aspect-ratio:16/9;border:0;border-radius:12px;margin-top:20px;display:block}
  .why .item{display:flex;gap:12px;align-items:flex-start}
  .why .dot{width:22px;height:22px;border-radius:50%;flex:none;background:rgba(61,220,151,.15);
    display:flex;align-items:center;justify-content:center;margin-top:2px}
  .why .dot svg{width:13px;height:13px;stroke:var(--mint)}
  .why .item p{color:var(--text-dim);font-size:.95rem}
  .why .item strong{color:var(--text);display:block;margin-bottom:2px}

  .cta-band{text-align:center;padding:44px 28px;margin:32px 0;border-radius:22px;
    background:linear-gradient(135deg,rgba(76,79,230,.18),rgba(196,181,253,.08));border:1px solid var(--border)}
  .cta-band h2{font-size:1.7rem;margin-bottom:10px}
  .cta-band p{color:var(--text-dim);margin-bottom:22px;max-width:520px;margin-left:auto;margin-right:auto}

  .related{margin:36px 0}
  .related h2{font-size:1.3rem;margin-bottom:16px}
  .chips{display:flex;flex-wrap:wrap;gap:10px}
  .chip{background:var(--glass);border:1px solid var(--border);border-radius:11px;padding:10px 15px;
    font-size:.9rem;color:var(--text-dim);transition:.16s}
  .chip:hover{border-color:var(--lilac);color:var(--text)}

  footer{border-top:1px solid var(--border);margin-top:50px;padding:34px 0;color:var(--text-faint);font-size:.9rem}
  .foot{display:flex;flex-wrap:wrap;gap:14px;justify-content:space-between;align-items:center}
  .foot a{color:var(--text-dim)} .foot a:hover{color:var(--lilac)}
  .disclaimer{font-size:.8rem;color:var(--text-faint);margin-top:14px;line-height:1.5;max-width:820px}

  .scoregrid{display:grid;grid-template-columns:150px 1fr;gap:26px;align-items:center;margin-top:16px}
  @media(max-width:560px){.scoregrid{grid-template-columns:1fr;justify-items:center}}
  .ring{width:140px;height:140px}
  .dims{width:100%}
  .dimrow{margin-bottom:12px}.dimrow:last-child{margin-bottom:0}
  .dimtop{display:flex;justify-content:space-between;font-size:.92rem;color:var(--text-dim);margin-bottom:5px}
  .dimtop b{font-weight:800}
  .dimtrack{height:7px;border-radius:4px;background:rgba(255,255,255,.06);overflow:hidden}
  .dimfill{height:100%;border-radius:4px}
  .review{border:1px solid var(--border);background:var(--glass-2);border-radius:14px;padding:16px 18px;margin-top:14px}
  .rhead{display:flex;justify-content:space-between;align-items:center;gap:10px}
  .rstars{color:#FFC862;letter-spacing:2px;font-size:.95rem}
  .rmeta{font-size:.82rem;color:var(--text-faint);margin-top:2px}
  .rtext{color:var(--text-dim);margin-top:10px;font-size:.97rem}
  .rfoot{margin-top:10px}
  .renew{font-size:.8rem;font-weight:700;padding:3px 10px;border-radius:999px}
  .renew.yes{color:var(--mint);background:rgba(61,220,151,.1);border:1px solid rgba(61,220,151,.3)}
  .renew.no{color:var(--warn);background:rgba(255,139,139,.08);border:1px solid rgba(255,139,139,.3)}

  .lockband{display:flex;align-items:center;gap:22px;padding:18px;border-radius:14px;
    background:var(--glass-2);border:1px solid var(--border)}
  @media(max-width:520px){.lockband{flex-direction:column;text-align:center}}
  .lockring{position:relative;width:110px;height:110px;flex:none}
  .lockring svg{width:110px;height:110px;filter:blur(1px)}
  .lockglyph{position:absolute;right:-4px;bottom:-4px;width:34px;height:34px;border-radius:50%;
    background:var(--indigo);display:flex;align-items:center;justify-content:center;
    font-size:15px;box-shadow:0 4px 14px rgba(79,70,229,.5)}
  .lockcopy{display:flex;flex-direction:column;gap:6px}
  .lockcopy strong{color:var(--text);font-size:.98rem;line-height:1.45}
  .lockcopy span{color:var(--text-faint);font-size:.88rem;line-height:1.5}

  .renewline{margin-top:14px;font-size:.98rem;color:var(--text-dim)}
  .methodline{margin-top:8px;font-size:.8rem;color:var(--text-faint);line-height:1.55}
  .methodline em{color:var(--text-dim);font-style:normal;font-weight:700}
  .rphotos{display:flex;gap:8px;margin:10px 0 4px;flex-wrap:wrap}
  .rphotos img{width:104px;height:104px;object-fit:cover;border-radius:10px;
    border:1px solid var(--border)}

  .crumbs{font-size:.78rem;color:var(--text-faint);margin:18px 0 4px}
  .crumbs a{color:var(--text-faint);text-decoration:none}
  .crumbs a:hover{color:var(--lilac)}
  .crumbs span{color:var(--text-dim)}
  .glance{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 6px}
  .chip{border:1px solid var(--border);background:var(--glass-2);border-radius:999px;
    padding:7px 14px;font-size:.84rem;color:var(--text-dim)}
  .chip strong{color:var(--text)}
  .claimstrip{display:flex;align-items:center;justify-content:space-between;gap:18px;
    border:1px dashed var(--border);background:var(--glass-2);border-radius:16px;
    padding:18px 22px;margin-top:22px}
  .claimstrip div{display:flex;flex-direction:column;gap:4px;min-width:0}
  .claimstrip strong{color:var(--text);font-size:.98rem}
  .claimstrip span{color:var(--text-faint);font-size:.85rem;line-height:1.5}
  @media(max-width:620px){.claimstrip{flex-direction:column;align-items:flex-start}}
  .stickybar{display:none}
  @media(max-width:640px){
    .stickybar{display:flex;position:fixed;left:0;right:0;bottom:0;z-index:60;
      align-items:center;justify-content:space-between;gap:12px;
      padding:10px 16px calc(10px + env(safe-area-inset-bottom));
      background:rgba(14,10,32,.92);backdrop-filter:blur(12px);
      border-top:1px solid var(--border)}
    .stickybar span{font-size:.88rem;font-weight:700;color:var(--text)}
    .stickybar .btn{padding:10px 18px;font-size:.85rem}
    body{padding-bottom:74px}
  }
  .mgmtresp{border:1px solid var(--border);border-left:3px solid var(--indigo);
    background:var(--glass-2);border-radius:14px;padding:16px 20px;margin-top:14px}
  .mgmtresp .mghead{font-weight:800;font-size:.9rem;color:var(--text);
    display:flex;align-items:center;gap:10px;margin-bottom:8px}
  .mgbadge{font-size:.7rem;font-weight:700;color:var(--lilac);
    border:1px solid var(--border);border-radius:999px;padding:2px 9px}
  .mgmtresp p{color:var(--text-dim);font-size:.92rem;margin:0}
"""

SHIELD_SVG = ('<svg width="17" height="17" viewBox="0 0 24 24" fill="none">'
              '<path d="M12 2 4 5.5v5.6c0 4.9 3.4 9.5 8 10.9 4.6-1.4 8-6 8-10.9V5.5L12 2z" fill="rgba(255,255,255,.2)"/>'
              '<path d="m8.6 12.2 2.3 2.3 4.5-4.8" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>')
CHECK_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke-width="2.4"><path d="M5 13l4 4L19 7" stroke-linecap="round" stroke-linejoin="round"/></svg>'


def header_html():
    return f"""<header>
  <div class="wrap nav">
    <a class="logo" href="{SITE_URL}/" aria-label="LeaseReputation home">
      <span class="shield">{SHIELD_SVG}</span>
      <span class="wm"><span class="l">lease</span><span class="r">reputation</span></span>
    </a>
    <a class="btn" href="{APP_URL}">Open the app</a>
  </div>
</header>"""


def footer_html():
    return f"""<footer>
  <div class="wrap">
    <div class="foot">
      <div><a href="{SITE_URL}/">leasereputation.com</a> &middot; <a href="{SITE_URL}/community/">All communities</a> &middot; <a href="{SITE_URL}/guides/tenant-rights/">Tenant rights</a> &middot; <a href="{SITE_URL}/privacy.html">Privacy</a> &middot; <a href="{SITE_URL}/terms.html">Terms</a></div>
      <div>&copy; 2026 Lease Reputation LLC</div>
    </div>
    <p class="disclaimer">LeaseReputation is an independent review platform and is not affiliated with, endorsed by, or sponsored by any apartment community, property manager, or developer named on this page. Community names and trademarks are the property of their respective owners and are used here for identification and reference only. Reviews reflect the opinions of verified residents. Verified reviewers may receive a small thank-you gift (such as a $5 coffee card); gifts are the same for every verified reviewer and are never conditioned on the content or sentiment of a review. Community photos via Google.</p>
  </div>
</footer>"""


def community_page(c, related, live=None, city_pages=frozenset(), explore_html="",
                   enrich_html="", indexable=True, n_in_city=0):
    slug = slugify_entry(c)
    thin = not indexable
    full_name = f'{c["name"]} — {c["city"]}, {c["state"]}'
    loc = f'{c["city"]}, {c["state"]} {c.get("zip","")}'.strip()
    title = f'{c["name"]} Reviews — {c["city"]}, {c["state"]} | LeaseReputation'
    if live and live.get("reviewCount", 0) > 0 and live.get("score", 0) > 0:
        if GATE_SCORES:
            desc = (f'{c["name"]} in {c["city"]}, {c["state"]} is rated '
                    f'{_score_label(live["score"])} by verified residents — '
                    f'{live["reviewCount"]} verified '
                    f'{"review" if live["reviewCount"] == 1 else "reviews"} on LeaseReputation. '
                    f'See the full Reputation Score before you sign.')
        else:
            desc = (f'{c["name"]} in {c["city"]}, {c["state"]} scores '
                    f'{live["score"]:.0f}/100 ({_score_label(live["score"])}) from '
                    f'{live["reviewCount"]} verified resident '
                    f'{"review" if live["reviewCount"] == 1 else "reviews"} on LeaseReputation. '
                    f'Reviews that can\'t be bought or buried.')
    else:
        desc = (f'Read verified resident reviews for {c["name"]} in {c["city"]}, {c["state"]}. '
                f'See its Reputation Score — built only from residents who actually lived there. '
                f'Reviews that can\'t be bought or buried.')
    canonical = f'{SITE_URL}/community/{slug}.html'
    crumbs_html, crumbs_schema = breadcrumbs(c, slug, city_pages)

    # Photo detection happens BEFORE schema/og so both can reference it.
    # Legacy curated photos are keyed by slug; the scaled fetcher keys by
    # place_id (stable across rebuilds — slugs can shift when collisions
    # renumber).
    _imgbase = os.path.join(os.path.dirname(os.path.abspath(__file__)), "community")
    photo_rel = f"images/{slug}.jpg"
    has_photo = os.path.exists(os.path.join(_imgbase, photo_rel))
    if not has_photo and c.get("place_id"):
        pid_rel = f"images/{c['place_id']}.jpg"
        if os.path.exists(os.path.join(_imgbase, pid_rel)):
            photo_rel, has_photo = pid_rel, True
    photo_abs_url = f"{SITE_URL}/community/{photo_rel}" if has_photo else ""
    og_image = photo_abs_url or f"{SITE_URL}/leasereputation-og.png"

    # Schema.org structured data — ApartmentComplex + the review platform.
    addr_parts = {}
    if c.get("address"): addr_parts["streetAddress"] = c["address"]
    addr_parts["addressLocality"] = c["city"]
    addr_parts["addressRegion"] = c["state"]
    if c.get("zip"): addr_parts["postalCode"] = c["zip"]
    addr_parts["addressCountry"] = "US"
    addr_json = ",".join(f'"{k}":"{esc(v)}"' for k, v in addr_parts.items())

    _img_schema = f'"image":"{photo_abs_url}",' if has_photo else ""
    schema = f'''<script type="application/ld+json">
{{
  "@context":"https://schema.org",
  "@type":"ApartmentComplex",
  "name":"{esc(c["name"])}",
  {_img_schema}"address":{{"@type":"PostalAddress",{addr_json}}},
  "url":"{canonical}",
  "description":"{esc(c["blurb"])}"{aggregate_schema(c, live)}
}}
</script>
<script type="application/ld+json">
{{
  "@context":"https://schema.org",
  "@type":"WebPage",
  "name":"{esc(title)}",
  "url":"{canonical}",
  "isPartOf":{{"@type":"WebSite","name":"LeaseReputation","url":"{SITE_URL}"}}
}}
</script>'''

    # Robots: thin pages are noindex,follow — link equity still flows to
    # the hubs and neighbors; the page flips to index the moment it earns
    # a review or an enrichment block.
    robots_meta = ('<meta name="robots" content="noindex,follow" />\n' if thin
                   else '<meta name="robots" content="index,follow,max-image-preview:large" />\n')

    facts = [("Location", loc), ("Neighborhood", c.get("area", c["city"]))]
    _g = (live or {}).get("grocery")
    if isinstance(_g, dict) and _g.get("name"):
        _dist = _g.get("distanceMi")
        _v = f"{_g['name']} · {_dist} mi" if _dist is not None else _g["name"]
        facts.append(("Closest grocery", _v))
    if c.get("developer"): facts.append(("Developer", c["developer"]))
    if c.get("manager"): facts.append(("Managed by", c["manager"]))
    facts_html = "".join(
        f'<div class="fact"><div class="k">{esc(k)}</div><div class="v">{esc(v)}</div></div>'
        for k, v in facts)

    # About paragraph: on synthesized pages add the unique bits we DO have
    # (street, zip, grocery, city count) so it's not the same sentence 18K times.
    about_p = esc(c["blurb"])
    if not c.get("_curated"):
        extra = []
        if c.get("address"):
            extra.append(f"It sits at {esc(c['address'])}, {esc(c['city'])}, {c['state']} {esc(c.get('zip',''))}".rstrip() + ".")
        if isinstance(_g, dict) and _g.get("name"):
            _d = _g.get("distanceMi")
            extra.append(f"The closest grocery is {esc(_g['name'])}"
                         + (f", about {_d} miles away." if _d is not None else "."))
        if n_in_city >= 3:
            extra.append(f"It's one of {n_in_city} apartment communities in {esc(c['city'])} listed on LeaseReputation.")
        if extra:
            about_p += " " + " ".join(extra)

    # "Why LeaseReputation" block: full version (with video) only on rich
    # pages; thin pages get two sentences so the page isn't 400 words of
    # site boilerplate around 60 words of community.
    if thin:
        why_block = f"""<div class="card">
    <h2>About the reviews</h2>
    <p>Every review of {esc(c["name"])} on LeaseReputation comes from a resident who proved they lived there. Scores are never sponsored and negative reviews can't be buried.</p>
  </div>"""
    else:
        why_block = f"""<div class="card">
    <h2>Why read {esc(c["name"])} reviews on LeaseReputation?</h2>
    <p>Most apartment reviews you find online can't be trusted — communities can bury bad reviews, and anyone can post a fake one. LeaseReputation is built differently.</p>
    <div class="why">
      <div class="item"><span class="dot">{CHECK_SVG}</span><p><strong>Verified residents only</strong>Every reviewer proves they actually lived at the community. No fakes, no competitors, no paid posts.</p></div>
      <div class="item"><span class="dot">{CHECK_SVG}</span><p><strong>Negative reviews stay up</strong>Communities can't bury or delete honest criticism the way they can on their own listings.</p></div>
      <div class="item"><span class="dot">{CHECK_SVG}</span><p><strong>The score can't be bought</strong>The Reputation Score is computed only from verified residents — never sponsored, boosted, or for sale.</p></div>
      <div class="item"><span class="dot">{CHECK_SVG}</span><p><strong>Specifics required</strong>Any rating below five stars requires a written explanation, so reviews are actually useful.</p></div>
    </div>
    <div class="vid" role="button" tabindex="0" aria-label="Play video: how LeaseReputation works"
      onkeydown='if(event.key==="Enter")this.click()'
      onclick='this.nextElementSibling.remove();this.outerHTML=`<iframe class="vid-frame" src="https://www.youtube-nocookie.com/embed/WjKOwDJykK4?autoplay=1" title="How LeaseReputation works" allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen></iframe>`'>
      <img src="{SITE_URL}/lr-explainer-thumb.jpg" alt="How LeaseReputation works — 60 second explainer" loading="lazy" width="1280" height="720" />
      <span class="vid-play">&#9654;</span>
    </div>
    <p class="vid-cap">Watch: how verified reviews work on LeaseReputation.</p>
  </div>"""

    about_card = f"""<div class="card">
    <h2>About {esc(c["name"])}</h2>
    <p>{about_p}</p>
    <div class="facts">{facts_html}</div>
  </div>

  {enrich_html}"""
    score_card = score_band_html(c["name"], live)
    # Unique-first ordering: reviewed pages lead with the score; thin pages
    # lead with what's actually specific to the community.
    lead_blocks = ((score_card + "\n\n  " + about_card) if not thin
                   else (about_card + "\n\n  " + score_card))

    related_chips = "".join(
        f'<a class="chip" href="{SITE_URL}/community/{slugify(r["name"], r["city"])}.html">{esc(r["name"])} &middot; {esc(r["city"])}</a>'
        for r in related)

    # Hero: photo banner when a local photo exists (detected above),
    # gradient hero otherwise.
    if has_photo:
        hero_block = f"""<section class="hero has-photo">
  <div class="hero-photo">
    <img src="{photo_rel}" alt="{esc(c['name'])} in {esc(c['city'])}, {esc(c['state'])}" loading="eager" width="1200" height="500" />
    <span class="photo-credit">Photo via Google</span>
    <div class="hero-inner">
      <div class="wrap-inner">
        <div class="eyebrow">Verified Resident Reviews</div>
        <h1>{esc(c["name"])}<br /><span class="accent">reviews you can trust.</span></h1>
        <p class="sub">Thinking about leasing at {esc(c["name"])} in {esc(c["city"])}? See what verified residents really think, on LeaseReputation.</p>
        <p class="meta">{esc(loc)}{" &middot; " + esc(c["developer"]) if c.get("developer") else ""}</p>
        <div class="cta-row">
          <a class="btn" href="{APP_URL}">See verified reviews</a>
          <a class="btn btn-ghost" href="{APP_URL}">Write a review</a>
        </div>
      </div>
    </div>
  </div>
</section>"""
    else:
        hero_block = f"""<section class="hero">
  <div class="wrap">
    <div class="eyebrow">Verified Resident Reviews</div>
    <h1>{esc(c["name"])}<br /><span class="accent">reviews you can trust.</span></h1>
    <p class="sub">Thinking about leasing at {esc(c["name"])} in {esc(c["city"])}? See what verified residents — people who actually lived there — really think, on LeaseReputation.</p>
    <p class="meta">{esc(loc)}{" &middot; " + esc(c["developer"]) if c.get("developer") else ""}</p>
    <div class="cta-row">
      <a class="btn" href="{APP_URL}">See verified reviews</a>
      <a class="btn btn-ghost" href="{APP_URL}">Write a review</a>
    </div>
  </div>
</section>"""

    return slug, f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}" />
<link rel="canonical" href="{canonical}" />
{robots_meta}<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Cpath d='M16 2l11 5v8c0 7.5-4.7 12.7-11 15C9.7 27.7 5 22.5 5 15V7l11-5z' fill='%234F46E5'/%3E%3Cpath d='M11 16.5l3.5 3.5 6.5-7' stroke='%2334D399' stroke-width='2.6' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E" />
<meta property="og:title" content="{esc(c["name"])} Reviews | LeaseReputation" />
<meta property="og:description" content="{esc(desc)}" />
<meta property="og:type" content="website" />
<meta property="og:url" content="{canonical}" />
<meta property="og:image" content="{og_image}" />
<meta name="twitter:card" content="summary_large_image" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
{schema}
{crumbs_schema}
<style>{PAGE_CSS}</style>
</head>
<body>
{header_html()}

{hero_block}

<div class="wrap">

  {crumbs_html}
  {glance_chips_html(c, live)}

  {lead_blocks}

  {reviews_section_html(c["name"], live)}

  {mgmt_response_html(c["name"], live)}

  {state_rights_html(c["state"])}

  {why_block}

  {claim_strip_html(c["name"], c["place_id"])}

  <div class="cta-band">
    <h2>See the real {esc(c["name"])} Reputation Score</h2>
    <p>Ratings on management, maintenance, noise, safety, value, and move-out — from verified residents, on the six dimensions that actually matter.</p>
    <div class="cta-row" style="justify-content:center">
      <a class="btn" href="{APP_URL}">Open {esc(c["name"])} on LeaseReputation</a>
    </div>
  </div>

  <div class="card">
    <h2>Lived at {esc(c["name"])}? Share your experience.</h2>
    <p>Your honest, verified review helps the next renter know before they lease — the good and the bad. It takes a few minutes, and your documents are deleted after verification.</p>
    <div class="cta-row"><a class="btn" href="{APP_URL}">Write a verified review</a></div>
  </div>

  <div class="related">
    <h2>Other communities on LeaseReputation</h2>
    <div class="chips">{related_chips}</div>
  </div>

  {explore_html}

</div>

{footer_html()}
{sticky_bar_html()}
</body>
</html>"""


# ── OPERATOR BRANDS (name-identifiable) ─────────────────────────────
# Brand pages aggregate every community whose name matches. Patterns are
# word-anchored to avoid false positives ("Camden" matches "Camden Sotelo"
# but a community coincidentally on Camden St. won't match its address).
BRAND_PATTERNS = [
    ("Camden", r"^camden\b"),
    ("AvalonBay (Avalon / AVA / eaves)", r"^(avalon|ava |eaves)\b"),
    ("MAA", r"^maa\b"),
    ("Broadstone (Alliance Residential)", r"^broadstone\b"),
    ("Cortland", r"^cortland\b"),
    ("Olympus Property", r"^olympus\b"),
    ("Greystar (branded)", r"^(elan|everleigh|album|overture)\b"),
    ("Bell Partners", r"^bell\b"),
    ("Gables Residential", r"^gables\b"),
    ("Windsor Communities", r"^windsor\b"),
    ("AMLI Residential", r"^amli\b"),
    ("Alta (Wood Partners)", r"^alta\b"),
    ("Modera (Mill Creek)", r"^modera\b"),
    ("Jefferson (JPI)", r"^jefferson\b"),
    ("Sparrow", r"^sparrow\b"),
    ("Presidium", r"^presidium\b"),
    ("The Standard", r"^the standard\b"),
    ("Marquis (CWS)", r"^marquis\b"),
    ("Sedona (BH Management)", r"^sedona\b"),
    ("Trammell Crow Residential (Alexan)", r"^alexan\b"),
    ("Hanover", r"^hanover\b"),
    ("Toll Brothers Apartment Living", r"^toll\b"),
    ("Fairfield", r"^fairfield\b"),
    ("IMT Residential", r"^imt\b"),
    ("Sares Regis", r"^sares\b"),
]


def brand_slug(name):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", name.lower())).strip("-")


def city_slug(city, state):
    return slugify(city, state.lower())


GROUP_CSS = """
  .grouplist{margin-top:8px}
  .grow{display:flex;align-items:center;gap:14px;padding:13px 4px;border-top:1px solid var(--border);text-decoration:none}
  .grow:first-child{border-top:none}
  .grow .gname{color:var(--text);font-weight:700;font-size:1rem;flex:1;min-width:0}
  .grow .gmeta{color:var(--text-faint);font-size:.82rem;white-space:nowrap}
  .grow .gtier{font-size:.78rem;font-weight:800;padding:3px 11px;border-radius:999px;white-space:nowrap}
  .grow:hover .gname{color:var(--lilac)}
  .statrow{display:flex;gap:12px;flex-wrap:wrap;margin:14px 0 4px}
  .statchip{border:1px solid var(--border);background:var(--glass-2);border-radius:999px;padding:8px 16px;font-size:.88rem;color:var(--text-dim)}
  .statchip b{color:var(--text)}
"""

GROUP_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>@TITLE@</title>
<meta name="description" content="@DESC@" />
<link rel="canonical" href="@CANON@" />
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Cpath d='M16 2l11 5v8c0 7.5-4.7 12.7-11 15C9.7 27.7 5 22.5 5 15V7l11-5z' fill='%234F46E5'/%3E%3Cpath d='M11 16.5l3.5 3.5 6.5-7' stroke='%2334D399' stroke-width='2.6' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E" />
<meta property="og:title" content="@TITLE@" />
<meta property="og:description" content="@DESC@" />
<meta property="og:image" content="@SITE@/leasereputation-og.png" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
<style>@CSS@</style>
</head>
<body>
@HEADER@
<section class="hero">
  <div class="wrap">
    <div class="eyebrow">@EYEBROW@</div>
    <h1>@H1@</h1>
    <p class="sub">@SUB@</p>
    <div class="statrow">@STATS@</div>
    <div class="cta-row"><a class="btn" href="@APP@">Open the app</a><a class="btn btn-ghost" href="@SITE@/community/">All communities</a></div>
  </div>
</section>
<div class="wrap">
  @BODY@
</div>
@FOOTER@
</body>
</html>"""


def _tier_chip(live):
    if not live or live.get("reviewCount", 0) <= 0 or live.get("score", 0) <= 0:
        return '<span class="gmeta">No verified reviews yet</span>'
    col = _score_color(live["score"])
    n = live["reviewCount"]
    return ('<span class="gtier" style="color:' + col + ';background:' + col
            + '18;border:1px solid ' + col + '55">' + _score_label(live["score"])
            + '</span><span class="gmeta">' + str(n)
            + (' review' if n == 1 else ' reviews') + '</span>')


def _group_rows(members, live_data):
    rows = ""
    for c in sorted(members, key=lambda x: x["name"].lower()):
        live = live_data.get(c.get("place_id", ""))
        rows += ('<a class="grow" href="' + SITE_URL + '/community/'
                 + slugify_entry(c) + '.html"><span class="gname">' + esc(c["name"])
                 + '</span>' + _tier_chip(live) + '</a>')
    return rows


def _group_stats(members, live_data, noun):
    n = len(members)
    reviewed = [live_data.get(c.get("place_id", "")) for c in members]
    reviewed = [l for l in reviewed if l and l.get("reviewCount", 0) > 0]
    total_reviews = sum(l["reviewCount"] for l in reviewed)
    stats = '<span class="statchip"><b>' + str(n) + '</b>&nbsp;' + noun + '</span>'
    stats += ('<span class="statchip"><b>' + str(total_reviews)
              + '</b>&nbsp;verified ' + ('review' if total_reviews == 1 else 'reviews') + '</span>')
    if reviewed:
        stats += ('<span class="statchip"><b>' + str(len(reviewed))
                  + '</b>&nbsp;scored ' + ('community' if len(reviewed) == 1 else 'communities') + '</span>')
    return stats


def render_group_page(title, desc, canon, eyebrow, h1, sub, members, live_data,
                      noun, extra_body=""):
    body = ('<div class="card"><h2>' + esc(h1.replace("<br />", " "))
            + '</h2><div class="grouplist">' + _group_rows(members, live_data)
            + '</div></div>' + extra_body)
    out = GROUP_TEMPLATE
    for token, val in [
        ("@TITLE@", esc(title)), ("@DESC@", esc(desc)), ("@CANON@", canon),
        ("@SITE@", SITE_URL), ("@CSS@", PAGE_CSS + GROUP_CSS),
        ("@HEADER@", header_html()), ("@EYEBROW@", esc(eyebrow)),
        ("@H1@", h1), ("@SUB@", esc(sub)),
        ("@STATS@", _group_stats(members, live_data, noun)),
        ("@APP@", APP_URL), ("@BODY@", body), ("@FOOTER@", footer_html()),
    ]:
        out = out.replace(token, val)
    return out


HUB_TEMPLATE = HUB_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>@TITLE@</title>
<meta name="description" content="@DESC@" />
<link rel="canonical" href="@CANON@" />
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Cpath d='M16 2l11 5v8c0 7.5-4.7 12.7-11 15C9.7 27.7 5 22.5 5 15V7l11-5z' fill='%234F46E5'/%3E%3Cpath d='M11 16.5l3.5 3.5 6.5-7' stroke='%2334D399' stroke-width='2.6' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E" />
<meta property="og:title" content="Apartment Communities — Verified Reviews | LeaseReputation" />
<meta property="og:description" content="@DESC@" />
<meta property="og:image" content="@SITE@/leasereputation-og.png" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
<style>@CSS@</style>
</head>
<body>
@HEADER@
<section class="hero">
  <div class="wrap">
    <div class="eyebrow">Verified Resident Reviews</div>
    <h1>Apartment reviews<br /><span class="accent">you can trust.</span></h1>
    <p class="sub">@N@ apartment communities and growing — every score built only from verified residents who actually lived there. Find your building, read the honest take, add your own.</p>
    <div class="cta-row"><a class="btn" href="@APP@">Open the app</a></div>
  </div>
</section>
<div class="wrap">
  @SECTIONS@
</div>
@FOOTER@
</body>
</html>"""

HUB_CSS = """
  .citygroup{border-top:1px solid var(--border);padding:10px 0}
  .citygroup summary{cursor:pointer;font-weight:700;color:var(--text);font-size:1.02rem;
    list-style:none;display:flex;align-items:center;gap:10px;padding:6px 0}
  .citygroup summary::-webkit-details-marker{display:none}
  .citygroup summary::before{content:"+";color:var(--lilac);font-weight:800;width:16px}
  .citygroup[open] summary::before{content:"−"}
  .ccount{font-size:.78rem;font-weight:700;color:var(--text-faint);
    background:var(--glass-2);border:1px solid var(--border);border-radius:999px;padding:2px 10px}
  .citylinks{display:flex;flex-wrap:wrap;gap:8px;padding:8px 0 6px 26px}
  .citylinks a{color:var(--text-dim);text-decoration:none;font-size:.9rem;
    border:1px solid var(--border);background:var(--glass-2);border-radius:999px;
    padding:6px 13px;transition:border-color .15s,color .15s}
  .citylinks a:hover{color:var(--text);border-color:var(--lilac)}
"""


def hub_page(communities):
    n = len(communities)
    title = "Verified Apartment Reviews by Community | LeaseReputation"
    desc = ("Browse " + str(n) + " apartment communities with verified resident "
            "reviews on LeaseReputation. Reputation Scores built only from "
            "residents who actually lived there — never sponsored, never for sale.")

    # Group: state -> city -> [communities]; states ordered by community count.
    states = {}
    for c in communities:
        states.setdefault(c["state"], {}).setdefault(c["city"], []).append(c)

    sections = ""
    for st in sorted(states, key=lambda s: -sum(len(v) for v in states[s].values())):
        cities = states[st]
        count = sum(len(v) for v in cities.values())
        st_name = STATE_NAMES.get(st, st)
        city_blocks = ""
        for city in sorted(cities):
            links = ""
            for c in sorted(cities[city], key=lambda x: x["name"].lower()):
                links += ('<a href="' + SITE_URL + '/community/'
                          + slugify_entry(c) + '.html">' + esc(c["name"]) + '</a>')
            city_blocks += ('<details class="citygroup"><summary>' + esc(city)
                            + ' <span class="ccount">' + str(len(cities[city]))
                            + '</span></summary><div class="citylinks">' + links
                            + '</div></details>')
        sections += ('<div class="card"><h2><a href="' + SITE_URL
                     + '/apartments/' + st.lower()
                     + '/" style="color:inherit;text-decoration:none">'
                     + esc(st_name) + '</a> <span class="ccount">' + str(count)
                     + ' communities</span></h2>' + city_blocks + '</div>')

    out = HUB_TEMPLATE
    for token, val in [
        ("@TITLE@", esc(title)), ("@DESC@", esc(desc)),
        ("@CANON@", SITE_URL + "/community/"), ("@SITE@", SITE_URL),
        ("@CSS@", PAGE_CSS + HUB_CSS), ("@HEADER@", header_html()),
        ("@N@", str(n)), ("@APP@", APP_URL),
        ("@SECTIONS@", sections), ("@FOOTER@", footer_html()),
    ]:
        out = out.replace(token, val)
    return out


def explore_links_html(c, city_pages, state_city_chips):
    """Geo mesh block on every community page: own city page (when it
    exists), the state hub, and the state's biggest city pages. Gives the
    crawler a lateral path out of every single page."""
    st = c["state"]
    st_name = STATE_NAMES.get(st, st)
    chips = ""
    own = city_slug(c["city"], st)
    if own in city_pages:
        chips += ('<a class="chip" href="' + SITE_URL + '/apartments/' + own
                  + '/">All ' + esc(c["city"]) + ' apartments</a>')
    chips += ('<a class="chip" href="' + SITE_URL + '/apartments/' + st.lower()
              + '/">All ' + esc(st_name) + ' communities</a>')
    added = 0
    for city, s, _n in state_city_chips:
        if added >= 5:
            break
        cs = city_slug(city, s)
        if cs == own:
            continue
        chips += ('<a class="chip" href="' + SITE_URL + '/apartments/' + cs
                  + '/">' + esc(city) + '</a>')
        added += 1
    return ('<div class="related"><h2>Explore ' + esc(st_name)
            + ' apartments</h2><div class="chips">' + chips + '</div></div>')


def state_hub_page(st, cities, live_data, city_pages):
    """One hub per state at /apartments/{st}/ — every community in the
    state is linked here (city groups), so nothing depends solely on the
    national mega-hub for discovery."""
    st_name = STATE_NAMES.get(st, st)
    members = [c for cs in cities.values() for c in cs]
    n = len(members)
    canon = SITE_URL + "/apartments/" + st.lower() + "/"
    # Tenant-rights guide card, when this state's guide has been built.
    guide_card = ""
    _guide = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "guides", "tenant-rights", st.lower(), "index.html")
    if os.path.exists(_guide):
        guide_card = ('<div class="card"><h2>Know your rights in '
                      + esc(st_name) + '</h2><p>Security deposit deadlines, '
                      'repair rights, entry notice, and eviction timelines — '
                      'with statute citations.</p><p><a class="btn ghost" href="'
                      + SITE_URL + '/guides/tenant-rights/' + st.lower()
                      + '/">' + esc(st_name) + ' tenant rights guide</a></p></div>')
    title = (st_name + " Apartments — Verified Resident Reviews | LeaseReputation")
    desc = ("Compare " + str(n) + " apartment communities across " + st_name
            + " with verified resident reviews on LeaseReputation. Reputation "
            "Scores built only from residents who actually lived there — "
            "never for sale.")
    # City-page chip row (cities big enough for their own page).
    paged = sorted([ct for ct in cities
                    if city_slug(ct, st) in city_pages],
                   key=lambda ct: -len(cities[ct]))
    chip_row = ""
    if paged:
        chips = "".join('<a href="' + SITE_URL + '/apartments/'
                        + city_slug(ct, st) + '/">' + esc(ct) + '</a>'
                        for ct in paged)
        chip_row = ('<div class="card"><h2>' + esc(st_name)
                    + ' city guides</h2><div class="citylinks" '
                    'style="padding-left:0">' + chips + '</div></div>')
    # Full city -> community listing (same collapsible pattern as the hub).
    city_blocks = ""
    for city in sorted(cities):
        links = "".join('<a href="' + SITE_URL + '/community/'
                        + slugify_entry(c) + '.html">' + esc(c["name"]) + '</a>'
                        for c in sorted(cities[city], key=lambda x: x["name"].lower()))
        city_blocks += ('<details class="citygroup"><summary>' + esc(city)
                        + ' <span class="ccount">' + str(len(cities[city]))
                        + '</span></summary><div class="citylinks">' + links
                        + '</div></details>')
    body = (guide_card + chip_row + '<div class="card"><h2>Every ' + esc(st_name)
            + ' community <span class="ccount">' + str(n)
            + '</span></h2>' + city_blocks + '</div>')
    h1 = ('Apartments in<br /><span class="accent">' + esc(st_name) + '.</span>')
    sub = (str(n) + " communities across " + st_name + " with verified-resident "
           "reviews. Every score computed from proven residents — never "
           "sponsored, boosted, or bought.")
    out = GROUP_TEMPLATE
    for token, val in [
        ("@TITLE@", esc(title)), ("@DESC@", esc(desc)), ("@CANON@", canon),
        ("@SITE@", SITE_URL), ("@CSS@", PAGE_CSS + GROUP_CSS + HUB_CSS),
        ("@HEADER@", header_html()), ("@EYEBROW@", "Verified Resident Reviews"),
        ("@H1@", h1), ("@SUB@", esc(sub)),
        ("@STATS@", _group_stats(members, live_data, "communities")),
        ("@APP@", APP_URL), ("@BODY@", body), ("@FOOTER@", footer_html()),
    ]:
        out = out.replace(token, val)
    return canon, out


def main():
    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "community")
    os.makedirs(outdir, exist_ok=True)

    live_data, extras = load_live_data()
    for c in COMMUNITIES:
        c["_curated"] = True
    all_communities = COMMUNITIES + extras

    # Unique slugs (two "Park Place"s in one city would otherwise collide).
    used_slugs = {}
    for c in all_communities:
        s = slugify(c["name"], c["city"])
        if s in used_slugs:
            used_slugs[s] += 1
            s = s + "-" + str(used_slugs[s])
        else:
            used_slugs[s] = 1
        c["_slug"] = s

    # Same-city communities index for related links.
    by_city = {}
    for c in all_communities:
        by_city.setdefault((c["city"].lower(), c["state"]), []).append(c)

    # Same-state ring index: spare related slots fill from the community's
    # NEIGHBORS in its state list (wrapping), so link equity chains through
    # every page in the state instead of piling onto the first few
    # communities in the global list.
    by_state = {}
    for c in all_communities:
        by_state.setdefault(c["state"], []).append(c)
    state_pos = {}
    for st, members in by_state.items():
        for k, x in enumerate(members):
            state_pos[id(x)] = k

    # Cities that will get their own /apartments/ page (3+ communities) —
    # breadcrumbs link the city crumb only when the page exists.
    _city_counts = {}
    for c in all_communities:
        _city_counts[(c["city"], c["state"])] = _city_counts.get(
            (c["city"], c["state"]), 0) + 1
    city_pages_set = frozenset(
        city_slug(city, st) for (city, st), n in _city_counts.items() if n >= 3)

    # City-page chips per state, biggest cities first (for explore blocks).
    _state_city_chips = {}
    for (city, st), n in _city_counts.items():
        if city_slug(city, st) in city_pages_set:
            _state_city_chips.setdefault(st, []).append((city, st, n))
    for st in _state_city_chips:
        _state_city_chips[st].sort(key=lambda t: -t[2])

    written = []          # (slug, name)
    sm_communities = []   # (loc, lastmod, rich) for the tiered sitemap
    n_rich = 0
    n_enriched = 0
    for i, c in enumerate(all_communities):
        # related = same city first, then same-state ring neighbors, up to 4
        key = (c["city"].lower(), c["state"])
        related = [x for x in by_city.get(key, []) if x is not c][:4]
        if len(related) < 4:
            ring = by_state.get(c["state"], [])
            k, step = state_pos.get(id(c), 0), 1
            while len(related) < 4 and step <= len(ring):
                cand = ring[(k + step) % len(ring)]
                if cand is not c and cand not in related:
                    related.append(cand)
                step += 1
        live = live_data.get(c.get("place_id", ""))
        explore = explore_links_html(c, city_pages_set,
                                     _state_city_chips.get(c["state"], []))
        # Carry enrich_pages.py output across the rebuild (see ENRICH_START).
        prev_path = os.path.join(outdir, f"{c['_slug']}.html")
        enrich_html = carry_enrichment(prev_path)
        if enrich_html:
            n_enriched += 1
        # RICH = reviews / curated / enriched. A Google photo alone is not
        # unique content and no longer qualifies (that was the bug).
        rich = bool((live and live["reviewCount"] >= MIN_RICH_REVIEWS)
                    or c.get("_curated") or enrich_html)
        if rich:
            n_rich += 1
        slug, html_out = community_page(c, related, live, city_pages_set, explore,
                                        enrich_html=enrich_html,
                                        indexable=(rich or not NOINDEX_THIN),
                                        n_in_city=len(by_city.get(key, [])))
        path = os.path.join(outdir, f"{slug}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html_out)
        written.append((slug, c["name"]))
        lastmod = ""
        if live:
            lastmod = live["latestReview"] or live["docUpdated"]
        sm_communities.append((f"{SITE_URL}/community/{slug}.html", lastmod, rich))
        print(f"  + community/{slug}.html — {c['name']}")
    print(f"  - rich tier: {n_rich} of {len(all_communities)} communities "
          f"({n_enriched} carried enrichment blocks)"
          + ("; thin pages are noindex,follow" if NOINDEX_THIN else ""))

    # hub
    with open(os.path.join(outdir, "index.html"), "w", encoding="utf-8") as f:
        f.write(hub_page(all_communities))
    print(f"  + community/index.html (hub, {len(all_communities)} communities)")

    base = os.path.dirname(os.path.abspath(__file__))
    extra_urls = []

    # ── CITY PAGES: /apartments/{city}-{st}/ ──
    cities = {}
    for c in all_communities:
        cities.setdefault((c["city"], c["state"]), []).append(c)
    citydir = os.path.join(base, "apartments")
    os.makedirs(citydir, exist_ok=True)
    n_city = 0
    for (city, st), members in cities.items():
        if len(members) < 3:
            continue  # thin pages help nobody
        slug = city_slug(city, st)
        st_name = STATE_NAMES.get(st, st)
        n = len(members)
        canon = SITE_URL + "/apartments/" + slug + "/"
        title = f"Apartments in {city}, {st} — Verified Resident Reviews | LeaseReputation"
        desc = (f"Compare {n} apartment communities in {city}, {st_name} with "
                f"verified resident reviews on LeaseReputation. Reputation Scores "
                f"built only from residents who actually lived there — never for sale.")
        h1 = ("Apartments in " + esc(city) + ",<br /><span class=\"accent\">"
              + st + "</span>")
        sub = (f"{n} communities in {city} with verified-resident reviews. Every "
               f"score computed from proven residents — never sponsored, boosted, "
               f"or bought. Find your building and read the honest version.")
        siblings = sorted([k for k in cities if k[1] == st and k != (city, st)
                           and len(cities[k]) >= 3],
                          key=lambda k: -len(cities[k]))[:8]
        chips = ('<a href="' + SITE_URL + '/apartments/' + st.lower()
                 + '/">All ' + esc(st_name) + ' communities</a>')
        chips += "".join('<a href="' + SITE_URL + '/apartments/'
                         + city_slug(cc, ss) + '/">' + esc(cc) + '</a>'
                         for cc, ss in siblings)
        rel = ('<div class="card"><h2>More ' + esc(st_name)
               + ' apartments</h2><div class="citylinks" style="padding-left:0">'
               + chips + '</div></div>')
        html_out = render_group_page(title, desc, canon,
                                     "Verified Resident Reviews", h1, sub,
                                     members, live_data, "communities", rel)
        d = os.path.join(citydir, slug)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(html_out)
        extra_urls.append(canon)
        n_city += 1
    print(f"  + {n_city} city pages (apartments/)")

    # ── STATE HUB PAGES: /apartments/{st}/ ──
    states_all = {}
    for c in all_communities:
        states_all.setdefault(c["state"], {}).setdefault(c["city"], []).append(c)
    n_state = 0
    for st, cts in states_all.items():
        canon, html_out = state_hub_page(st, cts, live_data, city_pages_set)
        d = os.path.join(citydir, st.lower())
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(html_out)
        extra_urls.append(canon)
        n_state += 1
    print(f"  + {n_state} state hub pages (apartments/{{st}}/)")

    # ── BRAND / MANAGEMENT PAGES: /management/{brand}/ ──
    branddir = os.path.join(base, "management")
    os.makedirs(branddir, exist_ok=True)
    brand_index = []
    for brand_name, pattern in BRAND_PATTERNS:
        rx = re.compile(pattern, re.IGNORECASE)
        members = [c for c in all_communities if rx.search(c["name"].strip())]
        if len(members) < 3:
            continue
        short = brand_name.split(" (")[0]
        bslug = brand_slug(short)
        canon = SITE_URL + "/management/" + bslug + "/"
        n = len(members)
        title = f"{short} Apartments — Verified Resident Reviews | LeaseReputation"
        desc = (f"{n} {short} apartment communities with verified resident "
                f"reviews on LeaseReputation. See how this operator's communities "
                f"are rated by proven residents — scores that are never for sale.")
        h1 = (esc(short) + ' communities,<br /><span class="accent">verified.</span>')
        sub = (f"Every {short} community on LeaseReputation, rated only by "
               f"verified residents. Operators can respond to reviews — they can "
               f"never change, hide, or buy a score.")
        html_out = render_group_page(title, desc, canon, "Operator Directory",
                                     h1, sub, members, live_data, "communities")
        d = os.path.join(branddir, bslug)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(html_out)
        extra_urls.append(canon)
        brand_index.append((short, bslug, n))
    if brand_index:
        chips = "".join('<a class="grow" href="' + SITE_URL + '/management/' + s
                        + '/"><span class="gname">' + esc(b)
                        + '</span><span class="gmeta">' + str(cnt)
                        + ' communities</span></a>'
                        for b, s, cnt in sorted(brand_index, key=lambda x: -x[2]))
        hub_html = render_group_page(
            "Apartment Management Companies — Verified Reviews | LeaseReputation",
            "See how major apartment operators' communities are rated by verified "
            "residents on LeaseReputation. Reputation follows the operator — and "
            "it's never for sale.",
            SITE_URL + "/management/",
            "Operator Directory",
            'Management companies,<br /><span class="accent">rated by residents.</span>',
            "An operator's reputation follows them from building to building. "
            "These are the major operators on LeaseReputation, rated only by "
            "verified residents of their communities.",
            [], live_data, "operators",
            '<div class="card"><h2>Operators</h2><div class="grouplist">'
            + chips + '</div></div>')
        with open(os.path.join(branddir, "index.html"), "w", encoding="utf-8") as f:
            f.write(hub_html)
        extra_urls.append(SITE_URL + "/management/")
    print(f"  + {len(brand_index)} operator pages + management hub")

    # regenerate tiered sitemaps (index + rich + directory)
    write_sitemap(sm_communities, extra_urls)
    # Keep the homepage's community counter live (rounds down to the
    # nearest hundred: 8,331 -> "8,300+"). Silently skipped if the span
    # isn't present.
    idx_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
    try:
        if os.path.exists(idx_path):
            html_src = open(idx_path, encoding="utf-8").read()
            n = len(all_communities)
            counter = "{:,}+".format((n // 100) * 100)
            new_html, subs = re.subn(
                r'(<span id="community-count">)[^<]*(</span>)',
                r"\g<1>" + counter + r"\g<2>", html_src)
            if subs:
                open(idx_path, "w", encoding="utf-8").write(new_html)
                print(f"  + index.html community counter -> {counter}")
    except Exception as e:
        print("  ! homepage counter update skipped: " + str(e))

    print(f"\nDone: {len(written)} community pages + hub + sitemap.")


def _url_tag(loc, lastmod, changefreq):
    """lastmod only when we know the REAL change date — a lastmod that's
    always the build date teaches Google to ignore the file entirely
    (that's the fetch gap we saw in GSC)."""
    lm = f"<lastmod>{lastmod}</lastmod>" if lastmod else ""
    return f"  <url><loc>{loc}</loc>{lm}<changefreq>{changefreq}</changefreq></url>"


def _write_urlset(path, url_tags):
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(url_tags) + "\n</urlset>\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write(xml)


def write_sitemap(sm_communities, extra_urls=None):
    """Tiered sitemap index:
      sitemap.xml            -> index (same URL GSC already has submitted)
      sitemap-rich.xml       -> core + hub/city/state/brand pages + rich
                                communities (reviews, curated, or photo)
      sitemap-directory.xml  -> the bare synthesized long tail
    Google samples the rich file's quality first; the directory file keeps
    every page discoverable without dragging the sample down."""
    base = os.path.dirname(os.path.abspath(__file__))
    today = datetime.date.today().isoformat()
    core = ["", "privacy.html", "terms.html", "cookies.html",
            "community-guidelines.html", "contact.html", "accessibility.html",
            "community/"]

    rich, directory = [], []
    for p in core:
        rich.append(_url_tag(f"{SITE_URL}/{p}", "", "monthly"))
    # Tenant-rights guides: auto-included as new states are added.
    _tr_dir = os.path.join(base, "guides", "tenant-rights")
    if os.path.isdir(_tr_dir):
        if os.path.exists(os.path.join(_tr_dir, "index.html")):
            rich.append(_url_tag(f"{SITE_URL}/guides/tenant-rights/",
                                 "", "monthly"))
        for st in sorted(os.listdir(_tr_dir)):
            if os.path.exists(os.path.join(_tr_dir, st, "index.html")):
                rich.append(_url_tag(f"{SITE_URL}/guides/tenant-rights/{st}/",
                                     "", "monthly"))
    for loc in (extra_urls or []):
        rich.append(_url_tag(loc, "", "weekly"))
    for loc, lastmod, is_rich in sm_communities:
        if is_rich:
            rich.append(_url_tag(loc, lastmod, "weekly"))
        else:
            directory.append(_url_tag(loc, lastmod, "monthly"))

    _write_urlset(os.path.join(base, "sitemap-rich.xml"), rich)
    _write_urlset(os.path.join(base, "sitemap-directory.xml"), directory)

    # Only the rich file is submitted by default. The directory file is
    # still written (flip DIRECTORY_IN_SITEMAP to re-list it) — but thin
    # pages are noindex, so listing them would just be contradictory.
    entries = [f'  <sitemap><loc>{SITE_URL}/sitemap-rich.xml</loc><lastmod>{today}</lastmod></sitemap>\n']
    if DIRECTORY_IN_SITEMAP:
        entries.append(f'  <sitemap><loc>{SITE_URL}/sitemap-directory.xml</loc><lastmod>{today}</lastmod></sitemap>\n')
    index = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
             + "".join(entries) + '</sitemapindex>\n')
    with open(os.path.join(base, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(index)
    print(f"  + sitemap.xml (index) + sitemap-rich.xml ({len(rich)} urls, submitted) "
          f"+ sitemap-directory.xml ({len(directory)} urls, "
          + ("submitted" if DIRECTORY_IN_SITEMAP else "written but NOT in index") + ")")


if __name__ == "__main__":
    main()