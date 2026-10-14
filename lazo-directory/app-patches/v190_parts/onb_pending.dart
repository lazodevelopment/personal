  // v190: the review screen. One honest status, a three-step timeline and
  // something useful to do while they wait. Declined requests can start over;
  // an approved request says so instead of spinning (Olivia Layne, 2026-10-14).
  Widget _onbTimelineRow(
      {required String title,
      required String sub,
      required int state, // 0 upcoming, 1 active, 2 done, 3 declined
      bool last = false}) {
    final Color ring = state == 0 ? _lzLine(goldLine) : (state == 3 ? const Color(0xFFB3413A) : gold);
    Widget dot;
    if (state == 2) {
      dot = Container(
          width: 26,
          height: 26,
          decoration: const BoxDecoration(shape: BoxShape.circle, color: gold),
          child: const Icon(Icons.check_rounded, size: 16, color: plumDeep));
    } else if (state == 3) {
      dot = Container(
          width: 26,
          height: 26,
          decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: const Color(0xFFB3413A).withOpacity(.12),
              border: Border.all(color: ring, width: 1.4)),
          child: const Icon(Icons.close_rounded,
              size: 15, color: Color(0xFFB3413A)));
    } else {
      dot = Container(
        width: 26,
        height: 26,
        alignment: Alignment.center,
        decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: state == 1 ? gold.withOpacity(.16) : Colors.transparent,
            border: Border.all(color: ring, width: 1.4)),
        child: state == 1
            ? ScaleTransition(
                scale: _pulseC,
                child: Container(
                    width: 9,
                    height: 9,
                    decoration: const BoxDecoration(
                        shape: BoxShape.circle, color: gold)))
            : null,
      );
    }
    return IntrinsicHeight(
      child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
        Column(children: <Widget>[
          dot,
          if (!last)
            Expanded(
              child: Container(
                  width: 1.4,
                  margin: const EdgeInsets.symmetric(vertical: 4),
                  color: state == 2 ? gold : _lzLine(goldLine)),
            ),
        ]),
        const SizedBox(width: 14),
        Expanded(
          child: Padding(
            padding: EdgeInsets.only(top: 3, bottom: last ? 0 : 18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(title,
                    style: TextStyle(
                        color: state == 0 ? _lzFg(muted) : _lzFg(ink),
                        fontSize: 14.5,
                        fontWeight: FontWeight.w700)),
                const SizedBox(height: 3),
                Text(sub,
                    style: TextStyle(
                        color: _lzFg(muted), fontSize: 12.5, height: 1.4)),
              ],
            ),
          ),
        ),
      ]),
    );
  }

  Widget _onbTip(IconData icon, String title, String body, {VoidCallback? onTap}) {
    final Widget row = Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
        Container(
          width: 38,
          height: 38,
          decoration: BoxDecoration(
              shape: BoxShape.circle, color: gold.withOpacity(.18)),
          child: Icon(icon, size: 19, color: _lzFg(plum)),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(title,
                  style: TextStyle(
                      color: _lzFg(ink),
                      fontSize: 14,
                      fontWeight: FontWeight.w700)),
              const SizedBox(height: 2),
              Text(body,
                  style: TextStyle(
                      color: _lzFg(muted), fontSize: 12.5, height: 1.4)),
            ],
          ),
        ),
        if (onTap != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Icon(Icons.chevron_right_rounded, color: _lzFg(muted)),
          ),
      ]),
    );
    if (onTap == null) {
      return row;
    }
    return InkWell(
        onTap: _h(onTap), borderRadius: BorderRadius.circular(12), child: row);
  }

  Widget _pendingView(Map<String, dynamic> claim) {
    _onbSawPending = true;
    final String name = claim['businessName'] == null
        ? 'your business'
        : claim['businessName'].toString();
    final String status =
        claim['status'] == null ? 'pending' : claim['status'].toString();
    final bool isClaim = claim['claimantRole'] != null;
    final String noun = isClaim ? 'claim' : 'listing';

    // v148: a request the AI reviewer never finished used to spin forever.
    // After three minutes it tells the truth: a person will finish the review.
    final dynamic createdAt = claim['createdAt'];
    final bool stale = status == 'pending' &&
        createdAt is Timestamp &&
        DateTime.now().difference(createdAt.toDate()).inMinutes >= 3;
    final bool declined = status == 'denied' || status == 'rejected';
    final bool approved = status == 'approved';
    final bool human = !declined && !approved && (status == 'needs_review' || stale);
    final bool checking = !declined && !approved && !human;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (checking || human) {
        _startPendingMotion();
      } else {
        _stopPendingMotion();
      }
    });
    final String submittedOn = createdAt is Timestamp
        ? 'Received ' + _shortDate(createdAt.toDate())
        : 'Received just now';

    const List<String> phrases = <String>[
      'Reading your document…',
      'Matching your business details…',
      'Checking your public listing…',
      'Confirming ownership signals…',
      'Almost there…',
    ];

    final String eyebrow;
    final String line;
    final IconData sealIcon;
    if (declined) {
      final String reason =
          claim['denyReason'] == null ? '' : claim['denyReason'].toString().trim();
      eyebrow = 'ABOUT YOUR ' + noun.toUpperCase();
      line = reason.isEmpty
          ? 'We weren’t able to verify this business with the information provided. You can start over with a different document, or write to us and we’ll help.'
          : reason;
      sealIcon = Icons.info_outline_rounded;
    } else if (approved) {
      eyebrow = 'APPROVED';
      line =
          'You’re verified. We’re opening your dashboard now. If it doesn’t appear in a minute or two, write to vendors@meetlazo.com and we’ll finish it by hand.';
      sealIcon = Icons.celebration_rounded;
    } else if (human) {
      eyebrow = 'IN REVIEW';
      line =
          'A specialist on our verification team is reviewing your $noun, usually within a day. Nothing else is needed from you. We’ll email you the moment you’re live.';
      sealIcon = Icons.person_search_rounded;
    } else {
      eyebrow = 'VERIFYING';
      line = phrases[_phrase % phrases.length];
      sealIcon = Icons.verified_user_rounded;
    }

    final Widget seal = checking
        ? SizedBox(
            width: 112,
            height: 112,
            child: Stack(alignment: Alignment.center, children: <Widget>[
              RotationTransition(
                turns: _spinC,
                child: CustomPaint(
                    size: const Size(112, 112), painter: _ArcPainter()),
              ),
              ScaleTransition(
                scale: _pulseC,
                child: Container(
                  width: 62,
                  height: 62,
                  decoration:
                      const BoxDecoration(shape: BoxShape.circle, color: gold),
                  child: Icon(sealIcon, color: plumDeep, size: 30),
                ),
              ),
            ]),
          )
        : Container(
            width: 68,
            height: 68,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: declined ? ivory.withOpacity(.1) : gold,
              border: declined ? Border.all(color: gold.withOpacity(.6)) : null,
              boxShadow: declined
                  ? null
                  : <BoxShadow>[
                      BoxShadow(color: gold.withOpacity(.35), blurRadius: 24)
                    ],
            ),
            child: Icon(sealIcon, color: declined ? gold : plumDeep, size: 32),
          );

    final Widget header = Container(
      margin: const EdgeInsets.fromLTRB(18, 14, 18, 0),
      padding: const EdgeInsets.fromLTRB(26, 30, 26, 28),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        gradient: _onbNight,
        border: Border.all(color: gold.withOpacity(.55)),
        boxShadow: <BoxShadow>[
          BoxShadow(
              color: plumDeep.withOpacity(_lzDark ? .5 : .22),
              blurRadius: 36,
              offset: const Offset(0, 16)),
        ],
      ),
      child: Column(children: <Widget>[
        seal,
        const SizedBox(height: 18),
        Text(eyebrow,
            style: const TextStyle(
                color: gold,
                fontSize: 10.5,
                letterSpacing: 2.6,
                fontWeight: FontWeight.w800)),
        const SizedBox(height: 8),
        Text(name,
            textAlign: TextAlign.center,
            style: _serif(
                size: 32, weight: FontWeight.w600, color: ivory, height: 1.05)),
        const SizedBox(height: 12),
        ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: AnimatedSwitcher(
            duration: const Duration(milliseconds: 450),
            child: Text(line,
                key: ValueKey<String>(line),
                textAlign: TextAlign.center,
                style: TextStyle(
                    color: ivory.withOpacity(.85), fontSize: 14, height: 1.45)),
          ),
        ),
        if (checking) ...<Widget>[
          const SizedBox(height: 10),
          const Text('This usually takes under a minute.',
              style: TextStyle(color: Color(0xFFCDB9CE), fontSize: 12)),
        ],
        if (declined) ...<Widget>[
          const SizedBox(height: 20),
          Wrap(
              alignment: WrapAlignment.center,
              spacing: 10,
              runSpacing: 10,
              children: <Widget>[
                _onbPrimary(
                    label: 'Start over',
                    icon: Icons.arrow_forward_rounded,
                    onPressed: () {
                      setState(() {
                        _onbRetry = true;
                      });
                    }),
                TextButton(
                  onPressed:
                      _h(() => _openUrl('mailto:vendors@meetlazo.com')),
                  style: TextButton.styleFrom(
                      foregroundColor: gold,
                      padding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 14)),
                  child: const Text('Email our team',
                      style: TextStyle(fontWeight: FontWeight.w700)),
                ),
              ]),
        ],
      ]),
    );

    final Widget timeline = Padding(
      padding: const EdgeInsets.fromLTRB(18, 16, 18, 0),
      child: _glass(
        radius: 24,
        padding: const EdgeInsets.fromLTRB(22, 20, 22, 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            _onbLabel('WHERE THINGS STAND'),
            const SizedBox(height: 16),
            _onbTimelineRow(
                title: isClaim ? 'Claim submitted' : 'Business submitted',
                sub: submittedOn,
                state: 2),
            _onbTimelineRow(
                title: 'Verification',
                sub: declined
                    ? 'Not approved'
                    : approved
                        ? 'Verified by the Lazo team'
                        : human
                            ? 'With our verification team · usually within a day'
                            : 'Checking your document and details',
                state: declined ? 3 : (approved ? 2 : 1)),
            _onbTimelineRow(
                title: 'Your profile goes live',
                sub: approved
                    ? 'Opening your dashboard…'
                    : 'Leads, reviews and June, your AI assistant, all in one place',
                state: approved ? 1 : 0,
                last: true),
          ],
        ),
      ),
    );

    final Widget tips = Padding(
      padding: const EdgeInsets.fromLTRB(18, 16, 18, 0),
      child: _glass(
        radius: 24,
        padding: const EdgeInsets.fromLTRB(22, 20, 22, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            _onbLabel('WHILE YOU WAIT'),
            const SizedBox(height: 8),
            _onbTip(Icons.photo_library_rounded, 'Pick your six best photos',
                'Profiles with six or more photos get the most inquiries. You’ll add them the moment you’re live.'),
            _onbTip(Icons.sell_rounded, 'Decide your starting price',
                'Couples filter by budget, so a starting price brings you better-fit leads.'),
            if (kIsWeb)
              _onbTip(Icons.phone_iphone_rounded, 'Get the Lazo app',
                  'New inquiries arrive as notifications, so you can be the first to reply.',
                  onTap: () => _openUrl('https://meetlazo.com/app/'))
            else
              _onbTip(Icons.notifications_active_rounded,
                  'Keep notifications on',
                  'New inquiries arrive as notifications, so you can be the first to reply.'),
          ],
        ),
      ),
    );

    return SingleChildScrollView(
      padding: const EdgeInsets.only(bottom: 48),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 600),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              header,
              timeline,
              if (!declined && !approved) tips,
              Padding(
                padding: const EdgeInsets.fromLTRB(18, 22, 18, 0),
                child: Center(
                  child: InkWell(
                    onTap: () => _openUrl('mailto:vendors@meetlazo.com'),
                    child: Text('Questions? vendors@meetlazo.com',
                        style: TextStyle(color: _lzFg(muted), fontSize: 12.5)),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

