"""Lazo category taxonomy. LOCKED 7/14/26 — slugs shape every URL; changing one later breaks links.
Each category: slug (URL), label, places_queries (text-search strings), singular."""

CATEGORIES = [
    {"slug": "wedding-photographers",  "label": "Wedding Photographers",  "singular": "Wedding Photographer",  "places_queries": ["wedding photographer"]},
    {"slug": "wedding-videographers",  "label": "Wedding Videographers",  "singular": "Wedding Videographer",  "places_queries": ["wedding videographer", "wedding videography"]},
    {"slug": "wedding-venues",         "label": "Wedding Venues",         "singular": "Wedding Venue",         "places_queries": ["wedding venue"]},
    {"slug": "wedding-planners",       "label": "Wedding Planners",       "singular": "Wedding Planner",       "places_queries": ["wedding planner", "wedding coordinator"]},
    {"slug": "wedding-djs",            "label": "Wedding DJs",            "singular": "Wedding DJ",            "places_queries": ["wedding dj"]},
    {"slug": "wedding-florists",       "label": "Wedding Florists",       "singular": "Wedding Florist",       "places_queries": ["wedding florist"]},
    {"slug": "wedding-caterers",       "label": "Wedding Caterers",       "singular": "Wedding Caterer",       "places_queries": ["wedding caterer", "wedding catering"]},
    {"slug": "wedding-cakes",          "label": "Wedding Cakes & Desserts","singular": "Wedding Cake Baker",   "places_queries": ["wedding cake bakery", "wedding cakes"]},
    {"slug": "hair-and-makeup",        "label": "Hair & Makeup Artists",  "singular": "Hair & Makeup Artist",  "places_queries": ["bridal hair and makeup", "bridal makeup artist"]},
    {"slug": "wedding-officiants",     "label": "Wedding Officiants",     "singular": "Wedding Officiant",     "places_queries": ["wedding officiant"]},
    {"slug": "wedding-transportation", "label": "Wedding Transportation", "singular": "Wedding Transportation Company", "places_queries": ["wedding transportation", "limo service wedding"]},
    {"slug": "wedding-rentals",        "label": "Wedding Rentals",        "singular": "Wedding Rental Company","places_queries": ["wedding rentals", "event rentals wedding"]},
    {"slug": "wedding-bands",          "label": "Live Wedding Bands",     "singular": "Live Wedding Band",     "places_queries": ["wedding band live music"]},
    {"slug": "wedding-invitations",    "label": "Invitations & Stationery","singular": "Wedding Stationer",    "places_queries": ["wedding invitations", "wedding stationery"]},
    {"slug": "day-of-coordination",    "label": "Day-Of Coordinators",    "singular": "Day-Of Coordinator",    "places_queries": ["day of wedding coordinator"]},
]

BY_SLUG = {c["slug"]: c for c in CATEGORIES}
