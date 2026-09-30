"""patch_home_app0930.py - JC-LAZO-HOME-0930-APP
The home page sells the app to couples, not claiming to vendors.
  1. A new section right under the hero: three App Store screenshots (Apple's
     own, /assets/app-*.webp), why Lazo over Zola and The Knot, the official
     "Download on the App Store" badge (/assets/appstore-badge.svg), Android
     in review, and a web CTA.
  2. The "Verified, and answering" row never says "No <city> vendor has
     claimed yet": a metro with no claimed vendors hides the row. The vendor
     claim tile is gone from the couples' home (it lives on /for-vendors/).
Applies to generate/templates/home.html (tonight's build) and dist/index.html
(live now). Idempotent.
  python generate\\patch_home_app0930.py
Then: python deploy\\upload_r2.py --prefix index.html --prefix assets/app- --prefix assets/appstore-badge.svg
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAG = "lz-app-home"

SECTION = f"""<!-- {TAG} -->
<section class="apphome" id="app">
<style>
.apphome{{max-width:1180px;margin:0 auto;padding:72px 28px 24px}}
.apphome .ag{{display:grid;gap:36px;align-items:center;grid-template-columns:1fr}}
@media(min-width:920px){{.apphome .ag{{grid-template-columns:1.05fr .95fr}}}}
.apphome .shots{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;align-items:end}}
.apphome .shots img{{width:100%;height:auto;display:block;border-radius:22px;box-shadow:0 28px 50px -30px rgba(36,30,43,.55)}}
.apphome .shots img:nth-child(2){{transform:translateY(-22px)}}
.apphome .why{{list-style:none;padding:0;margin:22px 0 0;display:grid;gap:12px}}
.apphome .why li{{display:grid;grid-template-columns:auto 1fr;gap:12px;align-items:start;font-size:15.5px;line-height:1.5}}
.apphome .why b{{font-family:"Cormorant Garamond",serif;font-size:22px;line-height:1;color:var(--gold-ink,#8A6A2F)}}
.apphome .get{{display:flex;flex-wrap:wrap;align-items:center;gap:16px;margin-top:26px}}
.apphome .get img{{height:52px;width:auto;display:block}}
.apphome .get small{{font-size:12.5px;color:var(--muted)}}
.apphome .get .web{{font-weight:700;color:var(--plum,#52284F);text-decoration:none;border-bottom:2px solid var(--gold,#D9B77C);padding-bottom:2px;font-size:14.5px}}
.apphome .vs{{margin-top:8px;font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--gold-ink,#8A6A2F);font-weight:700}}
@media(max-width:919px){{.apphome .shots{{max-width:520px;margin:0 auto}}}}
</style>
  <div class="ag">
    <div class="shots" aria-label="The Lazo app">
      <img src="/assets/app-1.webp" alt="The Lazo app: your wedding at a glance, 287 days to go, your vendor team and budget" loading="lazy" decoding="async" width="600" height="1298">
      <img src="/assets/app-3.webp" alt="Ask June anything: the AI planner suggesting verified venues in your city" loading="lazy" decoding="async" width="600" height="1298">
      <img src="/assets/app-8.webp" alt="Design your seating chart in the Lazo app" loading="lazy" decoding="async" width="600" height="1298">
    </div>
    <div>
      <p class="eyebrow">The Lazo app, now on iPhone</p>
      <h2 class="band-title">The whole wedding, planned from your phone.</h2>
      <p class="band-sub">Vendors you can trust, a planner that knows what to do next, and a wedding website that works the room on the day. Free, no ads, no upsells.</p>
      <p class="vs">Why couples pick Lazo over Zola and The Knot</p>
      <ul class="why">
        <li><b>01</b><span>Every review is from a couple who actually booked. No vendor can pay to rank.</span></li>
        <li><b>02</b><span>June, your AI planner, reads your date, budget and city and tells you what to do this week.</span></li>
        <li><b>03</b><span>One thread per vendor: the contract, the invoice and the payment live inside the conversation.</span></li>
        <li><b>04</b><span>A wedding website that does the day itself: guests add photos from their phones, find their table, and see what's happening now.</span></li>
      </ul>
      <div class="get">
        <a href="https://apps.apple.com/us/app/lazo-wedding-planner/id6812863675" aria-label="Download Lazo on the App Store"><img src="/assets/appstore-badge.svg" alt="Download on the App Store" width="156" height="52"></a>
        <small>Android is in review with Google Play.</small>
        <a class="web" href="https://app.meetlazo.com">Or start on the web &rarr;</a>
      </div>
    </div>
  </div>
</section>
<!-- /{TAG} -->
"""


def patch(path, is_template):
    s = path.read_text(encoding="utf-8")
    s = re.sub(rf"<!-- {TAG} -->.*?<!-- /{TAG} -->\n", "", s, flags=re.S)
    anchor = "{% if featured %}\n<section class=\"band\">" if is_template else '<section class="band">\n  <div class="rowhead">'
    if s.count(anchor) != 1:
        raise SystemExit(f"{path.name}: anchor x{s.count(anchor)}")
    s = s.replace(anchor, SECTION + anchor, 1)
    # the vendor claim tile: gone from the couples' home
    if is_template:
        s = re.sub(r'    \{% if featured\|length < 4 %\}\n    <a class="vf claim" href="/for-vendors/">.*?</a>\n    \{% endif %\}\n', "", s, count=1, flags=re.S)
    else:
        s = re.sub(r'    <a class="vf claim" href="/for-vendors/">.*?</a>\n', "", s, count=1, flags=re.S)
    # the JS: no claim tile, and a metro with nothing claimed hides the row instead of announcing it
    claim_js = re.search(r"\n      if\(list\.length<4\)\{html\+='<a class=\"vf claim\".*?\}\n", s, flags=re.S)
    if claim_js:
        s = s.replace(claim_js.group(0), "\n", 1)
    old_sub = "      if(sub)sub.textContent=list.length?"
    if old_sub in s and "geo-featured-hide" not in s:
        s = s.replace(old_sub, "      /* geo-featured-hide */ var band=grid.closest('section'); if(band)band.style.display=list.length?'':'none';\n" + old_sub, 1)
    path.write_text(s, encoding="utf-8", newline="\n")
    print(f"  {path.relative_to(ROOT)}: app section in, claim tile out, empty rows hidden")


patch(ROOT / "generate" / "templates" / "home.html", True)
patch(ROOT / "dist" / "index.html", False)
