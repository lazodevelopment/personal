r"""build_into.py - JC-LAZO-LOCAL-1017-001: run the nightly's build step into another folder.

    python deploy\build_into.py dist-next      # same as `build.py --tranche 8` + live_shells.py, but into dist-next/

For a hand publish while the nightly's sync still reads dist/: build here, then (with the nightly lock held)
swap the folders and run deploy_site.py --skip-build. Set LAZO_CURATED=1 and LAZO_SITEFACTS=1 like the nightly.
"""
import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "generate")); sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
target = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "dist-next")
assert target.name != "dist", "use build.py for dist itself"
import build  # noqa: E402
build.DIST = target
target.mkdir(exist_ok=True)
vendors = build.load_vendors_firestore(8)
vendors = build.saturday_enrich(vendors)
build.build(vendors)
import live_shells  # noqa: E402
live_shells.DIST = target
live_shells.main()
print(f"[build_into] done -> {target}")
