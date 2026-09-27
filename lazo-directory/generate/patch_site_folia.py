"""patch_site_folia.py - JC-LAZO-SITE-0920-FOLIA
  1. build.py renders /folia-alternative/ (pages/folia-alternative.html).
  2. home.html gets a Pricing + FAQ section above the vendor claim band -
     "Free for couples. Forever." with the tools listed, three answers, and
     Offer + FAQPage schema so the free price and the answers can show in
     search results.
  3. The Zola, Knot and WeddingWire comparison pages link to the Folia one.
Refuses to run twice.
  python generate\\patch_site_folia.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
b = ROOT / "generate" / "build.py"
s = b.read_text(encoding="utf-8")
if '"folia-alternative"' not in s:
    old = '"honeybook-alternative"]'
    assert s.count(old) == 1
    s = s.replace(old, '"honeybook-alternative", "folia-alternative"]')
    b.write_text(s, encoding="utf-8", newline="\n")
    print("build.py: folia-alternative in STATIC_PAGES")

h = ROOT / "generate" / "templates" / "home.html"
s = h.read_text(encoding="utf-8")
if "JC-LAZO-SITE-0920-FOLIA" not in s:
    old = '<section class="band band-claim" style="padding-top:0">\n  <div class="claim-strip claim-wide">\n    <h2>Own a wedding business?</h2>'
    assert s.count(old) == 1
    section = '''{#- JC-LAZO-SITE-0920-FOLIA: pricing (there is none) and the three questions, with schema -#}
<section class="band" id="pricing">
  <div style="max-width:860px;margin:0 auto;text-align:center">
    <p class="eyebrow">Pricing</p>
    <h2 class="band-title">Free for couples. Forever.</h2>
    <p class="band-sub">Every planning tool on Lazo is free, with no card, no ads, no guest cap and no paid tier: the guest list with RSVPs, the budget with real local ranges, reception and ceremony seating, the dream board, the day-of timeline, the shopping list, the marriage license guide and your wedding website. Vendors pay nothing to be listed and nothing to reply. Lazo earns when a couple books and pays a vendor through the thread, and only then.</p>
    <div class="promises" style="margin-top:26px;text-align:left">
      <div class="promise"><h3>$0 for couples</h3><p>Guest list, budget, seating, dream board, timeline, website, June. All of it, always.</p></div>
      <div class="promise"><h3>$0 for vendors to list</h3><p>Claim the profile, answer reviews, receive verified leads. No ad spend buys a better spot.</p></div>
      <div class="promise"><h3>A small fee on bookings</h3><p>When a couple pays a vendor through Lazo, Lazo keeps a small share of that payment. That is the whole business.</p></div>
    </div>
    <p style="margin-top:18px"><a class="btn-gold" href="https://app.meetlazo.com">Start planning free</a> &nbsp; <a href="/folia-alternative/" style="color:var(--plum);font-weight:600">Compare with paid planners &rarr;</a></p>
  </div>
</section>
<section class="band" id="faq" style="padding-top:0">
  <div style="max-width:860px;margin:0 auto">
    <h2 class="band-title" style="text-align:center">Questions couples ask</h2>
    <details class="faq"><summary>Is Lazo really free for couples?</summary><p>Yes. There is no paid tier for couples and nothing is capped. Lazo earns a small share when a couple pays a vendor through the thread, so the tools stay free and the rankings stay honest.</p></details>
    <details class="faq"><summary>How are vendors ranked?</summary><p>By the Lazo Score, built only from verified reviews from couples who proved the wedding happened, weighted for recency. No vendor can pay for a better position.</p></details>
    <details class="faq"><summary>What is June?</summary><p>Your AI planning copilot. She knows your date, budget, guest list and bookings, seats your guests from your parties and sides, drafts vendor messages, and tells you what to book next.</p></details>
    <details class="faq"><summary>Can I bring my guest list from The Knot, Zola or Folia?</summary><p>Yes. Export it as a CSV and import it in one step; June reads a pasted budget or vendor list. Registry links stay wherever they are.</p></details>
  </div>
</section>
'''
    s = s.replace(old, section + old)
    old2 = "{% block jsonld %}\n<script type=\"application/ld+json\">\n{\n  \"@context\": \"https://schema.org\",\n  \"@type\": \"Organization\","
    assert s.count(old2) == 1
    s = s.replace(old2, '''{% block jsonld %}
<script type="application/ld+json">
{"@context":"https://schema.org","@graph":[
 {"@type":"SoftwareApplication","name":"Lazo wedding planner","applicationCategory":"LifestyleApplication","operatingSystem":"Web, iOS, Android","url":"https://app.meetlazo.com","offers":{"@type":"Offer","price":"0","priceCurrency":"USD","description":"Free for couples: guest list, budget, seating charts, dream board, timeline, wedding website and June."}},
 {"@type":"FAQPage","mainEntity":[
  {"@type":"Question","name":"Is Lazo really free for couples?","acceptedAnswer":{"@type":"Answer","text":"Yes. There is no paid tier for couples and nothing is capped. Lazo earns a small share when a couple pays a vendor through the thread, so the tools stay free and the rankings stay honest."}},
  {"@type":"Question","name":"How are vendors ranked?","acceptedAnswer":{"@type":"Answer","text":"By the Lazo Score, built only from verified reviews from couples who proved the wedding happened, weighted for recency. No vendor can pay for a better position."}},
  {"@type":"Question","name":"What is June?","acceptedAnswer":{"@type":"Answer","text":"Your AI planning copilot. She knows your date, budget, guest list and bookings, seats your guests from your parties and sides, drafts vendor messages, and tells you what to book next."}},
  {"@type":"Question","name":"Can I bring my guest list from The Knot, Zola or Folia?","acceptedAnswer":{"@type":"Answer","text":"Yes. Export it as a CSV and import it in one step; June reads a pasted budget or vendor list. Registry links stay wherever they are."}}
 ]}
]}
</script>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Organization",''')
    h.write_text(s, encoding="utf-8", newline="\n")
    print("home.html: pricing + FAQ section and schema")

for name in ("zola-alternative", "the-knot-alternative", "weddingwire-alternative"):
    p = ROOT / "generate" / "templates" / "pages" / f"{name}.html"
    t = p.read_text(encoding="utf-8")
    if "folia-alternative" in t:
        continue
    old = '<a href="{{ base }}/why-lazo/">Why Lazo</a>'
    if t.count(old) == 1:
        t = t.replace(old, '<a href="{{ base }}/folia-alternative/">Folia alternative</a>\n' + old)
        p.write_text(t, encoding="utf-8", newline="\n")
        print(f"{name}: linked to Folia page")
