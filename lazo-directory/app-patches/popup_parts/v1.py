# Popup pass part v1 (vendor dashboard) - JC-LAZO-POPUP-1014
# Rebuilds the popups in: _railStrip, _feedSheet, _railSheet, _railGoalDialog,
# _submitClaim, _addListing, _viewProof, _adminDeny, _epTryClose,
# _epUploadGalleryPhotos, _epAddPackage, _epAddFaq, _epPickPreferred,
# _reportBugSheet, _ideasSheet, _openSupportSheet, _deleteVendorAccount,
# _starterLibrarySheet, _starterPreviewSheet, _disconnectSquare,
# _addPaymentLink, _setDefaultRetainer.


def apply(s: str) -> str:
    def rep(old, new):
        nonlocal s
        assert s.count(old) == 1, (s.count(old), old[:80])
        s = s.replace(old, new)

    def func(sig):
        assert s.count(sig) == 1, (s.count(sig), sig)
        i = s.index(sig)
        j = s.index('\n  }\n', i) + len('\n  }')
        return s[i:j]

    def between(after, start, end):
        a = s.index(after)
        i = s.index(start, a)
        j = s.index(end, i)
        return s[i:j]

    # ------------------------------------------------------------ _railStrip
    rep(between('Widget _railStrip(', '      _lzSheet<void>(', '    Widget chip('),
        r"""      _lzSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: _lzBg(ivory),
        constraints: const BoxConstraints(maxWidth: 640),
        builder: (BuildContext c) => id == null
            ? _lzFrame(c,
                icon: Icons.dashboard_customize_rounded,
                title: 'Your widgets',
                subtitle: 'Hold one and drag it to change the order.',
                bodyPadding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
                children: <Widget>[_railStack(vendorId, vd, sky, cons)])
            : SafeArea(
                child: ConstrainedBox(
                  constraints: BoxConstraints(maxHeight: MediaQuery.of(c).size.height * .88),
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.fromLTRB(16, 10, 16, 16),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
                      _railBody(id, vendorId, vd, sky, cons),
                    ]),
                  ),
                ),
              ),
      );
    }

""")

    # ------------------------------------------------------------ _feedSheet
    rep(func('  void _feedSheet() {'), r"""  void _feedSheet() {
    if (_uid == null) return;
    // opening the feed reads it
    final List<QueryDocumentSnapshot<Map<String, dynamic>>> docs = _liveQ['feed:$_uid']?.latest?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[];
    final WriteBatch b = FirebaseFirestore.instance.batch();
    int n = 0;
    for (final QueryDocumentSnapshot<Map<String, dynamic>> d in docs) {
      if (d.data()['read'] == true) continue;
      b.update(d.reference, <String, dynamic>{'read': true, 'readAt': Timestamp.now()});
      n++;
    }
    if (n > 0) b.commit().catchError((Object _) {});
    _lzSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: _lzBg(ivory),
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext c) => StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
        stream: _feedStream(),
        initialData: _liveQ['feed:$_uid']?.latest,
        builder: (BuildContext c2, AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> s) {
          final List<QueryDocumentSnapshot<Map<String, dynamic>>> ds = s.data?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[];
          return ConstrainedBox(
            constraints: BoxConstraints(maxHeight: MediaQuery.of(c2).size.height * .82),
            child: _lzFrame(c2,
                icon: Icons.auto_awesome_rounded,
                title: 'From June',
                subtitle: ds.isEmpty ? 'What\u2019s new with your business.' : 'Tap one to open it.',
                bodyPadding: const EdgeInsets.fromLTRB(14, 10, 14, 18),
                children: ds.isEmpty
                    ? <Widget>[
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 26, horizontal: 12),
                          child: Column(children: <Widget>[
                            const Icon(Icons.notifications_none_rounded, color: gold, size: 34),
                            const SizedBox(height: 10),
                            Text('Nothing yet. New leads, bookings, payments and reviews land here and on your phone.',
                                textAlign: TextAlign.center,
                                style: TextStyle(color: _lzFg(muted), fontSize: 13.5, height: 1.45)),
                          ]),
                        ),
                      ]
                    : <Widget>[
                        for (final QueryDocumentSnapshot<Map<String, dynamic>> d in ds) _pv1_feedRow(c2, d.data()),
                      ]),
          );
        },
      ),
    );
  }

  Widget _pv1_feedRow(BuildContext c2, Map<String, dynamic> m) {
    final String thread = (m['thread'] ?? '').toString();
    final String openTo = (m['open'] ?? '').toString();
    final bool fresh = m['readAt'] == null && m['read'] != true;
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: _Press(
        scale: .985,
        onTap: () {
          Navigator.of(c2).pop();
          if (thread.isNotEmpty) {
            _railOpen(thread);
          } else if (openTo == 'reviews') {
            setState(() => _dashMode = 'studio');
          }
        },
        child: Container(
          padding: const EdgeInsets.fromLTRB(12, 11, 12, 11),
          decoration: BoxDecoration(
            color: fresh ? _lzBg(card) : Colors.transparent,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: fresh ? gold.withOpacity(.55) : _lzLine(goldLine).withOpacity(.6)),
          ),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(shape: BoxShape.circle, color: gold.withOpacity(.16), border: Border.all(color: gold.withOpacity(.5))),
              child: Icon(_feedIcon((m['kind'] ?? '').toString()), size: 18, color: gold),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.only(top: 1),
                child: Text((m['text'] ?? '').toString(),
                    maxLines: 3,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(color: _lzFg(ink), fontSize: 13.5, height: 1.35, fontWeight: fresh ? FontWeight.w700 : FontWeight.w500)),
              ),
            ),
            const SizedBox(width: 8),
            Column(crossAxisAlignment: CrossAxisAlignment.end, children: <Widget>[
              Text(_feedAgo(m['at']), style: TextStyle(color: _lzFg(muted), fontSize: 11.5)),
              if (fresh) ...<Widget>[
                const SizedBox(height: 6),
                Container(width: 8, height: 8, decoration: const BoxDecoration(color: gold, shape: BoxShape.circle)),
              ],
            ]),
          ]),
        ),
      ),
    );
  }""")

    # ------------------------------------------------------------ _railSheet
    rep(func('  void _railSheet() {'), r"""  void _railSheet() {
    _lzSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: _lzBg(ivory),
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext c) => StatefulBuilder(builder: (BuildContext c2, StateSetter setS) {
        final List<String> on = _rail.where(_railKnown).toList();
        final List<String> off = _kRailAll.map((List<String> r) => r[0]).where((String id) => !on.contains(id)).toList();
        Widget row(String id, bool enabled, {int? index}) {
          final List<String> r = _railTitle(id);
          return Container(
            key: ValueKey<String>('sheet-$id'),
            margin: const EdgeInsets.only(bottom: 6),
            decoration: BoxDecoration(
              color: enabled ? _lzBg(card) : Colors.transparent,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: _lzLine(goldLine)),
            ),
            child: ListTile(
              contentPadding: const EdgeInsets.fromLTRB(8, 2, 6, 2),
              leading: index == null
                  ? Icon(Icons.add_circle_outline_rounded, color: _lzFg(muted))
                  : ReorderableDragStartListener(index: index, child: Icon(Icons.drag_indicator_rounded, color: _lzFg(muted))),
              title: Text(r[1], style: TextStyle(color: _lzFg(plum), fontWeight: FontWeight.w700, fontSize: 14)),
              subtitle: Text(r[2], style: TextStyle(color: _lzFg(muted), fontSize: 12)),
              trailing: Switch(
                value: enabled,
                activeColor: Colors.white,
                activeTrackColor: vGreen,
                onChanged: (bool v) {
                  setS(() {});
                  setState(() {
                    if (v) {
                      _rail = <String>[...on, id];
                    } else {
                      _rail = on.where((String x) => x != id).toList();
                    }
                  });
                  _saveRail();
                },
              ),
            ),
          );
        }

        return ConstrainedBox(
          constraints: BoxConstraints(maxHeight: MediaQuery.of(c2).size.height * .86),
          child: _lzFrame(c2,
              icon: Icons.dashboard_customize_rounded,
              title: 'Customize widgets',
              subtitle: 'Switch them on or off. Drag the handle to reorder.',
              children: <Widget>[
                _lzSection('On your dashboard', trailing: '${on.length}'),
                if (on.isEmpty)
                  _lzNote(Icons.widgets_outlined, 'No widgets on yet. Switch one on below.')
                else
                  ReorderableListView(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    buildDefaultDragHandles: false,
                    onReorder: (int from, int to) {
                      if (to > from) to -= 1;
                      final String x = on.removeAt(from);
                      on.insert(to, x);
                      setS(() {});
                      setState(() => _rail = List<String>.from(on));
                      _saveRail();
                    },
                    children: <Widget>[for (int i = 0; i < on.length; i++) row(on[i], true, index: i)],
                  ),
                if (off.isNotEmpty) ...<Widget>[
                  _lzSection('More widgets', trailing: '${off.length}'),
                  for (final String id in off) row(id, false),
                ],
              ],
              footer: _lzActions(primary: 'Done', icon: Icons.check_rounded, onPrimary: () => Navigator.of(c2).pop())),
        );
      }),
    );
  }""")

    # ------------------------------------------------------------ _railGoalDialog
    rep(func('  Future<void> _railGoalDialog('), r"""  Future<void> _railGoalDialog(int year, num gB, num gR) async {
    final TextEditingController b = TextEditingController(text: gB > 0 ? '${gB.round()}' : '');
    final TextEditingController r = TextEditingController(text: gR > 0 ? '${gR.round()}' : '');
    bool open = true;
    bool busy = false;
    bool saved = false;
    String err = '';
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 480),
      builder: (BuildContext sc) => StatefulBuilder(builder: (BuildContext c, StateSetter set) {
        void up(VoidCallback f) {
          if (open) set(f);
        }

        Future<void> save() async {
          if (busy) return;
          if (_uid == null) {
            Navigator.pop(sc);
            return;
          }
          final num nb = num.tryParse(b.text.replaceAll(RegExp(r'[^0-9.]'), '')) ?? 0;
          final num nr = num.tryParse(r.text.replaceAll(RegExp(r'[^0-9.]'), '')) ?? 0;
          up(() {
            busy = true;
            err = '';
          });
          try {
            await FirebaseFirestore.instance.collection('users').doc(_uid).set(<String, dynamic>{
              'vendorGoals': <String, dynamic>{'$year': <String, dynamic>{'bookings': nb, 'revenue': nr}}
            }, SetOptions(merge: true));
            saved = true;
            if (open) Navigator.pop(sc);
          } catch (e) {
            if (!open) {
              _toast('Could not save the goal: ' + _errText(e));
              return;
            }
            up(() {
              busy = false;
              err = 'Couldn\u2019t save the goal: ' + _errText(e);
            });
          }
        }

        return _lzFrame(c,
            icon: Icons.flag_rounded,
            title: 'Your $year goal',
            subtitle: 'Your season widget tracks bookings and revenue against it.',
            children: <Widget>[
              const SizedBox(height: 14),
              TextField(
                  controller: b,
                  autofocus: true,
                  enabled: !busy,
                  keyboardType: TextInputType.number,
                  textInputAction: TextInputAction.next,
                  cursorColor: _lzFg(plum),
                  style: TextStyle(color: _lzFg(ink), fontSize: 15),
                  decoration: _onbDeco('Weddings to book', icon: Icons.favorite_border_rounded).copyWith(hintText: '30')),
              const SizedBox(height: 12),
              TextField(
                  controller: r,
                  enabled: !busy,
                  keyboardType: TextInputType.number,
                  textInputAction: TextInputAction.done,
                  onSubmitted: (_) => save(),
                  cursorColor: _lzFg(plum),
                  style: TextStyle(color: _lzFg(ink), fontSize: 15),
                  decoration: _onbDeco('Revenue goal', icon: Icons.payments_outlined).copyWith(hintText: '120000', prefixText: '\$ ')),
              _onbError(err),
            ],
            footer: _lzActions(
                secondary: 'Cancel',
                onSecondary: () => Navigator.pop(sc),
                primary: 'Save goal',
                icon: Icons.check_rounded,
                busy: busy,
                onPrimary: save));
      }),
    );
    open = false;
    if (saved) _toast('Goal saved.');
  }""")

    # ------------------------------------------------------------ _submitClaim
    rep(between('Future<void> _submitClaim(', '      await _lzDialog<void>(', '      return;\n    }\n\n    final TextEditingController bizEmailC'),
        r"""      await _lzSheet<void>(
        context: context,
        constraints: const BoxConstraints(maxWidth: 480),
        builder: (BuildContext ctx) => _lzFrame(ctx,
            icon: Icons.verified_user_rounded,
            title: 'Already claimed',
            subtitle: '$name is verified by its owner.',
            children: <Widget>[
              const SizedBox(height: 14),
              _lzNote(Icons.mail_outline_rounded,
                  'If it\u2019s yours, email vendors@meetlazo.com and our team will review the ownership.'),
            ],
            footer: _lzActions(
                primary: 'Got it',
                icon: Icons.check_rounded,
                onPrimary: () => Navigator.pop(ctx))),
      );
""")
    rep(between('Future<void> _submitClaim(', '                TextField(\n                    controller: bizEmailC,\n',
                '                    enabled: !busy,'),
        """                TextField(
                    controller: bizEmailC,
                    autofocus: true,
""")

    # ------------------------------------------------------------ _addListing
    rep(between('Future<void> _addListing()', '                TextField(\n                    controller: nameC,\n',
                '                    enabled: !busy,'),
        """                TextField(
                    controller: nameC,
                    autofocus: true,
""")

    # ------------------------------------------------------------ _viewProof
    rep(func('  Future<void> _viewProof('), r"""  Future<void> _viewProof(String proofPath) async {
    try {
      final String url =
          await FirebaseStorage.instance.ref(proofPath).getDownloadURL();
      if (proofPath.toLowerCase().endsWith('.pdf')) {
        await _openUrl(url);
        return;
      }
      if (!mounted) {
        return;
      }
      await _lzDialog<void>(
        context: context,
        barrierColor: Colors.black.withOpacity(.82),
        builder: (BuildContext ctx) {
          final Size sz = MediaQuery.of(ctx).size;
          return SafeArea(
            child: Center(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Material(
                  color: Colors.transparent,
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 900),
                    child: Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
                      Row(children: <Widget>[
                        const Icon(Icons.verified_user_rounded, color: gold, size: 18),
                        const SizedBox(width: 8),
                        const Expanded(
                            child: Text('Proof of ownership',
                                style: TextStyle(color: ivory, fontSize: 15, fontWeight: FontWeight.w700))),
                        IconButton(
                            tooltip: 'Close',
                            onPressed: _h(() => Navigator.pop(ctx)),
                            icon: const Icon(Icons.close_rounded, color: ivory)),
                      ]),
                      const SizedBox(height: 6),
                      ConstrainedBox(
                        constraints: BoxConstraints(maxHeight: sz.height * .72),
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(14),
                          child: InteractiveViewer(
                            maxScale: 5,
                            child: Image.network(
                              url,
                              fit: BoxFit.contain,
                              loadingBuilder: (BuildContext c, Widget child, ImageChunkEvent? p) => p == null
                                  ? child
                                  : const SizedBox(
                                      width: 220,
                                      height: 220,
                                      child: Center(child: CircularProgressIndicator(color: gold))),
                              errorBuilder: (BuildContext c, Object e, StackTrace? st) => Container(
                                width: 300,
                                padding: const EdgeInsets.all(24),
                                color: plumDeep,
                                child: const Text('Couldn\u2019t load this image.',
                                    textAlign: TextAlign.center,
                                    style: TextStyle(color: ivory, fontSize: 14)),
                              ),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(height: 10),
                      Text('Pinch or scroll to zoom.',
                          style: TextStyle(color: ivory.withOpacity(.7), fontSize: 12.5)),
                    ]),
                  ),
                ),
              ),
            ),
          );
        },
      );
    } catch (e) {
      _toast('Could not open proof document.');
      debugPrint('LAZO admin proof error: ' + e.toString());
    }
  }""")

    # ------------------------------------------------------------ _adminDeny
    rep(func('  Future<void> _adminDeny('), r"""  Future<void> _adminDeny(String collection, String requestId) async {
    final TextEditingController reasonC = TextEditingController();
    bool open = true;
    bool busy = false;
    bool done = false;
    String err = '';
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 520),
      builder: (BuildContext sc) => StatefulBuilder(builder: (BuildContext ctx, StateSetter set) {
        void up(VoidCallback f) {
          if (open) set(f);
        }

        Future<void> deny() async {
          up(() {
            busy = true;
            err = '';
          });
          try {
            await FirebaseFirestore.instance
                .collection(collection)
                .doc(requestId)
                .update({
              'status': 'denied',
              'denyReason': reasonC.text.trim(),
              'approvedBy': 'admin',
              'actedByUid': _uid,
            });
            done = true;
            if (open) Navigator.pop(sc);
          } catch (e) {
            debugPrint('LAZO admin deny error: ' + e.toString());
            if (!open) {
              _toast('Deny failed - try again.');
              return;
            }
            up(() {
              busy = false;
              err = 'Deny failed. Try again.';
            });
          }
        }

        return _lzFrame(ctx,
            icon: Icons.block_rounded,
            title: 'Deny this request?',
            subtitle: 'The vendor sees the reason you give.',
            children: <Widget>[
              const SizedBox(height: 14),
              TextField(
                controller: reasonC,
                autofocus: true,
                enabled: !busy,
                minLines: 3,
                maxLines: 5,
                textCapitalization: TextCapitalization.sentences,
                cursorColor: _lzFg(plum),
                style: TextStyle(color: _lzFg(ink), fontSize: 15),
                decoration: _onbDeco('Reason', icon: Icons.notes_rounded)
                    .copyWith(hintText: 'e.g. The proof doesn\u2019t show the business name.'),
              ),
              _onbError(err),
            ],
            footer: _lzActions(
                secondary: 'Cancel',
                onSecondary: () => Navigator.pop(sc),
                primary: 'Deny request',
                danger: true,
                icon: Icons.block_rounded,
                busy: busy,
                onPrimary: deny));
      }),
    );
    open = false;
    if (done) _toast('Denied.');
  }""")

    # ------------------------------------------------------------ _epTryClose
    rep(func('  void _epTryClose() {'), r"""  void _epTryClose() {
    if (_epFingerprint() == _epBaseline) {
      setState(() => _editingProfile = false);
      return;
    }
    _lzConfirm('Discard your changes?',
            'You\u2019ve edited your profile since it was last saved. Leaving now throws those edits away.',
            confirm: 'Discard changes', cancel: 'Keep editing', danger: true)
        .then((bool ok) {
      if (ok && mounted) setState(() => _editingProfile = false);
    });
  }""")

    # ------------------------------------------------------------ _epUploadGalleryPhotos
    rep(between('Future<void> _epUploadGalleryPhotos()', '        bool proceed = false;\n', '        files = files.sublist(0, remaining);'),
        r"""        final bool proceed = await _lzConfirm(
            'Upload the first $remaining?',
            'You picked ${files.length} photos, and the gallery has room for $remaining more (of $cap).',
            confirm: 'Upload $remaining',
            cancel: 'Cancel',
            icon: Icons.photo_library_rounded);
        if (!proceed) {
          return;
        }
""")

    # ------------------------------------------------------------ _epAddPackage
    rep(func('  Future<void> _epAddPackage() async {'), r"""  Future<void> _epAddPackage() async {
    if (_epPackages.length >= 6) {
      _toast('Up to 6 packages on a profile.');
      return;
    }
    final TextEditingController nameC = TextEditingController();
    final TextEditingController priceC = TextEditingController();
    final TextEditingController incC = TextEditingController();
    final TextEditingController hoursC = TextEditingController();
    final TextEditingController offPeakC = TextEditingController();
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext ctx) => StatefulBuilder(builder: (BuildContext c, StateSetter set) {
        final bool ok = nameC.text.trim().isNotEmpty && priceC.text.trim().isNotEmpty;
        void add() {
          if (nameC.text.trim().isEmpty || priceC.text.trim().isEmpty) {
            return;
          }
          setState(() {
            _epPackages.add(<String, dynamic>{
              'name': nameC.text.trim(),
              'price': priceC.text.trim(),
              'offPeak': offPeakC.text.trim(),
              'hours': hoursC.text.trim(),
              'includes': incC.text.trim(),
            });
          });
          Navigator.pop(ctx);
        }

        Widget field(TextEditingController ctl, String label, String hint, {bool first = false, bool multi = false}) => TextField(
            controller: ctl,
            autofocus: first,
            minLines: multi ? 3 : 1,
            maxLines: multi ? 6 : 1,
            keyboardType: multi ? TextInputType.multiline : TextInputType.text,
            textInputAction: multi ? TextInputAction.newline : TextInputAction.next,
            textCapitalization: TextCapitalization.sentences,
            onChanged: (_) => set(() {}),
            cursorColor: _lzFg(plum),
            style: TextStyle(color: _lzFg(ink), fontSize: 14.5),
            decoration: _epDeco(label, hint));

        return _lzFrame(c,
            icon: Icons.sell_rounded,
            title: 'Add a package',
            subtitle: 'Couples compare these on your profile.',
            children: <Widget>[
              const SizedBox(height: 14),
              field(nameC, 'Package name', 'e.g. The Verse', first: true),
              _lzSection('Pricing'),
              field(priceC, 'Peak pricing', 'e.g. \u00242,000 or \u00242,000\u2013\u00242,400'),
              const SizedBox(height: 10),
              field(offPeakC, 'Off-peak pricing (optional)', 'Leave blank if the same year-round'),
              _lzSection('Details'),
              field(hoursC, 'Hours (optional)', 'e.g. 8 hours'),
              const SizedBox(height: 10),
              field(incC, 'What\u2019s included', 'One item per line', multi: true),
            ],
            footer: _lzActions(
                secondary: 'Cancel',
                onSecondary: () => Navigator.pop(ctx),
                primary: 'Add package',
                icon: Icons.add_rounded,
                onPrimary: ok ? add : null));
      }),
    );
  }""")

    # ------------------------------------------------------------ _epAddFaq
    rep(func('  Future<void> _epAddFaq() async {'), r"""  Future<void> _epAddFaq() async {
    if (_epFaqs.length >= 15) {
      _toast('Up to 15 FAQs on a profile.');
      return;
    }
    final TextEditingController qC = TextEditingController();
    final TextEditingController aC = TextEditingController();
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 540),
      builder: (BuildContext ctx) => StatefulBuilder(builder: (BuildContext c, StateSetter set) {
        final bool ok = qC.text.trim().isNotEmpty && aC.text.trim().isNotEmpty;
        void add() {
          if (qC.text.trim().isEmpty || aC.text.trim().isEmpty) {
            return;
          }
          setState(() {
            _epFaqs.add(<String, dynamic>{
              'q': qC.text.trim(),
              'a': aC.text.trim(),
            });
          });
          Navigator.pop(ctx);
        }

        return _lzFrame(c,
            icon: Icons.quiz_rounded,
            title: 'Add an FAQ',
            subtitle: 'Answer what couples ask you most.',
            children: <Widget>[
              const SizedBox(height: 14),
              TextField(
                  controller: qC,
                  autofocus: true,
                  textInputAction: TextInputAction.next,
                  textCapitalization: TextCapitalization.sentences,
                  onChanged: (_) => set(() {}),
                  cursorColor: _lzFg(plum),
                  style: TextStyle(color: _lzFg(ink), fontSize: 14.5),
                  decoration: _epDeco('Question', 'e.g. Are you insured?')),
              const SizedBox(height: 12),
              TextField(
                  controller: aC,
                  minLines: 3,
                  maxLines: 6,
                  keyboardType: TextInputType.multiline,
                  textCapitalization: TextCapitalization.sentences,
                  onChanged: (_) => set(() {}),
                  cursorColor: _lzFg(plum),
                  style: TextStyle(color: _lzFg(ink), fontSize: 14.5),
                  decoration: _epDeco('Your answer', 'A sentence or two is plenty')),
            ],
            footer: _lzActions(
                secondary: 'Cancel',
                onSecondary: () => Navigator.pop(ctx),
                primary: 'Add FAQ',
                icon: Icons.add_rounded,
                onPrimary: ok ? add : null));
      }),
    );
  }""")

    # ------------------------------------------------------------ _epPickPreferred
    rep(func('  Future<void> _epPickPreferred() async {'), r"""  Future<void> _epPickPreferred() async {
    if (_epPreferred.length >= 6) {
      _toast('Up to 6 preferred vendors.');
      return;
    }
    final TextEditingController searchC = TextEditingController();
    List<Map<String, dynamic>> results = <Map<String, dynamic>>[];
    bool searching = false;
    bool searched = false;
    bool open = true;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 520),
      builder: (BuildContext ctx) => StatefulBuilder(builder: (BuildContext c, StateSetter setD) {
        void up(VoidCallback f) {
          if (open) setD(f);
        }

        Future<void> run(String q) async {
          final String raw = q.trim();
          if (raw.length < 2 || searching) {
            return;
          }
          up(() => searching = true);
          List<Map<String, dynamic>> found = <Map<String, dynamic>>[];
          try {
            final String tq = _tcV(raw);
            final QuerySnapshot<Map<String, dynamic>> snap =
                await FirebaseFirestore.instance
                    .collection('vendors')
                    .orderBy('name')
                    .startAt(<String>[tq])
                    .endAt(<String>['$tq\uf8ff'])
                    .limit(12)
                    .get();
            for (final QueryDocumentSnapshot<Map<String, dynamic>> d
                in snap.docs) {
              final Map<String, dynamic> vd = d.data();
              if (d.id == _epVendorId) {
                continue;
              }
              found.add(<String, dynamic>{
                'placeId': d.id,
                'name': vd['name'] ?? '',
                'metroId': vd['metroId'] ?? '',
              });
            }
          } catch (e) {
            found = <Map<String, dynamic>>[];
          }
          up(() {
            results = found;
            searching = false;
            searched = true;
          });
        }

        Widget resultRow(Map<String, dynamic> r) {
          final String metro = _metroLabel(r['metroId'].toString());
          return Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: _Press(
              scale: .985,
              onTap: () {
                setState(() {
                  _epPreferred.add(r);
                });
                Navigator.pop(ctx);
              },
              child: Container(
                padding: const EdgeInsets.fromLTRB(14, 12, 12, 12),
                decoration: BoxDecoration(
                    color: _lzBg(card),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: _lzLine(goldLine))),
                child: Row(children: <Widget>[
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                      Text(r['name'].toString(),
                          style: TextStyle(color: _lzFg(plum), fontWeight: FontWeight.w700, fontSize: 14.5)),
                      const SizedBox(height: 2),
                      Text(metro.isEmpty ? r['metroId'].toString() : metro,
                          style: TextStyle(fontSize: 12, color: _lzFg(muted))),
                    ]),
                  ),
                  const Icon(Icons.add_circle_outline_rounded, color: gold, size: 22),
                ]),
              ),
            ),
          );
        }

        return _lzFrame(c,
            icon: Icons.handshake_rounded,
            title: 'Add a preferred vendor',
            subtitle: 'Recommend vendors you love working with.',
            headerExtra: TextField(
              controller: searchC,
              autofocus: true,
              textInputAction: TextInputAction.search,
              onSubmitted: run,
              cursorColor: _lzFg(plum),
              style: TextStyle(color: _lzFg(ink), fontSize: 14.5),
              decoration: _epDeco('Search by business name', 'Any city').copyWith(
                  suffixIcon: IconButton(
                      tooltip: 'Search',
                      icon: Icon(Icons.search_rounded, color: _lzFg(plum)),
                      onPressed: _h(() => run(searchC.text)))),
            ),
            children: <Widget>[
              const SizedBox(height: 14),
              if (searching)
                _lzBusy('Searching Lazo\u2026')
              else if (!searched)
                _lzNote(Icons.search_rounded, 'Type at least two letters of their business name, then search.')
              else if (results.isEmpty)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 18),
                  child: Column(children: <Widget>[
                    const Icon(Icons.search_off_rounded, color: gold, size: 32),
                    const SizedBox(height: 8),
                    Text('No vendors start with that name. Try the first word of it.',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: _lzFg(muted), fontSize: 13.5, height: 1.4)),
                  ]),
                )
              else ...<Widget>[
                _lzSection('Tap to add', trailing: '${results.length} found'),
                for (final Map<String, dynamic> r in results) resultRow(r),
              ],
            ]);
      }),
    );
    open = false;
  }""")

    # ------------------------------------------------------------ _reportBugSheet
    rep(func('  Future<void> _reportBugSheet() async {'), r"""  Future<void> _reportBugSheet() async {
    final User? u = FirebaseAuth.instance.currentUser;
    if (u == null) return;
    String area = '';
    String severity = 'annoying';
    final TextEditingController whatC = TextEditingController();
    final TextEditingController stepsC = TextEditingController();
    Uint8List? shot;
    String shotName = '';
    bool busy = false;
    bool open = true;
    bool sent = false;
    String err = '';
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext sc) => StatefulBuilder(builder: (BuildContext ctx, StateSetter setD) {
        void up(VoidCallback f) {
          if (open) setD(f);
        }

        Future<void> pickShot() async {
          try {
            final FilePickerResult? r =
                await FilePicker.platform.pickFiles(type: FileType.image, withData: true);
            if (r == null || r.files.isEmpty || r.files.first.bytes == null) return;
            if (r.files.first.bytes!.length > 10 * 1024 * 1024) {
              up(() => err = 'That screenshot is over 10MB.');
              return;
            }
            up(() {
              shot = r.files.first.bytes;
              shotName = r.files.first.name;
              err = '';
            });
          } catch (_) {
            up(() => err = 'Couldn\u2019t open your files.');
          }
        }

        Future<void> send() async {
          if (whatC.text.trim().length < 8) {
            up(() => err = 'Tell us a little more about what happened.');
            return;
          }
          up(() {
            busy = true;
            err = '';
          });
          String shotUrl = '';
          if (shot != null) {
            try {
              final String safe = shotName.replaceAll(RegExp(r'[^A-Za-z0-9._-]'), '_');
              final String path =
                  'support/${u.uid}/${DateTime.now().millisecondsSinceEpoch}_$safe';
              final Reference ref = FirebaseStorage.instance.ref(path);
              await ref.putData(
                  shot!,
                  SettableMetadata(
                      contentType: safe.toLowerCase().endsWith('.png') ? 'image/png' : 'image/jpeg'));
              shotUrl = await ref.getDownloadURL();
            } catch (e) {
              debugPrint('LAZO bug shot: ' + e.toString());
              // Ticket still goes; the screenshot is a bonus.
            }
          }
          final String what = whatC.text.trim();
          final String subject =
              '${area.isEmpty ? 'Bug' : area}: ${what.length > 60 ? what.substring(0, 60) + '\u2026' : what}';
          final Map<String, dynamic> cx = _supportContext(area);
          cx['severity'] = severity;
          cx['steps'] = stepsC.text.trim();
          if (shotUrl.isNotEmpty) cx['screenshotUrl'] = shotUrl;
          try {
            await FirebaseFirestore.instance.collection('supportTickets').add(<String, dynamic>{
              'role': 'vendor',
              'uid': u.uid,
              'email': u.email ?? '',
              'category': 'Report a bug',
              'subject': subject,
              'message': what,
              'vendorName': '',
              'status': 'open',
              'createdAt': FieldValue.serverTimestamp(),
              'context': cx,
            });
            sent = true;
            if (open) Navigator.pop(sc);
          } catch (e) {
            if (!open) {
              _toast('Could not send that - try again.');
              return;
            }
            up(() {
              busy = false;
              err = 'Couldn\u2019t send that. Check your connection and try again.';
            });
          }
        }

        final Uint8List? thumb = shot;
        return _lzFrame(ctx,
            icon: Icons.bug_report_rounded,
            title: 'Report a bug',
            subtitle: 'We read every one, and the fix usually ships within days.',
            children: <Widget>[
              _lzSection('Where'),
              Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
                for (final String a in kBugAreas)
                  _fbChip(a, area == a, () => up(() => area = a)),
              ]),
              _lzSection('How bad'),
              Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
                for (final List<String> sv in kBugSeverity)
                  _fbChip(sv[1], severity == sv[0], () => up(() => severity = sv[0]), sub: sv[2]),
              ]),
              _lzSection('What happened'),
              TextField(
                controller: whatC,
                enabled: !busy,
                cursorColor: _lzFg(plum),
                minLines: 2,
                maxLines: 5,
                textCapitalization: TextCapitalization.sentences,
                onChanged: (_) => up(() => err = ''),
                style: TextStyle(color: _lzFg(ink), fontSize: 14),
                decoration: _fbDeco('What happened?',
                        hint: 'The invoice reminder sent twice to the same couple.')
                    .copyWith(helperText: 'A sentence or two is plenty.'),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: stepsC,
                enabled: !busy,
                cursorColor: _lzFg(plum),
                minLines: 1,
                maxLines: 4,
                textCapitalization: TextCapitalization.sentences,
                style: TextStyle(color: _lzFg(ink), fontSize: 14),
                decoration: _fbDeco('How can we see it too? (optional)',
                    hint: 'Open the thread, tap Remind, wait a minute\u2026'),
              ),
              const SizedBox(height: 12),
              _Press(
                scale: .985,
                onTap: busy ? null : pickShot,
                child: Container(
                  padding: const EdgeInsets.fromLTRB(12, 10, 6, 10),
                  decoration: BoxDecoration(
                      color: _lzBg(card),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: thumb == null ? _lzLine(goldLine) : vGreen.withOpacity(.55))),
                  child: Row(children: <Widget>[
                    ClipRRect(
                      borderRadius: BorderRadius.circular(10),
                      child: thumb == null
                          ? Container(
                              width: 44,
                              height: 44,
                              color: plumDeep,
                              child: const Icon(Icons.add_photo_alternate_outlined, color: gold, size: 21))
                          : Image.memory(thumb, width: 44, height: 44, fit: BoxFit.cover),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                        Text(thumb == null ? 'Add a screenshot' : shotName,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(color: _lzFg(plum), fontSize: 14, fontWeight: FontWeight.w700)),
                        Text(thumb == null ? 'Optional, up to 10MB' : 'Attached',
                            style: TextStyle(
                                color: thumb == null ? _lzFg(muted) : vGreen, fontSize: 12, fontWeight: FontWeight.w600)),
                      ]),
                    ),
                    if (thumb != null)
                      IconButton(
                          tooltip: 'Remove',
                          onPressed: _h(busy ? null : () => up(() => shot = null)),
                          icon: Icon(Icons.close_rounded, color: _lzFg(muted), size: 19)),
                  ]),
                ),
              ),
              const SizedBox(height: 12),
              _lzNote(Icons.info_outline_rounded,
                  'We attach your plan, build ${kBuildId.split('-').last}, ${kIsWeb ? 'browser' : 'device'} and screen size, so you don\u2019t have to.'),
              _onbError(err),
            ],
            footer: _lzActions(
                secondary: 'Cancel',
                onSecondary: () => Navigator.pop(sc),
                primary: 'Send report',
                icon: Icons.send_rounded,
                busy: busy,
                onPrimary: whatC.text.trim().length < 8 ? null : send));
      }),
    );
    open = false;
    if (sent) {
      _toast(severity == 'blocks'
          ? 'Got it - marked as blocking. We\u2019ll email you as soon as it\u2019s fixed.'
          : 'Thanks - logged. We\u2019ll email you when it\u2019s fixed.');
    }
  }""")

    # ------------------------------------------------------------ _ideasSheet
    rep(func('  Future<void> _ideasSheet() async {'), r"""  Future<void> _ideasSheet() async {
    final User? u = FirebaseAuth.instance.currentUser;
    if (u == null) return;
    String tab = 'top';
    bool composing = false;
    bool open = true;
    Widget? composer;
    await _lzSheet<void>(
      context: context,
      isScrollControlled: true,
      constraints: const BoxConstraints(maxWidth: 720),
      builder: (BuildContext sc) => StatefulBuilder(
        builder: (BuildContext ctx, StateSetter setS) {
          void up(VoidCallback f) {
            if (open) setS(f);
          }

          // the composer is built once per visit so its text survives the
          // keyboard opening (which rebuilds this sheet)
          void compose(bool on) => up(() {
                composing = on;
                composer = on ? _ideaComposer(u, () => compose(false)) : null;
              });

          final Size scr = MediaQuery.of(ctx).size;
          return SizedBox(
            height: scr.height * (scr.width >= _lzWideAt ? .8 : .88),
            child: _lzFrame(ctx,
                fill: true,
                icon: Icons.lightbulb_rounded,
                title: composing ? 'Suggest an idea' : 'Ideas',
                subtitle: composing
                    ? 'One line is enough. Add the why if you like.'
                    : 'What would make Lazo better for your business? Vote for what you\u2019d use.',
                onBack: composing ? () => compose(false) : null,
                headerExtra: composing
                    ? null
                    : SingleChildScrollView(
                        scrollDirection: Axis.horizontal,
                        child: Row(children: <Widget>[
                          for (final List<String> t in const <List<String>>[
                            <String>['top', 'Most wanted'],
                            <String>['new', 'Newest'],
                            <String>['mine', 'Mine'],
                            <String>['shipped', 'Shipped'],
                          ])
                            Padding(
                              padding: const EdgeInsets.only(right: 6),
                              child: _fbChip(t[1], tab == t[0], () => up(() => tab = t[0])),
                            ),
                        ]),
                      ),
                bodyPadding: composing
                    ? const EdgeInsets.fromLTRB(4, 8, 4, 18)
                    : const EdgeInsets.fromLTRB(16, 12, 16, 22),
                children: composing
                    ? <Widget>[composer ?? const SizedBox.shrink()]
                    : <Widget>[
                        StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
                          stream: _ideasRef.orderBy('createdAt', descending: true).limit(200).snapshots(),
                          builder: (BuildContext c, AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> s) {
                            List<QueryDocumentSnapshot<Map<String, dynamic>>> docs =
                                (s.data?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[]).toList();
                            if (tab == 'shipped') {
                              docs = docs
                                  .where((QueryDocumentSnapshot<Map<String, dynamic>> d) =>
                                      (d.data()['status'] ?? '') == 'shipped')
                                  .toList();
                            } else if (tab == 'mine') {
                              docs = docs
                                  .where((QueryDocumentSnapshot<Map<String, dynamic>> d) => d.data()['uid'] == u.uid)
                                  .toList();
                            } else {
                              docs = docs
                                  .where((QueryDocumentSnapshot<Map<String, dynamic>> d) =>
                                      (d.data()['status'] ?? '') != 'shipped' &&
                                      (d.data()['status'] ?? '') != 'declined')
                                  .toList();
                              if (tab == 'top') {
                                docs.sort((QueryDocumentSnapshot<Map<String, dynamic>> a,
                                        QueryDocumentSnapshot<Map<String, dynamic>> b) =>
                                    (((b.data()['votes'] ?? 0) as num).toInt())
                                        .compareTo(((a.data()['votes'] ?? 0) as num).toInt()));
                              }
                            }
                            if (s.data == null && s.connectionState == ConnectionState.waiting) {
                              return _lzBusy('Loading the board\u2026');
                            }
                            if (docs.isEmpty) {
                              return Padding(
                                padding: const EdgeInsets.symmetric(vertical: 28, horizontal: 12),
                                child: Column(children: <Widget>[
                                  const Icon(Icons.lightbulb_outline_rounded, color: gold, size: 34),
                                  const SizedBox(height: 8),
                                  Text(
                                      tab == 'mine'
                                          ? 'You haven\u2019t suggested anything yet.'
                                          : tab == 'shipped'
                                              ? 'Nothing shipped from the board yet - the first ones are coming.'
                                              : 'The board is empty. Yours would be the first.',
                                      textAlign: TextAlign.center,
                                      style: TextStyle(color: _lzFg(muted), fontSize: 13.5, height: 1.4)),
                                ]),
                              );
                            }
                            return Column(
                                crossAxisAlignment: CrossAxisAlignment.stretch,
                                children: <Widget>[
                                  for (final QueryDocumentSnapshot<Map<String, dynamic>> d in docs) _ideaCard(d, u.uid),
                                ]);
                          },
                        ),
                      ],
                footer: composing
                    ? null
                    : _lzActions(
                        primary: 'Suggest an idea',
                        icon: Icons.add_rounded,
                        onPrimary: () => compose(true))),
          );
        },
      ),
    );
    open = false;
  }""")

    # ------------------------------------------------------------ _openSupportSheet
    rep(func('  Future<void> _openSupportSheet('), r"""  Future<void> _openSupportSheet(
      {String initialCategory = 'Report a couple',
      String initialSubject = ''}) async {
    final User? u = FirebaseAuth.instance.currentUser;
    if (u == null) return;
    String cat = initialCategory;
    final TextEditingController subjC =
        TextEditingController(text: initialSubject);
    final TextEditingController msgC = TextEditingController();
    bool busy = false;
    bool open = true;
    bool sent = false;
    String err = '';
    const List<String> cats = <String>[
      'Report a couple',
      'Report a bug',
      'Billing question',
      'Verification',
      'Something else',
    ];
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 540),
      builder: (BuildContext sc) => StatefulBuilder(builder: (BuildContext ctx, StateSetter setD) {
        void up(VoidCallback f) {
          if (open) setD(f);
        }

        final bool ready = subjC.text.trim().isNotEmpty && msgC.text.trim().isNotEmpty;
        Future<void> send() async {
          if (subjC.text.trim().isEmpty || msgC.text.trim().isEmpty) {
            up(() => err = 'Add a subject and a message first.');
            return;
          }
          up(() {
            busy = true;
            err = '';
          });
          try {
            await FirebaseFirestore.instance.collection('supportTickets').add(<String, dynamic>{
              'role': 'vendor',
              'uid': u.uid,
              'email': u.email ?? '',
              'category': cat,
              'subject': subjC.text.trim(),
              'message': msgC.text.trim(),
              'vendorName': '',
              'status': 'open',
              'createdAt': FieldValue.serverTimestamp(),
              'context': <String, dynamic>{
                'source': 'vendor_dashboard',
                'build': kBuildId,
                'vendorId': _vendorIdCache,
              },
            });
            sent = true;
            if (open) Navigator.pop(sc);
          } catch (_) {
            if (!open) {
              _toast('Could not send the ticket. Try again.');
              return;
            }
            up(() {
              busy = false;
              err = 'Couldn\u2019t send the ticket. Check your connection and try again.';
            });
          }
        }

        return _lzFrame(ctx,
            icon: Icons.support_agent_rounded,
            title: 'Support',
            subtitle: 'Tell us what\u2019s going on. We reply by email.',
            children: <Widget>[
              _lzSection('What is this about?'),
              Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                for (final String c in cats)
                  _onbChip(label: c, selected: cat == c, onTap: busy ? null : () => up(() => cat = c)),
              ]),
              _lzSection('Your message'),
              TextField(
                controller: subjC,
                autofocus: initialSubject.isEmpty,
                enabled: !busy,
                textInputAction: TextInputAction.next,
                textCapitalization: TextCapitalization.sentences,
                onChanged: (_) => up(() => err = ''),
                cursorColor: _lzFg(plum),
                style: TextStyle(color: _lzFg(ink), fontSize: 14),
                decoration: _fbDeco('Subject'),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: msgC,
                autofocus: initialSubject.isNotEmpty,
                enabled: !busy,
                minLines: 4,
                maxLines: 8,
                textCapitalization: TextCapitalization.sentences,
                onChanged: (_) => up(() => err = ''),
                cursorColor: _lzFg(plum),
                style: TextStyle(color: _lzFg(ink), fontSize: 14),
                decoration: _fbDeco('Tell us what happened'),
              ),
              _onbError(err),
            ],
            footer: _lzActions(
                secondary: 'Cancel',
                onSecondary: () => Navigator.pop(sc),
                primary: 'Send',
                icon: Icons.send_rounded,
                busy: busy,
                onPrimary: ready ? send : null));
      }),
    );
    open = false;
    if (sent) _toast('Ticket sent \u2713 We\u2019ll get back to you by email.');
  }""")

    # ------------------------------------------------------------ _deleteVendorAccount
    rep(func('  Future<void> _deleteVendorAccount() async {'), r"""  Future<void> _deleteVendorAccount() async {
    final User? u = FirebaseAuth.instance.currentUser;
    if (u == null) return;
    bool open = true;
    bool busy = false;
    bool done = false;
    String err = '';
    Future<void>? job;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 500),
      builder: (BuildContext sc) => StatefulBuilder(builder: (BuildContext ctx, StateSetter set) {
        void up(VoidCallback f) {
          if (open) set(f);
        }

        void fail(String m) {
          if (!open) {
            _toast(m);
            return;
          }
          up(() {
            busy = false;
            err = m;
          });
        }

        Future<void> go() async {
          up(() {
            busy = true;
            err = '';
          });
          try {
            await FirebaseFunctions.instance
                .httpsCallable('deleteMyVendorAccount',
                    options:
                        HttpsCallableOptions(timeout: const Duration(seconds: 300)))
                .call(<String, dynamic>{});
            try {
              await FirebaseAuth.instance.signOut();
            } catch (_) {}
            done = true;
            if (open) Navigator.pop(sc);
          } on FirebaseFunctionsException catch (e) {
            fail(e.message ?? 'Could not delete the account. Try again.');
          } catch (_) {
            fail('Could not delete the account. Try again.');
          }
        }

        Widget gone(IconData ic, String t) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Row(children: <Widget>[
                Icon(ic, size: 18, color: _lzFg(const Color(0xFFB3261E))),
                const SizedBox(width: 12),
                Expanded(child: Text(t, style: TextStyle(color: _lzFg(ink), fontSize: 14, height: 1.35))),
              ]),
            );

        return _lzFrame(ctx,
            icon: Icons.warning_amber_rounded,
            title: 'Delete your account?',
            subtitle: 'This can\u2019t be undone.',
            children: busy
                ? <Widget>[
                    const SizedBox(height: 14),
                    _lzBusy('Deleting your account. This can take a minute - keep this open.'),
                  ]
                : <Widget>[
                    _lzSection('What goes'),
                    gone(Icons.lock_outline_rounded, 'Your login'),
                    gone(Icons.photo_library_outlined, 'Your uploads and templates'),
                    gone(Icons.edit_note_rounded, 'Everything you added to your profile'),
                    gone(Icons.storefront_outlined, 'Your claim on the listing'),
                    gone(Icons.workspace_premium_outlined, 'Any active plan - it\u2019s cancelled'),
                    _onbError(err),
                  ],
            footer: _lzActions(
                secondary: 'Keep my account',
                onSecondary: () => Navigator.pop(sc),
                primary: 'Delete forever',
                danger: true,
                busy: busy,
                onPrimary: () {
                  job = go();
                }));
      }),
    );
    open = false;
    if (job != null) await job;
    if (!done || !mounted) return;
    context.goNamed('Welcome');
  }""")

    # ------------------------------------------------------------ _starterLibrarySheet
    rep(func('  Future<void> _starterLibrarySheet('), r"""  Future<void> _starterLibrarySheet(String vendorId) async {
    // Show only the starters written for this vendor's craft
    List<String> myCats = <String>[];
    try {
      final DocumentSnapshot<Map<String, dynamic>> vSnap =
          await FirebaseFirestore.instance
              .collection('vendors')
              .doc(vendorId)
              .get();
      myCats = List<String>.from(
          (vSnap.data()?['categories'] as List?) ?? const <dynamic>[]);
    } catch (_) {}
    final List<Map<String, String>> relevant =
        kStarterTemplates.where((Map<String, String> t) {
      final List<String> cats = kStarterCats[t['id']] ?? const <String>[];
      if (myCats.isEmpty) {
        return true;
      }
      return cats.any((String c) => myCats.contains(c));
    }).toList();
    if (!mounted) {
      return;
    }
    _lzSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: _lzBg(ivory),
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext ctx) => _lzFrame(ctx,
          icon: Icons.auto_stories_rounded,
          title: 'Starter templates',
          subtitle: 'Written for wedding vendors. A head start to personalize and review - not legal advice.',
          children: <Widget>[
            const SizedBox(height: 14),
            if (relevant.isEmpty) ...<Widget>[
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 14),
                child: Column(children: <Widget>[
                  const Icon(Icons.auto_stories_outlined, color: gold, size: 32),
                  const SizedBox(height: 8),
                  Text('Starters for your category are on the way.',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: _lzFg(muted), fontSize: 13.5, height: 1.4)),
                ]),
              ),
              _lzNote(Icons.auto_awesome_rounded,
                  'Meanwhile, import the contract you already use - June converts it in about a minute.'),
            ],
            for (final Map<String, String> t in relevant)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: _Press(
                  scale: .985,
                  onTap: () => _starterPreviewSheet(vendorId, t),
                  child: Container(
                    padding: const EdgeInsets.fromLTRB(14, 13, 10, 13),
                    decoration: BoxDecoration(
                        color: _lzBg(card),
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: _lzLine(goldLine))),
                    child: Row(children: <Widget>[
                      Container(
                          width: 40,
                          height: 40,
                          decoration: BoxDecoration(color: plumDeep, borderRadius: BorderRadius.circular(12)),
                          child: const Icon(Icons.description_rounded, color: gold, size: 20)),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                          Text(t['name'] ?? '',
                              style: TextStyle(color: _lzFg(plum), fontSize: 14.5, fontWeight: FontWeight.w700)),
                          const SizedBox(height: 2),
                          Text(t['blurb'] ?? '',
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(fontSize: 12.5, color: _lzFg(muted), height: 1.35)),
                        ]),
                      ),
                      Icon(Icons.chevron_right_rounded, color: _lzFg(muted)),
                    ]),
                  ),
                ),
              ),
          ]),
    );
  }""")

    # ------------------------------------------------------------ _starterPreviewSheet
    rep(func('  void _starterPreviewSheet('), r"""  void _starterPreviewSheet(String vendorId, Map<String, String> t) {
    bool adding = false;
    bool open = true;
    String err = '';
    final String body = t['body'] ?? '';
    final List<String> fields = <String>[];
    for (final RegExpMatch m in RegExp(r'\{([a-z0-9_]+)\}').allMatches(body)) {
      final String f = '{${m.group(1)!}}';
      if (!fields.contains(f)) {
        fields.add(f);
      }
    }
    final int sections = body
        .split('\n')
        .where((String l) => RegExp(r'^\d+\.\s').hasMatch(l.trim()))
        .length;
    Widget pill(IconData ic, String label) => Container(
          margin: const EdgeInsets.only(right: 8),
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(
              color: _lzBg(card),
              borderRadius: BorderRadius.circular(99),
              border: Border.all(color: _lzLine(goldLine))),
          child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
            Icon(ic, size: 14, color: gold),
            const SizedBox(width: 6),
            Text(label, style: TextStyle(color: _lzFg(plum), fontSize: 12, fontWeight: FontWeight.w700)),
          ]),
        );
    _lzSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: _lzBg(ivory),
      constraints: const BoxConstraints(maxWidth: 680),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setP) {
          void up(VoidCallback f) {
            if (open) setP(f);
          }

          Future<void> add() async {
            up(() {
              adding = true;
              err = '';
            });
            try {
              await FirebaseFirestore.instance
                  .collection('vendors')
                  .doc(vendorId)
                  .collection('contractTemplates')
                  .add(<String, dynamic>{
                'name': t['name'] ?? 'Starter template',
                'status': 'draft',
                'source': 'starter',
                'body': body,
                'fieldsDetected': fields,
                'notes': <String>[
                  'Lazo starter template - personalize the details and review with your own judgment before first use.',
                ],
                'version': 1,
                'createdBy': _uid,
                'createdAt': FieldValue.serverTimestamp(),
                'updatedAt': FieldValue.serverTimestamp(),
              });
              if (open) {
                Navigator.pop(ctx);
              }
              if (mounted) {
                Navigator.pop(context);
              }
              _toast('Added \u2713 Review & activate it in Contract templates.');
            } catch (_) {
              if (!open) {
                _toast('Could not add - try again.');
                return;
              }
              up(() {
                adding = false;
                err = 'Couldn\u2019t add it. Check your connection and try again.';
              });
            }
          }

          final Size scr = MediaQuery.of(ctx2).size;
          return SizedBox(
            height: scr.height * (scr.width >= _lzWideAt ? .8 : .86),
            child: _lzFrame(ctx2,
                fill: true,
                icon: Icons.description_rounded,
                title: t['name'] ?? '',
                subtitle: t['blurb'],
                headerExtra: Wrap(runSpacing: 6, children: <Widget>[
                  if (sections > 0) pill(Icons.format_list_numbered_rounded, '$sections sections'),
                  pill(Icons.edit_rounded, '${fields.length} details fill in per booking'),
                ]),
                children: <Widget>[
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.fromLTRB(18, 16, 18, 18),
                    decoration: BoxDecoration(
                        color: _lzBg(Colors.white),
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: _lzLine(goldLine))),
                    child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: _pv1_contractBody(body)),
                  ),
                  const SizedBox(height: 12),
                  _lzNote(Icons.info_outline_rounded,
                      'Highlighted words fill in from each booking. You can edit every line after you add it.'),
                  _onbError(err),
                ],
                footer: _lzActions(
                    secondary: 'Close',
                    onSecondary: () => Navigator.pop(ctx),
                    primary: 'Add to my templates',
                    icon: Icons.add_rounded,
                    busy: adding,
                    onPrimary: add)),
          );
        },
      ),
    ).then((_) => open = false);
  }

  /// A contract body as a reader sees it: headings, paragraphs and bullets,
  /// with each {placeholder} shown as a highlighted plain-words chip.
  List<Widget> _pv1_contractBody(String body) {
    final RegExp ph = RegExp(r'\{([a-z0-9_]+)\}');
    TextSpan rich(String line, TextStyle base) {
      final List<InlineSpan> parts = <InlineSpan>[];
      int at = 0;
      for (final RegExpMatch m in ph.allMatches(line)) {
        if (m.start > at) parts.add(TextSpan(text: line.substring(at, m.start)));
        parts.add(TextSpan(
            text: m.group(1)!.replaceAll('_', ' '),
            style: TextStyle(
                color: _lzFg(plum),
                fontWeight: FontWeight.w700,
                backgroundColor: gold.withOpacity(.22))));
        at = m.end;
      }
      if (at < line.length) parts.add(TextSpan(text: line.substring(at)));
      return TextSpan(style: base, children: parts);
    }

    final TextStyle para = TextStyle(fontSize: 13.5, color: _lzFg(ink), height: 1.55);
    final List<Widget> out = <Widget>[];
    bool first = true;
    for (final String raw in body.split('\n')) {
      final String line = raw.trim();
      if (line.isEmpty) {
        continue;
      }
      final bool heading = line.length < 90 &&
          line == line.toUpperCase() &&
          RegExp(r'[A-Z]').hasMatch(line);
      if (heading && first) {
        out.add(Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Text(line,
              textAlign: TextAlign.center,
              style: TextStyle(
                  fontSize: 12,
                  letterSpacing: 1.6,
                  fontWeight: FontWeight.w800,
                  color: _lzFg(plum))),
        ));
      } else if (heading) {
        final String h = line.replaceFirst(RegExp(r'^\d+\.\s*'), '');
        final String n = RegExp(r'^\d+').stringMatch(line) ?? '';
        out.add(Padding(
          padding: const EdgeInsets.only(top: 14, bottom: 6),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
            if (n.isNotEmpty) ...<Widget>[
              Text(n, style: _serif(size: 18, weight: FontWeight.w700, color: gold, height: 1.1)),
              const SizedBox(width: 8),
            ],
            Expanded(
              child: Text(
                  h.isEmpty ? line : h[0] + h.substring(1).toLowerCase(),
                  style: _serif(size: 18, weight: FontWeight.w700, height: 1.1)),
            ),
          ]),
        ));
      } else if (line.startsWith('- ')) {
        out.add(Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 6),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Container(width: 5, height: 5, decoration: const BoxDecoration(color: gold, shape: BoxShape.circle)),
            ),
            const SizedBox(width: 10),
            Expanded(child: Text.rich(rich(line.substring(2), para))),
          ]),
        ));
      } else {
        out.add(Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Text.rich(rich(line, para)),
        ));
      }
      first = false;
    }
    return out;
  }""")

    # ------------------------------------------------------------ _disconnectSquare
    rep(func('  Future<void> _disconnectSquare('), r"""  Future<void> _disconnectSquare(String vendorId) async {
    bool open = true;
    bool busy = false;
    bool done = false;
    String err = '';
    Future<void>? job;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 480),
      builder: (BuildContext sc) => StatefulBuilder(builder: (BuildContext ctx, StateSetter set) {
        void up(VoidCallback f) {
          if (open) set(f);
        }

        void fail(String m) {
          if (!open) {
            _toast(m);
            return;
          }
          up(() {
            busy = false;
            err = m;
          });
        }

        Future<void> go() async {
          up(() {
            busy = true;
            err = '';
          });
          try {
            final HttpsCallable fn = FirebaseFunctions.instance.httpsCallable(
                'squareDisconnect',
                options: HttpsCallableOptions(timeout: const Duration(seconds: 40)));
            await fn.call(<String, dynamic>{'vendorId': vendorId});
            done = true;
            if (open) Navigator.pop(sc);
          } on FirebaseFunctionsException catch (e) {
            fail(e.message ?? 'Could not disconnect Square.');
          } catch (_) {
            fail('Could not disconnect Square.');
          }
        }

        return _lzFrame(ctx,
            icon: Icons.link_off_rounded,
            title: 'Disconnect Square?',
            subtitle: 'New invoices stop offering Square card payments.',
            children: <Widget>[
              const SizedBox(height: 14),
              _lzNote(Icons.account_balance_wallet_outlined,
                  'Anything couples already paid stays exactly where it is - in your Square account.'),
              if (busy) ...<Widget>[
                const SizedBox(height: 12),
                _lzBusy('Disconnecting\u2026'),
              ],
              _onbError(err),
            ],
            footer: _lzActions(
                secondary: 'Keep it',
                onSecondary: () => Navigator.pop(sc),
                primary: 'Disconnect',
                danger: true,
                icon: Icons.link_off_rounded,
                busy: busy,
                onPrimary: () {
                  job = go();
                }));
      }),
    );
    open = false;
    if (job != null) await job;
    if (done) _toast('Square disconnected.');
  }""")

    # ------------------------------------------------------------ _addPaymentLink
    rep(func('  Future<void> _addPaymentLink('), r"""  Future<void> _addPaymentLink(String vendorId, List<dynamic> existing) async {
    final List<String> brands = <String>[
      'Venmo',
      'Cash App',
      'PayPal',
      'Authorize.net',
      'Zelle',
      'Other'
    ];
    const Map<String, String> hints = <String, String>{
      'Venmo': 'venmo.com/u/yourname or @yourhandle',
      'Cash App': 'cash.app/\$yourcashtag',
      'PayPal': 'paypal.me/yourname',
      'Authorize.net': 'Your payment page link',
      'Zelle': 'The email or phone your Zelle uses',
      'Other': 'A link couples can pay through',
    };
    String brand = brands.first;
    final TextEditingController urlC = TextEditingController();
    bool open = true;
    bool busy = false;
    bool added = false;
    String err = '';
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 520),
      builder: (BuildContext sc) => StatefulBuilder(builder: (BuildContext ctx2, StateSetter setD) {
        void up(VoidCallback f) {
          if (open) setD(f);
        }

        Future<void> add() async {
          final String u = urlC.text.trim();
          if (u.isEmpty || busy) {
            return;
          }
          up(() {
            busy = true;
            err = '';
          });
          try {
            final List<dynamic> next = List<dynamic>.from(existing)
              ..add(<String, dynamic>{'label': brand, 'url': u});
            await FirebaseFirestore.instance
                .collection('vendors')
                .doc(vendorId)
                .set(<String, dynamic>{'paymentLinks': next},
                    SetOptions(merge: true));
            added = true;
            if (open) Navigator.pop(sc);
          } catch (e) {
            if (!open) {
              _toast('Could not add that: ' + _errText(e));
              return;
            }
            up(() {
              busy = false;
              err = 'Couldn\u2019t add it. Check your connection and try again.';
            });
          }
        }

        return _lzFrame(ctx2,
            icon: Icons.account_balance_wallet_rounded,
            title: 'Add a payment method',
            subtitle: 'Couples see it as a way to pay you.',
            children: <Widget>[
              _lzSection('Pay with'),
              Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                for (final String b in brands)
                  _onbChip(label: b, selected: brand == b, onTap: busy ? null : () => up(() => brand = b)),
              ]),
              _lzSection('Where to send them'),
              TextField(
                controller: urlC,
                autofocus: true,
                enabled: !busy,
                keyboardType: TextInputType.url,
                autocorrect: false,
                textInputAction: TextInputAction.done,
                onChanged: (_) => up(() => err = ''),
                onSubmitted: (_) => add(),
                cursorColor: _lzFg(plum),
                style: TextStyle(color: _lzFg(ink), fontSize: 14.5),
                decoration: _epDeco('Link or handle', hints[brand] ?? ''),
              ),
              _onbError(err),
            ],
            footer: _lzActions(
                secondary: 'Cancel',
                onSecondary: () => Navigator.pop(sc),
                primary: 'Add $brand',
                icon: Icons.add_rounded,
                busy: busy,
                onPrimary: urlC.text.trim().isEmpty ? null : add));
      }),
    );
    open = false;
    if (added) _toast('Added \u2713');
  }""")

    # ------------------------------------------------------------ _setDefaultRetainer
    rep(func('  Future<void> _setDefaultRetainer('), r"""  Future<void> _setDefaultRetainer(String vendorId, num current) async {
    // v131: never let a bad field or a slow read swallow the tap.
    Map<String, dynamic> vd0 = <String, dynamic>{};
    try {
      final DocumentSnapshot<Map<String, dynamic>> vs = await FirebaseFirestore
          .instance
          .collection('vendors')
          .doc(vendorId)
          .get();
      vd0 = vs.data() ?? <String, dynamic>{};
    } catch (e) {
      debugPrint('LAZO retainer read: ' + e.toString());
      _toast('Could not open that: ' + _errText(e));
      return;
    }
    String mode = (vd0['retainerMode'] ?? 'contract').toString();
    num pct = 50;
    final dynamic rawPct = vd0['retainerPercent'];
    if (rawPct is num) {
      pct = rawPct;
    } else if (rawPct != null) {
      pct = num.tryParse(rawPct.toString()) ?? 50;
    }
    final TextEditingController flatC = TextEditingController(
        text: current > 0 ? current.round().toString() : '');
    bool open = true;
    bool busy = false;
    bool saved = false;
    num flatSaved = 0;
    String err = '';
    if (!mounted) return;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 520),
      builder: (BuildContext sc) => StatefulBuilder(builder: (BuildContext ctx2, StateSetter setD) {
        void up(VoidCallback f) {
          if (open) setD(f);
        }

        Future<void> save() async {
          final num flat = num.tryParse(flatC.text.trim()) ?? 0;
          up(() {
            busy = true;
            err = '';
          });
          try {
            await FirebaseFirestore.instance
                .collection('vendors')
                .doc(vendorId)
                .set(<String, dynamic>{
              'retainerMode': mode,
              'retainerPercent': pct,
              'defaultRetainer': mode == 'flat' ? flat : 0,
            }, SetOptions(merge: true));
            flatSaved = flat;
            saved = true;
            if (open) Navigator.pop(sc);
          } catch (e) {
            if (!open) {
              _toast('Could not save that: ' + _errText(e));
              return;
            }
            up(() {
              busy = false;
              err = 'Couldn\u2019t save. Check your connection and try again.';
            });
          }
        }

        Widget option(String id, IconData ic, String title, String sub) {
          final bool sel = mode == id;
          return Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: _Press(
              scale: .985,
              tick: _Tick.select,
              onTap: busy ? null : () => up(() => mode = id),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 180),
                padding: const EdgeInsets.fromLTRB(12, 12, 12, 12),
                decoration: BoxDecoration(
                  color: sel ? _lzBg(card) : Colors.transparent,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: sel ? gold : _lzLine(goldLine), width: sel ? 1.5 : 1),
                ),
                child: Row(children: <Widget>[
                  Container(
                      width: 36,
                      height: 36,
                      decoration: BoxDecoration(
                          color: sel ? plumDeep : _lzBg(const Color(0xFFF1E9E0)),
                          borderRadius: BorderRadius.circular(11)),
                      child: Icon(ic, size: 18, color: sel ? gold : _lzFg(muted))),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                      Text(title,
                          style: TextStyle(color: _lzFg(sel ? plum : ink), fontSize: 14, fontWeight: FontWeight.w700)),
                      const SizedBox(height: 2),
                      Text(sub, style: TextStyle(fontSize: 12, color: _lzFg(muted), height: 1.3)),
                    ]),
                  ),
                  Icon(sel ? Icons.radio_button_checked_rounded : Icons.radio_button_unchecked_rounded,
                      color: sel ? gold : _lzFg(muted), size: 20),
                ]),
              ),
            ),
          );
        }

        return _lzFrame(ctx2,
            icon: Icons.request_quote_rounded,
            title: 'Automatic retainer',
            subtitle: 'When a couple signs and no invoice has gone out yet, Lazo bills them right away.',
            children: <Widget>[
              const SizedBox(height: 14),
              option('contract', Icons.description_outlined, 'Follow my contract',
                  'Whatever retainer the signed contract states - recommended.'),
              option('percent', Icons.percent_rounded, 'Percent of the total',
                  'Half down is the industry norm. Set your own.'),
              option('flat', Icons.attach_money_rounded, 'A flat amount', 'Same retainer on every booking.'),
              option('off', Icons.do_not_disturb_on_outlined, 'Don\u2019t invoice automatically',
                  'You\u2019ll send invoices yourself.'),
              if (mode == 'percent') ...<Widget>[
                _lzSection('How much'),
                Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                  for (final num p in <num>[25, 30, 50])
                    _onbChip(label: '${p.round()}%', selected: pct == p, onTap: busy ? null : () => up(() => pct = p)),
                ]),
                const SizedBox(height: 10),
                _lzNote(Icons.calculate_outlined,
                    'On a \u00244,000 contract, that\u2019s \u0024${(4000 * pct / 100).round()}.'),
              ],
              if (mode == 'flat') ...<Widget>[
                _lzSection('How much'),
                TextField(
                  controller: flatC,
                  autofocus: flatC.text.isEmpty,
                  enabled: !busy,
                  keyboardType: TextInputType.number,
                  textInputAction: TextInputAction.done,
                  onSubmitted: (_) => save(),
                  cursorColor: _lzFg(plum),
                  style: TextStyle(color: _lzFg(ink), fontSize: 15),
                  decoration: _onbDeco('Amount', icon: Icons.attach_money_rounded).copyWith(hintText: 'e.g. 500'),
                ),
              ],
              _onbError(err),
            ],
            footer: _lzActions(
                secondary: 'Cancel',
                onSecondary: () => Navigator.pop(sc),
                primary: 'Save',
                icon: Icons.check_rounded,
                busy: busy,
                onPrimary: save));
      }),
    );
    open = false;
    if (!saved) return;
    _toast(mode == 'off'
        ? 'Automatic invoicing off.'
        : mode == 'contract'
            ? 'Saved - we\u2019ll follow each contract.'
            : mode == 'percent'
                ? 'Saved - ${pct.round()}% at signing.'
                : 'Saved - \u0024${flatSaved.round()} at signing.');
  }""")

    return s
