"""Couple v173: first session, June pointers, What's new, phone fixes (JC-LAZO-DISCOVER2-1018-COUPLE).

    python app-patches\\patch_couple_v173.py [base.txt]   # base defaults to Couple_master_v172.txt
                                                          # writes Couple_master_v173.txt
- first session: once setup is done, a "Start here" sheet with the three things that
  matter (guest count, budget, partner) replaces the auto-started 8-step tour; the tour
  stays in Account > Take the tour. couples.startDoneAt marks it shown.
- June pointers: one contextual card per session on Home, never in the first session,
  picked from state (website not published 90+ days out, partner not invited after two
  days, a vendor reply unread for a day, marriage license 45 days out, registry empty
  with a site live). Not now -> couples.pointersDone (never again); Show me opens it.
- What's new: a card on Home once per release (couples.whatsNewSeen), the full list in
  Account > More. Release notes live in the widget (_kWhatsNew); a releases collection
  can replace them later.
- Account shows the wedding date as "March 31, 2027"
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Couple_master_v172.txt"
DST = HERE / "Couple_master_v173.txt"
s = SRC.read_text(encoding="utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")


def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, f"expected {n}, found {c}: {a[:90]!r}"
    s = s.replace(a, b)


first_build = s.index("// Build ID:")
s = s[:first_build] + (
    "// Build ID: JC-LAZO-DISCOVER2-1018-COUPLE (v173: FIRST SESSION, POINTERS, WHAT'S NEW - a Start here sheet (guest "
    "count, budget, partner) the first time the plan is set up, instead of the auto tour (the tour stays in Account); one "
    "June pointer per session on Home from the plan's state, with Not now that sticks; a What's new card once per release "
    "and the list in Account; the Account date reads March 31, 2027; base v172)\n"
) + s[first_build:]

NEW_METHODS = r'''
  // ---------------- v173: FIRST SESSION, JUNE POINTERS, WHAT'S NEW ----------------
  static const String _kWhatsNewKey = '2026-10';
  // [title, line, line, openView] - the current release, newest first
  static const List<List<dynamic>> _kWhatsNew = <List<dynamic>>[
    <dynamic>['Lazo video calls', 'Call any vendor from their thread. Your camera stays off until you turn it on.', 'Vendors on Pro can schedule a call with you, with reminders the day before.', _View.messages],
    <dynamic>['Meal choices on RSVPs', 'Guests pick a meal and note allergies when they RSVP.', 'Send the counts to your caterer in one tap from Guests.', _View.guests],
    <dynamic>['Engagement session questionnaire', 'Your photographer sends it from your thread.', 'June suggests shoot locations near you.', _View.messages],
    <dynamic>['Getting started and What you can do', 'A card that ticks itself off as you plan.', 'Every screen and tool, one line each, from the desk button.', _View.hub],
  ];

  Future<void> _markWhatsNewSeen() async {
    try {
      await _coupleRef.set(<String, dynamic>{'whatsNewSeen': _kWhatsNewKey},
          SetOptions(merge: true));
    } catch (_) {}
  }

  Widget _whatsNewCard(Map<String, dynamic> couple) {
    if (couple['startDoneAt'] == null) return const SizedBox.shrink();
    if ((couple['whatsNewSeen'] ?? '') == _kWhatsNewKey) {
      return const SizedBox.shrink();
    }
    final List<List<dynamic>> items = _kWhatsNew.take(3).toList();
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: _glass(
        padding: const EdgeInsets.fromLTRB(18, 14, 18, 8),
        child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(children: <Widget>[
                const Icon(Icons.auto_awesome_rounded, size: 16, color: gold),
                const SizedBox(width: 8),
                Expanded(
                    child: Text('New in Lazo this month',
                        style: _serif(size: 21))),
              ]),
              const SizedBox(height: 6),
              for (final List<dynamic> it in items)
                _Press(
                  onTap: _h(() => setState(() => _view = it[3] as _View)),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 7),
                    child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                      Container(
                          margin: const EdgeInsets.only(top: 6),
                          width: 7,
                          height: 7,
                          decoration: const BoxDecoration(
                              color: gold, shape: BoxShape.circle)),
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
                                      fontSize: 12.5,
                                      height: 1.35,
                                      color: _lzFg(muted))),
                            ]),
                      ),
                      Icon(Icons.chevron_right_rounded, size: 18, color: _lzFg(muted)),
                    ]),
                  ),
                ),
              Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: <Widget>[
                    TextButton(
                      onPressed: _h(() => _whatsNewSheet()),
                      child: Text('Everything new →',
                          style: TextStyle(
                              fontSize: 12.5,
                              fontWeight: FontWeight.w700,
                              color: _lzFg(plum))),
                    ),
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
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 620),
      builder: (BuildContext ctx) => _lzFrame(ctx,
          icon: Icons.auto_awesome_rounded,
          title: 'What’s new',
          subtitle: 'October 2026',
          children: <Widget>[
            for (final List<dynamic> it in _kWhatsNew)
              Container(
                margin: const EdgeInsets.only(bottom: 10),
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                    color: _lzBg(Colors.white),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: _lzLine(const Color(0xFFEADFD3)))),
                child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(it[0] as String, style: _serif(size: 19)),
                      const SizedBox(height: 4),
                      Text('• ${it[1]}',
                          style: TextStyle(fontSize: 13, height: 1.4, color: _lzFg(ink))),
                      Text('• ${it[2]}',
                          style: TextStyle(fontSize: 13, height: 1.4, color: _lzFg(ink))),
                      const SizedBox(height: 8),
                      _Press(
                        onTap: () {
                          Navigator.of(ctx).pop();
                          setState(() => _view = it[3] as _View);
                        },
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                          decoration: BoxDecoration(
                              color: _lzBg(const Color(0xFFF3EADF)),
                              borderRadius: BorderRadius.circular(999)),
                          child: Text('Open →',
                              style: TextStyle(
                                  fontSize: 12.5,
                                  fontWeight: FontWeight.w700,
                                  color: _lzFg(plum))),
                        ),
                      ),
                    ]),
              ),
          ]),
    );
  }

  // One pointer per session. Picked once (so it does not flip while the
  // plan updates), never in the first session, never again after Not now.
  String _pointerKey = '';
  Future<void> _dismissPointer(String key) async {
    try {
      await _coupleRef.set(<String, dynamic>{
        'pointersDone': FieldValue.arrayUnion(<String>[key])
      }, SetOptions(merge: true));
    } catch (_) {}
  }

  List<dynamic>? _pointerFor(Map<String, dynamic> couple,
      List<QueryDocumentSnapshot<Map<String, dynamic>>> inqs, int? daysOut) {
    if (couple.isEmpty || couple['startDoneAt'] == null) return null;
    final List<dynamic> done =
        couple['pointersDone'] is List ? couple['pointersDone'] as List : <dynamic>[];
    final Map<String, dynamic> st = Map<String, dynamic>.from(
        (couple['starts'] as Map?) ?? <String, dynamic>{});
    final List<QueryDocumentSnapshot<Map<String, dynamic>>> siteDocs =
        _liveQ['site:$_cid']?.latest?.docs ??
            <QueryDocumentSnapshot<Map<String, dynamic>>>[];
    final bool siteOn = siteDocs.isNotEmpty;
    final Map<String, dynamic> site =
        siteOn ? siteDocs.first.data() : <String, dynamic>{};
    final DateTime now = DateTime.now();
    final dynamic created = couple['createdAt'];
    final int ageDays = created is Timestamp ? now.difference(created.toDate()).inDays : 0;
    bool unreadReply = false;
    for (final QueryDocumentSnapshot<Map<String, dynamic>> d in inqs) {
      final Map<String, dynamic> m = d.data();
      final dynamic at = m['lastMessageAt'];
      final dynamic read = m['coupleLastReadAt'];
      if ((m['lastMessageRole'] ?? '') == 'vendor' &&
          at is Timestamp &&
          now.difference(at.toDate()).inHours >= 24 &&
          (read is! Timestamp || read.compareTo(at) < 0)) {
        unreadReply = true;
      }
    }
    // [key, title, body, button, action]
    final List<List<dynamic>> all = <List<dynamic>>[
      if (unreadReply)
        <dynamic>['reply', 'A vendor answered you', 'A reply has been waiting a day. First reply wins their calendar too.', 'Open messages', () { setState(() => _view = _View.messages); }],
      if (daysOut != null && daysOut <= 45 && daysOut >= 0 && couple['licenseDone'] != true)
        <dynamic>['license', 'Your marriage license', 'Most counties issue it in minutes, but each has a window. Day-of has the fee, the wait and the office for yours.', 'See the license', () { setState(() => _view = _View.dayof); }],
      if (!siteOn && daysOut != null && daysOut > 90)
        <dynamic>['website', 'Your site is one tap from live', 'Story, RSVPs with meals, registry and hotels, on meetlazo.com. Guests can RSVP the day you send the link.', 'Open website', () { setState(() => _view = _View.website); }],
      if (st['partner'] != true && ageDays >= 2 && !(_liveQ['cinv:$_cid']?.latest?.docs.isNotEmpty ?? false))
        <dynamic>['partner', 'Plan together', 'Invite your partner: same plan, same inbox, nothing to forward.', 'Invite', () { _partnerSheet(couple); }],
      if (siteOn && !(site['registries'] is List && (site['registries'] as List).isNotEmpty))
        <dynamic>['registry', 'Add a registry link', 'Any store, fund or charity. It shows on your website the moment you add it.', 'Open registry', () { setState(() => _view = _View.registry); }],
    ];
    for (final List<dynamic> p in all) {
      if (done.contains(p[0])) continue;
      if (_pointerKey.isEmpty || _pointerKey == p[0]) return p;
    }
    return null;
  }

  Widget _pointerCard(Map<String, dynamic> couple,
      List<QueryDocumentSnapshot<Map<String, dynamic>>> inqs, int? daysOut) {
    final List<dynamic>? p = _pointerFor(couple, inqs, daysOut);
    if (p == null) return const SizedBox.shrink();
    _pointerKey = p[0] as String;
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: _glass(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 10),
        borderColor: gold,
        child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                Container(
                  width: 34,
                  height: 34,
                  decoration: const BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(colors: <Color>[gold, gold2])),
                  child: const Icon(Icons.auto_awesome_rounded, size: 17, color: plum),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text('June: ${p[1]}',
                            style: TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.w800,
                                color: _lzFg(plum))),
                        const SizedBox(height: 3),
                        Text(p[2] as String,
                            style: TextStyle(
                                fontSize: 12.5, height: 1.4, color: _lzFg(muted))),
                      ]),
                ),
              ]),
              Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: <Widget>[
                    TextButton(
                      onPressed: _h(() => _dismissPointer(p[0] as String)),
                      child: Text('Not now',
                          style: TextStyle(fontSize: 12.5, color: _lzFg(muted))),
                    ),
                    const SizedBox(width: 4),
                    FilledButton(
                      style: FilledButton.styleFrom(
                          backgroundColor: gold,
                          foregroundColor: plum,
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(10))),
                      onPressed: _h(() {
                        _dismissPointer(p[0] as String);
                        (p[4] as void Function())();
                      }),
                      child: Text(p[3] as String,
                          style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800)),
                    ),
                  ]),
            ]),
      ),
    );
  }

  // First session: three things, five minutes. Replaces the auto tour.
  Future<void> _startHereSheet(Map<String, dynamic> couple) async {
    try {
      await _coupleRef.set(<String, dynamic>{'startDoneAt': FieldValue.serverTimestamp()},
          SetOptions(merge: true));
    } catch (_) {}
    final List<List<dynamic>> items = _startItems(couple, _wcdInqs)
        .where((List<dynamic> i) => <String>['guests', 'budget', 'partner'].contains(i[0]) && i[2] != true)
        .toList();
    if (items.isEmpty || !mounted) return;
    const Map<String, String> why = <String, String>{
      'guests': 'Venues and caterers quote by headcount',
      'budget': 'June splits it across 15 categories for you',
      'partner': 'Same plan, same inbox',
    };
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext ctx) => _lzFrame(ctx,
          icon: Icons.flag_rounded,
          title: 'Start here',
          subtitle: '${items.length == 1 ? 'One thing' : items.length == 2 ? 'Two things' : 'Three things'}, a few minutes. Everything else can wait for June.',
          children: <Widget>[
            for (final List<dynamic> it in items)
              Container(
                padding: const EdgeInsets.symmetric(vertical: 10),
                decoration: BoxDecoration(
                    border: Border(top: BorderSide(color: _lzLine(const Color(0xFFF0E8DD))))),
                child: Row(children: <Widget>[
                  Container(
                      width: 22,
                      height: 22,
                      decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          border: Border.all(color: gold, width: 1.5))),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text((it[1] as String).replaceFirst('Add your ', 'Your ').replaceFirst('Set a ', 'Your '),
                              style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: _lzFg(plum))),
                          Text(why[it[0] as String] ?? '',
                              style: TextStyle(fontSize: 12, color: _lzFg(muted))),
                        ]),
                  ),
                  _Press(
                    onTap: () {
                      Navigator.of(ctx).pop();
                      (it[4] as void Function())();
                    },
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                      decoration: BoxDecoration(
                          color: _lzBg(const Color(0xFFF3EADF)),
                          borderRadius: BorderRadius.circular(999)),
                      child: Text(it[3] as String,
                          style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700, color: _lzFg(plum))),
                    ),
                  ),
                ]),
              ),
            const SizedBox(height: 14),
            Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: <Widget>[
              TextButton(
                onPressed: () => Navigator.of(ctx).pop(),
                child: Text('I’ll do this later',
                    style: TextStyle(fontSize: 13, color: _lzFg(muted))),
              ),
              FilledButton(
                style: FilledButton.styleFrom(
                    backgroundColor: gold,
                    foregroundColor: plum,
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 11),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                onPressed: () {
                  Navigator.of(ctx).pop();
                  (items.first[4] as void Function())();
                },
                child: Text('Start with ${(items.first[0] as String) == 'guests' ? 'guests' : (items.first[0] as String) == 'budget' ? 'the budget' : 'your partner'}',
                    style: const TextStyle(fontWeight: FontWeight.w800)),
              ),
            ]),
          ]),
    );
  }
'''

rep("  // ---------------- v172: GETTING STARTED + WHAT YOU CAN DO ----------------\n",
    NEW_METHODS + "\n  // ---------------- v172: GETTING STARTED + WHAT YOU CAN DO ----------------\n")

# first session: Start here instead of the auto tour (the tour stays in Account)
rep("""    final bool doneForMe = doneBy.contains(_uid) ||
        (doneBy.isEmpty && couple['tourDoneAt'] != null && _uid == _cid);
    if (doneForMe) {
      _tourChecked = true;
      return;
    }
    _tourChecked = true;
    Future<void>.delayed(const Duration(milliseconds: 900), () {
      if (mounted && _view == _View.hub)
        _startTour(_coupleTourSteps(needsSetup: needsSetup));
    });
  }""",
    """    final bool doneForMe = doneBy.contains(_uid) ||
        (doneBy.isEmpty && couple['tourDoneAt'] != null && _uid == _cid);
    if (doneForMe) {
      _tourChecked = true;
      return;
    }
    // v173: the first session opens Start here (three things) once the plan is
    // set up; the eight-step tour waits in Account > Take the tour.
    if (needsSetup) return; // decide again once the setup sheet is done
    _tourChecked = true;
    if (couple['startDoneAt'] != null) return;
    Future<void>.delayed(const Duration(milliseconds: 900), () {
      if (mounted && _view == _View.hub) _startHereSheet(couple);
    });
  }""")

# Home: pointer + what's new under the getting-started card
rep("""              // v172: getting started, ticks itself off
              if (!needsSetup) _startCard(couple, inqs),""",
    """              // v172: getting started, ticks itself off
              if (!needsSetup) _startCard(couple, inqs),
              // v173: one June pointer per session, and what's new once per release
              if (!needsSetup) _pointerCard(couple, inqs, daysOut),
              if (!needsSetup) _whatsNewCard(couple),""")

# Account: long date + What's new row
rep("""            title: 'Wedding date',
            value: weddingDate == null
                ? 'Set your date'
                : '${weddingDate.month}/${weddingDate.day}/${weddingDate.year}',""",
    """            title: 'Wedding date',
            value: weddingDate == null
                ? 'Set your date'
                : _longDate(weddingDate),""")
rep("""          _accountRow(
            icon: Icons.auto_awesome_motion_rounded,
            title: 'What you can do',
            value: 'Every screen and tool in Lazo, one line each',
            onTap: () => _whatYouCanDoSheet(),
          ),""",
    """          _accountRow(
            icon: Icons.auto_awesome_motion_rounded,
            title: 'What you can do',
            value: 'Every screen and tool in Lazo, one line each',
            onTap: () => _whatYouCanDoSheet(),
          ),
          _accountRow(
            icon: Icons.auto_awesome_rounded,
            title: 'What\\u2019s new',
            value: 'This month in Lazo',
            onTap: () => _whatsNewSheet(),
          ),""")

out = s.replace("\n", "\r\n") if crlf else s
DST.write_text(out, encoding="utf-8")
print("wrote", DST.name, len(s.splitlines()), "lines")
