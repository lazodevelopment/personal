r"""patch_june_native_v8.py - JuneNative v7 -> v8 (JC-LAZO-JUNE-NATIVE-1014-008)

1. THE RADIO OUTLIVES THE PAGE. It used to belong to one June widget: open Edit
   profile, come back, and the music played on with no Stop button and a dead
   visualizer (the new widget had no handle on the stream). Now JuneRadio is one
   player for the whole app; every June widget attaches to it, so the core keeps
   its spectrum and the controls work wherever you come back to.
2. A FLOATING PLAYER. While the radio plays and no June is on screen, a small
   player floats over every page: the bars, the station, pause / play, next, a
   station list with volume, and stop. Drag it anywhere.
3. JUNE READS HER LINE. On the dashboards (layout 'hero') June speaks the update
   she types in, once per new line per day. A speaker beside the line turns that
   off (remembered). Browsers allow sound only after a tap on the page, so on a
   fresh load she waits for the first tap anywhere.
4. JuneSpeech.say(text) for other widgets: the vendor dashboard's first-run tour
   uses it so June narrates each step. Music dips while she talks.

    python app-patches\patch_june_native_v8.py
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
s = (HERE / "JuneNative_v7.txt").read_text(encoding="utf-8")
OUT = HERE / "JuneNative_v8.txt"


def rep(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"anchor found {n}x (want {count}): {old[:80]!r}")
    s = s.replace(old, new)


# build id
rep("// Build ID: JC-LAZO-JUNE-NATIVE-1014-007 (007:", "// Build ID: JC-LAZO-JUNE-NATIVE-1014-008 (008: the radio is one player for the whole app with a floating mini player on every page; June reads her dashboard line aloud with a speaker to turn it off; JuneSpeech.say for the vendor tour; base 007) (007:")
rep("// END OF FILE - JC-LAZO-JUNE-NATIVE-1014-007", "// END OF FILE - JC-LAZO-JUNE-NATIVE-1014-008")

# the page script notes the first tap (browsers only allow sound after one)
rep("""  ['pointerdown','keydown','touchstart'].forEach(function(ev){ document.addEventListener(ev, function(){ ctx(); }, {passive:true}); });""",
    """  ['pointerdown','keydown','touchstart'].forEach(function(ev){ document.addEventListener(ev, function(){ ctx(); try{ document.body.dataset.juneActive='1'; }catch(e){} }, {passive:true}); });
  try{ if(navigator.userActivation&&navigator.userActivation.hasBeenActive){ document.body.dataset.juneActive='1'; } }catch(e){}""")

# radio state now lives in JuneRadio
rep("  String _radioName = '';\n", "")
a = s.index("  AudioPlayer? _radioPlayer;\n  html.AudioElement? _radioEl;")
b = s.index("  // the now-playing strip: station, previous / next, volume, stop")
s = s[:a] + """  // v008: the radio is JuneRadio.I, one player for the whole app, so it outlives this widget
  String get _radioName => JuneRadio.I.name;
  double get _radioVol => JuneRadio.I.vol;
  bool get _radioFft => JuneRadio.I.fft;
  Future<void> _radioPlay(int i) => JuneRadio.I.play(i, context);
  void _radioStop() => JuneRadio.I.stop();
  void _radioStep(int d) => JuneRadio.I.step(d, context);
  void _radioSetVol(double v) => JuneRadio.I.setVol(v);
  void _onRadio() {
    if (mounted) setState(() {});
  }

  // v008: June reads her dashboard line aloud - once per new line per day, after the first tap
  bool _heroVoice = true;
  bool _heroPrefs = false;
  String _heroSaid = '';
  String _heroPending = '';
  Timer? _heroWait;

  void _maybeSpeakHero(String line) {
    if (widget.layout != 'hero' || _loading || line.trim().isEmpty) return;
    if (!_heroPrefs) {
      _heroPending = line;
      return;
    }
    if (!_heroVoice || !_voice.enabled || JuneSpeech.hold) return;
    final String key = _localDay() + '|' + line;
    if (_heroSaid == key) return;
    _heroSaid = key;
    SharedPreferences.getInstance().then((SharedPreferences p) => p.setString('juneHeroSaid', key));
    _heroWait?.cancel();
    void go() {
      if (!mounted || !_heroVoice || !_voice.enabled || _typedFor != line || JuneSpeech.hold) return;
      _voice.say(line);
    }
    if (juneCanSpeak()) {
      go();
      return;
    }
    int n = 0;
    _heroWait = Timer.periodic(const Duration(milliseconds: 400), (Timer t) {
      if (++n > 1500 || !mounted) {
        t.cancel();
        return;
      }
      if (juneCanSpeak()) {
        t.cancel();
        go();
      }
    });
  }

  void _toggleHeroVoice() {
    setState(() => _heroVoice = !_heroVoice);
    if (!_heroVoice) {
      _heroWait?.cancel();
      _voice.stop();
      setState(() => _mode = 'idle');
    } else {
      _heroSaid = '';
      _maybeSpeakHero(_typedFor);
    }
    SharedPreferences.getInstance().then((SharedPreferences p) => p.setBool('juneHeroVoice', _heroVoice));
  }

  Widget _heroSpeaker() => Tooltip(
        message: _heroVoice ? 'June reads this aloud - tap to turn off' : 'Have June read this aloud',
        child: GestureDetector(
          onTap: _toggleHeroVoice,
          child: Container(
            width: 30,
            height: 30,
            margin: const EdgeInsets.only(left: 8, top: 1),
            decoration: BoxDecoration(shape: BoxShape.circle, color: Colors.black.withOpacity(.22), border: Border.all(color: (_heroVoice ? _gold : _muted).withOpacity(.6))),
            child: Icon(_heroVoice ? Icons.volume_up_rounded : Icons.volume_off_rounded, size: 15, color: _heroVoice ? _gold : _muted),
          ),
        ),
      );

""" + s[b:]

rep("    final bool radioOn = _radioName.isNotEmpty;", "    final bool radioOn = JuneRadio.I.playing;")
rep("""          _iconBtn(Icons.skip_next_rounded, () => _radioStep(1), 'Next station'),
          _iconBtn(Icons.stop_rounded, _radioStop, 'Stop the music', gold: true),""",
    """          _iconBtn(JuneRadio.I.playing ? Icons.pause_rounded : Icons.play_arrow_rounded, JuneRadio.I.toggle, JuneRadio.I.playing ? 'Pause' : 'Play'),
          _iconBtn(Icons.skip_next_rounded, () => _radioStep(1), 'Next station'),
          _iconBtn(Icons.stop_rounded, _radioStop, 'Stop the music', gold: true),""")

# the voice: music dips while June talks
rep("""  late final _Voice _voice = _Voice(_api, (bool s) {
    if (!mounted) return;""", """  late final _Voice _voice = _Voice(_api, (bool s) {
    JuneRadio.I.duck(s);
    if (!mounted) return;""")

# lifecycle
rep("""    super.initState();
    _juneWebInstall();""", """    super.initState();
    _juneWebInstall();
    JuneRadio.I.rev.addListener(_onRadio);
    JuneRadio.I.onError = (String m) {
      if (mounted) _addMsg('sys', m);
    };
    JuneRadio.I.setVisible(this, true);
    JuneSpeech._host = this;""")
rep("""      final bool? v = p.getBool('juneSpeak');
      if (v != null && mounted) setState(() => _voice.enabled = v);""", """      final bool? v = p.getBool('juneSpeak');
      if (v != null && mounted) setState(() => _voice.enabled = v);
      _heroVoice = p.getBool('juneHeroVoice') ?? true;
      _heroSaid = p.getString('juneHeroSaid') ?? '';
      _heroPrefs = true;
      if (_heroPending.isNotEmpty && mounted) _maybeSpeakHero(_heroPending);""")
rep("""  void dispose() {
    _focusT?.cancel();
    _typeT?.cancel();""", """  void dispose() {
    JuneRadio.I.rev.removeListener(_onRadio);
    JuneRadio.I.setVisible(this, false);
    if (identical(JuneSpeech._host, this)) JuneSpeech._host = null;
    _heroWait?.cancel();
    _focusT?.cancel();
    _typeT?.cancel();""")
rep("""      if (on != _onScreen) setState(() => _onScreen = on);""", """      JuneRadio.I.setVisible(this, on);
      if (on != _onScreen) setState(() => _onScreen = on);""")

# the hero line is spoken when it is typed in
rep("""    _typeT?.cancel();
    _typedFor = text;""", """    _typeT?.cancel();
    _typedFor = text;
    _maybeSpeakHero(text);""")
rep("""    final Widget lineText = Text(
      shown.isEmpty && (_loading || typing)""", """    final Widget lineText0 = Text(
      shown.isEmpty && (_loading || typing)""")
rep("""    final Widget recall = _s(_map(_snap['recall'])['text']).isEmpty""", """    final Widget lineText = line.isEmpty ? lineText0 : Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[Expanded(child: lineText0), _heroSpeaker()]);
    final Widget recall = _s(_map(_snap['recall'])['text']).isEmpty""")

# FlutterFlow's widgets/index.dart exports only "show JuneNative", so other widgets reach June's voice
# through statics on the widget class
rep("""class JuneNative extends StatefulWidget {
""", """class JuneNative extends StatefulWidget {
  /// v008: June speaks for other Lazo widgets (the vendor tour). Honors her voice switch.
  static Future<void> say(String text) => JuneSpeech.say(text);
  static void stopSpeaking() => JuneSpeech.stop();
  /// true while something else narrates; her dashboard line keeps quiet
  static set holdLine(bool on) => JuneSpeech.hold = on;
  static bool get holdLine => JuneSpeech.hold;

""")

# ---------------------------------------------------------------- new top-level pieces
TAIL = r"""

// ---------------------------------------------------------------- v008: the first tap (web sound needs one)
bool juneCanSpeak() {
  if (!kIsWeb) return true;
  try {
    return html.document.body?.dataset['juneActive'] == '1';
  } catch (_) {
    return true;
  }
}

// ---------------------------------------------------------------- v008: one radio for the whole app
class JuneRadio {
  JuneRadio._();
  static final JuneRadio I = JuneRadio._();
  final ValueNotifier<int> rev = ValueNotifier<int>(0);
  AudioPlayer? _player;
  html.AudioElement? _el;
  int idx = -1;
  double vol = 0.7;
  bool fft = false;
  bool playing = false;
  bool _on = false; // a station is loaded (playing or paused)
  bool _ducked = false;
  void Function(String message)? onError;
  final Set<Object> _visible = <Object>{};
  OverlayEntry? _entry;

  static List<List<String>> get stations => _JuneNativeState._radio;
  static List<String> get groups => _JuneNativeState._radioGroups;
  String get name => _on && idx >= 0 ? stations[idx][0] : '';
  bool get anyJuneVisible => _visible.isNotEmpty;

  void _bump() => rev.value = rev.value + 1;
  double get _eff => _ducked ? vol * 0.25 : vol;

  Future<void> play(int i, [BuildContext? ctx]) async {
    _halt();
    idx = i;
    _on = true;
    playing = true;
    _bump();
    if (ctx != null) _ensureMini(ctx);
    final List<String> st = stations[i];
    try {
      if (kIsWeb) {
        await _playWeb(st[1], true);
      } else {
        final AudioPlayer p = AudioPlayer();
        try {
          p.setAudioContext(AudioContext(iOS: AudioContextIOS(category: AVAudioSessionCategory.playback), android: AudioContextAndroid()));
        } catch (_) {}
        p.setVolume(_eff);
        _player = p;
        await p.play(UrlSource(st[1]));
      }
    } catch (e) {
      onError?.call('That station wouldn\'t start: ' + e.toString());
      stop();
    }
  }

  // web: through the analyser first (needs the stream to allow cross-origin audio); on error once more plainly
  Future<void> _playWeb(String url, bool withFft) async {
    final html.AudioElement a = html.AudioElement();
    if (withFft) a.crossOrigin = 'anonymous';
    a.src = url;
    a.volume = _eff;
    _el = a;
    fft = withFft;
    if (withFft) _juneWebAttach(a);
    a.onError.listen((_) {
      if (!identical(_el, a)) return;
      if (withFft) {
        _juneWebDetach(a);
        _el = null;
        _playWeb(url, false);
      } else {
        onError?.call('That station wouldn\'t start.');
        stop();
      }
    });
    _bump();
    await a.play().catchError((Object _) {});
  }

  void _halt() {
    try {
      _el?.pause();
      if (fft) _juneWebDetach(_el);
      _el?.remove();
      _el = null;
    } catch (_) {}
    try {
      _player?.stop();
      _player?.dispose();
      _player = null;
    } catch (_) {}
    fft = false;
  }

  void stop() {
    _halt();
    _on = false;
    playing = false;
    _removeMini();
    _bump();
  }

  void pause() {
    if (!_on || !playing) return;
    try {
      _el?.pause();
    } catch (_) {}
    try {
      _player?.pause();
    } catch (_) {}
    playing = false;
    _bump();
  }

  void resume() {
    if (!_on) {
      play(idx < 0 ? 0 : idx);
      return;
    }
    if (playing) return;
    try {
      _el?.play().catchError((Object _) {});
    } catch (_) {}
    try {
      _player?.resume();
    } catch (_) {}
    playing = true;
    _bump();
  }

  void toggle() => playing ? pause() : resume();

  void step(int d, [BuildContext? ctx]) {
    if (idx < 0) {
      play(0, ctx);
      return;
    }
    play((idx + d + stations.length) % stations.length, ctx);
  }

  void _applyVol() {
    try {
      _el?.volume = _eff;
    } catch (_) {}
    try {
      _player?.setVolume(_eff);
    } catch (_) {}
  }

  void setVol(double v) {
    vol = v.clamp(0.0, 1.0);
    _applyVol();
    _bump();
  }

  /// the music dips while June speaks
  void duck(bool on) {
    if (_ducked == on) return;
    _ducked = on;
    _applyVol();
  }

  void setVisible(Object who, bool on) {
    final bool before = _visible.isNotEmpty;
    if (on) {
      _visible.add(who);
    } else {
      _visible.remove(who);
    }
    if (before != _visible.isNotEmpty) {
      // never during a build: the mini player listens to rev
      WidgetsBinding.instance.addPostFrameCallback((_) => _bump());
    }
  }

  void _ensureMini(BuildContext ctx) {
    if (_entry != null) return;
    try {
      final OverlayState? o = Overlay.maybeOf(ctx, rootOverlay: true);
      if (o == null) return;
      final OverlayEntry e = OverlayEntry(builder: (BuildContext c) => const _JuneMini());
      _entry = e;
      o.insert(e);
    } catch (_) {}
  }

  void _removeMini() {
    try {
      _entry?.remove();
    } catch (_) {}
    _entry = null;
  }
}

// the floating player: over every page while the radio is on and no June is on screen
class _JuneMini extends StatefulWidget {
  const _JuneMini();
  @override
  State<_JuneMini> createState() => _JuneMiniState();
}

class _JuneMiniState extends State<_JuneMini> with SingleTickerProviderStateMixin {
  static Offset? _pos; // remembered for the session
  late final Ticker _t;
  double _ph = 0;
  Duration _last = Duration.zero;
  final List<double> _bars = List<double>.filled(5, .2);

  @override
  void initState() {
    super.initState();
    JuneRadio.I.rev.addListener(_r);
    _t = createTicker((Duration now) {
      final double dt = _last == Duration.zero ? .016 : math.min(.1, (now - _last).inMicroseconds / 1e6);
      _last = now;
      _ph += dt;
      final JuneRadio r = JuneRadio.I;
      if (!r.playing || r.anyJuneVisible) return;
      final List<double>? live = r.fft ? _juneWebFrame(5) : null;
      for (int b = 0; b < 5; b++) {
        final double want = live != null ? (.15 + .85 * live[b]) : (.3 + .55 * (0.5 + 0.5 * math.sin(_ph * (3.1 + b * 0.7) + b * 1.3)));
        _bars[b] += (want - _bars[b]) * math.min(1, dt * 14);
      }
      setState(() {});
    })..start();
  }

  void _r() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    JuneRadio.I.rev.removeListener(_r);
    _t.dispose();
    super.dispose();
  }

  Widget _b(IconData i, String tip, VoidCallback f, {bool gold = false}) => Tooltip(
        message: tip,
        child: GestureDetector(
          onTap: f,
          child: Container(
            width: 34,
            height: 34,
            margin: const EdgeInsets.only(left: 4),
            decoration: BoxDecoration(shape: BoxShape.circle, color: gold ? _gold : Colors.white.withOpacity(.1)),
            child: Icon(i, size: 19, color: gold ? _plumDeep : _ivory),
          ),
        ),
      );

  void _stations() {
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: _plumDeep,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (BuildContext c) => ValueListenableBuilder<int>(
        valueListenable: JuneRadio.I.rev,
        builder: (BuildContext c2, int _, Widget? __) {
          final JuneRadio r = JuneRadio.I;
          return SafeArea(
            child: ConstrainedBox(
              constraints: BoxConstraints(maxHeight: MediaQuery.of(c2).size.height * .75),
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(20, 16, 20, 20),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                  Row(children: <Widget>[
                    const Icon(Icons.radio_rounded, color: _gold, size: 18),
                    const SizedBox(width: 8),
                    const Expanded(child: Text('June radio', style: TextStyle(color: _ivory, fontSize: 17, fontWeight: FontWeight.w700))),
                    TextButton(onPressed: () => Navigator.of(c2).pop(), child: const Text('Done', style: TextStyle(color: _gold))),
                  ]),
                  Row(children: <Widget>[
                    const Icon(Icons.volume_down_rounded, size: 16, color: _muted),
                    Expanded(child: Slider(value: r.vol, activeColor: _gold, inactiveColor: Colors.white24, onChanged: r.setVol)),
                    const Icon(Icons.volume_up_rounded, size: 16, color: _muted),
                  ]),
                  for (final String g in JuneRadio.groups) ...<Widget>[
                    Padding(padding: const EdgeInsets.only(top: 12, bottom: 6), child: Text(g.toUpperCase(), style: const TextStyle(color: _muted, fontSize: 10.5, letterSpacing: 1.6, fontWeight: FontWeight.w700))),
                    Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
                      for (int i = 0; i < JuneRadio.stations.length; i++)
                        if (JuneRadio.stations[i][3] == g)
                          GestureDetector(
                            onTap: () => r.idx == i && r.name.isNotEmpty ? r.toggle() : r.play(i),
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                              decoration: BoxDecoration(
                                color: r.idx == i && r.name.isNotEmpty ? _gold : Colors.white.withOpacity(.07),
                                borderRadius: BorderRadius.circular(999),
                                border: Border.all(color: _gold.withOpacity(.4)),
                              ),
                              child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
                                if (r.idx == i && r.name.isNotEmpty) ...<Widget>[Icon(r.playing ? Icons.graphic_eq_rounded : Icons.pause_rounded, size: 13, color: _plumDeep), const SizedBox(width: 5)],
                                Text(JuneRadio.stations[i][0], style: TextStyle(color: r.idx == i && r.name.isNotEmpty ? _plumDeep : _ivory, fontSize: 12.5, fontWeight: FontWeight.w600)),
                              ]),
                            ),
                          ),
                    ]),
                  ],
                ]),
              ),
            ),
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final JuneRadio r = JuneRadio.I;
    if (r.name.isEmpty || r.anyJuneVisible) return const SizedBox.shrink();
    final Size sz = MediaQuery.of(context).size;
    final EdgeInsets pad = MediaQuery.of(context).padding;
    const double w = 300, h = 54;
    final double bw = math.min(w, sz.width - 24);
    final Offset p = _pos ?? Offset(16, sz.height - pad.bottom - h - 96);
    final Offset at = Offset(p.dx.clamp(8.0, math.max(8.0, sz.width - bw - 8)), p.dy.clamp(pad.top + 8, math.max(pad.top + 8, sz.height - pad.bottom - h - 8)));
    return Positioned(
      left: at.dx,
      top: at.dy,
      child: GestureDetector(
        onPanUpdate: (DragUpdateDetails d) => setState(() => _pos = at + d.delta),
        child: Material(
          color: Colors.transparent,
          child: Container(
            width: bw,
            height: h,
            padding: const EdgeInsets.fromLTRB(12, 0, 8, 0),
            decoration: BoxDecoration(
              gradient: const LinearGradient(colors: <Color>[Color(0xFF3D1C3B), Color(0xFF5A2D57)]),
              borderRadius: BorderRadius.circular(999),
              border: Border.all(color: _gold.withOpacity(.7)),
              boxShadow: const <BoxShadow>[BoxShadow(color: Color(0x55000000), blurRadius: 18, offset: Offset(0, 8))],
            ),
            child: Row(children: <Widget>[
              SizedBox(
                width: 22,
                height: 20,
                child: Row(crossAxisAlignment: CrossAxisAlignment.end, mainAxisAlignment: MainAxisAlignment.spaceBetween, children: <Widget>[
                  for (int b = 0; b < 5; b++)
                    Container(width: 3, height: 3 + 17 * (r.playing ? _bars[b].clamp(0.0, 1.0) : .12), decoration: BoxDecoration(color: _gold, borderRadius: BorderRadius.circular(2))),
                ]),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: GestureDetector(
                  onTap: _stations,
                  child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                    Text(r.name, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _ivory, fontSize: 13, fontWeight: FontWeight.w700)),
                    Text(r.playing ? 'June radio - tap for stations' : 'Paused', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _muted, fontSize: 10.5)),
                  ]),
                ),
              ),
              _b(r.playing ? Icons.pause_rounded : Icons.play_arrow_rounded, r.playing ? 'Pause' : 'Play', r.toggle, gold: true),
              _b(Icons.skip_next_rounded, 'Next station', () => r.step(1)),
              _b(Icons.close_rounded, 'Stop the radio', r.stop),
            ]),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------- v008: June's voice for other widgets
/// JuneSpeech.say('...') from any Lazo widget: through the June on screen if there is one (her core
/// moves with it), else a voice of its own. Honors the June voice switch (prefs 'juneSpeak'), waits
/// for the first tap on the web, and a newer line replaces an older one.
class JuneSpeech {
  static _JuneNativeState? _host;
  static _Voice? _solo;
  /// true while something else (the first-run tour) is narrating: the dashboard line keeps quiet
  static bool hold = false;
  static int _gen = 0;
  static Timer? _wait;

  static Future<bool> enabled() async {
    try {
      final SharedPreferences p = await SharedPreferences.getInstance();
      return p.getBool('juneSpeak') ?? true;
    } catch (_) {
      return true;
    }
  }

  static Future<void> setEnabled(bool on) async {
    try {
      final SharedPreferences p = await SharedPreferences.getInstance();
      await p.setBool('juneSpeak', on);
    } catch (_) {}
    final _JuneNativeState? h = _host;
    if (h != null && h.mounted) h._voice.enabled = on;
    if (!on) stop();
  }

  static Future<void> say(String text) async {
    final int g = ++_gen;
    _wait?.cancel();
    stop(keepGen: true);
    if (text.trim().isEmpty || !await enabled() || g != _gen) return;
    void go() {
      if (g != _gen) return;
      final _JuneNativeState? h = _host;
      if (h != null && h.mounted) {
        h._voice.say(text);
        return;
      }
      _solo ??= _Voice(_Api(), (bool s) => JuneRadio.I.duck(s));
      _solo!.say(text);
    }
    if (juneCanSpeak()) {
      go();
      return;
    }
    int n = 0;
    _wait = Timer.periodic(const Duration(milliseconds: 300), (Timer t) {
      if (g != _gen || ++n > 400) {
        t.cancel();
        return;
      }
      if (juneCanSpeak()) {
        t.cancel();
        go();
      }
    });
  }

  static void stop({bool keepGen = false}) {
    if (!keepGen) {
      _gen++;
      _wait?.cancel();
    }
    try {
      final _JuneNativeState? h = _host;
      if (h != null && h.mounted) h._voice.stop();
    } catch (_) {}
    try {
      _solo?.stop();
    } catch (_) {}
  }
}
"""
s = s.rstrip("\n") + "\n" + TAIL
OUT.write_text(s, encoding="utf-8", newline="\n")
print(f"wrote {OUT.name} ({len(s):,} chars)")
