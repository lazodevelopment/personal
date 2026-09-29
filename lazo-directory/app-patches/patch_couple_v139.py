"""patch_couple_v139.py - JC-LAZO-COUPLE-0929-V139
THE REVIEW - fixes from the 2026-09-29 read of the whole widget.
Data loss and corruption:
  1. Setup sheet no longer rewrites every category (a booked photographer
     flipped back to "needed" on reopen) and never blanks the names.
  2. Inquiries file under the VENDOR's category, not the Browse dropdown.
  3. Guest CSV import prefers First + Last columns over a column that merely
     contains "name", and de-dupes inside the file.
  4. Dream board: a dirty flag keeps the cached remote snapshot from reverting
     a pin or comment before the debounced save.
  5. New site slugs are checked for collisions (sarah-mike-2); publish errors
     are surfaced; trailing hyphens are stripped (the old regex matched "-$").
  6. RSVP import only writes meal / plus-ones when the reply gave them.
  7. Date pickers open after the wedding (firstDate never after initialDate).
  8. The tour and the notification ask are per partner (tourDoneBy,
     pushAsk.{uid}); a joining partner gets both.
  9. Partner invite reachable on phones (Account row -> sheet).
 10. Timeline sorts past midnight (01:10 send-off after 11:30 dancing);
     "Guests arrive" no longer filtered off the guest timeline.
Structure:
 11. Budget sheet rows close the sheet before switching screens; tip chips
     redraw inside the thread sheet (local StatefulBuilder).
 12. Weather stops refetching on every build after an error (10-minute
     back-off).
 13. Messages list sorts by latest activity and shows Said hello / Went
     another direction states.
Additions:
 14. Post-wedding June steps (thank-yous, chapters, photos).
 15. Notifications row in Account (re-ask any time).
 16. Chapters: list, edit, delete (the Add button opens the list).
 17. Guest search covers email, table and meal; delete asks first and removes
     the invite doc.
 18. Registry: tapping a store icon prefills that store; links are editable.
Text: "1 days", "hair & makeups", "0 months out", the dead ternary, the
literal \\u2713 in two toasts, "issued by the .", "Date removed" on a moment.
Applies on top of Couple_master_v138.txt -> Couple_master_v139.txt.
  python app-patches\\patch_couple_v139.py [src] [out]
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Couple_master_v138.txt"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "Couple_master_v139.txt"
s = SRC.read_text(encoding="utf-8")
if "JC-LAZO-COUPLE-0929-V139" in s:
    raise SystemExit("already applied")


def swap(old, new, label, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"ABORT [{label}]: anchor matched {n} times, expected {count}")
    s = s.replace(old, new)
    print(f"  ok  {label}")


swap("// (v138: MORE FOR THE SITE",
     "// (v139: THE REVIEW - setup no longer un-books vendors or blanks names; inquiries file under the vendor's own category; Knot/Zola CSV import reads First + Last and de-dupes; the dream board keeps pins through the save; site slugs check for collisions and publish errors surface; RSVP import keeps meal/plus-ones the couple typed; date pickers work after the wedding; tour and notification ask are per partner; partner invite on phones; timeline sorts past midnight; budget rows and tip chips work inside sheets; weather backs off after an error; messages sort by activity with hello/lost states; post-wedding June steps; Notifications in Account; chapters list/edit/delete; guest search by email/table/meal and delete-with-confirm; registry store prefill and editable links; text fixes. JC-LAZO-COUPLE-0929-V139; base v138)\n// (v138: MORE FOR THE SITE",
     "header")

# ---------------------------------------------------------------- 1. setup sheet
swap("""                                    await _coupleRef.set(<String, dynamic>{
                                      'names': namesC.text.trim(),
                                      if (metro.isNotEmpty) 'metroId': metro,
""", """                                    await _coupleRef.set(<String, dynamic>{
                                      if (namesC.text.trim().isNotEmpty)
                                        'names': namesC.text.trim(),
                                      if (metro.isNotEmpty) 'metroId': metro,
""", "setup: names only when typed")
swap("""                                    final WriteBatch wb =
                                        FirebaseFirestore.instance.batch();
                                    for (final Map<String, String> c
                                        in kCategories) {
                                      final String slug = c['slug'] ?? '';
                                      wb.set(
""", """                                    // v139: only categories with no plan
                                    // doc yet - reopening setup used to flip
                                    // a booked vendor back to "needed"
                                    final Set<String> hasPlan = <String>{};
                                    try {
                                      final QuerySnapshot<Map<String, dynamic>>
                                          pq = await _planRef.get();
                                      for (final QueryDocumentSnapshot<
                                              Map<String, dynamic>> pd
                                          in pq.docs) {
                                        if ((pd.data()['status'] ?? '')
                                            .toString()
                                            .isNotEmpty) {
                                          hasPlan.add(pd.id);
                                        }
                                      }
                                    } catch (_) {}
                                    final WriteBatch wb =
                                        FirebaseFirestore.instance.batch();
                                    for (final Map<String, String> c
                                        in kCategories) {
                                      final String slug = c['slug'] ?? '';
                                      if (hasPlan.contains(slug)) {
                                        continue;
                                      }
                                      wb.set(
""", "setup: never rewrite existing plan docs")

# ---------------------------------------------------------------- 2. inquiry category
swap("""  Future<void> _sendInquiry(Map<String, dynamic> v) async {
    final placeId = (v['placeId'] as String?) ?? '';
    final vendorName = (v['name'] as String?) ?? 'this vendor';
    if (placeId.isEmpty || _uid == null) return;
""", """  // v139: the vendor's own category (their doc carries `categories`), so an
  // inquiry from name search, Saved or a deep link marks the right row
  String _vendorCat(Map<String, dynamic> v) {
    final Set<String> known =
        kCategories.map((Map<String, String> c) => c['slug'] ?? '').toSet();
    final dynamic cs = v['categories'];
    if (cs is List) {
      if (cs.map((dynamic e) => e.toString()).contains(_browseCat)) {
        return _browseCat;
      }
      for (final dynamic e in cs) {
        if (known.contains(e.toString())) {
          return e.toString();
        }
      }
    }
    final String one = (v['category'] ?? '').toString();
    if (known.contains(one)) {
      return one;
    }
    return _browseCat;
  }

  Future<void> _sendInquiry(Map<String, dynamic> v) async {
    final placeId = (v['placeId'] as String?) ?? '';
    final vendorName = (v['name'] as String?) ?? 'this vendor';
    if (placeId.isEmpty || _uid == null) return;
    final String inqCat = _vendorCat(v);
""", "inquiry: vendor category helper")
swap("""        'metroId': _browseMetro,
        'category': _browseCat,
      },
    });
    // The list listens: inquiring marks the category researching, with who
    try {
      final DocumentSnapshot<Map<String, dynamic>> pd =
          await _planRef.doc(_browseCat).get();
      final String pst = (pd.data()?['status'] ?? 'needed') as String;
      if (pst != 'booked' && pst != 'skipped') {
        await _planRef.doc(_browseCat).set(<String, dynamic>{
""", """        'metroId': _browseMetro,
        'category': inqCat,
      },
    });
    // The list listens: inquiring marks the category researching, with who
    try {
      final DocumentSnapshot<Map<String, dynamic>> pd =
          await _planRef.doc(inqCat).get();
      final String pst = (pd.data()?['status'] ?? 'needed') as String;
      if (pst != 'booked' && pst != 'skipped') {
        await _planRef.doc(inqCat).set(<String, dynamic>{
""", "inquiry: file under the vendor's category")

# ---------------------------------------------------------------- 3. CSV import
swap("""      String name = iName >= 0 ? cell(r, iName) : '';
      if (name.isEmpty) name = ('${cell(r, iFirst)} ${cell(r, iLast)}').trim();
""", """      // v139: Knot and Zola exports carry First / Last; a column that only
      // CONTAINS "name" (First Name) used to win and drop every surname
      String name = (iFirst >= 0 || iLast >= 0)
          ? ('${cell(r, iFirst)} ${cell(r, iLast)}').trim()
          : '';
      if (name.isEmpty && iName >= 0) name = cell(r, iName);
""", "csv: first + last first")
swap("""        if (have.contains(g['name'].toString().toLowerCase())) continue;
        b.set(_coupleRef.collection('guests').doc(), g);
""", """        if (have.contains(g['name'].toString().toLowerCase())) continue;
        have.add(g['name'].toString().toLowerCase()); // v139: no dupes within the file
        b.set(_coupleRef.collection('guests').doc(), g);
""", "csv: de-dupe within the file")

# ---------------------------------------------------------------- 4. board dirty flag
swap("""  int _bdLocalRev =
      0; // bumps on every local change; remote snapshots older than our last save are ignored

  void _bdApplyRemote(Map<String, dynamic> d) {
    if (_bdDragging) return;
""", """  int _bdLocalRev =
      0; // bumps on every local change; remote snapshots older than our last save are ignored
  // v139: while a local change is waiting for its save, the cached remote
  // snapshot must not be re-applied - it reverted new pins and comments
  bool _bdDirty = false;

  void _bdApplyRemote(Map<String, dynamic> d) {
    if (_bdDragging || _bdDirty) return;
""", "board: apply guard")
swap("""  void _bdSave() {
    _bdSaveT?.cancel();
    _bdSaveT = Timer(const Duration(milliseconds: 500), () async {
      try {
        await _boardRef.set(<String, dynamic>{
          'items': _bdItems,
          'updatedAt': FieldValue.serverTimestamp(),
        }, SetOptions(merge: true));
      } catch (e) {
        _toast('Could not save the board: ' + e.toString());
      }
""", """  void _bdSave() {
    _bdDirty = true;
    _bdLocalRev++;
    _bdSaveT?.cancel();
    _bdSaveT = Timer(const Duration(milliseconds: 500), () async {
      try {
        await _boardRef.set(<String, dynamic>{
          'items': _bdItems,
          'updatedAt': FieldValue.serverTimestamp(),
        }, SetOptions(merge: true));
      } catch (e) {
        _toast('Could not save the board: ' + e.toString());
      } finally {
        _bdDirty = false;
      }
""", "board: dirty flag around the save")

# ---------------------------------------------------------------- 5. slug + publish errors
swap("""    sl = sl.replaceAll(RegExp(r'^-|-\\$'), '');
    return sl.isEmpty ? 'our-wedding' : sl;
""", """    sl = sl.replaceAll(RegExp(r'^-+|-+$'), ''); // v139: was matching "-$"
    return sl.isEmpty ? 'our-wedding' : sl;
""", "slug: trailing hyphen")
swap("""    setState(() => _webBusy = true);
    try {
      final String slug = doc?.id ?? _slugFor(joinedNames());
""", """    setState(() => _webBusy = true);
    try {
      // v139: a new site takes the first free slug - two "Sarah & Mike"s
      // used to write over each other's page
      String slug = doc?.id ?? '';
      if (slug.isEmpty) {
        final String base = _slugFor(joinedNames());
        slug = base;
        for (int n = 2; n < 50; n++) {
          final DocumentSnapshot<Map<String, dynamic>> ex =
              await FirebaseFirestore.instance
                  .collection('weddingSites')
                  .doc(slug)
                  .get();
          if (!ex.exists || ex.data()?['coupleUid'] == _cid) {
            break;
          }
          slug = '$base-$n';
        }
      }
""", "slug: first free")
swap("""      // v137: the seating lookup and the DJ page read mirrored copies
      await _mirrorSeating(slug, seatingOn);
      await _mirrorPlaylist(slug);
      if (mounted) {
        _siteLiveShareSheet(joinedNames(), slug);
      }
    } finally {
""", """      // v137: the seating lookup and the DJ page read mirrored copies
      await _mirrorSeating(slug, seatingOn);
      await _mirrorPlaylist(slug);
      if (mounted) {
        _siteLiveShareSheet(joinedNames(), slug);
      }
    } catch (e) {
      // v139: a rules rejection used to vanish behind try/finally
      _toastC('Couldn\\u2019t publish \\u2014 ${e.toString().length > 90 ? e.toString().substring(0, 90) : e}');
    } finally {
""", "publish: surface errors")

# ---------------------------------------------------------------- 6. RSVP import keeps couple edits
swap("""      'rsvp': (r['attending'] ?? 'yes') == 'yes' ? 'yes' : 'no',
      'meal': (r['meal'] ?? '') as String,
      'plusOnes': ((r['plusOnes'] ?? 0) as num).toInt(),
      if ((r['song'] ?? '').toString().trim().isNotEmpty)
""", """      'rsvp': (r['attending'] ?? 'yes') == 'yes' ? 'yes' : 'no',
      // v139: a blank reply no longer wipes what the couple typed
      if ((r['meal'] ?? '').toString().trim().isNotEmpty)
        'meal': (r['meal'] ?? '').toString().trim(),
      if (r['plusOnes'] is num && (r['plusOnes'] as num) > 0)
        'plusOnes': (r['plusOnes'] as num).toInt(),
      if ((r['song'] ?? '').toString().trim().isNotEmpty)
""", "rsvp import: keep edits")

# ---------------------------------------------------------------- 7. date pickers after the wedding
swap("""      initialDate: current ?? DateTime.now().add(const Duration(days: 270)),
      firstDate: DateTime.now(),
""", """      initialDate: current ?? DateTime.now().add(const Duration(days: 270)),
      // v139: after the wedding the picker asserted (initial before first)
      firstDate: (current != null && current.isBefore(DateTime.now()))
          ? current
          : DateTime.now(),
""", "date picker: account")
swap("""                    initialDate:
                        date ?? DateTime.now().add(const Duration(days: 300)),
                    firstDate: DateTime.now(),
""", """                    initialDate:
                        date ?? DateTime.now().add(const Duration(days: 300)),
                    firstDate: (date != null && date!.isBefore(DateTime.now()))
                        ? date!
                        : DateTime.now(),
""", "date picker: setup")

# ---------------------------------------------------------------- 8. tour + push per partner
swap("""    if (couple.isEmpty) return;
    if (couple['tourDoneAt'] != null) {
      _tourChecked = true;
      return;
    }
""", """    if (couple.isEmpty) return;
    // v139: per partner - a joining partner gets the tour too. A legacy
    // tourDoneAt with no tourDoneBy counts for the plan's creator only.
    final List<dynamic> doneBy =
        couple['tourDoneBy'] is List ? couple['tourDoneBy'] as List : <dynamic>[];
    final bool doneForMe = doneBy.contains(_uid) ||
        (doneBy.isEmpty && couple['tourDoneAt'] != null && _uid == _cid);
    if (doneForMe) {
      _tourChecked = true;
      return;
    }
""", "tour: per partner check")
swap("""      await _coupleRef.set(<String, dynamic>{
        'tourDoneAt': FieldValue.serverTimestamp(),
        'tourCompleted': completed,
      }, SetOptions(merge: true));
""", """      await _coupleRef.set(<String, dynamic>{
        'tourDoneAt': FieldValue.serverTimestamp(),
        'tourCompleted': completed,
        'tourDoneBy': FieldValue.arrayUnion(<dynamic>[_uid]),
      }, SetOptions(merge: true));
""", "tour: per partner write")
swap("""  Future<void> _maybeAskPush() async {
    if (_uid == null) return;
    try {
      final DocumentSnapshot<Map<String, dynamic>> c = await _coupleRef.get();
      final Map<String, dynamic> d = c.data() ?? <String, dynamic>{};
      if ((d['pushAskAnswer'] ?? '') == 'yes') return;
      final dynamic asked = d['pushAskedAt'];
      if (asked is Timestamp &&
          DateTime.now().difference(asked.toDate()).inDays < 30) return;
    } catch (_) {
      return;
    }
""", """  Future<void> _maybeAskPush({bool force = false}) async {
    if (_uid == null) return;
    if (!force) {
      try {
        final DocumentSnapshot<Map<String, dynamic>> c = await _coupleRef.get();
        final Map<String, dynamic> d = c.data() ?? <String, dynamic>{};
        // v139: per partner (pushAsk.{uid}); the plan-wide fields only count
        // for the creator, so a joining partner's devices register too
        Map<String, dynamic> mine = <String, dynamic>{};
        if (d['pushAsk'] is Map && (d['pushAsk'] as Map)[_uid] is Map) {
          mine = Map<String, dynamic>.from((d['pushAsk'] as Map)[_uid] as Map);
        } else if (_uid == _cid) {
          mine = <String, dynamic>{
            'answer': d['pushAskAnswer'],
            'at': d['pushAskedAt']
          };
        }
        if ((mine['answer'] ?? '') == 'yes') return;
        final dynamic asked = mine['at'];
        if (asked is Timestamp &&
            DateTime.now().difference(asked.toDate()).inDays < 30) return;
      } catch (_) {
        return;
      }
    }
""", "push: per partner check + force")
swap("""      await _coupleRef.set(<String, dynamic>{
        'pushAskedAt': FieldValue.serverTimestamp(),
        'pushAskAnswer': answer,
      }, SetOptions(merge: true));
""", """      await _coupleRef.set(<String, dynamic>{
        'pushAskedAt': FieldValue.serverTimestamp(),
        'pushAskAnswer': answer,
        'pushAsk': <String, dynamic>{
          _uid!: <String, dynamic>{
            'answer': answer,
            'at': FieldValue.serverTimestamp()
          }
        },
      }, SetOptions(merge: true));
""", "push: per partner write")

# ---------------------------------------------------------------- 9 + 15. account rows: partner, notifications
swap("""        _accountGroup(label: 'MORE', rows: <Widget>[
""", """        _accountGroup(label: 'THE TWO OF YOU', rows: <Widget>[
          _accountRow(
            icon: Icons.favorite_border_rounded,
            title: 'Your partner',
            value: 'Invite them to the shared plan, or join theirs',
            onTap: () => showModalBottomSheet<void>(
              context: context,
              backgroundColor: ivory,
              isScrollControlled: true,
              constraints: const BoxConstraints(maxWidth: 560),
              shape: const RoundedRectangleBorder(
                  borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
              builder: (BuildContext ctx) => SafeArea(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(18, 18, 18, 22),
                  child: _partnerCard(couple),
                ),
              ),
            ),
          ),
          _accountRow(
            icon: Icons.notifications_active_outlined,
            title: 'Notifications',
            value: 'Know the moment a vendor writes back',
            onTap: () => _maybeAskPush(force: true),
          ),
        ]),
        _accountGroup(label: 'MORE', rows: <Widget>[
""", "account: partner + notifications rows")

# ---------------------------------------------------------------- 10. timeline past midnight; guest words
swap("""  static String _tlHm(int m) {
""", """  // v139: a moment before 4 am belongs to the night before, so the send-off
  // at 01:10 sorts after the dancing, not before the ceremony
  static int _tlSortKey(dynamic hhmm) {
    final List<String> p = hhmm.toString().split(':');
    final int m = p.length == 2
        ? (int.tryParse(p[0]) ?? 0) * 60 + (int.tryParse(p[1]) ?? 0)
        : 0;
    return m < 240 ? m + 1440 : m;
  }

  static void _tlSortDocs(
      List<QueryDocumentSnapshot<Map<String, dynamic>>> evs) {
    evs.sort((QueryDocumentSnapshot<Map<String, dynamic>> a,
            QueryDocumentSnapshot<Map<String, dynamic>> b) =>
        _tlSortKey(a.data()['time'] ?? '')
            .compareTo(_tlSortKey(b.data()['time'] ?? '')));
  }

  static String _tlHm(int m) {
""", "timeline: sort helpers")
swap("""              final List<QueryDocumentSnapshot<Map<String, dynamic>>> evs =
                  sn.data?.docs ??
                      <QueryDocumentSnapshot<Map<String, dynamic>>>[];
              return Column(children: <Widget>[
                Padding(
                  padding: const EdgeInsets.fromLTRB(22, 18, 14, 8),
""", """              final List<QueryDocumentSnapshot<Map<String, dynamic>>> evs =
                  <QueryDocumentSnapshot<Map<String, dynamic>>>[
                ...(sn.data?.docs ??
                    <QueryDocumentSnapshot<Map<String, dynamic>>>[])
              ];
              _tlSortDocs(evs);
              return Column(children: <Widget>[
                Padding(
                  padding: const EdgeInsets.fromLTRB(22, 18, 14, 8),
""", "timeline: builder sorts")
swap("""          stream: _dayofRef.orderBy('time').snapshots(),
          builder: (BuildContext c,
              AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> s) {
            final List<QueryDocumentSnapshot<Map<String, dynamic>>> evs =
                s.data?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[];
""", """          stream: _liveQuery('dayof:$_cid', () => _dayofRef.orderBy('time')),
          initialData: _liveQ['dayof:$_cid']?.latest,
          builder: (BuildContext c,
              AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> s) {
            final List<QueryDocumentSnapshot<Map<String, dynamic>>> evs =
                <QueryDocumentSnapshot<Map<String, dynamic>>>[
              ...(s.data?.docs ??
                  <QueryDocumentSnapshot<Map<String, dynamic>>>[])
            ];
            _tlSortDocs(evs);
""", "timeline: inline list sorts + shared stream")
swap("""      final QuerySnapshot<Map<String, dynamic>> evs =
          await _dayofRef.orderBy('time').get();
      for (final QueryDocumentSnapshot<Map<String, dynamic>> d in evs.docs) {
        final Map<String, dynamic> m = d.data();
        final String label = (m['label'] ?? '').toString().trim();
""", """      final QuerySnapshot<Map<String, dynamic>> evq =
          await _dayofRef.orderBy('time').get();
      final List<QueryDocumentSnapshot<Map<String, dynamic>>> evs =
          <QueryDocumentSnapshot<Map<String, dynamic>>>[...evq.docs];
      _tlSortDocs(evs);
      for (final QueryDocumentSnapshot<Map<String, dynamic>> d in evs) {
        final Map<String, dynamic> m = d.data();
        final String label = (m['label'] ?? '').toString().trim();
""", "timeline: guest mirror sorts")
swap("""    'arriv', 'load', 'setup', 'set-up', 'set up', 'vendor', 'deliver',
""", """    'photographer', 'videographer', 'dj arriv', 'band arriv', 'florist',
    'caterer', 'planner', 'load', 'setup', 'set-up', 'set up', 'vendor', 'deliver',
""", "guest timeline: keep 'Guests arrive'")

# ---------------------------------------------------------------- 11. sheets: budget rows, tip chips
swap("""              out.add(_Press(
                onTap: () => setState(() => _view = _View.vendors),
""", """              out.add(_Press(
                onTap: () {
                  // v139: the card lives in a sheet - close it first
                  Navigator.of(context).maybePop();
                  setState(() => _view = _View.vendors);
                },
""", "budget: rows close the sheet")
swap("""                Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
                  for (final num t in <num>[0, 25, 50, 100, 200])
                    _Press(
                      tick: _Tick.select,
                      onTap: () => setState(() => _tipFor[invoiceId] = t),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 11, vertical: 6),
                        decoration: BoxDecoration(
                            color: tip == t ? gold : Colors.transparent,
                            borderRadius: BorderRadius.circular(999),
                            border: Border.all(
                                color:
                                    tip == t ? gold : ivory.withOpacity(.5))),
                        child: Text(t == 0 ? 'No tip' : _money(t),
                            style: TextStyle(
                                color: tip == t ? plumDeep : ivory,
                                fontSize: 11.5,
                                fontWeight: FontWeight.w800)),
                      ),
                    ),
                ]),
""", """                // v139: the chips sit in a modal sheet, so the page's
                // setState never redrew them - a local builder does
                StatefulBuilder(builder: (BuildContext tc, StateSetter setT) {
                  final num tipNow = _tipFor[invoiceId] ?? 0;
                  return Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
                    for (final num t in <num>[0, 25, 50, 100, 200])
                      _Press(
                        tick: _Tick.select,
                        onTap: () {
                          setT(() => _tipFor[invoiceId] = t);
                          if (mounted) setState(() {});
                        },
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 11, vertical: 6),
                          decoration: BoxDecoration(
                              color: tipNow == t ? gold : Colors.transparent,
                              borderRadius: BorderRadius.circular(999),
                              border: Border.all(
                                  color: tipNow == t
                                      ? gold
                                      : ivory.withOpacity(.5))),
                          child: Text(t == 0 ? 'No tip' : _money(t),
                              style: TextStyle(
                                  color: tipNow == t ? plumDeep : ivory,
                                  fontSize: 11.5,
                                  fontWeight: FontWeight.w800)),
                        ),
                      ),
                  ]);
                }),
""", "tips: local builder")

# ---------------------------------------------------------------- 12. weather back-off
swap("""  Future<void> _loadWeather(DateTime wedding, String metro) async {
    final String key = '${_ymd(wedding)}|$metro';
    if (_wxCache.containsKey(key) || _wxLoading.contains(key)) return;
""", """  final Map<String, int> _wxFailAt = <String, int>{}; // v139

  Future<void> _loadWeather(DateTime wedding, String metro) async {
    final String key = '${_ymd(wedding)}|$metro';
    if (_wxCache.containsKey(key) || _wxLoading.contains(key)) return;
    // v139: after a failure, wait ten minutes instead of refetching on
    // every build
    final int? failed = _wxFailAt[key];
    if (failed != null &&
        DateTime.now().millisecondsSinceEpoch - failed < 600000) return;
""", "weather: back-off check")
swap("""      debugPrint('LAZO weather: ' + e.toString());
      _wxErr = 'Weather is unavailable right now.';
      _wx = null;
    }
""", """      debugPrint('LAZO weather: ' + e.toString());
      _wxErr = 'Weather is unavailable right now.';
      _wx = null;
      _wxFailAt[key] = DateTime.now().millisecondsSinceEpoch;
    }
""", "weather: back-off stamp")

# ---------------------------------------------------------------- 13. messages: sort by activity, states
swap("""        docs.sort((QueryDocumentSnapshot<Map<String, dynamic>> a,
            QueryDocumentSnapshot<Map<String, dynamic>> b) {
          final dynamic ta = a.data()['createdAt'];
          final dynamic tb = b.data()['createdAt'];
          if (ta is Timestamp && tb is Timestamp) {
            return tb.compareTo(ta);
          }
          return 0;
        });
        // A blocked vendor leaves the inbox""", """        docs.sort((QueryDocumentSnapshot<Map<String, dynamic>> a,
            QueryDocumentSnapshot<Map<String, dynamic>> b) {
          // v139: latest activity first, not the day the inquiry was sent
          final Map<String, dynamic> ma = a.data(), mb = b.data();
          final dynamic ta =
              ma['lastMessageAt'] ?? ma['updatedAt'] ?? ma['createdAt'];
          final dynamic tb =
              mb['lastMessageAt'] ?? mb['updatedAt'] ?? mb['createdAt'];
          if (ta is Timestamp && tb is Timestamp) {
            return tb.compareTo(ta);
          }
          return 0;
        });
        // A blocked vendor leaves the inbox""", "messages: sort by activity")
swap("""                final bool replied = st == 'responded';
                final bool booked = st == 'booked';
                final Color sc = booked
                    ? vGreen
                    : replied
                        ? plum
                        : const Color(0xFF8A6A2F);
""", """                final bool replied = st == 'responded';
                final bool booked = st == 'booked';
                final bool lost = st == 'lost'; // v139
                final bool hello =
                    inq['hello'] == true && !booked && !lost && !replied;
                final Color sc = booked
                    ? vGreen
                    : lost
                        ? const Color(0xFF8A7D90)
                        : replied
                            ? plum
                            : const Color(0xFF8A6A2F);
""", "messages: states")
swap("""                                  booked
                                      ? 'Booked \\u00b7 tap to chat'
                                      : replied
                                          ? 'Replied - tap to read'
                                          : 'Waiting on reply',
""", """                                  booked
                                      ? 'Booked \\u00b7 tap to chat'
                                      : lost
                                          ? 'Went another direction'
                                          : hello
                                              ? 'Said hello \\u00b7 tap to read'
                                              : replied
                                                  ? 'Replied - tap to read'
                                                  : 'Waiting on reply',
""", "messages: state labels")

# ---------------------------------------------------------------- 14. post-wedding June steps
swap("""      int? daysOut) {
    final List<List<dynamic>> out = <List<dynamic>>[];
    for (final QueryDocumentSnapshot<Map<String, dynamic>> d in inqs) {
      final Map<String, dynamic> m = d.data();
      final String vn = (m['vendorName'] ?? 'your vendor').toString();
      if ((m['contractStatus'] ?? '') == 'sent') {
""", """      int? daysOut) {
    final List<List<dynamic>> out = <List<dynamic>>[];
    // v139: after the wedding, June stops saying "talk to three venues"
    if (daysOut != null && daysOut < 0) {
      out.add(<dynamic>[
        'Send the thank-you notes',
        'Tick each one off on the guest list as it goes out - the count at the top keeps you honest.',
        'Open guests',
        () => setState(() => _view = _View.guests),
      ]);
      out.add(<dynamic>[
        'Add a chapter to your site',
        'The honeymoon, the first anniversary, the news - your site keeps telling the story after the day.',
        'Open website',
        () => setState(() => _view = _View.website),
      ]);
      out.add(<dynamic>[
        'Gather the photos',
        'Approve what guests shared, download the wall, and link the photographer\\u2019s gallery when it lands.',
        'Open website',
        () => setState(() => _view = _View.website),
      ]);
      return out;
    }
    for (final QueryDocumentSnapshot<Map<String, dynamic>> d in inqs) {
      final Map<String, dynamic> m = d.data();
      final String vn = (m['vendorName'] ?? 'your vendor').toString();
      if ((m['contractStatus'] ?? '') == 'sent') {
""", "june: post-wedding steps")

# ---------------------------------------------------------------- 16. chapters: list, edit, delete
swap("""  Future<void> _addChapterDialog(String slug) async {
    final TextEditingController titleC = TextEditingController();
    final TextEditingController textC = TextEditingController();
    DateTime chDate = DateTime.now();
    final List<String> photos = <String>[];
    bool busy = false;
""", r'''  // v139: chapters can be listed, edited and deleted, not only added
  Future<void> _chaptersSheet(String slug) async {
    if (!mounted) {
      return;
    }
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: ivory,
      constraints: const BoxConstraints(maxWidth: 640),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (BuildContext ctx) => SafeArea(
        child: SizedBox(
          height: MediaQuery.of(ctx).size.height * .8,
          child: StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
            stream: FirebaseFirestore.instance
                .collection('weddingSites')
                .doc(slug)
                .collection('chapters')
                .orderBy('dateIso', descending: true)
                .snapshots(),
            builder: (BuildContext c,
                AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> sn) {
              final List<QueryDocumentSnapshot<Map<String, dynamic>>> docs =
                  sn.data?.docs ??
                      <QueryDocumentSnapshot<Map<String, dynamic>>>[];
              return Column(children: <Widget>[
                Padding(
                  padding: const EdgeInsets.fromLTRB(22, 18, 14, 8),
                  child: Row(children: <Widget>[
                    Expanded(
                      child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Text('Chapters', style: _serif(size: 26)),
                            Text(
                                docs.isEmpty
                                    ? 'Honeymoon, news, milestones — the story continues on your site.'
                                    : '${docs.length} on your site · tap one to edit',
                                style: const TextStyle(
                                    fontSize: 12.5, color: muted)),
                          ]),
                    ),
                    FilledButton.icon(
                      style: FilledButton.styleFrom(
                          backgroundColor: gold, foregroundColor: plumDeep),
                      onPressed: _h(() => _addChapterDialog(slug)),
                      icon: const Icon(Icons.add_rounded, size: 16),
                      label: const Text('Add'),
                    ),
                  ]),
                ),
                Expanded(
                  child: ListView(
                    padding: const EdgeInsets.fromLTRB(18, 6, 18, 24),
                    children: docs
                        .map((QueryDocumentSnapshot<Map<String, dynamic>> d) {
                      final Map<String, dynamic> ch = d.data();
                      final List<String> ph = List<String>.from(
                          (ch['photos'] as List?)
                                  ?.map((dynamic e) => e.toString()) ??
                              const <String>[]);
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: _Press(
                          scale: .985,
                          dim: .92,
                          onTap: () => _addChapterDialog(slug, d),
                          child: _glass(
                            padding: const EdgeInsets.all(14),
                            radius: 16,
                            tint: .6,
                            borderColor: gold.withOpacity(.4),
                            child: Row(children: <Widget>[
                              if (ph.isNotEmpty)
                                Padding(
                                  padding: const EdgeInsets.only(right: 12),
                                  child: ClipRRect(
                                    borderRadius: BorderRadius.circular(10),
                                    child: Image.network(ph.first,
                                        width: 52,
                                        height: 52,
                                        fit: BoxFit.cover,
                                        errorBuilder: (BuildContext c5,
                                                Object e, StackTrace? st) =>
                                            const SizedBox(
                                                width: 52, height: 52)),
                                  ),
                                ),
                              Expanded(
                                child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: <Widget>[
                                      Text((ch['title'] ?? '').toString(),
                                          style: const TextStyle(
                                              color: plum,
                                              fontSize: 14.5,
                                              fontWeight: FontWeight.w700)),
                                      Text(
                                          '${ch['dateIso'] ?? ''}${ph.isNotEmpty ? ' · ${ph.length} photo${ph.length == 1 ? '' : 's'}' : ''}',
                                          style: const TextStyle(
                                              fontSize: 11.5, color: muted)),
                                    ]),
                              ),
                              IconButton(
                                tooltip: 'Delete',
                                onPressed: _h(() async {
                                  final bool? sure = await showDialog<bool>(
                                    context: c,
                                    builder: (BuildContext dc) => AlertDialog(
                                      backgroundColor: ivory,
                                      title: const Text('Delete this chapter?',
                                          style: TextStyle(color: plum)),
                                      content: const Text(
                                          'It comes off your site right away.',
                                          style: TextStyle(
                                              color: ink, fontSize: 14)),
                                      actions: <Widget>[
                                        TextButton(
                                            onPressed: () =>
                                                Navigator.pop(dc, false),
                                            child: const Text('Keep',
                                                style:
                                                    TextStyle(color: ink))),
                                        FilledButton(
                                            style: FilledButton.styleFrom(
                                                backgroundColor: rose,
                                                foregroundColor: ivory),
                                            onPressed: () =>
                                                Navigator.pop(dc, true),
                                            child: const Text('Delete')),
                                      ],
                                    ),
                                  );
                                  if (sure == true) {
                                    await d.reference.delete();
                                  }
                                }),
                                icon: const Icon(Icons.delete_outline_rounded,
                                    color: muted, size: 20),
                              ),
                            ]),
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                ),
              ]);
            },
          ),
        ),
      ),
    );
  }

  Future<void> _addChapterDialog(String slug,
      [QueryDocumentSnapshot<Map<String, dynamic>>? existing]) async {
    final Map<String, dynamic> ex = existing?.data() ?? <String, dynamic>{};
    final TextEditingController titleC =
        TextEditingController(text: (ex['title'] ?? '').toString());
    final TextEditingController textC =
        TextEditingController(text: (ex['text'] ?? '').toString());
    DateTime chDate =
        DateTime.tryParse((ex['dateIso'] ?? '').toString()) ?? DateTime.now();
    final List<String> photos = List<String>.from(
        (ex['photos'] as List?)?.map((dynamic e) => e.toString()) ??
            const <String>[]);
    bool busy = false;
''', "chapters: sheet + editor takes an existing chapter")
swap("""    try {
      await FirebaseFirestore.instance
          .collection('weddingSites')
          .doc(slug)
          .collection('chapters')
          .add(<String, dynamic>{
        'title': titleC.text.trim(),
        'text': textC.text.trim(),
        'dateIso':
            '${chDate.year}-${chDate.month.toString().padLeft(2, '0')}-${chDate.day.toString().padLeft(2, '0')}',
        'photos': photos,
        'createdAt': FieldValue.serverTimestamp(),
      });
      _toastC('Chapter published \\u2014 it\\u2019s live on your site \\u2713');
""", """    try {
      final Map<String, dynamic> chData = <String, dynamic>{
        'title': titleC.text.trim(),
        'text': textC.text.trim(),
        'dateIso':
            '${chDate.year}-${chDate.month.toString().padLeft(2, '0')}-${chDate.day.toString().padLeft(2, '0')}',
        'photos': photos,
        if (existing == null) 'createdAt': FieldValue.serverTimestamp(),
        'updatedAt': FieldValue.serverTimestamp(),
      };
      if (existing != null) {
        await existing.reference.set(chData, SetOptions(merge: true));
      } else {
        await FirebaseFirestore.instance
            .collection('weddingSites')
            .doc(slug)
            .collection('chapters')
            .add(chData);
      }
      _toastC(existing != null
          ? 'Chapter updated \\u2713'
          : 'Chapter published \\u2014 it\\u2019s live on your site \\u2713');
""", "chapters: add or update")
swap("""                        onPressed: _h(() => _addChapterDialog(slug)),
                        icon: const Icon(Icons.auto_stories_rounded, size: 16),
                        label: const Text(
                            'Add a chapter \\u2014 honeymoon, news, milestones'),
""", """                        onPressed: _h(() => _chaptersSheet(slug)),
                        icon: const Icon(Icons.auto_stories_rounded, size: 16),
                        label: const Text(
                            'Chapters \\u2014 honeymoon, news, milestones'),
""", "chapters: button opens the list")

# ---------------------------------------------------------------- 17. guests: search + delete
swap("""          final Map<String, dynamic> g = d.data();
          return ('${g['name'] ?? ''} ${g['party'] ?? ''}')
              .toLowerCase()
              .contains(q);
        }).toList();
""", """          final Map<String, dynamic> g = d.data();
          // v139: email, table and meal too
          return ('${g['name'] ?? ''} ${g['party'] ?? ''} ${g['email'] ?? ''} ${g['tableName'] ?? ''} ${g['meal'] ?? ''}')
              .toLowerCase()
              .contains(q);
        }).toList();
""", "guests: search fields")
swap("""            if (id != null)
              TextButton(
                onPressed: _h(() async {
                  await _guestsRef.doc(id).delete();
                  if (ctx2.mounted) {
                    Navigator.pop(ctx2, false);
                  }
""", """            if (id != null)
              TextButton(
                onPressed: _h(() async {
                  // v139: ask first, and take the personal-link doc with it
                  final bool? sure = await showDialog<bool>(
                    context: ctx2,
                    builder: (BuildContext dc) => AlertDialog(
                      backgroundColor: ivory,
                      title: Text('Remove ${nameC.text.trim().isEmpty ? 'this guest' : nameC.text.trim()}?',
                          style: const TextStyle(color: plum)),
                      content: const Text(
                          'They come off the list, the seating chart and the site\\u2019s seat finder.',
                          style: TextStyle(color: ink, fontSize: 14)),
                      actions: <Widget>[
                        TextButton(
                            onPressed: () => Navigator.pop(dc, false),
                            child: const Text('Keep',
                                style: TextStyle(color: ink))),
                        FilledButton(
                            style: FilledButton.styleFrom(
                                backgroundColor: rose,
                                foregroundColor: ivory),
                            onPressed: () => Navigator.pop(dc, true),
                            child: const Text('Remove')),
                      ],
                    ),
                  );
                  if (sure != true) {
                    return;
                  }
                  await _guestsRef.doc(id).delete();
                  try {
                    final String slug = await _siteSlug();
                    if (slug.isNotEmpty) {
                      await FirebaseFirestore.instance
                          .collection('weddingSites')
                          .doc(slug)
                          .collection('invites')
                          .doc(id)
                          .delete();
                    }
                  } catch (_) {}
                  if (ctx2.mounted) {
                    Navigator.pop(ctx2, false);
                  }
""", "guests: delete confirm + invite cleanup")

# ---------------------------------------------------------------- 18. registry: store prefill, editable links
swap("""  Future<void> _addRegistryLink(List<Map<String, dynamic>> current) async {
    final TextEditingController labelC = TextEditingController();
    final TextEditingController urlC = TextEditingController();
    String detected = '';
""", """  Future<void> _addRegistryLink(List<Map<String, dynamic>> current,
      {String presetHost = '', String presetLabel = '', int editIndex = -1}) async {
    // v139: a tapped store icon prefills; editIndex >= 0 edits that row
    final Map<String, dynamic> ed =
        editIndex >= 0 && editIndex < current.length
            ? current[editIndex]
            : <String, dynamic>{};
    final TextEditingController labelC = TextEditingController(
        text: (ed['label'] ?? presetLabel).toString());
    final TextEditingController urlC = TextEditingController(
        text: (ed['url'] ?? (presetHost.isEmpty ? '' : 'https://$presetHost/'))
            .toString());
    String detected = '';
""", "registry: prefill + edit args")
swap("""                if (current.any((Map<String, dynamic> l) =>
                    (l['url'] ?? '').toString().toLowerCase() ==
                    url.toLowerCase())) {""", """                if (current.asMap().entries.any((MapEntry<int, Map<String, dynamic>> e) =>
                    e.key != editIndex &&
                    (e.value['url'] ?? '').toString().toLowerCase() ==
                        url.toLowerCase())) {""", "registry: dupe check skips the edited row")
swap("""                urlC.text = url;
                Navigator.pop(ctx2, true);
              }),
              child: const Text('Add'),""", """                urlC.text = url;
                Navigator.pop(ctx2, true);
              }),
              child: Text(editIndex >= 0 ? 'Save' : 'Add'),""", "registry: Save label")
swap("""    final List<Map<String, dynamic>> next =
        List<Map<String, dynamic>>.from(current)
          ..add(<String, dynamic>{
            'label': label,
            'url': url,
            'store': st == null ? '' : st[1]
          });
    await _saveRegistry(next);
    _toast('Added. Your website shows it now.');
  }""", """    final Map<String, dynamic> row = <String, dynamic>{
      'label': label,
      'url': url,
      'store': st == null ? '' : st[1]
    };
    final List<Map<String, dynamic>> next =
        List<Map<String, dynamic>>.from(current);
    if (editIndex >= 0 && editIndex < next.length) {
      next[editIndex] = row; // v139: edit in place
    } else {
      next.add(row);
    }
    await _saveRegistry(next);
    _toast(editIndex >= 0
        ? 'Saved. Your website shows it now.'
        : 'Added. Your website shows it now.');
  }""", "registry: edit in place")
swap("""      child: ListTile(
        dense: true,
        onTap: () => _openLink(url),
        leading: _storeMark(
            url,
            (store.isNotEmpty ? store : (link['label'] ?? 'R').toString())[0]
                .toUpperCase(),""", """      child: ListTile(
        dense: true,
        onTap: () => _openLink(url),
        onLongPress: () => _addRegistryLink(links, editIndex: i), // v139
        leading: _storeMark(
            url,
            (store.isNotEmpty ? store : (link['label'] ?? 'R').toString())[0]
                .toUpperCase(),""", "registry: long-press edits")
swap("""                child: _Press(
                  onTap: () => _addRegistryLink(links),
                  child:
                      _storeMark('https://${st[0]}/', st[1][0], plum, size: 34),
""", """                child: _Press(
                  onTap: () => _addRegistryLink(links,
                      presetHost: st[0], presetLabel: st[1]),
                  child:
                      _storeMark('https://${st[0]}/', st[1][0], plum, size: 34),
""", "registry: icon prefills")

# ---------------------------------------------------------------- text
swap("""                          : (daysOut < 0
                              ? '${-daysOut} days'
                              : '$daysOut days')),
""", """                          : (daysOut < 0
                              ? '${-daysOut} day${-daysOut == 1 ? '' : 's'}'
                              : '$daysOut day${daysOut == 1 ? '' : 's'}')),
""", "text: 1 day")
swap("""        'Talk to three ${label}s',
""", """        'Talk to three ${label.endsWith('s') ? label : (label.contains('&') ? '$label pros' : '${label}s')}',
""", "text: plural categories")
swap("""    final int months = (daysOut / 30.4).round();
    if (booked == 0) {
""", """    final int months = (daysOut / 30.4).round();
    final String monthsOut = months < 1 ? 'under a month' : '$months months';
    if (booked == 0) {
""", "text: months out helper")
swap("$months months out", "$monthsOut out", "text: months out uses", count=4)
swap("""          waiting == 0 ? '' : (waiting == 1 ? 'to read' : 'to read'),
""", """          waiting == 0 ? '' : 'to read',
""", "text: dead ternary")
swap("""                '$stateName: issued by the ${issuer.toLowerCase()}. Both of you go, with photo ID.',
""", """                issuer.trim().isEmpty
                    ? '$stateName: both of you go, with photo ID.'
                    : '$stateName: issued by the ${issuer.toLowerCase()}. Both of you go, with photo ID.',
""", "text: issuer")
swap("""                                          _toastUndo('Date removed.',
""", """                                          _toastUndo('Moment removed.',
""", "text: moment removed")
swap("""                                      'Sent to ${sent.map((Map<String, dynamic> e) => e['vendorName']).join(', ')} \\\\u2713 They can reply in your thread.');
""", """                                      'Sent to ${sent.map((Map<String, dynamic> e) => e['vendorName']).join(', ')} \\u2713 They can reply in your thread.');
""", "text: toast escape 1")
swap("""                        _toast('Copied \\\\u2713');
""", """                        _toast('Copied \\u2713');
""", "text: toast escape 2")

OUT.write_text(s, encoding="utf-8", newline="\n")
print(f"wrote {OUT.name} ({len(s):,} chars)")
