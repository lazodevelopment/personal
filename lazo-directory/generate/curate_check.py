"""curate_check.py - JC-LAZO-CURATE-1012: guardrails on curated picks before they ship.

    python generate\\curate_check.py [metro ...]      (default: every metro with a curated folder)

For every <metro>/<cat>.json: 6-12 picks, every pick id in the crawl, blurbs 120-480 chars, a dollar amount in a
blurb or from_price must appear in that vendor's crawled text, a `since` year must appear there too, and no
superlatives Lazo cannot back ("best-rated", "top-rated", "5-star", "award-winning" unless the site says so).
Exit code 1 if anything fails; prints every problem.
"""
import json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CURATED = HERE / "data" / "curated"
RAW = HERE / "data" / "curated-raw"
SUPER = re.compile(r"\b(best[- ]rated|top[- ]rated|5[- ]star|five[- ]star|#1|number one|award[- ]winning|highest[- ]rated)\b", re.I)


def raw_vendor(raw, vid):
    return next((v for v in raw["vendors"] if v["id"] == vid), {})


def check_metro(metro):
    problems = []
    raw = json.loads((RAW / f"{metro}.json").read_text(encoding="utf-8"))
    sites = raw["sites"]
    files = sorted((CURATED / metro).glob("*.json"))
    if len(files) < 6:
        problems.append(f"{metro}: only {len(files)} category files")
    for f in files:
        doc = json.loads(f.read_text(encoding="utf-8"))
        cat = doc["cat"]
        picks = doc.get("picks", [])
        if not 6 <= len(picks) <= 12:
            problems.append(f"{metro}/{cat}: {len(picks)} picks (want 6-12)")
        if len(doc.get("ask", [])) != 3:
            problems.append(f"{metro}/{cat}: {len(doc.get('ask', []))} ask questions (want 3)")
        seen = set()
        for p in picks:
            tag = f"{metro}/{cat}/{p['name']}"
            if p["id"] in seen:
                problems.append(f"{tag}: duplicate pick")
            seen.add(p["id"])
            s = sites.get(p["id"], {})
            if not s.get("ok"):
                problems.append(f"{tag}: site was not readable in the crawl")
                continue
            text = " ".join([s.get("title", ""), s.get("desc", ""), " ".join(s.get("h1", []) + s.get("h2", [])), s.get("about", ""), s.get("home", ""), s.get("price_page", "")])
            b = p["blurb"]
            if not 120 <= len(b) <= 480:
                problems.append(f"{tag}: blurb {len(b)} chars")
            if not 1 <= len(p.get("tags", [])) <= 4:
                problems.append(f"{tag}: {len(p.get('tags', []))} tags")
            lazo_price = str(raw_vendor(raw, p["id"]).get("startingPrice") or "")
            nums = set(re.findall(r"\$\s?(\d[\d,]*)", b + " " + (p.get("from_price") or "")))
            for n in nums:
                if n.replace(",", "") not in {str(x) for x in s["signals"]["prices"]} and n not in text.replace(",", "") and n not in text and n not in lazo_price:
                    problems.append(f"{tag}: ${n} not found on the vendor's site")
            if p.get("since") and str(p["since"]) not in text:
                problems.append(f"{tag}: since {p['since']} not found on the vendor's site")
            m = SUPER.search(b)
            if m and not re.search(re.escape(m.group(0)), text, re.I):
                problems.append(f"{tag}: '{m.group(0)}' is not on the vendor's site")
    return problems


def main():
    metros = sys.argv[1:] or sorted(p.name for p in CURATED.iterdir() if p.is_dir())
    bad = 0
    for m in metros:
        probs = check_metro(m)
        bad += len(probs)
        for p in probs:
            print("PROBLEM", p)
        print(f"{m}: {'ok' if not probs else str(len(probs)) + ' problems'}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
