"""curate_emit.py - JC-LAZO-CURATE-1012: turn a writer's picks file into the JSON the site generator reads.

A picks file is generate/data/curated/<metro>.py exposing CATS = {cat_slug: dict(excluded=str, ask=[3 str],
picks=[dict(id, tags[list], blurb, since?, from_price?)])}. This resolves each id against the crawl
(generate/data/curated-raw/<metro>.json) for the name, website, Instagram and verified flags, and writes
generate/data/curated/<metro>/<cat>.json.

    python generate\\curate_emit.py <metro>
"""
import importlib.util, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CURATED = HERE / "data" / "curated"
RAW = HERE / "data" / "curated-raw"

LABEL = {"wedding-venues": "wedding venue", "wedding-photographers": "wedding photographer", "wedding-videographers": "wedding videographer",
         "wedding-planners": "wedding planner", "wedding-florists": "wedding florist", "wedding-djs": "wedding DJ"}

HOW = ("We read the website of every {metro} {cat} listed on Lazo ({n} listings, {ok} sites reachable) and "
       "set aside the ones that are not really in the wedding business: {excluded}. What is left is a shortlist "
       "of vendors who say clearly what they do, show their work, and tell you how they work. Verified Lazo "
       "vendors come first. Nobody paid to be here, and this is not a ranking: Lazo ranks only on reviews "
       "from couples who booked.")


def metro_name(metro_id):
    sys.path.insert(0, str(HERE.parent))
    from config.metros import METROS
    return next((m["name"] for m in METROS if m["id"] == metro_id), metro_id.replace("-", " ").title())


def emit(metro, CATS, updated):
    raw = json.loads((RAW / f"{metro}.json").read_text(encoding="utf-8"))
    vendors = {v["id"]: v for v in raw["vendors"]}
    sites = raw["sites"]
    out_dir = CURATED / metro
    out_dir.mkdir(parents=True, exist_ok=True)
    name = metro_name(metro)
    report = []
    for cat, c in CATS.items():
        n = sum(1 for v in raw["vendors"] if cat in v["categories"])
        ok = sum(1 for v in raw["vendors"] if cat in v["categories"] and sites.get(v["id"], {}).get("ok"))
        picks = []
        for p in c["picks"]:
            if p["id"] not in vendors:
                raise SystemExit(f"{metro}/{cat}: pick id {p['id']} is not in the crawl")
            v = vendors[p["id"]]
            s = sites.get(p["id"], {})
            ig = next((x.split("instagram.com/")[-1].strip("/") for x in s.get("socials", [])
                       if "instagram.com/" in x and "/p/" not in x and x.split("instagram.com/")[-1].strip("/") not in ("wix", "", "accounts/login")), "")
            picks.append(dict(id=p["id"], name=v["name"], website=s.get("url") or v["website"], instagram=ig, tags=p["tags"], blurb=p["blurb"],
                              since=p.get("since"), from_price=p.get("from_price"), verified=v["verified"], claimed=v["claimed"]))
        doc = dict(metro=metro, cat=cat, updated=updated, read=ok, listed=n,
                   how=HOW.format(metro=name, cat=LABEL[cat], n=n, ok=ok, excluded=c["excluded"]), ask=c["ask"], picks=picks)
        (out_dir / f"{cat}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
        report.append(f"{cat}: {len(picks)} picks ({ok} of {n} sites read)")
    return report


def main():
    metro = sys.argv[1]
    spec = importlib.util.spec_from_file_location(f"curated_{metro}", CURATED / f"{metro}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for line in emit(metro, mod.CATS, getattr(mod, "UPDATED", "2026-10-12")):
        print(metro, line)


if __name__ == "__main__":
    main()
