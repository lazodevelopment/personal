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

import 'dart:async';
import 'dart:ui' as ui_dart;
import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';
import 'package:just_audio/just_audio.dart';

// ═══════════════════════════════════════════════════════════════════════
// JOVI HEALTH — MEDITATION AUDIO
// Version: 2026.09.22-r2 (Apple HIG pass: press feedback, Reduce Motion,
//          15s skip icons, navy toast, title-case labels)
// r1:      2026.04.20
// Build: JC-MEDIT-0922-002
//
// Navy + glass rebrand of the Kurv meditation audio screen. Reuses the
// same 9 audio files (Firebase Storage URLs preserved) but with:
//
//   - Single-track playback controller (just_audio) instead of 9
//     independent FF players stacked on top of each other
//   - Now-playing hero card that expands with full controls when a
//     track is active, collapses back to the track list when paused
//   - Tap a track to play it (auto-stops any currently playing track)
//   - Seek, skip forward/backward 15s, play/pause, and next-track
//   - Background playback supported via just_audio's native iOS/Android
//     audio session handling; works on web via HTMLAudioElement
//   - Meditative violet accent (softer than coral — calming without
//     being cold like the pure-navy two-factor/records screens)
//
// NOTE: The audio files stored under `kurv-health.firebasestorage.app`
// should be migrated to `jovi-health` Firebase Storage at some point,
// but for now the URLs still work — Firebase Storage URLs don't change
// on project rename.
// ═══════════════════════════════════════════════════════════════════════

// ───────────────────────────────────────────────────────────────────────
// JOVI BRAND COLORS
// ───────────────────────────────────────────────────────────────────────

const Color _joviNavy = Color(0xFF1A2744);
const Color _joviNavyDark = Color(0xFF0F1A2E);
const Color _joviNavyMid = Color(0xFF1F2B47);
const Color _joviCoral = Color(0xFFFF6B4A);
const Color _joviCoralDark = Color(0xFFE5583A);
const Color _joviMint = Color(0xFF00D4AA);
const Color _joviGold = Color(0xFFFFD166);
const Color _joviErrorRed = Color(0xFFE53E3E);

// Meditation-specific accent — a soft violet that reads as "calm."
// Matches the accent used on the pet widgets so the app feels cohesive,
// but the meditation screen uses it as the primary hue rather than coral.
const Color _meditationAccent = Color(0xFFA78BFA);
const Color _meditationAccentDark = Color(0xFF8B6EE8);

// ───────────────────────────────────────────────────────────────────────
// TRACK CATALOG
// Two kinds of audio in the widget:
//   - Recorded tracks  — static files, seekable, fixed duration
//   - Live streams     — continuous 24/7 radio, not seekable, no timer
// The _MeditationTrack model handles both via the `isLive` flag.
// ───────────────────────────────────────────────────────────────────────

class _MeditationTrack {
  final String title;
  final String subtitle;
  final String url;
  final IconData icon;
  final bool isLive;
  const _MeditationTrack({
    required this.title,
    required this.subtitle,
    required this.url,
    required this.icon,
    this.isLive = false,
  });
}

// ─── Live streams ─────────────────────────────────────────────────────
// Public radio streams from YourClassical (American Public Media).
// Streamed over HTTPS, no authentication required, 24/7 availability.
// If you commercialize Jovi Health, review APM's terms of service —
// most public radio permits attribution-only embedding but commercial
// apps should confirm directly.
const List<_MeditationTrack> _liveStreams = [
  _MeditationTrack(
    title: 'Relax',
    subtitle: 'Live · calming classical',
    url: 'https://relax.stream.publicradio.org/relax.mp3',
    icon: Icons.self_improvement_rounded,
    isLive: true,
  ),
  _MeditationTrack(
    title: 'Classical Essentials',
    subtitle: 'Live · timeless masterworks',
    url: 'https://favorites.stream.publicradio.org/favorites.mp3',
    icon: Icons.music_note_rounded,
    isLive: true,
  ),
];

// ─── Recorded library tracks ──────────────────────────────────────────
// Original Jovi meditation library. Firebase Storage URLs preserved.
// These are finite files with real durations and are seekable.
const List<_MeditationTrack> _libraryTracks = [
  _MeditationTrack(
    title: 'Cosmic Meditation',
    subtitle: 'Ambient soundscape · deep focus',
    url:
        'https://firebasestorage.googleapis.com/v0/b/kurv-health.firebasestorage.app/o/Cosmic%20Meditation.wav?alt=media&token=db0e8589-09ae-4301-8968-15193c7a19a2',
    icon: Icons.auto_awesome_rounded,
  ),
  _MeditationTrack(
    title: 'Main Meditation',
    subtitle: 'Guided · grounding and breath',
    url:
        'https://firebasestorage.googleapis.com/v0/b/kurv-health.firebasestorage.app/o/01_main.wav?alt=media&token=3b57dad3-4cbd-4e2e-add2-0f29b99ef7b3',
    icon: Icons.self_improvement_rounded,
  ),
  _MeditationTrack(
    title: 'Binaural Meditation',
    subtitle: 'Use headphones · dual-tone focus',
    url:
        'https://firebasestorage.googleapis.com/v0/b/kurv-health.firebasestorage.app/o/Binaural%20Meditation.wav?alt=media&token=bc7f207f-75a1-4fc4-b1b8-2d4613f3c414',
    icon: Icons.headphones_rounded,
  ),
  _MeditationTrack(
    title: 'Crystal Squad',
    subtitle: 'Bowls and chimes · reset the mind',
    url:
        'https://firebasestorage.googleapis.com/v0/b/kurv-health.firebasestorage.app/o/CrystalSquad_Meditation_Main.wav?alt=media&token=55c577cb-1bcd-45fa-adf0-31da3fe19956',
    icon: Icons.diamond_rounded,
  ),
  _MeditationTrack(
    title: 'Deep Meditation',
    subtitle: 'Extended · 20+ minutes of stillness',
    url:
        'https://firebasestorage.googleapis.com/v0/b/kurv-health.firebasestorage.app/o/In%20Meditation%20%20L.wav?alt=media&token=63035fac-b1af-4032-9eef-220be3b66214',
    icon: Icons.spa_rounded,
  ),
  _MeditationTrack(
    title: 'Indian Meditation',
    subtitle: 'Raga-inspired · tabla and tanpura',
    url:
        'https://firebasestorage.googleapis.com/v0/b/kurv-health.firebasestorage.app/o/Indian%20Meditation.wav?alt=media&token=1a169416-05ce-4423-963a-84749bd15d02',
    icon: Icons.temple_hindu_rounded,
  ),
  _MeditationTrack(
    title: 'Long Meditation',
    subtitle: 'Sleep-ready · low ambient drone',
    url:
        'https://firebasestorage.googleapis.com/v0/b/kurv-health.firebasestorage.app/o/Meditation%20(long%20version).wav?alt=media&token=05c3f54e-21ef-484a-8633-2f40ca44029e',
    icon: Icons.bedtime_rounded,
  ),
  _MeditationTrack(
    title: 'Guided Vocal',
    subtitle: 'Softly guided · relaxation vocals',
    url:
        'https://firebasestorage.googleapis.com/v0/b/kurv-health.firebasestorage.app/o/Relaxing%20Meditation%20Female%20Vocal%20Version%203.wav?alt=media&token=0b08fac3-f509-4b26-a12e-34a349f8936a',
    icon: Icons.record_voice_over_rounded,
  ),
  _MeditationTrack(
    title: 'Quick Reset',
    subtitle: 'Short session · pause between tasks',
    url:
        'https://firebasestorage.googleapis.com/v0/b/kurv-health.firebasestorage.app/o/item.wav?alt=media&token=1e687b7d-6ae4-4bb4-ba61-66828a02dab9',
    icon: Icons.timer_rounded,
  ),
];

// ═══════════════════════════════════════════════════════════════════════
// WIDGET
// ═══════════════════════════════════════════════════════════════════════

// ─── Motion (Apple "response" values; critically damped, no overshoot) ──
class _Motion {
  static const Duration pressIn = Duration(milliseconds: 90);
  static const Duration pressOut = Duration(milliseconds: 260);
  static const Duration select = Duration(milliseconds: 220);
  static const Duration enter = Duration(milliseconds: 420);
  static const Curve settle = Curves.easeOutCubic;
}

/// Reads the platform Reduce Motion flag without a BuildContext (initState-safe).
bool _platformReduceMotion() =>
    WidgetsBinding.instance.platformDispatcher.accessibilityFeatures
        .disableAnimations;

/// Press feedback that lives on pointer-down, not on release. Scales the
/// child down the instant a finger lands, releases when it lifts, and
/// springs back early if the finger travels ~10 px (a scroll, not a tap).
/// With [feedbackOnly] it animates but leaves tap handling to the child
/// (e.g. an InkWell), so nothing fires twice. Honors Reduce Motion.
class _Pressable extends StatefulWidget {
  final Widget child;
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;
  final bool enabled;
  final bool feedbackOnly;
  final double pressedScale;

  const _Pressable({
    Key? key,
    required this.child,
    this.onTap,
    this.onLongPress,
    this.enabled = true,
    this.feedbackOnly = false,
    this.pressedScale = 0.97,
  }) : super(key: key);

  @override
  State<_Pressable> createState() => _PressableState();
}

class _PressableState extends State<_Pressable> {
  static const double _slop = 10.0;
  bool _down = false;
  Offset? _downAt;

  void _set(bool v) {
    if (_down == v) return;
    setState(() => _down = v);
  }

  @override
  Widget build(BuildContext context) {
    final reduce = MediaQuery.maybeOf(context)?.disableAnimations ?? false;
    final animates =
        widget.enabled &&
            (widget.onTap != null ||
                widget.onLongPress != null ||
                widget.feedbackOnly);
    final scale = (_down && animates && !reduce) ? widget.pressedScale : 1.0;
    final scaled = AnimatedScale(
      scale: scale,
      duration: _down ? _Motion.pressIn : _Motion.pressOut,
      curve: _down ? Curves.easeOut : _Motion.settle,
      child: widget.child,
    );
    final handlesTap =
        (widget.onTap != null || widget.onLongPress != null) &&
            !widget.feedbackOnly;
    return Semantics(
      button: handlesTap,
      child: Listener(
        onPointerDown: (e) {
          _downAt = e.position;
          _set(true);
        },
        onPointerMove: (e) {
          final start = _downAt;
          if (start != null && (e.position - start).distance > _slop) {
            _set(false);
          }
        },
        onPointerUp: (_) => _set(false),
        onPointerCancel: (_) => _set(false),
        child: !handlesTap
            ? scaled
            : GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: widget.enabled ? widget.onTap : null,
                onLongPress: widget.enabled ? widget.onLongPress : null,
                child: scaled,
              ),
      ),
    );
  }
}

/// Toast in the app's own voice: navy surface, tinted icon, white text.
SnackBar _joviToast(
  String message, {
  required Color accent,
  IconData? icon,
  Duration? duration,
}) {
  return SnackBar(
    content: Row(children: [
      if (icon != null) Icon(icon, color: accent, size: 20),
      const SizedBox(width: 10),
      Expanded(
          child: Text(message,
              style: const TextStyle(
                  color: Colors.white,
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                  letterSpacing: -0.2))),
    ]),
    duration: duration ?? const Duration(milliseconds: 2800),
    backgroundColor: const Color(0xFF243352),
    elevation: 0,
    behavior: SnackBarBehavior.floating,
    margin: const EdgeInsets.fromLTRB(16, 0, 16, 24),
    shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: BorderSide(color: accent.withOpacity(0.35))),
  );
}

/// Drop-in for `Material(color: Colors.transparent, child: InkWell(...))`:
/// keeps the ripple and the existing tap handler, adds pointer-down press
/// feedback around it without firing anything twice.
class _PressableMaterial extends StatelessWidget {
  final Widget child;
  final double pressedScale;
  const _PressableMaterial({Key? key, required this.child, this.pressedScale = 0.98})
      : super(key: key);

  @override
  Widget build(BuildContext context) {
    return _Pressable(
      feedbackOnly: true,
      pressedScale: pressedScale,
      child: Material(color: Colors.transparent, child: child),
    );
  }
}

class JoviMeditationAudio extends StatefulWidget {
  final double? width;
  final double? height;

  const JoviMeditationAudio({
    Key? key,
    this.width,
    this.height,
  }) : super(key: key);

  @override
  State<JoviMeditationAudio> createState() => _JoviMeditationAudioState();
}

class _JoviMeditationAudioState extends State<JoviMeditationAudio>
    with SingleTickerProviderStateMixin {
  // ─── Audio state ──────────────────────────────────────────────────
  final AudioPlayer _player = AudioPlayer();
  int? _currentTrackIdx;
  bool _isPlaying = false;
  Duration _position = Duration.zero;
  Duration _duration = Duration.zero;
  bool _isBuffering = false;
  StreamSubscription<Duration>? _posSub;
  StreamSubscription<Duration?>? _durSub;
  StreamSubscription<PlayerState>? _stateSub;

  // Combined track list — live streams first, recorded library second.
  // Indexing is consistent across the app so _currentTrackIdx works for
  // either kind. The _isLive() helper keeps playback logic clean.
  List<_MeditationTrack> get _tracks => [..._liveStreams, ..._libraryTracks];
  bool _isLive(int idx) =>
      idx >= 0 && idx < _tracks.length && _tracks[idx].isLive;
  _MeditationTrack? get _currentTrack =>
      _currentTrackIdx != null ? _tracks[_currentTrackIdx!] : null;
  bool get _currentIsLive =>
      _currentTrackIdx != null && _isLive(_currentTrackIdx!);

  // ─── Animation ────────────────────────────────────────────────────
  late AnimationController _fadeCtrl;
  late Animation<double> _fadeAnim;

  @override
  void initState() {
    super.initState();

    _fadeCtrl = AnimationController(vsync: this, duration: _Motion.enter);
    _fadeAnim = CurvedAnimation(parent: _fadeCtrl, curve: Curves.easeOut);
    if (_platformReduceMotion()) {
      _fadeCtrl.value = 1.0;
    } else {
      _fadeCtrl.forward();
    }

    // Position updates — fires frequently while playing.
    _posSub = _player.positionStream.listen((p) {
      if (!mounted) return;
      setState(() => _position = p);
    });
    // Duration of the currently loaded track — arrives once loading resolves.
    _durSub = _player.durationStream.listen((d) {
      if (!mounted) return;
      setState(() => _duration = d ?? Duration.zero);
    });
    // Playback state — tells us playing/paused/buffering/completed.
    _stateSub = _player.playerStateStream.listen((state) {
      if (!mounted) return;
      setState(() {
        _isPlaying = state.playing;

        // Buffering logic differs between recorded tracks and live streams:
        //
        // RECORDED TRACKS: `loading` and `buffering` are both transient —
        // they clear once the player moves to `ready`. Showing a spinner
        // during either state is correct.
        //
        // LIVE STREAMS: just_audio reports `buffering` continuously while
        // a live stream is playing because it's always pulling new audio
        // from the network. We only want to show the spinner during the
        // *initial* load (before the stream starts playing). Once
        // state.playing is true, the stream is playing — any "buffering"
        // reported after that is the normal steady state.
        final isLiveAndPlaying = _currentIsLive && state.playing;
        _isBuffering = !isLiveAndPlaying &&
            (state.processingState == ProcessingState.loading ||
                state.processingState == ProcessingState.buffering);
      });
      // Auto-advance to the next track when the current one completes —
      // but NOT for live streams. If a live stream ends (e.g., network
      // blip), we want it to try reconnecting, not jump to another track.
      if (state.processingState == ProcessingState.completed &&
          !_currentIsLive) {
        _playNext();
      }
    });
  }

  @override
  void dispose() {
    _posSub?.cancel();
    _durSub?.cancel();
    _stateSub?.cancel();
    _player.dispose();
    _fadeCtrl.dispose();
    super.dispose();
  }

  // ─── Playback control helpers ─────────────────────────────────────

  Future<void> _playTrack(int idx) async {
    if (idx < 0 || idx >= _tracks.length) return;
    HapticFeedback.selectionClick();
    // If user tapped the currently-playing track, toggle pause/resume.
    if (_currentTrackIdx == idx && _isPlaying) {
      await _player.pause();
      return;
    }
    if (_currentTrackIdx == idx && !_isPlaying) {
      await _player.play();
      return;
    }
    // Different track — stop current, load new, play.
    setState(() {
      _currentTrackIdx = idx;
      _position = Duration.zero;
      _duration = Duration.zero;
      _isBuffering = true;
    });
    try {
      await _player.stop();
      // setUrl resolves once the track is loaded and ready to play.
      await _player.setUrl(_tracks[idx].url);
      await _player.play();
    } catch (e) {
      debugPrint('JoviMeditationAudio: failed to start playback: $e');
      if (!mounted) return;
      setState(() {
        _isBuffering = false;
      });
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast('Could not play this track. Try again.',
        accent: _joviErrorRed, icon: CupertinoIcons.exclamationmark_circle));
    }
  }

  Future<void> _togglePlayPause() async {
    if (_currentTrackIdx == null) {
      // Nothing loaded yet — start with the first track.
      await _playTrack(0);
      return;
    }
    HapticFeedback.lightImpact();
    if (_isPlaying) {
      await _player.pause();
    } else {
      await _player.play();
    }
  }

  Future<void> _playNext() async {
    if (_currentTrackIdx == null) {
      await _playTrack(0);
      return;
    }
    final next = (_currentTrackIdx! + 1) % _tracks.length;
    await _playTrack(next);
  }

  Future<void> _playPrevious() async {
    if (_currentTrackIdx == null) {
      await _playTrack(0);
      return;
    }
    // If we're more than 3 seconds in, restart the current track.
    // Otherwise skip to the previous one. Standard music player UX.
    if (_position.inSeconds > 3) {
      await _player.seek(Duration.zero);
      return;
    }
    final prev = (_currentTrackIdx! - 1 + _tracks.length) % _tracks.length;
    await _playTrack(prev);
  }

  Future<void> _seekRelative(Duration delta) async {
    if (_currentTrackIdx == null) return;
    HapticFeedback.selectionClick();
    final target = _position + delta;
    final clamped = target < Duration.zero
        ? Duration.zero
        : (target > _duration ? _duration : target);
    await _player.seek(clamped);
  }

  Future<void> _seekToFraction(double fraction) async {
    if (_currentTrackIdx == null || _duration == Duration.zero) return;
    final target = Duration(
      milliseconds:
          (_duration.inMilliseconds * fraction.clamp(0.0, 1.0)).round(),
    );
    await _player.seek(target);
  }

  // ─── Build ────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final screen = MediaQuery.of(context).size;
    return Container(
      width: widget.width ?? screen.width,
      height: widget.height ?? screen.height,
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [_joviNavy, _joviNavy, _joviNavyDark],
        ),
      ),
      child: SafeArea(
        child: FadeTransition(
          opacity: _fadeAnim,
          child: Stack(
            children: [
              // Ambient background orbs — adds depth without looking busy.
              Positioned(
                top: -80,
                right: -60,
                child:
                    _buildAmbientOrb(_meditationAccent.withOpacity(0.18), 240),
              ),
              Positioned(
                bottom: -100,
                left: -80,
                child: _buildAmbientOrb(_joviMint.withOpacity(0.08), 260),
              ),
              // Main content.
              Column(
                children: [
                  _buildHeader(),
                  Expanded(
                    child: SingleChildScrollView(
                      padding: const EdgeInsets.fromLTRB(16, 0, 16, 120),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _buildIntroCopy(),
                          const SizedBox(height: 18),
                          _buildTrackList(),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
              // Persistent "now playing" bar at the bottom when a track is
              // active. Stacked above content so it doesn't push anything.
              if (_currentTrackIdx != null)
                Positioned(
                  left: 12,
                  right: 12,
                  bottom: 12,
                  child: _buildNowPlayingBar(),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildAmbientOrb(Color color, double size) {
    return IgnorePointer(
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: RadialGradient(
            colors: [color, color.withOpacity(0)],
          ),
        ),
      ),
    );
  }

  // ─── Header ───────────────────────────────────────────────────────

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(8, 10, 16, 12),
      child: Row(
        children: [
          // Back button.
          _PressableMaterial(
            child: InkWell(
              onTap: () {
                HapticFeedback.selectionClick();
                if (Navigator.of(context).canPop()) {
                  Navigator.of(context).pop();
                }
              },
              borderRadius: BorderRadius.circular(22),
              child: Semantics(
                label: 'Back',
                button: true,
                child: Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.06),
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: Colors.white.withOpacity(0.14),
                      width: 0.8,
                    ),
                  ),
                  child: Icon(
                    Icons.arrow_back_ios_new_rounded,
                    color: Colors.white.withOpacity(0.85),
                    size: 17,
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          // Title + subtitle.
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: const [
                Text(
                  'Meditation',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 17,
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.4,
                    height: 1.1,
                  ),
                ),
                SizedBox(height: 2),
                Text(
                  'Guided and ambient · play anywhere',
                  style: TextStyle(
                    color: Color(0x88FFFFFF),
                    fontSize: 11.5,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0.2,
                  ),
                ),
              ],
            ),
          ),
          // Decorative icon — matches other Jovi headers.
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [_meditationAccent, _meditationAccentDark],
              ),
              borderRadius: BorderRadius.circular(11),
              boxShadow: [
                BoxShadow(
                  color: _meditationAccent.withOpacity(0.35),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: const Icon(
              Icons.self_improvement_rounded,
              color: Colors.white,
              size: 20,
            ),
          ),
        ],
      ),
    );
  }

  // ─── Intro copy ───────────────────────────────────────────────────

  Widget _buildIntroCopy() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: Colors.white.withOpacity(0.1),
          width: 1,
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: _meditationAccent.withOpacity(0.18),
              borderRadius: BorderRadius.circular(13),
              border: Border.all(
                color: _meditationAccent.withOpacity(0.3),
                width: 1,
              ),
            ),
            child: const Icon(
              Icons.favorite_rounded,
              color: _meditationAccent,
              size: 20,
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text(
                  'A moment for yourself',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 14.5,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -0.3,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  'Two live stations and nine recorded sessions. Tap any to begin.',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.6),
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ─── Track list ───────────────────────────────────────────────────

  Widget _buildTrackList() {
    final children = <Widget>[];

    // ─── Live Radio section ───────────────────────────────────────
    if (_liveStreams.isNotEmpty) {
      children.add(_buildSectionHeader(
        icon: Icons.radio_rounded,
        label: 'Live Radio',
        helper: 'Continuous · public classical',
      ));
      children.add(const SizedBox(height: 10));
      for (int i = 0; i < _liveStreams.length; i++) {
        // Live streams occupy indices [0, _liveStreams.length).
        children.add(Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: _buildTrackCard(i, _liveStreams[i]),
        ));
      }
      children.add(const SizedBox(height: 14));
    }

    // ─── Library section ──────────────────────────────────────────
    children.add(_buildSectionHeader(
      icon: Icons.library_music_rounded,
      label: 'Meditation Library',
      helper: '${_libraryTracks.length} guided and ambient tracks',
    ));
    children.add(const SizedBox(height: 10));
    for (int i = 0; i < _libraryTracks.length; i++) {
      // Library tracks occupy indices [_liveStreams.length, _tracks.length).
      final globalIdx = _liveStreams.length + i;
      children.add(Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: _buildTrackCard(globalIdx, _libraryTracks[i]),
      ));
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: children,
    );
  }

  Widget _buildSectionHeader({
    required IconData icon,
    required String label,
    required String helper,
  }) {
    return Row(
      children: [
        Container(
          width: 28,
          height: 28,
          decoration: BoxDecoration(
            color: _meditationAccent.withOpacity(0.14),
            borderRadius: BorderRadius.circular(9),
            border: Border.all(
              color: _meditationAccent.withOpacity(0.28),
              width: 0.8,
            ),
          ),
          child: Icon(icon, color: _meditationAccent, size: 15),
        ),
        const SizedBox(width: 10),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              label,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 15,
                fontWeight: FontWeight.w600,
                letterSpacing: -0.2,
              ),
            ),
            const SizedBox(height: 1),
            Text(
              helper,
              style: TextStyle(
                color: Colors.white.withOpacity(0.5),
                fontSize: 10.5,
                fontWeight: FontWeight.w600,
                letterSpacing: 0.4,
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildTrackCard(int idx, _MeditationTrack track) {
    final isCurrent = _currentTrackIdx == idx;
    final isThisPlaying = isCurrent && _isPlaying;
    final isThisBuffering = isCurrent && _isBuffering;
    return _PressableMaterial(
      child: InkWell(
        onTap: () => _playTrack(idx),
        borderRadius: BorderRadius.circular(16),
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: isCurrent
                ? _meditationAccent.withOpacity(0.12)
                : (track.isLive
                    ? Colors.white.withOpacity(0.04)
                    : Colors.white.withOpacity(0.05)),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: isCurrent
                  ? _meditationAccent.withOpacity(0.45)
                  : (track.isLive
                      ? _joviCoral.withOpacity(0.22)
                      : Colors.white.withOpacity(0.1)),
              width: isCurrent ? 1.3 : 1,
            ),
            boxShadow: isCurrent
                ? [
                    BoxShadow(
                      color: _meditationAccent.withOpacity(0.2),
                      blurRadius: 14,
                      offset: const Offset(0, 4),
                    ),
                  ]
                : null,
          ),
          child: Row(
            children: [
              _buildTrackArt(track, isCurrent),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    // Title + optional LIVE badge inline.
                    Row(
                      children: [
                        Flexible(
                          child: Text(
                            track.title,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 14.5,
                              fontWeight: FontWeight.w800,
                              letterSpacing: -0.3,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        if (track.isLive) ...[
                          const SizedBox(width: 8),
                          _buildLiveBadge(),
                        ],
                      ],
                    ),
                    const SizedBox(height: 3),
                    Text(
                      track.subtitle,
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.55),
                        fontSize: 11.5,
                        fontWeight: FontWeight.w500,
                        height: 1.3,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 10),
              // Playback indicator — changes based on state.
              if (isThisBuffering)
                const SizedBox(
                  width: 36,
                  height: 36,
                  child: Center(
                    child: SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor:
                            AlwaysStoppedAnimation<Color>(_meditationAccent),
                      ),
                    ),
                  ),
                )
              else
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: isCurrent
                        ? _meditationAccent
                        : Colors.white.withOpacity(0.08),
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: isCurrent
                          ? _meditationAccent
                          : Colors.white.withOpacity(0.14),
                      width: 0.8,
                    ),
                    boxShadow: isCurrent
                        ? [
                            BoxShadow(
                              color: _meditationAccent.withOpacity(0.45),
                              blurRadius: 10,
                              offset: const Offset(0, 3),
                            ),
                          ]
                        : null,
                  ),
                  child: Icon(
                    isThisPlaying
                        ? Icons.pause_rounded
                        : Icons.play_arrow_rounded,
                    color: isCurrent
                        ? Colors.white
                        : Colors.white.withOpacity(0.7),
                    size: 20,
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  /// Small pulsing LIVE badge shown on live-stream track cards and in
  /// the now-playing bar. Red dot + "LIVE" text. Universally-understood
  /// pattern from music apps and news channels.
  Widget _buildLiveBadge({bool compact = false}) {
    return Container(
      padding: EdgeInsets.symmetric(
          horizontal: compact ? 6 : 7, vertical: compact ? 2 : 3),
      decoration: BoxDecoration(
        color: _joviCoral.withOpacity(0.18),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(
          color: _joviCoral.withOpacity(0.5),
          width: 0.8,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: compact ? 4 : 5,
            height: compact ? 4 : 5,
            decoration: const BoxDecoration(
              color: _joviCoral,
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: _joviCoral,
                  blurRadius: 4,
                  spreadRadius: 0.5,
                ),
              ],
            ),
          ),
          SizedBox(width: compact ? 3 : 4),
          Text(
            'LIVE',
            style: TextStyle(
              color: _joviCoralDark,
              fontSize: compact ? 8.5 : 9.5,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.8,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTrackArt(_MeditationTrack track, bool isCurrent) {
    return Container(
      width: 46,
      height: 46,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: isCurrent
              ? const [_meditationAccent, _meditationAccentDark]
              : [
                  Colors.white.withOpacity(0.09),
                  Colors.white.withOpacity(0.04),
                ],
        ),
        borderRadius: BorderRadius.circular(13),
        border: Border.all(
          color: isCurrent
              ? _meditationAccent.withOpacity(0.5)
              : Colors.white.withOpacity(0.12),
          width: 1,
        ),
      ),
      child: Icon(
        track.icon,
        color: isCurrent ? Colors.white : _meditationAccent.withOpacity(0.9),
        size: 22,
      ),
    );
  }

  // ─── Now playing bar (persistent bottom sheet-style) ──────────────

  Widget _buildNowPlayingBar() {
    final idx = _currentTrackIdx!;
    final track = _tracks[idx];
    final progress = _duration.inMilliseconds == 0
        ? 0.0
        : (_position.inMilliseconds / _duration.inMilliseconds).clamp(0.0, 1.0);
    return ClipRRect(
      borderRadius: BorderRadius.circular(22),
      child: BackdropFilter(
        filter: ui_dart.ImageFilter.blur(sigmaX: 24, sigmaY: 24),
        child: Container(
          padding: const EdgeInsets.fromLTRB(14, 14, 14, 16),
          decoration: BoxDecoration(
            color: _joviNavyMid.withOpacity(0.82),
            borderRadius: BorderRadius.circular(22),
            border: Border.all(
              color: _meditationAccent.withOpacity(0.3),
              width: 1,
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.35),
                blurRadius: 28,
                offset: const Offset(0, 10),
              ),
              BoxShadow(
                color: _meditationAccent.withOpacity(0.15),
                blurRadius: 30,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                children: [
                  _buildTrackArt(track, true),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Row(
                          children: [
                            Flexible(
                              child: Text(
                                track.title,
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 13.5,
                                  fontWeight: FontWeight.w800,
                                  letterSpacing: -0.2,
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            if (track.isLive) ...[
                              const SizedBox(width: 7),
                              _buildLiveBadge(compact: true),
                            ],
                          ],
                        ),
                        const SizedBox(height: 1),
                        Text(
                          _isBuffering ? 'Buffering…' : track.subtitle,
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.55),
                            fontSize: 11,
                            fontWeight: FontWeight.w500,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                  _miniIconButton(
                    icon: Icons.close_rounded,
                    tooltip: 'Stop',
                    onTap: () async {
                      HapticFeedback.selectionClick();
                      await _player.stop();
                      if (!mounted) return;
                      setState(() {
                        // Clear every piece of playback state so there is
                        // no residual spinning, playing flag, or index.
                        // The player's own state stream may fire one more
                        // event after .stop() returns — _currentTrackIdx
                        // being null protects downstream UI from acting
                        // on that lingering event.
                        _currentTrackIdx = null;
                        _position = Duration.zero;
                        _duration = Duration.zero;
                        _isPlaying = false;
                        _isBuffering = false;
                      });
                    },
                  ),
                ],
              ),
              // Seek bar and timers — only for recorded tracks.
              // Live streams show no scrubber (you can't seek a live
              // broadcast) and no timer (there's no "end").
              if (!track.isLive) ...[
                const SizedBox(height: 12),
                _buildSeekBar(progress),
                const SizedBox(height: 8),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      _formatDuration(_position),
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.65),
                        fontSize: 10.5,
                        fontWeight: FontWeight.w700,
                        fontFeatures: const [FontFeature.tabularFigures()],
                      ),
                    ),
                    Text(
                      _duration == Duration.zero
                          ? '--:--'
                          : _formatDuration(_duration),
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.65),
                        fontSize: 10.5,
                        fontWeight: FontWeight.w700,
                        fontFeatures: const [FontFeature.tabularFigures()],
                      ),
                    ),
                  ],
                ),
              ] else ...[
                // Live stream: show a subtle "on air" line instead of a
                // scrubber, so the bar visually balances between title
                // and the playback controls.
                const SizedBox(height: 14),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      Icons.sensors_rounded,
                      color: Colors.white.withOpacity(0.45),
                      size: 13,
                    ),
                    const SizedBox(width: 6),
                    Text(
                      'Broadcasting now',
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.55),
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0.3,
                      ),
                    ),
                  ],
                ),
              ],
              const SizedBox(height: 10),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  _miniIconButton(
                    icon: Icons.skip_previous_rounded,
                    tooltip: 'Previous',
                    onTap: _playPrevious,
                    size: 42,
                  ),
                  // ±15s seek buttons only apply to recorded tracks.
                  // For live streams there's no way to seek backward
                  // or forward — the feed is what it is.
                  if (!track.isLive)
                    _miniIconButton(
                      icon: CupertinoIcons.gobackward_15,
                      tooltip: 'Back 15s',
                      onTap: () => _seekRelative(const Duration(seconds: -15)),
                      size: 42,
                    ),
                  _buildPlayPauseButton(),
                  if (!track.isLive)
                    _miniIconButton(
                      icon: CupertinoIcons.goforward_15,
                      tooltip: 'Forward 15s',
                      onTap: () => _seekRelative(const Duration(seconds: 15)),
                      size: 42,
                    ),
                  _miniIconButton(
                    icon: Icons.skip_next_rounded,
                    tooltip: 'Next',
                    onTap: _playNext,
                    size: 42,
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSeekBar(double progress) {
    return LayoutBuilder(builder: (ctx, constraints) {
      return GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTapDown: (d) {
          final frac = d.localPosition.dx / constraints.maxWidth;
          _seekToFraction(frac);
        },
        onHorizontalDragUpdate: (d) {
          final frac = d.localPosition.dx / constraints.maxWidth;
          _seekToFraction(frac);
        },
        child: SizedBox(
          height: 14,
          child: Stack(
            alignment: Alignment.centerLeft,
            children: [
              // Track background.
              Container(
                height: 3,
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              // Progress fill.
              FractionallySizedBox(
                widthFactor: progress,
                child: Container(
                  height: 3,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [_meditationAccent, _meditationAccentDark],
                    ),
                    borderRadius: BorderRadius.circular(2),
                    boxShadow: [
                      BoxShadow(
                        color: _meditationAccent.withOpacity(0.5),
                        blurRadius: 6,
                        offset: const Offset(0, 1),
                      ),
                    ],
                  ),
                ),
              ),
              // Thumb.
              Align(
                alignment: Alignment(
                  (progress * 2) - 1,
                  0,
                ),
                child: Container(
                  width: 12,
                  height: 12,
                  decoration: BoxDecoration(
                    color: Colors.white,
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: _meditationAccent.withOpacity(0.5),
                        blurRadius: 6,
                        offset: const Offset(0, 1),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      );
    });
  }

  Widget _buildPlayPauseButton() {
    return _PressableMaterial(
      child: InkWell(
        onTap: _togglePlayPause,
        borderRadius: BorderRadius.circular(28),
        child: Semantics(
          label: _isPlaying ? 'Pause' : 'Play',
          button: true,
          child: Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: const LinearGradient(
                colors: [_meditationAccent, _meditationAccentDark],
              ),
              boxShadow: [
                BoxShadow(
                  color: _meditationAccent.withOpacity(0.5),
                  blurRadius: 18,
                  offset: const Offset(0, 6),
                ),
              ],
            ),
            child: _isBuffering
                ? const Padding(
                    padding: EdgeInsets.all(16),
                    child: CircularProgressIndicator(
                      strokeWidth: 2.5,
                      valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                    ),
                  )
                : Icon(
                    _isPlaying ? Icons.pause_rounded : Icons.play_arrow_rounded,
                    color: Colors.white,
                    size: 28,
                  ),
          ),
        ),
      ),
    );
  }

  Widget _miniIconButton({
    required IconData icon,
    required VoidCallback onTap,
    String? tooltip,
    double size = 44,
  }) {
    final btn = _PressableMaterial(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(size / 2),
        child: Container(
          width: size,
          height: size,
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.06),
            shape: BoxShape.circle,
            border: Border.all(
              color: Colors.white.withOpacity(0.14),
              width: 0.8,
            ),
          ),
          child: Icon(
            icon,
            color: Colors.white.withOpacity(0.85),
            size: size * 0.46,
          ),
        ),
      ),
    );
    return tooltip != null ? Tooltip(message: tooltip, child: btn) : btn;
  }

  String _formatDuration(Duration d) {
    final minutes = d.inMinutes;
    final seconds = d.inSeconds.remainder(60);
    return '${minutes.toString()}:${seconds.toString().padLeft(2, '0')}';
  }
}
