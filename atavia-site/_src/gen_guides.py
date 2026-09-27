#!/usr/bin/env python3
"""
gen_guides.py — Atavia Weddings /guides/ section.

Six cornerstone informational articles. These do two jobs:
  1. Rank for high-volume top-of-funnel queries brides search BEFORE they book.
  2. Build the topical authority that helps the thousands of venue pages rank —
     a directory of thin pages with no supporting content looks like a doorway
     farm to Google. Real guides are what make it look like a real business.

Writes bodies to _src/pages/guides__*.html and a manifest to _src/guide_pages.py
(imported by build.py). Run: python3 _src/gen_guides.py && python3 _src/build.py
"""
import json, pathlib

SRC = pathlib.Path(__file__).resolve().parent
BASE = "https://ataviaweddings.com"
HERO = "https://firebasestorage.googleapis.com/v0/b/atavia-c29cd.firebasestorage.app/o/DSC_4772.jpg?alt=media&token=5182d7b9-096f-4902-a8b6-7ef2cd2e865a"
CTA  = "https://firebasestorage.googleapis.com/v0/b/atavia-c29cd.firebasestorage.app/o/atavia16.png?alt=media&token=4fff66fd-0144-474e-8fc1-d4ad8b6ab499"
def e(u): return u.replace("&", "&amp;")

# slug, title, h1, dek, meta description, [ (section heading, [paragraphs...]) ]
GUIDES = [
# JC-ATV-GUIDE-VET-0914-003: vendor-vetting guide (promotes Lazo), first card on the hub
("how-to-vet-wedding-vendors",
 "How to Vet a Wedding Vendor Before You Pay a Deposit",
 "Vet the Vendor <em>Before</em><br>the Deposit",
 "Five checks, ten minutes, and the one question most couples forget to ask.",
 "How to vet a wedding vendor in 2026 — the five checks that catch fake reviews, hidden fees and vendors who won’t show, and where to find prices before you ever send a message.",
 [
  ("Why the star rating tells you almost nothing",
   ["Sixteen years in, we have watched the same thing happen to hundreds of couples: they book the vendor with 4.9 stars and 200 reviews, and the day goes badly anyway. The rating wasn't lying, exactly. It just wasn't measuring what they thought it was.",
    "On the big planning sites, <strong>anyone can leave a review</strong> &mdash; a friend, a cousin, a vendor's own team. The sites don't check that a wedding happened, and they don't check that the reviewer paid for it. And the order you see vendors in is <strong>largely an ad product</strong>: the studios at the top of a &ldquo;best photographers in Dallas&rdquo; list are usually the ones paying the most that month, not the ones couples were happiest with.",
    "So a high rating on a paid listing is a starting point, not a verdict. The five checks below are what we'd do for our own family."]),
  ("Check 1 &mdash; The business is real, and it's the one you're talking to",
   ["Search the exact business name plus the word &ldquo;LLC&rdquo; or &ldquo;Inc.&rdquo; on your state's business registry. You're looking for two things: that it exists, and that the person messaging you is connected to it. A vendor who books under one name and contracts under another is a vendor you can't hold to anything.",
    "Then look at the last <strong>ninety days</strong> of their Instagram or gallery, not the highlight reel from 2022. You want proof they are shooting, cooking, or playing weddings <em>right now</em>, in the style they're selling you."]),
  ("Check 2 &mdash; The reviews come from couples who actually booked",
   ["Read the three most recent reviews and the three worst. Skip the five-star wall in the middle &mdash; it's the least informative part of any profile.",
    "Better still, use a platform that only publishes reviews from <strong>couples who paid and were married</strong>. That single filter removes the friend-and-family padding and the competitor sabotage in one move. This is the main reason we chose to be listed on <a href=\"https://meetlazo.com/?utm_source=ataviaweddings&amp;utm_medium=guide&amp;utm_campaign=vet-vendors\">Lazo</a>: every review there is tied to a booking, and no vendor can buy a higher spot in the results. If a review can't be traced to a real wedding, it isn't evidence."]),
  ("Check 3 &mdash; You saw a price before you sent a message",
   ["This is the question most couples forget to ask, because the big sites train you not to: <strong>&ldquo;What does it cost?&rdquo;</strong> A vendor who hides pricing behind a &ldquo;request a quote&rdquo; button isn't necessarily expensive &mdash; but they are planning to price you after they've read your budget, your venue, and your enthusiasm.",
    "Ask for the starting price and what it includes in your first message, or use a marketplace that puts <strong>packages and starting prices on the profile</strong> so you can compare what things actually cost in your city before you commit to a call. We publish ours on the <a href=\"/packages\">packages page</a> for the same reason."]),
  ("Check 4 &mdash; The contract says what the sales call said",
   ["Every promise that mattered on the call has to be on paper: hours of coverage, who is actually showing up (the owner, or a subcontractor you've never met), delivery timeline, what &ldquo;raw footage&rdquo; means, travel, overtime, and what happens if they cancel. Read our note on <a href=\"/guides/what-is-raw-footage\">what raw footage really means</a> &mdash; it's the line most often misunderstood.",
    "Then look at the money terms. A <strong>deposit of 20&ndash;30%</strong> is normal. A vendor asking for the full balance months ahead of the date, or only taking Zelle and Venmo with no contract, is asking you to carry all of the risk."]),
  ("Check 5 &mdash; They answer like someone who wants the job",
   ["Response time before you've paid is the best predictor of response time after. Two business days is fine. A week is a warning. And when they do reply, your note should reach <strong>the person who will be there on the day</strong>, not a sales inbox that hands you off later.",
    "Ask one specific question about your venue or your timeline. A pro answers it. A lead-farm sends you a brochure."]),
  ("The red flags, in one list",
   ["<strong>No business name you can look up.</strong> &nbsp;<strong>No recent work.</strong> &nbsp;<strong>Reviews with no wedding attached.</strong> &nbsp;<strong>&ldquo;Pricing on request&rdquo; with no range at all.</strong> &nbsp;<strong>A contract that doesn't name the shooter.</strong> &nbsp;<strong>Full payment up front.</strong> &nbsp;<strong>A week to reply, then a hard sell.</strong>",
    "One of these is a question to ask. Three is a different vendor."]),
  ("Where we'd send you to do all five at once",
   ["Most of this list exists because the big sites make you do the vetting yourself. The honest shortcut is a marketplace that has already done it: <a href=\"https://meetlazo.com/?utm_source=ataviaweddings&amp;utm_medium=guide&amp;utm_campaign=vet-vendors\">Lazo</a> is the verified wedding marketplace &mdash; real reviews from couples who booked, real prices on every profile, rankings no one can buy, and a planning assistant, June AI, who tells you what to book next based on your date, city and budget. It's free for couples, and it was built by working wedding pros, which is why we're listed there ourselves. Your message goes to the actual vendor, and the proposal, the contract and the payment stay in that same thread.",
    "Vet us the same way. We'd expect nothing less."])
 ]),
("how-to-choose-a-wedding-videographer",
 "How to Choose a Wedding Videographer",
 "How to Choose a<br><em>Wedding Videographer</em>",
 "The questions that actually matter — and the ones that don't.",
 "How to choose a wedding videographer: what to look for in a full film, what raw footage means, red flags to avoid, and the questions worth asking before you book.",
 [("Watch a full film, not just a highlight reel",
   ["Almost every videographer's website leads with a three-minute highlight reel set to a licensed song. Highlight reels are marketing — they're built from the best eight seconds of a twelve-hour day, and a mediocre filmmaker can still cut a decent one.",
    "Ask to see a <strong>full ceremony edit</strong> from a recent wedding. That's where skill actually shows: whether the audio of the vows is clean, whether the camera was in the right place when the bride's father reached for her hand, whether the edit holds its nerve during a long, quiet moment. If a videographer hesitates to show you a full film, that tells you something."]),
  ("Ask what you actually get, in writing",
   ["\"A wedding film\" means wildly different things to different studios. Pin down the deliverables: how long is the highlight film, do you get a longer documentary edit, do you get the <strong>full ceremony</strong> and <strong>full speeches</strong> uncut, and do you get the <a href=\"/guides/what-is-raw-footage\">raw footage</a>?",
    "Also ask about turnaround. Six to twelve weeks is normal. Anything over six months, ask why — and get the delivery window written into the contract, not promised in an email."]),
  ("Understand the coverage, not just the hours",
   ["Eight hours sounds like plenty until you map it against a real day. If you want getting-ready footage and you want the last dance, count backwards: hair and makeup at 11am and a sparkler exit at 10pm is eleven hours, not eight.",
    "Ask how many shooters are included. One person cannot be at the back of the aisle and on the groom's face at the same time. A <a href=\"/packages\">second shooter</a> is the difference between seeing the vows and seeing the reaction to them."]),
  ("The red flags",
   ["<strong>No contract.</strong> Walk away. A contract protects you far more than it protects them.",
    "<strong>Vague ownership language.</strong> You should know exactly what you can and can't do with your own film.",
    "<strong>Travel fees that appear late.</strong> Ask up front whether travel, parking, and overtime are included. Some studios quote low and add hundreds later. (We don't charge travel fees — we keep local teams in each market.)",
    "<strong>Only showing you weddings from years ago.</strong> Ask for something they shot in the last six months, ideally at a venue like yours."]),
  ("Trust the meeting, not just the portfolio",
   ["This person will be six feet from your face during the most emotional moments of your life. Technical skill matters, but so does whether they make you relax. Get on a call. If they talk more than they listen, that's your answer.",
    "And if you've already booked your venue, ask whether they've filmed there — or at least whether they know it. Someone who knows where the light falls at 6pm in that particular room will get shots a stranger won't."])]),

("wedding-photo-vs-video",
 "Wedding Photo vs. Video — Do You Need Both?",
 "Photo vs. Video &mdash;<br><em>Do You Need Both?</em>",
 "An honest answer, including when the answer is no.",
 "Wedding photography vs. videography: what each one actually captures, why couples who skip video regret it most, and when booking just one is the right call.",
 [("They capture genuinely different things",
   ["A photograph is a held moment. It goes on your wall, it goes to your grandmother, it's the image people will still be looking at in fifty years. Photography is the format of memory.",
    "A film captures the things a photo physically cannot: your partner's voice cracking on the second line of their vows. The specific way your friend laughs. The sound of the room when the doors open. People often say the thing they rewatch is not the highlight reel — it's the ten seconds of their grandfather saying something ordinary."]),
  ("The regret data is lopsided",
   ["Ask around and you'll notice a pattern: very few couples regret hiring a photographer, and very few regret hiring a videographer. But of couples who <em>skipped</em> one, the ones who skipped <strong>video</strong> regret it far more often — and it's the one thing you cannot go back and buy.",
    "The reason is simple. Photos of a wedding day are, to some degree, recoverable — guests take them, and the day is heavily photographed by accident. Nobody accidentally records clean audio of your vows."]),
  ("When one is genuinely enough",
   ["We'd rather be honest than sell you something you don't need. Book <strong>photo only</strong> if you're a couple who genuinely doesn't watch video, if your day is very short and intimate, or if the budget forces a choice and wall art matters more to you than motion.",
    "Book <strong>video only</strong> — rare, but real — if you have a photographer friend covering stills, or if what you care about is the ceremony and speeches rather than portraits."]),
  ("Why one team for both is usually better",
   ["When photo and video come from two different companies, they compete. They compete for position at the altar, for your time during portraits, and for the same five minutes of golden light. You end up refereeing.",
    "One team plans the day once. The photographer and filmmaker move around each other because they've done it a hundred times, the visual style matches across both, and your <a href=\"/packages\">combined package</a> costs less than booking two studios separately."]),
  ("What to do if the budget won't stretch",
   ["Cut hours before you cut a format. Six hours of photo and film will serve you better in twenty years than ten hours of photo alone. Coverage that ends after the first dance still gets you the entire story that matters — the getting ready, the ceremony, the speeches, the first dance.",
    "See what that actually looks like on our <a href=\"/packages\">packages page</a>, where a $500 deposit reserves the date."])]),

("what-is-raw-footage",
 "What \"Raw Footage\" Really Means",
 "What <em>Raw Footage</em><br>Really Means",
 "The most misunderstood line in a videography contract.",
 "What raw footage means in wedding videography: what you actually receive, why most studios don't include it, how big the files are, and why it matters in twenty years.",
 [("A definition, plainly",
   ["Raw footage is <strong>everything the cameras recorded</strong>, before any editing. Not the highlight film. Not the ceremony edit. The unfiltered clips — including the long, boring, unglamorous stretches where nothing much is happening.",
    "That sounds unappealing until you understand what's hiding in it."]),
  ("Why it matters more than couples expect",
   ["A highlight film is a curated story. It has to be — nobody watches a nine-hour movie of their own wedding. But curation means a filmmaker decided which moments made the cut, and they didn't know that your aunt who passed away six months later was on camera in the background for forty seconds, laughing at something off-frame.",
    "That's the argument for raw footage. It's not for watching often. It's insurance against the moments nobody knew were important yet."]),
  ("Why most studios don't include it",
   ["Three reasons, and only one of them is about you. <strong>Storage:</strong> a wedding can produce several hundred gigabytes to over a terabyte of footage. <strong>Delivery:</strong> that's expensive and slow to hand over. And <strong>protection:</strong> raw footage is unflattering. It shows shaky handheld moments, false starts, the shot where the operator missed focus. Some studios simply don't want you to see it.",
    "The third reason is the honest one, and it's why we include raw footage in <a href=\"/packages\">every collection</a>. If our work only looks good after editing, that's our problem to fix, not yours to be shielded from."]),
  ("What to actually ask for",
   ["Ask three specific questions. <strong>Is raw footage included, or is it an upsell?</strong> <strong>How is it delivered</strong> — a download link that expires, or a drive you keep? And <strong>how long do they archive it</strong> before it's deleted from their systems?",
    "That last one catches people out. Plenty of studios delete everything after 90 days. If you want your footage in ten years, you need your own copy."]),
  ("What to do with it once you have it",
   ["Back it up in two places — one physical drive and one cloud copy. Drives fail; clouds close accounts. Two copies in two formats is the rule.",
    "Then leave it alone. You won't watch it this year. You may not watch it for a decade. That's fine. It'll be there."])]),

("questions-to-ask-wedding-photographer",
 "17 Questions to Ask Before You Book",
 "Questions to Ask<br><em>Before You Book</em>",
 "Copy this list into your next vendor call.",
 "The questions to ask a wedding photographer or videographer before booking: coverage, deliverables, backups, contracts, travel fees, and the ones most couples forget.",
 [("About the work itself",
   ["<strong>1.</strong> Can I see a full film or full gallery from a recent wedding — not just a highlight reel?<br><strong>2.</strong> Have you shot at my venue, or a venue like it?<br><strong>3.</strong> Who will actually be shooting my wedding? (At larger studios, the person selling you is often not the person showing up.)<br><strong>4.</strong> How many weddings do you shoot in a weekend?<br><strong>5.</strong> What's your approach — do you direct and pose, or document?"]),
  ("About coverage",
   ["<strong>6.</strong> How many hours are included, and when does the clock start?<br><strong>7.</strong> How many shooters?<br><strong>8.</strong> What happens if the day runs long — what's the overtime rate?<br><strong>9.</strong> Do you take a break, and do we need to feed you? (Yes, and yes — put it in the catering count.)"]),
  ("About what you receive",
   ["<strong>10.</strong> Exactly what do I get, and when? Get the delivery window in the contract.<br><strong>11.</strong> Do I get the <a href=\"/guides/what-is-raw-footage\">raw footage</a> and the full, unedited ceremony?<br><strong>12.</strong> How are files delivered, and how long do you keep a backup?<br><strong>13.</strong> What can I do with the images and film — social, prints, submitting to publications?"]),
  ("About the things that go wrong",
   ["<strong>14.</strong> What happens if you get sick or your car breaks down? (The right answer is a named backup shooter and a network they can call — not \"that's never happened.\")<br><strong>15.</strong> Do you shoot to dual card slots? (This is the technical answer to \"what if a memory card fails.\" It should be yes.)<br><strong>16.</strong> Are you insured? Many venues require it in writing."]),
  ("The question almost nobody asks",
   ["<strong>17.</strong> What is <em>not</em> included that I'm likely to want?",
    "This is the one that saves people money. Ask it directly and watch how they answer. Travel fees, second shooters, drone coverage, extra hours, rush delivery, prints — the honest answer is a list. The dishonest answer is \"nothing.\"",
    "For the record: we don't charge travel fees, and raw footage is included in every collection. See exactly what's in each one on our <a href=\"/packages\">packages page</a>."])]),

("wedding-day-timeline",
 "A Wedding Day Timeline That Actually Works",
 "A Wedding Day<br><em>Timeline That Works</em>",
 "Built backwards from the light, the way photographers actually plan it.",
 "A realistic wedding day photo and video timeline — how much time each part actually takes, why you should plan around sunset, and where couples lose their portraits.",
 [("Plan backwards from sunset, not forwards from breakfast",
   ["The single most common timeline mistake is building the day forward and letting portraits land wherever they land — which is usually 2pm, under a hard overhead sun, in the worst light of the day.",
    "Instead, find your sunset time for your date. The 30–45 minutes before it is <strong>golden hour</strong>, and it is the best light you will get. Anchor your couple portraits there and build everything else around it. If your reception is underway by then, steal fifteen minutes and step outside. Every couple who does this is glad they did."]),
  ("How long things actually take",
   ["<strong>Getting ready:</strong> 60–90 minutes of coverage. The dress goes on last; tell your stylist the schedule.<br><strong>First look (optional):</strong> 20–30 minutes, and it buys you enormous flexibility later.<br><strong>Ceremony:</strong> 20–45 minutes for most; longer for a full mass or a multi-tradition ceremony.<br><strong>Family formals:</strong> plan 3 minutes per grouping. Ten groupings is thirty minutes, and it always runs long."]),
  ("The wedding party and couple portraits",
   ["<strong>Wedding party:</strong> 30 minutes.<br><strong>Couple portraits:</strong> 45 minutes if you can spare it, 30 at minimum, ideally split — some after the ceremony, and a short golden-hour session later.",
    "This is where time gets stolen. Cocktail hour is 60 minutes and everyone wants a piece of you. Protect the portrait window in writing and hand a printed timeline to your planner, your officiant, and your families."]),
  ("A worked example (5:00pm ceremony)",
   ["<strong>11:00am</strong> — coverage begins, getting ready<br><strong>1:30pm</strong> — first look and couple portraits<br><strong>2:30pm</strong> — wedding party<br><strong>3:15pm</strong> — hide; guests arrive<br><strong>5:00pm</strong> — ceremony<br><strong>5:30pm</strong> — family formals<br><strong>6:00pm</strong> — cocktail hour<br><strong>7:00pm</strong> — entrances, dinner, speeches<br><strong>8:15pm</strong> — <strong>golden hour portraits</strong> (15 min, step outside)<br><strong>8:45pm</strong> — first dance, dancing<br><strong>10:00pm</strong> — exit"]),
  ("Two things that buy you an hour",
   ["<strong>Do a first look.</strong> It's the single biggest timeline unlock — it moves portraits before the ceremony and hands your cocktail hour back to you. It doesn't cheapen the aisle moment; ask anyone who's done it.",
    "<strong>Get ready in one place.</strong> Every venue change costs 30–45 minutes of driving, parking, and reassembling. If both partners can prep at or near the venue, you gain an hour of coverage for free.",
    "Send us your timeline before the day — we'll tell you where it will break. See <a href=\"/packages\">what coverage length fits</a>."])]),

("wedding-videography-cost",
 "What Wedding Photography & Videography Actually Cost",
 "What It <em>Actually</em><br>Costs",
 "Real numbers, and where the money goes.",
 "What wedding photography and videography cost in 2026 — real price ranges, what drives the number up, hidden fees to watch for, and how to spend a smaller budget well.",
 [("The honest ranges",
   ["Nationally, wedding <strong>videography</strong> typically runs from around $1,200 for short single-shooter coverage to $5,000+ for a full-day, two-person cinematic production. <strong>Photography</strong> spans a similar range. In expensive metros, the top end goes considerably higher.",
    "Booking <strong>both from one studio</strong> almost always costs less than booking two — which is why combined collections exist. Our own <a href=\"/packages\">pricing</a> starts at $1,200 for film and $1,500 for photography, with combined collections from $3,000, and a $500 deposit reserves the date."]),
  ("What actually drives the price",
   ["<strong>Hours.</strong> The biggest single lever.<br><strong>Number of shooters.</strong> A second shooter is roughly the cost of an extra person's whole day.<br><strong>Editing time.</strong> This is the part couples never see. A highlight film can take 20–40 hours to cut. A photo gallery of 600 images takes days to cull and colour-grade. You are mostly paying for the work that happens after the wedding.",
    "<strong>Experience.</strong> A shooter who has done 200 weddings knows exactly where to stand when the doors open. That's what you're really buying."]),
  ("The fees that show up late",
   ["Get these in writing before you sign: <strong>travel fees</strong> (some studios charge hundreds once you're an hour away — we don't charge them at all), <strong>overtime</strong>, <strong>second shooter as an add-on</strong>, <strong>raw footage as an upsell</strong>, <strong>rush delivery</strong>, and <strong>album or print costs</strong>.",
    "A $2,000 quote with four of those attached is not a $2,000 quote."]),
  ("How to spend a smaller budget well",
   ["<strong>Buy skill, then buy hours.</strong> A great photographer for six hours beats an average one for ten.",
    "<strong>Cut the day, not the format.</strong> Coverage that ends after the first dance still captures everything that matters. The last hour of dancing is the least valuable footage of the night.",
    "<strong>Do a first look</strong> — it compresses your <a href=\"/guides/wedding-day-timeline\">timeline</a> and lets you book fewer hours.",
    "<strong>Book off-peak.</strong> A Friday or a November date is cheaper across every vendor category."]),
  ("What's worth paying more for",
   ["Two things, in our honest opinion. <strong>A second shooter</strong>, because one camera cannot see your face and your partner's face at the same time during the vows. And <strong>enough hours to reach golden hour</strong>, because that's where your best portraits will come from.",
    "Everything else — albums, drone, extra edits — can wait. Those two cannot be bought back later."])]),
]

# published dates by slug; anything not listed keeps the original launch date
DATES = {"how-to-vet-wedding-vendors": "2026-09-14"}

def article(g):
    slug, title, h1, dek, desc, sections = g
    secs = ""
    for head, paras in sections:
        body = "".join('<p>%s</p>' % p for p in paras)
        secs += ('<div class="guide-sec reveal"><h2>%s</h2>%s</div>' % (head, body))
    others = "".join(
        '<a href="/guides/%s">%s</a>' % (o[0], o[1])
        for o in GUIDES if o[0] != slug)
    return ('<section class="page-hero page-hero--short">'
      '<div class="page-hero__bg" aria-hidden="true"><img src="%s" alt="" onerror="this.onerror=null;this.src=\'%s\'"></div>'
      '<span class="page-hero__watermark" aria-hidden="true">A</span><div class="wrap">'
      '<nav class="crumbs" aria-label="Breadcrumb"><a href="/">Home</a> <span>/</span> <a href="/guides/">Guides</a> <span>/</span> <span>%s</span></nav>'
      '<div class="eyebrow center rules reveal">Wedding Guide</div>'
      '<h1 class="page-hero__title reveal d1">%s</h1>'
      '<p class="page-hero__sub reveal d2">%s</p></div></section>'
      '<section class="sec"><div class="wrap guide-body">%s'
      '<div class="guide-cta reveal"><h3>Planning your wedding?</h3>'
      '<p>We shoot photo and film nationwide &mdash; a local team, no travel fees, raw footage in every collection. A $500 deposit reserves your date.</p>'
      '<a href="/packages" class="btn btn--ghost" style="margin-right:10px">See Packages <span class="arr">&#8599;</span></a>'
      '<a href="/book/" class="btn btn--copper">Check Your Date <span class="arr">&#8599;</span></a></div>'
      '<div class="guide-more reveal"><h3>More guides</h3><div class="loc-grid">%s</div></div>'
      '</div></section>') % (e(HERO), HERO, title, h1, dek, secs, others)

manifest = []
for g in GUIDES:
    slug, title, h1, dek, desc, _ = g
    canon = "%s/guides/%s" % (BASE, slug)
    (SRC / "pages" / ("guides__" + slug + ".html")).write_text(article(g))
    art = {"@context":"https://schema.org","@type":"Article","headline":title,
           "description":desc,"image":CTA,
           "author":{"@type":"Organization","name":"Atavia Weddings"},
           "publisher":{"@type":"Organization","name":"Atavia Weddings",
                        "logo":{"@type":"ImageObject","url":CTA}},
           "datePublished":DATES.get(slug, "2026-07-03"),"dateModified":DATES.get(slug, "2026-07-03"),
           "mainEntityOfPage":canon}
    crumb = {"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
             {"@type":"ListItem","position":1,"name":"Guides","item":BASE + "/guides/"},
             {"@type":"ListItem","position":2,"name":title,"item":canon}]}
    schema = ('<script type="application/ld+json">%s</script>'
              '<script type="application/ld+json">%s</script>'
              % (json.dumps(art), json.dumps(crumb)))
    manifest.append(dict(slug="guides__" + slug, out="guides/%s.html" % slug, nav="", tier="guide",
        title="%s | Atavia Weddings" % title, desc=desc, canon=canon, schema_html=schema))

# hub
cards = "".join(
  '<a href="/guides/%s" class="fcard reveal" style="text-decoration:none">'
  '<div class="fcard__idx">%02d</div><h3>%s</h3><div class="fcard__rule"></div><p>%s</p>'
  '<span class="fcard__link">Read the guide &#8599;</span></a>' % (g[0], i + 1, g[1], g[3])
  for i, g in enumerate(GUIDES))
hub = ('<section class="page-hero page-hero--short">'
  '<div class="page-hero__bg" aria-hidden="true"><img src="%s" alt="" onerror="this.onerror=null;this.src=\'%s\'"></div>'
  '<span class="page-hero__watermark" aria-hidden="true">A</span><div class="wrap">'
  '<div class="eyebrow center rules reveal">Planning Guides</div>'
  '<h1 class="page-hero__title reveal d1">Wedding <em>Guides</em></h1>'
  '<p class="page-hero__sub reveal d2">Straight answers about photo and film &mdash; including the parts most studios would rather you didn\'t ask about.</p>'
  '</div></section>'
  '<section class="sec"><div class="wrap"><div class="cards cards--3">%s</div></div></section>'
  '<section class="cta-band cta-band--img" aria-label="Book Atavia Weddings">'
  '<img src="%s" alt="" loading="lazy" onerror="this.onerror=null;this.src=\'%s\'">'
  '<div class="wrap reveal"><span class="eyebrow center rules">Ready When You Are</span>'
  '<h2 class="cta-band__title" style="font-size:clamp(30px,4.6vw,58px);margin-top:20px">Let\'s capture your<br><em>wedding day.</em></h2>'
  '<a href="/book/" class="btn btn--copper" style="margin-top:26px">Reserve Your Date <span class="arr">&#8599;</span></a>'
  '</div></section>') % (e(HERO), HERO, cards, e(CTA), CTA)
(SRC / "pages" / "guides__index.html").write_text(hub)
manifest.append(dict(slug="guides__index", out="guides/index.html", nav="guides", tier="guidehub",
    title="Wedding Planning Guides | Atavia Weddings",
    desc="Straight answers on wedding photography and videography — how to choose a videographer, photo vs. film, raw footage, timelines, and what it really costs.",
    canon=BASE + "/guides/",
    schema_html='<script type="application/ld+json">{"@context":"https://schema.org","@type":"CollectionPage","name":"Wedding Planning Guides","url":"%s/guides/"}</script>' % BASE))

(SRC / "guide_pages.py").write_text("GUIDE_PAGES = " + repr(manifest) + "\n")
print("generated %d guides + 1 hub" % len(GUIDES))
