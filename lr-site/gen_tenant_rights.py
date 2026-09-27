#!/usr/bin/env python3
"""
LeaseReputation — state tenant-rights guide generator.

Renders /guides/tenant-rights/{st}/ pages from the STATES data below, using
the main generator's template/CSS/header/footer so the pages match the site.
Scaling to new states = adding a STATES entry (researched + cited) and
rerunning. The main generator's sitemap globs this folder automatically.

CONTENT DISCIPLINE (why this file looks the way it does):
  * Every legal fact carries its statute citation inline.
  * Every page carries a not-legal-advice disclaimer + last-reviewed date.
  * Facts come from the statutes / official state guidance, not from
    aggregator blogs (which conflict — e.g. several claim AZ's deposit
    window is 14 calendar days; the state's own guide says 14 days
    EXCLUDING weekends/holidays, per ARS 33-1321(D)).

USAGE:  python gen_tenant_rights.py     then regenerate + kv_sync as usual.
"""

import os
import json
import datetime
import importlib.util

BASE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "gen", os.path.join(BASE, "generate_community_pages.py"))
_gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gen)

SITE_URL = _gen.SITE_URL
APP_URL = _gen.APP_URL
esc = _gen.esc

LAST_REVIEWED = "August 2026"

# ─────────────────────────────────────────────────────────────────────────
# STATE DATA — one entry per state. Add states here as they're researched.
# Each fact: (heading, body_html_with_citations)
# ─────────────────────────────────────────────────────────────────────────
STATES = {
    "az": {
        "name": "Arizona",
        "statute": "Arizona Residential Landlord and Tenant Act (A.R.S. Title 33, Chapter 10)",
        "quick": [
            ("Deposit cap", "1.5 months' rent"),
            ("Deposit return", "14 business days"),
            ("Entry notice", "2 days"),
            ("Month-to-month notice", "30 days"),
        ],
        "sections": [
            ("Security deposits", [
                ("How much can be charged",
                 "Arizona caps all deposits combined — security, cleaning, pet, "
                 "prepaid rent, however they're labeled — at <b>one and one-half "
                 "months' rent</b> (A.R.S. § 33-1321(A)). A fee is only "
                 "non-refundable if the lease specifically says so in writing "
                 "(§ 33-1321(B))."),
                ("Getting it back",
                 "After your tenancy ends, the landlord has <b>14 days — "
                 "excluding Saturdays, Sundays, and legal holidays — </b> to "
                 "return your deposit with an itemized list of any deductions "
                 "(§ 33-1321(D)). Note: many websites wrongly say 14 calendar "
                 "days; the statute excludes weekends and holidays, so it's "
                 "effectively about three weeks."),
                ("The move-out inspection",
                 "You have the right to be told in writing when the move-out "
                 "walk-through will happen so you can be there (§ 33-1321(C)). "
                 "Go — it's your best chance to contest damage claims before "
                 "they become deductions."),
                ("If the landlord wrongfully keeps it",
                 "You can sue for the amount wrongfully withheld <b>plus damages "
                 "equal to twice that amount</b> (§ 33-1321(E)). Small claims "
                 "in Arizona justice courts handles disputes up to $3,500 — no "
                 "lawyer needed. Normal wear and tear (minor scuffs, small nail "
                 "holes, ordinary carpet wear) is never a valid deduction."),
            ]),
            ("Repairs & habitability", [
                ("What the landlord must maintain",
                 "Landlords must keep the unit fit and habitable: working "
                 "plumbing, electrical, heating, and — critically in Arizona — "
                 "<b>air conditioning</b>, plus compliance with building codes "
                 "affecting health and safety (§ 33-1324)."),
                ("If repairs don't happen",
                 "For serious problems, deliver written notice: the landlord "
                 "has <b>10 days</b> to fix most issues (<b>5 days</b> for "
                 "health and safety hazards) or the lease terminates "
                 "(§ 33-1361). For minor repairs, after written notice you can "
                 "hire a licensed contractor and deduct up to the greater of "
                 "$300 or half a month's rent (§ 33-1363)."),
                ("Essential services (A/C, water, power)",
                 "If the landlord fails to supply essential services like "
                 "cooling, water, or heat, you may get them restored yourself "
                 "and deduct the cost, procure substitute housing (rent abates), "
                 "or recover damages (§ 33-1364)."),
            ]),
            ("Privacy & entry", [
                ("Notice before entering",
                 "Except in emergencies, the landlord must give at least "
                 "<b>two days' notice</b> and enter only at reasonable times "
                 "(§ 33-1343)."),
                ("Lockouts are illegal",
                 "A landlord may never lock you out, shut off utilities, or "
                 "remove doors to force you out — only a court can order an "
                 "eviction (§ 33-1367). If it happens, you can recover "
                 "possession plus damages."),
            ]),
            ("Ending a lease & eviction", [
                ("Notice periods",
                 "Month-to-month tenancies require <b>30 days' written "
                 "notice</b> by either side before the next rent due date "
                 "(§ 33-1375). Fixed-term leases end on their own terms."),
                ("Nonpayment timeline",
                 "For unpaid rent, the landlord must serve a <b>5-day notice</b> "
                 "to pay before filing an eviction (§ 33-1368(B)). Paying in "
                 "full within those 5 days stops the case."),
                ("Early termination protections",
                 "Victims of domestic violence may terminate a lease early with "
                 "proper documentation (§ 33-1318), and servicemembers have "
                 "protections under federal law (SCRA)."),
                ("Retaliation is prohibited",
                 "A landlord can't raise rent, cut services, or move to evict "
                 "because you complained to a government agency, requested "
                 "repairs, or joined a tenant organization (§ 33-1381)."),
            ]),
        ],
        "faqs": [
            ("How long does my landlord have to return my security deposit in Arizona?",
             "14 days excluding Saturdays, Sundays, and legal holidays after the "
             "tenancy ends, with an itemized list of deductions (A.R.S. § 33-1321(D)). "
             "If they miss it, you can sue for the amount withheld plus double damages."),
            ("How much can a landlord charge for a security deposit in Arizona?",
             "No more than one and a half months' rent, counting all deposits and "
             "prepaid rent combined (A.R.S. § 33-1321(A))."),
            ("Can my landlord enter my apartment without notice in Arizona?",
             "No — outside emergencies, Arizona requires at least two days' notice "
             "and entry at reasonable times (A.R.S. § 33-1343)."),
            ("What can I do if my AC breaks and my landlord won't fix it in Arizona?",
             "Air conditioning is an essential service. After written notice you can "
             "restore it and deduct the cost, obtain substitute housing while rent "
             "abates, or pursue damages (A.R.S. §§ 33-1324, 33-1364)."),
        ],
    },
    "tx": {
        "name": "Texas",
        "statute": "Texas Property Code, Chapter 92 (Residential Tenancies)",
        "quick": [
            ("Deposit cap", "None"),
            ("Deposit return", "30 days"),
            ("Bad-faith penalty", "$100 + 3x"),
            ("Nonpayment notice", "3 days"),
        ],
        "sections": [
            ("Security deposits", [
                ("No cap — but strict return rules",
                 "Texas sets <b>no limit</b> on deposit amounts, but locks down "
                 "the return: the landlord must refund your deposit — or send a "
                 "written itemized list of deductions — <b>within 30 days</b> of "
                 "the day you surrender the premises (Tex. Prop. Code "
                 "§ 92.103). Give your forwarding address in writing "
                 "(§ 92.107) — the clock doesn't fully run without it."),
                ("The bad-faith hammer",
                 "A landlord who keeps your deposit in bad faith owes you "
                 "<b>$100 plus three times the amount wrongfully withheld, plus "
                 "attorney's fees</b> (§ 92.109) — and missing the 30-day "
                 "deadline creates a legal presumption of bad faith the "
                 "landlord must disprove (§ 92.109(d)). Normal wear and tear is "
                 "never deductible (§ 92.104)."),
            ]),
            ("Repairs", [
                ("Getting things fixed",
                 "For conditions affecting health or safety, send written "
                 "notice (certified mail is safest) and be current on rent. The "
                 "landlord gets a reasonable time — <b>presumed 7 days</b> — to "
                 "repair (§ 92.056). If they don't, remedies include lease "
                 "termination, a court order, damages, or repair-and-deduct up "
                 "to the greater of $500 or one month's rent for qualifying "
                 "conditions (§ 92.0561)."),
            ]),
            ("Privacy, entry & lockouts", [
                ("Entry notice",
                 "Texas has <b>no statute requiring advance notice</b> before a "
                 "landlord enters — your lease controls. Check the entry clause "
                 "before signing; most Texas leases allow entry for repairs and "
                 "showings."),
                ("The Texas lockout rule",
                 "Uniquely, a Texas landlord may change your locks for unpaid "
                 "rent if the lease allows and notices were given — but must "
                 "provide the new key <b>immediately on request, whether or not "
                 "you pay</b> (§ 92.0081). A landlord who locks you out and "
                 "refuses a key owes you possession plus damages."),
            ]),
            ("Ending a lease & eviction", [
                ("Timelines",
                 "Month-to-month tenancies end with <b>one month's notice</b> "
                 "(§ 91.001). Before filing an eviction, the landlord must give "
                 "a <b>3-day written notice to vacate</b> unless the lease sets "
                 "a different period (§ 24.005). Cases are filed in justice "
                 "court."),
                ("Protections",
                 "Victims of family violence may terminate early with proper "
                 "documentation (§ 92.016), servicemembers are covered by "
                 "§ 92.017 and the federal SCRA, and landlord retaliation "
                 "within 6 months of a repair request or complaint is "
                 "prohibited (§ 92.331)."),
            ]),
        ],
        "faqs": [
            ("How long does a Texas landlord have to return a security deposit?",
             "30 days after you surrender the premises — refund or written itemized "
             "deductions (Tex. Prop. Code § 92.103). Provide a written forwarding "
             "address; bad-faith retention costs the landlord $100 + 3x the amount "
             "withheld + attorney's fees (§ 92.109)."),
            ("Is there a limit on security deposits in Texas?",
             "No — Texas has no statutory cap on deposit amounts. The protection is "
             "on the back end: strict 30-day return rules and triple damages for "
             "bad-faith withholding."),
            ("Does my landlord have to give notice before entering in Texas?",
             "Texas has no statute requiring advance entry notice — your lease "
             "controls. Read the entry clause before you sign."),
            ("Can my landlord lock me out for unpaid rent in Texas?",
             "Only under strict conditions, and even then the landlord must give you "
             "the new key immediately on request whether or not you pay "
             "(Tex. Prop. Code § 92.0081)."),
        ],
    },
    "ca": {
        "name": "California",
        "statute": "California Civil Code (§§ 1940–1954.06) including AB 12 and AB 1482",
        "quick": [
            ("Deposit cap", "1 month's rent"),
            ("Deposit return", "21 days"),
            ("Entry notice", "24 hours"),
            ("Rent cap", "5% + CPI (max 10%)"),
        ],
        "sections": [
            ("Security deposits", [
                ("The new one-month cap",
                 "Since July 1, 2024 (AB 12), most California landlords may "
                 "collect at most <b>one month's rent</b> in deposits — "
                 "furnished or not, pet deposits included in the cap (Civ. Code "
                 "§ 1950.5). A narrow exception lets qualifying small landlords "
                 "(no more than two properties, four total units) charge up to "
                 "two months."),
                ("Getting it back",
                 "The landlord has <b>21 calendar days</b> after you vacate to "
                 "return the deposit or send an itemized statement — with "
                 "receipts required for any single deduction over $125 "
                 "(§ 1950.5(g)). Bad-faith retention exposes the landlord to "
                 "<b>up to twice the deposit</b> in damages (§ 1950.5(l)). "
                 "Since January 1, 2026, if you paid electronically, you can "
                 "get the refund electronically (AB 414)."),
                ("Move-out inspection",
                 "You can request an initial inspection before move-out so you "
                 "have the chance to fix issues yourself before they become "
                 "deductions (§ 1950.5(f))."),
            ]),
            ("Rent increases & just cause (AB 1482)",
             [
                ("The statewide rent cap",
                 "For most units 15+ years old, annual increases are capped at "
                 "<b>5% plus local CPI, never more than 10% total</b> "
                 "(Civ. Code § 1947.12). Many cities (LA, SF, San Jose, and "
                 "others) have stricter local rent control on top."),
                ("Just-cause eviction",
                 "After 12 months of tenancy, covered units require "
                 "<b>just cause</b> to terminate — at-fault (nonpayment, "
                 "breach) or no-fault (owner move-in, withdrawal), with "
                 "relocation assistance owed for no-fault terminations "
                 "(§ 1946.2)."),
            ]),
            ("Repairs & privacy", [
                ("Habitability",
                 "Units must be fit to live in — working plumbing, heat, "
                 "electrical, weatherproofing (§ 1941.1). After notice and a "
                 "reasonable time (presumed 30 days, less if urgent), you may "
                 "repair-and-deduct up to one month's rent, at most twice in "
                 "any 12 months (§ 1942)."),
                ("Entry notice",
                 "The landlord must give <b>24 hours' written notice</b> and "
                 "enter only during normal business hours for non-emergencies "
                 "(§ 1954)."),
                ("Retaliation",
                 "Rent hikes, service cuts, or eviction within 180 days of "
                 "exercising your rights (complaints, repair requests) are "
                 "presumed retaliatory and prohibited (§ 1942.5)."),
            ]),
        ],
        "faqs": [
            ("How much can a landlord charge for a security deposit in California?",
             "One month's rent for most landlords since July 1, 2024 under AB 12, "
             "counting all deposits combined (Civ. Code § 1950.5). Qualifying small "
             "landlords may charge up to two months."),
            ("How long does a California landlord have to return my deposit?",
             "21 calendar days after you vacate, with an itemized statement and "
             "receipts for deductions over $125 (Civ. Code § 1950.5(g)). Bad-faith "
             "withholding risks up to twice the deposit in damages."),
            ("How much can my rent go up in California?",
             "For most units 15+ years old, at most 5% plus local CPI per year, "
             "never exceeding 10% (AB 1482, Civ. Code § 1947.12). Local rent "
             "control may be stricter."),
            ("How much notice before my landlord can enter in California?",
             "24 hours' written notice, entry during normal business hours, except "
             "emergencies (Civ. Code § 1954)."),
        ],
    },
    "fl": {
        "name": "Florida",
        "statute": "Florida Statutes, Chapter 83, Part II (Residential Tenancies)",
        "quick": [
            ("Deposit cap", "None"),
            ("Deposit return", "15–30 days"),
            ("Entry notice", "12 hours"),
            ("Month-to-month notice", "30 days"),
        ],
        "sections": [
            ("Security deposits", [
                ("The two-track return rule",
                 "No deductions? The landlord must return your full deposit "
                 "<b>within 15 days</b> of move-out. Claiming deductions? They "
                 "must send written notice of the claim by certified mail "
                 "<b>within 30 days</b> — and you then have <b>15 days to "
                 "object</b> in writing (Fla. Stat. § 83.49(3)). Miss the "
                 "30-day notice and the landlord <b>forfeits the right to keep "
                 "any of it</b>."),
                ("Always leave a forwarding address",
                 "The claim notice goes to your last known address — give the "
                 "landlord your new address in writing at move-out or you may "
                 "never see the notice you're supposed to object to."),
                ("Fee-in-lieu option",
                 "Florida now lets landlords offer a monthly fee instead of a "
                 "deposit (§ 83.491). It's optional — and unlike a deposit, "
                 "those fees are <b>never refunded</b>. Do the math before "
                 "choosing it."),
            ]),
            ("Repairs & habitability", [
                ("What must be maintained",
                 "Structural components, plumbing, running hot water, heat, "
                 "locks, and (for apartments) pest control and garbage removal "
                 "(§ 83.51)."),
                ("The 7-day letter",
                 "If the landlord materially fails to maintain the unit, send "
                 "written notice; if it's not fixed <b>within 7 days</b>, you "
                 "may terminate the lease or, in qualifying cases, withhold "
                 "rent (§§ 83.56, 83.60). Follow the notice procedure exactly — "
                 "informal complaints don't preserve your rights."),
            ]),
            ("Privacy & entry", [
                ("12 hours, reasonable times",
                 "Non-emergency entry requires at least <b>12 hours' notice</b>, "
                 "between 7:30 a.m. and 8:00 p.m. (§ 83.53). Lockouts and "
                 "utility shutoffs are illegal — a landlord who does either "
                 "owes you actual damages or 3 months' rent, whichever is "
                 "greater (§ 83.67)."),
            ]),
            ("Ending a lease & eviction", [
                ("Notice periods",
                 "Month-to-month tenancies now require <b>30 days' written "
                 "notice</b> (§ 83.57(3), raised from 15 days in 2023 — many "
                 "older websites still say 15). For unpaid rent, the landlord "
                 "serves a <b>3-business-day notice</b> to pay or vacate before "
                 "filing (§ 83.56(3))."),
                ("What Florida doesn't have",
                 "No rent control (state law forbids local rent control), no "
                 "just-cause eviction requirement, and — since July 1, 2026 — "
                 "state preemption of local tenant ordinances (§ 83.425), so "
                 "county-level protections no longer apply. Chapter 83 is "
                 "essentially the whole rulebook."),
            ]),
        ],
        "faqs": [
            ("How long does a Florida landlord have to return a security deposit?",
             "15 days if returning it in full, or 30 days to send a certified-mail "
             "notice of intent to claim deductions — after which you have 15 days "
             "to object (Fla. Stat. § 83.49(3)). Missing the 30-day notice forfeits "
             "the landlord's claim."),
            ("How much notice must a Florida landlord give before entering?",
             "At least 12 hours for non-emergency entry, between 7:30 a.m. and "
             "8:00 p.m. (Fla. Stat. § 83.53)."),
            ("How much notice to end a month-to-month lease in Florida?",
             "30 days' written notice, under § 83.57(3) as amended in 2023 — the "
             "old 15-day rule no longer applies."),
            ("Is there rent control in Florida?",
             "No — Florida law preempts local rent control, and as of July 2026 "
             "state law also preempts most local tenant-protection ordinances "
             "(§ 83.425)."),
        ],
    },
    "ny": {
        "name": "New York",
        "statute": "NY General Obligations Law § 7-108 and Real Property Law (HSTPA 2019)",
        "quick": [
            ("Deposit cap", "1 month's rent"),
            ("Deposit return", "14 days"),
            ("Rent demand", "14 days"),
            ("Non-renewal notice", "30–90 days"),
        ],
        "sections": [
            ("Security deposits", [
                ("One month, no exceptions",
                 "Since the 2019 Housing Stability and Tenant Protection Act, "
                 "deposits statewide are capped at <b>one month's rent</b> "
                 "(Gen. Oblig. Law § 7-108(1-a)). Advance payments beyond first "
                 "month's rent + one month deposit are prohibited."),
                ("14 days to return it",
                 "The landlord must return your deposit with an itemized "
                 "statement <b>within 14 days</b> of you vacating "
                 "(§ 7-108(1-a)(e)). Miss the deadline or the itemization and "
                 "the landlord <b>forfeits any right to keep any of it</b>; "
                 "willful violations can cost up to <b>twice the deposit</b> in "
                 "punitive damages."),
                ("Inspections both ways",
                 "You're entitled to an inspection before move-out with notice "
                 "of what would be deducted — and the chance to cure it "
                 "yourself first (§ 7-108(1-a)(c))."),
            ]),
            ("Rent increases & lease non-renewal", [
                ("The 30/60/90 rule",
                 "To raise rent more than 5% or decline to renew, the landlord "
                 "must give written notice based on how long you've been there: "
                 "<b>30 days</b> (under 1 year), <b>60 days</b> (1–2 years), "
                 "<b>90 days</b> (over 2 years) (Real Prop. Law § 226-c). "
                 "Rent-stabilized units in NYC and elsewhere have far stronger "
                 "protections on top."),
                ("Late fees",
                 "Capped at the lesser of $50 or 5% of monthly rent, and only "
                 "after a 5-day grace period (RPL § 238-a)."),
            ]),
            ("Repairs & habitability", [
                ("The warranty of habitability",
                 "Every New York lease carries an unwaivable warranty that the "
                 "unit is fit for habitation — heat, hot water, and freedom "
                 "from dangerous conditions (RPL § 235-b). Breaches support "
                 "rent abatement in court."),
                ("Entry notice",
                 "New York has <b>no statewide entry-notice statute</b> for "
                 "most tenancies — your lease and local rules (especially in "
                 "NYC) govern. Reasonable notice is the enforceable norm; "
                 "harassment and self-help lockouts are illegal (RPAPL § 768 "
                 "in NYC; unlawful eviction laws statewide)."),
            ]),
            ("Eviction & retaliation", [
                ("Timelines",
                 "Before an eviction case for unpaid rent, the landlord must "
                 "serve a <b>14-day written rent demand</b> (RPAPL § 711(2)). "
                 "Only a court and marshal/sheriff can remove you — never the "
                 "landlord."),
                ("Retaliation",
                 "Retaliation for complaints or asserting rights is prohibited, "
                 "with a presumption of retaliation for landlord actions within "
                 "one year (RPL § 223-b)."),
            ]),
        ],
        "faqs": [
            ("How much can a landlord collect as a security deposit in New York?",
             "One month's rent, statewide, under the 2019 HSTPA (Gen. Oblig. Law "
             "§ 7-108(1-a)). Larger deposits and multi-month prepayments are "
             "prohibited."),
            ("How long does a New York landlord have to return my deposit?",
             "14 days after you vacate, with an itemized statement — missing it "
             "forfeits the landlord's right to any deductions (§ 7-108(1-a)(e))."),
            ("How much notice for a rent increase in New York?",
             "For increases over 5% or non-renewal: 30, 60, or 90 days' written "
             "notice depending on whether you've been there under 1 year, 1–2 "
             "years, or longer (RPL § 226-c)."),
            ("Can my landlord evict me without going to court in New York?",
             "No — only a court order enforced by a marshal or sheriff can remove "
             "you. A 14-day written rent demand must precede any nonpayment case "
             "(RPAPL § 711(2))."),
        ],
    },
    "co": {
        "name": "Colorado",
        "statute": "Colorado Revised Statutes, Title 38, Article 12 (and Title 13, Article 40)",
        "quick": [
            ("Deposit cap", "2 months' rent"),
            ("Deposit return", "30 days (60 max)"),
            ("Nonpayment notice", "10 days"),
            ("Late fee cap", "$50 or 5%"),
        ],
        "sections": [
            ("Security deposits", [
                ("The cap and the clock",
                 "Deposits are capped at <b>two months' rent</b> (C.R.S. "
                 "§ 38-12-102.5, since August 2023). Return is due <b>within "
                 "30 days</b> of move-out with an itemized statement — a lease "
                 "may extend that, but never past <b>60 days</b> "
                 "(§ 38-12-103). Miss the deadline and the landlord forfeits "
                 "the right to withhold anything."),
                ("2026 strengthened rules",
                 "Effective January 1, 2026 (HB 25-1249), landlords can't "
                 "deduct for normal wear and tear <b>or anything that "
                 "pre-existed your tenancy</b>, must supply supporting "
                 "documentation within 14 days of your written request, and "
                 "face <b>treble damages plus attorney fees</b> for bad-faith "
                 "retention — after you give 7 days' written notice before "
                 "filing suit."),
            ]),
            ("Repairs & habitability", [
                ("The warranty",
                 "Colorado's warranty of habitability (C.R.S. § 38-12-503) "
                 "covers working heat, plumbing, electricity, weatherproofing, "
                 "and freedom from mold and pest hazards. Report problems in "
                 "writing (email counts); landlords must respond promptly — "
                 "within 24 hours for conditions threatening life, health, or "
                 "safety."),
                ("Remedies",
                 "For uncured breaches, remedies include repair-and-deduct, "
                 "rent reduction, and lease termination under the habitability "
                 "statutes (§§ 38-12-507, -509). Retaliation for asserting "
                 "these rights is prohibited (§ 38-12-509)."),
            ]),
            ("Money rules", [
                ("Late fees",
                 "Capped at the <b>greater of $50 or 5%</b> of the overdue "
                 "amount, can't be charged until rent is at least <b>10 days "
                 "late</b>, and must be in the written lease (§ 38-12-105)."),
                ("Rent increases",
                 "No rent control (state law preempts local rent control, "
                 "§ 38-12-301), but rent can be raised at most <b>once in any "
                 "12 months</b>, with <b>60 days' notice</b> for "
                 "month-to-month tenancies (§§ 38-12-701, -702)."),
            ]),
            ("Ending a lease & eviction", [
                ("Timelines",
                 "Nonpayment requires a <b>10-day written notice</b> to pay or "
                 "vacate before an eviction filing (C.R.S. "
                 "§ 13-40-104(1)(d)). Month-to-month terminations for typical "
                 "tenancies require <b>21 days' notice</b> (§ 13-40-107); "
                 "longer tenancies require more. Colorado also now requires "
                 "cause for most evictions and non-renewals (HB 24-1098)."),
                ("Protections",
                 "Self-help lockouts and utility shutoffs are illegal; victims "
                 "of domestic violence or unsafe conditions have early "
                 "termination rights (§ 38-12-402); and only a court order "
                 "executed by the sheriff can remove you."),
            ]),
        ],
        "faqs": [
            ("How much can a Colorado landlord charge for a security deposit?",
             "No more than two months' rent (C.R.S. § 38-12-102.5, effective "
             "August 2023)."),
            ("How long does a Colorado landlord have to return my deposit?",
             "30 days after move-out with an itemized statement, extendable by the "
             "lease to at most 60 days (C.R.S. § 38-12-103). Bad-faith retention "
             "risks treble damages after a 7-day pre-suit notice."),
            ("How much notice before eviction for unpaid rent in Colorado?",
             "A 10-day written notice to pay or vacate must come before any filing "
             "(C.R.S. § 13-40-104(1)(d)), and late fees can't start until rent is "
             "10 days late."),
            ("Can my rent be raised twice in one year in Colorado?",
             "No — rent may be increased at most once in any 12-month period, with "
             "60 days' notice for month-to-month tenancies (C.R.S. §§ 38-12-701, "
             "-702)."),
        ],
    },
    "wa": {
        "name": "Washington",
        "statute": "Washington Residential Landlord-Tenant Act (RCW 59.18) incl. HB 1217 (2025)",
        "quick": [
            ("Deposit return", "30 days"),
            ("Entry notice", "2 days"),
            ("Rent cap", "7% + CPI (max 10%)"),
            ("Nonpayment notice", "14 days"),
        ],
        "sections": [
            ("Security deposits", [
                ("The checklist rule",
                 "A Washington landlord can only collect a deposit if the lease "
                 "is written AND both sides sign a <b>move-in condition "
                 "checklist</b> (RCW 59.18.260) — no checklist, no lawful "
                 "deposit. There's no statewide cap on the amount (Seattle has "
                 "local limits), and deposits must sit in a trust account "
                 "(59.18.270)."),
                ("Getting it back",
                 "The landlord has <b>30 days</b> after you move out to refund "
                 "the deposit or send a full and specific itemized statement "
                 "with supporting documentation (RCW 59.18.280 — older sites "
                 "still say 21 days; the window changed in 2023). Normal wear "
                 "and tear is never deductible, and deductions can't exceed "
                 "what the checklist and documentation support."),
            ]),
            ("Rent increases — the new regime (HB 1217)", [
                ("Washington now has a statewide rent cap",
                 "Since May 7, 2025, most annual increases are capped at "
                 "<b>7% plus CPI or 10%, whichever is lower</b> (the official "
                 "2026 figure is 9.683%), with <b>no increase allowed in the "
                 "first 12 months</b> of a tenancy and at most one increase "
                 "per 12 months. Exemptions include buildings under 12 years "
                 "old and certain nonprofit/public housing."),
                ("90 days' notice, real teeth",
                 "Any increase requires at least <b>90 days' written notice</b> "
                 "(RCW 59.18.140; Seattle requires 180). Increases above the "
                 "cap can be refused, and tenants can recover <b>up to three "
                 "times</b> any overcharge; the Attorney General can add "
                 "penalties."),
            ]),
            ("Repairs, privacy & fees", [
                ("Habitability",
                 "Landlords must keep the unit up to code — weathertight, "
                 "heated, with hot water and pest control (RCW 59.18.060). "
                 "After written notice, repair timelines run from 24 hours "
                 "(no hot water, heat, or electricity) to 10 days, with "
                 "repair-and-deduct and rent-escrow remedies if ignored."),
                ("Entry & late fees",
                 "Non-emergency entry requires <b>2 days' written notice</b> "
                 "(1 day to show the unit) at reasonable times "
                 "(RCW 59.18.150). No late fee may be charged if rent is paid "
                 "within <b>5 days</b> of the due date (59.18.170)."),
            ]),
            ("Ending a lease & eviction", [
                ("Just cause statewide",
                 "Since 2021, landlords need <b>just cause</b> to end most "
                 "tenancies or refuse renewal (RCW 59.18.650) — nonpayment, "
                 "lease violations, owner move-in, and other enumerated "
                 "grounds. For unpaid rent, a <b>14-day pay-or-vacate "
                 "notice</b> is required before filing (59.18.057), and only "
                 "the sheriff, on a court order, can remove you."),
            ]),
        ],
        "faqs": [
            ("How much can my rent go up per year in Washington?",
             "For most rentals, at most 7% plus CPI or 10%, whichever is lower — "
             "9.683% for 2026 — with no increase in the first 12 months and 90 "
             "days' written notice required (HB 1217, effective May 2025)."),
            ("How long does a Washington landlord have to return my deposit?",
             "30 days after move-out, with a full and specific itemized statement "
             "and documentation (RCW 59.18.280). The old 21-day window changed in "
             "2023."),
            ("Can my landlord collect a deposit without a move-in checklist in Washington?",
             "No — a deposit is only lawful with a written lease and a move-in "
             "condition checklist signed by both parties (RCW 59.18.260)."),
            ("How much notice before my landlord can enter in Washington?",
             "At least 2 days' written notice for non-emergency entry, or 1 day to "
             "show the unit to prospective tenants or buyers (RCW 59.18.150)."),
        ],
    },
    "or": {
        "name": "Oregon",
        "statute": "Oregon Residential Landlord and Tenant Act (ORS Chapter 90)",
        "quick": [
            ("Deposit return", "31 days"),
            ("Entry notice", "24 hours"),
            ("Rent cap", "7% + CPI (max 10%)"),
            ("First-year increases", "None"),
        ],
        "sections": [
            ("Security deposits", [
                ("No cap, strict clock",
                 "Oregon doesn't cap deposit amounts, but the landlord must "
                 "return your deposit with a written itemized accounting "
                 "<b>within 31 days</b> of the tenancy ending (ORS 90.300). "
                 "Wrongful withholding entitles you to <b>twice the amount "
                 "wrongfully kept</b>. Normal wear and tear is not deductible, "
                 "and any non-refundable fees must be specifically allowed by "
                 "statute and stated in the lease (ORS 90.302)."),
            ]),
            ("Rent increases & just cause", [
                ("The nation's first statewide rent cap",
                 "Annual increases on most units older than 15 years are "
                 "capped at <b>7% plus CPI, never exceeding 10%</b> "
                 "(ORS 90.324, tightened by SB 611 in 2023). <b>No increase at "
                 "all during the first year</b> of tenancy, and 90 days' "
                 "written notice for any increase after that (ORS 90.323)."),
                ("Just cause after year one",
                 "After 12 months, most no-cause terminations are prohibited "
                 "(ORS 90.427): the landlord needs tenant cause or a "
                 "qualifying landlord reason (sale to an owner-occupant, major "
                 "renovation, owner move-in) — the latter with 90 days' notice "
                 "and, for larger landlords, one month's rent in relocation "
                 "assistance."),
            ]),
            ("Repairs & privacy", [
                ("Habitability",
                 "Units must be habitable — weatherproof, plumbed, heated, "
                 "safe (ORS 90.320). After written notice, remedies for "
                 "uncured problems include repair-and-deduct, rent reduction, "
                 "and lease termination (ORS 90.360–90.368)."),
                ("Entry notice",
                 "Non-emergency entry requires at least <b>24 hours' "
                 "notice</b> at reasonable times (ORS 90.322)."),
            ]),
            ("Ending a lease & eviction", [
                ("Nonpayment timelines",
                 "Rent is late on the 5th; the landlord may then serve a "
                 "<b>144-hour (6-day) notice</b>, or wait until the 8th and "
                 "serve a <b>72-hour notice</b> (ORS 90.394). Paying within "
                 "the notice period ends it. Lockouts and utility shutoffs "
                 "are illegal (ORS 90.375)."),
                ("Retaliation",
                 "Rent hikes, service cuts, or eviction in response to "
                 "complaints or asserting rights are prohibited (ORS 90.385)."),
            ]),
        ],
        "faqs": [
            ("How much can rent increase per year in Oregon?",
             "For most units over 15 years old: 7% plus CPI, capped at 10% "
             "(ORS 90.324, SB 611). No increase during the first year of tenancy, "
             "and 90 days' written notice after that."),
            ("How long does an Oregon landlord have to return my deposit?",
             "31 days after the tenancy ends, with a written itemized accounting "
             "(ORS 90.300). Wrongful withholding = double damages."),
            ("Can my Oregon landlord evict me without a reason?",
             "After the first year, generally no — Oregon requires cause or a "
             "qualifying landlord reason with 90 days' notice and possible "
             "relocation assistance (ORS 90.427)."),
            ("How much notice before my landlord can enter in Oregon?",
             "At least 24 hours, at reasonable times, except emergencies "
             "(ORS 90.322)."),
        ],
    },
    "nv": {
        "name": "Nevada",
        "statute": "Nevada Revised Statutes, Chapter 118A (and Chapter 40)",
        "quick": [
            ("Deposit cap", "3 months' rent"),
            ("Deposit return", "30 days"),
            ("Entry notice", "24 hours"),
            ("Late fee cap", "5%"),
        ],
        "sections": [
            ("Security deposits", [
                ("The 3-month ceiling",
                 "Nevada allows the highest fixed deposit cap in the country — "
                 "<b>three months' rent</b> — but it covers <b>everything "
                 "combined</b>: security, pet, cleaning, and damage deposits "
                 "all count toward the same ceiling regardless of label "
                 "(NRS 118A.240, 118A.242). No deposit may be labeled "
                 "non-refundable except a reasonable cleaning fee."),
                ("30 days, with real consequences",
                 "The landlord must return the deposit with an itemized "
                 "written accounting <b>within 30 days</b> of the tenancy "
                 "ending (NRS 118A.242). Miss it, and the landlord is liable "
                 "for the <b>entire deposit plus a court-set penalty of up to "
                 "the entire deposit again</b> — a $2,000 deposit held late "
                 "can become a $4,000 judgment."),
            ]),
            ("Money rules", [
                ("Late fees",
                 "Hard-capped at <b>5% of the periodic rent</b>, only after a "
                 "mandatory <b>3-day grace period</b>, and only if the lease "
                 "provides for them (NRS 118A.210)."),
            ]),
            ("Repairs & privacy", [
                ("Habitability — including A/C",
                 "Landlords must maintain a habitable unit: plumbing, heat, "
                 "<b>air conditioning</b> (essential in Nevada), electrical, "
                 "and running hot water (NRS 118A.290). For failures of "
                 "essential services, remedies include withholding rent, "
                 "repair-and-deduct, substitute housing, or termination after "
                 "proper written notice (NRS 118A.355, 118A.380)."),
                ("Entry notice",
                 "At least <b>24 hours' notice</b>, entry at reasonable times, "
                 "except emergencies (NRS 118A.330)."),
            ]),
            ("Ending a lease & eviction", [
                ("Nevada's summary eviction system",
                 "Nonpayment starts with a <b>7-day pay-or-quit notice</b>; "
                 "paying in full within the window ends the case "
                 "(NRS 40.2512). Nevada's summary eviction process moves "
                 "fast — a tenant who doesn't respond in court within the "
                 "notice period can lose by default, so <b>never ignore an "
                 "eviction notice</b>. Month-to-month tenancies end on 30 "
                 "days' notice (NRS 40.251); tenants 60+ or with disabilities "
                 "can request an extra 30."),
                ("Lockouts & retaliation",
                 "Self-help lockouts and utility shutoffs are illegal "
                 "(NRS 118A.390), and retaliation for complaints or asserting "
                 "rights is prohibited (NRS 118A.510)."),
            ]),
        ],
        "faqs": [
            ("What's the maximum security deposit in Nevada?",
             "Three months' rent — the highest fixed cap of any state — counting "
             "all deposits combined, however they're labeled (NRS 118A.242)."),
            ("How long does a Nevada landlord have to return my deposit?",
             "30 days after the tenancy ends, with an itemized accounting. Failure "
             "makes the landlord liable for the entire deposit plus a penalty of "
             "up to the same amount again (NRS 118A.242)."),
            ("How much can a Nevada landlord charge in late fees?",
             "At most 5% of the rent, only after a mandatory 3-day grace period "
             "(NRS 118A.210)."),
            ("How long do I have if I get a nonpayment eviction notice in Nevada?",
             "The 7-day pay-or-quit notice is curable by paying in full — but "
             "Nevada's summary eviction moves fast, so respond in court within the "
             "window even if you dispute the debt (NRS 40.2512)."),
        ],
    },
    "ut": {
        "name": "Utah",
        "statute": "Utah Code Title 57, Chapters 17 & 22 (Renters' Deposits; Fit Premises Act)",
        "quick": [
            ("Deposit cap", "None"),
            ("Deposit return", "30 days"),
            ("Repair window", "3 days (corrective)"),
            ("Nonpayment notice", "3 business days"),
        ],
        "sections": [
            ("Security deposits", [
                ("No cap; written-disclosure rule",
                 "Utah sets no limit on deposit amounts, but any "
                 "<b>non-refundable</b> portion is only valid if disclosed to "
                 "you <b>in writing</b> when the deposit is taken (Utah Code "
                 "§ 57-17-2). If it wasn't disclosed in writing, it's "
                 "refundable."),
                ("The return clock",
                 "The landlord must return your deposit with an itemized list "
                 "of deductions within <b>30 days after the tenancy ends — or "
                 "15 days after receiving your new mailing address in writing, "
                 "whichever is later</b> (§ 57-17-3). Send that forwarding "
                 "address promptly and in writing. Noncompliance exposes the "
                 "landlord to the full deposit, a statutory penalty, and court "
                 "costs (§ 57-17-5)."),
            ]),
            ("Repairs — the Fit Premises Act", [
                ("What's owed",
                 "Landlords must maintain a safe, sanitary unit fit for human "
                 "occupancy — heat, water, electricity, structural soundness "
                 "(§ 57-22-4). Utah also requires <b>24 hours' notice</b> "
                 "before non-emergency entry unless your lease sets a "
                 "different rule (§ 57-22-4(2))."),
                ("The corrective-period system",
                 "Report deficient conditions in writing. The Fit Premises Act "
                 "then runs on corrective deadlines — as short as <b>3 "
                 "calendar days</b> for conditions like no heat or water "
                 "(§ 57-22-6). If the landlord blows the deadline, remedies "
                 "include rent abatement, repair-and-deduct, or terminating "
                 "the lease with your deposit and prepaid rent refunded."),
            ]),
            ("Ending a lease & eviction", [
                ("Utah moves fast",
                 "Nonpayment evictions start with a <b>3-business-day</b> pay-"
                 "or-vacate notice (Utah Code § 78B-6-802), and Utah's "
                 "unlawful detainer process is among the fastest in the "
                 "country — with <b>treble damages</b> possible for tenants "
                 "who hold over after notice. Take deadlines literally and "
                 "respond immediately. Month-to-month tenancies end on <b>15 "
                 "days' notice</b>."),
                ("What Utah doesn't have",
                 "No rent control (and state law preempts local rent "
                 "control), no just-cause requirement, no statutory late-fee "
                 "cap. The lease you sign is most of the law you'll live "
                 "under — read it accordingly."),
            ]),
        ],
        "faqs": [
            ("How long does a Utah landlord have to return my security deposit?",
             "Within 30 days after the tenancy ends, or 15 days after receiving "
             "your new mailing address in writing, whichever is later, with an "
             "itemized list of deductions (Utah Code § 57-17-3)."),
            ("Can a Utah landlord keep a non-refundable deposit?",
             "Only if the non-refundable portion was disclosed to you in writing "
             "when it was collected (Utah Code § 57-17-2). Undisclosed = "
             "refundable."),
            ("How fast can eviction happen in Utah?",
             "Fast — nonpayment requires only a 3-business-day notice "
             "(§ 78B-6-802) and Utah's court process is among the quickest in the "
             "country, with treble damages for holding over. Respond to any "
             "notice immediately."),
            ("Is there rent control in Utah?",
             "No — Utah has no rent control and state law preempts local rent "
             "control ordinances. Rent terms are governed by your lease."),
        ],
    },
    "nm": {
        "name": "New Mexico",
        "statute": "New Mexico Uniform Owner-Resident Relations Act (NMSA Ch. 47, Art. 8)",
        "quick": [
            ("Deposit cap", "1 month (leases <1 yr)"),
            ("Deposit return", "30 days"),
            ("Entry notice", "24 hours"),
            ("Late fee cap", "10%"),
        ],
        "sections": [
            ("Security deposits", [
                ("The split cap — and the interest rule",
                 "For leases <b>under one year</b>, deposits are capped at "
                 "<b>one month's rent</b> (NMSA § 47-8-18(A)). Annual leases "
                 "may carry a larger reasonable deposit — but then the "
                 "landlord <b>owes you annual interest</b> on it at the "
                 "passbook rate. A big deposit on a 12-month lease isn't "
                 "automatically illegal; an interest-free one may be."),
                ("30 days, or forfeit everything",
                 "The deposit plus an itemized deduction list is due within "
                 "<b>30 days</b> of the tenancy ending (§ 47-8-18(C)). A "
                 "landlord who misses it <b>forfeits the right to withhold "
                 "anything, loses the right to counterclaim, and owes your "
                 "court costs and attorney fees</b> (§ 47-8-18(D)) — one of "
                 "the sharpest deposit penalties in the country."),
            ]),
            ("Money rules", [
                ("Late fees",
                 "Capped at <b>10% of the rent</b> for the period, and only "
                 "if the lease provides for them, with notice of the charge "
                 "by the next rent due date (§ 47-8-15(D))."),
            ]),
            ("Repairs & privacy", [
                ("Habitability & remedies",
                 "The unit must comply with housing codes — plumbing, heat, "
                 "water, structural safety (§ 47-8-20). For violations, "
                 "written 7-day notice applies: uncured material problems let "
                 "you terminate, and qualifying conditions support rent "
                 "abatement under the Act (§§ 47-8-27.1, 47-8-27.2)."),
                ("Entry notice",
                 "At least <b>24 hours' written notice</b> for non-emergency "
                 "entry, at reasonable times (§ 47-8-24)."),
            ]),
            ("Ending a lease & eviction", [
                ("Timelines",
                 "Nonpayment requires a <b>3-day written notice</b> to pay or "
                 "quit (§ 47-8-33(D)); other lease violations get a 7-day "
                 "notice with a chance to cure. Month-to-month tenancies end "
                 "on <b>30 days' notice</b> (§ 47-8-37). Lockouts and utility "
                 "shutoffs are prohibited — only a court can evict."),
                ("Retaliation",
                 "Rent hikes, service cuts, or eviction within 6 months of a "
                 "complaint, repair request, or organizing activity are "
                 "presumed retaliatory and prohibited (§ 47-8-39)."),
            ]),
        ],
        "faqs": [
            ("How much can a landlord charge for a deposit in New Mexico?",
             "One month's rent for leases under a year (NMSA § 47-8-18(A)). Annual "
             "leases may carry a larger reasonable deposit, but the landlord then "
             "owes you annual interest on it."),
            ("How long does a New Mexico landlord have to return my deposit?",
             "30 days after the tenancy ends, with an itemized list. Missing it "
             "forfeits the landlord's right to withhold anything and makes them "
             "liable for your court costs and attorney fees (§ 47-8-18(C)–(D))."),
            ("How much can late fees be in New Mexico?",
             "At most 10% of the rent for the period, and only if your lease "
             "provides for them (NMSA § 47-8-15(D))."),
            ("How much notice before eviction for unpaid rent in New Mexico?",
             "A 3-day written notice to pay or quit must come first "
             "(NMSA § 47-8-33(D)); only a court order can actually remove you."),
        ],
    },
    "ga": {
        "name": "Georgia",
        "statute": "O.C.G.A. Title 44, Chapter 7, incl. the Safe at Home Act (HB 404, 2024)",
        "quick": [
            ("Deposit cap", "2 months' rent"),
            ("Deposit return", "30 days"),
            ("Wrongful withholding", "3x + fees"),
            ("Cure before eviction", "3 business days"),
        ],
        "sections": [
            ("The Safe at Home Act — Georgia's 2024 overhaul", [
                ("Habitability, finally in the statute",
                 "For leases signed or renewed on/after July 1, 2024, Georgia "
                 "has an express <b>warranty of habitability</b> — the unit "
                 "must be fit for human habitation (O.C.G.A. § 44-7-13(b)). "
                 "Georgia was one of the last states without one. The Act also "
                 "added <b>cooling</b> to the protected utilities a landlord "
                 "can't cut off (§ 44-7-14.1)."),
                ("The 3-day cure period",
                 "Before filing any eviction for unpaid rent or charges, the "
                 "landlord must deliver a written notice and give you <b>three "
                 "business days to pay everything owed</b> (§ 44-7-50). Paying "
                 "in full within the window stops the filing."),
            ]),
            ("Security deposits", [
                ("The new cap",
                 "Deposits are capped at <b>two months' rent</b> "
                 "(§ 44-7-30.1, since July 2024). Landlords with more than 10 "
                 "units must hold deposits in escrow or post a surety bond "
                 "(§ 44-7-31), and must give you a written move-in damage "
                 "list within 3 business days of move-in (§ 44-7-33) — "
                 "inspect and dispute it in writing before signing off."),
                ("Return & the triple-damages penalty",
                 "Return with an itemized statement is due <b>within 30 "
                 "days</b> (§ 44-7-34). Wrongful withholding makes the "
                 "landlord liable for <b>three times the amount improperly "
                 "kept plus attorney's fees</b> (§ 44-7-35(c)). Normal wear "
                 "and tear is never deductible."),
            ]),
            ("Privacy, entry & rent", [
                ("Entry notice",
                 "Georgia has <b>no statute requiring advance entry "
                 "notice</b> — your lease governs. Read the entry clause "
                 "before signing."),
                ("Rent rules",
                 "No rent control anywhere in Georgia (state preemption, "
                 "§ 44-7-19). For tenancies at will, rent increases and "
                 "landlord terminations require <b>60 days' notice</b>; "
                 "tenants only owe <b>30 days</b> to leave (§ 44-7-7) — one "
                 "of the few asymmetries in a tenant's favor."),
            ]),
            ("Eviction basics", [
                ("Process protections",
                 "Self-help evictions — lockouts, door removal, utility "
                 "shutoffs (including A/C) — are illegal; only a court's "
                 "dispossessory process can remove you. Habitability failures "
                 "under the new warranty can now be raised as a defense in "
                 "that proceeding for post-July-2024 leases."),
            ]),
        ],
        "faqs": [
            ("How much can a landlord charge for a security deposit in Georgia?",
             "Two months' rent, under the Safe at Home Act (O.C.G.A. § 44-7-30.1, "
             "effective July 1, 2024)."),
            ("How long does a Georgia landlord have to return my deposit?",
             "30 days, with an itemized statement (§ 44-7-34). Wrongful "
             "withholding = three times the amount kept plus attorney's fees "
             "(§ 44-7-35(c))."),
            ("Does Georgia have a warranty of habitability?",
             "Yes — since July 1, 2024, for leases signed or renewed after that "
             "date, units must be fit for human habitation (§ 44-7-13(b)), and "
             "cooling is a protected utility."),
            ("Can my Georgia landlord file for eviction the day rent is late?",
             "No — since the Safe at Home Act, a written notice and a "
             "3-business-day window to pay everything owed must come before any "
             "filing (§ 44-7-50)."),
        ],
    },
    "nc": {
        "name": "North Carolina",
        "statute": "N.C. General Statutes, Chapter 42 (Landlord and Tenant)",
        "quick": [
            ("Deposit cap", "2 wk / 1.5 mo / 2 mo"),
            ("Deposit return", "30 days (60 max)"),
            ("Late fee cap", "$15 or 5%"),
            ("Nonpayment demand", "10 days"),
        ],
        "sections": [
            ("Security deposits", [
                ("The tiered cap",
                 "North Carolina caps deposits by tenancy length: <b>two "
                 "weeks' rent</b> for week-to-week, <b>1.5 months</b> for "
                 "month-to-month, and <b>two months</b> for longer terms "
                 "(G.S. § 42-51). The deposit must sit in a licensed NC trust "
                 "account or be bonded, and you must be told <b>where, in "
                 "writing, within 30 days</b> (§ 42-50)."),
                ("Return rules",
                 "Itemized statement and balance due <b>within 30 days</b> of "
                 "move-out — extendable to <b>60 days</b> only if the landlord "
                 "sends an interim accounting within the first 30 "
                 "(§ 42-52). Deductions must fit the closed statutory list in "
                 "§ 42-51; wear and tear never qualifies. <b>Willful</b> "
                 "violations forfeit the landlord's right to keep anything, "
                 "plus your attorney's fees (§ 42-55)."),
            ]),
            ("Money rules", [
                ("Late fees",
                 "Capped at the greater of <b>$15 or 5%</b> of the rent, only "
                 "after rent is <b>5 days late</b>, only if the lease provides "
                 "for it, and only once per late payment (§ 42-46)."),
            ]),
            ("Repairs & privacy", [
                ("Habitability",
                 "Landlords must keep the unit fit and habitable — code "
                 "compliance, plumbing, heat, smoke/CO alarms (§ 42-42). "
                 "Important NC quirk: there's <b>no repair-and-deduct</b> "
                 "right — withholding rent unilaterally can get you evicted. "
                 "The lawful path is written notice, then small claims court "
                 "for rent abatement."),
                ("Entry notice",
                 "No fixed statutory notice period — the standard is "
                 "<b>reasonable notice</b> at reasonable times (24–48 hours "
                 "in practice), with emergencies excepted."),
            ]),
            ("Ending a lease & eviction", [
                ("Timelines",
                 "Nonpayment requires a <b>10-day demand for rent</b> before "
                 "filing (§ 42-3, unless the lease says otherwise). "
                 "Month-to-month terminations customarily run on 30 days' "
                 "notice (7 days week-to-week, § 42-14). Lockouts and utility "
                 "shutoffs are illegal — only summary ejectment through the "
                 "courts can remove you. Retaliation for complaints within 12 "
                 "months is a defense to eviction (§ 42-37.1)."),
            ]),
        ],
        "faqs": [
            ("How much can a North Carolina landlord charge for a deposit?",
             "It's tiered: two weeks' rent for week-to-week tenancies, 1.5 months "
             "for month-to-month, two months for longer terms (G.S. § 42-51)."),
            ("How long does an NC landlord have to return my deposit?",
             "30 days, extendable to 60 only if an interim accounting is sent "
             "within the first 30 (§ 42-52). Willful violations forfeit all "
             "deductions plus attorney's fees (§ 42-55)."),
            ("Can I withhold rent for repairs in North Carolina?",
             "No — NC has no repair-and-deduct or rent-withholding right, and "
             "doing it unilaterally risks eviction. Use written notice and small "
             "claims court for rent abatement instead (§ 42-44)."),
            ("How big can late fees be in North Carolina?",
             "The greater of $15 or 5% of the rent, only after 5 days late, and "
             "only if the lease provides for it (§ 42-46)."),
        ],
    },
    "va": {
        "name": "Virginia",
        "statute": "Virginia Residential Landlord and Tenant Act (Va. Code § 55.1-1200 et seq.)",
        "quick": [
            ("Deposit cap", "2 months' rent"),
            ("Deposit return", "45 days"),
            ("Late fee cap", "10%"),
            ("Nonpayment notice", "5 days"),
        ],
        "sections": [
            ("Security deposits", [
                ("Cap and clock",
                 "Deposits are capped at <b>two months' rent</b> and must be "
                 "returned with a written itemization <b>within 45 days</b> of "
                 "the tenancy ending or you vacating, whichever is later "
                 "(Va. Code § 55.1-1226). Deductions made during the tenancy "
                 "must be itemized to you within 30 days of the deduction."),
                ("The inspection rights",
                 "The landlord must give you written notice of your <b>right "
                 "to be present at the final move-out inspection</b> "
                 "(§ 55.1-1226). Go — it's your best shot at contesting "
                 "claimed damage before it becomes a deduction. A bare check "
                 "without the itemization doesn't satisfy the statute."),
            ]),
            ("Money rules", [
                ("Late fees",
                 "Capped at <b>10% of the periodic rent or 10% of the unpaid "
                 "balance, whichever is less</b>, and only if the lease "
                 "provides for them (§ 55.1-1204(E))."),
            ]),
            ("Repairs & privacy", [
                ("Habitability",
                 "The unit must comply with building codes — heat, water, hot "
                 "water, air conditioning if supplied, and freedom from mold "
                 "and pests (§ 55.1-1220). For serious uncured problems after "
                 "written notice, Virginia's remedy is a <b>tenant's "
                 "assertion</b> filed in General District Court with rent "
                 "paid into escrow (§ 55.1-1244) — a structured alternative "
                 "to unilateral withholding, which is risky."),
                ("Entry notice",
                 "For routine maintenance you didn't request, at least "
                 "<b>72 hours' notice</b>; entry at reasonable times "
                 "(§ 55.1-1229(A)). Emergencies excepted."),
            ]),
            ("Ending a lease & eviction", [
                ("Timelines",
                 "Nonpayment requires a <b>5-day pay-or-quit notice</b> "
                 "before filing (§ 55.1-1245(F)); paying in full within the "
                 "window ends it. Other curable violations get a 30-day "
                 "notice with 21 days to cure. Month-to-month tenancies end "
                 "on <b>30 days' written notice</b> (§ 55.1-1253). Only the "
                 "sheriff, on a court order, can remove you."),
                ("Retaliation",
                 "Rent hikes, service cuts, or eviction for complaints, "
                 "repair requests, or organizing are prohibited "
                 "(§ 55.1-1258)."),
            ]),
        ],
        "faqs": [
            ("How much can a Virginia landlord charge for a security deposit?",
             "Two months' rent maximum (Va. Code § 55.1-1226)."),
            ("How long does a Virginia landlord have to return my deposit?",
             "45 days after termination or your move-out, whichever is later, "
             "with a written itemization — a check without the itemization is "
             "statutorily defective (§ 55.1-1226)."),
            ("How much notice before entry in Virginia?",
             "At least 72 hours for routine maintenance you didn't request, at "
             "reasonable times (§ 55.1-1229(A))."),
            ("How big can late fees be in Virginia?",
             "At most 10% of the periodic rent or 10% of the unpaid balance, "
             "whichever is less (§ 55.1-1204(E))."),
        ],
    },
    "tn": {
        "name": "Tennessee",
        "statute": "Tennessee URLTA (T.C.A. Title 66, Ch. 28) — applies in counties over 75,000",
        "quick": [
            ("Deposit cap", "None"),
            ("Deposit return", "30 days"),
            ("Nonpayment notice", "14 days"),
            ("URLTA coverage", "Counties >75k only"),
        ],
        "sections": [
            ("The coverage quirk — read this first", [
                ("Where the law applies",
                 "Tennessee's URLTA only applies in <b>counties with more "
                 "than 75,000 residents</b> (T.C.A. § 66-28-102) — Davidson "
                 "(Nashville), Shelby (Memphis), Knox, Hamilton, Rutherford, "
                 "Williamson, Montgomery, and other large counties. In "
                 "smaller counties, common law and your lease govern instead, "
                 "and most of the protections below <b>don't apply by "
                 "statute</b>. Know which side of the line your county is "
                 "on."),
            ]),
            ("Security deposits (URLTA counties)", [
                ("The rules",
                 "No cap on amounts, but the deposit must sit in a Tennessee "
                 "bank account (§ 66-28-301), you're entitled to an itemized "
                 "list of any damage deductions with the right to inspect and "
                 "dispute, and the balance is due <b>within 30 days</b> of "
                 "move-out. Always give a written forwarding address — "
                 "deposits can be treated as abandoned if you don't respond "
                 "to notice within 60 days."),
            ]),
            ("Repairs & privacy (URLTA counties)", [
                ("Habitability",
                 "Landlords must comply with building codes and keep the unit "
                 "fit and habitable (§ 66-28-304). For essential-service "
                 "failures after written notice, remedies include procuring "
                 "services and deducting, substitute housing, or termination "
                 "(§ 66-28-502). For other material problems, a written "
                 "<b>14-day notice</b> that the lease terminates in 30 days "
                 "if uncured applies (§ 66-28-501)."),
                ("Entry",
                 "The landlord may enter only at reasonable times without "
                 "abusing the right, and must give <b>24 hours' notice</b> "
                 "for showings during the final 30 days of the lease "
                 "(§ 66-28-403)."),
            ]),
            ("Ending a lease & eviction", [
                ("Timelines",
                 "For unpaid rent in URLTA counties, the landlord serves a "
                 "<b>14-day written notice</b> — paying in full within the "
                 "window cures it (§ 66-28-505). Month-to-month tenancies "
                 "end on 30 days' notice (§ 66-28-512). Lockouts and utility "
                 "shutoffs are illegal; only court process removes you. "
                 "Tennessee has no rent control and state law preempts local "
                 "attempts."),
            ]),
        ],
        "faqs": [
            ("Does Tennessee's landlord-tenant law apply where I live?",
             "The URLTA only applies in counties over 75,000 residents — the "
             "Nashville, Memphis, Knoxville, Chattanooga metros and other large "
             "counties (T.C.A. § 66-28-102). In smaller counties, your lease and "
             "common law govern instead."),
            ("How long does a Tennessee landlord have to return my deposit?",
             "In URLTA counties, 30 days after move-out, with an itemized list of "
             "any deductions you have the right to inspect and dispute "
             "(§ 66-28-301). Give a written forwarding address."),
            ("How much notice before eviction for unpaid rent in Tennessee?",
             "In URLTA counties, a 14-day written notice that's fully curable by "
             "paying what's owed (§ 66-28-505)."),
            ("Is there a security deposit limit in Tennessee?",
             "No — Tennessee sets no cap on deposit amounts. The protections are "
             "procedural: bank-account holding, itemization, and the 30-day "
             "return (§ 66-28-301)."),
        ],
    },
    "sc": {
        "name": "South Carolina",
        "statute": "South Carolina Residential Landlord and Tenant Act (S.C. Code § 27-40)",
        "quick": [
            ("Deposit cap", "None"),
            ("Deposit return", "30 days"),
            ("Entry notice", "24 hours"),
            ("Nonpayment notice", "5 days"),
        ],
        "sections": [
            ("Security deposits", [
                ("The rules",
                 "No cap on amounts, but return with an itemized statement is "
                 "due <b>within 30 days</b> of the later of the tenancy "
                 "ending or you demanding it and providing a forwarding "
                 "address (S.C. Code § 27-40-410). <b>Bad-faith retention "
                 "makes the landlord liable for three times the amount "
                 "wrongfully withheld plus attorney's fees.</b> Normal wear "
                 "and tear is never deductible."),
            ]),
            ("Repairs & privacy", [
                ("Habitability",
                 "Landlords must comply with housing codes and keep the unit "
                 "fit — plumbing, heat, hot water, and safe common areas "
                 "(§ 27-40-440). For material noncompliance after <b>14 days' "
                 "written notice</b>, the lease terminates in 30 days if "
                 "uncured (§ 27-40-610); essential-service failures support "
                 "substitute housing or procure-and-deduct remedies "
                 "(§ 27-40-630)."),
                ("Entry notice",
                 "At least <b>24 hours' notice</b> and entry at reasonable "
                 "times for non-emergencies (§ 27-40-530)."),
            ]),
            ("Ending a lease & eviction", [
                ("The 5-day rule — and its lease trap",
                 "Nonpayment requires a <b>5-day written notice</b> before "
                 "eviction (§ 27-40-710(B)) — <b>but</b> South Carolina lets "
                 "a lease satisfy this permanently with a conspicuous clause "
                 "stating that the lease itself is your 5-day notice. If your "
                 "lease has that clause, the landlord can file on day 6 with "
                 "no further warning. Check your lease for it now, not when "
                 "rent is late."),
                ("Other timelines",
                 "Month-to-month tenancies end on <b>30 days' notice</b> "
                 "(§ 27-40-770). Lockouts and utility shutoffs are illegal "
                 "(§ 27-40-660), retaliation for complaints is prohibited "
                 "(§ 27-40-910), and only court process can remove you."),
            ]),
        ],
        "faqs": [
            ("How long does a South Carolina landlord have to return my deposit?",
             "30 days after the tenancy ends (or your demand with a forwarding "
             "address, if later), with an itemized statement (S.C. Code "
             "§ 27-40-410). Bad-faith withholding = triple damages plus "
             "attorney's fees."),
            ("How much notice before eviction for unpaid rent in South Carolina?",
             "5 days' written notice — unless your lease contains a conspicuous "
             "clause making the lease itself the permanent 5-day notice, in which "
             "case no further warning is required (§ 27-40-710(B)). Check your "
             "lease."),
            ("How much notice before my landlord can enter in South Carolina?",
             "At least 24 hours, at reasonable times, except emergencies "
             "(§ 27-40-530)."),
            ("Is there a security deposit limit in South Carolina?",
             "No cap on the amount — the protections are the 30-day itemized "
             "return and triple damages for bad-faith withholding "
             "(§ 27-40-410)."),
        ],
    },
    "il": {
        "name": "Illinois",
        "statute": "Illinois Security Deposit Return Act (765 ILCS 710) and related acts",
        "quick": [
            ("Deposit cap", "None (state)"),
            ("Itemization", "30 days"),
            ("Full return", "45 days"),
            ("Bad faith", "2x + fees"),
        ],
        "sections": [
            ("Security deposits — the 2024 change", [
                ("Everyone's covered now",
                 "For decades the Security Deposit Return Act only applied to "
                 "buildings with 5+ units. <b>Since January 1, 2024, it "
                 "covers every residential landlord in Illinois</b> "
                 "(765 ILCS 710) — many older guides still describe the old "
                 "threshold. No statewide cap on amounts, but the return "
                 "mechanics are strict."),
                ("The two-clock system",
                 "Deducting for damage? The landlord must deliver an itemized "
                 "statement <b>within 30 days</b> of move-out with paid "
                 "receipts or estimates (estimates require actual receipts "
                 "within 30 more days). No statement? The <b>full deposit is "
                 "due within 45 days</b>. Refusal or bad faith costs the "
                 "landlord <b>twice the deposit plus court costs and "
                 "attorney's fees</b>. Deposits in buildings of 25+ units "
                 "held 6+ months also earn interest (765 ILCS 715)."),
            ]),
            ("The local-ordinance layer — check your city", [
                ("Chicago and friends",
                 "If you rent in <b>Chicago</b>, the RLTO adds much stronger "
                 "rules: deposit interest, receipts for repairs over $100, "
                 "<b>48 hours' entry notice</b> (Mun. Code 5-12-050), and "
                 "capped late fees. <b>Suburban Cook County</b> has its own "
                 "RTLO, and <b>Evanston, Oak Park, and Mount Prospect</b> "
                 "run their own ordinances. Outside those, state law and "
                 "your lease govern — including entry, where Illinois has no "
                 "statewide notice statute and \"reasonable notice\" is the "
                 "norm."),
            ]),
            ("Ending a lease & eviction", [
                ("Timelines",
                 "Nonpayment requires a <b>5-day written notice</b> to pay "
                 "before filing (735 ILCS 5/9-209); paying in full within "
                 "the window cures it. Month-to-month tenancies end on "
                 "<b>30 days' notice</b> (9-207). Lockouts are illegal; only "
                 "court process removes you. Statewide, local rent control "
                 "is preempted by the Rent Control Preemption Act — no "
                 "Illinois city may cap rents."),
                ("Retaliation",
                 "The Landlord Retaliation Act (in force since 2023) "
                 "prohibits eviction, rent hikes, or service cuts in "
                 "response to complaints or asserting rights, with damages "
                 "and fee-shifting for violations."),
            ]),
        ],
        "faqs": [
            ("How long does an Illinois landlord have to return my deposit?",
             "Itemized deductions within 30 days (with receipts), or the full "
             "deposit within 45 days if no statement is provided — and since "
             "January 2024 this applies to ALL residential landlords, not just "
             "5+ unit buildings (765 ILCS 710). Bad faith = double the deposit "
             "plus fees."),
            ("Is there a security deposit limit in Illinois?",
             "Not at the state level. Chicago's RLTO and some suburbs impose "
             "their own deposit and interest rules — check your city's "
             "ordinance."),
            ("How much notice before my landlord can enter in Illinois?",
             "No statewide statute — reasonable notice is the norm. In Chicago, "
             "the RLTO requires 48 hours (Mun. Code 5-12-050)."),
            ("How much notice before eviction for unpaid rent in Illinois?",
             "A 5-day written notice to pay must come first; paying in full "
             "within the 5 days cures it (735 ILCS 5/9-209)."),
        ],
    },
    "oh": {
        "name": "Ohio",
        "statute": "Ohio Revised Code, Chapter 5321 (Landlords and Tenants)",
        "quick": [
            ("Deposit cap", "None"),
            ("Deposit return", "30 days"),
            ("Entry notice", "24 hours"),
            ("Nonpayment notice", "3 days"),
        ],
        "sections": [
            ("Security deposits", [
                ("The rules",
                 "No cap on amounts. Return with an itemized statement is due "
                 "<b>within 30 days</b> of the tenancy ending — give your "
                 "forwarding address in writing to trigger the full remedy "
                 "(ORC § 5321.16). Interest quirk: any deposit portion "
                 "<b>exceeding $50 or one month's rent</b> that's held 6+ "
                 "months earns 5% annual interest on the excess."),
                ("The double-recovery remedy",
                 "Wrongfully withheld amounts entitle you to <b>the amount "
                 "due PLUS damages equal to the amount wrongfully withheld "
                 "— effectively double — plus attorney's fees</b> "
                 "(§ 5321.16(C)). Ohio courts apply this mechanically when "
                 "the 30-day/itemization rules are blown."),
            ]),
            ("Repairs — Ohio's rent-escrow system", [
                ("How it works",
                 "Landlords must keep the unit fit and habitable "
                 "(§ 5321.04). Ohio's signature remedy: if you're <b>current "
                 "on rent</b>, give written notice of the problem; if it's "
                 "not fixed within 30 days (or reasonably promptly for "
                 "emergencies), you may <b>deposit your rent with the "
                 "municipal court clerk</b> (§ 5321.07) — the rent keeps "
                 "accruing but the landlord can't touch it until repairs "
                 "happen, and the court can order repairs or release funds "
                 "to you. Far safer than unilateral withholding."),
                ("Entry notice",
                 "At least <b>24 hours' notice</b> and entry at reasonable "
                 "times, except emergencies (§ 5321.04(A)(8)). Abuse of "
                 "access supports damages and an injunction."),
            ]),
            ("Ending a lease & eviction", [
                ("Timelines",
                 "Nonpayment and most evictions start with a <b>3-day "
                 "notice</b> containing statutorily required language "
                 "(ORC § 1923.04). Ohio's 3-day notice is <b>not</b> "
                 "curable by statute — the landlord can proceed even if you "
                 "pay, though most accept payment. Month-to-month tenancies "
                 "end on <b>30 days' notice</b> (§ 5321.17). Lockouts and "
                 "utility shutoffs are illegal (§ 5321.15)."),
                ("Retaliation",
                 "Eviction, rent hikes, or service cuts for complaining to a "
                 "government agency, the landlord, or joining a tenant "
                 "organization are prohibited (§ 5321.02)."),
            ]),
        ],
        "faqs": [
            ("How long does an Ohio landlord have to return my deposit?",
             "30 days after the tenancy ends, itemized — and wrongful "
             "withholding entitles you to the amount due plus equal damages "
             "(double) plus attorney's fees (ORC § 5321.16). Give a written "
             "forwarding address."),
            ("Can I withhold rent for repairs in Ohio?",
             "Use rent escrow instead: if you're current on rent and the "
             "landlord ignores written notice for 30 days, deposit rent with "
             "the municipal court clerk (§ 5321.07) — protected leverage "
             "without eviction risk."),
            ("How much notice before entry in Ohio?",
             "At least 24 hours, at reasonable times, except emergencies "
             "(§ 5321.04(A)(8))."),
            ("Does paying rent stop a 3-day notice in Ohio?",
             "Not automatically — Ohio's 3-day notice isn't statutorily "
             "curable, though many landlords accept payment. Treat any 3-day "
             "notice as urgent (ORC § 1923.04)."),
        ],
    },
    "mi": {
        "name": "Michigan",
        "statute": "Michigan Security Deposit Act (MCL 554.601 et seq.) and Truth in Renting Act",
        "quick": [
            ("Deposit cap", "1.5 months' rent"),
            ("Itemization", "30 days"),
            ("Landlord must sue by", "45 days"),
            ("Nonpayment demand", "7 days"),
        ],
        "sections": [
            ("Security deposits — a procedural chess game", [
                ("The setup",
                 "Deposits are capped at <b>1.5 months' rent</b> "
                 "(MCL 554.602). Within 14 days of move-in, the landlord "
                 "must give you written notice of where the deposit is held "
                 "and your obligation to provide a forwarding address within "
                 "4 days of moving out (554.603). You must also get "
                 "<b>inventory checklists</b> at move-in — complete yours "
                 "carefully; it's the baseline every damage claim gets "
                 "measured against (554.608)."),
                ("The move-out sequence — know your moves",
                 "The landlord has <b>30 days</b> to send an itemized damage "
                 "list with the statutory bold-print notice (554.609). "
                 "You then have <b>7 days to respond disputing</b> the "
                 "charges. Here's Michigan's unique twist: once you dispute, "
                 "the landlord <b>must file a lawsuit within 45 days of "
                 "move-out to keep a dime</b> — no suit means they waive all "
                 "claimed damages and owe you <b>double the amount "
                 "retained</b> (554.613). Dispute in writing, on time, every "
                 "time."),
            ]),
            ("Repairs & privacy", [
                ("Habitability",
                 "Landlords must keep the premises fit, in reasonable "
                 "repair, and code-compliant (MCL 554.139) — a covenant "
                 "courts read into every lease. Remedies run through "
                 "written notice, then court action or rent escrow; the "
                 "Truth in Renting Act also voids abusive lease clauses "
                 "(554.633)."),
                ("Entry",
                 "Michigan has <b>no statute setting entry notice</b> — "
                 "your lease governs, with reasonable notice the enforceable "
                 "norm. Lockouts and utility shutoffs are illegal "
                 "(600.2918), with damages of up to 3x actual injury or "
                 "$200, whichever is greater."),
            ]),
            ("Ending a lease & eviction", [
                ("Timelines",
                 "Nonpayment requires a <b>7-day written demand for "
                 "possession</b> before filing (MCL 600.5714) — paying in "
                 "full within the window ends it. Month-to-month tenancies "
                 "end on one rental period's notice — practically <b>one "
                 "month</b> (554.134). Only court-ordered eviction can "
                 "remove you."),
            ]),
        ],
        "faqs": [
            ("What's the maximum security deposit in Michigan?",
             "1.5 months' rent (MCL 554.602) — no lease term can increase it."),
            ("What should I do when my Michigan landlord sends a damage list?",
             "Respond disputing it in writing within 7 days. Once you dispute, "
             "the landlord must sue within 45 days of your move-out or waive "
             "everything and owe you double the amount retained (MCL 554.613)."),
            ("How long does a Michigan landlord have to return my deposit?",
             "The itemized damage list is due within 30 days (MCL 554.609). "
             "Provide your forwarding address within 4 days of moving out to "
             "preserve your full rights."),
            ("How much notice before eviction for unpaid rent in Michigan?",
             "A 7-day written demand for possession, curable by paying in full "
             "(MCL 600.5714)."),
        ],
    },
    "pa": {
        "name": "Pennsylvania",
        "statute": "Pennsylvania Landlord and Tenant Act of 1951 (68 P.S. § 250.101 et seq.)",
        "quick": [
            ("Deposit cap yr 1", "2 months"),
            ("Deposit cap yr 2+", "1 month"),
            ("Deposit return", "30 days"),
            ("Nonpayment notice", "10 days"),
        ],
        "sections": [
            ("Security deposits — the shrinking cap", [
                ("Two months, then one",
                 "Pennsylvania's cap steps down over time: <b>two months' "
                 "rent during the first year</b> of tenancy, then <b>one "
                 "month from year two onward</b> (68 P.S. § 250.511a) — "
                 "meaning after your first anniversary you can demand the "
                 "excess back. Deposits over $100 held past <b>two years</b> "
                 "must sit in escrow with <b>annual interest paid to you</b> "
                 "from year three (§ 250.511b)."),
                ("Return & double damages",
                 "Return with an itemized list is due <b>within 30 days</b> "
                 "of the lease ending or you vacating (§ 250.512). Provide "
                 "your new address in writing — it's a condition of the "
                 "penalty remedy. Blowing the 30 days without the list "
                 "forfeits the landlord's claims and exposes them to "
                 "<b>double the deposit</b> in damages."),
            ]),
            ("Repairs & privacy", [
                ("Habitability",
                 "Pennsylvania's implied warranty of habitability (from "
                 "<i>Pugh v. Holmes</i>) can't be waived: serious defects — "
                 "no heat, water, structural hazards — support rent "
                 "abatement, repair-and-deduct after notice and a reasonable "
                 "time, or termination. Document everything in writing; "
                 "Philadelphia adds its own certificate-of-rental-suitability "
                 "and lead-safety requirements."),
                ("Entry",
                 "No statewide entry-notice statute — the lease governs, "
                 "with reasonable notice the norm. Lockouts and utility "
                 "shutoffs are prohibited; only court process evicts."),
            ]),
            ("Ending a lease & eviction", [
                ("Timelines",
                 "Nonpayment requires a <b>10-day notice to quit</b> "
                 "(§ 250.501); other breaches get 15 days (leases of a year "
                 "or less) or 30 days (longer). <b>Watch for waivers</b>: "
                 "Pennsylvania uniquely allows leases to waive the notice to "
                 "quit entirely — if your lease has that clause, the "
                 "landlord can file with no warning. Check before signing. "
                 "Cases start in Magisterial District Court with appeal "
                 "rights to Common Pleas."),
            ]),
        ],
        "faqs": [
            ("How much can a Pennsylvania landlord charge for a deposit?",
             "Two months' rent in the first year, dropping to one month from "
             "year two — you can demand the excess back after your first year "
             "(68 P.S. § 250.511a). Deposits over $100 held past two years earn "
             "you annual interest."),
            ("How long does a PA landlord have to return my deposit?",
             "30 days with an itemized list (§ 250.512). Give your new address "
             "in writing; violations expose the landlord to double damages."),
            ("How much notice before eviction for unpaid rent in Pennsylvania?",
             "A 10-day notice to quit (§ 250.501) — unless your lease waived "
             "notice entirely, which Pennsylvania allows. Check your lease for "
             "a waiver clause."),
            ("How much notice before my landlord can enter in Pennsylvania?",
             "No statewide statute — your lease governs, with reasonable notice "
             "as the enforceable norm."),
        ],
    },
    "nj": {
        "name": "New Jersey",
        "statute": "N.J. Security Deposit Act (N.J.S.A. 46:8-19) and Anti-Eviction Act (2A:18-61.1)",
        "quick": [
            ("Deposit cap", "1.5 months' rent"),
            ("Deposit return", "30 days"),
            ("Wrongful withholding", "2x + costs"),
            ("Eviction", "Just cause required"),
        ],
        "sections": [
            ("Security deposits", [
                ("Cap, interest, and the annual limit",
                 "Deposits are capped at <b>1.5 months' rent</b>, and any "
                 "additional deposit collected in later years can't exceed "
                 "<b>10% of the current deposit per year</b> "
                 "(N.J.S.A. 46:8-21.2). The deposit must be held in a New "
                 "Jersey money-market fund or interest-bearing account with "
                 "the institution disclosed to you in writing — and the "
                 "<b>interest is yours</b>, paid annually in cash or as a "
                 "rent credit (46:8-19)."),
                ("Return & double damages",
                 "Return with an itemized statement — by personal delivery "
                 "or registered/certified mail — is due <b>within 30 days</b> "
                 "of the tenancy ending (46:8-21.1). Wrongful withholding "
                 "entitles you to <b>double the amount due plus court "
                 "costs</b>. Bonus rule: if the landlord never properly "
                 "deposited or disclosed the account, you can direct the "
                 "deposit be applied to rent."),
            ]),
            ("The Anti-Eviction Act — NJ's defining protection", [
                ("Just cause, statewide, permanent",
                 "For most rentals (owner-occupied 2–3 family buildings "
                 "excepted), a landlord <b>cannot refuse to renew or evict "
                 "without one of the statutory good causes</b> "
                 "(N.J.S.A. 2A:18-61.1) — nonpayment, lease violations after "
                 "notice, owner move-in, and other enumerated grounds. "
                 "Reaching the end of a lease term is <b>not</b> cause. This "
                 "makes New Jersey tenancies among the most durable in the "
                 "country."),
                ("Rent increases",
                 "No statewide cap, but increases can only take effect with "
                 "proper notice ending the old terms, must not be "
                 "\"unconscionable,\" and — critically — <b>over 100 NJ "
                 "municipalities have local rent control</b> (Newark, Jersey "
                 "City, Elizabeth, Paterson, and many more). Always check "
                 "your town's ordinance before accepting an increase."),
            ]),
            ("Repairs, habitability & eviction process", [
                ("Habitability",
                 "New Jersey's implied warranty of habitability (from "
                 "<i>Marini v. Ireland</i>) supports repair-and-deduct after "
                 "notice for vital services, rent abatement, and habitability "
                 "as an eviction defense."),
                ("Nonpayment moves fast — with one saving grace",
                 "NJ landlords generally need <b>no advance notice</b> "
                 "before filing a nonpayment case — the summons itself may "
                 "be your first warning. The protection: <b>paying "
                 "everything owed before or even on the trial date ends the "
                 "case</b>. Never ignore an NJ eviction summons; the courts "
                 "also run mandatory settlement conferences. Lockouts are "
                 "criminal; only a court officer executes removals."),
            ]),
        ],
        "faqs": [
            ("How much can a New Jersey landlord collect as a deposit?",
             "1.5 months' rent, with later-year additions capped at 10% of the "
             "deposit annually (N.J.S.A. 46:8-21.2). It must be held in a "
             "disclosed NJ interest-bearing account with the interest paid to "
             "you."),
            ("How long does an NJ landlord have to return my deposit?",
             "30 days, itemized, by personal delivery or registered/certified "
             "mail (46:8-21.1). Wrongful withholding = double the amount due "
             "plus court costs."),
            ("Can my New Jersey landlord refuse to renew my lease?",
             "Generally no — the Anti-Eviction Act requires statutory good "
             "cause to remove most tenants, and lease expiration alone is not "
             "cause (N.J.S.A. 2A:18-61.1)."),
            ("Is there rent control in New Jersey?",
             "Not statewide, but over 100 municipalities have local rent "
             "control ordinances — check your town before accepting any "
             "increase. Statewide, increases must also not be unconscionable."),
        ],
    },
    "ma": {
        "name": "Massachusetts",
        "statute": "Mass. General Laws c. 186, § 15B",
        "quick": [
            ("Deposit cap", "1 month's rent"),
            ("Deposit return", "30 days"),
            ("Violations", "Treble damages"),
            ("Move-in charges", "Strictly limited"),
        ],
        "sections": [
            ("Security deposits — the strictest law in America", [
                ("What can be charged at signing",
                 "Massachusetts limits move-in charges to exactly four "
                 "things: first month's rent, last month's rent, a security "
                 "deposit of at most <b>one month's rent</b>, and a "
                 "lock/key fee (G.L. c. 186, § 15B(1)(b)). <b>Pet fees, "
                 "move-in fees, application fees from tenants — all "
                 "illegal.</b> If you were charged one, you have a claim."),
                ("The landlord's obligation gauntlet",
                 "Holding a deposit lawfully requires: a receipt at payment; "
                 "the deposit in a <b>separate interest-bearing Massachusetts "
                 "bank account</b> with the bank name, address, and account "
                 "number disclosed within 30 days; a signed <b>statement of "
                 "condition</b> within 10 days of tenancy; <b>5% interest</b> "
                 "(or the bank rate) paid annually; and return within <b>30 "
                 "days</b> of move-out with a <b>sworn</b>, itemized "
                 "statement. Miss steps and the landlord forfeits the right "
                 "to keep anything."),
                ("Treble damages — automatic for the big ones",
                 "Failing to return the deposit within 30 days, never "
                 "depositing it in a proper account, or keeping it after "
                 "forfeiture triggers <b>automatic triple damages plus 5% "
                 "interest, court costs, and attorney's fees</b> "
                 "(§ 15B(7)). Massachusetts courts apply this "
                 "mechanically — it is the most tenant-favorable deposit "
                 "regime in the country, and most landlords violate at "
                 "least one requirement."),
            ]),
            ("Repairs & privacy", [
                ("Habitability",
                 "The State Sanitary Code sets detailed minimums — heat "
                 "(64°F nights/68°F days in season), hot water, no pests. "
                 "Remedies include rent withholding (protected when "
                 "conditions are code-violating and reported), "
                 "repair-and-deduct up to 4 months' rent for code "
                 "violations (c. 111, § 127L), and abatement."),
                ("Entry",
                 "Entry is limited to statutory purposes (inspection, "
                 "repairs, showing) — no notice period is specified, so "
                 "reasonable notice is the norm; the lease can't grant "
                 "blanket access (§ 15B(1)(a))."),
            ]),
            ("Ending a lease & eviction", [
                ("Timelines",
                 "Nonpayment requires a <b>14-day notice to quit</b> "
                 "(c. 186, § 11). Tenants without a similar notice in the "
                 "prior 12 months can <b>cure by paying everything owed by "
                 "the court answer date</b>. Month-to-month tenancies end on "
                 "30 days' or one full rental period's notice, whichever is "
                 "longer. Only court process (summary process) removes you; "
                 "rent control has been banned statewide since 1994."),
            ]),
        ],
        "faqs": [
            ("What can a Massachusetts landlord charge at move-in?",
             "Only four things: first month's rent, last month's rent, a "
             "security deposit up to one month's rent, and a lock/key fee "
             "(G.L. c. 186, § 15B). Pet fees and move-in fees are illegal."),
            ("What happens if my MA landlord doesn't return my deposit in 30 days?",
             "Automatic treble damages plus interest, costs, and attorney's "
             "fees (§ 15B(7)) — the strictest deposit penalty in the country. "
             "The same applies if it was never held in a proper Massachusetts "
             "escrow account."),
            ("Am I owed interest on my deposit in Massachusetts?",
             "Yes — 5% annually (or the bank rate), on both the security "
             "deposit and last month's rent, payable each year (§ 15B)."),
            ("Can I be evicted for nonpayment if I pay late in Massachusetts?",
             "The 14-day notice is curable: if you haven't received a similar "
             "notice in the past 12 months, paying everything owed by your "
             "court answer date ends the case (c. 186, § 11)."),
        ],
    },
    "md": {
        "name": "Maryland",
        "statute": "Md. Code, Real Property § 8-203 et seq.",
        "quick": [
            ("Deposit cap", "1 month's rent"),
            ("Deposit return", "45 days"),
            ("Wrongful withholding", "Up to 3x"),
            ("Nonpayment notice", "10 days"),
        ],
        "sections": [
            ("Security deposits", [
                ("The new one-month cap",
                 "For leases signed on or after <b>October 1, 2024</b>, "
                 "deposits are capped at <b>one month's rent</b> "
                 "(Real Prop. § 8-203(b)) — down from the old two months, "
                 "and another change older guides miss. Deposits over $50 "
                 "must sit in a Maryland escrow account and earn interest "
                 "at the greater of 1.5% or the U.S. Treasury yield when "
                 "held 6+ months."),
                ("Return & the inspection right",
                 "Return with an itemized statement is due <b>within 45 "
                 "days</b>. Wrongful withholding exposes the landlord to "
                 "<b>up to three times the withheld amount plus attorney's "
                 "fees</b> (§ 8-203(e)). Maryland also gives you the right "
                 "to be <b>present at the move-out inspection</b> — request "
                 "it by certified mail within 15 days of moving; the "
                 "landlord must then notify you of the date and time."),
            ]),
            ("Repairs & privacy", [
                ("Rent escrow",
                 "For serious defects — no heat, water, electricity, "
                 "structural hazards — after written notice and a "
                 "reasonable time (presumed 30 days), Maryland's remedy is "
                 "<b>rent escrow</b>: pay rent into court, which can order "
                 "repairs, abate rent, or release funds to you "
                 "(§ 8-211). Far safer than unilateral withholding."),
                ("Entry",
                 "No statewide entry-notice statute — your lease and county "
                 "code govern (several counties and Baltimore City set "
                 "their own rules). Reasonable notice is the enforceable "
                 "norm."),
            ]),
            ("Ending a lease & eviction", [
                ("Timelines",
                 "Since October 2021, nonpayment requires a <b>10-day "
                 "written notice of intent to file</b> before the landlord "
                 "can start a Failure to Pay Rent case (§ 8-401). Tenants "
                 "retain the <b>right of redemption</b> — paying everything "
                 "owed (plus costs) even up to eviction day stops most "
                 "removals, unless you've had 3+ judgments in the prior 12 "
                 "months (4 in Baltimore City). Month-to-month terminations "
                 "generally require 60 days' notice from the landlord. "
                 "Local layer: several counties (and Takoma Park) have "
                 "rent stabilization — check your county."),
            ]),
        ],
        "faqs": [
            ("How much can a Maryland landlord charge for a deposit?",
             "One month's rent for leases signed on or after October 1, 2024 "
             "(Real Prop. § 8-203(b)) — the old two-month cap no longer "
             "applies to new leases."),
            ("How long does a Maryland landlord have to return my deposit?",
             "45 days, itemized, with interest owed on deposits over $50 held "
             "6+ months. Wrongful withholding = up to 3x plus attorney's fees "
             "(§ 8-203(e))."),
            ("Can I be present at the move-out inspection in Maryland?",
             "Yes — request it by certified mail within 15 days of moving out, "
             "and the landlord must notify you of the inspection date and time "
             "(§ 8-203.1)."),
            ("Can I stop a Maryland eviction by paying what I owe?",
             "Usually yes — Maryland's right of redemption lets you stop a "
             "nonpayment eviction by paying everything owed plus costs, even "
             "on eviction day, unless you've had 3+ rent judgments in the past "
             "12 months (4 in Baltimore City)."),
        ],
    },
    "mn": {
        "name": "Minnesota",
        "statute": "Minn. Stat. Chapter 504B (major reforms effective 2024–2025)",
        "quick": [
            ("Deposit cap", "None"),
            ("Deposit return", "21 days"),
            ("Entry notice", "24 hours"),
            ("Nonpayment notice", "14 days"),
        ],
        "sections": [
            ("Security deposits", [
                ("Return, interest & the double penalty",
                 "No cap on amounts, but return with an itemized statement "
                 "is due <b>within 21 days</b> of the tenancy ending (and "
                 "your forwarding address), with <b>1% simple annual "
                 "interest</b> (Minn. Stat. § 504B.178). A landlord who "
                 "blows the deadline, skips the itemization, or ignores the "
                 "new <b>initial and move-out inspection</b> duties "
                 "(§ 504B.182, since 2024) owes you the wrongfully withheld "
                 "amount <b>plus an equal amount as a penalty</b> — "
                 "double — and bad faith adds punitive damages."),
                ("Don't skip the last month's rent",
                 "Withholding your final month's rent \"because they have "
                 "my deposit\" is specifically penalized in Minnesota "
                 "(§ 504B.178, subd. 8) — it can cost you a penalty equal "
                 "to the withheld portion. Pay the last month; collect the "
                 "deposit properly."),
            ]),
            ("The 2024–25 reform package", [
                ("What changed",
                 "Minnesota's recent overhaul added: a mandatory "
                 "<b>detailed 14-day written notice before any nonpayment "
                 "eviction filing</b> (§ 504B.321); <b>total-fee "
                 "transparency</b> — all non-optional fees must appear in "
                 "ads and the lease; late fees capped at <b>8%</b> "
                 "(§ 504B.177); a right to <b>organize tenant "
                 "associations</b> (2025); and required notice of the "
                 "state's rights handbook at signing."),
            ]),
            ("Repairs & privacy", [
                ("Habitability covenants",
                 "Landlords covenant that the unit is fit, in reasonable "
                 "repair, and code-compliant (§ 504B.161) — unwaivable. "
                 "Remedies include rent escrow through the court "
                 "(§ 504B.385) and emergency repair actions for loss of "
                 "essential services (§ 504B.381)."),
                ("Entry — with teeth",
                 "At least <b>24 hours' notice</b>, specifying a time "
                 "window, and entry only between <b>8 a.m. and 8 p.m.</b> "
                 "unless you agree otherwise (§ 504B.211). Violations "
                 "carry up to a <b>$500 civil penalty each</b>, plus rent "
                 "reduction and attorney's fees."),
            ]),
        ],
        "faqs": [
            ("How long does a Minnesota landlord have to return my deposit?",
             "21 days after the tenancy ends and you provide a forwarding "
             "address, with 1% annual interest and an itemized statement "
             "(Minn. Stat. § 504B.178). Violations = the withheld amount plus "
             "an equal penalty."),
            ("How much notice before eviction for unpaid rent in Minnesota?",
             "Since the 2024 reforms, a detailed 14-day written notice must "
             "come before any nonpayment filing (§ 504B.321)."),
            ("How much notice before my landlord can enter in Minnesota?",
             "At least 24 hours, specifying a time window, between 8 a.m. and "
             "8 p.m. — violations carry up to a $500 penalty each "
             "(§ 504B.211)."),
            ("Can I skip my last month's rent since my landlord has my deposit?",
             "No — Minnesota specifically penalizes this, up to the amount "
             "withheld (§ 504B.178, subd. 8). Pay the final month and collect "
             "the deposit through the 21-day process."),
        ],
    },
    "wi": {
        "name": "Wisconsin",
        "statute": "Wis. Stat. § 704.28 and Wis. Admin. Code ATCP 134",
        "quick": [
            ("Deposit cap", "None"),
            ("Deposit return", "21 days"),
            ("Entry notice", "12 hours"),
            ("Violations", "2x + fees"),
        ],
        "sections": [
            ("Security deposits", [
                ("The consumer-protection twist",
                 "Wisconsin runs deposits through its consumer-protection "
                 "code (ATCP 134), which means violations support <b>double "
                 "damages plus attorney's fees</b> via Wis. Stat. "
                 "§ 100.20(5) — a private right most states don't offer. No "
                 "cap on amounts; return with an itemized statement is due "
                 "<b>within 21 days</b> of you surrendering the premises "
                 "(§ 704.28, ATCP 134.06)."),
                ("The check-in sheet",
                 "You're entitled to at least <b>7 days after move-in</b> to "
                 "document existing damage on a check-in sheet, and the "
                 "landlord must tell you of your right to inspect and to "
                 "receive the prior tenant's deduction list (ATCP "
                 "134.06(1)–(2)). Do it thoroughly — it's the baseline for "
                 "every later dispute."),
            ]),
            ("Repairs & privacy", [
                ("Habitability & repairs",
                 "Untenantable conditions let you move out or abate rent "
                 "proportionally (§ 704.07). Landlords must disclose "
                 "code violations and uncorrected building-code orders "
                 "before signing (ATCP 134.04) — undisclosed ones support "
                 "the double-damages remedy too."),
                ("Entry notice",
                 "At least <b>12 hours' advance notice</b> and entry at "
                 "reasonable times, unless you consent to shorter "
                 "(§ 704.05(2), ATCP 134.09(2))."),
            ]),
            ("Ending a lease & eviction", [
                ("Timelines",
                 "For year-or-less leases, nonpayment gets a <b>5-day "
                 "notice with a right to cure</b>; a second default within "
                 "12 months can get a 14-day non-curable notice "
                 "(§ 704.17). Month-to-month tenancies end on <b>28 days' "
                 "notice</b> (§ 704.19). Self-help evictions and retaliatory "
                 "actions are prohibited (ATCP 134.09); only court process "
                 "removes you. Rent control is preempted statewide."),
            ]),
        ],
        "faqs": [
            ("How long does a Wisconsin landlord have to return my deposit?",
             "21 days after you surrender the premises, with an itemized "
             "statement (Wis. Stat. § 704.28). Violations support double "
             "damages plus attorney's fees under § 100.20(5)."),
            ("How much notice before my landlord can enter in Wisconsin?",
             "At least 12 hours, at reasonable times, unless you agree to "
             "less (§ 704.05(2), ATCP 134.09(2))."),
            ("What's the check-in sheet rule in Wisconsin?",
             "You get at least 7 days after move-in to document existing "
             "damage, plus the right to see the prior tenant's deduction "
             "list (ATCP 134.06). Complete it — it controls later disputes."),
            ("How much notice to end a month-to-month lease in Wisconsin?",
             "28 days' written notice by either side (§ 704.19)."),
        ],
    },
    "mo": {
        "name": "Missouri",
        "statute": "Mo. Rev. Stat. § 535.300 and Chapter 441",
        "quick": [
            ("Deposit cap", "2 months' rent"),
            ("Deposit return", "30 days"),
            ("Wrongful withholding", "Up to 2x"),
            ("Inspection right", "Yes"),
        ],
        "sections": [
            ("Security deposits", [
                ("Cap, clock & inspection",
                 "Deposits are capped at <b>two months' rent</b> "
                 "(Mo. Rev. Stat. § 535.300). Return with an itemized "
                 "statement is due <b>within 30 days</b>, and wrongful "
                 "withholding exposes the landlord to <b>up to twice the "
                 "amount wrongfully kept</b>. You also have the right to be "
                 "<b>present at the move-out inspection</b> — the landlord "
                 "must give you reasonable notice of its date and time. "
                 "Attend it."),
            ]),
            ("Repairs", [
                ("Repair-and-deduct — with strict conditions",
                 "Missouri's implied warranty of habitability (from "
                 "<i>King v. Moorehead</i>) is backed by a narrow statutory "
                 "repair-and-deduct: after 14 days' written notice, tenants "
                 "who've lived in the unit 6+ months, are current on rent, "
                 "and meet the statute's conditions may repair code-level "
                 "problems and deduct up to the greater of $300 or half a "
                 "month's rent, once per 12 months (§ 441.234). Follow the "
                 "conditions exactly — informal withholding risks "
                 "eviction."),
            ]),
            ("Privacy & eviction", [
                ("Entry",
                 "No statutory entry-notice period — your lease governs, "
                 "with reasonable notice the norm."),
                ("Timelines — Missouri moves quickly",
                 "There's <b>no statutory pre-filing notice for "
                 "nonpayment</b> — a landlord may demand rent and file a "
                 "rent-and-possession suit as soon as rent is due and "
                 "unpaid (§ 535.020). The saving grace: <b>paying all rent "
                 "owed plus costs before judgment stops the case</b>. "
                 "Month-to-month tenancies end on <b>one month's "
                 "notice</b> (§ 441.060). Lockouts and utility shutoffs "
                 "are illegal (§ 441.233), and only court process removes "
                 "you."),
            ]),
        ],
        "faqs": [
            ("How much can a Missouri landlord charge for a deposit?",
             "Two months' rent maximum (Mo. Rev. Stat. § 535.300)."),
            ("How long does a Missouri landlord have to return my deposit?",
             "30 days, itemized — wrongful withholding exposes the landlord "
             "to up to twice the amount kept (§ 535.300). You're entitled to "
             "reasonable notice of, and attendance at, the move-out "
             "inspection."),
            ("Can my Missouri landlord sue the day rent is late?",
             "Essentially yes — no pre-filing notice is required for "
             "nonpayment. But paying all rent plus costs before judgment "
             "stops the case (§ 535.020)."),
            ("Can I repair and deduct in Missouri?",
             "Only under § 441.234's strict conditions: 6+ months' tenancy, "
             "current on rent, 14 days' written notice, code-level problems, "
             "capped at the greater of $300 or half a month's rent, once per "
             "year. Outside those rails, don't withhold."),
        ],
    },
    "in": {
        "name": "Indiana",
        "statute": "Indiana Code, Title 32, Article 31 (Landlord-Tenant Relations)",
        "quick": [
            ("Deposit cap", "None"),
            ("Deposit return", "45 days"),
            ("Nonpayment notice", "10 days"),
            ("Entry notice", "Reasonable"),
        ],
        "sections": [
            ("Security deposits", [
                ("The 45-day clock — and its trigger",
                 "No cap on amounts. The landlord must mail an itemized "
                 "notice of damages and return any balance <b>within 45 "
                 "days</b> — but the clock only runs once the tenancy has "
                 "ended, you've delivered possession, AND you've supplied a "
                 "<b>written forwarding address</b> (IC 32-31-3-12). Put "
                 "that address in writing at move-out or your remedy "
                 "stalls."),
                ("The penalty",
                 "Missing the 45-day notice means the landlord <b>waives all "
                 "damage claims and owes the full deposit plus your "
                 "attorney's fees</b> (IC 32-31-3-12(b)) — no multiplier, "
                 "but fee-shifting alone makes small-claims cases viable."),
            ]),
            ("Repairs & privacy", [
                ("Habitability",
                 "Landlords must deliver and maintain the unit in a safe, "
                 "clean, habitable condition — working plumbing, electrical, "
                 "HVAC as supplied, and code compliance (IC 32-31-8-5). "
                 "Indiana's enforcement path is written notice, a "
                 "reasonable time, then a court action for damages or an "
                 "order (32-31-8-6) — there's <b>no statutory "
                 "repair-and-deduct</b>, so don't withhold informally."),
                ("Entry notice",
                 "The landlord must give <b>reasonable notice</b> (oral or "
                 "written) and enter at reasonable times (IC 32-31-5-6) — "
                 "no fixed hour count, but blanket-access lease clauses "
                 "don't override the reasonableness requirement."),
            ]),
            ("Ending a lease & eviction", [
                ("Timelines",
                 "Nonpayment requires a <b>10-day notice to pay or "
                 "quit</b> — paying within the window defeats the notice "
                 "(IC 32-31-1-6). Month-to-month tenancies end on <b>one "
                 "month's notice</b> (32-31-1-1). Lockouts and utility "
                 "shutoffs are prohibited; only court process removes you. "
                 "Rent control is preempted statewide."),
            ]),
        ],
        "faqs": [
            ("How long does an Indiana landlord have to return my deposit?",
             "45 days after the tenancy ends, you deliver possession, and you "
             "provide a written forwarding address (IC 32-31-3-12). Missing it "
             "waives all damage claims and adds your attorney's fees."),
            ("Is there a deposit limit in Indiana?",
             "No statutory cap — the protection is the 45-day itemization rule "
             "and fee-shifting for violations."),
            ("Can I repair and deduct in Indiana?",
             "No — Indiana has no statutory repair-and-deduct. Use written "
             "notice, then a court action under IC 32-31-8-6; informal "
             "withholding risks eviction."),
            ("How much notice before eviction for unpaid rent in Indiana?",
             "A 10-day notice to pay or quit, defeated by paying within the "
             "window (IC 32-31-1-6)."),
        ],
    },
    "ky": {
        "name": "Kentucky",
        "statute": "KRS Chapter 383 — URLTA by local adoption; deposit rules statewide",
        "quick": [
            ("Deposit cap", "None"),
            ("URLTA coverage", "~4 counties + cities"),
            ("Entry notice", "2 days (URLTA)"),
            ("Nonpayment notice", "7 days (URLTA)"),
        ],
        "sections": [
            ("The coverage map — read this first", [
                ("Where Kentucky's tenant law actually applies",
                 "Kentucky's URLTA only operates where local governments "
                 "adopted it: about <b>4 of 120 counties — Jefferson "
                 "(Louisville), Fayette (Lexington), Oldham, and Pulaski — "
                 "plus roughly 15 cities</b> (KRS 383.500). Everywhere "
                 "else, your lease and common law govern, and most "
                 "protections below don't apply by statute. Two things "
                 "apply <b>statewide regardless</b>: the security deposit "
                 "rules (KRS 383.580) and domestic-violence lease "
                 "protections (383.300)."),
            ]),
            ("Security deposits — statewide", [
                ("The procedural chain",
                 "No cap on amounts, but KRS 383.580 requires: the deposit "
                 "in a <b>separate, disclosed account</b> at a regulated "
                 "institution; a <b>move-in damage list</b> you can inspect "
                 "and dispute; and a <b>move-out damage list</b> with the "
                 "same rights. <b>Skipping the account or the lists "
                 "forfeits the landlord's right to withhold anything.</b>"),
                ("The refund mechanics",
                 "Rather than one simple deadline, Kentucky runs on demand "
                 "and notice: provide a forwarding address, demand your "
                 "refund in writing, and respond to the final damage list "
                 "— unclaimed refunds can be kept by the landlord <b>60 "
                 "days after notice</b>. Don't leave money on the table by "
                 "going silent."),
            ]),
            ("URLTA-county protections", [
                ("Repairs, entry & eviction",
                 "In adopted jurisdictions: habitability duties with 14-day "
                 "cure notices for material problems (KRS 383.625, "
                 "383.640), essential-service remedies including substitute "
                 "housing (383.640), <b>2 days' notice before entry</b> "
                 "(383.615), a <b>7-day pay-or-quit notice</b> for "
                 "nonpayment (383.660), 30-day month-to-month terminations "
                 "(383.695), and anti-retaliation rules (383.705). Bad-faith "
                 "landlord conduct can support damages up to 3 months' rent "
                 "plus fees. Outside those areas: read your lease "
                 "twice — it's most of your law."),
            ]),
        ],
        "faqs": [
            ("Does Kentucky's landlord-tenant law apply where I live?",
             "The URLTA applies only in ~4 counties (Jefferson, Fayette, "
             "Oldham, Pulaski) and about 15 cities that adopted it "
             "(KRS 383.500). The deposit rules (383.580) and DV protections "
             "apply statewide; everything else depends on your county."),
            ("What deposit protections do all Kentucky renters have?",
             "Statewide: the deposit must sit in a separate disclosed account, "
             "with move-in and move-out damage lists you can inspect and "
             "dispute — skipping any of it forfeits the landlord's right to "
             "withhold (KRS 383.580)."),
            ("How do I get my deposit back in Kentucky?",
             "Provide a written forwarding address, demand the refund in "
             "writing, and respond to the final damage list — unclaimed "
             "refunds can be kept 60 days after notice (KRS 383.580)."),
            ("How much notice before entry in Kentucky?",
             "In URLTA jurisdictions, at least 2 days at reasonable times "
             "(KRS 383.615). Elsewhere, your lease governs."),
        ],
    },
    "al": {
        "name": "Alabama",
        "statute": "Alabama Uniform Residential Landlord and Tenant Act (Ala. Code § 35-9A)",
        "quick": [
            ("Deposit cap", "1 month's rent"),
            ("Deposit return", "60 days"),
            ("Late return penalty", "2x deposit"),
            ("Nonpayment notice", "7 business days"),
        ],
        "sections": [
            ("Security deposits", [
                ("The cap — with a carve-out",
                 "Deposits are capped at <b>one month's rent</b>, but the "
                 "cap excludes separately agreed charges for pets, "
                 "tenant-made alterations, or specific added liability "
                 "(Ala. Code § 35-9A-201(a)) — so a lawful pet deposit can "
                 "ride on top. Anything mislabeled to dodge the cap is "
                 "still \"security.\""),
                ("60 days — the longest clock in the country",
                 "The landlord has <b>60 days</b> after termination and "
                 "delivery of possession to mail your refund or an "
                 "itemized accounting (§ 35-9A-201(b)–(c)) — give a written "
                 "forwarding address at move-out. The teeth: <b>missing the "
                 "60 days costs the landlord double your original "
                 "deposit</b> (§ 35-9A-201(f)). One more trap: an "
                 "unclaimed mailed refund is forfeited to the landlord "
                 "after 90/180-day windows, so cash the check."),
            ]),
            ("Repairs & privacy", [
                ("Habitability",
                 "Landlords must comply with building codes and keep the "
                 "unit habitable — plumbing, heat, water, working supplied "
                 "appliances (§ 35-9A-204). Material noncompliance gets a "
                 "written <b>14-day cure notice</b>; uncured, the lease "
                 "terminates (§ 35-9A-401). Essential-service failures "
                 "support procure-and-deduct or substitute housing "
                 "(§ 35-9A-404). Alabama has <b>no repair-and-deduct for "
                 "ordinary repairs</b> — stay on the statutory paths."),
                ("Entry notice",
                 "At least <b>2 days' notice</b> and entry at reasonable "
                 "times, except emergencies (§ 35-9A-303)."),
            ]),
            ("Ending a lease & eviction", [
                ("Timelines",
                 "Nonpayment requires a <b>7-business-day</b> pay-or-quit "
                 "notice, curable by paying in full (§ 35-9A-421(b)); other "
                 "material violations get 7-business-day cure notices with "
                 "a 14-day termination. Month-to-month tenancies end on "
                 "<b>30 days' notice</b> (§ 35-9A-441). Lockouts and "
                 "utility shutoffs are prohibited (§ 35-9A-407); only court "
                 "process removes you. Alabama has no rent control and "
                 "preempts local attempts."),
            ]),
        ],
        "faqs": [
            ("How much can an Alabama landlord charge for a deposit?",
             "One month's rent, excluding separately agreed pet, alteration, "
             "or added-liability charges (Ala. Code § 35-9A-201(a))."),
            ("How long does an Alabama landlord have to return my deposit?",
             "60 days — the longest window in the country — but missing it "
             "costs the landlord double your original deposit "
             "(§ 35-9A-201(f)). Provide a written forwarding address and cash "
             "the refund promptly; unclaimed refunds are eventually "
             "forfeited."),
            ("How much notice before eviction for unpaid rent in Alabama?",
             "7 business days, curable by paying everything owed within the "
             "window (§ 35-9A-421(b))."),
            ("How much notice before entry in Alabama?",
             "At least 2 days, at reasonable times, except emergencies "
             "(§ 35-9A-303)."),
        ],
    },
    "la": {
        "name": "Louisiana",
        "statute": "La. R.S. 9:3251 et seq. and the Louisiana Civil Code (arts. 2668–2729)",
        "quick": [
            ("Deposit cap", "None"),
            ("Deposit return", "1 month"),
            ("Willful withholding", "$300 or 2x"),
            ("Eviction notice", "5 days (waivable)"),
        ],
        "sections": [
            ("Security deposits", [
                ("The rules",
                 "No cap on amounts. The landlord must return your deposit "
                 "with an itemized statement for any deductions <b>within "
                 "one month</b> of the lease ending — leave a forwarding "
                 "address in writing (La. R.S. 9:3251). Normal wear and "
                 "tear is not deductible."),
                ("The demand letter is the weapon",
                 "Louisiana's penalty hinges on a <b>written demand</b>: if "
                 "the landlord fails to remit within <b>30 days of your "
                 "written demand</b>, that failure is <b>willful by "
                 "definition</b> — entitling you to the wrongfully kept "
                 "amount PLUS the greater of <b>$300 or twice that "
                 "amount</b>, plus attorney's fees (R.S. 9:3252–3253). "
                 "Send the demand by certified mail the day the month "
                 "lapses; it converts a stalling landlord into a statutory "
                 "payout."),
            ]),
            ("Repairs — civil-law style", [
                ("The lessor's warranty",
                 "As the country's civil-law state, Louisiana works "
                 "differently: the Civil Code obliges the lessor to "
                 "maintain the premises suitable for their purpose and "
                 "warrants against vices and defects (arts. 2682, 2696–"
                 "2697) — protections that exist in every lease "
                 "automatically. If the lessor fails to make required "
                 "repairs after demand, art. 2694 allows you to make them "
                 "and <b>deduct the reasonable cost from rent</b> — one of "
                 "the older repair-and-deduct rights in the country. "
                 "Document the demand and costs meticulously."),
                ("Entry",
                 "No statutory notice period — the lease governs; the "
                 "lessor must not disturb your peaceable possession "
                 "(art. 2682(3))."),
            ]),
            ("Ending a lease & eviction", [
                ("The 5-day notice — and the waiver trap",
                 "Eviction starts with a <b>5-day written notice to "
                 "vacate</b> (Code Civ. Proc. art. 4701) — but Louisiana "
                 "allows leases to <b>waive this notice entirely</b>. If "
                 "your lease has a waiver clause, the landlord can go "
                 "straight to court when the lease ends or rent goes "
                 "unpaid. Check your lease for the waiver before you sign, "
                 "not after. Month-to-month tenancies end on <b>10 days' "
                 "notice</b> before the end of the month (Civ. Code "
                 "art. 2728). Only court process and a constable removal "
                 "are lawful — lockouts support damages."),
            ]),
        ],
        "faqs": [
            ("How long does a Louisiana landlord have to return my deposit?",
             "One month after the lease ends, itemized (La. R.S. 9:3251). If "
             "they miss 30 days after your WRITTEN demand, the failure is "
             "willful by definition — worth the wrongful amount plus the "
             "greater of $300 or double, plus attorney's fees (9:3252)."),
            ("Should I send a demand letter for my deposit in Louisiana?",
             "Yes — the written demand is what triggers the statutory "
             "penalty. Send it certified mail as soon as the one-month window "
             "lapses."),
            ("How much notice before eviction in Louisiana?",
             "A 5-day notice to vacate (CCP art. 4701) — unless your lease "
             "waived it, which Louisiana permits. Check your lease for a "
             "waiver clause."),
            ("Can I repair and deduct in Louisiana?",
             "Yes — after demanding repairs the lessor is obliged to make, "
             "Civil Code art. 2694 lets you make them and deduct the "
             "reasonable cost from rent. Keep meticulous records."),
        ],
    },
    "ok": {
        "name": "Oklahoma",
        "statute": "Oklahoma Residential Landlord and Tenant Act (41 O.S. § 101 et seq.)",
        "quick": [
            ("Deposit cap", "None"),
            ("Deposit return", "45 days"),
            ("Demand deadline", "6 months"),
            ("Entry notice", "1 day"),
        ],
        "sections": [
            ("Security deposits — the demand trap", [
                ("You must ASK for it",
                 "Oklahoma's biggest quirk: the deposit isn't returned "
                 "automatically. You must make a <b>written demand</b> for "
                 "it — and if you don't demand within <b>6 months</b> of "
                 "the tenancy ending, <b>the landlord keeps it, "
                 "legally</b> (41 O.S. § 115). Put the demand in writing "
                 "at move-out, every time, no exceptions."),
                ("Once demanded",
                 "The landlord must hold deposits in a <b>federally insured "
                 "escrow account</b> in Oklahoma and, after your demand, "
                 "return the balance with an itemized statement within "
                 "<b>45 days</b> of termination and demand. Willful "
                 "wrongful withholding is a misdemeanor on top of civil "
                 "recovery."),
            ]),
            ("Repairs & privacy", [
                ("Habitability & the $100 repair right",
                 "Landlords must keep the unit habitable — plumbing, heat, "
                 "water, electrical, and code compliance (§ 118). For "
                 "essential-service failures after written notice, remedies "
                 "include procure-and-deduct, substitute housing, or "
                 "termination (§ 121); for minor issues, repair-and-deduct "
                 "is capped at <b>$100</b>. For material noncompliance, a "
                 "written <b>14-day cure / 30-day termination notice</b> "
                 "applies (§ 132)."),
                ("Entry notice",
                 "At least <b>1 day's notice</b> and entry at reasonable "
                 "times, except emergencies (§ 128)."),
            ]),
            ("Ending a lease & eviction", [
                ("Timelines",
                 "Nonpayment requires a <b>5-day written notice</b> to pay "
                 "or the lease terminates (§ 131) — paying in full within "
                 "the window cures it. Month-to-month tenancies end on "
                 "<b>30 days' notice</b> (§ 111). Lockouts and utility "
                 "shutoffs are prohibited (§ 123); only court process "
                 "removes you. No rent control statewide."),
            ]),
        ],
        "faqs": [
            ("How do I get my security deposit back in Oklahoma?",
             "You must demand it in writing — and within 6 months of the "
             "tenancy ending, or the landlord legally keeps it (41 O.S. "
             "§ 115). After demand, the itemized balance is due within 45 "
             "days."),
            ("Where must my Oklahoma deposit be held?",
             "In a federally insured escrow account in Oklahoma (§ 115). "
             "Willful wrongful withholding is a misdemeanor plus civil "
             "liability."),
            ("How much notice before entry in Oklahoma?",
             "At least 1 day, at reasonable times, except emergencies "
             "(§ 128)."),
            ("How much notice before eviction for unpaid rent in Oklahoma?",
             "A 5-day written notice, curable by paying in full within the "
             "window (§ 131)."),
        ],
    },
    "ms": {
        "name": "Mississippi",
        "statute": "Mississippi Residential Landlord and Tenant Act (Miss. Code § 89-8)",
        "quick": [
            ("Deposit cap", "None"),
            ("Deposit return", "45 days (after demand)"),
            ("Violation penalty", "$200 + damages"),
            ("Nonpayment notice", "3 days"),
        ],
        "sections": [
            ("Security deposits — another demand state", [
                ("The clock needs YOUR push",
                 "Mississippi's 45-day return clock only starts after "
                 "termination, delivery of possession, <b>and your "
                 "demand</b> (Miss. Code § 89-8-21(3)) — the deposit isn't "
                 "owed back automatically. Demand it in writing at "
                 "move-out with a forwarding address. Deductions require a "
                 "written itemized notice; wear and tear never qualifies."),
                ("The penalty",
                 "Failing the return or itemization rules (other than in "
                 "good faith) makes the landlord liable for your <b>actual "
                 "damages plus up to $200</b> (§ 89-8-21(4)) — modest, but "
                 "small-claims-viable, and the itemization failure alone "
                 "usually wins the whole deposit back."),
            ]),
            ("Repairs & privacy", [
                ("Habitability",
                 "Landlords must comply with housing codes materially "
                 "affecting health/safety and keep the unit habitable "
                 "(§ 89-8-23). Tenant remedies run through written notice "
                 "and, for uncured material problems, lease termination or "
                 "court action (§ 89-8-13, 89-8-15) — Mississippi's "
                 "repair-and-deduct is narrow, so paper every step."),
                ("Entry",
                 "<b>No entry statute at all</b> — notice and access rules "
                 "exist only if your lease creates them. Negotiate an "
                 "entry-notice clause before signing; without one, your "
                 "protection is the lease's quiet-enjoyment covenant."),
            ]),
            ("Ending a lease & eviction", [
                ("Timelines",
                 "Nonpayment gets a <b>3-day notice</b> to pay or the "
                 "lease terminates (§ 89-8-13). Substantial violations "
                 "materially affecting health and safety can terminate "
                 "<b>without any notice</b> (§ 89-8-19) — by either side. "
                 "Month-to-month tenancies end on <b>30 days' written "
                 "notice</b> (week-to-week: one week). Lockouts are "
                 "unlawful; eviction runs through the courts."),
            ]),
        ],
        "faqs": [
            ("How do I get my security deposit back in Mississippi?",
             "Demand it — the 45-day clock only starts after termination, "
             "delivery of possession, AND your demand (Miss. Code "
             "§ 89-8-21(3)). Demand in writing at move-out with a forwarding "
             "address."),
            ("What if my Mississippi landlord doesn't return the deposit?",
             "You can recover actual damages plus up to $200 for bad-faith "
             "noncompliance with the return or itemization rules "
             "(§ 89-8-21(4))."),
            ("How much notice before my landlord can enter in Mississippi?",
             "None by statute — entry rules exist only if your lease creates "
             "them. Negotiate an entry clause before signing."),
            ("How much notice before eviction for unpaid rent in Mississippi?",
             "A 3-day notice to pay or the lease terminates (§ 89-8-13)."),
        ],
    },
    "ar": {
        "name": "Arkansas",
        "statute": "Ark. Code § 18-16 and § 18-60 (landlord-tenant and unlawful detainer)",
        "quick": [
            ("Deposit cap", "2 months (6+ units)"),
            ("Deposit return", "60 days"),
            ("Nonpayment notice", "3 days"),
            ("Habitability", "Minimal — lease rules"),
        ],
        "sections": [
            ("Read this first — Arkansas is different", [
                ("The most landlord-favorable state",
                 "Arkansas has the thinnest tenant protections in the "
                 "country, and renting here means knowing exactly what "
                 "<b>isn't</b> protected: no entry-notice statute, no "
                 "meaningful repair remedies, and until 2021 no "
                 "habitability standard at all. Your lease is nearly all "
                 "of your law — negotiate it accordingly, and get every "
                 "landlord promise in writing."),
            ]),
            ("Security deposits", [
                ("The rules — and the exemption",
                 "Deposits are capped at <b>two months' rent</b> with a "
                 "<b>60-day</b> itemized return window (Ark. Code "
                 "§§ 18-16-304, -305) — but the entire deposit statute "
                 "<b>only applies to landlords with six or more rental "
                 "units</b> (§ 18-16-303). Rent from a small landlord and "
                 "the deposit is governed purely by your lease. Either "
                 "way: written forwarding address, written demand, keep "
                 "copies."),
            ]),
            ("Repairs & habitability", [
                ("The 2021 minimum — and its limits",
                 "Since 2021, landlords must provide bare minimums — "
                 "available hot/cold water, electricity, sewer, a "
                 "non-leaking roof, and functioning HVAC where supplied "
                 "(§ 18-17-502) — but the sole statutory remedy is "
                 "<b>terminating the lease and moving out</b> after notice "
                 "and an uncured 30 days. No rent withholding, no "
                 "repair-and-deduct, no abatement. If repairs matter to "
                 "you, they must be in the lease with real teeth."),
            ]),
            ("Eviction — know both tracks", [
                ("Civil: fast and non-curable",
                 "The civil track is a <b>3-day notice to quit</b> for "
                 "nonpayment (§ 18-60-304) — and the landlord is <b>not "
                 "required to accept late rent</b> to stop it. Pay on time "
                 "or negotiate in writing immediately."),
                ("Criminal: unique to Arkansas",
                 "Arkansas still has a criminal <b>\"failure to "
                 "vacate\"</b> statute (§ 18-16-101): after a 10-day "
                 "notice for nonpayment, remaining in the unit can be "
                 "charged as a misdemeanor. It's constitutionally "
                 "controversial and unevenly enforced, but it exists — "
                 "never ignore an Arkansas eviction notice of either "
                 "kind. Month-to-month tenancies end on 30 days' notice; "
                 "lockouts without court process remain unlawful."),
            ]),
        ],
        "faqs": [
            ("How long does an Arkansas landlord have to return my deposit?",
             "60 days, itemized (Ark. Code § 18-16-305) — but the deposit "
             "statute only applies to landlords with six or more units "
             "(§ 18-16-303). With a smaller landlord, your lease governs."),
            ("Can I withhold rent for repairs in Arkansas?",
             "No — Arkansas provides no rent-withholding, repair-and-deduct, "
             "or abatement remedy. The 2021 minimum-standards law's only "
             "remedy is terminating and moving out (§ 18-17-502)."),
            ("Can I be criminally charged for staying after an eviction notice in Arkansas?",
             "Arkansas uniquely retains a criminal failure-to-vacate statute "
             "(§ 18-16-101) — after a 10-day notice, remaining can be charged "
             "as a misdemeanor. Take every notice seriously and get legal "
             "help fast."),
            ("Does paying late rent stop an Arkansas eviction?",
             "Not necessarily — under the 3-day unlawful detainer notice, the "
             "landlord isn't required to accept payment to halt the case "
             "(§ 18-60-304)."),
        ],
    },
    "ks": {
        "name": "Kansas",
        "statute": "Kansas Residential Landlord and Tenant Act (K.S.A. § 58-2540 et seq.)",
        "quick": [
            ("Deposit cap", "1 mo (1.5 furnished)"),
            ("Deposit return", "30 days max"),
            ("Wrongful withholding", "1.5x"),
            ("Move-in inventory", "Within 5 days"),
        ],
        "sections": [
            ("Security deposits", [
                ("The tiered cap",
                 "Deposits are capped at <b>one month's rent</b> "
                 "unfurnished, <b>1.5 months</b> furnished, plus up to a "
                 "<b>half month more</b> for pets (K.S.A. § 58-2550(a))."),
                ("The 5-day inventory",
                 "Within <b>5 days of move-in</b>, you and the landlord "
                 "must jointly inventory the unit's condition (§ 58-2548). "
                 "Do it thoroughly and keep your signed copy — it's the "
                 "baseline for every deduction fight."),
                ("Return & the 1.5x penalty",
                 "The itemized balance is due <b>within 14 days of "
                 "determining deductions, and never later than 30 days</b> "
                 "after the tenancy ends (§ 58-2550(b)). Wrongful "
                 "withholding makes the landlord liable for <b>1.5 times "
                 "the amount wrongfully kept</b> (§ 58-2550(c))."),
            ]),
            ("Repairs & privacy", [
                ("Habitability",
                 "Landlords must comply with codes and keep the unit fit — "
                 "plumbing, heat, hot water, electrical (§ 58-2553). "
                 "Material noncompliance gets a written <b>14-day cure / "
                 "30-day termination notice</b> (§ 58-2559); "
                 "essential-service failures support procure-and-deduct or "
                 "substitute housing (§ 58-2561)."),
                ("Entry",
                 "<b>Reasonable notice</b> and entry at reasonable hours "
                 "(§ 58-2557) — no fixed hour count, but blanket-consent "
                 "clauses can't erase the reasonableness requirement."),
            ]),
            ("Ending a lease & eviction", [
                ("Timelines",
                 "Nonpayment requires a <b>3-day notice</b> to pay before "
                 "termination (§ 58-2564(b)); paying within the window "
                 "cures it. Month-to-month tenancies end on <b>30 days' "
                 "notice</b> (§ 58-2570). Lockouts and utility shutoffs "
                 "are unlawful; only court process removes you. Retaliation "
                 "for complaints is prohibited (§ 58-2572)."),
            ]),
        ],
        "faqs": [
            ("What's the maximum security deposit in Kansas?",
             "One month's rent unfurnished, 1.5 months furnished, plus up to "
             "half a month for pets (K.S.A. § 58-2550(a))."),
            ("How long does a Kansas landlord have to return my deposit?",
             "Within 14 days of determining deductions, and never later than "
             "30 days after the tenancy ends — wrongful withholding costs the "
             "landlord 1.5x the amount kept (§ 58-2550)."),
            ("Is a move-in inspection required in Kansas?",
             "Yes — a joint inventory within 5 days of move-in "
             "(§ 58-2548). Complete it carefully and keep your copy."),
            ("How much notice before eviction for unpaid rent in Kansas?",
             "A 3-day notice to pay, curable by paying in full "
             "(§ 58-2564(b))."),
        ],
    },
    "ia": {
        "name": "Iowa",
        "statute": "Iowa Uniform Residential Landlord and Tenant Law (Iowa Code § 562A)",
        "quick": [
            ("Deposit cap", "2 months' rent"),
            ("Deposit return", "30 days"),
            ("Bad faith", "Punitive damages"),
            ("Late fee caps", "Statutory"),
        ],
        "sections": [
            ("Security deposits", [
                ("The rules",
                 "Deposits are capped at <b>two months' rent</b> (Iowa "
                 "Code § 562A.12(1)). Return with an itemized statement is "
                 "due <b>within 30 days</b> of termination and your "
                 "written forwarding address (§ 562A.12(3)) — no address, "
                 "no clock, so provide it at move-out. Bad-faith retention "
                 "exposes the landlord to <b>punitive damages up to twice "
                 "the monthly rent</b> plus actual damages "
                 "(§ 562A.12(7))."),
            ]),
            ("Money rules — Iowa's specific late-fee caps", [
                ("Hard numbers",
                 "For rent of $700/month or less: at most <b>$12 per day, "
                 "$60 per month</b>. Over $700: at most <b>$20 per day, "
                 "$100 per month</b> (§ 562A.9(4)). Anything above those "
                 "numbers is unenforceable regardless of the lease."),
            ]),
            ("Repairs & privacy", [
                ("Habitability",
                 "Landlords must comply with codes and keep the unit fit "
                 "and habitable (§ 562A.15). Material noncompliance gets a "
                 "written <b>7-day cure / 30-day termination notice</b>; "
                 "essential-service failures support procure-and-deduct, "
                 "substitute housing, or abatement (§§ 562A.21–562A.23)."),
                ("Entry",
                 "At least <b>24 hours' notice</b> and entry at reasonable "
                 "times, except emergencies (§ 562A.19). Abuse of access "
                 "supports an injunction and lease termination."),
            ]),
            ("Ending a lease & eviction", [
                ("Timelines",
                 "Nonpayment requires a <b>3-day notice</b> to pay before "
                 "termination (§ 562A.27(2)) — curable by paying in full. "
                 "Month-to-month tenancies end on <b>30 days' notice</b> "
                 "(§ 562A.34). Lockouts and utility shutoffs are unlawful "
                 "(§ 562A.26); retaliation within one year of complaints "
                 "is presumed (§ 562A.36)."),
            ]),
        ],
        "faqs": [
            ("What's the maximum security deposit in Iowa?",
             "Two months' rent (Iowa Code § 562A.12(1))."),
            ("How long does an Iowa landlord have to return my deposit?",
             "30 days after termination and your written forwarding address — "
             "bad-faith retention adds punitive damages up to twice the "
             "monthly rent (§ 562A.12)."),
            ("How big can late fees be in Iowa?",
             "Rent ≤ $700/month: max $12/day and $60/month. Over $700: max "
             "$20/day and $100/month (§ 562A.9(4)). Higher amounts are "
             "unenforceable."),
            ("How much notice before entry in Iowa?",
             "At least 24 hours, at reasonable times, except emergencies "
             "(§ 562A.19)."),
        ],
    },
    "ne": {
        "name": "Nebraska",
        "statute": "Nebraska Uniform Residential Landlord and Tenant Act (Neb. Rev. Stat. § 76-1401 et seq.)",
        "quick": [
            ("Deposit cap", "1 mo (+¼ pet)"),
            ("Deposit return", "14 days"),
            ("Entry notice", "24 hours"),
            ("Nonpayment notice", "7 days"),
        ],
        "sections": [
            ("Security deposits", [
                ("Cap and the fast clock",
                 "Deposits are capped at <b>one month's rent</b>, plus up "
                 "to <b>one-quarter month more</b> for pets (Neb. Rev. "
                 "Stat. § 76-1416(1)). Return with an itemized statement "
                 "is due <b>within 14 days</b> of demand and your "
                 "forwarding address (§ 76-1416(2)) — one of the fastest "
                 "clocks in the country, but it's demand-triggered: put "
                 "the demand and address in writing at move-out."),
                ("The penalty",
                 "Wrongful withholding entitles you to the amount due plus "
                 "<b>damages up to one month's rent and reasonable "
                 "attorney's fees</b> (§ 76-1416(3))."),
            ]),
            ("Repairs & privacy", [
                ("Habitability",
                 "Landlords must comply with codes and keep the unit fit — "
                 "plumbing, heat, water, electrical (§ 76-1419). Material "
                 "noncompliance gets a written <b>14/30-day cure notice</b> "
                 "(§ 76-1425); essential-service failures support "
                 "procure-and-deduct, substitute housing, or abatement "
                 "(§ 76-1427)."),
                ("Entry",
                 "At least <b>one day's notice</b> and entry at reasonable "
                 "times, except emergencies (§ 76-1423)."),
            ]),
            ("Ending a lease & eviction", [
                ("Timelines",
                 "Nonpayment requires a <b>7-day notice</b> to pay before "
                 "termination (§ 76-1431(2)) — curable by paying in full. "
                 "Month-to-month tenancies end on <b>30 days' notice</b> "
                 "(§ 76-1437). Lockouts and utility shutoffs are unlawful "
                 "(§ 76-1430); retaliation for complaints is prohibited "
                 "(§ 76-1439). Only court process removes you."),
            ]),
        ],
        "faqs": [
            ("What's the maximum security deposit in Nebraska?",
             "One month's rent, plus up to one-quarter month for pets "
             "(Neb. Rev. Stat. § 76-1416(1))."),
            ("How long does a Nebraska landlord have to return my deposit?",
             "14 days after your demand and forwarding address — one of the "
             "fastest windows in the country (§ 76-1416(2)). Demand in "
             "writing at move-out."),
            ("What if my Nebraska landlord wrongfully keeps the deposit?",
             "You can recover the amount due plus damages up to one month's "
             "rent and attorney's fees (§ 76-1416(3))."),
            ("How much notice before eviction for unpaid rent in Nebraska?",
             "A 7-day notice to pay, curable by paying in full "
             "(§ 76-1431(2))."),
        ],
    },
    "ct": {
        "name": "Connecticut",
        "statute": "Conn. Gen. Stat. Title 47a (esp. § 47a-21)",
        "quick": [
            ("Deposit cap", "2 mo (1 mo if 62+)"),
            ("Deposit return", "21 days"),
            ("Interest", "Required annually"),
            ("Rent grace period", "9 days"),
        ],
        "sections": [
            ("Security deposits", [
                ("The age-based cap",
                 "Deposits are capped at <b>two months' rent</b> — dropping "
                 "to <b>one month for tenants 62 or older</b>, and a tenant "
                 "who turns 62 mid-tenancy can demand the excess back "
                 "(Conn. Gen. Stat. § 47a-21(b)). The deposit remains "
                 "<b>your property</b>, held in a Connecticut escrow "
                 "account, earning <b>annual interest</b> at the Banking "
                 "Commissioner's published rate."),
                ("The new 21-day clock",
                 "Since 2023, return with an itemized statement is due "
                 "within <b>21 days</b> of termination (or 15 days after "
                 "your forwarding address, whichever is later) — most "
                 "older guides still say 30 days; Public Act 23-207 "
                 "shortened it. Wrongful withholding costs the landlord "
                 "<b>twice the amount wrongfully kept</b> "
                 "(§ 47a-21(d))."),
            ]),
            ("Money & timing rules", [
                ("The 9-day grace period",
                 "Rent isn't legally \"late\" until <b>9 days</b> after the "
                 "due date for month-to-month and longer tenancies "
                 "(§ 47a-15a) — no late fee and no eviction notice can "
                 "start before then."),
            ]),
            ("Repairs & privacy", [
                ("Habitability",
                 "Landlords must keep the unit fit and habitable per codes "
                 "(§ 47a-7). Connecticut's structured remedy is a "
                 "<b>housing-code enforcement action with rent paid into "
                 "court</b> (§ 47a-14h) — a formal alternative to risky "
                 "unilateral withholding."),
                ("Entry",
                 "<b>Reasonable notice</b> and entry at reasonable times "
                 "for repairs, inspections, and showings (§ 47a-16); "
                 "emergencies excepted. Lockouts and utility shutoffs are "
                 "illegal (§ 47a-13, 53a-214)."),
            ]),
            ("Ending a lease & eviction", [
                ("Timelines",
                 "After the grace period, eviction starts with a "
                 "<b>notice to quit at least 3 days</b> before the stated "
                 "quit date (§ 47a-23), then a summary process case — "
                 "Connecticut's court timeline gives real opportunity to "
                 "answer and raise defenses. Retaliation within 6 months "
                 "of complaints is presumed unlawful (§ 47a-20). Only a "
                 "marshal on a court order can remove you."),
            ]),
        ],
        "faqs": [
            ("How much can a Connecticut landlord charge for a deposit?",
             "Two months' rent — one month if you're 62 or older, with the "
             "right to demand the excess back when you turn 62 "
             "(Conn. Gen. Stat. § 47a-21(b))."),
            ("How long does a Connecticut landlord have to return my deposit?",
             "21 days since Public Act 23-207 (or 15 days after your "
             "forwarding address, whichever is later) — older guides saying "
             "30 days are out of date. Wrongful withholding = double "
             "damages (§ 47a-21(d))."),
            ("Am I owed interest on my deposit in Connecticut?",
             "Yes — annually, at the rate published by the Banking "
             "Commissioner, on a deposit held in Connecticut escrow "
             "(§ 47a-21(i))."),
            ("When is rent legally late in Connecticut?",
             "Not until 9 days after the due date for monthly tenancies "
             "(§ 47a-15a) — no late fees or eviction notices before then."),
        ],
    },
    "ri": {
        "name": "Rhode Island",
        "statute": "Rhode Island Residential Landlord and Tenant Act (R.I.G.L. § 34-18)",
        "quick": [
            ("Deposit cap", "1 month's rent"),
            ("Deposit return", "20 days"),
            ("Entry notice", "2 days"),
            ("Nonpayment notice", "5 days (after 15)"),
        ],
        "sections": [
            ("Security deposits", [
                ("The rules",
                 "Deposits are capped at <b>one month's rent</b> "
                 "(R.I.G.L. § 34-18-19(a)). Return with an itemized "
                 "statement is due <b>within 20 days</b> of termination, "
                 "delivery of possession, and your forwarding address — "
                 "among the fastest clocks in the country. Wrongful "
                 "withholding exposes the landlord to <b>up to twice the "
                 "amount wrongfully kept plus attorney's fees</b> "
                 "(§ 34-18-19(c))."),
            ]),
            ("Repairs & privacy", [
                ("Habitability",
                 "Landlords must comply with codes and keep the unit fit "
                 "and habitable (§ 34-18-22). Material noncompliance gets "
                 "a written <b>20-day cure / 30-day termination "
                 "notice</b>; essential-service failures support "
                 "procure-and-deduct, substitute housing, or abatement "
                 "(§§ 34-18-28, 34-18-31)."),
                ("Entry",
                 "At least <b>2 days' notice</b> and entry at reasonable "
                 "times, except emergencies (§ 34-18-26)."),
            ]),
            ("Ending a lease & eviction", [
                ("Rhode Island's built-in cushion",
                 "For nonpayment, the landlord must wait until rent is "
                 "<b>15 days late</b>, then serve a <b>5-day demand "
                 "notice</b> before filing (§ 34-18-35) — paying "
                 "everything owed within the 5 days cures it, and "
                 "first-time cases can even be cured after filing. "
                 "Month-to-month tenancies end on <b>30 days' notice</b> "
                 "(§ 34-18-37). Lockouts and shutoffs are illegal "
                 "(§ 34-18-44); retaliation is presumed for landlord "
                 "action within 6 months of complaints (§ 34-18-46)."),
            ]),
        ],
        "faqs": [
            ("What's the maximum security deposit in Rhode Island?",
             "One month's rent (R.I.G.L. § 34-18-19(a))."),
            ("How long does a Rhode Island landlord have to return my deposit?",
             "20 days after termination, possession, and your forwarding "
             "address — wrongful withholding risks double plus attorney's "
             "fees (§ 34-18-19)."),
            ("How much notice before eviction for unpaid rent in Rhode Island?",
             "Rent must be 15 days late first, then a 5-day written demand — "
             "curable by paying in full (§ 34-18-35)."),
            ("How much notice before entry in Rhode Island?",
             "At least 2 days, at reasonable times, except emergencies "
             "(§ 34-18-26)."),
        ],
    },
    "nh": {
        "name": "New Hampshire",
        "statute": "N.H. RSA 540-A (deposits & prohibited practices) and RSA 540 (evictions)",
        "quick": [
            ("Deposit cap", "1 month or $100"),
            ("Deposit return", "30 days"),
            ("Violations", "Double recovery"),
            ("Eviction", "Statutory grounds"),
        ],
        "sections": [
            ("Security deposits", [
                ("The rules — and the exemption",
                 "Deposits are capped at the greater of <b>one month's "
                 "rent or $100</b> (RSA 540-A:6), must sit in a New "
                 "Hampshire bank (or be bonded) with the location "
                 "disclosed, and require a <b>written receipt</b> unless "
                 "paid by check. Interest is owed on deposits held a year "
                 "or more, payable on request. <b>Watch the exemption:</b> "
                 "these rules don't apply to a single-family house whose "
                 "owner rents no other property, or units in "
                 "owner-occupied buildings of 5 or fewer units (unless "
                 "you're 60+) (RSA 540-A:5)."),
                ("Return & the double remedy",
                 "Return with an itemized accounting is due <b>within 30 "
                 "days</b> of move-out (RSA 540-A:7). Violations of the "
                 "deposit rules entitle you to <b>double the amount "
                 "owed</b> (RSA 540-A:8)."),
            ]),
            ("Repairs & privacy", [
                ("Habitability",
                 "RSA 48-A:14's minimum standards (heat, water, no "
                 "serious code violations, no pest infestations) back an "
                 "implied warranty; documented violations support rent "
                 "withholding as a defense in eviction (RSA 540:13-d) if "
                 "you followed notice requirements. Report problems in "
                 "writing and to code enforcement."),
                ("Entry & prohibited practices",
                 "Entry requires <b>adequate notice under the "
                 "circumstances</b> (RSA 540-A:3) — no fixed hour count. "
                 "The same statute flatly bans lockouts, utility "
                 "shutoffs, and taking tenant property, with penalties up "
                 "to $1,000 per day for willful violations."),
            ]),
            ("Ending a lease & eviction", [
                ("Grounds-based eviction",
                 "New Hampshire evictions must state a <b>statutory "
                 "ground</b> (RSA 540:2): nonpayment, damage, behavior "
                 "affecting others' safety, or \"other good cause\" "
                 "(including legitimate business reasons). Nonpayment gets "
                 "a <b>7-day eviction notice</b> — and you can defeat it "
                 "by paying all rent due <b>plus $15</b> before the "
                 "notice expires (RSA 540:9) — other grounds get 30 days. "
                 "Only court process removes you."),
            ]),
        ],
        "faqs": [
            ("What's the maximum security deposit in New Hampshire?",
             "The greater of one month's rent or $100 (RSA 540-A:6) — though "
             "single-family homes with owner-landlords who rent nothing else, "
             "and small owner-occupied buildings, are exempt (RSA 540-A:5)."),
            ("How long does an NH landlord have to return my deposit?",
             "30 days, itemized (RSA 540-A:7). Violations = double the amount "
             "owed (RSA 540-A:8)."),
            ("Can I stop a New Hampshire nonpayment eviction by paying?",
             "Yes — pay all rent owed plus $15 in costs before the 7-day "
             "notice expires and the eviction is defeated (RSA 540:9)."),
            ("Can my NH landlord evict me without a reason?",
             "No — evictions must state a statutory ground under RSA 540:2, "
             "though \"other good cause\" includes legitimate business "
             "reasons."),
        ],
    },
    "vt": {
        "name": "Vermont",
        "statute": "9 V.S.A. Chapter 137 (Residential Rental Agreements)",
        "quick": [
            ("Deposit cap", "None (state)"),
            ("Deposit return", "14 days"),
            ("Entry notice", "48 hours"),
            ("No-cause notice", "60–90 days"),
        ],
        "sections": [
            ("Security deposits", [
                ("The 14-day hammer",
                 "No statewide cap, but Vermont's return clock is brutal "
                 "for landlords: the itemized statement and balance are "
                 "due <b>within 14 days</b> of when you vacate (9 V.S.A. "
                 "§ 4461(c)). Miss it and the landlord <b>forfeits the "
                 "right to withhold anything</b>; willful violations cost "
                 "<b>double the amount wrongfully withheld plus "
                 "attorney's fees</b> (§ 4461(e)–(f)). Burlington and a "
                 "few towns layer their own deposit ordinances on top."),
            ]),
            ("Repairs & privacy", [
                ("Habitability & the minor-repair right",
                 "Vermont's warranty of habitability is unwaivable "
                 "(§ 4457). For minor defects, after <b>30 days'</b> "
                 "written notice you may make the repair and <b>deduct up "
                 "to half a month's rent</b> (§ 4459); for serious "
                 "uncured problems, remedies include withholding when the "
                 "landlord had actual notice, damages, and termination "
                 "(§ 4458)."),
                ("Entry",
                 "At least <b>48 hours' notice</b>, with entry only "
                 "between <b>9 a.m. and 9 p.m.</b> (§ 4460) — one of the "
                 "most specific entry statutes anywhere."),
            ]),
            ("Ending a lease & eviction", [
                ("Timelines",
                 "Nonpayment requires a <b>14-day notice</b> "
                 "(§ 4467(a)) — paying everything owed <b>before the "
                 "rental period ends</b> voids it (and Vermont courts "
                 "allow cure later in many cases). No-cause terminations "
                 "of month-to-month tenancies require <b>60 days' "
                 "notice</b> — <b>90 days</b> if you've rented more than "
                 "two years (§ 4467(c), (e)). Burlington additionally "
                 "requires just cause by charter. Lockouts and shutoffs "
                 "are illegal (§ 4463); only court process removes you."),
            ]),
        ],
        "faqs": [
            ("How long does a Vermont landlord have to return my deposit?",
             "14 days from when you vacate — missing it forfeits the right "
             "to withhold anything, and willful violations cost double plus "
             "attorney's fees (9 V.S.A. § 4461)."),
            ("How much notice before my landlord can enter in Vermont?",
             "48 hours, and only between 9 a.m. and 9 p.m. (§ 4460)."),
            ("Can I repair and deduct in Vermont?",
             "Yes — for minor defects, after 30 days' written notice, up to "
             "half a month's rent (§ 4459)."),
            ("How much notice for a no-cause termination in Vermont?",
             "60 days for month-to-month tenancies — 90 days if you've "
             "rented more than two years (§ 4467(c)). Burlington requires "
             "just cause on top."),
        ],
    },
    "me": {
        "name": "Maine",
        "statute": "14 M.R.S. §§ 6001–6046 (esp. §§ 6031–6038)",
        "quick": [
            ("Deposit cap", "2 months' rent"),
            ("Deposit return", "30 days (21 at-will)"),
            ("Wrongful retention", "2x + fees"),
            ("Entry notice", "24 hours"),
        ],
        "sections": [
            ("Security deposits", [
                ("The rules",
                 "Deposits are capped at <b>two months' rent</b> "
                 "(14 M.R.S. § 6032) and must be held separate from the "
                 "landlord's funds. Return with an itemized statement is "
                 "due within <b>30 days</b> under a written lease — or "
                 "<b>21 days</b> for a tenancy at will (§ 6033). Wrongful "
                 "retention exposes the landlord to <b>double the amount "
                 "withheld plus attorney's fees</b> (§ 6034), and "
                 "missing the deadline forfeits the right to withhold at "
                 "all."),
            ]),
            ("Repairs & privacy", [
                ("Habitability",
                 "Maine's implied warranty of fitness for human "
                 "habitation is unwaivable (§ 6021): heat, water, and "
                 "freedom from dangerous conditions. Remedies after "
                 "written notice include rent withholding for serious "
                 "unsafe conditions (with rules), repair-and-deduct up "
                 "to $500 or half a month's rent for qualifying defects "
                 "(§ 6026), and code-enforcement leverage."),
                ("Entry",
                 "At least <b>24 hours' notice</b> and entry at "
                 "reasonable times, except emergencies (§ 6025)."),
            ]),
            ("Ending a lease & eviction", [
                ("Timelines",
                 "When rent is 7+ days late, the landlord may serve a "
                 "<b>7-day notice</b> — paying everything owed before the "
                 "notice expires voids it (§ 6002). Tenancies at will end "
                 "on <b>30 days' written notice</b>, and rent increases "
                 "for at-will tenants require <b>45 days' notice</b> "
                 "(§ 6015). Local layer: <b>Portland has rent control "
                 "and just-cause eviction</b> by ordinance — South "
                 "Portland too — so check your city. Lockouts and "
                 "shutoffs are illegal (§ 6014); only court process "
                 "removes you."),
            ]),
        ],
        "faqs": [
            ("What's the maximum security deposit in Maine?",
             "Two months' rent (14 M.R.S. § 6032)."),
            ("How long does a Maine landlord have to return my deposit?",
             "30 days under a written lease, 21 days for a tenancy at will "
             "(§ 6033). Wrongful retention = double plus attorney's fees "
             "(§ 6034)."),
            ("Can I stop a Maine nonpayment eviction by paying?",
             "Yes — pay everything owed before the 7-day notice expires and "
             "it's void (§ 6002)."),
            ("Is there rent control in Maine?",
             "Statewide no — but Portland and South Portland have local "
             "rent control and just-cause eviction ordinances. Check your "
             "city."),
        ],
    },
    "id": {
        "name": "Idaho",
        "statute": "Idaho Code § 6-320, § 6-321, § 55-208",
        "quick": [
            ("Deposit cap", "None"),
            ("Deposit return", "21 days (30 by lease)"),
            ("Nonpayment notice", "3 days"),
            ("Entry notice", "None (lease)"),
        ],
        "sections": [
            ("Security deposits", [
                ("The rules",
                 "No cap on amounts. Return with an itemized statement is "
                 "due <b>within 21 days</b> — extendable to at most <b>30 "
                 "days</b> only if your lease says so (Idaho Code "
                 "§ 6-321). Wrongful retention supports recovery of the "
                 "full amount due plus fees, and courts may award <b>up to "
                 "three times</b> the wrongfully withheld amount where the "
                 "refusal was arbitrary, capricious, or in bad faith."),
            ]),
            ("Repairs & privacy", [
                ("The 3-day letter system",
                 "Idaho's repair remedy is procedural: for habitability "
                 "failures (water, heat, structural, code hazards), serve "
                 "the landlord a written notice listing the failures; if "
                 "not fixed within <b>3 days</b>, you may sue in Idaho's "
                 "expedited landlord-tenant action for damages and repairs "
                 "(§ 6-320). No statutory repair-and-deduct or "
                 "withholding — the letter-then-court path is the lawful "
                 "one."),
                ("Entry",
                 "No entry statute — your lease governs. Negotiate a "
                 "notice clause before signing."),
            ]),
            ("Ending a lease & eviction", [
                ("Timelines",
                 "Nonpayment gets a <b>3-day notice</b> to pay or vacate "
                 "(§ 6-303(2)); paying within the window cures. "
                 "Month-to-month tenancies end on <b>one month's "
                 "notice</b> (§ 55-208), with 15 days' notice required "
                 "before a rent increase or new terms on a month-to-month. "
                 "Lockouts are unlawful; only court process removes you."),
            ]),
        ],
        "faqs": [
            ("How long does an Idaho landlord have to return my deposit?",
             "21 days — or up to 30 only if your lease says so (Idaho Code "
             "§ 6-321). Arbitrary or bad-faith retention can support up to "
             "treble damages."),
            ("Can I withhold rent for repairs in Idaho?",
             "No — Idaho's path is a written 3-day notice listing the "
             "failures, then an expedited court action (§ 6-320)."),
            ("How much notice before entry in Idaho?",
             "None by statute — your lease governs. Get a notice clause in "
             "writing."),
            ("How much notice before eviction for unpaid rent in Idaho?",
             "A 3-day notice to pay or vacate, curable by paying in full "
             "(§ 6-303(2))."),
        ],
    },
    "mt": {
        "name": "Montana",
        "statute": "Mont. Code § 70-24 (URLTA) and § 70-25 (deposits)",
        "quick": [
            ("Deposit cap", "None"),
            ("Deposit return", "10/30 days"),
            ("Entry notice", "24 hours"),
            ("Nonpayment notice", "3 days"),
        ],
        "sections": [
            ("Security deposits", [
                ("The split clock",
                 "No cap on amounts. If there are <b>no deductions</b>, "
                 "your deposit is due back within <b>10 days</b> — one of "
                 "the fastest windows anywhere. With deductions, the "
                 "itemized statement and balance are due within <b>30 "
                 "days</b> (Mont. Code § 70-25-202)."),
                ("The cleaning-notice right",
                 "Montana's distinctive rule: a landlord can't deduct for "
                 "cleaning unless you first got <b>written notice of the "
                 "cleaning condition and 24 hours to clean it "
                 "yourself</b> (§ 70-25-201(3)). No notice, no cleaning "
                 "deduction — full stop."),
            ]),
            ("Repairs & privacy", [
                ("Habitability",
                 "Landlords must maintain a fit, code-compliant unit "
                 "(§ 70-24-303). Material noncompliance gets a written "
                 "<b>14/30-day cure notice</b>; essential-service "
                 "failures support procure-and-deduct, substitute "
                 "housing, or abatement (§§ 70-24-406, -408)."),
                ("Entry",
                 "At least <b>24 hours' notice</b> and entry at "
                 "reasonable times (§ 70-24-312)."),
            ]),
            ("Ending a lease & eviction", [
                ("Timelines",
                 "Nonpayment gets a <b>3-day notice</b> to pay "
                 "(§ 70-24-422(2)) — curable in full. Month-to-month "
                 "tenancies end on <b>30 days' notice</b> (§ 70-24-441). "
                 "Lockouts and shutoffs are unlawful (§ 70-24-411); "
                 "retaliation within 6 months of complaints is presumed "
                 "(§ 70-24-431)."),
            ]),
        ],
        "faqs": [
            ("How long does a Montana landlord have to return my deposit?",
             "10 days if there are no deductions; 30 days with an itemized "
             "statement if there are (Mont. Code § 70-25-202)."),
            ("Can my Montana landlord deduct for cleaning?",
             "Only if you first received written notice of the cleaning "
             "needed and 24 hours to do it yourself (§ 70-25-201(3))."),
            ("How much notice before entry in Montana?",
             "At least 24 hours, at reasonable times (§ 70-24-312)."),
            ("How much notice before eviction for unpaid rent in Montana?",
             "A 3-day notice, curable by paying in full (§ 70-24-422(2))."),
        ],
    },
    "wy": {
        "name": "Wyoming",
        "statute": "Wyo. Stat. § 1-21-1201 et seq.",
        "quick": [
            ("Deposit cap", "None"),
            ("Deposit return", "30 days (+30 damage)"),
            ("Nonpayment notice", "3 days"),
            ("Entry notice", "None (lease)"),
        ],
        "sections": [
            ("Security deposits", [
                ("The rules",
                 "No cap on amounts. The balance plus a written "
                 "itemization is due <b>within 30 days</b> of termination "
                 "— or 15 days after your new mailing address, whichever "
                 "is later — with <b>an extra 30 days allowed only for "
                 "deductions due to damage</b> (Wyo. Stat. § 1-21-1208). "
                 "The lease must tell you if any portion is "
                 "non-refundable; unlabeled portions are refundable. "
                 "Noncompliance forfeits the deductions and supports "
                 "recovery of the full deposit plus damages."),
            ]),
            ("Repairs & habitability", [
                ("A thin regime — paper everything",
                 "Wyoming requires a safe and sanitary unit — plumbing, "
                 "heat, hot water, electrical (§ 1-21-1202) — but "
                 "enforcement is narrow: written notice, a reasonable "
                 "time, then either court action or terminating and "
                 "moving out (§ 1-21-1206). <b>No rent withholding, no "
                 "repair-and-deduct.</b> There's also no entry-notice "
                 "statute — like your repairs, your privacy rights are "
                 "mostly what your lease says. Negotiate before "
                 "signing."),
            ]),
            ("Ending a lease & eviction", [
                ("Timelines",
                 "Nonpayment or holdover gets a <b>3-day notice to "
                 "quit</b> (§ 1-21-1002 et seq.) before a forcible entry "
                 "and detainer case — Wyoming's process is among the "
                 "fastest, so respond immediately. Month-to-month "
                 "tenancies customarily end on notice equal to the rental "
                 "period. Lockouts without court process remain "
                 "unlawful."),
            ]),
        ],
        "faqs": [
            ("How long does a Wyoming landlord have to return my deposit?",
             "30 days after termination or 15 days after your new mailing "
             "address, whichever is later — plus up to 30 more days only "
             "for damage deductions (Wyo. Stat. § 1-21-1208)."),
            ("Can any of my Wyoming deposit be non-refundable?",
             "Only if the lease clearly says so — unlabeled portions remain "
             "refundable (§ 1-21-1207)."),
            ("Can I withhold rent for repairs in Wyoming?",
             "No — Wyoming's remedies are written notice then court action "
             "or moving out (§ 1-21-1206). No withholding, no "
             "repair-and-deduct."),
            ("How much notice before eviction in Wyoming?",
             "A 3-day notice to quit, then one of the fastest court "
             "processes in the country — never ignore it (§ 1-21-1002)."),
        ],
    },
    "nd": {
        "name": "North Dakota",
        "statute": "N.D. Cent. Code § 47-16-07.1 et seq.",
        "quick": [
            ("Deposit cap", "1 month's rent"),
            ("Deposit return", "30 days"),
            ("Interest", "If held 9+ months"),
            ("Nonpayment notice", "3 days"),
        ],
        "sections": [
            ("Security deposits", [
                ("Cap — with two exceptions",
                 "Deposits are capped at <b>one month's rent</b>, with two "
                 "statutory exceptions: a pet deposit can raise the total "
                 "to <b>the greater of $2,500 or two months' rent</b>, "
                 "and tenants with felony convictions or prior "
                 "lease-violation judgments can be charged up to two "
                 "months (N.D.C.C. § 47-16-07.1). Deposits must sit in a "
                 "<b>federally insured interest-bearing account</b>, with "
                 "the interest yours if the tenancy lasts <b>9 months or "
                 "more</b>."),
                ("Return",
                 "The itemized balance plus accrued interest is due "
                 "<b>within 30 days</b> of termination and your "
                 "forwarding address. Bad-faith retention supports "
                 "recovery of the amount due plus up to <b>treble "
                 "damages</b>."),
            ]),
            ("Repairs & privacy", [
                ("Habitability",
                 "Landlords must keep the unit fit and habitable and "
                 "comply with codes (§ 47-16-13.1). Remedies after "
                 "written notice include repair-and-deduct for qualifying "
                 "essential problems up to statutory limits and lease "
                 "termination for uncured material failures "
                 "(§ 47-16-13.2)."),
                ("Entry",
                 "<b>Reasonable notice</b> and entry at reasonable times "
                 "(§ 47-16-07.3); emergencies excepted."),
            ]),
            ("Ending a lease & eviction", [
                ("Timelines",
                 "Eviction requires a written <b>3-day notice of "
                 "intention to evict</b> (§ 47-32-01) before the summary "
                 "eviction case — North Dakota's court timeline is fast "
                 "(hearings within about two weeks), so act on any notice "
                 "immediately. Month-to-month tenancies end on <b>30 "
                 "days' notice</b> before the end of a rental period "
                 "(§ 47-16-15). Lockouts are unlawful; only court process "
                 "removes you."),
            ]),
        ],
        "faqs": [
            ("What's the maximum security deposit in North Dakota?",
             "One month's rent — except pets can raise it to the greater of "
             "$2,500 or two months, and certain conviction/judgment "
             "histories allow two months (N.D.C.C. § 47-16-07.1)."),
            ("Am I owed interest on my North Dakota deposit?",
             "Yes, if your tenancy lasts 9 months or more — the deposit "
             "must sit in a federally insured interest-bearing account "
             "(§ 47-16-07.1)."),
            ("How long does a North Dakota landlord have to return my deposit?",
             "30 days after termination and your forwarding address, "
             "itemized, with accrued interest — bad faith supports up to "
             "treble damages."),
            ("How much notice before eviction in North Dakota?",
             "A 3-day notice of intention to evict, followed by one of the "
             "fastest summary processes anywhere (§ 47-32-01)."),
        ],
    },
    "sd": {
        "name": "South Dakota",
        "statute": "S.D. Codified Laws § 43-32-6.1, § 43-32-24",
        "quick": [
            ("Deposit cap", "1 month's rent"),
            ("Deposit return", "2 weeks"),
            ("Itemized accounting", "45 days on request"),
            ("Nonpayment notice", "3 days"),
        ],
        "sections": [
            ("Security deposits", [
                ("The two-step return",
                 "Deposits are capped at <b>one month's rent</b> absent "
                 "special written conditions (S.D.C.L. § 43-32-6.1). The "
                 "landlord must return the deposit (or the balance with "
                 "reasons for any withholding) within <b>two weeks</b> of "
                 "termination — then, if you request it in writing, a "
                 "full <b>itemized accounting within 45 days</b> "
                 "(§ 43-32-24). Bad-faith retention forfeits the "
                 "landlord's claims and adds <b>punitive damages up to "
                 "$200</b>."),
            ]),
            ("Repairs & privacy", [
                ("Habitability",
                 "Landlords must keep the unit fit for its intended use "
                 "and in reasonable repair (§ 43-32-8). After written "
                 "notice and a reasonable time, South Dakota allows "
                 "<b>repair-and-deduct</b> for qualifying problems "
                 "(§ 43-32-9) or lease termination for material "
                 "failures."),
                ("Entry",
                 "At least <b>24 hours' notice</b> and entry at "
                 "reasonable times for non-emergencies (§ 43-32-32)."),
            ]),
            ("Ending a lease & eviction", [
                ("Timelines",
                 "Nonpayment gets a <b>3-day notice</b> to quit before a "
                 "forcible entry and detainer case (§ 21-16-1(4), "
                 "21-16-2) — South Dakota's 3-day notice is <b>not "
                 "statutorily curable</b>, though many landlords accept "
                 "payment. Month-to-month tenancies end on <b>one "
                 "month's notice</b> (§ 43-32-13); the landlord must "
                 "give 30 days before raising rent or changing terms. "
                 "Lockouts are unlawful; only court process removes "
                 "you."),
            ]),
        ],
        "faqs": [
            ("What's the maximum security deposit in South Dakota?",
             "One month's rent, absent special conditions agreed in writing "
             "(S.D.C.L. § 43-32-6.1)."),
            ("How long does a South Dakota landlord have to return my deposit?",
             "Two weeks, with reasons for any withholding — and a full "
             "itemized accounting within 45 days if you request it in "
             "writing (§ 43-32-24). Bad faith adds punitive damages up to "
             "$200."),
            ("How much notice before entry in South Dakota?",
             "At least 24 hours for non-emergencies (§ 43-32-32)."),
            ("Does paying rent stop a South Dakota 3-day notice?",
             "Not automatically — the notice isn't statutorily curable, "
             "though many landlords accept payment. Treat it as urgent "
             "(§ 21-16-2)."),
        ],
    },
    "de": {
        "name": "Delaware",
        "statute": "Delaware Residential Landlord-Tenant Code (25 Del. C. § 5101 et seq.)",
        "quick": [
            ("Deposit cap", "1 month (1yr+ lease)"),
            ("Deposit return", "20 days"),
            ("Late return", "Double"),
            ("Late fee cap", "5%"),
        ],
        "sections": [
            ("Security deposits", [
                ("The rules",
                 "For leases of a year or more, deposits are capped at "
                 "<b>one month's rent</b> (a separate pet deposit up to "
                 "one month is allowed); shorter tenancies aren't capped "
                 "(25 Del. C. § 5514(a)). The deposit must sit in a "
                 "disclosed federally insured escrow account. Return with "
                 "an itemized statement is due <b>within 20 days</b> of "
                 "termination — failure to return or itemize on time "
                 "costs the landlord <b>double the wrongfully withheld "
                 "amount</b> (§ 5514(g))."),
            ]),
            ("Money rules", [
                ("Late fees & the receiving-place rule",
                 "Late fees are capped at <b>5% of the monthly rent</b> "
                 "and can't be charged until rent is <b>5 days late</b> — "
                 "and if the landlord has no rent-receiving office in the "
                 "county, you get <b>3 extra days</b> (§ 5501(d))."),
            ]),
            ("Repairs & privacy", [
                ("Habitability",
                 "The Code requires a fit, code-compliant unit "
                 "(§ 5305). After written notice, remedies include "
                 "<b>repair-and-deduct</b> for qualifying defects (capped "
                 "per statute), rent abatement for essential-service "
                 "failures, and termination (§§ 5306–5308)."),
                ("Entry",
                 "At least <b>48 hours' notice</b>, entry between "
                 "<b>8 a.m. and 9 p.m.</b> (§ 5509) — among the most "
                 "specific entry rules in the country."),
            ]),
            ("Ending a lease & eviction", [
                ("Timelines",
                 "Nonpayment requires a <b>5-day written demand</b> "
                 "before filing (§ 5502) — paying in full within the "
                 "window ends it. Terminating a month-to-month or "
                 "declining renewal takes <b>60 days' notice</b> "
                 "(§§ 5106–5107). Lockouts and shutoffs are unlawful "
                 "(§ 5313); cases run through Justice of the Peace "
                 "Court."),
            ]),
        ],
        "faqs": [
            ("What's the maximum security deposit in Delaware?",
             "One month's rent for leases of a year or more (plus an "
             "optional pet deposit up to one month); shorter tenancies "
             "aren't capped (25 Del. C. § 5514(a))."),
            ("How long does a Delaware landlord have to return my deposit?",
             "20 days, itemized — late return or itemization costs the "
             "landlord double the wrongfully withheld amount "
             "(§ 5514(g))."),
            ("How big can late fees be in Delaware?",
             "5% of the monthly rent, only after rent is 5 days late — plus "
             "3 extra grace days if the landlord has no rent-receiving "
             "office in your county (§ 5501(d))."),
            ("How much notice before entry in Delaware?",
             "48 hours, and only between 8 a.m. and 9 p.m. (§ 5509)."),
        ],
    },
    "wv": {
        "name": "West Virginia",
        "statute": "W. Va. Code § 37-6A (deposits) and § 37-6 (landlord-tenant)",
        "quick": [
            ("Deposit cap", "None"),
            ("Deposit return", "60 days"),
            ("Nonpayment notice", "None required"),
            ("Entry notice", "None (lease)"),
        ],
        "sections": [
            ("Security deposits", [
                ("The long clock",
                 "No cap on amounts. Return with an itemized statement is "
                 "due within <b>60 days</b> of the tenancy ending — or 45 "
                 "days after a new tenant moves in, whichever is "
                 "shorter — with one extension: <b>15 extra days</b> when "
                 "damage repairs reasonably exceed the window, with "
                 "written notice (W. Va. Code § 37-6A-2). Failure "
                 "forfeits the deductions, and bad-faith withholding "
                 "supports the deposit plus additional damages under "
                 "§ 37-6A-5."),
            ]),
            ("Repairs & privacy", [
                ("Habitability",
                 "Landlords must deliver and maintain a fit and habitable "
                 "unit per the warranty in § 37-6-30 — plumbing, heat, "
                 "water, structural safety. Enforcement is written "
                 "notice, then court action for damages or an order; "
                 "West Virginia has <b>no statutory repair-and-deduct or "
                 "withholding</b>, so stay on the paper trail."),
                ("Entry",
                 "No entry-notice statute — your lease governs. Negotiate "
                 "a notice clause."),
            ]),
            ("Ending a lease & eviction", [
                ("No-notice filings — take every summons seriously",
                 "West Virginia allows a landlord to file for eviction "
                 "<b>immediately when rent is unpaid or the lease is "
                 "breached — no advance notice required</b> (§ 55-3A-1). "
                 "The court summons may be your first warning, with "
                 "hearings set quickly. Never ignore one; appear and "
                 "raise defenses. Month-to-month tenancies end on <b>one "
                 "full rental period's notice</b> (§ 37-6-5). Lockouts "
                 "without court process remain unlawful."),
            ]),
        ],
        "faqs": [
            ("How long does a West Virginia landlord have to return my deposit?",
             "60 days after the tenancy ends (or 45 days after a new tenant "
             "moves in, if shorter), itemized — with one 15-day extension "
             "for repairs exceeding the window, on written notice "
             "(W. Va. Code § 37-6A-2)."),
            ("How much notice before eviction in West Virginia?",
             "None is required — a landlord may file immediately on "
             "nonpayment or breach (§ 55-3A-1). The summons may be your "
             "first warning; respond immediately."),
            ("Can I withhold rent for repairs in West Virginia?",
             "No — WV has no statutory withholding or repair-and-deduct. "
             "Use written notice and court action under the § 37-6-30 "
             "warranty."),
            ("How much notice before entry in West Virginia?",
             "None by statute — your lease governs. Get a notice clause in "
             "writing."),
        ],
    },
    "hi": {
        "name": "Hawaii",
        "statute": "Hawaii Residential Landlord-Tenant Code (HRS Chapter 521)",
        "quick": [
            ("Deposit cap", "1 mo (+1 mo pet)"),
            ("Deposit return", "14 days"),
            ("Entry notice", "2 days"),
            ("M2M notice", "45/28 days"),
        ],
        "sections": [
            ("Security deposits", [
                ("The rules",
                 "Deposits are capped at <b>one month's rent</b>, with a "
                 "separate <b>pet deposit up to one more month</b> "
                 "allowed (not for service animals) (HRS § 521-44). "
                 "Return with a written itemization — including copies of "
                 "invoices for repairs — is due <b>within 14 days</b> of "
                 "termination. Missing the 14 days <b>forfeits the "
                 "landlord's right to withhold anything</b>, and "
                 "bad-faith retention exposes them to the deposit plus "
                 "damages."),
            ]),
            ("Repairs & privacy", [
                ("Habitability",
                 "Landlords must comply with codes and keep the unit "
                 "habitable (§ 521-42). After written notice, remedies "
                 "for qualifying defects include <b>repair-and-deduct up "
                 "to $500</b> (§ 521-64), rent abatement for major "
                 "failures, and termination for uncured material "
                 "problems."),
                ("Entry",
                 "At least <b>2 days' notice</b> and entry at reasonable "
                 "times (§ 521-53); emergencies excepted."),
            ]),
            ("Ending a lease & eviction", [
                ("The asymmetric notice rule",
                 "Hawaii's month-to-month notice is asymmetric in your "
                 "favor: the landlord must give <b>45 days</b>; you only "
                 "owe <b>28</b> (§ 521-71). For nonpayment, the landlord "
                 "issues a written demand and may proceed if rent isn't "
                 "paid within <b>5 business days</b> (§ 521-68) — paying "
                 "in full within the window cures. Lockouts and shutoffs "
                 "are unlawful (§ 521-63); summary possession runs "
                 "through District Court."),
            ]),
        ],
        "faqs": [
            ("What's the maximum security deposit in Hawaii?",
             "One month's rent, plus a separate pet deposit of up to one "
             "more month — not chargeable for service animals "
             "(HRS § 521-44)."),
            ("How long does a Hawaii landlord have to return my deposit?",
             "14 days, with a written itemization including repair "
             "invoices — missing it forfeits the right to withhold "
             "anything (§ 521-44)."),
            ("How much notice to end a month-to-month tenancy in Hawaii?",
             "45 days from the landlord; only 28 from you (§ 521-71)."),
            ("How much notice before eviction for unpaid rent in Hawaii?",
             "A written demand with 5 business days to pay — curable in "
             "full within the window (§ 521-68)."),
        ],
    },
    "ak": {
        "name": "Alaska",
        "statute": "Alaska Uniform Residential Landlord and Tenant Act (AS 34.03)",
        "quick": [
            ("Deposit cap", "2 months' rent"),
            ("Deposit return", "14/30 days"),
            ("Entry notice", "24 hours"),
            ("Nonpayment notice", "7 days"),
        ],
        "sections": [
            ("Security deposits", [
                ("Cap and the notice-dependent clock",
                 "Deposits are capped at <b>two months' rent</b> — unless "
                 "monthly rent exceeds $2,000, where no cap applies "
                 "(AS 34.03.070(a)). The return clock depends on you: "
                 "<b>14 days</b> if you gave proper notice before "
                 "leaving, <b>30 days</b> if you didn't or if damage "
                 "deductions apply (AS 34.03.070(g)). Give proper notice "
                 "and a forwarding address; wrongful withholding supports "
                 "recovery of <b>up to twice the amount withheld</b>."),
            ]),
            ("Repairs & privacy", [
                ("Habitability",
                 "Landlords must maintain a fit unit — waterproofing, "
                 "plumbing, heat, safe electrical (AS 34.03.100). "
                 "Material noncompliance gets a written <b>10/20-day cure "
                 "notice</b>; essential-service failures support "
                 "procure-and-deduct, substitute housing, or abatement "
                 "(AS 34.03.160, .180)."),
                ("Entry",
                 "At least <b>24 hours' notice</b> and entry at "
                 "reasonable times (AS 34.03.140)."),
            ]),
            ("Ending a lease & eviction", [
                ("Timelines",
                 "Nonpayment gets a <b>7-day notice to quit</b> "
                 "(AS 34.03.220(b)) — paying everything owed within the "
                 "window cures it. Month-to-month tenancies end on <b>30 "
                 "days' notice</b> (AS 34.03.290(b)). Lockouts and "
                 "shutoffs are unlawful (AS 34.03.210); only court "
                 "process (forcible entry and detainer) removes you, and "
                 "retaliation for complaints is prohibited "
                 "(AS 34.03.310)."),
            ]),
        ],
        "faqs": [
            ("What's the maximum security deposit in Alaska?",
             "Two months' rent — unless the monthly rent exceeds $2,000, "
             "where no cap applies (AS 34.03.070(a))."),
            ("How long does an Alaska landlord have to return my deposit?",
             "14 days if you gave proper notice before leaving; 30 days "
             "otherwise or when damage deductions apply (AS 34.03.070(g)). "
             "Wrongful withholding = up to double."),
            ("How much notice before entry in Alaska?",
             "At least 24 hours, at reasonable times (AS 34.03.140)."),
            ("How much notice before eviction for unpaid rent in Alaska?",
             "A 7-day notice to quit, curable by paying in full "
             "(AS 34.03.220(b))."),
        ],
    },
}


def render_state(key, data):
    st_name = data["name"]
    canon = f"{SITE_URL}/guides/tenant-rights/{key}/"
    title = f"{st_name} Tenant Rights ({LAST_REVIEWED.split()[-1]}) — Security Deposits, Repairs, Eviction | LeaseReputation"
    desc = (f"{st_name} renter rights, plainly explained with statute citations: "
            f"security deposit limits and deadlines, repair rights, entry notice, "
            f"and eviction timelines under the {data['statute']}.")

    stats = "".join(
        f'<span class="statchip"><b>{esc(v)}</b>&nbsp;{esc(k)}</span>'
        for k, v in data["quick"])

    body = ""
    for section_title, items in data["sections"]:
        cards = "".join(
            f"<h3>{esc(h)}</h3><p>{t}</p>" for h, t in items)
        body += f'<div class="card"><h2>{esc(section_title)}</h2>{cards}</div>'

    # Review CTA — the page's actual job.
    body += (
        '<div class="cta-band"><h2>Lived it? The next renter needs to know.</h2>'
        '<p>Statutes only help renters who know their rights before they sign. '
        'Your verified review of your ' + esc(st_name) + ' community — the '
        'deposit you did or didn\'t get back, the repairs that did or didn\'t '
        'happen — is what actually warns the next person.</p>'
        '<div class="cta-row" style="justify-content:center">'
        f'<a class="btn" href="{APP_URL}">Write a verified review</a>'
        f'<a class="btn ghost" href="{SITE_URL}/apartments/{key}/">All '
        + esc(st_name) + ' communities</a></div></div>')

    # FAQ (visible + schema)
    faq_html = "".join(
        f"<h3>{esc(q)}</h3><p>{esc(a)}</p>" for q, a in data["faqs"])
    body += f'<div class="card"><h2>{esc(st_name)} tenant rights FAQ</h2>{faq_html}</div>'

    faq_schema = json.dumps({
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{
            "@type": "Question", "name": q,
            "acceptedAnswer": {"@type": "Answer", "text": a},
        } for q, a in data["faqs"]]})
    body += f'<script type="application/ld+json">{faq_schema}</script>'

    # Disclaimer + provenance
    body += (
        '<div class="card"><p style="font-size:.85rem;color:var(--muted)">'
        'This guide is general information about the ' + esc(data["statute"])
        + ', not legal advice, and laws change. For advice about your '
        'situation, contact a licensed ' + esc(st_name) + ' attorney or legal '
        'aid organization. Last reviewed: ' + LAST_REVIEWED + '.</p></div>')

    h1 = (esc(st_name) + ' tenant rights,<br /><span class="accent">plainly '
          'explained.</span>')
    sub = ("Security deposits, repairs, privacy, and eviction timelines under "
           "the " + data["statute"] + " — with the statute citations, so you "
           "can point to the law, not argue about it.")

    out = _gen.GROUP_TEMPLATE
    for token, val in [
        ("@TITLE@", esc(title)), ("@DESC@", esc(desc)), ("@CANON@", canon),
        ("@SITE@", SITE_URL),
        ("@CSS@", _gen.PAGE_CSS + _gen.GROUP_CSS + _gen.HUB_CSS),
        ("@HEADER@", _gen.header_html()),
        ("@EYEBROW@", "Renter Rights Guide"),
        ("@H1@", h1), ("@SUB@", esc(sub)), ("@STATS@", stats),
        ("@APP@", APP_URL), ("@BODY@", body), ("@FOOTER@", _gen.footer_html()),
    ]:
        out = out.replace(token, val)
    return canon, out


def render_index():
    canon = f"{SITE_URL}/guides/tenant-rights/"
    year = LAST_REVIEWED.split()[-1]
    title = (f"Tenant Rights by State ({year}) — Security Deposits, Repairs "
             f"& Eviction Laws in All 50 States | LeaseReputation")
    desc = ("Plain-English tenant rights guides for all 50 states, with "
            "statute citations: security deposit limits and return deadlines, "
            "repair rights, entry notice, rent rules, and eviction timelines.")

    stats = "".join(
        f'<span class="statchip"><b>{esc(v)}</b>&nbsp;{esc(k)}</span>'
        for k, v in [("states covered", "50"), ("statute-cited", "Every claim"),
                     ("legalese", "Zero"), ("reviewed", LAST_REVIEWED)])

    links = "".join(
        f'<a href="{SITE_URL}/guides/tenant-rights/{key}/">'
        f'{esc(data["name"])}</a>'
        for key, data in sorted(STATES.items(), key=lambda kv: kv[1]["name"]))

    body = (
        '<div class="card"><h2>Pick your state</h2>'
        '<p>Every guide covers the four fights that actually happen: getting '
        'your security deposit back, getting repairs made, keeping your '
        'privacy, and surviving an eviction notice — each with the statute '
        'citations, so you can point to the law instead of arguing about '
        'it.</p><div class="citylinks" style="padding-left:0">' + links
        + '</div></div>'
        '<div class="card"><h2>Why statutes are half the story</h2>'
        '<p>Deposit deadlines and repair rights only help if you know them '
        'before you sign — and the other half is knowing how a specific '
        'community actually behaves when the lease ends. That\'s what '
        'verified resident reviews are for: the deposit that did or didn\'t '
        'come back, the maintenance ticket that did or didn\'t get answered. '
        'The law tells you your rights; residents tell you whether you\'ll '
        'need them.</p></div>'
        '<div class="cta-band"><h2>Know a community\'s reputation before '
        'you sign.</h2><p>19,000+ apartment communities, reviewed only by '
        'verified residents.</p>'
        '<div class="cta-row" style="justify-content:center">'
        f'<a class="btn" href="{SITE_URL}/community/">Browse communities</a>'
        f'<a class="btn ghost" href="{APP_URL}">Write a verified review</a>'
        '</div></div>'
        '<div class="card"><p style="font-size:.85rem;color:var(--muted)">'
        'These guides are general information, not legal advice, and laws '
        'change. For advice about your situation, contact a licensed '
        'attorney or legal aid organization in your state. Last reviewed: '
        + LAST_REVIEWED + '.</p></div>')

    h1 = ('Tenant rights in all 50 states,<br />'
          '<span class="accent">plainly explained.</span>')
    sub = ("Security deposits, repairs, privacy, and eviction — state by "
           "state, in plain English, with the statute citations that let you "
           "point to the law.")

    out = _gen.GROUP_TEMPLATE
    for token, val in [
        ("@TITLE@", esc(title)), ("@DESC@", esc(desc)), ("@CANON@", canon),
        ("@SITE@", SITE_URL),
        ("@CSS@", _gen.PAGE_CSS + _gen.GROUP_CSS + _gen.HUB_CSS),
        ("@HEADER@", _gen.header_html()),
        ("@EYEBROW@", "Renter Rights Guides"),
        ("@H1@", h1), ("@SUB@", esc(sub)), ("@STATS@", stats),
        ("@APP@", APP_URL), ("@BODY@", body), ("@FOOTER@", _gen.footer_html()),
    ]:
        out = out.replace(token, val)
    return out


def main():
    n = 0
    for key, data in STATES.items():
        canon, html = render_state(key, data)
        d = os.path.join(BASE, "guides", "tenant-rights", key)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  + guides/tenant-rights/{key}/ — {data['name']}")
        n += 1
    with open(os.path.join(BASE, "guides", "tenant-rights", "index.html"),
              "w", encoding="utf-8") as f:
        f.write(render_index())
    print("  + guides/tenant-rights/ — 50-state index")
    print(f"\nDone: {n} state guide(s) + index. Next: python "
          f"generate_community_pages.py (picks guides into the sitemap + "
          f"links from state hubs) -> kv_sync.")


if __name__ == "__main__":
    main()
