"""patch_hub_sell.py - JC-LAZO-WWI-0929-SELL
Sells the wedding website on meetlazo.com/wedding-websites/: a "Built for the
day itself" section after the plum band (ten feature cards with real
screenshots from /assets/ww-*.webp, four more in a strip), an honest
comparison table against The Knot and Zola, and five new rows in the
"Everything included" grid. Idempotent: the block sits between
<!-- lz-sell --> and <!-- /lz-sell -->, the CSS between the same markers in
<style>, and the grid rows are added once.

  python wedding-websites\\patch_hub_sell.py
Then: sync_dist.py + upload_r2.py --prefix wedding-websites --prefix assets/ww-
Screenshots: python wedding-websites\\_mock_now.py + headless Chrome (see the
2026-09-29 README note); WebP copies live in generate/static/ww-*.webp so
build.py ships them to /assets/.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
P = ROOT / "index.html"
s = P.read_text(encoding="utf-8")

CSS = """
/* ---- lz-sell: built for the day itself ---- */
.sell{background:#fff;border-top:1px solid var(--goldSoft);border-bottom:1px solid var(--goldSoft);padding:96px 22px}
.sell .sw{max-width:1180px;margin:0 auto}
.sell .sk{font-size:11px;letter-spacing:.42em;text-transform:uppercase;color:#8A6A2F;text-align:center;margin-bottom:12px}
.sell h2{font:500 clamp(30px,4.6vw,46px)/1.12 "Cormorant Garamond",serif;color:var(--plum);text-align:center;margin:0 auto 12px;max-width:22ch}
.sell h2 em{font-style:italic;color:var(--gold)}
.sell .sp{color:var(--muted);text-align:center;max-width:58ch;margin:0 auto;font-size:16.5px}
.fgrid{display:grid;gap:22px;margin-top:48px}
@media(min-width:700px){.fgrid{grid-template-columns:1fr 1fr}}
@media(min-width:1040px){.fgrid{grid-template-columns:1fr 1fr 1fr}}
.fc{background:var(--ivory);border:1px solid var(--goldSoft);border-radius:20px;overflow:hidden;display:flex;flex-direction:column;transition:transform .3s ease,box-shadow .3s ease}
.fc:hover{transform:translateY(-4px);box-shadow:0 30px 50px -30px rgba(36,30,43,.45)}
.fc.wide{grid-column:1/-1;flex-direction:row;align-items:stretch}
.fc.wide .shot{flex:1.4;aspect-ratio:auto;min-height:320px}
.fc.wide .ft{flex:1;align-self:center}
@media(max-width:699px){.fc.wide{flex-direction:column}.fc.wide .shot{min-height:0;aspect-ratio:16/10}}
.fc .shot{aspect-ratio:16/10;background:#EFE9E0 center/cover no-repeat;border-bottom:1px solid var(--goldSoft);position:relative}
.fc .shot img{width:100%;height:100%;object-fit:cover;object-position:top;display:block}
.fc .shot.phone-in{background:var(--plumDeep);display:flex;justify-content:center;align-items:flex-end;padding:22px 22px 0}
.fc .shot.phone-in img{width:min(62%,230px);height:auto;border-radius:22px 22px 0 0;border:6px solid #241E2B;border-bottom:0;box-shadow:0 20px 40px -20px rgba(0,0,0,.7)}
.fc .ft{padding:22px 24px 26px}
.fc .fk{font-size:10.5px;letter-spacing:.34em;text-transform:uppercase;color:#8A6A2F;margin-bottom:8px}
.fc h3{font:600 23px/1.15 "Cormorant Garamond",serif;color:var(--plum);margin:0 0 8px}
.fc p{font-size:14.5px;color:#6B6B66;line-height:1.6;margin:0}
.fc .new{position:absolute;top:12px;left:12px;background:var(--gold);color:var(--plumDeep);font-size:10px;letter-spacing:.24em;text-transform:uppercase;font-weight:600;border-radius:999px;padding:5px 10px}
.fmore{display:grid;gap:14px;margin-top:22px;grid-template-columns:1fr 1fr}
@media(min-width:900px){.fmore{grid-template-columns:repeat(4,1fr)}}
.fmore div{background:var(--ivory);border:1px solid var(--goldSoft);border-radius:14px;padding:16px 18px}
.fmore b{display:block;color:var(--plum);font-weight:500;margin-bottom:3px}
.fmore span{font-size:13.5px;color:#6B6B66}
.cmp{margin-top:84px}
.cmp h3{font:500 clamp(26px,3.6vw,36px)/1.15 "Cormorant Garamond",serif;color:var(--plum);text-align:center;margin:0 auto 10px;max-width:24ch}
.cmp .sp{margin-bottom:30px}
.cmpt{width:100%;max-width:920px;margin:0 auto;border-collapse:separate;border-spacing:0;background:var(--ivory);border:1px solid var(--goldSoft);border-radius:18px;overflow:hidden;font-size:14.5px}
.cmpt th,.cmpt td{padding:13px 16px;text-align:center;border-bottom:1px solid var(--goldSoft);vertical-align:middle}
.cmpt tr:last-child td{border-bottom:0}
.cmpt th{background:var(--plum);color:var(--ivory);font-weight:400;font-size:13px;letter-spacing:.06em}
.cmpt th:first-child,.cmpt td:first-child{text-align:left}
.cmpt td:first-child{color:var(--ink)}
.cmpt td:nth-child(2){background:rgba(217,183,124,.14);font-weight:500;color:var(--plum)}
.cmpt .y{color:#2E8B6B;font-weight:600}.cmpt .n{color:#B8AFA6}.cmpt .p{color:#8A6A2F;font-size:13px}
.cmp .fine{text-align:center;font-size:12px;color:var(--muted);margin-top:14px;letter-spacing:.02em}
.sell .scta{text-align:center;margin-top:44px}
.sell .scta a{display:inline-block;background:var(--plum);color:var(--ivory);text-decoration:none;border-radius:999px;padding:16px 34px;font-size:15px;letter-spacing:.04em}
.sell .scta a:hover{background:var(--plumDeep)}
.sell .scta p{font-size:13px;color:var(--muted);margin-top:12px}
@media(max-width:600px){.cmpt{font-size:13px}.cmpt th,.cmpt td{padding:10px 8px}}
/* ---- /lz-sell ---- */
"""

A = "/assets"
HTML = f"""<!-- lz-sell -->
<section class="sell rv" id="day-of">
 <div class="sw">
  <p class="sk">Built for the day itself</p>
  <h2>Every other wedding website is a brochure. <em>Yours works the room.</em></h2>
  <p class="sp">The Knot and Zola give you a pretty page with your date on it. Lazo's site knows your timeline, your seating chart, your guest list and your vendors &mdash; because it's the same account &mdash; so on the day it does things a brochure can't.</p>

  <div class="fgrid">
   <div class="fc wide">
    <div class="shot"><img src="{A}/ww-hero.webp" alt="A wedding website header with the couple's own photo positioned exactly where they want it" loading="lazy"><span class="new">New</span></div>
    <div class="ft"><p class="fk">Your photos, placed</p><h3>Drag it, zoom it, see it on a phone before you publish.</h3><p>Put your own photo in the header and beside your story. Drag until the two of you are where you want them, zoom in, check the phone frame &mdash; the site shows exactly what you saw. No cropping surprises.</p></div>
   </div>
   <div class="fc">
    <div class="shot"><img src="{A}/ww-wall.webp" alt="A photo wall on the wedding website filled with pictures guests added from their phones" loading="lazy"><span class="new">New</span></div>
    <div class="ft"><p class="fk">Guests' photos, live</p><h3>Every phone at the wedding is now your second photographer.</h3><p>From the day itself, guests tap one button and their photos land on your site for everyone. Approve them first if you like, remove any you don't, download the whole wall as one zip.</p></div>
   </div>
   <div class="fc">
    <div class="shot"><img src="{A}/ww-hourbyhour.webp" alt="The day hour by hour with the current moment marked Now and the next one marked Next" loading="lazy"><span class="new">New</span></div>
    <div class="ft"><p class="fk">Hour by hour</p><h3>On the day, the site knows what's happening <em>now</em>.</h3><p>Your planning timeline becomes the guests' schedule. On the wedding day it marks the moment you're in and the one that's next, so nobody has to ask when dinner is. One tap adds the whole day to their calendar.</p></div>
   </div>
   <div class="fc">
    <div class="shot"><img src="{A}/ww-seat.webp" alt="A guest types their name and the site shows their table, seat, tablemates and a map of the room" loading="lazy"><span class="new">New</span></div>
    <div class="ft"><p class="fk">Find your table</p><h3>No escort-card scramble.</h3><p>Guests type their name and get their table, their seat, who they're sitting with, and a little map of the room with their table lit up. It reads straight from your seating chart.</p></div>
   </div>
   <div class="fc">
    <div class="shot"><img src="{A}/ww-rsvp.webp" alt="An RSVP form already filled in for the guest, with dinner choices, plus-one count and which events they'll join" loading="lazy"><span class="new">New</span></div>
    <div class="ft"><p class="fk">Personal RSVP links</p><h3>"Hi Rosa" &mdash; and the form is already filled in.</h3><p>Every household gets its own link. The form opens with their names, how many they may bring, your dinner choices and the events they're invited to. The reply lands on the right guest, not in a pile to sort.</p></div>
   </div>
   <div class="fc">
    <div class="shot"><img src="{A}/ww-forecast.webp" alt="The venue card with the wedding-day forecast: high, low, chance of rain and sunset" loading="lazy"><span class="new">New</span></div>
    <div class="ft"><p class="fk">The forecast</p><h3>"Bring a layer for the evening."</h3><p>Inside two weeks, the site shows the forecast for your venue &mdash; high, low, rain odds, sunset &mdash; and one plain line of advice. Directions to the venue and to the hotel are one tap.</p></div>
   </div>
   <div class="fc">
    <div class="shot"><img src="{A}/ww-weekend.webp" alt="Welcome dinner and farewell brunch cards, each with directions and add-to-calendar" loading="lazy"><span class="new">New</span></div>
    <div class="ft"><p class="fk">The weekend</p><h3>Three days, one celebration.</h3><p>Mehndi, sangeet, welcome dinner, farewell brunch &mdash; add each with its own place and time. Guests say which they'll join right on the RSVP, and it shows up on your guest list.</p></div>
   </div>
   <div class="fc">
    <div class="shot"><img src="{A}/ww-spanish.webp" alt="The couple's story shown in Spanish after a guest picked their language" loading="lazy"><span class="new">New</span></div>
    <div class="ft"><p class="fk">In their language</p><h3>Abuela reads it in Spanish.</h3><p>A small language pill on your site translates every line into twenty languages on demand. Your parents' friends, the cousins abroad, the in-laws &mdash; everyone reads the same page in their own words.</p></div>
   </div>
   <div class="fc">
    <div class="shot"><img src="{A}/ww-slideshow.webp" alt="A full-screen slideshow of the guests' photos for a TV at the reception" loading="lazy"><span class="new">New</span></div>
    <div class="ft"><p class="fk">On the TV</p><h3>The reception watches itself.</h3><p>Open your site with one extra word in the link and it becomes a full-screen slideshow of the photos guests are adding, refreshing itself all night. Put it on the bar TV.</p></div>
   </div>
   <div class="fc">
    <div class="shot"><img src="{A}/ww-cards.webp" alt="Printable table cards with a QR code that opens the photo wall" loading="lazy"><span class="new">New</span></div>
    <div class="ft"><p class="fk">Table cards</p><h3>Print six to a page, done.</h3><p>QR cards for every table: share your photos, request a song, or both. Guests scan, the site opens, the photo lands. Nothing to install.</p></div>
   </div>
   <div class="fc wide">
    <div class="shot phone-in"><img src="{A}/ww-phone-wall.webp" alt="The photo wall on a phone" loading="lazy"></div>
    <div class="ft"><p class="fk">And the rest</p><h3>The night before, the DJ, the credits.</h3><p>Send everyone coming one email the day before &mdash; the schedule, the map, parking, the forecast, and each guest's table. Give the DJ a live page of every song request. Credit your vendors with links, so a guest planning their own wedding can book the photographer they're watching work.</p></div>
   </div>
  </div>

  <div class="fmore">
   <div><b>The day-before note</b><span>One email to everyone with an address: timeline, map, parking, forecast, their table.</span></div>
   <div><b>The DJ's page</b><span>Every request from the RSVP form and the request cards, refreshing itself all night.</span></div>
   <div><b>Vendors you can book</b><span>Your credits link to each vendor's Lazo page with a Check-your-date button.</span></div>
   <div><b>Ask June</b><span>A concierge on every site: what to wear, where to stay, when to arrive.</span></div>
  </div>

  <div class="cmp">
   <h3>What you get here that you don't get there</h3>
   <p class="sp">Both of those sites are lovely brochures. This is the part after "Save the date".</p>
   <table class="cmpt">
    <thead><tr><th>On the wedding website</th><th>Lazo</th><th>The Knot</th><th>Zola</th></tr></thead>
    <tbody>
     <tr><td>Designs, RSVP, registry, travel, passcode</td><td class="y">&#10003;</td><td class="y">&#10003;</td><td class="y">&#10003;</td></tr>
     <tr><td>Guests add photos from their phones, with approval, TV slideshow and zip download</td><td class="y">&#10003;</td><td class="n">&mdash;</td><td class="n">&mdash;</td></tr>
     <tr><td>Hour-by-hour schedule that marks <em>Now</em> and <em>Next</em> on the day</td><td class="y">&#10003;</td><td class="n">&mdash;</td><td class="n">&mdash;</td></tr>
     <tr><td>Find your table, with tablemates and a room map</td><td class="y">&#10003;</td><td class="n">&mdash;</td><td class="n">&mdash;</td></tr>
     <tr><td>Personal RSVP links that arrive pre-filled and matched to the guest</td><td class="y">&#10003;</td><td class="p">by name lookup</td><td class="p">by name lookup</td></tr>
     <tr><td>Wedding-day forecast for the venue, on the site</td><td class="y">&#10003;</td><td class="n">&mdash;</td><td class="n">&mdash;</td></tr>
     <tr><td>One-tap translation into 20 languages</td><td class="y">&#10003;</td><td class="n">&mdash;</td><td class="n">&mdash;</td></tr>
     <tr><td>Vendor credits you can book from</td><td class="y">&#10003;</td><td class="n">&mdash;</td><td class="n">&mdash;</td></tr>
     <tr><td>The morning after: days married, chapters, a guestbook</td><td class="y">&#10003;</td><td class="n">&mdash;</td><td class="n">&mdash;</td></tr>
     <tr><td>Same account as your vendors, contracts and payments</td><td class="y">&#10003;</td><td class="n">&mdash;</td><td class="n">&mdash;</td></tr>
     <tr><td>Free, no ads, no upsell, no card</td><td class="y">&#10003;</td><td class="p">free, with upsells</td><td class="p">free, with upsells</td></tr>
    </tbody>
   </table>
   <p class="fine">Based on the public feature lists of theknot.com and zola.com wedding websites as of September 2026. If we've missed something they do, tell us and we'll fix this table.</p>
  </div>

  <div class="scta">
   <a href="https://app.meetlazo.com/?template=peony">Make yours &mdash; free, live in minutes</a>
   <p>Shown on Peony, our newest design. Pick any of the twenty-one above; every feature comes with it.</p>
  </div>
 </div>
</section>
<!-- /lz-sell -->
"""

# idempotent: strip earlier copies
s = re.sub(r"\n/\* ---- lz-sell:.*?/\* ---- /lz-sell ---- \*/\n", "\n", s, flags=re.S)
s = re.sub(r"<!-- lz-sell -->.*?<!-- /lz-sell -->\n?", "", s, flags=re.S)

k = s.find("</style>")
if k < 0:
    raise SystemExit("no <style>")
s = s[:k] + CSS + s[k:]

anchor = '<section class="beyond rv">'
if s.count(anchor) != 1:
    raise SystemExit(f"beyond anchor x{s.count(anchor)}")
s = s.replace(anchor, HTML + "\n" + anchor)

# the "Everything included" grid gains the new rows, once
rows = """  <div><b>Guests&rsquo; photos</b><span>Added from their phones on the day, approved by you, shown on the TV, downloaded as one zip.</span></div>
  <div><b>Hour by hour</b><span>Your timeline for guests, marking what&rsquo;s happening now on the day.</span></div>
  <div><b>Find your table</b><span>Name in, table, seat, tablemates and a room map out.</span></div>
  <div><b>Personal RSVP links</b><span>Pre-filled for each household, with dinner choices and the weekend&rsquo;s events.</span></div>
  <div><b>Forecast &amp; languages</b><span>The venue forecast inside two weeks; the whole site in twenty languages.</span></div>
"""
if "<b>Find your table</b>" not in s:
    key = '  <div><b>Married mode</b>'
    if s.count(key) != 1:
        raise SystemExit("included anchor")
    s = s.replace(key, rows + key)

# the hero sub-line and the band lead sell it too
s = s.replace('<h2>One wedding website, with everything your guests will ask about</h2>',
              '<h2>One wedding website, with everything your guests will ask about &mdash; and the day-of tools nobody else has</h2>', 1)

P.write_text(s, encoding="utf-8", newline="\n")
print(f"index.html: sell section in ({len(s):,} bytes)")
