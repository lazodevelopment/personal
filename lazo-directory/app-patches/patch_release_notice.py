"""JC-LAZO-RELEASE-1020: the app-updated notice.

Builds Couple_master_v180.txt from v179 and Vendor_master_v222.txt from v221.

What changes:
  * each widget carries kLzWidgetVersion (its own build number);
  * on start it reads stats/appRelease (public read; written by publish_release.py)
    for the build live in the stores, the store links, a release key, a title and
    the notes;
  * a phone whose widget is older than the store build gets an "Lazo has been
    updated" popup with the notes and an Update button that opens the App Store or
    Google Play (again the next day if they chose Later);
  * everyone else (web, or a phone already on the latest) gets the What's new
    sheet once per release, and the Home card as before, both fed by the doc, so
    the notes change without a store round trip; the baked-in list is the fallback.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


WHATS_NEW = (
    "// What's new: Lazo tells you when it has been updated | On your phone, a note when a newer Lazo is "
    "in the App Store or Google Play, with what changed. | On the web, what's new opens once per release, "
    "and lives in Account. | {open}"
)


def patch(src: str, dst: str, reps: list[tuple[str, str]], header_new: str, header_old: str, open_: str) -> None:
    text = (HERE / src).read_text(encoding="utf-8")
    assert header_old in text, "old Build ID line missing"
    text = text.replace(header_old, header_new + "\n" + WHATS_NEW.format(open=open_) + "\n" + header_old, 1)
    for old, new in reps:
        n = text.count(old)
        if n != 1:
            print(f"!! {src}: expected 1 match, found {n} for:\n{old[:160]}")
            sys.exit(1)
        text = text.replace(old, new)
    (HERE / dst).write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {dst} ({text.count(chr(10))} lines)")


# ------------------------------------------------------------------ shared Dart
def release_block(role: str, ver: int, baked_key_name: str, baked_list_name: str,
                  item_open: str, open_type: str) -> str:
    """The release-notice members, parameterised for the two dashboards."""
    return f'''
  // ---------------- {role_tag(role)}: RELEASE NOTICE (JC-LAZO-RELEASE-1020) ----------------
  // kLzWidgetVersion is this widget's build. stats/appRelease (written by
  // app-patches/publish_release.py) carries the build live in the App Store and
  // Play Store ({role}), the store links, a release key, a title and the notes.
  // A phone whose widget is older than the store build gets an Update popup;
  // everyone else gets What's new once per release, from the doc, so the notes
  // change without a store round trip. The baked-in list below is the fallback.
  static const int kLzWidgetVersion = {ver};
  // Also a string the compiled web build keeps (app-patches/release_watch.py
  // reads it from main.dart.js to see which build is live).
  {"static const String kBuildId = 'JC-LAZO-RELEASE-1020-C180';" if role == "couple" else "// kBuildId above carries the same number for the vendor build."}
  static const String _kIosStore =
      'https://apps.apple.com/us/app/lazo-wedding-planner/id6812863675';
  static const String _kPlayStore =
      'https://play.google.com/store/apps/details?id=com.meetlazo.app';
  Map<String, dynamic> _rel = <String, dynamic>{{}};
  bool _relLoaded = false;
  bool _relPrompted = false;

  Future<void> _loadRelease() async {{
    try {{
      final DocumentSnapshot<Map<String, dynamic>> s = await FirebaseFirestore
          .instance
          .collection('stats')
          .doc('appRelease')
          .get();
      if (!mounted) return;
      setState(() {{
        _rel = s.data() ?? <String, dynamic>{{}};
        _relLoaded = true;
      }});
      // the build this device runs, for support and for the watcher's marker
      SharedPreferences.getInstance()
          .then((SharedPreferences p) => p.setString('lazo_build', kBuildId))
          .catchError((_) => true);
    }} catch (_) {{
      if (mounted) setState(() => _relLoaded = true);
    }}
  }}

  String get _wnKey {{
    final String k = (_rel['key'] ?? '').toString().trim();
    return k.isEmpty ? {baked_key_name} : k;
  }}

  String get _wnTitle {{
    final String t = (_rel['title'] ?? '').toString().trim();
    return t.isEmpty ? 'October 2026' : t;
  }}

  bool get _relIos => !kIsWeb && defaultTargetPlatform == TargetPlatform.iOS;

  /// The build live in this phone's store: {role}Ios / {role}Android when the
  /// watcher has set them, else the shared {role} number.
  int get _relStoreBuild {{
    final dynamic own = _rel[_relIos ? '{role}Ios' : '{role}Android'];
    if (own is num) return own.toInt();
    return _rel['{role}'] is num ? (_rel['{role}'] as num).toInt() : 0;
  }}

  /// This phone runs a widget older than the one in the stores.
  bool get _relOutdated => !kIsWeb && _relStoreBuild > kLzWidgetVersion;

  String get _relStoreName => _relIos ? 'App Store' : 'Google Play';

  String get _relStoreUrl {{
    final String ios = (_rel['ios'] ?? '').toString().trim();
    final String android = (_rel['android'] ?? '').toString().trim();
    if (_relIos) return ios.isEmpty ? _kIosStore : ios;
    return android.isEmpty ? _kPlayStore : android;
  }}

  Future<void> _openStore() async {{
    try {{
      await launchUrl(Uri.parse(_relStoreUrl),
          mode: LaunchMode.externalApplication);
    }} catch (_) {{}}
  }}

  /// Notes for this audience from the release doc; the baked-in list when the
  /// doc has none. Same shape as the baked list: [title, line, line, open].
  List<List<dynamic>> get _wnItems {{
    final dynamic raw = _rel['notes'];
    if (raw is List) {{
      final List<List<dynamic>> out = <List<dynamic>>[];
      for (final dynamic n in raw) {{
        if (n is! Map) continue;
        final String who = (n['for'] ?? 'both').toString();
        if (who != 'both' && who != '{role}') continue;
        final String title = (n['title'] ?? '').toString().trim();
        if (title.isEmpty) continue;
        out.add(<dynamic>[
          title,
          (n['line1'] ?? '').toString(),
          (n['line2'] ?? '').toString(),
          {item_open},
        ]);
      }}
      if (out.isNotEmpty) return out;
    }}
    return {baked_list_name};
  }}

  /// Once a visit, after the plan is on screen: the Update popup when this
  /// phone is behind the stores (again tomorrow after Later), else What's new
  /// once per release.
  void _maybeReleasePrompt(bool seen, VoidCallback showWhatsNew) {{
    if (_relPrompted || !_relLoaded || !mounted) return;
    _relPrompted = true;
    if (_relOutdated) {{
      SharedPreferences.getInstance().then((SharedPreferences p) {{
        final int last = p.getInt('lazo_update_nag_' + _wnKey) ?? 0;
        final int now = DateTime.now().millisecondsSinceEpoch;
        if (now - last < 20 * 3600 * 1000) return;
        p.setInt('lazo_update_nag_' + _wnKey, now);
        if (!mounted) return;
        WidgetsBinding.instance.addPostFrameCallback((_) {{
          if (mounted) _updateSheet();
        }});
      }}).catchError((_) {{}});
      return;
    }}
    if (seen) return;
    WidgetsBinding.instance.addPostFrameCallback((_) {{
      if (mounted) showWhatsNew();
    }});
  }}

  /// One note, compact, inside the Update popup.
  Widget _wnRow(List<dynamic> it) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
          Container(
              margin: const EdgeInsets.only(top: 6),
              width: 7,
              height: 7,
              decoration:
                  const BoxDecoration(color: gold, shape: BoxShape.circle)),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(it[0] as String,
                      style: TextStyle(
                          fontSize: 13.5,
                          fontWeight: FontWeight.w800,
                          color: _lzFg(plum))),
                  Text(it[1] as String,
                      style: TextStyle(
                          fontSize: 12.5, height: 1.35, color: _lzFg(muted))),
                ]),
          ),
        ]),
      );

  /// "Lazo has been updated": the notes, and Update on the App Store / Google
  /// Play. Later closes it; it comes back the next day while the phone is behind.
  Future<void> _updateSheet() async {{
    final List<List<dynamic>> items = _wnItems;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext ctx) => _lzFrame(ctx,
          icon: Icons.system_update_alt_rounded,
          title: 'Lazo has been updated',
          subtitle:
              'Download the latest version from the $_relStoreName to get everything below.',
          children: <Widget>[
            for (final List<dynamic> it in items) _wnRow(it),
          ],
          footer: _lzActions(
              secondary: 'Later',
              onSecondary: () => Navigator.of(ctx).pop(),
              primary: 'Update on the $_relStoreName',
              icon: Icons.open_in_new_rounded,
              onPrimary: () {{
                Navigator.of(ctx).pop();
                _openStore();
              }})),
    );
  }}
'''


def role_tag(role: str) -> str:
    return "v180" if role == "couple" else "v222"


# ------------------------------------------------------------------ COUPLE
COUPLE_OLD_HEADER = "// Build ID: JC-LAZO-VISIBILITY-1019-COUPLE (v179:"
COUPLE_NEW_HEADER = (
    "// Build ID: JC-LAZO-RELEASE-1020-COUPLE (v180: APP UPDATED NOTICE - the widget knows its build "
    "(kLzWidgetVersion) and reads stats/appRelease for the build live in the stores, the store links and "
    "the release notes; a phone behind the stores gets a 'Lazo has been updated' popup with the notes and "
    "Update on the App Store / Google Play (Later = again tomorrow); web and up-to-date phones get What's "
    "new once per release from the doc; the Home card and the Account sheet read the doc too, baked list as "
    "fallback, refreshed for the Oct 18-20 features; base v179)"
)

COUPLE_REPS: list[tuple[str, str]] = [
    # start: read the release doc
    (
        "    _lzLoadTheme(); // JC-LAZO-THEME-1009-001\n    WidgetsBinding.instance.addPostFrameCallback((_) {\n      final User? u = FirebaseAuth.instance.currentUser;",
        "    _lzLoadTheme(); // JC-LAZO-THEME-1009-001\n    _loadRelease(); // v180: stats/appRelease\n    WidgetsBinding.instance.addPostFrameCallback((_) {\n      final User? u = FirebaseAuth.instance.currentUser;",
    ),
    # baked key + list refreshed, release block inserted after
    (
        """  static const String _kWhatsNewKey = '2026-10';
  // [title, line, line, openView] - the current release, newest first
  static const List<List<dynamic>> _kWhatsNew = <List<dynamic>>[
    <dynamic>['Lazo video calls', 'Call any vendor from their thread. Your camera stays off until you turn it on.', 'Vendors on Pro can schedule a call with you, with reminders the day before.', _View.messages],
    <dynamic>['Meal choices on RSVPs', 'Guests pick a meal and note allergies when they RSVP.', 'Send the counts to your caterer in one tap from Guests.', _View.guests],
    <dynamic>['Engagement session questionnaire', 'Your photographer sends it from your thread.', 'June suggests shoot locations near you.', _View.messages],
    <dynamic>['Getting started and What you can do', 'A card that ticks itself off as you plan.', 'Every screen and tool, one line each, from the desk button.', _View.hub],
  ];
""",
        """  static const String _kWhatsNewKey = '2026-10-20';
  // [title, line, line, openView] - the current release, newest first.
  // v180: the fallback when stats/appRelease has no notes (see _wnItems).
  static const List<List<dynamic>> _kWhatsNew = <List<dynamic>>[
    <dynamic>['Your website, your way', 'Choose whether search engines can link to your site and whether it shows in Find a couple.', 'The password row sits right there too, on the Website screen.', _View.website],
    <dynamic>['Collect addresses, message guests, thank-you notes', 'A link and QR guests fill in with their address, from the Website screen.', 'Email a group of guests, and keep thank-you notes straight, from Guests.', _View.guests],
    <dynamic>['Three picks in your checklist', 'Every book-and-hire task shows three vendors from your city, free on your date first.', 'Tap one for the vendor, or See all to browse.', _View.checklist],
    <dynamic>['Planning checklist and invitations', 'A checklist by months out, seeded from your date, with overdue in rose.', 'Printable invitation cards with a QR to your site; guests and budget as CSV from Account.', _View.checklist],
    <dynamic>['Lazo video calls', 'Call any vendor from their thread. Your camera stays off until you turn it on.', 'Vendors on Pro can schedule a call with you, with reminders the day before.', _View.messages],
    <dynamic>['Meal choices on RSVPs', 'Guests pick a meal and note allergies when they RSVP.', 'Send the counts to your caterer in one tap from Guests.', _View.guests],
  ];
"""
        + release_block("couple", 180, "_kWhatsNewKey", "_kWhatsNew",
                        "_viewFor((n['open'] ?? '').toString())", "_View")
        + """
  _View _viewFor(String s) {
    for (final _View v in _View.values) {
      if (v.name == s) return v;
    }
    return _View.hub;
  }
""",
    ),
    # mark seen with the live key
    (
        "      await _coupleRef.set(<String, dynamic>{'whatsNewSeen': _kWhatsNewKey},",
        "      await _coupleRef.set(<String, dynamic>{'whatsNewSeen': _wnKey},",
    ),
    # the Home card: prompt once, live key, live items, Update when behind
    (
        """  Widget _whatsNewCard(Map<String, dynamic> couple) {
    if (couple['startDoneAt'] == null) return const SizedBox.shrink();
    if ((couple['whatsNewSeen'] ?? '') == _kWhatsNewKey) {
      return const SizedBox.shrink();
    }
    final List<List<dynamic>> items = _kWhatsNew.take(3).toList();
""",
        """  Widget _whatsNewCard(Map<String, dynamic> couple) {
    if (couple['startDoneAt'] == null) return const SizedBox.shrink();
    final bool seen = (couple['whatsNewSeen'] ?? '') == _wnKey;
    _maybeReleasePrompt(seen, _whatsNewSheet); // v180
    if (seen && !_relOutdated) {
      return const SizedBox.shrink();
    }
    final List<List<dynamic>> items = _wnItems.take(3).toList();
""",
    ),
    (
        """                Expanded(
                    child: Text('New in Lazo this month',
                        style: _serif(size: 21))),
              ]),
              const SizedBox(height: 6),
              for (final List<dynamic> it in items)
                _Press(
                  onTap: _h(() => setState(() => _view = it[3] as _View)),""",
        """                Expanded(
                    child: Text(
                        _relOutdated
                            ? 'Update Lazo for what\\u2019s new'
                            : 'New in Lazo this month',
                        style: _serif(size: 21))),
              ]),
              const SizedBox(height: 6),
              for (final List<dynamic> it in items)
                _Press(
                  onTap: _h(() => setState(() => _view = it[3] as _View)),""",
    ),
    (
        """                    TextButton(
                      onPressed: _h(_markWhatsNewSeen),
                      child: Text('Got it',
                          style: TextStyle(fontSize: 12, color: _lzFg(muted))),
                    ),
                  ]),
            ]),
      ),
    );
  }

  Future<void> _whatsNewSheet() async {
    _markWhatsNewSeen();
    if (!mounted) return;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 620),
      builder: (BuildContext ctx) => _lzFrame(ctx,
          icon: Icons.auto_awesome_rounded,
          title: 'What’s new',
          subtitle: 'October 2026',
          children: <Widget>[
            for (final List<dynamic> it in _kWhatsNew)""",
        """                    if (_relOutdated)
                      TextButton.icon(
                        onPressed: _h(_openStore),
                        icon: Icon(Icons.system_update_alt_rounded,
                            size: 16, color: _lzFg(plum)),
                        label: Text('Update on the $_relStoreName',
                            style: TextStyle(
                                fontSize: 12.5,
                                fontWeight: FontWeight.w800,
                                color: _lzFg(plum))),
                      )
                    else
                      TextButton(
                        onPressed: _h(_markWhatsNewSeen),
                        child: Text('Got it',
                            style: TextStyle(fontSize: 12, color: _lzFg(muted))),
                      ),
                  ]),
            ]),
      ),
    );
  }

  Future<void> _whatsNewSheet() async {
    _markWhatsNewSeen();
    if (!mounted) return;
    final List<List<dynamic>> items = _wnItems;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 620),
      builder: (BuildContext ctx) => _lzFrame(ctx,
          icon: Icons.auto_awesome_rounded,
          title: 'What’s new',
          subtitle: _relOutdated
              ? '$_wnTitle. Update Lazo from the $_relStoreName to use these.'
              : _wnTitle,
          footer: _relOutdated
              ? _lzActions(
                  secondary: 'Later',
                  onSecondary: () => Navigator.of(ctx).pop(),
                  primary: 'Update on the $_relStoreName',
                  icon: Icons.open_in_new_rounded,
                  onPrimary: () {
                    Navigator.of(ctx).pop();
                    _openStore();
                  })
              : null,
          children: <Widget>[
            for (final List<dynamic> it in items)""",
    ),
]

# ------------------------------------------------------------------ VENDOR
VENDOR_OLD_HEADER = "// Build ID: JC-LAZO-PEARL-1019-VENDOR (v221:"
VENDOR_NEW_HEADER = (
    "// Build ID: JC-LAZO-RELEASE-1020-VENDOR (v222: APP UPDATED NOTICE - the widget knows its build "
    "(kLzWidgetVersion, kBuildId) and reads stats/appRelease for the build live in the stores, the store links "
    "and the release notes; a phone behind the stores gets a 'Lazo has been updated' popup with the notes and "
    "Update on the App Store / Google Play (Later = again tomorrow); web and up-to-date phones get What's new "
    "once per release from the doc; the Today card and the Account sheet read the doc too, baked list as "
    "fallback, refreshed for the Oct 18-20 features; base v221)"
)

VENDOR_REPS: list[tuple[str, str]] = [
    (
        "    _lzLoadTheme(); // JC-LAZO-THEME-1009-001\n    _loadPlaces(); // v198\n",
        "    _lzLoadTheme(); // JC-LAZO-THEME-1009-001\n    _loadRelease(); // v222: stats/appRelease\n    _loadPlaces(); // v198\n",
    ),
    (
        "  static const String kBuildId = 'JC-LAZO-VDASH-1014-197';",
        "  static const String kBuildId = 'JC-LAZO-RELEASE-1020-222';",
    ),
    (
        """  static const String _kWhatsNewKeyV = '2026-10';
  // [title, line, line, mode or '' for the inbox]
  static const List<List<dynamic>> _kWhatsNewV = <List<dynamic>>[
    <dynamic>['Lazo video calls', 'Call a couple from the thread; their camera stays off until you allow it.', 'Schedule a call (Pro and Studio) with reminders the day before.', ''],
    <dynamic>['Insurance on file', 'Upload your COI once; the venues and planners you work with get it and its renewals.', 'Venues can request it from the thread.', 'profile'],
    <dynamic>['Meal counts and engagement ideas', 'The couple’s meal choices and allergies arrive by table, for the caterer.', 'June finds engagement shoot spots near the couple.', ''],
    <dynamic>['Get booked on Lazo and What you can do', 'A card that ticks itself off as you set up.', 'Every tab and tool, one line each, from the desk button.', 'leads'],
  ];
""",
        """  static const String _kWhatsNewKeyV = '2026-10-20';
  // [title, line, line, mode or '' for the inbox]
  // v222: the fallback when stats/appRelease has no notes (see _wnItems).
  static const List<List<dynamic>> _kWhatsNewV = <List<dynamic>>[
    <dynamic>['June drafts your listing', 'Tap Let June draft it under Bio and Services detail; she writes from your name, categories, markets and price.', 'Use it, try again, or keep yours.', 'profile'],
    <dynamic>['Home and travel markets', 'Pick the markets you serve at standard rates, and the ones where a travel fee may apply.', 'Couples searching in every one of them find you.', 'profile'],
    <dynamic>['A cleaner inbox', 'Lost threads leave the inbox; spam gets reported and the sender blocked.', 'Each lead says where it came from: Zola, The Knot, a forwarded email, your site.', ''],
    <dynamic>['Forward your leads', 'Forward any Knot, Zola, WeddingWire or Instagram inquiry to leads@meetlazo.com from your sign-in email.', 'It lands in your inbox as a lead, with its source.', ''],
    <dynamic>['Automations and exports', 'Every rule Lazo runs for you, in one place in Account.', 'Leads and payments as CSV, also from Account.', 'leads'],
    <dynamic>['Lazo video calls', 'Call a couple from the thread; their camera stays off until you allow it.', 'Schedule a call (Pro and Studio) with reminders the day before.', ''],
  ];
"""
        + release_block("vendor", 222, "_kWhatsNewKeyV", "_kWhatsNewV",
                        "(n['open'] ?? '').toString()", "String"),
    ),
    (
        "          .set(<String, dynamic>{'whatsNewSeen': _kWhatsNewKeyV}, SetOptions(merge: true));",
        "          .set(<String, dynamic>{'whatsNewSeen': _wnKey}, SetOptions(merge: true));",
    ),
    (
        """  Widget _whatsNewCardV(String vendorId, Map<String, dynamic> vd) {
    if (vendorId.isEmpty || vd['startDoneAt'] == null) return const SizedBox.shrink();
    if ((vd['whatsNewSeen'] ?? '') == _kWhatsNewKeyV) return const SizedBox.shrink();
    final List<List<dynamic>> items = _kWhatsNewV.take(3).toList();
""",
        """  Widget _whatsNewCardV(String vendorId, Map<String, dynamic> vd) {
    if (vendorId.isEmpty || vd['startDoneAt'] == null) return const SizedBox.shrink();
    final bool seen = (vd['whatsNewSeen'] ?? '') == _wnKey;
    _maybeReleasePrompt(seen, () => _whatsNewSheetV(vendorId)); // v222
    if (seen && !_relOutdated) return const SizedBox.shrink();
    final List<List<dynamic>> items = _wnItems.take(3).toList();
""",
    ),
    (
        """                Expanded(child: Text('New in Lazo this month', style: _serif(size: 21))),
              ]),
              const SizedBox(height: 6),
              for (final List<dynamic> it in items)
                _Press(
                  onTap: _h(() => _openWhatsNewV(it[3] as String)),""",
        """                Expanded(
                    child: Text(
                        _relOutdated
                            ? 'Update Lazo for what\\u2019s new'
                            : 'New in Lazo this month',
                        style: _serif(size: 21))),
              ]),
              const SizedBox(height: 6),
              for (final List<dynamic> it in items)
                _Press(
                  onTap: _h(() => _openWhatsNewV(it[3] as String)),""",
    ),
    (
        """                    TextButton(
                      onPressed: _h(() => _markWhatsNewSeenV(vendorId)),
                      child: Text('Got it', style: TextStyle(fontSize: 12, color: _lzFg(muted))),
                    ),
                  ]),
            ]),
      ),
    );
  }

  Future<void> _whatsNewSheetV(String vendorId) async {
    _markWhatsNewSeenV(vendorId);
    if (!mounted) return;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 620),
      builder: (BuildContext ctx) => _lzFrame(ctx,
          icon: Icons.auto_awesome_rounded,
          title: 'What’s new',
          subtitle: 'October 2026',
          children: <Widget>[
            for (final List<dynamic> it in _kWhatsNewV)""",
        """                    if (_relOutdated)
                      TextButton.icon(
                        onPressed: _h(_openStore),
                        icon: Icon(Icons.system_update_alt_rounded, size: 16, color: _lzFg(plum)),
                        label: Text('Update on the $_relStoreName',
                            style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800, color: _lzFg(plum))),
                      )
                    else
                      TextButton(
                        onPressed: _h(() => _markWhatsNewSeenV(vendorId)),
                        child: Text('Got it', style: TextStyle(fontSize: 12, color: _lzFg(muted))),
                      ),
                  ]),
            ]),
      ),
    );
  }

  Future<void> _whatsNewSheetV(String vendorId) async {
    _markWhatsNewSeenV(vendorId);
    if (!mounted) return;
    final List<List<dynamic>> items = _wnItems;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 620),
      builder: (BuildContext ctx) => _lzFrame(ctx,
          icon: Icons.auto_awesome_rounded,
          title: 'What’s new',
          subtitle: _relOutdated
              ? '$_wnTitle. Update Lazo from the $_relStoreName to use these.'
              : _wnTitle,
          footer: _relOutdated
              ? _lzActions(
                  secondary: 'Later',
                  onSecondary: () => Navigator.of(ctx).pop(),
                  primary: 'Update on the $_relStoreName',
                  icon: Icons.open_in_new_rounded,
                  onPrimary: () {
                    Navigator.of(ctx).pop();
                    _openStore();
                  })
              : null,
          children: <Widget>[
            for (final List<dynamic> it in items)""",
    ),
]


if __name__ == "__main__":
    patch("Couple_master_v179.txt", "Couple_master_v180.txt", COUPLE_REPS, COUPLE_NEW_HEADER, COUPLE_OLD_HEADER, "account")
    patch("Vendor_master_v221.txt", "Vendor_master_v222.txt", VENDOR_REPS, VENDOR_NEW_HEADER, VENDOR_OLD_HEADER, "leads")
