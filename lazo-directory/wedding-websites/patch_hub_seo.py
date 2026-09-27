"""patch_hub_seo.py - JC-LAZO-WWSEO-0919-003
Gives wedding-websites/index.html (the templates hub) what a page that wants
to rank needs: a keyword title, canonical + share tags, FAQPage / ItemList /
BreadcrumbList JSON-LD, and four content sections (how it works, what's
included, styles, FAQ) that say in plain words what the demos only show.
Idempotent: every insert sits between marker comments and is replaced on re-run.

  python wedding-websites\\patch_hub_seo.py
"""
import json, re, html
from pathlib import Path

ROOT = Path(__file__).resolve().parent
P = ROOT / "index.html"
THEMES = json.loads((ROOT / "themes.json").read_text(encoding="utf-8"))
HUB = "https://meetlazo.com/wedding-websites/"
TITLE = "Free Wedding Website Templates & Builder | Lazo"
N = len(THEMES)
WORDS = {13: "thirteen", 14: "fourteen", 15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen", 19: "nineteen", 20: "twenty", 21: "twenty-one", 22: "twenty-two", 24: "twenty-four"}
NWORD = WORDS.get(N, str(N))
LOOKS = {52: "fifty-two", 80: "eighty", 84: "eighty-four", 88: "eighty-eight", 96: "ninety-six"}.get(N * 4, str(N * 4))
DESC = (f"Free wedding website templates from Lazo: {N} designs, {N * 4} looks, RSVPs, schedule, registry and an optional passcode. "
        "Type your names, watch every design update live, and publish in minutes.")
OG_IMAGE = "https://meetlazo.com/assets/brand.png"

FAQ = [
 ("Are Lazo wedding websites really free?",
  "Yes. Every couple on Lazo gets a wedding website free, with every design, RSVPs, schedule, registry links and the passcode option included. There is no paid tier for couples and no card required."),
 ("How long does it take to make a wedding website?",
  "Minutes. Pick a design, type your names and date, add your venue and schedule, and share the link. Everything else, like travel notes, registry links, photos and your story, can be added whenever you have it."),
 ("What should we put on our wedding website?",
  "The things guests would otherwise text you: the date, ceremony and reception times, the venue with directions, dress code, where to stay and how to get around, how to RSVP and by when, your registry, a few photos and your story. Every Lazo design has a section for each."),
 ("Do guests need an account to RSVP?",
  "No. Guests open your link, tap RSVP, and reply with meals, plus-ones and notes. Each reply lands in your Lazo planner the moment it happens, so your headcount is always current."),
 ("Can we make our wedding website private?",
  "Yes. Add a passcode and only guests with it can open the site. Passcode sites are also kept out of search engines automatically."),
 ("Can we change the design later?",
  f"Yes. Switch between any of the {NWORD} designs and their color looks whenever you like. Your names, schedule, RSVPs and everything you have added carry over."),
 ("What happens to the site after the wedding?",
  "It keeps going. The morning after, the countdown turns into days married, a thank-you takes the RSVP's place, and you can add chapters, photos and a guestbook for as long as you want."),
 ("Does the website connect to our registry and vendors?",
  "Yes. Link any registry so guests can shop from your site, and because the website lives in your Lazo account, it sits alongside your vendors, contracts and payments."),
]

# Style chips. When a style has its own landing page, point the href there.
CHIPS = [
 ("Floral", "floral/"), ("Garden & greenery", "garden/"), ("Beach & coastal", "beach/"), ("Destination", "destination/"),
 ("Mountain", "mountain/"), ("Rustic & barn", "rustic/"), ("Vineyard", "vineyard/"), ("Fall & autumn", "fall/"),
 ("Black tie", "black-tie/"), ("Classic & elegant", "classic/"), ("Modern", "modern/"), ("Minimalist", "minimalist/"),
 ("Boho", "boho/"), ("Desert", "desert/"), ("Celestial", "celestial/"), ("Winter", "winter/"),
 ("Small wedding & elopement", "small-wedding/"), ("Romantic", "romantic/"),
 ("Watercolor", "watercolor/"), ("Geometric", "geometric/"), ("Vintage & art deco", "vintage/"), ("South Asian", "south-asian/"), ("Latin", "latin/"),
 ("With RSVP", "with-rsvp/"), ("With registry", "with-registry/"), ("Password protected", "password-protected/"),
]

INCLUDED = [
 ("RSVPs that file themselves", "Meals, plus-ones and song requests land in your planner as they arrive."),
 ("Schedule & venue", "Ceremony, cocktails, reception and send-off, with one-tap directions."),
 ("Travel & stays", "Hotel blocks, transport, parking and notes for out-of-town guests."),
 ("Registry links", "Link any registry and guests shop without leaving your site."),
 ("Photos & your story", "A gallery, how you met, and the moments you want everyone to know."),
 ("Passcode privacy", "Lock the site to guests only, and keep it out of search engines."),
 ("Your song", "Your first-dance song plays softly when guests open the site."),
 ("Nearby picks", "Eat, drink and do around the venue, your favourites first."),
 ("Married mode", "The morning after, the site flips to days married, chapters and a guestbook."),
]


def ld_json():
    items = [{"@type": "ListItem", "position": i + 1, "name": f"{t['name']} wedding website template",
              "url": f"{HUB}{slug}/"} for i, (slug, t) in enumerate(THEMES.items())]
    g = {"@context": "https://schema.org", "@graph": [
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Lazo", "item": "https://meetlazo.com/"},
            {"@type": "ListItem", "position": 2, "name": "Wedding websites", "item": HUB}]},
        {"@type": "WebPage", "@id": HUB, "url": HUB, "name": TITLE, "description": DESC,
         "isPartOf": {"@type": "WebSite", "name": "Lazo", "url": "https://meetlazo.com/"}},
        {"@type": "ItemList", "name": "Free wedding website templates", "numberOfItems": len(items), "itemListElement": items},
        {"@type": "SoftwareApplication", "name": "Lazo wedding website builder", "applicationCategory": "LifestyleApplication",
         "operatingSystem": "Web", "url": HUB,
         "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
         "featureList": [h for h, _ in INCLUDED]},
        {"@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ]},
    ]}
    return json.dumps(g, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def head_block():
    e = html.escape
    return ("<!-- lz-seo -->\n"
            f'<link rel="canonical" href="{HUB}">\n'
            '<meta property="og:type" content="website">\n<meta property="og:site_name" content="Lazo">\n'
            f'<meta property="og:url" content="{HUB}">\n<meta property="og:title" content="{e(TITLE)}">\n'
            f'<meta property="og:description" content="{e(DESC)}">\n<meta property="og:image" content="{OG_IMAGE}">\n'
            '<meta name="twitter:card" content="summary_large_image">\n'
            f'<meta name="twitter:title" content="{e(TITLE)}">\n<meta name="twitter:image" content="{OG_IMAGE}">\n'
            '<script type="application/ld+json">' + ld_json() + "</script>\n"
            "<!-- /lz-seo -->\n")


CSS = """/* lz-seo-css */
.sec{max-width:1080px;margin:0 auto;padding:76px 22px 0}
.sec .sk{font-size:11px;letter-spacing:.42em;text-transform:uppercase;color:#8A6A2F;text-align:center;margin-bottom:12px}
.sec h2{font:500 clamp(28px,4.2vw,40px)/1.15 "Cormorant Garamond",serif;color:var(--plum);text-align:center;margin:0 auto 10px;max-width:24ch}
.sec .sp{color:var(--muted);text-align:center;max-width:58ch;margin:0 auto;font-size:16px}
.steps{display:grid;gap:18px;margin-top:36px}
@media(min-width:760px){.steps{grid-template-columns:1fr 1fr 1fr}}
.step{background:#fff;border:1px solid var(--goldSoft);border-radius:18px;padding:26px 22px}
.step .n{font:600 30px/1 "Cormorant Garamond",serif;color:var(--gold)}
.step h3{font:600 21px "Cormorant Garamond",serif;color:var(--plum);margin:8px 0 6px}
.step p{font-size:14.5px;color:#6B6B66}
.incg{display:grid;gap:14px;margin-top:32px;grid-template-columns:1fr 1fr}
@media(min-width:760px){.incg{grid-template-columns:repeat(3,1fr)}}
.incg div{background:#fff;border:1px solid var(--goldSoft);border-radius:14px;padding:16px 18px}
.incg b{display:block;color:var(--plum);font-weight:500;margin-bottom:3px}
.incg span{font-size:13.5px;color:#6B6B66}
.chips{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;margin-top:26px}
.chips a{border:1px solid var(--goldSoft);border-radius:999px;padding:8px 16px;font-size:14px;text-decoration:none;color:var(--plum);background:#fff;transition:background .2s}
.chips a:hover{background:var(--wash)}
.faqs{max-width:820px}
.faqs details{border-bottom:1px solid var(--goldSoft);padding:16px 0}
.faqs details:first-of-type{margin-top:26px;border-top:1px solid var(--goldSoft)}
.faqs summary{cursor:pointer;font:400 17px "Jost",sans-serif;color:var(--plum);list-style:none;display:flex;justify-content:space-between;gap:16px}
.faqs summary::-webkit-details-marker{display:none}
.faqs summary::after{content:"+";color:var(--gold);font-size:22px;line-height:1}
.faqs details[open] summary::after{content:"\\2013"}
.faqs p{color:#6B6B66;font-size:15px;margin-top:10px;max-width:70ch}
/* /lz-seo-css */
"""


def sections():
    steps = [("Pick a design", f"{NWORD.capitalize()} designs, each with four color looks. Type your names above and every preview updates live."),
             ("Add your details", "Date, venue, schedule, travel, registry, photos and your story. Fill in what you have; add the rest later."),
             ("Share one link", "Send your meetlazo.com link. Guests RSVP on the site and every reply lands in your planner.")]
    e = html.escape
    out = ["<!-- lz-seo-sections -->",
           '<section class="sec rv" id="how">', ' <p class="sk">How it works</p>',
           ' <h2>Create a wedding website in minutes, for free</h2>',
           ' <p class="sp">No design skills, no card, no catch. A wedding website builder that lives inside the planner you use for everything else.</p>',
           ' <div class="steps">']
    out += [f'  <div class="step"><div class="n">{i+1}</div><h3>{e(h)}</h3><p>{e(p)}</p></div>' for i, (h, p) in enumerate(steps)]
    out += [' </div>', '</section>',
            '<section class="sec rv" id="included">', ' <p class="sk">Everything included</p>',
            ' <h2>One wedding website, with everything your guests will ask about</h2>',
            ' <p class="sp">Every design carries the same sections, so the only choice you make is how it looks.</p>',
            ' <div class="incg">']
    out += [f'  <div><b>{e(h)}</b><span>{e(p)}</span></div>' for h, p in INCLUDED]
    out += [' </div>', '</section>',
            '<section class="sec rv" id="styles">', ' <p class="sk">Find your style</p>',
            ' <h2>Wedding website templates for every kind of wedding</h2>',
            ' <p class="sp">Floral or minimalist, black tie or barefoot on the beach, a barn in the fall or a cabin in the snow. Start with the design closest to your day.</p>',
            ' <div class="chips">']
    out += [f'  <a href="{href}">{e(label)}</a>' for label, href in CHIPS]
    out += [' </div>', '</section>',
            '<section class="sec faqs rv" id="faq">', ' <p class="sk">Questions</p>',
            ' <h2>Wedding website FAQ</h2>']
    out += [f' <details><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in FAQ]
    out += ['</section>', '<!-- /lz-seo-sections -->', '']
    return "\n".join(out)


def rep(s, old, new, count=1):
    n = s.count(old)
    if n != count:
        raise SystemExit(f"anchor {old[:70]!r}: found {n}, wanted {count}")
    return s.replace(old, new)


s = P.read_text(encoding="utf-8")
# strip previous runs
s = re.sub(r"<!-- lz-seo -->.*?<!-- /lz-seo -->\n", "", s, flags=re.S)
s = re.sub(r"/\* lz-seo-css \*/.*?/\* /lz-seo-css \*/\n", "", s, flags=re.S)
s = re.sub(r"<!-- lz-seo-sections -->.*?<!-- /lz-seo-sections -->\n\n?", "", s, flags=re.S)

s = re.sub(r"<title>[^<]*</title>", "<title>" + html.escape(TITLE) + "</title>", s, count=1)
s = re.sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="' + html.escape(DESC, quote=True) + '">', s, count=1)
s = re.sub(r'<meta property="og:title" content="[^"]*">\n', "", s, count=1)
s = re.sub(r'<meta property="og:description" content="[^"]*">\n', "", s, count=1)
s = rep(s, '<meta name="theme-color" content="#52284F">\n', '<meta name="theme-color" content="#52284F">\n' + head_block())
s = rep(s, "</style>\n</head>", CSS + "</style>\n</head>")
s = s.replace('<p class="eyebrow">Free with every Lazo account</p>', '<p class="eyebrow">Free wedding website builder</p>', 1)
s = rep(s, '<section class="close">', sections() + '<section class="close">')
s = re.sub(r'<p class="sub">[\w-]+ designs, [\w-]+ looks,', f'<p class="sub">{NWORD.capitalize()} designs, {LOOKS} looks,', s, count=1)
s = re.sub(r'Live on all [\w-]+ previews below', f'Live on all {NWORD} previews below', s, count=1)
P.write_text(s, encoding="utf-8", newline="\n")
print(f"index.html: {len(s):,} bytes, {len(FAQ)} FAQs, {len(THEMES)} templates in ItemList")
