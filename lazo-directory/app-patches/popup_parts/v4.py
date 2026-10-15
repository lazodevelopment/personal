# Popup pass JC-LAZO-POPUP-1014, part v4 (vendor dashboard).
# Rebuilds the popups in: _practiceStrip, _fitSheet, _prefsSheet, _toggleShowcase,
# _helloSheet, _helloCompose, _addTeammateSheet, _editTeammate, _recommendTeamSheet,
# _editMessageDialog, _emojiSheet, _needsBooked, _teaserSheet, _sneakPeekSheet,
# _savedRepliesSheet, _savedReplyEditor, _teamSheet, _redeemInviteDialog,
# _calendarFeedSheet, _bookingStatusSheet. Helpers (_v4*) sit right after _practiceStrip.


def apply(s: str) -> str:
    def rep(old, new):
        nonlocal s
        assert s.count(old) == 1, (s.count(old), old[:80])
        s = s.replace(old, new)

    def func(sig, end, new):
        # The whole function, from its signature up to (not including) the text
        # that follows it. Both must be unique, so the slice is exact.
        assert s.count(sig) == 1, (s.count(sig), sig)
        i = s.index(sig)
        j = s.index(end, i)
        rep(s[i:j], new.strip('\n'))

    # ------------------------------------------------------------------
    # _practiceStrip + v4 helpers
    # ------------------------------------------------------------------
    func("  Widget _practiceStrip(\n",
         "\n\n  // ===================================================================\n  // v171: FIT GRADE",
         r"""
  Widget _practiceStrip(
      String inquiryId, Map<String, dynamic> inq, String vendorId) {
    if (inq['demo'] != true) return const SizedBox.shrink();
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 10, 16, 0),
      padding: const EdgeInsets.fromLTRB(14, 11, 12, 11),
      decoration: BoxDecoration(
        gradient: const LinearGradient(colors: <Color>[plumDeep, plum]),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: gold.withOpacity(.8)),
      ),
      child: Row(children: <Widget>[
        const Icon(Icons.school_rounded, color: gold, size: 18),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                const Text('PRACTICE COUPLE \u00b7 NOT A REAL INQUIRY',
                    style: TextStyle(
                        color: gold,
                        fontSize: 10,
                        letterSpacing: 1.6,
                        fontWeight: FontWeight.w800)),
                const SizedBox(height: 3),
                Text(
                    'Jordan & Sam are played by June so you can learn the dashboard. Reply, send a proposal, a contract, an invoice, a booking link, mark them booked - they answer within a minute. Nothing here counts toward your stats or money.',
                    style: TextStyle(
                        color: ivory.withOpacity(.9),
                        fontSize: 11.5,
                        height: 1.35)),
              ]),
        ),
        const SizedBox(width: 8),
        TextButton(
          style: TextButton.styleFrom(
              foregroundColor: plumDeep,
              backgroundColor: gold,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10))),
          onPressed: _h(() async {
            final bool ok = await _v4ConfirmRun(
              title: 'Done practicing?',
              body:
                  'This deletes the practice thread and everything in it. You can start a fresh one any time from Account.',
              confirm: 'Delete practice thread',
              cancel: 'Keep it',
              danger: true,
              busyLabel: 'Clearing the practice thread\u2026',
              run: () async {
                try {
                  await FirebaseFunctions.instance
                      .httpsCallable('demoEnd')
                      .call(<String, dynamic>{'vendorId': vendorId});
                  return null;
                } catch (e) {
                  return 'Couldn\u2019t delete it: ' + _errText(e);
                }
              },
            );
            if (!ok) return;
            if (mounted) setState(() => _showInbox = false);
            _toast('Practice thread deleted. You know the room now.');
          }),
          child: const Text('Done practicing',
              style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800)),
        ),
      ]),
    );
  }

  // ---------------- v4 popup helpers (JC-LAZO-POPUP-1014) ----------------
  /// An inline error inside a popup.
  Widget _v4Err(String err) => err.isEmpty
      ? const SizedBox.shrink()
      : Padding(
          padding: const EdgeInsets.only(top: 12),
          child: Container(
            padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
            decoration: BoxDecoration(
                color: _lzBg(const Color(0xFFFBEAEA)),
                borderRadius: BorderRadius.circular(13)),
            child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  const Icon(Icons.error_outline_rounded,
                      size: 18, color: Color(0xFFB3261E)),
                  const SizedBox(width: 10),
                  Expanded(
                      child: Text(err,
                          style: TextStyle(
                              fontSize: 13.5, color: _lzFg(ink), height: 1.4))),
                ]),
          ),
        );

  /// A pill choice (event types, days, categories).
  Widget _v4Chip(String label, bool on, VoidCallback onTap) => _Press(
        scale: .97,
        tick: _Tick.select,
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 160),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          decoration: BoxDecoration(
              color: on ? plumDeep : _lzBg(card),
              borderRadius: BorderRadius.circular(30),
              border: Border.all(color: on ? plumDeep : _lzLine(goldLine))),
          child: Text(label,
              style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  color: on ? gold : _lzFg(plum))),
        ),
      );

  /// A row card; tappable when onTap is given, gold-edged when on.
  Widget _v4Card(
      {required Widget child,
      bool on = false,
      VoidCallback? onTap,
      EdgeInsets padding = const EdgeInsets.fromLTRB(14, 12, 12, 12)}) {
    final Widget box = AnimatedContainer(
      duration: const Duration(milliseconds: 160),
      margin: const EdgeInsets.only(bottom: 8),
      padding: padding,
      decoration: BoxDecoration(
          color: _lzBg(card),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
              color: on ? gold : _lzLine(goldLine), width: on ? 1.5 : 1)),
      child: child,
    );
    if (onTap == null) return box;
    return _Press(scale: .985, onTap: onTap, child: box);
  }

  /// A number with a label under it.
  Widget _v4Stat(String n, String label) => Expanded(
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
          decoration: BoxDecoration(
              color: _lzBg(card),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: _lzLine(goldLine))),
          child: Column(children: <Widget>[
            Text(n, style: _serif(size: 26)),
            const SizedBox(height: 2),
            Text(label,
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 12, color: _lzFg(muted))),
          ]),
        ),
      );

  /// Empty state inside a popup: an icon, one line, and the action.
  Widget _v4Empty(IconData icon, String line,
          {String? action, VoidCallback? onAction}) =>
      Padding(
        padding: const EdgeInsets.symmetric(vertical: 26),
        child: Column(children: <Widget>[
          Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                  color: _lzBg(const Color(0xFFF6EEDF)),
                  shape: BoxShape.circle),
              child: Icon(icon, color: _lzFg(plum), size: 26)),
          const SizedBox(height: 12),
          Text(line,
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 14, color: _lzFg(muted), height: 1.45)),
          if (action != null && onAction != null) ...<Widget>[
            const SizedBox(height: 14),
            FilledButton.icon(
                style: FilledButton.styleFrom(
                    backgroundColor: gold,
                    foregroundColor: plumDeep,
                    minimumSize: const Size(0, 44),
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12))),
                onPressed: _h(onAction),
                icon: const Icon(Icons.add_rounded, size: 18),
                label: Text(action,
                    style: const TextStyle(fontWeight: FontWeight.w700))),
          ],
        ]),
      );

  /// A yes/no that does its work inside the popup: spinner on the button,
  /// errors shown in place. run returns null on success or the error to show.
  Future<bool> _v4ConfirmRun({
    required String title,
    required String body,
    required String confirm,
    String cancel = 'Not now',
    bool danger = false,
    IconData? icon,
    String busyLabel = '',
    required Future<String?> Function() run,
  }) async {
    if (!mounted) return false;
    bool open = true;
    bool busy = false;
    bool done = false;
    String err = '';
    final bool? ok = await _lzSheet<bool>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 480),
      builder: (BuildContext ctx) => StatefulBuilder(
          builder: (BuildContext sc, StateSetter set) {
        void up(VoidCallback f) {
          if (open) set(f);
        }

        return _lzFrame(ctx,
            icon: icon ?? (danger ? Icons.warning_amber_rounded : null),
            title: title,
            children: <Widget>[
              Text(body,
                  style:
                      TextStyle(fontSize: 14.5, color: _lzFg(ink), height: 1.5)),
              if (busy && busyLabel.isNotEmpty) ...<Widget>[
                const SizedBox(height: 14),
                _lzBusy(busyLabel),
              ],
              _v4Err(err),
            ],
            footer: _lzActions(
                secondary: cancel,
                onSecondary: () => Navigator.pop(ctx, false),
                primary: confirm,
                danger: danger,
                busy: busy,
                icon:
                    danger ? Icons.delete_outline_rounded : Icons.check_rounded,
                onPrimary: () async {
                  up(() {
                    busy = true;
                    err = '';
                  });
                  final String? e = await run();
                  if (e == null) {
                    done = true;
                    if (open && ctx.mounted) Navigator.pop(ctx, true);
                  } else {
                    up(() {
                      busy = false;
                      err = e;
                    });
                  }
                }));
      }),
    );
    open = false;
    return ok == true || done;
  }
""")

    # ------------------------------------------------------------------
    # _fitSheet
    # ------------------------------------------------------------------
    func("  Future<void> _fitSheet(",
         "\n\n  Widget _prefsCard(",
         r"""
  Future<void> _fitSheet(Map<String, dynamic> inq, _Fit fit) async {
    const Color bad = Color(0xFFB04343);
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 520),
      builder: (BuildContext ctx) => _lzFrame(ctx,
          icon: Icons.stars_rounded,
          title: '${fit.grade} fit',
          subtitle:
              'How ${(inq['coupleName'] ?? 'this couple').toString()} lines up with your Who I work with settings. A nudge, not a verdict.',
          children: <Widget>[
            const SizedBox(height: 14),
            Row(children: <Widget>[
              Text('${fit.score}', style: _serif(size: 36)),
              Padding(
                padding: const EdgeInsets.only(top: 8, left: 2),
                child: Text('/ 100',
                    style: TextStyle(fontSize: 13, color: _lzFg(muted))),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(99),
                  child: LinearProgressIndicator(
                      value: fit.score / 100,
                      minHeight: 8,
                      backgroundColor: _lzLine(goldLine).withOpacity(.55),
                      valueColor: AlwaysStoppedAnimation<Color>(fit.color)),
                ),
              ),
            ]),
            _lzSection('What went into it'),
            ...fit.why.map((List<dynamic> w) {
              final int pts = w[1] as int;
              final Color tone = pts > 0 ? vGreen : (pts < 0 ? bad : muted);
              return _v4Card(
                child: Row(children: <Widget>[
                  Icon(
                      pts > 0
                          ? Icons.add_circle_rounded
                          : (pts < 0
                              ? Icons.remove_circle_rounded
                              : Icons.circle_outlined),
                      size: 18,
                      color: _lzFg(tone)),
                  const SizedBox(width: 10),
                  Expanded(
                      child: Text(w[0] as String,
                          style: TextStyle(
                              color: _lzFg(ink), fontSize: 14, height: 1.35))),
                  if (pts != 0)
                    Container(
                      margin: const EdgeInsets.only(left: 8),
                      padding:
                          const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                          color: tone.withOpacity(.12),
                          borderRadius: BorderRadius.circular(20)),
                      child: Text(pts > 0 ? '+$pts' : '$pts',
                          style: TextStyle(
                              color: _lzFg(tone),
                              fontSize: 12,
                              fontWeight: FontWeight.w800)),
                    ),
                ]),
              );
            }),
          ],
          footer: _lzActions(
              secondary: 'Close',
              onSecondary: () => Navigator.pop(ctx),
              primary: 'Edit who I work with',
              icon: Icons.tune_rounded,
              onPrimary: () {
                Navigator.pop(ctx);
                _prefsSheet(_vendorIdCache);
              })),
    );
  }
""")

    # ------------------------------------------------------------------
    # _prefsSheet
    # ------------------------------------------------------------------
    func("  Future<void> _prefsSheet(String vendorId) async {",
         "\n\n  Widget _realWeddingsCard(",
         r"""
  Future<void> _prefsSheet(String vendorId) async {
    final Map<String, dynamic> vd =
        _liveD['vendor:$vendorId']?.latest?.data() ?? <String, dynamic>{};
    final Map<String, dynamic> p =
        Map<String, dynamic>.from((vd['prefs'] as Map?) ?? <String, dynamic>{});
    final TextEditingController minC = TextEditingController(
        text: p['minBudget'] is num && (p['minBudget'] as num) > 0
            ? (p['minBudget'] as num).round().toString()
            : '');
    final TextEditingController gMinC = TextEditingController(
        text: p['guestMin'] is num && (p['guestMin'] as num) > 0
            ? (p['guestMin'] as num).round().toString()
            : '');
    final TextEditingController gMaxC = TextEditingController(
        text: p['guestMax'] is num && (p['guestMax'] as num) > 0
            ? (p['guestMax'] as num).round().toString()
            : '');
    final TextEditingController travelC = TextEditingController(
        text: p['travelMiles'] is num && (p['travelMiles'] as num) > 0
            ? (p['travelMiles'] as num).round().toString()
            : '');
    final TextEditingController noteC =
        TextEditingController(text: (p['note'] ?? '').toString());
    final Set<String> types = <String>{
      ...((p['eventTypes'] as List?) ?? const <dynamic>[])
          .map((dynamic e) => e.toString())
    };
    final Set<int> daysOff = <int>{
      ...((p['daysOff'] as List?) ?? const <dynamic>[])
          .map((dynamic e) => (e as num).toInt())
    };
    bool saving = false;
    bool open = true;
    String err = '';
    if (!mounted) return;
    const List<String> dayNames = <String>[
      'Sun',
      'Mon',
      'Tue',
      'Wed',
      'Thu',
      'Fri',
      'Sat'
    ];
    final TextStyle fieldStyle = TextStyle(color: _lzFg(ink), fontSize: 14.5);
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 640),
      builder: (BuildContext ctx) =>
          StatefulBuilder(builder: (BuildContext sc, StateSetter setSheet) {
        void up(VoidCallback f) {
          if (open) setSheet(f);
        }

        Future<void> save() async {
          up(() {
            saving = true;
            err = '';
          });
          try {
            await FirebaseFirestore.instance
                .collection('vendors')
                .doc(vendorId)
                .set(<String, dynamic>{
              'prefs': <String, dynamic>{
                'minBudget':
                    num.tryParse(minC.text.replaceAll(RegExp(r'[^\d.]'), '')) ??
                        0,
                'guestMin': int.tryParse(gMinC.text.trim()) ?? 0,
                'guestMax': int.tryParse(gMaxC.text.trim()) ?? 0,
                'travelMiles': int.tryParse(travelC.text.trim()) ?? 0,
                'eventTypes': types.toList(),
                'daysOff': daysOff.toList(),
                'note': noteC.text.trim(),
                'updatedAt': FieldValue.serverTimestamp(),
              }
            }, SetOptions(merge: true));
            if (ctx.mounted) Navigator.pop(ctx);
            _toast('Saved - your leads are graded against it from now on.');
          } catch (e) {
            up(() {
              saving = false;
              err = 'Couldn\u2019t save: ' + _errText(e);
            });
          }
        }

        return _lzFrame(ctx,
            icon: Icons.tune_rounded,
            title: 'Who I work with',
            subtitle:
                'Every lead gets a Fit grade against this, and your public page says it plainly.',
            children: <Widget>[
              _lzSection('Budget'),
              TextField(
                  controller: minC,
                  keyboardType: TextInputType.number,
                  style: fieldStyle,
                  decoration:
                      _epDeco('Minimum budget', 'The smallest job you take')
                          .copyWith(prefixText: '\u0024 ')),
              _lzSection('Guest count'),
              Row(children: <Widget>[
                Expanded(
                    child: TextField(
                        controller: gMinC,
                        keyboardType: TextInputType.number,
                        inputFormatters: <TextInputFormatter>[
                          FilteringTextInputFormatter.digitsOnly
                        ],
                        style: fieldStyle,
                        decoration: _epDeco('From', 'Any'))),
                Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 10),
                    child: Text('to', style: TextStyle(color: _lzFg(muted)))),
                Expanded(
                    child: TextField(
                        controller: gMaxC,
                        keyboardType: TextInputType.number,
                        inputFormatters: <TextInputFormatter>[
                          FilteringTextInputFormatter.digitsOnly
                        ],
                        style: fieldStyle,
                        decoration: _epDeco('Up to', 'Any'))),
              ]),
              _lzSection('Event types'),
              Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                for (final List<String> t in _kEventTypes)
                  _v4Chip(
                      t[1],
                      types.contains(t[0]),
                      () => up(() {
                            if (!types.remove(t[0])) types.add(t[0]);
                          })),
              ]),
              _lzSection('Days I don\u2019t take'),
              Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                for (int d = 0; d < 7; d++)
                  _v4Chip(
                      dayNames[d],
                      daysOff.contains(d),
                      () => up(() {
                            if (!daysOff.remove(d)) daysOff.add(d);
                          })),
              ]),
              _lzSection('Travel'),
              TextField(
                  controller: travelC,
                  keyboardType: TextInputType.number,
                  inputFormatters: <TextInputFormatter>[
                    FilteringTextInputFormatter.digitsOnly
                  ],
                  style: fieldStyle,
                  decoration: _epDeco('Miles without a travel fee',
                      'From your home base')),
              _lzSection('One line for couples'),
              TextField(
                  controller: noteC,
                  maxLength: 140,
                  textCapitalization: TextCapitalization.sentences,
                  style: fieldStyle,
                  decoration: _epDeco('On your public page',
                      '\u201cIntimate weddings and elopements are my favorite\u201d')),
              const SizedBox(height: 4),
              _lzNote(Icons.visibility_outlined,
                  'Couples see your minimum (\u201cBooks weddings from \u00244,000\u201d) before they inquire, so the ones who reach out are the right ones.'),
              _v4Err(err),
            ],
            footer: _lzActions(
                secondary: 'Cancel',
                onSecondary: () => Navigator.pop(ctx),
                primary: 'Save',
                icon: Icons.check_rounded,
                busy: saving,
                onPrimary: save));
      }),
    );
    open = false;
  }
""")

    # ------------------------------------------------------------------
    # _toggleShowcase
    # ------------------------------------------------------------------
    func("  Future<void> _toggleShowcase(",
         "\n\n  // ===================================================================\n  // v172: SAY HELLO",
         r"""
  Future<void> _toggleShowcase(
      String vendorId, String slug, Map<String, dynamic> g, bool on) async {
    bool consent = false;
    final TextEditingController titleC = TextEditingController(
        text: (g['showcaseTitle'] ?? g['names'] ?? '').toString());
    final TextEditingController blurbC =
        TextEditingController(text: (g['showcaseBlurb'] ?? '').toString());
    Future<String?> push() async {
      try {
        await FirebaseFunctions.instance
            .httpsCallable('galleryShowcase')
            .call(<String, dynamic>{
          'vendorId': vendorId,
          'slug': slug,
          'on': on,
          'consent': consent,
          'title': titleC.text.trim(),
          'blurb': blurbC.text.trim(),
        });
        return null;
      } on FirebaseFunctionsException catch (e) {
        return e.message ?? 'Could not update.';
      } catch (e) {
        return _errText(e);
      }
    }

    if (on) {
      if (!mounted) return;
      bool open = true;
      bool busy = false;
      String err = '';
      await _lzSheet<void>(
        context: context,
        constraints: const BoxConstraints(maxWidth: 560),
        builder: (BuildContext ctx) => StatefulBuilder(
            builder: (BuildContext sc, StateSetter set) {
          void up(VoidCallback f) {
            if (open) set(f);
          }

          return _lzFrame(ctx,
              icon: Icons.public_rounded,
              title: 'Show this wedding publicly?',
              subtitle:
                  'A page at meetlazo.com/real/$slug that Google can find, and a spot on your profile.',
              children: <Widget>[
                const SizedBox(height: 14),
                TextField(
                    controller: titleC,
                    enabled: !busy,
                    textCapitalization: TextCapitalization.words,
                    style: TextStyle(color: _lzFg(ink), fontSize: 14.5),
                    decoration:
                        _epDeco('Title', 'Mindy & John at The Farm')),
                const SizedBox(height: 12),
                TextField(
                    controller: blurbC,
                    enabled: !busy,
                    minLines: 2,
                    maxLines: 4,
                    textCapitalization: TextCapitalization.sentences,
                    style: TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _epDeco('About the day (optional)',
                        'One or two lines about the day')),
                const SizedBox(height: 14),
                _v4Card(
                  on: consent,
                  onTap: busy ? null : () => up(() => consent = !consent),
                  child: Row(children: <Widget>[
                    Icon(
                        consent
                            ? Icons.check_box_rounded
                            : Icons.check_box_outline_blank_rounded,
                        color: _lzFg(consent ? plum : muted),
                        size: 22),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Text('The couple agreed to be featured',
                                style: TextStyle(
                                    color: _lzFg(ink),
                                    fontSize: 14,
                                    fontWeight: FontWeight.w700)),
                            const SizedBox(height: 2),
                            Text('Needed before it goes live.',
                                style: TextStyle(
                                    fontSize: 12.5, color: _lzFg(muted))),
                          ]),
                    ),
                  ]),
                ),
                const SizedBox(height: 4),
                _lzNote(Icons.lock_outline_rounded,
                    'Their private gallery and downloads stay private.'),
                _v4Err(err),
              ],
              footer: _lzActions(
                  secondary: 'Not now',
                  onSecondary: () => Navigator.pop(ctx),
                  primary: 'Show it',
                  icon: Icons.public_rounded,
                  busy: busy,
                  onPrimary: consent
                      ? () async {
                          up(() {
                            busy = true;
                            err = '';
                          });
                          final String? e = await push();
                          if (e == null) {
                            if (open && ctx.mounted) Navigator.pop(ctx);
                            _toast('Live at meetlazo.com/real/$slug');
                          } else {
                            up(() {
                              busy = false;
                              err = e;
                            });
                          }
                        }
                      : null));
        }),
      );
      open = false;
      return;
    }
    _showJuneVeil('Taking it down\u2026', 'One moment.');
    final String? e = await push();
    _popJuneVeil();
    _toast(e ?? 'Removed from your public page.');
  }
""")

    # ------------------------------------------------------------------
    # _helloSheet
    # ------------------------------------------------------------------
    func("  Future<void> _helloSheet(String vendorId",
         "\n\n  Future<bool> _helloCompose(",
         r"""
  Future<void> _helloSheet(String vendorId, Map<String, dynamic> vd) async {
    await _loadHellos(vendorId, force: true);
    if (!mounted) return;
    final Map<String, dynamic> h = _helloCache ?? <String, dynamic>{};
    final List<Map<String, dynamic>> matches =
        ((h['matches'] as List?) ?? const <dynamic>[])
            .map((dynamic e) => Map<String, dynamic>.from(e as Map))
            .toList();
    int cap = (h['cap'] is num) ? (h['cap'] as num).toInt() : 10;
    int used = (h['used'] is num) ? (h['used'] as num).toInt() : 0;
    final Set<String> done = <String>{};
    bool open = true;
    const List<String> dow = <String>[
      'Sun',
      'Mon',
      'Tue',
      'Wed',
      'Thu',
      'Fri',
      'Sat'
    ];
    // rank by fit against the vendor's prefs
    for (final Map<String, dynamic> m in matches) {
      final Map<String, dynamic> fake = <String, dynamic>{
        'structuredIntent': <String, dynamic>{
          'weddingDate': m['dateIso'],
          'budget': m['budget'] is num && (m['budget'] as num) > 0
              ? '\u0024${(m['budget'] as num).round()}'
              : '',
          'message': ''
        },
      };
      m['_fit'] = _fitOf(fake, vd);
    }
    matches.sort((Map<String, dynamic> a, Map<String, dynamic> b) =>
        ((b['_fit'] as _Fit).score).compareTo((a['_fit'] as _Fit).score));

    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 680),
      builder: (BuildContext ctx) =>
          StatefulBuilder(builder: (BuildContext sc, StateSetter setSheet) {
        final int left = cap - used < 0 ? 0 : cap - used;
        return _lzFrame(ctx,
            icon: Icons.waving_hand_rounded,
            title: 'Say hello first',
            subtitle:
                'Couples who set a date and still need you. Names appear only if they write back.',
            headerExtra: Row(children: <Widget>[
              _v4Stat('${matches.length}',
                  matches.length == 1 ? 'couple' : 'couples'),
              const SizedBox(width: 8),
              _v4Stat('$left',
                  left == 1 ? 'hello left this week' : 'hellos left this week'),
            ]),
            children: matches.isEmpty
                ? <Widget>[
                    _v4Empty(Icons.event_available_rounded,
                        'Nobody to greet right now. New couples set their date every week - check back.'),
                  ]
                : <Widget>[
                    const SizedBox(height: 12),
                    for (final Map<String, dynamic> m in matches)
                      Builder(builder: (BuildContext bc) {
                        final _Fit fit = m['_fit'] as _Fit;
                        final String cid = (m['coupleUid'] ?? '').toString();
                        final bool sent = done.contains(cid);
                        final List<dynamic> needs =
                            (m['needs'] as List?) ?? const <dynamic>[];
                        return _v4Card(
                          on: !sent,
                          child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                Row(children: <Widget>[
                                  Container(
                                    width: 40,
                                    height: 40,
                                    alignment: Alignment.center,
                                    decoration: BoxDecoration(
                                        color: plumDeep,
                                        borderRadius:
                                            BorderRadius.circular(12)),
                                    child: const Icon(Icons.favorite_rounded,
                                        color: gold, size: 18),
                                  ),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: <Widget>[
                                          Text(
                                              'A couple \u00b7 ${m['monthLabel']}${m['dow'] is num ? ' \u00b7 ${dow[(m['dow'] as num).toInt()]}' : ''}',
                                              style: TextStyle(
                                                  color: _lzFg(ink),
                                                  fontSize: 14.5,
                                                  fontWeight: FontWeight.w800)),
                                          const SizedBox(height: 2),
                                          Text(
                                              '${(m['budgetBand'] ?? '').toString().isEmpty ? 'Budget not set' : 'Budget ' + m['budgetBand']}${m['planningDays'] is num ? ' \u00b7 planning ${(m['planningDays'] as num).toInt() < 7 ? 'this week' : '${((m['planningDays'] as num) / 7).round()} wk'}' : ''}',
                                              style: TextStyle(
                                                  fontSize: 12.5,
                                                  color: _lzFg(muted))),
                                        ]),
                                  ),
                                  Container(
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 9, vertical: 4),
                                    decoration: BoxDecoration(
                                        color:
                                            _lzBg(fit.color.withOpacity(.14)),
                                        borderRadius:
                                            BorderRadius.circular(999),
                                        border: Border.all(
                                            color: _lzLine(
                                                fit.color.withOpacity(.6)))),
                                    child: Text('${fit.grade} fit',
                                        style: TextStyle(
                                            color: _lzFg(fit.color == gold
                                                ? const Color(0xFF8A6A2F)
                                                : fit.color),
                                            fontSize: 11,
                                            fontWeight: FontWeight.w800)),
                                  ),
                                ]),
                                if (needs.isNotEmpty) ...<Widget>[
                                  const SizedBox(height: 10),
                                  Wrap(
                                      spacing: 6,
                                      runSpacing: 6,
                                      children: <Widget>[
                                        for (final dynamic n in needs.take(4))
                                          Container(
                                            padding: const EdgeInsets.symmetric(
                                                horizontal: 9, vertical: 4),
                                            decoration: BoxDecoration(
                                                color: _lzBg(
                                                    const Color(0xFFF6EEDF)),
                                                borderRadius:
                                                    BorderRadius.circular(20)),
                                            child: Text(
                                                n
                                                    .toString()
                                                    .replaceFirst('wedding-', '')
                                                    .replaceAll('-', ' '),
                                                style: TextStyle(
                                                    fontSize: 11.5,
                                                    color: _lzFg(plum),
                                                    fontWeight:
                                                        FontWeight.w600)),
                                          ),
                                        if (needs.length > 4)
                                          Padding(
                                            padding:
                                                const EdgeInsets.only(top: 4),
                                            child: Text(
                                                '+${needs.length - 4} more',
                                                style: TextStyle(
                                                    fontSize: 11.5,
                                                    color: _lzFg(muted))),
                                          ),
                                      ]),
                                ],
                                const SizedBox(height: 10),
                                Align(
                                  alignment: Alignment.centerRight,
                                  child: sent
                                      ? Row(
                                          mainAxisSize: MainAxisSize.min,
                                          children: <Widget>[
                                              Icon(Icons.check_circle_rounded,
                                                  color: _lzFg(vGreen),
                                                  size: 17),
                                              const SizedBox(width: 6),
                                              Text('Hello sent',
                                                  style: TextStyle(
                                                      color: _lzFg(vGreen),
                                                      fontSize: 13,
                                                      fontWeight:
                                                          FontWeight.w800)),
                                            ])
                                      : FilledButton.icon(
                                          style: FilledButton.styleFrom(
                                              backgroundColor: plum,
                                              foregroundColor: ivory,
                                              disabledBackgroundColor:
                                                  muted.withOpacity(.35),
                                              elevation: 0,
                                              minimumSize: const Size(0, 42),
                                              padding:
                                                  const EdgeInsets.symmetric(
                                                      horizontal: 16),
                                              shape: RoundedRectangleBorder(
                                                  borderRadius:
                                                      BorderRadius.circular(
                                                          12))),
                                          onPressed: _h(used >= cap
                                              ? null
                                              : () async {
                                                  final bool ok =
                                                      await _helloCompose(
                                                          vendorId, vd, m);
                                                  if (ok && open)
                                                    setSheet(() {
                                                      done.add(cid);
                                                      used++;
                                                    });
                                                }),
                                          icon: const Icon(
                                              Icons.waving_hand_rounded,
                                              size: 16),
                                          label: Text(
                                              used >= cap
                                                  ? 'Out of hellos this week'
                                                  : 'Say hello',
                                              style: const TextStyle(
                                                  fontSize: 13,
                                                  fontWeight:
                                                      FontWeight.w800)),
                                        ),
                                ),
                              ]),
                        );
                      }),
                  ],
            footer: _lzActions(
                primary: 'Done',
                icon: Icons.check_rounded,
                onPrimary: () => Navigator.pop(ctx)));
      }),
    );
    open = false;
    _loadHellos(vendorId, force: true);
  }
""")

    # ------------------------------------------------------------------
    # _helloCompose
    # ------------------------------------------------------------------
    func("  Future<bool> _helloCompose(",
         "\n\n  // ===================================================================\n  // v173: YOUR TEAM",
         r"""
  Future<bool> _helloCompose(
      String vendorId, Map<String, dynamic> vd, Map<String, dynamic> m) async {
    final String first =
        (FirebaseAuth.instance.currentUser?.displayName ?? '').split(' ').first;
    final String cat = (vd['category'] ?? '')
        .toString()
        .replaceFirst('wedding-', '')
        .replaceAll('-', ' ');
    final TextEditingController c = TextEditingController(
        text:
            'Hi! ${first.isEmpty ? 'I\u2019m' : 'I\u2019m $first,'} with ${vd['name'] ?? 'our studio'} here in ${(vd['metroId'] ?? '').toString().split('-').map((String p) => p.isEmpty ? p : p[0].toUpperCase() + p.substring(1)).join(' ')}. '
            'I saw you\u2019re getting married ${m['monthLabel']} and still looking for ${cat.isEmpty ? 'someone' : 'a ' + cat.replaceFirst(RegExp(r's$'), '')} - that date is open on my calendar. '
            'No pressure at all; if it\u2019s helpful I\u2019d love to share what a day with us looks like.');
    bool busy = false;
    bool open = true;
    String err = '';
    bool sent = false;
    if (!mounted) return false;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 620),
      builder: (BuildContext ctx) => StatefulBuilder(
          builder: (BuildContext sc, StateSetter setSheet) {
        void up(VoidCallback f) {
          if (open) setSheet(f);
        }

        Future<void> send() async {
          up(() {
            busy = true;
            err = '';
          });
          try {
            await FirebaseFunctions.instance
                .httpsCallable('helloSend')
                .call(<String, dynamic>{
              'vendorId': vendorId,
              'coupleUid': m['coupleUid'],
              'text': c.text.trim(),
            });
            sent = true;
            if (ctx.mounted) Navigator.pop(ctx);
            _toast('Hello sent - it\u2019s a thread in your inbox now.');
          } on FirebaseFunctionsException catch (e) {
            up(() {
              busy = false;
              err = e.message ?? 'Couldn\u2019t send. Try again.';
            });
          } catch (e) {
            up(() {
              busy = false;
              err = _errText(e);
            });
          }
        }

        return _lzFrame(ctx,
            icon: Icons.waving_hand_rounded,
            title: 'Your hello',
            subtitle:
                'To a couple marrying ${m['monthLabel']}. It lands in their email and Lazo inbox, with your page attached.',
            children: <Widget>[
              const SizedBox(height: 14),
              TextField(
                controller: c,
                enabled: !busy,
                minLines: 5,
                maxLines: 10,
                maxLength: 1200,
                textCapitalization: TextCapitalization.sentences,
                onChanged: (_) => up(() {}),
                style: TextStyle(color: _lzFg(ink), fontSize: 14.5, height: 1.45),
                decoration: _epDeco('Message', 'Say hello'),
              ),
              _lzNote(Icons.tips_and_updates_outlined,
                  'Short and human wins - a few lines about you and their date.'),
              _v4Err(err),
            ],
            footer: _lzActions(
                secondary: 'Cancel',
                onSecondary: () => Navigator.pop(ctx),
                primary: 'Send hello',
                icon: Icons.send_rounded,
                busy: busy,
                onPrimary: c.text.trim().isEmpty ? null : send));
      }),
    );
    open = false;
    return sent;
  }
""")

    # ------------------------------------------------------------------
    # _addTeammateSheet
    # ------------------------------------------------------------------
    func("  Future<void> _addTeammateSheet(",
         "\n\n  Future<void> _editTeammate(",
         r"""
  Future<void> _addTeammateSheet(
      String vendorId, Map<String, dynamic> vd) async {
    final String metro = (vd['metroId'] ?? '').toString();
    final String metroName = metro
        .split('-')
        .map((String p) => p.isEmpty ? p : p[0].toUpperCase() + p.substring(1))
        .join(' ');
    final TextEditingController qC = TextEditingController();
    List<QueryDocumentSnapshot<Map<String, dynamic>>> pool =
        <QueryDocumentSnapshot<Map<String, dynamic>>>[];
    bool loading = true;
    bool started = false;
    bool open = true;
    String err = '';
    String cat = '';
    const List<String> cats = <String>[
      'wedding-photographers',
      'wedding-videographers',
      'wedding-venues',
      'wedding-planners',
      'wedding-djs',
      'wedding-florists',
      'wedding-caterers',
      'wedding-cakes',
      'hair-and-makeup',
      'wedding-officiants',
      'wedding-bands',
      'day-of-coordination'
    ];
    if (!mounted) return;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 640),
      builder: (BuildContext ctx) =>
          StatefulBuilder(builder: (BuildContext sc, StateSetter setSheet) {
        void up(VoidCallback f) {
          if (open) setSheet(f);
        }

        Future<void> load() async {
          up(() {
            loading = true;
            err = '';
          });
          try {
            Query<Map<String, dynamic>> q = FirebaseFirestore.instance
                .collection('vendors')
                .where('metroId', isEqualTo: metro);
            if (cat.isNotEmpty) q = q.where('category', isEqualTo: cat);
            final QuerySnapshot<Map<String, dynamic>> r =
                await q.limit(300).get();
            pool = r.docs
                .where((QueryDocumentSnapshot<Map<String, dynamic>> d) =>
                    d.id != vendorId && d.data()['delisted'] != true)
                .toList();
          } catch (_) {
            err = 'Couldn\u2019t load pros. Check your connection and try again.';
          }
          up(() => loading = false);
        }

        // load once when the sheet opens (the old check re-ran it on every
        // rebuild while the first load was still in flight)
        if (!started) {
          started = true;
          WidgetsBinding.instance.addPostFrameCallback((_) => load());
        }
        final String qq = qC.text.trim().toLowerCase();
        final List<QueryDocumentSnapshot<Map<String, dynamic>>> shown = pool
            .where((QueryDocumentSnapshot<Map<String, dynamic>> d) =>
                qq.isEmpty ||
                (d.data()['name'] ?? '').toString().toLowerCase().contains(qq))
            .take(40)
            .toList()
          ..sort((QueryDocumentSnapshot<Map<String, dynamic>> a,
              QueryDocumentSnapshot<Map<String, dynamic>> b) {
            final bool ca = (a.data()['claimedBy'] ?? '').toString().isNotEmpty,
                cb = (b.data()['claimedBy'] ?? '').toString().isNotEmpty;
            if (ca != cb) return ca ? -1 : 1;
            return (a.data()['name'] ?? '')
                .toString()
                .compareTo((b.data()['name'] ?? '').toString());
          });
        String label(String c) {
          final String t = c.replaceFirst('wedding-', '').replaceAll('-', ' ');
          return t.isEmpty ? t : t[0].toUpperCase() + t.substring(1);
        }

        return SizedBox(
          height: MediaQuery.of(ctx).size.height * .86,
          child: _lzFrame(ctx,
              fill: true,
              icon: Icons.group_add_rounded,
              title: 'Add to your team',
              subtitle:
                  'Pros${metroName.isEmpty ? '' : ' in $metroName'} you\u2019d put your name on.',
              headerExtra: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: <Widget>[
                    TextField(
                      controller: qC,
                      onChanged: (_) => up(() {}),
                      textInputAction: TextInputAction.search,
                      style: TextStyle(color: _lzFg(ink), fontSize: 14),
                      decoration: _epDeco('Search', 'A pro\u2019s business name')
                          .copyWith(
                              prefixIcon: Icon(Icons.search_rounded,
                                  size: 19, color: _lzFg(muted))),
                    ),
                    const SizedBox(height: 10),
                    SizedBox(
                      height: 36,
                      child: ListView(
                        scrollDirection: Axis.horizontal,
                        children: <Widget>[
                          Padding(
                              padding: const EdgeInsets.only(right: 8),
                              child: _v4Chip('All', cat.isEmpty, () {
                                cat = '';
                                load();
                              })),
                          for (final String c in cats)
                            Padding(
                                padding: const EdgeInsets.only(right: 8),
                                child: _v4Chip(label(c), cat == c, () {
                                  cat = c;
                                  load();
                                })),
                        ],
                      ),
                    ),
                  ]),
              children: loading
                  ? <Widget>[
                      const SizedBox(height: 14),
                      _lzBusy('Finding pros${metroName.isEmpty ? '' : ' in $metroName'}\u2026'),
                    ]
                  : shown.isEmpty
                      ? <Widget>[
                          _v4Err(err),
                          if (err.isEmpty)
                            _v4Empty(
                                Icons.search_off_rounded,
                                qq.isEmpty
                                    ? 'No pros in this category here yet.'
                                    : 'No one by that name. Try another spelling or category.'),
                        ]
                      : <Widget>[
                          const SizedBox(height: 12),
                          for (final QueryDocumentSnapshot<Map<String, dynamic>> d
                              in shown)
                            Builder(builder: (BuildContext bc) {
                              final Map<String, dynamic> m = d.data();
                              final String name = (m['name'] ?? '').toString();
                              final bool claimed =
                                  (m['claimedBy'] ?? '').toString().isNotEmpty;
                              return _v4Card(
                                onTap: () async {
                                  Navigator.pop(ctx);
                                  await _editTeammate(vendorId, vd, -1,
                                      candidate: <String, dynamic>{
                                        'vendorId': d.id,
                                        'name': name,
                                        'category':
                                            (m['category'] ?? '').toString(),
                                        'note': '',
                                        'weddingsTogether': 0,
                                      });
                                },
                                child: Row(children: <Widget>[
                                  Container(
                                    width: 38,
                                    height: 38,
                                    alignment: Alignment.center,
                                    decoration: BoxDecoration(
                                        color: plumDeep,
                                        borderRadius:
                                            BorderRadius.circular(11)),
                                    child: Text(
                                        name.isEmpty
                                            ? '?'
                                            : name[0].toUpperCase(),
                                        style: const TextStyle(
                                            color: gold,
                                            fontSize: 15,
                                            fontWeight: FontWeight.w800)),
                                  ),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: <Widget>[
                                          Text(name,
                                              maxLines: 1,
                                              overflow: TextOverflow.ellipsis,
                                              style: TextStyle(
                                                  color: _lzFg(ink),
                                                  fontSize: 14.5,
                                                  fontWeight: FontWeight.w700)),
                                          const SizedBox(height: 2),
                                          Text(
                                              '${label((m['category'] ?? '').toString())}${claimed ? ' \u00b7 on Lazo' : ' \u00b7 not claimed yet'}',
                                              style: TextStyle(
                                                  fontSize: 12.5,
                                                  color: _lzFg(claimed
                                                      ? vGreen
                                                      : muted))),
                                        ]),
                                  ),
                                  Icon(Icons.add_circle_outline_rounded,
                                      color: _lzFg(plum), size: 22),
                                ]),
                              );
                            }),
                        ]),
        );
      }),
    );
    open = false;
  }
""")

    # ------------------------------------------------------------------
    # _editTeammate
    # ------------------------------------------------------------------
    func("  Future<void> _editTeammate(",
         "\n\n  Future<void> _recommendTeamSheet(",
         r"""
  Future<void> _editTeammate(
      String vendorId, Map<String, dynamic> vd, int index,
      {Map<String, dynamic>? candidate}) async {
    final List<Map<String, dynamic>> team =
        ((vd['team'] as List?) ?? const <dynamic>[])
            .whereType<Map>()
            .map((Map m) => Map<String, dynamic>.from(m))
            .toList();
    final Map<String, dynamic> t =
        index >= 0 ? team[index] : (candidate ?? <String, dynamic>{});
    if (index < 0 &&
        team.any((Map<String, dynamic> x) => x['vendorId'] == t['vendorId'])) {
      _toast('${t['name']} is already on your team.');
      return;
    }
    final TextEditingController noteC =
        TextEditingController(text: (t['note'] ?? '').toString());
    final TextEditingController nC = TextEditingController(
        text:
            (t['weddingsTogether'] is num && (t['weddingsTogether'] as num) > 0)
                ? (t['weddingsTogether'] as num).toInt().toString()
                : '');
    final String catLabel = (t['category'] ?? '')
        .toString()
        .replaceFirst('wedding-', '')
        .replaceAll('-', ' ');
    bool busy = false;
    bool open = true;
    String err = '';
    if (!mounted) return;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 480),
      builder: (BuildContext ctx) =>
          StatefulBuilder(builder: (BuildContext sc, StateSetter set) {
        void up(VoidCallback f) {
          if (open) set(f);
        }

        Future<void> save() async {
          up(() {
            busy = true;
            err = '';
          });
          final Map<String, dynamic> saved = <String, dynamic>{
            'vendorId': t['vendorId'],
            'name': t['name'],
            'category': t['category'],
            'note': noteC.text.trim(),
            'weddingsTogether': int.tryParse(nC.text.trim()) ?? 0,
          };
          final List<Map<String, dynamic>> next =
              List<Map<String, dynamic>>.from(team);
          if (index >= 0)
            next[index] = saved;
          else
            next.add(saved);
          try {
            await FirebaseFirestore.instance
                .collection('vendors')
                .doc(vendorId)
                .set(<String, dynamic>{'team': next.take(12).toList()},
                    SetOptions(merge: true));
            if (ctx.mounted) Navigator.pop(ctx);
            _toast(index >= 0 ? 'Saved.' : '${t['name']} added to your team.');
          } catch (e) {
            up(() {
              busy = false;
              err = 'Couldn\u2019t save: ' + _errText(e);
            });
          }
        }

        return _lzFrame(ctx,
            icon: index >= 0
                ? Icons.edit_rounded
                : Icons.person_add_alt_1_rounded,
            title: (t['name'] ?? '').toString(),
            subtitle: catLabel.isEmpty
                ? null
                : catLabel[0].toUpperCase() + catLabel.substring(1),
            children: <Widget>[
              const SizedBox(height: 14),
              TextField(
                  controller: nC,
                  autofocus: index < 0,
                  enabled: !busy,
                  keyboardType: TextInputType.number,
                  inputFormatters: <TextInputFormatter>[
                    FilteringTextInputFormatter.digitsOnly
                  ],
                  textInputAction: TextInputAction.next,
                  style: TextStyle(color: _lzFg(ink), fontSize: 14.5),
                  decoration: _epDeco(
                      'Weddings together', 'How many you\u2019ve done')),
              const SizedBox(height: 12),
              TextField(
                  controller: noteC,
                  enabled: !busy,
                  maxLength: 160,
                  minLines: 2,
                  maxLines: 3,
                  textCapitalization: TextCapitalization.sentences,
                  style: TextStyle(color: _lzFg(ink), fontSize: 14.5),
                  decoration:
                      _epDeco('Why you trust them', 'Couples see this')),
              _v4Err(err),
            ],
            footer: _lzActions(
                secondary: 'Cancel',
                onSecondary: () => Navigator.pop(ctx),
                primary: index >= 0 ? 'Save' : 'Add to my team',
                icon: index >= 0
                    ? Icons.check_rounded
                    : Icons.group_add_rounded,
                busy: busy,
                onPrimary: save));
      }),
    );
    open = false;
  }
""")

    # ------------------------------------------------------------------
    # _recommendTeamSheet
    # ------------------------------------------------------------------
    func("  Future<void> _recommendTeamSheet(",
         "\n\n  Widget _invoicesStrip(",
         r"""
  Future<void> _recommendTeamSheet(
      String inquiryId, Map<String, dynamic> inq) async {
    final String vendorId = (inq['vendorId'] ?? '').toString();
    final Map<String, dynamic> vd =
        _liveD['vendor:$vendorId']?.latest?.data() ?? <String, dynamic>{};
    final List<Map<String, dynamic>> team =
        ((vd['team'] as List?) ?? const <dynamic>[])
            .whereType<Map>()
            .map((Map m) => Map<String, dynamic>.from(m))
            .toList();
    if (team.isEmpty) {
      _toast('Add your team first - Profile \u203a Your team.');
      await _addTeammateSheet(vendorId, vd);
      return;
    }
    final Set<String> picked = <String>{
      for (final Map<String, dynamic> t in team)
        (t['vendorId'] ?? '').toString()
    };
    final TextEditingController noteC = TextEditingController();
    bool busy = false;
    bool open = true;
    String err = '';
    if (!mounted) return;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 600),
      builder: (BuildContext ctx) => StatefulBuilder(
          builder: (BuildContext sc, StateSetter setSheet) {
        void up(VoidCallback f) {
          if (open) setSheet(f);
        }

        Future<void> send() async {
          up(() {
            busy = true;
            err = '';
          });
          try {
            await FirebaseFunctions.instance
                .httpsCallable('teamRecommend')
                .call(<String, dynamic>{
              'vendorId': vendorId,
              'inquiryId': inquiryId,
              'memberIds': picked.toList(),
              'note': noteC.text.trim(),
            });
            if (ctx.mounted) Navigator.pop(ctx);
            _toast('Sent - your team is in their thread.');
          } on FirebaseFunctionsException catch (e) {
            up(() {
              busy = false;
              err = e.message ?? 'Couldn\u2019t send. Try again.';
            });
          } catch (e) {
            up(() {
              busy = false;
              err = _errText(e);
            });
          }
        }

        return _lzFrame(ctx,
            icon: Icons.diversity_3_rounded,
            title: 'Recommend your team',
            subtitle:
                'To ${(inq['coupleName'] ?? 'this couple').toString()}. Each pro shows as a card with a one-tap date check.',
            children: <Widget>[
              _lzSection('Who to send',
                  trailing: '${picked.length} of ${team.length}'),
              for (final Map<String, dynamic> t in team)
                Builder(builder: (BuildContext bc) {
                  final String id = (t['vendorId'] ?? '').toString();
                  final bool on = picked.contains(id);
                  final String c = (t['category'] ?? '')
                      .toString()
                      .replaceFirst('wedding-', '')
                      .replaceAll('-', ' ');
                  return _v4Card(
                    on: on,
                    onTap: busy
                        ? null
                        : () => up(() {
                              if (!picked.remove(id)) picked.add(id);
                            }),
                    child: Row(children: <Widget>[
                      Icon(
                          on
                              ? Icons.check_circle_rounded
                              : Icons.radio_button_unchecked_rounded,
                          color: _lzFg(on ? vGreen : muted),
                          size: 22),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Text((t['name'] ?? '').toString(),
                                  style: TextStyle(
                                      color: _lzFg(ink),
                                      fontSize: 14.5,
                                      fontWeight: FontWeight.w700)),
                              if (c.isNotEmpty)
                                Text(c[0].toUpperCase() + c.substring(1),
                                    style: TextStyle(
                                        fontSize: 12.5, color: _lzFg(muted))),
                            ]),
                      ),
                    ]),
                  );
                }),
              const SizedBox(height: 8),
              TextField(
                controller: noteC,
                enabled: !busy,
                minLines: 2,
                maxLines: 4,
                maxLength: 400,
                textCapitalization: TextCapitalization.sentences,
                style: TextStyle(color: _lzFg(ink), fontSize: 14),
                decoration: _epDeco('A line from you (optional)',
                    '\u201cThese are the folks I\u2019d hire for my own wedding.\u201d'),
              ),
              _lzNote(Icons.notifications_none_rounded,
                  'Each pro sees you sent them.'),
              _v4Err(err),
            ],
            footer: _lzActions(
                secondary: 'Cancel',
                onSecondary: () => Navigator.pop(ctx),
                primary: picked.isEmpty
                    ? 'Pick at least one'
                    : 'Recommend ${picked.length} pro${picked.length == 1 ? '' : 's'}',
                icon: Icons.send_rounded,
                busy: busy,
                onPrimary: picked.isEmpty ? null : send));
      }),
    );
    open = false;
  }
""")

    # ------------------------------------------------------------------
    # _editMessageDialog
    # ------------------------------------------------------------------
    func("  Future<void> _editMessageDialog(",
         "\n\n  // v127: emoji.",
         r"""
  Future<void> _editMessageDialog(
      String inquiryId, String messageId, String current) async {
    final TextEditingController ec = TextEditingController(text: current);
    bool busy = false;
    bool open = true;
    String err = '';
    if (!mounted) return;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 520),
      builder: (BuildContext ctx) =>
          StatefulBuilder(builder: (BuildContext sc, StateSetter set) {
        void up(VoidCallback f) {
          if (open) set(f);
        }

        final String v = ec.text.trim();
        final bool can = v.isNotEmpty && v != current;
        Future<void> save() async {
          final String next = ec.text.trim();
          if (next.isEmpty || next == current) return;
          up(() {
            busy = true;
            err = '';
          });
          try {
            await FirebaseFirestore.instance
                .collection('inquiries')
                .doc(inquiryId)
                .collection('messages')
                .doc(messageId)
                .update(<String, dynamic>{
              'text': next,
              'editedAt': FieldValue.serverTimestamp(),
            });
            if (ctx.mounted) Navigator.pop(ctx);
          } catch (_) {
            up(() {
              busy = false;
              err = 'Couldn\u2019t save the edit. Try again.';
            });
          }
        }

        return _lzFrame(ctx,
            icon: Icons.edit_rounded,
            title: 'Edit message',
            children: <Widget>[
              const SizedBox(height: 14),
              TextField(
                controller: ec,
                autofocus: true,
                enabled: !busy,
                minLines: 2,
                maxLines: 6,
                textCapitalization: TextCapitalization.sentences,
                onChanged: (_) => up(() {}),
                style: TextStyle(color: _lzFg(ink), fontSize: 14.5, height: 1.4),
                decoration: _epDeco('Message', ''),
              ),
              _v4Err(err),
            ],
            footer: _lzActions(
                secondary: 'Cancel',
                onSecondary: () => Navigator.pop(ctx),
                primary: 'Save',
                icon: Icons.check_rounded,
                busy: busy,
                onPrimary: can ? save : null));
      }),
    );
    open = false;
  }
""")

    # ------------------------------------------------------------------
    # _emojiSheet (special: copy only)
    # ------------------------------------------------------------------
    rep(r"""                    child: Text('Tap to add \u2014 keep going, then close.',""",
        r"""                    child: Text('Tap to add as many as you like, then close.',""")

    # ------------------------------------------------------------------
    # _needsBooked
    # ------------------------------------------------------------------
    func("  Future<void> _needsBooked(",
         "\n\n  Future<void> _markDelivered(",
         r"""
  Future<void> _needsBooked(
      String inquiryId, Map<String, dynamic> inq, String what) async {
    if (!mounted) return;
    final bool go = await _lzConfirm(
        '$what opens once they\u2019re booked',
        'Mark ${(inq['coupleName'] ?? 'this couple').toString()} as booked and these tools unlock for their thread. It\u2019s also what tells Lazo when to ask them for a review.',
        confirm: 'Mark booked',
        cancel: 'Not yet',
        icon: Icons.celebration_rounded);
    if (go) {
      await _setStatus(inquiryId, 'booked');
      _toast('Booked. Delivery tools are open for this thread.');
    }
  }
""")

    # ------------------------------------------------------------------
    # _teaserSheet
    # ------------------------------------------------------------------
    func("  Future<void> _teaserSheet(",
         "\n\n  Future<void> _sneakPeekSheet(",
         r"""
  Future<void> _teaserSheet(String inquiryId, Map<String, dynamic> inq) async {
    final String vendorId = (inq['vendorId'] ?? '').toString();
    final TextEditingController urlC = TextEditingController();
    final TextEditingController vibeC = TextEditingController();
    final TextEditingController capC = TextEditingController();
    final TextEditingController msgC = TextEditingController();
    bool thinking = false;
    bool sending = false;
    bool drafted = false;
    bool open = true;
    String err = '';

    if (!mounted) return;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 680),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setS) {
          void up(VoidCallback f) {
            if (open) setS(f);
          }

          final bool linkOk = _looksLikeVideoLink(urlC.text.trim());

          Future<void> write() async {
            if (!_looksLikeVideoLink(urlC.text.trim())) {
              up(() => err = 'Paste a Vimeo or YouTube link.');
              return;
            }
            up(() {
              thinking = true;
              err = '';
            });
            try {
              final HttpsCallable fn = FirebaseFunctions.instance.httpsCallable(
                  'juneTeaser',
                  options: HttpsCallableOptions(
                      timeout: const Duration(seconds: 120)));
              final HttpsCallableResult<dynamic> out =
                  await fn.call(<String, dynamic>{
                'vendorId': vendorId,
                'inquiryId': inquiryId,
                'url': urlC.text.trim(),
                'vibe': vibeC.text.trim(),
              });
              final Map<String, dynamic> r =
                  Map<String, dynamic>.from(out.data as Map);
              up(() {
                capC.text = (r['caption'] ?? '').toString();
                msgC.text = (r['message'] ?? '').toString();
                drafted = true;
                thinking = false;
              });
            } on FirebaseFunctionsException catch (e) {
              up(() {
                thinking = false;
                err = (e.message ?? '').contains('studio-required')
                    ? 'Teasers are a Pro Studio feature.'
                    : (e.message ?? 'June couldn\u2019t write that one.');
              });
            } catch (e) {
              up(() {
                thinking = false;
                err = 'Couldn\u2019t reach June. Try again in a moment.';
              });
            }
          }

          Future<void> send() async {
            final String u = urlC.text.trim();
            if (!_looksLikeVideoLink(u)) {
              up(() => err = 'Paste a Vimeo or YouTube link.');
              return;
            }
            up(() {
              sending = true;
              err = '';
            });
            try {
              await FirebaseFirestore.instance
                  .collection('inquiries')
                  .doc(inquiryId)
                  .collection('messages')
                  .add(<String, dynamic>{
                'senderRole': 'vendor',
                'text': msgC.text.trim().isEmpty
                    ? 'A first look at your film \u2728'
                    : msgC.text.trim(),
                'at': FieldValue.serverTimestamp(),
                'teaser': <String, dynamic>{
                  'url': u,
                  'host':
                      u.toLowerCase().contains('vimeo') ? 'Vimeo' : 'YouTube',
                },
              });
              await FirebaseFirestore.instance
                  .collection('inquiries')
                  .doc(inquiryId)
                  .set(<String, dynamic>{
                'status': 'responded',
                'respondedAt': FieldValue.serverTimestamp(),
                'teaserSentAt': FieldValue.serverTimestamp(),
              }, SetOptions(merge: true));
              if (ctx.mounted) Navigator.pop(ctx);
              _toast('Teaser sent.');
            } catch (e) {
              up(() {
                sending = false;
                err = 'Couldn\u2019t send: ' + _errText(e);
              });
            }
          }

          return _lzFrame(ctx,
              icon: Icons.movie_creation_rounded,
              title: 'Send a teaser film',
              subtitle:
                  'It plays where you already host it - nothing to re-upload.',
              children: <Widget>[
                const SizedBox(height: 14),
                TextField(
                  controller: urlC,
                  autofocus: true,
                  enabled: !sending,
                  keyboardType: TextInputType.url,
                  onChanged: (_) => up(() {}),
                  style: TextStyle(color: _lzFg(ink), fontSize: 14.5),
                  decoration: _epDeco('Vimeo or YouTube link',
                          'https://vimeo.com/1234567890')
                      .copyWith(
                    suffixIcon: linkOk
                        ? Icon(Icons.check_circle_rounded,
                            color: _lzFg(vGreen), size: 19)
                        : null,
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: vibeC,
                  enabled: !thinking && !sending,
                  minLines: 2,
                  maxLines: 4,
                  textCapitalization: TextCapitalization.sentences,
                  style: TextStyle(color: _lzFg(ink), fontSize: 14),
                  decoration: _epDeco('What does the film feel like?',
                      'Golden hour, a lot of laughing, her dad crying during the toast'),
                ),
                const SizedBox(height: 6),
                Text(
                    'A line or two is plenty. June already knows the couple, the venue and the date.',
                    style: TextStyle(
                        fontSize: 12, color: _lzFg(muted), height: 1.4)),
                const SizedBox(height: 14),
                if (thinking)
                  _lzBusy('June is writing the note and the caption\u2026')
                else
                  OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(
                        foregroundColor: _lzFg(plum),
                        side: BorderSide(color: gold.withOpacity(.8)),
                        minimumSize: const Size(0, 46),
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(13))),
                    onPressed: _h(sending ? null : write),
                    icon: const Icon(Icons.auto_awesome_rounded, size: 17),
                    label: Text(
                        drafted ? 'Rewrite it' : 'June, write the words',
                        style: const TextStyle(
                            fontSize: 14, fontWeight: FontWeight.w700)),
                  ),
                if (drafted) ...<Widget>[
                  _lzSection('June\u2019s words', trailing: 'Edit anything'),
                  TextField(
                    controller: msgC,
                    enabled: !sending,
                    minLines: 2,
                    maxLines: 5,
                    textCapitalization: TextCapitalization.sentences,
                    style: TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _epDeco('Note to the couple', ''),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: capC,
                    minLines: 3,
                    maxLines: 8,
                    style: TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _epDeco('Instagram caption', ''),
                  ),
                  Align(
                    alignment: Alignment.centerRight,
                    child: TextButton.icon(
                      onPressed: _h(() async {
                        await Clipboard.setData(ClipboardData(text: capC.text));
                        _toast('Caption copied.');
                      }),
                      icon: Icon(Icons.copy_rounded,
                          size: 16, color: _lzFg(plum)),
                      label: Text('Copy caption',
                          style: TextStyle(
                              color: _lzFg(plum),
                              fontSize: 13,
                              fontWeight: FontWeight.w700)),
                    ),
                  ),
                ],
                _v4Err(err),
              ],
              footer: _lzActions(
                  secondary: 'Cancel',
                  onSecondary: () => Navigator.pop(ctx),
                  primary: 'Send to the couple',
                  icon: Icons.send_rounded,
                  busy: sending,
                  onPrimary: thinking ? null : send));
        },
      ),
    );
    open = false;
  }
""")

    # ------------------------------------------------------------------
    # _sneakPeekSheet
    # ------------------------------------------------------------------
    func("  Future<void> _sneakPeekSheet(",
         "\n\n  Future<Map<String, dynamic>?> _runSneakPeek(",
         r"""
  Future<void> _sneakPeekSheet(
      String inquiryId, Map<String, dynamic> inq) async {
    final String vendorId = (inq['vendorId'] ?? '').toString();
    List<Map<String, dynamic>> picks = <Map<String, dynamic>>[];
    final TextEditingController capC = TextEditingController();
    final TextEditingController msgC = TextEditingController();
    final Set<String> dropped = <String>{};
    int considered = 0;
    bool sending = false;
    bool busy = false;
    bool open = true;
    String note = '';
    double pct = 0;
    final bool owes = (inq['invoiceStatus'] ?? '') == 'due' ||
        (inq['invoiceStatus'] ?? '') == 'sent';

    if (!mounted) return;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 720),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setS) {
          void up(VoidCallback f) {
            if (open) setS(f);
          }

          final int keep = picks.length - dropped.length;

          Future<void> choose() async {
            final Map<String, dynamic>? r = await _runSneakPeek(
                vendorId, inquiryId, (String s, double p, bool b) {
              up(() {
                note = s;
                pct = p;
                busy = b;
              });
            });
            if (r == null) return;
            up(() {
              picks = (r['picks'] as List)
                  .map((dynamic e) => Map<String, dynamic>.from(e as Map))
                  .toList();
              considered = (r['considered'] ?? 0) as int;
              capC.text = (r['caption'] ?? '').toString();
              msgC.text = (r['message'] ?? '').toString();
            });
          }

          Future<void> send() async {
            up(() => sending = true);
            final bool ok = await _sendSneakPeek(
                inquiryId,
                picks
                    .where((Map<String, dynamic> p) =>
                        !dropped.contains((p['path'] ?? '').toString()))
                    .toList(),
                msgC.text.trim());
            if (ok && ctx.mounted) {
              Navigator.pop(ctx);
            } else {
              up(() => sending = false);
            }
          }

          final List<Widget> body;
          if (picks.isEmpty && busy) {
            body = <Widget>[
              const SizedBox(height: 26),
              Center(
                child: SizedBox(
                  width: 66,
                  height: 66,
                  child: Stack(alignment: Alignment.center, children: <Widget>[
                    SizedBox(
                      width: 66,
                      height: 66,
                      child: CircularProgressIndicator(
                        value: pct <= 0 ? null : pct,
                        strokeWidth: 3,
                        backgroundColor: plum.withOpacity(.10),
                        valueColor: const AlwaysStoppedAnimation<Color>(gold),
                      ),
                    ),
                    Icon(Icons.auto_awesome_rounded,
                        color: _lzFg(plum), size: 24),
                  ]),
                ),
              ),
              const SizedBox(height: 16),
              Text(note,
                  textAlign: TextAlign.center,
                  style: TextStyle(
                      fontSize: 14.5,
                      color: _lzFg(plum),
                      fontWeight: FontWeight.w700)),
              const SizedBox(height: 5),
              Text(
                  pct < .6
                      ? 'Resizing them so they upload fast.'
                      : 'This part takes a minute - she reads every frame.',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 12.5, color: _lzFg(muted))),
              const SizedBox(height: 20),
            ];
          } else if (picks.isEmpty) {
            body = <Widget>[
              const SizedBox(height: 14),
              if (owes) ...<Widget>[
                _lzNote(Icons.info_outline_rounded,
                    'Their invoice is still outstanding - sending is entirely your call.'),
                const SizedBox(height: 12),
              ],
              _Press(
                scale: .985,
                onTap: choose,
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 18, vertical: 24),
                  decoration: BoxDecoration(
                      color: _lzBg(card),
                      borderRadius: BorderRadius.circular(18),
                      border: Border.all(
                          color: gold.withOpacity(.75), width: 1.4)),
                  child: Column(children: <Widget>[
                    Icon(Icons.add_photo_alternate_outlined,
                        color: _lzFg(plum), size: 32),
                    const SizedBox(height: 10),
                    Text('Choose your photos',
                        style: TextStyle(
                            fontSize: 15.5,
                            fontWeight: FontWeight.w700,
                            color: _lzFg(plum))),
                    const SizedBox(height: 4),
                    Text(
                        '4 to 60 web-res frames. Straight from your export folder is fine.',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                            fontSize: 12.5, color: _lzFg(muted), height: 1.35)),
                  ]),
                ),
              ),
            ];
          } else {
            body = <Widget>[
              const SizedBox(height: 12),
              if (owes) ...<Widget>[
                _lzNote(Icons.info_outline_rounded,
                    'Their invoice is still outstanding - sending is entirely your call.'),
                const SizedBox(height: 10),
              ],
              _lzSection('June\u2019s picks',
                  trailing: '$keep of $considered frames'),
              SizedBox(
                height: 190,
                child: GridView.builder(
                  scrollDirection: Axis.horizontal,
                  gridDelegate:
                      const SliverGridDelegateWithFixedCrossAxisCount(
                          crossAxisCount: 2,
                          mainAxisSpacing: 8,
                          crossAxisSpacing: 8,
                          childAspectRatio: 1),
                  itemCount: picks.length,
                  itemBuilder: (BuildContext c3, int i) {
                    final Map<String, dynamic> p = picks[i];
                    final String path = (p['path'] ?? '').toString();
                    final bool off = dropped.contains(path);
                    return InkWell(
                      onTap: sending
                          ? null
                          : () => up(() {
                                if (off) {
                                  dropped.remove(path);
                                } else {
                                  dropped.add(path);
                                }
                              }),
                      child: Stack(fit: StackFit.expand, children: <Widget>[
                        ClipRRect(
                          borderRadius: BorderRadius.circular(10),
                          child: Opacity(
                            opacity: off ? .25 : 1,
                            child: Image.network((p['url'] ?? '').toString(),
                                fit: BoxFit.cover,
                                errorBuilder: (BuildContext c4, Object e,
                                        StackTrace? s) =>
                                    Container(color: plum.withOpacity(.08))),
                          ),
                        ),
                        Positioned(
                          left: 4,
                          bottom: 4,
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                                color: plumDeep.withOpacity(.8),
                                borderRadius: BorderRadius.circular(999)),
                            child: Text((p['moment'] ?? '').toString(),
                                style: const TextStyle(
                                    color: gold,
                                    fontSize: 8,
                                    fontWeight: FontWeight.w800)),
                          ),
                        ),
                        if (off)
                          Center(
                              child: Icon(Icons.block_rounded,
                                  color: _lzFg(const Color(0xFFB3413A)),
                                  size: 22)),
                      ]),
                    );
                  },
                ),
              ),
              const SizedBox(height: 6),
              Text('Tap a photo to leave it out.',
                  style: TextStyle(fontSize: 12, color: _lzFg(muted))),
              _lzSection('June\u2019s words', trailing: 'Edit anything'),
              TextField(
                controller: msgC,
                enabled: !sending,
                minLines: 2,
                maxLines: 5,
                textCapitalization: TextCapitalization.sentences,
                style: TextStyle(fontSize: 14, color: _lzFg(ink)),
                decoration: _epDeco('Note to the couple', ''),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: capC,
                minLines: 3,
                maxLines: 8,
                style: TextStyle(fontSize: 14, color: _lzFg(ink)),
                decoration: _epDeco('Instagram caption', ''),
              ),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton.icon(
                  onPressed: _h(() async {
                    await Clipboard.setData(ClipboardData(text: capC.text));
                    _toast('Caption copied.');
                  }),
                  icon: Icon(Icons.copy_rounded, size: 16, color: _lzFg(plum)),
                  label: Text('Copy caption',
                      style: TextStyle(
                          color: _lzFg(plum),
                          fontSize: 13,
                          fontWeight: FontWeight.w700)),
                ),
              ),
            ];
          }

          return _lzFrame(ctx,
              icon: Icons.auto_awesome_rounded,
              title: 'June Sneak Peek',
              subtitle: picks.isEmpty
                  ? 'June reads every frame, picks the moments that carry the day and writes the words. You edit before it goes.'
                  : 'Check June\u2019s picks and words, then send.',
              children: body,
              footer: picks.isEmpty
                  ? null
                  : _lzActions(
                      secondary: 'Cancel',
                      onSecondary: () => Navigator.pop(ctx),
                      primary: keep <= 0
                          ? 'Keep at least one'
                          : 'Send $keep to the couple',
                      icon: Icons.send_rounded,
                      busy: sending,
                      onPrimary: keep <= 0 ? null : send));
        },
      ),
    );
    open = false;
  }
""")

    # ------------------------------------------------------------------
    # _savedRepliesSheet
    # ------------------------------------------------------------------
    func("  Future<void> _savedRepliesSheet(",
         "\n\n  Future<void> _savedReplyEditor(",
         r"""
  Future<void> _savedRepliesSheet(
      String inquiryId, Map<String, dynamic> inq, String vendorId) async {
    if (!mounted) return;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 620),
      builder: (BuildContext ctx) =>
          StreamBuilder<DocumentSnapshot<Map<String, dynamic>>>(
        stream: _vendorDocStream(vendorId),
        initialData: _liveD['vendor:$vendorId']?.latest,
        builder: (BuildContext c2,
            AsyncSnapshot<DocumentSnapshot<Map<String, dynamic>>> vs) {
          final Map<String, dynamic> vd =
              vs.data?.data() ?? <String, dynamic>{};
          final List<Map<String, dynamic>> replies = <Map<String, dynamic>>[];
          if (vd['savedReplies'] is List) {
            for (final dynamic r in vd['savedReplies'] as List) {
              if (r is Map) {
                replies.add(Map<String, dynamic>.from(r));
              }
            }
          }
          return _lzFrame(ctx,
              icon: Icons.bookmarks_rounded,
              title: 'Saved replies',
              subtitle:
                  'Tap one to add it to your reply. {couple}, {date}, {venue} and {vendor} fill themselves in.',
              children: replies.isEmpty
                  ? <Widget>[
                      _v4Empty(Icons.bookmark_add_outlined,
                          'Write the message you send most and keep it here.',
                          action: 'New saved reply',
                          onAction: () => _savedReplyEditor(vendorId)),
                    ]
                  : <Widget>[
                      const SizedBox(height: 12),
                      for (final Map<String, dynamic> r in replies)
                        _v4Card(
                          padding: const EdgeInsets.fromLTRB(14, 12, 4, 12),
                          onTap: () {
                            final String merged = _mergeReply(
                                (r['text'] ?? '').toString(), inq, vd);
                            final String cur = _inboxMsgC.text.trim();
                            final String next =
                                cur.isEmpty ? merged : '$cur\n\n$merged';
                            _inboxMsgC.value = TextEditingValue(
                                text: next,
                                selection: TextSelection.collapsed(
                                    offset: next.length));
                            Navigator.pop(ctx);
                            if (mounted) setState(() {});
                          },
                          child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                Expanded(
                                  child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: <Widget>[
                                        Text((r['title'] ?? 'Reply').toString(),
                                            style: TextStyle(
                                                color: _lzFg(ink),
                                                fontSize: 14.5,
                                                fontWeight: FontWeight.w700)),
                                        const SizedBox(height: 3),
                                        Text((r['text'] ?? '').toString(),
                                            maxLines: 3,
                                            overflow: TextOverflow.ellipsis,
                                            style: TextStyle(
                                                fontSize: 13,
                                                color: _lzFg(muted),
                                                height: 1.4)),
                                      ]),
                                ),
                                IconButton(
                                  tooltip: 'Delete',
                                  icon: Icon(Icons.delete_outline_rounded,
                                      color: _lzFg(muted), size: 19),
                                  onPressed: _h(() async {
                                    final bool ok = await _lzConfirm(
                                        'Delete this saved reply?',
                                        '\u201c${(r['title'] ?? 'Reply').toString()}\u201d goes from every device you use Lazo on.',
                                        confirm: 'Delete reply',
                                        danger: true);
                                    if (!ok) return;
                                    try {
                                      await FirebaseFirestore.instance
                                          .collection('vendors')
                                          .doc(vendorId)
                                          .set(<String, dynamic>{
                                        'savedReplies': FieldValue.arrayRemove(
                                            <dynamic>[r]),
                                      }, SetOptions(merge: true));
                                    } catch (e) {
                                      _toast('Couldn\u2019t delete it: ' +
                                          _errText(e));
                                    }
                                  }),
                                ),
                              ]),
                        ),
                    ],
              footer: replies.isEmpty
                  ? null
                  : _lzActions(
                      secondary: 'Close',
                      onSecondary: () => Navigator.pop(ctx),
                      primary: 'New saved reply',
                      icon: Icons.add_rounded,
                      onPrimary: () => _savedReplyEditor(vendorId)));
        },
      ),
    );
  }
""")

    # ------------------------------------------------------------------
    # _savedReplyEditor
    # ------------------------------------------------------------------
    func("  Future<void> _savedReplyEditor(",
         "\n\n  // ---------------- v151: TEAM, CALENDAR",
         r"""
  Future<void> _savedReplyEditor(String vendorId) async {
    final TextEditingController titleC = TextEditingController();
    final TextEditingController textC = TextEditingController();
    bool busy = false;
    bool open = true;
    String err = '';
    if (!mounted) return;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 520),
      builder: (BuildContext ctx) =>
          StatefulBuilder(builder: (BuildContext sc, StateSetter set) {
        void up(VoidCallback f) {
          if (open) set(f);
        }

        final bool can =
            titleC.text.trim().isNotEmpty && textC.text.trim().isNotEmpty;
        Future<void> save() async {
          if (titleC.text.trim().isEmpty || textC.text.trim().isEmpty) {
            return;
          }
          up(() {
            busy = true;
            err = '';
          });
          try {
            await FirebaseFirestore.instance
                .collection('vendors')
                .doc(vendorId)
                .set(<String, dynamic>{
              'savedReplies': FieldValue.arrayUnion(<dynamic>[
                <String, dynamic>{
                  'title': titleC.text.trim(),
                  'text': textC.text.trim(),
                }
              ]),
            }, SetOptions(merge: true));
            if (ctx.mounted) Navigator.pop(ctx);
            _toast('Saved.');
          } catch (e) {
            up(() {
              busy = false;
              err = 'Couldn\u2019t save: ' + _errText(e);
            });
          }
        }

        return _lzFrame(ctx,
            icon: Icons.bookmark_add_rounded,
            title: 'New saved reply',
            subtitle: 'Write it once, drop it into any thread.',
            children: <Widget>[
              const SizedBox(height: 14),
              TextField(
                  controller: titleC,
                  autofocus: true,
                  enabled: !busy,
                  textCapitalization: TextCapitalization.sentences,
                  textInputAction: TextInputAction.next,
                  onChanged: (_) => up(() {}),
                  style: TextStyle(color: _lzFg(ink), fontSize: 14.5),
                  decoration: _epDeco('Name', 'Nudge, Pricing, Availability')),
              const SizedBox(height: 12),
              TextField(
                  controller: textC,
                  enabled: !busy,
                  minLines: 4,
                  maxLines: 8,
                  textCapitalization: TextCapitalization.sentences,
                  onChanged: (_) => up(() {}),
                  style:
                      TextStyle(color: _lzFg(ink), fontSize: 14, height: 1.4),
                  decoration: _epDeco('Message',
                      'Hi {couple}, {date} is open on our end. Here\u2019s how we work\u2026')),
              const SizedBox(height: 4),
              _lzNote(Icons.auto_fix_high_rounded,
                  '{couple}, {date}, {venue} and {vendor} fill themselves in when you use it.'),
              _v4Err(err),
            ],
            footer: _lzActions(
                secondary: 'Cancel',
                onSecondary: () => Navigator.pop(ctx),
                primary: 'Save',
                icon: Icons.check_rounded,
                busy: busy,
                onPrimary: can ? save : null));
      }),
    );
    open = false;
  }
""")

    # ------------------------------------------------------------------
    # _teamSheet
    # ------------------------------------------------------------------
    func("  Future<void> _teamSheet(String vendorId) async {",
         "\n\n  // Redeemed from the claim screen",
         r"""
  Future<void> _teamSheet(String vendorId) async {
    final TextEditingController emailC = TextEditingController();
    bool busy = false;
    bool open = true;
    String err = '';
    if (!mounted) return;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 620),
      builder: (BuildContext ctx) =>
          StatefulBuilder(builder: (BuildContext sc, StateSetter set) {
        void up(VoidCallback f) {
          if (open) set(f);
        }

        return StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
          stream: _liveQuery(
              'invites:$vendorId',
              () => FirebaseFirestore.instance
                  .collection('vendorInvites')
                  .where('vendorId', isEqualTo: vendorId)),
          initialData: _liveQ['invites:$vendorId']?.latest,
          builder: (BuildContext c2,
              AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> s) {
            // revoked invites are history, not people with access
            final List<QueryDocumentSnapshot<Map<String, dynamic>>> docs =
                (s.data?.docs ??
                        <QueryDocumentSnapshot<Map<String, dynamic>>>[])
                    .where((QueryDocumentSnapshot<Map<String, dynamic>> d) =>
                        (d.data()['status'] ?? '').toString() != 'revoked')
                    .toList();
            final String em = emailC.text.trim().toLowerCase();
            final bool valid =
                RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(em);

            Future<void> create() async {
              final String addr = emailC.text.trim().toLowerCase();
              if (!addr.contains('@') || busy) return;
              up(() {
                busy = true;
                err = '';
              });
              try {
                await FirebaseFirestore.instance
                    .collection('vendorInvites')
                    .add(<String, dynamic>{
                  'vendorId': vendorId,
                  'email': addr,
                  'role': 'manager',
                  'code': _randomCode(6),
                  'status': 'pending',
                  'createdBy': _uid,
                  'createdAt': FieldValue.serverTimestamp(),
                });
                emailC.clear();
                up(() => busy = false);
                _toast('Invite created - send them the code.');
              } catch (e) {
                up(() {
                  busy = false;
                  err = 'Couldn\u2019t create the invite: ' + _errText(e);
                });
              }
            }

            return _lzFrame(ctx,
                icon: Icons.manage_accounts_rounded,
                title: 'Team',
                subtitle:
                    'Managers see the same inbox, profile and Studio you do.',
                children: <Widget>[
                  _lzSection('People with access',
                      trailing: docs.isEmpty ? null : '${docs.length}'),
                  if (docs.isEmpty)
                    _v4Card(
                      child: Row(children: <Widget>[
                        Icon(Icons.person_outline_rounded,
                            color: _lzFg(muted), size: 20),
                        const SizedBox(width: 12),
                        Expanded(
                            child: Text(
                                'Just you for now. Invite a manager below.',
                                style: TextStyle(
                                    fontSize: 13.5, color: _lzFg(muted)))),
                      ]),
                    ),
                  for (final QueryDocumentSnapshot<Map<String, dynamic>> d
                      in docs)
                    Builder(builder: (BuildContext bc) {
                      final Map<String, dynamic> m = d.data();
                      final String st = (m['status'] ?? 'pending').toString();
                      final String email = (m['email'] ?? '').toString();
                      final String code = (m['code'] ?? '').toString();
                      final bool joined = st == 'accepted';
                      return _v4Card(
                        padding: const EdgeInsets.fromLTRB(12, 10, 4, 10),
                        child: Row(children: <Widget>[
                          Container(
                            width: 36,
                            height: 36,
                            alignment: Alignment.center,
                            decoration: BoxDecoration(
                                color: plumDeep,
                                borderRadius: BorderRadius.circular(11)),
                            child: Text(
                                email.isEmpty ? '?' : email[0].toUpperCase(),
                                style: const TextStyle(
                                    color: gold,
                                    fontSize: 14,
                                    fontWeight: FontWeight.w800)),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: <Widget>[
                                  Text(email,
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: TextStyle(
                                          color: _lzFg(ink),
                                          fontSize: 14,
                                          fontWeight: FontWeight.w600)),
                                  const SizedBox(height: 2),
                                  Text(
                                      joined
                                          ? 'Joined as ${(m['role'] ?? 'manager').toString()}'
                                          : 'Waiting for them \u00b7 code $code',
                                      style: TextStyle(
                                          fontSize: 12.5,
                                          color:
                                              _lzFg(joined ? vGreen : muted),
                                          fontWeight: joined
                                              ? FontWeight.w600
                                              : FontWeight.w400)),
                                ]),
                          ),
                          if (!joined)
                            IconButton(
                              tooltip: 'Copy code',
                              icon: Icon(Icons.copy_rounded,
                                  color: _lzFg(plum), size: 18),
                              onPressed: _h(() async {
                                await Clipboard.setData(
                                    ClipboardData(text: code));
                                _toast('Code copied.');
                              }),
                            ),
                          IconButton(
                            tooltip: joined ? 'Remove access' : 'Cancel invite',
                            icon: Icon(Icons.delete_outline_rounded,
                                color: _lzFg(muted), size: 19),
                            onPressed: _h(() async {
                              final bool ok = joined
                                  ? await _lzConfirm('Remove $email?',
                                      'They lose access to this business on their next sign-in.',
                                      confirm: 'Remove access', danger: true)
                                  : await _lzConfirm('Cancel this invite?',
                                      'The code $code stops working.',
                                      confirm: 'Cancel invite',
                                      cancel: 'Keep it',
                                      danger: true);
                              if (!ok) return;
                              try {
                                await d.reference.set(<String, dynamic>{
                                  'status': 'revoked',
                                  'revokedAt': FieldValue.serverTimestamp(),
                                }, SetOptions(merge: true));
                                _toast(joined
                                    ? 'Access removed on their next sign-in.'
                                    : 'Invite cancelled.');
                              } catch (e) {
                                _toast('Couldn\u2019t update: ' + _errText(e));
                              }
                            }),
                          ),
                        ]),
                      );
                    }),
                  _lzSection('Invite a manager'),
                  TextField(
                    controller: emailC,
                    enabled: !busy,
                    keyboardType: TextInputType.emailAddress,
                    textInputAction: TextInputAction.send,
                    autocorrect: false,
                    onChanged: (_) => up(() {}),
                    onSubmitted: (_) {
                      if (valid) create();
                    },
                    style: TextStyle(color: _lzFg(ink), fontSize: 14.5),
                    decoration:
                        _epDeco('Their email', 'assistant@yourstudio.com'),
                  ),
                  const SizedBox(height: 10),
                  _lzNote(Icons.info_outline_rounded,
                      'They sign up at app.meetlazo.com with this email, then enter the code on the claim screen.'),
                  _v4Err(err),
                ],
                footer: _lzActions(
                    secondary: 'Close',
                    onSecondary: () => Navigator.pop(ctx),
                    primary: 'Create invite',
                    icon: Icons.person_add_alt_1_rounded,
                    busy: busy,
                    onPrimary: valid ? create : null));
          },
        );
      }),
    );
    open = false;
  }
""")

    # ------------------------------------------------------------------
    # _redeemInviteDialog
    # ------------------------------------------------------------------
    func("  Future<void> _redeemInviteDialog() async {",
         "\n\n  Future<void> _calendarFeedSheet(",
         r"""
  Future<void> _redeemInviteDialog() async {
    final TextEditingController codeC = TextEditingController();
    bool busy = false;
    bool open = true;
    String err = '';
    if (!mounted) return;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 460),
      builder: (BuildContext ctx) =>
          StatefulBuilder(builder: (BuildContext ctx2, StateSetter setD) {
        void up(VoidCallback f) {
          if (open) setD(f);
        }

        String clean() => codeC.text.trim().toUpperCase().replaceAll(' ', '');
        Future<void> join() async {
          final String code = clean();
          if (code.length < 4 || busy) return;
          up(() {
            busy = true;
            err = '';
          });
          try {
            final HttpsCallable fn = FirebaseFunctions.instance.httpsCallable(
                'redeemVendorInvite',
                options:
                    HttpsCallableOptions(timeout: const Duration(seconds: 30)));
            await fn.call(<String, dynamic>{'code': code});
            if (ctx.mounted) Navigator.pop(ctx);
            _toast('You\u2019re in - the dashboard is loading.');
          } on FirebaseFunctionsException catch (e) {
            up(() {
              busy = false;
              err = e.message ?? 'That code didn\u2019t work.';
            });
          } catch (_) {
            up(() {
              busy = false;
              err = 'That code didn\u2019t work.';
            });
          }
        }

        return _lzFrame(ctx,
            icon: Icons.vpn_key_rounded,
            title: 'Enter your invite code',
            subtitle: 'The code from the business that invited you.',
            children: <Widget>[
              const SizedBox(height: 14),
              TextField(
                controller: codeC,
                autofocus: true,
                enabled: !busy,
                textAlign: TextAlign.center,
                textCapitalization: TextCapitalization.characters,
                textInputAction: TextInputAction.go,
                autocorrect: false,
                onChanged: (_) => up(() {}),
                onSubmitted: (_) => join(),
                style: TextStyle(
                    color: _lzFg(ink),
                    fontSize: 20,
                    letterSpacing: 4,
                    fontWeight: FontWeight.w700),
                decoration: _epDeco('Invite code', 'ABC123'),
              ),
              _v4Err(err),
            ],
            footer: _lzActions(
                secondary: 'Cancel',
                onSecondary: () => Navigator.pop(ctx),
                primary: 'Join',
                icon: Icons.login_rounded,
                busy: busy,
                onPrimary: clean().length < 4 ? null : join));
      }),
    );
    open = false;
  }
""")

    # ------------------------------------------------------------------
    # _calendarFeedSheet
    # ------------------------------------------------------------------
    func("  Future<void> _calendarFeedSheet(",
         "\n\n  Widget _acctBriefRow(",
         r"""
  Future<void> _calendarFeedSheet(String vendorId) async {
    Map<String, dynamic> vd =
        _liveD['vendor:$vendorId']?.latest?.data() ?? <String, dynamic>{};
    String token = (vd['calendarToken'] ?? '').toString();
    if (token.isEmpty) {
      token = _randomCode(28);
      try {
        await FirebaseFirestore.instance
            .collection('vendors')
            .doc(vendorId)
            .set(<String, dynamic>{'calendarToken': token},
                SetOptions(merge: true));
      } catch (e) {
        _toast('Could not create the feed: ' + _errText(e));
        return;
      }
    }
    final String url =
        'https://us-central1-lazo-513ec.cloudfunctions.net/vendorCalendar?v=$vendorId&t=$token';
    bool copied = false;
    bool open = true;
    if (!mounted) return;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 620),
      builder: (BuildContext ctx) =>
          StatefulBuilder(builder: (BuildContext sc, StateSetter set) {
        Widget app(IconData ic, String name, String how) => _v4Card(
              child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Icon(ic, color: _lzFg(plum), size: 20),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Text(name,
                                style: TextStyle(
                                    color: _lzFg(ink),
                                    fontSize: 14,
                                    fontWeight: FontWeight.w700)),
                            const SizedBox(height: 2),
                            Text(how,
                                style: TextStyle(
                                    fontSize: 12.5,
                                    color: _lzFg(muted),
                                    height: 1.4)),
                          ]),
                    ),
                  ]),
            );
        return _lzFrame(ctx,
            icon: Icons.event_rounded,
            title: 'Calendar feed',
            subtitle:
                'Booked weddings and blocked dates in the calendar you already use. It refreshes on its own.',
            children: <Widget>[
              const SizedBox(height: 14),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: _lzBg(card),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: _lzLine(goldLine)),
                ),
                child: SelectableText(url,
                    style: TextStyle(
                        fontSize: 12,
                        color: _lzFg(ink),
                        fontFamily: 'monospace')),
              ),
              _lzSection('Add it to'),
              app(Icons.calendar_month_rounded, 'Google Calendar',
                  'Other calendars \u203a + \u203a From URL, then paste the link.'),
              app(Icons.event_note_rounded, 'Apple Calendar',
                  'File \u203a New Calendar Subscription, then paste the link.'),
              app(Icons.mail_outline_rounded, 'Outlook',
                  'Add calendar \u203a Subscribe from web, then paste the link.'),
              const SizedBox(height: 4),
              _lzNote(Icons.lock_outline_rounded,
                  'Anyone with this link can see your booked dates. Treat it like a password.'),
            ],
            footer: _lzActions(
                secondary: 'Close',
                onSecondary: () => Navigator.pop(ctx),
                primary: copied ? 'Copied' : 'Copy feed link',
                icon: copied ? Icons.check_rounded : Icons.copy_rounded,
                onPrimary: () async {
                  await Clipboard.setData(ClipboardData(text: url));
                  if (open) set(() => copied = true);
                }));
      }),
    );
    open = false;
  }
""")

    # ------------------------------------------------------------------
    # _bookingStatusSheet
    # ------------------------------------------------------------------
    func("  Future<void> _bookingStatusSheet(",
         "\n\n  Future<void> _unbook(",
         r"""
  Future<void> _bookingStatusSheet(
      String inquiryId, Map<String, dynamic> inq) async {
    final bool booked = (inq['status'] ?? '').toString() == 'booked';
    final bool signed = (inq['contractStatus'] ?? '').toString() == 'signed';
    const List<List<String>> opts = <List<String>>[
      <String>[
        'couple_cancelled',
        'The couple cancelled',
        'They called off the wedding or changed vendors.'
      ],
      <String>[
        'date_changed',
        'The date changed',
        'Still working together - new date to confirm.'
      ],
      <String>[
        'vendor_cancelled',
        'I had to cancel',
        'You can no longer take this date.'
      ],
      <String>[
        'mistake',
        'Marked booked by mistake',
        'Just put it back the way it was.'
      ],
    ];
    String reason = '';
    if (!mounted) return;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 520),
      builder: (BuildContext ctx) =>
          StatefulBuilder(builder: (BuildContext sc, StateSetter set) {
        if (!booked) {
          return _lzFrame(ctx,
              icon: Icons.celebration_rounded,
              title: 'Mark as booked',
              subtitle:
                  'This marks the date as yours and starts the celebration.',
              children: <Widget>[
                const SizedBox(height: 14),
                _lzNote(Icons.event_available_rounded,
                    'If plans change later, you can release the date from here.'),
              ],
              footer: _lzActions(
                  secondary: 'Not yet',
                  onSecondary: () => Navigator.pop(ctx),
                  primary: 'Mark booked',
                  icon: Icons.celebration_rounded,
                  onPrimary: () {
                    Navigator.pop(ctx);
                    _setStatus(inquiryId, 'booked');
                  }));
        }
        return _lzFrame(ctx,
            icon: Icons.event_busy_rounded,
            title: 'This couple is booked',
            subtitle:
                'If plans changed, release the date. The thread, contract and invoices stay where they are.',
            children: <Widget>[
              _lzSection('What happened?'),
              for (final List<String> o in opts)
                _v4Card(
                  on: reason == o[0],
                  onTap: () => set(() => reason = o[0]),
                  child: Row(children: <Widget>[
                    Icon(
                        reason == o[0]
                            ? Icons.radio_button_checked_rounded
                            : Icons.radio_button_unchecked_rounded,
                        color: _lzFg(reason == o[0] ? plum : muted),
                        size: 21),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Text(o[1],
                                style: TextStyle(
                                    color: _lzFg(ink),
                                    fontSize: 14,
                                    fontWeight: FontWeight.w700)),
                            const SizedBox(height: 2),
                            Text(o[2],
                                style: TextStyle(
                                    fontSize: 12.5,
                                    color: _lzFg(muted),
                                    height: 1.35)),
                          ]),
                    ),
                  ]),
                ),
              if (signed) ...<Widget>[
                const SizedBox(height: 4),
                _lzNote(Icons.verified_outlined,
                    'Their signed contract stays on file either way. Releasing the date doesn\u2019t undo a signed agreement or refund anything.'),
              ],
            ],
            footer: _lzActions(
                secondary: 'Keep booked',
                onSecondary: () => Navigator.pop(ctx),
                primary:
                    reason == 'mistake' ? 'Put it back' : 'Release the date',
                icon: reason == 'mistake'
                    ? Icons.undo_rounded
                    : Icons.event_busy_rounded,
                danger: reason.isNotEmpty && reason != 'mistake',
                onPrimary: reason.isEmpty
                    ? null
                    : () async {
                        final List<String> o = opts.firstWhere(
                            (List<String> x) => x[0] == reason);
                        Navigator.pop(ctx);
                        await _unbook(inquiryId, o[0], o[1]);
                      }));
      }),
    );
  }
""")

    return s
