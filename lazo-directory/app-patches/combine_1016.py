r"""combine_1016.py - one Couple and one Vendor master with every 2026-10-16 feature.  JC-LAZO-COMBINED-1016

Four sessions each patched Couple v159 / Vendor v199 on their own, so each feature master lacks the others:
  Couple v160 safety, v161 meal choices, v163 engagement questionnaires
  Vendor v200 safety, v201 COI uploads, v202 meal counts, v203 engagement sessions
This re-runs those patch scripts one after another in a temp folder (none of the feature masters is overwritten)
and writes:
  Couple_master_v164.txt = v159 + v160 + v161 + v163
  Vendor_master_v204.txt = v199 + v200 + v201 + v202 + v203
Every patch keeps its exact-count asserts, so a clash stops the run.

    python app-patches\combine_1016.py
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(tmp, script, arg=None):
    cmd = [sys.executable, "-I", str(tmp / script)] + ([arg] if arg else [])
    r = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"{script} failed:\n{r.stdout}\n{r.stderr}")
    print("  " + (r.stdout.strip().splitlines() or [script])[-1])


def stamp(src, dst, line):
    s = src.read_text(encoding="utf-8")
    i = s.index("// Build ID:")
    s = s[:i] + line + "\n" + s[i:]
    dst.write_text(s, encoding="utf-8", newline="")
    print(f"wrote {dst.name} ({len(s):,} chars)")


with tempfile.TemporaryDirectory() as d:
    c = Path(d) / "c"
    c.mkdir()
    for f in ["patch_couple_v160.py", "patch_couple_v161.py", "patch_couple_v163.py", "Couple_master_v159.txt"]:
        shutil.copy(HERE / f, c / f)
    print("Couple:")
    run(c, "patch_couple_v160.py", "Couple_master_v159.txt")
    run(c, "patch_couple_v161.py", "Couple_master_v160.txt")
    run(c, "patch_couple_v163.py", "Couple_master_v161.txt")
    stamp(c / "Couple_master_v163.txt", HERE / "Couple_master_v164.txt",
          "// Build ID: JC-LAZO-COMBINED-1016-COUPLE (v164: COMBINED - v159 + v160 safety (outside video links) + "
          "v161 meal choices + v163 engagement questionnaires, chained by combine_1016.py; paste this one)")

    v = Path(d) / "v"
    v.mkdir()
    for f in ["patch_vendor_v200.py", "patch_vendor_v201.py", "patch_vendor_v202.py", "patch_vendor_v203.py",
              "Vendor_master_v199.txt"]:
        shutil.copy(HERE / f, v / f)
    print("Vendor:")
    run(v, "patch_vendor_v200.py", "Vendor_master_v199.txt")
    # patch_vendor_v201.py always reads Vendor_master_v199.txt from its own folder: hand it v200 under that name
    shutil.copy(v / "Vendor_master_v199.txt", v / "orig199.txt")
    shutil.copy(v / "Vendor_master_v200.txt", v / "Vendor_master_v199.txt")
    run(v, "patch_vendor_v201.py")
    shutil.copy(v / "orig199.txt", v / "Vendor_master_v199.txt")
    run(v, "patch_vendor_v202.py", "Vendor_master_v201.txt")
    run(v, "patch_vendor_v203.py", "Vendor_master_v202.txt")
    stamp(v / "Vendor_master_v203.txt", HERE / "Vendor_master_v204.txt",
          "// Build ID: JC-LAZO-COMBINED-1016-VENDOR (v204: COMBINED - v199 add a client + v200 safety (outside video "
          "links) + v201 COI uploads + v202 meal counts + v203 engagement sessions, chained by combine_1016.py; "
          "paste this one)")
