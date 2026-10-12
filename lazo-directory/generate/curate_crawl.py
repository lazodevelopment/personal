"""curate_crawl.py - JC-LAZO-CURATE-1012: gather the raw material for curated city x category picks.

Reads the vendors of one metro (the categories in config/city_guides.GUIDE_CATS) from Firestore, visits each
vendor's own website (home page plus an about / pricing page when linked), and writes one JSON with what the
site actually says: title, description, headings, the first stretch of body text, the about text, years in
business, prices mentioned, social links. Nothing is invented here; the picks and blurbs are written later from
these extracts only.

    python generate\\curate_crawl.py phoenix [out.json]
"""
import json, os, re, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from config.city_guides import GUIDE_CATS  # noqa: E402

UA = "Mozilla/5.0 (compatible; LazoBot/1.0; +https://meetlazo.com/for-vendors/)"
ABOUT_WORDS = ("about", "our-story", "story", "meet", "team", "who-we-are")
PRICE_WORDS = ("pricing", "investment", "packages", "rates", "collections", "services")
SOCIAL = ("instagram.com", "facebook.com", "vimeo.com", "youtube.com", "tiktok.com", "theknot.com", "weddingwire.com", "zola.com")


def load_vendors(metro):
    import firebase_admin
    from firebase_admin import credentials, firestore
    cred = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or r"C:\Users\kurvh\secrets\lazo-513ec-admin.json"
    firebase_admin.initialize_app(credentials.Certificate(cred))
    db = firestore.client()
    out = []
    for doc in db.collection("vendors").where("metroId", "==", metro).stream():
        v = doc.to_dict()
        if v.get("delisted"):
            continue
        cats = [c for c in (v.get("categories") or []) if c in GUIDE_CATS]
        if not cats:
            continue
        out.append({"id": doc.id, "name": v.get("name", ""), "website": (v.get("website") or "").strip(), "address": v.get("address", ""),
                    "phone": v.get("phone", ""), "categories": cats, "verified": bool(v.get("verified")), "claimed": bool(v.get("claimedBy")),
                    "travelFrom": v.get("travelFrom"), "bio": v.get("bio") or "", "startingPrice": v.get("startingPrice"), "priceRangeDisplay": v.get("priceRangeDisplay"),
                    "lat": v.get("lat"), "lng": v.get("lng"), "reviewCount": v.get("reviewCount") or 0, "score": v.get("score")})
    return out


def text_of(soup, limit):
    for t in soup(["script", "style", "noscript", "svg", "nav", "footer", "header", "form"]):
        t.decompose()
    chunks = []
    for el in soup.find_all(["p", "li", "h1", "h2", "h3", "blockquote"]):
        s = " ".join(el.get_text(" ", strip=True).split())
        if len(s) >= 40:
            chunks.append(s)
    out = " ".join(chunks)
    return out[:limit]


def fetch(url, timeout=12):
    r = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "en-US"}, timeout=timeout, allow_redirects=True)
    ct = r.headers.get("content-type", "")
    if r.status_code != 200 or "html" not in ct:
        return None, r.status_code
    return r.text, r.status_code


def signals(text):
    t = text
    years = sorted({int(y) for y in re.findall(r"(?:since|established|est\.?|founded)\s*(?:in\s*)?((?:19|20)\d{2})", t, re.I) if 1950 <= int(y) <= 2026})
    yrs = [int(n) for n in re.findall(r"(\d{1,2})\+?\s*years?\s+(?:of\s+)?(?:experience|in business|shooting|photographing|filming|planning)", t, re.I)]
    prices = re.findall(r"\$\s?(\d{1,3}(?:,\d{3})+|\d{3,5})(?!\d)", t)
    prices = sorted({int(p.replace(",", "")) for p in prices if 100 <= int(p.replace(",", "")) <= 50000})
    return {"since": years[:2], "years": yrs[:2], "prices": prices[:8]}


def crawl_one(v):
    out = {"id": v["id"], "ok": False}
    url = v["website"]
    if not url:
        out["why"] = "no website"
        return out
    if not re.match(r"^https?://", url):
        url = "https://" + url
    try:
        html, code = fetch(url)
    except Exception as e:
        out["why"] = f"{type(e).__name__}"
        return out
    if not html:
        out["why"] = f"http {code}"
        return out
    soup = BeautifulSoup(html, "lxml")
    host = urlparse(url).netloc.lower().replace("www.", "")
    links = {}
    socials = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(url, a["href"])
        h = urlparse(href).netloc.lower().replace("www.", "")
        if any(s in h for s in SOCIAL):
            socials.add(href.split("?")[0])
            continue
        if h != host:
            continue
        path = urlparse(href).path.lower()
        for w in ABOUT_WORDS:
            if w in path and "about" not in links:
                links["about"] = href
        for w in PRICE_WORDS:
            if w in path and "price" not in links:
                links["price"] = href
    title = (soup.title.get_text(" ", strip=True) if soup.title else "")[:160]
    md = soup.find("meta", attrs={"name": "description"})
    desc = (md.get("content", "") if md else "")[:300]
    h1 = [h.get_text(" ", strip=True)[:120] for h in soup.find_all("h1")][:3]
    h2 = [h.get_text(" ", strip=True)[:100] for h in soup.find_all("h2")][:8]
    home_text = text_of(soup, 1800)
    about_text, price_text = "", ""
    for key, limit in (("about", 1400), ("price", 900)):
        if key in links:
            try:
                h2_, _ = fetch(links[key])
                if h2_:
                    t = text_of(BeautifulSoup(h2_, "lxml"), limit)
                    if key == "about":
                        about_text = t
                    else:
                        price_text = t
            except Exception:
                pass
    sig = signals(" ".join([home_text, about_text, price_text, desc]))
    out.update({"ok": True, "url": url, "title": title, "desc": desc, "h1": h1, "h2": h2, "home": home_text, "about": about_text,
                "price_page": price_text, "socials": sorted(socials)[:6], "signals": sig, "has_about": bool(about_text), "has_price": bool(price_text)})
    return out


def main():
    metro = sys.argv[1] if len(sys.argv) > 1 else "phoenix"
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "generate" / "data" / "curated-raw" / f"{metro}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    vendors = load_vendors(metro)
    print(f"{metro}: {len(vendors)} vendors in guide categories, {sum(1 for v in vendors if v['website'])} with a website", flush=True)
    t0 = time.time()
    results = {}
    with ThreadPoolExecutor(max_workers=16) as ex:
        futs = {ex.submit(crawl_one, v): v["id"] for v in vendors}
        for i, f in enumerate(as_completed(futs), 1):
            r = f.result()
            results[r["id"]] = r
            if i % 100 == 0:
                print(f"  {i}/{len(vendors)} crawled, {time.time() - t0:.0f}s", flush=True)
    ok = sum(1 for r in results.values() if r["ok"])
    print(f"done: {ok} sites read, {len(results) - ok} unreachable or without a site, {time.time() - t0:.0f}s")
    out_path.write_text(json.dumps({"metro": metro, "vendors": vendors, "sites": results}, ensure_ascii=False), encoding="utf-8")
    print("wrote", out_path)


if __name__ == "__main__":
    main()
