"""patch_couple_v135.py - JC-LAZO-COUPLE-0920-V135
Two Folia moves on the couple dashboard:
  1. COMMENTS ON DREAM BOARD PINS. Each pin carries comments [{by, ini, name,
     text, at}]. Select a pin and Comment opens a thread sheet; a small
     badge on the pin shows the count. Initials come from the signed-in
     partner's display name (or email), so the two of you read as SW / JM.
  2. BUDGET ALLOCATION. The budget card gains an allocation view: every
     category with a planned amount as a bar, its share of the total, the
     spent portion darker, over-allocation in rose; and a last-change line -
     "Catering updated by Sarah · 2h ago" - from the plan doc's updatedAt and
     a new updatedBy the vendor editor now writes.
Applies on top of Couple_master_board.txt -> Couple_master_v135.txt.
Anchor-and-assert.
  python app-patches\\patch_couple_v135.py [src] [out]
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Couple_master_board.txt"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "Couple_master_v135.txt"
s = SRC.read_text(encoding="utf-8")
if "JC-LAZO-COUPLE-0920-V135" in s:
    raise SystemExit("already applied")


def swap(old, new, label, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"ABORT [{label}]: anchor matched {n} times, expected {count}")
    s = s.replace(old, new)
    print(f"  ok  {label}")


# ---------------------------------------------------------------- 1. comments on pins
swap("""  Future<void> _bdShare(Map<String, dynamic> couple) async {""",
     r'''  // v135: who is typing - initials and first name of the signed-in partner.
  List<String> _bdMe() {
    final User? u = FirebaseAuth.instance.currentUser;
    String name = (u?.displayName ?? '').trim();
    if (name.isEmpty) name = (u?.email ?? '').split('@').first;
    if (name.isEmpty) name = 'You';
    final List<String> parts = name.split(RegExp(r'[\s._-]+')).where((String w) => w.isNotEmpty).toList();
    final String ini = parts.take(2).map((String w) => w[0].toUpperCase()).join();
    return <String>[ini.isEmpty ? 'Y' : ini, parts.isEmpty ? 'You' : parts.first];
  }

  List<Map<String, dynamic>> _bdComments(Map<String, dynamic> it) => <Map<String, dynamic>>[
        if (it['comments'] is List)
          for (final dynamic c in it['comments'] as List)
            if (c is Map) Map<String, dynamic>.from(c)
      ];

  Future<void> _bdCommentSheet(Map<String, dynamic> it) async {
    final TextEditingController c = TextEditingController();
    final List<String> me = _bdMe();
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: ivory,
      isScrollControlled: true,
      constraints: const BoxConstraints(maxWidth: 520),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setS) {
          final List<Map<String, dynamic>> cs = _bdComments(it);
          return Padding(
            padding: EdgeInsets.only(bottom: MediaQuery.of(ctx2).viewInsets.bottom),
            child: SafeArea(
              child: Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
                Padding(
                  padding: const EdgeInsets.fromLTRB(22, 18, 14, 6),
                  child: Row(children: <Widget>[
                    if (it['kind'] == 'image')
                      ClipRRect(
                        borderRadius: BorderRadius.circular(8),
                        child: Image.network((it['url'] ?? '').toString(), width: 44, height: 44, fit: BoxFit.cover,
                            errorBuilder: (BuildContext a, Object b, StackTrace? d) => const SizedBox(width: 44, height: 44)),
                      )
                    else
                      Container(
                        width: 44,
                        height: 44,
                        decoration: BoxDecoration(
                            color: Color(int.tryParse('FF${(it['color'] ?? 'F3EBDD').toString()}', radix: 16) ?? 0xFFF3EBDD),
                            borderRadius: BorderRadius.circular(8)),
                      ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                        Text('Talk about this one', style: _serif(size: 22)),
                        Text(
                            ((it['title'] ?? it['text'] ?? '').toString()).isEmpty
                                ? (cs.isEmpty ? 'Nothing yet' : '${cs.length} comment${cs.length == 1 ? '' : 's'}')
                                : (it['title'] ?? it['text']).toString(),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(fontSize: 12.5, color: muted)),
                      ]),
                    ),
                    IconButton(icon: const Icon(Icons.close_rounded, color: muted), onPressed: () => Navigator.pop(ctx2)),
                  ]),
                ),
                Flexible(
                  child: ListView(
                    shrinkWrap: true,
                    padding: const EdgeInsets.fromLTRB(22, 6, 22, 6),
                    children: <Widget>[
                      if (cs.isEmpty)
                        const Padding(
                          padding: EdgeInsets.symmetric(vertical: 14),
                          child: Text('Say what you like about it, or what you’d change. Your partner sees it here too.',
                              style: TextStyle(fontSize: 13, color: muted, height: 1.45)),
                        ),
                      for (final Map<String, dynamic> cm in cs)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                            Container(
                              width: 30,
                              height: 30,
                              alignment: Alignment.center,
                              decoration: BoxDecoration(
                                  color: (cm['by'] ?? '') == (FirebaseAuth.instance.currentUser?.uid ?? '') ? plum : gold,
                                  shape: BoxShape.circle),
                              child: Text((cm['ini'] ?? '?').toString(),
                                  style: TextStyle(
                                      color: (cm['by'] ?? '') == (FirebaseAuth.instance.currentUser?.uid ?? '') ? gold : plumDeep,
                                      fontSize: 11,
                                      fontWeight: FontWeight.w800)),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                                Row(children: <Widget>[
                                  Text((cm['name'] ?? '').toString(), style: const TextStyle(color: plum, fontSize: 12.5, fontWeight: FontWeight.w800)),
                                  const SizedBox(width: 6),
                                  Text(cm['at'] is num ? _ago(Timestamp.fromMillisecondsSinceEpoch((cm['at'] as num).toInt())) : '',
                                      style: const TextStyle(fontSize: 11, color: muted)),
                                ]),
                                Text((cm['text'] ?? '').toString(), style: const TextStyle(color: ink, fontSize: 14, height: 1.4)),
                              ]),
                            ),
                            if ((cm['by'] ?? '') == (FirebaseAuth.instance.currentUser?.uid ?? ''))
                              IconButton(
                                icon: const Icon(Icons.close_rounded, size: 15, color: muted),
                                onPressed: () {
                                  setState(() {
                                    final List<Map<String, dynamic>> all = _bdComments(it);
                                    all.removeWhere((Map<String, dynamic> x) => x['at'] == cm['at'] && x['by'] == cm['by']);
                                    it['comments'] = all;
                                  });
                                  setS(() {});
                                  _bdSave();
                                },
                              ),
                          ]),
                        ),
                    ],
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(22, 6, 22, 18),
                  child: Row(children: <Widget>[
                    Container(
                      width: 30,
                      height: 30,
                      alignment: Alignment.center,
                      decoration: const BoxDecoration(color: plum, shape: BoxShape.circle),
                      child: Text(me[0], style: const TextStyle(color: gold, fontSize: 11, fontWeight: FontWeight.w800)),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: TextField(
                        controller: c,
                        minLines: 1,
                        maxLines: 3,
                        textCapitalization: TextCapitalization.sentences,
                        style: const TextStyle(color: ink, fontSize: 14),
                        decoration: _lightDeco('Candles instead of taper lights?'),
                        onSubmitted: (String v) {
                          if (v.trim().isEmpty) return;
                          setState(() {
                            final List<Map<String, dynamic>> all = _bdComments(it);
                            all.add(<String, dynamic>{
                              'by': FirebaseAuth.instance.currentUser?.uid ?? '',
                              'ini': me[0],
                              'name': me[1],
                              'text': v.trim(),
                              'at': DateTime.now().millisecondsSinceEpoch,
                            });
                            it['comments'] = all;
                          });
                          c.clear();
                          setS(() {});
                          _bdSave();
                        },
                      ),
                    ),
                    const SizedBox(width: 6),
                    IconButton(
                      icon: const Icon(Icons.send_rounded, color: plum),
                      onPressed: () {
                        final String v = c.text.trim();
                        if (v.isEmpty) return;
                        setState(() {
                          final List<Map<String, dynamic>> all = _bdComments(it);
                          all.add(<String, dynamic>{
                            'by': FirebaseAuth.instance.currentUser?.uid ?? '',
                            'ini': me[0],
                            'name': me[1],
                            'text': v,
                            'at': DateTime.now().millisecondsSinceEpoch,
                          });
                          it['comments'] = all;
                        });
                        c.clear();
                        setS(() {});
                        _bdSave();
                      },
                    ),
                  ]),
                ),
              ]),
            ),
          );
        },
      ),
    );
  }

  Future<void> _bdShare(Map<String, dynamic> couple) async {''', "comment sheet")

swap("""                  if (sel['kind'] == 'note') tool(Icons.edit_rounded, 'Edit', () => _bdAddNote(sel)),""",
     """                  tool(Icons.mode_comment_outlined,
                      _bdComments(sel).isEmpty ? 'Comment' : '${_bdComments(sel).length} comment${_bdComments(sel).length == 1 ? '' : 's'}',
                      () => _bdCommentSheet(sel)),
                  if (sel['kind'] == 'note') tool(Icons.edit_rounded, 'Edit', () => _bdAddNote(sel)),""",
     "comment tool")

swap("""          if (sel)
            Positioned(
              right: -8,
              bottom: -8,
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onPanStart: (DragStartDetails d) => _bdDragging = true,""",
     """          if (_bdComments(it).isNotEmpty)
            Positioned(
              left: -6,
              top: -6,
              child: GestureDetector(
                onTap: () => _bdCommentSheet(it),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                  decoration: BoxDecoration(
                      color: plum, borderRadius: BorderRadius.circular(999), border: Border.all(color: ivory, width: 1.5)),
                  child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
                    const Icon(Icons.mode_comment_rounded, size: 10, color: gold),
                    const SizedBox(width: 3),
                    Text('${_bdComments(it).length}', style: const TextStyle(color: gold, fontSize: 10, fontWeight: FontWeight.w800)),
                  ]),
                ),
              ),
            ),
          if (sel)
            Positioned(
              right: -8,
              bottom: -8,
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onPanStart: (DragStartDetails d) => _bdDragging = true,""",
     "comment badge")

# share page carries the comments under each picture
swap("""        h.write('<div><a href="${_esc(src.isEmpty ? u : src)}"><img src="${_esc(u)}" style="width:100%;border-radius:10px;display:block" alt=""></a>${cap.isEmpty ? '' : '<div style="font-size:12px;color:#6B5F72;margin-top:4px">' + _esc(cap) + '</div>'}</div>');""",
     """        final List<Map<String, dynamic>> cms = _bdComments(i);
        h.write('<div><a href="${_esc(src.isEmpty ? u : src)}"><img src="${_esc(u)}" style="width:100%;border-radius:10px;display:block" alt=""></a>${cap.isEmpty ? '' : '<div style="font-size:12px;color:#6B5F72;margin-top:4px">' + _esc(cap) + '</div>'}'
            '${cms.isEmpty ? '' : '<div style="font-size:11.5px;color:#52284F;margin-top:4px">' + cms.map((Map<String, dynamic> x) => '<b>' + _esc((x['name'] ?? '').toString()) + ':</b> ' + _esc((x['text'] ?? '').toString())).join('<br>') + '</div>'}</div>');""",
     "share comments")

# ---------------------------------------------------------------- 2. budget allocation
swap("""    await _planRef.doc(slug).set({
      'vendorName': nameC.text.trim(),
      'budgetPlanned': double.tryParse(planC.text.trim()),
      'budgetActual': double.tryParse(spentC.text.trim()),
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));""",
     """    await _planRef.doc(slug).set({
      'vendorName': nameC.text.trim(),
      'budgetPlanned': double.tryParse(planC.text.trim()),
      'budgetActual': double.tryParse(spentC.text.trim()),
      'updatedAt': FieldValue.serverTimestamp(),
      'updatedBy': _bdMe()[1], // v135: the last-change line on the budget card
    }, SetOptions(merge: true));""",
     "budget updatedBy")

swap("""          if (byCat.isNotEmpty) ...<Widget>[
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: byCat
                  .take(4)""",
     """          // v135: allocation - every planned category as a share of the total.
          ...(() {
            final List<Widget> out = <Widget>[];
            final List<List<dynamic>> rows = <List<dynamic>>[];
            Timestamp? latestAt;
            String latestLine = '';
            for (final Map<String, String> c in kCategories) {
              final Map<String, dynamic> p = plan[c['slug']] ?? const <String, dynamic>{};
              final num pl = (p['budgetPlanned'] as num?) ?? 0;
              final num sp = (p['budgetActual'] as num?) ?? 0;
              if (pl > 0 || sp > 0) rows.add(<dynamic>[c['label'], pl, sp]);
              final dynamic ua = p['updatedAt'];
              if (ua is Timestamp && (latestAt == null || ua.compareTo(latestAt!) > 0) && (pl > 0 || sp > 0)) {
                latestAt = ua;
                final String by = (p['updatedBy'] ?? '').toString();
                latestLine = '${c['label']} updated${by.isEmpty ? '' : ' by $by'} \\u00b7 ${_ago(ua)}';
              }
            }
            if (rows.isEmpty) return out;
            rows.sort((List<dynamic> a, List<dynamic> b) => ((b[1] as num) > 0 ? b[1] as num : b[2] as num).compareTo((a[1] as num) > 0 ? a[1] as num : a[2] as num));
            final num allocated = rows.fold<num>(0, (num acc, List<dynamic> r) => acc + (r[1] as num));
            final bool overAlloc = allocated > total;
            out.add(const SizedBox(height: 14));
            out.add(Row(children: <Widget>[
              const Expanded(
                child: Text('ALLOCATION',
                    style: TextStyle(fontSize: 10.5, letterSpacing: 2, color: plum, fontWeight: FontWeight.w700)),
              ),
              Text('${_money(allocated)} planned \\u00b7 ${(allocated / total * 100).round()}%',
                  style: TextStyle(fontSize: 11.5, color: overAlloc ? const Color(0xFFB3413A) : muted, fontWeight: FontWeight.w700)),
            ]));
            out.add(const SizedBox(height: 6));
            for (final List<dynamic> r in rows.take(8)) {
              final num pl = r[1] as num;
              final num sp = r[2] as num;
              final double share = (pl / total).clamp(0.0, 1.0).toDouble();
              final double spentShare = (sp / total).clamp(0.0, 1.0).toDouble();
              out.add(_Press(
                onTap: () => setState(() => _view = _View.vendors),
                child: Padding(
                  padding: const EdgeInsets.only(bottom: 7),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                    Row(children: <Widget>[
                      Expanded(child: Text(r[0].toString(), style: const TextStyle(color: ink, fontSize: 12.5, fontWeight: FontWeight.w700))),
                      Text('${pl > 0 ? (pl / total * 100).round() : 0}% \\u00b7 ${_money(pl > 0 ? pl : sp)}${sp > 0 && pl > 0 ? ' \\u00b7 ${_money(sp)} spent' : ''}',
                          style: TextStyle(fontSize: 11.5, color: sp > pl && pl > 0 ? const Color(0xFFB3413A) : muted)),
                    ]),
                    const SizedBox(height: 4),
                    SizedBox(
                      height: 6,
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(999),
                        child: Stack(fit: StackFit.expand, children: <Widget>[
                          Container(color: plum.withOpacity(.08)),
                          Align(alignment: Alignment.centerLeft, child: FractionallySizedBox(widthFactor: share, heightFactor: 1, child: Container(color: gold.withOpacity(.75)))),
                          Align(alignment: Alignment.centerLeft, child: FractionallySizedBox(widthFactor: spentShare, heightFactor: 1, child: Container(color: sp > pl && pl > 0 ? const Color(0xFFB3413A) : plum))),
                        ]),
                      ),
                    ),
                  ]),
                ),
              ));
            }
            if (rows.length > 8) {
              out.add(Text('and ${rows.length - 8} more', style: const TextStyle(fontSize: 11.5, color: muted)));
            }
            if (latestLine.isNotEmpty) {
              out.add(Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Row(children: <Widget>[
                  const Icon(Icons.history_rounded, size: 13, color: muted),
                  const SizedBox(width: 5),
                  Expanded(child: Text(latestLine, style: const TextStyle(fontSize: 11.5, color: muted))),
                ]),
              ));
            }
            return out;
          })(),
          if (byCat.isNotEmpty) ...<Widget>[
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: byCat
                  .take(4)""",
     "budget allocation view")

swap("// (v134: DREAM BOARD",
     "// (v135: COMMENTS + ALLOCATION - each dream-board pin has a comment thread (partner initials, delete your own, counted on a badge, printed under the picture on the shared page); the budget card shows every planned category as a bar with its share of the total, spent darker, over-allocation in rose, and a last-change line from the plan doc's updatedAt / updatedBy. JC-LAZO-COUPLE-0920-V135; base v134) (v134: DREAM BOARD",
     "header")

OUT.write_text(s, encoding="utf-8", newline="\n")
print(f"wrote {OUT} ({len(s):,} chars)")
