"""site_facts.py - JC-LAZO-SITEFACTS-1013: what each vendor's own website says, kept as facts.

Every vendor page outside the 4 rich ones is a stub Google has declined (GSC 2026-10-08: 2,823 crawled, not
indexed). This visits each vendor's website (home plus up to four linked pages: about, services, pricing,
FAQ, the venue's spaces) and keeps FACTS, not prose: the services and styles the site lists, a starting
price only where the site prints one next to "starting at / from", years in business, venue capacity,
languages, destination work, social profiles, and the site's own meta description as a short quote. It
also flags sites that are dead, parked, or not about weddings at all (headshot studios, funeral florists).

Prose is never copied: republishing another site's text is what Google's spam policy calls scraped content,
and it would rank as a duplicate of the vendor's own site. build.py renders these facts in Lazo's words
("From their website" block + LocalBusiness JSON-LD) when LAZO_SITEFACTS=1.

    python generate\\site_facts.py --metro phoenix              # one metro
    python generate\\site_facts.py --tranche 7                  # every live metro, resumable
    python generate\\site_facts.py --metro phoenix --limit 40   # a quick sample
    python generate\\site_facts.py --metro phoenix --report     # print what was found, no crawling

Output: generate/data/site-facts/<metro>.json  {placeId: facts}. Facts younger than --max-age days (30) are
kept, so a rerun only visits new or stale sites. robots.txt is honoured; one request at a time per site.
"""
import argparse, json, os, re, sys, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib import robotparser

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from config.metros import METROS, metros_for_tranche  # noqa: E402

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

OUT_DIR = ROOT / "generate" / "data" / "site-facts"
UA = "Mozilla/5.0 (compatible; LazoBot/1.0; +https://meetlazo.com/for-vendors/)"
BOT = "LazoBot"
MAX_BYTES = 8_000_000   # JC-LAZO-SITEFACTS-1014-MORE: was 1.5MB, which cut Elementor/Wix pages off before their text
THIS_YEAR = date.today().year

# Linked pages worth a visit, in order of value. One page per group, four pages at most.
SUBPAGES = (
    ("price", ("pricing", "price", "investment", "packages", "rates", "collections")),
    ("services", ("services", "offerings", "what-we-do", "menu", "menus", "catering")),
    ("about", ("about", "our-story", "story", "meet", "who-we-are")),
    ("faq", ("faq", "faqs", "questions")),
    ("venue", ("venue", "spaces", "space", "facilities", "the-property", "weddings")),
)
SOCIAL = {"instagram.com": "Instagram", "facebook.com": "Facebook", "tiktok.com": "TikTok", "pinterest.com": "Pinterest",
          "youtube.com": "YouTube", "vimeo.com": "Vimeo"}
SOCIAL_SKIP = ("sharer", "/share", "intent/", "/p/", "/reel/", "/watch", "/embed", "/plugins", "/dialog", "/hashtag", "/explore")
PARKED = re.compile(r"domain (?:name )?(?:is |may be )?for sale|buy this domain|this domain is parked|hugedomains|"
                    r"parked free|domain has expired|website coming soon|account (?:has been )?suspended", re.I)
GENERIC_DESC = re.compile(r"just another wordpress|wix\.com|squarespace|godaddy|^home$|default description|lorem ipsum", re.I)
WEDDING = re.compile(r"\bwedd(?:ing|ings)\b|\bbrid(?:e|es|al)\b|\belop(?:e|ement|ements|ing)\b|\bnewlywed|\bnuptial|"
                     r"\bbodas?\b|\bnovias?\b|\bmatrimonio|\bquincea", re.I)
# JC-LAZO-SITEFACTS-1014: an expired vendor domain bought by a gambling/pharma spammer (40 found on 2026-10-13).
# Lazo must not link to it or quote it.
SPAM = re.compile(r"togel|gacor|maxwin|\bslot ?(?:online|88|777|thailand|dana)\b|situs (?:slot|toto|judi|resmi)|judi (?:online|bola)|"
                  r"sbobet|bandar (?:togel|toto|judi)|pragmatic ?play|link alternatif|\btoto ?(?:4d|macau|slot)\b|"
                  r"\bjackpot\b.{0,40}\bslot|\bslot\b.{0,40}\bjackpot|kasino|casino online|online casino|\bviagra\b|\bcialis\b|"
                  r"mostbet|买球|hugedomains|aged domain", re.I)

# ---- what the site says it does, per category: (label, pattern). Labels are Lazo's wording. --------------------
_SHARED = [
    ("Elopements", r"\belop(?:e|ement|ements|ing)\b"),
    ("Destination weddings", r"destination wedding"),
    ("Vow renewals", r"vow renewal"),
    ("LGBTQ+ couples", r"lgbtq|same[- ]sex (?:wedding|couple|marriage)|queer couple"),
]
SERVICES = {
    "wedding-photographers": [
        ("Engagement sessions", r"engagement (?:session|shoot|photo)"), ("Bridal portraits", r"bridal (?:portrait|session)"),
        ("Second shooter", r"second (?:shooter|photographer)"), ("Drone photos", r"\bdrone\b"),
        ("Film photography", r"\b35mm\b|medium format|film photograph|shoot(?:s|ing)? (?:on |in )?film\b"),
        ("Heirloom albums", r"heirloom album|fine[- ]art album|wedding album|\balbums\b"),
        ("Online gallery", r"online gallery|digital gallery|online proofing"), ("Photo booth", r"photo ?booth"),
        ("Rehearsal dinner coverage", r"rehearsal dinner"), ("Boudoir", r"boudoir"),
    ],
    "wedding-videographers": [
        ("Same-day edit", r"same[- ]day edit"), ("Highlight film", r"highlight (?:film|video|reel)"),
        ("Full ceremony film", r"full[- ]length|full ceremony|feature film|documentary edit"),
        ("Drone footage", r"\bdrone\b"), ("Livestreaming", r"live ?stream"), ("Super 8 film", r"super ?8"),
        ("Raw footage", r"raw footage"), ("Teaser film", r"\bteaser\b|sneak peek"),
        ("Engagement films", r"engagement (?:film|video)"), ("Second videographer", r"second (?:videographer|shooter|camera)"),
    ],
    "wedding-venues": [
        ("Indoor spaces", r"\bindoor\b"), ("Outdoor ceremony", r"outdoor (?:ceremony|ceremonies|wedding)|ceremony (?:lawn|garden)"),
        ("Ceremony and reception on site", r"ceremony (?:and|&) reception"),
        ("In-house catering", r"in[- ]house (?:catering|chef|kitchen)|on[- ]site catering"),
        ("Outside caterers allowed", r"outside (?:caterer|catering|vendors)|bring your own caterer|preferred or outside"),
        ("Bar service", r"bar service|full bar|in[- ]house bar|bar packages?"),
        ("Getting-ready suites", r"bridal suite|getting[- ]ready|groom'?s? (?:suite|room|lounge)"),
        ("On-site lodging", r"on[- ]site lodging|guest (?:rooms|suites|cabins|cottages)|overnight accommodation"),
        ("All-inclusive packages", r"all[- ]inclusive"), ("Rain plan", r"rain plan|backup (?:indoor )?(?:space|plan|location)|inclement weather"),
        ("Tables and chairs included", r"tables (?:and|&) chairs"), ("Free parking", r"free parking|ample parking|on[- ]site parking"),
        ("Wheelchair accessible", r"wheelchair|\bADA\b(?: accessible| compliant)"), ("Pet friendly", r"pet[- ]friendly|dog[- ]friendly"),
        ("Day-of coordinator included", r"(?:day[- ]of )?coordinator (?:is )?included|venue coordinator"),
    ],
    "wedding-planners": [
        ("Full planning", r"full[- ](?:service )?planning"), ("Partial planning", r"partial planning"),
        ("Day-of coordination", r"day[- ]of coordinat"), ("Month-of coordination", r"month[- ]of coordinat"),
        ("Design and styling", r"event design|design (?:and|&) styling|floral design"),
        ("Budget management", r"budget (?:management|tracking|planning)"),
        ("Vendor referrals", r"vendor (?:referral|recommendation|management|selection|sourcing)"),
        ("Rehearsal coordination", r"rehearsal"), ("Welcome bags", r"welcome bags?"),
    ],
    "wedding-djs": [
        ("MC services", r"\bMC\b|emcee|master of ceremonies"), ("Uplighting", r"uplight"),
        ("Ceremony sound", r"ceremony (?:sound|audio|music|microphone)"), ("Photo booth", r"photo ?booth"),
        ("Dance floor lighting", r"dance floor light|intelligent lighting|moving heads"), ("Cold sparks", r"cold spark"),
        ("Dancing on a cloud", r"dancing on (?:the |a )?cloud|low fog|dry ice"), ("Monogram projection", r"monogram|\bgobo\b"),
        ("Live musicians", r"saxophon|live (?:violin|sax|percussion|drummer)"), ("Karaoke", r"karaoke"),
        ("Online planning portal", r"planning (?:portal|tool|app)|song request"),
    ],
    "wedding-florists": [
        ("Bridal bouquets", r"bouquet"), ("Boutonnieres", r"boutonni"), ("Centerpieces", r"centerpiece"),
        ("Ceremony arches", r"\barch(?:es|way)?\b|\barbor\b"), ("Large installations", r"installation|floral wall|hanging (?:floral|installation)"),
        ("Delivery and setup", r"deliver(?:y|ies) (?:and|&) (?:set ?up|install)|set ?up (?:and|&) breakdown"),
        ("Dried flowers", r"dried (?:flower|floral)|preserved flower"), ("Silk flowers", r"silk flower|faux flower|artificial flower"),
        ("A la carte orders", r"a[- ]la[- ]carte"), ("Locally grown flowers", r"locally grown|seasonal (?:blooms|flowers)|flower farm"),
    ],
    "wedding-caterers": [
        ("Plated dinners", r"\bplated\b"), ("Buffets", r"\bbuffet"), ("Family style", r"family[- ]style"),
        ("Food stations", r"(?:food|action|carving) stations?"), ("Food truck", r"food truck"),
        ("Bar service", r"bar (?:service|package)|bartend"), ("Tastings", r"\btastings?\b"),
        ("Vegan and vegetarian", r"\bvegan\b|vegetarian"), ("Gluten-free", r"gluten[- ]free"), ("Kosher", r"\bkosher\b"),
        ("Halal", r"\bhalal\b"), ("Rehearsal dinners", r"rehearsal dinner"), ("Late-night snacks", r"late[- ]night"),
        ("BBQ", r"\bbbq\b|barbecue"), ("Service staff", r"wait ?staff|service staff|servers"),
    ],
    "wedding-cakes": [
        ("Tastings", r"\btastings?\b"), ("Custom cakes", r"custom (?:cake|design)"), ("Cupcakes", r"cupcake"),
        ("Dessert tables", r"dessert (?:table|bar|display)"), ("Cookies", r"\bcookies?\b"), ("Macarons", r"macaron"),
        ("Groom's cakes", r"groom'?s cakes?"), ("Gluten-free", r"gluten[- ]free"), ("Vegan", r"\bvegan\b"),
        ("Delivery and setup", r"deliver"), ("Cutting cakes", r"cutting cake|sheet cake"),
    ],
    "hair-and-makeup": [
        ("Comes to you", r"on[- ]location|on[- ]site|we come to you|travel to you|mobile (?:hair|makeup|beauty)"),
        ("Airbrush makeup", r"airbrush"), ("Bridal trials", r"\btrials?\b"), ("Lashes", r"\blash"),
        ("Bridal party", r"bridal party|bridesmaid"), ("Hair extensions", r"extension"), ("Touch-ups", r"touch[- ]ups?"),
        ("Grooming for the groom", r"groom(?:ing|'?s)? (?:services|package|grooming)"),
    ],
    "wedding-officiants": [
        ("Custom ceremonies", r"custom(?:ized)? ceremon|personali[sz]ed ceremon|write (?:your|a) ceremony"),
        ("Non-religious ceremonies", r"non[- ]denominational|interfaith|secular|non[- ]religious"),
        ("Religious ceremonies", r"christian ceremon|catholic|religious ceremon"),
        ("Rehearsal", r"rehearsal"), ("License filing", r"marriage license|file (?:the|your) license"),
        ("Spanish ceremonies", r"spanish|bilingual|espa[nñ]ol"),
    ],
    "wedding-transportation": [
        ("Limousines", r"\blimo(?:usine)?s?\b"), ("Party buses", r"party bus"),
        ("Vintage cars", r"vintage|classic car|rolls[- ]royce|antique car"), ("Guest shuttles", r"shuttle"),
        ("Trolleys", r"trolley"), ("Sprinter vans", r"sprinter"), ("Coach buses", r"coach bus|motor ?coach"),
    ],
    "wedding-rentals": [
        ("Tables and chairs", r"tables|chairs"), ("Linens", r"linen"), ("Tents", r"\btents?\b"),
        ("Dance floors", r"dance floor"), ("Lighting", r"string lights|bistro lights|uplight|lighting"),
        ("Lounge furniture", r"lounge"), ("Arches and backdrops", r"\barch(?:es)?\b|backdrop"),
        ("Tableware", r"china|flatware|glassware|tableware|chargers"), ("Delivery and setup", r"deliver"),
    ],
    "wedding-bands": [
        ("Ceremony musicians", r"ceremony (?:music|musicians)|string quartet|string trio"),
        ("Cocktail hour sets", r"cocktail hour"), ("Horn section", r"horn section|\bhorns\b"),
        ("DJ between sets", r"\bdj\b"), ("Learns your first dance", r"learn (?:a|your) (?:special |first dance )?song|first dance"),
        ("MC services", r"\bMC\b|emcee"),
    ],
    "wedding-invitations": [
        ("Custom design", r"custom (?:design|invitation|suite)"), ("Letterpress", r"letterpress"), ("Foil printing", r"\bfoil"),
        ("Calligraphy", r"calligraph"), ("Save the dates", r"save[- ]the[- ]dates?"),
        ("Day-of paper", r"\bmenus\b|place cards|programs|signage|seating chart"),
        ("Envelope addressing", r"envelope addressing|guest addressing"), ("Digital invitations", r"digital invitation|e-?vite"),
        ("Wax seals", r"wax seal"),
    ],
    "day-of-coordination": [
        ("Day-of coordination", r"day[- ]of"), ("Month-of coordination", r"month[- ]of"), ("Rehearsal", r"rehearsal"),
        ("Timeline building", r"timeline"), ("Vendor confirmations", r"vendor (?:confirmation|communication|coordination)"),
        ("Setup and teardown", r"set ?up (?:and|&) (?:tear|break) ?down|d[eé]cor setup"),
    ],
}
STYLES = [  # photographers + videographers
    ("Documentary", r"documentary|photojournalis"), ("Fine art", r"fine[- ]art"), ("Editorial", r"editorial"),
    ("Light and airy", r"light (?:and|&) airy"), ("Moody", r"\bmoody\b"), ("True to color", r"true[- ]to[- ](?:life|color)"),
    ("Cinematic", r"cinematic"), ("Candid", r"\bcandid"), ("Timeless", r"\btimeless\b"),
]
LANGS = [("Spanish", r"se habla espa|en espa[nñ]ol|spanish[- ]speaking|habla(?:mos)? espa|hablamos|bilingual (?:english|spanish)|english (?:and|&) spanish"),
         # JC-LAZO-SITEFACTS-1014-MORE: only when the site says it is SPOKEN - "Korean BBQ" is a menu, not a language
         ("Vietnamese", r"(?:speak|speaks|speaking|spoken|fluent|bilingual|trilingual|multilingual|languages?)[^.\n]{0,40}\bvietnamese|\bvietnamese[- ](?:speaking|speaker|spoken)"), ("Korean", r"(?:speak|speaks|speaking|spoken|fluent|bilingual|trilingual|multilingual|languages?)[^.\n]{0,40}\bkorean|\bkorean[- ](?:speaking|speaker|spoken)"), ("Mandarin", r"(?:speak|speaks|speaking|spoken|fluent|bilingual|trilingual|multilingual|languages?)[^.\n]{0,40}\bmandarin|\bmandarin[- ](?:speaking|speaker|spoken)"),
         ("Hindi", r"(?:speak|speaks|speaking|spoken|fluent|bilingual|trilingual|multilingual|languages?)[^.\n]{0,40}\bhindi|\bhindi[- ](?:speaking|speaker|spoken)"), ("Portuguese", r"(?:speak|speaks|speaking|spoken|fluent|bilingual|trilingual|multilingual|languages?)[^.\n]{0,40}\bportugu[eê]se|\bportugu[eê]se[- ](?:speaking|speaker|spoken)"),
         ("French", r"\bfrench[- ]speaking|parlons fran|(?:speak|speaks|speaking|spoken|fluent|bilingual|trilingual|multilingual|languages?)[^.\n]{0,40}\bfrench"), ("Arabic", r"(?:speak|speaks|speaking|spoken|fluent|bilingual|trilingual|multilingual|languages?)[^.\n]{0,40}\barabic|\barabic[- ](?:speaking|speaker|spoken)")]
TRAVEL = re.compile(r"destination wedding|travel(?:s|ing)? (?:worldwide|nationwide|anywhere|the world)|available (?:for|to) travel|"
                    r"willing to travel|will travel|serving (?:all of |the )?(?:state|nationwide)", re.I)
_C = {cat: [(lab, re.compile(p, re.I)) for lab, p in pats + _SHARED] for cat, pats in SERVICES.items()}
_STYLES = [(lab, re.compile(p, re.I)) for lab, p in STYLES]
_LANGS = [(lab, re.compile(p, re.I)) for lab, p in LANGS]

# ---- numbers, only with the words that make them mean what we will say ----------------------------------------
P_SINCE = re.compile(r"(?:since|established|est\.?|founded|serving [\w ,]{0,40} since|in business since)\s*(?:in\s*)?((?:19|20)\d{2})\b", re.I)
P_EST = re.compile(r"(?:established|est\.|founded)\s*(?:in\s*)?((?:19|20)\d{2})\b", re.I)
P_YEARS = re.compile(r"\b(\d{1,2})\+?\s*years?\s+(?:of\s+)?(?:experience|in business|in the industry|shooting|photographing|filming|"
                     r"planning|serving|creating|designing)", re.I)
P_START = re.compile(r"(?:starting (?:at|from)|starts? at|start(?:ing)? (?:price|investment)|packages? (?:start|begin)\w* (?:at|from)|"
                     r"begin(?:s|ning)? at|prices? from|from just|investment (?:starts|begins) at|collections? (?:start|begin)\w* at|"
                     r"rates? (?:start|begin)\w* at|as low as)\s*:?\s*\$\s?(\d{1,3}(?:,\d{3})+|\d{2,6})(?:\.\d\d)?(\s*(?:per|/|a)\s*(?:person|guest|plate|head|hour|slice|serving))?", re.I)
P_PER = re.compile(r"\$\s?(\d{1,3}(?:\.\d\d)?)\s*(?:per|/|a)\s*(person|guest|plate|head|slice|serving)\b", re.I)
P_CAP = re.compile(r"(?:up to|accommodat\w*(?: up to)?|seat(?:s|ing)?(?: up to)?|capacity (?:of|for)(?: up to)?|holds(?: up to)?|"
                   r"for up to|maximum of|max(?:imum)? capacity(?: of)?:?)\s*(\d{2,4})\s*(?:\+\s*)?(?:seated |standing |of your )?"
                   r"(?:guests|people|persons|attendees|seated)", re.I)

# JC-LAZO-SITEFACTS-1014-MORE: more facts wedding sites state plainly
P_YEARS2 = re.compile(r"(?:over|more than|nearly|almost|for)\s+(\d{1,2})\+?\s+years\b(?=[^.]{0,50}(?:experience|business|industry|"
                      r"wedding|serving|photograph|film|plann|cater|bak|event|DJ|music|florist|design))", re.I)
P_WED_N = re.compile(r"(?:(?:over|more than|nearly|almost|upwards of)\s+(\d{1,2},\d{3}|\d{2,5})\+?|(\d{1,2},\d{3}|\d{2,5})\+)\s+"
                     r"(?:happy |beautiful |amazing |unforgettable )?(weddings|couples)\b", re.I)
P_INSURED = re.compile(r"\b(?:fully|licensed,?\s+(?:bonded,?\s+)?(?:and|&)|bonded\s+(?:and|&))\s+insured\b", re.I)
AWARDS = [("The Knot Best of Weddings", re.compile(r"best[-_ ]?of[-_ ]?weddings|\bbow[-_]?20[12]\d\b", re.I)),
          ("WeddingWire Couples' Choice", re.compile(r"couples[\u2019'_ -]?\s?choice", re.I))]
P_AWARD_YEAR = re.compile(r"(?:best[-_ ]?of[-_ ]?weddings|couples[\u2019'_ -]?\s?choice|\bbow)[^0-9]{0,30}(20[12]\d)", re.I)

_robots = {}
_robots_lock = threading.Lock()


def _allowed(url):
    p = urlparse(url)
    key = f"{p.scheme}://{p.netloc}"
    with _robots_lock:
        rp = _robots.get(key)
    if rp is None:
        rp = robotparser.RobotFileParser()
        try:
            r = requests.get(key + "/robots.txt", headers={"User-Agent": UA}, timeout=6)
            rp.parse(r.text.splitlines() if r.status_code == 200 and "html" not in r.headers.get("content-type", "") else [])
        except Exception:
            rp.parse([])
        with _robots_lock:
            _robots[key] = rp
    return rp.can_fetch(BOT, url)


def fetch(url, timeout=12):
    """(html, final_url, status). html is None for anything that is not a 200 HTML page."""
    with requests.get(url, headers={"User-Agent": UA, "Accept-Language": "en-US"}, timeout=timeout,
                      allow_redirects=True, stream=True) as r:
        ct = r.headers.get("content-type", "")
        if r.status_code != 200 or "html" not in ct:
            return None, r.url, r.status_code
        body = b""
        for chunk in r.iter_content(65536):
            body += chunk
            if len(body) > MAX_BYTES:
                break
        # JC-LAZO-SITEFACTS-1014-MORE: r.apparent_encoding re-reads the streamed body, which is already
        # consumed, and raised RuntimeError on 5,250 sites. Use the declared charset, else the page's own.
        enc = r.encoding if r.encoding and r.encoding.lower() != "iso-8859-1" else None
        if not enc:
            m = re.search(rb'<meta[^>]+charset=["\']?([\w-]+)', body[:4096], re.I)
            enc = m.group(1).decode("ascii", "ignore") if m else "utf-8"
        try:
            html = body.decode(enc, errors="replace")
        except LookupError:
            html = body.decode("utf-8", errors="replace")
        return _slim(html), r.url, 200


# Builder pages are mostly inline CSS, scripts, SVG and base64 images; parsing all of that in BeautifulSoup made
# the 8MB pages CPU-bound. None of it carries a fact, so it goes before the parser sees it. JSON-LD stays: it
# carries foundingDate and sameAs.   JC-LAZO-SITEFACTS-1014-MORE
_SLIM = re.compile(r"<style\b[^>]*>.*?</style\s*>|<script\b(?![^>]*ld\+json)[^>]*>.*?</script\s*>|<svg\b[^>]*>.*?</svg\s*>|"
                   r"<!--.*?-->|data:[\w/+.-]+;base64,[A-Za-z0-9+/=]{100,}|\sstyle=\"[^\"]{40,}\"", re.S | re.I)


def _slim(html):
    return _SLIM.sub(" ", html)


def visible_text(soup, limit=40000):
    for t in soup(["script", "style", "noscript", "svg", "iframe"]):
        t.decompose()
    # JC-LAZO-SITEFACTS-1014-MORE: the whole-page fallback is taken BEFORE nav/header/footer/form go, because
    # Wix and some themes wrap the entire page in one of them
    body = soup.body or soup
    full = " ".join(body.get_text(" ", strip=True).split())
    for t in soup(["nav", "footer", "header", "form"]):
        t.decompose()
    chunks = []
    for el in soup.find_all(["p", "li", "h1", "h2", "h3", "h4", "blockquote", "td", "dd", "figcaption"]):
        s = " ".join(el.get_text(" ", strip=True).split())
        if len(s) >= 12:
            chunks.append(s)
    out = " \n ".join(chunks)
    if len(out.split()) < 150:
        # JC-LAZO-SITEFACTS-1014-MORE: builder sites keep their copy in div/span; read the whole body instead
        if len(full.split()) > len(out.split()):
            out = full
    return out[:limit]


def _jsonld(soup):
    out = {}
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except Exception:
            continue
        items = data if isinstance(data, list) else data.get("@graph", [data]) if isinstance(data, dict) else []
        for it in items:
            if not isinstance(it, dict):
                continue
            if it.get("foundingDate") and "foundingDate" not in out:
                m = re.match(r"((?:19|20)\d{2})", str(it["foundingDate"]))
                if m:
                    out["foundingDate"] = int(m.group(1))
            pr = it.get("priceRange")
            if isinstance(pr, str) and re.fullmatch(r"\${1,4}", pr.strip()) and "priceRange" not in out:
                out["priceRange"] = pr.strip()
            sa = it.get("sameAs")
            if sa:
                out.setdefault("sameAs", []).extend(sa if isinstance(sa, list) else [sa])
    return out


def _social(href):
    p = urlparse(href)
    host = re.sub(r"^(?:www|m)\.", "", p.netloc.lower())
    for dom, label in SOCIAL.items():
        if host == dom or host.endswith("." + dom):
            path = p.path.rstrip("/")
            if not path or path.count("/") > 2 or any(s in href.lower() for s in SOCIAL_SKIP):
                return None
            return label, f"https://www.{dom}{path}/"
    return None


def extract(pages, home_soup_meta, cats, towns=(), badges=""):
    """pages: [(kind, url, text)]. Returns the facts dict (without crawl bookkeeping)."""
    text = " \n ".join(t for _, _, t in pages)
    f = {}
    svc = {}
    for cat in cats:
        hits = [lab for lab, rx in _C.get(cat, []) if rx.search(text)]
        if hits:
            svc[cat] = hits
    if svc:
        f["services"] = svc
    if set(cats) & {"wedding-photographers", "wedding-videographers"}:
        st = [lab for lab, rx in _STYLES if rx.search(text)]
        if st:
            f["styles"] = st[:4]
    langs = [lab for lab, rx in _LANGS if rx.search(text)]
    if langs:
        f["languages"] = langs
    if TRAVEL.search(text):
        f["travels"] = True
    # a venue's "since 1918" is usually the building; only "established / founded" dates the business there
    rx_since = P_EST if "wedding-venues" in cats else P_SINCE
    since = sorted({int(y) for y in rx_since.findall(text) if 1900 <= int(y) <= THIS_YEAR})
    if home_soup_meta.get("foundingDate") and 1900 <= home_soup_meta["foundingDate"] <= THIS_YEAR:
        since = [home_soup_meta["foundingDate"]] + since
    if since:
        f["since"] = since[0]
    else:
        yrs = [int(n) for n in P_YEARS.findall(text) + P_YEARS2.findall(text) if 2 <= int(n) <= 60]
        if yrs:
            f["years"] = max(yrs)
    wn = []
    for a1, a2, what in P_WED_N.findall(text):
        n = int((a1 or a2).replace(",", ""))
        if 20 <= n <= 20000 and not (1990 <= n <= THIS_YEAR + 1):   # "2024 weddings" is a year, not a count
            wn.append((n, what.lower()))
    if wn:
        n, what = max(wn)
        f["wed_count"] = {"n": n, "what": what}
    if P_INSURED.search(text):
        f["insured"] = "licensed" if re.search(r"licensed", P_INSURED.search(text).group(0), re.I) else "fully"
    aw_text = f"{text} {badges}"
    aw = [lab for lab, rx in AWARDS if rx.search(aw_text)]
    if aw:
        f["awards"] = aw
        yrs_aw = sorted({int(y) for y in P_AWARD_YEAR.findall(aw_text) if 2010 <= int(y) <= THIS_YEAR})
        if yrs_aw:
            f["award_years"] = yrs_aw[-4:]
    if towns:
        # towns[0] is the metro's own city, which nearly every local site names; it only counts alongside two others
        seen_t = [t for t in towns if re.search(r"\b" + re.escape(t) + r"\b", text)]
        if len([t for t in seen_t if t != towns[0]]) >= 2:
            f["areas"] = seen_t[:8]
    starts, per = [], []
    for m in P_START.finditer(text):
        n = int(m.group(1).replace(",", ""))
        unit = (m.group(2) or "").strip().lower()
        if unit:
            u = re.sub(r"^(?:per|/|a)\s*", "", unit)
            if 1 <= n <= 500:
                per.append((n, u))
        elif 100 <= n <= 100000:
            starts.append((n, m.group(0)[:80]))
    for m in P_PER.finditer(text):
        n = float(m.group(1))
        if 1 <= n <= 500:
            per.append((int(round(n)), m.group(2).lower()))
    if starts:
        n, ctx = min(starts)
        f["from_price"] = n
        f["from_price_ctx"] = ctx
    if per and set(cats) & {"wedding-caterers", "wedding-cakes", "wedding-venues", "wedding-bands", "wedding-djs"}:
        n, u = min(per)
        f["per_price"] = {"n": n, "unit": "guest" if u in ("person", "head", "plate", "guest") else u}
    if "wedding-venues" in cats:
        caps = [int(c) for c in P_CAP.findall(text) if 10 <= int(c) <= 5000]
        if caps:
            f["capacity"] = max(caps)
    f["wedding_hits"] = len(WEDDING.findall(text))
    return f


def crawl_one(job):
    """job = {'url', 'cats'} -> facts for that site (shared by every vendor that lists it)."""
    url, cats, towns = job["url"], job["cats"], job.get("towns") or ()
    out = {"url": url, "checked": date.today().isoformat(), "ok": False}
    try:
        if not _allowed(url):
            out["why"] = "robots"
            return out
        try:
            html, final, code = fetch(url)
        except requests.exceptions.SSLError:
            # JC-LAZO-SITEFACTS-1014-MORE: most certificate errors are www vs bare domain; try the other one
            p = urlparse(url)
            alt = p.netloc[4:] if p.netloc.startswith("www.") else "www." + p.netloc
            html, final, code = fetch(f"{p.scheme}://{alt}{p.path or '/'}")
    except requests.exceptions.SSLError:
        out["why"] = "ssl"
        return out
    except Exception as e:
        out["why"] = type(e).__name__
        return out
    if not html:
        out["why"] = f"http {code}"
        return out
    soup = BeautifulSoup(html, "lxml")
    host = urlparse(final).netloc.lower().replace("www.", "")
    out["final"] = final
    title = (soup.title.get_text(" ", strip=True) if soup.title else "")[:160]
    md = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
    desc = " ".join((md.get("content", "") if md else "").split())
    meta = _jsonld(soup)
    raw = soup.get_text(" ", strip=True)[:4000]  # the parked check reads the page before visible_text strips it
    # award badges are usually images: their alt text and file names say which award
    badges = " ".join(f"{im.get('alt', '')} {im.get('src', '')} {im.get('data-src', '')}" for im in soup.find_all("img"))[:20000]
    socials = {}
    sub = {}
    for a in soup.find_all("a", href=True):
        href = urljoin(final, a["href"].strip())
        s = _social(href)
        if s and s[0] not in socials:
            socials[s[0]] = s[1]
            continue
        p = urlparse(href)
        if p.netloc.lower().replace("www.", "") != host or p.scheme not in ("http", "https"):
            continue
        last = p.path.lower().rstrip("/").rsplit("/", 1)[-1]
        if not last or "." in last.replace(".html", "").replace(".php", ""):
            continue
        for kind, words in SUBPAGES:
            if kind not in sub and any(last == w or last.startswith(w + "-") or last.endswith("-" + w) for w in words):
                sub[kind] = href.split("#")[0]
    for x in meta.get("sameAs", []):
        s = _social(str(x))
        if s and s[0] not in socials:
            socials[s[0]] = s[1]
    pages = [("home", final, visible_text(soup))]
    seen = {final.rstrip("/")}
    for kind, _ in SUBPAGES:
        u = sub.get(kind)
        if not u or u.rstrip("/") in seen or len(pages) >= 5:
            continue
        seen.add(u.rstrip("/"))
        try:
            if not _allowed(u):
                continue
            time.sleep(0.4)
            h2, _, _ = fetch(u)
            if h2:
                pages.append((kind, u, visible_text(BeautifulSoup(h2, "lxml"))))
        except Exception:
            pass
    out.update(extract(pages, meta, cats, towns, badges))
    out["wedding_hits"] += len(WEDDING.findall(f"{title} {desc}"))  # a JS-built site may say it only in its title
    out["v"] = 4  # 2: wedding_hits includes the title + description; 3: 1014-MORE extraction; 4: + slim parse, header-wrapped pages
    if SPAM.search(f"{title} {desc}"):
        out["hijacked"] = True
    out["ok"] = True
    out["title"] = title
    out["pages"] = [k for k, _, _ in pages]
    out["words"] = sum(len(t.split()) for _, _, t in pages)
    if socials:
        out["socials"] = socials
    if 50 <= len(desc) <= 240 and not GENERIC_DESC.search(desc):
        out["desc"] = desc
    if PARKED.search(raw) and out["words"] < 400:
        out["parked"] = True
    return out


def norm_url(u):
    u = (u or "").strip()
    if not u:
        return ""
    if not re.match(r"^https?://", u, re.I):
        u = "https://" + u
    p = urlparse(u)
    host = p.netloc.lower()
    if not host or "." not in host:
        return ""
    # Places often hands us a Facebook page or a booking platform; those are not the vendor's own site.
    if any(d in host for d in ("facebook.com", "instagram.com", "yelp.com", "theknot.com", "weddingwire.com", "zola.com",
                               "google.com", "linktr.ee", "business.site", "square.site", "thumbtack.com", "gigsalad.com")):
        return ""
    return f"{p.scheme.lower()}://{host}{p.path or '/'}"


def _town(address):
    """Same rule as build.py _locality: '123 Main St, Scottsdale, AZ 85251, USA' -> 'Scottsdale'."""
    parts = [p.strip() for p in address.split(",")]
    return parts[-3] if len(parts) >= 3 and parts[-3] and not parts[-3][0].isdigit() else ""


def load_vendors(metro_ids):
    import firebase_admin
    from firebase_admin import credentials, firestore
    cred = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or r"C:\Users\kurvh\secrets\lazo-513ec-admin.json"
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(cred))
    db = firestore.client()
    for mid in metro_ids:
        rows = []
        for doc in db.collection("vendors").where("metroId", "==", mid).select(["name", "website", "categories", "delisted", "address"]).stream():
            v = doc.to_dict()
            if v.get("delisted"):
                continue
            rows.append({"id": doc.id, "name": v.get("name", ""), "website": v.get("website") or "", "categories": v.get("categories") or [],
                         "city": _town(v.get("address") or "")})
        yield mid, rows


def _save(path, metro, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"metro": metro, "updated": datetime.now().isoformat(timespec="seconds"), "vendors": data},
                              ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(path)


def run_metro(mid, vendors, a):
    path = OUT_DIR / f"{mid}.json"
    data = json.loads(path.read_text(encoding="utf-8"))["vendors"] if path.exists() else {}
    today = date.today()
    jobs = {}
    for v in vendors:
        u = norm_url(v["website"])
        if not u:
            continue
        old = data.get(v["id"])
        if old and a.upgrade and old.get("url") == u and _worth_upgrading(old):
            pass   # JC-LAZO-SITEFACTS-1014-MORE: revisit with the v3 reader whatever its age
        elif old and not a.refresh and old.get("url") == u:
            try:
                if (today - date.fromisoformat(old["checked"])).days < a.max_age:
                    continue
            except Exception:
                pass
        j = jobs.setdefault(u, {"url": u, "cats": set(), "ids": []})
        j["cats"].update(v["categories"])
        j["ids"].append(v["id"])
    from collections import Counter
    tc = Counter(v["city"] for v in vendors if v.get("city"))
    main = next((m["name"] for m in METROS if m["id"] == mid), "").split(",")[0].strip()
    towns = [main] + sorted((t for t, n in tc.items() if n >= 3 and len(t) >= 4 and t != main and t.lower() not in WORD_TOWNS),
                            key=lambda t: -tc[t])[:60]
    todo = list(jobs.values())[: a.limit or None]
    with_site = sum(1 for v in vendors if norm_url(v["website"]))
    print(f"{mid}: {len(vendors):,} vendors, {with_site:,} with their own site, {len(todo):,} sites to visit", flush=True)
    t0, done = time.time(), 0
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(crawl_one, {"url": j["url"], "cats": sorted(j["cats"]), "towns": towns}): j for j in todo}
        for f in as_completed(futs):
            j = futs[f]
            try:
                r = f.result()
            except Exception as e:
                r = {"url": j["url"], "checked": today.isoformat(), "ok": False, "why": type(e).__name__}
            for vid in j["ids"]:
                data[vid] = r
            done += 1
            if done % 200 == 0:
                _save(path, mid, data)
                print(f"  {done:,}/{len(todo):,} sites, {time.time() - t0:.0f}s", flush=True)
    _save(path, mid, data)
    summarize(mid, data)


# towns whose names are also ordinary words: "Surprise your guests" is not Surprise, AZ
WORD_TOWNS = {"surprise", "paradise", "liberty", "independence", "commerce", "friendly", "hope", "normal", "enterprise",
              "victory", "harmony", "unity", "union", "eden", "joy", "story", "republic", "lakeside", "riverside", "hollywood",
              "beverly", "grand", "plains", "center", "village", "mission", "orange", "lake", "sunrise", "hampton", "hamilton",
              "lincoln", "washington", "jackson", "franklin", "clinton", "madison", "marion", "springfield", "fairview"}

RETRY_WHY = ("RuntimeError", "ssl", "ConnectionError", "ReadTimeout", "ConnectTimeout", "ChunkedEncodingError")


def _worth_upgrading(old):
    """--upgrade: sites the v2 reader failed on or read thin, and nothing already read by v3."""
    if old.get("v", 1) >= 4:
        return False
    if not old.get("ok"):
        return old.get("why") in RETRY_WHY
    if old.get("parked") or old.get("hijacked"):
        return False
    return old.get("words", 0) < 500 or old.get("wedding_hits", 0) < 2 or score(old) < 4


def score(f):
    """How many distinct facts a page would show. build.py uses the same count."""
    n = 0
    n += min(len([x for xs in (f.get("services") or {}).values() for x in xs]), 3)
    n += bool(f.get("styles")) + bool(f.get("since") or f.get("years")) + bool(f.get("from_price") or f.get("per_price"))
    n += bool(f.get("capacity")) + bool(f.get("languages")) + bool(f.get("socials")) + bool(f.get("travels"))
    n += bool(f.get("wed_count")) + bool(f.get("awards")) + bool(f.get("insured")) + bool(f.get("areas"))
    return n


def summarize(mid, data, show=0):
    rows = list(data.values())
    ok = [r for r in rows if r.get("ok")]
    good = [r for r in ok if not r.get("parked") and r.get("wedding_hits", 0) > 0]
    print(f"  {mid}: {len(rows):,} vendors checked, {len(ok):,} sites read, {sum(1 for r in ok if r.get('parked')):,} parked, "
          f"{sum(1 for r in ok if not r.get('wedding_hits')):,} never mention weddings, "
          f"{sum(1 for r in good if score(r) >= 4):,} with 4+ facts, {sum(1 for r in good if r.get('from_price') or r.get('per_price')):,} with a price, "
          f"{sum(1 for r in rows if r.get('why') == 'robots'):,} blocked by robots.txt")
    if show:
        for vid, r in list(data.items())[:show]:
            if r.get("ok"):
                print(json.dumps({"id": vid, **{k: r[k] for k in r if k not in ("checked", "ok", "pages", "from_price_ctx")}}, ensure_ascii=False)[:600])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--metro", action="append", help="metro id (repeatable)")
    ap.add_argument("--tranche", type=int, help="every metro up to this tranche (7 = all)")
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--limit", type=int, default=0, help="visit at most N sites per metro (sampling)")
    ap.add_argument("--max-age", type=int, default=30, help="days before a site is visited again")
    ap.add_argument("--refresh", action="store_true", help="visit every site again regardless of age")
    ap.add_argument("--upgrade", action="store_true", help="revisit sites the v2 reader failed on or read thin")
    ap.add_argument("--report", action="store_true", help="summarize existing files, no crawling")
    ap.add_argument("--show", type=int, default=0, help="with --report, print N sample records")
    a = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ids = a.metro or ([m["id"] for m in metros_for_tranche(a.tranche)] if a.tranche else [])
    if not ids:
        ap.error("give --metro or --tranche")
    unknown = set(ids) - {m["id"] for m in METROS}
    if unknown:
        ap.error(f"unknown metro {', '.join(sorted(unknown))}")
    if a.report:
        for mid in ids:
            p = OUT_DIR / f"{mid}.json"
            if p.exists():
                summarize(mid, json.loads(p.read_text(encoding="utf-8"))["vendors"], a.show)
        return
    for mid, vendors in load_vendors(ids):
        run_metro(mid, vendors, a)


if __name__ == "__main__":
    main()


# ---- build side: build.py calls attach(by_metro) when LAZO_SITEFACTS=1 --------------------------------------------
PHOTO_VIDEO = ("wedding-photographers", "wedding-videographers")
PER_PRICE_CATS = ("wedding-caterers", "wedding-cakes", "wedding-venues", "wedding-bands", "wedding-djs")


def page_rows(f, cat):
    """(label, value) rows for one category page, in Lazo's words. [] when the site gives too little."""
    rows = []
    svc = (f.get("services") or {}).get(cat) or []
    if svc:
        rows.append(("Services they list", ", ".join(svc[:8])))
    if cat in PHOTO_VIDEO and f.get("styles"):
        rows.append(("Style, in their words", ", ".join(f["styles"])))
    if f.get("from_price"):
        rows.append(("Prices on their site", f"Starting at ${f['from_price']:,}"))
    elif f.get("per_price") and cat in PER_PRICE_CATS:
        rows.append(("Prices on their site", f"From ${f['per_price']['n']:,} per {f['per_price']['unit']}"))
    if cat == "wedding-venues" and f.get("capacity"):
        rows.append(("Capacity", f"Up to {f['capacity']:,} guests"))
    if f.get("since"):
        rows.append(("In business since", str(f["since"])))
    elif f.get("years"):
        rows.append(("Experience", f"{f['years']}+ years"))
    if f.get("languages"):
        rows.append(("Languages", " and ".join(["English"] + f["languages"]) if len(f["languages"]) == 1
                     else "English, " + ", ".join(f["languages"])))
    if f.get("travels") and "Destination weddings" not in svc:
        rows.append(("Travel", "Takes weddings outside the area"))
    # JC-LAZO-SITEFACTS-1014-MORE
    if f.get("wed_count"):
        rows.append(("Experience", f"{f['wed_count']['n']:,}+ {f['wed_count']['what']}, by their count")
                    if not (f.get("since") or f.get("years")) else ("Weddings so far", f"{f['wed_count']['n']:,}+ {f['wed_count']['what']}, by their count"))
    if f.get("awards"):
        yrs = f.get("award_years") or []
        rows.append(("Awards they list", ", ".join(f["awards"]) + (f" ({', '.join(map(str, yrs))})" if yrs else "")))
    if f.get("areas"):
        rows.append(("Areas they mention", ", ".join(f["areas"][:6])))
    if f.get("insured"):
        rows.append(("Insurance", "Licensed and insured, per their site" if f["insured"] == "licensed" else "Fully insured, per their site"))
    return rows


def attach(by_metro):
    """Hang site facts on every vendor dict: v['site'] (quote, socials, source), v['site_rows_by_cat'],
    v['site_ld'] (extra LocalBusiness fields) and v['site_score']. Claimed vendors are skipped: their own
    profile is the source of truth on their page."""
    n_v, n_facts = 0, 0
    for mid, vs in by_metro.items():
        p = OUT_DIR / f"{mid}.json"
        if not p.exists():
            continue
        facts = json.loads(p.read_text(encoding="utf-8"))["vendors"]
        for v in vs:
            f = facts.get(v.get("placeId"))
            if not f or not f.get("ok") or f.get("parked") or v.get("claimedBy"):
                continue
            head = f"{f.get('title') or ''} {f.get('desc') or ''}"
            if f.get("hijacked") or SPAM.search(head):      # files crawled before 1014 carry no hijacked flag
                continue
            if f.get("wedding_hits", 0) + (0 if f.get("v", 1) >= 2 else len(WEDDING.findall(head))) < 2:
                continue
            if f.get("v", 1) < 3 and f.get("languages"):
                # JC-LAZO-SITEFACTS-1014-MORE: the v2 reader took "Korean BBQ" for a language; until a site is
                # re-read, trust only Spanish, whose pattern always needed "se habla / hablamos / bilingual"
                f = dict(f, languages=[x for x in f["languages"] if x == "Spanish"])
                if not f["languages"]:
                    f.pop("languages")
            by_cat = {c: page_rows(f, c) for c in v.get("categories") or []}
            by_cat = {c: r for c, r in by_cat.items() if len(r) >= 2}
            ld = {}
            if f.get("socials"):
                ld["sameAs"] = list(f["socials"].values())
            if f.get("since"):
                ld["foundingDate"] = str(f["since"])
            if f.get("capacity") and "wedding-venues" in (v.get("categories") or []):
                ld["maximumAttendeeCapacity"] = f["capacity"]
            if f.get("languages"):
                ld["knowsLanguage"] = ["en"] + [{"Spanish": "es", "Vietnamese": "vi", "Korean": "ko", "Mandarin": "zh", "Hindi": "hi",
                                                 "Portuguese": "pt", "French": "fr", "Arabic": "ar"}[x] for x in f["languages"]]
            v["site_ld"] = ld
            if not by_cat and not f.get("socials"):
                continue
            try:
                checked = date.fromisoformat(f["checked"]).strftime("%B %Y")
            except Exception:
                checked = ""
            v["site_rows_by_cat"] = by_cat
            v["site_score"] = score(f)
            v["site_strong"] = bool(f.get("from_price") or f.get("per_price") or f.get("since") or f.get("capacity"))
            v["site"] = {"host": urlparse(f.get("final") or f["url"]).netloc.replace("www.", ""), "checked": checked,
                         "quote": f.get("desc") or "", "socials": f.get("socials") or {}}
            n_v += 1
            n_facts += bool(by_cat)
    print(f"[site-facts] {n_v:,} vendor(s) carry a block from their own site, {n_facts:,} with 2+ facts")
