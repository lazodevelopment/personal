"""patch_couple_shopping.py - JC-LAZO-COUPLE-0920-SHOP-001
A Shopping list screen on the couple dashboard: the things the couple buys
themselves (the registry is what guests buy). Items live in
couples/{cid}/shopping/{id}: {name, cat, qty, est, bought, note, link,
createdAt, updatedAt}. Categories: ceremony, reception, attire, stationery,
favors, dayof (the day-of kit), other.

  - Screen: total bought of total, dollars still to spend; filter chips (To
    buy / Bought / each category); items grouped by category with a one-tap
    bought toggle; tap to edit (name, category, quantity, estimate, link,
    note); hold to remove with undo.
  - "Start with the classic list" seeds 34 items with typical estimates when
    the list is empty - card box, guest book, cake knife, welcome sign, the
    emergency kit and so on - each in the right category.
  - Send to your planner: the open items as a page and a thread message
    through the same send sheet as the timeline (planner pre-checked).
  - Wired in: the desk rail (desktop and phone grid), the body switch, June's
    open map ("open shopping list") and her app map.

Applies on top of Couple_master_license.txt -> Couple_master_shopping.txt.
Anchor-and-assert.
  python app-patches\\patch_couple_shopping.py [src] [out]
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Couple_master_license.txt"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else SRC.with_name(SRC.stem.replace("_license", "") + "_shopping.txt")
s = SRC.read_text(encoding="utf-8")
if "JC-LAZO-COUPLE-0920-SHOP-001" in s:
    raise SystemExit("already applied")


def swap(old, new, label, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"ABORT [{label}]: anchor matched {n} times, expected {count}")
    s = s.replace(old, new)
    print(f"  ok  {label}")


# 1. the view
swap("""  messages,
  dayof
}
""", """  messages,
  dayof,
  shopping
}
""", "enum")

swap("""    if (_view == _View.registry) return _registryScreen(couple);
    if (_view == _View.guests) return _guestScreen();
""", """    if (_view == _View.registry) return _registryScreen(couple);
    if (_view == _View.shopping) return _shoppingScreen(couple);
    if (_view == _View.guests) return _guestScreen();
""", "body switch")

# 2. the rails
swap("""          _railNavRow('Registry', Icons.card_giftcard_rounded, _View.registry),
        ],
""", """          _railNavRow('Registry', Icons.card_giftcard_rounded, _View.registry),
          _railNavRow('Shopping list', Icons.shopping_bag_rounded, _View.shopping),
        ],
""", "desktop rail")

swap("""      <dynamic>[
        'Registry',
        Icons.card_giftcard_rounded,
        () => setState(() => _view = _View.registry),
        _View.registry
      ],
      <dynamic>[
        'Account',
""", """      <dynamic>[
        'Registry',
        Icons.card_giftcard_rounded,
        () => setState(() => _view = _View.registry),
        _View.registry
      ],
      <dynamic>[
        'Shopping',
        Icons.shopping_bag_rounded,
        () => setState(() => _view = _View.shopping),
        _View.shopping
      ],
      <dynamic>[
        'Account',
""", "phone grid")

# 3. June
swap("""    <String>['registry', 'Registry', 'registry|gifts'],
""", """    <String>['registry', 'Registry', 'registry|gifts'],
    <String>['shopping', 'Shopping list', 'shopping|shopping list|things to buy|to buy|supplies|decor list'],
""", "June open map")

swap("""      case 'registry':
        setState(() => _view = _View.registry);
        break;
      case 'account':""", """      case 'registry':
        setState(() => _view = _View.registry);
        break;
      case 'shopping':
        setState(() => _view = _View.shopping);
        break;
      case 'account':""", "June go")

swap("""using one of these keys: home, vendors, browse, messages, dayof, guests, seating, music, website, registry, account. '""",
     """using one of these keys: home, vendors, browse, messages, dayof, guests, seating, music, website, registry, shopping, account. '
      'Shopping list is the things the couple buys themselves for the wedding (decor, signs, card box, guest book, favors, the day-of kit), with a bought toggle and an estimate each - not the registry, which is what guests buy. '""",
     "June app map")

# 4. the screen, next to the registry screen
swap("""  Widget _registryScreen(Map<String, dynamic> couple) {""",
     r'''  // ---- JC-LAZO-COUPLE-0920-SHOP-001: the shopping list ----

  CollectionReference<Map<String, dynamic>> get _shopRef =>
      _coupleRef.collection('shopping');

  static const List<List<String>> kShopCats = <List<String>>[
    <String>['ceremony', 'Ceremony'],
    <String>['reception', 'Reception'],
    <String>['attire', 'Attire & beauty'],
    <String>['stationery', 'Stationery & signs'],
    <String>['favors', 'Favors & gifts'],
    <String>['dayof', 'Day-of kit'],
    <String>['other', 'Everything else'],
  ];

  static String _shopCatLabel(String c) {
    for (final List<String> k in kShopCats) {
      if (k[0] == c) return k[1];
    }
    return 'Everything else';
  }

  String _shopFilter = 'tobuy';

  // name, category, qty, typical estimate in dollars
  static const List<List<dynamic>> kShopClassic = <List<dynamic>>[
    <dynamic>['Unity candle or sand set', 'ceremony', 1, 40],
    <dynamic>['Ring box or pillow', 'ceremony', 1, 30],
    <dynamic>['Programs', 'ceremony', 100, 120],
    <dynamic>['Aisle runner or petals', 'ceremony', 1, 60],
    <dynamic>['Reserved-row signs', 'ceremony', 4, 25],
    <dynamic>['Card box', 'reception', 1, 45],
    <dynamic>['Guest book and pens', 'reception', 1, 40],
    <dynamic>['Cake knife and server', 'reception', 1, 35],
    <dynamic>['Toasting flutes', 'reception', 2, 40],
    <dynamic>['Table numbers', 'reception', 20, 40],
    <dynamic>['Place cards or escort cards', 'reception', 120, 60],
    <dynamic>['Centerpiece vases or candles', 'reception', 20, 200],
    <dynamic>['Sparklers or send-off supplies', 'reception', 100, 45],
    <dynamic>['Bathroom baskets', 'reception', 2, 50],
    <dynamic>['Wedding dress or suit alterations', 'attire', 1, 300],
    <dynamic>['Shoes', 'attire', 2, 200],
    <dynamic>['Veil or hairpiece', 'attire', 1, 100],
    <dynamic>['Jewelry', 'attire', 1, 150],
    <dynamic>['Getting-ready robes or shirts', 'attire', 6, 150],
    <dynamic>['Undergarments and shapewear', 'attire', 1, 80],
    <dynamic>['Welcome sign', 'stationery', 1, 60],
    <dynamic>['Seating chart sign', 'stationery', 1, 70],
    <dynamic>['Menu cards', 'stationery', 120, 80],
    <dynamic>['Bar sign and signature drink signs', 'stationery', 2, 40],
    <dynamic>['Thank-you cards and stamps', 'stationery', 120, 130],
    <dynamic>['Favors', 'favors', 120, 300],
    <dynamic>['Wedding-party gifts', 'favors', 8, 400],
    <dynamic>['Parent gifts', 'favors', 4, 200],
    <dynamic>['Welcome bags for out-of-town guests', 'favors', 20, 250],
    <dynamic>['Emergency kit (sewing, stain pen, pain relief, blister pads)', 'dayof', 1, 45],
    <dynamic>['Steamer', 'dayof', 1, 35],
    <dynamic>['Snacks and water for getting ready', 'dayof', 1, 60],
    <dynamic>['Vendor tip envelopes, labelled', 'dayof', 10, 5],
    <dynamic>['Marriage license (in the folder!)', 'dayof', 1, 0],
  ];

  Future<void> _seedShopping() async {
    final WriteBatch b = FirebaseFirestore.instance.batch();
    int i = 0;
    for (final List<dynamic> r in kShopClassic) {
      b.set(_shopRef.doc(), <String, dynamic>{
        'name': r[0],
        'cat': r[1],
        'qty': r[2],
        'est': r[3],
        'bought': false,
        'note': '',
        'link': '',
        'order': i++,
        'createdAt': FieldValue.serverTimestamp(),
      });
    }
    await b.commit();
    _toast('The classic list - cross off what you don’t need.');
  }

  Future<void> _editShopItem(
      QueryDocumentSnapshot<Map<String, dynamic>>? d) async {
    final Map<String, dynamic> it = d?.data() ?? <String, dynamic>{};
    final TextEditingController nameC =
        TextEditingController(text: (it['name'] ?? '').toString());
    final TextEditingController qtyC = TextEditingController(
        text: it['qty'] == null ? '1' : it['qty'].toString());
    final TextEditingController estC = TextEditingController(
        text: it['est'] == null ? '' : it['est'].toString());
    final TextEditingController linkC =
        TextEditingController(text: (it['link'] ?? '').toString());
    final TextEditingController noteC =
        TextEditingController(text: (it['note'] ?? '').toString());
    String cat = (it['cat'] ?? (_shopFilter.length > 5 && kShopCats.any((List<String> k) => k[0] == _shopFilter) ? _shopFilter : 'reception')).toString();
    final bool? ok = await showDialog<bool>(
      context: context,
      builder: (BuildContext ctx) => StatefulBuilder(
          builder: (BuildContext ctx2, StateSetter setD) => AlertDialog(
                backgroundColor: ivory,
                scrollable: true,
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(20)),
                title: Text(d == null ? 'Add to the list' : 'Edit item',
                    style: const TextStyle(
                        color: plum, fontSize: 17, fontWeight: FontWeight.w800)),
                content: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    TextField(
                        controller: nameC,
                        autofocus: d == null,
                        textCapitalization: TextCapitalization.sentences,
                        style: const TextStyle(color: ink),
                        decoration: _lightDeco('What', hint: 'Card box')),
                    const SizedBox(height: 10),
                    Row(children: <Widget>[
                      Expanded(
                        child: TextField(
                            controller: qtyC,
                            keyboardType: TextInputType.number,
                            style: const TextStyle(color: ink),
                            decoration: _lightDeco('How many')),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: TextField(
                            controller: estC,
                            keyboardType: TextInputType.number,
                            style: const TextStyle(color: ink),
                            decoration: _lightDeco('About \$', hint: 'total')),
                      ),
                    ]),
                    const SizedBox(height: 12),
                    const Text('WHERE IT’S FOR',
                        style: TextStyle(
                            fontSize: 10.5,
                            letterSpacing: 2,
                            color: plum,
                            fontWeight: FontWeight.w700)),
                    const SizedBox(height: 6),
                    Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
                      for (final List<String> k in kShopCats)
                        _tlChip(k[1], cat == k[0], () => setD(() => cat = k[0])),
                    ]),
                    const SizedBox(height: 10),
                    TextField(
                        controller: linkC,
                        keyboardType: TextInputType.url,
                        style: const TextStyle(color: ink),
                        decoration: _lightDeco('Link (optional)', hint: 'Where you found it')),
                    const SizedBox(height: 10),
                    TextField(
                        controller: noteC,
                        style: const TextStyle(color: ink),
                        decoration: _lightDeco('Note (optional)', hint: 'Colour, size, who’s buying it')),
                  ],
                ),
                actions: <Widget>[
                  TextButton(
                      onPressed: _h(() => Navigator.pop(ctx2, false)),
                      child: const Text('Cancel', style: TextStyle(color: muted))),
                  FilledButton(
                    style: FilledButton.styleFrom(
                        backgroundColor: gold, foregroundColor: plum),
                    onPressed: _h(() => Navigator.pop(ctx2, true)),
                    child: const Text('Save'),
                  ),
                ],
              )),
    );
    if (ok != true || nameC.text.trim().isEmpty) return;
    String link = linkC.text.trim();
    if (link.isNotEmpty && !link.startsWith('http')) link = 'https://' + link;
    final Map<String, dynamic> payload = <String, dynamic>{
      'name': nameC.text.trim(),
      'cat': cat,
      'qty': int.tryParse(qtyC.text.trim()) ?? 1,
      'est': int.tryParse(estC.text.trim().replaceAll(RegExp(r'[^0-9]'), '')) ?? 0,
      'link': link,
      'note': noteC.text.trim(),
      'updatedAt': FieldValue.serverTimestamp(),
    };
    if (d == null) {
      payload['bought'] = false;
      payload['order'] = DateTime.now().millisecondsSinceEpoch;
      payload['createdAt'] = FieldValue.serverTimestamp();
      await _shopRef.add(payload);
    } else {
      await d.reference.set(payload, SetOptions(merge: true));
    }
  }

  Future<void> _sendShopping(
      List<QueryDocumentSnapshot<Map<String, dynamic>>> docs,
      Map<String, dynamic> couple) async {
    final List<QueryDocumentSnapshot<Map<String, dynamic>>> open = docs
        .where((QueryDocumentSnapshot<Map<String, dynamic>> d) => d.data()['bought'] != true)
        .toList();
    if (open.isEmpty) {
      _toast('Everything is bought - nothing to send.');
      return;
    }
    final String who = _coupleLabel(couple);
    final String when = _weddingDateLine(couple);
    final StringBuffer t = StringBuffer();
    final StringBuffer h = StringBuffer();
    t.writeln('SHOPPING LIST - still to buy${when.isEmpty ? '' : ' - $when'}');
    for (final List<String> k in kShopCats) {
      final List<QueryDocumentSnapshot<Map<String, dynamic>>> rows = open
          .where((QueryDocumentSnapshot<Map<String, dynamic>> d) => (d.data()['cat'] ?? 'other') == k[0])
          .toList();
      if (rows.isEmpty) continue;
      t.writeln('');
      t.writeln(k[1].toUpperCase());
      h.write('<h2>${_esc(k[1])}</h2><table>');
      for (final QueryDocumentSnapshot<Map<String, dynamic>> d in rows) {
        final Map<String, dynamic> it = d.data();
        final int qty = it['qty'] is num ? (it['qty'] as num).toInt() : 1;
        final int est = it['est'] is num ? (it['est'] as num).toInt() : 0;
        final String note = (it['note'] ?? '').toString();
        final String link = (it['link'] ?? '').toString();
        t.writeln('${qty > 1 ? '$qty x ' : ''}${it['name'] ?? ''}${est > 0 ? ' - about \$$est' : ''}${note.isEmpty ? '' : ' - $note'}${link.isEmpty ? '' : ' - $link'}');
        h.write('<tr><td class="time">${qty > 1 ? '$qty ×' : ''}</td><td><b>${_esc((it['name'] ?? '').toString())}</b>'
            '${est > 0 ? ' <span style="color:#8A6A2F">about \$$est</span>' : ''}'
            '${note.isEmpty ? '' : '<br><span style="color:#6B5F72">${_esc(note)}</span>'}'
            '${link.isEmpty ? '' : '<br><a href="${_esc(link)}">${_esc(link)}</a>'}</td></tr>');
      }
      h.write('</table>');
    }
    await _sendToVendors(
      kind: 'shopping',
      title: 'shopping list',
      fileName: 'Shopping list.html',
      page: _printShell('Shopping list - still to buy',
          <String>[if (who.isNotEmpty) who, if (when.isNotEmpty) when].join(' · '), h.toString()),
      text: t.toString(),
      tags: <String>['planner'],
      note: 'Here’s what we still need to buy. Tell us if you’d rather source any of it, or if we’re missing something.',
      preview: '${open.length} item${open.length == 1 ? '' : 's'} still to buy',
    );
  }

  Widget _shoppingScreen(Map<String, dynamic> couple) {
    return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
      stream: _liveQuery('shop:$_cid', () => _shopRef.orderBy('order')),
      initialData: _liveQ['shop:$_cid']?.latest,
      builder: (BuildContext c, AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> sn) {
        final List<QueryDocumentSnapshot<Map<String, dynamic>>> docs =
            sn.data?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[];
        final int total = docs.length;
        int bought = 0;
        int toGo = 0;
        int spent = 0;
        for (final QueryDocumentSnapshot<Map<String, dynamic>> d in docs) {
          final Map<String, dynamic> it = d.data();
          final int est = it['est'] is num ? (it['est'] as num).toInt() : 0;
          if (it['bought'] == true) {
            bought++;
            spent += est;
          } else {
            toGo += est;
          }
        }
        final List<QueryDocumentSnapshot<Map<String, dynamic>>> shown = docs.where(
            (QueryDocumentSnapshot<Map<String, dynamic>> d) {
          final Map<String, dynamic> it = d.data();
          if (_shopFilter == 'tobuy') return it['bought'] != true;
          if (_shopFilter == 'bought') return it['bought'] == true;
          if (_shopFilter == 'all') return true;
          return (it['cat'] ?? 'other') == _shopFilter;
        }).toList();
        Widget chip(String key, String label, [int? n]) {
          final bool on = _shopFilter == key;
          return _Press(
            tick: _Tick.select,
            onTap: () => setState(() => _shopFilter = key),
            child: Container(
              margin: const EdgeInsets.only(right: 6),
              padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 7),
              decoration: BoxDecoration(
                color: on ? gold : Colors.white.withOpacity(.12),
                borderRadius: BorderRadius.circular(999),
                border: Border.all(color: on ? gold : ivory.withOpacity(.35)),
              ),
              child: Text(n == null ? label : '$label · $n',
                  style: TextStyle(
                      color: on ? plumDeep : ivory,
                      fontSize: 12,
                      fontWeight: FontWeight.w800)),
            ),
          );
        }

        return ListView(
          padding: const EdgeInsets.fromLTRB(18, 8, 18, 96),
          children: <Widget>[
            _subHeader('Shopping list',
                trailing: total == 0
                    ? null
                    : _Press(
                        onTap: () => _sendShopping(docs, couple),
                        child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
                          Icon(Icons.send_rounded, color: ivory.withOpacity(.9), size: 15),
                          const SizedBox(width: 4),
                          Text('Send',
                              style: TextStyle(
                                  color: ivory.withOpacity(.9),
                                  fontSize: 12,
                                  fontWeight: FontWeight.w800)),
                        ]),
                      )),
            Padding(
              padding: const EdgeInsets.only(left: 6, bottom: 14),
              child: Text(
                total == 0
                    ? 'The things you buy yourselves - signs, the card box, favors, the day-of kit. Your registry is what guests buy; this is the rest.'
                    : '$bought of $total bought${toGo > 0 ? ' · about \$$toGo still to spend' : ''}${spent > 0 ? ' · \$$spent spent' : ''}',
                style: TextStyle(fontSize: 13, color: ivory.withOpacity(.72), height: 1.45),
              ),
            ),
            if (total == 0)
              _glass(
                padding: const EdgeInsets.all(18),
                radius: 22,
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                  const Text('Start with the classic list',
                      style: TextStyle(color: plum, fontSize: 16, fontWeight: FontWeight.w800)),
                  const SizedBox(height: 6),
                  Text(
                      '${kShopClassic.length} things most weddings end up buying, in the right categories with rough prices. Cross off what you don’t need, add what we missed.',
                      style: const TextStyle(fontSize: 12.5, color: muted, height: 1.45)),
                  const SizedBox(height: 12),
                  Row(children: <Widget>[
                    FilledButton.icon(
                      style: FilledButton.styleFrom(backgroundColor: gold, foregroundColor: plum),
                      onPressed: _h(_seedShopping, _Tick.medium),
                      icon: const Icon(Icons.auto_awesome_rounded, size: 16),
                      label: const Text('Use the classic list',
                          style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800)),
                    ),
                    const SizedBox(width: 10),
                    TextButton(
                      onPressed: _h(() => _editShopItem(null)),
                      child: const Text('Add one thing',
                          style: TextStyle(color: plum, fontWeight: FontWeight.w700)),
                    ),
                  ]),
                ]),
              )
            else ...<Widget>[
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.only(bottom: 12),
                child: Row(children: <Widget>[
                  chip('tobuy', 'To buy', total - bought),
                  chip('bought', 'Bought', bought),
                  chip('all', 'All'),
                  for (final List<String> k in kShopCats)
                    if (docs.any((QueryDocumentSnapshot<Map<String, dynamic>> d) => (d.data()['cat'] ?? 'other') == k[0]))
                      chip(k[0], k[1]),
                ]),
              ),
              if (shown.isEmpty)
                Padding(
                  padding: const EdgeInsets.all(18),
                  child: Text(
                      _shopFilter == 'tobuy' ? 'Everything is bought.' : 'Nothing here yet.',
                      style: TextStyle(color: ivory.withOpacity(.72), fontSize: 13)),
                )
              else
                for (final List<String> k in kShopCats)
                  if (shown.any((QueryDocumentSnapshot<Map<String, dynamic>> d) => (d.data()['cat'] ?? 'other') == k[0]))
                    _glass(
                      padding: const EdgeInsets.fromLTRB(16, 14, 16, 8),
                      radius: 22,
                      margin: const EdgeInsets.only(bottom: 12),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                        Text(k[1].toUpperCase(),
                            style: const TextStyle(
                                fontSize: 10.5, letterSpacing: 2, color: plum, fontWeight: FontWeight.w700)),
                        const SizedBox(height: 4),
                        for (final QueryDocumentSnapshot<Map<String, dynamic>> d in shown)
                          if ((d.data()['cat'] ?? 'other') == k[0]) _shopRow(d),
                      ]),
                    ),
              Center(
                child: TextButton.icon(
                  onPressed: _h(() => _editShopItem(null)),
                  icon: Icon(Icons.add_rounded, color: ivory.withOpacity(.9), size: 18),
                  label: Text('Add something',
                      style: TextStyle(color: ivory.withOpacity(.9), fontWeight: FontWeight.w700)),
                ),
              ),
              Center(
                child: Text('Tap the circle when it’s bought · tap the name to edit · hold to remove',
                    style: TextStyle(fontSize: 10.5, color: ivory.withOpacity(.6))),
              ),
            ],
          ],
        );
      },
    );
  }

  Widget _shopRow(QueryDocumentSnapshot<Map<String, dynamic>> d) {
    final Map<String, dynamic> it = d.data();
    final bool bought = it['bought'] == true;
    final int qty = it['qty'] is num ? (it['qty'] as num).toInt() : 1;
    final int est = it['est'] is num ? (it['est'] as num).toInt() : 0;
    final String note = (it['note'] ?? '').toString();
    final String link = (it['link'] ?? '').toString();
    return _Press(
      onTap: () => _editShopItem(d),
      onLongPress: () async {
        final Map<String, dynamic> gone = d.data();
        final DocumentReference<Map<String, dynamic>> ref = d.reference;
        await ref.delete();
        _toastUndo('Removed.', () => ref.set(gone));
      },
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
          _Press(
            tick: _Tick.select,
            onTap: () async {
              await d.reference.set(<String, dynamic>{
                'bought': !bought,
                'boughtAt': bought ? FieldValue.delete() : FieldValue.serverTimestamp(),
              }, SetOptions(merge: true));
            },
            child: Container(
              width: 26,
              height: 26,
              margin: const EdgeInsets.only(top: 1),
              decoration: BoxDecoration(
                color: bought ? vGreen : Colors.white,
                shape: BoxShape.circle,
                border: Border.all(color: bought ? vGreen : goldLine, width: 1.6),
              ),
              child: bought ? const Icon(Icons.check_rounded, size: 16, color: Colors.white) : null,
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
              Text('${qty > 1 ? '$qty × ' : ''}${it['name'] ?? ''}',
                  style: TextStyle(
                      color: bought ? muted : ink,
                      fontSize: 13.5,
                      fontWeight: FontWeight.w700,
                      decoration: bought ? TextDecoration.lineThrough : null)),
              if (est > 0 || note.isNotEmpty)
                Text(
                    <String>[
                      if (est > 0) 'about \$$est',
                      if (note.isNotEmpty) note,
                    ].join(' · '),
                    style: const TextStyle(fontSize: 11.5, color: muted, height: 1.35)),
            ]),
          ),
          if (link.isNotEmpty)
            _Press(
              onTap: () async {
                final Uri? u = Uri.tryParse(link);
                if (u != null && await canLaunchUrl(u)) {
                  await launchUrl(u, mode: LaunchMode.externalApplication);
                }
              },
              child: const Padding(
                padding: EdgeInsets.all(4),
                child: Icon(Icons.open_in_new_rounded, size: 16, color: plum),
              ),
            ),
        ]),
      ),
    );
  }

  Widget _registryScreen(Map<String, dynamic> couple) {''', "shopping screen")

# 5. header history line
swap("// (v132: MARRIAGE LICENSE",
     "// (v133: SHOPPING LIST - a screen for the things the couple buys themselves (the registry is what guests buy): items in couples/{cid}/shopping with category, quantity, estimate, link, note and a bought toggle; bought-of-total and dollars-to-go at the top; filter chips by state and category; the classic list seeds 34 items with rough prices; Send to your planner through the send sheet; on the rail, the phone grid and June's open map. JC-LAZO-COUPLE-0920-SHOP-001; base v132) (v132: MARRIAGE LICENSE",
     "header")

OUT.write_text(s, encoding="utf-8", newline="\n")
print(f"wrote {OUT} ({len(s):,} chars)")
