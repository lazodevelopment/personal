"""Booking-order data for /when-to-book/.  JC-LAZO-ASK-0916-001

Lives in config/ because both generate/build.py and deploy/render_pages.py need
it, and deploy/ is not an importable package - build.py importing from a deploy
script would be backwards even if it worked.

The ONE_PER_DAY split is the actual insight on that page: urgency is set by
whether a vendor can serve more than one wedding on a date, not by category.
"""

# JC-LAZO-ASK-0916-001: which categories can only serve one wedding a day. That
# distinction - not the category - is what makes a booking urgent, and it is what
# splits /when-to-book/ into two waves.
ONE_PER_DAY = ["wedding-venues", "wedding-photographers", "wedding-planners",
               "wedding-videographers", "wedding-officiants", "wedding-bands",
               "wedding-djs", "day-of-coordination"]
WHEN_LABEL = {
    "wedding-venues": "12-18 months out", "wedding-planners": "12-18 months out",
    "wedding-photographers": "9-14 months out", "wedding-bands": "9-15 months out",
    "wedding-videographers": "8-12 months out", "wedding-djs": "6-9 months out",
    "wedding-officiants": "4-8 months out", "day-of-coordination": "4-8 months out",
    "wedding-caterers": "8-12 months out", "wedding-florists": "6-9 months out",
    "hair-and-makeup": "6-9 months out", "wedding-rentals": "6-9 months out",
    "wedding-invitations": "4-5 months out", "wedding-transportation": "4-8 months out",
    "wedding-cakes": "4-6 months out",
}
WTB_FAQS = [
    ("When should you start booking wedding vendors?",
     "Book the venue first, because it sets your date and nothing else can be confirmed without one - typically 12 to 18 months ahead for a peak Saturday. Then the vendors who can only take one wedding a day: photographer, planner, band and officiant."),
    ("Which wedding vendors book up first?",
     "The ones who can only serve one wedding per day and are chosen by reputation - venues, photographers, planners and live bands. Florists, caterers and stationers can take several weddings on the same date, so they are far less urgent."),
    ("Is six months too late to book wedding vendors?",
     "No. Cancellations happen constantly and vendors keep waitlists, so ask about availability rather than assuming. Leading with your date in the first message, and being flexible about the day of the week, transforms what is available."),
    ("What can't you rush when planning a wedding?",
     "Invitations need four to five months from design to mailbox, dress alterations need six to eight weeks and several fittings, and hand-lettered stationery or a ketubah is made to order. Ordering these late does not cost more - it simply does not work."),
]

