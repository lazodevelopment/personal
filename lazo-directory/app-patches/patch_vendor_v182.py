"""patch_vendor_v182.py - JC-LAZO-VDASH-1005-182
Talk to June opens june.meetlazo.com (the hub's custom domain, live 2026-10-05)
instead of the workers.dev address. Nothing else changes.

Anchor-and-assert against Vendor_master_v181.txt; writes Vendor_master_v182.txt.
  python app-patches\\patch_vendor_v182.py
"""
from pathlib import Path
HERE = Path(__file__).resolve().parent
src = HERE / "Vendor_master_v181.txt"; dst = HERE / "Vendor_master_v182.txt"
s = src.read_text(encoding="utf-8")
if "VDASH-1005-182" in s:
    raise SystemExit("already patched")

def rep(old, new, label, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"{label}: anchor found {n}x, wanted {count}: {old[:70]!r}")
    s = s.replace(old, new)

rep("// Build ID: JC-LAZO-VDASH-1005-181 (v181:",
    "// Build ID: JC-LAZO-VDASH-1005-182 (v182: Talk to June opens june.meetlazo.com. base v181)\n// (v181:",
    "build id")
rep("  // v180: the June hub (june-hub worker). Swap for june.meetlazo.com once the custom domain is on.\n"
    "  static const String kJuneHubUrl = 'https://june-hub.floral-credit-e4f0.workers.dev/';",
    "  // v182: the June hub on its own domain (the workers.dev address still answers).\n"
    "  static const String kJuneHubUrl = 'https://june.meetlazo.com/';",
    "hub url")

dst.write_text(s, encoding="utf-8")
print("wrote", dst.name, len(s), "chars")
