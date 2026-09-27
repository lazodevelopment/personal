#!/usr/bin/env python3
# ============================================================================
# ROVEN - resume_templates.py
# Build ID: JC-ROVEN-RESUMETPL-0730-002
#
# ATS-safe resume PDFs. Design rules, all deliberate:
#   - SINGLE COLUMN. Multi-column layouts are the single most common reason
#     an applicant tracking system mangles a resume.
#   - Real selectable text, no images of text, no text inside table cells
#     used for layout.
#   - Standard section headings ("Experience", "Education", "Skills") because
#     parsers look for exactly those words.
#   - Core PDF fonts only (Helvetica / Times) - no embedded font surprises.
#   - No headers/footers: many parsers drop them entirely.
#   - No watermark. It is the candidate's document.
# ============================================================================

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate,
                                Paragraph, Spacer, HRFlowable, KeepTogether)

INK = colors.HexColor("#16202E")
GREEN = colors.HexColor("#1CA45F")
GREY = colors.HexColor("#4A5568")
RULE = colors.HexColor("#C9D2DA")


# ---------------------------------------------------------------- helpers

def _esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def _styles(template):
    """Per-template type scale. Body stays >= 9.5pt for readability."""
    if template == "compact":
        name_sz, sec_sz, body_sz, lead = 20, 10.5, 9.5, 12.4
        gap_before, gap_after = 11, 4
    elif template == "modern":
        name_sz, sec_sz, body_sz, lead = 25, 11.5, 10, 13.6
        gap_before, gap_after = 15, 6
    else:  # clean
        name_sz, sec_sz, body_sz, lead = 23, 11, 10, 13.4
        gap_before, gap_after = 14, 5

    accent = GREEN if template == "modern" else INK
    return {
        "name": ParagraphStyle("name", fontName="Helvetica-Bold",
                               fontSize=name_sz, leading=name_sz * 1.12,
                               textColor=INK, spaceAfter=3),
        "contact": ParagraphStyle("contact", fontName="Helvetica",
                                  fontSize=body_sz - 0.5,
                                  leading=(body_sz - 0.5) * 1.35,
                                  textColor=GREY, spaceAfter=2),
        "section": ParagraphStyle("section", fontName="Helvetica-Bold",
                                  fontSize=sec_sz, leading=sec_sz * 1.2,
                                  textColor=accent,
                                  spaceBefore=gap_before,
                                  spaceAfter=gap_after),
        "role": ParagraphStyle("role", fontName="Helvetica-Bold",
                               fontSize=body_sz + 0.5,
                               leading=(body_sz + 0.5) * 1.3,
                               textColor=INK, spaceAfter=1),
        "meta": ParagraphStyle("meta", fontName="Helvetica-Oblique",
                               fontSize=body_sz - 0.5,
                               leading=(body_sz - 0.5) * 1.3,
                               textColor=GREY, spaceAfter=3),
        "body": ParagraphStyle("body", fontName="Helvetica", fontSize=body_sz,
                               leading=lead, textColor=INK, alignment=TA_LEFT,
                               spaceAfter=2),
        "bullet": ParagraphStyle("bullet", fontName="Helvetica",
                                 fontSize=body_sz, leading=lead,
                                 textColor=INK, leftIndent=12,
                                 bulletIndent=2, spaceAfter=1.5),
        "_accent": accent,
        "_gap": gap_after,
    }


def _rule(template, accent):
    if template == "compact":
        return HRFlowable(width="100%", thickness=0.6, color=RULE,
                          spaceBefore=1, spaceAfter=5)
    if template == "modern":
        return HRFlowable(width="100%", thickness=1.4, color=accent,
                          spaceBefore=1, spaceAfter=6)
    return HRFlowable(width="100%", thickness=0.8, color=RULE,
                      spaceBefore=1, spaceAfter=6)


def _contact_line(c):
    bits = [c.get("email"), c.get("phone"), c.get("location")]
    bits = [_esc(b) for b in bits if b]
    links = [_esc(l) for l in (c.get("links") or []) if l]
    line = "  |  ".join(bits)
    if links:
        line += ("<br/>" if line else "") + "  |  ".join(links)
    return line


# ---------------------------------------------------------------- builder

def build_pdf(path, data, template="clean"):
    """data = {contact:{name,email,phone,location,links[]},
               summary:str, roles:[{title,company,dates,location,bullets[]}],
               education:[{school,credential,dates}], skills:[str],
               certifications:[str]}"""
    st = _styles(template)
    margin = 0.55 * inch if template == "compact" else 0.7 * inch

    doc = BaseDocTemplate(
        path, pagesize=LETTER,
        leftMargin=margin, rightMargin=margin,
        topMargin=margin, bottomMargin=margin,
        title=f"{data.get('contact', {}).get('name', 'Resume')} - Resume",
        author=data.get("contact", {}).get("name", ""),
        subject="Resume", creator="Roven")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height,
                  id="body", leftPadding=0, rightPadding=0,
                  topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame])])

    s = []
    c = data.get("contact") or {}

    # ---- header ----
    s.append(Paragraph(_esc(c.get("name") or "Your Name"), st["name"]))
    cl = _contact_line(c)
    if cl:
        s.append(Paragraph(cl, st["contact"]))
    s.append(_rule(template, st["_accent"]))

    # ---- summary ----
    if data.get("summary"):
        s.append(Paragraph("Summary", st["section"]))
        s.append(Paragraph(_esc(data["summary"]), st["body"]))

    # ---- experience ----
    roles = data.get("roles") or []
    if roles:
        s.append(Paragraph("Experience", st["section"]))
        for r in roles:
            block = []
            title = _esc(r.get("title"))
            company = _esc(r.get("company"))
            head = title if not company else f"{title} &mdash; {company}"
            block.append(Paragraph(head, st["role"]))
            meta_bits = [_esc(r.get("dates")), _esc(r.get("location"))]
            meta = "  |  ".join(b for b in meta_bits if b)
            if meta:
                block.append(Paragraph(meta, st["meta"]))
            for b in (r.get("bullets") or []):
                if not b:
                    continue
                block.append(Paragraph(_esc(b), st["bullet"],
                                       bulletText="\u2022"))
            block.append(Spacer(1, st["_gap"] + 2))
            # keep a role's heading with at least its first lines
            s.append(KeepTogether(block[:3]) if len(block) > 3 else
                     KeepTogether(block))
            if len(block) > 3:
                s.extend(block[3:])

    # ---- education ----
    edu = data.get("education") or []
    if edu:
        s.append(Paragraph("Education", st["section"]))
        for e in edu:
            cred = _esc(e.get("credential"))
            school = _esc(e.get("school"))
            head = cred if not school else f"{cred} &mdash; {school}" \
                if cred else school
            s.append(Paragraph(head, st["role"]))
            if e.get("dates"):
                s.append(Paragraph(_esc(e["dates"]), st["meta"]))

    # ---- skills ----
    skills = [x for x in (data.get("skills") or []) if x]
    if skills:
        s.append(Paragraph("Skills", st["section"]))
        s.append(Paragraph(_esc("  |  ".join(skills)), st["body"]))

    # ---- certifications ----
    certs = [x for x in (data.get("certifications") or []) if x]
    if certs:
        s.append(Paragraph("Certifications", st["section"]))
        for ct in certs:
            s.append(Paragraph(_esc(ct), st["bullet"], bulletText="\u2022"))

    doc.build(s)
    return path


TEMPLATES = {
    "clean": {
        "name": "Clean",
        "note": "Classic single-column layout. The safest choice for any "
                "applicant tracking system.",
    },
    "modern": {
        "name": "Modern",
        "note": "Same structure with a green accent rule and slightly larger "
                "type. Still fully ATS-readable.",
    },
    "compact": {
        "name": "Compact",
        "note": "Tighter spacing for long work histories. Fits more on one "
                "page without shrinking the text below readable size.",
    },
}


# ============================================================================
# COVER LETTER
# Same header treatment as the resume so the two read as a set. Business
# letter structure, single column, real text - a human reads this one, but
# plenty of employers still run it through the same parser.
# ============================================================================

def build_cover_letter_pdf(path, data, template="clean"):
    """data = {contact:{name,email,phone,location},
               date:str, recipient:{company,name,title},
               role:str, body:[paragraph strings], closing:str}"""
    st = _styles(template)
    margin = 0.75 * inch

    doc = BaseDocTemplate(
        path, pagesize=LETTER,
        leftMargin=margin, rightMargin=margin,
        topMargin=margin, bottomMargin=margin,
        title=f"{data.get('contact', {}).get('name', '')} - Cover Letter",
        author=data.get("contact", {}).get("name", ""),
        subject="Cover letter", creator="Roven")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height,
                  id="body", leftPadding=0, rightPadding=0,
                  topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame])])

    para = ParagraphStyle("letter", fontName="Helvetica", fontSize=10.5,
                          leading=15.5, textColor=INK, spaceAfter=11)
    small = ParagraphStyle("small", fontName="Helvetica", fontSize=9.5,
                           leading=13.5, textColor=GREY, spaceAfter=2)

    s = []
    c = data.get("contact") or {}
    s.append(Paragraph(_esc(c.get("name") or "Your Name"), st["name"]))
    cl = _contact_line(c)
    if cl:
        s.append(Paragraph(cl, st["contact"]))
    s.append(_rule(template, st["_accent"]))
    s.append(Spacer(1, 10))

    if data.get("date"):
        s.append(Paragraph(_esc(data["date"]), small))
        s.append(Spacer(1, 8))

    r = data.get("recipient") or {}
    lines = [r.get("name"), r.get("title"), r.get("company")]
    for ln in [x for x in lines if x]:
        s.append(Paragraph(_esc(ln), small))
    if any(lines):
        s.append(Spacer(1, 12))

    greet = "Dear Hiring Manager,"
    if r.get("name"):
        greet = f"Dear {_esc(r['name'])},"
    s.append(Paragraph(greet, para))

    for p_ in (data.get("body") or []):
        if p_:
            s.append(Paragraph(_esc(p_), para))

    s.append(Spacer(1, 6))
    s.append(Paragraph(_esc(data.get("closing") or "Sincerely,"), para))
    s.append(Spacer(1, 14))
    s.append(Paragraph(_esc(c.get("name") or ""), para))

    doc.build(s)
    return path
