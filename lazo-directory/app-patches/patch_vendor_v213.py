"""Vendor v213: first session, June pointers, What's new, phone layout (JC-LAZO-DISCOVER2-1018-VENDOR).

    python app-patches\\patch_vendor_v213.py [base.txt]   # base defaults to Vendor_master_v212.txt
                                                          # writes Vendor_master_v213.txt
- first session: a "Start here" sheet (photos, starting price, Whop) instead of the
  auto-started tour; the tour stays in Account. vendors.startDoneAt marks it shown.
- June pointers on Today, one per session, never in the first session: no price sheet
  after three leads, Whop not connected with a booked couple, no saved replies after five
  replies, calendar feed off after the first booking. Not now -> vendors.pointersDone.
- What's new: a card on Today once per release (vendors.whatsNewSeen), the list in Account.
- phones: the five tabs sit above the hero, so the whole app is visible on the first screen
- the hero no longer carries "Verified reviews drive your ranking..." as a sentence; it is
  the verified badge's tooltip
- pipeline on phones (< 600 px): a list grouped by stage with a Move button, instead of
  three 560 px kanban columns
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Vendor_master_v212.txt"
DST = HERE / "Vendor_master_v213.txt"
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
    "// Build ID: JC-LAZO-DISCOVER2-1018-VENDOR (v213: FIRST SESSION, POINTERS, WHAT'S NEW, PHONE LAYOUT - a Start here "
    "sheet (photos, price, Whop) the first time, instead of the auto tour (the tour stays in Account); one June pointer "
    "per session on Today from the vendor's state; a What's new card once per release and the list in Account; on phones "
    "the five tabs sit above the hero and the pipeline is a list grouped by stage with a Move button; the hero's verified "
    "sentence moved into the badge's tooltip; base v212)\n"
) + s[first_build:]

NEW_METHODS = r'''
  // ---------------- v213: FIRST SESSION, JUNE POINTERS, WHAT'S NEW ----------------
  static const String _kWhatsNewKeyV = '2026-10';
  // [title, line, line, mode or '' for the inbox]
  static const List<List<dynamic>> _kWhatsNewV = <List<dynamic>>[
    <dynamic>['Lazo video calls', 'Call a couple from the thread; their camera stays off until you allow it.', 'Schedule a call (Pro and Studio) with reminders the day before.', ''],
    <dynamic>['Insurance on file', 'Upload your COI once; the venues and planners you work with get it and its renewals.', 'Venues can request it from the thread.', 'profile'],
    <dynamic>['Meal counts and engagement ideas', 'The couple’s meal choices and allergies arrive by table, for the caterer.', 'June finds engagement shoot spots near the couple.', ''],
    <dynamic>['Get booked on Lazo and What you can do', 'A card that ticks itself off as you set up.', 'Every tab and tool, one line each, from the desk button.', 'leads'],
  ];

  void _openWhatsNewV(String mode) {
    setState(() {
      _showAccount = false;
      _editingProfile = false;
      if (mode.isEmpty) {
        _showInbox = true;
      } else {
        _showInbox = false;
        _dashMode = mode;
      }
    });
  }

  Future<void> _markWhatsNewSeenV(String vendorId) async {
    if (vendorId.isEmpty) return;
    try {
      await FirebaseFirestore.instance
          .collection('vendors')
          .doc(vendorId)
          .set(<String, dynamic>{'whatsNewSeen': _kWhatsNewKeyV}, SetOptions(merge: true));
    } catch (_) {}
  }

  Widget _whatsNewCardV(String vendorId, Map<String, dynamic> vd) {
    if (vendorId.isEmpty || vd['startDoneAt'] == null) return const SizedBox.shrink();
    if ((vd['whatsNewSeen'] ?? '') == _kWhatsNewKeyV) return const SizedBox.shrink();
    final List<List<dynamic>> items = _kWhatsNewV.take(3).toList();
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: _glass(
        padding: const EdgeInsets.fromLTRB(18, 14, 18, 8),
        child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(children: <Widget>[
                const Icon(Icons.auto_awesome_rounded, size: 16, color: gold),
                const SizedBox(width: 8),
                Expanded(child: Text('New in Lazo this month', style: _serif(size: 21))),
              ]),
              const SizedBox(height: 6),
              for (final List<dynamic> it in items)
                _Press(
                  onTap: _h(() => _openWhatsNewV(it[3] as String)),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 7),
                    child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                      Container(
                          margin: const EdgeInsets.only(top: 6),
                          width: 7,
                          height: 7,
                          decoration: const BoxDecoration(color: gold, shape: BoxShape.circle)),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Text(it[0] as String,
                                  style: TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800, color: _lzFg(plum))),
                              Text(it[1] as String,
                                  style: TextStyle(fontSize: 12.5, height: 1.35, color: _lzFg(muted))),
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
                      onPressed: _h(() => _whatsNewSheetV(vendorId)),
                      child: Text('Everything new →',
                          style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700, color: _lzFg(plum))),
                    ),
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
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 620),
      builder: (BuildContext ctx) => _lzFrame(ctx,
          icon: Icons.auto_awesome_rounded,
          title: 'What’s new',
          subtitle: 'October 2026',
          children: <Widget>[
            for (final List<dynamic> it in _kWhatsNewV)
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
                      Text('• ${it[1]}', style: TextStyle(fontSize: 13, height: 1.4, color: _lzFg(ink))),
                      Text('• ${it[2]}', style: TextStyle(fontSize: 13, height: 1.4, color: _lzFg(ink))),
                      const SizedBox(height: 8),
                      _Press(
                        onTap: () {
                          Navigator.of(ctx).pop();
                          _openWhatsNewV(it[3] as String);
                        },
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                          decoration: BoxDecoration(
                              color: _lzBg(const Color(0xFFF3EADF)),
                              borderRadius: BorderRadius.circular(999)),
                          child: Text('Open →',
                              style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700, color: _lzFg(plum))),
                        ),
                      ),
                    ]),
              ),
          ]),
    );
  }

  String _pointerKeyV = '';
  Future<void> _dismissPointerV(String vendorId, String key) async {
    if (vendorId.isEmpty) return;
    try {
      await FirebaseFirestore.instance.collection('vendors').doc(vendorId).set(
          <String, dynamic>{'pointersDone': FieldValue.arrayUnion(<String>[key])},
          SetOptions(merge: true));
    } catch (_) {}
  }

  List<dynamic>? _pointerForV(String vendorId, Map<String, dynamic> vd) {
    if (vendorId.isEmpty || vd.isEmpty || vd['startDoneAt'] == null) return null;
    final List<dynamic> done =
        vd['pointersDone'] is List ? vd['pointersDone'] as List : <dynamic>[];
    final List<QueryDocumentSnapshot<Map<String, dynamic>>> leads =
        _liveQ['leads:$vendorId']?.latest?.docs ??
            <QueryDocumentSnapshot<Map<String, dynamic>>>[];
    int replied = 0;
    bool booked = false;
    for (final QueryDocumentSnapshot<Map<String, dynamic>> d in leads) {
      final Map<String, dynamic> m = d.data();
      if (m['respondedAt'] != null || (m['lastMessageRole'] ?? '') == 'vendor') replied++;
      if ((m['status'] ?? '') == 'booked') booked = true;
    }
    final bool hasSheet = (vd['priceSheetUrl'] ?? '').toString().trim().isNotEmpty ||
        (vd['packages'] is List && (vd['packages'] as List).isNotEmpty);
    final bool saved = vd['savedReplies'] is List && (vd['savedReplies'] as List).isNotEmpty;
    final bool feed = (vd['calendarToken'] ?? '').toString().isNotEmpty;
    void editProfile() {
      _openProfileEditor(vendorId, vd);
    }
    // [key, title, body, button, action]
    final List<List<dynamic>> all = <List<dynamic>>[
      if (booked && !_startWhopLive(vd))
        <dynamic>['whop', 'Get paid inside the thread', 'A couple is booked and there is no way to pay you yet. Connect Whop once; invoices and payment plans do the rest.', 'Connect Whop', () { _connectWhopSheet(vendorId); }],
      if (leads.length >= 3 && !hasSheet)
        <dynamic>['sheet', 'Couples ask about price first', 'Three leads and no packages or price sheet on your page. One upload answers it before they write.', 'Add packages', editProfile],
      if (replied >= 5 && !saved)
        <dynamic>['replies', 'Save the reply you keep typing', 'Five replies in. Saved replies drop into the composer with one tap, and June fills in the names.', 'Open inbox', () { setState(() { _showAccount = false; _editingProfile = false; _showInbox = true; }); }],
      if (booked && !feed)
        <dynamic>['feed', 'Your weddings, in your calendar', 'Booked dates and blocked days as a feed in Google or Apple Calendar, so nothing is double-booked.', 'Turn on the feed', () { _calendarFeedSheet(vendorId); }],
    ];
    for (final List<dynamic> p in all) {
      if (done.contains(p[0])) continue;
      if (_pointerKeyV.isEmpty || _pointerKeyV == p[0]) return p;
    }
    return null;
  }

  Widget _pointerCardV(String vendorId, Map<String, dynamic> vd) {
    final List<dynamic>? p = _pointerForV(vendorId, vd);
    if (p == null) return const SizedBox.shrink();
    _pointerKeyV = p[0] as String;
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
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
                      gradient: LinearGradient(colors: <Color>[gold, Color(0xFFC9A45C)])),
                  child: const Icon(Icons.auto_awesome_rounded, size: 17, color: plum),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text('June: ${p[1]}',
                            style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: _lzFg(plum))),
                        const SizedBox(height: 3),
                        Text(p[2] as String,
                            style: TextStyle(fontSize: 12.5, height: 1.4, color: _lzFg(muted))),
                      ]),
                ),
              ]),
              Row(mainAxisAlignment: MainAxisAlignment.end, children: <Widget>[
                TextButton(
                  onPressed: _h(() => _dismissPointerV(vendorId, p[0] as String)),
                  child: Text('Not now', style: TextStyle(fontSize: 12.5, color: _lzFg(muted))),
                ),
                const SizedBox(width: 4),
                FilledButton(
                  style: FilledButton.styleFrom(
                      backgroundColor: gold,
                      foregroundColor: plum,
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))),
                  onPressed: _h(() {
                    _dismissPointerV(vendorId, p[0] as String);
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

  // First session: three things that make the page convert. Replaces the auto tour.
  Future<void> _startHereSheetV(String vendorId, Map<String, dynamic> vd) async {
    if (vendorId.isEmpty) return;
    try {
      await FirebaseFirestore.instance.collection('vendors').doc(vendorId).set(
          <String, dynamic>{'startDoneAt': FieldValue.serverTimestamp()}, SetOptions(merge: true));
    } catch (_) {}
    final List<List<dynamic>> items = _startItemsV(vendorId, vd)
        .where((List<dynamic> i) => <String>['photos', 'price', 'whop'].contains(i[0]) && i[2] != true)
        .toList();
    if (items.isEmpty || !mounted) return;
    const Map<String, String> why = <String, String>{
      'photos': 'Couples scroll photos before they read a word',
      'price': 'Couples self-qualify; you get fewer dead-end leads',
      'whop': 'Invoices and payment plans go straight to you',
    };
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext ctx) => _lzFrame(ctx,
          icon: Icons.flag_rounded,
          title: 'Start here',
          subtitle: 'Couples see your page in search tonight. ${items.length == 1 ? 'One thing makes' : items.length == 2 ? 'Two things make' : 'Three things make'} it convert.',
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
                          shape: BoxShape.circle, border: Border.all(color: gold, width: 1.5))),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(it[1] as String,
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
                child: Text('I’ll do this later', style: TextStyle(fontSize: 13, color: _lzFg(muted))),
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
                child: const Text('Start', style: TextStyle(fontWeight: FontWeight.w800)),
              ),
            ]),
          ]),
    );
  }

  // v213: the pipeline on a phone - a list grouped by stage, Move instead of drag
  Future<void> _pipeMoveSheet(String vendorId, String inquiryId, String current,
      List<List<String>> stages) async {
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 480),
      builder: (BuildContext ctx) => _lzFrame(ctx,
          icon: Icons.swap_vert_rounded,
          title: 'Move to',
          children: <Widget>[
            for (final List<String> st in stages)
              _Press(
                onTap: st[0] == current
                    ? null
                    : () {
                        Navigator.of(ctx).pop();
                        _moveToStage(vendorId, inquiryId, st[0], _kStatusStages.contains(st[0]));
                      },
                child: Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                  decoration: BoxDecoration(
                      color: _lzBg(st[0] == current ? const Color(0xFFF3EADF) : Colors.white),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: _lzLine(st[0] == current ? gold : const Color(0xFFEADFD3)))),
                  child: Row(children: <Widget>[
                    Expanded(
                        child: Text(st[1],
                            style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: _lzFg(plum)))),
                    if (st[0] == current)
                      Text('current', style: TextStyle(fontSize: 11.5, color: _lzFg(muted))),
                  ]),
                ),
              ),
          ]),
    );
  }

  Widget _pipeListPhone(String vendorId, List<List<String>> stages,
      Map<String, List<QueryDocumentSnapshot<Map<String, dynamic>>>> cols) {
    return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          for (final List<String> st in stages) ...<Widget>[
            Padding(
              padding: const EdgeInsets.fromLTRB(2, 10, 2, 6),
              child: Row(children: <Widget>[
                Container(
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                        color: _lzBg(st[0] == 'booked' ? vGreen : st[0] == 'lost' ? muted : plum),
                        shape: BoxShape.circle)),
                const SizedBox(width: 7),
                Expanded(
                    child: Text(st[1],
                        style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800, color: _lzFg(plum)))),
                Text('${cols[st[0]]!.length}',
                    style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: _lzFg(muted))),
              ]),
            ),
            if (cols[st[0]]!.isEmpty)
              Padding(
                padding: const EdgeInsets.fromLTRB(17, 0, 0, 6),
                child: Text('Nobody here', style: TextStyle(fontSize: 12, color: _lzFg(muted))),
              ),
            for (final QueryDocumentSnapshot<Map<String, dynamic>> d in cols[st[0]]!)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(crossAxisAlignment: CrossAxisAlignment.center, children: <Widget>[
                  Expanded(child: _pipeCard(vendorId, d)),
                  const SizedBox(width: 6),
                  IconButton(
                    tooltip: 'Move',
                    visualDensity: VisualDensity.compact,
                    icon: Icon(Icons.swap_vert_rounded, size: 20, color: _lzFg(plum)),
                    onPressed: _h(() => _pipeMoveSheet(vendorId, d.id, st[0], stages)),
                  ),
                ]),
              ),
          ],
        ]);
  }

'''

rep("  // ---------------- v212: GET BOOKED ON LAZO + WHAT YOU CAN DO ----------------\n",
    NEW_METHODS + "  // ---------------- v212: GET BOOKED ON LAZO + WHAT YOU CAN DO ----------------\n")

# first session: Start here instead of the auto tour
rep("""    _tourChecked = true;
    final Map<String, dynamic> u = us.data() ?? <String, dynamic>{};
    if (u['vendorTourDoneAt'] != null) return;
    Future<void>.delayed(const Duration(milliseconds: 900), () {
      if (mounted && !_showInbox && !_showAccount && !_editingProfile)
        _startTour(_vendorTourSteps());
    });
  }""",
    """    final Map<String, dynamic> u = us.data() ?? <String, dynamic>{};
    if (u['vendorTourDoneAt'] != null) {
      _tourChecked = true;
      return;
    }
    // v213: the first session opens Start here (photos, price, Whop) once the
    // vendor doc is here; the eight-step tour waits in Account > Take the tour.
    final DocumentSnapshot<Map<String, dynamic>>? vs = _liveD['vendor:$vendorId']?.latest;
    if (vs == null || !vs.exists) return; // decide next frame
    _tourChecked = true;
    final Map<String, dynamic> vd = vs.data() ?? <String, dynamic>{};
    if (vd['startDoneAt'] != null) return;
    Future<void>.delayed(const Duration(milliseconds: 900), () {
      if (mounted && !_showInbox && !_showAccount && !_editingProfile)
        _startHereSheetV(vendorId, vd);
    });
  }""")

# Today: pointer + what's new under the start card
rep("""                _startCardV(vendorId, vd), // v212""",
    """                _startCardV(vendorId, vd), // v212
                _pointerCardV(vendorId, vd), // v213
                _whatsNewCardV(vendorId, vd), // v213""")

# phones: tabs above the hero
rep("""            return ListView(
              cacheExtent: 4000,
              padding: const EdgeInsets.fromLTRB(18, 10, 18, 32),
              children: <Widget>[
                hero,
                const SizedBox(height: 14),
                _dashModeToggle(),
                if (today) ...<Widget>[""",
    """            return ListView(
              cacheExtent: 4000,
              padding: const EdgeInsets.fromLTRB(18, 10, 18, 32),
              children: <Widget>[
                // v213: the five tabs first, so a phone shows the whole app
                _dashModeToggle(),
                const SizedBox(height: 14),
                hero,
                if (today) ...<Widget>[""")

# hero: the verified sentence becomes the badge's tooltip
rep("""                if (verified)
                  Text(
                      'Verified reviews drive your ranking - and only verified reviews.',
                      style: TextStyle(
                          fontSize: 13, color: ivory.withOpacity(.85))),
""", "")
rep("""    return Tooltip(
      message: 'Verified by Lazo',""",
    """    return Tooltip(
      message: 'Verified by Lazo. Verified reviews drive your ranking - and only verified reviews.',""")

# pipeline: list on phones
rep("""              SizedBox(
                height: 560,
                child: ListView(
                  scrollDirection: Axis.horizontal,
                  children: <Widget>[
                    for (final List<String> st in stages)
                      _pipeColumn(vendorId, st[0], st[1], cols[st[0]]!, stages),
                  ],
                ),
              ),""",
    """              LayoutBuilder(builder: (BuildContext lc, BoxConstraints box) {
                // v213: phones get a list by stage; wider screens keep the kanban
                if (box.maxWidth < 600) return _pipeListPhone(vendorId, stages, cols);
                return SizedBox(
                  height: 560,
                  child: ListView(
                    scrollDirection: Axis.horizontal,
                    children: <Widget>[
                      for (final List<String> st in stages)
                        _pipeColumn(vendorId, st[0], st[1], cols[st[0]]!, stages),
                    ],
                  ),
                );
              }),""")
rep("""                  '${docs.length} thread${docs.length == 1 ? '' : 's'} \\u00b7 drag a card to move it \\u00b7 tap to open',""",
    """                  '${docs.length} thread${docs.length == 1 ? '' : 's'} \\u00b7 ${MediaQuery.of(context).size.width < 600 ? 'tap to open \\u00b7 the arrows move a card' : 'drag a card to move it \\u00b7 tap to open'}',""")

# Account: What's new row after What you can do
rep("""                    _acctLive(Icons.auto_awesome_motion_rounded, 'What you can do', 'Every tab and tool in Lazo, one line each.', () => _whatYouCanDoSheetV()),""",
    """                    _acctLive(Icons.auto_awesome_motion_rounded, 'What you can do', 'Every tab and tool in Lazo, one line each.', () => _whatYouCanDoSheetV()),
                    _acctLive(Icons.auto_awesome_rounded, 'What\\u2019s new', 'This month in Lazo.', () => _whatsNewSheetV(vendorId)),""")

out = s.replace("\n", "\r\n") if crlf else s
DST.write_text(out, encoding="utf-8")
print("wrote", DST.name, len(s.splitlines()), "lines")
