"""Generates the Jovi marketing site (static HTML) into the repo root.
Run:  python _src/build.py
Shared chrome (header/footer/calculator) lives here so every page matches."""
import pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLINIC = "https://www.jovihealth.clinic"
PHONE_TEXT = "(888) 457-JOVI"
PHONE_TEL = "tel:18884575684"
# TODO: replace with the real store listings once the app is live.
APP_STORE = "#get-the-app"
PLAY_STORE = "#get-the-app"
YEAR = datetime.date.today().year

I = {  # inline SVG icons (24px, stroke)
    "check": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>',
    "shield": '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    "phone": '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="2" width="14" height="20" rx="2"/><path d="M12 18h.01"/></svg>',
    "receipt": '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 2v20l3-2 3 2 3-2 3 2 3-2V2l-3 2-3-2-3 2-3-2z"/><path d="M8 8h8M8 12h8M8 16h5"/></svg>',
    "pill": '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m10.5 20.5 10-10a4.95 4.95 0 1 0-7-7l-10 10a4.95 4.95 0 1 0 7 7z"/><path d="m8.5 8.5 7 7"/></svg>',
    "bolt": '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/></svg>',
    "folder": '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>',
    "family": '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    "paw": '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="4" r="2"/><circle cx="18" cy="8" r="2"/><circle cx="20" cy="16" r="2"/><path d="M9 10a5 5 0 0 1 5 5v3.5a3.5 3.5 0 0 1-6.84 1.045Q6.52 17.48 4.46 16.84A3.5 3.5 0 0 1 5.5 10z"/></svg>',
    "heart": '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7z"/></svg>',
    "card": '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20"/></svg>',
    "bell": '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>',
    "map": '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z"/><circle cx="12" cy="10" r="3"/></svg>',
    "chat": '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
    "info": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>',
    "menu": '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16"/></svg>',
    "apple": '<svg width="26" height="26" viewBox="0 0 24 24" fill="currentColor"><path d="M16.365 1.43c0 1.14-.417 2.1-1.25 2.88-.94.93-2.05 1.46-3.24 1.36a3.3 3.3 0 0 1-.03-.4c0-1.1.48-2.27 1.33-3.12.42-.44.96-.8 1.6-1.09.65-.28 1.26-.44 1.84-.47.03.28.03.55.03.84h-.28zm3.88 16.84c-.53 1.22-.78 1.77-1.46 2.85-.95 1.51-2.28 3.4-3.94 3.41-1.47.01-1.85-.96-3.85-.95-2 .01-2.42.97-3.9.95-1.66-.01-2.92-1.71-3.87-3.22C.53 17.45-.7 12.1 1.5 8.58c1.06-1.7 2.74-2.76 4.32-2.76 1.6 0 2.61.96 3.94.96 1.29 0 2.07-.96 3.93-.96 1.4 0 2.89.77 3.95 2.09-3.47 1.9-2.91 6.86.6 8.36z"/></svg>',
    "play": '<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M3 2.5v19l10.5-9.5z" opacity=".9"/><path d="M13.5 12 3 21.5l12.7-7.2z" opacity=".7"/><path d="M13.5 12 3 2.5l12.7 7.2z" opacity=".8"/><path d="m15.7 9.7 4.6 2.3-4.6 2.3L13.5 12z"/></svg>',
    "ig": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="20" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor"/></svg>',
    "fb": '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M14 8h3V4h-3c-2.8 0-4 1.8-4 4v2H7v4h3v6h4v-6h3l1-4h-4V8.6c0-.4.2-.6.6-.6z"/></svg>',
    "tt": '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M16.5 3c.4 2.3 1.9 3.8 4 4v3.3c-1.5 0-2.9-.5-4-1.3v6.4a5.7 5.7 0 1 1-5.7-5.7c.3 0 .6 0 .9.1v3.4a2.4 2.4 0 1 0 1.5 2.2V3h3.3z"/></svg>',
}

NAV = [("How it works", "/how-it-works"), ("Plans & pricing", "/plans"), ("Pets", "/pets"),
       ("Clinics", CLINIC), ("About", "/about"), ("FAQ", "/faq")]


def head(title, desc, path):
    canon = "https://www.jovihealth.com" + ("" if path == "/" else path)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canon}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:image" content="https://www.jovihealth.com/assets/img/lobby.webp">
<meta name="theme-color" content="#0B1426">
<link rel="icon" href="/assets/img/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700;800&family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/css/site.css">
</head>
<body>
<header class="hdr">
  <div class="wrap">
    <a class="brand" href="/" aria-label="Jovi home"><img src="/assets/img/jovi-logo-white.png" alt="Jovi"></a>
    <button class="nav-toggle" aria-label="Menu" aria-expanded="false">{I['menu']}</button>
    <nav class="nav" aria-label="Main">
      {''.join(f'<a href="{h}"{" target=_blank rel=noopener" if h.startswith("http") else ""}>{t}</a>' for t, h in NAV)}
      <a class="btn btn-primary btn-sm" href="/plans#pricing">Become a member</a>
    </nav>
  </div>
</header>
<main>
"""


FOOT = f"""
</main>
<footer class="ftr">
  <div class="wrap">
    <div class="ftr-grid">
      <div>
        <a class="brand" href="/"><img src="/assets/img/jovi-logo-white.png" alt="Jovi"></a>
        <p>A healthcare membership that's better than insurance. One monthly fee, any provider, $0 co-pays at Jovi Clinics, and coverage for your whole family, pets included.</p>
        <div class="social">
          <a href="https://www.instagram.com/jovi.health" target="_blank" rel="noopener" aria-label="Instagram">{I['ig']}</a>
          <a href="https://www.facebook.com/jovi.health" target="_blank" rel="noopener" aria-label="Facebook">{I['fb']}</a>
          <a href="https://www.tiktok.com/@jovi.health" target="_blank" rel="noopener" aria-label="TikTok">{I['tt']}</a>
        </div>
      </div>
      <div>
        <h5>Jovi</h5>
        <ul>
          <li><a href="/how-it-works">How it works</a></li>
          <li><a href="/plans">Plans &amp; pricing</a></li>
          <li><a href="/pets">Jovi Pets</a></li>
          <li><a href="/about">About Jovi</a></li>
          <li><a href="/faq">FAQ</a></li>
          <li><a href="{CLINIC}" target="_blank" rel="noopener">Jovi Clinics</a></li>
        </ul>
      </div>
      <div>
        <h5>Policies</h5>
        <ul>
          <li><a href="{CLINIC}/privacy-policy">Privacy Policy</a></li>
          <li><a href="{CLINIC}/terms-of-service">Terms of Service</a></li>
          <li><a href="{CLINIC}/membership-agreement">Membership Agreement</a></li>
          <li><a href="{CLINIC}/legal-and-compliance">Legal &amp; Compliance</a></li>
          <li><a href="{CLINIC}/non-discrimination-notice">Non-Discrimination Notice</a></li>
          <li><a href="{CLINIC}/accessibility-statement">Accessibility</a></li>
        </ul>
      </div>
      <div>
        <h5>Member support</h5>
        <p style="margin-top:0">Let's talk.</p>
        <a class="tel" href="{PHONE_TEL}">{PHONE_TEXT}</a>
        <p>Currently available in Arizona, Florida &amp; Texas.</p>
      </div>
    </div>
    <div class="ftr-bottom">
      <div class="legal">Jovi is a healthcare membership, not health insurance. Membership does not satisfy any individual mandate. Coverage, eligibility, and final pricing are confirmed at signup. Clinic images are artist renderings of upcoming Jovi Clinics.</div>
      <div>© {YEAR} Jovi Health LLC. All rights reserved.</div>
    </div>
  </div>
</footer>
<script src="/assets/js/site.js" defer></script>
<script src="/assets/js/pricing.js" defer></script>
</body>
</html>
"""


def calculator(compact=False):
    lead = ("" if compact else "")
    return f"""
<section class="section section--ivory" id="pricing">
  <div class="orb orb--teal br"></div>
  <div class="wrap">
    <div class="sec-head reveal">
      <span class="eyebrow"><span class="dot"></span> Transparent pricing</span>
      <h2>See what your membership would cost</h2>
      <p>Adjust the details below for an instant estimate. No signup, no email required. This is the same math the Jovi app uses at checkout.</p>
    </div>
    <div class="quote-grid">
      <div class="q-panel reveal-left">
        <div class="q-group">
          <h4>About you</h4>
          <div class="q-row">
            <div class="q-label">Your age</div>
            <div class="q-slider"><input type="range" id="primaryAge" min="18" max="75" value="30" aria-label="Your age"><span class="q-val" id="primaryAgeV">30</span></div>
          </div>
          <div class="q-row">
            <div class="q-label">Tobacco or marijuana use<small>15% surcharge on your premium</small></div>
            <div class="q-toggle" id="tgTobacco" role="switch" aria-checked="false" tabindex="0" aria-label="Tobacco or marijuana use"><span class="q-switch"></span></div>
          </div>
        </div>
        <div class="q-group">
          <h4>Your household</h4>
          <div class="q-row"><div class="q-label">Add spouse</div><div class="q-toggle" id="tgSpouse" role="switch" aria-checked="false" tabindex="0" aria-label="Add spouse"><span class="q-switch"></span></div></div>
          <div class="q-row hidden" id="spouseAgeRow"><div class="q-label">Spouse age</div><div class="q-slider"><input type="range" id="spouseAge" min="18" max="75" value="30" aria-label="Spouse age"><span class="q-val" id="spouseAgeV">30</span></div></div>
          <div class="q-row"><div class="q-label">Dependents<small>Children under 26</small></div><div class="stepper" data-stepper="dep"><button type="button" data-d="-1" aria-label="Fewer dependents">−</button><span class="sv" id="depV">0</span><button type="button" data-d="1" aria-label="More dependents">+</button></div></div>
          <div class="age-list hidden" id="depAges"></div>
          <div class="q-row"><div class="q-label">Pets<small>Dogs &amp; cats, 8 months to 20 years</small></div><div class="stepper" data-stepper="pet"><button type="button" data-d="-1" aria-label="Fewer pets">−</button><span class="sv" id="petV">0</span><button type="button" data-d="1" aria-label="More pets">+</button></div></div>
          <div class="age-list hidden" id="petAges"></div>
        </div>
        <div class="q-group">
          <h4>Coverage add-ons</h4>
          <div class="q-row"><div class="q-label">Dental coverage<small>+$35/mo per person</small></div><div class="q-toggle" id="tgDental" role="switch" aria-checked="false" tabindex="0" aria-label="Dental coverage"><span class="q-switch"></span></div></div>
          <div class="q-row"><div class="q-label">Vision coverage<small>+$15/mo per person</small></div><div class="q-toggle" id="tgVision" role="switch" aria-checked="false" tabindex="0" aria-label="Vision coverage"><span class="q-switch"></span></div></div>
        </div>
      </div>
      <div class="q-result reveal-right">
        <div class="rlabel">Your estimated monthly cost</div>
        <div class="q-total"><span class="cur">$</span><span id="qTotal">200</span><span class="per">/mo</span></div>
        <div class="q-break" id="qBreak"></div>
        <div class="q-div"></div>
        <div class="q-line"><span>Your deductible</span><b id="qDed">$2,000</b></div>
        <div class="q-meta"><span class="q-tag" id="qPlan">Individual plan</span><span class="q-tag hidden" id="qPetTag">Pets · 90% reimbursed · $500 deductible</span><span class="q-tag" id="qPass">Jovi Pass · $49 per priority visit</span></div>
        <div class="q-cta"><a class="btn btn-mint" href="#get-the-app">Become a member</a></div>
        <div class="q-note">Estimate only. Coverage, eligibility, and final pricing are confirmed at signup in the Jovi app. Currently available in AZ, FL &amp; TX.</div>
      </div>
    </div>
  </div>
</section>
"""


def app_cta():
    return f"""
<section class="section section--dark section--tight" id="get-the-app">
  <div class="wrap">
    <div class="app-cta reveal">
      <div>
        <span class="eyebrow"><span class="dot"></span> Get the app</span>
        <h2>Your membership lives in the Jovi app</h2>
        <p>Join in minutes, request care, file a claim with a photo, refill prescriptions, manage your family and pets, and show your digital membership card at any Jovi Clinic.</p>
        <div class="stores">
          <a class="store" href="{APP_STORE}" aria-label="Download on the App Store">{I['apple']}<span><small>Download on the</small><b>App Store</b></span></a>
          <a class="store" href="{PLAY_STORE}" aria-label="Get it on Google Play">{I['play']}<span><small>Get it on</small><b>Google Play</b></span></a>
        </div>
        <p class="small" style="margin-top:16px">Questions first? Call <a href="{PHONE_TEL}" class="lnk">{PHONE_TEXT}</a>.</p>
      </div>
      <div class="media"><img src="/assets/img/exam-room-3.webp" alt="A Jovi Clinic exam room" loading="lazy" width="1000" height="560"></div>
    </div>
  </div>
</section>
"""


def testimonials():
    qs = [
        ("I used to dread the doctor because of the cost and hassle. With Jovi I get direct access to providers without the insurance middleman, I know exactly what I pay each month, and the care is outstanding. I only wish I'd signed up sooner.", "E", "Emily T.", "Phoenix, AZ"),
        ("I used to pay outrageous premiums only to get hit with high deductibles and surprise bills. With Jovi I get quality care for a flat monthly fee. No co-pays, no hidden costs. It's transparent, affordable, and finally puts me in control.", "M", "Michael R.", "Tampa, FL"),
        ("Insurance was always frustrating. Waiting for approvals, dealing with denied claims, never knowing what I'd pay. Since switching to Jovi I have peace of mind. One predictable monthly fee, no networks, no referrals, no surprise bills.", "J", "James R.", "Austin, TX"),
    ]
    cards = "".join(f'<div class="quote reveal"><div class="mark">“</div><p>{q}</p><div class="who"><div class="av">{a}</div><div><b>{n}</b><span>{c}</span></div></div></div>' for q, a, n, c in qs)
    return f"""
<section class="section section--white">
  <div class="orb orb--coral tl"></div>
  <div class="wrap">
    <div class="sec-head reveal"><span class="eyebrow eyebrow--coral"><span class="dot"></span> Member love</span><h2>Loved by members across Arizona, Florida &amp; Texas</h2></div>
    <div class="quotes">{cards}</div>
  </div>
</section>
"""


FAQ_ITEMS = [
    ("Is Jovi insurance?", "No. Jovi is a healthcare membership, not health insurance. It gives you affordable, transparent access to care, including $0 co-pay visits at Jovi Clinics, without the complexity of traditional insurance. It does not satisfy any individual coverage mandate."),
    ("How is Jovi different from traditional health insurance?", "Instead of in-network versus out-of-network providers, pre-authorizations, and hidden fees, you pay one flat monthly fee and get reimbursed for out-of-pocket medical expenses through the Jovi app. You choose your own providers and you always know the cost up front."),
    ("How much can I save?", "Members save up to 70% compared to traditional insurance billing. We pass those savings directly to you."),
    ("How does reimbursement work?", "After a visit or a pharmacy pickup, upload the receipt in the Jovi app and we reimburse you directly. If you can't pay up front, upload the bill instead and we pay your doctor or pharmacy directly."),
    ("How does the deductible work?", "Your deductible is set by age: $1,500 through age 26, $2,000 through 45, $2,500 through 60, and $3,000 after that. It is designed to be reached quickly, and the app shows your progress on a status bar. Once it's met, Jovi covers your eligible expenses with no surprises."),
    ("Do I have to use specific doctors or hospitals?", "No. There are no network restrictions. See any doctor, specialist, pharmacy, or hospital you want. If you visit a Jovi Clinic, you get $0 co-pays, little to no wait, complimentary refreshments, and a handful of included services."),
    ("What types of care can I get?", "In-person visits at Jovi Clinics, telehealth consultations from home, prescription refills sent to any pharmacy, labs, IV therapy, vitamin shots, red light therapy, and more. Request care any time from the app."),
    ("Can I add dental and vision?", "Yes. Dental is $35 per person per month and vision is $15 per person per month, added to any plan."),
    ("What is Jovi Pass?", "Jovi Pass is a $49 one-time priority add-on for a single visit. It moves your appointment to the front of the line with an estimated wait of 0 to 5 minutes. It is optional and non-refundable once used."),
    ("Can I cover my pets?", "Yes. Dogs and cats from 8 months to 20 years old can be added to your plan. Pet coverage starts at $60 per month, includes accident and illness, reimburses 90% after a $500 deductible that is separate from your human plan, and comes with vet visits, vaccination tracking, medication reminders, and pet claims in the app."),
    ("How long does reimbursement take?", "Upload the receipt in the app and we process reimbursement promptly, either to you or straight to your provider."),
    ("Is there a limit on claims?", "No. Submit a claim whenever you receive care or pick up a prescription."),
    ("Can I cancel?", "Yes, from the app at any time. Your coverage continues until the end of your current billing period and nothing is charged after that."),
    ("Where is Jovi available?", "Jovi is currently available in Arizona, Florida, and Texas, with Jovi Clinics opening across those states as our community grows."),
]


def faq(items, heading="Good to know", sub="Jovi questions, answered", link=True):
    body = "".join(f'<details><summary>{q}</summary><div class="a">{a}</div></details>' for q, a in items)
    more = '<p style="text-align:center;margin-top:26px"><a class="btn btn-ghost" href="/faq">See all questions</a></p>' if link else ""
    return f"""
<section class="section section--ivory" id="faq">
  <div class="wrap">
    <div class="sec-head reveal"><span class="eyebrow"><span class="dot"></span> {heading}</span><h2>{sub}</h2></div>
    <div class="faq reveal">{body}</div>
    {more}
  </div>
</section>
"""


def li(b, rest):
    return f'<li>{I["check"]}<span><b>{b}</b> {rest}</span></li>'


# ─────────────────────────── HOME ───────────────────────────
HOME = head("Jovi — Healthcare Membership That's Better Than Insurance",
            "One simple monthly membership. See any doctor, get reimbursed in the app, $0 co-pays at Jovi Clinics, and coverage for your family and pets. Available in AZ, FL and TX.", "/") + f"""
<section class="hero hero--full">
  <img class="hero-bg" src="/assets/img/lobby.webp" alt="" width="2000" height="1116" fetchpriority="high">
  <div class="hero-shade"></div>
  <div class="wrap">
    <div class="hero-grid">
      <div class="reveal-left">
        <span class="eyebrow"><span class="dot"></span> Now in Arizona · Florida · Texas</span>
        <h1>Healthcare that's <em class="accent">better</em> than insurance.</h1>
        <p class="sub">One simple monthly fee. See any doctor you like and get reimbursed in the app, or walk into a Jovi Clinic with $0 co-pays. Your family and your pets, all on one plan.</p>
        <div class="cta">
          <a class="btn btn-primary" href="/plans#pricing">See plans &amp; pricing</a>
          <a class="btn btn-ghost" href="/how-it-works">How it works</a>
        </div>
        <div class="trust">
          <span>{I['check']} No networks</span><span>{I['check']} No referrals</span><span>{I['check']} No surprise bills</span><span>{I['check']} Cancel any time</span>
        </div>
      </div>
      <div class="hero-aside reveal-right">
        <div class="hero-card"><div class="ico">{I['bolt']}</div><div><b>$0 co-pay at Jovi Clinics</b><span>Plus labs, IV therapy and wellness shots included</span></div></div>
        <div class="hero-card"><div class="ico coral">{I['receipt']}</div><div><b>See any doctor</b><span>Snap the receipt, get reimbursed in the app</span></div></div>
        <div class="hero-card"><div class="ico gold">{I['paw']}</div><div><b>Pets on the same plan</b><span>90% back after a $500 deductible</span></div></div>
      </div>
    </div>
  </div>
</section>

<section class="section section--white section--tight">
  <div class="wrap">
    <div class="stats reveal">
      <div class="stat"><b>Up to 70%</b><span>Saved on care versus traditional insurance billing</span></div>
      <div class="stat"><b>$0</b><span>Co-pays at Jovi Clinics, with select generic prescriptions included</span></div>
      <div class="stat"><b class="coral">90%</b><span>Reimbursed on pet care after a $500 deductible</span></div>
      <div class="stat"><b>1 fee</b><span>One predictable monthly price for you, your family, and your pets</span></div>
    </div>
  </div>
</section>

<section class="section section--sand">
  <div class="wrap">
    <div class="sec-head reveal"><span class="eyebrow"><span class="dot"></span> Simple by design</span><h2>How Jovi works</h2><p>No insurance cards, no guessing what you'll owe. Three steps.</p></div>
    <div class="steps">
      <div class="step reveal"><div class="num">1</div><h3>Join in minutes</h3><p>Download the app, add your family and pets, pick dental or vision if you want them, and see your exact monthly price before you pay.</p></div>
      <div class="step reveal"><div class="num">2</div><h3>Get care anywhere</h3><p>Walk into a Jovi Clinic with $0 co-pays, book telehealth from your couch, or keep seeing your own doctor. No networks, no referrals.</p></div>
      <div class="step reveal"><div class="num">3</div><h3>Get reimbursed in the app</h3><p>Paid out of pocket somewhere else? Snap the receipt and we reimburse you, or upload the bill and we pay the provider directly.</p></div>
    </div>
    <p style="text-align:center;margin-top:34px"><a class="btn btn-ghost" href="/how-it-works">See the full walkthrough</a></p>
  </div>
</section>

<section class="section section--white">
  <div class="orb orb--mint br"></div>
  <div class="wrap">
    <div class="sec-head reveal"><span class="eyebrow"><span class="dot"></span> What's in the membership</span><h2>Everything, in one app</h2><p>Jovi was built in your pocket first. Every part of your care lives in one place.</p></div>
    <div class="grid-3">
      <div class="card reveal"><div class="ico">{I['phone']}</div><h3>Request care</h3><p>Book a clinic visit or telehealth in a few taps, pick a time, and track it. Reschedule from the app.</p></div>
      <div class="card reveal"><div class="ico coral">{I['receipt']}</div><h3>File a claim</h3><p>Photograph a receipt and get reimbursed, or have Jovi pay the provider. Track every claim's status.</p></div>
      <div class="card reveal"><div class="ico">{I['pill']}</div><h3>Refills &amp; pharmacies</h3><p>Request refills, send them to any pharmacy near you, see hours, and compare GoodRx prices.</p></div>
      <div class="card reveal"><div class="ico gold">{I['bolt']}</div><h3>Jovi Pass</h3><p>Need to be seen now? A $49 one-time Jovi Pass moves you to the front of the line with a 0 to 5 minute wait.</p></div>
      <div class="card reveal"><div class="ico">{I['folder']}</div><h3>Care records</h3><p>Visits, prescriptions, vaccinations, vitals, and lab results in one timeline. Export everything as a PDF.</p></div>
      <div class="card reveal"><div class="ico coral">{I['family']}</div><h3>Family coverage</h3><p>Add a spouse and dependents, manage everyone's care, and keep one bill.</p></div>
      <div class="card reveal"><div class="ico">{I['paw']}</div><h3>Jovi Pets</h3><p>Dogs and cats on the same plan: vet visits, vaccinations, medication reminders, weight alerts, and pet claims.</p><a class="tag" href="/pets">Learn about Jovi Pets</a></div>
      <div class="card reveal"><div class="ico gold">{I['heart']}</div><h3>Wellness built in</h3><p>Guided runs with GPS, meditation audio, a symptom checker, drug interaction checks, and vitals tracking.</p></div>
      <div class="card reveal"><div class="ico">{I['card']}</div><h3>Digital membership card</h3><p>Show it at any Jovi Clinic. No insurance card, no paperwork, no surprise bill afterwards.</p></div>
    </div>
  </div>
</section>

<section class="section section--ivory">
  <div class="wrap">
    <div class="split">
      <div class="reveal-left">
        <span class="eyebrow"><span class="dot"></span> Jovi Clinics</span>
        <h2>Walk into ours, or keep your own doctor</h2>
        <p>Jovi Clinics are the in-person side of your membership. Calm, modern spaces where members pay $0 co-pays and get labs, IV therapy, vitamin shots, body composition scans, and red light therapy included.</p>
        <ul class="checks">
          {li('$0 co-pay', 'for members at every clinic visit')}
          {li('Included services', 'a full blood panel yearly, IV therapy and vitamin shots monthly, body composition quarterly')}
          {li('Never locked in', 'see any provider you like and get reimbursed in the app')}
          {li('Opening across', 'Arizona, Florida, and Texas')}
        </ul>
        <div class="cta" style="display:flex;gap:12px;flex-wrap:wrap;margin-top:26px"><a class="btn btn-primary" href="{CLINIC}" target="_blank" rel="noopener">Explore Jovi Clinics</a></div>
      </div>
      <div class="media reveal-right"><img src="/assets/img/clinic-exterior.webp" alt="Exterior of a Jovi Clinic" loading="lazy" width="1200" height="672"></div>
    </div>
    <div class="gallery" style="margin-top:44px">
      <figure class="reveal"><img src="/assets/img/iv-lounge.webp" alt="IV therapy lounge" loading="lazy"><figcaption>IV therapy lounge</figcaption></figure>
      <figure class="reveal"><img src="/assets/img/exam-room-1.webp" alt="Exam room" loading="lazy"><figcaption>Modern exam rooms</figcaption></figure>
      <figure class="reveal"><img src="/assets/img/kids-corner.webp" alt="Family and kids corner" loading="lazy"><figcaption>Family &amp; kids corner</figcaption></figure>
    </div>
    <p class="small muted" style="text-align:center;margin-top:14px">Images are artist renderings of our upcoming Jovi Clinics.</p>
  </div>
</section>

<section class="section section--white">
  <div class="wrap">
    <div class="split rev">
      <div class="reveal-right">
        <span class="eyebrow eyebrow--coral"><span class="dot"></span> Jovi Pets</span>
        <h2>Your pets are family. Now they're on the plan.</h2>
        <p>Add dogs and cats to your membership for accident and illness coverage with 90% reimbursement after a $500 deductible that's separate from your own. Manage vet visits, vaccinations, medications, and claims in the same app.</p>
        <ul class="checks">
          {li('From $60/mo', 'for a pet under a year old, plus $7 per year of age')}
          {li('Any vet', 'pay at your vet, snap the receipt, get 90% back')}
          {li('Reminders', 'for boosters, medications, and weight alerts')}
        </ul>
        <div style="margin-top:26px"><a class="btn btn-coral" href="/pets">See pet coverage</a></div>
      </div>
      <div class="media reveal-left"><img src="/assets/img/jovi-pets-lobby.webp" alt="Jovi Pets lobby" loading="lazy" width="1200" height="672"></div>
    </div>
  </div>
</section>

<section class="section section--dark">
  <div class="wrap">
    <div class="sec-head reveal"><span class="eyebrow"><span class="dot"></span> The difference</span><h2>Jovi vs. the way it's always been</h2></div>
    <div class="cmp-wrap reveal">
    <table class="cmp">
      <thead><tr><th></th><th class="jovi">Jovi</th><th>Traditional insurance</th><th>Urgent care</th></tr></thead>
      <tbody>
        <tr><td>Predictable monthly cost</td><td class="yes">✓</td><td class="mid">~</td><td class="no">✕</td></tr>
        <tr><td>$0 co-pays at Jovi Clinics</td><td class="yes">✓</td><td class="no">✕</td><td class="no">✕</td></tr>
        <tr><td>No surprise bills</td><td class="yes">✓</td><td class="no">✕</td><td class="no">✕</td></tr>
        <tr><td>See any provider you like</td><td class="yes">✓</td><td class="mid">~</td><td class="yes">✓</td></tr>
        <tr><td>Walk-in &amp; same-day care</td><td class="yes">✓</td><td class="no">✕</td><td class="yes">✓</td></tr>
        <tr><td>Labs, IV therapy &amp; wellness included</td><td class="yes">✓</td><td class="no">✕</td><td class="no">✕</td></tr>
        <tr><td>Pets on the same plan</td><td class="yes">✓</td><td class="no">✕</td><td class="no">✕</td></tr>
        <tr><td>A care team that knows you</td><td class="yes">✓</td><td class="mid">~</td><td class="no">✕</td></tr>
      </tbody>
    </table>
    </div>
  </div>
</section>

{calculator()}
{testimonials()}
{faq(FAQ_ITEMS[:5])}
{app_cta()}
""" + FOOT

# ─────────────────────────── HOW IT WORKS ───────────────────────────
HOW = head("How Jovi Works — Join, Get Care, Get Reimbursed",
           "Join in minutes, see any doctor or walk into a Jovi Clinic, and get reimbursed in the app. A plain-English walkthrough of the Jovi membership.", "/how-it-works") + f"""
<section class="section section--ivory page-hero">
  <div class="orb orb--mint tl"></div>
  <div class="wrap">
    <span class="eyebrow"><span class="dot"></span> How it works</span>
    <h1>Care without the insurance middleman.</h1>
    <p>Jovi replaces networks, referrals, and mystery bills with one monthly membership, a clinic you can walk into, and an app that pays you back when you go anywhere else.</p>
  </div>
</section>

<section class="section section--white">
  <div class="wrap">
    <div class="steps">
      <div class="step reveal"><div class="num">1</div><h3>Join in minutes</h3><p>Download the Jovi app and answer a few questions: your birthdate, your spouse and dependents, your pets, and whether you want dental or vision. The app shows your exact monthly price before you pay. Membership starts the same day.</p></div>
      <div class="step reveal"><div class="num">2</div><h3>Get care your way</h3><p>Request a visit from the app and choose a Jovi Clinic or telehealth. Prefer your own doctor? Go. There are no networks and no referrals, so nothing needs approval first.</p></div>
      <div class="step reveal"><div class="num">3</div><h3>Pay nothing, or get paid back</h3><p>At a Jovi Clinic you pay $0. Anywhere else, snap the receipt in the app and we reimburse you, or upload the bill and we pay the provider directly.</p></div>
    </div>
  </div>
</section>

<section class="section section--sand">
  <div class="wrap">
    <div class="split">
      <div class="reveal-left">
        <span class="eyebrow"><span class="dot"></span> Two ways to be seen</span>
        <h2>$0 at a Jovi Clinic. Reimbursed everywhere else.</h2>
        <p><b>Visit a Jovi Clinic.</b> Walk in for primary care, urgent visits, labs, IV therapy, red light therapy, and more with $0 co-pays. Book from the app, or check in ahead and we'll text you when we're ready.</p>
        <p><b>See any provider.</b> Pay out of pocket at your own doctor, pharmacy, or hospital, then file a claim in the app. Members save up to 70% on care. If you can't pay up front, upload the bill and we settle it with the provider.</p>
        <ul class="checks">
          {li('Deductible by age.', '$1,500 through 26, $2,000 through 45, $2,500 through 60, $3,000 after. The app shows your progress.')}
          {li('Every claim tracked.', 'Submitted, under review, approved, paid. You get a notification at each step.')}
        </ul>
      </div>
      <div class="media reveal-right"><img src="/assets/img/exam-room-2.webp" alt="A Jovi Clinic exam room" loading="lazy" width="1000" height="560"></div>
    </div>
  </div>
</section>

<section class="section section--white">
  <div class="orb orb--coral br"></div>
  <div class="wrap">
    <div class="split rev">
      <div class="reveal-right">
        <span class="eyebrow eyebrow--coral"><span class="dot"></span> Jovi Pass</span>
        <h2>Need to be seen now? Skip the line.</h2>
        <p>Jovi Pass is a $49 one-time add-on for a single visit that puts you at the front of the queue with an estimated wait of 0 to 5 minutes instead of the usual 15 to 60. Add it when you request care. It's optional, and it's non-refundable once your priority slot is booked.</p>
        <ul class="plan-list" style="margin-top:20px">
          <li><span>Standard visit wait</span><b>15 to 60 min</b></li>
          <li><span>Jovi Pass wait</span><b>0 to 5 min</b></li>
          <li><span>Price</span><b>$49 one-time</b></li>
        </ul>
      </div>
      <div class="media reveal-left"><img src="/assets/img/hallway.webp" alt="A Jovi Clinic hallway" loading="lazy" width="1000" height="560"></div>
    </div>
  </div>
</section>

<section class="section section--ivory">
  <div class="wrap">
    <div class="sec-head reveal"><span class="eyebrow"><span class="dot"></span> Day to day</span><h2>What you'll actually use</h2></div>
    <div class="grid-3">
      <div class="card reveal"><div class="ico">{I['pill']}</div><h3>Prescriptions</h3><p>Request refills, choose any pharmacy near you with live hours, and check GoodRx cash prices before pickup.</p></div>
      <div class="card reveal"><div class="ico">{I['bell']}</div><h3>Reminders that matter</h3><p>Appointment reminders a day and an hour ahead, in your time zone. A heads-up three days before each payment. Booster and refill alerts.</p></div>
      <div class="card reveal"><div class="ico coral">{I['chat']}</div><h3>A real care team</h3><p>Message our team from the app. Care from licensed providers, never a bot or a call center.</p></div>
      <div class="card reveal"><div class="ico gold">{I['folder']}</div><h3>Your records, your way</h3><p>Visits, prescriptions, vaccinations, vitals, and pet records in one timeline. Export the whole thing as a PDF whenever you like.</p></div>
      <div class="card reveal"><div class="ico">{I['family']}</div><h3>Family in one place</h3><p>Add or update a spouse and dependents, book care for any of them, and keep one bill.</p></div>
      <div class="card reveal"><div class="ico coral">{I['shield']}</div><h3>Private by default</h3><p>Your health information is encrypted, never sold, and deletable from the app at any time.</p></div>
    </div>
  </div>
</section>
{faq([FAQ_ITEMS[0], FAQ_ITEMS[3], FAQ_ITEMS[4], FAQ_ITEMS[5], FAQ_ITEMS[12]])}
{app_cta()}
""" + FOOT

# ─────────────────────────── PLANS ───────────────────────────
PLANS = head("Jovi Plans & Pricing — Instant Membership Quote",
             "Transparent membership pricing by age, with dental, vision, family, and pet add-ons. Get an instant estimate with the same math the Jovi app uses.", "/plans") + f"""
<section class="section section--ivory page-hero">
  <div class="orb orb--mint tl"></div>
  <div class="wrap">
    <span class="eyebrow"><span class="dot"></span> Plans &amp; pricing</span>
    <h1>One price. No fine print.</h1>
    <p>Your membership price depends on the ages of the people and pets on your plan and the add-ons you choose. That's it. No tiers to decode and no open enrollment window.</p>
  </div>
</section>

{calculator()}

<section class="section section--white">
  <div class="wrap">
    <div class="sec-head reveal"><span class="eyebrow"><span class="dot"></span> The math, in the open</span><h2>How your price is built</h2><p>These are the exact rates the Jovi app uses at checkout.</p></div>
    <div class="grid-2">
      <div class="card reveal">
        <div class="ico">{I['family']}</div>
        <h3>Monthly premium per person</h3>
        <ul class="plan-list" style="margin-top:14px">
          <li><span>Through age 29</span><b>$150</b></li>
          <li><span>30 to 39</span><b>$200</b></li>
          <li><span>40 to 49</span><b>$250</b></li>
          <li><span>50 to 59</span><b>$300</b></li>
          <li><span>60 and up</span><b>$350</b></li>
          <li><span>Tobacco or marijuana use (primary member)</span><b>+15%</b></li>
        </ul>
      </div>
      <div class="card reveal">
        <div class="ico">{I['shield']}</div>
        <h3>Annual deductible per person</h3>
        <ul class="plan-list" style="margin-top:14px">
          <li><span>Through age 26</span><b>$1,500</b></li>
          <li><span>27 to 45</span><b>$2,000</b></li>
          <li><span>46 to 60</span><b>$2,500</b></li>
          <li><span>61 and up</span><b>$3,000</b></li>
        </ul>
        <p>Track your progress in the app. Once it's met, Jovi covers eligible expenses.</p>
      </div>
      <div class="card reveal">
        <div class="ico gold">{I['heart']}</div>
        <h3>Add-ons</h3>
        <ul class="plan-list" style="margin-top:14px">
          <li><span>Dental coverage</span><b>+$35 / person / mo</b></li>
          <li><span>Vision coverage</span><b>+$15 / person / mo</b></li>
          <li><span>Jovi Pass priority visit</span><b>$49 one-time</b></li>
        </ul>
        <p>Add or remove dental and vision from the app whenever you like.</p>
      </div>
      <div class="card reveal">
        <div class="ico coral">{I['paw']}</div>
        <h3>Pets</h3>
        <ul class="plan-list" style="margin-top:14px">
          <li><span>8 to 11 months old</span><b>$60 / mo</b></li>
          <li><span>1 year and older</span><b>$60 + $7 per year of age</b></li>
          <li><span>Deductible (separate from yours)</span><b>$500</b></li>
          <li><span>Reimbursement</span><b>90%</b></li>
        </ul>
        <p>Dogs and cats up to 20 years old. <a href="/pets" class="lnk">See what's covered</a>.</p>
      </div>
    </div>
  </div>
</section>

<section class="section section--sand">
  <div class="wrap">
    <div class="sec-head reveal"><span class="eyebrow"><span class="dot"></span> Every plan includes</span><h2>What you get for the monthly fee</h2></div>
    <div class="grid-3">
      <div class="card reveal"><div class="ico">{I['bolt']}</div><h3>$0 co-pays at Jovi Clinics</h3><p>Primary and preventive care, sick and urgent visits, wellness exams, and chronic condition management. Select generic prescriptions included.</p></div>
      <div class="card reveal"><div class="ico">{I['heart']}</div><h3>Included wellness services</h3><p>A full blood panel yearly, IV therapy and a vitamin shot monthly, red light therapy monthly, body composition quarterly.</p></div>
      <div class="card reveal"><div class="ico coral">{I['receipt']}</div><h3>Reimbursement anywhere</h3><p>See any provider, pharmacy, or hospital and file the receipt in the app. Members save up to 70% on care.</p></div>
      <div class="card reveal"><div class="ico">{I['phone']}</div><h3>Telehealth</h3><p>Consult from home when you don't need to be seen in person.</p></div>
      <div class="card reveal"><div class="ico gold">{I['folder']}</div><h3>The Jovi app</h3><p>Care requests, claims, refills, pharmacies, records, vitals, fitness, meditation, and your digital membership card.</p></div>
      <div class="card reveal"><div class="ico">{I['family']}</div><h3>Family on one bill</h3><p>Spouse and dependents under 26 on the same membership, each priced by their own age.</p></div>
    </div>
    <div class="callout" style="margin-top:34px">{I['info']}<div><b>Membership, not insurance.</b> Jovi is a healthcare membership and does not satisfy any individual coverage mandate. Cancel from the app at any time; coverage runs to the end of the billing period and nothing is charged after. Final pricing is confirmed at signup and available in Arizona, Florida, and Texas.</div></div>
  </div>
</section>
{faq([FAQ_ITEMS[4], FAQ_ITEMS[7], FAQ_ITEMS[8], FAQ_ITEMS[9], FAQ_ITEMS[12]])}
{app_cta()}
""" + FOOT

# ─────────────────────────── PETS ───────────────────────────
PETS = head("Jovi Pets — Pet Coverage on Your Jovi Membership",
            "Add dogs and cats to your Jovi membership. Accident and illness coverage, 90% reimbursement after a $500 deductible, and vet visits, vaccinations, and medications managed in the app.", "/pets") + f"""
<section class="hero hero--full">
  <img class="hero-bg" src="/assets/img/jovi-pets-lobby.webp" alt="" width="2000" height="1116" fetchpriority="high">
  <div class="hero-shade"></div>
  <div class="wrap">
    <div class="hero-grid">
      <div class="reveal-left">
        <span class="eyebrow eyebrow--coral"><span class="dot"></span> Jovi Pets</span>
        <h1>The same membership, <em class="accent-coral">for the whole pack.</em></h1>
        <p class="sub">Add dogs and cats to your Jovi plan for accident and illness coverage at any vet, with 90% reimbursed after a $500 deductible that never touches your own.</p>
        <div class="cta"><a class="btn btn-coral" href="/plans#pricing">Price a pet</a><a class="btn btn-ghost" href="#covered">What's covered</a></div>
      </div>
      <div class="hero-aside reveal-right">
        <div class="hero-card"><div class="ico coral">{I['paw']}</div><div><b>From $60 a month</b><span>$7 more per year of your pet's age</span></div></div>
        <div class="hero-card"><div class="ico">{I['shield']}</div><div><b>Accident + illness</b><span>Any licensed vet, 90% reimbursed</span></div></div>
      </div>
    </div>
  </div>
</section>

<section class="section section--white" id="covered">
  <div class="wrap">
    <div class="sec-head reveal"><span class="eyebrow eyebrow--coral"><span class="dot"></span> Coverage</span><h2>What's shared</h2><p>Accident and illness coverage for dogs and cats from 8 months to 20 years old.</p></div>
    <div class="grid-2">
      <div class="card reveal">
        <div class="ico coral">{I['shield']}</div>
        <h3>The plan</h3>
        <ul class="plan-list" style="margin-top:14px">
          <li><span>Coverage type</span><b>Accident + illness</b></li>
          <li><span>Reimbursement</span><b>90%</b></li>
          <li><span>Annual deductible</span><b>$500, separate from your plan</b></li>
          <li><span>Vets</span><b>Any licensed vet</b></li>
          <li><span>Eligible pets</span><b>Dogs &amp; cats, 8 mo to 20 yrs</b></li>
        </ul>
      </div>
      <div class="card reveal">
        <div class="ico coral">{I['receipt']}</div>
        <h3>Monthly price by age</h3>
        <ul class="plan-list" style="margin-top:14px">
          <li><span>8 to 11 months</span><b>$60</b></li>
          <li><span>1 year</span><b>$60</b></li>
          <li><span>3 years</span><b>$74</b></li>
          <li><span>7 years</span><b>$102</b></li>
          <li><span>12 years</span><b>$137</b></li>
        </ul>
        <p>$60 plus $7 for each year of age after the first. Multiple pets are each priced by their own age.</p>
      </div>
    </div>
  </div>
</section>

<section class="section section--sand">
  <div class="wrap">
    <div class="sec-head reveal"><span class="eyebrow eyebrow--coral"><span class="dot"></span> In the app</span><h2>Everything for your pet, next to everything for you</h2></div>
    <div class="grid-3">
      <div class="card reveal"><div class="ico coral">{I['receipt']}</div><h3>Pet claims</h3><p>Pay at the vet, photograph the invoice, and get 90% back after the deductible.</p></div>
      <div class="card reveal"><div class="ico coral">{I['folder']}</div><h3>Pet records</h3><p>Vet visits, treatments, and a full timeline per pet, including documents you upload.</p></div>
      <div class="card reveal"><div class="ico coral">{I['bell']}</div><h3>Vaccination tracking</h3><p>Boosters on a schedule with reminders 30, 7, and 0 days before they're due.</p></div>
      <div class="card reveal"><div class="ico coral">{I['pill']}</div><h3>Medication reminders</h3><p>Doses, schedules, and refills with a species-aware safety check.</p></div>
      <div class="card reveal"><div class="ico coral">{I['heart']}</div><h3>Weight alerts</h3><p>Log weights and get a nudge when your pet drifts outside a healthy range.</p></div>
      <div class="card reveal"><div class="ico coral">{I['chat']}</div><h3>Pet symptom checker</h3><p>Describe what you're noticing and get guidance on whether it can wait or needs a vet today.</p></div>
    </div>
  </div>
</section>

<section class="section section--ivory">
  <div class="wrap">
    <div class="split">
      <div class="reveal-left">
        <span class="eyebrow eyebrow--coral"><span class="dot"></span> Add a pet any time</span>
        <h2>Already a member? Add them from the app.</h2>
        <p>Open My Pets, add a profile with a photo and age, and the monthly price updates on your next bill. Pets added mid-cycle are prorated.</p>
        <div style="margin-top:26px;display:flex;gap:12px;flex-wrap:wrap"><a class="btn btn-coral" href="/plans#pricing">See your price</a><a class="btn btn-ghost" href="#get-the-app">Get the app</a></div>
      </div>
      <div class="media reveal-right"><img src="/assets/img/kids-corner.webp" alt="Family corner at a Jovi Clinic" loading="lazy" width="1000" height="560"></div>
    </div>
  </div>
</section>
{faq([FAQ_ITEMS[9], FAQ_ITEMS[3], FAQ_ITEMS[12]])}
{app_cta()}
""" + FOOT

# ─────────────────────────── ABOUT ───────────────────────────
ABOUT = head("About Jovi — Care You Can Count On, and Afford",
             "Jovi is a healthcare membership built to replace the complexity of insurance with one monthly fee, real providers, transparent pricing, and clinics that feel good to walk into.", "/about") + f"""
<section class="section section--ivory page-hero">
  <div class="orb orb--mint tl"></div>
  <div class="wrap">
    <span class="eyebrow"><span class="dot"></span> About Jovi</span>
    <h1>We think healthcare should feel good, not just be good.</h1>
    <p>Jovi started with a simple frustration: paying outrageous premiums and still not knowing what a visit would cost. So we built a membership that puts the price up front, lets you see anyone, and treats you like a person instead of a policy number.</p>
  </div>
</section>

<section class="section section--white">
  <div class="wrap">
    <div class="grid-3">
      <div class="card reveal"><div class="ico">{I['shield']}</div><h3>Transparent by design</h3><p>Clear, upfront pricing and no fine print. You always know what you pay, before you pay it.</p></div>
      <div class="card reveal"><div class="ico">{I['heart']}</div><h3>Real, licensed providers</h3><p>Care from actual medical professionals, never a bot or a call center. A care team that knows you by name.</p></div>
      <div class="card reveal"><div class="ico">{I['folder']}</div><h3>Your data stays private</h3><p>Your health information is encrypted, never sold, and you can export it or delete your account from the app at any time.</p></div>
    </div>
  </div>
</section>

<section class="section section--sand">
  <div class="wrap">
    <div class="split">
      <div class="reveal-left">
        <span class="eyebrow"><span class="dot"></span> Where we are</span>
        <h2>Arizona, Florida, and Texas first.</h2>
        <p>Jovi memberships are available across all three launch states today, and Jovi Clinics are opening in each as our community grows. Members are the first to know when a clinic opens near them.</p>
        <ul class="checks">
          {li('Arizona', 'now opening')}
          {li('Florida', 'opening soon')}
          {li('Texas', 'opening soon')}
        </ul>
        <div style="margin-top:26px"><a class="btn btn-ghost" href="{CLINIC}#locations" target="_blank" rel="noopener">Clinic locations</a></div>
      </div>
      <div class="media reveal-right"><img src="/assets/img/clinic-exterior.webp" alt="Exterior of a Jovi Clinic" loading="lazy" width="1200" height="672"></div>
    </div>
  </div>
</section>

<section class="section section--ivory">
  <div class="wrap">
    <div class="sec-head reveal"><span class="eyebrow"><span class="dot"></span> Talk to us</span><h2>Member support</h2><p>Questions about membership, a claim, or a clinic? Call or message us from the app.</p>
    <p style="margin-top:22px"><a class="btn btn-primary" href="{PHONE_TEL}">Call {PHONE_TEXT}</a></p></div>
  </div>
</section>
{app_cta()}
""" + FOOT

# ─────────────────────────── FAQ ───────────────────────────
FAQP = head("Jovi FAQ — Membership, Reimbursement, Pets and More",
            "Answers about how Jovi works: membership versus insurance, reimbursement, deductibles, providers, dental and vision, Jovi Pass, pets, and cancellation.", "/faq") + f"""
<section class="section section--ivory page-hero">
  <div class="orb orb--mint tl"></div>
  <div class="wrap">
    <span class="eyebrow"><span class="dot"></span> FAQ</span>
    <h1>Jovi questions, answered.</h1>
    <p>Can't find what you need? Call <a href="{PHONE_TEL}" class="lnk">{PHONE_TEXT}</a> or message us in the app.</p>
  </div>
</section>
{faq(FAQ_ITEMS, heading="Everything", sub="The full list", link=False)}
{app_cta()}
""" + FOOT

NOTFOUND = head("Page not found — Jovi", "That page doesn't exist.", "/404") + f"""
<section class="section section--ivory page-hero" style="min-height:60vh">
  <div class="wrap">
    <span class="eyebrow eyebrow--coral"><span class="dot"></span> 404</span>
    <h1>That page took a sick day.</h1>
    <p>Try the home page, or see plans and pricing.</p>
    <p style="margin-top:22px;display:flex;gap:12px;flex-wrap:wrap"><a class="btn btn-primary" href="/">Home</a><a class="btn btn-ghost" href="/plans">Plans &amp; pricing</a></p>
  </div>
</section>
""" + FOOT

PAGES = {"index.html": HOME, "how-it-works.html": HOW, "plans.html": PLANS, "pets.html": PETS,
         "about.html": ABOUT, "faq.html": FAQP, "404.html": NOTFOUND}

for name, html in PAGES.items():
    (ROOT / name).write_text(html, encoding="utf-8", newline="\n")
    print("wrote", name, len(html.splitlines()), "lines")
