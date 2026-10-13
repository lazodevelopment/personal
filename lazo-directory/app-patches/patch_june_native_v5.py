"""patch_june_native_v5.py - JC-LAZO-JUNE-NATIVE-1013-005
JuneNative_v4.txt -> JuneNative_v5.txt. June is never silent on phones (the Jovi voice stack, ported):
  1. A playback watchdog: if a clip never starts (no position within 5 s) or never ends (its known
     length from the level track + 4 s, else 90 s), playback is abandoned instead of hanging, which
     used to leave the queue stuck for 6 minutes with the text on screen and no voice.
  2. The phone's own voice (flutter_tts, en-GB to stay British) speaks any sentence whose clip could
     not be fetched or played, and takes over entirely when the hub says tts is not configured.
  3. The core keeps moving on its speaking motion while the device voice talks.
Pairs with the worker fix JC-LAZO-JUNE-CLIP-RANGE-1013-001 (clips now answer byte-range requests,
which iOS AVPlayer requires; that was the silent-voice bug).
NEW dependency in FlutterFlow: flutter_tts (Settings -> Custom Code -> Dependencies).
  python app-patches\\patch_june_native_v5.py
"""
from pathlib import Path
HERE = Path(__file__).resolve().parent


def rep(s, old, new, label, count=1):
    n = s.count(old)
    if n != count:
        raise SystemExit(f"{label}: anchor found {n}x, wanted {count}: {old[:80]!r}")
    return s.replace(old, new)


s = (HERE / "JuneNative_v4.txt").read_text(encoding="utf-8-sig")
s = rep(s, "// Build ID: JC-LAZO-JUNE-NATIVE-1011-004 (004:",
        "// Build ID: JC-LAZO-JUNE-NATIVE-1013-005 (005: never silent on phones - playback watchdog + the device's own voice as fallback, ported from Jovi; base 004) (004:", "build id")
s = rep(s, "//   speech_to_text ^7.0.0  (NEW - voice input; without it, remove the mic\n",
        "//   flutter_tts           (NEW in 005 - the phone's own voice when a clip cannot play)\n//   speech_to_text ^7.0.0  (NEW - voice input; without it, remove the mic\n", "deps doc")
s = rep(s, "import 'package:speech_to_text/speech_to_text.dart' as stt;\n",
        "import 'package:speech_to_text/speech_to_text.dart' as stt;\nimport 'package:flutter_tts/flutter_tts.dart';\n", "import")

# ---- _Voice: the fallback voice and the hub-voice switch
s = rep(s, "  bool speaking = false;\n  bool enabled = true;\n  int _gen = 0;\n  AudioPlayer? _player;\n  html.AudioElement? _el;\n",
        "  bool speaking = false;\n  bool enabled = true;\n  bool hubVoice = true; // false once the hub says tts is not configured; the device voice takes over\n  int _gen = 0;\n  AudioPlayer? _player;\n  html.AudioElement? _el;\n  FlutterTts? _tts;\n", "voice fields")

s = rep(s, """  void say(String text) {
    final String t = text.trim();
    if (!enabled || t.isEmpty) return;""",
        """  FlutterTts _ensureTts() {
    if (_tts != null) return _tts!;
    final FlutterTts t = FlutterTts();
    try {
      t.setLanguage('en-GB');
      t.setSpeechRate(0.5);
      t.setPitch(1.05);
      t.awaitSpeakCompletion(true);
      t.setIosAudioCategory(IosTextToSpeechAudioCategory.playback, <IosTextToSpeechAudioCategoryOptions>[IosTextToSpeechAudioCategoryOptions.mixWithOthers, IosTextToSpeechAudioCategoryOptions.duckOthers]);
    } catch (_) {}
    _tts = t;
    return t;
  }

  // JC-LAZO-JUNE-NATIVE-1013-005: the phone speaks the sentence itself when a clip cannot be fetched or played
  Future<void> _speakDevice(String text, int gen) async {
    if (kIsWeb || gen != _gen) return;
    try {
      _t0 = DateTime.now();
      await _ensureTts().speak(text).timeout(const Duration(minutes: 2), onTimeout: () => 1);
    } catch (e) {
      debugPrint('LAZO june device voice: ' + e.toString());
    }
  }

  void say(String text) {
    final String t = text.trim();
    if (!enabled || t.isEmpty) return;""", "tts helpers")

s = rep(s, """      String url = '';
      dynamic env;
      try {
        final dynamic j = await api.post('/api/clip', <String, dynamic>{'text': t});
        url = _s(_map(j)['url']);
        env = _map(j)['env'];
      } catch (e) {
        debugPrint('LAZO june clip: ' + e.toString());
      }
      if (url.isEmpty || gen != _gen) continue;
      await playUrl(url, gen, env);""",
        """      String url = '';
      dynamic env;
      if (hubVoice) {
        try {
          final dynamic j = await api.post('/api/clip', <String, dynamic>{'text': t});
          url = _s(_map(j)['url']);
          env = _map(j)['env'];
        } catch (e) {
          final String m = e.toString();
          if (m.contains('not configured')) hubVoice = false;
          debugPrint('LAZO june clip: ' + m);
        }
      }
      if (gen != _gen) break;
      bool ok = false;
      if (url.isNotEmpty) ok = await playUrl(url, gen, env);
      if (!ok && gen == _gen) await _speakDevice(t, gen);""", "pump")

# ---- playUrl reports whether the clip actually played; the phone branch gets the watchdog
s = rep(s, "  Future<void> playUrl(String url, [int? gen, dynamic env]) async {\n    final int g = gen ?? _gen;\n    _setTrack(env);\n    try {",
        "  Future<bool> playUrl(String url, [int? gen, dynamic env]) async {\n    final int g = gen ?? _gen;\n    _setTrack(env);\n    bool played = true;\n    try {", "playUrl sig")
s = rep(s, """        final bool ok = await _playWeb(url, true);
        if (!ok && g == _gen) await _playWeb(url, false);""",
        """        final bool ok = await _playWeb(url, true);
        if (!ok && g == _gen) played = await _playWeb(url, false);""", "web played")
s = rep(s, """        final AudioPlayer p = _ensure();
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
        await psub.cancel();""",
        """        final AudioPlayer p = _ensure();
        await p.stop();
        final Completer<bool> c = Completer<bool>();
        bool started = false;
        final StreamSubscription<void> sub = p.onPlayerComplete.listen((_) {
          if (!c.isCompleted) c.complete(true);
        });
        final StreamSubscription<Duration> psub = p.onPositionChanged.listen((Duration d) {
          _posKnown = d.inMicroseconds / 1e6;
          _posAt = DateTime.now();
          if (d.inMilliseconds > 0) started = true;
        });
        // JC-LAZO-JUNE-NATIVE-1013-005: a clip that never starts or never ends is abandoned, never waited on for minutes
        final double knownSecs = _trkFrames > 0 ? _trkFrames / _trkFps : 0;
        final Timer startDog = Timer(const Duration(seconds: 5), () {
          if (!started && !c.isCompleted) c.complete(false);
        });
        _t0 = DateTime.now();
        try {
          await p.play(UrlSource(url));
        } catch (e) {
          if (!c.isCompleted) c.complete(false);
          debugPrint('LAZO june play start: ' + e.toString());
        }
        played = await c.future.timeout(Duration(milliseconds: knownSecs > 0 ? ((knownSecs + 4) * 1000).round() : 90000), onTimeout: () => started);
        startDog.cancel();
        if (!played) {
          try {
            await p.stop();
          } catch (_) {}
        }
        await sub.cancel();
        await psub.cancel();""", "phone watchdog")
s = rep(s, """    } catch (e) {
      debugPrint('LAZO june play: ' + e.toString());
    }
    _trk = null;
    if (g != _gen) return;
  }""",
        """    } catch (e) {
      played = false;
      debugPrint('LAZO june play: ' + e.toString());
    }
    _trk = null;
    return played;
  }""", "playUrl tail")

# ---- stop() also silences the device voice
s = rep(s, """    try {
      _player?.stop();
    } catch (_) {}
    _trk = null;
    if (speaking) {""",
        """    try {
      _player?.stop();
    } catch (_) {}
    try {
      _tts?.stop();
    } catch (_) {}
    _trk = null;
    if (speaking) {""", "stop tts")

# ---- the brief's Listen button: if its audio cannot play, read it aloud sentence by sentence
s = rep(s, """      if (url.isNotEmpty) {
        setState(() => _mode = 'speaking');
        await _voice.playUrl(url, null, _map(j)['env']);
        if (mounted) setState(() => _mode = 'idle');
      } else {
        for (final String sent in text.split""", """      bool played = false;
      if (url.isNotEmpty) {
        setState(() => _mode = 'speaking');
        played = await _voice.playUrl(url, null, _map(j)['env']);
        if (mounted) setState(() => _mode = 'idle');
      }
      if (!played && _briefPlaying) {
        for (final String sent in text.split""", "brief fallback")

s = rep(s, "// END OF FILE - JC-LAZO-JUNE-NATIVE-1011-004", "// END OF FILE - JC-LAZO-JUNE-NATIVE-1013-005", "eof")
out = HERE / "JuneNative_v5.txt"
out.write_text(s, encoding="utf-8")
print("wrote", out.name, len(s))
