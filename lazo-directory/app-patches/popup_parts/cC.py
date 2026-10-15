# Popup pass (JC-LAZO-POPUP-1014), part cC: couple dashboard.
# Thread menu, block/report/went-elsewhere, thread chrome, questionnaire,
# June's contract read, review, timeline moment, chapters, site-live share,
# contracts vault, proposal accept, message edit, emoji copy, dream-board
# link/note/swatch/comments, shopping item.


def apply(s: str) -> str:
    def rep(old, new):
        nonlocal s
        assert s.count(old) == 1, (s.count(old), old[:80])
        s = s.replace(old, new)

    def span(start, end, new):
        # Replaces the text from `start` (unique) up to, not including, the
        # first `end` after it - i.e. one whole function in the base.
        nonlocal s
        assert s.count(start) == 1, (s.count(start), start[:80])
        i = s.index(start)
        j = s.index(end, i)
        assert j - i < 40000, (start[:60], j - i)
        old = s[i:j]
        assert s.count(old) == 1, start[:80]
        s = s[:i] + new + s[j:]

    # ------------------------------------------------------------ _threadMenu
    span("  Future<void> _threadMenu(BuildContext threadCtx, String inquiryId,",
         "  // Blocking is reversible on purpose",
         r"""  Future<void> _threadMenu(BuildContext threadCtx, String inquiryId,
      Map<String, dynamic> inq) async {
    final String vn = (inq['vendorName'] ?? 'this vendor').toString();
    final String status = (inq['status'] ?? '').toString();
    final bool blocked = (inq['blockedByCouple'] ?? false) == true;

    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 520),
      builder: (BuildContext ctx) => _lzFrame(ctx,
          icon: Icons.forum_outlined,
          title: vn,
          subtitle: 'Conversation options',
          children: <Widget>[
            const SizedBox(height: 14),
            if (status != 'booked' && status != 'lost')
              _pcC_opt(Icons.waving_hand_rounded, 'We went another direction',
                  'Let them know kindly, in one tap', () {
                Navigator.pop(ctx);
                _wentElsewhereSheet(threadCtx, inquiryId, inq);
              }),
            _pcC_opt(
                blocked ? Icons.lock_open_rounded : Icons.block_rounded,
                blocked ? 'Unblock $vn' : 'Block $vn',
                blocked
                    ? 'They can message you again'
                    : 'They can\u2019t message you, and they leave your search',
                () {
              Navigator.pop(ctx);
              _confirmBlock(threadCtx, inquiryId, inq, blocked);
            }, danger: !blocked),
            _pcC_opt(Icons.flag_rounded, 'Report this vendor',
                'Tell the Lazo team what happened', () {
              Navigator.pop(ctx);
              _reportSheet(threadCtx, inquiryId, inq);
            }, danger: true),
          ]),
    );
  }

  // ---- popup pass cC: small pieces shared by the popups in this part ----
  static const Color _pcC_red = Color(0xFFB3413A);

  // One option in a menu sheet: icon tile, title, one line, chevron.
  Widget _pcC_opt(IconData icon, String title, String sub, VoidCallback onTap,
      {bool danger = false}) {
    final Color tone = danger ? _pcC_red : plum;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: _Press(
        scale: .985,
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.fromLTRB(14, 13, 10, 13),
          decoration: BoxDecoration(
              color: _lzBg(cardBg),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                  color: danger
                      ? _pcC_red.withOpacity(.35)
                      : _lzLine(goldLine))),
          child: Row(children: <Widget>[
            Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                    color: tone.withOpacity(.1),
                    borderRadius: BorderRadius.circular(12)),
                child: Icon(icon, color: _lzFg(tone), size: 19)),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(title,
                        style: TextStyle(
                            fontSize: 14.5,
                            fontWeight: FontWeight.w700,
                            color: _lzFg(danger ? _pcC_red : ink))),
                    const SizedBox(height: 2),
                    Text(sub,
                        style: TextStyle(
                            fontSize: 12.5, color: _lzFg(muted), height: 1.35)),
                  ]),
            ),
            Icon(Icons.chevron_right_rounded, color: _lzFg(muted), size: 20),
          ]),
        ),
      ),
    );
  }

  // A failure shown inside the popup, under the thing that failed.
  Widget _pcC_err(String err) => err.isEmpty
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

  // An empty list inside a popup: an icon and one line.
  Widget _pcC_empty(IconData icon, String line) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 8),
        child: Column(children: <Widget>[
          Container(
              width: 52,
              height: 52,
              decoration: BoxDecoration(
                  color: _lzBg(const Color(0xFFF6EEDF)),
                  shape: BoxShape.circle),
              child: Icon(icon, color: _lzFg(plum), size: 24)),
          const SizedBox(height: 12),
          Text(line,
              textAlign: TextAlign.center,
              style: TextStyle(
                  fontSize: 14, color: _lzFg(muted), height: 1.45)),
        ]),
      );

  // A field-shaped row that opens a picker (time, date).
  Widget _pcC_pickRow(
          IconData icon, String label, String value, VoidCallback onTap) =>
      _Press(
        scale: .985,
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
          decoration: BoxDecoration(
              color: _lzBg(Colors.white),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: _lzLine(gold), width: 1.2)),
          child: Row(children: <Widget>[
            Icon(icon, size: 19, color: _lzFg(plum)),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(label,
                        style: TextStyle(
                            fontSize: 12,
                            color: _lzFg(plum),
                            fontWeight: FontWeight.w700)),
                    const SizedBox(height: 2),
                    Text(value,
                        style: TextStyle(
                            fontSize: 15,
                            color: _lzFg(ink),
                            fontWeight: FontWeight.w600)),
                  ]),
            ),
            Text('Change',
                style: TextStyle(
                    fontSize: 12.5,
                    color: _lzFg(plum),
                    fontWeight: FontWeight.w700)),
          ]),
        ),
      );

  // How far through a list of questions they are.
  Widget _pcC_progress(int done, int total) => Row(children: <Widget>[
        Expanded(
          child: ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
                value: total == 0 ? 0 : done / total,
                minHeight: 5,
                color: gold,
                backgroundColor: _lzLine(goldLine).withOpacity(.5)),
          ),
        ),
        const SizedBox(width: 12),
        Text('$done of $total answered',
            style: TextStyle(
                fontSize: 12.5,
                color: _lzFg(muted),
                fontWeight: FontWeight.w600)),
      ]);

  // One numbered question and its answer field.
  Widget _pcC_question(int i, String q, TextEditingController c,
          {bool autofocus = false, ValueChanged<String>? onChanged}) =>
      Padding(
        padding: const EdgeInsets.only(bottom: 18),
        child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              Row(
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
                                fontSize: 12,
                                fontWeight: FontWeight.w800))),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Padding(
                        padding: const EdgeInsets.only(top: 2),
                        child: Text(q,
                            style: TextStyle(
                                color: _lzFg(plum),
                                fontSize: 14,
                                fontWeight: FontWeight.w700,
                                height: 1.4)),
                      ),
                    ),
                  ]),
              const SizedBox(height: 8),
              TextField(
                controller: c,
                autofocus: autofocus,
                minLines: 1,
                maxLines: 5,
                textCapitalization: TextCapitalization.sentences,
                onChanged: onChanged,
                style: TextStyle(fontSize: 14.5, color: _lzFg(ink)),
                decoration: _lightDeco('', hint: 'Your answer'),
              ),
            ]),
      );

  // A reason chip (report, went elsewhere).
  Widget _pcC_reason(String label, bool on, Color tone, VoidCallback go) =>
      ChoiceChip(
        label: Text(label,
            style: TextStyle(
                fontSize: 13,
                color: on ? ivory : _lzFg(plum),
                fontWeight: FontWeight.w600)),
        selected: on,
        selectedColor: tone,
        checkmarkColor: ivory,
        backgroundColor: _lzBg(Colors.white),
        side: BorderSide(color: on ? tone : _lzLine(goldLine)),
        onSelected: _hb((_) => go()),
      );

""")

    # ----------------------------------------------------------- _confirmBlock
    span("  Future<void> _confirmBlock(BuildContext threadCtx, String inquiryId,",
         "  // Reporting queues the case for the Lazo team",
         r"""  Future<void> _confirmBlock(BuildContext threadCtx, String inquiryId,
      Map<String, dynamic> inq, bool currentlyBlocked) async {
    final String vn = (inq['vendorName'] ?? 'this vendor').toString();
    final bool unblocking = currentlyBlocked;
    final bool sure = await _lzConfirm(
        unblocking ? 'Unblock $vn?' : 'Block $vn?',
        unblocking
            ? 'They can reply in this conversation again, and they show up in your search.'
            : 'They can\u2019t message you again. The conversation leaves your inbox and they leave your search. You can undo this any time.',
        confirm: unblocking ? 'Unblock' : 'Block vendor',
        cancel: 'Cancel',
        danger: !unblocking,
        icon: unblocking ? Icons.lock_open_rounded : Icons.block_rounded);
    if (!sure) return;

    try {
      await FirebaseFunctions.instance
          .httpsCallable('blockVendor')
          .call(<String, dynamic>{
        'inquiryId': inquiryId,
        'blocked': !unblocking,
      });
    } on FirebaseFunctionsException catch (e) {
      _toast(e.message ?? 'Could not update that just now.');
      return;
    } catch (_) {
      _toast('Could not update that just now.');
      return;
    }

    if (!mounted) return;
    if (unblocking) {
      _toast('$vn is unblocked.');
      return;
    }
    // Close the thread: it has just left the inbox, so leaving it open would
    // show a conversation that is no longer in the list behind it.
    if (Navigator.of(threadCtx).canPop()) Navigator.pop(threadCtx);
    _toast('$vn is blocked. They cannot message you again.');
  }

""")

    # ------------------------------------------------------------ _reportSheet
    span("  Future<void> _reportSheet(BuildContext threadCtx, String inquiryId,",
         "  // Blocked conversations are kept, never deleted",
         r"""  Future<void> _reportSheet(BuildContext threadCtx, String inquiryId,
      Map<String, dynamic> inq) async {
    final String vn = (inq['vendorName'] ?? 'this vendor').toString();
    String reason = '';
    final TextEditingController detailC = TextEditingController();
    bool busy = false;
    bool open = true;
    String err = '';

    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext ctx) => StatefulBuilder(
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
              await FirebaseFunctions.instance
                  .httpsCallable('reportVendor')
                  .call(<String, dynamic>{
                'inquiryId': inquiryId,
                'reason': reason,
                'detail': detailC.text.trim(),
              });
            } catch (_) {
              up(() {
                busy = false;
                err =
                    'Could not send that just now. Check your connection and try again.';
              });
              return;
            }
            if (!mounted) return;
            if (ctx2.mounted) Navigator.pop(ctx2);
            if (Navigator.of(threadCtx).canPop()) {
              Navigator.pop(threadCtx);
            }
            _toast(
                'Thank you. We have blocked them and our team is looking into it.');
          }

          return _lzFrame(ctx2,
              icon: Icons.flag_rounded,
              title: 'Report $vn',
              subtitle: 'A real person on the Lazo team reads every report.',
              children: <Widget>[
                const SizedBox(height: 14),
                _lzNote(Icons.shield_outlined,
                    'They are blocked straight away. The conversation is kept so we can see what happened.'),
                _lzSection('What happened'),
                Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                  for (final List<String> o in const <List<String>>[
                    <String>['harassment', 'Harassment'],
                    <String>['inappropriate', 'Inappropriate'],
                    <String>['spam', 'Spam or pressure'],
                    <String>['scam', 'Scam or fraud'],
                    <String>['noshow', 'Took money and vanished'],
                    <String>['other', 'Something else'],
                  ])
                    _pcC_reason(o[1], reason == o[0], _pcC_red,
                        () => up(() => reason = o[0])),
                ]),
                const SizedBox(height: 16),
                TextField(
                  controller: detailC,
                  minLines: 3,
                  maxLines: 6,
                  textCapitalization: TextCapitalization.sentences,
                  style: TextStyle(color: _lzFg(ink), fontSize: 14),
                  decoration: _lightDeco('Details (optional)',
                      hint: 'Anything that helps us act faster'),
                ),
                _pcC_err(err),
                const SizedBox(height: 12),
                Text(
                    'If you are in immediate danger, contact your local emergency services first.',
                    style: TextStyle(
                        fontSize: 12, color: _lzFg(muted), height: 1.4)),
              ],
              footer: _lzActions(
                  secondary: 'Cancel',
                  onSecondary: () => Navigator.pop(ctx2),
                  primary: 'Send report',
                  icon: Icons.flag_rounded,
                  danger: true,
                  busy: busy,
                  onPrimary: reason.isEmpty ? null : send));
        },
      ),
    ).whenComplete(() => open = false);
  }

""")

    # ------------------------------------------------------ _wentElsewhereSheet
    span("  Future<void> _wentElsewhereSheet(BuildContext threadCtx, String inquiryId,",
         "  void _openCoupleThread(String inquiryId, Map<String, dynamic> inq) {",
         r"""  Future<void> _wentElsewhereSheet(BuildContext threadCtx, String inquiryId,
      Map<String, dynamic> inq) async {
    final String vn = (inq['vendorName'] ?? 'this vendor').toString();
    String reason = '';
    final TextEditingController noteC = TextEditingController();
    bool busy = false;
    bool open = true;
    String err = '';
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext ctx) => StatefulBuilder(
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
              await FirebaseFirestore.instance
                  .collection('inquiries')
                  .doc(inquiryId)
                  .set(<String, dynamic>{
                'status': 'lost',
                'lostReason': reason,
                'lostNote': noteC.text.trim(),
                'lostAt': FieldValue.serverTimestamp(),
              }, SetOptions(merge: true));
              final String note = noteC.text.trim();
              await FirebaseFirestore.instance
                  .collection('inquiries')
                  .doc(inquiryId)
                  .collection('messages')
                  .add(<String, dynamic>{
                'senderRole': 'couple',
                'text': note.isEmpty
                    ? 'Thank you so much for your time - we\u2019ve decided to go another direction. We really appreciated talking with you.'
                    : note,
                'at': FieldValue.serverTimestamp(),
                'system': 'lost',
              });
              if (ctx2.mounted) Navigator.pop(ctx2);
              if (threadCtx.mounted) Navigator.pop(threadCtx);
              _toast('Told $vn. That was kind.');
            } catch (e) {
              up(() {
                busy = false;
                err = 'Could not send that just now. Try again in a moment.';
              });
            }
          }

          return _lzFrame(ctx2,
              icon: Icons.waving_hand_rounded,
              title: 'Going another direction?',
              subtitle:
                  'Tell $vn why, in one tap. They\u2019d rather know than wonder.',
              children: <Widget>[
                _lzSection('The main reason'),
                Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                  for (final List<String> o in const <List<String>>[
                    <String>['price', 'Price'],
                    <String>['date', 'Date didn\u2019t work'],
                    <String>['style', 'Not our style'],
                    <String>['booked elsewhere', 'Booked someone else'],
                    <String>['changed plans', 'Plans changed'],
                    <String>['other', 'Something else'],
                  ])
                    _pcC_reason(o[1], reason == o[0], plum,
                        () => up(() => reason = o[0])),
                ]),
                const SizedBox(height: 16),
                TextField(
                  controller: noteC,
                  minLines: 2,
                  maxLines: 4,
                  textCapitalization: TextCapitalization.sentences,
                  style: TextStyle(color: _lzFg(ink), fontSize: 14),
                  decoration: _lightDeco('A line for them (optional)'),
                ),
                const SizedBox(height: 12),
                _lzNote(Icons.favorite_border_rounded,
                    'Leave it blank and we send a short, kind thank-you for you.'),
                _pcC_err(err),
              ],
              footer: _lzActions(
                  secondary: 'Cancel',
                  onSecondary: () => Navigator.pop(ctx2),
                  primary: 'Let them know',
                  icon: Icons.send_rounded,
                  busy: busy,
                  onPrimary: reason.isEmpty ? null : send));
        },
      ),
    ).whenComplete(() => open = false);
  }

""")

    # ------------------------------------------------------- _openCoupleThread
    # Chrome only: on a wide screen _lzSheet already centres the thread as a
    # card, so the card is drawn at the card's width with round corners at
    # every wide size (it used to switch at 900, leaving 760-900 as a
    # top-rounded sheet floating in a dialog), and the old full-screen tap
    # catcher is gone (the dialog barrier closes it).
    span("  void _openCoupleThread(String inquiryId, Map<String, dynamic> inq) {",
         "  // The thread itself: header, messages",
         r"""  void _openCoupleThread(String inquiryId, Map<String, dynamic> inq) {
    _openThreadId = inquiryId;
    _stampPresence(inquiryId, 'coupleActiveAt');
    _presenceTimer?.cancel();
    _presenceTimer = Timer.periodic(const Duration(seconds: 45),
        (_) => _stampPresence(inquiryId, 'coupleActiveAt'));
    // Read receipt: she has seen everything up to now
    FirebaseFirestore.instance
        .collection('inquiries')
        .doc(inquiryId)
        .set(<String, dynamic>{
      'coupleLastReadAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
    final TextEditingController c = TextEditingController();
    final String vn = (inq['vendorName'] ?? 'Vendor') as String;
    bool sending = false;
    _lzSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      constraints: const BoxConstraints(maxWidth: 760),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setSheet) {
          // v112: on a desktop the thread is a card over the dashboard, not a
          // sheet that paints the whole screen ivory. Phones keep the sheet.
          final Size scr = MediaQuery.of(ctx2).size;
          final double kb = MediaQuery.of(ctx2).viewInsets.bottom;
          final bool wideT = scr.width >= _lzWideAt;
          final double sheetH =
              wideT ? (scr.height - kb) * .84 : scr.height * .92;
          final Widget card = Container(
            constraints:
                BoxConstraints(maxWidth: wideT ? 760 : double.infinity),
            height: sheetH,
            clipBehavior: Clip.antiAlias,
            decoration: BoxDecoration(
              color: _lzBg(ivory),
              borderRadius: wideT
                  ? BorderRadius.circular(24)
                  : const BorderRadius.vertical(top: Radius.circular(26)),
              border: wideT ? Border.all(color: _lzLine(goldLine)) : null,
              boxShadow: wideT
                  ? <BoxShadow>[
                      BoxShadow(
                          color: Colors.black.withOpacity(.35),
                          blurRadius: 40,
                          offset: const Offset(0, 16))
                    ]
                  : null,
            ),
            child: _threadBody(ctx2, setSheet, inquiryId, inq, vn, c,
                () => sending, (bool v) => sending = v),
          );
          if (wideT) return card;
          return Padding(
            padding: EdgeInsets.only(bottom: kb),
            child: card,
          );
        },
      ),
    ).whenComplete(() {
      _presenceTimer?.cancel();
      _presenceTimer = null;
      _openThreadId = '';
    });
  }

""")

    # ------------------------------------------------------ _fillQuestionnaire
    span("  void _fillQuestionnaire(",
         "  Widget _coupleContracts(String inquiryId, String vendorName) {",
         r"""  void _fillQuestionnaire(
      String inquiryId, String qId, Map<String, dynamic> qn) {
    final List<dynamic> questions = qn['questions'] is List
        ? qn['questions'] as List<dynamic>
        : <dynamic>[];
    final Map<String, dynamic> prior = qn['answers'] is Map
        ? Map<String, dynamic>.from(qn['answers'] as Map)
        : <String, dynamic>{};
    final List<TextEditingController> cs = List<TextEditingController>.generate(
        questions.length,
        (int i) => TextEditingController(text: (prior['$i'] ?? '').toString()));
    final String from = (qn['vendorName'] ?? '').toString();
    bool saving = false;
    bool open = true;
    String err = '';
    _lzSheet(
      context: context,
      constraints: const BoxConstraints(maxWidth: 640),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setQ) {
          void up(VoidCallback f) {
            if (open) setQ(f);
          }

          final int answered = cs
              .where((TextEditingController t) => t.text.trim().isNotEmpty)
              .length;

          Future<void> send() async {
            up(() {
              saving = true;
              err = '';
            });
            final Map<String, String> ans = <String, String>{};
            for (int i = 0; i < cs.length; i++) {
              if (cs[i].text.trim().isNotEmpty) {
                ans['$i'] = cs[i].text.trim();
              }
            }
            try {
              await FirebaseFirestore.instance
                  .collection('inquiries')
                  .doc(inquiryId)
                  .collection('questionnaires')
                  .doc(qId)
                  .update(<String, dynamic>{
                'answers': ans,
                'status': 'completed',
                'completedAt': FieldValue.serverTimestamp(),
              });
              await FirebaseFirestore.instance
                  .collection('inquiries')
                  .doc(inquiryId)
                  .set(<String, dynamic>{
                'questionnaireStatus': 'completed',
                'questionnaireUpdatedAt': FieldValue.serverTimestamp(),
              }, SetOptions(merge: true));
              if (ctx2.mounted) {
                Navigator.pop(ctx);
              }
              _toastC('Sent. Your vendor has your answers.');
            } catch (_) {
              up(() {
                saving = false;
                err =
                    'Could not send your answers. Check your connection and try again.';
              });
            }
          }

          return _lzFrame(ctx2,
              icon: Icons.fact_check_outlined,
              title: (qn['title'] ?? 'Questionnaire').toString(),
              subtitle: from.isEmpty
                  ? 'Answer what you can - you can message about the rest.'
                  : 'From $from. Answer what you can - you can message about the rest.',
              headerExtra: questions.isEmpty
                  ? null
                  : _pcC_progress(answered, questions.length),
              children: <Widget>[
                const SizedBox(height: 16),
                if (questions.isEmpty)
                  _pcC_empty(Icons.fact_check_outlined,
                      'There are no questions in this one yet.')
                else
                  for (int i = 0; i < questions.length; i++)
                    _pcC_question(i, questions[i].toString(), cs[i],
                        autofocus: i == 0 && cs[0].text.isEmpty,
                        onChanged: (_) => up(() {})),
                _pcC_err(err),
              ],
              footer: _lzActions(
                  secondary: 'Later',
                  onSecondary: () => Navigator.pop(ctx2),
                  primary: 'Send answers',
                  icon: Icons.send_rounded,
                  busy: saving,
                  onPrimary: send));
        },
      ),
    ).whenComplete(() => open = false);
  }

""")

    # ----------------------------------------------------- _juneReviewContract
    # The read used to start inside the builder, so any rebuild of the sheet
    # (keyboard, rotation) asked June again. It starts once now; "Try again"
    # restarts it after a failure.
    span("  Future<void> _juneReviewContract(",
         "  static const String _kInvoicePdfBase =",
         r"""  Future<void> _juneReviewContract(
      String inquiryId, String contractId, String tName) async {
    Future<HttpsCallableResult<dynamic>> read() => FirebaseFunctions.instance
            .httpsCallable('reviewContractForCouple',
                options: HttpsCallableOptions(
                    timeout: const Duration(seconds: 120)))
            .call(<String, dynamic>{
          'inquiryId': inquiryId,
          'contractId': contractId,
        });
    Future<HttpsCallableResult<dynamic>> fut = read();
    _lzSheet(
      context: context,
      constraints: const BoxConstraints(maxWidth: 680),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setR) =>
            FutureBuilder<HttpsCallableResult<dynamic>>(
          future: fut,
          builder: (BuildContext c2,
              AsyncSnapshot<HttpsCallableResult<dynamic>> snap) {
            final bool loading = snap.connectionState != ConnectionState.done;
            bool bad = !loading && (snap.hasError || snap.data == null);
            Map<String, dynamic> r = <String, dynamic>{};
            if (!loading && !bad) {
              try {
                final Map<String, dynamic> out =
                    Map<String, dynamic>.from(snap.data!.data as Map);
                r = Map<String, dynamic>.from(out['review'] as Map);
              } catch (_) {
                bad = true;
              }
            }
            final List<dynamic> terms = (r['keyTerms'] as List?) ?? <dynamic>[];
            final List<dynamic> flags = (r['flags'] as List?) ?? <dynamic>[];
            final List<dynamic> qs = (r['questions'] as List?) ?? <dynamic>[];
            final List<Widget> body = <Widget>[const SizedBox(height: 16)];
            if (loading) {
              body.add(_lzBusy(
                  'June is reading every clause. It takes about fifteen seconds.'));
            } else if (bad) {
              body.add(_pcC_err(
                  'June couldn\u2019t finish the read. Give it another try in a moment.'));
            } else {
              final String summary = (r['summary'] ?? '').toString();
              if (summary.isNotEmpty) {
                body.add(Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                      color: _lzBg(cardBg),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: _lzLine(goldLine))),
                  child: Text(summary,
                      style: TextStyle(
                          color: _lzFg(ink), fontSize: 14.5, height: 1.55)),
                ));
              }
              if (terms.isNotEmpty) {
                body.add(_lzSection('Key terms'));
                body.add(Container(
                  decoration: BoxDecoration(
                      color: _lzBg(Colors.white),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: _lzLine(goldLine))),
                  child: Column(children: <Widget>[
                    for (int i = 0; i < terms.length; i++)
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 14, vertical: 11),
                        decoration: BoxDecoration(
                            border: i == 0
                                ? null
                                : Border(
                                    top: BorderSide(
                                        color: _lzLine(goldLine)
                                            .withOpacity(.6)))),
                        child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              SizedBox(
                                width: 130,
                                child: Text(
                                    (terms[i] is Map
                                            ? (terms[i] as Map)['label'] ?? ''
                                            : '')
                                        .toString(),
                                    style: TextStyle(
                                        color: _lzFg(muted), fontSize: 13)),
                              ),
                              Expanded(
                                child: Text(
                                    (terms[i] is Map
                                            ? (terms[i] as Map)['value'] ?? ''
                                            : terms[i])
                                        .toString(),
                                    style: TextStyle(
                                        color: _lzFg(ink),
                                        fontSize: 13,
                                        fontWeight: FontWeight.w700,
                                        height: 1.4)),
                              ),
                            ]),
                      ),
                  ]),
                ));
              }
              if (flags.isNotEmpty) {
                body.add(_lzSection('Worth knowing'));
                for (final dynamic f in flags) {
                  final Map<String, dynamic> m = f is Map
                      ? Map<String, dynamic>.from(f)
                      : <String, dynamic>{'text': f.toString()};
                  final bool caution = (m['severity'] ?? 'note') == 'caution';
                  final Color tone =
                      caution ? _pcC_red : const Color(0xFF8A6A2F);
                  body.add(Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Container(
                      padding: const EdgeInsets.fromLTRB(12, 11, 14, 11),
                      decoration: BoxDecoration(
                          color: tone.withOpacity(.07),
                          borderRadius: BorderRadius.circular(13),
                          border: Border.all(color: tone.withOpacity(.3))),
                      child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Icon(
                                caution
                                    ? Icons.error_outline_rounded
                                    : Icons.info_outline_rounded,
                                size: 18,
                                color: _lzFg(tone)),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text((m['text'] ?? '').toString(),
                                  style: TextStyle(
                                      color: _lzFg(ink),
                                      fontSize: 13.5,
                                      height: 1.45)),
                            ),
                          ]),
                    ),
                  ));
                }
              }
              if (qs.isNotEmpty) {
                body.add(_lzSection('Questions you could ask',
                    trailing: 'Tap one to send it'));
                for (int qi = 0; qi < qs.length; qi++) {
                  final String q = qs[qi].toString();
                  final bool sent = _juneQSent.contains('$inquiryId-$qi');
                  body.add(Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: _Press(
                      onTap: sent
                          ? null
                          : () async {
                              try {
                                await FirebaseFirestore.instance
                                    .collection('inquiries')
                                    .doc(inquiryId)
                                    .collection('messages')
                                    .add(<String, dynamic>{
                                  'senderRole': 'couple',
                                  'text': q,
                                  'at': FieldValue.serverTimestamp(),
                                });
                                _juneQSent.add('$inquiryId-$qi');
                                if (ctx2.mounted) setR(() {});
                              } catch (err) {
                                _toastC(
                                    'Could not send that question. Try again.');
                              }
                            },
                      child: Container(
                        padding: const EdgeInsets.all(13),
                        decoration: BoxDecoration(
                          color: _lzBg(
                              sent ? vGreen.withOpacity(.10) : Colors.white),
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(
                              color: _lzLine(sent
                                  ? vGreen.withOpacity(.6)
                                  : gold.withOpacity(.55))),
                        ),
                        child: Row(children: <Widget>[
                          Expanded(
                            child: Text(q,
                                style: TextStyle(
                                    color: _lzFg(sent
                                        ? const Color(0xFF2E6B52)
                                        : ink),
                                    fontSize: 13.5,
                                    height: 1.4)),
                          ),
                          const SizedBox(width: 10),
                          sent
                              ? Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: <Widget>[
                                      Icon(Icons.check_circle_rounded,
                                          color: _lzFg(vGreen), size: 16),
                                      const SizedBox(width: 4),
                                      Text('Sent',
                                          style: TextStyle(
                                              color: _lzFg(vGreen),
                                              fontSize: 12,
                                              fontWeight: FontWeight.w800)),
                                    ])
                              : Icon(Icons.send_rounded,
                                  color: _lzFg(plum), size: 17),
                        ]),
                      ),
                    ),
                  ));
                }
              }
              body.add(const SizedBox(height: 14));
              body.add(_lzNote(Icons.info_outline_rounded,
                  'June helps you understand what you\u2019re signing. She\u2019s not a lawyer, and this isn\u2019t legal advice.'));
            }
            return _lzFrame(ctx2,
                icon: Icons.auto_awesome_rounded,
                title: loading ? 'June is reading' : 'June read it',
                subtitle: tName,
                children: body,
                footer: loading
                    ? null
                    : bad
                        ? _lzActions(
                            secondary: 'Close',
                            onSecondary: () => Navigator.pop(ctx2),
                            primary: 'Try again',
                            icon: Icons.refresh_rounded,
                            onPrimary: () => setR(() => fut = read()))
                        : _lzActions(
                            primary: 'Done',
                            icon: Icons.check_rounded,
                            onPrimary: () => Navigator.pop(ctx2)));
          },
        ),
      ),
    );
  }

""")

    # ------------------------------------------------------- _leaveReviewSheet
    span("  Future<void> _leaveReviewSheet(",
         "  // v140: money flows into the plan.",
         r"""  Future<void> _leaveReviewSheet(
      String inquiryId, Map<String, dynamic> inq, String vendorName) async {
    int rating = 5;
    final TextEditingController txt = TextEditingController();
    bool saving = false;
    bool open = true;
    String err = '';
    const List<String> words = <String>[
      '',
      'Poor',
      'Not great',
      'Good',
      'Great',
      'Wonderful'
    ];
    if (!mounted) return;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setR) {
          void up(VoidCallback f) {
            if (open) setR(f);
          }

          Future<void> post() async {
            up(() {
              saving = true;
              err = '';
            });
            try {
              await FirebaseFirestore.instance
                  .collection('reviews')
                  .add(<String, dynamic>{
                'vendorId': inq['vendorId'],
                'inquiryId': inquiryId,
                'coupleUid': inq['coupleUid'],
                'coupleName': inq['coupleName'] ?? '',
                'rating': rating,
                'text': txt.text.trim(),
                'status': 'published',
                'source': 'lazo',
                'createdAt': FieldValue.serverTimestamp(),
              });
              if (ctx2.mounted) Navigator.pop(ctx2);
              _toastC('Thank you - that means a lot to them.');
            } catch (e) {
              up(() {
                saving = false;
                err = 'Could not post your review. Try again in a moment.';
              });
            }
          }

          return _lzFrame(ctx2,
              icon: Icons.star_rounded,
              title: 'Review $vendorName',
              subtitle:
                  'Honest is more useful than glowing. Other couples are counting on you.',
              children: <Widget>[
                const SizedBox(height: 14),
                Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: List<Widget>.generate(5, (int i) {
                      return IconButton(
                        tooltip: '${i + 1} star${i == 0 ? '' : 's'}',
                        onPressed: _h(() => up(() => rating = i + 1)),
                        icon: Icon(
                            i < rating
                                ? Icons.star_rounded
                                : Icons.star_outline_rounded,
                            color: gold,
                            size: 36),
                      );
                    })),
                Text(words[rating],
                    textAlign: TextAlign.center,
                    style: TextStyle(
                        color: _lzFg(plum),
                        fontSize: 14,
                        fontWeight: FontWeight.w700)),
                const SizedBox(height: 16),
                TextField(
                  controller: txt,
                  minLines: 4,
                  maxLines: 6,
                  maxLength: 900,
                  textCapitalization: TextCapitalization.sentences,
                  style: TextStyle(color: _lzFg(ink), fontSize: 14),
                  decoration: _lightDeco('Your review',
                      hint:
                          'What were they like to work with? What should the next couple know?'),
                ),
                _pcC_err(err),
              ],
              footer: _lzActions(
                  secondary: 'Later',
                  onSecondary: () => Navigator.pop(ctx2),
                  primary: 'Post review',
                  icon: Icons.star_rounded,
                  busy: saving,
                  onPrimary: post));
        },
      ),
    ).whenComplete(() => open = false);
  }

""")

    # ------------------------------------------------------ _editTimelineEvent
    span("  Future<void> _editTimelineEvent(",
         "  // ---- JC-LAZO-COUPLE-0920-TL-001: the anchored timeline ----",
         r"""  Future<void> _editTimelineEvent(
      QueryDocumentSnapshot<Map<String, dynamic>>? d) async {
    final Map<String, dynamic> ev = d?.data() ?? <String, dynamic>{};
    final TextEditingController labelC =
        TextEditingController(text: (ev['label'] ?? '').toString());
    final TextEditingController noteC =
        TextEditingController(text: (ev['note'] ?? '').toString());
    final List<String> t0 = ((ev['time'] ?? '16:00').toString()).split(':');
    TimeOfDay time = TimeOfDay(
        hour: int.tryParse(t0[0]) ?? 16,
        minute: t0.length > 1 ? int.tryParse(t0[1]) ?? 0 : 0);
    // JC-LAZO-COUPLE-0920-TL-001: how long it runs, whose moment it is, and
    // whether it is the ceremony - the anchor the whole day shifts around.
    int dur = ev['dur'] is num ? (ev['dur'] as num).toInt() : 0;
    final Set<String> owners = <String>{
      if (ev['owners'] is List)
        for (final dynamic o in ev['owners'] as List) o.toString()
    };
    bool anchor = ev['anchor'] == true;
    bool saving = false;
    bool open = true;
    String err = '';

    Future<void> save() async {
      final String hh =
          '${time.hour.toString().padLeft(2, '0')}:${time.minute.toString().padLeft(2, '0')}';
      final Map<String, dynamic> payload = <String, dynamic>{
        'time': hh,
        'label': labelC.text.trim(),
        'note': noteC.text.trim(),
        'dur': dur,
        'owners': owners.toList()..sort(),
        'anchor': anchor,
        'updatedAt': FieldValue.serverTimestamp(),
      };
      if (d == null) {
        await _dayofRef.add(payload);
      } else {
        await d.reference.set(payload, SetOptions(merge: true));
      }
      if (anchor) {
        // One anchor only: the ceremony.
        try {
          final QuerySnapshot<Map<String, dynamic>> others =
              await _dayofRef.where('anchor', isEqualTo: true).get();
          final WriteBatch b = FirebaseFirestore.instance.batch();
          bool any = false;
          for (final QueryDocumentSnapshot<Map<String, dynamic>> o
              in others.docs) {
            if (d != null && o.id == d.id) continue;
            if (d == null &&
                (o.data()['label'] ?? '') == labelC.text.trim() &&
                (o.data()['time'] ?? '') == hh) continue;
            b.set(o.reference, <String, dynamic>{'anchor': false},
                SetOptions(merge: true));
            any = true;
          }
          if (any) await b.commit();
        } catch (_) {}
      }
    }

    await _lzSheet<bool>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext ctx) => StatefulBuilder(
          builder: (BuildContext ctx2, StateSetter setD) {
        void up(VoidCallback f) {
          if (open) setD(f);
        }

        Future<void> go() async {
          up(() {
            saving = true;
            err = '';
          });
          try {
            await save();
            if (ctx2.mounted) Navigator.pop(ctx2, true);
          } catch (_) {
            up(() {
              saving = false;
              err =
                  'Could not save this moment. Check your connection and try again.';
            });
          }
        }

        return _lzFrame(ctx2,
            icon: Icons.schedule_rounded,
            title: d == null ? 'Add a moment' : 'Edit moment',
            subtitle: 'One line on your day-of timeline.',
            children: <Widget>[
              const SizedBox(height: 16),
              TextField(
                  controller: labelC,
                  autofocus: d == null,
                  textCapitalization: TextCapitalization.sentences,
                  textInputAction: TextInputAction.next,
                  onChanged: (_) => up(() {}),
                  style: TextStyle(color: _lzFg(ink)),
                  decoration: _lightDeco('What happens', hint: 'Ceremony')),
              const SizedBox(height: 12),
              _pcC_pickRow(Icons.schedule_rounded, 'Starts at',
                  time.format(ctx2), () async {
                final TimeOfDay? p =
                    await showTimePicker(context: ctx2, initialTime: time);
                if (p != null) {
                  up(() => time = p);
                }
              }),
              const SizedBox(height: 12),
              TextField(
                  controller: noteC,
                  textCapitalization: TextCapitalization.sentences,
                  style: TextStyle(color: _lzFg(ink)),
                  decoration: _lightDeco('Note (optional)',
                      hint: 'Where, who, what to bring')),
              _lzSection('How long'),
              Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
                for (final int m in const <int>[
                  0,
                  15,
                  30,
                  45,
                  60,
                  90,
                  120,
                  180
                ])
                  _tlChip(m == 0 ? 'A moment' : _tlDur(m), dur == m,
                      () => up(() => dur = m)),
              ]),
              _lzSection('Whose moment'),
              Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
                for (final List<String> o in kTlOwners)
                  _tlChip(
                      o[1],
                      owners.contains(o[0]),
                      () => up(() {
                            if (!owners.remove(o[0])) owners.add(o[0]);
                          })),
              ]),
              _lzSection('The anchor'),
              Align(
                alignment: Alignment.centerLeft,
                child: _tlChip(
                    'This is the ceremony \u00b7 the day is built around it',
                    anchor,
                    () => up(() => anchor = !anchor)),
              ),
              _pcC_err(err),
            ],
            footer: _lzActions(
                secondary: 'Cancel',
                onSecondary: () => Navigator.pop(ctx2, false),
                primary: d == null ? 'Add moment' : 'Save',
                icon: Icons.check_rounded,
                busy: saving,
                onPrimary: labelC.text.trim().isEmpty ? null : go));
      }),
    ).whenComplete(() => open = false);
  }

""")

    # ---------------------------------------------------------- _chaptersSheet
    span("  Future<void> _chaptersSheet(String slug) async {",
         "  Future<void> _addChapterDialog(String slug,",
         r"""  Future<void> _chaptersSheet(String slug) async {
    if (!mounted) {
      return;
    }
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 640),
      builder: (BuildContext ctx) =>
          StreamBuilder<QuerySnapshot<Map<String, dynamic>>>(
        stream: FirebaseFirestore.instance
            .collection('weddingSites')
            .doc(slug)
            .collection('chapters')
            .orderBy('dateIso', descending: true)
            .snapshots(),
        builder: (BuildContext c,
            AsyncSnapshot<QuerySnapshot<Map<String, dynamic>>> sn) {
          final List<QueryDocumentSnapshot<Map<String, dynamic>>> docs =
              sn.data?.docs ?? <QueryDocumentSnapshot<Map<String, dynamic>>>[];
          final bool loading = !sn.hasData && !sn.hasError;
          return _lzFrame(ctx,
              icon: Icons.auto_stories_rounded,
              title: 'Chapters',
              subtitle: docs.isEmpty
                  ? 'The story keeps going on your site after the big day.'
                  : '${docs.length} on your site - tap one to edit',
              children: <Widget>[
                const SizedBox(height: 14),
                if (loading)
                  _lzBusy('Loading your chapters')
                else if (docs.isEmpty)
                  _pcC_empty(Icons.auto_stories_outlined,
                      'No chapters yet. Add the honeymoon, big news or an anniversary.')
                else
                  for (final QueryDocumentSnapshot<Map<String, dynamic>> d
                      in docs)
                    _pcC_chapterRow(slug, d),
              ],
              footer: _lzActions(
                  secondary: 'Done',
                  onSecondary: () => Navigator.pop(ctx),
                  primary: 'Add a chapter',
                  icon: Icons.add_rounded,
                  onPrimary: () => _addChapterDialog(slug)));
        },
      ),
    );
  }

  Widget _pcC_chapterRow(
      String slug, QueryDocumentSnapshot<Map<String, dynamic>> d) {
    final Map<String, dynamic> ch = d.data();
    final List<String> ph = List<String>.from(
        (ch['photos'] as List?)?.map((dynamic e) => e.toString()) ??
            const <String>[]);
    final String title = (ch['title'] ?? '').toString();
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: _Press(
        scale: .985,
        dim: .92,
        onTap: () => _addChapterDialog(slug, d),
        child: Container(
          padding: const EdgeInsets.fromLTRB(12, 12, 4, 12),
          decoration: BoxDecoration(
              color: _lzBg(cardBg),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: _lzLine(goldLine))),
          child: Row(children: <Widget>[
            ClipRRect(
              borderRadius: BorderRadius.circular(10),
              child: ph.isNotEmpty
                  ? Image.network(ph.first,
                      width: 54,
                      height: 54,
                      fit: BoxFit.cover,
                      errorBuilder:
                          (BuildContext c5, Object e, StackTrace? st) =>
                              Container(
                                  width: 54,
                                  height: 54,
                                  color: gold.withOpacity(.12)))
                  : Container(
                      width: 54,
                      height: 54,
                      color: gold.withOpacity(.12),
                      child: Icon(Icons.auto_stories_outlined,
                          color: _lzFg(plum), size: 22)),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(title.isEmpty ? 'Untitled chapter' : title,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                            color: _lzFg(plum),
                            fontSize: 14.5,
                            fontWeight: FontWeight.w700)),
                    const SizedBox(height: 2),
                    Text(
                        '${ch['dateIso'] ?? ''}${ph.isNotEmpty ? ' \u00b7 ${ph.length} photo${ph.length == 1 ? '' : 's'}' : ''}',
                        style: TextStyle(fontSize: 12, color: _lzFg(muted))),
                  ]),
            ),
            IconButton(
              tooltip: 'Delete chapter',
              onPressed: _h(() async {
                final bool sure = await _lzConfirm('Delete this chapter?',
                    'It comes off your site right away.',
                    confirm: 'Delete chapter', cancel: 'Keep', danger: true);
                if (sure) {
                  await d.reference.delete();
                }
              }),
              icon: Icon(Icons.delete_outline_rounded,
                  color: _lzFg(muted), size: 20),
            ),
          ]),
        ),
      ),
    );
  }

""")

    # ------------------------------------------------------- _addChapterDialog
    span("  Future<void> _addChapterDialog(String slug,",
         "  void _siteLiveShareSheet(String names, String slug) {",
         r"""  Future<void> _addChapterDialog(String slug,
      [QueryDocumentSnapshot<Map<String, dynamic>>? existing]) async {
    final Map<String, dynamic> ex = existing?.data() ?? <String, dynamic>{};
    final TextEditingController titleC =
        TextEditingController(text: (ex['title'] ?? '').toString());
    final TextEditingController textC =
        TextEditingController(text: (ex['text'] ?? '').toString());
    DateTime chDate =
        DateTime.tryParse((ex['dateIso'] ?? '').toString()) ?? DateTime.now();
    final List<String> photos = List<String>.from(
        (ex['photos'] as List?)?.map((dynamic e) => e.toString()) ??
            const <String>[]);
    bool busy = false;
    bool saving = false;
    bool open = true;
    String err = '';
    const List<String> months = <String>[
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

    Future<void> pickPhotos(StateSetter setD) async {
      void up(VoidCallback f) {
        if (open) setD(f);
      }

      try {
        final FilePickerResult? res = await FilePicker.platform.pickFiles(
            type: FileType.image, allowMultiple: true, withData: true);
        if (res == null || res.files.isEmpty) {
          return;
        }
        up(() {
          busy = true;
          err = '';
        });
        for (final PlatformFile f in res.files) {
          if (photos.length >= 4) {
            break;
          }
          final Uint8List? bytes = f.bytes;
          if (bytes == null) {
            continue;
          }
          final String ext = f.name.contains('.')
              ? f.name.substring(f.name.lastIndexOf('.')).toLowerCase()
              : '.jpg';
          final String ctype = ext == '.png'
              ? 'image/png'
              : ext == '.webp'
                  ? 'image/webp'
                  : 'image/jpeg';
          final Reference ref = FirebaseStorage.instance.ref(
              'couples/$_uid/site/ch${DateTime.now().millisecondsSinceEpoch}$ext');
          await ref.putData(bytes, SettableMetadata(contentType: ctype));
          photos.add(await ref.getDownloadURL());
          up(() {});
        }
        up(() => busy = false);
      } catch (e) {
        up(() {
          busy = false;
          err = 'A photo didn\u2019t upload. Try a JPG or PNG, or try again.';
        });
      }
    }

    await _lzSheet<bool>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) {
          void up(VoidCallback f) {
            if (open) setD(f);
          }

          Future<void> publish() async {
            up(() {
              saving = true;
              err = '';
            });
            try {
              final Map<String, dynamic> chData = <String, dynamic>{
                'title': titleC.text.trim(),
                'text': textC.text.trim(),
                'dateIso':
                    '${chDate.year}-${chDate.month.toString().padLeft(2, '0')}-${chDate.day.toString().padLeft(2, '0')}',
                'photos': photos,
                if (existing == null) 'createdAt': FieldValue.serverTimestamp(),
                'updatedAt': FieldValue.serverTimestamp(),
              };
              if (existing != null) {
                await existing.reference.set(chData, SetOptions(merge: true));
              } else {
                await FirebaseFirestore.instance
                    .collection('weddingSites')
                    .doc(slug)
                    .collection('chapters')
                    .add(chData);
              }
              if (ctx2.mounted) Navigator.pop(ctx2, true);
              _toastC(existing != null
                  ? 'Chapter updated.'
                  : 'Chapter published. It\u2019s live on your site.');
            } catch (e) {
              up(() {
                saving = false;
                err = 'Couldn\u2019t publish just now. Try again in a moment.';
              });
            }
          }

          Widget thumb(Widget child) => ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: SizedBox(width: 74, height: 74, child: child),
              );

          return _lzFrame(ctx2,
              icon: Icons.auto_stories_rounded,
              title: existing == null ? 'Add a chapter' : 'Edit chapter',
              subtitle: 'Honeymoon photos, big news, anniversaries.',
              children: <Widget>[
                const SizedBox(height: 16),
                TextField(
                    controller: titleC,
                    autofocus: existing == null,
                    textCapitalization: TextCapitalization.sentences,
                    textInputAction: TextInputAction.next,
                    onChanged: (_) => up(() {}),
                    style: TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _lightDeco('Title',
                        hint: 'The honeymoon \u00b7 Big news \u00b7 One year in')),
                const SizedBox(height: 12),
                _pcC_pickRow(
                    Icons.event_rounded,
                    'Date',
                    '${months[chDate.month - 1]} ${chDate.day}, ${chDate.year}',
                    () async {
                  final DateTime? d = await showDatePicker(
                      context: ctx2,
                      initialDate: chDate,
                      firstDate: DateTime(2020),
                      lastDate: DateTime(2100));
                  if (d != null) {
                    up(() => chDate = d);
                  }
                }),
                const SizedBox(height: 12),
                TextField(
                    controller: textC,
                    minLines: 3,
                    maxLines: 6,
                    textCapitalization: TextCapitalization.sentences,
                    style: TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _lightDeco('The story')),
                _lzSection('Photos', trailing: '${photos.length} of 4'),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: <Widget>[
                    ...photos.map((String u) => thumb(Image.network(u,
                        fit: BoxFit.cover,
                        errorBuilder:
                            (BuildContext c5, Object e, StackTrace? st) =>
                                Container(color: gold.withOpacity(.12))))),
                    if (busy)
                      thumb(Container(
                        color: gold.withOpacity(.1),
                        child: const Center(
                            child: SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(
                                    color: gold, strokeWidth: 2))),
                      )),
                    if (!busy && photos.length < 4)
                      _Press(
                        onTap: () => pickPhotos(setD),
                        child: Container(
                          width: 74,
                          height: 74,
                          decoration: BoxDecoration(
                            color: _lzBg(Colors.white),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: _lzLine(gold)),
                          ),
                          child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: <Widget>[
                                Icon(Icons.add_photo_alternate_outlined,
                                    color: _lzFg(plum), size: 22),
                                const SizedBox(height: 3),
                                Text('Add',
                                    style: TextStyle(
                                        fontSize: 11.5,
                                        color: _lzFg(plum),
                                        fontWeight: FontWeight.w700)),
                              ]),
                        ),
                      ),
                  ],
                ),
                _pcC_err(err),
              ],
              footer: _lzActions(
                  secondary: 'Cancel',
                  onSecondary: () => Navigator.pop(ctx2, false),
                  primary:
                      existing == null ? 'Publish chapter' : 'Save chapter',
                  icon: Icons.check_rounded,
                  busy: saving,
                  onPrimary: titleC.text.trim().isEmpty || busy
                      ? null
                      : publish));
        },
      ),
    ).whenComplete(() => open = false);
  }

""")

    # ----------------------------------------------------- _siteLiveShareSheet
    span("  void _siteLiveShareSheet(String names, String slug) {",
         "  Future<void> _openContractPdf(Map<String, dynamic> ct) async {",
         r"""  void _siteLiveShareSheet(String names, String slug) {
    final String url = 'https://meetlazo.com/w/$slug/';
    final String msg =
        'Our wedding website is live \u{1F48D} $names \u2014 RSVP, the schedule, all of it: $url';
    bool copied = false;
    _lzSheet(
      context: context,
      constraints: const BoxConstraints(maxWidth: 520),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setS) {
          Future<void> copyLink() async {
            await Clipboard.setData(ClipboardData(text: url));
            if (ctx2.mounted) setS(() => copied = true);
          }

          Widget btn(IconData ic, String label, String sub, VoidCallback onTap) {
            return Expanded(
              child: _Press(
                onTap: onTap,
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 16),
                  margin: const EdgeInsets.symmetric(horizontal: 4),
                  decoration: BoxDecoration(
                    color: _lzBg(cardBg),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: _lzLine(goldLine)),
                  ),
                  child: Column(children: <Widget>[
                    Icon(ic, color: _lzFg(plum), size: 24),
                    const SizedBox(height: 6),
                    Text(label,
                        style: TextStyle(
                            color: _lzFg(ink),
                            fontSize: 13,
                            fontWeight: FontWeight.w700)),
                    const SizedBox(height: 2),
                    Text(sub,
                        textAlign: TextAlign.center,
                        style: TextStyle(color: _lzFg(muted), fontSize: 11.5)),
                  ]),
                ),
              ),
            );
          }

          return _lzFrame(ctx2,
              icon: Icons.celebration_rounded,
              title: 'Your website is live',
              subtitle:
                  'Send it to the people you love. RSVPs land right back here.',
              children: <Widget>[
                const SizedBox(height: 16),
                _Press(
                  onTap: copyLink,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 14, vertical: 13),
                    decoration: BoxDecoration(
                      color: _lzBg(Colors.white),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(
                          color: copied ? vGreen.withOpacity(.6) : _lzLine(gold)),
                    ),
                    child: Row(children: <Widget>[
                      Icon(Icons.language_rounded,
                          color: _lzFg(plum), size: 18),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(url.replaceFirst('https://', ''),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                                color: _lzFg(plum),
                                fontSize: 14,
                                fontWeight: FontWeight.w700)),
                      ),
                      const SizedBox(width: 8),
                      Icon(copied ? Icons.check_rounded : Icons.copy_rounded,
                          color: _lzFg(
                              copied ? vGreen : const Color(0xFF8A6A2F)),
                          size: 17),
                      if (copied) ...<Widget>[
                        const SizedBox(width: 4),
                        Text('Copied',
                            style: TextStyle(
                                color: _lzFg(vGreen),
                                fontSize: 12.5,
                                fontWeight: FontWeight.w700)),
                      ],
                    ]),
                  ),
                ),
                _lzSection('Share it'),
                Row(children: <Widget>[
                  btn(Icons.facebook_rounded, 'Facebook', 'Post the link', () {
                    _openLink(
                        'https://www.facebook.com/sharer/sharer.php?u=${Uri.encodeComponent(url)}&quote=${Uri.encodeComponent(msg)}');
                  }),
                  btn(Icons.photo_camera_rounded, 'Instagram',
                      'We copy a caption', () async {
                    await Clipboard.setData(ClipboardData(text: msg));
                    _toastC('Caption copied. Paste it into a Story or post.');
                    _openLink('https://www.instagram.com/');
                  }),
                ]),
              ],
              footer: _lzActions(
                  secondary: 'Done',
                  onSecondary: () => Navigator.pop(ctx2),
                  primary: copied ? 'Link copied' : 'Copy link',
                  icon: copied ? Icons.check_rounded : Icons.copy_rounded,
                  onPrimary: copyLink));
        },
      ),
    );
  }

""")

    # ----------------------------------------------------- _contractsVaultSheet
    # The lookup used to start inside the builder (so a rebuild ran it again);
    # it starts once when the sheet opens. Same queries.
    span("  Future<void> _contractsVaultSheet() async {",
         "  Future<void> _openSigning(String url) async {",
         r"""  Future<void> _contractsVaultSheet() async {
    if (_uid == null) {
      return;
    }
    final Future<List<Map<String, dynamic>>> load = () async {
      final List<Map<String, dynamic>> rows = <Map<String, dynamic>>[];
      final QuerySnapshot<Map<String, dynamic>> iq = await FirebaseFirestore
          .instance
          .collection('inquiries')
          .where('coupleUid', isEqualTo: _cid)
          .limit(40)
          .get();
      for (final QueryDocumentSnapshot<Map<String, dynamic>> inq in iq.docs) {
        try {
          final QuerySnapshot<Map<String, dynamic>> cs = await inq.reference
              .collection('contracts')
              .where('status', isEqualTo: 'signed')
              .get();
          for (final QueryDocumentSnapshot<Map<String, dynamic>> c
              in cs.docs) {
            rows.add(<String, dynamic>{
              ...c.data(),
              'vendorName': inq.data()['vendorName'] ?? 'Vendor',
            });
          }
        } catch (_) {}
      }
      rows.sort((Map<String, dynamic> a, Map<String, dynamic> b) {
        final Timestamp ta = (a['signedAt'] is Timestamp)
            ? a['signedAt'] as Timestamp
            : Timestamp(0, 0);
        final Timestamp tb = (b['signedAt'] is Timestamp)
            ? b['signedAt'] as Timestamp
            : Timestamp(0, 0);
        return tb.compareTo(ta);
      });
      return rows;
    }();
    _lzSheet(
      context: context,
      constraints: const BoxConstraints(maxWidth: 680),
      builder: (BuildContext ctx) => FutureBuilder<List<Map<String, dynamic>>>(
        future: load,
        builder:
            (BuildContext c2, AsyncSnapshot<List<Map<String, dynamic>>> s) {
          final List<Map<String, dynamic>> rows =
              s.data ?? <Map<String, dynamic>>[];
          final bool loading = s.connectionState != ConnectionState.done;
          return _lzFrame(ctx,
              icon: Icons.history_edu_rounded,
              title: 'Your contracts',
              subtitle: loading || rows.isEmpty
                  ? 'Every signed agreement, kept for you.'
                  : '${rows.length} signed \u00b7 kept for you',
              children: <Widget>[
                const SizedBox(height: 14),
                if (loading)
                  _lzBusy('Gathering your signed contracts')
                else if (s.hasError)
                  _pcC_err(
                      'Could not load your contracts. Close this and try again.')
                else if (rows.isEmpty)
                  _pcC_empty(Icons.history_edu_rounded,
                      'Nothing signed yet. When you sign a vendor\u2019s agreement, it lives here.')
                else
                  for (final Map<String, dynamic> ct in rows)
                    _pcC_contractRow(ct),
              ]);
        },
      ),
    );
  }

  Widget _pcC_contractRow(Map<String, dynamic> ct) {
    String when = '';
    if (ct['signedAt'] is Timestamp) {
      final DateTime dt = (ct['signedAt'] as Timestamp).toDate();
      when = 'Signed ${dt.month}/${dt.day}/${dt.year}';
    }
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.fromLTRB(14, 12, 6, 12),
      decoration: BoxDecoration(
        color: _lzBg(Colors.white),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: vGreen.withOpacity(.5)),
      ),
      child: Row(children: <Widget>[
        Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
                color: vGreen.withOpacity(.12),
                borderRadius: BorderRadius.circular(11)),
            child: Icon(Icons.verified_rounded, color: _lzFg(vGreen), size: 19)),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text((ct['templateName'] ?? 'Agreement').toString(),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                        color: _lzFg(ink),
                        fontSize: 14,
                        fontWeight: FontWeight.w700)),
                const SizedBox(height: 2),
                Text('${ct['vendorName']}${when.isEmpty ? '' : ' \u00b7 $when'}',
                    style: TextStyle(fontSize: 12, color: _lzFg(muted))),
              ]),
        ),
        TextButton(
          onPressed: _h(() => _openContractPdf(ct)),
          child: Text('View',
              style: TextStyle(
                  color: _lzFg(plum),
                  fontSize: 13,
                  fontWeight: FontWeight.w800)),
        ),
      ]),
    );
  }

""")

    # -------------------------------------------------------- _coupleProposals
    rep(r"""                            final bool? sure = await _lzDialog<bool>(
                              context: context,
                              builder: (BuildContext dc) => AlertDialog(
                                backgroundColor: _lzBg(ivory),
                                title: const Text('Accept this proposal?',
                                    style: TextStyle(color: plum)),
                                content: Text(
                                    price > 0
                                        ? '${_money(price)} from $vendorName. It becomes this category\u2019s planned figure if you haven\u2019t set one.'
                                        : 'You\u2019re telling $vendorName yes.',
                                    style: const TextStyle(
                                        color: ink, fontSize: 14)),
                                actions: <Widget>[
                                  TextButton(
                                      onPressed: () => Navigator.pop(dc, false),
                                      child: const Text('Not yet',
                                          style: TextStyle(color: ink))),
                                  FilledButton(
                                      style: FilledButton.styleFrom(
                                          backgroundColor: gold,
                                          foregroundColor: plumDeep),
                                      onPressed: () => Navigator.pop(dc, true),
                                      child: const Text('Accept')),
                                ],
                              ),
                            );
                            if (sure != true) {
                              return;
                            }""",
        r"""                            final bool sure = await _lzConfirm(
                                'Accept this proposal?',
                                price > 0
                                    ? '${_money(price)} from $vendorName. It becomes this category\u2019s planned figure if you haven\u2019t set one.'
                                    : 'You\u2019re telling $vendorName yes.',
                                confirm: 'Accept proposal',
                                cancel: 'Not yet',
                                icon: Icons.description_rounded);
                            if (!sure) {
                              return;
                            }""")
    rep(r"""                        'Accepted \u00b7 you\u2019re booked \uD83C\uDF89',""",
        r"""                        'Accepted \u00b7 you\u2019re booked',""")

    # ------------------------------------------------------ _editCoupleMessage
    span("  Future<void> _editCoupleMessage(",
         "  // v70: emoji, same set as the vendor sees.",
         r"""  Future<void> _editCoupleMessage(
      String inquiryId, String messageId, String current) async {
    final TextEditingController ec = TextEditingController(text: current);
    bool saving = false;
    bool open = true;
    String err = '';
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 520),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setE) {
          void up(VoidCallback f) {
            if (open) setE(f);
          }

          final String t = ec.text.trim();
          final bool can = t.isNotEmpty && t != current;

          Future<void> save() async {
            up(() {
              saving = true;
              err = '';
            });
            try {
              await FirebaseFirestore.instance
                  .collection('inquiries')
                  .doc(inquiryId)
                  .collection('messages')
                  .doc(messageId)
                  .update(<String, dynamic>{
                'text': ec.text.trim(),
                'editedAt': FieldValue.serverTimestamp(),
              });
              if (ctx2.mounted) Navigator.pop(ctx2);
            } catch (_) {
              up(() {
                saving = false;
                err = 'Could not save your edit. Try again.';
              });
            }
          }

          return _lzFrame(ctx2,
              icon: Icons.edit_rounded,
              title: 'Edit message',
              subtitle: 'It shows as edited in the conversation.',
              children: <Widget>[
                const SizedBox(height: 16),
                TextField(
                  controller: ec,
                  autofocus: true,
                  minLines: 2,
                  maxLines: 6,
                  textCapitalization: TextCapitalization.sentences,
                  onChanged: (_) => up(() {}),
                  style: TextStyle(color: _lzFg(ink)),
                  decoration: _lightDeco('Your message'),
                ),
                _pcC_err(err),
              ],
              footer: _lzActions(
                  secondary: 'Cancel',
                  onSecondary: () => Navigator.pop(ctx2),
                  primary: 'Save',
                  icon: Icons.check_rounded,
                  busy: saving,
                  onPrimary: can ? save : null));
        },
      ),
    ).whenComplete(() => open = false);
  }

""")

    # ------------------------------------------------------------ _emojiSheet
    # A picker: left alone apart from the house dash.
    rep(r"""                    child: Text('Tap to add \u2014 keep going, then close.',""",
        r"""                    child: Text('Tap to add - keep going, then close.',""")

    # -------------------------------------------------------------- _bdAddLink
    span("  Future<void> _bdAddLink() async {",
         "  Future<void> _bdAddPhoto() async {",
         r"""  Future<void> _bdAddLink() async {
    final TextEditingController c = TextEditingController();
    bool busy = false;
    bool open = true;
    String err = '';
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 520),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setL) {
          void up(VoidCallback f) {
            if (open) setL(f);
          }

          Future<void> pin() async {
            String u = c.text.trim();
            if (u.isEmpty || busy) return;
            if (!u.startsWith('http')) u = 'https://' + u;
            up(() {
              busy = true;
              err = '';
            });
            if (mounted) setState(() => _bdBusy = true);
            try {
              final httpc.Response r = await httpc
                  .get(Uri.parse('https://meetlazo.com/api/unfurl?u=' +
                      Uri.encodeComponent(u)))
                  .timeout(const Duration(seconds: 15));
              final Map<String, dynamic> j = r.statusCode == 200
                  ? Map<String, dynamic>.from(jsonDecode(r.body) as Map)
                  : <String, dynamic>{};
              final String img = (j['image'] ?? '').toString();
              if (ctx2.mounted) Navigator.pop(ctx2);
              if (img.isEmpty) {
                _bdAdd(<String, dynamic>{
                  'kind': 'note',
                  'text': (j['title'] ?? '').toString().isNotEmpty
                      ? j['title'].toString()
                      : u,
                  'src': u,
                  'color': 'F3EBDD',
                  'w': 220.0,
                  'ar': 1.4,
                });
                _toast(
                    'No picture on that page - pinned it as a note with the link.');
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
              up(() {
                busy = false;
                err =
                    'Could not read that link. Check it opens in your browser, then try again.';
              });
            } finally {
              if (mounted) setState(() => _bdBusy = false);
            }
          }

          return _lzFrame(ctx2,
              icon: Icons.link_rounded,
              title: 'Pin from a link',
              subtitle: 'We pull the picture and a caption from the page.',
              children: <Widget>[
                const SizedBox(height: 16),
                TextField(
                    controller: c,
                    autofocus: true,
                    enabled: !busy,
                    keyboardType: TextInputType.url,
                    textInputAction: TextInputAction.go,
                    onChanged: (_) => up(() {}),
                    onSubmitted: (_) => pin(),
                    style: TextStyle(color: _lzFg(ink)),
                    decoration: _lightDeco('Paste the link',
                        hint:
                            'A Pinterest pin, an Etsy listing, any page or picture')),
                const SizedBox(height: 12),
                if (busy)
                  _lzBusy('Reading the page\u2026')
                else
                  _lzNote(Icons.push_pin_outlined,
                      'On Pinterest, copy the link from the share button.'),
                _pcC_err(err),
              ],
              footer: _lzActions(
                  secondary: 'Cancel',
                  onSecondary: () => Navigator.pop(ctx2),
                  primary: 'Pin it',
                  icon: Icons.push_pin_rounded,
                  busy: busy,
                  onPrimary: c.text.trim().isEmpty ? null : pin));
        },
      ),
    ).whenComplete(() => open = false);
  }

""")

    # -------------------------------------------------------------- _bdAddNote
    span("  Future<void> _bdAddNote([Map<String, dynamic>? existing]) async {",
         "  Future<void> _bdAddSwatch([Map<String, dynamic>? existing]) async {",
         r"""  Future<void> _bdAddNote([Map<String, dynamic>? existing]) async {
    final TextEditingController c =
        TextEditingController(text: (existing?['text'] ?? '').toString());
    String color = (existing?['color'] ?? 'F3EBDD').toString();
    final bool? ok = await _lzSheet<bool>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 520),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) => _lzFrame(ctx2,
            icon: Icons.sticky_note_2_outlined,
            title: existing == null ? 'Add a note' : 'Edit note',
            subtitle: 'A thought, a rule, a feeling for the day.',
            children: <Widget>[
              const SizedBox(height: 16),
              TextField(
                  controller: c,
                  autofocus: true,
                  minLines: 3,
                  maxLines: 6,
                  textCapitalization: TextCapitalization.sentences,
                  onChanged: (_) => setD(() {}),
                  style: TextStyle(color: _lzFg(ink)),
                  decoration: _lightDeco('The note',
                      hint:
                          'Candlelight, long tables, no centrepieces taller than a wine glass')),
              _lzSection('Paper'),
              Wrap(spacing: 10, runSpacing: 10, children: <Widget>[
                for (final String k in const <String>[
                  'F3EBDD',
                  'F6E7E4',
                  'E7EFE6',
                  'E6EEF5',
                  'EFE9F5',
                  'FFFFFF'
                ])
                  _Press(
                    tick: _Tick.select,
                    onTap: () => setD(() => color = k),
                    child: Container(
                      width: 38,
                      height: 38,
                      decoration: BoxDecoration(
                          color: _lzBg(Color(int.parse('FF$k', radix: 16))),
                          shape: BoxShape.circle,
                          border: Border.all(
                              color: _lzLine(color == k ? plum : goldLine),
                              width: color == k ? 2.5 : 1)),
                      child: color == k
                          ? Icon(Icons.check_rounded,
                              size: 17, color: _lzFg(plum))
                          : null,
                    ),
                  ),
              ]),
            ],
            footer: _lzActions(
                secondary: 'Cancel',
                onSecondary: () => Navigator.pop(ctx2, false),
                primary: existing == null ? 'Add note' : 'Save',
                icon: Icons.check_rounded,
                onPrimary: c.text.trim().isEmpty
                    ? null
                    : () => Navigator.pop(ctx2, true))),
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
    _bdAdd(<String, dynamic>{
      'kind': 'note',
      'text': c.text.trim(),
      'color': color,
      'src': '',
      'w': 220.0,
      'ar': 1.3
    });
  }

""")

    # ------------------------------------------------------------ _bdAddSwatch
    span("  Future<void> _bdAddSwatch([Map<String, dynamic>? existing]) async {",
         "  // v135: who is typing - initials and first name",
         r"""  Future<void> _bdAddSwatch([Map<String, dynamic>? existing]) async {
    String color = (existing?['color'] ?? 'D9B77C').toString();
    final TextEditingController hexC = TextEditingController(text: color);
    final TextEditingController labelC =
        TextEditingController(text: (existing?['text'] ?? '').toString());
    final bool? ok = await _lzSheet<bool>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 520),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) {
          final Color shown =
              Color(int.tryParse('FF$color', radix: 16) ?? 0xFFD9B77C);
          return _lzFrame(ctx2,
              icon: Icons.palette_outlined,
              title: existing == null ? 'Add a color' : 'Edit color',
              subtitle: 'Pick from the palette or type a hex code.',
              children: <Widget>[
                const SizedBox(height: 16),
                Container(
                  height: 70,
                  alignment: Alignment.bottomLeft,
                  padding: const EdgeInsets.fromLTRB(14, 0, 14, 10),
                  decoration: BoxDecoration(
                      color: shown,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: _lzLine(goldLine))),
                  child: Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                    decoration: BoxDecoration(
                        color: Colors.white.withOpacity(.85),
                        borderRadius: BorderRadius.circular(999)),
                    child: Text(
                        labelC.text.trim().isEmpty
                            ? '#$color'
                            : '${labelC.text.trim()} \u00b7 #$color',
                        style: const TextStyle(
                            color: ink,
                            fontSize: 12,
                            fontWeight: FontWeight.w700)),
                  ),
                ),
                _lzSection('Palette'),
                Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                  for (final String k in kBoardColors)
                    _Press(
                      tick: _Tick.select,
                      onTap: () => setD(() {
                        color = k;
                        hexC.text = k;
                      }),
                      child: Container(
                        width: 36,
                        height: 36,
                        decoration: BoxDecoration(
                            color: _lzBg(Color(int.parse('FF$k', radix: 16))),
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(
                                color: _lzLine(color == k ? plum : goldLine),
                                width: color == k ? 2.5 : 1)),
                      ),
                    ),
                ]),
                const SizedBox(height: 16),
                TextField(
                    controller: hexC,
                    style: TextStyle(color: _lzFg(ink)),
                    onChanged: (String v) {
                      final String h = v.replaceAll('#', '').trim().toUpperCase();
                      if (RegExp(r'^[0-9A-F]{6}$').hasMatch(h)) {
                        setD(() => color = h);
                      }
                    },
                    decoration: _lightDeco('Hex', hint: 'D9B77C', prefix: '#')),
                const SizedBox(height: 12),
                TextField(
                    controller: labelC,
                    textCapitalization: TextCapitalization.sentences,
                    onChanged: (_) => setD(() {}),
                    style: TextStyle(color: _lzFg(ink)),
                    decoration: _lightDeco('Call it (optional)',
                        hint: 'Dusty sage, bridesmaids')),
              ],
              footer: _lzActions(
                  secondary: 'Cancel',
                  onSecondary: () => Navigator.pop(ctx2, false),
                  primary: existing == null ? 'Add color' : 'Save',
                  icon: Icons.check_rounded,
                  onPrimary: () => Navigator.pop(ctx2, true)));
        },
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
    _bdAdd(<String, dynamic>{
      'kind': 'swatch',
      'color': color,
      'text': labelC.text.trim(),
      'src': '',
      'w': 120.0,
      'ar': 1.0
    });
  }

""")

    # --------------------------------------------------------- _bdCommentSheet
    span("  Future<void> _bdCommentSheet(Map<String, dynamic> it) async {",
         "  Future<void> _bdShare(Map<String, dynamic> couple) async {",
         r"""  Future<void> _bdCommentSheet(Map<String, dynamic> it) async {
    final TextEditingController c = TextEditingController();
    final List<String> me = _bdMe();
    final String myUid = FirebaseAuth.instance.currentUser?.uid ?? '';
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 520),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setS) {
          final List<Map<String, dynamic>> cs = _bdComments(it);
          final String caption = (it['title'] ?? it['text'] ?? '').toString();

          void post() {
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
          }

          Widget avatar(String ini, bool mine) => Container(
                width: 30,
                height: 30,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                    color: mine ? plum : gold, shape: BoxShape.circle),
                child: Text(ini,
                    style: TextStyle(
                        color: mine ? gold : plumDeep,
                        fontSize: 11,
                        fontWeight: FontWeight.w800)),
              );

          return _lzFrame(ctx2,
              icon: Icons.forum_outlined,
              title: 'Talk about this one',
              subtitle: cs.isEmpty
                  ? 'Your partner sees it here too.'
                  : '${cs.length} comment${cs.length == 1 ? '' : 's'}',
              headerExtra: Row(children: <Widget>[
                ClipRRect(
                  borderRadius: BorderRadius.circular(10),
                  child: it['kind'] == 'image'
                      ? Image.network((it['url'] ?? '').toString(),
                          width: 48,
                          height: 48,
                          fit: BoxFit.cover,
                          errorBuilder:
                              (BuildContext a, Object b, StackTrace? d) =>
                                  const SizedBox(width: 48, height: 48))
                      : Container(
                          width: 48,
                          height: 48,
                          color: _lzBg(Color(int.tryParse(
                                  'FF${(it['color'] ?? 'F3EBDD').toString()}',
                                  radix: 16) ??
                              0xFFF3EBDD))),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(caption.isEmpty ? 'From your dream board' : caption,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                          fontSize: 13, color: _lzFg(ink), height: 1.35)),
                ),
              ]),
              children: <Widget>[
                const SizedBox(height: 12),
                if (cs.isEmpty)
                  _pcC_empty(Icons.chat_bubble_outline_rounded,
                      'Say what you like about it, or what you\u2019d change.'),
                for (final Map<String, dynamic> cm in cs)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          avatar((cm['ini'] ?? '?').toString(),
                              (cm['by'] ?? '') == myUid),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: <Widget>[
                                  Row(children: <Widget>[
                                    Text((cm['name'] ?? '').toString(),
                                        style: TextStyle(
                                            color: _lzFg(plum),
                                            fontSize: 12.5,
                                            fontWeight: FontWeight.w800)),
                                    const SizedBox(width: 6),
                                    Text(
                                        cm['at'] is num
                                            ? _ago(Timestamp
                                                .fromMillisecondsSinceEpoch(
                                                    (cm['at'] as num).toInt()))
                                            : '',
                                        style: TextStyle(
                                            fontSize: 11, color: _lzFg(muted))),
                                  ]),
                                  const SizedBox(height: 2),
                                  Text((cm['text'] ?? '').toString(),
                                      style: TextStyle(
                                          color: _lzFg(ink),
                                          fontSize: 14,
                                          height: 1.4)),
                                ]),
                          ),
                          if ((cm['by'] ?? '') == myUid)
                            IconButton(
                              tooltip: 'Delete comment',
                              icon: Icon(Icons.close_rounded,
                                  size: 15, color: _lzFg(muted)),
                              onPressed: () {
                                setState(() {
                                  final List<Map<String, dynamic>> all =
                                      _bdComments(it);
                                  all.removeWhere((Map<String, dynamic> x) =>
                                      x['at'] == cm['at'] &&
                                      x['by'] == cm['by']);
                                  it['comments'] = all;
                                });
                                setS(() {});
                                _bdSave();
                              },
                            ),
                        ]),
                  ),
              ],
              footer: Row(children: <Widget>[
                avatar(me[0], true),
                const SizedBox(width: 10),
                Expanded(
                  child: TextField(
                    controller: c,
                    autofocus: cs.isEmpty,
                    minLines: 1,
                    maxLines: 3,
                    textCapitalization: TextCapitalization.sentences,
                    textInputAction: TextInputAction.send,
                    style: TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _lightDeco('',
                        hint: 'Candles instead of taper lights?'),
                    onSubmitted: (String v) => post(),
                  ),
                ),
                const SizedBox(width: 6),
                IconButton(
                  tooltip: 'Send',
                  icon: Icon(Icons.send_rounded, color: _lzFg(plum)),
                  onPressed: post,
                ),
              ]));
        },
      ),
    );
  }

""")

    # ----------------------------------------------------------- _editShopItem
    span("  Future<void> _editShopItem(",
         "  Future<void> _sendShopping(",
         r"""  Future<void> _editShopItem(
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
    String cat = (it['cat'] ??
            (_shopFilter.length > 5 &&
                    kShopCats.any((List<String> k) => k[0] == _shopFilter)
                ? _shopFilter
                : 'reception'))
        .toString();
    bool saving = false;
    bool open = true;
    String err = '';

    Future<void> save() async {
      String link = linkC.text.trim();
      if (link.isNotEmpty && !link.startsWith('http')) link = 'https://' + link;
      final Map<String, dynamic> payload = <String, dynamic>{
        'name': nameC.text.trim(),
        'cat': cat,
        'qty': int.tryParse(qtyC.text.trim()) ?? 1,
        'est':
            int.tryParse(estC.text.trim().replaceAll(RegExp(r'[^0-9]'), '')) ??
                0,
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

    await _lzSheet<bool>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext ctx) => StatefulBuilder(
          builder: (BuildContext ctx2, StateSetter setD) {
        void up(VoidCallback f) {
          if (open) setD(f);
        }

        Future<void> go() async {
          up(() {
            saving = true;
            err = '';
          });
          try {
            await save();
            if (ctx2.mounted) Navigator.pop(ctx2, true);
          } catch (_) {
            up(() {
              saving = false;
              err = 'Could not save that. Check your connection and try again.';
            });
          }
        }

        return _lzFrame(ctx2,
            icon: Icons.shopping_bag_outlined,
            title: d == null ? 'Add to the list' : 'Edit item',
            subtitle: 'What you need, how many, and roughly what it costs.',
            children: <Widget>[
              const SizedBox(height: 16),
              TextField(
                  controller: nameC,
                  autofocus: d == null,
                  textCapitalization: TextCapitalization.sentences,
                  textInputAction: TextInputAction.next,
                  onChanged: (_) => up(() {}),
                  style: TextStyle(color: _lzFg(ink)),
                  decoration: _lightDeco('What', hint: 'Card box')),
              const SizedBox(height: 12),
              Row(children: <Widget>[
                Expanded(
                  child: TextField(
                      controller: qtyC,
                      keyboardType: TextInputType.number,
                      textInputAction: TextInputAction.next,
                      style: TextStyle(color: _lzFg(ink)),
                      decoration: _lightDeco('How many')),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: TextField(
                      controller: estC,
                      keyboardType: TextInputType.number,
                      textInputAction: TextInputAction.next,
                      style: TextStyle(color: _lzFg(ink)),
                      decoration: _lightDeco('About, in total',
                          hint: '0', prefix: '\$ ')),
                ),
              ]),
              _lzSection('Where it\u2019s for'),
              Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
                for (final List<String> k in kShopCats)
                  _tlChip(k[1], cat == k[0], () => up(() => cat = k[0])),
              ]),
              const SizedBox(height: 16),
              TextField(
                  controller: linkC,
                  keyboardType: TextInputType.url,
                  textInputAction: TextInputAction.next,
                  style: TextStyle(color: _lzFg(ink)),
                  decoration: _lightDeco('Link (optional)',
                      hint: 'Where you found it')),
              const SizedBox(height: 12),
              TextField(
                  controller: noteC,
                  textCapitalization: TextCapitalization.sentences,
                  style: TextStyle(color: _lzFg(ink)),
                  decoration: _lightDeco('Note (optional)',
                      hint: 'Colour, size, who\u2019s buying it')),
              _pcC_err(err),
            ],
            footer: _lzActions(
                secondary: 'Cancel',
                onSecondary: () => Navigator.pop(ctx2, false),
                primary: d == null ? 'Add to list' : 'Save',
                icon: Icons.check_rounded,
                busy: saving,
                onPrimary: nameC.text.trim().isEmpty ? null : go));
      }),
    ).whenComplete(() => open = false);
  }

""")
    return s
