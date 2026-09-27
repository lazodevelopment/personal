"""Planning-tool guides.  JC-LAZO-PLAN-0922-001

The "Your tools" group of the /planning/ cluster. The first guide answers
"best wedding planning apps", the query Zola's expert-advice article ranks for
with a list that puts Zola first. Ours compares the same apps honestly, says
what each is actually for, and makes the case for Lazo on the two things the
others cannot claim: rankings that are not for sale, and June. Same schema as
config/planning.py: question, short, group, cats, related, lede, sections
(heading, [html paragraphs]), practical [(what, why)], faqs [(q, a)].
"""

_TABLE = """<table class="cmp"><thead><tr><th>App</th><th>Best for</th><th>Free tier</th><th>Vendor directory</th><th>How vendors rank</th><th>AI planner</th></tr></thead><tbody>
<tr><td><strong>Lazo</strong></td><td>Finding and booking vendors you can verify, then planning the day in one place</td><td>Everything, no caps</td><td>119,000+ vendors, 108 metros, every business verified</td><td>Verified reviews from couples who booked; placement is not for sale</td><td>June, included</td></tr>
<tr><td><strong>Zola</strong></td><td>Registry, and a website that plugs into it</td><td>Planning tools free; registry earns the revenue</td><td>Large</td><td>Vendors buy advertising and placement</td><td>Basic suggestions</td></tr>
<tr><td><strong>The Knot</strong></td><td>The biggest directory and the longest-running checklists</td><td>Free</td><td>Largest</td><td>Vendors pay for tiers and featured spots</td><td>None to speak of</td></tr>
<tr><td><strong>WeddingWire</strong></td><td>Reviews at volume (same company as The Knot)</td><td>Free</td><td>Large</td><td>Paid tiers</td><td>None</td></tr>
<tr><td><strong>WithJoy</strong></td><td>A beautiful free website with guest list and messaging</td><td>Free</td><td>None</td><td>Not applicable</td><td>None</td></tr>
<tr><td><strong>Appy Couple</strong></td><td>A polished guest-facing app for the wedding weekend</td><td>Paid</td><td>None</td><td>Not applicable</td><td>None</td></tr>
</tbody></table>
<p class="cmp-note">Details as of September 2026; the other apps change their plans often, so check their pricing pages before you commit.</p>"""

APP_GUIDES = {
    "best-wedding-planning-apps": {
        "question": "What are the best wedding planning apps?",
        "short": "The best wedding planning apps",
        "group": "Your tools",
        "cats": ["wedding-planners", "day-of-coordination", "wedding-venues"],
        "related": ["how-to-make-a-wedding-website", "what-to-put-on-your-wedding-website", "when-to-book", "cost"],
        "lede": "The best wedding planning app is the one that does the job you actually have this month: finding vendors you can trust, keeping the guest list and budget in one place, and building a website that answers your guests' questions. Most couples end up with two or three apps, because the big names each do one thing well and the rest half-heartedly. Here is what each one is for, what it costs, and how it decides which vendors to show you, which matters more than any feature list.",
        "sections": [
            ("Start with the question no app answers on its front page", [
                "Every planning app has a checklist, a budget and a guest list. Those are table stakes and they all work. The difference that shapes your whole wedding is the vendor directory underneath, and specifically <strong>how a vendor gets to the top of it</strong>. On most marketplaces the answer is money: vendors buy tiers, featured placements and ad slots, and the ranking you scroll is partly an ad. On Lazo a vendor's position comes from verified reviews left by couples who actually booked them, weighted toward recent weddings, and no plan a vendor can buy touches it. If you remember one thing from this page, remember to ask that question of every app.",
                "The second question is whether the reviews are real. Anyone can leave five stars on most directories. Lazo only counts a review when the couple booked that vendor, either through their Lazo inquiry thread or by uploading the contract or receipt. That is why there are fewer reviews on a Lazo listing than on the same business elsewhere, and why they are worth more.",
            ]),
            ("The apps, compared", [
                _TABLE,
            ]),
            ("1. Lazo: for finding vendors you can verify, then planning with June", [
                "Lazo is a vendor marketplace first and a planner second, which is the order most couples actually need. Every one of the 119,000 businesses has been checked, and a claimed profile means the owner is really there to answer. You search by city and category, message vendors in one thread each, and a proposal, a contract and the payment all land in that same thread, so nothing lives in a stray email.",
                "The planning side is free with no caps: guest list with RSVPs from your website, budget with real price ranges for your city, reception and ceremony seating with meals per table, a day-of timeline that sends each vendor their own page, a shopping list, a dream board, a marriage-license lookup for your county, and a wedding website with 20 designs. <strong>June</strong> is the AI planner built into all of it. She knows your date, budget, guest list and bookings, seats your guests from your parties and sides, drafts messages to vendors in your voice, and tells you what to book next and whether it is late. There is no paid tier for couples; the business is an optional plan for vendors who want more tools, and it never changes who ranks where.",
                "Where Lazo is weaker: it is newer, so the registry is a link to wherever yours already lives rather than a store of its own, and there is no printed-invitation shop. If your wedding is registry-first, pair Lazo with Zola or Amazon for that part.",
            ]),
            ("2. Zola: for the registry, and a website that feeds it", [
                "Zola began as a registry and is still best at it. You can register for items, cash funds and experiences in one place, and the free wedding website ties into it cleanly. The planning tools that came later, the checklist, guest list and budget, are competent, and the paper suite is genuinely good if you want invitations to match the site.",
                "What to know before you choose it: the registry is where Zola earns its revenue, so the whole experience nudges toward it, and the vendor directory, which is large, ranks vendors partly on what they pay for. Zola's app is a fine companion to Lazo when the registry is the thing you need.",
            ]),
            ("3. The Knot: for sheer size and the checklist everyone's mother used", [
                "The Knot has the largest directory and the most exhaustive checklist, with two decades of planning content behind it. If you want a list of every task from eighteen months out to the honeymoon, it has one. The guest list and website work; the app is busy.",
                "The trade-off is the business model. Vendors pay The Knot for placement tiers and featured spots, so the top of any search is a mix of quality and spend, and your inquiry may go to several vendors at once. Use it for research and the checklist; verify the vendor somewhere the ranking is not for sale before you book.",
            ]),
            ("4. WeddingWire: for reading a lot of reviews", [
                "WeddingWire and The Knot are the same company, so the directory and the vendor pricing model overlap. WeddingWire's strength is review volume: many vendors have hundreds. Read them for pattern, not for the star average, and remember that any review can be left by anyone. Its planning tools mirror The Knot's.",
            ]),
            ("5. WithJoy: for a beautiful free website and nothing else", [
                "If all you need is a wedding website with RSVPs, a guest list and a way to message guests, WithJoy does it well and does it free. There is no vendor directory and no budget to speak of, which is exactly why it stays simple. Couples often run WithJoy for the site and something else for the planning; Lazo's website builder covers the same ground if you would rather keep it in one place.",
            ]),
            ("6. Appy Couple: for a guest-facing app on the weekend itself", [
                "Appy Couple is a paid, polished app that guests download for the schedule, directions and photos over the wedding weekend. It is a guest-experience product more than a planning one. Worth it for a large destination wedding with a full itinerary; unnecessary for most.",
            ]),
            ("How to combine them without losing your mind", [
                "Pick one app as the source of truth for the guest list and the budget and never let a second app own a copy. Lazo imports a guest list from The Knot, Zola or Folia as a CSV in one step, and June reads a pasted budget or vendor list, so switching is an afternoon, not a project.",
                "Keep vendor conversations where the contract will be signed. A thread that holds the proposal, the signed agreement and the paid retainer is the record you will want the week of the wedding, and the one your planner or day-of coordinator can be handed.",
                "Give your registry its own home and link to it from the website. Registry apps are good at registries; planning apps that try to be stores are a distraction.",
            ]),
        ],
        "practical": [
            ("Ask each app how a vendor reaches the top of a search.", "If the honest answer involves the vendor paying, treat the list as advertising with reviews attached. On Lazo the answer is verified bookings, and nothing a vendor pays for changes it."),
            ("Check whether reviews require a booking.", "A five-star average built from anyone who wants to leave one tells you less than ten reviews from couples who provably hired the business."),
            ("Import, don't retype.", "Export your guest list as a CSV from wherever it lives and import it once. Every app on this page can export; Lazo imports The Knot, Zola and Folia formats directly."),
            ("Keep one thread per vendor.", "The app that holds the proposal, the contract and the payment for a vendor is the one you will be searching at 11 pm the night before. Make sure it is the same app for every vendor."),
            ("Turn on the website before you send save-the-dates.", "Guests go looking the day the card arrives. Lazo, Zola and WithJoy all publish in minutes; do it first and fill it in after."),
        ],
        "faqs": [
            ("Is Lazo really free for couples?", "Yes. Every couple tool on Lazo is free with no guest cap, no ads and no upsell, and Lazo takes nothing from what you pay vendors. The business is an optional plan for vendors who want extra tools, which never affects rankings."),
            ("Which wedding planning app has the best vendor directory?", "The Knot has the largest. Lazo has the only one where every business is verified and placement is not for sale, with 119,000 vendors across 108 metros. If your city is on Lazo, start there and use The Knot to fill gaps."),
            ("Do I need more than one app?", "Usually two: one for vendors and planning, one for the registry. Lazo plus a registry app covers almost every wedding. Add a guest-facing weekend app only for a large destination wedding."),
            ("Which app is best on Android?", "Lazo, Zola, The Knot and WithJoy all ship Android and iPhone apps with the same features on both. Appy Couple's guest app is on both stores too."),
            ("Can I move my guest list from The Knot or Zola to Lazo?", "Yes. Export it as a CSV and import it in one step. June will also read a pasted budget or vendor list and set the matching parts of your plan."),
            ("What is June?", "June is the AI planner inside Lazo. She knows your date, budget, guest list and bookings, drafts your vendor messages, seats your guests, and tells you what to book next and whether it is late. She is included free."),
        ],
    },
}
