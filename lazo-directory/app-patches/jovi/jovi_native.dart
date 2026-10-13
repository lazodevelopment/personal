// Automatic FlutterFlow imports
import '/backend/backend.dart';
import '/flutter_flow/flutter_flow_theme.dart';
import '/flutter_flow/flutter_flow_util.dart';
import '/custom_code/widgets/index.dart'; // Imports other custom widgets
import '/custom_code/actions/index.dart'; // Imports custom actions
import '/flutter_flow/custom_functions.dart'; // Imports custom functions
import 'package:flutter/material.dart';
// Begin custom widget code
// DO NOT REMOVE OR MODIFY THE CODE ABOVE!

// jovi_native.dart
// Build ID: JC-JOVI-NATIVE-1013-005 (005: Plan tile leads the glance row; relaxation radio - spa, calm classical, sleep, chill; base 004) (004: layout 'hero' for Home - the core on the gradient, her one line typed in, one pill, one bar, glance tiles, chat in a sheet; base 003) (003: radio + focus, own-medication dose logging, the morning brief on a schedule; base 002) (002: the deck drops its own greeting, Home has one; base 001)
//
// JOVI, NATIVE. The member's own assistant inside the Jovi Health app, built on
// the June widget from Lazo (JuneNative v4) and tailored for care: the living
// core, a streaming chat with confirm-first actions, voice in (the device's
// speech recognition) and voice out (ElevenLabs through the Jovi hub, with the
// device's own voice as the fallback), today's brief read aloud, today's one
// thing with a streak, appointments, medications and refills, claims, billing,
// pets and their doses, vitals, vaccines, air and weather, reminders that reach
// the phone as a push, and memory.
//
// Her brain is the jovi-hub worker (jovi-admin/jovi-hub): this widget is a
// client of its /api/*, signed with the member's Firebase ID token. The worker
// reads and writes Firestore AS THE MEMBER, so the app's security rules decide
// what Jovi can see and do. Phones only (the app ships mobile only): no web
// branches, no universal_html.
//
// Widget name (FlutterFlow): JoviNative
// Parameters: layout 'full' (its own page) | 'hero' (the top of Home: Jovi's greeting
//             and line, one pill, one bar, glance tiles; the host draws the gradient) |
//             'deck' (the older dashboard band; kept for wide screens).
// Dependencies (FlutterFlow -> Settings -> Custom Code -> Dependencies):
//   just_audio (already in the project: the Meditation widget uses it)
//   flutter_tts (already in the project)
//   speech_to_text ^7.0.0  (NEW - voice input; without it, remove the mic
//                          button and the _Ears class below)
// Permissions (FlutterFlow -> Settings -> Permissions): Microphone and Speech
// Recognition, with a line like "Jovi listens when you tap the microphone."
// Page: create a page named `jovi` that hosts JoviNative(layout: 'full');
// pushes from the worker open that page by name.

import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'dart:math' as math;
import 'package:flutter/services.dart';
import 'package:flutter/scheduler.dart' show Ticker;
import 'package:http/http.dart' as httpc;
import 'package:firebase_auth/firebase_auth.dart';
import 'package:just_audio/just_audio.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:url_launcher/url_launcher.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:go_router/go_router.dart';

class JoviNative extends StatefulWidget {
  const JoviNative({
    super.key,
    this.width,
    this.height,
    this.layout = 'full',
  });
  final double? width;
  final double? height;
  final String layout;

  @override
  State<JoviNative> createState() => _JoviNativeState();
}

// ---------------------------------------------------------------- palette (the Jovi brand system, home.dart)
const Color _navyDeep = Color(0xFF0F1A2E);
const Color _navy = Color(0xFF1A2744);
const Color _coral = Color(0xFFFF6B4A);
const Color _coralSoft = Color(0xFFFF8F73);
const Color _mint = Color(0xFF00D4AA);
const Color _gold = Color(0xFFFFD166);
const Color _ivory = Color(0xFFFFF8F5);
const Color _muted = Color(0xFF9AA6BF);
const Color _red = Color(0xFFE53935);
const String _kHub = 'https://jovi-hub.floral-credit-e4f0.workers.dev';

String _s(dynamic v) => v == null ? '' : v.toString();
num _n(dynamic v) => v is num ? v : (num.tryParse(_s(v)) ?? 0);
String _money(dynamic v) {
  final num x = _n(v);
  final String whole = x.round().toString().replaceAllMapped(RegExp(r'(\d)(?=(\d{3})+$)'), (Match m) => '${m[1]},');
  return '\$' + whole;
}
List<Map<String, dynamic>> _list(dynamic v) => v is List ? v.whereType<Map>().map((Map e) => Map<String, dynamic>.from(e)).toList() : <Map<String, dynamic>>[];
List<String> _strs(dynamic v) => v is List ? v.map((dynamic e) => _s(e)).where((String e) => e.isNotEmpty).toList() : <String>[];
Map<String, dynamic> _map(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : <String, dynamic>{};
String _day(String iso) {
  try {
    final DateTime d = DateTime.parse(iso.length == 10 ? iso + 'T12:00:00' : iso).toLocal();
    const List<String> w = <String>['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const List<String> m = <String>['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return '${w[d.weekday - 1]}, ${m[d.month - 1]} ${d.day}';
  } catch (_) {
    return iso;
  }
}
String _when(String iso) {
  try {
    final DateTime d = DateTime.parse(iso).toLocal();
    final int h = d.hour % 12 == 0 ? 12 : d.hour % 12;
    return '${_day(iso)} · $h:${d.minute.toString().padLeft(2, '0')} ${d.hour < 12 ? 'AM' : 'PM'}';
  } catch (_) {
    return iso;
  }
}
String _clock(String iso) {
  try {
    final DateTime d = DateTime.parse(iso).toLocal();
    final int h = d.hour % 12 == 0 ? 12 : d.hour % 12;
    return '$h:${d.minute.toString().padLeft(2, '0')} ${d.hour < 12 ? 'AM' : 'PM'}';
  } catch (_) {
    return '';
  }
}
String _wmo(dynamic code) {
  const Map<int, String> t = <int, String>{0: 'Clear', 1: 'Mostly clear', 2: 'Partly cloudy', 3: 'Overcast', 45: 'Fog', 48: 'Fog', 51: 'Drizzle', 53: 'Drizzle', 55: 'Drizzle', 61: 'Rain', 63: 'Rain', 65: 'Heavy rain', 71: 'Snow', 73: 'Snow', 75: 'Snow', 80: 'Showers', 81: 'Showers', 82: 'Heavy showers', 95: 'Thunderstorms', 96: 'Thunderstorms', 99: 'Thunderstorms'};
  return t[_n(code).toInt()] ?? '';
}
IconData _wmoIcon(dynamic code) {
  final int c = _n(code).toInt();
  if (c == 0 || c == 1) return Icons.wb_sunny_rounded;
  if (c == 2) return Icons.wb_cloudy_rounded;
  if (c == 3 || c == 45 || c == 48) return Icons.cloud_rounded;
  if (c >= 95) return Icons.thunderstorm_rounded;
  if (c >= 71 && c <= 75) return Icons.ac_unit_rounded;
  return Icons.water_drop_rounded;
}
String _title(String s) => s.isEmpty ? s : s[0].toUpperCase() + s.substring(1).replaceAll('_', ' ');

// ---------------------------------------------------------------- the API: the Jovi hub, signed in as this member
class _Api {
  Future<Map<String, String>> _headers() async {
    final User? u = FirebaseAuth.instance.currentUser;
    final String t = u == null ? '' : (await u.getIdToken() ?? '');
    return <String, String>{'authorization': 'Bearer $t', 'content-type': 'application/json'};
  }

  Future<Map<String, dynamic>> get(String path) async {
    final httpc.Response r = await httpc.get(Uri.parse(_kHub + path), headers: await _headers()).timeout(const Duration(seconds: 30));
    final dynamic j = jsonDecode(r.body.isEmpty ? '{}' : r.body);
    if (r.statusCode >= 400) throw Exception(_s(j is Map ? (j['message'] ?? j['error']) : r.statusCode));
    return j is Map ? Map<String, dynamic>.from(j) : <String, dynamic>{'data': j};
  }

  Future<dynamic> post(String path, Map<String, dynamic> body) async {
    final httpc.Response r = await httpc.post(Uri.parse(_kHub + path), headers: await _headers(), body: jsonEncode(body)).timeout(const Duration(seconds: 60));
    final dynamic j = jsonDecode(r.body.isEmpty ? '{}' : r.body);
    if (r.statusCode >= 400) throw Exception(_s(j is Map ? (j['message'] ?? j['error']) : r.statusCode) + ' (${r.statusCode})');
    return j;
  }

  // the chat streams server-sent events: delta {text}, done {reply, actions, messages}, error {message}
  Future<void> chat(String text, List<Map<String, dynamic>> history, {required void Function(String) onDelta, required void Function(Map<String, dynamic>) onDone, required void Function(String) onError}) async {
    final httpc.Client client = httpc.Client();
    try {
      final httpc.Request req = httpc.Request('POST', Uri.parse('$_kHub/api/chat'));
      req.headers.addAll(await _headers());
      req.body = jsonEncode(<String, dynamic>{'text': text, 'messages': history});
      final httpc.StreamedResponse resp = await client.send(req).timeout(const Duration(seconds: 90));
      if (resp.statusCode >= 400) {
        onError('Jovi is unavailable (${resp.statusCode}).');
        return;
      }
      String buf = '';
      bool done = false;
      await for (final String chunk in resp.stream.transform(utf8.decoder)) {
        buf += chunk;
        int idx;
        while ((idx = buf.indexOf('\n\n')) >= 0) {
          final String frame = buf.substring(0, idx);
          buf = buf.substring(idx + 2);
          final RegExpMatch? ev = RegExp(r'^event: (.*)$', multiLine: true).firstMatch(frame);
          final RegExpMatch? da = RegExp(r'^data: (.*)$', multiLine: true).firstMatch(frame);
          if (ev == null || da == null) continue;
          dynamic d;
          try {
            d = jsonDecode(da.group(1)!);
          } catch (_) {
            continue;
          }
          final String kind = ev.group(1)!.trim();
          if (kind == 'delta') {
            onDelta(_s(_map(d)['text']));
          } else if (kind == 'done') {
            done = true;
            onDone(_map(d));
          } else if (kind == 'error') {
            onError(_s(_map(d)['message']));
          }
        }
      }
      if (!done) onDone(<String, dynamic>{});
    } catch (e) {
      onError(e.toString());
    } finally {
      client.close();
    }
  }
}

// ---------------------------------------------------------------- the voice out: ElevenLabs through the hub (one clip per sentence), the device voice when the hub has no key
class _Voice {
  _Voice(this.api, this.onState);
  final _Api api;
  final void Function(bool speaking) onState;
  final List<String> _queue = <String>[];
  bool speaking = false;
  bool enabled = true;
  bool hubVoice = true; // false after the hub says tts is not configured; the device voice takes over
  int _gen = 0;
  AudioPlayer? _player;
  FlutterTts? _tts;

  // the level track that came with the clip - frames x bands, bytes 0..255
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

  AudioPlayer _ensure() => _player ??= AudioPlayer();

  FlutterTts _ensureTts() {
    if (_tts != null) return _tts!;
    final FlutterTts t = FlutterTts();
    try {
      t.setLanguage('en-US');
      t.setSpeechRate(0.5);
      t.setPitch(1.0);
      t.awaitSpeakCompletion(true);
    } catch (_) {}
    _tts = t;
    return t;
  }

  void say(String text) {
    final String t = text.trim();
    if (!enabled || t.isEmpty) return;
    _queue.add(t);
    if (!speaking) _pump();
  }

  Future<void> _pump() async {
    speaking = true;
    onState(true);
    final int gen = _gen;
    while (_queue.isNotEmpty && gen == _gen) {
      final String t = _queue.removeAt(0);
      String url = '';
      dynamic env;
      if (hubVoice) {
        try {
          final dynamic j = await api.post('/api/clip', <String, dynamic>{'text': t});
          url = _s(_map(j)['url']);
          env = _map(j)['env'];
        } catch (e) {
          final String m = e.toString();
          if (m.contains('(501)') || m.contains('not configured')) hubVoice = false;
          debugPrint('JOVI clip: ' + m);
        }
      }
      if (gen != _gen) break;
      if (url.isNotEmpty) {
        await playUrl(url, gen, env);
      } else {
        await _speakDevice(t, gen);
      }
    }
    if (gen == _gen) {
      speaking = false;
      onState(false);
    }
  }

  Future<void> _speakDevice(String text, int gen) async {
    try {
      final FlutterTts t = _ensureTts();
      _t0 = DateTime.now();
      await t.speak(text).timeout(const Duration(minutes: 2), onTimeout: () => 1);
    } catch (e) {
      debugPrint('JOVI tts: ' + e.toString());
    }
    if (gen != _gen) return;
  }

  // plays one URL to the end
  Future<void> playUrl(String url, [int? gen, dynamic env]) async {
    final int g = gen ?? _gen;
    _setTrack(env);
    StreamSubscription<Duration>? psub;
    try {
      final AudioPlayer p = _ensure();
      await p.stop();
      psub = p.positionStream.listen((Duration d) {
        _posKnown = d.inMicroseconds / 1e6;
        _posAt = DateTime.now();
      });
      await p.setUrl(url);
      _t0 = DateTime.now();
      final Future<void> ended = p.processingStateStream.firstWhere((ProcessingState s) => s == ProcessingState.completed || s == ProcessingState.idle).then((_) {});
      await p.play();
      await ended.timeout(const Duration(minutes: 6), onTimeout: () {});
    } catch (e) {
      debugPrint('JOVI play: ' + e.toString());
    }
    await psub?.cancel();
    _trk = null;
    if (g != _gen) return;
  }

  void stop() {
    _gen++;
    _queue.clear();
    try {
      _player?.stop();
    } catch (_) {}
    try {
      _tts?.stop();
    } catch (_) {}
    _trk = null;
    if (speaking) {
      speaking = false;
      onState(false);
    }
  }

  void dispose() {
    stop();
    try {
      _player?.dispose();
    } catch (_) {}
  }
}

// ---------------------------------------------------------------- the voice in: the device's speech recognition
class _Ears {
  _Ears({required this.onText, required this.onState});
  final void Function(String text, bool isFinal) onText;
  final void Function(bool listening) onState;
  final stt.SpeechToText _stt = stt.SpeechToText();
  bool ready = false;
  bool listening = false;

  Future<bool> init() async {
    try {
      ready = await _stt.initialize(
        onStatus: (String s) {
          if (s == 'done' || s == 'notListening') {
            if (listening) {
              listening = false;
              onState(false);
            }
          }
        },
        onError: (dynamic e) {
          if (listening) {
            listening = false;
            onState(false);
          }
        },
      );
    } catch (e) {
      ready = false;
    }
    return ready;
  }

  Future<void> start() async {
    if (!ready && !(await init())) return;
    listening = true;
    onState(true);
    try {
      await _stt.listen(
        onResult: (dynamic r) {
          try {
            onText(_s(r.recognizedWords), r.finalResult == true);
          } catch (_) {}
        },
        listenFor: const Duration(seconds: 20),
        pauseFor: const Duration(seconds: 3),
        localeId: 'en_US',
      );
    } catch (e) {
      listening = false;
      onState(false);
    }
  }

  Future<void> stop() async {
    try {
      await _stt.stop();
    } catch (_) {}
    if (listening) {
      listening = false;
      onState(false);
    }
  }
}

// ---------------------------------------------------------------- the core: a circular spectrum analyser
class _CorePainter extends CustomPainter {
  _CorePainter({required this.levels, required this.caps, required this.swell, required this.bass, required this.rot, required this.tint, required this.live});
  final List<double> levels;
  final List<double> caps;
  final double swell;
  final double bass;
  final double rot;
  final Color tint;
  final bool live;

  @override
  void paint(Canvas canvas, Size size) {
    final double w = size.width;
    final Offset c = Offset(w / 2, size.height / 2);
    final int nb = levels.length;
    final double r0 = w * 0.21 * (1 + bass * 0.05);
    final double len = w * 0.25;
    final double gr = r0 * (1.9 + swell * 0.5);
    canvas.drawCircle(c, gr, Paint()..shader = RadialGradient(colors: <Color>[tint.withOpacity(live ? 0.28 : 0.16), tint.withOpacity(0.06), tint.withOpacity(0)], stops: const <double>[0, .5, 1]).createShader(Rect.fromCircle(center: c, radius: gr)));
    final double bw = math.max(1.5, (math.pi * r0) / nb * 0.62);
    final Paint bar = Paint()
      ..color = tint.withOpacity(live ? 0.92 : 0.5)
      ..strokeWidth = bw
      ..strokeCap = StrokeCap.butt;
    final Paint cap = Paint()
      ..color = Colors.white.withOpacity(live ? 0.85 : 0.35)
      ..strokeWidth = math.max(1, bw * 0.9);
    for (int s = -1; s <= 1; s += 2) {
      for (int b = 0; b < nb; b++) {
        final double a = math.pi / 2 + s * ((b + 0.5) / nb) * math.pi;
        final double l = r0 + math.max(1, levels[b] * len);
        final double cs = math.cos(a), sn = math.sin(a);
        canvas.drawLine(Offset(c.dx + cs * (r0 + 1), c.dy + sn * (r0 + 1)), Offset(c.dx + cs * l, c.dy + sn * l), bar);
        if (caps[b] > 0.06) {
          final double cl = r0 + caps[b] * len + bw * 1.2;
          canvas.drawLine(Offset(c.dx + cs * cl, c.dy + sn * cl), Offset(c.dx + cs * (cl + bw * 0.9), c.dy + sn * (cl + bw * 0.9)), cap);
        }
      }
    }
    canvas.drawCircle(c, r0, Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.4
      ..color = tint.withOpacity(live ? 0.75 : 0.45));
    final double orbit = r0 + len + bw * 2.2;
    final Paint op = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1
      ..color = tint.withOpacity(0.25 + swell * 0.5);
    const List<double> dash = <double>[0.5, 0.22, 0.12, 0.3];
    double ang = rot;
    for (int rep = 0; rep < 2; rep++) {
      for (int i = 0; i < 4; i++) {
        final double sweep = dash[i] * r0 / orbit;
        if (i % 2 == 0) canvas.drawArc(Rect.fromCircle(center: c, radius: orbit), ang, sweep, false, op);
        ang += sweep;
      }
    }
    final double nr = r0 * (0.34 + bass * 0.3) * (live ? 1 : 0.85);
    canvas.drawCircle(c, nr, Paint()..shader = RadialGradient(colors: <Color>[Colors.white, tint.withOpacity(0.9), tint.withOpacity(0.25), tint.withOpacity(0)], stops: const <double>[0, .25, .55, 1]).createShader(Rect.fromCircle(center: c, radius: nr)));
  }

  @override
  bool shouldRepaint(covariant _CorePainter old) => true;
}

// ---------------------------------------------------------------- the widget
class _JoviNativeState extends State<JoviNative> with SingleTickerProviderStateMixin {
  final _Api _api = _Api();
  late final _Voice _voice = _Voice(_api, (bool s) {
    if (!mounted) return;
    setState(() => _mode = s ? 'speaking' : (_thinking ? 'thinking' : 'idle'));
    _radioDuck(s);
  });
  late final _Ears _ears = _Ears(
    onText: _onHeard,
    onState: (bool l) {
      if (!mounted) return;
      setState(() {
        _listening = l;
        _mode = l ? 'listening' : (_voice.speaking ? 'speaking' : 'idle');
      });
    },
  );
  late final Ticker _ticker;

  Map<String, dynamic> _snap = <String, dynamic>{};
  String _err = '';
  bool _loading = true;
  bool _thinking = false;
  bool _listening = false;
  bool _micAvailable = false;
  String _mode = 'idle';
  String _heard = '';
  final List<Map<String, dynamic>> _chat = <Map<String, dynamic>>[]; // {role, text, item?, route?}
  List<Map<String, dynamic>> _hist = <Map<String, dynamic>>[];
  final TextEditingController _q = TextEditingController();
  final ScrollController _chatScroll = ScrollController();
  final TextEditingController _remText = TextEditingController();
  DateTime? _remWhen;
  bool _briefBusy = false;
  bool _briefPlaying = false;
  bool _doneBusy = false;
  bool _chipsAll = false;
  Timer? _refresh;
  // JC-JOVI-NATIVE-1013-003: radio, focus, alerts
  // for rest and recovery first: "play some music" starts the spa station; the keys are what the member may say
  static const List<List<String>> _radio = <List<String>>[
    <String>['Spa · Drone Zone', 'https://ice1.somafm.com/dronezone-128-mp3', 'spa,ambient,drone,meditat,relax,calmmusic,quiet'],
    <String>['Calm Classical', 'https://media-ssl.musicradio.com/ClassicFMCalm', 'calm,classical,classic,piano'],
    <String>['Sleep · Ambient Sleeping Pill', 'https://radio.stereoscenic.com/asp-s', 'sleep,bed,night,rest'],
    <String>['Chill · Groove Salad', 'https://ice1.somafm.com/groovesalad-128-mp3', 'chill,groove,lounge,downtempo'],
    <String>['Paradise Mellow', 'https://stream.radioparadise.com/mellow-128', 'mellow,acoustic'],
    <String>['Smooth Chill', 'https://media-ssl.musicradio.com/SmoothChill', 'smooth,jazz'],
  ];
  AudioPlayer? _radioPlayer;
  String _radioName = '';
  int _radioIdx = -1;
  double _radioVol = 0.7;
  DateTime? _focusEnd;
  Timer? _focusT;
  bool _alertsBusy = false;
  // JC-JOVI-NATIVE-1013-004: the hero
  int _typed = 0;
  String _typedFor = '';
  Timer? _typeT;
  bool _entered = false;
  bool _onScreen = true;
  int _visTick = 0;
  // the core's state
  static const int _nb = 40;
  final List<double> _lvl = List<double>.filled(_nb, 0);
  final List<double> _cap = List<double>.filled(_nb, 0);
  final List<double> _capT = List<double>.filled(_nb, 0);
  double _swell = 0, _bass = 0, _rot = 0, _phase = 0;
  Duration _last = Duration.zero;
  Color _tint = _coral;

  @override
  void initState() {
    super.initState();
    _ticker = createTicker(_tick)..start();
    _load(first: true);
    _refresh = Timer.periodic(const Duration(minutes: 3), (_) => _load());
    _ears.init().then((bool ok) {
      if (mounted) setState(() => _micAvailable = ok);
    });
    SharedPreferences.getInstance().then((SharedPreferences p) {
      final bool? v = p.getBool('joviSpeak');
      if (v != null && mounted) setState(() => _voice.enabled = v);
    });
  }

  @override
  void dispose() {
    _ticker.dispose();
    _refresh?.cancel();
    _focusT?.cancel();
    _typeT?.cancel();
    try {
      _radioPlayer?.dispose();
    } catch (_) {}
    _voice.dispose();
    _ears.stop();
    _q.dispose();
    _chatScroll.dispose();
    _remText.dispose();
    super.dispose();
  }

  // ---- the core animation: the clip's level track when she speaks, synthetic motion otherwise, real meter ballistics
  void _tick(Duration now) {
    final double dt = _last == Duration.zero ? 0.016 : math.min(0.1, (now - _last).inMicroseconds / 1e6);
    _last = now;
    _phase += dt;
    if (widget.layout == 'hero' && ++_visTick % 20 == 0) _checkOnScreen();
    if (!_onScreen && !_voice.speaking) return;
    final String m = _mode;
    double target = 0;
    if (m == 'thinking') target = 0.3 + 0.2 * math.sin(_phase * 6);
    else if (m == 'listening') target = 0.12 + 0.05 * math.sin(_phase * 3);
    else if (m == 'speaking') target = 0.25 + 0.55 * math.max(0, math.sin(_phase * 11) * 0.6 + math.sin(_phase * 4.3) * 0.4 + 0.2);
    List<double>? live;
    if (m == 'speaking') live = _voice.frame(_nb);
    if (live != null) {
      double sum = 0;
      for (final double v in live) sum += v;
      target = math.min(1, (sum / _nb) * 1.7 + 0.06);
    }
    final bool radioOn = _radioName.isNotEmpty;
    if (live == null && radioOn && m == 'idle') {
      // music motion: a beat and a slow swell (streams do not expose their audio on phones)
      final double beat = math.max(0, math.sin(_phase * 2 * math.pi * 1.9));
      target = 0.22 + 0.18 * math.pow(beat, 3) + 0.08 * math.sin(_phase * 0.6);
    }
    final double atk = 1 - math.exp(-dt * 60), rel = (live != null ? 7.5 : 4.2) * dt, capFall = 2.2 * dt;
    for (int b = 0; b < _nb; b++) {
      double shape;
      if (m == 'speaking') shape = math.exp(-math.pow((b - _nb * 0.3) / (_nb * 0.28), 2)) * (0.6 + 0.4 * math.sin(_phase * 9 + b * 0.7).abs());
      else if (m == 'thinking') shape = 0.5 + 0.5 * math.sin(_phase * 5 - b * 0.35);
      else if (radioOn) shape = (0.55 + 0.45 * math.sin(_phase * 3.1 + b * 0.9)) * (0.7 + 0.3 * math.exp(-math.pow((b - _nb * 0.2) / (_nb * 0.35), 2)));
      else shape = 0.4 + 0.3 * math.sin(_phase * 2 + b);
      final double v = live != null ? live[b] : (m == 'idle' && !radioOn ? 0.05 + 0.04 * math.sin(_phase * 1.1 + b * 0.45) * math.sin(_phase * 0.7 + b * 0.2) : target * shape);
      if (v > _lvl[b]) _lvl[b] += (v - _lvl[b]) * atk; else _lvl[b] = math.max(v, _lvl[b] - rel);
      if (_lvl[b] >= _cap[b]) {
        _cap[b] = _lvl[b];
        _capT[b] = 0.25;
      } else {
        _capT[b] -= dt;
        if (_capT[b] <= 0) _cap[b] = math.max(_lvl[b], _cap[b] - capFall);
      }
    }
    _swell += (target - _swell) * 0.15;
    _bass += ((live != null ? (live[0] + live[1] + live[2] + live[3]) / 4 : target * 0.5) - _bass) * (live != null ? 0.3 : 0.1);
    _rot += dt * (m == 'thinking' ? 1.4 : m == 'idle' ? (radioOn ? 0.3 : 0.12) : 0.25 + _swell * 0.6);
    final Color want = m == 'listening' ? _mint : m == 'thinking' ? _gold : m == 'speaking' ? const Color(0xFFFFD9CC) : (radioOn ? const Color(0xFF7FE0C8) : _coral);
    _tint = Color.lerp(_tint, want, 0.08) ?? want;
    if (mounted) setState(() {});
  }

  void _checkOnScreen() {
    try {
      final RenderObject? ro = context.findRenderObject();
      if (ro is! RenderBox || !ro.hasSize || !ro.attached) return;
      final Offset top = ro.localToGlobal(Offset.zero);
      final double h = MediaQuery.of(context).size.height;
      final bool on = top.dy + ro.size.height > -40 && top.dy < h + 40;
      if (on != _onScreen) setState(() => _onScreen = on);
    } catch (_) {}
  }

  // the brief's opening sentence typed in while the core reacts (Reduce Motion shows it whole)
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
  Future<void> _load({bool first = false}) async {
    try {
      final Map<String, dynamic> s = await _api.get('/api/state');
      if (!mounted) return;
      setState(() {
        _snap = s;
        _loading = false;
        _err = '';
      });
      if (first) {
        if (_map(s['brief'])['text'] == null) _makeBrief(false);
        final List<Map<String, dynamic>> due = _list(s['due']);
        if (due.isNotEmpty) {
          final String line = due.length == 1 ? 'You asked me to remind you: ${_s(due[0]['text'])}.' : 'You have ${due.length} reminders due. ' + due.take(3).map((Map<String, dynamic> r) => _s(r['text'])).join('; ') + '.';
          _addMsg('ai', line);
          _voice.say(line);
        }
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _err = e.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  Future<void> _makeBrief(bool force) async {
    setState(() => _briefBusy = true);
    try {
      final dynamic b = await _api.post('/api/brief', <String, dynamic>{'force': force});
      if (!mounted) return;
      setState(() => _snap['brief'] = _map(b));
    } catch (e) {
      debugPrint('JOVI brief: ' + e.toString());
    }
    if (mounted) setState(() => _briefBusy = false);
  }

  Future<void> _listenBrief() async {
    if (_briefPlaying) {
      _voice.stop();
      setState(() => _briefPlaying = false);
      return;
    }
    final String text = _s(_map(_snap['brief'])['text']);
    if (text.isEmpty) return;
    setState(() => _briefPlaying = true);
    try {
      // the hub keeps the brief's ElevenLabs audio; ask for it as a clip first, else read the text
      final dynamic j = await _api.post('/api/clip', <String, dynamic>{'brief': true}).catchError((Object _) => <String, dynamic>{});
      final String url = _s(_map(j)['url']);
      if (url.isNotEmpty) {
        setState(() => _mode = 'speaking');
        await _voice.playUrl(url, null, _map(j)['env']);
        if (mounted) setState(() => _mode = 'idle');
      } else {
        for (final String sent in text.split(RegExp(r'(?<=[.!?])\s+'))) {
          _voice.say(sent);
        }
        while (_voice.speaking && mounted) {
          await Future<void>.delayed(const Duration(milliseconds: 300));
        }
      }
    } catch (_) {}
    if (mounted) setState(() => _briefPlaying = false);
  }

  String _localDay() {
    final DateTime d = DateTime.now();
    return '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
  }

  Future<void> _markDone() async {
    final Map<String, dynamic> t = _map(_snap['todayTask']);
    if (_doneBusy) return;
    setState(() => _doneBusy = true);
    try {
      final dynamic j = await _api.post('/api/today/done', <String, dynamic>{'id': _s(t['id']), 'day': _localDay()});
      final Map<String, dynamic> st = _map(j);
      if (mounted) {
        setState(() => _snap['streak'] = st);
        HapticFeedback.mediumImpact();
        final int n = _n(st['count']).toInt();
        _addMsg('ai', n > 1 ? 'Done. That\'s $n days in a row.' : 'Done. One small thing a day is how health gets easier.');
      }
    } catch (e) {
      _addMsg('sys', 'Couldn\'t save that: ' + e.toString());
    }
    if (mounted) setState(() => _doneBusy = false);
  }

  // ---- chat
  void _addMsg(String role, String text, {Map<String, dynamic>? item, String? route}) {
    _chat.add(<String, dynamic>{'role': role, 'text': text, if (item != null) 'item': item, if (route != null) 'route': route});
    if (mounted) setState(() {});
    Future<void>.delayed(const Duration(milliseconds: 60), () {
      if (_chatScroll.hasClients) _chatScroll.jumpTo(_chatScroll.position.maxScrollExtent);
    });
  }

  Future<void> _ask(String raw) async {
    final String text = raw.trim();
    if (text.isEmpty || _thinking) return;
    _voice.stop();
    _q.clear();
    _addMsg('me', text);
    final String quick = _local(text);
    if (quick.isNotEmpty) {
      if (quick.trim().isNotEmpty) {
        _addMsg('ai', quick);
        _voice.say(quick);
      }
      return;
    }
    setState(() {
      _thinking = true;
      _mode = 'thinking';
    });
    final Map<String, dynamic> msg = <String, dynamic>{'role': 'ai', 'text': ''};
    _chat.add(msg);
    String full = '';
    int spoken = 0;
    void flush(bool fin) {
      final String rest = full.substring(spoken);
      if (fin) {
        if (rest.trim().isNotEmpty) _voice.say(rest);
        spoken = full.length;
        return;
      }
      final RegExpMatch? m = RegExp(r'^[\s\S]*?[.!?](?=\s|$)').firstMatch(rest);
      if (m == null) return;
      _voice.say(m.group(0)!);
      spoken += m.group(0)!.length;
    }

    await _api.chat(text, _hist, onDelta: (String d) {
      full += d;
      msg['text'] = full;
      if (mounted) setState(() => _mode = _voice.speaking ? 'speaking' : 'thinking');
      flush(false);
      if (_chatScroll.hasClients) _chatScroll.jumpTo(_chatScroll.position.maxScrollExtent);
    }, onDone: (Map<String, dynamic> d) {
      full = full.trim();
      msg['text'] = full.isEmpty ? '…' : full;
      flush(true);
      final List<Map<String, dynamic>> hist = _list(d['messages']);
      if (hist.isNotEmpty) _hist = hist;
      for (final Map<String, dynamic> a in _list(d['actions'])) {
        _handleAction(a);
      }
    }, onError: (String e) {
      msg['text'] = (full + '\n[' + e + ']').trim();
    });
    if (!mounted) return;
    setState(() {
      _thinking = false;
      _mode = _voice.speaking ? 'speaking' : 'idle';
    });
    _load();
  }

  void _handleAction(Map<String, dynamic> a) {
    final String t = _s(a['type']);
    if (t == 'open') {
      final String route = _s(a['route']);
      _addMsg('sys', 'Opening ${_s(a['label'])}.', route: route);
      _openPage(route, _s(a['label']));
    } else if (t == 'memory') {
      setState(() => _snap['memory'] = a['value']);
    } else if (t == 'reminders') {
      _loadReminders();
    } else if (t == 'confirm') {
      _addMsg('confirm', _s(_map(a['item'])['summary']), item: _map(a['item']));
    }
  }

  // native navigation: the FlutterFlow page by name (path style, the way the account menu does it)
  void _openPage(String route, String label) {
    if (route.isEmpty || !mounted) return;
    HapticFeedback.lightImpact();
    try {
      final String path = route.startsWith('/') ? route : '/$route';
      GoRouter.of(context).push(path);
    } catch (e) {
      debugPrint('JOVI open $route: $e');
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(SnackBar(content: Text('$label isn\'t available right now.')));
    }
  }

  Future<void> _decide(Map<String, dynamic> msg, String decision) async {
    final Map<String, dynamic> item = _map(msg['item']);
    setState(() => msg['busy'] = true);
    try {
      final dynamic rec = await _api.post('/api/act', <String, dynamic>{'item': item, 'decision': decision});
      final Map<String, dynamic> r = _map(rec);
      msg['status'] = _s(r['status']);
      msg['result'] = _s(r['result']);
      if (msg['status'] == 'done') {
        HapticFeedback.mediumImpact();
        _voice.say(_s(r['result']).isEmpty ? 'Done.' : _s(r['result']));
        _load();
      } else if (msg['status'] == 'failed') {
        _voice.say('That didn\'t go through. ' + _s(r['result']));
      }
    } catch (e) {
      msg['status'] = 'failed';
      msg['result'] = e.toString();
    }
    if (mounted) setState(() => msg['busy'] = false);
  }

  // a confirm card the widget raises itself (panel buttons), same shape as the brain's
  void _confirm(String kind, Map<String, dynamic> params, String summary) {
    _addMsg('confirm', summary, item: <String, dynamic>{'id': 'w${DateTime.now().millisecondsSinceEpoch}', 'kind': kind, 'params': params, 'summary': summary, 'status': 'awaiting confirmation'});
  }

  // a few answers that never need the brain
  String _local(String raw) {
    final String t = raw.toLowerCase().replaceAll(RegExp(r'^jovi,?\s*'), '').replaceAll(RegExp(r'[.!?]+$'), '').trim();
    if (RegExp(r'^(clear|reset|wipe|start over)( the| our| my)? ?(chat|conversation|page)?$').hasMatch(t) && t.length > 4) {
      _clearChat();
      return 'Fresh page. What next?';
    }
    if (RegExp(r'^(what time is it|time)$').hasMatch(t)) {
      final DateTime d = DateTime.now();
      final int h = d.hour % 12 == 0 ? 12 : d.hour % 12;
      return 'It\'s $h:${d.minute.toString().padLeft(2, '0')} ${d.hour < 12 ? 'AM' : 'PM'}.';
    }
    if (RegExp(r'^(stop|quiet|shush|never ?mind|cancel)$').hasMatch(t)) {
      _voice.stop();
      return ' ';
    }
    if (RegExp(r'^(stop|pause|turn off|kill|mute) (the )?(radio|music)$|^radio off$').hasMatch(t)) {
      _radioStop();
      return 'Radio off.';
    }
    final RegExpMatch? rp = RegExp(r'^(?:play|put on|turn on|start)\s+(?:the\s+|some\s+)?(radio|music|.+?)(?:\s+radio)?$').firstMatch(t);
    if (rp != null) {
      final String want = rp.group(1)!.replaceAll(' ', '');
      final int i = want == 'radio' || want == 'music' ? 0 : _radio.indexWhere((List<String> r) => r[2].split(',').any((String k) => want.contains(k)));
      if (i >= 0) {
        _radioPlay(i);
        return 'Playing ${_radio[i][0]}. Say "stop the music" or tap Stop under the core whenever you like.';
      }
    }
    if (RegExp(r'^(call 911|911|emergency)$').hasMatch(t)) {
      _call911();
      return 'Calling 911. If you can, unlock your door and keep your phone with you.';
    }
    return '';
  }

  void _call911() {
    HapticFeedback.heavyImpact();
    launchUrl(Uri.parse('tel:911')).catchError((Object _) => false);
  }

  void _onHeard(String text, bool fin) {
    setState(() => _heard = text);
    if (fin && text.trim().isNotEmpty) {
      _heard = '';
      _ask(text);
    }
  }

  Future<void> _toggleMic() async {
    if (_listening) {
      await _ears.stop();
      return;
    }
    _voice.stop();
    HapticFeedback.lightImpact();
    await _ears.start();
  }

  // ---- reminders + memory
  Future<void> _loadReminders() async {
    try {
      final Map<String, dynamic> r = await _api.get('/api/reminders');
      final List<Map<String, dynamic>> list = _list(r['data']).where((Map<String, dynamic> x) => x['done'] != true).toList();
      if (mounted) setState(() => _snap['reminders'] = list);
    } catch (_) {}
  }

  Future<void> _remPost(Map<String, dynamic> body) async {
    try {
      final dynamic r = await _api.post('/api/reminders', <String, dynamic>{...body, 'tz': _s(_snap['tz'])});
      if (mounted) setState(() => _snap['reminders'] = _list(r));
    } catch (e) {
      _addMsg('sys', 'Couldn\'t save that reminder: ' + e.toString());
    }
  }

  Future<void> _forget(String id) async {
    try {
      final dynamic r = await _api.post('/api/memory', <String, dynamic>{'id': id});
      if (mounted) setState(() => _snap['memory'] = _list(r));
    } catch (_) {}
  }

  void _toggleVoice() {
    setState(() => _voice.enabled = !_voice.enabled);
    if (!_voice.enabled) _voice.stop();
    SharedPreferences.getInstance().then((SharedPreferences p) => p.setBool('joviSpeak', _voice.enabled));
  }

  void _clearChat() {
    _voice.stop();
    setState(() {
      _chat.clear();
      _hist = <Map<String, dynamic>>[];
      _heard = '';
      _mode = 'idle';
    });
  }

  // ---- radio (JC-JOVI-NATIVE-1013-003): a second just_audio player, ducked while Jovi speaks
  Future<void> _radioPlay(int i) async {
    _radioStop();
    final List<String> st = _radio[i];
    _radioIdx = i;
    setState(() => _radioName = st[0]);
    try {
      final AudioPlayer p = AudioPlayer();
      _radioPlayer = p;
      await p.setVolume(_voice.speaking ? _radioVol * 0.15 : _radioVol);
      await p.setUrl(st[1]);
      p.play();
    } catch (e) {
      _addMsg('sys', 'That station wouldn\'t start: ' + e.toString());
      setState(() => _radioName = '');
    }
  }

  void _radioStop() {
    try {
      _radioPlayer?.stop();
      _radioPlayer?.dispose();
    } catch (_) {}
    _radioPlayer = null;
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
      _radioPlayer?.setVolume(_voice.speaking ? _radioVol * 0.15 : _radioVol);
    } catch (_) {}
    setState(() {});
  }

  void _radioDuck(bool speaking) {
    try {
      _radioPlayer?.setVolume(speaking ? _radioVol * 0.15 : _radioVol);
    } catch (_) {}
  }

  Widget _nowPlaying() {
    if (_radioName.isEmpty) return const SizedBox.shrink();
    return Container(
      margin: const EdgeInsets.only(top: 10),
      padding: const EdgeInsets.fromLTRB(12, 8, 8, 8),
      decoration: BoxDecoration(color: Colors.black.withOpacity(.28), borderRadius: BorderRadius.circular(14), border: Border.all(color: _mint.withOpacity(.45))),
      child: Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
        Row(children: <Widget>[
          const Icon(Icons.radio_rounded, size: 15, color: _mint),
          const SizedBox(width: 6),
          Expanded(child: Text(_radioName, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _ivory, fontSize: 12.5, fontWeight: FontWeight.w700))),
          _iconBtn(Icons.skip_previous_rounded, () => _radioStep(-1), 'Previous station'),
          _iconBtn(Icons.skip_next_rounded, () => _radioStep(1), 'Next station'),
          _iconBtn(Icons.stop_rounded, _radioStop, 'Stop the music', accent: true),
        ]),
        Row(children: <Widget>[
          const Icon(Icons.volume_down_rounded, size: 14, color: _muted),
          Expanded(
            child: SliderTheme(
              data: SliderTheme.of(context).copyWith(trackHeight: 2, thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 6), overlayShape: const RoundSliderOverlayShape(overlayRadius: 12), activeTrackColor: _mint, inactiveTrackColor: Colors.white.withOpacity(.15), thumbColor: _mint),
              child: Slider(value: _radioVol, onChanged: _radioSetVol),
            ),
          ),
          const Icon(Icons.volume_up_rounded, size: 14, color: _muted),
        ]),
      ]),
    );
  }

  Widget _iconBtn(IconData icon, VoidCallback onTap, String tip, {bool accent = false}) => Tooltip(
        message: tip,
        child: GestureDetector(
          onTap: onTap,
          child: Container(
            width: 30,
            height: 30,
            margin: const EdgeInsets.only(left: 4),
            decoration: BoxDecoration(shape: BoxShape.circle, color: accent ? _coral : Colors.white.withOpacity(.08), border: Border.all(color: accent ? _coral : Colors.white.withOpacity(.14))),
            child: Icon(icon, size: 17, color: accent ? _navyDeep : _ivory),
          ),
        ),
      );

  Widget _radioCard() => _card(
        title: 'Radio',
        sub: _radioName.isEmpty ? 'Music for rest and recovery: spa, calm classical, sleep, chill. Say "play some spa music" or pick a station.' : 'Playing $_radioName',
        trailing: _radioName.isNotEmpty ? _btn('Stop', _radioStop, icon: Icons.stop_rounded) : null,
        child: Wrap(
          spacing: 6,
          runSpacing: 6,
          children: <Widget>[
            for (int i = 0; i < _radio.length; i++)
              GestureDetector(
                onTap: () => _radioName == _radio[i][0] ? _radioStop() : _radioPlay(i),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 6),
                  decoration: BoxDecoration(color: _radioName == _radio[i][0] ? _coral : Colors.white.withOpacity(.07), borderRadius: BorderRadius.circular(999), border: Border.all(color: _coral.withOpacity(.4))),
                  child: Text(_radio[i][0], style: TextStyle(color: _radioName == _radio[i][0] ? _navyDeep : _ivory, fontSize: 12, fontWeight: FontWeight.w600)),
                ),
              ),
          ],
        ),
      );

  // ---- focus (JC-JOVI-NATIVE-1013-003): a block of quiet with the radio on; she says when
  void _focusStart(int minutes) {
    _focusT?.cancel();
    setState(() => _focusEnd = DateTime.now().add(Duration(minutes: minutes)));
    if (_radioName.isEmpty) _radioPlay(0);
    _focusT = Timer.periodic(const Duration(seconds: 1), (Timer t) {
      if (!mounted) return;
      final DateTime? end = _focusEnd;
      if (end == null) {
        t.cancel();
        return;
      }
      if (DateTime.now().isAfter(end)) {
        t.cancel();
        setState(() => _focusEnd = null);
        HapticFeedback.mediumImpact();
        _voice.say('Time. Stand up, stretch, have some water.');
        _addMsg('ai', 'Focus block done. Nice work.');
      } else {
        setState(() {});
      }
    });
  }

  void _focusStop() {
    _focusT?.cancel();
    setState(() => _focusEnd = null);
  }

  String _focusLeft() {
    final DateTime? end = _focusEnd;
    if (end == null) return '';
    final Duration d = end.difference(DateTime.now());
    final int m = d.inMinutes.clamp(0, 999), sec = (d.inSeconds % 60).clamp(0, 59);
    return 'focus ${m.toString().padLeft(2, '0')}:${sec.toString().padLeft(2, '0')}';
  }

  Widget _focusCard() {
    final bool on = _focusEnd != null;
    return _card(
      title: 'Focus',
      sub: on ? 'Head down. ${_focusLeft().replaceAll('focus ', '')} left. The radio stays on; I\'ll tell you when.' : 'A block of quiet with the radio on, for work, rest or a walk. I\'ll keep quiet and tell you when time is up.',
      trailing: on ? _btn('Stop', _focusStop, icon: Icons.stop_rounded) : null,
      child: Wrap(spacing: 8, runSpacing: 8, children: <Widget>[
        for (final int m in <int>[25, 50, 90]) _btn('$m min', on ? null : () => _focusStart(m), accent: m == 50, icon: Icons.timer_rounded),
      ]),
    );
  }

  // ---- the morning brief on a schedule (JC-JOVI-NATIVE-1013-003): users/{uid}.joviMorningOn / joviMorningHour
  Future<void> _setAlerts(bool enabled, int hour) async {
    if (_alertsBusy) return;
    setState(() => _alertsBusy = true);
    try {
      final dynamic r = await _api.post('/api/alerts', <String, dynamic>{'enabled': enabled, 'hour': hour});
      if (mounted) {
        setState(() {
          final Map<String, dynamic> m = _map(_snap['member']);
          m['morning'] = <String, dynamic>{'enabled': _map(r)['enabled'] == true, 'hour': _n(_map(r)['hour']).toInt()};
          _snap['member'] = m;
        });
      }
    } catch (e) {
      _addMsg('sys', 'Couldn\'t change that: ' + e.toString());
    }
    if (mounted) setState(() => _alertsBusy = false);
  }

  Widget _alertsRow() {
    final Map<String, dynamic> mo = _map(_map(_snap['member'])['morning']);
    final bool on = mo['enabled'] == true;
    final int hour = _n(mo['hour']) > 0 ? _n(mo['hour']).toInt() : 7;
    String h12(int h) => '${h % 12 == 0 ? 12 : h % 12} ${h < 12 ? 'AM' : 'PM'}';
    return Container(
      margin: const EdgeInsets.only(top: 12),
      padding: const EdgeInsets.fromLTRB(12, 8, 8, 8),
      decoration: BoxDecoration(color: Colors.black.withOpacity(.22), borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.white.withOpacity(.1))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
        Row(children: <Widget>[
          const Icon(Icons.wb_twilight_rounded, size: 15, color: _coralSoft),
          const SizedBox(width: 8),
          Expanded(child: Text(on ? 'Every morning at ${h12(hour)}, even when you don\'t open the app' : 'Push the brief to my phone every morning', style: const TextStyle(color: _ivory, fontSize: 12.5))),
          Switch(value: on, onChanged: _alertsBusy ? null : (bool v) => _setAlerts(v, hour), activeColor: _navyDeep, activeTrackColor: _mint, inactiveThumbColor: _muted, inactiveTrackColor: Colors.white.withOpacity(.12)),
        ]),
        if (on)
          Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
            for (final int h in <int>[6, 7, 8, 9, 10]) _chip(h12(h), onTap: _alertsBusy ? null : () => _setAlerts(true, h), accent: h == hour),
          ]),
      ]),
    );
  }

  // ---------------------------------------------------------------- UI
  TextStyle _serif(double size, {Color color = _ivory, FontWeight w = FontWeight.w600}) {
    try {
      return GoogleFonts.dmSerifDisplay(fontSize: size, fontWeight: w, color: color, height: 1.1);
    } catch (_) {
      return TextStyle(fontFamily: 'serif', fontSize: size, fontWeight: w, color: color, height: 1.1);
    }
  }

  Widget _card({required String title, Widget? trailing, String? sub, required Widget child}) => Container(
        margin: const EdgeInsets.only(bottom: 14),
        padding: const EdgeInsets.fromLTRB(18, 16, 18, 16),
        decoration: BoxDecoration(
          gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: <Color>[Colors.white.withOpacity(.09), Colors.white.withOpacity(.04)]),
          borderRadius: BorderRadius.circular(22),
          border: Border.all(color: Colors.white.withOpacity(.12)),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
          Row(children: <Widget>[
            Expanded(child: Text(title, style: _serif(21))),
            if (trailing != null) trailing,
          ]),
          if (sub != null) Padding(padding: const EdgeInsets.only(top: 2), child: Text(sub, style: const TextStyle(color: _muted, fontSize: 12.5, height: 1.4))),
          const SizedBox(height: 10),
          child,
        ]),
      );

  Widget _tag(String t, {Color? bg, Color? fg}) => Container(
        margin: const EdgeInsets.only(left: 6),
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
        decoration: BoxDecoration(color: bg ?? _coral.withOpacity(.14), borderRadius: BorderRadius.circular(7), border: Border.all(color: (bg ?? _coral).withOpacity(.3))),
        child: Text(t.toUpperCase(), style: TextStyle(color: fg ?? _coralSoft, fontSize: 9.5, letterSpacing: .8, fontWeight: FontWeight.w700)),
      );

  Widget _row({required String title, String? d, Widget? tag, Widget? side}) => Container(
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: const BoxDecoration(border: Border(top: BorderSide(color: Color(0x12FFFFFF)))),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
              Row(children: <Widget>[Flexible(child: Text(title, style: const TextStyle(color: _ivory, fontWeight: FontWeight.w600, fontSize: 14))), if (tag != null) tag]),
              if (d != null && d.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 2), child: Text(d, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _muted, fontSize: 12.5))),
            ]),
          ),
          if (side != null) Padding(padding: const EdgeInsets.only(left: 10), child: side),
        ]),
      );

  Widget _btn(String label, VoidCallback? onTap, {bool accent = false, IconData? icon, bool small = true}) {
    final Widget child = Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
      if (icon != null) Icon(icon, size: 15, color: accent ? _navyDeep : _ivory),
      if (icon != null && label.isNotEmpty) const SizedBox(width: 6),
      if (label.isNotEmpty) Text(label, style: TextStyle(fontSize: small ? 12 : 13.5, fontWeight: FontWeight.w700, color: accent ? _navyDeep : _ivory)),
    ]);
    return accent
        ? FilledButton(onPressed: onTap, style: FilledButton.styleFrom(backgroundColor: _coral, foregroundColor: _navyDeep, padding: EdgeInsets.symmetric(horizontal: small ? 12 : 18, vertical: small ? 6 : 12), minimumSize: const Size(0, 30), tapTargetSize: MaterialTapTargetSize.shrinkWrap, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(999))), child: child)
        : OutlinedButton(onPressed: onTap, style: OutlinedButton.styleFrom(side: BorderSide(color: _coral.withOpacity(.45)), padding: EdgeInsets.symmetric(horizontal: small ? 12 : 18, vertical: small ? 6 : 12), minimumSize: const Size(0, 30), tapTargetSize: MaterialTapTargetSize.shrinkWrap, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(999))), child: child);
  }

  Widget _stat(String v, String k, {Color? color}) => Expanded(
        child: Container(
          margin: const EdgeInsets.only(right: 8),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
          decoration: BoxDecoration(color: Colors.black.withOpacity(.22), borderRadius: BorderRadius.circular(14)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
            Text(v, style: _serif(22, color: color ?? _ivory)),
            const SizedBox(height: 2),
            Text(k, style: const TextStyle(color: _muted, fontSize: 11)),
          ]),
        ),
      );

  // ---- the console: core + chat
  List<String> get _chips {
    final List<String> out = <String>[];
    final Map<String, dynamic> c = _map(_snap['counts']);
    final List<Map<String, dynamic>> appts = _list(_snap['appointments']);
    final List<Map<String, dynamic>> doses = _list(_snap['dosesDue']);
    final List<Map<String, dynamic>> refill = _list(_snap['refillSoon']);
    final List<Map<String, dynamic>> pets = _list(_snap['pets']);
    final Map<String, dynamic> billing = _map(_snap['billing']);
    final List<Map<String, dynamic>> medsDue = _list(_snap['medsDue']);
    if (medsDue.isNotEmpty) out.add('Log my ${_s(medsDue.first['name'])}');
    if (doses.isNotEmpty) out.add('Log ${_s(doses.first['name'])} for ${_s(doses.first['pet'])}');
    if (appts.isNotEmpty) out.add(_n(c['today']) > 0 ? 'What do I need for today\'s appointment?' : 'When is my next appointment?');
    if (refill.isNotEmpty) out.add('Refill ${_s(refill.first['name'])}');
    if (_n(c['needsInfo']) > 0) out.add('What does my claim need?');
    if (billing['pastDue'] == true) out.add('What happened with my payment?');
    if (_n(c['openClaims']) > 0) out.add('Where are my claims?');
    if (pets.isNotEmpty) out.add('How is ${_s(pets.first['name'])} doing on meds?');
    out.addAll(<String>['Book an urgent care visit', 'Book a video visit', 'What are my medications?', 'How much of my deductible is left?', 'Log my blood pressure', 'Log my weight', 'What\'s the air like today?', 'Remind me to take my meds at 8pm', 'Open my membership card', 'Talk to support', 'What do you remember about me?']);
    final List<String> seen = <String>[];
    for (final String x in out) {
      if (!seen.contains(x)) seen.add(x);
    }
    return seen;
  }

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

  Widget _stateLabel() => Text(_focusEnd != null && _mode == 'idle' ? _focusLeft() : (_mode == 'idle' && _radioName.isNotEmpty ? '♪ $_radioName' : _mode), style: TextStyle(color: _focusEnd != null && _mode == 'idle' ? _gold : _muted, fontSize: 10.5, letterSpacing: 2));

  Widget _chatBox(double height) => Container(
        height: height,
        decoration: BoxDecoration(color: Colors.black.withOpacity(.25), borderRadius: BorderRadius.circular(16), border: Border.all(color: Colors.white.withOpacity(.08))),
        clipBehavior: Clip.antiAlias,
        child: Stack(children: <Widget>[
          Positioned.fill(child: _chatList()),
          if (_chat.isNotEmpty)
            Positioned(
              top: 6,
              right: 6,
              child: GestureDetector(
                onTap: _clearChat,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                  decoration: BoxDecoration(color: Colors.black.withOpacity(.45), borderRadius: BorderRadius.circular(999), border: Border.all(color: Colors.white.withOpacity(.16))),
                  child: const Row(mainAxisSize: MainAxisSize.min, children: <Widget>[Icon(Icons.close_rounded, size: 12, color: _muted), SizedBox(width: 4), Text('Clear', style: TextStyle(color: _muted, fontSize: 11, fontWeight: FontWeight.w700))]),
                ),
              ),
            ),
        ]),
      );

  Widget _chatList() => _chat.isEmpty
      ? const Center(child: Padding(padding: EdgeInsets.all(20), child: Text('Good to see you. Ask me about your appointments, medications, claims, your pets, or how to feel a little better today.', textAlign: TextAlign.center, style: TextStyle(color: _muted, fontSize: 13, height: 1.5))))
      : ListView.builder(
          controller: _chatScroll,
          padding: const EdgeInsets.all(12),
          itemCount: _chat.length,
          itemBuilder: (BuildContext c, int i) => _bubble(_chat[i]),
        );

  Widget _inputRow() => Row(children: <Widget>[
        Expanded(
          child: TextField(
            controller: _q,
            textInputAction: TextInputAction.send,
            onSubmitted: _ask,
            style: const TextStyle(color: _ivory, fontSize: 14),
            cursorColor: _coral,
            decoration: InputDecoration(
              hintText: 'When is my next visit? Refill my prescription…',
              hintStyle: const TextStyle(color: _muted, fontSize: 13),
              isDense: true,
              filled: true,
              fillColor: Colors.black.withOpacity(.3),
              contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(999), borderSide: BorderSide(color: _coral.withOpacity(.35))),
              enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(999), borderSide: BorderSide(color: _coral.withOpacity(.35))),
              focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(999), borderSide: const BorderSide(color: _coral)),
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
              decoration: BoxDecoration(shape: BoxShape.circle, color: _listening ? _mint : Colors.black.withOpacity(.3), border: Border.all(color: _listening ? _mint : _coral.withOpacity(.5))),
              child: Icon(_listening ? Icons.stop_rounded : Icons.mic_rounded, color: _listening ? _navyDeep : _coral, size: 20),
            ),
          ),
        const SizedBox(width: 8),
        GestureDetector(
          onTap: () => _ask(_q.text),
          child: Container(
            width: 42,
            height: 42,
            decoration: const BoxDecoration(shape: BoxShape.circle, color: _coral),
            child: const Icon(Icons.arrow_upward_rounded, color: _navyDeep, size: 22),
          ),
        ),
      ]);

  Widget _chip(String c, {VoidCallback? onTap, bool accent = false}) => GestureDetector(
        onTap: onTap ?? () => _ask(c),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 6),
          decoration: BoxDecoration(color: accent ? _coral.withOpacity(.16) : Colors.white.withOpacity(.07), borderRadius: BorderRadius.circular(999), border: Border.all(color: accent ? _coral.withOpacity(.5) : Colors.white.withOpacity(.14))),
          child: Text(c, style: TextStyle(color: accent ? _coralSoft : _ivory, fontSize: 12)),
        ),
      );

  Widget _chipsWrap({int show = 6}) {
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
  }

  Widget _emergencyLine() => GestureDetector(
        onTap: _call911,
        child: Padding(
          padding: const EdgeInsets.only(top: 10),
          child: Row(mainAxisAlignment: MainAxisAlignment.center, mainAxisSize: MainAxisSize.min, children: const <Widget>[
            Icon(Icons.emergency_rounded, size: 13, color: _red),
            SizedBox(width: 5),
            Text('Emergency? Tap to call 911. Jovi is not a clinician.', style: TextStyle(color: _muted, fontSize: 11)),
          ]),
        ),
      );

  Widget _console() {
    return _card(
      title: 'Jovi',
      trailing: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
        _stateLabel(),
        const SizedBox(width: 10),
        GestureDetector(
          onTap: _toggleVoice,
          child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
            Icon(_voice.enabled ? Icons.volume_up_rounded : Icons.volume_off_rounded, size: 16, color: _voice.enabled ? _coral : _muted),
            const SizedBox(width: 4),
            Text('voice', style: TextStyle(color: _voice.enabled ? _coral : _muted, fontSize: 12)),
          ]),
        ),
      ]),
      child: Column(children: <Widget>[
        _core(196),
        _nowPlaying(),
        const SizedBox(height: 10),
        _chatBox(220),
        if (_heard.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: Text(_heard, style: const TextStyle(color: _mint, fontSize: 12.5, fontStyle: FontStyle.italic))),
        const SizedBox(height: 10),
        _inputRow(),
        const SizedBox(height: 10),
        _chipsWrap(),
        _emergencyLine(),
      ]),
    );
  }

  // ---- the deck: Jovi across the top of Home. The host draws the surface; this is her core, her words, and the way to talk to her.
  String _headline() {
    if (_loading && _snap.isEmpty) return 'Reading your day…';
    final String brief = _s(_map(_snap['brief'])['text']).trim();
    if (brief.isNotEmpty) {
      final List<String> sents = brief.split(RegExp(r'(?<=[.!?])\s+'));
      return sents.take(2).join(' ');
    }
    final Map<String, dynamic> c = _map(_snap['counts']);
    final List<String> parts = <String>[
      _n(c['today']) > 0 ? '${_n(c['today']).toInt()} appointment${_n(c['today']) == 1 ? '' : 's'} today.' : _n(c['upcoming']) > 0 ? '${_n(c['upcoming']).toInt()} appointment${_n(c['upcoming']) == 1 ? '' : 's'} coming up.' : 'Nothing booked.',
      if (_n(c['dosesDue']) > 0) '${_n(c['dosesDue']).toInt()} pet dose${_n(c['dosesDue']) == 1 ? '' : 's'} due.',
      if (_n(c['refillSoon']) > 0) 'A refill is due.',
      'Ask me anything.',
    ];
    return parts.join(' ');
  }

  Future<void> _sheet(String title, Widget Function() build) async {
    if (!mounted) return;
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (BuildContext ctx) => Container(
        constraints: BoxConstraints(maxHeight: MediaQuery.of(ctx).size.height * .86),
        decoration: const BoxDecoration(
          gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: <Color>[_navyDeep, _navy]),
          borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
        ),
        child: SafeArea(
          top: false,
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 20),
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
              Center(child: Container(width: 38, height: 4, margin: const EdgeInsets.only(bottom: 12), decoration: BoxDecoration(color: Colors.white.withOpacity(.25), borderRadius: BorderRadius.circular(2)))),
              _SheetHost(build: build),
            ]),
          ),
        ),
      ),
    );
    if (mounted) setState(() {});
  }

  Widget _dockBtn(IconData icon, String label, VoidCallback onTap, {String? badge, bool on = false}) => Tooltip(
        message: label,
        child: GestureDetector(
          onTap: onTap,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
            decoration: BoxDecoration(color: on ? _coral.withOpacity(.18) : Colors.black.withOpacity(.22), borderRadius: BorderRadius.circular(12), border: Border.all(color: on ? _coral.withOpacity(.6) : Colors.white.withOpacity(.1))),
            child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
              Icon(icon, size: 15, color: on ? _coral : _coralSoft),
              const SizedBox(width: 6),
              Text(label, style: TextStyle(color: on ? _coralSoft : _ivory, fontSize: 11.5, fontWeight: FontWeight.w600)),
              if (badge != null && badge.isNotEmpty) ...<Widget>[
                const SizedBox(width: 6),
                Container(padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1), decoration: BoxDecoration(color: _mint, borderRadius: BorderRadius.circular(8)), child: Text(badge, style: const TextStyle(color: _navyDeep, fontSize: 10.5, fontWeight: FontWeight.w800))),
              ],
            ]),
          ),
        ),
      );

  Widget _dock() {
    final Map<String, dynamic> c = _map(_snap['counts']);
    final int rem = _list(_snap['reminders']).length;
    final Map<String, dynamic> billing = _map(_snap['billing']);
    final int pets = _list(_snap['pets']).length;
    return Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
      _dockBtn(Icons.auto_stories_rounded, 'Brief', () => _sheet('Brief', _briefCard)),
      _dockBtn(Icons.event_rounded, 'Appointments', () => _sheet('Appointments', _apptsCard), badge: _n(c['upcoming']) > 0 ? '${_n(c['upcoming']).toInt()}' : null),
      _dockBtn(Icons.medication_rounded, 'Medications', () => _sheet('Medications', _medsCard), badge: _n(c['refillSoon']) > 0 ? '${_n(c['refillSoon']).toInt()}' : null),
      _dockBtn(Icons.receipt_long_rounded, 'Claims', () => _sheet('Claims', _claimsCard), badge: _n(c['needsInfo']) > 0 ? '!' : (_n(c['openClaims']) > 0 ? '${_n(c['openClaims']).toInt()}' : null)),
      _dockBtn(Icons.credit_card_rounded, 'Billing', () => _sheet('Billing', _billingCard), badge: billing['pastDue'] == true ? '!' : null),
      if (pets > 0) _dockBtn(Icons.pets_rounded, 'Pets', () => _sheet('Pets', _petsCard), badge: _n(c['dosesDue']) > 0 ? '${_n(c['dosesDue']).toInt()}' : null),
      _dockBtn(Icons.monitor_heart_rounded, 'Vitals', () => _sheet('Vitals', _vitalsCard)),
      _dockBtn(Icons.vaccines_rounded, 'Vaccines', () => _sheet('Vaccines', _vaccinesCard), badge: _n(c['vaccinesDue']) > 0 ? '${_n(c['vaccinesDue']).toInt()}' : null),
      _dockBtn(Icons.air_rounded, 'Air & weather', () => _sheet('Air & weather', _weatherCard)),
      _dockBtn(Icons.alarm_rounded, 'Reminders', () => _sheet('Reminders', _remindersCard), badge: rem > 0 ? '$rem' : null),
      _dockBtn(Icons.psychology_rounded, 'Memory', () => _sheet('Memory', _memoryCard)),
      _dockBtn(Icons.timer_rounded, 'Focus', () => _sheet('Focus', _focusCard), on: _focusEnd != null),
      _dockBtn(Icons.radio_rounded, 'Radio', () => _sheet('Radio', _radioCard), on: _radioName.isNotEmpty),
      if (_chat.isNotEmpty) _dockBtn(Icons.cleaning_services_rounded, 'Clear chat', _clearChat),
    ]);
  }

  // ---- today's one thing, with a streak
  Widget _todayCard() {
    final Map<String, dynamic> t = _map(_snap['todayTask']);
    final Map<String, dynamic> st = _map(_snap['streak']);
    if (t.isEmpty) return const SizedBox.shrink();
    final bool done = st['doneToday'] == true;
    final int streak = _n(st['count']).toInt();
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 10, 12, 10),
      decoration: BoxDecoration(
        gradient: LinearGradient(colors: <Color>[_coral.withOpacity(done ? .10 : .20), _coral.withOpacity(.05)]),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: _coral.withOpacity(done ? .3 : .6)),
      ),
      child: Row(children: <Widget>[
        Container(
          width: 34,
          height: 34,
          decoration: BoxDecoration(shape: BoxShape.circle, color: done ? _mint.withOpacity(.25) : _coral.withOpacity(.18), border: Border.all(color: done ? _mint : _coral.withOpacity(.6))),
          child: Icon(done ? Icons.check_rounded : Icons.flag_rounded, size: 18, color: done ? _mint : _coralSoft),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: <Widget>[
            Row(children: <Widget>[
              Text(done ? 'DONE FOR TODAY' : 'TODAY', style: const TextStyle(color: _muted, fontSize: 9.5, letterSpacing: 2, fontWeight: FontWeight.w700)),
              if (streak > 0) ...<Widget>[
                const SizedBox(width: 8),
                const Icon(Icons.local_fire_department_rounded, size: 13, color: _gold),
                const SizedBox(width: 2),
                Text('$streak day${streak == 1 ? '' : 's'}', style: const TextStyle(color: _gold, fontSize: 11, fontWeight: FontWeight.w700)),
              ],
            ]),
            const SizedBox(height: 2),
            Text(done ? 'Tomorrow brings the next one. Keep the streak.' : _s(t['title']), maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _ivory, fontSize: 14.5, fontWeight: FontWeight.w700, height: 1.25)),
            if (!done && _s(t['why']).isNotEmpty) Text(_s(t['why']), maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _muted, fontSize: 12)),
          ]),
        ),
        const SizedBox(width: 8),
        if (!done) ...<Widget>[
          _btn('Do it', () => _ask(_s(t['ask'])), accent: true, icon: Icons.auto_awesome_rounded),
          const SizedBox(width: 6),
          _btn('', _doneBusy ? null : _markDone, icon: Icons.check_rounded),
        ],
      ]),
    );
  }

  // ---------------------------------------------------------------- the hero (JC-JOVI-NATIVE-1013-004)
  String _heroGreeting() {
    final int h = DateTime.now().hour;
    final String tod = h < 4 ? 'Still up' : h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
    String who = _s(_map(_snap['member'])['firstName']);
    if (who.isEmpty) {
      final String dn = (FirebaseAuth.instance.currentUser?.displayName ?? '').trim();
      if (dn.isNotEmpty) who = dn.split(' ').first;
    }
    return who.isEmpty ? '$tod.' : '$tod, $who.';
  }

  String _heroLine() {
    final String brief = _s(_map(_snap['brief'])['text']).trim();
    if (brief.isNotEmpty) {
      final RegExpMatch? m = RegExp(r'^[\s\S]*?[.!?](?=\s|$)').firstMatch(brief);
      final String first = (m?.group(0) ?? brief).trim();
      // the brief opens with its own greeting; the hero already greeted, so take the sentence after it when there is one
      if (RegExp(r'^(good (morning|afternoon|evening)|hello|hi|hey|morning|evening)\b', caseSensitive: false).hasMatch(first) && brief.length > first.length + 8) {
        final RegExpMatch? m2 = RegExp(r'^[\s\S]*?[.!?](?=\s|$)').firstMatch(brief.substring(first.length).trim());
        if (m2 != null) return m2.group(0)!.trim();
      }
      return first;
    }
    if (_loading && _snap.isEmpty) return '';
    final Map<String, dynamic> c = _map(_snap['counts']);
    if (_n(c['today']) > 0) return 'You have ${_n(c['today']).toInt()} appointment${_n(c['today']) == 1 ? '' : 's'} today.';
    if (_n(c['medsDue']) > 0) return 'A medication is still to take today.';
    if (_n(c['upcoming']) > 0) return 'Your next visit is ${_day(_s(_list(_snap['appointments']).first['date']))}.';
    return 'Nothing is waiting on you. Ask me anything.';
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
        decoration: BoxDecoration(shape: BoxShape.circle, color: done ? _mint.withOpacity(.22) : _coral.withOpacity(.18), border: Border.all(color: done ? _mint : _coral.withOpacity(.7))),
        child: Icon(done ? Icons.check_rounded : Icons.flag_rounded, size: 14, color: done ? _mint : _coralSoft),
      ),
      const SizedBox(width: 9),
      Expanded(
        child: Text(done ? 'Done for today${streak > 1 ? ' · $streak days running' : ''}.' : _s(t['title']), maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: done ? _muted : _ivory, fontSize: 14, fontWeight: FontWeight.w600)),
      ),
      if (!done) ...<Widget>[
        const SizedBox(width: 8),
        _btn('Do it', () => _openChat(ask: _s(t['ask'])), accent: true),
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
            color: Colors.white.withOpacity(.07),
            borderRadius: BorderRadius.circular(999),
            border: Border.all(color: Colors.white.withOpacity(.16)),
            boxShadow: <BoxShadow>[BoxShadow(color: Colors.black.withOpacity(.18), blurRadius: 18, offset: const Offset(0, 8))],
          ),
          child: Row(children: <Widget>[
            const Icon(Icons.auto_awesome_rounded, size: 16, color: _coralSoft),
            const SizedBox(width: 10),
            Expanded(child: Text(_chat.isNotEmpty ? 'Continue with Jovi…' : 'Ask Jovi anything', style: const TextStyle(color: _muted, fontSize: 14))),
            if (_micAvailable)
              GestureDetector(
                onTap: () {
                  _openChat(listen: true);
                },
                child: Container(
                  width: 38,
                  height: 38,
                  decoration: BoxDecoration(shape: BoxShape.circle, color: _listening ? _mint : _coral),
                  child: Icon(_listening ? Icons.stop_rounded : Icons.mic_rounded, color: _navyDeep, size: 19),
                ),
              ),
          ]),
        ),
      );

  // the chat as a sheet over Home: the core small, the conversation, the bar, the chips
  Future<void> _openChat({String? ask, bool listen = false}) async {
    HapticFeedback.selectionClick();
    if (ask != null && ask.isNotEmpty) _ask(ask);
    if (listen) _toggleMic();
    await _sheet('Jovi', () => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: <Widget>[
          Row(children: <Widget>[
            _core(84),
            const SizedBox(width: 10),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[Text('Jovi', style: _serif(22)), _stateLabel()])),
            GestureDetector(
              onTap: _toggleVoice,
              child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
                Icon(_voice.enabled ? Icons.volume_up_rounded : Icons.volume_off_rounded, size: 16, color: _voice.enabled ? _coral : _muted),
                const SizedBox(width: 4),
                Text('voice', style: TextStyle(color: _voice.enabled ? _coral : _muted, fontSize: 12)),
              ]),
            ),
          ]),
          _nowPlaying(),
          const SizedBox(height: 10),
          _chatBox(MediaQuery.of(context).size.height * .38),
          if (_heard.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: Text(_heard, style: const TextStyle(color: _mint, fontSize: 12.5, fontStyle: FontStyle.italic))),
          const SizedBox(height: 10),
          _inputRow(),
          const SizedBox(height: 10),
          _chipsWrap(show: 5),
          const SizedBox(height: 6),
          Wrap(spacing: 6, runSpacing: 6, children: <Widget>[
            _dockBtn(Icons.open_in_full_rounded, 'Open Jovi', () => _openPage('jovi', 'Jovi')),
            _dockBtn(Icons.timer_rounded, 'Focus', () => _sheet('Focus', _focusCard), on: _focusEnd != null),
            _dockBtn(Icons.radio_rounded, 'Radio', () => _sheet('Radio', _radioCard), on: _radioName.isNotEmpty),
            _dockBtn(Icons.psychology_rounded, 'Memory', () => _sheet('Memory', _memoryCard)),
          ]),
          _emergencyLine(),
        ]));
  }

  // glance tiles: the numbers at a glance, one tap to the sheet; hidden until there is something to show
  List<Map<String, dynamic>> _glances() {
    final Map<String, dynamic> c = _map(_snap['counts']);
    final Map<String, dynamic> b = _map(_snap['billing']);
    final List<Map<String, dynamic>> appts = _list(_snap['appointments']);
    final List<Map<String, dynamic>> out = <Map<String, dynamic>>[];
    // plan status first: it replaced Home's "Your plan is Active" line
    out.add(<String, dynamic>{'icon': Icons.verified_rounded, 'k': 'Plan', 'v': b['pastDue'] == true ? 'Past due' : _title(_s(b['status']).isEmpty ? 'active' : _s(b['status'])), 'accent': b['pastDue'] == true, 'good': b['pastDue'] != true, 'open': () => _sheet('Billing', _billingCard)});
    if (appts.isNotEmpty) {
      final Map<String, dynamic> a = appts.first;
      final String d = _day(_s(a['date']));
      out.add(<String, dynamic>{'icon': Icons.event_rounded, 'k': 'Next visit', 'v': '${_s(a['date']) == _s(_snap['today']) ? 'Today' : d.split(',').first} ${_s(a['time'])}', 'accent': _s(a['date']) == _s(_snap['today']), 'open': () => _sheet('Appointments', _apptsCard)});
    }
    if (_n(c['meds']) > 0 || _n(c['prescriptions']) > 0) {
      final int due = _n(c['medsDue']).toInt();
      out.add(<String, dynamic>{'icon': Icons.medication_rounded, 'k': 'Medications', 'v': _n(c['refillSoon']) > 0 ? 'Refill due' : due > 0 ? '$due to take' : 'On track', 'accent': due > 0 || _n(c['refillSoon']) > 0, 'open': () => _sheet('Medications', _medsCard)});
    }
    if (_n(c['dosesDue']) > 0 || _n(c['pets']) > 0) {
      final int due = _n(c['dosesDue']).toInt();
      out.add(<String, dynamic>{'icon': Icons.pets_rounded, 'k': 'Pets', 'v': due > 0 ? '$due dose${due == 1 ? '' : 's'} due' : 'All good', 'accent': due > 0, 'open': () => _sheet('Pets', _petsCard)});
    }
    if (_n(c['openClaims']) > 0) out.add(<String, dynamic>{'icon': Icons.receipt_long_rounded, 'k': 'Claims', 'v': _n(c['needsInfo']) > 0 ? 'Needs info' : '${_n(c['openClaims']).toInt()} in review', 'accent': _n(c['needsInfo']) > 0, 'open': () => _sheet('Claims', _claimsCard)});
    if (_n(b['deductible']) > 0) {
      final int pct = (100 * _n(b['deductiblePaid']) / _n(b['deductible'])).clamp(0, 100).round();
      out.add(<String, dynamic>{'icon': Icons.shield_rounded, 'k': 'Deductible', 'v': '$pct% met', 'accent': false, 'open': () => _sheet('Billing', _billingCard)});
    }
    if (_n(c['vaccinesDue']) > 0) out.add(<String, dynamic>{'icon': Icons.vaccines_rounded, 'k': 'Vaccines', 'v': '${_n(c['vaccinesDue']).toInt()} due', 'accent': true, 'open': () => _sheet('Vaccines', _vaccinesCard)});
    final List<Map<String, dynamic>> rem = _list(_snap['reminders']);
    if (rem.isNotEmpty) out.add(<String, dynamic>{'icon': Icons.alarm_rounded, 'k': 'Reminders', 'v': '${rem.length} set', 'accent': _list(_snap['due']).isNotEmpty, 'open': () => _sheet('Reminders', _remindersCard)});
    final Map<String, dynamic> w = _map(_map(_snap['weather'])['current']);
    if (w.isNotEmpty) out.add(<String, dynamic>{'icon': _wmoIcon(w['weather_code']), 'k': _s(_map(_map(_snap['weather'])['air'])['label']).isEmpty ? 'Outside' : 'Air ${_s(_map(_map(_snap['weather'])['air'])['label'])}', 'v': '${_n(w['temperature_2m']).round()}° ${_wmo(w['weather_code'])}', 'accent': _n(_map(_map(_snap['weather'])['air'])['aqi']) > 100, 'open': () => _sheet('Air & weather', _weatherCard)});
    return out;
  }

  Widget _glanceTile(Map<String, dynamic> g, int i, bool reduce) {
    final bool accent = g['accent'] == true, good = g['good'] == true;
    final Color c = accent ? _coralSoft : good ? _mint : _ivory;
    final Widget tile = GestureDetector(
      onTap: () {
        HapticFeedback.selectionClick();
        (g['open'] as VoidCallback)();
      },
      child: Container(
        width: 132,
        margin: const EdgeInsets.only(right: 10),
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(accent ? .10 : .06),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: accent ? _coral.withOpacity(.45) : Colors.white.withOpacity(.12)),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: <Widget>[
          Row(children: <Widget>[Icon(g['icon'] as IconData, size: 13, color: c), const SizedBox(width: 5), Expanded(child: Text(_s(g['k']).toUpperCase(), maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _muted, fontSize: 9.5, letterSpacing: 1.2, fontWeight: FontWeight.w700)))]),
          const SizedBox(height: 4),
          Text(_s(g['v']), maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: c, fontSize: 14.5, fontWeight: FontWeight.w700, letterSpacing: -.2)),
        ]),
      ),
    );
    if (reduce) return tile;
    // a staggered rise, Home's own 420 ms curve
    return AnimatedOpacity(
      opacity: _entered ? 1 : 0,
      duration: Duration(milliseconds: 420 + i * 60),
      curve: Curves.easeOutCubic,
      child: AnimatedSlide(offset: _entered ? Offset.zero : const Offset(0, .18), duration: Duration(milliseconds: 420 + i * 60), curve: Curves.easeOutCubic, child: tile),
    );
  }

  Widget _hero(BuildContext context) {
    final bool reduce = MediaQuery.maybeOf(context)?.disableAnimations ?? false;
    if (!_entered) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted && !_entered) setState(() => _entered = true);
      });
    }
    final String line = _heroLine();
    if (line != _typedFor) WidgetsBinding.instance.addPostFrameCallback((_) => _typeIn(line));
    final String shown = line.substring(0, math.min(_typed, line.length));
    final bool typing = shown.length < line.length;
    if (_err.isNotEmpty) {
      return Row(children: <Widget>[
        _core(96),
        const SizedBox(width: 14),
        Expanded(child: Text('Jovi couldn\'t load your records. $_err', style: const TextStyle(color: _muted, fontSize: 13, height: 1.4))),
        const SizedBox(width: 10),
        _btn('Try again', () => _load(first: true), accent: true),
      ]);
    }
    final List<Map<String, dynamic>> glances = _loading && _snap.isEmpty ? <Map<String, dynamic>>[] : _glances();
    Widget rise(Widget child, {int delay = 0}) => reduce
        ? child
        : AnimatedOpacity(
            opacity: _entered ? 1 : 0,
            duration: Duration(milliseconds: 420 + delay),
            curve: Curves.easeOutCubic,
            child: AnimatedSlide(offset: _entered ? Offset.zero : const Offset(0, .06), duration: Duration(milliseconds: 420 + delay), curve: Curves.easeOutCubic, child: child),
          );
    return Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: <Widget>[
      // her greeting on its own line, full width; the core and her line share the row beneath
      rise(Text(_heroGreeting(), maxLines: 1, overflow: TextOverflow.ellipsis, style: _serif(30, w: FontWeight.w500).copyWith(letterSpacing: -.6))),
      const SizedBox(height: 2),
      rise(Row(crossAxisAlignment: CrossAxisAlignment.center, children: <Widget>[
        GestureDetector(
          onTap: () {
            if (_voice.speaking) {
              _voice.stop();
              return;
            }
            _openPage('jovi', 'Jovi');
          },
          onLongPress: () => _openChat(listen: true),
          child: Semantics(label: 'Jovi', hint: 'Opens Jovi', button: true, child: _core(136)),
        ),
        const SizedBox(width: 4),
        Expanded(
          child: Text(
            shown.isEmpty && (_loading || typing) ? (line.isEmpty ? 'Reading your day…' : ' ') : shown + (typing ? '|' : ''),
            maxLines: 5,
            overflow: TextOverflow.ellipsis,
            style: _serif(17, color: _coralSoft, w: FontWeight.w400).copyWith(height: 1.35, fontStyle: FontStyle.italic),
          ),
        ),
      ])),
      const SizedBox(height: 14),
      rise(_heroPill(), delay: 60),
      if (_map(_snap['todayTask']).isNotEmpty) const SizedBox(height: 14),
      rise(_askBar(), delay: 120),
      if (glances.isNotEmpty) ...<Widget>[
        const SizedBox(height: 14),
        SizedBox(
          height: 66,
          child: ListView.builder(
            scrollDirection: Axis.horizontal,
            physics: const BouncingScrollPhysics(),
            clipBehavior: Clip.none,
            itemCount: glances.length,
            itemBuilder: (BuildContext c, int i) => _glanceTile(glances[i], i, reduce),
          ),
        ),
      ],
      if (_s(_map(_snap['recall'])['text']).isNotEmpty) ...<Widget>[
        const SizedBox(height: 10),
        rise(Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
          const Icon(Icons.psychology_rounded, size: 13, color: _muted),
          const SizedBox(width: 6),
          Expanded(child: Text('You told me: ${_s(_map(_snap['recall'])['text'])}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _muted, fontSize: 12, fontStyle: FontStyle.italic))),
        ]), delay: 200),
      ],
    ]);
  }

  Widget _deck(BuildContext context) {
    if (_err.isNotEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Row(children: <Widget>[
          _core(96),
          const SizedBox(width: 14),
          Expanded(child: Text('Jovi couldn\'t load your records. $_err', style: const TextStyle(color: _muted, fontSize: 13, height: 1.4))),
          const SizedBox(width: 10),
          _btn('Try again', () => _load(first: true), accent: true),
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
          if (hasBrief) _btn(_briefPlaying ? 'Stop' : 'Listen to today\'s brief', _listenBrief, accent: true, icon: _briefPlaying ? Icons.stop_rounded : Icons.play_arrow_rounded),
          _btn(_voice.enabled ? 'Voice on' : 'Voice off', _toggleVoice, icon: _voice.enabled ? Icons.volume_up_rounded : Icons.volume_off_rounded),
        ],
      );
      final Widget left = Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
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
      ]);
      final Widget right = Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: <Widget>[
        // the deck sits under Home's own greeting, so hers is the headline: the brief's opening, or the day in numbers
        Text(_headline(), maxLines: 3, overflow: TextOverflow.ellipsis, style: _serif(wide ? 20 : 17, w: FontWeight.w500).copyWith(height: 1.35)),
        if (_s(_map(_snap['recall'])['text']).isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
              const Icon(Icons.psychology_rounded, size: 14, color: _muted),
              const SizedBox(width: 6),
              Expanded(child: Text('You told me: ${_s(_map(_snap['recall'])['text'])}', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _muted, fontSize: 12.5, fontStyle: FontStyle.italic, height: 1.4))),
            ]),
          ),
        const SizedBox(height: 12),
        _todayCard(),
        const SizedBox(height: 12),
        if (_chat.isNotEmpty) _chatBox(wide ? 240 : 200),
        if (_heard.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: Text(_heard, style: const TextStyle(color: _mint, fontSize: 12.5, fontStyle: FontStyle.italic))),
        const SizedBox(height: 10),
        _inputRow(),
        const SizedBox(height: 10),
        _chipsWrap(show: wide ? 7 : 4),
        const SizedBox(height: 12),
        _dock(),
        _emergencyLine(),
      ]);
      if (!wide) return Column(children: <Widget>[left, const SizedBox(height: 16), right, const SizedBox(height: 56)]);
      return Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
        SizedBox(width: coreSize + 44, child: left),
        const SizedBox(width: 20),
        Expanded(child: right),
      ]);
    });
  }

  Widget _bubble(Map<String, dynamic> m) {
    final String role = _s(m['role']);
    if (role == 'confirm') {
      final String st = _s(m['status']);
      final Map<String, dynamic> item = _map(m['item']);
      final Map<String, dynamic> p = _map(item['params']);
      final String kind = _s(item['kind']);
      String body = '';
      if (kind == 'book_appointment') body = '${_s(p['visitType'])} · ${_s(p['visitMode'])}${_s(p['clinic']).isNotEmpty ? ' · ' + _s(p['clinic']) : ''}\n${_day(_s(p['date']))} at ${_s(p['time'])}${_s(p['symptom']).isNotEmpty ? '\n"' + _s(p['symptom']) + '"' : ''}';
      else if (kind == 'support_ticket') body = _s(p['description']);
      else if (kind == 'log_vital') body = _s(p['systolic']).isNotEmpty && _n(p['systolic']) > 0 ? '${_s(p['type'])}: ${_s(p['systolic'])}/${_s(p['diastolic'])}' : '${_s(p['type'])}: ${_s(p['value'])}';
      return Container(
        margin: const EdgeInsets.symmetric(vertical: 6),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: _coral.withOpacity(.1), borderRadius: BorderRadius.circular(14), border: Border.all(color: _coral.withOpacity(st == 'done' ? .9 : .45))),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
          Text(_s(m['text']), style: const TextStyle(color: _coralSoft, fontWeight: FontWeight.w700, fontSize: 13)),
          if (body.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 6), child: Text(body, style: const TextStyle(color: _ivory, fontSize: 13, height: 1.4))),
          const SizedBox(height: 8),
          if (st.isEmpty && m['busy'] != true)
            Row(children: <Widget>[_btn('Cancel', () => _decide(m, 'cancel')), const SizedBox(width: 8), _btn('Confirm', () => _decide(m, 'confirm'), accent: true)])
          else if (m['busy'] == true)
            const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: _coral))
          else
            Text(st == 'done' ? 'Done. ' + _s(m['result']) : st == 'failed' ? 'Couldn\'t do it: ' + _s(m['result']) : 'Cancelled.', style: TextStyle(color: st == 'failed' ? _red : _muted, fontSize: 12.5)),
        ]),
      );
    }
    final bool me = role == 'me';
    final bool sys = role == 'sys';
    return Align(
      alignment: me ? Alignment.centerRight : Alignment.centerLeft,
      child: GestureDetector(
        onTap: sys && _s(m['route']).isNotEmpty ? () => _openPage(_s(m['route']), _s(m['text'])) : null,
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 4),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          constraints: const BoxConstraints(maxWidth: 420),
          decoration: BoxDecoration(
            color: me ? _coral : sys ? Colors.transparent : Colors.white.withOpacity(.08),
            borderRadius: BorderRadius.circular(14),
            border: sys ? null : Border.all(color: me ? _coral : Colors.white.withOpacity(.12)),
          ),
          child: Text(_s(m['text']), style: TextStyle(color: me ? _navyDeep : sys ? _muted : _ivory, fontSize: sys ? 12 : 13.5, height: 1.45, fontStyle: sys ? FontStyle.italic : FontStyle.normal)),
        ),
      ),
    );
  }

  // ---- panels
  Widget _briefCard() {
    final Map<String, dynamic> b = _map(_snap['brief']);
    final String text = _s(b['text']);
    return _card(
      title: 'Today\'s brief',
      trailing: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
        if (text.isNotEmpty) _btn(_briefPlaying ? 'Stop' : 'Listen', _listenBrief, accent: true, icon: _briefPlaying ? Icons.stop_rounded : Icons.play_arrow_rounded),
        const SizedBox(width: 6),
        _btn('', _briefBusy ? null : () => _makeBrief(true), icon: Icons.refresh_rounded),
      ]),
      child: _briefBusy || (text.isEmpty && _loading)
          ? const Padding(padding: EdgeInsets.symmetric(vertical: 10), child: Text('Jovi is reading your morning…', style: TextStyle(color: _muted, fontStyle: FontStyle.italic)))
          : Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
              Text(text.isEmpty ? 'No brief yet. Tap refresh and Jovi will write one.' : text, style: const TextStyle(color: _ivory, fontSize: 15.5, height: 1.55)),
              _alertsRow(),
            ]),
    );
  }

  Widget _apptsCard() {
    final List<Map<String, dynamic>> ups = _list(_snap['appointments']);
    final List<Map<String, dynamic>> past = _list(_snap['pastVisits']);
    final String today = _s(_snap['today']);
    return _card(
      title: 'Appointments',
      trailing: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[_btn('Book', () => _openPage('requests', 'Request care'), icon: Icons.add_rounded), const SizedBox(width: 6), _btn('Records', () => _openPage('careRecords', 'Care records'))]),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
        if (ups.isEmpty) const Text('Nothing booked. Say "book an urgent care visit" or "book a video visit for Tuesday morning".', style: TextStyle(color: _muted, fontSize: 13.5)),
        for (final Map<String, dynamic> a in ups)
          _row(
            title: '${_s(a['visitType'])}${a['pet'] == true ? ' · ' + _s(a['petName']) : ''}',
            d: '${_day(_s(a['date']))} · ${_s(a['time'])} · ${_s(a['visitMode']) == 'Virtual' ? 'video visit' : _s(a['clinic'])}${_s(a['provider']).isNotEmpty ? ' · ' + _s(a['provider']) : ''}',
            tag: _tag(_s(a['status']), bg: _s(a['status']) == 'confirmed' ? _mint : (_s(a['date']) == today ? _gold : null), fg: _s(a['status']) == 'confirmed' || _s(a['date']) == today ? _navyDeep : null),
            side: Column(crossAxisAlignment: CrossAxisAlignment.end, children: <Widget>[
              if (_s(a['telehealthUrl']).isNotEmpty) _btn('Join', () => launchUrl(Uri.parse(_s(a['telehealthUrl'])), mode: LaunchMode.externalApplication), accent: true, icon: Icons.videocam_rounded),
              if (_s(a['telehealthUrl']).isNotEmpty) const SizedBox(height: 4),
              _btn('Cancel', () => _confirm('cancel_appointment', <String, dynamic>{'requestId': _s(a['requestId']), 'reason': 'Cancelled from Jovi'}, 'Cancel the ${_s(a['visitType'])} on ${_day(_s(a['date']))} at ${_s(a['time'])}')),
            ]),
          ),
        if (past.isNotEmpty) ...<Widget>[
          const SizedBox(height: 10),
          const Text('RECENT', style: TextStyle(color: _muted, fontSize: 10, letterSpacing: 2, fontWeight: FontWeight.w700)),
          for (final Map<String, dynamic> a in past.take(4)) _row(title: _s(a['visitType']), d: '${_day(_s(a['date']))} · ${_title(_s(a['status']))}${_s(a['provider']).isNotEmpty ? ' · ' + _s(a['provider']) : ''}', side: _s(a['visitRecordId']).isNotEmpty ? _btn('Summary', () => _ask('Summarise my visit on ${_day(_s(a['date']))}')) : null),
        ],
      ]),
    );
  }

  Widget _medsCard() {
    final List<Map<String, dynamic>> meds = _list(_snap['medications']);
    final List<Map<String, dynamic>> rx = _list(_snap['prescriptions']);
    final List<Map<String, dynamic>> open = _list(_snap['openRefills']);
    final List<String> soon = _list(_snap['refillSoon']).map((Map<String, dynamic> p) => _s(p['prescriptionId'])).toList();
    return _card(
      title: 'Medications',
      trailing: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[_btn('Refills', () => _openPage('scriptRefill', 'Refills')), const SizedBox(width: 6), _btn('Interactions', () => _openPage('drugInteractions', 'Drug interactions'))]),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
        if (rx.isNotEmpty) const Text('PRESCRIBED BY JOVI', style: TextStyle(color: _muted, fontSize: 10, letterSpacing: 2, fontWeight: FontWeight.w700)),
        for (final Map<String, dynamic> p in rx)
          _row(
            title: '${_s(p['name'])} ${_s(p['dosage']).isNotEmpty ? _s(p['dosage']) : _s(p['strength'])}',
            d: '${_s(p['frequency'])}${_s(p['prescriber']).isNotEmpty ? ' · ' + _s(p['prescriber']) : ''} · ${_n(p['refillsRemaining']).toInt()} refill${_n(p['refillsRemaining']) == 1 ? '' : 's'} left${_s(p['nextRefill']).isNotEmpty ? ' · next ' + _day(_s(p['nextRefill'])) : ''}',
            tag: soon.contains(_s(p['prescriptionId'])) ? _tag(_n(p['refillsRemaining']) == 0 ? 'renew' : 'refill due', bg: _gold, fg: _navyDeep) : null,
            side: open.any((Map<String, dynamic> r) => _s(r['prescriptionId']) == _s(p['prescriptionId']))
                ? const Text('in progress', style: TextStyle(color: _mint, fontSize: 11.5))
                : _n(p['refillsRemaining']) > 0
                    ? _btn('Refill', () => _confirm('request_refill', <String, dynamic>{'prescriptionId': _s(p['prescriptionId'])}, 'Request a refill of ${_s(p['name'])}'), accent: soon.contains(_s(p['prescriptionId'])))
                    : _btn('Renew', () => _ask('Book a visit to renew ${_s(p['name'])}')),
          ),
        if (meds.isNotEmpty) Padding(padding: EdgeInsets.only(top: rx.isNotEmpty ? 12 : 0), child: const Text('MY LIST', style: TextStyle(color: _muted, fontSize: 10, letterSpacing: 2, fontWeight: FontWeight.w700))),
        for (final Map<String, dynamic> x in meds)
          _row(
            title: '${_s(x['name'])} ${_s(x['dosage']).isNotEmpty ? _s(x['dosage']) : _s(x['strength'])}',
            d: '${_s(x['frequency'])}${x['asNeeded'] == true ? ' · as needed' : ''}${_s(x['condition']).isNotEmpty ? ' · for ' + _s(x['condition']) : ''}',
            tag: _n(x['takenToday']) > 0 ? _tag(_n(x['perDay']) > 0 ? 'today ${_n(x['takenToday']).toInt()} of ${_n(x['perDay']).toInt()}' : 'taken today', bg: _n(x['perDay']) > 0 && _n(x['takenToday']) < _n(x['perDay']) ? _gold : _mint, fg: _navyDeep) : null,
            side: _btn('Taken', () => _confirm('log_dose', <String, dynamic>{'medicationId': _s(x['medicationId']), 'status': 'taken'}, 'Log ${_s(x['name'])} as taken'), accent: _n(x['perDay']) > 0 && _n(x['takenToday']) < _n(x['perDay'])),
          ),
        if (rx.isEmpty && meds.isEmpty) const Text('No medications on file. Say "add lisinopril 10 mg once a day" to keep your own list here.', style: TextStyle(color: _muted, fontSize: 13.5)),
      ]),
    );
  }

  Widget _claimsCard() {
    final List<Map<String, dynamic>> claims = <Map<String, dynamic>>[..._list(_snap['claims'])];
    for (final Map<String, dynamic> p in _list(_snap['pets'])) claims.addAll(_list(p['claims']));
    claims.sort((Map<String, dynamic> a, Map<String, dynamic> b) => _s(b['submittedAt'] ?? b['date']).compareTo(_s(a['submittedAt'] ?? a['date'])));
    Color? bg(String st) => st == 'paid' ? _mint : st == 'approved' ? _mint : (st == 'rejected' || st == 'denied') ? _red : (st == 'needs_more_info' || st == 'needs_info') ? _gold : null;
    return _card(
      title: 'Claims',
      trailing: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[_btn('File', () => _openPage('FileClaim', 'File a claim'), accent: true, icon: Icons.add_rounded), if (_list(_snap['pets']).isNotEmpty) const SizedBox(width: 6), if (_list(_snap['pets']).isNotEmpty) _btn('Pet claim', () => _openPage('petFileClaim', 'Pet claim'))]),
      child: claims.isEmpty
          ? const Text('No claims yet. File one with a photo of the receipt and Jovi will track it here.', style: TextStyle(color: _muted, fontSize: 13.5))
          : Column(children: <Widget>[
              for (final Map<String, dynamic> c in claims.take(12))
                _row(
                  title: '${_s(_map(c['pet'])['name']).isNotEmpty ? _s(_map(c['pet'])['name']) + ' · ' : ''}${_s(c['provider']).isNotEmpty ? _s(c['provider']) : _title(_s(c['type']))}',
                  d: '${_s(c['date']).isNotEmpty ? _day(_s(c['date'])) : 'undated'}${_s(c['reason']).isNotEmpty ? ' · ' + _s(c['reason']) : ''}${_s(c['rejectionReason']).isNotEmpty ? ' · ' + _s(c['rejectionReason']) : ''}',
                  tag: _tag(_title(_s(c['status'])).replaceAll('needs more info', 'needs info'), bg: bg(_s(c['status'])), fg: bg(_s(c['status'])) != null ? (bg(_s(c['status'])) == _red ? Colors.white : _navyDeep) : null),
                  side: Column(crossAxisAlignment: CrossAxisAlignment.end, children: <Widget>[
                    if (c['amount'] != null) Text(_money(c['amount']), style: const TextStyle(color: _ivory, fontWeight: FontWeight.w700)),
                    if (c['paidAmount'] != null) Text('paid ${_money(c['paidAmount'])}', style: const TextStyle(color: _mint, fontSize: 11.5)),
                  ]),
                ),
            ]),
    );
  }

  Widget _billingCard() {
    final Map<String, dynamic> b = _map(_snap['billing']);
    final Map<String, dynamic> m = _map(_snap['member']);
    final num ded = _n(b['deductible']);
    final num paid = _n(b['deductiblePaid']);
    final double pct = ded > 0 ? math.min(1, paid / ded) : 0;
    return _card(
      title: 'Billing',
      trailing: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[_btn('Invoices', () => _openPage('invoices', 'Invoices')), const SizedBox(width: 6), _btn('Card', () => _openPage('DigitalMembershipCard', 'Membership card'))]),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
        Row(children: <Widget>[
          _stat(b['premium'] != null ? _money(b['premium']) : '–', 'a month'),
          _stat(_s(b['nextBilling']).isNotEmpty ? _day(_s(b['nextBilling'])).split(', ').last : '–', 'next charge'),
          _stat(_title(_s(b['status']).isEmpty ? 'active' : _s(b['status'])), b['pastDue'] == true ? 'past due' : 'membership', color: b['pastDue'] == true ? _red : _mint),
        ]),
        const SizedBox(height: 10),
        Text('${_s(m['planType'])}${_s(m['planTier']).isNotEmpty ? ' · ' + _s(m['planTier']) : ''}${m['dental'] == true ? ' · dental' : ''}${m['vision'] == true ? ' · vision' : ''}${m['petInsurance'] == true ? ' · pets' : ''}${_s(b['payment']).isNotEmpty ? ' · ' + _s(b['payment']) : ''}', style: const TextStyle(color: _muted, fontSize: 12.5)),
        if (ded > 0) ...<Widget>[
          const SizedBox(height: 10),
          ClipRRect(borderRadius: BorderRadius.circular(999), child: LinearProgressIndicator(value: pct, minHeight: 8, backgroundColor: Colors.black.withOpacity(.25), color: _coral)),
          const SizedBox(height: 6),
          Text('${_money(paid)} of your ${_money(ded)} deductible met · ${_money(math.max(0, ded - paid))} to go', style: const TextStyle(color: _muted, fontSize: 12.5)),
        ],
        if (b['pastDue'] == true) Padding(padding: const EdgeInsets.only(top: 10), child: Text('The last charge didn\'t go through${_s(b['lastChargeError']).isNotEmpty ? ' (' + _s(b['lastChargeError']) + ')' : ''}. Update your payment method in your profile.', style: const TextStyle(color: _coralSoft, fontSize: 13))),
        for (final Map<String, dynamic> i in _list(b['invoices']).take(4)) _row(title: '${_s(i['number']).isNotEmpty ? _s(i['number']) : 'Invoice'}${_s(i['period']).isNotEmpty ? ' · ' + _s(i['period']) : ''}', d: _s(i['issuedAt']).isNotEmpty ? _day(_s(i['issuedAt'])) : '', tag: _tag(_s(i['status']), bg: _s(i['status']) == 'paid' ? _mint : (_s(i['status']) == 'failed' || _s(i['status']) == 'returned') ? _red : null, fg: _s(i['status']) == 'paid' ? _navyDeep : (_s(i['status']) == 'failed' || _s(i['status']) == 'returned') ? Colors.white : null), side: i['total'] != null ? Text(_money(i['total']), style: const TextStyle(color: _ivory, fontWeight: FontWeight.w700)) : null),
      ]),
    );
  }

  Widget _petsCard() {
    final List<Map<String, dynamic>> pets = _list(_snap['pets']);
    return _card(
      title: 'Pets',
      trailing: _btn('Profiles', () => _openPage('petPro', 'Pets')),
      child: pets.isEmpty
          ? const Text('No pets on the plan yet. Add one in the app and Jovi will track their meds, doses, vaccines and claims.', style: TextStyle(color: _muted, fontSize: 13.5))
          : Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
              for (final Map<String, dynamic> p in pets) ...<Widget>[
                Padding(
                  padding: const EdgeInsets.only(top: 8, bottom: 2),
                  child: Row(children: <Widget>[
                    const Icon(Icons.pets_rounded, size: 15, color: _coralSoft),
                    const SizedBox(width: 6),
                    Expanded(child: Text('${_s(p['name'])} · ${_s(p['type'])}${_s(p['breed']).isNotEmpty ? ' · ' + _s(p['breed']) : ''}${_s(p['age']).isNotEmpty ? ' · ' + _s(p['age']) : ''}', style: const TextStyle(color: _ivory, fontWeight: FontWeight.w700, fontSize: 14))),
                    if (_strs(p['lowStock']).isNotEmpty) _tag('low on ${_strs(p['lowStock']).first}', bg: _gold, fg: _navyDeep),
                  ]),
                ),
                for (final Map<String, dynamic> d in _list(p['dosesToday']))
                  _row(
                    title: _s(d['name']),
                    d: '${_clock(_s(d['at']))} · ${_s(d['status'])}',
                    tag: _s(d['status']) == 'taken' ? _tag('taken', bg: _mint, fg: _navyDeep) : (_s(d['status']) == 'late' ? _tag('late', bg: _gold, fg: _navyDeep) : null),
                    side: _s(d['status']) == 'scheduled' || _s(d['status']) == 'late'
                        ? Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
                            _btn('Taken', () => _confirm('log_dose', <String, dynamic>{'petId': _s(p['petId']), 'medicationId': _s(d['medicationId']), 'status': 'taken'}, 'Log ${_s(d['name'])} for ${_s(p['name'])} as taken'), accent: true),
                            const SizedBox(width: 6),
                            _btn('Skip', () => _confirm('log_dose', <String, dynamic>{'petId': _s(p['petId']), 'medicationId': _s(d['medicationId']), 'status': 'skipped'}, 'Log ${_s(d['name'])} for ${_s(p['name'])} as skipped')),
                          ])
                        : null,
                  ),
                if (_list(p['dosesToday']).isEmpty && _list(p['medications']).isNotEmpty)
                  for (final Map<String, dynamic> mm in _list(p['medications']).take(4)) _row(title: '${_s(mm['name'])} ${_s(mm['dosage']).isNotEmpty ? _s(mm['dosage']) : _s(mm['strength'])}', d: _strs(mm['times']).isNotEmpty ? 'at ' + _strs(mm['times']).join(', ') : (mm['asNeeded'] == true ? 'as needed' : ''), side: _btn('Taken', () => _confirm('log_dose', <String, dynamic>{'petId': _s(p['petId']), 'medicationId': _s(mm['medicationId']), 'status': 'taken'}, 'Log ${_s(mm['name'])} for ${_s(p['name'])} as taken'))),
                for (final Map<String, dynamic> v in _list(p['vaccinesDue'])) _row(title: '${_s(v['name'])} due', d: _day(_s(v['expires'])), tag: _tag('vaccine', bg: _gold, fg: _navyDeep), side: _btn('Book', () => _ask('Book a wellness visit for ${_s(p['name'])}'))),
              ],
            ]),
    );
  }

  Widget _vitalsCard() {
    final Map<String, dynamic> v = _map(_snap['vitals']);
    final List<Map<String, dynamic>> latest = _list(v['latest']);
    String val(Map<String, dynamic> r) => r['systolic'] != null && _n(r['systolic']) > 0 ? '${_n(r['systolic']).toInt()}/${_n(r['diastolic']).toInt()}' : (_n(r['value']) == _n(r['value']).roundToDouble() ? '${_n(r['value']).toInt()}' : _n(r['value']).toStringAsFixed(1));
    return _card(
      title: 'Vitals',
      sub: 'Say "log my blood pressure 120 over 80" or "log my weight 172".',
      trailing: _btn('All', () => _openPage('Vitals', 'Vitals')),
      child: latest.isEmpty
          ? Wrap(spacing: 8, runSpacing: 8, children: <Widget>[for (final String t in <String>['Weight', 'Blood pressure', 'Heart rate', 'Blood glucose']) _btn('Log $t', () => _ask('Log my ${t.toLowerCase()}'))])
          : Column(children: <Widget>[
              for (final Map<String, dynamic> r in latest) _row(title: _s(r['type']), d: _when(_s(r['at'])), side: Text('${val(r)} ${_s(r['unit'])}', style: const TextStyle(color: _ivory, fontWeight: FontWeight.w700, fontSize: 15))),
              const SizedBox(height: 8),
              Wrap(spacing: 8, runSpacing: 8, children: <Widget>[_btn('Log weight', () => _ask('Log my weight')), _btn('Log blood pressure', () => _ask('Log my blood pressure'))]),
            ]),
    );
  }

  Widget _vaccinesCard() {
    final List<Map<String, dynamic>> vax = _list(_snap['vaccines']);
    final List<Map<String, dynamic>> due = vax.where((Map<String, dynamic> x) => x['due'] == true).toList();
    return _card(
      title: 'Vaccines',
      trailing: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[_btn('Mine', () => _openPage('vaccinations', 'Vaccinations')), if (_list(_snap['pets']).isNotEmpty) const SizedBox(width: 6), if (_list(_snap['pets']).isNotEmpty) _btn('Pets', () => _openPage('petVaccinations', 'Pet vaccinations'))]),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
        if (due.isEmpty) Text(vax.isEmpty ? 'No vaccinations on record yet.' : 'Nothing due in the next 60 days.', style: const TextStyle(color: _muted, fontSize: 13.5)),
        for (final Map<String, dynamic> x in due) _row(title: '${_s(x['name'])} for ${_s(x['patient'])}', d: '${x['overdue'] == true ? 'Overdue since ' : 'Due by '}${_day(_s(x['expires']))}', tag: _tag(x['overdue'] == true ? 'overdue' : 'due', bg: x['overdue'] == true ? _red : _gold, fg: x['overdue'] == true ? Colors.white : _navyDeep), side: _btn('Book', () => _ask('Book a wellness visit for the ${_s(x['name'])} booster'))),
        for (final Map<String, dynamic> p in _list(_snap['pets']))
          for (final Map<String, dynamic> x in _list(p['vaccinesDue'])) _row(title: '${_s(x['name'])} for ${_s(p['name'])}', d: 'Due by ${_day(_s(x['expires']))}', tag: _tag('pet', bg: _gold, fg: _navyDeep), side: _btn('Book', () => _ask('Book a wellness visit for ${_s(p['name'])}'))),
        if (vax.isNotEmpty && due.isEmpty) ...<Widget>[
          const SizedBox(height: 6),
          for (final Map<String, dynamic> x in vax.take(6)) _row(title: '${_s(x['name'])}${_s(x['dose']).isNotEmpty ? ' · ' + _s(x['dose']) : ''}', d: '${_s(x['patient'])}${_s(x['given']).isNotEmpty ? ' · given ' + _day(_s(x['given'])) : ''}${_s(x['expires']).isNotEmpty ? ' · good through ' + _day(_s(x['expires'])) : ''}'),
        ],
      ]),
    );
  }

  Widget _weatherCard() {
    final Map<String, dynamic> w = _map(_snap['weather']);
    final Map<String, dynamic> cur = _map(w['current']);
    final Map<String, dynamic> d = _map(w['daily']);
    final Map<String, dynamic> air = _map(w['air']);
    final String place = _s(_snap['place']).split(',').first;
    final List<dynamic> days = d['time'] is List ? d['time'] as List<dynamic> : <dynamic>[];
    final num aqi = _n(air['aqi']);
    final Color aqiColor = aqi <= 50 ? _mint : aqi <= 100 ? _gold : _coral;
    return _card(
      title: 'Air & weather',
      trailing: place.isNotEmpty ? _tag(place) : null,
      child: cur.isEmpty
          ? const Text('Add your city to your profile and Jovi will watch the air and the sky for you.', style: TextStyle(color: _muted, fontSize: 13))
          : Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
              Row(crossAxisAlignment: CrossAxisAlignment.end, children: <Widget>[
                Text('${_n(cur['temperature_2m']).round()}°', style: _serif(44)),
                const SizedBox(width: 12),
                Expanded(child: Text('${_wmo(cur['weather_code'])}\nfeels ${_n(cur['apparent_temperature']).round()}° · humidity ${_n(cur['relative_humidity_2m']).round()}%', style: const TextStyle(color: _muted, fontSize: 12.5, height: 1.4))),
              ]),
              const SizedBox(height: 10),
              Row(children: <Widget>[
                _stat(air['aqi'] == null ? '–' : '${aqi.toInt()}', _s(air['label']).isEmpty ? 'air quality' : 'air · ${_s(air['label'])}', color: air['aqi'] == null ? null : aqiColor),
                _stat(cur['uv_index'] == null ? '–' : '${_n(cur['uv_index']).toStringAsFixed(0)}', 'UV index', color: _n(cur['uv_index']) >= 6 ? _coral : null),
              ]),
              const SizedBox(height: 10),
              Row(children: <Widget>[
                for (int i = 1; i < math.min(6, days.length); i++)
                  Expanded(
                    child: Column(children: <Widget>[
                      Text(_day(_s(days[i])).split(',').first, style: const TextStyle(color: _ivory, fontSize: 11.5, fontWeight: FontWeight.w700)),
                      Icon(_wmoIcon((d['weather_code'] as List<dynamic>)[i]), size: 18, color: _coralSoft),
                      Text('${_n((d['temperature_2m_max'] as List<dynamic>)[i]).round()}°/${_n((d['temperature_2m_min'] as List<dynamic>)[i]).round()}°', style: const TextStyle(color: _muted, fontSize: 11)),
                    ]),
                  ),
              ]),
              for (final Map<String, dynamic> a in _list(w['nws'])) Padding(padding: const EdgeInsets.only(top: 8), child: Text('⚠ ${_s(a['headline']).isEmpty ? _s(a['event']) : _s(a['headline'])}', style: const TextStyle(color: _coralSoft, fontSize: 12))),
            ]),
    );
  }

  Widget _remindersCard() {
    final List<Map<String, dynamic>> list = _list(_snap['reminders']);
    final String now = DateTime.now().toUtc().toIso8601String();
    return _card(
      title: 'Reminders',
      sub: 'Say "remind me to take my meds at 8", or add one here. They reach your phone as a notification.',
      child: Column(children: <Widget>[
        Row(children: <Widget>[
          Expanded(
            child: TextField(
              controller: _remText,
              style: const TextStyle(color: _ivory, fontSize: 13.5),
              decoration: InputDecoration(hintText: 'What should I remind you of?', hintStyle: const TextStyle(color: _muted, fontSize: 13), isDense: true, filled: true, fillColor: Colors.black.withOpacity(.3), contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10), border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: _coral.withOpacity(.35)))),
            ),
          ),
          const SizedBox(width: 8),
          _btn(_remWhen == null ? 'When' : _when(_remWhen!.toIso8601String()), () async {
            final DateTime now = DateTime.now();
            final DateTime? d = await showDatePicker(context: context, initialDate: now, firstDate: now, lastDate: now.add(const Duration(days: 730)));
            if (d == null || !mounted) return;
            final TimeOfDay? t = await showTimePicker(context: context, initialTime: const TimeOfDay(hour: 9, minute: 0));
            if (t == null) return;
            setState(() => _remWhen = DateTime(d.year, d.month, d.day, t.hour, t.minute));
          }),
          const SizedBox(width: 6),
          _btn('Add', () {
            if (_remText.text.trim().isEmpty || _remWhen == null) {
              _addMsg('sys', 'Give the reminder a text and a time.');
              return;
            }
            final DateTime w = _remWhen!;
            final String local = '${w.year}-${w.month.toString().padLeft(2, '0')}-${w.day.toString().padLeft(2, '0')}T${w.hour.toString().padLeft(2, '0')}:${w.minute.toString().padLeft(2, '0')}';
            _remPost(<String, dynamic>{'text': _remText.text.trim(), 'when': local});
            _remText.clear();
            setState(() => _remWhen = null);
          }, accent: true),
        ]),
        if (list.isEmpty) const Padding(padding: EdgeInsets.only(top: 10), child: Text('No reminders set.', style: TextStyle(color: _muted, fontSize: 13))),
        for (final Map<String, dynamic> r in list.take(12))
          _row(
            title: _s(r['text']),
            d: _when(_s(r['at'])) + (_s(r['repeat']).isNotEmpty && _s(r['repeat']) != 'none' ? ' · ${_s(r['repeat'])}' : ''),
            tag: _s(r['at']).compareTo(now) <= 0 ? _tag('due', bg: _mint, fg: _navyDeep) : null,
            side: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[_btn('Done', () => _remPost(<String, dynamic>{'done': _s(r['id'])})), const SizedBox(width: 6), _btn('✕', () => _remPost(<String, dynamic>{'remove': _s(r['id'])}))]),
          ),
      ]),
    );
  }

  Widget _memoryCard() {
    final List<Map<String, dynamic>> mem = _list(_snap['memory']);
    return _card(
      title: 'Jovi remembers',
      sub: 'Say "remember that…" and it lands here. Nothing here leaves your account.',
      child: mem.isEmpty
          ? const Text('Nothing remembered yet.', style: TextStyle(color: _muted, fontSize: 13))
          : Column(children: mem.map((Map<String, dynamic> m) => _row(title: _s(m['text']), side: _btn('✕', () => _forget(_s(m['id']))))).toList()),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (widget.layout == 'hero') return _hero(context);
    if (widget.layout == 'deck') return _deck(context);
    final List<Widget> left = <Widget>[_console(), _todayCard(), const SizedBox(height: 14), _briefCard(), _apptsCard(), _medsCard()];
    final List<Widget> right = <Widget>[
      _claimsCard(),
      _billingCard(),
      if (_list(_snap['pets']).isNotEmpty) _petsCard(),
      _vitalsCard(),
      _vaccinesCard(),
      _weatherCard(),
      _remindersCard(),
      _memoryCard(),
      _focusCard(),
      _radioCard(),
    ];
    Widget body;
    if (_err.isNotEmpty) {
      body = Padding(padding: const EdgeInsets.all(24), child: Column(mainAxisSize: MainAxisSize.min, children: <Widget>[Text('Jovi couldn\'t load your records.', style: _serif(22)), const SizedBox(height: 8), Text(_err, style: const TextStyle(color: _muted, fontSize: 13)), const SizedBox(height: 14), _btn('Try again', () => _load(first: true), accent: true)]));
    } else {
      body = LayoutBuilder(builder: (BuildContext c, BoxConstraints box) {
        final bool wide = box.maxWidth >= 900;
        return SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 28),
          child: wide
              ? Row(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
                  Expanded(flex: 8, child: Column(children: left)),
                  const SizedBox(width: 14),
                  Expanded(flex: 5, child: Column(children: right)),
                ])
              : Column(children: <Widget>[...left, ...right]),
        );
      });
    }
    return Container(
      width: widget.width,
      height: widget.height,
      decoration: const BoxDecoration(
        gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: <Color>[Color(0xFF0B1426), _navyDeep, _navy]),
        borderRadius: BorderRadius.all(Radius.circular(22)),
      ),
      clipBehavior: Clip.antiAlias,
      child: _loading && _snap.isEmpty && _err.isEmpty
          ? const Center(child: SizedBox(width: 26, height: 26, child: CircularProgressIndicator(strokeWidth: 2, color: _coral)))
          : body,
    );
  }
}

// a dock sheet shows one of the panels; the panel reads the parent's state, and the parent's
// setState does not reach a sheet on another route, so a light poll keeps it fresh
class _SheetHost extends StatefulWidget {
  const _SheetHost({required this.build});
  final Widget Function() build;
  @override
  State<_SheetHost> createState() => _SheetHostState();
}

class _SheetHostState extends State<_SheetHost> {
  Timer? _t;
  @override
  void initState() {
    super.initState();
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
// END OF FILE - JC-JOVI-NATIVE-1013-001
