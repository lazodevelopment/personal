r"""Ship a footer change into the existing dist/ without a rebuild.  JC-LAZO-SWAPFOOT-0915-001

The footer lives in generate/templates/_footer.html and reaches pages through
base.html, so normally a footer change rides along with `python generate\build.py`.
Firestore builds are blocked on this machine (Application Control refuses grpc's
cygrpc DLL), and the footer is the site's internal-linking spine - it should not
wait for that. This renders the SAME template and swaps it into every page that
already has one.

It is contextual, exactly as a real build would be: a page under dist/denver/
gets the Denver footer, because _footer.html reads `metro`. The metro is taken
from the path, and the render is cached per metro, so 87k pages cost 46 renders.

    python deploy\swap_footer.py            # rewrite dist/
    python deploy\swap_footer.py --check    # report only, change nothing
    python deploy\bump_assets.py            # then the css/js stamp
    python deploy\deploy_site.py --skip-build

Safe to re-run: a page whose footer already matches is left untouched, so the
second run reports 0 changed. Pages with a different footer (the gallery
delivery page) have no <footer class="site-foot"> and are skipped by
construction. what-is-a-lazo used to be one of those; since
JC-LAZO-CFORM-0916-001 it extends base.html like every other page, so it now
carries the real footer and this script maintains it too.
"""
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

# JC-LAZO-DISTLOCK-0917-001: never rewrite dist/ under a live sync
sys.path.insert(0, str(ROOT / "deploy"))
from distlock import guard

FOOTER = re.compile(r'<footer class="site-foot">.*?</footer>', re.S)


def built_metros():
    """The cities that actually have a page - the footer must never link one that doesn't."""
    return [m for m in METROS if (DIST / m["id"] / "index.html").is_file()]


def renderer():
    env = Environment(loader=FileSystemLoader(TPL), autoescape=select_autoescape(["html"]))
    env.globals["foot_metros"] = [{"id": m["id"], "name": m["name"]} for m in built_metros()]
    env.globals["foot_cats"] = [{"slug": c["slug"], "label": c["label"]} for c in CATEGORIES]
    t = env.get_template("_footer.html")
    cache = {}

    def footer_for(metro_id):
        if metro_id not in cache:
            m = BY_ID.get(metro_id)
            cache[metro_id] = t.render(metro=m).rstrip("\n")
        return cache[metro_id]

    return footer_for


def metro_of(path: Path):
    """dist/denver/wedding-djs/foo/index.html -> 'denver'; dist/about/index.html -> None."""
    rel = path.relative_to(DIST).parts
    return rel[0] if rel and rel[0] in BY_ID else None


def main():
    check = "--check" in sys.argv
    guard(force=("--force" in sys.argv or "--check" in sys.argv))
    if not DIST.is_dir():
        sys.exit("dist/ not found - nothing to swap")
    cities = built_metros()
    if not cities:
        sys.exit("no metro pages in dist/ - refusing to write a footer with no cities")
    footer_for = renderer()
    print(f"{len(cities)} cities, {len(CATEGORIES)} categories; "
          f"{'checking' if check else 'rewriting'} dist/")

    scanned = changed = same = skipped = 0
    for p in DIST.rglob("*.html"):
        scanned += 1
        try:
            s = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            skipped += 1
            continue
        m = FOOTER.search(s)
        if not m:
            skipped += 1
            continue
        new = footer_for(metro_of(p))
        if m.group(0) == new:
            same += 1
        else:
            changed += 1
            if not check:
                p.write_text(s[:m.start()] + new + s[m.end():], encoding="utf-8", newline="")
        if scanned % 10000 == 0:
            print(f"  {scanned:,} scanned, {changed:,} to change")

    print(f"done: {scanned:,} pages scanned, {changed:,} "
          f"{'would change' if check else 'rewritten'}, {same:,} already current, "
          f"{skipped:,} without a site footer")


if __name__ == "__main__":
    main()
