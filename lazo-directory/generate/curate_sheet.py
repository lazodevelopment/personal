"""curate_sheet.py - JC-LAZO-CURATE-1012: the candidate sheet a writer reads before choosing picks.

    python generate\\curate_sheet.py <metro> [out.txt]

Reads generate/data/curated-raw/<metro>.json (from curate_crawl.py), scores every readable site for wedding
relevance, drops link pages and parked domains, and prints the top candidates per category with the facts the
site states: title, description, headings, years, prices seen, Instagram, and the first stretch of about/home
text. Picks are written from this sheet only.
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from config.city_guides import GUIDE_CATS  # noqa: E402

WED = re.compile(r"\b(wedding|weddings|bride|brides|bridal|couple|couples|elopement|ceremony|reception|newlywed)\b", re.I)
OFF = re.compile(r"\b(headshot|headshots|newborn|corporate video|podcast|commercial|brand film|real estate|quincea|mitzvah|sound stage|recording studio|alumni|marketing agency|festival stage|cake smash|boudoir|funeral|sympathy)\b", re.I)
TOP = 26


def town(a):
    m = re.search(r",\s*([A-Za-z .'-]+),\s*[A-Z]{2}\b", a or "")
    return m.group(1).strip() if m else ""


def main():
    metro = sys.argv[1]
    d = json.loads((ROOT / "generate" / "data" / "curated-raw" / f"{metro}.json").read_text(encoding="utf-8"))
    sites = d["sites"]
    out = []
    for cat in GUIDE_CATS:
        rows = []
        for v in d["vendors"]:
            if cat not in v["categories"]:
                continue
            s = sites.get(v["id"], {})
            if not s.get("ok"):
                continue
            blob = " ".join([s.get("title", ""), s.get("desc", ""), " ".join(s.get("h1", []) + s.get("h2", [])), s.get("about", ""), s.get("home", ""), s.get("price_page", "")])
            wed, off = len(WED.findall(blob)), len(OFF.findall(blob))
            if "linktr.ee" in s.get("url", "") or re.search(r"godaddy|domain for sale|example page", s.get("title", "") + s.get("desc", ""), re.I):
                continue
            if wed < 2:
                continue
            sc = (6 * (v["verified"] or v["claimed"]) + min(wed, 20) / 4 - 1.5 * min(off, 4) + 2 * s["has_about"] + 1.5 * s["has_price"]
                  + min(len(blob), 2500) / 1250 + bool(s["signals"]["since"] or s["signals"]["years"]) + bool(s["socials"]) - 2 * bool(v["travelFrom"]))
            rows.append((sc, wed, off, v, s))
        rows.sort(key=lambda r: -r[0])
        n_all = sum(1 for v in d["vendors"] if cat in v["categories"])
        n_ok = sum(1 for v in d["vendors"] if cat in v["categories"] and sites.get(v["id"], {}).get("ok"))
        out.append(f"\n######## {cat}  ({n_all} listings, {n_ok} sites readable, {len(rows)} wedding-relevant; top {min(TOP, len(rows))} below)")
        for sc, wed, off, v, s in rows[:TOP]:
            body = (s.get("about") or s.get("home") or "")[:460].replace("\n", " ")
            pp = (s.get("price_page") or "")[:180].replace("\n", " ")
            ig = [x.split("instagram.com/")[-1].strip("/") for x in s["socials"] if "instagram.com/" in x and "/p/" not in x]
            out.append(f"\n## {v['name']} | id={v['id']} | {town(v['address'])} | {'VERIFIED ' if v['verified'] else ''}{'CLAIMED' if v['claimed'] else ''} | {s['url']}\n"
                       f"   title: {s['title'][:100]} | desc: {s['desc'][:170]}\n"
                       f"   h: {' / '.join((s['h1'] + s['h2'])[:5])[:200]}\n"
                       f"   sig: since={s['signals']['since']} yrs={s['signals']['years']} $={s['signals']['prices'][:6]} ig={ig[:1]}"
                       f"{(' lazo_bio: ' + v['bio'][:140]) if v.get('bio') else ''}{(' lazo_price: ' + str(v['startingPrice'])) if v.get('startingPrice') else ''}\n"
                       f"   text: {body}{(' | PRICE PAGE: ' + pp) if pp else ''}")
    text = "\n".join(out)
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(text, encoding="utf-8")
        print("wrote", sys.argv[2], len(text), "chars")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(text)


if __name__ == "__main__":
    main()
