r"""patch_vendor_v202.py - Vendor -> v202: MEAL COUNTS.  JC-LAZO-VENDOR-1016-MEALS

The caterer / venue sees the couple's meal choices as numbers, not just a file.
When a couple sends meal choices (Couple v161 -> inquiries/{id}/shared/meals), the
thread gets a MEAL COUNTS row above "From the couple": confirmed heads, the top
entrees, vendor meals, the final-count date and a gold dot while there is
something the vendor hasn't opened. Tap for the whole count: totals per entree,
kids, no choice yet, still to reply, vendor meals, allergies by name, per-table
counts, what changed since the last send, and the full printable sheet. The
vendor sets the FINAL COUNT DUE date there (default shown: two weeks before the
wedding) - the couple sees it on their card and the reminder job nudges them 7
and 2 days before - and can "Ask for an update" (a templated message).
The "From the couple" chip reads "Meal choices".

Needs firestore.rules JC-LAZO-RULES-1016-MEALS (shared/meals read + the
vendor's finalDue / vendorSeenAt write). Without it the row simply never shows.

Base: the newest Vendor master below v202 (pass a path to override), so this
re-applies on top of v200 / v201 from the video-call and COI sessions.

    python app-patches\patch_vendor_v202.py [base.txt]   # writes Vendor_master_v202.txt
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if len(sys.argv) > 1:
    SRC = Path(sys.argv[1])
else:
    vs = sorted(int(m.group(1)) for p in HERE.glob("Vendor_master_v*.txt")
                if (m := re.fullmatch(r"Vendor_master_v(\d+)\.txt", p.name)) and int(m.group(1)) < 202)
    SRC = HERE / f"Vendor_master_v{vs[-1]}.txt"
DST = HERE / "Vendor_master_v202.txt"
BASE = re.search(r"v(\d+)", SRC.name).group(1)
s = SRC.read_text(encoding="utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")


def rep(old, new, n=1):
    global s
    c = s.count(old)
    assert c == n, f"expected {n} match(es), found {c}: {old[:90]!r}"
    s = s.replace(old, new)


rep("// lazo_vendor_dashboard.dart\n",
    "// lazo_vendor_dashboard.dart\n"
    "// Build ID: JC-LAZO-VENDOR-1016-MEALS (v202: MEAL COUNTS - a couple's Send meal choices (Couple v161, "
    "inquiries/{id}/shared/meals) shows as a MEAL COUNTS row in the thread: confirmed heads, top entrees, vendor "
    "meals, the final-count date, a gold dot until opened; tap for totals, kids, no choice yet, still to reply, "
    "allergies by name, per-table counts, changes since the last send and the printable sheet; the vendor sets "
    "the final count due date (the couple's reminders run off it) and can ask for an update; the From the couple "
    f"chip reads Meal choices; base v{BASE})\n")

rep("""    <String>['guest_list', 'Guest list & meals', 'restaurant'],""",
    """    <String>['guest_list', 'Meal choices', 'restaurant'],""")

rep("""                _fromCoupleStrip(mdocs),
                Expanded(""", """                _mealCountsStrip(inquiryId, coupleName),
                _fromCoupleStrip(mdocs),
                Expanded(""")

MEALS = r"""  // v202 JC-LAZO-VENDOR-1016-MEALS: the couple's meal counts, from Couple
  // v161's Send meal choices (inquiries/{id}/shared/meals). One row in the
  // thread; tap for the whole count, the final-count date, ask for an update.
  static const Color _mealRose = Color(0xFFB04343);

  static int _mInt(dynamic v) => v is num ? v.toInt() : 0;

  DocumentReference<Map<String, dynamic>> _mealsRef(String inquiryId) =>
      FirebaseFirestore.instance
          .collection('inquiries')
          .doc(inquiryId)
          .collection('shared')
          .doc('meals');

  List<MapEntry<String, int>> _mealTotalsOf(Map<String, dynamic> m) =>
      <MapEntry<String, int>>[
        if (m['totals'] is List)
          for (final dynamic e in m['totals'] as List)
            if (e is Map)
              MapEntry<String, int>((e['m'] ?? '').toString(), _mInt(e['n']))
      ];

  // The vendor's date, or two weeks before the wedding until they set one.
  DateTime? _mealDue(Map<String, dynamic> m) {
    if (m['finalDue'] is Timestamp) return (m['finalDue'] as Timestamp).toDate();
    if (m['weddingDate'] is Timestamp) {
      return (m['weddingDate'] as Timestamp)
          .toDate()
          .subtract(const Duration(days: 14));
    }
    return null;
  }

  bool _mealUnseen(Map<String, dynamic> m) {
    if (m['sentAt'] is! Timestamp) return false;
    if (m['vendorSeenAt'] is! Timestamp) return true;
    return (m['vendorSeenAt'] as Timestamp)
        .toDate()
        .isBefore((m['sentAt'] as Timestamp).toDate());
  }

  Widget _mealCountsStrip(String inquiryId, String coupleName) {
    return StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
      stream: _liveDoc('meals:$inquiryId', () => _mealsRef(inquiryId)),
      initialData: _liveD['meals:$inquiryId']?.latest,
      builder: (BuildContext c,
          AsyncSnapshot<DocumentSnapshot<Map<String, dynamic>>> s) {
        final Map<String, dynamic>? m = s.data?.data();
        if (m == null || m['kind'] != 'meals') return const SizedBox.shrink();
        final List<MapEntry<String, int>> totals = _mealTotalsOf(m);
        final DateTime? due = _mealDue(m);
        final bool set = m['finalDue'] is Timestamp;
        final bool unseen = _mealUnseen(m);
        final String line = <String>[
          '${_mInt(m['heads'])} confirmed',
          for (final MapEntry<String, int> e in totals.take(3))
            '${e.value} ${e.key}',
          if (totals.length > 3) '+${totals.length - 3} more',
          if (_mInt(m['vendorCount']) > 0) '${_mInt(m['vendorCount'])} vendor',
        ].join(' · ');
        return _Press(
          onTap: () => _mealCountsSheet(inquiryId, coupleName),
          child: Container(
            padding: const EdgeInsets.fromLTRB(14, 8, 10, 8),
            decoration: BoxDecoration(
              color: _lzBg(Colors.white),
              border:
                  Border(bottom: BorderSide(color: gold.withOpacity(.35))),
            ),
            child: Row(children: <Widget>[
              Icon(Icons.restaurant_rounded, size: 16, color: _lzFg(plum)),
              const SizedBox(width: 8),
              Text('MEAL COUNTS',
                  style: TextStyle(
                      color: _lzFg(plum),
                      fontSize: 9.5,
                      letterSpacing: 1.8,
                      fontWeight: FontWeight.w800)),
              if (unseen)
                Container(
                  margin: const EdgeInsets.only(left: 6),
                  width: 7,
                  height: 7,
                  decoration:
                      const BoxDecoration(color: gold, shape: BoxShape.circle),
                ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(line,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                        color: _lzFg(ink),
                        fontSize: 12,
                        fontWeight: FontWeight.w700)),
              ),
              if (due != null) ...<Widget>[
                const SizedBox(width: 8),
                Text(set ? 'Due ${_shortDate(due)}' : 'Set due date',
                    style: TextStyle(
                        color: _lzFg(set ? muted : plum),
                        fontSize: 11,
                        fontWeight: FontWeight.w800)),
              ],
              Icon(Icons.chevron_right_rounded,
                  size: 18, color: _lzFg(muted)),
            ]),
          ),
        );
      },
    );
  }

  Future<void> _mealCountsSheet(String inquiryId, String coupleName) async {
    try {
      await _mealsRef(inquiryId).set(<String, dynamic>{
        'vendorSeenAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));
    } catch (e) {
      debugPrint('LAZO meals seen: ' + e.toString());
    }
    if (!mounted) return;
    bool busy = false;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 600),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx, StateSetter setS) =>
            StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
          stream: _liveDoc('meals:$inquiryId', () => _mealsRef(inquiryId)),
          initialData: _liveD['meals:$inquiryId']?.latest,
          builder: (BuildContext c,
              AsyncSnapshot<DocumentSnapshot<Map<String, dynamic>>> s) {
            final Map<String, dynamic> m =
                s.data?.data() ?? <String, dynamic>{};
            final List<MapEntry<String, int>> totals = _mealTotalsOf(m);
            final DateTime? due = _mealDue(m);
            final bool set = m['finalDue'] is Timestamp;
            final String sent = m['sentAt'] is Timestamp
                ? _shortDate((m['sentAt'] as Timestamp).toDate())
                : '';
            final List<String> diff = <String>[];
            if (m['prev'] is Map) {
              final Map<String, dynamic> p =
                  Map<String, dynamic>.from(m['prev'] as Map);
              final Map<String, int> was = <String, int>{
                for (final MapEntry<String, int> e in _mealTotalsOf(p))
                  e.key: e.value
              };
              final Map<String, int> now = <String, int>{
                for (final MapEntry<String, int> e in totals) e.key: e.value
              };
              for (final String k in <String>{...now.keys, ...was.keys}) {
                final int d = (now[k] ?? 0) - (was[k] ?? 0);
                if (d != 0) diff.add('${d > 0 ? '+$d' : '−${-d}'} $k');
              }
              final int dv =
                  _mInt(m['vendorCount']) - _mInt(p['vendorCount']);
              if (dv != 0) {
                diff.add('${dv > 0 ? '+$dv' : '−${-dv}'} vendor meals');
              }
            }
            final String prevAt = m['prevAt'] is Timestamp
                ? _shortDate((m['prevAt'] as Timestamp).toDate())
                : '';
            final List<String> allergies = m['allergies'] is List
                ? (m['allergies'] as List).map((dynamic e) => e.toString()).toList()
                : <String>[];
            final List<Map<String, dynamic>> tables = m['tables'] is List
                ? (m['tables'] as List)
                    .whereType<Map>()
                    .map((Map e) => Map<String, dynamic>.from(e))
                    .toList()
                : <Map<String, dynamic>>[];
            final List<Map<String, dynamic>> vmeals = m['vendorMeals'] is List
                ? (m['vendorMeals'] as List)
                    .whereType<Map>()
                    .map((Map e) => Map<String, dynamic>.from(e))
                    .toList()
                : <Map<String, dynamic>>[];

            Widget countRow(String label, int n, {bool strong = true}) =>
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  child: Row(children: <Widget>[
                    Expanded(
                      child: Text(label,
                          style: TextStyle(
                              color: _lzFg(ink),
                              fontSize: 13.5,
                              fontWeight:
                                  strong ? FontWeight.w700 : FontWeight.w500)),
                    ),
                    Text('$n',
                        style: TextStyle(
                            color: _lzFg(strong ? plum : muted),
                            fontSize: 15,
                            fontWeight: FontWeight.w800)),
                  ]),
                );

            Future<void> pickDue() async {
              final DateTime now = DateTime.now();
              DateTime initial = due ?? now.add(const Duration(days: 14));
              if (initial.isBefore(now)) initial = now;
              final DateTime? picked = await showDatePicker(
                context: ctx,
                initialDate: initial,
                firstDate: DateTime(now.year, now.month, now.day),
                lastDate: DateTime(now.year + 3),
                helpText: 'Final count due',
                builder: (BuildContext dc, Widget? child) => Theme(
                  data: Theme.of(dc).copyWith(
                    colorScheme: const ColorScheme.light(
                      primary: plum,
                      onPrimary: ivory,
                      onSurface: ink,
                    ),
                  ),
                  child: child!,
                ),
              );
              if (picked == null) return;
              setS(() => busy = true);
              try {
                await _mealsRef(inquiryId).set(<String, dynamic>{
                  'finalDue': Timestamp.fromDate(
                      DateTime(picked.year, picked.month, picked.day, 12)),
                  'finalDueSetAt': FieldValue.serverTimestamp(),
                }, SetOptions(merge: true));
                _toast('Final count due ${_shortDate(picked)} ✓ '
                    '${coupleName.isEmpty ? 'The couple' : coupleName} will see it, with reminders before.');
              } catch (e) {
                _toast('Could not save the date: ' + _errText(e));
              }
              if (ctx.mounted) setS(() => busy = false);
            }

            Future<void> askUpdate() async {
              setS(() => busy = true);
              final String when = due == null ? '' : ' by ${_shortDate(due)}';
              try {
                await FirebaseFirestore.instance
                    .collection('inquiries')
                    .doc(inquiryId)
                    .collection('messages')
                    .add(<String, dynamic>{
                  'senderRole': 'vendor',
                  'text':
                      'Could you send us your updated meal choices$when? In your Lazo app: Guests › Meal choices › Send update. Thank you!',
                  'at': FieldValue.serverTimestamp(),
                });
                try {
                  await FirebaseFirestore.instance
                      .collection('inquiries')
                      .doc(inquiryId)
                      .set(<String, dynamic>{
                    'lastMessageAt': FieldValue.serverTimestamp(),
                    'lastMessageRole': 'vendor',
                    'lastMessagePreview': 'Asked for updated meal choices',
                  }, SetOptions(merge: true));
                } catch (_) {}
                _toast('Asked ✓ It’s in your thread.');
              } catch (e) {
                _toast('Could not send: ' + _errText(e));
              }
              if (ctx.mounted) setS(() => busy = false);
            }

            return _lzFrame(ctx,
                icon: Icons.restaurant_rounded,
                title: 'Meal counts',
                subtitle: <String>[
                  if (coupleName.isNotEmpty) coupleName,
                  if (sent.isNotEmpty) 'sent $sent',
                ].join(' · '),
                children: <Widget>[
                  if (m.isEmpty)
                    _lzNote(Icons.info_outline_rounded,
                        'Nothing sent yet.')
                  else ...<Widget>[
                    _lzSection('Meals',
                        trailing: '${_mInt(m['heads'])} confirmed'),
                    for (final MapEntry<String, int> e in totals)
                      countRow(e.key, e.value),
                    if (_mInt(m['noChoice']) > 0)
                      countRow('No choice yet', _mInt(m['noChoice']),
                          strong: false),
                    if (_mInt(m['vendorCount']) > 0)
                      countRow('Vendor meals', _mInt(m['vendorCount'])),
                    if (_mInt(m['awaiting']) > 0)
                      countRow('Guests still to reply', _mInt(m['awaiting']),
                          strong: false),
                    if (diff.isNotEmpty) ...<Widget>[
                      const SizedBox(height: 8),
                      _lzNote(Icons.update_rounded,
                          'Since ${prevAt.isEmpty ? 'their last send' : prevAt}: ${diff.join(', ')}'),
                    ],
                    _lzSection('Final count due'),
                    Row(children: <Widget>[
                      Icon(Icons.event_rounded,
                          size: 18,
                          color: _lzFg(set ? plum : _mealRose)),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                            due == null
                                ? 'Pick the date you need the final count.'
                                : set
                                    ? _shortDate(due)
                                    : 'Not set - about ${_shortDate(due)} (two weeks out) until you pick one.',
                            style: TextStyle(
                                color: _lzFg(ink),
                                fontSize: 13,
                                fontWeight:
                                    set ? FontWeight.w800 : FontWeight.w500)),
                      ),
                      TextButton(
                        onPressed: busy ? null : _h(pickDue),
                        child: Text(set ? 'Change' : 'Set date',
                            style: TextStyle(
                                color: _lzFg(plum),
                                fontWeight: FontWeight.w800)),
                      ),
                    ]),
                    if (allergies.isNotEmpty) ...<Widget>[
                      _lzSection('Allergies & dietary',
                          trailing: '${_mInt(m['allergyCount'])}'),
                      for (final String a in allergies)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 4),
                          child: Text('• $a',
                              style: TextStyle(
                                  color: _lzFg(ink), fontSize: 12.5)),
                        ),
                    ],
                    if (tables.isNotEmpty) ...<Widget>[
                      _lzSection('By table', trailing: '${tables.length}'),
                      for (final Map<String, dynamic> t in tables)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 5),
                          child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                SizedBox(
                                  width: 96,
                                  child: Text((t['t'] ?? '').toString(),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: TextStyle(
                                          color: _lzFg(plum),
                                          fontSize: 12.5,
                                          fontWeight: FontWeight.w800)),
                                ),
                                Expanded(
                                  child: Text((t['line'] ?? '').toString(),
                                      style: TextStyle(
                                          color: _lzFg(ink), fontSize: 12.5)),
                                ),
                              ]),
                        ),
                    ],
                    if (vmeals.isNotEmpty) ...<Widget>[
                      _lzSection('Vendor meals',
                          trailing: '${_mInt(m['vendorCount'])}'),
                      for (final Map<String, dynamic> v in vmeals)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 4),
                          child: Text(
                              '${v['name']}${(v['role'] ?? '').toString().isEmpty ? '' : ' (${v['role']})'}: ${_mInt(v['count'])}',
                              style: TextStyle(
                                  color: _lzFg(ink), fontSize: 12.5)),
                        ),
                    ],
                  ],
                ],
                footer: _lzActions(
                    secondary: 'Ask for an update',
                    onSecondary: busy ? null : _h(askUpdate),
                    primary: 'Full sheet',
                    icon: Icons.print_rounded,
                    onPrimary: (m['fileUrl'] ?? '').toString().isEmpty
                        ? null
                        : () => _openUrl(m['fileUrl'].toString())));
          },
        ),
      ),
    );
  }

"""
rep("""  // v159: what the couple has shared from their plan, one chip per kind,""",
    MEALS + """  // v159: what the couple has shared from their plan, one chip per kind,""")

if crlf:
    s = s.replace("\n", "\r\n")
DST.write_text(s, encoding="utf-8", newline="")
print(f"wrote {DST.name} from {SRC.name} ({len(s):,} chars)")
