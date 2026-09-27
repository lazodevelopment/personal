# =============================================================================
# ATAVIA WEDDINGS â€” AUTOMATED CONTRACT GENERATOR  (v1 Â· 2026-07-15)
# =============================================================================
# One chassis, three service-type variants (photo / video / combined),
# conditional payment blocks (standard / pif). Replaces the paper Credit Card
# Authorization Form with a Payment Authorization & Card on File clause
# (Stax tokenization â€” no card data ever touches our stack).
#
# Usage (library):
#   from atavia_contract_generator import generate_contract
#   pdf_bytes = generate_contract(package_id="duet",
#                                 payment_option="standard",   # or "pif"
#                                 client=CLIENT_DICT,          # or None for blank
#                                 out_path="contract.pdf")     # optional
#
# Usage (CLI test harness):
#   python atavia_contract_generator.py --all         -> renders all 22 variants
#   python atavia_contract_generator.py duet standard -> one blank contract
#
# Requires: reportlab, atavia_packages.json alongside this file,
#           fonts/ dir with CormorantGaramond-var.ttf + Lato-{Regular,Bold,Italic}.ttf
#           (falls back to Times/Helvetica if fonts missing).
# =============================================================================

import json
import os
import sys
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table,
    TableStyle, KeepTogether, HRFlowable,
)

# ---------------------------------------------------------------- palette ---
CHARCOAL = HexColor("#2B2B2B")
COPPER   = HexColor("#B0713F")
IVORY    = HexColor("#FAF7F2")
GREY     = HexColor("#6B6B6B")
LINE     = HexColor("#D8D2C8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------ fonts ---
def _register_fonts():
    """Register brand fonts; fall back to core-14 if unavailable."""
    fd = os.path.join(BASE_DIR, "fonts")
    try:
        pdfmetrics.registerFont(TTFont("Cormorant", os.path.join(fd, "CormorantGaramond-var.ttf")))
        pdfmetrics.registerFont(TTFont("Lato",       os.path.join(fd, "Lato-Regular.ttf")))
        pdfmetrics.registerFont(TTFont("Lato-Bold",  os.path.join(fd, "Lato-Bold.ttf")))
        pdfmetrics.registerFont(TTFont("Lato-Italic",os.path.join(fd, "Lato-Italic.ttf")))
        return {"display": "Cormorant", "body": "Lato", "bold": "Lato-Bold", "italic": "Lato-Italic"}
    except Exception:
        return {"display": "Times-Roman", "body": "Helvetica",
                "bold": "Helvetica-Bold", "italic": "Helvetica-Oblique"}

F = _register_fonts()

def _sp(text):
    """Letter-spaced section headers, matching the source contracts.
    Plain spaced characters â€” no canvas Tc tricks (see ReportLab trk() bug)."""
    return " ".join(list(text.replace(" ", "  ")))

# --------------------------------------------------------------- packages ---
with open(os.path.join(BASE_DIR, "atavia_packages.json"), encoding="utf-8") as _f:
    _DATA = json.load(_f)
BRAND    = _DATA["brand"]
RULES    = _DATA["pricing_rules"]
PACKAGES = {p["id"]: p for p in _DATA["packages"]}

SERVICE_NOUN = {   # drives every family-variant clause
    "photo":    {"svc": "photography", "svc_title": "Photography",
                 "media": "images", "replacement": "photographer",
                 "loss": "image files", "second": "Second Photographer"},
    "video":    {"svc": "videography", "svc_title": "Videography",
                 "media": "video content", "replacement": "videographer",
                 "loss": "video footage", "second": "Second Videographer"},
    "combined": {"svc": "photography and videography",
                 "svc_title": "Photography & Videography",
                 "media": "images and video content",
                 "replacement": "photographer and/or videographer",
                 "loss": "image and video files", "second": "Second Shooter"},
}

def compute_pricing(package_id, second_shooter=False, extra_hours=0,
                    discount=0, days_to_event=None):
    """Single source of truth for pricing math. Used by the generator AND by
    main.py so the server-side total can never drift from the contract.

    discount: a pre-validated inquiry-code discount amount (dollars). The
    caller (main.py) is responsible for validating the code itself; this
    function only does arithmetic and bounds-checking.

    Returns dict(base_total, addons=[{id,label,amount}], addons_total,
                 discount, total, coverage_hours)."""
    pkg = PACKAGES[package_id]
    extra_hours = int(extra_hours or 0)
    discount = int(discount or 0)
    if discount < 0:
        raise ValueError("discount cannot be negative")
    if extra_hours < 0 or extra_hours > RULES["max_extra_hours"]:
        raise ValueError(
            f"extra_hours must be 0-{RULES['max_extra_hours']}")
    addons = []
    if second_shooter:
        addons.append({
            "id": "second_shooter",
            "label": SERVICE_NOUN[pkg["service_type"]]["second"],
            "amount": RULES["addon_second_shooter"],
        })
    if extra_hours:
        addons.append({
            "id": "extra_hours",
            "label": (f"Additional Coverage \u2014 {extra_hours} "
                      f"{'Hour' if extra_hours == 1 else 'Hours'} @ "
                      f"{_money(RULES['addon_extra_hour'])}/hr"),
            "amount": extra_hours * RULES["addon_extra_hour"],
        })
    if days_to_event is not None and days_to_event <= RULES.get("rush_days", 14):
        addons.append({
            "id": "rush_fee",
            "label": "Short-Notice Accommodation Fee",
            "amount": RULES.get("rush_fee", 149),
        })
    addons_total = sum(a["amount"] for a in addons)
    gross = pkg["total"] + addons_total
    if discount >= gross:
        raise ValueError("discount cannot equal or exceed the package total")
    return {
        "base_total": pkg["total"],
        "addons": addons,
        "addons_total": addons_total,
        "discount": discount,
        "total": gross - discount,
        "coverage_hours": pkg["hours"] + extra_hours,
    }

def _money(n):
    return "${:,}".format(n)

# ============================================================ CLAUSE MODEL ==
# Each clause: dict(title=..., text=callable(ctx) -> str or None to omit).
# Numbering is computed at render time, so omitted clauses never leave gaps.
# Cross-references are by clause NAME, never number.

def _c_retainer(ctx):
    if ctx["payment_option"] == "standard":
        return (
            "A non-refundable retainer deposit of five hundred dollars ($500) is due upon "
            "execution of this Agreement to reserve the Event date and is applied toward the "
            "Total Investment. The remaining balance of {bal} is due fourteen (14) business days "
            "from the date this Agreement is executed \u2014 or, if the Event date falls sooner, no later than the day before the Event \u2014 and will be automatically "
            "charged to the Client's payment method on file as set forth in the Payment "
            "Authorization & Card on File clause below. Dates are reserved on a first-come, "
            "first-served basis."
        ).format(bal=_money(ctx["balance"]))
    return (
        "The Client has elected to pay the Total Investment in full upon execution of this "
        "Agreement and receives a one hundred dollar ($100) paid-in-full discount, for a "
        "discounted Total Investment of {pif}. Of this amount, five hundred dollars ($500) "
        "constitutes a non-refundable retainer that reserves the Event date. Dates are "
        "reserved on a first-come, first-served basis."
    ).format(pif=_money(ctx["pif_total"]))

def _c_payment_auth(ctx):
    return (
        "All payments under this Agreement are processed through the Company's secure "
        "third-party payment processor. Card information is entered by the Client directly "
        "with the processor and is never collected, viewed, or stored by the Company. Upon "
        "the Client's first payment, the Client's payment method is securely retained on "
        "file by the processor, and the Client authorizes the Company to charge that payment "
        "method for amounts due under this Agreement, including the remaining balance (if "
        "the Standard Plan is selected), overtime as described in the Overtime & Additional "
        "Coverage clause, any gratuity the Client elects to add as described in the "
        "Gratuity clause, and any other amounts the Client agrees to in writing. Charges "
        "will appear on the Client's statement as Danbren Media LLC, the Company's parent "
        "company. This authorization remains in effect until all amounts due under this "
        "Agreement are paid; the Client may update the payment method on file by written "
        "notice. The Client agrees not to dispute charges made in accordance with this "
        "Agreement."
    )

def _c_services(ctx):
    return ("The Company shall provide professional wedding {svc} services as outlined in "
            "the Services & Package Details above.").format(**ctx["nouns"])

def _c_second_shooter(ctx):
    if not ctx.get("second_shooter"):
        return None  # clause omitted entirely; numbering closes the gap
    return (
        "The Client has added a {second} to the collection at the time of booking for "
        "{price}, which is included in the Total Investment. The {second_lc} provides "
        "concurrent coverage during the contracted coverage hours \u2014 capturing "
        "simultaneous preparations, additional angles during key moments, and candid "
        "coverage \u2014 and carries backup equipment. The specific assignment and "
        "positioning of team members on the day of the Event remains at the Company's "
        "reasonable professional discretion, informed by the Client's timeline and "
        "questionnaire."
    ).format(second=ctx["nouns"]["second"],
             second_lc=ctx["nouns"]["second"].lower(),
             price=_money(RULES["addon_second_shooter"]))

def _c_overtime(ctx):
    pre = ""
    if ctx.get("extra_hours"):
        eh = ctx["extra_hours"]
        pre = (
            "The Client has purchased {n} additional {hr} of coverage at the time of "
            "booking at the published rate of {rate} per hour; such additional {hr2} "
            "{isare} included in the contracted coverage hours specified in the Services "
            "& Package Details above and in the Total Investment. "
        ).format(n=eh, hr="hour" if eh == 1 else "hours",
                 hr2="hour" if eh == 1 else "hours",
                 isare="is" if eh == 1 else "are",
                 rate=_money(RULES["addon_extra_hour"]))
    return pre + (
        "Coverage is limited to the number of hours specified in the Services & Package "
        "Details above. Should the Client require coverage beyond the contracted hours on "
        "the day of the Event, additional time will be billed at a rate of one hundred "
        "seventy-five dollars ($175) per hour, charged in full-hour increments. If "
        "additional coverage is arranged and paid for in advance of the Event date, the "
        "rate is reduced to one hundred twenty-five dollars ($125) per hour. Any overtime "
        "incurred on the day of the Event is due and payable, and the Company may charge "
        "the payment method on file, prior to delivery of the final files."
    )

def _c_license(ctx):
    st = ctx["service_type"]
    if st == "photo":
        return (
            "Upon receipt of payment in full, the Company grants the Client full ownership "
            "rights to the final edited images delivered under this Agreement, including the "
            "right to print, reproduce, and share them for personal use. The Company retains "
            "a non-exclusive license to use any images for portfolio, marketing, social "
            "media, advertising, and promotional purposes unless the Client provides written "
            "notice to opt out within thirty (30) days of signing this Agreement."
        )
    if st == "video":
        return (
            "The Company retains full copyright and ownership of all video content produced "
            "under this Agreement. The Client is granted a personal, non-exclusive license "
            "to use the video content for personal, non-commercial purposes. The Company "
            "reserves the right to use any video content for portfolio, marketing, social "
            "media, advertising, and promotional purposes unless the Client provides written "
            "notice to opt out within thirty (30) days of signing this Agreement."
        )
    return (
        "Upon receipt of payment in full, the Company grants the Client full ownership "
        "rights to the final edited images delivered under this Agreement, including the "
        "right to print, reproduce, and share them for personal use. The Company retains "
        "full copyright and ownership of all video content produced under this Agreement, "
        "and the Client is granted a personal, non-exclusive license to use the video "
        "content for personal, non-commercial purposes. The Company retains a non-exclusive "
        "license to use any images or video content for portfolio, marketing, social media, "
        "advertising, and promotional purposes unless the Client provides written notice to "
        "opt out within thirty (30) days of signing this Agreement."
    )

def _c_cooperation(ctx):
    return (
        "The Client agrees to provide a detailed timeline of the wedding day events no "
        "later than fourteen (14) days prior to the Event date. The Client agrees to "
        "cooperate with reasonable requests from the Company to facilitate {svc} coverage. "
        "The Client understands that the quality of the final product depends in part upon "
        "the Client's cooperation, including allowing adequate time for key moments and "
        "ensuring access to key locations."
    ).format(**ctx["nouns"])

def _c_exclusivity(ctx):
    return (
        "The Company shall be the sole and exclusive {svc} provider for the Event. The "
        "Client agrees that no other person or company shall be engaged, hired, or "
        "permitted to provide professional {svc} services at the Event during the "
        "Company's coverage period. This provision does not restrict guests from capturing "
        "personal, non-professional photographs or video for their own private use. Should "
        "another {svc} provider perform the same function at the Event in breach of this "
        "provision, the Client shall be in material breach of this Agreement, the Company "
        "shall not be responsible for any resulting interference with or compromise of its "
        "coverage, and the Company reserves the right to pursue any and all available legal "
        "and equitable remedies."
    ).format(**ctx["nouns"])

def _c_safe(ctx):
    return (
        "The Client agrees to provide a safe and respectful working environment for the "
        "Company's team. The Company reserves the right to pause, suspend, or cease "
        "coverage, without refund, if any member of the team is subjected to conditions "
        "that are unsafe, abusive, harassing, or threatening. The Company will make "
        "reasonable efforts to resume coverage once such conditions are resolved."
    )

def _c_cancellation(ctx):
    if ctx["payment_option"] == "standard":
        return (
            "The retainer deposit is non-refundable under all circumstances. If the Client "
            "cancels more than ninety (90) days prior to the Event date, any amounts paid "
            "in excess of the retainer deposit shall be refunded. If the Client cancels "
            "within ninety (90) days of the Event date, fifty percent (50%) of the total "
            "balance (excluding the non-refundable retainer) shall be retained by the "
            "Company. One complimentary reschedule is permitted if the new date is within "
            "twelve (12) months of the original date and is subject to availability."
        )
    return (
        "All amounts paid under this Agreement, including the discounted Total Investment "
        "paid at signing, are non-refundable upon cancellation by the Client for any "
        "reason. The parties agree that, in consideration of the Company's reservation of "
        "the Event date, declination of other bookings for that date, and allocation of "
        "personnel and resources, the Company's retention of all amounts paid constitutes "
        "reasonable liquidated damages and not a penalty. One complimentary reschedule is "
        "permitted if the new date is within twelve (12) months of the original date and "
        "is subject to availability."
    )

def _c_cancel_company(ctx):
    return (
        "In the unlikely event that the Company must cancel due to illness, emergency, or "
        "unforeseen circumstances, the Company will make every effort to secure a "
        "qualified replacement {replacement}. If no suitable replacement can be arranged, "
        "the Company shall provide a full refund of all payments received. The Company's "
        "liability in such event shall be limited to the return of all funds paid."
    ).format(**ctx["nouns"])

def _c_liability(ctx):
    return (
        "In the unlikely event of a total loss of {loss} due to equipment failure, memory "
        "card failure, or other unforeseen technical issues, the Company's total liability "
        "shall be limited to a full refund of all payments made under this Agreement. The "
        "Company shall not be held liable for any indirect, incidental, consequential, or "
        "special damages."
    ).format(**ctx["nouns"])

def _c_venue(ctx):
    return (
        "The Company shall not be held responsible for limitations or restrictions imposed "
        "by venues, officiants, or other vendors, including but not limited to no-flash "
        "policies, restricted access to certain areas, poor or insufficient lighting, "
        "obstruction or interference by guests or other vendors, or delays and timeline "
        "overruns caused by parties other than the Company. The Client acknowledges that "
        "such factors may affect the final product and are beyond the Company's reasonable "
        "control."
    )

def _c_force_majeure(ctx):
    return (
        "Neither party shall be liable for failure to perform obligations under this "
        "Agreement if such failure results from circumstances beyond the reasonable "
        "control of the affected party, including but not limited to natural disasters, "
        "pandemics, government restrictions, severe weather, venue closures, or acts of God."
    )

def _c_delivery(ctx):
    st = ctx["service_type"]
    if st == "photo":
        return (
            "All final edited images shall be delivered via a private online gallery. It is "
            "the Client's sole responsibility to download and back up all images within "
            "ninety (90) days of delivery. The Company is not responsible for files beyond "
            "the stated delivery period."
        )
    if st == "video":
        return (
            "All final video content shall be delivered via digital download or streaming "
            "link. It is the Client's sole responsibility to download and back up all files "
            "within ninety (90) days of delivery. The Company is not responsible for "
            "footage beyond the stated delivery period."
        )
    return (
        "Final edited images shall be delivered via a private online gallery and final "
        "video content via digital download or streaming link. It is the Client's sole "
        "responsibility to download and back up all files within ninety (90) days of "
        "delivery. The Company is not responsible for files beyond the stated delivery "
        "period."
    )

def _c_engagement(ctx):
    if ctx["service_type"] == "video":
        return None  # video collections do not include an engagement session
    return (
        "This collection includes one (1) complimentary engagement session of up to one "
        "(1) hour at one or more mutually agreed locations, to be scheduled at least "
        "thirty (30) days prior to the Event date and subject to availability."
    )

def _c_social(ctx):
    return (
        "The Client agrees to tag and credit Atavia Weddings on any social media posts "
        "featuring {media} produced by the Company. The Company appreciates but does not "
        "require vendor tagging."
    ).format(**ctx["nouns"])

def _c_meal(ctx):
    return (
        "For events with coverage exceeding five (5) hours, the Client agrees to provide "
        "a meal for each member of the team present at the event."
    )

def _c_gratuity(ctx):
    return (
        "Gratuity is neither required nor expected. Team members do not accept cash "
        "gratuities at the Event. If the Client wishes to recognize the team, an optional "
        "gratuity in an amount of the Client's choosing may be added through the Company's "
        "secure payment system at any time before or within ninety (90) days after the "
        "Event, and the Client authorizes such elected gratuity to be charged to the "
        "payment method on file. One hundred percent (100%) of gratuities are distributed "
        "to the team members who served the Client's Event. Gratuities are voluntary and "
        "non-refundable."
    )

def _c_travel(ctx):
    return (
        "No travel fees. The Company maintains dedicated teams positioned in the Client's "
        "area for seamless service without added travel costs."
    )

def _c_indemnification(ctx):
    return (
        "The Client agrees to indemnify and hold harmless the Company, its owners, "
        "employees, contractors, and agents from and against any and all claims, damages, "
        "losses, costs, and expenses (including reasonable attorney's fees) arising out of "
        "or related to the Client's breach of this Agreement or the Client's negligence or "
        "willful misconduct."
    )

def _c_disputes(ctx):
    return (
        "This Agreement shall be governed by and construed in accordance with the laws of "
        "the state in which the Client resides, as identified in this Agreement (the "
        "\u201cGoverning State\u201d). Any disputes arising under or in connection with "
        "this Agreement shall first be submitted to mediation in the Governing State. If "
        "mediation is unsuccessful, the dispute shall be resolved through binding "
        "arbitration in accordance with the rules of the American Arbitration Association."
    )

def _c_entire(ctx):
    return (
        "This Agreement constitutes the entire understanding between the parties and "
        "supersedes all prior negotiations, representations, warranties, commitments, "
        "offers, and agreements, whether written or oral. This Agreement may only be "
        "amended or modified by a written instrument signed by both parties."
    )

def _c_severability(ctx):
    return (
        "If any provision of this Agreement is found to be invalid, illegal, or "
        "unenforceable, the remaining provisions shall continue in full force and effect."
    )

def _services_title(ctx):
    return "{svc_title} Services".format(**ctx["nouns"])

def _license_title(ctx):
    return ("Creative License & Copyright" if ctx["service_type"] == "video"
            else "Creative License & Ownership")

CLAUSES = [
    (lambda c: "Retainer & Booking",                     _c_retainer),
    (lambda c: "Payment Authorization & Card on File",   _c_payment_auth),
    (_services_title,                                    _c_services),
    (lambda c: c["nouns"]["second"],                     _c_second_shooter),
    (lambda c: "Overtime & Additional Coverage",         _c_overtime),
    (_license_title,                                     _c_license),
    (lambda c: "Cooperation & Scheduling",               _c_cooperation),
    (lambda c: "Exclusivity",                            _c_exclusivity),
    (lambda c: "Safe & Respectful Working Environment",  _c_safe),
    (lambda c: "Cancellation & Rescheduling",            _c_cancellation),
    (lambda c: "Cancellation by Company",                _c_cancel_company),
    (lambda c: "Limitation of Liability",                _c_liability),
    (lambda c: "Venue & Third-Party Limitations",        _c_venue),
    (lambda c: "Force Majeure",                          _c_force_majeure),
    (lambda c: "Delivery",                               _c_delivery),
    (lambda c: "Engagement Session",                     _c_engagement),
    (lambda c: "Social Media & Vendor Tagging",          _c_social),
    (lambda c: "Meal Provision",                         _c_meal),
    (lambda c: "Gratuity",                               _c_gratuity),
    (lambda c: "Travel",                                 _c_travel),
    (lambda c: "Indemnification",                        _c_indemnification),
    (lambda c: "Dispute Resolution & Governing Law",     _c_disputes),
    (lambda c: "Entire Agreement",                       _c_entire),
    (lambda c: "Severability",                           _c_severability),
]

# ============================================================== RENDERING ===

def _styles():
    return {
        "brand": ParagraphStyle("brand", fontName=F["display"], fontSize=26,
                                textColor=CHARCOAL, alignment=TA_CENTER, leading=30),
        "doctitle": ParagraphStyle("doctitle", fontName=F["body"], fontSize=11,
                                   textColor=COPPER, alignment=TA_CENTER, leading=16),
        "section": ParagraphStyle("section", fontName=F["bold"], fontSize=9.5,
                                  textColor=COPPER, leading=14, spaceBefore=14,
                                  spaceAfter=6),
        "body": ParagraphStyle("body", fontName=F["body"], fontSize=8.6,
                               textColor=CHARCOAL, leading=12.6, alignment=TA_JUSTIFY,
                               spaceAfter=6),
        "clause": ParagraphStyle("clause", fontName=F["body"], fontSize=8.6,
                                 textColor=CHARCOAL, leading=12.6, alignment=TA_JUSTIFY,
                                 spaceAfter=7),
        "label": ParagraphStyle("label", fontName=F["bold"], fontSize=8.6,
                                textColor=CHARCOAL, leading=13),
        "value": ParagraphStyle("value", fontName=F["body"], fontSize=8.6,
                                textColor=CHARCOAL, leading=13),
        "fine": ParagraphStyle("fine", fontName=F["italic"], fontSize=7.6,
                               textColor=GREY, leading=10.5, alignment=TA_JUSTIFY),
        "bullet": ParagraphStyle("bullet", fontName=F["body"], fontSize=8.6,
                                 textColor=CHARCOAL, leading=13),
        "pkgname": ParagraphStyle("pkgname", fontName=F["display"], fontSize=13,
                                  textColor=CHARCOAL, leading=16, spaceAfter=4),
    }

def _field(label, value, S, width_label=1.55):
    """A label + underlined value cell pair for merge fields."""
    v = value if value else "\u00a0" * 4
    t = Table(
        [[Paragraph(f"<b>{label}</b>", S["label"]), Paragraph(v, S["value"])]],
        colWidths=[width_label * inch, None],
    )
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LINEBELOW", (1, 0), (1, 0), 0.5, LINE),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
    ]))
    return t

def _header_footer(canvas, doc, ctx):
    canvas.saveState()
    w, h = letter
    # footer rule + text (mirrors source layout)
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(0.75 * inch, 0.62 * inch, w - 0.75 * inch, 0.62 * inch)
    canvas.setFont(F["body"], 6.8)
    canvas.setFillColor(GREY)
    canvas.drawString(
        0.75 * inch, 0.46 * inch,
        f"{BRAND['name'].upper()} \u00b7 {BRAND['phone']} \u00b7 "
        f"{BRAND['email']} \u00b7 {BRAND['website']}",
    )
    canvas.drawRightString(
        w - 0.75 * inch, 0.46 * inch,
        f"{ctx['pkg']['name']} \u2014 {ctx['collection_family']} \u00b7 Page {doc.page}",
    )
    canvas.restoreState()

def _build_story(ctx):
    S = _styles()
    pkg = ctx["pkg"]
    client = ctx["client"] or {}
    story = []

    # -- masthead ------------------------------------------------------------
    story.append(Paragraph("ATAVIA WEDDINGS", S["brand"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(_sp("SERVICE AGREEMENT"), S["doctitle"]))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=0.7, color=COPPER))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f"This Wedding {ctx['nouns']['svc_title']} Service Agreement (the "
        f"\u201cAgreement\u201d) is entered into as of the date signed below, by and "
        f"between Atavia Weddings (hereinafter the \u201cCompany\u201d or "
        f"\u201cAtavia\u201d) and the Client(s) identified below.", S["body"]))

    # -- parties -------------------------------------------------------------
    story.append(Paragraph(_sp("PARTIES & CLIENT INFORMATION"), S["section"]))
    story.append(_field("Client Name:", client.get("client_names", ""), S))
    row = Table([[
        _field("Mailing Address:", client.get("mailing_address", ""), S, 1.3),
        _field("City / State / ZIP:", client.get("city_state_zip", ""), S, 1.3),
    ]], colWidths=[3.5 * inch, 3.5 * inch])
    row.setStyle(TableStyle([("LEFTPADDING", (0, 0), (0, 0), 0),
                             ("VALIGN", (0, 0), (-1, -1), "BOTTOM")]))
    story.append(row)
    row = Table([[
        _field("Client State of Residence (Governing State):",
               client.get("governing_state", ""), S, 2.9),
        _field("Phone:", client.get("phone", ""), S, 0.6),
    ]], colWidths=[4.4 * inch, 2.6 * inch])
    row.setStyle(TableStyle([("LEFTPADDING", (0, 0), (0, 0), 0),
                             ("VALIGN", (0, 0), (-1, -1), "BOTTOM")]))
    story.append(row)
    story.append(_field("Email:", client.get("email", ""), S, 0.6))

    # -- event ---------------------------------------------------------------
    story.append(Paragraph(_sp("EVENT DETAILS"), S["section"]))
    row = Table([[
        _field("Event Date:", client.get("event_date", ""), S, 0.95),
        _field("Estimated Guest Count:", client.get("guest_count", ""), S, 1.7),
    ]], colWidths=[3.5 * inch, 3.5 * inch])
    row.setStyle(TableStyle([("LEFTPADDING", (0, 0), (0, 0), 0),
                             ("VALIGN", (0, 0), (-1, -1), "BOTTOM")]))
    story.append(row)
    story.append(_field("Ceremony Venue:", client.get("ceremony_venue", ""), S, 1.35))
    story.append(_field("Reception Venue:", client.get("reception_venue", ""), S, 1.35))
    row = Table([[
        _field("Start Time:", client.get("start_time", ""), S, 0.9),
        _field("End Time:", client.get("end_time", ""), S, 0.85),
    ]], colWidths=[3.5 * inch, 3.5 * inch])
    row.setStyle(TableStyle([("LEFTPADDING", (0, 0), (0, 0), 0),
                             ("VALIGN", (0, 0), (-1, -1), "BOTTOM")]))
    story.append(row)

    # -- package -------------------------------------------------------------
    story.append(Paragraph(_sp("SERVICES & PACKAGE DETAILS"), S["section"]))
    story.append(Paragraph(f"{pkg['name']} \u2014 {pkg['collection_label']}",
                           S["pkgname"]))
    bl = list(pkg["bullets"])
    if ctx.get("second_shooter"):
        bl.append(f"{ctx['nouns']['second']} (Added)")
    if ctx.get("extra_hours"):
        eh = ctx["extra_hours"]
        bl.append(f"+{eh} Additional {'Hour' if eh == 1 else 'Hours'} "
                  f"({ctx['coverage_hours']} Hours of Coverage Total)")
    half = (len(bl) + 1) // 2
    left, right = bl[:half], bl[half:] + [""] * (half - len(bl[half:]))
    btab = Table(
        [[Paragraph(f"\u2022\u2002{a}", S["bullet"]),
          Paragraph(f"\u2022\u2002{b}" if b else "", S["bullet"])]
         for a, b in zip(left, right)],
        colWidths=[3.4 * inch, 3.4 * inch],
    )
    btab.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (0, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    story.append(btab)

    # -- investment summary (conditional on payment option) -------------------
    story.append(Paragraph(_sp("INVESTMENT SUMMARY"), S["section"]))
    addon_rows = []
    if ctx["addons"] or ctx["discount"]:
        addon_rows = [[f"{pkg['name']} \u2014 {ctx['collection_family']}",
                       _money(ctx["base_total"])]]
        addon_rows += [[a["label"], _money(a["amount"])]
                       for a in ctx["addons"]]
        if ctx["discount"]:
            code = f" ({ctx['discount_code']})" if ctx["discount_code"] else ""
            addon_rows.append([f"Inquiry Discount{code}",
                               f"\u2212{_money(ctx['discount'])}"])
    if ctx["payment_option"] == "standard":
        inv_rows = addon_rows + [
            ["Total Investment",                 _money(ctx["total"])],
            ["Retainer Deposit (due at signing)", _money(RULES["retainer"])],
            ["Remaining Balance",                _money(ctx["balance"])],
        ]
        fine = (
            "The $500 retainer is non-refundable and applied toward the Total "
            "Investment. The remaining balance is automatically charged to the payment "
            "method on file fourteen (14) business days after this Agreement is signed (or no later than the day before the Event, if sooner)."
        )
    else:
        inv_rows = addon_rows + [
            ["Total Investment",                          _money(ctx["total"])],
            ["Paid-in-Full Discount",                     f"\u2212{_money(RULES['pif_discount'])}"],
            ["Discounted Total Investment (due at signing)", _money(ctx["pif_total"])],
        ]
        fine = (
            "The discounted Total Investment is due in full at signing and is "
            "non-refundable as set forth in the Terms & Conditions."
        )
    itab = Table([[Paragraph(f"<b>{a}</b>", S["label"]),
                   Paragraph(b, S["value"])] for a, b in inv_rows],
                 colWidths=[4.4 * inch, 2.4 * inch])
    itab.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINE),
        ("LINEBELOW", (0, -1), (-1, -1), 0.9, COPPER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (0, -1), 0),
    ]))
    story.append(itab)
    story.append(Spacer(1, 4))
    story.append(Paragraph(fine, S["fine"]))

    # -- selected payment option ----------------------------------------------
    story.append(Paragraph(_sp("SELECTED PAYMENT OPTION"), S["section"]))
    if ctx["payment_option"] == "standard":
        story.append(Paragraph(
            f"<b>Standard Plan.</b> A $500 non-refundable retainer is due at signing; "
            f"the remaining balance of {_money(ctx['balance'])} is automatically charged "
            f"to the payment method on file fourteen (14) business days after signing (or no later than the day before the Event, if sooner). "
            f"Total Investment: {_money(ctx['total'])}.", S["clause"]))
    else:
        story.append(Paragraph(
            f"<b>Paid in Full.</b> The Client elects to pay the Total Investment in full "
            f"at signing and receives a $100 paid-in-full discount. Discounted Total "
            f"Investment: {_money(ctx['pif_total'])}. All amounts paid are non-refundable "
            f"as set forth in the Terms & Conditions.", S["clause"]))

    # -- terms & conditions ----------------------------------------------------
    story.append(Paragraph(_sp("TERMS & CONDITIONS"), S["section"]))
    n = 0
    for title_fn, text_fn in CLAUSES:
        text = text_fn(ctx)
        if text is None:
            continue
        n += 1
        story.append(Paragraph(
            f"<b>{n}. {title_fn(ctx)}.</b> {text}", S["clause"]))

    # -- acknowledgment & signatures -------------------------------------------
    sig_block = []
    sig_block.append(Paragraph(_sp("ACKNOWLEDGMENT & SIGNATURES"), S["section"]))
    ack = ("By signing below, the Client acknowledges that they have read, understand, "
           "and agree to all terms and conditions set forth in this Agreement. The "
           "Client further acknowledges that ")
    ack += ("the retainer deposit is non-refundable"
            if ctx["payment_option"] == "standard"
            else "all amounts paid under this Agreement are non-refundable")
    ack += " and that this Agreement is legally binding."
    sig_block.append(Paragraph(ack, S["body"]))
    sig_block.append(Spacer(1, 6))
    sig_block.append(Paragraph(_sp("CLIENT"), S["section"]))
    if ctx.get("signwell"):
        # SignWell text tags, rendered white-on-white so they're invisible but
        # machine-readable. Format: {{type:signer:required:label:prefill:api_id:width:height}}
        # {{s:1:y:::client_sig:200:36}}  = required signature field, signer 1, 200x36px
        # {{af_d_s:1::::date_signed:90:20}} = autofill date-signed, signer 1
        tag_style = ParagraphStyle("swtag", fontName=F["body"], fontSize=10,
                                   textColor=HexColor("#FFFFFF"), leading=13)
        sig_cell = Paragraph("{{s:1:y:::client_sig:200:36}}", tag_style)
        date_cell = Paragraph("{{af_d_s:1}}", tag_style)
        row = Table([[
            Table([[Paragraph("<b>Client Signature:</b>", S["label"]), sig_cell]],
                  colWidths=[1.35 * inch, None],
                  style=TableStyle([("LINEBELOW", (1, 0), (1, 0), 0.5, LINE),
                                    ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                                    ("LEFTPADDING", (0, 0), (0, 0), 0)])),
            Table([[Paragraph("<b>Date:</b>", S["label"]), date_cell]],
                  colWidths=[0.55 * inch, None],
                  style=TableStyle([("LINEBELOW", (1, 0), (1, 0), 0.5, LINE),
                                    ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                                    ("LEFTPADDING", (0, 0), (0, 0), 0)])),
        ]], colWidths=[4.4 * inch, 2.6 * inch])
        row.setStyle(TableStyle([("LEFTPADDING", (0, 0), (0, 0), 0),
                                 ("VALIGN", (0, 0), (-1, -1), "BOTTOM")]))
        sig_block.append(row)
    else:
        row = Table([[
            _field("Client Signature:", "", S, 1.35),
            _field("Date:", "", S, 0.55),
        ]], colWidths=[4.4 * inch, 2.6 * inch])
        row.setStyle(TableStyle([("LEFTPADDING", (0, 0), (0, 0), 0),
                                 ("VALIGN", (0, 0), (-1, -1), "BOTTOM")]))
        sig_block.append(row)
    row = Table([[
        _field("Printed Name:", client.get("client_names", ""), S, 1.15),
        _field("Phone Number:", client.get("phone", ""), S, 1.15),
    ]], colWidths=[3.5 * inch, 3.5 * inch])
    row.setStyle(TableStyle([("LEFTPADDING", (0, 0), (0, 0), 0),
                             ("VALIGN", (0, 0), (-1, -1), "BOTTOM")]))
    sig_block.append(row)
    sig_block.append(_field("Email Address:", client.get("email", ""), S, 1.15))
    sig_block.append(Spacer(1, 8))
    sig_block.append(Paragraph(_sp("ATAVIA WEDDINGS"), S["section"]))
    row = Table([[
        _field("Authorized Signature:", "", S, 1.6),
        _field("Date:", "", S, 0.55),
    ]], colWidths=[4.4 * inch, 2.6 * inch])
    row.setStyle(TableStyle([("LEFTPADDING", (0, 0), (0, 0), 0),
                             ("VALIGN", (0, 0), (-1, -1), "BOTTOM")]))
    sig_block.append(row)
    sig_block.append(_field("Printed Name / Title:",
                            ctx.get("company_signer", ""), S, 1.6))
    story.append(KeepTogether(sig_block))
    return story

# ================================================================= PUBLIC ===

def generate_contract(package_id, payment_option, client=None,
                      out_path=None, company_signer="Lauren McKinnon, Manager",
                      signwell=False, second_shooter=False, extra_hours=0,
                      discount=0, discount_code=""):
    """Render a contract PDF. Returns bytes; also writes to out_path if given.

    package_id     : one of the ids in atavia_packages.json
    payment_option : "standard" | "pif"
    client         : dict of merge fields (see _build_story) or None for blank
    signwell       : embed invisible SignWell text tags at the client
                     signature/date lines (for automated e-signature flow)
    second_shooter : bool â€” add a second photographer/videographer/shooter
                     ($500, per pricing_rules.addon_second_shooter)
    extra_hours    : int  â€” additional coverage hours purchased at booking
                     ($175/hr, per pricing_rules.addon_extra_hour; max 6)
    discount       : int  â€” pre-validated inquiry-code discount (dollars);
                     shown as its own line in the Investment Summary
    discount_code  : str  â€” the code, printed with the discount line
    """
    if package_id not in PACKAGES:
        raise ValueError(f"Unknown package_id '{package_id}'. "
                         f"Valid: {sorted(PACKAGES)}")
    if payment_option not in ("standard", "pif"):
        raise ValueError("payment_option must be 'standard' or 'pif'")

    pkg = PACKAGES[package_id]
    pricing = compute_pricing(package_id, second_shooter, extra_hours,
                              discount)
    total = pricing["total"]
    family = {"photo": "Photography Collection",
              "video": "Videography Collection",
              "combined": "Combined Collection"}[pkg["service_type"]]
    ctx = {
        "pkg": pkg,
        "service_type": pkg["service_type"],
        "nouns": SERVICE_NOUN[pkg["service_type"]],
        "payment_option": payment_option,
        "second_shooter": bool(second_shooter),
        "extra_hours": int(extra_hours or 0),
        "addons": pricing["addons"],
        "discount": pricing["discount"],
        "discount_code": (discount_code or "").strip().upper(),
        "base_total": pricing["base_total"],
        "addons_total": pricing["addons_total"],
        "coverage_hours": pricing["coverage_hours"],
        "total": total,
        "balance": total - RULES["retainer"],
        "pif_total": total - RULES["pif_discount"],
        "client": client,
        "collection_family": family,
        "company_signer": company_signer,
        "signwell": signwell,
    }

    import io
    buf = io.BytesIO()
    doc = BaseDocTemplate(
        buf, pagesize=letter,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.7 * inch, bottomMargin=0.85 * inch,
        title=f"Atavia Weddings Service Agreement \u2014 {pkg['name']}",
        author=BRAND["parent_company"],
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height,
                  id="main")
    doc.addPageTemplates([PageTemplate(
        id="page", frames=[frame],
        onPage=lambda c, d: _header_footer(c, d, ctx))])
    doc.build(_build_story(ctx))
    pdf = buf.getvalue()
    if out_path:
        with open(out_path, "wb") as f:
            f.write(pdf)
    return pdf

# ==================================================================== CLI ===

if __name__ == "__main__":
    args = sys.argv[1:]
    outdir = os.path.join(BASE_DIR, "generated")
    os.makedirs(outdir, exist_ok=True)
    # add-on flags usable with any invocation:
    #   --second-shooter      add the second shooter
    #   --extra-hours N       add N additional hours
    ss = "--second-shooter" in args
    eh = 0
    if "--extra-hours" in args:
        eh = int(args[args.index("--extra-hours") + 1])
    args = [a for i, a in enumerate(args)
            if a not in ("--second-shooter", "--extra-hours")
            and not (i > 0 and args[i - 1] == "--extra-hours")]
    suffix = (("_ss" if ss else "") + (f"_eh{eh}" if eh else ""))
    if args and args[0] == "--all":
        stamp = datetime.now().strftime("%Y%m%d")
        for pid in PACKAGES:
            for opt in ("standard", "pif"):
                fn = os.path.join(
                    outdir, f"Atavia_{pid}_{opt}{suffix}_{stamp}.pdf")
                generate_contract(pid, opt, out_path=fn,
                                  second_shooter=ss, extra_hours=eh)
                print("wrote", fn)
    elif args and args[0] == "--addon-samples":
        # one representative per service family, fully loaded, both plans
        stamp = datetime.now().strftime("%Y%m%d")
        for pid in ("garden", "reverie", "heirloom"):
            for opt in ("standard", "pif"):
                fn = os.path.join(
                    outdir, f"Atavia_{pid}_{opt}_ss_eh2_{stamp}.pdf")
                generate_contract(pid, opt, out_path=fn,
                                  second_shooter=True, extra_hours=2)
                print("wrote", fn)
    elif len(args) >= 2:
        fn = os.path.join(outdir, f"Atavia_{args[0]}_{args[1]}{suffix}.pdf")
        generate_contract(args[0], args[1], out_path=fn,
                          second_shooter=ss, extra_hours=eh)
        print("wrote", fn)
    else:
        print("usage: python atavia_contract_generator.py --all [--second-shooter] [--extra-hours N]")
        print("       python atavia_contract_generator.py <package_id> <standard|pif> [--second-shooter] [--extra-hours N]")
        print("       python atavia_contract_generator.py --addon-samples")
        print("packages:", ", ".join(sorted(PACKAGES)))
