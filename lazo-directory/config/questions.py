"""What to ask each kind of wedding vendor.  JC-LAZO-ASK-0916-001

/questions/ and /questions/<category>/. The third content cluster.

Two design decisions keep this from cannibalising what we already publish:

1. It does NOT repeat config/cost_guides.py. Each cost guide carries five
   obvious questions. These pages go past them, and the format is different:
   every question is paired with what a good answer actually sounds like and
   what should worry you. A list of questions is worth little; knowing how to
   read the answer is the whole product.

2. The UNIVERSAL questions - contract, deposit, cancellation, insurance,
   substitution, payment schedule - live ONCE, on the hub at /questions/, and
   every category page links to them. Writing them fifteen times would make our
   own fifteen pages near-duplicates of each other, which is exactly the trap
   this cluster exists to avoid. Category pages carry only what is specific to
   that trade.

Tone: these pages are adversarial on the couple's behalf, and they should be.
Lazo takes nothing from vendors per lead or per booking, so we have no reason to
soften what a bad answer sounds like. A platform paid by vendors could not
publish this file, and that is precisely why it is worth publishing.

Schema per category:
  lede      why this trade in particular needs careful questions
  groups    [(group heading, [ {q, listen} ])]
              q       the question, phrased as you would actually say it
              listen  what a good answer sounds like, and what should worry you
  faqs      rendered as FAQPage schema
"""

# Asked of every vendor, in every category. Rendered once, on the hub.
UNIVERSAL = [
    ("The contract", [
        {"q": "Can I see the contract before I pay anything?",
         "listen": "Any professional says yes immediately and sends it. Hesitation, or a deposit requested before you have read terms, is the single clearest warning sign in this entire list. Read the cancellation, postponement and substitution clauses before the price."},
        {"q": "What is the payment schedule, and what is actually refundable?",
         "listen": "A typical structure is a non-refundable retainer to hold the date plus a balance due days or weeks before. That is normal. What you want stated plainly is which portion is refundable and until when - and 'we would work something out' is not a term, it is a feeling."},
        {"q": "What happens if we postpone?",
         "listen": "Since 2020 most vendors have a written postponement policy. A good answer names a window, says whether the retainer transfers, and is honest that a new date depends on availability. No policy at all in 2026 suggests they have not thought about the most likely disruption to your wedding."},
        {"q": "What happens if you cannot make it?",
         "listen": "You want a named arrangement: a professional network they would call, a second shooter or associate who could step in, a refund position if nobody can. 'That has never happened' is not a plan, and it is the answer that should worry you most."},
    ]),
    ("Their business, not their portfolio", [
        {"q": "Do you carry liability insurance, and can you send a certificate?",
         "listen": "Yes, and they can produce it the same day - many venues require it, so professionals have the document ready. A vendor who has never been asked for one has not worked many real venues."},
        {"q": "How many weddings are you taking that weekend?",
         "listen": "One is ideal. Two is common and workable if they have separate teams. A vendor doing a Friday, Saturday and Sunday is tired by the time they reach yours, and you should know that going in."},
        {"q": "Who will I actually be dealing with between now and the wedding?",
         "listen": "Larger companies hand you from sales to operations to a day-of lead. That is fine when it is disclosed. It is not fine when you discover it a week out."},
        {"q": "How quickly do you normally reply?",
         "listen": "Judge this by what already happened rather than what they say. A vendor who took nine days to answer your first enquiry will not become faster once they have your deposit."},
    ]),
    ("Money questions people avoid", [
        {"q": "Is there anything not in this quote that I will end up paying?",
         "listen": "Travel, overtime, meals, parking, delivery, setup, strike, rush fees and taxes are the usual omissions. A confident vendor will list them unprompted. Ask for the all-in number for your specific wedding, not the package price."},
        {"q": "Do you receive anything for recommending other vendors?",
         "listen": "Referral fees and kickbacks are common in this industry and are not always disclosed. An honest answer is either 'no' or 'yes, and here is how it works'. It matters because it tells you whether a recommendation is an opinion or a commission."},
        {"q": "What does gratuity look like for your team?",
         "listen": "Ask before the day so you can budget it. Some contracts include a service charge that is not gratuity, which means you may be tipping on top without realising it."},
    ]),
]

QUESTIONS = {
    "wedding-photographers": {
        "lede": "You are hiring someone to produce the only record of a day that cannot be repeated, and you are usually judging them on a portfolio built from their best twenty weddings. The questions that matter are the ones that reveal the average wedding rather than the best one.",
        "groups": [
            ("Seeing the real work", [
                {"q": "Can I see a full gallery from a wedding that had bad weather?",
                 "listen": "Every photographer looks good in golden hour. What you are testing is whether they can work in a dark church, in rain, at a reception lit by nothing but string lights. A photographer proud of a difficult wedding is showing you the floor of their ability, which is what you are actually buying."},
                {"q": "Have you shot at my venue, and what did you learn there?",
                 "listen": "A specific answer - where the light falls at four o'clock, which room is impossible, where the good wall is - is worth a great deal. Never having shot there is fine if they ask about scouting it."},
                {"q": "How do you handle family group photos?",
                 "listen": "You want a system: a written list agreed beforehand, someone loud designated to gather people, a target of around twenty minutes. Photographers without a system lose forty-five minutes of cocktail hour and blame your family for it."},
            ]),
            ("Style and direction", [
                {"q": "How much do you direct, and how much do you observe?",
                 "listen": "Both approaches produce beautiful work, and the mismatch is what ruins days. If you hate being posed, a heavily directing photographer will exhaust you. If you freeze without instruction, a pure documentarian will leave you stranded."},
                {"q": "What do you do if we are running an hour behind?",
                 "listen": "A good answer is triage: which photographs they protect, what they cut, who they tell. Weddings run late almost every time, so this is a question about the likely case, not the unlikely one."},
                {"q": "Do you edit skin, bodies or faces by default?",
                 "listen": "Ask directly, because assumptions differ wildly and the results are permanent. Some retouch heavily as standard. Say now what you do and do not want changed about how you look."},
            ]),
            ("Delivery and afterwards", [
                {"q": "How long do you keep my files, and what if I lose them?",
                 "listen": "Many photographers archive for one to three years and then delete. Some charge for re-delivery. Get the retention period in writing and back the gallery up yourself the week it arrives - this is the most common way couples lose their wedding photographs."},
                {"q": "What happens if I do not like the photos?",
                 "listen": "There is rarely a remedy and an honest photographer will say so, which is why the earlier questions matter more than this one. What a good answer includes is a willingness to revisit specific edits."},
            ]),
        ],
        "faqs": [
            ("What questions should I ask a wedding photographer?",
             "Beyond price and hours: ask to see a complete gallery from a wedding with bad weather, how they handle family group photos, how much they direct versus observe, what they do if the day runs late, and how long they keep your files afterwards."),
            ("How do I know if a wedding photographer is good?",
             "Look at complete galleries rather than highlight selections, and specifically at difficult conditions - dark churches, rain, night receptions. Anyone looks good at sunset. Consistency across a whole wedding is what you are buying."),
            ("Should I ask about photo retouching?",
             "Yes, and explicitly. Photographers differ enormously in how much they edit skin and bodies by default, and the results are permanent. Say what you do and do not want changed before you book."),
        ],
    },
    "wedding-videographers": {
        "lede": "Wedding film is an audio product that happens to have pictures. Most of what goes wrong is sound - vows nobody can hear, toasts recorded from the back of a room - and most couples only discover it months later when the film arrives.",
        "groups": [
            ("Audio, which is the whole thing", [
                {"q": "Exactly who gets a microphone, and what is your backup if one fails?",
                 "listen": "You want lapel mics on the officiant and at least one partner, a recorder at the altar, and a feed from the DJ or band for speeches. A videographer relying on the camera's on-board mic will deliver a film where your vows are inaudible."},
                {"q": "What do you do about an outdoor ceremony in wind?",
                 "listen": "Windshields, mic placement out of the airflow, a backup recorder. Wind ruins more ceremony audio than any other cause, and a good videographer raises it before you do."},
            ]),
            ("The edit you will actually receive", [
                {"q": "Can I watch a complete film - the long one, not the highlight?",
                 "listen": "Highlight reels are made from the best ninety seconds of a wedding and every videographer has good ones. The documentary edit is where you see whether they can hold a ceremony together."},
                {"q": "Who chooses the music, and is it licensed?",
                 "listen": "Properly licensed music costs them money and protects your film from being muted on social platforms. A videographer using popular tracks without licences is handing you a film you cannot share."},
                {"q": "How many revisions do I get, and what counts as one?",
                 "listen": "One or two rounds is standard. What you want defined is scope: swapping a music track is a different request from re-cutting the ceremony, and the contract should distinguish them."},
            ]),
            ("On the day", [
                {"q": "How do you and my photographer stay out of each other's shots?",
                 "listen": "Experienced pairs have a protocol - sides, heights, who moves during the vows. A videographer who has not thought about it will end up in your photographs, and vice versa."},
                {"q": "Will you use a drone, and have you checked my venue allows it?",
                 "listen": "Many venues and most urban airspace prohibit it. A videographer promising drone footage without having checked is promising something they may not be permitted to deliver."},
            ]),
        ],
        "faqs": [
            ("What should I ask a wedding videographer?",
             "Focus on audio: who gets microphones, what the backup is, how they handle wind outdoors, and whether they take a feed from the DJ for speeches. Then ask to watch a complete film rather than a highlight reel, and confirm the music is properly licensed."),
            ("Why is wedding video audio so often bad?",
             "Because it depends on equipment most couples never ask about - lapel mics on the officiant and couple, a recorder at the altar, and a board feed for speeches. A videographer relying on the camera's built-in microphone will deliver inaudible vows."),
            ("Does wedding video music need to be licensed?",
             "Yes. Unlicensed popular music can get your film muted or removed on social platforms, and a videographer using it is passing that risk to you. Ask what licensing they hold."),
        ],
    },
    "wedding-venues": {
        "lede": "The venue is the biggest line in most budgets and the one with the most fees hidden behind the headline number. It is also the only vendor whose sales team is trained, which means you are the least experienced person in the conversation.",
        "groups": [
            ("The number behind the number", [
                {"q": "Can I have a sample invoice for a wedding my size, on my date?",
                 "listen": "This single request reveals more than any tour. A real invoice shows minimum spend, service charge, tax, rental, ceremony fee, cake cutting, corkage and overtime. Reluctance to produce one is itself the answer."},
                {"q": "Is the service charge gratuity, and do I tip on top?",
                 "listen": "Frequently it is not gratuity - it is the venue's operating charge, and staff may be tipped separately. On a $20,000 food and beverage spend, a 22% charge is $4,400 and you should know exactly what it buys."},
                {"q": "What has gone up in price in the last two years?",
                 "listen": "An honest venue tells you. This matters if you are booking eighteen months out with a contract that permits price adjustment - ask whether your quoted rates are locked."},
            ]),
            ("What actually happens on the day", [
                {"q": "Can I see the space set up for a wedding, not empty?",
                 "listen": "Empty rooms photograph beautifully and tell you nothing about where 140 people, a bar, a band and a dance floor actually fit. Ask for photographs from real weddings at your guest count."},
                {"q": "Who is the on-site contact on my wedding day, and will I meet them?",
                 "listen": "The person selling you the venue is very often not the person working your wedding. That is normal; not being introduced before the day is not."},
                {"q": "What is the noise curfew and what happens at it?",
                 "listen": "Ask what time the music must stop, whether it steps down or cuts off, and what the penalty is. Outdoor and residential-adjacent venues frequently have hard limits that end receptions earlier than couples expect."},
            ]),
            ("Constraints they may not volunteer", [
                {"q": "What are the restrictions on vendors, candles, confetti and end time?",
                 "listen": "Exclusive caterer lists, banned open flame, no confetti, insurance minimums and strict strike times all shape your day and your budget. Get the full list in writing rather than discovering it through your florist."},
                {"q": "Is there another event on site that day or the night before?",
                 "listen": "Shared sites mean shared parking, noise bleed, and no early access for setup. Ask specifically about the night before - it determines whether you can decorate in advance."},
            ]),
        ],
        "faqs": [
            ("What should I ask when touring a wedding venue?",
             "Ask for a sample invoice for your guest count and date, whether the service charge is gratuity, who the on-site contact will be on the day, what the noise curfew is, and what the restrictions are on vendors, candles and confetti."),
            ("Is a venue service charge the same as a tip?",
             "Often not. Many venues charge 18-24% as an operating charge rather than gratuity, with staff tipped separately. Ask directly, because on a large food and beverage spend the difference is thousands of dollars."),
            ("Should I ask to see a venue set up for a wedding?",
             "Yes. An empty room tells you nothing about where your guest count, bar, band and dance floor actually fit. Ask for photographs from real weddings at a similar size."),
        ],
    },
    "wedding-planners": {
        "lede": "Planning is the one category where the words mean different things at different companies. Two planners can quote the same price for wildly different amounts of work, and the only way to compare them is to make each describe the job rather than the tier.",
        "groups": [
            ("What you are actually buying", [
                {"q": "Walk me through everything you do, month by month, from now until the wedding.",
                 "listen": "This question is impossible to answer vaguely. A planner who has done the job describes a sequence. One who cannot is selling you a title."},
                {"q": "What is explicitly not included?",
                 "listen": "Design, rentals sourcing, RSVP management, guest accommodation, rehearsal dinner, day-after brunch and travel are frequently excluded from packages couples assume are comprehensive."},
                {"q": "How many weddings do you run in a month, and who else is on my team?",
                 "listen": "One planner running six weddings a month is not giving any of them the attention the sales conversation implied. Ask how work is distributed and who will be on site."},
            ]),
            ("Whose side they are on", [
                {"q": "Do you take commission from vendors you recommend?",
                 "listen": "This is the most important question in this category and it is rarely asked. Some planners receive referral fees, which is legal and common - but it means a recommendation may not be purely about fit. An honest planner answers directly either way."},
                {"q": "What happens if I want a vendor who is not on your preferred list?",
                 "listen": "A good planner works with anyone competent and tells you their honest reservations. A planner who resists without a specific reason may be protecting a relationship rather than your wedding."},
                {"q": "Tell me about a wedding that went wrong and what you did.",
                 "listen": "Everyone with real experience has one. The answer shows you how they think under pressure and whether they take responsibility. 'Nothing has ever gone wrong' means either inexperience or unwillingness to be straight with you."},
            ]),
            ("The day itself", [
                {"q": "What time do you arrive and when do you leave?",
                 "listen": "Some packages cover ten hours, which does not stretch from an 8am setup to a midnight strike. Find the gap now rather than at 11pm on your wedding night."},
                {"q": "Who handles vendor payments and gratuities on the day?",
                 "listen": "Ideally them, from envelopes you prepare in advance. If it is you, that is a job you have just been given without being told."},
            ]),
        ],
        "faqs": [
            ("What should I ask a wedding planner before hiring them?",
             "Ask them to describe month by month what they will do, what is explicitly excluded, how many weddings they run per month, whether they take commission from vendors they recommend, and what time they arrive and leave on the day."),
            ("Do wedding planners get kickbacks from vendors?",
             "Some do - referral fees are legal and common in the industry. It does not make a planner dishonest, but it does mean a recommendation may not be purely about fit for you. Ask directly; a good planner will answer either way."),
            ("How do I compare two wedding planner quotes?",
             "Not by tier name - 'partial planning' means different things at different companies. Make each describe the actual work month by month and list what is excluded, then compare those descriptions rather than the labels."),
        ],
    },
    "wedding-djs": {
        "lede": "The music is the easy part. What separates a wedding DJ from someone with a laptop is the microphone work, the reading of a room, and knowing when not to play the song you asked for. Most of these questions are really about that.",
        "groups": [
            ("The MC half of the job", [
                {"q": "Can I hear you on a microphone?",
                 "listen": "Ask for a recording of them making announcements at a real wedding. This is half the job and almost nobody checks it. Cheesy, over-loud MC work is the most common complaint about wedding DJs and it is entirely predictable in advance."},
                {"q": "How much do you talk during the night?",
                 "listen": "There is a wide range between a DJ who announces only what is needed and one who treats the reception as a radio show. Neither is wrong; the mismatch is."},
                {"q": "How do you handle the timeline with my coordinator?",
                 "listen": "The DJ effectively drives the second half of a wedding. A good one has a running order, checks in with the coordinator and photographer before key moments, and will not start the first dance while your photographer is changing a battery."},
            ]),
            ("Music and requests", [
                {"q": "What do you do when a guest requests something on my do-not-play list?",
                 "listen": "The right answer is that they decline politely and it never reaches the speakers. A DJ who says 'I read the room' may be telling you they will override you."},
                {"q": "How do you build the night if the floor is empty at 9pm?",
                 "listen": "Listen for craft: pulling the average age of the room, bringing tempo up gradually, using a known opener. 'I just play bangers' is not a plan."},
                {"q": "What happens during dinner and cocktail hour?",
                 "listen": "Those are two more hours of curation that many couples never discuss. Ask what they play and at what volume - conversation has to be possible."},
            ]),
            ("Equipment and rooms", [
                {"q": "What backup gear do you bring?",
                 "listen": "A spare controller, spare laptop, spare cables and a backup music library on separate storage. Weddings have been salvaged by a $200 spare and ruined by the lack of one."},
                {"q": "Have you worked in my space, and does it need extra sound?",
                 "listen": "Long rooms, outdoor areas and separate ceremony sites often need a second system. Better to hear that now than to discover the ceremony is inaudible from row six."},
            ]),
        ],
        "faqs": [
            ("What should I ask a wedding DJ?",
             "Ask to hear them on a microphone at a real wedding, how much they talk, what they do with a request from your do-not-play list, how they build the night if the floor is empty, and what backup equipment they bring."),
            ("How do I know if a wedding DJ is good?",
             "Judge the microphone work, not the mixing. Ask for audio of them making announcements at a real reception - cheesy or overbearing MC work is the most common complaint about wedding DJs, and it is entirely predictable in advance."),
            ("Should I give my DJ a do-not-play list?",
             "Yes, and ask explicitly what they do when a guest requests something on it. The right answer is that they decline politely. A DJ who says they will 'read the room' may be telling you they will override you."),
        ],
    },
    "wedding-florists": {
        "lede": "Florals are the category where couples most often arrive with a photograph and leave with a quote three times their budget. The gap is almost always stem count and season, and a good florist will explain that rather than simply saying yes.",
        "groups": [
            ("Getting a real quote", [
                {"q": "If I show you this photograph, what would it cost and what is in it?",
                 "listen": "You want a florist who breaks it down - 'that is about sixty stems of imported garden rose' - rather than one who nods. The honest ones tell you what a picture costs before you fall in love with it."},
                {"q": "What is in season and local around my date?",
                 "listen": "A florist who lights up at this question is one who designs rather than orders. Seasonal, local material is the single biggest lever on a floral budget and the answer should be specific to your week."},
                {"q": "If my budget is fixed at this number, what would you do with it?",
                 "listen": "This is the most productive question in the category. It moves the conversation from a wish list to a design, and it reveals whether they can work within constraints or only above them."},
            ]),
            ("The day itself", [
                {"q": "Who installs, how long does it take, and when do you need access?",
                 "listen": "Installations need venue access hours before guests arrive, which has to be agreed with the venue, not assumed. Ask how many people are coming and what they need."},
                {"q": "Can ceremony pieces be moved to the reception, and who moves them?",
                 "listen": "Repurposing effectively doubles what you bought, but somebody has to physically do it during cocktail hour. Confirm whether that is the florist, the venue, or nobody."},
                {"q": "What happens if a flower I chose is unavailable that week?",
                 "listen": "Flowers are agricultural and substitutions are normal. What you want is a florist who will call you rather than silently swap, and who has already thought about the closest alternative."},
            ]),
            ("Afterwards", [
                {"q": "Do you come back to strike, and is that in the price?",
                 "listen": "Many venues require everything removed the same night. If the florist is not striking, that job falls to you or your coordinator at midnight."},
                {"q": "Can guests take arrangements home?",
                 "listen": "Ask before the day. Rented vessels frequently must come back, and a guest walking off with one becomes a charge on your invoice."},
            ]),
        ],
        "faqs": [
            ("What should I ask a wedding florist?",
             "Ask what a photograph you like would actually cost and what is in it, what is in season and local around your date, and what they would do with your budget if it were fixed. Then cover installation access, repurposing ceremony pieces, and who strikes at the end."),
            ("Why are wedding flowers more expensive than I expected?",
             "Usually stem count and season. An inspiration photograph often contains several hundred stems, frequently of flowers that must be flown in out of season. A good florist will tell you what a picture costs before you commit to it."),
            ("Can wedding flowers be reused from the ceremony to the reception?",
             "Yes, and it effectively doubles what you bought - but someone must physically move them during cocktail hour. Confirm whether that is the florist, the venue or nobody, because it is a job that otherwise falls to your coordinator."),
        ],
    },
    "wedding-caterers": {
        "lede": "Catering quotes are the hardest to compare in wedding planning, because two caterers can quote the same per-head number for completely different amounts of food, staff and equipment. Every useful question here is an attempt to make the quotes comparable.",
        "groups": [
            ("Making quotes comparable", [
                {"q": "What is the all-in cost per guest, including staff, rentals, service charge and tax?",
                 "listen": "Insist on one number for your guest count. A $65 quote with rentals and staffing excluded can land above a $95 quote that includes everything, and no couple has ever been told this by the cheaper caterer."},
                {"q": "How many staff will be working, and what is the ratio?",
                 "listen": "Roughly one server per 10-12 guests for plated service, fewer for buffet. Low staffing is how a cheap quote stays cheap and how dinner takes ninety minutes to serve."},
                {"q": "How do you price children, vendors and anyone not eating a full meal?",
                 "listen": "Vendor meals are typically half price and children's meals less, but both are frequently left off a first quote entirely - and vendor meals are contractually required more often than couples realise. Ask for the headcount breakdown, not just a total."},
            ]),
            ("The food itself", [
                {"q": "Is the tasting the same food, by the same chef, that we will get?",
                 "listen": "Tastings are sometimes cooked by a senior chef in a test kitchen for four people, and your wedding is cooked by a line for 140. Ask who is cooking on the day."},
                {"q": "How do you keep 140 plates hot?",
                 "listen": "Listen for specifics: hold cabinets, a staggered fire, service in waves. This is the technical heart of wedding catering and vague answers predict lukewarm dinners."},
                {"q": "How are allergies and dietary requirements handled on the night?",
                 "listen": "You want named plates, a seating-chart cross-reference and a captain who knows. 'We will have some vegetarian options' is not a system, and it is how a guest with a serious allergy ends up eating bread."},
            ]),
            ("Bar", [
                {"q": "Can I see both a package price and a consumption estimate?",
                 "listen": "Which is cheaper depends entirely on your guests, and a caterer who only offers packages may be selling you the more profitable option. Ask for both."},
                {"q": "What happens when the bar gets busy at 9pm?",
                 "listen": "Bar staffing ratios and a second service point are what prevent a twenty-minute queue during the part of the night you are paying most for."},
            ]),
        ],
        "faqs": [
            ("What should I ask a wedding caterer?",
             "Ask for the all-in cost per guest including staffing, rentals, service charge and tax; how many staff will work and at what ratio; whether the tasting is cooked by the same chef who will cook your wedding; and how allergies are handled on the night."),
            ("How many staff should a wedding caterer provide?",
             "Roughly one server per 10-12 guests for plated service, fewer for buffet or stations. Understaffing is the usual reason a cheaper quote is cheaper, and the visible result is dinner taking far longer to serve."),
            ("Is a catering tasting the same food we will get?",
             "Not always. Tastings are sometimes prepared by a senior chef for four people while your wedding is cooked by a line for 140. Ask specifically who will be cooking on your date."),
        ],
    },
    "wedding-cakes": {
        "lede": "Cake is a small line with two reliable surprises in it: what you are actually buying is servings rather than tiers, and your venue may charge more to cut it than you expect.",
        "groups": [
            ("What you are buying", [
                {"q": "How many servings is this, and at what slice size?",
                 "listen": "Serving sizes vary between bakers, so 'serves 120' is not a fixed quantity. Ask for the slice dimensions - a generous baker and a stingy one can quote the same number for very different amounts of cake."},
                {"q": "Does my venue charge a cutting fee, and have you worked there?",
                 "listen": "At $3 a slice for 150 guests that is $450, which can exceed the cake. A baker who regularly works your venue will know the fee before you do."},
                {"q": "Can we do a display cake with kitchen sheet cakes?",
                 "listen": "Any baker should offer this, and it typically saves 40-60%. A refusal to discuss it is a sign you are being sold up."},
            ]),
            ("Whether it survives the day", [
                {"q": "How will this hold up in the temperature at my venue?",
                 "listen": "Buttercream in an August outdoor reception is a real structural question. A baker who asks about the venue, the time of day and whether the cake sits in sun is one who has had a cake fail."},
                {"q": "When do you deliver, who sets it up, and what is the plan if it is damaged?",
                 "listen": "Tiered cakes are assembled on site. Ask whether they stay to assemble, how late they deliver, and what happens if something goes wrong in the van."},
            ]),
            ("Taste, which is somehow last", [
                {"q": "Can we taste the exact flavour and filling combination we are ordering?",
                 "listen": "Tasting boxes often contain the baker's standard range, not your chosen combination. If you want an unusual pairing, ask to taste that specifically."},
                {"q": "Can you handle allergies safely, or is there cross-contamination?",
                 "listen": "A small bakery with one kitchen may not be able to guarantee a gluten-free or nut-free cake. An honest baker says so rather than promising it."},
            ]),
        ],
        "faqs": [
            ("What should I ask a wedding cake baker?",
             "Ask how many servings you are buying and at what slice size, whether your venue charges a cutting fee, whether you can do a display cake with kitchen sheet cakes, and how the cake will hold up in your venue's temperature."),
            ("What is a cake cutting fee?",
             "A charge some venues apply, typically $1-$4 per slice, to cut and serve a cake they did not supply. On a 150-guest wedding that can cost more than the cake, so confirm it before ordering."),
            ("Do wedding cake tastings include our chosen flavours?",
             "Not always - tasting boxes often contain the baker's standard range rather than your specific flavour and filling combination. If you want something unusual, ask to taste that exact pairing."),
        ],
    },
    "hair-and-makeup": {
        "lede": "Everything about hair and makeup is predictable except the thing that goes wrong, which is time. The morning of a wedding is the only part of the day with no slack in it, and the schedule is set by how many artists you hired.",
        "groups": [
            ("The morning schedule", [
                {"q": "How long will my party take, and how many artists are coming?",
                 "listen": "Roughly 45-75 minutes per service. Do the arithmetic out loud together: six people having hair and makeup is twelve services, which one artist cannot finish before lunch. If the numbers do not work, the answer is another artist, not a faster one."},
                {"q": "What time do you need to start, working backwards from when photographs begin?",
                 "listen": "Note the framing: not backwards from the ceremony. An artist who asks what time your photographer arrives is scheduling the morning correctly; one who works from the ceremony time will have you ready an hour after the getting-ready photographs were meant to happen."},
                {"q": "What happens if we fall behind?",
                 "listen": "Listen for a plan - who gets simplified, what gets cut, whether they can call in help. Every wedding morning runs late; the question is whether they have a response."},
            ]),
            ("The trial", [
                {"q": "Can we do the trial at the same time of day as the wedding?",
                 "listen": "Makeup looks different in morning light than in the evening, and a trial at 2pm tells you little about a 5pm ceremony. Good artists suggest this themselves."},
                {"q": "Will you photograph the trial and bring notes?",
                 "listen": "The person who does your trial should have written and photographic notes so the look is reproducible - particularly if a different artist from the team may do you on the day."},
                {"q": "Is the person doing my trial the person doing my wedding?",
                 "listen": "At larger companies, not necessarily. Get the name in the contract if it matters to you, which it should."},
            ]),
            ("Products and conditions", [
                {"q": "Will my makeup last through crying, heat and eight hours?",
                 "listen": "Ask specifically about your climate and whether they use airbrush or long-wear products. An outdoor August wedding is a different technical problem from an indoor December one."},
                {"q": "What do you need from the venue - space, light, power?",
                 "listen": "Artists need a window or their own lighting, chairs at the right height and power. Hotel rooms with no natural light are the usual problem, and the fix is knowing in advance."},
                {"q": "Who fixes my makeup after the ceremony if I have cried?",
                 "listen": "Either they stay, or they leave you a kit and show you how to use it. Both are fine answers. No answer at all means you are on your own at the exact moment every photograph starts being taken."},
            ]),
        ],
        "faqs": [
            ("What should I ask a wedding hair and makeup artist?",
             "Ask how long your party will take and how many artists are coming, what time they need to start working backwards from photographs, whether the trial can be at the same time of day as the wedding, and whether the person doing your trial is the person doing your wedding."),
            ("How many hair and makeup artists do we need?",
             "Count services, not people - one person having both hair and makeup is two services at roughly 45-75 minutes each. A party of six having both is twelve services, which one artist cannot complete in a morning. Two or three artists is usually the answer."),
            ("Should the makeup trial be at the same time of day as the wedding?",
             "Ideally yes. Makeup reads differently in morning versus evening light, so a 2pm trial tells you little about a 5pm ceremony. Good artists suggest this without being asked."),
        ],
    },
    "wedding-officiants": {
        "lede": "The officiant writes and performs the only part of the day that is legally required and emotionally central, and they are usually the cheapest vendor at the wedding. The questions worth asking are about the writing and the paperwork, in that order.",
        "groups": [
            ("The ceremony itself", [
                {"q": "Can I read a full ceremony script you have written?",
                 "listen": "Not an outline - a complete script from a real wedding. This is the product, and it is fully inspectable in advance, which is unusual among wedding vendors. Take the opportunity."},
                {"q": "How do you learn enough about us to write it?",
                 "listen": "A questionnaire, then a conversation, then a draft you can edit. An officiant who needs only your names is delivering a template with your names in it."},
                {"q": "When do we see the draft, and can we change it?",
                 "listen": "Two to four weeks out, with room for revision. Receiving the script for the first time at the rehearsal is too late to change anything."},
            ]),
            ("Traditions and blending", [
                {"q": "Are you comfortable including our cultural or religious elements?",
                 "listen": "If you want a lazo, arras, handfasting, a tea ceremony or seven steps, ask whether they have performed it and how they would sequence it. Enthusiasm plus specific questions is the answer you want."},
                {"q": "How do you handle a ceremony blending two faiths or none?",
                 "listen": "Interfaith and secular-plus-religious ceremonies need care about wording. An experienced officiant will describe how they have navigated it rather than promising it is easy."},
            ]),
            ("The legal part", [
                {"q": "Are you licensed to marry us in this county, and who files the licence?",
                 "listen": "Requirements vary by state and occasionally by county. You want a clear yes, and a clear statement that they file it and by when. This is the one thing at a wedding that cannot be fixed afterwards."},
                {"q": "Do you attend the rehearsal, and is it included?",
                 "listen": "Often a separate $100-$200. Worth it if your processional is complex or if family members are participating."},
                {"q": "What is your backup if you are ill?",
                 "listen": "You need a named colleague who could step in, because the wedding legally cannot proceed without a qualified officiant."},
            ]),
        ],
        "faqs": [
            ("What should I ask a wedding officiant?",
             "Ask to read a complete ceremony script they have written, how they learn about you before writing, when you will see your draft and whether you can edit it, whether they are licensed in your county, and who files the marriage licence."),
            ("How do I know if an officiant is legally able to marry us?",
             "Ask directly whether they are authorised in your specific county, since requirements vary by state and sometimes by county. Confirm who files the signed licence and by what deadline - it is the one part of a wedding that cannot be corrected later."),
            ("Can an officiant include our cultural traditions?",
             "A good one will ask specific questions about how you want a lazo, las arras, handfasting or a tea ceremony sequenced. Ask whether they have performed it before, and give them the script if your family has one."),
        ],
    },
    "wedding-bands": {
        "lede": "You are booking specific musicians, not a brand. The single most useful question in this category is which of the people in the video will actually be at your wedding, and it is the one couples most often forget to ask.",
        "groups": [
            ("Who is actually playing", [
                {"q": "If a musician is ill on the day, who replaces them and have they played with you?",
                 "listen": "Deps are normal in music and the good bands have a regular pool who know the set. What should worry you is a band that has never thought about it, or one that would simply play a horn arrangement without horns."},
                {"q": "Can I see unedited footage from a recent wedding?",
                 "listen": "Showreels are cut from the best bars of the best songs. Two continuous minutes from a real reception tells you whether the vocals are good and whether the room was full."},
                {"q": "Can we come and see you play?",
                 "listen": "Many bands do public showcases. An offer to arrange one is a strong sign; a refusal without an alternative is not."},
            ]),
            ("The shape of the night", [
                {"q": "What does the room sound like during your breaks?",
                 "listen": "Breaks are roughly a third of your reception. Some bands provide a proper DJ service, others put a phone through the PA and the dance floor empties. Ask to hear what the interval music actually is."},
                {"q": "Will you learn our first dance song?",
                 "listen": "Most will, some charge, a few will decline if it is far outside their style. Ask early, and ask for a recording in advance if it matters."},
                {"q": "Who MCs the announcements?",
                 "listen": "Bands are often less comfortable on the microphone than DJs. Establish who introduces the speeches and the first dance, because assuming it is covered is how it ends up being your best man."},
            ]),
            ("Logistics the venue will care about", [
                {"q": "What do you need - space, power, load-in time, parking?",
                 "listen": "A ten-piece band needs real stage area, multiple circuits and an hour to set up. Your venue needs this information, and the band should be able to supply a technical rider."},
                {"q": "Do you bring your own sound and lighting?",
                 "listen": "Most full bands do, and it saves a separate rental. Confirm it covers the ceremony and cocktail hour too if you want those."},
                {"q": "What are the break, meal and overtime terms?",
                 "listen": "Musicians require meals and scheduled breaks, and overtime is typically charged per 30 minutes per musician - which on a ten-piece band is not a small number."},
            ]),
        ],
        "faqs": [
            ("What should I ask a wedding band?",
             "Ask which musicians in their video are contracted for your date, to see unedited footage from a recent wedding, how many sets they play and what happens between them, whether they will learn your first dance, and what they need in space, power and load-in time."),
            ("Are the musicians in a wedding band's video the ones who will play?",
             "Not necessarily. Many wedding bands operate as agencies with rotating pools of musicians. Ask for a named line-up in the contract if the specific players matter to you."),
            ("What happens during a wedding band's breaks?",
             "It varies enormously - some provide a proper DJ service between sets, others play a phone through the PA. Since breaks account for roughly a third of your reception, ask specifically what they sound like."),
        ],
    },
    "day-of-coordination": {
        "lede": "The name of this service is actively misleading, and that is the reason to ask questions. What you want is someone who takes over weeks before the wedding, not someone who turns up on the morning holding a clipboard you wrote.",
        "groups": [
            ("When they actually start", [
                {"q": "What date do you take over, and what happens between now and then?",
                 "listen": "Four to six weeks out is the standard for real coordination: confirming vendors, building the timeline, chasing final counts. Someone who starts on the morning of is an assistant, not a coordinator, and should be priced as one."},
                {"q": "Do you contact all my vendors, or do I?",
                 "listen": "They should. Vendor confirmation calls are the bulk of the pre-wedding work and the thing that catches a missing delivery or a wrong arrival time."},
                {"q": "Will you build the timeline, or do I hand you mine?",
                 "listen": "Building a timeline from scratch requires knowing how long real things take. A coordinator who only executes your document is not bringing that expertise."},
            ]),
            ("On the day", [
                {"q": "How many hours, and does that cover setup and strike?",
                 "listen": "Many packages cover 10-12 hours, which will not stretch from an 8am setup to a midnight strike. Find the gap before the day, not during it."},
                {"q": "Who is with you, and what happens if you are in two places?",
                 "listen": "Setting a reception while the ceremony runs is a two-person job. Ask whether an assistant is included or extra."},
                {"q": "Do you handle vendor payments, gratuities and returns?",
                 "listen": "Distributing envelopes, returning rentals and getting the gifts and cake topper home are all real jobs that otherwise land on your family at midnight."},
            ]),
            ("Judgement", [
                {"q": "Tell me about something that went wrong and how you fixed it.",
                 "listen": "This is the whole job. Anyone experienced has a story about a late cake or a collapsed arch, and the answer shows how they think when the plan fails."},
                {"q": "What is on your timeline that I would not have thought of?",
                 "listen": "This is the question that reveals experience. Listen for the unglamorous items: when the photographer eats, who holds the rings before the ceremony, when the band loads in, who returns the rentals. A coordinator who names four of those has run real weddings."},
            ]),
        ],
        "faqs": [
            ("What should I ask a day-of coordinator?",
             "The most important question is what date they actually take over - real coordination starts four to six weeks out, not on the morning. Then ask whether they contact your vendors, whether they build the timeline, how many hours they cover, and who their backup is."),
            ("What is the difference between a day-of coordinator and someone who just shows up?",
             "Genuine day-of coordination begins four to six weeks before the wedding with vendor confirmations, timeline building and final counts. Someone arriving on the morning to execute a document you wrote is an assistant and should cost considerably less."),
            ("Does a day-of coordinator handle vendor payments?",
             "Good ones do - distributing gratuity envelopes you prepared, returning rentals and getting gifts home. Ask, because if they do not, those jobs land on your family at midnight."),
        ],
    },
    "wedding-transportation": {
        "lede": "Transportation is the vendor couples think about last and the one most likely to strand guests. Almost every question here is about time: when the clock starts, how many runs are included, and what happens at the end of the night.",
        "groups": [
            ("The clock", [
                {"q": "When does the billable time start - at pickup, or when the vehicle leaves the depot?",
                 "listen": "Frequently the depot, which can add an hour you did not know you were buying. This single question changes the real cost more than any other in the category."},
                {"q": "What is the minimum, and what does overtime cost?",
                 "listen": "Three to four hour minimums are standard regardless of journey length. Overtime is usually billed in 30 or 60-minute blocks and weddings run late, so know the rate."},
                {"q": "How many runs are included, and what does an extra late loop cost?",
                 "listen": "The end-of-night return is the run guests need most and the one most often omitted from a quote."},
            ]),
            ("The vehicles", [
                {"q": "Can this vehicle physically reach my venue?",
                 "listen": "Low bridges, narrow lanes, gravel drives and tight turning circles are real constraints. A company that asks for the address and checks is one that has been caught before."},
                {"q": "What is the backup if a vehicle breaks down?",
                 "listen": "You want a named alternative and a stated response time. Vintage cars in particular are single vehicles with no spare."},
                {"q": "Can I see the actual vehicle, not a stock photo?",
                 "listen": "Ask for a recent photograph of the specific vehicle. Fleet images are frequently newer or cleaner than what arrives."},
            ]),
            ("The details that catch people", [
                {"q": "What happens if the wedding party is late coming out?",
                 "listen": "Weddings run late and vehicles get billed by the hour. Ask whether the driver waits, when overtime starts, and who they call - you, or your coordinator. The answer should not be that they leave."},
                {"q": "What is the policy on drinks in the vehicle?",
                 "listen": "Some permit alcohol, some prohibit it, some charge a cleaning fee. Worth knowing before the wedding party gets in."},
                {"q": "Who is my point of contact on the day, and will the driver have the timeline?",
                 "listen": "The driver should have the schedule, the addresses and a phone number that is not yours."},
            ]),
        ],
        "faqs": [
            ("What should I ask a wedding transportation company?",
             "Ask when the billable clock starts - at pickup or when the vehicle leaves the depot - what the minimum and overtime rates are, how many runs are included, whether the vehicle can physically reach your venue, and what the backup is if it breaks down."),
            ("Do wedding cars charge from the depot?",
             "Many do, which can add an hour of billable time before the vehicle even reaches you. It is the single question that most changes the real cost, so ask it directly."),
            ("Should we provide transport for guests at the end of the night?",
             "The end-of-night run is the one guests need most, especially if you are serving alcohol - and it is the run most often left out of an initial quote. Ask what an extra late loop costs."),
        ],
    },
    "wedding-rentals": {
        "lede": "Rental quotes are itemised, which makes them look transparent and comparable. They usually are not, because delivery, setup, strike and damage terms sit outside the item list and can add a quarter to the total.",
        "groups": [
            ("The real total", [
                {"q": "What is the delivered, set up and struck total, not the item prices?",
                 "listen": "Delivery, setup and strike commonly add 15-25%. Two quotes are only comparable at this number, and one supplier will usually be reluctant to produce it."},
                {"q": "What does my caterer or venue already provide?",
                 "listen": "China, glassware, flatware, linens and tables are frequently included elsewhere. Renting them twice is among the most common wedding budget mistakes and costs $10-$30 per guest."},
                {"q": "What is the damage and replacement policy?",
                 "listen": "Ask the replacement rate for a broken glass or a stained linen, and whether a damage waiver is optional or automatic. Guests break things at every wedding."},
            ]),
            ("Timing and access", [
                {"q": "When do you deliver and collect, and does my venue allow those times?",
                 "listen": "Venues have strict load-in and strike windows. A supplier who wants to collect Monday when the venue requires everything gone Saturday night is a problem you find at midnight."},
                {"q": "Who is responsible for repacking at the end?",
                 "listen": "Frequently you are, and frequently nobody realises. Ask whether your coordinator, the venue or the rental company stacks and bags everything."},
                {"q": "Is my order held, or reallocated if someone books it first?",
                 "listen": "Inventory is finite locally. Confirm your items are reserved to your date in the contract rather than pencilled."},
            ]),
            ("If you are building on a bare site", [
                {"q": "What do I need beyond the tent - flooring, power, lighting, climate, restrooms?",
                 "listen": "An empty field needs all of it, and the tent is frequently the smallest line. A supplier who walks you through the full list is saving you from a large surprise."},
                {"q": "Who does the site visit, and when?",
                 "listen": "Tents need ground assessment, staking or weighting and access for a truck. A quote issued without a site visit is an estimate."},
                {"q": "What is the wind and weather plan?",
                 "listen": "Tents have wind ratings and there is a point at which they must be evacuated. Ask who makes that call and when."},
            ]),
        ],
        "faqs": [
            ("What should I ask a wedding rental company?",
             "Ask for the delivered, set up and struck total rather than item prices, what your caterer or venue already provides so you do not rent twice, what the damage and replacement policy is, and who repacks everything at the end of the night."),
            ("Are delivery and setup included in wedding rental quotes?",
             "Often not. They typically add 15-25% to an order and appear as separate lines, so two quotes are only genuinely comparable at the delivered-and-installed total."),
            ("What do I need to rent for a wedding in a field?",
             "Far more than a tent - flooring, power, lighting, climate control and restrooms are usually all required, and the tent is frequently the smallest line. Insist on a site visit before accepting any quote."),
        ],
    },
    "wedding-invitations": {
        "lede": "Stationery is the one vendor whose mistakes are permanent, public and printed a hundred times. Nearly every question here is about proofing, quantity and the thing nobody checks: postage.",
        "groups": [
            ("Getting it right before it prints", [
                {"q": "Who is responsible for proofreading, and what happens if an error prints?",
                 "listen": "Almost every contract makes the client responsible for the final proof. That is standard, and it means you must read it as though it costs $800 to be wrong, because it does."},
                {"q": "Can you send a sample addressed and stamped, exactly as guests will receive it?",
                 "listen": "This catches two things at once: how the finished suite feels in the hand, and what it actually weighs for postage. A stationer who offers this unprompted has been caught by postage before and does not intend to be again."},
                {"q": "How many rounds of proofs are included?",
                 "listen": "Two or three is typical, with charges beyond. Ask what counts as a round - a typo fix and a layout change may be priced differently."},
            ]),
            ("Quantity and postage", [
                {"q": "How many should I order for my guest list?",
                 "listen": "By household, not guest - roughly 60% of your count - plus 10-15% extra. A stationer who asks for your household count rather than your guest count is doing it right."},
                {"q": "What will a finished suite weigh, and what postage does it need?",
                 "listen": "Square, thick or oversized suites need extra postage, sometimes double. Ask them to weigh a complete assembled sample. This is the most common unbudgeted cost in the category."},
                {"q": "What does a small reprint cost?",
                 "listen": "Disproportionate, because it is a new press setup. This is why extras are cheap insurance and why the number matters now."},
            ]),
            ("Timeline and the rest of the paper", [
                {"q": "What is the last date I can change the guest list without it costing me?",
                 "listen": "Printing is a fixed run. Ask when the quantity locks, what a late addition costs, and whether they hold blanks for stragglers - which is the cheap answer most couples never hear about."},
                {"q": "Do you do day-of paper too, and should I order it now?",
                 "listen": "Menus, programmes, place cards, signage and thank-you cards are a second order most couples forget to budget. Ordering together often saves setup fees."},
                {"q": "Do you offer printed addressing, and what does calligraphy cost?",
                 "listen": "Calligraphy is commonly $2-$6 per envelope, which at 100 households can exceed the invitations. Printed addressing looks excellent at a fraction."},
            ]),
        ],
        "faqs": [
            ("What should I ask a wedding stationer?",
             "Ask who is responsible for proofreading and what happens if an error prints, to see a physical sample of the stock and printing method, how many proof rounds are included, what a finished suite weighs for postage, and what a small reprint would cost."),
            ("How many wedding invitations should I order?",
             "By household rather than by guest - roughly 60% of your guest count - plus 10-15% extra for addressing mistakes and keepsakes. Reprint runs are disproportionately expensive because they require a new press setup."),
            ("Why do wedding invitations sometimes need extra postage?",
             "Square, thick, rigid or oversized suites exceed standard letter parameters and can require double postage. Have your stationer weigh a complete assembled sample before you buy stamps - it is the most commonly unbudgeted cost in the category."),
        ],
    },
}
