r"""patch_couple_v161.py - Couple -> v161: MEAL CHOICES.  JC-LAZO-COUPLE-1016-MEALS

Couples send their vendors meal choices that are actually right:
  - every person coming counts, plus-ones too (their picks live in
    guests.plusAssign.{k} - the shape the seating chart already reads);
  - totals are CONFIRMED guests only; pending heads show as "still to reply",
    confirmed people with no pick as "no choice yet";
  - kids' meals on their own line, allergies by name, per-table counts once the
    seating chart has people at tables, and VENDOR MEALS (couples/{cid}/details/
    vendorMeals, prefilled from the booked team minus caterer and venue);
  - a Meal choices card on the Guests screen: totals, what's missing, the final
    count date each vendor set (or ~2 weeks out by default), and "Changed since
    you sent it Oct 2: +3 Chicken, -1 Salmon" with Send update;
  - Send meal choices goes through the existing send sheet (caterer + venue
    pre-checked): a summary message + "Guest list & meal choices.html"
    (printable / save as PDF; the name still matches Vendor v159+'s "Guest list
    & meals" chip), and a structured copy in inquiries/{id}/shared/meals for
    Vendor v202's Meal counts card;
  - the website RSVP import reads meals:[{name,meal,kid,allergies}] (the
    1016 templates) into meal/kid/allergies and plusAssign.{k}.

Needs firestore.rules JC-LAZO-RULES-1016-MEALS for shared/meals (the send still
posts the message and file without it; only the vendor card's copy fails).

Base: the newest Couple master below v161 (pass a path to override), so this
re-applies on top of a v160 another session lands first.

    python app-patches\patch_couple_v161.py [base.txt]   # writes Couple_master_v161.txt
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if len(sys.argv) > 1:
    SRC = Path(sys.argv[1])
else:
    vs = sorted(int(m.group(1)) for p in HERE.glob("Couple_master_v*.txt")
                if (m := re.fullmatch(r"Couple_master_v(\d+)\.txt", p.name)) and int(m.group(1)) < 161)
    SRC = HERE / f"Couple_master_v{vs[-1]}.txt"
DST = HERE / "Couple_master_v161.txt"
BASE = re.search(r"v(\d+)", SRC.name).group(1)
s = SRC.read_text(encoding="utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")


def rep(old, new, n=1):
    global s
    c = s.count(old)
    assert c == n, f"expected {n} match(es), found {c}: {old[:90]!r}"
    s = s.replace(old, new)


rep("// lazo_couple_dashboard.dart\n",
    "// lazo_couple_dashboard.dart\n"
    "// Build ID: JC-LAZO-COUPLE-1016-MEALS (v161: MEAL CHOICES - every person coming counts (plus-ones' picks in "
    "guests.plusAssign.{k}), confirmed-only totals with still-to-reply and no-choice-yet lines, kids' meals, allergies "
    "by name, per-table counts, vendor meals (details/vendorMeals); a Meal choices card on the Guests screen with the "
    "vendor's final-count date and 'changed since you sent it'; Send meal choices posts the summary + printable "
    "'Guest list & meal choices' to the caterer/venue thread and writes inquiries/{id}/shared/meals for Vendor v202; "
    f"the RSVP import reads the per-person meals[] from the 1016 site templates; base v{BASE})\n")

# ---- 1. RSVP import: a meal, kid's meal and allergies per person ----
rep("""      if (r['events'] is List)
        'events': List<String>.from(
            (r['events'] as List).map((dynamic e) => e.toString())),
      'updatedAt': FieldValue.serverTimestamp(),
    };
""", """      if (r['events'] is List)
        'events': List<String>.from(
            (r['events'] as List).map((dynamic e) => e.toString())),
      'updatedAt': FieldValue.serverTimestamp(),
    };
    // v161: the 1016 site sends a meal, kid's meal and allergies for every
    // person coming; plus-ones land in plusAssign.{k} (merged, so a seat the
    // chart already gave them stays).
    if (r['meals'] is List && (r['meals'] as List).isNotEmpty) {
      final List<dynamic> ms = r['meals'] as List;
      final Map<String, dynamic> pa = <String, dynamic>{};
      for (int i = 0; i < ms.length && i < 10; i++) {
        if (ms[i] is! Map) continue;
        final Map<String, dynamic> m =
            Map<String, dynamic>.from(ms[i] as Map);
        final String meal = (m['meal'] ?? '').toString().trim();
        final String al = (m['allergies'] ?? '').toString().trim();
        final bool kid = m['kid'] == true;
        if (i == 0) {
          if (meal.isNotEmpty) data['meal'] = meal;
          if (al.isNotEmpty) data['allergies'] = al;
          if (kid) data['kid'] = true;
          continue;
        }
        final String pn = (m['name'] ?? '').toString().trim();
        final Map<String, dynamic> one = <String, dynamic>{
          if (pn.isNotEmpty) 'name': pn,
          if (meal.isNotEmpty) 'meal': meal,
          if (al.isNotEmpty) 'allergies': al,
          if (kid) 'kid': true,
        };
        if (one.isNotEmpty) pa['$i'] = one;
      }
      if (pa.isNotEmpty) data['plusAssign'] = pa;
    } else if ((r['allergies'] ?? '').toString().trim().isNotEmpty) {
      data['allergies'] = (r['allergies'] ?? '').toString().trim();
    }
""")

# ---- 2. the send sheet: an extra on the sends doc, a hook after each vendor ----
rep("""    String Function(Map<String, dynamic> vendor)? pageFor,
    String Function(Map<String, dynamic> vendor)? textFor,
  }) async {
    final List<Map<String, dynamic>> booked = await _bookedForSend();""",
    """    String Function(Map<String, dynamic> vendor)? pageFor,
    String Function(Map<String, dynamic> vendor)? textFor,
    // v161: merged into couples/{cid}/sends/{kind}; run after each vendor
    // the send reached (meal choices write the vendor's structured copy).
    Map<String, dynamic>? sendsExtra,
    Future<void> Function(Map<String, dynamic> vendor)? afterEach,
  }) async {
    final List<Map<String, dynamic>> booked = await _bookedForSend();""")

rep("""              if (ok) {
                sent.add(<String, dynamic>{
                  'inquiryId': v['id'],
                  'vendorName': v['name'],
                });
              }""", """              if (ok) {
                sent.add(<String, dynamic>{
                  'inquiryId': v['id'],
                  'vendorName': v['name'],
                });
                if (afterEach != null) {
                  try {
                    await afterEach(v);
                  } catch (e) {
                    debugPrint('LAZO send after: ' + e.toString());
                  }
                }
              }""")

rep("""              await _sendsRef.doc(kind).set(<String, dynamic>{
                'kind': kind,
                'title': title,
                'to': sent,
                'at': FieldValue.serverTimestamp(),
              }, SetOptions(merge: true));""", """              await _sendsRef.doc(kind).set(<String, dynamic>{
                'kind': kind,
                'title': title,
                'to': sent,
                'at': FieldValue.serverTimestamp(),
                if (sendsExtra != null) ...sendsExtra,
              }, SetOptions(merge: true));""")

# the uploaded file's link, for the vendor's Meal counts card
rep("""      att = <String, dynamic>{
        'url': url,
        'name': fileName,
        'type': 'text/html',
        'size': bytes.length,
        'path': path,
      };""", """      att = <String, dynamic>{
        'url': url,
        'name': fileName,
        'type': 'text/html',
        'size': bytes.length,
        'path': path,
      };
      _lastSentUrl = url;""")
rep("""  Future<bool> _sendArtifact(String inquiryId, String fileName, String page,
      String note, String text, String title) async {
""", """  Future<bool> _sendArtifact(String inquiryId, String fileName, String page,
      String note, String text, String title) async {
    _lastSentUrl = '';
""")

# ---- 3. the guest sheet becomes Meal choices ----
a = s.index("  // ---- artifact 3: guest list + meals (the caterer sheet) ----\n")
b = s.index("  // ---- artifacts 4 + 5: photo groups / ceremony order (typed by the couple) ----\n")
assert s.count("  // ---- artifact 3: guest list + meals (the caterer sheet) ----\n") == 1
assert a < b and s[a:b].count("Future<void> _sendGuestSheet(") == 1
MEALS = r"""  // ---- artifact 3: meal choices + guest list (the caterer sheet) ----
  // v161 JC-LAZO-COUPLE-1016-MEALS. One count everyone reads: every person
  // coming (plus-ones' picks live in guests.plusAssign.{k}, the shape the
  // seating chart reads), confirmed guests only in the totals, pending heads
  // as "still to reply", kids' meals on their own line, allergies by name,
  // per-table counts once seated, and the vendor meals the couple owes their
  // team. Sent into the caterer's / venue's thread with a printable page, plus
  // inquiries/{id}/shared/meals for the vendor's Meal counts card.
  String _lastSentUrl = '';

  static const String kKidsMeal = 'Kids’ meal';

  DocumentReference<Map<String, dynamic>> get _vendorMealsRef =>
      _detailsRef.doc('vendorMeals');

  static int _mInt(dynamic v) => v is num ? v.toInt() : 0;

  // "Table 2" before "Table 10"
  static int _natCmp(String a, String b) {
    final RegExp d = RegExp(r'\d+');
    final Match? ma = d.firstMatch(a);
    final Match? mb = d.firstMatch(b);
    if (ma != null &&
        mb != null &&
        a.substring(0, ma.start) == b.substring(0, mb.start)) {
      final int c = int.parse(ma.group(0)!).compareTo(int.parse(mb.group(0)!));
      if (c != 0) return c;
    }
    return a.toLowerCase().compareTo(b.toLowerCase());
  }

  Map<String, dynamic> _mealSum(
      List<QueryDocumentSnapshot<Map<String, dynamic>>> docs,
      Map<String, dynamic> vm) {
    final Map<String, int> totals = <String, int>{};
    final Map<String, Map<String, int>> tables = <String, Map<String, int>>{};
    final List<String> allergies = <String>[];
    final List<List<String>> people = <List<String>>[];
    int heads = 0, awaiting = 0, noChoice = 0, kids = 0;
    void person(String name, String meal, bool kid, String al, String table) {
      heads++;
      final String key = kid ? kKidsMeal : meal;
      if (kid) kids++;
      if (key.isEmpty) {
        noChoice++;
      } else {
        totals[key] = (totals[key] ?? 0) + 1;
      }
      if (al.isNotEmpty) allergies.add('$name: $al');
      if (table.isNotEmpty) {
        final Map<String, int> t =
            tables.putIfAbsent(table, () => <String, int>{});
        final String tk = key.isEmpty ? 'No choice yet' : key;
        t[tk] = (t[tk] ?? 0) + 1;
      }
      people.add(<String>[
        name,
        kid
            ? (meal.isEmpty ? kKidsMeal : '$meal (kid)')
            : (meal.isEmpty ? 'No choice yet' : meal),
        al,
        table,
      ]);
    }

    for (final QueryDocumentSnapshot<Map<String, dynamic>> d in docs) {
      final Map<String, dynamic> g = d.data();
      final String r = (g['rsvp'] ?? 'pending').toString();
      if (r == 'no') continue;
      final int plus = _mInt(g['plusOnes']);
      if (r != 'yes') {
        awaiting += 1 + plus;
        continue;
      }
      final String nm = (g['name'] ?? '').toString().trim();
      final String name = nm.isEmpty ? 'Guest' : nm;
      person(
          name,
          (g['meal'] ?? '').toString().trim(),
          g['kid'] == true,
          (g['allergies'] ?? g['dietary'] ?? '').toString().trim(),
          (g['tableName'] ?? '').toString().trim());
      final Map<String, dynamic> pa = g['plusAssign'] is Map
          ? Map<String, dynamic>.from(g['plusAssign'] as Map)
          : <String, dynamic>{};
      for (int k = 1; k <= plus; k++) {
        final Map<String, dynamic> a = pa['$k'] is Map
            ? Map<String, dynamic>.from(pa['$k'] as Map)
            : <String, dynamic>{};
        final String pn = (a['name'] ?? '').toString().trim();
        person(
            pn.isEmpty
                ? '$name’s guest${plus > 1 ? ' $k' : ''}'
                : pn,
            (a['meal'] ?? '').toString().trim(),
            a['kid'] == true,
            (a['allergies'] ?? '').toString().trim(),
            (a['tableName'] ?? '').toString().trim());
      }
    }
    final List<Map<String, dynamic>> vrows = <Map<String, dynamic>>[];
    int vcount = 0;
    if (vm['rows'] is List) {
      for (final dynamic x in vm['rows'] as List) {
        if (x is! Map) continue;
        final int n = _mInt(x['count']);
        if (n <= 0) continue;
        vcount += n;
        vrows.add(<String, dynamic>{
          'name': (x['name'] ?? '').toString(),
          'role': (x['role'] ?? '').toString(),
          'count': n,
        });
      }
    }
    people.sort((List<String> a, List<String> b) =>
        a[0].toLowerCase().compareTo(b[0].toLowerCase()));
    return <String, dynamic>{
      'heads': heads,
      'awaiting': awaiting,
      'noChoice': noChoice,
      'kids': kids,
      'totals': totals,
      'tables': tables,
      'allergies': allergies,
      'people': people,
      'vendorMeals': vrows,
      'vendorCount': vcount,
    };
  }

  // Biggest first, kids' meals last.
  List<MapEntry<String, int>> _mealTotals(Map<String, dynamic> sum) {
    final Map<String, int> t = sum['totals'] as Map<String, int>;
    final List<MapEntry<String, int>> out = t.entries
        .where((MapEntry<String, int> e) => e.key != kKidsMeal)
        .toList()
      ..sort((MapEntry<String, int> a, MapEntry<String, int> b) =>
          b.value.compareTo(a.value));
    if ((t[kKidsMeal] ?? 0) > 0) {
      out.add(MapEntry<String, int>(kKidsMeal, t[kKidsMeal]!));
    }
    return out;
  }

  List<Map<String, dynamic>> _tableLines(Map<String, dynamic> sum) {
    final Map<String, Map<String, int>> t =
        sum['tables'] as Map<String, Map<String, int>>;
    final List<String> keys = t.keys.toList()..sort(_natCmp);
    return <Map<String, dynamic>>[
      for (final String k in keys)
        <String, dynamic>{
          't': k,
          'n': t[k]!.values.fold<int>(0, (int a, int b) => a + b),
          'line': (t[k]!.entries.toList()
                ..sort((MapEntry<String, int> a, MapEntry<String, int> b) =>
                    b.value.compareTo(a.value)))
              .map((MapEntry<String, int> e) => '${e.value} ${e.key}')
              .join(' · '),
        }
    ];
  }

  // What the last send said, kept on sends/guests.mealSnap to show what changed.
  Map<String, dynamic> _mealSnapOf(Map<String, dynamic> sum) =>
      <String, dynamic>{
        'heads': sum['heads'],
        'awaiting': sum['awaiting'],
        'noChoice': sum['noChoice'],
        'kids': sum['kids'],
        'vendorCount': sum['vendorCount'],
        'allergyCount': (sum['allergies'] as List<String>).length,
        'totals': <Map<String, dynamic>>[
          for (final MapEntry<String, int> e in _mealTotals(sum))
            <String, dynamic>{'m': e.key, 'n': e.value}
        ],
      };

  List<String> _mealDiff(Map<String, dynamic> was, Map<String, dynamic> now) {
    Map<String, int> tot(Map<String, dynamic> x) => <String, int>{
          if (x['totals'] is List)
            for (final dynamic e in x['totals'] as List)
              if (e is Map) (e['m'] ?? '').toString(): _mInt(e['n'])
        };
    final Map<String, int> a = tot(was);
    final Map<String, int> b = tot(now);
    final List<String> out = <String>[];
    String sign(int d) => d > 0 ? '+$d' : '−${-d}';
    for (final String k in <String>{...b.keys, ...a.keys}) {
      final int d = (b[k] ?? 0) - (a[k] ?? 0);
      if (d != 0) out.add('${sign(d)} $k');
    }
    final int dv = _mInt(now['vendorCount']) - _mInt(was['vendorCount']);
    if (dv != 0) out.add('${sign(dv)} vendor meal${dv.abs() == 1 ? '' : 's'}');
    final int da = _mInt(now['allergyCount']) - _mInt(was['allergyCount']);
    if (da != 0) out.add('${sign(da)} with allergies');
    return out;
  }

  String _mealLine(Map<String, dynamic> sum) {
    final List<String> bits = <String>[
      for (final MapEntry<String, int> e in _mealTotals(sum))
        '${e.value} ${e.key}',
      if (_mInt(sum['noChoice']) > 0) '${sum['noChoice']} no choice yet',
      if (_mInt(sum['vendorCount']) > 0)
        '${sum['vendorCount']} vendor meal${sum['vendorCount'] == 1 ? '' : 's'}',
      if ((sum['allergies'] as List<String>).isNotEmpty)
        '${(sum['allergies'] as List<String>).length} with allergies',
    ];
    return '${sum['heads']} confirmed${bits.isEmpty ? '' : ': ${bits.join(' · ')}'}'
        '${_mInt(sum['awaiting']) > 0 ? ' (${sum['awaiting']} still to reply)' : ''}';
  }

  String _mealText(Map<String, dynamic> sum, List<String> diff, String since,
      String who, String when) {
    final StringBuffer t = StringBuffer();
    t.writeln(
        'MEAL CHOICES${who.isEmpty ? '' : ' - $who'}${when.isEmpty ? '' : ' - $when'}');
    t.writeln('Confirmed guests: ${sum['heads']}'
        '${_mInt(sum['awaiting']) > 0 ? ' (${sum['awaiting']} still to reply)' : ''}');
    if (diff.isNotEmpty) {
      t.writeln('Changed since ${since.isEmpty ? 'last time' : since}: ${diff.join(', ')}');
    }
    t.writeln('');
    for (final MapEntry<String, int> e in _mealTotals(sum)) {
      t.writeln('${e.key}: ${e.value}');
    }
    if (_mInt(sum['noChoice']) > 0) t.writeln('No choice yet: ${sum['noChoice']}');
    final List<Map<String, dynamic>> vr =
        sum['vendorMeals'] as List<Map<String, dynamic>>;
    if (vr.isNotEmpty) {
      t.writeln('Vendor meals: ${sum['vendorCount']} ('
          '${vr.map((Map<String, dynamic> v) => '${v['name']} ${v['count']}').join(', ')})');
    }
    final List<String> al = sum['allergies'] as List<String>;
    if (al.isNotEmpty) {
      t.writeln('');
      t.writeln('ALLERGIES & DIETARY');
      for (final String x in al) {
        t.writeln('- $x');
      }
    }
    final List<Map<String, dynamic>> tl = _tableLines(sum);
    if (tl.isNotEmpty) {
      t.writeln('');
      t.writeln('BY TABLE');
      for (final Map<String, dynamic> x in tl) {
        t.writeln('${x['t']}: ${x['line']}');
      }
    }
    t.writeln('');
    t.writeln('Updated ${_shortDate(DateTime.now())} · the full list is attached.');
    return t.toString();
  }

  String _mealHtml(Map<String, dynamic> sum, List<String> diff, String since) {
    final StringBuffer h = StringBuffer();
    h.write('<p><b>Confirmed guests: ${sum['heads']}</b>'
        '${_mInt(sum['awaiting']) > 0 ? ' &middot; ${sum['awaiting']} still to reply' : ''}'
        ' &middot; updated ${_esc(_shortDate(DateTime.now()))}</p>');
    if (diff.isNotEmpty) {
      h.write('<p style="color:#8A6A2F"><b>Changed since ${_esc(since.isEmpty ? 'last time' : since)}:</b> '
          '${_esc(diff.join(', '))}</p>');
    }
    h.write('<h2>Meals</h2><table>');
    for (final MapEntry<String, int> e in _mealTotals(sum)) {
      h.write('<tr><td>${_esc(e.key)}</td><td><b>${e.value}</b></td></tr>');
    }
    if (_mInt(sum['noChoice']) > 0) {
      h.write('<tr><td>No choice yet</td><td><b>${sum['noChoice']}</b></td></tr>');
    }
    if (_mInt(sum['vendorCount']) > 0) {
      h.write('<tr><td>Vendor meals</td><td><b>${sum['vendorCount']}</b></td></tr>');
    }
    h.write('</table>');
    final List<String> al = sum['allergies'] as List<String>;
    if (al.isNotEmpty) {
      h.write('<h2>Allergies &amp; dietary</h2><table>');
      for (final String x in al) {
        final int i = x.indexOf(': ');
        h.write(i < 0
            ? '<tr><td colspan="2">${_esc(x)}</td></tr>'
            : '<tr><td><b>${_esc(x.substring(0, i))}</b></td><td>${_esc(x.substring(i + 2))}</td></tr>');
      }
      h.write('</table>');
    }
    final List<Map<String, dynamic>> tl = _tableLines(sum);
    if (tl.isNotEmpty) {
      h.write('<h2>By table</h2><table><tr><th>Table</th><th>Seated</th><th>Meals</th></tr>');
      for (final Map<String, dynamic> x in tl) {
        h.write('<tr><td><b>${_esc(x['t'].toString())}</b></td><td>${x['n']}</td>'
            '<td>${_esc(x['line'].toString())}</td></tr>');
      }
      h.write('</table>');
    }
    final List<Map<String, dynamic>> vr =
        sum['vendorMeals'] as List<Map<String, dynamic>>;
    if (vr.isNotEmpty) {
      h.write('<h2>Vendor meals</h2><table>');
      for (final Map<String, dynamic> v in vr) {
        h.write('<tr><td><b>${_esc(v['name'].toString())}</b></td>'
            '<td>${_esc(v['role'].toString())}</td><td>${v['count']}</td></tr>');
      }
      h.write('</table>');
    }
    h.write('<h2>Guests</h2><table><tr><th>Name</th><th>Meal</th>'
        '<th>Allergies / dietary</th><th>Table</th></tr>');
    for (final List<String> p in sum['people'] as List<List<String>>) {
      h.write('<tr>${p.map((String x) => '<td>${_esc(x)}</td>').join()}</tr>');
    }
    h.write('</table>');
    if (_mInt(sum['awaiting']) > 0) {
      h.write('<p>${sum['awaiting']} more guest${sum['awaiting'] == 1 ? ' hasn’t' : 's haven’t'} replied yet. '
          'We’ll send an update as RSVPs come in.</p>');
    }
    return h.toString();
  }

  Future<void> _sendGuestSheet(
      List<QueryDocumentSnapshot<Map<String, dynamic>>> docs,
      Map<String, dynamic> couple) =>
      _sendMealChoices(docs, couple);

  Future<void> _sendMealChoices(
      List<QueryDocumentSnapshot<Map<String, dynamic>>> docs,
      Map<String, dynamic> couple) async {
    if (docs.isEmpty) {
      _toast('Add guests first.');
      return;
    }
    Map<String, dynamic> vm = <String, dynamic>{};
    Map<String, dynamic> last = <String, dynamic>{};
    try {
      vm = (await _vendorMealsRef.get()).data() ?? <String, dynamic>{};
    } catch (_) {}
    try {
      last = (await _sendsRef.doc('guests').get()).data() ?? <String, dynamic>{};
    } catch (_) {}
    final Map<String, dynamic> sum = _mealSum(docs, vm);
    final Map<String, dynamic> snap = _mealSnapOf(sum);
    final Map<String, dynamic> was = last['mealSnap'] is Map
        ? Map<String, dynamic>.from(last['mealSnap'] as Map)
        : <String, dynamic>{};
    final List<String> diff = was.isEmpty ? <String>[] : _mealDiff(was, snap);
    final String since = last['at'] is Timestamp
        ? _shortDate((last['at'] as Timestamp).toDate())
        : '';
    final String who = _coupleLabel(couple);
    final String when = _weddingDateLine(couple);
    final List<Map<String, dynamic>> tl = _tableLines(sum);
    await _sendToVendors(
      kind: 'guests',
      title: 'meal choices',
      fileName: 'Guest list & meal choices.html',
      page: _printShell(
          'Meal choices',
          <String>[if (who.isNotEmpty) who, if (when.isNotEmpty) when]
              .join(' · '),
          _mealHtml(sum, diff, since)),
      text: _mealText(sum, diff, since, who, when),
      tags: <String>['caterer', 'venue'],
      note: was.isEmpty
          ? 'Here are our meal choices so far. We’ll send an update as more RSVPs come in.'
          : (diff.isEmpty
              ? 'Our meal choices again - nothing has changed since $since.'
              : 'Updated meal choices - since ${since.isEmpty ? 'last time' : since}: ${diff.join(', ')}.'),
      preview: _mealLine(sum),
      sendsExtra: <String, dynamic>{'mealSnap': snap},
      afterEach: (Map<String, dynamic> v) async {
        final DocumentReference<Map<String, dynamic>> ref = FirebaseFirestore
            .instance
            .collection('inquiries')
            .doc(v['id'].toString())
            .collection('shared')
            .doc('meals');
        Map<String, dynamic> old = <String, dynamic>{};
        try {
          old = (await ref.get()).data() ?? <String, dynamic>{};
        } catch (_) {}
        final List<String> al = sum['allergies'] as List<String>;
        final Map<String, dynamic> doc = <String, dynamic>{
          'kind': 'meals',
          'totals': snap['totals'],
          'heads': sum['heads'],
          'awaiting': sum['awaiting'],
          'noChoice': sum['noChoice'],
          'kids': sum['kids'],
          'allergies': <String>[
            for (final String x in al.take(80))
              x.length > 160 ? x.substring(0, 160) : x
          ],
          'allergyCount': al.length,
          'tables': tl.take(80).toList(),
          'vendorMeals': sum['vendorMeals'],
          'vendorCount': sum['vendorCount'],
          'sentAt': FieldValue.serverTimestamp(),
          'sentBy': _uid ?? '',
          'fileUrl': _lastSentUrl,
          'coupleName': who,
          if (couple['weddingDate'] is Timestamp)
            'weddingDate': couple['weddingDate'],
          if (old['totals'] is List)
            'prev': <String, dynamic>{
              'totals': old['totals'],
              'heads': old['heads'],
              'vendorCount': old['vendorCount'],
              'allergyCount': old['allergyCount'],
            },
          if (old['sentAt'] is Timestamp) 'prevAt': old['sentAt'],
        };
        // merge: every count is a list, so it is replaced whole (a dropped
        // entree can't linger); the vendor's finalDue / vendorSeenAt stay.
        await ref.set(doc, SetOptions(merge: true));
      },
    );
  }

  // The card on the Guests screen.
  Widget _mealCard(List<QueryDocumentSnapshot<Map<String, dynamic>>> docs) {
    if (docs.isEmpty) return const SizedBox.shrink();
    return StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
      stream: _liveDoc('vmeals:$_cid', () => _vendorMealsRef),
      initialData: _liveD['vmeals:$_cid']?.latest,
      builder: (BuildContext c,
          AsyncSnapshot<DocumentSnapshot<Map<String, dynamic>>> vs) {
        final Map<String, dynamic> vm = vs.data?.data() ?? <String, dynamic>{};
        return StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
          stream: _liveDoc('send:guests:$_cid', () => _sendsRef.doc('guests')),
          initialData: _liveD['send:guests:$_cid']?.latest,
          builder: (BuildContext c2,
              AsyncSnapshot<DocumentSnapshot<Map<String, dynamic>>> ss) {
            final Map<String, dynamic> sent =
                ss.data?.data() ?? <String, dynamic>{};
            final Map<String, dynamic> couple =
                _liveD['couple:$_cid']?.latest?.data() ?? <String, dynamic>{};
            final Map<String, dynamic> sum = _mealSum(docs, vm);
            final Map<String, dynamic> was = sent['mealSnap'] is Map
                ? Map<String, dynamic>.from(sent['mealSnap'] as Map)
                : <String, dynamic>{};
            final List<String> diff =
                was.isEmpty ? <String>[] : _mealDiff(was, _mealSnapOf(sum));
            final String since = sent['at'] is Timestamp
                ? _shortDate((sent['at'] as Timestamp).toDate())
                : '';
            final List<dynamic> to =
                sent['to'] is List ? sent['to'] as List : <dynamic>[];
            final List<MapEntry<String, int>> totals = _mealTotals(sum);
            final List<String> gaps = <String>[
              if (_mInt(sum['awaiting']) > 0) '${sum['awaiting']} still to reply',
              if (_mInt(sum['noChoice']) > 0) '${sum['noChoice']} no choice yet',
              if ((sum['allergies'] as List<String>).isNotEmpty)
                '${(sum['allergies'] as List<String>).length} with allergies',
              '${sum['vendorCount']} vendor meal${sum['vendorCount'] == 1 ? '' : 's'}',
            ];
            return Padding(
              padding: const EdgeInsets.only(top: 12),
              child: _glass(
                padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
                radius: 20,
                tint: .6,
                borderColor: gold.withOpacity(.5),
                child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Row(children: <Widget>[
                        Icon(Icons.restaurant_rounded,
                            color: _lzFg(plum), size: 18),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text('Meal choices',
                              style: TextStyle(
                                  color: _lzFg(ink),
                                  fontSize: 15,
                                  fontWeight: FontWeight.w800)),
                        ),
                        Text('${sum['heads']} confirmed',
                            style: TextStyle(
                                color: _lzFg(muted),
                                fontSize: 11.5,
                                fontWeight: FontWeight.w700)),
                      ]),
                      const SizedBox(height: 10),
                      if (totals.isEmpty)
                        Text(
                            _mInt(sum['heads']) == 0
                                ? 'Meal counts start with your first yes. Add dinner options to your website’s RSVP and guests pick their own.'
                                : 'No meal picks yet. Add dinner options to your website’s RSVP, or set a meal on each guest.',
                            style: TextStyle(
                                fontSize: 12, color: _lzFg(muted), height: 1.4))
                      else
                        Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
                          for (final MapEntry<String, int> e in totals)
                            Container(
                              padding: const EdgeInsets.fromLTRB(4, 4, 10, 4),
                              decoration: BoxDecoration(
                                color: _lzBg(Colors.white.withOpacity(.7)),
                                borderRadius: BorderRadius.circular(999),
                                border: Border.all(color: _lzLine(goldLine)),
                              ),
                              child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: <Widget>[
                                    Container(
                                      constraints:
                                          const BoxConstraints(minWidth: 24),
                                      padding: const EdgeInsets.symmetric(
                                          horizontal: 6, vertical: 2),
                                      decoration: BoxDecoration(
                                          color: _lzBg(plum),
                                          borderRadius:
                                              BorderRadius.circular(999)),
                                      child: Text('${e.value}',
                                          textAlign: TextAlign.center,
                                          style: TextStyle(
                                              color: _lzFg(gold),
                                              fontSize: 11.5,
                                              fontWeight: FontWeight.w800)),
                                    ),
                                    const SizedBox(width: 6),
                                    Text(e.key,
                                        style: TextStyle(
                                            color: _lzFg(ink),
                                            fontSize: 12.5,
                                            fontWeight: FontWeight.w700)),
                                  ]),
                            ),
                        ]),
                      const SizedBox(height: 8),
                      Text(gaps.join(' · '),
                          style: TextStyle(
                              fontSize: 11.5,
                              color: _lzFg(muted),
                              fontWeight: FontWeight.w600)),
                      for (final dynamic t in to.take(3))
                        if (t is Map && (t['inquiryId'] ?? '').toString().isNotEmpty)
                          _mealDueLine((t['inquiryId'] ?? '').toString(),
                              (t['vendorName'] ?? 'Your vendor').toString(), couple),
                      if (diff.isNotEmpty) ...<Widget>[
                        const SizedBox(height: 10),
                        _lzNote(Icons.update_rounded,
                            'Changed since you sent it${since.isEmpty ? '' : ' on $since'}: ${diff.join(', ')}'),
                      ],
                      const SizedBox(height: 12),
                      Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                        _pcB_chip(
                            Icons.send_rounded,
                            to.isEmpty
                                ? 'Send meal choices'
                                : (diff.isEmpty ? 'Send again' : 'Send update'),
                            () => _sendMealChoices(docs, couple)),
                        _pcB_chip(Icons.badge_outlined, 'Vendor meals',
                            () => _editVendorMeals(vm)),
                      ]),
                    ]),
              ),
            );
          },
        );
      },
    );
  }

  // "Final count due to Harvest Catering: Nov 1" - the vendor sets it in their
  // thread (Vendor v202); until then about two weeks before the wedding.
  Widget _mealDueLine(
      String inquiryId, String vendorName, Map<String, dynamic> couple) {
    return StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
      stream: _liveDoc(
          'meals:$inquiryId',
          () => FirebaseFirestore.instance
              .collection('inquiries')
              .doc(inquiryId)
              .collection('shared')
              .doc('meals')),
      initialData: _liveD['meals:$inquiryId']?.latest,
      builder: (BuildContext c,
          AsyncSnapshot<DocumentSnapshot<Map<String, dynamic>>> s) {
        final Map<String, dynamic> m = s.data?.data() ?? <String, dynamic>{};
        DateTime? due;
        bool set = false;
        if (m['finalDue'] is Timestamp) {
          due = (m['finalDue'] as Timestamp).toDate();
          set = true;
        } else if (couple['weddingDate'] is Timestamp) {
          due = (couple['weddingDate'] as Timestamp)
              .toDate()
              .subtract(const Duration(days: 14));
        }
        final bool seen = m['vendorSeenAt'] is Timestamp &&
            m['sentAt'] is Timestamp &&
            !(m['vendorSeenAt'] as Timestamp)
                .toDate()
                .isBefore((m['sentAt'] as Timestamp).toDate());
        if (due == null && !seen) return const SizedBox.shrink();
        final int days = due == null
            ? 999
            : DateTime(due.year, due.month, due.day)
                .difference(DateTime(DateTime.now().year,
                    DateTime.now().month, DateTime.now().day))
                .inDays;
        final bool soon = set && days >= 0 && days <= 7;
        final String dueText = due == null
            ? ''
            : set
                ? 'final count due ${_shortDate(due)}${days == 0 ? ' (today)' : days == 1 ? ' (tomorrow)' : days > 1 && days <= 7 ? ' (in $days days)' : ''}'
                : 'final count usually due about ${_shortDate(due)}';
        return Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Row(children: <Widget>[
            Icon(soon ? Icons.event_busy_rounded : Icons.event_rounded,
                size: 14, color: _lzFg(soon ? rose : muted)),
            const SizedBox(width: 6),
            Expanded(
              child: Text(
                  '$vendorName${dueText.isEmpty ? '' : ': $dueText'}${seen ? ' · seen' : ''}',
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                      fontSize: 11.5,
                      color: _lzFg(soon ? rose : muted),
                      fontWeight: soon ? FontWeight.w800 : FontWeight.w600)),
            ),
          ]),
        );
      },
    );
  }

  // Vendor meals: the team working through dinner. Prefilled from the booked
  // vendors (the caterer and the venue feed their own staff).
  Future<void> _editVendorMeals(Map<String, dynamic> vm) async {
    final List<Map<String, dynamic>> rows = <Map<String, dynamic>>[];
    final Set<String> seen = <String>{};
    if (vm['rows'] is List) {
      for (final dynamic x in vm['rows'] as List) {
        if (x is! Map) continue;
        final String nm = (x['name'] ?? '').toString().trim();
        if (nm.isEmpty) continue;
        seen.add(nm.toLowerCase());
        rows.add(<String, dynamic>{
          'name': nm,
          'role': (x['role'] ?? '').toString(),
          'count': _mInt(x['count']),
        });
      }
    }
    for (final Map<String, dynamic> v in await _bookedForSend()) {
      final String tag = (v['tag'] ?? '').toString();
      if (tag == 'caterer' || tag == 'venue') continue;
      final String nm = v['name'].toString().trim();
      if (nm.isEmpty || seen.contains(nm.toLowerCase())) continue;
      seen.add(nm.toLowerCase());
      rows.add(<String, dynamic>{
        'name': nm,
        'role': v['label'].toString(),
        'count': 1,
      });
    }
    if (!mounted) return;
    final TextEditingController addC = TextEditingController();
    bool busy = false;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx, StateSetter setS) {
          Future<void> save() async {
            setS(() => busy = true);
            try {
              await _vendorMealsRef.set(<String, dynamic>{
                'rows': <Map<String, dynamic>>[
                  for (final Map<String, dynamic> r in rows)
                    <String, dynamic>{
                      'name': r['name'],
                      'role': r['role'],
                      'count': r['count'],
                    }
                ],
                'updatedAt': FieldValue.serverTimestamp(),
              });
              if (ctx.mounted) Navigator.of(ctx).pop();
              _toast('Vendor meals saved ✓');
            } catch (_) {
              setS(() => busy = false);
              _toast('Could not save - try again.');
            }
          }

          void add() {
            final String t = addC.text.trim();
            if (t.isEmpty) return;
            setS(() {
              rows.add(<String, dynamic>{'name': t, 'role': '', 'count': 1});
              addC.clear();
            });
          }

          Widget row(int i) {
            final Map<String, dynamic> r = rows[i];
            final int n = _mInt(r['count']);
            return Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.fromLTRB(12, 6, 6, 6),
              decoration: BoxDecoration(
                color: _lzBg(Colors.white),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: _lzLine(n > 0 ? gold : goldLine)),
              ),
              child: Row(children: <Widget>[
                Expanded(
                  child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(r['name'].toString(),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                                color: _lzFg(ink),
                                fontSize: 13.5,
                                fontWeight: FontWeight.w800)),
                        if (r['role'].toString().isNotEmpty)
                          Text(r['role'].toString(),
                              style: TextStyle(
                                  fontSize: 11.5, color: _lzFg(muted))),
                      ]),
                ),
                IconButton(
                  tooltip: 'One fewer',
                  visualDensity: VisualDensity.compact,
                  onPressed: n > 0 ? () => setS(() => r['count'] = n - 1) : null,
                  icon: Icon(Icons.remove_circle_outline_rounded,
                      color: _lzFg(n > 0 ? plum : muted.withOpacity(.4))),
                ),
                SizedBox(
                  width: 22,
                  child: Text('$n',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                          color: _lzFg(ink),
                          fontSize: 15,
                          fontWeight: FontWeight.w800)),
                ),
                IconButton(
                  tooltip: 'One more',
                  visualDensity: VisualDensity.compact,
                  onPressed: n < 9 ? () => setS(() => r['count'] = n + 1) : null,
                  icon: Icon(Icons.add_circle_outline_rounded,
                      color: _lzFg(plum)),
                ),
              ]),
            );
          }

          final int total = rows.fold<int>(
              0, (int a, Map<String, dynamic> r) => a + _mInt(r['count']));
          return _lzFrame(ctx,
              icon: Icons.badge_outlined,
              title: 'Vendor meals',
              subtitle:
                  'Vendors working through dinner usually get a meal - check their contracts. A photographer with a second shooter is 2.',
              children: <Widget>[
                _lzSection('Who needs a meal', trailing: '$total'),
                if (rows.isEmpty)
                  _lzNote(Icons.info_outline_rounded,
                      'No vendors booked on Lazo yet. Add anyone working the day below.'),
                for (int i = 0; i < rows.length; i++) row(i),
                const SizedBox(height: 6),
                Row(children: <Widget>[
                  Expanded(
                    child: TextField(
                      controller: addC,
                      enabled: !busy,
                      textCapitalization: TextCapitalization.words,
                      onSubmitted: (String _) => add(),
                      style: TextStyle(color: _lzFg(ink), fontSize: 13.5),
                      decoration: _lightDeco('Add someone',
                          hint: 'Second shooter, coordinator…'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  _pcB_chip(Icons.add_rounded, 'Add', add),
                ]),
              ],
              footer: _lzActions(
                  secondary: 'Cancel',
                  onSecondary: () => Navigator.of(ctx).pop(),
                  primary: busy ? 'Saving…' : 'Save',
                  icon: Icons.check_rounded,
                  busy: busy,
                  onPrimary: save));
        },
      ),
    );
  }

"""
s = s[:a] + MEALS + s[b:]

# ---- 4. the Day-Of share row says what it is now ----
rep("""                  kind: 'guests',
                  icon: Icons.restaurant_rounded,
                  title: 'Guest list & meals',
                  sub: 'Headcount, meals, allergies, tables',""",
    """                  kind: 'guests',
                  icon: Icons.restaurant_rounded,
                  title: 'Meal choices',
                  sub: 'Meals per person, kids, allergies, tables, vendor meals',""")

# ---- 5. the Guests screen: the gold pill + the Meal choices card ----
rep("""                              Icon(Icons.send_rounded, color: plum, size: 14),
                              SizedBox(width: 5),
                              Text('Send to caterer',""",
    """                              Icon(Icons.send_rounded, color: plum, size: 14),
                              SizedBox(width: 5),
                              Text('Send meal choices',""")

# the one-line meal summary inside the headcount card moves to the card below
rep("""                Builder(builder: (BuildContext bc) {
                  final Map<String, int> meals = <String, int>{};
                  int allergies = 0;
                  for (final QueryDocumentSnapshot<Map<String, dynamic>> d
                      in docs) {
                    final Map<String, dynamic> g = d.data();
                    if ((g['rsvp'] ?? '') == 'no') {
                      continue;
                    }
                    final String m = (g['meal'] ?? '').toString().trim();
                    if (m.isNotEmpty) {
                      meals[m] = (meals[m] ?? 0) + 1;
                    }
                    if ((g['allergies'] ?? '').toString().trim().isNotEmpty) {
                      allergies++;
                    }
                  }
                  if (meals.isEmpty && allergies == 0) {
                    return const SizedBox.shrink();
                  }
                  final String line = <String>[
                    ...meals.entries.map(
                        (MapEntry<String, int> e) => '${e.value} ${e.key}'),
                    if (allergies > 0) '$allergies with allergies',
                  ].join(' \\u00b7 ');
                  return Padding(
                    padding: const EdgeInsets.only(top: 10),
                    child: Text(line,
                        textAlign: TextAlign.center,
                        style:  TextStyle(
                            fontSize: 11.5,
                            color: _lzFg(muted),
                            fontWeight: FontWeight.w600)),
                  );
                }),
              ]),
            ),
            _seatingCard(docs),""", """              ]),
            ),
            // v161: meals per person, what's missing, the vendor's date
            _mealCard(docs),
            _seatingCard(docs),""")

if crlf:
    s = s.replace("\n", "\r\n")
DST.write_text(s, encoding="utf-8", newline="")
print(f"wrote {DST.name} from {SRC.name} ({len(s):,} chars)")
