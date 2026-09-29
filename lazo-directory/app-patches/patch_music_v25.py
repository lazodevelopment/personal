"""patch_music_v25.py - JC-LAZO-MUSIC-0929-V25
COMPILE FIX. package:universal_html/js_util re-exports dart:js_util on the
web, and the Dart SDK FlutterFlow builds with no longer ships dart:js_util
(removed with the other legacy web libraries), so every jsu.* call came back
"isn't defined". The audio element still resolves (universal_html exports
dart:html on the web, which is deprecated but present), and universal_html's
MediaElement stub carries currentTime / duration / paused on phones too, so:
  - the js_util import and the Web Audio analyser (AudioContext,
    createMediaElementSource, AnalyserNode) are gone
  - position, length and paused come from the element's own properties
  - the equalizer is the beat-driven animation everywhere (_vizReal stays
    false), which is what phones always had
Same playback on web through the relay; same on phones through audioplayers.
Dependencies on this widget in FlutterFlow: audioplayers, universal_html, http.
Applies on top of Music_master.txt (v2.4.1) -> Music_master_v25.txt.
  python app-patches\\patch_music_v25.py [src] [out]
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "Music_master.txt"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "Music_master_v25.txt"
s = SRC.read_text(encoding="utf-8")
if "JC-LAZO-MUSIC-0929-V25" in s:
    raise SystemExit("already applied")


def swap(old, new, label, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"ABORT [{label}]: anchor matched {n} times, expected {count}")
    s = s.replace(old, new)
    print(f"  ok  {label}")


swap("// Build ID: JC-LAZO-MUSIC-0915-007\n",
     "// Build ID: JC-LAZO-MUSIC-0929-V25\n"
     "// (v2.5: COMPILE FIX - universal_html/js_util re-exports dart:js_util, which the current Dart SDK no longer ships, so every jsu.* call failed to compile. The Web Audio analyser is removed; position, length and paused come from the audio element's own properties (present on universal_html's phone stub too); the equalizer is the beat animation everywhere. Playback unchanged. Dependencies: audioplayers, universal_html, http. base v2.4.1)\n",
     "header")
swap("import 'package:universal_html/js_util.dart' as jsu;\n", "", "drop js_util import")
swap("""  Object? _actx; // JS AudioContext (via universal_html/js_util, web only)
  Object? _an; // JS AnalyserNode
  final Uint8List _fft = Uint8List(32);
  bool _vizReal = false;
""", """  // v2.5: no Web Audio - the analyser needed dart:js_util, which is gone
  Object? _actx; // always null now; kept so the stop/dispose paths read the same
  Object? _an; // always null now
  bool _vizReal = false; // stays false: the bars follow the beat animation
""", "fields")
swap("""    try {
      final Object? ctx = _actx;
      if (kIsWeb && ctx != null) jsu.callMethod(ctx, 'close', <Object?>[]);
      _actx = null;
    } catch (_) {}
""", """    _actx = null;
    _an = null;
""", "dispose")
swap("""  // universal_html's phone stub of the audio element has no currentTime /
  // duration / paused, so the web path reads them through js_util (these
  // only ever run behind kIsWeb).
  static double _elNum(html.AudioElement el, String prop) {
    try {
      final Object? v = jsu.getProperty(el, prop);
      return v is num ? v.toDouble() : 0;
    } catch (_) {
      return 0;
    }
  }

  static bool _elPaused(html.AudioElement el) {
    try {
      return jsu.getProperty(el, 'paused') == true;
    } catch (_) {
      return true;
    }
  }

  static void _elSet(html.AudioElement el, String prop, Object? v) {
    try {
      jsu.setProperty(el, prop, v);
    } catch (_) {}
  }

  void _resumeCtx() {
    final Object? ctx = _actx;
    if (!kIsWeb || ctx == null) return;
    try {
      jsu.callMethod(ctx, 'resume', <Object?>[]);
    } catch (_) {}
  }
""", """  // v2.5: the element's own properties. universal_html's MediaElement has
  // currentTime / duration / paused on every platform (a stub on phones),
  // and these only run behind kIsWeb anyway.
  static double _elNum(html.AudioElement el, String prop) {
    try {
      final num v = prop == 'duration' ? el.duration : el.currentTime;
      return v.isFinite ? v.toDouble() : 0;
    } catch (_) {
      return 0;
    }
  }

  static bool _elPaused(html.AudioElement el) {
    try {
      return el.paused;
    } catch (_) {
      return true;
    }
  }

  static void _elSet(html.AudioElement el, String prop, Object? v) {
    try {
      if (prop == 'currentTime' && v is num) el.currentTime = v;
    } catch (_) {}
  }

  void _resumeCtx() {}
""", "element properties")
swap("""  void _wireAnalyser(html.AudioElement a) {
    try {
      if (_actx == null) {
        Object? ctor;
        if (jsu.hasProperty(html.window, 'AudioContext')) {
          ctor = jsu.getProperty(html.window, 'AudioContext');
        } else if (jsu.hasProperty(html.window, 'webkitAudioContext')) {
          ctor = jsu.getProperty(html.window, 'webkitAudioContext');
        }
        if (ctor == null) throw StateError('no AudioContext');
        _actx = jsu.callConstructor(ctor as Function, <Object?>[]);
      }
      final Object ctx = _actx!;
      final Object src =
          jsu.callMethod(ctx, 'createMediaElementSource', <Object?>[a]);
      final Object an = jsu.callMethod(ctx, 'createAnalyser', <Object?>[]);
      jsu.setProperty(an, 'fftSize', 64);
      jsu.setProperty(an, 'smoothingTimeConstant', 0.78);
      jsu.callMethod(src, 'connect', <Object?>[an]);
      jsu.callMethod(
          an, 'connect', <Object?>[jsu.getProperty(ctx, 'destination')]);
      _an = an;
      _vizReal = true;
      _silentTicks = 0;
    } catch (e) {
      debugPrint('LAZO music analyser: ' + e.toString());
      _vizReal = false;
      _an = null;
    }
  }
""", """  // v2.5: the real spectrum needed dart:js_util; the bars follow the beat
  void _wireAnalyser(html.AudioElement a) {
    _vizReal = false;
    _an = null;
    _silentTicks = 0;
  }
""", "analyser removed")
swap("""    final Object? an = _an;
    if (_vizReal && an != null) {
      try {
        // On dart2js a Uint8List is a JS Uint8Array: filled in place.
        jsu.callMethod(an, 'getByteFrequencyData', <Object?>[_fft]);
        final Uint8List d = _fft;
        int sum = 0;
        for (int i = 0; i < d.length; i++) {
          sum += d[i];
        }
        if (playing && sum == 0) {
          _silentTicks++;
          if (_silentTicks > 40)
            _vizReal = false; // tainted or muted: fall back
        } else {
          _silentTicks = 0;
        }
        if (_vizReal) {
          for (int i = 0; i < _bars.length; i++) {
            final int bin = 1 + (i * (d.length - 2) ~/ _bars.length);
            final double v = d[bin] / 255.0;
            _bars[i] = math.max(0.04, _bars[i] * 0.55 + v * 0.45);
          }
        }
      } catch (_) {
        _vizReal = false;
      }
    }
    if (!_vizReal) {
""", """    if (!_vizReal) {
""", "tick without analyser")

OUT.write_text(s, encoding="utf-8", newline="\n")
left = [i for i, l in enumerate(s.splitlines(), 1) if "jsu." in l or "_fft" in l]
print("leftover js_util / _fft references:", left)
print(f"wrote {OUT.name} ({len(s):,} chars)")
