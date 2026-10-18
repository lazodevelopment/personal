"""JuneNative v12: copy that reads right inside the app (JC-LAZO-JUNE-NATIVE-1018-012).

    python app-patches\\patch_june_native_v12.py   # JuneNative_v11.txt -> JuneNative_v12.txt
Two hub-era lines said "in the app" / "open the Lazo app" to people already in the app.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
s = (HERE / "JuneNative_v11.txt").read_text(encoding="utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")


def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, f"expected {n}, found {c}: {a[:90]!r}"
    s = s.replace(a, b)


rep("// Build ID: JC-LAZO-JUNE-NATIVE-1016-011 (011:",
    "// Build ID: JC-LAZO-JUNE-NATIVE-1018-012 (012: the Money and Your team cards no longer say \"in the app\" / \"open the Lazo app\" to someone already in it; base 011) (011:")
rep("""const Text('Open the Lazo app once and your plan appears here.', style: TextStyle(color: _muted))""",
    """const Text('Your vendor team shows here once you add the categories you need.', style: TextStyle(color: _muted))""")
rep("""Text('Set a budget in the app, or say "our budget is 25,000".', style: TextStyle(color: _muted, fontSize: 12.5))""",
    """Text('Say "our budget is 25,000", or set it from the Budget tile.', style: TextStyle(color: _muted, fontSize: 12.5))""")

out = s.replace("\n", "\r\n") if crlf else s
(HERE / "JuneNative_v12.txt").write_text(out, encoding="utf-8")
print("wrote JuneNative_v12.txt", len(s.splitlines()), "lines")
