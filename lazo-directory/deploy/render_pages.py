r"""Re-render the standalone pages into dist/ without a full rebuild.  JC-LAZO-CFORM-0916-001

The marketing, legal and story pages (about, contact, delete-account, privacy,
terms, the comparison pages, what-is-a-lazo) don't depend on Firestore at all -
they're static templates. A full `python generate\build.py` renders 87,000 vendor
pages to change three of them, which is the reason copy edits to these pages kept
waiting for a nightly. This renders just these, exactly as build.py would, into
the existing dist/.

    python deploy\render_pages.py               # render them all
    python deploy\render_pages.py --check       # report only, change nothing
    python deploy\render_pages.py about contact # just these

Then, as with a footer change:

    python deploy\bump_assets.py                # css/js stamp, sitewide
    python deploy\deploy_site.py --skip-build   # sync to R2 + purge

The footer is rendered contextually here the same way build.py and swap_footer.py
do it, from the cities that actually have a page in dist/, so these pages never
link a metro that isn't live.
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DIST = ROOT / "dist"
TPL = ROOT / "generate" / "templates"

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config.metros import METROS, BY_ID
from config.taxonomy import CATEGORIES
from config.cost_guides import GUIDES as COST_GUIDES

BASE_URL = "https://meetlazo.com"

# Must stay in step with build.py's STATIC_PAGES. Each renders to /<slug>/index.html.
STATIC_PAGES = [
    "why-lazo", "for-vendors", "about", "contact", "delete-account", "terms", "privacy",
    "the-knot-alternative", "zola-alternative", "weddingwire-alternative",
    "the-knot-alternative-for-vendors", "weddingwire-alternative-for-vendors",
    "honeybook-alternative",
]
# Standalone templates that aren't under pages/: template name -> output directory.
STANDALONE = {"lazo_tradition.html": "what-is-a-lazo"}


def live_metros():
    """Only cities with a built page - the footer must never link one that doesn't."""
    return [m for m in METROS if (DIST / m["id"] / "index.html").is_file()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("only", nargs="*", help="page slugs to render (default: all)")
    ap.add_argument("--check", action="store_true", help="report what would change, write nothing")
    ap.add_argument("--force", action="store_true", help="write even while an rclone sync is running")
    args = ap.parse_args()

    if not DIST.is_dir():
        sys.exit("dist/ not found - run a full build first")
    # JC-LAZO-DISTLOCK-0917-001: never rewrite dist/ under a live sync
    sys.path.insert(0, str(ROOT / "deploy"))
    from distlock import guard
    guard(force="--force" in sys.argv or args.check)

    metros = live_metros()
    if not metros:
        sys.exit("dist/ has no metro pages - refusing to render a footer with no cities in it")

    env = Environment(loader=FileSystemLoader(TPL), autoescape=select_autoescape(["html"]))
    # Same stamp build.py computes, so a page rendered here agrees with the rest of
    # the site. bump_assets.py rewrites it sitewide afterwards either way.
    sys.path.insert(0, str(ROOT / "deploy"))
    from bump_assets import asset_version
    env.globals["asset_v"] = asset_version()
    env.globals["foot_metros"] = [{"id": m["id"], "name": m["name"]} for m in metros]
    env.globals["foot_cats"] = [{"slug": c["slug"], "label": c["label"]} for c in CATEGORIES]

    # build.py derives this from the vendors it loaded; without Firestore we read it
    # back off the home page's own copy so the number never contradicts itself.
    vendor_total_display = read_vendor_total() or "70,000+"

    ctx = dict(base=BASE_URL, metros=metros, categories=CATEGORIES,
               vendor_total_display=vendor_total_display, metro_count=len(metros))

    jobs = [(f"pages/{s}.html", s) for s in STATIC_PAGES] + list(STANDALONE.items())
    if args.only:
        wanted = {a.strip("/") for a in args.only}
        jobs = [j for j in jobs if j[1] in wanted]
        missing = wanted - {j[1] for j in jobs} - {"cost", "traditions", "questions", "planning", "guests"}
        if missing:
            sys.exit(f"unknown page(s): {', '.join(sorted(missing))}")

    changed = same = failed = 0
    for tpl_name, out_dir in jobs:
        if not (TPL / tpl_name).is_file():
            print(f"  skip        {out_dir:<38} (no {tpl_name})")
            continue
        try:
            html = env.get_template(tpl_name).render(**ctx)
        except Exception as e:
            failed += 1
            print(f"  FAILED      {out_dir:<38} {type(e).__name__}: {e}")
            continue
        dest = DIST / out_dir / "index.html"
        old = dest.read_text(encoding="utf-8") if dest.is_file() else None
        if old == html:
            same += 1
            print(f"  same        {out_dir}")
            continue
        changed += 1
        verb = "would write" if args.check else "wrote"
        print(f"  {verb:<11} {out_dir:<38} {len(html):>7,} chars"
              f"{'' if old is None else f'  (was {len(old):,})'}")
        if not args.check:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(html, encoding="utf-8")

    # JC-LAZO-COST-0916-001: the cost cluster. build.py counts vendors per
    # category/metro from the Firestore records it loaded; here there is no
    # Firestore, so we count the BUILT PAGES instead - the same number, because
    # a vendor page exists exactly when that vendor is on that category page.
    if not args.only or "cost" in {a.strip("/").split("/")[0] for a in args.only}:
        _c, _s, _f = render_cost(env, metros, args.check)
        changed += _c; same += _s; failed += _f
    if not args.only or "traditions" in {a.strip("/").split("/")[0] for a in args.only}:
        _c, _s, _f = render_traditions(env, metros, args.check)
        changed += _c; same += _s; failed += _f
    if not args.only or "questions" in {a.strip("/").split("/")[0] for a in args.only}:
        _c, _s, _f = render_questions(env, metros, args.check)
        changed += _c; same += _s; failed += _f
    if not args.only or "planning" in {a.strip("/").split("/")[0] for a in args.only}:
        _c, _s, _f = render_planning(env, metros, args.check)
        changed += _c; same += _s; failed += _f
    if not args.only or "guests" in {a.strip("/").split("/")[0] for a in args.only}:
        _c, _s, _f = render_guests(env, metros, args.check)
        changed += _c; same += _s; failed += _f

    print(f"\n{changed} changed, {same} unchanged, {failed} failed"
          f"{'  (--check: nothing written)' if args.check else ''}")
    if failed:
        sys.exit(1)
    if not args.check and changed:
        print("next: python deploy\\bump_assets.py && python deploy\\deploy_site.py --skip-build")


def add_to_sitemap(urls, check):
    """Put the cost URLs in the sitemap without regenerating it.

    build.py appends these to `urls` and rebuilds the sitemap from scratch, so a
    full build handles it. This script cannot: sharding and the stable-lastmod
    cache live in build.py and duplicating them here is how the two drift apart.
    So we append to the last shard, which has room (the cap is 45,000), and only
    when the URL is not already somewhere in the sitemap. Idempotent - a second
    run reports nothing to add, and the next full build rewrites it properly.
    """
    import datetime
    NL = chr(10)
    shards = sorted(DIST.glob("sitemap-*.xml"))
    if not shards:
        print("  sitemap    no shards found - skipped")
        return
    present = set()
    for sh in shards:
        present.update(re.findall(r"<loc>([^<]+)</loc>", sh.read_text(encoding="utf-8")))
    missing = [u for u in urls if u not in present]
    if not missing:
        print(f"  sitemap     all {len(urls)} URL(s) already listed")
        return
    if check:
        print(f"  sitemap     would add {len(missing)} URL(s) to {shards[-1].name}")
        return

    today = datetime.date.today().isoformat()
    last = shards[-1]
    s = last.read_text(encoding="utf-8")
    rows = NL.join(f"<url><loc>{u}</loc><lastmod>{today}</lastmod></url>" for u in missing)
    s = s.replace("</urlset>", rows + NL + "</urlset>", 1)
    last.write_text(s, encoding="utf-8")

    # the index's lastmod for that shard is now wrong, and a lastmod that lies is
    # worse than none - build.py's comment on this is the reason it is stable
    ix = DIST / "sitemap.xml"
    if ix.is_file():
        t = ix.read_text(encoding="utf-8")
        t = re.sub(r"(<loc>[^<]*/" + re.escape(last.name) + r"</loc><lastmod>)[^<]*(</lastmod>)",
                   r"\g<1>" + today + r"\g<2>", t)
        ix.write_text(t, encoding="utf-8")
    print(f"  sitemap     added {len(missing)} URL(s) to {last.name}")



from config.booking import ONE_PER_DAY, WHEN_LABEL, WTB_FAQS


def render_questions(env, metros, check):
    """/questions/, 15 category pages, and /when-to-book/."""
    from config.questions import QUESTIONS, UNIVERSAL
    from config.cost_guides import GUIDES
    from config.taxonomy import BY_SLUG
    out = DIST / "questions"
    t_one = env.get_template("questions_guide.html")
    changed = same = failed = 0
    first = sorted(metros, key=lambda m: m["name"])[0] if metros else {"id": "phoenix", "name": "Phoenix"}
    nq = lambda s: sum(len(items) for _, items in QUESTIONS[s]["groups"])
    rows = []

    for cat in CATEGORIES:
        q = QUESTIONS.get(cat["slug"])
        if not q:
            continue
        counts = [{"id": m["id"], "name": m["name"], "count": count_vendors(cat["slug"], m["id"])}
                  for m in metros]
        total = sum(c["count"] for c in counts)
        counts = sorted((c for c in counts if c["count"]), key=lambda x: -x["count"])[:24]
        sibs = [{"slug": o["slug"], "singular": o["singular"], "n": nq(o["slug"])}
                for o in CATEGORIES if o["slug"] != cat["slug"] and o["slug"] in QUESTIONS][:3]
        html = t_one.render(
            base=BASE_URL, cat=cat, q=q, q_short=GUIDES[cat["slug"]]["short"],
            metro_counts=counts, metro_count=len(metros), guide_count=len(QUESTIONS),
            siblings=sibs, first_metro=first,
            cat_total_display=(f"{(total // 100) * 100:,}+" if total >= 100 else str(total)),
            metros=metros, categories=CATEGORIES)
        changed, same = _emit(out / cat["slug"] / "index.html", html,
                              f"questions/{cat['slug']}", check, changed, same)
        rows.append({"slug": cat["slug"], "singular": cat["singular"], "n": nq(cat["slug"]),
                     "hook": q["lede"].split(". ")[0].rstrip(".") + "."})

    html = env.get_template("questions_index.html").render(
        base=BASE_URL, universal=UNIVERSAL, rows=rows, guide_count=len(QUESTIONS),
        first_metro=first, metros=metros, categories=CATEGORIES)
    changed, same = _emit(out / "index.html", html, "questions", check, changed, same)

    # /when-to-book/ - one page, built from the cost guides' own `timing` lines so
    # it can never drift from what those pages say.
    import datetime
    def wave(slugs):
        return [{"slug": c["slug"], "label": c["label"], "typical": GUIDES[c["slug"]]["typical"],
                 "timing": GUIDES[c["slug"]]["timing"], "when": WHEN_LABEL.get(c["slug"], "")}
                for c in CATEGORIES if c["slug"] in slugs and c["slug"] in GUIDES]
    first_wave = sorted(wave(ONE_PER_DAY), key=lambda r: ONE_PER_DAY.index(r["slug"]))
    second_wave = wave([c["slug"] for c in CATEGORIES if c["slug"] not in ONE_PER_DAY])
    html = env.get_template("when_to_book.html").render(
        base=BASE_URL, first_wave=first_wave, second_wave=second_wave, faqs=WTB_FAQS,
        year=datetime.date.today().year, guide_count=len(GUIDES), metro_count=len(metros),
        first_metro=first, metros=metros, categories=CATEGORIES)
    changed, same = _emit(DIST / "when-to-book" / "index.html", html, "when-to-book",
                          check, changed, same)

    urls = [f"{BASE_URL}/questions/{s}/" for s in QUESTIONS]
    urls += [f"{BASE_URL}/questions/", f"{BASE_URL}/when-to-book/"]
    add_to_sitemap(urls, check)
    return changed, same, failed



def render_planning(env, metros, check):
    """/planning/ plus one page per guide. Content is config/planning.py."""
    from config.planning import PLANNING
    from config.taxonomy import BY_SLUG
    out = DIST / "planning"
    t_one = env.get_template("planning_guide.html")
    changed = same = failed = 0
    first = sorted(metros, key=lambda m: m["name"])[0] if metros else {"id": "phoenix", "name": "Phoenix"}
    # a related slug may point outside the cluster at one of the other hubs
    OUT = {"when-to-book": ("/when-to-book/", "When to book everything", "Planning"),
           "cost": ("/cost/", "What a wedding costs", "Planning"),
           "questions": ("/questions/", "What to ask your vendors", "Planning")}

    for slug, t in PLANNING.items():
        rel = []
        for r in t["related"]:
            if r in OUT:
                h, sh, g = OUT[r]
                rel.append({"href": h, "short": sh, "group": g})
            elif r in PLANNING:
                rel.append({"href": f"/planning/{r}/", "short": PLANNING[r]["short"],
                            "group": PLANNING[r]["group"]})
        cats = [{"slug": c, "label": BY_SLUG[c]["label"], "singular": BY_SLUG[c]["singular"]}
                for c in t["cats"] if c in BY_SLUG]
        html = t_one.render(base=BASE_URL, t=t, slug=slug, related=rel, vendor_cats=cats,
                            first_metro=first, guide_count=len(PLANNING),
                            metros=metros, categories=CATEGORIES)
        changed, same = _emit(out / slug / "index.html", html, f"planning/{slug}",
                              check, changed, same)

    order = ["The day itself", "People", "The wedding party", "Words", "Money & who pays", "Logistics"]
    grouped = []
    for g in order:
        items = [{"slug": s, "short": t["short"], "question": t["question"],
                  "blurb": t["lede"].split(". ")[0].rstrip(".") + "."}
                 for s, t in PLANNING.items() if t["group"] == g]
        if items:
            grouped.append((g, items))
    html = env.get_template("planning_index.html").render(
        base=BASE_URL, groups=grouped, guide_count=len(PLANNING),
        first_metro=first, metros=metros, categories=CATEGORIES)
    changed, same = _emit(out / "index.html", html, "planning", check, changed, same)

    add_to_sitemap([f"{BASE_URL}/planning/{s}/" for s in PLANNING] + [f"{BASE_URL}/planning/"], check)
    return changed, same, failed



def render_guests(env, metros, check):
    """/guests/ plus one page per guide. Content is config/guests.py."""
    from config.guests import GUESTS
    out = DIST / "guests"
    t_one = env.get_template("guest_guide.html")
    changed = same = failed = 0
    first = sorted(metros, key=lambda m: m["name"])[0] if metros else {"id": "phoenix", "name": "Phoenix"}
    OUT = {"traditions": ("/traditions/", "Wedding traditions", "45 ceremonies explained"),
           "planning": ("/planning/", "Planning your own wedding", "Timelines, seating, vows"),
           "cost": ("/cost/", "What a wedding costs", "Honest ranges")}

    for slug, g in GUESTS.items():
        rel = []
        for r in g["related"]:
            if r in OUT:
                h, sh, gr = OUT[r]
                rel.append({"href": h, "short": sh, "group": gr})
            elif r in GUESTS:
                rel.append({"href": f"/guests/{r}/", "short": GUESTS[r]["short"],
                            "group": GUESTS[r]["group"]})
        html = t_one.render(base=BASE_URL, g=g, slug=slug, related=rel,
                            guide_count=len(GUESTS), first_metro=first,
                            metros=metros, categories=CATEGORIES)
        changed, same = _emit(out / slug / "index.html", html, f"guests/{slug}",
                              check, changed, same)

    order = ["What to wear", "Gifts", "At the wedding"]
    grouped = []
    for grp in order:
        items = [{"slug": s, "short": g["short"], "question": g["question"],
                  "blurb": g["answer"].split(". ")[0].rstrip(".") + "."}
                 for s, g in GUESTS.items() if g["group"] == grp]
        if items:
            grouped.append((grp, items))
    html = env.get_template("guests_index.html").render(
        base=BASE_URL, groups=grouped, guide_count=len(GUESTS),
        first_metro=first, metros=metros, categories=CATEGORIES)
    changed, same = _emit(out / "index.html", html, "guests", check, changed, same)

    add_to_sitemap([f"{BASE_URL}/guests/{s}/" for s in GUESTS] + [f"{BASE_URL}/guests/"], check)
    return changed, same, failed



def render_traditions(env, metros, check):
    """/traditions/ plus one page per tradition. Content is config/traditions.py."""
    from config.traditions import TRADITIONS
    from config.taxonomy import BY_SLUG
    out = DIST / "traditions"
    t_one = env.get_template("tradition.html")
    changed = same = failed = 0
    first = sorted(metros, key=lambda m: m["name"])[0] if metros else {"id": "phoenix", "name": "Phoenix"}

    def href(slug):
        # /what-is-a-lazo/ keeps its own URL - it has been indexed for months and
        # moving it under /traditions/ for tidiness would throw that away.
        return "/what-is-a-lazo/" if slug == "what-is-a-lazo" else f"/traditions/{slug}/"

    LAZO = {"short": "The lazo", "culture": "Mexican, Filipino & Spanish"}
    for slug, t in TRADITIONS.items():
        rel = []
        for r in t["related"]:
            meta = LAZO if r == "what-is-a-lazo" else TRADITIONS.get(r)
            if meta:
                rel.append({"href": href(r), "short": meta["short"], "culture": meta["culture"]})
        cats = [{"slug": c, "label": BY_SLUG[c]["label"], "singular": BY_SLUG[c]["singular"]}
                for c in t["cats"] if c in BY_SLUG]
        html = t_one.render(base=BASE_URL, t=t, slug=slug, related=rel, vendor_cats=cats,
                            first_metro=first, tradition_count=len(TRADITIONS) + 1,
                            metros=metros, categories=CATEGORIES)
        changed, same = _emit(out / slug / "index.html", html, f"traditions/{slug}",
                              check, changed, same)

    order = ["Latin American & Spanish", "Filipino", "Jewish", "South Asian",
             "East Asian", "Southeast Asian", "Middle Eastern & Persian", "African",
             "Eastern European", "European & Celtic", "African American",
             "Indigenous American", "Unity rituals"]
    grouped = []
    for g in order:
        items = [{"href": href(s), "short": t["short"], "culture": t["culture"],
                  # first sentence of the lede is the card blurb - no second copy to drift
                  "blurb": t["lede"].split(". ")[0].rstrip(".") + "."}
                 for s, t in TRADITIONS.items() if t["group"] == g]
        if items:
            grouped.append((g, items))
    html = env.get_template("traditions_index.html").render(
        base=BASE_URL, groups=grouped, tradition_count=len(TRADITIONS) + 1,
        first_metro=first, metros=metros, categories=CATEGORIES)
    changed, same = _emit(out / "index.html", html, "traditions", check, changed, same)

    urls = [f"{BASE_URL}/traditions/{s}/" for s in TRADITIONS] + [f"{BASE_URL}/traditions/"]
    add_to_sitemap(urls, check)
    return changed, same, failed



def count_vendors(cat_slug, metro_id):
    """How many vendors this metro/category page actually LISTS.

    Counted from the cards on the category page, not from directories on disk.
    dist/ is append-only - build.py writes vendor pages and never deletes them -
    so a vendor that was recategorised or moved metro (vendors are assigned by
    placeId, so adding a metro shifts hundreds of them) leaves its old directory
    behind. Counting directories over-reported Boston wedding venues as 348 when
    the category page lists 306, and a cost guide claiming vendors that are not
    on the page it links to is worse than no number at all.

    This matches what build.py counts from Firestore: both are "vendors on that
    category page", so the two builders now produce byte-identical output.
    """
    f = DIST / metro_id / cat_slug / "index.html"
    if not f.is_file():
        return 0
    return len(set(re.findall(rf'href="/{re.escape(metro_id)}/{re.escape(cat_slug)}/([a-z0-9_-]+)/"',
                              f.read_text(encoding="utf-8", errors="replace"))))


def render_cost(env, metros, check):
    """/cost/ plus one guide per category. Mirrors build.py's block exactly."""
    import datetime
    year = datetime.date.today().year
    out = DIST / "cost"
    t_guide = env.get_template("cost_guide.html")
    changed = same = failed = 0
    rows = []

    for cat in CATEGORIES:
        g = COST_GUIDES.get(cat["slug"])
        if not g:
            continue
        counts = [{"id": m["id"], "name": m["name"], "count": count_vendors(cat["slug"], m["id"])}
                  for m in metros]
        total = sum(c["count"] for c in counts)
        # biggest markets first: a reader scanning for their city wants the
        # obvious ones visible without expanding anything
        counts = sorted((c for c in counts if c["count"]), key=lambda x: -x["count"])[:24]
        sibs = [{"slug": o["slug"], "question": COST_GUIDES[o["slug"]]["question"],
                 "typical": COST_GUIDES[o["slug"]]["typical"]}
                for o in CATEGORIES if o["slug"] != cat["slug"] and o["slug"] in COST_GUIDES][:3]
        html = t_guide.render(
            base=BASE_URL, cat=cat, g=g, year=year, metro_counts=counts,
            metro_count=len(metros), guide_count=len(COST_GUIDES), siblings=sibs,
            cat_total_display=(f"{(total // 100) * 100:,}+" if total >= 100 else str(total)),
            metros=metros, categories=CATEGORIES)
        changed, same = _emit(out / cat["slug"] / "index.html", html,
                              f"cost/{cat['slug']}", check, changed, same)
        rows.append({"slug": cat["slug"], "question": g["question"],
                     "typical": g["typical"], "hook": g["hook"]})

    html = env.get_template("cost_index.html").render(
        base=BASE_URL, rows=rows, year=year, metro_count=len(metros),
        first_metro=(sorted(metros, key=lambda m: m["name"])[0] if metros
                     else {"id": "phoenix", "name": "Phoenix"}),
        metros=metros, categories=CATEGORIES)
    changed, same = _emit(out / "index.html", html, "cost", check, changed, same)

    add_to_sitemap([f"{BASE_URL}/cost/{r['slug']}/" for r in rows] + [f"{BASE_URL}/cost/"], check)
    return changed, same, failed


def _emit(dest, html, label, check, changed, same):
    """Write a page only when it differs, and report it the way main() does."""
    old = dest.read_text(encoding="utf-8") if dest.is_file() else None
    if old == html:
        print(f"  same        {label}")
        return changed, same + 1
    verb = "would write" if check else "wrote"
    print(f"  {verb:<11} {label:<38} {len(html):>7,} chars"
          f"{'' if old is None else f'  (was {len(old):,})'}")
    if not check:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html, encoding="utf-8")
    return changed + 1, same



def read_vendor_total():
    """Lift the "72,600+" figure back out of a page the last real build wrote.

    build.py counts this from the vendors it loaded out of Firestore; here there
    is no Firestore, and guessing would quietly walk the number backwards on
    /for-vendors/ every time someone fixed a typo. Reading it back means a page
    rendered by this script always agrees with the rest of the built site.
    /for-vendors/ is checked first because it prints the figure in a sentence
    that cannot be confused with anything else on the page.
    """
    import re
    for path, pat in (
        (DIST / "for-vendors" / "index.html", r"we index ([\d,]{4,})\+ wedding businesses"),
        (DIST / "index.html", r"([\d,]{4,})\+"),
    ):
        if not path.is_file():
            continue
        m = re.search(pat, path.read_text(encoding="utf-8"))
        if m:
            return f"{m.group(1)}+"
    return None


if __name__ == "__main__":
    main()
