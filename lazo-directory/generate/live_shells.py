r"""live_shells.py - JC-LAZO-LIVEPAGE-1014
A vendor page must exist the moment a listing is approved, not after the
nightly build. This renders vendor.html once per metro x category for a
placeholder vendor whose name, id and slug are tokens, into
dist/_live/shell/<metro>/<category>.html. When a vendor URL has no built page,
the worker (worker/src/index.js, livePage) finds the vendor in Firestore, puts
its name, id and slug in place of the tokens and serves it; the page's own
live hydration then fills every field the vendor edited (photos, packages,
owner, prices, socials, FAQs). Pages that exist already hydrate the same way,
so a vendor's edits show on their page immediately either way.

The worker never serves _* keys, so the shells are not public URLs.

    python generate\live_shells.py          # writes dist/_live/shell (about 1,600 files)

Run by the nightly after build.py and uploaded with the rest of dist/.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generate"))
sys.path.insert(0, str(ROOT))

import build  # noqa: E402  (module-level setup only; build() is not called)
from build import env, BASE_URL, BY_ID, METROS, CATEGORIES, BY_SLUG, FAQS, GENERIC_FAQ, _COST_TYPICAL, DIST  # noqa: E402

NAME, PID, SLUG = "ZZLZNAMEZZ", "ZZLZIDZZ", "zzlzslugzz"


def placeholder(metro, cat):
    c = BY_SLUG[cat]
    faqs = [(q.format(metro=metro["name"], category_plural=c["label"].lower(), category_singular=c["singular"].lower()),
             a.format(metro=metro["name"], category_plural=c["label"].lower(), category_singular=c["singular"].lower()))
            for q, a in FAQS.get(cat, []) + GENERIC_FAQ]
    return {
        "name": NAME, "placeId": PID, "slug": SLUG, "metroId": metro["id"], "categories": [cat],
        "claimStatus": "claimed", "claimedBy": "live", "verified": False,
        "score": build.PRIOR_SCORE, "reviewCount": 0, "faqs": faqs, "faqs_here": faqs, "faqs_by_cat": {cat: faqs},
        "near_venues": [], "related": [], "around": [], "areaServed": [], "also_cats": [], "peers_here": [],
        "locality": "", "place_note": "", "intro": "", "gallery": [], "packages": [], "social_links": [],
    }


def main():
    env.globals["asset_v"] = build._asset_version()
    built = [m for m in METROS if (DIST / m["id"] / "index.html").is_file()]
    env.globals["foot_metros"] = [{"id": m["id"], "name": m["name"]} for m in built]
    env.globals["foot_cats"] = [{"slug": c["slug"], "label": c["label"]} for c in CATEGORIES]
    t = env.get_template("vendor.html")
    out = DIST / "_live" / "shell"
    n = 0
    for m in built:
        d = out / m["id"]
        d.mkdir(parents=True, exist_ok=True)
        for c in CATEGORIES:
            html = t.render(metro=m, cat=c, v=placeholder(m, c["slug"]), base=BASE_URL, hotels=[],
                            cost_typical=_COST_TYPICAL.get(c["slug"]), cat_total=0, noindex=False)
            (d / f"{c['slug']}.html").write_text(html, encoding="utf-8")
            n += 1
    print(f"[live] {n} vendor page shells -> {out}")


if __name__ == "__main__":
    main()
