"""themes_extra.py - JC-LAZO-WWT-0919-004
Seven more themed templates, merged into make_themes.THEMES at import:
  harvest   fall / autumn            aquarelle  watercolor
  prism     geometric / modern       meadow     boho
  gilded    vintage / art deco       marigold   South Asian
  papel     Latin / papel picado
Same spec shape as make_themes (see build()). Copy is demo copy; the couple's
hydration replaces every line of it. Photos are Unsplash ids verified live
when this file was written; the gallery hides a photo that fails to load.
"""

U = "https://images.unsplash.com/photo-"
def img(id_, w=1200, q=74):
    return f"{U}{id_}?auto=format&fit=crop&w={w}&q={q}"

# the two lines every RSVP form shares; a theme may override
_COMMON = dict(
    song_ph="A song that gets everyone dancing (optional)",
    note_ph="Dietary notes, song requests, questions…",
    reg_h="Your presence is the whole point.",
    body_extra="",
)

def spec(**kw):
    d = dict(_COMMON)
    d.update(kw)
    return d


EXTRA = {
 "harvest": spec(
  name="Harvest", title="Harvest — a fall wedding website template | Lazo",
  desc="A free fall wedding website template from Lazo — maple, pumpkin and plum, with RSVPs, schedule, registry, and a site that says We're Married after the big day.",
  fonts="family=Playfair+Display:ital,wght@0,500;0,600;1,500&family=Lora:ital,wght@0,400;0,500;1,400&family=Jost:wght@300;400;500&display=swap",
  serif='"Lora",serif', display='"Playfair Display","Lora",serif', sans='"Jost",sans-serif',
  palettes={"maple":{"--bg":"#FBF6F0","--ink":"#3B2418","--mut":"#8A6B57","--acc":"#B4451F","--panel":"#FFFFFF","--line":"#EAD9CB","--sand":"#F3E4D3"},
            "pumpkin":{"--bg":"#FCF7EF","--ink":"#3A2A1A","--mut":"#8C7256","--acc":"#D3762A","--panel":"#FFFFFF","--line":"#EEDFC9","--sand":"#F5E7D0"},
            "plum":{"--bg":"#F9F4F5","--ink":"#3A1F2E","--mut":"#8A6A78","--acc":"#7A2E4E","--panel":"#FFFFFF","--line":"#E9D8DF","--sand":"#F1E3E8"},
            "moss":{"--bg":"#F6F7F1","--ink":"#2B3324","--mut":"#6E7A62","--acc":"#5E6E3A","--panel":"#FFFFFF","--line":"#DDE2D0","--sand":"#EBEDDC"}},
  hero="full", hero_img=img("1476820865390-c52aeebb9891", 1900), hero_filter="saturate(1.08) brightness(.94)",
  eyebrow="When the leaves turn", cdlabel="days until the harvest", n1="Hazel", n2="Rowan",
  where="Stonebridge Orchard · Hudson Valley, New York", date="2027-10-16",
  story_h="A cider stand, a wrong turn, and a very good pie.", story_p="We met in line at the orchard the October the hayride broke down. Nobody wanted to walk back, so we didn't. Four falls later we are getting married under the same maples, with the people who make our world and as much pie as the kitchen will allow.",
  story_img=img("1508193638397-1c4234db14d8", 1000), story_cap="Four falls in",
  gal_h="Cider, woodsmoke, the two of us.", gal=[(img("1476820865390-c52aeebb9891"), "The lane in October"), (img("1508193638397-1c4234db14d8", 900), "Where she asked"), (img("1510076857177-7470076d4098", 900), "Long tables, long evening")],
  day_h="Vows under the maples, dinner in the barn, a bonfire until the last log.",
  sched=[("3:30 pm","Guests arrive - hot cider and a hayride to the ceremony"),("4:00 pm","Ceremony under the maples"),("4:45 pm","Cocktails at the cider press"),("6:00 pm","Dinner in the barn"),("8:30 pm","Bonfire, pie and dancing")],
  ven=[("Ceremony","The Maple Row","4:00 in the afternoon","Bring a layer - the light goes golden and the air goes cold"),("Reception","The Big Barn","4:45 until the fire burns down","Dinner, toasts, pie and a very long dance")],
  thanks="The leaves turned right on time. Thank you for coming up the valley for us.",
  rsvp_h="Tell us you're coming to the orchard.", rsvp_p="Kindly reply by September 15 - the pie count waits for no one.", yes="Coming to the orchard", no="Sending love from afar",
  note_ph="Dietary notes, song requests, pie preferences…",
  reg_p="If you would like to give more, we have gathered a few things for the farmhouse - and a fund for the cider press we keep pricing.",
  faq=[("What should I wear?","Fall cocktail - wool, velvet, deep colours, boots you can walk a lane in. It is warm at four and cold by seven."),("Is it outdoors?","The ceremony is; the barn has a roof, heaters and a fire. Rain moves the ceremony inside."),("Where should we stay?","Rooms are held at the Stonebridge Inn through September 15 under Hazel and Rowan.")],
  extra_css="""
.leaves{position:absolute;inset:0;pointer-events:none;overflow:hidden;z-index:1}
.leaves i{position:absolute;top:-24px;width:14px;height:14px;border-radius:0 60% 0 60%;background:var(--acc);opacity:.7;animation:leaffall linear infinite}
@keyframes leaffall{0%{transform:translate3d(0,0,0) rotate(0)}100%{transform:translate3d(var(--dx,0),110vh,0) rotate(720deg)}}
.k::before{content:"\\1F342";margin-right:8px;font-size:12px}
section:nth-of-type(odd){background:linear-gradient(180deg,var(--bg),color-mix(in srgb,var(--sand) 45%,var(--bg)))}
@media(prefers-reduced-motion:reduce){.leaves{display:none}}
""",
  hero_art="""<div class="leaves" aria-hidden="true"></div>""",
  body_extra="""
<script>
(function(){var s=document.querySelector(".leaves");if(!s||matchMedia("(prefers-reduced-motion: reduce)").matches)return;var n=window.innerWidth<640?12:24,h="",c=["#B4451F","#D3762A","#E0A339","#8A3B2A"];
for(var i=0;i<n;i++){var sz=(9+Math.random()*10).toFixed(0);h+='<i style="left:'+(Math.random()*100).toFixed(2)+'%;width:'+sz+'px;height:'+sz+'px;background:'+c[i%4]+';opacity:'+(.45+Math.random()*.4).toFixed(2)+';--dx:'+((Math.random()*160-80).toFixed(0))+'px;animation-duration:'+(12+Math.random()*14).toFixed(1)+'s;animation-delay:-'+(Math.random()*20).toFixed(1)+'s"></i>'}
s.innerHTML=h;})();
</script>""",
 ),

 "aquarelle": spec(
  name="Aquarelle", title="Aquarelle — a watercolor wedding website template | Lazo",
  desc="A free watercolor wedding website template from Lazo — soft washes of blush, sky and lilac, with RSVPs, schedule, registry, and a site that says We're Married after the big day.",
  fonts="family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500;1,600&family=Karla:wght@300;400;500&display=swap",
  serif='"Cormorant Garamond",serif', display='"Cormorant Garamond",serif', sans='"Karla",sans-serif',
  palettes={"blush":{"--bg":"#FDF8F7","--ink":"#4A3A40","--mut":"#93808A","--acc":"#D08A9B","--panel":"#FFFFFF","--line":"#F1E1E5","--sand":"#F7E9EC"},
            "sky":{"--bg":"#F6FAFC","--ink":"#2F4352","--mut":"#7A8E9C","--acc":"#6FA6C8","--panel":"#FFFFFF","--line":"#DCEAF2","--sand":"#E7F1F7"},
            "lilac":{"--bg":"#FAF8FC","--ink":"#3F3550","--mut":"#8B819C","--acc":"#9B86C4","--panel":"#FFFFFF","--line":"#E7E0F1","--sand":"#EFEAF6"},
            "sage":{"--bg":"#F7FAF6","--ink":"#34423A","--mut":"#7B8A80","--acc":"#7FA88E","--panel":"#FFFFFF","--line":"#DCE8DF","--sand":"#E9F1EA"}},
  hero="band", hero_img=img("1490750967868-88aa4486c946", 1600), hero_filter="saturate(.9) brightness(1.02)",
  eyebrow="Painted in soft light", cdlabel="days until the first brushstroke", n1="Iris", n2="Theo",
  where="The Glasshouse · Portland, Oregon", date="2027-05-08",
  story_h="A shared umbrella and a museum that closed early.", story_p="We met on the steps of the art museum in the rain, both locked out, one umbrella between us. We walked to the river instead. Five springs later we are getting married in the glasshouse, and yes, we are bringing umbrellas.",
  story_img=img("1464366400600-7168b8af9bc3", 1000), story_cap="Five springs in",
  gal_h="Soft light, wet paint, the two of us.", gal=[(img("1490750967868-88aa4486c946"), "The glasshouse in May"), (img("1464366400600-7168b8af9bc3", 900), "Where he asked"), (img("1520854221256-17451cc331bf", 900), "Evenings like this one")],
  day_h="Vows among the ferns, dinner under glass, dancing as the rain comes in.",
  sched=[("3:30 pm","Guests arrive - tea, lemonade and a look around the gardens"),("4:00 pm","Ceremony in the fern house"),("4:40 pm","Cocktails on the terrace"),("6:00 pm","Dinner under glass"),("8:30 pm","Dancing until the lights go down")],
  ven=[("Ceremony","The Fern House","4:00 in the afternoon","Warm, green and dry whatever the sky does"),("Reception","The Glasshouse","4:40 until the last dance","Dinner, toasts and dancing under the roof")],
  thanks="It rained, of course. Thank you for coming in from it with us.",
  rsvp_h="Tell us you're coming to the glasshouse.", rsvp_p="Kindly reply by April 1 - the kitchen needs a count before the tulips go.", yes="Coming to the glasshouse", no="Sending love from afar",
  reg_p="If you would like to give more, we have gathered a few things for the flat - and a fund for the trip to the lakes we keep sketching.",
  faq=[("What should I wear?","Garden party - soft colours, florals, something you can dance in. The glasshouse is warm; the terrace is not."),("Is it outdoors?","Cocktails are on the terrace if the sky allows; everything else is under glass."),("Where should we stay?","Rooms are held at the Hotel Larkspur through April 1 under Iris and Theo.")],
  extra_css="""
.hero-band .hph{position:relative;overflow:hidden;background:var(--bg)}
.wash{position:absolute;inset:-20%;pointer-events:none;filter:blur(38px);opacity:.75}
.wash i{position:absolute;border-radius:50%;background:var(--acc);mix-blend-mode:multiply;animation:washdrift 22s ease-in-out infinite alternate}
.wash i:nth-child(1){left:6%;top:10%;width:38vw;height:38vw;opacity:.42}
.wash i:nth-child(2){right:4%;top:28%;width:32vw;height:32vw;opacity:.34;background:color-mix(in srgb,var(--acc) 55%,var(--sand));animation-duration:28s}
.wash i:nth-child(3){left:32%;bottom:-6%;width:44vw;height:30vw;opacity:.28;background:color-mix(in srgb,var(--acc) 35%,#fff);animation-duration:34s}
@keyframes washdrift{to{transform:translate3d(4%,-3%,0) scale(1.06)}}
h2::after{content:"";display:block;width:64px;height:8px;margin-top:12px;border-radius:999px;background:linear-gradient(90deg,var(--acc),transparent);opacity:.55}
.center h2::after{margin-left:auto;margin-right:auto}
.k::before{content:"";display:inline-block;width:10px;height:10px;margin:0 8px -1px 0;border-radius:50% 50% 50% 0;background:var(--acc);opacity:.7}
@media(prefers-reduced-motion:reduce){.wash i{animation:none}}
""",
  hero_art="""<div class="wash" aria-hidden="true"><i></i><i></i><i></i></div>""",
 ),

 "prism": spec(
  name="Prism", title="Prism — a geometric modern wedding website template | Lazo",
  desc="A free geometric wedding website template from Lazo — clean lines, terrazzo color and confident type, with RSVPs, schedule, registry, and a site that says We're Married after the big day.",
  fonts="family=Josefin+Sans:wght@300;400;600&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;1,9..40,400&display=swap",
  serif='"Josefin Sans",sans-serif', display='"Josefin Sans",sans-serif', sans='"DM Sans",sans-serif',
  palettes={"terrazzo":{"--bg":"#FBF9F6","--ink":"#1F1E1C","--mut":"#7A7570","--acc":"#E2694E","--panel":"#FFFFFF","--line":"#E9E3DB","--sand":"#F3EDE4"},
            "ink":{"--bg":"#F4F4F2","--ink":"#161616","--mut":"#6C6C6A","--acc":"#1F2A44","--panel":"#FFFFFF","--line":"#DEDEDA","--sand":"#E8E8E3"},
            "coral":{"--bg":"#FFF8F5","--ink":"#2A1E1B","--mut":"#8A7570","--acc":"#F0736A","--panel":"#FFFFFF","--line":"#F3DEDA","--sand":"#FBE9E4"},
            "mint":{"--bg":"#F5FAF8","--ink":"#1C2926","--mut":"#6F807B","--acc":"#2FA58B","--panel":"#FFFFFF","--line":"#D9E8E2","--sand":"#E6F2ED"}},
  hero="band", hero_img=img("1520854221256-17451cc331bf", 1600), hero_filter="saturate(1) brightness(1)",
  eyebrow="Two lines, one point", cdlabel="days until we intersect", n1="Maya", n2="Julian",
  where="The Foundry · Chicago, Illinois", date="2027-09-25",
  story_h="Same coffee order, opposite sides of the counter.", story_p="We met when she corrected his geometry on a napkin and he corrected her coffee order. Both were right. Three years later we are getting married in a converted foundry with big windows, good light and the people who make our world.",
  story_img=img("1519741497674-611481863552", 1000), story_cap="Three years in",
  gal_h="Straight lines, soft light, the two of us.", gal=[(img("1520854221256-17451cc331bf"), "The foundry floor"), (img("1519741497674-611481863552", 900), "Where he asked"), (img("1519225421980-715cb0215aed", 900), "Long table, big windows")],
  day_h="Vows by the windows, dinner on the floor, dancing under the trusses.",
  sched=[("4:30 pm","Guests arrive - aperitivo at the bar"),("5:00 pm","Ceremony by the north windows"),("5:30 pm","Cocktails on the roof"),("6:45 pm","Dinner on the foundry floor"),("9:00 pm","Dancing under the trusses")],
  ven=[("Ceremony","The North Windows","5:00 in the afternoon","Standing room by the glass if you want the light"),("Reception","The Foundry Floor","5:30 until the DJ gives up","Dinner, toasts and a very loud dance")],
  thanks="The lines met right on time. Thank you for coming to the city for us.",
  rsvp_h="Tell us you're coming to the foundry.", rsvp_p="Kindly reply by August 20 - the kitchen needs a count.", yes="Coming to the foundry", no="Sending love from afar",
  reg_p="If you would like to give more, we have gathered a few things for the loft - and a fund for the trip to Tokyo we keep drawing.",
  faq=[("What should I wear?","Cocktail, with a modern eye - clean lines, bold colour, comfortable shoes for concrete floors."),("Is there parking?","A lot beside the building, free after four. Rideshare drops at the north door."),("Where should we stay?","Rooms are held at the Hotel Meridian through August 20 under Maya and Julian.")],
  extra_css="""
.hero-band .hph{position:relative;overflow:hidden;background:var(--sand)}
.geo{position:absolute;inset:0;pointer-events:none}
.geo svg{width:100%;height:100%}
.eyebrow{letter-spacing:.6em}
h1{letter-spacing:.02em;text-transform:uppercase;font-weight:300}
h1 .amp{font-style:normal;font-weight:300}
h2{text-transform:uppercase;letter-spacing:.06em;font-weight:400;font-size:clamp(24px,3.6vw,36px)}
.k::before{content:"";display:inline-block;width:10px;height:10px;margin:0 8px -1px 0;background:var(--acc);transform:rotate(45deg)}
.ven,.chap,.vt,form{border-radius:4px}
""",
  hero_art="""<div class="geo" aria-hidden="true"><svg viewBox="0 0 1200 500" preserveAspectRatio="xMidYMid slice">
 <g fill="none" stroke="var(--acc)" stroke-width="1.5" opacity=".55">
  <circle cx="200" cy="140" r="120"/><circle cx="1000" cy="380" r="160"/><path d="M0 500L420 80M520 500L940 80M1040 500L1200 340"/>
 </g>
 <g fill="var(--acc)" opacity=".18"><polygon points="640,60 760,60 700,164"/><rect x="60" y="330" width="120" height="120" transform="rotate(20 120 390)"/><circle cx="900" cy="120" r="46"/></g>
 <g fill="var(--ink)" opacity=".08"><rect x="300" y="200" width="160" height="160" transform="rotate(45 380 280)"/><circle cx="1100" cy="90" r="70"/></g>
</svg></div>""",
 ),

 "meadow": spec(
  name="Meadow", title="Meadow — a boho wedding website template | Lazo",
  desc="A free boho wedding website template from Lazo — pampas, terracotta and warm neutrals, with RSVPs, schedule, registry, and a site that says We're Married after the big day.",
  fonts="family=Marcellus&family=Cormorant+Garamond:ital,wght@0,500;1,500&family=Nunito+Sans:wght@300;400;600&display=swap",
  serif='"Cormorant Garamond",serif', display='"Marcellus","Cormorant Garamond",serif', sans='"Nunito Sans",sans-serif',
  palettes={"pampas":{"--bg":"#FBF7F1","--ink":"#3D3229","--mut":"#8C7E70","--acc":"#B98A5E","--panel":"#FFFFFF","--line":"#EBE1D4","--sand":"#F3EADD"},
            "terracotta":{"--bg":"#FCF6F1","--ink":"#3E2A21","--mut":"#8F7566","--acc":"#C4693F","--panel":"#FFFFFF","--line":"#EFDDD1","--sand":"#F6E6DA"},
            "rust":{"--bg":"#FAF4EE","--ink":"#3A2620","--mut":"#8A6F64","--acc":"#9E4A2F","--panel":"#FFFFFF","--line":"#EAD8CD","--sand":"#F1E1D5"},
            "olive":{"--bg":"#F8F7F1","--ink":"#33352A","--mut":"#787A68","--acc":"#7C7F4B","--panel":"#FFFFFF","--line":"#E1E0D0","--sand":"#ECEBDC"}},
  hero="full", hero_img=img("1500382017468-9049fed747ef", 1900), hero_filter="saturate(.96) brightness(.95) sepia(.12)",
  eyebrow="Barefoot in the long grass", cdlabel="days until the meadow", n1="Wren", n2="Jasper",
  where="Fox Hollow Farm · Ojai, California", date="2027-06-05",
  story_h="A borrowed van, a flat tyre, and the best sunset either of us had seen.", story_p="We met on a road trip neither of us planned, when the van gave up outside Ojai and the sunset didn't. We stayed the week. Four summers later we are getting married in the meadow behind the farmhouse, shoes optional, with the people who make our world.",
  story_img=img("1465495976277-4387d4b0b4c6", 1000), story_cap="Four summers in",
  gal_h="Dry grass, golden hour, the two of us.", gal=[(img("1500382017468-9049fed747ef"), "The meadow at six"), (img("1465495976277-4387d4b0b4c6", 900), "Where she asked"), (img("1519225421980-715cb0215aed", 900), "Long tables in the grass")],
  day_h="Vows in the meadow, dinner under the oaks, dancing under string lights.",
  sched=[("4:00 pm","Guests arrive - lemonade, shade and a place to leave your shoes"),("4:30 pm","Ceremony in the meadow"),("5:15 pm","Cocktails at the farmhouse"),("6:30 pm","Dinner under the oaks"),("8:30 pm","Dancing under the lights")],
  ven=[("Ceremony","The Meadow","4:30 in the afternoon","Long grass, low sun, blankets on the hay bales"),("Reception","Under the Oaks","5:15 until the lights go off","Dinner, toasts and dancing on the boards")],
  thanks="The sun went down right on time. Thank you for coming out to the meadow with us.",
  rsvp_h="Tell us you're coming to the meadow.", rsvp_p="Kindly reply by May 1 - the farmhouse kitchen needs a count.", yes="Coming to the meadow", no="Sending love from afar",
  reg_p="If you would like to give more, we have gathered a few things for the cabin - and a fund for the van we are, unbelievably, buying.",
  faq=[("What should I wear?","Boho garden - linen, flowy things, earth tones. Flat shoes or none; it is a meadow."),("Is it outdoors?","All of it. Shade, fans and blankets are provided; the barn is the rain plan."),("Where should we stay?","Rooms are held at the Ojai Rancho Inn through May 1 under Wren and Jasper.")],
  extra_css="""
.pampas{position:absolute;left:0;right:0;bottom:-2px;height:150px;z-index:1;pointer-events:none;overflow:hidden}
.pampas svg{width:100%;height:100%}
.pampas .p{transform-origin:bottom center;animation:sway 6s ease-in-out infinite alternate}
.pampas .p:nth-child(2n){animation-duration:7.5s;animation-delay:-2s}.pampas .p:nth-child(3n){animation-duration:9s;animation-delay:-4s}
@keyframes sway{from{transform:rotate(-2deg)}to{transform:rotate(2.5deg)}}
.hero-full{padding-bottom:120px}
.k::before{content:"";display:inline-block;width:12px;height:12px;margin:0 8px -1px 0;border-radius:50%;border:1.5px solid var(--acc)}
h2{font-weight:500}
section:nth-of-type(odd){background:linear-gradient(180deg,var(--bg),color-mix(in srgb,var(--sand) 50%,var(--bg)))}
@media(prefers-reduced-motion:reduce){.pampas .p{animation:none}}
""",
  hero_art="""<div class="pampas" aria-hidden="true"><svg viewBox="0 0 1200 150" preserveAspectRatio="xMidYMax slice" fill="none" stroke="#F3EADD" stroke-linecap="round">
 <g class="p"><path d="M80 150V70" stroke-width="2"/><ellipse cx="80" cy="52" rx="9" ry="26" fill="#F3EADD" opacity=".75"/></g>
 <g class="p"><path d="M200 150V40" stroke-width="2"/><ellipse cx="200" cy="22" rx="10" ry="30" fill="#F3EADD" opacity=".7"/></g>
 <g class="p"><path d="M320 150V85" stroke-width="2"/><ellipse cx="320" cy="66" rx="8" ry="24" fill="#F3EADD" opacity=".8"/></g>
 <g class="p"><path d="M900 150V60" stroke-width="2"/><ellipse cx="900" cy="42" rx="9" ry="27" fill="#F3EADD" opacity=".75"/></g>
 <g class="p"><path d="M1030 150V30" stroke-width="2"/><ellipse cx="1030" cy="12" rx="10" ry="30" fill="#F3EADD" opacity=".7"/></g>
 <g class="p"><path d="M1140 150V80" stroke-width="2"/><ellipse cx="1140" cy="62" rx="8" ry="24" fill="#F3EADD" opacity=".8"/></g>
</svg></div>""",
 ),

 "gilded": spec(
  name="Gilded", title="Gilded — a vintage art deco wedding website template | Lazo",
  desc="A free art deco wedding website template from Lazo — gold fans, onyx and emerald, with RSVPs, schedule, registry, and a site that says We're Married after the big day.",
  fonts="family=Poiret+One&family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500&family=Josefin+Sans:wght@300;400&display=swap",
  serif='"Cormorant Garamond",serif', display='"Poiret One","Cormorant Garamond",serif', sans='"Josefin Sans",sans-serif',
  palettes={"onyx":{"--bg":"#141312","--ink":"#F2EADB","--mut":"#A79C88","--acc":"#D4AF5A","--panel":"#1E1C1A","--line":"#332F2A","--sand":"#26231F"},
            "emerald":{"--bg":"#0F2A24","--ink":"#EEF3EE","--mut":"#9DB5AA","--acc":"#D9B96A","--panel":"#153630","--line":"#274A42","--sand":"#1B3D35"},
            "ivory":{"--bg":"#FAF6EE","--ink":"#2B2520","--mut":"#7E7263","--acc":"#B08D3E","--panel":"#FFFFFF","--line":"#E9E0CF","--sand":"#F2EADA"},
            "burgundy":{"--bg":"#2A1016","--ink":"#F5E9EA","--mut":"#B9989E","--acc":"#D9B36A","--panel":"#361820","--line":"#4E2830","--sand":"#3D1B24"}},
  hero="band", hero_img=img("1519741497674-611481863552", 1600), hero_filter="saturate(.9) brightness(.9)",
  eyebrow="Est. this evening", cdlabel="days until the gala", n1="Evelyn", n2="Augustus",
  where="The Palladium Ballroom · Detroit, Michigan", date="2027-11-20",
  story_h="A jazz bar, a borrowed coat, and a very long last song.", story_p="We met at a bar with a piano and no coat check, when he lent her his coat and she kept it for the winter. Six winters later we are getting married in a ballroom with chandeliers, a big band and the people who make our world.",
  story_img=img("1519225421980-715cb0215aed", 1000), story_cap="Six winters in",
  gal_h="Gold light, black tie, the two of us.", gal=[(img("1519741497674-611481863552"), "The ballroom at eight"), (img("1606800052052-a08af7148866", 900), "Where he asked"), (img("1519225421980-715cb0215aed", 900), "The long table")],
  day_h="Vows under the chandeliers, dinner in the ballroom, a big band until two.",
  sched=[("5:30 pm","Guests arrive - champagne in the foyer"),("6:00 pm","Ceremony under the chandeliers"),("6:45 pm","Cocktails in the gallery"),("8:00 pm","Dinner in the ballroom"),("10:00 pm","The band, until they stop")],
  ven=[("Ceremony","The Grand Foyer","6:00 in the evening","Under the chandeliers; the good seats are on the left"),("Reception","The Palladium Ballroom","6:45 until the band packs up","Dinner, toasts and a very long dance")],
  thanks="The band played until two. Thank you for dressing up for us.",
  rsvp_h="Tell us you're coming to the gala.", rsvp_p="Kindly reply by October 20 - the kitchen needs a count before the season.", yes="Coming to the gala", no="Raising a glass from afar",
  song_ph="A song the band should know (optional)",
  reg_p="If you would like to give more, we have gathered a few things for the apartment - and a fund for the trip to Paris we keep toasting.",
  faq=[("What should I wear?","Black tie, with a nod to the twenties if you like - long dresses, tuxedos, sparkle welcome."),("Is there parking?","Valet at the Woodward entrance from five. Rideshare drops at the same door."),("Where should we stay?","Rooms are held at the Book Tower through October 20 under Evelyn and Augustus.")],
  extra_css="""
.hero-band .hph{position:relative;overflow:hidden;background:var(--bg)}
.deco{position:absolute;inset:0;pointer-events:none}
.deco svg{width:100%;height:100%}
.eyebrow{letter-spacing:.7em}
h1{letter-spacing:.08em;text-transform:uppercase}
h1 .amp{font-style:normal;font-family:"Cormorant Garamond",serif}
h2{letter-spacing:.04em}
.k{letter-spacing:.5em}
.k::before,.k::after{content:"";display:inline-block;width:22px;height:1px;background:var(--acc);margin:0 10px 4px;vertical-align:middle}
.ven,.chap,.vt,form,.pimg,.gal figure{border:1px solid var(--acc);border-radius:2px;outline:1px solid var(--line);outline-offset:4px}
input,textarea{background:var(--panel);color:var(--ink);border-color:var(--line)}
input::placeholder,textarea::placeholder{color:var(--mut)}
""",
  hero_art="""<div class="deco" aria-hidden="true"><svg viewBox="0 0 1200 500" preserveAspectRatio="xMidYMid slice" fill="none" stroke="var(--acc)">
 <g opacity=".5" stroke-width="1.2">
  <path d="M600 500 V300 M600 300 L520 380 M600 300 L680 380 M600 300 L560 400 M600 300 L640 400 M600 300 L590 420 M600 300 L610 420"/>
  <path d="M0 500 V380 L60 440 M0 380 L120 500 M0 300 L200 500 M1200 500 V380 L1140 440 M1200 380 L1080 500 M1200 300 L1000 500"/>
  <path d="M0 40 H1200 M0 56 H1200" opacity=".7"/>
 </g>
 <g opacity=".22" stroke-width="1">
  <circle cx="600" cy="120" r="70"/><circle cx="600" cy="120" r="90"/><circle cx="600" cy="120" r="110"/>
  <path d="M600 10 V230 M490 120 H710"/>
 </g>
</svg></div>""",
 ),

 "marigold": spec(
  name="Marigold", title="Marigold — a South Asian wedding website template | Lazo",
  desc="A free South Asian wedding website template from Lazo — marigold garlands, mehndi motifs, a multi-day schedule, RSVPs, registry, and a site that says We're Married after the big day.",
  fonts="family=Yeseva+One&family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500&family=Mulish:wght@300;400;600&display=swap",
  serif='"Cormorant Garamond",serif', display='"Yeseva One","Cormorant Garamond",serif', sans='"Mulish",sans-serif',
  palettes={"marigold":{"--bg":"#FFF8EC","--ink":"#4A2410","--mut":"#9A6B45","--acc":"#E4901E","--panel":"#FFFFFF","--line":"#F3DFBF","--sand":"#FBEBCB"},
            "magenta":{"--bg":"#FFF5F8","--ink":"#4A1230","--mut":"#9C5A7A","--acc":"#C81E6C","--panel":"#FFFFFF","--line":"#F4D6E3","--sand":"#FBE2EC"},
            "royal":{"--bg":"#F4F6FC","--ink":"#1B2350","--mut":"#616A9B","--acc":"#2E45B8","--panel":"#FFFFFF","--line":"#D8DDF2","--sand":"#E6EAF8"},
            "emerald":{"--bg":"#F3FAF6","--ink":"#123A2A","--mut":"#5C8A74","--acc":"#178A5A","--panel":"#FFFFFF","--line":"#D2EBDD","--sand":"#DFF2E7"}},
  hero="band", hero_img=img("1519741497674-611481863552", 1600), hero_filter="saturate(1.1) brightness(.95)",
  eyebrow="Three days, one celebration", cdlabel="days until the baraat", n1="Priya", n2="Arjun",
  where="The Grand Pavilion · Edison, New Jersey", date="2027-08-14",
  story_h="Two families, one dance floor, and a plate of jalebi.", story_p="We met at a friend's sangeet, when both of us were pushed onto the dance floor by aunties who had, it turns out, planned it. Three years later we are getting married over three days in August, with both families, a very long guest list and the people who make our world.",
  story_img=img("1490750967868-88aa4486c946", 1000), story_cap="Three years in",
  gal_h="Marigolds, mehndi, the two of us.", gal=[(img("1519741497674-611481863552"), "The mandap in August"), (img("1490750967868-88aa4486c946", 900), "Where he asked"), (img("1519225421980-715cb0215aed", 900), "The long table")],
  day_h="Mehndi on Thursday, sangeet on Friday, the baraat and the pheras on Saturday.",
  sched=[("Thursday, 4:00 pm","Mehndi at the house - henna, chai and music"),("Friday, 7:00 pm","Sangeet at the Pavilion - performances, then everyone dances"),("Saturday, 9:30 am","Baraat arrives - join the procession at the gate"),("Saturday, 11:00 am","Ceremony under the mandap"),("Saturday, 7:00 pm","Reception, dinner and dancing until late")],
  ven=[("Ceremony","The Mandap, Grand Pavilion","Saturday, 11:00 in the morning","Shoes off at the entrance; seating is open"),("Reception","The Grand Ballroom","Saturday, 7:00 in the evening","Dinner, toasts and dancing until the DJ gives up")],
  thanks="The baraat arrived only forty minutes late. Thank you for celebrating three days with us.",
  rsvp_h="Tell us which days you're coming.", rsvp_p="Kindly reply by July 10 - the caterers need a count for each event.", yes="Coming to celebrate", no="Sending blessings from afar",
  note_ph="Dietary notes (veg, Jain, halal), song requests, which events you'll attend…",
  reg_p="Your blessings are the gift. If you would like to give more, we have gathered a few things for the home - and a fund for the honeymoon in Kerala.",
  faq=[("What should I wear?","Indian or Western formal - lehengas, sarees, sherwanis, suits. Bright colour is encouraged for the sangeet; avoid red on Saturday, which is for the bride."),("What is a baraat?","The groom's procession to the venue, with music and dancing. Everyone on the groom's side joins in at the gate at 9:30; the bride's side receives it at the door."),("Where should we stay?","Rooms are held at the Edison Marriott through July 10 under Priya and Arjun. A shuttle runs to every event.")],
  extra_css="""
.hero-band .hph{position:relative;overflow:hidden;background:var(--bg)}
.garland{position:absolute;inset:0;pointer-events:none}
.garland svg{width:100%;height:100%}
.eyebrow{letter-spacing:.5em}
.k::before{content:"";display:inline-block;width:12px;height:12px;margin:0 8px -1px 0;border-radius:50%;background:radial-gradient(circle,var(--acc) 35%,transparent 40%),conic-gradient(var(--acc) 0 12deg,transparent 12deg 45deg,var(--acc) 45deg 57deg,transparent 57deg 90deg,var(--acc) 90deg 102deg,transparent 102deg 135deg,var(--acc) 135deg 147deg,transparent 147deg 180deg,var(--acc) 180deg 192deg,transparent 192deg 225deg,var(--acc) 225deg 237deg,transparent 237deg 270deg,var(--acc) 270deg 282deg,transparent 282deg 315deg,var(--acc) 315deg 327deg,transparent 327deg)}
h2{font-weight:600}
.ven,.chap,.vt,form{border-top:3px solid var(--acc)}
section:nth-of-type(odd){background:linear-gradient(180deg,var(--bg),color-mix(in srgb,var(--sand) 55%,var(--bg)))}
.sched li b{color:var(--acc)}
""",
  hero_art="""<div class="garland" aria-hidden="true"><svg viewBox="0 0 1200 500" preserveAspectRatio="xMidYMin slice">
 <defs><radialGradient id="mg" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#FFD166"/><stop offset="1" stop-color="var(--acc)"/></radialGradient></defs>
 <path d="M-20 40 Q 300 200 600 60 T 1220 40" fill="none" stroke="var(--acc)" stroke-width="2" opacity=".5"/>
 <path d="M-20 90 Q 300 250 600 110 T 1220 90" fill="none" stroke="var(--acc)" stroke-width="2" opacity=".35"/>
 <g fill="url(#mg)">
  <circle cx="60" cy="70" r="14"/><circle cx="150" cy="112" r="16"/><circle cx="250" cy="140" r="14"/><circle cx="360" cy="140" r="16"/><circle cx="470" cy="112" r="14"/><circle cx="560" cy="80" r="16"/>
  <circle cx="650" cy="80" r="14"/><circle cx="740" cy="112" r="16"/><circle cx="840" cy="140" r="14"/><circle cx="950" cy="140" r="16"/><circle cx="1050" cy="112" r="14"/><circle cx="1140" cy="70" r="16"/>
 </g>
 <g fill="var(--acc)" opacity=".18"><path d="M600 470 c-40-60-40-120 0-160 c40 40 40 100 0 160z"/><path d="M560 460 c-50-40-70-90-50-140 c50 20 70 70 50 140z"/><path d="M640 460 c50-40 70-90 50-140 c-50 20-70 70-50 140z"/></g>
</svg></div>""",
 ),

 "papel": spec(
  name="Papel", title="Papel — a Latin fiesta wedding website template | Lazo",
  desc="A free Latin wedding website template from Lazo — papel picado banners, cobalt and terracotta, with RSVPs, schedule, registry, and a site that says We're Married after the big day.",
  fonts="family=Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,700;1,9..144,500&family=Nunito:wght@300;400;600&display=swap",
  serif='"Fraunces",serif', display='"Fraunces",serif', sans='"Nunito",sans-serif',
  palettes={"fiesta":{"--bg":"#FFF9F2","--ink":"#3A2118","--mut":"#8F6A5A","--acc":"#E0512F","--panel":"#FFFFFF","--line":"#F3DCD1","--sand":"#FBE8DA"},
            "cobalt":{"--bg":"#F4F7FC","--ink":"#16264A","--mut":"#5E6E92","--acc":"#1F4FB8","--panel":"#FFFFFF","--line":"#D7E0F2","--sand":"#E5ECF8"},
            "terracotta":{"--bg":"#FBF5EF","--ink":"#3C2A20","--mut":"#8E7566","--acc":"#B8542E","--panel":"#FFFFFF","--line":"#EEDCCF","--sand":"#F5E5D6"},
            "jade":{"--bg":"#F3FAF7","--ink":"#153B30","--mut":"#5F8A7A","--acc":"#159A72","--panel":"#FFFFFF","--line":"#D1EBE1","--sand":"#DFF2EA"}},
  hero="band", hero_img=img("1465495976277-4387d4b0b4c6", 1600), hero_filter="saturate(1.1) brightness(.96)",
  eyebrow="¡Nos casamos!", cdlabel="days until the fiesta", n1="Lucía", n2="Mateo",
  where="Hacienda del Sol · San Antonio, Texas", date="2027-04-24",
  story_h="A taquería, a shared table, and one very good song.", story_p="We met at a taquería with one table left, and we shared it. The band played the song her abuela used to sing and he knew every word. Four springs later we are getting married at the hacienda with both families, a mariachi and the people who make our world.",
  story_img=img("1519225421980-715cb0215aed", 1000), story_cap="Four springs in",
  gal_h="Papel picado, mariachi, the two of us.", gal=[(img("1465495976277-4387d4b0b4c6"), "The courtyard in April"), (img("1519225421980-715cb0215aed", 900), "Where he asked"), (img("1520854221256-17451cc331bf", 900), "The long table")],
  day_h="Vows in the chapel, dinner in the courtyard, mariachi and dancing until the last song.",
  sched=[("4:00 pm","Guests arrive - agua fresca in the courtyard"),("4:30 pm","Ceremony in the chapel - the lazo and the arras"),("5:15 pm","Cocktails and mariachi"),("6:30 pm","Dinner in the courtyard"),("8:30 pm","La hora loca, then dancing until late")],
  ven=[("Ceremony","The Chapel","4:30 in the afternoon","The lazo is placed at the vows; godparents sit in the first row"),("Reception","The Courtyard","5:15 until the last song","Dinner, toasts, mariachi and a very long dance")],
  thanks="The mariachi played one more. Thank you for celebrating with both our families.",
  rsvp_h="Tell us you're coming to the fiesta.", rsvp_p="Kindly reply by March 20 - the kitchen needs a count for the tamales.", yes="Coming to the fiesta", no="Sending love from afar",
  song_ph="A song the mariachi should play (optional)",
  reg_p="Your presence is the gift. If you would like to give more, we have gathered a few things for the house - and a fund for the trip to Oaxaca we keep planning.",
  faq=[("What should I wear?","Cocktail, with colour - the courtyard is warm in April and the dance floor is stone."),("What is the lazo?","A rosary or ribbon placed around the couple during the vows by the padrinos, a sign the two are joined. Lazo is named for it."),("Where should we stay?","Rooms are held at the Hotel Emma through March 20 under Lucía and Mateo.")],
  extra_css="""
.hero-band .hph{position:relative;overflow:hidden;background:var(--bg)}
.picado{position:absolute;inset:0;pointer-events:none}
.picado svg{width:100%;height:100%}
.picado .row{animation:flutter 5s ease-in-out infinite alternate;transform-origin:50% 0}
.picado .row:nth-child(2){animation-duration:6.5s;animation-delay:-2s}
@keyframes flutter{from{transform:skewX(-1deg)}to{transform:skewX(1.2deg)}}
.eyebrow{letter-spacing:.4em;font-weight:600}
h1{font-weight:700}
.k::before{content:"";display:inline-block;width:12px;height:12px;margin:0 8px -1px 0;background:var(--acc);clip-path:polygon(50% 0,100% 50%,50% 100%,0 50%)}
.ven,.chap,.vt,form{border-left:4px solid var(--acc)}
section:nth-of-type(odd){background:linear-gradient(180deg,var(--bg),color-mix(in srgb,var(--sand) 55%,var(--bg)))}
@media(prefers-reduced-motion:reduce){.picado .row{animation:none}}
""",
  hero_art="""<div class="picado" aria-hidden="true"><svg viewBox="0 0 1200 500" preserveAspectRatio="xMidYMin slice">
 <defs><pattern id="pp" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="12" cy="12" r="4" fill="var(--bg)"/><rect x="0" y="0" width="6" height="6" fill="var(--bg)" opacity=".8"/></pattern></defs>
 <g class="row">
  <path d="M0 30 Q 600 90 1200 30" fill="none" stroke="var(--ink)" stroke-width="1.5" opacity=".5"/>
  <g fill="var(--acc)" opacity=".9">
   <path d="M40 34 h110 v70 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 z"/>
   <path d="M330 56 h110 v70 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 z" opacity=".75"/>
   <path d="M620 74 h110 v70 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 z"/>
   <path d="M900 56 h110 v70 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 z" opacity=".75"/>
  </g>
  <g fill="url(#pp)"><rect x="40" y="34" width="110" height="70"/><rect x="330" y="56" width="110" height="70"/><rect x="620" y="74" width="110" height="70"/><rect x="900" y="56" width="110" height="70"/></g>
 </g>
 <g class="row">
  <path d="M0 120 Q 600 180 1200 120" fill="none" stroke="var(--ink)" stroke-width="1.5" opacity=".35"/>
  <g fill="var(--ink)" opacity=".28">
   <path d="M180 126 h110 v70 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 z"/>
   <path d="M480 150 h110 v70 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 z"/>
   <path d="M770 160 h110 v70 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 z"/>
   <path d="M1050 130 h110 v70 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 l-10 12 l-10-12 z"/>
  </g>
 </g>
</svg></div>""",
 ),
}
