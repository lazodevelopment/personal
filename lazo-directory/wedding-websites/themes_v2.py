"""themes_v2.py - JC-LAZO-WWT-0921-001
The original thirteen templates, rebuilt to the standard of the seven added on
2026-09-19 (harvest, aquarelle, prism, meadow, gilded, marigold, papel), which
the founders judged premium where the originals read as party-invite generators.

What changes, per template:
  - a full-bleed photographic hero with a dark scrim and white editorial type
    (Fete included: its invitation-card split read as a party invite too)
  - no animated waves / stars / snow / leaves and no emoji glyphs in section kickers
  - display type chosen for weight and restraint (Rye and Cinzel are gone)
  - quieter eyebrow and countdown copy ("Together with their families", not
    "Y'all are invited")
What stays: every palette KEY (the couple app's picker and existing sites
reference them), the demo couples and their story, schedule, venues and FAQ,
and all data hooks, because everything is still built from _base.html.

Merged into make_themes.THEMES after themes_extra, so `python
wedding-websites\\make_themes.py sage` builds the v2 Sage. Then, as always:
  python wedding-websites\\apply_feel.py <slugs>
  python wedding-websites\\patch_seo.py <slugs>
  python wedding-websites\\sync_dist.py
  python deploy\\upload_r2.py --prefix wedding-websites
"""
U = "https://images.unsplash.com/photo-"
def img(id_, w=1200, q=74):
    return f"{U}{id_}?auto=format&fit=crop&w={w}&q={q}"

# the restrained section rhythm every v2 template shares: a faint tint on
# alternate sections, a hairline under the kicker, nothing animated.
CALM_CSS = """
section:nth-of-type(odd){background:linear-gradient(180deg,var(--bg),color-mix(in srgb,var(--sand) 42%,var(--bg)))}
.k{letter-spacing:.34em}
.hero-full .eyebrow{letter-spacing:.38em;font-size:11px;opacity:.9}
.hero-full h1{font-weight:500;letter-spacing:-.01em}
.hero-full .cdline{border-color:rgba(255,255,255,.45)}
"""

_COMMON = dict(
    song_ph="A song that gets everyone dancing (optional)",
    note_ph="Dietary notes, song requests, questions…",
    reg_h="Your presence is the whole point.",
    body_extra="", hero_art="", extra_css=CALM_CSS,
)
def spec(**kw):
    d = dict(_COMMON); d.update(kw); return d

V2 = {
 "sage": spec(
  name="Sage", title="Sage — a garden & greenery wedding website template | Lazo",
  desc="A free garden wedding website template from Lazo — sage, eucalyptus and terracotta, with RSVPs, schedule, registry, and a site that says We're Married after the big day.",
  fonts="family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500;1,600&family=Jost:wght@300;400;500&display=swap",
  serif='"Cormorant Garamond",serif', display='"Cormorant Garamond",serif', sans='"Jost",sans-serif',
  palettes={"garden":{"--bg":"#F8FAF6","--ink":"#2F3A32","--mut":"#74837A","--acc":"#6F8F76","--panel":"#FFFFFF","--line":"#DCE6DD","--sand":"#EAF0E8"},
            "eucalyptus":{"--bg":"#F6F9F8","--ink":"#2D3B38","--mut":"#6F8580","--acc":"#5D8A80","--panel":"#FFFFFF","--line":"#D8E5E1","--sand":"#E6EFEC"},
            "terracotta":{"--bg":"#FAF6F2","--ink":"#3B2F2A","--mut":"#8B7A70","--acc":"#B8674A","--panel":"#FFFFFF","--line":"#EBDCD2","--sand":"#F2E6DC"},
            "lavender":{"--bg":"#F9F8FB","--ink":"#3A3546","--mut":"#84809A","--acc":"#8A7DB0","--panel":"#FFFFFF","--line":"#E4E0EE","--sand":"#EEEBF4"}},
  hero="full", hero_img=img("1441974231531-c6227db76b6e", 1900), hero_filter="saturate(.92) brightness(.9)",
  eyebrow="Together with their families", cdlabel="days to go", n1="Ava", n2="Liam",
  where="Oak Creek · Sedona, Arizona", date="2026-10-17",
  story_h="The longer way around, on purpose.", story_p="We met on a trail neither of us meant to take, and kept taking the longer way ever since. Three autumns later we are getting married by the creek, with the people who walked it with us.",
  story_img=img("1523438885200-e635ba2c371e", 1000), story_cap="Three autumns in",
  gal_h="Green light, long tables, the two of us.", gal=[(img("1511795409834-ef04bbd61622"), "Long tables, longer toasts"), (img("1519225421980-715cb0215aed", 900), "Dinner under the string lights"), (img("1464366400600-7168b8af9bc3", 900), "Where it all began")],
  day_h="One canyon, one golden afternoon, everyone we love.",
  sched=[("3:30 pm","Guests arrive - lavender lemonade on the lawn"),("4:00 pm","Ceremony by the creek"),("4:45 pm","Cocktails in the garden"),("6:00 pm","Dinner under the oaks"),("8:30 pm","Dancing until the stars come out")],
  ven=[("Ceremony","Oak Creek Terrace","4:00 in the afternoon","Bring flat shoes - the path to the creek is gravel"),("Reception","The Garden Barn","4:45 until late","Dinner, toasts and a very long dance")],
  thanks="The creek kept its promise. Thank you for walking the long way with us.",
  rsvp_h="Save us a seat by the creek.", rsvp_p="Kindly reply by September 15 - the lemonade count waits for no one.", yes="Joyfully accepts", no="Regretfully declines",
  reg_p="If you would like to give more, we have gathered a few things for the garden - and a fund for the trail we keep talking about.",
  faq=[("What should I wear?","Garden cocktail - linen, florals, soft colours, and shoes that can handle grass and gravel. It cools quickly after sunset."),("Are kids welcome?","We love your children, and we have planned a grown-up evening. Babes in arms are always welcome."),("Where should we stay?","We have a block at the creekside inn under our names; the details are in your invitation.")],
 ),

 "noir": spec(
  name="Noir", title="Noir — a black-tie evening wedding website template | Lazo",
  desc="A free black-tie wedding website template from Lazo — midnight, champagne, bordeaux and emerald, with RSVPs, schedule, registry, and a site that says We're Married after the big day.",
  fonts="family=Bodoni+Moda:ital,opsz,wght@0,6..96,400;0,6..96,500;1,6..96,400&family=Archivo:wght@300;400;500&display=swap",
  serif='"Bodoni Moda",serif', display='"Bodoni Moda",serif', sans='"Archivo",sans-serif',
  palettes={"midnight":{"--bg":"#0F0E12","--ink":"#F3EEE6","--mut":"#A39C92","--acc":"#C9A45C","--panel":"#17161B","--line":"#2A2830","--sand":"#1D1B22"},
            "champagne":{"--bg":"#14100B","--ink":"#F5EEE2","--mut":"#A79B87","--acc":"#E3C888","--panel":"#1C1712","--line":"#302A22","--sand":"#221C15"},
            "bordeaux":{"--bg":"#170C10","--ink":"#F4EBEC","--mut":"#A8949A","--acc":"#B8425A","--panel":"#201318","--line":"#35222A","--sand":"#26171D"},
            "emerald":{"--bg":"#0B1512","--ink":"#EAF2EE","--mut":"#92A69D","--acc":"#3F9B7A","--panel":"#121E1A","--line":"#22332D","--sand":"#172521"}},
  hero="full", hero_img=img("1519741497674-611481863552", 1900), hero_filter="saturate(.85) brightness(.82) contrast(1.05)",
  eyebrow="Black tie · New Year's Eve", cdlabel="days until midnight", n1="Maya", n2="Jordan",
  where="The Athenaeum · Chicago, Illinois", date="2026-12-31",
  story_h="Ten years of December 31sts.", story_p="Our first New Year's Eve was a borrowed tuxedo and a dress from a friend's closet. Ten of them later, we are getting married at a quarter to midnight, with the people who kept us out late.",
  story_img=img("1511285560929-80b456fea0bc", 1000), story_cap="A decade in",
  gal_h="A decade, developed in black and white.", gal=[(img("1511285560929-80b456fea0bc"), "The proposal, 11:58 pm"), (img("1529636798458-92182e662485", 900), "Every party since 2016"), (img("1520854221256-17451cc331bf", 900), "Champagne, always")],
  day_h="One night, dressed to the nines.",
  sched=[("10:00 pm","Doors, coat check and a martini"),("11:00 pm","Ceremony in the Marble Hall"),("11:45 pm","Champagne on the rooftop"),("12:00 am","The first kiss of the year"),("12:15 am","Dinner, then dancing until the band gives up")],
  ven=[("Ceremony","The Marble Hall","11:00 in the evening","Black tie, and warm coats for the rooftop"),("Celebration","The Rooftop Ballroom","Midnight until late","Champagne, dinner and the count of the year")],
  thanks="Midnight came right on time. Thank you for spending the last night of the year with us.",
  rsvp_h="Tell us you'll be there at midnight.", rsvp_p="Kindly reply by December 1 - the champagne is being counted.", yes="Delightedly accepts", no="Regretfully declines",
  reg_p="If you would like to give more, we have gathered a few things for the apartment - and a fund for the trip we leave on New Year's Day.",
  faq=[("How formal is black tie?","Tuxedos, floor-length gowns, and anything you would wear to the opera. Sequins are encouraged after midnight."),("Is there parking?","Valet at the Michigan Avenue entrance from 9:30. The hotel garage is next door."),("Will it really go past midnight?","The ceremony ends at midnight and dinner starts after. Plan on being out until at least two.")],
  extra_css=CALM_CSS + """
.hero-full::after{background:linear-gradient(to bottom,rgba(0,0,0,.42),rgba(0,0,0,.18) 40%,rgba(8,8,10,.92) 96%)}
""",
 ),

 "dune": spec(
  name="Dune", title="Dune — a desert wedding website template | Lazo",
  desc="A free desert wedding website template from Lazo — golden hour, dusk and clay, with RSVPs, schedule, registry, and a site that says We're Married after the big day.",
  fonts="family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Karla:wght@300;400;500&display=swap",
  serif='"Fraunces",serif', display='"Fraunces",serif', sans='"Karla",sans-serif',
  palettes={"golden":{"--bg":"#FBF6EE","--ink":"#3A2A1E","--mut":"#8C7561","--acc":"#C07A3A","--panel":"#FFFFFF","--line":"#EDDDC8","--sand":"#F4E6D2"},
            "dusk":{"--bg":"#F9F4F3","--ink":"#3A2A33","--mut":"#8B737E","--acc":"#A5566B","--panel":"#FFFFFF","--line":"#EAD9DE","--sand":"#F1E4E7"},
            "clay":{"--bg":"#FAF5F1","--ink":"#3B2B24","--mut":"#8C776D","--acc":"#B25A3C","--panel":"#FFFFFF","--line":"#ECDBD1","--sand":"#F3E5DB"},
            "sandsky":{"--bg":"#F7F8FA","--ink":"#2E3642","--mut":"#74808F","--acc":"#4E6E8E","--panel":"#FFFFFF","--line":"#DCE2EA","--sand":"#E9EDF2"}},
  hero="full", hero_img=img("1500534314209-a25ddb2bd429", 1900), hero_filter="saturate(1.05) brightness(.9)",
  eyebrow="At golden hour", cdlabel="days until golden hour", n1="Sofia", n2="Mateo",
  where="La Casa Adobe · Scottsdale, Arizona", date="2027-03-06",
  story_h="The last horchata, and everything after.", story_p="We met over the last horchata at a taqueria that closed a year later. Five springs on, we are getting married in a courtyard that faces west, with the people who kept coming back.",
  story_img=img("1515934751635-c81c6bc9a2d8", 1000), story_cap="Five springs in",
  gal_h="The desert, and us in it.", gal=[(img("1520854221256-17451cc331bf"), "The two of us, golden hour"), (img("1606216794074-735e91aa2c92", 900), "Two rings, one horchata"), (img("1591604466107-ec97de577aff", 900), "Candlelit, always")],
  day_h="Ceremony at golden hour. Everything after, under the string lights.",
  sched=[("5:15 pm","Agua frescas in the courtyard"),("5:45 pm","Ceremony - face west"),("6:30 pm","Cocktails in the cactus garden"),("7:30 pm","Dinner under the string lights"),("9:30 pm","Dancing until the desert cools")],
  ven=[("Ceremony","The Courtyard","5:45 in the evening","Sunglasses for the ceremony, a layer for the night"),("Fiesta","The Cactus Garden","6:30 until late","Dinner, toasts and a very long dance")],
  thanks="The sun set exactly where we said it would. Thank you for coming out to the desert for us.",
  rsvp_h="Tell us you're coming to the desert.", rsvp_p="Kindly reply by February 1 - the taco count is a precise science.", yes="Joyfully accepts", no="Regretfully declines",
  reg_p="If you would like to give more, we have gathered a few things for the casita - and a fund for the road trip down the coast.",
  faq=[("What's the dress code?","Desert cocktail - linen, silk, earth tones, and shoes that can handle gravel. It is warm at six and cold by nine."),("Is the venue outdoors?","The ceremony and dinner are; the cantina is inside if the weather turns. Heaters come out after dark."),("Where should we stay?","We have a block at the resort down the road under our names; the details are in your invitation.")],
 ),

 "fete": spec(
  name="Fête", title="Fête — a classic formal wedding website template | Lazo",
  desc="A free classic wedding website template from Lazo — navy, blush, forest and black tie, with RSVPs, schedule, registry, and a site that says We're Married after the big day.",
  fonts="family=Playfair+Display:ital,wght@0,400;0,500;0,600;1,400&family=EB+Garamond:ital,wght@0,400;0,500;1,400&display=swap",
  serif='"EB Garamond",serif', display='"Playfair Display",serif', sans='"EB Garamond",serif',
  palettes={"navy":{"--bg":"#FBF9F5","--ink":"#1F2A44","--mut":"#6B7286","--acc":"#2B3D6B","--panel":"#FFFFFF","--line":"#E3E1DA","--sand":"#F1EEE6"},
            "blush":{"--bg":"#FCF8F6","--ink":"#3E3236","--mut":"#8C7D82","--acc":"#C88A93","--panel":"#FFFFFF","--line":"#EFE0E2","--sand":"#F6EAEC"},
            "forest":{"--bg":"#F8FAF7","--ink":"#22332A","--mut":"#6C7C72","--acc":"#2F5B45","--panel":"#FFFFFF","--line":"#DCE4DE","--sand":"#EAF0EB"},
            "blacktie":{"--bg":"#FAF9F7","--ink":"#1B1B1B","--mut":"#6E6E6E","--acc":"#B08D3E","--panel":"#FFFFFF","--line":"#E4E2DD","--sand":"#F0EEE8"}},
  hero="full", hero_img=img("1520854221256-17451cc331bf", 1900), hero_filter="saturate(.9) brightness(.86)",
  eyebrow="The honour of your presence", cdlabel="days until the fête", n1="Charlotte", n2="Henry",
  where="Magnolia Hall · Charleston, South Carolina", date="2027-06-12",
  story_h="Eight seasons of Sunday suppers.", story_p="It began with a Sunday supper neither of us was supposed to attend. Eight seasons of them later, we are getting married on the lawn where the first one ended, with everyone who ever pulled up a chair.",
  story_img=img("1529636798458-92182e662485", 1000), story_cap="Eight seasons in",
  gal_h="A formal affair, fondly.", gal=[(img("1591604466107-ec97de577aff"), "The first dance"), (img("1522413452208-996ff3f3e740", 900), "A sparkling send-off"), (img("1520854221256-17451cc331bf", 900), "To the happy couple")],
  day_h="An evening of ceremony, supper, and dancing on the lawn.",
  sched=[("5:00 pm","Guests are seated; the quartet plays"),("5:30 pm","The ceremony"),("6:15 pm","Cocktails on the terrace"),("7:30 pm","Supper in the garden tent"),("9:30 pm","Dancing on the lawn until eleven")],
  ven=[("Ceremony","The Magnolia Lawn","5:30 in the evening","Heels sink; wedges and flats are wise"),("Reception","The Garden Tent","6:15 until eleven","Supper, toasts and dancing under the tent")],
  thanks="The magnolias held their bloom for us. Thank you for the honour of your presence.",
  rsvp_h="The favour of a reply is requested.", rsvp_p="Kindly reply by May 1 - the seating chart is a work of diplomacy.", yes="Accepts with pleasure", no="Declines with regret",
  reg_p="If you would like to give more, we have gathered a few things for the house - and a fund for the honeymoon along the coast.",
  faq=[("What is the dress code?","Formal - suits or tuxedos, long dresses or elegant cocktail. The lawn is soft, so mind the heels."),("May we bring children?","We adore them, and we have planned an evening for grown-ups. Babes in arms are always welcome."),("Where should we stay?","We have a block at the inn on the square under our names; the details are in your invitation.")],
 ),

 "tide": spec(
  name="Tide", title="Tide — a coastal wedding website template | Lazo",
  desc="A free coastal wedding website template from Lazo — seaglass, harbor, coral and storm, with RSVPs, schedule, registry, and a site that says We're Married after the big day.",
  fonts="family=Cormorant:ital,wght@0,500;0,600;1,500&family=Nunito+Sans:wght@300;400;500&display=swap",
  serif='"Cormorant",serif', display='"Cormorant",serif', sans='"Nunito Sans",sans-serif',
  palettes={"seaglass":{"--bg":"#F6FAF9","--ink":"#22403F","--mut":"#6C8887","--acc":"#4E9A93","--panel":"#FFFFFF","--line":"#D8E8E6","--sand":"#E7F1EF"},
            "harbor":{"--bg":"#F5F8FB","--ink":"#1F3448","--mut":"#68798A","--acc":"#2F5D86","--panel":"#FFFFFF","--line":"#D8E2EC","--sand":"#E6EDF4"},
            "coral":{"--bg":"#FCF7F5","--ink":"#3E2E2B","--mut":"#8F7A75","--acc":"#E0715C","--panel":"#FFFFFF","--line":"#F0DDD8","--sand":"#F7E8E3"},
            "storm":{"--bg":"#F5F6F8","--ink":"#2A3038","--mut":"#737B86","--acc":"#4A5A6E","--panel":"#FFFFFF","--line":"#DDE1E7","--sand":"#EAEDF1"}},
  hero="full", hero_img=img("1507525428034-b723cf961d3e", 1900), hero_filter="saturate(.95) brightness(.9)",
  eyebrow="Where the land runs out", cdlabel="days until the tide turns", n1="Nora", n2="Beck",
  where="Windward Point · Cape Cod, Massachusetts", date="2027-08-21",
  story_h="Two towels, one sandbar, no plan.", story_p="We met on a sandbar that disappears twice a day, and stayed until it did. Six summers later we are getting married on the bluff above it, with the people who never asked us to leave early.",
  story_img=img("1505142468610-359e7d316be0", 1000), story_cap="Six summers in",
  gal_h="Salt, light, and the two of us.", gal=[(img("1473116763249-2faaef81ccda"), "The point at low tide"), (img("1505142468610-359e7d316be0", 900), "Where he asked"), (img("1511285560929-80b456fea0bc", 900), "Evenings like this one")],
  day_h="Ceremony on the bluff, dinner by the water, shoes optional throughout.",
  sched=[("4:00 pm","Guests arrive - cold lemonade, colder oysters"),("4:30 pm","Ceremony on the bluff"),("5:15 pm","Cocktails as the boats come in"),("6:30 pm","Dinner at the boathouse"),("8:30 pm","Bonfire and dancing until the tide turns")],
  ven=[("Ceremony","The Bluff","4:30 in the afternoon","Windy; bring a wrap and skip the hat"),("Reception","The Boathouse","5:15 until the tide turns","Dinner, toasts and a bonfire on the sand")],
  thanks="The tide turned right on time. Thank you for coming out to the point with us.",
  rsvp_h="Tell us you're coming ashore.", rsvp_p="Kindly reply by July 15 - the oyster count waits for no one.", yes="Coming ashore", no="Waving from dry land",
  reg_p="If you would like to give more, we have gathered a few things for the cottage - and a fund for the sailboat we keep pricing.",
  faq=[("What should I wear?","Coastal cocktail - linen, sundresses, and sandals you can slip off. Bring a layer for the bluff."),("Is it really barefoot?","The ceremony is on the grass above the beach; the boathouse has a floor. Heels are your call."),("Where should we stay?","We have a block at the inn by the harbor under our names; the details are in your invitation.")],
 ),

 "flora": spec(
  name="Flora", title="Flora — a floral wedding website template | Lazo",
  desc="A free floral wedding website template from Lazo — rose, peony, wildflower and dusk garden, with RSVPs, schedule, registry, and a site that says We're Married after the big day.",
  fonts="family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500;1,600&family=Mulish:wght@300;400;500&display=swap",
  serif='"Cormorant Garamond",serif', display='"Cormorant Garamond",serif', sans='"Mulish",sans-serif',
  palettes={"rose":{"--bg":"#FDF8F8","--ink":"#43303A","--mut":"#917C86","--acc":"#C86B84","--panel":"#FFFFFF","--line":"#F1DEE3","--sand":"#F8E9ED"},
            "peony":{"--bg":"#FCF7F5","--ink":"#3F2E30","--mut":"#8E7B7E","--acc":"#D4837E","--panel":"#FFFFFF","--line":"#F0DDD9","--sand":"#F7E8E4"},
            "wildflower":{"--bg":"#FAF9F5","--ink":"#3A3A2E","--mut":"#84846F","--acc":"#8E8A3E","--panel":"#FFFFFF","--line":"#E7E5D3","--sand":"#F0EEDF"},
            "duskgarden":{"--bg":"#F8F6FA","--ink":"#352E44","--mut":"#7F7793","--acc":"#6E5C9E","--panel":"#FFFFFF","--line":"#E3DDED","--sand":"#EDE8F4"}},
  hero="full", hero_img=img("1487530811176-3780de880c2d", 1900), hero_filter="saturate(.98) brightness(.88)",
  eyebrow="A garden in bloom", cdlabel="days until everything blooms", n1="Rosie", n2="Theo",
  where="The Conservatory · Savannah, Georgia", date="2027-04-24",
  story_h="It started with the wrong bouquet.", story_p="A florist's mix-up sent her peonies to his door. Five springs later we are getting married under the glass of the conservatory, with the people who told us to keep the flowers.",
  story_img=img("1455659817273-f96807779a8a", 1000), story_cap="Five springs in",
  gal_h="Five springs, pressed and kept.", gal=[(img("1490750967868-88aa4486c946"), "The conservatory in April"), (img("1465495976277-4387d4b0b4c6", 900), "Peony season, always"), (img("1519378058457-4c29a0a2efac", 900), "Candlelight and petals")],
  day_h="Vows among the vines, dinner under glass.",
  sched=[("4:30 pm","Guests arrive - rose lemonade in the orangery"),("5:00 pm","Ceremony in the palm house"),("5:45 pm","Cocktails in the garden"),("7:00 pm","Dinner under glass"),("9:00 pm","Dancing until the candles burn down")],
  ven=[("Ceremony","The Palm House","5:00 in the evening","Warm under the glass; dress light"),("Reception","The Orangery","5:45 until late","Dinner, toasts and a very long dance")],
  thanks="Everything bloomed on schedule. Thank you for being in the garden with us.",
  rsvp_h="Say you'll be in the garden.", rsvp_p="Kindly reply by March 20 - the florist needs a count.", yes="Joyfully accepts", no="Regretfully declines",
  reg_p="If you would like to give more, we have gathered a few things for the house - and a fund for the garden we are finally planting.",
  faq=[("What should I wear?","Garden party - florals, soft colours, and shoes that can handle a brick path. The glasshouse is warm."),("Are kids welcome?","We love them, and we have planned a grown-up evening. Babes in arms are always welcome."),("Where should we stay?","We have a block at the hotel on the square under our names; the details are in your invitation.")],
 ),

 "atelier": spec(
  name="Atelier", title="Atelier — a modern minimalist wedding website template | Lazo",
  desc="A free modern wedding website template from Lazo — gallery white, carbon, crimson and cobalt, with RSVPs, schedule, registry, and a site that says We're Married after the big day.",
  fonts="family=Archivo:wght@300;400;500;600&family=Archivo+Expanded:wght@500;600&family=Instrument+Serif:ital@0;1&display=swap",
  serif='"Instrument Serif",serif', display='"Archivo Expanded","Archivo",sans-serif', sans='"Archivo",sans-serif',
  palettes={"gallery":{"--bg":"#FAFAF8","--ink":"#151515","--mut":"#6F6F6A","--acc":"#151515","--panel":"#FFFFFF","--line":"#E4E4DF","--sand":"#F0F0EC"},
            "carbon":{"--bg":"#111111","--ink":"#F2F2EE","--mut":"#9A9A94","--acc":"#F2F2EE","--panel":"#191919","--line":"#2C2C2C","--sand":"#1E1E1E"},
            "crimson":{"--bg":"#FBF8F7","--ink":"#1B1516","--mut":"#7A6E70","--acc":"#B3202E","--panel":"#FFFFFF","--line":"#EADFDF","--sand":"#F3E9E9"},
            "cobalt":{"--bg":"#F8F9FB","--ink":"#131A2B","--mut":"#6C7386","--acc":"#1F3FBF","--panel":"#FFFFFF","--line":"#DEE2EC","--sand":"#EAEDF4"}},
  hero="full", hero_img=img("1606216794074-735e91aa2c92", 1900), hero_filter="grayscale(1) contrast(1.08) brightness(.86)",
  eyebrow="A small wedding, well made", cdlabel="days", n1="Ines", n2="Kai",
  where="Studio 4B · Brooklyn, New York", date="2027-05-15",
  story_h="We measured twice.", story_p="We met over a set of drawings that were wrong in the same place. Three years later we are getting married in the studio where we fixed them, with forty people and one very long table.",
  story_img=img("1520854221256-17451cc331bf", 1000), story_cap="Three years in",
  gal_h="Selected works.", gal=[(img("1511285560929-80b456fea0bc"), "Fig. 2 - the light we chose"), (img("1522413452208-996ff3f3e740", 900), "Fig. 3 - the studio"), (img("1522413452208-996ff3f3e740", 900), "Fig. 4 - details")],
  day_h="One table. Forty chairs. No speeches over four minutes.",
  sched=[("5:00 pm","Doors - natural wine, no name tags"),("5:30 pm","Ceremony by the window"),("6:00 pm","Drinks on the roof"),("7:00 pm","Dinner at the long table"),("9:30 pm","Records until the neighbours mind")],
  ven=[("Ceremony","The Window Wall","5:30 in the evening","Stand where the light is; there are no rows"),("Dinner","The Long Table","7:00 until late","One table, one menu, one very good playlist")],
  thanks="Forty chairs, all of them full. Thank you for making it.",
  rsvp_h="Forty chairs. One is yours.", rsvp_p="Reply by April 15 - the table is exactly as long as it needs to be.", yes="I'll be there", no="I can't make it",
  reg_p="If you would like to give more, we have gathered a few things for the apartment - and a fund for the chairs we keep not buying.",
  faq=[("Dress code?","Wear something you love. Black is welcome. So is colour."),("Can I bring a plus one?","If your invitation names one. The table is exactly forty."),("Where should we stay?","A few hotels within walking distance are listed with your invitation.")],
  extra_css=CALM_CSS + """
.k{letter-spacing:.4em;font-family:var(--sans)}
h1,h2,h3{letter-spacing:-.02em}
.hero-full .eyebrow{font-family:var(--sans)}
""",
 ),

 "verona": spec(
  name="Verona", title="Verona — a vineyard & Italian villa wedding website template | Lazo",
  desc="A free vineyard wedding website template from Lazo — harvest, Tuscan, olive and ink cream, with RSVPs, schedule, registry, and a site that says We're Married after the big day.",
  fonts="family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,500;1,9..144,400&family=Lora:ital,wght@0,400;0,500;1,400&display=swap",
  serif='"Lora",serif', display='"Fraunces",serif', sans='"Lora",serif',
  palettes={"harvest":{"--bg":"#FBF6EF","--ink":"#3A2A20","--mut":"#8B7562","--acc":"#9C4A2E","--panel":"#FFFFFF","--line":"#ECDCCB","--sand":"#F4E7D6"},
            "tuscan":{"--bg":"#FAF5EE","--ink":"#3B2F24","--mut":"#8B7A67","--acc":"#C3823A","--panel":"#FFFFFF","--line":"#EBDCC8","--sand":"#F3E6D3"},
            "olive":{"--bg":"#F8F8F2","--ink":"#2F3327","--mut":"#727863","--acc":"#6E7A3C","--panel":"#FFFFFF","--line":"#E0E2D0","--sand":"#ECEDDD"},
            "inkcream":{"--bg":"#FAF8F3","--ink":"#1F2530","--mut":"#6E7480","--acc":"#2C3A55","--panel":"#FFFFFF","--line":"#E3E1DA","--sand":"#F0EDE4"}},
  hero="full", hero_img=img("1506377247377-2a5b3b417ebb", 1900), hero_filter="saturate(1.02) brightness(.9)",
  eyebrow="Between the vines", cdlabel="days until the harvest toast", n1="Elena", n2="Sam",
  where="Bellorno Vineyard · Willamette Valley, Oregon", date="2027-10-02",
  story_h="A bottle we couldn't pronounce.", story_p="We met arguing over how to say the name of a wine neither of us could afford. Seven years later we are getting married at the end of row twelve, with the people who have shared every bottle since.",
  story_img=img("1528823872057-9c018a7a7553", 1000), story_cap="Seven years in",
  gal_h="Seven years, uncorked.", gal=[(img("1510076857177-7470076d4098"), "The rows in October"), (img("1528823872057-9c018a7a7553", 900), "The toast rehearsal"), (img("1414235077428-338989a2e8c0", 900), "The long table")],
  day_h="Vows in the rows, dinner in the barrel room.",
  sched=[("3:30 pm","Guests arrive - a glass of the good stuff"),("4:00 pm","Ceremony at the end of row twelve"),("4:45 pm","Cocktails on the terrace"),("6:00 pm","Dinner in the barrel room"),("8:30 pm","Dancing until the last cork")],
  ven=[("Ceremony","Row Twelve","4:00 in the afternoon","Gravel and grass; leave the stilettos at home"),("Reception","The Barrel Room","4:45 until the last cork","Dinner, toasts and a very long dance")],
  thanks="The harvest came in on time. Thank you for raising a glass with us.",
  rsvp_h="Raise a glass with us.", rsvp_p="Kindly reply by September 1 - the cellar is being counted.", yes="Joyfully accepts", no="Regretfully declines",
  reg_p="If you would like to give more, we have gathered a few things for the house - and a fund for the trip to the real Verona.",
  faq=[("What should I wear?","Vineyard cocktail - linen, silk, earth tones, and shoes that can handle gravel and grass. Bring a layer for the barrel room."),("Is it outdoors?","The ceremony is; the barrel room is inside and stays cool. Rain moves the ceremony under the terrace roof."),("Where should we stay?","We have a block at the inn in town under our names; the details are in your invitation.")],
 ),

 "shore": spec(
  name="Shore", title="Shore — an ocean wedding website template | Lazo",
  desc="A free ocean wedding website template from Lazo — lagoon, sunset, driftwood and deep, with RSVPs, schedule, registry, and a site that says We're Married after the big day.",
  fonts="family=Italiana&family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500&family=Jost:wght@300;400;500&display=swap",
  serif='"Cormorant Garamond",serif', display='"Italiana","Cormorant Garamond",serif', sans='"Jost",sans-serif',
  palettes={"lagoon":{"--bg":"#F7FBFA","--ink":"#17384A","--mut":"#5F7E8C","--acc":"#1B7F8C","--panel":"#FFFFFF","--line":"#D7E7EA","--sand":"#F2E8D5"},
            "sunset":{"--bg":"#FBF5F0","--ink":"#3A2A24","--mut":"#8C7468","--acc":"#E0745A","--panel":"#FFFFFF","--line":"#F0DDD3","--sand":"#F6E7D2"},
            "driftwood":{"--bg":"#F8F5EF","--ink":"#33302A","--mut":"#7E7568","--acc":"#8C7355","--panel":"#FFFFFF","--line":"#E7DFD1","--sand":"#EFE4D0"},
            "deep":{"--bg":"#F3F7F9","--ink":"#132A3A","--mut":"#5C7385","--acc":"#1E4C6E","--panel":"#FFFFFF","--line":"#D5E1E9","--sand":"#EFE6D3"}},
  hero="full", hero_img=img("1519046904884-53103b34b206", 1900), hero_filter="saturate(1.02) brightness(.9)",
  eyebrow="Where the water meets the sand", cdlabel="days until high tide", n1="Marina", n2="Cole",
  where="Pelican Point · Laguna Beach, California", date="2027-06-12",
  story_h="A boardwalk, two coffees, and a very long walk.", story_p="We met on the pier the morning after a storm - the water was wild and neither of us wanted to go home. Six summers later we are getting married on the sand below it, with the people who kept walking with us.",
  story_img=img("1471922694854-ff1b63b20054", 1000), story_cap="Six summers in",
  gal_h="Salt air, sea light, the two of us.", gal=[(img("1473116763249-2faaef81ccda"), "The point at low tide"), (img("1505142468610-359e7d316be0", 900), "Where he asked"), (img("1507525428034-b723cf961d3e", 900), "Evenings like this one")],
  day_h="Vows on the sand, dinner on the deck, dancing until the tide comes in.",
  sched=[("4:00 pm","Guests arrive - cold drinks and colder oysters"),("4:30 pm","Ceremony on the sand"),("5:15 pm","Cocktails as the boats come in"),("6:30 pm","Dinner on the deck"),("8:30 pm","Bonfire and dancing until the tide comes in")],
  ven=[("Ceremony","The Beach","4:30 in the afternoon","Bare feet welcome - the sand is soft"),("Reception","The Boathouse Deck","5:15 until the last wave","Dinner, toasts and a bonfire")],
  thanks="The tide came in right on time. Thank you for coming down to the water with us.",
  rsvp_h="Tell us you're coming to the shore.", rsvp_p="Kindly reply by May 1 - the oyster count waits for no one.", yes="Coming to the shore", no="Waving from dry land",
  note_ph="Dietary notes, song requests, questions about the tide…",
  reg_p="If you would like to give more, we have gathered a few things for the cottage - and a fund for the sailboat we keep talking about.",
  faq=[("What should I wear?","Beach cocktail - linen, sundresses, sandals you can slip off. Bring a layer for the bonfire."),("Is it really on the sand?","The ceremony is; the deck has a floor. Heels are your call."),("Where should we stay?","We have a block at the inn above the point under our names; the details are in your invitation.")],
 ),

 "summit": spec(
  name="Summit", title="Summit — a mountain wedding website template | Lazo",
  desc="A free mountain wedding website template from Lazo — alpine, granite, aspen and glacier, with RSVPs, schedule, registry, and a site that says We're Married after the big day.",
  fonts="family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Work+Sans:wght@300;400;500&display=swap",
  serif='"Fraunces",serif', display='"Fraunces",serif', sans='"Work Sans",sans-serif',
  palettes={"alpine":{"--bg":"#F6F8F6","--ink":"#22312B","--mut":"#69796F","--acc":"#3E6B57","--panel":"#FFFFFF","--line":"#D9E3DC","--sand":"#E9EFEA"},
            "granite":{"--bg":"#F6F6F5","--ink":"#2A2D31","--mut":"#71767C","--acc":"#4C5560","--panel":"#FFFFFF","--line":"#DEDFE1","--sand":"#EBECEC"},
            "aspen":{"--bg":"#FBF7EF","--ink":"#3B2F20","--mut":"#8C7B63","--acc":"#C8912E","--panel":"#FFFFFF","--line":"#ECDFC9","--sand":"#F4E8D4"},
            "glacier":{"--bg":"#F4F8FB","--ink":"#1F3344","--mut":"#657A8B","--acc":"#3A7CA5","--panel":"#FFFFFF","--line":"#D6E3EC","--sand":"#E5EEF4"}},
  hero="full", hero_img=img("1464822759023-fed622ff2c3b", 1900), hero_filter="saturate(.96) brightness(.88)",
  eyebrow="Above the treeline", cdlabel="days until the summit", n1="Juniper", n2="Reed",
  where="Timber Ridge · Aspen, Colorado", date="2027-09-04",
  story_h="Two headlamps, one trail, no map.", story_p="We met at a trailhead at four in the morning, both of us wrong about the route. Five summers later we are getting married above the treeline, with the people who hiked in behind us.",
  story_img=img("1469474968028-56623f02e42e", 1000), story_cap="Five summers in",
  gal_h="Thin air, long light, the two of us.", gal=[(img("1497436072909-60f360e1d4b1"), "The ridge at sunrise"), (img("1500534314209-a25ddb2bd429", 900), "Where she asked"), (img("1506905925346-21bda4d32df4", 900), "The valley from the lodge")],
  day_h="Vows on the ridge, dinner at the lodge, stars from the deck.",
  sched=[("3:00 pm","Guests arrive - the chairlift runs until 3:30"),("4:00 pm","Ceremony on the ridge"),("4:45 pm","Cocktails on the deck"),("6:00 pm","Dinner at the lodge"),("8:30 pm","Dancing, then the stars from the deck")],
  ven=[("Ceremony","The Ridge","4:00 in the afternoon","Thin air and a ten-minute walk; take it slow"),("Reception","Timber Ridge Lodge","4:45 until the fire burns down","Dinner, toasts and a very long dance")],
  thanks="The clouds parted at four on the dot. Thank you for climbing up here with us.",
  rsvp_h="Tell us you're coming up the mountain.", rsvp_p="Kindly reply by August 1 - the chairlift needs a count.", yes="Coming up the mountain", no="Sending love from sea level",
  reg_p="If you would like to give more, we have gathered a few things for the cabin - and a fund for the trek we keep planning.",
  faq=[("What should I wear?","Mountain formal - suits and long dresses with real shoes. It is warm at four and cold by seven; bring a wrap or a jacket."),("How do we get up there?","The chairlift runs from three; it is a ten-minute walk from the top. Anyone who would rather not ride can take the lodge shuttle."),("Where should we stay?","We have a block at the lodge under our names; the details are in your invitation.")],
 ),

 "ranch": spec(
  name="Ranch", title="Ranch — a rustic barn wedding website template | Lazo",
  desc="A free rustic barn wedding website template from Lazo — saddle, denim, prairie and dusk, with RSVPs, schedule, registry, and a site that says We're Married after the big day.",
  fonts="family=Playfair+Display:ital,wght@0,400;0,500;0,600;1,400&family=Zilla+Slab:ital,wght@0,400;0,500;1,400&family=Karla:wght@300;400;500&display=swap",
  serif='"Zilla Slab",serif', display='"Playfair Display",serif', sans='"Karla",sans-serif',
  palettes={"saddle":{"--bg":"#FAF6F0","--ink":"#3A2A1C","--mut":"#8A7660","--acc":"#8F5A2B","--panel":"#FFFFFF","--line":"#EADDCB","--sand":"#F2E7D6"},
            "denim":{"--bg":"#F6F8FA","--ink":"#22303F","--mut":"#69788A","--acc":"#3B5A7E","--panel":"#FFFFFF","--line":"#D9E2EB","--sand":"#E8EEF3"},
            "prairie":{"--bg":"#FAF9F3","--ink":"#3A3826","--mut":"#84806A","--acc":"#9A8A3C","--panel":"#FFFFFF","--line":"#E8E5D2","--sand":"#F1EEDF"},
            "dusk":{"--bg":"#F9F5F5","--ink":"#3A2A33","--mut":"#8A727E","--acc":"#8F4E68","--panel":"#FFFFFF","--line":"#EAD9DF","--sand":"#F1E4E8"}},
  hero="full", hero_img=img("1470071459604-3b5ec3a7fe05", 1900), hero_filter="saturate(1.02) brightness(.88)",
  eyebrow="Out where the land goes on", cdlabel="days until we say I do", n1="June", n2="Wyatt",
  where="Silver Creek Ranch · Bandera, Texas", date="2027-10-09",
  story_h="A borrowed truck and a flat tire.", story_p="We met on the side of a ranch road with one spare between us. Four falls later we are getting married in the barn at the end of it, with the people who have towed us home since.",
  story_img=img("1500382017468-9049fed747ef", 1000), story_cap="Four falls in",
  gal_h="Big sky, long tables, the two of us.", gal=[(img("1441974231531-c6227db76b6e"), "The creek in October"), (img("1504280390367-361c6d9f38f4", 900), "Where he asked"), (img("1513836279014-a89f7a76ae86", 900), "The road to the barn")],
  day_h="Vows under the live oak, dinner in the barn, a bonfire until the last log.",
  sched=[("4:00 pm","Guests arrive - sweet tea and something stronger"),("4:30 pm","Ceremony under the live oak"),("5:15 pm","Cocktails on the porch"),("6:30 pm","Dinner in the barn"),("8:30 pm","Bonfire and a two-step until the last log")],
  ven=[("Ceremony","The Live Oak","4:30 in the afternoon","Grass and gravel; boots welcome"),("Reception","The Big Barn","5:15 until the fire burns down","Dinner, toasts and a very long dance")],
  thanks="The sky did what Texas skies do. Thank you for driving out to the ranch for us.",
  rsvp_h="Tell us you're coming out to the ranch.", rsvp_p="Kindly reply by September 10 - the brisket count is serious business.", yes="Coming out to the ranch", no="Sending love from town",
  reg_p="If you would like to give more, we have gathered a few things for the house - and a fund for the porch we are finally building.",
  faq=[("What should I wear?","Ranch cocktail - denim is fine, boots are better, and anything you would wear to a good dinner outdoors. It cools quickly after sunset."),("Is it outdoors?","The ceremony is; the barn has a roof, fans and heaters. Rain moves the ceremony inside."),("Where should we stay?","We have a block at the inn in town under our names; the details are in your invitation.")],
 ),

 "starlit": spec(
  name="Starlit", title="Starlit — a celestial night-sky wedding website template | Lazo",
  desc="A free celestial wedding website template from Lazo — midnight, nebula, aurora and ember, with RSVPs, schedule, registry, and a site that says We're Married after the big day.",
  fonts="family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500&family=Jost:wght@300;400;500&display=swap",
  serif='"Cormorant Garamond",serif', display='"Cormorant Garamond",serif', sans='"Jost",sans-serif',
  palettes={"midnight":{"--bg":"#0E1220","--ink":"#EEF0F6","--mut":"#9AA0B4","--acc":"#D6B86A","--panel":"#161B2C","--line":"#262C40","--sand":"#1B2032"},
            "nebula":{"--bg":"#150F22","--ink":"#F1ECF7","--mut":"#A497B8","--acc":"#C58BD9","--panel":"#1E1730","--line":"#322745","--sand":"#241C38"},
            "aurora":{"--bg":"#0C1A1A","--ink":"#E9F3F1","--mut":"#8FA9A4","--acc":"#4FC3A1","--panel":"#132424","--line":"#233736","--sand":"#182B2A"},
            "ember":{"--bg":"#1A1210","--ink":"#F5ECE6","--mut":"#AD9A8F","--acc":"#E08A4E","--panel":"#241A17","--line":"#3A2C27","--sand":"#2A1F1B"}},
  hero="full", hero_img=img("1419242902214-272b3f66ee7a", 1900), hero_filter="saturate(1.05) brightness(.9)",
  eyebrow="Under a sky full of stars", cdlabel="nights until we say I do", n1="Celeste", n2="Adrian",
  where="Cielo Vineyard · Paso Robles, California", date="2027-09-18",
  story_h="A meteor shower, two blankets, and a very late night.", story_p="We met on a hill at two in the morning, both of us waiting for the same meteor shower. Four Augusts later we are getting married under the same sky, with the people who stayed up with us.",
  story_img=img("1444703686981-a3abbc4d4fe3", 1000), story_cap="Four Augusts in",
  gal_h="Night light, and the two of us in it.", gal=[(img("1464802686167-b939a6910659"), "The sky over the vineyard"), (img("1502134249126-9f3755a50d78", 900), "Where she asked"), (img("1519681393784-d120267933ba", 900), "The ridge after dark")],
  day_h="Vows at dusk, dinner under the stars, dancing until the sky turns.",
  sched=[("6:00 pm","Guests arrive - a glass as the light goes"),("6:45 pm","Ceremony at dusk"),("7:30 pm","Cocktails as the stars come out"),("8:30 pm","Dinner under the sky"),("10:30 pm","Dancing until the sky turns")],
  ven=[("Ceremony","The Hilltop","6:45 in the evening","Dusk, then dark; bring a layer"),("Reception","The Vineyard Terrace","7:30 until the sky turns","Dinner, toasts and a very long dance")],
  thanks="The sky was clear right on time. Thank you for staying up with us.",
  rsvp_h="Tell us you'll be under the stars.", rsvp_p="Kindly reply by August 15 - the telescope has a waiting list.", yes="Under the stars with you", no="Wishing on one from afar",
  reg_p="If you would like to give more, we have gathered a few things for the house - and a fund for the trip to see the northern lights.",
  faq=[("What should I wear?","Evening cocktail - deep colours, a little shimmer, and a layer for after dark. Grass and gravel underfoot."),("Is it outdoors?","Yes, all of it, under the sky. The barn is there if the weather turns."),("Where should we stay?","We have a block at the inn in town under our names; the details are in your invitation.")],
  extra_css=CALM_CSS + """
.hero-full::after{background:linear-gradient(to bottom,rgba(0,0,0,.4),rgba(0,0,0,.16) 40%,rgba(8,8,10,.92) 96%)}
""",
 ),

 "frost": spec(
  name="Frost", title="Frost — a winter wedding website template | Lazo",
  desc="A free winter wedding website template from Lazo — ice, evergreen, berry and silver, with RSVPs, schedule, registry, and a site that says We're Married after the big day.",
  fonts="family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500&family=Libre+Baskerville:ital,wght@0,400;1,400&family=Lato:wght@300;400;700&display=swap",
  serif='"Libre Baskerville",serif', display='"Cormorant Garamond",serif', sans='"Lato",sans-serif',
  palettes={"ice":{"--bg":"#F6F9FB","--ink":"#22323F","--mut":"#6B7C8A","--acc":"#5B8DB0","--panel":"#FFFFFF","--line":"#D8E4EC","--sand":"#E7EFF4"},
            "evergreen":{"--bg":"#F5F8F6","--ink":"#1F3129","--mut":"#67786F","--acc":"#2F5C46","--panel":"#FFFFFF","--line":"#D7E3DC","--sand":"#E6EEE9"},
            "berry":{"--bg":"#FBF6F7","--ink":"#3A2129","--mut":"#8A6E76","--acc":"#9C2F4B","--panel":"#FFFFFF","--line":"#ECD9DE","--sand":"#F3E4E8"},
            "silver":{"--bg":"#F7F7F8","--ink":"#2B2E33","--mut":"#74787E","--acc":"#6E7580","--panel":"#FFFFFF","--line":"#DFE1E4","--sand":"#ECEDEF"}},
  hero="full", hero_img=img("1418985991508-e47386d96a71", 1900), hero_filter="saturate(.9) brightness(.9)",
  eyebrow="In the deep of winter", cdlabel="days until the first snow", n1="Ingrid", n2="Elias",
  where="The Glass Chapel · Stowe, Vermont", date="2027-01-16",
  story_h="A snow day, a shared cab, and the wrong stop.", story_p="We met in a taxi neither of us had called, the night the city shut down for snow. Six winters later we are getting married in a glass chapel in the woods, with the people who kept us warm.",
  story_img=img("1478827387698-1527781a4887", 1000), story_cap="Six winters in",
  gal_h="Snow light, candlelight, the two of us.", gal=[(img("1483921020237-2ff51e8e4b22"), "The woods in January"), (img("1491002052546-bf38f186af56", 900), "Where he asked"), (img("1517299321609-52687d1bc55a", 900), "The lodge after dark")],
  day_h="Vows in the glass chapel, dinner by the fire, snow if we're lucky.",
  sched=[("3:30 pm","Guests arrive - mulled wine at the lodge"),("4:00 pm","Ceremony in the glass chapel"),("4:45 pm","Cocktails by the fire"),("6:00 pm","Dinner in the great room"),("8:30 pm","Dancing, then the sleigh back to the inn")],
  ven=[("Ceremony","The Glass Chapel","4:00 in the afternoon","Heated, but the path is snow; boots to the door, heels inside"),("Reception","The Lodge","4:45 until the fire burns down","Dinner, toasts and a very long dance")],
  thanks="It snowed at four on the dot. Thank you for coming out into the cold for us.",
  rsvp_h="Tell us you're coming in from the cold.", rsvp_p="Kindly reply by December 15 - the sleigh has a seat count.", yes="Coming in from the cold", no="Sending warmth from afar",
  reg_p="If you would like to give more, we have gathered a few things for the cabin - and a fund for the trip north to see the lights.",
  faq=[("What should I wear?","Winter formal - velvet, wool, deep colours, and a real coat for the path. There is a boot room by the chapel door."),("Is it really outdoors?","The chapel is glass and heated; the walk to it is not. Everything else is inside by a fire."),("Where should we stay?","We have a block at the inn in the village under our names; the details are in your invitation.")],
 ),
}
