r"""patch_hub_june_1014.py - JC-LAZO-WWHUB-1014
The hub at /wedding-websites/ learns what shipped on 2026-10-14:
  - a new section before "Built for the day itself": June writes the site,
    the wedding party, where to stay, every photo (with screenshots
    ww-dates / ww-party / ww-stay / ww-gallery from generate/static);
  - "Everything included" tiles: travel and photos reworded, plus June,
    the wedding party and the hashtag;
  - one FAQ, in the page and in the FAQPage JSON-LD; featureList grows.
Idempotent: refuses to run twice.

  python wedding-websites\patch_hub_june_1014.py
"""
import json
import re
from pathlib import Path

P = Path(__file__).resolve().parent / "index.html"
s = P.read_text(encoding="utf-8")
TAG = "JC-LAZO-WWHUB-1014"
if TAG in s:
    raise SystemExit("already patched")


def rep(old, new):
    global s
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"anchor found {n}x: {old[:70]!r}")
    s = s.replace(old, new)


SECTION = f"""<!-- {TAG} -->
<section class="sell rv" id="june">
 <div class="sw">
  <p class="sk">Written with June</p>
  <h2>Tell June how you met. <em>She writes the rest.</em></h2>
  <p class="sp">Most couples stall at the blank page. Answer five questions and June, the planner inside Lazo, drafts your whole site from what you told her. She invents nothing, and she leaves alone anything you&rsquo;ve already written.</p>

  <div class="fgrid">
   <div class="fc wide">
    <div class="shot"><img src="/assets/ww-dates.webp" alt="A wedding website timeline of the couple's story: the night they met, moving in, the proposal" loading="lazy"><span class="new">New</span></div>
    <div class="ft"><p class="fk">Build it with June</p><h3>Your story, your FAQ, your travel page, in about twenty seconds.</h3><p>June writes how you met and the milestones since, suggests a hashtag, and drafts the dress code. She checks what the weather has done that week for the last three years, writes the driving notes and finds hotels near your venue. Then she picks the design that suits your photos. You read it over and publish.</p></div>
   </div>
   <div class="fc">
    <div class="shot"><img src="/assets/ww-party.webp" alt="The wedding party on a wedding website, with photos, roles and a tab for each side" loading="lazy"></div>
    <div class="ft"><p class="fk">The wedding party</p><h3>Everyone standing up with you.</h3><p>Names, roles, photos and a line about each. Put people on a side and guests get a tab for each, so the groom&rsquo;s aunt can finally match a face to &ldquo;the maid of honor.&rdquo;</p></div>
   </div>
   <div class="fc">
    <div class="shot"><img src="/assets/ww-stay.webp" alt="Hotel cards with a Book button, the room-block code with tap to copy, the book-by date and directions" loading="lazy"></div>
    <div class="ft"><p class="fk">Where to stay</p><h3>The block code, one tap to copy.</h3><p>Each hotel gets a card with Book, Directions and Call, plus the rate and the book-by date. Guests copy your room-block code with one tap. No hotel yet? The site suggests well-rated ones near the venue, and the nearest airports with the drive.</p></div>
   </div>
   <div class="fc">
    <div class="shot"><img src="/assets/ww-gallery.webp" alt="Every one of the couple's photos in a full-screen masonry wall" loading="lazy"></div>
    <div class="ft"><p class="fk">Every photo</p><h3>Twenty-four photos, full screen.</h3><p>Tap any photo for a full-screen viewer that swipes on phones. When you have more photos than your design has frames, &ldquo;See all&rdquo; opens every one in a wall.</p></div>
   </div>
  </div>

  <div class="fmore">
   <div><b>Your story in dates</b><span>The night you met, the first trip, the question, each with a photo.</span></div>
   <div><b>Your hashtag</b><span>On the header and the photo wall, copied in one tap.</span></div>
   <div><b>Day tabs</b><span>A weekend on three dates sits in three tabs, today&rsquo;s open first.</span></div>
   <div><b>Your words, your venue</b><span>Write every section headline yourself, or let June. Every line names your venue, never a template&rsquo;s.</span></div>
  </div>
 </div>
</section>

<!-- lz-sell -->
<section class="sell rv" id="day-of">"""

rep("""<!-- lz-sell -->
<section class="sell rv" id="day-of">""", SECTION)

rep("""<div><b>Travel &amp; stays</b><span>Hotel blocks, transport, parking and notes for out-of-town guests.</span></div>""",
    """<div><b>Travel &amp; stays</b><span>Hotel cards with Book and a one-tap block code, airports, driving notes and parking.</span></div>""")
rep("""<div><b>Photos &amp; your story</b><span>A gallery, how you met, and the moments you want everyone to know.</span></div>""",
    """<div><b>Photos &amp; your story</b><span>Twenty-four photos with a full-screen viewer, how you met, and your story in dates.</span></div>""")
rep("""  <div><b>RSVPs that file themselves</b>""",
    """  <div><b>Built with June</b><span>Five questions, and June drafts your story, FAQ, travel and design.</span></div>
  <div><b>The wedding party</b><span>Names, roles and photos, with a tab for each side.</span></div>
  <div><b>Your hashtag</b><span>On the header and the guests&rsquo; photo wall, copied in one tap.</span></div>
  <div><b>RSVPs that file themselves</b>""")

Q = "Can June write our wedding website for us?"
A = ("Yes. Answer five questions in the website editor, or ask June in the Lazo app. June drafts your story and "
     "milestones, a hashtag, the dress code, the typical weather that week, driving notes and hotels near your venue, "
     "and suggests a design that suits your photos. She only writes what you tell her, fills only the fields you have "
     "left empty, and nothing goes live until you publish.")
rep("""<details><summary>How long does it take to make a wedding website?</summary>""",
    f"""<details><summary>{Q}</summary><p>{A}</p></details>
 <details><summary>How long does it take to make a wedding website?</summary>""")

# JSON-LD: the FAQ and the feature list
m = re.search(r'<script type="application/ld\+json">(.*?)</script>', s, re.S)
data = json.loads(m.group(1))
for node in data["@graph"]:
    if node.get("@type") == "FAQPage":
        node["mainEntity"].insert(1, {"@type": "Question", "name": Q, "acceptedAnswer": {"@type": "Answer", "text": A}})
    if node.get("@type") == "SoftwareApplication":
        for f in ["Built with June", "Wedding party", "Hotel cards with room-block codes", "Wedding hashtag"]:
            if f not in node["featureList"]:
                node["featureList"].append(f)
s = s[:m.start(1)] + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + s[m.end(1):]

P.write_text(s, encoding="utf-8", newline="\n")
print("hub updated")
