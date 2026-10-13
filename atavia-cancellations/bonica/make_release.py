"""Build the Bonica cancellation & retainer-waiver release PDF, styled like the Atavia contract."""
import os, sys
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONTS = os.path.expanduser("~/atavia-functions-live/bs/contract/fonts")
pdfmetrics.registerFont(TTFont("Lato", f"{FONTS}/Lato-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Lato-B", f"{FONTS}/Lato-Bold.ttf"))
pdfmetrics.registerFont(TTFont("Lato-I", f"{FONTS}/Lato-Italic.ttf"))
pdfmetrics.registerFont(TTFont("Corm", f"{FONTS}/CormorantGaramond-var.ttf"))
COPPER = HexColor("#B87A4B")

S = {
 "brand": ParagraphStyle("brand", fontName="Corm", fontSize=26, leading=30, alignment=1, textColor=black),
 "doctitle": ParagraphStyle("dt", fontName="Lato-B", fontSize=11.5, leading=14, alignment=1, textColor=COPPER, spaceBefore=4),
 "section": ParagraphStyle("sec", fontName="Lato-B", fontSize=9.5, leading=12, textColor=COPPER, spaceBefore=12, spaceAfter=4),
 "body": ParagraphStyle("body", fontName="Lato", fontSize=9.6, leading=14, spaceAfter=7),
 "small": ParagraphStyle("small", fontName="Lato-I", fontSize=8.2, leading=11, textColor=HexColor("#555555")),
 "field": ParagraphStyle("field", fontName="Lato", fontSize=9.6, leading=14),
}

BLANK = "_______________________________"
# Fill these in from the admin before sending (or leave blanks to hand-write).
D = dict(
    client="Cathleen Bonica",
    email="Cathy@globalfitnesscenter.com",
    event_date=os.environ.get("EVENT_DATE", "October 17, 2026"),
    package=os.environ.get("PACKAGE", "The Verse — Six Hours Videography Collection"),
    total=os.environ.get("TOTAL", "$1,400.00 (retainer $500.00 paid; remaining balance $900.00 waived under this Release)"),
    retainer=os.environ.get("RETAINER", "$500.00"),
    retainer_date=os.environ.get("RETAINER_DATE", "October 5, 2026"),
    contract_date=os.environ.get("CONTRACT_DATE", "October 5, 2026 (signed electronically via SignWell, document 8ff0fc8f-3bac-4a55-8198-787dc6ced949)"),
    call_date="October 12, 2026",
)

def P(t, s="body"): return Paragraph(t, S[s])
def field(label, value):
    return P(f"<b>{label}</b>&nbsp;&nbsp;{value}", "field")

story = []
story.append(P("Atavia <i>Weddings</i>", "brand"))
story.append(P("CANCELLATION ACKNOWLEDGMENT &amp; RETAINER WAIVER", "doctitle"))
story.append(Spacer(1, 6)); story.append(HRFlowable(width="100%", thickness=0.7, color=COPPER)); story.append(Spacer(1, 8))

story.append(P(
 "This Cancellation Acknowledgment &amp; Retainer Waiver (the “Release”) is made by the Client "
 "identified below (the “Client”) in favor of Atavia Weddings, a brand of Danbren Media LLC "
 "(the “Company”), and relates to the Wedding Videography Service Agreement between the "
 "parties (the “Agreement”)."))

story.append(P("BOOKING DETAILS", "section"))
story += [field("Client Name:", D["client"]),
          field("Client Email:", D["email"]),
          field("Mailing Address:", "61 Johnny Appleseed Lane, Leominster, MA 01453"),
          field("Event Date:", D["event_date"] + " — Saltwater Farm Vineyard, Stonington, CT"),
          field("Package:", D["package"]),
          field("Agreement Date:", D["contract_date"]),
          field("Total Investment under Agreement:", D["total"]),
          field("Non-Refundable Retainer Paid:", f"{D['retainer']} on {D['retainer_date']}")]

story.append(P("1. CANCELLATION BY CLIENT", "section"))
story.append(P(
 f"On {D['call_date']} the Client notified the Company by telephone that the Client wishes to cancel "
 "the Agreement and the Company’s videography services for the Event Date above. By signing below, "
 "the Client confirms that this cancellation is voluntary, is made at the Client’s sole election, and "
 "is effective as of the date of the Client’s signature (the “Cancellation Date”). The Company "
 "accepts the cancellation and releases the Event Date, which may be offered to other clients."))

story.append(P("2. RETAINER WAIVER", "section"))
story.append(P(
 f"The Client acknowledges that the retainer of {D['retainer']} paid at reservation is non-refundable "
 "under all circumstances, as set forth in the Agreement, and was paid in consideration of the Company "
 "reserving the Event Date and declining other bookings for that date. <b>The Client knowingly and "
 "voluntarily waives any right, claim or demand to a refund, return, credit or chargeback of the retainer, "
 "in whole or in part</b>, and agrees not to dispute the retainer charge with the Client’s card issuer "
 "or bank."))

story.append(P("3. NO FURTHER CHARGES", "section"))
story.append(P(
 "The Company confirms that, upon the Cancellation Date, no remaining balance, installment or other amount "
 "is due or will be charged to the Client’s card on file under the Agreement. The Company will cancel any "
 "scheduled balance charge and any open payment link, and will not retain the Client’s payment method for "
 "future charges. The Client’s only payment under the Agreement is the retainer described above."))

story.append(P("4. NO PUBLIC REVIEW OR STATEMENT", "section"))
story.append(P(
 "The Client acknowledges that no services were performed under the Agreement and that the Client therefore "
 "has no experience of the Company’s videography services to review. <b>The Client agrees not to post, publish "
 "or cause to be posted any review, rating, comment or statement concerning the Company, its services or its "
 "personnel</b> on any review platform, wedding marketplace (including The Knot, Zola, WeddingWire, Google, Yelp "
 "and Facebook), social media or other public forum. The Company agrees not to publish any public statement "
 "concerning the Client. The Client acknowledges that this term was specifically negotiated as part of this Release "
 "and is given in exchange for the Company’s waiver of the cancellation fee otherwise payable under the "
 "Agreement. Nothing in this section prevents either party from making truthful statements to a court, government "
 "agency or card issuer in a legal proceeding, or as otherwise required by law."))

story.append(P("5. MUTUAL RELEASE", "section"))
story.append(P(
 "In exchange for the Company’s waiver of all remaining amounts and of the cancellation fee that would otherwise be payable under the "
 "Agreement, the Client releases the Company, Danbren Media LLC, and their owners, employees and contractors "
 "from any and all claims arising out of or relating to the Agreement, the booking, or its cancellation, "
 "including any claim relating to communication or scheduling prior to the Cancellation Date. The Company "
 "likewise releases the Client from any further obligation under the Agreement, including any balance, "
 "cancellation fee or liquidated damages beyond the retainer already paid. The Agreement is terminated, and "
 "neither party owes the other any further performance."))

story.append(P("6. ACKNOWLEDGMENT", "section"))
story.append(P(
 "The Client confirms that the Client has read this Release, understands it, has had the opportunity to "
 "ask questions or seek independent advice, and signs it voluntarily. This Release may be signed "
 "electronically or in counterparts, and a scanned or photographed signature is as valid as an original."))

story.append(Spacer(1, 10))
story.append(P("SIGNATURES", "section"))
sig = Table([
 [P("<b>CLIENT</b>", "field"), P("<b>ATAVIA WEDDINGS</b>", "field")],
 [Spacer(1, 26), Spacer(1, 26)],
 [P("Signature: ____________________________", "field"), P("Signature: ____________________________", "field")],
 [P(f"Printed Name: {D['client']}", "field"), P("Printed Name: ________________________", "field")],
 [P("Date: ________________________", "field"), P("Date: ________________________", "field")],
], colWidths=[3.5*inch, 3.5*inch])
sig.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 0)]))
story.append(sig)
story.append(Spacer(1, 14))
story.append(P("Atavia Weddings · ataviaweddings.com · info@ataviaweddings.com", "small"))

out = os.path.expanduser("~/atavia-cancellations/bonica/Bonica_Cancellation_Release.pdf")
SimpleDocTemplate(out, pagesize=letter, leftMargin=0.9*inch, rightMargin=0.9*inch,
                  topMargin=0.8*inch, bottomMargin=0.8*inch,
                  title="Atavia Weddings — Cancellation Acknowledgment & Retainer Waiver",
                  author="Atavia Weddings").build(story)
print(out)
