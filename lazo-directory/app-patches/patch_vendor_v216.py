"""Vendor v216: Whop only on Money (JC-LAZO-WHOPONLY-1018-VENDOR).

    python app-patches\\patch_vendor_v216.py [base.txt]   # base defaults to Vendor_master_v215.txt
                                                          # writes Vendor_master_v216.txt
- the Get paid card drops the Stripe and Square sections. Lazo left Stripe (stripeConnectStart is
  not deployed, so Connect Stripe failed) and Square was never set up (sandbox with placeholder
  credentials). What stays: Set up Whop, retainer settings, and the vendor's own payment links.
  The Stripe/Square code paths stay in the file, unreachable, for a later decision.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Vendor_master_v215.txt"
DST = HERE / "Vendor_master_v216.txt"
s = SRC.read_text(encoding="utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")

first_build = s.index("// Build ID:")
s = s[:first_build] + (
    "// Build ID: JC-LAZO-WHOPONLY-1018-VENDOR (v216: WHOP ONLY - the Get paid card no longer offers Connect Stripe or "
    "Connect Square (neither is live on the server); Set up Whop and the vendor's own payment links remain; base v215)\n"
) + s[first_build:]

start = s.index("          // ---- Stripe ----\n")
end = s.index("          // ---- payment links ----\n")
assert 0 < end - start < 9000, (start, end)
block = s[start:end]
assert "'Connect Stripe'" in block and "'Connect Square'" in block and block.count("_connectSquare(vendorId)") == 1
s = s[:start] + "          // v216: Stripe and Square sections removed - Lazo is Whop only (see _connectStripe / _connectSquare, unreachable)\n" + s[end:]

out = s.replace("\n", "\r\n") if crlf else s
DST.write_text(out, encoding="utf-8")
print("wrote", DST.name, len(s.splitlines()), "lines")
