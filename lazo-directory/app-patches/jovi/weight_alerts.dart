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

// ═══════════════════════════════════════════════════════════════════════════
// JOVI HEALTH — WEIGHT ALERTS (IN-APP)
// Version: 2026.09.22-r2 (Apple HIG pass: press feedback, painted glass,
//          Reduce Motion, navy toasts, title-case labels)
// r1:      2026.04.19
// Build: JC-WEIGHTALERT-0922-002
//
// Surfaces in-app notification cards when a vet-recorded weight (entered
// by a provider in the admin app) exceeds the healthy range for the pet's
// breed. Listens to:
//
//   users/{uid}/pets/{petId}/vet_weight_logs/{logId}   (source of truth)
//   users/{uid}/weight_alerts/{alertId}                (in-app surface)
//
// Architecture notes:
//   - Admin app writes vet_weight_logs; this consumer reads them.
//   - A Cloud Function SHOULD own the alert-writing + FCM push path for
//     exactly-once delivery. Until that ships, this widget computes alerts
//     client-side as a fallback and writes to weight_alerts itself (idempotent
//     by logId so duplicate client runs don't spam).
//   - Member dismisses alerts by setting dismissed=true; the doc stays for
//     audit history.
//   - Breed reference dataset is curated inline (top ~25 US breeds). Unknown
//     or mixed breeds fall through to no alert — safer than false-alerting.
//   - Threshold: weight > (breedMean + 1 std dev) triggers an alert.
//
// CLOUD FUNCTION PSEUDOCODE (to hand to server-side dev):
//
//   exports.onVetWeightLogWrite = functions.firestore
//     .document('users/{uid}/pets/{petId}/vet_weight_logs/{logId}')
//     .onCreate(async (snap, context) => {
//       const log = snap.data();
//       const { uid, petId, logId } = context.params;
//       // 1. Read pet doc to get breed
//       const pet = await getPet(uid, petId);
//       // 2. Look up breed reference (same dataset as _breedRefs below)
//       const ref = lookupBreedRef(pet.breed, pet.type);
//       if (!ref) return; // unknown breed, skip
//       // 3. Compute threshold
//       const threshold = ref.meanLbs + ref.stdDevLbs;
//       if (log.weightLbs <= threshold) return; // within healthy range
//       // 4. Write alert doc (idempotent via logId)
//       await db.doc(`users/${uid}/weight_alerts/${logId}`).set({
//         logId, petId, petName: pet.name, weightLbs: log.weightLbs,
//         breedMeanLbs: ref.meanLbs, breedStdDev: ref.stdDevLbs,
//         threshold, providerName: log.providerName,
//         recordedAt: log.recordedAt, createdAt: FieldValue.serverTimestamp(),
//         dismissed: false, schemaVersion: 1,
//       }, { merge: false });
//       // 5. Send FCM push to user's devices
//       const tokens = await getUserFcmTokens(uid);
//       await admin.messaging().sendMulticast({
//         tokens,
//         notification: {
//           title: `${pet.name}'s weight is above range`,
//           body: `${log.weightLbs.toFixed(1)} lbs was logged. Tap to review.`,
//         },
//         data: { type: 'weight_alert', petId, alertId: logId },
//       });
//     });
// ═══════════════════════════════════════════════════════════════════════════

import 'dart:convert';
import 'dart:async';
import 'dart:math' as math;
import 'dart:ui' as ui_dart;
import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:intl/intl.dart';

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

class WeightAlerts extends StatefulWidget {
  /// If true, show only the most recent undismissed alert as a compact
  /// banner (for home dashboard usage). If false, show the full scrollable
  /// list of alerts (for a dedicated "Alerts" screen).
  final bool compact;

  /// If non-null, only show alerts for this specific pet. Useful for
  /// embedding in the Pet Profile detail view.
  final String? petId;

  final double? width;
  final double? height;

  const WeightAlerts({
    Key? key,
    this.width,
    this.height,
    this.compact = true,
    this.petId,
  }) : super(key: key);

  @override
  State<WeightAlerts> createState() => _WeightAlertsState();
}

class _WeightAlertsState extends State<WeightAlerts>
    with TickerProviderStateMixin {
  // ─── Alert state ────────────────────────────────────────────────────────
  List<_WeightAlert> _alerts = [];
  bool _alertsLoading = true;
  String? _alertsError;
  StreamSubscription<QuerySnapshot<Map<String, dynamic>>>? _alertsSub;

  // ─── Pet state (needed for client-side fallback) ────────────────────────
  // Map petId -> _PetLite. Populated once at init; refreshed if legacy doc
  // updates. Not a live stream — the fallback only needs the current breed/name.
  final Map<String, _PetLite> _petsById = {};
  bool _petsLoaded = false;

  // ─── Vet log listeners (client-side fallback) ───────────────────────────
  // We listen to vet_weight_logs for each pet so if the admin app writes a
  // new log and the Cloud Function hasn't yet fired, we compute the alert
  // client-side. Each pet gets its own sub.
  final Map<String, StreamSubscription<QuerySnapshot<Map<String, dynamic>>>>
      _vetLogsSubs = {};

  /// Track which log IDs we've already processed (to avoid re-checking
  /// existing logs on every snapshot).
  final Set<String> _processedLogIds = {};

  // ─── Animations ─────────────────────────────────────────────────────────
  late AnimationController _fadeCtrl;
  late Animation<double> _fadeAnim;

  // ─── Show/hide state for dismissed alerts in full view ──────────────────
  bool _showDismissed = false;

  // ─── Derived ────────────────────────────────────────────────────────────
  List<_WeightAlert> get _activeAlerts =>
      _alerts.where((a) => !a.dismissed).toList();

  List<_WeightAlert> get _dismissedAlerts =>
      _alerts.where((a) => a.dismissed).toList();

  List<_WeightAlert> get _visibleAlerts {
    if (widget.compact) {
      // Compact mode: only undismissed, only most recent per pet, max 3
      final byPet = <String, _WeightAlert>{};
      for (final a in _activeAlerts) {
        final existing = byPet[a.petId];
        if (existing == null || a.recordedAt.isAfter(existing.recordedAt)) {
          byPet[a.petId] = a;
        }
      }
      final list = byPet.values.toList()
        ..sort((a, b) => b.recordedAt.compareTo(a.recordedAt));
      return list.take(3).toList();
    }
    // Full view: active first, dismissed if toggled
    if (_showDismissed) {
      return [..._activeAlerts, ..._dismissedAlerts];
    }
    return _activeAlerts;
  }

  // ─── Lifecycle ──────────────────────────────────────────────────────────
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

    _subscribeAlerts();
    _loadPetsAndSubscribeVetLogs();
  }

  @override
  void dispose() {
    _fadeCtrl.dispose();
    _alertsSub?.cancel();
    for (final sub in _vetLogsSubs.values) {
      sub.cancel();
    }
    _vetLogsSubs.clear();
    super.dispose();
  }

  // ═══════════════════════════════════════════════════════════════════════
  // ALERTS SUBSCRIPTION
  // ═══════════════════════════════════════════════════════════════════════

  void _subscribeAlerts() {
    _alertsSub?.cancel();
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      if (mounted) {
        setState(() {
          _alertsLoading = false;
          _alerts = [];
        });
      }
      return;
    }
    try {
      Query<Map<String, dynamic>> query = FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .collection('weight_alerts');

      // If the widget is pet-scoped, filter server-side
      if (widget.petId != null && widget.petId!.isNotEmpty) {
        query = query.where('petId', isEqualTo: widget.petId);
      }

      _alertsSub = query
          .orderBy('recordedAt', descending: true)
          .limit(50)
          .snapshots()
          .listen(
        (snap) {
          if (!mounted) return;
          final list = <_WeightAlert>[];
          for (final doc in snap.docs) {
            try {
              list.add(_WeightAlert.fromFirestore(doc.id, doc.data()));
            } catch (e) {
              debugPrint('WeightAlerts: skipped malformed alert ${doc.id}: $e');
            }
          }
          setState(() {
            _alerts = list;
            _alertsLoading = false;
            _alertsError = null;
          });
        },
        onError: (err) {
          debugPrint('WeightAlerts: alerts listener error: $err');
          if (!mounted) return;
          setState(() {
            _alertsLoading = false;
            _alertsError = _friendlyErrorMessage(_classifyError(err));
          });
        },
        cancelOnError: false,
      );
    } catch (e) {
      debugPrint('WeightAlerts: failed to subscribe to alerts: $e');
      if (!mounted) return;
      setState(() {
        _alertsLoading = false;
        _alertsError = _friendlyErrorMessage(_classifyError(e));
      });
    }
  }

  // ═══════════════════════════════════════════════════════════════════════
  // PET LOADING + VET LOG SUBSCRIPTIONS (client-side fallback)
  // ═══════════════════════════════════════════════════════════════════════

  Future<void> _loadPetsAndSubscribeVetLogs() async {
    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user == null) return;

      final userDocF =
          FirebaseFirestore.instance.collection('users').doc(user.uid).get();
      final subcollF = FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .collection('pets')
          .get();

      final results = await Future.wait([userDocF, subcollF]);
      final userDoc = results[0] as DocumentSnapshot<Map<String, dynamic>>;
      final subcoll = results[1] as QuerySnapshot<Map<String, dynamic>>;

      final byId = <String, _PetLite>{};
      for (final doc in subcoll.docs) {
        try {
          final pet = _PetLite.fromSubcollection(doc.id, doc.data());
          byId[pet.petId] = pet;
        } catch (e) {
          debugPrint('WeightAlerts: skipped malformed pet ${doc.id}: $e');
        }
      }

      final userData = userDoc.data();
      final rawPets = userData?['pets'];
      List<dynamic>? legacyList;
      if (rawPets is List) {
        legacyList = rawPets;
      } else if (rawPets is String) {
        try {
          final parsed = jsonDecode(rawPets);
          if (parsed is List) legacyList = parsed;
        } catch (_) {}
      }
      if (legacyList != null) {
        for (final item in legacyList) {
          if (item is! Map) continue;
          try {
            final m = Map<String, dynamic>.from(item);
            final pet = _PetLite.fromLegacyJson(m);
            byId.putIfAbsent(pet.petId, () => pet);
          } catch (e) {
            debugPrint('WeightAlerts: skipped malformed legacy pet: $e');
          }
        }
      }

      if (!mounted) return;
      _petsById.clear();
      _petsById.addAll(byId);
      _petsLoaded = true;

      // Subscribe to vet weight logs for each pet (client fallback path).
      // If widget.petId is set, only subscribe to that one.
      final petsToWatch = widget.petId != null && widget.petId!.isNotEmpty
          ? (byId.containsKey(widget.petId)
              ? [byId[widget.petId]!]
              : <_PetLite>[])
          : byId.values.toList();

      for (final pet in petsToWatch) {
        _subscribeVetLogsForPet(pet);
      }
    } catch (e) {
      debugPrint('WeightAlerts: failed to load pets: $e');
    }
  }

  void _subscribeVetLogsForPet(_PetLite pet) {
    _vetLogsSubs[pet.petId]?.cancel();
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return;

    try {
      // Only listen to the most recent 5 logs — we just need to react to
      // newly-created ones, not backfill the entire history.
      final sub = FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .collection('pets')
          .doc(pet.petId)
          .collection('vet_weight_logs')
          .orderBy('recordedAt', descending: true)
          .limit(5)
          .snapshots()
          .listen(
        (snap) async {
          if (!mounted) return;
          for (final change in snap.docChanges) {
            if (change.type != DocumentChangeType.added) continue;
            final doc = change.doc;
            if (_processedLogIds.contains(doc.id)) continue;
            _processedLogIds.add(doc.id);
            try {
              final log =
                  _VetWeightLog.fromFirestore(pet.petId, doc.id, doc.data()!);
              // Compute + possibly write alert. Guarded by existing-doc check.
              final service = _WeightAlertService();
              await service.maybeCreateAlertForLog(pet: pet, log: log);
            } catch (e) {
              debugPrint('WeightAlerts: failed to process vet log ${doc.id}: $e');
            }
          }
        },
        onError: (err) {
          debugPrint('WeightAlerts: vet logs listener error for ${pet.petId}: $err');
        },
        cancelOnError: false,
      );
      _vetLogsSubs[pet.petId] = sub;
    } catch (e) {
      debugPrint('WeightAlerts: failed to subscribe vet logs (${pet.petId}): $e');
    }
  }

  // ═══════════════════════════════════════════════════════════════════════
  // DISMISS / ACTIONS
  // ═══════════════════════════════════════════════════════════════════════

  Future<void> _dismissAlert(_WeightAlert alert) async {
    HapticFeedback.lightImpact();
    try {
      final service = _WeightAlertService();
      await service.dismissAlert(alert.id);
      // Live listener updates state; no need to setState here.
    } catch (e) {
      debugPrint('WeightAlerts: dismiss failed: $e');
      if (!mounted) return;
      _showSnackBar("Couldn't dismiss that alert. Please try again.",
          isError: true);
    }
  }

  Future<void> _undismissAlert(_WeightAlert alert) async {
    HapticFeedback.lightImpact();
    try {
      final service = _WeightAlertService();
      await service.undismissAlert(alert.id);
    } catch (e) {
      debugPrint('WeightAlerts: undismiss failed: $e');
      if (!mounted) return;
      _showSnackBar("Couldn't restore that alert. Please try again.",
          isError: true);
    }
  }

  // ═══════════════════════════════════════════════════════════════════════
  // NAVIGATION HELPERS
  // ═══════════════════════════════════════════════════════════════════════

  void _openPetProfile(_WeightAlert alert) {
    HapticFeedback.lightImpact();
    final params = <String, String>{'petId': alert.petId};
    _tryRoute(['petPro', 'petProfiles', 'PetProfiles', 'pet_profiles'], params);
  }

  void _openSymptomChecker(_WeightAlert alert) {
    HapticFeedback.lightImpact();
    final params = <String, String>{'petId': alert.petId};
    _tryRoute(
      ['petSymptomChecker', 'PetSymptomChecker', 'pet_symptom_checker'],
      params,
    );
  }

  void _scheduleVetVisit(_WeightAlert alert) {
    HapticFeedback.mediumImpact();
    final params = <String, String>{
      'visitMode': 'Clinic',
      'audience': 'Pet',
      'petId': alert.petId,
    };
    _tryRoute(
      ['requests', 'Requests', 'requestCare'],
      params,
      fallbackMessage: "Couldn't open the request flow.",
    );
  }

  // NOTE: context.pushNamed never throws on an unknown name at runtime, so
  // only the FIRST candidate is ever tried. Keep the real route name first.
  void _tryRoute(List<String> candidates, Map<String, String> params,
      {String? fallbackMessage}) {
    for (final name in candidates) {
      try {
        context.pushNamed(name, queryParameters: params);
        return;
      } catch (_) {
        // try next candidate
      }
    }
    if (!mounted) return;
    _showSnackBar(fallbackMessage ?? "Couldn't open that screen.",
        isError: true);
  }

  // ═══════════════════════════════════════════════════════════════════════
  // UX HELPERS
  // ═══════════════════════════════════════════════════════════════════════

  void _showSnackBar(String message, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(message,
        accent: isError ? _joviErrorRed : _joviMintDark,
        icon: isError
            ? CupertinoIcons.exclamationmark_circle
            : CupertinoIcons.checkmark_circle));
  }

  String _formatLbs(double lbs) {
    if (lbs == lbs.roundToDouble()) {
      return '${lbs.toInt()} lbs';
    }
    return '${lbs.toStringAsFixed(1)} lbs';
  }

  String _formatShortDate(DateTime d) => DateFormat('MMM d, y').format(d);

  String _formatRelative(DateTime d) {
    final now = DateTime.now();
    final diff = now.difference(d);
    if (diff.inMinutes < 60) {
      final m = diff.inMinutes;
      return m <= 1 ? 'Just now' : '$m min ago';
    }
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    if (diff.inDays == 1) return 'Yesterday';
    if (diff.inDays < 7) return '${diff.inDays}d ago';
    if (diff.inDays < 60) return '${(diff.inDays / 7).round()}w ago';
    return DateFormat('MMM d, y').format(d);
  }

  // ═══════════════════════════════════════════════════════════════════════
  // ROOT BUILD
  // ═══════════════════════════════════════════════════════════════════════

  @override
  Widget build(BuildContext context) {
    if (widget.compact) {
      return _buildCompactView();
    }
    return _buildFullView();
  }

  // ─────────────────────────────────────────────────────────────────────
  // COMPACT VIEW — For home dashboard / embed anywhere.
  // Renders nothing (shrink) if no active alerts, otherwise shows a
  // compact stack of up to 3 most-recent-per-pet alerts.
  // ─────────────────────────────────────────────────────────────────────

  Widget _buildCompactView() {
    if (_alertsLoading) return const SizedBox.shrink();
    final visible = _visibleAlerts;
    if (visible.isEmpty) return const SizedBox.shrink();

    return FadeTransition(
      opacity: _fadeAnim,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            _buildCompactHeader(visible.length),
            const SizedBox(height: 8),
            ...visible.map((a) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: _buildCompactCard(a),
                )),
          ],
        ),
      ),
    );
  }

  Widget _buildCompactHeader(int count) {
    return Row(
      children: [
        Container(
          width: 26,
          height: 26,
          decoration: BoxDecoration(
            color: _joviGold.withOpacity(0.16),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: _joviGold.withOpacity(0.35),
              width: 0.8,
            ),
          ),
          child: const Icon(Icons.monitor_weight_rounded,
              color: _joviGold, size: 14),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            count == 1 ? 'Weight alert' : '$count weight alerts',
            style: const TextStyle(
              color: Colors.white,
              fontSize: 12.5,
              fontWeight: FontWeight.w800,
              letterSpacing: -0.2,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildCompactCard(_WeightAlert alert) {
    return _PressableMaterial(
      child: InkWell(
        onTap: () => _showAlertDetail(alert),
        borderRadius: BorderRadius.circular(14),
        child: _glassCard(
          bgOpacity: 0.08,
          borderOpacity: 0.3,
          borderWidth: 1,
          padding: const EdgeInsets.all(12),
          radius: 14,
          borderTint: _joviGold,
          child: Row(
            children: [
              _petAvatarOrIcon(alert, size: 40),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text.rich(
                      TextSpan(
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                          letterSpacing: -0.2,
                        ),
                        children: [
                          TextSpan(text: alert.petName),
                          const TextSpan(
                            text: "'s weight is above range",
                            style: TextStyle(fontWeight: FontWeight.w600),
                          ),
                        ],
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 3),
                    Row(
                      children: [
                        Icon(Icons.monitor_weight_outlined,
                            size: 11, color: Colors.white.withOpacity(0.5)),
                        const SizedBox(width: 3),
                        Text(
                          _formatLbs(alert.weightLbs),
                          style: TextStyle(
                            color: _joviGold,
                            fontSize: 11.5,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        const SizedBox(width: 4),
                        Text(
                          'logged ${_formatRelative(alert.recordedAt)}',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.55),
                            fontSize: 11,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              Icon(Icons.chevron_right_rounded,
                  color: Colors.white.withOpacity(0.4), size: 18),
            ],
          ),
        ),
      ),
    );
  }

  // ─────────────────────────────────────────────────────────────────────
  // FULL VIEW — Standalone scrollable page for "Alerts" tab
  // ─────────────────────────────────────────────────────────────────────

  Widget _buildFullView() {
    final mq = MediaQuery.of(context).size;
    return Container(
      width: mq.width,
      height: mq.height,
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [_joviNavy, _joviNavyDark],
        ),
      ),
      child: SafeArea(
        top: false,
        child: FadeTransition(
          opacity: _fadeAnim,
          child: Column(
            children: [
              _buildFullHeader(),
              Expanded(child: _buildFullBody()),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildFullHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(8, 14, 16, 10),
      child: Row(
        children: [
          // Back button — lets users exit the full-page weight alerts view.
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
                    Icons.arrow_back_rounded,
                    color: Colors.white.withOpacity(0.85),
                    size: 18,
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(width: 10),
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [_joviGold, _joviGoldDark],
              ),
              borderRadius: BorderRadius.circular(11),
              boxShadow: [
                BoxShadow(
                  color: _joviGold.withOpacity(0.35),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: const Icon(
              Icons.monitor_weight_rounded,
              color: _joviNavy,
              size: 20,
            ),
          ),
          const SizedBox(width: 10),
          const Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'Weight Alerts',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 17,
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.4,
                    height: 1.1,
                  ),
                ),
                SizedBox(height: 1),
                Text(
                  'From your vet visits',
                  style: TextStyle(
                    color: Color(0x88FFFFFF),
                    fontSize: 10.5,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0.1,
                  ),
                ),
              ],
            ),
          ),
          if (_dismissedAlerts.isNotEmpty)
            _PressableMaterial(
              child: InkWell(
                onTap: () {
                  HapticFeedback.lightImpact();
                  setState(() => _showDismissed = !_showDismissed);
                },
                borderRadius: BorderRadius.circular(10),
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.06),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: Colors.white.withOpacity(0.12),
                      width: 0.8,
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        _showDismissed
                            ? Icons.visibility_off_rounded
                            : Icons.history_rounded,
                        color: Colors.white.withOpacity(0.8),
                        size: 13,
                      ),
                      const SizedBox(width: 5),
                      Text(
                        _showDismissed ? 'Hide past' : 'Show past',
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.8),
                          fontSize: 11.5,
                          fontWeight: FontWeight.w700,
                          letterSpacing: -0.2,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildFullBody() {
    if (_alertsLoading) {
      return const Center(
        child: SizedBox(
          width: 28,
          height: 28,
          child: CircularProgressIndicator(
            strokeWidth: 2.5,
            valueColor: AlwaysStoppedAnimation<Color>(_joviGold),
          ),
        ),
      );
    }
    // If the user has no pets at all, show the unified no-pets state
    // that matches Pet Profiles / Vaccinations / etc. In this situation
    // weight alerts can never exist, so the celebratory "No alerts" message
    // would be misleading.
    if (_petsLoaded && _petsById.isEmpty) {
      return _buildNoPetsState();
    }
    // On transient load errors, also fall through to the no-pets state —
    // the useful actions (add a pet, go back) are the same.
    if (_alertsError != null) {
      return _buildNoPetsState();
    }
    final visible = _visibleAlerts;
    if (visible.isEmpty) {
      return _buildEmptyState();
    }

    return ListView.separated(
      padding: const EdgeInsets.fromLTRB(14, 6, 14, 24),
      itemCount: visible.length,
      separatorBuilder: (_, __) => const SizedBox(height: 12),
      itemBuilder: (ctx, i) => _buildFullCard(visible[i]),
    );
  }

  /// Unified "no pets" state — matches the design language of Pet Profiles,
  /// Pet Vaccinations, and the other pet widgets. Shown when the user has
  /// no pets at all (or when load fails — the useful actions are the same).
  Widget _buildNoPetsState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 82,
              height: 82,
              decoration: BoxDecoration(
                color: _petAccent.withOpacity(0.12),
                borderRadius: BorderRadius.circular(22),
                border: Border.all(
                  color: _petAccent.withOpacity(0.3),
                  width: 1,
                ),
              ),
              child: const Icon(
                Icons.pets_rounded,
                color: _petAccent,
                size: 38,
              ),
            ),
            const SizedBox(height: 20),
            const Text(
              "We noticed you don't have any pets",
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.w800,
                letterSpacing: -0.3,
                height: 1.35,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              'Add a pet now to start tracking weight trends and get alerts from vet visits.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white.withOpacity(0.6),
                fontSize: 13.5,
                fontWeight: FontWeight.w500,
                height: 1.5,
              ),
            ),
            const SizedBox(height: 24),
            _PressableMaterial(
              child: InkWell(
                onTap: _openPetProfilesRoute,
                borderRadius: BorderRadius.circular(13),
                child: Semantics(
                  label: 'Add a pet',
                  button: true,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 22, vertical: 13),
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [_petAccent, _petAccentDark],
                      ),
                      borderRadius: BorderRadius.circular(13),
                      boxShadow: [
                        BoxShadow(
                          color: _petAccent.withOpacity(0.4),
                          blurRadius: 16,
                          offset: const Offset(0, 5),
                        ),
                      ],
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.add_rounded, color: Colors.white, size: 17),
                        SizedBox(width: 7),
                        Text(
                          'Add a pet',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 14,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 0.1,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 12),
            _PressableMaterial(
              child: InkWell(
                onTap: () {
                  if (Navigator.of(context).canPop()) {
                    Navigator.of(context).pop();
                  }
                },
                borderRadius: BorderRadius.circular(10),
                child: Padding(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                  child: Text(
                    'Back',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.55),
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      decoration: TextDecoration.underline,
                      decorationColor: Colors.white.withOpacity(0.35),
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Navigate to Pet Profiles so user can add a pet.
  void _openPetProfilesRoute() {
    const routes = ['petPro', 'petProfiles', 'PetProfiles', 'pet_profiles'];
    for (final r in routes) {
      try {
        final path = r.startsWith('/') ? r : '/$r';
        context.push(path);
        return;
      } catch (_) {
        continue;
      }
    }
  }

  Widget _buildEmptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                color: _joviMint.withOpacity(0.1),
                shape: BoxShape.circle,
                border: Border.all(
                  color: _joviMint.withOpacity(0.3),
                  width: 1,
                ),
              ),
              child: const Icon(
                Icons.check_circle_outline_rounded,
                color: _joviMint,
                size: 32,
              ),
            ),
            const SizedBox(height: 18),
            const Text(
              'No weight alerts',
              style: TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.w800,
                color: Colors.white,
                letterSpacing: -0.3,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              "When your vet logs a weight that's above the healthy range for your pet's breed, it'll show up here with guidance.",
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 13,
                color: Colors.white.withOpacity(0.55),
                fontWeight: FontWeight.w500,
                height: 1.4,
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ignore: unused_element
  Widget _buildErrorState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_off_rounded, color: _joviErrorRed, size: 32),
            const SizedBox(height: 10),
            Text(
              _alertsError!,
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white.withOpacity(0.7),
                fontSize: 13,
                fontWeight: FontWeight.w600,
                height: 1.4,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFullCard(_WeightAlert alert) {
    final isOver = alert.lbsOver > 0;
    final accent = alert.dismissed
        ? Colors.white.withOpacity(0.5)
        : (isOver ? _joviGold : _joviMint);
    return _PressableMaterial(
      child: InkWell(
        onTap: () => _showAlertDetail(alert),
        borderRadius: BorderRadius.circular(16),
        child: _glassCard(
          bgOpacity: alert.dismissed ? 0.04 : 0.08,
          borderOpacity: alert.dismissed ? 0.1 : 0.3,
          borderWidth: 1,
          padding: const EdgeInsets.all(14),
          radius: 16,
          borderTint: accent,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                children: [
                  _petAvatarOrIcon(alert, size: 44),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          alert.petName,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 15.5,
                            fontWeight: FontWeight.w800,
                            letterSpacing: -0.2,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          alert.breedDisplayName,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.55),
                            fontSize: 11.5,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                  if (alert.dismissed)
                    _pill(
                      text: 'Dismissed',
                      color: Colors.white.withOpacity(0.55),
                      icon: Icons.visibility_off_rounded,
                      iconSize: 10,
                    )
                  else
                    _pill(
                      text: 'Above Range',
                      color: _joviGold,
                      icon: Icons.trending_up_rounded,
                      iconSize: 10,
                    ),
                ],
              ),
              const SizedBox(height: 14),
              _buildWeightRangeBar(alert),
              const SizedBox(height: 10),
              Row(
                children: [
                  Icon(Icons.schedule_rounded,
                      size: 11, color: Colors.white.withOpacity(0.5)),
                  const SizedBox(width: 4),
                  Text(
                    'Logged ${_formatRelative(alert.recordedAt)}',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.55),
                      fontSize: 11.5,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  if (alert.providerName != null &&
                      alert.providerName!.isNotEmpty) ...[
                    const SizedBox(width: 8),
                    Container(
                      width: 3,
                      height: 3,
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.3),
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Flexible(
                      child: Text(
                        alert.providerName!,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.55),
                          fontSize: 11.5,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ],
                  const Spacer(),
                  Icon(Icons.chevron_right_rounded,
                      color: Colors.white.withOpacity(0.4), size: 18),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// Visual bar showing healthy range with a marker for the pet's weight.
  Widget _buildWeightRangeBar(_WeightAlert alert) {
    // Scale the bar from 0 to ~1.5× threshold (or pet weight, whichever higher)
    final rangeMax = math.max(alert.thresholdLbs * 1.4, alert.weightLbs * 1.1);
    final rangeMin = math.max(0.0, alert.healthyLowLbs * 0.5);
    final totalRange = rangeMax - rangeMin;
    if (totalRange <= 0) return const SizedBox.shrink();

    final healthyStart = (alert.healthyLowLbs - rangeMin) / totalRange;
    final healthyEnd = (alert.healthyHighLbs - rangeMin) / totalRange;
    final petPos = ((alert.weightLbs - rangeMin) / totalRange).clamp(0.0, 1.0);

    return LayoutBuilder(
      builder: (ctx, constraints) {
        final barW = constraints.maxWidth;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            // Labels above
            Row(
              children: [
                Text(
                  'Healthy range',
                  style: TextStyle(
                    color: _joviMint.withOpacity(0.9),
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.1,
                  ),
                ),
                const Spacer(),
                Text(
                  'Your pet',
                  style: TextStyle(
                    color: _joviGold.withOpacity(0.9),
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.1,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            // Bar
            SizedBox(
              height: 18,
              child: Stack(
                children: [
                  // Background bar
                  Positioned.fill(
                    child: Container(
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.05),
                        borderRadius: BorderRadius.circular(9),
                        border: Border.all(
                          color: Colors.white.withOpacity(0.08),
                          width: 0.8,
                        ),
                      ),
                    ),
                  ),
                  // Healthy range (mint fill)
                  Positioned(
                    left: barW * healthyStart,
                    width: barW * (healthyEnd - healthyStart),
                    top: 0,
                    bottom: 0,
                    child: Container(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: [
                            _joviMint.withOpacity(0.3),
                            _joviMint.withOpacity(0.5),
                            _joviMint.withOpacity(0.3),
                          ],
                        ),
                        borderRadius: BorderRadius.circular(9),
                      ),
                    ),
                  ),
                  // Pet position marker
                  Positioned(
                    left: (barW * petPos - 7).clamp(0.0, barW - 14),
                    top: -3,
                    bottom: -3,
                    child: Container(
                      width: 14,
                      decoration: BoxDecoration(
                        color: _joviGold,
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(
                          color: _joviNavy,
                          width: 2,
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: _joviGold.withOpacity(0.5),
                            blurRadius: 8,
                            offset: const Offset(0, 2),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 6),
            // Numeric labels below
            Row(
              children: [
                Text(
                  '${_formatLbs(alert.healthyLowLbs)}\u2013${_formatLbs(alert.healthyHighLbs)}',
                  style: TextStyle(
                    color: _joviMint.withOpacity(0.9),
                    fontSize: 11.5,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const Spacer(),
                Text(
                  _formatLbs(alert.weightLbs),
                  style: const TextStyle(
                    color: _joviGold,
                    fontSize: 13.5,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.2,
                  ),
                ),
                const SizedBox(width: 4),
                if (alert.lbsOver > 0)
                  Text(
                    '(+${_formatLbs(alert.lbsOver)})',
                    style: TextStyle(
                      color: _joviGold.withOpacity(0.75),
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
              ],
            ),
          ],
        );
      },
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // SHARED UI HELPERS
  // ═══════════════════════════════════════════════════════════════════════

  Widget _glassCard({
    required Widget child,
    double bgOpacity = 0.08,
    double borderOpacity = 0.15,
    double borderWidth = 1.2,
    EdgeInsetsGeometry? padding,
    double radius = 20,
    double blur = 16,
    Color? borderTint,
    List<BoxShadow>? shadow,
  }) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(radius),
      child: RepaintBoundary(
        child: Container(
          padding: padding ?? const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(bgOpacity + 0.02),
            borderRadius: BorderRadius.circular(radius),
            border: Border.all(
              color: (borderTint ?? Colors.white).withOpacity(borderOpacity),
              width: borderWidth,
            ),
            boxShadow: shadow ??
                [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.2),
                    blurRadius: 22,
                    offset: const Offset(0, 10),
                  ),
                ],
          ),
          child: child,
        ),
      ),
    );
  }

  Widget _pill({
    required String text,
    required Color color,
    IconData? icon,
    double iconSize = 12,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withOpacity(0.16),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3), width: 0.8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, color: color, size: iconSize),
            const SizedBox(width: 4),
          ],
          Text(
            text,
            style: TextStyle(
              color: color,
              fontSize: 11.5,
              fontWeight: FontWeight.w700,
              letterSpacing: -0.1,
            ),
          ),
        ],
      ),
    );
  }

  Widget _petAvatarOrIcon(_WeightAlert alert, {double size = 40}) {
    if (alert.petPhotoUrl != null && alert.petPhotoUrl!.isNotEmpty) {
      return ClipOval(
        child: Image.network(
          alert.petPhotoUrl!,
          width: size,
          height: size,
          fit: BoxFit.cover,
          errorBuilder: (_, __, ___) => _petAvatarFallback(size),
        ),
      );
    }
    return _petAvatarFallback(size);
  }

  Widget _petAvatarFallback(double size) {
    return Container(
      width: size,
      height: size,
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: [_petAccent, _petAccentDark],
        ),
        shape: BoxShape.circle,
      ),
      child: Icon(
        Icons.pets_rounded,
        color: Colors.white,
        size: size * 0.55,
      ),
    );
  }

  Widget _primaryButton({
    required String label,
    required VoidCallback onTap,
    IconData? icon,
    Color? accent,
    Color? accentDark,
  }) {
    final c1 = accent ?? _joviGold;
    final c2 = accentDark ?? _joviGoldDark;
    // Gold-on-navy text reads best
    final textColor =
        accent == null || accent == _joviGold ? _joviNavy : Colors.white;
    return _PressableMaterial(
      child: InkWell(
        onTap: () {
          HapticFeedback.mediumImpact();
          onTap();
        },
        borderRadius: BorderRadius.circular(14),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(vertical: 13),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [c1, c2],
            ),
            borderRadius: BorderRadius.circular(14),
            boxShadow: [
              BoxShadow(
                color: c1.withOpacity(0.4),
                blurRadius: 16,
                offset: const Offset(0, 6),
              ),
            ],
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              if (icon != null) ...[
                Icon(icon, color: textColor, size: 17),
                const SizedBox(width: 6),
              ],
              Text(
                label,
                style: TextStyle(
                  color: textColor,
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                  letterSpacing: -0.2,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _secondaryButton({
    required String label,
    required VoidCallback onTap,
    IconData? icon,
  }) {
    return _PressableMaterial(
      child: InkWell(
        onTap: () {
          HapticFeedback.lightImpact();
          onTap();
        },
        borderRadius: BorderRadius.circular(14),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.06),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: Colors.white.withOpacity(0.18),
              width: 1,
            ),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              if (icon != null) ...[
                Icon(icon, color: Colors.white, size: 16),
                const SizedBox(width: 6),
              ],
              Text(
                label,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 13.5,
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

  // ═══════════════════════════════════════════════════════════════════════
  // ALERT DETAIL SHEET
  // Full detail view when member taps an alert. Shows weight context,
  // breed health note (if any), and action buttons routing to vet request
  // + symptom checker + pet profile.
  // ═══════════════════════════════════════════════════════════════════════

  void _showAlertDetail(_WeightAlert alert) {
    HapticFeedback.lightImpact();
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => DraggableScrollableSheet(
        initialChildSize: 0.85,
        maxChildSize: 0.95,
        minChildSize: 0.5,
        expand: false,
        builder: (ctx, scrollCtrl) => ClipRRect(
          borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
          child: BackdropFilter(
            filter: ui_dart.ImageFilter.blur(sigmaX: 20, sigmaY: 20),
            child: Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    _joviNavy.withOpacity(0.97),
                    _joviNavyDark.withOpacity(0.99),
                  ],
                ),
                borderRadius:
                    const BorderRadius.vertical(top: Radius.circular(28)),
                border: Border.all(
                  color: Colors.white.withOpacity(0.1),
                  width: 1,
                ),
              ),
              child: Column(
                children: [
                  // Drag handle
                  Container(
                    margin: const EdgeInsets.only(top: 10),
                    width: 38,
                    height: 4,
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                  _buildDetailHeader(ctx, alert),
                  Expanded(
                    child: ListView(
                      controller: scrollCtrl,
                      padding: const EdgeInsets.fromLTRB(20, 4, 20, 20),
                      children: [
                        _buildDetailHeroCard(alert),
                        const SizedBox(height: 14),
                        _buildDetailRangeCard(alert),
                        if (alert.healthNote != null &&
                            alert.healthNote!.isNotEmpty) ...[
                          const SizedBox(height: 14),
                          _buildHealthNoteCard(alert),
                        ],
                        const SizedBox(height: 14),
                        _buildWhatThisMeansCard(alert),
                        const SizedBox(height: 14),
                        _buildRecordDetailsCard(alert),
                        const SizedBox(height: 20),
                        _buildDetailActions(ctx, alert),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildDetailHeader(BuildContext ctx, _WeightAlert alert) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 12, 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _petAvatarOrIcon(alert, size: 48),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  alert.petName,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.4,
                    height: 1.2,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  alert.breedDisplayName,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.6),
                    fontSize: 12.5,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
          _PressableMaterial(
            child: InkWell(
              onTap: () => Navigator.pop(ctx),
              borderRadius: BorderRadius.circular(12),
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(Icons.close, color: Colors.white, size: 18),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDetailHeroCard(_WeightAlert alert) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            _joviGold.withOpacity(0.22),
            _joviGold.withOpacity(0.08),
          ],
        ),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: _joviGold.withOpacity(0.4),
          width: 1.2,
        ),
        boxShadow: [
          BoxShadow(
            color: _joviGold.withOpacity(0.2),
            blurRadius: 18,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Column(
        children: [
          Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: _joviGold.withOpacity(0.22),
                  borderRadius: BorderRadius.circular(11),
                  border: Border.all(
                    color: _joviGold.withOpacity(0.4),
                    width: 1,
                  ),
                ),
                child: const Icon(Icons.monitor_weight_rounded,
                    color: _joviGold, size: 22),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      'Weight logged',
                      style: TextStyle(
                        color: _joviGold.withOpacity(0.9),
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        letterSpacing: -0.1,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      _formatLbs(alert.weightLbs),
                      style: const TextStyle(
                        color: _joviGold,
                        fontSize: 26,
                        fontWeight: FontWeight.w700,
                        letterSpacing: -0.6,
                      ),
                    ),
                  ],
                ),
              ),
              if (alert.lbsOver > 0)
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: _joviGold.withOpacity(0.22),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: _joviGold.withOpacity(0.35),
                      width: 0.8,
                    ),
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.arrow_upward_rounded,
                              color: _joviGold, size: 12),
                          const SizedBox(width: 2),
                          Text(
                            _formatLbs(alert.lbsOver),
                            style: const TextStyle(
                              color: _joviGold,
                              fontSize: 13,
                              fontWeight: FontWeight.w700,
                              letterSpacing: -0.2,
                            ),
                          ),
                        ],
                      ),
                      Text(
                        'over',
                        style: TextStyle(
                          color: _joviGold.withOpacity(0.75),
                          fontSize: 9.5,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
          if (alert.providerName != null && alert.providerName!.isNotEmpty) ...[
            const SizedBox(height: 14),
            Container(height: 1, color: Colors.white.withOpacity(0.08)),
            const SizedBox(height: 12),
            Row(
              children: [
                Icon(Icons.local_hospital_rounded,
                    size: 13, color: Colors.white.withOpacity(0.55)),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    'Recorded by ${alert.providerName!}${alert.clinicName != null && alert.clinicName!.isNotEmpty ? ' at ${alert.clinicName}' : ''}',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.7),
                      fontSize: 11.5,
                      fontWeight: FontWeight.w600,
                      height: 1.3,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildDetailRangeCard(_WeightAlert alert) {
    return _glassCard(
      bgOpacity: 0.06,
      borderOpacity: 0.12,
      borderWidth: 1,
      padding: const EdgeInsets.all(16),
      radius: 16,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            'Healthy range for breed',
            style: TextStyle(
              color: _joviMint.withOpacity(0.9),
              fontSize: 13,
              fontWeight: FontWeight.w600,
              letterSpacing: -0.1,
            ),
          ),
          const SizedBox(height: 12),
          _buildWeightRangeBar(alert),
          const SizedBox(height: 14),
          Text(
            "Typical adult ${alert.breedDisplayName.toLowerCase()} weight is around ${_formatLbs(alert.breedMeanLbs)}, and most healthy pets fall within ${_formatLbs(alert.healthyLowLbs)}–${_formatLbs(alert.healthyHighLbs)}.",
            style: TextStyle(
              color: Colors.white.withOpacity(0.7),
              fontSize: 12.5,
              fontWeight: FontWeight.w500,
              height: 1.45,
            ),
          ),
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.04),
              borderRadius: BorderRadius.circular(9),
              border: Border.all(
                color: Colors.white.withOpacity(0.08),
                width: 0.8,
              ),
            ),
            child: Row(
              children: [
                Icon(Icons.info_outline_rounded,
                    color: Colors.white.withOpacity(0.5), size: 12),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    "Individual pets vary. Your vet is the best judge of what's healthy for your specific pet.",
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.55),
                      fontSize: 11,
                      fontWeight: FontWeight.w500,
                      height: 1.4,
                      fontStyle: FontStyle.italic,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHealthNoteCard(_WeightAlert alert) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: _joviCoral.withOpacity(0.1),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: _joviCoral.withOpacity(0.3),
          width: 1,
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: _joviCoral.withOpacity(0.18),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: _joviCoral.withOpacity(0.35),
                width: 0.8,
              ),
            ),
            child:
                const Icon(Icons.favorite_rounded, color: _joviCoral, size: 18),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'Why this matters for ${alert.breedDisplayName}s',
                  style: TextStyle(
                    color: _joviCoral,
                    fontSize: 12.5,
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.1,
                  ),
                ),
                const SizedBox(height: 5),
                Text(
                  alert.healthNote!,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.85),
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                    height: 1.45,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildWhatThisMeansCard(_WeightAlert alert) {
    return _glassCard(
      bgOpacity: 0.06,
      borderOpacity: 0.12,
      borderWidth: 1,
      padding: const EdgeInsets.all(14),
      radius: 16,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            'What to do',
            style: TextStyle(
              color: _petAccent.withOpacity(0.9),
              fontSize: 13,
              fontWeight: FontWeight.w600,
              letterSpacing: -0.1,
            ),
          ),
          const SizedBox(height: 10),
          _bulletRow(
            icon: Icons.chat_bubble_outline_rounded,
            title: 'Talk to your vet',
            body:
                "They can rule out underlying causes, recommend a safe weight-loss pace, and help you set realistic targets.",
          ),
          const SizedBox(height: 10),
          _bulletRow(
            icon: Icons.restaurant_outlined,
            title: 'Review diet with your vet',
            body:
                "Ask about portion sizes, feeding schedule, and whether a prescription diet would help. Small changes can add up.",
          ),
          const SizedBox(height: 10),
          _bulletRow(
            icon: Icons.directions_walk_rounded,
            title: 'Daily activity',
            body:
                "Regular, gentle exercise helps — especially for breeds with joint or back concerns. Your vet can advise on what's safe.",
          ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: _joviGold.withOpacity(0.08),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: _joviGold.withOpacity(0.22),
                width: 0.8,
              ),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(Icons.warning_amber_rounded,
                    color: _joviGoldDark, size: 14),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    "Don't drastically change your pet's diet on your own — rapid weight loss can cause serious health issues, especially in cats.",
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.8),
                      fontSize: 11.5,
                      fontWeight: FontWeight.w500,
                      height: 1.4,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _bulletRow({
    required IconData icon,
    required String title,
    required String body,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 30,
          height: 30,
          decoration: BoxDecoration(
            color: _petAccent.withOpacity(0.15),
            borderRadius: BorderRadius.circular(9),
            border: Border.all(
              color: _petAccent.withOpacity(0.3),
              width: 0.8,
            ),
          ),
          child: Icon(icon, color: _petAccent, size: 15),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                title,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 13.5,
                  fontWeight: FontWeight.w800,
                  letterSpacing: -0.2,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                body,
                style: TextStyle(
                  color: Colors.white.withOpacity(0.65),
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                  height: 1.4,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildRecordDetailsCard(_WeightAlert alert) {
    return _glassCard(
      bgOpacity: 0.05,
      borderOpacity: 0.1,
      borderWidth: 1,
      padding: const EdgeInsets.all(14),
      radius: 16,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            'Record details',
            style: TextStyle(
              color: Colors.white.withOpacity(0.55),
              fontSize: 13,
              fontWeight: FontWeight.w600,
              letterSpacing: -0.1,
            ),
          ),
          const SizedBox(height: 10),
          _detailRow('Date recorded',
              '${_formatShortDate(alert.recordedAt)} (${_formatRelative(alert.recordedAt)})'),
          if (alert.providerName != null && alert.providerName!.isNotEmpty)
            _detailRow('Provider', alert.providerName!),
          if (alert.clinicName != null && alert.clinicName!.isNotEmpty)
            _detailRow('Clinic', alert.clinicName!),
          _detailRow('Breed reference', alert.breedDisplayName),
          _detailRow('Breed average',
              '${_formatLbs(alert.breedMeanLbs)} (±${_formatLbs(alert.breedStdDev)})'),
          _detailRow('Alert threshold', _formatLbs(alert.thresholdLbs)),
          if (alert.dismissed && alert.dismissedAt != null)
            _detailRow('Dismissed',
                '${_formatShortDate(alert.dismissedAt!)} (${_formatRelative(alert.dismissedAt!)})'),
        ],
      ),
    );
  }

  Widget _detailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 110,
            child: Text(
              label,
              style: TextStyle(
                color: Colors.white.withOpacity(0.5),
                fontSize: 11.5,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.1,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 13,
                fontWeight: FontWeight.w700,
                height: 1.3,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDetailActions(BuildContext sheetCtx, _WeightAlert alert) {
    return Column(
      children: [
        _primaryButton(
          label: 'Schedule a Vet Visit',
          icon: Icons.local_hospital_rounded,
          onTap: () {
            Navigator.pop(sheetCtx);
            _scheduleVetVisit(alert);
          },
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: _secondaryButton(
                label: 'Open Profile',
                icon: Icons.pets_rounded,
                onTap: () {
                  Navigator.pop(sheetCtx);
                  _openPetProfile(alert);
                },
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _secondaryButton(
                label: 'Symptom Check',
                icon: Icons.psychology_rounded,
                onTap: () {
                  Navigator.pop(sheetCtx);
                  _openSymptomChecker(alert);
                },
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        if (alert.dismissed)
          _secondaryButton(
            label: 'Restore Alert',
            icon: Icons.undo_rounded,
            onTap: () {
              Navigator.pop(sheetCtx);
              _undismissAlert(alert);
            },
          )
        else
          _PressableMaterial(
            child: InkWell(
              onTap: () {
                Navigator.pop(sheetCtx);
                _dismissAlert(alert);
              },
              borderRadius: BorderRadius.circular(14),
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(vertical: 12),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.04),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: Colors.white.withOpacity(0.12),
                    width: 0.8,
                  ),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.visibility_off_outlined,
                        color: Colors.white.withOpacity(0.55), size: 14),
                    const SizedBox(width: 6),
                    Text(
                      'Dismiss this alert',
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.55),
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        letterSpacing: -0.1,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
      ],
    );
  }
}

// ─── Jovi Brand Color System ───────────────────────────────────────────────
const Color _joviCoral = Color(0xFFFF6B4A);
const Color _joviCoralLight = Color(0xFFFF8F73);
const Color _joviCoralDark = Color(0xFFE5583A);
const Color _joviNavy = Color(0xFF1A2744);
const Color _joviNavyDark = Color(0xFF0F1A2E);
const Color _joviNavyMid = Color(0xFF1F2B47);
const Color _joviMint = Color(0xFF00D4AA);
const Color _joviMintDark = Color(0xFF00B894);
const Color _joviGold = Color(0xFFFFD166);
const Color _joviGoldDark = Color(0xFFE6B84D);
const Color _joviErrorRed = Color(0xFFE53935);

// ─── Pet Accent ────────────────────────────────────────────────────────────
const Color _petAccent = Color(0xFFA78BFA);
const Color _petAccentDark = Color(0xFF8B6EE8);

// ═══════════════════════════════════════════════════════════════════════════
// ENUMS
// ═══════════════════════════════════════════════════════════════════════════

enum PetType { dog, cat, other }

PetType _petTypeParse(String? s) {
  if (s == null) return PetType.other;
  final lower = s.toLowerCase().trim();
  if (lower == 'dog') return PetType.dog;
  if (lower == 'cat') return PetType.cat;
  return PetType.other;
}

String _petTypeSerialize(PetType t) {
  if (t == PetType.dog) return 'dog';
  if (t == PetType.cat) return 'cat';
  return 'other';
}

enum _LoadErrorKind { permission, network, unknown }

_LoadErrorKind _classifyError(dynamic e) {
  final msg = e.toString().toLowerCase();
  if (msg.contains('permission-denied') || msg.contains('unauthorized')) {
    return _LoadErrorKind.permission;
  }
  if (msg.contains('unavailable') ||
      msg.contains('network') ||
      msg.contains('socketexception') ||
      msg.contains('timeout')) {
    return _LoadErrorKind.network;
  }
  return _LoadErrorKind.unknown;
}

String _friendlyErrorMessage(_LoadErrorKind kind) {
  if (kind == _LoadErrorKind.permission) {
    return "We couldn't access this data. Please sign in again.";
  }
  if (kind == _LoadErrorKind.network) {
    return 'Network hiccup. Please try again in a moment.';
  }
  return 'Something went wrong.';
}

// ═══════════════════════════════════════════════════════════════════════════
// BREED REFERENCE DATASET
//
// Mean + standard deviation in pounds for common US breeds. Where a breed
// has a meaningful sex dimorphism (Labs, Goldens, GSDs), we capture both.
// The alert threshold is: weight > mean + 1 standard deviation.
//
// Sources: AKC breed standards, Merck Veterinary Manual, Tufts published
// breed weight ranges. These are approximate for adult pets (>= 1 year for
// most small-to-medium breeds, >= 2 years for giant breeds). Use with care.
//
// Changes to this dataset should be kept in sync with the admin app and
// Cloud Function's version — or better, pull them all from a shared
// Firestore collection (`/reference/breed_weights/{breedKey}`) once the
// product grows beyond the inline dataset.
// ═══════════════════════════════════════════════════════════════════════════

class _BreedRef {
  final String breedKey; // normalized lowercase hyphenated
  final String displayName;
  final PetType species;
  final double meanLbs;
  final double stdDevLbs;
  final double? maleMeanLbs;
  final double? femaleMeanLbs;
  final String? healthNote; // optional callout for at-risk breeds

  const _BreedRef({
    required this.breedKey,
    required this.displayName,
    required this.species,
    required this.meanLbs,
    required this.stdDevLbs,
    this.maleMeanLbs,
    this.femaleMeanLbs,
    this.healthNote,
  });

  /// Threshold above which weight is considered high for this breed.
  double get thresholdLbs => meanLbs + stdDevLbs;

  /// Healthy range lower bound (mean - 1 SD, floored at 0).
  double get healthyLowLbs => math.max(0, meanLbs - stdDevLbs);

  /// Healthy range upper bound (mean + 1 SD).
  double get healthyHighLbs => meanLbs + stdDevLbs;
}

// Canonical breed catalog. Keep breedKey stable — changing a key invalidates
// existing alerts that referenced it.
const List<_BreedRef> _breedRefs = [
  // DOGS ──────────────────────────────────────────────────────────────────
  _BreedRef(
    breedKey: 'corgi-pembroke',
    displayName: 'Pembroke Welsh Corgi',
    species: PetType.dog,
    meanLbs: 27,
    stdDevLbs: 3,
    healthNote:
        "Corgis are prone to hip dysplasia and intervertebral disc disease (IVDD). Keeping weight in the healthy range significantly reduces joint and back strain.",
  ),
  _BreedRef(
    breedKey: 'corgi-cardigan',
    displayName: 'Cardigan Welsh Corgi',
    species: PetType.dog,
    meanLbs: 30,
    stdDevLbs: 4,
    healthNote:
        "Corgis are prone to hip dysplasia and IVDD. Staying in the healthy weight range reduces long-term joint and back strain.",
  ),
  _BreedRef(
    breedKey: 'dachshund-standard',
    displayName: 'Dachshund (Standard)',
    species: PetType.dog,
    meanLbs: 22,
    stdDevLbs: 4,
    healthNote:
        "Dachshunds have an elongated spine that makes them especially vulnerable to IVDD (slipped discs). Excess weight dramatically raises the risk of spinal injury.",
  ),
  _BreedRef(
    breedKey: 'dachshund-miniature',
    displayName: 'Dachshund (Miniature)',
    species: PetType.dog,
    meanLbs: 11,
    stdDevLbs: 2,
    healthNote:
        "Mini dachshunds are highly prone to IVDD. Even a pound or two over their healthy range significantly increases the risk of spinal issues.",
  ),
  _BreedRef(
    breedKey: 'basset-hound',
    displayName: 'Basset Hound',
    species: PetType.dog,
    meanLbs: 55,
    stdDevLbs: 8,
    healthNote:
        "Basset hounds' long backs and short legs make joint and spine issues common. Weight management is critical for mobility as they age.",
  ),
  _BreedRef(
    breedKey: 'labrador-retriever',
    displayName: 'Labrador Retriever',
    species: PetType.dog,
    meanLbs: 70,
    stdDevLbs: 9,
    maleMeanLbs: 75,
    femaleMeanLbs: 65,
    healthNote:
        "Labs are genetically predisposed to obesity (many carry the POMC gene variant). They also face high rates of hip and elbow dysplasia — weight control matters a lot.",
  ),
  _BreedRef(
    breedKey: 'golden-retriever',
    displayName: 'Golden Retriever',
    species: PetType.dog,
    meanLbs: 67,
    stdDevLbs: 8,
    maleMeanLbs: 72,
    femaleMeanLbs: 62,
    healthNote:
        "Goldens are prone to hip dysplasia and certain cancers. Keeping lean body condition has been shown to extend lifespan meaningfully in this breed.",
  ),
  _BreedRef(
    breedKey: 'german-shepherd',
    displayName: 'German Shepherd',
    species: PetType.dog,
    meanLbs: 75,
    stdDevLbs: 10,
    maleMeanLbs: 80,
    femaleMeanLbs: 65,
    healthNote:
        "GSDs have a high rate of hip and elbow dysplasia. Excess weight puts additional strain on already-vulnerable joints.",
  ),
  _BreedRef(
    breedKey: 'beagle',
    displayName: 'Beagle',
    species: PetType.dog,
    meanLbs: 23,
    stdDevLbs: 4,
    healthNote:
        "Beagles have strong food drive and are prone to obesity. Their IVDD risk climbs significantly with excess weight.",
  ),
  _BreedRef(
    breedKey: 'pug',
    displayName: 'Pug',
    species: PetType.dog,
    meanLbs: 16,
    stdDevLbs: 3,
    healthNote:
        "As a brachycephalic breed, pugs have a harder time regulating breathing. Excess weight compounds breathing problems and heat intolerance.",
  ),
  _BreedRef(
    breedKey: 'bulldog-english',
    displayName: 'English Bulldog',
    species: PetType.dog,
    meanLbs: 50,
    stdDevLbs: 6,
    healthNote:
        "Bulldogs are brachycephalic (flat-faced) and prone to breathing problems. Extra weight makes breathing harder and compounds heat intolerance.",
  ),
  _BreedRef(
    breedKey: 'bulldog-french',
    displayName: 'French Bulldog',
    species: PetType.dog,
    meanLbs: 22,
    stdDevLbs: 3,
    healthNote:
        "Frenchies are brachycephalic and prone to breathing and spinal issues (hemivertebrae). Weight management supports both.",
  ),
  _BreedRef(
    breedKey: 'chihuahua',
    displayName: 'Chihuahua',
    species: PetType.dog,
    meanLbs: 5,
    stdDevLbs: 1,
  ),
  _BreedRef(
    breedKey: 'yorkshire-terrier',
    displayName: 'Yorkshire Terrier',
    species: PetType.dog,
    meanLbs: 6,
    stdDevLbs: 1,
  ),
  _BreedRef(
    breedKey: 'shih-tzu',
    displayName: 'Shih Tzu',
    species: PetType.dog,
    meanLbs: 12,
    stdDevLbs: 2,
  ),
  _BreedRef(
    breedKey: 'pomeranian',
    displayName: 'Pomeranian',
    species: PetType.dog,
    meanLbs: 6,
    stdDevLbs: 1,
  ),
  _BreedRef(
    breedKey: 'poodle-standard',
    displayName: 'Standard Poodle',
    species: PetType.dog,
    meanLbs: 55,
    stdDevLbs: 8,
  ),
  _BreedRef(
    breedKey: 'poodle-miniature',
    displayName: 'Miniature Poodle',
    species: PetType.dog,
    meanLbs: 14,
    stdDevLbs: 2,
  ),
  _BreedRef(
    breedKey: 'poodle-toy',
    displayName: 'Toy Poodle',
    species: PetType.dog,
    meanLbs: 6,
    stdDevLbs: 1,
  ),
  _BreedRef(
    breedKey: 'boxer',
    displayName: 'Boxer',
    species: PetType.dog,
    meanLbs: 63,
    stdDevLbs: 8,
    maleMeanLbs: 68,
    femaleMeanLbs: 58,
  ),
  _BreedRef(
    breedKey: 'rottweiler',
    displayName: 'Rottweiler',
    species: PetType.dog,
    meanLbs: 100,
    stdDevLbs: 15,
    maleMeanLbs: 110,
    femaleMeanLbs: 90,
    healthNote:
        "Large breeds like Rottweilers face joint stress as they age. Lean body condition meaningfully extends healthy years.",
  ),
  _BreedRef(
    breedKey: 'doberman',
    displayName: 'Doberman Pinscher',
    species: PetType.dog,
    meanLbs: 80,
    stdDevLbs: 10,
  ),
  _BreedRef(
    breedKey: 'husky-siberian',
    displayName: 'Siberian Husky',
    species: PetType.dog,
    meanLbs: 48,
    stdDevLbs: 7,
  ),
  _BreedRef(
    breedKey: 'australian-shepherd',
    displayName: 'Australian Shepherd',
    species: PetType.dog,
    meanLbs: 50,
    stdDevLbs: 8,
  ),
  _BreedRef(
    breedKey: 'border-collie',
    displayName: 'Border Collie',
    species: PetType.dog,
    meanLbs: 40,
    stdDevLbs: 6,
  ),
  _BreedRef(
    breedKey: 'cavalier-king-charles',
    displayName: 'Cavalier King Charles Spaniel',
    species: PetType.dog,
    meanLbs: 16,
    stdDevLbs: 2,
  ),
  _BreedRef(
    breedKey: 'cocker-spaniel',
    displayName: 'Cocker Spaniel',
    species: PetType.dog,
    meanLbs: 26,
    stdDevLbs: 4,
  ),
  _BreedRef(
    breedKey: 'great-dane',
    displayName: 'Great Dane',
    species: PetType.dog,
    meanLbs: 150,
    stdDevLbs: 20,
    maleMeanLbs: 160,
    femaleMeanLbs: 135,
    healthNote:
        "Giant breeds carry joint stress their whole lives. Keeping a lean body condition is one of the strongest predictors of longevity in Great Danes.",
  ),
  // CATS ──────────────────────────────────────────────────────────────────
  _BreedRef(
    breedKey: 'domestic-shorthair',
    displayName: 'Domestic Shorthair',
    species: PetType.cat,
    meanLbs: 10,
    stdDevLbs: 2,
    healthNote:
        "Indoor cats are prone to weight gain. Excess weight significantly raises risk of diabetes, urinary issues, and joint disease.",
  ),
  _BreedRef(
    breedKey: 'domestic-longhair',
    displayName: 'Domestic Longhair',
    species: PetType.cat,
    meanLbs: 11,
    stdDevLbs: 2,
    healthNote:
        "Indoor cats are prone to weight gain. Watch for weight creeping up — it significantly raises risk of diabetes and urinary issues.",
  ),
  _BreedRef(
    breedKey: 'maine-coon',
    displayName: 'Maine Coon',
    species: PetType.cat,
    meanLbs: 15,
    stdDevLbs: 3,
    maleMeanLbs: 17,
    femaleMeanLbs: 12,
  ),
  _BreedRef(
    breedKey: 'siamese',
    displayName: 'Siamese',
    species: PetType.cat,
    meanLbs: 9,
    stdDevLbs: 2,
  ),
  _BreedRef(
    breedKey: 'persian',
    displayName: 'Persian',
    species: PetType.cat,
    meanLbs: 10,
    stdDevLbs: 2,
  ),
  _BreedRef(
    breedKey: 'ragdoll',
    displayName: 'Ragdoll',
    species: PetType.cat,
    meanLbs: 14,
    stdDevLbs: 3,
    maleMeanLbs: 17,
    femaleMeanLbs: 11,
  ),
  _BreedRef(
    breedKey: 'british-shorthair',
    displayName: 'British Shorthair',
    species: PetType.cat,
    meanLbs: 11,
    stdDevLbs: 2,
  ),
  _BreedRef(
    breedKey: 'sphynx',
    displayName: 'Sphynx',
    species: PetType.cat,
    meanLbs: 9,
    stdDevLbs: 2,
  ),
  _BreedRef(
    breedKey: 'bengal',
    displayName: 'Bengal',
    species: PetType.cat,
    meanLbs: 11,
    stdDevLbs: 2,
  ),
];

/// Attempts to find a breed reference for a given free-text breed string +
/// species. Normalizes and fuzzy-matches. Returns null if no confident match
/// (mixed breeds, unknown breeds, etc.) — safe default is no alert.
_BreedRef? _lookupBreedRef(String? breedInput, PetType species) {
  if (breedInput == null || breedInput.trim().isEmpty) return null;
  final normalized = _normalizeBreedString(breedInput);
  if (normalized.isEmpty) return null;

  // Pass 1: exact-ish match on display name or key
  for (final ref in _breedRefs) {
    if (ref.species != species) continue;
    if (ref.breedKey == normalized) return ref;
    if (_normalizeBreedString(ref.displayName) == normalized) return ref;
  }

  // Pass 2: substring / contains match (both directions)
  for (final ref in _breedRefs) {
    if (ref.species != species) continue;
    final refNorm = _normalizeBreedString(ref.displayName);
    if (normalized.contains(refNorm) || refNorm.contains(normalized)) {
      return ref;
    }
  }

  // Pass 3: strip common variant suffixes and try again
  final stripped = normalized
      .replaceAll('-mix', '')
      .replaceAll('-cross', '')
      .replaceAll('-blend', '');
  if (stripped != normalized && stripped.length >= 4) {
    for (final ref in _breedRefs) {
      if (ref.species != species) continue;
      final refNorm = _normalizeBreedString(ref.displayName);
      if (stripped.contains(refNorm) || refNorm.contains(stripped)) {
        return ref;
      }
    }
  }

  return null;
}

String _normalizeBreedString(String s) {
  return s
      .toLowerCase()
      .trim()
      .replaceAll(RegExp(r"[^a-z0-9\s-]"), '')
      .replaceAll(RegExp(r'\s+'), '-')
      .replaceAll(RegExp(r'-+'), '-');
}

// ═══════════════════════════════════════════════════════════════════════════
// DATA MODELS
// ═══════════════════════════════════════════════════════════════════════════

/// Pet view used by the alerts widget. Matches schema in other pet widgets.
class _PetLite {
  final String petId;
  final String name;
  final PetType type;
  final String? breed;
  final String? photoUrl;
  final double? weightLbs;
  final DateTime? dateOfBirth;
  final String? sex; // 'male' | 'female' | null

  const _PetLite({
    required this.petId,
    required this.name,
    this.type = PetType.other,
    this.breed,
    this.photoUrl,
    this.weightLbs,
    this.dateOfBirth,
    this.sex,
  });

  factory _PetLite.fromSubcollection(String docId, Map<String, dynamic> m) {
    DateTime? parseTs(dynamic v) {
      if (v == null) return null;
      if (v is Timestamp) return v.toDate();
      if (v is String) {
        final iso = DateTime.tryParse(v);
        if (iso != null) return iso;
        // Legacy MM/DD/YYYY from onboarding widget.
        final parts = v.split('/');
        if (parts.length == 3) {
          final mo = int.tryParse(parts[0]);
          final d = int.tryParse(parts[1]);
          final y = int.tryParse(parts[2]);
          if (mo != null && d != null && y != null) {
            try {
              return DateTime(y, mo, d);
            } catch (_) {}
          }
        }
      }
      return null;
    }

    double? asDouble(dynamic v) {
      if (v == null) return null;
      if (v is num) return v.toDouble();
      if (v is String) return double.tryParse(v);
      return null;
    }

    return _PetLite(
      petId: (m['petId'] as String?) ?? docId,
      name: (m['name'] as String?)?.trim().isNotEmpty == true
          ? (m['name'] as String).trim()
          : 'Unnamed pet',
      type: _petTypeParse(m['type'] as String?),
      breed: (m['breed'] as String?)?.trim(),
      photoUrl: (m['photoUrl'] as String?) ?? (m['photo_url'] as String?),
      weightLbs: asDouble(m['weightLbs'] ?? m['weight'] ?? m['weight_lbs']),
      dateOfBirth: parseTs(
          m['dateOfBirth'] ?? m['date_of_birth'] ?? m['dob'] ?? m['birthdate']),
      sex: ((m['sex'] as String?) ?? (m['gender'] as String?))?.toLowerCase(),
    );
  }

  factory _PetLite.fromLegacyJson(Map<String, dynamic> m) {
    DateTime? parseTs(dynamic v) {
      if (v == null) return null;
      if (v is Timestamp) return v.toDate();
      if (v is String) {
        final iso = DateTime.tryParse(v);
        if (iso != null) return iso;
        // Legacy MM/DD/YYYY from onboarding widget.
        final parts = v.split('/');
        if (parts.length == 3) {
          final mo = int.tryParse(parts[0]);
          final d = int.tryParse(parts[1]);
          final y = int.tryParse(parts[2]);
          if (mo != null && d != null && y != null) {
            try {
              return DateTime(y, mo, d);
            } catch (_) {}
          }
        }
      }
      return null;
    }

    double? asDouble(dynamic v) {
      if (v == null) return null;
      if (v is num) return v.toDouble();
      if (v is String) return double.tryParse(v);
      return null;
    }

    return _PetLite(
      petId: (m['petId'] as String?) ?? (m['id'] as String?) ?? 'legacy',
      name: (m['name'] as String?)?.trim() ?? 'My pet',
      type: _petTypeParse(m['type'] as String?),
      breed: (m['breed'] as String?)?.trim(),
      photoUrl: (m['photo_url'] as String?) ?? (m['photoUrl'] as String?),
      weightLbs: asDouble(m['weightLbs'] ?? m['weight'] ?? m['weight_lbs']),
      dateOfBirth: parseTs(
          m['date_of_birth'] ?? m['dateOfBirth'] ?? m['dob'] ?? m['birthdate']),
      sex: ((m['sex'] as String?) ?? (m['gender'] as String?))?.toLowerCase(),
    );
  }
}

/// A weight log entry recorded by a vet/admin user.
/// Written by the admin app at:
///   users/{uid}/pets/{petId}/vet_weight_logs/{logId}
class _VetWeightLog {
  final String id;
  final String petId;
  final double weightLbs;
  final DateTime recordedAt;
  final String? recordedBy;
  final String? providerName;
  final String? clinicName;
  final String source; // 'vet_visit', 'admin_sync', etc.
  final double? bodyConditionScore;
  final String? notes;
  final DateTime? createdAt;

  const _VetWeightLog({
    required this.id,
    required this.petId,
    required this.weightLbs,
    required this.recordedAt,
    this.recordedBy,
    this.providerName,
    this.clinicName,
    this.source = 'vet_visit',
    this.bodyConditionScore,
    this.notes,
    this.createdAt,
  });

  factory _VetWeightLog.fromFirestore(
    String petId,
    String docId,
    Map<String, dynamic> m,
  ) {
    DateTime parseTs(dynamic v) {
      if (v is Timestamp) return v.toDate();
      if (v is String) {
        return DateTime.tryParse(v) ?? DateTime.now();
      }
      return DateTime.now();
    }

    DateTime? parseTsNullable(dynamic v) {
      if (v == null) return null;
      if (v is Timestamp) return v.toDate();
      if (v is String) return DateTime.tryParse(v);
      return null;
    }

    double asDouble(dynamic v) {
      if (v is num) return v.toDouble();
      if (v is String) return double.tryParse(v) ?? 0.0;
      return 0.0;
    }

    double? asDoubleNullable(dynamic v) {
      if (v == null) return null;
      if (v is num) return v.toDouble();
      if (v is String) return double.tryParse(v);
      return null;
    }

    return _VetWeightLog(
      id: docId,
      petId: petId,
      weightLbs: asDouble(m['weightLbs'] ?? m['weight']),
      recordedAt: parseTs(m['recordedAt'] ?? m['date']),
      recordedBy: (m['recordedBy'] as String?)?.trim(),
      providerName: (m['providerName'] as String?)?.trim(),
      clinicName: (m['clinicName'] as String?)?.trim(),
      source: (m['source'] as String?) ?? 'vet_visit',
      bodyConditionScore: asDoubleNullable(m['bodyConditionScore']),
      notes: (m['notes'] as String?)?.trim(),
      createdAt: parseTsNullable(m['createdAt']),
    );
  }
}

/// A weight alert — surfaced in-app when a vet weight exceeds the healthy
/// range for the pet's breed. Written to users/{uid}/weight_alerts/{alertId}.
/// Ideally the Cloud Function owns creation; client fallback is idempotent
/// by using the triggering logId as the alertId.
class _WeightAlert {
  final String id;
  final String logId;
  final String petId;
  final String petName;
  final String? petPhotoUrl;
  final String breedKey;
  final String breedDisplayName;
  final double weightLbs;
  final double breedMeanLbs;
  final double breedStdDev;
  final double thresholdLbs;
  final double healthyLowLbs;
  final double healthyHighLbs;
  final String? healthNote;
  final String? providerName;
  final String? clinicName;
  final DateTime recordedAt;
  final DateTime? createdAt;
  final bool dismissed;
  final DateTime? dismissedAt;

  const _WeightAlert({
    required this.id,
    required this.logId,
    required this.petId,
    required this.petName,
    this.petPhotoUrl,
    required this.breedKey,
    required this.breedDisplayName,
    required this.weightLbs,
    required this.breedMeanLbs,
    required this.breedStdDev,
    required this.thresholdLbs,
    required this.healthyLowLbs,
    required this.healthyHighLbs,
    this.healthNote,
    this.providerName,
    this.clinicName,
    required this.recordedAt,
    this.createdAt,
    this.dismissed = false,
    this.dismissedAt,
  });

  /// How many lbs above the healthy high range (mean + 1 SD) this pet is.
  double get lbsOver => weightLbs - thresholdLbs;

  /// Percentage over the healthy high.
  double get pctOverHealthy =>
      thresholdLbs <= 0 ? 0 : (lbsOver / thresholdLbs) * 100.0;

  factory _WeightAlert.fromFirestore(String docId, Map<String, dynamic> m) {
    DateTime parseTs(dynamic v) {
      if (v is Timestamp) return v.toDate();
      if (v is String) {
        return DateTime.tryParse(v) ?? DateTime.now();
      }
      return DateTime.now();
    }

    DateTime? parseTsNullable(dynamic v) {
      if (v == null) return null;
      if (v is Timestamp) return v.toDate();
      if (v is String) return DateTime.tryParse(v);
      return null;
    }

    double asDouble(dynamic v) {
      if (v is num) return v.toDouble();
      if (v is String) return double.tryParse(v) ?? 0.0;
      return 0.0;
    }

    return _WeightAlert(
      id: docId,
      logId: (m['logId'] as String?) ?? docId,
      petId: (m['petId'] as String?) ?? '',
      petName: (m['petName'] as String?)?.trim().isNotEmpty == true
          ? (m['petName'] as String).trim()
          : 'Pet',
      petPhotoUrl: (m['petPhotoUrl'] as String?),
      breedKey: (m['breedKey'] as String?) ?? '',
      breedDisplayName: (m['breedDisplayName'] as String?) ?? '',
      weightLbs: asDouble(m['weightLbs']),
      breedMeanLbs: asDouble(m['breedMeanLbs']),
      breedStdDev: asDouble(m['breedStdDev']),
      thresholdLbs: asDouble(m['threshold'] ?? m['thresholdLbs']),
      healthyLowLbs: asDouble(m['healthyLowLbs']),
      healthyHighLbs:
          asDouble(m['healthyHighLbs'] ?? m['threshold'] ?? m['thresholdLbs']),
      healthNote: (m['healthNote'] as String?),
      providerName: (m['providerName'] as String?),
      clinicName: (m['clinicName'] as String?),
      recordedAt: parseTs(m['recordedAt']),
      createdAt: parseTsNullable(m['createdAt']),
      dismissed: m['dismissed'] == true,
      dismissedAt: parseTsNullable(m['dismissedAt']),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// WEIGHT ALERT SERVICE
//
// Handles both the read side (listening for weight_alerts docs) and the
// client-side fallback write path (writing alerts when the Cloud Function
// hasn't yet processed a new vet_weight_log).
//
// Idempotency: alertId always equals the triggering logId, so running the
// client-side write twice (or racing with the Cloud Function) doesn't
// create duplicates — `set(merge: false)` overwrites harmlessly, and since
// we only write when we don't already see an alert doc, the typical race
// outcome is "one wrote, one no-op'd".
// ═══════════════════════════════════════════════════════════════════════════

class _WeightAlertService {
  final String uid;

  const _WeightAlertService._(this.uid);

  factory _WeightAlertService() {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      throw StateError('No authenticated user.');
    }
    return _WeightAlertService._(user.uid);
  }

  CollectionReference<Map<String, dynamic>> get alertsCollection =>
      FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('weight_alerts');

  CollectionReference<Map<String, dynamic>> vetLogsCollection(String petId) =>
      FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('pets')
          .doc(petId)
          .collection('vet_weight_logs');

  Future<void> dismissAlert(String alertId) async {
    await alertsCollection.doc(alertId).update({
      'dismissed': true,
      'dismissedAt': FieldValue.serverTimestamp(),
    });
  }

  Future<void> undismissAlert(String alertId) async {
    await alertsCollection.doc(alertId).update({
      'dismissed': false,
      'dismissedAt': null,
    });
  }

  /// Client-side fallback: given a pet + a fresh vet weight log, compute
  /// whether it should trigger an alert and write the alert doc. The doc
  /// is keyed by logId so duplicate invocations are idempotent.
  Future<bool> maybeCreateAlertForLog({
    required _PetLite pet,
    required _VetWeightLog log,
  }) async {
    final ref = _lookupBreedRef(pet.breed, pet.type);
    if (ref == null) return false; // unknown breed — safe default
    if (log.weightLbs <= ref.thresholdLbs) return false; // healthy range

    // Check if alert already exists (e.g. Cloud Function beat us to it)
    final existing = await alertsCollection.doc(log.id).get();
    if (existing.exists) return false;

    await alertsCollection.doc(log.id).set({
      'logId': log.id,
      'petId': pet.petId,
      'petName': pet.name,
      'petPhotoUrl': pet.photoUrl,
      'breedKey': ref.breedKey,
      'breedDisplayName': ref.displayName,
      'weightLbs': log.weightLbs,
      'breedMeanLbs': ref.meanLbs,
      'breedStdDev': ref.stdDevLbs,
      'threshold': ref.thresholdLbs,
      'thresholdLbs': ref.thresholdLbs,
      'healthyLowLbs': ref.healthyLowLbs,
      'healthyHighLbs': ref.healthyHighLbs,
      'healthNote': ref.healthNote,
      'providerName': log.providerName,
      'clinicName': log.clinicName,
      'recordedAt': Timestamp.fromDate(log.recordedAt),
      'createdAt': FieldValue.serverTimestamp(),
      'dismissed': false,
      'source': 'client_fallback',
      'schemaVersion': 1,
    });
    return true;
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// WIDGET DECLARATION
// ═══════════════════════════════════════════════════════════════════════════
