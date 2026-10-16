r"""patch_june_native_v10.py - JuneNative v9 -> v10 (JC-LAZO-JUNE-NATIVE-1016-010)

On the web, June's "read my day" line could stay silent and then never try again that day:
1. SILENT AUDIO. Every clip went through a Web Audio analyser (for the core's spectrum). When the browser's
   AudioContext was not running yet, the clip still downloaded and "played" into a suspended context, so
   nothing came out. Now a clip only goes through the analyser when the context is already running;
   otherwise it plays straight to the speakers (the core falls back to the clip's level track).
2. BLOCKED PLAY WAS NOT NOTICED. When the browser refused to play (no click on the page yet), June waited
   up to six minutes and then counted the clip as played. Now a refused play is noticed at once.
3. MARKED READ TOO EARLY. The dashboard line was stored as "read today" before June spoke, so one silent
   attempt used up the day. Now it is stored only once she actually played it; a line the browser held
   back is retried on the next click anywhere on the page (up to three times).
Browsers still need one click or tap on a freshly loaded page before any sound; on phones she starts at once.

    python app-patches\patch_june_native_v10.py
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
s = (HERE / "JuneNative_v9.txt").read_text(encoding="utf-8")
OUT = HERE / "JuneNative_v10.txt"


def rep(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"anchor found {n}x (want {count}): {old[:80]!r}")
    s = s.replace(old, new)


rep("// Build ID: JC-LAZO-JUNE-NATIVE-1016-009 (009:",
    "// Build ID: JC-LAZO-JUNE-NATIVE-1016-010 (010: the web never plays a clip into a suspended audio context; a play the "
    "browser refuses is noticed and retried on the next click; the dashboard line counts as read only once it actually "
    "played; base 009) (009:")
rep("// END OF FILE - JC-LAZO-JUNE-NATIVE-1016-009", "// END OF FILE - JC-LAZO-JUNE-NATIVE-1016-010")

# ---- 1. the analyser only takes a clip when the audio context is already running
rep("""    var c=ctx(); if(!c) return;
    try{
      var n=S.nodes.get(el);""", """    var c=ctx(); if(!c) return;
    // v010: a suspended context would swallow the sound; play straight to the speakers this time
    if(c.state!=='running'){ S.an=null; return; }
    try{
      var n=S.nodes.get(el);""")

# ---- 2. the voice: a refused play is noticed, and a caller can wait for one line to finish
rep("""  final List<String> _queue = <String>[];
""", """  final List<String> _queue = <String>[];
  final List<Completer<bool>?> _doneQ = <Completer<bool>?>[]; // v010: one per queued line, completes true once it played
  bool blocked = false; // v010: the browser refused the last play (no click on the page yet)
""")

rep("""  Future<void> _speakDevice(String text, int gen) async {
    if (kIsWeb || gen != _gen) return;
    try {
      _t0 = DateTime.now();
      await _ensureTts().speak(text).timeout(const Duration(minutes: 2), onTimeout: () => 1);
    } catch (e) {
      debugPrint('LAZO june device voice: ' + e.toString());
    }
  }""", """  Future<bool> _speakDevice(String text, int gen) async {
    if (kIsWeb || gen != _gen) return false;
    try {
      _t0 = DateTime.now();
      await _ensureTts().speak(text).timeout(const Duration(minutes: 2), onTimeout: () => 1);
      return true;
    } catch (e) {
      debugPrint('LAZO june device voice: ' + e.toString());
      return false;
    }
  }""")

rep("""    _queue.add(t);
    if (!speaking) _pump();
  }
""", """    _queue.add(t);
    _doneQ.add(null);
    if (!speaking) _pump();
  }

  /// v010: like say, but completes true once this line actually played (false if it was stopped or refused)
  Future<bool> sayAndWait(String text) {
    final String t = text.trim();
    if (!enabled || t.isEmpty) return Future<bool>.value(false);
    final Completer<bool> c = Completer<bool>();
    _queue.add(t);
    _doneQ.add(c);
    if (!speaking) _pump();
    return c.future;
  }
""")

rep("""      final String t = _queue.removeAt(0);
      String url = '';""", """      final String t = _queue.removeAt(0);
      final Completer<bool>? done = _doneQ.isNotEmpty ? _doneQ.removeAt(0) : null;
      String url = '';""")

rep("""      if (gen != _gen) break;
      bool ok = false;
      if (url.isNotEmpty) ok = await playUrl(url, gen, env);
      if (!ok && gen == _gen) await _speakDevice(t, gen);
    }""", """      if (gen != _gen) {
        if (done != null && !done.isCompleted) done.complete(false);
        break;
      }
      bool ok = false;
      if (url.isNotEmpty) ok = await playUrl(url, gen, env);
      if (!ok && gen == _gen) ok = await _speakDevice(t, gen);
      if (done != null && !done.isCompleted) done.complete(ok && gen == _gen);
    }""")

rep("""    _t0 = DateTime.now();
    await a.play().catchError((Object _) {});
    final bool ok = await c.future.timeout(const Duration(minutes: 6), onTimeout: () => true);""",
    """    _t0 = DateTime.now();
    // v010: a refused play (no click on the page yet) used to wait six minutes and then count as played
    bool refused = false;
    await a.play().catchError((Object _) {
      refused = true;
    });
    blocked = refused;
    if (refused && !c.isCompleted) c.complete(false);
    final bool ok = await c.future.timeout(const Duration(minutes: 6), onTimeout: () => true);""")

rep("""  void stop() {
    _gen++;
    _queue.clear();
    try {
      _el?.pause();""", """  void stop() {
    _gen++;
    _queue.clear();
    for (final Completer<bool>? d in _doneQ) {
      if (d != null && !d.isCompleted) d.complete(false);
    }
    _doneQ.clear();
    try {
      _el?.pause();""")

# ---- 3. the dashboard line counts as read only once it played; a held-back line waits for the next click
rep("""  String _heroSaid = '';
""", """  String _heroSaid = '';
  String _heroTrying = ''; // v010: the line being attempted, so it is not started twice
""")

rep("""    final String key = _localDay() + '|' + line;
    if (_heroSaid == key) return;
    _heroSaid = key;
    SharedPreferences.getInstance().then((SharedPreferences p) => p.setString('juneHeroSaid', key));
    _heroWait?.cancel();
    void go() {
      if (!mounted || !_heroVoice || !_voice.enabled || _typedFor != line || JuneSpeech.hold) return;
      _voice.say(line);
    }""", """    final String key = _localDay() + '|' + line;
    if (_heroSaid == key || _heroTrying == key) return;
    _heroTrying = key;
    _heroWait?.cancel();
    int tries = 0;
    void go() {
      if (!mounted || !_heroVoice || !_voice.enabled || _typedFor != line || JuneSpeech.hold) {
        _heroTrying = '';
        return;
      }
      _voice.sayAndWait(line).then((bool ok) {
        if (!mounted) return;
        if (ok) {
          // v010: read today only once she actually played it
          _heroSaid = key;
          _heroTrying = '';
          SharedPreferences.getInstance().then((SharedPreferences p) => p.setString('juneHeroSaid', key));
        } else if (kIsWeb && _voice.blocked && ++tries < 4) {
          _juneNextTap(go); // the browser held the sound back until a click: try again on the next one
        } else {
          _heroTrying = '';
        }
      });
    }""")

# the next-click helper, next to the first-tap check
rep("""// ---------------------------------------------------------------- v008: the first tap (web sound needs one)
bool juneCanSpeak() {""", """// ---------------------------------------------------------------- v010: run once on the next click or tap (web)
void _juneNextTap(void Function() f) {
  if (!kIsWeb) return;
  try {
    late html.EventListener handler;
    handler = (html.Event _) {
      html.document.removeEventListener('pointerdown', handler);
      f();
    };
    html.document.addEventListener('pointerdown', handler);
  } catch (_) {}
}

// ---------------------------------------------------------------- v008: the first tap (web sound needs one)
bool juneCanSpeak() {""")

OUT.write_text(s, encoding="utf-8", newline="\n")
print(f"wrote {OUT.name} ({len(s):,} chars)")
