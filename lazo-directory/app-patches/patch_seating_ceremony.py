"""patch_seating_ceremony.py - JC-LAZO-SEAT-0920-009
Ceremony seating that knows about sides. The v6 ceremony plan was free rows on
a canvas; couples want "her family left, his family right, parents in the
front row". This adds, to the SeatingChart custom widget:
  - Lay out rows: a sheet (rows per side, seats per row, centre aisle or one
    block) that builds the whole ceremony - altar, aisle, rows on both sides -
    with the sides named after the couple and the first rows reserved.
  - Rows carry side / row / reserved; the inspector edits them with chips.
  - Row labels on the plan say the side and the reservation.
  - The guest rail on the ceremony plan shows each guest's side (from the
    guest card) and can filter by side; a guest seated across the aisle from
    their side gets the rule-warning pill on that row.
  - An Usher list print: rows by side, reserved rows, who sits where, and who
    has open seating on each side.
Anchor-and-assert. Nothing is written unless every anchor matches once.

  python app-patches\\patch_seating_ceremony.py [src] [out]
Default src app-patches\\Seating_master.txt, out ..._ceremony.txt. Paste the
output over the SeatingChart page's custom widget in FlutterFlow, test, publish.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Seating_master.txt"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else SRC.with_name(SRC.stem + "_ceremony.txt")
s = SRC.read_text(encoding="utf-8")
if "JC-LAZO-SEAT-0920-009" in s:
    raise SystemExit("already applied")


def swap(old, new, label, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"ABORT [{label}]: anchor matched {n} times, expected {count}")
    s = s.replace(old, new)
    print(f"  ok  {label}")


# ---------------------------------------------------------------- header
swap("// Build ID: JC-LAZO-SEAT-0915-008\n",
     "// Build ID: JC-LAZO-SEAT-0920-009\n"
     "// (v9: CEREMONY SIDES - Lay out rows builds altar, aisle and rows on both sides of the aisle, each side named after one of the couple, the first rows reserved (parents, grandparents); rows carry side / row / reserved, edited with chips in the inspector and shown on the row label; the rail on the ceremony plan shows each guest's side from their guest card and filters by it; a guest seated across the aisle from their side gets a warning pill on the row; an Usher list print lists rows by side with who sits where and who has open seating. base v8)\n",
     "header")

# ---------------------------------------------------------------- _SeatTable fields
swap("""    this.rotation = 0,
  });

  String id;
  String name;
  String shape; // round | rect | sweetheart | row
  int seats;
  double x;
  double y;
  double rotation; // degrees, long tables and rows
""", """    this.rotation = 0,
    this.side = '',
    this.row = 0,
    this.reserved = '',
  });

  String id;
  String name;
  String shape; // round | rect | sweetheart | row
  int seats;
  double x;
  double y;
  double rotation; // degrees, long tables and rows
  // v9: ceremony rows - which side of the aisle ('partner1' | 'partner2' |
  // '' for a single block), the row number from the front, and who the row
  // is held for ('Parents & immediate family', '' = open).
  String side;
  int row;
  String reserved;
""", "_SeatTable fields")

swap("""        'rotation': rotation,
      };
""", """        'rotation': rotation,
        'side': side,
        'row': row,
        'reserved': reserved,
      };
""", "_SeatTable.toMap")

swap("""      rotation: m['rotation'] is num ? (m['rotation'] as num).toDouble() : 0,
    );
  }
}
""", """      rotation: m['rotation'] is num ? (m['rotation'] as num).toDouble() : 0,
      side: (m['side'] ?? '').toString(),
      row: m['row'] is num ? (m['row'] as num).toInt() : 0,
      reserved: (m['reserved'] ?? '').toString(),
    );
  }
}
""", "_SeatTable.fromMap")

# ---------------------------------------------------------------- side helpers
swap("""  String _fld(String base) =>
      _plan == 'main' ? base : 'c' + base[0].toUpperCase() + base.substring(1);
""", """  String _fld(String base) =>
      _plan == 'main' ? base : 'c' + base[0].toUpperCase() + base.substring(1);

  // v9: the two sides of the aisle are named after the couple. The guest
  // card's side field is 'partner1' / 'partner2' / 'both'; partner 1 is the
  // first name in couples.names, partner 2 the second.
  String _sideFirstName(String s) {
    if (s != 'partner1' && s != 'partner2') return '';
    final List<String> parts =
        _coupleLabel.split(RegExp(r'\\s*(?:&|\\band\\b|\\+)\\s*'));
    final int i = s == 'partner1' ? 0 : 1;
    final String n = parts.length > i ? parts[i].trim() : '';
    if (n.isEmpty) return s == 'partner1' ? 'Partner 1' : 'Partner 2';
    return n.split(' ').first;
  }

  String _sideName(String s) {
    final String n = _sideFirstName(s);
    return n.isEmpty ? '' : '$n\\u2019s side';
  }

  String _sideTag(_Guest g) => _plan == 'ceremony' ? _sideName(g.side) : '';

  int _sideCount(String side) => _guests.values
      .where((_Guest g) => _coming(g) && g.side == side)
      .length;

  String _rowLabel(_SeatTable t, int filled) {
    final List<String> p = <String>[t.name];
    if (_plan == 'ceremony' && t.side.isNotEmpty) p.add(_sideName(t.side));
    if (t.reserved.isNotEmpty) p.add('Reserved \\u00b7 ${t.reserved}');
    p.add('$filled of ${t.seats}');
    return p.join('  \\u00b7  ');
  }
""", "side helpers")

# ---------------------------------------------------------------- plan switch resets a side filter
swap("""      _pickedParty = '';
      _fitted = false;
      _undo.clear();
""", """      _pickedParty = '';
      _fitted = false;
      _undo.clear();
      if (_filter.startsWith('side')) {
        _filter = 'unseated';
      }
""", "_switchPlan filter reset")

# ---------------------------------------------------------------- row label on the plan
swap("""                ? Text('${t.name}  \\u00b7  $filled of ${t.seats}',""",
     """                ? Text(_rowLabel(t, filled),""", "row label")

# ---------------------------------------------------------------- inspector: side + reserved
swap("""          ]),
          _label('SEATS'),
          Row(children: <Widget>[
            _roundBtn(Icons.remove_rounded, () async {""",
     """          ]),
          if (t.shape == 'row' && _plan == 'ceremony') ...<Widget>[
            _label('SIDE OF THE AISLE'),
            Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
              _chip(_sideName('partner1'), t.side == 'partner1', () {
                _pushUndo();
                t.side = 'partner1';
                poke();
                _scheduleSave();
              }),
              _chip(_sideName('partner2'), t.side == 'partner2', () {
                _pushUndo();
                t.side = 'partner2';
                poke();
                _scheduleSave();
              }),
              _chip('Either', t.side.isEmpty, () {
                _pushUndo();
                t.side = '';
                poke();
                _scheduleSave();
              }),
            ]),
            _label('RESERVED FOR'),
            Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
              for (final String r in const <String>[
                'Parents & immediate family',
                'Grandparents & family',
                'Wedding party',
              ])
                _chip(r, t.reserved == r, () {
                  _pushUndo();
                  t.reserved = t.reserved == r ? '' : r;
                  poke();
                  _scheduleSave();
                }),
              _chip('Open', t.reserved.isEmpty, () {
                _pushUndo();
                t.reserved = '';
                poke();
                _scheduleSave();
              }),
            ]),
            const SizedBox(height: 8),
            TextFormField(
              key: ValueKey<String>('res:${t.id}'),
              initialValue: t.reserved,
              textCapitalization: TextCapitalization.sentences,
              onChanged: (String v) {
                t.reserved = v.trim();
                poke();
                _scheduleSave();
              },
              style: const TextStyle(color: ink, fontSize: 13.5),
              decoration: _deco('Or write your own', 'e.g. Bride\\u2019s grandparents'),
            ),
          ],
          _label('SEATS'),
          Row(children: <Widget>[
            _roundBtn(Icons.remove_rounded, () async {""", "inspector side + reserved")

# ---------------------------------------------------------------- guest row shows the side
swap("""                  if (t != null || declined || pending || g.note.isNotEmpty)
                    Text(
                        <String>[
                          if (t != null) '${t.name} \\u00b7 seat ${g.seat + 1}',
""", """                  if (t != null ||
                      declined ||
                      pending ||
                      g.note.isNotEmpty ||
                      _sideTag(g).isNotEmpty)
                    Text(
                        <String>[
                          if (t != null) '${t.name} \\u00b7 seat ${g.seat + 1}',
                          if (_sideTag(g).isNotEmpty) _sideTag(g),
""", "guest row side")

# ---------------------------------------------------------------- rail filter by side
swap("""      if (_filter == 'seated' && !seated) {
        return false;
      }
""", """      if (_filter == 'seated' && !seated) {
        return false;
      }
      if (_filter == 'side1' && g.side != 'partner1') {
        return false;
      }
      if (_filter == 'side2' && g.side != 'partner2') {
        return false;
      }
""", "rail side filter")

swap("""            _filterChip('all', 'All', _comingCount, poke),
""", """            _filterChip('all', 'All', _comingCount, poke),
            if (_plan == 'ceremony') ...<Widget>[
              const SizedBox(width: 6),
              _filterChip('side1', _sideFirstName('partner1'),
                  _sideCount('partner1'), poke),
              const SizedBox(width: 6),
              _filterChip('side2', _sideFirstName('partner2'),
                  _sideCount('partner2'), poke),
            ],
""", "rail side chips")

# ---------------------------------------------------------------- warning: across the aisle
swap("""    // A party split across tables is worth a nudge even without a rule.
""", """    // v9: a guest seated across the aisle from the side on their guest card.
    if (_plan == 'ceremony') {
      for (final _SeatTable t in _tables) {
        if (t.side.isEmpty) {
          continue;
        }
        _occ(t.id).forEach((int seat, String gid) {
          final _Guest? g = _guests[gid];
          if (g == null) {
            return;
          }
          if ((g.side == 'partner1' || g.side == 'partner2') &&
              g.side != t.side) {
            add(t.id,
                '${g.name} is on ${_sideName(g.side)} on their guest card');
          }
        });
      }
    }
    // A party split across tables is worth a nudge even without a rule.
""", "aisle warning")

# ---------------------------------------------------------------- header button + more menu
swap("""      _planSwitch(),
      const SizedBox(width: 8),
      _addMenu(wide),
""", """      _planSwitch(),
      const SizedBox(width: 8),
      if (_plan == 'ceremony') ...<Widget>[
        _layoutBtn(wide),
        const SizedBox(width: 8),
      ],
      _addMenu(wide),
""", "header layout button")

swap("""          case 'renumber':
            _renumber();
            break;
""", """          case 'renumber':
            _renumber();
            break;
          case 'layout':
            _ceremonyLayoutSheet();
            break;
""", "more menu handler")

swap("""        _menuItem('venue', Icons.map_outlined, 'Venue and floor plan',""",
     """        if (_plan == 'ceremony')
          _menuItem('layout', Icons.grid_view_rounded, 'Lay out the ceremony',
              'Rows per side, seats per row, the aisle'),
        _menuItem('venue', Icons.map_outlined, 'Venue and floor plan',""", "more menu item")

swap("""                                  : 'Add rows of seats, an altar or arch, and an aisle. Seat the front rows - family, the wedding party - and leave the rest open.',""",
     """                                  : 'Tap Lay out rows for rows on both sides of the aisle, one side for each of you. Reserve the front rows for parents and family, seat the people who matter there, and leave the rest open.',""",
     "empty-state copy")

# ---------------------------------------------------------------- print: usher list
swap("""        _menuItem('caterer', Icons.restaurant_rounded, 'Caterer sheet',
            'Meals and notes per table'),
""", """        _menuItem('caterer', Icons.restaurant_rounded, 'Caterer sheet',
            'Meals and notes per table'),
        if (_plan == 'ceremony')
          _menuItem('usher', Icons.groups_rounded, 'Usher list',
              'Rows by side, reserved rows, who sits where'),
""", "print menu item")

swap("""      case 'caterer':
        h = _catererHtml();
        break;
""", """      case 'caterer':
        h = _catererHtml();
        break;
      case 'usher':
        h = _usherHtml();
        break;
""", "print dispatch")

# ---------------------------------------------------------------- the new methods
NEW = r'''
  // ---------------- v9: ceremony sides ----------------

  Widget _layoutBtn(bool wide) {
    return _Press(
      tick: _Tick.light,
      onTap: _ceremonyLayoutSheet,
      child: Container(
        padding: EdgeInsets.symmetric(horizontal: wide ? 14 : 10, vertical: 11),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: gold),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
          const Icon(Icons.grid_view_rounded, size: 16, color: plum),
          const SizedBox(width: 6),
          Text(wide ? 'Lay out rows' : 'Rows',
              style: const TextStyle(
                  color: plum, fontSize: 13, fontWeight: FontWeight.w700)),
        ]),
      ),
    );
  }

  // Rows per side, seats per row, an aisle or one block. Builds the whole
  // ceremony in one go; anything already on the plan is replaced after a
  // confirm, and its guests go back to the list.
  Future<void> _ceremonyLayoutSheet() async {
    if (_plan != 'ceremony') {
      _switchPlan('ceremony');
    }
    int rows = 8;
    int seats = 8;
    bool aisle = true;
    final List<_SeatTable> existing = _tables.where((_SeatTable t) => t.shape == 'row').toList();
    if (existing.isNotEmpty) {
      rows = existing.map((_SeatTable t) => t.row).fold<int>(0, math.max);
      if (rows == 0) rows = existing.length;
      seats = existing.first.seats;
      aisle = existing.any((_SeatTable t) => t.side.isNotEmpty);
    }
    final bool? go = await showModalBottomSheet<bool>(
      context: context,
      backgroundColor: ivory,
      isScrollControlled: true,
      constraints: const BoxConstraints(maxWidth: 520),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setS) => SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(22, 18, 22, 22),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(children: <Widget>[
                  Expanded(child: Text('Lay out the ceremony', style: _serif(size: 24))),
                  IconButton(
                      icon: const Icon(Icons.close_rounded, color: muted),
                      onPressed: _h(() => Navigator.pop(ctx2, false))),
                ]),
                const Text(
                    'Rows of seats facing the altar. With a centre aisle, the left rows are one of you and the right rows the other, named after you both - change any row’s side later. The front rows start reserved for parents and family.',
                    style: TextStyle(fontSize: 13, color: muted, height: 1.45)),
                const SizedBox(height: 14),
                _label('AISLE'),
                Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
                  _chip('Centre aisle · two sides', aisle, () => setS(() => aisle = true)),
                  _chip('One block · no sides', !aisle, () => setS(() => aisle = false)),
                ]),
                if (aisle) ...<Widget>[
                  const SizedBox(height: 8),
                  Text(
                      'Left: ${_sideName('partner1')}   ·   Right: ${_sideName('partner2')}',
                      style: const TextStyle(fontSize: 12.5, color: plum, fontWeight: FontWeight.w700)),
                ],
                _label(aisle ? 'ROWS PER SIDE' : 'ROWS'),
                Row(children: <Widget>[
                  _roundBtn(Icons.remove_rounded, () => setS(() => rows = math.max(1, rows - 1))),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 14),
                    child: Text('$rows', style: _serif(size: 28, height: 1)),
                  ),
                  _roundBtn(Icons.add_rounded, () => setS(() => rows = math.min(30, rows + 1))),
                ]),
                _label('SEATS PER ROW'),
                Row(children: <Widget>[
                  _roundBtn(Icons.remove_rounded, () => setS(() => seats = math.max(2, seats - 1))),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 14),
                    child: Text('$seats', style: _serif(size: 28, height: 1)),
                  ),
                  _roundBtn(Icons.add_rounded, () => setS(() => seats = math.min(kMaxRow, seats + 1))),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                        '${rows * seats * (aisle ? 2 : 1)} seats in all',
                        style: const TextStyle(fontSize: 12.5, color: muted)),
                  ),
                ]),
                const SizedBox(height: 18),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    style: FilledButton.styleFrom(
                        backgroundColor: plum,
                        foregroundColor: ivory,
                        elevation: 0,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                    onPressed: _h(() => Navigator.pop(ctx2, true), _Tick.medium),
                    child: Text(_tables.isEmpty ? 'Build the ceremony' : 'Rebuild the ceremony',
                        style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w800)),
                  ),
                ),
                if (_tables.isNotEmpty)
                  const Padding(
                    padding: EdgeInsets.only(top: 8),
                    child: Text(
                        'Rebuilding replaces the rows you have. Anyone seated on them goes back to the list.',
                        style: TextStyle(fontSize: 11.5, color: muted)),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
    if (go != true || !mounted) {
      return;
    }
    await _buildCeremonyLayout(rows, seats, aisle);
  }

  Future<void> _buildCeremonyLayout(int rows, int seats, bool aisle) async {
    _pushUndo();
    // Anyone on the old rows goes back to the list.
    final WriteBatch b = FirebaseFirestore.instance.batch();
    bool any = false;
    for (final _SeatTable t in _tables) {
      _occ(t.id).forEach((int seat, String gid) {
        _writeUnseat(b, gid);
        any = true;
      });
    }
    if (any) {
      await _commit(b);
    }
    const double margin = 80;
    const double aisleW = 70;
    const double gap = 28;
    const double step = 100; // row pitch: body, chairs, breathing room
    final double rowW = (seats * 40 + 24).clamp(120, 1300).toDouble();
    final Size altar = _Area.presetSize('altar');
    final double totalW =
        aisle ? margin * 2 + rowW * 2 + gap * 2 + aisleW : margin * 2 + rowW;
    final double y0 = 60 + altar.height + 70;
    final List<_SeatTable> ts = <_SeatTable>[];
    final List<_Area> areas =
        _areas.where((_Area a) => a.kind != 'altar' && a.kind != 'aisle').toList();
    areas.add(_Area(
        id: _newId('a'),
        kind: 'altar',
        label: _Area.presetLabel('altar'),
        x: (totalW - altar.width) / 2,
        y: 60,
        w: altar.width,
        h: altar.height));
    String reservedFor(int r) => r == 1
        ? 'Parents & immediate family'
        : (r == 2 ? 'Grandparents & family' : '');
    if (aisle) {
      final double leftX = margin;
      final double aisleX = leftX + rowW + gap;
      final double rightX = aisleX + aisleW + gap;
      areas.add(_Area(
          id: _newId('a'),
          kind: 'aisle',
          label: _Area.presetLabel('aisle'),
          x: aisleX,
          y: y0 - 20,
          w: aisleW,
          h: rows * step + 20));
      for (int r = 1; r <= rows; r++) {
        for (final String side in const <String>['partner1', 'partner2']) {
          ts.add(_SeatTable(
            id: _newId('t'),
            name: 'Row $r',
            shape: 'row',
            seats: seats,
            x: side == 'partner1' ? leftX : rightX,
            y: y0 + (r - 1) * step,
            side: side,
            row: r,
            reserved: reservedFor(r),
          ));
        }
      }
    } else {
      for (int r = 1; r <= rows; r++) {
        ts.add(_SeatTable(
          id: _newId('t'),
          name: 'Row $r',
          shape: 'row',
          seats: seats,
          x: margin,
          y: y0 + (r - 1) * step,
          row: r,
          reserved: reservedFor(r),
        ));
      }
    }
    setState(() {
      _tables = ts;
      _areas = areas;
      _canvasW = math.max(1600.0, totalW);
      _canvasH = math.max(1000.0, y0 + rows * step + 120);
      _sel = '';
      _fitted = false;
      _movedView = false;
    });
    _scheduleSave();
    _toast(aisle
        ? '$rows rows a side, ${_sideFirstName('partner1')} left and ${_sideFirstName('partner2')} right. Drag family into the front rows.'
        : '$rows rows of $seats. Drag family into the front rows.');
  }

  // The usher's page: rows by side, front to back, reserved rows named, and
  // who has open seating on each side.
  String _usherHtml() {
    final StringBuffer b = StringBuffer(_htmlHead(
        'Usher list - ${_coupleLabel.isEmpty ? 'our wedding' : _coupleLabel}',
        '.sides{display:flex;gap:28px;align-items:flex-start}.side{flex:1;min-width:0}'
            'h2{font-family:Georgia,serif;font-size:20px;color:#52284F;margin:18px 0 6px}'
            'table.u{width:100%;border-collapse:collapse;font-family:Arial,sans-serif;font-size:13px}'
            '.u td{padding:6px 8px;border-bottom:1px solid #F0E8DD;vertical-align:top}.u td.r{width:64px;color:#52284F;font-weight:700;white-space:nowrap}'
            '.u .res{display:inline-block;background:#F3E7CE;color:#8A6A2F;border-radius:999px;padding:1px 8px;font-size:11px;font-weight:700;margin-left:6px}'
            '.u .open{color:#6B5F72}.note{font-family:Arial,sans-serif;font-size:12px;color:#6B5F72;margin-top:10px}'));
    b.write('<h1>Usher list</h1><div class="sub">${_subLine()}</div>');
    final List<String> sides = <String>[
      if (_tables.any((_SeatTable t) => t.side == 'partner1')) 'partner1',
      if (_tables.any((_SeatTable t) => t.side == 'partner2')) 'partner2',
      if (_tables.any((_SeatTable t) => t.side.isEmpty)) '',
    ];
    b.write('<div class="sides">');
    for (final String side in sides) {
      final List<_SeatTable> rows = _tables
          .where((_SeatTable t) => t.side == side)
          .toList()
        ..sort((_SeatTable p, _SeatTable q) => p.y.compareTo(q.y));
      b.write('<div class="side"><h2>${side.isEmpty ? 'Seating' : _esc(_sideName(side))}</h2><table class="u">');
      for (final _SeatTable t in rows) {
        final Map<int, String> occ = _occ(t.id);
        final List<String> names = <String>[];
        for (int i = 0; i < t.seats; i++) {
          final String? gid = occ[i];
          if (gid != null) {
            names.add(_esc(_guests[gid]?.name ?? 'Guest'));
          }
        }
        b.write('<tr><td class="r">${_esc(t.name)}</td><td>');
        if (t.reserved.isNotEmpty) {
          b.write('<span class="res">${_esc(t.reserved)}</span> ');
        }
        b.write(names.isEmpty
            ? '<span class="open">${t.reserved.isEmpty ? 'Open seating' : 'Held - no names yet'}</span>'
            : names.join(', '));
        if (names.isNotEmpty && names.length < t.seats) {
          b.write(' <span class="open">· ${t.seats - names.length} open</span>');
        }
        b.write('</td></tr>');
      }
      if (side.isNotEmpty) {
        final List<String> open = _guests.values
            .where((_Guest g) => _coming(g) && g.side == side && _guestTableId(g).isEmpty)
            .map((_Guest g) => _esc(g.name))
            .toList()
          ..sort();
        b.write('<tr><td class="r">Open</td><td class="open">${open.isEmpty ? 'Everyone else on this side sits anywhere behind the reserved rows.' : open.join(', ')}</td></tr>');
      }
      b.write('</table></div>');
    }
    b.write('</div>');
    b.write('<p class="note">Guests marked “both” on their guest card may sit on either side. Reserved rows are held for the people named; ushers seat everyone else from the front open row back.</p>');
    b.write('</body></html>');
    return b.toString();
  }

  // ---------------- send to the planner ----------------
'''
swap("\n  // ---------------- send to the planner ----------------\n", NEW, "new methods")

OUT.write_text(s, encoding="utf-8", newline="\n")
print(f"wrote {OUT} ({len(s):,} chars)")
