"""themes_peony.py - JC-LAZO-WWT-0929-PEONY
The twenty-first template, built for the couple who wants the site to feel
like the bouquet: Peony. Blush ground, deep peony accent, Playfair Display
for the names, a petal-toss hero. Same bones as every other template (built
from _base.html by make_themes.py), so every day-of feature rides along.

  python wedding-websites\\make_themes.py peony
  python wedding-websites\\apply_feel.py peony
  python wedding-websites\\patch_seo.py peony
  python wedding-websites\\patch_photos_templates.py peony
  python wedding-websites\\patch_live_templates.py peony
  python wedding-websites\\patch_more_templates.py peony
"""
U = "https://images.unsplash.com/photo-"
def img(id_, w=1200, q=74):
    return f"{U}{id_}?auto=format&fit=crop&w={w}&q={q}"

PEONY = {
 "peony": dict(
  name="Peony", title="Peony — a blush & romantic wedding website template | Lazo",
  desc="A free romantic wedding website template from Lazo — blush, peony and champagne, Playfair type, with RSVPs, schedule, registry, a photo wall for guests, and a site that says We're Married after the big day.",
  fonts="family=Playfair+Display:ital,wght@0,500;0,600;1,500;1,600&family=Jost:wght@300;400;500&display=swap",
  serif='"Playfair Display",serif', display='"Playfair Display",serif', sans='"Jost",sans-serif',
  palettes={"peony":{"--bg":"#FDF7F8","--ink":"#3E2A33","--mut":"#957C86","--acc":"#C2506F","--panel":"#FFFFFF","--line":"#F3DFE5","--sand":"#F9EAEE"},
            "champagne":{"--bg":"#FCF8F2","--ink":"#3D3229","--mut":"#8F8073","--acc":"#B9924E","--panel":"#FFFFFF","--line":"#EFE3D0","--sand":"#F6ECDD"},
            "dusk":{"--bg":"#FAF7FB","--ink":"#3A2F46","--mut":"#8A7C97","--acc":"#8B62A8","--panel":"#FFFFFF","--line":"#E9DFF0","--sand":"#F1EAF6"},
            "ivory":{"--bg":"#FCFBF8","--ink":"#3B3430","--mut":"#8C8279","--acc":"#A9766A","--panel":"#FFFFFF","--line":"#EBE4DC","--sand":"#F4EEE6"}},
  hero="full", hero_img=img("1583939003579-730e3918a45a", 1900), hero_filter="saturate(1.04) brightness(.9)",
  eyebrow="Together with their families", cdlabel="days until the petals fly", n1="Clara", n2="Julian",
  where="Rosewood Hall · Charleston, South Carolina", date="2027-04-24",
  story_h="A borrowed pen, a wrong number, a very long lunch.", story_p="He asked to borrow a pen at the coffee counter and wrote his number on my cup - one digit off. I found him anyway. Four Aprils later we are getting married under the live oaks at Rosewood Hall, with everyone who ever told us it was meant to be.",
  story_img=img("1515934751635-c81c6bc9a2d8", 1000), story_cap="Four Aprils in",
  gal_h="Blush, light, the two of us.", gal=[(img("1523438885200-e635ba2c371e"), "The aisle at Rosewood"), (img("1537633552985-df8429e8048b", 900), "Where he asked"), (img("1469371670807-013ccf25f16a", 900), "Evenings like this one")],
  day_h="Vows under the oaks, dinner in the hall, dancing until the candles go.",
  sched=[("3:30 pm","Guests arrive - lemonade and a stroll through the gardens"),("4:00 pm","Ceremony under the live oaks"),("4:40 pm","Cocktails on the terrace"),("6:00 pm","Dinner in the hall"),("8:30 pm","First dance, then everyone")],
  ven=[("Ceremony","The Oak Lawn","4:00 in the afternoon","Chairs on the grass - heels beware"),("Reception","Rosewood Hall","4:40 until the last dance","Dinner, toasts and dancing under the chandeliers")],
  thanks="The petals flew right on time. Thank you for standing under the oaks with us.",
  rsvp_h="Tell us you'll be under the oaks.", rsvp_p="Kindly reply by March 20 - the kitchen needs a count before the peonies open.", yes="Joyfully accepts", no="Regretfully declines",
  song_ph="A song that gets everyone dancing (optional)", note_ph="Dietary notes, song requests, questions about the gardens…",
  reg_h="Your presence is the whole point.", reg_p="If you would like to give more, we have gathered a few things for the house on Meeting Street - and a fund for the honeymoon in Lisbon.",
  faq=[("What should I wear?","Garden formal - long dresses, light suits, soft colours. The lawn is grass, so choose heels with care."),("Is it outdoors?","The ceremony is; cocktails are on the terrace; dinner and dancing are inside the hall."),("Where should we stay?","Rooms are held at the Dewberry through March 20 under Clara and Julian.")],
  extra_css="""
h1{letter-spacing:-.02em}
h1 .amp{font-style:italic;font-weight:500}
section:nth-of-type(even){background:linear-gradient(180deg,var(--bg),color-mix(in srgb,var(--sand) 55%,var(--bg)))}
h2::after{content:"";display:block;width:56px;height:1px;margin-top:14px;background:var(--acc);opacity:.7}
.center h2::after{margin-left:auto;margin-right:auto}
.k::before{content:"";display:inline-block;width:9px;height:9px;margin:0 8px -1px 0;border-radius:50% 0 50% 50%;background:var(--acc);opacity:.75;transform:rotate(-20deg)}
.ven,.gbn,.vt,.chap,.ev,.seatc{border-radius:14px}
.gal img,.split .pimg img,.chimgs img{border-radius:12px}
form,.ocard{border-radius:16px}
button.go,.reg a.r,.gpbtn,.gbf button{border-radius:999px}
.hero-full::after{background:linear-gradient(to bottom,rgba(60,20,40,.28),rgba(60,20,40,.05) 40%,rgba(30,12,22,.86) 96%)}
""",
  hero_art="", body_extra="",
 ),
}
