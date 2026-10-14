r"""patch_vendor_v196.py - Vendor v195 -> v196 (JC-LAZO-VDASH-1014-196)
  - JUNE'S FEED: a bell in the header with the unread count; the sheet lists
    June's last 40 notices (users/{uid}/juneFeed, written by functions-dashboard
    027 together with the push), tap one to open the thread; opening marks read.
  - Your page: taps this week (calls, website, email, check your date, saves,
    Instagram) and a 14-day views chart (views.clicks / views.days, nightly).
  - No numbers twice: the hero drops Average reply, Next wedding and Profile
    views when the matching widget (Reply speed, Weddings coming up, Your page)
    is on.
  - One voice: the inbox chime stays quiet while June announces; the booking
    banner gives way to June's card (the confetti stays).
  - Phones: a strip of widget chips under the tabs on Today - each one-line
    summary opens that widget; "Widgets" opens them all.
  - Big screens: the widget column widens to 420 above 1500 px.
  - Widget titles in the serif; the late/overdue red reads in dark mode.

    python app-patches\patch_vendor_v196.py
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
s = (HERE / "Vendor_master_v195.txt").read_text(encoding="utf-8")
OUT = HERE / "Vendor_master_v196.txt"


def rep(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"anchor found {n}x (want {count}): {old[:90]!r}")
    s = s.replace(old, new)


rep("// Build ID: JC-LAZO-VDASH-1014-195 (v195:", "// Build ID: JC-LAZO-VDASH-1014-196 (v196: June's feed bell, taps + 14-day views on Your page, no duplicate hero numbers, chime quiet while June speaks, phone widget strip, wider rail on big screens, serif widget titles, dark-mode red. base v195) (v195:")

# ---- the rail body becomes a method so the phone strip can open one widget
a = s.index("    Widget body(String id) {\n      switch (id) {")
b = s.index("      return const SizedBox.shrink();\n    }\n", a) + len("      return const SizedBox.shrink();\n    }\n")
switch = s[a:b]
s = s[:a] + "    Widget body(String id) => _railBody(id, vendorId, vd, sky, consults);\n" + s[b:]
method = switch.replace("    Widget body(String id) {", "  Widget _railBody(String id, String vendorId, Map<String, dynamic> vd, Widget sky, Widget consults) {", 1)
method = "\n".join(l[2:] if l.startswith("  ") and not l.startswith("  Widget _railBody") else l for l in method.split("\n"))
rep("""  Widget _railCard(String title, IconData icon, Widget content, {String? sub}) => Padding(""", method + """
  Widget _railCard(String title, IconData icon, Widget content, {String? sub}) => Padding(""")

# ---- serif titles
rep("""              Expanded(child: Text(title, style: TextStyle(color: _lzFg(plum), fontWeight: FontWeight.w800, fontSize: 13.5))),
              if (sub != null) Text(sub, style: TextStyle(color: _lzFg(muted), fontSize: 10.5)),
            ]),
            const SizedBox(height: 12),""", """              Expanded(child: Text(title, style: GoogleFonts.cormorantGaramond(color: _lzFg(plum), fontWeight: FontWeight.w700, fontSize: 18.5, height: 1.1))),
              if (sub != null) Text(sub, style: TextStyle(color: _lzFg(muted), fontSize: 10.5)),
            ]),
            const SizedBox(height: 12),""")

# ---- the red that reads in dark mode, inside the widget code only
w0 = s.index("// ---------------- v194: WIDGETS UNDER THE SKY ----------------")
w1 = s.index("// ---------------- v177: FOLDABLE CARDS ----------------")
s = s[:w0] + s[w0:w1].replace("const Color(0xFFB4534B)", "_railRed") + s[w1:]
rep("""  bool _railKnown(String id) =>""", """  Color get _railRed => _lzDark ? const Color(0xFFEE9A90) : const Color(0xFFB4534B);
  Widget? _railSkyW, _railConsW; // v196: the latest weather / consults cards, for the phone strip

  bool _railKnown(String id) =>""")

# ---- Your page: taps + 14 days
rep("""          if (rank['pos'] is num && rank['of'] is num) ...<Widget>[""", """          // v196: taps this week and the last 14 days of views
          if (views['clicks'] is Map && (views['clicks'] as Map).isNotEmpty) ...<Widget>[
            const SizedBox(height: 12),
            Text('TAPS THIS WEEK', style: TextStyle(color: _lzFg(muted), fontSize: 9.5, letterSpacing: 1.3, fontWeight: FontWeight.w800)),
            const SizedBox(height: 6),
            Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
              for (final List<String> t in const <List<String>>[<String>['date', 'Check your date'], <String>['call', 'Calls'], <String>['web', 'Website'], <String>['email', 'Email'], <String>['ig', 'Instagram'], <String>['save', 'Saves']])
                if ((views['clicks'] as Map)[t[0]] is num && ((views['clicks'] as Map)[t[0]] as num) > 0)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                    decoration: BoxDecoration(color: _lzBg(plum.withOpacity(.05)), borderRadius: BorderRadius.circular(99), border: Border.all(color: _lzLine(goldLine))),
                    child: Text('${t[1]} ${((views['clicks'] as Map)[t[0]] as num).round()}', style: TextStyle(color: _lzFg(plum), fontSize: 11.5, fontWeight: FontWeight.w700)),
                  ),
            ]),
          ],
          if (views['days'] is List && (views['days'] as List).length >= 7) ...<Widget>[
            const SizedBox(height: 12),
            Text('VIEWS, LAST 14 DAYS', style: TextStyle(color: _lzFg(muted), fontSize: 9.5, letterSpacing: 1.3, fontWeight: FontWeight.w800)),
            const SizedBox(height: 6),
            SizedBox(
              height: 46,
              child: Builder(builder: (BuildContext _) {
                final List<num> ds = (views['days'] as List).map((dynamic x) => x is num ? x : 0).toList();
                final num top = ds.fold<num>(1, (num a, num b) => b > a ? b : a);
                return Row(crossAxisAlignment: CrossAxisAlignment.end, children: <Widget>[
                  for (int i = 0; i < ds.length; i++)
                    Expanded(
                      child: Tooltip(
                        message: '${ds[i].round()} views',
                        child: Container(
                          margin: const EdgeInsets.symmetric(horizontal: 1.5),
                          height: 4 + 42 * (ds[i] / top),
                          decoration: BoxDecoration(color: i == ds.length - 1 ? gold : _lzFg(plum).withOpacity(.55), borderRadius: BorderRadius.circular(3)),
                        ),
                      ),
                    ),
                ]);
              }),
            ),
          ],
          if (rank['pos'] is num && rank['of'] is num) ...<Widget>[""")

# ---- no numbers twice in the hero
rep("""          _heroTile(
              'Average reply',""", """          if (!_rail.contains('speed'))
          _heroTile(
              'Average reply',""")
rep("""          _heroTile(
              'Next wedding',""", """          if (!_rail.contains('coming'))
          _heroTile(
              'Next wedding',""")
rep("""          if (hasViews)
            _heroTile(
                'Profile views, 7 days',""", """          if (hasViews && !_rail.contains('analytics'))
            _heroTile(
                'Profile views, 7 days',""")

# ---- one voice
rep("""  void _playChime() {
    if (_chimeMuted) return;""", """  void _playChime() {
    if (_chimeMuted) return;
    if (_jwVoice && _jwFor.isNotEmpty && _tourIdx < 0) return; // v196: June says it instead""")
rep("""            _bookingBannerOverlay(),
""", """            if (_jwFor.isEmpty) _bookingBannerOverlay(), // v196: June's card announces bookings
""")

# ---- the weather / consults cards for the strip
rep("""              final Widget consults = _fold(
                  'consults',
                  'Consults',
                  _foldSummary('consults', vendorId, vd),
                  _upcomingConsultsCard(vendorId),
                  gap: 14);""", """              final Widget consults = _fold(
                  'consults',
                  'Consults',
                  _foldSummary('consults', vendorId, vd),
                  _upcomingConsultsCard(vendorId),
                  gap: 14);
              _railSkyW = sky;
              _railConsW = consults;""")

# ---- phones: the strip under the tabs on Today
rep("""              children: <Widget>[
                hero,
                const SizedBox(height: 14),
                _dashModeToggle(),
                const SizedBox(height: 16),
                ...mainKids,""", """              children: <Widget>[
                hero,
                const SizedBox(height: 14),
                _dashModeToggle(),
                if (today) ...<Widget>[
                  const SizedBox(height: 12),
                  _railStrip(vendorId, vd),
                ],
                const SizedBox(height: 16),
                ...mainKids,""")

# ---- big screens: a wider rail
rep("""                          width: 330,""", """                          width: MediaQuery.of(context).size.width >= 1500 ? 420 : 330,""")

# ---- the bell in the header
rep("""                              if (_isAdminUser)
                                IconButton(
                                  tooltip:
                                      _adminMode ? 'Vendor view' : 'Admin desk',""", """                              if (_uid != null) _feedBell(),
                              if (_isAdminUser)
                                IconButton(
                                  tooltip:
                                      _adminMode ? 'Vendor view' : 'Admin desk',""")

# ---- the code
rep("""  Widget _railCard(String title, IconData icon, Widget content, {String? sub}) => Padding(""", r"""  // v196: one line per widget for the phone strip
  String _railSummary(String id, String vendorId, Map<String, dynamic> vd) {
    final List<Map<String, dynamic>> leads = _railLeads(vendorId);
    final DateTime now = DateTime.now();
    switch (id) {
      case 'weather':
      case 'consults':
        return _foldSummary(id, vendorId, vd) ?? _railTitle(id)[1];
      case 'analytics':
        final Map<String, dynamic> v = vd['views'] is Map ? Map<String, dynamic>.from(vd['views'] as Map) : <String, dynamic>{};
        return v['d7'] is num ? '${(v['d7'] as num).round()} views this week' : 'Your page';
      case 'quiet':
        final int q = leads.where((Map<String, dynamic> m) => _railStage(m) != 'booked' && _railStage(m) != 'lost' && (m['lastMessageRole'] ?? '') == 'vendor' && m['lastMessageAt'] is Timestamp && now.difference((m['lastMessageAt'] as Timestamp).toDate()).inDays >= 3).length;
        return q == 0 ? 'Nobody quiet' : '$q quiet lead${q == 1 ? '' : 's'}';
      case 'funnel':
        final int n = leads.where((Map<String, dynamic> m) => _railStage(m) == 'new').length;
        return '$n new';
      case 'coming':
        final int c = leads.where((Map<String, dynamic> m) {
          final DateTime? d = _railWedding(m);
          return _railStage(m) == 'booked' && d != null && !d.isBefore(DateTime(now.year, now.month, now.day)) && d.difference(now).inDays <= 30;
        }).length;
        return c == 0 ? 'No weddings this month' : '$c wedding${c == 1 ? '' : 's'} in 30 days';
      case 'deposits':
        num t = 0;
        for (final QueryDocumentSnapshot<Map<String, dynamic>> d in _liveQ['invoices:$vendorId']?.latest?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[]) {
          final Map<String, dynamic> m = d.data();
          final dynamic dd = m['dueDate'];
          if ((m['status'] ?? '') == 'paid' || (m['status'] ?? '') == 'void' || dd is! Timestamp || dd.toDate().isAfter(now.add(const Duration(days: 8)))) continue;
          if (m['total'] is num) t += m['total'] as num;
        }
        return t > 0 ? '${_fmtMoney(t)} due this week' : 'Nothing due';
    }
    return _railTitle(id)[1];
  }

  Widget _railStrip(String vendorId, Map<String, dynamic> vd) {
    final List<String> ids = _rail.where(_railKnown).toList();
    void open(String? id) {
      final Widget sky = _railSkyW ?? const SizedBox.shrink();
      final Widget cons = _railConsW ?? const SizedBox.shrink();
      showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: _lzBg(ivory),
        shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
        builder: (BuildContext c) => SafeArea(
          child: ConstrainedBox(
            constraints: BoxConstraints(maxHeight: MediaQuery.of(c).size.height * .88),
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
                Center(child: Container(width: 36, height: 4, decoration: BoxDecoration(color: _lzLine(goldLine), borderRadius: BorderRadius.circular(3)))),
                const SizedBox(height: 12),
                if (id == null) _railStack(vendorId, vd, sky, cons) else _railBody(id, vendorId, vd, sky, cons),
              ]),
            ),
          ),
        ),
      );
    }

    Widget chip(String label, IconData icon, VoidCallback onTap, {bool lead = false}) => Padding(
          padding: const EdgeInsets.only(right: 8),
          child: _Press(
            scale: .96,
            onTap: onTap,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: lead ? plum : _lzBg(card),
                borderRadius: BorderRadius.circular(99),
                border: Border.all(color: lead ? gold : _lzLine(goldLine)),
              ),
              child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
                Icon(icon, size: 15, color: lead ? gold : gold),
                const SizedBox(width: 6),
                Text(label, style: TextStyle(color: lead ? ivory : _lzFg(plum), fontSize: 12.5, fontWeight: FontWeight.w700)),
              ]),
            ),
          ),
        );
    const Map<String, IconData> icons = <String, IconData>{
      'weather': Icons.wb_sunny_rounded, 'consults': Icons.event_available_rounded, 'analytics': Icons.insights_rounded, 'calendar': Icons.calendar_month_rounded,
      'funnel': Icons.filter_alt_rounded, 'goal': Icons.flag_rounded, 'hotdates': Icons.local_fire_department_rounded, 'money': Icons.payments_rounded,
      'reviews': Icons.star_rounded, 'notes': Icons.sticky_note_2_rounded, 'speed': Icons.bolt_rounded, 'quiet': Icons.hourglass_bottom_rounded,
      'deposits': Icons.request_quote_rounded, 'post': Icons.photo_camera_back_rounded, 'coming': Icons.event_rounded, 'strength': Icons.trending_up_rounded, 'share': Icons.ios_share_rounded,
    };
    return SizedBox(
      height: 40,
      child: ListView(scrollDirection: Axis.horizontal, children: <Widget>[
        chip('Widgets', Icons.dashboard_customize_rounded, () => open(null), lead: true),
        for (final String id in ids) chip(_railSummary(id, vendorId, vd), icons[id] ?? Icons.widgets_rounded, () => open(id)),
      ]),
    );
  }

  // ---- v196: JUNE'S FEED (the bell)
  Stream<QuerySnapshot<Map<String, dynamic>>> _feedStream() => _liveQuery('feed:$_uid',
      () => FirebaseFirestore.instance.collection('users').doc(_uid).collection('juneFeed').orderBy('at', descending: true).limit(40));

  Widget _feedBell() {
    return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
      stream: _feedStream(),
      initialData: _liveQ['feed:$_uid']?.latest,
      builder: (BuildContext c, AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> s) {
        final int unread = (s.data?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[]).where((QueryDocumentSnapshot<Map<String, dynamic>> d) => d.data()['read'] != true).length;
        return IconButton(
          tooltip: unread == 0 ? 'June\'s notices' : '$unread new from June',
          onPressed: _h(() => _feedSheet()),
          icon: Stack(clipBehavior: Clip.none, children: <Widget>[
            Icon(unread > 0 ? Icons.notifications_active_rounded : Icons.notifications_none_rounded, color: _lzFg(plum), size: 23),
            if (unread > 0)
              Positioned(
                right: -5,
                top: -4,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                  decoration: BoxDecoration(color: gold, borderRadius: BorderRadius.circular(99), border: Border.all(color: _lzBg(ivory), width: 1.5)),
                  child: Text(unread > 9 ? '9+' : '$unread', style: const TextStyle(color: plumDeep, fontSize: 10, fontWeight: FontWeight.w800)),
                ),
              ),
          ]),
        );
      },
    );
  }

  IconData _feedIcon(String k) {
    switch (k) {
      case 'lead':
        return Icons.mark_email_unread_rounded;
      case 'message':
        return Icons.chat_bubble_rounded;
      case 'booked':
        return Icons.celebration_rounded;
      case 'signed':
      case 'contract':
        return Icons.draw_rounded;
      case 'paid':
      case 'due':
      case 'invoice':
        return Icons.payments_rounded;
      case 'review':
        return Icons.star_rounded;
      case 'consult':
        return Icons.event_available_rounded;
      case 'rsvp':
        return Icons.how_to_reg_rounded;
      case 'morning':
        return Icons.wb_sunny_rounded;
    }
    return Icons.auto_awesome_rounded;
  }

  String _feedAgo(dynamic t) {
    if (t is! Timestamp) return '';
    final Duration d = DateTime.now().difference(t.toDate());
    if (d.inMinutes < 1) return 'now';
    if (d.inMinutes < 60) return '${d.inMinutes}m';
    if (d.inHours < 24) return '${d.inHours}h';
    if (d.inDays < 7) return '${d.inDays}d';
    return _jwDate(t);
  }

  void _feedSheet() {
    if (_uid == null) return;
    // opening the feed reads it
    final List<QueryDocumentSnapshot<Map<String, dynamic>>> docs = _liveQ['feed:$_uid']?.latest?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[];
    final WriteBatch b = FirebaseFirestore.instance.batch();
    int n = 0;
    for (final QueryDocumentSnapshot<Map<String, dynamic>> d in docs) {
      if (d.data()['read'] == true) continue;
      b.update(d.reference, <String, dynamic>{'read': true, 'readAt': Timestamp.now()});
      n++;
    }
    if (n > 0) b.commit().catchError((Object _) {});
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: _lzBg(ivory),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (BuildContext c) => SafeArea(
        child: ConstrainedBox(
          constraints: BoxConstraints(maxHeight: MediaQuery.of(c).size.height * .8),
          child: StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
            stream: _feedStream(),
            initialData: _liveQ['feed:$_uid']?.latest,
            builder: (BuildContext c2, AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> s) {
              final List<QueryDocumentSnapshot<Map<String, dynamic>>> ds = s.data?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[];
              return Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
                Padding(
                  padding: const EdgeInsets.fromLTRB(18, 14, 10, 4),
                  child: Row(children: <Widget>[
                    const Icon(Icons.auto_awesome_rounded, color: gold, size: 18),
                    const SizedBox(width: 8),
                    Expanded(child: Text('From June', style: GoogleFonts.cormorantGaramond(color: _lzFg(plum), fontSize: 22, fontWeight: FontWeight.w700))),
                    TextButton(onPressed: () => Navigator.of(c2).pop(), child: Text('Done', style: TextStyle(color: _lzFg(plum), fontWeight: FontWeight.w800))),
                  ]),
                ),
                if (ds.isEmpty)
                  Padding(padding: const EdgeInsets.fromLTRB(18, 8, 18, 24), child: Text('Nothing yet. New leads, bookings, payments and reviews show up here, and on your phone.', style: TextStyle(color: _lzFg(muted), fontSize: 13)))
                else
                  Flexible(
                    child: ListView.separated(
                      shrinkWrap: true,
                      padding: const EdgeInsets.fromLTRB(10, 0, 10, 16),
                      itemCount: ds.length,
                      separatorBuilder: (BuildContext _, int __) => Divider(height: 1, color: _lzLine(goldLine)),
                      itemBuilder: (BuildContext _, int i) {
                        final Map<String, dynamic> m = ds[i].data();
                        final String thread = (m['thread'] ?? '').toString();
                        final String openTo = (m['open'] ?? '').toString();
                        final bool fresh = m['readAt'] == null && m['read'] != true;
                        return ListTile(
                          contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                          leading: Container(
                            width: 36,
                            height: 36,
                            decoration: BoxDecoration(shape: BoxShape.circle, color: gold.withOpacity(.16), border: Border.all(color: gold.withOpacity(.5))),
                            child: Icon(_feedIcon((m['kind'] ?? '').toString()), size: 18, color: gold),
                          ),
                          title: Text((m['text'] ?? '').toString(), maxLines: 3, overflow: TextOverflow.ellipsis, style: TextStyle(color: _lzFg(ink), fontSize: 13.5, height: 1.35, fontWeight: fresh ? FontWeight.w700 : FontWeight.w500)),
                          trailing: Text(_feedAgo(m['at']), style: TextStyle(color: _lzFg(muted), fontSize: 11.5)),
                          onTap: () {
                            Navigator.of(c2).pop();
                            if (thread.isNotEmpty) {
                              _railOpen(thread);
                            } else if (openTo == 'reviews') {
                              setState(() => _dashMode = 'studio');
                            }
                          },
                        );
                      },
                    ),
                  ),
              ]);
            },
          ),
        ),
      ),
    );
  }

  Widget _railCard(String title, IconData icon, Widget content, {String? sub}) => Padding(""")

# ---- the Search segment reads in dark mode
rep("""const Map<String, Color> srcColor = <String, Color>{'search': Color(0xFF52284F),""", """final Map<String, Color> srcColor = <String, Color>{'search': _lzDark ? const Color(0xFFC9A0C6) : const Color(0xFF52284F),""")

OUT.write_text(s, encoding="utf-8", newline="\n")
print(f"wrote {OUT.name} ({len(s):,} chars)")
