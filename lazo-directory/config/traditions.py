"""Wedding tradition pages.  JC-LAZO-TRAD-0916-001

/traditions/<slug>/, with the hub at /traditions/. The second content cluster,
and the one that is actually ours: we are named after a wedding tradition, and
the big platforms cover this material thinly or not at all - a paragraph inside
a listicle, usually written by someone who has never seen the ceremony.

Why this cluster and not more cost pages: these are genuinely distinct topics
with their own search intent, so every page earns its URL. There is no data axis
here to multiply against, which is the point - nothing in this directory can be
turned into 58 near-identical copies.

/what-is-a-lazo/ stays where it is. It has been indexed for months and carries
whatever authority it has earned at that URL; moving it under /traditions/ to be
tidy would throw that away. It is cross-linked as a member of the cluster.

Editorial rules for this file:
  - Describe the ceremony as it is actually performed, not as Pinterest crops it.
  - Name the people. "The padrinos place the cord" beats "the cord is placed".
  - Never flatten a living tradition into a decor idea. Couples of that heritage
    are the harshest and most valuable readers these pages have.
  - Where practice varies by country or family, say so rather than picking one.
  - `planning` is what makes these marketplace pages rather than blog posts: the
    concrete thing a couple must tell a vendor for the tradition to go well.

Schema per tradition:
  question  the h1 and title - phrased as the search
  short     display name for cards and cross-links
  group     the hub's section heading - a small, fixed set, unlike `culture`
  culture   the descriptive label shown on the page itself
  also      other names readers may search for; rendered as "also called"
  lede      the direct answer, first paragraph
  sections  [(h2, [paragraph, ...])]
  planning  [(what to do, why)] - the vendor-facing half
  faqs      [(q, a)] rendered as FAQPage schema
  related   slugs of sibling traditions; "what-is-a-lazo" is allowed and special-cased
  cats      taxonomy slugs this tradition most concerns, for the vendor rail
"""

TRADITIONS = {
    # ---------------------------------------------- Latin American & Spanish
    "las-arras": {
        "group": 'Latin American & Spanish',
        "question": "What are las arras in a wedding?",
        "short": "Las arras",
        "culture": "Mexican, Spanish & Latin American",
        "also": "arras matrimoniales, the thirteen coins, las arras de oro",
        "cats": ["wedding-officiants", "wedding-photographers"],
        "related": ["what-is-a-lazo", "padrinos-and-madrinas", "la-vibora-de-la-mar"],
        "lede": "Las arras are thirteen coins the groom gives the bride during a Mexican, Spanish or Latin American wedding ceremony, usually just after the vows. He pours them from his hands into hers, and often she pours them back, and the exchange is a promise about how the two of them will handle everything they own from that day on.",
        "sections": [
            ("What the thirteen coins mean", [
                "The most common reading is that the thirteen coins stand for Christ and the twelve apostles, which is where the number comes from in the Catholic tradition the ceremony grew out of. Another reading, just as widely held, is that they represent the twelve months of the year plus one to give away - a reminder that a household should always have something left over for someone who has less.",
                "What the coins are not is a payment. The older interpretation, in which a groom demonstrated he could provide, has largely given way to a mutual one: the coins pass both ways, because both people are responsible for what they build. Many couples now make the return pour explicit for exactly that reason.",
            ]),
            ("How the exchange happens", [
                "The arras are usually carried in a small chest or box, often by a child in the wedding party, and blessed by the officiant before the exchange. The groom takes the box, pours the coins into the bride's cupped hands, and in most modern ceremonies she pours them back into his. Some officiants say a line over each handful; others let the gesture carry it.",
                "It takes perhaps a minute, and it happens close in - two pairs of hands and a lot of small falling coins. That physical detail matters more than it sounds like it should, because it is the part that photographs well and the part that goes wrong if nobody planned for it.",
            ]),
            ("Whose arras they are", [
                "The set is frequently a gift from the padrinos de arras, a couple chosen for the honour, and it is common for the coins to be kept afterwards and passed to the next couple in the family. Sets that have been through three or four marriages are ordinary rather than remarkable.",
                "If you are buying new, arras sets are sold as a coin set with a box, and range from simple to elaborate. Some couples use family coins, coins from countries that matter to them, or coins minted in the year they met.",
            ]),
        ],
        "planning": [
            ("Tell your officiant early", "Las arras has to be written into the order of service, and it sits in a specific place - after the rings, usually before or alongside the lazo. An officiant who has not done one before needs the script."),
            ("Tell your photographer it is coming", "It is a close, downward, hands-and-coins moment lasting under a minute. A photographer who knows it is next will be in position; one who does not will be shooting it from the back of the aisle."),
            ("Decide who holds the box", "Someone has to carry the arras up and hand it over at the right moment. This is usually a child, and children need a rehearsal more than adults do."),
            ("Count them before the day", "Thirteen. Coins go missing in transit, and nobody wants to discover that during the ceremony."),
        ],
        "faqs": [
            ("What do the 13 coins in a wedding mean?",
             "Las arras, the thirteen coins, are most often said to represent Christ and the twelve apostles. A second common interpretation is the twelve months of the year plus one to give to those in need. In both readings the exchange is a promise about how the couple will handle their resources together."),
            ("Who gives las arras?",
             "The groom gives them to the bride during the ceremony, and in most modern versions she pours them back to him to mark that the responsibility is shared. The coin set itself is frequently a gift from the padrinos de arras, a couple chosen for that honour."),
            ("When in the ceremony does the arras exchange happen?",
             "Usually after the vows and rings, often just before or alongside the lazo ceremony and the veil. Your officiant places it in the order of service, so tell them early if you want it included."),
        ],
    },
    "padrinos-and-madrinas": {
        "group": 'Latin American & Spanish',
        "question": "What do padrinos and madrinas do at a wedding?",
        "short": "Padrinos & madrinas",
        "culture": "Mexican, Spanish & Latin American",
        "also": "wedding godparents, padrinos de boda, sponsors",
        "cats": ["wedding-officiants", "wedding-planners"],
        "related": ["what-is-a-lazo", "las-arras", "filipino-wedding-traditions"],
        "lede": "Padrinos and madrinas are the wedding godparents in Mexican, Latin American and Filipino weddings: married couples the bride and groom choose to sponsor a specific part of the ceremony and, more importantly, to stand behind the marriage for the rest of their lives. Being asked is a genuine honour and carries a genuine obligation.",
        "sections": [
            ("What they actually do", [
                "Each pair of padrinos is attached to something. The padrinos de lazo place the cord. The padrinos de arras present the coins. There may be padrinos of the veil, the rings, the Bible and rosary, the cake, the bouquet, the first dance - the list varies by family and by country, and a large wedding can have a dozen pairs.",
                "The traditional expectation is that a padrino also sponsors the thing they are named for, financially. That convention is softening in many families and holding firm in others, which is precisely why it is worth being explicit when you ask.",
            ]),
            ("What it means beyond the day", [
                "The ceremonial role is the visible part. The real role is longer: padrinos are the couple you are supposed to call when the marriage is hard. In the older understanding they are witnesses to a promise and are expected to hold you to it.",
                "This is why padrinos are usually a married couple whose marriage the bride and groom admire, and why people often choose grandparents, aunts and uncles, or the friends who have been married longest. You are not choosing helpers. You are choosing an example.",
            ]),
            ("How to ask", [
                "Ask in person, well ahead, and say plainly which role you have in mind and what it involves - including whether you are asking them to sponsor the cost. Ambiguity here is the single most common source of awkwardness, and it is entirely avoidable.",
                "It is normal to have padrinos who are not part of the bridal party, and normal for padrinos to be considerably older than the couple. They are a different institution from bridesmaids and groomsmen and are not a substitute for them.",
            ]),
        ],
        "planning": [
            ("Give your officiant the list", "Every padrino pair that participates needs a cue in the order of service and, at many weddings, a name read aloud. Your officiant cannot improvise this."),
            ("Tell your coordinator who moves when", "Padrinos step forward mid-ceremony and return to their seats. Without a rehearsal that is a dozen people guessing."),
            ("Reserve their seats", "Padrinos need to be near the front and on an aisle, because they have to get up. This is a seating-chart decision, not a day-of one."),
            ("Be clear about sponsorship when you ask", "If you are asking someone to fund what they present, say so in the same conversation. Discovering the expectation later is how this tradition creates resentment instead of bonds."),
        ],
        "faqs": [
            ("What is the difference between padrinos and the wedding party?",
             "Bridesmaids and groomsmen are your friends standing with you on the day. Padrinos and madrinas are sponsors of specific ceremonial elements and, traditionally, lifelong guarantors of the marriage itself - usually married couples chosen as examples. Many weddings have both."),
            ("Do padrinos have to pay for what they sponsor?",
             "Traditionally yes, and in many families still. The convention is softening, so the only safe approach is to say clearly what you are asking for when you ask, rather than assuming either way."),
            ("How many padrinos can you have?",
             "There is no fixed number. Small weddings may have one or two pairs; large ones can have a dozen, each attached to a different element such as the lazo, las arras, the veil, the rings, the Bible or the cake."),
        ],
    },
    "the-veil-ceremony": {
        "group": 'Filipino',
        "question": "What is the veil ceremony in a wedding?",
        "short": "The veil ceremony",
        "culture": "Mexican, Spanish & Filipino",
        "also": "el velo, the veil and cord, veiling ceremony",
        "cats": ["wedding-officiants", "wedding-photographers"],
        "related": ["what-is-a-lazo", "filipino-wedding-traditions", "las-arras"],
        "lede": "In the veil ceremony, padrinos drape a length of white fabric over the bride's head and pin it to the groom's shoulder, covering the couple together during part of the ceremony. It is one of the three ceremonial gifts in Mexican and Filipino Catholic weddings, alongside the lazo and las arras, and it is about protection: what covers one of you now covers both.",
        "sections": [
            ("What the veil signifies", [
                "The usual reading is shelter. Placed over the bride's head and attached to the groom, the veil makes a single covered space out of two people, and the marriage is understood as the thing that shelters them from then on. In Filipino weddings it is often explained as the couple being clothed as one.",
                "It is frequently paired directly with the cord: veil first, then lazo over the top, so the couple is both covered and bound. Where all three gifts are used, the order is generally veil, then cord, then coins, though families vary.",
            ]),
            ("How it is done", [
                "The padrinos de velo step forward after the vows. One arranges the veil over the bride's head or shoulders, the other pins the far end to the groom's shoulder or lapel. The couple stays veiled through the prayers that follow, and it is removed near the end of the ceremony.",
                "In many Filipino weddings the bride's own long veil is used rather than a separate cloth, which means the moment is partly a matter of unpinning, arranging and re-pinning something already on her head. It takes longer than couples expect.",
            ]),
        ],
        "planning": [
            ("Pin it, do not balance it", "The veil has to survive kneeling, standing and prayers. Whoever pins it needs a real pin and a moment to do it properly - build that time into the order of service."),
            ("Warn your hair stylist", "A veil that gets lifted, draped and removed mid-ceremony interacts with the hairstyle underneath it. Your stylist should know at the trial, not on the morning."),
            ("Tell your videographer about the audio", "The couple is under fabric for several minutes of prayer. Lapel mics matter more here than at most ceremonies."),
        ],
        "faqs": [
            ("What does the veil ceremony symbolise?",
             "Protection and unity - the veil covers the bride and is pinned to the groom so that one covering shelters them both. In Filipino weddings it is often described as the couple being clothed as one."),
            ("Do you need the lazo and the veil, or just one?",
             "Either. Many Mexican and Filipino ceremonies use all three gifts - veil, cord and coins - but plenty of couples choose one or two. There is no requirement to include all of them."),
            ("Who places the veil?",
             "The padrinos de velo, a couple chosen for that role, place and pin it. It is a separate honour from the padrinos of the cord or the coins."),
        ],
    },
    "la-vibora-de-la-mar": {
        "group": 'Latin American & Spanish',
        "question": "What is La Víbora de la Mar?",
        "short": "La Víbora de la Mar",
        "culture": "Mexican & Latin American",
        "also": "the sea snake, the snake of the sea, la vibora",
        "cats": ["wedding-djs", "wedding-bands", "wedding-venues"],
        "related": ["la-hora-loca", "the-money-dance", "mariachi-at-weddings"],
        "lede": "La Víbora de la Mar is the wildest scheduled event at a Mexican wedding reception: the bride and groom stand on chairs holding hands overhead while guests form a chain and run underneath, faster and faster, until someone falls or the couple is nearly pulled off. It is a children's song turned into a reception ritual, and it is usually the moment the night stops being formal.",
        "sections": [
            ("How it works", [
                "The couple climbs onto two chairs and joins hands to make an arch. Guests link hands in a long chain and run beneath it in time to the song, which speeds up. Traditionally the women go first, then the men, who are generally rougher about it. The bride often throws her bouquet or her veil into the scrum.",
                "The chain gets faster and less careful as it goes, and the point, more or less, is chaos. Someone will trip. The couple is genuinely being shaken about on top of two chairs by people who love them.",
            ]),
            ("Where it comes from, and the safety part", [
                "The song is an old children's playground rhyme, and the wedding version has been standard at Mexican receptions for generations. Interpretations vary - a test of whether the couple can stay standing together is the most commonly offered one - but mostly it is a release valve after a long formal day.",
                "It is also the single most likely moment for an injury at a Mexican wedding. Chairs slip, dresses catch, guests are several drinks in. Couples increasingly do it holding a long ribbon or cloth between them rather than joined hands, or stand on something more stable than banquet chairs.",
            ]),
        ],
        "planning": [
            ("Tell your DJ or band well before the day", "They need the track and they need to know how long to stretch it. A DJ who has never run this will not know to speed it up."),
            ("Clear the floor and check the chairs", "You need real space and chairs that do not slide. Walk this with your coordinator and your venue - some venues will not allow standing on their furniture at all."),
            ("Warn your photographer to go wide and fast", "It is dark, it is moving and it is over in three minutes. This is a shutter-speed and lens decision they should make before it starts."),
            ("Think about footwear and the dress", "Many brides change shoes before this. Some change dresses."),
        ],
        "faqs": [
            ("What happens during La Víbora de la Mar?",
             "The couple stands on chairs holding hands to form an arch while guests link hands and run underneath to a song that gets progressively faster. Women typically go first, then men. It usually ends with someone falling over, which is broadly the intention."),
            ("Is La Víbora de la Mar dangerous?",
             "It can be - it is the most common source of minor injuries at Mexican receptions. Many couples now hold a ribbon between them instead of joining hands, use sturdy chairs rather than banquet chairs, and check that their venue permits it."),
            ("When in the reception does it happen?",
             "After dinner and the formal dances, once the night has loosened up. It often runs into or alongside La Hora Loca."),
        ],
    },
    "la-hora-loca": {
        "group": 'Latin American & Spanish',
        "question": "What is La Hora Loca?",
        "short": "La Hora Loca",
        "culture": "Latin American & Caribbean",
        "also": "the crazy hour, hora loca",
        "cats": ["wedding-djs", "wedding-bands", "wedding-rentals"],
        "related": ["la-vibora-de-la-mar", "mariachi-at-weddings", "the-money-dance"],
        "lede": "La Hora Loca is the hour, usually around midnight, when a Latin American reception deliberately detonates: the lights change, the music switches to carnival percussion, and guests are handed masks, feathered headpieces, LED glasses, glow sticks and inflatable instruments. Often stilt walkers, drummers or dancers arrive with them. It exists to reset a room that has been sitting down for three hours.",
        "sections": [
            ("What actually happens", [
                "At an agreed moment the DJ or band shifts abruptly - typically into Latin carnival, samba or soca percussion - while staff or hired performers move through the room distributing props. The change is meant to be sudden and slightly disorienting. Within a minute the dance floor that had thinned out is full again.",
                "The scale varies enormously. A minimal hora loca is a box of props and a playlist change. A full one is a booked troupe: stilt walkers, a drum line, costumed dancers, sometimes a saxophonist. Venezuelan and Colombian weddings are generally credited with popularising it, and it has spread widely well beyond those communities.",
            ]),
            ("Why it works", [
                "Receptions have a predictable sag. Dinner ends, the formal dances finish, older guests start leaving and the energy drops just as the night is supposed to get good. La Hora Loca is a deliberate intervention at exactly that point.",
                "It also gives guests who do not dance something to do. Handing a reserved uncle a pair of light-up glasses and a maraca is a more effective invitation to the floor than any song choice.",
            ]),
        ],
        "planning": [
            ("Agree the exact time with your DJ and coordinator", "It only works as a surprise and only if it lands at the sag, not before it. Pick a clock time and hold it."),
            ("Check the venue's rules first", "Stilt walkers need ceiling height. Confetti, foam and cold sparks are banned at many venues. Ask before you book performers."),
            ("Decide who hands out the props", "Someone has to distribute 150 items in ninety seconds. This is a job for staff or the troupe, not for your wedding party."),
            ("Tell your photographer the lighting is about to change", "The room goes dark and coloured with fast movement in it. Warn them so they are not changing settings through the best two minutes."),
        ],
        "faqs": [
            ("What is the crazy hour at a wedding?",
             "La Hora Loca, the crazy hour, is a deliberate mid-reception shift into carnival music with masks, props, glow items and often stilt walkers or a drum line. It typically happens around midnight to re-energise the dance floor."),
            ("How much does La Hora Loca cost?",
             "A props-and-playlist version can be a few hundred dollars in supplies. A booked troupe with performers, drummers and stilt walkers commonly runs $800 to $3,000 depending on the size of the act and your market."),
            ("When should La Hora Loca start?",
             "Usually after the formal dances and dinner, around 11pm or midnight, at the point where energy naturally dips. Agree a clock time with your DJ and coordinator in advance."),
        ],
    },
    "the-money-dance": {
        "group": 'Latin American & Spanish',
        "question": "What is the money dance at a wedding?",
        "short": "The money dance",
        "culture": "Latin American, Filipino & Polish",
        "also": "dollar dance, baile del billete, apron dance",
        "cats": ["wedding-djs", "wedding-bands"],
        "related": ["la-vibora-de-la-mar", "filipino-wedding-traditions", "la-hora-loca"],
        "lede": "In the money dance, guests pay a small amount for a moment on the dance floor with the bride or groom - pinning bills to their clothes, tucking notes into a purse, or handing them to an attendant. It appears in Latin American, Filipino, Polish, Greek and Nigerian weddings in different forms, and it is simultaneously a gift to the couple and a queue of people who each get thirty seconds alone with them.",
        "sections": [
            ("The different forms it takes", [
                "In many Latin American and Filipino weddings, guests pin bills directly to the couple's clothing, and by the end both are wearing a visible layer of money. In Polish weddings the bride's apron or a hat collects the notes. In Nigerian weddings guests shower or 'spray' bills over the dancing couple, which is a display of celebration more than a collection.",
                "The amount is not the point and is usually small. What varies is whether one partner or both dance, whether there is a queue master keeping it moving, and whether the money is collected by an attendant or attached to the couple.",
            ]),
            ("Why couples include it, and why some skip it", [
                "The strongest argument for it is not the money. It is that a wedding is the one event where a couple is surrounded by everyone they love and speaks properly to almost none of them. The money dance is a mechanism that puts every guest in front of them for a moment, by name.",
                "The argument against is that some guests read it as asking for cash, particularly in circles where the tradition is unfamiliar. Couples who want the contact without the transaction sometimes run it as a plain dance queue with no money at all.",
            ]),
        ],
        "planning": [
            ("Appoint someone to run the queue", "Without a person managing it, the money dance either stalls or runs forty minutes. A member of the wedding party with a loud voice is the usual answer."),
            ("Decide where the money goes", "Pinned to clothing, into an apron or purse, or handed to an attendant with a bag. Decide before the day and tell whoever is holding it."),
            ("Give your DJ a time limit", "Two or three songs. Your DJ should know to close it out rather than let it drift."),
            ("Tell guests it is coming", "A line on the wedding website removes the surprise for guests who have never seen it and lets them bring small bills."),
        ],
        "faqs": [
            ("How does the wedding money dance work?",
             "Guests pay a small amount for a brief dance with the bride or groom. Depending on the tradition the money is pinned to the couple's clothing, collected in an apron or purse, or handed to an attendant. It usually runs two or three songs."),
            ("Is the money dance rude?",
             "It is a long-standing tradition in Latin American, Filipino, Polish, Greek and Nigerian weddings and is not considered rude within them. Where guests are unfamiliar with it, a note on the wedding website explaining what it is removes any awkwardness."),
            ("How much do guests give at a money dance?",
             "Usually a small bill - the gesture matters more than the amount, and the dance is really a way for the couple to have a moment with every guest."),
        ],
    },
    "mariachi-at-weddings": {
        "group": 'Latin American & Spanish',
        "question": "How does mariachi work at a wedding?",
        "short": "Mariachi",
        "culture": "Mexican",
        "also": "mariachi band, serenata, wedding mariachi",
        "cats": ["wedding-bands", "wedding-djs", "wedding-venues"],
        "related": ["la-vibora-de-la-mar", "la-hora-loca", "what-is-a-lazo"],
        "lede": "A mariachi ensemble at a Mexican wedding is not background music. It is a set - violins, trumpets, guitarrón and vihuela, in full traje - performing for a defined stretch of the day, most often the ceremony, the cocktail hour, or the arrival of the couple at the reception. Most couples book mariachi for one or two hours and run a DJ or band for the rest of the night.",
        "sections": [
            ("Where in the day it fits", [
                "The three common placements are the ceremony itself, the hour immediately after it while guests move and mingle, and the couple's entrance at the reception. Some families also book a serenata the night before or the morning of - a smaller set performed for the bride at home, which is its own tradition and is often the more emotional of the two.",
                "Mariachi rarely plays the whole reception, partly because the repertoire is not built for four hours of dancing and partly because the cost of a full ensemble for that long is substantial. The standard arrangement is mariachi early, DJ or band later.",
            ]),
            ("What it costs and what you are booking", [
                "Ensembles are priced by size and by hour. A smaller group of five or six players for an hour is commonly $400 to $800; a full ten to twelve-piece ensemble for two hours often runs $1,200 to $2,500, more in markets with few groups and in peak season.",
                "You are booking a specific ensemble, not a style. Ask who is actually playing, hear recent live audio rather than a produced track, and confirm whether the trumpets are included - a mariachi without them is a different sound.",
            ]),
        ],
        "planning": [
            ("Give them the song list early", "Mariachi repertoire is deep but not infinite, and family songs matter here. Send your must-plays weeks ahead so they can prepare anything unfamiliar."),
            ("Sort out sound with your venue and DJ", "Mariachi is largely acoustic and often needs no PA outdoors, but indoors or in a large room it does. Your DJ and the ensemble need to have agreed who provides what."),
            ("Tell them where to stand", "Twelve musicians in full traje need floor space and an entrance. Walk it with your coordinator."),
            ("Plan the handover", "The moment mariachi finishes and the DJ takes over is a real transition. Scheduled properly it is seamless; unscheduled it is ten minutes of silence."),
        ],
        "faqs": [
            ("How much does a mariachi band cost for a wedding?",
             "A five or six-piece ensemble for an hour commonly costs $400 to $800. A full ten to twelve-piece group for two hours typically runs $1,200 to $2,500, varying by market and season."),
            ("How long should mariachi play at a wedding?",
             "One to two hours is standard - most often covering the ceremony, cocktail hour or the couple's entrance - with a DJ or band handling the rest of the reception."),
            ("What is a serenata?",
             "A smaller mariachi set performed for the bride the night before or the morning of the wedding, usually at home and for family only. It is a separate booking from the wedding day itself and is often the more emotional of the two."),
        ],
    },
    "filipino-wedding-traditions": {
        "group": 'Filipino',
        "question": "What are the Filipino wedding traditions?",
        "short": "Filipino wedding traditions",
        "culture": "Filipino",
        "also": "cord and veil ceremony, Filipino Catholic wedding, sponsors",
        "cats": ["wedding-officiants", "wedding-photographers", "wedding-planners"],
        "related": ["what-is-a-lazo", "the-veil-ceremony", "padrinos-and-madrinas"],
        "lede": "A Filipino Catholic wedding is built around three ceremonial gifts - the veil, the cord and the coins - each placed by a different pair of sponsors, plus the candle ceremony that opens them. Together they make the ceremony noticeably longer and more participatory than a Western Catholic wedding, because a dozen or more people have a named part in it.",
        "sections": [
            ("The candle, veil and cord", [
                "The candle sponsors light two taper candles at the start. The veil sponsors drape a white veil over the bride's head and pin it to the groom's shoulder, clothing the two as one. The cord sponsors then lay the yugal - a cord, oversized rosary or garland - over both of them in a figure eight, binding them together for the rest of the ceremony.",
                "Later the couple together lights a single unity candle from the two tapers. The sequence is deliberate: covered, bound, and then one flame from two.",
            ]),
            ("Sponsors, and why there are so many", [
                "Principal sponsors, the ninong and ninang, are the married couples who stand as witnesses and lifelong guarantors of the marriage - the Filipino equivalent of padrinos. Secondary sponsors handle the candle, veil and cord specifically. A large Filipino wedding can name twenty or more people in the programme.",
                "This is not ceremony padding. Being asked to sponsor is a real honour with a real obligation, and the number of sponsors is a direct statement about how many families are being joined.",
            ]),
            ("The reception", [
                "Filipino receptions commonly include the money dance, where guests pin bills to the couple, and frequently a released pair of doves. Programmes tend to be long and heavily hosted, with an emcee working through speeches, games and presentations rather than a floor that simply opens for dancing.",
            ]),
        ],
        "planning": [
            ("Give your officiant the full sponsor list", "Every sponsor pair is named and cued. This is the single most common thing that goes wrong, and it goes wrong loudly in front of everyone."),
            ("Rehearse the sponsors, not just the wedding party", "A dozen people have to step forward, do something with their hands and sit down again. That needs a run-through."),
            ("Budget the ceremony at double", "A Filipino Catholic ceremony with all the gifts commonly runs well over an hour. Your photographer's coverage window and your cocktail hour both depend on getting this estimate right."),
            ("Reserve aisle seats for sponsors", "They all have to get up. Handle it on the seating chart."),
        ],
        "faqs": [
            ("What is the cord and veil ceremony?",
             "Two of the three ceremonial gifts in a Filipino Catholic wedding. Veil sponsors drape a veil over the bride and pin it to the groom to clothe them as one; cord sponsors then lay a yugal - a cord or oversized rosary - over both in a figure eight to bind them together."),
            ("What is the difference between principal and secondary sponsors?",
             "Principal sponsors, the ninong and ninang, are married couples who act as witnesses and lifelong guarantors of the marriage. Secondary sponsors are assigned to a specific element - the candle, the veil or the cord - and perform it during the ceremony."),
            ("How long is a Filipino Catholic wedding ceremony?",
             "Commonly over an hour, and often considerably more, because the candle, veil and cord ceremonies each involve a different pair of sponsors stepping forward. Plan photography coverage and cocktail hour around the longer estimate."),
        ],
    },
    "unity-candle-ceremony": {
        "group": 'Unity rituals',
        "question": "What is a unity candle ceremony?",
        "short": "The unity candle",
        "culture": "Christian & widely adopted",
        "also": "unity ceremony, candle lighting, taper ceremony",
        "cats": ["wedding-officiants", "wedding-venues"],
        "related": ["filipino-wedding-traditions", "unity-sand-ceremony", "the-veil-ceremony"],
        "lede": "In a unity candle ceremony, two taper candles - usually lit earlier by the mothers of the couple - are used together to light a single larger candle, and the tapers are then either extinguished or left burning. It is one of the simplest and most widely adopted unity rituals, and the question of whether to blow out the tapers is a genuine point of disagreement.",
        "sections": [
            ("How it is done", [
                "The two mothers, or another pair chosen by the couple, light the taper candles near the start of the ceremony. After the vows the couple takes one taper each and touches both flames to the central candle at the same time. The central candle is then the only one that needs to stay lit.",
                "Whether the tapers go out afterwards is the interesting part. Extinguishing them reads as two lives merging into one. Leaving them lit reads as two people remaining themselves while making something new together. Many couples now leave them burning, and some officiants will say a line about exactly that choice.",
            ]),
            ("The thing nobody plans for", [
                "Unity candles go wrong outdoors more reliably than almost any other element of a wedding ceremony. Any breeze at all will take out a taper, and a couple standing in front of 120 people trying to relight a candle is a long few seconds.",
                "Hurricane glass, a sheltered position, or an indoor ceremony solve it. So does choosing a sand or water ceremony instead if you are outdoors and exposed.",
            ]),
        ],
        "planning": [
            ("Ask your venue about open flame", "A surprising number of venues restrict it, and some ban it entirely. Check before you buy anything."),
            ("Use hurricane glass outdoors, or choose something else", "Wind is the only real enemy here. Glass shields or a different unity ritual are the two reliable answers."),
            ("Test the wick before the day", "New candles with untrimmed or waxed-over wicks do not light quickly. Somebody should light them once, in advance."),
            ("Tell your photographer where the table is", "It is usually off to one side, which means the couple turns away from the guests and the camera for a full minute."),
        ],
        "faqs": [
            ("Do you blow out the taper candles after the unity candle?",
             "Either is correct. Extinguishing them symbolises two lives becoming one; leaving them lit symbolises two people remaining individuals while building something together. Many couples now leave them burning, and your officiant can say a line explaining the choice."),
            ("Who lights the unity candle tapers?",
             "Traditionally the mothers of the bride and groom, near the beginning of the ceremony. Some couples ask grandparents, children from a previous marriage, or other family members instead."),
            ("What is an alternative to a unity candle outdoors?",
             "A sand ceremony, a water blending ceremony, or handfasting - all of which are wind-proof. Outdoor unity candles fail regularly unless they are shielded by hurricane glass."),
        ],
    },
    "unity-sand-ceremony": {
        "group": 'Unity rituals',
        "question": "What is a sand ceremony at a wedding?",
        "short": "The sand ceremony",
        "culture": "Widely adopted",
        "also": "unity sand, blending ceremony",
        "cats": ["wedding-officiants", "wedding-venues"],
        "related": ["unity-candle-ceremony", "handfasting", "the-veil-ceremony"],
        "lede": "In a sand ceremony the couple pours two differently coloured sands into a single vessel, where the streams layer and mix and cannot be separated again. It does the same job as a unity candle with two practical advantages: it does not blow out, and it leaves a physical object the couple keeps.",
        "sections": [
            ("How it works, and the variations", [
                "Each partner holds a vial of coloured sand and pours into a shared vessel, usually simultaneously or in alternating streams so the layers interleave. The vessel is sealed or corked afterwards and kept.",
                "The obvious and best variation is adding more people. Children from previous relationships, parents, or the whole blended family can each pour a colour, which makes the ceremony say something a two-person ritual cannot. This is the main reason couples choose sand over a candle.",
            ]),
            ("What to watch for", [
                "Sand ceremonies photograph poorly if the vessel is opaque, if the sands are similar in tone, or if the table faces away from the guests. Clear glass, high-contrast colours and a table angled outward fix all three.",
                "Very fine sand pours fast; coarse sand pours slowly and unevenly. Buy it early and practise once, because the pour is the whole ceremony and it lasts about forty seconds.",
            ]),
        ],
        "planning": [
            ("Choose high-contrast colours", "Two similar shades produce a muddy vessel and an invisible photograph. Contrast is what makes the layers read."),
            ("Angle the table toward your guests", "Otherwise the ceremony happens behind the couple's backs."),
            ("Decide who is pouring", "If children or parents are included, they need a cue and a rehearsal like any other participant."),
            ("Have a plan to get it home", "It is a glass vessel full of loose sand. Somebody needs to be responsible for it at the end of the night."),
        ],
        "faqs": [
            ("What does a sand ceremony symbolise?",
             "Two lives blending into one that cannot be separated again - the layered sands physically cannot be sorted back into their original vials. When more family members pour, it symbolises the joining of whole households rather than only the couple."),
            ("Is a sand ceremony better than a unity candle?",
             "Outdoors, almost always - sand does not blow out. It also allows children and parents to participate, and it leaves a keepsake. A unity candle is the stronger choice indoors where flame reads more dramatically."),
            ("Can children take part in a sand ceremony?",
             "Yes, and it is the most common reason couples choose it. Each child pours their own colour, which makes the ceremony about the whole new family rather than only the couple."),
        ],
    },
    "handfasting": {
        "group": 'European & Celtic',
        "question": "What is handfasting at a wedding?",
        "short": "Handfasting",
        "culture": "Celtic & pagan",
        "also": "tying the knot, Celtic handfasting, binding ceremony",
        "cats": ["wedding-officiants", "wedding-photographers"],
        "related": ["what-is-a-lazo", "unity-sand-ceremony", "irish-wedding-traditions"],
        "lede": "Handfasting is the Celtic ceremony in which the couple's hands are bound together with cords or ribbons while they make their promises. It is where the phrase 'tying the knot' comes from, and it has become one of the most widely adopted non-religious ceremony rituals because it is simple, ancient, and visibly about the thing a wedding is about.",
        "sections": [
            ("Where it comes from", [
                "Handfasting appears in Celtic and Scottish practice, at various points as a betrothal rather than a marriage - a binding for a year and a day, after which the couple confirmed or dissolved it. Its modern revival runs through pagan and Wiccan ceremonies and, from there, into secular weddings generally.",
                "Its popularity now owes something to the fact that it carries meaning without carrying doctrine, which makes it usable by couples who want ritual without a religious frame.",
            ]),
            ("How the binding is done", [
                "The couple joins hands - often right to right and left to left, which crosses the arms into an infinity shape - and the officiant or family members lay cords across them, one at a time, frequently saying a vow or blessing with each. The cords are then tied or simply drawn into a knot as the couple pulls their hands apart at the end.",
                "The number and colour of cords is entirely open. Couples commonly use one cord per promise, or one per family, or fabric from something meaningful - a grandmother's scarf, a tartan, a christening blanket.",
            ]),
        ],
        "planning": [
            ("Practise the knot", "Binding two pairs of hands with several cords while everyone watches is harder than it looks. Your officiant should have done it at least once before your wedding."),
            ("Decide whether the cords come off", "Some couples stay bound for the rest of the ceremony; others slide free immediately. It changes what your hands can do afterwards, including the rings."),
            ("Do the rings first if hands are staying bound", "This is the ordering mistake almost everyone makes."),
            ("Choose fabric that photographs", "Thin, pale ribbon disappears against skin and a white dress. Texture and colour read far better."),
        ],
        "faqs": [
            ("Does handfasting mean you are legally married?",
             "Not by itself. Handfasting is a symbolic ritual within a ceremony; the legal marriage depends on your officiant, your licence and your jurisdiction's requirements, exactly as it would without it."),
            ("Where does 'tying the knot' come from?",
             "From handfasting - the literal binding of the couple's hands with cord during the ceremony. The phrase outlived widespread knowledge of the ritual it describes."),
            ("What do the handfasting cords mean?",
             "There is no fixed system. Couples commonly use one cord per vow, one per family being joined, or colours chosen for their own meanings. Fabric from a meaningful source - a family tartan, a grandmother's scarf - is a frequent choice."),
        ],
    },
    "jumping-the-broom": {
        "group": 'African American',
        "question": "What does jumping the broom mean?",
        "short": "Jumping the broom",
        "culture": "African American",
        "also": "the broom ceremony, wedding broom",
        "cats": ["wedding-officiants", "wedding-photographers"],
        "related": ["handfasting", "what-is-a-lazo", "unity-candle-ceremony"],
        "lede": "At the close of the ceremony the couple jumps together over a broom laid on the ground, and the guests count them in. In African American weddings it carries a specific weight: it descends from the weddings of enslaved people who were denied any legal marriage, and jumping the broom was how a community declared a marriage real when the law refused to.",
        "sections": [
            ("The history, plainly", [
                "Enslaved people in the United States could not legally marry. Communities held weddings anyway, and jumping the broom was among the rituals that marked a union as witnessed and binding within that community, whatever the law said. The practice has older parallels in West Africa and in Romani and Welsh custom, but its meaning in African American weddings is inseparable from that specific history.",
                "It fell out of use after emancipation, for the understandable reason that legal marriage was newly available and the broom was associated with its denial. Its modern revival is usually dated to the 1970s and to Roots, and it is now a deliberate act of remembrance - couples choose it as a way of marrying in front of the ancestors who could not.",
            ]),
            ("How it is done", [
                "The broom is laid across the end of the aisle, usually just after the pronouncement. The officiant explains what it means - this is one ritual where the explanation is genuinely part of it, because many guests will not know - and the couple jumps over it hand in hand, generally to a count.",
                "Decorated brooms are common, frequently made or dressed by a family member, and the broom is kept afterwards. Some families use the same broom across generations.",
            ]),
        ],
        "planning": [
            ("Have your officiant explain it aloud", "The history is the point. A jump without the words is a photo opportunity; with them it is the most moving thirty seconds of many ceremonies."),
            ("Decide who lays and removes the broom", "Somebody has to place it at the right moment and take it away afterwards. Assign it and rehearse it."),
            ("Check the dress and the shoes", "It is a real jump, in a gown, in front of everyone. Practise in something similar."),
            ("Tell your photographer it closes the ceremony", "It happens immediately after the pronouncement, when photographers are often repositioning for the recessional."),
        ],
        "faqs": [
            ("Why do couples jump the broom?",
             "In African American weddings it commemorates enslaved ancestors who were legally barred from marrying and who married anyway, with the broom jump marking the union as real within their community. Couples choose it today as an act of remembrance and continuity."),
            ("When in the ceremony do you jump the broom?",
             "Almost always at the very end, just after the pronouncement and before the recessional, with the officiant explaining its meaning first."),
            ("Who can jump the broom?",
             "It is most strongly associated with African American weddings and that specific history. Couples from other backgrounds with a genuine family or cultural connection to the practice also use it; the important thing is knowing and naming what it means."),
        ],
    },
    # ---------------------------------------------- Jewish
    "breaking-the-glass": {
        "group": 'Jewish',
        "question": "Why do they break a glass at a Jewish wedding?",
        "short": "Breaking the glass",
        "culture": "Jewish",
        "also": "stomping the glass, mazel tov glass",
        "cats": ["wedding-officiants", "wedding-photographers"],
        "related": ["the-hora", "the-chuppah", "the-ketubah"],
        "lede": "At the end of a Jewish wedding ceremony the groom - or both partners - stomps on a wrapped glass, it shatters, and the room shouts 'Mazel tov!' It is the single most recognisable moment in a Jewish wedding, and the reason usually given is the most serious one available: even at the height of joy, we remember that the world is broken.",
        "sections": [
            ("What it means", [
                "The oldest explanation is remembrance of the destruction of the Temple in Jerusalem - a deliberate note of grief placed inside the happiest moment of a couple's life, so that joy is never taken as complete while loss exists in the world.",
                "Rabbis and couples offer others alongside it: that the marriage should last as long as the glass stays broken, that the shattering marks an irreversible change of state, that it is a reminder of fragility and therefore of care. Most ceremonies name one or two aloud rather than leaving it unexplained.",
            ]),
            ("How it is done safely", [
                "The glass is wrapped in a cloth napkin or a purpose-made pouch and placed on the floor, usually on something hard. A thin glass breaks reliably; a thick tumbler does not, and a groom stamping repeatedly on an unbroken glass is a memorable moment for the wrong reason.",
                "Many couples now use a glass sold specifically for the purpose, and keep the shards afterwards - a whole small industry exists turning them into mezuzahs, art and keepsakes.",
            ]),
        ],
        "planning": [
            ("Use a thin glass, wrapped properly", "A lightbulb or a purpose-sold breaking glass shatters first time. A drinking tumbler often does not."),
            ("Tell your photographer the exact cue", "It is one frame and it is the last beat of the ceremony. They need to be on the feet, pre-focused, with the shout coming immediately after."),
            ("Decide who breaks it", "Traditionally the groom; many couples now do it together, which needs a rehearsal so the timing works."),
            ("Arrange for the shards", "Someone should collect them if you want them kept. This gets forgotten in the rush of the recessional."),
        ],
        "faqs": [
            ("What does breaking the glass symbolise?",
             "Most traditionally, remembrance of the destruction of the Temple in Jerusalem - grief held inside joy, so that celebration is never treated as complete while the world is broken. Couples also cite fragility, care, and the irreversibility of the moment."),
            ("Who breaks the glass at a Jewish wedding?",
             "Traditionally the groom, at the very end of the ceremony. Many couples today break it together, and some use two glasses."),
            ("What do you say after the glass breaks?",
             "'Mazel tov' - shouted by everyone present, immediately. It marks the end of the ceremony and the start of the celebration."),
        ],
    },
    "the-hora": {
        "group": 'Jewish',
        "question": "What is the hora at a wedding?",
        "short": "The hora",
        "culture": "Jewish",
        "also": "chair dance, horah, lifting the chairs",
        "cats": ["wedding-djs", "wedding-bands", "wedding-venues"],
        "related": ["breaking-the-glass", "the-chuppah", "la-hora-loca"],
        "lede": "The hora is the circle dance that opens a Jewish wedding reception, and its famous part is the chair lift: the couple is hoisted overhead on chairs while the room dances around them, each holding one end of a napkin between them. It is loud, fast and genuinely the high point of the night at most Jewish weddings.",
        "sections": [
            ("How it unfolds", [
                "Guests join hands in concentric circles and dance to Hava Nagila and related music, moving inward and outward. At some point strong volunteers bring two sturdy chairs, the couple sits, and they are lifted. Because they cannot hold hands at that height, they hold opposite ends of a napkin or handkerchief instead.",
                "Parents, grandparents and sometimes the wedding party get lifted after the couple. The dance runs as long as the energy holds - often ten or fifteen minutes, which is far longer than couples expect.",
            ]),
            ("The lift, honestly", [
                "This is the part that requires actual planning. It takes four capable people per chair who know what they are doing, chairs without arms and with solid frames, and a ceiling with real clearance. Injuries at weddings happen here more than almost anywhere else.",
                "Brief your lifters before the reception, not during it. Tell them to lift from the seat frame rather than the back, to move slowly, and to put the chair down when the couple says so rather than when the song ends.",
            ]),
        ],
        "planning": [
            ("Pick and brief your lifters in advance", "Eight named people, told the day before. Not whoever is nearest when the music starts."),
            ("Check ceiling height with your venue", "Chandeliers, low beams and tented ceilings are all real constraints, and the venue will know."),
            ("Use the right chairs", "Armless, solid, no folding chairs. Ask the venue to set two aside specifically."),
            ("Have the napkin ready", "The couple cannot hold hands while lifted. Someone should hand it up as they sit down."),
        ],
        "faqs": [
            ("What is the chair dance at a Jewish wedding?",
             "It is part of the hora, the circle dance that opens the reception. The couple is lifted overhead on chairs while guests dance around them, holding opposite ends of a napkin because they cannot reach each other's hands."),
            ("Why do they hold a napkin during the hora?",
             "Because once they are lifted on separate chairs they are too far apart to hold hands. Each holds one end of a napkin or handkerchief so they stay connected through the lift."),
            ("How long does the hora last?",
             "Commonly ten to fifteen minutes, often longer. It usually opens the reception and typically includes lifting the couple's parents after the couple themselves."),
        ],
    },
    "the-chuppah": {
        "group": 'Jewish',
        "question": "What is a chuppah?",
        "short": "The chuppah",
        "culture": "Jewish",
        "also": "huppah, wedding canopy",
        "cats": ["wedding-florists", "wedding-rentals", "wedding-venues"],
        "related": ["breaking-the-glass", "the-ketubah", "the-hora"],
        "lede": "A chuppah is the canopy a Jewish couple stands beneath to be married: a cloth held up by four poles, open on every side. The openness is the whole point - it represents the home the couple is building, and a home in this tradition is defined by the fact that its sides are open to everyone who might need to come in.",
        "sections": [
            ("What it represents", [
                "The canopy is the couple's first home together, and it is a roof without walls. The reference is to Abraham and Sarah's tent, open on all four sides so travellers could be welcomed from any direction. A chuppah with enclosed sides would say the opposite of what it is for.",
                "It is deliberately temporary and often visibly fragile - cloth and poles rather than anything built. A marriage is understood to be sheltered by the people holding it up rather than by the structure itself.",
            ]),
            ("Who holds it, and what it is made of", [
                "Many chuppahs are held by four people for the length of the ceremony, which is an honour given to close friends or family. Others are freestanding. Holding it for a forty-minute ceremony is harder than volunteers expect, and rotating holders mid-ceremony is common.",
                "The cloth is often meaningful rather than decorative: a family tallit, a quilt made by relatives, an heirloom textile. Florists build elaborate ones, but a grandfather's prayer shawl over four simple poles is the more traditional object.",
            ]),
        ],
        "planning": [
            ("Decide freestanding or held early", "It changes the rental, the florals and whether four people are standing still for forty minutes. This decision drives several vendors."),
            ("Weight it if you are outdoors", "A chuppah is a sail. Wind is the reason outdoor chuppahs fall over, and the fix is proper weighting, agreed with your rental company."),
            ("Tell your florist the cloth matters", "If you are using a family tallit, the florals frame it rather than cover it. Say so explicitly."),
            ("Brief the holders", "Rotating in a second set of holders halfway through is normal and should be rehearsed."),
        ],
        "faqs": [
            ("Why is a chuppah open on all sides?",
             "It represents the couple's home, modelled on Abraham and Sarah's tent which was open on four sides to welcome travellers from any direction. An open home is the point, so the sides are never enclosed."),
            ("Who holds the chuppah?",
             "Often four close friends or family members, as an honour, for the length of the ceremony. Freestanding chuppahs are also common, particularly for longer ceremonies or outdoor weddings."),
            ("What is a chuppah made of?",
             "Four poles and a cloth. The cloth is frequently meaningful rather than decorative - a family tallit, a handmade quilt or an heirloom textile - though florists also build elaborate floral versions."),
        ],
    },
    "the-ketubah": {
        "group": 'Jewish',
        "question": "What is a ketubah?",
        "short": "The ketubah",
        "culture": "Jewish",
        "also": "marriage contract, ketubah signing",
        "cats": ["wedding-invitations", "wedding-officiants", "wedding-photographers"],
        "related": ["the-chuppah", "breaking-the-glass", "the-hora"],
        "lede": "A ketubah is the Jewish marriage contract - historically a legal document setting out a husband's obligations to his wife, and today usually a piece of art the couple signs before the ceremony and hangs in their home. The signing happens privately, with witnesses, and is often the most emotionally intense part of the whole day precisely because almost nobody is watching.",
        "sections": [
            ("What it says", [
                "The traditional Aramaic text is a contract: it specifies what the husband owes the wife in food, clothing and intimacy, and what she receives if the marriage ends. It was, and this is worth stating plainly, a protective instrument for women at a time when they had little other recourse.",
                "Modern ketubot vary enormously. Orthodox couples use the traditional text unchanged. Conservative, Reform, egalitarian, interfaith and same-sex couples commonly use versions with mutual obligations, frequently in both Hebrew and English, and often written partly by the couple themselves.",
            ]),
            ("The signing", [
                "It takes place before the ceremony, in a small room, with the officiant and two witnesses. Traditionally the witnesses must be observant Jews unrelated to the couple; requirements vary by movement and your rabbi will tell you.",
                "Many couples describe this as the moment they actually felt married - the ceremony under the chuppah is public, and the signing is not. Photographers who know that treat it accordingly.",
            ]),
        ],
        "planning": [
            ("Order it three months out", "Ketubot are frequently made to order by an artist, with the couple's names and date lettered in. Rush fees are real and text errors are unfixable."),
            ("Proofread the Hebrew with your officiant", "Names, dates and spellings in Hebrew are the most common error, and they are permanent."),
            ("Ask your rabbi about witness requirements", "Who may sign varies by movement. Sort it before you ask two friends."),
            ("Tell your photographer to be in the room", "It is quiet, it is small, and it is often the best twenty minutes of the day."),
        ],
        "faqs": [
            ("What does a ketubah say?",
             "Traditionally it is a marriage contract in Aramaic setting out the husband's obligations to his wife and her entitlements if the marriage ends. Modern versions - Conservative, Reform, egalitarian, interfaith and same-sex - commonly use mutual language in Hebrew and English."),
            ("Who signs the ketubah?",
             "The couple, the officiant and two witnesses, usually in a private room before the ceremony. Traditional practice requires witnesses who are observant Jews unrelated to the couple, though requirements vary by movement."),
            ("When do you sign the ketubah?",
             "Before the ceremony, in a small private gathering. It is then often read aloud or displayed under the chuppah during the ceremony itself."),
        ],
    },
    # ---------------------------------------------- South Asian
    "mehndi-ceremony": {
        "group": 'South Asian',
        "question": "What is a mehndi ceremony?",
        "short": "Mehndi",
        "culture": "South Asian",
        "also": "henna night, mehendi, mehandi",
        "cats": ["hair-and-makeup", "wedding-photographers", "wedding-venues"],
        "related": ["the-baraat", "haldi-ceremony", "saptapadi"],
        "lede": "Mehndi is the pre-wedding celebration where intricate henna designs are applied to the bride's hands, arms and feet - a process that takes hours - while family and friends eat, sing and have their own henna done. It is usually one or two days before the wedding and is, for many families, the warmest and least formal event of the entire week.",
        "sections": [
            ("What happens", [
                "A mehndi artist works on the bride for anywhere from three to eight hours depending on the intricacy and coverage. Guests have simpler designs applied alongside. There is food, music and, in many families, choreographed dances that the relatives have been rehearsing for weeks.",
                "The groom's name or initials are traditionally hidden somewhere in the bride's design, and he is meant to find them - a game that produces a good deal of laughing and at least one photograph.",
            ]),
            ("The henna itself", [
                "Darker stain is considered auspicious, and the depth depends on the paste quality, how long it stays on, and aftercare. Serious brides leave it on overnight, avoid water afterwards, and treat the stain as it develops over the following day or two.",
                "One genuine safety point: 'black henna' containing PPD is not henna, causes chemical burns and permanent scarring in some people, and should be refused outright. Real henna stains orange first and darkens to deep red-brown over 24 to 48 hours.",
            ]),
        ],
        "planning": [
            ("Book the artist months ahead", "Good mehndi artists are booked out in peak season, and bridal coverage is a full day's work for one person."),
            ("Schedule it far enough ahead of the wedding", "The stain darkens for up to 48 hours. Most brides want mehndi two days before so it is at its deepest on the wedding day."),
            ("Insist on natural henna", "Ask what is in the paste. Refuse anything described as black henna."),
            ("Plan for immobile hands", "The bride cannot use her hands for hours, then must avoid water. Eating, bathroom trips and changing all need help arranged in advance."),
        ],
        "faqs": [
            ("How long does bridal mehndi take?",
             "Three to eight hours for a bride depending on intricacy and how far up the arms and legs the design goes. Guests' simpler designs take a few minutes each."),
            ("How long before the wedding should mehndi be done?",
             "Usually two days before. Henna stains orange at first and darkens over 24 to 48 hours, so timing it this way means the colour peaks on the wedding day."),
            ("Is black henna safe?",
             "No. So-called black henna usually contains PPD, a chemical that causes burns and can leave permanent scars. Natural henna stains orange and darkens to red-brown; anything promising instant black should be refused."),
        ],
    },
    "the-baraat": {
        "group": 'South Asian',
        "question": "What is a baraat?",
        "short": "The baraat",
        "culture": "South Asian",
        "also": "groom's procession, barat, ghodi",
        "cats": ["wedding-transportation", "wedding-bands", "wedding-venues"],
        "related": ["mehndi-ceremony", "haldi-ceremony", "saptapadi"],
        "lede": "The baraat is the groom's arrival procession at a South Asian wedding: he travels to the venue accompanied by his family and friends, traditionally on a decorated white horse, while a dhol drummer plays and everyone dances in the street in front of him. It is loud, it blocks traffic, and it is one of the great entrances in any wedding tradition.",
        "sections": [
            ("How it works", [
                "The groom's side gathers a short distance from the venue and processes the last stretch on foot, dancing, with the groom riding a horse or arriving in a decorated car - and increasingly a vintage car, a motorcycle or something more inventive. A dhol player leads, and the procession moves at the speed of the dancing, which is slow.",
                "At the venue the bride's family meets the procession for the milni, where members of each family greet their counterparts - fathers to fathers, brothers to brothers - often with garlands and often with some good-natured competition about who lifts whom.",
            ]),
            ("The part that needs permits", [
                "A baraat frequently occupies a public street for twenty to forty minutes with a hundred dancing people, amplified drums and a horse. In many cities that requires notifying police, sometimes a permit, and almost always a conversation with the venue.",
                "Horses need a handler, a permitted route, somewhere to wait and, in hot markets, shade and water. This is a real logistics item rather than a detail.",
            ]),
        ],
        "planning": [
            ("Check permits and the venue's policy early", "Street closures, amplified sound and livestock are all separately regulated. Start this months ahead."),
            ("Budget an hour, not twenty minutes", "Baraats consistently overrun, and every subsequent item in the day shifts with them. Tell your planner to build the buffer in."),
            ("Book the dhol player and the horse separately and early", "Both are specialist suppliers with limited availability in peak season."),
            ("Tell your photographer and videographer the route", "It is a moving, crowded, dusty procession. They need to know where it starts, where it ends and where they can get ahead of it."),
        ],
        "faqs": [
            ("What happens at a baraat?",
             "The groom processes to the wedding venue with his family and friends dancing around him to a dhol drummer, traditionally riding a decorated white horse. The bride's family meets the procession on arrival for the milni greeting."),
            ("How long does a baraat last?",
             "Typically 30 to 60 minutes, and it very often runs longer than planned because the procession moves at the speed of the dancing. Build a buffer into the day's timeline."),
            ("Do you need a permit for a baraat?",
             "Often yes. Occupying a public street with a large procession, amplified drums and a horse commonly requires notifying police or obtaining a permit, and the venue will have its own rules. Check several months ahead."),
        ],
    },
    "haldi-ceremony": {
        "group": 'South Asian',
        "question": "What is a haldi ceremony?",
        "short": "Haldi",
        "culture": "South Asian",
        "also": "pithi, turmeric ceremony, gaye holud",
        "cats": ["hair-and-makeup", "wedding-photographers"],
        "related": ["mehndi-ceremony", "the-baraat", "saptapadi"],
        "lede": "At the haldi ceremony, family members smear a paste of turmeric, sandalwood and oil onto the bride and groom - usually at their own homes, usually the morning of or the day before the wedding. It is a blessing, a skin ritual, and in practice a licensed opportunity for relatives to cover the couple in yellow paste while everyone laughs at them.",
        "sections": [
            ("What it is for", [
                "Turmeric is understood as purifying and auspicious, and the paste is applied to bless the couple, ward off harm and give the skin a glow before the wedding. Married women in the family usually begin, and then it escalates as everyone joins in.",
                "The tone is important: haldi is not solemn. It is deliberately messy and funny, and it is frequently the event where the couple's families relax into each other for the first time. In Bengali tradition the equivalent is gaye holud; in Gujarati families, pithi.",
            ]),
            ("The staining, which is real", [
                "Turmeric stains skin, nails, hair, fabric, tile and grout. The couple wears clothes designated to be ruined - traditionally yellow - and the ceremony is almost always held outdoors or somewhere hoseable.",
                "It washes off skin over a day or so with scrubbing, which is why haldi is scheduled with enough margin before the wedding. Nail beds and light-coloured grout hold it longest.",
            ]),
        ],
        "planning": [
            ("Hold it somewhere you do not mind staining", "Outdoors, on a terrace, or on a surface that can be hosed. Not on pale carpet, ever."),
            ("Schedule enough margin before the wedding", "Turmeric needs a day and some scrubbing to fade. The morning of the wedding is cutting it fine."),
            ("Warn your hair and makeup artist", "They need to know what the skin has just been through, especially if there is any residual tint."),
            ("Dress everyone for destruction", "Guests get covered too. Say so on the invitation so nobody arrives in something they love."),
        ],
        "faqs": [
            ("What is the purpose of the haldi ceremony?",
             "Turmeric paste is applied to the bride and groom as a blessing - understood as purifying, auspicious and good for the skin before the wedding. In practice it is also a deliberately messy, joyful event that brings both families together."),
            ("When is the haldi ceremony held?",
             "Usually the morning of the wedding or the day before, at the bride's and groom's homes separately. Leaving a day's margin helps, since turmeric takes time and scrubbing to fade from skin."),
            ("Does turmeric stain your skin?",
             "Yes, and clothing, nails and surfaces too. Wear clothes you are willing to ruin - traditionally yellow - and hold the ceremony outdoors or somewhere that can be washed down."),
        ],
    },
    "saptapadi": {
        "group": 'South Asian',
        "question": "What is saptapadi, the seven steps?",
        "short": "Saptapadi",
        "culture": "Hindu",
        "also": "seven steps, saat phere, seven vows",
        "cats": ["wedding-officiants", "wedding-photographers"],
        "related": ["the-baraat", "haldi-ceremony", "mehndi-ceremony"],
        "lede": "Saptapadi is the heart of a Hindu wedding: the couple takes seven steps together around a sacred fire, and with each step makes a specific vow. In most traditions the marriage is considered complete and binding at the seventh step - not at a pronouncement, not at a signature, but at a shared walk.",
        "sections": [
            ("The seven vows", [
                "Each step carries its own promise, and while the wording varies by region and family, the shape is consistent: to provide for and nourish each other; to grow together in strength; to prosper and hold wealth in common; to share happiness and hardship; to care for their children and family; to stay together through the seasons of life; and to remain friends, lifelong, above all else.",
                "That last one is worth noticing. The seventh and binding vow in one of the world's oldest continuous marriage rites is a promise of friendship.",
            ]),
            ("Around the fire", [
                "The steps are taken around Agni, the sacred fire, which serves as the witness to the marriage - the fire is the reason the ceremony is legally and religiously complete, standing in the role a registrar or congregation plays elsewhere. The couple's garments are usually knotted together for the circuits.",
                "A full Hindu ceremony containing saptapadi commonly runs one to three hours and includes many other rites around it. The seven steps themselves take a few minutes.",
            ]),
        ],
        "planning": [
            ("Confirm open flame with your venue months ahead", "A sacred fire indoors is a genuine fire-code question. Many venues permit it with conditions; some will not at all, and you need to know before you book."),
            ("Ask about ventilation and smoke alarms", "A havan produces real smoke. Venues that allow it will usually have a protocol - use it."),
            ("Tell your photographer the ceremony is long and seated", "Guests and photographers both need to know the shape of a two-hour ceremony so the key rites are not missed while someone is changing a lens."),
            ("Ask your priest for a written running order", "So your coordinator, photographer and videographer all know what is coming and when."),
        ],
        "faqs": [
            ("What are the seven steps in a Hindu wedding?",
             "Saptapadi - seven steps taken together around the sacred fire, each carrying a vow: to nourish each other, grow in strength, prosper together, share joy and sorrow, care for family, stay together through life's seasons, and remain lifelong friends."),
            ("When is a Hindu marriage considered complete?",
             "In most traditions at the seventh step of the saptapadi. The sacred fire, Agni, acts as the witness to the marriage."),
            ("How long is a Hindu wedding ceremony?",
             "Commonly one to three hours, containing many rites of which saptapadi is the central one. Ask your priest for a written running order so your vendors know the shape of it."),
        ],
    },
    # ---------------------------------------------- East Asian
    "chinese-tea-ceremony": {
        "group": 'East Asian',
        "question": "What is the Chinese tea ceremony at a wedding?",
        "short": "The tea ceremony",
        "culture": "Chinese",
        "also": "jing cha, wedding tea ceremony",
        "cats": ["wedding-photographers", "wedding-planners", "wedding-venues"],
        "related": ["korean-paebaek", "the-baraat", "unity-candle-ceremony"],
        "lede": "In the Chinese wedding tea ceremony the couple kneels and serves tea to their parents and elders in strict order of seniority, addressing each by their proper title. The elders drink, then give red envelopes or jewellery in return. It is a formal act of respect and of being formally received into each other's families, and it is usually held privately rather than in front of all the guests.",
        "sections": [
            ("The order, which matters", [
                "Tea is served by seniority, and getting the order wrong is a real error rather than a small one. It typically begins with the groom's parents, then grandparents and older relatives on his side, then the bride's family, though many families now do the bride's side first or run two ceremonies.",
                "The couple addresses each person by their correct familial title as they serve - a system considerably more precise in Chinese than in English, distinguishing maternal from paternal and older from younger. Couples often write themselves a list.",
            ]),
            ("What is served, and what comes back", [
                "The tea is usually sweet - lotus seeds and red dates are common, the pairing being a wish for children and for sweetness. It is served in small cups, held with both hands, offered while kneeling on cushions.",
                "Elders drink, offer a few words, and give red envelopes containing money or, frequently, gold jewellery placed directly on the bride. In many families the jewellery accumulates visibly across the ceremony.",
            ]),
        ],
        "planning": [
            ("Write the serving order down with a parent", "This is the one thing to get right, and the family member who knows the hierarchy should dictate it. Do not improvise."),
            ("Book a room and a time", "The tea ceremony is usually private and can take an hour with a large family. It needs its own slot in the day, not a gap."),
            ("Have someone manage the envelopes", "Red envelopes and jewellery accumulate fast. Assign one trusted person to collect and secure them as they are given."),
            ("Tell your photographer it is intimate and interior", "Small room, kneeling, low light, dozens of short exchanges. Very different from anything else in the day."),
        ],
        "faqs": [
            ("What is the purpose of the Chinese wedding tea ceremony?",
             "It is a formal act of respect in which the couple serves tea to parents and elders in order of seniority, and is formally received into each other's families. Elders respond with red envelopes or gold jewellery."),
            ("What order do you serve tea in?",
             "By seniority, traditionally starting with the groom's parents and grandparents before the bride's side, though many families now vary this. Write the order down with a family member who knows the hierarchy - getting it wrong is a genuine error."),
            ("What tea is used in a wedding tea ceremony?",
             "Usually a sweet tea with lotus seeds and red dates, symbolising a wish for children and for sweetness in the marriage. It is served in small cups, offered with both hands while kneeling."),
        ],
    },
    "korean-paebaek": {
        "group": 'East Asian',
        "question": "What is a paebaek ceremony?",
        "short": "Paebaek",
        "culture": "Korean",
        "also": "pyebaek, Korean wedding ceremony, chestnut and jujube",
        "cats": ["wedding-photographers", "wedding-rentals", "wedding-planners"],
        "related": ["chinese-tea-ceremony", "the-veil-ceremony", "unity-candle-ceremony"],
        "lede": "Paebaek is the Korean ceremony in which the couple, dressed in hanbok, formally greets the groom's parents - and now usually both families - with deep bows and tea. It ends with the parents throwing chestnuts and jujubes into a cloth the couple holds stretched between them, and the number they catch is said to predict how many children they will have.",
        "sections": [
            ("What happens", [
                "The couple wears hanbok and performs a deep formal bow, the keunjeol, to each set of parents in turn, then serves them tea or wine. The parents offer advice and blessings, and give money in return - traditionally tucked into the bride's skirt or handed over directly.",
                "Then the chestnuts and jujubes: dates for daughters, chestnuts for sons, thrown by the parents while the couple catches what they can in a stretched cloth. It is played for laughs, and it is the photograph everyone wants.",
            ]),
            ("How it fits a modern wedding", [
                "Paebaek was historically held at the groom's family home after the wedding and involved only his relatives. Most couples now hold it at the wedding venue between the ceremony and reception, and include both families, which is a reasonable and widely accepted adaptation.",
                "It requires a changed outfit, a dedicated room and a proper setup - a low table, screens, cushions - which most couples rent as a package from a specialist supplier.",
            ]),
        ],
        "planning": [
            ("Book the hanbok and the setup together", "Specialist suppliers rent the table, screens, cushions and the food display as one package, often with someone to dress the bride."),
            ("Schedule the outfit change realistically", "Hanbok takes time to put on properly, usually with help. Twenty minutes is optimistic."),
            ("Give it a private room between ceremony and reception", "It is a family event, not a guest event, and it needs its own space and slot in the timeline."),
            ("Warn your photographer about the throw", "The chestnut-and-jujube catch is fast, funny and unrepeatable. It should be the shot they are set up for."),
        ],
        "faqs": [
            ("What happens at a paebaek ceremony?",
             "The couple, in hanbok, performs deep formal bows to their parents and serves them tea or wine. Parents offer blessings and money, then throw chestnuts and jujubes for the couple to catch in a stretched cloth."),
            ("What do the chestnuts and dates mean at a Korean wedding?",
             "Jujubes (dates) traditionally represent daughters and chestnuts represent sons, and the number the couple catches is playfully said to predict how many children they will have."),
            ("When is paebaek held?",
             "Traditionally at the groom's family home after the wedding. Most couples now hold it at the venue between the ceremony and the reception, with both families present."),
        ],
    },
    # ---------------------------------------------- European
    "greek-stefana": {
        "group": 'European & Celtic',
        "question": "What are stefana in a Greek wedding?",
        "short": "Stefana",
        "culture": "Greek Orthodox",
        "also": "wedding crowns, stephana, crowning ceremony",
        "cats": ["wedding-officiants", "wedding-florists", "wedding-photographers"],
        "related": ["what-is-a-lazo", "the-veil-ceremony", "handfasting"],
        "lede": "Stefana are two crowns joined by a single white ribbon, placed on the heads of a Greek Orthodox couple during their wedding. The koumbaro or koumbara swaps them back and forth over the couple's heads three times, and the ribbon is the point: two crowns, one cord, one household with two heads.",
        "sections": [
            ("The crowning", [
                "The priest places the stefana, then the koumbaro - the wedding sponsor, a role of real ongoing significance - exchanges them over the couple's heads three times, the number recurring throughout the Orthodox service for the Trinity. The couple wears them for the rest of the ceremony, including the ceremonial walk around the altar table.",
                "The crowns mark the couple as the king and queen of their own household, and the joining ribbon says that the two crowns are one thing. They are removed by the priest at the end and kept afterwards, often in a purpose-made display case.",
            ]),
            ("The dance of Isaiah", [
                "Still crowned and holding candles, the couple is led by the priest three times around the altar table in the couple's first steps as a married pair. The koumbaro follows, steadying the stefana so they do not fall.",
                "This is the moment guests remember, and it is also a slow, circular, candlelit procession in a church - a genuinely difficult lighting situation that a photographer should know is coming.",
            ]),
        ],
        "planning": [
            ("Ask the church its photography rules first", "Orthodox churches vary widely on where photographers may stand and whether flash is permitted. Some restrict movement entirely during the crowning."),
            ("Choose stefana you intend to keep", "They are a permanent object, displayed at home afterwards. Many families pass them down or have them made to order."),
            ("Brief the koumbaro properly", "The three exchanges and the walk both depend on them. It is an active role, not an honorary one."),
            ("Check hairstyles against the crowns", "Stefana sit on the head and are swapped repeatedly. Your stylist needs to know at the trial."),
        ],
        "faqs": [
            ("What do the stefana symbolise?",
             "The crowns mark the couple as king and queen of their own household, and the single ribbon joining them signifies that the two are now one. They are worn for the remainder of the ceremony and kept afterwards."),
            ("Who swaps the stefana?",
             "The koumbaro or koumbara, the wedding sponsor, exchanges them over the couple's heads three times. It is a significant ongoing role in the couple's life, not just a ceremonial one."),
            ("What is the dance of Isaiah?",
             "The couple, still crowned and holding candles, is led by the priest three times around the altar table - their first steps together as a married couple, with the koumbaro following to steady the crowns."),
        ],
    },
    "irish-wedding-traditions": {
        "group": 'European & Celtic',
        "question": "What are Irish wedding traditions?",
        "short": "Irish wedding traditions",
        "culture": "Irish & Celtic",
        "also": "Claddagh ring, Irish wedding customs, Celtic wedding",
        "cats": ["wedding-officiants", "wedding-bands", "wedding-invitations"],
        "related": ["handfasting", "greek-stefana", "something-old-something-new"],
        "lede": "Irish wedding customs run from the Claddagh ring and handfasting to the magic hanky, the ringing of bells and a horseshoe carried for luck. Most are small, portable and easy to fold into any ceremony, which is why couples with distant Irish heritage adopt them more readily than almost any other tradition.",
        "sections": [
            ("The Claddagh ring", [
                "Two hands holding a crowned heart: friendship, love and loyalty. How it is worn is a message in itself - on the right hand with the point of the heart outward means unattached, turned inward means spoken for, and on the left hand turned inward means married.",
                "Claddagh rings are frequently used as the actual wedding band, and equally often passed from a grandmother, which makes them a natural 'something old'.",
            ]),
            ("Bells, hankies and horseshoes", [
                "Small bells are rung during the ceremony or given to guests, said to keep bad spirits away and, more usefully, to remind a couple of their vows when they later argue - many couples keep one at home for exactly that stated reason.",
                "The magic hanky is a lace handkerchief the bride carries and cries into, later stitched into a christening bonnet for a future child and unpicked back into a handkerchief for that child's own wedding. A horseshoe, traditionally real and now usually a small ornament, is carried points-up so the luck does not run out.",
            ]),
            ("Handfasting and the wedding band", [
                "Handfasting is Celtic in origin and is covered in its own guide. Irish weddings also lean heavily on live music, and a trad band for part of the night - fiddle, bodhrán, accordion - is common even at otherwise modern receptions.",
            ]),
        ],
        "planning": [
            ("Tell your officiant which customs you want", "Bells, a hanky and a horseshoe all need a cue or a mention. They are easy to include and easy to forget on the day."),
            ("Size a Claddagh ring properly if it is the band", "An heirloom ring may need resizing, which takes weeks and should be done by someone who has handled one before."),
            ("Ask about a trad set", "Many bands will play an hour of traditional Irish music and then switch. Agree which part of the night it covers."),
            ("Decide who carries the horseshoe", "It is traditionally carried by the bride and is the sort of thing that gets left in a hotel room."),
        ],
        "faqs": [
            ("How do you wear a Claddagh ring?",
             "On the right hand with the heart pointing outward means unattached; turned inward means in a relationship. On the left hand with the heart turned inward means married."),
            ("What is the Irish magic hanky?",
             "A lace handkerchief the bride carries on her wedding day, later stitched into a christening bonnet for a child, and unpicked back into a handkerchief for that child's own wedding."),
            ("Why do Irish weddings use bells?",
             "Bells are rung to ward off bad spirits, and are also given to couples as a reminder of their vows - a bell kept at home to be rung during an argument is a common and quite practical piece of the tradition."),
        ],
    },
    "something-old-something-new": {
        "group": 'European & Celtic',
        "question": "What does something old, something new mean?",
        "short": "Something old, something new",
        "culture": "English & widely adopted",
        "also": "something borrowed something blue, the rhyme, four somethings",
        "cats": ["wedding-invitations", "wedding-photographers", "hair-and-makeup"],
        "related": ["irish-wedding-traditions", "handfasting", "unity-sand-ceremony"],
        "lede": "Something old, something new, something borrowed, something blue, and a silver sixpence in her shoe. The rhyme is Victorian English, each item is a specific wish rather than a decoration, and the fifth line - the one almost everyone forgets - is the one about money.",
        "sections": [
            ("What each one is for", [
                "Something old carries continuity with the bride's family and past. Something new represents optimism for the life beginning. Something borrowed should come from a happily married woman, the idea being that her good fortune transfers with the object. Something blue stands for fidelity, love and purity - blue has been the colour of constancy in English tradition far longer than white has been the colour of weddings.",
                "The sixpence in the shoe is a wish for prosperity, traditionally given by the bride's father. It is the line most often dropped from the rhyme and the easiest to include.",
            ]),
            ("How couples actually do it now", [
                "The most meaningful versions are the least visible. A piece of a mother's dress sewn into the hem, a grandfather's watch in a pocket, a locket with a photograph pinned inside the bouquet, a blue ribbon stitched where nobody will see it.",
                "There is no requirement that any of it show, and the four somethings are among the easiest traditions to adapt - couples of every gender combination use them, and plenty of grooms carry their own.",
            ]),
        ],
        "planning": [
            ("Sort the sewing weeks ahead", "Anything stitched into a dress goes to the alterations appointment, not to the morning of the wedding."),
            ("Tell your photographer what they are", "These are small objects with large stories, and they are worth ten minutes of detail photography - but only if someone knows they exist."),
            ("Ask early for the borrowed item", "Asking a relative to lend something for the day is a lovely conversation, and a rushed one is less lovely."),
            ("Put the sixpence somewhere you can walk on", "Under the arch of the foot, taped, is the practical answer. A loose coin underfoot for eight hours is not."),
        ],
        "faqs": [
            ("What is the full something old something new rhyme?",
             "Something old, something new, something borrowed, something blue, and a silver sixpence in her shoe. The final line about the sixpence - a wish for prosperity - is the part most commonly left out."),
            ("Who should the borrowed item come from?",
             "Traditionally a happily married woman, on the idea that her good fortune in marriage passes along with the object. A mother's or grandmother's item is the most common choice."),
            ("Why something blue?",
             "Blue has signified fidelity, love and constancy in English tradition for centuries - considerably longer than white has been associated with weddings."),
        ],
    },
    # ---------------------------------------------- Middle Eastern & Persian
    "persian-sofreh-aghd": {
        "group": "Middle Eastern & Persian",
        "question": "What is a sofreh aghd?",
        "short": "The sofreh aghd",
        "culture": "Persian & Iranian",
        "also": "Persian wedding spread, sofreh-ye aghd",
        "cats": ["wedding-officiants", "wedding-rentals", "wedding-photographers"],
        "related": ["what-is-a-lazo", "the-chuppah", "greek-stefana"],
        "lede": "The sofreh aghd is the elaborate spread laid on the floor at a Persian wedding, facing east, covered with symbolic objects: a mirror, candles, honey, flatbread, eggs, coins, wild rue and a book of faith or poetry. The couple sits before it, and every item on it is a wish for something specific in the marriage.",
        "sections": [
            ("What is on it, and why", [
                "The mirror and two candelabra are the centrepiece: the couple's first glance at each other in the mirror is the image most Persian weddings are remembered by. Honey for sweetness, fed to each other on a fingertip. Flatbread and herbs for prosperity, decorated eggs and nuts for fertility, coins for wealth, and esfand (wild rue) burned to keep the evil eye away.",
                "A book sits at the centre - a Qur'an for Muslim families, the Avesta for Zoroastrians, or the poetry of Hafez or Khayyam for secular ones. The spread is genuinely ecumenical in practice; families adapt it to what they believe.",
            ]),
            ("The sugar cones, and the three asks", [
                "Two women whose own marriages are happy hold a cloth above the couple and grind two sugar cones over it, showering sweetness onto the marriage. It goes on through the ceremony and is one of the great photographs of any wedding tradition.",
                "Meanwhile the officiant asks the bride three times whether she consents. She traditionally stays silent for the first two - often while someone announces she has gone to pick flowers - and answers on the third. It is played for laughs and it is the moment the room waits for.",
            ]),
        ],
        "planning": [
            ("Book the sofreh setup as its own vendor", "Specialists rent and style the full spread, and it is a substantial floor installation that needs space, setup time and a specific orientation."),
            ("Tell your venue it faces east and sits on the floor", "It needs floor area in front of the couple, and the direction is not negotiable. Confirm the room can accommodate it."),
            ("Warn your venue about burning esfand", "It produces smoke. Many venues restrict it, and indoor smoke alarms are a real consideration."),
            ("Tell your photographer about the mirror and the sugar", "The first look in the mirror and the sugar grinding are the two defining images, and both are brief."),
        ],
        "faqs": [
            ("What is on a Persian sofreh aghd?",
             "A mirror and candelabra, honey, flatbread and herbs, decorated eggs and nuts, coins, wild rue, and a book of faith or poetry - each a specific wish for the marriage. The couple sits facing it, traditionally oriented east."),
            ("Why does the Persian bride say no three times?",
             "The officiant asks for her consent three times and she stays silent for the first two, often while a relative jokes that she has gone to pick flowers. She answers on the third. It is a lighthearted set piece that the whole room waits for."),
            ("What is the sugar cone ceremony?",
             "Two happily married women hold a cloth over the couple and grind sugar cones above it throughout the ceremony, showering sweetness onto the marriage. It is one of the most photographed moments in a Persian wedding."),
        ],
    },
    # ---------------------------------------------- South Asian
    "sikh-anand-karaj": {
        "group": "South Asian",
        "question": "What happens at a Sikh wedding ceremony?",
        "short": "Anand Karaj",
        "culture": "Sikh",
        "also": "Sikh wedding, blissful union, laavan",
        "cats": ["wedding-officiants", "wedding-photographers", "wedding-caterers"],
        "related": ["saptapadi", "the-baraat", "mehndi-ceremony"],
        "lede": "Anand Karaj means 'blissful union'. The couple circles the Guru Granth Sahib four times while four hymns, the laavan, are sung — each circuit marking a stage in the journey from worldly attachment to union with the divine. It takes place in a gurdwara, in the morning, with everyone seated on the floor.",
        "sections": [
            ("The four laavan", [
                "Each of the four hymns is read, then sung while the couple walks clockwise around the Guru Granth Sahib, the bride following the groom and holding one end of a scarf he carries. The first laav speaks of duty, the second of longing, the third of detachment, the fourth of union and harmony. The marriage is complete at the end of the fourth.",
                "There are no vows spoken by the couple. The commitment is made by walking the circuits in the presence of the scripture, which serves as the witness - a structure with a clear parallel to the fire in a Hindu ceremony.",
            ]),
            ("What guests should expect", [
                "Heads covered for everyone, shoes removed, and seating on the floor - men and women often on separate sides. No alcohol, tobacco or meat in the gurdwara. Guests should arrive before the ceremony begins and not walk in front of the Guru Granth Sahib.",
                "The ceremony usually runs an hour to ninety minutes and is followed by langar, the free communal meal served to everyone present regardless of faith, eaten sitting on the floor together.",
            ]),
        ],
        "planning": [
            ("Confirm the gurdwara's own rules first", "Photography restrictions, dress requirements and timing are set by the gurdwara, not by you. Ask before booking any vendor."),
            ("Tell your photographer about floor seating and head covering", "They will be working from the floor, covered, and often restricted in where they may stand. This changes lens choice and position."),
            ("Plan the day around a morning ceremony", "Anand Karaj is traditionally held in the morning, which shifts the entire timeline earlier than most weddings."),
            ("Coordinate langar with any separate reception catering", "Langar is served at the gurdwara. An evening reception is a separate meal and a separate caterer."),
        ],
        "faqs": [
            ("What are the four laavan?",
             "The four hymns sung during a Sikh wedding while the couple circles the Guru Granth Sahib. They describe duty, longing, detachment and finally union and harmony. The marriage is complete at the end of the fourth circuit."),
            ("Do Sikh couples say vows?",
             "Not spoken vows. The commitment is made by walking the four circuits in the presence of the Guru Granth Sahib, which acts as the witness to the marriage."),
            ("What should guests wear to a Sikh wedding?",
             "Modest dress with heads covered - scarves are usually provided at the gurdwara - and shoes removed. Seating is on the floor, and guests should avoid walking in front of the Guru Granth Sahib."),
        ],
    },
    "indian-sangeet": {
        "group": "South Asian",
        "question": "What is a sangeet?",
        "short": "The sangeet",
        "culture": "South Asian",
        "also": "sangeet ceremony, music night",
        "cats": ["wedding-djs", "wedding-bands", "wedding-venues"],
        "related": ["mehndi-ceremony", "haldi-ceremony", "the-baraat"],
        "lede": "The sangeet is the music and dance night before a South Asian wedding, and at many weddings it is the event people enjoy most. Both families perform — choreographed numbers rehearsed for weeks, often competitively — and it is where two sets of relatives who have never met stop being strangers.",
        "sections": [
            ("What actually happens", [
                "A hosted evening of performances: the bride's side and the groom's side each present dances, usually to Bollywood numbers, frequently with a friendly rivalry about who has rehearsed harder. Parents, siblings, cousins and occasionally grandparents take part. The couple often performs together.",
                "Between performances there is dinner, a DJ, and open dancing. The evening runs long, and unlike the wedding itself it has no ritual obligations - which is precisely why it is the one everyone relaxes at.",
            ]),
            ("Scale, and how it has grown", [
                "Historically an intimate evening of women singing traditional songs with a dholki drum. Today, at large weddings, it is a produced event with a stage, a sound system, lighting, a choreographer and rehearsals that start months out.",
                "Both versions are valid, and the smaller one is having a revival among couples who want something less like a show. What matters is deciding which you are hosting before you book a venue for it.",
            ]),
        ],
        "planning": [
            ("Book a DJ who has run a sangeet", "Performance tracks, cues, mic changes and a running order of a dozen acts is a different job from a reception. Ask specifically."),
            ("Confirm the venue has a stage and rehearsal access", "Performers need to run their piece in the space. A sangeet in a room with no stage and no soundcheck is a difficult night."),
            ("Send the DJ every track, edited, a week out", "Choreographed numbers are cut to a specific edit. The wrong version is a ruined performance somebody rehearsed for a month."),
            ("Allow more time than you think", "A dozen performances with introductions runs well over an hour. Build the dinner around it rather than into it."),
        ],
        "faqs": [
            ("What happens at a sangeet?",
             "Both families perform choreographed dances - usually to Bollywood music and often competitively - interspersed with dinner and open dancing. It is held before the wedding and is frequently the most enjoyed event of the week."),
            ("Who performs at a sangeet?",
             "Both sides: parents, siblings, cousins, friends and often the couple themselves. Groups rehearse for weeks, and at larger weddings a choreographer is hired months in advance."),
            ("How is a sangeet different from a mehndi?",
             "A mehndi is the henna ceremony, focused on the bride having intricate designs applied over several hours. A sangeet is a music and dance night with performances from both families. Some families combine them into one evening."),
        ],
    },
    # ---------------------------------------------- East & Southeast Asian
    "chinese-door-games": {
        "group": "East Asian",
        "question": "What are Chinese wedding door games?",
        "short": "Door games",
        "culture": "Chinese",
        "also": "chuangmen, gatecrashing, door blocking",
        "cats": ["wedding-photographers", "wedding-videographers", "wedding-planners"],
        "related": ["chinese-tea-ceremony", "korean-paebaek", "the-baraat"],
        "lede": "Before a Chinese groom can collect his bride, her friends barricade the door and make him earn his way in — through dares, quizzes about her, physical challenges, and ultimately red envelopes passed under the door. It is staged, it is loud, and it is one of the funniest hours of any wedding.",
        "sections": [
            ("How it is played", [
                "The bridesmaids set the challenges and the groomsmen have to complete them: eating something sour, doing press-ups, singing, answering questions about the bride that the groom really ought to know, or performing something embarrassing on video. Negotiation happens through the closed door, and red envelopes of money are the accepted currency for skipping a challenge.",
                "It ends when the door opens and the groom reaches the bride, usually to find her shoe hidden somewhere as one final task. The whole thing typically runs 30 to 60 minutes.",
            ]),
            ("Why it matters beyond the comedy", [
                "The framing is that the groom must demonstrate he will work for her, in front of the people who love her most, and that her friends are the ones deciding whether he has. Underneath the games it is a small negotiation between two groups of people who are about to become one family.",
                "It also loosens everyone up at the start of a long formal day, which is a structural function several cultures solve in different ways.",
            ]),
        ],
        "planning": [
            ("Tell your photographer and videographer it is happening", "It is fast, crowded, indoors and in a corridor. They need to know the location and to be inside before the door closes."),
            ("Build an hour into the timeline", "Door games routinely overrun, and everything after them - tea ceremony, ceremony, photographs - shifts with it."),
            ("Agree a floor on the red envelopes in advance", "The negotiation is theatre, but somebody has to have prepared envelopes. The couple should brief both sides on the scale."),
            ("Check the venue or building allows it", "Hotel corridors and apartment lobbies get loud. If it is happening at a hotel, tell them."),
        ],
        "faqs": [
            ("What are door games at a Chinese wedding?",
             "Challenges set by the bridesmaids that the groom and his groomsmen must complete before they are allowed in to collect the bride - dares, quizzes about her, physical tasks - with red envelopes accepted for skipping one. It usually runs 30 to 60 minutes."),
            ("How much money goes in the door game red envelopes?",
             "It varies enormously by family and region, and the amounts are symbolic rather than substantial. The couple should brief both sides on the expected scale so nobody arrives unprepared."),
            ("How long do Chinese door games take?",
             "Typically 30 to 60 minutes, and they routinely overrun. Build an hour into the timeline, because the tea ceremony and everything after it shifts with them."),
        ],
    },
    "vietnamese-tea-ceremony": {
        "group": "Southeast Asian",
        "question": "What happens at a Vietnamese wedding ceremony?",
        "short": "Vietnamese wedding traditions",
        "culture": "Vietnamese",
        "also": "le gia tien, dam hoi, Vietnamese tea ceremony",
        "cats": ["wedding-officiants", "wedding-photographers", "wedding-rentals"],
        "related": ["chinese-tea-ceremony", "korean-paebaek", "the-baraat"],
        "lede": "A Vietnamese wedding centres on le gia tien — the ceremony before the ancestral altar, held at each family's home. The groom's family arrives in procession carrying red lacquered boxes of gifts, and the couple asks permission of the ancestors before serving tea to the living elders.",
        "sections": [
            ("The procession and the boxes", [
                "The groom's family arrives in a formal order, carrying an odd number of red lacquered boxes covered in red cloth - traditionally containing betel leaves and areca nuts, tea, wine, roast pig, sticky rice and fruit. Unmarried members of each family hand them across in a line, receiving lucky money in return.",
                "The number of boxes is significant and varies by region: odd numbers in the north, often six in the south. Families agree the count in advance, and it is a genuine point of etiquette rather than decoration.",
            ]),
            ("Before the ancestors, then the elders", [
                "The couple lights incense at the family altar and bows to the ancestors, asking permission and announcing the marriage. Only then do they serve tea to the living elders, who offer blessings and give jewellery or red envelopes in return.",
                "The ao dai - the long silk tunic, usually red for the bride, often with a khan dong headpiece - is worn for this part of the day. Many couples change into Western dress for an evening reception.",
            ]),
        ],
        "planning": [
            ("Confirm the box count between families early", "It varies by region and is a real etiquette point. Agreeing it is a conversation between the two families, not a detail."),
            ("Allow travel time between two homes", "Le gia tien traditionally happens at both families' houses. That is two ceremonies and a journey, and it shapes the whole morning."),
            ("Tell your photographer about the altar and the incense", "Interior, low light, incense smoke, and a sequence of bows that happens once. They should know the order beforehand."),
            ("Plan the ao dai change into the timeline", "Changing into and out of an ao dai with a headpiece takes real time, and many couples do it more than once."),
        ],
        "faqs": [
            ("What is le gia tien?",
             "The Vietnamese ancestral ceremony, held at the family home before the altar. The couple lights incense, bows and asks the ancestors' permission to marry, then serves tea to the living elders, who give blessings and gifts in return."),
            ("What is in the red boxes at a Vietnamese wedding?",
             "Traditionally betel leaves and areca nuts, tea, wine, roast pig, sticky rice and fruit, carried by the groom's family in an odd number of red lacquered boxes. The count varies by region and is agreed between the families in advance."),
            ("What does a Vietnamese bride wear?",
             "An ao dai, the long silk tunic, usually red for the ceremony and often with a khan dong headpiece. Many couples change into Western attire for an evening reception."),
        ],
    },
    "hmong-wedding-traditions": {
        "group": "Southeast Asian",
        "question": "What are Hmong wedding traditions?",
        "short": "Hmong wedding traditions",
        "culture": "Hmong",
        "also": "Hmong wedding negotiation, mej koob",
        "cats": ["wedding-officiants", "wedding-caterers", "wedding-photographers"],
        "related": ["vietnamese-tea-ceremony", "chinese-tea-ceremony", "las-arras"],
        "lede": "A Hmong wedding is a negotiation between two clans, conducted by appointed spokesmen called mej koob who speak on the families' behalf across two or three days. Very little of it looks like a Western wedding, and almost all of the important work happens in conversation rather than ceremony.",
        "sections": [
            ("The mej koob and the negotiation", [
                "Each family appoints a mej koob - a skilled, respected negotiator who knows the protocols, the songs and the order of the ritual. They conduct the discussions: the terms, the bride price, the obligations each clan takes on, and the formal acceptance of the bride into the groom's clan.",
                "This is not a formality. The mej koob are genuinely negotiating on behalf of two lineages, and a good one is sought after. The proceedings include ritual songs and a precise etiquette of who speaks, when, and over what.",
            ]),
            ("Across the days", [
                "The events move between the two households over two or three days, with formal meals at each, the presentation of the bride to the groom's ancestors, and a series of ceremonial cups. Clan identity is central throughout - marriage moves a woman from her father's clan into her husband's, and much of the ritual marks that transfer.",
                "Many Hmong American couples now hold the traditional events across a weekend and a Western-style reception separately, which is a practical adaptation rather than a dilution.",
            ]),
        ],
        "planning": [
            ("Let the elders lead the traditional portion", "The protocols are held by the mej koob and the older generation. This is one tradition where the couple's job is largely to be guided."),
            ("Plan catering for multiple days and both households", "Formal meals at each home across two or three days is a substantial catering commitment that no single reception quote covers."),
            ("Brief your photographer that it is conversational", "Most of the significant moments are people seated and talking, not staged ritual. A photographer expecting a ceremony will miss the day."),
            ("Decide early whether you are also having a Western reception", "Many couples do. It is a separate event with a separate budget and timeline."),
        ],
        "faqs": [
            ("What is a mej koob?",
             "An appointed spokesman who conducts the wedding negotiation on a family's behalf at a Hmong wedding. Each side has one, and they handle the terms, the protocols and the ritual songs. A skilled mej koob is highly sought after."),
            ("How long does a Hmong wedding last?",
             "Traditionally two or three days, with events moving between the two households and formal meals at each. Many Hmong American couples now hold the traditional events across a weekend with a separate Western-style reception."),
            ("What is the Hmong bride price?",
             "A negotiated payment from the groom's clan to the bride's, agreed by the mej koob as part of the formal discussions. It recognises the family's raising of the bride and marks her movement between clans."),
        ],
    },
    # ---------------------------------------------- African
    "nigerian-traditional-wedding": {
        "group": "African",
        "question": "What happens at a Nigerian traditional wedding?",
        "short": "Nigerian traditional wedding",
        "culture": "Nigerian",
        "also": "introduction ceremony, igba nkwu, Yoruba engagement",
        "cats": ["wedding-caterers", "wedding-djs", "wedding-photographers"],
        "related": ["ethiopian-wedding-traditions", "jumping-the-broom", "the-money-dance"],
        "lede": "A Nigerian traditional wedding is a separate, full-scale event from the white wedding, usually held days or weeks before it — and for many families it is the one that counts. The specifics differ sharply between Yoruba, Igbo, Hausa and other groups, but all of them are family-to-family, colour-coordinated and very large.",
        "sections": [
            ("Yoruba and Igbo, briefly", [
                "At a Yoruba engagement, the groom's family formally asks for the bride through an alaga - a hired MC who runs the proceedings with humour and holds both families to protocol. The groom prostrates before her parents, gifts are presented and a letter of proposal is read aloud and answered.",
                "At an Igbo igba nkwu, the wine-carrying ceremony, the bride is given a cup of palm wine and must find her groom in the crowd - who is often deliberately hidden - and offer it to him. Drinking it in front of everyone is the moment the marriage is recognised.",
            ]),
            ("Aso ebi, and the scale", [
                "Guests wear aso ebi, a chosen fabric that the family selects and sells to attendees, so the room reads as colour-coordinated groups. Choosing the fabric and distributing it is a real planning task that starts months out.",
                "Guest counts run large - several hundred is ordinary - and spraying money over the dancing couple is standard. Both facts should shape your venue and catering decisions from the beginning rather than being discovered late.",
            ]),
        ],
        "planning": [
            ("Book a caterer who has cooked at this scale", "Several hundred guests, specific dishes, and often service across a long day. This is not a standard wedding catering brief."),
            ("Start aso ebi fabric months ahead", "Selecting, ordering and distributing fabric to hundreds of guests takes time and coordination, and guests need it before they can have outfits made."),
            ("Hire an alaga or MC who knows the protocols", "For a Yoruba ceremony especially, the alaga runs the event. This is a specialist role, not a generic MC booking."),
            ("Tell your venue about money spraying", "Some venues object to cash on the floor, and somebody has to collect it. Agree the arrangement in advance."),
        ],
        "faqs": [
            ("What is the difference between a Nigerian traditional wedding and a white wedding?",
             "They are two separate events. The traditional wedding is the family-to-family ceremony - Yoruba engagement, Igbo igba nkwu and so on - usually held days or weeks before the church or civil white wedding. For many families the traditional one is the one that counts."),
            ("What is aso ebi?",
             "A fabric chosen by the family and bought by guests so that groups at the wedding are colour-coordinated. Selecting and distributing it starts months ahead, because guests need time to have outfits made."),
            ("What is igba nkwu?",
             "The Igbo wine-carrying ceremony. The bride is given a cup of palm wine and must find her groom among the guests, who is often deliberately hidden, and offer it to him. His drinking it publicly marks the marriage."),
        ],
    },
    "ethiopian-wedding-traditions": {
        "group": "African",
        "question": "What are Ethiopian wedding traditions?",
        "short": "Ethiopian wedding traditions",
        "culture": "Ethiopian & Eritrean",
        "also": "telosh, melse, kelekel, Habesha wedding",
        "cats": ["wedding-caterers", "wedding-bands", "wedding-photographers"],
        "related": ["nigerian-traditional-wedding", "chinese-tea-ceremony", "greek-stefana"],
        "lede": "An Ethiopian wedding runs across several days and several distinct events: the shimagle asking on the family's behalf, the telosh when the groom's party comes to collect the bride, the wedding itself, and the melse and kelekel celebrations that follow it in traditional dress.",
        "sections": [
            ("The days, in order", [
                "First the shimagle - respected elders sent by the groom's family to formally ask the bride's family for the marriage. Then the telosh, when the groom arrives with his party, singing, to collect her; her family and friends make him wait and negotiate at the door before letting him through.",
                "After the wedding day come the melse and kelekel, held on following days, where the couple wears traditional habesha kemis and the celebrations are more informal, more musical and often more enjoyed than the wedding itself.",
            ]),
            ("Coffee, injera and the dancing", [
                "The coffee ceremony - green beans roasted, ground and brewed in a jebena in front of guests, served three times - appears throughout, and it is a genuine ceremony rather than a refreshment.",
                "Food is served on shared injera, eaten by hand from a common platter, which has real implications for how you seat and serve a large room. Eskista, the shoulder dancing, runs through the music and needs a floor and a band or DJ who knows the repertoire.",
            ]),
        ],
        "planning": [
            ("Budget for several events, not one", "Telosh, wedding, melse and kelekel are separate occasions with separate catering, outfits and often venues."),
            ("Find a caterer who serves injera properly at scale", "Shared platters change table layout, service style and staffing. A caterer who has not done it will get the logistics wrong."),
            ("Allow room and time for the coffee ceremony", "It is performed, not poured, and it needs space, a brazier and someone who knows the ritual."),
            ("Book musicians who know eskista and the repertoire", "A generic DJ will not carry the dancing. Ask specifically what they have played."),
        ],
        "faqs": [
            ("How long is an Ethiopian wedding?",
             "Several days. The shimagle asking comes first, then the telosh collection, then the wedding, then the melse and kelekel celebrations on following days in traditional dress."),
            ("What is telosh?",
             "The event where the groom and his party come singing to collect the bride from her family's home. Her friends and family block the way and negotiate before letting him through - a set piece that is played for fun."),
            ("What is an Ethiopian coffee ceremony?",
             "Green beans roasted, ground and brewed in a jebena in front of guests and served in three rounds. It is a performed ritual rather than a drinks service, and it needs space and someone who knows it."),
        ],
    },
    # ---------------------------------------------- Eastern European
    "polish-oczepiny": {
        "group": "Eastern European",
        "question": "What is oczepiny at a Polish wedding?",
        "short": "Oczepiny",
        "culture": "Polish",
        "also": "the unveiling, capping ceremony, Polish midnight games",
        "cats": ["wedding-djs", "wedding-bands", "wedding-venues"],
        "related": ["russian-bread-and-salt", "the-money-dance", "la-vibora-de-la-mar"],
        "lede": "At midnight, the bride's veil is removed and replaced with a cap — historically the mark of moving from maiden to married woman — and the party shifts into games. Modern oczepiny is mostly the games: the veil and tie are thrown, couples are paired off, and the reception restarts and runs until dawn.",
        "sections": [
            ("The unveiling", [
                "Traditionally the married women of the family gathered around the bride, removed her veil and placed a cap on her head while singing. It marked a change of status in a community where that status was publicly legible.",
                "Today most couples keep the gesture and lighten the meaning: the veil comes off at midnight, often with the bride's mother or grandmother doing it, and the room applauds a moment that used to be solemn.",
            ]),
            ("Midnight games, and what they are for", [
                "The veil is thrown to the unmarried women and the groom's tie to the unmarried men, and the two who catch them dance together. Then come the games - relay races, blindfolded tasks, contests between the couple - run by the band or an MC.",
                "The function is structural. A Polish reception runs until four or five in the morning, and oczepiny at midnight is the reset that carries the room through the second half of the night. It is the same job La Hora Loca does at a Latin American wedding.",
            ]),
        ],
        "planning": [
            ("Tell your band or DJ you want oczepiny and when", "They run it. A band that has done Polish weddings has a repertoire of games and the patter to go with it; one that has not will need briefing."),
            ("Check your venue's end time before planning a midnight event", "A reception with a midnight reset needs to run to three or four. Many venues will not, and that is a booking decision not a day-of one."),
            ("Plan food for the second half of the night", "Polish receptions serve a late supper. A caterer packing up at eleven leaves a room dancing until four with nothing to eat."),
            ("Warn your photographer the night has two halves", "Standard eight-hour coverage ends before oczepiny even starts."),
        ],
        "faqs": [
            ("What is oczepiny?",
             "The Polish midnight ceremony where the bride's veil is removed and replaced with a cap, marking her change of status, followed by games run by the band or MC. It resets the energy of a reception that will run until dawn."),
            ("When does oczepiny happen?",
             "At midnight, roughly halfway through a Polish reception. It exists to carry the room through a night that traditionally continues until four or five in the morning."),
            ("What games are played at a Polish wedding?",
             "The veil and tie are thrown to unmarried guests who then dance together, followed by relay races, blindfolded tasks and contests between the couple. The band or an MC runs them."),
        ],
    },
    "russian-bread-and-salt": {
        "group": "Eastern European",
        "question": "What is the bread and salt wedding tradition?",
        "short": "Bread and salt",
        "culture": "Russian, Ukrainian & Slavic",
        "also": "karavai, khleb-sol, welcoming bread",
        "cats": ["wedding-officiants", "wedding-cakes", "wedding-photographers"],
        "related": ["ukrainian-rushnyk", "polish-oczepiny", "greek-stefana"],
        "lede": "The couple's parents meet them with a decorated round loaf, the karavai, and a dish of salt. Each takes a bite without using their hands, and whoever takes the bigger bite is said to be the head of the household — which is why it is usually the funniest thirty seconds of a Slavic wedding.",
        "sections": [
            ("What it means", [
                "Bread is prosperity and salt is the hardship that comes with any life together. Offering both to a guest is the oldest gesture of hospitality in Slavic culture, and offering it to a newly married couple is the family welcoming them into their own home.",
                "The bigger-bite game is a modern addition to a much older ritual. Some families instead have the couple salt each other's piece, which is a promise to share the difficulty as well as the plenty.",
            ]),
            ("The karavai itself", [
                "The loaf is elaborately decorated with braided dough, birds, wheat and flowers, each element carrying meaning - wheat for prosperity, intertwined rings for the marriage. It is traditionally baked by a happily married woman in the family.",
                "It is a specialist bake, not a bread order. Bakeries in Slavic communities make them; elsewhere it is worth asking your wedding cake baker well in advance, or asking a relative.",
            ]),
        ],
        "planning": [
            ("Order the karavai months ahead", "It is a decorated ceremonial loaf, not a bread order. Find a baker who has made one, or ask a family member who knows."),
            ("Tell your photographer it happens on arrival", "It takes place as the couple enters the reception, often at the door - a spot photographers do not usually plan to be in."),
            ("Decide the rustnyk or tray in advance", "The loaf is presented on an embroidered cloth. Families often have one, and it belongs in the same conversation."),
            ("Brief whoever is holding it", "Parents present it. They need to know when, where to stand, and what they are saying."),
        ],
        "faqs": [
            ("What does bread and salt mean at a wedding?",
             "Bread represents prosperity and salt the hardship of life together. The couple's parents present both as a welcome into the family, drawing on the oldest gesture of hospitality in Slavic culture."),
            ("Who takes the bigger bite of the karavai?",
             "Whoever manages it is jokingly declared head of the household. It is a modern game attached to a much older ritual, and it is usually the moment the room laughs hardest."),
            ("What is a karavai?",
             "The decorated round loaf used in Slavic wedding ceremonies, braided with dough birds, wheat and flowers. Traditionally baked by a happily married woman in the family, it is a specialist bake that should be ordered well in advance."),
        ],
    },
    "ukrainian-rushnyk": {
        "group": "Eastern European",
        "question": "What is a rushnyk in a Ukrainian wedding?",
        "short": "The rushnyk",
        "culture": "Ukrainian",
        "also": "wedding towel, embroidered cloth, rushnychok",
        "cats": ["wedding-officiants", "wedding-rentals", "wedding-photographers"],
        "related": ["russian-bread-and-salt", "polish-oczepiny", "handfasting"],
        "lede": "A rushnyk is an embroidered ritual cloth, and at a Ukrainian wedding the couple stands on one during the ceremony. Whoever steps onto it first is said to lead the household. The embroidery is not decorative — the patterns are a regional language, and a family's rushnyk is often older than anyone present.",
        "sections": [
            ("Standing on the cloth", [
                "The rushnyk is laid before the altar and the couple steps onto it together to be married. Standing on it marks the ground they will build a life on, and it is one of the few wedding traditions where the object is literally underfoot rather than held or worn.",
                "Several rushnyky appear across a Ukrainian wedding: one to stand on, one to bind the couple's hands, one under the karavai, and others draped over icons. Families frequently own a set, embroidered by a grandmother, used across generations.",
            ]),
            ("Reading the embroidery", [
                "Red and black are the dominant colours - red for love and life, black for grief and the earth. Motifs are regional and specific: roosters, wheat, oak leaves, the tree of life, geometric patterns that identify a village as clearly as an accent would.",
                "A commissioned rushnyk takes months of handwork. Couples without a family one often commission a piece specifically, which makes it one of the few wedding purchases that becomes an heirloom immediately.",
            ]),
        ],
        "planning": [
            ("Ask your family before buying one", "Rushnyky are kept and passed down. There is a reasonable chance one already exists, and using it means considerably more than buying one."),
            ("Commission months ahead if you need one", "Hand embroidery of this kind takes months. It is not a purchase to make in the final weeks."),
            ("Tell your officiant it is part of the ceremony", "Laying the cloth and stepping onto it needs a cue and a moment in the order of service."),
            ("Tell your photographer to shoot low", "The rushnyk is on the floor under the couple, which is not where a camera naturally points during a ceremony."),
        ],
        "faqs": [
            ("What is a rushnyk used for at a wedding?",
             "The couple stands on an embroidered ritual cloth during the ceremony, marking the ground they will build their life on. Other rushnyky bind the couple's hands, sit under the ceremonial bread, and drape over icons."),
            ("What do the rushnyk embroidery patterns mean?",
             "Red represents love and life, black grief and the earth. Motifs - roosters, wheat, oak leaves, the tree of life - are regional and specific enough to identify a village."),
            ("Who steps on the rushnyk first?",
             "Whoever steps on first is traditionally said to lead the household, which gives the moment a competitive edge that families enjoy."),
        ],
    },
    # ---------------------------------------------- European & Celtic
    "scottish-wedding-traditions": {
        "group": "European & Celtic",
        "question": "What are Scottish wedding traditions?",
        "short": "Scottish wedding traditions",
        "culture": "Scottish",
        "also": "quaich, pinning the tartan, Scottish wedding customs",
        "cats": ["wedding-officiants", "wedding-bands", "wedding-invitations"],
        "related": ["handfasting", "irish-wedding-traditions", "greek-stefana"],
        "lede": "Scottish weddings bring the quaich, the pinning of the tartan, handfasting and a ceilidh — and the ceilidh is the one that changes the evening. A caller teaches the room the dances as they go, which means everyone dances, including the people who never dance.",
        "sections": [
            ("The quaich and the tartan", [
                "The quaich is a shallow two-handled cup - the 'cup of friendship' - filled with whisky and drunk from by both partners, each hand on a handle. Two hands each means neither can hold a weapon, which is the old reading, and drinking from one cup is the obvious one. Families often use a quaich that has been used before.",
                "Pinning the tartan is the moment a sash of the groom's clan tartan is pinned onto the bride, formally welcoming her into the family. It is usually done by his mother, and at clan weddings it carries real weight.",
            ]),
            ("The ceilidh", [
                "A ceilidh band plus a caller who explains each dance before it starts. The Gay Gordons, Strip the Willow, the Dashing White Sergeant - nobody is expected to know them, which is exactly why the floor fills.",
                "It changes what a reception is. There is no gap where people stand around waiting for the dancing to get going, because the caller simply starts and everyone is pulled in.",
            ]),
        ],
        "planning": [
            ("Book a ceilidh band with a caller", "The caller is the point. A band without one leaves a room that does not know the steps standing still."),
            ("Check your floor size and surface", "Ceilidh dances move in large circles and lines and need real space. A small dance floor genuinely does not work."),
            ("Ask families about an existing quaich", "Many have one. Using a family quaich is meaningfully different from buying one."),
            ("Tell your venue about whisky in the ceremony", "Some venues restrict alcohol outside licensed service areas, which includes a ceremonial cup."),
        ],
        "faqs": [
            ("What is a quaich ceremony?",
             "Both partners drink whisky from a shallow two-handled cup, each holding a handle. It is the 'cup of friendship', and sharing one cup with both hands occupied is the traditional image of trust between two families."),
            ("What is a ceilidh at a wedding?",
             "Scottish social dancing with a live band and a caller who teaches each dance before it starts. Because nobody is expected to know the steps, the floor fills in a way most wedding receptions never manage."),
            ("What is pinning the tartan?",
             "A sash of the groom's clan tartan is pinned onto the bride, usually by his mother, formally welcoming her into the clan."),
        ],
    },
    "italian-wedding-traditions": {
        "group": "European & Celtic",
        "question": "What are Italian wedding traditions?",
        "short": "Italian wedding traditions",
        "culture": "Italian",
        "also": "la busta, bomboniere, confetti, Italian wedding customs",
        "cats": ["wedding-caterers", "wedding-cakes", "wedding-invitations"],
        "related": ["greek-stefana", "scottish-wedding-traditions", "the-money-dance"],
        "lede": "Italian weddings are organised around food and around two objects: la busta, the envelope of cash guests give in place of a gift, and the bomboniere, the favour the couple gives back. Between them sits a meal considerably longer than most guests expect.",
        "sections": [
            ("La busta and the bomboniere", [
                "Guests give money in an envelope, handed over at the reception, and the amount is understood to at least cover the cost of their seat. The bride often carries a satin bag, la borsa, to collect them.",
                "In return each guest leaves with a bomboniera - a small keepsake with five sugared almonds, confetti, tied in tulle. Five because the number is indivisible, and for health, wealth, happiness, fertility and long life. The almond is bitter and the sugar is sweet, which is the point.",
            ]),
            ("The meal, which is the event", [
                "A traditional Italian wedding meal runs to many courses across several hours: antipasti, a primo of pasta, a secondo of meat or fish, contorni, then dolci, the cake, and often a table of pastries afterwards. Four to five hours at the table is normal.",
                "This shapes everything else. There is less standing-around time, dancing starts later, and the catering brief is entirely different from a plated three-course dinner. Tell your venue and caterer early what you are planning.",
            ]),
        ],
        "planning": [
            ("Tell your caterer how many courses, early", "A five-hour multi-course meal is a different staffing, kitchen and timeline plan from a three-course dinner."),
            ("Order bomboniere with enough lead time", "One per guest or household, often personalised. It is a real order, not an afterthought."),
            ("Plan how la busta is collected and secured", "Envelopes of cash accumulate through the night. Assign one trusted person and somewhere locked."),
            ("Push the dancing later in the timeline", "If dinner runs to four hours, a DJ booked to finish at eleven will have played to a seated room all night."),
        ],
        "faqs": [
            ("What is la busta at an Italian wedding?",
             "An envelope of cash given by guests in place of a gift, handed over at the reception. The amount is generally understood to at least cover the cost of that guest's place at the meal."),
            ("What are bomboniere?",
             "Favours given to each guest, traditionally five sugared almonds - confetti - wrapped in tulle. Five because the number cannot be divided, representing health, wealth, happiness, fertility and long life."),
            ("How long is an Italian wedding meal?",
             "Four to five hours is normal, running through antipasti, a pasta course, a meat or fish course, sides, dessert, cake and often a pastry table. It shapes the whole reception timeline."),
        ],
    },
    "german-polterabend": {
        "group": "European & Celtic",
        "question": "What is a Polterabend?",
        "short": "Polterabend",
        "culture": "German",
        "also": "plate smashing, German pre-wedding party",
        "cats": ["wedding-venues", "wedding-rentals", "day-of-coordination"],
        "related": ["polish-oczepiny", "scottish-wedding-traditions", "italian-wedding-traditions"],
        "lede": "The night before a German wedding, guests smash porcelain outside the couple's home — and the couple sweeps it up together. The noise is meant to drive off bad luck, and the sweeping is the actual point: the first thing they do as a couple is clean up a mess together.",
        "sections": [
            ("What gets broken, and what does not", [
                "Porcelain, crockery, tiles, sinks - anything ceramic. Explicitly not glass, which is considered unlucky, and not mirrors. Guests bring their own chipped plates and old dishes rather than anything new being bought to destroy.",
                "It is loud, informal and held outdoors, usually with beer and food, and there is no dress code or programme. Anyone can come; unlike the wedding it is not really an invitation-only event.",
            ]),
            ("The sweeping", [
                "The couple clears it up together, with a broom and a dustpan, in front of everyone. The symbolism is not subtle and it is the reason the tradition survives: the first shared task of the marriage is tidying up a mess other people made.",
                "Some couples keep a shard. It is also, practically, a lot of broken ceramic to dispose of, which is worth thinking about before it is all over a driveway.",
            ]),
        ],
        "planning": [
            ("Do not let anyone bring glass", "Glass is considered unlucky and is genuinely dangerous underfoot. Say so on the invitation."),
            ("Arrange disposal in advance", "A large quantity of broken ceramic needs a bin and somewhere to take it. This is the part everyone forgets."),
            ("Check with a venue or your neighbours", "It is loud and it is late. If it is not at a private home, the venue has to agree to it."),
            ("Hold it the night before, not on the day", "It is an evening of standing outdoors with beer. Putting it the night before a wedding morning is the tradition, and it is worth respecting the hour it ends."),
        ],
        "faqs": [
            ("What happens at a Polterabend?",
             "Guests smash porcelain and crockery outside the couple's home the night before the wedding, and the couple sweeps it up together. The noise is said to drive off bad luck and the sweeping represents facing tasks together."),
            ("Why can't you break glass at a Polterabend?",
             "Glass is considered unlucky, and mirrors especially so. Only porcelain, crockery and other ceramics are smashed - and guests bring their own old dishes rather than buying anything new."),
            ("Who is invited to a Polterabend?",
             "Traditionally anyone - it is an informal, open evening rather than an invitation-only event, which is part of what distinguishes it from the wedding itself."),
        ],
    },
    "swedish-wedding-traditions": {
        "group": "European & Celtic",
        "question": "What are Swedish wedding traditions?",
        "short": "Swedish wedding traditions",
        "culture": "Swedish & Nordic",
        "also": "toastmaster, three rings, Scandinavian wedding customs",
        "cats": ["wedding-djs", "wedding-caterers", "day-of-coordination"],
        "related": ["german-polterabend", "scottish-wedding-traditions", "italian-wedding-traditions"],
        "lede": "Two things define a Swedish wedding: the toastmaster, who runs an evening of speeches and songs with real authority, and the kissing rule — if either partner leaves the room, the guests queue up to kiss the one who stayed.",
        "sections": [
            ("The toastmästare", [
                "A friend appointed months ahead to run the reception. They collect speech requests in advance, order them, time them, introduce each one, and lead the songs between courses. It is a genuine job with weeks of preparation, and it is an honour to be asked.",
                "Because speeches are managed rather than volunteered, a Swedish reception has many of them and they rarely drag. The toastmaster is the mechanism, and it solves a problem most wedding cultures simply endure.",
            ]),
            ("The kissing rule and the three rings", [
                "If the bride leaves the room, the women queue to kiss the groom. If the groom leaves, the men queue to kiss the bride. Guests enforce it enthusiastically, and it makes leaving the table a decision.",
                "Swedish brides traditionally receive three rings: engagement, wedding, and one for motherhood. Some also place a silver coin from their father in one shoe and a gold coin from their mother in the other, so they never go without.",
            ]),
        ],
        "planning": [
            ("Appoint the toastmaster months ahead", "They need time to gather speeches, build a running order and prepare the songs. Asking them late means the role does not work."),
            ("Tell your DJ or band the toastmaster runs the room", "The two need to coordinate. A DJ who does not know there is a toastmaster will talk over them."),
            ("Plan for a long evening at the table", "Courses interleaved with speeches and songs means dinner runs several hours. Your caterer and venue need to know."),
            ("Brief guests on the kissing rule", "It only works if everyone knows. A line in the programme is enough."),
        ],
        "faqs": [
            ("What does a wedding toastmaster do in Sweden?",
             "They run the entire reception: collecting speech requests in advance, ordering and timing them, introducing each speaker and leading songs between courses. It is a significant role appointed months ahead."),
            ("What is the Swedish wedding kissing tradition?",
             "If the bride leaves the room, the women queue to kiss the groom, and if the groom leaves, the men queue to kiss the bride. Guests enforce it with enthusiasm."),
            ("Why do Swedish brides get three rings?",
             "Traditionally one for the engagement, one for the wedding and one for motherhood. Some brides also carry a silver coin from their father in one shoe and a gold coin from their mother in the other."),
        ],
    },
    # ---------------------------------------------- Latin American additions
    "puerto-rican-wedding-traditions": {
        "group": "Latin American & Spanish",
        "question": "What are Puerto Rican wedding traditions?",
        "short": "Puerto Rican traditions",
        "culture": "Puerto Rican",
        "also": "capias, muñeca, la hora loca",
        "cats": ["wedding-djs", "wedding-bands", "wedding-invitations"],
        "related": ["las-arras", "la-hora-loca", "the-money-dance"],
        "lede": "Two things are distinctly Puerto Rican: the capias, ribbons printed with the couple's names that guests are given as keepsakes, and the muñeca — a doll dressed as the bride, covered in those capias, that sits on the head table and is dismantled through the night.",
        "sections": [
            ("Capias and the muñeca", [
                "Capias are small printed ribbons carrying the couple's names and the date. They are pinned to a bride doll placed at the head table, and during the reception the couple removes them one at a time and pins them to guests as they thank them individually.",
                "It is an efficient piece of social engineering: it gives the couple a reason to reach every guest personally, one at a time, with something to hand over. Many cultures solve the same problem with a money dance or a receiving line.",
            ]),
            ("The rest of the evening", [
                "Las arras and the lazo both appear in Puerto Rican Catholic ceremonies, as they do elsewhere in Latin America. The reception leans heavily on live music - salsa, merengue, bomba and plena - and frequently includes a hora loca in the later hours.",
                "Food tends toward a long buffet or stations rather than a plated dinner, which changes the room's shape: people move and mix rather than staying seated through courses.",
            ]),
        ],
        "planning": [
            ("Order capias with your stationery", "They are printed items, one per guest, and they are usually ordered alongside invitations rather than separately."),
            ("Decide who assembles the muñeca", "Someone has to pin several hundred ribbons onto a doll before the wedding. It is a real task, usually done by family."),
            ("Book musicians who play the repertoire", "Salsa, merengue, bomba and plena are specific. Ask what a band or DJ has actually played, not whether they can."),
            ("Build the capia distribution into the timeline", "Reaching every guest individually takes real time. Treat it like a receiving line rather than assuming it happens between songs."),
        ],
        "faqs": [
            ("What are capias at a Puerto Rican wedding?",
             "Small printed ribbons carrying the couple's names and wedding date, pinned to a bride doll at the head table and then given individually to guests by the couple as they thank them during the reception."),
            ("What is the muñeca at a Puerto Rican wedding?",
             "A doll dressed as the bride, covered in capias, that sits on the head table. The couple removes the ribbons one by one through the evening and pins them on guests."),
            ("Do Puerto Rican weddings use las arras and the lazo?",
             "Yes - both appear in Puerto Rican Catholic ceremonies as they do across Latin America, alongside distinctly Puerto Rican elements like the capias and the muñeca."),
        ],
    },
    "las-cintas-de-torta": {
        "group": "Latin American & Spanish",
        "question": "What is the cake ribbon pull?",
        "short": "Cintas de torta",
        "culture": "Peruvian & Latin American",
        "also": "ribbon pull, cake pull, cintas",
        "cats": ["wedding-cakes", "wedding-photographers", "wedding-djs"],
        "related": ["las-arras", "the-money-dance", "puerto-rican-wedding-traditions"],
        "lede": "Ribbons are baked into the bottom tier of the cake, each tied to a small charm, with exactly one attached to a ring. Single women each take a ribbon and pull at the same time, and whoever draws the ring is said to be next to marry — the bouquet toss, with better photographs and no injuries.",
        "sections": [
            ("How it works", [
                "Charms are tied to ribbons and tucked between the cake layers before frosting, ribbon ends left showing. Before the cake is cut, the single women gather, each takes one, and on a count everyone pulls.",
                "The charms carry meanings that vary by family: a ring for marriage, an anchor for adventure, a heart for love, a coin for wealth, a thimble for independence. Every participant keeps hers, so nobody leaves empty-handed - which is the improvement on a bouquet toss.",
            ]),
            ("Talking to your baker about it", [
                "The charms must be food-safe and wrapped, and the ribbons placed so they pull cleanly without dragging the tier over. A baker who has done it before will handle this without being asked; one who has not needs telling early.",
                "It happens immediately before the cake cutting, which means it is a scheduled moment rather than a spontaneous one, and the cake has to be in position with guests gathered.",
            ]),
        ],
        "planning": [
            ("Tell your baker at the order, not the week before", "Charms must be food-safe and wrapped, and the ribbons set so a pull does not topple the tier. It affects how the cake is built."),
            ("Buy the charms early", "Charm sets are ordered, and you need one per participant plus the ring. Count the likely number generously."),
            ("Schedule it right before the cake cutting", "It needs guests gathered and the cake in place, so it belongs in the running order rather than happening whenever."),
            ("Tell your photographer to shoot the pull, not the cake", "Everyone pulls at once and it is over in a second. The faces are the photograph."),
        ],
        "faqs": [
            ("What is a cake ribbon pull?",
             "Charms on ribbons are baked into the bottom tier of the wedding cake, one of them a ring. Single women each take a ribbon and pull together, and whoever draws the ring is said to marry next. Everyone keeps her charm."),
            ("What do the cake pull charms mean?",
             "Meanings vary by family, but commonly a ring for marriage, an anchor for adventure, a heart for love, a coin for wealth and a thimble for independence."),
            ("How do you get charms into a wedding cake?",
             "Your baker tucks them, food-safe and wrapped, between the layers before frosting with the ribbon ends showing. Tell them when you order, because it affects how the cake is constructed."),
        ],
    },
    # ---------------------------------------------- Jewish addition
    "the-bedeken": {
        "group": "Jewish",
        "question": "What is the bedeken?",
        "short": "The bedeken",
        "culture": "Jewish",
        "also": "badeken, the veiling ceremony",
        "cats": ["wedding-photographers", "wedding-videographers", "wedding-officiants"],
        "related": ["the-chuppah", "breaking-the-glass", "the-ketubah"],
        "lede": "Before the ceremony, the groom is brought to the bride — often carried, singing, by a crowd of men — and lowers the veil over her face himself. It is brief, loud and frequently the most emotional moment of a Jewish wedding, precisely because it happens before anything formal has begun.",
        "sections": [
            ("Why the groom veils her", [
                "The reason usually given is Jacob, who was deceived into marrying Leah because he could not see her face beneath the veil. The groom lowers it himself to confirm he knows exactly who he is marrying.",
                "A second reading holds that veiling her signals he values what cannot be seen over what can. Both are commonly offered, and many officiants say one aloud as it happens.",
            ]),
            ("What it actually looks like", [
                "The bride is seated, often on a decorated chair, surrounded by women. The groom arrives escorted by a singing, dancing crowd of men, reaches her, the two see each other - frequently for the first time that day, and sometimes the first in a week - and he lowers the veil. Fathers and grandfathers often bless her immediately after.",
                "It takes perhaps two minutes. It is chaotic, crowded and completely unstaged, which is why it produces photographs unlike anything else in the day.",
            ]),
        ],
        "planning": [
            ("Tell your photographer exactly where it happens", "Crowded, indoors, fast, with the couple briefly in the middle of a moving crowd. They need a position before it starts, not after."),
            ("Allow time in the schedule", "The procession, the veiling and the blessings that follow take longer than the two minutes it appears to be."),
            ("Tell your videographer about the singing", "The music is live, unamplified and from a moving crowd. Their microphone plan differs from the ceremony's."),
            ("Decide about a first look separately", "If the bedeken is your first sight of each other that day, a first look would change it. Many couples deliberately keep the bedeken as that moment."),
        ],
        "faqs": [
            ("What happens at a bedeken?",
             "The groom is escorted to the seated bride by a singing crowd, sees her, and lowers her veil himself before the ceremony. Fathers and grandfathers often bless her immediately afterwards."),
            ("Why does the groom lower the bride's veil?",
             "The traditional reason recalls Jacob, who was deceived into marrying Leah beneath a veil - so the groom confirms he knows who he is marrying. A second reading is that he values what cannot be seen over what can."),
            ("When does the bedeken happen?",
             "Before the ceremony, usually right after the ketubah signing and immediately before the procession to the chuppah."),
        ],
    },
    # ---------------------------------------------- Indigenous American
    "native-american-blanket-ceremony": {
        "group": "Indigenous American",
        "question": "What is a wedding blanket ceremony?",
        "short": "The blanket ceremony",
        "culture": "Native American",
        "also": "blanket wrapping, wedding vase ceremony",
        "cats": ["wedding-officiants", "wedding-photographers", "wedding-rentals"],
        "related": ["what-is-a-lazo", "handfasting", "unity-candle-ceremony"],
        "lede": "In the blanket ceremony the couple arrives wrapped in separate blue blankets, representing their past and its difficulties. Those are removed and a single white blanket is placed around them both. Practices differ substantially between nations, and this is a tradition to approach through a specific community rather than in general.",
        "sections": [
            ("The blankets, and the vase", [
                "Blue for the life each person has lived, white for the one they are beginning together. Removing the blue and being wrapped in a single white blanket is the visible moment of the marriage, and the white blanket is kept afterwards - frequently displayed in the home for the rest of their lives.",
                "A wedding vase ceremony often accompanies it: a vessel with two spouts and one shared chamber, from which each partner drinks. Two openings, one body of water.",
            ]),
            ("Approaching it respectfully", [
                "There is no single Native American wedding. Cherokee, Navajo, Hopi, Lakota and hundreds of other nations have distinct ceremonies, languages and protocols, and several are not open to outsiders at all. Describing a generic version does a disservice to all of them.",
                "If you have a connection to a specific nation, the ceremony belongs to that community and its elders, and they are who to ask. If you do not, this is one of the clearest cases where borrowing the visible form without the relationship is not the same act as participating in it.",
            ]),
        ],
        "planning": [
            ("Ask the specific community, not the internet", "Protocols, permissions and who may officiate belong to individual nations. This is the whole planning step and it cannot be shortcut."),
            ("Confirm what may be photographed", "Many ceremonies restrict or prohibit photography. Ask before booking a photographer, and brief them precisely."),
            ("Source the blankets through the right channels", "Buying from Native artists and communities rather than a generic supplier matters, and elders will often advise on it."),
            ("Give your officiant the full order of service", "If a traditional practitioner leads it, your coordinator and photographer need briefing from them, not from a guide like this one."),
        ],
        "faqs": [
            ("What does the blanket ceremony symbolise?",
             "The blue blankets represent each person's past and its hardships; the single white blanket wrapped around them both represents the shared life beginning. The white blanket is kept and often displayed at home afterwards."),
            ("What is a wedding vase ceremony?",
             "A vessel with two spouts and one shared chamber, from which each partner drinks - two openings drawing from one body of water. It frequently accompanies the blanket ceremony."),
            ("Is it appropriate to include a Native American ceremony in our wedding?",
             "Only through a genuine connection to a specific nation and with that community's guidance. There is no generic Native American wedding - hundreds of nations have distinct ceremonies, some closed to outsiders - so the question belongs to the community's elders, not to a guide."),
        ],
    },
    # ---------------------------------------------- Faith
    "buddhist-wedding-traditions": {
        "group": "East Asian",
        "question": "What happens at a Buddhist wedding?",
        "short": "Buddhist weddings",
        "culture": "Buddhist",
        "also": "Buddhist blessing ceremony, sai sin, water blessing",
        "cats": ["wedding-officiants", "wedding-venues", "wedding-photographers"],
        "related": ["chinese-tea-ceremony", "saptapadi", "vietnamese-tea-ceremony"],
        "lede": "Buddhism does not treat marriage as a religious sacrament, so there is no required Buddhist wedding ceremony. What happens instead is a blessing: monks chant, the couple makes offerings, and the marriage is recognised as a commitment the couple makes to each other rather than a status conferred on them.",
        "sections": [
            ("What a blessing looks like", [
                "Monks - traditionally an odd number - chant sutras while the couple kneels before a shrine, offering candles, incense and flowers. In Thai and Cambodian practice a single cotton thread, sai sin, is looped around the couple's heads or wrists, linking them to each other and to the blessing.",
                "Water is poured over the couple's hands from a conch shell or vessel, by monks and then by family members in turn, each offering a wish. Guests frequently participate, which makes it one of the more inclusive ceremony structures.",
            ]),
            ("Combining it with a legal ceremony", [
                "Because the blessing is not itself a legal marriage in most countries, couples typically pair it with a civil ceremony - often at a registry office beforehand, sometimes on the same day with a separate officiant.",
                "Monks generally cannot accept money directly. Offerings to the temple are the usual arrangement, and the temple will explain what is customary. Ask rather than guessing.",
            ]),
        ],
        "planning": [
            ("Ask the temple what is customary, including offerings", "Monks typically do not take payment directly. The temple will tell you the expected form, and this is not something to improvise."),
            ("Arrange the legal marriage separately", "A blessing is generally not a legal ceremony. Sort the civil side and confirm who signs and files."),
            ("Confirm timing with the temple", "Ceremonies are frequently held in the morning, and monks' schedules are fixed. Your day is built around their availability."),
            ("Check photography rules and dress requirements", "Shoes off, shoulders covered, and restrictions on where a photographer may stand or point a camera are common."),
        ],
        "faqs": [
            ("Is a Buddhist wedding a religious ceremony?",
             "Buddhism does not treat marriage as a sacrament, so there is no required religious wedding. What takes place is a blessing - monks chanting, offerings, and water poured over the couple's hands - alongside a separate civil marriage."),
            ("What is sai sin?",
             "A white cotton thread looped around the couple's heads or wrists in Thai and Cambodian practice, connecting them to each other and to the blessing being given."),
            ("Do you pay monks for a Buddhist wedding?",
             "Monks generally cannot accept money directly. An offering to the temple is the usual arrangement, and the temple will explain what is customary - ask rather than assuming."),
        ],
    },
}
