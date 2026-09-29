"""make_features.py - JC-LAZO-WWSEO-0929-FEATURES
Feature landing pages under /wedding-websites/{slug}/ for the things couples
actually search for and that only Lazo's site does: guest photo sharing, the
seat finder, a wedding website in Spanish (and 19 more languages), the live
day-of timeline, and a straight comparison with Zola and The Knot. Built from
the hub (index.html) the way make_styles.py builds the style pages - same
head, CSS and footer - with a screenshot, plain copy, a FAQ, three templates
and links to the other feature pages. Each is a real crawlable page with its
own title, description, canonical and JSON-LD (WebPage + FAQPage +
BreadcrumbList). sync_dist.py copies every wedding-websites/*/index.html into
dist and the templates sitemap, so nothing else needs wiring.

  python wedding-websites\\make_features.py            # all
  python wedding-websites\\make_features.py guest-photo-sharing
Then: python wedding-websites\\patch_hub_sell.py (the hub links here),
sync_dist.py, upload_r2.py --prefix wedding-websites, deploy\\indexnow.py.
"""
import json, re, sys, html
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from make_styles import CARDS, relink, HUB  # noqa: E402

HUB_URL = "https://meetlazo.com/wedding-websites/"
A = "https://meetlazo.com/assets"

FEATURES = {
 "guest-photo-sharing": dict(
  name="Guest photo sharing",
  title="Free Wedding Guest Photo Sharing on Your Wedding Website | Lazo",
  h1="Wedding guest photo sharing, built into your wedding website",
  desc="Guests add photos from their phones straight to your free wedding website - QR table cards, approval before they show, a slideshow for the TV and one zip of everything. No app, no fee, no separate site.",
  shot="ww-wall.webp", alt="A wedding website's photo wall filled with pictures guests added from their phones",
  intro=[
   "Every phone at your wedding is a camera, and most of those photos never reach you. Lazo puts a photo wall on your wedding website itself: from the wedding day on, guests tap one button, pick photos, and they land on your site for everyone to see. Nothing to install, no code to type, no separate photo-sharing site to explain at the reception.",
   "You stay in charge. Turn on approval and every photo waits for your yes. Remove anything you don't want. Put the wall on the bar TV as a full-screen slideshow that refreshes itself all night. When it's over, download the whole wall as one zip.",
  ],
  points=[
   ("QR cards, six to a page", "Print table cards that open the wall. Guests scan, tap, done."),
   ("Approve first, if you like", "Hold new photos until you've seen them, or let them fly."),
   ("The reception watches itself", "Add one word to your link and the site becomes a slideshow for a TV."),
   ("Everything in one zip", "Every photo, full size, in one download when the day is over."),
   ("Free, and part of the site", "Other tools charge $49 to $119 for this and send guests somewhere else."),
  ],
  faq=[
   ("Do guests need an app?", "No. They open your wedding website on their phone, tap Add photos, and choose from their camera roll. It works on iPhone and Android in any browser."),
   ("Can I approve photos before they show?", "Yes. Turn on Approve photos before they show and each upload waits in your dashboard until you say yes. You can also remove any photo at any time."),
   ("How do guests find the wall?", "Print the QR table cards from your dashboard, share your site link, or add it to the day-before email Lazo sends to everyone coming."),
   ("Is there a limit?", "Up to 1,000 photos per wedding, 10 MB each. Photos are resized on the guest's phone before upload, so they arrive fast."),
   ("Can I show the photos on a screen at the reception?", "Yes. Open your site with ?wall=1 on the end of the link and it becomes a full-screen slideshow that pulls in new photos as they arrive."),
  ],
  themes=["peony", "flora", "sage"],
 ),
 "find-your-table": dict(
  name="Find your table",
  title="Wedding Seating Chart Lookup on Your Website: Guests Find Their Table | Lazo",
  h1="Let guests find their table on your wedding website",
  desc="A seat finder on your free wedding website: guests type their name and see their table, seat, tablemates and a map of the room. Straight from your seating chart, no escort cards to reprint.",
  shot="ww-seat.webp", alt="A guest types their name and the wedding website shows their table, seat, tablemates and a map of the room",
  intro=[
   "Escort cards get lost, seating charts get reprinted the night before, and someone always ends up asking the coordinator. On a Lazo wedding website, guests type their name and get their table, their seat, who they're sitting with, and a small map of the room with their table lit up.",
   "It reads from the seating chart you build in the Lazo planner, so a last-minute move on your chart is a last-minute move on the site. Turn it on when the chart is final; turn it off any time.",
  ],
  points=[
   ("Name in, table out", "Works with first name, last name or the household name on the invitation."),
   ("Who they're sitting with", "The tablemates show beneath the table, so the walk over is a friendly one."),
   ("A map of the room", "Your floor plan, drawn small, with their table highlighted."),
   ("In the day-before email", "Everyone coming gets their table in the note Lazo sends the night before."),
   ("On any phone", "No app. The site is the app."),
  ],
  faq=[
   ("Where does the seating information come from?", "From the seating chart in your Lazo planner. Publish your website after the chart is final and the site reads the same tables and seats."),
   ("Can guests see the whole seating chart?", "No. They search for their own name and see their table and tablemates. There is no list of everyone."),
   ("What if a guest isn't found?", "The site suggests trying a first or last name and asking at the door. Names match loosely, so 'Rosa' finds 'Rosa Alvarez'."),
   ("Can I turn it off?", "Yes, with one switch in the website editor. It also hides itself automatically after the wedding."),
  ],
  themes=["fete", "gilded", "atelier"],
 ),
 "spanish-wedding-website": dict(
  name="In their language",
  title="Wedding Website in Spanish (and 20 Languages) for Free | Lazo",
  h1="A wedding website your whole family can read",
  desc="Free bilingual wedding website: one tap translates your site into Spanish, Hindi, Chinese, Vietnamese, Tagalog, Portuguese and more. One link for everyone, in the language they read.",
  shot="ww-spanish.webp", alt="The couple's story on a wedding website shown in Spanish after a guest picked their language",
  intro=[
   "Abuela reads it in Spanish. The cousins in Manila read it in Tagalog. Your in-laws read it in Hindi. A Lazo wedding website carries a small language pill; a guest picks their language and every line on the page, from the schedule to the RSVP form, reads in it. One link, no second site to maintain.",
   "Twenty languages are there today: Spanish, French, Portuguese, German, Italian, Hindi, Chinese, Japanese, Korean, Vietnamese, Tagalog, Arabic, Russian, Polish, Hebrew, Greek, Turkish, Dutch, Swedish and Ukrainian. Your names, your date and your photos stay exactly as you set them.",
  ],
  points=[
   ("One site, every language", "No copy to keep in sync, no second page to update when the shuttle time changes."),
   ("The RSVP too", "Dinner choices, plus-ones and the events they'll join, all translated."),
   ("Remembered on their phone", "Pick Spanish once and the site opens in Spanish next time."),
   ("Designed for multi-day weddings", "Marigold, Papel and Peony carry the weekend's events with directions and calendar links."),
  ],
  faq=[
   ("Is the translation automatic?", "Yes. When a guest picks a language, the site translates its text on the spot. Names, dates and anything you typed in another language are left as they are."),
   ("Which languages are available?", "Twenty: Spanish, French, Portuguese, German, Italian, Hindi, Chinese, Japanese, Korean, Vietnamese, Tagalog, Arabic, Russian, Polish, Hebrew, Greek, Turkish, Dutch, Swedish and Ukrainian."),
   ("Can I turn it off?", "Yes, in the website editor under Live on the day."),
   ("Does it cost anything?", "No. Every Lazo wedding website is free, including translation."),
  ],
  themes=["papel", "marigold", "peony"],
 ),
 "day-of-timeline": dict(
  name="Day-of timeline",
  title="Wedding Day Timeline on Your Website, Live on the Day | Lazo",
  h1="A wedding website that knows what's happening right now",
  desc="Your wedding day timeline on your free wedding website: hour by hour for guests, marking what's happening now and what's next on the day, with the forecast, directions and one-tap add-to-calendar.",
  shot="ww-hourbyhour.webp", alt="The wedding day hour by hour on the website, with the current moment marked Now and the next marked Next",
  intro=[
   "When is dinner? Where do we go after the ceremony? Is the shuttle back at ten or eleven? On a Lazo wedding website the timeline you plan in your dashboard becomes the guests' schedule, and on the wedding day it marks the moment you're in and the one that's next, so nobody has to ask.",
   "Inside two weeks the site adds the forecast for your venue with one plain line of advice. Directions to the venue and to the hotel are one tap. Guests can add the whole day to their calendar, and the night before, Lazo emails everyone the schedule, the map, parking and their table.",
  ],
  points=[
   ("Now and Next, on the day", "The list updates itself every half minute."),
   ("The forecast, in plain words", "High, low, rain odds, sunset, and 'bring a layer for the evening'."),
   ("Directions that open the phone's maps", "The venue and the hotel, one tap."),
   ("The whole day in a calendar", "One .ics with every moment, or the ceremony in Google Calendar."),
   ("The day-before note", "One email to everyone coming, with their own table in it."),
  ],
  faq=[
   ("Do I have to build the timeline twice?", "No. Build it once on the Day-of screen in your Lazo planner. Publishing your website copies it over, minus vendor-only moments like load-in."),
   ("What does the site show before the wedding day?", "The same schedule, without the Now and Next markers. Those appear on the day itself."),
   ("Where does the forecast come from?", "Open-Meteo, for your venue's location, inside 16 days of the date. Further out the site shows nothing rather than a guess."),
   ("Can I keep some moments private?", "Yes. Moments owned by your vendors (setup, sound check, first look with the photographer) are left off the guest schedule automatically."),
  ],
  themes=["summit", "tide", "noir"],
 ),
 "vs-zola-the-knot": dict(
  name="Lazo vs Zola vs The Knot",
  title="Lazo vs Zola vs The Knot: Free Wedding Websites Compared (2026) | Lazo",
  h1="Lazo vs Zola vs The Knot wedding websites",
  desc="An honest comparison of free wedding website builders. What Zola and The Knot do well, and the ten things a Lazo wedding website does that they don't: guest photos, a seat finder, a live timeline, translation and more.",
  shot="ww-hero.webp", alt="A Lazo wedding website header with the couple's own photo",
  intro=[
   "Zola and The Knot make good wedding websites. They are free, the designs are lovely, RSVPs work, and registries link. If you want a page that says who, when and where, either will do. This page is about what happens after the invitation goes out.",
   "A Lazo wedding website lives in the same account as your guest list, seating chart, timeline and vendors. That is why it can do things a brochure can't: let guests add photos from their phones, tell each guest their table, mark what's happening right now on the day, translate itself for family abroad, and keep going after the wedding with chapters and a guestbook.",
  ],
  points=[
   ("Both have", "Designs, RSVPs, registry links, travel details, a passcode, a free plan."),
   ("Only Lazo", "Guest photo wall with approval, slideshow and zip. Find your table with a room map. Hour by hour with Now and Next. The venue forecast. Twenty languages. Vendor credits you can book from. Days-married mode, chapters and a guestbook. No upsells."),
   ("The honest caveat", "Zola sells invitations and a registry of its own; The Knot has the biggest vendor directory in the country. Lazo's directory is 119,000 vendors and growing, and Lazo never sells you paper."),
  ],
  faq=[
   ("Is Lazo really free?", "Yes. No plan, no card, no ads on your site, no premium tier for features. Lazo makes money when vendors upgrade their profiles, not from couples."),
   ("Can I bring my guest list from Zola or The Knot?", "Yes. Export the CSV from either and import it in the Lazo planner; names, emails, meals and RSVP status come with it."),
   ("Can I use my own domain?", "Your site lives at meetlazo.com/w/your-names. A custom domain is on the roadmap."),
   ("What does Zola do that Lazo doesn't?", "Zola sells matching paper invitations and runs its own registry store. Lazo links to any registry and doesn't sell paper."),
  ],
  themes=["peony", "fete", "harvest"],
 ),
}


def ld(slug, spec, url):
    graph = [
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Lazo", "item": "https://meetlazo.com/"},
            {"@type": "ListItem", "position": 2, "name": "Wedding websites", "item": HUB_URL},
            {"@type": "ListItem", "position": 3, "name": spec["name"], "item": url}]},
        {"@type": "WebPage", "@id": url, "url": url, "name": spec["title"], "description": spec["desc"],
         "isPartOf": {"@type": "WebSite", "name": "Lazo", "url": "https://meetlazo.com/"},
         "primaryImageOfPage": f"{A}/{spec['shot']}",
         "about": {"@type": "SoftwareApplication", "name": "Lazo wedding website", "applicationCategory": "LifestyleApplication",
                   "operatingSystem": "Web, iOS, Android", "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}}},
        {"@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in spec["faq"]]},
    ]
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def build(slug):
    spec = FEATURES[slug]
    url = f"{HUB_URL}{slug}/"
    E = html.escape
    s = HUB
    s = re.sub(r"<!-- lz-seo -->.*?<!-- /lz-seo -->\n", "", s, flags=re.S)
    s = re.sub(r"<title>[^<]*</title>", "<title>" + E(spec["title"]) + "</title>", s, count=1)
    s = re.sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="' + E(spec["desc"], quote=True) + '">', s, count=1)
    head = ("<!-- lz-seo -->\n"
            f'<link rel="canonical" href="{url}">\n'
            '<meta property="og:type" content="article">\n<meta property="og:site_name" content="Lazo">\n'
            f'<meta property="og:url" content="{url}">\n<meta property="og:title" content="{E(spec["title"])}">\n'
            f'<meta property="og:description" content="{E(spec["desc"])}">\n<meta property="og:image" content="{A}/{spec["shot"]}">\n'
            '<meta name="twitter:card" content="summary_large_image">\n'
            '<script type="application/ld+json">' + ld(slug, spec, url) + "</script>\n"
            "<!-- /lz-seo -->\n")
    s = s.replace('<meta name="theme-color" content="#52284F">\n', '<meta name="theme-color" content="#52284F">\n' + head, 1)
    # hero copy
    s = s.replace('<p class="eyebrow">Free wedding website builder</p>',
                  '<p class="eyebrow"><a href="../" style="text-decoration:none">Wedding websites</a> · ' + E(spec["name"]) + '</p>', 1)
    s = re.sub(r"<h1>.*?</h1>", "<h1>" + E(spec["h1"]) + "</h1>", s, count=1, flags=re.S)
    s = re.sub(r'<p class="sub">.*?</p>', '<p class="sub">' + E(spec["desc"]) + "</p>", s, count=1, flags=re.S)
    # three templates in the grid
    a = s.index('<main class="grid" id="grid">\n') + len('<main class="grid" id="grid">\n')
    b = s.index("</main>", a)
    s = s[:a] + "".join(relink(CARDS[t]) for t in spec["themes"]) + s[b:]
    s = s.replace('card.querySelector("[data-f]").src=id+"/?"+fp.toString();', 'card.querySelector("[data-f]").src="../"+id+"/?"+fp.toString();', 1)
    s = s.replace('card.querySelector("[data-view]").href=id+"/"+(qs?"?"+qs:"");', 'card.querySelector("[data-view]").href="../"+id+"/"+(qs?"?"+qs:"");', 1)
    s = s.replace('view.href=slug+"/?palette="+k;', 'view.href="../"+slug+"/?palette="+k;', 1)
    s = s.replace('href="noir/?married=1"', 'href="../noir/?married=1"', 1)
    s = re.sub(r"Live on all [\w-]+ previews below", "Live on all three previews below", s, count=1)
    # hub-only blocks out
    s = re.sub(r"<!-- lz-seo-sections -->.*?<!-- /lz-seo-sections -->\n\n?", "", s, flags=re.S)
    s = re.sub(r"<!-- lz-filters -->.*?<!-- /lz-filters -->\n", "", s, flags=re.S)
    s = re.sub(r"\s*<!-- lz-married -->.*?<!-- /lz-married -->", "", s, flags=re.S)
    s = re.sub(r"\n<script>\n/\* lz-filters-js \*/.*?/\* /lz-filters-js \*/\n</script>", "", s, flags=re.S)
    s = re.sub(r"<!-- lz-sell -->.*?<!-- /lz-sell -->\n?", "", s, flags=re.S)
    s = re.sub(r'<section class="beyond rv">.*?</section>\n', "", s, count=1, flags=re.S)
    # the feature story, ABOVE the template grid: screenshot, copy, points
    sib = [(k, v["name"]) for k, v in FEATURES.items() if k != slug]
    story = ['<!-- lz-feature -->',
             '<section class="sell rv" id="feature" style="padding-top:56px;margin-top:40px">', ' <div class="sw">',
             '  <div class="fgrid" style="margin-top:0">',
             '   <div class="fc wide">',
             f'    <div class="shot"><img src="{A}/{spec["shot"]}" alt="{E(spec["alt"], quote=True)}" loading="eager"></div>',
             f'    <div class="ft"><p class="fk">{E(spec["name"])}</p><h3>{E(spec["intro"][0].split(". ")[0])}.</h3><p>{E(". ".join(spec["intro"][0].split(". ")[1:]))}</p></div>',
             '   </div>', '  </div>',
             f'  <p class="sp" style="margin-top:34px;max-width:64ch">{E(spec["intro"][1])}</p>',
             '  <div class="fmore" style="margin-top:28px">']
    story += [f'   <div><b>{E(t)}</b><span>{E(p)}</span></div>' for t, p in spec["points"]]
    story += ['  </div>',
              '  <div class="scta"><a href="https://app.meetlazo.com/?template=' + spec["themes"][0] + '">Make yours &mdash; free, live in minutes</a>'
              '<p>Every Lazo design carries this. Three to start with are below.</p></div>',
              ' </div>', '</section>', '<!-- /lz-feature -->', '']
    s = s.replace('<main class="grid" id="grid">', "\n".join(story) + '<main class="grid" id="grid">', 1)
    # FAQ + other features, before the close
    body = ['<!-- lz-feature-sections -->',
            '<section class="sec faqs rv" id="faq">', ' <p class="sk">Questions</p>', f' <h2>{E(spec["name"])}: questions couples ask</h2>']
    body += [f' <details><summary>{E(q)}</summary><p>{E(a)}</p></details>' for q, a in spec["faq"]]
    body += ['</section>',
             '<section class="sec rv" id="more">', ' <p class="sk">More the site does</p>', ' <h2>Built for the day itself</h2>',
             ' <div class="chips">', '  <a href="../#day-of">Everything, on one page</a>']
    body += [f'  <a href="../{k}/">{E(nm)}</a>' for k, nm in sib]
    body += [' </div>', '</section>', '<!-- /lz-feature-sections -->', '']
    s = s.replace('<section class="close">', "\n".join(body) + '<section class="close">', 1)
    out = ROOT / slug / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(s, encoding="utf-8", newline="\n")
    print(f"  {slug}: {len(s):,} bytes")


if __name__ == "__main__":
    for slug in (sys.argv[1:] or list(FEATURES)):
        build(slug)
