"""Wedding guest guides.  JC-LAZO-GUEST-0917-001

/guests/ and /guests/<slug>/. The fifth content cluster, and the first one
written for somebody other than the couple.

WHY IT EXISTS. We wrote 101 pages for people planning a wedding and none for
people attending one. Then we pulled Google's own autocomplete for a set of
seeds, and four of the top nine suggestions for "is it rude to" - across all
searches, not wedding searches - were wedding guest questions:

    is it rude to wear black to a wedding
    is it rude to wear red to a wedding
    is it rude to wear white to a wedding
    is it rude to leave a wedding early

Guests outnumber couples at every wedding by roughly a hundred to one, they are
anxious about getting it wrong, and they search in complete sentences. We had
nothing for them.

HOW THESE ARE WRITTEN. Differently from every other cluster. A guest searching
"can I wear black to a wedding" wants the answer in two seconds, not an essay,
so `answer` is a direct verdict in the first line and the page earns its length
underneath. Hedging at the top of these pages is a failure.

They also carry the one thing a generic etiquette site cannot: our traditions
cluster. "Can I wear red" has a different answer at a Chinese or Indian wedding,
where red is the celebratory colour, than at a Western one - and we have 45
pages explaining exactly those weddings to link to.

Schema per guide:
  question  the search, verbatim where it reads naturally
  short     card label
  group     hub section
  answer    the verdict, first line, no hedging
  sections  [(h2, [paragraph, ...])]
  quick     [(situation, what to do)] - the scannable decision table
  faqs      [(q, a)] for FAQPage schema
  related   sibling slugs; "traditions" and "planning" hubs allowed. The colour
            pages point at /traditions/ deliberately - "can I wear red" has a
            different answer at a Chinese or Indian wedding, and we have 45
            pages explaining those weddings that a generic etiquette site does not.
"""

GUESTS = {
    # ---------------------------------------------------------------- attire
    "what-to-wear-to-a-wedding": {
        "related": ['wedding-dress-codes-explained', 'can-you-wear-black-to-a-wedding', 'can-you-wear-white-to-a-wedding'],
        "question": "What should you wear to a wedding?",
        "short": "What to wear",
        "group": "What to wear",
        "answer": "Follow the dress code on the invitation, and if there isn't one, assume cocktail attire: a knee-length or midi dress, or a suit and tie. Avoid white, avoid anything that reads as more formal than the couple, and check the venue — a barn in October and a ballroom in June ask for different shoes.",
        "sections": [
            ("When there is no dress code", [
                "Look at three things: the venue, the time, and the season. An evening reception at a hotel is dressier than a 2pm garden ceremony. A barn, a beach or a backyard all mean flat or block heels rather than stilettos, whatever the invitation says.",
                "When genuinely unsure, cocktail attire is the safe middle for almost every wedding in the United States. It is hard to be criticised for it, and being slightly overdressed reads as respectful in a way that being underdressed does not.",
            ]),
            ("The things that actually cause offence", [
                "White, ivory, cream or champagne, unless the couple has explicitly invited it. This is the one rule with almost no exceptions.",
                "Anything that upstages — a floor-length gown at a casual wedding, a veil-adjacent headpiece, or a dress so attention-getting that it becomes the topic.",
                "Wearing the wedding party's colour, if you know it. Not a rule, but it produces confused photographs.",
            ]),
            ("Practical things people forget", [
                "Outdoor ceremonies mean grass, and grass means heels sink. Block heels, wedges or flats are the answer, and plenty of guests bring a second pair for dancing.",
                "Churches and many religious venues expect covered shoulders. A wrap in your bag solves it and weighs nothing.",
                "Receptions run cold from air conditioning and outdoor evenings run colder. Something over your shoulders is the most reliably useful thing you will bring.",
            ]),
        ],
        "quick": [
            ("Invitation says black tie", "Floor-length gown or a tuxedo. This one is not flexible."),
            ("Invitation says cocktail", "Knee-length or midi dress, or a suit and tie."),
            ("No dress code given", "Cocktail attire, adjusted for venue and time of day."),
            ("Outdoor or barn venue", "Block heels or flats, and something warm for the evening."),
            ("Religious ceremony", "Covered shoulders, knees covered, and a scarf if heads are covered."),
        ],
        "faqs": [
            ("What do you wear to a wedding if there is no dress code?",
             "Cocktail attire is the safe default: a knee-length or midi dress, or a suit and tie. Adjust for the venue and the time - an evening hotel reception is dressier than an afternoon garden ceremony."),
            ("What should you never wear to a wedding?",
             "White, ivory, cream or champagne, unless the couple has specifically said otherwise. Beyond that, avoid anything that upstages the couple or reads as considerably more formal than the event itself."),
            ("Can you wear a long dress to a wedding as a guest?",
             "Yes, particularly for black tie or formal evening weddings. At a casual daytime wedding a floor-length gown may feel out of step with the room, but it is a question of fit rather than a rule."),
        ],
    },
    "can-you-wear-black-to-a-wedding": {
        "related": ['can-you-wear-white-to-a-wedding', 'can-you-wear-red-to-a-wedding', 'wedding-dress-codes-explained'],
        "question": "Is it rude to wear black to a wedding?",
        "short": "Wearing black",
        "group": "What to wear",
        "answer": "No. Black is completely acceptable at weddings now, and at a formal or evening wedding it is one of the best choices you can make. The old rule — that black signalled mourning and was therefore an insult — has been gone for decades in most of the United States and Europe.",
        "sections": [
            ("Where the rule came from, and why it went", [
                "Black was the colour of mourning, and wearing it to a celebration read as a comment on the marriage. That association faded through the twentieth century as black became the default colour of evening formality, and a black cocktail dress is now among the most common things a wedding guest wears.",
                "If anyone still objects, it will be a much older relative, and it will be a private opinion rather than a scene. It is not something to reorganise your outfit around.",
            ]),
            ("Where it is still worth thinking twice", [
                "At some traditional Catholic, Orthodox and Southern Baptist weddings, and among some older families, the association lingers. If you know the family holds it, choose navy or deep green and the question disappears.",
                "At many <a href='/traditions/chinese-tea-ceremony/'>Chinese</a>, <a href='/traditions/saptapadi/'>Indian</a> and other Asian weddings, black carries stronger associations with mourning and is genuinely better avoided — red, gold and bright colours are celebratory. This is the one context where the old rule still meaningfully applies.",
                "A summer afternoon garden wedding is the other case: black is not rude, just heavy. It is a question of the room rather than of respect.",
            ]),
            ("How to wear it well", [
                "Treat it as a colour rather than a default. Texture, a bright accessory, or a fabric with some life to it reads as dressed for a wedding; a plain matte sheath can read as dressed for work.",
                "At a black tie wedding, black is arguably the correct answer rather than merely a permitted one.",
            ]),
        ],
        "quick": [
            ("Formal or evening wedding", "Wear black. It is ideal."),
            ("Black tie", "Black is close to the expected answer."),
            ("Daytime garden or beach wedding", "Fine, but lighter colours suit the setting better."),
            ("Chinese, Indian or other Asian wedding", "Avoid black. Choose red, gold or another bright colour."),
            ("You know the family is traditional about it", "Navy or deep green gets you the same look with no question."),
        ],
        "faqs": [
            ("Is it rude to wear black to a wedding?",
             "No. Black is entirely acceptable at weddings today and is an excellent choice for formal or evening celebrations. The mourning association faded decades ago in most of the US and Europe."),
            ("When should you not wear black to a wedding?",
             "At many Chinese, Indian and other Asian weddings, where black is associated with mourning and bright colours are celebratory. Also worth avoiding if you know the family holds the older tradition - navy or deep green is an easy substitute."),
            ("Can you wear black to a black tie wedding?",
             "Yes, and it is close to the expected choice. Black tie is where black is most clearly correct rather than merely allowed."),
        ],
    },
    "can-you-wear-white-to-a-wedding": {
        "related": ['can-you-wear-black-to-a-wedding', 'can-you-wear-red-to-a-wedding', 'what-to-wear-to-a-wedding'],
        "question": "Is it rude to wear white to a wedding?",
        "short": "Wearing white",
        "group": "What to wear",
        "answer": "Yes — don't. This is the one wedding guest rule that genuinely still holds. Unless the couple has explicitly asked guests to wear white, avoid white, ivory, cream, champagne and blush-that-photographs-white.",
        "sections": [
            ("Why this one survived when the others didn't", [
                "Most etiquette rules faded because their original reasoning stopped applying. This one persists for a practical reason that has not changed: in photographs, the person in white is the bride, and a guest in an off-white dress genuinely creates confusion in images the couple keeps forever.",
                "It costs you nothing to avoid, which is the other half of why it survives. There is no outfit you cannot assemble in another colour.",
            ]),
            ("The colours that catch people out", [
                "Ivory, cream, champagne, oyster, bone and very pale blush all photograph as white under flash, even when they clearly are not white in the room. If you have to hold it up to a window to decide, choose something else.",
                "A print with a white background is the common grey area. A mostly-white floral dress reads as white from across a room. Prints where the pattern dominates are fine.",
                "White separates — a white shirt with a coloured skirt, or a white blazer — are generally fine, because the silhouette does not read as a dress.",
            ]),
            ("When white is actually requested", [
                "Some couples ask for all-white guests, particularly at destination and beach weddings, and a few cultures have their own conventions. If the invitation or wedding website says white, wear white with confidence.",
                "At many <a href='/traditions/chinese-tea-ceremony/'>Chinese</a> and <a href='/traditions/saptapadi/'>Indian</a> weddings white is associated with mourning and funerals — a stronger reason to avoid it than the Western one.",
            ]),
        ],
        "quick": [
            ("Any standard Western wedding", "Avoid white, ivory, cream, champagne and pale blush."),
            ("The couple asked for white", "Wear white. Follow the invitation."),
            ("Mostly-white floral print", "Risky. Choose one where the pattern dominates."),
            ("White shirt or blazer with colour", "Generally fine - the silhouette does not read as a dress."),
            ("Chinese or Indian wedding", "Avoid white entirely; it is associated with mourning."),
        ],
        "faqs": [
            ("Can wedding guests wear white?",
             "No, unless the couple has specifically asked for it. Avoid white, ivory, cream, champagne and very pale blush - all of which photograph as white under flash even when they do not look white in person."),
            ("Is ivory the same as white for a wedding guest?",
             "For this purpose, yes. Ivory, cream, champagne and bone all read as white in photographs, which is the actual reason the rule exists."),
            ("Can you wear a white floral dress to a wedding?",
             "Only if the pattern dominates. A mostly-white floral reads as a white dress from across a room and in photographs."),
        ],
    },
    "can-you-wear-red-to-a-wedding": {
        "related": ['traditions', 'can-you-wear-white-to-a-wedding', 'what-to-wear-to-a-wedding'],
        "question": "Is it rude to wear red to a wedding?",
        "short": "Wearing red",
        "group": "What to wear",
        "answer": "At a Western wedding, no — red is fine, though it is attention-getting and worth a moment's thought. At a Chinese or Indian wedding the answer flips entirely: red is the bride's colour, and wearing it is closer to wearing white at a Western wedding.",
        "sections": [
            ("The Western answer", [
                "There is no rule against red. The hesitation people feel comes from a vague sense that red is 'too much' - and the honest version of that is that a bright red dress draws the eye, which at somebody else's wedding is worth being deliberate about rather than avoiding.",
                "Deeper reds - burgundy, wine, oxblood - carry none of that and are among the best autumn and winter wedding colours available to a guest.",
            ]),
            ("Where red is the bride's colour", [
                "At a <a href='/traditions/chinese-tea-ceremony/'>Chinese wedding</a>, red is the colour of luck and celebration, and the bride commonly wears a red qipao or a red gown for part of the day. A guest in bright red is stepping into that.",
                "At many <a href='/traditions/mehndi-ceremony/'>Indian and South Asian weddings</a> the bride's lehenga is traditionally red or deep pink. The same logic applies, and the safest choice as a guest is any other bright colour - jewel tones are welcome and white and black are the ones to avoid.",
                "When you are invited to a wedding in a tradition you do not know, the wedding website or one question to whoever invited you resolves it in thirty seconds. Asking is never the rude part.",
            ]),
        ],
        "quick": [
            ("Western wedding", "Red is fine. Deep reds are especially good in autumn and winter."),
            ("Chinese wedding", "Avoid red - it is the bride's colour. Choose another bright colour."),
            ("Indian or South Asian wedding", "Avoid red and deep pink. Jewel tones are welcome; avoid white and black."),
            ("Not sure which tradition", "Ask whoever invited you, or check the wedding website."),
        ],
        "faqs": [
            ("Can you wear red to a wedding?",
             "At a Western wedding, yes - there is no rule against it, though bright red is attention-getting. At a Chinese or Indian wedding, avoid it: red is traditionally the bride's colour."),
            ("What colour should you not wear to an Indian wedding?",
             "Red and deep pink, because they are traditionally the bride's colours, plus white and black, which are associated with mourning. Bright jewel tones are welcome and expected."),
            ("Is burgundy okay to wear to a wedding?",
             "Yes. Deeper reds like burgundy, wine and oxblood carry none of the attention-getting quality of bright red and are excellent autumn and winter guest colours."),
        ],
    },
    "wedding-dress-codes-explained": {
        "related": ['what-to-wear-to-a-wedding', 'wedding-guest-etiquette', 'can-you-wear-black-to-a-wedding'],
        "question": "What does black tie optional mean?",
        "short": "Dress codes explained",
        "group": "What to wear",
        "answer": "Black tie optional means a tuxedo is welcome but a dark suit and tie is equally correct, and for women a floor-length gown, a formal midi or dressy separates all work. It is the couple saying they want a formal evening without requiring anyone to rent a tuxedo.",
        "sections": [
            ("The codes, from most to least formal", [
                "<strong>White tie.</strong> Rare. Tailcoat, white waistcoat and bow tie; floor-length ball gown. If you are invited to one, the invitation will make it unmistakable.",
                "<strong>Black tie.</strong> Tuxedo required; floor-length gown or a very formal midi. Not a suggestion.",
                "<strong>Black tie optional</strong> or <strong>formal.</strong> Tuxedo welcome, dark suit and tie equally fine. Gown, formal midi, or dressy separates.",
                "<strong>Cocktail.</strong> The most common code in the US. Suit and tie; knee-length or midi dress. Not floor-length, not a sundress.",
                "<strong>Dressy casual</strong> or <strong>semi-formal.</strong> Sport coat, no tie required; a nice dress or smart separates.",
                "<strong>Casual.</strong> Still means smart. Chinos and a collared shirt, a sundress. Never jeans unless the couple has said jeans.",
            ]),
            ("The invented ones", [
                "Garden party, beach formal, festive, dusty-blue-and-sage - couples increasingly write their own. These are aesthetic requests rather than formality levels, and the reliable move is to read the formality from the venue and time, then apply their colour or mood note on top.",
                "'Festive' almost always means cocktail attire with something celebratory about it. 'Beach formal' means formal fabrics and flat shoes. 'Garden party' means cocktail with a print and a shoe that survives grass.",
            ]),
            ("When in doubt", [
                "Check the couple's wedding website, which usually elaborates. If it does not, dress to the more formal reading — being slightly overdressed at a wedding is invisible, and being underdressed is not.",
            ]),
        ],
        "quick": [
            ("White tie", "Tailcoat; floor-length ball gown."),
            ("Black tie", "Tuxedo required; floor-length or very formal midi."),
            ("Black tie optional", "Tuxedo or dark suit; gown, formal midi or dressy separates."),
            ("Cocktail", "Suit and tie; knee-length or midi dress."),
            ("Dressy casual", "Sport coat, no tie needed; nice dress or smart separates."),
            ("Casual", "Smart, never jeans unless the couple said jeans."),
        ],
        "faqs": [
            ("What does black tie optional mean for a guest?",
             "A tuxedo is welcome but a dark suit and tie is equally correct. For women, a floor-length gown, a formal midi or dressy separates all work. The couple wants a formal evening without requiring anyone to rent a tuxedo."),
            ("What does cocktail attire mean for a wedding?",
             "A suit and tie, or a knee-length or midi dress. It is the most common dress code at American weddings - dressier than a sundress, less formal than a floor-length gown."),
            ("What does festive attire mean at a wedding?",
             "Almost always cocktail attire with something celebratory about it - colour, sparkle or pattern. It is an aesthetic request rather than a formality level."),
        ],
    },
    # ---------------------------------------------------------------- gifts
    "how-much-to-give-for-a-wedding-gift": {
        "related": ['wedding-registry-etiquette', 'wedding-guest-etiquette', 'wedding-rsvp-etiquette'],
        "question": "How much should you give for a wedding gift?",
        "short": "How much to give",
        "group": "Gifts",
        "answer": "Most guests give between $75 and $200, with $100–$150 the most common single figure. Give what your budget allows — the widely repeated rule that you should 'cover your plate' is not real etiquette, and no couple worth attending is auditing what you spent.",
        "sections": [
            ("What people actually give", [
                "A rough and honest range: $50–$100 from a colleague or a distant friend, $100–$150 from a friend, $150–$300 from close friends and family, and more from immediate family who want to and can. Couples attending together frequently give one combined gift rather than doubling.",
                "Where you live moves the number. Large-city weddings see higher averages than rural ones, and some communities and cultures have their own conventions, particularly where cash is the norm.",
            ]),
            ("The 'cover your plate' myth", [
                "The idea that your gift should equal what the couple spent per head is not etiquette and never was. It was invented by people guessing, and it produces the perverse result that being invited to an expensive wedding costs you more.",
                "You were invited because they want you there, not to fund the catering. If your budget is $60, give $60 without apology.",
            ]),
            ("Cash, registry, or something else", [
                "Follow the registry if there is one — couples build it around what they need, and buying off it is never wrong. If there is a cash or honeymoon fund, that is an explicit statement of preference and it is fine to use it.",
                "In many communities cash is simply the norm, given in an envelope at the reception. Italian, Chinese, Korean, Filipino and Polish weddings among many others have long-standing versions of this, and following the local custom is the courteous move.",
                "Handmade or personal gifts are welcome when they are genuinely thoughtful and not a way to spend less while appearing to spend more.",
            ]),
        ],
        "quick": [
            ("Colleague or distant friend", "$50-$100"),
            ("Friend", "$100-$150"),
            ("Close friend or family", "$150-$300"),
            ("Attending as a couple", "One combined gift is normal, not double"),
            ("Can't afford much", "Give less, without apology. A card and a small gift is fine."),
            ("Invited but not attending", "A gift is a kind gesture but is not required."),
        ],
        "faqs": [
            ("How much money should you give for a wedding?",
             "Most guests give $75 to $200, with $100 to $150 the most common amount. Close friends and family often give more. Give what your budget allows rather than what you think is expected."),
            ("Do you have to cover your plate with a wedding gift?",
             "No. The idea that your gift should match what the couple spent per head is not real etiquette - it was invented by guesswork, and it wrongly implies an expensive wedding obliges you to spend more."),
            ("Do you give a gift if you can't attend the wedding?",
             "It is a kind gesture and often appreciated, but it is not required. A card with your congratulations is entirely sufficient if you are not attending."),
        ],
    },
    "wedding-registry-etiquette": {
        "related": ['how-much-to-give-for-a-wedding-gift', 'wedding-guest-etiquette', 'wedding-rsvp-etiquette'],
        "question": "Do you have to buy off the wedding registry?",
        "short": "Registry etiquette",
        "group": "Gifts",
        "answer": "No, but you probably should. A registry is the couple telling you exactly what they want, and buying off it is the single most reliable way to give something useful. Going off-registry works when you know them well and have thought about it — not when you simply prefer your own idea.",
        "sections": [
            ("Why registries are worth following", [
                "Couples build registries around gaps in their home and a spread of prices so guests can spend what suits them. Buying off it guarantees the gift is wanted, not duplicated, and the right size and colour.",
                "The most common off-registry mistake is a decorative object chosen to your taste rather than theirs. It will be displayed when you visit and stored the rest of the time, and everyone involved knows it.",
            ]),
            ("Cash funds and honeymoon registries", [
                "If a couple has set up a honeymoon or house fund, they have told you plainly what they need. Contributing to it is not lazy and is frequently more useful than an object.",
                "Contributions are usually visible to the couple by name and amount but not to other guests. Give what you would have spent on a physical gift.",
            ]),
            ("Timing and delivery", [
                "Ship to the address on the registry rather than bringing a boxed gift to the venue. Somebody has to carry everything home at midnight, and it is usually a parent.",
                "Gifts are traditionally welcome up to a year after the wedding, though sooner is kinder - a gift arriving in March is harder to include in the thank-you notes the couple is trying to finish.",
            ]),
        ],
        "quick": [
            ("Registry exists", "Buy from it. It is the safest and most useful choice."),
            ("Everything in your budget is taken", "Group with other guests on a larger item, or give cash."),
            ("Honeymoon or cash fund", "Contribute. It is an explicit request."),
            ("You want to go off-registry", "Only if you know them well and have genuinely thought about it."),
            ("Delivering the gift", "Ship to the registry address, not the venue."),
        ],
        "faqs": [
            ("Is it rude to not buy from the wedding registry?",
             "Not rude, but the registry is the couple telling you what they actually want. Going off-registry works when you know them well and have thought carefully; it goes wrong when you simply prefer your own idea."),
            ("Should you bring the gift to the wedding?",
             "Ship it to the address on the registry instead. Physical gifts brought to the venue have to be carried home at the end of the night, usually by a parent."),
            ("How long do you have to send a wedding gift?",
             "Gifts are traditionally welcome up to a year after the wedding, but sooner is considerably kinder - a late gift arrives after the couple has finished their thank-you notes."),
        ],
    },
    # ---------------------------------------------------------------- behaviour
    "is-it-rude-to-leave-a-wedding-early": {
        "related": ['wedding-guest-etiquette', 'wedding-rsvp-etiquette', 'what-to-wear-to-a-wedding'],
        "question": "Is it rude to leave a wedding early?",
        "short": "Leaving early",
        "group": "At the wedding",
        "answer": "Not if you stay past the key moments and say goodbye properly. The reasonable minimum is the ceremony, dinner, the toasts and the first dance. After that, leaving quietly is entirely acceptable and nobody will notice.",
        "sections": [
            ("What counts as staying long enough", [
                "The ceremony, dinner and the formal moments - toasts, first dance, parent dances, cake cutting - are the parts the couple planned around having everyone present. Once the dancing is properly underway, the evening has become optional.",
                "At a wedding with a send-off, staying for it is a genuine kindness: a sparkler exit with eleven people is a sad photograph. If you know there is one, either stay or leave well before it.",
            ]),
            ("Saying goodbye without causing a scene", [
                "Find the couple, congratulate them briefly, and go. Thirty seconds. Do not wait for a natural gap in their evening, because there will not be one, and do not deliver a long explanation of why you are leaving.",
                "If you genuinely cannot reach them - they are dancing, or mid-photograph, or surrounded - tell a parent or a member of the wedding party, or send a message the next morning. Slipping out without a word is the only version that reads as rude.",
            ]),
            ("Reasons nobody will question", [
                "A babysitter, a long drive, an early flight, a medical reason, or a child who has hit their limit. Mention it briefly when you say goodbye and it will be entirely understood.",
                "If you know in advance you will need to leave early, tell the couple before the day. It removes any ambiguity and lets them find you for a photograph beforehand.",
            ]),
        ],
        "quick": [
            ("Before the ceremony ends", "Only for an emergency. Tell someone."),
            ("After dinner but before toasts", "Early. Say goodbye properly and briefly explain."),
            ("After the first dance", "Entirely acceptable."),
            ("Once dancing is underway", "Fine. Say goodbye and go."),
            ("There is a planned send-off", "Stay for it, or leave well before."),
            ("Can't find the couple", "Tell a parent or the wedding party, or message the next morning."),
        ],
        "faqs": [
            ("When can you leave a wedding?",
             "After the ceremony, dinner, toasts and the first dance is the reasonable minimum. Once dancing is properly underway, leaving is entirely acceptable and generally unnoticed."),
            ("Do you have to say goodbye to the couple when leaving a wedding?",
             "Yes - thirty seconds is enough. If you genuinely cannot reach them, tell a parent or a member of the wedding party, or message them the next morning. Leaving with no word at all is the version that reads as rude."),
            ("Is it rude to skip the reception and only attend the ceremony?",
             "It depends on whether you RSVP'd for the reception. Accepting a seat at dinner and not using it costs the couple money, so decline the reception in advance rather than leaving after the ceremony."),
        ],
    },
    "wedding-rsvp-etiquette": {
        "related": ['wedding-guest-etiquette', 'how-much-to-give-for-a-wedding-gift', 'is-it-rude-to-leave-a-wedding-early'],
        "question": "What are the rules for RSVPing to a wedding?",
        "short": "RSVP etiquette",
        "group": "At the wedding",
        "answer": "Reply by the date on the card, reply even if it's a no, and only bring the people named on the invitation. An unanswered RSVP is the single most annoying thing a guest can do, because the couple has to chase you personally while planning a wedding.",
        "sections": [
            ("Reply on time, and reply either way", [
                "Roughly a fifth of guests miss the deadline at every wedding, which means the couple spends the following week texting people individually. Replying the day you receive it takes ninety seconds and removes you from that list.",
                "A no is genuinely useful. Couples plan headcount, seating and catering from the total, and a firm decline is worth more to them than a silence they have to interpret.",
            ]),
            ("Who you may bring", [
                "Exactly the people named on the invitation. 'Ms Jane Doe' means one person. 'Ms Jane Doe and Guest' means you may bring someone. 'The Doe Family' includes children; your name alone does not.",
                "Do not ask to add someone unless something has genuinely changed, and accept the answer immediately if you do. Venues have hard capacity limits and catering is charged per head, so a plus-one is a real cost rather than a formality.",
            ]),
            ("Changes and dietary requirements", [
                "If you accept and then cannot come, tell them as soon as you know. The final headcount locks two to three weeks out, and after that the couple pays for your seat whether you sit in it or not.",
                "Give allergies and dietary requirements on the RSVP itself, not to a server on the night. The kitchen builds named plates from the seating chart, and a late request is genuinely hard to accommodate.",
            ]),
        ],
        "quick": [
            ("You got the invitation", "Reply within a few days. Do not wait for the deadline."),
            ("You can't attend", "Still reply. A firm no is useful to them."),
            ("Invitation names only you", "Come alone. Do not bring a guest."),
            ("You want to bring someone", "Ask only if something genuinely changed, and accept the answer."),
            ("Plans change after accepting", "Tell them immediately - the headcount locks 2-3 weeks out."),
            ("You have an allergy", "Put it on the RSVP, not on the night."),
        ],
        "faqs": [
            ("What happens if you don't RSVP to a wedding?",
             "The couple has to chase you personally, usually in the week they are finalising catering numbers. About a fifth of guests miss the deadline at every wedding, and it is the most common avoidable annoyance in wedding planning."),
            ("Can you bring a plus-one if the invitation doesn't say so?",
             "No. The invitation names exactly who is invited. Venues have hard capacity limits and catering is charged per person, so an extra guest is a genuine cost rather than a formality."),
            ("What if you RSVP yes and then can't attend?",
             "Tell them as soon as you know. The final headcount usually locks two to three weeks before the wedding, and after that the couple pays for your seat regardless."),
        ],
    },
    "wedding-guest-etiquette": {
        "related": ['what-to-wear-to-a-wedding', 'wedding-rsvp-etiquette', 'how-much-to-give-for-a-wedding-gift'],
        "question": "What are the rules for wedding guests?",
        "short": "Guest etiquette",
        "group": "At the wedding",
        "answer": "Reply on time, dress to the code, don't wear white, arrive early, put your phone away during the ceremony, don't propose or announce anything, and say goodbye before you leave. Almost everything else is flexible.",
        "sections": [
            ("Arriving", [
                "Aim to be seated 15 to 20 minutes before the stated ceremony time. Arriving as it begins means being walked in by an usher in front of everyone; arriving after means waiting outside until it is over, at many venues.",
                "The time on the invitation is when the ceremony starts, not when doors open.",
            ]),
            ("During the ceremony", [
                "Phones away and silent - not on your lap, away. Unplugged ceremonies are increasingly common and increasingly enforced, and even where they are not, a wall of raised phones is exactly what the couple paid a photographer to avoid. Your photograph of the aisle will be worse than theirs and will be in theirs.",
                "Do not step into the aisle to take a picture. This is the single most common way a guest ruins a professional photograph of the processional.",
            ]),
            ("At the reception", [
                "Sit where the chart says. It took hours and it accounts for things you cannot see.",
                "Do not propose, announce a pregnancy, or otherwise take the day. It happens, and it is remembered for decades.",
                "Drink at a pace you can sustain until the end. The cautionary tale at every wedding is a guest, not a vendor.",
                "Say goodbye before you go, briefly.",
            ]),
        ],
        "quick": [
            ("Arriving", "Seated 15-20 minutes before the stated time."),
            ("During the ceremony", "Phone away, out of the aisle, no photographs."),
            ("Seating", "Sit where the chart says."),
            ("Speeches", "Only if you were asked in advance."),
            ("Announcements", "Never. Not a proposal, not a pregnancy."),
            ("Leaving", "Say goodbye to the couple first."),
        ],
        "faqs": [
            ("What time should you arrive at a wedding?",
             "Seated 15 to 20 minutes before the stated ceremony time. The time on the invitation is when the ceremony begins, not when doors open, and late arrivals are often held outside until it is finished."),
            ("Can you take photos during a wedding ceremony?",
             "Increasingly not - unplugged ceremonies are common and enforced. Even where phones are allowed, stepping into the aisle is the most common way a guest ruins the professional photographs the couple paid for."),
            ("Is it okay to propose at someone else's wedding?",
             "No. Proposals, pregnancy announcements and any other personal news take a day the couple planned and paid for. It is remembered for decades, and never fondly."),
        ],
    },
}
