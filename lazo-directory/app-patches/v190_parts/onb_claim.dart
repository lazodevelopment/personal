  // ============================================================
  // v190: ONBOARDING. A vendor's first five minutes on Lazo: find the
  // listing, prove it, watch it go live. One hero, one search, one honest
  // status. The _onb pieces below also dress the claim and add-business
  // sheets and the review screen. JC-LAZO-ONBOARD-1014-190
  // ============================================================

  String _onbFirstName() {
    String n = '';
    final DocumentSnapshot<Map<String, dynamic>>? s =
        _liveD['user:$_uid']?.latest;
    final Map<String, dynamic>? d = s?.data();
    if (d != null && d['display_name'] != null) {
      n = d['display_name'].toString().trim();
    }
    if (n.isEmpty) {
      n = (FirebaseAuth.instance.currentUser?.displayName ?? '').trim();
    }
    if (n.isEmpty || n.contains('@')) {
      return '';
    }
    return n.split(RegExp(r'\s+')).first;
  }

  // The newest open request (claim or new listing) decides the screen; with
  // none open, the newest declined one does, until the vendor starts over.
  Map<String, dynamic>? _onbPick(
      List<QueryDocumentSnapshot<Map<String, dynamic>>> docs) {
    if (docs.isEmpty) {
      return null;
    }
    final List<Map<String, dynamic>> all = docs
        .map((QueryDocumentSnapshot<Map<String, dynamic>> d) => d.data())
        .toList();
    // a request written a moment ago has no server time yet: it is the newest
    int ms(Map<String, dynamic> m) {
      final dynamic t = m['createdAt'];
      return t is Timestamp ? t.millisecondsSinceEpoch : 4102444800000;
    }

    all.sort((Map<String, dynamic> a, Map<String, dynamic> b) =>
        ms(b).compareTo(ms(a)));
    for (final Map<String, dynamic> m in all) {
      if (m['status'] != 'denied' && m['status'] != 'rejected') {
        return m;
      }
    }
    return _onbRetry ? null : all.first;
  }

  // They watched the review finish: the dashboard arrives with confetti.
  void _onbCelebrateLive() {
    if (!mounted || _confettiShowing) {
      return;
    }
    _toast('You’re live on Lazo. Welcome aboard.');
    if (_reducedMotion(context)) {
      return;
    }
    setState(() => _confettiShowing = true);
    _confettiC?.dispose();
    _confettiC = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 3600));
    _confettiC!.addListener(() {
      if (mounted) {
        setState(() {});
      }
    });
    _confettiC!.addStatusListener((AnimationStatus st) {
      if (st == AnimationStatus.completed && mounted) {
        setState(() => _confettiShowing = false);
      }
    });
    _confettiC!.forward();
  }

  static const LinearGradient _onbNight = LinearGradient(
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
      colors: <Color>[Color(0xFF2A1229), plumDeep, plum]);

  Widget _onbLabel(String t) {
    return Text(t,
        style: TextStyle(
            color: _lzDark ? gold : plum,
            fontSize: 10.5,
            letterSpacing: 2.2,
            fontWeight: FontWeight.w800));
  }

  Widget _onbMonogram(String name, {double size = 48}) {
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: <Color>[plum, plumDeep]),
        border: Border.all(color: gold.withOpacity(.7), width: 1.2),
      ),
      child: Text(_initials(name.isEmpty ? '?' : name),
          style: _serif(
              size: size * .4, weight: FontWeight.w700, color: gold, height: 1)),
    );
  }

  Widget _onbPrimary(
      {required String label,
      VoidCallback? onPressed,
      bool busy = false,
      String busyLabel = '',
      IconData? icon,
      bool compact = false}) {
    final bool on = onPressed != null && !busy;
    return AnimatedOpacity(
      duration: const Duration(milliseconds: 200),
      opacity: on || busy ? 1 : .45,
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(999),
          gradient: const LinearGradient(
              colors: <Color>[Color(0xFFE8CC96), gold, Color(0xFFC9A263)]),
          boxShadow: on && !compact
              ? <BoxShadow>[
                  BoxShadow(
                      color: gold.withOpacity(.35),
                      blurRadius: 18,
                      offset: const Offset(0, 6)),
                ]
              : null,
        ),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            borderRadius: BorderRadius.circular(999),
            onTap: on ? _h(onPressed) : null,
            child: Padding(
              padding: EdgeInsets.symmetric(
                  horizontal: compact ? 16 : 22, vertical: compact ? 10 : 15),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                mainAxisAlignment: MainAxisAlignment.center,
                children: <Widget>[
                  if (busy) ...<Widget>[
                    const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(
                            strokeWidth: 2, color: plumDeep)),
                    const SizedBox(width: 10),
                  ],
                  Text(busy && busyLabel.isNotEmpty ? busyLabel : label,
                      style: TextStyle(
                          color: plumDeep,
                          fontSize: compact ? 13.5 : 15,
                          fontWeight: FontWeight.w800,
                          letterSpacing: .2)),
                  if (!busy && icon != null) ...<Widget>[
                    const SizedBox(width: 8),
                    Icon(icon, size: 18, color: plumDeep),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _onbSecondary(
      {required String label, required VoidCallback? onPressed, IconData? icon}) {
    return OutlinedButton.icon(
      style: OutlinedButton.styleFrom(
        foregroundColor: _lzFg(plum),
        side: BorderSide(color: _lzDark ? gold.withOpacity(.6) : gold),
        shape: const StadiumBorder(),
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 13),
      ),
      onPressed: _h(onPressed),
      icon: Icon(icon ?? Icons.add_rounded, size: 18),
      label: Text(label,
          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
    );
  }

  Widget _onbChip(
      {required String label, required bool selected, VoidCallback? onTap}) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 180),
      decoration: BoxDecoration(
        color: selected ? plum : _lzBg(Colors.white),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: selected ? plum : _lzLine(goldLine)),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(999),
          onTap: _h(onTap, _Tick.select),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
            child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
              if (selected) ...<Widget>[
                const Icon(Icons.check_rounded, size: 15, color: ivory),
                const SizedBox(width: 5),
              ],
              Text(label,
                  style: TextStyle(
                      color: selected ? ivory : _lzFg(plum),
                      fontSize: 13,
                      fontWeight: FontWeight.w600)),
            ]),
          ),
        ),
      ),
    );
  }

  Widget _onbPerk(IconData icon, String label) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
      decoration: BoxDecoration(
        color: ivory.withOpacity(.07),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: gold.withOpacity(.35)),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
        Icon(icon, size: 14, color: gold),
        const SizedBox(width: 6),
        Text(label,
            style: const TextStyle(
                color: ivory, fontSize: 12, fontWeight: FontWeight.w600)),
      ]),
    );
  }

  // Find -> Verify -> Go live, across the hero. step is 0-based.
  Widget _onbSteps(int step) {
    const List<String> labels = <String>[
      'Find your business',
      'Verify ownership',
      'Go live'
    ];
    final List<Widget> row = <Widget>[];
    for (int i = 0; i < labels.length; i++) {
      final bool done = i < step;
      final bool on = i == step;
      row.add(Expanded(
        child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Container(
                height: 3,
                decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(2),
                    color: done || on ? gold : ivory.withOpacity(.18)),
              ),
              const SizedBox(height: 9),
              Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                Container(
                  width: 18,
                  height: 18,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: done ? gold : Colors.transparent,
                    border: Border.all(
                        color: done || on ? gold : ivory.withOpacity(.35)),
                  ),
                  child: done
                      ? const Icon(Icons.check_rounded,
                          size: 12, color: plumDeep)
                      : Text('${i + 1}',
                          style: TextStyle(
                              color: on ? gold : ivory.withOpacity(.55),
                              fontSize: 10,
                              fontWeight: FontWeight.w700)),
                ),
                const SizedBox(width: 7),
                Flexible(
                  child: Text(labels[i],
                      maxLines: 2,
                      style: TextStyle(
                          color: on || done ? ivory : ivory.withOpacity(.55),
                          fontSize: 12,
                          height: 1.25,
                          fontWeight: on ? FontWeight.w700 : FontWeight.w500)),
                ),
              ]),
            ]),
      ));
      if (i < labels.length - 1) {
        row.add(const SizedBox(width: 12));
      }
    }
    return Row(crossAxisAlignment: CrossAxisAlignment.start, children: row);
  }

  Widget _onbHero() {
    final String first = _onbFirstName();
    final bool narrow = MediaQuery.of(context).size.width < 560;
    return Container(
      margin: const EdgeInsets.fromLTRB(18, 14, 18, 0),
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
      child: ClipRRect(
        borderRadius: BorderRadius.circular(28),
        child: Stack(children: <Widget>[
          // the light on the invitation: a soft gold glow in the corner
          Positioned(
            right: -90,
            top: -100,
            child: Container(
              width: 280,
              height: 280,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(colors: <Color>[
                  gold.withOpacity(.26),
                  gold.withOpacity(0)
                ]),
              ),
            ),
          ),
          Padding(
            padding: EdgeInsets.fromLTRB(narrow ? 22 : 34, narrow ? 26 : 34,
                narrow ? 22 : 34, narrow ? 22 : 28),
            child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  const Text('FOR WEDDING PROFESSIONALS',
                      style: TextStyle(
                          color: gold,
                          fontSize: 10.5,
                          letterSpacing: 2.6,
                          fontWeight: FontWeight.w700)),
                  const SizedBox(height: 12),
                  Text(
                      first.isEmpty
                          ? 'Welcome to Lazo.'
                          : 'Welcome to Lazo, $first.',
                      style: _serif(
                          size: narrow ? 32 : 42,
                          weight: FontWeight.w600,
                          color: ivory,
                          height: 1.04)),
                  const SizedBox(height: 10),
                  ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 520),
                    child: Text(
                        'Claim your free profile and start receiving inquiries from verified couples planning their wedding in your city.',
                        style: TextStyle(
                            color: ivory.withOpacity(.82),
                            fontSize: 14.5,
                            height: 1.45)),
                  ),
                  const SizedBox(height: 22),
                  _onbSteps(0),
                  const SizedBox(height: 20),
                  Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
                    _onbPerk(Icons.workspace_premium_rounded, 'Free forever'),
                    _onbPerk(Icons.verified_rounded, 'Verified couples only'),
                    _onbPerk(
                        Icons.auto_awesome_rounded, 'June, your AI assistant'),
                  ]),
                ]),
          ),
        ]),
      ),
    );
  }

  Widget _onbMetroPicker() {
    final List<DropdownMenuItem<String>> items = <DropdownMenuItem<String>>[];
    for (int i = 0; i < _metroIds.length; i++) {
      items.add(DropdownMenuItem<String>(
          value: _metroIds[i], child: Text(_metroNames[i])));
    }
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 2, 8, 2),
      decoration: BoxDecoration(
        color: _lzBg(Colors.white),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: _lzLine(goldLine)),
      ),
      child: Row(children: <Widget>[
        Icon(Icons.place_rounded, color: _lzFg(plum), size: 19),
        const SizedBox(width: 10),
        Text('Where you work',
            style: TextStyle(color: _lzFg(muted), fontSize: 12.5)),
        const SizedBox(width: 12),
        Expanded(
          child: DropdownButtonHideUnderline(
            child: DropdownButton<String>(
              value: _claimMetro,
              dropdownColor: _lzBg(ivory),
              menuMaxHeight: 420,
              isExpanded: true,
              borderRadius: BorderRadius.circular(16),
              icon: Icon(Icons.expand_more_rounded, color: _lzFg(plum)),
              style: TextStyle(
                  color: _lzFg(plum), fontSize: 15, fontWeight: FontWeight.w700),
              items: items,
              onChanged: (String? v) {
                if (v == null) {
                  return;
                }
                setState(() {
                  _claimMetro = v;
                });
                if (_searchC.text.trim().length >= 2) {
                  _runSearch();
                }
              },
            ),
          ),
        ),
      ]),
    );
  }

  Widget _onbSearchField() {
    final bool ready = _searchC.text.trim().length >= 2;
    final OutlineInputBorder rest = OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: BorderSide(color: _lzLine(goldLine)));
    return TextField(
      controller: _searchC,
      textInputAction: TextInputAction.search,
      onChanged: (String s) {
        _debounceT?.cancel();
        _debounceT = Timer(const Duration(milliseconds: 400), () {
          _runSearch();
        });
        setState(() {});
      },
      onSubmitted: (String s) {
        _debounceT?.cancel();
        _runSearch();
      },
      cursorColor: _lzFg(plum),
      style: TextStyle(
          color: _lzFg(ink), fontSize: 16, fontWeight: FontWeight.w500),
      decoration: InputDecoration(
        hintText: 'Your business name',
        hintStyle: TextStyle(color: _lzFg(muted).withOpacity(.8), fontSize: 16),
        prefixIcon: Icon(Icons.search_rounded, color: _lzFg(plum)),
        suffixIcon: Padding(
          padding: const EdgeInsets.fromLTRB(0, 6, 6, 6),
          child: _searching
              ? const Padding(
                  padding: EdgeInsets.all(12),
                  child: SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: gold)))
              : _onbPrimary(
                  label: 'Search',
                  compact: true,
                  onPressed: ready
                      ? () {
                          _debounceT?.cancel();
                          _runSearch();
                        }
                      : null),
        ),
        filled: true,
        fillColor: _lzBg(Colors.white),
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 16, vertical: 18),
        enabledBorder: rest,
        border: rest,
        focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: const BorderSide(color: gold, width: 1.6)),
      ),
    );
  }

  Widget _claimView() {
    _stopPendingMotion();
    final bool narrow = MediaQuery.of(context).size.width < 560;
    return SingleChildScrollView(
      padding: const EdgeInsets.only(bottom: 48),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 760),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              _onbHero(),
              Padding(
                padding: const EdgeInsets.fromLTRB(18, 16, 18, 0),
                child: _glass(
                  radius: 24,
                  padding: EdgeInsets.fromLTRB(
                      narrow ? 16 : 22, 20, narrow ? 16 : 22, 18),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      _onbLabel('STEP 1 · FIND YOUR BUSINESS'),
                      const SizedBox(height: 6),
                      Text(
                          'Most wedding businesses are already on Lazo. Search the name couples know you by.',
                          style: TextStyle(
                              color: _lzFg(muted), fontSize: 13, height: 1.4)),
                      const SizedBox(height: 16),
                      _onbMetroPicker(),
                      const SizedBox(height: 10),
                      _onbSearchField(),
                    ],
                  ),
                ),
              ),
              _resultsView(),
              _inviteCodeRow(),
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

  Widget _onbNewBusinessCard(
      {required String title,
      required String body,
      IconData icon = Icons.storefront_rounded,
      bool compact = false}) {
    return Container(
      padding: EdgeInsets.all(compact ? 16 : 22),
      decoration: BoxDecoration(
        color: _lzBg(const Color(0xFFF6EEE2)),
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: _lzLine(goldLine)),
      ),
      child: Row(children: <Widget>[
        if (!compact) ...<Widget>[
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
                shape: BoxShape.circle, color: gold.withOpacity(.22)),
            child: Icon(icon, color: _lzFg(plum), size: 24),
          ),
          const SizedBox(width: 14),
        ],
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(title,
                  style: _serif(
                      size: compact ? 18 : 21,
                      weight: FontWeight.w700,
                      height: 1.15)),
              const SizedBox(height: 4),
              Text(body,
                  style: TextStyle(
                      color: _lzFg(muted), fontSize: 12.5, height: 1.4)),
              const SizedBox(height: 12),
              _onbSecondary(
                  label: 'Add your business',
                  icon: Icons.add_business_rounded,
                  onPressed: _addListing),
            ],
          ),
        ),
      ]),
    );
  }

  Widget _onbSkeleton() {
    final Color bar = _lzDark
        ? ivory.withOpacity(.08)
        : const Color(0xFFEFE6D8);
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: _glass(
        radius: 20,
        padding: const EdgeInsets.all(14),
        child: Row(children: <Widget>[
          Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(shape: BoxShape.circle, color: bar)),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Container(
                      height: 14,
                      width: 180,
                      decoration: BoxDecoration(
                          color: bar, borderRadius: BorderRadius.circular(6))),
                  const SizedBox(height: 8),
                  Container(
                      height: 10,
                      width: 120,
                      decoration: BoxDecoration(
                          color: bar, borderRadius: BorderRadius.circular(6))),
                ]),
          ),
        ]),
      ),
    );
  }

  Widget _onbResultCard(Map<String, dynamic> v) {
    final String vName = v['name'] == null ? '' : v['name'].toString();
    final String vAddr = v['address'] == null ? '' : v['address'].toString();
    final String vMetro =
        v['metroId'] == null ? '' : _metroLabel(v['metroId'].toString());
    String cat = '';
    if (v['categories'] is List && (v['categories'] as List).isNotEmpty) {
      final int ci = _catIds.indexOf((v['categories'] as List).first.toString());
      if (ci >= 0) {
        cat = _catNames[ci];
      }
    }
    final List<String> bits = <String>[
      if (cat.isNotEmpty) cat,
      if (vAddr.isNotEmpty) vAddr,
      if (vMetro.isNotEmpty && !vAddr.contains(vMetro)) vMetro,
    ];
    final bool claimed = v['claimStatus'] == 'claimed';
    final bool narrow = MediaQuery.of(context).size.width < 520;
    final Widget cta = claimed
        ? Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: _lzBg(const Color(0xFFF1E9E0)),
              borderRadius: BorderRadius.circular(999),
              border: Border.all(color: _lzLine(goldLine)),
            ),
            child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
              Icon(Icons.lock_rounded, size: 13, color: _lzFg(muted)),
              const SizedBox(width: 5),
              Text('Claimed',
                  style: TextStyle(
                      fontSize: 12,
                      color: _lzFg(muted),
                      fontWeight: FontWeight.w700)),
            ]),
          )
        : _onbPrimary(
            label: narrow ? 'Claim' : 'This is mine',
            compact: true,
            onPressed: _submitting
                ? null
                : () {
                    _submitClaim(v);
                  });
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: _glass(
        radius: 20,
        padding: const EdgeInsets.all(14),
        child: Row(children: <Widget>[
          _onbMonogram(vName),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(vName,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: _serif(
                        size: 20, weight: FontWeight.w700, height: 1.12)),
                if (bits.isNotEmpty) ...<Widget>[
                  const SizedBox(height: 4),
                  Text(bits.join(' · '),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                          color: _lzFg(muted), fontSize: 12.5, height: 1.35)),
                ],
              ],
            ),
          ),
          const SizedBox(width: 10),
          cta,
        ]),
      ),
    );
  }

  Widget _resultsView() {
    const EdgeInsets pad = EdgeInsets.fromLTRB(18, 14, 18, 0);
    final String q = _searchC.text.trim();
    final String metroName = _metroLabel(_claimMetro);
    if (_searching && _results.isEmpty) {
      return Padding(
          padding: pad,
          child: Column(
              children: <Widget>[_onbSkeleton(), _onbSkeleton(), _onbSkeleton()]));
    }
    if (!_searched) {
      return Padding(
        padding: pad,
        child: _onbNewBusinessCard(
            title: 'Not listed yet?',
            body:
                'Add your business in about two minutes. We verify it, then your profile goes live.'),
      );
    }
    if (_searchError != null) {
      return Padding(
        padding: pad,
        child: _glass(
          radius: 20,
          child: Row(children: <Widget>[
            Icon(Icons.wifi_off_rounded, color: _lzFg(muted)),
            const SizedBox(width: 12),
            Expanded(
                child: Text(_searchError ?? '',
                    style: TextStyle(color: _lzFg(muted), fontSize: 13))),
            TextButton(
                onPressed: _h(_runSearch),
                child: Text('Try again',
                    style: TextStyle(
                        color: _lzFg(plum), fontWeight: FontWeight.w700))),
          ]),
        ),
      );
    }
    if (_results.isEmpty) {
      return Padding(
        padding: pad,
        child: _onbNewBusinessCard(
            icon: Icons.travel_explore_rounded,
            title: 'No listing called “$q”' +
                (metroName.isEmpty ? '' : ' in $metroName') +
                ' yet.',
            body:
                'Check the spelling, or add your business now. It takes about two minutes, and our team usually verifies it the same day.'),
      );
    }
    final List<Widget> cards = <Widget>[
      Padding(
        padding: const EdgeInsets.fromLTRB(4, 0, 4, 10),
        child: Text(
            _results.length == 1
                ? '1 match · tap the one that’s yours'
                : '${_results.length} matches · tap the one that’s yours',
            style: TextStyle(
                color: _lzFg(muted),
                fontSize: 12,
                fontWeight: FontWeight.w600,
                letterSpacing: .3)),
      ),
    ];
    for (final Map<String, dynamic> v in _results) {
      cards.add(_onbResultCard(v));
    }
    cards.add(const SizedBox(height: 6));
    cards.add(_onbNewBusinessCard(
        compact: true,
        title: 'Don’t see yours?',
        body: 'Add it in about two minutes.'));
    return Padding(
      padding: pad,
      child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch, children: cards),
    );
  }

  // ---- the sheets: claim and add-business share one frame ----

  Widget _onbSheetSteps(int step, List<String> steps) {
    final List<Widget> row = <Widget>[];
    for (int i = 0; i < steps.length; i++) {
      final bool lit = i <= step;
      row.add(Expanded(
        child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              AnimatedContainer(
                duration: const Duration(milliseconds: 280),
                curve: Curves.easeOutCubic,
                height: 3,
                decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(2),
                    color: lit ? gold : ivory.withOpacity(.2)),
              ),
              const SizedBox(height: 7),
              Text(steps[i],
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                      color: i == step
                          ? ivory
                          : ivory.withOpacity(lit ? .75 : .45),
                      fontSize: 11,
                      fontWeight:
                          i == step ? FontWeight.w700 : FontWeight.w500)),
            ]),
      ));
      if (i < steps.length - 1) {
        row.add(const SizedBox(width: 8));
      }
    }
    return Row(children: row);
  }

  // A plum header with the step bars, a scrolling body, and a footer that
  // never scrolls away. Fixed width so a field never resizes the sheet.
  Widget _onbSheet({
    required BuildContext ctx,
    required IconData icon,
    required String eyebrow,
    required String title,
    String subtitle = '',
    int step = -1,
    List<String> steps = const <String>[],
    required List<Widget> body,
    required Widget footer,
  }) {
    final Size sz = MediaQuery.of(ctx).size;
    final bool phone = sz.width < 600;
    return Dialog(
      backgroundColor: _lzBg(ivory),
      insetPadding: EdgeInsets.symmetric(
          horizontal: phone ? 12 : 40, vertical: phone ? 20 : 32),
      clipBehavior: Clip.antiAlias,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(28)),
      child: ConstrainedBox(
        constraints: BoxConstraints(
            maxWidth: 500, maxHeight: sz.height * (phone ? .92 : .88)),
        child: SizedBox(
          width: 500,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              Container(
                padding: const EdgeInsets.fromLTRB(24, 24, 24, 20),
                decoration: const BoxDecoration(gradient: _onbNight),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Row(children: <Widget>[
                      Container(
                        width: 46,
                        height: 46,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: gold.withOpacity(.14),
                          border: Border.all(color: gold.withOpacity(.6)),
                        ),
                        child: Icon(icon, color: gold, size: 22),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Text(eyebrow,
                                style: const TextStyle(
                                    color: gold,
                                    fontSize: 10.5,
                                    letterSpacing: 2.2,
                                    fontWeight: FontWeight.w800)),
                            const SizedBox(height: 4),
                            Text(title,
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                                style: _serif(
                                    size: 25,
                                    weight: FontWeight.w700,
                                    color: ivory,
                                    height: 1.08)),
                          ],
                        ),
                      ),
                    ]),
                    if (subtitle.isNotEmpty) ...<Widget>[
                      const SizedBox(height: 12),
                      Text(subtitle,
                          style: TextStyle(
                              color: ivory.withOpacity(.8),
                              fontSize: 13,
                              height: 1.4)),
                    ],
                    if (steps.isNotEmpty) ...<Widget>[
                      const SizedBox(height: 18),
                      _onbSheetSteps(step, steps),
                    ],
                  ],
                ),
              ),
              Flexible(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.fromLTRB(24, 22, 24, 8),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: body,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.fromLTRB(12, 12, 20, 16),
                decoration: BoxDecoration(
                    border:
                        Border(top: BorderSide(color: _lzLine(goldLine)))),
                child: footer,
              ),
            ],
          ),
        ),
      ),
    );
  }

  InputDecoration _onbDeco(String label,
      {String helper = '', IconData? icon}) {
    final OutlineInputBorder rest = OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: BorderSide(color: _lzLine(goldLine)));
    return InputDecoration(
      labelText: label,
      helperText: helper.isEmpty ? null : helper,
      helperMaxLines: 2,
      prefixIcon:
          icon == null ? null : Icon(icon, size: 19, color: _lzFg(muted)),
      labelStyle: TextStyle(color: _lzFg(muted), fontSize: 14),
      floatingLabelStyle: TextStyle(
          color: _lzFg(plum), fontSize: 13, fontWeight: FontWeight.w700),
      helperStyle: TextStyle(color: _lzFg(muted), fontSize: 11.5),
      filled: true,
      fillColor: _lzBg(Colors.white),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      enabledBorder: rest,
      disabledBorder: rest,
      border: rest,
      focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: gold, width: 1.6)),
    );
  }

  Widget _onbProof(
      {required Uint8List? bytes,
      required bool isPdf,
      required String fileName,
      required bool busy,
      required VoidCallback onPick}) {
    final Widget inner;
    if (bytes == null) {
      inner = Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 22),
        decoration: BoxDecoration(
          color: _lzBg(const Color(0xFFFBF5EA)),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(
              color: _lzDark ? gold.withOpacity(.45) : gold.withOpacity(.75),
              width: 1.2),
        ),
        child: Column(children: <Widget>[
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
                shape: BoxShape.circle, color: gold.withOpacity(.2)),
            child: Icon(Icons.upload_file_rounded, color: _lzFg(plum), size: 24),
          ),
          const SizedBox(height: 10),
          Text('Upload a document',
              style: TextStyle(
                  color: _lzFg(plum),
                  fontSize: 14.5,
                  fontWeight: FontWeight.w800)),
          const SizedBox(height: 4),
          Text(
              'A PDF or photo of your business license, insurance certificate, EIN letter or a utility bill.',
              textAlign: TextAlign.center,
              style:
                  TextStyle(color: _lzFg(muted), fontSize: 12, height: 1.4)),
        ]),
      );
    } else {
      inner = Container(
        width: double.infinity,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: _lzBg(Colors.white),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: vGreen, width: 1.2),
        ),
        child: Row(children: <Widget>[
          ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: SizedBox(
              width: 56,
              height: 56,
              child: isPdf
                  ? Container(
                      color: _lzBg(const Color(0xFFF3ECE5)),
                      child: Icon(Icons.picture_as_pdf_rounded,
                          color: _lzFg(plum), size: 28))
                  : Image.memory(bytes, fit: BoxFit.cover),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(children: const <Widget>[
                  Icon(Icons.check_circle_rounded, color: vGreen, size: 16),
                  SizedBox(width: 6),
                  Text('Attached',
                      style: TextStyle(
                          color: vGreen,
                          fontSize: 12.5,
                          fontWeight: FontWeight.w800)),
                ]),
                const SizedBox(height: 3),
                Text(fileName.isEmpty ? 'Your document' : fileName,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                        color: _lzFg(ink),
                        fontSize: 13,
                        fontWeight: FontWeight.w600)),
              ],
            ),
          ),
          Text('Replace',
              style: TextStyle(
                  color: _lzFg(plum),
                  fontSize: 12.5,
                  fontWeight: FontWeight.w800)),
          const SizedBox(width: 6),
        ]),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: busy ? null : onPick,
            borderRadius: BorderRadius.circular(18),
            child: inner,
          ),
        ),
        const SizedBox(height: 10),
        Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
          Padding(
            padding: const EdgeInsets.only(top: 1),
            child: Icon(Icons.lock_rounded, size: 13, color: _lzFg(muted)),
          ),
          const SizedBox(width: 6),
          Expanded(
            child: Text(
                'Private. Only the Lazo verification team sees this document. It never appears on your profile.',
                style:
                    TextStyle(color: _lzFg(muted), fontSize: 11.5, height: 1.4)),
          ),
        ]),
      ],
    );
  }

  Widget _onbError(String? msg) {
    if (msg == null || msg.isEmpty) {
      return const SizedBox.shrink();
    }
    const Color red = Color(0xFFB3413A);
    return Padding(
      padding: const EdgeInsets.only(top: 14),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
        decoration: BoxDecoration(
          color: _lzBg(const Color(0xFFF7E8E6)),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: red.withOpacity(.6)),
        ),
        child: Row(children: <Widget>[
          Icon(Icons.error_outline_rounded, size: 17, color: _lzFg(red)),
          const SizedBox(width: 8),
          Expanded(
              child: Text(msg,
                  style: TextStyle(color: _lzFg(red), fontSize: 12.5))),
        ]),
      ),
    );
  }

  Widget _onbFooter(
      {required String backLabel,
      required VoidCallback? onBack,
      required Widget primary}) {
    return Row(children: <Widget>[
      TextButton(
        onPressed: _h(onBack),
        style: TextButton.styleFrom(
            foregroundColor: _lzFg(muted),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12)),
        child: Text(backLabel,
            style: const TextStyle(fontWeight: FontWeight.w600)),
      ),
      const Spacer(),
      primary,
    ]);
  }

