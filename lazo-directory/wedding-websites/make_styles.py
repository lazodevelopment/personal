"""make_styles.py - JC-LAZO-WWSEO-0919-005
Builds the style and intent landing pages under /wedding-websites/{style}/
from the hub (index.html) plus themes.json. Zola's style filters are query
params that canonical back to one page; these are real, crawlable pages, each
with its own title, copy, matching template grid, FAQ and JSON-LD.

  python wedding-websites\\make_styles.py           # all
  python wedding-websites\\make_styles.py floral    # one
Then rebuild the hub (patch_hub_seo.py) so its chips point here. build.py
copies every wedding-websites/*/index.html into dist and the sitemap.
"""
import json, re, sys, html
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HUB_URL = "https://meetlazo.com/wedding-websites/"
THEMES = json.loads((ROOT / "themes.json").read_text(encoding="utf-8"))
HUB = (ROOT / "index.html").read_text(encoding="utf-8")

# slug -> page spec. `themes` is the ordered template list; `tags` pulls in any
# theme whose themes.json styles include that tag (after the explicit ones).
STYLES = {
 "floral": dict(themes=["flora","sage","verona"], name="Floral", h1="Floral wedding website templates", tags=["floral", "garden"],
  sub="Blooms, greenery and soft color. Free floral wedding websites with RSVPs, schedule and registry, live in minutes.",
  intro=["A floral wedding website sets the tone before the invitation is even opened. Flora leans romantic with full blooms and blush; Sage keeps it botanical with hand-drawn greenery; Verona brings harvest color and candlelight for a vineyard or fall wedding.",
         "Every design carries the same sections, so pick the one that matches your flowers and your venue, type your names, and share the link. Guests RSVP on the site and every reply lands in your Lazo planner."],
  points=["Soft palettes that match blush, sage, peony and garden-rose flowers", "Photo gallery and story sections that let your florals and venue do the talking", "Four color looks per design, so the site matches your bouquet, not the other way round"],
  faq=[("Which template is best for a garden wedding?", "Sage, with its hand-drawn greenery, is the natural fit for a garden or greenhouse wedding. Flora suits a wedding with big romantic florals, and Verona suits a vineyard or late-summer garden party."),
       ("Can we match the site colors to our flowers?", "Yes. Each design has four color looks you can switch between at any time, and the palette applies across every section of the site."),
       ("Do floral designs work on phones?", "Every Lazo design is built phone-first, since that is where nearly all guests open a wedding link. Preview any template above on a phone frame before you choose.")]),
 "garden": dict(name="Garden & greenery", h1="Garden and greenery wedding website templates", tags=["garden", "greenery"],
  sub="Hand-drawn greenery, botanical type and lots of light. Free garden wedding websites with RSVPs, schedule and registry.",
  intro=["Garden weddings are about the setting, so the website should be quiet and green. Sage is drawn for exactly this: eucalyptus and garden looks, botanical type and plenty of air around your names. Flora adds fuller blooms for a rose-garden or conservatory wedding.",
         "Add the schedule, the venue with one-tap directions, where to stay and what to wear, and your guests have everything for a day outdoors."],
  points=["Eucalyptus, sage and garden color looks", "A dress-code line and weather notes where guests will actually read them", "Nearby picks for guests staying the weekend, your favourites first"],
  faq=[("What should a garden wedding website tell guests?", "Beyond the basics, tell guests about footwear and terrain, shade and weather plans, parking or shuttles, and whether the ceremony moves indoors in rain. Every Lazo design has a FAQ section for exactly this."),
       ("Is Sage free?", "Yes. Every Lazo wedding website design is free, including RSVPs, schedule, registry links and the passcode option."),
       ("Can we add photos of the venue?", "Yes. Add a cover photo and a gallery, and they appear throughout the design.")]),
 "beach": dict(name="Beach & coastal", h1="Beach wedding website templates", tags=["beach", "coastal"],
  sub="Waves, sand and seaglass. Free beach wedding websites with travel details, RSVPs, schedule and registry.",
  intro=["A beach wedding usually means guests travelling, so the website has a job to do: flights, where to stay, what to wear on sand, and when to be where. Shore and Tide are built for it, with breezy type, coastal color looks and a travel section right up front.",
         "Shore leans ocean with waves, sand and shells; Tide is lighter and more barefoot. Both hold the schedule, the venue with directions, RSVPs and your registry."],
  points=["Lagoon, sunset, seaglass and harbor color looks", "Travel and stays section for hotel blocks, transport and tips", "Dress code and 'shoes optional' notes where guests will see them"],
  faq=[("Which is better for a destination beach wedding, Shore or Tide?", "Shore has the stronger ocean imagery and a sunset look; Tide is quieter and more coastal-casual. Preview both with your names above and go with the one that feels like your beach."),
       ("Can guests RSVP with meal choices and plus-ones?", "Yes. RSVPs collect attendance, meals, plus-ones and notes, and each reply files itself in your Lazo planner."),
       ("Can we add a hotel block and shuttle times?", "Yes. Every design has a travel section for hotel blocks, transport, parking and notes for out-of-town guests.")]),
 "destination": dict(name="Destination", h1="Destination wedding website templates", tags=["destination"],
  sub="Everything travelling guests need on one link: flights, stays, schedule, RSVPs and registry. Free.",
  intro=["For a destination wedding, the website is the itinerary. Guests need dates early, hotel blocks, how to get from the airport, the welcome drinks, the day itself and the farewell brunch, all in one place they can find on their phone.",
         "Shore, Tide, Summit and Dune all put travel front and centre, with a schedule that runs over several days and a FAQ for the questions you will otherwise answer twenty times."],
  points=["Multi-day schedule with times and locations", "Travel and stays section: flights, hotel blocks, transport, tips", "Passcode option so only invited guests see the details"],
  faq=[("When should we publish a destination wedding website?", "As early as you can, ideally with the save-the-date, so guests can book travel. Publish with the date, location and hotel block, then add the schedule and details as you confirm them."),
       ("Can we password-protect the site?", "Yes. Add a passcode and only guests with it can open the site. Passcode sites are also kept out of search engines."),
       ("Does the schedule handle several days of events?", "Yes. Add as many events as you like, each with a time, location and note, from the welcome party to the send-off.")]),
 "mountain": dict(themes=["summit","frost","ranch"], name="Mountain", h1="Mountain wedding website templates", tags=["mountain"],
  sub="Peaks, pines and alpine light. Free mountain wedding websites with travel, RSVPs, schedule and registry.",
  intro=["Summit is drawn for a wedding with a view: alpine and granite looks, pine-line illustration and type that stays readable against a big landscape photo. Frost carries the same feeling into a winter lodge wedding, and Ranch covers the high-desert and cabin end of things.",
         "Mountain weddings mean altitude, weather and winding roads, so the FAQ and travel sections earn their keep."],
  points=["Alpine and granite color looks", "Room for altitude, weather and footwear notes in the FAQ", "One-tap directions to a venue that maps do not always find"],
  faq=[("Which template suits a lodge or cabin wedding?", "Summit for a summer or fall mountain wedding, Frost for a snowy lodge, and Ranch if the venue is more cabin and big sky than peaks."),
       ("Can we warn guests about altitude and weather?", "Yes. Every design has a FAQ section, and the dress-code line and travel notes are where guests look first."),
       ("Is there a countdown?", "Yes. The site counts down to your day, then flips the morning after to count the days married.")]),
 "rustic": dict(name="Rustic & barn", h1="Rustic and barn wedding website templates", tags=["rustic", "barn", "western"],
  sub="Boots, barns, big sky and candlelight. Free rustic wedding websites with RSVPs, schedule and registry.",
  intro=["Rustic covers a lot of ground: a barn strung with lights, a ranch with big sky, a vineyard with long tables. Ranch is the western one, boots and barns and denim; Verona is harvest and candlelight; Summit is pines and a view.",
         "All three keep the type warm and the sections simple, and all three hold RSVPs, schedule, travel and registry."],
  points=["Saddle, denim, harvest and alpine color looks", "Parking and 'it is a working farm' notes where guests will see them", "Song requests on the RSVP for a barn dance worth the name"],
  faq=[("Which template is best for a barn wedding?", "Ranch if the wedding is western or on a ranch; Verona if it is a barn dressed with candles and long tables; Summit if the barn has mountains behind it."),
       ("Can guests request songs when they RSVP?", "Yes. The RSVP has a song-request line, and every request lands in your Lazo planner with the reply."),
       ("Can we add parking and shuttle details?", "Yes. The travel section covers parking, transport and notes for guests coming from out of town.")]),
 "vineyard": dict(themes=["verona","sage"], name="Vineyard", h1="Vineyard and winery wedding website templates", tags=["vineyard"],
  sub="Harvest color, long tables and candlelight. Free winery wedding websites with RSVPs, schedule and registry.",
  intro=["Verona is the vineyard design: harvest and Tuscan-gold looks, a menu-card feel to the schedule, and candlelit photography. It suits a winery wedding in any season and a late-summer or fall garden party just as well.",
         "Add your names, the estate, the schedule from ceremony to last pour, and where guests can stay nearby."],
  points=["Harvest burgundy and Tuscan-gold color looks", "Schedule laid out like a menu card", "Nearby picks for tasting rooms and restaurants around the venue"],
  faq=[("Does Verona work for a fall wedding that is not at a winery?", "Yes. The harvest palette and candlelight suit any fall wedding, from a barn to a restaurant buyout."),
       ("Can we list wineries and restaurants for guests?", "Yes. The nearby section shows eat, drink and things-to-do picks around the venue, with your own favourites first."),
       ("Can we link our registry?", "Yes. Link any registry and guests shop from your site without leaving it.")]),
 "fall": dict(themes=["verona","ranch","summit"], name="Fall & autumn", h1="Fall wedding website templates", tags=["fall"],
  sub="Harvest color, candlelight and evergreen. Free fall wedding websites with RSVPs, schedule and registry.",
  intro=["Fall weddings want warmth on the page: burgundy, gold, deep green. Verona brings harvest color and candlelight; Ranch adds saddle brown and big sky; Summit gives you pines and alpine light for a mountain fall.",
         "Preview each with your names above. Switching designs later keeps everything you have added."],
  points=["Burgundy, tuscan gold, saddle and alpine-green looks", "Sunset-time notes for an outdoor ceremony that ends in the dark", "Registry and RSVP built in"],
  faq=[("Which template is best for an October wedding?", "Verona for harvest color and candlelight, Summit for a mountain or lake fall wedding, Ranch for a barn or ranch."),
       ("Can we change the design after we publish?", "Yes. Switch designs or color looks anytime; your names, schedule and RSVPs carry over."),
       ("Is there a place for a rain plan?", "Yes. Use the FAQ section, and the dress-code line for layers and footwear.")]),
 "black-tie": dict(name="Black tie", h1="Black tie wedding website templates", tags=["black-tie"],
  sub="Editorial type, midnight gold and a monogram crest. Free formal wedding websites with RSVPs, schedule and registry.",
  intro=["A black-tie wedding website should look like the invitation: restrained, formal, expensive-looking. Noir is editorial black and gold with a champagne look; Fête is classic formal with a crest of your initials.",
         "Both set your names in serif display type, carry the dress code where guests will see it, and hold the schedule, RSVPs and registry."],
  points=["Midnight gold, champagne, navy and blush formal looks", "A dress-code line guests cannot miss", "Monogram crest built from your initials"],
  faq=[("Noir or Fête?", "Noir is darker and more editorial, with gold on black; Fête is lighter and more traditional, with a crest and navy or blush. Type your names above and see both."),
       ("Can we state the dress code clearly?", "Yes. The dress code sits on the day section in every design, with room for a note about what black tie means for your wedding."),
       ("Can guests RSVP for a formal dinner with meal choices?", "Yes. RSVPs collect meal choices, plus-ones and notes, and each one files itself in your planner.")]),
 "classic": dict(name="Classic & elegant", h1="Classic and elegant wedding website templates", tags=["classic", "elegant"],
  sub="Timeless serif type, a monogram and formal structure. Free elegant wedding websites with RSVPs, schedule and registry.",
  intro=["Classic never dates. Fête gives you a crest of your initials, formal serif type and navy-and-gold or blush looks; Noir takes the same restraint into black tie; Starlit and Frost add a little romance, with lantern light and winter candles.",
         "Every design keeps the sections guests expect, in the order they expect them."],
  points=["Monogram crest from your initials", "Navy, gold, blush, midnight and ice color looks", "Schedule, travel, RSVP and registry in the classic order"],
  faq=[("What makes a wedding website look elegant?", "Restraint: a serif display face, one or two colors, generous space and few sections. Every Lazo design is built that way, and Fête is the most traditional."),
       ("Can we use our initials as a monogram?", "Yes. Fête builds a crest from your initials automatically, and updates as you type your names."),
       ("Is the site free?", "Yes. Every design, with RSVPs, schedule, registry links and the passcode option, is free for couples.")]),
 "modern": dict(name="Modern", h1="Modern wedding website templates", tags=["modern"],
  sub="Big type, clean lines and lots of air. Free modern wedding websites with RSVPs, schedule and registry.",
  intro=["Modern here means confident and simple: Atelier sets your names in big type and gets out of the way; Dune is desert-modern with adobe arches and golden-hour color; Noir is the editorial one, gold on black.",
         "None of them need photos to look finished, which helps before the engagement shoot."],
  points=["Gallery, carbon, golden-hour and midnight looks", "Designs that look complete before you have photos", "Sections you can leave out without leaving a hole"],
  faq=[("Which template is the most minimal?", "Atelier. Big type, no illustration, black or white looks. Dune is modern with more color and shape."),
       ("Do we need photos for a modern design to look good?", "No. Atelier and Noir are typographic and look finished with no photos at all. Add a gallery whenever you have one."),
       ("Can we remove sections we do not need?", "Yes. Leave a section empty and it does not show.")]),
 "minimalist": dict(themes=["atelier","noir","dune"], name="Minimalist", h1="Minimalist wedding website templates", tags=["minimalist"],
  sub="Names, date, place. Big type and nothing extra. Free minimalist wedding websites with RSVPs and schedule.",
  intro=["Atelier is the minimalist design: your names in large type, the date and place, a schedule, an RSVP, and as little else as you want. Gallery and carbon looks, black on white or white on black.",
         "It suits a small wedding, a city-hall ceremony, an elopement with a dinner after, or any couple who wants the site to say less."],
  points=["Two looks: gallery (light) and carbon (dark)", "Reads perfectly with no photos", "RSVP, schedule and registry, nothing forced"],
  faq=[("Is Atelier good for a small wedding or elopement?", "Yes. It is built for exactly that: a few details, well set. Leave out what you do not need."),
       ("Can we still collect RSVPs on a minimalist site?", "Yes. RSVPs, meal choices and plus-ones work the same on every design."),
       ("Can we add photos later?", "Yes. Add a cover and a gallery whenever you have them; the design makes room.")]),
 "boho": dict(name="Boho", h1="Boho wedding website templates", tags=["boho"],
  sub="Desert light, dried florals, greenery and warm neutrals. Free boho wedding websites with RSVPs, schedule and registry.",
  intro=["Boho sits between desert and garden: terracotta and dusty rose, pampas and eucalyptus, golden hour. Dune covers the desert end with adobe arches; Sage covers the greenery end with hand-drawn botanicals.",
         "Both keep the type soft and the sections simple, and both hold RSVPs, schedule, travel and registry."],
  points=["Terracotta, dusty rose, eucalyptus and garden looks", "Illustration that suits dried florals and desert venues", "Song requests on the RSVP"],
  faq=[("Dune or Sage for a boho wedding?", "Dune if your palette is terracotta and sand, Sage if it is greenery and cream. Preview both with your names above."),
       ("Can we use our own photos?", "Yes. Add a cover photo and a gallery and they appear throughout the design."),
       ("Is it free?", "Yes. Every Lazo wedding website design is free for couples, with RSVPs and registry included.")]),
 "desert": dict(themes=["dune","ranch","atelier"], name="Desert", h1="Desert wedding website templates", tags=["desert"],
  sub="Adobe arches, golden hour and dusk color. Free desert wedding websites with travel, RSVPs, schedule and registry.",
  intro=["Dune is drawn for the desert: adobe arches, golden-hour and desert-dusk looks, and type that sits well over a big-sky photo. It suits Sedona, Joshua Tree, Palm Springs, Santa Fe and every ranch and vineyard in between.",
         "Desert weddings mean heat and distance, so the travel section and the FAQ do real work."],
  points=["Golden-hour and desert-dusk color looks", "Sunset-time and heat notes in the FAQ", "Travel and stays for guests flying in"],
  faq=[("Is Dune good for a Sedona or Joshua Tree wedding?", "Yes. It is built for red rock and big sky, and the golden-hour look matches the light."),
       ("Can we tell guests about heat, shade and water?", "Yes. Use the FAQ and dress-code line; guests read those first."),
       ("Can we add hotel blocks?", "Yes. The travel section holds hotel blocks, transport, parking and tips.")]),
 "celestial": dict(themes=["starlit","frost","noir"], name="Celestial", h1="Celestial and starry night wedding website templates", tags=["celestial"],
  sub="Lanterns, constellations and a sky full of stars. Free celestial wedding websites with RSVPs, schedule and registry.",
  intro=["Starlit is the night-sky design: midnight and nebula looks, lantern light, gold on deep blue, and type that reads like an evening invitation. It suits an evening wedding, a rooftop, a garden after dark, or a winter ceremony by candlelight.",
         "Frost carries the same evening feel into snow and evergreens."],
  points=["Midnight, nebula and gold color looks", "Built for an evening schedule", "Your song plays softly when guests open the site"],
  faq=[("Is Starlit dark on phones?", "It is a deep-blue design with high-contrast type, and it reads clearly on any phone. Preview it above."),
       ("Can our first-dance song play on the site?", "Yes. Pick your song on the Music page and it plays quietly when guests open your site, easy to pause."),
       ("Can we switch to a lighter look later?", "Yes. Switch designs or color looks anytime; everything you have added carries over.")]),
 "winter": dict(themes=["frost","starlit","summit"], name="Winter", h1="Winter wedding website templates", tags=["winter", "holiday"],
  sub="Snow, evergreens and candlelight. Free winter wedding websites with travel, RSVPs, schedule and registry.",
  intro=["Frost is the winter design: ice and evergreen looks, snow and candlelight, and space for the travel notes a winter wedding needs. Starlit adds lantern light for a December evening; Summit covers a snowy mountain lodge.",
         "Add the schedule, where to stay, and what to wear when it is cold, and your guests are set."],
  points=["Ice-blue and evergreen color looks", "Weather, roads and layers notes in the FAQ", "Travel and stays for guests coming in for the holidays"],
  faq=[("Which template suits a December or holiday wedding?", "Frost for snow and evergreens, Starlit for an evening by lantern light, Summit for a mountain lodge."),
       ("Can we warn guests about winter roads and weather?", "Yes. The FAQ and travel sections are made for it."),
       ("Does the site keep going after the wedding?", "Yes. The morning after, it flips to days married, with chapters, photos and a guestbook.")]),
 "small-wedding": dict(themes=["atelier","dune","tide","sage"], name="Small wedding & elopement", h1="Wedding website templates for small weddings and elopements", tags=["small-wedding", "elopement"],
  sub="A few details, beautifully set. Free wedding websites for intimate weddings, elopements and dinners after.",
  intro=["A small wedding still needs a link: the date, the place, the dinner after, where to stay, and a way for the thirty people who matter to reply. Atelier says all of it in big type and nothing else; Dune and Tide do the same with more warmth.",
         "And for an elopement, the site is where everyone else finds out: publish after, with photos, a story and a guestbook."],
  points=["Designs that look finished with three details and no photos", "RSVPs for a dinner, a party or a weekend", "Married mode: publish after the elopement with photos and a guestbook"],
  faq=[("Can we publish the site after we elope?", "Yes. Publish whenever you like, and the site starts in married mode with your photos, your story and a guestbook for everyone to sign."),
       ("Do we need to fill in every section?", "No. Leave a section empty and it does not show."),
       ("Can we collect RSVPs for just a dinner?", "Yes. Add the dinner as the only event and guests RSVP to that.")]),
 "romantic": dict(name="Romantic", h1="Romantic wedding website templates", tags=["romantic"],
  sub="Florals, candlelight and starlight. Free romantic wedding websites with RSVPs, schedule and registry.",
  intro=["Romantic means soft: full blooms, candlelight, a night sky, snow. Flora is roses and peonies; Starlit is lanterns and stars; Verona is candlelit harvest; Frost is winter by candlelight.",
         "Each sets your names in serif display type and gives your story and photos room."],
  points=["Rose, peony, midnight, harvest and ice looks", "A story section that reads like a letter", "Your song, playing softly when guests arrive"],
  faq=[("Which template is the most romantic?", "Flora if you love florals, Starlit if you love an evening sky. Both are soft, serif and photo-friendly."),
       ("Can we write our story on the site?", "Yes. Every design has a story section, and married mode adds chapters for what comes after."),
       ("Can we add our song?", "Yes. Pick it on the Music page and it plays quietly when guests open the site.")]),

 "watercolor": dict(themes=["aquarelle","flora","sage"], name="Watercolor", h1="Watercolor wedding website templates", tags=["watercolor"],
  sub="Soft washes of blush, sky and lilac. Free watercolor wedding websites with RSVPs, schedule and registry.",
  intro=["Aquarelle is the watercolor design: washes of color that drift behind your names, a serif that reads like an invitation, and four looks from blush to sage. Flora and Sage carry the same softness with florals and greenery instead of paint.",
         "It suits a garden or greenhouse wedding, a spring or summer date, and any couple whose invitations were painted rather than printed."],
  points=["Blush, sky, lilac and sage color looks", "Washes that move gently, and stop for guests who prefer reduced motion", "Looks finished with no photos at all"],
  faq=[("Can we match the site to our watercolor invitations?", "Yes. Pick the look closest to the invitation's palette; the wash and the type follow it across every section."),
       ("Is Aquarelle free?", "Yes. Every Lazo wedding website design is free for couples, with RSVPs, schedule and registry included."),
       ("Does the watercolor effect work on phones?", "Yes. It is drawn by the browser, not an image, so it loads instantly and looks sharp on any screen.")]),
 "geometric": dict(themes=["prism","atelier","noir"], name="Geometric", h1="Geometric and art deco wedding website templates", tags=["geometric","art-deco"],
  sub="Clean lines, terrazzo color and confident type. Free geometric wedding websites with RSVPs, schedule and registry.",
  intro=["Prism is the geometric design: circles, lines and terrazzo color behind uppercase names, built for a loft, a gallery, a foundry or a rooftop. Gilded takes the same discipline into art deco with gold fans on onyx; Atelier strips it to type alone.",
         "All three look complete before you have a single photo, which helps in the months before the engagement shoot."],
  points=["Terrazzo, ink, coral and mint color looks", "Designs that need no photos to look finished", "Sections you can leave out without leaving a hole"],
  faq=[("Which template is best for a city or loft wedding?", "Prism for a modern space with big windows, Gilded for a ballroom or a hotel with history, Atelier for a restaurant or a registry office."),
       ("Can we use a dark look?", "Yes. Prism has an ink look, Gilded is dark by default with onyx, emerald and burgundy, and Atelier has a carbon look."),
       ("Do the shapes move?", "Gently, and never for guests who have asked their phone for reduced motion.")]),
 "vintage": dict(themes=["gilded","fete","verona"], name="Vintage & art deco", h1="Vintage and art deco wedding website templates", tags=["vintage","art-deco"],
  sub="Gold fans, onyx, emerald and a big band. Free vintage wedding websites with RSVPs, schedule and registry.",
  intro=["Gilded is the art deco design: gold fans and sunbursts on onyx, emerald or burgundy, uppercase names with a Cormorant ampersand, and an ivory look for daytime. It was drawn for a ballroom, a hotel with a history, a jazz band and black tie.",
         "Fête carries the vintage feeling into classic formal with a crest; Verona into candlelight and long tables."],
  points=["Onyx, emerald, ivory and burgundy looks", "Deco rules and fans drawn by the browser, sharp on any screen", "A dress-code line guests cannot miss"],
  faq=[("Is Gilded too dark for daytime?", "Switch to the ivory look for a daytime wedding and the same fans and type sit on cream and gold."),
       ("Can guests request a song for the band?", "Yes. The RSVP has a song-request line, and every request lands in your Lazo planner with the reply."),
       ("Does it work for a 1920s theme?", "That is exactly what it is drawn for. Add a line about the dress code and let the design do the rest.")]),
 "south-asian": dict(themes=["marigold","gilded","flora"], name="South Asian", h1="Indian and South Asian wedding website templates", tags=["south-asian","indian","multi-day"],
  sub="Marigold garlands, a multi-day schedule, RSVPs per event and registry. Free Indian wedding websites, live in minutes.",
  intro=["Marigold is drawn for a South Asian wedding: garlands across the top, marigold, magenta, royal blue and emerald looks, and a schedule built for several days. Mehndi on Thursday, sangeet on Friday, the baraat and the pheras on Saturday, the reception that night, each with its own time, place and note.",
         "The RSVP asks which events a guest is coming to and about dietary needs, veg, Jain or halal, so both families get counts they can hand to the caterers. The FAQ has room to explain the baraat to guests who have never joined one."],
  points=["Marigold, magenta, royal-blue and emerald color looks", "A schedule that runs across days, with who is invited to what", "RSVP notes for dietary needs and which events guests will attend"],
  faq=[("Does the schedule handle mehndi, sangeet, baraat and reception?", "Yes. Add as many events as you like across as many days as you need, each with a time, a venue and a note."),
       ("Can guests tell us which events they are attending?", "Yes. The RSVP has a note line for exactly that, and every reply lands in your Lazo planner."),
       ("Can we write in more than one language?", "Yes. Every line on the site is yours to write, in any language or in two.")]),
 "latin": dict(themes=["papel","dune","verona"], name="Latin", h1="Latin and Mexican wedding website templates", tags=["latin","mexican","fiesta"],
  sub="Papel picado, mariachi, the lazo and the padrinos. Free Latin wedding websites with RSVPs, schedule and registry.",
  intro=["Papel is drawn for a Latin wedding: papel picado banners fluttering across the top, fiesta red, cobalt, terracotta and jade looks, and a schedule with room for the lazo and the arras at the ceremony, the mariachi at cocktails and la hora loca after dinner.",
         "Lazo is named for the lazo, the ribbon or rosary the padrinos place around the couple at the vows. Dune and Verona carry the same warmth into a hacienda or a vineyard."],
  points=["Fiesta, cobalt, terracotta and jade color looks", "Room in the ceremony section for the lazo, the arras and the padrinos", "A song-request line for the mariachi"],
  faq=[("Can we explain the lazo and the padrinos to guests?", "Yes. The FAQ section is made for it, and the ceremony card has a note line for who does what."),
       ("Can we write the site in Spanish, or both languages?", "Yes. Every line on the site is yours to write, in either language or both."),
       ("Can guests request songs for the mariachi?", "Yes. The RSVP has a song-request line, and every request lands in your Lazo planner with the reply.")]),
 # intent pages
 "with-rsvp": dict(name="With RSVP", h1="Wedding website templates with online RSVP", tags=[], themes=list(THEMES),
  sub="Guests reply on the site; every reply lands in your planner with meals, plus-ones and notes. Free, on every design.",
  intro=["Every Lazo wedding website has online RSVP built in, on every design. Guests open your link, tap RSVP, and reply with attendance, meal choices, plus-ones, song requests and a note. No account, no app.",
         "Each reply files itself in your Lazo planner the moment it arrives, so the headcount is always current and the caterer's number is never a project. Set an RSVP-by date and it shows on the site."],
  points=["Attendance, meals, plus-ones, song requests and notes", "Replies land in your planner as they happen", "RSVP-by date shown on the site; RSVP closes when you say"],
  faq=[("Do guests need an account to RSVP?", "No. Guests reply on the site itself; nothing to download or sign up for."),
       ("Can we collect meal choices and dietary notes?", "Yes. Meals, plus-ones and a free-text note are on every RSVP."),
       ("Can we close RSVPs after the deadline?", "Yes. Turn RSVP off from your planner and the site shows a thank-you in its place.")]),
 "with-registry": dict(name="With registry", h1="Wedding website templates with a registry link", tags=[], themes=list(THEMES),
  sub="Link any registry and guests shop from your site without leaving it. Free, on every design.",
  intro=["A wedding website with a registry link saves you the awkward line on the invitation. Add one registry or several, from any store or a cash fund, and they appear in the registry section of every Lazo design with a note in your words.",
         "Guests tap through from your site, and the same link sends them back to the schedule, travel and RSVP."],
  points=["Any registry, any store, cash funds included", "A registry note in your own words", "One link that holds registry, RSVP and everything else"],
  faq=[("Which registries can we link?", "Any. Add the link and a name and it shows in the registry section."),
       ("Can we ask for no gifts, or for a honeymoon fund?", "Yes. Write the note the way you want it; the registry section shows it above the links."),
       ("Is the registry section free?", "Yes. Every part of a Lazo wedding website is free for couples.")]),
 "password-protected": dict(name="Password protected", h1="Password protected wedding website templates", tags=[], themes=list(THEMES),
  sub="Add a passcode and only invited guests can open your site. Free, on every design, and kept out of search engines.",
  intro=["Some weddings want a closed door. Add a passcode to any Lazo wedding website and guests need it to open the site; put it on the invitation and nowhere else. Passcode sites are also marked so search engines do not index them.",
         "Everything else works the same: RSVPs, schedule, travel, registry, photos and your song."],
  points=["One passcode for the whole site, changeable anytime", "Automatically kept out of Google and other search engines", "Share previews show your names and nothing else"],
  faq=[("How do guests get the passcode?", "Put it on the invitation or in the message you send with the link. You can change it at any time."),
       ("Will a passcode site show up in Google?", "No. Passcode sites carry a no-index instruction and stay out of search results."),
       ("Can we remove the passcode later?", "Yes. Clear it in your planner and the site opens for everyone with the link.")]),
}

ORDER = list(THEMES)


def themes_for(spec):
    got = list(spec.get("themes", []))
    for tag in spec.get("tags", []):
        for slug in ORDER:
            if tag in THEMES[slug]["styles"] and slug not in got:
                got.append(slug)
    return got


CARD_RX = re.compile(r' <div class="tpl rv" data-t="(\w+)"[^>]*>.*?<div class="btns">.*?</div>\n </div>\n', re.S)
CARDS = {m.group(1): m.group(0) for m in CARD_RX.finditer(HUB)}
assert len(CARDS) == len(THEMES), f"found {len(CARDS)} cards in hub, expected {len(THEMES)}"


def relink(card):
    card = re.sub(r'href="(\w+)/', r'href="../\1/', card)
    card = re.sub(r'src="(\w+)/\?frame=1"', r'src="../\1/?frame=1"', card)
    return card


def ld_json(slug, spec, url, title, desc, tlist):
    e = lambda x: x
    return json.dumps({"@context": "https://schema.org", "@graph": [
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Lazo", "item": "https://meetlazo.com/"},
            {"@type": "ListItem", "position": 2, "name": "Wedding websites", "item": HUB_URL},
            {"@type": "ListItem", "position": 3, "name": spec["name"], "item": url}]},
        {"@type": "CollectionPage", "@id": url, "url": url, "name": title, "description": desc,
         "isPartOf": {"@type": "WebSite", "name": "Lazo", "url": "https://meetlazo.com/"}},
        {"@type": "ItemList", "name": spec["h1"], "numberOfItems": len(tlist), "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": f"{THEMES[t]['name']} wedding website template", "url": f"{HUB_URL}{t}/"}
            for i, t in enumerate(tlist)]},
        {"@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in spec["faq"]]},
    ]}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def build(slug):
    spec = STYLES[slug]
    tlist = themes_for(spec)
    assert tlist, f"{slug}: no templates"
    url = f"{HUB_URL}{slug}/"
    h1 = spec["h1"]
    if h1.split()[0] not in ("Indian", "Latin", "Mexican", "South"):
        h1 = h1[0].lower() + h1[1:]
    title = f"Free {h1} | Lazo"
    if slug in ("with-rsvp", "with-registry", "password-protected"):
        title = f"{spec['h1']} (Free) | Lazo"
    desc = spec["sub"]
    E = html.escape
    s = HUB
    # head
    s = re.sub(r"<!-- lz-seo -->.*?<!-- /lz-seo -->\n", "", s, flags=re.S)
    s = re.sub(r"<title>[^<]*</title>", "<title>" + E(title) + "</title>", s, count=1)
    s = re.sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="' + E(desc, quote=True) + '">', s, count=1)
    head = ("<!-- lz-seo -->\n"
            f'<link rel="canonical" href="{url}">\n'
            '<meta property="og:type" content="website">\n<meta property="og:site_name" content="Lazo">\n'
            f'<meta property="og:url" content="{url}">\n<meta property="og:title" content="{E(title)}">\n'
            f'<meta property="og:description" content="{E(desc)}">\n<meta property="og:image" content="https://meetlazo.com/assets/brand.png">\n'
            '<meta name="twitter:card" content="summary_large_image">\n'
            '<script type="application/ld+json">' + ld_json(slug, spec, url, title, desc, tlist) + "</script>\n"
            "<!-- /lz-seo -->\n")
    s = s.replace('<meta name="theme-color" content="#52284F">\n', '<meta name="theme-color" content="#52284F">\n' + head, 1)
    # hero copy
    s = s.replace('<p class="eyebrow">Free wedding website builder</p>',
                  '<p class="eyebrow"><a href="../" style="text-decoration:none">Wedding websites</a> · ' + E(spec["name"]) + '</p>', 1)
    s = re.sub(r"<h1>.*?</h1>", "<h1>" + E(spec["h1"]) + "</h1>", s, count=1, flags=re.S)
    s = re.sub(r'<p class="sub">.*?</p>', '<p class="sub">' + E(spec["sub"]) + "</p>", s, count=1, flags=re.S)
    n = len(tlist)
    word = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight"}.get(n, str(n))
    live = {1: "Live on the preview below", 2: "Live on both previews below"}.get(n, f"Live on all {word} previews below")
    s = re.sub(r"Live on all [\w-]+ previews below", live, s, count=1)
    # grid
    a = s.index('<main class="grid" id="grid">\n') + len('<main class="grid" id="grid">\n')
    b = s.index("</main>", a)
    s = s[:a] + "".join(relink(CARDS[t]) for t in tlist) + s[b:]
    # relative links inside JS
    s = s.replace('card.querySelector("[data-f]").src=id+"/?"+fp.toString();', 'card.querySelector("[data-f]").src="../"+id+"/?"+fp.toString();', 1)
    s = s.replace('card.querySelector("[data-view]").href=id+"/"+(qs?"?"+qs:"");', 'card.querySelector("[data-view]").href="../"+id+"/"+(qs?"?"+qs:"");', 1)
    s = s.replace('view.href=slug+"/?palette="+k;', 'view.href="../"+slug+"/?palette="+k;', 1)
    s = s.replace('href="noir/?married=1"', 'href="../noir/?married=1"', 1)
    # hub-only sections out, style sections in
    s = re.sub(r"<!-- lz-seo-sections -->.*?<!-- /lz-seo-sections -->\n\n?", "", s, flags=re.S)
    # the style pages are one style already: no filter row, no married switch
    s = re.sub(r"<!-- lz-filters -->.*?<!-- /lz-filters -->\n", "", s, flags=re.S)
    s = re.sub(r"<!-- lz-sell -->.*?<!-- /lz-sell -->\n?", "", s, flags=re.S)  # JC-LAZO-HUB-0930-FIX
    s = re.sub(r"<!-- lz-sell -->.*?<!-- /lz-sell -->\n?", "", s, flags=re.S)  # JC-LAZO-HUB-0930-FIX
    s = re.sub(r"\s*<!-- lz-married -->.*?<!-- /lz-married -->", "", s, flags=re.S)
    s = re.sub(r"\n<script>\n/\* lz-filters-js \*/.*?/\* /lz-filters-js \*/\n</script>", "", s, flags=re.S)
    s = re.sub(r'<section class="beyond rv">.*?</section>\n', "", s, count=1, flags=re.S)
    sib = [(k, v["name"]) for k, v in STYLES.items() if k != slug]
    body = ["<!-- lz-style-sections -->",
            '<section class="sec rv" id="about">', f' <p class="sk">{E(spec["name"])} wedding websites</p>',
            f' <h2>{E(spec["h1"])}, free on Lazo</h2>']
    body += [f' <p class="sp" style="margin-bottom:14px">{E(p)}</p>' for p in spec["intro"]]
    body += [' <div class="incg" style="grid-template-columns:1fr;max-width:720px;margin-left:auto;margin-right:auto">']
    body += [f'  <div><b>{E(p)}</b></div>' for p in spec["points"]]
    body += [' </div>', '</section>',
             '<section class="sec faqs rv" id="faq">', ' <p class="sk">Questions</p>', f' <h2>{E(spec["name"])} wedding website FAQ</h2>']
    body += [f' <details><summary>{E(q)}</summary><p>{E(a)}</p></details>' for q, a in spec["faq"]]
    body += ['</section>',
             '<section class="sec rv" id="styles">', ' <p class="sk">More styles</p>', ' <h2>Wedding website templates for every kind of wedding</h2>',
             ' <div class="chips">', '  <a href="../">All templates</a>']
    body += [f'  <a href="../{k}/">{E(nm)}</a>' for k, nm in sib]
    body += [' </div>', '</section>', '<!-- /lz-style-sections -->', '']
    s = s.replace('<section class="close">', "\n".join(body) + '<section class="close">', 1)
    out = ROOT / slug / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(s, encoding="utf-8", newline="\n")
    print(f"  {slug}: {n} templates, {len(s):,} bytes")


if __name__ == "__main__":
    for slug in (sys.argv[1:] or list(STYLES)):
        build(slug)
