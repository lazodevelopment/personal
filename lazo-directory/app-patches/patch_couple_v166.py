r"""patch_couple_v166.py - Couple v165 -> v166: LIGHT / DARK IN THE TOP BAR.  JC-LAZO-THEME-SWITCH-1016-COUPLE

The theme was only reachable through Account > Appearance. A round sun / moon button now sits in the top bar,
next to share and June's bell: one tap flips light <-> dark (saved in lazo_theme, shared with the vendor
dashboard). Account > Appearance keeps Light / Dark / Auto.

    python app-patches\patch_couple_v166.py [base.txt]   # base defaults to Couple_master_v165.txt
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Couple_master_v165.txt"
DST = HERE / "Couple_master_v166.txt"
s = SRC.read_text(encoding="utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")


def rep(old, new, n=1):
    global s
    c = s.count(old)
    assert c == n, f"expected {n} match(es), found {c}: {old[:90]!r}"
    s = s.replace(old, new)


rep("// Build ID: JC-LAZO-CALLS-1016-COUPLE",
    "// Build ID: JC-LAZO-THEME-SWITCH-1016-COUPLE (v166: LIGHT / DARK IN THE TOP BAR - a sun / moon button next to "
    "share and the bell flips the theme in one tap; Account > Appearance keeps Light / Dark / Auto; base v165)\n"
    "// Build ID: JC-LAZO-CALLS-1016-COUPLE")

rep("""                  _roundBtn(Icons.ios_share_rounded, () => _shareLazo()),""",
    """                  _roundBtn(_lzDark ? Icons.light_mode_rounded : Icons.dark_mode_rounded,
                      () => _lzSetTheme(_lzDark ? 'light' : 'dark')),
                  const SizedBox(width: 10),
                  _roundBtn(Icons.ios_share_rounded, () => _shareLazo()),""")

if crlf:
    s = s.replace("\n", "\r\n")
DST.write_text(s, encoding="utf-8", newline="")
print(f"wrote {DST.name} from {SRC.name} ({len(s):,} chars)")
