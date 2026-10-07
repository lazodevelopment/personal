"""patch_june_embed.py - JC-LAZO-JUNE-EMBED-1008-001
June lives inside both dashboards. Couple_master_v146 -> v147, Vendor_master_v182 -> v183.
  - web: the June hub is embedded in place (iframe over the canvas, signed in via juneToken, mic + autoplay allowed)
      couple: the June view is the hub, full height; vendor: the Ask June card becomes the hub (640px)
  - phones: a June card with "Open June" (in-app browser, signed in). The couple's text chat stays on phones.
  python app-patches\\patch_june_embed.py
"""
from pathlib import Path
HERE = Path(__file__).resolve().parent
SNIPPET = (HERE / "june_embed_snippet.dart").read_text(encoding="utf-8")

def rep(s, old, new, label, count=1):
    n = s.count(old)
    if n != count:
        raise SystemExit(f"{label}: anchor found {n}x, wanted {count}: {old[:70]!r}")
    return s.replace(old, new)

JUNE_URL = '''  // JC-LAZO-JUNE-EMBED-1008-001: the hub URL, signed in through the juneToken callable (one hour), plain URL as the fallback
  Future<String> _juneUrl({bool embed = false}) async {
    String url = kJuneHubUrl + (embed ? '?embed=1' : '');
    try {
      final HttpsCallable fn = FirebaseFunctions.instance.httpsCallable(
          'juneToken',
          options: HttpsCallableOptions(timeout: const Duration(seconds: 15)));
      final HttpsCallableResult<dynamic> r =
          await fn.call(<String, dynamic>{});
      final String t = ((r.data as Map)['token'] ?? '').toString();
      if (t.isNotEmpty) {
        url = '$kJuneHubUrl?${embed ? 'embed=1&' : ''}t=${Uri.encodeComponent(t)}';
      }
    } catch (e) {
      debugPrint('LAZO juneToken: ' + e.toString());
    }
    return url;
  }

'''

# ---------------------------------------------------------------- couple
src = HERE / "Couple_master_v146.txt"; dst = HERE / "Couple_master_v147.txt"
s = src.read_text(encoding="utf-8")
if "JUNE-EMBED-1008-001" in s: raise SystemExit("couple already patched")
s = rep(s, "// (v146: COUPLE VIEW DONE PROPERLY",
        "// (v147: JUNE IN THE DASHBOARD - the June view is the hub itself on the web (embedded, signed in, mic and voice on); on phones a June card opens it in the in-app browser and the text chat stays. JC-LAZO-JUNE-EMBED-1008-001; base v146)\n// (v146: COUPLE VIEW DONE PROPERLY", "build note")
# _talkToJune -> uses _juneUrl; mobile opens in-app
s = rep(s, '''  Future<void> _talkToJune() async {
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
  }''',
JUNE_URL + '''  Future<void> _talkToJune() async {
    final String url = await _juneUrl();
    try {
      await launchUrl(Uri.parse(url),
          mode: kIsWeb ? LaunchMode.externalApplication : LaunchMode.inAppWebView);
    } catch (e) {
      debugPrint('LAZO june hub: ' + e.toString());
    }
  }''', "couple talkToJune")
# the June view: hub on web, chat (with an Open June row) on phones
s = rep(s, '''  Widget _juneScreen() {
    _juneLoadHistory();
    return Column(
      children: <Widget>[
        Padding(
          padding: const EdgeInsets.fromLTRB(18, 8, 18, 0),
          child: _subHeader('June',
              trailing: _hasRail ? null : _deskHeaderButton()),
        ),''',
'''  // JC-LAZO-JUNE-EMBED-1008-001: on the web the June view IS the hub
  Widget _juneScreen() {
    if (!kIsWeb) return _juneChatScreen();
    return Column(
      children: <Widget>[
        Padding(
          padding: const EdgeInsets.fromLTRB(18, 8, 18, 0),
          child: _subHeader('June',
              trailing: _hasRail ? null : _deskHeaderButton()),
        ),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(18, 10, 18, 14),
            child: _JuneEmbed(
                key: const ValueKey<String>('june-embed-couple'),
                urlFuture: _juneUrl(embed: true),
                openExternal: _talkToJune),
          ),
        ),
      ],
    );
  }

  Widget _juneChatScreen() {
    _juneLoadHistory();
    return Column(
      children: <Widget>[
        Padding(
          padding: const EdgeInsets.fromLTRB(18, 8, 18, 0),
          child: _subHeader('June',
              trailing: _hasRail ? null : _deskHeaderButton()),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(18, 8, 18, 4),
          child: _JuneEmbed(
              key: const ValueKey<String>('june-embed-couple-phone'),
              urlFuture: _juneUrl(embed: true),
              openExternal: _talkToJune,
              blurb:
                  'Talk to her out loud, hear your brief, and let her message vendors or tick things off for you. One tap, already signed in.'),
        ),''', "couple june screen")
# the embed class, before the file's trailer
s = s.rstrip() + chr(10)*2 + SNIPPET + chr(10) + "// END OF FILE - JC-LAZO-COUPLE-1008-V147" + chr(10)
dst.write_text(s, encoding="utf-8")
print("wrote", dst.name, len(s))

# ---------------------------------------------------------------- vendor
src = HERE / "Vendor_master_v182.txt"; dst = HERE / "Vendor_master_v183.txt"
s = src.read_text(encoding="utf-8")
if "JUNE-EMBED-1008-001" in s: raise SystemExit("vendor already patched")
s = rep(s, "// Build ID: JC-LAZO-VDASH-1005-182 (v182:",
        "// Build ID: JC-LAZO-VDASH-1008-183 (v183: JUNE IN THE DASHBOARD - the Ask June card is the June hub itself on the web (embedded, signed in, mic and voice on); on phones it is a June card that opens the hub in the in-app browser. JC-LAZO-JUNE-EMBED-1008-001; base v182) (v182:", "build note")
s = rep(s, '''  Future<void> _talkToJune() async {
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
  }''',
JUNE_URL + '''  Future<void> _talkToJune() async {
    final String url = await _juneUrl();
    if (kIsWeb) { await _openUrl(url); return; }
    try {
      await launchUrl(Uri.parse(url), mode: LaunchMode.inAppWebView);
    } catch (e) {
      await _openUrl(url);
    }
  }''', "vendor talkToJune")
# the card: header stays, body becomes the embed
a = s.index("  Widget _askJuneCard(String vendorId, Map<String, dynamic> vd) {")
b = s.index("\n  }\n", a) + len("\n  }\n")
card = '''  Widget _askJuneCard(String vendorId, Map<String, dynamic> vd) {
    // JC-LAZO-JUNE-EMBED-1008-001: June herself, in the card
    return _glass(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
      borderColor: gold.withOpacity(.7),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(children: <Widget>[
            _cardIconChip(Icons.auto_awesome_rounded),
            const Expanded(
              child: Text('June',
                  style: TextStyle(
                      color: plum, fontSize: 15, fontWeight: FontWeight.w700)),
            ),
            if (kIsWeb)
              TextButton.icon(
                onPressed: _h(() => _talkToJune()),
                icon: const Icon(Icons.open_in_new_rounded, size: 14, color: plum),
                label: const Text('Open in a tab',
                    style: TextStyle(
                        fontSize: 11.5, fontWeight: FontWeight.w700, color: plum)),
                style: TextButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  minimumSize: const Size(0, 28),
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
              ),
            const SizedBox(width: 6),
            _foldBtn('june'),
          ]),
          const SizedBox(height: 4),
          const Text(
              'She reads your real leads, money and dates. Talk to her, hear today\\u2019s brief, and let her draft, tag and add tasks when you say so.',
              style: TextStyle(fontSize: 11.5, color: muted, height: 1.35)),
          const SizedBox(height: 10),
          _JuneEmbed(
              key: ValueKey<String>('june-embed-' + vendorId),
              urlFuture: _juneUrl(embed: true),
              height: kIsWeb ? 680 : null,
              openExternal: _talkToJune,
              blurb:
                  'Who is waiting on you, this week\\u2019s weddings with the forecast, money due, a first reply for every lead, and a brief read aloud. One tap, already signed in.'),
        ],
      ),
    );
  }
'''
s = s[:a] + card + s[b:]
s = s.rstrip() + chr(10)*2 + SNIPPET + chr(10) + "// END OF FILE - JC-LAZO-VDASH-1008-183" + chr(10)
dst.write_text(s, encoding="utf-8")
print("wrote", dst.name, len(s))
