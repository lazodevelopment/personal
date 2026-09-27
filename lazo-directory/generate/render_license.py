"""render_license.py - JC-LAZO-LICENSE-0920-001
Renders /marriage-license/ (hub, 51 state pages, data.json) into dist/ on its
own, without a full build, so the pages can ship between nightlies:

  python generate\\render_license.py
  python deploy\\upload_r2.py --prefix marriage-license

build.py renders the same pages (and adds them to the sitemap) on every full
build; this script exists for the first publish and quick fixes.
"""
import json, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from jinja2 import Environment, FileSystemLoader  # noqa: E402
from config.metros import METROS  # noqa: E402
from config.taxonomy import CATEGORIES  # noqa: E402
from config.marriage_license import STATES, COUNTIES, BY_ABBR, fee_text, wait_text, valid_text  # noqa: E402

BASE_URL = "https://meetlazo.com"
DIST = ROOT / "dist"
env = Environment(loader=FileSystemLoader(str(ROOT / "generate" / "templates")), autoescape=False)
live_metros = list(METROS)
first = live_metros[0]
try:
    vendor_total_display = json.loads((ROOT / "generate" / "vendor_paths.json").read_text(encoding="utf-8")).get("total_display", "")
except Exception:
    vendor_total_display = ""
if not vendor_total_display:
    try:
        import re
        home = (DIST / "index.html").read_text(encoding="utf-8")
        m = re.search(r"([\d,]{5,}) wedding", home)
        vendor_total_display = m.group(1) if m else "100,000+"
    except Exception:
        vendor_total_display = "100,000+"

common = dict(base=BASE_URL, metros=live_metros, categories=CATEGORIES,
              vendor_total_display=vendor_total_display, metro_count=len(live_metros), first_metro=first)
ldir = DIST / "marriage-license"
ldir.mkdir(exist_ok=True)
year = date.today().year
metros_by_state = {}
for m in METROS:
    metros_by_state.setdefault(BY_ABBR.get(m["state"], ""), []).append(m)
states = []
for slug, st in STATES.items():
    states.append(dict(st, slug=slug, fee_text=fee_text(st["fee"]), wait_text=wait_text(st["wait_days"]), valid_text=valid_text(st["valid_days"])))
states.sort(key=lambda r: r["name"])
(ldir / "index.html").write_text(env.get_template("license_index.html").render(states=states, year=year, **common), encoding="utf-8")
t = env.get_template("license_state.html")
data = {"updated": date.today().isoformat(), "states": {}, "metros": {}}
for row in states:
    ms = metros_by_state.get(row["slug"], [])
    offices = [{"metro": m["name"], "metro_id": m["id"], "county": c, "office": o, "site": u, "fee": f, "note": n}
               for m in ms for (c, o, u, f, n) in COUNTIES.get(m["id"], [])]
    d = ldir / row["slug"]
    d.mkdir(exist_ok=True)
    (d / "index.html").write_text(t.render(s=row, offices=offices, year=year, **dict(common, metros=ms)), encoding="utf-8")
    data["states"][row["slug"]] = {k: row[k] for k in ("name", "abbr", "issuer", "fee", "fee_text", "wait_days", "wait_text", "valid_days", "valid_text", "witnesses", "min_age", "course", "notes")}
for m in METROS:
    data["metros"][m["id"]] = {"state": BY_ABBR.get(m["state"], ""), "offices": [
        {"county": c, "office": o, "site": u, "fee": f, "note": n} for (c, o, u, f, n) in COUNTIES.get(m["id"], [])]}
(ldir / "data.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
missing = [m["id"] for m in METROS if m["id"] not in COUNTIES]
print(f"rendered hub + {len(states)} states + data.json into {ldir}; metros without an office entry: {missing or 'none'}")
