"""patch_vendor_v181.py - JC-LAZO-VDASH-1005-181
Talk to June opens the hub already signed in: the button calls the juneToken
callable (functions-dashboard/june-token.js, build 022) for a one-hour custom
token and opens kJuneHubUrl?t=<token>; the hub exchanges it with Firebase and
the vendor never types a second password. If the callable fails (offline, old
functions), it falls back to the plain hub URL exactly as v180 did.

Anchor-and-assert against Vendor_master_v180.txt; writes Vendor_master_v181.txt.
  python app-patches\\patch_vendor_v181.py
"""
from pathlib import Path
HERE = Path(__file__).resolve().parent
src = HERE / "Vendor_master_v180.txt"; dst = HERE / "Vendor_master_v181.txt"
s = src.read_text(encoding="utf-8")
if "VDASH-1005-181" in s:
    raise SystemExit("already patched")

def rep(old, new, label, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"{label}: anchor found {n}x, wanted {count}: {old[:70]!r}")
    s = s.replace(old, new)

rep("// Build ID: JC-LAZO-VDASH-1004-180 (v180:",
    "// Build ID: JC-LAZO-VDASH-1005-181 (v181: TALK TO JUNE SIGNED IN - the button asks the juneToken callable for a custom token and opens the hub with ?t=, falling back to the plain URL. base v180)\n// (v180:",
    "build id")

rep("              onPressed: _h(() => _openUrl(kJuneHubUrl)),",
    "              onPressed: _h(() => _talkToJune()),",
    "button handler")

rep("  Future<void> _openUrl(String url) async {",
    '''  // v181: hand the signed-in vendor to the June hub with a one-hour custom token
  Future<void> _talkToJune() async {
    String url = kJuneHubUrl;
    try {
      final HttpsCallable fn = FirebaseFunctions.instance.httpsCallable(
          'juneToken',
          options: HttpsCallableOptions(timeout: const Duration(seconds: 15)));
      final HttpsCallableResult<dynamic> r =
          await fn.call(<String, dynamic>{});
      final String t = ((r.data as Map)['token'] ?? '').toString();
      if (t.isNotEmpty) {
        url = '$kJuneHubUrl?t=${Uri.encodeComponent(t)}';
      }
    } catch (e) {
      debugPrint('LAZO juneToken: ' + e.toString());
    }
    await _openUrl(url);
  }

  Future<void> _openUrl(String url) async {''',
    "talk to june method")

dst.write_text(s, encoding="utf-8")
print("wrote", dst.name, len(s), "chars")
