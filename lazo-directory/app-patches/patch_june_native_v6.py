"""patch_june_native_v6.py - JC-LAZO-JUNE-NATIVE-1013-006: June's hero for the dashboards.
JuneNative_v5.txt -> JuneNative_v6.txt. layout 'hero' (ported from Jovi's, in plum and gold):
  - her greeting in the serif face, then the core on the dashboard's own photo + scrim (no box) beside her
    line from the brief, typed in while the core moves; tap the core to stop her, long-press to talk
  - today's one thing as one pill (Do it, Done, the streak), one "Ask June" bar with the mic inside
  - chat opens as a sheet over the dashboard, with the core, chips, radio, focus and the whole dock in it
  - wide screens (>= 760): two columns - core and greeting on the left, line, pill and bar on the right
  - no stat tiles here: the dashboards draw their own (live, from their own streams) under the hero
  - Reduce Motion honoured; the core idles while the hero is scrolled off screen
  python app-patches\\patch_june_native_v6.py
"""
from pathlib import Path
HERE = Path(__file__).resolve().parent


def rep(s, old, new, label, count=1):
    n = s.count(old)
    if n != count:
        raise SystemExit(f"{label}: anchor found {n}x, wanted {count}: {old[:80]!r}")
    return s.replace(old, new)


s = (HERE / "JuneNative_v5.txt").read_text(encoding="utf-8-sig")
s = rep(s, "// Build ID: JC-LAZO-JUNE-NATIVE-1013-005 (005:",
        "// Build ID: JC-LAZO-JUNE-NATIVE-1013-006 (006: layout 'hero' for the dashboards - greeting, core + her line typed in, one pill, one Ask June bar, chat in a sheet; base 005) (005:", "build id")
s = rep(s, "//             layout 'full' (the hub) | 'deck' (across the top of a dashboard; the host draws the surface).",
        "//             layout 'full' (the hub) | 'hero' (the top of a dashboard: greeting, core, her line, one pill,\n//             one bar; the host draws the photo and its own stat tiles) | 'deck' (the older dashboard band).", "doc")

# ---- state
s = rep(s, "  bool _postBusy = false;\n",
        """  bool _postBusy = false;

  // JC-LAZO-JUNE-NATIVE-1013-006: the hero
  int _typed = 0;
  String _typedFor = '';
  Timer? _typeT;
  bool _entered = false;
  bool _onScreen = true;
  int _visTick = 0;
""", "hero state")
s = rep(s, "  void dispose() {\n    _focusT?.cancel();\n    _ticker.dispose();\n",
        "  void dispose() {\n    _focusT?.cancel();\n    _typeT?.cancel();\n    _ticker.dispose();\n", "dispose")

# ---- the core idles while the hero is off screen
s = rep(s, """  void _tick(Duration now) {
    final double dt = _last == Duration.zero ? 0.016 : math.min(0.1, (now - _last).inMicroseconds / 1e6);
    _last = now;
    _phase += dt;
""", """  void _tick(Duration now) {
    final double dt = _last == Duration.zero ? 0.016 : math.min(0.1, (now - _last).inMicroseconds / 1e6);
    _last = now;
    _phase += dt;
    if (widget.layout == 'hero' && ++_visTick % 20 == 0) _checkOnScreen();
    if (!_onScreen && !_voice.speaking && _radioName.isEmpty) return;
""", "tick idle")

s = rep(s, "  // ---- data\n", """  void _checkOnScreen() {
    try {
      final RenderObject? ro = context.findRenderObject();
      if (ro is! RenderBox || !ro.hasSize || !ro.attached) return;
      final Offset top = ro.localToGlobal(Offset.zero);
      final double h = MediaQuery.of(context).size.height;
      final bool on = top.dy + ro.size.height > -40 && top.dy < h + 40;
      if (on != _onScreen) setState(() => _onScreen = on);
    } catch (_) {}
  }

  // her line typed in while the core moves (Reduce Motion shows it whole)
  void _typeIn(String text) {
    if (text == _typedFor) return;
    _typeT?.cancel();
    _typedFor = text;
    final bool reduce = MediaQuery.maybeOf(context)?.disableAnimations ?? false;
    if (reduce || text.isEmpty) {
      setState(() => _typed = text.length);
      return;
    }
    setState(() => _typed = 0);
    _typeT = Timer.periodic(const Duration(milliseconds: 22), (Timer t) {
      if (!mounted || _typedFor != text) {
        t.cancel();
        return;
      }
      setState(() => _typed = math.min(text.length, _typed + 1));
      if (_typed >= text.length) t.cancel();
    });
  }

  // ---- data
""", "visibility + typing")

# ---- the hero
s = rep(s, "  Widget _deck(BuildContext context) {", r"""  // ---------------------------------------------------------------- the hero (JC-LAZO-JUNE-NATIVE-1013-006)
  String _heroGreeting() {
    final int h = DateTime.now().hour;
    final String tod = h < 4 ? 'Still up' : h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
    String who = '';
    if (_couple) {
      final String names = _s(_map(_snap['couple'])['names']).trim();
      if (names.isNotEmpty && names.length <= 24) who = names;
    }
    if (who.isEmpty) {
      final String dn = (FirebaseAuth.instance.currentUser?.displayName ?? '').trim();
      if (dn.isNotEmpty) who = dn.split(' ').first;
    }
    return who.isEmpty ? '$tod.' : '$tod, $who.';
  }

  String _heroLine() {
    final String brief = _s(_map(_snap['brief'])['text']).trim();
    if (brief.isNotEmpty) {
      final RegExp sent = RegExp(r'^[\s\S]*?[.!?](?=\s|$)');
      final String first = (sent.firstMatch(brief)?.group(0) ?? brief).trim();
      // the brief opens with its own greeting; the hero already greeted, so take the sentence after it
      if (RegExp(r'^(good (morning|afternoon|evening)|hello|hi|hey|morning|evening)\b', caseSensitive: false).hasMatch(first) && brief.length > first.length + 8) {
        final RegExpMatch? m2 = sent.firstMatch(brief.substring(first.length).trim());
        if (m2 != null) return m2.group(0)!.trim();
      }
      return first;
    }
    if (_loading && _snap.isEmpty) return '';
    final String h = _headline();
    return h == 'Reading your day…' ? '' : h;
  }

  Widget _heroPill() {
    final Map<String, dynamic> t = _map(_snap['todayTask']);
    final Map<String, dynamic> st = _map(_snap['streak']);
    if (t.isEmpty) return const SizedBox.shrink();
    final bool done = st['doneToday'] == true;
    final int streak = _n(st['count']).toInt();
    return Row(children: <Widget>[
      Container(
        width: 26,
        height: 26,
        decoration: BoxDecoration(shape: BoxShape.circle, color: done ? _sage.withOpacity(.22) : _gold.withOpacity(.18), border: Border.all(color: done ? _sage : _gold.withOpacity(.7))),
        child: Icon(done ? Icons.check_rounded : Icons.flag_rounded, size: 14, color: done ? _sage : _goldSoft),
      ),
      const SizedBox(width: 9),
      Expanded(
        child: Text(done ? 'Done for today${streak > 1 ? ' · $streak days running' : ''}.' : _s(t['title']), maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: done ? _muted : _ivory, fontSize: 14, fontWeight: FontWeight.w600)),
      ),
      if (!done) ...<Widget>[
        const SizedBox(width: 4),
        _btn('Do it', () => _openChat(ask: _s(t['ask'])), gold: true),
        const SizedBox(width: 4),
        _btn('', _doneBusy ? null : _markDone, icon: Icons.check_rounded),
      ],
    ]);
  }

  Widget _askBar() => GestureDetector(
        onTap: () => _openChat(),
        child: Container(
          height: 50,
          padding: const EdgeInsets.fromLTRB(16, 0, 6, 0),
          decoration: BoxDecoration(
            color: Colors.black.withOpacity(.28),
            borderRadius: BorderRadius.circular(999),
            border: Border.all(color: _gold.withOpacity(.40)),
            boxShadow: <BoxShadow>[BoxShadow(color: Colors.black.withOpacity(.22), blurRadius: 18, offset: const Offset(0, 8))],
          ),
          child: Row(children: <Widget>[
            const Icon(Icons.auto_awesome_rounded, size: 16, color: _gold),
            const SizedBox(width: 10),
            Expanded(child: Text(_chat.isNotEmpty ? 'Continue with June…' : 'Ask June anything', maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: _ivory.withOpacity(.72), fontSize: 14))),
            if (_micAvailable)
              GestureDetector(
                onTap: () => _openChat(listen: true),
                child: Container(
                  width: 38,
                  height: 38,
                  decoration: BoxDecoration(shape: BoxShape.circle, color: _listening ? _rose : _gold),
                  child: Icon(_listening ? Icons.stop_rounded : Icons.mic_rounded, color: _plumDeep, size: 19),
                ),
              ),
          ]),
        ),
      );

  // the conversation as a sheet over the dashboard: the core, the chat, the chips, and the whole dock
  Future<void> _openChat({String? ask, bool listen = false}) async {
    HapticFeedback.selectionClick();
    if (ask != null && ask.isNotEmpty) _ask(ask);
    if (listen) _toggleMic();
    await _sheet('June', () => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
          Row(children: <Widget>[
            _core(84),
            const SizedBox(width: 10),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[Text('June', style: _serif(24, color: _ivory)), _stateLabel()])),
            GestureDetector(
              onTap: _toggleVoice,
              child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
                Icon(_voice.enabled ? Icons.volume_up_rounded : Icons.volume_off_rounded, size: 16, color: _voice.enabled ? _gold : _muted),
                const SizedBox(width: 4),
                Text('voice', style: TextStyle(color: _voice.enabled ? _gold : _muted, fontSize: 12)),
              ]),
            ),
          ]),
          _nowPlaying(),
          const SizedBox(height: 10),
          _chatBox(MediaQuery.of(context).size.height * .36),
          if (_heard.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: Text(_heard, style: const TextStyle(color: _rose, fontSize: 12.5, fontStyle: FontStyle.italic))),
          const SizedBox(height: 10),
          _inputRow(),
          const SizedBox(height: 10),
          _chipsWrap(show: 5),
          const SizedBox(height: 12),
          _dock(false),
        ]));
  }

  Widget _hero(BuildContext context) {
    final bool reduce = MediaQuery.maybeOf(context)?.disableAnimations ?? false;
    if (!_entered) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted && !_entered) setState(() => _entered = true);
      });
    }
    if (_err.isNotEmpty) {
      return Row(children: <Widget>[
        _core(96),
        const SizedBox(width: 14),
        Expanded(child: Text('June couldn\'t load your day. $_err', style: const TextStyle(color: _muted, fontSize: 13, height: 1.4))),
        const SizedBox(width: 10),
        _btn('Try again', () => _load(first: true), gold: true),
      ]);
    }
    final String line = _heroLine();
    if (line != _typedFor) WidgetsBinding.instance.addPostFrameCallback((_) => _typeIn(line));
    final String shown = line.substring(0, math.min(_typed, line.length));
    final bool typing = shown.length < line.length;
    Widget rise(Widget child, {int delay = 0}) => reduce
        ? child
        : AnimatedOpacity(
            opacity: _entered ? 1 : 0,
            duration: Duration(milliseconds: 420 + delay),
            curve: Curves.easeOutCubic,
            child: AnimatedSlide(offset: _entered ? Offset.zero : const Offset(0, .06), duration: Duration(milliseconds: 420 + delay), curve: Curves.easeOutCubic, child: child),
          );
    Widget core(double size) => GestureDetector(
          onTap: () {
            if (_voice.speaking) {
              _voice.stop();
              if (mounted) setState(() => _mode = 'idle');
              return;
            }
            _openChat();
          },
          onLongPress: () => _openChat(listen: true),
          child: Semantics(label: 'June', hint: 'Talk to June', button: true, child: _core(size)),
        );
    final Widget greeting = FittedBox(fit: BoxFit.scaleDown, alignment: Alignment.centerLeft, child: Text(_heroGreeting(), maxLines: 1, style: _serif(30, color: _ivory, w: FontWeight.w500).copyWith(letterSpacing: -.5, shadows: const <Shadow>[Shadow(color: Color(0x99000000), blurRadius: 10, offset: Offset(0, 1))])));
    final Widget lineText = Text(
      shown.isEmpty && (_loading || typing) ? (line.isEmpty ? 'Reading your day…' : ' ') : shown + (typing ? '|' : ''),
      maxLines: 5,
      overflow: TextOverflow.ellipsis,
      style: _serif(17.5, color: _goldSoft, w: FontWeight.w400).copyWith(height: 1.35, fontStyle: FontStyle.italic, shadows: const <Shadow>[Shadow(color: Color(0x99000000), blurRadius: 8, offset: Offset(0, 1))]),
    );
    final Widget recall = _s(_map(_snap['recall'])['text']).isEmpty
        ? const SizedBox.shrink()
        : Padding(
            padding: const EdgeInsets.only(top: 10),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
              Icon(Icons.psychology_rounded, size: 13, color: _ivory.withOpacity(.6)),
              const SizedBox(width: 6),
              Expanded(child: Text('You told me: ${_s(_map(_snap['recall'])['text'])}', maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: _ivory.withOpacity(.66), fontSize: 12, fontStyle: FontStyle.italic))),
            ]),
          );
    final bool speakingNow = _voice.speaking || _mode == 'speaking';
    final Widget stopRow = speakingNow
        ? Padding(padding: const EdgeInsets.only(top: 8), child: _btn('Stop', () {
            _voice.stop();
            if (mounted) setState(() => _mode = 'idle');
          }, icon: Icons.stop_rounded))
        : const SizedBox.shrink();
    return LayoutBuilder(builder: (BuildContext c, BoxConstraints box) {
      final bool wide = box.maxWidth >= 760;
      if (wide) {
        return Row(crossAxisAlignment: CrossAxisAlignment.center, children: <Widget>[
          rise(Column(mainAxisSize: MainAxisSize.min, children: <Widget>[core(196), stopRow, _nowPlaying()])),
          const SizedBox(width: 22),
          // the right column keeps a reading width, so the pill's buttons stay beside their task
          Expanded(
            child: Align(
              alignment: Alignment.centerLeft,
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 640),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: <Widget>[
                  rise(greeting),
                  const SizedBox(height: 8),
                  rise(lineText, delay: 40),
                  const SizedBox(height: 16),
                  rise(_heroPill(), delay: 80),
                  if (_map(_snap['todayTask']).isNotEmpty) const SizedBox(height: 12),
                  rise(_askBar(), delay: 120),
                  rise(recall, delay: 160),
                ]),
              ),
            ),
          ),
        ]);
      }
      return Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: <Widget>[
        rise(greeting),
        const SizedBox(height: 2),
        rise(Row(crossAxisAlignment: CrossAxisAlignment.center, children: <Widget>[
          core(132),
          const SizedBox(width: 4),
          Expanded(child: lineText),
        ])),
        rise(stopRow),
        _nowPlaying(),
        const SizedBox(height: 12),
        rise(_heroPill(), delay: 60),
        if (_map(_snap['todayTask']).isNotEmpty) const SizedBox(height: 12),
        rise(_askBar(), delay: 120),
        rise(recall, delay: 180),
      ]);
    });
  }

  Widget _deck(BuildContext context) {""", "hero")

s = rep(s, "    if (widget.layout == 'deck') return _deck(context);",
        "    if (widget.layout == 'hero') return _hero(context);\n    if (widget.layout == 'deck') return _deck(context);", "build switch")
s = rep(s, "// END OF FILE - JC-LAZO-JUNE-NATIVE-1013-005", "// END OF FILE - JC-LAZO-JUNE-NATIVE-1013-006", "eof")
out = HERE / "JuneNative_v6.txt"
out.write_text(s, encoding="utf-8")
print("wrote", out.name, len(s))
