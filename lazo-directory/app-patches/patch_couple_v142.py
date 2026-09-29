"""patch_couple_v142.py - JC-LAZO-COUPLE-0929-V142
Peony is the default design: a couple who opens the website editor with no
saved design, no ?template= from the marketing page and no legacy value
starts on Peony (was Fete), and an unknown saved value falls back to Peony.
Applies on top of Couple_master_v141.txt -> Couple_master_v142.txt.
"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Couple_master_v141.txt"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "Couple_master_v142.txt"
s = SRC.read_text(encoding="utf-8")
if "JC-LAZO-COUPLE-0929-V142" in s:
    raise SystemExit("already applied")
def swap(old, new, label, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"ABORT [{label}]: anchor matched {n} times, expected {count}")
    s = s.replace(old, new); print(f"  ok  {label}")
swap("// (v141: PEONY", "// (v142: Peony is the default design for a new site (was Fete). JC-LAZO-COUPLE-0929-V142; base v141)\n// (v141: PEONY", "header")
swap("        (_pendingTemplate.isNotEmpty ? _pendingTemplate : 'fete')) as String;", "        (_pendingTemplate.isNotEmpty ? _pendingTemplate : 'peony')) as String; // v142", "default design")
swap("""    ].contains(template)) {
      template = 'fete';
    }
""", """    ].contains(template)) {
      template = 'peony'; // v142
    }
""", "unknown falls back to Peony")
OUT.write_text(s, encoding="utf-8", newline="\n"); print(f"wrote {OUT.name}")
