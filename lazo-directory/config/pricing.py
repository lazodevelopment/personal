"""Per-category FAQ content for vendor pages. Ranges phrased honestly ("typically",
"many couples budget") — grounded in real operator pricing (founder's own package data
for photo/video) and broad market norms elsewhere. FAQPage schema is rendered from these.
{metro} and {category_singular} are substituted at build time."""

FAQS = {
    "wedding-photographers": [
        ("How much does a wedding photographer cost in {metro}?",
         "Most couples in {metro} budget between $1,500 and $3,500 for wedding photography. Packages at the lower end typically cover 6\u20138 hours with one shooter; higher tiers add a second shooter, engagement sessions, and albums. Always confirm exactly how many hours and edited images are included."),
        ("When should we book our wedding photographer?",
         "Photographers with strong reputations are commonly booked 9\u201314 months ahead \u2014 earlier for peak-season Saturdays. If your date is inside six months, ask about waitlists and cancellations; openings do appear."),
        ("What should we ask before booking?",
         "Ask to see two full galleries from real weddings (not highlight reels), confirm who will actually shoot your wedding, and get delivery timelines and image counts in the contract."),
    ],
    "wedding-videographers": [
        ("How much does a wedding videographer cost in {metro}?",
         "Wedding films in {metro} typically run $1,200 to $2,500 for core coverage \u2014 usually a highlight film plus ceremony coverage \u2014 with premium packages adding full features, drone work, and same-day edits. Confirm film length, delivery time, and music licensing in writing."),
        ("Do we really need both a photographer and videographer?",
         "They capture different things: photos are how you'll display the day; film is how you'll relive it \u2014 voices, vows, toasts, movement. Many couples who skip video name it their biggest regret; if budget forces a choice, consider a shorter film package over none."),
    ],
    "wedding-venues": [
        ("How much do wedding venues cost in {metro}?",
         "Venue pricing in {metro} spans widely \u2014 from around $3,000 for simpler spaces to $15,000+ for full-service estates and resorts. The real number to compare is total cost: ask what's included (tables, chairs, linens, staffing) and what's required (mandated caterers, minimums, service fees)."),
        ("What questions should we ask on a venue tour?",
         "Ask about rain plans, vendor restrictions, overtime fees, when vendors can load in, what the service charge covers, and exactly when you get the space. Get the full fee schedule in writing before signing."),
    ],
    "wedding-planners": [
        ("How much does a wedding planner cost in {metro}?",
         "Day-of coordination in {metro} commonly runs $800\u2013$2,000; partial planning $2,000\u2013$4,500; full-service planning often starts around $4,500 and scales with the wedding. Many planners saved couples more than their fee through vendor knowledge and mistake-avoidance."),
        ("Planner vs. venue coordinator \u2014 what's the difference?",
         "A venue coordinator works for the venue and manages the venue's responsibilities. A planner works for you \u2014 across every vendor, the timeline, and the day itself. Most couples need at least a day-of coordinator even at venues with great staff."),
    ],
    "wedding-djs": [
        ("How much does a wedding DJ cost in {metro}?",
         "Most {metro} couples spend $1,000\u2013$2,000 for a wedding DJ, typically covering 5\u20136 hours, sound, and MC duties. Lighting, ceremony audio, and photo booths are common add-ons. The MC skill matters as much as the music \u2014 ask how they handle announcements and reading a room."),
    ],
    "wedding-florists": [
        ("How much do wedding flowers cost in {metro}?",
         "Couples in {metro} commonly budget $1,500\u2013$4,000 for florals, with bridal bouquets, ceremony pieces, and centerpieces as the main drivers. Seasonal, locally available blooms stretch budgets furthest \u2014 share your palette and priorities and let the florist propose within them."),
    ],
    "wedding-caterers": [
        ("How much does wedding catering cost in {metro}?",
         "Catering in {metro} typically runs $40\u2013$120 per guest depending on service style \u2014 buffet and stations at the lower range, plated service higher. Confirm what staffing, rentals, and service fees are included; the per-plate number rarely tells the whole story."),
    ],
    "wedding-cakes": [
        ("How much does a wedding cake cost in {metro}?",
         "Wedding cakes in {metro} usually price by the slice \u2014 commonly $4\u2013$9 \u2014 so a 120-guest cake often lands between $500 and $1,000. Detailed sugar work and metallic finishes raise the number; many couples pair a smaller display cake with sheet cakes to serve everyone."),
    ],
    "hair-and-makeup": [
        ("How much is bridal hair and makeup in {metro}?",
         "Bridal hair and makeup in {metro} typically runs $150\u2013$350 for the bride (often including a trial), with bridal-party services around $75\u2013$150 per person per service. Book a trial 2\u20133 months out, and confirm on-site timing \u2014 morning schedules are where weddings run late."),
    ],
    "wedding-officiants": [
        ("How much does a wedding officiant cost in {metro}?",
         "Professional officiants in {metro} commonly charge $300\u2013$800, typically including a planning meeting, a personalized ceremony script, and rehearsal attendance at higher tiers. Ask to read or watch a past ceremony \u2014 their voice sets the tone for the most important twenty minutes of the day."),
    ],
    "wedding-transportation": [
        ("How much is wedding transportation in {metro}?",
         "Wedding transportation in {metro} typically runs $400\u2013$1,200 depending on vehicle and hours \u2014 classic cars and limos often carry 3\u20134 hour minimums. Book early for peak Saturdays, and build buffer time into the schedule for photos."),
    ],
    "wedding-rentals": [
        ("How much do wedding rentals cost in {metro}?",
         "Rental budgets in {metro} vary enormously with guest count and design \u2014 many couples land between $1,500 and $5,000 covering tables, chairs, linens, and tableware. Delivery, setup, and strike fees are often separate line items; confirm them before comparing quotes."),
    ],
    "wedding-bands": [
        ("How much does a live wedding band cost in {metro}?",
         "Live bands in {metro} commonly run $2,500\u2013$7,000 depending on size and demand. Many couples split the difference: band for the reception, DJ or playlist for ceremony and cocktail hour. Always watch live or recent unedited footage before booking."),
    ],
    "wedding-invitations": [
        ("How much do wedding invitations cost in {metro}?",
         "Couples typically spend $400\u2013$1,500 on invitation suites, driven by printing method \u2014 digital printing at the lower end, letterpress and foil above it. Order 10\u201315% extra for keepsakes and mistakes, and start 4\u20135 months before the wedding."),
    ],
    "day-of-coordination": [
        ("How much does day-of coordination cost in {metro}?",
         "Day-of coordination in {metro} commonly runs $800\u2013$2,000 \u2014 and \u201cday-of\u201d usually means the coordinator starts 4\u20136 weeks out: confirming vendors, building the timeline, and running rehearsal and wedding day so nobody in your family works your wedding."),
    ],
}

GENERIC_FAQ = [
    ("How does Lazo rank {category_plural} in {metro}?",
     "Rankings come from the Lazo Score \u2014 verified reviews weighted for recency \u2014 and are never sold. Vendors without verified reviews yet start at the community baseline of 65 and earn their score as verified reviews arrive."),
]
