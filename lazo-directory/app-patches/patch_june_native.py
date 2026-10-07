"""patch_june_native.py - JC-LAZO-JUNE-NATIVE-1008-001
Native June in both dashboards: Couple_master_v147 -> v148, Vendor_master_v183 -> v184.
Replaces the iframe embed (v147/v183) with the JuneNative custom widget (JuneNative_v1.txt), which
is native Dart on web, iOS and Android. The couple's June view is JuneNative(role: 'couple'); the
vendor's Ask June card holds JuneNative(role: 'vendor'). The _JuneEmbed class stays in the files but
is no longer used.
  python app-patches\\patch_june_native.py
"""
from pathlib import Path
HERE = Path(__file__).resolve().parent

def rep(s, old, new, label, count=1):
    n = s.count(old)
    if n != count:
        raise SystemExit(f"{label}: anchor found {n}x, wanted {count}: {old[:70]!r}")
    return s.replace(old, new)

# ---------------------------------------------------------------- couple
src = HERE / "Couple_master_v147.txt"; dst = HERE / "Couple_master_v148.txt"
s = src.read_text(encoding="utf-8")
if "JUNE-NATIVE-1008-001" in s: raise SystemExit("couple already patched")
s = rep(s, "// (v147: JUNE IN THE DASHBOARD",
        "// (v148: JUNE, NATIVE - the June view is the JuneNative custom widget (native Dart: core, voice in and out, brief, waiting, coming up, weather, team, money, guests, reminders, memory, radio) on web and in the store apps. JC-LAZO-JUNE-NATIVE-1008-001; base v147)\n// (v147: JUNE IN THE DASHBOARD", "build note")
a = s.index("  // JC-LAZO-JUNE-EMBED-1008-001: on the web the June view IS the hub\n  Widget _juneScreen() {")
b = s.index("  Widget _juneChatScreen() {")
s = s[:a] + '''  // JC-LAZO-JUNE-NATIVE-1008-001: the June view is June herself, native
  Widget _juneScreen() {
    return Column(
      children: <Widget>[
        Padding(
          padding: const EdgeInsets.fromLTRB(18, 8, 18, 0),
          child: _subHeader('June',
              trailing: _hasRail ? null : _deskHeaderButton()),
        ),
        const Expanded(
          child: Padding(
            padding: EdgeInsets.fromLTRB(18, 10, 18, 14),
            child: JuneNative(role: 'couple'),
          ),
        ),
      ],
    );
  }

''' + s[b:]
s = s.replace("// END OF FILE - JC-LAZO-COUPLE-1008-V147", "// END OF FILE - JC-LAZO-COUPLE-1008-V148")
dst.write_text(s, encoding="utf-8")
print("wrote", dst.name, len(s))

# ---------------------------------------------------------------- vendor
src = HERE / "Vendor_master_v183.txt"; dst = HERE / "Vendor_master_v184.txt"
s = src.read_text(encoding="utf-8")
if "JUNE-NATIVE-1008-001" in s: raise SystemExit("vendor already patched")
s = rep(s, "// Build ID: JC-LAZO-VDASH-1008-183 (v183:",
        "// Build ID: JC-LAZO-VDASH-1008-184 (v184: JUNE, NATIVE - the Ask June card holds the JuneNative custom widget (native Dart) on web and in the store apps. JC-LAZO-JUNE-NATIVE-1008-001; base v183) (v183:", "build note")
s = rep(s, '''          _JuneEmbed(
              key: ValueKey<String>('june-embed-' + vendorId),
              urlFuture: _juneUrl(embed: true),
              height: kIsWeb ? 680 : null,
              openExternal: _talkToJune,
              blurb:
                  'Who is waiting on you, this week\\u2019s weddings with the forecast, money due, a first reply for every lead, and a brief read aloud. One tap, already signed in.'),''',
'''          // JC-LAZO-JUNE-NATIVE-1008-001: June herself, native
          const SizedBox(
            height: 820,
            child: JuneNative(role: 'vendor'),
          ),''', "vendor card body")
s = s.replace("// END OF FILE - JC-LAZO-VDASH-1008-183", "// END OF FILE - JC-LAZO-VDASH-1008-184")
dst.write_text(s, encoding="utf-8")
print("wrote", dst.name, len(s))
