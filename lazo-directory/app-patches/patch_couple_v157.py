r"""patch_couple_v157.py - Couple v156 -> v157 (JC-LAZO-COUPLE-1014-157)
  - JUNE'S FEED: a bell in the header with the unread count; the sheet lists
    June's last 40 notices (users/{uid}/juneFeed, from functions-dashboard 027,
    which also pushes them to the phone); tap one to open it; opening reads them.
  - PARTNERS IN STEP: importing guests, adding a guest, marking a vendor
    booked and publishing the website write couples/{cid}/activity; the other
    partner hears it from June live on the dashboard, and as a push (027).
  - Pay from the widget: Payments due rows carry a Pay button (the same card
    checkout the thread uses; falls back to the thread).
  - Your website: visits (7 days and all time) from the site's own counter.
  - No numbers twice: the hero drops Vendor team, Budget and Vendor replies
    when those widgets are on.
  - One voice: the inbox chime stays quiet while June announces.
  - Phones: a strip of widget chips near the top of the hub.
  - Big screens: the widget column widens to 420 above 1500 px.
  - Widget titles in the serif; links and the overdue red read in both themes.

    python app-patches\patch_couple_v157.py
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
s = (HERE / "Couple_master_v156.txt").read_text(encoding="utf-8")
OUT = HERE / "Couple_master_v157.txt"


def rep(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"anchor found {n}x (want {count}): {old[:90]!r}")
    s = s.replace(old, new)


# ---- the widget body becomes a method (the phone strip opens one widget)
a = s.index("    Widget body(String id) {\n      switch (id) {\n        case 'weather':")
b = s.index("      return const SizedBox.shrink();\n    }\n", a) + len("      return const SizedBox.shrink();\n    }\n")
switch = s[a:b]
s = s[:a] + "    Widget body(String id) => _crBody(id, couple, plan, inqs, wed, daysOut);\n" + s[b:]
method = switch.replace("    Widget body(String id) {", "  Widget _crBody(String id, Map<String, dynamic> couple, Map<String, Map<String, dynamic>> plan, List<QueryDocumentSnapshot<Map<String, dynamic>>> inqs, DateTime? wed, int? daysOut) {", 1)
method = "\n".join(l[2:] if l.startswith("  ") and not l.startswith("  Widget _crBody") else l for l in method.split("\n"))
rep("""  Widget _crCard(String title, IconData icon, Widget content, {String? sub}) => Padding(""", method + """
  Widget _crCard(String title, IconData icon, Widget content, {String? sub}) => Padding(""")

# ---- serif titles
rep("""              Expanded(child: Text(title, style: TextStyle(color: _lzFg(plum), fontWeight: FontWeight.w800, fontSize: 13.5))),""",
    """              Expanded(child: Text(title, style: _serif(size: 19, weight: FontWeight.w600, color: _lzFg(plum)))),""")

# ---- links and red that read in both themes (widget code only)
w0 = s.index("  // v156: WIDGETS (couples)")
w1 = s.index("  List<_TourStep> _coupleTourSteps({required bool needsSetup}) {")
seg = s[w0:w1]
seg = re.sub(r"const Text\(('[^']*'), style: TextStyle\(color: gold, ", r"Text(\1, style: TextStyle(color: _crLink, ", seg)
seg = seg.replace("const Color(0xFFB4534B)", "_crRed")
seg = seg.replace("const Icon(Icons.dashboard_customize_rounded, size: 16, color: gold),", "Icon(Icons.dashboard_customize_rounded, size: 16, color: _crLink),")
seg = seg.replace("style: const TextStyle(color: gold, fontWeight: FontWeight.w700, fontSize: 12.5)),", "style: TextStyle(color: _crLink, fontWeight: FontWeight.w700, fontSize: 12.5)),")
seg = seg.replace("style: const TextStyle(color: gold, fontWeight: FontWeight.w800, fontSize: 12)", "style: TextStyle(color: _crLink, fontWeight: FontWeight.w800, fontSize: 12)")
s = s[:w0] + seg + s[w1:]
rep("""  bool _crKnown(String id) =>""", """  Color get _crLink => _lzDark ? gold : plum;
  Color get _crRed => _lzDark ? const Color(0xFFEE9A90) : const Color(0xFFB4534B);

  bool _crKnown(String id) =>""")

# ---- no numbers twice in the hero
rep("""      _heroTile(
          'Vendor team',""", """      if (!_cr.contains('team'))
      _heroTile(
          'Vendor team',""")
rep("""      _heroTile(
          'Budget',""", """      if (!_cr.contains('budget'))
      _heroTile(
          'Budget',""")
rep("""      _heroTile(
          'Vendor replies',""", """      if (!_cr.contains('replies'))
      _heroTile(
          'Vendor replies',""")

# ---- one voice
rep("""  void _playChime() {
    if (_chimeMuted) return;""", """  void _playChime() {
    if (_chimeMuted) return;
    if (_cwVoice && _cwFor.isNotEmpty && _tourIdx < 0) return; // v157: June says it instead""")

# ---- big screens
rep("""            SizedBox(
              width: 340,
              child: ListView(
                cacheExtent: 3000,""", """            SizedBox(
              width: cons.maxWidth >= 1500 ? 420 : 340,
              child: ListView(
                cacheExtent: 3000,""")

# ---- phones: the strip near the top
rep("""              _linkBookingBanner(couple, inqs),
              const SizedBox(height: 14),""", """              _linkBookingBanner(couple, inqs),
              if (!railSide) ...<Widget>[
                const SizedBox(height: 12),
                _crStrip(couple, plan, inqs, weddingDate, daysOut),
              ],
              const SizedBox(height: 14),""")

# ---- the bell in the header
rep("""                  _msgHeaderButton(),
                  const SizedBox(width: 10),""", """                  _cFeedBell(),
                  const SizedBox(width: 10),
                  _msgHeaderButton(),
                  const SizedBox(width: 10),""")

# ---- partner activity: where it happens
rep("""      if (inBatch > 0) await b.commit();
      await _coupleRef.set(
          <String, dynamic>{'importedAt': FieldValue.serverTimestamp()},
          SetOptions(merge: true));""", """      if (inBatch > 0) await b.commit();
      await _coupleRef.set(
          <String, dynamic>{'importedAt': FieldValue.serverTimestamp()},
          SetOptions(merge: true));
      if (added > 0) _logActivity('imported $added guest${added == 1 ? '' : 's'} to the list.', open: 'guests');""")
rep("""    if (id == null) {
      data['createdAt'] = FieldValue.serverTimestamp();
      await _guestsRef.add(data);
    } else {""", """    if (id == null) {
      data['createdAt'] = FieldValue.serverTimestamp();
      await _guestsRef.add(data);
      _logActivity('added ${data['name']} to the guest list.', open: 'guests');
    } else {""")
rep("""    _celebrate();
    _bookedShareSnack('$vendorName is booked """, """    _celebrate();
    _logActivity('booked $vendorName for the $label.', open: 'vendors');
    _bookedShareSnack('$vendorName is booked """)
rep("""        _siteLiveShareSheet(joinedNames(), slug);""", """        _logActivity('published your wedding website.', open: 'website');
        _siteLiveShareSheet(joinedNames(), slug);""")

# the other partner hears it live (the push comes from the server)
rep("""    Future<void>.delayed(const Duration(seconds: 6), _cwDaily);
  }""", """    // v157: what the other partner just did
    _cwSubs.add(_coupleRef.collection('activity').orderBy('at', descending: true).limit(10).snapshots().listen((QuerySnapshot<Map<String, dynamic>> snap) {
      final bool first = !_cwArmed.contains('act');
      for (final DocumentChange<Map<String, dynamic>> ch in snap.docChanges) {
        if (ch.type != DocumentChangeType.added) continue;
        final Map<String, dynamic> a = ch.doc.data() ?? <String, dynamic>{};
        if ((a['by'] ?? '') == _uid) continue;
        if (first) {
          if (_cwSince(a['at'])) _cwAwayAdd('act:${ch.doc.id}', (a['text'] ?? '').toString().replaceAll(RegExp(r'\\.$'), ''));
          continue;
        }
        if (!_cwFresh(a['at'], minutes: 10)) continue;
        final String open = (a['open'] ?? '').toString();
        _cwSay('act:${ch.doc.id}', (a['text'] ?? '').toString(), icon: Icons.favorite_rounded, go: open == 'guests' ? _View.guests : open == 'website' ? _View.website : open == 'vendors' ? _View.vendors : null);
      }
      _cwArmed.add('act');
    }, onError: (Object _) {}));

    Future<void>.delayed(const Duration(seconds: 6), _cwDaily);
  }

  // v157: a line for the partner (and the push the server sends them)
  Future<void> _logActivity(String what, {String open = ''}) async {
    if (_cid.isEmpty || _uid == null) return;
    final String me = (FirebaseAuth.instance.currentUser?.displayName ?? '').trim().split(RegExp(r'\\s+')).first;
    final String who = me.isEmpty ? 'Your partner' : me;
    try {
      await _coupleRef.collection('activity').add(<String, dynamic>{
        'by': _uid,
        'byName': who,
        'text': '$who $what',
        'open': open,
        'at': FieldValue.serverTimestamp(),
      });
    } catch (_) {}
  }""")

# ---- payments: a Pay button, and the code for everything else
rep("""          return _crRow(
            title: (_cwInq[inq]?['vendor'] ?? 'Your vendor').toString(),
            sub: (i['title'] ?? 'Invoice').toString(),""", """          return Row(children: <Widget>[
            Expanded(
              child: _crRow(
            title: (_cwInq[inq]?['vendor'] ?? 'Your vendor').toString(),
            sub: (i['title'] ?? 'Invoice').toString(),""")
rep("""            rightColor: days < 0 ? _crRed : (days <= 7 ? gold : _lzFg(plum)),
            onTap: () {
              setState(() => _view = _View.messages);
              _openCoupleThread(inq, (_cwInq[inq]?['data'] as Map<String, dynamic>?) ?? <String, dynamic>{});
            },
          );""", """            rightColor: days < 0 ? _crRed : (days <= 7 ? gold : _lzFg(plum)),
            onTap: () {
              setState(() => _view = _View.messages);
              _openCoupleThread(inq, (_cwInq[inq]?['data'] as Map<String, dynamic>?) ?? <String, dynamic>{});
            },
              ),
            ),
            const SizedBox(width: 6),
            FilledButton(
              style: FilledButton.styleFrom(backgroundColor: gold, foregroundColor: plumDeep, visualDensity: VisualDensity.compact, padding: const EdgeInsets.symmetric(horizontal: 12)),
              onPressed: _payingInvoiceId == (i['_id'] ?? '').toString() ? null : () => _crPay(inq, (i['_id'] ?? '').toString()),
              child: Text(_payingInvoiceId == (i['_id'] ?? '').toString() ? '...' : 'Pay', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5)),
            ),
          ]);""")

rep("""  Widget _crCard(String title, IconData icon, Widget content, {String? sub}) => Padding(""", r"""  // v157: pay from the widget - the thread's card checkout, else the thread
  Future<void> _crPay(String inquiryId, String invoiceId) async {
    if (inquiryId.isEmpty || invoiceId.isEmpty) return;
    setState(() => _payingInvoiceId = invoiceId);
    try {
      final httpc.Response res = await httpc.get(Uri.parse('$_kCheckoutFn?inquiry=$inquiryId&invoice=$invoiceId&tip=0'), headers: <String, String>{'Content-Type': 'application/json'}).timeout(const Duration(seconds: 25));
      final dynamic r = jsonDecode(res.body.isEmpty ? '{}' : res.body);
      final String url = r is Map ? (r['url'] ?? '').toString() : '';
      if (url.isNotEmpty) {
        await _openSigning(url);
        return;
      }
    } catch (_) {
    } finally {
      if (mounted) setState(() => _payingInvoiceId = '');
    }
    // no card checkout for this vendor: the thread shows how they take payment
    if (!mounted) return;
    setState(() => _view = _View.messages);
    _openCoupleThread(inquiryId, (_cwInq[inquiryId]?['data'] as Map<String, dynamic>?) ?? <String, dynamic>{});
  }

  // v157: one line per widget for the phone strip
  String _crSummary(String id, Map<String, dynamic> couple, Map<String, Map<String, dynamic>> plan, List<QueryDocumentSnapshot<Map<String, dynamic>>> inqs, int? daysOut) {
    switch (id) {
      case 'countdown':
        return daysOut == null ? 'Set your date' : daysOut < 0 ? 'Married' : daysOut == 0 ? 'Today!' : '$daysOut days to go';
      case 'weather':
        return _weatherFoldSummary(couple) ?? 'Weather';
      case 'team':
        final List<Map<String, dynamic>> need = plan.values.where((Map<String, dynamic> p) => (p['status'] ?? 'needed') != 'skipped').toList();
        return need.isEmpty ? 'Vendor team' : '${need.where((Map<String, dynamic> p) => p['status'] == 'booked').length} of ${need.length} booked';
      case 'budget':
        final num total = couple['budgetTotal'] is num ? couple['budgetTotal'] as num : 0;
        num committed = 0;
        for (final Map<String, dynamic> p in plan.values) {
          if (p['budgetActual'] is num) committed += p['budgetActual'] as num;
        }
        return total > 0 ? '\$${_money(total - committed)} left' : 'Budget';
      case 'replies':
        final int w = inqs.where((QueryDocumentSnapshot<Map<String, dynamic>> d) => (d.data()['lastMessageRole'] ?? '') == 'vendor' && (d.data()['status'] ?? '') != 'lost').length;
        return w == 0 ? 'Nobody waiting' : '$w waiting on you';
      case 'payments':
        num t = 0;
        for (final List<Map<String, dynamic>> l in _cwInv.values) {
          for (final Map<String, dynamic> i in l) {
            if ((i['status'] ?? '') != 'paid' && (i['status'] ?? '') != 'void' && i['total'] is num && i['dueDate'] is Timestamp) t += i['total'] as num;
          }
        }
        return t > 0 ? '\$${_money(t)} due' : 'Nothing due';
      case 'rsvp':
        int yes = 0;
        for (final QueryDocumentSnapshot<Map<String, dynamic>> d in _liveQ['guests:$_cid']?.latest?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[]) {
          final String r = (d.data()['rsvp'] ?? '').toString().toLowerCase();
          if (d.data()['rsvp'] == true || r.startsWith('yes') || r.startsWith('attend')) yes += d.data()['count'] is num ? (d.data()['count'] as num).toInt() : 1;
        }
        return '$yes coming';
      case 'website':
        final Map<String, dynamic> sd = _liveD['site:$_cwSlug']?.latest?.data() ?? <String, dynamic>{};
        return _cwSlug.isEmpty ? 'Your website' : '${(sd['viewsTotal'] is num ? (sd['viewsTotal'] as num).round() : 0)} visits';
    }
    return _crTitle(id)[1];
  }

  Widget _crStrip(Map<String, dynamic> couple, Map<String, Map<String, dynamic>> plan, List<QueryDocumentSnapshot<Map<String, dynamic>>> inqs, DateTime? wed, int? daysOut) {
    final List<String> ids = _cr.where(_crKnown).toList();
    void open(String? id) {
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
                if (id == null) _crStack(couple, plan, inqs, wed, daysOut) else _crBody(id, couple, plan, inqs, wed, daysOut),
              ]),
            ),
          ),
        ),
      );
    }

    const Map<String, IconData> icons = <String, IconData>{
      'weather': Icons.wb_sunny_rounded, 'countdown': Icons.hourglass_top_rounded, 'budget': Icons.account_balance_wallet_rounded, 'rsvp': Icons.how_to_reg_rounded,
      'team': Icons.groups_rounded, 'payments': Icons.payments_rounded, 'replies': Icons.mark_chat_unread_rounded, 'website': Icons.language_rounded,
      'dayof': Icons.schedule_rounded, 'shopping': Icons.shopping_bag_rounded, 'notes': Icons.sticky_note_2_rounded,
    };
    Widget chip(String label, IconData icon, VoidCallback onTap, {bool lead = false}) => Padding(
          padding: const EdgeInsets.only(right: 8),
          child: _Press(
            scale: .96,
            onTap: onTap,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(color: lead ? gold : _lzBg(ivory.withOpacity(.12)), borderRadius: BorderRadius.circular(99), border: Border.all(color: gold.withOpacity(lead ? 1 : .6))),
              child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
                Icon(icon, size: 15, color: lead ? plumDeep : gold),
                const SizedBox(width: 6),
                Text(label, style: TextStyle(color: lead ? plumDeep : ivory, fontSize: 12.5, fontWeight: FontWeight.w700)),
              ]),
            ),
          ),
        );
    return SizedBox(
      height: 40,
      child: ListView(scrollDirection: Axis.horizontal, children: <Widget>[
        chip('Widgets', Icons.dashboard_customize_rounded, () => open(null), lead: true),
        for (final String id in ids) chip(_crSummary(id, couple, plan, inqs, daysOut), icons[id] ?? Icons.widgets_rounded, () => open(id)),
      ]),
    );
  }

  // ---- v157: JUNE'S FEED (the bell)
  Stream<QuerySnapshot<Map<String, dynamic>>> _cFeedStream() => _liveQuery('feed:$_uid',
      () => FirebaseFirestore.instance.collection('users').doc(_uid).collection('juneFeed').orderBy('at', descending: true).limit(40));

  Widget _cFeedBell() {
    if (_uid == null) return const SizedBox.shrink();
    return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
      stream: _cFeedStream(),
      initialData: _liveQ['feed:$_uid']?.latest,
      builder: (BuildContext c, AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> s) {
        final int unread = (s.data?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[]).where((QueryDocumentSnapshot<Map<String, dynamic>> d) => d.data()['read'] != true).length;
        return _Press(
          scale: .92,
          onTap: _cFeedSheet,
          child: Stack(clipBehavior: Clip.none, children: <Widget>[
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(shape: BoxShape.circle, color: _lzBg(ivory.withOpacity(.10)), border: Border.all(color: gold.withOpacity(.7), width: 1.2)),
              child: Icon(unread > 0 ? Icons.notifications_active_rounded : Icons.notifications_none_rounded, color: gold, size: 20),
            ),
            if (unread > 0)
              Positioned(
                right: -2,
                top: -2,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                  decoration: BoxDecoration(color: gold, borderRadius: BorderRadius.circular(99), border: Border.all(color: plumDeep, width: 1.5)),
                  child: Text(unread > 9 ? '9+' : '$unread', style: const TextStyle(color: plumDeep, fontSize: 10, fontWeight: FontWeight.w800)),
                ),
              ),
          ]),
        );
      },
    );
  }

  IconData _cFeedIcon(String k) {
    switch (k) {
      case 'message':
        return Icons.chat_bubble_rounded;
      case 'booked':
        return Icons.celebration_rounded;
      case 'contract':
        return Icons.draw_rounded;
      case 'invoice':
      case 'due':
        return Icons.payments_rounded;
      case 'rsvp':
        return Icons.how_to_reg_rounded;
      case 'partner':
        return Icons.favorite_rounded;
      case 'morning':
        return Icons.wb_sunny_rounded;
    }
    return Icons.auto_awesome_rounded;
  }

  void _cFeedSheet() {
    if (_uid == null) return;
    final List<QueryDocumentSnapshot<Map<String, dynamic>>> docs = _liveQ['feed:$_uid']?.latest?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[];
    final WriteBatch b = FirebaseFirestore.instance.batch();
    int n = 0;
    for (final QueryDocumentSnapshot<Map<String, dynamic>> d in docs) {
      if (d.data()['read'] == true) continue;
      b.update(d.reference, <String, dynamic>{'read': true, 'readAt': FieldValue.serverTimestamp()});
      n++;
    }
    if (n > 0) b.commit().catchError((Object _) {});
    String ago(dynamic t) {
      if (t is! Timestamp) return '';
      final Duration d = DateTime.now().difference(t.toDate());
      if (d.inMinutes < 1) return 'now';
      if (d.inMinutes < 60) return '${d.inMinutes}m';
      if (d.inHours < 24) return '${d.inHours}h';
      if (d.inDays < 7) return '${d.inDays}d';
      return _shortDate(t.toDate());
    }

    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: _lzBg(ivory),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (BuildContext c) => SafeArea(
        child: ConstrainedBox(
          constraints: BoxConstraints(maxHeight: MediaQuery.of(c).size.height * .8),
          child: StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
            stream: _cFeedStream(),
            initialData: _liveQ['feed:$_uid']?.latest,
            builder: (BuildContext c2, AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> s) {
              final List<QueryDocumentSnapshot<Map<String, dynamic>>> ds = s.data?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[];
              return Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
                Padding(
                  padding: const EdgeInsets.fromLTRB(18, 14, 10, 4),
                  child: Row(children: <Widget>[
                    const Icon(Icons.auto_awesome_rounded, color: gold, size: 18),
                    const SizedBox(width: 8),
                    Expanded(child: Text('From June', style: _serif(size: 22, weight: FontWeight.w600, color: _lzFg(plum)))),
                    TextButton(onPressed: () => Navigator.of(c2).pop(), child: Text('Done', style: TextStyle(color: _lzFg(plum), fontWeight: FontWeight.w800))),
                  ]),
                ),
                if (ds.isEmpty)
                  Padding(padding: const EdgeInsets.fromLTRB(18, 8, 18, 24), child: Text('Nothing yet. Vendor replies, contracts, payments and RSVPs show up here, and on your phone.', style: TextStyle(color: _lzFg(muted), fontSize: 13)))
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
                            child: Icon(_cFeedIcon((m['kind'] ?? '').toString()), size: 18, color: gold),
                          ),
                          title: Text((m['text'] ?? '').toString(), maxLines: 3, overflow: TextOverflow.ellipsis, style: TextStyle(color: _lzFg(ink), fontSize: 13.5, height: 1.35, fontWeight: fresh ? FontWeight.w700 : FontWeight.w500)),
                          trailing: Text(ago(m['at']), style: TextStyle(color: _lzFg(muted), fontSize: 11.5)),
                          onTap: () {
                            Navigator.of(c2).pop();
                            if (thread.isNotEmpty) {
                              setState(() => _view = _View.messages);
                              _openCoupleThread(thread, (_cwInq[thread]?['data'] as Map<String, dynamic>?) ?? <String, dynamic>{});
                            } else if (openTo == 'guests') {
                              setState(() => _view = _View.guests);
                            } else if (openTo == 'website') {
                              setState(() => _view = _View.website);
                            } else if (openTo == 'vendors') {
                              setState(() => _view = _View.vendors);
                            } else if (openTo == 'june') {
                              setState(() => _view = _View.june);
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

  Widget _crCard(String title, IconData icon, Widget content, {String? sub}) => Padding(""")

# ---- the website widget: visits
rep("""    final String url = 'https://meetlazo.com/w/$_cwSlug/';
    final int n = _liveQ['rsvp:$_cwSlug']?.latest?.docs.length ?? 0;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
      Row(children: <Widget>[
        _crStat('$n', 'RSVPs through your site'),
      ]),""", """    final String url = 'https://meetlazo.com/w/$_cwSlug/';
    final int n = _liveQ['rsvp:$_cwSlug']?.latest?.docs.length ?? 0;
    return StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
      stream: _liveDoc('site:$_cwSlug', () => FirebaseFirestore.instance.collection('weddingSites').doc(_cwSlug)),
      initialData: _liveD['site:$_cwSlug']?.latest,
      builder: (BuildContext c, AsyncSnapshot<DocumentSnapshot<Map<String, dynamic>>> sd) {
        final Map<String, dynamic> site = sd.data?.data() ?? <String, dynamic>{};
        final int total = site['viewsTotal'] is num ? (site['viewsTotal'] as num).round() : 0;
        int week = 0;
        if (site['viewsByDay'] is Map) {
          final DateTime now = DateTime.now();
          for (int k = 0; k < 7; k++) {
            final dynamic v = (site['viewsByDay'] as Map)[_ymd(now.subtract(Duration(days: k)))];
            if (v is num) week += v.round();
          }
        }
        return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
      Row(children: <Widget>[
        _crStat('$week', 'Visits this week'),
        const SizedBox(width: 8),
        _crStat('$total', 'Visits in all'),
        const SizedBox(width: 8),
        _crStat('$n', 'RSVPs online'),
      ]),""")
rep("""          onPressed: () => setState(() => _view = _View.website),
          icon: const Icon(Icons.edit_rounded, size: 15, color: gold),
          label: Text('Edit', style: TextStyle(color: _crLink, fontWeight: FontWeight.w800, fontSize: 12)),
        ),
      ]),
    ]);
  }""", """          onPressed: () => setState(() => _view = _View.website),
          icon: const Icon(Icons.edit_rounded, size: 15, color: gold),
          label: Text('Edit', style: TextStyle(color: _crLink, fontWeight: FontWeight.w800, fontSize: 12)),
        ),
      ]),
    ]);
      },
    );
  }""")

OUT.write_text(s, encoding="utf-8", newline="\n")
print(f"wrote {OUT.name} ({len(s):,} chars)")
