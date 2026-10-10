"""patch_june_native_v2.py - JC-LAZO-JUNE-NATIVE-1010-002
JuneNative_v1_ff.txt -> JuneNative_v2.txt
  1. Her core moves with her real voice (JC-LAZO-JUNE-ENV-1010-001): every clip from the hub now
     comes with a level track (24 bands, 20 frames a second, measured from the audio itself); the
     widget keeps it beside the playback position and feeds the bars from it. No track -> the old
     synthetic motion, so nothing regresses while the hub is mid-deploy.
  2. layout: 'deck' (JC-LAZO-JUNE-DECK-1010-001): June across the top of a dashboard - a large core
     with the brief and voice controls beside it, her greeting and headline, the chat, the mic, the
     chips - no card chrome, no gradient, no panels (the dashboard draws the deck and the numbers).
     layout: 'full' is the hub as before. FlutterFlow: add parameter `layout` (String).
  python app-patches\\patch_june_native_v2.py
"""
from pathlib import Path
HERE = Path(__file__).resolve().parent


def rep(s, old, new, label, count=1):
    n = s.count(old)
    if n != count:
        raise SystemExit(f"{label}: anchor found {n}x, wanted {count}: {old[:70]!r}")
    return s.replace(old, new)


s = (HERE / "JuneNative_v1_ff.txt").read_text(encoding="utf-8-sig")

# ---------------------------------------------------------------- build id + param
s = rep(s, "// Build ID: JC-LAZO-JUNE-NATIVE-1008-001\n",
        "// Build ID: JC-LAZO-JUNE-NATIVE-1010-002 (002: the core follows her real voice - clips carry a level track; layout 'deck' for the dashboards; base 001)\n", 'build id')
s = rep(s, "// Parameters: role 'couple' | 'vendor' (which panels and chips to show).\n",
        "// Parameters: role 'couple' | 'vendor' (which panels and chips to show).\n"
        "//             layout 'full' (the hub) | 'deck' (across the top of a dashboard; the host draws the surface).\n", 'param doc')
s = rep(s, "    this.role = 'couple',\n  });\n  final double? width;\n  final double? height;\n  final String role;\n",
        "    this.role = 'couple',\n    this.layout = 'full',\n  });\n  final double? width;\n  final double? height;\n  final String role;\n  final String layout;\n", 'param')
s = rep(s, "import 'dart:convert';\n", "import 'dart:convert';\nimport 'dart:typed_data';\n", 'typed_data import')

# ---------------------------------------------------------------- the voice: a level track beside playback
s = rep(s, "  AudioPlayer? _player;\n  html.AudioElement? _el;\n\n  AudioPlayer _ensure() {",
        '''  AudioPlayer? _player;
  html.AudioElement? _el;

  // JC-LAZO-JUNE-ENV-1010-001: the level track that came with the clip - frames x bands, bytes 0..255
  Uint8List? _trk;
  int _trkNb = 24;
  double _trkFps = 20;
  int _trkFrames = 0;
  DateTime? _t0;
  double _posKnown = 0;
  DateTime? _posAt;
  bool get hasTrack => _trk != null;

  void _setTrack(dynamic env) {
    _trk = null;
    _t0 = null;
    _posAt = null;
    _posKnown = 0;
    final Map<String, dynamic> e = _map(env);
    final String b64 = _s(e['b64']);
    if (b64.isEmpty) return;
    try {
      _trk = base64Decode(b64);
    } catch (_) {
      _trk = null;
      return;
    }
    _trkNb = _n(e['nb']) > 0 ? _n(e['nb']).toInt() : 24;
    _trkFps = _n(e['fps']) > 0 ? _n(e['fps']).toDouble() : 20;
    _trkFrames = _trk!.length ~/ _trkNb;
  }

  double _pos() {
    if (kIsWeb) {
      try {
        final html.AudioElement? a = _el;
        if (a != null) return a.currentTime.toDouble();
      } catch (_) {}
    }
    final DateTime? at = _posAt;
    if (at != null) return _posKnown + DateTime.now().difference(at).inMicroseconds / 1e6;
    final DateTime? t0 = _t0;
    return t0 == null ? 0 : DateTime.now().difference(t0).inMicroseconds / 1e6;
  }

  /// levels 0..1 for [nb] bars at the current playback position; null without a track
  List<double>? frame(int nb) {
    final Uint8List? t = _trk;
    if (t == null || _trkFrames == 0) return null;
    final double f = _pos() * _trkFps;
    final int i0 = f.floor().clamp(0, _trkFrames - 1);
    final int i1 = (i0 + 1).clamp(0, _trkFrames - 1);
    final double k = (f - f.floor()).clamp(0.0, 1.0);
    double at(int i, int j) => t[i * _trkNb + j] / 255.0;
    final List<double> out = List<double>.filled(nb, 0);
    for (int b = 0; b < nb; b++) {
      final double x = b * (_trkNb - 1) / math.max(1, nb - 1);
      final int j0 = x.floor();
      final int j1 = math.min(_trkNb - 1, j0 + 1);
      final double kk = x - j0;
      final double a = at(i0, j0) * (1 - kk) + at(i0, j1) * kk;
      final double c = at(i1, j0) * (1 - kk) + at(i1, j1) * kk;
      out[b] = a * (1 - k) + c * k;
    }
    return out;
  }

  AudioPlayer _ensure() {''', 'voice fields')

s = rep(s, '''      String url = '';
      try {
        final dynamic j = await api.post('/api/clip', <String, dynamic>{'text': t});
        url = _s(_map(j)['url']);
      } catch (e) {
        debugPrint('LAZO june clip: ' + e.toString());
      }
      if (url.isEmpty || gen != _gen) continue;
      await playUrl(url, gen);''',
        '''      String url = '';
      dynamic env;
      try {
        final dynamic j = await api.post('/api/clip', <String, dynamic>{'text': t});
        url = _s(_map(j)['url']);
        env = _map(j)['env'];
      } catch (e) {
        debugPrint('LAZO june clip: ' + e.toString());
      }
      if (url.isEmpty || gen != _gen) continue;
      await playUrl(url, gen, env);''', 'pump')

s = rep(s, '''  Future<void> playUrl(String url, [int? gen]) async {
    final int g = gen ?? _gen;
    try {
      if (kIsWeb) {
        final html.AudioElement a = html.AudioElement();
        _el = a;
        a.src = url;
        a.preload = 'auto';
        final Completer<void> c = Completer<void>();
        a.onEnded.listen((_) {
          if (!c.isCompleted) c.complete();
        });
        a.onError.listen((_) {
          if (!c.isCompleted) c.complete();
        });
        await a.play().catchError((Object _) {});
        await c.future.timeout(const Duration(minutes: 6), onTimeout: () {});
        if (identical(_el, a)) _el = null;
      } else {
        final AudioPlayer p = _ensure();
        await p.stop();
        final Completer<void> c = Completer<void>();
        final StreamSubscription<void> sub = p.onPlayerComplete.listen((_) {
          if (!c.isCompleted) c.complete();
        });
        await p.play(UrlSource(url));
        await c.future.timeout(const Duration(minutes: 6), onTimeout: () {});
        await sub.cancel();
      }
    } catch (e) {
      debugPrint('LAZO june play: ' + e.toString());
    }
    if (g != _gen) return;
  }''',
        '''  Future<void> playUrl(String url, [int? gen, dynamic env]) async {
    final int g = gen ?? _gen;
    _setTrack(env);
    try {
      if (kIsWeb) {
        final html.AudioElement a = html.AudioElement();
        _el = a;
        a.src = url;
        a.preload = 'auto';
        final Completer<void> c = Completer<void>();
        a.onEnded.listen((_) {
          if (!c.isCompleted) c.complete();
        });
        a.onError.listen((_) {
          if (!c.isCompleted) c.complete();
        });
        _t0 = DateTime.now();
        await a.play().catchError((Object _) {});
        await c.future.timeout(const Duration(minutes: 6), onTimeout: () {});
        if (identical(_el, a)) _el = null;
      } else {
        final AudioPlayer p = _ensure();
        await p.stop();
        final Completer<void> c = Completer<void>();
        final StreamSubscription<void> sub = p.onPlayerComplete.listen((_) {
          if (!c.isCompleted) c.complete();
        });
        final StreamSubscription<Duration> psub = p.onPositionChanged.listen((Duration d) {
          _posKnown = d.inMicroseconds / 1e6;
          _posAt = DateTime.now();
        });
        _t0 = DateTime.now();
        await p.play(UrlSource(url));
        await c.future.timeout(const Duration(minutes: 6), onTimeout: () {});
        await sub.cancel();
        await psub.cancel();
      }
    } catch (e) {
      debugPrint('LAZO june play: ' + e.toString());
    }
    _trk = null;
    if (g != _gen) return;
  }''', 'playUrl')

s = rep(s, '''      _el?.pause();
      _el = null;
    } catch (_) {}
    try {
      _player?.stop();
    } catch (_) {}
    if (speaking) {''',
        '''      _el?.pause();
      _el = null;
    } catch (_) {}
    try {
      _player?.stop();
    } catch (_) {}
    _trk = null;
    if (speaking) {''', 'stop')

# the brief plays with its track too
s = rep(s, '''      if (url.isNotEmpty) {
        setState(() => _mode = 'speaking');
        await _voice.playUrl(url);
        if (mounted) setState(() => _mode = 'idle');''',
        '''      if (url.isNotEmpty) {
        setState(() => _mode = 'speaking');
        await _voice.playUrl(url, null, _map(j)['env']);
        if (mounted) setState(() => _mode = 'idle');''', 'brief play')

# ---------------------------------------------------------------- the tick: real levels when there is a track
s = rep(s, '''    final double atk = 1 - math.exp(-dt * 60), rel = 4.2 * dt, capFall = 2.2 * dt;
    for (int b = 0; b < _nb; b++) {
      double shape;''',
        '''    // JC-LAZO-JUNE-ENV-1010-001: while a clip plays, the bars are the clip
    final List<double>? live = m == 'speaking' ? _voice.frame(_nb) : null;
    if (live != null) {
      double sum = 0;
      for (final double v in live) sum += v;
      target = math.min(1, (sum / _nb) * 1.7 + 0.06);
    }
    final double atk = 1 - math.exp(-dt * 60), rel = (live != null ? 7.5 : 4.2) * dt, capFall = 2.2 * dt;
    for (int b = 0; b < _nb; b++) {
      double shape;''', 'tick live')
s = rep(s, "      final double v = m == 'idle' ? 0.03 + 0.025 * math.sin(_phase * 1.3 + b * 0.5) : target * shape;",
        "      final double v = live != null ? live[b] : (m == 'idle' ? 0.05 + 0.04 * math.sin(_phase * 1.1 + b * 0.45) * math.sin(_phase * 0.7 + b * 0.2) : target * shape);", 'tick v')
s = rep(s, "    _bass += (target * 0.5 - _bass) * 0.1;",
        "    _bass += ((live != null ? (live[0] + live[1] + live[2] + live[3]) / 4 : target * 0.5) - _bass) * (live != null ? 0.3 : 0.1);", 'tick bass')

# ---------------------------------------------------------------- the console, in parts, and the deck
a = s.index("  // ---- the console: core + chat\n  Widget _console() {")
b = s.index("  Widget _bubble(Map<String, dynamic> m) {")
console = r'''  // ---- the console: core + chat (in parts, so the deck can lay them out its own way)
  List<String> get _chips => _couple
      ? <String>['What should we do next?', 'Who\'s waiting on us?', 'How are the RSVPs?', 'Where are we on budget?', 'What\'s the forecast for our day?', 'Find us a florist', 'Play some music']
      : <String>['Who is waiting on me?', 'What\'s on this week?', 'Weather for my next wedding', 'How much is outstanding?', 'Which leads went quiet?', 'Play some music'];

  Widget _core(double size) => GestureDetector(
        onTap: () {
          if (_voice.speaking) _voice.stop();
        },
        child: SizedBox(
          width: size,
          height: size,
          child: CustomPaint(painter: _CorePainter(levels: _lvl, caps: _cap, swell: _swell, bass: _bass, rot: _rot, tint: _tint, live: _mode != 'idle' || _radioName.isNotEmpty)),
        ),
      );

  Widget _stateLabel() => Text(_mode == 'idle' && _radioName.isNotEmpty ? '♪ $_radioName' : _mode, style: const TextStyle(color: _muted, fontSize: 10.5, letterSpacing: 2));

  void _toggleVoice() {
    setState(() => _voice.enabled = !_voice.enabled);
    if (!_voice.enabled) _voice.stop();
    SharedPreferences.getInstance().then((SharedPreferences p) => p.setBool('juneSpeak', _voice.enabled));
  }

  Widget _chatBox(double height) => Container(
        height: height,
        decoration: BoxDecoration(color: Colors.black.withOpacity(.25), borderRadius: BorderRadius.circular(16), border: Border.all(color: Colors.white.withOpacity(.08))),
        child: _chat.isEmpty
            ? Center(child: Padding(padding: const EdgeInsets.all(20), child: Text(_couple ? 'Good to see you both. Ask me anything about your vendors, your guests, the budget or the big day.' : 'Good to see you. Ask me anything about your couples, dates or money.', textAlign: TextAlign.center, style: const TextStyle(color: _muted, fontSize: 13, height: 1.5))))
            : ListView.builder(
                controller: _chatScroll,
                padding: const EdgeInsets.all(12),
                itemCount: _chat.length,
                itemBuilder: (BuildContext c, int i) => _bubble(_chat[i]),
              ),
      );

  Widget _inputRow() => Row(children: <Widget>[
        Expanded(
          child: TextField(
            controller: _q,
            textInputAction: TextInputAction.send,
            onSubmitted: _ask,
            style: const TextStyle(color: _ivory, fontSize: 14),
            cursorColor: _gold,
            decoration: InputDecoration(
              hintText: _couple ? 'What should we do next? Who\'s waiting on us?' : 'Who is waiting on me? What\'s the weather Saturday?',
              hintStyle: const TextStyle(color: _muted, fontSize: 13),
              isDense: true,
              filled: true,
              fillColor: Colors.black.withOpacity(.3),
              contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(999), borderSide: BorderSide(color: _gold.withOpacity(.35))),
              enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(999), borderSide: BorderSide(color: _gold.withOpacity(.35))),
              focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(999), borderSide: const BorderSide(color: _gold)),
            ),
          ),
        ),
        const SizedBox(width: 8),
        if (_micAvailable)
          GestureDetector(
            onTap: _toggleMic,
            child: Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(shape: BoxShape.circle, color: _listening ? _rose : Colors.black.withOpacity(.3), border: Border.all(color: _listening ? _rose : _gold.withOpacity(.5))),
              child: Icon(_listening ? Icons.stop_rounded : Icons.mic_rounded, color: _listening ? _plumDeep : _gold, size: 20),
            ),
          ),
        const SizedBox(width: 8),
        GestureDetector(
          onTap: () => _ask(_q.text),
          child: Container(
            width: 42,
            height: 42,
            decoration: const BoxDecoration(shape: BoxShape.circle, color: _gold),
            child: const Icon(Icons.arrow_upward_rounded, color: _plumDeep, size: 22),
          ),
        ),
      ]);

  Widget _chipsWrap() => Wrap(
        spacing: 6,
        runSpacing: 6,
        children: _chips
            .map((String c) => GestureDetector(
                  onTap: () => _ask(c),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 6),
                    decoration: BoxDecoration(color: Colors.white.withOpacity(.07), borderRadius: BorderRadius.circular(999), border: Border.all(color: Colors.white.withOpacity(.14))),
                    child: Text(c, style: const TextStyle(color: _ivory, fontSize: 12)),
                  ),
                ))
            .toList(),
      );

  Widget _console() {
    return _card(
      title: 'June',
      trailing: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
        _stateLabel(),
        const SizedBox(width: 10),
        GestureDetector(
          onTap: _toggleVoice,
          child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
            Icon(_voice.enabled ? Icons.volume_up_rounded : Icons.volume_off_rounded, size: 16, color: _voice.enabled ? _gold : _muted),
            const SizedBox(width: 4),
            Text('voice', style: TextStyle(color: _voice.enabled ? _gold : _muted, fontSize: 12)),
          ]),
        ),
      ]),
      child: Column(children: <Widget>[
        _core(196),
        const SizedBox(height: 10),
        _chatBox(220),
        if (_heard.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: Text(_heard, style: const TextStyle(color: _rose, fontSize: 12.5, fontStyle: FontStyle.italic))),
        const SizedBox(height: 10),
        _inputRow(),
        const SizedBox(height: 10),
        _chipsWrap(),
      ]),
    );
  }

  // ---- the deck (JC-LAZO-JUNE-DECK-1010-001): June across the top of a dashboard. The host
  // draws the surface and the numbers; this is her core, her words, and the way to talk to her.
  String _greeting() {
    final int h = DateTime.now().hour;
    final String tod = h < 4 ? 'Still up' : h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
    final String who = _couple ? _s(_map(_snap['couple'])['names']) : '';
    return who.isEmpty ? '$tod.' : '$tod, $who.';
  }

  String _headline() {
    if (_loading && _snap.isEmpty) return 'Reading your day…';
    final String brief = _s(_map(_snap['brief'])['text']).trim();
    if (brief.isNotEmpty) {
      final List<String> sents = brief.split(RegExp(r'(?<=[.!?])\s+'));
      return sents.take(2).join(' ');
    }
    final int w = _list(_snap['waiting']).length;
    final Map<String, dynamic> m = _map(_snap['money']);
    final double due = _n(m[_couple ? 'open' : 'outstanding']).toDouble();
    final List<String> parts = <String>[
      w == 0 ? 'Nobody is waiting on you.' : '$w ${_couple ? (w == 1 ? 'vendor is' : 'vendors are') : (w == 1 ? 'couple is' : 'couples are')} waiting on you.',
      if (due > 0) '\$${due.round()} ${_couple ? 'due soon' : 'outstanding'}.',
      'Ask me anything.',
    ];
    return parts.join(' ');
  }

  Widget _deck(BuildContext context) {
    if (_err.isNotEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Row(children: <Widget>[
          _core(96),
          const SizedBox(width: 14),
          Expanded(child: Text('June couldn\'t load your data. $_err', style: const TextStyle(color: _muted, fontSize: 13, height: 1.4))),
          const SizedBox(width: 10),
          _btn('Try again', () => _load(first: true), gold: true),
        ]),
      );
    }
    return LayoutBuilder(builder: (BuildContext c, BoxConstraints box) {
      final bool wide = box.maxWidth >= 760;
      final double coreSize = wide ? 236 : 168;
      final bool hasBrief = _s(_map(_snap['brief'])['text']).isNotEmpty;
      final Widget controls = Wrap(
        spacing: 8,
        runSpacing: 8,
        alignment: WrapAlignment.center,
        children: <Widget>[
          if (hasBrief) _btn(_briefPlaying ? 'Stop' : 'Listen to today\'s brief', _listenBrief, gold: true, icon: _briefPlaying ? Icons.stop_rounded : Icons.play_arrow_rounded),
          _btn(_voice.enabled ? 'Voice on' : 'Voice off', _toggleVoice, icon: _voice.enabled ? Icons.volume_up_rounded : Icons.volume_off_rounded),
        ],
      );
      final Widget left = Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
        _core(coreSize),
        const SizedBox(height: 2),
        _stateLabel(),
        const SizedBox(height: 12),
        controls,
      ]);
      final Widget right = Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: <Widget>[
        Text(_greeting(), maxLines: 1, overflow: TextOverflow.ellipsis, style: _serif(wide ? 30 : 24, color: _ivory, w: FontWeight.w500)),
        const SizedBox(height: 6),
        Text(_headline(), maxLines: 3, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _goldSoft, fontSize: 14, height: 1.5)),
        const SizedBox(height: 14),
        if (_chat.isNotEmpty) _chatBox(wide ? 240 : 200),
        if (_heard.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: Text(_heard, style: const TextStyle(color: _rose, fontSize: 12.5, fontStyle: FontStyle.italic))),
        const SizedBox(height: 10),
        _inputRow(),
        const SizedBox(height: 10),
        _chipsWrap(),
      ]);
      if (!wide) return Column(children: <Widget>[left, const SizedBox(height: 16), right]);
      return Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
        SizedBox(width: coreSize + 44, child: left),
        const SizedBox(width: 20),
        Expanded(child: right),
      ]);
    });
  }

'''
s = s[:a] + console + s[b:]

s = rep(s, "  Widget build(BuildContext context) {\n    final List<Widget> left = <Widget>[_console(), _briefCard(), _waitingCard(), _upcomingCard()];",
        "  Widget build(BuildContext context) {\n    if (widget.layout == 'deck') return _deck(context);\n    final List<Widget> left = <Widget>[_console(), _briefCard(), _waitingCard(), _upcomingCard()];", 'build')
s = rep(s, "// END OF FILE - JC-LAZO-JUNE-NATIVE-1008-001", "// END OF FILE - JC-LAZO-JUNE-NATIVE-1010-002", 'end')
(HERE / "JuneNative_v2.txt").write_text(s, encoding="utf-8")
print("wrote JuneNative_v2.txt", len(s))
