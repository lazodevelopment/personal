"""Couple v178: three vendor picks inside the checklist task (JC-LAZO-PICKS-1019-COUPLE).

    python app-patches\\patch_couple_v178.py [base.txt]   # base defaults to Couple_master_v177.txt
                                                          # writes Couple_master_v178.txt
Pearl Connect's one structural edge (2026-10-19 audit): vendors show up inside the couple's checklist
task, native to the planning journey. Now every 'Book the ...' / 'Hire ...' / 'Order invitations' /
'Cake tasting' / 'Rentals' / 'Tour venues' / 'Engagement photos' / 'Finalize the menu' task that maps to a
Lazo category carries a "Three <category> picks" chip (hidden once the task is ticked). It opens a sheet
with up to three vendors from the couple's city in that category - claimed and verified first, then by
score, preferring vendors who have not marked the wedding date unavailable - with From $, Verified and
Free-on-your-date chips; tap one for the usual vendor sheet (message, page, save); "See all" opens Browse
on that category. One Firestore query per category, cached for the session. If the plan already says
that category is booked, the chip says so and stays out of the way. No rules or worker changes.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Couple_master_v177.txt"
DST = HERE / "Couple_master_v178.txt"
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
    "// Build ID: JC-LAZO-PICKS-1019-COUPLE (v178: THREE PICKS IN THE CHECKLIST - every book/hire task that maps to a "
    "Lazo category gets a chip that opens three vendors from your city (claimed + verified first, free on your date "
    "preferred), tap for the vendor sheet, See all opens Browse; hidden once ticked or booked; base v177)\n"
) + s[first_build:]

rep("              _checklistRow(d, now),", "              _checklistRow(d, now, couple), // v178")
rep("  Widget _checklistRow(QueryDocumentSnapshot<Map<String, dynamic>> d, DateTime now) {",
    "  Widget _checklistRow(QueryDocumentSnapshot<Map<String, dynamic>> d, DateTime now, Map<String, dynamic> couple) {")
rep("""              if (due != null)
                Text(late ? 'Was due ${_shortDate(due)}' : 'By ${_shortDate(due)}${due.year != now.year ? ' ${due.year}' : ''}',
                    style: TextStyle(fontSize: 11.5, color: _lzFg(late ? const Color(0xFFB04A4A) : muted))),
            ]),""", """              if (due != null)
                Text(late ? 'Was due ${_shortDate(due)}' : 'By ${_shortDate(due)}${due.year != now.year ? ' ${due.year}' : ''}',
                    style: TextStyle(fontSize: 11.5, color: _lzFg(late ? const Color(0xFFB04A4A) : muted))),
              // v178: three picks for the task, right where the task is
              if (!done && _pickCatFor((m['title'] ?? '').toString()) != null)
                Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: _picksChip(_pickCatFor((m['title'] ?? '').toString())!, couple),
                ),
            ]),""")

HELPERS = r"""  // ---- v178: three picks inside the checklist task -------------------------------------
  static const List<List<String>> _kPickWords = <List<String>>[
    <String>['venue', 'wedding-venues'], <String>['planner', 'wedding-planners'], <String>['coordinator', 'day-of-coordination'],
    <String>['photograph', 'wedding-photographers'], <String>['engagement photos', 'wedding-photographers'],
    <String>['videograph', 'wedding-videographers'], <String>['caterer', 'wedding-caterers'], <String>['menu', 'wedding-caterers'],
    <String>['dj', 'wedding-djs'], <String>['band', 'wedding-bands'], <String>['florist', 'wedding-florists'],
    <String>['officiant', 'wedding-officiants'], <String>['hair and makeup', 'hair-and-makeup'],
    <String>['invitations', 'wedding-invitations'], <String>['transportation', 'wedding-transportation'],
    <String>['cake', 'wedding-cakes'], <String>['rentals', 'wedding-rentals'],
  ];
  final Map<String, List<Map<String, dynamic>>> _picksCache = <String, List<Map<String, dynamic>>>{};

  String? _pickCatFor(String title) {
    final String t = title.toLowerCase().trim();
    if (t.contains('wedding bands') || t.contains('rehearsal')) return null; // rings, not musicians
    const List<String> starts = <String>['book', 'hire', 'order invitations', 'cake', 'rentals', 'engagement', 'finalize the menu', 'tour'];
    if (!starts.any((String p) => t.startsWith(p))) return null;
    for (final List<String> w in _kPickWords) {
      if (t.contains(w[0])) return w[1];
    }
    return null;
  }

  String _pickLabel(String cat) {
    for (final Map<String, String> c in kCategories) {
      if (c['slug'] == cat) return (c['label'] ?? cat).toLowerCase();
    }
    return 'vendor';
  }

  bool _pickBusy(Map<String, dynamic> v, Map<String, dynamic> couple) {
    final dynamic wd = couple['weddingDate'];
    if (wd is! Timestamp) return false;
    final DateTime d = wd.toDate();
    final String ymd = '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
    final List<dynamic> busy = v['unavailableDates'] is List ? v['unavailableDates'] as List : const <dynamic>[];
    return busy.contains(ymd);
  }

  Widget _picksChip(String cat, Map<String, dynamic> couple) {
    return Align(
      alignment: Alignment.centerLeft,
      child: ActionChip(
        avatar: Icon(Icons.auto_awesome_rounded, size: 14, color: _lzFg(plum)),
        label: Text('Three ${_pickLabel(cat)} picks',
            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: _lzFg(plum))),
        backgroundColor: _lzBg(ivory),
        side: BorderSide(color: gold.withOpacity(.6)),
        visualDensity: VisualDensity.compact,
        onPressed: () => _picksSheet(cat, couple),
      ),
    );
  }

  Future<List<Map<String, dynamic>>> _picksLoad(String cat, Map<String, dynamic> couple) async {
    final String metro = (couple['metroId'] ?? '').toString();
    final String key = '$metro|$cat';
    final List<Map<String, dynamic>>? hit = _picksCache[key];
    if (hit != null) return hit;
    final QuerySnapshot<Map<String, dynamic>> snap = await FirebaseFirestore.instance
        .collection('vendors')
        .where('metroId', isEqualTo: metro)
        .where('categories', arrayContains: cat)
        .limit(60)
        .get();
    final List<Map<String, dynamic>> all = <Map<String, dynamic>>[
      for (final QueryDocumentSnapshot<Map<String, dynamic>> d in snap.docs)
        if (d.data()['delisted'] != true) (d.data()..['id'] = d.id),
    ];
    int rank(Map<String, dynamic> v) =>
        (v['claimStatus'] == 'claimed' ? 1000 : 0) + (v['verified'] == true ? 500 : 0) + ((v['score'] ?? 0) as num).toInt();
    all.sort((Map<String, dynamic> a, Map<String, dynamic> b) => rank(b).compareTo(rank(a)));
    final List<Map<String, dynamic>> free =
        all.where((Map<String, dynamic> v) => !_pickBusy(v, couple)).toList();
    final List<Map<String, dynamic>> out = (free.length >= 3 ? free : all).take(3).toList();
    _picksCache[key] = out;
    return out;
  }

  Future<void> _picksSheet(String cat, Map<String, dynamic> couple) async {
    final String metro = (couple['metroId'] ?? '').toString();
    final String label = _pickLabel(cat);
    if (metro.isEmpty) {
      _toastC('Set your city first — it’s in Account.');
      return;
    }
    bool booked = false;
    try {
      final DocumentSnapshot<Map<String, dynamic>> p = await _planRef.doc(cat).get();
      booked = (p.data()?['status'] ?? '') == 'booked';
    } catch (_) {}
    if (booked) {
      _toastC('You already booked your $label — it’s on your Vendor team.');
      return;
    }
    List<Map<String, dynamic>> picks = <Map<String, dynamic>>[];
    try {
      picks = await _picksLoad(cat, couple);
    } catch (_) {}
    if (!mounted) return;
    final bool dateKnown = couple['weddingDate'] is Timestamp;
    final String city = _tc(metro.replaceAll('-', ' '));
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext ctx) => _lzFrame(ctx,
          icon: Icons.auto_awesome_rounded,
          title: 'Three $label picks',
          subtitle: picks.isEmpty
              ? 'Nobody in $city is listed for this yet. Browse shows the nearest.'
              : 'In $city, claimed and verified first${dateKnown ? ', free on your date where we know it' : ''}. Tap one to read more or message them.',
          children: <Widget>[
            const SizedBox(height: 12),
            for (final Map<String, dynamic> v in picks)
              Builder(builder: (BuildContext bc) {
                final num? from = _startingPriceOf(v);
                final bool verified = v['verified'] == true;
                final bool free = dateKnown && !_pickBusy(v, couple);
                return _Press(
                  scale: .99,
                  onTap: () {
                    Navigator.pop(ctx);
                    _vendorSheet(v);
                  },
                  child: Container(
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.fromLTRB(14, 12, 12, 12),
                    decoration: BoxDecoration(
                      color: _lzBg(Colors.white.withOpacity(.9)),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: _lzLine(gold.withOpacity(.6))),
                    ),
                    child: Row(children: <Widget>[
                      Expanded(
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                          Text((v['name'] ?? 'Vendor').toString(),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(fontSize: 14.5, fontWeight: FontWeight.w800, color: _lzFg(plum))),
                          const SizedBox(height: 4),
                          Wrap(spacing: 6, runSpacing: 4, crossAxisAlignment: WrapCrossAlignment.center, children: <Widget>[
                            if (from != null)
                              Text('From ${_money(from)}',
                                  style: TextStyle(color: _lzFg(const Color(0xFF8A6A2F)), fontSize: 12.5, fontWeight: FontWeight.w800)),
                            if (verified)
                              Text('✦ Verified', style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700, color: _lzFg(plum))),
                            if (free)
                              Text('Free on your date', style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700, color: _lzFg(vGreen))),
                            if (((v['rating'] ?? 0) as num) > 0)
                              Text('★ ${((v['rating'] ?? 0) as num).toStringAsFixed(1)}',
                                  style: TextStyle(fontSize: 11.5, color: _lzFg(muted))),
                          ]),
                        ]),
                      ),
                      Icon(Icons.chevron_right_rounded, color: _lzFg(muted)),
                    ]),
                  ),
                );
              }),
            const SizedBox(height: 6),
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton.icon(
                onPressed: () {
                  Navigator.pop(ctx);
                  _openBrowse(category: cat, metro: metro);
                },
                icon: const Icon(Icons.search_rounded, size: 16),
                label: Text(picks.isEmpty ? 'Open Browse' : 'See every $label in $city'),
                style: TextButton.styleFrom(foregroundColor: _lzFg(plum)),
              ),
            ),
          ]),
    );
  }

"""
rep("  // ---- invitations\n  String _siteUrl(String slug)", HELPERS + "  // ---- invitations\n  String _siteUrl(String slug)")

if crlf:
    s = s.replace("\n", "\r\n")
DST.write_text(s, encoding="utf-8")
print("wrote", DST, len(s.splitlines()), "lines")
