"""patch_couple_v140.py - JC-LAZO-COUPLE-0929-V140
The four items left open by the review:
  1. BROWSE, RANKED. A second query - the top 24 by score for the metro and
     category (composite index metroId / categories / score, deployed with
     firestore.indexes.json) - merges into the unordered 60, so a big metro's
     best vendors always appear. The team card's "talking" count reads
     structuredIntent.category like everything else.
  2. MONEY FLOWS. Paid invoices write plan/{category}.paid.{inquiryId} = paid
     total the moment the thread sees them; accepted proposals write
     plan/{category}.quoted.{inquiryId} = price and fill an empty planned
     figure; "spent" everywhere is max(typed amount, paid on Lazo), so nothing
     double counts and a typed figure still wins. Accept asks first.
  3. DEAD CODE WIRED OR GONE. The v91 team card (road to the date, lead
     months, recommendations) heads the Vendor team screen using the live
     inquiries list; the Saved tile opens a sheet with the saved-vendors card
     (Browse when empty); _messagesPreview, _budgetMini, _browseCardTile and
     _seedStarterTimeline are removed.
  4. THE WEBSITE EDITOR. A jump bar of section chips at the top scrolls to
     any of its sections; tapping outside no longer discards edits; Cancel
     asks before throwing work away.
Applies on top of Couple_master_v139.txt -> Couple_master_v140.txt.
  python app-patches\\patch_couple_v140.py [src] [out]
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Couple_master_v139.txt"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "Couple_master_v140.txt"
s = SRC.read_text(encoding="utf-8")
if "JC-LAZO-COUPLE-0929-V140" in s:
    raise SystemExit("already applied")


def swap(old, new, label, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"ABORT [{label}]: anchor matched {n} times, expected {count}")
    s = s.replace(old, new)
    print(f"  ok  {label}")


def remove_method(signature, label):
    """Delete a method whose declaration starts with `signature` (at two-space
    indent) through its matching closing brace. Aborts if the brace walk does
    not end on a lone `  }` line."""
    global s
    start = s.find("\n" + signature)
    if start < 0:
        raise SystemExit(f"ABORT [{label}]: not found")
    start += 1
    i = s.find("{", start)
    depth = 0
    j = i
    in_str = None
    while j < len(s):
        ch = s[j]
        if in_str:
            if ch == "\\":
                j += 2
                continue
            if ch == in_str:
                in_str = None
        elif ch in ("'", '"'):
            in_str = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
        j += 1
    end = s.find("\n", j) + 1
    block = s[start:end]
    if not block.rstrip("\n").endswith("\n  }"):
        raise SystemExit(f"ABORT [{label}]: brace walk ended badly: {block[-80:]!r}")
    # swallow one blank line after it
    if s[end:end + 1] == "\n":
        end += 1
    s = s[:start] + s[end:]
    print(f"  ok  {label} ({block.count(chr(10))} lines removed)")


swap("// (v139: THE REVIEW",
     "// (v140: THE OPEN ITEMS - Browse merges the top-24-by-score query (composite index) into the unordered 60 so the best vendors always show; paid invoices and accepted proposals flow into the plan (paid.{inquiryId} / quoted.{inquiryId}; spent = max(typed, paid on Lazo)); Accept proposal asks first; the v91 team card heads the Vendor team screen; the Saved tile opens the saved-vendors sheet; four dead widgets removed; the website editor gets a section jump bar, is modal, and Cancel asks before discarding. JC-LAZO-COUPLE-0929-V140; base v139)\n// (v139: THE REVIEW",
     "header")

# ---------------------------------------------------------------- 1. browse ranked
swap("""  StreamSubscription<QuerySnapshot<Map<String, dynamic>>>? _inqSub;
""", """  // v140: the top of the ranking for the current metro + category, fetched
  // once per pair and merged into the unordered page so the best vendors
  // are never the ones the 60-limit dropped. Needs the composite index
  // vendors(metroId, categories contains, score desc); without it the
  // query fails quietly and Browse behaves as before.
  final Map<String, List<QueryDocumentSnapshot<Map<String, dynamic>>>>
      _topScored = <String, List<QueryDocumentSnapshot<Map<String, dynamic>>>>{};
  final Set<String> _topScoredBusy = <String>{};

  void _ensureTopScored(String metro, String cat) {
    final String key = '$metro|$cat';
    if (metro.isEmpty ||
        cat.isEmpty ||
        _topScored.containsKey(key) ||
        _topScoredBusy.contains(key)) {
      return;
    }
    _topScoredBusy.add(key);
    FirebaseFirestore.instance
        .collection('vendors')
        .where('metroId', isEqualTo: metro)
        .where('categories', arrayContains: cat)
        .orderBy('score', descending: true)
        .limit(24)
        .get()
        .then((QuerySnapshot<Map<String, dynamic>> q) {
      _topScored[key] = q.docs;
      _topScoredBusy.remove(key);
      if (mounted) setState(() {});
    }).catchError((Object e) {
      _topScored[key] = <QueryDocumentSnapshot<Map<String, dynamic>>>[];
      _topScoredBusy.remove(key);
      debugPrint('LAZO top-scored: ' + e.toString());
    });
  }

  StreamSubscription<QuerySnapshot<Map<String, dynamic>>>? _inqSub;
""", "browse: top-scored fetch")
swap("""                    final docs = [
                      ...(snap.data?.docs ??
                          <QueryDocumentSnapshot<Map<String, dynamic>>>[])
                    ];
                    docs.sort((a, b) {
                      final sa = ((a.data()['score'] ?? 0) as num).toDouble();
                      final sb = ((b.data()['score'] ?? 0) as num).toDouble();
                      return sb.compareTo(sa);
                    });
""", """                    _ensureTopScored(_browseMetro, _browseCat);
                    final Set<String> seenIds = <String>{};
                    final docs = <QueryDocumentSnapshot<Map<String, dynamic>>>[
                      for (final QueryDocumentSnapshot<Map<String, dynamic>> d
                          in <QueryDocumentSnapshot<Map<String, dynamic>>>[
                        ...(_topScored['$_browseMetro|$_browseCat'] ??
                            <QueryDocumentSnapshot<Map<String, dynamic>>>[]),
                        ...(snap.data?.docs ??
                            <QueryDocumentSnapshot<Map<String, dynamic>>>[]),
                      ])
                        if (seenIds.add(d.id)) d
                    ];
                    docs.sort((a, b) {
                      final sa = ((a.data()['score'] ?? 0) as num).toDouble();
                      final sb = ((b.data()['score'] ?? 0) as num).toDouble();
                      return sb.compareTo(sa);
                    });
""", "browse: merge top-scored")
swap("""      final dynamic cat = m['vendorCategory'] ?? m['category'];
      if (cat != null)
        talking[cat.toString()] = (talking[cat.toString()] ?? 0) + 1;
""", """      final dynamic cat = m['vendorCategory'] ??
          m['category'] ??
          (m['structuredIntent'] is Map
              ? (m['structuredIntent'] as Map)['category']
              : null);
      if (cat != null)
        talking[cat.toString()] = (talking[cat.toString()] ?? 0) + 1;
""", "team card: talking count reads structuredIntent")

# ---------------------------------------------------------------- 2. money flows
swap("""  Widget _coupleInvoices(String inquiryId, String vendorName) {
    return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
""", """  // v140: money flows into the plan. spent = max(what the couple typed,
  // what was paid on Lazo) - a typed figure still wins, nothing double
  // counts, and a paid invoice shows up without anyone retyping it.
  static num _spentOf(Map<String, dynamic> p) {
    final num typed = (p['budgetActual'] as num?) ?? 0;
    num paid = 0;
    if (p['paid'] is Map) {
      for (final dynamic v in (p['paid'] as Map).values) {
        if (v is num) paid += v;
      }
    }
    return typed > paid ? typed : paid;
  }

  String _inqCategory(String inquiryId) {
    for (final QueryDocumentSnapshot<Map<String, dynamic>> d in _inqDocs) {
      if (d.id != inquiryId) continue;
      final Map<String, dynamic> m = d.data();
      final dynamic si = m['structuredIntent'];
      final String c = (m['vendorCategory'] ??
              m['category'] ??
              (si is Map ? si['category'] : null) ??
              '')
          .toString();
      return c;
    }
    return '';
  }

  final Map<String, num> _paidNoted = <String, num>{};
  void _notePaid(String inquiryId, num paidSum) {
    if (_paidNoted[inquiryId] == paidSum) return;
    _paidNoted[inquiryId] = paidSum;
    final String cat = _inqCategory(inquiryId);
    if (cat.isEmpty) return;
    _planRef.doc(cat).set(<String, dynamic>{
      'paid': <String, dynamic>{inquiryId: paidSum},
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true)).catchError((Object e) {
      debugPrint('LAZO paid note: ' + e.toString());
    });
  }

  Future<void> _noteQuoted(String inquiryId, num price) async {
    final String cat = _inqCategory(inquiryId);
    if (cat.isEmpty || price <= 0) return;
    try {
      final DocumentSnapshot<Map<String, dynamic>> pd =
          await _planRef.doc(cat).get();
      final num planned = (pd.data()?['budgetPlanned'] as num?) ?? 0;
      await _planRef.doc(cat).set(<String, dynamic>{
        'quoted': <String, dynamic>{inquiryId: price},
        if (planned <= 0) 'budgetPlanned': price,
        'updatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));
    } catch (e) {
      debugPrint('LAZO quoted note: ' + e.toString());
    }
  }

  Widget _coupleInvoices(String inquiryId, String vendorName) {
    return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
""", "money: helpers")
swap("""            (s.data?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[])
                .where((QueryDocumentSnapshot<Map<String, dynamic>> d) =>
                    (d.data()['status'] ?? '') != 'void')
                .toList();
        if (docs.isEmpty) {
          return const SizedBox.shrink();
        }
        return Column(
          children: docs.map((QueryDocumentSnapshot<Map<String, dynamic>> d) {
            final Map<String, dynamic> inv = d.data();
            final bool paid = (inv['status'] ?? '') == 'paid';
""", """            (s.data?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[])
                .where((QueryDocumentSnapshot<Map<String, dynamic>> d) =>
                    (d.data()['status'] ?? '') != 'void')
                .toList();
        if (s.hasData) {
          // v140: what has been paid here lands on the plan
          num paidSum = 0;
          for (final QueryDocumentSnapshot<Map<String, dynamic>> d in docs) {
            if ((d.data()['status'] ?? '') == 'paid') {
              paidSum += (d.data()['total'] as num?) ?? 0;
            }
          }
          _notePaid(inquiryId, paidSum);
        }
        if (docs.isEmpty) {
          return const SizedBox.shrink();
        }
        return Column(
          children: docs.map((QueryDocumentSnapshot<Map<String, dynamic>> d) {
            final Map<String, dynamic> inv = d.data();
            final bool paid = (inv['status'] ?? '') == 'paid';
""", "money: paid invoices noted")
swap("""                          onPressed: _h(() async {
                            await d.reference.update(<String, dynamic>{
                              'status': 'accepted',
                              'respondedAt': FieldValue.serverTimestamp()
                            });
                          }, _Tick.medium),
                          child: const Text('Accept proposal',
""", """                          onPressed: _h(() async {
                            // v140: ask first, then let the price reach the plan
                            final num price = (p['price'] as num?) ?? 0;
                            final bool? sure = await showDialog<bool>(
                              context: context,
                              builder: (BuildContext dc) => AlertDialog(
                                backgroundColor: ivory,
                                title: const Text('Accept this proposal?',
                                    style: TextStyle(color: plum)),
                                content: Text(
                                    price > 0
                                        ? '${_money(price)} from $vendorName. It becomes this category\\u2019s planned figure if you haven\\u2019t set one.'
                                        : 'You\\u2019re telling $vendorName yes.',
                                    style: const TextStyle(
                                        color: ink, fontSize: 14)),
                                actions: <Widget>[
                                  TextButton(
                                      onPressed: () => Navigator.pop(dc, false),
                                      child: const Text('Not yet',
                                          style: TextStyle(color: ink))),
                                  FilledButton(
                                      style: FilledButton.styleFrom(
                                          backgroundColor: gold,
                                          foregroundColor: plumDeep),
                                      onPressed: () => Navigator.pop(dc, true),
                                      child: const Text('Accept')),
                                ],
                              ),
                            );
                            if (sure != true) {
                              return;
                            }
                            await d.reference.update(<String, dynamic>{
                              'status': 'accepted',
                              'respondedAt': FieldValue.serverTimestamp()
                            });
                            await _noteQuoted(inquiryId, price);
                          }, _Tick.medium),
                          child: const Text('Accept proposal',
""", "money: accept asks + quoted")
swap("""      final num s = (p['budgetActual'] as num?) ?? 0;
      final num pl = (p['budgetPlanned'] as num?) ?? 0;
      spent += s;
""", """      final num s = _spentOf(p); // v140: typed or paid on Lazo
      final num pl = (p['budgetPlanned'] as num?) ?? 0;
      spent += s;
""", "money: budget card spent")
swap("""              final num sp = (p['budgetActual'] as num?) ?? 0;
""", """              final num sp = _spentOf(p); // v140
""", "money: allocation spent")
swap("""        committed += ((p['budgetActual'] ?? 0) as num).toDouble();
""", """        committed += _spentOf(p).toDouble(); // v140
""", "money: committed", count=3)

# ---------------------------------------------------------------- 3. dead code: wire or remove
swap("""    final metroId = (couple['metroId'] as String?) ?? _browseMetro;
    return ListView(
      padding: const EdgeInsets.fromLTRB(18, 8, 18, 32),
      children: [
        _subHeader('Vendor team'),
        ...kCategories.map((c) {
""", """    final metroId = (couple['metroId'] as String?) ?? _browseMetro;
    // v140: the v91 team card (road to the date, booking-lead months,
    // recommendations) finally heads the screen, on the live inquiries
    final DateTime? teamWedding = couple['weddingDate'] is Timestamp
        ? (couple['weddingDate'] as Timestamp).toDate()
        : null;
    return ListView(
      padding: const EdgeInsets.fromLTRB(18, 8, 18, 32),
      children: [
        _subHeader('Vendor team'),
        _teamCard(couple, plan, _inqDocs, teamWedding),
        const SizedBox(height: 14),
        const Padding(
          padding: EdgeInsets.only(left: 6, bottom: 8),
          child: Text('Every category',
              style: TextStyle(
                  color: plum, fontSize: 15.5, fontWeight: FontWeight.w700)),
        ),
        ...kCategories.map((c) {
""", "team card: wired")
swap("""        'Saved vendors',
        saved == 0 ? 'None saved' : '$saved saved',
        saved == 0 ? 'Tap the heart on any vendor' : 'Check their dates',
        () => setState(() => _view = _View.browse),
""", """        'Saved vendors',
        saved == 0 ? 'None saved' : '$saved saved',
        saved == 0 ? 'Tap the heart on any vendor' : 'Check their dates',
        () => saved == 0
            ? setState(() => _view = _View.browse)
            : showModalBottomSheet<void>(
                context: context,
                backgroundColor: ivory,
                isScrollControlled: true,
                constraints: const BoxConstraints(maxWidth: 640),
                shape: const RoundedRectangleBorder(
                    borderRadius:
                        BorderRadius.vertical(top: Radius.circular(26))),
                builder: (BuildContext ctx) => SafeArea(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.fromLTRB(18, 18, 18, 22),
                    child: _savedCard(couple),
                  ),
                ),
              ),
""", "saved tile: opens the saved card")
remove_method("  Widget _messagesPreview(", "remove _messagesPreview")
remove_method("  Widget _budgetMini(", "remove _budgetMini")
remove_method("  Widget _browseCardTile(", "remove _browseCardTile")
remove_method("  Future<void> _seedStarterTimeline(", "remove _seedStarterTimeline")

# ---------------------------------------------------------------- 4. the editor
swap("""  Widget _wbSection(String label) {
    return Padding(
      padding: const EdgeInsets.only(top: 16, bottom: 8),
      child: Row(children: <Widget>[
""", """  // v140: every section registers a key so the jump bar can scroll to it
  final Map<String, GlobalKey> _wbKeys = <String, GlobalKey>{};
  bool _wbJumpArmed = false;

  Widget _wbJumpBar(StateSetter setD) {
    if (_wbKeys.isEmpty) {
      if (!_wbJumpArmed) {
        _wbJumpArmed = true;
        WidgetsBinding.instance.addPostFrameCallback((_) {
          try {
            setD(() {});
          } catch (_) {}
        });
      }
      return const SizedBox(height: 4);
    }
    return SizedBox(
      height: 36,
      child: ListView(
        scrollDirection: Axis.horizontal,
        children: _wbKeys.entries.map((MapEntry<String, GlobalKey> e) {
          final String label = e.key.contains(' \\u00b7 ')
              ? e.key.split(' \\u00b7 ').first
              : e.key;
          return Padding(
            padding: const EdgeInsets.only(right: 6),
            child: ActionChip(
              label: Text(
                  label[0] + label.substring(1).toLowerCase(),
                  style: const TextStyle(
                      color: plum, fontSize: 11.5, fontWeight: FontWeight.w700)),
              backgroundColor: gold.withOpacity(.16),
              side: BorderSide(color: gold.withOpacity(.5)),
              padding: const EdgeInsets.symmetric(horizontal: 8),
              onPressed: () {
                HapticFeedback.selectionClick();
                final BuildContext? c = e.value.currentContext;
                if (c != null) {
                  Scrollable.ensureVisible(c,
                      duration: const Duration(milliseconds: 320),
                      alignment: 0.02,
                      curve: Curves.easeOutCubic);
                }
              },
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _wbSection(String label) {
    final GlobalKey k = _wbKeys.putIfAbsent(label, () => GlobalKey());
    return Padding(
      key: k,
      padding: const EdgeInsets.only(top: 16, bottom: 8),
      child: Row(children: <Widget>[
""", "editor: jump bar + keyed sections")
swap("""    final bool? ok = await showDialog<bool>(
      context: context,
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) => Dialog(
          backgroundColor: ivory,
          insetPadding:
              const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
""", """    _wbKeys.clear();
    _wbJumpArmed = false;
    final bool? ok = await showDialog<bool>(
      context: context,
      barrierDismissible: false, // v140: a tap outside no longer discards edits
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) => Dialog(
          backgroundColor: ivory,
          insetPadding:
              const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
""", "editor: modal + keys reset")
swap("""                  const Text('Your wedding website',
                      style: TextStyle(
                          color: plum,
                          fontWeight: FontWeight.w700,
                          fontSize: 17)),
                  const SizedBox(height: 6),
                  Flexible(
""", """                  const Text('Your wedding website',
                      style: TextStyle(
                          color: plum,
                          fontWeight: FontWeight.w700,
                          fontSize: 17)),
                  const SizedBox(height: 6),
                  _wbJumpBar(setD),
                  const SizedBox(height: 4),
                  Flexible(
""", "editor: jump bar placed")
swap("""                      TextButton(
                          onPressed: _h(() => Navigator.pop(ctx2, false)),
                          child: const Text('Cancel',
                              style: TextStyle(color: ink))),
                      const SizedBox(width: 6),
                      FilledButton(
                        style: FilledButton.styleFrom(
                            backgroundColor: gold, foregroundColor: plum),
                        onPressed:
                            _h(() => Navigator.pop(ctx2, true), _Tick.medium),
                        child: const Text('Publish'),
""", """                      TextButton(
                          onPressed: _h(() async {
                            // v140: ask before throwing the edits away
                            final bool? sure = await showDialog<bool>(
                              context: ctx2,
                              builder: (BuildContext dc) => AlertDialog(
                                backgroundColor: ivory,
                                title: const Text('Discard your changes?',
                                    style: TextStyle(color: plum)),
                                content: const Text(
                                    'Anything you changed here is lost. Publish keeps it.',
                                    style: TextStyle(color: ink, fontSize: 14)),
                                actions: <Widget>[
                                  TextButton(
                                      onPressed: () => Navigator.pop(dc, false),
                                      child: const Text('Keep editing',
                                          style: TextStyle(color: ink))),
                                  FilledButton(
                                      style: FilledButton.styleFrom(
                                          backgroundColor: rose,
                                          foregroundColor: ivory),
                                      onPressed: () => Navigator.pop(dc, true),
                                      child: const Text('Discard')),
                                ],
                              ),
                            );
                            if (sure == true && ctx2.mounted) {
                              Navigator.pop(ctx2, false);
                            }
                          }),
                          child: const Text('Cancel',
                              style: TextStyle(color: ink))),
                      const SizedBox(width: 6),
                      FilledButton(
                        style: FilledButton.styleFrom(
                            backgroundColor: gold, foregroundColor: plum),
                        onPressed:
                            _h(() => Navigator.pop(ctx2, true), _Tick.medium),
                        child: const Text('Publish'),
""", "editor: cancel asks")

OUT.write_text(s, encoding="utf-8", newline="\n")
print(f"wrote {OUT.name} ({len(s):,} chars)")
