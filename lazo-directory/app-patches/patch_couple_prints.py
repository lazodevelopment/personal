"""patch_couple_prints.py - JC-LAZO-COUPLE-0920-PRINTS
A Photos & prints screen on the couple dashboard. Photographers deliver
galleries at meetlazo.com/g/{slug}; the couple keeps those links here
(couples.galleries: [{slug, names, vendor, passcode}]), opens the gallery,
orders prints from it (the gallery page runs the store: favorites -> WHCC's
editor -> cart -> Stripe), and sees every print order with its status and
tracking, read from meetlazo.com/api/prints/orders.
  - Add a gallery: paste the link (or just the slug) and, if the gallery has a
    passcode, the passcode, kept on the couple doc so orders can be read.
  - Each gallery card: photographer, names, Open gallery, Order prints.
  - Orders: product, size, quantity, total, status pill, carrier + tracking.
  - On the rail, the phone grid and June's map ("open my photos").
Applies on top of Couple_master_v135.txt -> Couple_master_prints.txt.
  python app-patches\\patch_couple_prints.py [src] [out]
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Couple_master_v135.txt"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "Couple_master_prints.txt"
s = SRC.read_text(encoding="utf-8")
if "JC-LAZO-COUPLE-0920-PRINTS" in s:
    raise SystemExit("already applied")


def swap(old, new, label, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"ABORT [{label}]: anchor matched {n} times, expected {count}")
    s = s.replace(old, new)
    print(f"  ok  {label}")


swap("""  shopping,
  board
}
""", """  shopping,
  board,
  prints
}
""", "enum")

swap("""    if (_view == _View.board) return _boardScreen(couple);
""", """    if (_view == _View.board) return _boardScreen(couple);
    if (_view == _View.prints) return _printsScreen(couple);
""", "body switch")

swap("""          _railNavRow('Dream board', Icons.auto_awesome_mosaic_rounded, _View.board),
        ],
""", """          _railNavRow('Dream board', Icons.auto_awesome_mosaic_rounded, _View.board),
          _railNavRow('Photos & prints', Icons.photo_library_rounded, _View.prints),
        ],
""", "desktop rail")

swap("""      <dynamic>[
        'Dream board',
        Icons.auto_awesome_mosaic_rounded,
        () => setState(() => _view = _View.board),
        _View.board
      ],
""", """      <dynamic>[
        'Dream board',
        Icons.auto_awesome_mosaic_rounded,
        () => setState(() => _view = _View.board),
        _View.board
      ],
      <dynamic>[
        'Photos',
        Icons.photo_library_rounded,
        () => setState(() => _view = _View.prints),
        _View.prints
      ],
""", "phone grid")

swap("""    <String>['board', 'Dream board', 'dream board|mood board|moodboard|inspiration|pinterest|vision board|inspo'],
""", """    <String>['board', 'Dream board', 'dream board|mood board|moodboard|inspiration|pinterest|vision board|inspo'],
    <String>['prints', 'Photos & prints', 'photos|gallery|galleries|prints|print order|order prints|album|our pictures'],
""", "June open map")

swap("""      case 'board':
        setState(() => _view = _View.board);
        break;
""", """      case 'board':
        setState(() => _view = _View.board);
        break;
      case 'prints':
        setState(() => _view = _View.prints);
        break;
""", "June go")

swap("""home, vendors, browse, messages, dayof, guests, seating, music, website, registry, shopping, board, account. '""",
     """home, vendors, browse, messages, dayof, guests, seating, music, website, registry, shopping, board, prints, account. '
      'Photos & prints holds the galleries their photographer delivered (meetlazo.com/g/ links), opens them, orders professional prints from them, and shows print orders with tracking. '""",
     "June app map")

swap("""  // ---- JC-LAZO-COUPLE-0920-BOARD-001: the dream board ----""",
     r'''  // ---- JC-LAZO-COUPLE-0920-PRINTS: photos & prints ----

  List<Map<String, dynamic>> _galleriesOf(Map<String, dynamic> couple) => <Map<String, dynamic>>[
        if (couple['galleries'] is List)
          for (final dynamic g in couple['galleries'] as List)
            if (g is Map) Map<String, dynamic>.from(g)
      ];

  Map<String, List<Map<String, dynamic>>> _prOrders = <String, List<Map<String, dynamic>>>{};
  Set<String> _prLoading = <String>{};

  Future<void> _prLoadOrders(Map<String, dynamic> g, {bool force = false}) async {
    final String slug = (g['slug'] ?? '').toString();
    if (slug.isEmpty || _prLoading.contains(slug) || (!force && _prOrders.containsKey(slug))) return;
    _prLoading.add(slug);
    try {
      final String pass = (g['passcode'] ?? '').toString();
      final httpc.Response r = await httpc
          .get(Uri.parse('https://meetlazo.com/api/prints/orders?slug=${Uri.encodeComponent(slug)}${pass.isEmpty ? '' : '&passcode=${Uri.encodeComponent(pass)}'}'))
          .timeout(const Duration(seconds: 12));
      final Map<String, dynamic> j = r.statusCode == 200 ? Map<String, dynamic>.from(jsonDecode(r.body) as Map) : <String, dynamic>{};
      _prOrders[slug] = <Map<String, dynamic>>[
        if (j['orders'] is List)
          for (final dynamic o in j['orders'] as List)
            if (o is Map) Map<String, dynamic>.from(o)
      ];
    } catch (e) {
      _prOrders[slug] = <Map<String, dynamic>>[];
      debugPrint('LAZO prints orders: ' + e.toString());
    } finally {
      _prLoading.remove(slug);
      if (mounted) setState(() {});
    }
  }

  Future<void> _prAddGallery(Map<String, dynamic> couple) async {
    final TextEditingController linkC = TextEditingController();
    final TextEditingController passC = TextEditingController();
    final bool? ok = await showDialog<bool>(
      context: context,
      builder: (BuildContext ctx) => AlertDialog(
        backgroundColor: ivory,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Text('Add a gallery', style: TextStyle(color: plum, fontSize: 17, fontWeight: FontWeight.w800)),
        content: Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
          TextField(controller: linkC, autofocus: true, keyboardType: TextInputType.url, style: const TextStyle(color: ink), decoration: _lightDeco('Gallery link', hint: 'meetlazo.com/g/hazel-and-rowan-a1b2c3')),
          const SizedBox(height: 10),
          TextField(controller: passC, style: const TextStyle(color: ink), decoration: _lightDeco('Passcode (if the gallery has one)')),
          const SizedBox(height: 8),
          const Text('Your photographer sends the link when the gallery is ready. It stays here so you can order prints any time.', style: TextStyle(fontSize: 12, color: muted, height: 1.4)),
        ]),
        actions: <Widget>[
          TextButton(onPressed: _h(() => Navigator.pop(ctx, false)), child: const Text('Cancel', style: TextStyle(color: muted))),
          FilledButton(style: FilledButton.styleFrom(backgroundColor: gold, foregroundColor: plum), onPressed: _h(() => Navigator.pop(ctx, true)), child: const Text('Add')),
        ],
      ),
    );
    if (ok != true) return;
    final RegExpMatch? m = RegExp(r'(?:/g/)?([a-z0-9-]{3,80})/?(?:\?.*)?$').firstMatch(linkC.text.trim().toLowerCase());
    if (m == null) { _toast('That does not look like a gallery link.'); return; }
    final String slug = m.group(1)!;
    final List<Map<String, dynamic>> gs = _galleriesOf(couple);
    if (gs.any((Map<String, dynamic> g) => g['slug'] == slug)) { _toast('That gallery is already here.'); return; }
    String names = '', vendor = '';
    try {
      final DocumentSnapshot<Map<String, dynamic>> d = await FirebaseFirestore.instance.collection('galleries').doc(slug).get();
      if (!d.exists) { _toast('We could not find that gallery. Check the link.'); return; }
      names = (d.data()?['names'] ?? '').toString();
      vendor = (d.data()?['vendorName'] ?? '').toString();
    } catch (_) {}
    gs.add(<String, dynamic>{'slug': slug, 'names': names, 'vendor': vendor, 'passcode': passC.text.trim(), 'addedAt': DateTime.now().millisecondsSinceEpoch});
    await _coupleRef.set(<String, dynamic>{'galleries': gs}, SetOptions(merge: true));
    _prOrders.remove(slug);
  }

  Future<void> _prOpen(String path) async {
    final Uri u = Uri.parse('https://meetlazo.com$path');
    if (await canLaunchUrl(u)) await launchUrl(u, mode: LaunchMode.externalApplication);
  }

  Widget _printsScreen(Map<String, dynamic> couple) {
    final List<Map<String, dynamic>> gs = _galleriesOf(couple);
    for (final Map<String, dynamic> g in gs) {
      _prLoadOrders(g);
    }
    final List<Map<String, dynamic>> orders = <Map<String, dynamic>>[
      for (final Map<String, dynamic> g in gs) ...(_prOrders[(g['slug'] ?? '').toString()] ?? const <Map<String, dynamic>>[])
    ]..sort((Map<String, dynamic> a, Map<String, dynamic> b) => (b['createdAt'] ?? '').toString().compareTo((a['createdAt'] ?? '').toString()));
    String statusLabel(String st) => <String, String>{
          'paid': 'Paid · sending to the lab', 'paid_unsubmitted': 'Paid · sending to the lab', 'submitted': 'At the lab',
          'accepted': 'In production', 'shipped': 'Shipped', 'rejected': 'Needs attention',
        }[st] ?? st;
    return ListView(
      padding: const EdgeInsets.fromLTRB(18, 8, 18, 96),
      children: <Widget>[
        _subHeader('Photos & prints',
            trailing: _Press(
              onTap: () => _prAddGallery(couple),
              child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
                Icon(Icons.add_rounded, color: ivory.withOpacity(.9), size: 16),
                const SizedBox(width: 3),
                Text('Add a gallery', style: TextStyle(color: ivory.withOpacity(.9), fontSize: 12, fontWeight: FontWeight.w800)),
              ]),
            )),
        Padding(
          padding: const EdgeInsets.only(left: 6, bottom: 14),
          child: Text(
              gs.isEmpty
                  ? 'When your photographer delivers your gallery on Lazo, keep the link here. Open it any time, tap the hearts, and order professional prints of your favorites - shipped to your door, no lab branding.'
                  : '${gs.length} galler${gs.length == 1 ? 'y' : 'ies'}${orders.isEmpty ? '' : ' · ${orders.length} print order${orders.length == 1 ? '' : 's'}'}',
              style: TextStyle(fontSize: 13, color: ivory.withOpacity(.72), height: 1.45)),
        ),
        if (gs.isEmpty)
          _glass(
            padding: const EdgeInsets.all(18),
            radius: 22,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
              const Text('Have a gallery link?', style: TextStyle(color: plum, fontSize: 16, fontWeight: FontWeight.w800)),
              const SizedBox(height: 6),
              const Text('It looks like meetlazo.com/g/your-names. Paste it and it lives here.', style: TextStyle(fontSize: 12.5, color: muted, height: 1.45)),
              const SizedBox(height: 12),
              FilledButton.icon(
                style: FilledButton.styleFrom(backgroundColor: gold, foregroundColor: plum),
                onPressed: _h(() => _prAddGallery(couple)),
                icon: const Icon(Icons.link_rounded, size: 16),
                label: const Text('Add a gallery', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800)),
              ),
            ]),
          ),
        for (final Map<String, dynamic> g in gs)
          _glass(
            padding: const EdgeInsets.all(18),
            radius: 22,
            margin: const EdgeInsets.only(bottom: 12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
              Row(children: <Widget>[
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(color: plum, borderRadius: BorderRadius.circular(12)),
                  child: const Icon(Icons.photo_library_rounded, color: gold, size: 22),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                    Text((g['names'] ?? '').toString().isEmpty ? 'Your gallery' : (g['names'] ?? '').toString(), style: _serif(size: 20)),
                    Text(<String>[
                      if ((g['vendor'] ?? '').toString().isNotEmpty) 'by ${g['vendor']}',
                      'meetlazo.com/g/${g['slug']}',
                    ].join(' · '), style: const TextStyle(fontSize: 11.5, color: muted)),
                  ]),
                ),
                _Press(
                  onLongPress: () async {
                    final List<Map<String, dynamic>> rest = gs.where((Map<String, dynamic> x) => x['slug'] != g['slug']).toList();
                    await _coupleRef.set(<String, dynamic>{'galleries': rest}, SetOptions(merge: true));
                    _toastUndo('Gallery removed.', () => _coupleRef.set(<String, dynamic>{'galleries': gs}, SetOptions(merge: true)));
                  },
                  onTap: () {},
                  child: const Padding(padding: EdgeInsets.all(4), child: Icon(Icons.more_horiz_rounded, size: 18, color: muted)),
                ),
              ]),
              const SizedBox(height: 12),
              Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                FilledButton.icon(
                  style: FilledButton.styleFrom(backgroundColor: gold, foregroundColor: plum, padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10)),
                  onPressed: _h(() => _prOpen('/g/${g['slug']}')),
                  icon: const Icon(Icons.print_rounded, size: 16),
                  label: const Text('Open & order prints', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800)),
                ),
                OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(foregroundColor: plum, side: BorderSide(color: gold.withOpacity(.8)), padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10)),
                  onPressed: _h(() => _prLoadOrders(g, force: true)),
                  icon: const Icon(Icons.refresh_rounded, size: 16),
                  label: Text(_prLoading.contains(g['slug']) ? 'Checking…' : 'Refresh orders', style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800)),
                ),
              ]),
              const SizedBox(height: 6),
              const Text('Tap the hearts in the gallery, then Order prints. Sizes, papers and framing are chosen in the lab’s editor; you pay Lazo and the box arrives with no lab branding.',
                  style: TextStyle(fontSize: 11.5, color: muted, height: 1.4)),
            ]),
          ),
        if (orders.isNotEmpty) ...<Widget>[
          const SizedBox(height: 6),
          Padding(padding: const EdgeInsets.only(left: 6, bottom: 8), child: Text('PRINT ORDERS', style: TextStyle(fontSize: 10.5, letterSpacing: 2, color: ivory.withOpacity(.75), fontWeight: FontWeight.w700))),
          for (final Map<String, dynamic> o in orders)
            _glass(
              padding: const EdgeInsets.all(14),
              radius: 18,
              margin: const EdgeInsets.only(bottom: 10),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                if ((o['preview'] ?? '').toString().isNotEmpty)
                  ClipRRect(
                    borderRadius: BorderRadius.circular(10),
                    child: Image.network((o['preview'] ?? '').toString(), width: 64, height: 64, fit: BoxFit.cover,
                        errorBuilder: (BuildContext a, Object b, StackTrace? c) => const SizedBox(width: 64, height: 64)),
                  )
                else
                  Container(width: 64, height: 64, decoration: BoxDecoration(color: gold.withOpacity(.2), borderRadius: BorderRadius.circular(10)), child: const Icon(Icons.print_rounded, color: plum)),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                    Text('${o['product'] ?? 'Prints'}${(o['quantity'] is num && (o['quantity'] as num) > 1) ? ' × ${o['quantity']}' : ''}', style: const TextStyle(color: ink, fontSize: 14, fontWeight: FontWeight.w700)),
                    if (o['summary'] is List && (o['summary'] as List).isNotEmpty)
                      Text((o['summary'] as List).join(' · '), style: const TextStyle(fontSize: 11.5, color: muted)),
                    const SizedBox(height: 6),
                    Wrap(spacing: 6, runSpacing: 4, crossAxisAlignment: WrapCrossAlignment.center, children: <Widget>[
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
                        decoration: BoxDecoration(
                            color: o['status'] == 'shipped' ? const Color(0xFFE7F3EC) : (o['status'] == 'rejected' ? const Color(0xFFFBECEC) : const Color(0xFFF7EBD3)),
                            borderRadius: BorderRadius.circular(999)),
                        child: Text(statusLabel((o['status'] ?? '').toString()),
                            style: TextStyle(
                                color: o['status'] == 'shipped' ? vGreen : (o['status'] == 'rejected' ? const Color(0xFFB04343) : const Color(0xFF8A6A2F)),
                                fontSize: 11,
                                fontWeight: FontWeight.w800)),
                      ),
                      if (o['total'] is num) Text('\$${(o['total'] as num).toStringAsFixed(2)}', style: const TextStyle(fontSize: 12, color: muted)),
                    ]),
                    if (o['tracking'] is List && (o['tracking'] as List).isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.only(top: 6),
                        child: _Press(
                          onTap: () async {
                            final String u = (o['trackingUrl'] ?? '').toString();
                            if (u.isEmpty) return;
                            final Uri uri = Uri.parse(u);
                            if (await canLaunchUrl(uri)) await launchUrl(uri, mode: LaunchMode.externalApplication);
                          },
                          child: Text('${o['carrier'] ?? ''} ${(o['tracking'] as List).join(', ')}${(o['trackingUrl'] ?? '').toString().isEmpty ? '' : ' · Track →'}',
                              style: const TextStyle(fontSize: 12, color: plum, fontWeight: FontWeight.w700)),
                        ),
                      ),
                    if (o['status'] == 'rejected' && (o['error'] ?? '').toString().isNotEmpty)
                      Padding(padding: const EdgeInsets.only(top: 4), child: Text((o['error'] ?? '').toString(), style: const TextStyle(fontSize: 11.5, color: Color(0xFFB04343)))),
                  ]),
                ),
              ]),
            ),
        ],
      ],
    );
  }

  // ---- JC-LAZO-COUPLE-0920-BOARD-001: the dream board ----''', "prints screen")

swap("// (v135: COMMENTS + ALLOCATION",
     "// (v136: PHOTOS & PRINTS - a screen that keeps the photographer's gallery links (couples.galleries), opens them, sends the couple into the print store on the gallery page, and lists print orders with status and tracking from meetlazo.com/api/prints/orders. JC-LAZO-COUPLE-0920-PRINTS; base v135) (v135: COMMENTS + ALLOCATION",
     "header")

OUT.write_text(s, encoding="utf-8", newline="\n")
print(f"wrote {OUT} ({len(s):,} chars)")
