import sys
s = open(sys.argv[1], encoding="utf-8").read()
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, old[:60]
    s = s.replace(old, new)
rep("// Build ID: JC-LAZO-AUTH-0919-021 (v21:", "// Build ID: JC-LAZO-AUTH-1007-022 (v22: WELCOME PAGES RIDE THROUGH SIGNUP - the meetlazo.com/welcome/<hook>/ ad pages send ?from=welcome-<hook>&intent=&names=&date=&metro=&design=&source=&guests= plus utm_*; goNamed drops the query, so those keys are stashed in SharedPreferences 'lazo_pending_welcome' on arrival (the couple dashboard v144+ reads them once, pre-fills the plan and writes couples.acq, then clears the key); an ad visitor who is signed out lands straight on the couple signup form; from/intent join signupSource. Replaces the separate stashWelcomeParams custom action. base v21)\n// (v21:")
rep("import 'dart:math' as math;\n", "import 'dart:convert';\nimport 'dart:math' as math;\n")
rep("  static const String kPrefSave = 'lazo_pending_save';\n", "  static const String kPrefSave = 'lazo_pending_save';\n  // v22: the ad landing pages' hand-off, read by LazoCoupleDashboard.\n  static const String kPrefWelcome = 'lazo_pending_welcome';\n")
rep("        'template',\n        'save',\n      ]) {", "        'template',\n        'save',\n        'from',\n        'intent',\n      ]) {")
rep("      _stashDeepLink();\n      _routeIfSignedIn();", "      _stashWelcome();\n      _stashDeepLink();\n      _routeIfSignedIn();")
rep("  Future<void> _clearPendingRole() async {", '''  // v22: a couple arriving from meetlazo.com/welcome/<hook>/ (the Meta ad
  // funnels). Everything the page knew about them rides in one preference;
  // the dashboard reads it once and pre-fills names, date, metro and design.
  Future<void> _stashWelcome() async {
    try {
      final Map<String, String> q = Uri.base.queryParameters;
      final bool ours = (q['from'] ?? '').startsWith('welcome') ||
          (q['intent'] ?? '').isNotEmpty ||
          (q['names'] ?? '').isNotEmpty ||
          (q['date'] ?? '').isNotEmpty;
      if (!ours) return;
      const List<String> keep = <String>[
        'from',
        'intent',
        'names',
        'date',
        'metro',
        'design',
        'template',
        'source',
        'guests',
        'month',
        'utm_source',
        'utm_medium',
        'utm_campaign',
        'utm_content',
        'utm_term',
        'fbclid'
      ];
      final Map<String, String> out = <String, String>{};
      for (final String k in keep) {
        final String v = (q[k] ?? '').trim();
        if (v.isNotEmpty) out[k] = v.length > 200 ? v.substring(0, 200) : v;
      }
      if (out.isEmpty) return;
      final SharedPreferences prefs = await SharedPreferences.getInstance();
      await prefs.setString(kPrefWelcome, jsonEncode(out));
      // The ad already asked "planning a wedding?" - skip the role screen.
      if (mounted &&
          FirebaseAuth.instance.currentUser == null &&
          _mode == _Mode.welcome) {
        final String nm = (out['names'] ?? '').trim();
        setState(() {
          _rolePick = 'couple';
          _mode = _Mode.signup;
          if (nm.isNotEmpty && _name.text.trim().isEmpty) {
            _name.text = nm.split(RegExp(r'\s*(&|and|\+)\s*')).first.trim();
          }
        });
      }
    } catch (_) {}
  }

  Future<void> _clearPendingRole() async {''')
rep("// END OF FILE - JC-LAZO-AUTH-0919-021", "// END OF FILE - JC-LAZO-AUTH-1007-022")
open(sys.argv[2], "w", encoding="utf-8", newline="\n").write(s)
print("ok", len(s))
