"""patch_couple_v145.py - JC-LAZO-COUPLE-1007-V145
TALK TO JUNE for couples: a gold "Talk to June" button beside "Ask June" in the
"This week, with June" card opens the June hub (june.meetlazo.com), which now
serves couples too (free): the brief read aloud in her voice, the core, their
team and budget, vendor threads, guests and RSVPs, the day-of timeline, weather
for the big day, and confirm-first actions. The button asks the juneToken
callable (functions-dashboard/june-token.js, any signed-in uid) for a one-hour
custom token and opens kJuneHubUrl?t=<token>, so the couple lands signed in; if
the callable fails it opens the plain URL and they sign in with their Lazo login.

Anchor-and-assert against Couple_master_v144.txt; writes Couple_master_v145.txt.
  python app-patches\\patch_couple_v145.py
"""
from pathlib import Path
HERE = Path(__file__).resolve().parent
src = HERE / "Couple_master_v144.txt"; dst = HERE / "Couple_master_v145.txt"
s = src.read_text(encoding="utf-8")
if "COUPLE-1007-V145" in s:
    raise SystemExit("already patched")

def rep(old, new, label, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"{label}: anchor found {n}x, wanted {count}: {old[:70]!r}")
    s = s.replace(old, new)

# ---- build note
rep("// (v144: WELCOME PAGES LAND PRE-FILLED",
    "// (v145: TALK TO JUNE - a gold button beside Ask June opens the June hub (kJuneHubUrl, june.meetlazo.com) signed in through the juneToken callable (?t=), plain URL as the fallback. JC-LAZO-COUPLE-1007-V145; base v144)\n"
    "// (v144: WELCOME PAGES LAND PRE-FILLED",
    "build note")

# ---- the hub address, next to the category table
rep("  static const List<Map<String, String>> kCategories = [",
    "  // v145: the June hub (june-hub worker on june.meetlazo.com); serves couples and vendors\n"
    "  static const String kJuneHubUrl = 'https://june.meetlazo.com/';\n\n"
    "  static const List<Map<String, String>> kCategories = [",
    "hub url")

# ---- the button, beside Ask June in the week card header
rep('''                    onPressed: _h(() => _askJune('')),
                    child: const Text('Ask June',
                        style: TextStyle(
                            fontSize: 13, fontWeight: FontWeight.w700)),
                  ),
                  const SizedBox(width: 6),''',
'''                    onPressed: _h(() => _askJune('')),
                    child: const Text('Ask June',
                        style: TextStyle(
                            fontSize: 13, fontWeight: FontWeight.w700)),
                  ),
                  const SizedBox(width: 6),
                  // v145: the full June, in her own voice, at june.meetlazo.com
                  FilledButton(
                    style: FilledButton.styleFrom(
                        backgroundColor: gold,
                        foregroundColor: plum,
                        padding: const EdgeInsets.symmetric(
                            horizontal: 14, vertical: 10),
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10))),
                    onPressed: _h(() => _talkToJune()),
                    child: const Text('Talk to June',
                        style: TextStyle(
                            fontSize: 13, fontWeight: FontWeight.w700)),
                  ),
                  const SizedBox(width: 6),''',
    "talk to june button")

# ---- the hand-off, next to the in-card ask
rep("  void _askJune(String q) {",
    '''  // v145: hand the signed-in couple to the June hub with a one-hour custom token
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
    try {
      await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
    } catch (e) {
      debugPrint('LAZO june hub: ' + e.toString());
    }
  }

  void _askJune(String q) {''',
    "talk to june method")

dst.write_text(s, encoding="utf-8")
print("wrote", dst.name, len(s), "chars")
