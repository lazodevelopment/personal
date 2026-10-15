# Popup pass (JC-LAZO-POPUP-1014), part cB - couple dashboard.
# Functions: _crStrip, _cFeedSheet, _crSheet, _deskTiles (left as is), _sendToVendors,
# _editDetails, _timelineBuilderSheet, _deleteAccount, _editWantedSheet, _budgetSheet,
# _setupSheet, _partnerSheet, _openSupportSheet, _accountScreen, _refineSheet,
# _vendorSheet, _editWebsite.


def apply(s: str) -> str:
    def rep(old, new):
        nonlocal s
        assert s.count(old) == 1, (s.count(old), old[:80])
        s = s.replace(old, new)

    def span(start, end, new):
        # Replace everything from `start` (inclusive) up to `end` (exclusive).
        nonlocal s
        assert s.count(start) == 1, ('start', s.count(start), start[:80])
        assert s.count(end) == 1, ('end', s.count(end), end[:80])
        i = s.index(start)
        j = s.index(end)
        assert j > i, ('order', start[:60], end[:60])
        s = s[:i] + new + s[j:]

    for start, end, new in BLOCKS:
        span(start, end, new)
    for old, new in REPS:
        rep(old, new)
    return s


BLOCKS = []
REPS = []

# ---------------------------------------------------------------- _crStrip
BLOCKS.append((
r"""    void open(String? id) {
      _lzSheet<void>(""",
r"""    const Map<String, IconData> icons = <String, IconData>{
      'weather': Icons.wb_sunny_rounded,""",
r"""    void open(String? id) {
      if (id == null) {
        _lzSheet<void>(
          context: context,
          constraints: const BoxConstraints(maxWidth: 720),
          builder: (BuildContext c) => ConstrainedBox(
            constraints: BoxConstraints(maxHeight: MediaQuery.of(c).size.height * .88),
            child: _lzFrame(c,
                icon: Icons.dashboard_customize_rounded,
                title: 'Your widgets',
                subtitle: 'Press and hold a widget to move it.',
                bodyPadding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
                children: <Widget>[_crStack(couple, plan, inqs, wed, daysOut)]),
          ),
        );
        return;
      }
      // One widget opens on its own card, which already carries its title.
      _lzSheet<void>(
        context: context,
        constraints: const BoxConstraints(maxWidth: 640),
        builder: (BuildContext c) => SafeArea(
          top: false,
          child: ConstrainedBox(
            constraints: BoxConstraints(maxHeight: MediaQuery.of(c).size.height * .88),
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(16, 10, 16, 16),
              child: _crBody(id, couple, plan, inqs, wed, daysOut),
            ),
          ),
        ),
      );
    }

"""))

# ---------------------------------------------------------------- _cFeedSheet
BLOCKS.append((
r"""    _lzSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: _lzBg(ivory),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (BuildContext c) => SafeArea(
        child: ConstrainedBox(
          constraints: BoxConstraints(maxHeight: MediaQuery.of(c).size.height * .8),""",
r"""  Widget _crCard(String title, IconData icon, Widget content, {String? sub}) =>""",
r"""    _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext c) => ConstrainedBox(
        constraints: BoxConstraints(maxHeight: MediaQuery.of(c).size.height * .8),
        child: StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
          stream: _cFeedStream(),
          initialData: _liveQ['feed:$_uid']?.latest,
          builder: (BuildContext c2, AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> s) {
            final List<QueryDocumentSnapshot<Map<String, dynamic>>> ds = s.data?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[];
            Widget item(Map<String, dynamic> m) {
              final String thread = (m['thread'] ?? '').toString();
              final String openTo = (m['open'] ?? '').toString();
              final bool fresh = m['readAt'] == null && m['read'] != true;
              return ListTile(
                contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                leading: Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(shape: BoxShape.circle, color: gold.withOpacity(.16), border: Border.all(color: gold.withOpacity(.5))),
                  child: Icon(_cFeedIcon((m['kind'] ?? '').toString()), size: 18, color: gold),
                ),
                title: Text((m['text'] ?? '').toString(), maxLines: 3, overflow: TextOverflow.ellipsis, style: TextStyle(color: _lzFg(ink), fontSize: 13.5, height: 1.35, fontWeight: fresh ? FontWeight.w700 : FontWeight.w500)),
                trailing: Text(ago(m['at']), style: TextStyle(color: _lzFg(muted), fontSize: 11.5)),
                onTap: () {
                  Navigator.of(c2).pop();
                  if (thread.isNotEmpty) {
                    setState(() => _view = _View.messages);
                    _openCoupleThread(thread, (_cwInq[thread]?['data'] as Map<String, dynamic>?) ?? <String, dynamic>{});
                  } else if (openTo == 'guests') {
                    setState(() => _view = _View.guests);
                  } else if (openTo == 'website') {
                    setState(() => _view = _View.website);
                  } else if (openTo == 'vendors') {
                    setState(() => _view = _View.vendors);
                  } else if (openTo == 'june') {
                    setState(() => _view = _View.june);
                  }
                },
              );
            }

            return _lzFrame(c2,
                icon: Icons.auto_awesome_rounded,
                title: 'From June',
                subtitle: n > 0 ? '$n new since you last looked' : 'Vendor replies, contracts, payments and RSVPs',
                bodyPadding: const EdgeInsets.fromLTRB(12, 6, 12, 16),
                children: <Widget>[
                  if (ds.isEmpty)
                    _pcB_empty(Icons.notifications_none_rounded, 'Nothing yet. When a vendor replies or a guest RSVPs, it lands here and on your phone.')
                  else
                    for (int i = 0; i < ds.length; i++) ...<Widget>[
                      if (i > 0) Divider(height: 1, color: _lzLine(goldLine)),
                      item(ds[i].data()),
                    ],
                ]);
          },
        ),
      ),
    );
  }

  /// cB: empty state inside a popup - an icon, one line, and the way forward.
  Widget _pcB_empty(IconData icon, String text, {String? action, VoidCallback? onAction}) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 22, horizontal: 12),
        child: Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
          Container(
              width: 52,
              height: 52,
              decoration: BoxDecoration(shape: BoxShape.circle, color: gold.withOpacity(.14), border: Border.all(color: gold.withOpacity(.5))),
              child: Icon(icon, color: gold, size: 24)),
          const SizedBox(height: 12),
          Text(text, textAlign: TextAlign.center, style: TextStyle(color: _lzFg(muted), fontSize: 13.5, height: 1.45)),
          if (action != null && onAction != null) ...<Widget>[
            const SizedBox(height: 8),
            TextButton(
                onPressed: _h(onAction),
                child: Text(action, style: TextStyle(color: _lzFg(plum), fontWeight: FontWeight.w700))),
          ],
        ]),
      );

  /// cB: a small pill button for secondary ways out (email, copy, call, ...).
  Widget _pcB_chip(IconData icon, String label, VoidCallback onTap) => _Press(
        tick: _Tick.select,
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 9),
          decoration: BoxDecoration(
              color: _lzBg(Colors.white),
              borderRadius: BorderRadius.circular(999),
              border: Border.all(color: _lzLine(goldLine))),
          child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
            Icon(icon, size: 16, color: _lzFg(plum)),
            const SizedBox(width: 7),
            Text(label, style: TextStyle(color: _lzFg(plum), fontSize: 13, fontWeight: FontWeight.w700)),
          ]),
        ),
      );

"""))

# ---------------------------------------------------------------- _crSheet
BLOCKS.append((
r"""  void _crSheet() {""",
r"""  Widget _crStat(String big, String label) => Expanded(""",
r"""  void _crSheet() {
    _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext c) => StatefulBuilder(builder: (BuildContext c2, StateSetter setS) {
        final List<String> on = _cr.where(_crKnown).toList();
        final List<String> off = _kCrAll.map((List<String> r) => r[0]).where((String id) => !on.contains(id)).toList();
        Widget row(String id, bool enabled, {int? index}) {
          final List<String> r = _crTitle(id);
          return ListTile(
            key: ValueKey<String>('crsheet-$id'),
            contentPadding: const EdgeInsets.symmetric(horizontal: 4),
            leading: index == null ? Icon(Icons.add_circle_outline_rounded, color: _lzFg(muted)) : ReorderableDragStartListener(index: index, child: Icon(Icons.drag_indicator_rounded, color: _lzFg(muted))),
            title: Text(r[1], style: TextStyle(color: _lzFg(plum), fontWeight: FontWeight.w700, fontSize: 14)),
            subtitle: Text(r[2], style: TextStyle(color: _lzFg(muted), fontSize: 12)),
            trailing: Switch(
              value: enabled,
              activeColor: Colors.white,
              activeTrackColor: vGreen,
              onChanged: (bool v) {
                setS(() {});
                setState(() => _cr = v ? <String>[...on, id] : on.where((String x) => x != id).toList());
                _crSave();
              },
            ),
          );
        }

        return ConstrainedBox(
          constraints: BoxConstraints(maxHeight: MediaQuery.of(c2).size.height * .82),
          child: _lzFrame(c2,
              icon: Icons.dashboard_customize_rounded,
              title: 'Choose widgets',
              subtitle: 'Switch them on or off. Drag the handle to reorder.',
              bodyPadding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
              children: <Widget>[
                if (on.isEmpty) _pcB_empty(Icons.widgets_outlined, 'No widgets on yet. Switch one on below.'),
                ReorderableListView(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  buildDefaultDragHandles: false,
                  onReorder: (int from, int to) {
                    if (to > from) to -= 1;
                    final String x = on.removeAt(from);
                    on.insert(to, x);
                    setS(() {});
                    setState(() => _cr = List<String>.from(on));
                    _crSave();
                  },
                  children: <Widget>[for (int i = 0; i < on.length; i++) row(on[i], true, index: i)],
                ),
                if (off.isNotEmpty) ...<Widget>[
                  _lzSection('More widgets'),
                  for (final String id in off) row(id, false),
                ],
              ],
              footer: _lzActions(primary: 'Done', icon: Icons.check_rounded, onPrimary: () => Navigator.of(c2).pop())),
        );
      }),
    );
  }

"""))

# ---------------------------------------------------------------- _sendToVendors
BLOCKS.append((
r"""    final TextEditingController noteC = TextEditingController(text: note);
    bool busy = false;
    await _lzSheet<void>(""",
r"""  // Printable page in a new tab (web). Same trick the seating chart uses.""",
r"""    final TextEditingController noteC = TextEditingController(text: note);
    bool busy = false;
    String err = '';
    Future<void> emailIt() async {
      final Uri u = Uri.parse(
          'mailto:?subject=${Uri.encodeComponent(title)}&body=${Uri.encodeComponent(text)}');
      try {
        await launchUrl(u);
      } catch (_) {
        await Clipboard.setData(ClipboardData(text: text));
        _toast('Copied - paste it into an email.');
      }
    }

    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx, StateSetter setS) {
          Future<void> send() async {
            setS(() {
              busy = true;
              err = '';
            });
            final List<Map<String, dynamic>> sent = <Map<String, dynamic>>[];
            for (final Map<String, dynamic> v in booked) {
              if (!picked.contains(v['id'])) continue;
              final bool ok = await _sendArtifact(
                  v['id'].toString(),
                  fileName,
                  pageFor == null ? page : pageFor(v),
                  noteC.text.trim(),
                  textFor == null ? text : textFor(v),
                  title);
              if (ok) {
                sent.add(<String, dynamic>{
                  'inquiryId': v['id'],
                  'vendorName': v['name'],
                });
              }
            }
            if (sent.isEmpty) {
              if (ctx.mounted) {
                setS(() {
                  busy = false;
                  err = 'That didn\u2019t send. Check your connection and try again.';
                });
              }
              return;
            }
            try {
              await _sendsRef.doc(kind).set(<String, dynamic>{
                'kind': kind,
                'title': title,
                'to': sent,
                'at': FieldValue.serverTimestamp(),
              }, SetOptions(merge: true));
            } catch (_) {}
            if (ctx.mounted) Navigator.of(ctx).pop();
            _toast(
                'Sent to ${sent.map((Map<String, dynamic> e) => e['vendorName']).join(', ')} \u2713 They can reply in your thread.');
          }

          Widget vendorRow(Map<String, dynamic> v) {
            final String id = v['id'].toString();
            final bool on = picked.contains(id);
            final String nm = v['name'].toString();
            final String initials = nm
                .split(' ')
                .where((String w) => w.isNotEmpty)
                .take(2)
                .map((String w) => w[0].toUpperCase())
                .join();
            return _Press(
              tick: _Tick.select,
              onTap: () {
                if (busy) return;
                setS(() {
                  if (on) {
                    picked.remove(id);
                  } else {
                    picked.add(id);
                  }
                });
              },
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 160),
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.fromLTRB(10, 9, 12, 9),
                decoration: BoxDecoration(
                  color: _lzBg(on ? Colors.white : Colors.white.withOpacity(.55)),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: _lzLine(on ? plum : goldLine), width: on ? 1.6 : 1),
                ),
                child: Row(children: <Widget>[
                  Container(
                    width: 36,
                    height: 36,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(color: _lzBg(on ? plum : gold.withOpacity(.25)), shape: BoxShape.circle),
                    child: Text(initials.isEmpty ? '?' : initials,
                        style: TextStyle(color: _lzFg(on ? gold : plum), fontSize: 12.5, fontWeight: FontWeight.w800)),
                  ),
                  const SizedBox(width: 11),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                      Text(nm, style: TextStyle(color: _lzFg(ink), fontSize: 14, fontWeight: FontWeight.w800)),
                      Text(v['label'].toString(), style: TextStyle(fontSize: 11.5, color: _lzFg(muted))),
                    ]),
                  ),
                  Icon(on ? Icons.check_circle_rounded : Icons.radio_button_unchecked_rounded,
                      color: _lzFg(on ? vGreen : muted.withOpacity(.6)), size: 22),
                ]),
              ),
            );
          }

          return _lzFrame(ctx,
              icon: Icons.send_rounded,
              title: 'Send $title',
              subtitle: preview.isNotEmpty
                  ? preview
                  : (booked.isEmpty
                      ? 'Email it, copy it or print it.'
                      : 'It lands in each vendor\u2019s thread on Lazo.'),
              children: <Widget>[
                if (booked.isEmpty) ...<Widget>[
                  const SizedBox(height: 10),
                  _lzNote(Icons.info_outline_rounded,
                      'No vendors booked on Lazo yet. Once one is, this goes straight to their thread.'),
                ] else ...<Widget>[
                  _lzSection('Who gets it', trailing: '${picked.length} of ${booked.length}'),
                  for (final Map<String, dynamic> v in booked) vendorRow(v),
                  const SizedBox(height: 6),
                  TextField(
                    controller: noteC,
                    enabled: !busy,
                    minLines: 2,
                    maxLines: 4,
                    textCapitalization: TextCapitalization.sentences,
                    style: TextStyle(color: _lzFg(ink), fontSize: 13.5),
                    decoration: _lightDeco('A note to go with it (optional)'),
                  ),
                ],
                if (err.isNotEmpty) ...<Widget>[
                  const SizedBox(height: 12),
                  _lzNote(Icons.error_outline_rounded, err),
                ],
                _lzSection(booked.isEmpty ? 'Other ways to share it' : 'Or share it yourself'),
                Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                  if (booked.isNotEmpty) _pcB_chip(Icons.mail_outline_rounded, 'Email it', emailIt),
                  _pcB_chip(Icons.copy_rounded, 'Copy text', () async {
                    await Clipboard.setData(ClipboardData(text: text));
                    _toast('Copied \u2713');
                  }),
                  _pcB_chip(Icons.print_rounded, 'Print', () => _openHtml(page, text)),
                ]),
              ],
              footer: booked.isEmpty
                  ? _lzActions(
                      secondary: 'Close',
                      onSecondary: () => Navigator.of(ctx).pop(),
                      primary: 'Email it',
                      icon: Icons.mail_outline_rounded,
                      onPrimary: emailIt)
                  : _lzActions(
                      secondary: 'Cancel',
                      onSecondary: () => Navigator.of(ctx).pop(),
                      primary: busy
                          ? 'Sending\u2026'
                          : 'Send to ${picked.length} vendor${picked.length == 1 ? '' : 's'}',
                      icon: Icons.send_rounded,
                      busy: busy,
                      onPrimary: picked.isEmpty ? null : send));
        },
      ),
    );
  }

"""))

# ---------------------------------------------------------------- _editDetails
BLOCKS.append((
r"""    final String blurb = kind == 'photos'""",
r"""  Future<void> _sendDetails(String kind, Map<String, dynamic> couple) async {""",
r"""    final String blurb = kind == 'photos'
        ? 'Your photographer plans the day around this. Names help - "Aunt May" beats "an aunt".'
        : 'Your officiant, planner and DJ all read this. Add things in order; the arrows move one up.';
    if (!mounted) return;
    bool saving = false;
    String err = '';
    Future<void> save() async {
      await _detailsRef.doc(kind).set(<String, dynamic>{
        for (final List<String> f in fields) f[0]: items[f[0]]!.join('\n'),
        'updatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));
    }

    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 640),
      builder: (BuildContext ctx) =>
          StatefulBuilder(builder: (BuildContext sc, StateSetter setSheet) {
        int total = 0;
        for (final List<String> l in items.values) total += l.length;

        Future<void> run(bool send) async {
          setSheet(() {
            saving = true;
            err = '';
          });
          try {
            await save();
          } catch (e) {
            if (sc.mounted) {
              setSheet(() {
                saving = false;
                err = 'Couldn\u2019t save just now. Check your connection and try again.';
              });
            }
            return;
          }
          if (ctx.mounted) Navigator.pop(ctx);
          if (!send) {
            _toast('Saved.');
            return;
          }
          try {
            final Map<String, dynamic> couple =
                _liveD['couple:$_cid']?.latest?.data() ?? <String, dynamic>{};
            await _sendDetails(kind, couple);
          } catch (e) {
            _toast('Could not send: $e');
          }
        }

        Future<void> editItem(List<String> f, List<String> list, int index, bool multiline) async {
          final TextEditingController ec = TextEditingController(text: list[index]);
          final String? v = await _lzSheet<String>(
            context: sc,
            constraints: const BoxConstraints(maxWidth: 480),
            builder: (BuildContext dctx) => _lzFrame(dctx,
                icon: Icons.edit_rounded,
                title: f[1],
                subtitle: 'Clear it to remove this one.',
                children: <Widget>[
                  const SizedBox(height: 10),
                  TextField(
                      controller: ec,
                      autofocus: true,
                      minLines: 1,
                      maxLines: multiline ? 4 : 2,
                      textCapitalization: TextCapitalization.sentences,
                      textInputAction: multiline ? TextInputAction.newline : TextInputAction.done,
                      onSubmitted: multiline ? null : (String t) => Navigator.pop(dctx, t.trim()),
                      style: TextStyle(color: _lzFg(ink), fontSize: 14.5),
                      decoration: _lightDeco('Item')),
                ],
                footer: _lzActions(
                    secondary: 'Cancel',
                    onSecondary: () => Navigator.pop(dctx),
                    primary: 'Save',
                    icon: Icons.check_rounded,
                    onPrimary: () => Navigator.pop(dctx, ec.text.trim()))),
          );
          if (v != null) {
            setSheet(() {
              if (v.isEmpty) {
                list.removeAt(index);
              } else {
                list[index] = v;
              }
            });
          }
        }

        Widget section(List<String> f) {
          final String key = f[0];
          final List<String> list = items[key]!;
          final bool multiline = key == 'notes' || key == 'readings';
          return Container(
            margin: const EdgeInsets.only(bottom: 12),
            padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
            decoration: BoxDecoration(
                color: _lzBg(Colors.white.withOpacity(.8)),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: _lzLine(goldLine))),
            child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Row(children: <Widget>[
                    Expanded(
                      child: Text(f[1].toUpperCase(),
                          style: TextStyle(
                              color: _lzFg(plum),
                              fontSize: 10.5,
                              letterSpacing: 1.6,
                              fontWeight: FontWeight.w800)),
                    ),
                    if (list.isEmpty &&
                        (starters[key] ?? const <String>[]).isNotEmpty)
                      _Press(
                        tick: _Tick.select,
                        onTap: () =>
                            setSheet(() => list.addAll(starters[key]!)),
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 9, vertical: 4),
                          decoration: BoxDecoration(
                              color: gold.withOpacity(.18),
                              borderRadius: BorderRadius.circular(999),
                              border: Border.all(color: gold.withOpacity(.6))),
                          child: Text('Use a typical list',
                              style: TextStyle(
                                  color: _lzFg(plumDeep),
                                  fontSize: 10.5,
                                  fontWeight: FontWeight.w800)),
                        ),
                      ),
                  ]),
                  if (list.isEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 8, bottom: 4),
                      child: Text(f[2].replaceAll('\n', ' \u00b7 '),
                          style: TextStyle(
                              fontSize: 12,
                              color: _lzFg(ink.withOpacity(.4)),
                              height: 1.4)),
                    ),
                  ...list.asMap().entries.map((MapEntry<int, String> e) =>
                      Padding(
                        padding: const EdgeInsets.only(top: 6),
                        child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Container(
                                  width: 22,
                                  height: 22,
                                  margin: const EdgeInsets.only(top: 1),
                                  alignment: Alignment.center,
                                  decoration: BoxDecoration(
                                      color: gold.withOpacity(.2),
                                      borderRadius: BorderRadius.circular(999)),
                                  child: Text('${e.key + 1}',
                                      style: TextStyle(
                                          color: _lzFg(plum),
                                          fontSize: 11,
                                          fontWeight: FontWeight.w800))),
                              const SizedBox(width: 9),
                              Expanded(
                                child: _Press(
                                  tick: _Tick.select,
                                  onTap: () => editItem(f, list, e.key, multiline),
                                  child: Text(e.value,
                                      style: TextStyle(
                                          color: _lzFg(ink),
                                          fontSize: 14,
                                          height: 1.35)),
                                ),
                              ),
                              if (e.key > 0)
                                _Press(
                                  tick: _Tick.select,
                                  onTap: () => setSheet(() {
                                    final String x = list.removeAt(e.key);
                                    list.insert(e.key - 1, x);
                                  }),
                                  child: Tooltip(
                                    message: 'Move up',
                                    child: Padding(
                                        padding: const EdgeInsets.all(3),
                                        child: Icon(Icons.arrow_upward_rounded,
                                            size: 15, color: _lzFg(muted))),
                                  ),
                                ),
                              _Press(
                                tick: _Tick.select,
                                onTap: () =>
                                    setSheet(() => list.removeAt(e.key)),
                                child: Tooltip(
                                  message: 'Remove',
                                  child: Padding(
                                      padding: const EdgeInsets.all(3),
                                      child: Icon(Icons.close_rounded,
                                          size: 15, color: _lzFg(muted))),
                                ),
                              ),
                            ]),
                      )),
                  const SizedBox(height: 8),
                  Row(children: <Widget>[
                    Expanded(
                      child: TextField(
                        controller: adders[key],
                        textInputAction: TextInputAction.done,
                        textCapitalization: TextCapitalization.sentences,
                        onSubmitted: (String v) {
                          if (v.trim().isEmpty) return;
                          setSheet(() {
                            list.add(v.trim());
                            adders[key]!.clear();
                          });
                        },
                        style: TextStyle(color: _lzFg(ink), fontSize: 13.5),
                        decoration:
                            _lightDeco(multiline ? 'Add a note' : 'Add one'),
                      ),
                    ),
                    const SizedBox(width: 8),
                    IconButton(
                      tooltip: 'Add',
                      onPressed: _h(() {
                        final String v = adders[key]!.text.trim();
                        if (v.isEmpty) return;
                        setSheet(() {
                          list.add(v);
                          adders[key]!.clear();
                        });
                      }),
                      icon: Icon(Icons.add_circle_rounded,
                          color: _lzFg(plum), size: 26),
                    ),
                  ]),
                ]),
          );
        }

        return ConstrainedBox(
          constraints: BoxConstraints(maxHeight: MediaQuery.of(sc).size.height * .9),
          child: _lzFrame(sc,
              icon: kind == 'photos' ? Icons.photo_camera_rounded : Icons.menu_book_rounded,
              title: title,
              subtitle: blurb,
              bodyPadding: const EdgeInsets.fromLTRB(18, 14, 18, 14),
              children: <Widget>[
                for (final List<String> f in fields) section(f),
                if (err.isNotEmpty) _lzNote(Icons.error_outline_rounded, err),
              ],
              footer: Row(children: <Widget>[
                Padding(
                  padding: const EdgeInsets.only(left: 4, right: 8),
                  child: Text('$total item${total == 1 ? '' : 's'}',
                      style: TextStyle(
                          color: _lzFg(muted),
                          fontSize: 12.5,
                          fontWeight: FontWeight.w700)),
                ),
                Expanded(
                  child: _lzActions(
                      secondary: 'Save',
                      onSecondary: () => run(false),
                      primary: 'Save & send',
                      icon: Icons.send_rounded,
                      busy: saving,
                      onPrimary: total == 0 ? null : () => run(true)),
                ),
              ])),
        );
      }),
    );
    if (mounted) setState(() {});
  }

"""))

# ---------------------------------------------------------------- _timelineBuilderSheet
BLOCKS.append((
r"""  Future<void> _timelineBuilderSheet(""",
r"""  Future<void> _seedClassicDay(BuildContext ctx) async {""",
r"""  Future<void> _timelineBuilderSheet(
      Map<String, dynamic> couple, List<List<String>> team) async {
    if (!mounted) return;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 640),
      builder: (BuildContext ctx) => ConstrainedBox(
        constraints: BoxConstraints(maxHeight: MediaQuery.of(ctx).size.height * .88),
        child: StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
          stream: _liveQuery('dayof:$_cid', () => _dayofRef.orderBy('time')),
          initialData: _liveQ['dayof:$_cid']?.latest,
          builder: (BuildContext c,
              AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> sn) {
            final List<QueryDocumentSnapshot<Map<String, dynamic>>> evs =
                <QueryDocumentSnapshot<Map<String, dynamic>>>[
              ...(sn.data?.docs ??
                  <QueryDocumentSnapshot<Map<String, dynamic>>>[])
            ];
            _tlSortDocs(evs);

            Widget moment(int i) {
              final Map<String, dynamic> ev = evs[i].data();
              final bool last = i == evs.length - 1;
              final String hint = i == 0 ? '' : _tlHint(evs[i - 1].data(), ev);
              final bool clash = hint.startsWith('Overlaps');
              return _Press(
                onTap: () => _editTimelineEvent(evs[i]),
                child: IntrinsicHeight(
                  child: Row(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: <Widget>[
                        SizedBox(
                          width: 74,
                          child: Padding(
                            padding: const EdgeInsets.only(top: 10),
                            child: Text(_tlRange(ev),
                                style: TextStyle(
                                    color: _lzFg(clash ? rose : plum),
                                    fontSize: 12,
                                    height: 1.25,
                                    fontWeight: FontWeight.w800)),
                          ),
                        ),
                        Column(children: <Widget>[
                          Container(
                              width: 10,
                              height: 10,
                              margin: const EdgeInsets.only(top: 12),
                              decoration: BoxDecoration(
                                  color: gold,
                                  shape: BoxShape.circle,
                                  border: Border.all(color: plum, width: 1.5))),
                          if (!last)
                            Expanded(
                                child: Container(
                                    width: 2, color: gold.withOpacity(.5))),
                        ]),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Padding(
                            padding: const EdgeInsets.fromLTRB(0, 8, 0, 16),
                            child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: <Widget>[
                                  Text((ev['label'] ?? '').toString(),
                                      style: TextStyle(
                                          color: _lzFg(ink),
                                          fontSize: 14.5,
                                          fontWeight: FontWeight.w700)),
                                  if ((ev['note'] ?? '').toString().isNotEmpty)
                                    Text((ev['note'] ?? '').toString(),
                                        style: TextStyle(
                                            fontSize: 12.5,
                                            color: _lzFg(muted),
                                            height: 1.35)),
                                  _tlOwnerRow(ev),
                                  if (hint.isNotEmpty)
                                    Padding(
                                      padding: const EdgeInsets.only(top: 4),
                                      child: Text(hint,
                                          style: TextStyle(
                                              fontSize: 11,
                                              color: _lzFg(clash
                                                  ? rose
                                                  : const Color(0xFF8A6A2F)),
                                              fontWeight: FontWeight.w700)),
                                    ),
                                ]),
                          ),
                        ),
                        IconButton(
                          // 44x44 is the floor on both platforms; compact density was 40.
                          constraints:
                              const BoxConstraints(minWidth: 44, minHeight: 44),
                          padding: EdgeInsets.zero,
                          tooltip: 'Remove this moment',
                          onPressed: _h(() async {
                            // Snapshot first: after the delete
                            // there is nothing left to read.
                            final Map<String, dynamic> gone = evs[i].data();
                            final DocumentReference<Map<String, dynamic>> ref =
                                evs[i].reference;
                            await ref.delete();
                            _toastUndo('Moment removed.', () => ref.set(gone));
                          }),
                          icon: Icon(Icons.close_rounded,
                              color: _lzFg(muted), size: 16),
                        ),
                      ]),
                ),
              );
            }

            return _lzFrame(ctx,
                icon: Icons.schedule_rounded,
                title: 'Day-of timeline',
                subtitle: evs.isEmpty
                    ? 'The whole day, hour by hour. Every vendor plans around it.'
                    : '${evs.length} moment${evs.length == 1 ? '' : 's'} \u00b7 tap one to change it',
                headerExtra: evs.isEmpty
                    ? null
                    : Align(
                        alignment: Alignment.centerLeft,
                        child: _tlChip(
                            _tlAnchor(evs) == null
                                ? 'Mark the ceremony to shift the whole day'
                                : 'Ceremony at ${_fmtClock((_tlAnchor(evs)!.data()['time'] ?? '').toString())} \u00b7 change',
                            _tlAnchor(evs) != null,
                            () => _tlReanchor(ctx, evs)),
                      ),
                bodyPadding: const EdgeInsets.fromLTRB(18, 12, 18, 12),
                children: <Widget>[
                  if (evs.isEmpty)
                    _pcB_empty(Icons.schedule_rounded,
                        'Getting ready, first look, ceremony, cocktails, dinner, dances, send-off. Start from a classic day built around your ceremony time, then adjust.')
                  else
                    for (int i = 0; i < evs.length; i++) moment(i),
                ],
                footer: evs.isEmpty
                    ? _lzActions(
                        secondary: 'Add one moment',
                        onSecondary: () => _editTimelineEvent(null),
                        primary: 'Start from a classic day',
                        icon: Icons.auto_awesome_rounded,
                        onPrimary: () => _seedClassicDay(ctx))
                    : _lzActions(
                        secondary: 'Add a moment',
                        onSecondary: () => _editTimelineEvent(null),
                        primary: 'Send to vendors',
                        icon: Icons.send_rounded,
                        onPrimary: () {
                          Navigator.pop(ctx);
                          _sendTimeline(evs, team, couple);
                        }));
          },
        ),
      ),
    );
  }

"""))

# ---------------------------------------------------------------- _deleteAccount
BLOCKS.append((
r"""  Future<void> _deleteAccount() async {""",
r"""  // v91: flat ivory on the plum canvas.""",
r"""  Future<void> _deleteAccount() async {
    final User? u0 = FirebaseAuth.instance.currentUser;
    if (u0 == null) return;
    final User u = u0;

    // Deletion runs server-side now. The old code here deleted couples/{cid} and
    // its 'plan' subcollection, swallowed every error, then deleted the login
    // regardless - leaving the wedding website, every message thread, the other
    // seven subcollections and all uploaded photos behind, and unreachable once
    // the login was gone. deleteMyAccount removes all of it and deletes the
    // login LAST, so a partial failure is retryable rather than permanent.
    // See functions-dashboard/deleteAccount.js.
    // cB (JC-LAZO-POPUP-1014): one popup asks, works, asks for the password
    // when Firebase wants a recent login, and shows any failure in place.
    final String email = u.email ?? '';
    final TextEditingController passC = TextEditingController();
    bool busy = false;
    bool needPass = false;
    bool gone = false;
    String err = '';
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 480),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext sc, StateSetter setS) {
          void upd(VoidCallback f) {
            if (sc.mounted) setS(f);
          }

          Future<void> go() async {
            upd(() {
              busy = true;
              err = '';
            });
            try {
              if (needPass) {
                await u.reauthenticateWithCredential(
                    EmailAuthProvider.credential(email: email, password: passC.text));
              }
              await FirebaseFunctions.instance
                  .httpsCallable('deleteMyAccount')
                  .call(<String, dynamic>{});
              gone = true;
              if (ctx.mounted) Navigator.pop(ctx);
            } on FirebaseFunctionsException catch (e) {
              upd(() {
                busy = false;
                err = e.message ?? 'We could not delete your account just now.';
              });
            } on FirebaseAuthException catch (e) {
              if (!needPass && e.code == 'requires-recent-login') {
                upd(() {
                  busy = false;
                  needPass = true;
                });
              } else {
                upd(() {
                  busy = false;
                  err = needPass
                      ? 'Password didn\u2019t match - account not deleted.'
                      : (e.message ?? 'We could not delete your account just now.');
                });
              }
            } catch (_) {
              upd(() {
                busy = false;
                err = needPass
                    ? 'Password didn\u2019t match - account not deleted.'
                    : 'We could not delete your account just now.';
              });
            }
          }

          return _lzFrame(sc,
              icon: needPass ? Icons.lock_outline_rounded : Icons.warning_amber_rounded,
              title: needPass ? 'Confirm it\u2019s you' : 'Delete your account?',
              subtitle: needPass
                  ? 'Enter your password to finish deleting your account.'
                  : 'This can\u2019t be undone.',
              children: <Widget>[
                const SizedBox(height: 10),
                if (!needPass)
                  Text(
                      'Your account and wedding plan are deleted for good, with your website, message threads and photos.',
                      style: TextStyle(fontSize: 14.5, color: _lzFg(ink), height: 1.5))
                else
                  TextField(
                    controller: passC,
                    autofocus: true,
                    obscureText: true,
                    enabled: !busy,
                    textInputAction: TextInputAction.done,
                    onChanged: (String _) => upd(() {}),
                    onSubmitted: (String _) {
                      if (!busy && passC.text.isNotEmpty) go();
                    },
                    style: TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _lightDeco('Password'),
                  ),
                if (busy) ...<Widget>[
                  const SizedBox(height: 14),
                  _lzBusy('Deleting your account\u2026'),
                ],
                if (err.isNotEmpty) ...<Widget>[
                  const SizedBox(height: 14),
                  _lzNote(Icons.error_outline_rounded, err),
                ],
              ],
              footer: _lzActions(
                  secondary: 'Keep my account',
                  onSecondary: () => Navigator.pop(sc),
                  primary: needPass ? 'Delete' : 'Delete my account',
                  danger: true,
                  icon: Icons.delete_outline_rounded,
                  busy: busy,
                  onPrimary: needPass && passC.text.isEmpty ? null : go));
        },
      ),
    );
    if (!gone) return;
    await FirebaseAuth.instance.signOut();
    if (!mounted) return;
    context.goNamed(pageWelcome);
  }

"""))

# ---------------------------------------------------------------- _editWantedSheet
BLOCKS.append((
r"""  Future<void> _editWantedSheet(Map<String, Map<String, dynamic>> plan) async {""",
r"""  // ---------------- v91: WEBSITE + BUDGET, AT A GLANCE ----------------""",
r"""  Future<void> _editWantedSheet(Map<String, Map<String, dynamic>> plan) async {
    final Set<String> wanted = <String>{
      for (final Map<String, String> c in kCategories)
        if ((plan[c['slug']]?['status'] ?? 'needed').toString() != 'skipped')
          c['slug'] ?? ''
    };
    if (!mounted) return;
    bool saving = false;
    String err = '';
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 620),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) {
          Future<void> save() async {
            setD(() {
              saving = true;
              err = '';
            });
            try {
              final WriteBatch b = FirebaseFirestore.instance.batch();
              for (final Map<String, String> c in kCategories) {
                final String slug = c['slug'] ?? '';
                final String cur =
                    (plan[slug]?['status'] ?? 'needed').toString();
                if (cur == 'booked') continue;
                final String next = wanted.contains(slug)
                    ? (cur == 'skipped' ? 'needed' : cur)
                    : 'skipped';
                if (next != cur) {
                  b.set(
                      _planRef.doc(slug),
                      <String, dynamic>{
                        'status': next,
                        'updatedAt': FieldValue.serverTimestamp()
                      },
                      SetOptions(merge: true));
                }
              }
              await b.commit();
              if (ctx2.mounted) Navigator.pop(ctx2);
            } catch (_) {
              if (ctx2.mounted) {
                setD(() {
                  saving = false;
                  err = 'Couldn\u2019t save just now. Check your connection and try again.';
                });
              }
            }
          }

          return _lzFrame(ctx2,
              icon: Icons.checklist_rounded,
              title: 'Which vendors do you need?',
              subtitle: 'Tap to add or remove. Booked vendors stay either way.',
              children: <Widget>[
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: <Widget>[
                    for (final Map<String, String> c in kCategories)
                      Builder(builder: (BuildContext bc) {
                        final String slug = c['slug'] ?? '';
                        final bool booked =
                            (plan[slug]?['status'] ?? '') == 'booked';
                        final bool on = wanted.contains(slug) || booked;
                        return FilterChip(
                          label: Text(c['label'] ?? '',
                              style: TextStyle(
                                  fontSize: 12.5,
                                  color: _lzFg(on ? ivory : plum),
                                  fontWeight: FontWeight.w600)),
                          selected: on,
                          selectedColor: plum,
                          checkmarkColor: gold,
                          backgroundColor: _lzBg(Colors.white),
                          side: BorderSide(color: gold.withOpacity(.6)),
                          tooltip: booked ? 'Booked' : null,
                          onSelected: _hb(booked || saving
                              ? null
                              : (bool v) => setD(() {
                                    if (v) {
                                      wanted.add(slug);
                                    } else {
                                      wanted.remove(slug);
                                    }
                                  })),
                        );
                      }),
                  ],
                ),
                if (err.isNotEmpty) ...<Widget>[
                  const SizedBox(height: 14),
                  _lzNote(Icons.error_outline_rounded, err),
                ],
              ],
              footer: _lzActions(
                  secondary: 'Cancel',
                  onSecondary: () => Navigator.pop(ctx2),
                  primary:
                      'Save my ${wanted.length} vendor${wanted.length == 1 ? '' : 's'}',
                  icon: Icons.check_rounded,
                  busy: saving,
                  onPrimary: save));
        },
      ),
    );
  }

"""))

# ---------------------------------------------------------------- _budgetSheet
BLOCKS.append((
r"""  Future<void> _budgetSheet(Map<String, dynamic> couple,""",
r"""  // ---------------- v91: SETUP, THE WAY JUNE WOULD ASK ----------------""",
r"""  Future<void> _budgetSheet(Map<String, dynamic> couple,
      Map<String, Map<String, dynamic>> plan) async {
    if (!mounted) return;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 720),
      builder: (BuildContext ctx) => ConstrainedBox(
        constraints: BoxConstraints(maxHeight: MediaQuery.of(ctx).size.height * .88),
        child: _lzFrame(ctx,
            icon: Icons.account_balance_wallet_rounded,
            title: 'Budget',
            subtitle: 'What you planned and what\u2019s committed, line by line.',
            bodyPadding: const EdgeInsets.fromLTRB(18, 14, 18, 24),
            children: <Widget>[
              StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
                stream: _liveQuery('plan:$_cid', () => _planRef),
                initialData: _liveQ['plan:$_cid']?.latest,
                builder: (BuildContext c2,
                    AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> ps) {
                  final Map<String, Map<String, dynamic>> livePlan =
                      <String, Map<String, dynamic>>{
                    for (final QueryDocumentSnapshot<Map<String, dynamic>> d
                        in ps.data?.docs ??
                            <QueryDocumentSnapshot<Map<String, dynamic>>>[])
                      d.id: d.data()
                  };
                  return _budgetCard(couple, livePlan);
                },
              ),
            ]),
      ),
    );
  }

"""))

# ---------------------------------------------------------------- _setupSheet
BLOCKS.append((
r"""    int step = 0;
    bool saving = false;
    if (!mounted) return;
    await _lzSheet<void>(""",
r"""  // ---------------- v91: PLAN TOGETHER ----------------""",
r"""    int step = 0;
    bool saving = false;
    String err = '';
    if (!mounted) return;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 620),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) {
          // Title, then the one line that says why June asks.
          const List<List<String>> asks = <List<String>>[
            <String>['Who\u2019s getting married?', 'Your names, the way you\u2019d like them shown.'],
            <String>['When\u2019s the day?', 'A month is enough for now.'],
            <String>['Where?', 'The city sets who June can show you and what things cost.'],
            <String>['A rough budget', 'June uses it to keep proposals honest, not to judge.'],
            <String>['Which vendors do you need?', 'Tap to add or remove. You can change this any time.'],
          ];
          const List<IconData> stepIcons = <IconData>[
            Icons.favorite_rounded,
            Icons.event_rounded,
            Icons.place_rounded,
            Icons.account_balance_wallet_rounded,
            Icons.checklist_rounded,
          ];

          Future<void> next() async {
            if (step < asks.length - 1) {
              setD(() => step++);
              return;
            }
            setD(() {
              saving = true;
              err = '';
            });
            try {
              final double? b = double.tryParse(
                  budgetC.text.trim().replaceAll(',', ''));
              await _coupleRef.set(<String, dynamic>{
                if (namesC.text.trim().isNotEmpty) 'names': namesC.text.trim(),
                if (metro.isNotEmpty) 'metroId': metro,
                if (date != null) 'weddingDate': Timestamp.fromDate(date!),
                if (b != null && b > 0) 'budgetTotal': b,
                'setupDoneAt': FieldValue.serverTimestamp(),
                'updatedAt': FieldValue.serverTimestamp(),
              }, SetOptions(merge: true));
              // v139: only categories with no plan
              // doc yet - reopening setup used to flip
              // a booked vendor back to "needed"
              final Set<String> hasPlan = <String>{};
              try {
                final QuerySnapshot<Map<String, dynamic>> pq =
                    await _planRef.get();
                for (final QueryDocumentSnapshot<Map<String, dynamic>> pd
                    in pq.docs) {
                  if ((pd.data()['status'] ?? '').toString().isNotEmpty) {
                    hasPlan.add(pd.id);
                  }
                }
              } catch (_) {}
              final WriteBatch wb = FirebaseFirestore.instance.batch();
              for (final Map<String, String> c in kCategories) {
                final String slug = c['slug'] ?? '';
                if (hasPlan.contains(slug)) {
                  continue;
                }
                wb.set(
                    _planRef.doc(slug),
                    <String, dynamic>{
                      'status': wanted.contains(slug) ? 'needed' : 'skipped'
                    },
                    SetOptions(merge: true));
              }
              await wb.commit();
              if (ctx2.mounted) Navigator.pop(ctx2);
            } catch (e) {
              if (ctx2.mounted) {
                setD(() {
                  saving = false;
                  err = 'Couldn\u2019t save just now. Check your connection and try again.';
                });
              }
            }
          }

          Widget body;
          if (step == 0) {
            body = TextField(
                controller: namesC,
                autofocus: true,
                textCapitalization: TextCapitalization.words,
                textInputAction: TextInputAction.next,
                onSubmitted: (String _) => next(),
                style: TextStyle(color: _lzFg(ink), fontSize: 16),
                decoration: _lightDeco('Your names', hint: 'Mindy and John'));
          } else if (step == 1) {
            body = OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                  foregroundColor: _lzFg(plum),
                  side: const BorderSide(color: gold),
                  alignment: Alignment.centerLeft,
                  padding:
                      const EdgeInsets.symmetric(vertical: 16, horizontal: 16),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14))),
              onPressed: _h(() async {
                final DateTime? picked = await showDatePicker(
                    context: ctx2,
                    initialDate:
                        date ?? DateTime.now().add(const Duration(days: 300)),
                    firstDate: (date != null && date!.isBefore(DateTime.now()))
                        ? date!
                        : DateTime.now(),
                    lastDate:
                        DateTime.now().add(const Duration(days: 365 * 4)));
                if (picked != null) setD(() => date = picked);
              }),
              icon: const Icon(Icons.event_rounded, size: 18),
              label: Text(date == null ? 'Pick the date' : _longDate(date!),
                  style: const TextStyle(
                      fontSize: 15, fontWeight: FontWeight.w700)),
            );
          } else if (step == 2) {
            body = DropdownButtonFormField<String>(
              value: metro.isEmpty ? null : metro,
              dropdownColor: _lzBg(ivory),
              style: TextStyle(color: _lzFg(ink), fontSize: 15),
              decoration: _lightDeco('City'),
              items: <DropdownMenuItem<String>>[
                for (final Map<String, String> m in kMetros)
                  DropdownMenuItem<String>(
                      value: m['id'], child: Text(m['label'] ?? ''))
              ],
              onChanged: (String? v) => setD(() => metro = v ?? ''),
            );
          } else if (step == 3) {
            body = TextField(
                controller: budgetC,
                autofocus: true,
                keyboardType: TextInputType.number,
                textInputAction: TextInputAction.next,
                onSubmitted: (String _) => next(),
                style: TextStyle(color: _lzFg(ink), fontSize: 16),
                decoration: _lightDeco('Total budget',
                    hint: '25000', prefix: '\u0024 '));
          } else {
            body = Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
              for (final Map<String, String> c in kCategories)
                FilterChip(
                  label: Text(c['label'] ?? '',
                      style: TextStyle(
                          fontSize: 12.5,
                          color: _lzFg(wanted.contains(c['slug']) ? ivory : plum),
                          fontWeight: FontWeight.w600)),
                  selected: wanted.contains(c['slug']),
                  selectedColor: plum,
                  checkmarkColor: gold,
                  backgroundColor: _lzBg(Colors.white),
                  side: BorderSide(color: gold.withOpacity(.6)),
                  onSelected: _hb((bool v) => setD(() {
                        if (v) {
                          wanted.add(c['slug'] ?? '');
                        } else {
                          wanted.remove(c['slug']);
                        }
                      })),
                ),
            ]);
          }
          final bool lastStep = step == asks.length - 1;
          return _lzFrame(ctx2,
              icon: stepIcons[step],
              title: asks[step][0],
              subtitle: asks[step][1],
              headerExtra: Row(children: <Widget>[
                Expanded(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(99),
                    child: LinearProgressIndicator(
                        value: (step + 1) / asks.length,
                        minHeight: 5,
                        backgroundColor: _lzLine(goldLine).withOpacity(.5),
                        valueColor: const AlwaysStoppedAnimation<Color>(gold)),
                  ),
                ),
                const SizedBox(width: 10),
                Text('June \u00b7 ${step + 1} of ${asks.length}',
                    style: TextStyle(
                        fontSize: 12,
                        color: _lzFg(muted),
                        fontWeight: FontWeight.w600)),
              ]),
              children: <Widget>[
                const SizedBox(height: 14),
                KeyedSubtree(key: ValueKey<int>(step), child: body),
                if (err.isNotEmpty) ...<Widget>[
                  const SizedBox(height: 14),
                  _lzNote(Icons.error_outline_rounded, err),
                ],
              ],
              footer: _lzActions(
                  secondary: step > 0 ? 'Back' : 'Not now',
                  onSecondary: step > 0
                      ? () => setD(() => step--)
                      : () => Navigator.pop(ctx2),
                  primary: lastStep ? 'Done' : 'Next',
                  icon: lastStep ? Icons.check_rounded : Icons.arrow_forward_rounded,
                  busy: saving,
                  onPrimary: next));
        },
      ),
    );
  }

"""))

# ---------------------------------------------------------------- _partnerSheet
BLOCKS.append((
r"""  Future<void> _partnerSheet(Map<String, dynamic> couple) async {""",
r"""  String _randomCode(int n) {""",
r"""  Future<void> _partnerSheet(Map<String, dynamic> couple) async {
    final TextEditingController emailC = TextEditingController();
    final TextEditingController codeC = TextEditingController();
    bool inviting = false, joining = false;
    String inviteErr = '', joinErr = '';
    if (!mounted) return;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 620),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext sc, StateSetter setS) {
          void upd(VoidCallback f) {
            if (sc.mounted) setS(f);
          }

          final String em = emailC.text.trim().toLowerCase();
          final bool emailOk = em.contains('@');
          final String code =
              codeC.text.trim().toUpperCase().replaceAll(' ', '');

          Future<void> invite() async {
            if (!emailOk || inviting) return;
            upd(() {
              inviting = true;
              inviteErr = '';
            });
            try {
              await FirebaseFirestore.instance
                  .collection('coupleInvites')
                  .add(<String, dynamic>{
                'coupleUid': _cid,
                'email': em,
                'code': _randomCode(6),
                'status': 'pending',
                'createdBy': _uid,
                'createdAt': FieldValue.serverTimestamp(),
              });
              emailC.clear();
              upd(() => inviting = false);
              _toast('Invite created - send them the code.');
            } catch (e) {
              upd(() {
                inviting = false;
                inviteErr = 'Couldn\u2019t create the invite. Try again in a moment.';
              });
            }
          }

          Future<void> join() async {
            if (code.length < 4 || joining) return;
            upd(() {
              joining = true;
              joinErr = '';
            });
            try {
              final HttpsCallable fn = FirebaseFunctions.instance.httpsCallable(
                  'redeemCoupleInvite',
                  options: HttpsCallableOptions(
                      timeout: const Duration(seconds: 30)));
              final HttpsCallableResult<dynamic> out =
                  await fn.call(<String, dynamic>{'code': code});
              final Map<String, dynamic> r =
                  Map<String, dynamic>.from(out.data as Map);
              final String cu = (r['coupleUid'] ?? '').toString();
              if (ctx.mounted) Navigator.pop(ctx);
              if (cu.isNotEmpty && mounted) {
                setState(() => _coupleIdCache = cu);
              }
              _toast('You\u2019re in - one plan, both of you.');
            } on FirebaseFunctionsException catch (e) {
              upd(() {
                joining = false;
                joinErr = e.message ?? 'That code did not work.';
              });
            } catch (_) {
              upd(() {
                joining = false;
                joinErr = 'That code did not work.';
              });
            }
          }

          return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
            stream: _liveQuery(
                'cinv:$_cid',
                () => FirebaseFirestore.instance
                    .collection('coupleInvites')
                    .where('coupleUid', isEqualTo: _cid)),
            initialData: _liveQ['cinv:$_cid']?.latest,
            builder: (BuildContext c2,
                AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> s) {
              final List<QueryDocumentSnapshot<Map<String, dynamic>>> docs =
                  s.data?.docs ??
                      <QueryDocumentSnapshot<Map<String, dynamic>>>[];
              return _lzFrame(sc,
                  icon: Icons.favorite_rounded,
                  title: 'Plan together',
                  subtitle: 'One plan and one inbox, for both of you.',
                  children: <Widget>[
                    _lzSection('Invite your partner'),
                    for (final QueryDocumentSnapshot<Map<String, dynamic>> d
                        in docs)
                      Container(
                        margin: const EdgeInsets.only(bottom: 8),
                        padding: const EdgeInsets.fromLTRB(12, 8, 6, 8),
                        decoration: BoxDecoration(
                            color: _lzBg(Colors.white),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: _lzLine(goldLine))),
                        child: Row(children: <Widget>[
                          Icon(
                              (d.data()['status'] ?? 'pending') == 'accepted'
                                  ? Icons.check_circle_rounded
                                  : Icons.hourglass_top_rounded,
                              size: 18,
                              color: (d.data()['status'] ?? 'pending') ==
                                      'accepted'
                                  ? vGreen
                                  : gold),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: <Widget>[
                                  Text((d.data()['email'] ?? '').toString(),
                                      style: TextStyle(
                                          color: _lzFg(ink),
                                          fontSize: 13.5,
                                          fontWeight: FontWeight.w600)),
                                  Text(
                                      (d.data()['status'] ?? 'pending') ==
                                              'accepted'
                                          ? 'Joined'
                                          : 'Code ${(d.data()['code'] ?? '').toString()} - waiting for them',
                                      style: TextStyle(
                                          fontSize: 12, color: _lzFg(muted))),
                                ]),
                          ),
                          if ((d.data()['status'] ?? 'pending') != 'accepted')
                            IconButton(
                              tooltip: 'Copy code',
                              icon: Icon(Icons.copy_rounded,
                                  color: _lzFg(plum), size: 18),
                              onPressed: _h(() async {
                                await Clipboard.setData(ClipboardData(
                                    text: (d.data()['code'] ?? '').toString()));
                                _toast('Code copied \u2713');
                              }),
                            ),
                        ]),
                      ),
                    TextField(
                        controller: emailC,
                        enabled: !inviting,
                        keyboardType: TextInputType.emailAddress,
                        textInputAction: TextInputAction.send,
                        onChanged: (String _) => upd(() {}),
                        onSubmitted: (String _) => invite(),
                        style: TextStyle(color: _lzFg(ink), fontSize: 14.5),
                        decoration: _lightDeco('Their email',
                            hint: 'name@example.com')),
                    const SizedBox(height: 10),
                    FilledButton.icon(
                      style: FilledButton.styleFrom(
                          backgroundColor: gold,
                          foregroundColor: plumDeep,
                          disabledBackgroundColor: gold.withOpacity(.45),
                          disabledForegroundColor: plumDeep.withOpacity(.7),
                          elevation: 0,
                          minimumSize: const Size(0, 46),
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(13))),
                      onPressed: _h(emailOk && !inviting ? invite : null,
                          _Tick.medium),
                      icon: inviting
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(
                                  strokeWidth: 2, color: plumDeep))
                          : const Icon(Icons.favorite_rounded, size: 17),
                      label: const Text('Invite my partner',
                          style: TextStyle(fontWeight: FontWeight.w800)),
                    ),
                    if (inviteErr.isNotEmpty) ...<Widget>[
                      const SizedBox(height: 10),
                      _lzNote(Icons.error_outline_rounded, inviteErr),
                    ],
                    const SizedBox(height: 10),
                    _lzNote(Icons.info_outline_rounded,
                        'They sign up at app.meetlazo.com with this email, then enter the code under Plan together.'),
                    _lzSection('Were you invited?'),
                    Row(children: <Widget>[
                      Expanded(
                        child: TextField(
                            controller: codeC,
                            enabled: !joining,
                            textCapitalization: TextCapitalization.characters,
                            textInputAction: TextInputAction.go,
                            onChanged: (String _) => upd(() {}),
                            onSubmitted: (String _) => join(),
                            style: TextStyle(
                                color: _lzFg(ink),
                                fontSize: 16,
                                letterSpacing: 3,
                                fontWeight: FontWeight.w700),
                            decoration: _lightDeco('Invite code')),
                      ),
                      const SizedBox(width: 10),
                      OutlinedButton(
                        style: OutlinedButton.styleFrom(
                            foregroundColor: _lzFg(plum),
                            side: const BorderSide(color: gold),
                            minimumSize: const Size(0, 50),
                            padding: const EdgeInsets.symmetric(horizontal: 18),
                            shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(13))),
                        onPressed: _h(code.length >= 4 && !joining ? join : null),
                        child: joining
                            ? SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(
                                    strokeWidth: 2, color: _lzFg(plum)))
                            : const Text('Join',
                                style: TextStyle(fontWeight: FontWeight.w800)),
                      ),
                    ]),
                    if (joinErr.isNotEmpty) ...<Widget>[
                      const SizedBox(height: 10),
                      _lzNote(Icons.error_outline_rounded, joinErr),
                    ],
                  ]);
            },
          );
        },
      ),
    );
  }

"""))

# ---------------------------------------------------------------- _openSupportSheet
BLOCKS.append((
r"""  Future<void> _openSupportSheet() async {""",
r"""  Widget _accountScreen(Map<String, dynamic> couple) {""",
r"""  Future<void> _openSupportSheet() async {
    final User? u0 = FirebaseAuth.instance.currentUser;
    if (u0 == null) return;
    final User u = u0;
    String cat = 'Report a vendor';
    final TextEditingController vendC = TextEditingController();
    final TextEditingController subjC = TextEditingController();
    final TextEditingController msgC = TextEditingController();
    bool busy = false;
    String err = '';
    const List<List<dynamic>> cats = <List<dynamic>>[
      <dynamic>['Report a vendor', Icons.flag_outlined],
      <dynamic>['Report a bug', Icons.bug_report_outlined],
      <dynamic>['Billing question', Icons.receipt_long_outlined],
      <dynamic>['Something else', Icons.help_outline_rounded],
    ];
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 520),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext sc, StateSetter setD) {
          void upd(VoidCallback f) {
            if (sc.mounted) setD(f);
          }

          final bool ready =
              subjC.text.trim().isNotEmpty && msgC.text.trim().isNotEmpty;

          Future<void> send() async {
            upd(() {
              busy = true;
              err = '';
            });
            try {
              await FirebaseFirestore.instance
                  .collection('supportTickets')
                  .add(<String, dynamic>{
                'role': 'couple',
                'uid': u.uid,
                'email': u.email ?? '',
                'category': cat,
                'subject': subjC.text.trim(),
                'message': msgC.text.trim(),
                'vendorName': vendC.text.trim(),
                'status': 'open',
                'createdAt': FieldValue.serverTimestamp(),
                'context': <String, dynamic>{
                  'source': 'couple_dashboard',
                  'build': 'v90',
                },
              });
              if (ctx.mounted) Navigator.pop(ctx);
              _toastC('Ticket sent \u2713 We\u2019ll get back to you by email.');
            } catch (_) {
              upd(() {
                busy = false;
                err = 'Couldn\u2019t send the ticket. Check your connection and try again.';
              });
            }
          }

          return _lzFrame(sc,
              icon: Icons.support_agent_rounded,
              title: 'Support',
              subtitle: 'Tell us what happened. We\u2019ll reply by email.',
              children: <Widget>[
                _lzSection('What is this about?'),
                Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                  for (final List<dynamic> c in cats)
                    ChoiceChip(
                      avatar: Icon(c[1] as IconData,
                          size: 16, color: _lzFg(cat == c[0] ? ivory : plum)),
                      label: Text(c[0] as String,
                          style: TextStyle(
                              fontSize: 12.5,
                              color: _lzFg(cat == c[0] ? ivory : plum),
                              fontWeight: FontWeight.w600)),
                      selected: cat == c[0],
                      showCheckmark: false,
                      selectedColor: plum,
                      backgroundColor: _lzBg(Colors.white),
                      side: BorderSide(color: gold.withOpacity(.6)),
                      onSelected: busy
                          ? null
                          : _hb((bool _) => upd(() => cat = c[0] as String)),
                    ),
                ]),
                const SizedBox(height: 16),
                if (cat == 'Report a vendor') ...<Widget>[
                  TextField(
                    controller: vendC,
                    enabled: !busy,
                    textCapitalization: TextCapitalization.words,
                    textInputAction: TextInputAction.next,
                    cursorColor: _lzFg(plum),
                    style: TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _lightDeco('Which vendor?'),
                  ),
                  const SizedBox(height: 12),
                ],
                TextField(
                  controller: subjC,
                  enabled: !busy,
                  textCapitalization: TextCapitalization.sentences,
                  textInputAction: TextInputAction.next,
                  onChanged: (String _) => upd(() {}),
                  cursorColor: _lzFg(plum),
                  style: TextStyle(color: _lzFg(ink), fontSize: 14),
                  decoration: _lightDeco('Subject'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: msgC,
                  enabled: !busy,
                  minLines: 4,
                  maxLines: 6,
                  textCapitalization: TextCapitalization.sentences,
                  onChanged: (String _) => upd(() {}),
                  cursorColor: _lzFg(plum),
                  style: TextStyle(color: _lzFg(ink), fontSize: 14),
                  decoration: _lightDeco('Tell us what happened'),
                ),
                if (err.isNotEmpty) ...<Widget>[
                  const SizedBox(height: 12),
                  _lzNote(Icons.error_outline_rounded, err),
                ],
              ],
              footer: _lzActions(
                  secondary: 'Cancel',
                  onSecondary: () => Navigator.pop(sc),
                  primary: busy ? 'Sending\u2026' : 'Send',
                  icon: Icons.send_rounded,
                  busy: busy,
                  onPrimary: ready ? send : null));
        },
      ),
    );
  }

"""))

# ---------------------------------------------------------------- _accountScreen
# "Your partner" opened a sheet holding the Plan together card, which opened a
# second sheet on top. It opens the Plan together sheet directly now.
BLOCKS.append((
r"""            onTap: () => _lzSheet<void>(
              context: context,
              backgroundColor: _lzBg(ivory),
              isScrollControlled: true,
              constraints: const BoxConstraints(maxWidth: 560),""",
r"""          _accountRow(
            icon: Icons.notifications_active_outlined,""",
r"""            onTap: () => _partnerSheet(couple),
          ),
"""))

# ---------------------------------------------------------------- _refineSheet
BLOCKS.append((
r"""  Future<void> _refineSheet() async {""",
r"""  Widget _monogram(String name,""",
r"""  Future<void> _refineSheet() async {
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) {
          void set(VoidCallback f) {
            setD(f);
            setState(() {});
          }

          Widget toggle(
                  String label, String why, bool v, ValueChanged<bool> f) =>
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 3),
                child: Row(children: <Widget>[
                  Expanded(
                    child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(label,
                              style: TextStyle(
                                  color: _lzFg(ink),
                                  fontSize: 14,
                                  fontWeight: FontWeight.w700)),
                          Text(why,
                              style: TextStyle(
                                  color: _lzFg(muted), fontSize: 11.5)),
                        ]),
                  ),
                  _lazoSwitch(
                      value: v, onChanged: _hb((bool b) => set(() => f(b)))),
                ]),
              );

          final int n = _activeRefinements.length;
          return _lzFrame(ctx2,
              icon: Icons.tune_rounded,
              title: 'Narrow it down',
              subtitle: n == 0
                  ? 'By budget, and by the kind of business you want.'
                  : '$n filter${n == 1 ? '' : 's'} on',
              children: <Widget>[
                _lzSection('Budget'),
                Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                  for (final List<dynamic> o in <List<dynamic>>[
                    <dynamic>[0, 'Any budget'],
                    <dynamic>[1, 'Under \u00242k'],
                    <dynamic>[2, '\u00242\u20135k'],
                    <dynamic>[3, '\u00245k+'],
                  ])
                    ChoiceChip(
                      label: Text(o[1] as String,
                          style: TextStyle(
                              fontSize: 12.5,
                              color: _lzFg(_fPrice == o[0] ? ivory : plum),
                              fontWeight: FontWeight.w600)),
                      selected: _fPrice == o[0],
                      showCheckmark: false,
                      selectedColor: plum,
                      backgroundColor: _lzBg(Colors.white),
                      side: BorderSide(color: gold.withOpacity(.6)),
                      onSelected:
                          _hb((_) => set(() => _fPrice = o[0] as int)),
                    ),
                ]),
                _lzSection('The business'),
                toggle('Woman-led', 'Owned or led by a woman', _fWoman,
                    (bool v) => _fWoman = v),
                toggle('LGBTQ+ owned', 'Owned by an LGBTQ+ person', _fLgbtq,
                    (bool v) => _fLgbtq = v),
                toggle('Deals', 'Has an offer on right now', _fDeals,
                    (bool v) => _fDeals = v),
                toggle('Top rated', 'Strongest verified reviews', _fTop,
                    (bool v) => _fTop = v),
              ],
              footer: _lzActions(
                  secondary: n > 0 ? 'Clear all' : null,
                  onSecondary: () => set(() {
                        _fPrice = 0;
                        _fWoman = false;
                        _fLgbtq = false;
                        _fDeals = false;
                        _fTop = false;
                      }),
                  primary: 'Show vendors',
                  icon: Icons.search_rounded,
                  onPrimary: () => Navigator.pop(ctx2)));
        },
      ),
    );
  }

"""))

# ---------------------------------------------------------------- _vendorSheet
BLOCKS.append((
r"""    _lzSheet(
      context: context,
      backgroundColor: _lzBg(ivory),
      isScrollControlled: true,
      constraints: const BoxConstraints(maxWidth: 680),""",
r"""  Widget _websiteScreen(Map<String, dynamic> couple) {""",
r"""    final double rating = ((v['rating'] ?? 0) as num).toDouble();
    _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 680),
      builder: (BuildContext ctx) => _lzFrame(ctx,
          title: name,
          subtitle: <String>[
            if (rating > 0) '\u2605 ${rating.toStringAsFixed(1)}',
            if (address.isNotEmpty) address,
          ].join('  \u00b7  '),
          children: <Widget>[
            const SizedBox(height: 12),
            Row(crossAxisAlignment: CrossAxisAlignment.center, children: <Widget>[
              _vendorThumb(v, 64,
                  claimed: ((v['claimedBy'] ?? '') as String? ?? '').isNotEmpty,
                  verified: (v['verified'] as bool?) ?? false),
              const SizedBox(width: 14),
              Expanded(
                child: Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                  if (phone.isNotEmpty)
                    _pcB_chip(Icons.call_rounded, 'Call',
                        () => _openLink('tel:$phone')),
                  if (website.isNotEmpty)
                    _pcB_chip(Icons.language_rounded, 'Website',
                        () => _openLink(website)),
                  if (pageSlug.isNotEmpty)
                    _pcB_chip(
                        Icons.storefront_rounded,
                        'Lazo profile',
                        () => _openLink(
                            'https://meetlazo.com/$metroId/$slug/$pageSlug/')),
                ]),
              ),
            ]),
            if (unclaimed) ...<Widget>[
              const SizedBox(height: 14),
              _lzNote(Icons.schedule_rounded,
                  'This vendor hasn\u2019t joined Lazo yet. You can still reach out - we\u2019ll let them know a couple is waiting.'),
            ],
            _worksWithLine(v),
            const SizedBox(height: 14),
            _Press(
              onTap: () {
                Navigator.pop(ctx);
                _markHired(v);
              },
              child: Container(
                padding: const EdgeInsets.fromLTRB(14, 12, 10, 12),
                decoration: BoxDecoration(
                    color: _lzBg(Colors.white),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: vGreen.withOpacity(.55))),
                child: Row(children: <Widget>[
                  const Icon(Icons.check_circle_rounded, color: vGreen, size: 20),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text('We already hired them',
                              style: TextStyle(
                                  color: _lzFg(ink),
                                  fontSize: 14,
                                  fontWeight: FontWeight.w700)),
                          Text('Marks them booked in your plan',
                              style: TextStyle(
                                  color: _lzFg(muted), fontSize: 12)),
                        ]),
                  ),
                  Icon(Icons.chevron_right_rounded, color: _lzFg(muted)),
                ]),
              ),
            ),
          ],
          footer: Row(children: <Widget>[
            StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
              stream: _liveDoc('couple:$_cid', () => _coupleRef),
              initialData: _liveD['couple:$_cid']?.latest,
              builder: (BuildContext c2,
                  AsyncSnapshot<DocumentSnapshot<Map<String, dynamic>>> cs) {
                final bool on = _isSaved(cs.data?.data() ?? <String, dynamic>{},
                    (v['placeId'] ?? '').toString());
                return OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(
                      foregroundColor: _lzFg(on ? ivory : plum),
                      backgroundColor: _lzBg(on ? plum : Colors.transparent),
                      side: BorderSide(
                          color: _lzLine(on ? plum : gold.withOpacity(.7))),
                      minimumSize: const Size(0, 46),
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(13))),
                  onPressed: _h(() => _toggleSave(v)),
                  icon: Icon(
                      on ? Icons.favorite_rounded : Icons.favorite_border_rounded,
                      size: 18),
                  label: Text(on ? 'Saved' : 'Save',
                      style: const TextStyle(fontWeight: FontWeight.w700)),
                );
              },
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _lzActions(
                  primary: 'Check your date',
                  icon: Icons.mail_outline_rounded,
                  onPrimary: () {
                    Navigator.pop(ctx);
                    _sendInquiry(v);
                  }),
            ),
          ])),
    );
  }

"""))

# ---------------------------------------------------------------- _editWebsite
# The editor itself stays as it is (a full editor); the chrome around it gets
# the house header, a close that asks first, _lzConfirm for discard, and the
# _lzActions footer. Publish with no names used to close and silently drop
# every edit; it now says so in place and keeps the editor open.
REPS.append((
r"""    _wbKeys.clear();
    _wbJumpArmed = false;
    final bool? ok = await _lzDialog<bool>(""",
r"""    _wbKeys.clear();
    _wbJumpArmed = false;
    String pubErr = '';
    Future<void> discardSite(BuildContext c) async {
      final bool sure = await _lzConfirm('Discard your changes?',
          'Anything you changed here is lost. Publish keeps it.',
          confirm: 'Discard changes', cancel: 'Keep editing', danger: true);
      if (sure && c.mounted) {
        Navigator.pop(c, false);
      }
    }

    final bool? ok = await _lzDialog<bool>("""))

REPS.append((
r"""                   Text('Your wedding website',
                      style: TextStyle(
                          color: _lzFg(plum),
                          fontWeight: FontWeight.w700,
                          fontSize: 17)),
                  const SizedBox(height: 6),
                  _wbJumpBar(setD),""",
r"""                  Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Container(
                            width: 42,
                            height: 42,
                            decoration: BoxDecoration(
                                color: plumDeep,
                                borderRadius: BorderRadius.circular(13)),
                            child: const Icon(Icons.language_rounded,
                                color: gold, size: 21)),
                        const SizedBox(width: 13),
                        Expanded(
                          child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                const SizedBox(height: 2),
                                Text('Your wedding website',
                                    style: _serif(size: 25, height: 1.1)),
                                const SizedBox(height: 4),
                                Text(
                                    doc == null
                                        ? 'Fill in what you like. Publish puts it live.'
                                        : 'meetlazo.com/w/${doc.id}',
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: TextStyle(
                                        fontSize: 13.5,
                                        color: _lzFg(muted),
                                        height: 1.4)),
                              ]),
                        ),
                        IconButton(
                            tooltip: 'Close',
                            icon: Icon(Icons.close_rounded,
                                color: _lzFg(muted)),
                            onPressed: _h(() => discardSite(ctx2))),
                      ]),
                  const SizedBox(height: 10),
                  _wbJumpBar(setD),"""))

BLOCKS.append((
r"""                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: <Widget>[
                      TextButton(
                          onPressed: _h(() async {
                            // v140: ask before throwing the edits away""",
r"""    if (ok != true || joinedNames().isEmpty) {""",
r"""                  if (pubErr.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 10),
                      child: _lzNote(Icons.error_outline_rounded, pubErr),
                    ),
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.only(top: 12),
                    decoration: BoxDecoration(
                        border: Border(
                            top: BorderSide(
                                color: _lzLine(goldLine).withOpacity(.7)))),
                    child: _lzActions(
                        // v140: ask before throwing the edits away
                        secondary: 'Cancel',
                        onSecondary: () => discardSite(ctx2),
                        primary: doc == null ? 'Publish' : 'Publish changes',
                        icon: Icons.public_rounded,
                        onPrimary: () {
                          if (joinedNames().isEmpty) {
                            setD(() => pubErr =
                                'Add at least one name - it\u2019s the title of your site.');
                            return;
                          }
                          Navigator.pop(ctx2, true);
                        }),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
"""))
