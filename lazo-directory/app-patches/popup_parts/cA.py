# Popup pass JC-LAZO-POPUP-1014, part cA (couple dashboard).
# Each rep() swaps one whole assigned function (plus cA helpers placed right after
# _dayBeforeSheet and _sendInquiry) for its rebuilt version.

def apply(s: str) -> str:
    def rep(old, new):
        nonlocal s
        assert s.count(old) == 1, (s.count(old), old[:80])
        s = s.replace(old, new)

    # _positionSheet
    rep(r"""  Future<Map<String, dynamic>?> _positionSheet({
    required Map<String, dynamic> photo,
    required String title,
    required String hint,
    required List<List<dynamic>> frames, // [label, width/height]
    bool canChoose = true,
    bool canRemove = true,
  }) async {
    final String url = (photo['url'] ?? '').toString();
    double fx = ((photo['x'] as num?) ?? .5).toDouble();
    double fy = ((photo['y'] as num?) ?? .5).toDouble();
    double fz =
        ((photo['zoom'] as num?) ?? 1).toDouble().clamp(1.0, 3.0).toDouble();
    int frame = 0;
    Size? nat;
    _imgSize(url).then((Size? v) => nat = v);
    if (!mounted) {
      return null;
    }
    return _lzSheet<Map<String, dynamic>>(
      context: context,
      isScrollControlled: true,
      backgroundColor: _lzBg(ivory),
      constraints: const BoxConstraints(maxWidth: 620),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) {
          final double aspect = (frames[frame][1] as num).toDouble();
          return Padding(
            padding: EdgeInsets.fromLTRB(
                20, 14, 20, 20 + MediaQuery.of(ctx2).viewInsets.bottom),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Center(
                  child: Container(
                      width: 40,
                      height: 4,
                      decoration: BoxDecoration(
                          color: plum.withOpacity(.25),
                          borderRadius: BorderRadius.circular(4))),
                ),
                const SizedBox(height: 14),
                Text(title,
                    style:
                        _serif(size: 24, weight: FontWeight.w600, color: _lzFg(plum))),
                const SizedBox(height: 4),
                Text(hint,
                    style:  TextStyle(
                        color: _lzFg(muted), fontSize: 13.5, height: 1.4)),
                if (frames.length > 1) ...<Widget>[
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 8,
                    children: frames.asMap().entries.map(
                        (MapEntry<int, List<dynamic>> e) {
                      final bool sel = e.key == frame;
                      return ChoiceChip(
                        label: Text(e.value[0] as String,
                            style: TextStyle(
                                color: _lzFg(sel ? plum : ivory),
                                fontSize: 12,
                                fontWeight: FontWeight.w700)),
                        selected: sel,
                        selectedColor: gold,
                        backgroundColor: plum,
                        showCheckmark: false,
                        onSelected: (bool v) {
                          HapticFeedback.selectionClick();
                          setD(() => frame = e.key);
                        },
                      );
                    }).toList(),
                  ),
                ],
                const SizedBox(height: 14),
                LayoutBuilder(builder: (BuildContext lc, BoxConstraints cons) {
                  double w = cons.maxWidth;
                  double h = w / aspect;
                  final double maxH =
                      MediaQuery.of(ctx2).size.height * .42;
                  if (h > maxH) {
                    h = maxH;
                    w = h * aspect;
                  }
                  return Center(
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(18),
                      child: GestureDetector(
                        behavior: HitTestBehavior.opaque,
                        onPanUpdate: (DragUpdateDetails d) {
                          // how far the picture can slide inside the frame at
                          // this zoom; the finger moves it that far, so the
                          // focus point moves the opposite way in proportion
                          double px, py;
                          final Size? n = nat;
                          if (n != null && n.width > 0 && n.height > 0) {
                            final double sc =
                                math.max(w / n.width, h / n.height);
                            px = n.width * sc * fz - w;
                            py = n.height * sc * fz - h;
                          } else {
                            px = w * fz * .6;
                            py = h * fz * .6;
                          }
                          setD(() {
                            if (px > 2) {
                              fx = (fx - d.delta.dx / px).clamp(0.0, 1.0).toDouble();
                            }
                            if (py > 2) {
                              fy = (fy - d.delta.dy / py).clamp(0.0, 1.0).toDouble();
                            }
                          });
                        },
                        child: SizedBox(
                          width: w,
                          height: h,
                          child: Stack(fit: StackFit.expand, children: <Widget>[
                            const ColoredBox(color: plumDeep),
                            _placed(<String, dynamic>{
                              'url': url,
                              'x': fx,
                              'y': fy,
                              'zoom': fz
                            }),
                            Positioned(
                              left: 14,
                              bottom: 12,
                              child: Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 9, vertical: 5),
                                decoration: BoxDecoration(
                                    color: plumDeep.withOpacity(.55),
                                    borderRadius: BorderRadius.circular(999)),
                                child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: <Widget>[
                                      const Icon(Icons.open_with_rounded,
                                          color: ivory, size: 14),
                                      const SizedBox(width: 6),
                                      Text('Drag to move',
                                          style: TextStyle(
                                              color: ivory.withOpacity(.9),
                                              fontSize: 12,
                                              fontWeight: FontWeight.w600)),
                                    ]),
                              ),
                            ),
                          ]),
                        ),
                      ),
                    ),
                  );
                }),
                const SizedBox(height: 8),
                Row(children: <Widget>[
                   Icon(Icons.zoom_out_rounded, color: _lzFg(muted), size: 18),
                  Expanded(
                    child: SliderTheme(
                      data: SliderTheme.of(ctx2).copyWith(
                          activeTrackColor: gold,
                          inactiveTrackColor: gold.withOpacity(.25),
                          thumbColor: plum,
                          overlayColor: gold.withOpacity(.2),
                          trackHeight: 3),
                      child: Slider(
                        value: fz,
                        min: 1,
                        max: 3,
                        onChanged: (double v) => setD(() => fz = v),
                        onChangeEnd: (double v) =>
                            HapticFeedback.selectionClick(),
                      ),
                    ),
                  ),
                   Icon(Icons.zoom_in_rounded, color: _lzFg(muted), size: 18),
                ]),
                const SizedBox(height: 6),
                Wrap(
                  spacing: 2,
                  runSpacing: 2,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: <Widget>[
                    TextButton.icon(
                      onPressed: _h(() => setD(() {
                            fx = .5;
                            fy = .5;
                            fz = 1;
                          })),
                      icon:  Icon(Icons.center_focus_strong_rounded,
                          color: _lzFg(plum), size: 18),
                      label:
                           Text('Center', style: TextStyle(color: _lzFg(plum))),
                    ),
                    if (canChoose)
                      TextButton.icon(
                        onPressed: _h(() => Navigator.pop(
                            ctx2, <String, dynamic>{'choose': true})),
                        icon:  Icon(Icons.photo_camera_rounded,
                            color: _lzFg(plum), size: 18),
                        label:  Text('Different photo',
                            style: TextStyle(color: _lzFg(plum))),
                      ),
                    if (canRemove)
                      TextButton.icon(
                        onPressed: _h(() => Navigator.pop(
                            ctx2, <String, dynamic>{'remove': true})),
                        icon:  Icon(Icons.delete_outline_rounded,
                            color: _lzFg(rose), size: 18),
                        label:  Text('Remove',
                            style: TextStyle(color: _lzFg(rose))),
                      ),
                  ],
                ),
                const SizedBox(height: 6),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    style: FilledButton.styleFrom(
                        backgroundColor: gold,
                        foregroundColor: plumDeep,
                        padding: const EdgeInsets.symmetric(vertical: 13),
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12))),
                    onPressed: _h(
                        () => Navigator.pop(ctx2, <String, dynamic>{
                              'url': url,
                              'x': fx,
                              'y': fy,
                              'zoom': double.parse(fz.toStringAsFixed(2)),
                            }),
                        _Tick.medium),
                    child: const Text('Use this',
                        style: TextStyle(fontWeight: FontWeight.w700)),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }""",
        r"""  Future<Map<String, dynamic>?> _positionSheet({
    required Map<String, dynamic> photo,
    required String title,
    required String hint,
    required List<List<dynamic>> frames, // [label, width/height]
    bool canChoose = true,
    bool canRemove = true,
  }) async {
    final String url = (photo['url'] ?? '').toString();
    double fx = ((photo['x'] as num?) ?? .5).toDouble();
    double fy = ((photo['y'] as num?) ?? .5).toDouble();
    double fz =
        ((photo['zoom'] as num?) ?? 1).toDouble().clamp(1.0, 3.0).toDouble();
    int frame = 0;
    Size? nat;
    _imgSize(url).then((Size? v) => nat = v);
    if (!mounted) {
      return null;
    }
    return _lzSheet<Map<String, dynamic>>(
      context: context,
      isScrollControlled: true,
      backgroundColor: _lzBg(ivory),
      constraints: const BoxConstraints(maxWidth: 620),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) {
          final double aspect = (frames[frame][1] as num).toDouble();
          return Padding(
            padding: EdgeInsets.fromLTRB(
                20, 10, 12, 20 +MediaQuery.of(ctx2).viewInsets.bottom),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: Text(title,
                          style: _serif(
                              size: 24, weight: FontWeight.w600, color: _lzFg(plum))),
                    ),
                  ),
                  IconButton(
                      tooltip: 'Close',
                      icon: Icon(Icons.close_rounded, color: _lzFg(muted)),
                      onPressed: _h(() => Navigator.of(ctx2).maybePop())),
                ]),
                const SizedBox(height: 4),
                Text(hint,
                    style:  TextStyle(
                        color: _lzFg(muted), fontSize: 13.5, height: 1.4)),
                if (frames.length > 1) ...<Widget>[
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 8,
                    children: frames.asMap().entries.map(
                        (MapEntry<int, List<dynamic>> e) {
                      final bool sel = e.key == frame;
                      return ChoiceChip(
                        label: Text(e.value[0] as String,
                            style: TextStyle(
                                color: _lzFg(sel ? plum : ivory),
                                fontSize: 12,
                                fontWeight: FontWeight.w700)),
                        selected: sel,
                        selectedColor: gold,
                        backgroundColor: plum,
                        showCheckmark: false,
                        onSelected: (bool v) {
                          HapticFeedback.selectionClick();
                          setD(() => frame = e.key);
                        },
                      );
                    }).toList(),
                  ),
                ],
                const SizedBox(height: 14),
                LayoutBuilder(builder: (BuildContext lc, BoxConstraints cons) {
                  double w = cons.maxWidth;
                  double h = w / aspect;
                  final double maxH =
                      MediaQuery.of(ctx2).size.height * .42;
                  if (h > maxH) {
                    h = maxH;
                    w = h * aspect;
                  }
                  return Center(
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(18),
                      child: GestureDetector(
                        behavior: HitTestBehavior.opaque,
                        onPanUpdate: (DragUpdateDetails d) {
                          // how far the picture can slide inside the frame at
                          // this zoom; the finger moves it that far, so the
                          // focus point moves the opposite way in proportion
                          double px, py;
                          final Size? n = nat;
                          if (n != null && n.width > 0 && n.height > 0) {
                            final double sc =
                                math.max(w / n.width, h / n.height);
                            px = n.width * sc * fz - w;
                            py = n.height * sc * fz - h;
                          } else {
                            px = w * fz * .6;
                            py = h * fz * .6;
                          }
                          setD(() {
                            if (px > 2) {
                              fx = (fx - d.delta.dx / px).clamp(0.0, 1.0).toDouble();
                            }
                            if (py > 2) {
                              fy = (fy - d.delta.dy / py).clamp(0.0, 1.0).toDouble();
                            }
                          });
                        },
                        child: SizedBox(
                          width: w,
                          height: h,
                          child: Stack(fit: StackFit.expand, children: <Widget>[
                            const ColoredBox(color: plumDeep),
                            _placed(<String, dynamic>{
                              'url': url,
                              'x': fx,
                              'y': fy,
                              'zoom': fz
                            }),
                            Positioned(
                              left: 14,
                              bottom: 12,
                              child: Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 9, vertical: 5),
                                decoration: BoxDecoration(
                                    color: plumDeep.withOpacity(.55),
                                    borderRadius: BorderRadius.circular(999)),
                                child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: <Widget>[
                                      const Icon(Icons.open_with_rounded,
                                          color: ivory, size: 14),
                                      const SizedBox(width: 6),
                                      Text('Drag to move',
                                          style: TextStyle(
                                              color: ivory.withOpacity(.9),
                                              fontSize: 12,
                                              fontWeight: FontWeight.w600)),
                                    ]),
                              ),
                            ),
                          ]),
                        ),
                      ),
                    ),
                  );
                }),
                const SizedBox(height: 8),
                Row(children: <Widget>[
                   Icon(Icons.zoom_out_rounded, color: _lzFg(muted), size: 18),
                  Expanded(
                    child: SliderTheme(
                      data: SliderTheme.of(ctx2).copyWith(
                          activeTrackColor: gold,
                          inactiveTrackColor: gold.withOpacity(.25),
                          thumbColor: plum,
                          overlayColor: gold.withOpacity(.2),
                          trackHeight: 3),
                      child: Slider(
                        value: fz,
                        min: 1,
                        max: 3,
                        onChanged: (double v) => setD(() => fz = v),
                        onChangeEnd: (double v) =>
                            HapticFeedback.selectionClick(),
                      ),
                    ),
                  ),
                   Icon(Icons.zoom_in_rounded, color: _lzFg(muted), size: 18),
                ]),
                const SizedBox(height: 6),
                Wrap(
                  spacing: 2,
                  runSpacing: 2,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: <Widget>[
                    TextButton.icon(
                      onPressed: _h(() => setD(() {
                            fx = .5;
                            fy = .5;
                            fz = 1;
                          })),
                      icon:  Icon(Icons.center_focus_strong_rounded,
                          color: _lzFg(plum), size: 18),
                      label:
                           Text('Center', style: TextStyle(color: _lzFg(plum))),
                    ),
                    if (canChoose)
                      TextButton.icon(
                        onPressed: _h(() => Navigator.pop(
                            ctx2, <String, dynamic>{'choose': true})),
                        icon:  Icon(Icons.photo_camera_rounded,
                            color: _lzFg(plum), size: 18),
                        label:  Text('Different photo',
                            style: TextStyle(color: _lzFg(plum))),
                      ),
                    if (canRemove)
                      TextButton.icon(
                        onPressed: _h(() => Navigator.pop(
                            ctx2, <String, dynamic>{'remove': true})),
                        icon:  Icon(Icons.delete_outline_rounded,
                            color: _lzFg(rose), size: 18),
                        label:  Text('Remove',
                            style: TextStyle(color: _lzFg(rose))),
                      ),
                  ],
                ),
                const SizedBox(height: 6),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    style: FilledButton.styleFrom(
                        backgroundColor: gold,
                        foregroundColor: plumDeep,
                        padding: const EdgeInsets.symmetric(vertical: 13),
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12))),
                    onPressed: _h(
                        () => Navigator.pop(ctx2, <String, dynamic>{
                              'url': url,
                              'x': fx,
                              'y': fy,
                              'zoom': double.parse(fz.toStringAsFixed(2)),
                            }),
                        _Tick.medium),
                    child: const Text('Use this',
                        style: TextStyle(fontWeight: FontWeight.w700)),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }""")

    # _dayBeforeSheet
    rep(r"""  Future<void> _dayBeforeSheet(String slug, Map<String, dynamic> w) async {
    final TextEditingController noteC = TextEditingController(
        text: (w['dayBeforeNote'] ?? '').toString().isNotEmpty
            ? (w['dayBeforeNote'] ?? '').toString()
            : 'We can’t wait to see you tomorrow. Here’s everything you need for the day.');
    bool busy = false;
    String status = w['dayBeforeSentAt'] != null
        ? 'Sent once already to ${w['dayBeforeSentTo'] ?? '?'} guests.'
        : '';
    if (!mounted) {
      return;
    }
    await _lzSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: _lzBg(ivory),
      constraints: const BoxConstraints(maxWidth: 620),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) {
          Future<void> send(bool test) async {
            setD(() => busy = true);
            final Map<String, dynamic> r = await _workerPost(
                'https://meetlazo.com/api/w/$slug/day-before', <String, dynamic>{
              'test': test,
              'note': noteC.text.trim(),
              'replyTo': FirebaseAuth.instance.currentUser?.email ?? '',
            });
            try {
              await FirebaseFirestore.instance
                  .collection('weddingSites')
                  .doc(slug)
                  .set(<String, dynamic>{'dayBeforeNote': noteC.text.trim()},
                      SetOptions(merge: true));
            } catch (_) {}
            setD(() {
              busy = false;
              status = r['ok'] == true
                  ? (test
                      ? 'Test sent to ${FirebaseAuth.instance.currentUser?.email ?? 'you'} ✓'
                      : 'Sent to ${r['sent']} guest${r['sent'] == 1 ? '' : 's'}${(r['failed'] ?? 0) != 0 ? ' (${r['failed']} failed)' : ''} ✓')
                  : (r['message'] ?? 'Could not send — ${r['error'] ?? 'try again'}.')
                      .toString();
            });
          }

          return Padding(
            padding: EdgeInsets.fromLTRB(
                20, 14, 20, 20 + MediaQuery.of(ctx2).viewInsets.bottom),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Center(
                  child: Container(
                      width: 40,
                      height: 4,
                      decoration: BoxDecoration(
                          color: plum.withOpacity(.25),
                          borderRadius: BorderRadius.circular(4))),
                ),
                const SizedBox(height: 14),
                Text('The day-before note',
                    style:
                        _serif(size: 24, weight: FontWeight.w600, color: _lzFg(plum))),
                const SizedBox(height: 4),
                 Text(
                    'One email to everyone coming who left an address: your line, the day hour by hour, the venue with a map, parking, the forecast, and each guest’s table if the seat finder is on. Replies come to you.',
                    style:
                        TextStyle(color: _lzFg(muted), fontSize: 13.5, height: 1.4)),
                const SizedBox(height: 14),
                TextField(
                    controller: noteC,
                    maxLines: 3,
                    maxLength: 600,
                    style:  TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _lightDeco('A line from the two of you')),
                const SizedBox(height: 6),
                if (status.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Text(status,
                        style:  TextStyle(
                            color: _lzFg(plum),
                            fontSize: 13,
                            fontWeight: FontWeight.w600)),
                  ),
                Row(children: <Widget>[
                  OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(
                        foregroundColor: _lzFg(plum),
                        side: BorderSide(color: gold.withOpacity(.8))),
                    onPressed: _h(busy ? null : () => send(true)),
                    icon: const Icon(Icons.send_rounded, size: 15),
                    label: const Text('Send a test to me'),
                  ),
                  const Spacer(),
                  FilledButton(
                    style: FilledButton.styleFrom(
                        backgroundColor: gold, foregroundColor: plumDeep),
                    onPressed: _h(
                        busy
                            ? null
                            : () async {
                                final bool? sure = await _lzDialog<bool>(
                                  context: ctx2,
                                  builder: (BuildContext dc) => AlertDialog(
                                    backgroundColor: _lzBg(ivory),
                                    title: const Text('Send to everyone?',
                                        style: TextStyle(color: plum)),
                                    content: const Text(
                                        'Every guest who is coming and left an email gets it now.',
                                        style: TextStyle(
                                            color: ink, fontSize: 14)),
                                    actions: <Widget>[
                                      TextButton(
                                          onPressed: () =>
                                              Navigator.pop(dc, false),
                                          child: const Text('Not yet',
                                              style:
                                                  TextStyle(color: ink))),
                                      FilledButton(
                                          style: FilledButton.styleFrom(
                                              backgroundColor: gold,
                                              foregroundColor: plumDeep),
                                          onPressed: () =>
                                              Navigator.pop(dc, true),
                                          child: const Text('Send')),
                                    ],
                                  ),
                                );
                                if (sure == true) {
                                  await send(false);
                                }
                              },
                        _Tick.medium),
                    child: Text(busy ? 'Sending…' : 'Send to everyone',
                        style: const TextStyle(fontWeight: FontWeight.w700)),
                  ),
                ]),
              ],
            ),
          );
        },
      ),
    );
  }""",
        r"""  Future<void> _dayBeforeSheet(String slug, Map<String, dynamic> w) async {
    final TextEditingController noteC = TextEditingController(
        text: (w['dayBeforeNote'] ?? '').toString().isNotEmpty
            ? (w['dayBeforeNote'] ?? '').toString()
            : 'We can’t wait to see you tomorrow. Here’s everything you need for the day.');
    bool busy = false;
    bool testing = false;
    bool ok = true;
    bool open = true;
    String status = w['dayBeforeSentAt'] != null
        ? 'Sent once already, to ${w['dayBeforeSentTo'] ?? 'your'} guests.'
        : '';
    if (!mounted) {
      return;
    }
    await _lzSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: _lzBg(ivory),
      constraints: const BoxConstraints(maxWidth: 620),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) {
          void up(VoidCallback f) {
            if (open) setD(f);
          }

          Future<void> send(bool test) async {
            up(() {
              busy = true;
              testing = test;
            });
            final Map<String, dynamic> r = await _workerPost(
                'https://meetlazo.com/api/w/$slug/day-before', <String, dynamic>{
              'test': test,
              'note': noteC.text.trim(),
              'replyTo': FirebaseAuth.instance.currentUser?.email ?? '',
            });
            try {
              await FirebaseFirestore.instance
                  .collection('weddingSites')
                  .doc(slug)
                  .set(<String, dynamic>{'dayBeforeNote': noteC.text.trim()},
                      SetOptions(merge: true));
            } catch (_) {}
            up(() {
              busy = false;
              ok = r['ok'] == true;
              status = ok
                  ? (test
                      ? 'Test sent to ${FirebaseAuth.instance.currentUser?.email ?? 'you'}.'
                      : 'Sent to ${r['sent']} guest${r['sent'] == 1 ? '' : 's'}${(r['failed'] ?? 0) != 0 ? ' (${r['failed']} didn’t go through)' : ''}.')
                  : (r['message'] ?? 'Couldn’t send - ${r['error'] ?? 'try again'}.')
                      .toString();
            });
          }

          return _lzFrame(ctx2,
              icon: Icons.mark_email_unread_outlined,
              title: 'The day-before note',
              subtitle: 'One email to every guest who’s coming. Replies come to you.',
              children: <Widget>[
                const SizedBox(height: 14),
                TextField(
                    controller: noteC,
                    autofocus: false,
                    enabled: !busy,
                    minLines: 2,
                    maxLines: 4,
                    maxLength: 600,
                    textCapitalization: TextCapitalization.sentences,
                    style: TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _lightDeco('A line from the two of you')),
                _lzSection('What else is in it'),
                Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                  for (final List<dynamic> e in <List<dynamic>>[
                    <dynamic>[Icons.schedule_rounded, 'The day, hour by hour'],
                    <dynamic>[Icons.place_outlined, 'Venue and map'],
                    <dynamic>[Icons.local_parking_rounded, 'Parking'],
                    <dynamic>[Icons.wb_sunny_outlined, 'The forecast'],
                    <dynamic>[Icons.event_seat_outlined, 'Their table, if seat finder is on'],
                  ])
                    _pcA_chip(e[0] as IconData, e[1] as String),
                ]),
                const SizedBox(height: 14),
                if (busy)
                  _lzBusy(testing ? 'Sending a test to you…' : 'Sending to your guests…')
                else if (status.isNotEmpty)
                  _pcA_status(status, ok),
              ],
              footer: _lzActions(
                  secondary: 'Send a test to me',
                  onSecondary: () => send(true),
                  primary: 'Send to everyone',
                  icon: Icons.send_rounded,
                  busy: busy,
                  onPrimary: () async {
                    final bool sure = await _lzConfirm('Send to everyone?',
                        'Every guest who’s coming and left an email gets it now.',
                        confirm: 'Send it', cancel: 'Not yet', icon: Icons.send_rounded);
                    if (sure) {
                      await send(false);
                    }
                  }));
        },
      ),
    );
    open = false;
  }

  // ---- cA popup helpers (JC-LAZO-POPUP-1014) ----
  // a result line inside a popup: green check when it worked, red when not
  Widget _pcA_status(String text, bool ok) => Container(
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
        decoration: BoxDecoration(
            color: ok
                ? vGreen.withOpacity(.10)
                : _lzBg(const Color(0xFFFBEAEA)),
            borderRadius: BorderRadius.circular(13)),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
          Icon(ok ? Icons.check_circle_rounded : Icons.error_outline_rounded,
              size: 18, color: ok ? vGreen : const Color(0xFFB3261E)),
          const SizedBox(width: 10),
          Expanded(
              child: Text(text,
                  style: TextStyle(fontSize: 13.5, color: _lzFg(ink), height: 1.4))),
        ]),
      );

  // a small non-tappable chip: an icon and a few words
  Widget _pcA_chip(IconData icon, String label) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 7),
        decoration: BoxDecoration(
            color: _lzBg(cardBg),
            borderRadius: BorderRadius.circular(30),
            border: Border.all(color: _lzLine(goldLine))),
        child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
          Icon(icon, size: 15, color: _lzFg(plum)),
          const SizedBox(width: 6),
          Text(label,
              style: TextStyle(
                  fontSize: 12.5, fontWeight: FontWeight.w600, color: _lzFg(plum))),
        ]),
      );

  // a tappable choice card: icon, title, one line; gold border when picked
  Widget _pcA_pick(IconData icon, String title, String sub, bool sel, VoidCallback? onTap) =>
      _Press(
        scale: .985,
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          padding: const EdgeInsets.fromLTRB(14, 13, 12, 13),
          decoration: BoxDecoration(
              color: sel ? plumDeep : _lzBg(cardBg),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                  color: sel ? plumDeep : _lzLine(goldLine), width: sel ? 1.4 : 1)),
          child: Row(children: <Widget>[
            Icon(icon, color: sel ? gold : _lzFg(plum), size: 21),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                Text(title,
                    style: TextStyle(
                        fontSize: 14.5,
                        fontWeight: FontWeight.w700,
                        color: sel ? ivory : _lzFg(plum))),
                if (sub.isNotEmpty) ...<Widget>[
                  const SizedBox(height: 2),
                  Text(sub,
                      style: TextStyle(
                          fontSize: 12.5,
                          height: 1.35,
                          color: sel ? ivory.withOpacity(.75) : _lzFg(muted))),
                ],
              ]),
            ),
            if (sel) const Icon(Icons.check_circle_rounded, color: gold, size: 20),
          ]),
        ),
      );

  // an empty state inside a popup: icon, one line, and (optionally) the action
  Widget _pcA_empty(IconData icon, String text, {String? action, VoidCallback? onAction}) =>
      Padding(
        padding: const EdgeInsets.symmetric(vertical: 22),
        child: Column(children: <Widget>[
          Container(
              width: 54,
              height: 54,
              decoration: BoxDecoration(
                  color: _lzBg(const Color(0xFFF6EEDF)), shape: BoxShape.circle),
              child: Icon(icon, color: _lzFg(plum), size: 26)),
          const SizedBox(height: 12),
          Text(text,
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 14, color: _lzFg(muted), height: 1.45)),
          if (action != null && onAction != null) ...<Widget>[
            const SizedBox(height: 10),
            TextButton.icon(
                style: TextButton.styleFrom(foregroundColor: _lzFg(plum)),
                onPressed: _h(onAction),
                icon: const Icon(Icons.add_rounded, size: 18),
                label: Text(action, style: const TextStyle(fontWeight: FontWeight.w700))),
          ],
        ]),
      );""")

    # _pendingPhotosSheet
    rep(r"""  Future<void> _pendingPhotosSheet(String slug) async {
    Map<String, dynamic> j = await _workerGet(
        'https://meetlazo.com/api/w/$slug/photos?pending=1&t=${DateTime.now().millisecondsSinceEpoch}');
    List<Map<String, dynamic>> list = ((j['photos'] as List?) ?? const <dynamic>[])
        .whereType<Map>()
        .map((Map e) => Map<String, dynamic>.from(e))
        .toList();
    if (!mounted) {
      return;
    }
    await _lzSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: _lzBg(ivory),
      constraints: const BoxConstraints(maxWidth: 720),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) {
          Future<void> act(List<String> ids, bool decline) async {
            final Map<String, dynamic> r = await _workerPost(
                'https://meetlazo.com/api/w/$slug/photos/approve',
                <String, dynamic>{'ids': ids, 'decline': decline});
            if (r['ok'] == true) {
              setD(() => list.removeWhere(
                  (Map<String, dynamic> p) => ids.contains(p['id'])));
              _gpFuture = null;
              _toastC(decline
                  ? 'Declined ✓'
                  : 'On the wall ✓');
            } else {
              _toastC('Could not do that — try again.');
            }
          }

          return Padding(
            padding: const EdgeInsets.fromLTRB(20, 14, 20, 20),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Center(
                  child: Container(
                      width: 40,
                      height: 4,
                      decoration: BoxDecoration(
                          color: plum.withOpacity(.25),
                          borderRadius: BorderRadius.circular(4))),
                ),
                const SizedBox(height: 14),
                Row(children: <Widget>[
                  Expanded(
                      child: Text('Waiting for approval',
                          style: _serif(
                              size: 24,
                              weight: FontWeight.w600,
                              color: _lzFg(plum)))),
                  if (list.isNotEmpty)
                    TextButton(
                        onPressed: _h(() => act(
                            list
                                .map((Map<String, dynamic> p) =>
                                    (p['id'] ?? '').toString())
                                .toList(),
                            false)),
                        child:  Text('Approve all',
                            style: TextStyle(
                                color: _lzFg(plum), fontWeight: FontWeight.w700))),
                ]),
                Text(
                    list.isEmpty
                        ? 'Nothing waiting. Photos guests send show up here first while the hold is on.'
                        : '${list.length} photo${list.length == 1 ? '' : 's'} — tap ✓ to put it on the wall, ✕ to decline.',
                    style:  TextStyle(
                        color: _lzFg(muted), fontSize: 13.5, height: 1.4)),
                const SizedBox(height: 12),
                Flexible(
                  child: list.isEmpty
                      ? const SizedBox(height: 30)
                      : GridView.builder(
                          shrinkWrap: true,
                          gridDelegate:
                              const SliverGridDelegateWithMaxCrossAxisExtent(
                                  maxCrossAxisExtent: 140,
                                  mainAxisSpacing: 8,
                                  crossAxisSpacing: 8),
                          itemCount: list.length,
                          itemBuilder: (BuildContext gc, int i) {
                            final Map<String, dynamic> p = list[i];
                            final String u = (p['url'] ?? '').toString();
                            final String id = (p['id'] ?? '').toString();
                            return ClipRRect(
                              borderRadius: BorderRadius.circular(12),
                              child: Stack(
                                  fit: StackFit.expand,
                                  children: <Widget>[
                                    GestureDetector(
                                      onTap: () => _openLink(u),
                                      child: Image.network(u,
                                          fit: BoxFit.cover,
                                          errorBuilder: (BuildContext c5,
                                                  Object e, StackTrace? st) =>
                                              Container(
                                                  color: gold.withOpacity(.08))),
                                    ),
                                    Positioned(
                                      left: 0,
                                      right: 0,
                                      bottom: 0,
                                      child: Container(
                                        color: plumDeep.withOpacity(.65),
                                        padding: const EdgeInsets.symmetric(
                                            horizontal: 4, vertical: 2),
                                        child: Row(children: <Widget>[
                                          Expanded(
                                            child: Text(
                                                (p['name'] ?? '').toString(),
                                                maxLines: 1,
                                                overflow: TextOverflow.ellipsis,
                                                style: const TextStyle(
                                                    color: ivory,
                                                    fontSize: 10)),
                                          ),
                                          IconButton(
                                              padding: EdgeInsets.zero,
                                              constraints:
                                                  const BoxConstraints(),
                                              onPressed: _h(() =>
                                                  act(<String>[id], true)),
                                              icon: const Icon(
                                                  Icons.close_rounded,
                                                  color: ivory,
                                                  size: 18)),
                                          const SizedBox(width: 6),
                                          IconButton(
                                              padding: EdgeInsets.zero,
                                              constraints:
                                                  const BoxConstraints(),
                                              onPressed: _h(() =>
                                                  act(<String>[id], false)),
                                              icon: const Icon(
                                                  Icons.check_rounded,
                                                  color: gold,
                                                  size: 20)),
                                        ]),
                                      ),
                                    ),
                                  ]),
                            );
                          },
                        ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }""",
        r"""  Future<void> _pendingPhotosSheet(String slug) async {
    Map<String, dynamic> j = await _workerGet(
        'https://meetlazo.com/api/w/$slug/photos?pending=1&t=${DateTime.now().millisecondsSinceEpoch}');
    List<Map<String, dynamic>> list = ((j['photos'] as List?) ?? const <dynamic>[])
        .whereType<Map>()
        .map((Map e) => Map<String, dynamic>.from(e))
        .toList();
    if (!mounted) {
      return;
    }
    bool open = true;
    bool busyAll = false;
    final Set<String> working = <String>{};
    String err = '';
    await _lzSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: _lzBg(ivory),
      constraints: const BoxConstraints(maxWidth: 720),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) {
          void up(VoidCallback f) {
            if (open) setD(f);
          }

          Future<void> act(List<String> ids, bool decline) async {
            up(() {
              working.addAll(ids);
              err = '';
            });
            final Map<String, dynamic> r = await _workerPost(
                'https://meetlazo.com/api/w/$slug/photos/approve',
                <String, dynamic>{'ids': ids, 'decline': decline});
            if (r['ok'] == true) {
              _gpFuture = null;
              up(() {
                working.removeAll(ids);
                list.removeWhere(
                    (Map<String, dynamic> p) => ids.contains(p['id']));
              });
            } else {
              up(() {
                working.removeAll(ids);
                err = 'Couldn’t do that. Check your connection and try again.';
              });
            }
          }

          Widget tileBtn(IconData ic, Color bg, Color fg, String tip, VoidCallback? onTap) =>
              Tooltip(
                message: tip,
                child: _Press(
                  onTap: onTap,
                  child: Container(
                      width: 34,
                      height: 34,
                      decoration: BoxDecoration(color: bg, shape: BoxShape.circle),
                      child: Icon(ic, color: fg, size: 19)),
                ),
              );

          return _lzFrame(ctx2,
              icon: Icons.photo_library_outlined,
              title: 'Waiting for approval',
              subtitle: list.isEmpty
                  ? 'While the hold is on, guest photos land here first.'
                  : '${list.length} photo${list.length == 1 ? '' : 's'} from guests. Tap a photo to see it full size.',
              children: <Widget>[
                const SizedBox(height: 14),
                if (list.isEmpty)
                  _pcA_empty(Icons.check_circle_outline_rounded,
                      'Nothing waiting. You’re all caught up.')
                else
                  GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                        maxCrossAxisExtent: 170,
                        mainAxisSpacing: 10,
                        crossAxisSpacing: 10),
                    itemCount: list.length,
                    itemBuilder: (BuildContext gc, int i) {
                      final Map<String, dynamic> p = list[i];
                      final String u = (p['url'] ?? '').toString();
                      final String id = (p['id'] ?? '').toString();
                      final String who = (p['name'] ?? '').toString();
                      final bool w8 = busyAll || working.contains(id);
                      return ClipRRect(
                        borderRadius: BorderRadius.circular(14),
                        child: Stack(fit: StackFit.expand, children: <Widget>[
                          GestureDetector(
                            onTap: () => _openLink(u),
                            child: Image.network(u,
                                fit: BoxFit.cover,
                                errorBuilder: (BuildContext c5, Object e, StackTrace? st) =>
                                    Container(
                                        color: gold.withOpacity(.08),
                                        child: Icon(Icons.broken_image_outlined,
                                            color: _lzFg(muted)))),
                          ),
                          Positioned(
                            left: 0,
                            right: 0,
                            bottom: 0,
                            child: Container(
                              padding: const EdgeInsets.fromLTRB(8, 18, 6, 6),
                              decoration: BoxDecoration(
                                  gradient: LinearGradient(
                                      begin: Alignment.topCenter,
                                      end: Alignment.bottomCenter,
                                      colors: <Color>[
                                    plumDeep.withOpacity(0),
                                    plumDeep.withOpacity(.8),
                                  ])),
                              child: Row(children: <Widget>[
                                Expanded(
                                  child: Text(who.isEmpty ? 'A guest' : who,
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(
                                          color: ivory,
                                          fontSize: 11.5,
                                          fontWeight: FontWeight.w600)),
                                ),
                                if (w8)
                                  const Padding(
                                    padding: EdgeInsets.all(8),
                                    child: SizedBox(
                                        width: 18,
                                        height: 18,
                                        child: CircularProgressIndicator(
                                            strokeWidth: 2, color: gold)),
                                  )
                                else ...<Widget>[
                                  tileBtn(Icons.close_rounded, Colors.white.withOpacity(.18),
                                      ivory, 'Decline', () => act(<String>[id], true)),
                                  const SizedBox(width: 6),
                                  tileBtn(Icons.check_rounded, gold, plumDeep,
                                      'Put it on the wall', () => act(<String>[id], false)),
                                ],
                              ]),
                            ),
                          ),
                        ]),
                      );
                    },
                  ),
                if (err.isNotEmpty) ...<Widget>[
                  const SizedBox(height: 12),
                  _pcA_status(err, false),
                ],
              ],
              footer: list.isEmpty
                  ? _lzActions(
                      primary: 'Done',
                      icon: Icons.check_rounded,
                      onPrimary: () => Navigator.pop(ctx2))
                  : _lzActions(
                      secondary: 'Close',
                      onSecondary: () => Navigator.pop(ctx2),
                      primary: list.length == 1 ? 'Approve it' : 'Approve all ${list.length}',
                      icon: Icons.done_all_rounded,
                      busy: busyAll,
                      onPrimary: () async {
                        up(() => busyAll = true);
                        await act(
                            list
                                .map((Map<String, dynamic> p) => (p['id'] ?? '').toString())
                                .toList(),
                            false);
                        up(() => busyAll = false);
                      }));
        },
      ),
    );
    open = false;
  }""")

    # _eventEditor
    rep(r"""  Future<Map<String, dynamic>?> _eventEditor(
      BuildContext ctx, Map<String, dynamic>? cur) async {
    final Map<String, dynamic> c = cur ?? <String, dynamic>{};
    final TextEditingController nameC =
        TextEditingController(text: (c['name'] ?? '').toString());
    final TextEditingController dateC =
        TextEditingController(text: (c['dateIso'] ?? '').toString());
    final TextEditingController timeC =
        TextEditingController(text: (c['time'] ?? '').toString());
    final TextEditingController venC =
        TextEditingController(text: (c['venueName'] ?? '').toString());
    final TextEditingController addrC =
        TextEditingController(text: (c['venueAddress'] ?? '').toString());
    final TextEditingController noteC =
        TextEditingController(text: (c['note'] ?? '').toString());
    final TextEditingController dressC =
        TextEditingController(text: (c['dress'] ?? '').toString());
    bool ask = c['rsvp'] == true;
    final String? act = await _lzDialog<String>(
      context: ctx,
      builder: (BuildContext dc) => StatefulBuilder(
        builder: (BuildContext dc2, StateSetter setE) => AlertDialog(
          backgroundColor: _lzBg(ivory),
          title: Text(cur == null ? 'Add an event' : 'Edit event',
              style:  TextStyle(color: _lzFg(plum))),
          content: SizedBox(
            width: 420,
            child: SingleChildScrollView(
              child: Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
                TextField(
                    controller: nameC,
                    textCapitalization: TextCapitalization.words,
                    style:  TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _lightDeco('Event', hint: 'Welcome dinner')),
                const SizedBox(height: 10),
                Row(children: <Widget>[
                  Expanded(
                    child: TextField(
                        controller: dateC,
                        readOnly: true,
                        style:  TextStyle(color: _lzFg(ink), fontSize: 14),
                        decoration: _lightDeco('Date', hint: 'Tap to pick'),
                        onTap: () async {
                          final DateTime? d = await showDatePicker(
                              context: dc2,
                              initialDate: DateTime.tryParse(dateC.text) ??
                                  DateTime.now(),
                              firstDate: DateTime(2020),
                              lastDate: DateTime(2040));
                          if (d != null) {
                            setE(() => dateC.text =
                                '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}');
                          }
                        }),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextField(
                        controller: timeC,
                        style:  TextStyle(color: _lzFg(ink), fontSize: 14),
                        decoration: _lightDeco('Time', hint: '6:30 PM')),
                  ),
                ]),
                const SizedBox(height: 10),
                TextField(
                    controller: venC,
                    style:  TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _lightDeco('Place')),
                const SizedBox(height: 10),
                TextField(
                    controller: addrC,
                    style:  TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _lightDeco('Address')),
                const SizedBox(height: 10),
                TextField(
                    controller: dressC,
                    style:  TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _lightDeco('Dress (optional)')),
                const SizedBox(height: 10),
                TextField(
                    controller: noteC,
                    maxLines: 2,
                    style:  TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _lightDeco('A line for guests (optional)')),
                SwitchListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  activeColor: Colors.white,
                  activeTrackColor: vGreen,
                  inactiveThumbColor: Colors.white,
                  inactiveTrackColor: muted.withOpacity(.4),
                  title: const Text('Ask on the RSVP who’s joining',
                      style: TextStyle(fontSize: 13.5)),
                  value: ask,
                  onChanged: _hb((bool v) => setE(() => ask = v)),
                ),
              ]),
            ),
          ),
          actions: <Widget>[
            if (cur != null)
              TextButton(
                  onPressed: _h(() => Navigator.pop(dc2, 'delete')),
                  child: const Text('Remove',
                      style: TextStyle(color: Color(0xFF8A7D90)))),
            TextButton(
                onPressed: _h(() => Navigator.pop(dc2, null)),
                child:  Text('Cancel', style: TextStyle(color: _lzFg(ink)))),
            FilledButton(
                style: FilledButton.styleFrom(
                    backgroundColor: gold, foregroundColor: plum),
                onPressed: _h(() => Navigator.pop(dc2, 'save')),
                child: const Text('Save')),
          ],
        ),
      ),
    );
    if (act == 'delete') {
      return <String, dynamic>{'_delete': true};
    }
    if (act != 'save' || nameC.text.trim().isEmpty) {
      return null;
    }
    return <String, dynamic>{
      'name': nameC.text.trim(),
      'dateIso': dateC.text.trim(),
      'time': timeC.text.trim(),
      'venueName': venC.text.trim(),
      'venueAddress': addrC.text.trim(),
      'note': noteC.text.trim(),
      'dress': dressC.text.trim(),
      'rsvp': ask,
    };
  }""",
        r"""  Future<Map<String, dynamic>?> _eventEditor(
      BuildContext ctx, Map<String, dynamic>? cur) async {
    final Map<String, dynamic> c = cur ?? <String, dynamic>{};
    final TextEditingController nameC =
        TextEditingController(text: (c['name'] ?? '').toString());
    final TextEditingController dateC =
        TextEditingController(text: (c['dateIso'] ?? '').toString());
    final TextEditingController timeC =
        TextEditingController(text: (c['time'] ?? '').toString());
    final TextEditingController venC =
        TextEditingController(text: (c['venueName'] ?? '').toString());
    final TextEditingController addrC =
        TextEditingController(text: (c['venueAddress'] ?? '').toString());
    final TextEditingController noteC =
        TextEditingController(text: (c['note'] ?? '').toString());
    final TextEditingController dressC =
        TextEditingController(text: (c['dress'] ?? '').toString());
    bool ask = c['rsvp'] == true;
    final String? act = await _lzSheet<String>(
      context: ctx,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext dc) => StatefulBuilder(
        builder: (BuildContext dc2, StateSetter setE) {
          final bool valid = nameC.text.trim().isNotEmpty;
          return _lzFrame(dc2,
              icon: Icons.celebration_outlined,
              title: cur == null ? 'Add an event' : 'Edit event',
              subtitle: 'It shows on your website with the rest of the weekend.',
              children: <Widget>[
                const SizedBox(height: 14),
                TextField(
                    controller: nameC,
                    autofocus: cur == null,
                    textCapitalization: TextCapitalization.words,
                    textInputAction: TextInputAction.next,
                    onChanged: (_) => setE(() {}),
                    style: TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _lightDeco('Event', hint: 'Welcome dinner')),
                const SizedBox(height: 10),
                Row(children: <Widget>[
                  Expanded(
                    child: TextField(
                        controller: dateC,
                        readOnly: true,
                        style: TextStyle(color: _lzFg(ink), fontSize: 14),
                        decoration: _lightDeco('Date', hint: 'Tap to pick'),
                        onTap: () async {
                          final DateTime? d = await showDatePicker(
                              context: dc2,
                              initialDate: DateTime.tryParse(dateC.text) ??
                                  DateTime.now(),
                              firstDate: DateTime(2020),
                              lastDate: DateTime(2040));
                          if (d != null) {
                            setE(() => dateC.text =
                                '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}');
                          }
                        }),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextField(
                        controller: timeC,
                        keyboardType: TextInputType.datetime,
                        textInputAction: TextInputAction.next,
                        style: TextStyle(color: _lzFg(ink), fontSize: 14),
                        decoration: _lightDeco('Time', hint: '6:30 PM')),
                  ),
                ]),
                _lzSection('Where'),
                TextField(
                    controller: venC,
                    textCapitalization: TextCapitalization.words,
                    textInputAction: TextInputAction.next,
                    style: TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _lightDeco('Place')),
                const SizedBox(height: 10),
                TextField(
                    controller: addrC,
                    keyboardType: TextInputType.streetAddress,
                    textInputAction: TextInputAction.next,
                    style: TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _lightDeco('Address')),
                _lzSection('For guests'),
                TextField(
                    controller: dressC,
                    textCapitalization: TextCapitalization.sentences,
                    textInputAction: TextInputAction.next,
                    style: TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _lightDeco('Dress (optional)')),
                const SizedBox(height: 10),
                TextField(
                    controller: noteC,
                    minLines: 1,
                    maxLines: 3,
                    textCapitalization: TextCapitalization.sentences,
                    style: TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _lightDeco('A line for guests (optional)')),
                const SizedBox(height: 6),
                SwitchListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  activeColor: Colors.white,
                  activeTrackColor: vGreen,
                  inactiveThumbColor: Colors.white,
                  inactiveTrackColor: muted.withOpacity(.4),
                  title: Text('Ask on the RSVP who’s joining',
                      style: TextStyle(fontSize: 13.5, color: _lzFg(ink))),
                  value: ask,
                  onChanged: _hb((bool v) => setE(() => ask = v)),
                ),
              ],
              footer: _lzActions(
                  secondary: cur != null ? 'Remove event' : 'Cancel',
                  onSecondary: () async {
                    if (cur == null) {
                      Navigator.pop(dc2, null);
                      return;
                    }
                    final bool sure = await _lzConfirm('Remove this event?',
                        '${nameC.text.trim().isEmpty ? 'It' : nameC.text.trim()} comes off your website.',
                        confirm: 'Remove event', cancel: 'Keep it', danger: true);
                    if (sure && dc2.mounted) {
                      Navigator.pop(dc2, 'delete');
                    }
                  },
                  primary: cur == null ? 'Add event' : 'Save',
                  icon: Icons.check_rounded,
                  onPrimary: valid ? () => Navigator.pop(dc2, 'save') : null));
        },
      ),
    );
    if (act == 'delete') {
      return <String, dynamic>{'_delete': true};
    }
    if (act != 'save' || nameC.text.trim().isEmpty) {
      return null;
    }
    return <String, dynamic>{
      'name': nameC.text.trim(),
      'dateIso': dateC.text.trim(),
      'time': timeC.text.trim(),
      'venueName': venC.text.trim(),
      'venueAddress': addrC.text.trim(),
      'note': noteC.text.trim(),
      'dress': dressC.text.trim(),
      'rsvp': ask,
    };
  }""")

    # _guestPhotosSheet
    rep(r"""  Future<void> _guestPhotosSheet(String slug) async {
    List<Map<String, dynamic>> list = await _guestPhotos(slug, fresh: true);
    if (!mounted) {
      return;
    }
    await _lzSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: _lzBg(ivory),
      constraints: const BoxConstraints(maxWidth: 720),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) {
          Future<void> remove(Map<String, dynamic> p) async {
            final bool? sure = await _lzDialog<bool>(
              context: ctx2,
              builder: (BuildContext dc) => AlertDialog(
                backgroundColor: _lzBg(ivory),
                title:  Text('Remove this photo?',
                    style: TextStyle(color: _lzFg(plum))),
                content:  Text(
                    'It comes off the wall for everyone and the file is deleted. This can’t be undone.',
                    style: TextStyle(color: _lzFg(ink), fontSize: 14)),
                actions: <Widget>[
                  TextButton(
                      onPressed: () => Navigator.pop(dc, false),
                      child:  Text('Keep', style: TextStyle(color: _lzFg(ink)))),
                  FilledButton(
                      style: FilledButton.styleFrom(
                          backgroundColor: rose, foregroundColor: ivory),
                      onPressed: () => Navigator.pop(dc, true),
                      child: const Text('Remove')),
                ],
              ),
            );
            if (sure != true) {
              return;
            }
            try {
              await FirebaseFirestore.instance
                  .collection('weddingSites')
                  .doc(slug)
                  .update(<String, dynamic>{
                'guestPhotosRemoved': FieldValue.arrayUnion(<dynamic>[p['id']]),
              });
              setD(() => list.removeWhere(
                  (Map<String, dynamic> x) => x['id'] == p['id']));
              _gpFuture = Future<List<Map<String, dynamic>>>.value(
                  List<Map<String, dynamic>>.from(list));
              // the worker deletes the file on its next listing
              Future<void>.delayed(const Duration(seconds: 2), () {
                _guestPhotosFetch(slug);
              });
              _toastC('Removed — it’s off the wall within a minute.');
            } catch (_) {
              _toastC('Could not remove — try again.');
            }
          }

          return Padding(
            padding: EdgeInsets.fromLTRB(
                20, 14, 20, 20 + MediaQuery.of(ctx2).viewInsets.bottom),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Center(
                  child: Container(
                      width: 40,
                      height: 4,
                      decoration: BoxDecoration(
                          color: plum.withOpacity(.25),
                          borderRadius: BorderRadius.circular(4))),
                ),
                const SizedBox(height: 14),
                Row(children: <Widget>[
                  Expanded(
                    child: Text('Photos from your guests',
                        style: _serif(
                            size: 24, weight: FontWeight.w600, color: _lzFg(plum))),
                  ),
                  TextButton.icon(
                    onPressed: _h(() => _pendingPhotosSheet(slug)),
                    icon:  Icon(Icons.pending_actions_rounded,
                        color: _lzFg(plum), size: 18),
                    label:  Text('Waiting',
                        style: TextStyle(
                            color: _lzFg(plum), fontWeight: FontWeight.w700)),
                  ),
                  IconButton(
                    tooltip: 'Refresh',
                    onPressed: _h(() async {
                      final List<Map<String, dynamic>> l =
                          await _guestPhotos(slug, fresh: true);
                      setD(() => list = l);
                    }),
                    icon:  Icon(Icons.refresh_rounded, color: _lzFg(plum)),
                  ),
                ]),
                Text(
                    list.isEmpty
                        ? 'Nothing shared yet. From the wedding day, guests add photos from their phones on your site.'
                        : '${list.length} photo${list.length == 1 ? '' : 's'} · tap to open, hold to remove.',
                    style:  TextStyle(
                        color: _lzFg(muted), fontSize: 13.5, height: 1.4)),
                const SizedBox(height: 12),
                Flexible(
                  child: list.isEmpty
                      ? const SizedBox(height: 40)
                      : GridView.builder(
                          shrinkWrap: true,
                          gridDelegate:
                              const SliverGridDelegateWithMaxCrossAxisExtent(
                                  maxCrossAxisExtent: 120,
                                  mainAxisSpacing: 8,
                                  crossAxisSpacing: 8),
                          itemCount: list.length,
                          itemBuilder: (BuildContext gc, int i) {
                            final Map<String, dynamic> p = list[i];
                            final String u = (p['url'] ?? '').toString();
                            return GestureDetector(
                              onTap: () => _openLink(u),
                              onLongPress: () => remove(p),
                              child: ClipRRect(
                                borderRadius: BorderRadius.circular(12),
                                child: Stack(
                                    fit: StackFit.expand,
                                    children: <Widget>[
                                      Image.network(
                                        'https://wsrv.nl/?url=${Uri.encodeComponent(u)}&w=300&q=70',
                                        fit: BoxFit.cover,
                                        errorBuilder: (BuildContext c5,
                                                Object e, StackTrace? st) =>
                                            Container(
                                                color: gold.withOpacity(.08),
                                                child:  Icon(
                                                    Icons
                                                        .broken_image_outlined,
                                                    color: _lzFg(muted))),
                                      ),
                                      if ((p['name'] ?? '')
                                          .toString()
                                          .isNotEmpty)
                                        Positioned(
                                          left: 0,
                                          right: 0,
                                          bottom: 0,
                                          child: Container(
                                            padding:
                                                const EdgeInsets.symmetric(
                                                    horizontal: 6,
                                                    vertical: 3),
                                            color: plumDeep.withOpacity(.6),
                                            child: Text(
                                                (p['name'] ?? '').toString(),
                                                maxLines: 1,
                                                overflow:
                                                    TextOverflow.ellipsis,
                                                style: const TextStyle(
                                                    color: ivory,
                                                    fontSize: 10,
                                                    fontWeight:
                                                        FontWeight.w700)),
                                          ),
                                        ),
                                      Positioned(
                                        top: 4,
                                        right: 4,
                                        child: _Press(
                                          tick: _Tick.select,
                                          onTap: () => remove(p),
                                          child: Container(
                                            width: 22,
                                            height: 22,
                                            decoration: const BoxDecoration(
                                                color: plumDeep,
                                                shape: BoxShape.circle),
                                            child: const Icon(
                                                Icons.close_rounded,
                                                color: ivory,
                                                size: 14),
                                          ),
                                        ),
                                      ),
                                    ]),
                              ),
                            );
                          },
                        ),
                ),
                const SizedBox(height: 12),
                Row(children: <Widget>[
                  TextButton.icon(
                    onPressed: _h(list.isEmpty
                        ? null
                        : () async {
                            await Clipboard.setData(ClipboardData(
                                text: list
                                    .map((Map<String, dynamic> p) =>
                                        (p['url'] ?? '').toString())
                                    .join('\n')));
                            _toastC(
                                'All ${list.length} links copied — paste them anywhere ✓');
                          }),
                    icon:  Icon(Icons.link_rounded, color: _lzFg(plum), size: 18),
                    label:  Text('Copy all links',
                        style: TextStyle(color: _lzFg(plum))),
                  ),
                  TextButton.icon(
                    onPressed: _h(list.isEmpty
                        ? null
                        : () => _openLink(
                            'https://meetlazo.com/w/$slug/photos/download')),
                    icon:  Icon(Icons.download_rounded,
                        color: _lzFg(plum), size: 18),
                    label:  Text('Zip', style: TextStyle(color: _lzFg(plum))),
                  ),
                  const Spacer(),
                  FilledButton(
                    style: FilledButton.styleFrom(
                        backgroundColor: gold, foregroundColor: plumDeep),
                    onPressed: _h(() => _openLink(
                        'https://meetlazo.com/w/$slug/?photos=1#photos')),
                    child: const Text('See the wall',
                        style: TextStyle(fontWeight: FontWeight.w700)),
                  ),
                ]),
              ],
            ),
          );
        },
      ),
    );
  }""",
        r"""  Future<void> _guestPhotosSheet(String slug) async {
    List<Map<String, dynamic>> list = await _guestPhotos(slug, fresh: true);
    if (!mounted) {
      return;
    }
    bool open = true;
    bool refreshing = false;
    String note = '';
    bool noteOk = true;
    await _lzSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: _lzBg(ivory),
      constraints: const BoxConstraints(maxWidth: 720),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) {
          void up(VoidCallback f) {
            if (open) setD(f);
          }

          Future<void> remove(Map<String, dynamic> p) async {
            final bool sure = await _lzConfirm('Remove this photo?',
                'It comes off the wall for everyone and the file is deleted. This can’t be undone.',
                confirm: 'Remove photo', cancel: 'Keep it', danger: true);
            if (!sure) {
              return;
            }
            try {
              await FirebaseFirestore.instance
                  .collection('weddingSites')
                  .doc(slug)
                  .update(<String, dynamic>{
                'guestPhotosRemoved': FieldValue.arrayUnion(<dynamic>[p['id']]),
              });
              up(() {
                list.removeWhere((Map<String, dynamic> x) => x['id'] == p['id']);
                note = 'Removed. It’s off the wall within a minute.';
                noteOk = true;
              });
              _gpFuture = Future<List<Map<String, dynamic>>>.value(
                  List<Map<String, dynamic>>.from(list));
              // the worker deletes the file on its next listing
              Future<void>.delayed(const Duration(seconds: 2), () {
                _guestPhotosFetch(slug);
              });
            } catch (_) {
              up(() {
                note = 'Couldn’t remove that photo. Check your connection and try again.';
                noteOk = false;
              });
            }
          }

          Widget tool(IconData ic, String label, VoidCallback? onTap, {bool spin = false}) =>
              _Press(
                scale: .97,
                onTap: onTap,
                child: Opacity(
                  opacity: onTap == null ? .45 : 1,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    decoration: BoxDecoration(
                        color: _lzBg(cardBg),
                        borderRadius: BorderRadius.circular(30),
                        border: Border.all(color: _lzLine(goldLine))),
                    child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
                      if (spin)
                        const SizedBox(
                            width: 15,
                            height: 15,
                            child: CircularProgressIndicator(strokeWidth: 2, color: gold))
                      else
                        Icon(ic, size: 16, color: _lzFg(plum)),
                      const SizedBox(width: 6),
                      Text(label,
                          style: TextStyle(
                              fontSize: 13, fontWeight: FontWeight.w700, color: _lzFg(plum))),
                    ]),
                  ),
                ),
              );

          return _lzFrame(ctx2,
              icon: Icons.photo_camera_back_outlined,
              title: 'Photos from your guests',
              subtitle: list.isEmpty
                  ? 'From the wedding day, guests add photos from their phones on your site.'
                  : '${list.length} photo${list.length == 1 ? '' : 's'}. Tap one to open it, hold to remove it.',
              headerExtra: Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                tool(Icons.pending_actions_rounded, 'Waiting for approval',
                    () => _pendingPhotosSheet(slug)),
                tool(Icons.refresh_rounded, 'Refresh', refreshing
                    ? null
                    : () async {
                        up(() => refreshing = true);
                        final List<Map<String, dynamic>> l =
                            await _guestPhotos(slug, fresh: true);
                        up(() {
                          list = l;
                          refreshing = false;
                        });
                      }, spin: refreshing),
                tool(Icons.link_rounded, 'Copy all links', list.isEmpty
                    ? null
                    : () async {
                        await Clipboard.setData(ClipboardData(
                            text: list
                                .map((Map<String, dynamic> p) => (p['url'] ?? '').toString())
                                .join('\n')));
                        up(() {
                          note = 'All ${list.length} links copied. Paste them anywhere.';
                          noteOk = true;
                        });
                      }),
                tool(Icons.download_rounded, 'Download all (zip)', list.isEmpty
                    ? null
                    : () => _openLink('https://meetlazo.com/w/$slug/photos/download')),
              ]),
              children: <Widget>[
                const SizedBox(height: 14),
                if (note.isNotEmpty) ...<Widget>[
                  _pcA_status(note, noteOk),
                  const SizedBox(height: 12),
                ],
                if (list.isEmpty)
                  _pcA_empty(Icons.photo_library_outlined,
                      'Nothing shared yet. Guests’ photos show up here as they add them.')
                else
                  GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                        maxCrossAxisExtent: 130, mainAxisSpacing: 8, crossAxisSpacing: 8),
                    itemCount: list.length,
                    itemBuilder: (BuildContext gc, int i) {
                      final Map<String, dynamic> p = list[i];
                      final String u = (p['url'] ?? '').toString();
                      return GestureDetector(
                        onTap: () => _openLink(u),
                        onLongPress: () => remove(p),
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(12),
                          child: Stack(fit: StackFit.expand, children: <Widget>[
                            Image.network(
                              'https://wsrv.nl/?url=${Uri.encodeComponent(u)}&w=300&q=70',
                              fit: BoxFit.cover,
                              errorBuilder: (BuildContext c5, Object e, StackTrace? st) =>
                                  Container(
                                      color: gold.withOpacity(.08),
                                      child: Icon(Icons.broken_image_outlined,
                                          color: _lzFg(muted))),
                            ),
                            if ((p['name'] ?? '').toString().isNotEmpty)
                              Positioned(
                                left: 0,
                                right: 0,
                                bottom: 0,
                                child: Container(
                                  padding: const EdgeInsets.fromLTRB(6, 12, 6, 4),
                                  decoration: BoxDecoration(
                                      gradient: LinearGradient(
                                          begin: Alignment.topCenter,
                                          end: Alignment.bottomCenter,
                                          colors: <Color>[
                                        plumDeep.withOpacity(0),
                                        plumDeep.withOpacity(.75),
                                      ])),
                                  child: Text((p['name'] ?? '').toString(),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(
                                          color: ivory,
                                          fontSize: 10.5,
                                          fontWeight: FontWeight.w700)),
                                ),
                              ),
                            Positioned(
                              top: 4,
                              right: 4,
                              child: Tooltip(
                                message: 'Remove',
                                child: _Press(
                                  tick: _Tick.select,
                                  onTap: () => remove(p),
                                  child: Container(
                                    width: 24,
                                    height: 24,
                                    decoration: BoxDecoration(
                                        color: plumDeep.withOpacity(.85),
                                        shape: BoxShape.circle),
                                    child: const Icon(Icons.close_rounded,
                                        color: ivory, size: 14),
                                  ),
                                ),
                              ),
                            ),
                          ]),
                        ),
                      );
                    },
                  ),
              ],
              footer: _lzActions(
                  secondary: 'Close',
                  onSecondary: () => Navigator.pop(ctx2),
                  primary: 'See the wall',
                  icon: Icons.open_in_new_rounded,
                  onPrimary: () =>
                      _openLink('https://meetlazo.com/w/$slug/?photos=1#photos')));
        },
      ),
    );
    open = false;
  }""")

    # _plusEditor
    rep(r"""  Future<Map<String, dynamic>?> _plusEditor(BuildContext ctx, String title,
      List<List<String>> fields, Map<String, dynamic>? cur,
      {String slot = 'item', List<String> sides = const <String>[]}) async {
    final Map<String, dynamic> c = cur ?? <String, dynamic>{};
    final Map<String, TextEditingController> tc =
        <String, TextEditingController>{
      for (final List<String> f in fields)
        if (<String>['text', 'multi', 'url', 'num'].contains(f[3]))
          f[0]: TextEditingController(
              text: c[f[0]] == null ? '' : c[f[0]].toString())
    };
    String photoUrl = (c['photo'] ?? '').toString();
    String side = (c['side'] ?? '').toString();
    final Map<String, bool> flags = <String, bool>{
      for (final List<String> f in fields)
        if (f[3] == 'bool') f[0]: cur == null ? true : c[f[0]] != false
    };
    bool busy = false;
    final String? act = await _lzDialog<String>(
      context: ctx,
      builder: (BuildContext dc) => StatefulBuilder(
        builder: (BuildContext dc2, StateSetter setE) => AlertDialog(
          backgroundColor: _lzBg(ivory),
          title: Text(title, style: TextStyle(color: _lzFg(plum))),
          content: SizedBox(
            width: 420,
            child: SingleChildScrollView(
              child: Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
                for (final List<String> f in fields) ...<Widget>[
                  if (tc.containsKey(f[0]))
                    TextField(
                        controller: tc[f[0]],
                        maxLines: f[3] == 'multi' ? 3 : 1,
                        keyboardType: f[3] == 'num'
                            ? TextInputType.number
                            : f[3] == 'url'
                                ? TextInputType.url
                                : TextInputType.text,
                        textCapitalization: f[3] == 'url' || f[3] == 'num'
                            ? TextCapitalization.none
                            : TextCapitalization.sentences,
                        style: TextStyle(color: _lzFg(ink), fontSize: 14),
                        decoration: _lightDeco(f[1],
                            hint: f[2].isEmpty ? null : f[2])),
                  if (f[3] == 'side')
                    Align(
                      alignment: Alignment.centerLeft,
                      child: Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
                        for (final List<String> o in <List<String>>[
                          <String>['a', sides.isNotEmpty ? sides[0] : 'First side'],
                          <String>['b', sides.length > 1 ? sides[1] : 'Second side'],
                          <String>['', 'Both / neither'],
                        ])
                          ChoiceChip(
                            label: Text(o[1]),
                            selected: side == o[0],
                            selectedColor: gold.withOpacity(.45),
                            backgroundColor: _lzBg(Colors.white),
                            labelStyle:
                                TextStyle(color: _lzFg(plum), fontSize: 12.5),
                            onSelected: (bool v) => setE(() => side = o[0]),
                          ),
                      ]),
                    ),
                  if (f[3] == 'photo')
                    Row(children: <Widget>[
                      if (photoUrl.isNotEmpty)
                        Padding(
                          padding: const EdgeInsets.only(right: 10),
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(10),
                            child: Image.network(photoUrl,
                                width: 56, height: 56, fit: BoxFit.cover),
                          ),
                        ),
                      TextButton.icon(
                        onPressed: busy
                            ? null
                            : () async {
                                setE(() => busy = true);
                                final String? u = await _uploadSlotPhoto(slot);
                                setE(() {
                                  busy = false;
                                  if (u != null) {
                                    photoUrl = u;
                                  }
                                });
                              },
                        icon: busy
                            ? const SizedBox(
                                width: 14,
                                height: 14,
                                child: CircularProgressIndicator(strokeWidth: 2))
                            : Icon(Icons.add_a_photo_outlined,
                                size: 16, color: _lzFg(plum)),
                        label: Text(
                            photoUrl.isEmpty ? 'Add a photo' : 'Change photo',
                            style: TextStyle(color: _lzFg(plum))),
                      ),
                      if (photoUrl.isNotEmpty)
                        TextButton(
                            onPressed: () => setE(() => photoUrl = ''),
                            child: const Text('Remove',
                                style: TextStyle(color: Color(0xFF8A7D90)))),
                    ]),
                  if (f[3] == 'bool')
                    SwitchListTile(
                      dense: true,
                      contentPadding: EdgeInsets.zero,
                      activeColor: Colors.white,
                      activeTrackColor: vGreen,
                      inactiveThumbColor: Colors.white,
                      inactiveTrackColor: muted.withOpacity(.4),
                      title: Text(f[1], style: const TextStyle(fontSize: 13.5)),
                      value: flags[f[0]] ?? true,
                      onChanged: (bool v) => setE(() => flags[f[0]] = v),
                    ),
                  const SizedBox(height: 10),
                ],
              ]),
            ),
          ),
          actions: <Widget>[
            if (cur != null)
              TextButton(
                  onPressed: _h(() => Navigator.pop(dc2, 'delete')),
                  child: const Text('Remove',
                      style: TextStyle(color: Color(0xFF8A7D90)))),
            TextButton(
                onPressed: _h(() => Navigator.pop(dc2, null)),
                child: Text('Cancel', style: TextStyle(color: _lzFg(ink)))),
            FilledButton(
                style: FilledButton.styleFrom(
                    backgroundColor: gold, foregroundColor: plum),
                onPressed: busy ? null : _h(() => Navigator.pop(dc2, 'save')),
                child: const Text('Save')),
          ],
        ),
      ),
    );
    if (act == 'delete') {
      return <String, dynamic>{'_delete': true};
    }
    final String first = tc[fields.first[0]]?.text.trim() ?? '';
    if (act != 'save' || first.isEmpty) {
      return null;
    }
    final Map<String, dynamic> out = <String, dynamic>{};
    for (final List<String> f in fields) {
      switch (f[3]) {
        case 'photo':
          out[f[0]] = photoUrl;
          break;
        case 'side':
          out[f[0]] = side;
          break;
        case 'bool':
          out[f[0]] = flags[f[0]] ?? true;
          break;
        case 'num':
          final String t = tc[f[0]]!.text.trim();
          out[f[0]] = t.isEmpty ? null : num.tryParse(t.replaceAll(',', ''));
          break;
        case 'url':
          String u = tc[f[0]]!.text.trim();
          if (u.isNotEmpty && !u.startsWith('http')) {
            u = 'https://$u';
          }
          out[f[0]] = u.startsWith('https://') ? u : '';
          break;
        default:
          out[f[0]] = tc[f[0]]!.text.trim();
      }
    }
    return out;
  }""",
        r"""  Future<Map<String, dynamic>?> _plusEditor(BuildContext ctx, String title,
      List<List<String>> fields, Map<String, dynamic>? cur,
      {String slot = 'item', List<String> sides = const <String>[]}) async {
    final Map<String, dynamic> c = cur ?? <String, dynamic>{};
    final Map<String, TextEditingController> tc =
        <String, TextEditingController>{
      for (final List<String> f in fields)
        if (<String>['text', 'multi', 'url', 'num'].contains(f[3]))
          f[0]: TextEditingController(
              text: c[f[0]] == null ? '' : c[f[0]].toString())
    };
    String photoUrl = (c['photo'] ?? '').toString();
    String side = (c['side'] ?? '').toString();
    final Map<String, bool> flags = <String, bool>{
      for (final List<String> f in fields)
        if (f[3] == 'bool') f[0]: cur == null ? true : c[f[0]] != false
    };
    bool busy = false;
    final String firstKey = fields.isEmpty ? '' : fields.first[0];
    final String? act = await _lzSheet<String>(
      context: ctx,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext dc) => StatefulBuilder(
        builder: (BuildContext dc2, StateSetter setE) {
          final bool valid = (tc[firstKey]?.text.trim() ?? '').isNotEmpty;
          return _lzFrame(dc2,
              icon: cur == null ? Icons.add_rounded : Icons.edit_outlined,
              title: title,
              subtitle: cur == null
                  ? 'It shows on your website once you save.'
                  : 'Changes show on your website once you save.',
              children: <Widget>[
                const SizedBox(height: 14),
                for (final List<String> f in fields) ...<Widget>[
                  if (tc.containsKey(f[0]))
                    TextField(
                        controller: tc[f[0]],
                        autofocus: cur == null && f[0] == firstKey,
                        minLines: 1,
                        maxLines: f[3] == 'multi' ? 4 : 1,
                        onChanged: f[0] == firstKey ? (_) => setE(() {}) : null,
                        keyboardType: f[3] == 'num'
                            ? const TextInputType.numberWithOptions(decimal: true)
                            : f[3] == 'url'
                                ? TextInputType.url
                                : f[3] == 'multi'
                                    ? TextInputType.multiline
                                    : TextInputType.text,
                        textCapitalization: f[3] == 'url' || f[3] == 'num'
                            ? TextCapitalization.none
                            : TextCapitalization.sentences,
                        style: TextStyle(color: _lzFg(ink), fontSize: 14),
                        decoration: _lightDeco(f[1],
                            hint: f[2].isEmpty ? null : f[2])),
                  if (f[3] == 'side') ...<Widget>[
                    Text(f[1].isEmpty ? 'Whose side' : f[1],
                        style: TextStyle(
                            fontSize: 12.5, fontWeight: FontWeight.w700, color: _lzFg(muted))),
                    const SizedBox(height: 8),
                    Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                      for (final List<String> o in <List<String>>[
                        <String>['a', sides.isNotEmpty ? sides[0] : 'First side'],
                        <String>['b', sides.length > 1 ? sides[1] : 'Second side'],
                        <String>['', 'Both / neither'],
                      ])
                        _Press(
                          scale: .97,
                          onTap: () => setE(() => side = o[0]),
                          child: AnimatedContainer(
                            duration: const Duration(milliseconds: 180),
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
                            decoration: BoxDecoration(
                                color: side == o[0] ? plumDeep : _lzBg(cardBg),
                                borderRadius: BorderRadius.circular(30),
                                border: Border.all(
                                    color: side == o[0] ? plumDeep : _lzLine(goldLine))),
                            child: Text(o[1],
                                style: TextStyle(
                                    fontSize: 13,
                                    fontWeight: FontWeight.w700,
                                    color: side == o[0] ? gold : _lzFg(plum))),
                          ),
                        ),
                    ]),
                  ],
                  if (f[3] == 'photo')
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                          color: _lzBg(cardBg),
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: _lzLine(goldLine))),
                      child: Row(children: <Widget>[
                        ClipRRect(
                          borderRadius: BorderRadius.circular(10),
                          child: SizedBox(
                            width: 56,
                            height: 56,
                            child: photoUrl.isNotEmpty
                                ? Image.network(photoUrl, fit: BoxFit.cover)
                                : ColoredBox(
                                    color: _lzBg(const Color(0xFFF6EEDF)),
                                    child: Icon(Icons.image_outlined, color: _lzFg(muted))),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: busy
                              ? Text('Uploading…',
                                  style: TextStyle(fontSize: 13.5, color: _lzFg(muted)))
                              : TextButton.icon(
                                  style: TextButton.styleFrom(
                                      alignment: Alignment.centerLeft,
                                      foregroundColor: _lzFg(plum)),
                                  onPressed: _h(() async {
                                    setE(() => busy = true);
                                    final String? u = await _uploadSlotPhoto(slot);
                                    setE(() {
                                      busy = false;
                                      if (u != null) {
                                        photoUrl = u;
                                      }
                                    });
                                  }),
                                  icon: const Icon(Icons.add_a_photo_outlined, size: 17),
                                  label: Text(
                                      photoUrl.isEmpty ? 'Add a photo' : 'Change photo',
                                      style: const TextStyle(fontWeight: FontWeight.w700)),
                                ),
                        ),
                        if (busy)
                          const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(strokeWidth: 2, color: gold))
                        else if (photoUrl.isNotEmpty)
                          IconButton(
                              tooltip: 'Take the photo off',
                              onPressed: _h(() => setE(() => photoUrl = '')),
                              icon: Icon(Icons.close_rounded, color: _lzFg(muted), size: 19)),
                      ]),
                    ),
                  if (f[3] == 'bool')
                    SwitchListTile(
                      dense: true,
                      contentPadding: EdgeInsets.zero,
                      activeColor: Colors.white,
                      activeTrackColor: vGreen,
                      inactiveThumbColor: Colors.white,
                      inactiveTrackColor: muted.withOpacity(.4),
                      title: Text(f[1],
                          style: TextStyle(fontSize: 13.5, color: _lzFg(ink))),
                      value: flags[f[0]] ?? true,
                      onChanged: (bool v) => setE(() => flags[f[0]] = v),
                    ),
                  const SizedBox(height: 10),
                ],
              ],
              footer: _lzActions(
                  secondary: cur != null ? 'Remove' : 'Cancel',
                  onSecondary: () async {
                    if (cur == null) {
                      Navigator.pop(dc2, null);
                      return;
                    }
                    final bool sure = await _lzConfirm('Remove this?',
                        'It comes off your website.',
                        confirm: 'Remove it', cancel: 'Keep it', danger: true);
                    if (sure && dc2.mounted) {
                      Navigator.pop(dc2, 'delete');
                    }
                  },
                  primary: 'Save',
                  icon: Icons.check_rounded,
                  onPrimary: busy || !valid ? null : () => Navigator.pop(dc2, 'save')));
        },
      ),
    );
    if (act == 'delete') {
      return <String, dynamic>{'_delete': true};
    }
    final String first = tc[fields.first[0]]?.text.trim() ?? '';
    if (act != 'save' || first.isEmpty) {
      return null;
    }
    final Map<String, dynamic> out = <String, dynamic>{};
    for (final List<String> f in fields) {
      switch (f[3]) {
        case 'photo':
          out[f[0]] = photoUrl;
          break;
        case 'side':
          out[f[0]] = side;
          break;
        case 'bool':
          out[f[0]] = flags[f[0]] ?? true;
          break;
        case 'num':
          final String t = tc[f[0]]!.text.trim();
          out[f[0]] = t.isEmpty ? null : num.tryParse(t.replaceAll(',', ''));
          break;
        case 'url':
          String u = tc[f[0]]!.text.trim();
          if (u.isNotEmpty && !u.startsWith('http')) {
            u = 'https://$u';
          }
          out[f[0]] = u.startsWith('https://') ? u : '';
          break;
        default:
          out[f[0]] = tc[f[0]]!.text.trim();
      }
    }
    return out;
  }""")

    # _juneSiteDraft
    rep(r"""  Future<Map<String, dynamic>?> _juneSiteDraft(BuildContext ctx) async {
    final List<List<String>> qs = <List<String>>[
      <String>['met', 'How did you meet?', 'Where, when, who said what first'],
      <String>['proposal', 'The proposal', 'Where and how it happened'],
      <String>['moments', 'Dates that matter (optional)', 'First trip, moving in, the dog'],
      <String>['vibe', 'The feel you want', 'Garden, candlelit, relaxed but dressy'],
      <String>['notes', 'Anything guests should know (optional)', 'Outdoor ceremony, kids welcome, parking'],
    ];
    final Map<String, TextEditingController> c = <String, TextEditingController>{
      for (final List<String> q in qs) q[0]: TextEditingController()
    };
    final bool? go = await _lzDialog<bool>(
      context: ctx,
      builder: (BuildContext dc) => AlertDialog(
        backgroundColor: _lzBg(ivory),
        title: Text('Build it with June', style: TextStyle(color: _lzFg(plum))),
        content: SizedBox(
          width: 440,
          child: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
              Text(
                  'A few lines each is plenty. June only writes what you tell her and fills the fields you have left empty.',
                  style: TextStyle(fontSize: 12, color: _lzFg(muted))),
              const SizedBox(height: 12),
              for (final List<String> q in qs) ...<Widget>[
                TextField(
                    controller: c[q[0]],
                    maxLines: q[0] == 'vibe' ? 1 : 3,
                    minLines: 1,
                    textCapitalization: TextCapitalization.sentences,
                    style: TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _lightDeco(q[1], hint: q[2])),
                const SizedBox(height: 10),
              ],
            ]),
          ),
        ),
        actions: <Widget>[
          TextButton(
              onPressed: _h(() => Navigator.pop(dc, false)),
              child: Text('Cancel', style: TextStyle(color: _lzFg(ink)))),
          FilledButton(
              style: FilledButton.styleFrom(
                  backgroundColor: gold, foregroundColor: plum),
              onPressed: _h(() => Navigator.pop(dc, true)),
              child: const Text('Write it')),
        ],
      ),
    );
    if (go != true) {
      return null;
    }
    if (c['met']!.text.trim().isEmpty && c['proposal']!.text.trim().isEmpty) {
      _toastC('Tell June a little about how you met first.');
      return null;
    }
    bool open = true;
    // ignore: unawaited_futures
    _lzDialog<void>(
      context: ctx,
      barrierDismissible: false,
      builder: (BuildContext dc) => AlertDialog(
        backgroundColor: _lzBg(ivory),
        content: Row(children: <Widget>[
          const SizedBox(
              width: 22,
              height: 22,
              child: CircularProgressIndicator(strokeWidth: 2.4)),
          const SizedBox(width: 16),
          Expanded(
              child: Text(
                  'June is writing your site… this takes about twenty seconds.',
                  style: TextStyle(color: _lzFg(ink), fontSize: 13.5))),
        ]),
      ),
    ).then((_) => open = false);
    void closeWait() {
      if (open) {
        open = false;
        Navigator.of(ctx, rootNavigator: true).pop();
      }
    }
    try {
      final String? t = await FirebaseAuth.instance.currentUser?.getIdToken();
      if (t == null) {
        closeWait();
        _toastC('Sign in again, then ask June.');
        return null;
      }
      final httpc.Response r = await httpc
          .post(Uri.parse('https://june.meetlazo.com/api/site/draft'),
              headers: <String, String>{
                'authorization': 'Bearer $t',
                'content-type': 'application/json',
              },
              body: jsonEncode(<String, dynamic>{
                'answers': <String, String>{
                  for (final MapEntry<String, TextEditingController> e
                      in c.entries)
                    e.key: e.value.text.trim()
                }
              }))
          .timeout(const Duration(seconds: 120));
      closeWait();
      final dynamic j = jsonDecode(r.body);
      if (r.statusCode != 200 || j is! Map || j['draft'] is! Map) {
        _toastC(j is Map && j['error'] != null
            ? 'June couldn’t finish: ${j['error'].toString().length > 80 ? j['error'].toString().substring(0, 80) : j['error']}'
            : 'June couldn’t finish the draft — try again in a moment.');
        return null;
      }
      return Map<String, dynamic>.from(j);
    } catch (_) {
      closeWait();
      _toastC('June couldn’t finish the draft — try again in a moment.');
      return null;
    }
  }""",
        r"""  Future<Map<String, dynamic>?> _juneSiteDraft(BuildContext ctx) async {
    final List<List<String>> qs = <List<String>>[
      <String>['met', 'How did you meet?', 'Where, when, who said what first'],
      <String>['proposal', 'The proposal', 'Where and how it happened'],
      <String>['moments', 'Dates that matter (optional)', 'First trip, moving in, the dog'],
      <String>['vibe', 'The feel you want', 'Garden, candlelit, relaxed but dressy'],
      <String>['notes', 'Anything guests should know (optional)', 'Outdoor ceremony, kids welcome, parking'],
    ];
    final Map<String, TextEditingController> c = <String, TextEditingController>{
      for (final List<String> q in qs) q[0]: TextEditingController()
    };
    bool open = true;
    bool busy = false;
    String err = '';
    final Map<String, dynamic>? out = await _lzSheet<Map<String, dynamic>>(
      context: ctx,
      constraints: const BoxConstraints(maxWidth: 580),
      isDismissible: true,
      builder: (BuildContext dc) => StatefulBuilder(
        builder: (BuildContext dc2, StateSetter setE) {
          void up(VoidCallback f) {
            if (open) setE(f);
          }

          final bool enough = c['met']!.text.trim().isNotEmpty ||
              c['proposal']!.text.trim().isNotEmpty;

          Future<void> write() async {
            up(() {
              busy = true;
              err = '';
            });
            try {
              final String? t = await FirebaseAuth.instance.currentUser?.getIdToken();
              if (t == null) {
                up(() {
                  busy = false;
                  err = 'Sign in again, then ask June.';
                });
                return;
              }
              final httpc.Response r = await httpc
                  .post(Uri.parse('https://june.meetlazo.com/api/site/draft'),
                      headers: <String, String>{
                        'authorization': 'Bearer $t',
                        'content-type': 'application/json',
                      },
                      body: jsonEncode(<String, dynamic>{
                        'answers': <String, String>{
                          for (final MapEntry<String, TextEditingController> e
                              in c.entries)
                            e.key: e.value.text.trim()
                        }
                      }))
                  .timeout(const Duration(seconds: 120));
              final dynamic j = jsonDecode(r.body);
              if (r.statusCode != 200 || j is! Map || j['draft'] is! Map) {
                up(() {
                  busy = false;
                  err = j is Map && j['error'] != null
                      ? 'June couldn’t finish: ${j['error'].toString().length > 80 ? j['error'].toString().substring(0, 80) : j['error']}'
                      : 'June couldn’t finish. Try again in a moment.';
                });
                return;
              }
              if (open && dc2.mounted) {
                Navigator.pop(dc2, Map<String, dynamic>.from(j));
              }
            } catch (_) {
              up(() {
                busy = false;
                err = 'June couldn’t finish. Try again in a moment.';
              });
            }
          }

          return _lzFrame(dc2,
              icon: Icons.auto_awesome_rounded,
              title: 'Build it with June',
              subtitle: 'A few lines each is plenty. June only writes what you tell her.',
              children: <Widget>[
                const SizedBox(height: 14),
                for (int i = 0; i < qs.length; i++) ...<Widget>[
                  TextField(
                      controller: c[qs[i][0]],
                      autofocus: i == 0,
                      enabled: !busy,
                      maxLines: qs[i][0] == 'vibe' ? 1 : 3,
                      minLines: 1,
                      onChanged: i < 2 ? (_) => up(() {}) : null,
                      textCapitalization: TextCapitalization.sentences,
                      style: TextStyle(color: _lzFg(ink), fontSize: 14),
                      decoration: _lightDeco(qs[i][1], hint: qs[i][2])),
                  const SizedBox(height: 10),
                ],
                _lzNote(Icons.edit_note_rounded,
                    'She fills only the fields you’ve left empty, and you read it all before it goes live.'),
                if (busy) ...<Widget>[
                  const SizedBox(height: 12),
                  _lzBusy('June is writing your site. This takes about twenty seconds.'),
                ],
                if (err.isNotEmpty) ...<Widget>[
                  const SizedBox(height: 12),
                  _pcA_status(err, false),
                ],
              ],
              footer: _lzActions(
                  secondary: 'Cancel',
                  onSecondary: () => Navigator.pop(dc2),
                  primary: enough ? 'Write it' : 'Tell June how you met',
                  icon: Icons.auto_awesome_rounded,
                  busy: busy,
                  onPrimary: enough ? write : null));
        },
      ),
    );
    open = false;
    return out;
  }""")

    # _juneSiteResult
    rep(r"""  Future<bool> _juneSiteResult(BuildContext ctx, List<String> filled,
      Map<String, dynamic> meta, String tpl, String current) async {
    final List<String> checks = ((meta['toConfirm'] is List)
            ? (meta['toConfirm'] as List)
            : const <dynamic>[])
        .map((dynamic e) => e.toString())
        .toList();
    final String why = (meta['designWhy'] ?? '').toString();
    final bool offer = tpl.isNotEmpty && tpl != current;
    final String nice =
        tpl.isEmpty ? '' : tpl[0].toUpperCase() + tpl.substring(1);
    final bool? use = await _lzDialog<bool>(
      context: ctx,
      builder: (BuildContext dc) => AlertDialog(
        backgroundColor: _lzBg(ivory),
        title: Text(filled.isEmpty ? 'Nothing to fill' : 'June’s draft is in',
            style: TextStyle(color: _lzFg(plum))),
        content: SizedBox(
          width: 440,
          child: SingleChildScrollView(
            child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                      filled.isEmpty
                          ? 'Every field June writes already has your words, so she left them alone.'
                          : 'June filled ${filled.join(', ')}. Read it over before you publish — it’s your site.',
                      style: TextStyle(color: _lzFg(ink), fontSize: 13.5)),
                  if (checks.isNotEmpty) ...<Widget>[
                    const SizedBox(height: 12),
                    Text('WORTH CHECKING',
                        style: TextStyle(
                            fontSize: 10.5,
                            letterSpacing: 1.4,
                            color: _lzFg(muted),
                            fontWeight: FontWeight.w700)),
                    const SizedBox(height: 4),
                    for (final String x in checks)
                      Padding(
                        padding: const EdgeInsets.only(top: 3),
                        child: Text('• $x',
                            style: TextStyle(color: _lzFg(ink), fontSize: 13)),
                      ),
                  ],
                  if (offer) ...<Widget>[
                    const SizedBox(height: 12),
                    Text('June suggests the $nice design.',
                        style: TextStyle(
                            color: _lzFg(plum),
                            fontSize: 13.5,
                            fontWeight: FontWeight.w700)),
                    if (why.isNotEmpty)
                      Text(why,
                          style: TextStyle(color: _lzFg(muted), fontSize: 12.5)),
                  ],
                ]),
          ),
        ),
        actions: <Widget>[
          if (offer)
            TextButton(
                onPressed: _h(() => Navigator.pop(dc, false)),
                child: Text('Keep my design',
                    style: TextStyle(color: _lzFg(ink)))),
          FilledButton(
              style: FilledButton.styleFrom(
                  backgroundColor: gold, foregroundColor: plum),
              onPressed: _h(() => Navigator.pop(dc, offer)),
              child: Text(offer ? 'Use $nice' : 'Done')),
        ],
      ),
    );
    return use == true;
  }""",
        r"""  Future<bool> _juneSiteResult(BuildContext ctx, List<String> filled,
      Map<String, dynamic> meta, String tpl, String current) async {
    final List<String> checks = ((meta['toConfirm'] is List)
            ? (meta['toConfirm'] as List)
            : const <dynamic>[])
        .map((dynamic e) => e.toString())
        .toList();
    final String why = (meta['designWhy'] ?? '').toString();
    final bool offer = tpl.isNotEmpty && tpl != current;
    final String nice =
        tpl.isEmpty ? '' : tpl[0].toUpperCase() + tpl.substring(1);
    final bool? use = await _lzSheet<bool>(
      context: ctx,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext dc) => _lzFrame(dc,
          icon: filled.isEmpty ? Icons.check_rounded : Icons.auto_awesome_rounded,
          title: filled.isEmpty ? 'Nothing to fill' : 'June’s words are in',
          subtitle: filled.isEmpty
              ? 'Every field June writes already has your words, so she left them alone.'
              : 'Read it over before you publish. It’s your site.',
          children: <Widget>[
            if (filled.isNotEmpty) ...<Widget>[
              _lzSection('What she filled', trailing: '${filled.length}'),
              Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                for (final String f in filled) _pcA_chip(Icons.check_rounded, f),
              ]),
            ],
            if (checks.isNotEmpty) ...<Widget>[
              _lzSection('Worth checking'),
              for (final String x in checks)
                Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.fromLTRB(14, 11, 14, 11),
                  decoration: BoxDecoration(
                      color: _lzBg(cardBg),
                      borderRadius: BorderRadius.circular(13),
                      border: Border.all(color: _lzLine(goldLine))),
                  child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                    Icon(Icons.fact_check_outlined, size: 18, color: _lzFg(plum)),
                    const SizedBox(width: 10),
                    Expanded(
                        child: Text(x,
                            style: TextStyle(color: _lzFg(ink), fontSize: 13.5, height: 1.4))),
                  ]),
                ),
            ],
            if (offer) ...<Widget>[
              _lzSection('A design to match'),
              Container(
                padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
                decoration: BoxDecoration(
                    color: plumDeep, borderRadius: BorderRadius.circular(16)),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                  const Icon(Icons.palette_outlined, color: gold, size: 22),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                      Text('June suggests $nice',
                          style: const TextStyle(
                              color: ivory, fontSize: 15, fontWeight: FontWeight.w700)),
                      if (why.isNotEmpty) ...<Widget>[
                        const SizedBox(height: 3),
                        Text(why,
                            style: TextStyle(
                                color: ivory.withOpacity(.78), fontSize: 13, height: 1.4)),
                      ],
                    ]),
                  ),
                ]),
              ),
            ],
          ],
          footer: _lzActions(
              secondary: offer ? 'Keep my design' : null,
              onSecondary: () => Navigator.pop(dc, false),
              primary: offer ? 'Use $nice' : 'Done',
              icon: offer ? Icons.palette_outlined : Icons.check_rounded,
              onPrimary: () => Navigator.pop(dc, offer))),
    );
    return use == true;
  }""")

    # _editGuest
    rep(r"""  Future<void> _editGuest([String? id, Map<String, dynamic>? cur]) async {
    final Map<String, dynamic> c = cur ?? <String, dynamic>{};
    final TextEditingController nameC =
        TextEditingController(text: (c['name'] ?? '') as String);
    final TextEditingController partyC =
        TextEditingController(text: (c['party'] ?? '') as String);
    final TextEditingController emailC =
        TextEditingController(text: (c['email'] ?? '') as String);
    final TextEditingController addrC =
        TextEditingController(text: (c['address'] ?? '') as String);
    final TextEditingController plusC = TextEditingController(
        text: c['plusOnes'] == null ? '0' : c['plusOnes'].toString());
    final TextEditingController allergyC =
        TextEditingController(text: (c['allergies'] ?? '') as String);
    String side = (c['side'] ?? 'both') as String;
    String group = (c['group'] ?? 'friends') as String;
    String rsvp = (c['rsvp'] ?? 'pending') as String;
    String meal = (c['meal'] ?? '') as String;
    bool thanked = c['thankYouAt'] != null; // v137

    final bool? ok = await _lzDialog<bool>(
      context: context,
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) => AlertDialog(
          backgroundColor: _lzBg(ivory),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: Text(id == null ? 'Add guest' : 'Edit guest',
              style:  TextStyle(
                  color: _lzFg(plum), fontWeight: FontWeight.w700, fontSize: 17)),
          content: SizedBox(
            width: 340,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  TextField(
                      controller: nameC,
                      style:  TextStyle(color: _lzFg(ink), fontSize: 14),
                      decoration: _lightDeco('Name')),
                  const SizedBox(height: 10),
                  TextField(
                      controller: partyC,
                      style:  TextStyle(color: _lzFg(ink), fontSize: 14),
                      decoration: _lightDeco('Party / household (optional)',
                          hint: 'e.g. The Garcias')),
                  const SizedBox(height: 10),
                  Row(children: <Widget>[
                    Expanded(
                      child: DropdownButtonFormField<String>(
                        dropdownColor: _lzBg(ivory),
                        style:  TextStyle(color: _lzFg(ink), fontSize: 14),
                        iconEnabledColor: plum,
                        value: group,
                        decoration: _lightDeco('Group'),
                        items: const <DropdownMenuItem<String>>[
                          DropdownMenuItem(
                              value: 'family', child: Text('Family')),
                          DropdownMenuItem(
                              value: 'friends', child: Text('Friends')),
                          DropdownMenuItem(
                              value: 'wedding-party',
                              child: Text('Wedding party')),
                          DropdownMenuItem(value: 'work', child: Text('Work')),
                          DropdownMenuItem(
                              value: 'other', child: Text('Other')),
                        ],
                        onChanged: (String? v) =>
                            setD(() => group = v ?? group),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: DropdownButtonFormField<String>(
                        dropdownColor: _lzBg(ivory),
                        style:  TextStyle(color: _lzFg(ink), fontSize: 14),
                        iconEnabledColor: plum,
                        value: side,
                        decoration: _lightDeco('Side'),
                        items: const <DropdownMenuItem<String>>[
                          DropdownMenuItem(
                              value: 'partner1', child: Text('Partner 1')),
                          DropdownMenuItem(
                              value: 'partner2', child: Text('Partner 2')),
                          DropdownMenuItem(value: 'both', child: Text('Both')),
                        ],
                        onChanged: (String? v) => setD(() => side = v ?? side),
                      ),
                    ),
                  ]),
                  const SizedBox(height: 10),
                  Row(children: <Widget>[
                    Expanded(
                      child: DropdownButtonFormField<String>(
                        dropdownColor: _lzBg(ivory),
                        style:  TextStyle(color: _lzFg(ink), fontSize: 14),
                        iconEnabledColor: plum,
                        value: rsvp,
                        decoration: _lightDeco('RSVP'),
                        items: const <DropdownMenuItem<String>>[
                          DropdownMenuItem(
                              value: 'pending', child: Text('Pending')),
                          DropdownMenuItem(
                              value: 'yes', child: Text('Attending')),
                          DropdownMenuItem(
                              value: 'no', child: Text('Declined')),
                        ],
                        onChanged: (String? v) => setD(() => rsvp = v ?? rsvp),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: TextField(
                          controller: plusC,
                          keyboardType: TextInputType.number,
                          style:  TextStyle(color: _lzFg(ink), fontSize: 14),
                          decoration: _lightDeco('+1s')),
                    ),
                  ]),
                  const SizedBox(height: 10),
                  TextField(
                      onChanged: (String v) => meal = v,
                      controller: TextEditingController(text: meal),
                      style:  TextStyle(color: _lzFg(ink)),
                      decoration: _lightDeco('Meal (optional)',
                          hint: 'Chicken, Veg\u2026')),
                  if ((c['tableName'] ?? '').toString().trim().isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: Text(
                          'Seated at ${c['tableName']} - move them on the seating chart.',
                          style:  TextStyle(fontSize: 11.5, color: _lzFg(muted))),
                    ),
                  const SizedBox(height: 10),
                  TextField(
                      controller: allergyC,
                      style:  TextStyle(color: _lzFg(ink)),
                      decoration: _lightDeco('Allergies / dietary (optional)',
                          hint: 'Gluten-free, nut allergy\u2026')),
                  const SizedBox(height: 10),
                  TextField(
                      controller: emailC,
                      keyboardType: TextInputType.emailAddress,
                      style:  TextStyle(color: _lzFg(ink), fontSize: 14),
                      decoration: _lightDeco('Email (optional)')),
                  if (rsvp == 'yes')
                    SwitchListTile(
                      dense: true,
                      contentPadding: EdgeInsets.zero,
                      activeColor: Colors.white,
                      activeTrackColor: vGreen,
                      inactiveThumbColor: Colors.white,
                      inactiveTrackColor: muted.withOpacity(.4),
                      title: const Text('Thank-you note sent',
                          style: TextStyle(fontSize: 13.5)),
                      value: thanked,
                      onChanged: _hb((bool v) => setD(() => thanked = v)),
                    ),
                  const SizedBox(height: 10),
                  TextField(
                      controller: addrC,
                      style:  TextStyle(color: _lzFg(ink), fontSize: 14),
                      decoration: _lightDeco('Mailing address (optional)')),
                ],
              ),
            ),
          ),
          actions: <Widget>[
            if (id != null)
              TextButton.icon(
                onPressed: _h(() => _personalLink(id, <String, dynamic>{
                      'name': nameC.text.trim(),
                      'party': partyC.text.trim(),
                      'plusOnes': int.tryParse(plusC.text.trim()) ?? 0,
                    })),
                icon:  Icon(Icons.link_rounded, size: 16, color: _lzFg(plum)),
                label:  Text('Personal RSVP link',
                    style: TextStyle(color: _lzFg(plum), fontSize: 12.5)),
              ),
            if (id != null)
              TextButton(
                onPressed: _h(() async {
                  // v139: ask first, and take the personal-link doc with it
                  final bool? sure = await _lzDialog<bool>(
                    context: ctx2,
                    builder: (BuildContext dc) => AlertDialog(
                      backgroundColor: _lzBg(ivory),
                      title: Text('Remove ${nameC.text.trim().isEmpty ? 'this guest' : nameC.text.trim()}?',
                          style:  TextStyle(color: _lzFg(plum))),
                      content:  Text(
                          'They come off the list, the seating chart and the site\u2019s seat finder.',
                          style: TextStyle(color: _lzFg(ink), fontSize: 14)),
                      actions: <Widget>[
                        TextButton(
                            onPressed: () => Navigator.pop(dc, false),
                            child:  Text('Keep',
                                style: TextStyle(color: _lzFg(ink)))),
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
                }),
                child: const Text('Delete',
                    style: TextStyle(color: Color(0xFF8A7D90))),
              ),
            TextButton(
                onPressed: _h(() => Navigator.pop(ctx2, false)),
                child:  Text('Cancel', style: TextStyle(color: _lzFg(ink)))),
            FilledButton(
              style: FilledButton.styleFrom(
                  backgroundColor: gold, foregroundColor: plum),
              onPressed: _h(() => Navigator.pop(ctx2, true)),
              child: const Text('Save'),
            ),
          ],
        ),
      ),
    );
    if (ok != true || nameC.text.trim().isEmpty) {
      return;
    }
    final Map<String, dynamic> data = <String, dynamic>{
      'name': nameC.text.trim(),
      'party': partyC.text.trim(),
      'group': group,
      'side': side,
      'rsvp': rsvp,
      'meal': meal.trim(),
      'plusOnes': int.tryParse(plusC.text.trim()) ?? 0,
      'allergies': allergyC.text.trim(),
      'email': emailC.text.trim(),
      'address': addrC.text.trim(),
      'thankYouAt': thanked
          ? (c['thankYouAt'] ?? FieldValue.serverTimestamp())
          : null,
      'updatedAt': FieldValue.serverTimestamp(),
    };
    if (id == null) {
      data['createdAt'] = FieldValue.serverTimestamp();
      await _guestsRef.add(data);
      _logActivity('added ${data['name']} to the guest list.', open: 'guests');
    } else {
      await _guestsRef.doc(id).set(data, SetOptions(merge: true));
    }
  }""",
        r"""  Future<void> _editGuest([String? id, Map<String, dynamic>? cur]) async {
    final Map<String, dynamic> c = cur ?? <String, dynamic>{};
    final TextEditingController nameC =
        TextEditingController(text: (c['name'] ?? '') as String);
    final TextEditingController partyC =
        TextEditingController(text: (c['party'] ?? '') as String);
    final TextEditingController emailC =
        TextEditingController(text: (c['email'] ?? '') as String);
    final TextEditingController addrC =
        TextEditingController(text: (c['address'] ?? '') as String);
    final TextEditingController plusC = TextEditingController(
        text: c['plusOnes'] == null ? '0' : c['plusOnes'].toString());
    final TextEditingController allergyC =
        TextEditingController(text: (c['allergies'] ?? '') as String);
    String side = (c['side'] ?? 'both') as String;
    String group = (c['group'] ?? 'friends') as String;
    String rsvp = (c['rsvp'] ?? 'pending') as String;
    String meal = (c['meal'] ?? '') as String;
    final TextEditingController mealC = TextEditingController(text: meal);
    bool thanked = c['thankYouAt'] != null; // v137
    bool deleting = false;

    final bool? ok = await _lzSheet<bool>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) {
          final bool valid = nameC.text.trim().isNotEmpty;

          Widget chips(List<List<String>> opts, String val, void Function(String) pick) =>
              Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                for (final List<String> o in opts)
                  _Press(
                    scale: .97,
                    onTap: () => setD(() => pick(o[0])),
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 180),
                      padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 8),
                      decoration: BoxDecoration(
                          color: val == o[0] ? plumDeep : _lzBg(cardBg),
                          borderRadius: BorderRadius.circular(30),
                          border: Border.all(
                              color: val == o[0] ? plumDeep : _lzLine(goldLine))),
                      child: Text(o[1],
                          style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w700,
                              color: val == o[0] ? gold : _lzFg(plum))),
                    ),
                  ),
              ]);

          Future<void> remove() async {
            // v139: ask first, and take the personal-link doc with it
            final bool sure = await _lzConfirm(
                'Remove ${nameC.text.trim().isEmpty ? 'this guest' : nameC.text.trim()}?',
                'They come off the list, the seating chart and the site’s seat finder.',
                confirm: 'Remove guest',
                cancel: 'Keep',
                danger: true);
            if (!sure) {
              return;
            }
            setD(() => deleting = true);
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
          }

          return _lzFrame(ctx2,
              icon: id == null ? Icons.person_add_alt_1_rounded : Icons.person_outline_rounded,
              title: id == null ? 'Add guest' : 'Edit guest',
              subtitle: id == null
                  ? 'Only the name is needed. Fill in the rest any time.'
                  : 'Changes save to your guest list and seating chart.',
              children: <Widget>[
                const SizedBox(height: 14),
                TextField(
                    controller: nameC,
                    autofocus: id == null,
                    textCapitalization: TextCapitalization.words,
                    textInputAction: TextInputAction.next,
                    onChanged: (_) => setD(() {}),
                    style: TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _lightDeco('Name')),
                const SizedBox(height: 10),
                TextField(
                    controller: partyC,
                    textCapitalization: TextCapitalization.words,
                    textInputAction: TextInputAction.next,
                    style: TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _lightDeco('Party / household (optional)',
                        hint: 'e.g. The Garcias')),
                _lzSection('RSVP'),
                Row(children: <Widget>[
                  Expanded(
                    child: chips(const <List<String>>[
                      <String>['pending', 'Waiting'],
                      <String>['yes', 'Attending'],
                      <String>['no', 'Declined'],
                    ], rsvp, (String v) => rsvp = v),
                  ),
                  const SizedBox(width: 10),
                  SizedBox(
                    width: 84,
                    child: TextField(
                        controller: plusC,
                        keyboardType: TextInputType.number,
                        style: TextStyle(color: _lzFg(ink), fontSize: 14),
                        decoration: _lightDeco('+1s')),
                  ),
                ]),
                if (rsvp == 'yes')
                  SwitchListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    activeColor: Colors.white,
                    activeTrackColor: vGreen,
                    inactiveThumbColor: Colors.white,
                    inactiveTrackColor: muted.withOpacity(.4),
                    title: Text('Thank-you note sent',
                        style: TextStyle(fontSize: 13.5, color: _lzFg(ink))),
                    value: thanked,
                    onChanged: _hb((bool v) => setD(() => thanked = v)),
                  ),
                _lzSection('Group'),
                chips(const <List<String>>[
                  <String>['family', 'Family'],
                  <String>['friends', 'Friends'],
                  <String>['wedding-party', 'Wedding party'],
                  <String>['work', 'Work'],
                  <String>['other', 'Other'],
                ], group, (String v) => group = v),
                _lzSection('Side'),
                chips(const <List<String>>[
                  <String>['partner1', 'Partner 1'],
                  <String>['partner2', 'Partner 2'],
                  <String>['both', 'Both'],
                ], side, (String v) => side = v),
                _lzSection('Food'),
                TextField(
                    onChanged: (String v) => meal = v,
                    controller: mealC,
                    textCapitalization: TextCapitalization.sentences,
                    style: TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _lightDeco('Meal (optional)',
                        hint: 'Chicken, Veg…')),
                if ((c['tableName'] ?? '').toString().trim().isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: _lzNote(Icons.table_restaurant_outlined,
                        'Seated at ${c['tableName']}. Move them on the seating chart.'),
                  ),
                const SizedBox(height: 10),
                TextField(
                    controller: allergyC,
                    textCapitalization: TextCapitalization.sentences,
                    style: TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _lightDeco('Allergies / dietary (optional)',
                        hint: 'Gluten-free, nut allergy…')),
                _lzSection('Contact'),
                TextField(
                    controller: emailC,
                    keyboardType: TextInputType.emailAddress,
                    autocorrect: false,
                    style: TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _lightDeco('Email (optional)')),
                const SizedBox(height: 10),
                TextField(
                    controller: addrC,
                    keyboardType: TextInputType.streetAddress,
                    minLines: 1,
                    maxLines: 3,
                    style: TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _lightDeco('Mailing address (optional)')),
                if (id != null) ...<Widget>[
                  _lzSection('More'),
                  Row(children: <Widget>[
                    Expanded(
                      child: _pcA_pick(Icons.link_rounded, 'Personal RSVP link',
                          'Just for this guest', false, deleting
                              ? null
                              : () => _personalLink(id, <String, dynamic>{
                                    'name': nameC.text.trim(),
                                    'party': partyC.text.trim(),
                                    'plusOnes': int.tryParse(plusC.text.trim()) ?? 0,
                                  })),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: _pcA_pick(Icons.person_remove_outlined, 'Remove guest',
                          'From the list and seating', false, deleting ? null : remove),
                    ),
                  ]),
                ],
                if (deleting) ...<Widget>[
                  const SizedBox(height: 12),
                  _lzBusy('Removing them…'),
                ],
              ],
              footer: _lzActions(
                  secondary: 'Cancel',
                  onSecondary: () => Navigator.pop(ctx2, false),
                  primary: id == null ? 'Add guest' : 'Save',
                  icon: Icons.check_rounded,
                  busy: deleting,
                  onPrimary: valid ? () => Navigator.pop(ctx2, true) : null));
        },
      ),
    );
    if (ok != true || nameC.text.trim().isEmpty) {
      return;
    }
    final Map<String, dynamic> data = <String, dynamic>{
      'name': nameC.text.trim(),
      'party': partyC.text.trim(),
      'group': group,
      'side': side,
      'rsvp': rsvp,
      'meal': meal.trim(),
      'plusOnes': int.tryParse(plusC.text.trim()) ?? 0,
      'allergies': allergyC.text.trim(),
      'email': emailC.text.trim(),
      'address': addrC.text.trim(),
      'thankYouAt': thanked
          ? (c['thankYouAt'] ?? FieldValue.serverTimestamp())
          : null,
      'updatedAt': FieldValue.serverTimestamp(),
    };
    if (id == null) {
      data['createdAt'] = FieldValue.serverTimestamp();
      await _guestsRef.add(data);
      _logActivity('added ${data['name']} to the guest list.', open: 'guests');
    } else {
      await _guestsRef.doc(id).set(data, SetOptions(merge: true));
    }
  }""")

    # _adjustPhotoSheet
    rep(r"""  Future<void> _adjustPhotoSheet(Map<String, dynamic> couple) async {
    final String photo = (couple['photoUrl'] ?? '').toString();
    if (photo.isEmpty) {
      await _changePhoto();
      return;
    }
    double fx = .5, fy = .5;
    final dynamic f = couple['photoFocus'];
    if (f is Map) {
      if (f['x'] is num) fx = (f['x'] as num).toDouble().clamp(0, 1).toDouble();
      if (f['y'] is num) fy = (f['y'] as num).toDouble().clamp(0, 1).toDouble();
    }
    bool saving = false;
    if (!mounted) return;
    await _lzSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: _lzBg(ivory),
      constraints: const BoxConstraints(maxWidth: 620),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) {
          return Padding(
            padding: EdgeInsets.fromLTRB(
                20, 14, 20, 20 + MediaQuery.of(ctx2).viewInsets.bottom),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Center(
                  child: Container(
                      width: 40,
                      height: 4,
                      decoration: BoxDecoration(
                          color: plum.withOpacity(.25),
                          borderRadius: BorderRadius.circular(4))),
                ),
                const SizedBox(height: 14),
                Text('Position your photo',
                    style:
                        _serif(size: 24, weight: FontWeight.w600, color: _lzFg(plum))),
                const SizedBox(height: 4),
                 Text(
                    'Drag the photo until the two of you are where you want them. This is how it crops on your home screen.',
                    style:
                        TextStyle(color: _lzFg(muted), fontSize: 13.5, height: 1.4)),
                const SizedBox(height: 14),
                LayoutBuilder(builder: (BuildContext lc, BoxConstraints cons) {
                  final double w = cons.maxWidth;
                  final double h = w < 520 ? w * .78 : w * .42;
                  return ClipRRect(
                    borderRadius: BorderRadius.circular(18),
                    child: GestureDetector(
                      behavior: HitTestBehavior.opaque,
                      onPanUpdate: (DragUpdateDetails d) {
                        // dragging the picture right shows more of its left
                        // side, i.e. the focus point moves left.
                        setD(() {
                          fx = (fx - d.delta.dx / w).clamp(0.0, 1.0).toDouble();
                          fy = (fy - d.delta.dy / h).clamp(0.0, 1.0).toDouble();
                        });
                      },
                      child: SizedBox(
                        width: w,
                        height: h,
                        child: Stack(fit: StackFit.expand, children: <Widget>[
                          const ColoredBox(color: plumDeep),
                          Image(
                            image:
                                ResizeImage(NetworkImage(photo), width: 1400),
                            fit: BoxFit.cover,
                            alignment: Alignment(fx * 2 - 1, fy * 2 - 1),
                          ),
                          // the same scrim the hero paints, so the preview
                          // is honest about how dark the bottom gets
                          const DecoratedBox(
                            decoration: BoxDecoration(
                              gradient: LinearGradient(
                                begin: Alignment.topCenter,
                                end: Alignment.bottomCenter,
                                colors: <Color>[
                                  Color(0x333D1C3B),
                                  Color(0xC63D1C3B),
                                  Color(0xF23D1C3B)
                                ],
                                stops: <double>[0, .55, 1],
                              ),
                            ),
                          ),
                          Positioned(
                            left: 14,
                            bottom: 12,
                            child: Row(children: <Widget>[
                              const Icon(Icons.open_with_rounded,
                                  color: ivory, size: 14),
                              const SizedBox(width: 6),
                              Text('Drag to move',
                                  style: TextStyle(
                                      color: ivory.withOpacity(.85),
                                      fontSize: 12,
                                      fontWeight: FontWeight.w600)),
                            ]),
                          ),
                        ]),
                      ),
                    ),
                  );
                }),
                const SizedBox(height: 14),
                Row(children: <Widget>[
                  TextButton.icon(
                    onPressed: _h(() => setD(() {
                          fx = .5;
                          fy = .5;
                        })),
                    icon:  Icon(Icons.center_focus_strong_rounded,
                        color: _lzFg(plum), size: 18),
                    label:  Text('Center', style: TextStyle(color: _lzFg(plum))),
                  ),
                  TextButton.icon(
                    onPressed: _h(() async {
                      Navigator.pop(ctx2);
                      await _changePhoto();
                    }),
                    icon:  Icon(Icons.photo_camera_rounded,
                        color: _lzFg(plum), size: 18),
                    label:  Text('Different photo',
                        style: TextStyle(color: _lzFg(plum))),
                  ),
                  const Spacer(),
                  FilledButton(
                    style: FilledButton.styleFrom(
                        backgroundColor: gold,
                        foregroundColor: plumDeep,
                        padding: const EdgeInsets.symmetric(
                            horizontal: 22, vertical: 12),
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12))),
                    onPressed: _h(saving
                        ? null
                        : () async {
                            setD(() => saving = true);
                            try {
                              await _coupleRef.set(<String, dynamic>{
                                'photoFocus': <String, double>{'x': fx, 'y': fy}
                              }, SetOptions(merge: true));
                              if (ctx2.mounted) Navigator.pop(ctx2);
                              _toastC('Photo position saved \u2713');
                            } catch (_) {
                              setD(() => saving = false);
                              _toastC('Could not save - try again.');
                            }
                          }),
                    child: Text(saving ? 'Saving\u2026' : 'Save',
                        style: const TextStyle(fontWeight: FontWeight.w700)),
                  ),
                ]),
              ],
            ),
          );
        },
      ),
    );
  }""",
        r"""  Future<void> _adjustPhotoSheet(Map<String, dynamic> couple) async {
    final String photo = (couple['photoUrl'] ?? '').toString();
    if (photo.isEmpty) {
      await _changePhoto();
      return;
    }
    double fx = .5, fy = .5;
    final dynamic f = couple['photoFocus'];
    if (f is Map) {
      if (f['x'] is num) fx = (f['x'] as num).toDouble().clamp(0, 1).toDouble();
      if (f['y'] is num) fy = (f['y'] as num).toDouble().clamp(0, 1).toDouble();
    }
    bool saving = false;
    String err = '';
    if (!mounted) return;
    await _lzSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: _lzBg(ivory),
      constraints: const BoxConstraints(maxWidth: 620),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) {
          return Padding(
            padding: EdgeInsets.fromLTRB(
                20, 10, 12, 20 + MediaQuery.of(ctx2).viewInsets.bottom),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: Text('Position your photo',
                          style: _serif(
                              size: 24, weight: FontWeight.w600, color: _lzFg(plum))),
                    ),
                  ),
                  IconButton(
                      tooltip: 'Close',
                      icon: Icon(Icons.close_rounded, color: _lzFg(muted)),
                      onPressed: _h(() => Navigator.of(ctx2).maybePop())),
                ]),
                Text(
                    'Drag it until the two of you sit where you want. This is how it crops on your home screen.',
                    style:
                        TextStyle(color: _lzFg(muted), fontSize: 13.5, height: 1.4)),
                const SizedBox(height: 14),
                LayoutBuilder(builder: (BuildContext lc, BoxConstraints cons) {
                  final double w = cons.maxWidth;
                  final double h = w < 520 ? w * .78 : w * .42;
                  return ClipRRect(
                    borderRadius: BorderRadius.circular(18),
                    child: GestureDetector(
                      behavior: HitTestBehavior.opaque,
                      onPanUpdate: (DragUpdateDetails d) {
                        // dragging the picture right shows more of its left
                        // side, i.e. the focus point moves left.
                        setD(() {
                          fx = (fx - d.delta.dx / w).clamp(0.0, 1.0).toDouble();
                          fy = (fy - d.delta.dy / h).clamp(0.0, 1.0).toDouble();
                        });
                      },
                      child: SizedBox(
                        width: w,
                        height: h,
                        child: Stack(fit: StackFit.expand, children: <Widget>[
                          const ColoredBox(color: plumDeep),
                          Image(
                            image:
                                ResizeImage(NetworkImage(photo), width: 1400),
                            fit: BoxFit.cover,
                            alignment: Alignment(fx * 2 - 1, fy * 2 - 1),
                          ),
                          // the same scrim the hero paints, so the preview
                          // is honest about how dark the bottom gets
                          const DecoratedBox(
                            decoration: BoxDecoration(
                              gradient: LinearGradient(
                                begin: Alignment.topCenter,
                                end: Alignment.bottomCenter,
                                colors: <Color>[
                                  Color(0x333D1C3B),
                                  Color(0xC63D1C3B),
                                  Color(0xF23D1C3B)
                                ],
                                stops: <double>[0, .55, 1],
                              ),
                            ),
                          ),
                          Positioned(
                            left: 14,
                            bottom: 12,
                            child: Row(children: <Widget>[
                              const Icon(Icons.open_with_rounded,
                                  color: ivory, size: 14),
                              const SizedBox(width: 6),
                              Text('Drag to move',
                                  style: TextStyle(
                                      color: ivory.withOpacity(.85),
                                      fontSize: 12,
                                      fontWeight: FontWeight.w600)),
                            ]),
                          ),
                        ]),
                      ),
                    ),
                  );
                }),
                const SizedBox(height: 14),
                Row(children: <Widget>[
                  TextButton.icon(
                    onPressed: _h(() => setD(() {
                          fx = .5;
                          fy = .5;
                        })),
                    icon:  Icon(Icons.center_focus_strong_rounded,
                        color: _lzFg(plum), size: 18),
                    label:  Text('Center', style: TextStyle(color: _lzFg(plum))),
                  ),
                  TextButton.icon(
                    onPressed: _h(() async {
                      Navigator.pop(ctx2);
                      await _changePhoto();
                    }),
                    icon:  Icon(Icons.photo_camera_rounded,
                        color: _lzFg(plum), size: 18),
                    label:  Text('Different photo',
                        style: TextStyle(color: _lzFg(plum))),
                  ),
                ]),
                if (err.isNotEmpty) ...<Widget>[
                  const SizedBox(height: 8),
                  _pcA_status(err, false),
                ],
                const SizedBox(height: 12),
                Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: _lzActions(
                      secondary: 'Cancel',
                      onSecondary: () => Navigator.pop(ctx2),
                      primary: 'Save position',
                      icon: Icons.check_rounded,
                      busy: saving,
                      onPrimary: () async {
                        setD(() {
                          saving = true;
                          err = '';
                        });
                        try {
                          await _coupleRef.set(<String, dynamic>{
                            'photoFocus': <String, double>{'x': fx, 'y': fy}
                          }, SetOptions(merge: true));
                          if (ctx2.mounted) Navigator.pop(ctx2);
                          _toastC('Photo position saved.');
                        } catch (_) {
                          if (ctx2.mounted) {
                            setD(() {
                              saving = false;
                              err = 'Couldn\u2019t save. Check your connection and try again.';
                            });
                          }
                        }
                      }),
                ),
              ],
            ),
          );
        },
      ),
    );
  }""")

    # _setBudgetSheet
    rep(r"""  Future<void> _setBudgetSheet(num? current) async {
    final TextEditingController c = TextEditingController(
        text: current == null ? '' : current.round().toString());
    final bool? ok = await _lzDialog<bool>(
      context: context,
      builder: (BuildContext ctx) => AlertDialog(
        backgroundColor: _lzBg(ivory),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title:  Text('Your wedding budget',
            style: TextStyle(
                color: _lzFg(plum), fontWeight: FontWeight.w700, fontSize: 18)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
             Text(
                'The number you\u2019re planning around. Lazo tracks spending against it as you book your team.',
                style: TextStyle(fontSize: 12.5, color: _lzFg(muted))),
            const SizedBox(height: 12),
            TextField(
              controller: c,
              keyboardType: TextInputType.number,
              autofocus: true,
              style:  TextStyle(color: _lzFg(ink)),
              decoration: _lightDeco('Total budget \$'),
            ),
          ],
        ),
        actions: <Widget>[
          TextButton(
              onPressed: _h(() => Navigator.pop(ctx, false)),
              child:  Text('Cancel', style: TextStyle(color: _lzFg(ink)))),
          FilledButton(
            style: FilledButton.styleFrom(
                backgroundColor: gold, foregroundColor: plum),
            onPressed: _h(() => Navigator.pop(ctx, true)),
            child: const Text('Save'),
          ),
        ],
      ),
    );
    if (ok != true) {
      return;
    }
    final double? v = double.tryParse(c.text.trim().replaceAll(',', ''));
    await _coupleRef.set(<String, dynamic>{
      'budgetTotal': v,
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
  }""",
        r"""  Future<void> _setBudgetSheet(num? current) async {
    final TextEditingController c = TextEditingController(
        text: current == null ? '' : current.round().toString());
    final bool? ok = await _lzSheet<bool>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 480),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) {
          final double? v = double.tryParse(c.text.trim().replaceAll(',', ''));
          final bool valid = c.text.trim().isEmpty || (v != null && v >= 0);
          return _lzFrame(ctx2,
              icon: Icons.savings_outlined,
              title: 'Your wedding budget',
              subtitle: 'The number you’re planning around. Lazo tracks spending against it as you book.',
              children: <Widget>[
                const SizedBox(height: 14),
                TextField(
                  controller: c,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  autofocus: true,
                  textInputAction: TextInputAction.done,
                  onChanged: (_) => setD(() {}),
                  onSubmitted: (_) {
                    if (valid) Navigator.pop(ctx2, true);
                  },
                  style: TextStyle(color: _lzFg(ink), fontSize: 20, fontWeight: FontWeight.w600),
                  decoration: _lightDeco('Total budget', hint: '35,000', prefix: '\$ '),
                ),
              ],
              footer: _lzActions(
                  secondary: 'Cancel',
                  onSecondary: () => Navigator.pop(ctx2, false),
                  primary: 'Save budget',
                  icon: Icons.check_rounded,
                  onPrimary: valid ? () => Navigator.pop(ctx2, true) : null));
        },
      ),
    );
    if (ok != true) {
      return;
    }
    final double? v = double.tryParse(c.text.trim().replaceAll(',', ''));
    await _coupleRef.set(<String, dynamic>{
      'budgetTotal': v,
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
  }""")

    # _editVendor
    rep(r"""  Future<void> _editVendor(
      String slug, String label, Map<String, dynamic> current) async {
    final nameC =
        TextEditingController(text: (current['vendorName'] ?? '') as String);
    final planC = TextEditingController(
        text: current['budgetPlanned'] == null
            ? ''
            : (current['budgetPlanned'] as num).toStringAsFixed(0));
    final spentC = TextEditingController(
        text: current['budgetActual'] == null
            ? ''
            : (current['budgetActual'] as num).toStringAsFixed(0));
    final ok = await _lzDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: _lzBg(ivory),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Text('Your $label',
            style:  TextStyle(
                color: _lzFg(plum), fontWeight: FontWeight.w700, fontSize: 18)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
                controller: nameC,
                style:  TextStyle(color: _lzFg(ink)),
                decoration: _lightDeco('Vendor name')),
            const SizedBox(height: 12),
            Row(children: [
              Expanded(
                child: TextField(
                    controller: planC,
                    keyboardType: TextInputType.number,
                    style:  TextStyle(color: _lzFg(ink)),
                    decoration: _lightDeco('Budget \$')),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: TextField(
                    controller: spentC,
                    keyboardType: TextInputType.number,
                    style:  TextStyle(color: _lzFg(ink)),
                    decoration: _lightDeco('Spent \$')),
              ),
            ]),
          ],
        ),
        actions: [
          TextButton(
              onPressed: _h(() => Navigator.pop(ctx, false)),
              child:  Text('Cancel', style: TextStyle(color: _lzFg(ink)))),
          FilledButton(
            style: FilledButton.styleFrom(
                backgroundColor: gold, foregroundColor: plum),
            onPressed: _h(() => Navigator.pop(ctx, true)),
            child: const Text('Save'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    await _planRef.doc(slug).set({
      'vendorName': nameC.text.trim(),
      'budgetPlanned': double.tryParse(planC.text.trim()),
      'budgetActual': double.tryParse(spentC.text.trim()),
      'updatedAt': FieldValue.serverTimestamp(),
      'updatedBy': _bdMe()[1], // v135: the last-change line on the budget card
    }, SetOptions(merge: true));
  }""",
        r"""  Future<void> _editVendor(
      String slug, String label, Map<String, dynamic> current) async {
    final nameC =
        TextEditingController(text: (current['vendorName'] ?? '') as String);
    final planC = TextEditingController(
        text: current['budgetPlanned'] == null
            ? ''
            : (current['budgetPlanned'] as num).toStringAsFixed(0));
    final spentC = TextEditingController(
        text: current['budgetActual'] == null
            ? ''
            : (current['budgetActual'] as num).toStringAsFixed(0));
    final ok = await _lzSheet<bool>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 520),
      builder: (ctx) => _lzFrame(ctx,
          icon: Icons.storefront_outlined,
          title: 'Your $label',
          subtitle: 'Who you booked, and what it costs.',
          children: <Widget>[
            const SizedBox(height: 14),
            TextField(
                controller: nameC,
                autofocus: nameC.text.isEmpty,
                textCapitalization: TextCapitalization.words,
                textInputAction: TextInputAction.next,
                style: TextStyle(color: _lzFg(ink), fontSize: 14),
                decoration: _lightDeco('Vendor name')),
            _lzSection('Money'),
            Row(children: <Widget>[
              Expanded(
                child: TextField(
                    controller: planC,
                    keyboardType: TextInputType.number,
                    textInputAction: TextInputAction.next,
                    style: TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _lightDeco('Budget', prefix: '\$ ')),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: TextField(
                    controller: spentC,
                    keyboardType: TextInputType.number,
                    textInputAction: TextInputAction.done,
                    onSubmitted: (_) => Navigator.pop(ctx, true),
                    style: TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _lightDeco('Spent', prefix: '\$ ')),
              ),
            ]),
          ],
          footer: _lzActions(
              secondary: 'Cancel',
              onSecondary: () => Navigator.pop(ctx, false),
              primary: 'Save',
              icon: Icons.check_rounded,
              onPrimary: () => Navigator.pop(ctx, true))),
    );
    if (ok != true) return;
    await _planRef.doc(slug).set({
      'vendorName': nameC.text.trim(),
      'budgetPlanned': double.tryParse(planC.text.trim()),
      'budgetActual': double.tryParse(spentC.text.trim()),
      'updatedAt': FieldValue.serverTimestamp(),
      'updatedBy': _bdMe()[1], // v135: the last-change line on the budget card
    }, SetOptions(merge: true));
  }""")

    # _sendInquiry
    rep(r"""  Future<void> _sendInquiry(Map<String, dynamic> v) async {
    final placeId = (v['placeId'] as String?) ?? '';
    final vendorName = (v['name'] as String?) ?? 'this vendor';
    if (placeId.isEmpty || _uid == null) return;
    // v146: a vendor looking around must never create a real inquiry
    if (_previewVendor != null) {
      _toast(
          'Preview mode: messaging vendors is off here. This is what a couple would see when they reach out to $vendorName.');
      return;
    }
    final String inqCat = _vendorCat(v);
    final coupleSnap = await _coupleRef.get();
    final couple = coupleSnap.data() ?? <String, dynamic>{};
    if (!mounted) return;
    final msgC = TextEditingController(
        text:
            'Hi! We found you on Lazo and would love to hear about your availability and packages.');
    final ok = await _lzDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: _lzBg(ivory),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Text('Contact $vendorName',
            style:  TextStyle(
                color: _lzFg(plum), fontWeight: FontWeight.w700, fontSize: 17)),
        content: SizedBox(
          width: 400,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: msgC,
                maxLines: 4,
                style:  TextStyle(color: _lzFg(ink), fontSize: 14),
                decoration: _lightDeco('Your message'),
              ),
              const SizedBox(height: 10),
              Row(children:  [
                Icon(Icons.verified_rounded, color: _lzFg(vGreen), size: 15),
                SizedBox(width: 6),
                Expanded(
                  child: Text(
                    'Sent as a verified couple with your date attached. Never sold, never shared.',
                    style: TextStyle(fontSize: 11.5, color: _lzFg(muted)),
                  ),
                ),
              ]),
            ],
          ),
        ),
        actions: [
          TextButton(
              onPressed: _h(() => Navigator.pop(ctx, false)),
              child:  Text('Cancel', style: TextStyle(color: _lzFg(ink)))),
          FilledButton(
            style: FilledButton.styleFrom(
                backgroundColor: gold, foregroundColor: plum),
            onPressed: _h(() => Navigator.pop(ctx, true), _Tick.medium),
            child: const Text('Send'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    final ts = couple['weddingDate'];
    final Map<String, dynamic>? refBy =
        _pendingReferral != null && _pendingReferral!['vendorId'] == placeId
            ? <String, dynamic>{
                'vendorId': _pendingReferral!['fromVendorId'],
                'name': _pendingReferral!['fromVendorName']
              }
            : null;
    _pendingReferral = null;
    await FirebaseFirestore.instance.collection('inquiries').add({
      'coupleUid': _cid,
      'vendorId': placeId,
      'vendorName': vendorName,
      'message': msgC.text.trim(),
      'status': 'new',
      if (refBy != null) 'referredBy': refBy,
      'createdAt': FieldValue.serverTimestamp(),
      'structuredIntent': {
        'weddingDate': ts is Timestamp
            ? ts.toDate().toIso8601String().split('T').first
            : 'Date TBD',
        'metroId': _browseMetro,
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
          'status': 'researching',
          'vendorName': vendorName,
          'updatedAt': FieldValue.serverTimestamp(),
        }, SetOptions(merge: true));
      }
    } catch (_) {}
    if (!mounted) return;
    final bool vUnclaimed = ((v['claimedBy'] ?? '') as String? ?? '').isEmpty;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      backgroundColor: _lzBg(ivory),
      duration: Duration(seconds: vUnclaimed ? 6 : 4),
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      content: Text(
          vUnclaimed
              ? 'Sent \u2014 $vendorName hasn\u2019t joined Lazo yet, so we\u2019re letting them know a couple\u2019s waiting. Their phone & website are on their card meanwhile.'
              : 'Sent to $vendorName \uD83D\uDD17',
          style:  TextStyle(color: _lzFg(ink), fontWeight: FontWeight.w600)),
    ));
    _maybeAskPush();
  }""",
        r"""  Future<void> _sendInquiry(Map<String, dynamic> v) async {
    final placeId = (v['placeId'] as String?) ?? '';
    final vendorName = (v['name'] as String?) ?? 'this vendor';
    if (placeId.isEmpty || _uid == null) return;
    // v146: a vendor looking around must never create a real inquiry
    if (_previewVendor != null) {
      _toast(
          'Preview mode: messaging vendors is off here. This is what a couple would see when they reach out to $vendorName.');
      return;
    }
    final String inqCat = _vendorCat(v);
    final coupleSnap = await _coupleRef.get();
    final couple = coupleSnap.data() ?? <String, dynamic>{};
    if (!mounted) return;
    final msgC = TextEditingController(
        text:
            'Hi! We found you on Lazo and would love to hear about your availability and packages.');
    final ts = couple['weddingDate'];
    bool open = true;
    bool busy = false;
    String err = '';
    final ok = await _lzSheet<bool>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) {
          void up(VoidCallback f) {
            if (open) setD(f);
          }

          Future<void> send() async {
            up(() {
              busy = true;
              err = '';
            });
            try {
              final Map<String, dynamic>? refBy = _pendingReferral != null &&
                      _pendingReferral!['vendorId'] == placeId
                  ? <String, dynamic>{
                      'vendorId': _pendingReferral!['fromVendorId'],
                      'name': _pendingReferral!['fromVendorName']
                    }
                  : null;
              _pendingReferral = null;
              await FirebaseFirestore.instance.collection('inquiries').add({
                'coupleUid': _cid,
                'vendorId': placeId,
                'vendorName': vendorName,
                'message': msgC.text.trim(),
                'status': 'new',
                if (refBy != null) 'referredBy': refBy,
                'createdAt': FieldValue.serverTimestamp(),
                'structuredIntent': {
                  'weddingDate': ts is Timestamp
                      ? ts.toDate().toIso8601String().split('T').first
                      : 'Date TBD',
                  'metroId': _browseMetro,
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
                    'status': 'researching',
                    'vendorName': vendorName,
                    'updatedAt': FieldValue.serverTimestamp(),
                  }, SetOptions(merge: true));
                }
              } catch (_) {}
              if (open && ctx2.mounted) Navigator.pop(ctx2, true);
            } catch (_) {
              up(() {
                busy = false;
                err = 'Couldn’t send. Check your connection and try again.';
              });
            }
          }

          return _lzFrame(ctx2,
              icon: Icons.mail_outline_rounded,
              title: 'Contact $vendorName',
              subtitle: 'They reply in your Lazo messages.',
              children: <Widget>[
                const SizedBox(height: 14),
                Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                  _pcA_chip(
                      Icons.event_outlined,
                      ts is Timestamp
                          ? _pcA_date(ts.toDate())
                          : 'Date to be decided'),
                  if (inqCat.isNotEmpty)
                    _pcA_chip(Icons.sell_outlined, _catLabel(inqCat)),
                ]),
                const SizedBox(height: 14),
                TextField(
                  controller: msgC,
                  enabled: !busy,
                  minLines: 3,
                  maxLines: 6,
                  textCapitalization: TextCapitalization.sentences,
                  onChanged: (_) => up(() {}),
                  style: TextStyle(color: _lzFg(ink), fontSize: 14, height: 1.45),
                  decoration: _lightDeco('Your message'),
                ),
                const SizedBox(height: 12),
                _lzNote(Icons.verified_rounded,
                    'Sent as a verified couple with your date attached. Never sold, never shared.'),
                if (err.isNotEmpty) ...<Widget>[
                  const SizedBox(height: 12),
                  _pcA_status(err, false),
                ],
              ],
              footer: _lzActions(
                  secondary: 'Cancel',
                  onSecondary: () => Navigator.pop(ctx2, false),
                  primary: 'Send',
                  icon: Icons.send_rounded,
                  busy: busy,
                  onPrimary: msgC.text.trim().isEmpty ? null : send));
        },
      ),
    );
    open = false;
    if (ok != true) return;
    if (!mounted) return;
    final bool vUnclaimed = ((v['claimedBy'] ?? '') as String? ?? '').isEmpty;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      backgroundColor: _lzBg(ivory),
      duration: Duration(seconds: vUnclaimed ? 6 : 4),
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      content: Text(
          vUnclaimed
              ? 'Sent. $vendorName hasn’t joined Lazo yet, so we’re letting them know a couple’s waiting. Their phone and website are on their card meanwhile.'
              : 'Sent to $vendorName.',
          style: TextStyle(color: _lzFg(ink), fontWeight: FontWeight.w600)),
    ));
    _maybeAskPush();
  }

  // "Sat, Jun 13, 2027" without pulling in intl here
  String _pcA_date(DateTime d) {
    const List<String> mo = <String>[
      'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
    ];
    const List<String> wd = <String>['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    return '${wd[d.weekday - 1]}, ${mo[d.month - 1]} ${d.day}, ${d.year}';
  }""")

    # _maybeAskPush
    rep(r"""  Future<void> _maybeAskPush({bool force = false}) async {
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
    // Let the "Sent" confirmation land and be read before anything else
    // appears on top of it.
    await Future<void>.delayed(const Duration(milliseconds: 1400));
    if (!mounted) return;
    final bool? yes = await _lzSheet<bool>(
      context: context,
      backgroundColor: _lzBg(ivory),
      isScrollControlled: true,
      constraints: const BoxConstraints(maxWidth: 560),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (BuildContext ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(22, 20, 22, 22),
          child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(children: <Widget>[
                  Container(
                    width: 38,
                    height: 38,
                    decoration: BoxDecoration(
                        color: plumDeep,
                        borderRadius: BorderRadius.circular(12)),
                    child: const Icon(Icons.notifications_active_rounded,
                        color: gold, size: 19),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                      child: Text('Want a heads up when they write back?',
                          style: _serif(size: 23))),
                ]),
                const SizedBox(height: 10),
                 Text(
                    'Most vendors reply within a day or two. We\u2019ll let you know when one does - and for nothing else. No marketing, no reminders, no nudging you about your florist.',
                    style: TextStyle(fontSize: 13, color: _lzFg(muted), height: 1.45)),
                const SizedBox(height: 16),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    style: FilledButton.styleFrom(
                        backgroundColor: gold,
                        foregroundColor: plumDeep,
                        elevation: 0,
                        padding: const EdgeInsets.symmetric(vertical: 13)),
                    onPressed: _h(() => Navigator.pop(ctx, true)),
                    child: const Text('Yes, let me know',
                        style: TextStyle(fontWeight: FontWeight.w800)),
                  ),
                ),
                const SizedBox(height: 4),
                Center(
                  child: TextButton(
                    onPressed: _h(() => Navigator.pop(ctx, false)),
                    child:  Text('Not now',
                        style: TextStyle(
                            color: _lzFg(muted), fontWeight: FontWeight.w700)),
                  ),
                ),
              ]),
        ),
      ),
    );
    if (yes != true) {
      await _stampPushAsk('no');
      return;
    }
    final bool ok = await _registerPush();
    // 'blocked' means they said yes to us and the OS said no - asking again
    // can't help, only a trip to system settings can.
    await _stampPushAsk(ok ? 'yes' : 'blocked');
    if (ok) _toast('Done - we\u2019ll let you know.');
  }""",
        r"""  Future<void> _maybeAskPush({bool force = false}) async {
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
    // Let the "Sent" confirmation land and be read before anything else
    // appears on top of it.
    await Future<void>.delayed(const Duration(milliseconds: 1400));
    if (!mounted) return;
    final bool? yes = await _lzSheet<bool>(
      context: context,
      backgroundColor: _lzBg(ivory),
      isScrollControlled: true,
      constraints: const BoxConstraints(maxWidth: 520),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (BuildContext ctx) => _lzFrame(ctx,
          icon: Icons.notifications_active_rounded,
          title: 'A heads up when they write back?',
          subtitle: 'Most vendors reply within a day or two.',
          children: <Widget>[
            const SizedBox(height: 14),
            for (final List<dynamic> r in <List<dynamic>>[
              <dynamic>[Icons.mark_chat_unread_outlined, 'When a vendor replies', true],
              <dynamic>[Icons.campaign_outlined, 'Marketing', false],
              <dynamic>[Icons.alarm_off_rounded, 'Reminders or nudges', false],
            ])
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Row(children: <Widget>[
                  Icon(r[0] as IconData, size: 19, color: _lzFg(plum)),
                  const SizedBox(width: 12),
                  Expanded(
                      child: Text(r[1] as String,
                          style: TextStyle(fontSize: 14.5, color: _lzFg(ink)))),
                  Icon(
                      (r[2] as bool) ? Icons.check_circle_rounded : Icons.block_rounded,
                      size: 19,
                      color: (r[2] as bool) ? vGreen : _lzFg(muted)),
                ]),
              ),
          ],
          footer: _lzActions(
              secondary: 'Not now',
              onSecondary: () => Navigator.pop(ctx, false),
              primary: 'Yes, let me know',
              icon: Icons.notifications_active_rounded,
              onPrimary: () => Navigator.pop(ctx, true))),
    );
    if (yes != true) {
      await _stampPushAsk('no');
      return;
    }
    final bool ok = await _registerPush();
    // 'blocked' means they said yes to us and the OS said no - asking again
    // can't help, only a trip to system settings can.
    await _stampPushAsk(ok ? 'yes' : 'blocked');
    if (ok) _toast('Done - we’ll let you know.');
  }""")

    # _addRegistryLink
    rep(r"""  Future<void> _addRegistryLink(List<Map<String, dynamic>> current,
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
    String error = '';
    final bool? ok = await _lzDialog<bool>(
      context: context,
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) => AlertDialog(
          backgroundColor: _lzBg(ivory),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: Text('Add a registry', style: _serif(size: 24)),
          content: SizedBox(
            width: 440,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                 Text(
                    'Paste the link guests would use. Any store, any fund - we recognize the big ones.',
                    style:
                        TextStyle(fontSize: 12.5, color: _lzFg(muted), height: 1.4)),
                const SizedBox(height: 10),
                Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
                  for (final List<String> p in const <List<String>>[
                    <String>['Zola', 'https://www.zola.com/registry/'],
                    <String>['Amazon', 'https://www.amazon.com/wedding/'],
                    <String>['Target', 'https://www.target.com/gift-registry/'],
                    <String>['Honeymoon fund', 'https://www.honeyfund.com/'],
                    <String>['Venmo', 'https://venmo.com/u/'],
                  ])
                    ActionChip(
                      avatar: _storeMark(p[1], p[0][0], plum, size: 20),
                      label: Text(p[0],
                          style:  TextStyle(
                              fontSize: 12,
                              color: _lzFg(plum),
                              fontWeight: FontWeight.w600)),
                      backgroundColor: _lzBg(Colors.white),
                      side: BorderSide(color: gold.withOpacity(.6)),
                      onPressed: _h(() => setD(() {
                            urlC.text = p[1];
                            labelC.text = p[0] == 'Honeymoon fund'
                                ? 'Honeymoon fund'
                                : p[0];
                            detected = p[0];
                            error = '';
                          })),
                    ),
                ]),
                const SizedBox(height: 12),
                TextField(
                  controller: urlC,
                  keyboardType: TextInputType.url,
                  autofocus: true,
                  style:  TextStyle(color: _lzFg(ink), fontSize: 14.5),
                  onChanged: (String v) {
                    final String u = v.trim().startsWith('http')
                        ? v.trim()
                        : 'https://${v.trim()}';
                    final List<String>? st = _storeFor(u);
                    setD(() {
                      detected = st == null ? '' : st[1];
                      if (st != null && labelC.text.trim().isEmpty)
                        labelC.text = st[1];
                      error = '';
                    });
                  },
                  decoration: _lightDeco('Registry link',
                          hint: 'https://www.zola.com/registry/yournames')
                      .copyWith(
                    suffixIcon: detected.isEmpty
                        ? null
                        : Padding(
                            padding: const EdgeInsets.only(right: 10, top: 14),
                            child: Text(detected,
                                style:  TextStyle(
                                    color: _lzFg(vGreen),
                                    fontSize: 12,
                                    fontWeight: FontWeight.w700)),
                          ),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: labelC,
                  style:  TextStyle(color: _lzFg(ink), fontSize: 14.5),
                  decoration: _lightDeco('Shown to guests as (optional)',
                      hint: 'Amazon, Our honeymoon fund\u2026'),
                ),
                if (error.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Text(error,
                        style:  TextStyle(
                            color: _lzFg(Color(0xFFB04343)), fontSize: 12.5)),
                  ),
              ],
            ),
          ),
          actions: <Widget>[
            TextButton(
                onPressed: _h(() => Navigator.pop(ctx2, false)),
                child:  Text('Cancel', style: TextStyle(color: _lzFg(muted)))),
            FilledButton(
              style: FilledButton.styleFrom(
                  backgroundColor: gold, foregroundColor: plum),
              onPressed: _h(() {
                String url = urlC.text.trim();
                if (url.isEmpty) {
                  setD(() => error = 'Paste the registry link first.');
                  return;
                }
                if (!url.startsWith('http')) url = 'https://$url';
                if (!_urlOk(url)) {
                  setD(() =>
                      error = 'That doesn\u2019t look like a web address.');
                  return;
                }
                if (current.asMap().entries.any((MapEntry<int, Map<String, dynamic>> e) =>
                    e.key != editIndex &&
                    (e.value['url'] ?? '').toString().toLowerCase() ==
                        url.toLowerCase())) {
                  setD(() => error = 'That link is already on your list.');
                  return;
                }
                urlC.text = url;
                Navigator.pop(ctx2, true);
              }),
              child: Text(editIndex >= 0 ? 'Save' : 'Add'),
            ),
          ],
        ),
      ),
    );
    if (ok != true) return;
    final String url = urlC.text.trim();
    final List<String>? st = _storeFor(url);
    final String label = labelC.text.trim().isNotEmpty
        ? labelC.text.trim()
        : (st == null
            ? (Uri.tryParse(url)?.host ?? 'Registry').replaceFirst('www.', '')
            : st[1]);
    final Map<String, dynamic> row = <String, dynamic>{
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
  }""",
        r"""  Future<void> _addRegistryLink(List<Map<String, dynamic>> current,
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
    {
      final String u0 = urlC.text.trim();
      final List<String>? st0 = u0.isEmpty ? null : _storeFor(u0);
      if (st0 != null) detected = st0[1];
    }
    String error = '';
    bool busy = false;
    bool open = true;
    final bool? ok = await _lzSheet<bool>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) {
          void up(VoidCallback f) {
            if (open) setD(f);
          }

          Future<void> save() async {
            String url = urlC.text.trim();
            if (url.isEmpty) {
              up(() => error = 'Paste the registry link first.');
              return;
            }
            if (!url.startsWith('http')) url = 'https://$url';
            if (!_urlOk(url)) {
              up(() => error = 'That doesn’t look like a web address.');
              return;
            }
            if (current.asMap().entries.any((MapEntry<int, Map<String, dynamic>> e) =>
                e.key != editIndex &&
                (e.value['url'] ?? '').toString().toLowerCase() ==
                    url.toLowerCase())) {
              up(() => error = 'That link is already on your list.');
              return;
            }
            urlC.text = url;
            final List<String>? st = _storeFor(url);
            final String label = labelC.text.trim().isNotEmpty
                ? labelC.text.trim()
                : (st == null
                    ? (Uri.tryParse(url)?.host ?? 'Registry').replaceFirst('www.', '')
                    : st[1]);
            final Map<String, dynamic> row = <String, dynamic>{
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
            up(() {
              busy = true;
              error = '';
            });
            try {
              await _saveRegistry(next);
              if (open && ctx2.mounted) Navigator.pop(ctx2, true);
            } catch (_) {
              up(() {
                busy = false;
                error = 'Couldn’t save. Check your connection and try again.';
              });
            }
          }

          return _lzFrame(ctx2,
              icon: Icons.card_giftcard_rounded,
              title: editIndex >= 0 ? 'Edit registry' : 'Add a registry',
              subtitle: 'Paste the link guests would use. Any store, any fund.',
              children: <Widget>[
                _lzSection('Start from a store'),
                Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                  for (final List<String> p in const <List<String>>[
                    <String>['Zola', 'https://www.zola.com/registry/'],
                    <String>['Amazon', 'https://www.amazon.com/wedding/'],
                    <String>['Target', 'https://www.target.com/gift-registry/'],
                    <String>['Honeymoon fund', 'https://www.honeyfund.com/'],
                    <String>['Venmo', 'https://venmo.com/u/'],
                  ])
                    _Press(
                      scale: .97,
                      onTap: busy
                          ? null
                          : () => up(() {
                                urlC.text = p[1];
                                labelC.text = p[0];
                                detected = p[0];
                                error = '';
                              }),
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 180),
                        padding: const EdgeInsets.fromLTRB(6, 6, 13, 6),
                        decoration: BoxDecoration(
                            color: detected == p[0] ? plumDeep : _lzBg(cardBg),
                            borderRadius: BorderRadius.circular(30),
                            border: Border.all(
                                color: detected == p[0] ? plumDeep : _lzLine(goldLine))),
                        child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
                          _storeMark(p[1], p[0][0], plum, size: 22),
                          const SizedBox(width: 7),
                          Text(p[0],
                              style: TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w700,
                                  color: detected == p[0] ? gold : _lzFg(plum))),
                        ]),
                      ),
                    ),
                ]),
                const SizedBox(height: 16),
                TextField(
                  controller: urlC,
                  keyboardType: TextInputType.url,
                  autofocus: urlC.text.isEmpty,
                  autocorrect: false,
                  enabled: !busy,
                  textInputAction: TextInputAction.next,
                  style: TextStyle(color: _lzFg(ink), fontSize: 14.5),
                  onChanged: (String v) {
                    final String u = v.trim().startsWith('http')
                        ? v.trim()
                        : 'https://${v.trim()}';
                    final List<String>? st = _storeFor(u);
                    up(() {
                      detected = st == null ? '' : st[1];
                      if (st != null && labelC.text.trim().isEmpty)
                        labelC.text = st[1];
                      error = '';
                    });
                  },
                  decoration: _lightDeco('Registry link',
                          hint: 'https://www.zola.com/registry/yournames')
                      .copyWith(
                    suffixIcon: detected.isEmpty
                        ? null
                        : Padding(
                            padding: const EdgeInsets.only(right: 10, top: 14),
                            child: Text(detected,
                                style: TextStyle(
                                    color: _lzFg(vGreen),
                                    fontSize: 12,
                                    fontWeight: FontWeight.w700)),
                          ),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: labelC,
                  enabled: !busy,
                  textCapitalization: TextCapitalization.sentences,
                  textInputAction: TextInputAction.done,
                  onSubmitted: (_) {
                    if (!busy) save();
                  },
                  style: TextStyle(color: _lzFg(ink), fontSize: 14.5),
                  decoration: _lightDeco('Shown to guests as (optional)',
                      hint: 'Amazon, Our honeymoon fund…'),
                ),
                if (error.isNotEmpty) ...<Widget>[
                  const SizedBox(height: 12),
                  _pcA_status(error, false),
                ],
              ],
              footer: _lzActions(
                  secondary: 'Cancel',
                  onSecondary: () => Navigator.pop(ctx2, false),
                  primary: editIndex >= 0 ? 'Save' : 'Add registry',
                  icon: editIndex >= 0 ? Icons.check_rounded : Icons.add_rounded,
                  busy: busy,
                  onPrimary: urlC.text.trim().isEmpty ? null : save));
        },
      ),
    );
    open = false;
    if (ok != true) return;
    _toast(editIndex >= 0
        ? 'Saved. Your website shows it now.'
        : 'Added. Your website shows it now.');
  }""")

    # _editRegistryNote
    rep(r"""  Future<void> _editRegistryNote(
      Map<String, dynamic> couple, List<Map<String, dynamic>> links) async {
    final TextEditingController c =
        TextEditingController(text: (couple['registryNote'] ?? '').toString());
    final bool? ok = await _lzDialog<bool>(
      context: context,
      builder: (BuildContext ctx) => AlertDialog(
        backgroundColor: _lzBg(ivory),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Text('A note to guests', style: _serif(size: 24)),
        content: SizedBox(
          width: 440,
          child: TextField(
            controller: c,
            minLines: 2,
            maxLines: 5,
            autofocus: true,
            style:  TextStyle(color: _lzFg(ink), fontSize: 14.5),
            decoration: _lightDeco('',
                hint:
                    'Your presence is the gift. If you\u2019d like to give something, these are the places we\u2019d love\u2026'),
          ),
        ),
        actions: <Widget>[
          TextButton(
              onPressed: _h(() => Navigator.pop(ctx, false)),
              child:  Text('Cancel', style: TextStyle(color: _lzFg(muted)))),
          FilledButton(
              style: FilledButton.styleFrom(
                  backgroundColor: gold, foregroundColor: plum),
              onPressed: _h(() => Navigator.pop(ctx, true)),
              child: const Text('Save')),
        ],
      ),
    );
    if (ok != true) return;
    await _saveRegistry(links, note: c.text.trim());
  }""",
        r"""  Future<void> _editRegistryNote(
      Map<String, dynamic> couple, List<Map<String, dynamic>> links) async {
    final TextEditingController c =
        TextEditingController(text: (couple['registryNote'] ?? '').toString());
    bool open = true;
    bool busy = false;
    String err = '';
    final bool? ok = await _lzSheet<bool>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 540),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) {
          void up(VoidCallback f) {
            if (open) setD(f);
          }

          Future<void> save() async {
            up(() {
              busy = true;
              err = '';
            });
            try {
              await _saveRegistry(links, note: c.text.trim());
              if (open && ctx2.mounted) Navigator.pop(ctx2, true);
            } catch (_) {
              up(() {
                busy = false;
                err = 'Couldn’t save. Check your connection and try again.';
              });
            }
          }

          return _lzFrame(ctx2,
              icon: Icons.edit_note_rounded,
              title: 'A note to guests',
              subtitle: 'It sits above your registries on your website.',
              children: <Widget>[
                const SizedBox(height: 14),
                TextField(
                  controller: c,
                  minLines: 3,
                  maxLines: 6,
                  autofocus: true,
                  enabled: !busy,
                  textCapitalization: TextCapitalization.sentences,
                  style: TextStyle(color: _lzFg(ink), fontSize: 14.5, height: 1.45),
                  decoration: _lightDeco('',
                      hint:
                          'Your presence is the gift. If you’d like to give something, these are the places we’d love…'),
                ),
                if (err.isNotEmpty) ...<Widget>[
                  const SizedBox(height: 12),
                  _pcA_status(err, false),
                ],
              ],
              footer: _lzActions(
                  secondary: 'Cancel',
                  onSecondary: () => Navigator.pop(ctx2, false),
                  primary: 'Save note',
                  icon: Icons.check_rounded,
                  busy: busy,
                  onPrimary: save));
        },
      ),
    );
    open = false;
    if (ok == true) _toast('Saved. Your website shows it now.');
  }""")

    # _editDisplayName
    rep(r"""  Future<void> _editDisplayName() async {
    final u = FirebaseAuth.instance.currentUser;
    if (u == null) return;
    final c = TextEditingController(text: u.displayName ?? '');
    final ok = await _lzDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: _lzBg(ivory),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title:  Text('Your name',
            style: TextStyle(color: _lzFg(plum), fontWeight: FontWeight.w700)),
        content: TextField(
          controller: c,
          autofocus: true,
          style:  TextStyle(color: _lzFg(ink), fontSize: 14),
          decoration: _lightDeco('Display name'),
        ),
        actions: [
          TextButton(
              onPressed: _h(() => Navigator.pop(ctx, false)),
              child:  Text('Cancel', style: TextStyle(color: _lzFg(ink)))),
          FilledButton(
            style: FilledButton.styleFrom(
                backgroundColor: gold, foregroundColor: plum),
            onPressed: _h(() => Navigator.pop(ctx, true)),
            child: const Text('Save'),
          ),
        ],
      ),
    );
    if (ok != true || c.text.trim().isEmpty) return;
    await u.updateDisplayName(c.text.trim());
    await FirebaseFirestore.instance
        .collection('users')
        .doc(u.uid)
        .set({'display_name': c.text.trim()}, SetOptions(merge: true));
    if (mounted) setState(() {});
  }""",
        r"""  Future<void> _editDisplayName() async {
    final u = FirebaseAuth.instance.currentUser;
    if (u == null) return;
    final c = TextEditingController(text: u.displayName ?? '');
    final ok = await _lzSheet<bool>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 460),
      builder: (ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) {
          final bool valid = c.text.trim().isNotEmpty;
          return _lzFrame(ctx2,
              icon: Icons.badge_outlined,
              title: 'Your name',
              subtitle: 'How vendors and your partner see you on Lazo.',
              children: <Widget>[
                const SizedBox(height: 14),
                TextField(
                  controller: c,
                  autofocus: true,
                  textCapitalization: TextCapitalization.words,
                  textInputAction: TextInputAction.done,
                  onChanged: (_) => setD(() {}),
                  onSubmitted: (_) {
                    if (valid) Navigator.pop(ctx2, true);
                  },
                  style: TextStyle(color: _lzFg(ink), fontSize: 14),
                  decoration: _lightDeco('Display name'),
                ),
              ],
              footer: _lzActions(
                  secondary: 'Cancel',
                  onSecondary: () => Navigator.pop(ctx2, false),
                  primary: 'Save',
                  icon: Icons.check_rounded,
                  onPrimary: valid ? () => Navigator.pop(ctx2, true) : null));
        },
      ),
    );
    if (ok != true || c.text.trim().isEmpty) return;
    await u.updateDisplayName(c.text.trim());
    await FirebaseFirestore.instance
        .collection('users')
        .doc(u.uid)
        .set({'display_name': c.text.trim()}, SetOptions(merge: true));
    if (mounted) setState(() {});
  }""")

    # _addKeyDate
    rep(r"""  Future<void> _addKeyDate(Map<String, dynamic> couple) async {
    final TextEditingController c = TextEditingController();
    DateTime? picked;
    String? chosen;
    final bool? ok = await _lzDialog<bool>(
      context: context,
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx, StateSetter setD) => AlertDialog(
          backgroundColor: _lzBg(cardBg),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: Text('Add a date', style: _serif(size: 26)),
          content: SizedBox(
            width: 420,
            child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: kKeyDateIdeas
                        .map((String i) => ActionChip(
                              label: Text(i,
                                  style: TextStyle(
                                      fontSize: 12,
                                      color: _lzFg(chosen == i ? plumDeep : ivory),
                                      fontWeight: FontWeight.w800)),
                              backgroundColor: _lzBg(chosen == i ? gold : plum),
                              surfaceTintColor: Colors.transparent,
                              elevation: 0,
                              side: BorderSide(
                                  color:
                                      _lzLine(gold.withOpacity(chosen == i ? 1 : .6))),
                              onPressed: _h(() => setD(() {
                                    chosen = i;
                                    c.text = i;
                                  })),
                            ))
                        .toList(),
                  ),
                  const SizedBox(height: 10),
                  TextField(
                    controller: c,
                    style:  TextStyle(color: _lzFg(ink)),
                    onChanged: (_) => setD(() => chosen = null),
                    decoration: _lightDeco('What is it?',
                        hint: 'Engagement session at the lake'),
                  ),
                  const SizedBox(height: 10),
                  OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(
                        foregroundColor: _lzFg(plum),
                        side:  BorderSide(color: _lzLine(goldLine))),
                    onPressed: _h(() async {
                      final DateTime now = DateTime.now();
                      final DateTime? d = await showDatePicker(
                        context: ctx,
                        initialDate: picked ?? now,
                        firstDate: DateTime(now.year - 1),
                        lastDate: DateTime(now.year + 3),
                      );
                      if (d != null) setD(() => picked = d);
                    }),
                    icon: const Icon(Icons.event_rounded, size: 16),
                    label: Text(
                        picked == null ? 'Pick the day' : _longDate(picked!),
                        style: const TextStyle(fontWeight: FontWeight.w700)),
                  ),
                ]),
          ),
          actions: <Widget>[
            TextButton(
                onPressed: _h(() => Navigator.of(ctx).pop(false)),
                child:  Text('Cancel', style: TextStyle(color: _lzFg(muted)))),
            FilledButton(
                style: FilledButton.styleFrom(
                    backgroundColor: plum, foregroundColor: ivory),
                onPressed: _h((c.text.trim().isEmpty || picked == null)
                    ? null
                    : () => Navigator.of(ctx).pop(true)),
                child: const Text('Add')),
          ],
        ),
      ),
    );
    if (ok != true || picked == null) return;
    final List<Map<String, dynamic>> list = _keyDates(couple)
      ..add(<String, dynamic>{
        'label': c.text.trim(),
        'date': Timestamp.fromDate(
            DateTime(picked!.year, picked!.month, picked!.day, 12))
      });
    try {
      await _coupleRef
          .set(<String, dynamic>{'keyDates': list}, SetOptions(merge: true));
      setState(() => _wxSel = _ymd(picked!));
    } catch (e) {
      _toast('Could not save that date: $e');
    }
  }""",
        r"""  Future<void> _addKeyDate(Map<String, dynamic> couple) async {
    final TextEditingController c = TextEditingController();
    DateTime? picked;
    String? chosen;
    bool open = true;
    bool busy = false;
    String err = '';
    final bool? ok = await _lzSheet<bool>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 540),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx, StateSetter setD) {
          void up(VoidCallback f) {
            if (open) setD(f);
          }

          final bool valid = c.text.trim().isNotEmpty && picked != null;

          Future<void> save() async {
            final DateTime p = picked!;
            final List<Map<String, dynamic>> list = _keyDates(couple)
              ..add(<String, dynamic>{
                'label': c.text.trim(),
                'date': Timestamp.fromDate(DateTime(p.year, p.month, p.day, 12))
              });
            up(() {
              busy = true;
              err = '';
            });
            try {
              await _coupleRef
                  .set(<String, dynamic>{'keyDates': list}, SetOptions(merge: true));
              if (open && ctx.mounted) Navigator.of(ctx).pop(true);
            } catch (e) {
              up(() {
                busy = false;
                err = 'Couldn’t save that date. Check your connection and try again.';
              });
            }
          }

          Future<void> pickDay() async {
            final DateTime now = DateTime.now();
            final DateTime? d = await showDatePicker(
              context: ctx,
              initialDate: picked ?? now,
              firstDate: DateTime(now.year - 1),
              lastDate: DateTime(now.year + 3),
            );
            if (d != null) up(() => picked = d);
          }

          return _lzFrame(ctx,
              icon: Icons.event_available_rounded,
              title: 'Add a date',
              subtitle: 'Shoots, tastings, fittings - the days around the big one.',
              children: <Widget>[
                _lzSection('Ideas'),
                Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                  for (final String i in kKeyDateIdeas)
                    _Press(
                      scale: .97,
                      onTap: busy
                          ? null
                          : () => up(() {
                                chosen = i;
                                c.text = i;
                              }),
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 180),
                        padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 8),
                        decoration: BoxDecoration(
                            color: chosen == i ? plumDeep : _lzBg(cardBg),
                            borderRadius: BorderRadius.circular(30),
                            border: Border.all(
                                color: chosen == i ? plumDeep : _lzLine(goldLine))),
                        child: Text(i,
                            style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w700,
                                color: chosen == i ? gold : _lzFg(plum))),
                      ),
                    ),
                ]),
                const SizedBox(height: 16),
                TextField(
                  controller: c,
                  enabled: !busy,
                  textCapitalization: TextCapitalization.sentences,
                  style: TextStyle(color: _lzFg(ink), fontSize: 14),
                  onChanged: (_) => up(() => chosen = null),
                  decoration: _lightDeco('What is it?',
                      hint: 'Engagement session at the lake'),
                ),
                const SizedBox(height: 12),
                _pcA_pick(
                    Icons.event_rounded,
                    picked == null ? 'Pick the day' : _longDate(picked!),
                    picked == null ? 'Tap to open the calendar' : 'Tap to change it',
                    picked != null,
                    busy ? null : pickDay),
                if (err.isNotEmpty) ...<Widget>[
                  const SizedBox(height: 12),
                  _pcA_status(err, false),
                ],
              ],
              footer: _lzActions(
                  secondary: 'Cancel',
                  onSecondary: () => Navigator.of(ctx).pop(false),
                  primary: c.text.trim().isEmpty
                      ? 'Name the date'
                      : (picked == null ? 'Pick the day' : 'Add date'),
                  icon: Icons.add_rounded,
                  busy: busy,
                  onPrimary: valid ? save : null));
        },
      ),
    );
    open = false;
    if (ok != true || picked == null) return;
    if (mounted) setState(() => _wxSel = _ymd(picked!));
  }""")

    # _deskSheet
    rep(r"""  Future<void> _deskSheet() async {
    // [label, icon, what it does, which screen it lands on]
    // The fourth entry is what lets a tile know it is the screen you are
    // already on. Seating and Music leave the dashboard for their own pages,
    // so they have no view to match and never light up.
    final List<List<dynamic>> items = <List<dynamic>>[
      <dynamic>[
        'Home',
        Icons.home_rounded,
        () => setState(() => _view = _View.hub),
        _View.hub
      ],
      <dynamic>[
        'Vendor team',
        Icons.checklist_rounded,
        () => setState(() => _view = _View.vendors),
        _View.vendors
      ],
      <dynamic>[
        'Browse',
        Icons.storefront_rounded,
        () => setState(() => _view = _View.browse),
        _View.browse
      ],
      <dynamic>[
        'Messages',
        Icons.chat_bubble_rounded,
        () => setState(() => _view = _View.messages),
        _View.messages
      ],
      <dynamic>[
        'June',
        Icons.auto_awesome_rounded,
        () => setState(() => _view = _View.june),
        _View.june
      ],
      <dynamic>[
        'Day-of',
        Icons.event_rounded,
        () => setState(() => _view = _View.dayof),
        _View.dayof
      ],
      <dynamic>[
        'Guests',
        Icons.group_rounded,
        () => setState(() => _view = _View.guests),
        _View.guests
      ],
      <dynamic>['Seating', Icons.table_restaurant_rounded, _openSeating, null],
      <dynamic>['Music', Icons.music_note_rounded, _openMusic, null],
      <dynamic>[
        'Website',
        Icons.language_rounded,
        () => setState(() => _view = _View.website),
        _View.website
      ],
      <dynamic>[
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
        'Dream board',
        Icons.auto_awesome_mosaic_rounded,
        () => setState(() => _view = _View.board),
        _View.board
      ],
      <dynamic>[
        'Account',
        Icons.person_rounded,
        () => setState(() => _view = _View.account),
        _View.account
      ],
    ];
    // SPATIAL CONSISTENCY. The desk used to slide up from the bottom edge with
    // no relationship to the button that summoned it - tap a circle in the
    // corner, watch a full-width panel arrive from somewhere else. Now it
    // grows out of that corner and shrinks back into it, so the button and
    // the panel read as one object opening rather than two unrelated ones.
    //
    // The curve is critically damped, no overshoot: a tap carries no momentum,
    // and bounce belongs to gestures that were thrown. easeIn on the way out
    // mirrors easeOut on the way in, so the return retraces the path.
    //
    // Reduced motion keeps the plain slide - the vestibular problem is the
    // zoom, not the transition.
    final bool calm = _reducedMotion(context);
    await _lzSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (BuildContext ctx) => SafeArea(
        child: AnimatedBuilder(
          // The route's OWN animation, not one of ours.
          //
          // Supplying a transitionAnimationController here and disposing it
          // after the await crashed the app: showModalBottomSheet's Future
          // completes when the route is popped, which is BEFORE the exit
          // animation has run, so the dispose tore the controller down
          // mid-flight and the next tick threw. Borrowing the route's
          // animation gives the same motion with no lifecycle to get wrong.
          animation: ModalRoute.of(ctx)?.animation ?? kAlwaysCompleteAnimation,
          builder: (BuildContext actx, Widget? panel) {
            if (calm) return panel!;
            final Animation<double> a =
                ModalRoute.of(actx)?.animation ?? kAlwaysCompleteAnimation;
            final double t = (a.status == AnimationStatus.reverse
                    ? Curves.easeInCubic
                    : Curves.easeOutCubic)
                .transform(a.value.clamp(0.0, 1.0));
            return Transform.scale(
              scale: .88 + .12 * t,
              // Roughly where the button sits: hard right, on the floor.
              alignment: const Alignment(.8, 1),
              child: panel,
            );
          },
          child: Container(
            margin: const EdgeInsets.fromLTRB(10, 0, 10, 10),
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
            decoration: BoxDecoration(
              // Lit from above, like everything else here: one flat fill gave
              // the tiles nothing to sit in.
              gradient: const LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: <Color>[Color(0xFF3B1C3D), Color(0xFF291228)],
              ),
              borderRadius: BorderRadius.circular(26),
              border: Border.all(color: gold.withOpacity(.6)),
              boxShadow: <BoxShadow>[
                // A bigger surface reads as a thicker one: wider, softer, and
                // sitting further off the page than the button that opened it.
                BoxShadow(
                    color: Colors.black.withOpacity(.38),
                    blurRadius: 40,
                    spreadRadius: -4,
                    offset: const Offset(0, 18)),
                BoxShadow(
                    color: Colors.black.withOpacity(.26),
                    blurRadius: 10,
                    offset: const Offset(0, 3)),
              ],
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                Container(
                    width: 44,
                    height: 4,
                    margin: const EdgeInsets.only(bottom: 12),
                    decoration: BoxDecoration(
                        color: gold.withOpacity(.45),
                        borderRadius: BorderRadius.circular(99))),
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Text('YOUR PLANNING DESK',
                      style: TextStyle(
                          color: gold.withOpacity(.9),
                          fontSize: 10.5,
                          letterSpacing: 2.2,
                          fontWeight: FontWeight.w700)),
                ),
                GridView.count(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  crossAxisCount: 4,
                  mainAxisSpacing: 10,
                  crossAxisSpacing: 10,
                  childAspectRatio: .92,
                  children: <Widget>[
                    for (final List<dynamic> it in items)
                      _deskSheetTile(ctx, it),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }""",
        r"""  Future<void> _deskSheet() async {
    // [label, icon, what it does, which screen it lands on]
    // The fourth entry is what lets a tile know it is the screen you are
    // already on. Seating and Music leave the dashboard for their own pages,
    // so they have no view to match and never light up.
    final List<List<dynamic>> items = <List<dynamic>>[
      <dynamic>[
        'Home',
        Icons.home_rounded,
        () => setState(() => _view = _View.hub),
        _View.hub
      ],
      <dynamic>[
        'Vendor team',
        Icons.checklist_rounded,
        () => setState(() => _view = _View.vendors),
        _View.vendors
      ],
      <dynamic>[
        'Browse',
        Icons.storefront_rounded,
        () => setState(() => _view = _View.browse),
        _View.browse
      ],
      <dynamic>[
        'Messages',
        Icons.chat_bubble_rounded,
        () => setState(() => _view = _View.messages),
        _View.messages
      ],
      <dynamic>[
        'June',
        Icons.auto_awesome_rounded,
        () => setState(() => _view = _View.june),
        _View.june
      ],
      <dynamic>[
        'Day-of',
        Icons.event_rounded,
        () => setState(() => _view = _View.dayof),
        _View.dayof
      ],
      <dynamic>[
        'Guests',
        Icons.group_rounded,
        () => setState(() => _view = _View.guests),
        _View.guests
      ],
      <dynamic>['Seating', Icons.table_restaurant_rounded, _openSeating, null],
      <dynamic>['Music', Icons.music_note_rounded, _openMusic, null],
      <dynamic>[
        'Website',
        Icons.language_rounded,
        () => setState(() => _view = _View.website),
        _View.website
      ],
      <dynamic>[
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
        'Dream board',
        Icons.auto_awesome_mosaic_rounded,
        () => setState(() => _view = _View.board),
        _View.board
      ],
      <dynamic>[
        'Account',
        Icons.person_rounded,
        () => setState(() => _view = _View.account),
        _View.account
      ],
    ];
    // SPATIAL CONSISTENCY. The desk used to slide up from the bottom edge with
    // no relationship to the button that summoned it - tap a circle in the
    // corner, watch a full-width panel arrive from somewhere else. Now it
    // grows out of that corner and shrinks back into it, so the button and
    // the panel read as one object opening rather than two unrelated ones.
    //
    // The curve is critically damped, no overshoot: a tap carries no momentum,
    // and bounce belongs to gestures that were thrown. easeIn on the way out
    // mirrors easeOut on the way in, so the return retraces the path.
    //
    // Reduced motion keeps the plain slide - the vestibular problem is the
    // zoom, not the transition.
    final bool calm = _reducedMotion(context);
    await _lzSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (BuildContext ctx) => SafeArea(
        child: AnimatedBuilder(
          // The route's OWN animation, not one of ours.
          //
          // Supplying a transitionAnimationController here and disposing it
          // after the await crashed the app: showModalBottomSheet's Future
          // completes when the route is popped, which is BEFORE the exit
          // animation has run, so the dispose tore the controller down
          // mid-flight and the next tick threw. Borrowing the route's
          // animation gives the same motion with no lifecycle to get wrong.
          animation: ModalRoute.of(ctx)?.animation ?? kAlwaysCompleteAnimation,
          builder: (BuildContext actx, Widget? panel) {
            if (calm) return panel!;
            final Animation<double> a =
                ModalRoute.of(actx)?.animation ?? kAlwaysCompleteAnimation;
            final double t = (a.status == AnimationStatus.reverse
                    ? Curves.easeInCubic
                    : Curves.easeOutCubic)
                .transform(a.value.clamp(0.0, 1.0));
            return Transform.scale(
              scale: .88 + .12 * t,
              // Roughly where the button sits: hard right, on the floor.
              alignment: const Alignment(.8, 1),
              child: panel,
            );
          },
          child: Container(
            margin: const EdgeInsets.fromLTRB(10, 0, 10, 10),
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
            decoration: BoxDecoration(
              // Lit from above, like everything else here: one flat fill gave
              // the tiles nothing to sit in.
              gradient: const LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: <Color>[Color(0xFF3B1C3D), Color(0xFF291228)],
              ),
              borderRadius: BorderRadius.circular(26),
              border: Border.all(color: gold.withOpacity(.6)),
              boxShadow: <BoxShadow>[
                // A bigger surface reads as a thicker one: wider, softer, and
                // sitting further off the page than the button that opened it.
                BoxShadow(
                    color: Colors.black.withOpacity(.38),
                    blurRadius: 40,
                    spreadRadius: -4,
                    offset: const Offset(0, 18)),
                BoxShadow(
                    color: Colors.black.withOpacity(.26),
                    blurRadius: 10,
                    offset: const Offset(0, 3)),
              ],
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                // the clear sheet gets no handle from _lzSheet, so the desk
                // keeps its own - on phones only, where it can be swiped away
                if (MediaQuery.of(ctx).size.width < _lzWideAt)
                Container(
                    width: 44,
                    height: 4,
                    margin: const EdgeInsets.only(bottom: 12),
                    decoration: BoxDecoration(
                        color: gold.withOpacity(.45),
                        borderRadius: BorderRadius.circular(99))),
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Text('YOUR PLANNING DESK',
                      style: TextStyle(
                          color: gold.withOpacity(.9),
                          fontSize: 10.5,
                          letterSpacing: 2.2,
                          fontWeight: FontWeight.w700)),
                ),
                GridView.count(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  crossAxisCount: 4,
                  mainAxisSpacing: 10,
                  crossAxisSpacing: 10,
                  childAspectRatio: .92,
                  children: <Widget>[
                    for (final List<dynamic> it in items)
                      _deskSheetTile(ctx, it),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }""")

    return s
