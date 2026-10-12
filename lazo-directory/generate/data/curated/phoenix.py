# Curated picks for Phoenix x the six guide categories. JC-LAZO-CURATE-1012
# Written 2026-10-12 from generate/data/curated-raw/phoenix.json (each vendor's own website, crawled by
# generate/curate_crawl.py). Every sentence below restates something the vendor says about themselves;
# nothing is inferred, no ratings are claimed. Prices are quoted only where the site prints them.
# Run `python generate/data/curated/phoenix.py` to emit phoenix/<cat>.json next to this file.
import json
from pathlib import Path

HOW = ("We read the website of every Phoenix {cat} listed on Lazo ({n} listings, {ok} sites reachable) and "
       "set aside the ones that are not really in the wedding business: {excluded}. What is left is a shortlist "
       "of vendors who say clearly what they do, show their work, and tell you how they work. Verified Lazo "
       "vendors come first. Nobody paid to be here, and this is not a ranking: Lazo ranks only on reviews "
       "from couples who booked.")

CATS = {
"wedding-venues": dict(
  excluded="meeting rooms, alumni halls and link pages with no venue behind them",
  ask=["Is the date you want a Saturday in October to April? Those go first here, often a year out.",
       "Does the package include the ceremony site, the coordinator and the rentals, or are those separate lines?",
       "Where do guests go when it is 105 degrees? Ask to see the indoor and shaded options, not just the lawn."],
  picks=[
    dict(id="ChIJ7esTJjekK4cRvotkki49sYg", tags=["historic mansion", "English gardens", "all-inclusive"],
         blurb="A historic Mesa mansion with English gardens and six ceremony sites, run by Wedgewood Weddings. Packages are all-inclusive and customizable, and the venue publishes real-wedding stories and photo galleries so you can see how the rooms are used."),
    dict(id="ChIJ9dW2Bq0UK4cRKkDShh2qBjU", tags=["all-inclusive", "family-owned", "one wedding a day"],
         blurb="Part of Aldea Weddings, the family company two sisters started in 2004 that now runs several Valley venues. Tercero in Glendale is all-inclusive, hosts one event a day, and prints its package pricing on the site rather than making you ask."),
    dict(id="ChIJ_RAVsZmwK4cRmFTksssMoWM", tags=["indoor and outdoor", "planning team included", "publishes pricing"],
         blurb="Mesa's Superstition Manor pairs indoor and outdoor spaces with a planning team that walks you from choosing the ceremony spot to running the day. Packages list two getting-ready suites open all day and six hours of event time, and pricing is published."),
    dict(id="ChIJx-ViTZcHK4cRwnkci3vPKnY", tags=["ballrooms to 300", "from $4,000", "all-inclusive"],
         blurb="Tuscan-style ballrooms for up to 300 guests with indoor and outdoor ceremony options. Villa Tuscana's coordinators handle linens, centerpieces and the schedule, and the site states packages start at $4,000, which makes it one of the few Phoenix venues that leads with a number.",
         from_price="$4,000"),
    dict(id="ChIJX2YYWH-PK4cRbM9CdI_bQlQ", tags=["lakeside", "Bartlett Lake", "from-scratch kitchen"],
         blurb="The newest lakeside venue in Arizona, on Bartlett Lake about 45 minutes from central Phoenix. Venue at the Cove hosts intimate and large weddings and makes a point of its from-scratch kitchen."),
    dict(id="ChIJGcyvgpa3K4cRziKBKU_wunI", tags=["desert views", "Superstition Mountains", "family-owned"],
         blurb="A family-owned desert venue at the foot of the Superstition Mountains, established in 2014. The Paseo bills itself as the place for a true Arizona wedding, and its team page introduces everyone from office staff to the set-up crew.",
         since=2014),
    dict(id="ChIJgcOXJh6vK4cREGdpkbF6xsY", tags=["waterfalls", "four courtyards", "all-inclusive"],
         blurb="Colby Falls in Gilbert is Wedgewood's desert-modern venue, with dramatic waterfalls and four courtyards. Same all-inclusive package structure as its sister venues, with an on-site planner assigned to each wedding."),
    dict(id="ChIJMR-wNsykK4cRgk6Yibb59ds", tags=["mountain views", "sunset", "ceremony and reception in one"],
         blurb="The Vistas Pavilion sits above the Valley at Las Sendas Golf Club in Mesa, with west-facing views built for sunset ceremonies. Ceremony and reception happen in one place, with the club's kitchen behind the menu."),
    dict(id="ChIJL4Bh8HypK4cRU5jtC8t4MHg", tags=["historic downtown Gilbert", "publishes ballpark pricing"],
         blurb="A wedding and event venue in historic downtown Gilbert, run by Dina, who came up through Las Vegas hospitality. The Cottage prints ballpark package estimates on its site so you can compare it with other venues before you tour."),
    dict(id="ChIJfdW--oVZK4cRe6JAV1dPjyo", tags=["West Valley", "desert and mountain views", "family-run"],
         blurb="The Willow is the West Valley's desert venue in Surprise, with mountain views and a single signature package. The team describes itself as a family driven by faith and creativity, and the site shows galleries of real weddings held there."),
    dict(id="ChIJS0QJU42nK4cRkXK58CF7zRY", tags=["1930s farmhouse", "gardens", "weddings since 1991"],
         blurb="A 1930s Mesa farmhouse that has hosted weddings since 1991. The Wright House runs twilight tours on Monday evenings with no appointment needed, which is a low-pressure way to see the grounds lit up.",
         since=1991),
    dict(id="ChIJDQ-c3_-zK4cRv46x-JyrNPE", tags=["rustic barn", "Queen Creek", "family-owned"],
         blurb="A rustic Queen Creek venue built around 1800s architecture and 250-year-old barn wood, run by the Baldwin family since 2020. For couples who want the barn look without leaving the East Valley.",
         since=2020),
  ]),

"wedding-photographers": dict(
  excluded="headshot studios, newborn and family portrait photographers, and a New York studio with no Arizona presence",
  ask=["How many weddings have you shot at venues like mine, and can I see a full gallery from one, not just highlights?",
       "What is the delivery timeline, and is a second shooter included or an add-on?",
       "If I want film or a specific editing style, is that your default or a special request?"],
  picks=[
    dict(id="manual-phoenix-atavia-weddings", tags=["photo and video", "cinematic films", "Lazo verified"],
         blurb="Atavia Weddings shoots photo and video as one team, pairing timeless stills with cinematic films for couples who value story over spectacle. Now booking 2026 and 2027, and one of the few Phoenix vendors with a verified, claimed Lazo profile.",
         from_price="$1,200"),
    dict(id="ChIJp5g0WuinK4cRUPSASqlRbBs", tags=["since 1996", "team of photographers", "true-to-color"],
         blurb="Matt has been shooting weddings since 1996; he and Dani started Still Life Studios in 2004. A Mesa-based team that specializes in Phoenix, Scottsdale and Gilbert weddings and makes a point of images that are true to color.",
         since=1996),
    dict(id="ChIJpV97KbQLK4cRTd8fZCMKkDg", tags=["150+ weddings", "documentary", "from $1,250"],
         blurb="Over ten years and 150 Arizona weddings, shot on 50mm and 85mm primes at wide apertures for that soft, dreamy look. Desert Light Weddings publishes packages from $1,250 and promises no hidden fees.",
         from_price="$1,250"),
    dict(id="ChIJaS_ApI5pK4cRtHtcPlVvLRA", tags=["16+ years", "luxury", "photo and video"],
         blurb="Lovelee Photography has photographed Arizona weddings for more than 16 years and says it is trusted by the state's premier venues. Associate videographers shoot in the same natural, elegant style, so photo and film match."),
    dict(id="ChIJ_egzTWYSK4cR_ve8rRgb29A", tags=["adventurous couples", "elopements", "Sedona"],
         blurb="T.J. Shull has documented love stories for 12 years with a colorful, timeless style aimed at adventurous couples. Based in Phoenix, works Scottsdale and Sedona often, and travels for destination weddings."),
    dict(id="ChIJuxt7yNxdK4cRLpTy29SaX5Y", tags=["photo and video", "editorial", "since 2020"],
         blurb="Kate Grutsky blends candid storytelling with an editorial eye and runs a photo and video team out of Peoria. Documenting Arizona weddings since 2020, with Phoenix, Scottsdale and destination work.",
         since=2020),
    dict(id="ChIJIbQPWaVxK4cRlrx10_szRyw", tags=["15 years", "faith-rooted", "photobooth"],
         blurb="Lia's Photography describes an approach rooted in faith, family and connection, photographing the prayers and quiet moments as much as the portraits. Fifteen years of Arizona weddings, plus modern photobooth services."),
    dict(id="ChIJ97JX60KfToYRqV-ObmAumh0", tags=["intimate weddings", "elopements", "digital and film"],
         blurb="Annette Ambrose photographs intimate weddings and elopements out of Scottsdale, shooting both digital and film. A former flight attendant who spent ten years traveling the world before turning the camera on couples."),
    dict(id="ChIJaWmGTAEGK4cRH8JZ5YPnNYE", tags=["calm approach", "sentimental", "destination"],
         blurb="Suzy Goodrick promises a calm approach for an effortless photography experience, with intentional storytelling for sentimental couples. Based in Gilbert, shoots Phoenix and destination weddings."),
    dict(id="ChIJryt_YaFzK4cR-uOO98x8Ar4", tags=["husband and wife", "hair and makeup on the team", "video available"],
         blurb="Signature Wedding Photography is Tavit, a veteran event photographer, and Lydia, an award-winning hair and makeup artist. The pairing is unusual and practical, and they cover Phoenix, Scottsdale, Sedona and Flagstaff with video as an option."),
    dict(id="ChIJ8WgrqrULK4cRDQ0_M6KP4a4", tags=["husband and wife", "candid", "Scottsdale"],
         blurb="Ivonne and Travis are a Scottsdale husband-and-wife team who describe themselves as storytellers of candid, timeless images, photographing weddings across Arizona and beyond."),
    dict(id="ChIJfVQc7uFsK4cRCLmksm7EHPU", tags=["photojournalism", "documentary", "no travel fees in AZ"],
         blurb="Inloveness Photography works in a photojournalistic style, blending candid documentary moments with artfully composed portraits, for couples who would rather forget Pinterest than follow it."),
  ]),

"wedding-videographers": dict(
  excluded="corporate video houses, production studios and sound stages that do not film weddings",
  ask=["Is audio from the vows and toasts recorded on lapel mics and a board feed, or just the camera?",
       "How long until the highlight film and the full-length edit arrive, and are raw files included?",
       "Is there an hourly cap, and what happens if the reception runs late?"],
  picks=[
    dict(id="manual-phoenix-atavia-weddings", tags=["cinematic films", "photo and video", "Lazo verified"],
         blurb="Atavia Weddings crafts cinematic films alongside stills, for couples who want the day remembered as it felt. Now booking 2026 and 2027, with a verified, claimed Lazo profile.",
         from_price="$1,200"),
    dict(id="ChIJn6ReX0-nK4cRPGi4Uas3pAE", tags=["cinematic", "storytelling", "travels worldwide"],
         blurb="Evan Dangerfield films cinematic wedding films built on authentic storytelling, from luxury Scottsdale celebrations to mountain weddings in Sedona and destinations beyond. Based in Phoenix, offers engagement sessions too."),
    dict(id="ChIJWT8o5pRzK4cR1H6nYoubTn0", tags=["husband and wife", "10 years", "Indian weddings"],
         blurb="SkyPoint Productions is a husband-and-wife team with ten years of wedding film experience, specializing in story-driven luxury cinematography and Indian wedding videography, with elopement films as well."),
    dict(id="ChIJ5YOuVhj7KocRXqoUebvLP3o", tags=["unlimited hours", "drone", "Super 8mm"],
         blurb="John Houston Films includes unlimited coverage in every package, so there is no hourly limit to watch, plus drone footage, full recordings of the ceremony and formalities, and Super 8mm film as an option. Covers all of Arizona from Maricopa."),
    dict(id="ChIJ270gyumnK4cRRrR5XVXTkhM", tags=["hand-crafted films", "two cinematographers", "publishes collections"],
         blurb="Serendipity Cinema is a Gilbert team making hand-crafted cinematic wedding films, with collections that scale up to two cinematographers for twelve hours. Collection pricing is printed on the site, roughly $4,100 to $6,100 at our read."),
    dict(id="ChIJbbSJyemnK4cRSThhJFz96U0", tags=["budget-minded", "since 2009", "Serendipity's sister"],
         blurb="Simply Cinema is Serendipity's simpler sister brand, born in 2009 for couples who want a quality film with simplified coverage and a lighter price. Same Gilbert team behind it.",
         since=2009),
    dict(id="ChIJWR91BRimK4cRjPxMshNpFT4", tags=["cinematic", "Mesa"],
         blurb="PictureVideo.com, Perry Sevey's Mesa studio, makes cinematic wedding films meant to transport you back to the day rather than just document it, shot at celebrations across the Valley."),
    dict(id="ChIJWb8YPqILK4cRttOo9cMiuho", tags=["photo and film", "Arizona and California"],
         blurb="Halo Productions pairs timeless photography with cinematic wedding films for couples who want to feel fully present on the day. Scottsdale-based, works Arizona and California."),
    dict(id="ChIJKX-Y0gJJWoIRIjPicl-_IZI", tags=["documentary", "candid", "local Essentials package"],
         blurb="AZ Film Company shoots documentary-style films with a candid approach, out of Goodyear. Pricing is by inquiry, with an Essentials package offered only locally."),
    dict(id="ChIJZ5CgD5sPK4cRyyGhtdQ69f8", tags=["photo and cinema", "transparent pricing", "almost ten years"],
         blurb="Lee Media Weddings has done photo and cinema for almost ten years, and its pricing page is laid out simply by photo, cinema, or both. Tempe-based, editorial polish with a hands-on approach."),
    dict(id="ChIJs15tZSrbIUgRFMEfhiscruM", tags=["affordable", "no travel fees", "15 years"],
         blurb="Diamond Ring Media offers affordable photo and video packages with no travel fees in Arizona, led personally through 15 years of weddings by its owner. Based in Glendale."),
    dict(id="ChIJpXSUt72xK4cRT_PDUT1Jo0w", tags=["economy plans from $549", "deluxe from $1,299"],
         blurb="Altar Images AZ in Mesa prints its pricing: economy plans from $549 for small, single-location events and deluxe plans from $1,299 for full-day coverage, with photo montages and engagement videos as add-ons.",
         from_price="$549"),
  ]),

"wedding-planners": dict(
  excluded="stage and festival crews, caterers and venues that also sell coordination, and rental companies",
  ask=["Full planning, partial, or day-of only? Ask what each tier includes in hours and in meetings.",
       "Which Phoenix venues and vendors have you worked with this year? Local relationships are the job.",
       "Who is on site on the wedding day, the planner you hired or an associate?"],
  picks=[
    dict(id="ChIJ5Yr-oCN0K4cRw5Bes0leu6Q", tags=["since 2011", "busy professionals", "hospitality-rooted"],
         blurb="Pop the Cork Productions has planned Arizona weddings since 2011 with a pitch aimed at busy professionals who want a planner at their side. Celebrations rooted in hospitality, with planning and coordination tiers published on the site.",
         since=2011),
    dict(id="ChIJh8aQdxtpK4cRRfBwy3hFROY", tags=["weddings only", "full-service", "destination"],
         blurb="Jordyn plans weddings and only weddings, full-service in Arizona and at destinations worldwide. The site lays out support levels so you can pick the amount of help that fits your day."),
    dict(id="ChIJs9x2kkwHK4cRMRJKOWWYz5k", tags=["multi-award-winning", "Arizona Bride Best, twice", "design-led"],
         blurb="Black Tie Optional has twice been named Best by Arizona Bride Magazine and plans weddings for couples who, in its words, do not do boring. Tempe-based, design-heavy, built around the couple's own story."),
    dict(id="ChIJM5JnwJULK4cR5fRcqHHz9YA", tags=["luxury", "multi-day", "AZ, CA, Mountain West, Mexico"],
         blurb="Mandy Marie Events plans luxury destination weddings and multi-day celebrations across Arizona, California, the Mountain West and Mexico, with concierge-level planning and editorial-caliber design."),
    dict(id="ChIJuzvP8RkACSQR7MmLaih0lyg", tags=["luxury", "full-service", "proposal design"],
         blurb="Soul Agave, led by Dominique Mattessino in Gilbert, does luxury full-service planning plus proposal design, for couples with a distinct style who obsess over their love story."),
    dict(id="ChIJI1x1sYljK4cRVb3Dv0XG5x0", tags=["boutique", "8 years", "immersion process"],
         blurb="Sweet Simplicity Events is a boutique Phoenix planner founded to fight weddings that look perfect but feel impersonal. Eight years in, the process starts with getting to know your story before any design."),
    dict(id="ChIJOVTuWDwSK4cRaID_CWYQ9vA", tags=["15+ years", "OK! Magazine Best Wedding Planner 2023"],
         blurb="Lisa brings more than 15 years in events and hospitality and was voted Best Wedding Planner by OK! Magazine in 2023. Stylish Events by Lisa handles weddings and social events throughout Arizona.",
         since=2015),
    dict(id="ChIJJ7g0V1irK4cRPFqdrD6b700", tags=["South Asian", "multicultural", "luxury"],
         blurb="Apropos Creations is Arizona's South Asian and multicultural wedding specialist, keeping traditions at the heart of the celebration while planning at a luxury level. Chandler-based, serves every couple and culture."),
    dict(id="ChIJ1yGAujpPfGMRVP5T2VSF97Y", tags=["bespoke", "high-end", "hospitality degree"],
         blurb="MatchBox Event Co. is Natalia's bespoke planning studio in Phoenix, crafted guest experiences backed by a hospitality management degree from Northern Arizona University. Weddings plus social and corporate events."),
    dict(id="ChIJHfnxobYLK4cRytTA-ojNmu8", tags=["luxury", "destination", "a decade of experience"],
         blurb="Westgate Events is Cydney Lundahl's luxury wedding and event studio in Scottsdale, with over a decade in the industry and a curated vendor team tailored to each couple."),
    dict(id="ChIJ5Y7FCflPK4cR-ap5dPYe3SU", tags=["day-of coordination", "wedding day management"],
         blurb="Sweet I Do's specializes in wedding day management, the day-of coordination that lets you be a guest at your own wedding. Phoenix metro, for couples who planned it themselves and want the day run by someone else."),
    dict(id="ChIJgXd0ReCrK4cR5f7UN4In7xk", tags=["micro weddings", "all-inclusive", "up to 24 guests"],
         blurb="Meander Gatherings runs all-inclusive micro and pop-up weddings for up to 24 people, bringing the setup to a location you choose. For couples who want a real ceremony without a 150-person production."),
  ]),

"wedding-florists": dict(
  excluded="same-day delivery shops and funeral florists that do not do wedding design, a floral preservation drop-off, and a painter",
  ask=["Do you design for the venue, or deliver arrangements? Installation and teardown are the difference in price.",
       "What is in season in Phoenix for my month, and what gets shipped in?",
       "Can I see a full wedding's florals, not a bouquet photo, at a budget like mine?"],
  picks=[
    dict(id="ChIJ5wThAOARK4cR_WeNCf7AYIQ", tags=["full-service design", "Phoenix Flower District", "since 2011"],
         blurb="LUX Wedding Florist is a full-service wedding and event design studio in the heart of the Phoenix Flower District, creating events since 2011. The site lists awards and features and a love-notes page of past couples.",
         since=2011),
    dict(id="ChIJw1yZ_0hwK4cRKWztAI9Z28U", tags=["weddings only", "since 1995", "locally owned"],
         blurb="Flowers by Jodi has specialized exclusively in weddings and events since 1995, across Arizona and beyond. An upscale, locally owned studio with three decades of wedding flowers behind it.",
         since=1995),
    dict(id="ChIJ91xZ01F0K4cRgGJMU4na0WA", tags=["30+ years in floral", "husband and wife", "events only"],
         blurb="Your Event Florist in Scottsdale is a husband-and-wife event floral business started as newlyweds more than 19 years ago, with Kevin bringing over 30 years in the floral industry. The site shows real weddings by couple name."),
    dict(id="ChIJg0MwsPgOK4cRcAHW_x86QyI", tags=["art-focused", "13 years", "thousands of events"],
         blurb="Form Floral began as Malori Maeva's one-woman operation 13 years ago and has since designed for thousands of weddings and events, with an art-focused style built around the desert landscape."),
    dict(id="ChIJFfxuRjuyzScRv61RG_8Sxwk", tags=["fine art", "installations", "Phoenix and Los Angeles"],
         blurb="Snapdragon Atelier does fine art wedding florals designed for the space and told through the story, with premium seasonal blooms and installation managed directly with the venue. Phoenix, Scottsdale and Los Angeles."),
    dict(id="ChIJPzfmjV6oK4cRSpfHL06jK4k", tags=["custom wedding decor", "Mesa", "statewide"],
         blurb="Blume Events is Kristen and David Mandly's wedding florist in Mesa, designing custom floral decor for weddings from Phoenix and Gilbert to Tucson and Sedona. Kristen has been doing wedding flowers since she was sixteen."),
    dict(id="ChIJ1wsPRpKjXYcRxNlt3VRgNjA", tags=["wedding florals", "mobile bloom bar", "event rentals"],
         blurb="Social Fleur, founded by Cecilia, does custom wedding florals and centerpieces plus a mobile bloom bar and event rentals, so one team covers the flowers and the vibe. Phoenix and Scottsdale."),
    dict(id="ChIJTwruUUptK4cRtO7M30aU_JY", tags=["floral design studio", "weddings and delivery"],
         blurb="Blooming Canyon is Isis Lopez's home-based floral design studio in Phoenix, offering wedding flowers alongside delivery and designer's-choice work, drawing on a love of flowers that started more than 30 years ago."),
    dict(id="ChIJ2fB8RSxFK4cRoWuVTC6iKvc", tags=["Arizona Master Florist", "planning and floral", "Tongan-American design"],
         blurb="Designs by Zima is led by an Arizona Master Florist and combines wedding planning with floral design, with palettes inspired by a Tongan-American background. Over ten years of events across the country."),
    dict(id="ChIJQVYmFOARK4cRmhn2BZOLD_U", tags=["wholesale", "DIY couples", "Flower District"],
         blurb="Not a designer but worth knowing: Arizona Flower Market sells fresh wholesale and bulk flowers plus supplies in the Phoenix Flower District, the place DIY couples and many local florists buy stems."),
    dict(id="ChIJHZaRsxUMK4cRd9sRZA5pDIw", tags=["50+ years", "four Valley locations", "retail florist"],
         blurb="Phoenix Flower Shops has been the Valley's local florist for over 50 years, with four retail locations and wedding flowers among its services. The traditional retail option if you want a shop rather than a studio."),
  ]),

"wedding-djs": dict(
  excluded="recording studios, AV production crews and an out-of-state DJ company with a Phoenix landing page",
  ask=["Who exactly will be at my wedding, and can I talk to that DJ before I sign?",
       "How do you handle the ceremony audio and the toasts, not just the dance floor?",
       "What is in the base price, and what are uplighting, photo booth and extra hours on top?"],
  picks=[
    dict(id="ChIJ37OMK3Eux6MRKUBOHrVTfb0", tags=["team of DJs", "matched to the couple", "weddings and events"],
         blurb="Ray the DJ runs a team of Phoenix wedding and event DJs it describes as family, and pairs each couple with the DJ whose style fits. The site walks through how it builds a wedding timeline, not just a playlist."),
    dict(id="ChIJg4XlJmSvK4cRymR0bZDFvAY", tags=["since 2005", "luxury wedding entertainment", "2024 Couples' Choice"],
         blurb="Direct Sounds has set its standard for luxury wedding entertainment since 2005 and lists a 2024 Couples' Choice award. The DJ doubles as master of ceremonies and coordinates the flow of the night with the venue.",
         since=2005),
    dict(id="ChIJ5WbjrQBlK4cRq4dPL1RPobI", tags=["DJ since 1994", "Wedding Entertainment Director", "emcee"],
         blurb="Shawn Whittemore started as an Arizona event DJ in 1994 and earned the Wedding Entertainment Director title in 2007. Event Synergy is a one-DJ, wedding-focused operation with lighting, screens and monograms as add-ons."),
    dict(id="ChIJ-V0HBeYBK4cRffZRULcqN1g", tags=["weddings only", "upfront rates", "flipbook booth"],
         blurb="Red Letter DJs serves weddings exclusively and promises to be open about its rates, no 'starting at' games. Chandler-based, with videography and a flipbook photo booth available from the same team."),
    dict(id="ChIJS7gFrzKSTywRss7OMbkzjs8", tags=["Couples' Choice winner", "photo booth", "photo bus"],
         blurb="Jazzy J Entertainment is a WeddingWire Couples' Choice winner offering DJ and master of ceremonies plus a photo booth, a photo bus and uplighting, with couples' quotes about full dance floors on the site."),
    dict(id="ChIJgds6ZgINK4cRxzI_ir8j3J4", tags=["statewide", "high-profile events", "team"],
         blurb="Engage Entertainment fields a roster of DJs it says have each been recognized at high-profile events, for weddings and parties across Arizona. The site leads with couples' own words about the dance floor."),
    dict(id="ChIJ2XL6rn0RK4cRHTA1M8GweOU", tags=["female-led collective", "DJs and live musicians", "modern weddings"],
         blurb="Shuffle House is a female-led collective founded by Miss Mixx: elite DJs, musicians and, in its words, vibe architects for modern weddings. Tell them the vibe and they match the DJ or build a full soundscape with live strings."),
    dict(id="ChIJLQR7QGcJK4cR_MnaJHbziDM", tags=["since 1999", "MC-led", "timeline help"],
         blurb="Starz Entertainment has worked Phoenix and Scottsdale weddings since 1999 and treats the MC as the voice of your event, helping organize details, timeline and music long before the day.",
         since=1999),
    dict(id="ChIJH3k-uQ1jK4cRMDsQQ2YiKJ0", tags=["36 years", "20 hours of prep", "120-item checklist"],
         blurb="SKM Entertainment in Scottsdale claims 36 years of entertainment, more than 20 hours of preparation before each event and a 120-item checklist on the day. DJ and MC, photo booths, lighting and effects.",
         since=1987),
    dict(id="ChIJ1y6QdM9oK4cRKn7OygMqjCc", tags=["since 2002", "customized weddings", "Glendale"],
         blurb="All-American DJ and Entertainment has served Phoenix-area weddings since 2002 with a focus on customized events that do not look like everyone else's. The site is built around reviews from named couples."),
    dict(id="ChIJhRk8ZJwNK4cRNnihl7s9Td8", tags=["Indian and Desi weddings", "event lighting", "DJ Isaac"],
         blurb="Hyper Productions and DJ Isaac are Arizona's Indian wedding DJ and entertainment specialists, with event lighting and a crew of professionals, working Arizona and California."),
    dict(id="ChIJ9YVA0YITCq0RPScejt9bBqU", tags=["20+ years", "emcee", "Chandler"],
         blurb="Heavy DJs brings JJ Nite's two decades as a mobile DJ and emcee, including time as an on-air radio personality, to weddings and parties across the Valley, with a polished emcee style and packed-floor promise."),
  ]),
}


def main():
    here = Path(__file__).resolve().parent
    raw = json.loads((here.parent / "curated-raw" / "phoenix.json").read_text(encoding="utf-8"))
    vendors = {v["id"]: v for v in raw["vendors"]}
    sites = raw["sites"]
    out_dir = here / "phoenix"; out_dir.mkdir(exist_ok=True)
    for cat, c in CATS.items():
        n = sum(1 for v in raw["vendors"] if cat in v["categories"])
        ok = sum(1 for v in raw["vendors"] if cat in v["categories"] and sites.get(v["id"], {}).get("ok"))
        picks = []
        for p in c["picks"]:
            v = vendors[p["id"]]; s = sites.get(p["id"], {})
            ig = next((x.split("instagram.com/")[-1].strip("/") for x in s.get("socials", []) if "instagram.com/" in x and "/p/" not in x and x.split("instagram.com/")[-1].strip("/") not in ("wix", "")), "")
            picks.append(dict(id=p["id"], name=v["name"], website=s.get("url") or v["website"], instagram=ig, tags=p["tags"], blurb=p["blurb"],
                              since=p.get("since"), from_price=p.get("from_price"), verified=v["verified"], claimed=v["claimed"]))
        doc = dict(metro="phoenix", cat=cat, updated="2026-10-12", read=ok, listed=n,
                   how=HOW.format(cat={"wedding-venues": "wedding venue", "wedding-photographers": "wedding photographer", "wedding-videographers": "wedding videographer",
                                       "wedding-planners": "wedding planner", "wedding-florists": "wedding florist", "wedding-djs": "wedding DJ"}[cat], n=n, ok=ok, excluded=c["excluded"]),
                   ask=c["ask"], picks=picks)
        (out_dir / f"{cat}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
        print(cat, len(picks), "picks;", ok, "of", n, "sites read")


if __name__ == "__main__":
    main()
