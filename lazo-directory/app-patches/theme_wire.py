"""theme_wire.py - JC-LAZO-THEME-1009-001, step 2 of 2 (after theme_rewrite.py)
Wires the mode into each dashboard: loads lazo_theme at start, resolves light/dark at the top of
the root build (so 'system' follows the phone live), and adds Appearance (Light / Dark / Auto)
to the Account screen.
  python theme_wire.py couple|vendor <in.dart> <out.dart>
"""
import sys
from pathlib import Path


def rep(s, old, new, label):
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"{label}: anchor found {n}x: {old[:80]!r}")
    return s.replace(old, new)


PICKER = r'''
// JC-LAZO-THEME-1009-001: the Appearance control - three segments, gold on the chosen one.
Widget _lzThemePicker(void Function(String) onPick) {
  Widget seg(String v, IconData icon, String label) {
    final bool on = _lzThemePref == v;
    return Expanded(
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: () => onPick(v),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 220),
          curve: Curves.easeOutCubic,
          height: 40,
          decoration: BoxDecoration(
            color: on ? const Color(0xFFD9B77C) : Colors.transparent,
            borderRadius: BorderRadius.circular(999),
          ),
          child: Row(mainAxisAlignment: MainAxisAlignment.center, children: <Widget>[
            Icon(icon, size: 16, color: on ? const Color(0xFF3D1C3B) : _lzFg(const Color(0xFF6B5F72))),
            const SizedBox(width: 6),
            Text(label,
                style: TextStyle(
                    fontSize: 13,
                    fontWeight: on ? FontWeight.w800 : FontWeight.w600,
                    color: on ? const Color(0xFF3D1C3B) : _lzFg(const Color(0xFF6B5F72)))),
          ]),
        ),
      ),
    );
  }

  return Container(
    padding: const EdgeInsets.all(4),
    decoration: BoxDecoration(
      color: _lzBg(const Color(0xFFFAF6F0)).withOpacity(_lzDark ? 1 : .9),
      borderRadius: BorderRadius.circular(999),
      border: Border.all(color: _lzLine(const Color(0xFFE6D6B8))),
    ),
    child: Row(children: <Widget>[
      seg('light', Icons.light_mode_rounded, 'Light'),
      seg('dark', Icons.dark_mode_rounded, 'Dark'),
      seg('system', Icons.brightness_auto_rounded, 'Auto'),
    ]),
  );
}
'''

METHODS = r'''
  // JC-LAZO-THEME-1009-001: light / dark / auto, remembered on this device
  void _lzLoadTheme() {
    SharedPreferences.getInstance().then((SharedPreferences p) {
      final String? v = p.getString('lazo_theme');
      if (v != null && v != _lzThemePref && mounted) {
        setState(() => _lzThemePref = v);
      }
    }).catchError((_) {});
  }

  void _lzSetTheme(String v) {
    if (v == _lzThemePref) return;
    HapticFeedback.selectionClick();
    setState(() => _lzThemePref = v);
    SharedPreferences.getInstance()
        .then((SharedPreferences p) => p.setString('lazo_theme', v))
        .catchError((_) => true);
  }

'''


def wire_couple(s):
    s = rep(s, "    super.initState();\n    WidgetsBinding.instance.addPostFrameCallback((_) {\n      final User? u = FirebaseAuth.instance.currentUser;\n      if (u != null) _ensureCoupleChime",
            "    super.initState();\n    _lzLoadTheme(); // JC-LAZO-THEME-1009-001\n    WidgetsBinding.instance.addPostFrameCallback((_) {\n      final User? u = FirebaseAuth.instance.currentUser;\n      if (u != null) _ensureCoupleChime", 'couple initState')
    s = rep(s, "  @override\n  Widget build(BuildContext context) {\n    if (_uid == null) {\n      return _frame(",
            "  @override\n  Widget build(BuildContext context) {\n    _lzDark = _lzResolveDark(context); // JC-LAZO-THEME-1009-001\n    if (_uid == null) {\n      return _frame(", 'couple build')
    s = rep(s, "  Widget _accountRow({\n    required IconData icon,", METHODS + "  Widget _accountRow({\n    required IconData icon,", 'couple methods')
    s = rep(s, "        _accountGroup(label: 'PREFERENCES', rows: <Widget>[\n",
            "        _accountGroup(label: 'PREFERENCES', rows: <Widget>[\n"
            "          // JC-LAZO-THEME-1009-001\n"
            "          Padding(\n"
            "            padding: const EdgeInsets.fromLTRB(14, 13, 14, 13),\n"
            "            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[\n"
            "              Row(children: <Widget>[\n"
            "                _accountIconTile(_lzDark ? Icons.dark_mode_rounded : Icons.light_mode_rounded),\n"
            "                const SizedBox(width: 12),\n"
            "                Expanded(\n"
            "                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[\n"
            "                    Text('Appearance', style: TextStyle(color: _lzFg(plum), fontSize: 14, fontWeight: FontWeight.w700)),\n"
            "                    const SizedBox(height: 2),\n"
            "                    Text(_lzThemePref == 'system' ? 'Follows your phone' : (_lzDark ? 'Dark - mission control' : 'Light'),\n"
            "                        style: TextStyle(fontSize: 12.5, color: _lzFg(muted), height: 1.3)),\n"
            "                  ]),\n"
            "                ),\n"
            "              ]),\n"
            "              const SizedBox(height: 12),\n"
            "              _lzThemePicker(_lzSetTheme),\n"
            "            ]),\n"
            "          ),\n", 'couple account row')
    return s


def wire_vendor(s):
    s = rep(s, "  void initState() {\n    super.initState();\n    final User? u = FirebaseAuth.instance.currentUser;\n    if (u != null) {\n      _uid = u.uid;\n    }\n",
            "  void initState() {\n    super.initState();\n    _lzLoadTheme(); // JC-LAZO-THEME-1009-001\n    final User? u = FirebaseAuth.instance.currentUser;\n    if (u != null) {\n      _uid = u.uid;\n    }\n", 'vendor initState')
    s = rep(s, "  @override\n  Widget build(BuildContext context) {\n    Widget body;\n    if (_uid == null) {",
            "  @override\n  Widget build(BuildContext context) {\n    _lzDark = _lzResolveDark(context); // JC-LAZO-THEME-1009-001\n"
            "    if (!kIsWeb && _lzBarDark != _lzDark) {\n"
            "      // the phone's clock and battery follow the canvas: dark icons on ivory, light on plum-black\n"
            "      _lzBarDark = _lzDark;\n"
            "      SystemChrome.setSystemUIOverlayStyle((_lzDark ? SystemUiOverlayStyle.light : SystemUiOverlayStyle.dark)\n"
            "          .copyWith(statusBarColor: Colors.transparent));\n"
            "    }\n"
            "    Widget body;\n    if (_uid == null) {", 'vendor build')
    s = rep(s, "bool _lzDark = false;\n", "bool _lzDark = false;\nbool? _lzBarDark;\n", 'vendor bar flag')
    s = rep(s, "  Widget _accountView() {\n", METHODS + "  Widget _accountView() {\n", 'vendor methods')
    # the wordmark PNG is plum; on the dark canvas it is tinted ivory
    s = rep(s, "                                    brandUrl,\n                                    height: 24,\n",
            "                                    brandUrl,\n                                    height: 24,\n"
            "                                    color: _lzDark ? const Color(0xFFF3ECE5) : null, // JC-LAZO-THEME-1009-001\n"
            "                                    colorBlendMode: _lzDark ? BlendMode.srcIn : null,\n", 'vendor wordmark')
    # the Appearance card right under the avatar on Your account
    a = s.index("  Widget _accountView() {\n")
    anchor = "            const SizedBox(height: 20),\n            Container(\n              padding: const EdgeInsets.all(18),"
    b = s.index(anchor, a)
    card = ("            const SizedBox(height: 20),\n"
            "            // JC-LAZO-THEME-1009-001\n"
            "            Container(\n"
            "              padding: const EdgeInsets.fromLTRB(18, 16, 18, 16),\n"
            "              decoration: BoxDecoration(\n"
            "                color: _lzBg(card),\n"
            "                borderRadius: BorderRadius.circular(16),\n"
            "                border: Border.all(color: _lzLine(goldLine)),\n"
            "              ),\n"
            "              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[\n"
            "                Text('Appearance', style: TextStyle(color: _lzFg(plum), fontSize: 15, fontWeight: FontWeight.w800)),\n"
            "                const SizedBox(height: 2),\n"
            "                Text(_lzThemePref == 'system' ? 'Follows your device' : (_lzDark ? 'Dark - mission control' : 'Light'),\n"
            "                    style: TextStyle(fontSize: 12.5, color: _lzFg(muted))),\n"
            "                const SizedBox(height: 12),\n"
            "                _lzThemePicker(_lzSetTheme),\n"
            "              ]),\n"
            "            ),\n")
    s = s[:b] + card + s[b:]
    return s


def serif_default(s, label):
    """_serif flips only its own default; a colour a caller passes was already placed by role
    at the call site (and the sky cards pass theirs unflipped on purpose)."""
    sig = "      Color color = plum,\n      double height = 1.05}) {"
    a = s.index("  TextStyle _serif(")
    b = s.index(sig, a)
    s = s[:b] + "      Color? color,\n      double height = 1.05}) {" + s[b + len(sig):]
    end = s.index("\n  }\n", b)
    body = s[b:end]
    n = body.count("_lzFg(color)")
    if n == 0:
        raise SystemExit(label + ': _serif body has no _lzFg(color)')
    body = body.replace("_lzFg(color)", "(color ?? _lzFg(plum))")
    return s[:b] + body + s[end:]


if __name__ == '__main__':
    kind, src, dst = sys.argv[1], sys.argv[2], sys.argv[3]
    s = Path(src).read_text(encoding='utf-8-sig')
    s = serif_default(s, kind)
    s = wire_couple(s) if kind == 'couple' else wire_vendor(s)
    marker = '// ---------------------------------------------------------------- end JC-LAZO-THEME-1009-001\n'
    s = rep(s, marker, PICKER + marker, 'picker')
    Path(dst).write_text(s, encoding='utf-8')
    print('wired', kind, '->', dst)
