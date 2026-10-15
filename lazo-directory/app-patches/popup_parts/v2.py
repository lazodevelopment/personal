# Popup pass JC-LAZO-POPUP-1014, PART v2 (vendor dashboard).
# Plans, contract templates, questionnaires, the push ask and the contract flow.
# Each function is replaced as a whole slice: from its own signature up to the
# next declaration (which is not touched). Every Firestore path, callable name,
# argument and written value is carried over unchanged.


def apply(s: str) -> str:
    def rep(old, new):
        nonlocal s
        assert s.count(old) == 1, (s.count(old), old[:80])
        s = s.replace(old, new)

    def fn(start, end, inner=None):
        """The text of one assigned function: from `start` (or `inner`, found
        after `start`) up to the declaration `end` that follows it."""
        assert s.count(start) == 1, ('start', start)
        i = s.index(start)
        if inner is not None:
            i = s.index(inner, i)
        j = s.index(end, i)
        assert s.count(end) == 1, ('end', end)
        old = s[i:j]
        assert old.endswith('  }\n\n'), ('tail', old[-40:])
        return old

    # ------------------------------------------------------------------
    # _showUpgradeSheet (+ the part's shared helpers right after it)
    # ------------------------------------------------------------------
    rep(fn('  void _showUpgradeSheet(String vendorId, String currentTier) {',
           '  Widget _cadenceChip('), r"""  void _showUpgradeSheet(String vendorId, String currentTier) {
    bool pif = false;
    bool busy = false;
    _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 640),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setU) => _lzFrame(ctx2,
            icon: Icons.workspace_premium_rounded,
            title: currentTier == 'studio'
                ? 'Your plan'
                : currentTier == 'pro'
                    ? 'Upgrade your plan'
                    : 'Choose your plan',
            subtitle: 'Founding prices, locked in for life.',
            headerExtra: Row(children: <Widget>[
              _cadenceChip('Monthly', !pif, () => setU(() => pif = false)),
              const SizedBox(width: 8),
              _cadenceChip(
                  'Pay for the year', pif, () => setU(() => pif = true)),
            ]),
            children: <Widget>[
              const SizedBox(height: 14),
              _tierCard(
                ctx: ctx,
                setU: setU,
                busy: busy,
                onBusy: (bool b) => busy = b,
                vendorId: vendorId,
                tier: 'pro',
                currentTier: currentTier,
                title: 'Pro',
                price: pif ? '\$790/yr' : '\$79/mo',
                note: pif
                    ? 'Two months free · billed once'
                    : 'Founding price · cancel anytime',
                bullets: const <String>[
                  'Reach couples in every market you serve - no metro cap',
                  'Enhanced profile with priority placement of your work',
                  'Inquiry and profile analytics',
                ],
                pif: pif,
              ),
              const SizedBox(height: 10),
              _tierCard(
                ctx: ctx,
                setU: setU,
                busy: busy,
                onBusy: (bool b) => busy = b,
                vendorId: vendorId,
                tier: 'studio',
                currentTier: currentTier,
                title: 'Pro Studio',
                price: pif ? '\$1,290/yr' : '\$129/mo',
                note: pif
                    ? 'Two months free · billed once'
                    : 'Founding price · cancel anytime',
                bullets: const <String>[
                  'June for Studio - your AI business copilot: pricing, profile audits, replies she drafts for you',
                  'Everything in Pro',
                  'Full CRM: contracts, e-signatures, questionnaires, invoicing',
                  'Instant Booking badge on your profile',
                ],
                pif: pif,
                featured: true,
              ),
              const SizedBox(height: 14),
              _lzNote(Icons.verified_outlined,
                  'Your ranking is earned by verified reviews and responsiveness - never purchased. The free tier stays free forever.'),
            ]),
      ),
    );
  }

  // ---- v2 popup helpers (JC-LAZO-POPUP-1014) ----
  // The _lzFrame header for the few popups that keep their own layout
  // (editors with a list or text area that fills the sheet).
  Widget _pv2Head(BuildContext ctx, IconData icon, String title,
      {String? subtitle, List<Widget> actions = const <Widget>[]}) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(22, 14, 10, 12),
      child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                    color: plumDeep, borderRadius: BorderRadius.circular(13)),
                child: Icon(icon, color: gold, size: 21)),
            const SizedBox(width: 13),
            Expanded(
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    const SizedBox(height: 2),
                    Text(title, style: _serif(size: 25, height: 1.1)),
                    if (subtitle != null && subtitle.isNotEmpty) ...<Widget>[
                      const SizedBox(height: 4),
                      Text(subtitle,
                          style: TextStyle(
                              fontSize: 13.5,
                              color: _lzFg(muted),
                              height: 1.4)),
                    ],
                  ]),
            ),
            ...actions,
            IconButton(
                tooltip: 'Close',
                icon: Icon(Icons.close_rounded, color: _lzFg(muted)),
                onPressed: _h(() => Navigator.of(ctx).maybePop())),
          ]),
    );
  }

  Widget _pv2Divider() => Divider(
      height: 1, thickness: 1, color: _lzLine(goldLine).withOpacity(.7));

  Widget _pv2Foot(BuildContext ctx, Widget child) => Container(
        decoration: BoxDecoration(
            color: _lzBg(ivory),
            border: Border(
                top: BorderSide(color: _lzLine(goldLine).withOpacity(.7)))),
        padding: EdgeInsets.fromLTRB(
            18, 12, 18, 12 + MediaQuery.of(ctx).padding.bottom * .5),
        child: child,
      );

  Widget _pv2Err(String err) => err.isEmpty
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
                              fontSize: 13.5,
                              color: _lzFg(ink),
                              height: 1.4))),
                ]),
          ),
        );

  // A tappable row card: icon chip, title, one line, chevron.
  Widget _pv2Row(
      {required IconData icon,
      required String title,
      String? sub,
      VoidCallback? onTap,
      bool danger = false,
      Widget? trailing}) {
    const Color red = Color(0xFFB3413A);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: _Press(
        scale: .985,
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.fromLTRB(14, 12, 10, 12),
          decoration: BoxDecoration(
              color: _lzBg(card),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                  color: danger
                      ? _lzLine(red.withOpacity(.35))
                      : _lzLine(goldLine))),
          child: Row(children: <Widget>[
            Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                    color: danger ? red.withOpacity(.1) : plumDeep,
                    borderRadius: BorderRadius.circular(11)),
                child: Icon(icon, size: 18, color: danger ? _lzFg(red) : gold)),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(title,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                            fontSize: 14.5,
                            fontWeight: FontWeight.w700,
                            color: _lzFg(danger ? red : plum))),
                    if (sub != null && sub.isNotEmpty) ...<Widget>[
                      const SizedBox(height: 2),
                      Text(sub,
                          style: TextStyle(
                              fontSize: 12.5,
                              color: _lzFg(muted),
                              height: 1.35)),
                    ],
                  ]),
            ),
            const SizedBox(width: 6),
            trailing ?? Icon(Icons.chevron_right_rounded, color: _lzFg(muted)),
          ]),
        ),
      ),
    );
  }

  Widget _pv2Empty(IconData icon, String line) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 22, horizontal: 12),
        child: Column(children: <Widget>[
          Icon(icon, size: 30, color: _lzFg(muted)),
          const SizedBox(height: 10),
          Text(line,
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 13.5, color: _lzFg(muted), height: 1.4)),
        ]),
      );

  // Long contract or template text, in a quiet bordered box.
  Widget _pv2Doc(String text) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: _lzBg(Colors.white),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: _lzLine(goldLine)),
        ),
        child: SelectableText(text.isEmpty ? 'Nothing here yet.' : text,
            style: TextStyle(fontSize: 12.5, color: _lzFg(ink), height: 1.5)),
      );

  List<Widget> _pv2Notes(List<String> notes) => <Widget>[
        if (notes.isNotEmpty) ...<Widget>[
          _lzSection('June’s notes'),
          for (final String n in notes)
            Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: _lzNote(Icons.lightbulb_outline_rounded, n)),
        ],
      ];

""")

    # ------------------------------------------------------------------
    # _mobilePlanSheet
    # ------------------------------------------------------------------
    rep(fn('  Future<void> _mobilePlanSheet(', '  // v140: declined renewals'), r"""  Future<void> _mobilePlanSheet(
      String tier, String status, bool canceling) async {
    final String plan = tier == 'studio'
        ? 'Lazo Pro Studio'
        : tier == 'pro'
            ? 'Lazo Pro'
            : 'Free listing';
    final String line = tier.isEmpty
        ? 'Pro and Pro Studio unlock June, contracts, invoices, galleries and more.'
        : status == 'past_due'
            ? 'Your last renewal didn’t go through.'
            : canceling
                ? 'Cancels at the end of the current period.'
                : 'Active.';
    // v179: Apple permits a link out to the browser for purchases on the US
    // storefront only, so the button appears for US-region devices; everywhere
    // else the sheet is text only. The web build never reaches this sheet.
    final bool usDevice =
        (WidgetsBinding.instance.platformDispatcher.locale.countryCode ?? '')
                .toUpperCase() ==
            'US';
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 520),
      builder: (BuildContext ctx) => _lzFrame(ctx,
          icon: Icons.workspace_premium_rounded,
          title: plan,
          subtitle: line,
          children: <Widget>[
            const SizedBox(height: 14),
            _lzNote(Icons.language_rounded,
                'Plans, upgrades and card details are managed on meetlazo.com from any browser. Changes show here within a minute.'),
          ],
          footer: usDevice
              ? _lzActions(
                  secondary: 'Close',
                  onSecondary: () => Navigator.pop(ctx),
                  primary: 'Manage on meetlazo.com',
                  icon: Icons.open_in_new_rounded,
                  onPrimary: () {
                    Navigator.pop(ctx);
                    _openUrl('https://meetlazo.com/for-vendors/#pricing');
                  })
              : _lzActions(
                  primary: 'Done',
                  icon: Icons.check_rounded,
                  onPrimary: () => Navigator.pop(ctx))),
    );
  }

""")

    # ------------------------------------------------------------------
    # _manageProSheet
    # ------------------------------------------------------------------
    rep(fn('  Future<void> _manageProSheet(String vendorId) async {',
           '  Widget _templatesCard('), r"""  Future<void> _manageProSheet(String vendorId) async {
    final DocumentSnapshot<Map<String, dynamic>> sSnap = await FirebaseFirestore
        .instance
        .collection('proSubscriptions')
        .doc(vendorId)
        .get();
    if (!mounted) {
      return;
    }
    final Map<String, dynamic> s = sSnap.data() ?? <String, dynamic>{};
    final String tier = (s['tier'] ?? '') as String;
    final String status = (s['status'] ?? '') as String;
    final bool canceling = s['cancelAtPeriodEnd'] == true;
    if (!kIsWeb) {
      // v157: App Store / Play rules - no purchase or card flow inside the
      // native apps. Show the plan, point at the website.
      await _mobilePlanSheet(tier, status, canceling);
      return;
    }
    String until = '';
    if (s['currentPeriodEnd'] is Timestamp) {
      final DateTime e = (s['currentPeriodEnd'] as Timestamp).toDate();
      const List<String> mo = <String>[
        'January',
        'February',
        'March',
        'April',
        'May',
        'June',
        'July',
        'August',
        'September',
        'October',
        'November',
        'December'
      ];
      until = '${mo[e.month - 1]} ${e.day}, ${e.year}';
    }
    final String state = canceling
        ? 'Canceling - you keep full access through $until.'
        : status == 'past_due'
            ? 'Payment issue - we’ll retry your card.'
            : until.isEmpty
                ? 'Active'
                : (s['cadence'] == 'pif'
                    ? 'Paid in full - runs through $until.'
                    : 'Renews on $until.');
    // v2: canceling asks first, inside the same popup, and waits there.
    bool confirming = false;
    bool busy = false;
    String err = '';
    _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 520),
      builder: (BuildContext ctx) => StatefulBuilder(
          builder: (BuildContext ctx2, StateSetter setM) {
        void up(VoidCallback f) {
          if (ctx2.mounted) setM(f);
        }

        if (confirming) {
          return _lzFrame(ctx2,
              icon: Icons.warning_amber_rounded,
              title: 'Cancel your subscription?',
              onBack: busy
                  ? null
                  : () => up(() {
                        confirming = false;
                        err = '';
                      }),
              children: <Widget>[
                const SizedBox(height: 14),
                Text(
                    until.isEmpty
                        ? 'You keep access through your paid period, and it won’t renew.'
                        : 'You keep full access through $until, and it won’t renew.',
                    style: TextStyle(
                        fontSize: 14.5, color: _lzFg(ink), height: 1.5)),
                _pv2Err(err),
              ],
              footer: _lzActions(
                  secondary: 'Keep my plan',
                  onSecondary: () => up(() {
                        confirming = false;
                        err = '';
                      }),
                  primary: 'Cancel subscription',
                  danger: true,
                  icon: Icons.cancel_outlined,
                  busy: busy,
                  onPrimary: () async {
                    up(() {
                      busy = true;
                      err = '';
                    });
                    try {
                      final HttpsCallable fn = FirebaseFunctions.instance
                          .httpsCallable('cancelProSubscription');
                      await fn.call(<String, dynamic>{'vendorId': vendorId});
                      if (ctx2.mounted) Navigator.pop(ctx2);
                      _toast(
                          'Canceled - you keep access through your paid period.');
                    } catch (_) {
                      up(() {
                        busy = false;
                        err = 'Could not cancel - try again.';
                      });
                    }
                  }));
        }
        return _lzFrame(ctx2,
            icon: Icons.workspace_premium_rounded,
            title: tier == 'studio' ? 'Lazo Pro Studio' : 'Lazo Pro',
            subtitle: state,
            children: <Widget>[
              const SizedBox(height: 14),
              if (status == 'past_due')
                _lzNote(Icons.credit_card_rounded,
                    'Your last payment didn’t go through. Update your card to fix it now.')
              else if (status == 'canceled')
                _lzNote(Icons.info_outline_rounded,
                    'This subscription has ended.')
              else
                _lzNote(Icons.lock_outline_rounded,
                    'Card changes happen on a secure payment page that opens in a new tab.'),
            ],
            footer: status == 'canceled'
                ? _lzActions(
                    primary: 'Done',
                    icon: Icons.check_rounded,
                    onPrimary: () => Navigator.pop(ctx2))
                : _lzActions(
                    secondary: canceling ? null : 'Cancel subscription',
                    onSecondary: () => up(() => confirming = true),
                    primary: 'Update payment method',
                    icon: Icons.credit_card_rounded,
                    onPrimary: () {
                      Navigator.pop(ctx2);
                      _startCardUpdate(vendorId);
                    }));
      }),
    );
  }

""")

    # ------------------------------------------------------------------
    # _showParseResult
    # ------------------------------------------------------------------
    rep(fn('  void _showParseResult(String vendorId, Map<String, dynamic> r) {',
           '  void _showTemplateSheet('), r"""  void _showParseResult(String vendorId, Map<String, dynamic> r) {
    final String tid = (r['templateId'] ?? '') as String;
    final String name = (r['name'] ?? 'Template') as String;
    final List<String> fields = r['fieldsDetected'] is List
        ? (r['fieldsDetected'] as List)
            .map((dynamic e) => e.toString())
            .toList()
        : <String>[];
    final List<String> notes = r['notes'] is List
        ? (r['notes'] as List).map((dynamic e) => e.toString()).toList()
        : <String>[];
    final String preview = (r['preview'] ?? '') as String;
    bool busy = false;
    String err = '';
    _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 680),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setP) => _lzFrame(ctx2,
            icon: Icons.auto_awesome_rounded,
            title: 'June read your contract',
            subtitle: name,
            children: <Widget>[
              if (fields.isNotEmpty) ...<Widget>[
                _lzSection('Fields she’ll fill in',
                    trailing: '${fields.length}'),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: fields
                      .map((String f2) => Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 10, vertical: 5),
                            decoration: BoxDecoration(
                              color: vGreen.withOpacity(.13),
                              borderRadius: BorderRadius.circular(999),
                              border:
                                  Border.all(color: vGreen.withOpacity(.5)),
                            ),
                            child: Text(f2,
                                style: TextStyle(
                                    color: _lzFg(vGreen),
                                    fontSize: 11.5,
                                    fontWeight: FontWeight.w700)),
                          ))
                      .toList(),
                ),
              ],
              ..._pv2Notes(notes),
              if (preview.isNotEmpty) ...<Widget>[
                _lzSection('Preview'),
                _pv2Doc(preview),
              ],
              const SizedBox(height: 12),
              _lzNote(Icons.verified_user_outlined,
                  'Read it through before you activate it. Only active templates can be sent to couples.'),
              _pv2Err(err),
            ],
            footer: _lzActions(
                secondary: 'Review later',
                onSecondary: () => Navigator.pop(ctx2),
                primary: 'Activate template',
                icon: Icons.check_rounded,
                busy: busy,
                onPrimary: () async {
                  setP(() {
                    busy = true;
                    err = '';
                  });
                  try {
                    await _setTemplateStatus(vendorId, tid, 'active');
                    if (ctx2.mounted) Navigator.pop(ctx2);
                    _toast('Template activated.');
                  } catch (_) {
                    if (ctx2.mounted) {
                      setP(() {
                        busy = false;
                        err =
                            'Couldn’t activate it. Check your connection and try again.';
                      });
                    }
                  }
                })),
      ),
    );
  }

""")

    # ------------------------------------------------------------------
    # _showTemplateSheet
    # ------------------------------------------------------------------
    rep(fn('  void _showTemplateSheet(String vendorId, String tid, Map<String, dynamic> t) {',
           '  Future<void> _templateEditorSheet('), r"""  void _showTemplateSheet(String vendorId, String tid, Map<String, dynamic> t) {
    final String name = (t['name'] ?? 'Template') as String;
    final String status = (t['status'] ?? 'draft') as String;
    final String body = (t['body'] ?? '') as String;
    final List<String> notes = t['notes'] is List
        ? (t['notes'] as List).map((dynamic e) => e.toString()).toList()
        : <String>[];
    final bool active = status == 'active';
    bool busy = false;
    String err = '';
    _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 680),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setT) => _lzFrame(ctx2,
            icon: Icons.description_rounded,
            title: name,
            subtitle: active
                ? 'Active - ready to send to couples.'
                : 'Needs review - activate it to send it to couples.',
            children: <Widget>[
              ..._pv2Notes(notes),
              _lzSection('The contract'),
              _pv2Doc(body),
              _pv2Err(err),
            ],
            footer: Row(children: <Widget>[
              IconButton(
                tooltip: 'Delete template',
                icon: Icon(Icons.delete_outline_rounded,
                    color: _lzFg(const Color(0xFFB3413A))),
                onPressed: busy
                    ? null
                    : _h(() async {
                        final bool ok = await _lzConfirm(
                            'Delete this template?',
                            '“$name” is removed from your templates for good.',
                            confirm: 'Delete template',
                            cancel: 'Keep it',
                            danger: true);
                        if (!ok) return;
                        if (ctx2.mounted) Navigator.pop(ctx2);
                        await FirebaseFirestore.instance
                            .collection('vendors')
                            .doc(vendorId)
                            .collection('contractTemplates')
                            .doc(tid)
                            .delete();
                        _toast('Template deleted');
                      }),
              ),
              Expanded(
                child: _lzActions(
                    secondary: 'Edit',
                    onSecondary: () {
                      Navigator.pop(ctx2);
                      _templateEditorSheet(vendorId, tid);
                    },
                    primary: active ? 'Deactivate' : 'Activate template',
                    icon: active
                        ? Icons.pause_circle_outline_rounded
                        : Icons.check_rounded,
                    busy: busy,
                    onPrimary: () async {
                      setT(() {
                        busy = true;
                        err = '';
                      });
                      try {
                        await _setTemplateStatus(
                            vendorId, tid, active ? 'draft' : 'active');
                        if (ctx2.mounted) Navigator.pop(ctx2);
                        _toast(active
                            ? 'Moved back to review.'
                            : 'Template activated.');
                      } catch (_) {
                        if (ctx2.mounted) {
                          setT(() {
                            busy = false;
                            err =
                                'Couldn’t change it. Check your connection and try again.';
                          });
                        }
                      }
                    }),
              ),
            ])),
      ),
    );
  }

""")

    # ------------------------------------------------------------------
    # _templateEditorSheet (full editor: own layout, frame header + footer)
    # ------------------------------------------------------------------
    rep(fn('  Future<void> _templateEditorSheet(String vendorId, String tid) async {',
           '  Future<void> _setTemplateStatus('), r"""  Future<void> _templateEditorSheet(String vendorId, String tid) async {
    final DocumentReference<Map<String, dynamic>> ref = FirebaseFirestore
        .instance
        .collection('vendors')
        .doc(vendorId)
        .collection('contractTemplates')
        .doc(tid);
    final DocumentSnapshot<Map<String, dynamic>> snap = await ref.get();
    if (!snap.exists || !mounted) {
      return;
    }
    final Map<String, dynamic> t = snap.data()!;
    final TextEditingController nameC =
        TextEditingController(text: (t['name'] ?? '').toString());
    final TextEditingController bodyC =
        TextEditingController(text: (t['body'] ?? '').toString());
    bool saving = false;
    String err = '';
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 820),
      builder: (BuildContext ctx) {
        return StatefulBuilder(builder: (BuildContext ctx2, StateSetter setE) {
          final bool longEnough = bodyC.text.trim().length >= 40;
          return Padding(
            padding:
                EdgeInsets.only(bottom: MediaQuery.of(ctx2).viewInsets.bottom),
            child: ConstrainedBox(
              constraints: BoxConstraints(
                  maxHeight: MediaQuery.of(ctx2).size.height * .92),
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: <Widget>[
                    _pv2Head(ctx2, Icons.edit_note_rounded, 'Edit template',
                        subtitle:
                            'Change any wording. Keep the {{double_braces}} - they fill in automatically.'),
                    _pv2Divider(),
                    Expanded(
                      child: Padding(
                        padding: const EdgeInsets.fromLTRB(22, 14, 22, 12),
                        child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: <Widget>[
                              TextField(
                                controller: nameC,
                                textCapitalization: TextCapitalization.words,
                                textInputAction: TextInputAction.next,
                                style: TextStyle(
                                    color: _lzFg(ink), fontSize: 14.5),
                                decoration: _epDeco('Template name', ''),
                              ),
                              const SizedBox(height: 10),
                              Expanded(
                                child: Container(
                                  decoration: BoxDecoration(
                                    color: _lzBg(Colors.white),
                                    borderRadius: BorderRadius.circular(14),
                                    border:
                                        Border.all(color: _lzLine(goldLine)),
                                  ),
                                  padding: const EdgeInsets.all(12),
                                  child: TextField(
                                    controller: bodyC,
                                    maxLines: null,
                                    expands: true,
                                    onChanged: (String _) => setE(() {}),
                                    textAlignVertical: TextAlignVertical.top,
                                    style: TextStyle(
                                        color: _lzFg(ink),
                                        fontSize: 12.5,
                                        height: 1.5,
                                        fontFamily: 'monospace'),
                                    decoration: const InputDecoration(
                                        border: InputBorder.none),
                                  ),
                                ),
                              ),
                              const SizedBox(height: 8),
                              Text(
                                  longEnough
                                      ? 'Contracts already sent keep the wording they were signed with.'
                                      : 'That looks too short to be a contract.',
                                  style: TextStyle(
                                      fontSize: 12,
                                      color: longEnough
                                          ? _lzFg(muted)
                                          : _lzFg(const Color(0xFFB3413A)),
                                      height: 1.4)),
                              _pv2Err(err),
                            ]),
                      ),
                    ),
                    _pv2Foot(
                      ctx2,
                      _lzActions(
                          secondary: 'Cancel',
                          onSecondary: () => Navigator.pop(ctx2),
                          primary: 'Save changes',
                          icon: Icons.check_rounded,
                          busy: saving,
                          onPrimary: !longEnough
                              ? null
                              : () async {
                                  final String body = bodyC.text;
                                  if (body.trim().length < 40) {
                                    return;
                                  }
                                  setE(() {
                                    saving = true;
                                    err = '';
                                  });
                                  final RegExp tokRe = RegExp(
                                      r'\{\{\s*([a-zA-Z0-9_]+)\s*\}\}');
                                  final List<String> fields = <String>[];
                                  for (final RegExpMatch m
                                      in tokRe.allMatches(body)) {
                                    final String f = m.group(1)!;
                                    if (!fields.contains(f)) {
                                      fields.add(f);
                                    }
                                  }
                                  try {
                                    await ref.set(<String, dynamic>{
                                      'name': nameC.text.trim().isEmpty
                                          ? (t['name'] ?? 'Template')
                                          : nameC.text.trim(),
                                      'body': body,
                                      'fields': fields,
                                      'editedAt': FieldValue.serverTimestamp(),
                                      'updatedAt':
                                          FieldValue.serverTimestamp(),
                                    }, SetOptions(merge: true));
                                    if (ctx2.mounted) {
                                      Navigator.pop(ctx2);
                                    }
                                    _toast(
                                        'Template saved - ${fields.length} auto-fill fields.');
                                  } catch (e) {
                                    if (ctx2.mounted) {
                                      setE(() {
                                        saving = false;
                                        err =
                                            'Couldn’t save. Check your connection and try again.';
                                      });
                                    }
                                  }
                                }),
                    ),
                  ]),
            ),
          );
        });
      },
    );
  }

""")

    # ------------------------------------------------------------------
    # _maybeAskPush
    # ------------------------------------------------------------------
    rep(fn('  Future<void> _maybeAskPush() async {',
           '  Future<void> _stampPushAsk('), r"""  Future<void> _maybeAskPush() async {
    if (_vendorIdCache.isEmpty) return;
    final DocumentReference<Map<String, dynamic>> vref =
        FirebaseFirestore.instance.collection('vendors').doc(_vendorIdCache);
    try {
      final DocumentSnapshot<Map<String, dynamic>> v = await vref.get();
      final Map<String, dynamic> d = v.data() ?? <String, dynamic>{};
      if ((d['pushAskAnswer'] ?? '') == 'yes') return;
      final dynamic asked = d['pushAskedAt'];
      if (asked is Timestamp &&
          DateTime.now().difference(asked.toDate()).inDays < 30) return;
    } catch (_) {
      return;
    }
    // Let the sent message land in the thread before anything covers it.
    await Future<void>.delayed(const Duration(milliseconds: 1400));
    if (!mounted) return;
    final bool yes = await _lzConfirm(
        'Want the next lead the moment it lands?',
        'Couples message a few vendors at once, and the first real reply usually wins the booking. We’ll ping you when one writes - and for nothing else.',
        confirm: 'Yes, notify me',
        cancel: 'Not now',
        icon: Icons.notifications_active_rounded);
    if (yes != true) {
      await _stampPushAsk('no');
      return;
    }
    final bool ok = await _registerPush();
    // 'blocked' means they said yes to us and the OS said no - asking again
    // can't help, only a trip to system settings can.
    await _stampPushAsk(ok ? 'yes' : 'blocked');
    if (ok) _toast('Done - we’ll let you know.');
  }

""")

    # ------------------------------------------------------------------
    # _sendQuestionnaireSheet
    # ------------------------------------------------------------------
    rep(fn('  Future<void> _sendQuestionnaireSheet(',
           '  // Build or edit a reusable questionnaire template.'), r"""  Future<void> _sendQuestionnaireSheet(
      String inquiryId, Map<String, dynamic> inq) async {
    final String vendorId = (inq['vendorId'] ?? '').toString();
    if (vendorId.isEmpty) {
      _toast('Vendor profile not found on this inquiry.');
      return;
    }
    final DocumentSnapshot<Map<String, dynamic>> vs = await FirebaseFirestore
        .instance
        .collection('vendors')
        .doc(vendorId)
        .get();
    final Map<String, dynamic> vd = vs.data() ?? <String, dynamic>{};
    final String bizName = (vd['name'] ?? 'Your vendor').toString();
    if (!mounted) return;
    _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 600),
      builder: (BuildContext ctx) => _lzFrame(ctx,
          icon: Icons.fact_check_rounded,
          title: 'Send a questionnaire',
          subtitle:
              'They answer in their thread, and it comes from $bizName.',
          children: <Widget>[
            StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
              stream: FirebaseFirestore.instance
                  .collection('vendors')
                  .doc(vendorId)
                  .collection('questionnaireTemplates')
                  .snapshots(),
              builder: (BuildContext c2,
                  AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> s) {
                final List<QueryDocumentSnapshot<Map<String, dynamic>>> tpl =
                    s.data?.docs ??
                        <QueryDocumentSnapshot<Map<String, dynamic>>>[];
                return Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: <Widget>[
                      if (!s.hasData && !s.hasError) ...<Widget>[
                        const SizedBox(height: 14),
                        _lzBusy('Loading your questionnaires…'),
                      ],
                      if (tpl.isNotEmpty) ...<Widget>[
                        _lzSection('Your questionnaires',
                            trailing: 'Tap one to send'),
                        ...tpl.map(
                            (QueryDocumentSnapshot<Map<String, dynamic>> d) {
                          final Map<String, dynamic> q = d.data();
                          final List<dynamic> qs =
                              (q['questions'] as List?) ?? const <dynamic>[];
                          return _pv2Row(
                            icon: Icons.fact_check_rounded,
                            title: (q['title'] ?? 'Questionnaire') as String,
                            sub:
                                '${qs.length} question${qs.length == 1 ? '' : 's'}',
                            trailing: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: <Widget>[
                                  IconButton(
                                    tooltip: 'Edit',
                                    icon: Icon(Icons.edit_rounded,
                                        color: _lzFg(muted), size: 18),
                                    onPressed: _h(() {
                                      Navigator.pop(ctx);
                                      _questionnaireEditor(vendorId, d.id, q);
                                    }),
                                  ),
                                  Icon(Icons.send_rounded,
                                      color: _lzFg(plum), size: 18),
                                  const SizedBox(width: 6),
                                ]),
                            onTap: () {
                              Navigator.pop(ctx);
                              _createQuestionnaire(
                                  inquiryId,
                                  (q['type'] ?? 'custom').toString(),
                                  (q['title'] ?? 'Questionnaire').toString(),
                                  qs.map((dynamic e) => e.toString()).toList(),
                                  bizName);
                            },
                          );
                        }),
                      ],
                      _lzSection(
                          tpl.isEmpty ? 'Start one' : 'Or start a new one'),
                      _pv2Row(
                        icon: Icons.auto_awesome_rounded,
                        title: tpl.isEmpty
                            ? 'Start from the Lazo set for ${_catLabelFor((((vd['categories'] as List?) ?? const <dynamic>[
                                  ''
                                ]).first).toString())}s'
                            : 'Add another from the Lazo starter set',
                        sub:
                            '${_starterFor(vd).length} questions written for your craft - edit freely',
                        onTap: () {
                          Navigator.pop(ctx);
                          _questionnaireEditor(
                              vendorId, null, <String, dynamic>{
                            'title': 'Wedding Day Details',
                            'questions': _starterFor(vd),
                          });
                        },
                      ),
                      _pv2Row(
                        icon: Icons.edit_note_rounded,
                        title: 'Write my own from scratch',
                        sub: 'A blank questionnaire, in your words',
                        onTap: () {
                          Navigator.pop(ctx);
                          _questionnaireEditor(
                              vendorId, null, <String, dynamic>{
                            'title': '',
                            'questions': <String>[],
                          });
                        },
                      ),
                    ]);
              },
            ),
          ]),
    );
  }

""")

    # ------------------------------------------------------------------
    # _juneQuestions
    # ------------------------------------------------------------------
    rep(fn('  Future<List<String>?> _juneQuestions(String vendorId,',
           '  Future<void> _questionnaireEditor('), r"""  Future<List<String>?> _juneQuestions(String vendorId,
      {required String mode, List<String> existing = const <String>[]}) async {
    String brief = '';
    if (mode == 'draft') {
      final TextEditingController b = TextEditingController();
      final bool? go = await _lzSheet<bool>(
        context: context,
        constraints: const BoxConstraints(maxWidth: 520),
        builder: (BuildContext ctx) => _lzFrame(ctx,
            icon: Icons.auto_awesome_rounded,
            title: 'What is it for?',
            subtitle:
                'Optional. June already knows your craft, packages and how you work.',
            children: <Widget>[
              const SizedBox(height: 14),
              TextField(
                controller: b,
                autofocus: true,
                textInputAction: TextInputAction.done,
                onSubmitted: (String _) => Navigator.pop(ctx, true),
                style: TextStyle(color: _lzFg(ink), fontSize: 14.5),
                decoration: _epDeco(
                    'A word or two', 'wedding day, elopement, engagement session'),
              ),
            ],
            footer: _lzActions(
                secondary: 'Cancel',
                onSecondary: () => Navigator.pop(ctx, false),
                primary: 'Ask June',
                icon: Icons.auto_awesome_rounded,
                onPrimary: () => Navigator.pop(ctx, true))),
      );
      if (go != true) return null;
      brief = b.text.trim();
    }
    _showJuneVeil(
        mode == 'tighten'
            ? 'June is tightening it…'
            : 'June is writing your questions…',
        'She is reading your packages, your services, and the way you work.');
    try {
      final HttpsCallable fn = FirebaseFunctions.instance.httpsCallable(
          'juneQuestionnaire',
          options: HttpsCallableOptions(timeout: const Duration(seconds: 120)));
      final HttpsCallableResult<dynamic> out = await fn.call(<String, dynamic>{
        'vendorId': vendorId,
        'mode': mode,
        'brief': brief,
        'questions': existing,
      });
      _popJuneVeil();
      final Map<String, dynamic> r = Map<String, dynamic>.from(out.data as Map);
      final List<String> qs = (r['questions'] as List?)
              ?.map((dynamic e) => e.toString())
              .where((String s) => s.trim().isNotEmpty)
              .toList() ??
          <String>[];
      if (qs.isEmpty) {
        _toast('June came back empty - try again.');
        return null;
      }
      _toast('${qs.length} questions ready - edit anything, then save.');
      return qs;
    } on FirebaseFunctionsException catch (e) {
      _popJuneVeil();
      if ((e.message ?? '').contains('studio-required')) {
        _toast('June for Studio is a Pro Studio feature.');
        _upgradeSheet(vendorId);
      } else {
        _toast(e.message ?? 'June could not write that one.');
      }
      return null;
    } catch (_) {
      _popJuneVeil();
      _toast('June could not write that one - try again.');
      return null;
    }
  }

""")

    # ------------------------------------------------------------------
    # _questionnaireEditor (reorderable editor: own layout, frame header + footer)
    # ------------------------------------------------------------------
    rep(fn('  Future<void> _questionnaireEditor(',
           '  Future<void> _createQuestionnaire('), r"""  Future<void> _questionnaireEditor(
      String vendorId, String? templateId, Map<String, dynamic> seed) async {
    final TextEditingController titleC =
        TextEditingController(text: (seed['title'] ?? '').toString());
    final List<TextEditingController> qcs =
        ((seed['questions'] as List?) ?? const <dynamic>[])
            .map((dynamic e) => TextEditingController(text: e.toString()))
            .toList();
    if (qcs.isEmpty) qcs.add(TextEditingController());
    bool saving = false;
    String err = '';
    if (!mounted) return;
    final ButtonStyle juneBtn = OutlinedButton.styleFrom(
        foregroundColor: _lzFg(plum),
        side: BorderSide(color: gold.withOpacity(.8)),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        padding: const EdgeInsets.symmetric(vertical: 11));
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 680),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setE) {
          final bool hasQ =
              qcs.any((TextEditingController x) => x.text.trim().isNotEmpty);
          return Padding(
            padding:
                EdgeInsets.only(bottom: MediaQuery.of(ctx2).viewInsets.bottom),
            child: SizedBox(
              height: MediaQuery.of(ctx2).size.height * .86,
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: <Widget>[
                    _pv2Head(
                        ctx2,
                        Icons.fact_check_rounded,
                        templateId == null
                            ? 'New questionnaire'
                            : 'Edit questionnaire',
                        subtitle:
                            'Make it sound like you. Couples see it under your name.',
                        actions: <Widget>[
                          if (templateId != null)
                            IconButton(
                              tooltip: 'Delete questionnaire',
                              icon: Icon(Icons.delete_outline_rounded,
                                  color: _lzFg(const Color(0xFFB3413A)),
                                  size: 20),
                              onPressed: _h(() async {
                                final bool ok = await _lzConfirm(
                                    'Delete this questionnaire?',
                                    'It’s removed from your templates. Ones you already sent stay in their threads.',
                                    confirm: 'Delete questionnaire',
                                    cancel: 'Keep it',
                                    danger: true);
                                if (!ok) return;
                                await FirebaseFirestore.instance
                                    .collection('vendors')
                                    .doc(vendorId)
                                    .collection('questionnaireTemplates')
                                    .doc(templateId)
                                    .delete();
                                if (ctx2.mounted) Navigator.pop(ctx2);
                                _toast('Template deleted');
                              }),
                            ),
                        ]),
                    _pv2Divider(),
                    Expanded(
                      child: Padding(
                        padding: const EdgeInsets.fromLTRB(22, 14, 22, 0),
                        child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: <Widget>[
                              TextField(
                                controller: titleC,
                                autofocus: titleC.text.isEmpty,
                                textCapitalization: TextCapitalization.words,
                                style: TextStyle(
                                    color: _lzFg(ink), fontSize: 15),
                                decoration: _epDeco(
                                    'Title', 'e.g. Wedding Day Details'),
                              ),
                              const SizedBox(height: 10),
                              Row(children: <Widget>[
                                Expanded(
                                  child: OutlinedButton.icon(
                                    style: juneBtn,
                                    onPressed: _h(() async {
                                      final List<String>? out =
                                          await _juneQuestions(vendorId,
                                              mode: 'draft',
                                              existing: qcs
                                                  .map((TextEditingController
                                                          x) =>
                                                      x.text.trim())
                                                  .where((String s) =>
                                                      s.isNotEmpty)
                                                  .toList());
                                      if (out == null) return;
                                      setE(() {
                                        qcs.clear();
                                        for (final String q in out) {
                                          qcs.add(
                                              TextEditingController(text: q));
                                        }
                                        if (titleC.text.trim().isEmpty) {
                                          titleC.text = 'Wedding Day Details';
                                        }
                                      });
                                    }),
                                    icon: const Icon(Icons.auto_awesome_rounded,
                                        size: 15),
                                    label: const Text('June, write it',
                                        style: TextStyle(
                                            fontSize: 12.5,
                                            fontWeight: FontWeight.w800)),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: OutlinedButton.icon(
                                    style: juneBtn,
                                    onPressed: _h(() async {
                                      final List<String> cur = qcs
                                          .map((TextEditingController x) =>
                                              x.text.trim())
                                          .where((String s) => s.isNotEmpty)
                                          .toList();
                                      if (cur.length < 2) {
                                        _toast(
                                            'Add a few questions first and June will tidy them.');
                                        return;
                                      }
                                      final List<String>? out =
                                          await _juneQuestions(vendorId,
                                              mode: 'tighten', existing: cur);
                                      if (out == null) return;
                                      setE(() {
                                        qcs.clear();
                                        for (final String q in out) {
                                          qcs.add(
                                              TextEditingController(text: q));
                                        }
                                      });
                                    }),
                                    icon: const Icon(
                                        Icons.auto_fix_high_rounded,
                                        size: 15),
                                    label: const Text('June, tighten it',
                                        style: TextStyle(
                                            fontSize: 12.5,
                                            fontWeight: FontWeight.w800)),
                                  ),
                                ),
                              ]),
                              Padding(
                                padding:
                                    const EdgeInsets.only(top: 6, bottom: 2),
                                child: Text(
                                    'June reads your packages and how you work. Nothing is saved until you save.',
                                    style: TextStyle(
                                        fontSize: 11.5, color: _lzFg(muted))),
                              ),
                              _lzSection('Questions',
                                  trailing: 'Drag to reorder'),
                              Expanded(
                                child: ReorderableListView.builder(
                                  buildDefaultDragHandles: false,
                                  itemCount: qcs.length,
                                  onReorder: (int a, int b) {
                                    setE(() {
                                      if (b > a) b -= 1;
                                      final TextEditingController m =
                                          qcs.removeAt(a);
                                      qcs.insert(b, m);
                                    });
                                  },
                                  itemBuilder: (BuildContext c3, int i) {
                                    return Padding(
                                      key: ValueKey<int>(qcs[i].hashCode),
                                      padding:
                                          const EdgeInsets.only(bottom: 8),
                                      child: Row(children: <Widget>[
                                        ReorderableDragStartListener(
                                          index: i,
                                          child: Padding(
                                            padding: const EdgeInsets.only(
                                                right: 6),
                                            child: Icon(
                                                Icons.drag_indicator_rounded,
                                                color: _lzFg(muted),
                                                size: 18),
                                          ),
                                        ),
                                        Expanded(
                                          child: TextField(
                                            controller: qcs[i],
                                            maxLines: null,
                                            textCapitalization:
                                                TextCapitalization.sentences,
                                            onChanged: (String _) =>
                                                setE(() {}),
                                            style: TextStyle(
                                                color: _lzFg(ink),
                                                fontSize: 13.5),
                                            decoration: _epDeco(
                                                'Question ${i + 1}', ''),
                                          ),
                                        ),
                                        IconButton(
                                          tooltip: 'Remove question',
                                          icon: Icon(Icons.close_rounded,
                                              color: _lzFg(muted), size: 17),
                                          onPressed: _h(
                                              () => setE(() => qcs.removeAt(i))),
                                        ),
                                      ]),
                                    );
                                  },
                                ),
                              ),
                              Align(
                                alignment: Alignment.centerLeft,
                                child: TextButton.icon(
                                  onPressed: _h(() => setE(
                                      () => qcs.add(TextEditingController()))),
                                  icon: Icon(Icons.add_rounded,
                                      color: _lzFg(plum), size: 18),
                                  label: Text('Add a question',
                                      style: TextStyle(
                                          color: _lzFg(plum),
                                          fontSize: 13,
                                          fontWeight: FontWeight.w800)),
                                ),
                              ),
                              _pv2Err(err),
                              const SizedBox(height: 8),
                            ]),
                      ),
                    ),
                    _pv2Foot(
                      ctx2,
                      _lzActions(
                          secondary: 'Cancel',
                          onSecondary: () => Navigator.pop(ctx2),
                          primary: 'Save questionnaire',
                          icon: Icons.check_rounded,
                          busy: saving,
                          onPrimary: !hasQ
                              ? null
                              : () async {
                                  final List<String> qs = qcs
                                      .map((TextEditingController c4) =>
                                          c4.text.trim())
                                      .where((String s) => s.isNotEmpty)
                                      .toList();
                                  if (qs.isEmpty) {
                                    return;
                                  }
                                  setE(() {
                                    saving = true;
                                    err = '';
                                  });
                                  final Map<String, dynamic> data =
                                      <String, dynamic>{
                                    'title': titleC.text.trim().isEmpty
                                        ? 'Wedding Day Details'
                                        : titleC.text.trim(),
                                    'questions': qs,
                                    'type': 'custom',
                                    'updatedAt': FieldValue.serverTimestamp(),
                                  };
                                  final CollectionReference<
                                          Map<String, dynamic>> col =
                                      FirebaseFirestore.instance
                                          .collection('vendors')
                                          .doc(vendorId)
                                          .collection('questionnaireTemplates');
                                  try {
                                    if (templateId == null) {
                                      data['createdAt'] =
                                          FieldValue.serverTimestamp();
                                      await col.add(data);
                                    } else {
                                      await col
                                          .doc(templateId)
                                          .set(data, SetOptions(merge: true));
                                    }
                                    if (ctx2.mounted) Navigator.pop(ctx2);
                                    _toast('Saved. Send it from any thread.');
                                  } catch (_) {
                                    if (ctx2.mounted) {
                                      setE(() {
                                        saving = false;
                                        err =
                                            'Couldn’t save. Check your connection and try again.';
                                      });
                                    }
                                  }
                                }),
                    ),
                  ]),
            ),
          );
        },
      ),
    );
  }

""")

    # ------------------------------------------------------------------
    # _questionnaireAnswersSheet
    # ------------------------------------------------------------------
    rep(fn('  void _questionnaireAnswersSheet(Map<String, dynamic> qn) {',
           '  Widget _contractsStrip('), r"""  void _questionnaireAnswersSheet(Map<String, dynamic> qn) {
    final List<dynamic> qs = qn['questions'] is List
        ? qn['questions'] as List<dynamic>
        : <dynamic>[];
    final Map<String, dynamic> ans = qn['answers'] is Map
        ? Map<String, dynamic>.from(qn['answers'] as Map)
        : <String, dynamic>{};
    int answered = 0;
    for (int i = 0; i < qs.length; i++) {
      if ((ans['$i'] ?? '').toString().trim().isNotEmpty) answered++;
    }
    _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 640),
      builder: (BuildContext ctx) => _lzFrame(ctx,
          icon: Icons.fact_check_rounded,
          title: (qn['title'] ?? 'Responses') as String,
          subtitle: '$answered of ${qs.length} answered',
          children: <Widget>[
            const SizedBox(height: 14),
            if (qs.isEmpty)
              _pv2Empty(Icons.help_outline_rounded,
                  'There are no questions in this one.'),
            for (int i = 0; i < qs.length; i++)
              Container(
                margin: const EdgeInsets.only(bottom: 10),
                padding: const EdgeInsets.fromLTRB(12, 12, 14, 12),
                decoration: BoxDecoration(
                  color: _lzBg(card),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: _lzLine(goldLine)),
                ),
                child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Container(
                          width: 24,
                          height: 24,
                          alignment: Alignment.center,
                          decoration: const BoxDecoration(
                              color: plumDeep, shape: BoxShape.circle),
                          child: Text('${i + 1}',
                              style: const TextStyle(
                                  color: gold,
                                  fontSize: 11.5,
                                  fontWeight: FontWeight.w800))),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Text(qs[i].toString(),
                                  style: TextStyle(
                                      color: _lzFg(plum),
                                      fontSize: 13,
                                      fontWeight: FontWeight.w700,
                                      height: 1.35)),
                              const SizedBox(height: 5),
                              (ans['$i'] ?? '').toString().trim().isEmpty
                                  ? Text('No answer',
                                      style: TextStyle(
                                          fontSize: 13.5,
                                          fontStyle: FontStyle.italic,
                                          color: _lzFg(muted)))
                                  : SelectableText((ans['$i'] ?? '').toString(),
                                      style: TextStyle(
                                          fontSize: 14,
                                          color: _lzFg(ink),
                                          height: 1.45)),
                            ]),
                      ),
                    ]),
              ),
          ]),
    );
  }

""")

    # ------------------------------------------------------------------
    # _contractActionsSheet
    # ------------------------------------------------------------------
    rep(fn('  void _contractActionsSheet(String vendorId, String inquiryId,',
           '  Future<void> _rescindContract('), r"""  void _contractActionsSheet(String vendorId, String inquiryId,
      String contractId, Map<String, dynamic> ct) {
    final String status = (ct['status'] ?? 'draft') as String;
    final String pdfPath = (ct['pdfPath'] ?? '') as String;
    final String signedPath = (ct['signedPdfPath'] ?? '') as String;
    final String openPath = signedPath.isNotEmpty ? signedPath : pdfPath;
    final int nMiss =
        ct['missingFields'] is List ? (ct['missingFields'] as List).length : 0;
    final String sub = status == 'signed'
        ? 'Signed by the couple.'
        : status == 'sent'
            ? 'Sent - waiting on the couple’s signature.'
            : status == 'declined'
                ? 'The couple declined this one.'
                : status == 'draft'
                    ? (nMiss > 0
                        ? '$nMiss blank${nMiss == 1 ? '' : 's'} to fill before it can be sent.'
                        : 'Ready to send.')
                    : '';
    _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 520),
      builder: (BuildContext ctx) => _lzFrame(ctx,
          icon: Icons.history_edu_rounded,
          title: (ct['templateName'] ?? 'Contract') as String,
          subtitle: sub,
          children: <Widget>[
            const SizedBox(height: 14),
            if (openPath.isNotEmpty)
              _pv2Row(
                icon: Icons.picture_as_pdf_rounded,
                title: 'View PDF',
                sub: signedPath.isNotEmpty
                    ? 'The signed copy'
                    : 'Opens in a new tab',
                onTap: () {
                  Navigator.pop(ctx);
                  _openContractPdf(openPath);
                },
              ),
            if (status == 'draft' && nMiss == 0)
              _pv2Row(
                icon: Icons.send_rounded,
                title: 'Send for signature',
                sub: 'The couple signs from their thread or email',
                onTap: () {
                  Navigator.pop(ctx);
                  _sendForSignature(vendorId, inquiryId, contractId);
                },
              ),
            if (status == 'draft')
              _pv2Row(
                icon: Icons.delete_outline_rounded,
                title: 'Delete this contract',
                sub: 'It hasn’t been sent, so it goes with its PDF',
                danger: true,
                onTap: () {
                  Navigator.pop(ctx);
                  _rescindContract(
                      vendorId,
                      inquiryId,
                      contractId,
                      'Delete this contract?',
                      'It hasn’t been sent yet. The contract and its PDF are removed for good.');
                },
              ),
            if (status == 'sent') ...<Widget>[
              _lzNote(Icons.info_outline_rounded,
                  'A sent contract can’t be edited. To change the terms, rescind it and send a new one - June refills everything.'),
              const SizedBox(height: 10),
              _pv2Row(
                icon: Icons.undo_rounded,
                title: 'Rescind and send a new one',
                sub: 'Voids their signing link and clears it from the thread',
                danger: true,
                onTap: () {
                  Navigator.pop(ctx);
                  _rescindContract(
                      vendorId,
                      inquiryId,
                      contractId,
                      'Rescind this contract?',
                      'The couple’s signing link is voided and the contract disappears from their thread. You can generate and send a new one anytime.');
                },
              ),
            ],
            if (status == 'declined')
              _pv2Row(
                icon: Icons.archive_outlined,
                title: 'Remove from thread',
                sub: 'Hidden from the thread - the record is kept',
                onTap: () {
                  Navigator.pop(ctx);
                  _rescindContract(
                      vendorId,
                      inquiryId,
                      contractId,
                      'Remove this declined contract?',
                      'It’s hidden from the thread - the record is kept.');
                },
              ),
            if (status == 'signed')
              _lzNote(Icons.verified_rounded,
                  'Signed contracts are executed legal records, so they can’t be removed.'),
          ]),
    );
  }

""")

    # ------------------------------------------------------------------
    # _rescindContract
    # ------------------------------------------------------------------
    rep(fn('  Future<void> _rescindContract(String vendorId, String inquiryId,',
           '  Future<void> _openContractPdf('), r"""  Future<void> _rescindContract(String vendorId, String inquiryId,
      String contractId, String title, String message) async {
    final bool go = await _lzConfirm(title, message,
        confirm: title.startsWith('Rescind')
            ? 'Rescind contract'
            : title.startsWith('Remove')
                ? 'Remove contract'
                : 'Delete contract',
        cancel: 'Keep it',
        danger: true);
    if (go != true) {
      return;
    }
    try {
      final HttpsCallable fn = FirebaseFunctions.instance.httpsCallable(
          'rescindContract',
          options: HttpsCallableOptions(timeout: const Duration(seconds: 60)));
      final HttpsCallableResult<dynamic> out = await fn.call(<String, dynamic>{
        'vendorId': vendorId,
        'inquiryId': inquiryId,
        'contractId': contractId,
      });
      final Map<String, dynamic> r = Map<String, dynamic>.from(out.data as Map);
      final String res = (r['result'] ?? '') as String;
      _toast(res == 'deleted'
          ? 'Contract deleted'
          : res == 'rescinded'
              ? 'Contract rescinded'
              : 'Removed');
    } on FirebaseFunctionsException catch (e) {
      _toast(e.message ?? 'Could not complete - try again.');
    } catch (_) {
      _toast('Could not complete - try again.');
    }
  }

""")

    # ------------------------------------------------------------------
    # _startContractFlow
    # ------------------------------------------------------------------
    rep(fn('  Future<void> _startContractFlow(',
           '  void _noActiveTemplateSheet('), r"""  Future<void> _startContractFlow(
      String inquiryId, Map<String, dynamic> inq) async {
    final String vendorId = (inq['vendorId'] ?? '') as String;
    if (vendorId.isEmpty) {
      _toast('Vendor profile not found on this inquiry.');
      return;
    }
    _showJuneVeil('Opening your contract studio…',
        'June is gathering what she already knows - names, dates, venue, pricing.');
    final QuerySnapshot<Map<String, dynamic>> allT = await FirebaseFirestore
        .instance
        .collection('vendors')
        .doc(vendorId)
        .collection('contractTemplates')
        .get();
    final List<QueryDocumentSnapshot<Map<String, dynamic>>> actives = allT.docs
        .where((QueryDocumentSnapshot<Map<String, dynamic>> d) =>
            (d.data()['status'] ?? 'draft') == 'active')
        .toList();
    final List<QueryDocumentSnapshot<Map<String, dynamic>>> drafts = allT.docs
        .where((QueryDocumentSnapshot<Map<String, dynamic>> d) =>
            (d.data()['status'] ?? 'draft') != 'active')
        .toList();
    if (actives.isEmpty) {
      _popJuneVeil();
      _noActiveTemplateSheet(vendorId, inquiryId, inq, drafts);
      return;
    }
    final List<QueryDocumentSnapshot<Map<String, dynamic>>> ts0 = actives;
    if (ts0.length == 1) {
      _contractValuesForm(
          vendorId, inquiryId, inq, ts0.first.id, ts0.first.data());
      return;
    }
    if (!mounted) {
      _popJuneVeil();
      return;
    }
    _popJuneVeil();
    _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 520),
      builder: (BuildContext ctx) => _lzFrame(ctx,
          icon: Icons.description_rounded,
          title: 'Which template?',
          subtitle: 'June fills in what she already knows about this couple.',
          children: <Widget>[
            const SizedBox(height: 14),
            ...ts0.map((QueryDocumentSnapshot<Map<String, dynamic>> d) =>
                _pv2Row(
                  icon: Icons.description_rounded,
                  title: (d.data()['name'] ?? 'Template') as String,
                  onTap: () {
                    Navigator.pop(ctx);
                    _contractValuesForm(
                        vendorId, inquiryId, inq, d.id, d.data());
                  },
                )),
          ]),
    );
  }

""")

    # ------------------------------------------------------------------
    # _noActiveTemplateSheet
    # ------------------------------------------------------------------
    rep(fn('  void _noActiveTemplateSheet(',
           '  void _reviewAndUseTemplate('), r"""  void _noActiveTemplateSheet(
      String vendorId,
      String inquiryId,
      Map<String, dynamic> inq,
      List<QueryDocumentSnapshot<Map<String, dynamic>>> drafts) {
    _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext ctx) => _lzFrame(ctx,
          icon: drafts.isEmpty
              ? Icons.upload_file_rounded
              : Icons.fact_check_rounded,
          title: drafts.isEmpty
              ? 'Add a contract template first'
              : 'One quick review first',
          subtitle: drafts.isEmpty
              ? 'June turns your own contract into a reusable template in about a minute.'
              : 'Look over June’s conversion and activate it. This contract fills in right after.',
          children: <Widget>[
            const SizedBox(height: 14),
            if (drafts.isEmpty) ...<Widget>[
              _pv2Row(
                icon: Icons.upload_file_rounded,
                title: 'Upload your contract',
                sub: 'A PDF, Word or text file - from any CRM or your own files',
                onTap: () {
                  Navigator.pop(ctx);
                  _uploadContractTemplate(vendorId);
                },
              ),
              _pv2Row(
                icon: Icons.auto_stories_rounded,
                title: 'Use a Lazo starter template',
                sub: 'Start from a ready-made contract and make it yours',
                onTap: () {
                  Navigator.pop(ctx);
                  _starterLibrarySheet(vendorId);
                },
              ),
            ] else ...<Widget>[
              _lzSection('Waiting for your review',
                  trailing: '${drafts.length}'),
              ...drafts.map((QueryDocumentSnapshot<Map<String, dynamic>> d) =>
                  _pv2Row(
                    icon: Icons.description_rounded,
                    title: (d.data()['name'] ?? 'Template') as String,
                    sub: 'Needs review',
                    onTap: () {
                      Navigator.pop(ctx);
                      _reviewAndUseTemplate(
                          vendorId, inquiryId, inq, d.id, d.data());
                    },
                  )),
            ],
          ]),
    );
  }

""")

    # ------------------------------------------------------------------
    # _reviewAndUseTemplate
    # ------------------------------------------------------------------
    rep(fn('  void _reviewAndUseTemplate(String vendorId, String inquiryId,',
           '  Future<void> _venueSearchSheet('), r"""  void _reviewAndUseTemplate(String vendorId, String inquiryId,
      Map<String, dynamic> inq, String tid, Map<String, dynamic> t) {
    final String body = (t['body'] ?? '') as String;
    final List<String> notes = t['notes'] is List
        ? (t['notes'] as List).map((dynamic e) => e.toString()).toList()
        : <String>[];
    bool busy = false;
    String err = '';
    _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 680),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setR) => _lzFrame(ctx2,
            icon: Icons.fact_check_rounded,
            title: (t['name'] ?? 'Template') as String,
            subtitle:
                'Read it through, then activate it to fill in this contract.',
            children: <Widget>[
              ..._pv2Notes(notes),
              _lzSection('The contract'),
              _pv2Doc(body),
              _pv2Err(err),
            ],
            footer: _lzActions(
                secondary: 'Not now',
                onSecondary: () => Navigator.pop(ctx2),
                primary: 'Activate and continue',
                icon: Icons.check_circle_rounded,
                busy: busy,
                onPrimary: () async {
                  setR(() {
                    busy = true;
                    err = '';
                  });
                  try {
                    await _setTemplateStatus(vendorId, tid, 'active');
                  } catch (_) {
                    if (ctx2.mounted) {
                      setR(() {
                        busy = false;
                        err =
                            'Couldn’t activate it. Check your connection and try again.';
                      });
                    }
                    return;
                  }
                  if (!ctx2.mounted) {
                    return;
                  }
                  Navigator.pop(ctx2);
                  _toast('Template activated.');
                  _contractValuesForm(vendorId, inquiryId, inq, tid, t);
                })),
      ),
    );
  }

""")

    # ------------------------------------------------------------------
    # _venueSearchSheet
    # ------------------------------------------------------------------
    rep(fn('  Future<void> _venueSearchSheet(TextEditingController target) async {',
           '  Future<void> _pickContractDate('), r"""  Future<void> _venueSearchSheet(TextEditingController target) async {
    final TextEditingController q =
        TextEditingController(text: target.text.split(',').first.trim());
    List<Map<String, String>> results = <Map<String, String>>[];
    bool busy = false;
    bool searched = false;
    String err = '';
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setV) {
          Future<void> run() async {
            if (busy || q.text.trim().length < 3) {
              return;
            }
            setV(() {
              busy = true;
              err = '';
            });
            try {
              final HttpsCallable fn = FirebaseFunctions.instance.httpsCallable(
                  'venueSearch',
                  options:
                      HttpsCallableOptions(timeout: const Duration(seconds: 20)));
              final HttpsCallableResult<dynamic> out =
                  await fn.call(<String, dynamic>{'query': q.text.trim()});
              final Map<String, dynamic> r =
                  Map<String, dynamic>.from(out.data as Map);
              results = <Map<String, String>>[];
              if (r['results'] is List) {
                for (final dynamic e in r['results'] as List) {
                  if (e is Map) {
                    results.add(<String, String>{
                      'name': (e['name'] ?? '').toString(),
                      'address': (e['address'] ?? '').toString(),
                    });
                  }
                }
              }
              searched = true;
            } catch (_) {
              err = 'Search failed - try again.';
            }
            if (ctx2.mounted) setV(() => busy = false);
          }

          final bool canSearch = !busy && q.text.trim().length >= 3;
          return _lzFrame(ctx2,
              icon: Icons.location_on_rounded,
              title: 'Find the venue',
              subtitle: 'Tap a result to fill in the name and address.',
              headerExtra: Row(children: <Widget>[
                Expanded(
                  child: TextField(
                    controller: q,
                    autofocus: true,
                    textInputAction: TextInputAction.search,
                    textCapitalization: TextCapitalization.words,
                    onChanged: (String _) => setV(() {}),
                    onSubmitted: (String _) => run(),
                    style: TextStyle(fontSize: 14.5, color: _lzFg(ink)),
                    decoration: _epDeco('Venue', 'Venue name or city…'),
                  ),
                ),
                const SizedBox(width: 8),
                FilledButton(
                  style: FilledButton.styleFrom(
                      backgroundColor: gold,
                      foregroundColor: plumDeep,
                      disabledBackgroundColor: gold.withOpacity(.45),
                      disabledForegroundColor: plumDeep.withOpacity(.7),
                      minimumSize: const Size(0, 46),
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(13))),
                  onPressed: canSearch ? _h(run) : null,
                  child: busy
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(
                              strokeWidth: 2, color: plumDeep))
                      : const Text('Search',
                          style: TextStyle(fontWeight: FontWeight.w700)),
                ),
              ]),
              children: <Widget>[
                const SizedBox(height: 14),
                if (busy)
                  _lzBusy('Searching venues…')
                else if (results.isNotEmpty)
                  ...results.map((Map<String, String> v) => _pv2Row(
                        icon: Icons.location_on_rounded,
                        title: v['name'] ?? '',
                        sub: v['address'] ?? '',
                        trailing: Icon(Icons.add_circle_outline_rounded,
                            color: _lzFg(plum), size: 20),
                        onTap: () {
                          target.text = '${v['name']}, ${v['address']}';
                          Navigator.pop(ctx);
                        },
                      ))
                else
                  _pv2Empty(
                      searched
                          ? Icons.search_off_rounded
                          : Icons.travel_explore_rounded,
                      searched
                          ? 'No venues found. Try the venue name and city.'
                          : 'Search by venue name, then tap the right one.'),
                _pv2Err(err),
              ]);
        },
      ),
    );
  }

""")

    # ------------------------------------------------------------------
    # _contractValuesForm: veil copy, then the sheet itself (from
    # `bool generating` to the end). Prefill, fields, values and the
    # generateContract call are carried over unchanged.
    # ------------------------------------------------------------------
    rep("""        'Names, dates, venue, and pricing — pulled from everything the thread already knows.');""",
        r"""        'Names, dates, venue and pricing - pulled from everything the thread already knows.');""")
    rep(fn('  Future<void> _contractValuesForm(', '  Future<void> _sendForSignature(',
           inner='    bool generating = false;\n'), r"""    bool generating = false;
    String genErr = '';
    _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 760),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setSheet) {
          final int remaining = cs.values
              .where((TextEditingController c2) => c2.text.trim().isEmpty)
              .length;
          final bool ready = remaining == 0;
          return Padding(
            padding:
                EdgeInsets.only(bottom: MediaQuery.of(ctx2).viewInsets.bottom),
            child: SizedBox(
              height: MediaQuery.of(ctx2).size.height * .86,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: <Widget>[
                  _pv2Head(ctx2, Icons.history_edu_rounded,
                      (t['name'] ?? 'Contract') as String,
                      subtitle:
                          'June filled in what she knows. Every field appears in the contract, so none can be blank.'),
                  _pv2Divider(),
                  Expanded(
                    child: SingleChildScrollView(
                      padding: const EdgeInsets.fromLTRB(22, 4, 22, 22),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: <Widget>[
                          if (showPkgPicker) ...<Widget>[
                            _lzSection('Fill from a package'),
                            Wrap(
                              spacing: 8,
                              runSpacing: 8,
                              children: vendorPackages
                                  .map((Map<String, dynamic> p) => ActionChip(
                                        backgroundColor: _lzBg(
                                            Colors.white.withOpacity(.85)),
                                        side: BorderSide(
                                            color: gold.withOpacity(.7)),
                                        avatar: Icon(Icons.inventory_2_outlined,
                                            size: 15, color: _lzFg(plum)),
                                        label: Text((p['name'] ?? '') as String,
                                            style: TextStyle(
                                                fontSize: 12.5,
                                                fontWeight: FontWeight.w600,
                                                color: _lzFg(plum))),
                                        onPressed: _h(() {
                                          final String nm =
                                              (p['name'] ?? '') as String;
                                          final String pr =
                                              (p['price'] ?? '') as String;
                                          final String hrs =
                                              (p['hours'] ?? '') as String;
                                          final String inc =
                                              (p['includes'] ?? '') as String;
                                          if (cs.containsKey('package_name') &&
                                              nm.isNotEmpty) {
                                            cs['package_name']!.text = nm;
                                          }
                                          if (cs.containsKey('total_price') &&
                                              pr.isNotEmpty) {
                                            cs['total_price']!.text =
                                                _fmtMoney(pr);
                                          }
                                          if (cs.containsKey(
                                                  'coverage_hours') &&
                                              hrs.isNotEmpty) {
                                            cs['coverage_hours']!.text = hrs;
                                          }
                                          if (cs.containsKey(
                                                  'package_description') &&
                                              inc.isNotEmpty) {
                                            cs['package_description']!.text =
                                                inc;
                                          }
                                          setSheet(() {});
                                        }),
                                      ))
                                  .toList(),
                            ),
                          ],
                          _lzSection('Contract details',
                              trailing: ready
                                  ? 'All filled in'
                                  : '$remaining to fill'),
                          LayoutBuilder(
                              builder: (BuildContext lc, BoxConstraints lb) {
                            final bool two = lb.maxWidth >= 560;
                            return Wrap(
                              spacing: 12,
                              runSpacing: 12,
                              children: fields.map((String f) {
                                final bool isDate = f.endsWith('_date');
                                final bool wide = f == '__venue' ||
                                    f.contains('description') ||
                                    f.contains('includes') ||
                                    f.contains('address') ||
                                    f.contains('notes');
                                final bool money = f.contains('price') ||
                                    f.contains('amount') ||
                                    f.contains('fee');
                                return SizedBox(
                                  width: (two && !wide)
                                      ? (lb.maxWidth - 12) / 2
                                      : lb.maxWidth,
                                  child: TextField(
                                    controller: cs[f],
                                    readOnly: isDate,
                                    minLines: wide && !isDate ? 4 : 1,
                                    maxLines: wide && !isDate ? 10 : 1,
                                    keyboardType: wide && !isDate
                                        ? TextInputType.multiline
                                        : TextInputType.text,
                                    textCapitalization:
                                        TextCapitalization.sentences,
                                    onChanged: (String _) => setSheet(() {}),
                                    onTap: isDate
                                        ? () async {
                                            await _pickContractDate(cs[f]!);
                                            setSheet(() {});
                                          }
                                        : null,
                                    style: TextStyle(
                                        fontSize: 13.5, color: _lzFg(ink)),
                                    decoration: InputDecoration(
                                      labelText: _fieldLabel(f),
                                      alignLabelWithHint: wide,
                                      helperText: (f.contains('description') ||
                                              f.contains('includes'))
                                          ? 'One item per line - they appear as a list in the contract'
                                          : null,
                                      helperStyle: TextStyle(
                                          fontSize: 10.5, color: _lzFg(muted)),
                                      helperMaxLines: 2,
                                      prefixText: money ? '\$ ' : null,
                                      prefixStyle: TextStyle(
                                          color: _lzFg(plum),
                                          fontSize: 13.5,
                                          fontWeight: FontWeight.w700),
                                      hintText: f == '__venue'
                                          ? 'The Wrigley Mansion, 2501 E Telawa Trl, Phoenix, AZ'
                                          : (f.contains('description') ||
                                                  f.contains('includes'))
                                              ? '8 hours of coverage\nTwo photographers\n300+ edited images\nOnline gallery\nPrint release'
                                              : null,
                                      hintStyle: const TextStyle(
                                          fontSize: 11.5,
                                          color: Color(0xFFB9AEC0)),
                                      labelStyle: TextStyle(
                                          fontSize: 12, color: _lzFg(muted)),
                                      floatingLabelStyle: TextStyle(
                                          fontSize: 12.5,
                                          color: _lzFg(plum),
                                          fontWeight: FontWeight.w700),
                                      isDense: true,
                                      filled: true,
                                      fillColor: _lzBg(Colors.white),
                                      suffixIcon: isDate
                                          ? Icon(Icons.calendar_month_rounded,
                                              color: _lzFg(plum), size: 18)
                                          : f == '__venue'
                                              ? IconButton(
                                                  tooltip: 'Search venues',
                                                  icon: Icon(
                                                      Icons.search_rounded,
                                                      color: _lzFg(plum),
                                                      size: 19),
                                                  onPressed: _h(() async {
                                                    await _venueSearchSheet(
                                                        cs[f]!);
                                                    setSheet(() {});
                                                  }),
                                                )
                                              : null,
                                      border: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(12),
                                        borderSide: BorderSide(
                                            color: gold.withOpacity(.6)),
                                      ),
                                      enabledBorder: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(12),
                                        borderSide: BorderSide(
                                            color: cs[f]!.text.trim().isEmpty
                                                ? gold
                                                : _lzLine(
                                                    gold.withOpacity(.5))),
                                      ),
                                      focusedBorder: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(12),
                                        borderSide: const BorderSide(
                                            color: gold, width: 1.7),
                                      ),
                                    ),
                                  ),
                                );
                              }).toList(),
                            );
                          }),
                        ],
                      ),
                    ),
                  ),
                  _pv2Foot(
                    ctx2,
                    Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: <Widget>[
                          if (genErr.isNotEmpty)
                            Padding(
                                padding: const EdgeInsets.only(bottom: 10),
                                child: _pv2Err(genErr)),
                          _lzActions(
                              secondary: 'Cancel',
                              onSecondary: () => Navigator.pop(ctx),
                              primary: generating
                                  ? 'Generating…'
                                  : ready
                                      ? 'Generate contract'
                                      : remaining == 1
                                          ? '1 field left'
                                          : '$remaining fields left',
                              icon: Icons.history_edu_rounded,
                              busy: generating,
                              onPrimary: !ready
                                  ? null
                                  : () async {
                                      setSheet(() {
                                        generating = true;
                                        genErr = '';
                                      });
                                      final Map<String, String> vals =
                                          <String, String>{};
                                      cs.forEach((String k,
                                          TextEditingController c2) {
                                        final String tv = c2.text.trim();
                                        if (tv.isEmpty) {
                                          return;
                                        }
                                        if (k == '__venue') {
                                          final int ci = tv.indexOf(',');
                                          if (ci > 0) {
                                            vals['venue_name'] =
                                                tv.substring(0, ci).trim();
                                            vals['venue_address'] =
                                                tv.substring(ci + 1).trim();
                                          } else {
                                            vals['venue_name'] = tv;
                                            vals['venue_address'] = tv;
                                          }
                                        } else {
                                          vals[k] = tv;
                                        }
                                      });
                                      try {
                                        final HttpsCallable fn =
                                            FirebaseFunctions.instance
                                                .httpsCallable(
                                                    'generateContract',
                                                    options:
                                                        HttpsCallableOptions(
                                                            timeout:
                                                                const Duration(
                                                                    seconds:
                                                                        120)));
                                        final HttpsCallableResult<dynamic>
                                            out =
                                            await fn.call(<String, dynamic>{
                                          'vendorId': vendorId,
                                          'inquiryId': inquiryId,
                                          'templateId': templateId,
                                          'values': vals,
                                        });
                                        final Map<String, dynamic> r =
                                            Map<String, dynamic>.from(
                                                out.data as Map);
                                        if (!ctx2.mounted) {
                                          return;
                                        }
                                        Navigator.pop(ctx);
                                        _contractDraftedSheet(
                                            vendorId, inquiryId, r);
                                      } on FirebaseFunctionsException catch (e) {
                                        if (ctx2.mounted) {
                                          setSheet(() {
                                            generating = false;
                                            genErr = e.message ??
                                                'Could not generate - try again.';
                                          });
                                        }
                                      } catch (_) {
                                        if (ctx2.mounted) {
                                          setSheet(() {
                                            generating = false;
                                            genErr =
                                                'Could not generate - try again.';
                                          });
                                        }
                                      }
                                    }),
                        ]),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

""")

    # ------------------------------------------------------------------
    # _sendForSignature
    # ------------------------------------------------------------------
    rep(fn('  Future<void> _sendForSignature(',
           '  void _contractDraftedSheet('), r"""  Future<void> _sendForSignature(
      String vendorId, String inquiryId, String contractId) async {
    if (contractId.isEmpty) {
      return;
    }
    final bool go = await _lzConfirm(
        'Send for signature?',
        'The couple gets it in their thread and by email, and signs electronically. It shows as signed here the moment they do.',
        confirm: 'Send for signature',
        cancel: 'Not yet',
        icon: Icons.send_rounded);
    if (go != true) {
      return;
    }
    _toast('Sending for signature…');
    try {
      final HttpsCallable fn = FirebaseFunctions.instance.httpsCallable(
          'sendContractForSignature',
          options: HttpsCallableOptions(timeout: const Duration(seconds: 120)));
      await fn.call(<String, dynamic>{
        'vendorId': vendorId,
        'inquiryId': inquiryId,
        'contractId': contractId,
      });
      _toast('Sent. The couple can now review and sign.');
    } on FirebaseFunctionsException catch (e) {
      _toast(e.message ?? 'Could not send - try again.');
    } catch (_) {
      _toast('Could not send - try again.');
    }
  }

""")
    return s
