# Venue photography manifest — Atavia's OWN photos only (portfolio-clause work).
#
# Upload to Firebase Storage bucket atavia-c29cd.firebasestorage.app under:
#     venue-photos/<venue-slug>-<n>.jpg        (n starts at 1)
# e.g. venue-photos/castle-hill-inn-1.jpg, venue-photos/castle-hill-inn-2.jpg
#
# The slug is the venue page filename (venues/<state>/<city>/<slug>.html).
# Then set the count here and rebuild. Never list photos that aren't uploaded.
#
# Resize to ~2000px on the long edge before upload to keep egress light.

PHOTOS = {
    # "castle-hill-inn": 3,
    # "willowdale-estate": 2,
}
