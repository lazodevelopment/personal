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
// JOVI HEALTH — RUN HISTORY + DETAIL (SELF-CONTAINED)
// Version: 2026.04.22-s4 (r1: added JoviRunHistoryList.openDetail static
//          helper for cross-file snackbar navigation. No type deps on
//          any other custom-code file — history is fully self-contained
//          and communicates with fitness_home only through Firestore.)
// r2 (2026.09.22): Apple HIG pass — press feedback, painted glass rows,
//          Cupertino delete confirms, navy toasts, title-case labels.
// r3 (2026.09.22): post-run summary mode (justFinished) opened from Stop.
// Build: JC-RUNHISTORY-0922-003
//
// Widget Name (for FF): JoviRunHistoryList
//
// Companion to jovi_run_engine.dart (Session 1), jovi_run_services.dart
// and jovi_run_active.dart (Session 2). This file holds:
//
//   1. RunHistoryList — paginated list of past activities, grouped
//      into week buckets ("This week", "Last week", "Two weeks ago",
//      then by month). Swipe left on a row to delete. Tap a row to
//      open the detail screen. Filter chips at top (All / Run /
//      Walk / Ride).
//
//   2. RunDetailScreen — full detail view for one activity:
//        - Header: type + date + hero stats (distance, time)
//        - Map: route on Mapbox with start/end markers, auto-fit
//          camera to the bounding box
//        - Stats grid: avg pace, avg speed, elevation, moving time,
//          point count
//        - Splits table: per-mile or per-5-mi rows
//        - Notes field: editable, autosaves on blur
//        - Delete button: confirms, deletes summary doc AND points
//          subcollection
//
// DATA:
//   Reads from users/{uid}/activities (summary docs). Query is
//   filtered to status=='completed' — discarded runs never show up.
//   Ordered by startedAt DESC, paginated at 20 docs per page.
//
//   Detail screen additionally reads the points subcollection on
//   demand for the route line.
//
// DESIGN:
//   Navy + glass consistent with every other Jovi widget. Coral
//   accents, white-at-7% fill glass cards, BackdropFilter blur 12-16.
//
// REQUIRED PUB DEPS (all already added in SETUP.md §6):
//   - mapbox_maps_flutter ^2.3.0 (detail screen route display)
//   - cloud_firestore (already in project)
//
// NAVIGATION:
//   Entry point is the 'History' tab on RunFitnessHome. Row tap →
//   Navigator.push(RunDetailScreen(activityId: ...)).
// =======================================================================

import 'dart:async';
import 'dart:ui';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';
import 'package:mapbox_maps_flutter/mapbox_maps_flutter.dart' as mb;

// =======================================================================
// PRIMARY WIDGET — declared FIRST so FlutterFlow's "Widget Name" field
// matches it. Public proxy that forwards callbacks to the full
// implementation further down in this file. This is what the
// tabbed RunFitnessHome wraps in its History tab.
// =======================================================================

// Mapbox token — keep in sync with jovi_run_active.dart. If you
// change one, change the other. (Same global access token, just
// referenced from two files.)
const String _mapboxPublicToken =
    'pk.eyJ1Ijoiam92aWhlYWx0aCIsImEiOiJjbW9hYzk5cDAwNTlhMnhwd3V5a2ZxeHh6In0.Ke708anyClWtZlo75KEMag';

// Brand palette (local copy — FF files are own compile units).
const Color _joviCoral = Color(0xFFFF6B4A);
const Color _joviCoralLight = Color(0xFFFF8F73);
const Color _joviCoralDark = Color(0xFFE5583A);
const Color _joviNavy = Color(0xFF1A2744);
const Color _joviNavyDark = Color(0xFF0F1A2E);
const Color _joviNavyMid = Color(0xFF1F2B47);
const Color _joviMint = Color(0xFF00D4AA);
const Color _joviGold = Color(0xFFFFD166);
const Color _joviErrorRed = Color(0xFFE53935);

// Same conversion constants as the engine, local copy.
const double _metersPerMile = 1609.344;
const double _mphPerMps = 2.23694;

void _log(String msg) {
  // ignore: avoid_print
  if (kDebugMode) debugPrint('[RunHistory] $msg');
}

void _logError(String msg, Object? err, [StackTrace? st]) {
  // ignore: avoid_print
  if (kDebugMode) {
    debugPrint('[RunHistory][ERROR] $msg: $err');
    if (st != null) debugPrint('$st');
  }
}

// =======================================================================
// GLASS CARD HELPER
// Same treatment used across all Jovi widgets — white@7% fill,
// BackdropFilter blur, white@12% border, subtle shadow.
// =======================================================================

Widget _glassCard({
  required Widget child,
  EdgeInsets padding = const EdgeInsets.all(14),
  double borderRadius = 14,
  Color? tint,
  Color? borderColor,
  VoidCallback? onTap,
}) {
  // Painted glass: rows live in a scrolling list over an opaque navy
  // gradient, where a live blur is pure GPU cost.
  final content = ClipRRect(
    borderRadius: BorderRadius.circular(borderRadius),
    child: RepaintBoundary(
      child: Container(
        padding: padding,
        decoration: BoxDecoration(
          color: tint ?? Colors.white.withOpacity(0.09),
          borderRadius: BorderRadius.circular(borderRadius),
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
  if (onTap == null) return content;
  return _PressableMaterial(
    child: InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(borderRadius),
      child: content,
    ),
  );
}

// =======================================================================
// HISTORY ROW MODEL
// Lightweight summary read directly from activities collection. We
// don't reuse the engine's ActivitySession model here because we
// don't need the full point list + state machine — this is a
// read-only view.
// =======================================================================

class _HistoryRow {
  final String id;
  final String type; // "run" | "walk" | "ride"
  final DateTime startedAt;
  final DateTime? endedAt;
  final double distanceMeters;
  final int movingSeconds;
  final double? avgSpeedMps;
  final double elevationGainMeters;
  final int pointCount;

  const _HistoryRow({
    required this.id,
    required this.type,
    required this.startedAt,
    this.endedAt,
    required this.distanceMeters,
    required this.movingSeconds,
    this.avgSpeedMps,
    required this.elevationGainMeters,
    required this.pointCount,
  });

  factory _HistoryRow.fromFirestore(String id, Map<String, dynamic> m) {
    return _HistoryRow(
      id: id,
      type: (m['type'] as String?) ?? 'run',
      startedAt: (m['startedAt'] as Timestamp).toDate(),
      endedAt: (m['endedAt'] as Timestamp?)?.toDate(),
      distanceMeters: (m['distanceMeters'] as num?)?.toDouble() ?? 0,
      movingSeconds: (m['movingSeconds'] as num?)?.toInt() ?? 0,
      avgSpeedMps: (m['avgSpeedMetersPerSecond'] as num?)?.toDouble(),
      elevationGainMeters: (m['elevationGainMeters'] as num?)?.toDouble() ?? 0,
      pointCount: (m['pointCount'] as num?)?.toInt() ?? 0,
    );
  }
}

String _activityIconName(String type) {
  // Just a key string — _activityIcon() maps to an IconData.
  switch (type) {
    case 'walk':
      return 'walk';
    case 'ride':
      return 'ride';
    case 'run':
    default:
      return 'run';
  }
}

IconData _activityIcon(String type) {
  switch (type) {
    case 'walk':
      return Icons.directions_walk_rounded;
    case 'ride':
      return Icons.directions_bike_rounded;
    case 'run':
    default:
      return Icons.directions_run_rounded;
  }
}

String _activityLabel(String type) {
  switch (type) {
    case 'walk':
      return 'Walk';
    case 'ride':
      return 'Ride';
    case 'run':
    default:
      return 'Run';
  }
}

// =======================================================================
// FORMAT HELPERS
// Duplicate the engine's formatters here to keep this file self-
// contained. Same math + output as jovi_run_engine.dart.
// =======================================================================

String _fmtDistanceMi(double meters) {
  return '${(meters / _metersPerMile).toStringAsFixed(2)} mi';
}

String _fmtDurationHMS(int totalSeconds) {
  final h = totalSeconds ~/ 3600;
  final m = (totalSeconds % 3600) ~/ 60;
  final s = totalSeconds % 60;
  if (h > 0) {
    return '$h:${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
  }
  return '${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
}

String _fmtDurationShort(int totalSeconds) {
  final h = totalSeconds ~/ 3600;
  final m = (totalSeconds % 3600) ~/ 60;
  if (h > 0) return '${h}h ${m}m';
  return '${m}m';
}

String _fmtPaceMinPerMile(double? speedMps) {
  if (speedMps == null || speedMps < 0.1) return '--:--';
  final secPerMile = _metersPerMile / speedMps;
  final mins = secPerMile ~/ 60;
  final secs = (secPerMile % 60).round();
  return '$mins:${secs.toString().padLeft(2, '0')}';
}

String _fmtSpeedMph(double? speedMps) {
  if (speedMps == null || speedMps < 0) return '--';
  return (speedMps * _mphPerMps).toStringAsFixed(1);
}

String _fmtElevationFt(double meters) {
  return '${(meters * 3.28084).round()} ft';
}

/// Friendly relative date label for row dates. "Today", "Yesterday",
/// then weekday for the past week, then date-with-year for older.
String _fmtRowDate(DateTime d) {
  final now = DateTime.now();
  final today = DateTime(now.year, now.month, now.day);
  final that = DateTime(d.year, d.month, d.day);
  final diff = today.difference(that).inDays;

  const weekdays = [
    'Mon',
    'Tue',
    'Wed',
    'Thu',
    'Fri',
    'Sat',
    'Sun',
  ];
  const months = [
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec',
  ];
  final hour12 = d.hour == 0 ? 12 : (d.hour > 12 ? d.hour - 12 : d.hour);
  final ampm = d.hour < 12 ? 'AM' : 'PM';
  final time = '$hour12:${d.minute.toString().padLeft(2, '0')} $ampm';

  if (diff == 0) return 'Today · $time';
  if (diff == 1) return 'Yesterday · $time';
  if (diff < 7) return '${weekdays[d.weekday - 1]} · $time';
  if (d.year == now.year) {
    return '${weekdays[d.weekday - 1]}, ${months[d.month - 1]} ${d.day}';
  }
  return '${months[d.month - 1]} ${d.day}, ${d.year}';
}

// =======================================================================
// WEEK BUCKET GROUPING
//
// Groups a chronologically-sorted list of rows into labeled buckets:
//   "This week", "Last week", "Two weeks ago", "Three weeks ago",
//   then by month ("April 2026", "March 2026", etc).
//
// "Week" is defined as Mon-Sun. An activity done on Sunday evening
// belongs to that week, not the next week.
// =======================================================================

class _Bucket {
  final String label;
  final List<_HistoryRow> rows;
  _Bucket(this.label) : rows = <_HistoryRow>[];
}

List<_Bucket> _bucketize(List<_HistoryRow> rows) {
  final buckets = <_Bucket>[];
  final now = DateTime.now();

  // Compute the Monday 00:00 for the week of reference day `d`.
  DateTime mondayOf(DateTime d) {
    final day = DateTime(d.year, d.month, d.day);
    final weekday = day.weekday; // Monday=1 ... Sunday=7
    return day.subtract(Duration(days: weekday - 1));
  }

  final thisMonday = mondayOf(now);
  final lastMonday = thisMonday.subtract(const Duration(days: 7));
  final twoMondays = thisMonday.subtract(const Duration(days: 14));
  final threeMondays = thisMonday.subtract(const Duration(days: 21));
  final fourMondays = thisMonday.subtract(const Duration(days: 28));

  final thisWeek = _Bucket('This week');
  final lastWeek = _Bucket('Last week');
  final twoWeeks = _Bucket('Two weeks ago');
  final threeWeeks = _Bucket('Three weeks ago');
  // Month buckets are created lazily keyed by "YYYY-MM".
  final monthBuckets = <String, _Bucket>{};

  const months = [
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
  ];

  for (final r in rows) {
    final start = r.startedAt;
    if (!start.isBefore(thisMonday)) {
      thisWeek.rows.add(r);
    } else if (!start.isBefore(lastMonday)) {
      lastWeek.rows.add(r);
    } else if (!start.isBefore(twoMondays)) {
      twoWeeks.rows.add(r);
    } else if (!start.isBefore(threeMondays)) {
      threeWeeks.rows.add(r);
    } else if (!start.isBefore(fourMondays)) {
      // Don't create a separate "four weeks ago" — collapse into the
      // month it's in, matching spec.
      final key = '${start.year}-${start.month.toString().padLeft(2, "0")}';
      final label = '${months[start.month - 1]} ${start.year}';
      monthBuckets.putIfAbsent(key, () => _Bucket(label)).rows.add(r);
    } else {
      final key = '${start.year}-${start.month.toString().padLeft(2, "0")}';
      final label = '${months[start.month - 1]} ${start.year}';
      monthBuckets.putIfAbsent(key, () => _Bucket(label)).rows.add(r);
    }
  }

  for (final b in [thisWeek, lastWeek, twoWeeks, threeWeeks]) {
    if (b.rows.isNotEmpty) buckets.add(b);
  }
  // Month buckets in reverse-chron order.
  final monthKeys = monthBuckets.keys.toList()..sort((a, b) => b.compareTo(a));
  for (final k in monthKeys) {
    buckets.add(monthBuckets[k]!);
  }
  return buckets;
}

// =======================================================================
// RUN HISTORY LIST
//
// Paginated list of past activities. Visible as the "History" tab
// inside RunFitnessHome — NOT typically used as a standalone page.
// (It can be placed standalone if you want a dedicated history page,
// but the tabbed version is the intended UX.)
//
// QUERY:
//   users/{uid}/activities
//     .where('status', isEqualTo: 'completed')
//     .where('type', isEqualTo: <filter>) // optional
//     .orderBy('startedAt', descending: true)
//     .limit(20)                           // page 1
//     .startAfterDocument(lastDoc)         // page 2+
//
// SWIPE TO DELETE:
//   Dismissible with a DismissDirection.endToStart → shows a red
//   "Delete" background as the row animates left. Confirm dialog
//   before actually deleting. Delete removes the summary doc AND
//   batches through the points subcollection.
//
// EMPTY STATE:
//   Friendly "No activities yet" with an illustration placeholder
//   and a Start button. Calls widget.onStartTapped, which the
//   parent RunFitnessHome uses to switch tabs back to Start.
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

class JoviRunHistoryList extends StatefulWidget {
  const JoviRunHistoryList({
    Key? key,
    this.width,
    this.height,
  }) : super(key: key);

  final double? width;
  final double? height;

  // Static callback slots so we don't expose function-typed params to
  // FlutterFlow's parameter panel (FF can't infer those types and blocks
  // save). The parent widget (JoviRunFitnessHome) sets these BEFORE
  // building JoviRunHistoryList, and clears them in dispose.
  //
  // Both are optional. If left null:
  //   - onRowRequested → tap opens RunDetailScreen via Navigator.push
  //   - onStartRequested → empty-state Start button calls Navigator.maybePop
  //
  // These are intentionally static (not instance) because FF parameter
  // inference walks the constructor/field list; keeping them off the
  // class surface entirely is the cleanest way to stay invisible to it.
  static void Function(String activityId)? onRowRequested;
  static void Function()? onStartRequested;

  /// Cross-file helper for pushing the RunDetailScreen. Used by
  /// jovi_run_fitness_home.dart's post-run "VIEW" snackbar action
  /// since RunDetailScreen is a non-widget class that can't be
  /// referenced across FF compile units directly — but static
  /// methods on a widget class CAN be accessed across files via
  /// the FF widgets barrel.
  ///
  /// Pushes via Navigator.of(context).push with a MaterialPageRoute.
  /// If the caller needs root-level push behavior (e.g. after the
  /// previous route has already popped), they should pass a root
  /// navigator context.
  static Future<void> openDetail(BuildContext context, String activityId,
      {bool justFinished = false}) {
    return Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => RunDetailScreen(
          activityId: activityId,
          justFinished: justFinished,
        ),
        fullscreenDialog: justFinished,
      ),
    );
  }

  @override
  State<JoviRunHistoryList> createState() => _JoviRunHistoryListState();
}

class _JoviRunHistoryListState extends State<JoviRunHistoryList> {
  static const int _pageSize = 20;

  final ScrollController _scrollCtrl = ScrollController();
  final List<_HistoryRow> _rows = [];
  final Set<String> _seenIds = <String>{}; // dedupe across pages
  DocumentSnapshot<Map<String, dynamic>>? _lastDoc;
  bool _loading = false;
  bool _reachedEnd = false;
  String? _error;
  String _filter = 'all'; // 'all' | 'run' | 'walk' | 'ride'

  @override
  void initState() {
    super.initState();
    _scrollCtrl.addListener(_onScroll);
    _loadPage(reset: true);
  }

  @override
  void dispose() {
    _scrollCtrl.removeListener(_onScroll);
    _scrollCtrl.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollCtrl.position.pixels >=
        _scrollCtrl.position.maxScrollExtent - 200) {
      if (!_loading && !_reachedEnd) {
        _loadPage();
      }
    }
  }

  Future<void> _refresh() async {
    await _loadPage(reset: true);
  }

  Future<void> _loadPage({bool reset = false}) async {
    if (_loading) return;
    final uid = FirebaseAuth.instance.currentUser?.uid;
    if (uid == null) {
      setState(() => _error = 'Sign in to see your history.');
      return;
    }
    setState(() {
      _loading = true;
      if (reset) {
        _error = null;
        _rows.clear();
        _seenIds.clear();
        _lastDoc = null;
        _reachedEnd = false;
      }
    });

    try {
      Query<Map<String, dynamic>> q = FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('activities')
          .where('status', isEqualTo: 'completed');
      if (_filter != 'all') {
        q = q.where('type', isEqualTo: _filter);
      }
      q = q.orderBy('startedAt', descending: true).limit(_pageSize);
      if (_lastDoc != null) {
        q = q.startAfterDocument(_lastDoc!);
      }
      final snap = await q.get();
      final newRows = <_HistoryRow>[];
      for (final doc in snap.docs) {
        if (_seenIds.contains(doc.id)) continue;
        try {
          newRows.add(_HistoryRow.fromFirestore(doc.id, doc.data()));
          _seenIds.add(doc.id);
        } catch (e, st) {
          _logError('skipped malformed activity ${doc.id}', e, st);
        }
      }
      setState(() {
        _rows.addAll(newRows);
        if (snap.docs.isNotEmpty) {
          _lastDoc = snap.docs.last;
        }
        if (snap.docs.length < _pageSize) {
          _reachedEnd = true;
        }
        _loading = false;
      });
    } catch (e, st) {
      _logError('history load failed', e, st);
      setState(() {
        _loading = false;
        _error = 'Could not load history. Pull to refresh.';
      });
    }
  }

  Future<void> _onFilterChanged(String next) async {
    if (_filter == next) return;
    setState(() => _filter = next);
    HapticFeedback.selectionClick();
    await _loadPage(reset: true);
  }

  Future<bool> _confirmDelete(_HistoryRow r) async {
    final confirmed = await showCupertinoDialog<bool>(
      context: context,
      builder: (ctx) => CupertinoAlertDialog(
        title: const Text('Delete This Activity?'),
        content: Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Text(
            'This will permanently delete the '
            '${_activityLabel(r.type).toLowerCase()} on '
            '${_fmtRowDate(r.startedAt)}. This cannot be undone.',
          ),
        ),
        actions: [
          CupertinoDialogAction(
            isDefaultAction: true,
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Keep'),
          ),
          CupertinoDialogAction(
            isDestructiveAction: true,
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    return confirmed == true;
  }

  Future<void> _deleteActivity(_HistoryRow r) async {
    final uid = FirebaseAuth.instance.currentUser?.uid;
    if (uid == null) return;
    final docRef = FirebaseFirestore.instance
        .collection('users')
        .doc(uid)
        .collection('activities')
        .doc(r.id);

    try {
      // Delete points subcollection in batches. Firestore doesn't
      // cascade, so we have to handle this explicitly.
      await _deletePointsSubcollection(docRef);
      await docRef.delete();
      _log('deleted activity ${r.id}');

      if (mounted) {
        ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(
            'Activity deleted',
            accent: _joviMint,
            icon: CupertinoIcons.checkmark_circle,
            duration: const Duration(seconds: 2)));
      }
    } catch (e, st) {
      _logError('delete failed', e, st);
      if (mounted) {
        ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(
            'Could not delete. Try again.',
            accent: _joviErrorRed,
            icon: CupertinoIcons.exclamationmark_circle));
      }
      // Put the row back on failure.
      if (mounted) {
        setState(() {
          _rows.add(r);
          _rows.sort((a, b) => b.startedAt.compareTo(a.startedAt));
          _seenIds.add(r.id);
        });
      }
    }
  }

  Future<void> _deletePointsSubcollection(
    DocumentReference<Map<String, dynamic>> activityRef,
  ) async {
    // Firestore batch limit is 500. Most runs will have < 3000
    // points so this loop terminates quickly.
    const batchSize = 450;
    while (true) {
      final snap =
          await activityRef.collection('points').limit(batchSize).get();
      if (snap.docs.isEmpty) break;
      final batch = FirebaseFirestore.instance.batch();
      for (final d in snap.docs) {
        batch.delete(d.reference);
      }
      await batch.commit();
      if (snap.docs.length < batchSize) break;
    }
  }

  void _openDetail(_HistoryRow r) {
    final cb = JoviRunHistoryList.onRowRequested;
    if (cb != null) {
      cb(r.id);
      return;
    }
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => RunDetailScreen(activityId: r.id),
        fullscreenDialog: false,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [_joviNavy, _joviNavyDark, _joviNavyDark],
          stops: [0.0, 0.5, 1.0],
        ),
      ),
      child: RefreshIndicator(
        color: _joviCoral,
        backgroundColor: _joviNavy,
        onRefresh: _refresh,
        child: CustomScrollView(
          controller: _scrollCtrl,
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            SliverToBoxAdapter(child: _buildFilterChips()),
            if (_error != null)
              SliverToBoxAdapter(child: _buildErrorCard())
            else if (_rows.isEmpty && !_loading)
              SliverFillRemaining(
                hasScrollBody: false,
                child: _buildEmptyState(),
              )
            else
              ..._buildBucketedContent(),
            if (_loading && _rows.isEmpty)
              SliverFillRemaining(
                hasScrollBody: false,
                child: _buildLoadingState(),
              ),
            if (_loading && _rows.isNotEmpty)
              const SliverToBoxAdapter(child: _PaginationSpinner()),
            const SliverToBoxAdapter(child: SizedBox(height: 24)),
          ],
        ),
      ),
    );
  }

  Widget _buildFilterChips() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 6),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 2),
        child: Row(
          children: [
            _filterChip('all', 'All'),
            const SizedBox(width: 8),
            _filterChip('run', 'Runs'),
            const SizedBox(width: 8),
            _filterChip('walk', 'Walks'),
            const SizedBox(width: 8),
            _filterChip('ride', 'Rides'),
          ],
        ),
      ),
    );
  }

  Widget _filterChip(String value, String label) {
    final selected = _filter == value;
    return _PressableMaterial(
      child: InkWell(
        onTap: () => _onFilterChanged(value),
        borderRadius: BorderRadius.circular(20),
        child: AnimatedContainer(
          duration: _Motion.select,
          curve: _Motion.settle,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          decoration: BoxDecoration(
            gradient: selected
                ? const LinearGradient(
                    colors: [_joviCoral, _joviCoralLight],
                  )
                : null,
            color: selected ? null : Colors.white.withOpacity(0.06),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: selected
                  ? _joviCoral.withOpacity(0.6)
                  : Colors.white.withOpacity(0.12),
            ),
            boxShadow: selected
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
              color: selected ? Colors.white : Colors.white.withOpacity(0.7),
              fontSize: 13,
              fontWeight: FontWeight.w800,
              letterSpacing: 0.3,
            ),
          ),
        ),
      ),
    );
  }

  List<Widget> _buildBucketedContent() {
    final buckets = _bucketize(_rows);
    final widgets = <Widget>[];
    for (final b in buckets) {
      widgets.add(SliverToBoxAdapter(child: _buildBucketHeader(b)));
      widgets.add(
        SliverList(
          delegate: SliverChildBuilderDelegate(
            (ctx, i) {
              final row = b.rows[i];
              return Padding(
                padding: const EdgeInsets.fromLTRB(14, 0, 14, 10),
                child: _buildRowSwipeable(row),
              );
            },
            childCount: b.rows.length,
          ),
        ),
      );
    }
    return widgets;
  }

  Widget _buildBucketHeader(_Bucket b) {
    final totalMeters =
        b.rows.fold<double>(0, (sum, r) => sum + r.distanceMeters);
    final totalSeconds = b.rows.fold<int>(0, (sum, r) => sum + r.movingSeconds);
    return Padding(
      padding: const EdgeInsets.fromLTRB(18, 16, 18, 10),
      child: Row(
        children: [
          Container(
            width: 3,
            height: 16,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [_joviCoral, _joviCoralLight],
              ),
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(width: 10),
          Text(
            b.label,
            style: TextStyle(
              color: Colors.white.withOpacity(0.7),
              fontSize: 13,
              fontWeight: FontWeight.w600,
              letterSpacing: -0.1,
            ),
          ),
          const Spacer(),
          Text(
            '${_fmtDistanceMi(totalMeters)} · ${_fmtDurationShort(totalSeconds)}',
            style: TextStyle(
              color: Colors.white.withOpacity(0.5),
              fontSize: 11.5,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.2,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRowSwipeable(_HistoryRow r) {
    return Dismissible(
      key: ValueKey('activity_${r.id}'),
      direction: DismissDirection.endToStart,
      background: Container(
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.symmetric(horizontal: 22),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              _joviErrorRed.withOpacity(0.8),
              _joviErrorRed,
            ],
            begin: Alignment.centerLeft,
            end: Alignment.centerRight,
          ),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: const [
            Icon(Icons.delete_outline_rounded, color: Colors.white, size: 22),
            SizedBox(width: 8),
            Text(
              'Delete',
              style: TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w800,
                fontSize: 14,
                letterSpacing: 0.3,
              ),
            ),
          ],
        ),
      ),
      confirmDismiss: (_) async {
        final ok = await _confirmDelete(r);
        return ok;
      },
      onDismissed: (_) {
        setState(() {
          _rows.removeWhere((x) => x.id == r.id);
          _seenIds.remove(r.id);
        });
        // Actual delete happens async after the dismiss animation.
        unawaited(_deleteActivity(r));
      },
      child: _buildRow(r),
    );
  }

  Widget _buildRow(_HistoryRow r) {
    final isRide = r.type == 'ride';
    return _glassCard(
      padding: const EdgeInsets.all(14),
      borderRadius: 16,
      onTap: () => _openDetail(r),
      child: Row(
        children: [
          Container(
            width: 52,
            height: 52,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  _joviCoral.withOpacity(0.3),
                  _joviCoralLight.withOpacity(0.13),
                ],
              ),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                color: _joviCoral.withOpacity(0.4),
                width: 0.8,
              ),
            ),
            child: Icon(
              _activityIcon(r.type),
              color: Colors.white,
              size: 26,
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  _activityLabel(r.type),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.2,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  _fmtRowDate(r.startedAt),
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.55),
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    _miniStat(
                      _fmtDistanceMi(r.distanceMeters),
                      Icons.straighten_rounded,
                    ),
                    const SizedBox(width: 12),
                    _miniStat(
                      _fmtDurationShort(r.movingSeconds),
                      Icons.timer_outlined,
                    ),
                    const SizedBox(width: 12),
                    _miniStat(
                      isRide
                          ? '${_fmtSpeedMph(r.avgSpeedMps)} mph'
                          : '${_fmtPaceMinPerMile(r.avgSpeedMps)} /mi',
                      isRide ? Icons.speed_rounded : Icons.timer_rounded,
                    ),
                  ],
                ),
              ],
            ),
          ),
          Icon(
            Icons.chevron_right_rounded,
            color: Colors.white.withOpacity(0.3),
            size: 22,
          ),
        ],
      ),
    );
  }

  Widget _miniStat(String value, IconData icon) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, color: _joviCoral, size: 12),
        const SizedBox(width: 4),
        Text(
          value,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 12.5,
            fontWeight: FontWeight.w800,
            letterSpacing: 0.1,
          ),
        ),
      ],
    );
  }

  Widget _buildEmptyState() {
    return Padding(
      padding: const EdgeInsets.all(32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 88,
            height: 88,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: LinearGradient(
                colors: [
                  _joviCoral.withOpacity(0.2),
                  _joviCoralLight.withOpacity(0.08),
                ],
              ),
              border: Border.all(
                color: _joviCoral.withOpacity(0.35),
                width: 1.2,
              ),
            ),
            child: const Icon(
              Icons.directions_run_rounded,
              color: Colors.white,
              size: 40,
            ),
          ),
          const SizedBox(height: 20),
          const Text(
            'No activities yet',
            style: TextStyle(
              color: Colors.white,
              fontSize: 20,
              fontWeight: FontWeight.w700,
              letterSpacing: -0.3,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            _filter == 'all'
                ? 'Your completed runs, walks, and rides will appear here.'
                : 'No ${_filter}s yet. Try a different filter or start one.',
            style: TextStyle(
              color: Colors.white.withOpacity(0.6),
              fontSize: 14,
              fontWeight: FontWeight.w500,
              height: 1.4,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 22),
          SizedBox(
            height: 48,
            child: ElevatedButton(
              onPressed: () {
                HapticFeedback.lightImpact();
                final cb = JoviRunHistoryList.onStartRequested;
                if (cb != null) {
                  cb();
                } else {
                  Navigator.of(context).maybePop();
                }
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: _joviCoral,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 28),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(13),
                ),
                elevation: 6,
                shadowColor: _joviCoral.withOpacity(0.4),
              ),
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.play_arrow_rounded, size: 20),
                  SizedBox(width: 4),
                  Text(
                    'Start an Activity',
                    style: TextStyle(
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0.2,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLoadingState() {
    return Padding(
      padding: const EdgeInsets.all(32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const CircularProgressIndicator(
            valueColor: AlwaysStoppedAnimation<Color>(_joviCoral),
            strokeWidth: 2.4,
          ),
          const SizedBox(height: 14),
          Text(
            'Loading your history…',
            style: TextStyle(
              color: Colors.white.withOpacity(0.6),
              fontSize: 13,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorCard() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: _glassCard(
        padding: const EdgeInsets.all(16),
        borderColor: _joviErrorRed.withOpacity(0.4),
        tint: _joviErrorRed.withOpacity(0.1),
        child: Row(
          children: [
            const Icon(
              Icons.error_outline_rounded,
              color: _joviErrorRed,
              size: 22,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                _error ?? 'Something went wrong.',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PaginationSpinner extends StatelessWidget {
  const _PaginationSpinner({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.symmetric(vertical: 18),
      child: Center(
        child: SizedBox(
          width: 22,
          height: 22,
          child: CircularProgressIndicator(
            valueColor: AlwaysStoppedAnimation<Color>(_joviCoral),
            strokeWidth: 2.2,
          ),
        ),
      ),
    );
  }
}

// =======================================================================
// RUN DETAIL SCREEN
//
// Full-screen detail view for one completed activity. Hydrates from
// Firestore on open — summary doc, all split entries (embedded in
// summary), and the points subcollection for the map route.
//
// LAYOUT:
//   - Top app bar (back arrow, more menu)
//   - Hero header: activity icon, type, date, distance/duration
//     in huge text
//   - Map card: full route rendered as coral polyline, start (green)
//     and end (coral) markers, camera auto-fit to bounding box
//   - Stats grid: avg pace/speed, elevation, moving time, total time,
//     point count
//   - Splits table: per-mile (or per-5mi for ride)
//   - Notes field: editable TextField that autosaves on blur
//   - Delete button at bottom (confirms)
//
// Accepts `activityId` — required.
// =======================================================================

class RunDetailScreen extends StatefulWidget {
  const RunDetailScreen({
    Key? key,
    required this.activityId,
    this.justFinished = false,
    this.width,
    this.height,
  }) : super(key: key);

  final String activityId;

  /// True when opened straight from Stop. Shows the post-run summary
  /// header, waits for the final checkpoint to land, and swaps the back
  /// arrow for a Done button.
  final bool justFinished;
  final double? width;
  final double? height;

  @override
  State<RunDetailScreen> createState() => _RunDetailScreenState();
}

class _RunDetailScreenState extends State<RunDetailScreen> {
  bool _loading = true;
  String? _error;
  Map<String, dynamic>? _summary;
  List<_DetailPoint> _points = [];

  mb.MapboxMap? _mapController;
  mb.PolylineAnnotationManager? _routeManager;
  mb.PointAnnotationManager? _markerManager;
  bool _mapReady = false;
  bool _routeDrawn = false;

  late final TextEditingController _notesCtrl;
  Timer? _notesDebounceTimer;
  String? _lastSavedNotes;
  bool _notesSaving = false;
  bool _notesSaved = false;

  @override
  void initState() {
    super.initState();
    _notesCtrl = TextEditingController();
    _load();
  }

  @override
  void dispose() {
    _notesDebounceTimer?.cancel();
    // One last save attempt on exit for pending edits.
    _flushNotesIfDirty();
    _notesCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final uid = FirebaseAuth.instance.currentUser?.uid;
    if (uid == null) {
      setState(() {
        _loading = false;
        _error = 'Sign in to view this activity.';
      });
      return;
    }
    try {
      final docRef = FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('activities')
          .doc(widget.activityId);
      // Right after Stop, the engine's final checkpoint (summary + last
      // GPS points) is still in flight. Poll briefly until the summary
      // reads 'completed' so the member never sees a half-written run.
      DocumentSnapshot<Map<String, dynamic>> summarySnap = await docRef.get();
      if (widget.justFinished) {
        for (var attempt = 0; attempt < 8; attempt++) {
          final status = summarySnap.data()?['status'] as String?;
          if (summarySnap.exists && status == 'completed') break;
          await Future<void>.delayed(const Duration(milliseconds: 600));
          if (!mounted) return;
          summarySnap = await docRef.get();
        }
      }
      if (!summarySnap.exists) {
        setState(() {
          _loading = false;
          _error = 'Activity not found.';
        });
        return;
      }
      final summary = summarySnap.data()!;
      final pointsSnap =
          await docRef.collection('points').orderBy('sequenceNum').get();
      final points = <_DetailPoint>[];
      for (final d in pointsSnap.docs) {
        try {
          final m = d.data();
          points.add(_DetailPoint(
            lat: (m['lat'] as num).toDouble(),
            lng: (m['lng'] as num).toDouble(),
          ));
        } catch (_) {}
      }
      final existingNotes = (summary['notes'] as String?) ?? '';
      if (!mounted) return;
      setState(() {
        _summary = summary;
        _points = points;
        _loading = false;
        _notesCtrl.text = existingNotes;
        _lastSavedNotes = existingNotes;
      });
      if (widget.justFinished) HapticFeedback.mediumImpact();
      // If the map loaded before data did, draw now.
      if (_mapReady) {
        unawaited(_drawRouteAndFitCamera());
      }
    } catch (e, st) {
      _logError('detail load failed', e, st);
      if (mounted) {
        setState(() {
          _loading = false;
          _error = 'Could not load this activity. Try again later.';
        });
      }
    }
  }

  // ------------------------------------------------------------------
  // Notes autosave
  // ------------------------------------------------------------------

  void _onNotesChanged(String _) {
    _notesDebounceTimer?.cancel();
    _notesDebounceTimer = Timer(const Duration(seconds: 1), () {
      _flushNotesIfDirty();
    });
    if (_notesSaved) setState(() => _notesSaved = false);
  }

  Future<void> _flushNotesIfDirty() async {
    final current = _notesCtrl.text;
    if (current == _lastSavedNotes) return;
    final uid = FirebaseAuth.instance.currentUser?.uid;
    if (uid == null) return;
    if (mounted) setState(() => _notesSaving = true);
    try {
      await FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('activities')
          .doc(widget.activityId)
          .set({
        'notes': current,
        'updatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));
      _lastSavedNotes = current;
      if (mounted) {
        setState(() {
          _notesSaving = false;
          _notesSaved = true;
        });
        // Clear the saved indicator after a short delay.
        Future.delayed(const Duration(seconds: 2), () {
          if (mounted && _notesCtrl.text == _lastSavedNotes) {
            setState(() => _notesSaved = false);
          }
        });
      }
    } catch (e, st) {
      _logError('notes save failed', e, st);
      if (mounted) setState(() => _notesSaving = false);
    }
  }

  // ------------------------------------------------------------------
  // Delete
  // ------------------------------------------------------------------

  Future<void> _onDeleteTapped() async {
    final summary = _summary;
    if (summary == null) return;
    final type = (summary['type'] as String?) ?? 'run';
    final date = (summary['startedAt'] as Timestamp?)?.toDate();
    final confirmed = await showCupertinoDialog<bool>(
      context: context,
      builder: (ctx) => CupertinoAlertDialog(
        title: const Text('Delete This Activity?'),
        content: Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Text(
            date == null
                ? 'This will permanently delete this '
                    '${_activityLabel(type).toLowerCase()}. '
                    'This cannot be undone.'
                : 'This will permanently delete the '
                    '${_activityLabel(type).toLowerCase()} on '
                    '${_fmtRowDate(date)}. This cannot be undone.',
          ),
        ),
        actions: [
          CupertinoDialogAction(
            isDefaultAction: true,
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Keep'),
          ),
          CupertinoDialogAction(
            isDestructiveAction: true,
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    final uid = FirebaseAuth.instance.currentUser?.uid;
    if (uid == null) return;

    try {
      final docRef = FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('activities')
          .doc(widget.activityId);
      // Delete points in batches.
      const batchSize = 450;
      while (true) {
        final snap = await docRef.collection('points').limit(batchSize).get();
        if (snap.docs.isEmpty) break;
        final batch = FirebaseFirestore.instance.batch();
        for (final d in snap.docs) {
          batch.delete(d.reference);
        }
        await batch.commit();
        if (snap.docs.length < batchSize) break;
      }
      await docRef.delete();
      if (!mounted) return;
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(
            'Activity deleted',
            accent: _joviMint,
            icon: CupertinoIcons.checkmark_circle,
            duration: const Duration(seconds: 2)));
      Navigator.of(context).pop();
    } catch (e, st) {
      _logError('detail delete failed', e, st);
      if (mounted) {
        ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(
            'Could not delete. Try again.',
            accent: _joviErrorRed,
            icon: CupertinoIcons.exclamationmark_circle));
      }
    }
  }

  // ------------------------------------------------------------------
  // Build
  // ------------------------------------------------------------------

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
            stops: [0.0, 0.4, 1.0],
          ),
        ),
        child: SafeArea(
          child: _buildBody(),
        ),
      ),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const CircularProgressIndicator(
              valueColor: AlwaysStoppedAnimation<Color>(_joviCoral),
              strokeWidth: 2.4,
            ),
            const SizedBox(height: 14),
            Text(
              widget.justFinished ? 'Saving your activity…' : 'Loading…',
              style: TextStyle(
                color: Colors.white.withOpacity(0.6),
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      );
    }
    if (_error != null || _summary == null) {
      return Column(
        children: [
          _buildTopBar(title: ''),
          Expanded(
            child: Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(
                      Icons.error_outline_rounded,
                      color: _joviErrorRed,
                      size: 38,
                    ),
                    const SizedBox(height: 12),
                    Text(
                      _error ?? 'Something went wrong.',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      );
    }
    return _buildLoadedContent();
  }

  Widget _buildLoadedContent() {
    final s = _summary!;
    final type = (s['type'] as String?) ?? 'run';
    return Column(
      children: [
        _buildTopBar(
            title: widget.justFinished ? 'Summary' : _activityLabel(type)),
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(14, 4, 14, 24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (widget.justFinished) ...[
                  _buildFinishedBanner(s),
                  const SizedBox(height: 14),
                ],
                _buildHeroHeader(s),
                const SizedBox(height: 14),
                _buildMapCard(),
                const SizedBox(height: 14),
                _buildStatsGrid(s),
                const SizedBox(height: 14),
                _buildSplitsCard(s),
                const SizedBox(height: 14),
                _buildNotesCard(),
                const SizedBox(height: 18),
                _buildDeleteButton(),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildTopBar({required String title}) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(6, 8, 6, 6),
      child: Row(
        children: [
          if (widget.justFinished)
            const SizedBox(width: 72)
          else
            IconButton(
              onPressed: () {
                _flushNotesIfDirty();
                Navigator.of(context).maybePop();
              },
              icon: const Icon(Icons.arrow_back_ios_new_rounded,
                  color: Colors.white, size: 20),
            ),
          const Spacer(),
          if (title.isNotEmpty)
            Text(
              title,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 17,
                fontWeight: FontWeight.w600,
                letterSpacing: -0.4,
              ),
            ),
          const Spacer(),
          if (widget.justFinished)
            SizedBox(
              width: 72,
              child: TextButton(
                onPressed: () {
                  HapticFeedback.lightImpact();
                  _flushNotesIfDirty();
                  Navigator.of(context).maybePop();
                },
                style: TextButton.styleFrom(
                  foregroundColor: _joviCoralLight,
                  minimumSize: const Size(44, 44),
                ),
                child: const Text(
                  'Done',
                  style: TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.4,
                  ),
                ),
              ),
            )
          else
            const SizedBox(width: 48), // balance back button
        ],
      ),
    );
  }

  /// Post-run celebration strip. Plain and quick: a mint check, the
  /// headline, and where the run went. No confetti, no overshoot.
  Widget _buildFinishedBanner(Map<String, dynamic> s) {
    final type = (s['type'] as String?) ?? 'run';
    final distance = (s['distanceMeters'] as num?)?.toDouble() ?? 0;
    final rawSplits = s['splits'];
    final splitCount = rawSplits is List ? rawSplits.length : 0;
    final unit = type == 'ride' ? '5-mile' : 'mile';
    final detail = splitCount > 0
        ? '$splitCount $unit split${splitCount == 1 ? '' : 's'} recorded'
        : distance < 100
            ? 'Short one, but it counts'
            : 'Saved to your history';
    return _glassCard(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
      borderRadius: 18,
      tint: _joviMint.withOpacity(0.1),
      borderColor: _joviMint.withOpacity(0.35),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: _joviMint.withOpacity(0.18),
              shape: BoxShape.circle,
              border: Border.all(color: _joviMint.withOpacity(0.4)),
            ),
            child: const Icon(CupertinoIcons.checkmark_alt,
                color: _joviMint, size: 24),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  '${_activityLabel(type)} complete',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.5,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  detail,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.65),
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHeroHeader(Map<String, dynamic> s) {
    final type = (s['type'] as String?) ?? 'run';
    final startedAt = (s['startedAt'] as Timestamp?)?.toDate();
    final distance = (s['distanceMeters'] as num?)?.toDouble() ?? 0;
    final moving = (s['movingSeconds'] as num?)?.toInt() ?? 0;
    return _glassCard(
      padding: const EdgeInsets.fromLTRB(18, 16, 18, 18),
      borderRadius: 18,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      _joviCoral.withOpacity(0.35),
                      _joviCoralLight.withOpacity(0.18),
                    ],
                  ),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: _joviCoral.withOpacity(0.45),
                    width: 0.8,
                  ),
                ),
                child: Icon(_activityIcon(type), color: Colors.white, size: 22),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      _activityLabel(type),
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                        letterSpacing: -0.2,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      startedAt == null ? '—' : _fmtRowDate(startedAt),
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.6),
                        fontSize: 12.5,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Expanded(
                child: _heroStat(
                  label: 'Distance',
                  value: (distance / _metersPerMile).toStringAsFixed(2),
                  unit: 'mi',
                ),
              ),
              Container(
                width: 1,
                height: 50,
                color: Colors.white.withOpacity(0.1),
              ),
              Expanded(
                child: _heroStat(
                  label: 'Time',
                  value: _fmtDurationHMS(moving),
                  unit: null,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _heroStat({
    required String label,
    required String value,
    String? unit,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.center,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          label,
          style: TextStyle(
            color: Colors.white.withOpacity(0.6),
            fontSize: 12,
            fontWeight: FontWeight.w600,
            letterSpacing: -0.1,
          ),
        ),
        const SizedBox(height: 4),
        FittedBox(
          fit: BoxFit.scaleDown,
          child: Text(
            value,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 38,
              fontWeight: FontWeight.w700,
              letterSpacing: -1.3,
              height: 1.0,
            ),
          ),
        ),
        if (unit != null) ...[
          const SizedBox(height: 2),
          Text(
            unit,
            style: TextStyle(
              color: Colors.white.withOpacity(0.5),
              fontSize: 12,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.5,
            ),
          ),
        ],
      ],
    );
  }

  // ------------------------------------------------------------------
  // MAP CARD — static route display with start/end markers
  // ------------------------------------------------------------------

  Widget _buildMapCard() {
    if (_mapboxPublicToken.startsWith('pk.REPLACE')) {
      return _glassCard(
        padding: const EdgeInsets.all(24),
        borderRadius: 18,
        child: Column(
          children: [
            const Icon(
              Icons.map_outlined,
              color: _joviGold,
              size: 32,
            ),
            const SizedBox(height: 10),
            Text(
              'Map unavailable — Mapbox token not configured.',
              style: TextStyle(
                color: _joviGold.withOpacity(0.9),
                fontSize: 12.5,
                fontWeight: FontWeight.w700,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      );
    }
    if (_points.length < 2) {
      return _glassCard(
        padding: const EdgeInsets.all(24),
        borderRadius: 18,
        child: Column(
          children: [
            Icon(
              Icons.location_off_rounded,
              color: Colors.white.withOpacity(0.5),
              size: 28,
            ),
            const SizedBox(height: 10),
            Text(
              'No GPS data for this activity.',
              style: TextStyle(
                color: Colors.white.withOpacity(0.6),
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      );
    }

    mb.MapboxOptions.setAccessToken(_mapboxPublicToken);

    return ClipRRect(
      borderRadius: BorderRadius.circular(18),
      child: SizedBox(
        height: 260,
        child: Stack(
          fit: StackFit.expand,
          children: [
            mb.MapWidget(
              key: ValueKey('detail_map_${widget.activityId}'),
              styleUri: 'mapbox://styles/mapbox/outdoors-v12',
              cameraOptions: mb.CameraOptions(
                center: mb.Point(
                  coordinates: mb.Position(
                    _points.first.lng,
                    _points.first.lat,
                  ),
                ),
                zoom: 13.5,
              ),
              onMapCreated: _onDetailMapCreated,
            ),
            // Subtle overlay tint so the navy+glass feel carries
            // through even on the map.
            IgnorePointer(
              child: Container(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(18),
                  border: Border.all(
                    color: Colors.white.withOpacity(0.12),
                    width: 1,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _onDetailMapCreated(mb.MapboxMap controller) async {
    _mapController = controller;
    try {
      _routeManager =
          await controller.annotations.createPolylineAnnotationManager();
      _markerManager =
          await controller.annotations.createPointAnnotationManager();
      _mapReady = true;
      await _drawRouteAndFitCamera();
    } catch (e, st) {
      _logError('detail map setup failed', e, st);
    }
  }

  Future<void> _drawRouteAndFitCamera() async {
    if (!_mapReady || _routeDrawn) return;
    if (_points.length < 2) return;
    final routeMgr = _routeManager;
    if (routeMgr == null) return;
    try {
      final coords =
          _points.map((p) => mb.Position(p.lng, p.lat)).toList(growable: false);
      await routeMgr.create(
        mb.PolylineAnnotationOptions(
          geometry: mb.LineString(coordinates: coords),
          lineColor: _joviCoral.value,
          lineWidth: 5.0,
          lineOpacity: 0.95,
        ),
      );

      // Fit camera to the route's bounding box. We compute min/max
      // manually since different mapbox_maps_flutter versions expose
      // fit-coordinates helpers differently.
      double minLat = _points.first.lat;
      double maxLat = _points.first.lat;
      double minLng = _points.first.lng;
      double maxLng = _points.first.lng;
      for (final p in _points) {
        if (p.lat < minLat) minLat = p.lat;
        if (p.lat > maxLat) maxLat = p.lat;
        if (p.lng < minLng) minLng = p.lng;
        if (p.lng > maxLng) maxLng = p.lng;
      }
      final centerLat = (minLat + maxLat) / 2;
      final centerLng = (minLng + maxLng) / 2;
      // Rough zoom heuristic based on bounding box span. A real
      // fit-bounds would use cameraForCoordinates but the API varies
      // across versions; this works for the vast majority of runs.
      final latSpan = (maxLat - minLat).abs();
      final lngSpan = (maxLng - minLng).abs();
      final span = latSpan > lngSpan ? latSpan : lngSpan;
      double zoom;
      if (span < 0.005) {
        zoom = 15.5;
      } else if (span < 0.01) {
        zoom = 14.5;
      } else if (span < 0.025) {
        zoom = 13.5;
      } else if (span < 0.06) {
        zoom = 12.5;
      } else if (span < 0.15) {
        zoom = 11;
      } else {
        zoom = 10;
      }

      await _mapController?.flyTo(
        mb.CameraOptions(
          center: mb.Point(
            coordinates: mb.Position(centerLng, centerLat),
          ),
          zoom: zoom,
        ),
        mb.MapAnimationOptions(duration: 400),
      );
      _routeDrawn = true;
    } catch (e, st) {
      _logError('draw route failed', e, st);
    }
  }

  // ------------------------------------------------------------------
  // STATS GRID — 2x3 grid of secondary stats
  // ------------------------------------------------------------------

  Widget _buildStatsGrid(Map<String, dynamic> s) {
    final type = (s['type'] as String?) ?? 'run';
    final isRide = type == 'ride';
    final avgSpeed = (s['avgSpeedMetersPerSecond'] as num?)?.toDouble();
    final elev = (s['elevationGainMeters'] as num?)?.toDouble() ?? 0;
    final elevLoss = (s['elevationLossMeters'] as num?)?.toDouble() ?? 0;
    final duration = (s['durationSeconds'] as num?)?.toInt() ?? 0;
    final moving = (s['movingSeconds'] as num?)?.toInt() ?? 0;
    final pointCount = (s['pointCount'] as num?)?.toInt() ?? 0;
    return _glassCard(
      padding: const EdgeInsets.all(14),
      borderRadius: 16,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(2, 0, 2, 8),
            child: Text(
              'Stats',
              style: TextStyle(
                color: Colors.white.withOpacity(0.6),
                fontSize: 13,
                fontWeight: FontWeight.w600,
                letterSpacing: -0.1,
              ),
            ),
          ),
          Row(
            children: [
              Expanded(
                child: _statTile(
                  label: isRide ? 'Avg speed' : 'Avg pace',
                  value: isRide
                      ? _fmtSpeedMph(avgSpeed)
                      : _fmtPaceMinPerMile(avgSpeed),
                  unit: isRide ? 'mph' : '/mi',
                  icon: Icons.speed_rounded,
                ),
              ),
              Expanded(
                child: _statTile(
                  label: 'Elev gain',
                  value: _fmtElevationFt(elev).split(' ').first,
                  unit: 'ft',
                  icon: Icons.terrain_rounded,
                ),
              ),
            ],
          ),
          Container(
            height: 1,
            color: Colors.white.withOpacity(0.06),
            margin: const EdgeInsets.symmetric(vertical: 10),
          ),
          Row(
            children: [
              Expanded(
                child: _statTile(
                  label: 'Moving',
                  value: _fmtDurationHMS(moving),
                  icon: Icons.timer_outlined,
                ),
              ),
              Expanded(
                child: _statTile(
                  label: 'Total',
                  value: _fmtDurationHMS(duration),
                  icon: Icons.schedule_rounded,
                ),
              ),
            ],
          ),
          Container(
            height: 1,
            color: Colors.white.withOpacity(0.06),
            margin: const EdgeInsets.symmetric(vertical: 10),
          ),
          Row(
            children: [
              Expanded(
                child: _statTile(
                  label: 'Elev loss',
                  value: _fmtElevationFt(elevLoss).split(' ').first,
                  unit: 'ft',
                  icon: Icons.south_rounded,
                ),
              ),
              Expanded(
                child: _statTile(
                  label: 'GPS points',
                  value: '$pointCount',
                  icon: Icons.my_location_rounded,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _statTile({
    required String label,
    required String value,
    String? unit,
    required IconData icon,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Icon(icon, color: _joviCoral, size: 14),
          const SizedBox(width: 7),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  label,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.6),
                    fontSize: 11.5,
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.1,
                  ),
                ),
                const SizedBox(height: 1),
                Text.rich(
                  TextSpan(
                    children: [
                      TextSpan(
                        text: value,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 16,
                          fontWeight: FontWeight.w700,
                          letterSpacing: -0.3,
                        ),
                      ),
                      if (unit != null)
                        TextSpan(
                          text: ' $unit',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.55),
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ------------------------------------------------------------------
  // SPLITS CARD — per-mile (or per-5mi for ride) pace table
  // ------------------------------------------------------------------

  Widget _buildSplitsCard(Map<String, dynamic> s) {
    final rawSplits = s['splits'];
    if (rawSplits is! List || rawSplits.isEmpty) {
      return const SizedBox.shrink();
    }
    final type = (s['type'] as String?) ?? 'run';
    final isRide = type == 'ride';
    final splits = <_DetailSplit>[];
    for (final raw in rawSplits) {
      if (raw is Map<String, dynamic>) {
        try {
          splits.add(_DetailSplit(
            index: (raw['index'] as num).toInt(),
            distanceMeters: (raw['distanceMeters'] as num).toDouble(),
            durationSeconds: (raw['durationSeconds'] as num).toInt(),
            avgSpeedMps: (raw['avgSpeedMps'] as num).toDouble(),
          ));
        } catch (_) {}
      }
    }
    if (splits.isEmpty) return const SizedBox.shrink();

    // Find the fastest pace so we can highlight it with a coral bar.
    double maxSpeed = 0;
    for (final sp in splits) {
      if (sp.avgSpeedMps > maxSpeed) maxSpeed = sp.avgSpeedMps;
    }

    return _glassCard(
      padding: const EdgeInsets.all(14),
      borderRadius: 16,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(2, 0, 2, 10),
            child: Row(
              children: [
                Text(
                  isRide ? '5-Mile Splits' : 'Mile Splits',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.6),
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.1,
                  ),
                ),
                const Spacer(),
                Text(
                  '${splits.length}',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.35),
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
          ...splits.map((sp) {
            final barWidth = maxSpeed > 0 ? (sp.avgSpeedMps / maxSpeed) : 0.0;
            final isFastest = sp.avgSpeedMps == maxSpeed;
            return Padding(
              padding: const EdgeInsets.symmetric(vertical: 5),
              child: Row(
                children: [
                  SizedBox(
                    width: 26,
                    child: Text(
                      '${sp.index + 1}',
                      style: TextStyle(
                        color: isFastest ? _joviCoral : Colors.white,
                        fontSize: 13.5,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  Expanded(
                    child: Stack(
                      children: [
                        Container(
                          height: 18,
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.04),
                            borderRadius: BorderRadius.circular(4),
                          ),
                        ),
                        FractionallySizedBox(
                          widthFactor: barWidth.clamp(0.02, 1.0),
                          child: Container(
                            height: 18,
                            decoration: BoxDecoration(
                              gradient: LinearGradient(
                                colors: [
                                  _joviCoral.withOpacity(isFastest ? 0.8 : 0.5),
                                  _joviCoralLight
                                      .withOpacity(isFastest ? 0.6 : 0.3),
                                ],
                              ),
                              borderRadius: BorderRadius.circular(4),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  SizedBox(
                    width: 64,
                    child: Text(
                      isRide
                          ? '${_fmtSpeedMph(sp.avgSpeedMps)} mph'
                          : '${_fmtPaceMinPerMile(sp.avgSpeedMps)} /mi',
                      textAlign: TextAlign.right,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 13,
                        fontWeight: FontWeight.w800,
                        fontFeatures: [FontFeature.tabularFigures()],
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  SizedBox(
                    width: 44,
                    child: Text(
                      _fmtDurationHMS(sp.durationSeconds),
                      textAlign: TextAlign.right,
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.55),
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        fontFeatures: const [FontFeature.tabularFigures()],
                      ),
                    ),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }

  // ------------------------------------------------------------------
  // NOTES CARD — editable, autosaves on blur
  // ------------------------------------------------------------------

  Widget _buildNotesCard() {
    return _glassCard(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 14),
      borderRadius: 16,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                'Notes',
                style: TextStyle(
                  color: Colors.white.withOpacity(0.6),
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  letterSpacing: -0.1,
                ),
              ),
              const Spacer(),
              if (_notesSaving)
                Row(
                  children: [
                    SizedBox(
                      width: 11,
                      height: 11,
                      child: CircularProgressIndicator(
                        valueColor: AlwaysStoppedAnimation<Color>(
                          Colors.white.withOpacity(0.45),
                        ),
                        strokeWidth: 1.6,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      'Saving',
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.45),
                        fontSize: 10.5,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0.3,
                      ),
                    ),
                  ],
                )
              else if (_notesSaved)
                Row(
                  children: [
                    const Icon(Icons.check_circle_rounded,
                        color: _joviMint, size: 12),
                    const SizedBox(width: 4),
                    Text(
                      'Saved',
                      style: TextStyle(
                        color: _joviMint.withOpacity(0.85),
                        fontSize: 10.5,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.3,
                      ),
                    ),
                  ],
                ),
            ],
          ),
          const SizedBox(height: 8),
          Focus(
            onFocusChange: (focused) {
              if (!focused) _flushNotesIfDirty();
            },
            child: TextField(
              controller: _notesCtrl,
              maxLines: null,
              minLines: 3,
              textCapitalization: TextCapitalization.sentences,
              cursorColor: _joviCoral,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 14,
                fontWeight: FontWeight.w500,
                height: 1.4,
              ),
              onChanged: _onNotesChanged,
              decoration: InputDecoration(
                hintText: 'How did this activity feel? Weather, mood, '
                    'anything worth remembering.',
                hintStyle: TextStyle(
                  color: Colors.white.withOpacity(0.3),
                  fontSize: 13.5,
                  fontWeight: FontWeight.w500,
                  height: 1.4,
                ),
                isCollapsed: true,
                contentPadding:
                    const EdgeInsets.symmetric(vertical: 8, horizontal: 0),
                border: InputBorder.none,
                enabledBorder: InputBorder.none,
                focusedBorder: InputBorder.none,
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ------------------------------------------------------------------
  // DELETE BUTTON
  // ------------------------------------------------------------------

  Widget _buildDeleteButton() {
    return SizedBox(
      width: double.infinity,
      child: TextButton.icon(
        onPressed: _onDeleteTapped,
        icon: Icon(
          Icons.delete_outline_rounded,
          color: _joviErrorRed.withOpacity(0.9),
          size: 18,
        ),
        label: Text(
          'Delete Activity',
          style: TextStyle(
            color: _joviErrorRed.withOpacity(0.9),
            fontSize: 13.5,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.2,
          ),
        ),
        style: TextButton.styleFrom(
          padding: const EdgeInsets.symmetric(vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: BorderSide(
              color: _joviErrorRed.withOpacity(0.3),
              width: 1,
            ),
          ),
        ),
      ),
    );
  }
}

// =======================================================================
// SUPPORTING MODELS
// =======================================================================

class _DetailPoint {
  final double lat;
  final double lng;
  const _DetailPoint({required this.lat, required this.lng});
}

class _DetailSplit {
  final int index;
  final double distanceMeters;
  final int durationSeconds;
  final double avgSpeedMps;
  const _DetailSplit({
    required this.index,
    required this.distanceMeters,
    required this.durationSeconds,
    required this.avgSpeedMps,
  });
}
