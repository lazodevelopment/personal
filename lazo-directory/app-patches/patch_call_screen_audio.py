"""Call screen v2 (JC-LAZO-CALLSCHED-1016-APP): audio only made obvious.
Edits app-patches/lazo_call_screen.dart.txt in place (the v165 copy is kept as lazo_call_screen_v165.dart.txt).
    python app-patches\\patch_call_screen_audio.py
"""
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
P = HERE / 'lazo_call_screen.dart.txt'
KEEP = HERE / 'lazo_call_screen_v165.dart.txt'
if not KEEP.exists():
    shutil.copy(P, KEEP)
s = KEEP.read_text(encoding='utf-8')


def rep(a, b):
    global s
    c = s.count(a)
    assert c == 1, (a[:70], c)
    s = s.replace(a, b)


rep("""//   - one tap to leave, and for vendors one tap to leave and report.""", """//   - one tap to leave, and for vendors one tap to leave and report.
//   - (v2, JC-LAZO-CALLSCHED-1016) audio only made obvious: with no camera on,
//     both people show as avatars with a speaking ring; the couple can mark
//     "Audio only" and the vendor sees "Prefers audio only" instead of the
//     camera prompt; "Join with video" turns the vendor's camera on at join.""")
rep("""    // ignore: unused_element_parameter
    this.onReport, // the couple app doesn't pass it
  });""", """    // ignore: unused_element_parameter
    this.onReport, // the couple app doesn't pass it
    // ignore: unused_element_parameter
    this.startCamera = false, // only the vendor app passes it
  });""")
rep("""  final VoidCallback? onReport;

  @override""", """  final VoidCallback? onReport;
  final bool startCamera; // "Join with video" (the couple's camera still waits for the vendor)

  @override""")
rep("""  String _status = 'Connecting…';""", """  String _status = 'Connecting…';
  bool _coupleAudioOnly = false;
  double _meLevel = 0;
  double _otherLevel = 0;
  Timer? _lvl;""")
rep("""  void dispose() {
    _poll?.cancel();""", """  void dispose() {
    _poll?.cancel();
    _lvl?.cancel();""")
rep("""      _poll = Timer.periodic(const Duration(seconds: 2), (_) => _tick());
      _tick();""", """      _poll = Timer.periodic(const Duration(seconds: 2), (_) => _tick());
      _lvl = Timer.periodic(const Duration(milliseconds: 500), (_) => _levels());
      _tick();
      if (widget.startCamera && _isVendor) await _cameraOn();""")
rep("""      _coupleCamAllowed = v['coupleCamAllowed'] == true;
      _otherPresent""", """      _coupleCamAllowed = v['coupleCamAllowed'] == true;
      _coupleAudioOnly = v['coupleAudioOnly'] == true;
      _otherPresent""")
rep("""  Future<void> _allowCouple(bool on) async {""", """  // who is speaking: audio levels from the connection stats, twice a second
  Future<void> _levels() async {
    double read(List<StatsReport> rs, String type) {
      double best = 0;
      for (final StatsReport r in rs) {
        if (r.type != type) continue;
        final Map<dynamic, dynamic> v = r.values;
        if ((v['kind'] ?? v['mediaType'] ?? '').toString() != 'audio') continue;
        final dynamic a = v['audioLevel'];
        final double x = a is num ? a.toDouble() : double.tryParse('$a') ?? 0;
        if (x > best) best = x;
      }
      return best;
    }

    try {
      final double o = _pcSub == null ? 0 : read(await _pcSub!.getStats(), 'inbound-rtp');
      final double me = _pc == null || !_micOn ? 0 : read(await _pc!.getStats(), 'media-source');
      final bool changed = (o > .02) != (_otherLevel > .02) || (me > .02) != (_meLevel > .02);
      _otherLevel = o;
      _meLevel = me;
      if (changed) _set(() {});
    } catch (_) {}
  }

  Future<void> _setAudioPref(bool on) async {
    final Map<String, dynamic> r = await _rt('POST', 'pref', <String, dynamic>{'audioOnly': on});
    if (r['_status'] == 200) {
      _set(() => _coupleAudioOnly = r['coupleAudioOnly'] == true);
      if (on && _camOn) await _cameraOff();
    }
  }

  Future<void> _allowCouple(bool on) async {""")
rep("""  Widget _btn(IconData icon, String label, VoidCallback? onTap,""", """  Widget _avatar(String name, bool speaking, bool me) {
    final List<String> parts = name.replaceAll('&', ' ').split(RegExp(r'\\s+')).where((String w) => w.isNotEmpty).toList();
    final String ini = parts.isEmpty ? '?' : parts.take(2).map((String w) => w[0].toUpperCase()).join();
    return Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
      AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        width: 112,
        height: 112,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: me ? const Color(0xFF3A2B44) : const Color(0xFF52284F),
          border: Border.all(
              color: speaking ? const Color(0xFFD4B37A) : Colors.white.withOpacity(.12),
              width: speaking ? 5 : 2),
          boxShadow: speaking
              ? <BoxShadow>[BoxShadow(color: const Color(0xFFD4B37A).withOpacity(.45), blurRadius: 24, spreadRadius: 2)]
              : const <BoxShadow>[],
        ),
        child: Text(ini,
            style: const TextStyle(color: Colors.white, fontSize: 34, fontWeight: FontWeight.w700)),
      ),
      const SizedBox(height: 10),
      Text(me ? '$name (you)' : name,
          textAlign: TextAlign.center,
          style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w600)),
      const SizedBox(height: 4),
      Text(speaking ? 'Speaking' : (me && !_micOn ? 'Muted' : ' '),
          style: TextStyle(color: const Color(0xFFD4B37A).withOpacity(.9), fontSize: 12)),
    ]);
  }

  // nobody on camera: both people as avatars, a speaking ring, and why
  Widget _audioPanel() {
    final String note = _coupleAudioOnly
        ? (_isVendor
            ? '${widget.otherName} prefer audio only. Their camera stays off.'
            : 'You chose audio only. You can turn your camera on any time${_camAllowed ? '' : ' once ${widget.otherName} allows it'}.')
        : 'Audio only for now. Cameras stay off until someone turns theirs on.';
    return ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: Container(
        color: const Color(0xFF241E2B),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
        child: Stack(children: <Widget>[
          // remote audio plays through this renderer
          Positioned(left: 0, top: 0, width: 2, height: 2, child: Opacity(opacity: 0, child: RTCVideoView(_remoteR))),
          Center(
            child: SingleChildScrollView(
              child: Column(mainAxisSize: MainAxisSize.min, children: <Widget>[
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                  decoration: BoxDecoration(
                      color: Colors.white.withOpacity(.08), borderRadius: BorderRadius.circular(999)),
                  child: const Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
                    Icon(Icons.graphic_eq_rounded, color: Color(0xFFD4B37A), size: 16),
                    SizedBox(width: 6),
                    Text('Audio only', style: TextStyle(color: Colors.white, fontSize: 12.5, fontWeight: FontWeight.w700)),
                  ]),
                ),
                const SizedBox(height: 28),
                Wrap(alignment: WrapAlignment.center, spacing: 36, runSpacing: 24, children: <Widget>[
                  _avatar(widget.otherName, _otherPresent && _otherLevel > .02, false),
                  _avatar(widget.myName, _meLevel > .02, true),
                ]),
                const SizedBox(height: 26),
                Text(note,
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Colors.white.withOpacity(.7), fontSize: 12.5, height: 1.4)),
              ]),
            ),
          ),
        ]),
      ),
    );
  }

  Widget _btn(IconData icon, String label, VoidCallback? onTap,""")
rep("""            Expanded(child: wide ? Row(children: tiles) : Column(children: tiles)),""", """            Expanded(
                child: (!_remoteVideo && !_camOn)
                    ? _audioPanel()
                    : (wide ? Row(children: tiles) : Column(children: tiles))),""")
rep("""              if (_isVendor)
                TextButton.icon(
                  onPressed: () => _allowCouple(!_coupleCamAllowed),""", """              if (_isVendor && _coupleAudioOnly && !_coupleCamAllowed)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                      color: Colors.white.withOpacity(.08), borderRadius: BorderRadius.circular(999)),
                  child: const Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
                    Icon(Icons.headset_rounded, color: Color(0xFFD4B37A), size: 16),
                    SizedBox(width: 6),
                    Text('Prefers audio only', style: TextStyle(color: Color(0xFFD4B37A), fontSize: 12.5)),
                  ]),
                )
              else if (_isVendor)
                TextButton.icon(
                  onPressed: () => _allowCouple(!_coupleCamAllowed),""")
rep("""              if (_isVendor)
                _btn(_hidden || !_revealed""", """              if (!_isVendor)
                _btn(Icons.headset_rounded, _coupleAudioOnly ? 'Audio only \\u2713' : 'Audio only',
                    () => _setAudioPref(!_coupleAudioOnly),
                    bg: _coupleAudioOnly ? const Color(0xFF52284F) : null),
              if (_isVendor)
                _btn(_hidden || !_revealed""")
P.write_text(s, encoding='utf-8')
print('call screen v2 written')
