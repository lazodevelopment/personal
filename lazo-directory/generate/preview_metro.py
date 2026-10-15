"""preview_metro.py - build ONE metro into dist-preview/ without touching dist/ or Firestore slugs.

    python generate\\preview_metro.py phoenix          # -> dist-preview/phoenix/...

Sets LAZO_CURATED=1 so curated picks (generate/data/curated/<metro>/<cat>.json) render. The nightly build does
not set that variable, so nothing reaches the live site until it is switched on there.
"""
import os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "generate"))
os.environ.setdefault("LAZO_CURATED", "1")
os.chdir(ROOT)

metro = sys.argv[1] if len(sys.argv) > 1 else "phoenix"
import build  # noqa: E402
import config.metros as metros_cfg  # noqa: E402

only = [m for m in metros_cfg.METROS if m["id"] in (metro, "phoenix")]   # the homepage needs its home metro (phoenix)
assert only, f"unknown metro {metro}"
build.metros_for_tranche = lambda t: only
build._writeback_slugs = lambda by_metro: None          # preview never writes to Firestore
build.DIST = ROOT / "dist-preview"
build.DIST.mkdir(exist_ok=True)

vendors = build.load_vendors_firestore(7)
vendors = build.saturday_enrich(vendors)
# build() rewrites vendor_paths.json from the pages it wrote; a one-metro preview would leave the nightly a
# one-metro map and lose every other metro's 301 history. Put the real one back afterwards.
_paths = ROOT / "generate" / "vendor_paths.json"
_saved = _paths.read_bytes() if _paths.exists() else None
try:
    build.build(vendors)
finally:
    if _saved is not None:
        _paths.write_bytes(_saved)
print("preview written to", build.DIST / metro)
