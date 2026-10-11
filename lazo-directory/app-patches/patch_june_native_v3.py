"""patch_june_native_v3.py - JC-LAZO-JUNE-NATIVE-1011-003
JuneNative_v2.txt -> JuneNative_v3.txt. The deck, finished:
  1. REAL AUDIO ON THE WEB: a small script is injected once; every <audio> June plays (her clips AND
     the radio) is routed through a Web Audio analyser and 40 log-spaced bands + an envelope are
     written to document.body.dataset.juneLv each frame; the core reads them. Same analyser settings
     as the JARVIS hub (fftSize 2048, smoothing .05, -82..-14 dB), so it looks the same. If a stream
     refuses cross-origin audio, it is replayed plainly and the core falls back to its music motion.
  2. THE RADIO HAS CONTROLS: a now-playing strip under the core (station, previous/next, volume, Stop),
     a radio sheet from the dock, and the core moves to the music (real on web, music motion on phones).
  3. CHIPS THAT KNOW THE DAY: suggestions are built from the live state - the couple waiting longest,
     quiet leads, money due, the next wedding, what is left to book - then the evergreen ones, with
     a 'More' that opens the full list grouped.
  4. THE DOCK: a row of instruments under the chat - Brief, Waiting, Coming up, Weather, Money,
     Team / Page, Reminders, Memory, Radio, Clear - each opening the matching panel as a sheet, so
     nothing the hub can do is missing from the deck.
  5. Stop while she speaks: the state label becomes a Stop pill.
  python app-patches\\patch_june_native_v3.py
"""
from pathlib import Path
HERE = Path(__file__).resolve().parent


def rep(s, old, new, label, count=1):
    n = s.count(old)
    if n != count:
        raise SystemExit(f"{label}: anchor found {n}x, wanted {count}: {old[:70]!r}")
    return s.replace(old, new)


s = (HERE / "JuneNative_v2.txt").read_text(encoding="utf-8-sig")
s = rep(s, "// Build ID: JC-LAZO-JUNE-NATIVE-1010-002 (002:",
        "// Build ID: JC-LAZO-JUNE-NATIVE-1011-003 (003: real audio analysis on the web for clips and radio; radio controls; chips built from the day; the dock of instruments; base 002) (002:", 'build id')

# ---------------------------------------------------------------- the web analyser bridge
s = rep(s, "// ---------------------------------------------------------------- the voice out", r'''// ---------------------------------------------------------------- the web analyser (JC-LAZO-JUNE-NATIVE-1011-003)
// On the web every <audio> June plays goes through a Web Audio analyser; the script writes
// 40 bands + an envelope to document.body.dataset.juneLv each frame and the core reads them.
// Inert on phones (nothing here runs unless kIsWeb).
const String _kJuneWebJs = r"""
(function(){
  if (window.__june) return;
  var S = { ctx:null, an:null, nodes:new WeakMap(), buf:null, edges:null, NB:40, peak:0.04 };
  function ctx(){ if(!S.ctx){ try{ S.ctx = new (window.AudioContext||window.webkitAudioContext)(); }catch(e){ return null; } } if(S.ctx.state==='suspended'){ S.ctx.resume().catch(function(){}); } return S.ctx; }
  ['pointerdown','keydown','touchstart'].forEach(function(ev){ document.addEventListener(ev, function(){ ctx(); }, {passive:true}); });
  function tune(an){
    try{ an.fftSize=2048; an.smoothingTimeConstant=0.05; an.minDecibels=-82; an.maxDecibels=-14; }catch(e){}
    var sr=(an.context&&an.context.sampleRate)||44100, bins=an.frequencyBinCount, hz=sr/2/bins;
    S.buf=new Uint8Array(bins); S.time=new Uint8Array(an.fftSize);
    var NB=S.NB, lo=55, hi=Math.min(11000, sr/2-100), edges=new Int32Array(NB+1);
    for(var b=0;b<=NB;b++) edges[b]=Math.max(1, Math.round(lo*Math.pow(hi/lo,b/NB)/hz));
    for(var b2=1;b2<=NB;b2++) if(edges[b2]<=edges[b2-1]) edges[b2]=edges[b2-1]+1;
    S.edges=edges;
  }
  document.addEventListener('june-attach', function(e){
    var id=e.detail&&e.detail.id, el=id&&document.getElementById(id); if(!el) return;
    var c=ctx(); if(!c) return;
    try{
      var n=S.nodes.get(el);
      if(!n){ var src=c.createMediaElementSource(el); var an=c.createAnalyser(); tune(an); src.connect(an); an.connect(c.destination); n={src:src,an:an}; S.nodes.set(el,n); }
      S.an=n.an;
    }catch(err){ S.an=null; }
  });
  document.addEventListener('june-detach', function(){ S.an=null; document.body.dataset.juneLv=''; });
  var out=new Array(S.NB);
  function loop(){
    if(S.an&&S.edges){
      S.an.getByteFrequencyData(S.buf); S.an.getByteTimeDomainData(S.time);
      for(var b=0;b<S.NB;b++){ var m=0; for(var i=S.edges[b];i<S.edges[b+1];i++){ if(S.buf[i]>m) m=S.buf[i]; } var tilt=0.9+0.35*(b/S.NB); out[b]=Math.round(Math.min(1, Math.pow(m/255,1.1)*tilt*1.25)*100); }
      var sq=0,N=S.time.length; for(var j=0;j<N;j++){ var v=(S.time[j]-128)/128; sq+=v*v; }
      var rms=Math.sqrt(sq/N); S.peak=Math.max(rms, S.peak*0.995, 0.04); var env=Math.round(Math.min(1, rms/S.peak)*100);
      document.body.dataset.juneLv=out.join(',')+'|'+env;
    }
    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);
  window.__june=S;
})();
""";
bool _juneWebReady = false;
int _juneWebSeq = 0;

void _juneWebInstall() {
  if (!kIsWeb || _juneWebReady) return;
  _juneWebReady = true;
  try {
    final html.ScriptElement sc = html.ScriptElement();
    sc.text = _kJuneWebJs;
    html.document.head?.append(sc);
  } catch (_) {}
}

/// gives the element an id, puts it in the document and asks the script to analyse it
String _juneWebAttach(html.AudioElement a) {
  final String id = 'june-audio-${++_juneWebSeq}';
  try {
    a.id = id;
    a.style.display = 'none';
    html.document.body?.append(a);
    html.document.dispatchEvent(html.CustomEvent('june-attach', detail: <String, dynamic>{'id': id}));
  } catch (_) {}
  return id;
}

void _juneWebDetach(html.AudioElement? a) {
  try {
    html.document.dispatchEvent(html.CustomEvent('june-detach'));
    a?.remove();
  } catch (_) {}
}

/// the latest frame from the script: [levels 0..1 x nb, envelope 0..1], or null
List<double>? _juneWebFrame(int nb) {
  if (!kIsWeb) return null;
  try {
    final String? raw = html.document.body?.dataset['juneLv'];
    if (raw == null || raw.isEmpty) return null;
    final int bar = raw.indexOf('|');
    final List<String> parts = (bar < 0 ? raw : raw.substring(0, bar)).split(',');
    if (parts.length < 8) return null;
    final List<double> out = List<double>.filled(nb + 1, 0);
    for (int b = 0; b < nb; b++) {
      final double x = b * (parts.length - 1) / math.max(1, nb - 1);
      final int j0 = x.floor();
      final int j1 = math.min(parts.length - 1, j0 + 1);
      final double k = x - j0;
      final double a = (int.tryParse(parts[j0]) ?? 0) / 100.0;
      final double c = (int.tryParse(parts[j1]) ?? 0) / 100.0;
      out[b] = a * (1 - k) + c * k;
    }
    out[nb] = bar < 0 ? 0 : (int.tryParse(raw.substring(bar + 1)) ?? 0) / 100.0;
    return out;
  } catch (_) {
    return null;
  }
}

// ---------------------------------------------------------------- the voice out''', 'web bridge')

# clips on the web: through the analyser (cross-origin allowed by the hub)
s = rep(s, '''      if (kIsWeb) {
        final html.AudioElement a = html.AudioElement();
        _el = a;
        a.src = url;
        a.preload = 'auto';
        final Completer<void> c = Completer<void>();''',
        '''      if (kIsWeb) {
        final html.AudioElement a = html.AudioElement();
        _el = a;
        a.crossOrigin = 'anonymous';
        a.src = url;
        a.preload = 'auto';
        _juneWebAttach(a);
        final Completer<void> c = Completer<void>();''', 'clip attach')
s = rep(s, '''        await c.future.timeout(const Duration(minutes: 6), onTimeout: () {});
        if (identical(_el, a)) _el = null;''',
        '''        await c.future.timeout(const Duration(minutes: 6), onTimeout: () {});
        _juneWebDetach(a);
        if (identical(_el, a)) _el = null;''', 'clip detach')
s = rep(s, '''    try {
      _el?.pause();
      _el = null;
    } catch (_) {}
    try {
      _player?.stop();
    } catch (_) {}
    _trk = null;
    if (speaking) {''',
        '''    try {
      _el?.pause();
      _juneWebDetach(_el);
      _el = null;
    } catch (_) {}
    try {
      _player?.stop();
    } catch (_) {}
    _trk = null;
    if (speaking) {''', 'voice stop detach')

# ---------------------------------------------------------------- the radio: controls, volume, analyser, fallback
s = rep(s, '''  AudioPlayer? _radioPlayer;
  html.AudioElement? _radioEl;

  Future<void> _radioPlay(int i) async {
    _radioStop();
    final List<String> st = _radio[i];
    setState(() => _radioName = st[0]);
    try {
      if (kIsWeb) {
        final html.AudioElement a = html.AudioElement();
        a.src = st[1];
        a.volume = 0.7;
        _radioEl = a;
        await a.play().catchError((Object _) {});
      } else {
        final AudioPlayer p = AudioPlayer();
        try {
          p.setAudioContext(AudioContext(iOS: AudioContextIOS(category: AVAudioSessionCategory.playback), android: AudioContextAndroid()));
        } catch (_) {}
        p.setVolume(0.7);
        _radioPlayer = p;
        await p.play(UrlSource(st[1]));
      }
    } catch (e) {
      _addMsg('sys', 'That station wouldn\\'t start: ' + e.toString());
      setState(() => _radioName = '');
    }
  }

  void _radioStop() {
    try {
      _radioEl?.pause();
      _radioEl = null;
    } catch (_) {}
    try {
      _radioPlayer?.stop();
      _radioPlayer?.dispose();
      _radioPlayer = null;
    } catch (_) {}
    if (_radioName.isNotEmpty && mounted) setState(() => _radioName = '');
  }''',
        '''  AudioPlayer? _radioPlayer;
  html.AudioElement? _radioEl;
  int _radioIdx = -1;
  double _radioVol = 0.7;
  bool _radioFft = false; // web: the stream allowed cross-origin audio, so the core has its spectrum

  Future<void> _radioPlay(int i) async {
    _radioStop();
    final List<String> st = _radio[i];
    _radioIdx = i;
    setState(() => _radioName = st[0]);
    try {
      if (kIsWeb) {
        await _radioPlayWeb(st[1], true);
      } else {
        final AudioPlayer p = AudioPlayer();
        try {
          p.setAudioContext(AudioContext(iOS: AudioContextIOS(category: AVAudioSessionCategory.playback), android: AudioContextAndroid()));
        } catch (_) {}
        p.setVolume(_radioVol);
        _radioPlayer = p;
        await p.play(UrlSource(st[1]));
      }
    } catch (e) {
      _addMsg('sys', 'That station wouldn\\'t start: ' + e.toString());
      setState(() => _radioName = '');
    }
  }

  // web: first through the analyser (needs the stream to allow cross-origin audio); if the element
  // errors, once more plainly so the music still plays, with the core on its music motion
  Future<void> _radioPlayWeb(String url, bool withFft) async {
    final html.AudioElement a = html.AudioElement();
    if (withFft) a.crossOrigin = 'anonymous';
    a.src = url;
    a.volume = _radioVol;
    _radioEl = a;
    _radioFft = withFft;
    if (withFft) _juneWebAttach(a);
    a.onError.listen((_) {
      if (!identical(_radioEl, a)) return;
      if (withFft) {
        _juneWebDetach(a);
        _radioEl = null;
        _radioPlayWeb(url, false);
      } else {
        _addMsg('sys', 'That station wouldn\\'t start.');
        _radioStop();
      }
    });
    await a.play().catchError((Object _) {});
  }

  void _radioStop() {
    try {
      _radioEl?.pause();
      if (_radioFft) _juneWebDetach(_radioEl);
      _radioEl?.remove();
      _radioEl = null;
    } catch (_) {}
    try {
      _radioPlayer?.stop();
      _radioPlayer?.dispose();
      _radioPlayer = null;
    } catch (_) {}
    _radioFft = false;
    if (_radioName.isNotEmpty && mounted) setState(() => _radioName = '');
  }

  void _radioStep(int d) {
    if (_radioIdx < 0) {
      _radioPlay(0);
      return;
    }
    _radioPlay((_radioIdx + d + _radio.length) % _radio.length);
  }

  void _radioSetVol(double v) {
    _radioVol = v.clamp(0.0, 1.0);
    try {
      _radioEl?.volume = _radioVol;
    } catch (_) {}
    try {
      _radioPlayer?.setVolume(_radioVol);
    } catch (_) {}
    setState(() {});
  }

  // the now-playing strip: station, previous / next, volume, stop
  Widget _nowPlaying() {
    if (_radioName.isEmpty) return const SizedBox.shrink();
    return Container(
      margin: const EdgeInsets.only(top: 10),
      padding: const EdgeInsets.fromLTRB(12, 8, 8, 8),
      decoration: BoxDecoration(color: Colors.black.withOpacity(.28), borderRadius: BorderRadius.circular(14), border: Border.all(color: _sage.withOpacity(.45))),
      child: Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
        Row(children: <Widget>[
          const Icon(Icons.radio_rounded, size: 15, color: _sage),
          const SizedBox(width: 6),
          Expanded(child: Text(_radioName, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _ivory, fontSize: 12.5, fontWeight: FontWeight.w700))),
          _iconBtn(Icons.skip_previous_rounded, () => _radioStep(-1), 'Previous station'),
          _iconBtn(Icons.skip_next_rounded, () => _radioStep(1), 'Next station'),
          _iconBtn(Icons.stop_rounded, _radioStop, 'Stop the music', gold: true),
        ]),
        Row(children: <Widget>[
          const Icon(Icons.volume_down_rounded, size: 14, color: _muted),
          Expanded(
            child: SliderTheme(
              data: SliderTheme.of(context).copyWith(trackHeight: 2, thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 6), overlayShape: const RoundSliderOverlayShape(overlayRadius: 12), activeTrackColor: _sage, inactiveTrackColor: Colors.white.withOpacity(.15), thumbColor: _sage),
              child: Slider(value: _radioVol, onChanged: _radioSetVol),
            ),
          ),
          const Icon(Icons.volume_up_rounded, size: 14, color: _muted),
        ]),
      ]),
    );
  }

  Widget _iconBtn(IconData icon, VoidCallback onTap, String tip, {bool gold = false}) => Tooltip(
        message: tip,
        child: GestureDetector(
          onTap: onTap,
          child: Container(
            width: 30,
            height: 30,
            margin: const EdgeInsets.only(left: 4),
            decoration: BoxDecoration(shape: BoxShape.circle, color: gold ? _gold : Colors.white.withOpacity(.08), border: Border.all(color: gold ? _gold : Colors.white.withOpacity(.14))),
            child: Icon(icon, size: 17, color: gold ? _plumDeep : _ivory),
          ),
        ),
      );''', 'radio')

# the radio card gets the volume too (the hub's panel and the dock's sheet)
s = rep(s, '''  Widget _radioCard() => _card(
        title: 'Radio',
        trailing: _radioName.isNotEmpty ? _btn('Stop', _radioStop, icon: Icons.stop_rounded) : null,
        child: Wrap(''',
        '''  Widget _radioCard() => _card(
        title: 'Radio',
        sub: _radioName.isEmpty ? 'Something to work to. Say "play some music" or pick a station.' : 'Playing $_radioName',
        trailing: _radioName.isNotEmpty ? _btn('Stop', _radioStop, icon: Icons.stop_rounded) : null,
        child: Wrap(''', 'radio card sub')

# ---------------------------------------------------------------- the tick: web analyser first, then the track, then music motion
s = rep(s, '''    // JC-LAZO-JUNE-ENV-1010-001: while a clip plays, the bars are the clip
    final List<double>? live = m == 'speaking' ? _voice.frame(_nb) : null;
    if (live != null) {
      double sum = 0;
      for (final double v in live) sum += v;
      target = math.min(1, (sum / _nb) * 1.7 + 0.06);
    }''',
        '''    // JC-LAZO-JUNE-NATIVE-1011-003: the real thing when we have it - the web
    // analyser (clips and radio), else the clip's level track; otherwise motion
    final bool radioOn = _radioName.isNotEmpty;
    List<double>? live;
    if (kIsWeb && (m == 'speaking' || (radioOn && _radioFft && m == 'idle'))) {
      final List<double>? f = _juneWebFrame(_nb);
      if (f != null) {
        live = f.sublist(0, _nb);
        target = math.min(1, f[_nb] * 0.9 + 0.05);
      }
    }
    if (live == null && m == 'speaking') live = _voice.frame(_nb);
    if (live != null && !(kIsWeb && m != 'speaking')) {
      double sum = 0;
      for (final double v in live) sum += v;
      target = math.min(1, (sum / _nb) * 1.7 + 0.06);
    }
    if (live == null && radioOn && m == 'idle') {
      // phones (and streams without cross-origin audio): music motion - a beat and a slow swell
      final double beat = math.max(0, math.sin(_phase * 2 * math.pi * 1.9));
      target = 0.22 + 0.18 * math.pow(beat, 3) + 0.08 * math.sin(_phase * 0.6);
    }''', 'tick live')
s = rep(s, "      else if (m == 'thinking') shape = 0.5 + 0.5 * math.sin(_phase * 5 - b * 0.35);\n      else shape = 0.4 + 0.3 * math.sin(_phase * 2 + b);",
        "      else if (m == 'thinking') shape = 0.5 + 0.5 * math.sin(_phase * 5 - b * 0.35);\n      else if (radioOn) shape = (0.55 + 0.45 * math.sin(_phase * 3.1 + b * 0.9)) * (0.7 + 0.3 * math.exp(-math.pow((b - _nb * 0.2) / (_nb * 0.35), 2)));\n      else shape = 0.4 + 0.3 * math.sin(_phase * 2 + b);", 'tick shape')
s = rep(s, "      final double v = live != null ? live[b] : (m == 'idle' ? 0.05 + 0.04 * math.sin(_phase * 1.1 + b * 0.45) * math.sin(_phase * 0.7 + b * 0.2) : target * shape);",
        "      final double v = live != null ? live[b] : (m == 'idle' && !radioOn ? 0.05 + 0.04 * math.sin(_phase * 1.1 + b * 0.45) * math.sin(_phase * 0.7 + b * 0.2) : target * shape);", 'tick v')
s = rep(s, "    _rot += dt * (m == 'thinking' ? 1.4 : m == 'idle' ? 0.12 : 0.25 + _swell * 0.6);",
        "    _rot += dt * (m == 'thinking' ? 1.4 : m == 'idle' ? (radioOn ? 0.3 : 0.12) : 0.25 + _swell * 0.6);", 'tick rot')

# ---------------------------------------------------------------- init: install the bridge
s = rep(s, "    _ticker = createTicker(_tick)..start();\n    _load(first: true);",
        "    _juneWebInstall();\n    _ticker = createTicker(_tick)..start();\n    _load(first: true);", 'init')

# ---------------------------------------------------------------- chips that know the day
s = rep(s, '''  List<String> get _chips => _couple
      ? <String>['What should we do next?', 'Who\\'s waiting on us?', 'How are the RSVPs?', 'Where are we on budget?', 'What\\'s the forecast for our day?', 'Find us a florist', 'Play some music']
      : <String>['Who is waiting on me?', 'What\\'s on this week?', 'Weather for my next wedding', 'How much is outstanding?', 'Which leads went quiet?', 'Play some music'];
''',
        '''  // JC-LAZO-JUNE-NATIVE-1011-003: suggestions built from the day, then the evergreen ones
  List<String> get _chips {
    final List<String> out = <String>[];
    final List<Map<String, dynamic>> waiting = _list(_snap['waiting']);
    final Map<String, dynamic> money = _map(_snap['money']);
    final List<Map<String, dynamic>> weddings = _list(_snap['weddings']);
    final List<Map<String, dynamic>> reminders = _list(_snap['reminders']);
    if (_couple) {
      if (waiting.isNotEmpty) out.add('Draft a reply to ${_s(waiting.first['vendor'])}');
      String need = '';
      for (final Map<String, dynamic> p in _list(_snap['team'])) {
        if (_s(p['status']) == 'needed' || _s(p['status']).isEmpty) {
          need = _s(p['label']).isNotEmpty ? _s(p['label']) : _s(p['category']).replaceAll('-', ' ');
          if (need.isNotEmpty) break;
        }
      }
      if (need.isNotEmpty) out.add('Find us a ${need.toLowerCase().replaceAll('wedding ', '')}');
      if (_n(money['open']) > 0) out.add('What\\'s due this month?');
      if (_n(_snap['daysToGo']) > 0 && _n(_snap['daysToGo']) < 30) out.add('What\\'s left before the day?');
      out.addAll(<String>['What should we do next?', 'Who\\'s waiting on us?', 'How are the RSVPs?', 'Who hasn\\'t RSVP\\'d?', 'Where are we on budget?', 'What\\'s the forecast for our day?', 'Help us with the seating', 'Show our shopping list', 'What should we ask a venue?', 'Remind us to call the florist Friday', 'What do you remember about us?', 'Play some music']);
    } else {
      if (waiting.isNotEmpty) out.add('Draft a reply to ${_s(waiting.first['couple'])}');
      if (waiting.length > 1) out.add('Who is waiting on me?');
      if (_n(money['overdue']) > 0) out.add('Who is overdue?');
      else if (_n(money['outstanding']) > 0) out.add('How much is outstanding?');
      if (weddings.isNotEmpty) out.add('Weather for ${_s(weddings.first['couple'])}\\'s wedding');
      if (reminders.isNotEmpty) out.add('What are my reminders?');
      out.addAll(<String>['Who is waiting on me?', 'What\\'s on this week?', 'Which leads went quiet?', 'Write a first reply for my newest lead', 'How am I ranking?', 'Read me my reviews', 'Block a date for me', 'Remind me to follow up tomorrow', 'What should I post this week?', 'Give me the Monday review', 'What do you remember about me?', 'Play some music']);
    }
    final List<String> seen = <String>[];
    for (final String c in out) {
      if (!seen.contains(c)) seen.add(c);
    }
    return seen;
  }

  bool _chipsAll = false;
''', 'chips')
s = rep(s, '''  Widget _chipsWrap() => Wrap(
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
      );''',
        '''  Widget _chip(String c, {VoidCallback? onTap, bool accent = false}) => GestureDetector(
        onTap: onTap ?? () => _ask(c),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 6),
          decoration: BoxDecoration(color: accent ? _gold.withOpacity(.16) : Colors.white.withOpacity(.07), borderRadius: BorderRadius.circular(999), border: Border.all(color: accent ? _gold.withOpacity(.5) : Colors.white.withOpacity(.14))),
          child: Text(c, style: TextStyle(color: accent ? _goldSoft : _ivory, fontSize: 12)),
        ),
      );

  Widget _chipsWrap({int show = 7}) {
    final List<String> all = _chips;
    final List<String> vis = _chipsAll ? all : all.take(show).toList();
    return Wrap(
      spacing: 6,
      runSpacing: 6,
      children: <Widget>[
        for (final String c in vis) _chip(c),
        if (all.length > show) _chip(_chipsAll ? 'Fewer' : 'More…', onTap: () => setState(() => _chipsAll = !_chipsAll), accent: true),
      ],
    );
  }''', 'chips wrap')

# ---------------------------------------------------------------- the dock + the deck
s = rep(s, '''      final Widget left = Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
        _core(coreSize),
        const SizedBox(height: 2),
        _stateLabel(),
        const SizedBox(height: 12),
        controls,
      ]);''',
        '''      final Widget left = Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
        _core(coreSize),
        const SizedBox(height: 2),
        _voice.speaking || _mode == 'speaking'
            ? _btn('Stop', () {
                _voice.stop();
                if (mounted) setState(() => _mode = 'idle');
              }, icon: Icons.stop_rounded)
            : _stateLabel(),
        const SizedBox(height: 12),
        controls,
        _nowPlaying(),
      ]);''', 'deck left')
s = rep(s, '''        const SizedBox(height: 10),
        _inputRow(),
        const SizedBox(height: 10),
        _chipsWrap(),
      ]);
      if (!wide) return Column(children: <Widget>[left, const SizedBox(height: 16), right]);''',
        '''        const SizedBox(height: 10),
        _inputRow(),
        const SizedBox(height: 10),
        _chipsWrap(show: wide ? 8 : 5),
        const SizedBox(height: 12),
        _dock(wide),
      ]);
      if (!wide) return Column(children: <Widget>[left, const SizedBox(height: 16), right]);''', 'deck right')

s = rep(s, "  Widget _deck(BuildContext context) {",
        '''  // ---- the dock (JC-LAZO-JUNE-NATIVE-1011-003): every panel the hub has, one tap from the deck
  Future<void> _sheet(String title, Widget Function() build) async {
    if (!mounted) return;
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (BuildContext ctx) => StatefulBuilder(builder: (BuildContext sc, StateSetter setSheet) {
        return Container(
          constraints: BoxConstraints(maxHeight: MediaQuery.of(ctx).size.height * .86),
          decoration: const BoxDecoration(
            gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: <Color>[Color(0xFF2A1229), Color(0xFF3D1C3B)]),
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: SafeArea(
            top: false,
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(16, 10, 16, 20),
              child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
                Center(child: Container(width: 38, height: 4, margin: const EdgeInsets.only(bottom: 12), decoration: BoxDecoration(color: Colors.white.withOpacity(.25), borderRadius: BorderRadius.circular(2)))),
                // the panel reads this widget's state; rebuild it when ours changes
                _SheetHost(parent: this, build: build),
              ]),
            ),
          ),
        );
      }),
    );
    if (mounted) setState(() {});
  }

  Widget _dockBtn(IconData icon, String label, VoidCallback onTap, {String? badge, bool on = false}) => Tooltip(
        message: label,
        child: GestureDetector(
          onTap: onTap,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
            decoration: BoxDecoration(color: on ? _gold.withOpacity(.18) : Colors.black.withOpacity(.22), borderRadius: BorderRadius.circular(12), border: Border.all(color: on ? _gold.withOpacity(.6) : Colors.white.withOpacity(.1))),
            child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
              Icon(icon, size: 15, color: on ? _gold : _goldSoft),
              const SizedBox(width: 6),
              Text(label, style: TextStyle(color: on ? _goldSoft : _ivory, fontSize: 11.5, fontWeight: FontWeight.w600)),
              if (badge != null && badge.isNotEmpty) ...<Widget>[
                const SizedBox(width: 6),
                Container(padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1), decoration: BoxDecoration(color: _rose, borderRadius: BorderRadius.circular(8)), child: Text(badge, style: const TextStyle(color: _plumDeep, fontSize: 10.5, fontWeight: FontWeight.w800))),
              ],
            ]),
          ),
        ),
      );

  Widget _dock(bool wide) {
    final int waiting = _list(_snap['waiting']).length + (_couple ? _list(_snap['tasks']).length : 0);
    final int rem = _list(_snap['reminders']).length;
    final Map<String, dynamic> money = _map(_snap['money']);
    final num due = _couple ? _n(money['open']) : _n(money['outstanding']);
    return Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
      _dockBtn(Icons.auto_stories_rounded, 'Brief', () => _sheet('Brief', _briefCard)),
      _dockBtn(Icons.mark_chat_unread_rounded, 'Waiting', () => _sheet('Waiting', _waitingCard), badge: waiting > 0 ? '$waiting' : null),
      _dockBtn(Icons.event_rounded, 'Coming up', () => _sheet('Coming up', _upcomingCard)),
      _dockBtn(Icons.wb_sunny_rounded, 'Weather', () => _sheet('Weather', _weatherCard)),
      _dockBtn(Icons.payments_rounded, 'Money', () => _sheet('Money', _moneyCard), badge: due > 0 ? '\\$${due.round()}' : null),
      if (_couple) _dockBtn(Icons.groups_rounded, 'Team', () => _sheet('Team', _teamCard)) else _dockBtn(Icons.storefront_rounded, 'My page', () => _sheet('My page', _pageCard)),
      if (_couple) _dockBtn(Icons.how_to_reg_rounded, 'Guests', () => _sheet('Guests', _guestsCard)),
      _dockBtn(Icons.alarm_rounded, 'Reminders', () => _sheet('Reminders', _remindersCard), badge: rem > 0 ? '$rem' : null),
      _dockBtn(Icons.psychology_rounded, 'Memory', () => _sheet('Memory', _memoryCard)),
      _dockBtn(Icons.radio_rounded, 'Radio', () => _sheet('Radio', _radioCard), on: _radioName.isNotEmpty),
      if (_chat.isNotEmpty)
        _dockBtn(Icons.cleaning_services_rounded, 'Clear chat', () => setState(() {
              _chat.clear();
              _hist = <Map<String, dynamic>>[];
            })),
    ]);
  }

  Widget _deck(BuildContext context) {''', 'dock')

# the sheet host: rebuilds the panel whenever the widget's state changes (reminders added, radio switched ...)
s = rep(s, "// END OF FILE - JC-LAZO-JUNE-NATIVE-1010-002",
        '''// JC-LAZO-JUNE-NATIVE-1011-003: a dock sheet shows one of the hub's panels; the panel reads the
// parent's state, so the host rebuilds on every parent build (the parent calls setState freely).
class _SheetHost extends StatefulWidget {
  const _SheetHost({required this.parent, required this.build});
  final _JuneNativeState parent;
  final Widget Function() build;
  @override
  State<_SheetHost> createState() => _SheetHostState();
}

class _SheetHostState extends State<_SheetHost> {
  Timer? _t;
  @override
  void initState() {
    super.initState();
    // the parent's setState does not reach a sheet on another route; a light poll keeps it fresh
    _t = Timer.periodic(const Duration(milliseconds: 400), (_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _t?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => widget.build();
}
// END OF FILE - JC-LAZO-JUNE-NATIVE-1011-003''', 'sheet host')


# June says what she put on instead of a blank bubble
s = rep(s, """      if (i >= 0) {
        _radioPlay(i);
        return ' ';
      }""", """      if (i >= 0) {
        _radioPlay(i);
        return 'Playing ${_radio[i][0]}. Say "stop the music" or tap Stop under the core whenever you like.';
      }""", 'radio reply')

# phones: room under the dock so the dashboard's floating button never covers it
s = rep(s, "      if (!wide) return Column(children: <Widget>[left, const SizedBox(height: 16), right]);",
        "      if (!wide) return Column(children: <Widget>[left, const SizedBox(height: 16), right, const SizedBox(height: 56)]);", 'deck phone pad')

# clips on the web: retry plainly if the analysed load errors
s = rep(s, "      if (kIsWeb) {\n        final html.AudioElement a = html.AudioElement();\n        _el = a;\n        a.crossOrigin = 'anonymous';\n        a.src = url;\n        a.preload = 'auto';\n        _juneWebAttach(a);\n        final Completer<void> c = Completer<void>();\n        a.onEnded.listen((_) {\n          if (!c.isCompleted) c.complete();\n        });\n        a.onError.listen((_) {\n          if (!c.isCompleted) c.complete();\n        });\n        _t0 = DateTime.now();\n        await a.play().catchError((Object _) {});\n        await c.future.timeout(const Duration(minutes: 6), onTimeout: () {});\n        _juneWebDetach(a);\n        if (identical(_el, a)) _el = null;\n      } else {",
        '      if (kIsWeb) {\n        // through the analyser first; if the element errors (a clip the browser\n        // will not share cross-origin), once more plainly so she is never silent\n        final bool ok = await _playWeb(url, true);\n        if (!ok && g == _gen) await _playWeb(url, false);\n      } else {', 'clip fallback')
s = rep(s, "  // plays one URL to the end (web: an <audio> element; phones: audioplayers)\n  Future<void> playUrl(String url, [int? gen, dynamic env]) async {", "  // web: one element, played to the end; false if it errored before it ended\n  Future<bool> _playWeb(String url, bool withFft) async {\n    final html.AudioElement a = html.AudioElement();\n    _el = a;\n    if (withFft) a.crossOrigin = 'anonymous';\n    a.src = url;\n    a.preload = 'auto';\n    if (withFft) _juneWebAttach(a);\n    final Completer<bool> c = Completer<bool>();\n    a.onEnded.listen((_) {\n      if (!c.isCompleted) c.complete(true);\n    });\n    a.onError.listen((_) {\n      if (!c.isCompleted) c.complete(false);\n    });\n    _t0 = DateTime.now();\n    await a.play().catchError((Object _) {});\n    final bool ok = await c.future.timeout(const Duration(minutes: 6), onTimeout: () => true);\n    if (withFft) _juneWebDetach(a);\n    try {\n      a.remove();\n    } catch (_) {}\n    if (identical(_el, a)) _el = null;\n    return ok;\n  }\n\n  // plays one URL to the end (web: an <audio> element; phones: audioplayers)\n  Future<void> playUrl(String url, [int? gen, dynamic env]) async {", 'clip helper')

# greet by first name when the plan has no names
s = rep(s, "    final String who = _couple ? _s(_map(_snap['couple'])['names']) : '';\n    return who.isEmpty ? '$tod.' : '$tod, $who.';",
        "    String who = _couple ? _s(_map(_snap['couple'])['names']) : '';\n    if (who.isEmpty) {\n      // the person's own first name, from their Lazo sign-in\n      final String dn = (FirebaseAuth.instance.currentUser?.displayName ?? '').trim();\n      if (dn.isNotEmpty) who = dn.split(' ').first;\n    }\n    return who.isEmpty ? '$tod.' : '$tod, $who.';", 'greeting name')
(HERE / "JuneNative_v3.txt").write_text(s, encoding="utf-8")
print("wrote JuneNative_v3.txt", len(s))
