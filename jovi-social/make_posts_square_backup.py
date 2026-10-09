"""Renders 30 Instagram/Facebook feed posts (1080x1080) for the Jovi launch runway, plus captions.
Run: python make_posts.py   → out/NN-slug.png, captions.md, captions.csv, contact-sheet.png
Brand: navy #0B1426/#1A2744, coral #FF6B4A, mint #00D4AA, gold #FFD166, ivory #FBF7F3. Sora display, DM Sans body.
"""
import csv, pathlib, textwrap
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "out"; OUT.mkdir(exist_ok=True)
IMG = pathlib.Path("C:/Users/kurvh/jovi-site/assets/img")
W = H = 1080
NAVY, NAVY2, CORAL, MINT, GOLD, IVORY, WHITE = (11, 20, 38), (26, 39, 68), (255, 107, 74), (0, 212, 170), (255, 209, 102), (251, 247, 243), (255, 255, 255)
INK = (19, 27, 46)

def font(kind, size, weight):
    f = ImageFont.truetype(str(ROOT / "fonts" / ("Sora.ttf" if kind == "sora" else "DMSans.ttf")), size)
    f.set_variation_by_name(weight)
    return f

LOGO_W = Image.open(IMG / "jovi-logo-white.png").convert("RGBA")
LOGO_N = Image.open(IMG / "jovi-logo-navy.png").convert("RGBA")

def logo(canvas, white=True, x=64, y=56, h=54):
    src = LOGO_W if white else LOGO_N
    w = int(src.width * h / src.height)
    canvas.alpha_composite(src.resize((w, h), Image.LANCZOS), (x, y))

def cover(path, box=(W, H), darken=0.0):
    im = Image.open(IMG / path).convert("RGB"); bw, bh = box
    s = max(bw / im.width, bh / im.height); im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS)
    l = (im.width - bw) // 2; t = (im.height - bh) // 2; im = im.crop((l, t, l + bw, t + bh)).convert("RGBA")
    if darken: im = Image.alpha_composite(im, Image.new("RGBA", box, (11, 20, 38, int(255 * darken))))
    return im

def gradient(box, top, bottom, alpha_top=255, alpha_bottom=255):
    bw, bh = box; g = Image.new("RGBA", box)
    px = g.load()
    for y in range(bh):
        t = y / max(1, bh - 1); c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)); a = int(alpha_top + (alpha_bottom - alpha_top) * t)
        for x in range(bw): px[x, y] = (*c, a)
    return g

def check(d, x, y, s=22, col=WHITE, w=5):
    d.line((x, y + s * 0.55, x + s * 0.38, y + s), fill=col, width=w); d.line((x + s * 0.38, y + s, x + s, y + s * 0.15), fill=col, width=w)
def cross(d, x, y, s=20, col=CORAL, w=5):
    d.line((x, y, x + s, y + s), fill=col, width=w); d.line((x + s, y, x, y + s), fill=col, width=w)

def wrap(draw, text, f, maxw):
    lines = []
    for para in text.split("\n"):
        words = para.split(" "); cur = ""
        for w in words:
            test = (cur + " " + w).strip()
            if draw.textlength(test, font=f) <= maxw: cur = test
            else: lines.append(cur); cur = w
        lines.append(cur)
    return lines

def text_block(draw, xy, text, f, fill, maxw, lh=1.12, align="left"):
    x, y = xy; lines = wrap(draw, text, f, maxw); size = f.size
    for ln in lines:
        if align == "center": tx = x + (maxw - draw.textlength(ln, font=f)) / 2
        else: tx = x
        draw.text((tx, y), ln, font=f, fill=fill); y += int(size * lh)
    return y

def pill(draw, xy, text, f, fg, bg, padx=22, pady=12):
    x, y = xy; tw = draw.textlength(text, font=f); h = f.size + pady * 2
    draw.rounded_rectangle((x, y, x + tw + padx * 2, y + h), radius=h // 2, fill=bg)
    draw.text((x + padx, y + pady - 2), text, font=f, fill=fg)
    return y + h

def footer(draw, canvas, dark=True):
    f = font("dm", 26, "Medium"); col = (255, 255, 255, 160) if dark else (19, 27, 46, 140)
    draw.text((64, H - 84), "jovihealth.com  ·  AZ · FL · TX", font=f, fill=col)
    f2 = font("dm", 22, "Regular"); draw.text((64, H - 50), "A healthcare membership, not insurance.", font=f2, fill=(255, 255, 255, 110) if dark else (19, 27, 46, 110))

# ── Templates ──────────────────────────────────────────────────────────────
def photo_card(bg, eyebrow, headline, sub=None, accent=CORAL, darken=0.55):
    c = cover(bg, darken=0.15); c.alpha_composite(gradient((W, H), NAVY, NAVY, 0, int(255 * 0.95)))
    c.alpha_composite(gradient((W, H), NAVY, NAVY, int(255 * darken), 0).transpose(Image.FLIP_TOP_BOTTOM).crop((0, 0, W, 420)), (0, 0))
    d = ImageDraw.Draw(c); logo(c)
    y = 560
    if eyebrow: pill(d, (64, y - 70), eyebrow.upper(), font("sora", 22, "SemiBold"), NAVY, accent)
    y = text_block(d, (64, y), headline, font("sora", 78, "ExtraBold"), WHITE, 952, 1.05)
    if sub: text_block(d, (64, y + 18), sub, font("dm", 34, "Medium"), (255, 255, 255, 215), 900, 1.3)
    footer(d, c); return c

def stat_card(number, line, sub=None, bg=NAVY, num_color=CORAL, photo=None):
    c = Image.new("RGBA", (W, H), bg)
    if photo: p = cover(photo, (W, 420), darken=0.35); c.alpha_composite(p, (0, H - 420)); c.alpha_composite(gradient((W, 200), bg, bg, 255, 0), (0, H - 420))
    d = ImageDraw.Draw(c); logo(c)
    f = font("sora", 210 if len(number) <= 4 else 150, "ExtraBold"); d.text((64, 200), number, font=f, fill=num_color)
    y = 200 + f.size + 30
    y = text_block(d, (64, y), line, font("sora", 56, "Bold"), WHITE, 952, 1.1)
    if sub: text_block(d, (64, y + 14), sub, font("dm", 32, "Medium"), (255, 255, 255, 200), 900, 1.3)
    footer(d, c); return c

def list_card(title, items, bg_photo=None, accent=MINT):
    c = Image.new("RGBA", (W, H), IVORY); d = ImageDraw.Draw(c)
    top = 400; d.rectangle((0, 0, W, top), fill=NAVY)
    if bg_photo: p = cover(bg_photo, (W, top), darken=0.55); c.alpha_composite(p, (0, 0))
    d = ImageDraw.Draw(c); logo(c)
    text_block(d, (64, 150), title, font("sora", 62, "ExtraBold"), WHITE, 952, 1.06)
    y = top + 56
    for it in items:
        d.ellipse((64, y + 10, 64 + 34, y + 44), fill=accent); check(d, 72, y + 17, s=18, col=NAVY, w=4)
        y = text_block(d, (124, y), it, font("dm", 36, "Medium"), INK, 880, 1.25) + 22
    footer(d, c, dark=False); return c

def quote_card(quote, who, where, bg=CORAL):
    c = Image.new("RGBA", (W, H), bg); d = ImageDraw.Draw(c); logo(c)
    d.text((64, 190), "\u201c", font=font("sora", 200, "ExtraBold"), fill=(255, 255, 255, 120))
    y = text_block(d, (64, 330), quote, font("sora", 46, "SemiBold"), WHITE, 952, 1.25)
    d.text((64, y + 40), who, font=font("sora", 34, "Bold"), fill=WHITE); d.text((64, y + 86), where, font=font("dm", 30, "Medium"), fill=(255, 255, 255, 200))
    footer(d, c); return c

def compare_card(title, rows):
    c = Image.new("RGBA", (W, H), NAVY); d = ImageDraw.Draw(c); logo(c)
    text_block(d, (64, 150), title, font("sora", 58, "ExtraBold"), WHITE, 952, 1.06)
    y = 330; colx = [64, 560, 800]
    d.text((colx[1], y), "Jovi", font=font("sora", 30, "Bold"), fill=MINT); d.text((colx[2], y), "Insurance", font=font("sora", 30, "Bold"), fill=(255, 255, 255, 160)); y += 64
    for label, a, b in rows:
        d.line((64, y - 14, W - 64, y - 14), fill=(255, 255, 255, 30), width=2)
        d.text((colx[0], y), label, font=font("dm", 32, "Medium"), fill=WHITE)
        for cx, v in ((colx[1], a), (colx[2], b)):
            if v == "✓": check(d, cx + 4, y + 4, s=26, col=MINT, w=6)
            elif v == "✕": cross(d, cx + 6, y + 6, s=24, col=CORAL, w=6)
            else: d.text((cx + 2, y - 8), "~", font=font("sora", 40, "Bold"), fill=GOLD)
        y += 74
    footer(d, c); return c

def price_card(title, rows, total):
    c = Image.new("RGBA", (W, H), IVORY); d = ImageDraw.Draw(c); logo(c, white=False)
    text_block(d, (64, 150), title, font("sora", 58, "ExtraBold"), INK, 952, 1.06)
    y = 330
    for label, val in rows:
        d.text((64, y), label, font=font("dm", 36, "Medium"), fill=INK); tw = d.textlength(val, font=font("sora", 36, "Bold")); d.text((W - 64 - tw, y), val, font=font("sora", 36, "Bold"), fill=INK)
        d.line((64, y + 60, W - 64, y + 60), fill=(19, 27, 46, 30), width=2); y += 84
    d.rounded_rectangle((64, y + 20, W - 64, y + 170), radius=26, fill=NAVY)
    d.text((96, y + 58), "Your monthly membership", font=font("dm", 32, "Medium"), fill=(255, 255, 255, 200))
    tw = d.textlength(total, font=font("sora", 70, "ExtraBold")); d.text((W - 96 - tw, y + 44), total, font=font("sora", 70, "ExtraBold"), fill=CORAL)
    footer(d, c, dark=False); return c

# ── Content calendar ───────────────────────────────────────────────────────
HASH = "#JoviHealth #HealthcareMembership #NoSurpriseBills #DirectCare #Arizona #Florida #Texas #HealthcareReimagined"
POSTS = [
 (1, "coming-soon", lambda: photo_card("clinic-exterior.webp", "Coming soon", "Healthcare that's better than insurance.", "One monthly membership. Any doctor. $0 co-pays at Jovi Clinics."),
  "Something better is coming to Arizona, Florida, and Texas.\n\nJovi is a healthcare membership, not insurance. One monthly price you understand, any doctor you want, and $0 co-pays when you walk into a Jovi Clinic.\n\nFollow along. Launch is close.\n\n" + HASH),
 (2, "one-price", lambda: stat_card("1", "monthly price. That's the whole bill.", "No deductible games, no networks, no surprise bills.", photo="lobby.webp"),
  "Here's the entire pricing model: your age sets a monthly price. Add dental or vision if you want them. Add your family and your pets. That's it.\n\nNo open enrollment. No fine print. Cancel any time.\n\n" + HASH),
 (3, "zero-copay", lambda: stat_card("$0", "co-pay at every Jovi Clinic visit.", "Primary care, urgent visits, labs, IV therapy, and more.", num_color=MINT, photo="exam-room-3.webp"),
  "Walk in. Get seen. Walk out. No bill later.\n\nMembers pay $0 at Jovi Clinics for primary care, sick visits, wellness exams, and more. If a service ever costs extra, we tell you before, never after.\n\n" + HASH),
 (4, "any-doctor", lambda: photo_card("hallway.webp", "Your choice", "Keep your own doctor. We'll pay you back.", "See any provider, pharmacy, or hospital. Snap the receipt in the app.", accent=MINT),
  "You're never locked in. Prefer your own doctor, pharmacy, or hospital? Pay out of pocket, photograph the receipt in the Jovi app, and we reimburse you directly. Members save up to 70% on care.\n\n" + HASH),
 (5, "save-70", lambda: stat_card("70%", "Up to 70% saved on care vs. traditional insurance billing.", "We pass the savings to you, not to a middleman.", num_color=GOLD),
  "Insurance billing adds cost at every step: networks, prior authorizations, denials, appeals. Jovi removes the middleman and pays your provider directly. Up to 70% saved on care.\n\n" + HASH),
 (6, "membership-not-insurance", lambda: compare_card("Membership vs. insurance", [("Predictable monthly cost", "✓", "~"), ("$0 co-pays at Jovi Clinics", "✓", "✕"), ("No surprise bills", "✓", "✕"), ("See any provider", "✓", "~"), ("Same-day & walk-in care", "✓", "✕"), ("Pets on the same plan", "✓", "✕")]),
  "Jovi is not insurance, and that's the point. Here's how the two compare on the things that actually matter when you're sick.\n\nQuestions? Ask below. We answer every one.\n\n" + HASH),
 (7, "pricing-individual", lambda: price_card("What a 30-year-old pays", [("Membership (ages 30–39)", "$200"), ("Dental (optional)", "+$35"), ("Vision (optional)", "+$15")], "$250/mo"),
  "Transparent pricing means we'll post it. A member in their 30s pays $200 a month. Dental and vision are optional add-ons. Estimate yours at jovihealth.com.\n\n" + HASH),
 (8, "pricing-family", lambda: price_card("A family of four", [("Two adults (40s)", "$500"), ("Two kids", "$300"), ("One 3-year-old dog", "$74")], "$874/mo"),
  "Everyone in the house on one plan, including the dog. Each person is priced by their own age, so you always know exactly what you pay.\n\nRun your own numbers on jovihealth.com. No signup needed.\n\n" + HASH),
 (9, "pets-intro", lambda: photo_card("jovi-pets-lobby.webp", "Jovi Pets", "Your pets are family. Now they're on the plan.", "Accident and illness coverage, 90% back after a $500 deductible.", accent=CORAL),
  "Meet Jovi Pets. Add dogs and cats to your membership from $60 a month. Any licensed vet, 90% reimbursed after a $500 deductible that never touches yours.\n\nVet visits, vaccinations, medications, and claims all live in the same app as your own care.\n\n" + HASH + " #JoviPets #PetInsurance #DogsOfInstagram #CatsOfInstagram"),
 (10, "app-refills", lambda: list_card("Refills, handled in the app", ["Request a refill in two taps", "Send it to any pharmacy near you", "See hours and whether it's open now", "Compare GoodRx prices before pickup"], bg_photo="exam-room-1.webp"),
  "Running low? Request a refill from the Jovi app, pick any pharmacy near you, and get a notification when it's ready. Check GoodRx cash prices before you go.\n\n" + HASH + " #Pharmacy"),
 (11, "clinic-tour-lobby", lambda: photo_card("lobby.webp", "Step inside", "A clinic designed to feel different.", "Calm, modern, and welcoming. More wellness space than waiting room."),
  "This is what a Jovi Clinic looks like. Complimentary hydration bar, check in ahead so you're not shuffling in a waiting room, and a care team that knows your name.\n\nRenderings shown. Locations opening across AZ, FL, and TX.\n\n" + HASH + " #ClinicDesign"),
 (12, "included-services", lambda: list_card("Included with membership", ["Full blood panel, yearly", "IV therapy, monthly", "Vitamin shot, monthly", "Body composition scan, quarterly", "Red light therapy, monthly"], bg_photo="iv-lounge.webp"),
  "These aren't upsells. They're included. Labs, IV therapy, vitamin shots, body composition, and red light therapy come with your membership at Jovi Clinics.\n\n" + HASH + " #IVTherapy #Wellness"),
 (13, "jovi-pass", lambda: stat_card("0–5", "minute wait with Jovi Pass.", "A $49 one-time add-on that puts you at the front of the line.", num_color=MINT),
  "Need to be seen now? Jovi Pass moves you to the front of the line for a single visit, with an estimated wait of 0 to 5 minutes. $49, one time, only when you want it.\n\n" + HASH),
 (14, "quote-emily", lambda: quote_card("I know exactly what I pay each month, and the care is outstanding. I only wish I'd signed up sooner.", "Emily T.", "Phoenix, AZ"),
  "Members like Emily are why we built Jovi. Predictable cost. Real providers. No dread.\n\n" + HASH + " #MemberStory"),
 (15, "telehealth", lambda: photo_card("exam-room-2.webp", "From your couch", "Video visits, when you don't need to come in.", "Book telehealth from the app. In-person follow-up if you need it.", accent=MINT),
  "Some things don't need a drive. Book a video visit from the Jovi app and see a licensed provider from home. If you need to be seen in person, we'll get you in.\n\n" + HASH + " #Telehealth"),
 (16, "no-surprise-bills", lambda: stat_card("0", "surprise bills. Ever.", "If something costs extra, you hear it before, not after.", num_color=CORAL, photo="hallway.webp"),
  "The envelope that shows up three weeks after a visit? Not a thing here. At Jovi you know the cost before care happens, and clinic visits are $0 for members.\n\n" + HASH),
 (17, "how-it-works", lambda: list_card("How Jovi works", ["Join in minutes in the app", "Walk into a Jovi Clinic or book telehealth", "Or see any provider you like", "Snap the receipt, get reimbursed"], accent=CORAL),
  "Four steps, no insurance card.\n1. Join in the app.\n2. Walk into a Jovi Clinic or book a video visit.\n3. Or keep seeing your own doctor.\n4. Snap the receipt and get paid back.\n\n" + HASH),
 (18, "family", lambda: photo_card("kids-corner.webp", "Whole family", "One plan for everyone at your table.", "Spouse, kids, and pets, each priced by age, one bill."),
  "Add a spouse and dependents under 26 to one membership. Everyone gets their own price by age, you get one bill, and the whole household's care lives in one app.\n\n" + HASH + " #FamilyHealth"),
 (19, "deductible", lambda: list_card("A deductible you can actually meet", ["$1,500 through age 26", "$2,000 through 45", "$2,500 through 60", "$3,000 after that", "Track it live in the app"]),
  "Your deductible is set by age and designed to be reached, not dodged. The app shows your progress on a status bar. Once it's met, Jovi covers eligible expenses.\n\n" + HASH),
 (20, "quote-michael", lambda: quote_card("Quality care for a flat monthly fee. No co-pays, no hidden costs. It finally puts me in control.", "Michael R.", "Tampa, FL", bg=NAVY2),
  "Michael switched from a high-deductible plan with surprise bills. Now he pays one flat fee and knows what he gets.\n\n" + HASH + " #MemberStory"),
 (21, "pets-app", lambda: list_card("Jovi Pets, in the app", ["Vaccination reminders 30, 7, and 0 days out", "Medication schedules and dose logging", "Weight alerts by breed", "Pet claims with a photo of the invoice"], bg_photo="jovi-pets-lobby.webp", accent=CORAL),
  "Your dog's rabies booster, your cat's meds, the vet invoice from last week. All in the same app as your own care, with reminders so nothing slips.\n\n" + HASH + " #JoviPets #PetHealth"),
 (22, "records", lambda: photo_card("exam-room-1.webp", "Your records", "Every visit, prescription, and result in one timeline.", "Export the whole thing as a PDF whenever you want.", accent=MINT),
  "Your health history should belong to you. In the Jovi app, visits, prescriptions, vaccinations, vitals, and lab results sit in one timeline, and you can export all of it as a PDF in one tap.\n\n" + HASH),
 (23, "states", lambda: stat_card("3", "states at launch: Arizona, Florida, Texas.", "Clinics opening in each as the community grows.", num_color=GOLD, photo="clinic-exterior.webp"),
  "We're launching in Arizona, Florida, and Texas. Members are the first to know when a clinic opens near them.\n\nWhere should we open next? Tell us below.\n\n" + HASH + " #Phoenix #Tampa #Dallas #Scottsdale #Austin"),
 (24, "care-team", lambda: photo_card("hallway.webp", "Real people", "Licensed providers. Never a bot, never a call center.", "A care team that knows you by name.", accent=CORAL),
  "Message your care team from the app and a real clinician answers. Same faces at every visit, so you're never starting over with a stranger.\n\n" + HASH),
 (25, "symptom-checker", lambda: list_card("Not sure if you need to be seen?", ["Describe what's going on in the app", "Get guidance in plain English", "Book a visit or a video call in one tap", "Urgent? We tell you straight away"], bg_photo="exam-room-3.webp", accent=GOLD),
  "The Jovi symptom checker helps you figure out whether it can wait, needs a visit, or needs urgent care right now. Then it books the visit for you.\n\nIt's guidance, not a diagnosis. A real provider is always one tap away.\n\n" + HASH),
 (26, "cancel-anytime", lambda: stat_card("0", "contracts. Cancel from the app any time.", "Coverage runs to the end of your billing period. Nothing after.", num_color=MINT),
  "No annual lock-in, no phone tree to cancel. If Jovi stops being right for you, cancel in the app. Your coverage continues through the end of the period you paid for.\n\n" + HASH),
 (27, "quote-james", lambda: quote_card("One predictable monthly fee, no networks, no referrals, no surprise bills. Peace of mind.", "James R.", "Austin, TX"),
  "James put it better than we could.\n\n" + HASH + " #MemberStory #Austin"),
 (28, "faq-insurance", lambda: list_card("Is Jovi insurance?", ["No. Jovi is a healthcare membership.", "One monthly fee for access to care", "$0 co-pays at Jovi Clinics", "Reimbursement anywhere else", "Simpler by design"], accent=CORAL),
  "The most common question we get: is this insurance? No. Jovi is a healthcare membership. It gives you affordable, transparent access to care without networks, referrals, or surprise bills. It does not satisfy an individual coverage mandate.\n\n" + HASH),
 (29, "countdown", lambda: photo_card("lobby.webp", "Almost here", "The Jovi app launches soon.", "iOS and Android. Follow for the release date."),
  "We're in final testing. The Jovi app is coming to the App Store and Google Play. Turn on notifications so you don't miss launch day.\n\n" + HASH + " #ComingSoon #AppLaunch"),
 (30, "join", lambda: stat_card("Join", "the membership that's better than insurance.", "See your price in 30 seconds at jovihealth.com", num_color=CORAL, photo="clinic-exterior.webp"),
  "Ready? See what your membership would cost, no signup needed, at jovihealth.com. Then watch for the app.\n\nWelcome to Jovi.\n\n" + HASH),
]

rows = []
sheet = Image.new("RGB", (6 * 360, 5 * 360), (245, 246, 249))
for i, (n, slug, make, caption) in enumerate(POSTS):
    im = make().convert("RGB"); name = f"{n:02d}-{slug}.png"; im.save(OUT / name, optimize=True)
    sheet.paste(im.resize((350, 350), Image.LANCZOS), ((i % 6) * 360 + 5, (i // 6) * 360 + 5))
    rows.append((n, name, caption)); print("rendered", name)
sheet.save(ROOT / "contact-sheet.png", optimize=True)

with open(ROOT / "captions.md", "w", encoding="utf-8") as f:
    f.write("# Jovi launch runway: 30 posts\n\nPost one per day, feed post on Instagram and Facebook (same image, same caption). Stories: reuse the image with a 'Learn more' link sticker to jovihealth.com. Best times for this audience: 7–8 am or 6–8 pm local.\n\n")
    for n, name, cap in rows: f.write(f"## Day {n} · {name}\n\n{cap}\n\n---\n\n")
with open(ROOT / "captions.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f); w.writerow(["day", "image", "caption"]); [w.writerow(r) for r in rows]
print("done", len(rows))
