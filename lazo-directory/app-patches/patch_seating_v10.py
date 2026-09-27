"""patch_seating_v10.py - JC-LAZO-SEAT-0920-010
Three things Folia does that we didn't:
  1. MEALS ON THE TABLE. Every reception table shows its meal counts from the
     guest list - "5 chicken · 2 fish · 1 veg" - under the seat count, and the
     rail gets a chip per meal so "who still needs a seat among the fish" is
     one tap. Reads guests.meal, the same field the caterer sheet prints.
  2. TWO MORE SHAPES. A king's table (long, seats down both sides and one at
     each head) and a serpentine (an S-curve band, seats along both edges,
     drawn with a painter). In the Add menu, the inspector and the print.
  3. THE PROCESSIONAL. On the ceremony plan, a Processional button opens an
     ordered list - officiant, grandparents, parents, the wedding party in
     pairs, ring bearer, flower girl, the couple - that the couple reorders
     by drag, with "Use a typical order" to start. Stored on the ceremony doc
     (seating/ceremony.processional) and printed at the top of the usher list.
Applies on top of Seating_master_ceremony.txt -> Seating_master_v10.txt.
Anchor-and-assert.
  python app-patches\\patch_seating_v10.py [src] [out]
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Seating_master_ceremony.txt"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "Seating_master_v10.txt"
s = SRC.read_text(encoding="utf-8")
if "JC-LAZO-SEAT-0920-010" in s:
    raise SystemExit("already applied")


def swap(old, new, label, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"ABORT [{label}]: anchor matched {n} times, expected {count}")
    s = s.replace(old, new)
    print(f"  ok  {label}")


swap("// Build ID: JC-LAZO-SEAT-0920-009\n",
     "// Build ID: JC-LAZO-SEAT-0920-010\n"
     "// (v10: MEALS, SHAPES, PROCESSIONAL - every reception table shows its meal counts from the guest list and the rail filters by meal; king's table (seats down both sides and a head at each end) and serpentine (an S-band drawn by a painter, seats along both edges) join round, long, sweetheart and row; on the ceremony plan a Processional sheet orders who walks when, drag to reorder, typical order to start, stored on seating/ceremony.processional and printed at the top of the usher list. base v9)\n",
     "header")

# ---------------------------------------------------------------- 1. meals
swap("""  String _rowLabel(_SeatTable t, int filled) {""",
     """  // v10: meal counts at a table, from guests.meal ("Chicken", "fish"...).
  String _mealOf(String gid) {
    final _Guest? g = _guests[gid];
    if (g == null) return '';
    final Map<String, dynamic> raw = _raw[g.parentId] ?? const <String, dynamic>{};
    if (g.isPlus) {
      final Map<String, dynamic> pa = raw[_fld('plusAssign')] is Map
          ? Map<String, dynamic>.from(raw[_fld('plusAssign')] as Map)
          : const <String, dynamic>{};
      final Map<String, dynamic> a = pa['${g.k}'] is Map ? Map<String, dynamic>.from(pa['${g.k}'] as Map) : const <String, dynamic>{};
      final String pm = (a['meal'] ?? '').toString().trim();
      if (pm.isNotEmpty) return pm;
    }
    return (raw['meal'] ?? '').toString().trim();
  }

  Map<String, int> _mealCounts(String tableId) {
    final Map<String, int> out = <String, int>{};
    _occ(tableId).forEach((int seat, String gid) {
      final String m = _mealOf(gid);
      if (m.isEmpty) return;
      final String k = m[0].toUpperCase() + m.substring(1).toLowerCase();
      out[k] = (out[k] ?? 0) + 1;
    });
    return out;
  }

  String _mealLine(String tableId) {
    final Map<String, int> c = _mealCounts(tableId);
    if (c.isEmpty) return '';
    final List<MapEntry<String, int>> e = c.entries.toList()
      ..sort((MapEntry<String, int> a, MapEntry<String, int> b) => b.value.compareTo(a.value));
    return e.map((MapEntry<String, int> x) => '${x.value} ${x.key.toLowerCase()}').join(' \\u00b7 ');
  }

  List<String> _mealChoices() {
    final Set<String> out = <String>{};
    for (final _Guest g in _guests.values) {
      if (!_coming(g)) continue;
      final String m = _mealOf(g.id);
      if (m.isNotEmpty) out.add(m[0].toUpperCase() + m.substring(1).toLowerCase());
    }
    final List<String> l = out.toList()..sort();
    return l.take(6).toList();
  }

  int _mealCount(String meal) => _guests.values
      .where((_Guest g) => _coming(g) && _mealOf(g.id).toLowerCase() == meal.toLowerCase())
      .length;

  String _rowLabel(_SeatTable t, int filled) {""", "meal helpers")

swap("""                    const SizedBox(height: 3),
                    Text('$filled of ${t.seats}',
                        style: TextStyle(
                            fontSize: 11,
                            color: full ? vGreen : muted,
                            fontWeight: FontWeight.w700)),
                    if (warns.isNotEmpty)""",
     """                    const SizedBox(height: 3),
                    Text('$filled of ${t.seats}',
                        style: TextStyle(
                            fontSize: 11,
                            color: full ? vGreen : muted,
                            fontWeight: FontWeight.w700)),
                    if (_plan == 'main' && _mealLine(t.id).isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.only(top: 2),
                        child: Text(_mealLine(t.id),
                            textAlign: TextAlign.center,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                                fontSize: 9.5,
                                color: Color(0xFF8A6A2F),
                                fontWeight: FontWeight.w700,
                                height: 1.2)),
                      ),
                    if (warns.isNotEmpty)""", "meal line on the table")

swap("""      if (_filter == 'side2' && g.side != 'partner2') {
        return false;
      }
""", """      if (_filter == 'side2' && g.side != 'partner2') {
        return false;
      }
      if (_filter.startsWith('meal:') &&
          _mealOf(g.id).toLowerCase() != _filter.substring(5).toLowerCase()) {
        return false;
      }
""", "rail meal filter")

swap("""            if (_plan == 'ceremony') ...<Widget>[
              const SizedBox(width: 6),
              _filterChip('side1', _sideFirstName('partner1'),
                  _sideCount('partner1'), poke),""",
     """            if (_plan == 'main')
              for (final String m in _mealChoices()) ...<Widget>[
                const SizedBox(width: 6),
                _filterChip('meal:$m', m, _mealCount(m), poke),
              ],
            if (_plan == 'ceremony') ...<Widget>[
              const SizedBox(width: 6),
              _filterChip('side1', _sideFirstName('partner1'),
                  _sideCount('partner1'), poke),""", "rail meal chips")

swap("""      if (_filter.startsWith('side')) {
        _filter = 'unseated';
      }
""", """      if (_filter.startsWith('side') || _filter.startsWith('meal:')) {
        _filter = 'unseated';
      }
""", "plan switch resets meal filter")

# ---------------------------------------------------------------- 2. shapes
swap("""  int _seatCap(_SeatTable t) =>
      t.shape == 'sweetheart' ? 2 : (t.shape == 'row' ? kMaxRow : kMaxSeats);""",
     """  int _seatCap(_SeatTable t) => t.shape == 'sweetheart'
      ? 2
      : (t.shape == 'row' || t.shape == 'king' || t.shape == 'serp' ? kMaxRow : kMaxSeats);""",
     "seat cap")

swap("""      seats: shape == 'sweetheart' ? 2 : (shape == 'rect' ? 10 : 8),""",
     """      seats: shape == 'sweetheart'
          ? 2
          : (shape == 'rect' ? 10 : (shape == 'king' ? 14 : (shape == 'serp' ? 16 : 8))),""",
     "add-table default seats")

swap("""        _menuItem('table:rect', Icons.crop_landscape_rounded, 'Long table',
            '10 seats to start'),
        if (!cer)
          _menuItem('table:sweetheart', Icons.favorite_border_rounded,
              'Sweetheart table', 'Just the two of you'),""",
     """        _menuItem('table:rect', Icons.crop_landscape_rounded, 'Long table',
            '10 seats to start'),
        if (!cer)
          _menuItem('table:king', Icons.table_bar_rounded, 'King\\u2019s table',
              'Long, a head seat at each end \\u00b7 14 to start'),
        if (!cer)
          _menuItem('table:serp', Icons.waves_rounded, 'Serpentine',
              'An S-curve, seats along both sides \\u00b7 16 to start'),
        if (!cer)
          _menuItem('table:sweetheart', Icons.favorite_border_rounded,
              'Sweetheart table', 'Just the two of you'),""",
     "add menu shapes")

swap("""            _chip('Row', t.shape == 'row', () {
              _pushUndo();
              t.shape = 'row';
              poke();
              _scheduleSave();
            }),
            if (_plan == 'main')
              _chip('Sweetheart', t.shape == 'sweetheart', () {""",
     """            _chip('Row', t.shape == 'row', () {
              _pushUndo();
              t.shape = 'row';
              poke();
              _scheduleSave();
            }),
            if (_plan == 'main')
              _chip('King\\u2019s', t.shape == 'king', () {
                _pushUndo();
                t.shape = 'king';
                if (t.seats < 4) {
                  _setSeats(t, 4);
                }
                poke();
                _scheduleSave();
              }),
            if (_plan == 'main')
              _chip('Serpentine', t.shape == 'serp', () {
                _pushUndo();
                t.shape = 'serp';
                if (t.seats < 4) {
                  _setSeats(t, 4);
                }
                poke();
                _scheduleSave();
              }),
            if (_plan == 'main')
              _chip('Sweetheart', t.shape == 'sweetheart', () {""",
     "inspector shape chips")

swap("""    if (s == 'row') {
      return 'Row';
    }
    return 'Round table';
  }
""", """    if (s == 'row') {
      return 'Row';
    }
    if (s == 'king') {
      return 'King\\u2019s table';
    }
    if (s == 'serp') {
      return 'Serpentine';
    }
    return 'Round table';
  }
""", "shape label")

swap("""    if (shape == 'row') {
      return Size((seats * 40 + 24).clamp(120, 1300).toDouble(), 30);
    }
    if (shape == 'rect') {""",
     """    if (shape == 'row') {
      return Size((seats * 40 + 24).clamp(120, 1300).toDouble(), 30);
    }
    if (shape == 'king') {
      // two head seats, the rest split down the long sides
      final int perSide = ((seats - 2) / 2).ceil().clamp(1, 30);
      return Size((perSide * 44 + 60).clamp(160, 1400).toDouble(), 84);
    }
    if (shape == 'serp') {
      final int perSide = (seats / 2).ceil().clamp(2, 30);
      return Size((perSide * 46 + 40).clamp(200, 1400).toDouble(), 150);
    }
    if (shape == 'rect') {""", "shape sizes")

swap("""    if (shape == 'sweetheart' || shape == 'row') {
      final double step = s.width / (seats + 1);
      return Offset(step * (i + 1), s.height + kRing);
    }
    if (shape == 'rect') {""",
     """    if (shape == 'sweetheart' || shape == 'row') {
      final double step = s.width / (seats + 1);
      return Offset(step * (i + 1), s.height + kRing);
    }
    if (shape == 'king') {
      if (i == 0) return Offset(-kRing, s.height / 2); // the head, left
      if (i == 1) return Offset(s.width + kRing, s.height / 2); // the head, right
      final int rest = seats - 2;
      final int top = rest - (rest ~/ 2);
      final int j = i - 2;
      if (j < top) {
        final double stepT = s.width / (top + 1);
        return Offset(stepT * (j + 1), -kRing);
      }
      final int k = j - top;
      final int bottom = rest - top;
      final double stepB = s.width / ((bottom == 0 ? 1 : bottom) + 1);
      return Offset(stepB * (k + 1), s.height + kRing);
    }
    if (shape == 'serp') {
      // The band's centre line is an S over the width; seats sit on both edges.
      final int top = seats - (seats ~/ 2);
      final int bottom = seats - top;
      final bool onTop = i < top;
      final int n = onTop ? top : bottom;
      final int j = onTop ? i : i - top;
      final double x = s.width * (j + 1) / (n + 1);
      final double cy = serpY(x, s);
      return Offset(x, onTop ? cy - kSerpHalf - kRing : cy + kSerpHalf + kRing);
    }
    if (shape == 'rect') {""", "seat centres")

swap("""  // v7: which way a chair's back faces - away from the table.
  double seatAngle(int i) {
    if (shape == 'sweetheart') return math.pi; // chairs below, facing the table
    if (shape == 'row') return 0; // a ceremony row faces forward
    if (shape == 'rect') {""",
     """  // v10: the serpentine band - half its thickness and its centre line.
  static const double kSerpHalf = 30;
  static double serpY(double x, Size s) =>
      s.height / 2 + (s.height / 2 - kSerpHalf - 6) * math.sin(2 * math.pi * x / s.width);

  // v7: which way a chair's back faces - away from the table.
  double seatAngle(int i) {
    if (shape == 'sweetheart') return math.pi; // chairs below, facing the table
    if (shape == 'row') return 0; // a ceremony row faces forward
    if (shape == 'king') {
      if (i == 0) return -math.pi / 2;
      if (i == 1) return math.pi / 2;
      final int rest = seats - 2;
      final int top = rest - (rest ~/ 2);
      return (i - 2) < top ? 0 : math.pi;
    }
    if (shape == 'serp') {
      final int top = seats - (seats ~/ 2);
      return i < top ? 0 : math.pi;
    }
    if (shape == 'rect') {""", "seat angles")

swap("""      seats: seats.clamp(1, shape == 'row' ? 30 : 20).toInt(),""",
     """      seats: seats.clamp(1, shape == 'row' || shape == 'king' || shape == 'serp' ? 30 : 20).toInt(),""",
     "fromMap clamp")

# the serpentine draws itself
swap("""    // Captured in a final: the builder below must not see the later
    // reassignments of `body` (it would return the wrapper that contains it).
    final Widget plate =
        SizedBox(width: sz.width, height: sz.height, child: body);""",
     """    // v10: a serpentine is a painted band, not a box.
    if (t.shape == 'serp') {
      body = Stack(clipBehavior: Clip.none, children: <Widget>[
        CustomPaint(
          size: sz,
          painter: _SerpPainter(
              border: warns.isNotEmpty ? rose : (sel ? plum : const Color(0xFFD8C7A6)),
              width: sel ? 2.5 : 1.6),
        ),
        Positioned.fill(
          child: Center(
            child: Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
              Text(t.name, textAlign: TextAlign.center, maxLines: 1, overflow: TextOverflow.ellipsis, style: _serif(size: 17, height: 1)),
              Text('$filled of ${t.seats}',
                  style: TextStyle(fontSize: 11, color: full ? vGreen : muted, fontWeight: FontWeight.w700)),
              if (_mealLine(t.id).isNotEmpty)
                Text(_mealLine(t.id), maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 9.5, color: Color(0xFF8A6A2F), fontWeight: FontWeight.w700)),
            ]),
          ),
        ),
      ]);
    }
    // Captured in a final: the builder below must not see the later
    // reassignments of `body` (it would return the wrapper that contains it).
    final Widget plate =
        SizedBox(width: sz.width, height: sz.height, child: body);""",
     "serpentine body")

swap("""      if (t.shape == 'round') {
        s.write(
            '<circle cx="$cx" cy="$cy" r="${sz.width / 2}" fill="#fff" stroke="#52284F" stroke-width="1.5"/>');
      } else {""",
     """      if (t.shape == 'round') {
        s.write(
            '<circle cx="$cx" cy="$cy" r="${sz.width / 2}" fill="#fff" stroke="#52284F" stroke-width="1.5"/>');
      } else if (t.shape == 'serp') {
        final StringBuffer d = StringBuffer();
        for (int k = 0; k <= 24; k++) {
          final double px = sz.width * k / 24;
          d.write('${k == 0 ? 'M' : 'L'}${(t.x + px).toStringAsFixed(1)} ${(t.y + _SeatTable.serpY(px, sz)).toStringAsFixed(1)} ');
        }
        s.write(
            '<path d="$d" fill="none" stroke="#52284F" stroke-width="${_SeatTable.kSerpHalf * 2 + 1.5}" stroke-linecap="round"/>'
            '<path d="$d" fill="none" stroke="#fff" stroke-width="${_SeatTable.kSerpHalf * 2 - 1.5}" stroke-linecap="round"/>');
      } else {""", "print serpentine")

swap("""enum _Tick { none, select, light, medium }
""", """// v10: the serpentine band. Three plates like the boxes: shadow, rim, top.
class _SerpPainter extends CustomPainter {
  const _SerpPainter({required this.border, required this.width});
  final Color border;
  final double width;

  Path _path(Size s) {
    final Path p = Path();
    for (int k = 0; k <= 40; k++) {
      final double x = s.width * k / 40;
      final double y = _SeatTable.serpY(x, s);
      if (k == 0) {
        p.moveTo(x, y);
      } else {
        p.lineTo(x, y);
      }
    }
    return p;
  }

  @override
  void paint(Canvas canvas, Size size) {
    final Path p = _path(size);
    const double band = _SeatTable.kSerpHalf * 2;
    canvas.save();
    canvas.translate(0, 4);
    canvas.drawPath(p, Paint()..color = const Color(0xFF3D1C3B).withOpacity(.14)..style = PaintingStyle.stroke..strokeWidth = band..strokeCap = StrokeCap.round);
    canvas.restore();
    canvas.drawPath(p, Paint()..color = border..style = PaintingStyle.stroke..strokeWidth = band + width * 2..strokeCap = StrokeCap.round);
    canvas.drawPath(
        p,
        Paint()
          ..shader = const LinearGradient(colors: <Color>[Colors.white, Color(0xFFFBF7F0), Color(0xFFEFE4D2)]).createShader(Offset.zero & size)
          ..style = PaintingStyle.stroke
          ..strokeWidth = band
          ..strokeCap = StrokeCap.round);
    // the inner rim the boxes have, as two thin lines along the band's edges
    final Paint rim = Paint()
      ..color = const Color(0xFFE6D6B8).withOpacity(.9)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;
    for (final double off in <double>[-(_SeatTable.kSerpHalf - 5), _SeatTable.kSerpHalf - 5]) {
      final Path e = Path();
      for (int k = 0; k <= 40; k++) {
        final double x = size.width * k / 40;
        final double y = _SeatTable.serpY(x, size) + off;
        if (k == 0) {
          e.moveTo(x, y);
        } else {
          e.lineTo(x, y);
        }
      }
      canvas.drawPath(e, rim);
    }
  }

  @override
  bool shouldRepaint(_SerpPainter old) => old.border != border || old.width != width;
}

enum _Tick { none, select, light, medium }
""", "serpentine painter")

# ---------------------------------------------------------------- 3. the processional
swap("""  Widget _layoutBtn(bool wide) {""",
     r'''  // v10: who walks when. Lives on the ceremony doc; read when the sheet opens.
  static const List<List<String>> kProcTypical = <List<String>>[
    <String>['Officiant', 'takes their place'],
    <String>['Grandparents', 'seated in the front rows'],
    <String>['Parents of partner 1', 'seated front row, aisle side'],
    <String>['Parents of partner 2', 'seated front row, aisle side'],
    <String>['Partner 2 and their party', 'to the front'],
    <String>['Wedding party', 'in pairs, or one side then the other'],
    <String>['Ring bearer', ''],
    <String>['Flower girl', ''],
    <String>['Partner 1', 'with whoever walks them - everyone stands'],
  ];

  Future<void> _processionalSheet() async {
    if (_plan != 'ceremony') {
      _switchPlan('ceremony');
    }
    List<Map<String, dynamic>> steps = <Map<String, dynamic>>[];
    try {
      final DocumentSnapshot<Map<String, dynamic>> d = await _planRef('ceremony').get();
      if (d.data()?['processional'] is List) {
        for (final dynamic x in d.data()!['processional'] as List) {
          if (x is Map) steps.add(Map<String, dynamic>.from(x));
        }
      }
    } catch (_) {}
    if (!mounted) return;
    Future<void> save() async {
      try {
        await _planRef('ceremony').set(<String, dynamic>{
          'processional': steps,
          'updatedAt': FieldValue.serverTimestamp(),
        }, SetOptions(merge: true));
        _scheduleShare();
      } catch (e) {
        _toast('Could not save the processional: ' + _errText(e));
      }
    }

    Future<void> edit(StateSetter setS, [int? idx]) async {
      final TextEditingController who = TextEditingController(text: idx == null ? '' : (steps[idx]['who'] ?? '').toString());
      final TextEditingController note = TextEditingController(text: idx == null ? '' : (steps[idx]['note'] ?? '').toString());
      final bool? ok = await showDialog<bool>(
        context: context,
        builder: (BuildContext ctx) => AlertDialog(
          backgroundColor: ivory,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: Text(idx == null ? 'Add a step' : 'Edit step', style: const TextStyle(color: plum, fontSize: 17, fontWeight: FontWeight.w800)),
          content: Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
            TextField(controller: who, autofocus: true, textCapitalization: TextCapitalization.sentences, style: const TextStyle(color: ink), decoration: _deco('Who', 'e.g. Grandparents')),
            const SizedBox(height: 10),
            TextField(controller: note, style: const TextStyle(color: ink), decoration: _deco('Note (optional)', 'to the front row, aisle side')),
          ]),
          actions: <Widget>[
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel', style: TextStyle(color: muted))),
            FilledButton(style: FilledButton.styleFrom(backgroundColor: gold, foregroundColor: plum), onPressed: () => Navigator.pop(ctx, true), child: const Text('Save')),
          ],
        ),
      );
      if (ok != true || who.text.trim().isEmpty) return;
      setS(() {
        if (idx == null) {
          steps.add(<String, dynamic>{'who': who.text.trim(), 'note': note.text.trim()});
        } else {
          steps[idx] = <String, dynamic>{'who': who.text.trim(), 'note': note.text.trim()};
        }
      });
      await save();
    }

    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: ivory,
      isScrollControlled: true,
      constraints: const BoxConstraints(maxWidth: 560),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setS) => SafeArea(
          child: SizedBox(
            height: MediaQuery.of(ctx2).size.height * .82,
            child: Column(children: <Widget>[
              Padding(
                padding: const EdgeInsets.fromLTRB(22, 18, 14, 8),
                child: Row(children: <Widget>[
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                      Text('The processional', style: _serif(size: 24)),
                      const Text('Who walks in, in what order. Drag to reorder. The front rows on the plan are where they end up.',
                          style: TextStyle(fontSize: 12.5, color: muted, height: 1.4)),
                    ]),
                  ),
                  IconButton(icon: const Icon(Icons.close_rounded, color: muted), onPressed: () => Navigator.pop(ctx2)),
                ]),
              ),
              Divider(height: 1, color: gold.withOpacity(.35)),
              Expanded(
                child: steps.isEmpty
                    ? Center(
                        child: Padding(
                          padding: const EdgeInsets.all(28),
                          child: Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
                            const Icon(Icons.directions_walk_rounded, color: gold, size: 40),
                            const SizedBox(height: 12),
                            const Text('Start from the usual order', style: TextStyle(color: plum, fontSize: 16, fontWeight: FontWeight.w800)),
                            const SizedBox(height: 6),
                            const Text('Officiant, grandparents, parents, the wedding party, the little ones, then the entrance. Change any of it.',
                                textAlign: TextAlign.center, style: TextStyle(fontSize: 13, color: muted, height: 1.45)),
                            const SizedBox(height: 16),
                            FilledButton.icon(
                              style: FilledButton.styleFrom(backgroundColor: gold, foregroundColor: plumDeep, elevation: 0),
                              onPressed: () async {
                                setS(() => steps = <Map<String, dynamic>>[
                                      for (final List<String> p in kProcTypical) <String, dynamic>{'who': p[0], 'note': p[1]}
                                    ]);
                                await save();
                              },
                              icon: const Icon(Icons.auto_awesome_rounded, size: 16),
                              label: const Text('Use a typical order', style: TextStyle(fontWeight: FontWeight.w800)),
                            ),
                            TextButton(onPressed: () => edit(setS), child: const Text('Or add one step', style: TextStyle(color: plum, fontWeight: FontWeight.w700))),
                          ]),
                        ),
                      )
                    : ReorderableListView.builder(
                        padding: const EdgeInsets.fromLTRB(14, 10, 14, 10),
                        itemCount: steps.length,
                        onReorder: (int a, int b) async {
                          setS(() {
                            if (b > a) b--;
                            final Map<String, dynamic> it = steps.removeAt(a);
                            steps.insert(b, it);
                          });
                          await save();
                        },
                        itemBuilder: (BuildContext ic, int i) => Container(
                          key: ValueKey<String>('proc$i${steps[i]['who']}'),
                          margin: const EdgeInsets.only(bottom: 6),
                          padding: const EdgeInsets.fromLTRB(12, 10, 6, 10),
                          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12), border: Border.all(color: goldLine)),
                          child: Row(children: <Widget>[
                            Container(
                              width: 24,
                              height: 24,
                              alignment: Alignment.center,
                              decoration: const BoxDecoration(color: plum, shape: BoxShape.circle),
                              child: Text('${i + 1}', style: const TextStyle(color: gold, fontSize: 11, fontWeight: FontWeight.w800)),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: _Press(
                                onTap: () => edit(setS, i),
                                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                                  Text((steps[i]['who'] ?? '').toString(), style: const TextStyle(color: ink, fontSize: 14, fontWeight: FontWeight.w700)),
                                  if ((steps[i]['note'] ?? '').toString().isNotEmpty)
                                    Text((steps[i]['note'] ?? '').toString(), style: const TextStyle(fontSize: 11.5, color: muted)),
                                ]),
                              ),
                            ),
                            IconButton(
                              icon: const Icon(Icons.close_rounded, size: 16, color: muted),
                              onPressed: () async {
                                setS(() => steps.removeAt(i));
                                await save();
                              },
                            ),
                            const Icon(Icons.drag_handle_rounded, color: muted, size: 18),
                          ]),
                        ),
                      ),
              ),
              Divider(height: 1, color: gold.withOpacity(.35)),
              Padding(
                padding: const EdgeInsets.fromLTRB(18, 10, 18, 12),
                child: Row(children: <Widget>[
                  OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(foregroundColor: plum, side: BorderSide(color: gold.withOpacity(.8))),
                    onPressed: () => edit(setS),
                    icon: const Icon(Icons.add_rounded, size: 17),
                    label: const Text('Add a step', style: TextStyle(fontWeight: FontWeight.w800)),
                  ),
                  const Spacer(),
                  Text('${steps.length} step${steps.length == 1 ? '' : 's'} · prints on the usher list', style: const TextStyle(fontSize: 11.5, color: muted)),
                ]),
              ),
            ]),
          ),
        ),
      ),
    );
  }

  Widget _procBtn(bool wide) {
    return _Press(
      tick: _Tick.light,
      onTap: _processionalSheet,
      child: Container(
        padding: EdgeInsets.symmetric(horizontal: wide ? 14 : 10, vertical: 11),
        decoration: BoxDecoration(borderRadius: BorderRadius.circular(10), border: Border.all(color: gold)),
        child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
          const Icon(Icons.directions_walk_rounded, size: 16, color: plum),
          const SizedBox(width: 6),
          Text(wide ? 'Processional' : 'Walk',
              style: const TextStyle(color: plum, fontSize: 13, fontWeight: FontWeight.w700)),
        ]),
      ),
    );
  }

  Widget _layoutBtn(bool wide) {''', "processional sheet")

swap("""      if (_plan == 'ceremony') ...<Widget>[
        _layoutBtn(wide),
        const SizedBox(width: 8),
      ],""",
     """      if (_plan == 'ceremony') ...<Widget>[
        _layoutBtn(wide),
        const SizedBox(width: 8),
        _procBtn(wide),
        const SizedBox(width: 8),
      ],""", "header processional button")

# the usher list prints the processional first; it reads the doc synchronously from the last share payload cache
swap("""    b.write('<h1>Usher list</h1><div class="sub">${_subLine()}</div>');
    final List<String> sides = <String>[""",
     """    b.write('<h1>Usher list</h1><div class="sub">${_subLine()}</div>');
    if (_procCache.isNotEmpty) {
      b.write('<h2>The processional</h2><ol style="font-family:Arial,sans-serif;font-size:13px;line-height:1.7">');
      for (final Map<String, dynamic> st in _procCache) {
        final String n = (st['note'] ?? '').toString();
        b.write('<li><b>${_esc((st['who'] ?? '').toString())}</b>${n.isEmpty ? '' : ' - ' + _esc(n)}</li>');
      }
      b.write('</ol>');
    }
    final List<String> sides = <String>[""", "usher print processional")

# keep a copy of the processional from the plan stream so the print has it
swap("""      setState(() {
        _canvasW = cv['w'] is num ? (cv['w'] as num).toDouble() : 1600;
        _canvasH = cv['h'] is num ? (cv['h'] as num).toDouble() : 1000;
        _venueName = (d['venueName'] ?? '').toString();
        _tables = ts;
        _areas = ar;""",
     """      setState(() {
        _canvasW = cv['w'] is num ? (cv['w'] as num).toDouble() : 1600;
        _canvasH = cv['h'] is num ? (cv['h'] as num).toDouble() : 1000;
        _venueName = (d['venueName'] ?? '').toString();
        _tables = ts;
        _areas = ar;
        if (_plan == 'ceremony') {
          _procCache = <Map<String, dynamic>>[
            if (d['processional'] is List)
              for (final dynamic x in d['processional'] as List)
                if (x is Map) Map<String, dynamic>.from(x)
          ];
        }""", "processional cache")

swap("""  String _shopFilter = 'tobuy';""" if False else """  String _filter = 'unseated';""",
     """  String _filter = 'unseated';
  List<Map<String, dynamic>> _procCache = <Map<String, dynamic>>[]; // v10""", "processional field")

OUT.write_text(s, encoding="utf-8", newline="\n")
print(f"wrote {OUT} ({len(s):,} chars)")
