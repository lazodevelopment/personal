r"""patch_vendor_v194.py - Vendor v193 -> v194 (JC-LAZO-VDASH-1014-194)
WIDGETS UNDER THE SKY. The right rail on Today (and the end of Today on
phones) becomes a stack of widgets the vendor chooses and orders: drag the
grip (or long-press on a phone) to move one, Customize to add or remove.
Order and choice live on vendors.layout.rail and follow them across devices.

  weather    The sky (as before)              consults   Calls and tours (as before)
  analytics  Your page: profile views (7 days, change), where visitors came
             from, couples who wrote (30 days, change), booked this year,
             inquiry-to-booking rate, rank in the metro
  calendar   Availability: this month with booked, blocked and asked-about dates
  funnel     Pipeline at a glance: new, talking, booked, lost
  goal       Season goal: bookings and revenue against a goal they set
  hotdates   Most-asked dates: the dates couples ask about most
  money      Money this month (the Money card)
  reviews    Rating, count and the latest review
  notes      A private notepad (users/{uid}.vendorNotes, never on the public doc)

    python app-patches\patch_vendor_v194.py
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
s = (HERE / "Vendor_master_v193.txt").read_text(encoding="utf-8")
OUT = HERE / "Vendor_master_v194.txt"


def rep(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"anchor found {n}x (want {count}): {old[:80]!r}")
    s = s.replace(old, new)


rep("// Build ID: JC-LAZO-VDASH-1014-193 (v193:", "// Build ID: JC-LAZO-VDASH-1014-194 (v194: WIDGETS UNDER THE SKY - the Today rail is a stack of widgets the vendor picks and drags into order: weather, consults, Your page analytics, availability calendar, pipeline at a glance, season goal, most-asked dates, money this month, reviews, notes; vendors.layout.rail. base v193) (v193:")

rep("        _syncFolds(vd);", "        _syncFolds(vd);\n        _syncRail(vd);")

# Today: the rail is the widget stack (phones get it at the end of the column)
rep("""                if (!wide) ...<Widget>[
                  const SizedBox(height: 16),
                  sky,
                  consults,
                ],
              ];
              // phones fold the rail into the column above, so only desktop
              // gets a separate rail - otherwise June and the sky show twice
              railKids = wide
                  ? <Widget>[sky, consults]
                  : <Widget>[];""", """                if (!wide) ...<Widget>[
                  const SizedBox(height: 16),
                  _railStack(vendorId, vd, sky, consults),
                ],
              ];
              // phones fold the rail into the column above, so only desktop
              // gets a separate rail - otherwise June and the sky show twice
              railKids = wide
                  ? <Widget>[_railStack(vendorId, vd, sky, consults)]
                  : <Widget>[];""")

rep("""  // ---------------- v177: FOLDABLE CARDS ----------------""", r"""  // ---------------- v194: WIDGETS UNDER THE SKY ----------------
  static const List<List<String>> _kRailAll = <List<String>>[
    <String>['weather', 'Weather', 'The sky for your next wedding, or today'],
    <String>['consults', 'Consults', 'Calls and tours coming up'],
    <String>['analytics', 'Your page', 'Views, where visitors come from, inquiries and bookings'],
    <String>['calendar', 'Availability', 'Booked, blocked and asked-about dates'],
    <String>['funnel', 'Pipeline at a glance', 'How many couples sit at each stage'],
    <String>['goal', 'Season goal', 'Bookings and revenue against your goal'],
    <String>['hotdates', 'Most-asked dates', 'The dates couples ask you about most'],
    <String>['money', 'Money this month', 'Paid, outstanding and what is due next'],
    <String>['reviews', 'Reviews', 'Your rating and the latest review'],
    <String>['notes', 'Notes', 'A private notepad'],
  ];
  static const List<String> _kRailDefault = <String>['weather', 'consults', 'analytics', 'calendar', 'funnel', 'goal'];
  List<String> _rail = List<String>.from(_kRailDefault);
  String _railSynced = '';
  DateTime _railMonth = DateTime(DateTime.now().year, DateTime.now().month, 1);
  final TextEditingController _railNoteC = TextEditingController();
  bool _railNoteLoaded = false;
  Timer? _railNoteT;

  bool _railKnown(String id) => _kRailAll.any((List<String> r) => r[0] == id);
  List<String> _railTitle(String id) => _kRailAll.firstWhere((List<String> r) => r[0] == id, orElse: () => <String>[id, id, '']);

  void _syncRail(Map<String, dynamic> d) {
    final Map<String, dynamic> lay = d['layout'] is Map ? Map<String, dynamic>.from(d['layout'] as Map) : <String, dynamic>{};
    if (lay['rail'] is! List) return;
    final List<String> l = (lay['rail'] as List).map((dynamic e) => e.toString()).where(_railKnown).toList();
    final String sig = l.join(',');
    if (sig == _railSynced) return;
    _railSynced = sig;
    _rail = l;
  }

  Future<void> _saveRail() async {
    _railSynced = _rail.join(',');
    if (_vendorIdCache.isEmpty) return;
    try {
      await FirebaseFirestore.instance.collection('vendors').doc(_vendorIdCache).set(<String, dynamic>{
        'layout': <String, dynamic>{'rail': _rail}
      }, SetOptions(merge: true));
    } catch (e) {
      debugPrint('LAZO rail: ' + e.toString());
    }
  }

  Widget _railStack(String vendorId, Map<String, dynamic> vd, Widget sky, Widget consults) {
    final List<String> ids = _rail.where(_railKnown).toList();
    Widget body(String id) {
      switch (id) {
        case 'weather':
          return sky;
        case 'consults':
          return consults;
        case 'money':
          return Padding(padding: const EdgeInsets.only(bottom: 14), child: _moneyMini(vendorId));
        case 'analytics':
          return _railCard('Your page', Icons.insights_rounded, _railAnalytics(vendorId, vd), sub: 'Views update overnight');
        case 'calendar':
          return _railCard('Availability', Icons.calendar_month_rounded, _railCalendar(vendorId, vd));
        case 'funnel':
          return _railCard('Pipeline at a glance', Icons.filter_alt_rounded, _railFunnel(vendorId));
        case 'goal':
          return _railCard('Season goal', Icons.flag_rounded, _railGoal(vendorId));
        case 'hotdates':
          return _railCard('Most-asked dates', Icons.local_fire_department_rounded, _railHotDates(vendorId));
        case 'reviews':
          return _railCard('Reviews', Icons.star_rounded, _railReviews(vendorId, vd));
        case 'notes':
          return _railCard('Notes', Icons.sticky_note_2_rounded, _railNotes(), sub: 'Only you see these');
      }
      return const SizedBox.shrink();
    }

    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
      ReorderableListView(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        buildDefaultDragHandles: false,
        padding: EdgeInsets.zero,
        proxyDecorator: (Widget child, int i, Animation<double> a) => Material(
          color: Colors.transparent,
          elevation: 10,
          shadowColor: const Color(0x55000000),
          borderRadius: BorderRadius.circular(20),
          child: child,
        ),
        onReorder: (int from, int to) {
          setState(() {
            if (to > from) to -= 1;
            final String x = ids.removeAt(from);
            ids.insert(to, x);
            _rail = List<String>.from(ids);
          });
          HapticFeedback.selectionClick();
          _saveRail();
        },
        children: <Widget>[
          for (int i = 0; i < ids.length; i++)
            KeyedSubtree(
              key: ValueKey<String>('rail-${ids[i]}'),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
                Center(
                  child: ReorderableDragStartListener(
                    index: i,
                    child: MouseRegion(
                      cursor: SystemMouseCursors.grab,
                      child: Tooltip(
                        message: 'Drag to move',
                        child: Container(
                          width: 54,
                          height: 14,
                          alignment: Alignment.center,
                          child: Container(width: 30, height: 4, decoration: BoxDecoration(color: _lzLine(goldLine), borderRadius: BorderRadius.circular(3))),
                        ),
                      ),
                    ),
                  ),
                ),
                ReorderableDelayedDragStartListener(index: i, child: body(ids[i])),
              ]),
            ),
        ],
      ),
      Center(
        child: TextButton.icon(
          onPressed: _h(() => _railSheet()),
          icon: Icon(Icons.dashboard_customize_rounded, size: 16, color: _lzFg(plum)),
          label: Text(ids.isEmpty ? 'Add widgets' : 'Customize widgets', style: TextStyle(color: _lzFg(plum), fontWeight: FontWeight.w700, fontSize: 12.5)),
        ),
      ),
    ]);
  }

  Widget _railCard(String title, IconData icon, Widget content, {String? sub}) => Padding(
        padding: const EdgeInsets.only(bottom: 14),
        child: _glass(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
          radius: 20,
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
            Row(children: <Widget>[
              Icon(icon, size: 16, color: gold),
              const SizedBox(width: 8),
              Expanded(child: Text(title, style: TextStyle(color: _lzFg(plum), fontWeight: FontWeight.w800, fontSize: 13.5))),
              if (sub != null) Text(sub, style: TextStyle(color: _lzFg(muted), fontSize: 10.5)),
            ]),
            const SizedBox(height: 12),
            content,
          ]),
        ),
      );

  void _railSheet() {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: _lzBg(ivory),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (BuildContext c) => StatefulBuilder(builder: (BuildContext c2, StateSetter setS) {
        final List<String> on = _rail.where(_railKnown).toList();
        final List<String> off = _kRailAll.map((List<String> r) => r[0]).where((String id) => !on.contains(id)).toList();
        Widget row(String id, bool enabled, {int? index}) {
          final List<String> r = _railTitle(id);
          return ListTile(
            key: ValueKey<String>('sheet-$id'),
            contentPadding: const EdgeInsets.symmetric(horizontal: 4),
            leading: index == null
                ? Icon(Icons.add_circle_outline_rounded, color: _lzFg(muted))
                : ReorderableDragStartListener(index: index, child: Icon(Icons.drag_indicator_rounded, color: _lzFg(muted))),
            title: Text(r[1], style: TextStyle(color: _lzFg(plum), fontWeight: FontWeight.w700, fontSize: 14)),
            subtitle: Text(r[2], style: TextStyle(color: _lzFg(muted), fontSize: 12)),
            trailing: Switch(
              value: enabled,
              activeColor: Colors.white,
              activeTrackColor: vGreen,
              onChanged: (bool v) {
                setS(() {});
                setState(() {
                  if (v) {
                    _rail = <String>[...on, id];
                  } else {
                    _rail = on.where((String x) => x != id).toList();
                  }
                });
                _saveRail();
              },
            ),
          );
        }

        return SafeArea(
          child: ConstrainedBox(
            constraints: BoxConstraints(maxHeight: MediaQuery.of(c2).size.height * .82),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(18, 14, 18, 8),
              child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
                Row(children: <Widget>[
                  Expanded(child: Text('Your widgets', style: TextStyle(color: _lzFg(plum), fontSize: 18, fontWeight: FontWeight.w800))),
                  TextButton(onPressed: () => Navigator.of(c2).pop(), child: Text('Done', style: TextStyle(color: _lzFg(plum), fontWeight: FontWeight.w800))),
                ]),
                Text('Switch widgets on or off, and drag to put them in the order you like.', style: TextStyle(color: _lzFg(muted), fontSize: 12.5)),
                const SizedBox(height: 8),
                Flexible(
                  child: ListView(shrinkWrap: true, children: <Widget>[
                    ReorderableListView(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      buildDefaultDragHandles: false,
                      onReorder: (int from, int to) {
                        if (to > from) to -= 1;
                        final String x = on.removeAt(from);
                        on.insert(to, x);
                        setS(() {});
                        setState(() => _rail = List<String>.from(on));
                        _saveRail();
                      },
                      children: <Widget>[for (int i = 0; i < on.length; i++) row(on[i], true, index: i)],
                    ),
                    if (off.isNotEmpty) ...<Widget>[
                      Padding(padding: const EdgeInsets.only(top: 12, bottom: 4), child: Text('MORE WIDGETS', style: TextStyle(color: _lzFg(muted), fontSize: 10.5, letterSpacing: 1.4, fontWeight: FontWeight.w800))),
                      for (final String id in off) row(id, false),
                    ],
                  ]),
                ),
              ]),
            ),
          ),
        );
      }),
    );
  }

  // ---- shared reads for the widgets
  List<Map<String, dynamic>> _railLeads(String vendorId) {
    final QuerySnapshot<Map<String, dynamic>>? q = _liveQ['leads:$vendorId']?.latest ?? _leadsLatest(vendorId);
    return (q?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[])
        .map((QueryDocumentSnapshot<Map<String, dynamic>> d) => <String, dynamic>{...d.data(), '_id': d.id})
        .where((Map<String, dynamic> m) => m['demo'] != true)
        .toList();
  }

  DateTime? _railWedding(Map<String, dynamic> m) {
    final dynamic si = m['structuredIntent'];
    if (si is! Map) return null;
    final dynamic w = si['weddingDate'];
    if (w is Timestamp) return w.toDate();
    return DateTime.tryParse((w ?? '').toString());
  }

  String _railStage(Map<String, dynamic> m) {
    final String st = (m['status'] ?? '').toString();
    if (st == 'booked' || st == 'delivered') return 'booked';
    if (st == 'lost') return 'lost';
    if (st.isEmpty || st == 'new') return 'new';
    return 'talking';
  }

  Widget _railStat(String big, String label, {String delta = ''}) => Expanded(
        child: Container(
          padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
          decoration: BoxDecoration(color: _lzBg(plum.withOpacity(.04)), borderRadius: BorderRadius.circular(14), border: Border.all(color: _lzLine(goldLine))),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
            Row(crossAxisAlignment: CrossAxisAlignment.end, children: <Widget>[
              Flexible(child: Text(big, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: _lzFg(plum), fontSize: 22, fontWeight: FontWeight.w800, height: 1))),
              if (delta.isNotEmpty) ...<Widget>[
                const SizedBox(width: 6),
                Text(delta, style: TextStyle(color: delta.startsWith('+') ? vGreen : (delta.startsWith('-') ? const Color(0xFFB4534B) : _lzFg(muted)), fontSize: 11, fontWeight: FontWeight.w800)),
              ],
            ]),
            const SizedBox(height: 4),
            Text(label, maxLines: 2, style: TextStyle(color: _lzFg(muted), fontSize: 11, height: 1.25)),
          ]),
        ),
      );

  String _railDelta(num now, num before) {
    if (before <= 0) return now > 0 ? 'new' : '';
    final int pct = (((now - before) / before) * 100).round();
    if (pct == 0) return '=';
    return (pct > 0 ? '+' : '') + '$pct%';
  }

  // ---- Your page
  Widget _railAnalytics(String vendorId, Map<String, dynamic> vd) {
    return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
      stream: _leadsStream(vendorId),
      initialData: _leadsLatest(vendorId),
      builder: (BuildContext c, AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> s) {
        final Map<String, dynamic> views = vd['views'] is Map ? Map<String, dynamic>.from(vd['views'] as Map) : <String, dynamic>{};
        final num v7 = views['d7'] is num ? views['d7'] as num : 0;
        final num vPrev = views['d7Prev'] is num ? views['d7Prev'] as num : 0;
        final Map<String, dynamic> src = views['src'] is Map ? Map<String, dynamic>.from(views['src'] as Map) : <String, dynamic>{};
        final List<Map<String, dynamic>> leads = _railLeads(vendorId);
        final DateTime now = DateTime.now();
        int in30 = 0, prev30 = 0, bookedYear = 0, booked = 0;
        for (final Map<String, dynamic> m in leads) {
          final dynamic ca = m['createdAt'];
          if (ca is Timestamp) {
            final int age = now.difference(ca.toDate()).inDays;
            if (age < 30) in30++;
            else if (age < 60) prev30++;
          }
          if (_railStage(m) == 'booked') {
            booked++;
            final dynamic ba = m['bookedAt'] ?? m['createdAt'];
            if (ba is Timestamp && ba.toDate().year == now.year) bookedYear++;
          }
        }
        final int rate = leads.isEmpty ? 0 : ((booked / leads.length) * 100).round();
        final Map<String, dynamic> rank = vd['rank'] is Map ? Map<String, dynamic>.from(vd['rank'] as Map) : <String, dynamic>{};
        const Map<String, String> srcName = <String, String>{'search': 'Search', 'social': 'Social', 'lazo': 'Lazo', 'direct': 'Direct', 'other': 'Other'};
        const Map<String, Color> srcColor = <String, Color>{'search': Color(0xFF52284F), 'social': Color(0xFFC7869C), 'lazo': Color(0xFFD9B77C), 'direct': Color(0xFF8DA399), 'other': Color(0xFFB9ADC0)};
        final List<MapEntry<String, num>> parts = src.entries
            .map((MapEntry<String, dynamic> e) => MapEntry<String, num>(srcName.containsKey(e.key) ? e.key : 'other', e.value is num ? e.value as num : 0))
            .where((MapEntry<String, num> e) => e.value > 0)
            .toList();
        final Map<String, num> merged = <String, num>{};
        for (final MapEntry<String, num> e in parts) {
          merged[e.key] = (merged[e.key] ?? 0) + e.value;
        }
        final List<MapEntry<String, num>> segs = merged.entries.toList()..sort((MapEntry<String, num> a, MapEntry<String, num> b) => b.value.compareTo(a.value));
        final num total = segs.fold<num>(0, (num a, MapEntry<String, num> e) => a + e.value);
        return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
          Row(children: <Widget>[
            _railStat('${v7.round()}', 'Profile views, 7 days', delta: _railDelta(v7, vPrev)),
            const SizedBox(width: 8),
            _railStat('$in30', 'Couples who wrote, 30 days', delta: _railDelta(in30, prev30)),
          ]),
          const SizedBox(height: 8),
          Row(children: <Widget>[
            _railStat('$bookedYear', 'Booked in ${now.year}'),
            const SizedBox(width: 8),
            _railStat(leads.isEmpty ? '-' : '$rate%', 'Inquiries that booked'),
          ]),
          if (total > 0) ...<Widget>[
            const SizedBox(height: 12),
            Text('WHERE VISITORS CAME FROM', style: TextStyle(color: _lzFg(muted), fontSize: 9.5, letterSpacing: 1.3, fontWeight: FontWeight.w800)),
            const SizedBox(height: 6),
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: SizedBox(
                height: 10,
                child: Row(children: <Widget>[
                  for (final MapEntry<String, num> e in segs) Expanded(flex: math.max(1, (e.value / total * 1000).round()), child: Container(color: srcColor[e.key])),
                ]),
              ),
            ),
            const SizedBox(height: 6),
            Wrap(spacing: 10, runSpacing: 4, children: <Widget>[
              for (final MapEntry<String, num> e in segs)
                Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
                  Container(width: 8, height: 8, decoration: BoxDecoration(color: srcColor[e.key], shape: BoxShape.circle)),
                  const SizedBox(width: 4),
                  Text('${srcName[e.key]} ${e.value.round()}', style: TextStyle(color: _lzFg(ink), fontSize: 11.5)),
                ]),
            ]),
          ],
          if (rank['pos'] is num && rank['of'] is num) ...<Widget>[
            const SizedBox(height: 12),
            Row(children: <Widget>[
              Icon(Icons.emoji_events_rounded, size: 15, color: gold),
              const SizedBox(width: 6),
              Expanded(child: Text('#${(rank['pos'] as num).round()} of ${(rank['of'] as num).round()} ${(rank['label'] ?? '').toString()}', style: TextStyle(color: _lzFg(ink), fontSize: 12.5, fontWeight: FontWeight.w600))),
            ]),
          ],
        ]);
      },
    );
  }

  // ---- Availability
  Widget _railCalendar(String vendorId, Map<String, dynamic> vd) {
    return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
      stream: _leadsStream(vendorId),
      initialData: _leadsLatest(vendorId),
      builder: (BuildContext c, AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> s) {
        final Map<String, List<String>> booked = <String, List<String>>{};
        final Map<String, List<String>> asked = <String, List<String>>{};
        for (final Map<String, dynamic> m in _railLeads(vendorId)) {
          final DateTime? w = _railWedding(m);
          if (w == null) continue;
          final String k = _ymd(w);
          final String who = (m['coupleName'] ?? 'A couple').toString();
          final String stg = _railStage(m);
          if (stg == 'booked') {
            booked.putIfAbsent(k, () => <String>[]).add(who);
          } else if (stg != 'lost') {
            asked.putIfAbsent(k, () => <String>[]).add(who);
          }
        }
        final Set<String> blocked = ((vd['unavailableDates'] as List?) ?? const <dynamic>[]).map((dynamic e) => e.toString()).toSet();
        final DateTime m0 = _railMonth;
        final int days = DateTime(m0.year, m0.month + 1, 0).day;
        final int lead = (DateTime(m0.year, m0.month, 1).weekday + 6) % 7; // Monday first
        const List<String> mo = <String>['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
        final String today = _ymd(DateTime.now());
        Widget cell(int d) {
          final String k = _ymd(DateTime(m0.year, m0.month, d));
          final bool b = booked.containsKey(k), x = blocked.contains(k), a = asked.containsKey(k);
          return GestureDetector(
            onTap: () {
              final List<String> l = <String>[
                if (b) 'Booked: ${booked[k]!.join(', ')}',
                if (x) 'Blocked',
                if (a) 'Asked: ${asked[k]!.join(', ')}',
              ];
              if (l.isNotEmpty) _toast('${mo[m0.month - 1]} $d - ${l.join(' / ')}');
            },
            child: Container(
              margin: const EdgeInsets.all(1.5),
              decoration: BoxDecoration(
                color: b ? gold : (x ? _lzBg(muted.withOpacity(.16)) : Colors.transparent),
                borderRadius: BorderRadius.circular(8),
                border: k == today ? Border.all(color: _lzLine(plum), width: 1.4) : null,
              ),
              child: Stack(alignment: Alignment.center, children: <Widget>[
                Text('$d', style: TextStyle(fontSize: 11.5, fontWeight: b ? FontWeight.w800 : FontWeight.w500, color: b ? plumDeep : _lzFg(x ? muted : ink), decoration: x && !b ? TextDecoration.lineThrough : null)),
                if (a && !b) Positioned(bottom: 3, child: Container(width: 4, height: 4, decoration: BoxDecoration(color: _lzFg(plum), shape: BoxShape.circle))),
              ]),
            ),
          );
        }

        return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
          Row(children: <Widget>[
            IconButton(visualDensity: VisualDensity.compact, icon: Icon(Icons.chevron_left_rounded, color: _lzFg(plum)), onPressed: () => setState(() => _railMonth = DateTime(m0.year, m0.month - 1, 1))),
            Expanded(child: Text('${mo[m0.month - 1]} ${m0.year}', textAlign: TextAlign.center, style: TextStyle(color: _lzFg(plum), fontWeight: FontWeight.w800, fontSize: 13))),
            IconButton(visualDensity: VisualDensity.compact, icon: Icon(Icons.chevron_right_rounded, color: _lzFg(plum)), onPressed: () => setState(() => _railMonth = DateTime(m0.year, m0.month + 1, 1))),
          ]),
          Row(children: <Widget>[
            for (final String d in const <String>['M', 'T', 'W', 'T', 'F', 'S', 'S'])
              Expanded(child: Text(d, textAlign: TextAlign.center, style: TextStyle(color: _lzFg(muted), fontSize: 10, fontWeight: FontWeight.w700))),
          ]),
          const SizedBox(height: 4),
          GridView.count(
            crossAxisCount: 7,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            childAspectRatio: 1.15,
            children: <Widget>[
              for (int i = 0; i < lead; i++) const SizedBox.shrink(),
              for (int d = 1; d <= days; d++) cell(d),
            ],
          ),
          const SizedBox(height: 8),
          Wrap(spacing: 12, runSpacing: 4, children: <Widget>[
            _railKey(gold, 'Booked'),
            _railKey(muted.withOpacity(.35), 'Blocked'),
            _railKey(plum, 'Couples asked', dot: true),
          ]),
        ]);
      },
    );
  }

  Widget _railKey(Color c, String t, {bool dot = false}) => Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
        Container(width: dot ? 6 : 10, height: dot ? 6 : 10, decoration: BoxDecoration(color: _lzFg(c), borderRadius: BorderRadius.circular(dot ? 3 : 3))),
        const SizedBox(width: 5),
        Text(t, style: TextStyle(color: _lzFg(muted), fontSize: 11)),
      ]);

  // ---- Pipeline at a glance
  Widget _railFunnel(String vendorId) {
    return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
      stream: _leadsStream(vendorId),
      initialData: _leadsLatest(vendorId),
      builder: (BuildContext c, AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> s) {
        final Map<String, int> n = <String, int>{'new': 0, 'talking': 0, 'booked': 0, 'lost': 0};
        for (final Map<String, dynamic> m in _railLeads(vendorId)) {
          n[_railStage(m)] = (n[_railStage(m)] ?? 0) + 1;
        }
        final int most = math.max(1, n.values.fold<int>(0, math.max));
        Widget bar(String k, String label, Color col) => Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(children: <Widget>[
                SizedBox(width: 62, child: Text(label, style: TextStyle(color: _lzFg(ink), fontSize: 12, fontWeight: FontWeight.w600))),
                Expanded(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(6),
                    child: LinearProgressIndicator(value: (n[k] ?? 0) / most, minHeight: 10, backgroundColor: _lzBg(plum.withOpacity(.06)), valueColor: AlwaysStoppedAnimation<Color>(col)),
                  ),
                ),
                SizedBox(width: 34, child: Text('${n[k]}', textAlign: TextAlign.right, style: TextStyle(color: _lzFg(plum), fontSize: 13, fontWeight: FontWeight.w800))),
              ]),
            );
        return Column(children: <Widget>[
          bar('new', 'New', const Color(0xFFC7869C)),
          bar('talking', 'Talking', const Color(0xFF8DA399)),
          bar('booked', 'Booked', gold),
          bar('lost', 'Lost', const Color(0xFFB9ADC0)),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
              onPressed: _h(() => setState(() => _dashMode = 'pipeline')),
              child: Text('Open Pipeline', style: TextStyle(color: _lzFg(plum), fontSize: 12, fontWeight: FontWeight.w800)),
            ),
          ),
        ]);
      },
    );
  }

  // ---- Season goal (users/{uid}.vendorGoals: private)
  Widget _railGoal(String vendorId) {
    return StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
      stream: _userDocStream(),
      initialData: _liveD['user:$_uid']?.latest,
      builder: (BuildContext c, AsyncSnapshot<DocumentSnapshot<Map<String, dynamic>>> us) {
        final Map<String, dynamic> u = us.data?.data() ?? <String, dynamic>{};
        final int year = DateTime.now().year;
        final Map<String, dynamic> g = (u['vendorGoals'] is Map && (u['vendorGoals'] as Map)['$year'] is Map)
            ? Map<String, dynamic>.from((u['vendorGoals'] as Map)['$year'] as Map)
            : <String, dynamic>{};
        final num gB = g['bookings'] is num ? g['bookings'] as num : 0;
        final num gR = g['revenue'] is num ? g['revenue'] as num : 0;
        return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
          stream: _invoicesAllStream(vendorId),
          initialData: _liveQ['invoices:$vendorId']?.latest,
          builder: (BuildContext c2, AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> inv) {
            int bookedYear = 0;
            for (final Map<String, dynamic> m in _railLeads(vendorId)) {
              if (_railStage(m) != 'booked') continue;
              final dynamic ba = m['bookedAt'] ?? m['createdAt'];
              if (ba is Timestamp && ba.toDate().year == year) bookedYear++;
            }
            num paid = 0;
            for (final QueryDocumentSnapshot<Map<String, dynamic>> d in inv.data?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[]) {
              final Map<String, dynamic> m = d.data();
              if ((m['status'] ?? '') != 'paid' || m['demo'] == true) continue;
              final dynamic pa = m['paidAt'];
              if (pa is Timestamp && pa.toDate().year == year && m['total'] is num) paid += m['total'] as num;
            }
            Widget line(String label, String have, String want, double v) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
                    Row(children: <Widget>[
                      Expanded(child: Text(label, style: TextStyle(color: _lzFg(ink), fontSize: 12.5, fontWeight: FontWeight.w600))),
                      Text(want.isEmpty ? have : '$have of $want', style: TextStyle(color: _lzFg(plum), fontSize: 12.5, fontWeight: FontWeight.w800)),
                    ]),
                    const SizedBox(height: 5),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(6),
                      child: LinearProgressIndicator(value: v.clamp(0.0, 1.0), minHeight: 9, backgroundColor: _lzBg(plum.withOpacity(.06)), valueColor: AlwaysStoppedAnimation<Color>(v >= 1 ? vGreen : gold)),
                    ),
                  ]),
                );
            return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
              line('Weddings booked in $year', '$bookedYear', gB > 0 ? '${gB.round()}' : '', gB > 0 ? bookedYear / gB : 0),
              line('Paid to you in $year', _fmtMoney(paid), gR > 0 ? _fmtMoney(gR) : '', gR > 0 ? (paid / gR).toDouble() : 0),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  onPressed: _h(() => _railGoalDialog(year, gB, gR)),
                  child: Text(gB > 0 || gR > 0 ? 'Change goal' : 'Set a goal', style: TextStyle(color: _lzFg(plum), fontSize: 12, fontWeight: FontWeight.w800)),
                ),
              ),
            ]);
          },
        );
      },
    );
  }

  Future<void> _railGoalDialog(int year, num gB, num gR) async {
    final TextEditingController b = TextEditingController(text: gB > 0 ? '${gB.round()}' : '');
    final TextEditingController r = TextEditingController(text: gR > 0 ? '${gR.round()}' : '');
    final bool? ok = await showDialog<bool>(
      context: context,
      builder: (BuildContext c) => AlertDialog(
        backgroundColor: _lzBg(ivory),
        title: Text('Your $year goal', style: TextStyle(color: _lzFg(plum))),
        content: SizedBox(
          width: 360,
          child: Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
            TextField(controller: b, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Weddings to book', hintText: '30')),
            const SizedBox(height: 10),
            TextField(controller: r, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Revenue goal (\$)', hintText: '120000')),
          ]),
        ),
        actions: <Widget>[
          TextButton(onPressed: () => Navigator.of(c).pop(false), child: const Text('Cancel')),
          FilledButton(style: FilledButton.styleFrom(backgroundColor: plum), onPressed: () => Navigator.of(c).pop(true), child: const Text('Save')),
        ],
      ),
    );
    if (ok != true || _uid == null) return;
    final num nb = num.tryParse(b.text.replaceAll(RegExp(r'[^0-9.]'), '')) ?? 0;
    final num nr = num.tryParse(r.text.replaceAll(RegExp(r'[^0-9.]'), '')) ?? 0;
    try {
      await FirebaseFirestore.instance.collection('users').doc(_uid).set(<String, dynamic>{
        'vendorGoals': <String, dynamic>{'$year': <String, dynamic>{'bookings': nb, 'revenue': nr}}
      }, SetOptions(merge: true));
      _toast('Goal saved.');
    } catch (e) {
      _toast('Could not save the goal: ' + _errText(e));
    }
  }

  // ---- Most-asked dates
  Widget _railHotDates(String vendorId) {
    return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
      stream: _leadsStream(vendorId),
      initialData: _leadsLatest(vendorId),
      builder: (BuildContext c, AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> s) {
        final DateTime today = DateTime.now();
        final Map<String, int> asked = <String, int>{};
        final Set<String> bookedOn = <String>{};
        for (final Map<String, dynamic> m in _railLeads(vendorId)) {
          final DateTime? w = _railWedding(m);
          if (w == null || w.isBefore(DateTime(today.year, today.month, today.day))) continue;
          final String k = _ymd(w);
          if (_railStage(m) == 'booked') bookedOn.add(k);
          if (_railStage(m) != 'lost') asked[k] = (asked[k] ?? 0) + 1;
        }
        final List<MapEntry<String, int>> top = asked.entries.toList()
          ..sort((MapEntry<String, int> a, MapEntry<String, int> b) => b.value != a.value ? b.value.compareTo(a.value) : a.key.compareTo(b.key));
        if (top.isEmpty) {
          return Text('When couples ask about dates, the busiest ones show here, so you know which dates to price higher.', style: TextStyle(color: _lzFg(muted), fontSize: 12.5, height: 1.4));
        }
        const List<String> wd = <String>['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
        const List<String> mo = <String>['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        return Column(children: <Widget>[
          for (final MapEntry<String, int> e in top.take(5))
            Builder(builder: (BuildContext _) {
              final DateTime d = DateTime.parse(e.key);
              return Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(children: <Widget>[
                  Expanded(child: Text('${wd[d.weekday - 1]}, ${mo[d.month - 1]} ${d.day}${d.year != today.year ? ' ${d.year}' : ''}', style: TextStyle(color: _lzFg(ink), fontSize: 13, fontWeight: FontWeight.w600))),
                  Text('${e.value} couple${e.value == 1 ? '' : 's'}', style: TextStyle(color: _lzFg(muted), fontSize: 12)),
                  if (bookedOn.contains(e.key)) ...<Widget>[
                    const SizedBox(width: 8),
                    Container(padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2), decoration: BoxDecoration(color: gold, borderRadius: BorderRadius.circular(8)), child: const Text('BOOKED', style: TextStyle(color: plumDeep, fontSize: 9.5, fontWeight: FontWeight.w800))),
                  ],
                ]),
              );
            }),
        ]);
      },
    );
  }

  // ---- Reviews
  Widget _railReviews(String vendorId, Map<String, dynamic> vd) {
    return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
      stream: _liveQuery('railReviews:$vendorId', () => FirebaseFirestore.instance.collection('reviews').where('vendorId', isEqualTo: vendorId)),
      builder: (BuildContext c, AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> s) {
        final List<Map<String, dynamic>> rs = (s.data?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[]).map((QueryDocumentSnapshot<Map<String, dynamic>> d) => d.data()).toList();
        if (rs.isEmpty) {
          return Text('No reviews yet. They come only from couples who booked you through Lazo. Ask your next couple after the wedding.', style: TextStyle(color: _lzFg(muted), fontSize: 12.5, height: 1.4));
        }
        rs.sort((Map<String, dynamic> a, Map<String, dynamic> b) {
          final dynamic x = a['createdAt'], y = b['createdAt'];
          return (y is Timestamp && x is Timestamp) ? y.compareTo(x) : 0;
        });
        final List<num> stars = rs.map((Map<String, dynamic> r) => r['rating']).whereType<num>().toList();
        final double avg = stars.isEmpty ? 0 : stars.fold<num>(0, (num a, num b) => a + b) / stars.length;
        final Map<String, dynamic> last = rs.first;
        final String txt = (last['text'] ?? '').toString().trim();
        return Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
          Row(children: <Widget>[
            Text(avg.toStringAsFixed(1), style: TextStyle(color: _lzFg(plum), fontSize: 26, fontWeight: FontWeight.w800)),
            const SizedBox(width: 8),
            for (int i = 1; i <= 5; i++) Icon(i <= avg.round() ? Icons.star_rounded : Icons.star_outline_rounded, size: 17, color: gold),
            const Spacer(),
            Text('${rs.length} review${rs.length == 1 ? '' : 's'}', style: TextStyle(color: _lzFg(muted), fontSize: 12)),
          ]),
          if (txt.isNotEmpty) ...<Widget>[
            const SizedBox(height: 8),
            Text('"${txt.length > 180 ? txt.substring(0, 177).trimRight() + '...' : txt}"', style: TextStyle(color: _lzFg(ink), fontSize: 12.5, height: 1.4, fontStyle: FontStyle.italic)),
            if ((last['coupleName'] ?? '').toString().isNotEmpty)
              Padding(padding: const EdgeInsets.only(top: 4), child: Text('- ${last['coupleName']}', style: TextStyle(color: _lzFg(muted), fontSize: 11.5))),
          ],
        ]);
      },
    );
  }

  // ---- Notes (private: users/{uid}.vendorNotes)
  Widget _railNotes() {
    if (!_railNoteLoaded) {
      _railNoteLoaded = true;
      final Map<String, dynamic> u = _liveD['user:$_uid']?.latest?.data() ?? <String, dynamic>{};
      _railNoteC.text = (u['vendorNotes'] ?? '').toString();
    }
    return TextField(
      controller: _railNoteC,
      minLines: 4,
      maxLines: 10,
      style: TextStyle(color: _lzFg(ink), fontSize: 13.5, height: 1.4),
      decoration: InputDecoration(
        hintText: 'Shot lists, follow-ups, gear to pack...',
        hintStyle: TextStyle(color: _lzFg(muted), fontSize: 13),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: _lzLine(goldLine))),
        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: _lzLine(goldLine))),
        isDense: true,
      ),
      onChanged: (String v) {
        _railNoteT?.cancel();
        _railNoteT = Timer(const Duration(milliseconds: 900), () async {
          if (_uid == null) return;
          try {
            await FirebaseFirestore.instance.collection('users').doc(_uid).set(<String, dynamic>{'vendorNotes': v}, SetOptions(merge: true));
          } catch (_) {}
        });
      },
    );
  }

  // ---------------- v177: FOLDABLE CARDS ----------------""")

rep("""    _jwNoticeT?.cancel();
    _jwSeenT?.cancel();""", """    _jwNoticeT?.cancel();
    _jwSeenT?.cancel();
    _railNoteT?.cancel();
    _railNoteC.dispose();""")

OUT.write_text(s, encoding="utf-8", newline="\n")
print(f"wrote {OUT.name} ({len(s):,} chars)")
