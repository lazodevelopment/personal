"""patch_friendly_errors.py - JC-LAZO-JUNE-ERR-1014-001: June and Jovi never show a raw exception.
A slow or unreachable hub used to print "TimeoutException after 0:00:30.000000: Future not completed" under the core.
Errors now become one plain sentence; the hub's own friendly messages (no account yet, sign in) pass through.
Edits patch_june_native_v6.py (so JuneNative_v6 is regenerated with it) and jovi/jovi_native.dart in place.
  python app-patches\\patch_friendly_errors.py
"""
from pathlib import Path
HERE = Path(__file__).resolve().parent

FRIENDLY = r"""
  // JC-LAZO-JUNE-ERR-1014-001: one plain sentence, never a raw exception
  String _friendlyErr(Object e) {
    final String raw = e.toString().replaceFirst('Exception: ', '').trim();
    debugPrint('assistant load: ' + raw);
    final String low = raw.toLowerCase();
    if (low.contains('timeout') || low.contains('socket') || low.contains('host lookup') || low.contains('clientexception') || low.contains('connection') || low.contains('xmlhttprequest')) {
      return 'I can\'t reach my notes right now. Check your connection, then try again.';
    }
    if (low.contains('sign in') || low.contains('(401)') || low == '401') return 'Please sign in again and I\'ll pick up where we left off.';
    // the hub's own messages are written for people; anything that still looks like code is not shown
    if (raw.isNotEmpty && raw.length < 220 && !RegExp(r'(Exception|Error|Future|0x|\(\d{3}\)|null)').hasMatch(raw)) return raw;
    return 'Something went wrong on my side. Try again in a moment.';
  }
"""


def rep(s, old, new, label, count=1):
    n = s.count(old)
    if n != count:
        raise SystemExit(f"{label}: anchor found {n}x, wanted {count}: {old[:80]!r}")
    return s.replace(old, new)


# ---- June: add the edits to the v6 generator (it reads v5 and writes v6)
p = HERE / "patch_june_native_v6.py"
s = p.read_text(encoding="utf-8")
if "JC-LAZO-JUNE-ERR-1014-001" not in s:
    add = (
        "\n# ---- JC-LAZO-JUNE-ERR-1014-001: never show a raw exception\n"
        "s = rep(s, \"        _err = e.toString().replaceFirst('Exception: ', '');\", \"        _err = _friendlyErr(e);\", \"friendly assign\")\n"
        "s = rep(s, \"  // ---- data\\n\", " + repr(FRIENDLY.lstrip("\n") + "\n  // ---- data\n") + ", \"friendly fn\")\n"
        "s = rep(s, \"Text('June couldn\\\\'t load your data. $_err',\", \"Text(_err,\", \"deck err text\")\n"
        "s = rep(s, \"Text('June couldn\\\\'t load your day. $_err',\", \"Text(_err,\", \"hero err text\")\n"
    )
    anchor = 'out = HERE / "JuneNative_v6.txt"'
    s = rep(s, anchor, add + anchor, "june generator anchor")
    p.write_text(s, encoding="utf-8")
    print("june generator updated")

# ---- Jovi: edit the widget directly
j = HERE / "jovi" / "jovi_native.dart"
t = j.read_text(encoding="utf-8")
if "JC-LAZO-JUNE-ERR-1014-001" not in t:
    t = rep(t, "        _err = e.toString().replaceFirst('Exception: ', '');", "        _err = _friendlyErr(e);", "jovi assign")
    t = rep(t, "  // ---- data\n", FRIENDLY.lstrip("\n") + "\n  // ---- data\n", "jovi fn")
    t = rep(t, "Text('Jovi couldn\\'t load your records. $_err',", "Text(_err,", "jovi err text", count=2)
    j.write_text(t, encoding="utf-8")
    print("jovi updated")
