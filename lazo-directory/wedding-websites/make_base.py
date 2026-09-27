"""make_base.py - JC-LAZO-WWT-0915-003
Derives wedding-websites/_base.html (the tokenised template make_themes.py
fills) from the Tide template, so every new theme carries exactly Tide's
hydration, RSVP, guestbook, June and chapters code.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
s = (ROOT / "tide" / "index.html").read_text(encoding="utf-8")

# strip any feel/song layer so the base is clean (apply_feel adds it back)
s = re.sub(r"\n/\* ---- JC-LAZO-WWS-0915-FEEL: the feel ---- \*/.*?/\* ---- /JC-LAZO-WWS-0915-FEEL ---- \*/\n", "\n", s, flags=re.S)
s = re.sub(r"\n<script>\n/\* JC-LAZO-WWS-0915-(?:SONG|FEEL).*?</script>\n", "\n", s, flags=re.S)


def rep(old, new, count=None):
    global s
    n = s.count(old)
    if n == 0 or (count is not None and n != count):
        raise SystemExit(f"anchor {old[:60]!r}: found {n}, wanted {count}")
    s = s.replace(old, new)


rep("<!-- JC-LAZO-WWT-0907-002: sections visible without scrolling (previews, print, slow observers); registry anchor, note and store icons; add-to-calendar on the venue card; RSVP deadline line -->",
    "<!-- JC-LAZO-WWT-0915-003: themed template built from _base.html by make_themes.py; same hydration as Tide (JC-LAZO-WWT-0907-002) -->", 1)
rep("<title>Tide — a coastal wedding website template | Lazo</title>", "<title>@@TITLE@@</title>", 1)
rep('<meta name="description" content="A free tide wedding website template from Lazo — RSVPs, schedule, registry, and a site that says We\'re Married after the big day.">',
    '<meta name="description" content="@@DESC@@">', 1)
rep("family=Cormorant:ital,wght@0,500;0,600;1,500&family=Nunito+Sans:wght@300;400;600&display=swap", "@@FONTS@@", 1)
rep(":root{--bg:#F7FAFB;--ink:#1E3A4C;--mut:#6E8899;--acc:#2E7C8F;--panel:#FFFFFF;--line:#DCE8ED;--lz-plum:#52284F;--lz-gold:#D9B77C}",
    ":root{@@ROOTVARS@@;--lz-plum:#52284F;--lz-gold:#D9B77C}", 1)
# type: the h1 takes the display face, everything else the serif; sans everywhere else
rep('h1{font:600 clamp(52px,8.4vw,108px)/1.02 "Cormorant",serif;', 'h1{font:600 clamp(52px,8.4vw,108px)/1.02 @@DISPLAY@@;', 1)
rep('"Cormorant",serif', "@@SERIF@@")
rep('"Nunito Sans",sans-serif', "@@SANS@@")
rep('"Nunito Sans"', "@@SANS@@")
rep("input,textarea{font:inherit;font-size:15px;padding:13px 14px;background:#FFFFFF;", "input,textarea{font:inherit;font-size:15px;padding:13px 14px;background:var(--panel);", 1)
rep("https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1900&q=74", "@@HERO_IMG@@")
rep("filter:saturate(1.02) brightness(.96)", "filter:@@HERO_FILTER@@")
rep("</style>\n\n<script>\n(function(){\n var P=", "@@EXTRA_CSS@@\n</style>\n\n<script>\n(function(){\n var P=", 1)
s = re.sub(r"var P=\{.*?\};\n", "var P=@@PALETTES@@;\n", s, count=1, flags=re.S)
rep("Template · <b>&nbsp;Tide</b>", "Template · <b>&nbsp;@@NAME@@</b>", 1)
# hero
a = s.index('<header class="hero hero-band">')
b = s.index("</header>", a) + len("</header>")
s = s[:a] + "@@HERO@@" + s[b:]
# story
rep("<h2>Two towels, one sandbar, no plan.</h2>", "<h2>@@STORY_H@@</h2>", 1)
s = re.sub(r'<p class="lede">Nora was reading;.*?</p>', '<p class="lede">@@STORY_P@@</p>', s, count=1, flags=re.S)
rep('<figure class="pimg"><img loading="lazy" src="https://images.unsplash.com/photo-1519046904884-53103b34b206?auto=format&fit=crop&w=1000&q=74" alt="" onerror="this.closest(\'figure\').style.display=\'none\'"><figcaption>Nine summers in</figcaption></figure>',
    '<figure class="pimg"><img loading="lazy" src="@@STORY_IMG@@" alt="" onerror="this.closest(\'figure\').style.display=\'none\'"><figcaption>@@STORY_CAP@@</figcaption></figure>', 1)
# gallery
rep("<h2>Salt, light, and the two of us.</h2>", "<h2>@@GAL_H@@</h2>", 1)
a = s.index('<div class="gal">\n') + len('<div class="gal">\n')
b = s.index("  </div>\n </div>\n</section>", a)
s = s[:a] + "@@GAL@@\n" + s[b:]
# the day
rep('<h2 style="margin:0 auto">Ceremony on the bluff, dinner by the water, shoes optional throughout.</h2>', '<h2 style="margin:0 auto">@@DAY_H@@</h2>', 1)
a = s.index('<ul class="sched">\n') + len('<ul class="sched">\n')
b = s.index("   </ul>", a)
s = s[:a] + "@@SCHED@@\n" + s[b:]
a = s.index('<div class="venlist">\n') + len('<div class="venlist">\n')
b = s.index("   </div>\n  </div>\n </div>\n</section>", a)
s = s[:a] + "@@VENS@@\n" + s[b:]
# thanks
rep('<p class="lede">The tide turned right on time. Thank you for coming ashore for us.</p>', '<p class="lede">@@THANKS@@</p>', 1)
# rsvp
rep("<h2>Tell us you&#x27;re coming ashore.</h2>", "<h2>@@RSVP_H@@</h2>", 1)
rep('<p class="lede">Kindly reply by August 1 — the oyster count waits for no one.</p>', '<p class="lede">@@RSVP_P@@</p>', 1)
rep("<span>Coming ashore</span>", "<span>@@YES@@</span>", 1)
rep("<span>Waving from the mainland</span>", "<span>@@NO@@</span>", 1)
rep('placeholder="A song that gets everyone dancing (optional)"', 'placeholder="@@SONG_PH@@"', 1)
rep('placeholder="Dietary notes, song requests, boat questions…"', 'placeholder="@@NOTE_PH@@"', 1)
# registry
rep('<h2 style="margin:0 auto">Your presence is the whole point.</h2>', '<h2 style="margin:0 auto">@@REG_H@@</h2>', 1)
s = re.sub(r'<p class="lede">If you&#x27;d like to give more.*?</p>', '<p class="lede">@@REG_P@@</p>', s, count=1, flags=re.S)
# faq
a = s.index('<div class="faq">\n') + len('<div class="faq">\n')
b = s.index("  </div>\n </div>\n</section>", a)
s = s[:a] + "@@FAQ@@\n" + s[b:]
# scripts
rep('https://app.meetlazo.com/?template=tide', 'https://app.meetlazo.com/?template=@@SLUG@@', 1)
rep('let when=new Date("2027-09-04T17:00:00");', 'let when=new Date("@@DATE@@T17:00:00");', 1)
rep("\n</body>", "\n@@BODY_EXTRA@@\n</body>", 1)

for leak in ("Nora", "Beck", "Cape Cod", "oyster", "sandbar", "Windward", "bluff", "boathouse"):
    if leak in s:
        i = s.index(leak)
        raise SystemExit(f"demo copy leaked into base: {leak!r} near {s[max(0,i-60):i+40]!r}")
(ROOT / "_base.html").write_text(s, encoding="utf-8", newline="\n")
print(f"_base.html written ({len(s):,} bytes)")
