"""make_themes.py - JC-LAZO-WWT-0915-003
Builds the themed wedding-website templates from one base and a spec each:
Shore (ocean), Summit (mountains), Ranch (western), Starlit (night sky),
Frost (winter). Same bones as Tide - the data hooks, hydration, RSVP,
guestbook, June and chapters are the same code - with their own type,
palettes, hero, illustration and demo copy. Re-runnable.

  python wedding-websites\\make_themes.py            # all five
  python wedding-websites\\make_themes.py shore      # one
Then: python wedding-websites\\apply_feel.py  (feel + the couple's song)
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = (ROOT / "_base.html").read_text(encoding="utf-8")

U = "https://images.unsplash.com/photo-"
def img(id_, w=1200, q=74):
    return f"{U}{id_}?auto=format&fit=crop&w={w}&q={q}"

THEMES = {
 "shore": dict(
  name="Shore", title="Shore — an ocean wedding website template | Lazo",
  desc="A free ocean wedding website template from Lazo — waves, sand and shells, with RSVPs, schedule, registry, and a site that says We're Married after the big day.",
  fonts="family=Italiana&family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500&family=Jost:wght@300;400;500&display=swap",
  serif='"Cormorant Garamond",serif', display='"Italiana","Cormorant Garamond",serif', sans='"Jost",sans-serif',
  palettes={"lagoon":{"--bg":"#F7FBFA","--ink":"#17384A","--mut":"#5F7E8C","--acc":"#1B7F8C","--panel":"#FFFFFF","--line":"#D7E7EA","--sand":"#F2E8D5"},
            "sunset":{"--bg":"#FBF5F0","--ink":"#3A2A24","--mut":"#8C7468","--acc":"#E0745A","--panel":"#FFFFFF","--line":"#F0DDD3","--sand":"#F6E7D2"},
            "driftwood":{"--bg":"#F8F5EF","--ink":"#33302A","--mut":"#7E7568","--acc":"#8C7355","--panel":"#FFFFFF","--line":"#E7DFD1","--sand":"#EFE4D0"},
            "deep":{"--bg":"#F3F7F9","--ink":"#132A3A","--mut":"#5C7385","--acc":"#1E4C6E","--panel":"#FFFFFF","--line":"#D5E1E9","--sand":"#EFE6D3"}},
  hero="full", hero_img=img("1519046904884-53103b34b206", 1900), hero_filter="saturate(1.04) brightness(.96)",
  eyebrow="Where the water meets the sand", cdlabel="days until high tide", n1="Marina", n2="Cole",
  where="Pelican Point · Laguna Beach, California", date="2027-06-12",
  story_h="A boardwalk, two coffees, and a very long walk.", story_p="We met on the pier the morning after a storm - the water was wild and neither of us wanted to go home. Six summers later we are getting married on the sand at Pelican Point, shoes in hand, with the people who make our world.",
  story_img=img("1471922694854-ff1b63b20054", 1000), story_cap="Six summers in",
  gal_h="Salt air, sea light, the two of us.", gal=[(img("1473116763249-2faaef81ccda"), "The point at low tide"), (img("1505142468610-359e7d316be0", 900), "Where he asked"), (img("1507525428034-b723cf961d3e", 900), "Evenings like this one")],
  day_h="Vows on the sand, dinner on the deck, dancing until the tide comes in.",
  sched=[("4:00 pm","Guests arrive - cold drinks and colder oysters"),("4:30 pm","Ceremony on the sand"),("5:15 pm","Cocktails as the boats come in"),("6:30 pm","Dinner on the deck"),("8:30 pm","Bonfire, s'mores and dancing")],
  ven=[("Ceremony","The Beach","4:30 in the afternoon","Bare feet welcome - the sand is soft"),("Reception","The Boathouse Deck","5:15 until the last wave","Dinner, toasts and a bonfire")],
  thanks="The tide came in right on time. Thank you for coming down to the water with us.",
  rsvp_h="Tell us you're coming to the shore.", rsvp_p="Kindly reply by May 1 - the oyster count waits for no one.", yes="Coming to the shore", no="Waving from dry land",
  song_ph="A song that gets everyone on the sand (optional)", note_ph="Dietary notes, song requests, questions about the tide...",
  reg_h="Your presence is the whole point.", reg_p="If you would like to give more, we have gathered a few things for the cottage - and a fund for the sailboat we keep talking about.",
  faq=[("What should I wear?","Beach cocktail - linen, sundresses, sandals you can slip off. Bring a layer for the bonfire."),("Is it really on the sand?","The ceremony is; the deck has a floor. Heels sink, so choose accordingly."),("Where should we stay?","Rooms are held at the Pelican Inn through May 1 under Marina and Cole.")],
  extra_css="""
.shore-waves{position:absolute;left:0;right:0;bottom:-2px;height:120px;z-index:0;pointer-events:none;overflow:hidden}
.shore-waves svg{position:absolute;left:0;bottom:0;width:200%;height:100%}
.shore-waves .w1{animation:shw 18s linear infinite;opacity:.55}.shore-waves .w2{animation:shw 26s linear infinite reverse;opacity:.7;bottom:-8px}.shore-waves .w3{animation:shw 34s linear infinite;bottom:-18px}
@keyframes shw{from{transform:translateX(0)}to{transform:translateX(-50%)}}
.hero-full{padding-bottom:110px}
.k::before{content:"";display:inline-block;width:14px;height:14px;margin:0 8px -2px 0;background:currentColor;-webkit-mask:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M12 3c5 0 9 4.2 9 9.4 0 3.7-2.3 6.5-4.6 8.3-.8.6-1.9 0-1.9-1v-6.2c0-.6-.4-1-1-1h-3c-.6 0-1 .4-1 1v6.2c0 1-1.1 1.6-1.9 1C5.3 18.9 3 16.1 3 12.4 3 7.2 7 3 12 3zm0 2c-3.9 0-7 3.3-7 7.4 0 2.4 1.2 4.3 2.7 5.7V13.5c0-1.7 1.3-3 3-3h2.6c1.7 0 3 1.3 3 3v4.6c1.5-1.4 2.7-3.3 2.7-5.7C19 8.3 15.9 5 12 5z'/%3E%3C/svg%3E") center/contain no-repeat;mask:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M12 3c5 0 9 4.2 9 9.4 0 3.7-2.3 6.5-4.6 8.3-.8.6-1.9 0-1.9-1v-6.2c0-.6-.4-1-1-1h-3c-.6 0-1 .4-1 1v6.2c0 1-1.1 1.6-1.9 1C5.3 18.9 3 16.1 3 12.4 3 7.2 7 3 12 3zm0 2c-3.9 0-7 3.3-7 7.4 0 2.4 1.2 4.3 2.7 5.7V13.5c0-1.7 1.3-3 3-3h2.6c1.7 0 3 1.3 3 3v4.6c1.5-1.4 2.7-3.3 2.7-5.7C19 8.3 15.9 5 12 5z'/%3E%3C/svg%3E") center/contain no-repeat}
section:nth-of-type(odd){background:linear-gradient(180deg,var(--bg),color-mix(in srgb,var(--sand) 40%,var(--bg)))}
@media(prefers-reduced-motion:reduce){.shore-waves svg{animation:none}}
""",
  hero_art="""<div class="shore-waves" aria-hidden="true">
 <svg class="w1" viewBox="0 0 2880 120" preserveAspectRatio="none"><path fill="var(--bg)" d="M0 70c120-30 240-30 360 0s240 30 360 0 240-30 360 0 240 30 360 0 240-30 360 0 240 30 360 0 240-30 360 0 240 30 360 0v50H0z" opacity=".5"/></svg>
 <svg class="w2" viewBox="0 0 2880 120" preserveAspectRatio="none"><path fill="var(--bg)" d="M0 80c160-40 320-40 480 0s320 40 480 0 320-40 480 0 320 40 480 0 320-40 480 0 320 40 480 0v40H0z" opacity=".75"/></svg>
 <svg class="w3" viewBox="0 0 2880 120" preserveAspectRatio="none"><path fill="var(--bg)" d="M0 95c200-30 400-30 600 0s400 30 600 0 400-30 600 0 400 30 600 0 400-30 480 0v25H0z"/></svg>
</div>""",
  body_extra="",
 ),
 "summit": dict(
  name="Summit", title="Summit — a mountain wedding website template | Lazo",
  desc="A free mountain wedding website template from Lazo — peaks, pines and alpine light, with RSVPs, schedule, registry, and a site that says We're Married after the big day.",
  fonts="family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Work+Sans:wght@300;400;500&display=swap",
  serif='"Fraunces",serif', display='"Fraunces",serif', sans='"Work Sans",sans-serif',
  palettes={"alpine":{"--bg":"#F5F7F4","--ink":"#1F2E2A","--mut":"#68786F","--acc":"#2F5D50","--panel":"#FFFFFF","--line":"#DCE4DF"},
            "granite":{"--bg":"#F4F5F6","--ink":"#23292F","--mut":"#737B84","--acc":"#4A5560","--panel":"#FFFFFF","--line":"#DEE2E6"},
            "aspen":{"--bg":"#FAF6EE","--ink":"#332A1B","--mut":"#86775E","--acc":"#B8862B","--panel":"#FFFFFF","--line":"#EADFCB"},
            "glacier":{"--bg":"#F3F8FA","--ink":"#1B2F3A","--mut":"#607886","--acc":"#3E7E9E","--panel":"#FFFFFF","--line":"#D6E4EA"}},
  hero="band", hero_img=img("1506905925346-21bda4d32df4", 1900), hero_filter="saturate(1.02) brightness(.97)",
  eyebrow="Above the tree line", cdlabel="days until the summit", n1="Wren", n2="Tobias",
  where="Timberline Lodge · Mount Hood, Oregon", date="2027-08-21",
  story_h="Two trail maps, one wrong turn, no regrets.", story_p="We met on a switchback in the rain, arguing about which way was down. Neither of us was right, and we have been getting lost together ever since. This August we are getting married above the tree line, where the air is thin and the view goes on forever.",
  story_img=img("1464822759023-fed622ff2c3b", 1000), story_cap="Five summers on the trail",
  gal_h="Thin air, long light, the two of us.", gal=[(img("1469474968028-56623f02e42e"), "The lake where he asked"), (img("1497436072909-60f360e1d4b1", 900), "Basecamp, most weekends"), (img("1500534314209-a25ddb2bd429", 900), "Golden hour on the ridge")],
  day_h="Vows on the ridge, dinner in the lodge, stars from the deck.",
  sched=[("3:30 pm","Guests arrive - the shuttle runs from the village"),("4:00 pm","Ceremony on the ridge"),("4:45 pm","Cocktails on the deck"),("6:00 pm","Dinner by the great fireplace"),("8:30 pm","Dancing, then stars from the deck")],
  ven=[("Ceremony","The Ridge","4:00 in the afternoon","A short walk from the lodge - wear something you can stand in on gravel"),("Reception","Timberline Lodge","4:45 until late","Dinner, toasts and a fireplace the size of a car")],
  thanks="The clouds parted right on time. Thank you for climbing up here with us.",
  rsvp_h="Tell us you're coming up the mountain.", rsvp_p="Kindly reply by July 15 - the lodge needs a headcount for the shuttle.", yes="Coming up the mountain", no="Staying in the valley",
  song_ph="A song for the deck (optional)", note_ph="Dietary notes, song requests, questions about the altitude...",
  reg_h="Your presence is the whole point.", reg_p="If you would like to give more, we have gathered a few things for the cabin - and a fund for the trip to Patagonia we keep planning.",
  faq=[("What should I wear?","Mountain formal - suits and dresses with a warm layer. Evenings at altitude run cold, and the deck is worth it."),("How do we get up there?","A shuttle runs from the village every half hour from 2:30. Parking at the lodge is limited."),("Where should we stay?","Rooms are held at the lodge through July 15 under Wren and Tobias.")],
  extra_css="""
.summit-peaks{position:absolute;left:0;right:0;bottom:-1px;height:34%;min-height:120px;pointer-events:none;overflow:hidden}
.summit-peaks svg{position:absolute;left:0;bottom:0;width:100%;height:100%;will-change:transform}
.hero-band .hph{position:relative}
.k::before{content:"";display:inline-block;width:13px;height:13px;margin:0 8px -1px 0;background:currentColor;-webkit-mask:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M12 2l4 6h-2.5l3.5 5h-2.5l4 6H5.5l4-6H7l3.5-5H8z'/%3E%3C/svg%3E") center/contain no-repeat;mask:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M12 2l4 6h-2.5l3.5 5h-2.5l4 6H5.5l4-6H7l3.5-5H8z'/%3E%3C/svg%3E") center/contain no-repeat}
""",
  hero_art="""<div class="summit-peaks" aria-hidden="true">
 <svg class="p1" viewBox="0 0 1440 220" preserveAspectRatio="none"><path fill="var(--acc)" opacity=".22" d="M0 220 L0 168 L140 128 L250 150 L400 104 L540 146 L700 92 L840 138 L980 112 L1120 154 L1260 126 L1440 160 L1440 220Z"/></svg>
 <svg class="p2" viewBox="0 0 1440 220" preserveAspectRatio="none"><path fill="var(--bg)" opacity=".72" d="M0 220 L0 186 L120 158 L240 176 L380 140 L520 172 L660 148 L800 180 L960 152 L1100 178 L1250 160 L1440 190 L1440 220Z"/></svg>
 <svg class="p3" viewBox="0 0 1440 220" preserveAspectRatio="none"><path fill="var(--bg)" d="M0 220 L0 200 L200 170 L380 200 L560 165 L760 205 L940 175 L1140 205 L1300 185 L1440 210 L1440 220Z"/></svg>
</div>""",
  body_extra="""
<script>
(function(){if(matchMedia("(prefers-reduced-motion: reduce)").matches)return;var l=document.querySelectorAll(".summit-peaks svg");if(!l.length)return;var t=false;
function f(){t=false;var y=window.scrollY||0;l[0].style.transform="translateY("+(y*.10)+"px)";if(l[1])l[1].style.transform="translateY("+(y*.05)+"px)";}
addEventListener("scroll",function(){if(!t){t=true;requestAnimationFrame(f);}},{passive:true});})();
</script>""",
 ),
 "ranch": dict(
  name="Ranch", title="Ranch — a western wedding website template | Lazo",
  desc="A free western wedding website template from Lazo — boots, barns and big sky, with RSVPs, schedule, registry, and a site that says We're Married after the big day.",
  fonts="family=Rye&family=Zilla+Slab:ital,wght@0,500;0,600;1,500&family=Karla:wght@300;400;500&display=swap",
  serif='"Zilla Slab",serif', display='"Zilla Slab",serif', sans='"Karla",sans-serif',
  palettes={"saddle":{"--bg":"#F9F4EC","--ink":"#2F231A","--mut":"#84705E","--acc":"#8B4A2B","--panel":"#FFFDF8","--line":"#E6D9C6"},
            "denim":{"--bg":"#F4F6F8","--ink":"#1F2A36","--mut":"#68737F","--acc":"#3B5B7C","--panel":"#FFFFFF","--line":"#D9E0E7"},
            "prairie":{"--bg":"#FAF6EC","--ink":"#332B1C","--mut":"#8A7B5E","--acc":"#9A7B3C","--panel":"#FFFDF7","--line":"#EADFC8"},
            "dusk":{"--bg":"#F9F1EC","--ink":"#35241E","--mut":"#8B7167","--acc":"#C25B3A","--panel":"#FFFCF9","--line":"#EFDAD1"}},
  hero="split", hero_img=img("1500382017468-9049fed747ef", 1900), hero_filter="sepia(.12) saturate(1.1) brightness(.95)",
  eyebrow="Y'all are invited", cdlabel="days until we tie the knot", n1="June", n2="Wyatt",
  where="Silver Creek Ranch · Bandera, Texas", date="2027-10-09",
  story_h="A two-step, a flat tire, and the rest is history.", story_p="We met at a dance hall in Gruene and left in the same truck - which then broke down outside Bandera. We have been fixing things together ever since. This October we are getting married under the oaks at Silver Creek, with barbecue, a band and the biggest sky in Texas.",
  story_img=img("1470071459604-3b5ec3a7fe05", 1000), story_cap="Four years, three trucks",
  gal_h="Big sky, red dirt, the two of us.", gal=[(img("1504280390367-361c6d9f38f4"), "Sunset at the creek"), (img("1441974231531-c6227db76b6e", 900), "The road in"), (img("1513836279014-a89f7a76ae86", 900), "Where he asked")],
  day_h="Vows under the oaks, brisket in the barn, boots on the dance floor.",
  sched=[("4:00 pm","Guests arrive - sweet tea and something stronger"),("4:30 pm","Ceremony under the live oaks"),("5:15 pm","Cocktails by the creek"),("6:30 pm","Barbecue in the barn"),("8:30 pm","Live band, two-stepping, fireworks at ten")],
  ven=[("Ceremony","The Live Oaks","4:30 in the afternoon","Hay-bale seating - dust off your boots"),("Reception","The Barn","5:15 until the band quits","Brisket, toasts and a proper dance floor")],
  thanks="The band played late and nobody's boots survived. Thank you for riding out here for us.",
  rsvp_h="Tell us you're saddling up.", rsvp_p="Kindly reply by September 1 - the pitmaster needs a count.", yes="Saddling up", no="Can't make the ride",
  song_ph="A song that fills the dance floor (optional)", note_ph="Dietary notes, song requests, questions about the drive...",
  reg_h="Your presence is the whole point.", reg_p="If you would like to give more, we have gathered a few things for the homestead - and a fund for the horse we keep pretending we won't buy.",
  faq=[("What should I wear?","Ranch formal - boots encouraged, hats welcome, denim fine after the ceremony. The barn floor is kind to two-steppers."),("How do we get there?","Silver Creek is forty minutes from San Antonio. The last mile is gravel; any car makes it. Parking is in the front pasture."),("Where should we stay?","Rooms are held at the Bandera Inn through September 1 under June and Wyatt.")],
  extra_css="""
.eyebrow{font-family:"Rye","Zilla Slab",serif;letter-spacing:.14em;font-size:13px}
.hero-split .frame{border:2px solid var(--acc);outline:1px dashed var(--acc);outline-offset:6px;position:relative}
.hero-split .frame::before,.hero-split .frame::after{content:"\\2605";position:absolute;top:-13px;font-size:16px;color:var(--acc);background:var(--bg);padding:0 6px}
.hero-split .frame::before{left:22px}.hero-split .frame::after{right:22px}
.hero-split .mono{border-width:2px;border-style:double;width:82px;height:82px}
.hero-split .hph{filter:sepia(.12) saturate(1.1) brightness(.95)}
.k::before{content:"";display:inline-block;width:13px;height:13px;margin:0 8px -1px 0;background:currentColor;-webkit-mask:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M12 2l2.9 6.6 7.1.6-5.4 4.7 1.6 7.1L12 17.3 5.8 21l1.6-7.1L2 9.2l7.1-.6z'/%3E%3C/svg%3E") center/contain no-repeat;mask:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M12 2l2.9 6.6 7.1.6-5.4 4.7 1.6 7.1L12 17.3 5.8 21l1.6-7.1L2 9.2l7.1-.6z'/%3E%3C/svg%3E") center/contain no-repeat}
.sched b{font-family:"Zilla Slab",serif;font-size:15px}
button.go,.gbf button{letter-spacing:.2em;font-family:"Zilla Slab",serif;font-size:14px}
""",
  hero_art="", body_extra="",
 ),
 "starlit": dict(
  name="Starlit", title="Starlit — a night-sky wedding website template | Lazo",
  desc="A free celestial wedding website template from Lazo — a sky full of stars, with RSVPs, schedule, registry, and a site that says We're Married after the big day.",
  fonts="family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500;1,600&family=Jost:wght@300;400;500&display=swap",
  serif='"Cormorant Garamond",serif', display='"Cormorant Garamond",serif', sans='"Jost",sans-serif',
  palettes={"midnight":{"--bg":"#0F1526","--ink":"#F1EEF7","--mut":"#A9A6BD","--acc":"#D9B77C","--panel":"#171E33","--line":"#2A3350"},
            "nebula":{"--bg":"#120F22","--ink":"#F3EEF9","--mut":"#B3A6C6","--acc":"#C98BD3","--panel":"#1B172E","--line":"#332B4D"},
            "aurora":{"--bg":"#0B1A1F","--ink":"#EAF4F1","--mut":"#9DB7B0","--acc":"#7FD3B3","--panel":"#12252B","--line":"#22403F"},
            "ember":{"--bg":"#1A1220","--ink":"#F7EFEA","--mut":"#BFA9A3","--acc":"#F0A26B","--panel":"#241A2B","--line":"#3D2E44"}},
  hero="full", hero_img=img("1444703686981-a3abbc4d4fe3", 1900), hero_filter="saturate(1.05) brightness(.9)",
  eyebrow="Under a sky full of stars", cdlabel="nights until we say I do", n1="Celeste", n2="Adrian",
  where="Cielo Vineyard · Paso Robles, California", date="2027-09-18",
  story_h="A meteor shower, a blanket, and a very late night.", story_p="We met on a hillside at two in the morning, waiting for the Perseids with a hundred strangers. We were the last two still looking up. This September we are getting married under that same sky, with lanterns in the vines and a band until the stars fade.",
  story_img=img("1419242902214-272b3f66ee7a", 1000), story_cap="Every August since",
  gal_h="Lanterns, long nights, the two of us.", gal=[(img("1464802686167-b939a6910659"), "The sky that started it"), (img("1519681393784-d120267933ba", 900), "Where he asked"), (img("1502134249126-9f3755a50d78", 900), "Nights like this one")],
  day_h="Vows at sunset, dinner by lantern light, dancing under the Milky Way.",
  sched=[("6:00 pm","Guests arrive - sparkling wine as the sun goes"),("6:30 pm","Ceremony at sunset"),("7:15 pm","Cocktails in the vines"),("8:30 pm","Dinner by lantern light"),("10:00 pm","Dancing, then the telescopes come out")],
  ven=[("Ceremony","The Hilltop","6:30, as the sun sets","A short walk up from the barn - the view is the point"),("Reception","The Lantern Barn","7:15 until the stars fade","Dinner, toasts and a very late night")],
  thanks="The sky did exactly what we hoped. Thank you for staying up with us.",
  rsvp_h="Tell us you'll be there when the stars come out.", rsvp_p="Kindly reply by August 15 - we are counting lanterns.", yes="Counting the stars with you", no="Wishing on one from afar",
  song_ph="A song for the dance floor (optional)", note_ph="Dietary notes, song requests, questions about the night...",
  reg_h="Your presence is the whole point.", reg_p="If you would like to give more, we have gathered a few things for the house - and a fund for the trip to see the northern lights.",
  faq=[("What should I wear?","Evening attire - deep colours, a little shimmer if you like. The hillside runs cool after dark, so bring a wrap."),("How late does it go?","Late. The last shuttle leaves at half past midnight, and the telescopes stay out until then."),("Where should we stay?","Rooms are held at the Cielo Inn through August 15 under Celeste and Adrian.")],
  extra_css="""
input,textarea{background:var(--panel)}
.hero-full::after{background:linear-gradient(to bottom,rgba(0,0,0,.2),rgba(0,0,0,.05) 40%,var(--bg) 98%)}
.stars{position:absolute;inset:0;z-index:-1;pointer-events:none}
.hero-band .hph::after{background:linear-gradient(to bottom,rgba(0,0,0,.06),transparent 30%,var(--bg) 99%)}
.k::before{content:"\\2726";margin-right:8px;font-size:12px}
.u,.cdline{color:var(--acc)}
button.go{background:var(--acc);color:var(--bg)}button.go:hover{background:var(--ink);color:var(--bg)}
.reg a.r{border-color:var(--acc);color:var(--acc)}
.demo-bar{background:#07090F}
""",
  hero_art="""<canvas class="stars" aria-hidden="true"></canvas>""",
  body_extra="""
<script>
(function(){var c=document.querySelector("canvas.stars");if(!c)return;var reduce=matchMedia("(prefers-reduced-motion: reduce)").matches;var x=c.getContext("2d"),W,H,st=[];
function size(){var h=c.parentNode;W=c.width=h.clientWidth;H=c.height=h.clientHeight;st=[];for(var i=0;i<Math.min(220,W*H/6000);i++)st.push({x:Math.random()*W,y:Math.random()*H*.8,r:Math.random()*1.3+.3,p:Math.random()*6.28,s:.4+Math.random()*1.2});}
function draw(t){x.clearRect(0,0,W,H);for(var i=0;i<st.length;i++){var s=st[i],a=reduce?.8:.45+.45*Math.sin(t/1000*s.s+s.p);x.globalAlpha=a;x.fillStyle="#FFF6E0";x.beginPath();x.arc(s.x,s.y,s.r,0,6.28);x.fill();}x.globalAlpha=1;if(!reduce)requestAnimationFrame(draw);}
size();addEventListener("resize",size);requestAnimationFrame(draw);})();
</script>""",
 ),
 "frost": dict(
  name="Frost", title="Frost — a winter wedding website template | Lazo",
  desc="A free winter wedding website template from Lazo — snow, evergreens and candlelight, with RSVPs, schedule, registry, and a site that says We're Married after the big day.",
  fonts="family=Cinzel:wght@500;600&family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Lato:wght@300;400;700&display=swap",
  serif='"Libre Baskerville",serif', display='"Libre Baskerville",serif', sans='"Lato",sans-serif',
  palettes={"ice":{"--bg":"#F6F9FB","--ink":"#1D2B36","--mut":"#6C7F8D","--acc":"#3F7C9B","--panel":"#FFFFFF","--line":"#DAE5EC"},
            "evergreen":{"--bg":"#F5F8F5","--ink":"#1E2E27","--mut":"#69796F","--acc":"#2F5B48","--panel":"#FFFFFF","--line":"#DBE5DF"},
            "berry":{"--bg":"#FBF5F6","--ink":"#33232A","--mut":"#86727A","--acc":"#9B3548","--panel":"#FFFFFF","--line":"#EDDCE0"},
            "silver":{"--bg":"#F6F7F8","--ink":"#23292F","--mut":"#747C86","--acc":"#6B7482","--panel":"#FFFFFF","--line":"#DEE2E7"}},
  hero="band", hero_img=img("1491002052546-bf38f186af56", 1900), hero_filter="saturate(.96) brightness(1.02)",
  eyebrow="A winter wedding", cdlabel="days until the snow", n1="Ingrid", n2="Elias",
  where="The Glass House · Stowe, Vermont", date="2027-12-18",
  story_h="A snowed-in cabin, one deck of cards, and no signal.", story_p="We met when a blizzard shut the mountain road and two strangers ended up in the same cabin with a woodstove and a deck of cards. Three winters later we are getting married in Stowe, in a glass house in the snow, with candles on every table and hot cider at the door.",
  story_img=img("1418985991508-e47386d96a71", 1000), story_cap="Three winters in",
  gal_h="Snow light, candlelight, the two of us.", gal=[(img("1478827387698-1527781a4887"), "The mountain, that first morning"), (img("1483921020237-2ff51e8e4b22", 900), "Where he asked"), (img("1517299321609-52687d1bc55a", 900), "Evenings like this one")],
  day_h="Vows in the glass house, dinner by the fire, snow on everything.",
  sched=[("3:30 pm","Guests arrive - hot cider and a warm fire"),("4:00 pm","Ceremony in the glass house"),("4:45 pm","Cocktails by the fire pits"),("6:00 pm","Dinner by candlelight"),("8:30 pm","Dancing, then sledding for the brave")],
  ven=[("Ceremony","The Glass House","4:00 in the afternoon","Warm inside, snow outside, blankets on every chair"),("Reception","The Lodge","4:45 until the fire burns down","Dinner, toasts and a very long dance")],
  thanks="It snowed, right on cue. Thank you for braving the roads for us.",
  rsvp_h="Tell us you're coming in from the cold.", rsvp_p="Kindly reply by November 20 - the kitchen needs a count before the first snow.", yes="Coming in from the cold", no="Warm wishes from afar",
  song_ph="A song for the dance floor (optional)", note_ph="Dietary notes, song requests, questions about the roads...",
  reg_h="Your presence is the whole point.", reg_p="If you would like to give more, we have gathered a few things for the house - and a fund for the ski trip we keep postponing.",
  faq=[("What should I wear?","Winter formal - velvet, wool, deep colours. Boots for the walk in; dancing shoes in a bag."),("What about the roads?","The lodge plows every hour. A shuttle runs from the village from 2:30, and we recommend it if it is snowing."),("Where should we stay?","Rooms are held at the Stowe Inn through November 20 under Ingrid and Elias.")],
  extra_css="""
.eyebrow{font-family:"Cinzel",serif;letter-spacing:.34em}
.snow{position:absolute;inset:0;pointer-events:none;overflow:hidden;z-index:1}
.snow i{position:absolute;top:-10px;width:6px;height:6px;border-radius:50%;background:#fff;opacity:.85;filter:blur(.3px);animation:snowfall linear infinite}
@keyframes snowfall{to{transform:translate3d(var(--dx,0),110vh,0)}}
.hero-band .hph{position:relative}
.k::before{content:"\\2744";margin-right:8px;font-size:12px}
.ven,.chap,.vt,.gbn,form{box-shadow:0 1px 0 rgba(255,255,255,.8) inset}
@media(prefers-reduced-motion:reduce){.snow{display:none}}
""",
  hero_art="""<div class="snow" aria-hidden="true"></div>""",
  body_extra="""
<script>
(function(){var s=document.querySelector(".snow");if(!s||matchMedia("(prefers-reduced-motion: reduce)").matches)return;var n=window.innerWidth<640?28:56,h="";
for(var i=0;i<n;i++){var sz=(2+Math.random()*5).toFixed(1);h+='<i style="left:'+(Math.random()*100).toFixed(2)+'%;width:'+sz+'px;height:'+sz+'px;opacity:'+(.35+Math.random()*.55).toFixed(2)+';--dx:'+((Math.random()*80-40).toFixed(0))+'px;animation-duration:'+(9+Math.random()*12).toFixed(1)+'s;animation-delay:-'+(Math.random()*20).toFixed(1)+'s"></i>';}
s.innerHTML=h;})();
</script>""",
 ),
}

# JC-LAZO-WWT-0919-004: seven more themes live in themes_extra.py
import sys as _sys; _sys.path.insert(0, str(ROOT))
from themes_extra import EXTRA as _EXTRA
THEMES.update(_EXTRA)
# JC-LAZO-WWT-0921-001: the original thirteen, rebuilt premium, override their
# hand-built specs (see themes_v2.py).
from themes_v2 import V2 as _V2
THEMES.update(_V2)


# Shared by every theme: on a full-bleed photo hero the type sits on the dark
# gradient, so it is white there whatever the palette's ink is.
COMMON_CSS = """
.hero-full .wrap{color:#fff;text-shadow:0 1px 18px rgba(0,0,0,.35)}
.hero-full h1,.hero-full .eyebrow,.hero-full .cdline,.hero-full .cdline b{color:#fff}
.hero-full h1 .amp{color:#fff;opacity:.85}
.hero-full .where{color:rgba(255,255,255,.86)}
.hero-full .cdline{border-color:rgba(255,255,255,.55)}
"""


def hero_html(t):
    n1, n2 = t["n1"], t["n2"]
    where = t["where"]
    common = (f'<p class="eyebrow" data-eyebrow>{t["eyebrow"]}</p>\n'
              f'   <h1><span data-n1>{n1}</span><span class="amp">&amp;</span><span data-n2>{n2}</span></h1>\n'
              f'   <p class="where"><span data-wprefix></span><span data-date-long></span> · {where}</p>\n'
              f'   <p class="cdline"><b data-cd="d">—</b> <span data-cdlabel>{t["cdlabel"]}</span></p>')
    art = t.get("hero_art", "")
    if t["hero"] == "full":
        return (f'<header class="hero hero-full">\n <div class="hph" aria-hidden="true"></div>\n {art}\n'
                f' <div class="wrap">\n   {common}\n </div>\n</header>')
    if t["hero"] == "band":
        return (f'<header class="hero hero-band">\n <div class="hph" aria-hidden="true">{art}</div>\n'
                f' <div class="wrap heroc">\n   {common}\n </div>\n</header>')
    if t["hero"] == "split":
        return (f'<header class="hero hero-split">\n <div class="invite">\n  <div class="frame">\n'
                f'   <div class="mono" aria-hidden="true"><span data-i1>{n1[0]}</span><span data-i2>{n2[0]}</span></div>\n'
                f'   {common}\n  </div>\n </div>\n <div class="hph" aria-hidden="true">{art}</div>\n</header>')
    raise ValueError(t["hero"])


def build(slug):
    t = THEMES[slug]
    s = BASE
    rep = {
        "SLUG": slug, "NAME": t["name"], "TITLE": t["title"], "DESC": t["desc"], "FONTS": t["fonts"],
        "SERIF": t["serif"], "DISPLAY": t["display"], "SANS": t["sans"],
        "PALETTES": json.dumps(t["palettes"], separators=(",", ":")),
        "ROOTVARS": ";".join(f"{k}:{v}" for k, v in next(iter(t["palettes"].values())).items()),
        "HERO_IMG": t["hero_img"], "HERO_FILTER": t["hero_filter"], "HERO": hero_html(t),
        "EXTRA_CSS": COMMON_CSS + t.get("extra_css", ""), "BODY_EXTRA": t.get("body_extra", ""),
        "DATE": t["date"], "STORY_H": t["story_h"], "STORY_P": t["story_p"], "STORY_IMG": t["story_img"], "STORY_CAP": t["story_cap"],
        "GAL_H": t["gal_h"], "DAY_H": t["day_h"], "THANKS": t["thanks"],
        "RSVP_H": t["rsvp_h"], "RSVP_P": t["rsvp_p"], "YES": t["yes"], "NO": t["no"], "SONG_PH": t["song_ph"], "NOTE_PH": t["note_ph"],
        "REG_H": t["reg_h"], "REG_P": t["reg_p"], "N1": t["n1"], "N2": t["n2"],
    }
    g = t["gal"]
    rep["GAL"] = "\n".join(
        f'  <figure class="{"g-tall" if i == 0 else "g-sq"}"><img loading="lazy" src="{u}" alt="" onerror="this.closest(\'figure\').style.display=\'none\'"><figcaption>{c}</figcaption></figure>'
        for i, (u, c) in enumerate(g))
    rep["SCHED"] = "\n".join(f"   <li><b>{a}</b><span>{b}</span></li>" for a, b in t["sched"])
    rep["VENS"] = "\n".join(f'   <div class="ven"><p class="k">{k}</p><h3>{h}</h3><p>{p}</p><p class="dim">{d}</p></div>' for k, h, p, d in t["ven"])
    rep["FAQ"] = "\n".join(f"  <details><summary>{q}</summary><p>{a}</p></details>" for q, a in t["faq"])
    for k, v in rep.items():
        s = s.replace("@@" + k + "@@", v)
    left = [w for w in s.split("@@")[1::2]]
    if left:
        raise SystemExit(f"{slug}: unreplaced tokens {left[:5]}")
    out = ROOT / slug / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(s, encoding="utf-8", newline="\n")
    print(f"  {slug}: {len(s):,} bytes")


if __name__ == "__main__":
    for slug in (sys.argv[1:] or list(THEMES)):
        build(slug)
