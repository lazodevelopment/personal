"""Wedding planning guides.  JC-LAZO-PLAN-0917-001

/planning/ and /planning/<slug>/. The fourth content cluster, and the most
competitive material on the internet - every wedding site has a vows page. Two
rules keep these worth publishing.

FIRST, they must not duplicate our own four existing clusters:
    /cost/          per-category pricing AND the whole-budget breakdown
    /when-to-book/  booking lead times, months out
    /questions/     what to ask vendors (134 questions)
    /traditions/    25 ceremony rituals
So: no budget page, no booking-timeline page, no vendor-question page, and
nothing about the meaning of a ceremony ritual. /planning/wedding-day-timeline/
is about the day itself, which is a different question from when to book.

SECOND, every page has to say something the generic version does not. The test
applied while writing: would a couple who has read three other wedding sites
learn anything here? If the answer is no, the page is padding and should not
exist. Concretely that means naming the thing that actually goes wrong - the
receiving line nobody budgeted twenty minutes for, the marriage licence that
expires before the wedding, the speech that runs eleven minutes.

`practical` is the marketplace half: the specific thing to tell a vendor, and
which vendor. That is what makes these pages ours rather than a blog.

Schema per guide:
  question  the search itself, used as h1 and title
  short     display name for cards and cross-links
  group     hub section heading (small fixed set)
  lede      the direct answer, first paragraph
  sections  [(h2, [paragraph, ...])]
  practical [(what to do, why)] - vendor-facing where possible
  faqs      [(q, a)] rendered as FAQPage schema
  cats      taxonomy slugs for the vendor rail
  related   sibling slugs; "when-to-book" / "cost" / "questions" allowed
"""

PLANNING = {
    # ------------------------------------------------------------ the day itself
    "wedding-day-timeline": {
        "question": "What does a wedding day timeline look like?",
        "short": "The wedding day timeline",
        "group": "The day itself",
        "cats": ["day-of-coordination", "wedding-photographers", "wedding-planners"],
        "related": ["ceremony-order", "reception-order", "wedding-emergency-kit"],
        "lede": "A wedding day timeline is built backwards, not forwards. You fix the ceremony time, work back from it to find when hair and makeup must start, then forward from it through photographs, cocktail hour and dinner. Almost every wedding that runs late does so because it was planned in the other direction.",
        "sections": [
            ("Work backwards from the ceremony", [
                "Start at the ceremony time and subtract. Photographs before the ceremony need 60 to 90 minutes. Getting into the dress needs 30. Hair and makeup needs 45 to 75 minutes per service, and with a party of six that is most of a morning. Travel between locations needs whatever the map says plus twenty minutes, because a wedding party does not move at the speed of one person.",
                "Do this arithmetic honestly and you will usually find the morning starts earlier than anyone expected. That is the useful output. The alternative is discovering it on the day.",
            ]),
            ("The three places time disappears", [
                "<strong>Family photographs.</strong> Budget twenty minutes and a written list, and appoint someone loud to gather people. Without a list this takes forty-five minutes and eats your cocktail hour.",
                "<strong>The receiving line.</strong> Roughly ten seconds per guest if it moves well, which at 140 guests is twenty-five minutes. Most couples never schedule it at all and simply lose that time from dinner.",
                "<strong>Travel and transitions.</strong> Getting 140 people from a ceremony to a reception across town takes far longer than moving one car. If the venues are separate, this is the single biggest risk in your day.",
            ]),
            ("Build in slack, in specific places", [
                "Fifteen minutes of buffer before the ceremony and fifteen before dinner service absorbs almost everything that goes wrong. Slack spread thinly across the day disappears; slack in two named blocks survives.",
                "Give the timeline to every vendor at least a week out, not on the morning. Your photographer, DJ, caterer and coordinator each need to know when the others are doing things, and that coordination is most of what a day-of coordinator is for.",
            ]),
        ],
        "practical": [
            ("Have your coordinator build it, not you", "Building a timeline requires knowing how long real things take. This is the core of what day-of coordination buys, and it is why the cheapest planning tier is the one couples least regret."),
            ("Send it to every vendor a week ahead", "Each vendor plans their own day around it. A timeline distributed on the morning is a timeline nobody has read."),
            ("Ask your photographer for their version", "Photographers run the first half of most weddings and know exactly how long the photographs you want will take. Their input is free and usually corrects your estimate."),
            ("Decide about a first look early", "A first look moves most photography before the ceremony and typically returns an hour of cocktail hour to you. It changes the whole shape of the day, so decide before anything else is scheduled."),
        ],
        "faqs": [
            ("How do you make a wedding day timeline?",
             "Work backwards from the ceremony time. Subtract 60-90 minutes for pre-ceremony photographs, 30 to get into the dress, and 45-75 minutes per hair and makeup service. Then work forwards through photographs, cocktail hour and dinner, adding fifteen minutes of buffer before the ceremony and before dinner."),
            ("How long should a wedding day be?",
             "Most run eight to ten hours from the start of hair and makeup to the last dance. The ceremony itself is typically 20-45 minutes; the reception four to five hours. Two venues rather than one adds an hour of transitions."),
            ("What makes a wedding run late?",
             "Three things, reliably: family photographs without a written list, a receiving line nobody scheduled, and moving guests between two venues. Each costs 20-45 minutes and each is entirely predictable in advance."),
        ],
    },
    "ceremony-order": {
        "question": "What is the order of a wedding ceremony?",
        "short": "The ceremony order",
        "group": "The day itself",
        "cats": ["wedding-officiants", "wedding-photographers", "wedding-djs"],
        "related": ["wedding-day-timeline", "writing-your-own-vows", "reception-order"],
        "lede": "Most wedding ceremonies follow the same seven beats: processional, welcome, readings, vows, rings, pronouncement, recessional. Everything else is inserted between those, and the whole thing usually takes 20 to 30 minutes unless a religious liturgy or several traditions extend it.",
        "sections": [
            ("The standard sequence", [
                "The processional seats family, then brings in the wedding party and the person or people walking the aisle. The officiant welcomes everyone and usually says why they are there. Readings follow, then the vows, then the exchange of rings. The officiant pronounces the couple married, they kiss, and the recessional takes everyone back out.",
                "Where traditions are included - a lazo, las arras, a veil ceremony, handfasting, a unity candle - they almost always sit after the vows and rings and before the pronouncement. Your officiant places them in the order of service, and they add time.",
            ]),
            ("Who walks in, and in what order", [
                "The convention is officiant first, then the partner not walking the aisle with their party, then the other party, then flower children and ring bearers, then the person walking the aisle with whoever is escorting them. Guests stand for that last entrance.",
                "None of this is fixed. Couples walk in together, are escorted by both parents, walk alone, or skip the processional entirely. The only genuine requirement is that everyone knows where to stand when the music stops, which is what the rehearsal is for.",
            ]),
            ("How long it actually takes", [
                "A civil ceremony with no readings can be twelve minutes. A standard ceremony with two readings and personal vows is 25 to 30. A full Catholic Mass is an hour or more, and a Filipino Catholic ceremony with candle, veil and cord ceremonies frequently exceeds that.",
                "Tell your photographer and your caterer the honest estimate, because your cocktail hour, sunset photographs and dinner service are all scheduled off it.",
            ]),
        ],
        "practical": [
            ("Get the written order of service from your officiant", "Your coordinator, photographer, videographer and musicians all work from it. An officiant who cannot produce one a fortnight ahead has not written your ceremony yet."),
            ("Rehearse the processional with the actual people", "The rehearsal exists for this. Who walks with whom, how fast, where they stop, which side they stand on - it is ten minutes of work that prevents the most visible kind of confusion."),
            ("Tell your musicians how long the aisle is", "Processional music has to stretch or stop cleanly. A DJ or string trio who has seen the space can time it; one who has not will fade out awkwardly."),
            ("Name someone to cue the start", "Somebody has to tell the musicians the doors are opening. Unassigned, this falls to whoever is nearest, and it is how ceremonies start four minutes late for no reason."),
        ],
        "faqs": [
            ("What is the order of events in a wedding ceremony?",
             "Processional, welcome, readings, vows, ring exchange, pronouncement and kiss, recessional. Cultural traditions such as a lazo, las arras or handfasting are usually inserted after the rings and before the pronouncement."),
            ("How long is a wedding ceremony?",
             "Typically 20 to 30 minutes for a standard ceremony with readings and personal vows. A civil ceremony can be twelve minutes; a full Catholic Mass an hour or more. Give your vendors the honest number, because the rest of the day is scheduled off it."),
            ("Who walks down the aisle first?",
             "Conventionally the officiant, then the wedding party, then children, then whoever is walking the aisle last with their escort. There is no rule - couples walk in together, with both parents, or alone - but everyone needs to know the plan before the rehearsal."),
        ],
    },
    "reception-order": {
        "question": "What is the order of events at a wedding reception?",
        "short": "The reception order",
        "group": "The day itself",
        "cats": ["wedding-djs", "wedding-caterers", "day-of-coordination"],
        "related": ["wedding-day-timeline", "wedding-speeches", "first-dance"],
        "lede": "A reception has a shape: entrance, dinner, speeches, first dances, then the floor opens. The sequence matters more than the timings, because each item is either feeding energy into the night or draining it, and the classic mistake is putting three speeches between dinner and dancing.",
        "sections": [
            ("The usual running order", [
                "Cocktail hour while the couple finishes photographs. Guests are seated. The wedding party and couple are announced in. Welcome, then dinner is served. Speeches are given - either between courses or immediately after. First dance, then parent dances. The floor opens, and cake cutting, bouquet toss and any cultural dances happen once people are already up.",
                "Cake cutting and the bouquet toss work best partway through dancing rather than before it. Both pause the floor, and a floor that has been dancing recovers in one song. A floor that has not started never does.",
            ]),
            ("Speeches, and where they go", [
                "Between courses is the kindest placement: guests are seated and fed, nobody is waiting for food, and the pause is natural. All speeches stacked after dinner is the most common arrangement and the one that most reliably stalls a room.",
                "Three speeches at five minutes each is fifteen minutes. In practice, unbriefed speakers run eleven minutes apiece. Cap the number, give each a time, and have your DJ or MC hold them to it.",
            ]),
            ("When the energy actually dips", [
                "Roughly two hours in, after the formal items are done and before the night finds its own momentum. This is precisely where traditions like La Hora Loca exist to intervene, and where a good DJ earns their fee.",
                "It is also when older guests leave, which is fine - but if you want photographs with them, take those earlier rather than assuming there will be a moment later.",
            ]),
        ],
        "practical": [
            ("Give your DJ or MC the running order in writing", "They drive the second half of the night. Every announcement, every transition and the timing of the first dance runs through them."),
            ("Tell your photographer when the first dance is", "It is a fixed, unrepeatable moment in bad light. A photographer who is changing a lens when it starts cannot go back."),
            ("Coordinate speeches with the kitchen", "A caterer plating a course during a speech is a clash of two schedules. Your coordinator should have agreed it with the captain."),
            ("Decide about a send-off early", "Sparklers, cold sparks and confetti are frequently banned by venues, and a send-off needs guests who have not already left. If you want one, schedule it earlier than feels right."),
        ],
        "faqs": [
            ("What is the typical order of a wedding reception?",
             "Cocktail hour, guests seated, wedding party and couple announced in, dinner, speeches, first dance and parent dances, then the floor opens. Cake cutting and the bouquet toss work best partway through dancing rather than before it."),
            ("When should wedding speeches happen?",
             "Between dinner courses is kindest - guests are seated and fed, and the pause feels natural. Stacking every speech after dinner is the most common arrangement and the most reliable way to stall a room before dancing starts."),
            ("When should we cut the cake?",
             "Partway through dancing rather than before it. Cake cutting pauses the floor, and a floor that is already dancing recovers within a song, while one that has not started may never get going."),
        ],
    },
    "first-dance": {
        "question": "How do you choose a first dance song?",
        "short": "The first dance",
        "group": "The day itself",
        "cats": ["wedding-djs", "wedding-bands", "wedding-photographers"],
        "related": ["reception-order", "wedding-day-timeline", "wedding-speeches"],
        "lede": "The practical constraints on a first dance song are shorter than people expect: it wants a steady tempo, a clear beginning, and ideally a length under three and a half minutes. Meaning matters, but a four-and-a-half minute song with a long instrumental middle is a surprisingly long time to be looked at.",
        "sections": [
            ("What makes a song work", [
                "A recognisable opening so guests know it has started. A tempo you can actually move to - many beloved songs are slower than they feel on headphones. And a length you can sustain: three minutes is comfortable, four is long, and anything past that usually wants cutting or an invitation for others to join partway through.",
                "Check the lyrics all the way to the end. A remarkable number of wedding-sounding songs are about loss, leaving or someone who is not coming back, and the third verse is where that usually becomes apparent.",
            ]),
            ("Cutting the song, and being watched", [
                "Any DJ can edit a track down. A clean fade at 2:45 is invisible to guests and a relief to the couple. Ask for it rather than enduring a long outro.",
                "If dancing in front of everyone is not appealing, the standard fix is to invite the wedding party in after the first verse and everyone else after the second. It is a normal thing to plan and nobody notices it was planned.",
            ]),
            ("If you want lessons", [
                "Two or three lessons is usually plenty to stop the swaying-in-a-circle default. Book them six to eight weeks out, not the week before, and practise in shoes similar to the ones you will wear.",
                "Tell the instructor the exact recording you are using. Live-band versions and remixes have different tempos and arrangements, and choreography learned to the wrong one falls apart.",
            ]),
        ],
        "practical": [
            ("Send the exact recording to your DJ or band", "Not the song title - the specific version. Covers, live versions and radio edits differ in length, tempo and arrangement."),
            ("Ask your band whether they will learn it", "Most will, some charge, and a few will decline if it sits far outside their style. Ask early, because the answer may change your choice."),
            ("Ask your DJ to edit it to length", "A fade at around 2:45 is standard and makes the moment better. This is a normal request, not a difficult one."),
            ("Tell your photographer and videographer the plan", "If the wedding party joins partway through, they will frame the opening differently. It is one sentence and it changes the photographs."),
        ],
        "faqs": [
            ("How long should a first dance be?",
             "Around three minutes is comfortable. Four feels long and anything beyond that usually wants cutting or an invitation for the wedding party to join partway through. Any DJ can fade a track cleanly at about 2:45."),
            ("Do we need first dance lessons?",
             "Not necessarily, but two or three lessons six to eight weeks out is usually enough to move beyond swaying in a circle. Practise in shoes similar to the ones you will wear, and tell the instructor the exact recording."),
            ("What makes a good first dance song?",
             "A recognisable opening, a tempo you can genuinely move to, and a length under about three and a half minutes. Check the lyrics to the end - many wedding-sounding songs turn out to be about loss or leaving."),
        ],
    },
    "wedding-emergency-kit": {
        "question": "What should be in a wedding emergency kit?",
        "short": "The emergency kit",
        "group": "The day itself",
        "cats": ["day-of-coordination", "hair-and-makeup", "wedding-planners"],
        "related": ["wedding-day-timeline", "rain-plan", "reception-order"],
        "lede": "A wedding emergency kit solves about a dozen predictable problems: a broken strap, a stain, a headache, a blister, a missing button. Most of it costs under fifty dollars, and the single most useful item is the one almost nobody packs - a phone charger with a long cable.",
        "sections": [
            ("What gets used at almost every wedding", [
                "Safety pins and a small sewing kit with thread matching every outfit. Fashion tape. A stain remover pen and a Tide-style wipe. Blister plasters and flat shoes. Painkillers, antacids and antihistamines. Deodorant, powder to cut shine, and a lint roller. Tissues, straws so lipstick survives drinking, and breath mints.",
                "And the phone charger. Somebody's phone is running the music before the ceremony, holding the readings, or coordinating the shuttle, and it will be at 8%.",
            ]),
            ("What gets used occasionally but saves the day", [
                "Super glue for a broken heel or a bead. Clear nail polish for a run in tights and for stopping a fray. A steamer or wrinkle-release spray. Scissors. Double-sided tape. A white chalk stick, which hides a mark on a white dress better than any cleaning product and is the trick most stylists know.",
                "A printed copy of the timeline and every vendor's phone number, on paper. When a phone dies or a signal drops, the paper copy is what keeps the day moving.",
            ]),
            ("Who carries it", [
                "Not the couple. Give it to your coordinator, or to a specific member of the wedding party who is told in advance that this is their job. A kit in a hotel room three miles away has solved nothing.",
                "Split it: a small pouch that travels with the party through the day, and the bulk of it in one place at the venue.",
            ]),
        ],
        "practical": [
            ("Hand it to your coordinator at the rehearsal", "So it is on site before the morning, and so the person responsible for it has actually seen it."),
            ("Ask your hair and makeup artist what to add", "They know what your specific products need for touch-ups, and will often tell you what to buy rather than selling it to you."),
            ("Print the vendor contact sheet", "Phones die and venues have dead spots. A paper list of every vendor's mobile number is the cheapest insurance in wedding planning."),
            ("Check what your venue already has", "Many keep a kit, a steamer and a first-aid box. Ask, and pack around the gaps rather than duplicating."),
        ],
        "faqs": [
            ("What should be in a wedding day emergency kit?",
             "Safety pins, a sewing kit with matching thread, fashion tape, stain remover, blister plasters, painkillers, deodorant, a lint roller, tissues, straws, mints - and a phone charger with a long cable, which is the most-needed and least-packed item."),
            ("Who should carry the wedding emergency kit?",
             "Your coordinator, or a named member of the wedding party who has been told in advance. Not the couple. Split it into a small pouch that travels through the day and the bulk kept at the venue."),
            ("How do you get a stain off a wedding dress?",
             "A stain pen or wipe for most marks, and a white chalk stick for anything that remains - chalk hides a mark on white fabric better than cleaning it on the day, and it is the trick most stylists rely on."),
        ],
    },
    # ------------------------------------------------------------ people
    "guest-list": {
        "question": "How do you make a wedding guest list?",
        "short": "The guest list",
        "group": "People",
        "cats": ["wedding-venues", "wedding-caterers", "wedding-invitations"],
        "related": ["plus-ones", "kids-at-weddings", "seating-chart"],
        "lede": "The guest list is the most expensive decision in wedding planning, because catering, bar, rentals, cake, invitations and transport are all priced per person. Twenty fewer guests usually saves more than every negotiation you will have with every vendor combined.",
        "sections": [
            ("Build it in tiers, not in one pass", [
                "Write three lists: people whose absence would genuinely change the day, people you would be glad to see, and people you are considering out of obligation. Invite tier one, then add from tier two until you reach your number. Tier three is the list you are allowed to cut, and naming it as a tier makes cutting it possible.",
                "Expect a decline rate of 10 to 20% for a local wedding and considerably more for a destination one. Inviting to capacity assuming everyone comes is how a 120-person venue ends up with 140 confirmed guests and nowhere to put them.",
            ]),
            ("Whose list is it", [
                "Parents contributing financially frequently expect to invite people, and the resulting arithmetic is the most common source of conflict in wedding planning. The workable approach is to agree a number per side early and let each side fill it however they like.",
                "It is easier to say 'you have twenty' than to adjudicate individual names, and it moves the conversation from a negotiation about people to a negotiation about a number.",
            ]),
            ("The rules that make cuts defensible", [
                "Pick a principle and apply it without exception: no colleagues, no one you have not spoken to in two years, no plus-ones for guests not in a long-term relationship. A rule applied evenly is defensible. An exception made once is a rule that no longer exists, and everyone who hears about it will ask.",
                "Write the rule down and use the same words with everyone who asks. That sentence is the whole tool.",
            ]),
        ],
        "practical": [
            ("Fix the number before you book the venue", "Venue capacity and catering minimums are both set by headcount. Choosing a venue first and a guest list second is how couples end up paying for a room they must fill."),
            ("Collect addresses early", "Chasing 90 postal addresses takes weeks. Start it when you start the list, not when the invitations arrive from the printer."),
            ("Count households, not people, for stationery", "Invitations are ordered per household - roughly 60% of your guest count - plus 10-15% extra."),
            ("Tell your caterer the real number, early", "Final counts are usually due two to three weeks out, and the number you give is the number you pay for whether or not those people come."),
        ],
        "faqs": [
            ("How do you cut down a wedding guest list?",
             "Build it in three tiers - essential, glad to see, obligation - and cut from the third. Then pick a rule and apply it to everyone without exception: no colleagues, no one you have not spoken to in two years. A rule applied evenly is defensible; an exception made once ends the rule."),
            ("What percentage of wedding guests decline?",
             "Typically 10-20% for a local wedding, and considerably more for a destination one. Inviting to your venue's exact capacity on the assumption everyone attends is a common and expensive mistake."),
            ("How do you handle parents wanting to invite people?",
             "Agree a number per side early and let each side fill it as they choose. Negotiating a headcount is far easier than adjudicating individual names, and it is the single most effective way to defuse the most common wedding planning conflict."),
        ],
    },
    "plus-ones": {
        "question": "Who gets a plus-one at a wedding?",
        "short": "Plus-ones",
        "group": "People",
        "cats": ["wedding-invitations", "wedding-venues", "wedding-caterers"],
        "related": ["guest-list", "kids-at-weddings", "rsvp-management"],
        "lede": "There is no universal rule about plus-ones, which is exactly why you need your own. The workable convention is that anyone married, engaged, living with a partner, or in a long-term relationship gets one by name, and everyone else is invited alone — applied to every guest without exception.",
        "sections": [
            ("Draw the line, then hold it", [
                "The common lines are: partners of any kind, or partners you have met, or partners in relationships over a year. Any of them is fine. What matters is that you can state it in one sentence and that it applies to everyone at the same tier.",
                "Guests talk. One exception made for a close friend becomes the reason three other people ask, and there is no version of that conversation that goes well. The rule is what protects you, so decide it before the first person asks.",
            ]),
            ("Say it on the envelope, not in the fine print", [
                "Address the invitation to exactly who is invited, by name. 'Ms Jane Doe and Mr John Smith' is unambiguous; 'Ms Jane Doe and Guest' explicitly offers a plus-one; 'Ms Jane Doe' invites one person.",
                "Then reinforce it on the RSVP: a card or online form that names the invited guests and does not allow adding names removes the ambiguity entirely. Most awkward plus-one situations are really RSVP design problems.",
            ]),
            ("When someone asks anyway", [
                "Answer once, warmly, with your rule: 'We'd have loved to, but we're at capacity and had to keep it to partners people live with.' Do not negotiate and do not explain further. A second sentence invites a second request.",
                "The genuine exceptions worth considering are guests who will know nobody at all, particularly if they are travelling a long way. That is a hospitality judgement rather than a breach of the rule, and it is defensible if you would extend it to anyone in the same position.",
            ]),
        ],
        "practical": [
            ("Name every guest on the invitation", "The envelope is the mechanism. Ambiguity there is what creates the awkward conversation later."),
            ("Use an RSVP that cannot add names", "Whether paper or online, it should list the invited guests and only allow yes or no. Your wedding website can do this."),
            ("Give your caterer the confirmed number, not the invited one", "Plus-one confusion is a leading cause of headcount drift, and you pay per head."),
            ("Tell whoever is seating people", "An unexpected extra guest is a seating chart problem at the exact moment nobody can fix it."),
        ],
        "faqs": [
            ("Do you have to give everyone a plus-one?",
             "No. The common convention is that anyone married, engaged, cohabiting or in a long-term relationship gets one, and everyone else is invited alone. What matters is applying whatever line you choose to every guest at the same tier without exception."),
            ("How do you say no plus-ones on an invitation?",
             "By addressing the invitation to exactly who is invited, by name, and using an RSVP that lists those names and does not allow adding more. Most plus-one awkwardness is really an RSVP design problem."),
            ("What do you say when a guest asks for a plus-one?",
             "Answer once, warmly, with your rule - that you are at capacity and had to limit it to partners people live with - and do not negotiate further. A second sentence of explanation invites a second request."),
        ],
    },
    "kids-at-weddings": {
        "question": "Should you have kids at your wedding?",
        "short": "Kids at weddings",
        "group": "People",
        "cats": ["wedding-venues", "wedding-caterers", "day-of-coordination"],
        "related": ["guest-list", "plus-ones", "seating-chart"],
        "lede": "Either choice is entirely normal, and both need to be communicated clearly and early. An adults-only wedding is not rude; springing it on a guest who has already booked flights and a family room is. The decision is easy — the logistics of announcing it are what actually require thought.",
        "sections": [
            ("If you are having children", [
                "Count them properly with your caterer: children's meals are typically discounted but are frequently left off a first quote entirely. Ask about a kids' menu and confirm the age cut-off.",
                "The thing that makes it work is somewhere for them to be. A separate room with a sitter, activity bags at the table, and an honest expectation that they will be gone by nine. Many couples hire a sitter for the reception, which costs less than a floral centrepiece and is the difference between parents enjoying the night and leaving at eight.",
            ]),
            ("If you are not", [
                "Say it early - on the save-the-date or the wedding website, not for the first time on the invitation. Guests with children need lead time to arrange care, and some will need to decide whether to travel at all.",
                "Address invitations to named adults only, and put one clear line on the website: 'We're having an adults-only celebration.' No apology, no explanation. Explanations read as negotiable.",
            ]),
            ("The in-between versions", [
                "Plenty of couples include only children in the wedding party, or only immediate family, or allow children at the ceremony but not the reception. All of these work. Each needs stating explicitly, because guests will otherwise apply the version they prefer.",
                "If you are hosting a rehearsal dinner or a next-day brunch, making one of those child-friendly is a genuine kindness to travelling families and costs you nothing at the wedding itself.",
            ]),
        ],
        "practical": [
            ("Put it on the website before the invitations go out", "Save-the-date timing gives guests months to arrange care. Invitation timing gives them weeks, and some of them will decline."),
            ("Confirm the children's headcount with your caterer", "Kids' meals are usually cheaper but are routinely missing from a first quote. Confirm the price and the age cut-off."),
            ("Ask your venue about a quiet room", "Most have something. A room with a sitter for the evening is one of the highest-value small spends at a wedding with families."),
            ("Tell your photographer if children are in the ceremony", "Flower children and ring bearers need a rehearsal and, on the day, a plan for what happens if one of them stops walking."),
        ],
        "faqs": [
            ("How do you say no kids at a wedding?",
             "State it on the save-the-date or your wedding website, months before invitations, then address invitations to named adults only. One clear line - 'We're having an adults-only celebration' - with no apology and no explanation, because explanations read as negotiable."),
            ("Is it rude to have an adults-only wedding?",
             "No. What causes genuine offence is announcing it late, after guests have booked travel and arranged a family trip. The decision is yours; the timing is the courtesy."),
            ("What do you do with kids at a wedding reception?",
             "A separate quiet room with a hired sitter is the arrangement that works best, and it costs less than a floral centrepiece. Activity bags at the table help, and most children are gone by nine."),
        ],
    },
    "seating-chart": {
        "question": "How do you make a wedding seating chart?",
        "short": "The seating chart",
        "group": "People",
        "cats": ["day-of-coordination", "wedding-planners", "wedding-rentals"],
        "related": ["guest-list", "rsvp-management", "reception-order"],
        "lede": "Do not start the seating chart until RSVPs are closed and the final count is in, because every change cascades. Then work in tables rather than in seats: group people first, place the groups in the room, and only assign individual chairs if your caterer needs it for a plated meal.",
        "sections": [
            ("Group first, place second", [
                "Sort guests into natural clusters - college friends, your partner's cousins, work people, the neighbours - and treat each cluster as a block. Most clusters are close to a table's worth, and the ones that are not get combined with the group they will most easily talk to.",
                "Then place the blocks in the room. Older guests away from the speakers. Small children near an exit. The friends who will dance nearest the floor. People who need to leave early near the door.",
            ]),
            ("The decisions people agonise over", [
                "<strong>Divorced parents.</strong> Separate tables, both near the front, equal distance from you. Ask each of them privately what they would prefer rather than guessing.",
                "<strong>The singles table.</strong> Do not build one. Seat people with those they will actually enjoy; a table constructed from unrelated people who share only a relationship status is visible to everyone sitting at it.",
                "<strong>Your own table.</strong> A sweetheart table for two, or a head table with the wedding party, or joining a table of friends. All normal. A sweetheart table means you will speak to almost nobody during dinner, which some couples want and others regret.",
            ]),
            ("Assigned tables versus assigned seats", [
                "Assigned tables with open seating at them is enough for most weddings and is far less work. Plated dinners with multiple entrée choices are the case where caterers genuinely need assigned seats, so ask yours before deciding.",
                "Whatever you choose, a legible escort display at the entrance is what prevents a queue. Alphabetical by surname, not grouped by table - guests know their own name, not their table number.",
            ]),
        ],
        "practical": [
            ("Wait for final RSVPs", "Starting early guarantees doing it twice. Every late decline reshuffles a table."),
            ("Ask your caterer whether they need assigned seats", "Plated service with entrée choices usually does; buffet and family-style usually do not. It halves the work if they do not."),
            ("Send the final chart to your coordinator and caterer", "They set the room and place the cards. A chart that exists only on your laptop is not a chart."),
            ("Order the escort display alphabetically", "By surname, not by table. Guests look for their own name, and alphabetical ordering is what stops a queue forming at the door."),
        ],
        "faqs": [
            ("When should you do the wedding seating chart?",
             "After RSVPs close and you have a final count. Starting earlier guarantees redoing it, because every late decline reshuffles a table."),
            ("Do you need assigned seats at a wedding?",
             "Assigned tables with open seating at them is enough for most weddings. Assigned seats are genuinely needed for plated dinners with multiple entrée choices - ask your caterer, because it halves the work if they do not need it."),
            ("How do you seat divorced parents at a wedding?",
             "Separate tables, both near the front, equal distance from you. Ask each of them privately what they would prefer rather than guessing - the question is almost always better received than the assumption."),
        ],
    },
    "wedding-party": {
        "question": "How do you choose your wedding party?",
        "short": "The wedding party",
        "group": "People",
        "cats": ["hair-and-makeup", "wedding-photographers", "day-of-coordination"],
        "related": ["guest-list", "wedding-speeches", "rehearsal-dinner"],
        "lede": "Choose people for who they are on a hard day, not for who has the longest history with you. The wedding party's real job is not decorative: they answer the phone at 8am, they keep a nervous person calm, and one of them speaks in front of 140 people.",
        "sections": [
            ("What you are actually asking of them", [
                "A full day beginning early, often with hair and makeup they may pay for themselves. An outfit they buy. Travel, and usually a pre-wedding event or two. And on the day, the job of noticing what is going wrong before you do.",
                "Say all of that when you ask, including the money. The most common friction in wedding parties is financial and it is almost always caused by an unstated assumption rather than an unreasonable one.",
            ]),
            ("Size, symmetry and the rest of it", [
                "The sides do not need to match, people do not need to be the same gender as the person they stand with, and nobody is obliged to reciprocate because you were in their wedding. These conventions are dissolving quickly and no guest will notice.",
                "Large wedding parties are slower: more hair and makeup services, more people to gather for photographs, more to organise. Eight people is a morning. Sixteen is a logistical operation.",
            ]),
            ("The people you cannot include", [
                "Somebody will be left out who expected to be in. The kind version is to tell them directly and early, in person, and to give them a real role instead - a reading, greeting guests, managing something specific - rather than hoping they will not mind.",
                "Do not invent a title to soften it. A made-up role reads as exactly what it is.",
            ]),
        ],
        "practical": [
            ("State the costs when you ask", "Outfit, travel, hair and makeup, any events. The conversation is easy in advance and hard afterwards."),
            ("Tell your hair and makeup artist the number early", "Party size sets the morning schedule and how many artists you need. It is the single biggest driver of whether you are ready on time."),
            ("Give your photographer the list and the relationships", "So they know who to gather for photographs and who matters in them."),
            ("Name one person as the point of contact", "Your coordinator needs someone in the party to relay to. Without it, every message goes to the couple."),
        ],
        "faqs": [
            ("How many people should be in a wedding party?",
             "There is no correct number, but size has real consequences: each person adds hair and makeup services, time to gather for photographs, and coordination. Eight people is a manageable morning; sixteen is a logistical operation."),
            ("Do wedding party sides have to be equal?",
             "No. Uneven sides, mixed-gender parties, and people standing with whoever they are closest to are all completely normal now, and guests do not notice."),
            ("Who pays for bridesmaid hair and makeup?",
             "Either the couple or the bridesmaids - both are entirely normal. What matters is saying which when you ask, because unstated financial assumptions are the most common source of wedding party friction."),
        ],
    },
    # ------------------------------------------------------------ words
    "writing-your-own-vows": {
        "question": "How do you write your own wedding vows?",
        "short": "Writing your own vows",
        "group": "Words",
        "cats": ["wedding-officiants", "wedding-videographers", "wedding-photographers"],
        "related": ["ceremony-order", "wedding-speeches", "wedding-day-timeline"],
        "lede": "Personal vows work when they are specific and short. One minute each, read from a card, containing two or three concrete promises and one real detail about the person. The failure mode is not being unromantic - it is being general, because general is what everyone else's vows already sound like.",
        "sections": [
            ("Structure that works", [
                "A workable shape: why this person, one specific memory or trait, then the promises, then what you are committing to. Roughly 150 to 200 words, which is about a minute spoken. Vows over two minutes lose a room, and the room includes you.",
                "Agree the format with your partner beforehand - similar length, similar tone, whether you are being funny. Mismatched vows are genuinely awkward, and it is the one part of the ceremony where you cannot adjust mid-way.",
            ]),
            ("Specific beats poetic", [
                "'I promise to love you forever' is true and says nothing, because it could be said by anyone to anyone. 'I promise to keep making you coffee before you are properly awake, and to keep pretending I do not notice you crying at adverts' is about one person.",
                "Take promises from your actual life. The details that land hardest are the small ones the two of you would recognise from across a room, not the large ones everyone shares.",
            ]),
            ("The mechanics on the day", [
                "Write them on a card, not a phone. Phones lock, glare and look wrong in photographs, and a card in a shaking hand is easier to hold than a screen. Print them large enough to read while emotional.",
                "Give a copy to your officiant. People lose their place, forget the card, or cannot speak, and an officiant holding a spare can feed you a line invisibly. It is the single best insurance for this part of the day.",
            ]),
        ],
        "practical": [
            ("Ask your officiant to hold a spare copy", "Standard practice, invisible to guests, and the fix for the most common thing that goes wrong here."),
            ("Confirm your venue permits personal vows", "Some religious ceremonies require set liturgical wording and allow personal vows only at the rehearsal dinner or not at all. Ask before writing."),
            ("Tell your videographer you are doing personal vows", "It changes the microphone plan: they will want lapel mics on both of you rather than relying on the officiant's."),
            ("Write them two weeks out, not the night before", "Not for polish - so you can read them aloud once and hear where they are too long."),
        ],
        "faqs": [
            ("How long should wedding vows be?",
             "About one minute each, roughly 150-200 words. Anything past two minutes loses the room. Agree a similar length and tone with your partner beforehand, because mismatched vows are awkward and cannot be adjusted mid-ceremony."),
            ("What should you include in personal wedding vows?",
             "Why this person, one specific memory or trait, two or three concrete promises, and what you are committing to. Specific beats poetic - promises drawn from your actual daily life land far harder than universal declarations."),
            ("Should you memorise your wedding vows?",
             "No. Read them from a printed card, not a phone - phones lock, glare and photograph badly. Give a spare copy to your officiant, who can feed you a line invisibly if you lose your place."),
        ],
    },
    "wedding-speeches": {
        "question": "How do you write a wedding speech?",
        "short": "Wedding speeches",
        "group": "Words",
        "cats": ["wedding-djs", "wedding-bands", "day-of-coordination"],
        "related": ["reception-order", "writing-your-own-vows", "wedding-party"],
        "lede": "Five minutes. Every good wedding speech is about five minutes, contains one story rather than a list of them, and ends with a toast people know to raise a glass to. The most common failure is length, and the second is a story that is funnier to the speaker than to the room.",
        "sections": [
            ("The shape of a speech that works", [
                "Say who you are and how you know them. Tell one story - a single, specific story with a beginning and an end. Turn it to say something true about the couple. Then toast. That is the entire structure and it holds for a best man, a maid of honour, a parent or the couple themselves.",
                "One story told properly beats four told quickly. The instinct to include everything is what produces an eleven-minute speech, and eleven minutes is where a room starts checking its phones.",
            ]),
            ("What to cut", [
                "Ex-partners. Anything about drinking, however affectionately. In-jokes only four people understand. Anything you would not say with the person's grandmother sitting three feet away, because she is. And any sentence that begins 'I've known him since...' followed by a chronology.",
                "The test worth applying: would this be funny to someone who has never met either of them? If the humour depends on knowing the person, it is a story for the rehearsal dinner.",
            ]),
            ("Delivering it", [
                "Read it aloud twice, timed. Print it in large type on cards - not a phone. Hold the microphone close and speak more slowly than feels natural, because nerves accelerate everyone.",
                "Say the toast line clearly and raise your glass as you say it, so the room knows it has ended. Speeches that trail off leave everyone unsure whether to clap, which is a sad end to a good speech.",
            ]),
        ],
        "practical": [
            ("Give every speaker a time limit and mean it", "Five minutes each. Tell them the number when you ask, not the week before."),
            ("Tell your DJ or MC who is speaking and in what order", "They introduce each speaker and close the section. Unbriefed, this falls to whoever holds the microphone."),
            ("Coordinate with the kitchen", "Speeches between courses work best, but only if your caterer knows. A course arriving mid-speech is two schedules colliding."),
            ("Ask for a handheld mic, not a lectern mic", "Speakers move. A fixed microphone captures half of a nervous speech and your videographer captures the rest badly."),
        ],
        "faqs": [
            ("How long should a wedding speech be?",
             "Five minutes. Unbriefed speakers routinely run eleven, which is where a room starts losing interest. Give every speaker a time limit when you ask them, and have your DJ or MC hold them to it."),
            ("What should you not say in a wedding speech?",
             "Ex-partners, drinking stories, in-jokes only a few people understand, and anything you would not say with the person's grandmother three feet away - because she is. If the humour requires knowing the person, save it for the rehearsal dinner."),
            ("What is the order of wedding speeches?",
             "Commonly the hosts or parents, then the best man and maid of honour, then the couple. The order matters less than the placement: between dinner courses is kinder than stacking them all before dancing."),
        ],
    },
    "invitation-wording": {
        "question": "How do you word a wedding invitation?",
        "short": "Invitation wording",
        "group": "Words",
        "cats": ["wedding-invitations", "wedding-venues"],
        "related": ["rsvp-management", "guest-list", "plus-ones"],
        "lede": "A wedding invitation has to convey five things: who is hosting, who is marrying, when, where, and what to do next. Everything beyond that is style. The part couples get wrong is not the formal phrasing — it is leaving out the information guests actually need, like dress code and whether children are invited.",
        "sections": [
            ("Who is hosting, and why it is the first line", [
                "Traditionally the hosts are whoever is paying, and the invitation opens in their voice: 'Mr and Mrs James Doe request the pleasure of your company at the marriage of their daughter...'. When the couple hosts, it opens with them: 'Together with their families, Jane Doe and John Smith invite you...'.",
                "The 'together with their families' formulation is now the most widely used, because it is accurate in most modern situations - several people contributed - and it avoids ranking anyone.",
            ]),
            ("Formality, and matching it to the day", [
                "'Request the honour of your presence' traditionally signals a religious venue; 'request the pleasure of your company' signals anywhere else. Spelling out the date and time in words reads formal; numerals read modern. Neither is incorrect.",
                "What matters is consistency with the wedding itself. A black-tie invitation to a barn reception confuses people about what to wear, and that confusion is the actual cost of getting the register wrong.",
            ]),
            ("What couples leave out and should not", [
                "<strong>Dress code.</strong> If you care at all, say it. Guests would rather be told than guess, and 'black tie optional' or 'garden party attire' takes four words.",
                "<strong>Whether children are invited.</strong> Named addressing carries it, but a line on the website removes all doubt.",
                "<strong>End time or an indication of the shape of the day.</strong> Guests booking travel and childcare need to know whether this ends at ten or at two.",
                "<strong>The website.</strong> One line pointing to it lets you keep the invitation clean and put everything else there.",
            ]),
        ],
        "practical": [
            ("Proofread as though it costs $800 to be wrong", "Because it does. Almost every stationery contract makes you responsible for the final proof, and a reprint is a fresh press setup."),
            ("Check the date against a calendar, out loud", "Wrong day-of-week for the date is the single most common invitation error, and it is invisible when you are reading for typos."),
            ("Put details on your wedding website, not the invitation", "Dress code detail, directions, hotels, registry and FAQs all belong there. One line on the invitation keeps it uncluttered."),
            ("Have your stationer weigh a finished suite", "Square, thick or oversized invitations need extra postage, sometimes double. This is the most commonly unbudgeted cost in stationery."),
        ],
        "faqs": [
            ("How do you word a wedding invitation when the couple is hosting?",
             "'Together with their families, Jane Doe and John Smith invite you to celebrate their marriage.' This formulation is now the most widely used because it is accurate when several people have contributed and avoids ranking anyone."),
            ("What is the difference between 'honour of your presence' and 'pleasure of your company'?",
             "Traditionally, 'the honour of your presence' signals a religious venue and 'the pleasure of your company' signals anywhere else. Neither is incorrect anywhere; what matters more is that the formality matches the wedding itself."),
            ("Should you put the dress code on a wedding invitation?",
             "Yes, if you care at all. Four words - 'black tie optional', 'garden party attire' - saves every guest from guessing. Anything longer belongs on your wedding website."),
        ],
    },
    "thank-you-notes": {
        "question": "When should you send wedding thank-you notes?",
        "short": "Thank-you notes",
        "group": "Words",
        "cats": ["wedding-invitations"],
        "related": ["invitation-wording", "rsvp-management", "guest-list"],
        "lede": "Within three months of the wedding, and within two weeks for gifts that arrive beforehand. The much-repeated 'you have a year' is a myth that has caused more guilt than it has relieved — and the real trick is writing them as gifts arrive rather than facing 90 of them at once.",
        "sections": [
            ("The timeline that actually works", [
                "Gifts arriving before the wedding: reply within two weeks of receiving them. Gifts given at or after the wedding: within three months. Handwritten, on paper, posted.",
                "Writing them as they arrive turns a daunting block of 90 notes into a few each week. Couples who wait until after the honeymoon face the whole pile at once, which is why the job so often stretches past the point of being gracious.",
            ]),
            ("What to write", [
                "Name the specific gift and say something true about using it. 'Thank you for the Dutch oven - we have already made two batches of chili in it' takes ten seconds longer than a generic line and reads completely differently.",
                "For cash or a contribution, name what it is going toward: the honeymoon, the deposit, the thing you had been saving for. You do not need to state the amount.",
                "Three or four sentences is plenty. Mention the person - that you were glad they came, or sorry they could not - and sign both names.",
            ]),
            ("Tracking, which is the actual hard part", [
                "Keep a running list from the first gift: who, what, when it arrived, and whether the note is sent. This lives naturally on your wedding website alongside the guest list, where both of you can update it.",
                "Assign someone at the reception to record who gave what, because cards separate from gifts constantly. Without it you will be guessing in February.",
            ]),
        ],
        "practical": [
            ("Order thank-you cards with your invitations", "Same press setup, often cheaper, and they arrive before you need them rather than three weeks after."),
            ("Track gifts from the first one, not from the wedding", "A running list costs nothing at the start and is impossible to reconstruct later."),
            ("Assign someone to log gifts at the reception", "Cards and gifts separate. Somebody should be writing down who gave what as they arrive."),
            ("Split the list between you", "Write to your own side. It halves the work and the notes sound more like the person who knows them."),
        ],
        "faqs": [
            ("How long do you have to send wedding thank-you notes?",
             "Within three months of the wedding, and within two weeks for gifts that arrive beforehand. The common claim that you have a year is a myth, and following it usually makes the job harder rather than easier."),
            ("What do you write in a wedding thank-you note?",
             "Name the specific gift and say something true about using it, mention the person, and sign both names. Three or four sentences is plenty. For cash, say what it is going toward without naming the amount."),
            ("Do you send thank-you notes for cash gifts?",
             "Yes. Name what the money is going toward - the honeymoon, a deposit, something you had been saving for - without stating the amount."),
        ],
    },
    # ------------------------------------------------------------ logistics
    "marriage-license": {
        "question": "How do you get a marriage license?",
        "short": "The marriage license",
        "group": "Logistics",
        "cats": ["wedding-officiants"],
        "related": ["ceremony-order", "name-change", "wedding-day-timeline"],
        "lede": "Both of you apply in person at a county clerk's office, bring photo ID, pay a fee usually between $30 and $120, and receive the license. The two details that catch couples out are that licenses expire — commonly 30 to 90 days — and that some states impose a waiting period between issue and ceremony.",
        "sections": [
            ("What you need, roughly everywhere", [
                "Government photo ID for both of you, and often your Social Security numbers. If either of you has been married before, the date the previous marriage ended and sometimes the divorce decree or death certificate. Some counties require the names and birthplaces of your parents.",
                "Rules vary by state and sometimes by county, and the county clerk's own website is the authority - not a wedding blog, and not us. Read it once, a few months out, and note exactly what it asks for.",
            ]),
            ("Timing, which is where it goes wrong", [
                "<strong>Expiry.</strong> Licenses are valid for a limited window - frequently 30 to 90 days. Applying six months ahead to be organised is how couples arrive at the ceremony with an expired one.",
                "<strong>Waiting periods.</strong> Some states require a gap between issuing and the ceremony, often 24 to 72 hours. That matters for a Friday wedding with a Thursday application.",
                "<strong>Office hours.</strong> Clerk offices keep short weekday hours, are closed on public holidays, and often do not take appointments late in the week. Destination and out-of-state couples should plan an extra day.",
                "The usual sweet spot is applying two to four weeks before the wedding.",
            ]),
            ("Afterwards", [
                "Your officiant signs it, witnesses sign if your state requires them, and someone files it with the county - usually the officiant, within a stated number of days. Confirm who is filing and by when, because this is the one part of a wedding that cannot be fixed later.",
                "Order certified copies of the marriage certificate once it is recorded. You will need them for a name change, and ordering two or three at once is cheaper and faster than going back.",
            ]),
        ],
        "practical": [
            ("Read your county clerk's own page, not a summary", "Requirements vary by state and sometimes county. The clerk's site is the only authority, and it takes five minutes."),
            ("Apply two to four weeks out", "Late enough that it will not expire, early enough to absorb a closed office or a missing document."),
            ("Confirm with your officiant who files it", "Usually them, within a set number of days. Get the answer before the wedding, not after."),
            ("Order certified copies straight away", "You need them for a name change, and ordering several at once is cheaper than a second request."),
        ],
        "faqs": [
            ("How long is a marriage license valid?",
             "Commonly 30 to 90 days, depending on the state. Applying months in advance is a frequent mistake - couples arrive at the ceremony with an expired license. Two to four weeks before the wedding is the usual sweet spot."),
            ("Is there a waiting period for a marriage license?",
             "In some states, yes - often 24 to 72 hours between issuing and the ceremony. Check your county clerk's own page, because it varies by state and sometimes by county."),
            ("Who files the marriage license after the wedding?",
             "Usually the officiant, within a number of days set by the state. Confirm who is responsible before the wedding - it is the one part of the day that cannot be corrected afterwards."),
        ],
    },
    "rsvp-management": {
        "question": "How do you manage wedding RSVPs?",
        "short": "Managing RSVPs",
        "group": "Logistics",
        "cats": ["wedding-invitations", "wedding-caterers", "day-of-coordination"],
        "related": ["guest-list", "seating-chart", "plus-ones"],
        "lede": "Set your RSVP deadline three to four weeks before the wedding, roughly a week before your caterer's final count is due. That gap is not padding — it is the week you will spend chasing the twenty percent of guests who have not replied, because there are always twenty percent.",
        "sections": [
            ("The deadline, and the week after it", [
                "Work backwards: your caterer needs a final number two to three weeks out, so the RSVP date sits a week before that. Print the deadline on the card and on your website.",
                "Then expect to chase. Roughly a fifth of guests do not reply by any deadline, and it is not personal. Plan a round of texts and calls for the week after, and split the list between you so you are contacting people you actually know.",
            ]),
            ("Online, paper, or both", [
                "An online RSVP on your wedding website is faster, cheaper, and gives you a live count with meal choices attached. A paper card with a stamped return envelope gets better response rates from older guests. Offering both is normal and costs little.",
                "Whichever you use, the form should name the invited guests and not allow adding names. Most plus-one and children awkwardness is an RSVP design problem rather than an etiquette one.",
            ]),
            ("Collect the right things", [
                "Attendance, meal choice if you need it, and dietary requirements or allergies. Nothing else. Long RSVP forms lower response rates.",
                "Keep dietary requirements in one list with names attached - your caterer needs named plates, not a count of vegetarians, and the seating chart is how the kitchen finds them on the night.",
            ]),
        ],
        "practical": [
            ("Set the RSVP date a week before the caterer's deadline", "That week is for chasing, and you will need it."),
            ("Use a form that cannot add guests", "It should list the invited names and allow only yes or no. This removes the most common source of headcount drift."),
            ("Give your caterer named dietary requirements", "Not a count. They need to know which seat the nut allergy is in, which means the seating chart and the allergy list have to match."),
            ("Confirm when your final number locks", "That is the number you pay for, whether or not those guests come. Know the date and what a late change costs."),
        ],
        "faqs": [
            ("When should the wedding RSVP deadline be?",
             "Three to four weeks before the wedding - about a week before your caterer's final count is due. That week is for chasing the roughly twenty percent of guests who do not reply by any deadline."),
            ("What do you do when guests don't RSVP?",
             "Chase them directly by text or phone in the week after the deadline, splitting the list so each of you contacts people you know. It is entirely normal and not personal; plan for it rather than being surprised."),
            ("Should wedding RSVPs be online or on paper?",
             "Online is faster and gives a live count with meal choices; paper gets better response rates from older guests. Offering both is normal. Either way, the form should name the invited guests and not allow adding names."),
        ],
    },
    "rehearsal-dinner": {
        "question": "Who is invited to the rehearsal dinner?",
        "short": "The rehearsal dinner",
        "group": "Logistics",
        "cats": ["wedding-caterers", "wedding-venues", "wedding-officiants"],
        "related": ["wedding-party", "ceremony-order", "wedding-speeches"],
        "lede": "At minimum: the wedding party and their partners, immediate family, the officiant, and anyone with a role in the ceremony. Beyond that it grows as far as you want it to, and the most common modern version includes all out-of-town guests — which can quietly turn a dinner for 20 into an event for 60.",
        "sections": [
            ("The guest list, and how it escalates", [
                "The core group is whoever needs to be at the rehearsal, plus their partners. Adding grandparents and close family is standard. Adding out-of-town guests is a genuine kindness to people who have travelled, and it is also the decision that changes the budget most.",
                "Be deliberate: there is a real difference between a dinner for the twenty people who rehearsed and a second reception for sixty. Both are fine; only one of them is cheap.",
            ]),
            ("The rehearsal itself", [
                "Half an hour at the ceremony venue, ideally with your officiant and coordinator. Walk the processional, fix where everyone stands, decide who holds the rings and who cues the music. That is genuinely all it is.",
                "Book the venue time in writing. Ceremony spaces frequently have another event the evening before, and a rehearsal that cannot happen at the venue happens in a car park.",
            ]),
            ("Speeches and tone", [
                "This is where the longer, more personal, funnier speeches belong - the ones with in-jokes that would not work for 140 people. Many couples explicitly move toasts here to keep the reception moving.",
                "It is also the natural moment for gifts to the wedding party and parents, and for anything you want to say to a small room rather than a large one.",
            ]),
        ],
        "practical": [
            ("Book the rehearsal slot with your venue in writing", "Ceremony venues often host an event the night before. Assuming access is how rehearsals end up in a car park."),
            ("Tell your officiant and coordinator the time", "The rehearsal is their working session. Without them it is a group of people guessing where to stand."),
            ("Decide the guest list before booking a restaurant", "Twenty people and sixty people are different venues and different budgets. Do it in that order."),
            ("Move the long speeches here", "It keeps the reception moving and gives the personal material a room that suits it."),
        ],
        "faqs": [
            ("Who should be invited to the rehearsal dinner?",
             "At minimum the wedding party and their partners, immediate family, the officiant, and anyone with a ceremony role. Many couples also invite all out-of-town guests, which is a kindness but can turn a dinner for 20 into an event for 60."),
            ("How long does a wedding rehearsal take?",
             "About half an hour. You walk the processional, fix where everyone stands, and decide who holds the rings and who cues the music. Book the venue slot in writing, because ceremony spaces often have another event the night before."),
            ("Who pays for the rehearsal dinner?",
             "Traditionally the groom's family, though it is now as often the couple or shared. Like most wedding money questions, the answer matters less than agreeing it early and explicitly."),
        ],
    },
    "rain-plan": {
        "question": "What is a wedding rain plan?",
        "short": "The rain plan",
        "group": "Logistics",
        "cats": ["wedding-venues", "wedding-rentals", "day-of-coordination"],
        "related": ["wedding-day-timeline", "wedding-emergency-kit", "seating-chart"],
        "lede": "A rain plan is not 'we'll move inside'. It is a specific alternative layout, a named person who decides, and a deadline by which they decide — because a tent company needs hours of notice and a room cannot be reset in ten minutes.",
        "sections": [
            ("The three things that make it real", [
                "<strong>A specific space.</strong> Not 'indoors' - the actual room, with a layout you have seen, at your guest count. Ask your venue for photographs of a wedding held in the backup space, because backup rooms are usually smaller and always feel different.",
                "<strong>A named decision-maker.</strong> Your coordinator or venue manager, not you. On the morning you will be the least objective person available and the least able to take the call calmly.",
                "<strong>A deadline.</strong> Usually the morning of, sometimes the night before. It is set by how long the reset physically takes and by your tent company's notice period - not by the last moment the forecast might improve.",
            ]),
            ("Tents, and what they actually require", [
                "A tent booked on the day is a tent that does not exist. Companies need days of notice in peak season, which is why couples with outdoor ceremonies frequently book one on hold, with an agreed cancellation window and fee.",
                "Tents also bring flooring, lighting, power, sidewalls and sometimes heating. A tent alone in wet grass is not a solution, and the full package is a substantial cost that should be priced before you need it.",
            ]),
            ("Everything else weather touches", [
                "Hair and makeup schedules shift if guests arrive wet. Photographers need an indoor location scouted for portraits. Florals wilt in heat and blow over in wind. Ceremony audio fails outdoors in wind more than from any other cause. Guests need somewhere to put umbrellas.",
                "Heat is the underrated one. Shade, water stations and a shorter outdoor ceremony matter more at 98 degrees than rain contingency ever will.",
            ]),
        ],
        "practical": [
            ("Ask your venue for photos of a real wedding in the backup space", "Not a floor plan. Backup rooms are smaller than couples imagine and the photographs prevent a bad surprise."),
            ("Name the decision-maker and the deadline in writing", "Your coordinator or venue manager decides, by an agreed time. Putting it in writing is what stops the conversation happening at 9am on the day."),
            ("Ask your tent supplier their notice period and cancellation fee", "A tent cannot be summoned on the morning. Booking one on hold with a known cancellation window is the standard approach."),
            ("Have your photographer scout an indoor portrait spot", "They should identify it at the walkthrough, not while it is raining."),
        ],
        "faqs": [
            ("What should a wedding rain plan include?",
             "A specific alternative space you have seen at your guest count, a named person who makes the call - your coordinator or venue manager, not you - and a deadline for deciding, set by how long the reset takes and your tent company's notice period."),
            ("When do you decide to move a wedding indoors?",
             "By an agreed deadline, usually the morning of and sometimes the night before. It is set by physical reset time and tent notice periods, not by the last moment the forecast might improve."),
            ("Do you need to book a tent just in case?",
             "For an outdoor ceremony in an unpredictable season, usually yes - on hold, with an agreed cancellation window and fee. Tent companies need days of notice in peak season, so one booked on the day does not exist."),
        ],
    },
    "wedding-website": {
        "question": "What should you put on your wedding website?",
        "short": "Your wedding website",
        "group": "Logistics",
        "cats": ["wedding-invitations", "wedding-venues"],
        "related": ["rsvp-management", "invitation-wording", "plus-ones"],
        "lede": "A wedding website exists to answer the questions guests would otherwise text you. Date, location, times, dress code, where to stay, whether children are invited, and an RSVP. Everything else is optional, and the sites that work are the ones a guest can read in ninety seconds.",
        "sections": [
            ("What guests actually look for", [
                "In rough order of how often it is asked: what time does it start, where exactly is it, what should I wear, can I bring my partner, are children invited, where do I stay, how do I get there, and where are you registered.",
                "Answer those eight plainly and near the top. The story of how you met is lovely and nobody came to the site for it - put it below the practical information, not above.",
            ]),
            ("The parts that do real work", [
                "<strong>RSVP.</strong> Live counts, meal choices and dietary requirements collected in one place, with a form that names invited guests and does not allow adding names. This alone justifies having a site.",
                "<strong>Accommodation.</strong> Two or three options at different prices, with any room block code and its expiry. Out-of-town guests will thank you and stop asking.",
                "<strong>Travel and parking.</strong> Especially for venues that are hard to find, have limited parking, or need a shuttle. Include the shuttle schedule if there is one.",
                "<strong>A schedule.</strong> Rough times for the day and any surrounding events, so guests can book flights and childcare.",
            ]),
            ("Housekeeping", [
                "Put the URL on your save-the-date, which is months before the invitation and exactly when guests start planning travel.",
                "Password-protect it only if you have a genuine reason; a password is one more thing for guests to lose. Do not put your home address on a public page, and if you are collecting gifts, link to a registry rather than publishing account details.",
            ]),
        ],
        "practical": [
            ("Put the URL on the save-the-date", "Months earlier than the invitation, and exactly when guests start booking travel."),
            ("Use the RSVP to collect named dietary requirements", "Your caterer needs names attached to allergies, not a count, and this is where that data is cleanest."),
            ("Add the children and plus-one policy as a plain line", "One sentence removes the most common awkward conversation in wedding planning."),
            ("Keep it to ninety seconds of reading", "Practical information first. The story of how you met goes underneath it."),
        ],
        "faqs": [
            ("What should be on a wedding website?",
             "Date, venue and times, dress code, whether children are invited, plus-one policy, accommodation options, travel and parking, a rough schedule, registry links, and an RSVP form. Answer the practical questions near the top and put your story underneath."),
            ("When should you send out your wedding website?",
             "Put the URL on your save-the-date, months before the invitation. That is when guests start booking travel and arranging childcare, and it is when they most need the information."),
            ("Should a wedding website be password protected?",
             "Only if you have a specific reason - a password is one more thing for guests to lose. Regardless, never publish your home address, and link to a registry rather than posting account details."),
        ],
    },
    "name-change": {
        "question": "How do you change your name after marriage?",
        "short": "Changing your name",
        "group": "Logistics",
        "cats": ["wedding-officiants"],
        "related": ["marriage-license", "thank-you-notes", "rsvp-management"],
        "lede": "The order is fixed and it matters: certified marriage certificate first, then Social Security, then your driver's licence, then passport, then banks and everything else. Doing it out of order is the reason the process takes people months instead of weeks.",
        "sections": [
            ("The sequence", [
                "<strong>1. Certified marriage certificate.</strong> Not the decorative one from your ceremony - a certified copy from the county where it was recorded. Order two or three; nearly every subsequent step wants to see one.",
                "<strong>2. Social Security card.</strong> Free, and everything downstream checks against this record. Allow a couple of weeks for the update to propagate before the next step.",
                "<strong>3. Driver's licence.</strong> In person, with the certificate and your updated Social Security details.",
                "<strong>4. Passport.</strong> Free if your passport is under a year old, otherwise a renewal fee. Do not start this if you are travelling soon - your name must match your ticket.",
                "<strong>5. Everything else.</strong> Banks, employer and payroll, insurance, mortgage or lease, utilities, voter registration, loyalty accounts, medical records, your will.",
            ]),
            ("The honeymoon trap", [
                "Book travel in the name currently on your passport. If your ticket says your married name and your passport says your maiden name, you may not board.",
                "This is why most couples honeymoon first and change names afterwards, and it is worth deciding before tickets are booked rather than after.",
            ]),
            ("Your options are wider than two", [
                "Taking your partner's name, keeping your own, hyphenating, both partners changing to a combined name, or moving your maiden name to the middle are all available, and either partner can do any of them. Some states allow a name change on the marriage licence application itself, which is considerably simpler than a court petition.",
                "A change beyond what the marriage licence permits - inventing a new surname, for instance - generally requires a court order in most states. Check your state's rules before assuming.",
            ]),
        ],
        "practical": [
            ("Order three certified copies at once", "Almost every step wants to see one, and ordering again later costs more time than money."),
            ("Do Social Security before the DMV", "Everything downstream validates against that record. Out of order is the main reason this drags on for months."),
            ("Book the honeymoon in your current passport name", "A ticket that does not match your passport can stop you boarding. This is the single most common name-change mistake."),
            ("Check whether your state allows it on the licence", "Some do, which avoids a separate court petition entirely. Ask the county clerk when you apply."),
        ],
        "faqs": [
            ("What is the order for changing your name after marriage?",
             "Certified marriage certificate, then Social Security, then driver's licence, then passport, then banks and everything else. Each step validates against the previous one, and doing it out of order is why the process takes months for some people."),
            ("Can you travel on your honeymoon after changing your name?",
             "Book travel in the name currently on your passport. If the ticket and the passport disagree you may not be allowed to board, which is why most couples honeymoon first and change names afterwards."),
            ("Do you have to change your name after marriage?",
             "No. Keeping your name, hyphenating, both partners taking a combined name, or moving a maiden name to the middle are all options, and either partner can do any of them. Some states allow the change on the marriage licence application itself."),
        ],
    },
    # ------------------------------------------------------------ money & who pays
    "who-pays-for-the-wedding": {
        "question": "Who pays for the wedding?",
        "short": "Who pays for the wedding",
        "group": "Money & who pays",
        "cats": ["wedding-venues", "wedding-caterers", "wedding-planners"],
        "related": ["who-pays-for-the-rehearsal-dinner", "who-pays-for-the-bridal-shower", "cost"],
        "lede": "In the United States today, most weddings are paid for by some combination of the couple and both sets of parents, and the couple is usually the largest single contributor. The traditional split — the bride's family pays for nearly everything — describes almost nobody's wedding now, and treating it as the default is how these conversations go wrong.",
        "sections": [
            ("What the tradition actually said", [
                "The bride's family paid for the venue, catering, flowers, photography, music, invitations and the dress. The groom's family paid for the rehearsal dinner, the officiant's fee, the marriage licence and the honeymoon. The groom bought the rings.",
                "It is worth knowing because older relatives may still assume it, and because it explains why the rehearsal dinner is still frequently the groom's family's event. It is not worth following as a rule.",
            ]),
            ("How it usually works now", [
                "The most common arrangement is that the couple pays the largest share and each family contributes what they can and want to, often toward specific things — one set of parents takes the bar, the other takes the flowers. Couples marrying later, with established careers, frequently pay for everything themselves.",
                "The workable approach is to ask each contributing party for a number rather than a list. 'What are you comfortable contributing?' is a far easier conversation than assigning line items, and it avoids anyone feeling audited.",
            ]),
            ("Who pays in Mexican and Latin American weddings", [
                "The padrinos change the arithmetic entirely. Rather than one family funding the wedding, individual sponsors take individual elements — the padrinos de lazo buy the cord, the padrinos de arras the coins, and others may sponsor the cake, the flowers, the music or the bar. A large wedding can have a dozen sponsor pairs.",
                "Being asked is an honour and the expectation is often financial, which is exactly why the asking should be explicit. <a href=\"/traditions/padrinos-and-madrinas/\">How padrinos work, and how to ask</a> covers it properly.",
                "Filipino weddings use the same structure through principal and secondary sponsors, and many other cultures have their own versions. If either family comes from one of these traditions, the American default is not the starting point.",
            ]),
            ("Having the conversation", [
                "Have it early, before anything is booked, because a venue deposit changes what is negotiable. Ask each side separately and privately, so nobody is comparing in the room.",
                "Ask for a figure, not a promise to help. 'We'd like to contribute' is not a number, and building a budget on it is how couples end up short in the final month.",
                "Be clear about what a contribution buys in influence. Money frequently arrives with expectations about the guest list, and it is kinder to establish that up front than to discover it when somebody adds eleven names.",
            ]),
        ],
        "practical": [
            ("Get a number from each side before booking anything", "A venue deposit is the point after which the budget stops being theoretical. Have the conversations first."),
            ("Ask each family separately", "Privately and without comparison. Contributions differ, and a joint conversation makes that a competition."),
            ("Decide what a contribution buys in guest list", "Money usually arrives with expectations. Agreeing the number of guests each side invites, at the same time as the money, prevents the most common conflict in wedding planning."),
            ("Put it in your budget as a confirmed figure only", "Verbal 'we'll help' is not a line item. Until you have a number, plan without it."),
        ],
        "faqs": [
            ("Who traditionally pays for the wedding?",
             "Traditionally the bride's family paid for the venue, catering, flowers, photography, music, invitations and dress, while the groom's family paid for the rehearsal dinner, officiant, marriage licence and honeymoon. Almost nobody follows this split today."),
            ("Who pays for the wedding in Mexican culture?",
             "Padrinos - chosen sponsors - traditionally fund individual elements rather than one family funding everything. The padrinos de lazo buy the cord, the padrinos de arras the coins, and others sponsor the cake, flowers, music or bar. Being asked is an honour that usually carries a financial expectation, so the asking should be explicit."),
            ("How do you ask parents to pay for a wedding?",
             "Ask each side separately and privately, before anything is booked, and ask for a figure rather than a promise to help. Also agree at the same time what the contribution means for guest list input - money usually arrives with expectations."),
        ],
    },
    "who-pays-for-the-rehearsal-dinner": {
        "question": "Who pays for the rehearsal dinner?",
        "short": "Who pays for the rehearsal dinner",
        "group": "Money & who pays",
        "cats": ["wedding-caterers", "wedding-venues"],
        "related": ["rehearsal-dinner", "who-pays-for-the-wedding", "who-pays-for-the-bridal-shower"],
        "lede": "Traditionally the groom's family, and this is one of the few old conventions that has largely survived. Increasingly the couple hosts it themselves, or the two families split it — but if nobody has said otherwise, the groom's parents are the ones most people still expect to offer.",
        "sections": [
            ("Why this one survived", [
                "The traditional division gave the bride's family the wedding and the groom's family the rehearsal dinner. Even as the wedding half collapsed, the rehearsal dinner stayed attached, largely because it is a discrete event with a clear host rather than a shared pot.",
                "It also gives the groom's family a role that is genuinely theirs at a wedding weekend where much of the rest is not, which is a reason many families still like it.",
            ]),
            ("What it costs, and how the guest list drives it", [
                "The core list — wedding party, partners, immediate family, officiant — is usually 20 to 30 people. Adding all out-of-town guests, which is now common, can push it past 60 and turns a dinner into a second reception.",
                "Whoever is hosting should set the guest list, because they are setting the cost. The most common friction here is one family expanding the list for an event another family is paying for.",
            ]),
            ("If nobody offers", [
                "Ask directly rather than waiting. 'We're planning the rehearsal dinner — is that something you'd like to host, or should we?' is a complete, unembarrassing question, and it resolves in one conversation what can otherwise sit unspoken for months.",
                "Couples hosting it themselves is entirely normal now, as is splitting it. There is no version of this that anyone will judge.",
            ]),
        ],
        "practical": [
            ("Settle the host before the guest list", "Whoever pays sets the list, because the list sets the cost. Doing it the other way round is the usual source of friction."),
            ("Decide early whether out-of-town guests are invited", "It is the difference between a dinner for 25 and an event for 60, which means a different venue and a different budget."),
            ("Book the restaurant once the number is fixed", "Not before. Rehearsal dinner venues are booked on headcount and many have minimums."),
            ("Confirm the rehearsal slot with your ceremony venue first", "The dinner follows the rehearsal, and the rehearsal time is set by a venue that may have another event that evening."),
        ],
        "faqs": [
            ("Who traditionally pays for the rehearsal dinner?",
             "The groom's family. This is one of the few traditional divisions that largely survived, partly because it is a discrete event with a clear host and gives the groom's family a role of their own."),
            ("Who is invited to the rehearsal dinner?",
             "At minimum the wedding party and partners, immediate family, the officiant and anyone with a ceremony role - usually 20 to 30 people. Inviting all out-of-town guests is increasingly common but can push it past 60."),
            ("What if the groom's family doesn't offer to host the rehearsal dinner?",
             "Ask directly: 'We're planning the rehearsal dinner - is that something you'd like to host, or should we?' Couples hosting it themselves or splitting it is entirely normal now."),
        ],
    },
    "who-pays-for-the-bridal-shower": {
        "question": "Who pays for the bridal shower and bachelorette party?",
        "short": "Who pays for showers & parties",
        "group": "Money & who pays",
        "cats": ["wedding-venues", "wedding-caterers"],
        "related": ["who-pays-for-the-wedding", "who-pays-for-the-rehearsal-dinner", "wedding-party"],
        "lede": "The bridal shower is hosted and paid for by whoever throws it — traditionally the maid of honour and bridesmaids, sometimes a relative. The bachelorette is different: attendees pay their own way, and they usually cover the bride's share between them. Neither should be funded by the bride, and neither should quietly bankrupt anyone.",
        "sections": [
            ("The shower", [
                "The host pays. Traditionally that is the maid of honour and the bridal party together, sometimes with a mother, aunt or close family friend hosting instead. Costs are usually split among hosts rather than carried by one.",
                "Etiquette historically held that immediate family should not host a shower, since it looked like soliciting gifts for themselves. That has faded almost entirely and nobody will remark on it now.",
            ]),
            ("The bachelorette", [
                "Attendees pay their own travel, accommodation and activities, and it is customary for the group to split the bride's share so she is not paying for her own party. That is the convention; it is not an obligation on anyone who cannot afford it.",
                "This is where wedding party costs escalate hardest. A destination bachelorette can cost a bridesmaid more than the wedding gift, the dress and the travel to the wedding combined, and it is the most common reason people quietly decline to be in a wedding party.",
            ]),
            ("Keeping it from becoming a problem", [
                "Whoever is organising should circulate a realistic all-in cost early, before anyone books flights. A number in advance lets people opt out gracefully; a number that emerges in instalments does not.",
                "Offer a version people can join for less — one night instead of three, or the dinner without the weekend. The point is that everybody who loves her gets to be there, not that everybody spends the same.",
                "If you are the bride: say plainly that you would rather have people there than have an expensive trip. It is the single most useful thing you can do, and it has to come from you.",
            ]),
        ],
        "practical": [
            ("The host pays for the shower, not the bride", "Traditionally the maid of honour and bridesmaids, splitting it between them. A relative hosting is also entirely normal."),
            ("Circulate the bachelorette's full cost before anyone books", "All in - travel, accommodation, activities, the bride's share. People need one number early, not instalments."),
            ("Offer a cheaper way to take part", "One night rather than three, or dinner without the weekend. Attendance should not be means-tested."),
            ("Split the bride's share, but don't compel it", "It is the convention that the group covers her, but nobody should be pressured into a cost they cannot manage."),
        ],
        "faqs": [
            ("Who pays for the bridal shower?",
             "Whoever hosts it - traditionally the maid of honour and bridesmaids splitting the cost, sometimes a mother, aunt or family friend. The bride should not be paying for her own shower."),
            ("Who pays for the bachelorette party?",
             "Attendees pay their own way, and the group customarily splits the bride's share so she is not funding her own party. It is a convention rather than an obligation on anyone who cannot afford it."),
            ("Can the bride's mother host the bridal shower?",
             "Yes. The old etiquette that immediate family should not host - because it looked like soliciting gifts - has faded almost entirely and nobody will remark on it today."),
        ],
    },
    "wedding-dress-cost": {
        "question": "How much does a wedding dress cost?",
        "short": "What a wedding dress costs",
        "group": "Money & who pays",
        "cats": ["hair-and-makeup", "wedding-photographers"],
        "related": ["who-pays-for-the-wedding", "wedding-rings-cost", "cost"],
        "lede": "Most wedding dresses cost between $1,200 and $2,500, and the number that catches people out is alterations — commonly $300 to $800 on top, almost never included, and required on nearly every dress. Budget for the dress and the alterations as one figure or you will be surprised twice.",
        "sections": [
            ("What the ranges buy", [
                "Under $800: off-the-rack, sample sales, pre-owned, and increasingly good direct-to-consumer labels. Pre-owned in particular is an underused market — a dress worn once for eight hours, at half price.",
                "$1,200–$2,500: the range most couples land in. Bridal-salon labels, ordered to your size from a size chart, delivered in four to six months.",
                "$2,500–$8,000+: designer labels, heavy beadwork, silk rather than synthetics, and made-to-measure or couture at the top.",
            ]),
            ("Alterations, which nobody budgets", [
                "Almost every dress needs them, because bridal is ordered from a size chart rather than fitted. A hem, a bustle and side seams commonly run $300 to $800, and more for beaded fabrics where every alteration means hand-removing and re-applying beadwork.",
                "You will usually have two to three fittings across six to eight weeks. Book the first one three months out, and do not lose weight deliberately between fittings — alterations are cut to the body at the time.",
            ]),
            ("The rest of the number", [
                "Veil, shoes, undergarments and jewellery add $200 to $800 for most people. Preservation and cleaning afterwards is another $150 to $400 if you want it.",
                "Shopping timeline matters more than any negotiation: ordered dresses take four to six months to arrive plus two for alterations, so start eight to ten months out. Rush fees for a late order are real and steep.",
            ]),
        ],
        "practical": [
            ("Budget the dress and alterations as one number", "Alterations are $300-$800 on almost every dress and are essentially never included in the price you are quoted."),
            ("Start shopping eight to ten months out", "Four to six months to arrive, plus two for fittings. Rush fees for a late order are steep and avoidable."),
            ("Consider pre-owned seriously", "A dress worn once for eight hours at roughly half price is the single biggest saving available in this category."),
            ("Tell your hair and makeup artist the neckline", "It genuinely changes what suits you, and they will ask at the trial - bring a photograph."),
        ],
        "faqs": [
            ("How much does a wedding dress cost on average?",
             "Most wedding dresses cost $1,200 to $2,500, with off-the-rack and pre-owned options under $800 and designer or couture from $2,500 to $8,000 and beyond. Alterations of $300 to $800 are additional and almost always required."),
            ("Are alterations included in the price of a wedding dress?",
             "Almost never. Bridal dresses are ordered from a size chart rather than fitted, so nearly every one needs altering - commonly $300 to $800, and more for beaded fabrics where beadwork must be removed and reapplied by hand."),
            ("How far in advance should you buy a wedding dress?",
             "Eight to ten months before the wedding. Ordered dresses take four to six months to arrive, and alterations need another two months across two or three fittings."),
        ],
    },
    "wedding-rings-cost": {
        "question": "How much does a wedding ring cost?",
        "short": "What rings cost",
        "group": "Money & who pays",
        "cats": ["wedding-invitations"],
        "related": ["wedding-dress-cost", "who-pays-for-the-wedding", "cost"],
        "lede": "Wedding bands typically cost $500 to $1,500 each, and engagement rings $2,000 to $8,000 depending almost entirely on the centre stone. The 'two months' salary' rule is not a tradition — it was an advertising slogan written by De Beers in the 1930s, and it is worth knowing that before budgeting around it.",
        "sections": [
            ("Bands", [
                "A plain gold or platinum band runs $300 to $1,000 depending on metal and width; platinum costs meaningfully more than gold and is heavier and more durable. Diamond-set or patterned bands run $1,000 to $3,000.",
                "Metal choice matters more practically than aesthetically: platinum and gold scratch differently, and if one of you works with your hands, say so in the shop. A jeweller will steer you well if they know.",
            ]),
            ("Engagement rings, and where the money goes", [
                "The centre stone is nearly the entire price. A natural one-carat diamond of decent quality commonly runs $4,000 to $8,000; the same stone lab-grown is frequently 60 to 80% less, is chemically identical, and is now a mainstream choice rather than a compromise.",
                "Setting, metal and side stones add a few hundred to a couple of thousand. Cut matters more than carat for how a stone actually looks, and is the place to spend if you are choosing where to spend.",
                "Sapphires, emeralds and other coloured stones cost substantially less at comparable size and are increasingly common.",
            ]),
            ("The two months' salary thing", [
                "It is a De Beers advertising campaign from the 1930s, later revised upward to three months. It has no traditional basis whatsoever and exists to make a number feel like an obligation.",
                "Spend what you can comfortably spend. Nobody at your wedding will know the price of the ring, and the people who ask are not people to budget around.",
            ]),
        ],
        "practical": [
            ("Buy the bands together and early", "Sizing and engraving take two to four weeks, and it is one fewer thing in the final month."),
            ("Ask about lab-grown before assuming natural", "Chemically identical, commonly 60-80% less, and now entirely mainstream. It is the largest saving in this category."),
            ("Tell the jeweller what you do with your hands", "It should change the metal and the setting they recommend. A raised setting on someone who works manually is a repair waiting to happen."),
            ("Insure them, and do it immediately", "Usually a rider on home contents insurance and inexpensive. Rings are lost and stolen far more often than couples expect."),
        ],
        "faqs": [
            ("How much does a wedding ring cost on average?",
             "Wedding bands typically cost $500 to $1,500 each - $300 to $1,000 for a plain gold or platinum band, more for diamond-set or patterned designs. Engagement rings usually run $2,000 to $8,000 depending on the centre stone."),
            ("Is the two months' salary rule real?",
             "No. It was a De Beers advertising slogan from the 1930s, later revised upward to three months. It has no traditional basis and exists to make a number feel obligatory."),
            ("Are lab-grown diamonds worth it?",
             "They are chemically identical to natural diamonds and commonly cost 60-80% less, which makes them the single largest saving available in this category. They are now a mainstream choice rather than a compromise."),
        ],
    },
    # ------------------------------------------------------------ the wedding party
    "maid-of-honor-duties": {
        "question": "What are the maid of honor's duties?",
        "short": "Maid of honor duties",
        "group": "The wedding party",
        "cats": ["hair-and-makeup", "day-of-coordination", "wedding-photographers"],
        "related": ["bridesmaid-duties", "best-man-duties", "wedding-party"],
        "lede": "The maid of honour's real job is not on the list anyone hands you. It is to be the person who notices what is going wrong before the bride does, and to handle it without telling her. Everything else — the shower, the speech, the dress, the signature — is scheduling.",
        "sections": [
            ("Before the wedding", [
                "Host or co-host the bridal shower with the bridesmaids, and organise the bachelorette — including circulating an honest all-in cost early so nobody is surprised. Coordinate the bridesmaids on dresses, fittings, hair and makeup timings, and payment.",
                "Be the person the bride can complain to. Much of this role is absorbing stress rather than adding to it, and the most useful thing you can say in most months is 'I'll handle it.'",
            ]),
            ("On the day", [
                "Get her fed and watered, hold the bouquet, fix the dress, manage the bustle after the ceremony — learn it at a fitting, because nobody can work one out in a bathroom at 9pm. Keep the phone, the lipstick and the emergency kit.",
                "Sign the marriage licence as a witness if you have been asked. Give the speech. Then watch the room: for the relative who needs a seat, the vendor who needs an answer, the thing the bride would be dealing with if you were not.",
            ]),
            ("What the role does not require", [
                "Paying for things you cannot afford. If the dress, the travel and the bachelorette exceed your budget, say so early and privately — a good friend would rather know than have you quietly absorb it.",
                "Being a wedding planner. If the wedding needs coordination, that is a coordinator's job, and suggesting one is more useful than attempting it yourself.",
            ]),
        ],
        "practical": [
            ("Learn the bustle at a fitting", "Genuinely the most useful five minutes of preparation in this role. Take a photograph of it."),
            ("Get the vendor contact list from the coordinator", "So you can answer a question without waking the bride's mother."),
            ("Circulate bachelorette costs before anyone books", "One honest number early, not instalments. It is the main reason people decline this role."),
            ("Time your speech and cut it to five minutes", "Read it aloud twice. Nerves accelerate everyone, and eleven minutes is the default failure."),
        ],
        "faqs": [
            ("What does the maid of honor actually do?",
             "Hosts or co-hosts the shower, organises the bachelorette, coordinates the bridesmaids, gives a speech, signs as a witness if asked, and on the day handles the dress, the bustle and anything going wrong - ideally before the bride notices."),
            ("Does the maid of honor have to pay for the bachelorette?",
             "No. Attendees pay their own way and the group customarily splits the bride's share. If the combined cost of dress, travel and bachelorette exceeds your budget, say so early and privately."),
            ("Does the maid of honor have to give a speech?",
             "It is customary but not compulsory, and a good friend will not force it. If you are giving one, five minutes with a single story beats a list of memories."),
        ],
    },
    "bridesmaid-duties": {
        "question": "What are a bridesmaid's duties?",
        "short": "Bridesmaid duties",
        "group": "The wedding party",
        "cats": ["hair-and-makeup", "wedding-photographers"],
        "related": ["maid-of-honor-duties", "best-man-duties", "wedding-party"],
        "lede": "Buy the dress, turn up to the things, and on the day be useful without being asked. That is genuinely most of it. The rest is being someone the bride does not have to manage in a month when she is managing everything.",
        "sections": [
            ("What you are committing to", [
                "A dress you pay for, usually $100 to $300, plus alterations. Hair and makeup, which may or may not be covered — ask when you accept. Travel to the wedding and often to a bachelorette. Attendance at the shower, the rehearsal and the rehearsal dinner.",
                "Ask about all of it at the point of accepting, including who pays for what. It is a completely normal question and the awkwardness of asking is far smaller than the awkwardness of discovering later.",
            ]),
            ("On the wedding day", [
                "Arrive when you are told, not when you are ready. The morning schedule is built backwards from when photographs start and one late arrival moves everything.",
                "Eat breakfast, drink water, and pace the champagne. The wedding party member who peaks at 3pm is a genre.",
                "Watch for what needs doing: a grandmother who needs a chair, a flower child who has stopped walking, a bride who needs the bathroom in a large dress. Nobody will ask you.",
            ]),
            ("Saying no, or saying less", [
                "You can decline. Being asked is a compliment, not a summons, and a friend who cannot afford a destination bachelorette and a $280 dress should say so rather than going into debt quietly.",
                "You can also negotiate. 'I can do the wedding and the shower but not the bachelorette weekend' is a reasonable sentence between friends, and it is far better said in March than in July.",
            ]),
        ],
        "practical": [
            ("Ask what it will cost when you accept", "Dress, alterations, hair, makeup, travel, bachelorette. All of it, at the start."),
            ("Order the dress the week you are asked to", "Bridal-party dresses ship on the same long timelines as wedding dresses, and a late order delays everyone's alterations."),
            ("Arrive at the time you are given", "The morning runs backwards from photographs. One late arrival moves the whole schedule."),
            ("Bring flats and a phone charger", "You will be standing for nine hours, and somebody's phone is running something important."),
        ],
        "faqs": [
            ("What are bridesmaids responsible for?",
             "Buying the dress and paying for alterations, attending the shower, rehearsal and rehearsal dinner, usually the bachelorette, and on the wedding day being useful without being asked - arriving on time, staying fed and watching for what needs doing."),
            ("Do bridesmaids pay for their own hair and makeup?",
             "Sometimes, and sometimes the couple covers it. Both are entirely normal - which is why you should ask at the point of accepting rather than assuming."),
            ("Can you say no to being a bridesmaid?",
             "Yes. Being asked is a compliment rather than a summons, and declining early - or negotiating which events you can afford - is far better than quietly going into debt over it."),
        ],
    },
    "best-man-duties": {
        "question": "What are the best man's duties?",
        "short": "Best man duties",
        "group": "The wedding party",
        "cats": ["wedding-djs", "day-of-coordination", "wedding-transportation"],
        "related": ["maid-of-honor-duties", "bridesmaid-duties", "wedding-speeches"],
        "lede": "Hold the rings, give the speech, organise the bachelor party, and on the day keep the groom fed, on time and calm. The two things that actually go wrong in this role are a speech nobody timed and a ring nobody can find, and both are entirely preventable.",
        "sections": [
            ("Before the day", [
                "Organise the bachelor party, including circulating a realistic all-in cost early so people can opt out gracefully. Coordinate the groomsmen on suits, fittings and collection — rented suits in particular have a pickup and a return date, and the return is the one that gets forgotten.",
                "Write the speech properly, more than a week out. One story, five minutes, timed aloud twice. Cut anything about ex-partners or drinking, and anything only four people will understand.",
            ]),
            ("On the day", [
                "Keep the rings — in a pocket that buttons, and check it more than once. Get the groom to the venue early. Make sure he eats, which he will not do on his own.",
                "Sign as a witness if asked. Give the speech. Then take on the jobs that otherwise land on the couple: paying and tipping vendors from envelopes prepared in advance, returning rented suits, getting the gifts and the cake topper home.",
            ]),
            ("The speech, specifically", [
                "This is the part people remember and the part most commonly done badly. Five minutes. One story with a beginning and an end. Turn it to say something true about them, then toast clearly so the room knows to raise a glass.",
                "Read it aloud, timed, twice. Unbriefed speakers routinely run eleven minutes, and the room is always kinder to a short speech than to a complete one.",
            ]),
        ],
        "practical": [
            ("Put the rings in a pocket that buttons", "And check it twice. A ring in an open pocket is the single most preventable disaster in this role."),
            ("Confirm who returns rented suits, and when", "Rentals have a return date and a late fee, and it is the job that gets forgotten on the Monday."),
            ("Take the vendor payment envelopes", "Prepared by the couple in advance. It is a real job that otherwise lands on them or a parent at midnight."),
            ("Time the speech out loud, twice", "Five minutes. Nerves make everyone faster and longer at the same time."),
        ],
        "faqs": [
            ("What does the best man do on the wedding day?",
             "Keeps the rings, gets the groom there early and fed, signs as a witness if asked, gives the speech, and handles jobs that would otherwise fall to the couple - vendor payments, returning rented suits and getting gifts home."),
            ("How long should a best man speech be?",
             "Five minutes. One story with a beginning and an end, turned to say something true about the couple, then a clear toast. Unbriefed speakers routinely run eleven minutes."),
            ("Who pays for the bachelor party?",
             "Attendees pay their own way and usually split the groom's share. The best man should circulate a realistic all-in cost early so people can decline gracefully rather than discovering the total in instalments."),
        ],
    },
}

# JC-LAZO-WWSEO-0919-007: the wedding-website guides live beside this file
from config.planning_websites import WEBSITE_GUIDES
PLANNING.update(WEBSITE_GUIDES)
from config.planning_apps import APP_GUIDES  # JC-LAZO-PLAN-0922-001: "Your tools"
PLANNING.update(APP_GUIDES)
