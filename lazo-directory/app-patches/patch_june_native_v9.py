r"""patch_june_native_v9.py - JuneNative v8 -> v9 (JC-LAZO-JUNE-NATIVE-1016-009)

1. JUNE KEEPS TALKING WHEN YOU LEAVE THE PAGE. Her voice used to belong to one
   June widget and died with it: tap anywhere that changed the page and she
   stopped mid-sentence. Now, like the radio, there is one voice for the whole
   app (JuneSpeech.voice); every June widget speaks through it and, when it
   goes, she carries on.
2. THE FLOATING PLAYER CARRIES HER. While she talks and no June is on screen,
   the floating player shows "June" with moving bars and a Stop button (and the
   radio's play / pause when a station is on). It goes away when she finishes
   and the radio is off.
3. The brief plays through the same voice, so the floating Stop covers it too.

    python app-patches\patch_june_native_v9.py
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
s = (HERE / "JuneNative_v8.txt").read_text(encoding="utf-8")
OUT = HERE / "JuneNative_v9.txt"


def rep(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"anchor found {n}x (want {count}): {old[:80]!r}")
    s = s.replace(old, new)


# build id
rep("// Build ID: JC-LAZO-JUNE-NATIVE-1014-008 (008:", "// Build ID: JC-LAZO-JUNE-NATIVE-1016-009 (009: one voice for the whole app - June keeps talking when you leave the page, and the floating player shows her with a Stop button; base 008) (008:")
rep("// END OF FILE - JC-LAZO-JUNE-NATIVE-1014-008", "// END OF FILE - JC-LAZO-JUNE-NATIVE-1016-009")

# ---- _Voice: one clip played as speech (the brief), so the speaking state and Stop cover it
rep("""  void stop() {
    _gen++;
    _queue.clear();""", """  // v009: one clip (the brief) played as speech - the floating player shows it and its Stop works
  Future<bool> playAlone(String url, dynamic env) async {
    stop();
    final int g = _gen;
    speaking = true;
    onState(true);
    final bool ok = await playUrl(url, g, env);
    if (g == _gen) {
      speaking = false;
      onState(false);
    }
    return ok;
  }

  void stop() {
    _gen++;
    _queue.clear();""")

# ---- the widget speaks through the app's one voice instead of owning one
rep("""  final _Api _api = _Api();
  late final _Voice _voice = _Voice(_api, (bool s) {
    JuneRadio.I.duck(s);
    if (!mounted) return;
    setState(() => _mode = s ? 'speaking' : (_thinking ? 'thinking' : 'idle'));
  });""", """  final _Api _api = _Api();
  // v009: one voice for the whole app, like the radio - leaving the page no longer cuts her off
  _Voice get _voice => JuneSpeech.voice;
  void _onTalk() {
    if (!mounted) return;
    final bool s = JuneSpeech.talking.value;
    if (s) {
      // the floating player carries her if this page goes away mid-sentence (never during a build)
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted && JuneSpeech.talking.value) JuneRadio.I._ensureMini(context);
      });
    }
    setState(() => _mode = s ? 'speaking' : (_thinking ? 'thinking' : 'idle'));
  }""")

rep("""    JuneRadio.I.setVisible(this, true);
    JuneSpeech._host = this;
""", """    JuneRadio.I.setVisible(this, true);
    JuneSpeech.talking.addListener(_onTalk);
    if (_voice.speaking) _mode = 'speaking';
""")

rep("""    JuneRadio.I.setVisible(this, false);
    if (identical(JuneSpeech._host, this)) JuneSpeech._host = null;
""", """    JuneRadio.I.setVisible(this, false);
    JuneSpeech.talking.removeListener(_onTalk);
""")

rep("""    _voice.dispose();
    _ears.stop();""", """    // v009: no _voice.dispose() - she keeps talking on the next page
    _ears.stop();""")

# the brief goes through the voice's speaking state
rep("played = await _voice.playUrl(url, null, _map(j)['env']);", "played = await _voice.playAlone(url, _map(j)['env']);")

# ---- the radio's stop leaves the floating player up while she is still talking
rep("""    playing = false;
    _removeMini();
    _bump();""", """    playing = false;
    if (!JuneSpeech.talking.value) _removeMini();
    _bump();""")

# ---- the floating player: June while she talks, the radio otherwise
rep("""      final JuneRadio r = JuneRadio.I;
      if (!r.playing || r.anyJuneVisible) return;
      final List<double>? live = r.fft ? _juneWebFrame(5) : null;""", """      final JuneRadio r = JuneRadio.I;
      final bool talk = JuneSpeech.talking.value;
      if ((!r.playing && !talk) || r.anyJuneVisible) return;
      final List<double>? live = talk ? JuneSpeech.voice.frame(5) : (r.fft ? _juneWebFrame(5) : null);""")

rep("""    final JuneRadio r = JuneRadio.I;
    if (r.name.isEmpty || r.anyJuneVisible) return const SizedBox.shrink();""", """    final JuneRadio r = JuneRadio.I;
    final bool talk = JuneSpeech.talking.value;
    if ((r.name.isEmpty && !talk) || r.anyJuneVisible) return const SizedBox.shrink();""")

rep("Container(width: 3, height: 3 + 17 * (r.playing ? _bars[b].clamp(0.0, 1.0) : .12),",
    "Container(width: 3, height: 3 + 17 * (r.playing || talk ? _bars[b].clamp(0.0, 1.0) : .12),")

rep("""                  onTap: _stations,
                  child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                    Text(r.name, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _ivory, fontSize: 13, fontWeight: FontWeight.w700)),
                    Text(r.playing ? 'June radio - tap for stations' : 'Paused', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _muted, fontSize: 10.5)),
                  ]),
                ),
              ),
              _b(r.playing ? Icons.pause_rounded : Icons.play_arrow_rounded, r.playing ? 'Pause' : 'Play', r.toggle, gold: true),
              _b(Icons.skip_next_rounded, 'Next station', () => r.step(1)),
              _b(Icons.close_rounded, 'Stop the radio', r.stop),""", """                  onTap: talk ? null : _stations,
                  child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                    Text(talk ? 'June' : r.name, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _ivory, fontSize: 13, fontWeight: FontWeight.w700)),
                    Text(talk ? (r.name.isEmpty ? 'Still talking - tap stop to quiet her' : 'Talking over ' + r.name) : (r.playing ? 'June radio - tap for stations' : 'Paused'), maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _muted, fontSize: 10.5)),
                  ]),
                ),
              ),
              if (talk) ...<Widget>[
                if (r.name.isNotEmpty) _b(r.playing ? Icons.pause_rounded : Icons.play_arrow_rounded, r.playing ? 'Pause the radio' : 'Play the radio', r.toggle),
                _b(Icons.stop_rounded, 'Stop June', () => JuneSpeech.stop(), gold: true),
              ] else ...<Widget>[
                _b(r.playing ? Icons.pause_rounded : Icons.play_arrow_rounded, r.playing ? 'Pause' : 'Play', r.toggle, gold: true),
                _b(Icons.skip_next_rounded, 'Next station', () => r.step(1)),
                _b(Icons.close_rounded, 'Stop the radio', r.stop),
              ],""")

# ---- JuneSpeech owns the one voice
rep("""  static _JuneNativeState? _host;
  static _Voice? _solo;
""", """  /// v009: June's one voice for the whole app; every June widget speaks through it, so she
  /// outlives the page she started on (like JuneRadio)
  static final ValueNotifier<bool> talking = ValueNotifier<bool>(false);
  static final _Voice voice = _Voice(_Api(), (bool s) {
    JuneRadio.I.duck(s);
    talking.value = s;
    // never during a build: the floating player listens to rev
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!talking.value && !JuneRadio.I._on) JuneRadio.I._removeMini();
      JuneRadio.I._bump();
    });
  });
""")

rep("""    final _JuneNativeState? h = _host;
    if (h != null && h.mounted) h._voice.enabled = on;
    if (!on) stop();""", """    voice.enabled = on;
    if (!on) stop();""")

rep("""      if (g != _gen) return;
      final _JuneNativeState? h = _host;
      if (h != null && h.mounted) {
        h._voice.say(text);
        return;
      }
      _solo ??= _Voice(_Api(), (bool s) => JuneRadio.I.duck(s));
      _solo!.say(text);""", """      if (g != _gen) return;
      voice.say(text);""")

rep("""    try {
      final _JuneNativeState? h = _host;
      if (h != null && h.mounted) h._voice.stop();
    } catch (_) {}
    try {
      _solo?.stop();
    } catch (_) {}""", """    try {
      voice.stop();
    } catch (_) {}""")

OUT.write_text(s, encoding="utf-8", newline="\n")
print(f"wrote {OUT.name} ({len(s):,} chars)")
