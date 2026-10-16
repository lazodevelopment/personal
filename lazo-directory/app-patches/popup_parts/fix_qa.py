"""fix_qa.py - JC-LAZO-POPUP-1014 QA pass 2: fixes for what the testers found (applied after the parts).

Couple:
  F1 budget sheet showed the total from when it opened - it now reads the couple doc live.
  F2 the Vendor team month road overflowed with 4 categories + "+N" in a 92 px column - 3 rows + "+N".
  F3 Edit vendor: "3,250" parsed to null and erased the amount - commas and $ are stripped first.
  F4 "Multiple widgets used the same GlobalKey" on every screen change: the floating Ask June bar and the
     June hero both carried _kTourJune. The tour only points at Home, where the hero has it; the bar drops it.
  F5 Website names: the split regex matched "and" inside names ("Alexandra" -> "Alex & ra") - word boundaries.
  F6 Shopping estimate: "12.50" saved as 1250 (the "." was stripped) - parsed as money, rounded to dollars.
"""


def apply_couple(s: str) -> str:
    def rep(old, new):
        nonlocal s
        assert s.count(old) == 1, (s.count(old), old[:90])
        s = s.replace(old, new)

    # F1
    rep("""                  return _budgetCard(couple, livePlan);
                },
              ),""", """                  return StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
                    stream: _liveDoc('couple:$_cid', () => _coupleRef),
                    builder: (BuildContext c3,
                        AsyncSnapshot<DocumentSnapshot<Map<String, dynamic>>> cs) {
                      final Map<String, dynamic> liveCouple =
                          cs.data?.data() ?? couple;
                      return _budgetCard(liveCouple, livePlan);
                    },
                  );
                },
              ),""")
    # F2
    rep("""            for (final Map<String, String> c in cats.take(4))
              Padding(
                padding: const EdgeInsets.only(bottom: 2),""", """            for (final Map<String, String> c in cats.take(cats.length > 3 ? 2 : 3))
              Padding(
                padding: const EdgeInsets.only(bottom: 2),""")
    rep("""            if (cats.length > 4)
              Text('+${cats.length - 4}',""", """            if (cats.length > 3)
              Text('+${cats.length - 2} more',""")
    # F3
    rep("""      'budgetPlanned': double.tryParse(planC.text.trim()),
      'budgetActual': double.tryParse(spentC.text.trim()),""",
        """      'budgetPlanned': double.tryParse(planC.text.replaceAll(RegExp(r'[^0-9.]'), '')),
      'budgetActual': double.tryParse(spentC.text.replaceAll(RegExp(r'[^0-9.]'), '')),""")
    # F4
    rep("""      child: Center(
        key: _kTourJune,
        child: ConstrainedBox(""", """      child: Center(
        child: ConstrainedBox(""")
    # F5
    rep(r"""_joined.split(RegExp(r'\s*(?:&|\+|and)\s*', caseSensitive: false));""",
        r"""_joined.split(RegExp(r'\s*(?:&|\+|\band\b)\s*', caseSensitive: false));""")
    # F6
    rep("""            int.tryParse(estC.text.trim().replaceAll(RegExp(r'[^0-9]'), '')) ??
                0,""", """            (double.tryParse(estC.text.trim().replaceAll(RegExp(r'[^0-9.]'), '')) ??
                    0)
                .round(),""")
    # F7 toasts show on top of an open popup (kit _lzToastOver); the Undo works from inside a sheet
    rep("""  void _toast(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(""", """  void _toast(String message) {
    if (!mounted) return;
    if (_lzToastOver(message)) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(""")
    rep("""  void _toastC(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(""", """  void _toastC(String message) {
    if (!mounted) return;
    if (_lzToastOver(message)) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(""")
    rep("""  void _toastUndo(String message, Future<void> Function() undo) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)""", """  void _toastUndo(String message, Future<void> Function() undo) {
    if (!mounted) return;
    if (_lzToastOver(message, action: 'Undo', duration: const Duration(seconds: 6), onAction: () async {
      try {
        await undo();
      } catch (_) {
        _toastC('Could not undo that.');
      }
    })) return;
    ScaffoldMessenger.of(context)""")
    # F8 Add a date: with a name and no day, the main button ("Pick the day") opens the calendar instead of doing nothing
    rep("""                      : (picked == null ? 'Pick the day' : 'Add date'),
                  icon: Icons.add_rounded,
                  busy: busy,
                  onPrimary: valid ? save : null));""", """                      : (picked == null ? 'Pick the day' : 'Add date'),
                  icon: picked == null && c.text.trim().isNotEmpty ? Icons.event_rounded : Icons.add_rounded,
                  busy: busy,
                  onPrimary: valid
                      ? save
                      : (c.text.trim().isNotEmpty && picked == null ? pickDay : null)));""")
    # F9 Remove guest: the spinner belonged to the delete, not to "Save"
    rep("""                  primary: id == null ? 'Add guest' : 'Save',
                  icon: Icons.check_rounded,
                  busy: deleting,
                  onPrimary: valid ? () => Navigator.pop(ctx2, true) : null));""", """                  primary: id == null ? 'Add guest' : 'Save',
                  icon: Icons.check_rounded,
                  onPrimary: valid && !deleting ? () => Navigator.pop(ctx2, true) : null));""")
    # F10 Waiting for approval: a failed load said "all caught up"
    rep("""        .toList();
    if (!mounted) {
      return;
    }
    bool open = true;
    bool busyAll = false;
    final Set<String> working = <String>{};
    String err = '';""", """        .toList();
    if (!mounted) {
      return;
    }
    bool open = true;
    bool busyAll = false;
    final Set<String> working = <String>{};
    String err = j['photos'] is List
        ? ''
        : 'Couldn\\u2019t load the photos waiting. Check your connection, then close this and try again.';""")
    rep("""                if (list.isEmpty)
                  _pcA_empty(Icons.check_circle_outline_rounded,""", """                if (list.isEmpty && err.isEmpty)
                  _pcA_empty(Icons.check_circle_outline_rounded,""")
    # F11 Our story in dates: the title is the required field, not "When" (it was whichever field came first)
    rep("""    final String firstKey = fields.isEmpty ? '' : fields.first[0];""",
        """    final String firstKey = fields.any((List<String> f) => f[0] == 'title')
        ? 'title'
        : (fields.isEmpty ? '' : fields.first[0]);""")
    rep("""    final String first = tc[fields.first[0]]?.text.trim() ?? '';""",
        """    final String first = tc[firstKey]?.text.trim() ?? '';""")
    # F12 Send to vendors: an attachment upload that hangs no longer holds "Sending..." for 45 s
    rep("""      await r.putData(bytes, SettableMetadata(contentType: 'text/html'));""",
        """      await r.putData(bytes, SettableMetadata(contentType: 'text/html')).timeout(const Duration(seconds: 20));""")
    # F13 Guest list: "Add guest" readable on the plum page and clear of the floating Ask June bar
    rep("""              icon:  Icon(Icons.person_add_alt_1_rounded,
                  size: 19, color: _lzFg(plum)),
              label:  Text('Add guest',
                  style: TextStyle(color: _lzFg(plum), fontWeight: FontWeight.w600)),""", """              icon: const Icon(Icons.person_add_alt_1_rounded, size: 19, color: gold),
              label: const Text('Add guest',
                  style: TextStyle(color: gold, fontWeight: FontWeight.w700)),""")
    rep("""                padding:
                    const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
              ),
            ),
          ],
        );
      },
    );
  }

  void _shareGuestList(""", """                padding:
                    const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
              ),
            ),
            const SizedBox(height: 96), // clears the floating Ask June bar
          ],
        );
      },
    );
  }

  void _shareGuestList(""")
    # F14 Weather card: "Weathe/r" - the title keeps its width, the date line gives way
    rep("""              Expanded(child: Text('Weather', style: _serif(size: 22))),
              Text('$title \\u00b7 ${_longDate(wedding)}',
                  style: const TextStyle(fontSize: 11.5, color: muted)),""", """              Text('Weather', maxLines: 1, softWrap: false, style: _serif(size: 22)),
              const SizedBox(width: 10),
              Expanded(
                  child: Text('$title \\u00b7 ${_longDate(wedding)}',
                      textAlign: TextAlign.right,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 11.5, color: muted))),""")
    # F15 A widget opened from the strip closes when a tap in it changes the screen behind
    rep("""  Widget _crStrip(Map<String, dynamic> couple,""", """  BuildContext? _crSheetCtx;

  Widget _crSheetHold(BuildContext c, Widget child) {
    _crSheetCtx = c;
    return child;
  }

  @override
  void setState(VoidCallback fn) {
    final _View before = _view;
    super.setState(fn);
    final BuildContext? sc = _crSheetCtx;
    if (_view != before && sc != null) {
      _crSheetCtx = null;
      Future<void>.microtask(() {
        if (sc.mounted) Navigator.of(sc).maybePop();
      });
    }
  }

  Widget _crStrip(Map<String, dynamic> couple,""")
    rep("""          builder: (BuildContext c) => ConstrainedBox(
            constraints: BoxConstraints(maxHeight: MediaQuery.of(c).size.height * .88),
            child: _lzFrame(c,
                icon: Icons.dashboard_customize_rounded,
                title: 'Your widgets',
                subtitle: 'Press and hold a widget to move it.',
                bodyPadding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
                children: <Widget>[_crStack(couple, plan, inqs, wed, daysOut)]),
          ),
        );
        return;""", """          builder: (BuildContext c) => _crSheetHold(c, ConstrainedBox(
            constraints: BoxConstraints(maxHeight: MediaQuery.of(c).size.height * .88),
            child: _lzFrame(c,
                icon: Icons.dashboard_customize_rounded,
                title: 'Your widgets',
                subtitle: 'Press and hold a widget to move it.',
                bodyPadding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
                children: <Widget>[_crStack(couple, plan, inqs, wed, daysOut)]),
          )),
        ).whenComplete(() => _crSheetCtx = null);
        return;""")
    rep("""        builder: (BuildContext c) => SafeArea(
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
    }""", """        builder: (BuildContext c) => _crSheetHold(c, SafeArea(
          top: false,
          child: ConstrainedBox(
            constraints: BoxConstraints(maxHeight: MediaQuery.of(c).size.height * .88),
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(16, 10, 16, 16),
              child: _crBody(id, couple, plan, inqs, wed, daysOut),
            ),
          ),
        )),
      ).whenComplete(() => _crSheetCtx = null);
    }""")
    # F16 raw "internal [0]" shown as the error on Delete account, partner Join and Block
    rep("""                err = e.message ?? 'We could not delete your account just now.';""",
        """                err = _lzFnMsg(e, 'We could not delete your account just now. Check your connection and try again.');""")
    rep("""                      : (e.message ?? 'We could not delete your account just now.');""",
        """                      : _lzFnMsg(e, 'We could not delete your account just now. Check your connection and try again.');""")
    rep("""                joinErr = e.message ?? 'That code did not work.';""",
        """                joinErr = _lzFnMsg(e, 'That code did not work. Check it and try again.');""")
    rep("""      _toast(e.message ?? 'Could not update that just now.');""",
        """      _toast(_lzFnMsg(e, 'Could not update that just now. Try again in a moment.'));""")
    # F17 Setup reopened from Account: the vendor chips start from the plan (not a fixed default set), and
    # toggling needed <-> skipped saves; only booked / researching categories are left untouched
    rep("""    int step = 0;
    bool saving = false;
    String err = '';
    if (!mounted) return;""", """    int step = 0;
    bool saving = false;
    String err = '';
    try {
      final QuerySnapshot<Map<String, dynamic>> pq0 = await _planRef.get();
      final Set<String> fromPlan = <String>{
        for (final QueryDocumentSnapshot<Map<String, dynamic>> pd in pq0.docs)
          if ((pd.data()['status'] ?? '').toString().isNotEmpty &&
              (pd.data()['status'] ?? '').toString() != 'skipped')
            pd.id
      };
      if (pq0.docs.isNotEmpty) {
        wanted
          ..clear()
          ..addAll(fromPlan);
      }
    } catch (_) {}
    if (!mounted) return;""")
    rep("""                  if ((pd.data()['status'] ?? '').toString().isNotEmpty) {
                    hasPlan.add(pd.id);
                  }""", """                  if (const <String>['booked', 'researching']
                      .contains((pd.data()['status'] ?? '').toString())) {
                    hasPlan.add(pd.id);
                  }""")
    # F18 "Yes, let me know" when the device or browser blocks notifications: say so
    rep("""    await _stampPushAsk(ok ? 'yes' : 'blocked');
    if (ok) _toast('Done - we’ll let you know.');""", """    await _stampPushAsk(ok ? 'yes' : 'blocked');
    if (ok) {
      _toast('Done - we’ll let you know.');
    } else {
      _toast('Notifications are off for Lazo on this device. Turn them on in your settings, then try again from Account.');
    }""")
    # F20 support tickets were stamped build 'v90'
    rep("""                  'build': 'v90',""", """                  'build': 'v158',""")
    # F21 Undo after removing a moment / shopping item: keep a real copy of the data before the delete
    rep("""                            final Map<String, dynamic> gone = evs[i].data();""",
        """                            final Map<String, dynamic> gone = Map<String, dynamic>.from(evs[i].data());""")
    rep("""        final Map<String, dynamic> gone = d.data();
        final DocumentReference<Map<String, dynamic>> ref = d.reference;
        await ref.delete();
        _toastUndo('Removed.', () => ref.set(gone));""", """        final Map<String, dynamic> gone = Map<String, dynamic>.from(d.data());
        final DocumentReference<Map<String, dynamic>> ref = d.reference;
        await ref.delete();
        _toastUndo('Removed.', () => ref.set(gone));""")
    # F22 marriage license: "Apply between Mar 28 and Mar 28" (a one-year window with no years shown)
    rep("""        window = 'Apply between ${_licDate(earliest)} and ${_licDate(latest)}';""",
        """        window = earliest.isBefore(DateTime.now())
            ? 'Apply any time before ${_licDate(latest)}, ${latest.year}'
            : 'Apply between ${_licDate(earliest)}${earliest.year != latest.year ? ', ${earliest.year}' : ''} and ${_licDate(latest)}, ${latest.year}';""")
    # F23 Day-of: the last timeline line sat under the floating Ask June bar
    rep("""    }
    return ListView(
      padding: const EdgeInsets.fromLTRB(18, 8, 18, 32),
      children: <Widget>[""", """    }
    return ListView(
      padding: const EdgeInsets.fromLTRB(18, 8, 18, 110),
      children: <Widget>[""")
    # F24 a category marked skipped no longer counts toward the planned total (money already spent on it still does)
    rep("""      final num pl = (p['budgetPlanned'] as num?) ?? 0;
      spent += s;""", """      final num pl = (p['status'] ?? '') == 'skipped' ? 0 : ((p['budgetPlanned'] as num?) ?? 0);
      spent += s;""")
    rep("""              final num pl = (p['budgetPlanned'] as num?) ?? 0;
              final num sp = _spentOf(p); // v140""", """              final num pl = (p['status'] ?? '') == 'skipped' ? 0 : ((p['budgetPlanned'] as num?) ?? 0);
              final num sp = _spentOf(p); // v140""")
    rep("""      if (p['budgetPlanned'] is num) planned += p['budgetPlanned'] as num;
      if (p['budgetActual'] is num) committed += p['budgetActual'] as num;""", """      if (p['budgetPlanned'] is num && (p['status'] ?? '') != 'skipped') planned += p['budgetPlanned'] as num;
      if (p['budgetActual'] is num) committed += p['budgetActual'] as num;""")
    rep("""      planned += ((p['budgetPlanned'] ?? 0) as num).toDouble();""",
        """      if ((p['status'] ?? '') != 'skipped') planned += ((p['budgetPlanned'] ?? 0) as num).toDouble();""")
    # F25 partner "Copy code" said nothing when the phone refused the clipboard: the code is shown instead
    rep("""                              onPressed: _h(() async {
                                await Clipboard.setData(ClipboardData(
                                    text: (d.data()['code'] ?? '').toString()));
                                _toast('Code copied \\u2713');
                              }),""", """                              onPressed: _h(() async {
                                final String code = (d.data()['code'] ?? '').toString();
                                try {
                                  await Clipboard.setData(ClipboardData(text: code));
                                  _toast('Code copied');
                                } catch (_) {
                                  _toast('Couldn\\u2019t copy it here. The code is $code - send it to your partner.');
                                }
                              }),""")
    # F19 the contracts vault (_contractsVaultSheet) had no way in: an Account row and a Vendor team card
    rep("""          _accountRow(
            icon: Icons.notifications_active_outlined,
            title: 'Notifications',
            value: 'Know the moment a vendor writes back',
            onTap: () => _maybeAskPush(force: true),
          ),
        ]),""", """          _accountRow(
            icon: Icons.notifications_active_outlined,
            title: 'Notifications',
            value: 'Know the moment a vendor writes back',
            onTap: () => _maybeAskPush(force: true),
          ),
          _accountRow(
            icon: Icons.description_outlined,
            title: 'Contracts',
            value: 'Every agreement your vendors sent, signed or waiting, in one place',
            onTap: () => _contractsVaultSheet(),
          ),
        ]),""")
    rep("""        _subHeader('Vendor team'),
        _teamCard(couple, plan, _inqDocs, teamWedding),
        const SizedBox(height: 14),""", """        _subHeader('Vendor team'),
        _teamCard(couple, plan, _inqDocs, teamWedding),
        const SizedBox(height: 12),
        _Press(
          scale: .985,
          onTap: () => _contractsVaultSheet(),
          child: Container(
            padding: const EdgeInsets.fromLTRB(14, 12, 12, 12),
            decoration: BoxDecoration(
                color: _lzBg(cardBg),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: _lzLine(goldLine))),
            child: Row(children: <Widget>[
              Container(
                  width: 38,
                  height: 38,
                  decoration: BoxDecoration(color: plumDeep, borderRadius: BorderRadius.circular(11)),
                  child: const Icon(Icons.description_outlined, color: gold, size: 19)),
              const SizedBox(width: 12),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                  Text('Your contracts',
                      style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: _lzFg(plum))),
                  const SizedBox(height: 2),
                  Text('Signed and waiting, with the PDFs',
                      style: TextStyle(fontSize: 12.5, color: _lzFg(muted))),
                ]),
              ),
              Icon(Icons.chevron_right_rounded, color: _lzFg(muted)),
            ]),
          ),
        ),
        const SizedBox(height: 14),""")
    return s


def apply_vendor(s: str) -> str:
    def rep(old, new):
        nonlocal s
        assert s.count(old) == 1, (s.count(old), old[:90])
        s = s.replace(old, new)

    # F7 (vendor) toasts show on top of an open popup
    rep("""  void _toast(String message) {
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(""", """  void _toast(String message) {
    if (!mounted) {
      return;
    }
    if (_lzToastOver(message)) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(""")

    # V1 (high) a reply, proposal or teaser in a booked / lost thread set status back to 'responded'
    #    and un-booked the couple. Only an open lead moves to 'responded'.
    rep("""    await ref.update(<String, dynamic>{
      'status': status,
      'vendorReply': text,
      'respondedAt': FieldValue.serverTimestamp(),
    });
    _maybeAskPush();""", """    String cur = '';
    try {
      cur = ((await ref.get()).data()?['status'] ?? '').toString();
    } catch (_) {}
    await ref.update(<String, dynamic>{
      if (!const <String>['booked', 'delivered', 'lost', 'closed'].contains(cur)) 'status': status,
      'vendorReply': text,
      'respondedAt': FieldValue.serverTimestamp(),
    });
    _maybeAskPush();""")
    # V2 (high) dropping a lead on Lost or Delivered opened the "Mark booked" sheet; each column now does its own thing
    rep("""      if (!s.exists || !mounted) return;
      await _bookingStatusSheet(inquiryId, s.data()!);
      return;
    }""", """      if (!s.exists || !mounted) return;
      final String cur = (s.data()!['status'] ?? '').toString();
      if (key == 'lost') {
        if (cur == 'lost' || cur == 'closed') return;
        if (cur == 'booked') {
          await _bookingStatusSheet(inquiryId, s.data()!); // releasing a booking asks why
          return;
        }
        final bool go = await _lzConfirm('Mark this lead lost?',
            'It moves to Lost. You can still message them, and a reply from them brings it back.',
            confirm: 'Mark lost', cancel: 'Keep it', danger: true, icon: Icons.do_not_disturb_on_outlined);
        if (go) await _setStatus(inquiryId, 'lost');
        return;
      }
      if (key == 'delivered') {
        if (cur != 'booked') {
          _toast('Mark them booked first - delivery comes after the booking.');
          return;
        }
        await _markDelivered(inquiryId);
        return;
      }
      await _bookingStatusSheet(inquiryId, s.data()!);
      return;
    }""")
    # V3 a released booking ('closed') fell back to New/Talking; it is Lost
    rep("""  String _stageOf(Map<String, dynamic> inq, List<List<String>> stages) {
    final String st = (inq['status'] ?? '').toString();
    if (st == 'lost') return 'lost';""", """  String _stageOf(Map<String, dynamic> inq, List<List<String>> stages) {
    final String st = (inq['status'] ?? '').toString();
    if (st == 'lost' || st == 'closed') return 'lost';""")
    rep("""    if (st == 'booked' || st == 'delivered') return 'booked';
    if (st == 'lost') return 'lost';""", """    if (st == 'booked' || st == 'delivered') return 'booked';
    if (st == 'lost' || st == 'closed') return 'lost';""")
    # V4 "Booked" toast showed even when the write failed: _setStatus reports success
    rep("""  Future<void> _setStatus(String id, String status) async {
    try {
      await _setStatusInner(id, status);
    } catch (e) {
      _toast('Could not update: ' + _errText(e));
      debugPrint('LAZO setStatus: ' + e.toString());
    }
  }""", """  Future<bool> _setStatus(String id, String status) async {
    try {
      await _setStatusInner(id, status);
      return true;
    } catch (e) {
      _toast('Could not update: ' + _errText(e));
      debugPrint('LAZO setStatus: ' + e.toString());
      return false;
    }
  }""")
    rep("""    if (go) {
      await _setStatus(inquiryId, 'booked');
      _toast('Booked. Delivery tools are open for this thread.');
    }""", """    if (go && await _setStatus(inquiryId, 'booked')) {
      _toast('Booked. Delivery tools are open for this thread.');
    }""")
    # V5 (money) an invoice line with an amount but no label counted in "Send $X" but was dropped on save
    rep("""              if (lb.isEmpty || am == null) continue;
              lines.add(<String, dynamic>{'label': lb, 'amount': am});""", """              if (am == null || am <= 0) continue;
              lines.add(<String, dynamic>{
                'label': lb.isNotEmpty ? lb : (titleC.text.trim().isEmpty ? 'Services' : titleC.text.trim()),
                'amount': am
              });""")
    # V6 (money) the thread's invoiceStatus followed the last invoice touched, so a thread could read Paid with a
    #    balance still due; it is now worked out from all its invoices. Voiding asks first.
    rep("""  String _invMoney(num v) {""", """  /// The thread's invoiceStatus from ALL its invoices: anything still open wins, then paid, then void.
  Future<void> _rollupInvoiceStatus(String inquiryId) async {
    final DocumentReference<Map<String, dynamic>> iq =
        FirebaseFirestore.instance.collection('inquiries').doc(inquiryId);
    final QuerySnapshot<Map<String, dynamic>> all = await iq.collection('invoices').get();
    final List<String> st = <String>[
      for (final QueryDocumentSnapshot<Map<String, dynamic>> d in all.docs) (d.data()['status'] ?? '').toString()
    ];
    final String roll = st.any((String x) => x == 'sent' || x == 'due' || x == 'overdue')
        ? 'sent'
        : (st.contains('paid') ? 'paid' : (st.isEmpty ? '' : 'void'));
    await iq.set(<String, dynamic>{
      'invoiceStatus': roll,
      'invoiceUpdatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
  }

  String _invMoney(num v) {""")
    rep("""              await FirebaseFirestore.instance
                  .collection('inquiries')
                  .doc(inquiryId)
                  .set(<String, dynamic>{
                'invoiceStatus': 'paid',
                'invoiceUpdatedAt': FieldValue.serverTimestamp(),
              }, SetOptions(merge: true));""", """              await _rollupInvoiceStatus(inquiryId);""")
    rep("""                    onTap: () async {
                      await d.reference.set(<String, dynamic>{
                        'status': 'void',
                        'voidedAt': FieldValue.serverTimestamp(),
                      }, SetOptions(merge: true));
                      await FirebaseFirestore.instance
                          .collection('inquiries')
                          .doc(inquiryId)
                          .set(<String, dynamic>{
                        'invoiceStatus': 'void',
                        'invoiceUpdatedAt': FieldValue.serverTimestamp(),
                      }, SetOptions(merge: true));
                      _toast('Invoice voided.');
                    },""", """                    onTap: () async {
                      final bool go = await _lzConfirm('Void this invoice?',
                          'The couple can no longer pay it. This can\\u2019t be undone - send a new invoice if you need one.',
                          confirm: 'Void invoice', cancel: 'Keep it', danger: true);
                      if (!go) return;
                      try {
                        await d.reference.set(<String, dynamic>{
                          'status': 'void',
                          'voidedAt': FieldValue.serverTimestamp(),
                        }, SetOptions(merge: true));
                        await _rollupInvoiceStatus(inquiryId);
                        _toast('Invoice voided.');
                      } catch (e) {
                        _toast('Could not void it: ' + _errText(e));
                      }
                    },""")
    # V7 (money) $1,250.50 showed as $1,251 in the proposal preview and message: cents are kept when there are any
    rep("""  String _invMoney(num v) {
    final String s = v.round().toString();""", """  String _invMoney(num v) {
    final int cents = (v * 100).round();
    if (cents % 100 != 0) {
      final String whole = _invMoney(cents ~/ 100);
      return '$whole.${(cents % 100).toString().padLeft(2, '0')}';
    }
    final String s = v.round().toString();""")
    # V8 a tag over 24 characters closed the sheet without saving and without a word
    rep("""      if (tag.isEmpty || tag.length > 24) return;
      await FirebaseFirestore.instance
          .collection('inquiries')
          .doc(inquiryId)
          .set(<String, dynamic>{
        'tags': FieldValue.arrayUnion(<dynamic>[tag])""", """      if (tag.isEmpty) return;
      if (tag.length > 24) throw 'Tags can be up to 24 characters - try a shorter one.';
      await FirebaseFirestore.instance
          .collection('inquiries')
          .doc(inquiryId)
          .set(<String, dynamic>{
        'tags': FieldValue.arrayUnion(<dynamic>[tag])""")
    # V9 a failed couple search read as "nobody to greet"
    rep("""        return count == 0
            ? 'Nobody to greet right now'""", """        if (h['error'] != null) return 'Couldn\\u2019t load couples - try again soon';
        return count == 0
            ? 'Nobody to greet right now'""")
    rep("""    final String headline = _helloCache == null
        ? 'Finding couples who still need you\\u2026'
        : count == 0""", """    final String headline = _helloCache == null
        ? 'Finding couples who still need you\\u2026'
        : h['error'] != null
            ? 'Couldn\\u2019t load couples right now. Check your connection and try again soon.'
            : count == 0""")
    # V10 contract flow: a failed template fetch left June's "opening your contract studio" veil up forever
    rep("""    final QuerySnapshot<Map<String, dynamic>> allT = await FirebaseFirestore
        .instance
        .collection('vendors')
        .doc(vendorId)
        .collection('contractTemplates')
        .get();
    final List<QueryDocumentSnapshot<Map<String, dynamic>>> actives = allT.docs""", """    final QuerySnapshot<Map<String, dynamic>> allT;
    try {
      allT = await FirebaseFirestore.instance
          .collection('vendors')
          .doc(vendorId)
          .collection('contractTemplates')
          .get();
    } catch (e) {
      _popJuneVeil();
      _toast('Couldn\\u2019t open your contract templates: ' + _errText(e));
      return;
    }
    final List<QueryDocumentSnapshot<Map<String, dynamic>>> actives = allT.docs""")
    # V11 (high) the consult scheduler never saved: weekly hours were lists inside lists, which Firestore refuses.
    #     Each window is now a map {"0": start, "1": end}; functions-dashboard/scheduler.js reads w[0] / w[1],
    #     which works on that map unchanged. The sheet reads both shapes.
    rep("""                'hours': hours,""", """                'hours': <String, dynamic>{
                  for (final MapEntry<String, List<List<String>>> e in hours.entries)
                    e.key: <Map<String, String>>[
                      for (final List<String> w in e.value) <String, String>{'0': w[0], '1': w[1]}
                    ]
                },""")
    rep("""      hours[d[0]] = w
          .whereType<List>()
          .map((List x) => <String>[x[0].toString(), x[1].toString()])
          .toList();""", """      hours[d[0]] = <List<String>>[
        for (final dynamic x in w)
          if (x is List && x.length >= 2)
            <String>[x[0].toString(), x[1].toString()]
          else if (x is Map && x['0'] != null && x['1'] != null)
            <String>[x['0'].toString(), x['1'].toString()]
      ];""")
    # V12 raw server errors ("[firebase_functions/internal] internal [0]") reached vendors through _errText
    rep("""  String _errText(Object e) {
    String s = e.toString();""", """  String _errText(Object e) {
    if (e is FirebaseFunctionsException) {
      return _lzFnMsg(e, 'Something went wrong on our side. Try again in a moment.');
    }
    if (e is String) return e;
    if (e is TimeoutException) return 'That took too long. Check your connection and try again.';
    String s = e.toString().replaceFirst(RegExp(r'^\\[[a-z_/\\-]+\\]\\s*'), '');""")
    # V13 on a phone these errors sat below the fold, so Send looked like it did nothing: also shown on top
    rep("""            up(() {
              busy = false;
              err = 'Couldn\\u2019t send that. Check your connection and try again.';
            });""", """            up(() {
              busy = false;
              err = 'Couldn\\u2019t send that. Check your connection and try again.';
            });
            _toast(err);""")
    rep("""            up(() {
              busy = false;
              err = 'Couldn\\u2019t send the ticket. Check your connection and try again.';
            });""", """            up(() {
              busy = false;
              err = 'Couldn\\u2019t send the ticket. Check your connection and try again.';
            });
            _toast(err);""")
    rep("""            setSheet(() {
              saving = false;
              err = 'Could not save: ' + _errText(e);
            });
          }
        }

        return _lzFrame(sc,
            icon: Icons.event_available_rounded,""", """            setSheet(() {
              saving = false;
              err = 'Could not save: ' + _errText(e);
            });
            _toast(err);
          }
        }

        return _lzFrame(sc,
            icon: Icons.event_available_rounded,""")
    # V14 "Who I work with" saved a guest range of 200 to 50
    rep("""                'guestMin': int.tryParse(gMinC.text.trim()) ?? 0,
                'guestMax': int.tryParse(gMaxC.text.trim()) ?? 0,""", """                'guestMin': () {
                  final int a = int.tryParse(gMinC.text.trim()) ?? 0, b = int.tryParse(gMaxC.text.trim()) ?? 0;
                  return a > 0 && b > 0 && a > b ? b : a;
                }(),
                'guestMax': () {
                  final int a = int.tryParse(gMinC.text.trim()) ?? 0, b = int.tryParse(gMaxC.text.trim()) ?? 0;
                  return a > 0 && b > 0 && a > b ? a : b;
                }(),""")
    # V15 bug reports and tickets said "build 177"
    rep("""  static const String kBuildId = 'JC-LAZO-VDASH-0915-177';""",
        """  static const String kBuildId = 'JC-LAZO-VDASH-1014-197';""")
    # V16 a vendor at the photo limit was told "Unlimited gallery is coming with Lazo Pro", Pro or not
    rep("""          : 'Free profiles include 10 photos. Unlimited gallery is coming with Lazo Pro.');""",
        """          : 'Your gallery holds $cap photos. Remove one to add another.');""")
    # V18 dark mode: brand swatches went through _lzBg, so Blush / Ivory / Champagne showed as dark browns, and the
    #     ring on the picked swatch vanished. A swatch shows its true colour; the picked one gets a gold ring.
    rep("""                      color: _lzBg(_hexColor(w[0], plum)),
                      shape: BoxShape.circle,
                      border: Border.all(
                          color: _lzLine(cur.toUpperCase() == w[0].toUpperCase()
                              ? ink
                              : Colors.white),""", """                      color: _hexColor(w[0], plum),
                      shape: BoxShape.circle,
                      border: Border.all(
                          color: cur.toUpperCase() == w[0].toUpperCase()
                              ? (_lzDark ? gold : ink)
                              : (_lzDark ? Colors.white.withOpacity(.35) : Colors.white),""")
    # V19 due dates picked on the calendar were saved at local midnight: a couple a few time zones west of the
    #     vendor saw the day before. They are saved at local noon (the day is the same everywhere in the US).
    rep("""                'dueDate': due == null ? null : Timestamp.fromDate(due!),""",
        """                'dueDate': due == null ? null : Timestamp.fromDate(DateTime(due!.year, due!.month, due!.day, 12)),""")
    rep("""            'dueAt': due == null ? null : Timestamp.fromDate(due!),""",
        """            'dueAt': due == null ? null : Timestamp.fromDate(DateTime(due!.year, due!.month, due!.day, 12)),""")
    # V20 on a phone the floating desk button covered the end of "Save profile": it is hidden while the editor
    #     is open (see V26). Squeezing the save bar instead overflowed it at 375 px.
    # V21 the preferred-vendor picker let the same vendor be added twice: one already on the list reads "Added"
    rep("""        Widget resultRow(Map<String, dynamic> r) {
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
              },""", """        Widget resultRow(Map<String, dynamic> r) {
          final String metro = _metroLabel(r['metroId'].toString());
          final bool already = _epPreferred.any((Map<String, dynamic> p) =>
              (p['placeId'] ?? '').toString() == (r['placeId'] ?? '').toString());
          return Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: _Press(
              scale: .985,
              onTap: already
                  ? () => _toast('${r['name']} is already on your list.')
                  : () {
                      setState(() {
                        _epPreferred.add(r);
                      });
                      Navigator.pop(ctx);
                    },""")
    rep("""                  const Icon(Icons.add_circle_outline_rounded, color: gold, size: 22),""",
        """                  already
                      ? Text('Added', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700, color: _lzFg(vGreen)))
                      : const Icon(Icons.add_circle_outline_rounded, color: gold, size: 22),""")
    # V22 the profile editor's switch rows sat in coloured cards with no Material: Flutter logged "ListTile
    #     background color or ink splashes may be invisible" on every scroll. Same row, transparent Material behind it.
    n_sw = s.count("SwitchListTile(")
    assert n_sw == 9, n_sw
    s = s.replace("SwitchListTile(", "_LzSwitchTile(")
    s = s.rstrip("\n") + '''

/// SwitchListTile with a transparent Material behind it, so its ink draws on coloured cards (JC-LAZO-POPUP-1014).
class _LzSwitchTile extends StatelessWidget {
  const _LzSwitchTile({
    required this.value,
    required this.title,
    required this.onChanged,
    this.dense,
    this.contentPadding,
    this.activeTrackColor,
    this.activeColor,
  });
  final bool value;
  final Widget title;
  final ValueChanged<bool>? onChanged;
  final bool? dense;
  final EdgeInsetsGeometry? contentPadding;
  final Color? activeTrackColor;
  final Color? activeColor;

  @override
  Widget build(BuildContext context) => Material(
        type: MaterialType.transparency,
        child: SwitchListTile(
          value: value,
          title: title,
          onChanged: onChanged,
          dense: dense,
          contentPadding: contentPadding,
          activeTrackColor: activeTrackColor,
          activeColor: activeColor,
        ),
      );
}
'''
    # V23 every "e.message ?? 'fallback'" (Square, payment plan, contract generate, checkout, Whop, delete...) showed a
    #     bare "internal [0]" when the server failed: all go through _lzFnMsg (real messages still pass through)
    import re as _re
    s, n_msg = _re.subn(r"e\.message \?\?\s*('(?:[^'\\]|\\.)+')", r"_lzFnMsg(e, \1)", s)
    assert n_msg >= 18, n_msg
    # V24 the hello sheet still said "Nobody to greet" when the couple search failed
    rep("""                    _v4Empty(Icons.event_available_rounded,
                        'Nobody to greet right now. New couples set their date every week - check back.'),""",
        """                    _v4Empty(Icons.event_available_rounded,
                        h['error'] != null
                            ? 'Couldn\\u2019t load couples right now. Check your connection and try again soon.'
                            : 'Nobody to greet right now. New couples set their date every week - check back.'),""")
    # V25 the proposal card in the thread read "$1251": real money format, cents kept
    rep("""                          '\\$${((p['price'] ?? 0) as num).toStringAsFixed(0)} \\u00b7 ${st == 'sent'""",
        """                          '${_invMoney((p['price'] ?? 0) as num)} \\u00b7 ${st == 'sent'""")
    # V26 on a phone the floating desk button covered the thread's Send button: hidden while the inbox is open
    rep("""            if (_uid != null && MediaQuery.of(context).size.width < 1100)
              _vendorFab(),""", """            if (_uid != null && MediaQuery.of(context).size.width < 1100 && !_showInbox && !_editingProfile)
              _vendorFab(),""")
    # V27 dark mode: the brand preview remapped the vendor's own colours (a Blush button rendered plum)
    rep("""                child: Container(
                  color: _lzBg(pCol),
                  padding: const EdgeInsets.fromLTRB(20, 22, 20, 20),""", """                child: Container(
                  color: pCol,
                  padding: const EdgeInsets.fromLTRB(20, 22, 20, 20),""")
    rep("""                        decoration: BoxDecoration(
                            color: _lzBg(Colors.white),
                            borderRadius: BorderRadius.circular(13)),
                        child: Image.network(logo, fit: BoxFit.contain),""", """                        decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(13)),
                        child: Image.network(logo, fit: BoxFit.contain),""")
    rep("""                    Text(name.toUpperCase(),
                        style: TextStyle(
                            color: _lzFg(aCol),""", """                    Text(name.toUpperCase(),
                        style: TextStyle(
                            color: aCol,""")
    rep("""                      decoration: BoxDecoration(
                          color: _lzBg(aCol),
                          borderRadius: BorderRadius.circular(10)),
                      child: Text('Pay \\$500',
                          style: TextStyle(
                              color: _lzFg(pCol),""", """                      decoration: BoxDecoration(
                          color: aCol,
                          borderRadius: BorderRadius.circular(10)),
                      child: Text('Pay \\$500',
                          style: TextStyle(
                              color: pCol,""")
    # V28 a flat automatic retainer with no amount saved $0 ("Saved - $0 at signing")
    rep("""        Future<void> save() async {
          final num flat = num.tryParse(flatC.text.trim()) ?? 0;
          up(() {
            busy = true;
            err = '';
          });""", """        Future<void> save() async {
          final num flat = num.tryParse(flatC.text.replaceAll(RegExp(r'[^0-9.]'), '')) ?? 0;
          if (mode == 'flat' && flat <= 0) {
            up(() => err = 'Enter the retainer amount, or pick another option.');
            return;
          }
          up(() {
            busy = true;
            err = '';
          });""")
    # V17 the FAQ card said "Up to 6"; the editor allows 15
    rep("""            'The questions couples always ask - answered once, shown on your profile. Up to 6.',""",
        """            'The questions couples always ask - answered once, shown on your profile. Up to 15.',""")
    return s
