"""Repairs UTF-8 text mangled by an earlier ANSI read/write in build.py
(em-dashes showing as a-hat sequences on live pages). Run once from lazo-directory root."""
from pathlib import Path
bp = Path("generate/build.py")
raw = bp.read_text(encoding="utf-8")
fixes = {
    "\u00e2\u20ac\u201d": "\u2014",  # em dash
    "\u00e2\u20ac\u201c": "\u2013",  # en dash
    "\u00e2\u20ac\u2122": "\u2019",  # right single quote
    "\u00e2\u20ac\u02dc": "\u2018",  # left single quote
    "\u00e2\u20ac\u0153": "\u201c",  # left double quote
    "\u00e2\u20ac\u009d": "\u201d",  # right double quote
    "\u00e2\u20ac\u00a6": "\u2026",  # ellipsis
    "\u00c2\u00a0": "\u00a0",        # nbsp
}
count = 0
for bad, good in fixes.items():
    n = raw.count(bad)
    if n:
        raw = raw.replace(bad, good)
        count += n
bp.write_text(raw, encoding="utf-8")
print(f"REPAIRED: {count} mangled sequences fixed" if count else "No mojibake found (maybe already repaired).")
