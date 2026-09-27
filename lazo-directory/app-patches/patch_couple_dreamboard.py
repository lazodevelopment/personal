"""patch_couple_dreamboard.py - JC-LAZO-COUPLE-0920-BOARD-001
The dream board: a free canvas where the couple pins what they found - a
Pinterest pin, an Etsy listing, a photo from their phone - plus notes and
color swatches, and moves it all around. One document,
couples/{cid}/board/main {items: [{id, kind, url, src, title, text, color,
x, y, w, ar, z}], updatedAt}, saved half a second after the last move.

  - Pin from a link: paste any page URL; meetlazo.com/api/unfurl turns it
    into the picture and a caption (direct image URLs work as they are).
  - Pin a photo: upload from the device (Storage, same path the website
    gallery uses so the existing rules allow it).
  - Notes (a soft card of text) and color swatches (16 presets or a hex).
  - Drag anything; pinch or scroll to zoom; drag the corner to resize; tap
    to select for Open source / Edit / Bring to front / Remove.
  - Share the board: pictures, notes and colors as a page to the florist,
    planner and photographer through the send sheet.
  - On the rail, the phone grid and June's open map ("open the dream board").

Applies on top of Couple_master_shopping.txt -> Couple_master_board.txt.
Anchor-and-assert.
  python app-patches\\patch_couple_dreamboard.py [src] [out]
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Couple_master_shopping.txt"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else SRC.with_name(SRC.stem.replace("_shopping", "") + "_board.txt")
s = SRC.read_text(encoding="utf-8")
if "JC-LAZO-COUPLE-0920-BOARD-001" in s:
    raise SystemExit("already applied")


def swap(old, new, label, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"ABORT [{label}]: anchor matched {n} times, expected {count}")
    s = s.replace(old, new)
    print(f"  ok  {label}")


# 1. the view
swap("""  dayof,
  shopping
}
""", """  dayof,
  shopping,
  board
}
""", "enum")

swap("""    if (_view == _View.shopping) return _shoppingScreen(couple);
""", """    if (_view == _View.shopping) return _shoppingScreen(couple);
    if (_view == _View.board) return _boardScreen(couple);
""", "body switch")

# 2. the rails
swap("""          _railNavRow('Shopping list', Icons.shopping_bag_rounded, _View.shopping),
        ],
""", """          _railNavRow('Shopping list', Icons.shopping_bag_rounded, _View.shopping),
          _railNavRow('Dream board', Icons.auto_awesome_mosaic_rounded, _View.board),
        ],
""", "desktop rail")

swap("""      <dynamic>[
        'Shopping',
        Icons.shopping_bag_rounded,
        () => setState(() => _view = _View.shopping),
        _View.shopping
      ],
""", """      <dynamic>[
        'Shopping',
        Icons.shopping_bag_rounded,
        () => setState(() => _view = _View.shopping),
        _View.shopping
      ],
      <dynamic>[
        'Dream board',
        Icons.auto_awesome_mosaic_rounded,
        () => setState(() => _view = _View.board),
        _View.board
      ],
""", "phone grid")

# 3. June
swap("""    <String>['shopping', 'Shopping list', 'shopping|shopping list|things to buy|to buy|supplies|decor list'],
""", """    <String>['shopping', 'Shopping list', 'shopping|shopping list|things to buy|to buy|supplies|decor list'],
    <String>['board', 'Dream board', 'dream board|mood board|moodboard|inspiration|pinterest|vision board|inspo'],
""", "June open map")

swap("""      case 'shopping':
        setState(() => _view = _View.shopping);
        break;
""", """      case 'shopping':
        setState(() => _view = _View.shopping);
        break;
      case 'board':
        setState(() => _view = _View.board);
        break;
""", "June go")

swap("""home, vendors, browse, messages, dayof, guests, seating, music, website, registry, shopping, account. '""",
     """home, vendors, browse, messages, dayof, guests, seating, music, website, registry, shopping, board, account. '
      'Dream board is a movable inspiration board: pictures pinned from any link (Pinterest, Etsy, a blog) or uploaded, notes and color swatches, shareable to the florist, planner and photographer. '""",
     "June app map")

# 4. the screen, next to the shopping screen
swap("""  // ---- JC-LAZO-COUPLE-0920-SHOP-001: the shopping list ----""",
     r'''  // ---- JC-LAZO-COUPLE-0920-BOARD-001: the dream board ----

  DocumentReference<Map<String, dynamic>> get _boardRef =>
      _coupleRef.collection('board').doc('main');

  static const double kBoardW = 2000;
  static const double kBoardH = 1400;
  static const List<String> kBoardColors = <String>[
    'F6E7E4', 'E8C4BF', 'C97C7C', 'A64D4D', 'F3EBDD', 'D9B77C', 'B08D3E', '8A6A2F',
    'E7EFE6', 'A8C0A0', '5B7553', '2F5D50', 'E6EEF5', '9FB8CF', '4A6C8C', '1F2A44',
    'EFE9F5', 'C9B6E4', '7A5C99', '52284F', 'FFFFFF', 'D9D4CC', '6B6B66', '241E2B',
  ];

  List<Map<String, dynamic>> _bdItems = <Map<String, dynamic>>[];
  bool _bdLoaded = false;
  String _bdSel = '';
  bool _bdDragging = false;
  bool _bdBusy = false;
  Timer? _bdSaveT;
  final TransformationController _bdTc = TransformationController();
  int _bdLocalRev = 0; // bumps on every local change; remote snapshots older than our last save are ignored

  void _bdApplyRemote(Map<String, dynamic> d) {
    if (_bdDragging) return;
    final List<Map<String, dynamic>> next = <Map<String, dynamic>>[];
    if (d['items'] is List) {
      for (final dynamic it in d['items'] as List) {
        if (it is Map) next.add(Map<String, dynamic>.from(it));
      }
    }
    _bdItems = next;
    _bdLoaded = true;
  }

  void _bdSave() {
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
    });
  }

  double _bdScale() => _bdTc.value.getMaxScaleOnAxis();

  String _bdId() => 'b${DateTime.now().millisecondsSinceEpoch}${_bdItems.length}';

  int _bdTopZ() {
    int z = 0;
    for (final Map<String, dynamic> it in _bdItems) {
      final int iz = it['z'] is num ? (it['z'] as num).toInt() : 0;
      if (iz > z) z = iz;
    }
    return z;
  }

  // Somewhere free-ish in the current view: the centre, nudged for each item.
  Offset _bdSpot() {
    final int n = _bdItems.length;
    return Offset(200 + (n % 6) * 90.0, 160 + ((n ~/ 6) % 5) * 80.0);
  }

  void _bdAdd(Map<String, dynamic> it) {
    final Offset o = _bdSpot();
    it['id'] = _bdId();
    it['x'] = o.dx;
    it['y'] = o.dy;
    it['z'] = _bdTopZ() + 1;
    setState(() {
      _bdItems.add(it);
      _bdSel = it['id'].toString();
    });
    _bdSave();
  }

  Map<String, dynamic>? _bdById(String id) {
    for (final Map<String, dynamic> it in _bdItems) {
      if (it['id'] == id) return it;
    }
    return null;
  }

  Future<void> _bdAddLink() async {
    final TextEditingController c = TextEditingController();
    final bool? ok = await showDialog<bool>(
      context: context,
      builder: (BuildContext ctx) => AlertDialog(
        backgroundColor: ivory,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Text('Pin from a link',
            style: TextStyle(color: plum, fontSize: 17, fontWeight: FontWeight.w800)),
        content: Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
          TextField(
              controller: c,
              autofocus: true,
              keyboardType: TextInputType.url,
              style: const TextStyle(color: ink),
              decoration: _lightDeco('Paste the link', hint: 'A Pinterest pin, an Etsy listing, any page or picture')),
          const SizedBox(height: 8),
          const Text('We pull the picture and a caption from the page. Copy the link from the share button on Pinterest.',
              style: TextStyle(fontSize: 12, color: muted, height: 1.4)),
        ]),
        actions: <Widget>[
          TextButton(onPressed: _h(() => Navigator.pop(ctx, false)), child: const Text('Cancel', style: TextStyle(color: muted))),
          FilledButton(
              style: FilledButton.styleFrom(backgroundColor: gold, foregroundColor: plum),
              onPressed: _h(() => Navigator.pop(ctx, true)),
              child: const Text('Pin it')),
        ],
      ),
    );
    if (ok != true) return;
    String u = c.text.trim();
    if (u.isEmpty) return;
    if (!u.startsWith('http')) u = 'https://' + u;
    setState(() => _bdBusy = true);
    try {
      final httpc.Response r = await httpc
          .get(Uri.parse('https://meetlazo.com/api/unfurl?u=' + Uri.encodeComponent(u)))
          .timeout(const Duration(seconds: 15));
      final Map<String, dynamic> j = r.statusCode == 200 ? Map<String, dynamic>.from(jsonDecode(r.body) as Map) : <String, dynamic>{};
      final String img = (j['image'] ?? '').toString();
      if (img.isEmpty) {
        _bdAdd(<String, dynamic>{
          'kind': 'note',
          'text': (j['title'] ?? '').toString().isNotEmpty ? j['title'].toString() : u,
          'src': u,
          'color': 'F3EBDD',
          'w': 220.0,
          'ar': 1.4,
        });
        _toast('No picture on that page - pinned it as a note with the link.');
      } else {
        _bdAdd(<String, dynamic>{
          'kind': 'image',
          'url': img,
          'src': (j['url'] ?? u).toString(),
          'title': (j['title'] ?? '').toString(),
          'site': (j['site'] ?? '').toString(),
          'w': 260.0,
          'ar': 1.0,
        });
      }
    } catch (e) {
      _toast('Could not read that link: ' + e.toString());
    } finally {
      if (mounted) setState(() => _bdBusy = false);
    }
  }

  Future<void> _bdAddPhoto() async {
    try {
      final FilePickerResult? res = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: <String>['jpg', 'jpeg', 'png', 'webp'],
        withData: true,
        allowMultiple: true,
      );
      if (res == null || res.files.isEmpty) return;
      setState(() => _bdBusy = true);
      for (final PlatformFile f in res.files.take(6)) {
        final Uint8List? bytes = f.bytes;
        if (bytes == null || bytes.length > 8 * 1024 * 1024) continue;
        final String ext = f.name.contains('.') ? f.name.substring(f.name.lastIndexOf('.')).toLowerCase() : '.jpg';
        final String ctype = ext == '.png' ? 'image/png' : (ext == '.webp' ? 'image/webp' : 'image/jpeg');
        // The website gallery path: the storage rules already allow it.
        final Reference ref = FirebaseStorage.instance.ref('couples/$_uid/site/board${DateTime.now().millisecondsSinceEpoch}$ext');
        await ref.putData(bytes, SettableMetadata(contentType: ctype));
        final String url = await ref.getDownloadURL();
        _bdAdd(<String, dynamic>{'kind': 'image', 'url': url, 'src': '', 'title': '', 'site': '', 'w': 260.0, 'ar': 1.0});
      }
    } catch (e) {
      _toast(e.toString().contains('permission') || e.toString().contains('unauthorized')
          ? 'Photo upload isn’t permitted yet - storage rules need the couples/site path.'
          : 'Upload failed: ' + e.toString());
    } finally {
      if (mounted) setState(() => _bdBusy = false);
    }
  }

  Future<void> _bdAddNote([Map<String, dynamic>? existing]) async {
    final TextEditingController c = TextEditingController(text: (existing?['text'] ?? '').toString());
    String color = (existing?['color'] ?? 'F3EBDD').toString();
    final bool? ok = await showDialog<bool>(
      context: context,
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) => AlertDialog(
          backgroundColor: ivory,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: Text(existing == null ? 'Add a note' : 'Edit note',
              style: const TextStyle(color: plum, fontSize: 17, fontWeight: FontWeight.w800)),
          content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
            TextField(
                controller: c,
                autofocus: true,
                minLines: 2,
                maxLines: 6,
                textCapitalization: TextCapitalization.sentences,
                style: const TextStyle(color: ink),
                decoration: _lightDeco('The note', hint: 'Candlelight, long tables, no centrepieces taller than a wine glass')),
            const SizedBox(height: 10),
            Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
              for (final String k in const <String>['F3EBDD', 'F6E7E4', 'E7EFE6', 'E6EEF5', 'EFE9F5', 'FFFFFF'])
                _Press(
                  tick: _Tick.select,
                  onTap: () => setD(() => color = k),
                  child: Container(
                    width: 28,
                    height: 28,
                    decoration: BoxDecoration(
                        color: Color(int.parse('FF$k', radix: 16)),
                        shape: BoxShape.circle,
                        border: Border.all(color: color == k ? plum : goldLine, width: color == k ? 2.5 : 1)),
                  ),
                ),
            ]),
          ]),
          actions: <Widget>[
            TextButton(onPressed: _h(() => Navigator.pop(ctx2, false)), child: const Text('Cancel', style: TextStyle(color: muted))),
            FilledButton(
                style: FilledButton.styleFrom(backgroundColor: gold, foregroundColor: plum),
                onPressed: _h(() => Navigator.pop(ctx2, true)),
                child: const Text('Save')),
          ],
        ),
      ),
    );
    if (ok != true || c.text.trim().isEmpty) return;
    if (existing != null) {
      setState(() {
        existing['text'] = c.text.trim();
        existing['color'] = color;
      });
      _bdSave();
      return;
    }
    _bdAdd(<String, dynamic>{'kind': 'note', 'text': c.text.trim(), 'color': color, 'src': '', 'w': 220.0, 'ar': 1.3});
  }

  Future<void> _bdAddSwatch([Map<String, dynamic>? existing]) async {
    String color = (existing?['color'] ?? 'D9B77C').toString();
    final TextEditingController hexC = TextEditingController(text: color);
    final TextEditingController labelC = TextEditingController(text: (existing?['text'] ?? '').toString());
    final bool? ok = await showDialog<bool>(
      context: context,
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) => AlertDialog(
          backgroundColor: ivory,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: Text(existing == null ? 'Add a color' : 'Edit color',
              style: const TextStyle(color: plum, fontSize: 17, fontWeight: FontWeight.w800)),
          content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
            Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
              for (final String k in kBoardColors)
                _Press(
                  tick: _Tick.select,
                  onTap: () => setD(() {
                    color = k;
                    hexC.text = k;
                  }),
                  child: Container(
                    width: 30,
                    height: 30,
                    decoration: BoxDecoration(
                        color: Color(int.parse('FF$k', radix: 16)),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: color == k ? plum : goldLine, width: color == k ? 2.5 : 1)),
                  ),
                ),
            ]),
            const SizedBox(height: 10),
            Row(children: <Widget>[
              Container(
                  width: 34,
                  height: 34,
                  decoration: BoxDecoration(
                      color: Color(int.tryParse('FF${hexC.text.replaceAll('#', '')}', radix: 16) ?? 0xFFD9B77C),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: goldLine))),
              const SizedBox(width: 10),
              Expanded(
                child: TextField(
                    controller: hexC,
                    style: const TextStyle(color: ink),
                    onChanged: (String v) {
                      final String h = v.replaceAll('#', '').trim().toUpperCase();
                      if (RegExp(r'^[0-9A-F]{6}$').hasMatch(h)) setD(() => color = h);
                    },
                    decoration: _lightDeco('Hex', hint: 'D9B77C')),
              ),
            ]),
            const SizedBox(height: 10),
            TextField(
                controller: labelC,
                style: const TextStyle(color: ink),
                decoration: _lightDeco('Call it (optional)', hint: 'Dusty sage, bridesmaids')),
          ]),
          actions: <Widget>[
            TextButton(onPressed: _h(() => Navigator.pop(ctx2, false)), child: const Text('Cancel', style: TextStyle(color: muted))),
            FilledButton(
                style: FilledButton.styleFrom(backgroundColor: gold, foregroundColor: plum),
                onPressed: _h(() => Navigator.pop(ctx2, true)),
                child: const Text('Save')),
          ],
        ),
      ),
    );
    if (ok != true) return;
    if (existing != null) {
      setState(() {
        existing['color'] = color;
        existing['text'] = labelC.text.trim();
      });
      _bdSave();
      return;
    }
    _bdAdd(<String, dynamic>{'kind': 'swatch', 'color': color, 'text': labelC.text.trim(), 'src': '', 'w': 120.0, 'ar': 1.0});
  }

  Future<void> _bdShare(Map<String, dynamic> couple) async {
    if (_bdItems.isEmpty) {
      _toast('Pin a few things first.');
      return;
    }
    final String who = _coupleLabel(couple);
    final String when = _weddingDateLine(couple);
    final StringBuffer h = StringBuffer();
    final StringBuffer t = StringBuffer();
    t.writeln('DREAM BOARD${when.isEmpty ? '' : ' - $when'}');
    final List<Map<String, dynamic>> imgs = _bdItems.where((Map<String, dynamic> i) => i['kind'] == 'image').toList();
    final List<Map<String, dynamic>> notes = _bdItems.where((Map<String, dynamic> i) => i['kind'] == 'note').toList();
    final List<Map<String, dynamic>> sw = _bdItems.where((Map<String, dynamic> i) => i['kind'] == 'swatch').toList();
    if (sw.isNotEmpty) {
      h.write('<h2>Colors</h2><div style="display:flex;flex-wrap:wrap;gap:10px">');
      t.writeln('');
      t.writeln('COLORS');
      for (final Map<String, dynamic> i in sw) {
        final String c = (i['color'] ?? 'D9B77C').toString();
        final String l = (i['text'] ?? '').toString();
        h.write('<div style="text-align:center;font-size:12px;color:#6B5F72"><div style="width:64px;height:64px;border-radius:12px;background:#$c;border:1px solid #E6D6B8"></div>#$c${l.isEmpty ? '' : '<br>' + _esc(l)}</div>');
        t.writeln('#$c${l.isEmpty ? '' : ' - $l'}');
      }
      h.write('</div>');
    }
    if (notes.isNotEmpty) {
      h.write('<h2>Notes</h2><ul>');
      t.writeln('');
      t.writeln('NOTES');
      for (final Map<String, dynamic> i in notes) {
        final String src = (i['src'] ?? '').toString();
        h.write('<li>${_esc((i['text'] ?? '').toString())}${src.isEmpty ? '' : ' <a href="${_esc(src)}">link</a>'}</li>');
        t.writeln('- ${i['text'] ?? ''}${src.isEmpty ? '' : ' ($src)'}');
      }
      h.write('</ul>');
    }
    if (imgs.isNotEmpty) {
      h.write('<h2>Pictures</h2><div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px">');
      t.writeln('');
      t.writeln('PICTURES');
      for (final Map<String, dynamic> i in imgs) {
        final String u = (i['url'] ?? '').toString();
        final String src = (i['src'] ?? '').toString();
        final String cap = (i['title'] ?? '').toString();
        h.write('<div><a href="${_esc(src.isEmpty ? u : src)}"><img src="${_esc(u)}" style="width:100%;border-radius:10px;display:block" alt=""></a>${cap.isEmpty ? '' : '<div style="font-size:12px;color:#6B5F72;margin-top:4px">' + _esc(cap) + '</div>'}</div>');
        t.writeln('${cap.isEmpty ? '' : cap + ' - '}${src.isEmpty ? u : src}');
      }
      h.write('</div>');
    }
    await _sendToVendors(
      kind: 'board',
      title: 'dream board',
      fileName: 'Dream board.html',
      page: _printShell('Dream board', <String>[if (who.isNotEmpty) who, if (when.isNotEmpty) when].join(' · '), h.toString()),
      text: t.toString(),
      tags: <String>['florist', 'planner', 'photo'],
      note: 'Here’s our dream board - the look we’re going for. Tell us what’s realistic and what you’d change.',
      preview: '${imgs.length} picture${imgs.length == 1 ? '' : 's'}, ${notes.length} note${notes.length == 1 ? '' : 's'}, ${sw.length} color${sw.length == 1 ? '' : 's'}',
    );
  }

  Widget _boardScreen(Map<String, dynamic> couple) {
    return StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
      stream: _liveDoc('board:$_cid', () => _boardRef),
      initialData: _liveD['board:$_cid']?.latest,
      builder: (BuildContext c, AsyncSnapshot<DocumentSnapshot<Map<String, dynamic>>> sn) {
        if (sn.hasData) _bdApplyRemote(sn.data!.data() ?? <String, dynamic>{});
        final Map<String, dynamic>? sel = _bdSel.isEmpty ? null : _bdById(_bdSel);
        final bool empty = _bdItems.isEmpty;
        Widget tool(IconData ic, String label, VoidCallback go, {bool solid = false}) {
          return _Press(
            tick: _Tick.light,
            onTap: _bdBusy ? null : go,
            child: Container(
              margin: const EdgeInsets.only(right: 8),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
              decoration: BoxDecoration(
                color: solid ? gold : Colors.white.withOpacity(.12),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: solid ? gold : ivory.withOpacity(.35)),
              ),
              child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
                Icon(ic, size: 15, color: solid ? plumDeep : ivory),
                const SizedBox(width: 6),
                Text(label, style: TextStyle(color: solid ? plumDeep : ivory, fontSize: 12.5, fontWeight: FontWeight.w800)),
              ]),
            ),
          );
        }

        final List<Widget> sorted = <Widget>[];
        final List<Map<String, dynamic>> byZ = List<Map<String, dynamic>>.from(_bdItems)
          ..sort((Map<String, dynamic> a, Map<String, dynamic> b) =>
              ((a['z'] is num ? (a['z'] as num) : 0)).compareTo(b['z'] is num ? (b['z'] as num) : 0));
        for (final Map<String, dynamic> it in byZ) {
          sorted.add(_boardItem(it));
        }

        return Column(children: <Widget>[
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 8, 18, 0),
            child: _subHeader('Dream board',
                trailing: empty
                    ? null
                    : _Press(
                        onTap: () => _bdShare(couple),
                        child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
                          Icon(Icons.send_rounded, color: ivory.withOpacity(.9), size: 15),
                          const SizedBox(width: 4),
                          Text('Share', style: TextStyle(color: ivory.withOpacity(.9), fontSize: 12, fontWeight: FontWeight.w800)),
                        ]),
                      )),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 0, 18, 10),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(children: <Widget>[
                tool(Icons.link_rounded, 'Pin a link', _bdAddLink, solid: true),
                tool(Icons.add_photo_alternate_rounded, 'Photo', _bdAddPhoto),
                tool(Icons.sticky_note_2_rounded, 'Note', () => _bdAddNote()),
                tool(Icons.palette_rounded, 'Color', () => _bdAddSwatch()),
                if (_bdBusy)
                  const Padding(
                    padding: EdgeInsets.only(left: 4),
                    child: SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: gold)),
                  ),
              ]),
            ),
          ),
          if (sel != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(18, 0, 18, 8),
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(children: <Widget>[
                  if ((sel['src'] ?? '').toString().isNotEmpty)
                    tool(Icons.open_in_new_rounded, 'Open source', () async {
                      final Uri? u = Uri.tryParse(sel['src'].toString());
                      if (u != null && await canLaunchUrl(u)) await launchUrl(u, mode: LaunchMode.externalApplication);
                    }),
                  if (sel['kind'] == 'note') tool(Icons.edit_rounded, 'Edit', () => _bdAddNote(sel)),
                  if (sel['kind'] == 'swatch') tool(Icons.edit_rounded, 'Edit', () => _bdAddSwatch(sel)),
                  tool(Icons.flip_to_front_rounded, 'To front', () {
                    setState(() => sel['z'] = _bdTopZ() + 1);
                    _bdSave();
                  }),
                  tool(Icons.delete_outline_rounded, 'Remove', () {
                    final Map<String, dynamic> gone = Map<String, dynamic>.from(sel);
                    setState(() {
                      _bdItems.removeWhere((Map<String, dynamic> i) => i['id'] == gone['id']);
                      _bdSel = '';
                    });
                    _bdSave();
                    _toastUndo('Removed from the board.', () async {
                      setState(() => _bdItems.add(gone));
                      _bdSave();
                    });
                  }),
                ]),
              ),
            ),
          Expanded(
            child: Container(
              margin: const EdgeInsets.fromLTRB(18, 0, 18, 18),
              decoration: BoxDecoration(
                color: const Color(0xFFF7F1E8),
                borderRadius: BorderRadius.circular(22),
                border: Border.all(color: gold.withOpacity(.5)),
              ),
              clipBehavior: Clip.antiAlias,
              child: Stack(children: <Widget>[
                InteractiveViewer(
                  transformationController: _bdTc,
                  minScale: .25,
                  maxScale: 3,
                  boundaryMargin: const EdgeInsets.all(400),
                  constrained: false,
                  child: GestureDetector(
                    behavior: HitTestBehavior.opaque,
                    onTap: () => setState(() => _bdSel = ''),
                    child: SizedBox(
                      width: kBoardW,
                      height: kBoardH,
                      child: Stack(clipBehavior: Clip.none, children: <Widget>[
                        Positioned.fill(
                          child: IgnorePointer(
                            child: CustomPaint(painter: _BoardGridPainter(gold.withOpacity(.22))),
                          ),
                        ),
                        ...sorted,
                      ]),
                    ),
                  ),
                ),
                if (empty)
                  Positioned.fill(
                    child: IgnorePointer(
                      child: Center(
                        child: Container(
                          constraints: const BoxConstraints(maxWidth: 380),
                          padding: const EdgeInsets.all(22),
                          decoration: BoxDecoration(
                            color: ivory.withOpacity(.94),
                            borderRadius: BorderRadius.circular(18),
                            border: Border.all(color: goldLine),
                          ),
                          child: Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
                            Text('The look you’re going for', style: _serif(size: 24)),
                            const SizedBox(height: 6),
                            const Text(
                                'Pin a link from Pinterest, Etsy or anywhere and the picture lands here. Add photos from your phone, notes, and the colors. Drag it all around; drag a corner to resize. Share it with your florist, planner and photographer when it says what you mean.',
                                textAlign: TextAlign.center,
                                style: TextStyle(fontSize: 13, color: muted, height: 1.45)),
                          ]),
                        ),
                      ),
                    ),
                  ),
              ]),
            ),
          ),
        ]);
      },
    );
  }

  Widget _boardItem(Map<String, dynamic> it) {
    final String id = it['id'].toString();
    final String kind = (it['kind'] ?? 'note').toString();
    final double w = (it['w'] is num ? (it['w'] as num).toDouble() : 220).clamp(60, 900).toDouble();
    final double ar = (it['ar'] is num ? (it['ar'] as num).toDouble() : 1).clamp(.2, 5).toDouble();
    final double hgt = kind == 'note' ? (it['h'] is num ? (it['h'] as num).toDouble() : w / ar) : w / ar;
    final double x = it['x'] is num ? (it['x'] as num).toDouble() : 100;
    final double y = it['y'] is num ? (it['y'] as num).toDouble() : 100;
    final bool sel = _bdSel == id;
    Widget body;
    if (kind == 'image') {
      body = ClipRRect(
        borderRadius: BorderRadius.circular(10),
        child: Image.network(
          (it['url'] ?? '').toString(),
          width: w,
          height: hgt,
          fit: BoxFit.cover,
          frameBuilder: (BuildContext c, Widget child, int? frame, bool sync) {
            if (frame != null && it['arReal'] != true) {
              // First paint: read the real aspect once, so the pin keeps its shape.
              WidgetsBinding.instance.addPostFrameCallback((_) {
                final ImageStream st = Image.network((it['url'] ?? '').toString()).image.resolve(const ImageConfiguration());
                late final ImageStreamListener l;
                l = ImageStreamListener((ImageInfo info, bool _) {
                  st.removeListener(l);
                  final double real = info.image.width / info.image.height;
                  if (mounted && (it['arReal'] != true)) {
                    setState(() {
                      it['ar'] = real;
                      it['arReal'] = true;
                    });
                    _bdSave();
                  }
                });
                st.addListener(l);
              });
            }
            return child;
          },
          errorBuilder: (BuildContext c, Object e, StackTrace? st) => Container(
            width: w,
            height: hgt,
            color: const Color(0xFFEFE4D2),
            alignment: Alignment.center,
            child: const Icon(Icons.broken_image_outlined, color: muted),
          ),
        ),
      );
      final String cap = (it['title'] ?? '').toString();
      if (cap.isNotEmpty) {
        body = Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
          body,
          SizedBox(
            width: w,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(2, 4, 2, 0),
              child: Text(cap, maxLines: 2, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 11, color: muted, height: 1.3)),
            ),
          ),
        ]);
      }
    } else if (kind == 'swatch') {
      final String c = (it['color'] ?? 'D9B77C').toString();
      final String l = (it['text'] ?? '').toString();
      body = Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
        Container(
          width: w,
          height: w,
          decoration: BoxDecoration(
              color: Color(int.tryParse('FF$c', radix: 16) ?? 0xFFD9B77C),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: Colors.white, width: 3),
              boxShadow: const <BoxShadow>[BoxShadow(color: Color(0x22000000), blurRadius: 8, offset: Offset(0, 3))]),
        ),
        SizedBox(
          width: w,
          child: Text(l.isEmpty ? '#$c' : '$l · #$c', textAlign: TextAlign.center, maxLines: 2, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 11, color: muted, fontWeight: FontWeight.w700)),
        ),
      ]);
    } else {
      final String c = (it['color'] ?? 'F3EBDD').toString();
      body = Container(
        width: w,
        constraints: BoxConstraints(minHeight: hgt * .6),
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
        decoration: BoxDecoration(
            color: Color(int.tryParse('FF$c', radix: 16) ?? 0xFFF3EBDD),
            borderRadius: BorderRadius.circular(10),
            boxShadow: const <BoxShadow>[BoxShadow(color: Color(0x22000000), blurRadius: 8, offset: Offset(0, 3))]),
        child: Text((it['text'] ?? '').toString(),
            style: TextStyle(color: ink, fontSize: (w / 14).clamp(12, 20).toDouble(), height: 1.35, fontFamily: GoogleFonts.cormorantGaramond().fontFamily, fontWeight: FontWeight.w600)),
      );
    }
    return Positioned(
      left: x,
      top: y,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: () => setState(() => _bdSel = sel ? '' : id),
        onPanStart: (DragStartDetails d) {
          _bdDragging = true;
          setState(() {
            _bdSel = id;
            it['z'] = _bdTopZ() + 1;
          });
        },
        onPanUpdate: (DragUpdateDetails d) {
          final double sc = _bdScale();
          setState(() {
            it['x'] = ((it['x'] as num).toDouble() + d.delta.dx / sc).clamp(-200, kBoardW - 40).toDouble();
            it['y'] = ((it['y'] as num).toDouble() + d.delta.dy / sc).clamp(-200, kBoardH - 40).toDouble();
          });
        },
        onPanEnd: (DragEndDetails d) {
          _bdDragging = false;
          _bdSave();
        },
        onPanCancel: () {
          _bdDragging = false;
          _bdSave();
        },
        child: Stack(clipBehavior: Clip.none, children: <Widget>[
          AnimatedContainer(
            duration: const Duration(milliseconds: 140),
            padding: const EdgeInsets.all(4),
            decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: sel ? plum : Colors.transparent, width: 2)),
            child: body,
          ),
          if (sel)
            Positioned(
              right: -8,
              bottom: -8,
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onPanStart: (DragStartDetails d) => _bdDragging = true,
                onPanUpdate: (DragUpdateDetails d) {
                  final double sc = _bdScale();
                  setState(() {
                    it['w'] = ((it['w'] as num).toDouble() + d.delta.dx / sc).clamp(60, 900).toDouble();
                    if (kind == 'note') {
                      it['h'] = (((it['h'] is num ? (it['h'] as num) : w / ar).toDouble()) + d.delta.dy / sc).clamp(60, 900).toDouble();
                    }
                  });
                },
                onPanEnd: (DragEndDetails d) {
                  _bdDragging = false;
                  _bdSave();
                },
                child: Container(
                  width: 26,
                  height: 26,
                  decoration: BoxDecoration(color: plum, shape: BoxShape.circle, border: Border.all(color: ivory, width: 2)),
                  child: const Icon(Icons.open_in_full_rounded, size: 13, color: gold),
                ),
              ),
            ),
        ]),
      ),
    );
  }

  // ---- JC-LAZO-COUPLE-0920-SHOP-001: the shopping list ----''', "board screen")

# 5. the grid painter, a top-level class at the end of the file
swap("""enum _Tick { none, select, light, medium }
""", """// JC-LAZO-COUPLE-0920-BOARD-001: the dream board's faint dot grid.
class _BoardGridPainter extends CustomPainter {
  const _BoardGridPainter(this.color);
  final Color color;
  @override
  void paint(Canvas canvas, Size size) {
    final Paint p = Paint()..color = color;
    for (double x = 0; x < size.width; x += 40) {
      for (double y = 0; y < size.height; y += 40) {
        canvas.drawCircle(Offset(x, y), 1.2, p);
      }
    }
  }

  @override
  bool shouldRepaint(_BoardGridPainter old) => old.color != color;
}

enum _Tick { none, select, light, medium }
""", "grid painter")

# 6. header history line
swap("// (v133: SHOPPING LIST",
     "// (v134: DREAM BOARD - a movable inspiration board: pin a link (Pinterest, Etsy, any page - meetlazo.com/api/unfurl reads the picture and caption), upload photos, add notes and color swatches; drag, zoom, resize from the corner, tap to select for open-source / edit / to-front / remove; one doc couples/{cid}/board/main saved half a second after the last move; Share sends pictures, notes and colors to the florist, planner and photographer; on the rail, the phone grid and June's map. JC-LAZO-COUPLE-0920-BOARD-001; base v133) (v133: SHOPPING LIST",
     "header")

OUT.write_text(s, encoding="utf-8", newline="\n")
print(f"wrote {OUT} ({len(s):,} chars)")
