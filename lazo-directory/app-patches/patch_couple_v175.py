"""Couple v175: Whop only for card payments (JC-LAZO-WHOPONLY-1018-COUPLE).

    python app-patches\\patch_couple_v175.py [base.txt]   # base defaults to Couple_master_v174.txt
                                                          # writes Couple_master_v175.txt
- the Pay by card button shows only for vendors on Whop. Stripe was left (its checkout is not
  deployed) and Square was never set up, so a stale stripeChargesEnabled / squareConnected flag
  on a vendor doc used to show a card button that failed. Other vendors show their payment links.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Couple_master_v174.txt"
DST = HERE / "Couple_master_v175.txt"
s = SRC.read_text(encoding="utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")


def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, f"expected {n}, found {c}: {a[:90]!r}"
    s = s.replace(a, b)


first_build = s.index("// Build ID:")
s = s[:first_build] + (
    "// Build ID: JC-LAZO-WHOPONLY-1018-COUPLE (v175: WHOP ONLY - Pay by card shows only for vendors on Whop; a stale "
    "Stripe or Square flag on a vendor no longer shows a card button that cannot complete; base v174)\n"
) + s[first_build:]

rep("""        final bool cards = whop ||
            vd['stripeChargesEnabled'] == true ||
            vd['squareConnected'] == true;""",
    """        // v175: Whop only - Stripe is gone from the server and Square was never set up
        final bool cards = whop;""")

out = s.replace("\n", "\r\n") if crlf else s
DST.write_text(out, encoding="utf-8")
print("wrote", DST.name, len(s.splitlines()), "lines")
