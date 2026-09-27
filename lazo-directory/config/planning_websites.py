"""Wedding-website guides.  JC-LAZO-WWSEO-0919-007

Four guides in the /planning/ cluster, group "Your wedding website". They
answer the searches that sit one step before "wedding website templates":
what goes on it, how to make one, what it should say, when to send it.
Each one is written against our own product (the sections every Lazo design
has, the RSVP that files itself, married mode) because that is the answer
we can give that a generic blog cannot. Same schema as config/planning.py.
"""

WEBSITE_GUIDES = {
    "what-to-put-on-your-wedding-website": {
        "question": "What should we put on our wedding website?",
        "short": "What goes on the website",
        "group": "Your wedding website",
        "cats": ["wedding-venues", "wedding-planners", "day-of-coordination"],
        "related": ["how-to-make-a-wedding-website", "wedding-website-wording", "when-to-send-wedding-website"],
        "lede": "Put on your wedding website every question a guest would otherwise text you, in the order they will ask it: when and where, how to get there and where to stay, what to wear, how to reply and by when, and where the registry is. Everything else, the story, the photos, the party, is welcome but optional. The test for each section is simple: would a guest who has only the invitation still need to ask?",
        "sections": [
            ("The five things every guest needs", [
                "<strong>Date, time and place.</strong> The full date with the year, the ceremony start time, and the venue name with a street address that works in a map app. Guests screenshot this section more than any other; make it the first thing on the page.",
                "<strong>Getting there and staying over.</strong> The nearest airport, the hotel block with its booking deadline and code, shuttle times if there are any, and parking. If the ceremony and reception are in different places, say how guests move between them and how long it takes.",
                "<strong>Dress code, in plain words.</strong> 'Cocktail attire' means different things in different families. Add one line about the setting: grass, sand, a stone floor, an unheated barn in October. Guests choose shoes on that line.",
                "<strong>RSVP, with a deadline.</strong> Say how to reply and by when, and make the deadline at least two weeks before your caterer's final count. On a Lazo site the RSVP is on the page and every reply lands in your planner with meals and plus-ones attached, so the deadline is the only thing you have to decide.",
                "<strong>The registry.</strong> Link it; do not describe it. A short note in your own words ('your presence is the gift; if you would like to give more, we have gathered a few things for the house') does the work the invitation cannot.",
            ]),
            ("The things that stop the texts", [
                "A schedule of the whole day, with times, not just the ceremony. Guests plan their afternoon around when they can leave. If there is a welcome drink the night before or a brunch the morning after, put those on the schedule too, with who is invited.",
                "A FAQ, which is where the awkward answers go: whether children are invited, whether there is a plus-one, what happens if it rains, whether the ceremony is unplugged, whether there is a cash bar. Writing these down once saves you saying them twenty times, and guests would rather read them than ask.",
                "Something local for people travelling in: three places to eat, one for coffee, one thing to do with a free afternoon. On a Lazo site the nearby section fills itself from the venue, with your own picks first.",
            ]),
            ("The things that make it yours", [
                "How you met, in a paragraph, not a page. Guests read it; long versions get skimmed. A cover photo and a small gallery of the two of you, not the engagement shoot in full.",
                "Your wedding party by name, if you like, with a line each. Your vendors, if they are good, because guests ask who did the flowers.",
                "What comes after. Most wedding websites die the morning after with a countdown stuck at zero. A Lazo site flips to married mode: the countdown turns into days married, the RSVP becomes a thank-you, and a guestbook and chapters carry it on.",
            ]),
            ("What to leave off", [
                "Anything a stranger should not know: your home address, the passcode to the site, the hotel room block details if the site is public. If you want the details private, add a passcode and put it on the invitation.",
                "Gift amounts, dress-code policing, and long lists of rules. One warm line beats three stern ones.",
            ]),
        ],
        "practical": [
            ("Ask your venue for the address guests should use, not the postal one.", "Large venues often have a guest entrance a street away from the registered address. The venue coordinator knows which one the map should point to."),
            ("Ask the hotel for the block deadline and code in writing, then put both on the site.", "Blocks release on a fixed date and guests miss it. The website is the only place every guest will see the deadline."),
            ("Ask your caterer for their final-count date and set the RSVP deadline two weeks before it.", "The gap is where you chase the last twelve replies. Without it, the count is a guess."),
        ],
        "faqs": [
            ("Should the wedding website have a password?", "Only if you would be uncomfortable with a stranger reading it. Most couples leave the site public and keep addresses and room-block codes off it. If you add a passcode on Lazo, the site also stays out of search engines."),
            ("How much should we write about ourselves?", "One paragraph on how you met and one on the proposal is plenty. Guests are there for the logistics; the story is the reward for scrolling."),
            ("Do we need a FAQ section?", "Yes, if only for children, plus-ones and the rain plan. Those three questions generate more texts than everything else combined."),
        ],
    },
    "how-to-make-a-wedding-website": {
        "question": "How do we make a wedding website?",
        "short": "How to make a wedding website",
        "group": "Your wedding website",
        "cats": ["wedding-planners", "wedding-photographers"],
        "related": ["what-to-put-on-your-wedding-website", "wedding-website-wording", "when-to-send-wedding-website"],
        "lede": "Making a wedding website takes about twenty minutes if you do it in the right order: pick a design, type your names and date, add the venue and the schedule, publish, and share the link. Everything else, the travel section, the registry, the photos, the story, can be added later without changing the link. The mistake is waiting until you have all of it, because the people who need the site most, the ones booking flights, need it first.",
        "sections": [
            ("Start with what is fixed", [
                "You need three things to publish: your names, your date, and the venue. If you have those, make the site today, even if the site says nothing else. Guests booking travel need the date and the city, and a site with two facts on it is more useful than a beautiful one that goes live a month before the wedding.",
                "On Lazo, pick any of the designs, type your names and watch every preview update, then create the site with that design. It is live at your own link immediately, and it is free, with no card.",
            ]),
            ("Add the logistics, then stop", [
                "The schedule, with times: ceremony, cocktails, dinner, dancing, and anything the night before or the morning after. The venue with the address guests should use. Where to stay, with the hotel block deadline. How to RSVP and by when. That is a complete wedding website; publish it and send the link with the save-the-date.",
                "Every Lazo design has a section for each of these, in the same order, so the only decision is which design. Leave a section empty and it does not show.",
            ]),
            ("Come back for the rest", [
                "Photos, when you have the engagement shoot. The story, when you have an evening. Dress code, when you have decided. Registry, once it exists. Vendors, once they are booked; on Lazo, vendors you book through the planner appear on the site on their own.",
                "None of these change the link, so nothing you have already sent goes stale. Guests who open the site in month one and again in month six see the same address with more on it.",
            ]),
            ("Choosing a design without agonising", [
                "Match the venue, not your personality. A garden wedding wants greenery, a ballroom wants black tie, a beach wants a beach. Guests should get the setting from the site before they read a word.",
                "Check it on a phone, because that is where nearly every guest will open it. Type your own names into the preview; a design that looks right with 'Charlotte and Henry' can look different with a long double-barrelled surname.",
                "You can change designs later on Lazo and everything you have added carries over, so the choice is not final.",
            ]),
            ("Before you share it", [
                "Open the link on a phone that is not yours. Tap the address and check the map opens in the right place. Tap RSVP and reply as a test guest, then delete the reply. Read the dress code line as a guest who has never met you.",
                "Decide whether the site is public or has a passcode. Public sites can be found by name, which guests like; passcode sites need the code on the invitation.",
            ]),
        ],
        "practical": [
            ("Tell your stationer the website link before the save-the-dates go to print.", "The link goes on the save-the-date and the invitation. Make the site first so the link exists; on Lazo it is meetlazo.com/w/ and your names."),
            ("Ask your photographer for three engagement photos early, in web sizes.", "The full gallery arrives weeks later. Three photos are enough for the cover and the story section, and the site looks finished."),
            ("Ask your venue whether guests should use the venue's own directions.", "Some venues have a directions page for a reason: the map route crosses a locked gate or a private road."),
        ],
        "faqs": [
            ("How early should we make the wedding website?", "As soon as you have a date and a venue, ideally before the save-the-dates go out, so the link can be on them. Fill in the rest over time."),
            ("Do we need to know how to code or design?", "No. On Lazo you pick a design, type your names and details, and it is live. There is nothing to install and no design decisions beyond which template and which color look."),
            ("Can we change the design after publishing?", "Yes. Switch designs or color looks any time; your names, schedule, RSVPs and everything else carry over and the link stays the same."),
        ],
    },
    "wedding-website-wording": {
        "question": "What should our wedding website say?",
        "short": "Wedding website wording",
        "group": "Your wedding website",
        "cats": ["wedding-planners", "wedding-officiants"],
        "related": ["what-to-put-on-your-wedding-website", "how-to-make-a-wedding-website", "when-to-send-wedding-website"],
        "lede": "Write your wedding website the way you would text a friend who is coming: short, warm, and specific. The welcome is two sentences. The story is a paragraph. The logistics are facts, not prose. The RSVP asks plainly. The registry note says thank you before it says anything else. Below is wording for each section you can lift and change, and the lines to avoid.",
        "sections": [
            ("The welcome", [
                "Two sentences at most. 'We are getting married on June 12 at Magnolia Hall in Charleston, and we would love you to be there. Everything you need is below.' Names and the date are already in the header; the welcome's job is to sound like you.",
                "Avoid: 'Welcome to our wedding website!' as the whole line. It says nothing the header did not.",
            ]),
            ("How we met", [
                "One paragraph, one detail that only you could write. 'We met in line at the orchard the October the hayride broke down. Nobody wanted to walk back, so we didn't.' The specific detail does more than three sentences of adjectives.",
                "If two people are writing it, write two short paragraphs, one each, and label them. Guests love the disagreement about who spoke first.",
            ]),
            ("The schedule and venue", [
                "Facts, in a list, in order, with times. '4:00 pm, ceremony on the lawn. 4:45, cocktails on the terrace. 6:00, dinner in the barn. 8:30, dancing until the lights go off.' One warm note per event is fine: 'bring a layer, the light goes golden and the air goes cold.'",
                "For the venue, the name, the address guests should use, and one line about the setting. 'The ceremony is on grass; heels sink.'",
            ]),
            ("Travel and stays", [
                "'We have held rooms at the Stonebridge Inn until September 15 under Hazel and Rowan; call or book with code HRWED. The nearest airport is Albany, an hour away. A shuttle leaves the inn at 3:15 and comes back at 11 and midnight.' Every number a guest needs, none they do not.",
            ]),
            ("Dress code", [
                "Name the code, then translate it. 'Cocktail attire: suits and dresses, no need for a tie. It is a meadow, so flat shoes or none.' 'Black tie: long dresses and tuxedos. Sparkle welcome.' 'Indian or Western formal; bright colour is encouraged for the sangeet.'",
                "Avoid rules about what not to wear, beyond one line if it matters ('please avoid white, and red on Saturday, which is for the bride').",
            ]),
            ("The RSVP", [
                "Ask plainly and give the date. 'Kindly reply by May 1; the kitchen needs a count.' The yes and no should sound like you: 'Coming to the orchard' / 'Sending love from afar' reads better than 'Accepts' / 'Declines'. On Lazo the RSVP is on the site and the labels are yours to change.",
            ]),
            ("The registry", [
                "Thank first. 'Your presence is the whole point. If you would like to give more, we have gathered a few things for the house, and a fund for the trip to the lakes we keep talking about.' Then the links. For no gifts: 'Your being there is the gift; please do not bring one.' For a cash fund: name what it is for; a purpose makes it a present rather than a request.",
            ]),
            ("The FAQ", [
                "Answer the awkward questions in one line each, kindly. 'Are children invited? We love your kids, and this one is grown-ups only.' 'Can I bring a guest? If your invitation names one, yes.' 'What if it rains? The ceremony moves into the barn, and the barn has a bar.' 'Is there parking? Yes, in the field by the gate; a shuttle runs from the inn if you would rather not drive.'",
            ]),
            ("After the wedding", [
                "The thank-you replaces the RSVP. 'The leaves turned right on time. Thank you for coming up the valley for us.' On Lazo this appears the morning after on its own, along with days married and a guestbook, so write it before the wedding while you still have time.",
            ]),
        ],
        "practical": [
            ("Ask your officiant for the ceremony length and put it in the schedule.", "Guests decide when to leave a cocktail hour by when the ceremony ends, and officiants know their timing to the minute."),
            ("Ask your planner or coordinator to read the FAQ as a guest.", "They have watched a hundred weddings and know which question you forgot: usually the rain plan, the shuttle, or the bar."),
        ],
        "faqs": [
            ("How formal should the wording be?", "As formal as the invitation, one notch warmer. The invitation sets the tone; the website is where you sound like yourselves."),
            ("Should we write in first person or third?", "First person, plural: 'we'. Third person ('the couple requests') belongs on the invitation, if anywhere."),
            ("Do we have to include a story?", "No. Many couples leave it off and guests do not miss it. If you write one, keep it to a paragraph with one true detail."),
        ],
    },
    "when-to-send-wedding-website": {
        "question": "When should we send out our wedding website?",
        "short": "When to share the website",
        "group": "Your wedding website",
        "cats": ["wedding-planners", "wedding-invitations"],
        "related": ["what-to-put-on-your-wedding-website", "how-to-make-a-wedding-website", "wedding-website-wording"],
        "lede": "Share your wedding website with the save-the-date, six to eight months before the wedding, or ten to twelve for a destination wedding, with the date, the city and where to stay already on it. Send the link again with the invitation, when the schedule, RSVP and registry are complete. The site is the one thing you send that can improve after you send it, so the first version does not have to be finished, only correct.",
        "sections": [
            ("With the save-the-date: the travel version", [
                "Guests who fly need the date, the city and the hotel block before anything else, and they need them months out. That is the whole job of the first version of your site. Put the link on the save-the-date and make sure the site has the date, the venue city, the hotel block with its deadline, and the nearest airport.",
                "Do not wait for the design to be perfect or the story to be written. A site with four facts on it, sent early, is worth more than a beautiful one sent late. On Lazo the link never changes, so whatever you add later reaches the same guests.",
            ]),
            ("With the invitation: the complete version", [
                "By the time invitations go out, eight to ten weeks before the wedding, the site should carry the full schedule, the dress code, the RSVP with its deadline, the registry and the FAQ. Put the link on the invitation and, if you are collecting RSVPs online, say so plainly: 'please reply at the link by May 1'.",
                "This is the version most guests will actually read, on their phone, the evening the invitation arrives. Check it on a phone that day.",
            ]),
            ("The reminders nobody sends", [
                "Two weeks before the RSVP deadline, message the people who have not replied, with the link. On a Lazo site the planner shows who has not replied, so this is a list, not a search.",
                "One week before the wedding, send the link once more to everyone with the final schedule and the shuttle times. Details change in the last month, and the site is where the current version lives.",
            ]),
            ("Destination and multi-day weddings", [
                "Go earlier: ten to twelve months for the save-the-date and the first version of the site, because guests are booking flights and taking leave. Put the whole weekend on the schedule as soon as it exists, with who is invited to what, so guests can book the right nights.",
                "For a multi-day celebration, an RSVP per event matters more than the deadline. Every Lazo design handles a multi-day schedule, and the RSVP note can ask which days a guest is coming.",
            ]),
            ("After the wedding", [
                "The site is still useful the week after, for the thank-yous and the photos, and for guests who want to sign the guestbook. On Lazo it flips to married mode the morning after on its own; send the link one last time with the first photos and it becomes the place the wedding lives.",
            ]),
        ],
        "practical": [
            ("Ask your stationer to leave room for the link on the save-the-date, not only the invitation.", "The save-the-date is the one guests pin to the fridge for months. A link there is read many times; a link on the invitation is read once."),
            ("Ask the hotel how long the block holds and put that date on the site before you send anything.", "Blocks commonly release 30 days out. A guest who sees the deadline in month one books; one who sees it in month six finds the block gone."),
            ("Ask your caterer for the final-count date before you set the RSVP deadline.", "The RSVP deadline should be two weeks before the caterer's date, and the invitation should carry the same date as the site."),
        ],
        "faqs": [
            ("Is it too early to send the website with the save-the-date?", "No, as long as it has the date, the city and where to stay. Travelling guests want it early, and everything else can be added later without changing the link."),
            ("Should the RSVP deadline be on the website or the invitation?", "Both, and the same date on each. Set it at least two weeks before your caterer's final-count date so you have time to chase the last replies."),
            ("How do we send the link?", "On the save-the-date and the invitation in print, and by message for reminders. On Lazo the link is meetlazo.com/w/ and your names; short enough to print and to say out loud."),
        ],
    },
}
