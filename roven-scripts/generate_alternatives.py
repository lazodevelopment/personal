#!/usr/bin/env python3
# ============================================================================
# ROVEN - generate_alternatives.py
# Build ID: JC-ROVEN-ALTPAGES-0801-003
#
# Builds /alternatives/{slug}.html comparison pages plus an index.
#
# A NOTE ON ACCURACY, READ IT:
# Competitor claims here are deliberately general and hedged, and describe
# publicly documented business models only ("charges per application",
# "subscription pricing"). Specific prices are NOT stated, because they change
# and a wrong number on a page whose whole argument is honesty would be the
# worst possible own goal. Every page tells the reader to check the
# competitor's current pricing themselves. Keep it that way.
#
# Usage:  python generate_alternatives.py --out C:\\Users\\kurvh\\roven-site
# ============================================================================

import argparse
import os
from datetime import date

COMPETITORS = [
    {
        "slug": "indeed-alternative",
        "name": "Indeed",
        "title": "Indeed Alternative for Employers | Roven",
        "desc": "Looking for an Indeed alternative? Roven is free to post and "
                "charges one flat fee only when you actually hire. Verified "
                "employers, confirmed-open listings, public response rates.",
        "h1": "An Indeed alternative that only charges you when you hire.",
        "model": "Indeed's employer products are built around sponsored "
                 "listings and pay-per-application billing. You are charged "
                 "as applications arrive, whether or not any of them are "
                 "qualified and whether or not you ever make a hire.",
        "pain": [
            ("You pay for the flood, not the outcome",
             "Billing tied to application volume rewards volume. That is why "
             "the applications keep coming and the qualified ones don't."),
            ("Visibility is an auction",
             "Sponsored placement means your listing competes on budget "
             "against every other employer in your area."),
            ("Nothing measures whether candidates hear back",
             "Response rates are not published, so ghosting costs an employer "
             "nothing - and candidates have learned to expect silence."),
        ],
        "audience": "employer",
    },
    {
        "slug": "ziprecruiter-alternative",
        "name": "ZipRecruiter",
        "title": "ZipRecruiter Alternative | Pay Per Hire, Not Per Month | Roven",
        "desc": "A ZipRecruiter alternative with no monthly subscription. "
                "Roven is free to post and charges one flat fee per completed "
                "hire. Verified employers and public response records.",
        "h1": "A ZipRecruiter alternative with no monthly subscription.",
        "model": "ZipRecruiter sells employer plans on a recurring "
                 "subscription, typically priced per active job slot per "
                 "month. The bill arrives whether you hired anyone that month "
                 "or not.",
        "pain": [
            ("The meter runs while you're not hiring",
             "Subscriptions charge for access, not outcomes. A slow hiring "
             "quarter costs exactly the same as a busy one."),
            ("Slot limits shape your hiring",
             "Per-slot pricing quietly discourages posting the roles you "
             "actually need to fill."),
            ("Cancel and your pipeline goes with it",
             "Access-based pricing means your hiring stops the day you stop "
             "paying."),
        ],
        "audience": "employer",
    },
    {
        "slug": "gohire-alternative",
        "name": "GoHire",
        "title": "GoHire Alternative for Small Businesses | Roven",
        "desc": "A GoHire alternative built for small businesses: free to "
                "post, no monthly plan, one flat fee only when you hire.",
        "h1": "A GoHire alternative with no monthly plan at all.",
        "model": "GoHire is applicant-tracking software sold on monthly "
                 "tiers, with features and job limits gated by plan level.",
        "pain": [
            ("You pay before you get value",
             "Software subscriptions charge on day one. Roven charges after "
             "someone accepts your offer."),
            ("Tiers gate the basics",
             "Plan-based pricing tends to put the useful parts a tier above "
             "wherever you are."),
            ("An ATS doesn't bring you candidates",
             "Tracking applicants and finding them are different problems. "
             "Roven's match engine emails fitting candidates the moment your "
             "role goes live."),
        ],
        "audience": "employer",
    },
    {
        "slug": "linkedin-jobs-alternative",
        "name": "LinkedIn Jobs",
        "title": "LinkedIn Jobs Alternative for Local Hiring | Roven",
        "desc": "A LinkedIn Jobs alternative for local and trade hiring. Free "
                "to post, pay only on a completed hire, every employer "
                "verified.",
        "h1": "A LinkedIn Jobs alternative for the roles LinkedIn isn't built for.",
        "model": "LinkedIn sells job promotion on a daily budget model, "
                 "competing for attention inside a professional social "
                 "network whose audience skews heavily toward office and "
                 "corporate roles.",
        "pain": [
            ("The audience may not be your workforce",
             "Technicians, stylists, dental assistants and kitchen staff are "
             "not primarily job hunting on a corporate social network."),
            ("Daily budgets are a meter",
             "Promoted posts spend continuously and stop being seen when the "
             "budget does."),
            ("Applications without accountability",
             "Nothing published tracks whether applicants ever get answered."),
        ],
        "audience": "employer",
    },
    {
        "slug": "craigslist-jobs-alternative",
        "name": "Craigslist Jobs",
        "title": "Craigslist Jobs Alternative | Verified Employers | Roven",
        "desc": "A Craigslist jobs alternative with verified employers and "
                "real applicants. Free to post, one flat fee per hire.",
        "h1": "A Craigslist alternative where every employer is verified.",
        "model": "Craigslist charges a flat posting fee in most job "
                 "categories and markets, with no verification of who is "
                 "posting and no structure around what happens next.",
        "pain": [
            ("Anyone can post as anyone",
             "No verification means candidates approach every listing warily "
             "- including yours."),
            ("You pay to post, then you're on your own",
             "The fee buys placement, not applicants, and certainly not a "
             "hire."),
            ("No structure after the application",
             "Everything after 'they emailed you' is a spreadsheet you "
             "maintain by hand."),
        ],
        "audience": "employer",
    },
    {
        "slug": "monster-alternative",
        "name": "Monster",
        "title": "Monster Alternative for Employers | Roven",
        "desc": "A Monster alternative with no subscription and no resume "
                "database fees. Free to post, pay only when you hire.",
        "h1": "A Monster alternative that charges on outcomes, not access.",
        "model": "Monster sells employer plans and resume-database access on "
                 "subscription terms, priced by job slots and search seats.",
        "pain": [
            ("Database access is a subscription, not a hire",
             "Paying to search resumes is paying for access. It guarantees "
             "nothing about filling the role."),
            ("Recurring cost, occasional need",
             "Most small employers hire in bursts. Subscriptions bill "
             "steadily regardless."),
            ("Cold outreach to unwilling candidates",
             "Roven works the other way: candidates opt in, and the engine "
             "brings the fitting ones to your listing."),
        ],
        "audience": "employer",
    },
    {
        "slug": "staffing-agency-alternative",
        "name": "A Staffing Agency",
        "title": "Staffing Agency Alternative | Hire Direct, Pay Once | Roven",
        "desc": "A staffing agency alternative: hire directly, pay one flat "
                "placement fee instead of an ongoing hourly markup. Verified "
                "candidates, free to post.",
        "h1": "A staffing agency alternative where the markup ends.",
        "model": "Staffing agencies place a worker on their own payroll and "
                 "bill you an hourly rate well above the wage. That markup "
                 "applies to every hour worked, for as long as the placement "
                 "lasts - and converting the person to your own payroll "
                 "usually carries a separate buyout fee.",
        "pain": [
            ("The cost never stops",
             "A one-time fee ends. An hourly uplift runs for the life of the "
             "placement, which is why a long assignment can cost several "
             "times a direct-hire fee."),
            ("You don't choose, you receive",
             "Agencies send who they have on the bench. You are hiring their "
             "inventory, not the market."),
            ("Converting them costs again",
             "Wanting to keep someone good typically triggers a conversion "
             "fee on top of everything already paid."),
        ],
        "audience": "employer",
    },
    {
        "slug": "recruiter-alternative",
        "name": "A Contingency Recruiter",
        "title": "Recruiter Alternative | Flat Fee Per Hire | Roven",
        "desc": "A recruiter alternative that charges a flat fee per hire "
                "instead of a percentage of salary. Free to post, verified "
                "candidates, pay only on a completed hire.",
        "h1": "A recruiter alternative that doesn't take a slice of the salary.",
        "model": "Contingency recruiters typically charge a percentage of the "
                 "hire's first-year salary, commonly quoted between 15% and "
                 "25%. The better the person you hire, the more the "
                 "introduction costs you.",
        "pain": [
            ("The fee scales with the salary, not the work",
             "Finding a $90,000 hire is not three times the work of finding a "
             "$30,000 hire, but the percentage says it is."),
            ("It penalises hiring well",
             "Paying more for a stronger candidate is a strange incentive to "
             "build a hiring budget around."),
            ("One role, one relationship",
             "A recruiter fills the role in front of them. A marketplace "
             "keeps working for the next one, and the one after that."),
        ],
        "audience": "employer",
    },
    {
        "slug": "free-resume-builder",
        "name": None,
        "title": "Free Resume Builder - No Download Fee, No Watermark | Roven",
        "desc": "A genuinely free resume builder. Build it, improve it with "
                "AI, download the PDF - no payment, no watermark, no trial. "
                "ATS-safe templates.",
        "h1": "A free resume builder that actually lets you download it.",
        "model": None,
        "pain": None,
        "audience": "candidate",
    },
]

CSS = """
.alt-hero{background:radial-gradient(1000px 460px at 78% -10%,rgba(28,164,95,.30),transparent 60%),linear-gradient(180deg,#101b14 0%,#0E141D 100%);border-bottom:1px solid rgba(58,219,139,.18);padding:64px 0 56px}
.alt-plate{display:inline-flex;align-items:center;gap:8px;background:rgba(28,164,95,.16);border:1px solid rgba(58,219,139,.5);border-radius:100px;padding:7px 14px;margin-bottom:18px}
.alt-plate span{font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.14em;font-weight:700;color:#3ADB8B}
.alt-hero h1{font-family:'Bricolage Grotesque',sans-serif;font-size:clamp(30px,4.2vw,46px);font-weight:800;letter-spacing:-1.4px;line-height:1.08;color:#fff;margin:0 0 16px;max-width:820px}
.alt-lede{font-size:16.5px;line-height:1.65;color:rgba(255,255,255,.74);max-width:660px;margin:0 0 24px}
.alt-cta{display:inline-block;background:#1CA45F;color:#fff;text-decoration:none;font-weight:600;font-size:15px;padding:14px 28px;border-radius:100px;box-shadow:0 6px 24px rgba(28,164,95,.32)}
.alt-cta.ghost{background:transparent;border:1px solid rgba(255,255,255,.26);box-shadow:none;margin-left:10px}
.alt-table{width:100%;border-collapse:separate;border-spacing:0;margin:26px 0 10px;border:1px solid rgba(255,255,255,.13);border-radius:18px;overflow:hidden}
.alt-table th,.alt-table td{padding:15px 16px;text-align:left;font-size:14px;line-height:1.5;border-bottom:1px solid rgba(255,255,255,.08)}
.alt-table thead th{font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.12em;font-weight:700;color:rgba(255,255,255,.55);background:rgba(255,255,255,.04)}
.alt-table thead th.rov{color:#3ADB8B;background:rgba(28,164,95,.12)}
.alt-table td.q{font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.1em;font-weight:700;color:rgba(255,255,255,.5)}
.alt-table td.them{color:rgba(255,255,255,.6)}
.alt-table td.rov{color:#fff;background:rgba(28,164,95,.09);font-weight:500}
.alt-table td.rov b{color:#3ADB8B}
.alt-table tr:last-child td{border-bottom:none}
.alt-points{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;margin-top:22px}
.alt-point{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.12);border-radius:16px;padding:20px}
.alt-point h3{font-family:'Bricolage Grotesque',sans-serif;font-size:17px;margin:0 0 8px;color:#fff;letter-spacing:-.3px}
.alt-point p{font-size:13.5px;line-height:1.6;color:rgba(255,255,255,.65);margin:0}
.alt-fair{font-size:12.5px;line-height:1.7;color:rgba(255,255,255,.45);border-left:2px solid rgba(255,255,255,.16);padding-left:14px;margin-top:26px;max-width:720px}
@media(max-width:640px){.alt-table th,.alt-table td{padding:11px 10px;font-size:12.5px}.alt-cta.ghost{margin-left:0;margin-top:10px}}
"""

NAV = """<nav class="nav">
  <div class="wrap nav-inner">
    <a class="logo-link" href="/" aria-label="Roven home"><img class="logo-img" src="/logo.png" alt="Roven" width="640" height="293"></a>
    <button class="nav-toggle" aria-expanded="false" aria-controls="navlinks">MENU</button>
    <ul class="nav-links" id="navlinks">
      <li><a href="/how-it-works">How it works</a></li>
      <li><a href="/employers">For employers</a></li>
      <li><a href="/about">About</a></li>
    </ul>
  </div>
</nav>
<script src="/motion.js" defer></script>"""

FOOTER = """<footer class="footer">
  <div class="wrap">
    <div class="footer-social" style="display:flex;gap:14px;align-items:center;margin:26px 0 18px">
      <a href="https://facebook.com/hireroven" target="_blank" rel="noopener" aria-label="Roven on Facebook" style="display:inline-flex;width:36px;height:36px;border-radius:100px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.14);align-items:center;justify-content:center;color:rgba(255,255,255,.75);text-decoration:none"><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M13.5 21v-8h2.7l.4-3.2h-3.1V7.7c0-.9.3-1.6 1.6-1.6h1.7V3.2c-.3 0-1.3-.1-2.5-.1-2.5 0-4.2 1.5-4.2 4.3v2.4H7.4V13h2.7v8h3.4z"/></svg></a>
      <a href="https://instagram.com/hireroven" target="_blank" rel="noopener" aria-label="Roven on Instagram" style="display:inline-flex;width:36px;height:36px;border-radius:100px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.14);align-items:center;justify-content:center;color:rgba(255,255,255,.75);text-decoration:none"><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2.2c3.2 0 3.6 0 4.9.1 1.2.1 1.8.2 2.2.4.6.2 1 .5 1.4.9.4.4.7.8.9 1.4.2.4.4 1 .4 2.2.1 1.3.1 1.7.1 4.9s0 3.6-.1 4.9c-.1 1.2-.2 1.8-.4 2.2-.2.6-.5 1-.9 1.4-.4.4-.8.7-1.4.9-.4.2-1 .4-2.2.4-1.3.1-1.7.1-4.9.1s-3.6 0-4.9-.1c-1.2-.1-1.8-.2-2.2-.4-.6-.2-1-.5-1.4-.9-.4-.4-.7-.8-.9-1.4-.2-.4-.4-1-.4-2.2C2.2 15.6 2.2 15.2 2.2 12s0-3.6.1-4.9c.1-1.2.2-1.8.4-2.2.2-.6.5-1 .9-1.4.4-.4.8-.7 1.4-.9.4-.2 1-.4 2.2-.4C8.4 2.2 8.8 2.2 12 2.2zm0 1.8c-3.1 0-3.5 0-4.8.1-1.1.1-1.5.2-1.7.3-.4.2-.7.4-1 .7-.3.3-.5.6-.7 1-.1.2-.3.6-.3 1.7-.1 1.3-.1 1.7-.1 4.8s0 3.5.1 4.8c.1 1.1.2 1.5.3 1.7.2.4.4.7.7 1 .3.3.6.5 1 .7.2.1.6.3 1.7.3 1.3.1 1.7.1 4.8.1s3.5 0 4.8-.1c1.1-.1 1.5-.2 1.7-.3.4-.2.7-.4 1-.7.3-.3.5-.6.7-1 .1-.2.3-.6.3-1.7.1-1.3.1-1.7.1-4.8s0-3.5-.1-4.8c-.1-1.1-.2-1.5-.3-1.7-.2-.4-.4-.7-.7-1-.3-.3-.6-.5-1-.7-.2-.1-.6-.3-1.7-.3-1.3-.1-1.7-.1-4.8-.1zm0 3.1a4.9 4.9 0 1 1 0 9.8 4.9 4.9 0 0 1 0-9.8zm0 1.8a3.1 3.1 0 1 0 0 6.2 3.1 3.1 0 0 0 0-6.2zm5.1-3.1a1.1 1.1 0 1 1 0 2.3 1.1 1.1 0 0 1 0-2.3z"/></svg></a>
      <a href="https://youtube.com/@hireroven" target="_blank" rel="noopener" aria-label="Roven on YouTube" style="display:inline-flex;width:36px;height:36px;border-radius:100px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.14);align-items:center;justify-content:center;color:rgba(255,255,255,.75);text-decoration:none"><svg width="17" height="17" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M21.6 7.2s-.2-1.4-.8-2c-.7-.8-1.6-.8-2-.9C16 4 12 4 12 4s-4 0-6.8.3c-.4 0-1.2.1-2 .9-.6.6-.8 2-.8 2S2.2 8.9 2.2 10.5v1.5c0 1.6.2 3.3.2 3.3s.2 1.4.8 2c.7.8 1.7.8 2.1.9 1.6.1 6.7.3 6.7.3s4 0 6.8-.3c.4 0 1.2-.1 2-.9.6-.6.8-2 .8-2s.2-1.6.2-3.3v-1.5c0-1.6-.2-3.3-.2-3.3zM9.9 14.9V8.6l5.4 3.2-5.4 3.1z"/></svg></a>
      <a href="https://tiktok.com/@hireroven" target="_blank" rel="noopener" aria-label="Roven on TikTok" style="display:inline-flex;width:36px;height:36px;border-radius:100px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.14);align-items:center;justify-content:center;color:rgba(255,255,255,.75);text-decoration:none"><svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M16.6 5.8a5.4 5.4 0 0 1-1.2-3.3h-3v12.2a2.9 2.9 0 1 1-2.1-2.8V8.7a6 6 0 1 0 5.2 5.9V9.2a8.4 8.4 0 0 0 4.9 1.6V7.7a5.4 5.4 0 0 1-3.8-1.9z"/></svg></a>
    </div>
      <p style="font-size:11px;line-height:1.6;color:rgba(255,255,255,.4);max-width:640px;margin:0 0 14px">Roven is a hiring marketplace. Roven is not an employment agency, staffing firm, or recruiter, and is not a party to any employment relationship formed through the platform.</p>
    <div class="footer-legal">
      <span>&copy; 2026 ROVEN &middot; ROVEN HR, LLC</span>
    </div>
  </div>
</footer>"""


def head(c):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{c['title']}</title>
<meta name="description" content="{c['desc']}">
<link rel="canonical" href="https://rovenhr.com/alternatives/{c['slug']}">
<meta property="og:title" content="{c['title']}">
<meta property="og:description" content="{c['desc']}">
<meta property="og:url" content="https://rovenhr.com/alternatives/{c['slug']}">
<meta property="og:type" content="website">
<meta property="og:image" content="https://rovenhr.com/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@500;600;700;800&family=Instrument+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="icon" type="image/x-icon" href="/favicon.ico">
<link rel="stylesheet" href="/styles.css">
<style>{CSS}</style>
</head>
<body>
{NAV}
<div class="scroll-progress" aria-hidden="true"><div class="bar"></div></div>"""


def faq_schema(items):
    q = ",".join(
        '{"@type":"Question","name":"%s","acceptedAnswer":{"@type":"Answer",'
        '"text":"%s"}}' % (a.replace('"', "'"), b.replace('"', "'"))
        for a, b in items)
    return ('<script type="application/ld+json">{"@context":'
            '"https://schema.org","@type":"FAQPage","mainEntity":[%s]}</script>'
            % q)


def employer_page(c):
    n = c["name"]
    rows = [
        ("TO POST", f"{n}: paid, on their published terms", "<b>$0.</b> Always free."),
        ("YOU PAY WHEN", "Regardless of whether you hire",
         "<b>Only when your offer is accepted</b>"),
        ("APPLICANTS", "Open to bulk-apply tools and bots",
         "<b>Verified humans</b> with real work history"),
        ("VISIBILITY", "Influenced by ad spend",
         "Surfaces on <b>fit</b>, never on budget"),
        ("LISTING FRESHNESS", "Stale listings can linger indefinitely",
         "<b>30-day confirmation clock</b> or it comes down"),
        ("ACCOUNTABILITY", "Response rates not published",
         "<b>Your response record is public</b> - and unbuyable"),
    ]
    table = "".join(
        f'<tr><td class="q">{a}</td><td class="them">{b}</td>'
        f'<td class="rov">{d}</td></tr>' for a, b, d in rows)
    points = "".join(
        f'<div class="alt-point"><h3>{t}</h3><p>{p}</p></div>'
        for t, p in c["pain"])

    faqs = [
        (f"What is the best alternative to {n} for small businesses?",
         "Roven is free to post and charges one flat placement fee only when "
         "a candidate accepts your offer. There is no subscription, no "
         "per-application billing and no sponsored placement."),
        ("How much does Roven cost?",
         "List pricing is $249 per contract, part-time or temporary hire and "
         "$499 per full-time W-2 hire, with launch pricing currently at $99 "
         "and $199. Placement fees are waived entirely while the marketplace "
         "grows, and the first 100 verified employers keep 50% off list "
         "pricing for life."),
        (f"Is Roven really free compared to {n}?",
         "Posting, searching and messaging are free permanently. The only "
         "charge Roven ever makes is a placement fee at the moment a hire is "
         "confirmed, and that fee is currently waived."),
        ("What happens if the hire doesn't work out?",
         "If a hire ends within 30 days, the placement fee is credited in "
         "full toward your next placement."),
    ]
    return f"""{head(c)}
<header class="alt-hero">
  <div class="wrap">
    <div class="alt-plate"><span>ROVEN VS {n.upper()}</span></div>
    <h1>{c['h1']}</h1>
    <p class="alt-lede">{c['model']}<br><br>Roven works the other way round: posting is free, every employer is verified, and one flat fee applies only when someone accepts your offer.</p>
    <a class="alt-cta" href="https://app.rovenhr.com">Post a role free</a>
    <a class="alt-cta ghost" href="/employers">See the pricing</a>
  </div>
</header>

<section class="section">
  <div class="wrap">
    <p class="kicker">Side by side</p>
    <h2>How the two models differ.</h2>
    <table class="alt-table">
      <thead><tr><th></th><th>{n.upper()}</th><th class="rov">ROVEN</th></tr></thead>
      <tbody>{table}</tbody>
    </table>
    <p class="alt-fair">We describe {n}'s business model in general terms only and quote no prices for it, because their pricing changes and a wrong number on a page about honesty would be worth less than nothing. Check their current rates yourself, then compare. If anything here is out of date, tell us at <a href="mailto:hello@rovenhr.com" style="color:#3ADB8B">hello@rovenhr.com</a> and we'll correct it.</p>
  </div>
</section>

<section class="section tint">
  <div class="wrap">
    <p class="kicker">Why employers switch</p>
    <h2>The three complaints we hear most.</h2>
    <div class="alt-points">{points}</div>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <p class="kicker">What you get instead</p>
    <h2>Free to post. Paid only on a hire.</h2>
    <div class="alt-points">
      <div class="alt-point"><h3>Verified employers only</h3><p>Every business is checked before it can post. Candidates know your listing is real, which is why they take it seriously.</p></div>
      <div class="alt-point"><h3>The engine finds candidates</h3><p>The moment your role goes live, matching candidates are emailed - before it reaches the general feed.</p></div>
      <div class="alt-point"><h3>AI writes the job post</h3><p>Give rough notes, get an editable description. It won't invent pay, benefits or requirements you didn't state.</p></div>
      <div class="alt-point"><h3>Interviews scheduled in-app</h3><p>Offer up to three times, they pick one, both sides get it in writing. No phone tag.</p></div>
      <div class="alt-point"><h3>A public accountability record</h3><p>Your response rate and speed are computed from real activity and shown on every listing. It can't be edited or bought - only earned.</p></div>
      <div class="alt-point"><h3>30-day guarantee</h3><p>If a hire ends within 30 days, the fee is credited in full toward your next placement.</p></div>
    </div>
  </div>
</section>

<section class="section cta-band">
  <div class="wrap" style="text-align:center">
    <p class="kicker" style="text-align:center">Founding employers - first 100, nationwide</p>
    <h2 style="max-width:none">Try it while it costs nothing.</h2>
    <p class="sub">Placement fees are waived entirely right now. The first 100 verified employers in the US lock founding terms: free for 12 months after pricing activates, then 50% off list pricing for life.</p>
    <a class="alt-cta" href="https://app.rovenhr.com">Create your employer account</a>
    <a class="alt-cta ghost" href="/contact">Talk to us first</a>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <p class="kicker">Questions</p>
    <h2>Straight answers.</h2>
    <div class="faq">
      {''.join(f'<details><summary>{a}</summary><p>{b}</p></details>' for a, b in faqs)}
    </div>
  </div>
</section>
{faq_schema(faqs)}
{FOOTER}
</body>
</html>"""


def resume_page(c):
    faqs = [
        ("Is the Roven resume builder really free?",
         "Yes. Build it, improve it, download the PDF - no payment, no trial, "
         "no watermark. Most resume builders let you build free and then "
         "charge to download. We don't."),
        ("Do I need an account?",
         "Yes, a free Roven account. The builder works from your work history, "
         "so you enter it once - by uploading a resume or typing it in - and "
         "it becomes both your resume and your Roven profile."),
        ("Are the templates ATS-friendly?",
         "Every template is single-column with real selectable text and "
         "standard section headings, which is what applicant tracking systems "
         "parse reliably. Multi-column designs are the most common reason a "
         "resume gets mangled before a human ever reads it."),
        ("Can I use the resume anywhere, or only on Roven?",
         "Anywhere. It's your document. Download it and send it wherever you "
         "want - there's no watermark and no restriction."),
        ("What does the AI actually change?",
         "It rewrites bullets to be specific and verb-first, drafts a summary "
         "from your material, and flags where a number would strengthen a "
         "claim. It will never invent employers, dates, metrics or "
         "certifications you didn't provide."),
    ]
    return f"""{head(c)}
<header class="alt-hero">
  <div class="wrap">
    <div class="alt-plate"><span>FREE RESUME BUILDER</span></div>
    <h1>{c['h1']}</h1>
    <p class="alt-lede">Most resume builders let you build one free, then ask for a card before you can download the file you just made. Roven doesn't. Build it, improve it with AI, download the PDF. No payment, no trial, no watermark.</p>
    <a class="alt-cta" href="https://app.rovenhr.com">Build my resume free</a>
    <a class="alt-cta ghost" href="/how-it-works">How Roven works</a>
  </div>
</header>

<section class="section">
  <div class="wrap">
    <p class="kicker">How it works</p>
    <h2>Three steps, about five minutes.</h2>
    <div class="steps">
      <div class="step"><span class="step-num">01</span><div><h4>Add your work history</h4><p>Upload an existing resume and we read it into a structured profile, or type your history in if you don't have one yet. You only do this once.</p></div></div>
      <div class="step"><span class="step-num">02</span><div><h4>Let the AI sharpen it</h4><p>Bullets get rewritten to be specific and verb-first, a summary is drafted from your own material, and you get direct notes on what would make it stronger. Nothing is invented - no fake metrics, no borrowed job titles.</p></div></div>
      <div class="step"><span class="step-num">03</span><div><h4>Pick a template and download</h4><p>Three ATS-safe layouts. Download the PDF and use it anywhere - Roven, Indeed, email, print. It's yours.</p></div></div>
    </div>
  </div>
</section>

<section class="section tint">
  <div class="wrap">
    <p class="kicker">Why ATS-safe matters</p>
    <h2>Pretty resumes get rejected by software.</h2>
    <div class="alt-points">
      <div class="alt-point"><h3>Single column, always</h3><p>Two-column layouts are the most common reason an applicant tracking system scrambles a resume before a person sees it. Every Roven template is single-column.</p></div>
      <div class="alt-point"><h3>Real text, not pictures of text</h3><p>Graphics-heavy templates often export as images that parsers can't read at all. Ours stay selectable and machine-readable.</p></div>
      <div class="alt-point"><h3>Standard section headings</h3><p>Parsers look for the words Experience, Education and Skills. Creative alternatives like "Where I've Made an Impact" quietly break them.</p></div>
    </div>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <p class="kicker">And then</p>
    <h2>Your resume becomes a profile that works while you don't.</h2>
    <p class="sub">Because the builder runs on your Roven profile, finishing your resume also arms the match engine. Every new role posted on Roven is scored against your history, and when one fits you get an email - before it reaches the general feed. Every employer is verified, every listing shows the pay, and every application gets a real answer.</p>
    <a class="alt-cta" href="https://app.rovenhr.com">Start free</a>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <p class="kicker">Questions</p>
    <h2>Straight answers.</h2>
    <div class="faq">
      {''.join(f'<details><summary>{a}</summary><p>{b}</p></details>' for a, b in faqs)}
    </div>
  </div>
</section>
{faq_schema(faqs)}
{FOOTER}
</body>
</html>"""


def index_page(items):
    cards = "".join(
        f'<div class="alt-point"><h3><a href="/alternatives/{c["slug"]}" '
        f'style="color:#fff;text-decoration:none">{c["h1"]}</a></h3>'
        f'<p>{c["desc"]}</p></div>' for c in items)
    c = {"slug": "", "title": "Roven vs the big job boards | Comparisons",
         "desc": "How Roven compares to Indeed, ZipRecruiter, GoHire, "
                 "LinkedIn Jobs, Monster and Craigslist - and why we only "
                 "charge when you actually hire.",
         "h1": "Roven vs the big job boards."}
    return f"""{head(c)}
<header class="alt-hero">
  <div class="wrap">
    <div class="alt-plate"><span>COMPARISONS</span></div>
    <h1>Roven vs the big job boards.</h1>
    <p class="alt-lede">Every one of them charges you for access, applications or ad placement. Roven charges one flat fee when someone accepts your offer - and nothing before that.</p>
    <a class="alt-cta" href="/employers">See our pricing</a>
  </div>
</header>
<section class="section">
  <div class="wrap">
    <p class="kicker">Side by side</p>
    <h2>Pick your current platform.</h2>
    <div class="alt-points">{cards}</div>
  </div>
</section>
{FOOTER}
</body>
</html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="roven-site root")
    args = ap.parse_args()

    outdir = os.path.join(args.out, "alternatives")
    os.makedirs(outdir, exist_ok=True)

    written = []
    for c in COMPETITORS:
        html = resume_page(c) if c["audience"] == "candidate" else employer_page(c)
        path = os.path.join(outdir, f"{c['slug']}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        written.append(c["slug"])
        print(f"  wrote alternatives/{c['slug']}.html")

    with open(os.path.join(outdir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_page([c for c in COMPETITORS if c["audience"] == "employer"]))
    print("  wrote alternatives/index.html")

    # sitemap for just these pages
    today = date.today().isoformat()
    slugs = written + [""]          # "" -> the directory index
    urls = "".join(
        f"<url><loc>https://rovenhr.com/alternatives/{s}</loc>"
        f"<lastmod>{today}</lastmod><changefreq>monthly</changefreq>"
        f"<priority>{'0.9' if s == '' else '0.8'}</priority></url>"
        for s in slugs)
    sm = ('<?xml version="1.0" encoding="UTF-8"?>'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
          f'{urls}</urlset>')
    with open(os.path.join(args.out, "sitemap-alternatives.xml"), "w",
              encoding="utf-8") as f:
        f.write(sm)
    print(f"  wrote sitemap-alternatives.xml ({len(slugs)} urls)")
    print(f"\n{len(written)+1} pages generated. Deploy, then submit "
          f"sitemap-alternatives.xml in Google Search Console.")


if __name__ == "__main__":
    main()
