"""outreach_emails.py - JC-LAZO-OUTREACH-1018: the "claim your profile" list.

Every vendor page on meetlazo.com is a listing nobody has claimed. This finds the address to write to: it
pulls every unclaimed, listed vendor with a website out of Firestore, visits the site (home, then the
contact page, then about) with the same fetcher, robots.txt rules and User-Agent as site_facts.py, and
keeps every email address the site publishes - mailto: links, Cloudflare-protected addresses, JSON-LD,
plain text, "name [at] domain [dot] com" - scored so the business's own domain beats a gmail which beats
a role address at some other domain. Junk (noreply, example, wixpress, sentry, image file names) is dropped.
Sites with only a contact form are counted as such, so Jesse knows how many can't be emailed at all.

    python generate\\outreach_emails.py --vendors            # Firestore -> data/outreach/_vendors.json
    python generate\\outreach_emails.py --metro phoenix      # crawl one metro (resumable)
    python generate\\outreach_emails.py --all                # every metro, biggest first
    python generate\\outreach_emails.py --summary            # CSVs: by metro, by category, one row per vendor
    python generate\\outreach_emails.py --push               # outreach/{vendorId} docs in Firestore

Output: generate/data/outreach/<metro>.json  {placeId: result}. The folder is git-ignored: it holds
other people's email addresses. Nothing here sends anything.

Firestore shape (collection `outreach`, one doc per vendor, admin-only - no rule names it, so clients get
the default deny; vendors/{id} is world-readable, which is why the emails do NOT go under it):
  outreach/{vendorId}
    vendorId, name, metroId, categories[], pageUrl, website, siteHost
    site:     ok | form_only | no_contact | dead | robots | skipped
    emails:   [{addr, score, where, page}]   best: addr | null
    form:     true when the site has a contact form / booking widget
    sharedBy: n    (how many listed vendors share this website - a chain gets ONE email)
    flags:    {noWedding, parked, hijacked}
    token:    22-char URL-safe id for the tracked claim link (meetlazo.com/claim/{token})
    status:   listed  (Phase 2 moves it: queued, sent, bounced, complained, unsubscribed, clicked, claimed)
    checkedAt, createdAt
"""
import argparse, base64, csv, json, os, re, secrets, sys, time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "generate"))
import site_facts as SF  # noqa: E402  - fetch rules, robots, norm_url, parked/spam detection
from config.metros import METROS  # noqa: E402

OUT_DIR = ROOT / "generate" / "data" / "outreach"
FACTS_DIR = SF.OUT_DIR
VENDORS_FILE = OUT_DIR / "_vendors.json"
PATHS_FILE = ROOT / "generate" / "vendor_paths.json"
SITE = "https://meetlazo.com"

# ---- what counts as an email -------------------------------------------------------------------------------------
EMAIL_RX = re.compile(r"[A-Za-z0-9][A-Za-z0-9._%+'-]{0,63}@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*\.[A-Za-z]{2,24}")
# "name [at] domain [dot] com", "name (at) domain.com", "name AT domain DOT com", "name {at} domain"
OBF_RX = re.compile(r"([A-Za-z0-9._%+-]{1,64})\s*(?:\[\s*at\s*\]|\(\s*at\s*\)|\{\s*at\s*\}|<\s*at\s*>|\s+AT\s+|\s+at\s+(?=[A-Za-z0-9-]+\s*(?:\[|\(|\{|\s+DOT\s+|\s+dot\s+)))\s*"
                    r"([A-Za-z0-9-]{1,63}(?:\s*(?:\[\s*dot\s*\]|\(\s*dot\s*\)|\{\s*dot\s*\}|\s+DOT\s+|\s+dot\s+|\.)\s*[A-Za-z0-9-]{1,63}){1,3})")
MAILTO_RX = re.compile(r"mailto:([^\"'?>\s]+)", re.I)
CF_RX = re.compile(r"data-cfemail=[\"']([0-9a-fA-F]+)[\"']|/cdn-cgi/l/email-protection#([0-9a-fA-F]+)")

FREE_MAIL = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com", "aol.com", "me.com", "mac.com", "live.com",
             "msn.com", "comcast.net", "att.net", "sbcglobal.net", "verizon.net", "cox.net", "ymail.com", "protonmail.com",
             "proton.me", "mail.com", "earthlink.net", "bellsouth.net", "charter.net", "rocketmail.com", "googlemail.com",
             "yahoo.co.uk", "hotmail.co.uk", "optonline.net", "roadrunner.com", "frontier.com", "windstream.net", "centurylink.net",
             "juno.com", "netzero.net", "q.com", "pm.me", "hey.com", "fastmail.com", "zoho.com", " me.com"}
ROLE = {"info", "hello", "contact", "contactus", "bookings", "booking", "book", "inquire", "inquiry", "inquiries", "enquiries",
        "events", "event", "weddings", "wedding", "studio", "team", "office", "sales", "admin", "mail", "email", "support", "help",
        "hi", "hey", "general", "reservations", "orders", "catering", "frontdesk", "welcome", "connect", "service", "customerservice",
        "marketing", "media", "press", "careers", "jobs", "billing", "accounts", "accounting", "hr"}
# Addresses that are never a vendor's inbox. Checked against the whole lower-cased address.
JUNK_RX = re.compile(r"noreply|no-reply|no_reply|donotreply|do-not-reply|mailer-daemon|postmaster@|abuse@|dmca@|privacy@|legal@|unsubscribe|"
                     r"example\.|\.example$|@example|sentry|wixpress|@wix\.com|squarespace|godaddy|shopify|wordpress|@w3\.org|schema\.org|"
                     r"yourdomain|your-domain|yourname|yoursite|yourcompany|@domain\.|@email\.com|@mail\.com$|@test\.|^test@|^user@|^username@|^name@|"
                     r"^someone@|^email@|^sample@|^mysite|^johndoe|^janedoe|^jdoe|john\.doe|jane\.doe|^jsmith|^firstname|^lastname|^first\.last|"
                     r"lorem|placeholder|@site\.com|@company\.com|@business\.com|@hostname|@localhost|@2x|@3x|\.(?:png|jpe?g|gif|svg|webp|avif|css|js|json|pdf|mp4|woff2?|ttf|eot|ico|html?)$|"
                     r"@google\.com|@facebook\.com|@fb\.com|@apple\.com|@paypal\.com|amazonses|mailchimp|constantcontact|@hubspot|cloudflare|jquery|"
                     r"@npmjs|@github|@reactjs|@vuejs|@angular|@getbootstrap|@fontawesome|@typekit|@adobe\.com|@microsoft\.com|@mozilla|"
                     r"@instagram|@twitter|@x\.com|@tiktok|@pinterest|@youtube|@linkedin|@yelp\.com|@theknot|@weddingwire|@zola\.com|@honeybook\.com|"
                     r"@dubsado|@squareup|@stripe\.com|@intuit|@quickbooks|@wufoo|@typeform|@jotform|@formspree|@mailgun|@sendgrid|@resend|@postmarkapp|"
                     r"@elementor|@wpengine|@kinsta|@flywheel|@bluehost|@hostgator|@siteground|@dreamhost|@weebly|@duda|@webflow|@framer|@carrd|"
                     r"@showit|@pixieset|@tave|@17hats|@studioninja|@sprout|@shootproof|@pic-time|@smugmug|@zenfolio|"
                     r"^(?:[0-9a-f]{16,}|[0-9]{6,})@|u003e|%[0-9a-f]{2}|\.\.|@.*@", re.I)
# a web designer's or theme vendor's address sits on many client sites; it is not the vendor
DESIGNER_RX = re.compile(r"webdesign|web-design|webdev|sitedesign|seo@|design@.*(?:agency|studio)|@.*(?:webdesign|designco|creativeagency|digitalagency|mediaagency|marketing)\.", re.I)
VALID_TLD_RX = re.compile(r"\.(?:com|net|org|co|us|biz|info|me|io|studio|photography|photo|photos|wedding|weddings|events|design|art|love|life|"
                          r"live|film|video|music|band|dj|cakes?|flowers?|florist|catering|cafe|restaurant|bar|club|house|space|place|church|"
                          r"online|site|website|web|shop|store|boutique|salon|beauty|makeup|hair|style|pro|expert|services?|agency|company|"
                          r"inc|llc|ltd|group|team|work|works|studio|media|digital|tv|fm|am|xyz|app|dev|page|blog|email|pink|black|gold|"
                          r"rocks|ninja|guru|nyc|la|vegas|miami|boston|london|ca|uk|mx|au|nz|de|fr|es|it|nl|be|ch|at|ie|pt|br|ar|in|jp|kr|"
                          r"edu|gov|mil|coop|travel|tours|wine|beer|coffee|events|party|dance|fun|cool|today|world|global|international|"
                          r"capital|realty|properties|rentals|limo|limos|taxi|cars|auto|bike|farm|ranch|garden|gardens|villas|estate|"
                          r"tech|tools|solutions|systems|network|center|academy|school|university|institute|foundation|charity|ngo|"
                          r"mobi|name|tel|asia|cat|jobs|museum|aero|pw|cc|ws|tk|ly|to|ai|gg|st|sh|vc|vg|ms|bz|ag|lc|gd|tc|ky|bm|bs|"
                          r"im|je|gs|ac|fo|gl|is|no|se|dk|fi|pl|cz|sk|hu|ro|gr|tr|il|za|ng|ke|gh|eg|ma|ph|sg|my|th|vn|id|hk|tw|cn|ru|ua)$", re.I)

CONTACT_WORDS = ("contact", "contact-us", "contactus", "contact_us", "get-in-touch", "getintouch", "inquire", "inquiry", "inquiries",
                 "enquire", "enquiry", "reach-us", "reach-out", "connect", "hire", "hire-us", "book", "booking", "book-now", "bookings",
                 "request", "request-a-quote", "quote", "lets-talk", "let-s-talk", "say-hello", "hello", "info", "information", "touch")
ABOUT_WORDS = ("about", "about-us", "aboutus", "about-me", "our-story", "story", "meet", "who-we-are", "team", "our-team", "the-team", "bio")
FORM_RX = re.compile(r"honeybook|dubsado|typeform|jotform|hubspot|formspree|cognitoforms|wufoo|17hats|studioninja|tave\.com|pixieset|"
                     r"wix-form|wixforms|contact-form-7|wpcf7|gravity ?forms|gform|ninja-forms|formidable|elementor-form|forminator|"
                     r"squarespace.*form|sqs-block-form|form-block|hbspt\.forms|calendly|acuityscheduling|zola\.com/wedding-vendors|"
                     r"theknot\.com/marketplace|weddingwire\.com/biz|thumbtack|gigsalad|bark\.com|houzz|mailchimp|klaviyo|iframe[^>]+form", re.I)
PRIOR_DEAD = {"http 404", "http 410", "ConnectionError", "ConnectTimeout", "InvalidURL", "MissingSchema", "InvalidSchema", "LocationParseError"}
MAX_SUBPAGES = 2


def _cf_decode(hexstr):
    try:
        b = bytes.fromhex(hexstr)
        k = b[0]
        return "".join(chr(c ^ k) for c in b[1:])
    except Exception:
        return ""


def clean(addr):
    """One candidate string -> a lower-cased address or ''."""
    a = unquote(unescape(addr or "")).strip().strip(".,;:()[]<>\"'").lower()
    a = a.split("?")[0].replace("mailto:", "")
    a = a.replace("[at]", "@").replace("(at)", "@").replace("{at}", "@").replace(" at ", "@")
    a = re.sub(r"\s*(?:\[\s*dot\s*\]|\(\s*dot\s*\)|\{\s*dot\s*\}|\s+dot\s+)\s*", ".", a)
    a = re.sub(r"\s+", "", a)
    if a.startswith("u003e"):
        a = a[5:]
    m = EMAIL_RX.search(a)
    if not m or m.group(0) != a:
        if not m:
            return ""
        a = m.group(0)
    if len(a) > 90 or a.count("@") != 1 or not VALID_TLD_RX.search(a) or JUNK_RX.search(a) or DESIGNER_RX.search(a):
        return ""
    local, dom = a.split("@")
    if len(local) < 2 or local.startswith(("-", ".", "_")) or len(dom) < 4 or re.fullmatch(r"[0-9.]+", dom):
        return ""
    # a hex or tracking-id local part is a bounce address or a web beacon, never a mailbox
    if re.fullmatch(r"[0-9a-f]{12,}", local) or re.fullmatch(r"[a-z0-9]{24,}", local):
        return ""
    return a


def _root(host):
    """'www.foo.co.uk' -> 'foo.co.uk', 'mail.foo.com' -> 'foo.com' (good enough for a match test)."""
    host = host.lower().lstrip(".")
    host = re.sub(r"^(?:www\d?|m|en|mail|info|site|home|web|shop|store|booking|book)\.", "", host)
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in ("co", "com", "net", "org", "ac", "gov") and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def score(addr, where, page, site_host):
    local, dom = addr.split("@")
    root_site, root_mail = _root(site_host), _root(dom)
    if root_site and (root_mail == root_site or root_mail.endswith("." + root_site) or root_site.endswith("." + root_mail)):
        s, kind = 60, "own-domain"
    elif dom in FREE_MAIL:
        s, kind = 35, "free-mail"
    else:
        s, kind = 18, "other-domain"
    base_local = re.sub(r"[0-9._-]", "", local)
    if base_local not in ROLE and not any(base_local.startswith(r) and len(base_local) - len(r) <= 2 for r in ("info", "hello", "contact", "booking", "inquir")):
        s += 10   # a person's mailbox
    s += {"mailto": 15, "cf": 15, "jsonld": 15, "text": 8, "obfuscated": 8, "raw": 0}.get(where, 0)
    s += {"home": 5, "contact": 6, "about": 3}.get(page, 0)
    return min(s, 100), kind


def emails_in(raw_html, soup, final_url):
    """[(addr, where)] from one page, in discovery order."""
    found = []
    seen = set()

    def add(cands, where):
        for c in cands:
            a = clean(c)
            if a and a not in seen:
                seen.add(a)
                found.append((a, where))

    add(MAILTO_RX.findall(raw_html), "mailto")
    for a in soup.find_all("a", href=True):
        if a["href"].lower().startswith("mailto:"):
            add([a["href"][7:]], "mailto")
    add([_cf_decode(h1 or h2) for h1, h2 in CF_RX.findall(raw_html)], "cf")
    for tag in soup.find_all("script", type="application/ld+json"):
        for m in re.finditer(r'"email"\s*:\s*"([^"]+)"', tag.string or ""):
            add([m.group(1)], "jsonld")
    text = soup.get_text(" ", strip=True)
    add(EMAIL_RX.findall(text), "text")
    add([f"{u}@{d}" for u, d in OBF_RX.findall(text)], "obfuscated")
    # attributes, data-*, inline JSON (Wix keeps the contact email in a script blob); lowest confidence
    add(EMAIL_RX.findall(raw_html), "raw")
    return found


def has_form(raw_html, soup):
    if FORM_RX.search(raw_html):
        return True
    for f in soup.find_all("form"):
        if f.find("textarea") or f.find("input", attrs={"type": "email"}) or f.find("input", attrs={"name": re.compile("email|message|phone", re.I)}):
            return True
    return False


def fetch_raw(url, timeout=12):
    """Same rules as site_facts.fetch, but hands back the RAW html too (mailto: and data-cfemail sit in markup)."""
    with requests.get(url, headers={"User-Agent": SF.UA, "Accept-Language": "en-US"}, timeout=timeout, allow_redirects=True, stream=True) as r:
        ct = r.headers.get("content-type", "")
        if r.status_code != 200 or "html" not in ct:
            return None, r.url, r.status_code
        body = b""
        for chunk in r.iter_content(65536):
            body += chunk
            if len(body) > SF.MAX_BYTES:
                break
        enc = r.encoding if r.encoding and r.encoding.lower() != "iso-8859-1" else None
        if not enc:
            m = re.search(rb'<meta[^>]+charset=["\']?([\w-]+)', body[:4096], re.I)
            enc = m.group(1).decode("ascii", "ignore") if m else "utf-8"
        try:
            html = body.decode(enc, errors="replace")
        except LookupError:
            html = body.decode("utf-8", errors="replace")
        return html, r.url, 200


def _subpages(soup, final, host):
    """{kind: url} for the contact and about pages linked from this page."""
    out = {}
    for a in soup.find_all("a", href=True):
        href = urljoin(final, a["href"].strip()).split("#")[0]
        p = urlparse(href)
        if p.scheme not in ("http", "https") or p.netloc.lower().replace("www.", "") != host:
            continue
        last = p.path.lower().rstrip("/").rsplit("/", 1)[-1].replace(".html", "").replace(".php", "").replace(".aspx", "")
        label = " ".join(a.get_text(" ", strip=True).lower().split())[:40]
        if "contact" not in out and (last in CONTACT_WORDS or label in ("contact", "contact us", "get in touch", "inquire", "inquiry", "book now", "let's talk", "say hello", "connect", "reach out")):
            out["contact"] = href
        elif "about" not in out and (last in ABOUT_WORDS or label in ("about", "about us", "about me", "our story", "meet the team", "the team")):
            out["about"] = href
    return out


def crawl_site(url):
    """One website -> result dict shared by every vendor that lists it."""
    out = {"url": url, "checked": date.today().isoformat(), "site": "dead", "emails": [], "form": False, "pages": []}
    try:
        if not SF._allowed(url):
            out["site"] = "robots"
            return out
        try:
            html, final, code = fetch_raw(url)
        except requests.exceptions.SSLError:
            p = urlparse(url)
            alt = p.netloc[4:] if p.netloc.startswith("www.") else "www." + p.netloc
            html, final, code = fetch_raw(f"{p.scheme}://{alt}{p.path or '/'}")
    except requests.exceptions.SSLError:
        out["why"] = "ssl"
        return out
    except Exception as e:
        out["why"] = type(e).__name__
        return out
    if not html:
        out["why"] = f"http {code}"
        return out
    out["final"] = final
    host = urlparse(final).netloc.lower().replace("www.", "")
    out["host"] = host
    slim = SF._slim(html)
    soup = BeautifulSoup(slim, "lxml")
    title = (soup.title.get_text(" ", strip=True) if soup.title else "")[:160]
    raw_text = soup.get_text(" ", strip=True)[:4000]
    if SF.PARKED.search(raw_text) and len(raw_text.split()) < 400:
        out["parked"] = True
    if SF.SPAM.search(title + " " + raw_text[:1500]):
        out["hijacked"] = True
    out["wedding_hits"] = len(SF.WEDDING.findall(raw_text + " " + title))
    found = {}   # addr -> (where, page)
    form = False
    pages = [("home", final, html, soup)]
    out["pages"].append("home")
    subs = _subpages(soup, final, host)
    for kind, _, h, s in pages:
        for addr, where in emails_in(h, s, final):
            found.setdefault(addr, (where, kind))
        form = form or has_form(h, s)

    def own(a):
        return score(a, "mailto", "home", host)[1] == "own-domain"

    # the contact page is worth a visit unless the home page already gave the business's own address by mailto
    need_more = not any(own(a) and found[a][0] in ("mailto", "cf", "jsonld") for a in found)
    for kind in ("contact", "about"):
        u = subs.get(kind)
        if not u or not need_more or u.rstrip("/") == final.rstrip("/") or len(out["pages"]) > MAX_SUBPAGES:
            continue
        try:
            if not SF._allowed(u):
                continue
            time.sleep(0.3)
            h2, f2, _ = fetch_raw(u)
            if not h2:
                continue
            s2 = BeautifulSoup(SF._slim(h2), "lxml")
            out["pages"].append(kind)
            for addr, where in emails_in(h2, s2, f2):
                found.setdefault(addr, (where, kind))
            form = form or has_form(h2, s2)
            if any(own(a) for a in found):
                need_more = False
        except Exception:
            pass
    rows = []
    for addr, (where, page) in found.items():
        s, kind = score(addr, where, page, host)
        rows.append({"addr": addr, "score": s, "kind": kind, "where": where, "page": page})
    rows.sort(key=lambda r: -r["score"])
    out["emails"] = rows[:6]
    out["form"] = form
    out["title"] = title
    if out.get("parked") or out.get("hijacked"):
        out["site"] = "parked" if out.get("parked") else "hijacked"
    elif rows:
        out["site"] = "ok"
    elif form:
        out["site"] = "form_only"
    else:
        out["site"] = "no_contact"
    return out


# ---- the vendor list ---------------------------------------------------------------------------------------------
def pull_vendors():
    import firebase_admin
    from firebase_admin import credentials, firestore
    cred = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or r"C:\Users\kurvh\secrets\lazo-513ec-admin.json"
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(cred))
    db = firestore.client()
    paths = json.loads(PATHS_FILE.read_text(encoding="utf-8"))["paths"]
    by_pid = defaultdict(dict)
    for k, p in paths.items():
        pid, cat = k.split("|", 1)
        by_pid[pid][cat] = p
    rows, n_all, n_claimed, n_delisted, n_nosite, n_unlisted = {}, 0, 0, 0, 0, 0
    fields = ["name", "website", "categories", "delisted", "claimedBy", "claimStatus", "metroId", "address", "phone", "email", "slug", "travelFrom"]
    for doc in db.collection("vendors").select(fields).stream():
        v = doc.to_dict()
        n_all += 1
        if v.get("delisted"):
            n_delisted += 1
            continue
        if v.get("claimedBy") or v.get("claimStatus") == "claimed":
            n_claimed += 1
            continue
        url = SF.norm_url(v.get("website") or "")
        if not url:
            n_nosite += 1
            continue
        pages = by_pid.get(doc.id)
        if not pages:
            n_unlisted += 1
            continue
        cats = [c for c in (v.get("categories") or []) if c in pages] or list(pages)
        rows[doc.id] = {"id": doc.id, "name": v.get("name") or "", "metroId": v.get("metroId") or "", "categories": cats,
                        "website": url, "pageUrl": SITE + pages[cats[0]], "pages": pages, "city": SF._town(v.get("address") or ""),
                        "phone": v.get("phone") or "", "placesEmail": v.get("email") or ""}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    meta = {"pulled": datetime.now().isoformat(timespec="seconds"), "vendorsInFirestore": n_all, "delisted": n_delisted, "claimed": n_claimed,
            "noUsableWebsite": n_nosite, "notPublished": n_unlisted, "toContact": len(rows)}
    VENDORS_FILE.write_text(json.dumps({"meta": meta, "vendors": rows}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps(meta, indent=1))
    return rows


def load_vendors():
    if not VENDORS_FILE.exists():
        return pull_vendors()
    return json.loads(VENDORS_FILE.read_text(encoding="utf-8"))["vendors"]


def prior_facts(mid):
    p = FACTS_DIR / f"{mid}.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))["vendors"]


def _save(path, mid, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"metro": mid, "updated": datetime.now().isoformat(timespec="seconds"), "vendors": data},
                              ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(path)


def run_metro(mid, vendors, a):
    path = OUT_DIR / f"{mid}.json"
    data = json.loads(path.read_text(encoding="utf-8"))["vendors"] if path.exists() else {}
    facts = prior_facts(mid)
    jobs = {}
    skipped = 0
    for v in vendors:
        if v["id"] in data and not a.refresh:
            continue
        pf = facts.get(v["id"])
        if pf and not a.refresh and pf.get("url") == v["website"]:
            # site_facts already found the site dead, parked or hijacked: no second visit
            why = pf.get("why")
            if (not pf.get("ok") and why in PRIOR_DEAD) or pf.get("parked") or pf.get("hijacked"):
                data[v["id"]] = {"url": v["website"], "checked": pf.get("checked"), "site": "parked" if pf.get("parked") else "hijacked" if pf.get("hijacked") else "dead",
                                 "why": why or ("parked" if pf.get("parked") else "hijacked"), "emails": [], "form": False, "pages": [], "prior": True}
                skipped += 1
                continue
        j = jobs.setdefault(v["website"], {"url": v["website"], "ids": []})
        j["ids"].append(v["id"])
    todo = list(jobs.values())[: a.limit or None]
    print(f"{mid}: {len(vendors):,} vendors to contact, {len(set(v['website'] for v in vendors)):,} distinct sites, "
          f"{skipped:,} known dead/parked, {len(todo):,} sites to visit", flush=True)
    if not todo:
        _save(path, mid, data)
        return
    t0, done = time.time(), 0
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(crawl_site, j["url"]): j for j in todo}
        for f in as_completed(futs):
            j = futs[f]
            try:
                r = f.result()
            except Exception as e:
                r = {"url": j["url"], "checked": date.today().isoformat(), "site": "dead", "why": type(e).__name__, "emails": [], "form": False, "pages": []}
            for vid in j["ids"]:
                data[vid] = r
            done += 1
            if done % 200 == 0:
                _save(path, mid, data)
                print(f"  {done:,}/{len(todo):,} sites, {time.time() - t0:.0f}s", flush=True)
    _save(path, mid, data)
    c = Counter(r["site"] for r in data.values())
    print(f"  {mid}: {len(data):,} vendors - {c.get('ok', 0):,} with an email, {c.get('form_only', 0):,} form only, {c.get('no_contact', 0):,} no contact, "
          f"{c.get('dead', 0):,} dead, {c.get('robots', 0):,} robots, {c.get('parked', 0) + c.get('hijacked', 0):,} parked/hijacked  ({time.time() - t0:.0f}s)", flush=True)


# ---- summary + push ----------------------------------------------------------------------------------------------
def _best(r):
    em = r.get("emails") or []
    return em[0] if em else None


def iter_results(vendors):
    by_metro = defaultdict(list)
    for v in vendors.values():
        by_metro[v["metroId"]].append(v)
    shared = Counter(v["website"] for v in vendors.values())
    for mid, vs in by_metro.items():
        p = OUT_DIR / f"{mid}.json"
        data = json.loads(p.read_text(encoding="utf-8"))["vendors"] if p.exists() else {}
        for v in vs:
            yield mid, v, data.get(v["id"]), shared[v["website"]]


def summary(vendors):
    met = defaultdict(Counter)
    cat = defaultdict(Counter)
    kinds = Counter()
    rows = []
    for mid, v, r, sh in iter_results(vendors):
        site = r["site"] if r else "pending"
        b = _best(r) if r else None
        for bucket in (met[mid], cat[v["categories"][0]]):
            bucket["vendors"] += 1
            bucket["checked"] += bool(r)
            bucket["fetched"] += bool(r and r["site"] in ("ok", "form_only", "no_contact"))
            bucket["email"] += bool(b)
            bucket["own_domain"] += bool(b and b["kind"] == "own-domain")
            bucket["form_only"] += site == "form_only"
            bucket["no_contact"] += site == "no_contact"
            bucket["dead"] += site in ("dead", "robots", "parked", "hijacked")
            bucket["shared_site"] += sh > 1
        if b:
            kinds[b["kind"]] += 1
        rows.append([v["id"], v["name"], mid, v["categories"][0], v["pageUrl"], v["website"], site, b["addr"] if b else "",
                     b["score"] if b else "", b["kind"] if b else "", b["where"] if b else "", len(r.get("emails") or []) if r else 0,
                     int(bool(r and r.get("form"))), sh, int(bool(r and r.get("wedding_hits") == 0)), v["city"], v["phone"]])
    cols = ["vendors", "checked", "fetched", "email", "own_domain", "form_only", "no_contact", "dead", "shared_site"]
    for name, table in (("_summary_by_metro.csv", met), ("_summary_by_category.csv", cat)):
        with (OUT_DIR / name).open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["key"] + cols + ["email_pct_of_fetched"])
            for k in sorted(table, key=lambda k: -table[k]["vendors"]):
                t = table[k]
                w.writerow([k] + [t[c] for c in cols] + [f"{100 * t['email'] / t['fetched']:.0f}%" if t["fetched"] else ""])
    with (OUT_DIR / "_all.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["vendorId", "name", "metro", "category", "pageUrl", "website", "site", "bestEmail", "score", "kind", "where", "emailsFound",
                    "hasForm", "sharedBy", "noWeddingMention", "city", "phone"])
        w.writerows(rows)
    tot = Counter()
    for t in met.values():
        tot.update(t)
    print(json.dumps({"totals": dict(tot), "bestEmailKind": dict(kinds)}, indent=1))
    return tot


def push(vendors):
    import firebase_admin
    from firebase_admin import credentials, firestore
    cred = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or r"C:\Users\kurvh\secrets\lazo-513ec-admin.json"
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(cred))
    db = firestore.client()
    col = db.collection("outreach")
    existing = {d.id: d.to_dict() for d in col.select(["token", "status"]).stream()}
    batch, n, w = db.batch(), 0, 0
    for mid, v, r, sh in iter_results(vendors):
        if not r:
            continue
        old = existing.get(v["id"]) or {}
        b = _best(r)
        doc = {"vendorId": v["id"], "name": v["name"], "metroId": mid, "categories": v["categories"], "pageUrl": v["pageUrl"], "website": v["website"],
               "siteHost": r.get("host") or urlparse(v["website"]).netloc.replace("www.", ""), "site": r["site"], "emails": r.get("emails") or [],
               "best": b["addr"] if b else None, "form": bool(r.get("form")), "sharedBy": sh,
               "flags": {"noWedding": r.get("wedding_hits") == 0, "parked": bool(r.get("parked")), "hijacked": bool(r.get("hijacked"))},
               "token": old.get("token") or secrets.token_urlsafe(16), "status": old.get("status") or "listed",
               "checkedAt": r.get("checked"), "updatedAt": firestore.SERVER_TIMESTAMP}
        if not old:
            doc["createdAt"] = firestore.SERVER_TIMESTAMP
        batch.set(col.document(v["id"]), doc, merge=True)
        n += 1
        if n % 400 == 0:
            batch.commit()
            batch = db.batch()
            w += 400
            if w % 10000 == 0:
                print(f"  {w:,} written", flush=True)
    batch.commit()
    print(f"outreach: {n:,} docs written")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--vendors", action="store_true", help="pull the unclaimed list from Firestore again")
    ap.add_argument("--metro", action="append")
    ap.add_argument("--all", action="store_true", help="every metro, largest first")
    ap.add_argument("--workers", type=int, default=32)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--push", action="store_true")
    a = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    vendors = pull_vendors() if a.vendors else load_vendors()
    by_metro = defaultdict(list)
    for v in vendors.values():
        by_metro[v["metroId"]].append(v)
    if a.metro or a.all:
        ids = a.metro or sorted(by_metro, key=lambda m: -len(by_metro[m]))
        for mid in ids:
            if mid not in by_metro:
                print(f"{mid}: no vendors to contact")
                continue
            run_metro(mid, by_metro[mid], a)
    if a.summary:
        summary(vendors)
    if a.push:
        push(vendors)


if __name__ == "__main__":
    main()
