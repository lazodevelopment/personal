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

only = [m for m in metros_cfg.METROS if m["id"] == metro]
assert only, f"unknown metro {metro}"
build.metros_for_tranche = lambda t: only
build._writeback_slugs = lambda by_metro: None          # preview never writes to Firestore
build.DIST = ROOT / "dist-preview"
build.DIST.mkdir(exist_ok=True)

vendors = build.load_vendors_firestore(7)
vendors = build.saturday_enrich(vendors)
build.build(vendors)
print("preview written to", build.DIST / metro)
