# Popup pass JC-LAZO-POPUP-1014, part v3 (vendor dashboard).
# Generated: exact-string replacements against popup_parts/base_vendor.txt.

def apply(s: str) -> str:
    def rep(old, new):
        nonlocal s
        assert s.count(old) == 1, (s.count(old), old[:80])
        s = s.replace(old, new)

    # A contract ready + v3 helpers
    rep(r"""  void _contractDraftedSheet(
      String vendorId, String inquiryId, Map<String, dynamic> r) {
    final String pdfPath = (r['pdfPath'] ?? '') as String;
    final List<String> missing = r['missingFields'] is List
        ? (r['missingFields'] as List).map((dynamic e) => e.toString()).toList()
        : <String>[];
    final bool usedProposal = r['usedProposal'] == true;
    _lzSheet(
      context: context,
      backgroundColor: _lzBg(ivory),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (BuildContext ctx) => Padding(
        padding: const EdgeInsets.fromLTRB(22, 22, 22, 30),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(children:  <Widget>[
              Icon(Icons.check_circle_rounded, color: _lzFg(vGreen), size: 22),
              SizedBox(width: 8),
              Text('Contract drafted',
                  style: TextStyle(
                      color: _lzFg(plum), fontSize: 18, fontWeight: FontWeight.w800)),
            ]),
            const SizedBox(height: 6),
            Text(
                usedProposal
                    ? 'Package and price pulled from your proposal in this thread.'
                    : 'No proposal found - package details came from what you entered.',
                style:  TextStyle(fontSize: 12.5, color: _lzFg(muted))),
            if (missing.isNotEmpty) ...<Widget>[
              const SizedBox(height: 8),
              Text(
                  '${missing.length} unfilled: ${missing.join(', ')} - these appear as blank lines in the PDF.',
                  style:
                       TextStyle(fontSize: 12, color: _lzFg(Color(0xFF8A6A2F)))),
            ],
            const SizedBox(height: 16),
            if (missing.isEmpty)
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  style: FilledButton.styleFrom(
                      backgroundColor: vGreen,
                      foregroundColor: ivory,
                      padding: const EdgeInsets.symmetric(vertical: 13)),
                  onPressed: _h(() {
                    final String cid = (r['contractId'] ?? '') as String;
                    Navigator.pop(ctx);
                    _sendForSignature(vendorId, inquiryId, cid);
                  }, _Tick.medium),
                  icon: const Icon(Icons.send_rounded, size: 18),
                  label: const Text('Send for signature',
                      style: TextStyle(fontWeight: FontWeight.w700)),
                ),
              ),
            if (missing.isEmpty) const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                    foregroundColor: _lzFg(plum),
                    side: BorderSide(color: gold.withOpacity(.8)),
                    padding: const EdgeInsets.symmetric(vertical: 13)),
                onPressed: _h(
                    pdfPath.isEmpty ? null : () => _openContractPdf(pdfPath)),
                icon: const Icon(Icons.picture_as_pdf_rounded, size: 18),
                label: const Text('View PDF',
                    style: TextStyle(fontWeight: FontWeight.w600)),
              ),
            ),
            if (missing.isNotEmpty) ...<Widget>[
              const SizedBox(height: 8),
               Text(
                  'Fill the blank fields and generate again to enable sending.',
                  style: TextStyle(fontSize: 11, color: _lzFg(muted))),
            ],
          ],
        ),
      ),
    );
  }
""", r"""  void _contractDraftedSheet(
      String vendorId, String inquiryId, Map<String, dynamic> r) {
    final String pdfPath = (r['pdfPath'] ?? '') as String;
    final List<String> missing = r['missingFields'] is List
        ? (r['missingFields'] as List).map((dynamic e) => e.toString()).toList()
        : <String>[];
    final bool usedProposal = r['usedProposal'] == true;
    final VoidCallback? viewPdf =
        pdfPath.isEmpty ? null : () => _openContractPdf(pdfPath);
    _lzSheet(
      context: context,
      constraints: const BoxConstraints(maxWidth: 540),
      builder: (BuildContext ctx) => _lzFrame(ctx,
          icon: Icons.history_edu_rounded,
          title: 'Your contract is ready',
          subtitle: usedProposal
              ? 'Package and price came from your proposal in this thread.'
              : 'No proposal in this thread, so the package details came from what you entered.',
          children: <Widget>[
            const SizedBox(height: 14),
            _pv3Tile(
                Icons.picture_as_pdf_rounded,
                'Contract PDF',
                viewPdf == null
                    ? 'The PDF isn\u2019t ready to open yet.'
                    : 'Read it the way they will.',
                viewPdf,
                trailing: Icons.open_in_new_rounded),
            if (missing.isEmpty) ...<Widget>[
              const SizedBox(height: 4),
              _lzNote(Icons.check_circle_outline_rounded,
                  'Every field is filled in. Send it and they can review and sign from the thread.'),
            ] else ...<Widget>[
              _lzSection('Still blank', trailing: '${missing.length}'),
              Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
                for (final String f in missing)
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 11, vertical: 6),
                    decoration: BoxDecoration(
                        color: _lzBg(const Color(0xFFF6EEDF)),
                        borderRadius: BorderRadius.circular(999),
                        border: Border.all(color: _lzLine(goldLine))),
                    child: Text(f,
                        style: TextStyle(
                            fontSize: 12.5,
                            fontWeight: FontWeight.w600,
                            color: _lzFg(const Color(0xFF8A6A2F)))),
                  ),
              ]),
              const SizedBox(height: 14),
              _lzNote(Icons.info_outline_rounded,
                  'Blank fields print as empty lines. Fill them in and generate it again to send it for signature.'),
            ],
          ],
          footer: missing.isEmpty
              ? _lzActions(
                  secondary: 'Not yet',
                  onSecondary: () => Navigator.pop(ctx),
                  primary: 'Send for signature',
                  icon: Icons.send_rounded,
                  onPrimary: () {
                    final String cid = (r['contractId'] ?? '') as String;
                    Navigator.pop(ctx);
                    _sendForSignature(vendorId, inquiryId, cid);
                  })
              : _lzActions(
                  secondary: 'Close',
                  onSecondary: () => Navigator.pop(ctx),
                  primary: 'View PDF',
                  icon: Icons.picture_as_pdf_rounded,
                  onPrimary: viewPdf)),
    );
  }

  // ---- popup pass v3: shared pieces for the vendor popups below ----
  /// An inline error inside a popup, in place of a toast nobody reads.
  Widget _pv3Err(String msg) => Container(
        width: double.infinity,
        margin: const EdgeInsets.only(top: 12),
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
        decoration: BoxDecoration(
            color: _lzBg(const Color(0xFFFBEAEA)),
            borderRadius: BorderRadius.circular(13),
            border: Border.all(color: _lzLine(const Color(0xFFD9A0A0)))),
        child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Icon(Icons.error_outline_rounded,
                  size: 18, color: _lzFg(const Color(0xFF7C2B2B))),
              const SizedBox(width: 10),
              Expanded(
                  child: Text(msg,
                      style: TextStyle(
                          fontSize: 13,
                          color: _lzFg(const Color(0xFF7C2B2B)),
                          height: 1.4))),
            ]),
      );

  /// A tappable row card: icon chip, title, one line, chevron.
  Widget _pv3Tile(IconData icon, String title, String sub, VoidCallback? onTap,
      {bool locked = false, IconData trailing = Icons.chevron_right_rounded}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: _Press(
        onTap: onTap,
        enabled: onTap != null,
        scale: .985,
        child: Container(
          padding: const EdgeInsets.fromLTRB(12, 11, 10, 11),
          decoration: BoxDecoration(
              color: _lzBg(card),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: _lzLine(goldLine))),
          child: Row(children: <Widget>[
            Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                    color: locked ? _lzBg(const Color(0xFFEDE6EE)) : plumDeep,
                    borderRadius: BorderRadius.circular(12)),
                child: Icon(locked ? Icons.lock_outline_rounded : icon,
                    color: locked ? _lzFg(muted) : gold, size: 19)),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(title,
                        style: TextStyle(
                            color: _lzFg(locked ? muted : plum),
                            fontSize: 14.5,
                            fontWeight: FontWeight.w700)),
                    if (sub.isNotEmpty) ...<Widget>[
                      const SizedBox(height: 2),
                      Text(sub,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                              fontSize: 12.5,
                              color: _lzFg(muted),
                              height: 1.3)),
                    ],
                  ]),
            ),
            const SizedBox(width: 6),
            Icon(trailing, color: _lzFg(muted), size: 19),
          ]),
        ),
      ),
    );
  }

  /// A step card with a number, a title, one line and its own action.
  Widget _pv3Step(int n, String title, String body, Widget action) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.fromLTRB(14, 13, 14, 14),
      decoration: BoxDecoration(
          color: _lzBg(card),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: _lzLine(goldLine))),
      child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            Row(children: <Widget>[
              Container(
                  width: 24,
                  height: 24,
                  alignment: Alignment.center,
                  decoration: const BoxDecoration(
                      color: plumDeep, shape: BoxShape.circle),
                  child: Text('$n',
                      style: const TextStyle(
                          color: gold,
                          fontSize: 12,
                          fontWeight: FontWeight.w800))),
              const SizedBox(width: 10),
              Expanded(
                child: Text(title,
                    style: TextStyle(
                        color: _lzFg(ink),
                        fontSize: 14.5,
                        fontWeight: FontWeight.w700)),
              ),
            ]),
            const SizedBox(height: 6),
            Text(body,
                style:
                    TextStyle(fontSize: 12.5, color: _lzFg(muted), height: 1.4)),
            const SizedBox(height: 10),
            action,
          ]),
    );
  }
""")

    # B1 proposal frame + send()
    rep(r"""    await _lzSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setS) {
          final num price =
              num.tryParse(priceC.text.replaceAll(',', '').trim()) ?? 0;
          return Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 720),
              child: Container(
                margin: EdgeInsets.only(
                    bottom: MediaQuery.of(ctx2).viewInsets.bottom),
                padding: const EdgeInsets.fromLTRB(24, 12, 24, 24),
                decoration:  BoxDecoration(
                  color: _lzBg(ivory),
                  borderRadius: BorderRadius.vertical(top: Radius.circular(26)),
                ),
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Center(
                        child: Container(
                            width: 44,
                            height: 4,
                            decoration: BoxDecoration(
                                color: plum.withOpacity(.2),
                                borderRadius: BorderRadius.circular(99))),
                      ),
                      const SizedBox(height: 16),
                      Row(children: <Widget>[
                        Container(
                          width: 38,
                          height: 38,
                          decoration: BoxDecoration(
                              gradient: const LinearGradient(
                                  colors: <Color>[plumDeep, plum]),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: gold.withOpacity(.7))),
                          child: const Icon(Icons.request_quote_rounded,
                              color: gold, size: 19),
                        ),
                        const SizedBox(width: 11),
                        Expanded(
                          child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                 Text('Send a proposal',
                                    style: TextStyle(
                                        color: _lzFg(ink),
                                        fontSize: 18,
                                        fontWeight: FontWeight.w800)),
                                Text(
                                    bizName.isEmpty
                                        ? 'They see it in the thread, under your name.'
                                        : 'They see it in the thread, under $bizName.',
                                    style:  TextStyle(
                                        color: _lzFg(muted), fontSize: 11.5)),
                              ]),
                        ),
                        IconButton(
                            icon:  Icon(Icons.close_rounded, color: _lzFg(muted)),
                            onPressed: _h(() => Navigator.pop(ctx2))),
                      ]),
""", r"""    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 720),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setS) {
          final num price =
              num.tryParse(priceC.text.replaceAll(',', '').trim()) ?? 0;
          Future<void> send() async {
            if (titleC.text.trim().isEmpty) {
              setS(() => err = 'Give the proposal a name.');
              return;
            }
            if (price <= 0) {
              setS(() => err = 'Add a price.');
              return;
            }
            setS(() {
              sending = true;
              err = '';
            });
            try {
              final List<String> inc = incC.text
                  .split('\n')
                  .map((String s) => s.trim())
                  .where((String s) => s.isNotEmpty)
                  .toList();
              await FirebaseFirestore.instance
                  .collection('inquiries')
                  .doc(inquiryId)
                  .collection('proposals')
                  .add(<String, dynamic>{
                'title': titleC.text.trim(),
                'price': price,
                'note': noteC.text.trim(),
                'includes': inc,
                'validUntil':
                    holdUntil == null ? null : Timestamp.fromDate(holdUntil!),
                'status': 'sent',
                'createdAt': FieldValue.serverTimestamp(),
              });
              await _sendVendorMessage(
                  inquiryId,
                  noteC.text.trim().isEmpty
                      ? 'I\u2019ve put together a proposal for you \u2014 ${titleC.text.trim()}, ${_invMoney(price)}. It\u2019s just above.'
                      : noteC.text.trim(),
                  'responded');
              if (ctx2.mounted) Navigator.pop(ctx2);
              _toast('Proposal sent \u2713');
            } catch (e) {
              setS(() {
                sending = false;
                err = 'Could not send: ' + _errText(e);
              });
            }
          }

          return _lzFrame(ctx2,
              icon: Icons.request_quote_rounded,
              title: 'Send a proposal',
              subtitle: bizName.isEmpty
                  ? 'They see it in the thread, under your name.'
                  : 'They see it in the thread, under $bizName.',
              children: <Widget>[
""")

    # B2 proposal package label
    rep(r"""                        const SizedBox(height: 14),
                         Text('START FROM A PACKAGE',
                            style: TextStyle(
                                color: _lzFg(muted),
                                fontSize: 8.5,
                                letterSpacing: 1.4,
                                fontWeight: FontWeight.w800)),
                        const SizedBox(height: 7),
""", r"""                        _lzSection('Start from a package'),
""")

    # B3 proposal title field
    rep(r"""                      TextField(
                        controller: titleC,
                        onChanged: (_) => setS(() {}),
                        style:  TextStyle(color: _lzFg(ink), fontSize: 14.5),
                        decoration: _epDeco('What you\u2019re proposing',
                            'The Verse \u2014 8 hours'),
                      ),
""", r"""                      TextField(
                        controller: titleC,
                        autofocus: packs.isEmpty,
                        textInputAction: TextInputAction.next,
                        onChanged: (_) => setS(() {}),
                        style:  TextStyle(color: _lzFg(ink), fontSize: 14.5),
                        decoration: _epDeco('What you\u2019re proposing',
                            'The Verse - 8 hours'),
                      ),
""")

    # B4 proposal helper copy
    rep(r"""                          helperText:
                              'One item per line \u2014 they see it as a list',
""", r"""                          helperText:
                              'One item per line - they see it as a list',
""")

    # B5 proposal note hint
    rep(r"""                            'Loved hearing about your day \u2014 here\u2019s what I\u2019d suggest.'),
""", r"""                            'Loved hearing about your day - here\u2019s what I\u2019d suggest.'),
""")

    # B6 proposal footer
    rep(r"""                      const SizedBox(height: 16),
                      SizedBox(
                        width: double.infinity,
                        child: FilledButton(
                          style: FilledButton.styleFrom(
                              backgroundColor: gold,
                              foregroundColor: plum,
                              padding:
                                  const EdgeInsets.symmetric(vertical: 14)),
                          onPressed: _h(
                              sending
                                  ? null
                                  : () async {
                                      if (titleC.text.trim().isEmpty) {
                                        setS(() =>
                                            err = 'Give the proposal a name.');
                                        return;
                                      }
                                      if (price <= 0) {
                                        setS(() => err = 'Add a price.');
                                        return;
                                      }
                                      setS(() {
                                        sending = true;
                                        err = '';
                                      });
                                      try {
                                        final List<String> inc = incC.text
                                            .split('\n')
                                            .map((String s) => s.trim())
                                            .where((String s) => s.isNotEmpty)
                                            .toList();
                                        await FirebaseFirestore.instance
                                            .collection('inquiries')
                                            .doc(inquiryId)
                                            .collection('proposals')
                                            .add(<String, dynamic>{
                                          'title': titleC.text.trim(),
                                          'price': price,
                                          'note': noteC.text.trim(),
                                          'includes': inc,
                                          'validUntil': holdUntil == null
                                              ? null
                                              : Timestamp.fromDate(holdUntil!),
                                          'status': 'sent',
                                          'createdAt':
                                              FieldValue.serverTimestamp(),
                                        });
                                        await _sendVendorMessage(
                                            inquiryId,
                                            noteC.text.trim().isEmpty
                                                ? 'I\u2019ve put together a proposal for you \u2014 ${titleC.text.trim()}, ${_invMoney(price)}. It\u2019s just above.'
                                                : noteC.text.trim(),
                                            'responded');
                                        if (ctx2.mounted) Navigator.pop(ctx2);
                                        _toast('Proposal sent \u2713');
                                      } catch (e) {
                                        setS(() {
                                          sending = false;
                                          err =
                                              'Could not send: ' + _errText(e);
                                        });
                                      }
                                    },
                              _Tick.medium),
                          child: Text(
                              sending ? 'Sending\u2026' : 'Send proposal',
                              style: const TextStyle(
                                  fontSize: 14.5, fontWeight: FontWeight.w800)),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }
""", r"""              ],
              footer: _lzActions(
                  secondary: 'Cancel',
                  onSecondary: () => Navigator.pop(ctx2),
                  primary: sending ? 'Sending\u2026' : 'Send proposal',
                  icon: Icons.send_rounded,
                  busy: sending,
                  onPrimary: titleC.text.trim().isEmpty || price <= 0
                      ? null
                      : send));
        },
      ),
    );
  }
""")

    # C composer tools
    rep(r"""    _lzSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      // v144: constrain the ROUTE. A Center inside the builder still gets a
      // full-width box handed to it, which is why the sheet spanned the
      // monitor.
      constraints: const BoxConstraints(maxWidth: 620),
      builder: (BuildContext ctx) {
        Widget row(IconData ic, String title, String sub, VoidCallback go,
            {bool locked = false}) {
          return ListTile(
            onTap: () {
              Navigator.pop(ctx);
              go();
            },
            leading: Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                gradient: locked
                    ? LinearGradient(colors: <Color>[
                        muted.withOpacity(.35),
                        muted.withOpacity(.22)
                      ])
                    : const LinearGradient(colors: <Color>[plumDeep, plum]),
                borderRadius: BorderRadius.circular(13),
                border: Border.all(
                    color:
                        _lzLine(locked ? muted.withOpacity(.4) : gold.withOpacity(.6))),
              ),
              child: Icon(locked ? Icons.lock_outline_rounded : ic,
                  color: _lzFg(locked ? ivory : gold), size: 20),
            ),
            title: Text(title,
                style: TextStyle(
                    color: _lzFg(locked ? muted : plum),
                    fontSize: 14.5,
                    fontWeight: FontWeight.w700)),
            subtitle:
                Text(sub, style:  TextStyle(fontSize: 11.5, color: _lzFg(muted))),
            trailing:
                 Icon(Icons.chevron_right_rounded, color: _lzFg(muted), size: 20),
          );
        }

        // v143: nine tools no longer fit a min-height sheet. Cap it, scroll it,
        // and stop it spanning the whole monitor.
        return Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 620),
            child: Container(
              constraints: BoxConstraints(
                  maxHeight: MediaQuery.of(ctx).size.height * .82),
              decoration:  BoxDecoration(
                color: _lzBg(ivory),
                borderRadius: BorderRadius.vertical(top: Radius.circular(26)),
              ),
              child: SafeArea(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(10, 12, 10, 14),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Center(
                        child: Container(
                            width: 44,
                            height: 4,
                            margin: const EdgeInsets.only(bottom: 12),
                            decoration: BoxDecoration(
                                color: plum.withOpacity(.2),
                                borderRadius: BorderRadius.circular(99))),
                      ),
                       Padding(
                        padding: EdgeInsets.only(left: 16, bottom: 6),
                        child: Text('STUDIO TOOLS',
                            style: TextStyle(
                                color: _lzFg(muted),
                                fontSize: 10,
                                letterSpacing: 2,
                                fontWeight: FontWeight.w800)),
                      ),
                      Flexible(
                        child: ListView(
                          shrinkWrap: true,
                          padding: EdgeInsets.zero,
                          children: <Widget>[
                            row(Icons.attach_file_rounded, 'Send a file',
                                kAttachHint, () => _sendAttachment(inquiryId)),
                            if (_delivers())
                              row(
                                  Icons.auto_awesome_motion_rounded,
                                  'June Sneak Peek',
                                  _isBooked(inq)
                                      ? 'Drop the take \u2014 June picks the frames and writes the words'
                                      : 'Opens once you mark them booked',
                                  _isBooked(inq)
                                      ? () => _sneakPeekSheet(inquiryId, inq)
                                      : () => _needsBooked(
                                          inquiryId, inq, 'Sneak Peek'),
                                  locked: !_isBooked(inq)),
                            if (_isVideo())
                              row(
                                  Icons.movie_creation_rounded,
                                  'Send a teaser film',
                                  _isBooked(inq)
                                      ? 'Paste your Vimeo or YouTube link \u2014 June writes the words'
                                      : 'Opens once you mark them booked',
                                  _isBooked(inq)
                                      ? () => _teaserSheet(inquiryId, inq)
                                      : () => _needsBooked(
                                          inquiryId, inq, 'Teaser films'),
                                  locked: !_isBooked(inq)),
                            if (_delivers())
                              row(
                                  Icons.local_shipping_rounded,
                                  _isVideo() && !_isPhoto()
                                      ? 'Mark film delivered'
                                      : 'Mark gallery delivered',
                                  _isBooked(inq)
                                      ? 'Starts their review request \u2014 not before'
                                      : 'Opens once you mark them booked',
                                  _isBooked(inq)
                                      ? () => _markDelivered(inquiryId)
                                      : () => _needsBooked(
                                          inquiryId, inq, 'Delivery'),
                                  locked: !_isBooked(inq)),
                            row(
                                Icons.request_quote_rounded,
                                'Send a proposal',
                                'Price a package for this couple',
                                () => _sendProposal(inquiryId)),
                            row(
                                Icons.history_edu_rounded,
                                'Send a contract',
                                'E-signature agreement \u2014 June prefills it',
                                () => _startContractFlow(inquiryId, inq)),
                            row(
                                Icons.fact_check_outlined,
                                'Send a questionnaire',
                                'Collect the details before the day',
                                () => _sendQuestionnaireSheet(inquiryId, inq)),
                            row(
                                Icons.receipt_long_rounded,
                                'Send an invoice',
                                'An itemized payment request',
                                () => _invoiceComposeSheet(inquiryId, inq)),
                            row(
                                Icons.calendar_month_rounded,
                                'Set up a payment plan',
                                'Retainer + installments, each with a due date',
                                () => _paymentPlanSheet(inquiryId, inq)),
                            row(
                                Icons.group_rounded,
                                'Recommend my team',
                                _isBooked(inq)
                                    ? 'Your trusted pros, as one-tap cards in their thread'
                                    : 'Opens once you mark them booked',
                                _isBooked(inq)
                                    ? () => _recommendTeamSheet(inquiryId, inq)
                                    : () => _needsBooked(inquiryId, inq,
                                        'Recommending your team'),
                                locked: !_isBooked(inq)),
                            row(
                                Icons.event_available_rounded,
                                'Send a booking link',
                                'They pick a time from your calendar - no back and forth',
                                () => _sendBookingLink(inquiryId, inq)),
                            row(
                                Icons.task_alt_rounded,
                                'Add a task',
                                'For you, a manager, or the couple - with a due date',
                                () => _taskSheet(inquiryId, inq,
                                    (inq['vendorId'] ?? '') as String)),
                            row(
                                Icons.link_rounded,
                                'Copy booking link',
                                'One page with their proposal, agreement and every payment - no login',
                                () => _copyBookingLink(inquiryId, inq)),
                            row(
                                Icons.auto_awesome_rounded,
                                'June: draft a reply',
                                'She reads the thread and writes it \u2014 you edit and send',
                                () => _juneDraftReply(
                                    (inq['vendorId'] ?? '') as String,
                                    inquiryId,
                                    msgC)),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
""", r"""    _lzSheet(
      context: context,
      // v144: constrain the ROUTE so the sheet never spans a monitor.
      constraints: const BoxConstraints(maxWidth: 620),
      builder: (BuildContext ctx) {
        final bool booked = _isBooked(inq);
        const String later = 'Opens once you mark them booked';
        Widget row(IconData ic, String title, String sub, VoidCallback go,
            {bool locked = false}) {
          return _pv3Tile(ic, title, sub, () {
            Navigator.pop(ctx);
            go();
          }, locked: locked);
        }

        return _lzFrame(ctx,
            icon: Icons.handyman_rounded,
            title: 'Studio tools',
            subtitle: 'Everything you can send from this thread.',
            children: <Widget>[
              _lzSection('Reply and send'),
              row(
                  Icons.auto_awesome_rounded,
                  'June writes a reply',
                  'She reads the thread and writes it - you edit and send',
                  () => _juneDraftReply(
                      (inq['vendorId'] ?? '') as String, inquiryId, msgC)),
              row(Icons.attach_file_rounded, 'Send a file', kAttachHint,
                  () => _sendAttachment(inquiryId)),
              row(Icons.request_quote_rounded, 'Send a proposal',
                  'Price a package for this couple',
                  () => _sendProposal(inquiryId)),
              row(Icons.history_edu_rounded, 'Send a contract',
                  'E-signature agreement - June fills it in',
                  () => _startContractFlow(inquiryId, inq)),
              row(Icons.fact_check_outlined, 'Send a questionnaire',
                  'Collect the details before the day',
                  () => _sendQuestionnaireSheet(inquiryId, inq)),
              row(
                  Icons.event_available_rounded,
                  'Send a booking link',
                  'They pick a time from your calendar - no back and forth',
                  () => _sendBookingLink(inquiryId, inq)),
              row(
                  Icons.task_alt_rounded,
                  'Add a task',
                  'For you, a manager, or the couple - with a due date',
                  () => _taskSheet(
                      inquiryId, inq, (inq['vendorId'] ?? '') as String)),
              _lzSection('Get paid'),
              row(Icons.receipt_long_rounded, 'Send an invoice',
                  'An itemized payment request',
                  () => _invoiceComposeSheet(inquiryId, inq)),
              row(Icons.calendar_month_rounded, 'Set up a payment plan',
                  'Retainer + installments, each with a due date',
                  () => _paymentPlanSheet(inquiryId, inq)),
              row(
                  Icons.link_rounded,
                  'Copy booking link',
                  'One page with their proposal, agreement and every payment - no login',
                  () => _copyBookingLink(inquiryId, inq)),
              _lzSection('Once they\u2019re booked',
                  trailing: booked ? null : 'Mark them booked to open'),
              if (_delivers())
                row(
                    Icons.auto_awesome_motion_rounded,
                    'June Sneak Peek',
                    booked
                        ? 'Drop the take - June picks the frames and writes the words'
                        : later,
                    booked
                        ? () => _sneakPeekSheet(inquiryId, inq)
                        : () => _needsBooked(inquiryId, inq, 'Sneak Peek'),
                    locked: !booked),
              if (_isVideo())
                row(
                    Icons.movie_creation_rounded,
                    'Send a teaser film',
                    booked
                        ? 'Paste your Vimeo or YouTube link - June writes the words'
                        : later,
                    booked
                        ? () => _teaserSheet(inquiryId, inq)
                        : () => _needsBooked(inquiryId, inq, 'Teaser films'),
                    locked: !booked),
              if (_delivers())
                row(
                    Icons.local_shipping_rounded,
                    _isVideo() && !_isPhoto()
                        ? 'Mark film delivered'
                        : 'Mark gallery delivered',
                    booked ? 'Starts their review request - not before' : later,
                    booked
                        ? () => _markDelivered(inquiryId)
                        : () => _needsBooked(inquiryId, inq, 'Delivery'),
                    locked: !booked),
              row(
                  Icons.group_rounded,
                  'Recommend my team',
                  booked
                      ? 'Your trusted pros, as one-tap cards in their thread'
                      : later,
                  booked
                      ? () => _recommendTeamSheet(inquiryId, inq)
                      : () => _needsBooked(
                          inquiryId, inq, 'Recommending your team'),
                  locked: !booked),
            ]);
      },
    );
""")

    # D june studio title
    rep(r"""                                Text('June for Studio',
                                    style: TextStyle(
                                        color: _lzFg(plum),
                                        fontSize: 17,
                                        fontWeight: FontWeight.w800)),
""", r"""                                Text('June for Studio',
                                    style: _serif(size: 24, height: 1.1)),
""")

    # E invoice compose
    rep(r"""    if (!mounted) return;
    const Color ink = Color(0xFF241E2B);
    final TextEditingController titleC = TextEditingController(text: prefTitle);
    final List<Map<String, TextEditingController>> items =
        <Map<String, TextEditingController>>[
      <String, TextEditingController>{
        'label': TextEditingController(text: prefLabel),
        'amount': TextEditingController(
            text: prefBalance > 0 ? prefBalance.toString() : ''),
      }
    ];
    DateTime? due;
    bool sending = false;
    String errMsg = '';

    InputDecoration deco(String hint) => InputDecoration(
          hintText: hint,
          hintStyle: TextStyle(color: _lzFg(ink.withOpacity(.35)), fontSize: 13.5),
          filled: true,
          fillColor: _lzBg(Colors.white),
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 13, vertical: 12),
          border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide(color: plum.withOpacity(.18))),
          enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide(color: plum.withOpacity(.18))),
          focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: const BorderSide(color: plum, width: 1.4)),
        );

    await _lzSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (BuildContext ctx2) {
        return StatefulBuilder(
            builder: (BuildContext sc, StateSetter setSheet) {
          num total = 0;
          for (final Map<String, TextEditingController> it in items) {
            total +=
                num.tryParse(it['amount']!.text.replaceAll(',', '').trim()) ??
                    0;
          }
          return Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 720),
              child: Container(
                margin: EdgeInsets.only(
                    bottom: MediaQuery.of(ctx2).viewInsets.bottom),
                padding: const EdgeInsets.fromLTRB(22, 12, 22, 24),
                decoration:  BoxDecoration(
                  color: _lzBg(ivory),
                  borderRadius: BorderRadius.vertical(top: Radius.circular(26)),
                ),
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Center(
                        child: Container(
                            width: 44,
                            height: 4,
                            decoration: BoxDecoration(
                                color: plum.withOpacity(.2),
                                borderRadius: BorderRadius.circular(99))),
                      ),
                      const SizedBox(height: 16),
                      Row(children: <Widget>[
                        Container(
                          width: 38,
                          height: 38,
                          decoration: BoxDecoration(
                              gradient: const LinearGradient(
                                  colors: <Color>[plumDeep, plum]),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: gold.withOpacity(.7))),
                          child: const Icon(Icons.receipt_long_rounded,
                              color: gold, size: 19),
                        ),
                        const SizedBox(width: 11),
                        Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children:  <Widget>[
                              Text('Send an invoice',
                                  style: TextStyle(
                                      color: _lzFg(ink),
                                      fontSize: 18,
                                      fontWeight: FontWeight.w800)),
                              Text(
                                  'It lands in the thread \u2014 and as a beautiful PDF.',
                                  style: TextStyle(
                                      color: Color(0xFF8A7F90),
                                      fontSize: 11.5)),
                            ]),
                      ]),
                      const SizedBox(height: 16),
                      Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                        _invChip(sc, 'Retainer', prefRetainer > 0, () {
                          setSheet(() {
                            titleC.text = 'Booking retainer';
                            items[0]['label']!.text =
                                'Retainer \u2014 due at signing';
                            items[0]['amount']!.text = prefRetainer.toString();
                          });
                        }),
                        _invChip(sc, 'Balance', prefBalance > 0, () {
                          setSheet(() {
                            titleC.text = 'Wedding balance';
                            items[0]['label']!.text = prefLabel.isEmpty
                                ? 'Remaining balance'
                                : prefLabel;
                            items[0]['amount']!.text = prefBalance.toString();
                          });
                        }),
                        _invChip(sc, 'Custom', true, () {
                          setSheet(() {
                            titleC.text = 'Invoice';
                            items[0]['label']!.text = '';
                            items[0]['amount']!.text = '';
                          });
                        }),
                      ]),
                      const SizedBox(height: 14),
                      TextField(
                          controller: titleC,
                          style:  TextStyle(color: _lzFg(ink), fontSize: 14),
                          decoration: deco('Invoice title')),
                      const SizedBox(height: 12),
                      ...items.asMap().entries.map((e) {
                        final int ix = e.key;
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 9),
                          child: Row(children: <Widget>[
                            Expanded(
                              flex: 5,
                              child: TextField(
                                  controller: e.value['label'],
                                  style:  TextStyle(
                                      color: _lzFg(ink), fontSize: 13.5),
                                  decoration: deco('What is this for?')),
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              flex: 2,
                              child: TextField(
                                  controller: e.value['amount'],
                                  keyboardType:
                                      const TextInputType.numberWithOptions(
                                          decimal: true),
                                  onChanged: (_) => setSheet(() {}),
                                  style:  TextStyle(
                                      color: _lzFg(ink),
                                      fontSize: 13.5,
                                      fontWeight: FontWeight.w700),
                                  decoration: deco('\u0024')),
                            ),
                            if (items.length > 1)
                              IconButton(
                                  onPressed: _h(
                                      () => setSheet(() => items.removeAt(ix))),
                                  icon: Icon(Icons.close_rounded,
                                      color: _lzFg(ink.withOpacity(.4)), size: 18)),
                          ]),
                        );
                      }),
                      TextButton.icon(
                        onPressed: _h(() => setSheet(() {
                              items.add(<String, TextEditingController>{
                                'label': TextEditingController(),
                                'amount': TextEditingController(),
                              });
                            })),
                        icon:  Icon(Icons.add_rounded,
                            color: _lzFg(plum), size: 17),
                        label:  Text('Add a line',
                            style: TextStyle(
                                color: _lzFg(plum),
                                fontSize: 12.5,
                                fontWeight: FontWeight.w700)),
                      ),
                      const SizedBox(height: 4),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 14, vertical: 12),
                        decoration: BoxDecoration(
                            color: _lzBg(Colors.white),
                            borderRadius: BorderRadius.circular(14),
                            border: Border.all(color: gold.withOpacity(.6))),
                        child: Row(children: <Widget>[
                           Text('Total',
                              style: TextStyle(
                                  color: _lzFg(ink),
                                  fontSize: 13,
                                  fontWeight: FontWeight.w700)),
                          const Spacer(),
                          Text(
                              '\u0024' +
                                  total.toStringAsFixed(total % 1 == 0 ? 0 : 2),
                              style:  TextStyle(
                                  color: _lzFg(plum),
                                  fontSize: 19,
                                  fontWeight: FontWeight.w800)),
                        ]),
                      ),
                      const SizedBox(height: 12),
                      Row(children: <Widget>[
                         Text('Due',
                            style: TextStyle(
                                color: _lzFg(ink),
                                fontSize: 12.5,
                                fontWeight: FontWeight.w700)),
                        const SizedBox(width: 10),
                        _invChip(sc, 'Upon receipt', due == null,
                            () => setSheet(() => due = null),
                            selected: due == null),
                        const SizedBox(width: 8),
                        SizedBox(
                          width: 132,
                          child: _invChip(
                              sc,
                              due == null
                                  ? 'Pick a date'
                                  : '${due!.month.toString().padLeft(2, '0')}/${due!.day.toString().padLeft(2, '0')}/${due!.year}',
                              true, () async {
                            final DateTime? d = await showDatePicker(
                                context: sc,
                                initialDate: due ??
                                    DateTime.now()
                                        .add(const Duration(days: 14)),
                                firstDate: DateTime.now(),
                                lastDate: DateTime.now()
                                    .add(const Duration(days: 730)));
                            if (d != null) setSheet(() => due = d);
                          }, selected: due != null),
                        ),
                      ]),
                      if (errMsg.isNotEmpty) ...<Widget>[
                        const SizedBox(height: 12),
                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                              color: _lzBg(const Color(0xFFFBEAEA)),
                              borderRadius: BorderRadius.circular(12),
                              border:
                                  Border.all(color: const Color(0xFFD9A0A0))),
                          child: Text(errMsg,
                              style:  TextStyle(
                                  color: _lzFg(Color(0xFF7C2B2B)), fontSize: 12)),
                        ),
                      ],
                      const SizedBox(height: 16),
                      SizedBox(
                        width: double.infinity,
                        child: FilledButton(
                          style: FilledButton.styleFrom(
                              backgroundColor: gold,
                              foregroundColor: plum,
                              padding:
                                  const EdgeInsets.symmetric(vertical: 14)),
                          onPressed: _h(
                              sending
                                  ? null
                                  : () async {
                                      final List<Map<String, dynamic>> lines =
                                          <Map<String, dynamic>>[];
                                      num t2 = 0;
                                      for (final Map<String,
                                          TextEditingController> it in items) {
                                        final String lb =
                                            it['label']!.text.trim();
                                        final num? am = num.tryParse(
                                            it['amount']!
                                                .text
                                                .replaceAll(',', '')
                                                .trim());
                                        if (lb.isEmpty || am == null) continue;
                                        lines.add(<String, dynamic>{
                                          'label': lb,
                                          'amount': am
                                        });
                                        t2 += am;
                                      }
                                      if (lines.isEmpty || t2 <= 0) {
                                        setSheet(() => errMsg =
                                            'Add at least one line with an amount.');
                                        return;
                                      }
                                      setSheet(() {
                                        sending = true;
                                        errMsg = '';
                                      });
                                      try {
                                        final DocumentReference<
                                                Map<String, dynamic>> ref =
                                            FirebaseFirestore.instance
                                                .collection('inquiries')
                                                .doc(inquiryId)
                                                .collection('invoices')
                                                .doc();
                                        await ref.set(<String, dynamic>{
                                          'vendorId': inq['vendorId'],
                                          'coupleUid': inq['coupleUid'],
                                          'title': titleC.text.trim().isEmpty
                                              ? 'Invoice'
                                              : titleC.text.trim(),
                                          'lineItems': lines,
                                          'total': t2,
                                          'dueDate': due == null
                                              ? null
                                              : Timestamp.fromDate(due!),
                                          'status': 'sent',
                                          'createdAt':
                                              FieldValue.serverTimestamp(),
                                          'sentAt':
                                              FieldValue.serverTimestamp(),
                                        });
                                        await FirebaseFirestore.instance
                                            .collection('inquiries')
                                            .doc(inquiryId)
                                            .set(<String, dynamic>{
                                          'invoiceStatus': 'sent',
                                          'invoiceUpdatedAt':
                                              FieldValue.serverTimestamp(),
                                          'lastInvoiceId': ref.id,
                                        }, SetOptions(merge: true));
                                        if (ctx2.mounted) {
                                          Navigator.pop(ctx2);
                                        }
                                        if (mounted) {
                                          ScaffoldMessenger.of(context)
                                              .showSnackBar(SnackBar(
                                            backgroundColor: _lzBg(ivory),
                                            behavior: SnackBarBehavior.floating,
                                            shape: RoundedRectangleBorder(
                                                borderRadius:
                                                    BorderRadius.circular(14),
                                                side: BorderSide(
                                                    color:
                                                        gold.withOpacity(.55))),
                                            content: const Text(
                                                'Invoice sent \u2014 it\u2019s in the thread.',
                                                style: TextStyle(
                                                    color: ink,
                                                    fontWeight:
                                                        FontWeight.w600)),
                                            action: SnackBarAction(
                                              label: 'View PDF',
                                              textColor: plum,
                                              // SnackBarAction wants a non-null callback
                                              onPressed: _h(() => _openUrl(
                                                  '$_kInvoicePdfBase?inquiry=$inquiryId&invoice=${ref.id}'))!,
                                            ),
                                          ));
                                        }
                                      } catch (e) {
                                        setSheet(() {
                                          sending = false;
                                          errMsg = 'Could not send \u2014 $e';
                                        });
                                      }
                                    },
                              _Tick.medium),
                          child: Text(
                              sending ? 'Sending\u2026' : 'Send invoice',
                              style: const TextStyle(
                                  fontSize: 14.5, fontWeight: FontWeight.w800)),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          );
        });
      },
    );
  }
""", r"""    if (!mounted) return;
    const Color ink = Color(0xFF241E2B);
    final TextEditingController titleC = TextEditingController(text: prefTitle);
    final List<Map<String, TextEditingController>> items =
        <Map<String, TextEditingController>>[
      <String, TextEditingController>{
        'label': TextEditingController(text: prefLabel),
        'amount': TextEditingController(
            text: prefBalance > 0 ? prefBalance.toString() : ''),
      }
    ];
    DateTime? due;
    bool sending = false;
    String errMsg = '';

    String money(num v) => '\$' + v.toStringAsFixed(v % 1 == 0 ? 0 : 2);

    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 720),
      builder: (BuildContext ctx2) {
        return StatefulBuilder(
            builder: (BuildContext sc, StateSetter setSheet) {
          num total = 0;
          for (final Map<String, TextEditingController> it in items) {
            total +=
                num.tryParse(it['amount']!.text.replaceAll(',', '').trim()) ??
                    0;
          }

          Future<void> send() async {
            final List<Map<String, dynamic>> lines = <Map<String, dynamic>>[];
            num t2 = 0;
            for (final Map<String, TextEditingController> it in items) {
              final String lb = it['label']!.text.trim();
              final num? am = num.tryParse(
                  it['amount']!.text.replaceAll(',', '').trim());
              if (lb.isEmpty || am == null) continue;
              lines.add(<String, dynamic>{'label': lb, 'amount': am});
              t2 += am;
            }
            if (lines.isEmpty || t2 <= 0) {
              setSheet(() =>
                  errMsg = 'Add at least one line with what it\u2019s for and an amount.');
              return;
            }
            setSheet(() {
              sending = true;
              errMsg = '';
            });
            try {
              final DocumentReference<Map<String, dynamic>> ref =
                  FirebaseFirestore.instance
                      .collection('inquiries')
                      .doc(inquiryId)
                      .collection('invoices')
                      .doc();
              await ref.set(<String, dynamic>{
                'vendorId': inq['vendorId'],
                'coupleUid': inq['coupleUid'],
                'title': titleC.text.trim().isEmpty
                    ? 'Invoice'
                    : titleC.text.trim(),
                'lineItems': lines,
                'total': t2,
                'dueDate': due == null ? null : Timestamp.fromDate(due!),
                'status': 'sent',
                'createdAt': FieldValue.serverTimestamp(),
                'sentAt': FieldValue.serverTimestamp(),
              });
              await FirebaseFirestore.instance
                  .collection('inquiries')
                  .doc(inquiryId)
                  .set(<String, dynamic>{
                'invoiceStatus': 'sent',
                'invoiceUpdatedAt': FieldValue.serverTimestamp(),
                'lastInvoiceId': ref.id,
              }, SetOptions(merge: true));
              if (ctx2.mounted) {
                Navigator.pop(ctx2);
              }
              if (mounted) {
                ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                  backgroundColor: _lzBg(ivory),
                  behavior: SnackBarBehavior.floating,
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14),
                      side: BorderSide(color: gold.withOpacity(.55))),
                  content: const Text(
                      'Invoice sent \u2014 it\u2019s in the thread.',
                      style:
                          TextStyle(color: ink, fontWeight: FontWeight.w600)),
                  action: SnackBarAction(
                    label: 'View PDF',
                    textColor: plum,
                    // SnackBarAction wants a non-null callback
                    onPressed: _h(() => _openUrl(
                        '$_kInvoicePdfBase?inquiry=$inquiryId&invoice=${ref.id}'))!,
                  ),
                ));
              }
            } catch (e) {
              setSheet(() {
                sending = false;
                errMsg = 'Could not send - $e';
              });
            }
          }

          return _lzFrame(sc,
              icon: Icons.receipt_long_rounded,
              title: 'Send an invoice',
              subtitle: 'It lands in the thread, with a PDF they can keep.',
              children: <Widget>[
                _lzSection('Start from'),
                Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                  _invChip(sc, 'Retainer', prefRetainer > 0, () {
                    setSheet(() {
                      titleC.text = 'Booking retainer';
                      items[0]['label']!.text =
                          'Retainer \u2014 due at signing';
                      items[0]['amount']!.text = prefRetainer.toString();
                    });
                  }),
                  _invChip(sc, 'Balance', prefBalance > 0, () {
                    setSheet(() {
                      titleC.text = 'Wedding balance';
                      items[0]['label']!.text = prefLabel.isEmpty
                          ? 'Remaining balance'
                          : prefLabel;
                      items[0]['amount']!.text = prefBalance.toString();
                    });
                  }),
                  _invChip(sc, 'Custom', true, () {
                    setSheet(() {
                      titleC.text = 'Invoice';
                      items[0]['label']!.text = '';
                      items[0]['amount']!.text = '';
                    });
                  }),
                ]),
                if (prefBalance > 0) ...<Widget>[
                  const SizedBox(height: 8),
                  Text('Filled in from their signed contract.',
                      style: TextStyle(fontSize: 12, color: _lzFg(muted))),
                ],
                const SizedBox(height: 16),
                TextField(
                    controller: titleC,
                    textInputAction: TextInputAction.next,
                    style: TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration: _epDeco('Invoice title', 'Wedding balance')),
                _lzSection('Line items',
                    trailing: items.length > 1 ? '${items.length} lines' : null),
                ...items.asMap().entries.map(
                    (MapEntry<int, Map<String, TextEditingController>> e) {
                  final int ix = e.key;
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: Row(children: <Widget>[
                      Expanded(
                        flex: 5,
                        child: TextField(
                            controller: e.value['label'],
                            textInputAction: TextInputAction.next,
                            style:
                                TextStyle(color: _lzFg(ink), fontSize: 13.5),
                            decoration: _epDeco(
                                'What it\u2019s for', 'Remaining balance')),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        flex: 3,
                        child: TextField(
                            controller: e.value['amount'],
                            keyboardType: const TextInputType.numberWithOptions(
                                decimal: true),
                            onChanged: (_) => setSheet(() {}),
                            style: TextStyle(
                                color: _lzFg(ink),
                                fontSize: 13.5,
                                fontWeight: FontWeight.w700),
                            decoration: _epDeco('Amount', '0').copyWith(
                                prefixText: '\$ ',
                                prefixStyle: TextStyle(
                                    color: _lzFg(plum),
                                    fontSize: 13.5,
                                    fontWeight: FontWeight.w700))),
                      ),
                      if (items.length > 1)
                        IconButton(
                            tooltip: 'Remove line',
                            onPressed:
                                _h(() => setSheet(() => items.removeAt(ix))),
                            icon: Icon(Icons.close_rounded,
                                color: _lzFg(ink.withOpacity(.4)), size: 18)),
                    ]),
                  );
                }),
                Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton.icon(
                    onPressed: _h(() => setSheet(() {
                          items.add(<String, TextEditingController>{
                            'label': TextEditingController(),
                            'amount': TextEditingController(),
                          });
                        })),
                    icon: Icon(Icons.add_rounded, color: _lzFg(plum), size: 17),
                    label: Text('Add a line',
                        style: TextStyle(
                            color: _lzFg(plum),
                            fontSize: 13,
                            fontWeight: FontWeight.w700)),
                  ),
                ),
                const SizedBox(height: 4),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                  decoration: BoxDecoration(
                      color: _lzBg(card),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: _lzLine(goldLine))),
                  child: Row(children: <Widget>[
                    Text('Total',
                        style: TextStyle(
                            color: _lzFg(ink),
                            fontSize: 13.5,
                            fontWeight: FontWeight.w700)),
                    const Spacer(),
                    Text(money(total),
                        style: _serif(size: 26, height: 1)),
                  ]),
                ),
                _lzSection('Due'),
                Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                  _invChip(sc, 'Upon receipt', true,
                      () => setSheet(() => due = null),
                      selected: due == null),
                  _invChip(
                      sc,
                      due == null
                          ? 'Pick a date'
                          : '${due!.month.toString().padLeft(2, '0')}/${due!.day.toString().padLeft(2, '0')}/${due!.year}',
                      true, () async {
                    final DateTime? d = await showDatePicker(
                        context: sc,
                        initialDate:
                            due ?? DateTime.now().add(const Duration(days: 14)),
                        firstDate: DateTime.now(),
                        lastDate: DateTime.now().add(const Duration(days: 730)));
                    if (d != null) setSheet(() => due = d);
                  }, selected: due != null),
                ]),
                if (errMsg.isNotEmpty) _pv3Err(errMsg),
              ],
              footer: _lzActions(
                  secondary: 'Cancel',
                  onSecondary: () => Navigator.pop(ctx2),
                  primary: sending
                      ? 'Sending\u2026'
                      : (total > 0 ? 'Send ${money(total)}' : 'Send invoice'),
                  icon: Icons.send_rounded,
                  busy: sending,
                  onPrimary: total > 0 ? send : null));
        });
      },
    );
  }
""")

    # F mark invoice paid
    rep(r"""    String method = methods.first;
    final bool? go = await _lzDialog<bool>(
      context: context,
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) => AlertDialog(
          backgroundColor: _lzBg(ivory),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title:  Text('How did they pay?',
              style: TextStyle(
                  color: _lzFg(plum), fontSize: 17, fontWeight: FontWeight.w800)),
          content: SizedBox(
          width: 440,
          child: Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
             Text(
                'This records a payment you already received \u2014 nobody gets charged.',
                style: TextStyle(fontSize: 12, color: _lzFg(muted), height: 1.35)),
            const SizedBox(height: 12),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: methods.map((String m2) {
                final bool sel = method == m2;
                return ChoiceChip(
                  label: Text(m2,
                      style: TextStyle(
                          fontSize: 11.5,
                          color: _lzFg(sel ? ivory : plum),
                          fontWeight: FontWeight.w700)),
                  selected: sel,
                  selectedColor: plum,
                  backgroundColor: _lzBg(Colors.white),
                  side: BorderSide(color: gold.withOpacity(.6)),
                  onSelected: _hb((_) => setD(() => method = m2)),
                );
              }).toList(),
            ),
          ]),
        ),
          actions: <Widget>[
            TextButton(
              onPressed: _h(() => Navigator.of(ctx).pop(false)),
              child:  Text('Cancel',
                  style: TextStyle(color: _lzFg(muted), fontWeight: FontWeight.w700)),
            ),
            FilledButton(
              style: FilledButton.styleFrom(
                  backgroundColor: gold, foregroundColor: plum),
              onPressed: _h(() => Navigator.of(ctx).pop(true)),
              child: const Text('Mark paid',
                  style: TextStyle(fontWeight: FontWeight.w800)),
            ),
          ],
        ),
      ),
    );
    if (go != true) {
      return;
    }
    try {
      await invoiceRef.set(<String, dynamic>{
        'status': 'paid',
        'paidAt': FieldValue.serverTimestamp(),
        'paidVia': method,
      }, SetOptions(merge: true));
      await FirebaseFirestore.instance
          .collection('inquiries')
          .doc(inquiryId)
          .set(<String, dynamic>{
        'invoiceStatus': 'paid',
        'invoiceUpdatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));
      _toast('Marked paid \u2713');
    } catch (e) {
      _toast('Could not mark paid: ' + _errText(e));
    }
  }
""", r"""    String method = methods.first;
    bool busy = false;
    String err = '';
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 480),
      builder: (BuildContext ctx) => StatefulBuilder(
        builder: (BuildContext ctx2, StateSetter setD) {
          Future<void> save() async {
            setD(() {
              busy = true;
              err = '';
            });
            try {
              await invoiceRef.set(<String, dynamic>{
                'status': 'paid',
                'paidAt': FieldValue.serverTimestamp(),
                'paidVia': method,
              }, SetOptions(merge: true));
              await FirebaseFirestore.instance
                  .collection('inquiries')
                  .doc(inquiryId)
                  .set(<String, dynamic>{
                'invoiceStatus': 'paid',
                'invoiceUpdatedAt': FieldValue.serverTimestamp(),
              }, SetOptions(merge: true));
              if (ctx.mounted) Navigator.of(ctx).pop();
              _toast('Marked paid \u2713');
            } catch (e) {
              setD(() {
                busy = false;
                err = 'Could not mark paid: ' + _errText(e);
              });
            }
          }

          return _lzFrame(ctx2,
              icon: Icons.payments_rounded,
              title: 'How did they pay?',
              subtitle:
                  'This records money you already have - nobody gets charged.',
              children: <Widget>[
                const SizedBox(height: 14),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: methods
                      .map((String m2) => _invChip(ctx2, m2, !busy,
                          () => setD(() => method = m2),
                          selected: method == m2))
                      .toList(),
                ),
                const SizedBox(height: 14),
                _lzNote(Icons.info_outline_rounded,
                    'The invoice is saved as paid by $method.'),
                if (err.isNotEmpty) _pv3Err(err),
              ],
              footer: _lzActions(
                  secondary: 'Cancel',
                  onSecondary: () => Navigator.of(ctx).pop(),
                  primary: 'Mark paid',
                  icon: Icons.check_rounded,
                  busy: busy,
                  onPrimary: save));
        },
      ),
    );
  }
""")

    # G connect Whop
    rep(r"""    final TextEditingController bizC = TextEditingController();
    bool busy = false;
    String err = '';
    await _lzSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (BuildContext ctx2) {
        return StatefulBuilder(
            builder: (BuildContext sc, StateSetter setSheet) {
          Widget step(int n, String title, String body, Widget action) {
            return Container(
              margin: const EdgeInsets.only(bottom: 10),
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                  color: _lzBg(Colors.white),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: gold.withOpacity(.55))),
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Row(children: <Widget>[
                      Container(
                          width: 24,
                          height: 24,
                          alignment: Alignment.center,
                          decoration: const BoxDecoration(
                              color: plum, shape: BoxShape.circle),
                          child: Text('$n',
                              style: const TextStyle(
                                  color: gold,
                                  fontSize: 12,
                                  fontWeight: FontWeight.w800))),
                      const SizedBox(width: 9),
                      Text(title,
                          style:  TextStyle(
                              color: _lzFg(ink),
                              fontSize: 14,
                              fontWeight: FontWeight.w800)),
                    ]),
                    const SizedBox(height: 6),
                    Text(body,
                        style:  TextStyle(
                            fontSize: 12, color: _lzFg(muted), height: 1.4)),
                    const SizedBox(height: 10),
                    action,
                  ]),
            );
          }

          return Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 620),
              child: Container(
                margin: EdgeInsets.only(
                    bottom: MediaQuery.of(ctx2).viewInsets.bottom),
                padding: const EdgeInsets.fromLTRB(22, 12, 22, 24),
                decoration:  BoxDecoration(
                    color: _lzBg(ivory),
                    borderRadius:
                        BorderRadius.vertical(top: Radius.circular(26))),
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Center(
                          child: Container(
                              width: 44,
                              height: 4,
                              decoration: BoxDecoration(
                                  color: plum.withOpacity(.2),
                                  borderRadius: BorderRadius.circular(99)))),
                      const SizedBox(height: 16),
                       Text('Get paid through Whop',
                          style: TextStyle(
                              color: _lzFg(ink),
                              fontSize: 18,
                              fontWeight: FontWeight.w800)),
                      const Text('Two steps. Your money never touches Lazo.',
                          style: TextStyle(
                              color: Color(0xFF8A7F90), fontSize: 11.5)),
                      const SizedBox(height: 16),
                      step(
                          1,
                          'Install the Lazo Payments app',
                          'Opens Whop. Sign in (or make a business - it takes a couple of minutes and Whop handles the identity check) and install the app on it.',
                          OutlinedButton.icon(
                            onPressed: _h(installUrl.isEmpty
                                ? null
                                : () => _openUrl(installUrl)),
                            icon:  Icon(Icons.open_in_new_rounded,
                                size: 15, color: _lzFg(plum)),
                            label:  Text('Open Whop',
                                style: TextStyle(
                                    color: _lzFg(plum),
                                    fontSize: 12.5,
                                    fontWeight: FontWeight.w800)),
                            style: OutlinedButton.styleFrom(
                                side: BorderSide(color: plum.withOpacity(.5)),
                                shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(11))),
                          )),
                      step(
                          2,
                          'Paste your business id',
                          'It is in your Whop dashboard address bar and starts with biz_. We check the install and switch you over.',
                          Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                TextField(
                                  controller: bizC,
                                  style:
                                       TextStyle(color: _lzFg(ink), fontSize: 14),
                                  decoration: InputDecoration(
                                    hintText: 'biz_xxxxxxxxxxxx',
                                    hintStyle: TextStyle(
                                        color: _lzFg(ink.withOpacity(.35)),
                                        fontSize: 13.5),
                                    filled: true,
                                    fillColor: _lzBg(ivory),
                                    contentPadding: const EdgeInsets.symmetric(
                                        horizontal: 13, vertical: 12),
                                    border: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(12),
                                        borderSide: BorderSide(
                                            color: plum.withOpacity(.18))),
                                    enabledBorder: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(12),
                                        borderSide: BorderSide(
                                            color: plum.withOpacity(.18))),
                                    focusedBorder: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(12),
                                        borderSide: const BorderSide(
                                            color: plum, width: 1.4)),
                                  ),
                                ),
                                if (err.isNotEmpty)
                                  Padding(
                                    padding: const EdgeInsets.only(top: 8),
                                    child: Text(err,
                                        style:  TextStyle(
                                            color: _lzFg(Color(0xFFB04343)),
                                            fontSize: 12)),
                                  ),
                                const SizedBox(height: 10),
                                ElevatedButton(
                                  onPressed: _h(busy
                                      ? null
                                      : () async {
                                          final String biz = bizC.text.trim();
                                          if (!biz.startsWith('biz_')) {
                                            setSheet(() => err =
                                                'That should start with biz_');
                                            return;
                                          }
                                          setSheet(() {
                                            busy = true;
                                            err = '';
                                          });
                                          try {
                                            final HttpsCallable fn =
                                                FirebaseFunctions.instance
                                                    .httpsCallable(
                                                        'whopVendorConnect');
                                            await fn.call(<String, dynamic>{
                                              'vendorId': vendorId,
                                              'companyId': biz,
                                            });
                                            if (ctx2.mounted) {
                                              Navigator.pop(ctx2);
                                            }
                                            _toast(
                                                'Whop is on. New invoices settle in your balance.');
                                          } on FirebaseFunctionsException catch (e) {
                                            setSheet(() {
                                              busy = false;
                                              err = e.message ??
                                                  'Whop did not confirm the install.';
                                            });
                                          } catch (e) {
                                            setSheet(() {
                                              busy = false;
                                              err = _errText(e);
                                            });
                                          }
                                        }),
                                  style: ElevatedButton.styleFrom(
                                      backgroundColor: plum,
                                      elevation: 0,
                                      padding: const EdgeInsets.symmetric(
                                          horizontal: 18, vertical: 12),
                                      shape: RoundedRectangleBorder(
                                          borderRadius:
                                              BorderRadius.circular(11))),
                                  child: Text(
                                      busy ? 'Checking\u2026' : 'Turn on Whop',
                                      style: const TextStyle(
                                          color: Colors.white,
                                          fontSize: 13,
                                          fontWeight: FontWeight.w800)),
                                ),
                              ])),
                    ],
                  ),
                ),
              ),
            ),
          );
        });
      },
    );
  }
""", r"""    final TextEditingController bizC = TextEditingController();
    bool busy = false;
    String err = '';
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 620),
      builder: (BuildContext ctx2) {
        return StatefulBuilder(
            builder: (BuildContext sc, StateSetter setSheet) {
          Future<void> connect() async {
            final String biz = bizC.text.trim();
            if (!biz.startsWith('biz_')) {
              setSheet(() => err = 'That should start with biz_');
              return;
            }
            setSheet(() {
              busy = true;
              err = '';
            });
            try {
              final HttpsCallable fn =
                  FirebaseFunctions.instance.httpsCallable('whopVendorConnect');
              await fn.call(<String, dynamic>{
                'vendorId': vendorId,
                'companyId': biz,
              });
              if (ctx2.mounted) {
                Navigator.pop(ctx2);
              }
              _toast('Whop is on. New invoices settle in your balance.');
            } on FirebaseFunctionsException catch (e) {
              setSheet(() {
                busy = false;
                err = e.message ?? 'Whop did not confirm the install.';
              });
            } catch (e) {
              setSheet(() {
                busy = false;
                err = _errText(e);
              });
            }
          }

          return _lzFrame(sc,
              icon: Icons.bolt_rounded,
              title: 'Get paid through Whop',
              subtitle: 'Two steps. Your money never touches Lazo.',
              children: <Widget>[
                const SizedBox(height: 14),
                _pv3Step(
                    1,
                    'Install the Lazo Payments app',
                    'Opens Whop. Sign in or make a business (a couple of minutes - Whop handles the identity check), then install the app on it.',
                    Align(
                      alignment: Alignment.centerLeft,
                      child: OutlinedButton.icon(
                        onPressed: _h(installUrl.isEmpty
                            ? null
                            : () => _openUrl(installUrl)),
                        icon: Icon(Icons.open_in_new_rounded,
                            size: 15, color: _lzFg(plum)),
                        label: Text('Open Whop',
                            style: TextStyle(
                                color: _lzFg(plum),
                                fontSize: 13,
                                fontWeight: FontWeight.w700)),
                        style: OutlinedButton.styleFrom(
                            side: BorderSide(color: _lzLine(gold)),
                            padding: const EdgeInsets.symmetric(
                                horizontal: 14, vertical: 11),
                            shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(11))),
                      ),
                    )),
                _pv3Step(
                    2,
                    'Paste your business id',
                    'It\u2019s in your Whop dashboard address bar and starts with biz_. We check the install and switch you over.',
                    TextField(
                      controller: bizC,
                      autocorrect: false,
                      textInputAction: TextInputAction.done,
                      onChanged: (_) => setSheet(() => err = ''),
                      onSubmitted: (_) {
                        if (!busy && bizC.text.trim().isNotEmpty) connect();
                      },
                      style: TextStyle(color: _lzFg(ink), fontSize: 14),
                      decoration:
                          _epDeco('Business id', 'biz_xxxxxxxxxxxx'),
                    )),
                if (err.isNotEmpty) _pv3Err(err),
              ],
              footer: _lzActions(
                  secondary: 'Not now',
                  onSecondary: () => Navigator.pop(ctx2),
                  primary: busy ? 'Checking\u2026' : 'Turn on Whop',
                  icon: Icons.bolt_rounded,
                  busy: busy,
                  onPrimary: bizC.text.trim().isEmpty ? null : connect));
        });
      },
    );
  }
""")

    # H1 plan frame + send()
    rep(r"""    await _lzSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (BuildContext ctx2) {
        return StatefulBuilder(
            builder: (BuildContext sc, StateSetter setSheet) {
          final num total =
              num.tryParse(totalC.text.replaceAll(',', '').trim()) ?? 0;
          num sum = 0;
          for (final Map<String, dynamic> r in rows) {
            sum += num.tryParse((r['amount'] as TextEditingController)
                    .text
                    .replaceAll(',', '')
                    .trim()) ??
                0;
          }
          final num drift = total - sum;

          Widget chip(String label, bool on, VoidCallback onTap) {
            return InkWell(
              onTap: onTap,
              borderRadius: BorderRadius.circular(999),
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                decoration: BoxDecoration(
                    color: _lzBg(on ? plum : Colors.white),
                    borderRadius: BorderRadius.circular(999),
                    border:
                        Border.all(color: _lzLine(on ? plum : plum.withOpacity(.25)))),
                child: Text(label,
                    style: TextStyle(
                        color: _lzFg(on ? Colors.white : plum),
                        fontSize: 12,
                        fontWeight: FontWeight.w800)),
              ),
            );
          }

          Widget section(String t) => Padding(
                padding: const EdgeInsets.only(top: 14, bottom: 7),
                child: Text(t.toUpperCase(),
                    style:  TextStyle(
                        color: _lzFg(muted),
                        fontSize: 9.5,
                        letterSpacing: 1.4,
                        fontWeight: FontWeight.w800)),
              );

          return Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 720),
              child: Container(
                margin: EdgeInsets.only(
                    bottom: MediaQuery.of(ctx2).viewInsets.bottom),
                padding: const EdgeInsets.fromLTRB(22, 12, 22, 24),
                decoration:  BoxDecoration(
                    color: _lzBg(ivory),
                    borderRadius:
                        BorderRadius.vertical(top: Radius.circular(26))),
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Center(
                          child: Container(
                              width: 44,
                              height: 4,
                              decoration: BoxDecoration(
                                  color: plum.withOpacity(.2),
                                  borderRadius: BorderRadius.circular(99)))),
                      const SizedBox(height: 16),
                      Row(children: <Widget>[
                        Container(
                          width: 38,
                          height: 38,
                          decoration: BoxDecoration(
                              gradient: const LinearGradient(
                                  colors: <Color>[plumDeep, plum]),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: gold.withOpacity(.7))),
                          child: const Icon(Icons.calendar_month_rounded,
                              color: gold, size: 19),
                        ),
                        const SizedBox(width: 11),
                         Expanded(
                          child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                Text('Set up a payment plan',
                                    style: TextStyle(
                                        color: _lzFg(ink),
                                        fontSize: 18,
                                        fontWeight: FontWeight.w800)),
                                Text(
                                    'Each payment is its own invoice with a due date. Reminders go out three days before, on the day, and weekly after.',
                                    style: TextStyle(
                                        color: Color(0xFF8A7F90),
                                        fontSize: 11.5,
                                        height: 1.3)),
                              ]),
                        ),
                      ]),
                      const SizedBox(height: 16),
""", r"""    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 720),
      builder: (BuildContext ctx2) {
        return StatefulBuilder(
            builder: (BuildContext sc, StateSetter setSheet) {
          final num total =
              num.tryParse(totalC.text.replaceAll(',', '').trim()) ?? 0;
          num sum = 0;
          for (final Map<String, dynamic> r in rows) {
            sum += num.tryParse((r['amount'] as TextEditingController)
                    .text
                    .replaceAll(',', '')
                    .trim()) ??
                0;
          }
          final num drift = total - sum;

          Widget chip(String label, bool on, VoidCallback onTap) {
            return _Press(
              tick: _Tick.select,
              onTap: onTap,
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 160),
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                decoration: BoxDecoration(
                    color: _lzBg(on ? plum : Colors.white),
                    borderRadius: BorderRadius.circular(999),
                    border:
                        Border.all(color: _lzLine(on ? plum : plum.withOpacity(.25)))),
                child: Text(label,
                    style: TextStyle(
                        color: _lzFg(on ? Colors.white : plum),
                        fontSize: 12.5,
                        fontWeight: FontWeight.w700)),
              ),
            );
          }

          Widget section(String t) => _lzSection(t);

          Future<void> send() async {
            if (total <= 0) {
              setSheet(() => err = 'Enter the total.');
              return;
            }
            if (rows.isEmpty) {
              setSheet(() => err = 'Pick a schedule or add a payment.');
              return;
            }
            if (drift.abs() > 1) {
              setSheet(
                  () => err = 'The payments need to add up to the total.');
              return;
            }
            setSheet(() {
              sending = true;
              err = '';
            });
            try {
              final List<Map<String, dynamic>> sched =
                  rows.map((Map<String, dynamic> r) {
                final DateTime d = r['due'] as DateTime;
                return <String, dynamic>{
                  'label': (r['label'] as TextEditingController).text.trim(),
                  'amount': num.tryParse((r['amount'] as TextEditingController)
                          .text
                          .replaceAll(',', '')
                          .trim()) ??
                      0,
                  'dueDate':
                      '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}',
                };
              }).toList();
              final HttpsCallable fn =
                  FirebaseFunctions.instance.httpsCallable('planCreate');
              await fn.call(<String, dynamic>{
                'inquiryId': inquiryId,
                'vendorId': (inq['vendorId'] ?? '') as String,
                'title': titleC.text.trim(),
                'total': total,
                'schedule': sched,
                'lateFee': feeType == 'none'
                    ? null
                    : <String, dynamic>{
                        'type': feeType,
                        'amount': num.tryParse(feeC.text.trim()) ?? 0,
                        'graceDays': int.tryParse(graceC.text.trim()) ?? 0,
                        'every': feeEvery,
                      },
                'tipAllowed': tips,
                'autopay': autopay,
              });
              if (ctx2.mounted) Navigator.pop(ctx2);
              _toast('Payment plan is out - every payment is in the thread.');
            } on FirebaseFunctionsException catch (e) {
              setSheet(() {
                sending = false;
                err = e.message ?? 'Could not create the plan.';
              });
            } catch (e) {
              setSheet(() {
                sending = false;
                err = _errText(e);
              });
            }
          }

          return _lzFrame(sc,
              icon: Icons.calendar_month_rounded,
              title: 'Set up a payment plan',
              subtitle:
                  'Each payment is its own invoice. Reminders go out three days before, on the day, and weekly after.',
              children: <Widget>[
                      const SizedBox(height: 14),
""")

    # H2 plan title/total fields
    rep(r"""                      Row(children: <Widget>[
                        Expanded(
                            flex: 3,
                            child: TextField(
                                controller: titleC,
                                style:
                                     TextStyle(color: _lzFg(ink), fontSize: 14),
                                decoration: deco('Plan title'))),
                        const SizedBox(width: 10),
                        Expanded(
                            flex: 2,
                            child: TextField(
                                controller: totalC,
                                keyboardType: TextInputType.number,
                                onChanged: (_) => setSheet(() {
                                      if (preset.isNotEmpty) {
                                        final num t = num.tryParse(totalC.text
                                                .replaceAll(',', '')
                                                .trim()) ??
                                            0;
                                        if (t > 0) buildPreset(preset, t);
                                      }
                                    }),
                                style:
                                     TextStyle(color: _lzFg(ink), fontSize: 14),
                                decoration: deco('Total \u0024'))),
                      ]),
""", r"""                      Row(children: <Widget>[
                        Expanded(
                            flex: 3,
                            child: TextField(
                                controller: titleC,
                                textInputAction: TextInputAction.next,
                                style:
                                     TextStyle(color: _lzFg(ink), fontSize: 14),
                                decoration:
                                    _epDeco('Plan title', 'Payment plan'))),
                        const SizedBox(width: 10),
                        Expanded(
                            flex: 2,
                            child: TextField(
                                controller: totalC,
                                autofocus: prefTotal <= 0,
                                keyboardType: TextInputType.number,
                                onChanged: (_) => setSheet(() {
                                      if (preset.isNotEmpty) {
                                        final num t = num.tryParse(totalC.text
                                                .replaceAll(',', '')
                                                .trim()) ??
                                            0;
                                        if (t > 0) buildPreset(preset, t);
                                      }
                                    }),
                                style: TextStyle(
                                    color: _lzFg(ink),
                                    fontSize: 14,
                                    fontWeight: FontWeight.w700),
                                decoration: _epDeco('Total', '4800').copyWith(
                                    prefixText: '\$ ',
                                    prefixStyle: TextStyle(
                                        color: _lzFg(plum),
                                        fontSize: 14,
                                        fontWeight: FontWeight.w700)))),
                      ]),
                      if (prefTotal > 0) ...<Widget>[
                        const SizedBox(height: 6),
                        Text('Total filled in from this thread.',
                            style:
                                TextStyle(fontSize: 12, color: _lzFg(muted))),
                      ],
""")

    # H4 plan late fee row wraps
    rep(r"""                        Row(children: <Widget>[
                          SizedBox(
                              width: 96,
                              child: TextField(
                                  controller: feeC,
                                  keyboardType: TextInputType.number,
                                  style:  TextStyle(
                                      color: _lzFg(ink), fontSize: 13.5),
                                  decoration:
                                      deco(feeType == 'pct' ? '%' : '\u0024'))),
                          const SizedBox(width: 8),
                           Text('after',
                              style: TextStyle(color: _lzFg(muted), fontSize: 12.5)),
                          const SizedBox(width: 8),
                          SizedBox(
                              width: 64,
                              child: TextField(
                                  controller: graceC,
                                  keyboardType: TextInputType.number,
                                  style:  TextStyle(
                                      color: _lzFg(ink), fontSize: 13.5),
                                  decoration: deco('days'))),
                          const SizedBox(width: 8),
                           Text('days,',
                              style: TextStyle(color: _lzFg(muted), fontSize: 12.5)),
                          const SizedBox(width: 8),
                          chip('once', feeEvery == 'once',
                              () => setSheet(() => feeEvery = 'once')),
                          const SizedBox(width: 6),
                          chip('every week', feeEvery == 'weekly',
                              () => setSheet(() => feeEvery = 'weekly')),
                        ]),
""", r"""                        Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            crossAxisAlignment: WrapCrossAlignment.center,
                            children: <Widget>[
                              SizedBox(
                                  width: 96,
                                  child: TextField(
                                      controller: feeC,
                                      keyboardType: TextInputType.number,
                                      style: TextStyle(
                                          color: _lzFg(ink), fontSize: 13.5),
                                      decoration: deco(
                                          feeType == 'pct' ? '%' : '\$'))),
                              Text('after',
                                  style: TextStyle(
                                      color: _lzFg(muted), fontSize: 12.5)),
                              SizedBox(
                                  width: 64,
                                  child: TextField(
                                      controller: graceC,
                                      keyboardType: TextInputType.number,
                                      style: TextStyle(
                                          color: _lzFg(ink), fontSize: 13.5),
                                      decoration: deco('days'))),
                              Text('days,',
                                  style: TextStyle(
                                      color: _lzFg(muted), fontSize: 12.5)),
                              chip('once', feeEvery == 'once',
                                  () => setSheet(() => feeEvery = 'once')),
                              chip('every week', feeEvery == 'weekly',
                                  () => setSheet(() => feeEvery = 'weekly')),
                            ]),
""")

    # H3 plan footer
    rep(r"""                      const SizedBox(height: 6),
                       Text(
                          'Autopay today means the pay link lands in their thread and inbox on the due date - one tap. Card-on-file charging follows once Whop confirms it.',
                          style: TextStyle(
                              fontSize: 10.5, color: _lzFg(muted), height: 1.35)),
                      if (err.isNotEmpty)
                        Padding(
                          padding: const EdgeInsets.only(top: 10),
                          child: Text(err,
                              style:  TextStyle(
                                  color: _lzFg(Color(0xFFB04343)), fontSize: 12)),
                        ),
                      const SizedBox(height: 16),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton(
                          onPressed: _h(
                              sending
                                  ? null
                                  : () async {
                                      if (total <= 0) {
                                        setSheet(
                                            () => err = 'Enter the total.');
                                        return;
                                      }
                                      if (rows.isEmpty) {
                                        setSheet(() => err =
                                            'Pick a schedule or add a payment.');
                                        return;
                                      }
                                      if (drift.abs() > 1) {
                                        setSheet(() => err =
                                            'The payments need to add up to the total.');
                                        return;
                                      }
                                      setSheet(() {
                                        sending = true;
                                        err = '';
                                      });
                                      try {
                                        final List<Map<String, dynamic>> sched =
                                            rows.map((Map<String, dynamic> r) {
                                          final DateTime d =
                                              r['due'] as DateTime;
                                          return <String, dynamic>{
                                            'label': (r['label']
                                                    as TextEditingController)
                                                .text
                                                .trim(),
                                            'amount': num.tryParse((r['amount']
                                                        as TextEditingController)
                                                    .text
                                                    .replaceAll(',', '')
                                                    .trim()) ??
                                                0,
                                            'dueDate':
                                                '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}',
                                          };
                                        }).toList();
                                        final HttpsCallable fn =
                                            FirebaseFunctions.instance
                                                .httpsCallable('planCreate');
                                        await fn.call(<String, dynamic>{
                                          'inquiryId': inquiryId,
                                          'vendorId':
                                              (inq['vendorId'] ?? '') as String,
                                          'title': titleC.text.trim(),
                                          'total': total,
                                          'schedule': sched,
                                          'lateFee': feeType == 'none'
                                              ? null
                                              : <String, dynamic>{
                                                  'type': feeType,
                                                  'amount': num.tryParse(
                                                          feeC.text.trim()) ??
                                                      0,
                                                  'graceDays': int.tryParse(
                                                          graceC.text.trim()) ??
                                                      0,
                                                  'every': feeEvery,
                                                },
                                          'tipAllowed': tips,
                                          'autopay': autopay,
                                        });
                                        if (ctx2.mounted) Navigator.pop(ctx2);
                                        _toast(
                                            'Payment plan is out - every payment is in the thread.');
                                      } on FirebaseFunctionsException catch (e) {
                                        setSheet(() {
                                          sending = false;
                                          err = e.message ??
                                              'Could not create the plan.';
                                        });
                                      } catch (e) {
                                        setSheet(() {
                                          sending = false;
                                          err = _errText(e);
                                        });
                                      }
                                    },
                              _Tick.medium),
                          style: ElevatedButton.styleFrom(
                              backgroundColor: plum,
                              elevation: 0,
                              padding: const EdgeInsets.symmetric(vertical: 14),
                              shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(12))),
                          child: Text(
                              sending
                                  ? 'Sending\u2026'
                                  : rows.isEmpty
                                      ? 'Send the plan'
                                      : 'Send ${rows.length} payment${rows.length == 1 ? '' : 's'}',
                              style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 14,
                                  fontWeight: FontWeight.w800)),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          );
        });
      },
    );
  }
""", r"""                      const SizedBox(height: 12),
                      _lzNote(Icons.autorenew_rounded,
                          'Autopay today means the pay link lands in their thread and inbox on the due date - one tap. Card-on-file charging follows once Whop confirms it.'),
                      if (err.isNotEmpty) _pv3Err(err),
              ],
              footer: _lzActions(
                  secondary: 'Cancel',
                  onSecondary: () => Navigator.pop(ctx2),
                  primary: sending
                      ? 'Sending\u2026'
                      : rows.isEmpty
                          ? 'Send the plan'
                          : 'Send ${rows.length} payment${rows.length == 1 ? '' : 's'}',
                  icon: Icons.send_rounded,
                  busy: sending,
                  onPrimary: total > 0 && rows.isNotEmpty && drift.abs() <= 1
                      ? send
                      : null));
        });
      },
    );
  }
""")

    # I lead form
    rep(r"""    await _lzSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: _lzBg(ivory),
      constraints: const BoxConstraints(maxWidth: 640),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (BuildContext ctx) =>
          StatefulBuilder(builder: (BuildContext sc, StateSetter setSheet) {
        return SafeArea(
          child: Padding(
            padding: EdgeInsets.fromLTRB(
                22, 18, 22, 22 + MediaQuery.of(ctx).viewInsets.bottom),
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Row(children: <Widget>[
                    Expanded(
                        child: Text('Lead form for your website',
                            style: _serif(size: 24))),
                    Switch(
                        value: enabled,
                        activeColor: vGreen,
                        onChanged: _hb((bool v) async {
                          setSheet(() => enabled = v);
                          await save();
                          _toast(v ? 'Form is on.' : 'Form is off.');
                        })),
                  ]),
                  const SizedBox(height: 4),
                   Text(
                      'Inquiries from your own site, your Instagram bio or a QR code land here as threads - with the page and campaign they came from. You reply once; they get it by text and email, and their texts come back into the thread.',
                      style:
                          TextStyle(fontSize: 12.5, color: _lzFg(muted), height: 1.4)),
                  const SizedBox(height: 14),
                   Text('ON YOUR WEBSITE',
                      style: TextStyle(
                          color: _lzFg(muted),
                          fontSize: 9.5,
                          letterSpacing: 1.4,
                          fontWeight: FontWeight.w800)),
                  const SizedBox(height: 6),
                  codeBox(snippet),
                  const SizedBox(height: 8),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      style: FilledButton.styleFrom(
                          backgroundColor: gold,
                          foregroundColor: plumDeep,
                          elevation: 0,
                          padding: const EdgeInsets.symmetric(vertical: 12)),
                      onPressed: _h(() async {
                        await Clipboard.setData(ClipboardData(text: snippet));
                        _toast('Code copied \u2713');
                      }),
                      icon: const Icon(Icons.copy_rounded, size: 16),
                      label: const Text('Copy the code',
                          style: TextStyle(fontWeight: FontWeight.w800)),
                    ),
                  ),
                  const SizedBox(height: 6),
                   Text(
                      'Paste it where the form should appear - Squarespace and Wix: a Code / Embed block; WordPress: a Custom HTML block; Showit: an Embed Code element. It matches your page; add data-accent="#hex" to recolor the button.',
                      style:
                          TextStyle(fontSize: 11.5, color: _lzFg(muted), height: 1.4)),
                  const SizedBox(height: 14),
                   Text('OR JUST A LINK',
                      style: TextStyle(
                          color: _lzFg(muted),
                          fontSize: 9.5,
                          letterSpacing: 1.4,
                          fontWeight: FontWeight.w800)),
                  const SizedBox(height: 6),
                  codeBox(hosted),
                  const SizedBox(height: 8),
                  Row(children: <Widget>[
                    Expanded(
                      child: OutlinedButton.icon(
                        style: OutlinedButton.styleFrom(
                            foregroundColor: _lzFg(plum),
                            side: BorderSide(color: gold.withOpacity(.8)),
                            padding: const EdgeInsets.symmetric(vertical: 12)),
                        onPressed: _h(() async {
                          await Clipboard.setData(ClipboardData(text: hosted));
                          _toast('Link copied \u2713');
                        }),
                        icon: const Icon(Icons.link_rounded, size: 16),
                        label: const Text('Copy link',
                            style: TextStyle(fontWeight: FontWeight.w800)),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: OutlinedButton.icon(
                        style: OutlinedButton.styleFrom(
                            foregroundColor: _lzFg(plum),
                            side: BorderSide(color: gold.withOpacity(.8)),
                            padding: const EdgeInsets.symmetric(vertical: 12)),
                        onPressed: _h(() => _openUrl(hosted)),
                        icon: const Icon(Icons.open_in_new_rounded, size: 16),
                        label: const Text('Preview',
                            style: TextStyle(fontWeight: FontWeight.w800)),
                      ),
                    ),
                  ]),
                  const SizedBox(height: 6),
                   Text(
                      'Use the link as a button on any site builder, in your Instagram bio, or as a QR code on a bridal-show card.',
                      style:
                          TextStyle(fontSize: 11.5, color: _lzFg(muted), height: 1.4)),
                  const SizedBox(height: 14),
                   Text('AFTER THEY SEND',
                      style: TextStyle(
                          color: _lzFg(muted),
                          fontSize: 9.5,
                          letterSpacing: 1.4,
                          fontWeight: FontWeight.w800)),
                  const SizedBox(height: 6),
                  TextField(
                    controller: thanksC,
                    style:  TextStyle(color: _lzFg(ink), fontSize: 13.5),
                    onSubmitted: (_) => save(),
                    onTapOutside: (_) => save(),
                    decoration: InputDecoration(
                      hintText: 'Thank-you message (optional)',
                      hintStyle:
                          TextStyle(color: _lzFg(ink.withOpacity(.35)), fontSize: 13),
                      filled: true,
                      fillColor: _lzBg(Colors.white),
                      isDense: true,
                      contentPadding: const EdgeInsets.symmetric(
                          horizontal: 12, vertical: 11),
                      border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12),
                          borderSide:  BorderSide(color: _lzLine(goldLine))),
                      enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12),
                          borderSide:  BorderSide(color: _lzLine(goldLine))),
                    ),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: redirectC,
                    style:  TextStyle(color: _lzFg(ink), fontSize: 13.5),
                    keyboardType: TextInputType.url,
                    onSubmitted: (_) => save(),
                    onTapOutside: (_) => save(),
                    decoration: InputDecoration(
                      hintText:
                          'Or send them to a page: https://yoursite.com/thank-you',
                      hintStyle:
                          TextStyle(color: _lzFg(ink.withOpacity(.35)), fontSize: 13),
                      filled: true,
                      fillColor: _lzBg(Colors.white),
                      isDense: true,
                      contentPadding: const EdgeInsets.symmetric(
                          horizontal: 12, vertical: 11),
                      border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12),
                          borderSide:  BorderSide(color: _lzLine(goldLine))),
                      enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12),
                          borderSide:  BorderSide(color: _lzLine(goldLine))),
                    ),
                  ),
                  const SizedBox(height: 6),
                   Text(
                      'A thank-you page lets Meta and Google count the lead as a conversion. The form also fires a Lead event to your pixel if it is on the page.',
                      style:
                          TextStyle(fontSize: 11.5, color: _lzFg(muted), height: 1.4)),
                ],
              ),
            ),
          ),
        );
      }),
    );
    await save();
  }
""", r"""    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 640),
      builder: (BuildContext ctx) =>
          StatefulBuilder(builder: (BuildContext sc, StateSetter setSheet) {
        Widget smallBtn(IconData ic, String label, VoidCallback onTap) =>
            TextButton.icon(
              style: TextButton.styleFrom(
                  foregroundColor: _lzFg(plum),
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 8)),
              onPressed: _h(onTap),
              icon: Icon(ic, size: 16),
              label: Text(label,
                  style: const TextStyle(
                      fontSize: 13, fontWeight: FontWeight.w700)),
            );
        return _lzFrame(sc,
            icon: Icons.web_rounded,
            title: 'Lead form',
            subtitle:
                'Inquiries from your site, Instagram bio or a QR code land here as threads.',
            headerExtra: Container(
              padding: const EdgeInsets.fromLTRB(14, 2, 6, 2),
              decoration: BoxDecoration(
                  color: _lzBg(card),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: _lzLine(goldLine))),
              child: Row(children: <Widget>[
                Icon(
                    enabled
                        ? Icons.check_circle_rounded
                        : Icons.pause_circle_outline_rounded,
                    size: 18,
                    color: _lzFg(enabled ? vGreen : muted)),
                const SizedBox(width: 8),
                Expanded(
                    child: Text(enabled ? 'Taking inquiries' : 'Turned off',
                        style: TextStyle(
                            fontSize: 13.5,
                            fontWeight: FontWeight.w700,
                            color: _lzFg(ink)))),
                Switch(
                    value: enabled,
                    activeColor: vGreen,
                    onChanged: _hb((bool v) async {
                      setSheet(() => enabled = v);
                      await save();
                      _toast(v ? 'Form is on.' : 'Form is off.');
                    })),
              ]),
            ),
            children: <Widget>[
              const SizedBox(height: 12),
              _lzNote(Icons.forum_outlined,
                  'You reply once - they get it by text and email, and their texts come back into the thread, with the page and campaign they came from.'),
              _lzSection('On your website'),
              codeBox(snippet),
              const SizedBox(height: 8),
              Text(
                  'Paste it where the form should go: a Code or Embed block on Squarespace and Wix, Custom HTML on WordPress, an Embed Code element on Showit. Add data-accent="#hex" to recolor the button.',
                  style: TextStyle(
                      fontSize: 12, color: _lzFg(muted), height: 1.45)),
              _lzSection('Or just a link'),
              codeBox(hosted),
              Row(children: <Widget>[
                smallBtn(Icons.link_rounded, 'Copy link', () async {
                  await Clipboard.setData(ClipboardData(text: hosted));
                  _toast('Link copied \u2713');
                }),
                smallBtn(Icons.open_in_new_rounded, 'Preview',
                    () => _openUrl(hosted)),
              ]),
              Text(
                  'Use it as a button on any site, in your Instagram bio, or as a QR code on a bridal-show card.',
                  style: TextStyle(
                      fontSize: 12, color: _lzFg(muted), height: 1.45)),
              _lzSection('After they send'),
              TextField(
                controller: thanksC,
                textInputAction: TextInputAction.next,
                style: TextStyle(color: _lzFg(ink), fontSize: 13.5),
                onSubmitted: (_) => save(),
                onTapOutside: (_) => save(),
                decoration: _epDeco('Thank-you message (optional)',
                    'Thank you - I\u2019ll be in touch within a day.'),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: redirectC,
                style: TextStyle(color: _lzFg(ink), fontSize: 13.5),
                keyboardType: TextInputType.url,
                onSubmitted: (_) => save(),
                onTapOutside: (_) => save(),
                decoration: _epDeco('Or a thank-you page (optional)',
                    'https://yoursite.com/thank-you'),
              ),
              const SizedBox(height: 10),
              _lzNote(Icons.insights_rounded,
                  'A thank-you page lets Meta and Google count the lead as a conversion. The form also fires a Lead event to your pixel if it is on the page.'),
            ],
            footer: _lzActions(
                secondary: 'Done',
                onSecondary: () => Navigator.pop(ctx),
                primary: 'Copy the code',
                icon: Icons.copy_rounded,
                onPrimary: () async {
                  await Clipboard.setData(ClipboardData(text: snippet));
                  _toast('Code copied \u2713');
                }));
      }),
    );
    await save();
  }
""")

    # J stages
    rep(r"""    await _lzSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: _lzBg(ivory),
      constraints: const BoxConstraints(maxWidth: 560),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (BuildContext ctx) =>
          StatefulBuilder(builder: (BuildContext sc, StateSetter setSheet) {
        return SafeArea(
          child: Padding(
            padding: EdgeInsets.fromLTRB(
                22, 18, 22, 22 + MediaQuery.of(ctx).viewInsets.bottom),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('Your stages', style: _serif(size: 24)),
                const SizedBox(height: 4),
                 Text(
                    'New and Talking come first; Booked, Delivered and Lost come last and follow the real status. Add the steps in between that match how you work.',
                    style:
                        TextStyle(fontSize: 12.5, color: _lzFg(muted), height: 1.4)),
                const SizedBox(height: 12),
                if (custom.isEmpty)
                   Text(
                      'No custom stages yet - try "Tour scheduled" or "Waiting on deposit".',
                      style: TextStyle(fontSize: 12, color: _lzFg(muted))),
                ...custom
                    .asMap()
                    .entries
                    .map((MapEntry<int, Map<String, dynamic>> e) {
                  final int i = e.key;
                  return Container(
                    margin: const EdgeInsets.only(bottom: 6),
                    padding:
                        const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    decoration: BoxDecoration(
                        color: _lzBg(Colors.white),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: _lzLine(goldLine))),
                    child: Row(children: <Widget>[
                      Expanded(
                        child: Text((e.value['label'] ?? '').toString(),
                            style:  TextStyle(
                                color: _lzFg(ink),
                                fontSize: 13.5,
                                fontWeight: FontWeight.w700)),
                      ),
                      IconButton(
                        visualDensity: VisualDensity.compact,
                        onPressed: _h(i == 0
                            ? null
                            : () => setSheet(() {
                                  final Map<String, dynamic> x =
                                      custom.removeAt(i);
                                  custom.insert(i - 1, x);
                                })),
                        icon:  Icon(Icons.arrow_upward_rounded,
                            size: 16, color: _lzFg(muted)),
                      ),
                      IconButton(
                        visualDensity: VisualDensity.compact,
                        onPressed: _h(i == custom.length - 1
                            ? null
                            : () => setSheet(() {
                                  final Map<String, dynamic> x =
                                      custom.removeAt(i);
                                  custom.insert(i + 1, x);
                                })),
                        icon:  Icon(Icons.arrow_downward_rounded,
                            size: 16, color: _lzFg(muted)),
                      ),
                      IconButton(
                        visualDensity: VisualDensity.compact,
                        onPressed: _h(() => setSheet(() => custom.removeAt(i))),
                        icon:  Icon(Icons.close_rounded,
                            size: 16, color: _lzFg(muted)),
                      ),
                    ]),
                  );
                }),
                const SizedBox(height: 8),
                Row(children: <Widget>[
                  Expanded(
                    child: TextField(
                      controller: addC,
                      style:  TextStyle(color: _lzFg(ink), fontSize: 13.5),
                      decoration: InputDecoration(
                        hintText: 'New stage name',
                        hintStyle: TextStyle(
                            color: _lzFg(ink.withOpacity(.35)), fontSize: 13),
                        isDense: true,
                        filled: true,
                        fillColor: _lzBg(Colors.white),
                        contentPadding: const EdgeInsets.symmetric(
                            horizontal: 12, vertical: 11),
                        border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                            borderSide:  BorderSide(color: _lzLine(goldLine))),
                        enabledBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                            borderSide:  BorderSide(color: _lzLine(goldLine))),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  FilledButton(
                    style: FilledButton.styleFrom(
                        backgroundColor: plum,
                        elevation: 0,
                        padding: const EdgeInsets.symmetric(
                            horizontal: 14, vertical: 12),
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(11))),
                    onPressed: _h(() {
                      final String label = addC.text.trim();
                      if (label.isEmpty || custom.length >= 8) return;
                      setSheet(() {
                        custom.add(<String, dynamic>{
                          'key': 'c_' + _randomCode(6).toLowerCase(),
                          'label': label,
                        });
                        addC.clear();
                      });
                    }),
                    child: const Text('Add',
                        style: TextStyle(
                            color: Colors.white, fontWeight: FontWeight.w800)),
                  ),
                ]),
                const SizedBox(height: 14),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    style: FilledButton.styleFrom(
                        backgroundColor: gold,
                        foregroundColor: plumDeep,
                        elevation: 0,
                        padding: const EdgeInsets.symmetric(vertical: 13)),
                    onPressed: _h(() async {
                      await save();
                      if (ctx.mounted) Navigator.pop(ctx);
                      _toast('Stages saved');
                    }),
                    child: const Text('Save stages',
                        style: TextStyle(fontWeight: FontWeight.w800)),
                  ),
                ),
              ],
            ),
          ),
        );
      }),
    );
  }
""", r"""    bool saving = false;
    String err = '';
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext ctx) =>
          StatefulBuilder(builder: (BuildContext sc, StateSetter setSheet) {
        void add() {
          final String label = addC.text.trim();
          if (label.isEmpty || custom.length >= 8) return;
          setSheet(() {
            custom.add(<String, dynamic>{
              'key': 'c_' + _randomCode(6).toLowerCase(),
              'label': label,
            });
            addC.clear();
          });
        }

        Widget fixed(List<String> names) =>
            Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
              for (final String n in names)
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 11, vertical: 6),
                  decoration: BoxDecoration(
                      color: _lzBg(const Color(0xFFF6EEDF)),
                      borderRadius: BorderRadius.circular(999)),
                  child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
                    Icon(Icons.lock_outline_rounded,
                        size: 12, color: _lzFg(muted)),
                    const SizedBox(width: 5),
                    Text(n,
                        style: TextStyle(
                            fontSize: 12.5,
                            fontWeight: FontWeight.w700,
                            color: _lzFg(muted))),
                  ]),
                ),
            ]);

        return _lzFrame(sc,
            icon: Icons.view_kanban_rounded,
            title: 'Your stages',
            subtitle:
                'Add the steps between Talking and Booked that match how you work.',
            children: <Widget>[
              _lzSection('Always first'),
              fixed(<String>['New', 'Talking']),
              _lzSection('Yours', trailing: '${custom.length} of 8'),
              if (custom.isEmpty)
                Container(
                  padding: const EdgeInsets.fromLTRB(14, 14, 14, 14),
                  margin: const EdgeInsets.only(bottom: 8),
                  decoration: BoxDecoration(
                      color: _lzBg(card),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: _lzLine(goldLine))),
                  child: Row(children: <Widget>[
                    Icon(Icons.add_road_rounded, size: 20, color: _lzFg(plum)),
                    const SizedBox(width: 10),
                    Expanded(
                        child: Text(
                            'None yet - try Tour scheduled or Waiting on deposit.',
                            style: TextStyle(
                                fontSize: 13,
                                color: _lzFg(muted),
                                height: 1.35))),
                  ]),
                ),
              ...custom
                  .asMap()
                  .entries
                  .map((MapEntry<int, Map<String, dynamic>> e) {
                final int i = e.key;
                return Container(
                  margin: const EdgeInsets.only(bottom: 6),
                  padding: const EdgeInsets.fromLTRB(14, 4, 4, 4),
                  decoration: BoxDecoration(
                      color: _lzBg(card),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: _lzLine(goldLine))),
                  child: Row(children: <Widget>[
                    Expanded(
                      child: Text((e.value['label'] ?? '').toString(),
                          style: TextStyle(
                              color: _lzFg(ink),
                              fontSize: 14,
                              fontWeight: FontWeight.w600)),
                    ),
                    IconButton(
                      tooltip: 'Move up',
                      visualDensity: VisualDensity.compact,
                      onPressed: _h(i == 0
                          ? null
                          : () => setSheet(() {
                                final Map<String, dynamic> x =
                                    custom.removeAt(i);
                                custom.insert(i - 1, x);
                              })),
                      icon: Icon(Icons.arrow_upward_rounded,
                          size: 16, color: _lzFg(muted)),
                    ),
                    IconButton(
                      tooltip: 'Move down',
                      visualDensity: VisualDensity.compact,
                      onPressed: _h(i == custom.length - 1
                          ? null
                          : () => setSheet(() {
                                final Map<String, dynamic> x =
                                    custom.removeAt(i);
                                custom.insert(i + 1, x);
                              })),
                      icon: Icon(Icons.arrow_downward_rounded,
                          size: 16, color: _lzFg(muted)),
                    ),
                    IconButton(
                      tooltip: 'Remove',
                      visualDensity: VisualDensity.compact,
                      onPressed: _h(() => setSheet(() => custom.removeAt(i))),
                      icon: Icon(Icons.close_rounded,
                          size: 16, color: _lzFg(muted)),
                    ),
                  ]),
                );
              }),
              if (custom.length < 8) ...<Widget>[
                const SizedBox(height: 6),
                Row(children: <Widget>[
                  Expanded(
                    child: TextField(
                      controller: addC,
                      autofocus: custom.isEmpty,
                      textInputAction: TextInputAction.done,
                      onChanged: (_) => setSheet(() {}),
                      onSubmitted: (_) => add(),
                      style: TextStyle(color: _lzFg(ink), fontSize: 13.5),
                      decoration: _epDeco('New stage', 'Tour scheduled'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  FilledButton(
                    style: FilledButton.styleFrom(
                        backgroundColor: plum,
                        foregroundColor: Colors.white,
                        elevation: 0,
                        minimumSize: const Size(0, 46),
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12))),
                    onPressed: addC.text.trim().isEmpty ? null : _h(add),
                    child: const Text('Add',
                        style: TextStyle(fontWeight: FontWeight.w700)),
                  ),
                ]),
              ],
              _lzSection('Always last'),
              fixed(<String>['Booked', 'Delivered', 'Lost']),
              const SizedBox(height: 8),
              Text('These follow the real booking status.',
                  style: TextStyle(fontSize: 12, color: _lzFg(muted))),
              if (err.isNotEmpty) _pv3Err(err),
            ],
            footer: _lzActions(
                secondary: 'Cancel',
                onSecondary: () => Navigator.pop(ctx),
                primary: 'Save stages',
                icon: Icons.check_rounded,
                busy: saving,
                onPrimary: () async {
                  setSheet(() {
                    saving = true;
                    err = '';
                  });
                  try {
                    await save();
                    if (ctx.mounted) Navigator.pop(ctx);
                    _toast('Stages saved');
                  } catch (e) {
                    setSheet(() {
                      saving = false;
                      err = 'Could not save: ' + _errText(e);
                    });
                  }
                }));
      }),
    );
  }
""")

    # K add tag
    rep(r"""    await _lzSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: _lzBg(ivory),
      constraints: const BoxConstraints(maxWidth: 520),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (BuildContext ctx) => SafeArea(
        child: Padding(
          padding: EdgeInsets.fromLTRB(
              22, 18, 22, 22 + MediaQuery.of(ctx).viewInsets.bottom),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('Tag this thread', style: _serif(size: 22)),
              const SizedBox(height: 10),
              if (palette.isNotEmpty)
                Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
                  for (final String t in palette)
                    _tagChip(t, have.contains(t), () async {
                      await apply(t);
                      if (ctx.mounted) Navigator.pop(ctx);
                    }),
                ]),
              const SizedBox(height: 10),
              Row(children: <Widget>[
                Expanded(
                  child: TextField(
                    controller: c,
                    autofocus: palette.isEmpty,
                    textInputAction: TextInputAction.done,
                    onSubmitted: (String v) async {
                      await apply(v);
                      if (ctx.mounted) Navigator.pop(ctx);
                    },
                    style:  TextStyle(color: _lzFg(ink), fontSize: 13.5),
                    decoration: InputDecoration(
                      hintText: 'New tag - "referral", "elopement", "hot"',
                      hintStyle:
                          TextStyle(color: _lzFg(ink.withOpacity(.35)), fontSize: 13),
                      isDense: true,
                      filled: true,
                      fillColor: _lzBg(Colors.white),
                      contentPadding: const EdgeInsets.symmetric(
                          horizontal: 12, vertical: 11),
                      border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12),
                          borderSide:  BorderSide(color: _lzLine(goldLine))),
                      enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12),
                          borderSide:  BorderSide(color: _lzLine(goldLine))),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                FilledButton(
                  style: FilledButton.styleFrom(
                      backgroundColor: plum,
                      elevation: 0,
                      padding: const EdgeInsets.symmetric(
                          horizontal: 14, vertical: 12),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(11))),
                  onPressed: _h(() async {
                    await apply(c.text);
                    if (ctx.mounted) Navigator.pop(ctx);
                  }),
                  child: const Text('Add',
                      style: TextStyle(
                          color: Colors.white, fontWeight: FontWeight.w800)),
                ),
              ]),
            ],
          ),
        ),
      ),
    );
  }
""", r"""    bool busy = false;
    String err = '';
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 520),
      builder: (BuildContext ctx) =>
          StatefulBuilder(builder: (BuildContext sc, StateSetter setSheet) {
        Future<void> pick(String t) async {
          if (busy) return;
          setSheet(() {
            busy = true;
            err = '';
          });
          try {
            await apply(t);
            if (ctx.mounted) Navigator.pop(ctx);
          } catch (e) {
            setSheet(() {
              busy = false;
              err = 'Could not tag it: ' + _errText(e);
            });
          }
        }

        return _lzFrame(sc,
            icon: Icons.sell_outlined,
            title: 'Tag this thread',
            subtitle: 'Tags show on pipeline cards and filter your leads.',
            children: <Widget>[
              if (palette.isNotEmpty) ...<Widget>[
                _lzSection('Your tags'),
                Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
                  for (final String t in palette)
                    _tagChip(t, have.contains(t), () => pick(t)),
                ]),
              ],
              _lzSection('New tag'),
              TextField(
                controller: c,
                autofocus: palette.isEmpty,
                textInputAction: TextInputAction.done,
                onChanged: (_) => setSheet(() {}),
                onSubmitted: (String v) => pick(v),
                style: TextStyle(color: _lzFg(ink), fontSize: 13.5),
                decoration: _epDeco('Tag', 'referral, elopement, hot'),
              ),
              const SizedBox(height: 6),
              Text('Up to 24 characters. It joins your tag list for next time.',
                  style: TextStyle(fontSize: 12, color: _lzFg(muted))),
              if (err.isNotEmpty) _pv3Err(err),
            ],
            footer: _lzActions(
                secondary: 'Cancel',
                onSecondary: () => Navigator.pop(ctx),
                primary: 'Add tag',
                icon: Icons.add_rounded,
                busy: busy,
                onPrimary: c.text.trim().isEmpty ? null : () => pick(c.text)));
      }),
    );
  }
""")

    # L task
    rep(r"""    await _lzSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: _lzBg(ivory),
      constraints: const BoxConstraints(maxWidth: 560),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (BuildContext ctx) =>
          StatefulBuilder(builder: (BuildContext sc, StateSetter setSheet) {
        InputDecoration deco(String hint) => InputDecoration(
              hintText: hint,
              hintStyle: TextStyle(color: _lzFg(ink.withOpacity(.35)), fontSize: 13),
              isDense: true,
              filled: true,
              fillColor: _lzBg(Colors.white),
              contentPadding:
                  const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
              border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide:  BorderSide(color: _lzLine(goldLine))),
              enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide:  BorderSide(color: _lzLine(goldLine))),
            );
        Widget quick(String label, DateTime d) => _tagChip(
            label,
            due != null &&
                due!.year == d.year &&
                due!.month == d.month &&
                due!.day == d.day,
            () => setSheet(() => due = d));
        return SafeArea(
          child: Padding(
            padding: EdgeInsets.fromLTRB(
                22, 18, 22, 22 + MediaQuery.of(ctx).viewInsets.bottom),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(existing == null ? 'Add a task' : 'Edit task',
                    style: _serif(size: 22)),
                const SizedBox(height: 10),
                TextField(
                    controller: titleC,
                    autofocus: existing == null,
                    style:  TextStyle(color: _lzFg(ink), fontSize: 14),
                    decoration:
                        deco('What needs doing? - "Send the timeline draft"')),
                const SizedBox(height: 8),
                TextField(
                    controller: noteC,
                    maxLines: 2,
                    style:  TextStyle(color: _lzFg(ink), fontSize: 13),
                    decoration: deco('Note (optional)')),
                const SizedBox(height: 12),
                 Text('DUE',
                    style: TextStyle(
                        color: _lzFg(muted),
                        fontSize: 9.5,
                        letterSpacing: 1.4,
                        fontWeight: FontWeight.w800)),
                const SizedBox(height: 6),
                Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
                  quick('Today', today),
                  quick('Tomorrow', today.add(const Duration(days: 1))),
                  quick('Next week', today.add(const Duration(days: 7))),
                  _tagChip(
                      due == null
                          ? 'Pick a date'
                          : '${due!.month}/${due!.day}/${due!.year}',
                      false, () async {
                    final DateTime? d = await showDatePicker(
                        context: sc,
                        initialDate: due ?? today,
                        firstDate: today.subtract(const Duration(days: 365)),
                        lastDate: today.add(const Duration(days: 1095)));
                    if (d != null)
                      setSheet(() => due = DateTime(d.year, d.month, d.day));
                  }),
                  if (due != null)
                    _tagChip(
                        'No date', false, () => setSheet(() => due = null)),
                ]),
                const SizedBox(height: 12),
                 Text('FOR',
                    style: TextStyle(
                        color: _lzFg(muted),
                        fontSize: 9.5,
                        letterSpacing: 1.4,
                        fontWeight: FontWeight.w800)),
                const SizedBox(height: 6),
                Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
                  _tagChip('Me / my team', who == 'vendor',
                      () => setSheet(() => who = 'vendor')),
                  _tagChip('The couple', who == 'couple',
                      () => setSheet(() => who = 'couple'),
                      tint: vGreen),
                ]),
                if (who == 'couple')
                   Padding(
                    padding: EdgeInsets.only(top: 6),
                    child: Text(
                        'They see it in their thread and get a reminder the morning it is due (text and email for website leads).',
                        style: TextStyle(
                            fontSize: 11, color: _lzFg(muted), height: 1.35)),
                  ),
                if (err.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Text(err,
                        style:  TextStyle(
                            color: _lzFg(Color(0xFFB04343)), fontSize: 12)),
                  ),
                const SizedBox(height: 14),
                Row(children: <Widget>[
                  if (existing != null)
                    TextButton(
                      onPressed: _h(() async {
                        await existing.reference.delete();
                        if (ctx.mounted) Navigator.pop(ctx);
                      }),
                      child:  Text('Delete',
                          style: TextStyle(
                              color: _lzFg(muted),
                              fontSize: 12.5,
                              fontWeight: FontWeight.w700)),
                    ),
                  const Spacer(),
                  FilledButton(
                    style: FilledButton.styleFrom(
                        backgroundColor: plum,
                        elevation: 0,
                        padding: const EdgeInsets.symmetric(
                            horizontal: 18, vertical: 12),
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(11))),
                    onPressed: _h(() async {
                      final String title = titleC.text.trim();
                      if (title.isEmpty) {
                        setSheet(() => err = 'Give it a title.');
                        return;
                      }
                      final Map<String, dynamic> data = <String, dynamic>{
                        'title': title,
                        'note': noteC.text.trim(),
                        'dueAt': due == null ? null : Timestamp.fromDate(due!),
                        'assignedTo': who,
                        'vendorId': vendorId,
                        'coupleUid': (inq['coupleUid'] ?? '').toString(),
                        'done': false,
                      };
                      try {
                        if (existing != null) {
                          await existing.reference
                              .set(data, SetOptions(merge: true));
                        } else {
                          data['createdAt'] = FieldValue.serverTimestamp();
                          data['createdBy'] = _uid ?? '';
                          await FirebaseFirestore.instance
                              .collection('inquiries')
                              .doc(inquiryId)
                              .collection('tasks')
                              .add(data);
                          if (who == 'couple') {
                            await FirebaseFirestore.instance
                                .collection('inquiries')
                                .doc(inquiryId)
                                .collection('messages')
                                .add(<String, dynamic>{
                              'senderRole': 'vendor',
                              'system': true,
                              'text':
                                  'Quick one for you: $title${due == null ? '' : ' - by ${due!.month}/${due!.day}'}.',
                              'at': FieldValue.serverTimestamp(),
                            });
                          }
                        }
                        if (ctx.mounted) Navigator.pop(ctx);
                      } catch (e) {
                        setSheet(() => err = _errText(e));
                      }
                    }),
                    child: Text(existing == null ? 'Add task' : 'Save',
                        style: const TextStyle(
                            color: Colors.white, fontWeight: FontWeight.w800)),
                  ),
                ]),
              ],
            ),
          ),
        );
      }),
    );
  }
""", r"""    bool saving = false;
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext ctx) =>
          StatefulBuilder(builder: (BuildContext sc, StateSetter setSheet) {
        Widget quick(String label, DateTime d) => _tagChip(
            label,
            due != null &&
                due!.year == d.year &&
                due!.month == d.month &&
                due!.day == d.day,
            () => setSheet(() => due = d));

        Future<void> save() async {
          final String title = titleC.text.trim();
          if (title.isEmpty) {
            setSheet(() => err = 'Give it a title.');
            return;
          }
          final Map<String, dynamic> data = <String, dynamic>{
            'title': title,
            'note': noteC.text.trim(),
            'dueAt': due == null ? null : Timestamp.fromDate(due!),
            'assignedTo': who,
            'vendorId': vendorId,
            'coupleUid': (inq['coupleUid'] ?? '').toString(),
            'done': false,
          };
          setSheet(() {
            saving = true;
            err = '';
          });
          try {
            if (existing != null) {
              await existing.reference.set(data, SetOptions(merge: true));
            } else {
              data['createdAt'] = FieldValue.serverTimestamp();
              data['createdBy'] = _uid ?? '';
              await FirebaseFirestore.instance
                  .collection('inquiries')
                  .doc(inquiryId)
                  .collection('tasks')
                  .add(data);
              if (who == 'couple') {
                await FirebaseFirestore.instance
                    .collection('inquiries')
                    .doc(inquiryId)
                    .collection('messages')
                    .add(<String, dynamic>{
                  'senderRole': 'vendor',
                  'system': true,
                  'text':
                      'Quick one for you: $title${due == null ? '' : ' - by ${due!.month}/${due!.day}'}.',
                  'at': FieldValue.serverTimestamp(),
                });
              }
            }
            if (ctx.mounted) Navigator.pop(ctx);
          } catch (e) {
            setSheet(() {
              saving = false;
              err = _errText(e);
            });
          }
        }

        Future<void> remove() async {
          final QueryDocumentSnapshot<Map<String, dynamic>>? d = existing;
          if (d == null) return;
          final bool ok = await _lzConfirm(
              'Delete this task?', 'This can\u2019t be undone.',
              confirm: 'Delete task', cancel: 'Keep it', danger: true);
          if (!ok) return;
          try {
            await d.reference.delete();
            if (ctx.mounted) Navigator.pop(ctx);
          } catch (e) {
            setSheet(() => err = 'Could not delete: ' + _errText(e));
          }
        }

        return _lzFrame(sc,
            icon: Icons.task_alt_rounded,
            title: existing == null ? 'Add a task' : 'Edit task',
            subtitle: 'For you, your team or the couple.',
            children: <Widget>[
              const SizedBox(height: 14),
              TextField(
                  controller: titleC,
                  autofocus: existing == null,
                  textInputAction: TextInputAction.next,
                  onChanged: (_) => setSheet(() {}),
                  style: TextStyle(color: _lzFg(ink), fontSize: 14),
                  decoration: _epDeco('Task', 'Send the timeline')),
              const SizedBox(height: 10),
              TextField(
                  controller: noteC,
                  minLines: 1,
                  maxLines: 3,
                  keyboardType: TextInputType.multiline,
                  style: TextStyle(color: _lzFg(ink), fontSize: 13.5),
                  decoration: _epDeco('Note (optional)', 'Anything to remember')),
              _lzSection('Due'),
              Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
                quick('Today', today),
                quick('Tomorrow', today.add(const Duration(days: 1))),
                quick('Next week', today.add(const Duration(days: 7))),
                _tagChip(
                    due == null
                        ? 'Pick a date'
                        : '${due!.month}/${due!.day}/${due!.year}',
                    false, () async {
                  final DateTime? d = await showDatePicker(
                      context: sc,
                      initialDate: due ?? today,
                      firstDate: today.subtract(const Duration(days: 365)),
                      lastDate: today.add(const Duration(days: 1095)));
                  if (d != null)
                    setSheet(() => due = DateTime(d.year, d.month, d.day));
                }),
                if (due != null)
                  _tagChip('No date', false, () => setSheet(() => due = null)),
              ]),
              _lzSection('For'),
              Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
                _tagChip('Me / my team', who == 'vendor',
                    () => setSheet(() => who = 'vendor')),
                _tagChip('The couple', who == 'couple',
                    () => setSheet(() => who = 'couple'),
                    tint: vGreen),
              ]),
              if (who == 'couple') ...<Widget>[
                const SizedBox(height: 12),
                _lzNote(Icons.notifications_none_rounded,
                    'They see it in their thread and get a reminder the morning it\u2019s due (text and email for website leads).'),
              ],
              if (err.isNotEmpty) _pv3Err(err),
            ],
            footer: _lzActions(
                secondary: existing == null ? 'Cancel' : 'Delete',
                onSecondary: existing == null
                    ? () => Navigator.pop(ctx)
                    : () {
                        remove();
                      },
                primary: existing == null ? 'Add task' : 'Save',
                icon: existing == null ? Icons.add_rounded : Icons.check_rounded,
                busy: saving,
                onPrimary: titleC.text.trim().isEmpty ? null : save));
      }),
    );
  }
""")

    # M brand
    rep(r"""    bool saving = false;
    if (!mounted) return;

    await _lzSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: _lzBg(ivory),
      constraints: const BoxConstraints(maxWidth: 620),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (BuildContext ctx) =>
          StatefulBuilder(builder: (BuildContext sc, StateSetter setSheet) {
        final Color pCol = _hexColor(primary, plum);
        final Color aCol = _hexColor(accent, gold);
        final bool serif = font == 'serif';

        Widget swatchRow(
            List<List<String>> sw, String cur, void Function(String) pick) {
          return Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
            for (final List<String> w in sw)
              Tooltip(
                message: w[1],
                child: InkWell(
                  onTap: () => pick(w[0]),
                  borderRadius: BorderRadius.circular(999),
                  child: Container(
                    width: 30,
                    height: 30,
                    decoration: BoxDecoration(
                      color: _lzBg(_hexColor(w[0], plum)),
                      shape: BoxShape.circle,
                      border: Border.all(
                          color: _lzLine(cur.toUpperCase() == w[0].toUpperCase()
                              ? ink
                              : Colors.white),
                          width: cur.toUpperCase() == w[0].toUpperCase()
                              ? 2.5
                              : 1.5),
                      boxShadow: <BoxShadow>[
                        BoxShadow(
                            color: Colors.black.withOpacity(.12), blurRadius: 4)
                      ],
                    ),
                  ),
                ),
              ),
          ]);
        }

        InputDecoration hexDeco(String hint) => InputDecoration(
              hintText: hint,
              hintStyle: TextStyle(color: _lzFg(ink.withOpacity(.35)), fontSize: 12.5),
              isDense: true,
              filled: true,
              fillColor: _lzBg(Colors.white),
              contentPadding:
                  const EdgeInsets.symmetric(horizontal: 10, vertical: 9),
              border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide:  BorderSide(color: _lzLine(goldLine))),
              enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide:  BorderSide(color: _lzLine(goldLine))),
            );

        return SafeArea(
          child: Padding(
            padding: EdgeInsets.fromLTRB(
                22, 18, 22, 22 + MediaQuery.of(ctx).viewInsets.bottom),
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('Your brand', style: _serif(size: 24)),
                  const SizedBox(height: 4),
                   Text(
                      'Couples should feel like they are dealing with you, not with Lazo. These colors and this type go on your booking pages, your galleries, your lead form and every email they get from you.',
                      style:
                          TextStyle(fontSize: 12.5, color: _lzFg(muted), height: 1.4)),
                  const SizedBox(height: 14),
                  // ---- live preview ----
                  ClipRRect(
                    borderRadius: BorderRadius.circular(16),
                    child: Container(
                      color: _lzBg(pCol),
                      padding: const EdgeInsets.fromLTRB(20, 22, 20, 20),
                      child: Column(children: <Widget>[
                        if (logo.isNotEmpty)
                          Container(
                            width: 56,
                            height: 56,
                            margin: const EdgeInsets.only(bottom: 10),
                            padding: const EdgeInsets.all(6),
                            decoration: BoxDecoration(
                                color: _lzBg(Colors.white),
                                borderRadius: BorderRadius.circular(13)),
                            child: Image.network(logo, fit: BoxFit.contain),
                          ),
                        Text(name.toUpperCase(),
                            style: TextStyle(
                                color: _lzFg(aCol),
                                fontSize: 10,
                                letterSpacing: 2,
                                fontWeight: FontWeight.w800)),
                        const SizedBox(height: 6),
                        Text('Your booking with $name',
                            textAlign: TextAlign.center,
                            style: serif
                                ? GoogleFonts.cormorantGaramond(
                                    color: Colors.white,
                                    fontSize: 30,
                                    fontWeight: FontWeight.w600,
                                    height: 1.05)
                                : const TextStyle(
                                    color: Colors.white,
                                    fontSize: 24,
                                    fontWeight: FontWeight.w700,
                                    height: 1.1)),
                        const SizedBox(height: 12),
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 16, vertical: 9),
                          decoration: BoxDecoration(
                              color: _lzBg(aCol),
                              borderRadius: BorderRadius.circular(10)),
                          child: Text('Pay \u0024500',
                              style: TextStyle(
                                  color: _lzFg(pCol),
                                  fontSize: 13,
                                  fontWeight: FontWeight.w800)),
                        ),
                      ]),
                    ),
                  ),
                  const SizedBox(height: 16),
                   Text('PRIMARY',
                      style: TextStyle(
                          color: _lzFg(muted),
                          fontSize: 9.5,
                          letterSpacing: 1.4,
                          fontWeight: FontWeight.w800)),
                  const SizedBox(height: 6),
                  Row(children: <Widget>[
                    Expanded(
                        child: swatchRow(
                            _kBrandSwatches,
                            primary,
                            (String h) => setSheet(() {
                                  primary = h;
                                  pC.text = h;
                                }))),
                    const SizedBox(width: 10),
                    SizedBox(
                      width: 96,
                      child: TextField(
                          controller: pC,
                          onChanged: (String v) =>
                              setSheet(() => primary = v.trim()),
                          style:  TextStyle(
                              color: _lzFg(ink),
                              fontSize: 12.5,
                              fontFamily: 'monospace'),
                          decoration: hexDeco('#52284F')),
                    ),
                  ]),
                  const SizedBox(height: 14),
                   Text('ACCENT',
                      style: TextStyle(
                          color: _lzFg(muted),
                          fontSize: 9.5,
                          letterSpacing: 1.4,
                          fontWeight: FontWeight.w800)),
                  const SizedBox(height: 6),
                  Row(children: <Widget>[
                    Expanded(
                        child: swatchRow(
                            _kAccentSwatches,
                            accent,
                            (String h) => setSheet(() {
                                  accent = h;
                                  aC.text = h;
                                }))),
                    const SizedBox(width: 10),
                    SizedBox(
                      width: 96,
                      child: TextField(
                          controller: aC,
                          onChanged: (String v) =>
                              setSheet(() => accent = v.trim()),
                          style:  TextStyle(
                              color: _lzFg(ink),
                              fontSize: 12.5,
                              fontFamily: 'monospace'),
                          decoration: hexDeco('#D9B77C')),
                    ),
                  ]),
                  const SizedBox(height: 14),
                   Text('TYPE',
                      style: TextStyle(
                          color: _lzFg(muted),
                          fontSize: 9.5,
                          letterSpacing: 1.4,
                          fontWeight: FontWeight.w800)),
                  const SizedBox(height: 6),
                  Wrap(spacing: 8, children: <Widget>[
                    _tagChip('Serif - editorial', serif,
                        () => setSheet(() => font = 'serif')),
                    _tagChip('Sans - clean', !serif,
                        () => setSheet(() => font = 'sans')),
                  ]),
                  const SizedBox(height: 6),
                  Text(
                      logo.isEmpty
                          ? 'Add your logo in Edit profile and it appears at the top of every page and email.'
                          : 'Your logo comes from Edit profile.',
                      style:  TextStyle(fontSize: 11, color: _lzFg(muted))),
                  const SizedBox(height: 16),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton(
                      style: FilledButton.styleFrom(
                          backgroundColor: gold,
                          foregroundColor: plumDeep,
                          elevation: 0,
                          padding: const EdgeInsets.symmetric(vertical: 13)),
                      onPressed: _h(
                          saving
                              ? null
                              : () async {
                                  final RegExp hex =
                                      RegExp(r'^#[0-9a-fA-F]{6}$');
                                  if (!hex.hasMatch(primary) ||
                                      !hex.hasMatch(accent)) {
                                    _toast(
                                        'Colors need to be six-digit hex, like #52284F.');
                                    return;
                                  }
                                  setSheet(() => saving = true);
                                  try {
                                    await FirebaseFirestore.instance
                                        .collection('vendors')
                                        .doc(vendorId)
                                        .set(<String, dynamic>{
                                      'brand': <String, dynamic>{
                                        'primary': primary.toUpperCase(),
                                        'accent': accent.toUpperCase(),
                                        'font': font,
                                        'updatedAt':
                                            FieldValue.serverTimestamp(),
                                      }
                                    }, SetOptions(merge: true));
                                    if (ctx.mounted) Navigator.pop(ctx);
                                    _toast(
                                        'Brand saved - live on your pages within a minute.');
                                  } catch (e) {
                                    setSheet(() => saving = false);
                                    _toast('Could not save: ' + _errText(e));
                                  }
                                },
                          _Tick.medium),
                      child: Text(saving ? 'Saving\u2026' : 'Save brand',
                          style: const TextStyle(fontWeight: FontWeight.w800)),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      }),
    );
  }
""", r"""    bool saving = false;
    String err = '';
    if (!mounted) return;

    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 620),
      builder: (BuildContext ctx) =>
          StatefulBuilder(builder: (BuildContext sc, StateSetter setSheet) {
        final Color pCol = _hexColor(primary, plum);
        final Color aCol = _hexColor(accent, gold);
        final bool serif = font == 'serif';
        final RegExp hex = RegExp(r'^#[0-9a-fA-F]{6}$');
        final bool hexOk = hex.hasMatch(primary) && hex.hasMatch(accent);

        Widget swatchRow(
            List<List<String>> sw, String cur, void Function(String) pick) {
          return Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
            for (final List<String> w in sw)
              Tooltip(
                message: w[1],
                child: InkWell(
                  onTap: () => pick(w[0]),
                  borderRadius: BorderRadius.circular(999),
                  child: Container(
                    width: 30,
                    height: 30,
                    decoration: BoxDecoration(
                      color: _lzBg(_hexColor(w[0], plum)),
                      shape: BoxShape.circle,
                      border: Border.all(
                          color: _lzLine(cur.toUpperCase() == w[0].toUpperCase()
                              ? ink
                              : Colors.white),
                          width: cur.toUpperCase() == w[0].toUpperCase()
                              ? 2.5
                              : 1.5),
                      boxShadow: <BoxShadow>[
                        BoxShadow(
                            color: Colors.black.withOpacity(.12), blurRadius: 4)
                      ],
                    ),
                  ),
                ),
              ),
          ]);
        }

        InputDecoration hexDeco(String hint) => InputDecoration(
              hintText: hint,
              hintStyle: TextStyle(color: _lzFg(ink.withOpacity(.35)), fontSize: 12.5),
              isDense: true,
              filled: true,
              fillColor: _lzBg(Colors.white),
              contentPadding:
                  const EdgeInsets.symmetric(horizontal: 10, vertical: 9),
              border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide:  BorderSide(color: _lzLine(goldLine))),
              enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide:  BorderSide(color: _lzLine(goldLine))),
            );

        Future<void> save() async {
          if (!hexOk) {
            setSheet(() =>
                err = 'Colors need to be six-digit hex, like #52284F.');
            return;
          }
          setSheet(() {
            saving = true;
            err = '';
          });
          try {
            await FirebaseFirestore.instance
                .collection('vendors')
                .doc(vendorId)
                .set(<String, dynamic>{
              'brand': <String, dynamic>{
                'primary': primary.toUpperCase(),
                'accent': accent.toUpperCase(),
                'font': font,
                'updatedAt': FieldValue.serverTimestamp(),
              }
            }, SetOptions(merge: true));
            if (ctx.mounted) Navigator.pop(ctx);
            _toast('Brand saved - live on your pages within a minute.');
          } catch (e) {
            setSheet(() {
              saving = false;
              err = 'Could not save: ' + _errText(e);
            });
          }
        }

        return _lzFrame(sc,
            icon: Icons.palette_outlined,
            title: 'Your brand',
            subtitle:
                'Your colors and type on booking pages, galleries, the lead form and every email.',
            children: <Widget>[
              const SizedBox(height: 14),
              // ---- live preview ----
              ClipRRect(
                borderRadius: BorderRadius.circular(16),
                child: Container(
                  color: _lzBg(pCol),
                  padding: const EdgeInsets.fromLTRB(20, 22, 20, 20),
                  child: Column(children: <Widget>[
                    if (logo.isNotEmpty)
                      Container(
                        width: 56,
                        height: 56,
                        margin: const EdgeInsets.only(bottom: 10),
                        padding: const EdgeInsets.all(6),
                        decoration: BoxDecoration(
                            color: _lzBg(Colors.white),
                            borderRadius: BorderRadius.circular(13)),
                        child: Image.network(logo, fit: BoxFit.contain),
                      ),
                    Text(name.toUpperCase(),
                        style: TextStyle(
                            color: _lzFg(aCol),
                            fontSize: 10,
                            letterSpacing: 2,
                            fontWeight: FontWeight.w800)),
                    const SizedBox(height: 6),
                    Text('Your booking with $name',
                        textAlign: TextAlign.center,
                        style: serif
                            ? GoogleFonts.cormorantGaramond(
                                color: Colors.white,
                                fontSize: 30,
                                fontWeight: FontWeight.w600,
                                height: 1.05)
                            : const TextStyle(
                                color: Colors.white,
                                fontSize: 24,
                                fontWeight: FontWeight.w700,
                                height: 1.1)),
                    const SizedBox(height: 12),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 9),
                      decoration: BoxDecoration(
                          color: _lzBg(aCol),
                          borderRadius: BorderRadius.circular(10)),
                      child: Text('Pay \$500',
                          style: TextStyle(
                              color: _lzFg(pCol),
                              fontSize: 13,
                              fontWeight: FontWeight.w800)),
                    ),
                  ]),
                ),
              ),
              _lzSection('Primary'),
              Row(children: <Widget>[
                Expanded(
                    child: swatchRow(
                        _kBrandSwatches,
                        primary,
                        (String h) => setSheet(() {
                              primary = h;
                              pC.text = h;
                            }))),
                const SizedBox(width: 10),
                SizedBox(
                  width: 96,
                  child: TextField(
                      controller: pC,
                      autocorrect: false,
                      onChanged: (String v) =>
                          setSheet(() => primary = v.trim()),
                      style: TextStyle(
                          color: _lzFg(ink),
                          fontSize: 12.5,
                          fontFamily: 'monospace'),
                      decoration: hexDeco('#52284F')),
                ),
              ]),
              _lzSection('Accent'),
              Row(children: <Widget>[
                Expanded(
                    child: swatchRow(
                        _kAccentSwatches,
                        accent,
                        (String h) => setSheet(() {
                              accent = h;
                              aC.text = h;
                            }))),
                const SizedBox(width: 10),
                SizedBox(
                  width: 96,
                  child: TextField(
                      controller: aC,
                      autocorrect: false,
                      onChanged: (String v) =>
                          setSheet(() => accent = v.trim()),
                      style: TextStyle(
                          color: _lzFg(ink),
                          fontSize: 12.5,
                          fontFamily: 'monospace'),
                      decoration: hexDeco('#D9B77C')),
                ),
              ]),
              _lzSection('Type'),
              Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                _tagChip('Serif - editorial', serif,
                    () => setSheet(() => font = 'serif')),
                _tagChip('Sans - clean', !serif,
                    () => setSheet(() => font = 'sans')),
              ]),
              const SizedBox(height: 14),
              _lzNote(
                  Icons.image_outlined,
                  logo.isEmpty
                      ? 'Add your logo in Edit profile and it appears at the top of every page and email.'
                      : 'Your logo comes from Edit profile.'),
              if (!hexOk)
                _pv3Err('Colors need to be six-digit hex, like #52284F.')
              else if (err.isNotEmpty)
                _pv3Err(err),
            ],
            footer: _lzActions(
                secondary: 'Cancel',
                onSecondary: () => Navigator.pop(ctx),
                primary: saving ? 'Saving\u2026' : 'Save brand',
                icon: Icons.check_rounded,
                busy: saving,
                onPrimary: hexOk ? save : null));
      }),
    );
  }
""")

    # N0 scheduler err state
    rep(r"""    final String publicUrl = 'https://meetlazo.com/book/$vendorId';
    bool saving = false;
""", r"""    final String publicUrl = 'https://meetlazo.com/book/$vendorId';
    bool saving = false;
    String err = '';
""")

    # N1 scheduler section labels
    rep(r"""        Widget label(String t) => Padding(
              padding: const EdgeInsets.only(top: 14, bottom: 6),
              child: Text(t.toUpperCase(),
                  style:  TextStyle(
                      color: _lzFg(muted),
                      fontSize: 9.5,
                      letterSpacing: 1.4,
                      fontWeight: FontWeight.w800)),
            );
        Future<String?> pickTime(String cur) async {
""", r"""        Widget label(String t) => _lzSection(t);
        Future<String?> pickTime(String cur) async {
""")

    # N2 scheduler frame + save()
    rep(r"""        return SafeArea(
          child: Padding(
            padding: EdgeInsets.fromLTRB(
                22, 18, 22, 22 + MediaQuery.of(ctx).viewInsets.bottom),
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Row(children: <Widget>[
                    Expanded(
                        child:
                            Text('Consult scheduler', style: _serif(size: 24))),
                    Switch(
                        value: enabled,
                        activeColor: vGreen,
                        onChanged:
                            _hb((bool v) => setSheet(() => enabled = v))),
                  ]),
                  const SizedBox(height: 4),
                   Text(
                      'Couples pick a time from your real availability; you both get a calendar invite, and reminders go out the day before and an hour before. Your blocked dates and booked weddings are never offered.',
                      style:
                          TextStyle(fontSize: 12.5, color: _lzFg(muted), height: 1.4)),
""", r"""        Future<void> save() async {
          setSheet(() {
            saving = true;
            err = '';
          });
          final List<Map<String, dynamic>> cleanTypes = types
              .where((Map<String, dynamic> t) =>
                  (t['label'] ?? '').toString().trim().isNotEmpty)
              .map((Map<String, dynamic> t) => <String, dynamic>{
                    'key': (t['key'] ?? 'intro').toString(),
                    'label': (t['label'] ?? '').toString().trim(),
                    'minutes': (t['minutes'] is num)
                        ? (t['minutes'] as num).toInt()
                        : 30,
                    'mode': (t['mode'] ?? 'video').toString(),
                    'location': (t['location'] ?? '').toString().trim(),
                  })
              .toList();
          try {
            await FirebaseFirestore.instance
                .collection('vendors')
                .doc(vendorId)
                .set(<String, dynamic>{
              'scheduler': <String, dynamic>{
                'enabled': enabled,
                'tz': tzGuess(),
                'slotMinutes': slot,
                'bufferMinutes': buffer,
                'minNoticeHours': notice,
                'maxDaysOut': 60,
                'videoLink': videoC.text.trim(),
                'hours': hours,
                'types': cleanTypes.isEmpty
                    ? <Map<String, dynamic>>[
                        <String, dynamic>{
                          'key': 'intro',
                          'label': 'Intro call',
                          'minutes': 30,
                          'mode': 'video',
                          'location': ''
                        }
                      ]
                    : cleanTypes,
                'updatedAt': FieldValue.serverTimestamp(),
              }
            }, SetOptions(merge: true));
            if (ctx.mounted) Navigator.pop(ctx);
            _toast(enabled
                ? 'Scheduler is live at $publicUrl'
                : 'Scheduler saved (off).');
          } catch (e) {
            setSheet(() {
              saving = false;
              err = 'Could not save: ' + _errText(e);
            });
          }
        }

        return _lzFrame(sc,
            icon: Icons.event_available_rounded,
            title: 'Consult scheduler',
            subtitle: 'Couples pick a time from your real availability.',
            headerExtra: Container(
              padding: const EdgeInsets.fromLTRB(14, 2, 6, 2),
              decoration: BoxDecoration(
                  color: _lzBg(card),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: _lzLine(goldLine))),
              child: Row(children: <Widget>[
                Icon(
                    enabled
                        ? Icons.check_circle_rounded
                        : Icons.pause_circle_outline_rounded,
                    size: 18,
                    color: _lzFg(enabled ? vGreen : muted)),
                const SizedBox(width: 8),
                Expanded(
                    child: Text(enabled ? 'Taking bookings' : 'Paused',
                        style: TextStyle(
                            fontSize: 13.5,
                            fontWeight: FontWeight.w700,
                            color: _lzFg(ink)))),
                Switch(
                    value: enabled,
                    activeColor: vGreen,
                    onChanged: _hb((bool v) => setSheet(() => enabled = v))),
              ]),
            ),
            children: <Widget>[
                  const SizedBox(height: 12),
                  _lzNote(Icons.notifications_active_outlined,
                      'You both get a calendar invite, with reminders the day before and an hour before. Blocked dates and booked weddings are never offered.'),
""")

    # N3 scheduler footer
    rep(r"""                  const SizedBox(height: 16),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton(
                      style: FilledButton.styleFrom(
                          backgroundColor: gold,
                          foregroundColor: plumDeep,
                          elevation: 0,
                          padding: const EdgeInsets.symmetric(vertical: 13)),
                      onPressed: _h(
                          saving
                              ? null
                              : () async {
                                  setSheet(() => saving = true);
                                  final List<Map<String, dynamic>> cleanTypes =
                                      types
                                          .where((Map<String, dynamic> t) =>
                                              (t['label'] ?? '')
                                                  .toString()
                                                  .trim()
                                                  .isNotEmpty)
                                          .map((Map<String, dynamic> t) =>
                                              <String, dynamic>{
                                                'key': (t['key'] ?? 'intro')
                                                    .toString(),
                                                'label': (t['label'] ?? '')
                                                    .toString()
                                                    .trim(),
                                                'minutes': (t['minutes'] is num)
                                                    ? (t['minutes'] as num)
                                                        .toInt()
                                                    : 30,
                                                'mode': (t['mode'] ?? 'video')
                                                    .toString(),
                                                'location':
                                                    (t['location'] ?? '')
                                                        .toString()
                                                        .trim(),
                                              })
                                          .toList();
                                  try {
                                    await FirebaseFirestore.instance
                                        .collection('vendors')
                                        .doc(vendorId)
                                        .set(<String, dynamic>{
                                      'scheduler': <String, dynamic>{
                                        'enabled': enabled,
                                        'tz': tzGuess(),
                                        'slotMinutes': slot,
                                        'bufferMinutes': buffer,
                                        'minNoticeHours': notice,
                                        'maxDaysOut': 60,
                                        'videoLink': videoC.text.trim(),
                                        'hours': hours,
                                        'types': cleanTypes.isEmpty
                                            ? <Map<String, dynamic>>[
                                                <String, dynamic>{
                                                  'key': 'intro',
                                                  'label': 'Intro call',
                                                  'minutes': 30,
                                                  'mode': 'video',
                                                  'location': ''
                                                }
                                              ]
                                            : cleanTypes,
                                        'updatedAt':
                                            FieldValue.serverTimestamp(),
                                      }
                                    }, SetOptions(merge: true));
                                    if (ctx.mounted) Navigator.pop(ctx);
                                    _toast(enabled
                                        ? 'Scheduler is live at $publicUrl'
                                        : 'Scheduler saved (off).');
                                  } catch (e) {
                                    setSheet(() => saving = false);
                                    _toast('Could not save: ' + _errText(e));
                                  }
                                },
                          _Tick.medium),
                      child: Text(saving ? 'Saving\u2026' : 'Save scheduler',
                          style: const TextStyle(fontWeight: FontWeight.w800)),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      }),
    );
  }
""", r"""                  if (err.isNotEmpty) _pv3Err(err),
            ],
            footer: _lzActions(
                secondary: 'Cancel',
                onSecondary: () => Navigator.pop(ctx),
                primary: saving ? 'Saving\u2026' : 'Save scheduler',
                icon: Icons.check_rounded,
                busy: saving,
                onPrimary: save));
      }),
    );
  }
""")

    # O MCP
    rep(r"""    Future<void> mint(StateSetter setSheet) async {
      setSheet(() => busy = true);
      try {
        final HttpsCallable fn =
            FirebaseFunctions.instance.httpsCallable('mcpToken');
        final HttpsCallableResult<dynamic> r = await fn
            .call(<String, dynamic>{'vendorId': vendorId, 'action': 'mint'});
        setSheet(() {
          url = ((r.data as Map?)?['url'] ?? '').toString();
          connected = true;
          busy = false;
        });
      } catch (e) {
        setSheet(() => busy = false);
        _toast('Could not create the link: ' + _errText(e));
      }
    }

    await _lzSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: _lzBg(ivory),
      constraints: const BoxConstraints(maxWidth: 620),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(26))),
      builder: (BuildContext ctx) =>
          StatefulBuilder(builder: (BuildContext sc, StateSetter setSheet) {
        Widget step(String n, String t) => Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Container(
                        width: 20,
                        height: 20,
                        alignment: Alignment.center,
                        decoration: const BoxDecoration(
                            color: plum, shape: BoxShape.circle),
                        child: Text(n,
                            style: const TextStyle(
                                color: gold,
                                fontSize: 11,
                                fontWeight: FontWeight.w800))),
                    const SizedBox(width: 8),
                    Expanded(
                        child: Text(t,
                            style:  TextStyle(
                                fontSize: 12.5, color: _lzFg(ink), height: 1.4))),
                  ]),
            );
        return SafeArea(
          child: Padding(
            padding: EdgeInsets.fromLTRB(
                22, 18, 22, 22 + MediaQuery.of(ctx).viewInsets.bottom),
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('Connect Claude or ChatGPT', style: _serif(size: 24)),
                  const SizedBox(height: 4),
                   Text(
                      '"Who is waiting on me?" "What is due this week?" "Draft a reply to Sarah about the second shooter." Your assistant can see your pipeline, every thread, money and consults - and, when you say so, reply, add tasks, tag and move things. Nothing about other vendors, ever.',
                      style:
                          TextStyle(fontSize: 12.5, color: _lzFg(muted), height: 1.4)),
                  const SizedBox(height: 14),
                  if (url.isNotEmpty) ...<Widget>[
                     Text('YOUR PRIVATE LINK - SHOWN ONCE',
                        style: TextStyle(
                            color: _lzFg(muted),
                            fontSize: 9.5,
                            letterSpacing: 1.4,
                            fontWeight: FontWeight.w800)),
                    const SizedBox(height: 6),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                          color: _lzBg(Colors.white),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: gold)),
                      child: SelectableText(url,
                          style:  TextStyle(
                              fontSize: 11.5,
                              color: _lzFg(ink),
                              fontFamily: 'monospace')),
                    ),
                    const SizedBox(height: 8),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton.icon(
                        style: FilledButton.styleFrom(
                            backgroundColor: gold,
                            foregroundColor: plumDeep,
                            elevation: 0,
                            padding: const EdgeInsets.symmetric(vertical: 12)),
                        onPressed: _h(() async {
                          await Clipboard.setData(ClipboardData(text: url));
                          _toast('Link copied \u2713');
                        }),
                        icon: const Icon(Icons.copy_rounded, size: 16),
                        label: const Text('Copy link',
                            style: TextStyle(fontWeight: FontWeight.w800)),
                      ),
                    ),
                    const SizedBox(height: 6),
                     Text(
                        'Treat it like a password - anyone with it can read your threads. Close this and it is gone; you can always make a new one.',
                        style: TextStyle(
                            fontSize: 11, color: _lzFg(muted), height: 1.35)),
                    const SizedBox(height: 14),
                     Text('CLAUDE',
                        style: TextStyle(
                            color: _lzFg(muted),
                            fontSize: 9.5,
                            letterSpacing: 1.4,
                            fontWeight: FontWeight.w800)),
                    const SizedBox(height: 6),
                    step('1',
                        'claude.ai \u203a Settings \u203a Connectors \u203a Add custom connector.'),
                    step('2',
                        'Name it Lazo, paste the link, Add. Leave authentication blank.'),
                    step('3',
                        'In a chat, turn Lazo on under the tools menu and ask "What is waiting on me?"'),
                    const SizedBox(height: 8),
                     Text('CHATGPT',
                        style: TextStyle(
                            color: _lzFg(muted),
                            fontSize: 9.5,
                            letterSpacing: 1.4,
                            fontWeight: FontWeight.w800)),
                    const SizedBox(height: 6),
                    step('1',
                        'Settings \u203a Connectors \u203a Create (developer mode on) \u203a paste the link as the MCP server URL, no auth.'),
                    step('2', 'Start a chat, pick Lazo under Tools.'),
                    const SizedBox(height: 8),
                     Text('CLAUDE CODE / CURSOR',
                        style: TextStyle(
                            color: _lzFg(muted),
                            fontSize: 9.5,
                            letterSpacing: 1.4,
                            fontWeight: FontWeight.w800)),
                    const SizedBox(height: 6),
                    step('1', 'claude mcp add --transport http lazo <link>'),
                  ] else if (connected) ...<Widget>[
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                          color: vGreen.withOpacity(.1),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: vGreen.withOpacity(.5))),
                      child: Row(children: <Widget>[
                         Icon(Icons.check_circle_rounded,
                            color: _lzFg(vGreen), size: 18),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                              'Connected${client.isNotEmpty ? ' \u00b7 last used by $client' : ''}${lastUsed is Timestamp ? ' \u00b7 ${lastUsed.toDate().month}/${lastUsed.toDate().day}' : ''}',
                              style:  TextStyle(
                                  color: _lzFg(vGreen),
                                  fontSize: 12.5,
                                  fontWeight: FontWeight.w800)),
                        ),
                      ]),
                    ),
                    const SizedBox(height: 8),
                     Text(
                        'The link itself is only shown when it is made. Lost it? Make a new one - the old one stops working the moment you do.',
                        style: TextStyle(
                            fontSize: 11.5, color: _lzFg(muted), height: 1.4)),
                  ] else
                     Text('Not connected yet.',
                        style: TextStyle(fontSize: 12.5, color: _lzFg(muted))),
                  const SizedBox(height: 14),
                  Row(children: <Widget>[
                    Expanded(
                      child: FilledButton(
                        style: FilledButton.styleFrom(
                            backgroundColor: plum,
                            elevation: 0,
                            padding: const EdgeInsets.symmetric(vertical: 12),
                            shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(11))),
                        onPressed: _h(busy ? null : () => mint(setSheet)),
                        child: Text(
                            busy
                                ? 'One moment\u2026'
                                : connected
                                    ? 'Make a new link'
                                    : 'Make my link',
                            style: const TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.w800)),
                      ),
                    ),
                    if (connected) ...<Widget>[
                      const SizedBox(width: 8),
                      OutlinedButton(
                        style: OutlinedButton.styleFrom(
                            foregroundColor: _lzFg(muted),
                            side:  BorderSide(color: _lzLine(goldLine)),
                            padding: const EdgeInsets.symmetric(
                                horizontal: 14, vertical: 12)),
                        onPressed: _h(busy
                            ? null
                            : () async {
                                setSheet(() => busy = true);
                                try {
                                  await FirebaseFunctions.instance
                                      .httpsCallable('mcpToken')
                                      .call(<String, dynamic>{
                                    'vendorId': vendorId,
                                    'action': 'revoke'
                                  });
                                  setSheet(() {
                                    connected = false;
                                    url = '';
                                    busy = false;
                                  });
                                  _toast('Disconnected.');
                                } catch (e) {
                                  setSheet(() => busy = false);
                                  _toast(_errText(e));
                                }
                              }),
                        child: const Text('Turn off',
                            style: TextStyle(fontWeight: FontWeight.w700)),
                      ),
                    ],
                  ]),
                ],
              ),
            ),
          ),
        );
      }),
    );
  }
""", r"""    String err = '';

    Future<void> mint(StateSetter setSheet) async {
      setSheet(() {
        busy = true;
        err = '';
      });
      try {
        final HttpsCallable fn =
            FirebaseFunctions.instance.httpsCallable('mcpToken');
        final HttpsCallableResult<dynamic> r = await fn
            .call(<String, dynamic>{'vendorId': vendorId, 'action': 'mint'});
        setSheet(() {
          url = ((r.data as Map?)?['url'] ?? '').toString();
          connected = true;
          busy = false;
        });
      } catch (e) {
        setSheet(() {
          busy = false;
          err = 'Could not create the link: ' + _errText(e);
        });
      }
    }

    Future<void> revoke(StateSetter setSheet) async {
      final bool ok = await _lzConfirm('Turn off the connection?',
          'Your assistant loses access right away. You can make a new link any time.',
          confirm: 'Turn off',
          cancel: 'Keep it',
          danger: true,
          icon: Icons.link_off_rounded);
      if (!ok) return;
      setSheet(() {
        busy = true;
        err = '';
      });
      try {
        await FirebaseFunctions.instance
            .httpsCallable('mcpToken')
            .call(<String, dynamic>{'vendorId': vendorId, 'action': 'revoke'});
        setSheet(() {
          connected = false;
          url = '';
          busy = false;
        });
        _toast('Disconnected.');
      } catch (e) {
        setSheet(() {
          busy = false;
          err = _errText(e);
        });
      }
    }

    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 620),
      builder: (BuildContext ctx) =>
          StatefulBuilder(builder: (BuildContext sc, StateSetter setSheet) {
        Widget step(String n, String t) => Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Container(
                        width: 22,
                        height: 22,
                        alignment: Alignment.center,
                        decoration: const BoxDecoration(
                            color: plumDeep, shape: BoxShape.circle),
                        child: Text(n,
                            style: const TextStyle(
                                color: gold,
                                fontSize: 11,
                                fontWeight: FontWeight.w800))),
                    const SizedBox(width: 10),
                    Expanded(
                        child: SelectableText(t,
                            style: TextStyle(
                                fontSize: 13, color: _lzFg(ink), height: 1.45))),
                  ]),
            );
        return _lzFrame(sc,
            icon: Icons.hub_outlined,
            title: 'Connect Claude or ChatGPT',
            subtitle:
                'Your own assistant, reading your pipeline, threads, money and consults.',
            children: <Widget>[
              if (url.isNotEmpty) ...<Widget>[
                _lzSection('Your private link - shown once'),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                      color: _lzBg(card),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: gold)),
                  child: SelectableText(url,
                      style: TextStyle(
                          fontSize: 11.5,
                          color: _lzFg(ink),
                          fontFamily: 'monospace')),
                ),
                const SizedBox(height: 10),
                _lzNote(Icons.lock_outline_rounded,
                    'Treat it like a password - anyone with it can read your threads. Close this and it\u2019s gone; you can always make a new one.'),
                _lzSection('Claude'),
                step('1',
                    'claude.ai \u203a Settings \u203a Connectors \u203a Add custom connector.'),
                step('2',
                    'Name it Lazo, paste the link, Add. Leave authentication blank.'),
                step('3',
                    'In a chat, turn Lazo on under the tools menu and ask "What is waiting on me?"'),
                _lzSection('ChatGPT'),
                step('1',
                    'Settings \u203a Connectors \u203a Create (developer mode on) \u203a paste the link as the MCP server URL, no auth.'),
                step('2', 'Start a chat, pick Lazo under Tools.'),
                _lzSection('Claude Code / Cursor'),
                step('1', 'claude mcp add --transport http lazo <link>'),
              ] else if (connected) ...<Widget>[
                const SizedBox(height: 14),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                      color: vGreen.withOpacity(.1),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: vGreen.withOpacity(.5))),
                  child: Row(children: <Widget>[
                    Icon(Icons.check_circle_rounded,
                        color: _lzFg(vGreen), size: 18),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                          'Connected${client.isNotEmpty ? ' \u00b7 last used by $client' : ''}${lastUsed is Timestamp ? ' \u00b7 ${lastUsed.toDate().month}/${lastUsed.toDate().day}' : ''}',
                          style: TextStyle(
                              color: _lzFg(vGreen),
                              fontSize: 13,
                              fontWeight: FontWeight.w700)),
                    ),
                  ]),
                ),
                const SizedBox(height: 10),
                _lzNote(Icons.info_outline_rounded,
                    'The link is only shown when it\u2019s made. Lost it? Make a new one - the old one stops working the moment you do.'),
              ] else ...<Widget>[
                _lzSection('Ask it things like'),
                for (final String q in <String>[
                  'Who is waiting on me?',
                  'What is due this week?',
                  'Write a reply to Sarah about the second shooter.',
                ])
                  Container(
                    margin: const EdgeInsets.only(bottom: 6),
                    padding:
                        const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    decoration: BoxDecoration(
                        color: _lzBg(card),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: _lzLine(goldLine))),
                    child: Row(children: <Widget>[
                      Icon(Icons.chat_bubble_outline_rounded,
                          size: 16, color: _lzFg(plum)),
                      const SizedBox(width: 10),
                      Expanded(
                          child: Text(q,
                              style: TextStyle(
                                  fontSize: 13.5, color: _lzFg(ink)))),
                    ]),
                  ),
                const SizedBox(height: 8),
                _lzNote(Icons.verified_user_outlined,
                    'It can reply, add tasks, tag and move things only when you say so. Nothing about other vendors, ever.'),
              ],
              if (err.isNotEmpty) _pv3Err(err),
            ],
            footer: url.isNotEmpty
                ? _lzActions(
                    secondary: 'Turn off',
                    onSecondary: () => revoke(setSheet),
                    primary: 'Copy link',
                    icon: Icons.copy_rounded,
                    busy: busy,
                    onPrimary: () async {
                      await Clipboard.setData(ClipboardData(text: url));
                      _toast('Link copied \u2713');
                    })
                : _lzActions(
                    secondary: connected ? 'Turn off' : 'Not now',
                    onSecondary: connected
                        ? () => revoke(setSheet)
                        : () => Navigator.pop(ctx),
                    primary: busy
                        ? 'One moment\u2026'
                        : connected
                            ? 'Make a new link'
                            : 'Make my link',
                    icon: Icons.link_rounded,
                    busy: busy,
                    onPrimary: () => mint(setSheet)));
      }),
    );
  }
""")

    # Q desk
    rep(r"""    await _lzSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (BuildContext ctx) => SafeArea(
        child: Container(
          margin: const EdgeInsets.fromLTRB(10, 0, 10, 10),
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
          decoration: BoxDecoration(
            color: _lzBg(ivory),
            borderRadius: BorderRadius.circular(26),
            border: Border.all(color: gold.withOpacity(.7)),
            boxShadow: <BoxShadow>[
              BoxShadow(
                  color: Colors.black.withOpacity(.3),
                  blurRadius: 30,
                  offset: const Offset(0, 10))
            ],
          ),
          child: Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
            Container(
                width: 44,
                height: 4,
                margin: const EdgeInsets.only(bottom: 12),
                decoration: BoxDecoration(
                    color: plum.withOpacity(.2),
                    borderRadius: BorderRadius.circular(99))),
             Padding(
              padding: EdgeInsets.only(bottom: 12),
              child: Text('YOUR DESK',
                  style: TextStyle(
                      color: _lzFg(plum),
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
                  _Press(
                    onTap: () {
                      Navigator.pop(ctx);
                      (it[2] as VoidCallback)();
                    },
                    child: Container(
                      decoration: BoxDecoration(
                          color: _lzBg(Colors.white),
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: _lzLine(goldLine))),
                      child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: <Widget>[
                            Icon(it[1] as IconData, color: _lzFg(plum), size: 24),
                            const SizedBox(height: 7),
                            Text(it[0] as String,
                                textAlign: TextAlign.center,
                                style:  TextStyle(
                                    color: _lzFg(ink),
                                    fontSize: 11,
                                    fontWeight: FontWeight.w700)),
                          ]),
                    ),
                  ),
              ],
            ),
          ]),
        ),
      ),
    );
  }
""", r"""    final String bizName = (vd['name'] ?? '').toString();
    await _lzSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      builder: (BuildContext ctx) => _lzFrame(ctx,
          icon: Icons.grid_view_rounded,
          title: 'Your desk',
          subtitle: bizName.isEmpty
              ? 'Jump to any part of your studio.'
              : 'Jump to any part of $bizName.',
          children: <Widget>[
            const SizedBox(height: 14),
            GridView.count(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisCount: 4,
              mainAxisSpacing: 10,
              crossAxisSpacing: 10,
              childAspectRatio: .92,
              children: <Widget>[
                for (final List<dynamic> it in items)
                  _Press(
                    onTap: () {
                      Navigator.pop(ctx);
                      (it[2] as VoidCallback)();
                    },
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 4),
                      decoration: BoxDecoration(
                          color: _lzBg(card),
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: _lzLine(goldLine))),
                      child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: <Widget>[
                            Icon(it[1] as IconData, color: _lzFg(plum), size: 24),
                            const SizedBox(height: 7),
                            Text(it[0] as String,
                                textAlign: TextAlign.center,
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(
                                    color: _lzFg(ink),
                                    fontSize: 11.5,
                                    fontWeight: FontWeight.w700)),
                          ]),
                    ),
                  ),
              ],
            ),
          ]),
    );
  }
""")

    return s
