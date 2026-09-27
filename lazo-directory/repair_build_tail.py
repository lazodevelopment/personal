"""Repairs build.py's tail after the saturday patch mis-nested the runner
lines inside saturday_enrich(). Run from lazo-directory root:
    python repair_build_tail.py
Then build normally."""
from pathlib import Path
import ast

bp = Path("generate/build.py")
src = bp.read_text(encoding="utf-8")

RUNNER = '''

if __name__ == "__main__":
    vendors = load_vendors_mock(Path(a.mock)) if a.mock else load_vendors_firestore(a.tranche)
    vendors = saturday_enrich(vendors)
    build(vendors)
'''

if "REPAIRED-TAIL" in src:
    print("Already repaired.")
    raise SystemExit

# 1. Remove the dead runner lines trapped inside saturday_enrich (after its return)
dead_variants = [
    '''    return vendors

    vendors = load_vendors_mock(Path(a.mock)) if a.mock else load_vendors_firestore(a.tranche)
    vendors = saturday_enrich(vendors)
    build(vendors)''',
    '''    return vendors
    vendors = load_vendors_mock(Path(a.mock)) if a.mock else load_vendors_firestore(a.tranche)
    vendors = saturday_enrich(vendors)
    build(vendors)''',
]
removed = False
for dead in dead_variants:
    if dead in src:
        src = src.replace(dead, "    return vendors")
        removed = True
        break
if not removed:
    # tolerate whitespace drift: regex fallback
    import re
    pat = re.compile(
        r"    return vendors\s*\n\s*vendors = load_vendors_mock\(Path\(a\.mock\)\) if a\.mock else load_vendors_firestore\(a\.tranche\)\s*\n\s*vendors = saturday_enrich\(vendors\)\s*\n\s*build\(vendors\)")
    src2, n = pat.subn("    return vendors", src)
    if n:
        src = src2
        removed = True
assert removed, "dead runner block not found - paste build.py's last 60 lines to Claude"

# 2. Append a correct runner at module end
src = src.rstrip() + "\n\n# REPAIRED-TAIL" + RUNNER
bp.write_text(src, encoding="utf-8")

# 3. Verify: parses AND the runner is at module level
tree = ast.parse(src)
top_ifs = [n for n in tree.body if isinstance(n, ast.If)]
assert any("__main__" in ast.dump(n.test) for n in top_ifs), "runner not at module level"
print("REPAIRED: runner restored at module level. Syntax verified.")
