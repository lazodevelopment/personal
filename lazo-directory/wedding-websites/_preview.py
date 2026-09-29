"""_preview.py - renders a template the way the worker does for a live couple
site (window.LAZO_SITE injected, demo bar gone) into _preview/<slug>.html so
the hydrated layout and the couple's-song player can be checked locally.

  python wedding-websites\\_preview.py shore [preview-mp3-url]
"""
import json, sys, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
slug = sys.argv[1] if len(sys.argv) > 1 else "shore"
src = sys.argv[2] if len(sys.argv) > 2 else ""
html = (ROOT / slug / "index.html").read_text(encoding="utf-8")
U = "https://images.unsplash.com/photo-"
payload = {
    "slug": "sarah-and-mike", "names": "Sarah & Mike", "dateIso": "2027-06-12",
    "story": "We met at a friend's backyard party and argued about the playlist for an hour. We've been arguing about playlists ever since.",
    "venueName": "The Orchard House", "venueAddress": "1400 Old Mill Road, Sedona, Arizona",
    "ceremonyTime": "4:30 pm", "cocktailTime": "5:15 pm", "receptionTime": "6:30 pm", "sendOffTime": "10:30 pm",
    "dressCode": "Garden cocktail", "hotelBlock": "Rooms held at the Sedona Inn under Sarah & Mike through May 1",
    "transport": "A shuttle runs from the inn every half hour from 3:30", "parking": "Lot behind the barn",
    "travelNotes": "The road in is gravel for the last mile.",
    "registryLinks": [{"label": "Crate & Barrel", "url": "https://www.crateandbarrel.com"}], "registryNote": "",
    "rsvpBy": "May 1, 2027", "vendorTeam": [{"category": "Photographer", "name": "Atavia Weddings", "vendorId": "ChIJdemo", "url": "https://meetlazo.com/phoenix/wedding-photographers/atavia-weddings/"}, {"category": "Venue", "name": "The Orchard House"}],
    "siteGallery": [f"{U}1519046904884-53103b34b206?auto=format&fit=crop&w=1200&q=74", f"{U}1473116763249-2faaef81ccda?auto=format&fit=crop&w=900&q=74", f"{U}1505142468610-359e7d316be0?auto=format&fit=crop&w=900&q=74"],
    "passcode": "", "rsvpOpen": True, "coverUrl": "", "palette": "",
    # JC-LAZO-WWS-0929-PHOTOS: positioned photos + the guests' wall (add ?photos=1 to the preview URL to see it before the date)
    "heroPhoto": {"url": f"{U}1519741497674-611481863552?auto=format&fit=crop&w=1900&q=74", "x": 0.5, "y": 0.35, "zoom": 1.3},
    "storyPhoto": {"url": f"{U}1522673607200-164d1b6ce486?auto=format&fit=crop&w=1000&q=74", "x": 0.6, "y": 0.4, "zoom": 1.0},
    "siteGalleryFocus": [{"x": 0.5, "y": 0.2, "zoom": 1.6}, {"x": 0.5, "y": 0.5, "zoom": 1.0}, {"x": 0.3, "y": 0.5, "zoom": 1.2}],
    "guestPhotosOn": True, "guestPhotosNote": "",
    # JC-LAZO-WWS-0929-LIVE
    "timelineOn": True, "timeline": [{"time": "16:00", "label": "Guests arrive", "note": "Cold drinks on the porch", "dur": 30}, {"time": "16:30", "label": "Ceremony", "note": "", "dur": 30}, {"time": "17:15", "label": "Cocktail hour", "note": "", "dur": 75}, {"time": "18:30", "label": "Dinner", "note": "", "dur": 90}, {"time": "20:00", "label": "First dance, then everyone", "note": "", "dur": 150}, {"time": "22:30", "label": "Send-off", "note": "Sparklers by the barn", "dur": 15}],
    "seatingOn": True, "mealOptions": ["Chicken", "Salmon", "Garden risotto"], "galleryUrl": "https://meetlazo.com/g/sarah-and-mike", "translateOn": True,
    "song": {"title": "Perfect", "artist": "Ed Sheeran", "art": "", "trackId": "", "autoplay": True,
             "src": ("https://meetlazo.com/music/preview?u=" + urllib.parse.quote(src, safe="")) if src else ""} if src else None,
}
inject = "<script>window.LAZO_SITE=" + json.dumps(payload).replace("<", "\\u003c") + ";</script>\n"
html = html.replace("</head>", inject + "</head>", 1)
out = ROOT / "_preview" / f"{slug}.html"
out.parent.mkdir(exist_ok=True)
out.write_text(html, encoding="utf-8", newline="\n")
print(f"wrote {out.relative_to(ROOT)}")
