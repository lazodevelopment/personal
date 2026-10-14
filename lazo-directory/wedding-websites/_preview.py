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
    "siteGallery": [f"{U}1519046904884-53103b34b206?auto=format&fit=crop&w=1200&q=74", f"{U}1473116763249-2faaef81ccda?auto=format&fit=crop&w=900&q=74", f"{U}1505142468610-359e7d316be0?auto=format&fit=crop&w=900&q=74", f"{U}1511285560929-80b456fea0bc?auto=format&fit=crop&w=900&q=74", f"{U}1465495976277-4387d4b0b4c6?auto=format&fit=crop&w=900&q=74", f"{U}1519225421980-715cb0215aed?auto=format&fit=crop&w=900&q=74", f"{U}1606216794074-735e91aa2c92?auto=format&fit=crop&w=900&q=74"],
    "passcode": "", "rsvpOpen": True, "coverUrl": "", "palette": "",
    # JC-LAZO-WWS-0929-PHOTOS: positioned photos + the guests' wall (add ?photos=1 to the preview URL to see it before the date)
    "heroPhoto": {"url": f"{U}1519741497674-611481863552?auto=format&fit=crop&w=1900&q=74", "x": 0.5, "y": 0.35, "zoom": 1.3},
    "storyPhoto": {"url": f"{U}1522673607200-164d1b6ce486?auto=format&fit=crop&w=1000&q=74", "x": 0.6, "y": 0.4, "zoom": 1.0},
    "siteGalleryFocus": [{"x": 0.5, "y": 0.2, "zoom": 1.6}, {"x": 0.5, "y": 0.5, "zoom": 1.0}, {"x": 0.3, "y": 0.5, "zoom": 1.2}],
    "guestPhotosOn": True, "guestPhotosNote": "",
    # JC-LAZO-WWS-0929-LIVE
    "timelineOn": True, "timeline": [{"time": "16:00", "label": "Guests arrive", "note": "Cold drinks on the porch", "dur": 30}, {"time": "16:30", "label": "Ceremony", "note": "", "dur": 30}, {"time": "17:15", "label": "Cocktail hour", "note": "", "dur": 75}, {"time": "18:30", "label": "Dinner", "note": "", "dur": 90}, {"time": "20:00", "label": "First dance, then everyone", "note": "", "dur": 150}, {"time": "22:30", "label": "Send-off", "note": "Sparklers by the barn", "dur": 15}],
    "events": [{"name": "Welcome dinner", "dateIso": "2027-06-11", "time": "6:30 PM", "venueName": "The Sedona Inn", "venueAddress": "120 Main St, Sedona, AZ", "note": "Casual, come as you are", "dress": "", "rsvp": True}, {"name": "Farewell brunch", "dateIso": "2027-06-13", "time": "10:00 AM", "venueName": "The Orchard House", "venueAddress": "1400 Old Mill Road, Sedona, Arizona", "note": "", "dress": "", "rsvp": True}],
    "hotelAddress": "120 Main St, Sedona, AZ", "guestPhotosHold": False,
    # JC-LAZO-WWS-1014-PLUS: party, hotels, airports, hashtag, story in dates
    "hashtag": "SarahSaysYesToMike", "partySides": ["Sarah's side", "Mike's side"],
    "weddingParty": [
        {"name": "Jenna Cole", "role": "Maid of honor", "side": "a", "photo": f"{U}1494790108377-be9c29b29330?auto=format&fit=crop&w=400&q=74", "note": "Sister, and the keeper of every embarrassing story."},
        {"name": "Ava Lin", "role": "Bridesmaid", "side": "a", "photo": "", "note": ""},
        {"name": "Marcus Reed", "role": "Best man", "side": "b", "photo": f"{U}1500648767791-00dcc994a43e?auto=format&fit=crop&w=400&q=74", "note": "Roommate for six years."},
        {"name": "Dev Patel", "role": "Groomsman", "side": "b", "photo": "", "note": ""},
        {"name": "Rev. Ann Hale", "role": "Officiant", "side": "", "photo": "", "note": ""}],
    "hotels": [
        {"name": "The Sedona Inn", "address": "120 Main St, Sedona, AZ", "url": "https://example.com/book", "code": "SARAHMIKE27", "deadline": "May 1, 2027", "rate": "$189 a night", "phone": "(928) 555-0100", "note": "Shuttle to the venue from 3:30", "block": True}],
    "airports": [], "drivingNotes": "From Phoenix take I-17 N to exit 298, then 179 N into Sedona. The last mile to the Orchard House is gravel.",
    "milestones": [
        {"when": "August 2019", "title": "The playlist argument", "text": "An hour by the speaker at Dana's party.", "photo": f"{U}1529634806980-85c3dd6d34ac?auto=format&fit=crop&w=600&q=74"},
        {"when": "Spring 2022", "title": "Moved in", "text": "One apartment, two record collections.", "photo": ""},
        {"when": "New Year's Eve 2025", "title": "He asked", "text": "On the roof, at midnight, during the wrong song.", "photo": ""}],
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
