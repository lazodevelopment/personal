"""Couple v174: Part 3 before-launch gaps (JC-LAZO-GAPS-1018-COUPLE).

    python app-patches\\patch_couple_v174.py [base.txt]   # base defaults to Couple_master_v173.txt
                                                          # writes Couple_master_v174.txt
- Checklist: a full planning checklist by months-out (couples/{cid}/checklist), seeded from
  the wedding date with "Start from the classic list" (59 tasks), tick / add your own /
  long-press to remove, overdue in rose, "on track" at the top; on the rail, the desk
  sheet and What you can do
- Invitations: a card on the Website screen with a digital invitation - a QR code that
  opens the site, the link and an invitation text to copy, printable cards (2 per page)
- Browse: a "Free on our date" refinement that hides vendors who marked the date unavailable
- Account > More > Export your data: guests (with addresses) and budget as CSV
  (download on web, copied on phones)
Guest addresses and any-CSV import already existed (v98/v139), so nothing to add there.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Couple_master_v173.txt"
DST = HERE / "Couple_master_v174.txt"
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
    "// Build ID: JC-LAZO-GAPS-1018-COUPLE (v174: CHECKLIST, INVITATIONS, FREE ON OUR DATE, EXPORT - a planning checklist "
    "by months out seeded from the date (59 tasks, tick, add, remove, overdue in rose); an Invitations card on the website "
    "screen with a QR that opens the site, copyable text and printable cards; a Free-on-our-date refinement on Browse; "
    "guests and budget as CSV from Account; base v173)\n"
) + s[first_build:]

# ---- enum + screen switch + rail + desk + what-you-can-do
rep("enum _View {\n  hub,\n  vendors,\n  registry,", "enum _View {\n  hub,\n  vendors,\n  registry,\n  checklist,")
rep("    if (_view == _View.shopping) return _shoppingScreen(couple);",
    "    if (_view == _View.shopping) return _shoppingScreen(couple);\n    if (_view == _View.checklist) return _checklistScreen(couple);")
rep("""          _railNavRow(
              'Shopping list', Icons.shopping_bag_rounded, _View.shopping),""",
    """          _railNavRow(
              'Shopping list', Icons.shopping_bag_rounded, _View.shopping),
          _railNavRow('Checklist', Icons.checklist_rtl_rounded, _View.checklist),""")
rep("""      <dynamic>[
        'Dream board',
        Icons.auto_awesome_mosaic_rounded,""",
    """      <dynamic>[
        'Checklist',
        Icons.checklist_rtl_rounded,
        () => setState(() => _view = _View.checklist),
        _View.checklist
      ],
      <dynamic>[
        'Dream board',
        Icons.auto_awesome_mosaic_rounded,""")
rep("""      <dynamic>['Plan', 'Dream board', 'Pin Pinterest or Etsy links, photos and colors; share it with your florist', Icons.auto_awesome_mosaic_rounded, false, false, () { setState(() => _view = _View.board); }],""",
    """      <dynamic>['Plan', 'Checklist', 'The whole plan by months out, ticked as you go; add your own', Icons.checklist_rtl_rounded, false, true, () { setState(() => _view = _View.checklist); }],
      <dynamic>['Plan', 'Dream board', 'Pin Pinterest or Etsy links, photos and colors; share it with your florist', Icons.auto_awesome_mosaic_rounded, false, false, () { setState(() => _view = _View.board); }],""")

# ---- browse: free on our date
rep("  bool _fDeals = false;\n", "  bool _fDeals = false;\n  bool _fFree = false; // v174: hides vendors who marked the wedding date unavailable\n")
rep("        if (_fDeals) 'Deals',\n", "        if (_fDeals) 'Deals',\n        if (_fFree) 'Free on our date',\n")
rep("""                toggle('Top rated', 'Strongest verified reviews', _fTop,
                    (bool v) => _fTop = v),""",
    """                toggle('Top rated', 'Strongest verified reviews', _fTop,
                    (bool v) => _fTop = v),
                toggle('Free on our date', 'Hides anyone who marked your date unavailable', _fFree,
                    (bool v) => _fFree = v),""")
rep("                  _fDeals = false;\n", "                  _fDeals = false;\n                  _fFree = false;\n", 1) if s.count("                  _fDeals = false;\n") == 1 else None
rep("                        _fDeals = false;\n", "                        _fDeals = false;\n                        _fFree = false;\n", 1) if s.count("                        _fDeals = false;\n") == 1 else None
rep("""    if (_fDeals && !_hasDeal(v)) {
      return false;
    }
    return true;
  }""",
    """    if (_fDeals && !_hasDeal(v)) {
      return false;
    }
    if (_fFree && _busyOnOurDate(v)) {
      return false;
    }
    return true;
  }

  // v174: vendors keep unavailableDates as yyyy-mm-dd strings
  bool _busyOnOurDate(Map<String, dynamic> v) {
    final dynamic wd = _wcdCouple['weddingDate'];
    if (wd is! Timestamp) return false;
    final DateTime d = wd.toDate();
    final String ymd = '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
    final List<dynamic> busy = v['unavailableDates'] is List ? v['unavailableDates'] as List : const <dynamic>[];
    return busy.contains(ymd);
  }""")

# ---- website: invitations card
rep("""              _liveLinksCard(slug, w),
              const SizedBox(height: 14),""",
    """              _invitationsCard(slug, w), // v174
              const SizedBox(height: 14),
              _liveLinksCard(slug, w),
              const SizedBox(height: 14),""")

# ---- account: export
rep("""          _accountRow(
            icon: Icons.auto_awesome_rounded,
            title: 'What\\u2019s new',
            value: 'This month in Lazo',
            onTap: () => _whatsNewSheet(),
          ),""",
    """          _accountRow(
            icon: Icons.auto_awesome_rounded,
            title: 'What\\u2019s new',
            value: 'This month in Lazo',
            onTap: () => _whatsNewSheet(),
          ),
          _accountRow(
            icon: Icons.download_rounded,
            title: 'Export your data',
            value: 'Guests with addresses, and your budget, as CSV',
            onTap: () => _exportSheet(),
          ),""")

NEW_METHODS = r'''
  // ---------------- v174: CHECKLIST, INVITATIONS, EXPORT ----------------
  // [months before, title]
  static const List<List<dynamic>> _kClassicChecklist = <List<dynamic>>[
    <dynamic>[12, 'Set a budget'], <dynamic>[12, 'Draft the guest count'], <dynamic>[12, 'Pick a date and a season'],
    <dynamic>[12, 'Tour venues'], <dynamic>[11, 'Book the venue'], <dynamic>[11, 'Hire a planner, if you want one'],
    <dynamic>[11, 'Book the photographer'], <dynamic>[10, 'Book the videographer'], <dynamic>[10, 'Start the wedding website'],
    <dynamic>[10, 'Choose the wedding party'], <dynamic>[9, 'Book the caterer'], <dynamic>[9, 'Book the DJ or band'],
    <dynamic>[9, 'Book the florist'], <dynamic>[9, 'Engagement photos'], <dynamic>[8, 'Send save-the-dates'],
    <dynamic>[8, 'Reserve hotel room blocks'], <dynamic>[8, 'Shop for the dress or suit'], <dynamic>[7, 'Book the officiant'],
    <dynamic>[7, 'Book hair and makeup'], <dynamic>[7, 'Register for gifts'], <dynamic>[6, 'Order invitations'],
    <dynamic>[6, 'Book transportation'], <dynamic>[6, 'Plan the honeymoon'], <dynamic>[6, 'Cake tasting and order'],
    <dynamic>[5, 'Order the wedding bands'], <dynamic>[5, 'Finalize the menu'], <dynamic>[5, 'Rentals: tables, chairs, linens'],
    <dynamic>[4, 'Book the rehearsal dinner'], <dynamic>[4, 'Write the ceremony'], <dynamic>[4, 'First fittings'],
    <dynamic>[3, 'Mail the invitations'], <dynamic>[3, 'Check the marriage license rules'], <dynamic>[3, 'Draft the day-of timeline'],
    <dynamic>[2, 'Final dress or suit fitting'], <dynamic>[2, 'Write your vows'], <dynamic>[2, 'Order favors and signage'],
    <dynamic>[2, 'Confirm arrival times with every vendor'], <dynamic>[1, 'RSVP deadline'], <dynamic>[1, 'Seating chart'],
    <dynamic>[1, 'Meal counts to the caterer'], <dynamic>[1, 'Schedule the final payments'], <dynamic>[1, 'Hair and makeup trial'],
    <dynamic>[1, 'Shot list to the photographer'], <dynamic>[1, 'Playlist to the DJ'], <dynamic>[0.5, 'Final headcount to vendors'],
    <dynamic>[0.5, 'Pick up the rings'], <dynamic>[0.5, 'Confirm the timeline with everyone'], <dynamic>[0.5, 'Pack for the honeymoon'],
    <dynamic>[0.25, 'Marriage license in hand'], <dynamic>[0.25, 'Rehearsal'], <dynamic>[0.25, 'Send the day-before note'],
    <dynamic>[0.25, 'Pack an emergency kit'], <dynamic>[0.25, 'Tips in envelopes'], <dynamic>[0, 'Eat breakfast'],
    <dynamic>[0, 'Hand the rings to your best person'], <dynamic>[0, 'Be present'], <dynamic>[-1, 'Thank-you notes'],
    <dynamic>[-1, 'Review your vendors on Lazo'], <dynamic>[-1, 'Preserve the dress or suit'],
  ];

  CollectionReference<Map<String, dynamic>> get _checkRef =>
      _coupleRef.collection('checklist');

  String _checkBucket(num mb) {
    if (mb >= 12) return '12+ months out';
    if (mb >= 9) return '9 to 11 months out';
    if (mb >= 6) return '6 to 8 months out';
    if (mb >= 4) return '4 to 5 months out';
    if (mb >= 2) return '2 to 3 months out';
    if (mb >= 1) return 'The last month';
    if (mb >= 0.5) return 'Two weeks out';
    if (mb > 0) return 'The last week';
    if (mb == 0) return 'The day';
    return 'After';
  }

  DateTime? _checkDue(DateTime? wd, num mb) {
    if (wd == null) return null;
    return wd.subtract(Duration(days: (mb * 30).round()));
  }

  Future<void> _seedChecklist(DateTime? wd) async {
    final WriteBatch b = FirebaseFirestore.instance.batch();
    int i = 0;
    for (final List<dynamic> it in _kClassicChecklist) {
      final num mb = it[0] as num;
      final DateTime? due = _checkDue(wd, mb);
      b.set(_checkRef.doc(), <String, dynamic>{
        'title': it[1],
        'mb': mb,
        'order': i++,
        'due': due == null ? null : Timestamp.fromDate(due),
        'done': false,
        'createdAt': FieldValue.serverTimestamp(),
      });
    }
    await b.commit();
    _toastC('Your checklist is ready: ${_kClassicChecklist.length} things, in order.');
  }

  Future<void> _addChecklistItem(DateTime? wd) async {
    final TextEditingController c = TextEditingController();
    num mb = 3;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 520),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext sc, StateSetter setS) => _lzFrame(ctx,
            icon: Icons.add_task_rounded,
            title: 'Add to the checklist',
            children: <Widget>[
              TextField(
                controller: c,
                autofocus: true,
                textCapitalization: TextCapitalization.sentences,
                style: TextStyle(color: _lzFg(ink), fontSize: 15),
                decoration: InputDecoration(
                  hintText: 'Book the photo booth',
                  filled: true,
                  fillColor: _lzBg(Colors.white),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: gold)),
                  enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: gold)),
                ),
              ),
              const SizedBox(height: 12),
              Text('WHEN', style: TextStyle(fontSize: 10.5, letterSpacing: 2, fontWeight: FontWeight.w800, color: _lzFg(plum))),
              const SizedBox(height: 6),
              Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
                for (final List<dynamic> o in <List<dynamic>>[<dynamic>[12, '12 months out'], <dynamic>[9, '9 months'], <dynamic>[6, '6 months'], <dynamic>[3, '3 months'], <dynamic>[1, 'Last month'], <dynamic>[0.25, 'Last week'], <dynamic>[0, 'The day'], <dynamic>[-1, 'After']])
                  ChoiceChip(
                    label: Text(o[1] as String, style: TextStyle(fontSize: 12, color: mb == o[0] ? plum : _lzFg(plum))),
                    selected: mb == o[0],
                    selectedColor: gold,
                    backgroundColor: _lzBg(Colors.white),
                    side: BorderSide(color: gold.withOpacity(.6)),
                    onSelected: (_) => setS(() => mb = o[0] as num),
                  ),
              ]),
              const SizedBox(height: 14),
              FilledButton(
                style: FilledButton.styleFrom(backgroundColor: gold, foregroundColor: plum, padding: const EdgeInsets.symmetric(vertical: 13)),
                onPressed: () async {
                  final String t = c.text.trim();
                  if (t.isEmpty) return;
                  final DateTime? due = _checkDue(wd, mb);
                  await _checkRef.add(<String, dynamic>{
                    'title': t, 'mb': mb, 'order': 999,
                    'due': due == null ? null : Timestamp.fromDate(due),
                    'done': false, 'mine': true, 'createdAt': FieldValue.serverTimestamp(),
                  });
                  if (ctx.mounted) Navigator.of(ctx).pop();
                },
                child: const Text('Add', style: TextStyle(fontWeight: FontWeight.w800)),
              ),
            ]),
      ),
    );
  }

  Widget _checklistScreen(Map<String, dynamic> couple) {
    final DateTime? wd = couple['weddingDate'] is Timestamp ? (couple['weddingDate'] as Timestamp).toDate() : null;
    return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
      stream: _liveQuery('check:$_cid', () => _checkRef.orderBy('order')),
      initialData: _liveQ['check:$_cid']?.latest,
      builder: (BuildContext c, AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> sn) {
        final List<QueryDocumentSnapshot<Map<String, dynamic>>> docs =
            (sn.data?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[]).toList()
              ..sort((QueryDocumentSnapshot<Map<String, dynamic>> a, QueryDocumentSnapshot<Map<String, dynamic>> b) {
                final num ma = (a.data()['mb'] ?? 0) as num;
                final num mb2 = (b.data()['mb'] ?? 0) as num;
                if (ma != mb2) return mb2.compareTo(ma);
                return ((a.data()['order'] ?? 0) as num).compareTo((b.data()['order'] ?? 0) as num);
              });
        final DateTime now = DateTime.now();
        int done = 0, overdue = 0;
        for (final QueryDocumentSnapshot<Map<String, dynamic>> d in docs) {
          final Map<String, dynamic> m = d.data();
          if (m['done'] == true) {
            done++;
          } else if (m['due'] is Timestamp && (m['due'] as Timestamp).toDate().isBefore(now)) {
            overdue++;
          }
        }
        final bool loaded = sn.connectionState != ConnectionState.waiting || sn.hasData;
        String bucket = '';
        return ListView(
          padding: const EdgeInsets.fromLTRB(18, 16, 18, 120),
          children: <Widget>[
            _subHeader('Checklist',
                trailing: docs.isEmpty
                    ? null
                    : TextButton.icon(
                        onPressed: _h(() => _addChecklistItem(wd)),
                        icon: const Icon(Icons.add_rounded, size: 18, color: gold),
                        label: const Text('Add', style: TextStyle(color: gold, fontWeight: FontWeight.w800)))),
            if (docs.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: _glass(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
                  child: Row(children: <Widget>[
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                        Text('$done of ${docs.length} done', style: _serif(size: 20)),
                        const SizedBox(height: 2),
                        Text(
                            overdue == 0
                                ? 'You’re on track. June keeps an eye on what’s next.'
                                : '$overdue ${overdue == 1 ? 'thing was' : 'things were'} due before today. Tick what’s done, or leave them - it’s your list.',
                            style: TextStyle(fontSize: 12.5, color: _lzFg(overdue == 0 ? muted : const Color(0xFFB04A4A)))),
                      ]),
                    ),
                    SizedBox(
                      width: 48,
                      height: 48,
                      child: Stack(alignment: Alignment.center, children: <Widget>[
                        CircularProgressIndicator(
                            value: docs.isEmpty ? 0 : done / docs.length,
                            strokeWidth: 5,
                            backgroundColor: _lzBg(const Color(0xFFEFE6DA)),
                            valueColor: const AlwaysStoppedAnimation<Color>(gold)),
                        Text('${docs.isEmpty ? 0 : (100 * done / docs.length).round()}%',
                            style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: _lzFg(plum))),
                      ]),
                    ),
                  ]),
                ),
              ),
            if (loaded && docs.isEmpty)
              _glass(
                padding: const EdgeInsets.all(20),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                  Text('The whole plan, by months out', style: _serif(size: 22)),
                  const SizedBox(height: 6),
                  Text(
                      wd == null
                          ? 'Set your wedding date first and every task gets a due date.'
                          : '${_kClassicChecklist.length} things most couples do, each dated from ${_longDate(wd)}. Tick them as you go, add your own, remove what isn’t you.',
                      style: TextStyle(fontSize: 13.5, height: 1.45, color: _lzFg(muted))),
                  const SizedBox(height: 14),
                  Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                    FilledButton(
                      style: FilledButton.styleFrom(backgroundColor: gold, foregroundColor: plum, padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12)),
                      onPressed: _h(() => _seedChecklist(wd)),
                      child: const Text('Start from the classic list', style: TextStyle(fontWeight: FontWeight.w800)),
                    ),
                    OutlinedButton(
                      style: OutlinedButton.styleFrom(foregroundColor: _lzFg(plum), side: const BorderSide(color: gold)),
                      onPressed: _h(() => _addChecklistItem(wd)),
                      child: const Text('Add my own', style: TextStyle(fontWeight: FontWeight.w700)),
                    ),
                  ]),
                ]),
              ),
            for (final QueryDocumentSnapshot<Map<String, dynamic>> d in docs) ...<Widget>[
              if (_checkBucket((d.data()['mb'] ?? 0) as num) != bucket)
                Padding(
                  padding: const EdgeInsets.fromLTRB(4, 14, 0, 6),
                  child: Text((bucket = _checkBucket((d.data()['mb'] ?? 0) as num)).toUpperCase(),
                      style: TextStyle(fontSize: 10.5, letterSpacing: 2, fontWeight: FontWeight.w800, color: _lzFg(ivory.withOpacity(.85)))),
                ),
              _checklistRow(d, now),
            ],
          ],
        );
      },
    );
  }

  Widget _checklistRow(QueryDocumentSnapshot<Map<String, dynamic>> d, DateTime now) {
    final Map<String, dynamic> m = d.data();
    final bool done = m['done'] == true;
    final DateTime? due = m['due'] is Timestamp ? (m['due'] as Timestamp).toDate() : null;
    final bool late = !done && due != null && due.isBefore(now);
    return _Press(
      scale: .99,
      onTap: _h(() => d.reference.set(<String, dynamic>{
            'done': !done,
            'doneAt': done ? null : FieldValue.serverTimestamp(),
          }, SetOptions(merge: true))),
      onLongPress: () async {
        await d.reference.delete();
        _toastC('Removed: ${m['title']}');
      },
      child: Container(
        margin: const EdgeInsets.only(bottom: 6),
        padding: const EdgeInsets.fromLTRB(12, 11, 12, 11),
        decoration: BoxDecoration(
            color: _lzBg(Colors.white.withOpacity(done ? .55 : .92)),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: _lzLine(late ? const Color(0xFFD9A0A0) : const Color(0xFFEADFD3)))),
        child: Row(children: <Widget>[
          Container(
            width: 22,
            height: 22,
            decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: done ? vGreen : Colors.transparent,
                border: Border.all(color: done ? vGreen : (late ? const Color(0xFFB04A4A) : gold), width: 1.5)),
            child: done ? const Icon(Icons.check_rounded, size: 14, color: Colors.white) : null,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
              Text((m['title'] ?? '').toString(),
                  style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: _lzFg(done ? muted : ink),
                      decoration: done ? TextDecoration.lineThrough : TextDecoration.none)),
              if (due != null)
                Text(late ? 'Was due ${_shortDate(due)}' : 'By ${_shortDate(due)}${due.year != now.year ? ' ${due.year}' : ''}',
                    style: TextStyle(fontSize: 11.5, color: _lzFg(late ? const Color(0xFFB04A4A) : muted))),
            ]),
          ),
          if (m['mine'] == true)
            Icon(Icons.person_rounded, size: 14, color: _lzFg(muted)),
        ]),
      ),
    );
  }

  // ---- invitations
  String _siteUrl(String slug) => 'https://meetlazo.com/w/$slug';
  String _qrUrl(String data) =>
      'https://api.qrserver.com/v1/create-qr-code/?size=360x360&margin=12&color=52284F&data=${Uri.encodeComponent(data)}';

  Widget _invitationsCard(String slug, Map<String, dynamic> w) {
    return _glass(
      tint: .6,
      borderColor: gold.withOpacity(.6),
      child: Row(children: <Widget>[
        Container(
          width: 44,
          height: 44,
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(12), color: _lzBg(plum.withOpacity(.1))),
          child: Icon(Icons.mail_rounded, color: _lzFg(plum), size: 22),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
            Text('Invitations', style: TextStyle(color: _lzFg(plum), fontSize: 15.5, fontWeight: FontWeight.w700)),
            const SizedBox(height: 2),
            Text('A digital invite with a QR code that opens your site, text to send, and cards to print.',
                style: TextStyle(fontSize: 12.5, height: 1.35, color: _lzFg(muted))),
          ]),
        ),
        const SizedBox(width: 8),
        FilledButton(
          style: FilledButton.styleFrom(backgroundColor: gold, foregroundColor: plum, padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10)),
          onPressed: _h(() => _inviteSheet(slug, w)),
          child: const Text('Open', style: TextStyle(fontWeight: FontWeight.w800)),
        ),
      ]),
    );
  }

  Future<void> _inviteSheet(String slug, Map<String, dynamic> w) async {
    final Map<String, dynamic> couple = _wcdCouple;
    final String names = (couple['names'] ?? w['names'] ?? 'Our wedding').toString();
    final DateTime? wd = couple['weddingDate'] is Timestamp ? (couple['weddingDate'] as Timestamp).toDate() : null;
    final String when = wd == null ? '' : _longDate(wd);
    final String venue = (w['venueName'] ?? w['venue'] ?? '').toString();
    final String url = _siteUrl(slug);
    final String text = '$names\n${when.isEmpty ? '' : '$when\n'}${venue.isEmpty ? '' : '$venue\n'}\nWe’d love you there. Everything you need, and your RSVP, is at $url';
    String esc(String t) => t.replaceAll('&', '&amp;').replaceAll('<', '&lt;');
    final String card = '<div class="c"><div class="n">${esc(names)}</div>'
        '${when.isEmpty ? '' : '<div class="d">${esc(when)}</div>'}'
        '${venue.isEmpty ? '' : '<div class="v">${esc(venue)}</div>'}'
        '<div class="l">We’d love you there. RSVP and every detail at</div>'
        '<div class="u">${esc(url.replaceFirst('https://', ''))}</div>'
        '<img src="${_qrUrl(url)}" width="120" height="120" alt="QR"/></div>';
    final String page = '<!doctype html><html><head><meta charset="utf-8"><title>${esc(names)} - invitations</title>'
        '<style>@page{margin:14mm}body{margin:0;font-family:Georgia,serif;color:#52284F;background:#fff}'
        '.c{width:5in;height:7in;margin:0 auto 10mm;border:1px solid #D9B77C;border-radius:14px;padding:28px;box-sizing:border-box;text-align:center;display:flex;flex-direction:column;justify-content:center;align-items:center;page-break-inside:avoid}'
        '.n{font-size:34px;line-height:1.1;margin-bottom:12px}.d{font-size:16px;letter-spacing:2px;text-transform:uppercase;margin-bottom:6px}.v{font-size:15px;color:#6B5F72;margin-bottom:18px}'
        '.l{font-family:Helvetica,Arial,sans-serif;font-size:12px;color:#6B5F72;margin-bottom:4px}.u{font-family:Helvetica,Arial,sans-serif;font-size:13px;font-weight:700;margin-bottom:14px}'
        '@media print{.c{page-break-after:always}}</style></head><body>$card$card</body></html>';
    if (!mounted) return;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext ctx) => _lzFrame(ctx,
          icon: Icons.mail_rounded,
          title: 'Invitations',
          subtitle: 'Guests scan the code or open the link; your site has the details and the RSVP.',
          children: <Widget>[
            Center(
              child: Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: gold.withOpacity(.6))),
                child: Image.network(_qrUrl(url), width: 180, height: 180,
                    errorBuilder: (BuildContext c2, Object e, StackTrace? st) => SizedBox(
                        width: 180, height: 180,
                        child: Center(child: Text('QR unavailable offline', style: TextStyle(fontSize: 12, color: _lzFg(muted)))))),
              ),
            ),
            const SizedBox(height: 10),
            Center(child: Text(url.replaceFirst('https://', ''), style: TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700, color: _lzFg(plum)))),
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(color: _lzBg(Colors.white), borderRadius: BorderRadius.circular(12), border: Border.all(color: _lzLine(const Color(0xFFEADFD3)))),
              child: Text(text, style: TextStyle(fontSize: 13, height: 1.45, color: _lzFg(ink))),
            ),
            const SizedBox(height: 12),
            Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
              FilledButton.icon(
                style: FilledButton.styleFrom(backgroundColor: gold, foregroundColor: plum),
                onPressed: () { Clipboard.setData(ClipboardData(text: text)); _toastC('Invitation copied - paste it into a text or an email.'); },
                icon: const Icon(Icons.copy_rounded, size: 16),
                label: const Text('Copy invitation', style: TextStyle(fontWeight: FontWeight.w800)),
              ),
              OutlinedButton.icon(
                style: OutlinedButton.styleFrom(foregroundColor: _lzFg(plum), side: const BorderSide(color: gold)),
                onPressed: () { Clipboard.setData(ClipboardData(text: url)); _toastC('Link copied.'); },
                icon: const Icon(Icons.link_rounded, size: 16),
                label: const Text('Copy link', style: TextStyle(fontWeight: FontWeight.w700)),
              ),
              OutlinedButton.icon(
                style: OutlinedButton.styleFrom(foregroundColor: _lzFg(plum), side: const BorderSide(color: gold)),
                onPressed: () => _openHtml(page, text),
                icon: const Icon(Icons.print_rounded, size: 16),
                label: Text(kIsWeb ? 'Print cards' : 'Copy for printing', style: const TextStyle(fontWeight: FontWeight.w700)),
              ),
            ]),
            const SizedBox(height: 8),
            Text('Printed cards are 5 x 7 inches, two per page. Paper invitations from a print shop come later.',
                style: TextStyle(fontSize: 11.5, color: _lzFg(muted))),
          ]),
    );
  }

  // ---- export
  String _csvCell(Object? v) {
    String t = v == null ? '' : (v is Timestamp ? v.toDate().toIso8601String().substring(0, 10) : v.toString());
    if (t.contains(',') || t.contains('"') || t.contains('\n')) t = '"${t.replaceAll('"', '""')}"';
    return t;
  }

  void _deliverCsv(String name, String csv) {
    if (!kIsWeb) {
      Clipboard.setData(ClipboardData(text: csv));
      _toastC('Copied as CSV - paste it into Numbers, Sheets or an email.');
      return;
    }
    try {
      final html.Blob blob = html.Blob(<String>[csv], 'text/csv');
      final String url = html.Url.createObjectUrlFromBlob(blob);
      html.AnchorElement(href: url)
        ..setAttribute('download', name)
        ..click();
      html.Url.revokeObjectUrl(url);
    } catch (e) {
      Clipboard.setData(ClipboardData(text: csv));
      _toastC('Copied as CSV.');
    }
  }

  Future<void> _exportSheet() async {
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 520),
      builder: (BuildContext ctx) => _lzFrame(ctx,
          icon: Icons.download_rounded,
          title: 'Export your data',
          subtitle: 'Your plan is yours. Two files, no login, nothing held back.',
          children: <Widget>[
            _accountRow(
              icon: Icons.group_rounded,
              title: 'Guests',
              value: 'Name, party, email, phone, address, RSVP, plus-ones, meal, allergies, table',
              onTap: () async {
                final QuerySnapshot<Map<String, dynamic>> qs = await _guestsRef.get();
                const List<String> cols = <String>['name', 'party', 'email', 'phone', 'address', 'rsvp', 'plusOnes', 'meal', 'allergies', 'tableName', 'group', 'side'];
                final StringBuffer b = StringBuffer(cols.join(','))..write('\n');
                for (final QueryDocumentSnapshot<Map<String, dynamic>> d in qs.docs) {
                  b.writeln(cols.map((String k) => _csvCell(d.data()[k])).join(','));
                }
                _deliverCsv('lazo-guests.csv', b.toString());
              },
            ),
            _accountRow(
              icon: Icons.savings_rounded,
              title: 'Budget',
              value: 'Every category with planned, committed and paid',
              onTap: () async {
                final QuerySnapshot<Map<String, dynamic>> qs = await _planRef.get();
                final Set<String> keys = <String>{'category'};
                for (final QueryDocumentSnapshot<Map<String, dynamic>> d in qs.docs) {
                  for (final String k in d.data().keys) {
                    if (d.data()[k] is num || d.data()[k] is String || d.data()[k] is bool) keys.add(k);
                  }
                }
                final List<String> cols = keys.toList();
                final StringBuffer b = StringBuffer(cols.join(','))..write('\n');
                for (final QueryDocumentSnapshot<Map<String, dynamic>> d in qs.docs) {
                  b.writeln(cols.map((String k) => k == 'category' ? _csvCell(d.id) : _csvCell(d.data()[k])).join(','));
                }
                _deliverCsv('lazo-budget.csv', b.toString());
              },
            ),
          ]),
    );
  }
'''

rep("  // ---------------- v173: FIRST SESSION, JUNE POINTERS, WHAT'S NEW ----------------\n",
    NEW_METHODS + "\n  // ---------------- v173: FIRST SESSION, JUNE POINTERS, WHAT'S NEW ----------------\n")

out = s.replace("\n", "\r\n") if crlf else s
DST.write_text(out, encoding="utf-8")
print("wrote", DST.name, len(s.splitlines()), "lines")
