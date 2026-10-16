"""Call screen v3 (JC-LAZO-CALLS-1016-APP-003): Jesse's production fixes.
Reads lazo_call_screen.dart.txt (v2), keeps it as lazo_call_screen_v2.dart.txt, writes v3 in place.
    python app-patches\\patch_call_screen_v3.py
 1. vendor header on phones: the name on its own line, the camera control on a second row
 2. "Show / Hide video" only once the couple's video exists
 3. the five call buttons stay on one row on phones (short labels: Report, Start video ...)
 4. the couple's locked camera explained, and a notice when it's allowed
 5. every call-service request times out (12 s) and the media queue skips a stuck step (20 s): LzCallQueue
 7. the watermark is bigger and sparser on wide tiles
"""
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
P = HERE / 'lazo_call_screen.dart.txt'
KEEP = HERE / 'lazo_call_screen_v2.dart.txt'
if not KEEP.exists():
    shutil.copy(P, KEEP)
s = KEEP.read_text(encoding='utf-8')


def rep(a, b):
    global s
    c = s.count(a)
    assert c == 1, (a[:80], c)
    s = s.replace(a, b)


# ---- 5. a queue that can't stall, public so test/call_queue_test.dart can check it
rep("""class _LazoCallScreen extends StatefulWidget {""", """/// One-at-a-time queue for the call's media steps (JC-LAZO-CALLS-1016-APP-003).
/// A step that never finishes - a request the network swallowed - is given up
/// after [limit], so the steps behind it (later video, a reconnect) still run.
class LzCallQueue {
  LzCallQueue({this.limit = const Duration(seconds: 20)});
  final Duration limit;
  Future<void> _chain = Future<void>.value();

  Future<T> run<T>(Future<T> Function() step) {
    final Completer<T> c = Completer<T>();
    _chain = _chain.then((_) async {
      try {
        c.complete(await step().timeout(limit));
      } catch (e, st) {
        c.completeError(e, st);
      }
    });
    return c.future;
  }
}

class _LazoCallScreen extends StatefulWidget {""")
rep("""  Timer? _poll;
  Future<void> _chain = Future<void>.value();
""", """  Timer? _poll;
  final LzCallQueue _queue = LzCallQueue();
  bool _wasAllowed = false;
  String _notice = '';
  Timer? _noticeT;
""")
rep("""  Future<T> _serial<T>(Future<T> Function() f) {
    final Completer<T> c = Completer<T>();
    _chain = _chain.then((_) async {
      try {
        c.complete(await f());
      } catch (e, st) {
        c.completeError(e, st);
      }
    });
    return c.future;
  }""", """  Future<T> _serial<T>(Future<T> Function() f) => _queue.run<T>(f);""")
rep("""    final String b = jsonEncode(body ?? <String, dynamic>{});
    final httpc.Response r = method == 'PUT'
        ? await httpc.put(u, headers: h, body: b)
        : await httpc.post(u, headers: h, body: b);
    Map<String, dynamic> data = <String, dynamic>{};""", """    final String b = jsonEncode(body ?? <String, dynamic>{});
    final httpc.Response r;
    try {
      r = await (method == 'PUT'
              ? httpc.put(u, headers: h, body: b)
              : httpc.post(u, headers: h, body: b))
          .timeout(const Duration(seconds: 12));
    } catch (_) {
      return <String, dynamic>{'_status': 0, 'error': 'timeout'}; // no answer: callers treat it as a failure and retry
    }
    Map<String, dynamic> data = <String, dynamic>{};""")
rep("""  void dispose() {
    _poll?.cancel();
    _lvl?.cancel();""", """  void dispose() {
    _poll?.cancel();
    _lvl?.cancel();
    _noticeT?.cancel();""")
# _tick: the queue can now throw (a step timed out) - keep polling
rep("""    await _serial(() => _sync(osid, tracks));
  }""", """    try {
      await _serial(() => _sync(osid, tracks));
    } catch (_) {} // a stuck step was given up; the next tick tries again
  }""")
# _cameraOn / _cameraOff: a timed-out step is a failed step
rep("""    final bool ok = await _serial(() async {""", """    bool ok = false;
    try {
      ok = await _serial(() async {""")
rep("""      await _pc!.setRemoteDescription(
          RTCSessionDescription(sd['sdp'] as String, sd['type'] as String));
      return true;
    });
    if (!ok) {""", """      await _pc!.setRemoteDescription(
          RTCSessionDescription(sd['sdp'] as String, sd['type'] as String));
      return true;
    });
    } catch (_) {
      ok = false;
    }
    if (!ok) {""")
rep("""    if (!serverClosed && mid != null) {
      await _serial(() => _rt('PUT', 'sessions/$_sid/tracks/close', <String, dynamic>{""", """    if (!serverClosed && mid != null) {
      await _serial(() => _rt('PUT', 'sessions/$_sid/tracks/close', <String, dynamic>{""")
rep("""            'force': true,
          }));
    }
    _videoMid = null;""", """            'force': true,
          })).catchError((Object _) => <String, dynamic>{});
    }
    _videoMid = null;""")
# 4. notice when the vendor allows the couple's camera
rep("""    final bool allowed = v['camAllowed'] == true;""", """    final bool allowed = v['camAllowed'] == true;
    if (!_isVendor && allowed && !_wasAllowed && !_camOn) {
      _noticeT?.cancel();
      _set(() => _notice = 'You can turn your camera on now.');
      _noticeT = Timer(const Duration(seconds: 6), () => _set(() => _notice = ''));
    }
    _wasAllowed = allowed;""")

# ---- 7. watermark: bigger and sparser on wide tiles
rep("""        final int rows = (b.maxHeight / 70).ceil().clamp(1, 24);""", """        final bool big = b.maxWidth > 520;
        final double gap = big ? 120 : 70;
        final int rows = (b.maxHeight / gap).ceil().clamp(1, 24);""")
rep("""                top: i * 70.0 + 16,
                left: i.isEven ? 0 : -70,""", """                top: i * gap + 16,
                left: i.isEven ? 0 : (big ? -140 : -70),""")
rep("""                  child: Text('$line      $line',
                      softWrap: false,
                      style: TextStyle(
                          color: Colors.white.withOpacity(0.30),
                          fontSize: 12,""", """                  child: Text(big ? '$line            $line' : '$line      $line',
                      softWrap: false,
                      style: TextStyle(
                          color: Colors.white.withOpacity(0.30),
                          fontSize: big ? 16 : 12,""")

# ---- 3. buttons: compact, flexible, labels never wrap
rep("""  Widget _btn(IconData icon, String label, VoidCallback? onTap,
      {Color? bg, Color fg = Colors.white}) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 5),
      child: Column(mainAxisSize: MainAxisSize.min, children: <Widget>[""", """  Widget _btn(IconData icon, String label, VoidCallback? onTap,
      {Color? bg, Color fg = Colors.white}) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 3),
      child: Column(mainAxisSize: MainAxisSize.min, children: <Widget>[""")
rep("""        const SizedBox(height: 5),
        Text(label,
            style: TextStyle(color: Colors.white.withOpacity(.85), fontSize: 11)),
      ]),""", """        const SizedBox(height: 5),
        FittedBox(
          fit: BoxFit.scaleDown,
          child: Text(label,
              maxLines: 1,
              style: TextStyle(color: Colors.white.withOpacity(.85), fontSize: 11)),
        ),
      ]),""")

# ---- 1 + 4 + 2 + 3: header, hints, controls
rep("""            Row(children: <Widget>[
              const Icon(Icons.verified_user_rounded, color: Color(0xFFD4B37A), size: 18),
              const SizedBox(width: 8),
              Expanded(
                child: Text('Lazo video call · ${widget.otherName}',
                    style: const TextStyle(
                        color: Colors.white, fontSize: 15, fontWeight: FontWeight.w700)),
              ),
              if (_isVendor && _coupleAudioOnly && !_coupleCamAllowed)""", """            _header(wide),
            if (_notice.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                  decoration: BoxDecoration(
                      color: const Color(0xFFD4B37A), borderRadius: BorderRadius.circular(999)),
                  child: Text(_notice,
                      style: const TextStyle(color: Color(0xFF241E2B), fontSize: 13, fontWeight: FontWeight.w700)),
                ),
              ),
            if (_status.isEmpty && !_isVendor && !_camAllowed && !_camOn && !_coupleAudioOnly)
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Text('${widget.otherName} turns your camera on when they\\u2019re ready.',
                    style: TextStyle(color: Colors.white.withOpacity(.75), fontSize: 12.5)),
              ),""")
rep("""                  label: Text(
                      _coupleCamAllowed ? 'Their camera: allowed' : 'Let them use camera',
                      style: const TextStyle(color: Color(0xFFD4B37A), fontSize: 12.5)),
                ),
            ]),
            if (_status.isNotEmpty)""", """            if (_status.isNotEmpty)""")
rep("""            Wrap(alignment: WrapAlignment.center, runSpacing: 8, children: <Widget>[
              _btn(_micOn ? Icons.mic_rounded : Icons.mic_off_rounded,
                  _micOn ? 'Mute' : 'Unmute', _toggleMic),
              _btn(_camOn ? Icons.videocam_rounded : Icons.videocam_off_rounded,
                  _camOn ? 'Camera off' : (!_isVendor && !_camAllowed ? 'Camera locked' : 'Camera on'),
                  (!_isVendor && !_camAllowed && !_camOn)
                      ? null
                      : () => _camOn ? _cameraOff() : _cameraOn()),
              if (!_isVendor)
                _btn(Icons.headset_rounded, _coupleAudioOnly ? 'Audio only \\u2713' : 'Audio only',
                    () => _setAudioPref(!_coupleAudioOnly),
                    bg: _coupleAudioOnly ? const Color(0xFF52284F) : null),
              if (_isVendor)
                _btn(_hidden || !_revealed ? Icons.visibility_off_rounded : Icons.visibility_rounded,
                    _hidden || !_revealed ? 'Their video hidden' : 'Hide their video',
                    () => _set(() {
                          if (!_revealed) {
                            _revealed = true;
                            _hidden = false;
                          } else {
                            _hidden = !_hidden;
                          }
                        })),
              _btn(Icons.call_end_rounded, 'Leave', () => _leave(),
                  bg: const Color(0xFFB3261E)),
              if (_isVendor && widget.onReport != null)
                _btn(Icons.flag_rounded, 'Leave + report', () => _leave(report: true),
                    bg: const Color(0xFF6E1A14)),
            ]),""", """            Row(mainAxisAlignment: MainAxisAlignment.center, children: <Widget>[
              for (final Widget b in <Widget>[
                _btn(_micOn ? Icons.mic_rounded : Icons.mic_off_rounded,
                    _micOn ? 'Mute' : 'Unmute', _toggleMic),
                _btn(_camOn ? Icons.videocam_rounded : Icons.videocam_off_rounded,
                    _camOn ? 'Stop video' : (!_isVendor && !_camAllowed ? 'Locked' : 'Start video'),
                    (!_isVendor && !_camAllowed && !_camOn)
                        ? null
                        : () => _camOn ? _cameraOff() : _cameraOn()),
                if (!_isVendor)
                  _btn(Icons.headset_rounded, _coupleAudioOnly ? 'Audio only \\u2713' : 'Audio only',
                      () => _setAudioPref(!_coupleAudioOnly),
                      bg: _coupleAudioOnly ? const Color(0xFF52284F) : null),
                if (_isVendor && _remoteVideo)
                  _btn(_hidden || !_revealed ? Icons.visibility_rounded : Icons.visibility_off_rounded,
                      _hidden || !_revealed ? 'Show video' : 'Hide video',
                      () => _set(() {
                            if (!_revealed) {
                              _revealed = true;
                              _hidden = false;
                            } else {
                              _hidden = !_hidden;
                            }
                          })),
                _btn(Icons.call_end_rounded, 'Leave', () => _leave(),
                    bg: const Color(0xFFB3261E)),
                if (_isVendor && widget.onReport != null)
                  _btn(Icons.flag_rounded, 'Report', () => _leave(report: true),
                      bg: const Color(0xFF6E1A14)),
              ])
                Flexible(child: b),
            ]),""")

# the header itself: one row on wide screens, two rows on phones
rep("""  Widget _btn(IconData icon, String label, VoidCallback? onTap,""", """  Widget _header(bool wide) {
    final Widget title = Row(children: <Widget>[
      const Icon(Icons.verified_user_rounded, color: Color(0xFFD4B37A), size: 18),
      const SizedBox(width: 8),
      Expanded(
        child: Text(wide ? 'Lazo video call \\u00b7 ${widget.otherName}' : widget.otherName,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w700)),
      ),
    ]);
    Widget? control;
    if (_isVendor && _coupleAudioOnly && !_coupleCamAllowed) {
      control = Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
            color: Colors.white.withOpacity(.08), borderRadius: BorderRadius.circular(999)),
        child: const Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
          Icon(Icons.headset_rounded, color: Color(0xFFD4B37A), size: 16),
          SizedBox(width: 6),
          Text('Prefers audio only', style: TextStyle(color: Color(0xFFD4B37A), fontSize: 12.5)),
        ]),
      );
    } else if (_isVendor) {
      control = TextButton.icon(
        onPressed: () => _allowCouple(!_coupleCamAllowed),
        style: TextButton.styleFrom(padding: const EdgeInsets.symmetric(horizontal: 8)),
        icon: Icon(_coupleCamAllowed ? Icons.videocam_rounded : Icons.videocam_off_rounded,
            color: const Color(0xFFD4B37A), size: 18),
        label: Text(_coupleCamAllowed ? 'Their camera: allowed' : 'Let them use camera',
            style: const TextStyle(color: Color(0xFFD4B37A), fontSize: 12.5)),
      );
    }
    if (control == null) return title;
    if (wide) return Row(children: <Widget>[Expanded(child: title), control]);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: <Widget>[
      title,
      Padding(padding: const EdgeInsets.only(top: 4, left: 18), child: control),
    ]);
  }

  Widget _btn(IconData icon, String label, VoidCallback? onTap,""")
rep("""//   - (v2, JC-LAZO-CALLSCHED-1016)""", """//   - (v3, JC-LAZO-CALLS-1016-APP-003: phone header on two rows, five buttons on
//     one row, Show/Hide video only once there is video, the couple's locked-
//     camera hint, timeouts on every request + a queue that can't stall,
//     a bigger watermark on wide tiles)
//   - (v2, JC-LAZO-CALLSCHED-1016)""")
# the old one-row header's chip / camera button, now drawn by _header()
_hint = s.index("turns your camera on when they")
_a = s.index("                Container(\n                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),", _hint)
_b = s.index("            if (_status.isNotEmpty)", _a)
assert _b - _a < 1500, 'leftover block looks wrong'
s = s[:_a] + s[_b:]

P.write_text(s, encoding='utf-8')
print('call screen v3 written')
