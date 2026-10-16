r"""patch_vendor_v206.py - Vendor v205 -> v206: THE LAZO VERIFIED BADGE.  JC-LAZO-VERIFIED-BADGE-1016-VENDOR

The dashboard hero's "Lazo verified" pill was a flat gold chip whose dark plum text the night theme turned pale
pink (#E2C6DE), so in dark mode it was unreadable. Verification takes real work, so the badge now looks earned:
  - a gold gradient with a soft glow and a fine highlight edge, a verified seal icon and bolder lettering;
  - dark mode: white seal and text on a deeper gold (readable, still clearly the gold badge);
  - light mode: deep plum on bright gold;
  - colors are set directly, not through the night-theme mapper, so the text never washes out;
  - "Claimed" (not yet verified) keeps the plain outlined pill, so the verified one stands apart.

    python app-patches\patch_vendor_v206.py [base.txt]   # base defaults to Vendor_master_v205.txt
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Vendor_master_v205.txt"
DST = HERE / "Vendor_master_v206.txt"
s = SRC.read_text(encoding="utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")


def rep(old, new, n=1):
    global s
    c = s.count(old)
    assert c == n, f"expected {n} match(es), found {c}: {old[:90]!r}"
    s = s.replace(old, new)


rep("// Build ID: JC-LAZO-CALLS-1016-VENDOR",
    "// Build ID: JC-LAZO-VERIFIED-BADGE-1016-VENDOR (v206: THE LAZO VERIFIED BADGE - gold gradient, glow and a verified "
    "seal; white on deeper gold in dark mode, where the old plum text washed out; Claimed keeps the plain pill; "
    "a light / dark switch in the top bar next to the bell; base v205)\n// Build ID: JC-LAZO-CALLS-1016-VENDOR")

# the light / dark switch in the top bar, next to June's bell (Account > Appearance keeps Light / Dark / Auto)
rep("""                              if (_uid != null) _feedBell(),""",
    """                              IconButton(
                                tooltip: _lzDark ? 'Switch to light' : 'Switch to dark',
                                onPressed: _h(() => _lzSetTheme(_lzDark ? 'light' : 'dark')),
                                icon: Icon(_lzDark ? Icons.light_mode_rounded : Icons.dark_mode_rounded,
                                    color: _lzFg(plum), size: 22),
                              ),
                              if (_uid != null) _feedBell(),""")

rep("""                _heroPill(verified ? 'Lazo verified' : 'Claimed', verified),""",
    """                verified ? _verifiedBadge() : _heroPill('Claimed', false),""")

rep("""  Widget _heroTile(String label, String value, String unit, String sub) {""",
    """  // v206: the badge a vendor earns. Colors are set directly (not through _lzFg),
  // so the night theme can't wash the lettering out.
  Widget _verifiedBadge() {
    final bool dark = _lzDark;
    final Color ink = dark ? Colors.white : plumDeep;
    return Tooltip(
      message: 'Verified by Lazo',
      child: Container(
        padding: const EdgeInsets.fromLTRB(7, 4, 13, 4),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: dark
                ? const <Color>[Color(0xFFB8914A), Color(0xFF7E5B22)]
                : const <Color>[Color(0xFFF4DFB0), Color(0xFFD9B77C)],
          ),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(
              color: dark
                  ? const Color(0xFFF1D9A6).withOpacity(.65)
                  : const Color(0xFFB8924F).withOpacity(.7),
              width: 1),
          boxShadow: <BoxShadow>[
            BoxShadow(
                color: const Color(0xFFD9B77C).withOpacity(dark ? .30 : .40),
                blurRadius: 14,
                offset: const Offset(0, 3)),
          ],
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
          Icon(Icons.verified_rounded, size: 16, color: ink),
          const SizedBox(width: 5),
          Text('Lazo verified',
              style: TextStyle(
                  color: ink,
                  fontSize: 12.5,
                  fontWeight: FontWeight.w800,
                  letterSpacing: .3)),
        ]),
      ),
    );
  }

  Widget _heroTile(String label, String value, String unit, String sub) {""")

if crlf:
    s = s.replace("\n", "\r\n")
DST.write_text(s, encoding="utf-8", newline="")
print(f"wrote {DST.name} from {SRC.name} ({len(s):,} chars)")
