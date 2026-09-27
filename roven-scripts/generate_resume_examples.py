#!/usr/bin/env python3
# ============================================================================
# ROVEN - generate_resume_examples.py
# Build ID: JC-ROVEN-RESUMEEX-0801-002
#
# Programmatic SEO for "{role} resume example" - deliberately aimed at the
# trades, healthcare support, service and event roles the big AI resume sites
# ignore. They all target software engineer / marketing manager / data
# analyst, which are the most competitive terms on the internet. Nobody is
# fighting for "HVAC technician resume example".
#
# Every example person is fictional and generically named. Every bullet is
# written to model good practice (verb-first, specific, honest) so the page
# teaches as well as ranks.
#
# Usage: python generate_resume_examples.py --out C:\\Users\\kurvh\\roven-site
# ============================================================================

import argparse
import os
from datetime import date

# ---------------------------------------------------------------- content

ROLES = [
    {
        "slug": "hvac-technician",
        "title": "HVAC Technician",
        "family": "Skilled trades",
        "name": "Jordan Reyes",
        "summary": "HVAC service technician with 8 years in residential "
                   "diagnostics and repair. EPA 608 Universal certified, "
                   "comfortable running a full service board unsupervised.",
        "jobs": [
            ("Lead Service Technician", "Residential HVAC company",
             "2021 - Present",
             ["Run 8-10 residential service calls per day on split systems, "
              "heat pumps and package units.",
              "Diagnose electrical faults, refrigerant issues and airflow "
              "problems, documenting root cause on every ticket.",
              "Train junior technicians on refrigerant handling and EPA "
              "compliance.",
              "Hold a 4.9 customer rating across 600+ completed jobs."]),
            ("HVAC Technician", "Mechanical services contractor",
             "2018 - 2021",
             ["Performed preventative maintenance on 200+ residential "
              "accounts on a seasonal schedule.",
              "Reduced repeat callbacks by documenting findings and parts "
              "used on each visit."]),
        ],
        "skills": ["Refrigerant handling", "Electrical diagnostics",
                   "Brazing", "Ductwork", "Heat pumps", "Preventative "
                   "maintenance", "Customer communication"],
        "certs": ["EPA 608 Universal", "NATE Core"],
        "looks_for": [
            ("Certifications up front",
             "EPA 608 is a legal requirement for handling refrigerant. Put it "
             "where it cannot be missed - not buried at the bottom."),
            ("Call volume and system types",
             "\"Residential split systems, 8-10 calls a day\" tells a service "
             "manager more about you than any adjective will."),
            ("Whether you can work unsupervised",
             "Small shops are hiring someone to send out alone. Say plainly "
             "that you run your own board."),
        ],
    },
    {
        "slug": "dental-assistant",
        "title": "Dental Assistant",
        "family": "Healthcare support",
        "name": "Alex Morgan",
        "summary": "Dental assistant with 5 years chairside in general and "
                   "restorative practice. Radiography certified, fluent in "
                   "Spanish, experienced with Dentrix.",
        "jobs": [
            ("Dental Assistant", "General dentistry practice", "2022 - Present",
             ["Assist chairside on 20-25 patients per day across restorative, "
              "hygiene and emergency appointments.",
              "Take and process digital radiographs; maintain imaging "
              "equipment and infection control logs.",
              "Manage sterilization workflow and instrument inventory for a "
              "four-operatory practice.",
              "Translate for Spanish-speaking patients during treatment "
              "planning."]),
            ("Dental Assistant", "Family dental office", "2021 - 2022",
             ["Prepared operatories, charted treatment and handled patient "
              "intake for two providers.",
              "Scheduled recall appointments, improving hygiene "
              "re-appointment consistency."]),
        ],
        "skills": ["Chairside assisting", "Digital radiography",
                   "Sterilization and infection control", "Dentrix",
                   "Treatment charting", "Spanish (fluent)"],
        "certs": ["Radiography certification", "BLS / CPR"],
        "looks_for": [
            ("State credentials and radiography",
             "Requirements vary by state and practices screen for them first. "
             "List exactly what you hold."),
            ("Practice software",
             "Dentrix, Eaglesoft or Open Dental - naming the one you know "
             "shortens your training time, and offices notice."),
            ("Patient volume per day",
             "It tells an office manager whether you can keep up with their "
             "schedule."),
        ],
    },
    {
        "slug": "medical-assistant",
        "title": "Medical Assistant",
        "family": "Healthcare support",
        "name": "Sam Rivera",
        "summary": "Certified medical assistant with 6 years in family "
                   "medicine and urgent care. Comfortable with both clinical "
                   "and front-office duties in a high-volume clinic.",
        "jobs": [
            ("Medical Assistant", "Family medicine clinic", "2021 - Present",
             ["Room and triage 30+ patients daily, recording vitals and "
              "history in Epic.",
              "Draw blood, administer injections and run point-of-care "
              "testing.",
              "Manage prior authorizations and referral coordination for "
              "three providers.",
              "Trained two new assistants on clinic intake workflow."]),
            ("Medical Assistant", "Urgent care center", "2019 - 2021",
             ["Assisted with laceration repair, splinting and in-house "
              "imaging intake.",
              "Maintained supply par levels and controlled-substance logs."]),
        ],
        "skills": ["Phlebotomy", "Vitals and triage", "Injections",
                   "Epic EHR", "Prior authorizations", "Point-of-care "
                   "testing", "Sterile technique"],
        "certs": ["CMA (AAMA)", "BLS / CPR"],
        "looks_for": [
            ("Certification body, spelled out",
             "CMA, RMA and CCMA are different credentials. Name yours "
             "exactly - clinics screen on it."),
            ("EHR system",
             "Epic, Cerner or athenahealth. Knowing theirs saves the clinic "
             "weeks."),
            ("Clinical vs administrative split",
             "Be clear about which you have done. Many postings need both, "
             "and vagueness reads as neither."),
        ],
    },
    {
        "slug": "wedding-photographer",
        "title": "Wedding Photographer",
        "family": "Events and creative",
        "name": "Casey Lin",
        "summary": "Wedding photographer with 7 years shooting full-day "
                   "coverage and second-shooting for studios. Owns a full "
                   "dual-body kit and delivers galleries within three weeks.",
        "jobs": [
            ("Lead Photographer", "Independent studio", "2020 - Present",
             ["Shoot 25-30 full-day weddings per season, from preparation "
              "through reception exit.",
              "Deliver edited galleries of 600-900 images within a "
              "three-week turnaround.",
              "Direct a second shooter and coordinate timelines with "
              "planners and venue staff.",
              "Maintain dual-body coverage with backup gear on every event."]),
            ("Second Shooter", "Regional wedding studios", "2018 - 2020",
             ["Second-shot 40+ weddings across three studios, covering "
              "reception and detail work.",
              "Handled same-night card backup and culling handoff to lead "
              "photographers."]),
        ],
        "skills": ["Full-day wedding coverage", "Off-camera flash",
                   "Lightroom and Capture One", "Timeline coordination",
                   "Second shooting", "Client communication"],
        "certs": [],
        "looks_for": [
            ("Whether you own a working kit",
             "Studios hiring second shooters need to know you arrive with two "
             "bodies, fast glass and backups. Say so."),
            ("Volume and turnaround",
             "\"25-30 weddings a season, three-week delivery\" is the single "
             "most useful line on the page."),
            ("Reliability, stated plainly",
             "The industry's biggest problem is people who cancel the week "
             "of. Any evidence of dependability is worth more than style."),
        ],
    },
    {
        "slug": "line-cook",
        "title": "Line Cook",
        "family": "Food service",
        "name": "Riley Novak",
        "summary": "Line cook with 6 years across scratch kitchens and "
                   "high-volume service. Runs saute and grill stations; "
                   "ServSafe certified.",
        "jobs": [
            ("Line Cook", "Full-service restaurant", "2022 - Present",
             ["Run saute and grill during dinner service averaging 180 covers "
              "a night.",
              "Execute prep lists and station mise for a scratch menu "
              "changing seasonally.",
              "Cover expo on weekend service and train new line staff on "
              "station standards."]),
            ("Prep Cook", "Neighborhood bistro", "2020 - 2022",
             ["Handled daily prep, stocks and butchery for a 12-item menu.",
              "Maintained walk-in organization and dating to health-code "
              "standard."]),
        ],
        "skills": ["Saute", "Grill", "Expo", "Knife skills", "Scratch prep",
                   "Food safety", "High-volume service"],
        "certs": ["ServSafe Food Handler"],
        "looks_for": [
            ("Covers per night",
             "It is the fastest way a chef judges whether you can handle "
             "their volume."),
            ("Which stations you run",
             "Saute, grill, garde manger, expo. Naming them beats \"strong "
             "kitchen experience\" every time."),
            ("ServSafe",
             "Many kitchens require it. If you have it, it belongs near the "
             "top."),
        ],
    },
    {
        "slug": "cdl-truck-driver",
        "title": "CDL Truck Driver",
        "family": "Transportation",
        "name": "Dana Whitfield",
        "summary": "Class A CDL driver with 9 years and 600,000 accident-free "
                   "miles. Regional and OTR experience, clean MVR, current "
                   "DOT medical card.",
        "jobs": [
            ("Class A Driver", "Regional freight carrier", "2020 - Present",
             ["Run regional dry van routes averaging 2,400 miles per week "
              "across five states.",
              "Maintain 98% on-time delivery with full ELD compliance and no "
              "preventable incidents.",
              "Complete pre- and post-trip inspections and manage load "
              "securement on every run."]),
            ("OTR Driver", "National carrier", "2017 - 2020",
             ["Ran long-haul routes coast to coast on a 34-hour reset "
              "schedule.",
              "Handled reefer loads with temperature monitoring and "
              "documentation."]),
        ],
        "skills": ["Class A CDL", "ELD compliance", "Load securement",
                   "Pre-trip inspection", "Reefer", "Dry van", "DOT "
                   "regulations"],
        "certs": ["Class A CDL", "DOT medical card", "TWIC"],
        "looks_for": [
            ("Endorsements and license class",
             "Hazmat, tanker, doubles. These are pass/fail filters - list "
             "them explicitly."),
            ("Safety record in numbers",
             "Accident-free miles and a clean MVR are the two things every "
             "recruiter checks."),
            ("Route type experience",
             "OTR, regional, local and dedicated are different jobs. Say "
             "which you have run."),
        ],
    },
    {
        "slug": "hair-stylist",
        "title": "Hair Stylist",
        "family": "Personal services",
        "name": "Jamie Cortez",
        "summary": "Licensed cosmetologist with 6 years behind the chair. "
                   "Colour specialist with a returning client base and "
                   "consistent retail attachment.",
        "jobs": [
            ("Stylist", "Full-service salon", "2021 - Present",
             ["Maintain a book of 40+ returning clients with 85% rebooking.",
              "Specialize in balayage, colour correction and lived-in colour.",
              "Average $18 retail attachment per service ticket.",
              "Mentor two apprentices on colour formulation and consultation."]),
            ("Stylist", "Neighborhood salon", "2019 - 2021",
             ["Built a client base from walk-in traffic to a mostly booked "
              "schedule within 14 months.",
              "Ran front-desk booking and inventory on closing shifts."]),
        ],
        "skills": ["Balayage", "Colour correction", "Cutting", "Blowouts",
                   "Client consultation", "Retail sales", "Booking systems"],
        "certs": ["State cosmetology license"],
        "looks_for": [
            ("License number and state",
             "Non-negotiable. It is the first thing a salon owner checks."),
            ("Whether you bring a book",
             "A returning client base is the most valuable thing you own. "
             "Rebooking rate says it in one number."),
            ("Retail attachment",
             "Salons make real margin on product. If you sell, say how much."),
        ],
    },
    {
        "slug": "warehouse-associate",
        "title": "Warehouse Associate",
        "family": "Logistics",
        "name": "Morgan Ellis",
        "summary": "Warehouse associate with 5 years in pick-pack, receiving "
                   "and inventory. Forklift certified, comfortable on RF "
                   "scanners and WMS.",
        "jobs": [
            ("Warehouse Associate", "Distribution center", "2022 - Present",
             ["Pick and pack 250+ orders per shift against SLA using RF "
              "scanners.",
              "Operate sit-down and reach forklifts for receiving and "
              "putaway.",
              "Run cycle counts and reconcile inventory variances in the WMS.",
              "Maintain 99.6% pick accuracy across a rolling 12-month "
              "average."]),
            ("Shipping Clerk", "Third-party logistics provider",
             "2020 - 2022",
             ["Staged outbound freight and generated BOLs for LTL carriers.",
              "Verified inbound receipts against purchase orders."]),
        ],
        "skills": ["Forklift (sit-down and reach)", "RF scanning", "WMS",
                   "Cycle counting", "Pick-pack", "Receiving", "Shipping "
                   "documentation"],
        "certs": ["Forklift certification", "OSHA 10"],
        "looks_for": [
            ("Equipment you are certified on",
             "Sit-down, reach, order picker and cherry picker are different "
             "certifications. Be specific."),
            ("Throughput and accuracy",
             "Units per hour and pick accuracy are the two numbers "
             "supervisors hire on."),
            ("Shift availability",
             "Nights and weekends are frequently the open roles. Saying you "
             "are available moves you up the pile."),
        ],
    },
    {
        "slug": "office-manager",
        "title": "Office Manager",
        "family": "Administration",
        "name": "Taylor Brooks",
        "summary": "Office manager with 8 years running operations for small "
                   "businesses. Handles bookkeeping, scheduling, vendors and "
                   "payroll support for teams up to 30.",
        "jobs": [
            ("Office Manager", "Professional services firm", "2020 - Present",
             ["Manage day-to-day operations for a 24-person office including "
              "scheduling, vendors and facilities.",
              "Run AP/AR in QuickBooks and prepare monthly reconciliations "
              "for the accountant.",
              "Administer payroll submission and onboarding paperwork for new "
              "hires.",
              "Renegotiated three vendor contracts, reducing recurring "
              "overhead."]),
            ("Administrative Coordinator", "Regional contractor",
             "2018 - 2020",
             ["Coordinated scheduling and permits across four field crews.",
              "Maintained certificates of insurance and compliance records."]),
        ],
        "skills": ["QuickBooks", "AP/AR", "Payroll administration",
                   "Vendor management", "Scheduling", "Onboarding",
                   "Microsoft 365"],
        "certs": [],
        "looks_for": [
            ("Team and company size",
             "Running a 6-person office and a 60-person office are different "
             "jobs. Name the number."),
            ("Which systems you actually run",
             "QuickBooks, Gusto, ADP. Owners hire for the exact stack they "
             "already use."),
            ("What you own end to end",
             "Payroll, AP, HR paperwork. Ambiguity here costs you the "
             "interview."),
        ],
    },
    {
        "slug": "automotive-technician",
        "title": "Automotive Technician",
        "family": "Skilled trades",
        "name": "Chris Vaughn",
        "summary": "Automotive technician with 7 years in general repair and "
                   "diagnostics. ASE certified in engine repair, brakes and "
                   "electrical systems.",
        "jobs": [
            ("Automotive Technician", "Independent repair shop",
             "2021 - Present",
             ["Diagnose and repair drivability, electrical and brake issues "
              "across domestic and import vehicles.",
              "Average 45-55 flat-rate hours per week with a low comeback "
              "rate.",
              "Perform state inspections and document findings for service "
              "advisors.",
              "Own a full set of hand tools and diagnostic scanner."]),
            ("Lube and Tire Technician", "Service center", "2019 - 2021",
             ["Completed oil services, tire mounting, balancing and "
              "alignments.",
              "Performed multi-point inspections and flagged safety items for "
              "advisors."]),
        ],
        "skills": ["Drivability diagnostics", "Brakes and suspension",
                   "Electrical systems", "Scan tools", "State inspection",
                   "Alignment", "Flat-rate efficiency"],
        "certs": ["ASE A1, A5, A6", "State inspection license"],
        "looks_for": [
            ("ASE certifications by number",
             "A1 through A8 mean specific things to a service manager. List "
             "the ones you hold."),
            ("Flat-rate hours produced",
             "It is how shops measure a technician. If you turn 50 hours, say "
             "50 hours."),
            ("Whether you own tools",
             "A serious question in this trade. Answer it on the resume."),
        ],
    },
    {
        "slug": "electrician",
        "title": "Electrician",
        "family": "Skilled trades",
        "name": "Avery Sloan",
        "summary": "Journeyman electrician with 9 years in residential and "
                   "light commercial work. Licensed, comfortable running "
                   "service calls and small crews.",
        "jobs": [
            ("Journeyman Electrician", "Electrical contractor",
             "2020 - Present",
             ["Run residential service calls and panel upgrades, typically "
              "5-7 calls per day.",
              "Lead a two-person crew on light commercial tenant "
              "improvements.",
              "Pull permits and coordinate inspections with local "
              "jurisdictions.",
              "Troubleshoot circuits, install fixtures and terminate "
              "panels to NEC standard."]),
            ("Apprentice Electrician", "Residential contractor",
             "2016 - 2020",
             ["Completed a four-year apprenticeship covering rough-in, trim "
              "and service work.",
              "Assisted on new-construction rough-ins across 60+ homes."]),
        ],
        "skills": ["Panel upgrades", "Service calls", "NEC code",
                   "Troubleshooting", "Conduit bending", "Permitting",
                   "Crew leadership"],
        "certs": ["Journeyman electrician license", "OSHA 10"],
        "looks_for": [
            ("License class and state",
             "Apprentice, journeyman and master are legally different. State "
             "yours exactly."),
            ("Residential vs commercial vs industrial",
             "Different work entirely. Contractors filter on it immediately."),
            ("Whether you can run a job alone",
             "Small contractors are usually hiring someone to send out "
             "unsupervised."),
        ],
    },
    {
        "slug": "veterinary-technician",
        "title": "Veterinary Technician",
        "family": "Healthcare support",
        "name": "Quinn Delaney",
        "summary": "Credentialed veterinary technician with 6 years in "
                   "general practice and emergency. Experienced in anesthesia "
                   "monitoring, dentistry and client education.",
        "jobs": [
            ("Veterinary Technician", "Small animal practice",
             "2021 - Present",
             ["Monitor anesthesia for 6-10 surgical procedures per day "
              "including dentals and spays.",
              "Place IV catheters, draw blood and run in-house lab "
              "diagnostics.",
              "Take and position digital radiographs including dental "
              "series.",
              "Educate clients on post-operative care and medication "
              "schedules."]),
            ("Veterinary Assistant", "Emergency animal hospital",
             "2019 - 2021",
             ["Triaged incoming emergencies and assisted with critical care "
              "stabilization.",
              "Maintained controlled-substance logs and treatment records."]),
        ],
        "skills": ["Anesthesia monitoring", "IV catheterization",
                   "Dental prophylaxis", "Radiography", "In-house lab",
                   "Client education", "Triage"],
        "certs": ["Credentialed veterinary technician (CVT/RVT/LVT)"],
        "looks_for": [
            ("Credential and state",
             "CVT, RVT and LVT vary by state and matter legally. Spell yours "
             "out."),
            ("Anesthesia experience",
             "The single most-screened skill in this field. Give volume."),
            ("Emergency vs general practice",
             "They are different rhythms. Practices hire for one or the "
             "other."),
        ],
    },
]

CSS = """
.rex-hero{background:radial-gradient(950px 440px at 78% -10%,rgba(28,164,95,.28),transparent 60%),linear-gradient(180deg,#101b14 0%,#0E141D 100%);border-bottom:1px solid rgba(58,219,139,.18);padding:58px 0 50px}
.rex-plate{display:inline-flex;gap:8px;background:rgba(28,164,95,.16);border:1px solid rgba(58,219,139,.5);border-radius:100px;padding:7px 14px;margin-bottom:16px}
.rex-plate span{font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.14em;font-weight:700;color:#3ADB8B}
.rex-hero h1{font-family:'Bricolage Grotesque',sans-serif;font-size:clamp(28px,4vw,44px);font-weight:800;letter-spacing:-1.3px;line-height:1.1;color:#fff;margin:0 0 14px;max-width:800px}
.rex-lede{font-size:16px;line-height:1.65;color:rgba(255,255,255,.72);max-width:660px;margin:0 0 22px}
.rex-cta{display:inline-block;background:#1CA45F;color:#fff;text-decoration:none;font-weight:600;font-size:15px;padding:14px 28px;border-radius:100px;box-shadow:0 6px 24px rgba(28,164,95,.3)}
.rex-cta.ghost{background:transparent;border:1px solid rgba(255,255,255,.26);box-shadow:none;margin-left:10px}
.rex-paper{background:#fff;color:#16202E;border-radius:16px;padding:44px 46px;margin:26px 0 8px;box-shadow:0 26px 60px rgba(0,0,0,.4)}
.rex-paper h2.n{font-family:'Bricolage Grotesque',sans-serif;font-size:27px;margin:0 0 4px;letter-spacing:-.6px;color:#16202E}
.rex-paper .c{font-size:12.5px;color:#5B6874;margin:0 0 14px}
.rex-paper hr{border:none;border-top:1px solid #C9D2DA;margin:0 0 16px}
.rex-paper h3{font-family:'Bricolage Grotesque',sans-serif;font-size:14px;letter-spacing:.02em;color:#16202E;margin:20px 0 8px;text-transform:none}
.rex-paper .role{font-weight:700;font-size:13.5px;margin:12px 0 1px;color:#16202E}
.rex-paper .meta{font-size:12px;color:#5B6874;font-style:italic;margin:0 0 6px}
.rex-paper ul{margin:0 0 4px;padding-left:18px}
.rex-paper li{font-size:13px;line-height:1.55;margin-bottom:4px;color:#16202E}
.rex-paper .flat{font-size:13px;line-height:1.6;color:#16202E;margin:0}
.rex-note{font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.1em;font-weight:700;color:rgba(255,255,255,.4);text-align:center;margin-bottom:26px}
.rex-points{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;margin-top:20px}
.rex-point{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.12);border-radius:16px;padding:20px}
.rex-point h3{font-family:'Bricolage Grotesque',sans-serif;font-size:16.5px;margin:0 0 8px;color:#fff;letter-spacing:-.3px}
.rex-point p{font-size:13.5px;line-height:1.6;color:rgba(255,255,255,.65);margin:0}
.rex-more{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}
.rex-more a{display:inline-block;padding:9px 15px;border-radius:100px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.15);color:rgba(255,255,255,.82);text-decoration:none;font-size:13px}
.rex-more a:hover{border-color:rgba(58,219,139,.5);color:#3ADB8B}
@media(max-width:640px){.rex-paper{padding:26px 22px}.rex-cta.ghost{margin-left:0;margin-top:10px}}
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

FOOTER_LINKS = """      <p style="font-size:11px;line-height:1.6;color:rgba(255,255,255,.4);max-width:640px;margin:0 0 14px">Roven is a hiring marketplace. Roven is not an employment agency, staffing firm, or recruiter, and is not a party to any employment relationship formed through the platform.</p>
    <div class="footer-legal">
      <span>&copy; 2026 ROVEN &middot; ROVEN HR, LLC</span>
    </div>"""


def head(title, desc, canon):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canon}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canon}">
<meta property="og:type" content="article">
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


def paper(r):
    jobs = ""
    for t, comp, dates, bullets in r["jobs"]:
        lis = "".join(f"<li>{b}</li>" for b in bullets)
        jobs += (f'<p class="role">{t} &mdash; {comp}</p>'
                 f'<p class="meta">{dates}</p><ul>{lis}</ul>')
    certs = ""
    if r["certs"]:
        certs = ('<h3>Certifications</h3><p class="flat">'
                 + "  |  ".join(r["certs"]) + "</p>")
    return f"""<div class="rex-paper">
  <h2 class="n">{r['name']}</h2>
  <p class="c">city, state  |  email address  |  phone number</p>
  <hr>
  <h3>Summary</h3>
  <p class="flat">{r['summary']}</p>
  <h3>Experience</h3>
  {jobs}
  <h3>Skills</h3>
  <p class="flat">{"  |  ".join(r['skills'])}</p>
  {certs}
</div>
<p class="rex-note">EXAMPLE ONLY &middot; FICTIONAL PERSON &middot; WRITTEN TO SHOW GOOD PRACTICE, NOT TO BE COPIED VERBATIM</p>"""


def role_page(r, others):
    title = f"{r['title']} Resume Example (2026) | Free Builder | Roven"
    desc = (f"A real {r['title'].lower()} resume example plus what employers "
            f"actually screen for. Build yours free on Roven - no download "
            f"fee, no watermark, ATS-safe.")
    canon = f"https://rovenhr.com/resume-examples/{r['slug']}"
    points = "".join(f'<div class="rex-point"><h3>{t}</h3><p>{p}</p></div>'
                     for t, p in r["looks_for"])
    more = "".join(
        f'<a href="/resume-examples/{o["slug"]}">{o["title"]}</a>'
        for o in others[:8])

    faqs = [
        (f"What should a {r['title'].lower()} resume include?",
         f"A short summary, your work history with specific duties and "
         f"volume, your skills, and any licenses or certifications the role "
         f"legally requires. For a {r['title'].lower()}, employers screen "
         f"hardest on {r['looks_for'][0][0].lower()}."),
        ("How long should it be?",
         "One page for most people. Two pages only if you have more than ten "
         "years of directly relevant work. Nobody is impressed by length."),
        ("Should I use a template with columns and graphics?",
         "No. Two-column layouts and graphics are the most common reason an "
         "applicant tracking system scrambles a resume before a person reads "
         "it. Single column, real text, standard headings."),
        ("Is the Roven resume builder free?",
         "Yes - build it, improve it with AI, and download the PDF with no "
         "payment and no watermark. Most builders charge at the download "
         "step. We don't."),
    ]
    faq_json = ",".join(
        '{"@type":"Question","name":"%s","acceptedAnswer":{"@type":"Answer",'
        '"text":"%s"}}' % (a.replace('"', "'"), b.replace('"', "'"))
        for a, b in faqs)

    return f"""{head(title, desc, canon)}
<header class="rex-hero">
  <div class="wrap">
    <div class="rex-plate"><span>RESUME EXAMPLE &middot; {r['family'].upper()}</span></div>
    <h1>{r['title']} resume example</h1>
    <p class="rex-lede">A complete, honest example of what a strong {r['title'].lower()} resume looks like &mdash; plus the three things employers in this field actually screen for. Then build your own free: no download fee, no watermark, ATS-safe.</p>
    <a class="rex-cta" href="https://app.rovenhr.com">Build mine free</a>
    <a class="rex-cta ghost" href="/alternatives/free-resume-builder">How the builder works</a>
  </div>
</header>

<section class="section">
  <div class="wrap">
    <p class="kicker">The example</p>
    <h2>What a strong one looks like.</h2>
    {paper(r)}
  </div>
</section>

<section class="section tint">
  <div class="wrap">
    <p class="kicker">What employers screen for</p>
    <h2>Three things that decide it.</h2>
    <div class="rex-points">{points}</div>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <p class="kicker">Before you send it</p>
    <h2>Four rules that survive any applicant tracking system.</h2>
    <div class="rex-points">
      <div class="rex-point"><h3>One column, always</h3><p>Two-column layouts are the single most common reason a resume gets mangled before a human sees it.</p></div>
      <div class="rex-point"><h3>Real text, not images</h3><p>Graphics-heavy templates often export as pictures that parsers cannot read at all.</p></div>
      <div class="rex-point"><h3>Standard headings</h3><p>Parsers look for Experience, Education and Skills. Creative alternatives quietly break them.</p></div>
      <div class="rex-point"><h3>Numbers over adjectives</h3><p>"8-10 calls a day" beats "hard working" every time. One is checkable; the other is noise.</p></div>
    </div>
  </div>
</section>

<section class="section cta-band">
  <div class="wrap" style="text-align:center">
    <p class="kicker" style="text-align:center">Free forever for job seekers</p>
    <h2 style="max-width:none">Build yours in about five minutes.</h2>
    <p class="sub">Upload an existing resume and we read it into a profile, or type your history in. The AI sharpens the wording without inventing anything, you pick a template, and you download the PDF. No payment, no watermark, no trial. And your profile then works on its own: every new {r['title'].lower()} role posted on Roven gets scored against you, and you get an email when one fits.</p>
    <a class="rex-cta" href="https://app.rovenhr.com">Start free</a>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <p class="kicker">Questions</p>
    <h2>Straight answers.</h2>
    <div class="faq">
      {''.join(f'<details><summary>{a}</summary><p>{b}</p></details>' for a, b in faqs)}
    </div>
    <p class="kicker" style="margin-top:34px">More examples</p>
    <div class="rex-more">{more}
      <a href="/resume-examples/">See all &rarr;</a>
    </div>
  </div>
</section>
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{faq_json}]}}</script>
<footer class="footer"><div class="wrap">{FOOTER_LINKS}</div></footer>
</body>
</html>"""


def index_page(roles):
    title = "Resume Examples by Job (2026) | Free Resume Builder | Roven"
    desc = ("Free resume examples for trades, healthcare support, service and "
            "event roles - HVAC, dental assistant, CDL driver, line cook and "
            "more. Build yours free, no download fee.")
    canon = "https://rovenhr.com/resume-examples/"
    fams = {}
    for r in roles:
        fams.setdefault(r["family"], []).append(r)
    blocks = ""
    for fam, items in sorted(fams.items()):
        cards = "".join(
            f'<div class="rex-point"><h3><a href="/resume-examples/'
            f'{r["slug"]}" style="color:#fff;text-decoration:none">'
            f'{r["title"]}</a></h3><p>{r["summary"][:120]}...</p></div>'
            for r in items)
        blocks += (f'<p class="kicker" style="margin-top:34px">{fam}</p>'
                   f'<div class="rex-points">{cards}</div>')
    return f"""{head(title, desc, canon)}
<header class="rex-hero">
  <div class="wrap">
    <div class="rex-plate"><span>RESUME EXAMPLES</span></div>
    <h1>Resume examples for the jobs nobody writes about.</h1>
    <p class="rex-lede">Every resume site has an example for software engineers. Almost none have one for an HVAC technician, a dental assistant, a CDL driver or a second shooter. These do &mdash; with what employers in each field actually screen for.</p>
    <a class="rex-cta" href="https://app.rovenhr.com">Build mine free</a>
  </div>
</header>
<section class="section">
  <div class="wrap">
    <h2>Pick your role.</h2>
    {blocks}
  </div>
</section>
<footer class="footer"><div class="wrap">{FOOTER_LINKS}</div></footer>
</body>
</html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    outdir = os.path.join(args.out, "resume-examples")
    os.makedirs(outdir, exist_ok=True)

    for r in ROLES:
        others = [o for o in ROLES if o["slug"] != r["slug"]]
        with open(os.path.join(outdir, f"{r['slug']}.html"), "w",
                  encoding="utf-8") as f:
            f.write(role_page(r, others))
        print(f"  wrote resume-examples/{r['slug']}.html")

    with open(os.path.join(outdir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_page(ROLES))
    print("  wrote resume-examples/index.html")

    today = date.today().isoformat()
    slugs = [r["slug"] for r in ROLES] + [""]     # "" -> directory index
    urls = "".join(
        f"<url><loc>https://rovenhr.com/resume-examples/{s}</loc>"
        f"<lastmod>{today}</lastmod><changefreq>monthly</changefreq>"
        f"<priority>{'0.9' if s == '' else '0.8'}</priority></url>"
        for s in slugs)
    with open(os.path.join(args.out, "sitemap-resume-examples.xml"), "w",
              encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                f'{urls}</urlset>')
    print(f"  wrote sitemap-resume-examples.xml ({len(ROLES)+1} urls)")
    print(f"\n{len(ROLES)+1} pages generated.")


if __name__ == "__main__":
    main()
