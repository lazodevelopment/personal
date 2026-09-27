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

// =======================================================================
// JOVI HEALTH — FITNESS HOME + ACTIVE RUN UI (SELF-CONTAINED)
// Version: 2026.04.22-s4 (r1: merged engine + services + UI into one
//          file because FF compiles each widget file as an independent
//          unit — cross-file type imports don't work for non-widget
//          classes. Renamed Split → ActivitySplit to avoid collision
//          with Flutter's animations Split.)
// r2 (2026.09.22): Apple HIG pass — press feedback, painted glass on the
//          Start tab, Cupertino alerts, PopScope, adaptive switches, no
//          location prompt for weather, no simulated weather.
// r3 (2026.09.22): Stop now opens the post-run summary instead of a toast.
// Build: JC-RUNFIT-0922-003
//
// Widget Name (for FF): JoviRunFitnessHome
//
// This file contains EVERYTHING the fitness feature needs to run:
//   1. Core types / math (from former jovi_run_engine.dart)
//      - ActivityType enum, ActivitySplit, ActivityStats,
//        ActivitySession, GpsPoint, SessionStatus enum
//      - Unit conversions + formatters
//      - RunTrackingService (GPS stream + auto-pause + rolling pace)
//      - RunPersistenceService (Firestore checkpointing + recovery)
//      - LocationPermissionDeniedException / ServiceDisabled
//
//   2. Services (from former jovi_run_services.dart)
//      - PrimaryStatChoice enum
//      - RunSettings (Firestore-backed prefs)
//      - RunAudioCueService (TTS + audio_session ducking)
//      - RunAcquisitionState enum
//      - RunController (singleton coordinating tracking + persistence
//        + audio; the entry point used by the UI)
//
//   3. UI screens
//      - RunPermissionPrimer (glass pre-prompt)
//      - JoviRunFitnessHome (Start + History tabbed home — THE WIDGET)
//      - RunActivityPicker (Run/Walk/Ride chooser)
//      - RunActiveScreen (Mapbox + stats overlay during a live activity)
//
// WHY IT'S SELF-CONTAINED:
//   FlutterFlow wraps each custom widget file in its own library.
//   A widget file CAN reference other widget CLASSES via the
//   auto-generated `/custom_code/widgets/index.dart` barrel, but it
//   CANNOT reference non-widget types declared in other files —
//   those live inside the other file's private library scope.
//   Consequence: all shared types must be duplicated into every file
//   that uses them.
//
// CROSS-FILE COORDINATION (with jovi_run_history.dart):
//   - This file WRITES runs to Firestore under users/{uid}/activities
//   - jovi_run_history.dart READS them. No Dart-level reference.
//   - The "tap History tab in empty state to switch to Start tab"
//     callback is wired via JoviRunHistoryList.onStartRequested static.
//   - History tap → RunDetailScreen is handled inside the history file.
//
// BRAND:
//   Navy + glassmorphism, coral accents. Route line on map is coral.
//
// PUB DEPS (all listed in SETUP.md):
//   geolocator, uuid, mapbox_maps_flutter, flutter_tts,
//   permission_handler, wakelock_plus, cloud_firestore, firebase_auth
//   (audio_session is FF-bundled; don't re-declare)
//
// MAPBOX TOKEN:
//   Edit _mapboxPublicToken below before running or the map will be
//   blank. See SETUP.md section 8.
// =======================================================================

import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;
import 'dart:ui';

import 'package:audio_session/audio_session.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as network_http;
import 'package:intl/intl.dart';
import 'package:mapbox_maps_flutter/mapbox_maps_flutter.dart' as mb;
import 'package:permission_handler/permission_handler.dart';
import 'package:uuid/uuid.dart';
import 'package:wakelock_plus/wakelock_plus.dart';

// =======================================================================
// MAPBOX PUBLIC TOKEN
//
// Replace this with YOUR public token from account.mapbox.com
// (starts with "pk."). The secret download token (starts with "sk.")
// goes in native config files — see SETUP.md sections 8 and 9.
//
// This token is safe to include in client code. Mapbox's free tier
// includes 50,000 map loads/month which is well above anything
// Jovi would hit in early stages.
// =======================================================================

const String _mapboxPublicToken =
    'pk.eyJ1Ijoiam92aWhlYWx0aCIsImEiOiJjbW9hYzk5cDAwNTlhMnhwd3V5a2ZxeHh6In0.Ke708anyClWtZlo75KEMag';

// =======================================================================
// BRAND PALETTE (local copy — FF custom widgets are own compile units)
// =======================================================================

const Color _joviCoral = Color(0xFFFF6B4A);
const Color _joviCoralLight = Color(0xFFFF8F73);
const Color _joviCoralDark = Color(0xFFE5583A);
const Color _joviNavy = Color(0xFF1A2744);
const Color _joviNavyDark = Color(0xFF0F1A2E);
const Color _joviMint = Color(0xFF00D4AA);
const Color _joviGold = Color(0xFFFFD166);
const Color _joviErrorRed = Color(0xFFE53935);

// =======================================================================
// LOGGING HELPERS
// No-op stubs; swap for Firebase Analytics / Crashlytics when ready.
// Used by both the engine-layer classes below (tracking, persistence)
// and the UI (activity picker, active screen).
// =======================================================================

void _log(String msg) {
  // ignore: avoid_print
  if (kDebugMode) debugPrint('[JoviRunFit] $msg');
}

void _logError(String msg, Object? err, [StackTrace? st]) {
  // ignore: avoid_print
  if (kDebugMode) {
    debugPrint('[JoviRunFit][ERROR] $msg: $err');
    if (st != null) debugPrint('$st');
  }
}

void _analytics(String event, [Map<String, Object?>? props]) {
  if (props == null || props.isEmpty) {
    _log('analytics: $event');
  } else {
    _log('analytics: $event $props');
  }
}

// =======================================================================
// UNIT CONVERSIONS
// Everything INTERNAL is metric. Display helpers convert to US units.
// This prevents the "is this value feet or meters?" bugs that plague
// fitness apps.
// =======================================================================

const double _metersPerMile = 1609.344;
const double _metersPerKilometer = 1000.0;
const double _feetPerMeter = 3.28084;
const double _mphPerMps = 2.23694;

double metersToMiles(double meters) => meters / _metersPerMile;
double metersToKilometers(double meters) => meters / _metersPerKilometer;
double metersToFeet(double meters) => meters * _feetPerMeter;
double mpsToMph(double mps) => mps * _mphPerMps;

/// Pace as "min:ss per mile" string from speed in m/s.
/// Returns "--:--" for zero or near-zero speed (can't divide).
String formatPaceMinPerMile(double? speedMps) {
  if (speedMps == null || speedMps < 0.1) return '--:--';
  // seconds per meter * meters per mile = seconds per mile
  final secondsPerMile = _metersPerMile / speedMps;
  final minutes = secondsPerMile ~/ 60;
  final seconds = (secondsPerMile % 60).round();
  return '$minutes:${seconds.toString().padLeft(2, '0')}';
}

/// Speed in MPH rounded to 1 decimal. For cycling display.
String formatSpeedMph(double? speedMps) {
  if (speedMps == null || speedMps < 0) return '--';
  return mpsToMph(speedMps).toStringAsFixed(1);
}

/// Distance as "X.XX mi" — miles with 2 decimal precision.
String formatDistanceMiles(double meters) {
  return '${metersToMiles(meters).toStringAsFixed(2)} mi';
}

/// Duration as "HH:MM:SS" or "MM:SS" if under an hour.
String formatDuration(Duration d) {
  final h = d.inHours;
  final m = d.inMinutes % 60;
  final s = d.inSeconds % 60;
  if (h > 0) {
    return '$h:${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
  }
  return '${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
}

String formatElevationFeet(double meters) {
  return '${metersToFeet(meters).round()} ft';
}

// =======================================================================
// ACTIVITY TYPE
//
// Our three supported activities. The enum drives:
//   - UI labels + icons
//   - Which display format to use (run/walk show pace, cycling shows mph)
//   - Auto-pause thresholds (see _thresholdsFor below)
//   - HealthKit workout type mapping (Session 3)
//   - Calorie MET coefficient (Session 3)
// =======================================================================

enum ActivityType { run, walk, ride }

String activityTypeLabel(ActivityType t) {
  switch (t) {
    case ActivityType.run:
      return 'Run';
    case ActivityType.walk:
      return 'Walk';
    case ActivityType.ride:
      return 'Ride';
  }
}

String activityTypeSerialize(ActivityType t) {
  switch (t) {
    case ActivityType.run:
      return 'run';
    case ActivityType.walk:
      return 'walk';
    case ActivityType.ride:
      return 'ride';
  }
}

ActivityType activityTypeParse(String? raw) {
  switch (raw?.toLowerCase().trim()) {
    case 'walk':
      return ActivityType.walk;
    case 'ride':
    case 'cycle':
    case 'bike':
      return ActivityType.ride;
    case 'run':
    default:
      return ActivityType.run;
  }
}

IconData activityTypeIcon(ActivityType t) {
  switch (t) {
    case ActivityType.run:
      return Icons.directions_run_rounded;
    case ActivityType.walk:
      return Icons.directions_walk_rounded;
    case ActivityType.ride:
      return Icons.directions_bike_rounded;
  }
}

/// Primary stat to feature for this activity. Runners + walkers care
/// about pace (min/mile); cyclists care about speed (mph). The active-
/// run UI reads this to decide which huge number to put front-and-center.
enum PrimaryStat { pacePerMile, speedMph }

PrimaryStat primaryStatFor(ActivityType t) {
  switch (t) {
    case ActivityType.run:
    case ActivityType.walk:
      return PrimaryStat.pacePerMile;
    case ActivityType.ride:
      return PrimaryStat.speedMph;
  }
}

// =======================================================================
// AUTO-PAUSE THRESHOLDS
//
// Auto-pause is the thing most likely to annoy users if tuned wrong.
// We use HYSTERESIS — different enter/exit speeds to prevent flapping
// when a runner stops at a crosswalk and shuffles a step forward.
//
// These numbers come from a combination of Strava's defaults (where
// they're documented via GPS-community reverse-engineering) and our
// own judgment for walking, which Strava doesn't auto-pause.
//
// `minDwellSeconds` is how long the speed must STAY under the threshold
// before we actually declare a pause. Prevents single bad GPS fixes
// from triggering false pauses.
// =======================================================================

class _AutoPauseThresholds {
  final double pauseBelowMps;
  final double resumeAboveMps;
  final int minDwellSeconds;
  const _AutoPauseThresholds({
    required this.pauseBelowMps,
    required this.resumeAboveMps,
    required this.minDwellSeconds,
  });
}

/// Activity-tuned auto-pause thresholds. Documented values:
///   Running: pause below 2.0 mph / 0.89 m/s, resume above 3.0 mph /
///     1.34 m/s, dwell 3s. A walker pace is ~3 mph so runner auto-
///     pause won't trigger if they slow to a walk — they'd need to
///     stop entirely.
///   Walking: pause below 0.8 mph / 0.36 m/s, resume above 1.5 mph /
///     0.67 m/s, dwell 5s. Walkers naturally have more pace variance
///     (chatting with a friend, standing at a corner) so we need a
///     lower floor and longer dwell.
///   Cycling: pause below 3.0 mph / 1.34 m/s, resume above 5.0 mph /
///     2.24 m/s, dwell 5s. Stops-at-stoplights are the main use case.
_AutoPauseThresholds _thresholdsFor(ActivityType t) {
  switch (t) {
    case ActivityType.run:
      return const _AutoPauseThresholds(
        pauseBelowMps: 0.89,
        resumeAboveMps: 1.34,
        minDwellSeconds: 3,
      );
    case ActivityType.walk:
      return const _AutoPauseThresholds(
        pauseBelowMps: 0.36,
        resumeAboveMps: 0.67,
        minDwellSeconds: 5,
      );
    case ActivityType.ride:
      return const _AutoPauseThresholds(
        pauseBelowMps: 1.34,
        resumeAboveMps: 2.24,
        minDwellSeconds: 5,
      );
  }
}

// =======================================================================
// GPS FILTER CONSTANTS
//
// Raw GPS is noisy. Without filtering, a runner standing still can
// "gain" 50 feet of distance just from GPS jitter. These constants
// control how aggressively we reject bad fixes.
// =======================================================================

/// Reject fixes with horizontal accuracy worse than this. A fix with
/// 50m accuracy is worse than no fix for computing distance — it can
/// add 100m of phantom distance with each update.
const double _maxAccuracyMeters = 30.0;

/// If two fixes are closer than this, we treat them as jitter and
/// don't add the delta to total distance. Calibrated for typical
/// consumer GPS noise floor.
const double _minPointDeltaMeters = 3.0;

/// If two consecutive fixes would imply a speed faster than this, the
/// second fix is rejected as an outlier (the runner did not just
/// teleport 200 meters). 40 m/s is ~90 mph, comfortably above even
/// elite cyclists descending.
const double _maxPlausibleSpeedMps = 40.0;

/// Rolling window size for pace smoothing. Instantaneous pace is so
/// noisy the display jitters 6:30 → 9:15 → 7:45 every second, which
/// is useless. Averaging over the last N fixes feels much better.
const int _paceSmoothingWindowPoints = 10;

/// How often the tracking service emits an "update" to listeners.
/// Higher than the GPS sample rate would waste UI frames; lower would
/// make the live-pace display feel laggy. 500ms is a good balance.
const Duration _updateTickInterval = Duration(milliseconds: 500);

/// How often RunPersistenceService checkpoints to Firestore. A phone
/// crash loses at most this much data. 15s is the sweet spot between
/// Firestore write cost and crash-resilience.
const Duration _checkpointInterval = Duration(seconds: 15);

/// ActivitySplit distance for run/walk. Per-mile splits are the standard for
/// US users. Cyclists get per-5-mile splits because per-mile splits
/// on a 40-mile ride is a wall of numbers.
double splitDistanceMetersFor(ActivityType t) {
  switch (t) {
    case ActivityType.run:
    case ActivityType.walk:
      return _metersPerMile;
    case ActivityType.ride:
      return _metersPerMile * 5;
  }
}

// =======================================================================
// GPS POINT
//
// A single sample from the Geolocator stream, normalized. Stored as
// a point in users/{uid}/activities/{id}/points subcollection.
//
// `sequenceNum` matters because GPS timestamps occasionally collide
// (platform returns two fixes with the same second) and we want a
// total ordering when we read points back for map rendering.
// =======================================================================

@immutable
class GpsPoint {
  final double lat;
  final double lng;
  final double? altitudeMeters;
  final double? speedMps;
  final double? accuracyMeters;
  final DateTime timestamp;
  final int sequenceNum;

  const GpsPoint({
    required this.lat,
    required this.lng,
    this.altitudeMeters,
    this.speedMps,
    this.accuracyMeters,
    required this.timestamp,
    required this.sequenceNum,
  });

  factory GpsPoint.fromGeolocator(Position p, int sequenceNum) {
    return GpsPoint(
      lat: p.latitude,
      lng: p.longitude,
      altitudeMeters: p.altitude,
      speedMps: p.speed >= 0 ? p.speed : null, // negative = unknown
      accuracyMeters: p.accuracy >= 0 ? p.accuracy : null,
      timestamp: p.timestamp,
      sequenceNum: sequenceNum,
    );
  }

  Map<String, dynamic> toFirestore() {
    return {
      'lat': lat,
      'lng': lng,
      if (altitudeMeters != null) 'altitudeMeters': altitudeMeters,
      if (speedMps != null) 'speedMps': speedMps,
      if (accuracyMeters != null) 'accuracyMeters': accuracyMeters,
      'timestamp': Timestamp.fromDate(timestamp),
      'sequenceNum': sequenceNum,
      // Bucket points into 100-point groups. Lets us paginate the map
      // render for very long rides without reading 5000 docs at once.
      'bucket': sequenceNum ~/ 100,
    };
  }

  factory GpsPoint.fromFirestore(Map<String, dynamic> m) {
    return GpsPoint(
      lat: (m['lat'] as num).toDouble(),
      lng: (m['lng'] as num).toDouble(),
      altitudeMeters: (m['altitudeMeters'] as num?)?.toDouble(),
      speedMps: (m['speedMps'] as num?)?.toDouble(),
      accuracyMeters: (m['accuracyMeters'] as num?)?.toDouble(),
      timestamp: (m['timestamp'] as Timestamp).toDate(),
      sequenceNum: (m['sequenceNum'] as num).toInt(),
    );
  }
}

// =======================================================================
// HAVERSINE DISTANCE
//
// Great-circle distance between two lat/lng points in meters. The
// Geolocator.distanceBetween() static does this too but we use a
// pure-Dart version so the ActivitySession model can be unit-tested
// without platform channels.
//
// Error on distances under 10km is < 0.5%, well below GPS noise floor.
// =======================================================================

const double _earthRadiusMeters = 6371000.0;

double haversineMeters(double lat1, double lng1, double lat2, double lng2) {
  final dLat = _degToRad(lat2 - lat1);
  final dLng = _degToRad(lng2 - lng1);
  final a = math.sin(dLat / 2) * math.sin(dLat / 2) +
      math.cos(_degToRad(lat1)) *
          math.cos(_degToRad(lat2)) *
          math.sin(dLng / 2) *
          math.sin(dLng / 2);
  final c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a));
  return _earthRadiusMeters * c;
}

double _degToRad(double d) => d * math.pi / 180.0;

// =======================================================================
// SPLIT
//
// A single split (one mile for run/walk, 5 miles for cycling). Emitted
// each time the session crosses a split boundary. Used for the post-
// run summary display ("Mile 1: 8:42, Mile 2: 8:38, Mile 3: 8:51 ...").
// =======================================================================

@immutable
class ActivitySplit {
  final int index; // 0-based, mile 1 = index 0
  final double distanceMeters; // actual distance in this split
  final Duration duration;
  final double avgSpeedMps;
  final double elevationGainMeters;

  const ActivitySplit({
    required this.index,
    required this.distanceMeters,
    required this.duration,
    required this.avgSpeedMps,
    required this.elevationGainMeters,
  });

  /// Pace for this split as min:ss.
  String get paceMinPerMile => formatPaceMinPerMile(avgSpeedMps);

  Map<String, dynamic> toFirestore() {
    return {
      'index': index,
      'distanceMeters': distanceMeters,
      'durationSeconds': duration.inSeconds,
      'avgSpeedMps': avgSpeedMps,
      'elevationGainMeters': elevationGainMeters,
    };
  }

  factory ActivitySplit.fromFirestore(Map<String, dynamic> m) {
    return ActivitySplit(
      index: (m['index'] as num).toInt(),
      distanceMeters: (m['distanceMeters'] as num).toDouble(),
      duration: Duration(seconds: (m['durationSeconds'] as num).toInt()),
      avgSpeedMps: (m['avgSpeedMps'] as num).toDouble(),
      elevationGainMeters: (m['elevationGainMeters'] as num).toDouble(),
    );
  }
}

// =======================================================================
// ACTIVITY STATS
//
// Derived, computed numbers for the current session. Recomputed by the
// tracking service every update tick. This is the data the UI reads
// to render live stats.
//
// Immutable snapshot — every update produces a new one. Makes it
// trivial to compare against the previous state for "did anything
// actually change" optimizations.
// =======================================================================

@immutable
class ActivityStats {
  final double distanceMeters;
  final Duration elapsed; // wall-clock since start
  final Duration movingTime; // elapsed minus paused durations
  final double? currentSpeedMps; // smoothed
  final double? avgSpeedMps; // over entire moving time
  final double elevationGainMeters;
  final double elevationLossMeters;
  final int pointCount;
  final int splitCount;

  const ActivityStats({
    required this.distanceMeters,
    required this.elapsed,
    required this.movingTime,
    this.currentSpeedMps,
    this.avgSpeedMps,
    required this.elevationGainMeters,
    required this.elevationLossMeters,
    required this.pointCount,
    required this.splitCount,
  });

  factory ActivityStats.empty() {
    return const ActivityStats(
      distanceMeters: 0,
      elapsed: Duration.zero,
      movingTime: Duration.zero,
      currentSpeedMps: null,
      avgSpeedMps: null,
      elevationGainMeters: 0,
      elevationLossMeters: 0,
      pointCount: 0,
      splitCount: 0,
    );
  }

  String get distanceDisplay => formatDistanceMiles(distanceMeters);
  String get durationDisplay => formatDuration(movingTime);
  String get currentPaceDisplay => formatPaceMinPerMile(currentSpeedMps);
  String get avgPaceDisplay => formatPaceMinPerMile(avgSpeedMps);
  String get currentSpeedDisplay => formatSpeedMph(currentSpeedMps);
  String get avgSpeedDisplay => formatSpeedMph(avgSpeedMps);
  String get elevationGainDisplay => formatElevationFeet(elevationGainMeters);
}

// =======================================================================
// SESSION STATUS
//
// The activity state machine. Valid transitions:
//
//   idle ──start()──▶ recording ──pause()──▶ paused
//                         │                     │
//                         │                  resume()
//                         │                     │
//                         ◀─────────────────────┘
//                         │
//                      stop()
//                         │
//                         ▼
//                     completed  (terminal)
//                         ▲
//                         │
//                         └── discard()  also sets status=discarded
//                                         which is terminal too
//
// Auto-pause sets status=paused same as manual pause; the "autoPaused"
// flag distinguishes so the UI can show a different message ("Auto-
// paused, start moving to resume") vs manual.
// =======================================================================

enum SessionStatus { idle, recording, paused, completed, discarded }

bool _isActive(SessionStatus s) =>
    s == SessionStatus.recording || s == SessionStatus.paused;
bool _isTerminal(SessionStatus s) =>
    s == SessionStatus.completed || s == SessionStatus.discarded;

// =======================================================================
// ACTIVITY SESSION
//
// The heart of the engine. Holds every piece of state for one in-
// progress (or finished) activity.
//
// Not a ChangeNotifier — this is meant to be an immutable-ish data
// class. The SERVICE owns the lifecycle; it builds updated sessions
// and broadcasts them. That separation keeps this class easy to
// reason about and unit-test.
//
// The `points` and `splits` fields are stored as lists because we
// DO mutate them during recording (appending). Callers treat them
// as read-only when they receive a session snapshot.
// =======================================================================

class ActivitySession {
  /// Stable id. Doubles as the Firestore doc id.
  final String id;

  /// What kind of activity.
  final ActivityType type;

  /// Wall-clock start. Doesn't change across pauses.
  final DateTime startedAt;

  /// Wall-clock end (set on stop/discard).
  DateTime? endedAt;

  /// Current lifecycle state.
  SessionStatus status;

  /// True if the current paused state was triggered by auto-pause
  /// detection rather than a user tap. Reset when manually paused or
  /// when recording resumes.
  bool autoPaused;

  /// Total time spent paused across ALL pauses in this session. Used
  /// to compute moving time = wallClockElapsed - totalPausedTime.
  Duration totalPausedTime;

  /// Timestamp of the most recent transition INTO paused state.
  /// Null when not currently paused. Used to accumulate totalPausedTime
  /// when we transition back to recording.
  DateTime? pausedAt;

  /// All GPS fixes this session has accepted after filtering.
  /// Typically ~1 per second. Not all will be written to Firestore
  /// immediately — the persistence service batches.
  final List<GpsPoint> points;

  /// Completed splits (one entry per split boundary crossed).
  final List<ActivitySplit> splits;

  /// Total distance in meters accumulated across all accepted points.
  /// Computed incrementally (not reducing over `points` each time) so
  /// this stays O(1) per update even for 2-hour rides.
  double distanceMeters;

  /// Total elevation gain/loss. Incrementally accumulated. Uses a
  /// dead-band filter (changes under 1m are noise) to avoid wildly
  /// overstating elevation like some fitness apps do.
  double elevationGainMeters;
  double elevationLossMeters;

  /// Optional user-entered notes, set at save time.
  String? notes;

  /// Device model string. Stored for debugging weird GPS behavior.
  String? deviceModel;

  ActivitySession({
    required this.id,
    required this.type,
    required this.startedAt,
    this.endedAt,
    required this.status,
    this.autoPaused = false,
    this.totalPausedTime = Duration.zero,
    this.pausedAt,
    List<GpsPoint>? points,
    List<ActivitySplit>? splits,
    this.distanceMeters = 0.0,
    this.elevationGainMeters = 0.0,
    this.elevationLossMeters = 0.0,
    this.notes,
    this.deviceModel,
  })  : points = points ?? <GpsPoint>[],
        splits = splits ?? <ActivitySplit>[];

  /// Fresh session ready to record. Generates a new UUIDv4 as the id.
  factory ActivitySession.startFresh(ActivityType type) {
    return ActivitySession(
      id: const Uuid().v4(),
      type: type,
      startedAt: DateTime.now(),
      status: SessionStatus.recording,
    );
  }

  // ------------------------------------------------------------------
  // DERIVED STATS
  // Read-only accessors. Always computed from fields above.
  // ------------------------------------------------------------------

  /// Wall-clock duration from start to either end or now.
  Duration get wallClockElapsed {
    final end = endedAt ?? DateTime.now();
    return end.difference(startedAt);
  }

  /// Moving time = wall-clock elapsed minus time spent paused. This
  /// is the time runners actually care about — "how long did I run
  /// for" not "how long between hitting start and hitting stop".
  Duration get movingTime {
    var paused = totalPausedTime;
    if (status == SessionStatus.paused && pausedAt != null) {
      // Currently paused — include the in-progress pause.
      paused += DateTime.now().difference(pausedAt!);
    }
    final wall = wallClockElapsed;
    if (paused >= wall) return Duration.zero;
    return wall - paused;
  }

  /// Average speed in m/s across moving time only. Null if no distance
  /// or zero moving time.
  double? get avgSpeedMps {
    final mt = movingTime.inSeconds;
    if (mt <= 0 || distanceMeters <= 0) return null;
    return distanceMeters / mt;
  }

  /// Current speed as the smoothed rolling average over the last N
  /// accepted points. Null if too few points to form a window.
  double? get currentSpeedMps {
    if (points.length < 2) return null;
    final windowSize = math.min(_paceSmoothingWindowPoints, points.length);
    final window = points.sublist(points.length - windowSize);
    // Sum up segment distances + durations within the window.
    double dist = 0;
    Duration dur = Duration.zero;
    for (int i = 1; i < window.length; i++) {
      final a = window[i - 1];
      final b = window[i];
      dist += haversineMeters(a.lat, a.lng, b.lat, b.lng);
      dur += b.timestamp.difference(a.timestamp);
    }
    if (dur.inMilliseconds <= 0 || dist <= 0) return null;
    return dist / (dur.inMilliseconds / 1000.0);
  }

  /// Snapshot the derived stats. Convenient for the service to hand
  /// to UI via its notifier.
  ActivityStats get stats => ActivityStats(
        distanceMeters: distanceMeters,
        elapsed: wallClockElapsed,
        movingTime: movingTime,
        currentSpeedMps: currentSpeedMps,
        avgSpeedMps: avgSpeedMps,
        elevationGainMeters: elevationGainMeters,
        elevationLossMeters: elevationLossMeters,
        pointCount: points.length,
        splitCount: splits.length,
      );

  // ------------------------------------------------------------------
  // FIRESTORE SERIALIZATION
  // Summary doc only — points live in a subcollection written by the
  // persistence service, not this class.
  // ------------------------------------------------------------------

  Map<String, dynamic> toSummaryFirestore() {
    final s = avgSpeedMps;
    return {
      'type': activityTypeSerialize(type),
      'startedAt': Timestamp.fromDate(startedAt),
      if (endedAt != null) 'endedAt': Timestamp.fromDate(endedAt!),
      'distanceMeters': distanceMeters,
      'durationSeconds': wallClockElapsed.inSeconds,
      'movingSeconds': movingTime.inSeconds,
      if (s != null) 'avgSpeedMetersPerSecond': s,
      if (s != null && s > 0) 'avgPaceSecondsPerMeter': 1.0 / s,
      'elevationGainMeters': elevationGainMeters,
      'elevationLossMeters': elevationLossMeters,
      'splits': splits.map((x) => x.toFirestore()).toList(),
      'status': _statusSerialize(status),
      'pointCount': points.length,
      'autoPaused': autoPaused,
      'totalPausedSeconds': totalPausedTime.inSeconds,
      if (notes != null && notes!.isNotEmpty) 'notes': notes,
      if (deviceModel != null) 'deviceModel': deviceModel,
      'updatedAt': FieldValue.serverTimestamp(),
    };
  }

  /// Reconstruct a session from a summary doc. Used by the persistence
  /// service when resuming a crashed run. Points are loaded separately
  /// from the subcollection.
  factory ActivitySession.fromSummaryFirestore(
    String id,
    Map<String, dynamic> m,
  ) {
    final rawSplits = m['splits'];
    final splits = <ActivitySplit>[];
    if (rawSplits is List) {
      for (final s in rawSplits) {
        if (s is Map<String, dynamic>) {
          try {
            splits.add(ActivitySplit.fromFirestore(s));
          } catch (_) {
            // Malformed split — skip rather than crash the whole load.
          }
        }
      }
    }
    return ActivitySession(
      id: id,
      type: activityTypeParse(m['type'] as String?),
      startedAt: (m['startedAt'] as Timestamp).toDate(),
      endedAt: (m['endedAt'] as Timestamp?)?.toDate(),
      status: _statusParse(m['status'] as String?),
      autoPaused: (m['autoPaused'] as bool?) ?? false,
      totalPausedTime:
          Duration(seconds: (m['totalPausedSeconds'] as num?)?.toInt() ?? 0),
      splits: splits,
      distanceMeters: (m['distanceMeters'] as num?)?.toDouble() ?? 0,
      elevationGainMeters: (m['elevationGainMeters'] as num?)?.toDouble() ?? 0,
      elevationLossMeters: (m['elevationLossMeters'] as num?)?.toDouble() ?? 0,
      notes: m['notes'] as String?,
      deviceModel: m['deviceModel'] as String?,
    );
  }
}

String _statusSerialize(SessionStatus s) {
  switch (s) {
    case SessionStatus.idle:
      return 'idle';
    case SessionStatus.recording:
      return 'recording';
    case SessionStatus.paused:
      return 'paused';
    case SessionStatus.completed:
      return 'completed';
    case SessionStatus.discarded:
      return 'discarded';
  }
}

SessionStatus _statusParse(String? raw) {
  switch (raw) {
    case 'recording':
      return SessionStatus.recording;
    case 'paused':
      return SessionStatus.paused;
    case 'completed':
      return SessionStatus.completed;
    case 'discarded':
      return SessionStatus.discarded;
    case 'idle':
    default:
      return SessionStatus.idle;
  }
}

// =======================================================================
// RUN TRACKING SERVICE
//
// The owner of the GPS stream + the session lifecycle. This is the
// class UI code interacts with for start/pause/resume/stop.
//
// USAGE (for future session-2 UI code):
//
//   final tracking = RunTrackingService();
//   await tracking.start(ActivityType.run);
//   // ... UI subscribes to `tracking` via ChangeNotifier listener
//   tracking.pause();         // manual pause
//   tracking.resume();
//   final session = await tracking.stop();  // returns final session
//
// THREADING:
//   All work happens on the main isolate. The Geolocator plugin
//   already delivers platform callbacks there. We use a periodic
//   Timer for the UI update tick (separate from the GPS sample rate).
//
// AUTO-PAUSE STATE MACHINE:
//   Runs on every accepted GPS fix. We track two values:
//     _slowStartedAt: when the rolling speed first went below the
//       pause threshold (null if currently above)
//     _fastStartedAt: same for resume threshold
//   When the "below" streak exceeds minDwellSeconds we auto-pause.
//   When the "above" streak exceeds a small resume dwell we auto-
//   resume. This is hysteresis in action — the two thresholds are
//   different so a runner jogging-then-walking-then-jogging doesn't
//   flap the pause state.
// =======================================================================

class RunTrackingService extends ChangeNotifier {
  ActivitySession? _session;
  ActivityType? _activityType;
  StreamSubscription<Position>? _positionSub;
  Timer? _updateTicker;

  // Last-notify throttle. We only call notifyListeners() at most once
  // per _updateTickInterval to avoid spamming UI frames on every GPS
  // fix when fix rate is high.
  DateTime _lastNotify = DateTime.fromMillisecondsSinceEpoch(0);

  // Auto-pause state machine scratchpad.
  DateTime? _slowStartedAt;
  DateTime? _fastStartedAt;
  static const int _autoResumeDwellSeconds = 2;

  // Sequence counter for GpsPoint.sequenceNum. Monotonic across the
  // session — never reset even across pauses.
  int _seq = 0;

  /// The session currently being recorded, or null if idle / no run
  /// has been started yet. Callers in session 2+ will read this to
  /// drive UI.
  ActivitySession? get session => _session;

  /// Shortcut for UI — null if no session.
  ActivityStats? get stats => _session?.stats;

  /// Whether the service is currently recording or paused (not idle
  /// and not completed).
  bool get isActive => _session != null && _isActive(_session!.status);

  /// Whether currently paused (auto or manual).
  bool get isPaused => _session?.status == SessionStatus.paused;

  /// Whether the current pause is from auto-pause detection (vs. user
  /// tapping the pause button). Callers use this to change the pause
  /// banner's message.
  bool get isAutoPaused => isPaused && (_session?.autoPaused ?? false);

  // ------------------------------------------------------------------
  // LIFECYCLE
  // ------------------------------------------------------------------

  /// Begin a new recording session. Requests location permission if
  /// not already granted. Throws on permission denial — caller is
  /// responsible for surfacing a user-friendly error.
  Future<void> start(ActivityType type) async {
    if (isActive) {
      throw StateError(
          'Cannot start: another session is already active (id=${_session?.id}).');
    }

    // Permission gate. `whileInUse` is the minimum — `always` is
    // better for background runs but on iOS requires a separate
    // system prompt that can only appear on a second launch. See
    // SETUP.md for the full permission-primer flow plan.
    final perm = await Geolocator.checkPermission();
    if (perm == LocationPermission.denied) {
      final requested = await Geolocator.requestPermission();
      if (requested == LocationPermission.denied ||
          requested == LocationPermission.deniedForever) {
        throw const LocationPermissionDeniedException();
      }
    } else if (perm == LocationPermission.deniedForever) {
      throw const LocationPermissionDeniedException();
    }

    final serviceOn = await Geolocator.isLocationServiceEnabled();
    if (!serviceOn) {
      throw const LocationServiceDisabledException();
    }

    _activityType = type;
    _session = ActivitySession.startFresh(type);
    _seq = 0;
    _slowStartedAt = null;
    _fastStartedAt = null;

    _analytics('activity_started', {
      'type': activityTypeSerialize(type),
      'sessionId': _session!.id,
    });

    _startPositionStream(type);
    _startUpdateTicker();
    notifyListeners();
  }

  /// Manual pause. Safe to call while already paused (no-op).
  void pause() {
    final s = _session;
    if (s == null || s.status != SessionStatus.recording) return;
    s.status = SessionStatus.paused;
    s.autoPaused = false;
    s.pausedAt = DateTime.now();
    _slowStartedAt = null;
    _fastStartedAt = null;
    _analytics('activity_paused', {
      'sessionId': s.id,
      'mode': 'manual',
    });
    notifyListeners();
  }

  /// Resume from pause (auto or manual). Safe to call when already
  /// recording.
  void resume() {
    final s = _session;
    if (s == null || s.status != SessionStatus.paused) return;
    if (s.pausedAt != null) {
      s.totalPausedTime += DateTime.now().difference(s.pausedAt!);
      s.pausedAt = null;
    }
    s.status = SessionStatus.recording;
    s.autoPaused = false;
    _slowStartedAt = null;
    _fastStartedAt = null;
    _analytics('activity_resumed', {
      'sessionId': s.id,
    });
    notifyListeners();
  }

  /// Stop and finalize. Returns the completed session. After this
  /// call, `session` still points to the now-completed session until
  /// the UI navigates away and calls `discardCompletedSession()`.
  Future<ActivitySession> stop() async {
    final s = _session;
    if (s == null) {
      throw StateError('Cannot stop: no session in progress.');
    }
    // Accumulate the final pause window if paused when stopped.
    if (s.status == SessionStatus.paused && s.pausedAt != null) {
      s.totalPausedTime += DateTime.now().difference(s.pausedAt!);
      s.pausedAt = null;
    }
    s.status = SessionStatus.completed;
    s.endedAt = DateTime.now();

    await _positionSub?.cancel();
    _positionSub = null;
    _updateTicker?.cancel();
    _updateTicker = null;

    _analytics('activity_stopped', {
      'sessionId': s.id,
      'type': activityTypeSerialize(s.type),
      'distanceMeters': s.distanceMeters.round(),
      'movingSeconds': s.movingTime.inSeconds,
      'pointCount': s.points.length,
    });

    notifyListeners();
    return s;
  }

  /// Mark the session as discarded. Does not delete from Firestore —
  /// the persistence service's cleanup job handles that.
  Future<ActivitySession> discard() async {
    final s = _session;
    if (s == null) {
      throw StateError('Cannot discard: no session in progress.');
    }
    if (s.status == SessionStatus.paused && s.pausedAt != null) {
      s.totalPausedTime += DateTime.now().difference(s.pausedAt!);
      s.pausedAt = null;
    }
    s.status = SessionStatus.discarded;
    s.endedAt = DateTime.now();
    await _positionSub?.cancel();
    _positionSub = null;
    _updateTicker?.cancel();
    _updateTicker = null;
    _analytics('activity_discarded', {
      'sessionId': s.id,
      'type': activityTypeSerialize(s.type),
    });
    notifyListeners();
    return s;
  }

  /// Release the completed or discarded session. Call this after the
  /// post-run summary UI has done its thing (saved / shared / closed).
  /// After this, `session` is null until `start()` is called again.
  void clearCompletedSession() {
    if (_session != null && !_isTerminal(_session!.status)) {
      _log('clearCompletedSession called on non-terminal session — ignored');
      return;
    }
    _session = null;
    _activityType = null;
    notifyListeners();
  }

  @override
  void dispose() {
    _positionSub?.cancel();
    _updateTicker?.cancel();
    super.dispose();
  }

  // ------------------------------------------------------------------
  // STREAM SETUP
  // ------------------------------------------------------------------

  // Global user preference for GPS accuracy — set by RunController from
  // RunSettings before startActivity is called. If 'balanced', we downshift
  // from LocationAccuracy.best to .high (roughly 20-30% battery savings
  // with modest precision loss). If 'precise' (default), activity-type
  // defaults win.
  GpsAccuracyChoice _userGpsAccuracy = GpsAccuracyChoice.precise;

  /// Call before startActivity() to let user prefs influence GPS fidelity.
  void setGpsAccuracy(GpsAccuracyChoice choice) {
    _userGpsAccuracy = choice;
  }

  void _startPositionStream(ActivityType type) {
    // Desired accuracy is the LESSER of (user preference) and
    // (activity-type default). Balanced pref trims everything down a
    // notch; precise uses the activity-type default.
    LocationAccuracy accuracy;
    int distanceFilter;
    switch (type) {
      case ActivityType.run:
      case ActivityType.walk:
        accuracy = _userGpsAccuracy == GpsAccuracyChoice.balanced
            ? LocationAccuracy.high
            : LocationAccuracy.best;
        distanceFilter = 0; // every fix, we filter ourselves
        break;
      case ActivityType.ride:
        accuracy = _userGpsAccuracy == GpsAccuracyChoice.balanced
            ? LocationAccuracy.medium
            : LocationAccuracy.high;
        distanceFilter = 0;
        break;
    }

    final settings = LocationSettings(
      accuracy: accuracy,
      distanceFilter: distanceFilter,
    );

    _positionSub?.cancel();
    _positionSub =
        Geolocator.getPositionStream(locationSettings: settings).listen(
      _onPosition,
      onError: (err, st) {
        _logError('position stream error', err, st);
      },
      cancelOnError: false, // keep stream alive on transient errors
    );
  }

  void _startUpdateTicker() {
    _updateTicker?.cancel();
    _updateTicker = Timer.periodic(_updateTickInterval, (_) {
      if (_session == null) return;
      _maybeNotify();
    });
  }

  // ------------------------------------------------------------------
  // GPS FIX HANDLING
  // The one place where distance accumulates, elevation accumulates,
  // splits emit, and auto-pause evaluates.
  // ------------------------------------------------------------------

  void _onPosition(Position p) {
    final s = _session;
    if (s == null || _isTerminal(s.status)) return;

    // Reject if accuracy is poor. A 50m-accuracy fix can add 100m of
    // phantom distance vs. the previous fix.
    if (p.accuracy < 0 || p.accuracy > _maxAccuracyMeters) {
      return;
    }

    final incoming = GpsPoint.fromGeolocator(p, _seq);

    // Dedupe / jitter reject: if the fix is within _minPointDeltaMeters
    // of the last accepted point, treat it as noise.
    if (s.points.isNotEmpty) {
      final last = s.points.last;
      final delta =
          haversineMeters(last.lat, last.lng, incoming.lat, incoming.lng);
      if (delta < _minPointDeltaMeters) {
        // Still feed speed into auto-pause state — a stationary reading
        // counts as "slow" for pause detection.
        _evaluateAutoPause(incoming.speedMps ?? 0.0);
        return;
      }

      // Teleport reject: if implied speed exceeds physical plausibility,
      // drop this fix. (Runner did not just warp 300m in 2 seconds.)
      final dtSec =
          incoming.timestamp.difference(last.timestamp).inMilliseconds / 1000.0;
      if (dtSec > 0) {
        final impliedSpeed = delta / dtSec;
        if (impliedSpeed > _maxPlausibleSpeedMps) {
          _log('rejecting teleport fix: ${impliedSpeed.toStringAsFixed(1)}m/s');
          return;
        }
      }

      // Accept. Accumulate distance and elevation only if recording
      // (not during pause — a paused runner walking to get water
      // should not add distance).
      if (s.status == SessionStatus.recording) {
        s.distanceMeters += delta;
        _accumulateElevation(last, incoming, s);
        _maybeEmitSplit(s);
      }
    }

    _seq++;
    s.points.add(GpsPoint(
      lat: incoming.lat,
      lng: incoming.lng,
      altitudeMeters: incoming.altitudeMeters,
      speedMps: incoming.speedMps,
      accuracyMeters: incoming.accuracyMeters,
      timestamp: incoming.timestamp,
      sequenceNum: _seq,
    ));

    _evaluateAutoPause(incoming.speedMps ?? 0.0);

    // Notify more aggressively right after a split — the UI should
    // re-render immediately with the new split entry.
    _maybeNotify();
  }

  void _accumulateElevation(GpsPoint from, GpsPoint to, ActivitySession s) {
    final a = from.altitudeMeters;
    final b = to.altitudeMeters;
    if (a == null || b == null) return;
    final delta = b - a;
    // Dead-band — ignore sub-meter changes (GPS altitude is noisy).
    if (delta.abs() < 1.0) return;
    if (delta > 0) {
      s.elevationGainMeters += delta;
    } else {
      s.elevationLossMeters += -delta;
    }
  }

  void _maybeEmitSplit(ActivitySession s) {
    final splitDistance = splitDistanceMetersFor(s.type);
    final expectedSplitIndex = (s.distanceMeters / splitDistance).floor();
    // Emit one split per boundary crossed. If we somehow cross two
    // boundaries in one fix (4G-spotty area sync), emit both — the
    // while loop handles that edge case.
    while (s.splits.length < expectedSplitIndex) {
      final nextIndex = s.splits.length;
      // For the split duration, we approximate: this split's share of
      // moving time is proportional to its share of total distance.
      // So if totalMoving=600s and total=3mi, each mile-split ≈ 200s.
      // Precision per-fix split-time would require tracking cumulative
      // moving-time at each GPS point (more state than it's worth
      // for the first version). Session 2 refinement.
      final totalMovingMs = s.movingTime.inMilliseconds;
      final totalDist = s.distanceMeters;
      final splitDurMs = totalDist > 0
          ? (totalMovingMs * (splitDistance / totalDist)).round()
          : 0;
      final splitDur = Duration(milliseconds: splitDurMs);
      final splitSpeed =
          splitDurMs > 0 ? splitDistance / (splitDurMs / 1000.0) : 0.0;
      s.splits.add(ActivitySplit(
        index: nextIndex,
        distanceMeters: splitDistance,
        duration: splitDur,
        avgSpeedMps: splitSpeed,
        elevationGainMeters: 0.0, // Session 2 refinement
      ));
      _analytics('split_emitted', {
        'sessionId': s.id,
        'index': nextIndex,
        'pace': formatPaceMinPerMile(splitSpeed),
      });
      // Force next tick to notify.
      _lastNotify = DateTime.fromMillisecondsSinceEpoch(0);
    }
  }

  // ------------------------------------------------------------------
  // AUTO-PAUSE STATE MACHINE
  // ------------------------------------------------------------------

  void _evaluateAutoPause(double observedSpeedMps) {
    final s = _session;
    final type = _activityType;
    if (s == null || type == null) return;
    // Don't evaluate if we're not in a state where auto-pause makes
    // sense.
    if (_isTerminal(s.status)) return;
    // Only auto-pause from recording. Only auto-resume from paused.
    final t = _thresholdsFor(type);
    final now = DateTime.now();

    if (s.status == SessionStatus.recording) {
      if (observedSpeedMps < t.pauseBelowMps) {
        _slowStartedAt ??= now;
        final dwelled = now.difference(_slowStartedAt!).inSeconds;
        if (dwelled >= t.minDwellSeconds) {
          // Auto-pause.
          s.status = SessionStatus.paused;
          s.autoPaused = true;
          s.pausedAt = now;
          _slowStartedAt = null;
          _fastStartedAt = null;
          _analytics('activity_paused', {
            'sessionId': s.id,
            'mode': 'auto',
          });
          _lastNotify = DateTime.fromMillisecondsSinceEpoch(0);
          notifyListeners();
        }
      } else {
        _slowStartedAt = null;
      }
    } else if (s.status == SessionStatus.paused && s.autoPaused) {
      if (observedSpeedMps > t.resumeAboveMps) {
        _fastStartedAt ??= now;
        final dwelled = now.difference(_fastStartedAt!).inSeconds;
        if (dwelled >= _autoResumeDwellSeconds) {
          // Auto-resume. Accumulate the pause window.
          if (s.pausedAt != null) {
            s.totalPausedTime += now.difference(s.pausedAt!);
            s.pausedAt = null;
          }
          s.status = SessionStatus.recording;
          s.autoPaused = false;
          _slowStartedAt = null;
          _fastStartedAt = null;
          _analytics('activity_resumed', {
            'sessionId': s.id,
            'mode': 'auto',
          });
          _lastNotify = DateTime.fromMillisecondsSinceEpoch(0);
          notifyListeners();
        }
      } else {
        _fastStartedAt = null;
      }
    }
  }

  // ------------------------------------------------------------------
  // NOTIFY THROTTLE
  // ------------------------------------------------------------------

  void _maybeNotify() {
    final now = DateTime.now();
    if (now.difference(_lastNotify) >= _updateTickInterval) {
      _lastNotify = now;
      notifyListeners();
    }
  }
}

// =======================================================================
// TYPED EXCEPTIONS
// Throwable from start() for callers to pattern-match on.
// =======================================================================

class LocationPermissionDeniedException implements Exception {
  const LocationPermissionDeniedException();
  @override
  String toString() => 'Location permission is required to track activities.';
}

class LocationServiceDisabledException implements Exception {
  const LocationServiceDisabledException();
  @override
  String toString() => 'Turn on Location Services to start tracking.';
}

// =======================================================================
// RUN PERSISTENCE SERVICE
//
// Responsible for saving activity data to Firestore. Subscribes to
// the same RunTrackingService notifier and checkpoints in two ways:
//
//   1. SUMMARY DOC: rewritten every _checkpointInterval (15s) while
//      recording. Contains distance / time / splits / status. Small.
//
//   2. POINTS SUBCOLLECTION: new GPS fixes flushed every checkpoint
//      in batches. We track what's already been flushed via
//      `_flushedPointCount` so we don't re-write anything.
//
// CRASH RECOVERY:
//   If the app dies mid-run, the next app launch finds a summary doc
//   with status='recording'. The UI can offer "Resume run?" — call
//   resumeFromFirestore(id), which hydrates a session from Firestore
//   (summary + all points) and hands it back so the tracking service
//   can continue. Live GPS state (the auto-pause dwell timers, etc.)
//   starts fresh; moving time & distance already accumulated are
//   preserved.
//
// CLEANUP:
//   A discarded run stays in Firestore with status='discarded'. A
//   scheduled Cloud Function (not yet written — backend todo) can
//   purge discarded docs > 30 days old if desired.
// =======================================================================

class RunPersistenceService {
  final RunTrackingService tracking;

  /// Number of points that have been written to Firestore already.
  /// Incremented after successful batch writes. Used to know what
  /// range of `session.points` to write next checkpoint.
  int _flushedPointCount = 0;

  /// The session this service is currently persisting. Cleared on
  /// stop/discard.
  ActivitySession? _boundSession;

  Timer? _checkpointTimer;

  /// True once we've created the summary doc at least once. Prevents
  /// spurious "is this a new session" logic when the tracking service
  /// emits an update before the first checkpoint runs.
  bool _summaryCreated = false;

  RunPersistenceService({required this.tracking}) {
    tracking.addListener(_onTrackingUpdate);
  }

  void dispose() {
    _checkpointTimer?.cancel();
    tracking.removeListener(_onTrackingUpdate);
  }

  // ------------------------------------------------------------------
  // LIFECYCLE HOOKS
  // Triggered by tracking service state changes.
  // ------------------------------------------------------------------

  void _onTrackingUpdate() {
    final s = tracking.session;
    if (s == null) {
      // Session was cleared — tear down.
      _teardown();
      return;
    }

    // New session detected — bind.
    if (_boundSession == null || _boundSession!.id != s.id) {
      _bindTo(s);
    }

    // Terminal transitions force an immediate final checkpoint.
    if (s.status == SessionStatus.completed ||
        s.status == SessionStatus.discarded) {
      _checkpointTimer?.cancel();
      _checkpointTimer = null;
      // Fire-and-forget: final checkpoint writes summary + any
      // remaining points.
      unawaited(_checkpoint(final_: true));
    }
  }

  void _bindTo(ActivitySession s) {
    _teardown();
    _boundSession = s;
    _flushedPointCount = 0;
    _summaryCreated = false;
    _checkpointTimer = Timer.periodic(_checkpointInterval, (_) {
      unawaited(_checkpoint());
    });
    // Immediate first summary write so the doc exists even if the
    // user kills the app within the first 15 seconds.
    unawaited(_checkpoint(initial: true));
  }

  void _teardown() {
    _checkpointTimer?.cancel();
    _checkpointTimer = null;
    _boundSession = null;
    _flushedPointCount = 0;
    _summaryCreated = false;
  }

  // ------------------------------------------------------------------
  // CHECKPOINT
  // Writes the summary doc and any new points in batches.
  // ------------------------------------------------------------------

  Future<void> _checkpoint({bool initial = false, bool final_ = false}) async {
    final s = _boundSession;
    if (s == null) return;

    final uid = FirebaseAuth.instance.currentUser?.uid;
    if (uid == null) {
      _log('checkpoint skipped: no authenticated user');
      return;
    }

    final docRef = FirebaseFirestore.instance
        .collection('users')
        .doc(uid)
        .collection('activities')
        .doc(s.id);

    try {
      // Summary. On first write use set() with merge so we
      // establish the doc; subsequent writes use update() to minimize
      // payload but set() with merge is idempotent so we just use it.
      final summary = s.toSummaryFirestore();
      if (!_summaryCreated) {
        summary['createdAt'] = FieldValue.serverTimestamp();
      }
      await docRef.set(summary, SetOptions(merge: true));
      _summaryCreated = true;

      // Points batch. Only flush points we haven't flushed yet.
      final total = s.points.length;
      if (total > _flushedPointCount) {
        final toFlush = s.points.sublist(_flushedPointCount, total);
        // Firestore batch limit is 500 writes. In practice a 15s
        // window at ~1Hz GPS = ~15 points, so this is only ever in
        // play during recovery of a long backlog.
        const batchMax = 450;
        for (int i = 0; i < toFlush.length; i += batchMax) {
          final end = math.min(i + batchMax, toFlush.length);
          final slice = toFlush.sublist(i, end);
          final batch = FirebaseFirestore.instance.batch();
          for (final p in slice) {
            final pointRef = docRef
                .collection('points')
                .doc('${p.sequenceNum.toString().padLeft(8, '0')}');
            batch.set(pointRef, p.toFirestore());
          }
          await batch.commit();
        }
        _flushedPointCount = total;
      }

      _log(
          'checkpoint${initial ? " (initial)" : ""}${final_ ? " (final)" : ""}: '
          'sessionId=${s.id}, points=$_flushedPointCount/$total, '
          'dist=${s.distanceMeters.round()}m, status=${_statusSerialize(s.status)}');
    } catch (e, st) {
      _logError('checkpoint failed', e, st);
      // Non-fatal — next checkpoint will catch up.
    }
  }

  // ------------------------------------------------------------------
  // RECOVERY
  // Look for runs stuck in 'recording' state from before a crash.
  // ------------------------------------------------------------------

  /// Return any activities with status='recording' for the current
  /// user. Typically called on app launch. If the list is non-empty,
  /// the UI should offer "Resume run?" for each.
  static Future<List<ActivitySession>> findInterruptedRuns() async {
    final uid = FirebaseAuth.instance.currentUser?.uid;
    if (uid == null) return const [];
    try {
      final snap = await FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('activities')
          .where('status', isEqualTo: 'recording')
          .orderBy('startedAt', descending: true)
          .limit(5)
          .get();
      final out = <ActivitySession>[];
      for (final doc in snap.docs) {
        try {
          final s = ActivitySession.fromSummaryFirestore(doc.id, doc.data());
          out.add(s);
        } catch (e, st) {
          _logError('skipped malformed recovery candidate ${doc.id}', e, st);
        }
      }
      _log('findInterruptedRuns: ${out.length} candidate(s)');
      return out;
    } catch (e, st) {
      _logError('findInterruptedRuns query failed', e, st);
      return const [];
    }
  }

  /// Load an activity's points subcollection into memory. Used by the
  /// recovery flow + by the run detail screen (Session 4) for map
  /// rendering. Loads all points — fine for runs up to a few thousand
  /// points. Very long rides (10k+ points) might want pagination;
  /// noted for future optimization.
  static Future<List<GpsPoint>> loadPoints(String activityId) async {
    final uid = FirebaseAuth.instance.currentUser?.uid;
    if (uid == null) return const [];
    try {
      final snap = await FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('activities')
          .doc(activityId)
          .collection('points')
          .orderBy('sequenceNum')
          .get();
      final out = <GpsPoint>[];
      for (final doc in snap.docs) {
        try {
          out.add(GpsPoint.fromFirestore(doc.data()));
        } catch (e) {
          _logError('skipped malformed point ${doc.id}', e);
        }
      }
      return out;
    } catch (e, st) {
      _logError('loadPoints failed for activity $activityId', e, st);
      return const [];
    }
  }

  /// Mark a stale-but-not-crashed session as abandoned. Useful when
  /// the user chooses "discard" on a recovery prompt.
  static Future<void> markDiscarded(String activityId) async {
    final uid = FirebaseAuth.instance.currentUser?.uid;
    if (uid == null) return;
    try {
      await FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('activities')
          .doc(activityId)
          .set({
        'status': 'discarded',
        'endedAt': FieldValue.serverTimestamp(),
        'updatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));
      _log('markDiscarded: $activityId');
    } catch (e, st) {
      _logError('markDiscarded failed for $activityId', e, st);
    }
  }
}

enum PrimaryStatChoice {
  pace, // run/walk default
  speed, // cycling default
  distance,
  duration,
}

String primaryStatChoiceLabel(PrimaryStatChoice c) {
  switch (c) {
    case PrimaryStatChoice.pace:
      return 'Pace';
    case PrimaryStatChoice.speed:
      return 'Speed';
    case PrimaryStatChoice.distance:
      return 'Distance';
    case PrimaryStatChoice.duration:
      return 'Time';
  }
}

String _primaryStatChoiceSerialize(PrimaryStatChoice c) {
  switch (c) {
    case PrimaryStatChoice.pace:
      return 'pace';
    case PrimaryStatChoice.speed:
      return 'speed';
    case PrimaryStatChoice.distance:
      return 'distance';
    case PrimaryStatChoice.duration:
      return 'duration';
  }
}

PrimaryStatChoice _primaryStatChoiceParse(String? raw) {
  switch (raw) {
    case 'speed':
      return PrimaryStatChoice.speed;
    case 'distance':
      return PrimaryStatChoice.distance;
    case 'duration':
      return PrimaryStatChoice.duration;
    case 'pace':
    default:
      return PrimaryStatChoice.pace;
  }
}

// GPS accuracy level. Balanced trades a bit of precision for better
// battery life; precise uses LocationAccuracy.best (best battery-murderer
// the phone supports). Most users should leave this on precise — modern
// phones can sustain it for a 2-3 hour run with room to spare.
enum GpsAccuracyChoice { balanced, precise }

String gpsAccuracyChoiceLabel(GpsAccuracyChoice c) {
  switch (c) {
    case GpsAccuracyChoice.balanced:
      return 'Balanced';
    case GpsAccuracyChoice.precise:
      return 'Precise';
  }
}

// =======================================================================
// RUN SETTINGS
//
// User prefs, persisted to Firestore. Loaded once on RunController
// init, re-saved whenever the user changes them. Cached in-memory for
// fast reads during an active run (we can't have settings blocking on
// network just to render the active screen).
//
// Defaults are what gets used when a user first opens the feature
// before any settings have been saved.
// =======================================================================

class RunSettings {
  final PrimaryStatChoice primaryStatForRun;
  final PrimaryStatChoice primaryStatForWalk;
  final PrimaryStatChoice primaryStatForRide;
  final bool voiceCuesEnabled;
  final double voiceVolume; // 0.0 to 1.0
  final bool autoPauseEnabled;
  final bool keepScreenOn;
  final bool useMetric; // false = miles (US default), true = km
  final GpsAccuracyChoice gpsAccuracy; // balanced or precise
  final double dailyGoalMiles; // 0 = no goal set
  final double weeklyGoalMiles; // 0 = no goal set

  const RunSettings({
    this.primaryStatForRun = PrimaryStatChoice.pace,
    this.primaryStatForWalk = PrimaryStatChoice.pace,
    this.primaryStatForRide = PrimaryStatChoice.speed,
    this.voiceCuesEnabled = true,
    this.voiceVolume = 0.8,
    this.autoPauseEnabled = true,
    this.keepScreenOn = true,
    this.useMetric = false,
    this.gpsAccuracy = GpsAccuracyChoice.precise,
    this.dailyGoalMiles = 0,
    this.weeklyGoalMiles = 0,
  });

  /// Pick the user's preferred primary stat for the given activity.
  PrimaryStatChoice primaryStatFor(String activityTypeSerialized) {
    switch (activityTypeSerialized) {
      case 'walk':
        return primaryStatForWalk;
      case 'ride':
        return primaryStatForRide;
      case 'run':
      default:
        return primaryStatForRun;
    }
  }

  RunSettings copyWith({
    PrimaryStatChoice? primaryStatForRun,
    PrimaryStatChoice? primaryStatForWalk,
    PrimaryStatChoice? primaryStatForRide,
    bool? voiceCuesEnabled,
    double? voiceVolume,
    bool? autoPauseEnabled,
    bool? keepScreenOn,
    bool? useMetric,
    GpsAccuracyChoice? gpsAccuracy,
    double? dailyGoalMiles,
    double? weeklyGoalMiles,
  }) {
    return RunSettings(
      primaryStatForRun: primaryStatForRun ?? this.primaryStatForRun,
      primaryStatForWalk: primaryStatForWalk ?? this.primaryStatForWalk,
      primaryStatForRide: primaryStatForRide ?? this.primaryStatForRide,
      voiceCuesEnabled: voiceCuesEnabled ?? this.voiceCuesEnabled,
      voiceVolume: voiceVolume ?? this.voiceVolume,
      autoPauseEnabled: autoPauseEnabled ?? this.autoPauseEnabled,
      keepScreenOn: keepScreenOn ?? this.keepScreenOn,
      useMetric: useMetric ?? this.useMetric,
      gpsAccuracy: gpsAccuracy ?? this.gpsAccuracy,
      dailyGoalMiles: dailyGoalMiles ?? this.dailyGoalMiles,
      weeklyGoalMiles: weeklyGoalMiles ?? this.weeklyGoalMiles,
    );
  }

  Map<String, dynamic> toFirestore() {
    return {
      'primaryStatForRun': _primaryStatChoiceSerialize(primaryStatForRun),
      'primaryStatForWalk': _primaryStatChoiceSerialize(primaryStatForWalk),
      'primaryStatForRide': _primaryStatChoiceSerialize(primaryStatForRide),
      'voiceCuesEnabled': voiceCuesEnabled,
      'voiceVolume': voiceVolume,
      'autoPauseEnabled': autoPauseEnabled,
      'keepScreenOn': keepScreenOn,
      'useMetric': useMetric,
      'gpsAccuracy':
          gpsAccuracy == GpsAccuracyChoice.precise ? 'precise' : 'balanced',
      'dailyGoalMiles': dailyGoalMiles,
      'weeklyGoalMiles': weeklyGoalMiles,
      'updatedAt': FieldValue.serverTimestamp(),
    };
  }

  factory RunSettings.fromFirestore(Map<String, dynamic> m) {
    return RunSettings(
      primaryStatForRun:
          _primaryStatChoiceParse(m['primaryStatForRun'] as String?),
      primaryStatForWalk:
          _primaryStatChoiceParse(m['primaryStatForWalk'] as String?),
      primaryStatForRide: m['primaryStatForRide'] == null
          ? PrimaryStatChoice.speed
          : _primaryStatChoiceParse(m['primaryStatForRide'] as String?),
      voiceCuesEnabled: (m['voiceCuesEnabled'] as bool?) ?? true,
      voiceVolume:
          ((m['voiceVolume'] as num?)?.toDouble() ?? 0.8).clamp(0.0, 1.0),
      autoPauseEnabled: (m['autoPauseEnabled'] as bool?) ?? true,
      keepScreenOn: (m['keepScreenOn'] as bool?) ?? true,
      useMetric: (m['useMetric'] as bool?) ?? false,
      gpsAccuracy: (m['gpsAccuracy'] as String?) == 'balanced'
          ? GpsAccuracyChoice.balanced
          : GpsAccuracyChoice.precise,
      dailyGoalMiles: (m['dailyGoalMiles'] as num?)?.toDouble() ?? 0,
      weeklyGoalMiles: (m['weeklyGoalMiles'] as num?)?.toDouble() ?? 0,
    );
  }

  /// Read settings from Firestore for the current user. Returns
  /// defaults if the doc doesn't exist yet or if the user is not
  /// signed in.
  static Future<RunSettings> load() async {
    final uid = FirebaseAuth.instance.currentUser?.uid;
    if (uid == null) return const RunSettings();
    try {
      final doc = await FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('prefs')
          .doc('run')
          .get();
      if (!doc.exists) return const RunSettings();
      final data = doc.data();
      if (data == null) return const RunSettings();
      return RunSettings.fromFirestore(data);
    } catch (e, st) {
      _logError('RunSettings.load failed', e, st);
      return const RunSettings();
    }
  }

  /// Save these settings for the current user.
  Future<void> save() async {
    final uid = FirebaseAuth.instance.currentUser?.uid;
    if (uid == null) return;
    try {
      await FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('prefs')
          .doc('run')
          .set(toFirestore(), SetOptions(merge: true));
      _log('RunSettings saved');
    } catch (e, st) {
      _logError('RunSettings.save failed', e, st);
    }
  }
}

// =======================================================================
// RUN AUDIO CUE SERVICE
//
// Fires TTS announcements at split boundaries. Keeps the user aware
// of their pace without making them look at the phone.
//
// Audio session handling (iOS):
//   When TTS plays, the OS needs to know to DUCK the user's music
//   rather than stop it. audio_session.configure() with the "speech"
//   category handles this. Without it, the user's Spotify gets
//   paused by the TTS engine and doesn't resume.
//
// Background playback (iOS):
//   The `audio` background mode in Info.plist (set in SETUP.md §4) is
//   what keeps TTS working when the user locks the phone during a run.
//   Without that, TTS silently stops when the app backgrounds.
//
// Dependencies on jovi_run_engine.dart:
//   RunTrackingService (listener target)
//   ActivitySession (read splits + type)
//   ActivityType (for announcement text — "one mile" vs "five miles")
//   ActivitySplit (for pace in announcements)
// =======================================================================

class RunAudioCueService {
  final FlutterTts _tts = FlutterTts();
  bool _enabled = true;
  bool _initialized = false;
  double _volume = 0.8;
  int _lastAnnouncedSplitIndex = -1;
  String? _lastAnnouncedSessionId;

  /// Set before a run to enable or disable voice cues. The controller
  /// reads from RunSettings and updates this.
  set enabled(bool value) {
    _enabled = value;
    if (!value) {
      // Mid-run toggle off — stop any in-progress utterance.
      unawaited(_tts.stop());
    }
  }

  bool get enabled => _enabled;

  /// Sets the TTS playback volume (0.0 to 1.0). Applied immediately if
  /// TTS is already initialized; otherwise stored and applied at init.
  Future<void> setVolume(double v) async {
    _volume = v.clamp(0.0, 1.0);
    if (_initialized) {
      try {
        await _tts.setVolume(_volume);
      } catch (e) {
        _logError('setVolume failed', e);
      }
    }
  }

  /// One-time setup. Configures the audio session + TTS voice/rate.
  /// Safe to call multiple times — subsequent calls no-op.
  Future<void> init() async {
    if (_initialized) return;
    try {
      // Configure iOS audio session to duck music during speech.
      final session = await AudioSession.instance;
      await session.configure(const AudioSessionConfiguration(
        avAudioSessionCategory: AVAudioSessionCategory.playback,
        avAudioSessionCategoryOptions: AVAudioSessionCategoryOptions.duckOthers,
        avAudioSessionMode: AVAudioSessionMode.spokenAudio,
        avAudioSessionRouteSharingPolicy:
            AVAudioSessionRouteSharingPolicy.defaultPolicy,
        avAudioSessionSetActiveOptions: AVAudioSessionSetActiveOptions.none,
        androidAudioAttributes: AndroidAudioAttributes(
          contentType: AndroidAudioContentType.speech,
          flags: AndroidAudioFlags.none,
          usage: AndroidAudioUsage.assistanceNavigationGuidance,
        ),
        androidAudioFocusGainType:
            AndroidAudioFocusGainType.gainTransientMayDuck,
        androidWillPauseWhenDucked: false,
      ));

      await _tts.setLanguage('en-US');
      await _tts.setSpeechRate(0.5); // slightly slower than default,
      // easier to catch while running and out of breath
      await _tts.setVolume(_volume);
      await _tts.setPitch(1.0);

      // Some platforms need this to route through the audio session.
      // Harmless no-op on others.
      try {
        await _tts.awaitSpeakCompletion(true);
      } catch (_) {}

      _initialized = true;
      _log('RunAudioCueService initialized');
    } catch (e, st) {
      _logError('RunAudioCueService.init failed', e, st);
      // Non-fatal — voice cues will just be silent. Better than
      // crashing the tracking experience.
    }
  }

  /// Called by the controller on every tracking-service notification.
  /// Emits a cue iff a new split has appeared since our last check.
  void onTrackingUpdate(ActivitySession? session) {
    if (!_enabled || session == null) return;

    // Session identity change — reset state so a new run starts
    // counting splits from index 0 again.
    if (session.id != _lastAnnouncedSessionId) {
      _lastAnnouncedSessionId = session.id;
      _lastAnnouncedSplitIndex = -1;
    }

    // Only announce splits that are genuinely new.
    if (session.splits.length - 1 > _lastAnnouncedSplitIndex) {
      final newestIndex = session.splits.length - 1;
      final split = session.splits[newestIndex];
      _lastAnnouncedSplitIndex = newestIndex;
      _announceSplit(split, session);
    }
  }

  /// Say "One mile, eight forty-two pace" for a run/walk, or
  /// "Five miles, fourteen point two miles per hour" for cycling.
  Future<void> _announceSplit(
      ActivitySplit split, ActivitySession session) async {
    if (!_initialized) await init();
    if (!_enabled) return;

    final milestoneNumber = split.index + 1; // index 0 = "mile 1"
    final milestoneLabel = session.type == ActivityType.ride
        ? _rideMilestoneLabel(milestoneNumber)
        : _runWalkMilestoneLabel(milestoneNumber);

    String paceOrSpeedPhrase;
    if (session.type == ActivityType.ride) {
      final mph = mpsToMph(split.avgSpeedMps);
      paceOrSpeedPhrase = '${mph.toStringAsFixed(1)} miles per hour average';
    } else {
      // Pace as "eight forty-two" — English speakers announce pace
      // this way, not "8:42". flutter_tts can SAY "8:42" fine but
      // the natural version is clearer at speed.
      final paceSec =
          split.avgSpeedMps > 0 ? (1609.344 / split.avgSpeedMps).round() : 0;
      final paceMin = paceSec ~/ 60;
      final paceRemSec = paceSec % 60;
      paceOrSpeedPhrase =
          '$paceMin ${paceRemSec == 0 ? "flat" : paceRemSec} pace';
    }

    final phrase = '$milestoneLabel. $paceOrSpeedPhrase.';

    _analytics('voice_cue_fired', {
      'sessionId': session.id,
      'splitIndex': split.index,
      'text': phrase,
    });

    try {
      // stop() first in case a previous cue is still playing. Avoids
      // pile-ups on slow devices.
      await _tts.stop();
      await _tts.speak(phrase);
    } catch (e, st) {
      _logError('TTS speak failed', e, st);
    }
  }

  /// "One mile", "Two miles", "Ten miles", etc. for run/walk.
  String _runWalkMilestoneLabel(int n) {
    const ones = [
      'zero',
      'one',
      'two',
      'three',
      'four',
      'five',
      'six',
      'seven',
      'eight',
      'nine',
      'ten',
    ];
    if (n <= 10) {
      return n == 1 ? '${ones[n]} mile' : '${ones[n]} miles';
    }
    return n == 1 ? '$n mile' : '$n miles';
  }

  /// "Five miles", "Ten miles", "Fifteen miles", etc. for cycling
  /// (5-mile splits, so milestone 1 = 5mi, 2 = 10mi, 3 = 15mi, etc.)
  String _rideMilestoneLabel(int milestoneIndex) {
    final totalMiles = milestoneIndex * 5;
    return '$totalMiles miles';
  }

  /// Announce a one-off message. Used for "GPS acquired — starting"
  /// and other key state transitions.
  Future<void> announce(String phrase) async {
    if (!_initialized) await init();
    if (!_enabled) return;
    try {
      await _tts.stop();
      await _tts.speak(phrase);
    } catch (e, st) {
      _logError('TTS announce failed', e, st);
    }
  }

  /// Reset per-session state. Called by the controller on start().
  void resetForNewSession() {
    _lastAnnouncedSessionId = null;
    _lastAnnouncedSplitIndex = -1;
  }

  /// Shut down. Call from RunController.dispose().
  Future<void> dispose() async {
    try {
      await _tts.stop();
    } catch (_) {}
  }
}

// =======================================================================
// RUN CONTROLLER
//
// The singleton coordinator that ties everything together. UI widgets
// subscribe to this one instance. Owns:
//
//   - ONE RunTrackingService
//   - ONE RunPersistenceService
//   - ONE RunAudioCueService
//   - RunSettings (hydrated on first access, persisted on change)
//   - Wakelock state management
//   - GPS acquisition state (separate from the engine's session state)
//
// USAGE:
//   final ctl = RunController.instance;
//   await ctl.init();                       // once, on app launch
//   await ctl.startActivity(ActivityType.run); // begin GPS acquisition
//   // ctl is a ChangeNotifier — UI widgets subscribe for updates
//   ctl.pause();
//   ctl.resume();
//   final session = await ctl.stop();       // returns final session
//   ctl.clearCompleted();                   // after summary screen
//
// GPS ACQUISITION STATE MACHINE:
//   The problem: GPS accuracy is garbage for the first 15-30 seconds
//   after the stream opens. If we just start recording right away,
//   the first mile reads 42 feet because the runner covered half a
//   block while GPS was still locking on.
//
//   The fix: "Acquiring GPS" splash. When the user taps Start, we
//   open the GPS stream but don't create the session until we've seen
//   a fix with accuracy < 30m. At that point we create the session
//   and begin recording.
//
//   The UI reads `acquisitionState` to decide what to show:
//     - idle:       no activity picked, idle dashboard
//     - acquiring:  GPS stream open, waiting for good fix
//     - recording:  session exists, forwarding to RunTrackingService
//     - completed:  session finished, summary screen should show
//
//   Transitions:
//     idle ─startActivity()─▶ acquiring ─fix<30m─▶ recording
//                 │                │                   │
//                 │             abort()               stop()
//                 │                │                   │
//                 ◀────────────────┴───────────────▶ completed
//                                                      │
//                                              clearCompleted()
//                                                      │
//                                                      ▼
//                                                    idle
// =======================================================================

enum RunAcquisitionState { idle, acquiring, recording, completed }

class RunController extends ChangeNotifier {
  RunController._();

  // Lazy singleton. Initialized on first access.
  static RunController? _instance;
  static RunController get instance {
    _instance ??= RunController._();
    return _instance!;
  }

  /// Test-only reset hook. Production code should never call this —
  /// disposing the singleton mid-run would lose the in-progress
  /// session. Exists so test code can start from a clean slate.
  @visibleForTesting
  static void disposeInstance() {
    _instance?._disposeInternal();
    _instance = null;
  }

  // Owned services.
  final RunTrackingService _tracking = RunTrackingService();
  late final RunPersistenceService _persistence =
      RunPersistenceService(tracking: _tracking);
  final RunAudioCueService _audio = RunAudioCueService();

  RunSettings _settings = const RunSettings();
  RunAcquisitionState _acquisitionState = RunAcquisitionState.idle;
  ActivityType? _pendingActivity;
  StreamSubscription<Position>? _acquisitionSub;
  DateTime? _acquisitionStartedAt;
  double? _lastSeenAccuracyMeters;
  bool _initialized = false;

  // --- Public read-only state for UI ---

  RunSettings get settings => _settings;
  RunAcquisitionState get acquisitionState => _acquisitionState;
  ActivityType? get pendingActivity => _pendingActivity;
  ActivitySession? get session => _tracking.session;
  ActivityStats? get stats => _tracking.stats;
  bool get isRecording => _tracking.isActive && !_tracking.isPaused;
  bool get isPaused => _tracking.isPaused;
  bool get isAutoPaused => _tracking.isAutoPaused;
  double? get lastSeenAccuracyMeters => _lastSeenAccuracyMeters;
  Duration get acquisitionElapsed {
    final started = _acquisitionStartedAt;
    if (started == null) return Duration.zero;
    return DateTime.now().difference(started);
  }

  /// Direct access to the underlying tracking service for widgets that
  /// want to listen to it directly rather than through this controller.
  /// Most UI should just subscribe to RunController and be done with it.
  RunTrackingService get tracking => _tracking;

  // --- Initialization ---

  /// One-time setup. Call on app launch, before any UI shows. Loads
  /// settings and warms up the TTS engine so the first voice cue
  /// doesn't have a 1-2 second spool-up delay.
  Future<void> init() async {
    if (_initialized) return;
    _initialized = true;
    try {
      _settings = await RunSettings.load();
      _audio.enabled = _settings.voiceCuesEnabled;
      await _audio.setVolume(_settings.voiceVolume);
      _tracking.setGpsAccuracy(_settings.gpsAccuracy);
      await _audio.init();
      // Subscribe our audio service to tracking notifications so it
      // can fire cues when new splits appear.
      _tracking.addListener(_onTrackingChanged);
      _log('RunController initialized');
    } catch (e, st) {
      _logError('RunController.init failed', e, st);
    }
  }

  void _disposeInternal() {
    _acquisitionSub?.cancel();
    _tracking.removeListener(_onTrackingChanged);
    _persistence.dispose();
    _audio.dispose();
    _tracking.dispose();
    super.dispose();
  }

  // --- Settings ---

  /// Update settings and persist. Notifies listeners so the UI
  /// re-renders with the new choices immediately.
  Future<void> updateSettings(RunSettings next) async {
    _settings = next;
    _audio.enabled = next.voiceCuesEnabled;
    await _audio.setVolume(next.voiceVolume);
    _tracking.setGpsAccuracy(next.gpsAccuracy);
    notifyListeners();
    await next.save();
  }

  // --- Activity lifecycle ---

  /// Begin GPS acquisition for a new activity. The actual recording
  /// starts only after we've seen a fix with reasonable accuracy
  /// (see acquisitionState transitions).
  ///
  /// Throws:
  ///   - LocationPermissionDeniedException if the user denies or has
  ///     previously denied location permission
  ///   - LocationServiceDisabledException if OS location is off
  Future<void> startActivity(ActivityType type) async {
    if (_acquisitionState != RunAcquisitionState.idle) {
      throw StateError(
          'Cannot start: controller is not idle (state=$_acquisitionState).');
    }

    // Request permissions + verify location service is on. We do this
    // here rather than letting RunTrackingService throw later because
    // we want to surface the permission prompt BEFORE showing the
    // "Acquiring GPS" splash.
    final perm = await Geolocator.checkPermission();
    if (perm == LocationPermission.denied) {
      final asked = await Geolocator.requestPermission();
      if (asked == LocationPermission.denied ||
          asked == LocationPermission.deniedForever) {
        throw const LocationPermissionDeniedException();
      }
    } else if (perm == LocationPermission.deniedForever) {
      throw const LocationPermissionDeniedException();
    }

    final serviceOn = await Geolocator.isLocationServiceEnabled();
    if (!serviceOn) {
      throw const LocationServiceDisabledException();
    }

    _pendingActivity = type;
    _acquisitionState = RunAcquisitionState.acquiring;
    _acquisitionStartedAt = DateTime.now();
    _lastSeenAccuracyMeters = null;

    if (_settings.keepScreenOn) {
      try {
        await WakelockPlus.enable();
      } catch (e) {
        _logError('wakelock enable failed', e);
      }
    }

    _audio.resetForNewSession();

    _analytics('acquisition_started', {
      'type': activityTypeSerialize(type),
    });

    // Open a brief GPS stream to pick up first fix. We use a separate
    // subscription here (not the tracking service) because we don't
    // yet have a session to feed points into.
    const acquireSettings = LocationSettings(
      accuracy: LocationAccuracy.best,
      distanceFilter: 0,
    );
    _acquisitionSub?.cancel();
    _acquisitionSub =
        Geolocator.getPositionStream(locationSettings: acquireSettings).listen(
      _onAcquiringFix,
      onError: (err, st) {
        _logError('acquisition stream error', err, st);
      },
      cancelOnError: false,
    );

    notifyListeners();
  }

  /// Abort GPS acquisition before a session has been created. Doesn't
  /// end an in-progress run — for that, use stop() or discard().
  Future<void> abortAcquisition() async {
    if (_acquisitionState != RunAcquisitionState.acquiring) return;
    await _acquisitionSub?.cancel();
    _acquisitionSub = null;
    _acquisitionState = RunAcquisitionState.idle;
    _pendingActivity = null;
    _acquisitionStartedAt = null;
    _lastSeenAccuracyMeters = null;
    try {
      await WakelockPlus.disable();
    } catch (_) {}
    _analytics('acquisition_aborted');
    notifyListeners();
  }

  void _onAcquiringFix(Position p) {
    _lastSeenAccuracyMeters = p.accuracy >= 0 ? p.accuracy : null;
    notifyListeners(); // update the "Acquiring..." splash accuracy readout

    // Wait for a fix with accuracy <= 30m. We also give up and
    // accept a worse fix after 45 seconds of waiting (better to start
    // with some error than make the user wait forever in a canyon).
    final acc = p.accuracy;
    final elapsed = acquisitionElapsed;
    final goodEnough = acc >= 0 && acc <= 30.0;
    final timedOut = elapsed.inSeconds >= 45;
    if (!goodEnough && !timedOut) return;

    final type = _pendingActivity;
    if (type == null) return;

    // Transition to recording. Close our acquisition stream; the
    // tracking service opens its own fresh one.
    _acquisitionSub?.cancel();
    _acquisitionSub = null;

    _analytics('acquisition_completed', {
      'accuracy': acc.round(),
      'elapsedSeconds': elapsed.inSeconds,
      'timedOut': timedOut,
    });

    _tracking.start(type).then((_) {
      _acquisitionState = RunAcquisitionState.recording;
      notifyListeners();
      _audio.announce('Starting ${activityTypeLabel(type).toLowerCase()}.');
    }).catchError((e, st) {
      _logError('tracking.start after acquisition failed', e, st);
      // Reset to idle so user can try again.
      _acquisitionState = RunAcquisitionState.idle;
      _pendingActivity = null;
      notifyListeners();
    });
  }

  /// Manual pause. Safe to call when not recording.
  void pause() {
    _tracking.pause();
    _audio.announce('Paused.');
  }

  /// Resume from pause.
  void resume() {
    _tracking.resume();
    _audio.announce('Resuming.');
  }

  /// Stop and finalize. Returns the completed session, same as the
  /// tracking service's stop(). After this, `acquisitionState` is
  /// `completed` and the UI should navigate to the summary screen.
  Future<ActivitySession> stop() async {
    try {
      final s = await _tracking.stop();
      _acquisitionState = RunAcquisitionState.completed;
      try {
        await WakelockPlus.disable();
      } catch (_) {}
      await _audio.announce('Workout complete.');
      notifyListeners();
      return s;
    } catch (e, st) {
      _logError('stop failed', e, st);
      rethrow;
    }
  }

  /// Discard an in-progress session without saving.
  Future<ActivitySession> discard() async {
    try {
      final s = await _tracking.discard();
      _acquisitionState = RunAcquisitionState.idle;
      _pendingActivity = null;
      try {
        await WakelockPlus.disable();
      } catch (_) {}
      notifyListeners();
      return s;
    } catch (e, st) {
      _logError('discard failed', e, st);
      rethrow;
    }
  }

  /// Call after the summary screen has closed. Clears the terminal
  /// session so a new activity can be started.
  void clearCompleted() {
    _tracking.clearCompletedSession();
    _acquisitionState = RunAcquisitionState.idle;
    _pendingActivity = null;
    _acquisitionStartedAt = null;
    _lastSeenAccuracyMeters = null;
    notifyListeners();
  }

  // --- Tracking event forwarding ---

  void _onTrackingChanged() {
    // Forward cue-relevant updates to the audio service.
    _audio.onTrackingUpdate(_tracking.session);
    // And fanout to our own listeners so UI re-renders.
    notifyListeners();
  }
}

// =======================================================================
// UI SCREENS (originally from jovi_run_active.dart)
// =======================================================================

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

class RunPermissionPrimer extends StatefulWidget {
  const RunPermissionPrimer({
    Key? key,
    this.width,
    this.height,
  }) : super(key: key);

  final double? width;
  final double? height;

  @override
  State<RunPermissionPrimer> createState() => _RunPermissionPrimerState();
}

class _RunPermissionPrimerState extends State<RunPermissionPrimer> {
  bool _checking = true;
  bool _requesting = false;

  @override
  void initState() {
    super.initState();
    _checkAndMaybeSkip();
  }

  Future<void> _checkAndMaybeSkip() async {
    try {
      final perm = await Geolocator.checkPermission();
      if (perm == LocationPermission.always ||
          perm == LocationPermission.whileInUse) {
        if (mounted) Navigator.of(context).pop(true);
        return;
      }
    } catch (_) {
      // Fall through — show the primer.
    }
    if (mounted) setState(() => _checking = false);
  }

  Future<void> _onContinue() async {
    setState(() => _requesting = true);
    try {
      // permission_handler is friendlier than Geolocator here because
      // it lets us re-open Settings if permission was permanently
      // denied in a past session.
      final status = await Permission.locationWhenInUse.request();
      _log('primer request result: $status');
      if (!mounted) return;
      if (status.isPermanentlyDenied) {
        _showSettingsDialog();
        return;
      }
      Navigator.of(context).pop(status.isGranted);
    } catch (e) {
      _log('primer request error: $e');
      if (mounted) Navigator.of(context).pop(false);
    }
  }

  void _showSettingsDialog() {
showCupertinoDialog<void>(
      context: context,
      builder: (ctx) => CupertinoAlertDialog(
        title: const Text('Enable Location'),
        content: const Padding(
          padding: EdgeInsets.only(top: 8),
          child: Text('Location permission was previously denied. Open Settings to enable it?'),
        ),
        actions: [
          CupertinoDialogAction(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Cancel'),
          ),
          CupertinoDialogAction(
            isDefaultAction: true,
            onPressed: () async {
              Navigator.of(ctx).pop();
              await openAppSettings();
              if (mounted) Navigator.of(context).pop(false);
            },
            child: const Text('Open Settings'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_checking) {
      return const Scaffold(
        backgroundColor: _joviNavy,
        body: Center(
          child: CircularProgressIndicator(
            valueColor: AlwaysStoppedAnimation<Color>(_joviCoral),
          ),
        ),
      );
    }

    return Scaffold(
      backgroundColor: _joviNavyDark,
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [_joviNavy, _joviNavyDark],
          ),
        ),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              children: [
                const Spacer(),
                // Hero icon
                Container(
                  width: 84,
                  height: 84,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: LinearGradient(
                      colors: [
                        _joviCoral.withOpacity(0.3),
                        _joviCoralLight.withOpacity(0.15),
                      ],
                    ),
                    border: Border.all(
                      color: _joviCoral.withOpacity(0.5),
                      width: 1.5,
                    ),
                  ),
                  child: const Icon(
                    Icons.my_location_rounded,
                    color: Colors.white,
                    size: 40,
                  ),
                ),
                const SizedBox(height: 24),
                const Text(
                  'Jovi needs your location',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 24,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.5,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 12),
                Text(
                  'We use your location to track distance, pace, '
                  'and elevation while you run, walk, or ride.\n\n'
                  'Your route stays private — we never share it.',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.75),
                    fontSize: 15,
                    height: 1.5,
                    fontWeight: FontWeight.w500,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 28),
                // Bullet highlights
                _primerBullet(Icons.timer_outlined,
                    'Accurate pace and distance tracking'),
                const SizedBox(height: 12),
                _primerBullet(Icons.terrain_rounded,
                    'Elevation and splits for every activity'),
                const SizedBox(height: 12),
                _primerBullet(Icons.lock_outline_rounded,
                    'Data is stored privately in your account'),
                const Spacer(),
                // Continue
                SizedBox(
                  width: double.infinity,
                  height: 56,
                  child: ElevatedButton(
                    onPressed: _requesting ? null : _onContinue,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: _joviCoral,
                      foregroundColor: Colors.white,
                      disabledBackgroundColor: _joviCoral.withOpacity(0.5),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(14),
                      ),
                      elevation: 6,
                      shadowColor: _joviCoral.withOpacity(0.5),
                    ),
                    child: _requesting
                        ? const SizedBox(
                            width: 22,
                            height: 22,
                            child: CircularProgressIndicator(
                              color: Colors.white,
                              strokeWidth: 2.2,
                            ),
                          )
                        : const Text(
                            'Continue',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 0.2,
                            ),
                          ),
                  ),
                ),
                const SizedBox(height: 10),
                TextButton(
                  onPressed: _requesting
                      ? null
                      : () => Navigator.of(context).pop(false),
                  style: TextButton.styleFrom(
                    foregroundColor: Colors.white.withOpacity(0.6),
                  ),
                  child: const Text(
                    'Not now',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                const SizedBox(height: 8),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _primerBullet(IconData icon, String text) {
    return Row(
      children: [
        Container(
          width: 34,
          height: 34,
          decoration: BoxDecoration(
            color: _joviCoral.withOpacity(0.18),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: _joviCoral.withOpacity(0.35),
              width: 0.8,
            ),
          ),
          child: Icon(icon, color: _joviCoral, size: 18),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Text(
            text,
            style: TextStyle(
              color: Colors.white.withOpacity(0.85),
              fontSize: 14,
              fontWeight: FontWeight.w600,
              height: 1.4,
            ),
          ),
        ),
      ],
    );
  }
}

// =======================================================================
// RUN ACTIVITY PICKER
//
// Entry screen of the running feature. User picks Run / Walk / Ride,
// taps Start. Handles permission flow + transitions into the active
// run screen.
//
// Pattern:
//   - Three big cards, vertically stacked, each with icon + label +
//     brief description ("Track distance, pace, elevation")
//   - Selection highlighted with coral border + glow
//   - Bottom Start button, disabled until a type is chosen
//   - Settings gear in top-right → opens run settings (Session 4)
//
// Flow on tap Start:
//   1. Check Geolocator.checkPermission()
//   2. If denied → push RunPermissionPrimer, wait for result
//   3. If granted (initially or via primer) → call
//      RunController.instance.startActivity(type), then push
//      RunActiveScreen
//   4. If denied after primer → show dialog, user can retry or cancel
// =======================================================================

// =======================================================================
// RUN FITNESS HOME
//
// Tabbed entry-point widget. Place this on your fitnessHome page
// instead of RunActivityPicker. Two tabs: Start (picker) and History
// (list of past runs). This is what JC drops onto the page.
//
// Tabs use animated underline + coral active color. Minimal
// chrome — the picker and history each manage their own content
// below.
//
// Cross-tab navigation:
//   - History empty-state tapping "Start an activity" flips back to
//     the Start tab via the onStartTapped callback we pass in.
// =======================================================================

class JoviRunFitnessHome extends StatefulWidget {
  const JoviRunFitnessHome({
    Key? key,
    this.width,
    this.height,
  }) : super(key: key);

  final double? width;
  final double? height;

  @override
  State<JoviRunFitnessHome> createState() => _JoviRunFitnessHomeState();
}

class _JoviRunFitnessHomeState extends State<JoviRunFitnessHome> {
  int _tabIndex = 0; // 0 = Start, 1 = History

  @override
  void initState() {
    super.initState();
    // Wire up JoviRunHistoryList's static start-tapped callback so its
    // empty-state Start button flips us back to the Start tab instead
    // of popping the route. We use a static slot instead of a widget
    // parameter because FlutterFlow's parameter inference rejects
    // function-typed params. Cleared in dispose to avoid leaking a
    // reference to this State after unmount.
    JoviRunHistoryList.onStartRequested = () {
      if (!mounted) return;
      setState(() => _tabIndex = 0);
    };
  }

  @override
  void dispose() {
    // Only clear if this instance is still the registered callback —
    // protects against a stale clear if the static slot has been
    // re-assigned by another instance (shouldn't happen in practice
    // but cheap to guard).
    JoviRunHistoryList.onStartRequested = null;
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _joviNavyDark,
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [_joviNavy, _joviNavyDark, _joviNavyDark],
            stops: [0.0, 0.5, 1.0],
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              _buildTabs(),
              Expanded(
                child: IndexedStack(
                  index: _tabIndex,
                  children: [
                    // Tab 0: picker. We disable its SafeArea + gradient
                    // (we're providing them) by keeping the picker
                    // inside our own scaffold. The picker's own
                    // Scaffold will just repeat the background —
                    // harmless but slightly redundant. Could be
                    // optimized by extracting picker content into a
                    // pure body widget later.
                    const RunActivityPicker(),
                    // Tab 1: history. The empty-state Start button's
                    // callback is wired up via JoviRunHistoryList's
                    // static callback slot in our initState above.
                    const JoviRunHistoryList(),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTabs() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
      child: Row(
        children: [
          _tabButton(0, 'Start'),
          _tabButton(1, 'History'),
          const Spacer(),
        ],
      ),
    );
  }

  Widget _tabButton(int index, String label) {
    final active = _tabIndex == index;
    return Padding(
      padding: const EdgeInsets.only(right: 6),
      child: _PressableMaterial(
        child: InkWell(
          onTap: () {
            HapticFeedback.selectionClick();
            setState(() => _tabIndex = index);
          },
          borderRadius: BorderRadius.circular(12),
          child: AnimatedContainer(
            duration: _Motion.select,
            curve: _Motion.settle,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            decoration: BoxDecoration(
              gradient: active
                  ? const LinearGradient(
                      colors: [_joviCoral, _joviCoralLight],
                    )
                  : null,
              color: active ? null : Colors.white.withOpacity(0.04),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: active
                    ? _joviCoral.withOpacity(0.6)
                    : Colors.white.withOpacity(0.1),
              ),
              boxShadow: active
                  ? [
                      BoxShadow(
                        color: _joviCoral.withOpacity(0.3),
                        blurRadius: 10,
                        offset: const Offset(0, 3),
                      ),
                    ]
                  : null,
            ),
            child: Text(
              label,
              style: TextStyle(
                color: active ? Colors.white : Colors.white.withOpacity(0.65),
                fontSize: 14,
                fontWeight: FontWeight.w800,
                letterSpacing: 0.3,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// =======================================================================
// WEATHER SERVICE
//
// Matches the home dashboard's weather pattern exactly: OpenWeatherMap
// /data/2.5/weather endpoint, imperial units, same API key.
//
// Differences vs. home dashboard:
//   - Only fetches the base /weather endpoint (no UV/air/forecast) because
//     the fitness card only needs current temp + conditions. Less quota
//     burn, faster load.
//   - Adds a "runnability" heuristic that shades the card based on
//     conditions: green for 40-75°F + clear, amber for edge conditions,
//     red for extreme heat/cold/storms.
//   - Simulated fallback on location-denied or API failure.
//
// The API key is the same one the home dashboard uses — keep them in
// sync if you ever rotate it. Free tier = 1000 calls/day.
// =======================================================================

const String _runWeatherApiKey = '39eee692f6e29d0092f80bac534c5db7';

enum RunWeatherQuality { great, ok, bad, unknown }

class RunWeatherData {
  final double tempF;
  final double feelsLikeF;
  final int humidityPct;
  final double windMph;
  final String cityName;
  final String description;
  final String icon; // emoji
  final RunWeatherQuality quality;
  final String qualityNote;

  const RunWeatherData({
    required this.tempF,
    required this.feelsLikeF,
    required this.humidityPct,
    required this.windMph,
    required this.cityName,
    required this.description,
    required this.icon,
    required this.quality,
    required this.qualityNote,
  });
}

class RunWeatherService {
  RunWeatherData? _cached;
  DateTime? _cachedAt;

  // Cache for 15 minutes — roughly how often OpenWeatherMap recommends
  // polling for accurate current conditions.
  static const _cacheDuration = Duration(minutes: 15);

  /// Fetch current weather. Returns cached data if fresh, otherwise
  /// attempts a live fetch. Falls back to simulated values on permission
  /// denied or API failure so the card never stays in a loading state.
  /// Returns null when location has not been granted yet or the fetch
  /// fails. The card simply hides in that case: the permission prompt
  /// belongs to the moment the member taps Start, not to a weather tile,
  /// and made-up conditions must never be presented as real.
  Future<RunWeatherData?> get() async {
    final now = DateTime.now();
    if (_cached != null &&
        _cachedAt != null &&
        now.difference(_cachedAt!) < _cacheDuration) {
      return _cached!;
    }

    try {
      final perm = await Geolocator.checkPermission();
      if (perm != LocationPermission.always &&
          perm != LocationPermission.whileInUse) {
        return null;
      }
      final pos = await Geolocator.getCurrentPosition(
        // ignore: deprecated_member_use
        desiredAccuracy: LocationAccuracy.medium,
      );
      final live = await _fetchLive(pos.latitude, pos.longitude);
      if (live != null) {
        _cached = live;
        _cachedAt = now;
        return live;
      }
    } catch (e, st) {
      _logError('weather fetch failed', e, st);
    }
    return null;
  }

  Future<RunWeatherData?> _fetchLive(double lat, double lon) async {
    try {
      final url =
          'https://api.openweathermap.org/data/2.5/weather?lat=$lat&lon=$lon&appid=$_runWeatherApiKey&units=imperial';
      final resp = await network_http.get(Uri.parse(url));
      if (resp.statusCode != 200) return null;
      final j = jsonDecode(resp.body) as Map<String, dynamic>;
      final main = j['main'] as Map<String, dynamic>? ?? {};
      final weatherList = j['weather'] as List<dynamic>? ?? [];
      final weatherJson = weatherList.isNotEmpty
          ? weatherList[0] as Map<String, dynamic>
          : <String, dynamic>{};
      final wind = j['wind'] as Map<String, dynamic>? ?? {};

      final temp = (main['temp'] as num?)?.toDouble() ?? 70;
      final feels = (main['feels_like'] as num?)?.toDouble() ?? temp;
      final humidity = (main['humidity'] as num?)?.toInt() ?? 50;
      final windSpeed = (wind['speed'] as num?)?.toDouble() ?? 0;
      final cityName = j['name'] as String? ?? 'Your Location';
      final weatherId = (weatherJson['id'] as num?)?.toInt() ?? 800;
      final description = weatherJson['main'] as String? ?? 'Clear';

      final quality = _scoreQuality(temp, weatherId, windSpeed, humidity);

      return RunWeatherData(
        tempF: temp,
        feelsLikeF: feels,
        humidityPct: humidity,
        windMph: windSpeed,
        cityName: cityName,
        description: description,
        icon: _weatherIdToEmoji(weatherId),
        quality: quality,
        qualityNote: _qualityNoteFor(quality, temp, weatherId, windSpeed),
      );
    } catch (e, st) {
      _logError('weather API parse failed', e, st);
      return null;
    }
  }

  // ignore: unused_element
  RunWeatherData _simulated() {
    final now = DateTime.now();
    final month = now.month;
    final hour = now.hour;
    int base = 68;
    if (month >= 12 || month <= 2) base = 45;
    if (month >= 6 && month <= 8) base = 82;
    if (hour >= 5 && hour <= 8) base -= 6;
    if (hour >= 14 && hour <= 17) base += 4;
    if (hour < 5 || hour > 20) base -= 10;
    final q = _scoreQuality(base.toDouble(), 800, 5, 55);
    return RunWeatherData(
      tempF: base.toDouble(),
      feelsLikeF: base.toDouble(),
      humidityPct: 55,
      windMph: 5,
      cityName: 'Your Location',
      description: 'Clear',
      icon: '🌤️',
      quality: q,
      qualityNote: _qualityNoteFor(q, base.toDouble(), 800, 5),
    );
  }

  RunWeatherQuality _scoreQuality(
      double tempF, int weatherId, double windMph, int humidity) {
    // Thunderstorm/snow/freezing drizzle — bad
    if (weatherId >= 200 && weatherId < 300) return RunWeatherQuality.bad;
    if (weatherId >= 600 && weatherId < 700) return RunWeatherQuality.bad;
    // Extreme heat / cold
    if (tempF >= 95 || tempF <= 20) return RunWeatherQuality.bad;
    // Heavy rain / high wind
    if (weatherId == 502 || weatherId == 503 || weatherId == 504) {
      return RunWeatherQuality.bad;
    }
    if (windMph >= 25) return RunWeatherQuality.bad;

    // Light rain / drizzle / hot-ish / cold-ish — ok
    if (weatherId >= 300 && weatherId < 600) return RunWeatherQuality.ok;
    if (tempF >= 85 || tempF <= 35) return RunWeatherQuality.ok;
    if (windMph >= 15) return RunWeatherQuality.ok;
    if (humidity >= 80) return RunWeatherQuality.ok;

    // Sweet spot: 40-82°F, dry, light wind
    return RunWeatherQuality.great;
  }

  String _qualityNoteFor(
      RunWeatherQuality q, double tempF, int weatherId, double windMph) {
    switch (q) {
      case RunWeatherQuality.great:
        return 'Great conditions for a run';
      case RunWeatherQuality.ok:
        if (tempF >= 85) return 'Warm — hydrate and pace yourself';
        if (tempF <= 35) return 'Cold — layer up before heading out';
        if (windMph >= 15) return 'Windy — plan your route accordingly';
        if (weatherId >= 300 && weatherId < 600)
          return 'Wet out — watch footing';
        return 'Decent — go if you\'re up for it';
      case RunWeatherQuality.bad:
        if (weatherId >= 200 && weatherId < 300)
          return 'Thunderstorms — stay indoors';
        if (weatherId >= 600 && weatherId < 700) return 'Snow — use caution';
        if (tempF >= 95) return 'Extreme heat — consider indoors';
        if (tempF <= 20) return 'Extreme cold — consider indoors';
        if (windMph >= 25) return 'High wind — not ideal';
        return 'Rough conditions — maybe skip today';
      case RunWeatherQuality.unknown:
        return 'Conditions unavailable';
    }
  }

  String _weatherIdToEmoji(int id) {
    if (id >= 200 && id < 300) return '⛈️';
    if (id >= 300 && id < 400) return '🌦️';
    if (id >= 500 && id < 600) return '🌧️';
    if (id >= 600 && id < 700) return '🌨️';
    if (id >= 700 && id < 800) return '🌫️';
    if (id == 800) return '☀️';
    if (id == 801) return '🌤️';
    if (id == 802) return '⛅';
    if (id == 803 || id == 804) return '☁️';
    return '🌤️';
  }
}

// =======================================================================
// GOALS & RECENT ACTIVITY SERVICE
//
// Reads from users/{uid}/activities to compute:
//   - Today's distance (all completed activities started today)
//   - This week's distance (Monday 00:00 — Sunday 23:59)
//   - Most recent completed activity (for "last run" card)
//
// Cached in-memory for the duration of one picker visit so tab-flipping
// doesn't re-query Firestore. Explicitly refreshed on pull-to-refresh.
// =======================================================================

class RunGoalProgress {
  final double todayMiles;
  final double weekMiles;
  final int todayActivityCount;
  final int weekActivityCount;
  final Map<String, dynamic>? lastActivity; // Raw doc data + id for card
  final String? lastActivityId;

  const RunGoalProgress({
    required this.todayMiles,
    required this.weekMiles,
    required this.todayActivityCount,
    required this.weekActivityCount,
    this.lastActivity,
    this.lastActivityId,
  });

  static const empty = RunGoalProgress(
    todayMiles: 0,
    weekMiles: 0,
    todayActivityCount: 0,
    weekActivityCount: 0,
  );
}

class RunGoalsService {
  RunGoalProgress? _cached;
  DateTime? _cachedAt;
  static const _cacheDuration = Duration(minutes: 2);

  Future<RunGoalProgress> load({bool force = false}) async {
    final now = DateTime.now();
    if (!force &&
        _cached != null &&
        _cachedAt != null &&
        now.difference(_cachedAt!) < _cacheDuration) {
      return _cached!;
    }
    final result = await _fetch();
    _cached = result;
    _cachedAt = now;
    return result;
  }

  Future<RunGoalProgress> _fetch() async {
    final uid = FirebaseAuth.instance.currentUser?.uid;
    if (uid == null) return RunGoalProgress.empty;

    try {
      final now = DateTime.now();
      final today0 = DateTime(now.year, now.month, now.day);
      // Week starts Monday. weekday: Mon=1..Sun=7
      final daysSinceMon = now.weekday - 1;
      final weekStart = DateTime(now.year, now.month, now.day - daysSinceMon);

      final snap = await FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('activities')
          .where('status', isEqualTo: 'completed')
          .orderBy('startedAt', descending: true)
          .limit(50) // enough to cover a typical week
          .get();

      double todayMi = 0;
      double weekMi = 0;
      int todayCount = 0;
      int weekCount = 0;
      Map<String, dynamic>? lastActivity;
      String? lastActivityId;

      for (final doc in snap.docs) {
        final d = doc.data();
        final ts = d['startedAt'];
        if (ts is! Timestamp) continue;
        final started = ts.toDate();
        final distMeters = (d['distanceMeters'] as num?)?.toDouble() ?? 0;
        final miles = distMeters / 1609.344;

        lastActivity ??= d;
        lastActivityId ??= doc.id;

        if (started.isAfter(weekStart) || started.isAtSameMomentAs(weekStart)) {
          weekMi += miles;
          weekCount++;
        }
        if (started.isAfter(today0) || started.isAtSameMomentAs(today0)) {
          todayMi += miles;
          todayCount++;
        }
      }

      return RunGoalProgress(
        todayMiles: todayMi,
        weekMiles: weekMi,
        todayActivityCount: todayCount,
        weekActivityCount: weekCount,
        lastActivity: lastActivity,
        lastActivityId: lastActivityId,
      );
    } catch (e, st) {
      _logError('goals fetch failed', e, st);
      return RunGoalProgress.empty;
    }
  }
}

// =======================================================================
// SETTINGS SHEET
//
// Glass bottom sheet, navy gradient, drag handle, 4 sections. Uses
// StatefulWidget (not StatelessWidget) because we need live state for
// the pending changes — user can toggle multiple settings and only
// hit "Done" to commit. Dismissing the sheet without Done still saves
// (matches expectation from Apple Health / Strava).
// =======================================================================

class _RunSettingsSheet extends StatefulWidget {
  final RunSettings initial;
  final void Function(RunSettings updated) onChanged;

  const _RunSettingsSheet({
    required this.initial,
    required this.onChanged,
  });

  @override
  State<_RunSettingsSheet> createState() => _RunSettingsSheetState();
}

class _RunSettingsSheetState extends State<_RunSettingsSheet> {
  late RunSettings _current;

  @override
  void initState() {
    super.initState();
    _current = widget.initial;
  }

  void _update(RunSettings next) {
    setState(() => _current = next);
    widget.onChanged(next);
  }

  @override
  Widget build(BuildContext context) {
    final mq = MediaQuery.of(context);
    return Container(
      constraints: BoxConstraints(
        maxHeight: mq.size.height * 0.88,
      ),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [_joviNavy, _joviNavyDark],
        ),
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(28),
          topRight: Radius.circular(28),
        ),
        border: Border.all(
          color: Colors.white.withOpacity(0.08),
          width: 1,
        ),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Drag handle
          Padding(
            padding: const EdgeInsets.only(top: 10, bottom: 8),
            child: Container(
              width: 44,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.25),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          // Title row
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 4, 20, 14),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(9),
                  decoration: BoxDecoration(
                    color: _joviCoral.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(11),
                  ),
                  child: const Icon(Icons.tune_rounded,
                      color: _joviCoral, size: 19),
                ),
                const SizedBox(width: 12),
                const Text(
                  'Fitness Settings',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.6,
                  ),
                ),
                const Spacer(),
                _PressableMaterial(
                  child: InkWell(
                    onTap: () => Navigator.of(context).pop(),
                    borderRadius: BorderRadius.circular(20),
                    child: Container(
                      padding: const EdgeInsets.all(7),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.08),
                        shape: BoxShape.circle,
                      ),
                      child: Icon(Icons.close_rounded,
                          color: Colors.white.withOpacity(0.8), size: 17),
                    ),
                  ),
                ),
              ],
            ),
          ),
          // Content
          Flexible(
            child: SingleChildScrollView(
              padding: EdgeInsets.fromLTRB(20, 4, 20, 20 + mq.padding.bottom),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildDisplaySection(),
                  const SizedBox(height: 18),
                  _buildAudioSection(),
                  const SizedBox(height: 18),
                  _buildTrackingSection(),
                  const SizedBox(height: 18),
                  _buildGoalsSection(),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ------------------------ SECTIONS ------------------------

  Widget _buildDisplaySection() {
    return _sectionCard(
      title: 'Display',
      icon: Icons.remove_red_eye_outlined,
      children: [
        _sectionLabel('Primary stat during runs'),
        const SizedBox(height: 8),
        _segmentedControl<PrimaryStatChoice>(
          options: const [
            PrimaryStatChoice.pace,
            PrimaryStatChoice.speed,
            PrimaryStatChoice.distance,
            PrimaryStatChoice.duration,
          ],
          labelOf: primaryStatChoiceLabel,
          selected: _current.primaryStatForRun,
          onChange: (v) => _update(_current.copyWith(
            primaryStatForRun: v,
            // Keep walk synced with run (most people want the same)
            primaryStatForWalk: v,
          )),
        ),
        const SizedBox(height: 10),
        Text(
          'Applies to Run and Walk. Rides default to Speed.',
          style: TextStyle(
            color: Colors.white.withOpacity(0.5),
            fontSize: 11.5,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 16),
        _divider(),
        const SizedBox(height: 14),
        _sectionLabel('Units'),
        const SizedBox(height: 8),
        _segmentedControl<bool>(
          options: const [false, true],
          labelOf: (v) => v ? 'Kilometers' : 'Miles',
          selected: _current.useMetric,
          onChange: (v) => _update(_current.copyWith(useMetric: v)),
        ),
      ],
    );
  }

  Widget _buildAudioSection() {
    return _sectionCard(
      title: 'Audio',
      icon: Icons.record_voice_over_outlined,
      children: [
        _toggleRow(
          title: 'Voice cues',
          subtitle: 'Spoken pace and distance at each split boundary',
          value: _current.voiceCuesEnabled,
          onChange: (v) => _update(_current.copyWith(voiceCuesEnabled: v)),
        ),
        if (_current.voiceCuesEnabled) ...[
          const SizedBox(height: 14),
          _divider(),
          const SizedBox(height: 14),
          _sectionLabel('Voice volume'),
          const SizedBox(height: 4),
          Row(
            children: [
              Icon(Icons.volume_down_rounded,
                  color: Colors.white.withOpacity(0.4), size: 20),
              Expanded(
                child: SliderTheme(
                  data: SliderThemeData(
                    activeTrackColor: _joviCoral,
                    inactiveTrackColor: Colors.white.withOpacity(0.1),
                    thumbColor: _joviCoral,
                    overlayColor: _joviCoral.withOpacity(0.15),
                    trackHeight: 3,
                    thumbShape:
                        const RoundSliderThumbShape(enabledThumbRadius: 8),
                  ),
                  child: Slider(
                    value: _current.voiceVolume,
                    onChanged: (v) =>
                        _update(_current.copyWith(voiceVolume: v)),
                  ),
                ),
              ),
              Icon(Icons.volume_up_rounded,
                  color: Colors.white.withOpacity(0.8), size: 20),
              const SizedBox(width: 6),
              SizedBox(
                width: 36,
                child: Text(
                  '${(_current.voiceVolume * 100).round()}%',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 12.5,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
        ],
      ],
    );
  }

  Widget _buildTrackingSection() {
    return _sectionCard(
      title: 'Tracking',
      icon: Icons.gps_fixed_rounded,
      children: [
        _toggleRow(
          title: 'Auto-pause',
          subtitle: 'Pauses the timer when you stop moving',
          value: _current.autoPauseEnabled,
          onChange: (v) => _update(_current.copyWith(autoPauseEnabled: v)),
        ),
        const SizedBox(height: 14),
        _divider(),
        const SizedBox(height: 14),
        _toggleRow(
          title: 'Keep screen awake',
          subtitle: 'Prevents screen from dimming during a run',
          value: _current.keepScreenOn,
          onChange: (v) => _update(_current.copyWith(keepScreenOn: v)),
        ),
        const SizedBox(height: 14),
        _divider(),
        const SizedBox(height: 14),
        _sectionLabel('GPS accuracy'),
        const SizedBox(height: 8),
        _segmentedControl<GpsAccuracyChoice>(
          options: const [
            GpsAccuracyChoice.balanced,
            GpsAccuracyChoice.precise,
          ],
          labelOf: gpsAccuracyChoiceLabel,
          selected: _current.gpsAccuracy,
          onChange: (v) => _update(_current.copyWith(gpsAccuracy: v)),
        ),
        const SizedBox(height: 10),
        Text(
          _current.gpsAccuracy == GpsAccuracyChoice.precise
              ? 'Highest precision. Uses more battery.'
              : 'Good precision with better battery life. Recommended for long rides.',
          style: TextStyle(
            color: Colors.white.withOpacity(0.5),
            fontSize: 11.5,
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }

  Widget _buildGoalsSection() {
    final useMetric = _current.useMetric;
    final unit = useMetric ? 'km' : 'mi';
    final daily = useMetric
        ? _current.dailyGoalMiles * 1.609344
        : _current.dailyGoalMiles;
    final weekly = useMetric
        ? _current.weeklyGoalMiles * 1.609344
        : _current.weeklyGoalMiles;

    return _sectionCard(
      title: 'Goals',
      icon: Icons.flag_outlined,
      children: [
        _goalStepper(
          title: 'Daily goal',
          subtitle: 'Resets every midnight',
          valueText: daily <= 0 ? 'Off' : '${daily.toStringAsFixed(1)} $unit',
          onMinus: () {
            var next = _current.dailyGoalMiles - (useMetric ? 0.62 : 0.5);
            if (next < 0) next = 0;
            _update(_current.copyWith(dailyGoalMiles: next));
          },
          onPlus: () {
            final next = _current.dailyGoalMiles + (useMetric ? 0.62 : 0.5);
            _update(_current.copyWith(dailyGoalMiles: next.clamp(0.0, 50.0)));
          },
        ),
        const SizedBox(height: 14),
        _divider(),
        const SizedBox(height: 14),
        _goalStepper(
          title: 'Weekly goal',
          subtitle: 'Resets every Monday',
          valueText: weekly <= 0 ? 'Off' : '${weekly.toStringAsFixed(1)} $unit',
          onMinus: () {
            var next = _current.weeklyGoalMiles - (useMetric ? 3.1 : 2.0);
            if (next < 0) next = 0;
            _update(_current.copyWith(weeklyGoalMiles: next));
          },
          onPlus: () {
            final next = _current.weeklyGoalMiles + (useMetric ? 3.1 : 2.0);
            _update(_current.copyWith(weeklyGoalMiles: next.clamp(0.0, 200.0)));
          },
        ),
      ],
    );
  }

  // ------------------------ PRIMITIVES ------------------------

  Widget _sectionCard({
    required String title,
    required IconData icon,
    required List<Widget> children,
  }) {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: Colors.white.withOpacity(0.08)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 15, color: _joviCoral.withOpacity(0.9)),
              const SizedBox(width: 8),
              Text(
                title,
                style: const TextStyle(
                  color: _joviCoral,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  letterSpacing: -0.1,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          ...children,
        ],
      ),
    );
  }

  Widget _sectionLabel(String text) => Text(
        text,
        style: TextStyle(
          color: Colors.white.withOpacity(0.85),
          fontSize: 13.5,
          fontWeight: FontWeight.w600,
        ),
      );

  Widget _divider() => Container(
        height: 1,
        color: Colors.white.withOpacity(0.06),
      );

  Widget _segmentedControl<T>({
    required List<T> options,
    required String Function(T) labelOf,
    required T selected,
    required void Function(T) onChange,
  }) {
    return Container(
      padding: const EdgeInsets.all(3),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.06),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        children: options.map((opt) {
          final active = opt == selected;
          return Expanded(
            child: _PressableMaterial(
              child: InkWell(
                onTap: () {
                  if (!active) {
                    HapticFeedback.selectionClick();
                    onChange(opt);
                  }
                },
                borderRadius: BorderRadius.circular(8),
                child: AnimatedContainer(
                  duration: _Motion.select,
                  curve: _Motion.settle,
                  padding: const EdgeInsets.symmetric(vertical: 10),
                  decoration: BoxDecoration(
                    color: active ? _joviCoral : Colors.transparent,
                    borderRadius: BorderRadius.circular(8),
                    boxShadow: active
                        ? [
                            BoxShadow(
                              color: _joviCoral.withOpacity(0.3),
                              blurRadius: 8,
                              offset: const Offset(0, 2),
                            ),
                          ]
                        : null,
                  ),
                  child: Center(
                    child: Text(
                      labelOf(opt),
                      style: TextStyle(
                        color: active
                            ? Colors.white
                            : Colors.white.withOpacity(0.7),
                        fontSize: 12.5,
                        fontWeight: active ? FontWeight.w800 : FontWeight.w600,
                        letterSpacing: -0.1,
                      ),
                    ),
                  ),
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _toggleRow({
    required String title,
    required String subtitle,
    required bool value,
    required void Function(bool) onChange,
  }) {
    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.2,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                subtitle,
                style: TextStyle(
                  color: Colors.white.withOpacity(0.5),
                  fontSize: 11.5,
                  fontWeight: FontWeight.w500,
                  height: 1.35,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(width: 12),
        Switch.adaptive(
          value: value,
          onChanged: (v) {
            HapticFeedback.selectionClick();
            onChange(v);
          },
          activeColor: Colors.white,
          activeTrackColor: _joviCoral,
          inactiveThumbColor: Colors.white.withOpacity(0.8),
          inactiveTrackColor: Colors.white.withOpacity(0.12),
        ),
      ],
    );
  }

  Widget _goalStepper({
    required String title,
    required String subtitle,
    required String valueText,
    required VoidCallback onMinus,
    required VoidCallback onPlus,
  }) {
    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.2,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                subtitle,
                style: TextStyle(
                  color: Colors.white.withOpacity(0.5),
                  fontSize: 11.5,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(width: 12),
        _stepperButton(icon: Icons.remove_rounded, onTap: onMinus),
        SizedBox(
          width: 72,
          child: Text(
            valueText,
            textAlign: TextAlign.center,
            style: TextStyle(
              color: valueText == 'Off'
                  ? Colors.white.withOpacity(0.4)
                  : Colors.white,
              fontSize: 14,
              fontWeight: FontWeight.w800,
              letterSpacing: -0.2,
            ),
          ),
        ),
        _stepperButton(icon: Icons.add_rounded, onTap: onPlus),
      ],
    );
  }

  Widget _stepperButton({
    required IconData icon,
    required VoidCallback onTap,
  }) {
    return _PressableMaterial(
      child: InkWell(
        onTap: () {
          HapticFeedback.selectionClick();
          onTap();
        },
        borderRadius: BorderRadius.circular(10),
        child: Container(
          width: 40,
          height: 40,
          decoration: BoxDecoration(
            color: _joviCoral.withOpacity(0.15),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: _joviCoral.withOpacity(0.3)),
          ),
          child: Icon(icon, size: 18, color: _joviCoral),
        ),
      ),
    );
  }
}

class RunActivityPicker extends StatefulWidget {
  const RunActivityPicker({
    Key? key,
    this.width,
    this.height,
  }) : super(key: key);

  final double? width;
  final double? height;

  @override
  State<RunActivityPicker> createState() => _RunActivityPickerState();
}

class _RunActivityPickerState extends State<RunActivityPicker> {
  ActivityType? _selected;
  bool _starting = false;
  bool _controllerInited = false;

  // Start-tab dynamic data
  final RunWeatherService _weatherSvc = RunWeatherService();
  final RunGoalsService _goalsSvc = RunGoalsService();
  RunWeatherData? _weather;
  bool _weatherLoading = true;
  RunGoalProgress _goals = RunGoalProgress.empty;
  bool _goalsLoading = true;

  @override
  void initState() {
    super.initState();
    _initController();
    _loadWeather();
    _loadGoals();
  }

  Future<void> _loadWeather() async {
    try {
      final w = await _weatherSvc.get();
      if (!mounted) return;
      setState(() {
        _weather = w;
        _weatherLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _weatherLoading = false);
    }
  }

  Future<void> _loadGoals({bool force = false}) async {
    try {
      final g = await _goalsSvc.load(force: force);
      if (!mounted) return;
      setState(() {
        _goals = g;
        _goalsLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _goalsLoading = false);
    }
  }

  Future<void> _refreshAll() async {
    HapticFeedback.lightImpact();
    setState(() {
      _weatherLoading = true;
      _goalsLoading = true;
    });
    await Future.wait([_loadWeather(), _loadGoals(force: true)]);
  }

  Future<void> _initController() async {
    try {
      await RunController.instance.init();
      if (mounted) setState(() => _controllerInited = true);
    } catch (e) {
      _log('controller init failed: $e');
      if (mounted) setState(() => _controllerInited = true);
    }
  }

  Future<void> _onStart() async {
    final type = _selected;
    if (type == null || _starting) return;
    setState(() => _starting = true);
    HapticFeedback.mediumImpact();

    try {
      // Permission gate: check current state; if denied, show primer.
      final perm = await Geolocator.checkPermission();
      bool granted = perm == LocationPermission.always ||
          perm == LocationPermission.whileInUse;

      if (!granted) {
        final result = await Navigator.of(context).push<bool>(
          MaterialPageRoute(
            builder: (_) => const RunPermissionPrimer(),
            fullscreenDialog: true,
          ),
        );
        granted = result == true;
      }

      if (!granted) {
        if (mounted) {
          setState(() => _starting = false);
          _showPermissionDeniedDialog();
        }
        return;
      }

      // Verify OS location service is on.
      final serviceOn = await Geolocator.isLocationServiceEnabled();
      if (!serviceOn) {
        if (mounted) {
          setState(() => _starting = false);
          _showLocationServiceOffDialog();
        }
        return;
      }

      // Kick off acquisition.
      await RunController.instance.startActivity(type);

      if (!mounted) return;
      // Push to active screen. RunController's state machine is in
      // "acquiring" — the active screen reads that and shows the
      // "Acquiring GPS" splash until recording begins.
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => const RunActiveScreen(),
          fullscreenDialog: true,
        ),
      );
      if (mounted) setState(() => _starting = false);
    } catch (e, st) {
      _log('start flow error: $e\n$st');
      if (mounted) {
        setState(() => _starting = false);
        _showError(e);
      }
    }
  }

  void _showError(Object err) {
    final text = err is LocationPermissionDeniedException
        ? 'Location permission is required to track activities.'
        : err is LocationServiceDisabledException
            ? 'Turn on Location Services to start tracking.'
            : 'Something went wrong. Please try again.';
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(text,
        accent: _joviErrorRed, icon: CupertinoIcons.exclamationmark_circle));
  }

  void _showLocationServiceOffDialog() {
showCupertinoDialog<void>(
      context: context,
      builder: (ctx) => CupertinoAlertDialog(
        title: const Text('Location Is Off'),
        content: const Padding(
          padding: EdgeInsets.only(top: 8),
          child: Text('Turn on Location Services in your device settings to track your activity.'),
        ),
        actions: [
          CupertinoDialogAction(
            isDefaultAction: true,
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  // Shown when the user taps "Not now" on the permission primer (or
  // denies the OS permission dialog). GPS is required to track a run,
  // so we can't continue — but a silent no-op looks broken. Give them
  // a clear explanation plus a path to enable permissions later.
  void _showPermissionDeniedDialog() {
    showCupertinoDialog<void>(
      context: context,
      builder: (ctx) => CupertinoAlertDialog(
        title: const Text('Location Needed'),
        content: const Padding(
          padding: EdgeInsets.only(top: 8),
          child: Text(
              'Tracking your pace, distance, and route needs GPS access. You can change this anytime in Settings under Location Services.'),
        ),
        actions: [
          CupertinoDialogAction(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Not Now'),
          ),
          CupertinoDialogAction(
            isDefaultAction: true,
            onPressed: () async {
              Navigator.of(ctx).pop();
              try {
                await openAppSettings();
              } catch (_) {}
            },
            child: const Text('Open Settings'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _joviNavyDark,
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [_joviNavy, _joviNavyDark, _joviNavyDark],
            stops: [0.0, 0.5, 1.0],
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              // Top bar
              Padding(
                padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
                child: Row(
                  children: [
                    IconButton(
                      onPressed: () => Navigator.of(context).maybePop(),
                      icon: const Icon(Icons.arrow_back_rounded,
                          color: Colors.white),
                    ),
                    const Spacer(),
                    IconButton(
                      onPressed: _openSettingsSheet,
                      icon: Icon(
                        Icons.tune_rounded,
                        color: Colors.white.withOpacity(0.8),
                      ),
                    ),
                  ],
                ),
              ),
              // Main scrollable content: header, weather, goals,
              // last activity, activity tiles. Using RefreshIndicator
              // so pull-to-refresh re-fetches weather + goals.
              Expanded(
                child: RefreshIndicator(
                  onRefresh: _refreshAll,
                  color: _joviCoral,
                  backgroundColor: _joviNavy,
                  child: ListView(
                    physics: const AlwaysScrollableScrollPhysics(
                      parent: BouncingScrollPhysics(),
                    ),
                    padding: const EdgeInsets.symmetric(horizontal: 20),
                    children: [
                      // Greeting + weather-aware title
                      Padding(
                        padding: const EdgeInsets.fromLTRB(4, 4, 4, 18),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              _buildGreeting(),
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 28,
                                fontWeight: FontWeight.w700,
                                letterSpacing: -0.7,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              _buildSubtitle(),
                              style: TextStyle(
                                color: Colors.white.withOpacity(0.55),
                                fontSize: 14.5,
                                fontWeight: FontWeight.w500,
                                height: 1.3,
                              ),
                            ),
                          ],
                        ),
                      ),
                      // Weather card
                      _buildWeatherCard(),
                      const SizedBox(height: 14),
                      // Goals row: daily ring + weekly bar
                      _buildGoalsCard(),
                      const SizedBox(height: 14),
                      // Last activity — tap to open detail
                      if (_goals.lastActivity != null) ...[
                        _buildLastActivityCard(),
                        const SizedBox(height: 18),
                      ] else
                        const SizedBox(height: 6),
                      // Section header
                      Padding(
                        padding: const EdgeInsets.fromLTRB(4, 6, 4, 10),
                        child: Text(
                          'Start an Activity',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.6),
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            letterSpacing: -0.1,
                          ),
                        ),
                      ),
                      _activityCard(
                        ActivityType.run,
                        'Track your pace, splits, and distance.',
                      ),
                      const SizedBox(height: 12),
                      _activityCard(
                        ActivityType.walk,
                        'Log your daily miles with auto-pause.',
                      ),
                      const SizedBox(height: 12),
                      _activityCard(
                        ActivityType.ride,
                        'Speed, distance, and elevation for your ride.',
                      ),
                      const SizedBox(height: 20),
                    ],
                  ),
                ),
              ),
              // Start button
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
                child: SizedBox(
                  width: double.infinity,
                  height: 60,
                  child: ElevatedButton(
                    onPressed:
                        (_selected == null || _starting || !_controllerInited)
                            ? null
                            : _onStart,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: _joviCoral,
                      foregroundColor: Colors.white,
                      disabledBackgroundColor: Colors.white.withOpacity(0.1),
                      disabledForegroundColor: Colors.white.withOpacity(0.4),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(16),
                      ),
                      elevation: _selected != null ? 8 : 0,
                      shadowColor: _joviCoral.withOpacity(0.5),
                    ),
                    child: _starting
                        ? const SizedBox(
                            width: 22,
                            height: 22,
                            child: CircularProgressIndicator(
                              color: Colors.white,
                              strokeWidth: 2.2,
                            ),
                          )
                        : Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(Icons.play_arrow_rounded,
                                  size: 26,
                                  color: _selected != null
                                      ? Colors.white
                                      : Colors.white.withOpacity(0.4)),
                              const SizedBox(width: 6),
                              Text(
                                _selected == null
                                    ? 'Pick an activity'
                                    : 'Start ${activityTypeLabel(_selected!)}',
                                style: const TextStyle(
                                  fontSize: 17,
                                  fontWeight: FontWeight.w800,
                                  letterSpacing: 0.3,
                                ),
                              ),
                            ],
                          ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ------------------------ NEW HELPERS (Start tab redesign) ------------------------

  String _buildGreeting() {
    final h = DateTime.now().hour;
    final part =
        h < 12 ? 'Good morning' : (h < 17 ? 'Good afternoon' : 'Good evening');
    return part;
  }

  String _buildSubtitle() {
    final settings = RunController.instance.settings;
    if (_goals.weekActivityCount > 0 && settings.weeklyGoalMiles > 0) {
      final unit = settings.useMetric ? 'km' : 'mi';
      final done =
          settings.useMetric ? _goals.weekMiles * 1.609344 : _goals.weekMiles;
      final goal = settings.useMetric
          ? settings.weeklyGoalMiles * 1.609344
          : settings.weeklyGoalMiles;
      return '${done.toStringAsFixed(1)} / ${goal.toStringAsFixed(1)} $unit this week';
    }
    if (_goals.weekActivityCount > 0) {
      return 'Nice work this week — keep the momentum.';
    }
    return 'Ready when you are.';
  }

  // ---- Settings sheet ----

  void _openSettingsSheet() {
    HapticFeedback.lightImpact();
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      barrierColor: Colors.black.withOpacity(0.55),
      builder: (sheetCtx) {
        return _RunSettingsSheet(
          initial: RunController.instance.settings,
          onChanged: (next) {
            // Commit each change immediately so the UI reflects live.
            // Settings fire a notifyListeners, so this picker re-reads
            // via setState below.
            RunController.instance.updateSettings(next);
            if (mounted) setState(() {});
          },
        );
      },
    );
  }

  // ---- Weather card ----

  Widget _buildWeatherCard() {
    if (_weatherLoading) {
      return _glassShell(
        height: 110,
        child: const Center(
          child: SizedBox(
            width: 20,
            height: 20,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              valueColor: AlwaysStoppedAnimation<Color>(_joviCoral),
            ),
          ),
        ),
      );
    }
    final w = _weather;
    if (w == null) return const SizedBox.shrink();

    // Accent color + label by runnability
    Color accent;
    String qualityLabel;
    IconData qualityIcon;
    switch (w.quality) {
      case RunWeatherQuality.great:
        accent = _joviMint;
        qualityLabel = 'Great';
        qualityIcon = Icons.check_circle_rounded;
        break;
      case RunWeatherQuality.ok:
        accent = _joviGold;
        qualityLabel = 'OK';
        qualityIcon = Icons.info_rounded;
        break;
      case RunWeatherQuality.bad:
        accent = _joviErrorRed;
        qualityLabel = 'Tough';
        qualityIcon = Icons.warning_rounded;
        break;
      case RunWeatherQuality.unknown:
        accent = Colors.white.withOpacity(0.4);
        qualityLabel = '—';
        qualityIcon = Icons.help_outline_rounded;
        break;
    }

    return ClipRRect(
      borderRadius: BorderRadius.circular(18),
      child: RepaintBoundary(
        child: Container(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.09),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(
              color: accent.withOpacity(0.28),
              width: 1.2,
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.18),
                blurRadius: 14,
                offset: const Offset(0, 6),
              ),
              BoxShadow(
                color: accent.withOpacity(0.06),
                blurRadius: 18,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              // Big emoji icon
              Container(
                width: 56,
                height: 56,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.05),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: Colors.white.withOpacity(0.1),
                  ),
                ),
                child: Text(
                  w.icon,
                  style: const TextStyle(fontSize: 30),
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Row(
                      children: [
                        Text(
                          '${w.tempF.round()}°',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 28,
                            fontWeight: FontWeight.w700,
                            letterSpacing: -1,
                            height: 1.0,
                          ),
                        ),
                        const SizedBox(width: 6),
                        Padding(
                          padding: const EdgeInsets.only(top: 3),
                          child: Text(
                            'F',
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.55),
                              fontSize: 13,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: accent.withOpacity(0.18),
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(
                              color: accent.withOpacity(0.4),
                              width: 0.8,
                            ),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(qualityIcon, size: 10, color: accent),
                              const SizedBox(width: 3),
                              Text(
                                qualityLabel,
                                style: TextStyle(
                                  color: accent,
                                  fontSize: 10.5,
                                  fontWeight: FontWeight.w700,
                                  letterSpacing: -0.1,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 3),
                    Text(
                      w.qualityNote,
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.7),
                        fontSize: 12.5,
                        fontWeight: FontWeight.w500,
                        height: 1.25,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 5),
                    Row(
                      children: [
                        _weatherMiniChip(
                            Icons.opacity_rounded, '${w.humidityPct}%'),
                        const SizedBox(width: 8),
                        _weatherMiniChip(
                            Icons.air_rounded, '${w.windMph.round()} mph'),
                        const SizedBox(width: 8),
                        Flexible(
                          child: Text(
                            w.cityName,
                            overflow: TextOverflow.ellipsis,
                            maxLines: 1,
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.45),
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _weatherMiniChip(IconData icon, String text) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 11, color: Colors.white.withOpacity(0.55)),
        const SizedBox(width: 3),
        Text(
          text,
          style: TextStyle(
            color: Colors.white.withOpacity(0.65),
            fontSize: 11,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }

  // ---- Goals card (daily ring + weekly bar side-by-side) ----

  Widget _buildGoalsCard() {
    final settings = RunController.instance.settings;
    final useMetric = settings.useMetric;
    final unit = useMetric ? 'km' : 'mi';

    final dailyGoalMi = settings.dailyGoalMiles;
    final weeklyGoalMi = settings.weeklyGoalMiles;
    final dailyDoneMi = _goals.todayMiles;
    final weeklyDoneMi = _goals.weekMiles;

    // Show set-up empty-state if no goals configured
    if (dailyGoalMi <= 0 && weeklyGoalMi <= 0) {
      return _PressableMaterial(
        child: InkWell(
          onTap: _openSettingsSheet,
          borderRadius: BorderRadius.circular(18),
          child: _glassShell(
            height: 86,
            borderColor: Colors.white.withOpacity(0.1),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              child: Row(
                children: [
                  Container(
                    width: 42,
                    height: 42,
                    decoration: BoxDecoration(
                      color: _joviCoral.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: _joviCoral.withOpacity(0.25),
                      ),
                    ),
                    child: const Icon(Icons.flag_outlined,
                        color: _joviCoral, size: 20),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Text(
                          'Set a goal',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 14.5,
                            fontWeight: FontWeight.w800,
                            letterSpacing: -0.2,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          'Daily or weekly targets help keep you consistent.',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.55),
                            fontSize: 12,
                            fontWeight: FontWeight.w500,
                            height: 1.3,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Icon(
                    Icons.chevron_right_rounded,
                    color: Colors.white.withOpacity(0.4),
                    size: 22,
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    }

    return _glassShell(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            // Daily ring
            if (dailyGoalMi > 0) ...[
              _buildDailyRing(
                doneMi: dailyDoneMi,
                goalMi: dailyGoalMi,
                useMetric: useMetric,
                unit: unit,
              ),
              const SizedBox(width: 16),
            ],
            // Weekly bar
            Expanded(
              child: weeklyGoalMi > 0
                  ? _buildWeeklyBar(
                      doneMi: weeklyDoneMi,
                      goalMi: weeklyGoalMi,
                      useMetric: useMetric,
                      unit: unit,
                    )
                  : _buildDailyOnlyDetail(
                      doneMi: dailyDoneMi,
                      goalMi: dailyGoalMi,
                      useMetric: useMetric,
                      unit: unit,
                    ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDailyRing({
    required double doneMi,
    required double goalMi,
    required bool useMetric,
    required String unit,
  }) {
    final pct = goalMi > 0 ? (doneMi / goalMi).clamp(0.0, 1.0) : 0.0;
    final displayDone = useMetric ? doneMi * 1.609344 : doneMi;
    return SizedBox(
      width: 82,
      height: 82,
      child: Stack(
        alignment: Alignment.center,
        children: [
          SizedBox(
            width: 82,
            height: 82,
            child: CircularProgressIndicator(
              value: pct,
              strokeWidth: 7,
              backgroundColor: Colors.white.withOpacity(0.08),
              valueColor: AlwaysStoppedAnimation<Color>(
                pct >= 1.0 ? _joviMint : _joviCoral,
              ),
            ),
          ),
          Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                displayDone.toStringAsFixed(1),
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.5,
                  height: 1.0,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                unit,
                style: TextStyle(
                  color: Colors.white.withOpacity(0.55),
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.1,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildWeeklyBar({
    required double doneMi,
    required double goalMi,
    required bool useMetric,
    required String unit,
  }) {
    final pct = goalMi > 0 ? (doneMi / goalMi).clamp(0.0, 1.0) : 0.0;
    final displayDone = useMetric ? doneMi * 1.609344 : doneMi;
    final displayGoal = useMetric ? goalMi * 1.609344 : goalMi;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          children: [
            Text(
              'This week',
              style: TextStyle(
                color: Colors.white.withOpacity(0.55),
                fontSize: 11,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.5,
              ),
            ),
            const Spacer(),
            if (pct >= 1.0)
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.check_circle_rounded,
                      color: _joviMint, size: 13),
                  const SizedBox(width: 3),
                  Text(
                    'Met',
                    style: TextStyle(
                      color: _joviMint,
                      fontSize: 10.5,
                      fontWeight: FontWeight.w700,
                      letterSpacing: -0.1,
                    ),
                  ),
                ],
              ),
          ],
        ),
        const SizedBox(height: 4),
        Row(
          crossAxisAlignment: CrossAxisAlignment.baseline,
          textBaseline: TextBaseline.alphabetic,
          children: [
            Text(
              displayDone.toStringAsFixed(1),
              style: const TextStyle(
                color: Colors.white,
                fontSize: 24,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.5,
                height: 1.0,
              ),
            ),
            const SizedBox(width: 4),
            Text(
              '/ ${displayGoal.toStringAsFixed(1)} $unit',
              style: TextStyle(
                color: Colors.white.withOpacity(0.45),
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: Stack(
            children: [
              Container(
                height: 6,
                color: Colors.white.withOpacity(0.08),
              ),
              FractionallySizedBox(
                widthFactor: pct,
                child: Container(
                  height: 6,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: pct >= 1.0
                          ? const [_joviMint, _joviMint]
                          : const [_joviCoral, _joviCoralLight],
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 4),
        Text(
          _goals.weekActivityCount == 0
              ? 'No activities yet this week'
              : '${_goals.weekActivityCount} ${_goals.weekActivityCount == 1 ? 'activity' : 'activities'} logged',
          style: TextStyle(
            color: Colors.white.withOpacity(0.45),
            fontSize: 11,
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }

  // When only a daily goal is set, show daily summary next to the ring.
  Widget _buildDailyOnlyDetail({
    required double doneMi,
    required double goalMi,
    required bool useMetric,
    required String unit,
  }) {
    final pct = goalMi > 0 ? (doneMi / goalMi).clamp(0.0, 1.0) : 0.0;
    final displayGoal = useMetric ? goalMi * 1.609344 : goalMi;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          'Today\'s goal',
          style: TextStyle(
            color: Colors.white.withOpacity(0.55),
            fontSize: 11,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.5,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          '${displayGoal.toStringAsFixed(1)} $unit',
          style: const TextStyle(
            color: Colors.white,
            fontSize: 20,
            fontWeight: FontWeight.w700,
            letterSpacing: -0.4,
            height: 1.0,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          pct >= 1.0
              ? 'Crushed it. Optional bonus miles await.'
              : '${((1 - pct) * 100).round()}% to go',
          style: TextStyle(
            color: pct >= 1.0 ? _joviMint : Colors.white.withOpacity(0.55),
            fontSize: 12,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }

  // ---- Last activity card ----

  Widget _buildLastActivityCard() {
    final last = _goals.lastActivity;
    final id = _goals.lastActivityId;
    if (last == null || id == null) return const SizedBox.shrink();

    final type = last['type'] as String? ?? 'run';
    final distMeters = (last['distanceMeters'] as num?)?.toDouble() ?? 0;
    final movingSec = (last['movingSeconds'] as num?)?.toInt() ?? 0;
    final avgSpeedMps = (last['avgSpeedMetersPerSecond'] as num?)?.toDouble();
    final startedRaw = last['startedAt'];
    DateTime? started;
    if (startedRaw is Timestamp) started = startedRaw.toDate();

    final settings = RunController.instance.settings;
    final useMetric = settings.useMetric;
    final distStr = useMetric
        ? '${(distMeters / 1000).toStringAsFixed(2)} km'
        : '${(distMeters / 1609.344).toStringAsFixed(2)} mi';
    final durStr = formatDuration(Duration(seconds: movingSec));
    final isRide = type == 'ride';
    final paceOrSpeed = avgSpeedMps == null || avgSpeedMps < 0.1
        ? '—'
        : isRide
            ? (useMetric
                ? '${(avgSpeedMps * 3.6).toStringAsFixed(1)} km/h'
                : '${mpsToMph(avgSpeedMps).toStringAsFixed(1)} mph')
            : (useMetric
                ? '${_paceMinPerKm(avgSpeedMps)} /km'
                : '${formatPaceMinPerMile(avgSpeedMps)} /mi');
    final typeIcon = type == 'walk'
        ? Icons.directions_walk_rounded
        : type == 'ride'
            ? Icons.pedal_bike_rounded
            : Icons.directions_run_rounded;
    final typeLabel = type == 'walk'
        ? 'Walk'
        : type == 'ride'
            ? 'Ride'
            : 'Run';

    return _PressableMaterial(
      child: InkWell(
        onTap: () {
          HapticFeedback.lightImpact();
          JoviRunHistoryList.openDetail(context, id);
        },
        borderRadius: BorderRadius.circular(18),
        child: _glassShell(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
            child: Row(
              children: [
                Container(
                  width: 46,
                  height: 46,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [_joviCoral, _joviCoralDark],
                    ),
                    borderRadius: BorderRadius.circular(13),
                    boxShadow: [
                      BoxShadow(
                        color: _joviCoral.withOpacity(0.3),
                        blurRadius: 10,
                        offset: const Offset(0, 4),
                      ),
                    ],
                  ),
                  child: Icon(typeIcon, color: Colors.white, size: 22),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Row(
                        children: [
                          Text(
                            'Last $typeLabel',
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 14,
                              fontWeight: FontWeight.w800,
                              letterSpacing: -0.2,
                            ),
                          ),
                          const SizedBox(width: 8),
                          if (started != null)
                            Text(
                              _friendlyTimeSince(started),
                              style: TextStyle(
                                color: Colors.white.withOpacity(0.5),
                                fontSize: 11.5,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Row(
                        children: [
                          _miniStat(distStr, Icons.straighten_rounded),
                          const SizedBox(width: 10),
                          _miniStat(durStr, Icons.access_time_rounded),
                          const SizedBox(width: 10),
                          _miniStat(
                              paceOrSpeed,
                              isRide
                                  ? Icons.speed_rounded
                                  : Icons.timer_rounded),
                        ],
                      ),
                    ],
                  ),
                ),
                Icon(
                  Icons.chevron_right_rounded,
                  color: Colors.white.withOpacity(0.4),
                  size: 22,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _miniStat(String text, IconData icon) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 12, color: Colors.white.withOpacity(0.55)),
        const SizedBox(width: 4),
        Text(
          text,
          style: TextStyle(
            color: Colors.white.withOpacity(0.85),
            fontSize: 12,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }

  String _paceMinPerKm(double speedMps) {
    if (speedMps < 0.1) return '--:--';
    final secPerKm = 1000 / speedMps;
    final mins = secPerKm ~/ 60;
    final secs = (secPerKm % 60).round();
    return '$mins:${secs.toString().padLeft(2, '0')}';
  }

  String _friendlyTimeSince(DateTime when) {
    final diff = DateTime.now().difference(when);
    if (diff.inMinutes < 60) return 'Just now';
    if (diff.inHours < 24) {
      return '${diff.inHours} ${diff.inHours == 1 ? 'hour' : 'hours'} ago';
    }
    if (diff.inDays == 1) return 'Yesterday';
    if (diff.inDays < 7) return '${diff.inDays} days ago';
    return DateFormat('MMM d').format(when);
  }

  Widget _glassShell({
    required Widget child,
    double? height,
    Color? borderColor,
  }) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(18),
      child: RepaintBoundary(
        child: Container(
          height: height,
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.07),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(
              color: borderColor ?? Colors.white.withOpacity(0.08),
              width: 1,
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.15),
                blurRadius: 14,
                offset: const Offset(0, 6),
              ),
            ],
          ),
          child: child,
        ),
      ),
    );
  }

  // ------------------------ END NEW HELPERS ------------------------

  Widget _activityCard(ActivityType type, String description) {
    final isSelected = _selected == type;
    return _PressableMaterial(
      child: InkWell(
        onTap: () {
          HapticFeedback.selectionClick();
          setState(() => _selected = type);
        },
        borderRadius: BorderRadius.circular(18),
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(18),
            boxShadow: isSelected
                ? [
                    BoxShadow(
                      color: _joviCoral.withOpacity(0.35),
                      blurRadius: 18,
                      offset: const Offset(0, 6),
                    ),
                  ]
                : [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.25),
                      blurRadius: 10,
                      offset: const Offset(0, 4),
                    ),
                  ],
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(18),
            child: RepaintBoundary(
              child: AnimatedContainer(
                duration: _Motion.select,
                curve: _Motion.settle,
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  color: isSelected
                      ? _joviCoral.withOpacity(0.15)
                      : Colors.white.withOpacity(0.085),
                  borderRadius: BorderRadius.circular(18),
                  border: Border.all(
                    color: isSelected
                        ? _joviCoral
                        : Colors.white.withOpacity(0.12),
                    width: isSelected ? 1.6 : 1,
                  ),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 58,
                      height: 58,
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: isSelected
                              ? [
                                  _joviCoral.withOpacity(0.35),
                                  _joviCoralLight.withOpacity(0.18),
                                ]
                              : [
                                  Colors.white.withOpacity(0.1),
                                  Colors.white.withOpacity(0.04),
                                ],
                        ),
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(
                          color: isSelected
                              ? _joviCoral.withOpacity(0.5)
                              : Colors.white.withOpacity(0.1),
                          width: 0.8,
                        ),
                      ),
                      child: Icon(
                        activityTypeIcon(type),
                        color: isSelected
                            ? Colors.white
                            : Colors.white.withOpacity(0.85),
                        size: 30,
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            activityTypeLabel(type),
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 19,
                              fontWeight: FontWeight.w700,
                              letterSpacing: -0.3,
                            ),
                          ),
                          const SizedBox(height: 3),
                          Text(
                            description,
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.6),
                              fontSize: 13,
                              fontWeight: FontWeight.w500,
                              height: 1.3,
                            ),
                          ),
                        ],
                      ),
                    ),
                    if (isSelected)
                      Container(
                        width: 26,
                        height: 26,
                        decoration: const BoxDecoration(
                          shape: BoxShape.circle,
                          color: _joviCoral,
                        ),
                        child: const Icon(
                          Icons.check_rounded,
                          color: Colors.white,
                          size: 17,
                        ),
                      ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// =======================================================================
// RUN ACTIVE SCREEN
//
// The screen during a live activity. Subscribes to
// RunController.instance for state updates.
//
// States it renders:
//   1. ACQUIRING — showing "Acquiring GPS..." splash with accuracy
//      readout. No recording yet. User can cancel via back button.
//   2. RECORDING / PAUSED — Mapbox backdrop with route line, stats
//      overlay, pause/stop controls. Auto-pause banner when
//      autoPaused is true.
//   3. COMPLETED — briefly visible as the user transitions to
//      Summary. We just pop back rather than render anything special.
//
// Prevents back navigation during recording — users must tap Stop.
// Handles phone lock gracefully via wakelock (enabled in controller
// when recording).
// =======================================================================

class RunActiveScreen extends StatefulWidget {
  const RunActiveScreen({
    Key? key,
    this.width,
    this.height,
  }) : super(key: key);

  final double? width;
  final double? height;

  @override
  State<RunActiveScreen> createState() => _RunActiveScreenState();
}

class _RunActiveScreenState extends State<RunActiveScreen>
    with WidgetsBindingObserver {
  final RunController _ctl = RunController.instance;
  Timer? _tickerTimer;
  mb.MapboxMap? _mapController;
  mb.PointAnnotationManager? _userMarkerManager;
  mb.PolylineAnnotationManager? _routeManager;
  mb.PolylineAnnotation? _routeAnnotation;
  int _lastRenderedPointCount = 0;
  bool _cameraFollowingUser = true;
  bool _mapReady = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _ctl.addListener(_onControllerUpdate);
    // Periodic ticker so the elapsed-time readout updates between
    // GPS fixes. 500ms cadence matches the engine's update throttle.
    _tickerTimer = Timer.periodic(const Duration(milliseconds: 500), (_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _ctl.removeListener(_onControllerUpdate);
    _tickerTimer?.cancel();
    super.dispose();
  }

  void _onControllerUpdate() {
    if (!mounted) return;
    // When we transition to completed, leave this screen so the
    // summary screen can take over. Session 3 will wire up the
    // summary — for now we just pop to the picker.
    if (_ctl.acquisitionState == RunAcquisitionState.completed) {
      // Defer pop so we don't call pop during a notify callback.
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        final s = _ctl.session;
        final completedId = s?.id;
        // Capture the root navigator before popping: the summary is
        // pushed onto whatever sits behind this screen.
        final rootNav = Navigator.of(context, rootNavigator: true);
        if (s != null && completedId == null) {
          _showCompletedSnackbar(s, completedId);
        }
        _ctl.clearCompleted();
        Navigator.of(context).pop();
        if (completedId != null) {
          // Post-run summary: the detail screen in justFinished mode
          // waits for the final checkpoint, then shows the map, splits
          // and a notes field. RunDetailScreen lives in the history
          // file, reached through the widget-class static.
          JoviRunHistoryList.openDetail(rootNav.context, completedId,
              justFinished: true);
        }
      });
      return;
    }
    // Redraw + sync map.
    setState(() {});
    _syncMapToSession();
  }

  void _showCompletedSnackbar(ActivitySession s, String? completedActivityId) {
    // Capture the navigator context from the parent — after this
    // screen pops, we want the "View" action to push the detail
    // onto whatever was behind us.
    final rootNav = Navigator.of(context, rootNavigator: true);
    final scaffold = ScaffoldMessenger.of(context);
    scaffold.showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.check_circle_rounded,
                color: Colors.white, size: 22),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                '${activityTypeLabel(s.type)} saved — ${formatDistanceMiles(s.distanceMeters)} in ${formatDuration(s.movingTime)}',
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
            ),
          ],
        ),
        backgroundColor: _joviMint,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
        duration: const Duration(seconds: 5),
        action: completedActivityId == null
            ? null
            : SnackBarAction(
                label: 'View',
                textColor: Colors.white,
                onPressed: () {
                  // Navigate to the detail screen for the run just
                  // finished. Uses the root navigator so this works
                  // even after the active screen has popped.
                  //
                  // RunDetailScreen lives in jovi_run_history.dart —
                  // a separate FF compile unit — so we can't reference
                  // it directly. JoviRunHistoryList.openDetail is a
                  // static helper on a widget class (which IS visible
                  // across files via the FF widgets barrel) that
                  // pushes the detail screen for us.
                  JoviRunHistoryList.openDetail(
                      rootNav.context, completedActivityId);
                },
              ),
      ),
    );
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    // When app comes back to foreground, force a rebuild so stats
    // readouts are current (the elapsed counter depends on DateTime.now).
    if (state == AppLifecycleState.resumed && mounted) {
      setState(() {});
    }
  }

  Future<bool> _onWillPop() async {
    // Disallow back-navigation during an active session. User must
    // long-press Stop to finish a run intentionally.
    if (_ctl.acquisitionState == RunAcquisitionState.acquiring) {
      await _ctl.abortAcquisition();
      return true;
    }
    if (_ctl.session == null) return true;
    // Show a dismiss prompt — but default to NOT popping so pocket
    // swipes don't kill the run.
    final result = await showCupertinoDialog<bool>(
      context: context,
      builder: (ctx) => CupertinoAlertDialog(
        title: const Text('End This Activity?'),
        content: const Padding(
          padding: EdgeInsets.only(top: 8),
          child: Text(
              'Your progress will be discarded. To save it, hold the Stop button instead.'),
        ),
        actions: [
          CupertinoDialogAction(
            isDefaultAction: true,
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Keep Going'),
          ),
          CupertinoDialogAction(
            isDestructiveAction: true,
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Discard'),
          ),
        ],
      ),
    );
    if (result == true) {
      await _ctl.discard();
      return true;
    }
    return false;
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) async {
        if (didPop) return;
        final shouldPop = await _onWillPop();
        if (shouldPop && mounted) Navigator.of(context).pop();
      },
      child: Scaffold(
        backgroundColor: _joviNavyDark,
        body: AnnotatedRegion<SystemUiOverlayStyle>(
          value: const SystemUiOverlayStyle(
            statusBarColor: Colors.transparent,
            statusBarIconBrightness: Brightness.light,
          ),
          child: _buildBody(),
        ),
      ),
    );
  }

  Widget _buildBody() {
    switch (_ctl.acquisitionState) {
      case RunAcquisitionState.acquiring:
        return _buildAcquiringSplash();
      case RunAcquisitionState.recording:
        return _buildActiveContent();
      case RunAcquisitionState.idle:
      case RunAcquisitionState.completed:
        // Should not normally be visible — we pop in these cases. Guard
        // with a neutral navy background.
        return const SizedBox.expand();
    }
  }

  // ------------------------------------------------------------------
  // ACQUIRING GPS SPLASH
  // ------------------------------------------------------------------

  Widget _buildAcquiringSplash() {
    final acc = _ctl.lastSeenAccuracyMeters;
    final elapsed = _ctl.acquisitionElapsed;
    final accRatio =
        acc == null ? null : (30.0 / acc).clamp(0.0, 1.0).toDouble();
    final type = _ctl.pendingActivity ?? ActivityType.run;

    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [_joviNavy, _joviNavyDark],
        ),
      ),
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(
            children: [
              Row(
                children: [
                  IconButton(
                    onPressed: () async {
                      await _ctl.abortAcquisition();
                      if (mounted) Navigator.of(context).pop();
                    },
                    icon: const Icon(Icons.close_rounded,
                        color: Colors.white, size: 26),
                  ),
                  const Spacer(),
                ],
              ),
              const Spacer(),
              // Pulsing GPS icon
              _AcquiringPulse(icon: activityTypeIcon(type)),
              const SizedBox(height: 30),
              const Text(
                'Finding satellites…',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 26,
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.5,
                ),
              ),
              const SizedBox(height: 10),
              Text(
                acc == null
                    ? 'Hold tight — this usually takes a few seconds.'
                    : 'Signal accuracy: ${acc.round()}m',
                style: TextStyle(
                  color: Colors.white.withOpacity(0.65),
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 36),
              // Accuracy bar
              Container(
                width: double.infinity,
                height: 8,
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.08),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: FractionallySizedBox(
                  alignment: Alignment.centerLeft,
                  widthFactor: accRatio ?? 0.05,
                  child: Container(
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [_joviCoral, _joviCoralLight],
                      ),
                      borderRadius: BorderRadius.circular(4),
                      boxShadow: [
                        BoxShadow(
                          color: _joviCoral.withOpacity(0.4),
                          blurRadius: 8,
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 24),
              if (elapsed.inSeconds >= 15)
                Text(
                  'Taking longer than usual. Try stepping outside for a clearer signal.',
                  style: TextStyle(
                    color: _joviGold.withOpacity(0.9),
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                  ),
                  textAlign: TextAlign.center,
                ),
              const Spacer(flex: 2),
              TextButton(
                onPressed: () async {
                  await _ctl.abortAcquisition();
                  if (mounted) Navigator.of(context).pop();
                },
                style: TextButton.styleFrom(
                  foregroundColor: Colors.white.withOpacity(0.55),
                ),
                child: const Text(
                  'Cancel',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              const SizedBox(height: 10),
            ],
          ),
        ),
      ),
    );
  }

  // Active content + map sync continue in next part...

  // ------------------------------------------------------------------
  // ACTIVE (recording / paused) CONTENT
  // Mapbox backdrop, stats overlay, controls.
  // ------------------------------------------------------------------

  Widget _buildActiveContent() {
    return Stack(
      fit: StackFit.expand,
      children: [
        // Map backdrop
        _buildMap(),
        // Scrim for readability over the map
        _buildScrim(),
        // Auto-pause / manual-pause banner
        if (_ctl.isPaused) _buildPauseBanner(),
        // Top bar (activity type + lock button)
        Positioned(
          top: 0,
          left: 0,
          right: 0,
          child: SafeArea(child: _buildTopBar()),
        ),
        // Stats overlay (primary + secondary) anchored toward the top
        Positioned(
          top: 0,
          left: 0,
          right: 0,
          child: SafeArea(
            child: Padding(
              padding: const EdgeInsets.only(top: 64),
              child: _buildStatsOverlay(),
            ),
          ),
        ),
        // Bottom controls
        Positioned(
          bottom: 0,
          left: 0,
          right: 0,
          child: SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: _buildControls(),
            ),
          ),
        ),
        // Recenter button (small FAB, bottom-right above controls)
        Positioned(
          bottom: 130,
          right: 18,
          child: SafeArea(
            top: false,
            child: AnimatedOpacity(
              duration: const Duration(milliseconds: 250),
              opacity: _cameraFollowingUser ? 0.0 : 1.0,
              child: IgnorePointer(
                ignoring: _cameraFollowingUser,
                child: _buildRecenterButton(),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildScrim() {
    // Vertical gradient — dark at top for status bar readability,
    // dark at bottom to make controls pop, lighter in the middle so
    // the user can see where they're going on the map.
    return IgnorePointer(
      child: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            stops: [0.0, 0.25, 0.55, 1.0],
            colors: [
              Color(0xCC0F1A2E), // top dark
              Color(0x550F1A2E),
              Color(0x330F1A2E),
              Color(0xEE0F1A2E), // bottom dark
            ],
          ),
        ),
      ),
    );
  }

  // ------------------------------------------------------------------
  // MAP — Mapbox
  // The map widget handles its own lifecycle. We set up the annotation
  // managers when onMapCreated fires, then the controller-update
  // listener re-draws the route line whenever new points arrive.
  // ------------------------------------------------------------------

  Widget _buildMap() {
    if (_mapboxPublicToken.startsWith('pk.REPLACE')) {
      // Friendly message if the developer hasn't set a token yet.
      return Container(
        color: _joviNavyDark,
        alignment: Alignment.center,
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Text(
            'Map unavailable — Mapbox token not configured. See SETUP.md §7.',
            style: TextStyle(
              color: _joviGold.withOpacity(0.9),
              fontSize: 13,
              fontWeight: FontWeight.w600,
            ),
            textAlign: TextAlign.center,
          ),
        ),
      );
    }

    // mapbox_maps_flutter requires the token to be set globally before
    // constructing a MapWidget. We do it lazily here — idempotent.
    mb.MapboxOptions.setAccessToken(_mapboxPublicToken);

    return mb.MapWidget(
      key: const ValueKey('jovi_run_map'),
      cameraOptions: mb.CameraOptions(
        center: mb.Point(coordinates: mb.Position(-95.7129, 37.0902)),
        zoom: 15.5,
      ),
      styleUri: 'mapbox://styles/mapbox/outdoors-v12',
      onMapCreated: _onMapCreated,
      onScrollListener: (_) {
        // Any user drag kills follow mode until they hit Recenter.
        if (_cameraFollowingUser) {
          setState(() => _cameraFollowingUser = false);
        }
      },
    );
  }

  Future<void> _onMapCreated(mb.MapboxMap controller) async {
    _mapController = controller;
    try {
      // NOTE: we intentionally do NOT call compass/scaleBar/logo/
      // attribution .updateSettings here — those APIs vary by
      // mapbox_maps_flutter version and are cosmetic. Defaults are
      // fine for v1. If you want to hide the Mapbox logo or compass,
      // the APIs may differ slightly across package versions.

      _routeManager =
          await controller.annotations.createPolylineAnnotationManager();
      _userMarkerManager =
          await controller.annotations.createPointAnnotationManager();

      _mapReady = true;
      // Trigger first sync with current session data.
      await _syncMapToSession();
    } catch (e) {
      _log('map setup error: $e');
    }
  }

  Future<void> _syncMapToSession() async {
    if (!_mapReady) return;
    final session = _ctl.session;
    if (session == null || session.points.isEmpty) return;

    try {
      // Redraw route line if we have new points.
      if (session.points.length != _lastRenderedPointCount) {
        await _redrawRouteLine(session);
        _lastRenderedPointCount = session.points.length;
      }

      // Follow camera to latest point.
      if (_cameraFollowingUser) {
        final last = session.points.last;
        await _mapController?.flyTo(
          mb.CameraOptions(
            center: mb.Point(
              coordinates: mb.Position(last.lng, last.lat),
            ),
            zoom: 16.5,
          ),
          mb.MapAnimationOptions(duration: 500),
        );
      }
    } catch (e) {
      _log('map sync error: $e');
    }
  }

  Future<void> _redrawRouteLine(ActivitySession session) async {
    final mgr = _routeManager;
    if (mgr == null) return;
    // Delete the old polyline and recreate with the updated point
    // list. For v1 this is simple and reliable; a future optimization
    // would be incremental append rather than full redraw.
    if (_routeAnnotation != null) {
      try {
        await mgr.delete(_routeAnnotation!);
      } catch (_) {}
      _routeAnnotation = null;
    }
    if (session.points.length < 2) return;

    final coords = session.points
        .map((p) => mb.Position(p.lng, p.lat))
        .toList(growable: false);
    final line = mb.LineString(coordinates: coords);
    _routeAnnotation = await mgr.create(
      mb.PolylineAnnotationOptions(
        geometry: line,
        lineColor: _joviCoral.value,
        lineWidth: 5.0,
        lineOpacity: 0.95,
      ),
    );
  }

  Widget _buildRecenterButton() {
    return _PressableMaterial(
      child: InkWell(
        onTap: () {
          HapticFeedback.lightImpact();
          setState(() => _cameraFollowingUser = true);
          _syncMapToSession();
        },
        borderRadius: BorderRadius.circular(24),
        child: Container(
          width: 44,
          height: 44,
          decoration: BoxDecoration(
            color: _joviNavy.withOpacity(0.85),
            shape: BoxShape.circle,
            border: Border.all(color: Colors.white.withOpacity(0.2)),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.4),
                blurRadius: 12,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: const Icon(
            Icons.my_location_rounded,
            color: Colors.white,
            size: 22,
          ),
        ),
      ),
    );
  }

  // ------------------------------------------------------------------
  // TOP BAR — activity type pill
  // ------------------------------------------------------------------

  Widget _buildTopBar() {
    final type = _ctl.session?.type ?? ActivityType.run;
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
      child: Row(
        children: [
          _glassCard(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(activityTypeIcon(type), color: _joviCoral, size: 16),
                const SizedBox(width: 6),
                Text(
                  activityTypeLabel(type),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 12.5,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.1,
                  ),
                ),
              ],
            ),
          ),
          const Spacer(),
          // Signal indicator (accuracy dot)
          _glassCard(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                _signalDot(),
                const SizedBox(width: 6),
                Text(
                  'GPS',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.85),
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1.2,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _signalDot() {
    final last = _ctl.session?.points.isNotEmpty == true
        ? _ctl.session!.points.last.accuracyMeters
        : _ctl.lastSeenAccuracyMeters;
    Color dot;
    if (last == null) {
      dot = Colors.white.withOpacity(0.4);
    } else if (last <= 10) {
      dot = _joviMint;
    } else if (last <= 20) {
      dot = _joviGold;
    } else {
      dot = _joviErrorRed;
    }
    return Container(
      width: 8,
      height: 8,
      decoration: BoxDecoration(
        color: dot,
        shape: BoxShape.circle,
        boxShadow: [
          BoxShadow(color: dot.withOpacity(0.6), blurRadius: 5),
        ],
      ),
    );
  }

  // ------------------------------------------------------------------
  // PAUSE BANNER
  // ------------------------------------------------------------------

  Widget _buildPauseBanner() {
    final auto = _ctl.isAutoPaused;
    return Positioned(
      top: 108,
      left: 16,
      right: 16,
      child: SafeArea(
        bottom: false,
        child: _glassCard(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          tint: _joviGold.withOpacity(0.18),
          borderColor: _joviGold.withOpacity(0.5),
          child: Row(
            children: [
              Icon(
                auto ? Icons.pause_circle_outline_rounded : Icons.pause_rounded,
                color: _joviGold,
                size: 20,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  auto ? 'Auto-paused — start moving to resume' : 'Paused',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ------------------------------------------------------------------
  // STATS OVERLAY — primary huge number + 3 secondary stats
  // ------------------------------------------------------------------

  Widget _buildStatsOverlay() {
    final s = _ctl.session;
    final stats = _ctl.stats;
    if (s == null || stats == null) return const SizedBox.shrink();

    final choice = _ctl.settings.primaryStatFor(activityTypeSerialize(s.type));
    final primary = _primaryStatDisplay(choice, stats, s.type);
    final secondaries = _secondaryStatDisplays(choice, stats, s.type);

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        children: [
          _glassCard(
            padding: const EdgeInsets.fromLTRB(18, 14, 18, 16),
            child: Column(
              children: [
                // Primary label
                Text(
                  primary.label,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.65),
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.1,
                  ),
                ),
                const SizedBox(height: 4),
                // Huge value
                FittedBox(
                  fit: BoxFit.scaleDown,
                  child: Text(
                    primary.value,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 72,
                      fontWeight: FontWeight.w700,
                      letterSpacing: -2.5,
                      height: 1.0,
                    ),
                  ),
                ),
                if (primary.unit != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    primary.unit!,
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.6),
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.5,
                    ),
                  ),
                ],
                const SizedBox(height: 14),
                // Separator
                Container(
                  height: 1,
                  color: Colors.white.withOpacity(0.1),
                ),
                const SizedBox(height: 12),
                // Three secondary stats
                Row(
                  children: [
                    for (int i = 0; i < secondaries.length; i++) ...[
                      if (i > 0)
                        Container(
                          width: 1,
                          height: 34,
                          color: Colors.white.withOpacity(0.08),
                        ),
                      Expanded(child: _secondaryTile(secondaries[i])),
                    ],
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          // Splits mini-list (most recent 3)
          _buildRecentSplits(s),
        ],
      ),
    );
  }

  Widget _secondaryTile(_StatDisplay d) {
    return Column(
      children: [
        Text(
          d.label,
          style: TextStyle(
            color: Colors.white.withOpacity(0.65),
            fontSize: 11.5,
            fontWeight: FontWeight.w600,
            letterSpacing: -0.1,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          d.value,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 20,
            fontWeight: FontWeight.w700,
            letterSpacing: -0.5,
          ),
        ),
      ],
    );
  }

  _StatDisplay _primaryStatDisplay(
      PrimaryStatChoice choice, ActivityStats stats, ActivityType type) {
    switch (choice) {
      case PrimaryStatChoice.pace:
        return _StatDisplay(
          label: 'Pace',
          value: stats.currentPaceDisplay,
          unit: '/ mi',
        );
      case PrimaryStatChoice.speed:
        return _StatDisplay(
          label: 'Speed',
          value: stats.currentSpeedDisplay,
          unit: 'mph',
        );
      case PrimaryStatChoice.distance:
        return _StatDisplay(
          label: 'Distance',
          value: metersToMiles(stats.distanceMeters).toStringAsFixed(2),
          unit: 'mi',
        );
      case PrimaryStatChoice.duration:
        return _StatDisplay(
          label: 'Time',
          value: formatDuration(stats.movingTime),
          unit: null,
        );
    }
  }

  List<_StatDisplay> _secondaryStatDisplays(
    PrimaryStatChoice chosen,
    ActivityStats stats,
    ActivityType type,
  ) {
    // Return the 3 stats that AREN'T the primary one.
    final all = <PrimaryStatChoice, _StatDisplay>{
      PrimaryStatChoice.distance: _StatDisplay(
        label: 'Distance',
        value: '${metersToMiles(stats.distanceMeters).toStringAsFixed(2)} mi',
      ),
      PrimaryStatChoice.duration: _StatDisplay(
        label: 'Time',
        value: formatDuration(stats.movingTime),
      ),
      PrimaryStatChoice.pace: _StatDisplay(
        label: type == ActivityType.ride ? 'Avg speed' : 'Avg pace',
        value: type == ActivityType.ride
            ? '${stats.avgSpeedDisplay} mph'
            : '${stats.avgPaceDisplay} /mi',
      ),
      PrimaryStatChoice.speed: _StatDisplay(
        label: 'Avg speed',
        value: '${stats.avgSpeedDisplay} mph',
      ),
    };
    // Remove the primary's corresponding entry. The map trick above
    // over-indexes because `pace` and `speed` share the "speed" slot
    // for secondary — collapse them so we don't show pace twice.
    all.remove(chosen);
    if (chosen == PrimaryStatChoice.pace) {
      all.remove(PrimaryStatChoice.speed);
    } else if (chosen == PrimaryStatChoice.speed) {
      all.remove(PrimaryStatChoice.pace);
    }
    final secondaries = all.values.toList(growable: true);
    // Add an elevation tile on the end since the above only gives us 3
    // candidates.
    secondaries.add(_StatDisplay(
      label: 'Elev',
      value: stats.elevationGainDisplay,
    ));
    // We want exactly 3 secondary stats. Take the first 3.
    return secondaries.take(3).toList();
  }

  // ------------------------------------------------------------------
  // RECENT SPLITS MINI-LIST
  // ------------------------------------------------------------------

  Widget _buildRecentSplits(ActivitySession s) {
    if (s.splits.isEmpty) {
      return const SizedBox.shrink();
    }
    // Show the most recent 3 splits.
    final recent =
        s.splits.length <= 3 ? s.splits : s.splits.sublist(s.splits.length - 3);
    return _glassCard(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            s.type == ActivityType.ride ? 'Recent 5-mile splits' : 'Recent splits',
            style: TextStyle(
              color: Colors.white.withOpacity(0.65),
              fontSize: 12,
              fontWeight: FontWeight.w600,
              letterSpacing: -0.1,
            ),
          ),
          const SizedBox(height: 6),
          ...recent.map((sp) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Row(
                  children: [
                    SizedBox(
                      width: 38,
                      child: Text(
                        '${sp.index + 1}',
                        style: const TextStyle(
                          color: _joviCoral,
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    Expanded(
                      child: Text(
                        s.type == ActivityType.ride
                            ? '${mpsToMph(sp.avgSpeedMps).toStringAsFixed(1)} mph'
                            : '${sp.paceMinPerMile} /mi',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    Text(
                      formatDuration(sp.duration),
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.6),
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        fontFeatures: const [FontFeature.tabularFigures()],
                      ),
                    ),
                  ],
                ),
              )),
        ],
      ),
    );
  }

  // ------------------------------------------------------------------
  // CONTROLS — Pause (single tap) + Stop (long-press to confirm)
  // ------------------------------------------------------------------

  Widget _buildControls() {
    return Row(
      children: [
        // PAUSE / RESUME — single tap, coral
        Expanded(
          flex: 1,
          child: _primaryControlButton(
            label: _ctl.isPaused ? 'Resume' : 'Pause',
            icon:
                _ctl.isPaused ? Icons.play_arrow_rounded : Icons.pause_rounded,
            color: _ctl.isPaused ? _joviMint : _joviCoral,
            onTap: () {
              HapticFeedback.mediumImpact();
              if (_ctl.isPaused) {
                _ctl.resume();
              } else {
                _ctl.pause();
              }
            },
          ),
        ),
        const SizedBox(width: 12),
        // STOP — long-press only, red
        Expanded(
          flex: 1,
          child: _StopButton(
            onLongPressComplete: () async {
              HapticFeedback.heavyImpact();
              await _ctl.stop();
            },
          ),
        ),
      ],
    );
  }

  Widget _primaryControlButton({
    required String label,
    required IconData icon,
    required Color color,
    required VoidCallback onTap,
  }) {
    return _PressableMaterial(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(18),
        child: Container(
          height: 70,
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [color, color.withOpacity(0.85)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(18),
            boxShadow: [
              BoxShadow(
                color: color.withOpacity(0.45),
                blurRadius: 16,
                offset: const Offset(0, 6),
              ),
            ],
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, color: Colors.white, size: 26),
              const SizedBox(width: 6),
              Text(
                label,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 17,
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.2,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ------------------------------------------------------------------
  // GLASS CARD HELPER
  // ------------------------------------------------------------------

  Widget _glassCard({
    required Widget child,
    EdgeInsets padding = const EdgeInsets.all(14),
    Color? tint,
    Color? borderColor,
  }) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(14),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 14, sigmaY: 14),
        child: Container(
          padding: padding,
          decoration: BoxDecoration(
            color: tint ?? Colors.white.withOpacity(0.07),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: borderColor ?? Colors.white.withOpacity(0.12),
              width: 1,
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.2),
                blurRadius: 12,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: child,
        ),
      ),
    );
  }
}

// =======================================================================
// STAT DISPLAY VALUE CLASS
// =======================================================================

class _StatDisplay {
  final String label;
  final String value;
  final String? unit;
  const _StatDisplay({required this.label, required this.value, this.unit});
}

// =======================================================================
// STOP BUTTON (long-press)
//
// Tapping does nothing — user must hold for ~1 second. A fill
// animation gives visual feedback about progress. Matches the pattern
// in most running apps (Strava, Nike Run Club) — prevents pocket-stops.
// =======================================================================

class _StopButton extends StatefulWidget {
  final Future<void> Function() onLongPressComplete;
  const _StopButton({Key? key, required this.onLongPressComplete})
      : super(key: key);

  @override
  State<_StopButton> createState() => _StopButtonState();
}

class _StopButtonState extends State<_StopButton>
    with SingleTickerProviderStateMixin {
  static const Duration _holdDuration = Duration(milliseconds: 1000);
  late final AnimationController _fillController;
  bool _pressing = false;

  @override
  void initState() {
    super.initState();
    _fillController = AnimationController(
      vsync: this,
      duration: _holdDuration,
    )..addStatusListener((status) async {
        if (status == AnimationStatus.completed) {
          // Reached 100% fill — trigger the stop.
          if (_pressing && mounted) {
            await widget.onLongPressComplete();
          }
        }
      });
  }

  @override
  void dispose() {
    _fillController.dispose();
    super.dispose();
  }

  void _onTapDown(_) {
    setState(() => _pressing = true);
    _fillController.forward();
    HapticFeedback.selectionClick();
  }

  void _onTapUp(_) {
    setState(() => _pressing = false);
    _fillController.reverse();
  }

  void _onTapCancel() {
    setState(() => _pressing = false);
    _fillController.reverse();
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: _onTapDown,
      onTapUp: _onTapUp,
      onTapCancel: _onTapCancel,
      onTap: () {
        // Tell the user what's expected on a plain tap.
        HapticFeedback.lightImpact();
        ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(
            'Hold Stop to finish your activity',
            accent: Colors.white70,
            icon: CupertinoIcons.hand_raised,
            duration: const Duration(seconds: 2)));
      },
      child: AnimatedBuilder(
        animation: _fillController,
        builder: (context, child) {
          return Container(
            height: 70,
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.06),
              borderRadius: BorderRadius.circular(18),
              border: Border.all(
                color: _joviErrorRed.withOpacity(0.7),
                width: 1.5,
              ),
              boxShadow: [
                BoxShadow(
                  color: _joviErrorRed.withOpacity(0.2),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(16),
              child: Stack(
                children: [
                  // Fill overlay — grows from left to right as the
                  // user holds.
                  FractionallySizedBox(
                    alignment: Alignment.centerLeft,
                    widthFactor: _fillController.value,
                    child: Container(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: [
                            _joviErrorRed,
                            _joviErrorRed.withOpacity(0.7),
                          ],
                        ),
                      ),
                    ),
                  ),
                  // Label
                  Center(
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.stop_rounded,
                          color: _fillController.value > 0.15
                              ? Colors.white
                              : _joviErrorRed,
                          size: 26,
                        ),
                        const SizedBox(width: 6),
                        Text(
                          _pressing ? 'Hold…' : 'Stop',
                          style: TextStyle(
                            color: _fillController.value > 0.15
                                ? Colors.white
                                : _joviErrorRed,
                            fontSize: 17,
                            fontWeight: FontWeight.w700,
                            letterSpacing: -0.2,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}

// =======================================================================
// ACQUIRING PULSE WIDGET
//
// The animated "searching for GPS" icon shown on the acquisition
// splash. Two concentric rings that pulse outward.
// =======================================================================

class _AcquiringPulse extends StatefulWidget {
  final IconData icon;
  const _AcquiringPulse({required this.icon});

  @override
  State<_AcquiringPulse> createState() => _AcquiringPulseState();
}

class _AcquiringPulseState extends State<_AcquiringPulse>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );
    if (_platformReduceMotion()) {
      _ctrl.value = 0.3;
    } else {
      _ctrl.repeat();
    }
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 180,
      height: 180,
      child: Stack(
        alignment: Alignment.center,
        children: [
          AnimatedBuilder(
            animation: _ctrl,
            builder: (context, _) {
              return Stack(
                alignment: Alignment.center,
                children: [
                  _ring(80 + _ctrl.value * 70, 1 - _ctrl.value),
                  _ring(
                    80 + ((_ctrl.value + 0.5) % 1.0) * 70,
                    1 - ((_ctrl.value + 0.5) % 1.0),
                  ),
                ],
              );
            },
          ),
          Container(
            width: 78,
            height: 78,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: LinearGradient(
                colors: [
                  _joviCoral.withOpacity(0.35),
                  _joviCoralLight.withOpacity(0.15),
                ],
              ),
              border: Border.all(
                color: _joviCoral.withOpacity(0.5),
                width: 1.2,
              ),
            ),
            child: Icon(widget.icon, color: Colors.white, size: 38),
          ),
        ],
      ),
    );
  }

  Widget _ring(double size, double opacity) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        border: Border.all(
          color: _joviCoral.withOpacity(opacity.clamp(0.0, 0.5)),
          width: 2,
        ),
      ),
    );
  }
}
