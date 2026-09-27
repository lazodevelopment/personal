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
// JOVI HEALTH — PET MEDICATION REMINDER & ADHERENCE HUB
// Version: 2026.09.22-r2 (Apple HIG pass: press feedback, painted glass,
//          Cupertino delete confirm, camera/library picker, adaptive switch,
//          title-case labels, PRN notes now saved)
// r1:      2026.04.18
// Build: JC-PETMEDS-0922-002
//
// A fork of the human MedicationReminderWidget, adapted for pet care:
//   - Per-pet medication tracking with canonical vet drug catalog
//   - Species-aware drug filtering (dogs vs cats) — critical safety
//   - Weight-based dosing hints (pet meds are mg/kg, not fixed-dose)
//   - Pet-specific interaction DB (NSAIDs, MDR1 gene, Tylenol-in-cats)
//   - Pharmacy awareness: vet dispensary / Chewy / 1-800-PetMeds
//   - Same 6 schedule types: clockTimes, meals, interval, weekly, taper, PRN
//   - Same dose event tracking + adherence metrics as human widget
//
// DATA MODEL:
// Medications live at users/{uid}/pets/{petId}/medications/{medId}
// Dose events at  users/{uid}/pets/{petId}/dose_events/{eventId}
// Pet list reads from users/{uid}/pets subcollection + legacy array
// (same dual-source pattern as Pet Vaccinations for compat with
// onboarding + profile update widgets).
//
// CRITICAL SAFETY:
// This widget ENFORCES species filtering — when a cat is selected, the
// drug picker will NOT show Tylenol, Rimadyl, Ibuprofen, etc., because
// those are fatal to cats at normal doses. The catalog marks each
// drug with a `safeFor` set. If a user types a dangerous drug by
// hand, a warning banner fires on save.
//
// DISCLAIMER:
// Veterinary medicine has more variability than human medicine:
//  - Dosing is weight-based (mg/kg) and breed-sensitive (MDR1 in Collies)
//  - Many human OTC meds are toxic at low doses for cats and some dogs
//  - Interval between doses for injectable meds varies (Cytopoint 4-6wk,
//    Convenia 14d, Bravecto 12wk)
//  - Rx fulfillment goes through vet, Chewy Pharmacy, 1-800-PetMeds,
//    or compounding pharmacies — NOT member's human CVS/Walgreens
//
// The UI shows a "confirm with your vet" hint everywhere drug data is
// surfaced, plus a one-time acceptance dialog before first use.
//
// BLOCK BEFORE PRODUCTION:
//   - Vet clinical review of the drug catalog + interaction DB
//   - Firestore security rules for users/{uid}/pets/*/medications/*
//     and .../dose_events/*
//   - Legal review of the species-safety warnings
//   - Confirm Firebase Storage rules for pet med photos
//     (path: users/{uid}/pets/{petId}/meds/{medId}.png)
// ═══════════════════════════════════════════════════════════════════════════

import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'dart:ui' as ui;
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_storage/firebase_storage.dart';
import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';
import 'package:image_picker/image_picker.dart';

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
            : _Pressable(
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

class PetMedications extends StatefulWidget {
  const PetMedications({
    super.key,
    this.width,
    this.height,
    this.petId,
  });

  final double? width;
  final double? height;

  /// If provided, auto-select this pet on open. Matches the pattern used
  /// by Pet Vaccinations when navigating from a specific pet's profile.
  final String? petId;

  @override
  State<PetMedications> createState() => _PetMedicationsState();
}

class _PetMedicationsState extends State<PetMedications>
    with TickerProviderStateMixin {
  // ─── Controllers ─────────────────────────────────────────────────────────
  late AnimationController _fadeCtrl;
  late Animation<double> _fadeAnim;
  late TextEditingController _searchController;

  // ─── UI state ────────────────────────────────────────────────────────────
  _Tab _tab = _Tab.today;
  bool _isLoading = true;
  bool _isSearching = false;
  String _searchQuery = '';
  String _medsFilter = 'all'; // all | active | prn | stopped | taper
  String _historyRange = '7d';
  String _insightsRange = '30d';

  // ─── Data ────────────────────────────────────────────────────────────────
  String? _uid;
  List<_PetLite> _pets = [];
  String? _currentPetId;
  List<PetMedication> _medications = [];
  List<DoseEvent> _doseEvents = [];
  UserPrefs _prefs = const UserPrefs();
  List<InteractionResult> _activeInteractions = [];
  bool _notifAvailable = false;

  // ─── Firestore refs for current pet ──────────────────────────────────────
  CollectionReference<Map<String, dynamic>>? _medsCol;
  CollectionReference<Map<String, dynamic>>? _doseCol;
  DocumentReference<Map<String, dynamic>>? _petDoc;
  DocumentReference<Map<String, dynamic>>? _userDoc;

  // ─── Lifecycle ──────────────────────────────────────────────────────────
  @override
  void initState() {
    super.initState();
    _fadeCtrl = AnimationController(vsync: this, duration: _Motion.select);
    _fadeAnim = CurvedAnimation(parent: _fadeCtrl, curve: Curves.easeOut);
    _searchController = TextEditingController();
    _initialize();
  }

  @override
  void dispose() {
    _fadeCtrl.dispose();
    _searchController.dispose();
    super.dispose();
  }

  // ─── Bootstrap ──────────────────────────────────────────────────────────
  Future<void> _initialize() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      if (mounted) setState(() => _isLoading = false);
      return;
    }
    _uid = user.uid;
    _userDoc = FirebaseFirestore.instance.collection('users').doc(_uid);
    _notifAvailable = await _Notify.probe(_uid);

    await _loadPets();
    _selectInitialPet();

    if (_currentPetId != null) {
      _rebindPetRefs();
      await _loadDataForCurrentPet();
    }

    if (mounted) {
      setState(() => _isLoading = false);
      if (_platformReduceMotion()) {
        _fadeCtrl.value = 1.0;
      } else {
        _fadeCtrl.forward();
      }
    }
    _checkDisclaimerAcceptance();
  }

  /// Load pets from BOTH subcollection and legacy array, dedupe by petId.
  /// Subcollection wins over legacy for any given petId. Same pattern as
  /// Pet Vaccinations for bidirectional compat with onboarding + profile
  /// update widgets.
  Future<void> _loadPets() async {
    if (_userDoc == null) return;
    final Map<String, _PetLite> byId = {};

    // 1. Subcollection (canonical)
    try {
      final sub = await _userDoc!.collection('pets').get();
      for (final d in sub.docs) {
        final pet = _PetLite.fromSubcollection(d.id, d.data());
        byId[pet.petId] = pet;
      }
    } catch (_) {}

    // 2. Legacy array (only merge in pets we didn't already see)
    try {
      final userSnap = await _userDoc!.get();
      final raw = userSnap.data()?['pets'];
      if (raw is List) {
        for (final item in raw) {
          if (item is String) {
            final legacy = _PetLite.fromLegacyJson(item);
            if (legacy != null) {
              byId.putIfAbsent(legacy.petId, () => legacy);
            }
          } else if (item is Map) {
            // Some builds may have written as map not string
            final m = Map<String, dynamic>.from(item);
            final petId = (m['petId'] as String?)?.trim();
            if (petId != null && petId.isNotEmpty) {
              byId.putIfAbsent(
                petId,
                () => _PetLite(
                  petId: petId,
                  name: (m['name'] as String?) ?? 'Unnamed pet',
                  type: _petTypeParse(m['type'] as String?),
                  breed: m['breed'] as String?,
                  photoUrl: m['photo_url'] as String?,
                ),
              );
            }
          }
        }
      }
    } catch (_) {}

    final list = byId.values.toList()
      ..sort((a, b) => a.name.toLowerCase().compareTo(b.name.toLowerCase()));
    _pets = list;
  }

  void _selectInitialPet() {
    if (_pets.isEmpty) {
      _currentPetId = null;
      return;
    }
    // Prefer widget.petId param if valid
    if (widget.petId != null && _pets.any((p) => p.petId == widget.petId)) {
      _currentPetId = widget.petId;
      return;
    }
    _currentPetId = _pets.first.petId;
  }

  void _rebindPetRefs() {
    if (_userDoc == null || _currentPetId == null) return;
    _petDoc = _userDoc!.collection('pets').doc(_currentPetId);
    _medsCol = _petDoc!.collection('medications');
    _doseCol = _petDoc!.collection('dose_events');
  }

  Future<void> _switchPet(String petId) async {
    if (petId == _currentPetId) return;
    setState(() {
      _currentPetId = petId;
      _isLoading = true;
      _medications = [];
      _doseEvents = [];
      _activeInteractions = [];
    });
    _rebindPetRefs();
    await _loadDataForCurrentPet();
    if (mounted) setState(() => _isLoading = false);
  }

  Future<void> _loadDataForCurrentPet() async {
    if (_medsCol == null || _doseCol == null || _petDoc == null) return;
    try {
      // user prefs
      final userSnap = await _userDoc!.get();
      _prefs = UserPrefs.fromMap(
          userSnap.data()?['pet_med_prefs'] as Map<String, dynamic>?);

      // medications
      final medsSnap = await _medsCol!.get();
      _medications = medsSnap.docs
          .map((d) => PetMedication.fromDoc(d.id, d.data()))
          .toList();
      _medications.sort((a, b) => a.name.compareTo(b.name));

      // dose events — 90 days
      final since = DateTime.now().subtract(const Duration(days: 90));
      final doseSnap = await _doseCol!
          .where('scheduledFor', isGreaterThan: Timestamp.fromDate(since))
          .get();
      _doseEvents =
          doseSnap.docs.map((d) => DoseEvent.fromDoc(d.id, d.data())).toList();

      await _generateDoseEvents();
      await _sweepMissedDoses();
      _recalcInteractions();
    } catch (_) {
      _medications = [];
      _doseEvents = [];
    }
  }

  // ─── Disclaimer ─────────────────────────────────────────────────────────
  Future<void> _checkDisclaimerAcceptance() async {
    if (_userDoc == null) return;
    try {
      final snap = await _userDoc!.get();
      final accepted = snap.data()?['petMedDisclaimerAcceptedAt'];
      if (accepted != null) return;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _showDisclaimerDialog();
      });
    } catch (_) {}
  }

  Future<void> _showDisclaimerDialog() async {
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      barrierColor: Colors.black.withOpacity(0.7),
      builder: (ctx) => PopScope(
        canPop: false,
        child: Dialog(
          backgroundColor: Colors.transparent,
          insetPadding: const EdgeInsets.all(22),
          child: Container(
            constraints: const BoxConstraints(maxWidth: 440),
            padding: const EdgeInsets.all(22),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  _Jovi.navy.withOpacity(0.98),
                  _Jovi.navyDark.withOpacity(0.98),
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(22),
              border: Border.all(
                color: Colors.white.withOpacity(0.14),
                width: 0.8,
              ),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      width: 42,
                      height: 42,
                      decoration: BoxDecoration(
                        gradient: _Jovi.petGradient,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Icon(
                        Icons.pets_rounded,
                        color: Colors.white,
                        size: 22,
                      ),
                    ),
                    const SizedBox(width: 12),
                    const Expanded(
                      child: Text(
                        'Before you continue',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 18),
                Text(
                  'Jovi helps you track your pet\'s medications and adherence. '
                  'It is not a substitute for veterinary care.',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.85),
                    fontSize: 13,
                    height: 1.5,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  'Pet medicine differs from human medicine: many common OTC meds '
                  '(Tylenol, Ibuprofen, Aspirin) are toxic to pets at normal doses. '
                  'Some drugs are breed-sensitive. Always follow your vet\'s directions '
                  'exactly — never start, stop, or change a dose on your own. '
                  'Fill pet prescriptions through your vet, Chewy Pharmacy, 1-800-PetMeds, '
                  'or compounding pharmacies — NOT your human pharmacy.',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.75),
                    fontSize: 12,
                    height: 1.5,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  'For suspected poisoning, call ASPCA Animal Poison Control '
                  '(888) 426-4435 or Pet Poison Helpline (855) 764-7661 immediately.',
                  style: TextStyle(
                    color: _Jovi.gold.withOpacity(0.9),
                    fontSize: 12,
                    height: 1.5,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 20),
                SizedBox(
                  width: double.infinity,
                  child: _Pressable(
                    onTap: () async {
                      try {
                        await _userDoc!.set(
                          {
                            'petMedDisclaimerAcceptedAt':
                                FieldValue.serverTimestamp(),
                            'petMedDisclaimerVersion': 1,
                          },
                          SetOptions(merge: true),
                        );
                      } catch (_) {}
                      if (ctx.mounted) Navigator.pop(ctx);
                    },
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 13),
                      decoration: BoxDecoration(
                        gradient: _Jovi.petGradient,
                        borderRadius: BorderRadius.circular(99),
                        boxShadow: [
                          BoxShadow(
                            color: _Jovi.petAccent.withOpacity(0.35),
                            blurRadius: 16,
                            offset: const Offset(0, 6),
                          ),
                        ],
                      ),
                      child: const Center(
                        child: Text(
                          'I understand',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 14,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 0.3,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // ─── Dose event generation ──────────────────────────────────────────────
  Future<void> _generateDoseEvents({bool force = false}) async {
    if (_doseCol == null || _petDoc == null) return;
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final horizon = DateTime(today.year, today.month, today.day + 7);

    if (!force) {
      try {
        final petSnap = await _petDoc!.get();
        final lastTs = petSnap.data()?['medsLastGeneratedThrough'];
        if (lastTs is Timestamp) {
          final last = lastTs.toDate();
          if (!last.isBefore(horizon)) return;
        }
      } catch (_) {}
    }

    final existing = <String, DoseEvent>{};
    for (final ev in _doseEvents) {
      existing['${ev.medicationId}|${ev.scheduledFor.toIso8601String()}'] = ev;
    }

    var batch = FirebaseFirestore.instance.batch();
    int writes = 0;
    final newEvents = <DoseEvent>[];

    final currentPet = _currentPet;

    for (final med in _medications) {
      if (!med.isActive || !med.remindersEnabled) continue;
      if (med.isAsNeeded || med.preset == SchedulePreset.prn) continue;

      var cursor = today;
      final yesterday = DateTime(today.year, today.month, today.day - 1);
      while (!cursor.isAfter(horizon)) {
        final times = _ScheduleEngine.expectedDoses(med, cursor, _prefs);
        for (final t in times) {
          if (t.isBefore(yesterday)) continue;
          final key = '${med.id}|${t.toIso8601String()}';
          if (existing.containsKey(key)) continue;
          final ref = _doseCol!.doc();
          final ev = DoseEvent(
            id: ref.id,
            medicationId: med.id,
            medicationName: med.name,
            scheduledFor: t,
            status: DoseStatus.scheduled,
          );
          batch.set(ref, ev.toMap());
          newEvents.add(ev);
          writes++;

          if (_notifAvailable &&
              _uid != null &&
              _currentPetId != null &&
              currentPet != null &&
              t.isAfter(now)) {
            _Notify.schedule(
              uid: _uid!,
              petId: _currentPetId!,
              petName: currentPet.name,
              medId: med.id,
              medName: med.name,
              dosage: med.dosage.isNotEmpty ? med.dosage : med.strength,
              fireAt: t,
              advanceMinutes: _prefs.reminderAdvanceMinutes,
            );
          }
          if (writes >= 400) {
            try {
              await batch.commit();
            } catch (_) {}
            batch = FirebaseFirestore.instance.batch();
            writes = 0;
          }
        }
        cursor = DateTime(cursor.year, cursor.month, cursor.day + 1);
      }
    }

    if (writes > 0) {
      try {
        await batch.commit();
      } catch (_) {}
    }

    try {
      await _petDoc!.set(
        {'medsLastGeneratedThrough': Timestamp.fromDate(horizon)},
        SetOptions(merge: true),
      );
    } catch (_) {}
    _doseEvents = [..._doseEvents, ...newEvents];
  }

  Future<void> _sweepMissedDoses() async {
    if (_doseCol == null) return;
    final now = DateTime.now();
    var batch = FirebaseFirestore.instance.batch();
    int writes = 0;
    for (int i = 0; i < _doseEvents.length; i++) {
      final ev = _doseEvents[i];
      if (ev.status != DoseStatus.scheduled) continue;
      if (!ev.scheduledFor.isBefore(now)) continue;
      final minutesPast = now.difference(ev.scheduledFor).inMinutes;
      if (minutesPast > 120) {
        final updated = ev.copyWith(status: DoseStatus.missed);
        batch.update(_doseCol!.doc(ev.id), {'status': DoseStatus.missed.name});
        _doseEvents[i] = updated;
        writes++;
        if (writes >= 400) {
          try {
            await batch.commit();
          } catch (_) {}
          batch = FirebaseFirestore.instance.batch();
          writes = 0;
        }
      }
    }
    if (writes > 0) {
      try {
        await batch.commit();
      } catch (_) {}
    }
  }

  void _recalcInteractions() {
    final active = _medications.where((m) => m.isActive).toList();
    _activeInteractions = InteractionCheck.scan(active);
  }

  // ─── Dose actions ───────────────────────────────────────────────────────
  Future<void> _markDoseTaken(DoseEvent ev, {bool skipped = false}) async {
    if (_doseCol == null) return;
    final currentIdx = _doseEvents.indexWhere((e) => e.id == ev.id);
    if (currentIdx >= 0 &&
        _doseEvents[currentIdx].status != DoseStatus.scheduled) {
      return;
    }
    final now = DateTime.now();
    final minutesLate = skipped ? 0 : now.difference(ev.scheduledFor).inMinutes;
    final status = skipped
        ? DoseStatus.skipped
        : (minutesLate > 30 ? DoseStatus.late : DoseStatus.taken);

    final updated = ev.copyWith(
      status: status,
      takenAt: skipped ? null : now,
      minutesLate: minutesLate.abs(),
    );

    final idx = _doseEvents.indexWhere((e) => e.id == ev.id);
    if (idx >= 0) _doseEvents[idx] = updated;

    if (!skipped) {
      final medIdx = _medications.indexWhere((m) => m.id == ev.medicationId);
      if (medIdx >= 0) {
        final med = _medications[medIdx];
        if (med.pillCount > 0) {
          final newMed = med.copyWith(pillCount: med.pillCount - 1);
          _medications[medIdx] = newMed;
          if (_medsCol != null) {
            try {
              await _medsCol!
                  .doc(med.id)
                  .update({'pillCount': newMed.pillCount});
            } catch (_) {}
          }
        }
      }
    }

    try {
      await _doseCol!.doc(ev.id).update({
        'status': status.name,
        'takenAt': skipped ? null : Timestamp.fromDate(now),
        'minutesLate': minutesLate.abs(),
      });
    } catch (_) {}

    if (mounted) setState(() {});
  }

  Future<void> _undoDose(DoseEvent ev) async {
    if (_doseCol == null) return;
    final currentIdx = _doseEvents.indexWhere((e) => e.id == ev.id);
    if (currentIdx >= 0 &&
        _doseEvents[currentIdx].status == DoseStatus.scheduled) {
      return;
    }
    final wasConsumed =
        ev.status == DoseStatus.taken || ev.status == DoseStatus.late;
    final reverted = ev.copyWith(
      status: DoseStatus.scheduled,
      takenAt: null,
      minutesLate: 0,
    );
    final idx = _doseEvents.indexWhere((e) => e.id == ev.id);
    if (idx >= 0) _doseEvents[idx] = reverted;

    if (wasConsumed) {
      final medIdx = _medications.indexWhere((m) => m.id == ev.medicationId);
      if (medIdx >= 0) {
        final med = _medications[medIdx];
        final newMed = med.copyWith(pillCount: med.pillCount + 1);
        _medications[medIdx] = newMed;
        if (_medsCol != null) {
          try {
            await _medsCol!.doc(med.id).update({'pillCount': newMed.pillCount});
          } catch (_) {}
        }
      }
    }

    try {
      await _doseCol!.doc(ev.id).update({
        'status': DoseStatus.scheduled.name,
        'takenAt': null,
        'minutesLate': 0,
      });
    } catch (_) {}

    if (mounted) setState(() {});
  }

  Future<void> _logPRN(PetMedication med, String? reason,
      {String? notes}) async {
    if (_doseCol == null) return;
    final now = DateTime.now();
    final ref = _doseCol!.doc();
    final ev = DoseEvent(
      id: ref.id,
      medicationId: med.id,
      medicationName: med.name,
      scheduledFor: now,
      takenAt: now,
      status: DoseStatus.taken,
      reason: reason,
      // The PRN sheet collected notes but never passed them on; now saved.
      notes: (notes == null || notes.trim().isEmpty) ? null : notes.trim(),
    );
    _doseEvents.add(ev);
    final idx = _medications.indexWhere((m) => m.id == med.id);
    if (idx >= 0) {
      final liveMed = _medications[idx];
      if (liveMed.pillCount > 0) {
        final updated = liveMed.copyWith(pillCount: liveMed.pillCount - 1);
        _medications[idx] = updated;
        if (_medsCol != null) {
          try {
            await _medsCol!
                .doc(liveMed.id)
                .update({'pillCount': updated.pillCount});
          } catch (_) {}
        }
      }
    }
    try {
      await ref.set(ev.toMap());
    } catch (_) {}
    if (mounted) setState(() {});
  }

  int _prnCountToday(String medId) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    return _doseEvents.where((e) {
      if (e.medicationId != medId) return false;
      if (e.status != DoseStatus.taken) return false;
      if (e.scheduledFor.isBefore(today)) return false;
      if (e.reason != null) return true;
      if (e.takenAt != null &&
          (e.takenAt!.difference(e.scheduledFor).inSeconds).abs() < 60) {
        return true;
      }
      return false;
    }).length;
  }

  DateTime? _lastPRNTime(String medId) {
    DateTime? last;
    for (final e in _doseEvents) {
      if (e.medicationId != medId) continue;
      if (e.status != DoseStatus.taken) continue;
      if (e.takenAt == null) continue;
      final isPRN = e.reason != null ||
          (e.takenAt!.difference(e.scheduledFor).inSeconds).abs() < 60;
      if (!isPRN) continue;
      if (last == null || e.takenAt!.isAfter(last)) last = e.takenAt;
    }
    return last;
  }

  // ─── Helpers / selectors ────────────────────────────────────────────────
  PetMedication? _medicationById(String id) {
    for (final m in _medications) {
      if (m.id == id) return m;
    }
    return null;
  }

  _PetLite? get _currentPet {
    if (_currentPetId == null) return null;
    for (final p in _pets) {
      if (p.petId == _currentPetId) return p;
    }
    return null;
  }

  List<DoseEvent> _eventsForDay(DateTime day) {
    final dayStart = DateTime(day.year, day.month, day.day);
    final dayEnd = DateTime(day.year, day.month, day.day + 1);
    return _doseEvents
        .where((e) =>
            !e.scheduledFor.isBefore(dayStart) &&
            e.scheduledFor.isBefore(dayEnd))
        .toList()
      ..sort((a, b) => a.scheduledFor.compareTo(b.scheduledFor));
  }

  double _adherenceRate(int days) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final start = DateTime(today.year, today.month, today.day - days);
    final relevant = _doseEvents.where((e) =>
        !e.scheduledFor.isBefore(start) &&
        e.scheduledFor.isBefore(now) &&
        e.status != DoseStatus.scheduled);
    final total = relevant.length;
    if (total == 0) return 0;
    final kept = relevant
        .where(
            (e) => e.status == DoseStatus.taken || e.status == DoseStatus.late)
        .length;
    return kept / total;
  }

  int _streakDays() {
    int streak = 0;
    int emptyDaysSeen = 0;
    var cursor = DateTime.now();
    cursor = DateTime(cursor.year, cursor.month, cursor.day);
    final hasAnyHistory = _doseEvents.any(
      (e) => e.status != DoseStatus.scheduled,
    );
    if (!hasAnyHistory) return 0;
    while (true) {
      final events = _eventsForDay(cursor)
          .where((e) => e.status != DoseStatus.scheduled)
          .toList();
      if (events.isEmpty) {
        emptyDaysSeen++;
        if (emptyDaysSeen > 14) break;
        cursor = DateTime(cursor.year, cursor.month, cursor.day - 1);
        continue;
      }
      emptyDaysSeen = 0;
      final allKept = events.every(
          (e) => e.status == DoseStatus.taken || e.status == DoseStatus.late);
      if (!allKept) break;
      streak++;
      cursor = DateTime(cursor.year, cursor.month, cursor.day - 1);
      if (streak > 365) break;
    }
    return streak;
  }

  List<MapEntry<String, int>> _topMissed(int days) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final start = DateTime(today.year, today.month, today.day - days);
    final counts = <String, int>{};
    for (final e in _doseEvents) {
      if (e.scheduledFor.isBefore(start)) continue;
      if (e.status != DoseStatus.missed) continue;
      counts[e.medicationName] = (counts[e.medicationName] ?? 0) + 1;
    }
    final list = counts.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    return list.take(5).toList();
  }

  int _dueNowCount() {
    final now = DateTime.now();
    final cutoff = now.add(const Duration(hours: 2));
    return _doseEvents
        .where((e) =>
            e.status == DoseStatus.scheduled &&
            !e.scheduledFor
                .isBefore(now.subtract(const Duration(minutes: 30))) &&
            e.scheduledFor.isBefore(cutoff))
        .length;
  }

  // ─── CRUD ───────────────────────────────────────────────────────────────
  Future<void> _saveMedication(PetMedication med) async {
    if (_medsCol == null) return;
    try {
      await _medsCol!.doc(med.id).set(med.toMap());
      final idx = _medications.indexWhere((m) => m.id == med.id);
      if (idx >= 0) {
        _medications[idx] = med;
      } else {
        _medications.add(med);
      }
      _medications.sort((a, b) => a.name.compareTo(b.name));
      _recalcInteractions();
      await _generateDoseEvents(force: true);
    } catch (_) {}
    if (mounted) setState(() {});
  }

  Future<void> _deleteMedication(String medId) async {
    if (_medsCol == null) return;
    try {
      await _medsCol!.doc(medId).delete();
      if (_uid != null) await _Notify.clearForMed(uid: _uid!, medId: medId);
      if (_doseCol != null) {
        final future = await _doseCol!
            .where('medicationId', isEqualTo: medId)
            .where('status', isEqualTo: DoseStatus.scheduled.name)
            .get();
        final batch = FirebaseFirestore.instance.batch();
        for (final d in future.docs) {
          batch.delete(d.reference);
        }
        await batch.commit();
      }
    } catch (_) {}
    _medications.removeWhere((m) => m.id == medId);
    _doseEvents.removeWhere(
        (e) => e.medicationId == medId && e.status == DoseStatus.scheduled);
    _recalcInteractions();
    if (mounted) setState(() {});
  }

  Future<void> _stopMedication(String medId) async {
    final idx = _medications.indexWhere((m) => m.id == medId);
    if (idx < 0 || _medsCol == null) return;
    final updated = _medications[idx].copyWith(stopDate: DateTime.now());
    _medications[idx] = updated;
    try {
      await _medsCol!.doc(medId).update({
        'stopDate': Timestamp.fromDate(updated.stopDate!),
      });
      if (_uid != null) await _Notify.clearForMed(uid: _uid!, medId: medId);
    } catch (_) {}
    _recalcInteractions();
    if (mounted) setState(() {});
  }

  Future<void> _resumeMedication(String medId) async {
    final idx = _medications.indexWhere((m) => m.id == medId);
    if (idx < 0 || _medsCol == null) return;
    final updated = _medications[idx].copyWith(clearStopDate: true);
    _medications[idx] = updated;
    try {
      await _medsCol!.doc(medId).update({'stopDate': null});
    } catch (_) {}
    await _generateDoseEvents(force: true);
    if (mounted) setState(() {});
  }

  // ─── Formatting ─────────────────────────────────────────────────────────
  String _timeLabel(DateTime dt) {
    final hour12 = dt.hour == 0 ? 12 : (dt.hour > 12 ? dt.hour - 12 : dt.hour);
    final ampm = dt.hour >= 12 ? 'PM' : 'AM';
    return '$hour12:${dt.minute.toString().padLeft(2, "0")} $ampm';
  }

  String _dateLabel(DateTime dt) {
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
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final that = DateTime(dt.year, dt.month, dt.day);
    final diff = that.difference(today).inDays;
    if (diff == 0) return 'Today';
    if (diff == -1) return 'Yesterday';
    if (diff == 1) return 'Tomorrow';
    return '${months[dt.month - 1]} ${dt.day}';
  }

  String _formatRelativeTime(DateTime dt) {
    final now = DateTime.now();
    final diff = dt.difference(now);
    final future = !diff.isNegative;
    final abs = diff.abs();
    if (abs.inMinutes < 1) return 'now';
    if (abs.inMinutes < 60) {
      return future ? 'in ${abs.inMinutes} min' : '${abs.inMinutes} min ago';
    }
    if (abs.inHours < 24) {
      return future ? 'in ${abs.inHours}h' : '${abs.inHours}h ago';
    }
    if (abs.inDays < 7) {
      return future ? 'in ${abs.inDays}d' : '${abs.inDays}d ago';
    }
    return _dateLabel(dt);
  }

  ResponsiveConfig _config(BoxConstraints c) =>
      ResponsiveConfig.fromWidth(c.maxWidth);

  // ═══════════════════════════════════════════════════════════════════════
  // GLASS HELPERS & COMMON UI
  // ═══════════════════════════════════════════════════════════════════════

  Widget _glassCard({
    required Widget child,
    EdgeInsets padding = const EdgeInsets.all(16),
    double radius = 22,
    Color? tint,
    double opacity = 0.08,
    Border? border,
  }) {
    // Painted glass: cards sit in ListViews over an opaque navy gradient,
    // where a live blur is pure GPU cost.
    return ClipRRect(
      borderRadius: BorderRadius.circular(radius),
      child: RepaintBoundary(
        child: Container(
          padding: padding,
          decoration: BoxDecoration(
            color: (tint ?? Colors.white).withOpacity(opacity + 0.02),
            borderRadius: BorderRadius.circular(radius),
            border: border ??
                Border.all(
                  color: Colors.white.withOpacity(0.12),
                  width: 0.8,
                ),
          ),
          child: child,
        ),
      ),
    );
  }

  Widget _glassPill({
    required Widget child,
    EdgeInsets padding =
        const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
    Color? tint,
    double opacity = 0.1,
    VoidCallback? onTap,
  }) {
    final pill = ClipRRect(
      borderRadius: BorderRadius.circular(99),
      child: RepaintBoundary(
        child: Container(
          padding: padding,
          decoration: BoxDecoration(
            color: (tint ?? Colors.white).withOpacity(opacity),
            borderRadius: BorderRadius.circular(99),
            border: Border.all(
              color: Colors.white.withOpacity(0.14),
              width: 0.8,
            ),
          ),
          child: child,
        ),
      ),
    );
    if (onTap == null) return pill;
    return _Pressable(
      onTap: onTap,
      child: pill,
    );
  }

  Widget _petGradientIcon(IconData icon, {double size = 22}) {
    return ShaderMask(
      shaderCallback: (bounds) => _Jovi.petGradient.createShader(bounds),
      child: Icon(icon, size: size, color: Colors.white),
    );
  }

  Widget _sectionHeader({
    required String title,
    String? subtitle,
    Widget? trailing,
    EdgeInsets padding = const EdgeInsets.symmetric(horizontal: 4, vertical: 8),
  }) {
    return Padding(
      padding: padding,
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    color: Colors.white,
                    letterSpacing: 0.2,
                  ),
                ),
                if (subtitle != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    subtitle,
                    style: TextStyle(
                      fontSize: 11,
                      color: Colors.white.withOpacity(0.6),
                    ),
                  ),
                ],
              ],
            ),
          ),
          if (trailing != null) trailing,
        ],
      ),
    );
  }

  Widget _emptyState({
    required IconData icon,
    required String title,
    String? subtitle,
    Widget? action,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 40),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 72,
            height: 72,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: _Jovi.petGradient,
              boxShadow: [
                BoxShadow(
                  color: _Jovi.petAccent.withOpacity(0.35),
                  blurRadius: 24,
                  offset: const Offset(0, 8),
                ),
              ],
            ),
            child: Icon(icon, color: Colors.white, size: 32),
          ),
          const SizedBox(height: 16),
          Text(
            title,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 17,
              fontWeight: FontWeight.w700,
            ),
          ),
          if (subtitle != null) ...[
            const SizedBox(height: 6),
            Text(
              subtitle,
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white.withOpacity(0.65),
                fontSize: 13,
                height: 1.4,
              ),
            ),
          ],
          if (action != null) ...[
            const SizedBox(height: 16),
            action,
          ],
        ],
      ),
    );
  }

  Widget _statusBadge(DoseStatus s, {double fontSize = 10}) {
    final color = _Jovi.statusColor(s);
    final label = _Jovi.statusLabel(s);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withOpacity(0.18),
        borderRadius: BorderRadius.circular(99),
        border: Border.all(color: color.withOpacity(0.5), width: 0.6),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontSize: fontSize + 1,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.1,
        ),
      ),
    );
  }

  Widget _severityBadge(InteractionSeverity s, {double fontSize = 10}) {
    final color = _Jovi.severityColor(s);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withOpacity(0.18),
        borderRadius: BorderRadius.circular(99),
        border: Border.all(color: color.withOpacity(0.6), width: 0.7),
      ),
      child: Text(
        s.label,
        style: TextStyle(
          color: color,
          fontSize: fontSize,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.5,
        ),
      ),
    );
  }

  Widget _primaryButton({
    required String label,
    IconData? icon,
    VoidCallback? onTap,
    bool fullWidth = false,
    Color? tint,
  }) {
    final gradient = tint == null
        ? _Jovi.petGradient
        : LinearGradient(
            colors: [tint, tint.withOpacity(0.8)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          );
    final btn = _Pressable(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        decoration: BoxDecoration(
          gradient: gradient,
          borderRadius: BorderRadius.circular(99),
          boxShadow: [
            BoxShadow(
              color: (tint ?? _Jovi.petAccent).withOpacity(0.35),
              blurRadius: 16,
              offset: const Offset(0, 6),
            ),
          ],
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (icon != null) ...[
              Icon(icon, color: Colors.white, size: 18),
              const SizedBox(width: 8),
            ],
            Text(
              label,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 14,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.3,
              ),
            ),
          ],
        ),
      ),
    );
    return fullWidth ? SizedBox(width: double.infinity, child: btn) : btn;
  }

  Widget _secondaryButton({
    required String label,
    IconData? icon,
    VoidCallback? onTap,
    bool fullWidth = false,
    Color? color,
  }) {
    final c = color ?? Colors.white;
    final btn = _Pressable(
      onTap: onTap,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(99),
        child: RepaintBoundary(
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 11),
            decoration: BoxDecoration(
              color: c.withOpacity(0.08),
              borderRadius: BorderRadius.circular(99),
              border: Border.all(color: c.withOpacity(0.28), width: 0.8),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                if (icon != null) ...[
                  Icon(icon, color: c, size: 16),
                  const SizedBox(width: 8),
                ],
                Text(
                  label,
                  style: TextStyle(
                    color: c,
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
    return fullWidth ? SizedBox(width: double.infinity, child: btn) : btn;
  }

  Widget _sheetHandle() {
    return Center(
      child: Container(
        margin: const EdgeInsets.only(top: 8, bottom: 12),
        width: 40,
        height: 4,
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.25),
          borderRadius: BorderRadius.circular(4),
        ),
      ),
    );
  }

  void _showSnack(String msg, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(msg,
        accent: isError ? _Jovi.softRed : _Jovi.mint,
        icon: isError
            ? CupertinoIcons.exclamationmark_circle
            : CupertinoIcons.checkmark_circle,
        duration: Duration(seconds: isError ? 4 : 3)));
  }

  Future<T?> _showNavyBottomSheet<T>({
    required Widget Function(BuildContext) builder,
  }) {
    return showModalBottomSheet<T>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      barrierColor: Colors.black.withOpacity(0.55),
      builder: (ctx) {
        return SafeArea(
          top: false,
          child: Padding(
            padding: EdgeInsets.only(
              bottom: MediaQuery.of(ctx).viewInsets.bottom,
            ),
            child: ClipRRect(
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(28),
                topRight: Radius.circular(28),
              ),
              child: BackdropFilter(
                filter: ui.ImageFilter.blur(sigmaX: 30, sigmaY: 30),
                child: Container(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [
                        _Jovi.navy.withOpacity(0.98),
                        _Jovi.navyDark.withOpacity(0.98),
                      ],
                    ),
                    borderRadius: const BorderRadius.only(
                      topLeft: Radius.circular(28),
                      topRight: Radius.circular(28),
                    ),
                    border: Border(
                      top: BorderSide(
                        color: Colors.white.withOpacity(0.12),
                        width: 0.8,
                      ),
                    ),
                  ),
                  constraints: BoxConstraints(
                    maxHeight: MediaQuery.of(ctx).size.height * 0.92,
                  ),
                  child: builder(ctx),
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  Future<T?> _showNavyDialog<T>({
    required Widget Function(BuildContext) builder,
  }) {
    return showGeneralDialog<T>(
      context: context,
      barrierDismissible: true,
      barrierLabel: 'dialog',
      barrierColor: Colors.black.withOpacity(0.6),
      transitionDuration: const Duration(milliseconds: 220),
      transitionBuilder: (ctx, anim, sec, child) {
        return FadeTransition(
          opacity: anim,
          child: ScaleTransition(
            scale: Tween<double>(begin: 0.94, end: 1).animate(
              CurvedAnimation(parent: anim, curve: Curves.easeOutCubic),
            ),
            child: child,
          ),
        );
      },
      pageBuilder: (ctx, a, b) => Center(
        child: Padding(
          padding: const EdgeInsets.all(22),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(24),
            child: BackdropFilter(
              filter: ui.ImageFilter.blur(sigmaX: 30, sigmaY: 30),
              child: Material(
                color: Colors.transparent,
                child: Container(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [
                        _Jovi.navy.withOpacity(0.97),
                        _Jovi.navyDark.withOpacity(0.97),
                      ],
                    ),
                    borderRadius: BorderRadius.circular(24),
                    border: Border.all(
                      color: Colors.white.withOpacity(0.14),
                      width: 0.8,
                    ),
                  ),
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 480),
                    child: builder(ctx),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _miniLinkButton(String label, IconData icon, VoidCallback onTap) {
    return _Pressable(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: _Jovi.petAccent.withOpacity(0.15),
          borderRadius: BorderRadius.circular(99),
          border: Border.all(
            color: _Jovi.petAccent.withOpacity(0.35),
            width: 0.6,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: _Jovi.petAccent, size: 12),
            const SizedBox(width: 4),
            Text(
              label,
              style: const TextStyle(
                color: _Jovi.petAccent,
                fontSize: 10,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.3,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _infoChip({
    required IconData icon,
    required String label,
    Color? color,
  }) {
    final c = color ?? Colors.white.withOpacity(0.7);
    final bg = color == null
        ? Colors.white.withOpacity(0.08)
        : color.withOpacity(0.15);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(99),
        border: Border.all(
          color: color == null
              ? Colors.white.withOpacity(0.12)
              : color.withOpacity(0.3),
          width: 0.6,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 11, color: c),
          const SizedBox(width: 4),
          Text(
            label,
            style: TextStyle(
              color: c,
              fontSize: 10,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }

  Widget _actionRow({
    required IconData icon,
    required String label,
    required String value,
    Color? iconColor,
  }) {
    return Row(
      children: [
        Icon(
          icon,
          size: 14,
          color: iconColor ?? Colors.white.withOpacity(0.6),
        ),
        const SizedBox(width: 8),
        Text(
          label,
          style: TextStyle(
            color: Colors.white.withOpacity(0.55),
            fontSize: 12,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            value,
            textAlign: TextAlign.right,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ],
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // MAIN BUILD
  // ═══════════════════════════════════════════════════════════════════════

  @override
  Widget build(BuildContext context) {
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light,
      child: Container(
        width: widget.width ?? MediaQuery.of(context).size.width,
        height: widget.height ?? MediaQuery.of(context).size.height,
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [_Jovi.navy, _Jovi.navy, _Jovi.navyDark],
          ),
        ),
        child: Stack(
          children: [
            // Ambient pet-accent haze (top right)
            Positioned(
              top: -80,
              right: -60,
              child: Container(
                width: 280,
                height: 280,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: RadialGradient(
                    colors: [
                      _Jovi.petAccent.withOpacity(0.18),
                      _Jovi.petAccent.withOpacity(0),
                    ],
                  ),
                ),
              ),
            ),
            Positioned(
              bottom: -60,
              left: -40,
              child: Container(
                width: 260,
                height: 260,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: RadialGradient(
                    colors: [
                      _Jovi.mint.withOpacity(0.12),
                      _Jovi.mint.withOpacity(0),
                    ],
                  ),
                ),
              ),
            ),
            SafeArea(
              child: LayoutBuilder(
                builder: (context, constraints) {
                  final cfg = _config(constraints);
                  return Column(
                    children: [
                      _buildTopBar(cfg),
                      if (_isSearching) _buildSearchBar(cfg),
                      if (_pets.isNotEmpty && _currentPet != null)
                        _buildTabBar(cfg),
                      Expanded(
                        child: _isLoading
                            ? const Center(
                                child: CircularProgressIndicator(
                                  color: _Jovi.petAccent,
                                  strokeWidth: 2.5,
                                ),
                              )
                            : _pets.isEmpty
                                ? _buildNoPetsState()
                                : FadeTransition(
                                    opacity: _fadeAnim,
                                    child: _buildActiveTab(cfg),
                                  ),
                      ),
                    ],
                  );
                },
              ),
            ),
            // Floating add button
            if (!_isLoading && _currentPetId != null)
              Positioned(
                right: 16,
                bottom: 20,
                child: _Pressable(
                  onTap: () => _openAddEditSheet(null),
                  child: Container(
                    width: 56,
                    height: 56,
                    decoration: BoxDecoration(
                      gradient: _Jovi.petGradient,
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: _Jovi.petAccent.withOpacity(0.5),
                          blurRadius: 18,
                          offset: const Offset(0, 8),
                        ),
                      ],
                    ),
                    child: const Icon(
                      Icons.add_rounded,
                      color: Colors.white,
                      size: 28,
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildNoPetsState() {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: _emptyState(
        icon: Icons.pets_rounded,
        title: 'No pets yet',
        subtitle:
            'Add your first pet from Pet Profiles to start tracking medications.',
        action: _primaryButton(
          label: 'Open Pet Profiles',
          icon: Icons.open_in_new_rounded,
          onTap: () {
            // Try a few naming variants for the pet profiles route.
            // IMPORTANT: ONE attempt per route — context.push queues the
            // navigation even on misconfigured routes, so doubling up
            // causes duplicate page keys and navigator asserts.
            const routes = [
              'petPro',
              'petProfiles',
              'PetProfiles',
              'pet_profiles',
              'petprofiles',
            ];
            for (final r in routes) {
              try {
                final path = r.startsWith('/') ? r : '/$r';
                context.push(path);
                return;
              } catch (_) {
                continue;
              }
            }
            _showSnack('Could not open Pet Profiles', isError: true);
          },
        ),
      ),
    );
  }

  Widget _buildTopBar(ResponsiveConfig cfg) {
    return Padding(
      padding: EdgeInsets.fromLTRB(cfg.pad, 8, cfg.pad, 8),
      child: Row(
        children: [
          _Pressable(
            onTap: () {
              HapticFeedback.lightImpact();
              Navigator.of(context).maybePop();
            },
            child: Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.08),
                shape: BoxShape.circle,
                border: Border.all(
                  color: Colors.white.withOpacity(0.15),
                  width: 0.8,
                ),
              ),
              child: const Icon(
                Icons.arrow_back_ios_new_rounded,
                color: Colors.white,
                size: 18,
              ),
            ),
          ),
          const SizedBox(width: 12),
          const Text(
            'Pet Meds',
            style: TextStyle(
              color: Colors.white,
              fontSize: 17,
              fontWeight: FontWeight.w600,
              letterSpacing: -0.4,
            ),
          ),
          const Spacer(),
          if (_pets.length > 1)
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: _petSwitcherChip(),
            ),
          _Pressable(
            onTap: () {
              setState(() {
                _isSearching = !_isSearching;
                if (!_isSearching) {
                  _searchController.clear();
                  _searchQuery = '';
                }
              });
            },
            child: Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: _isSearching
                    ? _Jovi.petAccent.withOpacity(0.2)
                    : Colors.white.withOpacity(0.08),
                shape: BoxShape.circle,
                border: Border.all(
                  color: _isSearching
                      ? _Jovi.petAccent.withOpacity(0.4)
                      : Colors.white.withOpacity(0.15),
                  width: 0.8,
                ),
              ),
              child: Icon(
                _isSearching ? Icons.close_rounded : Icons.search_rounded,
                color: _isSearching ? _Jovi.petAccent : Colors.white,
                size: 20,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _petSwitcherChip() {
    final current = _currentPet;
    if (current == null) return const SizedBox.shrink();
    return _Pressable(
      onTap: _showPetSwitcher,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: _Jovi.petAccent.withOpacity(0.14),
          borderRadius: BorderRadius.circular(99),
          border: Border.all(
            color: _Jovi.petAccent.withOpacity(0.3),
            width: 0.8,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            _petAvatar(current, size: 22),
            const SizedBox(width: 6),
            Text(
              current.name,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 12,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(width: 4),
            Icon(
              Icons.expand_more_rounded,
              color: Colors.white.withOpacity(0.6),
              size: 16,
            ),
          ],
        ),
      ),
    );
  }

  Widget _petAvatar(_PetLite pet, {double size = 42}) {
    if (pet.photoUrl != null && pet.photoUrl!.isNotEmpty) {
      return ClipOval(
        child: Image.network(
          pet.photoUrl!,
          width: size,
          height: size,
          fit: BoxFit.cover,
          errorBuilder: (ctx, err, st) => _petAvatarFallback(pet, size),
          loadingBuilder: (ctx, child, prog) {
            if (prog == null) return child;
            return _petAvatarFallback(pet, size);
          },
        ),
      );
    }
    return _petAvatarFallback(pet, size);
  }

  Widget _petAvatarFallback(_PetLite pet, double size) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        gradient: _Jovi.petGradient,
        shape: BoxShape.circle,
      ),
      child: Icon(
        _petTypeIcon(pet.type),
        color: Colors.white,
        size: size * 0.5,
      ),
    );
  }

  Future<void> _showPetSwitcher() async {
    await _showNavyBottomSheet(
      builder: (ctx) => SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _sheetHandle(),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 4, 20, 20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Switch pet',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 17,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 12),
                  for (final p in _pets) ...[
                    _Pressable(
                      onTap: () {
                        Navigator.pop(ctx);
                        _switchPet(p.petId);
                      },
                      child: _glassCard(
                        padding: const EdgeInsets.all(12),
                        tint: p.petId == _currentPetId ? _Jovi.petAccent : null,
                        opacity: p.petId == _currentPetId ? 0.12 : 0.05,
                        child: Row(
                          children: [
                            _petAvatar(p, size: 48),
                            const SizedBox(width: 14),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    p.name,
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontSize: 15,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                  Text(
                                    '${_petTypeLabel(p.type)}${p.breed != null && p.breed!.isNotEmpty ? " • ${p.breed}" : ""}',
                                    style: TextStyle(
                                      color: Colors.white.withOpacity(0.65),
                                      fontSize: 12,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            if (p.petId == _currentPetId)
                              Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 8, vertical: 3),
                                decoration: BoxDecoration(
                                  color: Colors.white.withOpacity(0.18),
                                  borderRadius: BorderRadius.circular(99),
                                ),
                                child: const Text(
                                  'Current',
                                  style: TextStyle(
                                    color: Colors.white,
                                    fontSize: 10,
                                    fontWeight: FontWeight.w700,
                                    letterSpacing: -0.1,
                                  ),
                                ),
                              ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSearchBar(ResponsiveConfig cfg) {
    return Padding(
      padding: EdgeInsets.fromLTRB(cfg.pad, 4, cfg.pad, 8),
      child: Container(
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.08),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: Colors.white.withOpacity(0.15),
            width: 0.8,
          ),
        ),
        child: TextField(
          controller: _searchController,
          autofocus: true,
          autocorrect: false,
          textInputAction: TextInputAction.search,
          cursorColor: _Jovi.petAccent,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 14,
            fontWeight: FontWeight.w500,
          ),
          decoration: InputDecoration(
            hintText: 'Search medications, conditions, vet…',
            hintStyle: TextStyle(
              color: Colors.white.withOpacity(0.4),
              fontSize: 13,
            ),
            prefixIcon: Icon(
              Icons.search_rounded,
              color: Colors.white.withOpacity(0.5),
              size: 20,
            ),
            border: InputBorder.none,
            contentPadding: const EdgeInsets.symmetric(vertical: 12),
          ),
          onChanged: (v) {
            setState(() => _searchQuery = v);
            if (_tab != _Tab.meds) {
              setState(() => _tab = _Tab.meds);
            }
          },
        ),
      ),
    );
  }

  Widget _buildTabBar(ResponsiveConfig cfg) {
    const tabs = [_Tab.today, _Tab.meds, _Tab.history, _Tab.insights];
    const labels = ['Today', 'Meds', 'History', 'Insights'];
    const icons = [
      Icons.today_rounded,
      Icons.medication_rounded,
      Icons.history_rounded,
      Icons.insights_rounded,
    ];
    final dueNow = _dueNowCount();

    return Padding(
      padding: EdgeInsets.fromLTRB(cfg.pad, 4, cfg.pad, 10),
      child: Container(
        padding: const EdgeInsets.all(4),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.06),
          borderRadius: BorderRadius.circular(99),
          border: Border.all(
            color: Colors.white.withOpacity(0.1),
            width: 0.6,
          ),
        ),
        child: Row(
          children: [
            for (int i = 0; i < tabs.length; i++)
              Expanded(
                child: _Pressable(
                  onTap: () {
                    if (_tab == tabs[i]) return;
                    HapticFeedback.selectionClick();
                    setState(() => _tab = tabs[i]);
                    if (MediaQuery.maybeOf(context)?.disableAnimations ??
                        false) {
                      _fadeCtrl.value = 1.0;
                    } else {
                      _fadeCtrl.forward(from: 0.35);
                    }
                  },
                  child: AnimatedContainer(
                    duration: _Motion.select,
                    curve: _Motion.settle,
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    decoration: BoxDecoration(
                      gradient: _tab == tabs[i] ? _Jovi.petGradient : null,
                      borderRadius: BorderRadius.circular(99),
                      boxShadow: _tab == tabs[i]
                          ? [
                              BoxShadow(
                                color: _Jovi.petAccent.withOpacity(0.35),
                                blurRadius: 12,
                                offset: const Offset(0, 4),
                              ),
                            ]
                          : null,
                    ),
                    child: Stack(
                      clipBehavior: Clip.none,
                      alignment: Alignment.center,
                      children: [
                        Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              icons[i],
                              color: _tab == tabs[i]
                                  ? Colors.white
                                  : Colors.white.withOpacity(0.55),
                              size: 16,
                            ),
                            const SizedBox(height: 2),
                            Text(
                              labels[i],
                              style: TextStyle(
                                color: _tab == tabs[i]
                                    ? Colors.white
                                    : Colors.white.withOpacity(0.55),
                                fontSize: 10,
                                fontWeight: FontWeight.w700,
                                letterSpacing: 0.2,
                              ),
                            ),
                          ],
                        ),
                        if (tabs[i] == _Tab.today && dueNow > 0)
                          Positioned(
                            top: -4,
                            right: -4,
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 5, vertical: 1),
                              decoration: BoxDecoration(
                                color: _Jovi.errorRed,
                                borderRadius: BorderRadius.circular(99),
                                border: Border.all(
                                  color: _Jovi.navy,
                                  width: 1.5,
                                ),
                              ),
                              constraints: const BoxConstraints(
                                minWidth: 16,
                                minHeight: 16,
                              ),
                              child: Text(
                                '$dueNow',
                                textAlign: TextAlign.center,
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 9,
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
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
    );
  }

  Widget _buildActiveTab(ResponsiveConfig cfg) {
    switch (_tab) {
      case _Tab.today:
        return _buildTodayTab(cfg);
      case _Tab.meds:
        return _buildMedsTab(cfg);
      case _Tab.history:
        return _buildHistoryTab(cfg);
      case _Tab.insights:
        return _buildInsightsTab(cfg);
      default:
        return _buildTodayTab(cfg);
    }
  }

  // ═══════════════════════════════════════════════════════════════════════
  // TODAY TAB
  // ═══════════════════════════════════════════════════════════════════════

  Widget _buildTodayTab(ResponsiveConfig cfg) {
    final pet = _currentPet;
    if (pet == null) {
      return _emptyState(
        icon: Icons.pets_rounded,
        title: 'No pet selected',
        subtitle: 'Pick a pet to see their medications.',
      );
    }
    final now = DateTime.now();
    final todayEvents = _eventsForDay(now);
    final scheduledMeds = _medications
        .where((m) =>
            m.isActive && !m.isAsNeeded && m.preset != SchedulePreset.prn)
        .toList();
    final prnMeds = _medications
        .where((m) =>
            m.isActive && (m.isAsNeeded || m.preset == SchedulePreset.prn))
        .toList();

    // Check for species-safety warnings in active meds
    final warnings = <String>[];
    for (final m in _medications.where((m) => m.isActive)) {
      final w = _VetDrugDB.speciesSafetyWarning(m.name, pet.type);
      if (w != null) warnings.add('${m.name}: $w');
    }

    if (scheduledMeds.isEmpty && prnMeds.isEmpty) {
      return _emptyState(
        icon: Icons.medication_rounded,
        title: 'No medications for ${pet.name}',
        subtitle:
            'Tap the + button to add a medication and start tracking doses.',
        action: _primaryButton(
          label: 'Add Medication',
          icon: Icons.add_rounded,
          onTap: () => _openAddEditSheet(null),
        ),
      );
    }

    final upcoming = <DoseEvent>[];
    final dueNow = <DoseEvent>[];
    final missed = <DoseEvent>[];
    final taken = <DoseEvent>[];

    for (final ev in todayEvents) {
      if (ev.status == DoseStatus.taken || ev.status == DoseStatus.late) {
        taken.add(ev);
      } else if (ev.status == DoseStatus.missed ||
          ev.status == DoseStatus.skipped) {
        missed.add(ev);
      } else {
        final mins = ev.scheduledFor.difference(now).inMinutes;
        if (mins.abs() <= 30 || (mins < 0 && mins > -120)) {
          dueNow.add(ev);
        } else {
          upcoming.add(ev);
        }
      }
    }

    return ListView(
      padding: EdgeInsets.fromLTRB(cfg.pad, 8, cfg.pad, 100),
      children: [
        if (warnings.isNotEmpty) ...[
          _buildSafetyWarningBanner(warnings),
          const SizedBox(height: 12),
        ],
        _buildDailySummary(todayEvents, pet),
        const SizedBox(height: 16),
        if (dueNow.isNotEmpty) ...[
          _sectionHeader(
            title: 'Due now',
            subtitle:
                '${dueNow.length} ${dueNow.length == 1 ? "dose" : "doses"} ready to give',
          ),
          const SizedBox(height: 8),
          for (final ev in dueNow) ...[
            _buildDoseCard(ev, emphasized: true),
            const SizedBox(height: 10),
          ],
          const SizedBox(height: 8),
        ],
        if (upcoming.isNotEmpty) ...[
          _sectionHeader(title: 'Coming up', subtitle: 'Later today'),
          const SizedBox(height: 8),
          for (final ev in upcoming) ...[
            _buildDoseCard(ev),
            const SizedBox(height: 10),
          ],
          const SizedBox(height: 8),
        ],
        if (prnMeds.isNotEmpty) ...[
          _sectionHeader(title: 'As needed', subtitle: 'Log when given'),
          const SizedBox(height: 8),
          for (final med in prnMeds) ...[
            _buildPRNCard(med),
            const SizedBox(height: 10),
          ],
          const SizedBox(height: 8),
        ],
        if (taken.isNotEmpty) ...[
          _sectionHeader(
            title: 'Completed',
            subtitle:
                '${taken.length} ${taken.length == 1 ? "dose" : "doses"} today',
          ),
          const SizedBox(height: 8),
          for (final ev in taken) ...[
            _buildDoseCard(ev),
            const SizedBox(height: 10),
          ],
          const SizedBox(height: 8),
        ],
        if (missed.isNotEmpty) ...[
          _sectionHeader(
            title: 'Missed',
            subtitle: 'Skipped or missed today',
          ),
          const SizedBox(height: 8),
          for (final ev in missed) ...[
            _buildDoseCard(ev),
            const SizedBox(height: 10),
          ],
        ],
      ],
    );
  }

  // Species-safety warning banner — shown when any active med is
  // flagged as dangerous for the pet's species (e.g. Tylenol for cat)
  Widget _buildSafetyWarningBanner(List<String> warnings) {
    return _glassCard(
      padding: const EdgeInsets.all(14),
      tint: _Jovi.errorRed,
      opacity: 0.12,
      border: Border.all(
        color: _Jovi.errorRed.withOpacity(0.5),
        width: 1.2,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(
                Icons.warning_amber_rounded,
                color: _Jovi.errorRed,
                size: 20,
              ),
              const SizedBox(width: 8),
              const Expanded(
                child: Text(
                  'Species safety warning',
                  style: TextStyle(
                    color: _Jovi.errorRed,
                    fontSize: 14,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.2,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          for (final w in warnings)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Container(
                      width: 4,
                      height: 4,
                      decoration: const BoxDecoration(
                        color: _Jovi.errorRed,
                        shape: BoxShape.circle,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      w,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        height: 1.4,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          const SizedBox(height: 4),
          Text(
            'Review these with your vet. ASPCA Poison Control: (888) 426-4435',
            style: TextStyle(
              color: Colors.white.withOpacity(0.7),
              fontSize: 11,
              fontStyle: FontStyle.italic,
              height: 1.4,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDailySummary(List<DoseEvent> todayEvents, _PetLite pet) {
    final scheduled = todayEvents
        .where((e) =>
            e.status != DoseStatus.skipped &&
            (e.status == DoseStatus.scheduled ||
                e.status == DoseStatus.taken ||
                e.status == DoseStatus.late ||
                e.status == DoseStatus.missed))
        .length;
    final taken = todayEvents
        .where(
            (e) => e.status == DoseStatus.taken || e.status == DoseStatus.late)
        .length;
    final remaining =
        todayEvents.where((e) => e.status == DoseStatus.scheduled).length;
    final progress = scheduled == 0 ? 0.0 : (taken / scheduled).clamp(0.0, 1.0);
    final streak = _streakDays();
    final percentage = scheduled == 0 ? 0 : ((taken / scheduled) * 100).round();
    final now = DateTime.now();

    return _glassCard(
      padding: const EdgeInsets.all(20),
      tint: _Jovi.petAccent,
      opacity: 0.06,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _petAvatar(pet, size: 40),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _greeting(now, pet.name),
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    Text(
                      '${_petTypeLabel(pet.type)}${pet.breed != null && pet.breed!.isNotEmpty ? " • ${pet.breed}" : ""}',
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.65),
                        fontSize: 11,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
              if (streak > 0)
                _glassPill(
                  tint: _Jovi.gold,
                  opacity: 0.16,
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.local_fire_department_rounded,
                          color: _Jovi.gold, size: 14),
                      const SizedBox(width: 4),
                      Text(
                        '$streak',
                        style: const TextStyle(
                          color: _Jovi.gold,
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '$taken',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 44,
                  fontWeight: FontWeight.w800,
                  height: 1,
                ),
              ),
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Text(
                  ' / $scheduled doses',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.7),
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              const Spacer(),
              if (scheduled > 0)
                Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Text(
                    '$percentage%',
                    style: TextStyle(
                      color: _progressColor(progress),
                      fontSize: 24,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 10),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: progress,
              minHeight: 6,
              backgroundColor: Colors.white.withOpacity(0.1),
              valueColor:
                  AlwaysStoppedAnimation<Color>(_progressColor(progress)),
            ),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Icon(
                remaining > 0
                    ? Icons.schedule_rounded
                    : Icons.check_circle_rounded,
                size: 14,
                color:
                    remaining > 0 ? Colors.white.withOpacity(0.65) : _Jovi.mint,
              ),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  remaining > 0
                      ? '$remaining ${remaining == 1 ? "dose" : "doses"} remaining today'
                      : 'All doses handled for today',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.72),
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
            ],
          ),
          if (!_notifAvailable) ...[
            const SizedBox(height: 10),
            Row(
              children: [
                Icon(Icons.notifications_off_outlined,
                    size: 13, color: _Jovi.gold.withOpacity(0.8)),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    'Local reminders not enabled on device',
                    style: TextStyle(
                      color: _Jovi.gold.withOpacity(0.8),
                      fontSize: 11,
                      fontStyle: FontStyle.italic,
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

  Color _progressColor(double p) {
    if (p >= 0.9) return _Jovi.mint;
    if (p >= 0.7) return _Jovi.gold;
    if (p >= 0.4) return _Jovi.petAccent;
    return _Jovi.errorRed;
  }

  String _greeting(DateTime dt, String petName) {
    if (dt.hour < 5) return "$petName's late night";
    if (dt.hour < 12) return "$petName's morning";
    if (dt.hour < 17) return "$petName's afternoon";
    if (dt.hour < 21) return "$petName's evening";
    return "$petName tonight";
  }

  Widget _buildDoseCard(DoseEvent ev, {bool emphasized = false}) {
    final med = _medicationById(ev.medicationId);
    final now = DateTime.now();
    final isPast = ev.scheduledFor.isBefore(now);
    final isPending = ev.status == DoseStatus.scheduled;
    final isComplete =
        ev.status == DoseStatus.taken || ev.status == DoseStatus.late;
    final isMissed =
        ev.status == DoseStatus.missed || ev.status == DoseStatus.skipped;

    final Color accent = isComplete
        ? _Jovi.mint
        : (isMissed
            ? _Jovi.errorRed
            : (emphasized ? _Jovi.petAccent : _Jovi.sky));

    return _Pressable(
      onTap: () => _showDoseActionSheet(ev),
      child: _glassCard(
        padding: EdgeInsets.all(emphasized ? 14 : 12),
        tint: emphasized ? _Jovi.petAccent : null,
        opacity: emphasized ? 0.08 : 0.06,
        border: emphasized
            ? Border.all(
                color: _Jovi.petAccent.withOpacity(0.35),
                width: 1.2,
              )
            : null,
        child: Row(
          children: [
            Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                color: accent.withOpacity(0.18),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: accent.withOpacity(0.35),
                  width: 0.8,
                ),
              ),
              child: Icon(
                med?.type.icon ?? Icons.medication_rounded,
                color: accent,
                size: 20,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Flexible(
                        child: Text(
                          ev.medicationName,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 15,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                      if (med?.strength.isNotEmpty ?? false) ...[
                        const SizedBox(width: 6),
                        Text(
                          med!.strength,
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.6),
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ],
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      Icon(
                        Icons.schedule_rounded,
                        size: 11,
                        color: Colors.white.withOpacity(0.55),
                      ),
                      const SizedBox(width: 4),
                      Text(
                        _timeLabel(ev.scheduledFor),
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.75),
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
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
                          isComplete && ev.takenAt != null
                              ? 'Given ${_formatRelativeTime(ev.takenAt!)}'
                              : (isPast && isPending
                                  ? 'Was due ${_formatRelativeTime(ev.scheduledFor)}'
                                  : _formatRelativeTime(ev.scheduledFor)),
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: isPast && isPending
                                ? _Jovi.gold
                                : Colors.white.withOpacity(0.55),
                            fontSize: 11,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                    ],
                  ),
                  if (med?.dosage.isNotEmpty ?? false) ...[
                    const SizedBox(height: 4),
                    Text(
                      med!.dosage,
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.6),
                        fontSize: 11,
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(width: 8),
            if (isPending)
              _giveDoseButton(ev, emphasized: emphasized)
            else
              _statusBadge(ev.status),
          ],
        ),
      ),
    );
  }

  Widget _giveDoseButton(DoseEvent ev, {bool emphasized = false}) {
    return _Pressable(
      onTap: () => _markDoseTaken(ev),
      child: Container(
        width: 44,
        height: 44,
        decoration: BoxDecoration(
          gradient: emphasized
              ? _Jovi.petGradient
              : LinearGradient(
                  colors: [_Jovi.mint, _Jovi.mintDark],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
          shape: BoxShape.circle,
          boxShadow: [
            BoxShadow(
              color:
                  (emphasized ? _Jovi.petAccent : _Jovi.mint).withOpacity(0.35),
              blurRadius: 12,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: const Icon(Icons.check_rounded, color: Colors.white, size: 22),
      ),
    );
  }

  Widget _buildPRNCard(PetMedication med) {
    final takenToday = _prnCountToday(med.id);
    final lastTaken = _lastPRNTime(med.id);
    final now = DateTime.now();
    final hoursSinceLast =
        lastTaken == null ? null : now.difference(lastTaken).inMinutes / 60.0;
    final canTakeNow = takenToday < med.prnMaxPerDay &&
        (hoursSinceLast == null || hoursSinceLast >= med.prnMinHoursBetween);

    return _Pressable(
      onTap: canTakeNow ? () => _openPRNLogSheet(med) : null,
      child: _glassCard(
        padding: const EdgeInsets.all(12),
        tint: _Jovi.petAccent,
        opacity: 0.05,
        child: Row(
          children: [
            Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                color: _Jovi.petAccent.withOpacity(0.2),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: _Jovi.petAccent.withOpacity(0.35),
                  width: 0.8,
                ),
              ),
              child: Icon(med.type.icon, color: _Jovi.petAccent, size: 20),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Flexible(
                        child: Text(
                          med.name,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 15,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                      if (med.strength.isNotEmpty) ...[
                        const SizedBox(width: 6),
                        Text(
                          med.strength,
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.6),
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ],
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: _Jovi.petAccent.withOpacity(0.18),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: const Text(
                          'As needed',
                          style: TextStyle(
                            color: _Jovi.petAccent,
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            letterSpacing: -0.1,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        '$takenToday / ${med.prnMaxPerDay} today',
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.7),
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                  if (lastTaken != null) ...[
                    const SizedBox(height: 4),
                    Text(
                      'Last: ${_formatRelativeTime(lastTaken)}',
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.55),
                        fontSize: 11,
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(width: 8),
            if (canTakeNow)
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
                decoration: BoxDecoration(
                  gradient: _Jovi.petGradient,
                  borderRadius: BorderRadius.circular(99),
                  boxShadow: [
                    BoxShadow(
                      color: _Jovi.petAccent.withOpacity(0.3),
                      blurRadius: 10,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.add_rounded, color: Colors.white, size: 14),
                    SizedBox(width: 4),
                    Text(
                      'Log',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              )
            else
              Tooltip(
                message: takenToday >= med.prnMaxPerDay
                    ? 'Daily limit reached'
                    : 'Too soon since last dose',
                child: Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.05),
                    borderRadius: BorderRadius.circular(99),
                  ),
                  child: Icon(
                    Icons.lock_clock_rounded,
                    color: Colors.white.withOpacity(0.4),
                    size: 18,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  // ─── Dose action sheet ──────────────────────────────────────────────────
  Future<void> _showDoseActionSheet(DoseEvent ev) async {
    final med = _medicationById(ev.medicationId);
    final isPending = ev.status == DoseStatus.scheduled;
    final isMissed =
        ev.status == DoseStatus.missed || ev.status == DoseStatus.skipped;

    await _showNavyBottomSheet(
      builder: (ctx) => SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            _sheetHandle(),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 4, 20, 20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        width: 48,
                        height: 48,
                        decoration: BoxDecoration(
                          gradient: _Jovi.petGradient,
                          borderRadius: BorderRadius.circular(14),
                        ),
                        child: Icon(
                          med?.type.icon ?? Icons.medication_rounded,
                          color: Colors.white,
                          size: 24,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              ev.medicationName,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 18,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            if (med?.strength.isNotEmpty ?? false)
                              Text(
                                '${med!.strength}${med.dosage.isNotEmpty ? " • ${med.dosage}" : ""}',
                                style: TextStyle(
                                  color: Colors.white.withOpacity(0.65),
                                  fontSize: 13,
                                ),
                              ),
                          ],
                        ),
                      ),
                      _statusBadge(ev.status, fontSize: 11),
                    ],
                  ),
                  const SizedBox(height: 16),
                  _glassCard(
                    padding: const EdgeInsets.all(12),
                    opacity: 0.04,
                    child: Column(
                      children: [
                        _actionRow(
                          icon: Icons.schedule_rounded,
                          label: 'Scheduled',
                          value:
                              '${_timeLabel(ev.scheduledFor)} • ${_dateLabel(ev.scheduledFor)}',
                        ),
                        if (ev.takenAt != null) ...[
                          const SizedBox(height: 8),
                          _actionRow(
                            icon: Icons.check_circle_rounded,
                            label: 'Given',
                            value:
                                '${_timeLabel(ev.takenAt!)}${ev.minutesLate > 30 ? " (${ev.minutesLate} min late)" : ""}',
                            iconColor: _Jovi.mint,
                          ),
                        ],
                        if (ev.reason != null && ev.reason!.isNotEmpty) ...[
                          const SizedBox(height: 8),
                          _actionRow(
                            icon: Icons.note_rounded,
                            label: 'Reason',
                            value: ev.reason!,
                          ),
                        ],
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                  if (med?.instructions.isNotEmpty ?? false) ...[
                    _sectionHeader(title: 'Instructions'),
                    const SizedBox(height: 4),
                    Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: [
                        for (final inst in med!.instructions)
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 10, vertical: 5),
                            decoration: BoxDecoration(
                              color: _Jovi.mint.withOpacity(0.14),
                              borderRadius: BorderRadius.circular(99),
                              border: Border.all(
                                color: _Jovi.mint.withOpacity(0.3),
                                width: 0.6,
                              ),
                            ),
                            child: Text(
                              inst,
                              style: const TextStyle(
                                color: _Jovi.mint,
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                      ],
                    ),
                    const SizedBox(height: 16),
                  ],
                  if (isPending) ...[
                    Row(
                      children: [
                        Expanded(
                          child: _primaryButton(
                            label: 'Gave it',
                            icon: Icons.check_rounded,
                            fullWidth: true,
                            tint: _Jovi.mint,
                            onTap: () async {
                              Navigator.pop(ctx);
                              await _markDoseTaken(ev);
                              _showSnack('Dose logged');
                            },
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: _secondaryButton(
                            label: 'Skip',
                            icon: Icons.block_rounded,
                            fullWidth: true,
                            onTap: () async {
                              Navigator.pop(ctx);
                              await _markDoseTaken(ev, skipped: true);
                              _showSnack('Dose skipped');
                            },
                          ),
                        ),
                      ],
                    ),
                  ] else ...[
                    Row(
                      children: [
                        Expanded(
                          child: _secondaryButton(
                            label: 'Undo',
                            icon: Icons.undo_rounded,
                            fullWidth: true,
                            onTap: () async {
                              Navigator.pop(ctx);
                              await _undoDose(ev);
                              _showSnack('Dose reverted to scheduled');
                            },
                          ),
                        ),
                        if (isMissed) ...[
                          const SizedBox(width: 10),
                          Expanded(
                            child: _primaryButton(
                              label: 'Give now',
                              icon: Icons.check_rounded,
                              fullWidth: true,
                              tint: _Jovi.mint,
                              onTap: () async {
                                Navigator.pop(ctx);
                                await _markDoseTaken(ev);
                                _showSnack('Dose logged');
                              },
                            ),
                          ),
                        ],
                      ],
                    ),
                  ],
                  const SizedBox(height: 10),
                  if (med != null)
                    Center(
                      child: TextButton.icon(
                        onPressed: () {
                          Navigator.pop(ctx);
                          _openMedDetails(med);
                        },
                        icon: Icon(
                          Icons.info_outline_rounded,
                          size: 16,
                          color: Colors.white.withOpacity(0.6),
                        ),
                        label: Text(
                          'View medication details',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.6),
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ─── PRN log sheet ──────────────────────────────────────────────────────
  Future<void> _openPRNLogSheet(PetMedication med) async {
    String? selectedReason;
    String customReason = '';
    final reasons = [
      'Pain',
      'Anxiety',
      'Itching',
      'Nausea',
      'Seizure',
      'Motion sickness',
      'Other',
    ];
    final notesCtrl = TextEditingController();

    await _showNavyBottomSheet(
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setSheet) => SingleChildScrollView(
          padding: EdgeInsets.only(
            bottom: MediaQuery.of(ctx).viewInsets.bottom,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              _sheetHandle(),
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 4, 20, 20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          width: 48,
                          height: 48,
                          decoration: BoxDecoration(
                            gradient: _Jovi.petGradient,
                            borderRadius: BorderRadius.circular(14),
                          ),
                          child: Icon(
                            med.type.icon,
                            color: Colors.white,
                            size: 24,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Log ${med.name}',
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 18,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                              Text(
                                '${med.strength}${med.dosage.isNotEmpty ? " • ${med.dosage}" : ""}',
                                style: TextStyle(
                                  color: Colors.white.withOpacity(0.65),
                                  fontSize: 12,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 20),
                    _sectionHeader(title: 'Why?'),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        for (final r in reasons)
                          _reasonChip(
                            r,
                            selectedReason == r,
                            () => setSheet(() => selectedReason = r),
                          ),
                      ],
                    ),
                    if (selectedReason == 'Other') ...[
                      const SizedBox(height: 10),
                      Container(
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.06),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                            color: Colors.white.withOpacity(0.12),
                            width: 0.8,
                          ),
                        ),
                        child: TextField(
                          autofocus: true,
                          cursorColor: _Jovi.petAccent,
                          style: const TextStyle(color: Colors.white),
                          decoration: const InputDecoration(
                            hintText: 'Custom reason',
                            hintStyle: TextStyle(color: Colors.white38),
                            border: InputBorder.none,
                            contentPadding: EdgeInsets.symmetric(
                              horizontal: 12,
                              vertical: 10,
                            ),
                          ),
                          onChanged: (v) => customReason = v,
                        ),
                      ),
                    ],
                    const SizedBox(height: 16),
                    _sectionHeader(title: 'Notes (optional)'),
                    const SizedBox(height: 8),
                    Container(
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.06),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: Colors.white.withOpacity(0.12),
                          width: 0.8,
                        ),
                      ),
                      child: TextField(
                        controller: notesCtrl,
                        maxLines: 3,
                        textCapitalization: TextCapitalization.sentences,
                        cursorColor: _Jovi.petAccent,
                        style: const TextStyle(color: Colors.white),
                        decoration: const InputDecoration(
                          hintText:
                              'How is your pet doing? severity, trigger, etc.',
                          hintStyle: TextStyle(color: Colors.white38),
                          border: InputBorder.none,
                          contentPadding: EdgeInsets.symmetric(
                            horizontal: 12,
                            vertical: 10,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 20),
                    Row(
                      children: [
                        Expanded(
                          child: _secondaryButton(
                            label: 'Cancel',
                            fullWidth: true,
                            onTap: () => Navigator.pop(ctx),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: _primaryButton(
                            label: 'Log Dose',
                            icon: Icons.check_rounded,
                            fullWidth: true,
                            onTap: () async {
                              final reason = selectedReason == 'Other'
                                  ? (customReason.isNotEmpty
                                      ? customReason
                                      : 'Other')
                                  : selectedReason;
                              final notes = notesCtrl.text;
                              Navigator.pop(ctx);
                              await _logPRN(med, reason, notes: notes);
                              _showSnack('Dose logged');
                            },
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

    notesCtrl.dispose();
  }

  Widget _reasonChip(String label, bool selected, VoidCallback onTap) {
    return _Pressable(
      onTap: onTap,
      child: AnimatedContainer(
        duration: _Motion.select,
        curve: _Motion.settle,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
        decoration: BoxDecoration(
          gradient: selected ? _Jovi.petGradient : null,
          color: selected ? null : Colors.white.withOpacity(0.06),
          borderRadius: BorderRadius.circular(99),
          border: Border.all(
            color: selected
                ? _Jovi.petAccent.withOpacity(0.5)
                : Colors.white.withOpacity(0.14),
            width: 0.8,
          ),
          boxShadow: selected
              ? [
                  BoxShadow(
                    color: _Jovi.petAccent.withOpacity(0.3),
                    blurRadius: 10,
                    offset: const Offset(0, 3),
                  ),
                ]
              : null,
        ),
        child: Text(
          label,
          style: TextStyle(
            color: selected ? Colors.white : Colors.white.withOpacity(0.8),
            fontSize: 12,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // MEDS TAB
  // ═══════════════════════════════════════════════════════════════════════

  List<PetMedication> get _filteredMeds {
    var list = [..._medications];
    switch (_medsFilter) {
      case 'active':
        list = list.where((m) => m.isActive).toList();
        break;
      case 'prn':
        list = list
            .where((m) => m.isAsNeeded || m.preset == SchedulePreset.prn)
            .toList();
        break;
      case 'stopped':
        list = list.where((m) => !m.isActive).toList();
        break;
      case 'taper':
        list = list.where((m) => m.isTaper).toList();
        break;
      default:
        break;
    }
    if (_searchQuery.trim().isNotEmpty) {
      final q = _searchQuery.toLowerCase();
      list = list.where((m) {
        return m.name.toLowerCase().contains(q) ||
            (m.condition?.toLowerCase().contains(q) ?? false) ||
            (m.prescribedBy?.toLowerCase().contains(q) ?? false) ||
            (m.pharmacy?.toLowerCase().contains(q) ?? false) ||
            m.strength.toLowerCase().contains(q);
      }).toList();
    }
    list.sort((a, b) {
      if (a.isActive && !b.isActive) return -1;
      if (!a.isActive && b.isActive) return 1;
      return a.name.compareTo(b.name);
    });
    return list;
  }

  Widget _buildMedsTab(ResponsiveConfig cfg) {
    if (_medications.isEmpty) {
      return _emptyState(
        icon: Icons.medication_outlined,
        title: 'No medications yet',
        subtitle: 'Tap + to add your first medication.',
        action: _primaryButton(
          label: 'Add Medication',
          icon: Icons.add_rounded,
          onTap: () => _openAddEditSheet(null),
        ),
      );
    }

    final filtered = _filteredMeds;
    final activeCount = _medications.where((m) => m.isActive).length;
    final prnCount = _medications
        .where((m) => m.isAsNeeded || m.preset == SchedulePreset.prn)
        .length;
    final stoppedCount = _medications.where((m) => !m.isActive).length;
    final taperCount = _medications.where((m) => m.isTaper).length;

    return Column(
      children: [
        Padding(
          padding: EdgeInsets.fromLTRB(cfg.pad, 8, cfg.pad, 8),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                _filterChip(
                  'All',
                  _medications.length,
                  _medsFilter == 'all',
                  () => setState(() => _medsFilter = 'all'),
                ),
                const SizedBox(width: 8),
                _filterChip(
                  'Active',
                  activeCount,
                  _medsFilter == 'active',
                  () => setState(() => _medsFilter = 'active'),
                  color: _Jovi.mint,
                ),
                const SizedBox(width: 8),
                _filterChip(
                  'PRN',
                  prnCount,
                  _medsFilter == 'prn',
                  () => setState(() => _medsFilter = 'prn'),
                  color: _Jovi.petAccent,
                ),
                if (taperCount > 0) ...[
                  const SizedBox(width: 8),
                  _filterChip(
                    'Taper',
                    taperCount,
                    _medsFilter == 'taper',
                    () => setState(() => _medsFilter = 'taper'),
                    color: _Jovi.gold,
                  ),
                ],
                const SizedBox(width: 8),
                _filterChip(
                  'Stopped',
                  stoppedCount,
                  _medsFilter == 'stopped',
                  () => setState(() => _medsFilter = 'stopped'),
                  color: Colors.white54,
                ),
              ],
            ),
          ),
        ),
        Expanded(
          child: filtered.isEmpty
              ? _emptyState(
                  icon: Icons.search_off_rounded,
                  title: 'No matches',
                  subtitle: _searchQuery.isNotEmpty
                      ? 'Try a different search term'
                      : 'No medications in this filter',
                )
              : ListView.builder(
                  padding: EdgeInsets.fromLTRB(cfg.pad, 4, cfg.pad, 100),
                  itemCount: filtered.length,
                  itemBuilder: (context, i) {
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: _buildMedCard(filtered[i]),
                    );
                  },
                ),
        ),
      ],
    );
  }

  Widget _filterChip(
    String label,
    int count,
    bool selected,
    VoidCallback onTap, {
    Color? color,
  }) {
    final c = color ?? _Jovi.petAccent;
    return _Pressable(
      onTap: onTap,
      child: AnimatedContainer(
        duration: _Motion.select,
        curve: _Motion.settle,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          gradient:
              selected ? LinearGradient(colors: [c, c.withOpacity(0.8)]) : null,
          color: selected ? null : Colors.white.withOpacity(0.06),
          borderRadius: BorderRadius.circular(99),
          border: Border.all(
            color:
                selected ? c.withOpacity(0.5) : Colors.white.withOpacity(0.12),
            width: 0.8,
          ),
          boxShadow: selected
              ? [
                  BoxShadow(
                    color: c.withOpacity(0.35),
                    blurRadius: 12,
                    offset: const Offset(0, 4),
                  ),
                ]
              : null,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              label,
              style: TextStyle(
                color: selected ? Colors.white : Colors.white.withOpacity(0.75),
                fontSize: 12,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.3,
              ),
            ),
            const SizedBox(width: 6),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
              decoration: BoxDecoration(
                color: selected
                    ? Colors.white.withOpacity(0.25)
                    : Colors.white.withOpacity(0.1),
                borderRadius: BorderRadius.circular(99),
              ),
              child: Text(
                '$count',
                style: TextStyle(
                  color:
                      selected ? Colors.white : Colors.white.withOpacity(0.7),
                  fontSize: 10,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMedCard(PetMedication med) {
    final isActive = med.isActive;
    final isTaper = med.isTaper;
    final isPRN = med.isAsNeeded || med.preset == SchedulePreset.prn;
    final scheduleLabel = _ScheduleEngine.summarize(med, _prefs);
    final pet = _currentPet;
    // Is this drug dangerous for this species?
    final safetyWarning = pet == null
        ? null
        : _VetDrugDB.speciesSafetyWarning(med.name, pet.type);

    return _Pressable(
      onTap: () => _openMedDetails(med),
      child: _glassCard(
        padding: const EdgeInsets.all(14),
        opacity: isActive ? 0.06 : 0.04,
        border: safetyWarning != null
            ? Border.all(
                color: _Jovi.errorRed.withOpacity(0.5),
                width: 1.2,
              )
            : null,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                    gradient: isActive
                        ? _Jovi.petGradient
                        : LinearGradient(
                            colors: [
                              Colors.white.withOpacity(0.15),
                              Colors.white.withOpacity(0.08),
                            ],
                          ),
                    borderRadius: BorderRadius.circular(14),
                    boxShadow: isActive
                        ? [
                            BoxShadow(
                              color: _Jovi.petAccent.withOpacity(0.25),
                              blurRadius: 10,
                              offset: const Offset(0, 4),
                            ),
                          ]
                        : null,
                  ),
                  child: Icon(
                    med.type.icon,
                    color:
                        isActive ? Colors.white : Colors.white.withOpacity(0.5),
                    size: 24,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Flexible(
                            child: Text(
                              med.name,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                color: isActive
                                    ? Colors.white
                                    : Colors.white.withOpacity(0.55),
                                fontSize: 16,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                          if (med.strength.isNotEmpty) ...[
                            const SizedBox(width: 6),
                            Text(
                              med.strength,
                              style: TextStyle(
                                color: Colors.white.withOpacity(0.55),
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                          const SizedBox(width: 8),
                          if (!isActive)
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: Colors.white.withOpacity(0.12),
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: Text(
                                'Stopped',
                                style: TextStyle(
                                  color: Colors.white.withOpacity(0.6),
                                  fontSize: 10,
                                  fontWeight: FontWeight.w700,
                                  letterSpacing: -0.1,
                                ),
                              ),
                            )
                          else if (isTaper)
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: _Jovi.gold.withOpacity(0.18),
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: const Text(
                                'Taper',
                                style: TextStyle(
                                  color: _Jovi.gold,
                                  fontSize: 10,
                                  fontWeight: FontWeight.w700,
                                  letterSpacing: -0.1,
                                ),
                              ),
                            )
                          else if (isPRN)
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: _Jovi.petAccent.withOpacity(0.18),
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: const Text(
                                'As needed',
                                style: TextStyle(
                                  color: _Jovi.petAccent,
                                  fontSize: 10,
                                  fontWeight: FontWeight.w700,
                                  letterSpacing: -0.1,
                                ),
                              ),
                            ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Row(
                        children: [
                          Icon(
                            Icons.schedule_rounded,
                            size: 11,
                            color: Colors.white.withOpacity(0.55),
                          ),
                          const SizedBox(width: 4),
                          Flexible(
                            child: Text(
                              scheduleLabel,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                color: Colors.white.withOpacity(0.7),
                                fontSize: 12,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ),
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
            if (safetyWarning != null) ...[
              const SizedBox(height: 10),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: _Jovi.errorRed.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: _Jovi.errorRed.withOpacity(0.4),
                    width: 0.8,
                  ),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(
                      Icons.warning_amber_rounded,
                      color: _Jovi.errorRed,
                      size: 14,
                    ),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        safetyWarning,
                        style: const TextStyle(
                          color: _Jovi.errorRed,
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          height: 1.3,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
            if ((med.condition?.isNotEmpty ?? false) ||
                (med.prescribedBy?.isNotEmpty ?? false) ||
                (med.pharmacy?.isNotEmpty ?? false) ||
                med.pillCount > 0) ...[
              const SizedBox(height: 10),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  if (med.condition?.isNotEmpty ?? false)
                    _infoChip(
                      icon: Icons.medical_information_outlined,
                      label: med.condition!,
                    ),
                  if (med.prescribedBy?.isNotEmpty ?? false)
                    _infoChip(
                      icon: Icons.badge_outlined,
                      label: 'Dr. ${med.prescribedBy!}',
                    ),
                  if (med.pharmacy?.isNotEmpty ?? false)
                    _infoChip(
                      icon: Icons.local_pharmacy_outlined,
                      label: med.pharmacy!,
                    ),
                  if (med.pillCount > 0)
                    _infoChip(
                      icon: Icons.inventory_2_outlined,
                      label: '${med.pillCount} left',
                      color: med.pillCount <= 3
                          ? _Jovi.errorRed
                          : (med.pillCount <= med.refillThreshold
                              ? _Jovi.gold
                              : null),
                    )
                  else if (med.isOutOfStock)
                    _infoChip(
                      icon: Icons.error_outline_rounded,
                      label: 'Out of stock',
                      color: _Jovi.errorRed,
                    ),
                ],
              ),
            ],
            if (med.instructions.isNotEmpty) ...[
              const SizedBox(height: 8),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  for (final inst in med.instructions.take(3))
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: _Jovi.mint.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(99),
                        border: Border.all(
                          color: _Jovi.mint.withOpacity(0.25),
                          width: 0.6,
                        ),
                      ),
                      child: Text(
                        inst.length > 40 ? '${inst.substring(0, 40)}…' : inst,
                        style: TextStyle(
                          color: _Jovi.mint.withOpacity(0.95),
                          fontSize: 10,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  if (med.instructions.length > 3)
                    Text(
                      '+${med.instructions.length - 3} more',
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.5),
                        fontSize: 10,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // HISTORY TAB
  // ═══════════════════════════════════════════════════════════════════════

  int _rangeDays(String range) {
    switch (range) {
      case '7d':
        return 7;
      case '30d':
        return 30;
      case '90d':
        return 90;
      case 'all':
      default:
        return 365;
    }
  }

  Widget _buildHistoryTab(ResponsiveConfig cfg) {
    final days = _rangeDays(_historyRange);
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final start = DateTime(today.year, today.month, today.day - (days - 1));

    final events = _doseEvents
        .where((e) =>
            !e.scheduledFor.isBefore(start) && e.status != DoseStatus.scheduled)
        .toList()
      ..sort((a, b) => b.scheduledFor.compareTo(a.scheduledFor));

    final byDate = <DateTime, List<DoseEvent>>{};
    for (final e in events) {
      final d = DateTime(
        e.scheduledFor.year,
        e.scheduledFor.month,
        e.scheduledFor.day,
      );
      byDate.putIfAbsent(d, () => []).add(e);
    }
    final sortedDates = byDate.keys.toList()..sort((a, b) => b.compareTo(a));

    return ListView(
      padding: EdgeInsets.fromLTRB(cfg.pad, 8, cfg.pad, 100),
      children: [
        _rangePillRow(_historyRange, (r) {
          setState(() => _historyRange = r);
        }),
        const SizedBox(height: 14),
        _buildHeatmap(days),
        const SizedBox(height: 16),
        if (events.isEmpty)
          _emptyState(
            icon: Icons.history_rounded,
            title: 'No dose history yet',
            subtitle: 'Logged doses will appear here',
          )
        else
          for (final d in sortedDates) ...[
            _historyDaySection(d, byDate[d]!),
            const SizedBox(height: 12),
          ],
      ],
    );
  }

  Widget _rangePillRow(String current, void Function(String) onChange) {
    const keys = ['7d', '30d', '90d', 'all'];
    const labels = ['7 days', '30 days', '90 days', 'All'];
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          for (int i = 0; i < keys.length; i++) ...[
            _rangeChip(
              labels[i],
              current == keys[i],
              () => onChange(keys[i]),
            ),
            if (i < keys.length - 1) const SizedBox(width: 8),
          ],
        ],
      ),
    );
  }

  Widget _rangeChip(String label, bool selected, VoidCallback onTap) {
    return _Pressable(
      onTap: onTap,
      child: AnimatedContainer(
        duration: _Motion.select,
        curve: _Motion.settle,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          gradient: selected ? _Jovi.petGradient : null,
          color: selected ? null : Colors.white.withOpacity(0.06),
          borderRadius: BorderRadius.circular(99),
          border: Border.all(
            color: selected
                ? _Jovi.petAccent.withOpacity(0.5)
                : Colors.white.withOpacity(0.12),
            width: 0.8,
          ),
          boxShadow: selected
              ? [
                  BoxShadow(
                    color: _Jovi.petAccent.withOpacity(0.3),
                    blurRadius: 10,
                    offset: const Offset(0, 4),
                  ),
                ]
              : null,
        ),
        child: Text(
          label,
          style: TextStyle(
            color: selected ? Colors.white : Colors.white.withOpacity(0.75),
            fontSize: 12,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.3,
          ),
        ),
      ),
    );
  }

  Widget _buildHeatmap(int days) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final buckets = <DateTime, _DayRatio>{};
    for (int i = 0; i < days; i++) {
      final d = DateTime(today.year, today.month, today.day - i);
      buckets[d] = const _DayRatio(total: 0, kept: 0);
    }
    for (final e in _doseEvents) {
      if (e.status == DoseStatus.scheduled) continue;
      final d = DateTime(
        e.scheduledFor.year,
        e.scheduledFor.month,
        e.scheduledFor.day,
      );
      final existing = buckets[d];
      if (existing == null) continue;
      final isKept =
          e.status == DoseStatus.taken || e.status == DoseStatus.late;
      buckets[d] = _DayRatio(
        total: existing.total + 1,
        kept: existing.kept + (isKept ? 1 : 0),
      );
    }

    final columns = days <= 7 ? 7 : (days <= 30 ? 10 : 15);
    final sortedDays = buckets.keys.toList()..sort();

    return _glassCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _petGradientIcon(Icons.grid_view_rounded, size: 18),
              const SizedBox(width: 8),
              const Text(
                'Adherence heatmap',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const Spacer(),
              _heatmapLegend(),
            ],
          ),
          const SizedBox(height: 12),
          LayoutBuilder(
            builder: (ctx, constraints) {
              const spacing = 4.0;
              final cellSize =
                  (constraints.maxWidth - spacing * (columns - 1)) / columns;
              return Wrap(
                spacing: spacing,
                runSpacing: spacing,
                children: [
                  for (final d in sortedDays)
                    _heatmapCell(
                      d,
                      buckets[d]!,
                      cellSize,
                      isToday: d == today,
                    ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _heatmapCell(
    DateTime day,
    _DayRatio r,
    double size, {
    bool isToday = false,
  }) {
    final Color color;
    final double opacity;
    if (r.total == 0) {
      color = Colors.white;
      opacity = 0.06;
    } else {
      final ratio = r.kept / r.total;
      if (ratio >= 0.9) {
        color = _Jovi.mint;
      } else if (ratio >= 0.7) {
        color = _Jovi.gold;
      } else if (ratio >= 0.4) {
        color = _Jovi.petAccent;
      } else {
        color = _Jovi.errorRed;
      }
      opacity = 0.8;
    }
    return Tooltip(
      message: r.total == 0
          ? '${_dateLabel(day)}: no doses'
          : '${_dateLabel(day)}: ${r.kept}/${r.total}',
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          color: color.withOpacity(opacity),
          borderRadius: BorderRadius.circular(4),
          border: isToday
              ? Border.all(color: Colors.white.withOpacity(0.5), width: 1.2)
              : Border.all(
                  color: Colors.white.withOpacity(0.08),
                  width: 0.5,
                ),
        ),
      ),
    );
  }

  Widget _heatmapLegend() {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        _legendDot(_Jovi.errorRed),
        const SizedBox(width: 3),
        _legendDot(_Jovi.petAccent),
        const SizedBox(width: 3),
        _legendDot(_Jovi.gold),
        const SizedBox(width: 3),
        _legendDot(_Jovi.mint),
      ],
    );
  }

  Widget _legendDot(Color color) {
    return Container(
      width: 10,
      height: 10,
      decoration: BoxDecoration(
        color: color.withOpacity(0.8),
        borderRadius: BorderRadius.circular(2),
      ),
    );
  }

  Widget _historyDaySection(DateTime day, List<DoseEvent> events) {
    final kept = events
        .where(
            (e) => e.status == DoseStatus.taken || e.status == DoseStatus.late)
        .length;
    final total = events.length;
    final pct = total == 0 ? 0 : ((kept / total) * 100).round();
    final color = total == 0
        ? Colors.white.withOpacity(0.5)
        : (pct >= 90
            ? _Jovi.mint
            : (pct >= 70
                ? _Jovi.gold
                : (pct >= 40 ? _Jovi.petAccent : _Jovi.errorRed)));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
          child: Row(
            children: [
              Text(
                _dateLabel(day),
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.18),
                  borderRadius: BorderRadius.circular(99),
                  border: Border.all(
                    color: color.withOpacity(0.4),
                    width: 0.6,
                  ),
                ),
                child: Text(
                  '$kept/$total • $pct%',
                  style: TextStyle(
                    color: color,
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.3,
                  ),
                ),
              ),
            ],
          ),
        ),
        for (final e in events) ...[
          _buildHistoryRow(e),
          const SizedBox(height: 6),
        ],
      ],
    );
  }

  Widget _buildHistoryRow(DoseEvent ev) {
    final color = _Jovi.statusColor(ev.status);
    final icon = _Jovi.statusIcon(ev.status);

    return _Pressable(
      onTap: () => _showDoseActionSheet(ev),
      child: _glassCard(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        opacity: 0.05,
        child: Row(
          children: [
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: color.withOpacity(0.18),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: color.withOpacity(0.35),
                  width: 0.6,
                ),
              ),
              child: Icon(icon, color: color, size: 16),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    ev.medicationName,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Row(
                    children: [
                      Text(
                        _timeLabel(ev.scheduledFor),
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.65),
                          fontSize: 11,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      if (ev.minutesLate > 30) ...[
                        const SizedBox(width: 6),
                        Text(
                          '• ${ev.minutesLate} min late',
                          style: TextStyle(
                            color: _Jovi.gold.withOpacity(0.9),
                            fontSize: 11,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                      if (ev.reason != null && ev.reason!.isNotEmpty) ...[
                        const SizedBox(width: 6),
                        Flexible(
                          child: Text(
                            '• ${ev.reason}',
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              color: _Jovi.petAccent.withOpacity(0.85),
                              fontSize: 11,
                              fontStyle: FontStyle.italic,
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            _statusBadge(ev.status),
          ],
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // INSIGHTS TAB
  // ═══════════════════════════════════════════════════════════════════════

  Widget _buildInsightsTab(ResponsiveConfig cfg) {
    final days = _rangeDays(_insightsRange);
    final adherence = _adherenceRate(days);
    final streak = _streakDays();

    final lowStock =
        _medications.where((m) => m.isActive && m.isLowStock).toList();
    final outOfStock =
        _medications.where((m) => m.isActive && m.isOutOfStock).toList();
    final activeTapers =
        _medications.where((m) => m.isActive && m.isTaper).toList();
    final missedTop = _topMissed(days);
    final interactions = _activeInteractions;

    return ListView(
      padding: EdgeInsets.fromLTRB(cfg.pad, 8, cfg.pad, 100),
      children: [
        _rangePillRow(_insightsRange, (r) {
          setState(() => _insightsRange = r);
        }),
        const SizedBox(height: 14),
        _buildAdherenceSummary(adherence, streak, days),
        const SizedBox(height: 16),
        if (interactions.isNotEmpty) ...[
          _sectionHeader(
            title: 'Drug interactions',
            subtitle: '${interactions.length} flagged',
          ),
          const SizedBox(height: 8),
          for (final r in interactions) ...[
            _buildInteractionCard(r),
            const SizedBox(height: 8),
          ],
          const SizedBox(height: 8),
        ],
        if (outOfStock.isNotEmpty) ...[
          _sectionHeader(
            title: 'Out of medication',
            subtitle:
                '${outOfStock.length} ${outOfStock.length == 1 ? "med needs" : "meds need"} refill',
            trailing: _miniLinkButton(
              'Pharmacies',
              Icons.local_pharmacy_rounded,
              _showPharmacyInfo,
            ),
          ),
          const SizedBox(height: 8),
          for (final med in outOfStock) ...[
            _buildAlertCard(
              med: med,
              icon: Icons.error_outline_rounded,
              color: _Jovi.errorRed,
              message: 'Out of stock',
            ),
            const SizedBox(height: 8),
          ],
          const SizedBox(height: 8),
        ],
        if (lowStock.isNotEmpty) ...[
          _sectionHeader(
            title: 'Refill soon',
            subtitle:
                '${lowStock.length} ${lowStock.length == 1 ? "med running low" : "meds running low"}',
          ),
          const SizedBox(height: 8),
          for (final med in lowStock) ...[
            _buildAlertCard(
              med: med,
              icon: Icons.inventory_2_outlined,
              color: _Jovi.gold,
              message: '${med.pillCount} left',
            ),
            const SizedBox(height: 8),
          ],
          const SizedBox(height: 8),
        ],
        if (activeTapers.isNotEmpty) ...[
          _sectionHeader(
            title: 'Active tapers',
            subtitle: '${activeTapers.length} ongoing',
          ),
          const SizedBox(height: 8),
          for (final med in activeTapers) ...[
            _buildTaperCard(med),
            const SizedBox(height: 8),
          ],
          const SizedBox(height: 8),
        ],
        if (missedTop.isNotEmpty) ...[
          _sectionHeader(
            title: 'Most missed',
            subtitle: 'Last ${days == 365 ? "year" : "$days days"}',
          ),
          const SizedBox(height: 8),
          _glassCard(
            padding: const EdgeInsets.all(14),
            opacity: 0.05,
            child: Column(
              children: [
                for (int i = 0; i < missedTop.length; i++) ...[
                  Row(
                    children: [
                      Container(
                        width: 26,
                        height: 26,
                        decoration: BoxDecoration(
                          color: _Jovi.errorRed.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Center(
                          child: Text(
                            '${i + 1}',
                            style: const TextStyle(
                              color: _Jovi.errorRed,
                              fontSize: 11,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          missedTop[i].key,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                      Text(
                        '${missedTop[i].value} missed',
                        style: TextStyle(
                          color: _Jovi.errorRed.withOpacity(0.9),
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                  if (i < missedTop.length - 1) ...[
                    const SizedBox(height: 8),
                    Divider(
                      height: 1,
                      color: Colors.white.withOpacity(0.06),
                    ),
                    const SizedBox(height: 8),
                  ],
                ],
              ],
            ),
          ),
          const SizedBox(height: 16),
        ],
        _secondaryButton(
          label: 'Export Medication List',
          icon: Icons.file_download_outlined,
          fullWidth: true,
          onTap: _openExportSheet,
        ),
        const SizedBox(height: 10),
        _secondaryButton(
          label: 'Pet Pharmacy Options',
          icon: Icons.local_pharmacy_outlined,
          fullWidth: true,
          onTap: _showPharmacyInfo,
        ),
        const SizedBox(height: 12),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Text(
            'This app helps you track pet medications — not a substitute for veterinary care. '
            'Always confirm dosing and interactions with your vet. ASPCA Poison Control: (888) 426-4435.',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white.withOpacity(0.4),
              fontSize: 10,
              fontStyle: FontStyle.italic,
              height: 1.4,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildAdherenceSummary(double rate, int streak, int days) {
    final pct = (rate * 100).round();
    String grade;
    Color gradeColor;
    if (rate >= 0.9) {
      grade = 'Excellent';
      gradeColor = _Jovi.mint;
    } else if (rate >= 0.75) {
      grade = 'Good';
      gradeColor = _Jovi.gold;
    } else if (rate >= 0.5) {
      grade = 'Needs work';
      gradeColor = _Jovi.petAccent;
    } else {
      grade = 'Poor';
      gradeColor = _Jovi.errorRed;
    }

    return _glassCard(
      padding: const EdgeInsets.all(18),
      tint: gradeColor,
      opacity: 0.06,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _petGradientIcon(Icons.insights_rounded, size: 20),
              const SizedBox(width: 8),
              Text(
                'Last ${days == 365 ? "year" : "$days days"}',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const Spacer(),
              if (streak > 0)
                _glassPill(
                  tint: _Jovi.gold,
                  opacity: 0.16,
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.local_fire_department_rounded,
                          color: _Jovi.gold, size: 13),
                      const SizedBox(width: 4),
                      Text(
                        '$streak day streak',
                        style: const TextStyle(
                          color: _Jovi.gold,
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '$pct',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 56,
                  fontWeight: FontWeight.w800,
                  height: 1,
                  letterSpacing: -2,
                ),
              ),
              const Padding(
                padding: EdgeInsets.only(bottom: 10),
                child: Text(
                  '%',
                  style: TextStyle(
                    color: Colors.white70,
                    fontSize: 24,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              const Spacer(),
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  decoration: BoxDecoration(
                    color: gradeColor.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(99),
                    border: Border.all(
                      color: gradeColor.withOpacity(0.5),
                      width: 0.8,
                    ),
                  ),
                  child: Text(
                    grade,
                    style: TextStyle(
                      color: gradeColor,
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0.3,
                    ),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'adherence rate',
            style: TextStyle(
              color: Colors.white.withOpacity(0.55),
              fontSize: 12,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInteractionCard(InteractionResult r) {
    final color = _Jovi.severityColor(r.severity);
    return _glassCard(
      padding: const EdgeInsets.all(12),
      opacity: 0.05,
      tint: color,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                r.severity == InteractionSeverity.avoid
                    ? Icons.block_rounded
                    : Icons.warning_amber_rounded,
                color: color,
                size: 18,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  '${r.drugA} + ${r.drugB}',
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              _severityBadge(r.severity),
            ],
          ),
          const SizedBox(height: 6),
          Padding(
            padding: const EdgeInsets.only(left: 26),
            child: Text(
              r.summary,
              style: TextStyle(
                color: Colors.white.withOpacity(0.75),
                fontSize: 11,
                height: 1.4,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAlertCard({
    required PetMedication med,
    required IconData icon,
    required Color color,
    required String message,
  }) {
    return _Pressable(
      onTap: () => _openMedDetails(med),
      child: _glassCard(
        padding: const EdgeInsets.all(12),
        opacity: 0.05,
        tint: color,
        child: Row(
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: color.withOpacity(0.18),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(icon, color: color, size: 18),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    med.name,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  Text(
                    message,
                    style: TextStyle(
                      color: color.withOpacity(0.9),
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
            Icon(
              Icons.chevron_right_rounded,
              color: Colors.white.withOpacity(0.4),
              size: 20,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTaperCard(PetMedication med) {
    final step = _ScheduleEngine.currentTaperStep(med) ?? 1;
    final total = med.taperSteps.length;
    final progress = total == 0 ? 0.0 : step / total;
    final currentStep = med.taperSteps.isNotEmpty && step <= total
        ? med.taperSteps[step - 1]
        : null;

    return _Pressable(
      onTap: () => _openMedDetails(med),
      child: _glassCard(
        padding: const EdgeInsets.all(12),
        opacity: 0.05,
        tint: _Jovi.gold,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: _Jovi.gold.withOpacity(0.18),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(
                    Icons.stairs_rounded,
                    color: _Jovi.gold,
                    size: 18,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        med.name,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      Text(
                        currentStep != null
                            ? 'Step $step of $total • ${currentStep.dose}'
                            : 'Step $step of $total',
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.7),
                          fontSize: 11,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
                Text(
                  '$step/$total',
                  style: const TextStyle(
                    color: _Jovi.gold,
                    fontSize: 14,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: progress,
                minHeight: 4,
                backgroundColor: Colors.white.withOpacity(0.08),
                valueColor: const AlwaysStoppedAnimation<Color>(_Jovi.gold),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // MED DETAILS SHEET
  // ═══════════════════════════════════════════════════════════════════════

  Future<void> _openMedDetails(PetMedication med) async {
    await _showNavyBottomSheet(
      builder: (ctx) {
        final recentEvents = _doseEvents
            .where((e) => e.medicationId == med.id)
            .toList()
          ..sort((a, b) => b.scheduledFor.compareTo(a.scheduledFor));
        final last10 = recentEvents.take(10).toList();
        final myInteractions = _activeInteractions
            .where((r) => r.drugA == med.name || r.drugB == med.name)
            .toList();
        final pet = _currentPet;
        final safetyWarning = pet == null
            ? null
            : _VetDrugDB.speciesSafetyWarning(med.name, pet.type);

        return SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _sheetHandle(),
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 4, 20, 20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          width: 56,
                          height: 56,
                          decoration: BoxDecoration(
                            gradient: _Jovi.petGradient,
                            borderRadius: BorderRadius.circular(16),
                            boxShadow: [
                              BoxShadow(
                                color: _Jovi.petAccent.withOpacity(0.3),
                                blurRadius: 12,
                                offset: const Offset(0, 4),
                              ),
                            ],
                          ),
                          child: Icon(
                            med.type.icon,
                            color: Colors.white,
                            size: 28,
                          ),
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                med.name,
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 20,
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                              if (med.strength.isNotEmpty)
                                Text(
                                  '${med.strength}${med.dosage.isNotEmpty ? " • ${med.dosage}" : ""}',
                                  style: TextStyle(
                                    color: Colors.white.withOpacity(0.7),
                                    fontSize: 13,
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                            ],
                          ),
                        ),
                        if (!med.isActive)
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              color: Colors.white.withOpacity(0.12),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                              'Stopped',
                              style: TextStyle(
                                color: Colors.white.withOpacity(0.7),
                                fontSize: 11,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                      ],
                    ),
                    const SizedBox(height: 18),
                    // Safety warning (highest priority)
                    if (safetyWarning != null) ...[
                      _glassCard(
                        padding: const EdgeInsets.all(14),
                        opacity: 0.15,
                        tint: _Jovi.errorRed,
                        border: Border.all(
                          color: _Jovi.errorRed.withOpacity(0.5),
                          width: 1.2,
                        ),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Icon(
                              Icons.warning_amber_rounded,
                              color: _Jovi.errorRed,
                              size: 20,
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text(
                                    'Species Safety Warning',
                                    style: TextStyle(
                                      color: _Jovi.errorRed,
                                      fontSize: 12,
                                      fontWeight: FontWeight.w700,
                                      letterSpacing: -0.1,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    safetyWarning,
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontSize: 12,
                                      height: 1.4,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 10),
                    ],
                    // Schedule
                    _glassCard(
                      padding: const EdgeInsets.all(14),
                      opacity: 0.04,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Icon(
                                Icons.schedule_rounded,
                                color: Colors.white.withOpacity(0.7),
                                size: 16,
                              ),
                              const SizedBox(width: 8),
                              const Text(
                                'Schedule',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 13,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Text(
                            _ScheduleEngine.summarize(med, _prefs),
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.85),
                              fontSize: 13,
                              height: 1.4,
                            ),
                          ),
                          if (med.isTaper && med.taperSteps.isNotEmpty) ...[
                            const SizedBox(height: 10),
                            Divider(
                              height: 1,
                              color: Colors.white.withOpacity(0.08),
                            ),
                            const SizedBox(height: 10),
                            Text(
                              'Taper plan',
                              style: TextStyle(
                                color: Colors.white.withOpacity(0.6),
                                fontSize: 11,
                                fontWeight: FontWeight.w700,
                                letterSpacing: 0.3,
                              ),
                            ),
                            const SizedBox(height: 6),
                            for (int i = 0; i < med.taperSteps.length; i++)
                              Padding(
                                padding: const EdgeInsets.only(bottom: 4),
                                child: Text(
                                  'Day ${med.taperSteps[i].startDay}+ • ${med.taperSteps[i].dose}${med.taperSteps[i].times.isEmpty ? "" : " at ${med.taperSteps[i].times.join(", ")}"}',
                                  style: TextStyle(
                                    color: Colors.white.withOpacity(0.7),
                                    fontSize: 11,
                                  ),
                                ),
                              ),
                          ],
                        ],
                      ),
                    ),
                    const SizedBox(height: 10),
                    // Inventory
                    if (med.pillCount > 0 || med.refillThreshold > 0) ...[
                      _glassCard(
                        padding: const EdgeInsets.all(14),
                        opacity: 0.04,
                        child: Row(
                          children: [
                            Icon(
                              Icons.inventory_2_outlined,
                              color: med.isLowStock
                                  ? _Jovi.gold
                                  : Colors.white.withOpacity(0.7),
                              size: 16,
                            ),
                            const SizedBox(width: 8),
                            const Text(
                              'Inventory',
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 13,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const Spacer(),
                            Text(
                              '${med.pillCount} left',
                              style: TextStyle(
                                color: med.isOutOfStock
                                    ? _Jovi.errorRed
                                    : (med.isLowStock
                                        ? _Jovi.gold
                                        : Colors.white),
                                fontSize: 14,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                            const SizedBox(width: 6),
                            Text(
                              '(refill at ${med.refillThreshold})',
                              style: TextStyle(
                                color: Colors.white.withOpacity(0.5),
                                fontSize: 11,
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 10),
                    ],
                    // Condition / prescriber / pharmacy / notes
                    if ((med.condition?.isNotEmpty ?? false) ||
                        (med.prescribedBy?.isNotEmpty ?? false) ||
                        (med.pharmacy?.isNotEmpty ?? false) ||
                        (med.notes?.isNotEmpty ?? false)) ...[
                      _glassCard(
                        padding: const EdgeInsets.all(14),
                        opacity: 0.04,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (med.condition?.isNotEmpty ?? false) ...[
                              _detailRow(
                                icon: Icons.medical_information_outlined,
                                label: 'Treating',
                                value: med.condition!,
                              ),
                              const SizedBox(height: 8),
                            ],
                            if (med.prescribedBy?.isNotEmpty ?? false) ...[
                              _detailRow(
                                icon: Icons.badge_outlined,
                                label: 'Vet',
                                value: med.prescribedBy!,
                              ),
                              const SizedBox(height: 8),
                            ],
                            if (med.pharmacy?.isNotEmpty ?? false) ...[
                              _detailRow(
                                icon: Icons.local_pharmacy_outlined,
                                label: 'Pharmacy',
                                value: med.pharmacy!,
                              ),
                              const SizedBox(height: 8),
                            ],
                            if (med.notes?.isNotEmpty ?? false) ...[
                              _detailRow(
                                icon: Icons.sticky_note_2_outlined,
                                label: 'Notes',
                                value: med.notes!,
                              ),
                            ],
                          ],
                        ),
                      ),
                      const SizedBox(height: 10),
                    ],
                    // Instructions
                    if (med.instructions.isNotEmpty) ...[
                      _glassCard(
                        padding: const EdgeInsets.all(14),
                        opacity: 0.04,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: const [
                                Icon(
                                  Icons.info_outline_rounded,
                                  color: _Jovi.mint,
                                  size: 16,
                                ),
                                SizedBox(width: 8),
                                Text(
                                  'Instructions',
                                  style: TextStyle(
                                    color: Colors.white,
                                    fontSize: 13,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            for (final inst in med.instructions) ...[
                              Padding(
                                padding: const EdgeInsets.only(bottom: 6),
                                child: Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Padding(
                                      padding: const EdgeInsets.only(top: 5),
                                      child: Container(
                                        width: 4,
                                        height: 4,
                                        decoration: BoxDecoration(
                                          color: _Jovi.mint,
                                          borderRadius:
                                              BorderRadius.circular(2),
                                        ),
                                      ),
                                    ),
                                    const SizedBox(width: 8),
                                    Expanded(
                                      child: Text(
                                        inst,
                                        style: TextStyle(
                                          color: Colors.white.withOpacity(0.8),
                                          fontSize: 12,
                                          height: 1.4,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
                      const SizedBox(height: 10),
                    ],
                    // Interactions
                    if (myInteractions.isNotEmpty) ...[
                      _sectionHeader(
                        title: 'Interactions',
                        subtitle:
                            '${myInteractions.length} flagged with other meds',
                      ),
                      const SizedBox(height: 6),
                      for (final r in myInteractions) ...[
                        _buildInteractionCard(r),
                        const SizedBox(height: 8),
                      ],
                      const SizedBox(height: 4),
                    ],
                    // Recent doses
                    if (last10.isNotEmpty) ...[
                      _sectionHeader(title: 'Recent doses'),
                      const SizedBox(height: 6),
                      _glassCard(
                        padding: const EdgeInsets.all(10),
                        opacity: 0.04,
                        child: Column(
                          children: [
                            for (int i = 0; i < last10.length; i++) ...[
                              Row(
                                children: [
                                  Icon(
                                    _Jovi.statusIcon(last10[i].status),
                                    color: _Jovi.statusColor(last10[i].status),
                                    size: 14,
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      '${_dateLabel(last10[i].scheduledFor)} at ${_timeLabel(last10[i].scheduledFor)}',
                                      overflow: TextOverflow.ellipsis,
                                      style: TextStyle(
                                        color: Colors.white.withOpacity(0.8),
                                        fontSize: 12,
                                      ),
                                    ),
                                  ),
                                  _statusBadge(last10[i].status, fontSize: 9),
                                ],
                              ),
                              if (i < last10.length - 1) ...[
                                const SizedBox(height: 6),
                                Divider(
                                  height: 1,
                                  color: Colors.white.withOpacity(0.05),
                                ),
                                const SizedBox(height: 6),
                              ],
                            ],
                          ],
                        ),
                      ),
                      const SizedBox(height: 14),
                    ],
                    // Actions
                    Row(
                      children: [
                        Expanded(
                          child: _secondaryButton(
                            label: 'Edit',
                            icon: Icons.edit_rounded,
                            fullWidth: true,
                            onTap: () {
                              Navigator.pop(ctx);
                              _openAddEditSheet(med);
                            },
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: med.isActive
                              ? _secondaryButton(
                                  label: 'Stop',
                                  icon: Icons.stop_circle_outlined,
                                  color: _Jovi.gold,
                                  fullWidth: true,
                                  onTap: () async {
                                    Navigator.pop(ctx);
                                    await _stopMedication(med.id);
                                    _showSnack('Medication stopped');
                                  },
                                )
                              : _secondaryButton(
                                  label: 'Resume',
                                  icon: Icons.play_circle_outline_rounded,
                                  color: _Jovi.mint,
                                  fullWidth: true,
                                  onTap: () async {
                                    Navigator.pop(ctx);
                                    await _resumeMedication(med.id);
                                    _showSnack('Medication resumed');
                                  },
                                ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    _secondaryButton(
                      label: 'Delete Medication',
                      icon: Icons.delete_outline_rounded,
                      color: _Jovi.errorRed,
                      fullWidth: true,
                      onTap: () async {
                        final ok = await _confirmDelete(med.name);
                        if (ok) {
                          Navigator.pop(ctx);
                          await _deleteMedication(med.id);
                          _showSnack('Medication deleted');
                        }
                      },
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _detailRow({
    required IconData icon,
    required String label,
    required String value,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: Colors.white.withOpacity(0.55), size: 14),
        const SizedBox(width: 8),
        SizedBox(
          width: 90,
          child: Text(
            label,
            style: TextStyle(
              color: Colors.white.withOpacity(0.55),
              fontSize: 11,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        Expanded(
          child: Text(
            value,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 12,
              fontWeight: FontWeight.w500,
              height: 1.4,
            ),
          ),
        ),
      ],
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // PHARMACY INFO
  // Pet meds don't go through human pharmacies (CVS/Walgreens) — this modal
  // lists the legitimate options so users don't get confused.
  // ═══════════════════════════════════════════════════════════════════════

  Future<void> _showPharmacyInfo() async {
    await _showNavyBottomSheet(
      builder: (ctx) => SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _sheetHandle(),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 4, 20, 20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      _petGradientIcon(
                        Icons.local_pharmacy_rounded,
                        size: 22,
                      ),
                      const SizedBox(width: 10),
                      const Expanded(
                        child: Text(
                          'Pet pharmacy options',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 18,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Pet prescriptions don\'t fill at human pharmacies (CVS, Walgreens). '
                    'Here\'s where to get them:',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.7),
                      fontSize: 12,
                      height: 1.4,
                    ),
                  ),
                  const SizedBox(height: 16),
                  _pharmacyTile(
                    icon: Icons.medical_services_rounded,
                    title: 'Your vet clinic',
                    subtitle:
                        'Fastest for controlled substances, injectables, and urgent Rx. May be slightly more expensive.',
                    accent: _Jovi.mint,
                  ),
                  const SizedBox(height: 10),
                  _pharmacyTile(
                    icon: Icons.pets_rounded,
                    title: 'Chewy Pharmacy',
                    subtitle:
                        'Auto-ship, often cheapest. Ask your vet to send the Rx directly. chewy.com/pharmacy',
                    accent: _Jovi.petAccent,
                  ),
                  const SizedBox(height: 10),
                  _pharmacyTile(
                    icon: Icons.phone_rounded,
                    title: '1-800-PetMeds',
                    subtitle:
                        'Mail-order pet pharmacy. Competitive pricing on flea/tick, heart, and common maintenance meds.',
                    accent: _Jovi.sky,
                  ),
                  const SizedBox(height: 10),
                  _pharmacyTile(
                    icon: Icons.science_rounded,
                    title: 'Compounding pharmacy',
                    subtitle:
                        'For custom flavors, strengths, or forms (transdermal, liquid). Your vet can refer you to one near you.',
                    accent: _Jovi.gold,
                  ),
                  const SizedBox(height: 16),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: _Jovi.gold.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: _Jovi.gold.withOpacity(0.3),
                        width: 0.8,
                      ),
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Icon(
                          Icons.lightbulb_outline_rounded,
                          color: _Jovi.gold,
                          size: 16,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            'Many human-labeled drugs (gabapentin, fluoxetine, famotidine) can also be filled at human pharmacies like Costco or GoodRx when prescribed by a vet — often at huge savings. Ask your vet for a paper script.',
                            style: TextStyle(
                              color: _Jovi.gold.withOpacity(0.95),
                              fontSize: 11,
                              height: 1.5,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),
                  _primaryButton(
                    label: 'Got it',
                    fullWidth: true,
                    onTap: () => Navigator.pop(ctx),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _pharmacyTile({
    required IconData icon,
    required String title,
    required String subtitle,
    required Color accent,
  }) {
    return _glassCard(
      padding: const EdgeInsets.all(14),
      opacity: 0.05,
      tint: accent,
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: accent.withOpacity(0.18),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, color: accent, size: 20),
          ),
          const SizedBox(width: 12),
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
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  subtitle,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.7),
                    fontSize: 11,
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

  // ═══════════════════════════════════════════════════════════════════════
  // CONFIRM DELETE
  // ═══════════════════════════════════════════════════════════════════════

  Future<bool> _confirmDelete(String name) async {
    final result = await showCupertinoDialog<bool>(
      context: context,
      builder: (ctx) => CupertinoAlertDialog(
        title: const Text('Delete Medication?'),
        content: Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Text(
              'This permanently removes $name and all of its dose history. This cannot be undone.'),
        ),
        actions: [
          CupertinoDialogAction(
            isDefaultAction: true,
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          CupertinoDialogAction(
            isDestructiveAction: true,
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    return result ?? false;
  }

  // ignore: unused_element
  Future<bool> _confirmDeleteLegacy(String name) async {
    final result = await _showNavyDialog<bool>(
      builder: (ctx) => Padding(
        padding: const EdgeInsets.all(22),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: _Jovi.errorRed.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(
                    Icons.delete_outline_rounded,
                    color: _Jovi.errorRed,
                    size: 22,
                  ),
                ),
                const SizedBox(width: 12),
                const Expanded(
                  child: Text(
                    'Delete medication?',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 17,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              'This will permanently remove $name and all its dose history. This cannot be undone.',
              style: TextStyle(
                color: Colors.white.withOpacity(0.75),
                fontSize: 13,
                height: 1.4,
              ),
            ),
            const SizedBox(height: 18),
            Row(
              children: [
                Expanded(
                  child: _secondaryButton(
                    label: 'Cancel',
                    fullWidth: true,
                    onTap: () => Navigator.pop(ctx, false),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _primaryButton(
                    label: 'Delete',
                    fullWidth: true,
                    tint: _Jovi.errorRed,
                    onTap: () => Navigator.pop(ctx, true),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
    return result ?? false;
  }

  // ═══════════════════════════════════════════════════════════════════════
  // EXPORT SHEET — vet-ready text format
  // ═══════════════════════════════════════════════════════════════════════

  Future<void> _openExportSheet() async {
    final pet = _currentPet;
    final activeList = _medications.where((m) => m.isActive).toList();
    final stoppedList = _medications.where((m) => !m.isActive).toList();
    final buf = StringBuffer();
    buf.writeln('═══════════════════════════════════════════');
    buf.writeln('PET MEDICATION LIST');
    if (pet != null) {
      buf.writeln('Pet: ${pet.name} (${_petTypeLabel(pet.type)}'
          '${pet.breed != null && pet.breed!.isNotEmpty ? ", ${pet.breed}" : ""})');
      if (pet.weightLbs != null) {
        buf.writeln(
            'Weight: ${pet.weightLbs!.toStringAsFixed(1)} lbs (${pet.weightKg!.toStringAsFixed(1)} kg)');
      }
    }
    buf.writeln(
        'Generated: ${_dateLabel(DateTime.now())} at ${_timeLabel(DateTime.now())}');
    buf.writeln('═══════════════════════════════════════════');
    buf.writeln();
    if (activeList.isEmpty && stoppedList.isEmpty) {
      buf.writeln('No medications on record.');
    }
    if (activeList.isNotEmpty) {
      buf.writeln('ACTIVE MEDICATIONS (${activeList.length})');
      buf.writeln('-------------------------------------------');
      for (int i = 0; i < activeList.length; i++) {
        final m = activeList[i];
        buf.writeln();
        buf.writeln(
            '${i + 1}. ${m.name}${m.strength.isNotEmpty ? " ${m.strength}" : ""}');
        if (m.dosage.isNotEmpty) buf.writeln('   Dose: ${m.dosage}');
        buf.writeln('   Schedule: ${_ScheduleEngine.summarize(m, _prefs)}');
        if (m.condition?.isNotEmpty ?? false) {
          buf.writeln('   For: ${m.condition}');
        }
        if (m.prescribedBy?.isNotEmpty ?? false) {
          buf.writeln('   Vet: ${m.prescribedBy}');
        }
        if (m.pharmacy?.isNotEmpty ?? false) {
          buf.writeln('   Pharmacy: ${m.pharmacy}');
        }
        if (m.instructions.isNotEmpty) {
          buf.writeln('   Notes: ${m.instructions.join("; ")}');
        }
        if (m.pillCount > 0) {
          buf.writeln('   On hand: ${m.pillCount}');
        }
      }
      buf.writeln();
    }
    if (stoppedList.isNotEmpty) {
      buf.writeln();
      buf.writeln('STOPPED MEDICATIONS (${stoppedList.length})');
      buf.writeln('-------------------------------------------');
      for (int i = 0; i < stoppedList.length; i++) {
        final m = stoppedList[i];
        buf.writeln();
        buf.writeln(
            '${i + 1}. ${m.name}${m.strength.isNotEmpty ? " ${m.strength}" : ""}');
        if (m.stopDate != null) {
          buf.writeln('   Stopped: ${_dateLabel(m.stopDate!)}');
        }
      }
      buf.writeln();
    }
    if (_activeInteractions.isNotEmpty) {
      buf.writeln();
      buf.writeln('INTERACTION FLAGS (${_activeInteractions.length})');
      buf.writeln('-------------------------------------------');
      for (final r in _activeInteractions) {
        buf.writeln();
        buf.writeln('[${r.severity.label}] ${r.drugA} + ${r.drugB}');
        buf.writeln('   ${r.summary}');
      }
    }
    buf.writeln();
    buf.writeln('═══════════════════════════════════════════');
    buf.writeln('Generated by Jovi Health');
    buf.writeln('Not medical advice. Verify with your veterinarian.');
    final text = buf.toString();

    await _showNavyBottomSheet(
      builder: (ctx) => SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            _sheetHandle(),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 4, 20, 20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      _petGradientIcon(
                        Icons.file_download_outlined,
                        size: 22,
                      ),
                      const SizedBox(width: 10),
                      const Text(
                        'Medication List',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Vet-ready format. Tap "Copy" to paste into a message or email.',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.65),
                      fontSize: 12,
                      height: 1.4,
                    ),
                  ),
                  const SizedBox(height: 14),
                  Container(
                    constraints: BoxConstraints(
                      maxHeight: MediaQuery.of(ctx).size.height * 0.45,
                    ),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.black.withOpacity(0.25),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: Colors.white.withOpacity(0.1),
                        width: 0.8,
                      ),
                    ),
                    child: SingleChildScrollView(
                      child: SelectableText(
                        text,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 11,
                          fontFamily: 'monospace',
                          height: 1.4,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 14),
                  Row(
                    children: [
                      Expanded(
                        child: _secondaryButton(
                          label: 'Close',
                          fullWidth: true,
                          onTap: () => Navigator.pop(ctx),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _primaryButton(
                          label: 'Copy',
                          icon: Icons.copy_rounded,
                          fullWidth: true,
                          onTap: () {
                            Clipboard.setData(ClipboardData(text: text));
                            Navigator.pop(ctx);
                            _showSnack('Copied to clipboard');
                          },
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
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // ADD / EDIT MED SHEET LAUNCHER
  // Full implementation lives in the _AddEditPetMedSheet StatefulWidget
  // (separate class to keep its internal state clean). Arrives in Part 3.
  // ═══════════════════════════════════════════════════════════════════════

  Future<void> _openAddEditSheet(PetMedication? existing) async {
    final pet = _currentPet;
    if (pet == null || _uid == null || _currentPetId == null) {
      _showSnack('Please select a pet first', isError: true);
      return;
    }
    final isEdit = existing != null;
    await _showNavyBottomSheet(
      builder: (ctx) => _AddEditPetMedSheet(
        existing: existing,
        pet: pet,
        prefs: _prefs,
        allMeds: _medications,
        uid: _uid!,
        petId: _currentPetId!,
        onSave: (med) async {
          // Pre-save interaction check (only on add or if name changed)
          if (!isEdit || existing.name != med.name) {
            final others = _medications
                .where((m) => m.id != med.id && m.isActive)
                .toList();
            final results = InteractionCheck.checkAgainst(
              med.name,
              med.species,
              others,
            );
            if (results.isNotEmpty) {
              final proceed = await _showInteractionWarning(results);
              if (!proceed) return false;
            }
          }
          await _saveMedication(med);
          _showSnack(isEdit ? 'Medication updated' : 'Medication added');
          return true;
        },
      ),
    );
  }

  Future<bool> _showInteractionWarning(
    List<InteractionResult> results,
  ) async {
    final result = await _showNavyDialog<bool>(
      builder: (ctx) => Padding(
        padding: const EdgeInsets.all(22),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [_Jovi.errorRed, _Jovi.softRed],
                    ),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: const Icon(
                    Icons.warning_amber_rounded,
                    color: Colors.white,
                    size: 22,
                  ),
                ),
                const SizedBox(width: 12),
                const Expanded(
                  child: Text(
                    'Interaction warning',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            Text(
              'This medication interacts with ${results.length == 1 ? "another" : "others"} on your pet\'s list. Confirm with your vet before adding.',
              style: TextStyle(
                color: Colors.white.withOpacity(0.8),
                fontSize: 13,
                height: 1.4,
              ),
            ),
            const SizedBox(height: 14),
            ...results.map((r) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: _buildInteractionCard(r),
                )),
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: _secondaryButton(
                    label: 'Cancel',
                    fullWidth: true,
                    onTap: () => Navigator.pop(ctx, false),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _primaryButton(
                    label: 'Add anyway',
                    fullWidth: true,
                    onTap: () => Navigator.pop(ctx, true),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
    return result ?? false;
  }
}

// ─── Enums ──────────────────────────────────────────────────────────────────

enum ScreenType { compact, medium, expanded, large }

enum _Tab { today, meds, history, insights }

enum PetType { dog, cat, other }

String _petTypeLabel(PetType t) {
  switch (t) {
    case PetType.dog:
      return 'Dog';
    case PetType.cat:
      return 'Cat';
    case PetType.other:
      return 'Other';
  }
}

PetType _petTypeParse(String? raw) {
  if (raw == null) return PetType.other;
  switch (raw.toLowerCase().trim()) {
    case 'dog':
    case 'canine':
    case 'puppy':
      return PetType.dog;
    case 'cat':
    case 'feline':
    case 'kitten':
      return PetType.cat;
    default:
      return PetType.other;
  }
}

IconData _petTypeIcon(PetType t) {
  switch (t) {
    case PetType.dog:
      return Icons.pets_rounded;
    case PetType.cat:
      return Icons.pets_rounded;
    case PetType.other:
      return Icons.pets_outlined;
  }
}

enum MedType {
  pill('Pill', Icons.medication_rounded),
  capsule('Capsule', Icons.medication_outlined),
  tablet('Tablet', Icons.circle_outlined),
  liquid('Liquid / oral suspension', Icons.water_drop_rounded),
  injection('Injection', Icons.colorize_rounded),
  topical('Topical / spot-on', Icons.healing_rounded),
  chewable('Chewable', Icons.cookie_rounded),
  drops('Drops (eye / ear)', Icons.opacity_rounded),
  other('Other', Icons.medical_services_rounded);

  const MedType(this.label, this.icon);
  final String label;
  final IconData icon;
}

enum SchedulePreset {
  clockTimes('Specific Times'),
  meals('With Meals'),
  interval('Every N Hours'),
  weekly('Certain Days'),
  taper('Taper Schedule'),
  prn('As Needed (PRN)');

  const SchedulePreset(this.label);
  final String label;
}

enum DoseStatus {
  scheduled,
  taken,
  late,
  missed,
  skipped,
}

enum MealTiming {
  none('Anytime'),
  beforeMeal('Before Meal'),
  withMeal('With Food'),
  afterMeal('After Meal'),
  emptyStomach('Empty Stomach'),
  bedtime('At Bedtime');

  const MealTiming(this.label);
  final String label;
}

enum InteractionSeverity {
  avoid('Avoid', 'Do not combine'),
  caution('Caution', 'Use with care'),
  monitor('Monitor', 'Watch for effects');

  const InteractionSeverity(this.label, this.detail);
  final String label;
  final String detail;
}

// ─── Responsive Config ─────────────────────────────────────────────────────

class ResponsiveConfig {
  final ScreenType screen;
  final double pad;
  final double cardRadius;
  final double titleSize;
  final double bodySize;
  final double smallSize;
  final double iconSize;

  const ResponsiveConfig({
    required this.screen,
    required this.pad,
    required this.cardRadius,
    required this.titleSize,
    required this.bodySize,
    required this.smallSize,
    required this.iconSize,
  });

  static ResponsiveConfig fromWidth(double w) {
    if (w < 380) {
      return const ResponsiveConfig(
        screen: ScreenType.compact,
        pad: 14,
        cardRadius: 20,
        titleSize: 18,
        bodySize: 13,
        smallSize: 11,
        iconSize: 20,
      );
    } else if (w < 600) {
      return const ResponsiveConfig(
        screen: ScreenType.medium,
        pad: 16,
        cardRadius: 22,
        titleSize: 20,
        bodySize: 14,
        smallSize: 12,
        iconSize: 22,
      );
    } else if (w < 900) {
      return const ResponsiveConfig(
        screen: ScreenType.expanded,
        pad: 20,
        cardRadius: 24,
        titleSize: 22,
        bodySize: 15,
        smallSize: 12,
        iconSize: 24,
      );
    }
    return const ResponsiveConfig(
      screen: ScreenType.large,
      pad: 24,
      cardRadius: 26,
      titleSize: 24,
      bodySize: 16,
      smallSize: 13,
      iconSize: 26,
    );
  }
}

// ─── Palette ───────────────────────────────────────────────────────────────

class _Jovi {
  static const Color coral = Color(0xFFFF6B4A);
  static const Color coralLight = Color(0xFFFF8F73);
  static const Color coralDark = Color(0xFFE5583A);
  static const Color navy = Color(0xFF1A2744);
  static const Color navyDark = Color(0xFF0F1A2E);
  static const Color navyMid = Color(0xFF1F2B47);
  static const Color mint = Color(0xFF00D4AA);
  static const Color mintDark = Color(0xFF00B894);
  static const Color gold = Color(0xFFFFD166);
  static const Color goldDark = Color(0xFFE6B84D);
  static const Color errorRed = Color(0xFFE53935);
  static const Color softRed = Color(0xFFFF8A80);
  static const Color sky = Color(0xFF56CCF2);
  // Pet section accent — violet, matches Pet Profiles + Vaccinations
  static const Color petAccent = Color(0xFFA78BFA);
  static const Color petAccentDark = Color(0xFF8B6EE8);

  static LinearGradient get petGradient => const LinearGradient(
        colors: [petAccent, petAccentDark],
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
      );
  static LinearGradient get coralGradient => const LinearGradient(
        colors: [coral, coralDark],
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
      );
  static LinearGradient get navyGradient => const LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [navy, navy, navyDark],
      );

  static Color statusColor(DoseStatus s) {
    switch (s) {
      case DoseStatus.scheduled:
        return sky;
      case DoseStatus.taken:
        return mint;
      case DoseStatus.late:
        return gold;
      case DoseStatus.missed:
        return errorRed;
      case DoseStatus.skipped:
        return Colors.white54;
    }
  }

  static IconData statusIcon(DoseStatus s) {
    switch (s) {
      case DoseStatus.scheduled:
        return Icons.schedule_rounded;
      case DoseStatus.taken:
        return Icons.check_circle_rounded;
      case DoseStatus.late:
        return Icons.watch_later_rounded;
      case DoseStatus.missed:
        return Icons.cancel_rounded;
      case DoseStatus.skipped:
        return Icons.block_rounded;
    }
  }

  static String statusLabel(DoseStatus s) {
    switch (s) {
      case DoseStatus.scheduled:
        return 'Due';
      case DoseStatus.taken:
        return 'Given';
      case DoseStatus.late:
        return 'Late';
      case DoseStatus.missed:
        return 'Missed';
      case DoseStatus.skipped:
        return 'Skipped';
    }
  }

  static Color severityColor(InteractionSeverity s) {
    switch (s) {
      case InteractionSeverity.avoid:
        return errorRed;
      case InteractionSeverity.caution:
        return coral;
      case InteractionSeverity.monitor:
        return gold;
    }
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// LIGHTWEIGHT PET MODEL
// Same 5-field minimum as Pet Vaccinations for legacy-array compat,
// plus weightLbs and dateOfBirth for weight-based dosing hints when
// available from Pet Profiles.
// ═══════════════════════════════════════════════════════════════════════════

class _PetLite {
  final String petId;
  final String name;
  final PetType type;
  final String? breed;
  final String? photoUrl;
  final double? weightLbs;
  final DateTime? dateOfBirth;

  const _PetLite({
    required this.petId,
    required this.name,
    this.type = PetType.other,
    this.breed,
    this.photoUrl,
    this.weightLbs,
    this.dateOfBirth,
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
      breed: m['breed'] as String?,
      photoUrl: m['photoUrl'] as String? ?? m['photo_url'] as String?,
      weightLbs: asDouble(m['weightLbs'] ?? m['weight']),
      dateOfBirth: parseTs(m['dateOfBirth'] ?? m['dob'] ?? m['birthdate']),
    );
  }

  /// Parse from the legacy 5-field JSON string entry (onboarding/update).
  /// Those entries don't carry weight or DOB; return what we can.
  static _PetLite? fromLegacyJson(String jsonStr) {
    try {
      final decoded = jsonDecode(jsonStr);
      if (decoded is! Map) return null;
      final m = Map<String, dynamic>.from(decoded);
      final petId = (m['petId'] as String?)?.trim();
      final name = (m['name'] as String?)?.trim();
      if (petId == null || petId.isEmpty) return null;
      if (name == null || name.isEmpty) return null;
      return _PetLite(
        petId: petId,
        name: name,
        type: _petTypeParse(m['type'] as String?),
        breed: m['breed'] as String?,
        photoUrl: m['photo_url'] as String?,
      );
    } catch (_) {
      return null;
    }
  }

  double? get weightKg {
    if (weightLbs == null) return null;
    return weightLbs! * 0.453592;
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// DATA MODELS
// Same shape as the human widget, plus species + dosePerKg hint.
// ═══════════════════════════════════════════════════════════════════════════

class TaperStep {
  final int startDay;
  final String dose;
  final List<String> times;

  const TaperStep({
    required this.startDay,
    required this.dose,
    required this.times,
  });

  Map<String, dynamic> toMap() => {
        'startDay': startDay,
        'dose': dose,
        'times': times,
      };

  static TaperStep fromMap(Map<String, dynamic> m) => TaperStep(
        startDay: (m['startDay'] as num?)?.toInt() ?? 0,
        dose: (m['dose'] as String?) ?? '',
        times: ((m['times'] as List?) ?? const [])
            .map((e) => e.toString())
            .toList(),
      );
}

class PetMedication {
  final String id;
  final String name;
  final String strength;
  final String dosage;
  final MedType type;
  final PetType species;
  final String? condition;
  final String? prescribedBy; // vet name
  final String? pharmacy; // "Vet dispensary", "Chewy Pharmacy", etc.
  final String? notes;
  final String? imageUrl;
  final SchedulePreset preset;
  final List<String> times;
  final List<int> daysOfWeek;
  final bool isAsNeeded;
  final DateTime startDate;
  final DateTime? stopDate;
  final int pillCount;
  final int refillThreshold;
  final MealTiming mealTiming;
  final List<String> instructions;
  final int prnMaxPerDay;
  final double prnMinHoursBetween;
  final bool remindersEnabled;
  final bool isTaper;
  final List<TaperStep> taperSteps;
  final int intervalHours;
  final String? firstDoseTime;

  /// Canonical catalog key or 'custom'. Used for interaction checks.
  final String drugKey;

  PetMedication({
    required this.id,
    required this.name,
    this.strength = '',
    this.dosage = '',
    this.type = MedType.pill,
    this.species = PetType.other,
    this.condition,
    this.prescribedBy,
    this.pharmacy,
    this.notes,
    this.imageUrl,
    this.preset = SchedulePreset.clockTimes,
    this.times = const [],
    this.daysOfWeek = const [],
    this.isAsNeeded = false,
    DateTime? startDate,
    this.stopDate,
    this.pillCount = 0,
    this.refillThreshold = 10,
    this.mealTiming = MealTiming.none,
    this.instructions = const [],
    this.prnMaxPerDay = 4,
    this.prnMinHoursBetween = 4.0,
    this.remindersEnabled = true,
    this.isTaper = false,
    this.taperSteps = const [],
    this.intervalHours = 8,
    this.firstDoseTime,
    this.drugKey = 'custom',
  }) : startDate = startDate ?? DateTime.now();

  bool get isActive {
    final now = DateTime.now();
    if (now.isBefore(startDate)) return false;
    if (stopDate != null && now.isAfter(stopDate!)) return false;
    return true;
  }

  bool get isLowStock => pillCount > 0 && pillCount <= refillThreshold;
  bool get isOutOfStock => pillCount <= 0;

  PetMedication copyWith({
    String? name,
    String? strength,
    String? dosage,
    MedType? type,
    PetType? species,
    String? condition,
    String? prescribedBy,
    String? pharmacy,
    String? notes,
    String? imageUrl,
    SchedulePreset? preset,
    List<String>? times,
    List<int>? daysOfWeek,
    bool? isAsNeeded,
    DateTime? startDate,
    DateTime? stopDate,
    bool clearStopDate = false,
    int? pillCount,
    int? refillThreshold,
    MealTiming? mealTiming,
    List<String>? instructions,
    int? prnMaxPerDay,
    double? prnMinHoursBetween,
    bool? remindersEnabled,
    bool? isTaper,
    List<TaperStep>? taperSteps,
    int? intervalHours,
    String? firstDoseTime,
    String? drugKey,
  }) {
    return PetMedication(
      id: id,
      name: name ?? this.name,
      strength: strength ?? this.strength,
      dosage: dosage ?? this.dosage,
      type: type ?? this.type,
      species: species ?? this.species,
      condition: condition ?? this.condition,
      prescribedBy: prescribedBy ?? this.prescribedBy,
      pharmacy: pharmacy ?? this.pharmacy,
      notes: notes ?? this.notes,
      imageUrl: imageUrl ?? this.imageUrl,
      preset: preset ?? this.preset,
      times: times ?? this.times,
      daysOfWeek: daysOfWeek ?? this.daysOfWeek,
      isAsNeeded: isAsNeeded ?? this.isAsNeeded,
      startDate: startDate ?? this.startDate,
      stopDate: clearStopDate ? null : (stopDate ?? this.stopDate),
      pillCount: pillCount ?? this.pillCount,
      refillThreshold: refillThreshold ?? this.refillThreshold,
      mealTiming: mealTiming ?? this.mealTiming,
      instructions: instructions ?? this.instructions,
      prnMaxPerDay: prnMaxPerDay ?? this.prnMaxPerDay,
      prnMinHoursBetween: prnMinHoursBetween ?? this.prnMinHoursBetween,
      remindersEnabled: remindersEnabled ?? this.remindersEnabled,
      isTaper: isTaper ?? this.isTaper,
      taperSteps: taperSteps ?? this.taperSteps,
      intervalHours: intervalHours ?? this.intervalHours,
      firstDoseTime: firstDoseTime ?? this.firstDoseTime,
      drugKey: drugKey ?? this.drugKey,
    );
  }

  Map<String, dynamic> toMap() => {
        'name': name,
        'strength': strength,
        'dosage': dosage,
        'type': type.name,
        'species': _petTypeSerialize(species),
        'condition': condition,
        'prescribedBy': prescribedBy,
        'pharmacy': pharmacy,
        'notes': notes,
        'imageUrl': imageUrl,
        'preset': preset.name,
        'times': times,
        'daysOfWeek': daysOfWeek,
        'isAsNeeded': isAsNeeded,
        'startDate': Timestamp.fromDate(startDate),
        'stopDate': stopDate == null ? null : Timestamp.fromDate(stopDate!),
        'pillCount': pillCount,
        'refillThreshold': refillThreshold,
        'mealTiming': mealTiming.name,
        'instructions': instructions,
        'prnMaxPerDay': prnMaxPerDay,
        'prnMinHoursBetween': prnMinHoursBetween,
        'remindersEnabled': remindersEnabled,
        'isTaper': isTaper,
        'taperSteps': taperSteps.map((s) => s.toMap()).toList(),
        'intervalHours': intervalHours,
        'firstDoseTime': firstDoseTime,
        'drugKey': drugKey,
        'schemaVersion': 1,
      };

  static PetMedication fromDoc(String id, Map<String, dynamic> m) {
    DateTime? ts(dynamic v) {
      if (v is Timestamp) return v.toDate();
      if (v is DateTime) return v;
      return null;
    }

    return PetMedication(
      id: id,
      name: (m['name'] as String?) ?? '',
      strength: (m['strength'] as String?) ?? '',
      dosage: (m['dosage'] as String?) ?? '',
      type: MedType.values.firstWhere(
        (t) => t.name == (m['type'] as String?),
        orElse: () => MedType.pill,
      ),
      species: _petTypeParse(m['species'] as String?),
      condition: m['condition'] as String?,
      prescribedBy: m['prescribedBy'] as String?,
      pharmacy: m['pharmacy'] as String?,
      notes: m['notes'] as String?,
      imageUrl: m['imageUrl'] as String?,
      preset: SchedulePreset.values.firstWhere(
        (p) => p.name == (m['preset'] as String?),
        orElse: () => SchedulePreset.clockTimes,
      ),
      times:
          ((m['times'] as List?) ?? const []).map((e) => e.toString()).toList(),
      daysOfWeek: ((m['daysOfWeek'] as List?) ?? const [])
          .map((e) => (e as num).toInt())
          .toList(),
      isAsNeeded: (m['isAsNeeded'] as bool?) ?? false,
      startDate: ts(m['startDate']) ?? DateTime.now(),
      stopDate: ts(m['stopDate']),
      pillCount: (m['pillCount'] as num?)?.toInt() ?? 0,
      refillThreshold: (m['refillThreshold'] as num?)?.toInt() ?? 10,
      mealTiming: MealTiming.values.firstWhere(
        (t) => t.name == (m['mealTiming'] as String?),
        orElse: () => MealTiming.none,
      ),
      instructions: ((m['instructions'] as List?) ?? const [])
          .map((e) => e.toString())
          .toList(),
      prnMaxPerDay: (m['prnMaxPerDay'] as num?)?.toInt() ?? 4,
      prnMinHoursBetween: (m['prnMinHoursBetween'] as num?)?.toDouble() ?? 4.0,
      remindersEnabled: (m['remindersEnabled'] as bool?) ?? true,
      isTaper: (m['isTaper'] as bool?) ?? false,
      taperSteps: ((m['taperSteps'] as List?) ?? const [])
          .map((e) => TaperStep.fromMap(Map<String, dynamic>.from(e as Map)))
          .toList(),
      intervalHours: (m['intervalHours'] as num?)?.toInt() ?? 8,
      firstDoseTime: m['firstDoseTime'] as String?,
      drugKey: (m['drugKey'] as String?) ?? 'custom',
    );
  }
}

String _petTypeSerialize(PetType t) {
  switch (t) {
    case PetType.dog:
      return 'dog';
    case PetType.cat:
      return 'cat';
    case PetType.other:
      return 'other';
  }
}

class DoseEvent {
  final String id;
  final String medicationId;
  final String medicationName;
  final DateTime scheduledFor;
  final DoseStatus status;
  final DateTime? takenAt;
  final int minutesLate;
  final String? notes;
  final String? reason; // PRN reason (pain / anxiety / etc.)

  const DoseEvent({
    required this.id,
    required this.medicationId,
    required this.medicationName,
    required this.scheduledFor,
    this.status = DoseStatus.scheduled,
    this.takenAt,
    this.minutesLate = 0,
    this.notes,
    this.reason,
  });

  DoseEvent copyWith({
    DoseStatus? status,
    DateTime? takenAt,
    int? minutesLate,
    String? notes,
    String? reason,
  }) =>
      DoseEvent(
        id: id,
        medicationId: medicationId,
        medicationName: medicationName,
        scheduledFor: scheduledFor,
        status: status ?? this.status,
        takenAt: takenAt ?? this.takenAt,
        minutesLate: minutesLate ?? this.minutesLate,
        notes: notes ?? this.notes,
        reason: reason ?? this.reason,
      );

  Map<String, dynamic> toMap() => {
        'medicationId': medicationId,
        'medicationName': medicationName,
        'scheduledFor': Timestamp.fromDate(scheduledFor),
        'status': status.name,
        'takenAt': takenAt == null ? null : Timestamp.fromDate(takenAt!),
        'minutesLate': minutesLate,
        'notes': notes,
        'reason': reason,
      };

  static DoseEvent fromDoc(String id, Map<String, dynamic> m) {
    DateTime? ts(dynamic v) {
      if (v is Timestamp) return v.toDate();
      if (v is DateTime) return v;
      return null;
    }

    return DoseEvent(
      id: id,
      medicationId: (m['medicationId'] as String?) ?? '',
      medicationName: (m['medicationName'] as String?) ?? '',
      scheduledFor: ts(m['scheduledFor']) ?? DateTime.now(),
      status: DoseStatus.values.firstWhere(
        (s) => s.name == (m['status'] as String?),
        orElse: () => DoseStatus.scheduled,
      ),
      takenAt: ts(m['takenAt']),
      minutesLate: (m['minutesLate'] as num?)?.toInt() ?? 0,
      notes: m['notes'] as String?,
      reason: m['reason'] as String?,
    );
  }
}

class UserPrefs {
  final String breakfastTime;
  final String dinnerTime;
  final String bedtimeTime;
  final bool notificationsEnabled;
  final int reminderAdvanceMinutes;

  const UserPrefs({
    this.breakfastTime = '08:00',
    this.dinnerTime = '18:30',
    this.bedtimeTime = '22:00',
    this.notificationsEnabled = true,
    this.reminderAdvanceMinutes = 0,
  });

  UserPrefs copyWith({
    String? breakfastTime,
    String? dinnerTime,
    String? bedtimeTime,
    bool? notificationsEnabled,
    int? reminderAdvanceMinutes,
  }) =>
      UserPrefs(
        breakfastTime: breakfastTime ?? this.breakfastTime,
        dinnerTime: dinnerTime ?? this.dinnerTime,
        bedtimeTime: bedtimeTime ?? this.bedtimeTime,
        notificationsEnabled: notificationsEnabled ?? this.notificationsEnabled,
        reminderAdvanceMinutes:
            reminderAdvanceMinutes ?? this.reminderAdvanceMinutes,
      );

  Map<String, dynamic> toMap() => {
        'breakfastTime': breakfastTime,
        'dinnerTime': dinnerTime,
        'bedtimeTime': bedtimeTime,
        'notificationsEnabled': notificationsEnabled,
        'reminderAdvanceMinutes': reminderAdvanceMinutes,
      };

  static UserPrefs fromMap(Map<String, dynamic>? m) {
    if (m == null) return const UserPrefs();
    return UserPrefs(
      breakfastTime: (m['breakfastTime'] as String?) ?? '08:00',
      dinnerTime: (m['dinnerTime'] as String?) ?? '18:30',
      bedtimeTime: (m['bedtimeTime'] as String?) ?? '22:00',
      notificationsEnabled: (m['notificationsEnabled'] as bool?) ?? true,
      reminderAdvanceMinutes:
          (m['reminderAdvanceMinutes'] as num?)?.toInt() ?? 0,
    );
  }
}

class _DayRatio {
  final int total;
  final int kept;
  const _DayRatio({required this.total, required this.kept});
}

// ═══════════════════════════════════════════════════════════════════════════
// VETERINARY DRUG CATALOG
// Species-aware. Each entry declares which species it's SAFE for.
// The UI filters the picker by the selected pet's species. Human OTCs
// toxic to cats (Tylenol, Ibuprofen, Aspirin, Naproxen) are marked
// dogOnly and will NEVER appear when a cat is selected.
//
// Dosing guidance is TYPICAL — not a prescription. The UI always shows
// "confirm with your vet" on auto-filled hints.
// ═══════════════════════════════════════════════════════════════════════════

class _VetDrugInfo {
  final String canonical;
  final List<String> aliases;
  final Set<PetType> safeFor; // {dog}, {cat}, {dog, cat}
  final String defaultInstruction;
  final MealTiming defaultTiming;
  final String? commonCondition;
  final String? dosageHint; // human-readable, e.g. "2 mg/kg PO twice daily"
  final bool isInjection;
  final bool isPRN;

  /// Optional default interval in days for long-acting drugs (Cytopoint 28-42,
  /// Bravecto 84, Convenia 14). null means daily-or-less.
  final int? defaultIntervalDays;

  /// WARN if this drug requires breed-awareness (e.g. ivermectin + MDR1 Collies).
  final String? breedWarning;

  const _VetDrugInfo({
    required this.canonical,
    this.aliases = const [],
    required this.safeFor,
    this.defaultInstruction = '',
    this.defaultTiming = MealTiming.none,
    this.commonCondition,
    this.dosageHint,
    this.isInjection = false,
    this.isPRN = false,
    this.defaultIntervalDays,
    this.breedWarning,
  });

  bool safeForSpecies(PetType t) => safeFor.contains(t);
}

class _VetDrugDB {
  static const Set<PetType> _dogOnly = {PetType.dog};
  static const Set<PetType> _catOnly = {PetType.cat};
  static const Set<PetType> _both = {PetType.dog, PetType.cat};

  static const List<_VetDrugInfo> all = [
    // ── NSAID / pain (DOGS ONLY for vet NSAIDs; NSAIDs dangerous for cats) ──
    _VetDrugInfo(
      canonical: 'carprofen',
      aliases: ['rimadyl', 'novox', 'vetprofen'],
      safeFor: _dogOnly,
      defaultInstruction:
          'NEVER give with another NSAID or steroid. Monitor for vomiting, loss of appetite, or dark stools.',
      defaultTiming: MealTiming.withMeal,
      commonCondition: 'Arthritis / Post-surgical pain',
      dosageHint: '2 mg/kg PO twice daily, or 4.4 mg/kg once daily',
    ),
    _VetDrugInfo(
      canonical: 'meloxicam',
      aliases: ['metacam'],
      safeFor: _dogOnly,
      defaultInstruction:
          'Dogs only for chronic use. Give with food. Never combine with other NSAIDs or steroids.',
      defaultTiming: MealTiming.withMeal,
      commonCondition: 'Arthritis / Inflammation',
      dosageHint: '0.1 mg/kg once daily (after initial 0.2 mg/kg loading)',
    ),
    _VetDrugInfo(
      canonical: 'grapiprant',
      aliases: ['galliprant'],
      safeFor: _dogOnly,
      defaultInstruction:
          'Give on empty stomach. Do not combine with other NSAIDs or steroids.',
      defaultTiming: MealTiming.emptyStomach,
      commonCondition: 'Arthritis pain',
      dosageHint: '2 mg/kg once daily',
    ),
    _VetDrugInfo(
      canonical: 'firocoxib',
      aliases: ['previcox'],
      safeFor: _dogOnly,
      defaultInstruction: 'Dogs only. Monitor for GI upset.',
      defaultTiming: MealTiming.withMeal,
      commonCondition: 'Arthritis / Post-surgical pain',
      dosageHint: '5 mg/kg once daily',
    ),
    _VetDrugInfo(
      canonical: 'robenacoxib',
      aliases: ['onsior'],
      safeFor: _both,
      defaultInstruction:
          'Short-term use. Follow vet directions carefully. Cats: max 6 days.',
      defaultTiming: MealTiming.emptyStomach,
      commonCondition: 'Post-surgical / Acute pain',
      dosageHint: '1 mg/kg once daily',
    ),
    _VetDrugInfo(
      canonical: 'gabapentin',
      aliases: [],
      safeFor: _both,
      defaultInstruction:
          'Liquid form for cats must be XYLITOL-FREE — xylitol is toxic to dogs.',
      commonCondition: 'Neuropathic pain / Anxiety / Seizures',
      dosageHint: 'Dogs: 5-30 mg/kg q8-12h. Cats: 5-20 mg/kg q12h.',
    ),
    _VetDrugInfo(
      canonical: 'tramadol',
      aliases: [],
      safeFor: _both,
      defaultInstruction:
          'May cause sedation. Do not combine with SSRIs, MAOIs, or human serotonin drugs.',
      commonCondition: 'Pain',
      dosageHint: 'Dogs: 2-5 mg/kg q8-12h. Cats: 1-2 mg/kg q12h.',
    ),
    _VetDrugInfo(
      canonical: 'amantadine',
      aliases: [],
      safeFor: _both,
      defaultInstruction: 'Often used as adjunct for chronic pain.',
      commonCondition: 'Chronic pain',
      dosageHint: '3-5 mg/kg once daily',
    ),

    // ── Allergy / skin ──
    _VetDrugInfo(
      canonical: 'oclacitinib',
      aliases: ['apoquel'],
      safeFor: _dogOnly,
      defaultInstruction:
          'Dogs over 12 months only. Twice daily for first 14 days, then once daily. Monitor for infections.',
      commonCondition: 'Itch / Allergic dermatitis',
      dosageHint: '0.4-0.6 mg/kg twice daily loading, then once daily',
    ),
    _VetDrugInfo(
      canonical: 'lokivetmab',
      aliases: ['cytopoint'],
      safeFor: _dogOnly,
      defaultInstruction: 'Injectable. Lasts 4-8 weeks. Given at vet clinic.',
      isInjection: true,
      defaultIntervalDays: 35, // midpoint 4-6 weeks
      commonCondition: 'Atopic dermatitis',
      dosageHint: '2 mg/kg subcutaneous injection',
    ),
    _VetDrugInfo(
      canonical: 'cyclosporine',
      aliases: ['atopica'],
      safeFor: _both,
      defaultInstruction:
          'Give on empty stomach for best absorption (2 hours before food).',
      defaultTiming: MealTiming.emptyStomach,
      commonCondition: 'Atopic dermatitis / Immune conditions',
      dosageHint: 'Dogs: 5 mg/kg once daily. Cats: 7 mg/kg once daily.',
    ),
    _VetDrugInfo(
      canonical: 'diphenhydramine',
      aliases: ['benadryl'],
      safeFor: _both,
      defaultInstruction:
          'Use PLAIN Benadryl only — NEVER combination products with decongestants or acetaminophen. May cause sedation.',
      isPRN: true,
      commonCondition: 'Mild allergies / Anxiety',
      dosageHint: 'Dogs: 2-4 mg/kg q8-12h. Cats: 0.5-2 mg/kg q8-12h.',
    ),
    _VetDrugInfo(
      canonical: 'cetirizine',
      aliases: ['zyrtec'],
      safeFor: _both,
      defaultInstruction:
          'Use PLAIN cetirizine — NEVER Zyrtec-D (pseudoephedrine is toxic).',
      commonCondition: 'Allergies',
      dosageHint: 'Dogs: 1 mg/kg once daily. Cats: 2.5-5 mg once daily.',
    ),

    // ── Anxiety / behavior ──
    _VetDrugInfo(
      canonical: 'trazodone',
      aliases: [],
      safeFor: _both,
      defaultInstruction:
          'Give 1-2 hours before stressful event (vet visit, fireworks, travel).',
      isPRN: true,
      commonCondition: 'Situational anxiety',
      dosageHint: 'Dogs: 3-7 mg/kg. Cats: 50-100 mg per cat.',
    ),
    _VetDrugInfo(
      canonical: 'fluoxetine',
      aliases: ['reconcile', 'prozac'],
      safeFor: _both,
      defaultInstruction:
          'Takes 4-6 weeks for full effect. Do not stop abruptly.',
      commonCondition: 'Chronic anxiety / Behavior disorders',
      dosageHint: 'Dogs: 1-2 mg/kg once daily. Cats: 0.5-1 mg/kg once daily.',
    ),
    _VetDrugInfo(
      canonical: 'clomipramine',
      aliases: ['clomicalm'],
      safeFor: _dogOnly,
      defaultInstruction: 'Give with food.',
      defaultTiming: MealTiming.withMeal,
      commonCondition: 'Separation anxiety',
      dosageHint: '1-3 mg/kg twice daily',
    ),
    _VetDrugInfo(
      canonical: 'alprazolam',
      aliases: [],
      safeFor: _both,
      defaultInstruction:
          'Controlled substance. Use only as prescribed. May cause sedation or paradoxical excitement.',
      isPRN: true,
      commonCondition: 'Acute anxiety / Noise phobia',
      dosageHint: 'Dogs: 0.02-0.1 mg/kg. Cats: 0.125-0.25 mg per cat.',
    ),
    _VetDrugInfo(
      canonical: 'dexmedetomidine gel',
      aliases: ['sileo'],
      safeFor: _dogOnly,
      defaultInstruction:
          'Apply to dog\'s cheek with finger cot. For noise aversion only. Do not swallow.',
      isPRN: true,
      commonCondition: 'Noise aversion (fireworks / thunder)',
      dosageHint: 'Dose per vet — based on body weight table',
    ),

    // ── Antibiotics ──
    _VetDrugInfo(
      canonical: 'amoxicillin-clavulanate',
      aliases: ['clavamox'],
      safeFor: _both,
      defaultInstruction: 'Finish entire course even if pet seems better.',
      defaultTiming: MealTiming.withMeal,
      commonCondition: 'Bacterial infection',
      dosageHint:
          'Dogs: 12.5-25 mg/kg twice daily. Cats: 12.5-25 mg/kg twice daily.',
    ),
    _VetDrugInfo(
      canonical: 'amoxicillin',
      aliases: [],
      safeFor: _both,
      defaultInstruction: 'Finish entire course.',
      commonCondition: 'Bacterial infection',
      dosageHint: '11-22 mg/kg twice daily',
    ),
    _VetDrugInfo(
      canonical: 'enrofloxacin',
      aliases: ['baytril'],
      safeFor: _both,
      defaultInstruction:
          'CATS: do not exceed 5 mg/kg once daily — higher doses can cause retinal damage and blindness.',
      commonCondition: 'Bacterial infection (UTI / skin / resp)',
      dosageHint: 'Dogs: 5-20 mg/kg once daily. Cats: max 5 mg/kg once daily.',
    ),
    _VetDrugInfo(
      canonical: 'cefpodoxime',
      aliases: ['simplicef'],
      safeFor: _dogOnly,
      defaultInstruction: 'Finish entire course.',
      commonCondition: 'Skin / soft tissue infection',
      dosageHint: '5-10 mg/kg once daily',
    ),
    _VetDrugInfo(
      canonical: 'clindamycin',
      aliases: [],
      safeFor: _both,
      defaultInstruction:
          'For cats, follow with small water syringe to prevent esophageal irritation.',
      commonCondition: 'Dental / bone / soft tissue infection',
      dosageHint: 'Dogs: 5.5-11 mg/kg q12h. Cats: 11 mg/kg q24h.',
    ),
    _VetDrugInfo(
      canonical: 'metronidazole',
      aliases: ['flagyl'],
      safeFor: _both,
      defaultInstruction:
          'Tastes bitter — compounded formulations often work better for cats.',
      defaultTiming: MealTiming.withMeal,
      commonCondition: 'GI infection / Giardia / IBD',
      dosageHint: '10-25 mg/kg twice daily (short courses only)',
    ),
    _VetDrugInfo(
      canonical: 'doxycycline',
      aliases: [],
      safeFor: _both,
      defaultInstruction:
          'Follow with water to prevent esophageal ulcer — especially critical in cats.',
      commonCondition: 'Tick-borne disease / Respiratory infection',
      dosageHint: '5-10 mg/kg once daily',
    ),
    _VetDrugInfo(
      canonical: 'cefovecin',
      aliases: ['convenia'],
      safeFor: _both,
      defaultInstruction:
          'Long-acting injection. Single dose lasts about 14 days. Given at clinic.',
      isInjection: true,
      defaultIntervalDays: 14,
      commonCondition: 'Skin / soft tissue infection',
      dosageHint: '8 mg/kg subcutaneous',
    ),

    // ── Anti-emetic / GI ──
    _VetDrugInfo(
      canonical: 'maropitant',
      aliases: ['cerenia'],
      safeFor: _both,
      defaultInstruction:
          'Can be given 1-2 hours before car travel to prevent motion sickness.',
      commonCondition: 'Nausea / Vomiting / Motion sickness',
      dosageHint:
          'Dogs: 2 mg/kg once daily (8 mg/kg for motion). Cats: 1 mg/kg.',
    ),
    _VetDrugInfo(
      canonical: 'metoclopramide',
      aliases: ['reglan'],
      safeFor: _both,
      defaultInstruction: 'Give 30 min before meals.',
      defaultTiming: MealTiming.beforeMeal,
      commonCondition: 'Nausea / Delayed gastric emptying',
      dosageHint: '0.2-0.5 mg/kg q6-8h',
    ),
    _VetDrugInfo(
      canonical: 'famotidine',
      aliases: ['pepcid'],
      safeFor: _both,
      defaultInstruction: 'Use plain famotidine only (no Pepcid Complete).',
      commonCondition: 'Acid reflux / Stomach upset',
      dosageHint: '0.5-1 mg/kg once or twice daily',
    ),
    _VetDrugInfo(
      canonical: 'omeprazole',
      aliases: ['prilosec'],
      safeFor: _both,
      defaultInstruction: 'Give 30 min before meals. Short-term use preferred.',
      defaultTiming: MealTiming.beforeMeal,
      commonCondition: 'Acid reflux / Gastric ulcer',
      dosageHint: '0.5-1 mg/kg once daily',
    ),
    _VetDrugInfo(
      canonical: 'sucralfate',
      aliases: ['carafate'],
      safeFor: _both,
      defaultInstruction:
          'Give on empty stomach. Separate from other meds by 2 hours.',
      defaultTiming: MealTiming.emptyStomach,
      commonCondition: 'GI ulcer / Esophagitis',
      dosageHint: 'Dogs: 0.5-1 g per dog. Cats: 0.25-0.5 g per cat.',
    ),
    _VetDrugInfo(
      canonical: 's-adenosylmethionine',
      aliases: ['denamarin', 'sam-e'],
      safeFor: _both,
      defaultInstruction:
          'Give on empty stomach — 1 hour before food for best absorption.',
      defaultTiming: MealTiming.emptyStomach,
      commonCondition: 'Liver support',
      dosageHint: '17-22 mg/kg once daily',
    ),

    // ── Heart ──
    _VetDrugInfo(
      canonical: 'pimobendan',
      aliases: ['vetmedin'],
      safeFor: _dogOnly,
      defaultInstruction:
          'Give on empty stomach for best absorption (1 hour before food).',
      defaultTiming: MealTiming.emptyStomach,
      commonCondition: 'Heart failure / Mitral valve disease',
      dosageHint: '0.25-0.3 mg/kg twice daily',
    ),
    _VetDrugInfo(
      canonical: 'enalapril',
      aliases: [],
      safeFor: _both,
      defaultInstruction: 'Monitor kidney function regularly.',
      commonCondition: 'Heart failure / Hypertension',
      dosageHint: '0.25-0.5 mg/kg once or twice daily',
    ),
    _VetDrugInfo(
      canonical: 'benazepril',
      aliases: [],
      safeFor: _both,
      defaultInstruction: 'Monitor kidney values.',
      commonCondition: 'Heart failure / Kidney disease',
      dosageHint: '0.25-0.5 mg/kg once daily',
    ),
    _VetDrugInfo(
      canonical: 'furosemide',
      aliases: ['lasix', 'salix'],
      safeFor: _both,
      defaultInstruction:
          'Diuretic — ensure fresh water always available. Frequent urination expected.',
      commonCondition: 'Heart failure / Edema',
      dosageHint: '1-4 mg/kg q8-12h (adjusted per response)',
    ),
    _VetDrugInfo(
      canonical: 'spironolactone',
      aliases: [],
      safeFor: _both,
      defaultInstruction: 'Potassium-sparing diuretic. Monitor potassium.',
      commonCondition: 'Heart failure',
      dosageHint: '1-2 mg/kg once or twice daily',
    ),

    // ── Seizure ──
    _VetDrugInfo(
      canonical: 'phenobarbital',
      aliases: [],
      safeFor: _both,
      defaultInstruction:
          'Controlled substance. NEVER stop abruptly. Monitor liver enzymes.',
      commonCondition: 'Seizures / Epilepsy',
      dosageHint: '2-4 mg/kg twice daily',
    ),
    _VetDrugInfo(
      canonical: 'levetiracetam',
      aliases: ['keppra'],
      safeFor: _both,
      defaultInstruction: 'Do not stop suddenly. Give at same times daily.',
      commonCondition: 'Seizures',
      dosageHint: '20-30 mg/kg q8h (or extended-release q12h)',
    ),
    _VetDrugInfo(
      canonical: 'zonisamide',
      aliases: [],
      safeFor: _both,
      defaultInstruction: 'Give with food.',
      defaultTiming: MealTiming.withMeal,
      commonCondition: 'Seizures',
      dosageHint: 'Dogs: 5-10 mg/kg twice daily. Cats: 5 mg/kg twice daily.',
    ),
    _VetDrugInfo(
      canonical: 'potassium bromide',
      aliases: ['kbr'],
      safeFor: _dogOnly,
      defaultInstruction:
          'Dogs only — toxic to cats. Keep salt intake consistent.',
      commonCondition: 'Refractory seizures',
      dosageHint: '30-40 mg/kg once daily (load higher initially)',
    ),

    // ── Endocrine ──
    _VetDrugInfo(
      canonical: 'trilostane',
      aliases: ['vetoryl'],
      safeFor: _dogOnly,
      defaultInstruction:
          'Give with food. Monitor for lethargy/vomiting — Addisonian crisis risk.',
      defaultTiming: MealTiming.withMeal,
      commonCondition: 'Cushing\'s disease',
      dosageHint: '2-6 mg/kg once or twice daily',
    ),
    _VetDrugInfo(
      canonical: 'methimazole',
      aliases: ['tapazole', 'felimazole'],
      safeFor: _catOnly,
      defaultInstruction:
          'Cats only. Wear gloves when handling. Monitor CBC and thyroid levels.',
      commonCondition: 'Hyperthyroidism',
      dosageHint: 'Cats: 2.5-5 mg twice daily initial',
    ),
    _VetDrugInfo(
      canonical: 'levothyroxine',
      aliases: ['thyro-tabs', 'soloxine'],
      safeFor: _dogOnly,
      defaultInstruction:
          'Dogs primarily. Give on empty stomach, consistent timing daily.',
      defaultTiming: MealTiming.emptyStomach,
      commonCondition: 'Hypothyroidism',
      dosageHint: 'Dogs: 0.02 mg/kg twice daily initial',
    ),
    _VetDrugInfo(
      canonical: 'insulin (vetsulin / prozinc)',
      aliases: ['vetsulin', 'prozinc', 'caninsulin'],
      safeFor: _both,
      defaultInstruction:
          'Refrigerate. Mix by rolling — never shake. Rotate injection sites. Give after a meal.',
      defaultTiming: MealTiming.afterMeal,
      isInjection: true,
      commonCondition: 'Diabetes',
      dosageHint: 'Starting: 0.25-0.5 U/kg twice daily (adjust per BG)',
    ),

    // ── Parasite prevention (usually every 30 days or longer) ──
    _VetDrugInfo(
      canonical: 'ivermectin-pyrantel',
      aliases: ['heartgard', 'iverhart', 'tri-heart'],
      safeFor: _dogOnly,
      defaultInstruction:
          'Monthly chewable. Test for heartworm first if missed >2 doses.',
      isPRN: false,
      defaultIntervalDays: 30,
      commonCondition: 'Heartworm prevention',
      dosageHint: 'Per weight chart on package',
      breedWarning:
          'Collies, Shelties, Aussies, and other MDR1 breeds can be sensitive. Use Heartgard-labeled products (safe at prevention dose) and discuss with vet.',
    ),
    _VetDrugInfo(
      canonical: 'afoxolaner',
      aliases: ['nexgard'],
      safeFor: _dogOnly,
      defaultInstruction: 'Monthly chewable. Give with food.',
      defaultTiming: MealTiming.withMeal,
      defaultIntervalDays: 30,
      commonCondition: 'Flea / tick prevention',
    ),
    _VetDrugInfo(
      canonical: 'fluralaner',
      aliases: ['bravecto'],
      safeFor: _both,
      defaultInstruction:
          'Dogs: every 12 weeks oral. Cats: every 12 weeks topical.',
      defaultIntervalDays: 84,
      commonCondition: 'Flea / tick prevention',
    ),
    _VetDrugInfo(
      canonical: 'sarolaner',
      aliases: ['simparica', 'simparica trio'],
      safeFor: _dogOnly,
      defaultInstruction: 'Monthly chewable.',
      defaultIntervalDays: 30,
      commonCondition: 'Flea / tick (trio adds heartworm)',
    ),
    _VetDrugInfo(
      canonical: 'selamectin',
      aliases: ['revolution'],
      safeFor: _both,
      defaultInstruction:
          'Monthly topical. Apply to skin between shoulder blades.',
      defaultIntervalDays: 30,
      commonCondition: 'Flea / heartworm / ear mites',
    ),
    _VetDrugInfo(
      canonical: 'milbemycin-lufenuron',
      aliases: ['sentinel', 'interceptor'],
      safeFor: _both,
      defaultInstruction: 'Monthly chewable. Give with food.',
      defaultTiming: MealTiming.withMeal,
      defaultIntervalDays: 30,
      commonCondition: 'Heartworm / intestinal parasites',
    ),

    // ── Dewormers ──
    _VetDrugInfo(
      canonical: 'fenbendazole',
      aliases: ['panacur', 'safe-guard'],
      safeFor: _both,
      defaultInstruction: 'Often given as 3-5 day course. Give with food.',
      defaultTiming: MealTiming.withMeal,
      commonCondition: 'Intestinal parasites / Giardia',
      dosageHint: '50 mg/kg once daily for 3-5 days',
    ),
    _VetDrugInfo(
      canonical: 'praziquantel',
      aliases: ['drontal'],
      safeFor: _both,
      defaultInstruction: 'Single dose for tapeworm treatment.',
      commonCondition: 'Tapeworm',
      dosageHint: '5-10 mg/kg single dose',
    ),

    // ── Eye / ear ──
    _VetDrugInfo(
      canonical: 'neomycin-polymyxin-bacitracin ophthalmic',
      aliases: ['neo-poly-bac', 'triple antibiotic ophthalmic'],
      safeFor: _both,
      defaultInstruction:
          'Gently pull down lower lid. Apply ribbon along inside of eyelid.',
      commonCondition: 'Bacterial conjunctivitis',
      dosageHint: 'Apply q4-8h as prescribed',
    ),
    _VetDrugInfo(
      canonical: 'cyclosporine ophthalmic',
      aliases: ['optimmune'],
      safeFor: _dogOnly,
      defaultInstruction: 'Daily drop for dry eye (KCS).',
      commonCondition: 'Dry eye / KCS',
      dosageHint: '1 drop q12h',
    ),
    _VetDrugInfo(
      canonical: 'mometasone otic',
      aliases: ['mometamax'],
      safeFor: _dogOnly,
      defaultInstruction:
          'Shake well. Clean ear before application. Massage base of ear.',
      commonCondition: 'Ear infection (dogs)',
    ),
  ];

  /// Get entries safe for the given species (plus "both" safes).
  static List<_VetDrugInfo> forSpecies(PetType species) {
    if (species == PetType.other) {
      // "Other" pets (rabbits, birds, reptiles) have entirely different drug
      // lists — we return empty so the user is forced to type custom names.
      return const [];
    }
    return all.where((d) => d.safeForSpecies(species)).toList();
  }

  static _VetDrugInfo? lookup(String rawName, [PetType? species]) {
    if (rawName.trim().isEmpty) return null;
    final q = rawName.toLowerCase().trim();
    final pool = species == null ? all : forSpecies(species);
    for (final info in pool) {
      if (info.canonical == q) return info;
      for (final a in info.aliases) {
        if (a.toLowerCase() == q) return info;
      }
    }
    for (final info in pool) {
      if (info.canonical.contains(q) || q.contains(info.canonical)) {
        return info;
      }
      for (final a in info.aliases) {
        if (a.toLowerCase().contains(q) || q.contains(a.toLowerCase())) {
          return info;
        }
      }
    }
    return null;
  }

  /// Suggest drug names for autocomplete, filtered by species.
  static List<String> suggestNames(String prefix, PetType species) {
    if (prefix.trim().isEmpty) return const [];
    final q = prefix.toLowerCase().trim();
    final pool = forSpecies(species);
    final seen = <String>{};
    final out = <String>[];
    for (final info in pool) {
      if (info.canonical.startsWith(q)) {
        if (seen.add(info.canonical)) out.add(_title(info.canonical));
      }
      for (final a in info.aliases) {
        if (a.toLowerCase().startsWith(q)) {
          if (seen.add(a.toLowerCase())) out.add(_title(a));
        }
      }
      if (out.length >= 8) break;
    }
    return out;
  }

  /// Dangerous-for-species flag. If user manually types a drug known to be
  /// toxic to the selected species, we warn before allowing save.
  static String? speciesSafetyWarning(String rawName, PetType species) {
    final q = rawName.toLowerCase().trim();
    if (q.isEmpty) return null;
    // Hard-coded danger list — more permissive than the catalog which only
    // includes vet-appropriate drugs.
    const dangerousForCats = {
      'tylenol': 'Acetaminophen is FATAL to cats at normal doses. Never give.',
      'acetaminophen':
          'Acetaminophen is FATAL to cats at normal doses. Never give.',
      'paracetamol':
          'Acetaminophen is FATAL to cats at normal doses. Never give.',
      'ibuprofen':
          'Ibuprofen causes severe kidney damage and ulcers in cats. Never give.',
      'advil':
          'Advil (ibuprofen) causes severe kidney damage and ulcers in cats.',
      'motrin':
          'Motrin (ibuprofen) causes severe kidney damage and ulcers in cats.',
      'aspirin':
          'Aspirin has a very narrow safety margin in cats. Only under vet supervision.',
      'bayer':
          'Bayer (aspirin) has a very narrow safety margin in cats. Only under vet supervision.',
      'naproxen': 'Naproxen is severely toxic to cats. Never give.',
      'aleve': 'Aleve (naproxen) is severely toxic to cats. Never give.',
      'rimadyl': 'Rimadyl (carprofen) is for dogs — do NOT give to cats.',
      'carprofen': 'Carprofen is for dogs — do NOT give to cats.',
      'meloxicam':
          'Meloxicam is approved for short-term use in cats under vet supervision only.',
      'previcox': 'Previcox (firocoxib) is for dogs — do NOT give to cats.',
      'galliprant': 'Galliprant is for dogs — do NOT give to cats.',
      'apoquel': 'Apoquel (oclacitinib) is for dogs — do NOT give to cats.',
      'pepcid complete':
          'Pepcid Complete contains additives unsafe for pets. Use plain famotidine.',
      'zyrtec-d': 'Zyrtec-D contains pseudoephedrine — TOXIC to cats and dogs.',
    };
    const dangerousForDogs = {
      'tylenol':
          'Acetaminophen is toxic to dogs at normal human doses. Only under vet supervision.',
      'xylitol': 'Xylitol is FATAL to dogs. Check labels carefully.',
      'ibuprofen':
          'Ibuprofen causes ulcers and kidney damage in dogs. Never give without vet Rx.',
      'advil':
          'Advil (ibuprofen) causes ulcers and kidney damage in dogs. Never give.',
    };
    final pool = species == PetType.cat ? dangerousForCats : dangerousForDogs;
    for (final entry in pool.entries) {
      if (q.contains(entry.key)) return entry.value;
    }
    return null;
  }

  static String _title(String s) => s
      .split('-')
      .map((w) => w.isEmpty ? w : w[0].toUpperCase() + w.substring(1))
      .join('-');
}

// ═══════════════════════════════════════════════════════════════════════════
// INTERACTION CHECKER
// Pet-specific interactions. Conservative list — only well-established
// clinically important pairs. If not sure, DON'T include it.
// ═══════════════════════════════════════════════════════════════════════════

class InteractionResult {
  final String drugA;
  final String drugB;
  final InteractionSeverity severity;
  final String summary;

  const InteractionResult({
    required this.drugA,
    required this.drugB,
    required this.severity,
    required this.summary,
  });
}

class _InteractionPair {
  final String a;
  final String b;
  final InteractionSeverity severity;
  final String summary;

  const _InteractionPair({
    required this.a,
    required this.b,
    required this.severity,
    required this.summary,
  });
}

class InteractionCheck {
  /// Pet-specific interactions. Keys use canonical drug names from
  /// _VetDrugDB for reliable matching.
  static const List<_InteractionPair> _pairs = [
    // NSAID + NSAID / NSAID + steroid — GI ulceration, kidney damage
    _InteractionPair(
      a: 'carprofen',
      b: 'meloxicam',
      severity: InteractionSeverity.avoid,
      summary:
          'Never combine two NSAIDs. High risk of GI ulceration, kidney damage, liver toxicity.',
    ),
    _InteractionPair(
      a: 'carprofen',
      b: 'grapiprant',
      severity: InteractionSeverity.avoid,
      summary:
          'Never combine. Use washout period of 5-7 days when switching NSAIDs.',
    ),
    _InteractionPair(
      a: 'carprofen',
      b: 'firocoxib',
      severity: InteractionSeverity.avoid,
      summary: 'Never combine two NSAIDs.',
    ),
    _InteractionPair(
      a: 'meloxicam',
      b: 'firocoxib',
      severity: InteractionSeverity.avoid,
      summary: 'Never combine two NSAIDs.',
    ),
    _InteractionPair(
      a: 'meloxicam',
      b: 'grapiprant',
      severity: InteractionSeverity.avoid,
      summary: 'Never combine two NSAIDs.',
    ),
    // NSAID + ACE inhibitor — kidney injury risk
    _InteractionPair(
      a: 'carprofen',
      b: 'enalapril',
      severity: InteractionSeverity.caution,
      summary:
          'Increased risk of acute kidney injury. Monitor kidney values closely.',
    ),
    _InteractionPair(
      a: 'carprofen',
      b: 'benazepril',
      severity: InteractionSeverity.caution,
      summary:
          'Increased risk of acute kidney injury. Monitor kidney values closely.',
    ),
    _InteractionPair(
      a: 'meloxicam',
      b: 'enalapril',
      severity: InteractionSeverity.caution,
      summary: 'Increased risk of acute kidney injury.',
    ),
    // NSAID + diuretic
    _InteractionPair(
      a: 'carprofen',
      b: 'furosemide',
      severity: InteractionSeverity.caution,
      summary: 'Increased kidney injury risk, especially in dehydrated pets.',
    ),
    // Tramadol + SSRI — serotonin syndrome
    _InteractionPair(
      a: 'tramadol',
      b: 'fluoxetine',
      severity: InteractionSeverity.caution,
      summary: 'Serotonin syndrome risk. Monitor for agitation, tremors.',
    ),
    _InteractionPair(
      a: 'tramadol',
      b: 'clomipramine',
      severity: InteractionSeverity.caution,
      summary: 'Serotonin syndrome risk.',
    ),
    // Metronidazole + cyclosporine
    _InteractionPair(
      a: 'metronidazole',
      b: 'cyclosporine',
      severity: InteractionSeverity.caution,
      summary:
          'Metronidazole can raise cyclosporine levels. Monitor cyclosporine trough.',
    ),
    // Enrofloxacin + metal antacids
    _InteractionPair(
      a: 'enrofloxacin',
      b: 'sucralfate',
      severity: InteractionSeverity.caution,
      summary: 'Reduces antibiotic absorption. Separate by at least 2 hours.',
    ),
    // Levothyroxine absorption
    _InteractionPair(
      a: 'levothyroxine',
      b: 'sucralfate',
      severity: InteractionSeverity.caution,
      summary: 'Sucralfate reduces absorption. Separate by 4 hours.',
    ),
    // Benzo + opioid — CNS depression
    _InteractionPair(
      a: 'alprazolam',
      b: 'tramadol',
      severity: InteractionSeverity.caution,
      summary: 'Additive sedation and CNS depression.',
    ),
    // Phenobarbital + many drugs (induction)
    _InteractionPair(
      a: 'phenobarbital',
      b: 'doxycycline',
      severity: InteractionSeverity.monitor,
      summary: 'Phenobarbital reduces doxycycline levels.',
    ),
    _InteractionPair(
      a: 'phenobarbital',
      b: 'fluoxetine',
      severity: InteractionSeverity.monitor,
      summary: 'Phenobarbital reduces fluoxetine levels.',
    ),
    // NSAIDs + sucralfate absorption issue
    _InteractionPair(
      a: 'carprofen',
      b: 'sucralfate',
      severity: InteractionSeverity.monitor,
      summary: 'Separate by 2 hours to maintain absorption.',
    ),
    // Trilostane + spironolactone (aldosterone interaction)
    _InteractionPair(
      a: 'trilostane',
      b: 'spironolactone',
      severity: InteractionSeverity.caution,
      summary: 'Additive potassium elevation. Monitor potassium and cortisol.',
    ),
  ];

  static String _canonical(String name, [PetType? species]) {
    final info = _VetDrugDB.lookup(name, species);
    return info?.canonical ?? name.toLowerCase().trim();
  }

  static List<InteractionResult> scan(List<PetMedication> meds) {
    final results = <InteractionResult>[];
    final seen = <String>{};
    final canonicals = meds.map((m) => _canonical(m.name, m.species)).toList();

    for (int i = 0; i < meds.length; i++) {
      for (int j = i + 1; j < meds.length; j++) {
        final a = canonicals[i];
        final b = canonicals[j];
        for (final p in _pairs) {
          final matches = (p.a == a && p.b == b) || (p.a == b && p.b == a);
          if (!matches) continue;
          final key = a.compareTo(b) < 0 ? '$a|$b' : '$b|$a';
          if (seen.add(key)) {
            results.add(InteractionResult(
              drugA: meds[i].name,
              drugB: meds[j].name,
              severity: p.severity,
              summary: p.summary,
            ));
          }
        }
      }
    }
    results.sort((a, b) => a.severity.index.compareTo(b.severity.index));
    return results;
  }

  static List<InteractionResult> checkAgainst(
    String newMedName,
    PetType species,
    List<PetMedication> existing,
  ) {
    final newCanonical = _canonical(newMedName, species);
    final results = <InteractionResult>[];
    for (final m in existing) {
      final existingCanonical = _canonical(m.name, m.species);
      for (final p in _pairs) {
        final matches = (p.a == newCanonical && p.b == existingCanonical) ||
            (p.a == existingCanonical && p.b == newCanonical);
        if (matches) {
          results.add(InteractionResult(
            drugA: newMedName,
            drugB: m.name,
            severity: p.severity,
            summary: p.summary,
          ));
        }
      }
    }
    results.sort((a, b) => a.severity.index.compareTo(b.severity.index));
    return results;
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// NOTIFICATION SERVICE
// Same pattern as human widget: write to users/{uid}/scheduled_reminders and
// let the host app fire the actual local notification. This keeps the custom
// widget decoupled from flutter_local_notifications init state.
// ═══════════════════════════════════════════════════════════════════════════

class _Notify {
  static bool _probed = false;
  static bool _available = false;

  static Future<bool> probe(String? uid) async {
    if (_probed) return _available;
    _probed = true;
    if (uid == null) {
      _available = false;
      return false;
    }
    try {
      final snap = await FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .get()
          .timeout(const Duration(seconds: 3));
      _available = (snap.data()?['notifications_enabled'] as bool?) ?? false;
    } catch (_) {
      _available = false;
    }
    return _available;
  }

  static Future<void> schedule({
    required String uid,
    required String petId,
    required String petName,
    required String medId,
    required String medName,
    required String dosage,
    required DateTime fireAt,
    int advanceMinutes = 0,
  }) async {
    try {
      final fireActual = fireAt.subtract(Duration(minutes: advanceMinutes));
      await FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('scheduled_reminders')
          .add({
        'petId': petId,
        'petName': petName,
        'medicationId': medId,
        'title': '$petName needs $medName',
        'body': dosage.isEmpty ? 'Tap to log the dose' : '$dosage • tap to log',
        'fireAt': Timestamp.fromDate(fireActual),
        'createdAt': FieldValue.serverTimestamp(),
        'fired': false,
        'source': 'pet_medications',
      });
    } catch (_) {}
  }

  static Future<void> clearForMed({
    required String uid,
    required String medId,
  }) async {
    try {
      final snap = await FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('scheduled_reminders')
          .where('medicationId', isEqualTo: medId)
          .where('fired', isEqualTo: false)
          .get();
      final batch = FirebaseFirestore.instance.batch();
      for (final d in snap.docs) {
        batch.delete(d.reference);
      }
      await batch.commit();
    } catch (_) {}
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// SCHEDULE ENGINE
// Ported verbatim from human widget — species-agnostic. All logic works the
// same way for pets: clock times, meal times, every N hours, specific days,
// taper schedules, PRN.
// ═══════════════════════════════════════════════════════════════════════════

class _ScheduleEngine {
  static List<DateTime> expectedDoses(
    PetMedication med,
    DateTime day,
    UserPrefs prefs,
  ) {
    if (med.isAsNeeded || med.preset == SchedulePreset.prn) return const [];
    final dayStart = DateTime(day.year, day.month, day.day);
    if (med.startDate.isAfter(dayStart.add(const Duration(days: 1)))) {
      return const [];
    }
    if (med.stopDate != null && dayStart.isAfter(med.stopDate!)) {
      return const [];
    }

    switch (med.preset) {
      case SchedulePreset.clockTimes:
        return _fromTimes(dayStart, med.times, med.daysOfWeek);
      case SchedulePreset.meals:
        final List<String> times = [];
        for (final tag in med.times) {
          switch (tag) {
            case 'breakfast':
              times.add(prefs.breakfastTime);
              break;
            case 'dinner':
              times.add(prefs.dinnerTime);
              break;
            case 'bedtime':
              times.add(prefs.bedtimeTime);
              break;
            default:
              break;
          }
        }
        return _fromTimes(dayStart, times, med.daysOfWeek);
      case SchedulePreset.interval:
        return _intervalDoses(
          dayStart,
          med.intervalHours,
          med.firstDoseTime ?? '08:00',
        );
      case SchedulePreset.weekly:
        return _fromTimes(dayStart, med.times, med.daysOfWeek);
      case SchedulePreset.taper:
        return _taperDoses(med, dayStart);
      case SchedulePreset.prn:
        return const [];
    }
  }

  static List<DateTime> _fromTimes(
    DateTime dayStart,
    List<String> times,
    List<int> daysOfWeek,
  ) {
    if (daysOfWeek.isNotEmpty && !daysOfWeek.contains(dayStart.weekday)) {
      return const [];
    }
    final out = <DateTime>[];
    for (final t in times) {
      final parts = t.split(':');
      if (parts.length != 2) continue;
      final h = int.tryParse(parts[0]) ?? 0;
      final m = int.tryParse(parts[1]) ?? 0;
      out.add(DateTime(dayStart.year, dayStart.month, dayStart.day, h, m));
    }
    out.sort();
    return out;
  }

  static List<DateTime> _intervalDoses(
    DateTime dayStart,
    int intervalHours,
    String firstDoseTime,
  ) {
    if (intervalHours <= 0 || intervalHours > 24) return const [];
    final parts = firstDoseTime.split(':');
    final h = int.tryParse(parts.isNotEmpty ? parts[0] : '8') ?? 8;
    final m = int.tryParse(parts.length > 1 ? parts[1] : '0') ?? 0;
    final out = <DateTime>[];
    var t = DateTime(dayStart.year, dayStart.month, dayStart.day, h, m);
    final dayEnd = DateTime(dayStart.year, dayStart.month, dayStart.day + 1);
    while (t.isBefore(dayEnd)) {
      out.add(t);
      t = t.add(Duration(hours: intervalHours));
    }
    return out;
  }

  static List<DateTime> _taperDoses(PetMedication med, DateTime dayStart) {
    if (med.taperSteps.isEmpty) return const [];
    final startDay = DateTime(
      med.startDate.year,
      med.startDate.month,
      med.startDate.day,
    );
    final daysSince = dayStart.difference(startDay).inDays;
    if (daysSince < 0) return const [];
    final sorted = [...med.taperSteps]
      ..sort((a, b) => a.startDay.compareTo(b.startDay));
    TaperStep? active;
    for (final step in sorted) {
      if (daysSince >= step.startDay) {
        active = step;
      }
    }
    if (active == null) return const [];
    if (active.times.isEmpty) return const [];
    return _fromTimes(dayStart, active.times, const []);
  }

  static int? currentTaperStep(PetMedication med) {
    if (!med.isTaper || med.taperSteps.isEmpty) return null;
    final now = DateTime.now();
    final startDay = DateTime(
      med.startDate.year,
      med.startDate.month,
      med.startDate.day,
    );
    final daysSince =
        DateTime(now.year, now.month, now.day).difference(startDay).inDays;
    if (daysSince < 0) return null;
    final sorted = [...med.taperSteps]
      ..sort((a, b) => a.startDay.compareTo(b.startDay));
    int idx = 0;
    bool found = false;
    for (int i = 0; i < sorted.length; i++) {
      if (daysSince >= sorted[i].startDay) {
        idx = i;
        found = true;
      }
    }
    if (!found) return null;
    return idx + 1;
  }

  static String summarize(PetMedication med, UserPrefs prefs) {
    if (med.isAsNeeded || med.preset == SchedulePreset.prn) {
      return 'As needed • max ${med.prnMaxPerDay}/day';
    }
    switch (med.preset) {
      case SchedulePreset.clockTimes:
        if (med.times.isEmpty) return 'No times set';
        final dow =
            med.daysOfWeek.isEmpty ? 'Daily' : _weekdayLabel(med.daysOfWeek);
        return '$dow at ${med.times.map(_fmtTime).join(", ")}';
      case SchedulePreset.meals:
        if (med.times.isEmpty) return 'No meals selected';
        return 'With ${med.times.join(", ")}';
      case SchedulePreset.interval:
        return 'Every ${med.intervalHours}h, starting ${_fmtTime(med.firstDoseTime ?? "08:00")}';
      case SchedulePreset.weekly:
        if (med.times.isEmpty || med.daysOfWeek.isEmpty) {
          return 'Weekly (incomplete)';
        }
        return '${_weekdayLabel(med.daysOfWeek)} at ${med.times.map(_fmtTime).join(", ")}';
      case SchedulePreset.taper:
        final step = currentTaperStep(med);
        return 'Taper ${step ?? 0}/${med.taperSteps.length}';
      case SchedulePreset.prn:
        return 'As needed';
    }
  }

  static String _fmtTime(String hhmm) {
    final parts = hhmm.split(':');
    if (parts.length != 2) return hhmm;
    final h = int.tryParse(parts[0]) ?? 0;
    final m = int.tryParse(parts[1]) ?? 0;
    final hour12 = h == 0 ? 12 : (h > 12 ? h - 12 : h);
    final ampm = h >= 12 ? 'PM' : 'AM';
    return '${hour12}:${m.toString().padLeft(2, "0")} $ampm';
  }

  static String _weekdayLabel(List<int> days) {
    if (days.length == 7) return 'Daily';
    if (_setEquals(days, const [1, 2, 3, 4, 5])) return 'Weekdays';
    if (_setEquals(days, const [6, 7])) return 'Weekends';
    const names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    final sorted = [...days]..sort();
    return sorted.map((d) => names[d - 1]).join(', ');
  }

  static bool _setEquals(List<int> a, List<int> b) {
    if (a.length != b.length) return false;
    final sa = {...a};
    return sa.containsAll(b);
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// IMAGE HELPER
// Same resize-to-400 pattern as human widget. Upload path is per-pet:
// users/{uid}/pets/{petId}/meds/{medId}.png
// ═══════════════════════════════════════════════════════════════════════════

class _ImageHelper {
  static Future<Uint8List?> resizeTo400(Uint8List bytes) async {
    try {
      final codec = await ui.instantiateImageCodec(
        bytes,
        targetWidth: 400,
        targetHeight: 400,
      );
      final frame = await codec.getNextFrame();
      final byteData =
          await frame.image.toByteData(format: ui.ImageByteFormat.png);
      return byteData?.buffer.asUint8List();
    } catch (_) {
      return bytes;
    }
  }

  static Future<String?> uploadMedPhoto(
    String uid,
    String petId,
    String medId,
    Uint8List bytes,
  ) async {
    try {
      final ref = FirebaseStorage.instance
          .ref()
          .child('users/$uid/pets/$petId/meds/$medId.png');
      await ref.putData(
        bytes,
        SettableMetadata(contentType: 'image/png'),
      );
      return await ref.getDownloadURL();
    } catch (_) {
      return null;
    }
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// MAIN WIDGET
// ═══════════════════════════════════════════════════════════════════════════

// END OF _PetMedicationsState class

// ═══════════════════════════════════════════════════════════════════════════
// ADD / EDIT PET MEDICATION SHEET
// Full-featured add/edit form with:
//   • Species-filtered drug autocomplete (cats never see Tylenol, Rimadyl, etc)
//   • Auto-seed from vet drug catalog (instructions, condition, meal timing)
//   • Weight-based dosage hints when pet.weightLbs is on file
//   • Species-safety red banner for dangerous drugs typed manually
//   • MDR1 breed warning banner for ivermectin in Collie/Sheltie/Aussie
//   • All 6 schedule types with full editors
//   • Pharmacy field with 4 suggestion chips
//   • Photo upload to users/{uid}/pets/{petId}/meds/{medId}.png
// ═══════════════════════════════════════════════════════════════════════════

class _AddEditPetMedSheet extends StatefulWidget {
  final PetMedication? existing;
  final _PetLite pet;
  final UserPrefs prefs;
  final List<PetMedication> allMeds;
  final String uid;
  final String petId;
  final Future<bool> Function(PetMedication) onSave;

  const _AddEditPetMedSheet({
    required this.existing,
    required this.pet,
    required this.prefs,
    required this.allMeds,
    required this.uid,
    required this.petId,
    required this.onSave,
  });

  @override
  State<_AddEditPetMedSheet> createState() => _AddEditPetMedSheetState();
}

class _AddEditPetMedSheetState extends State<_AddEditPetMedSheet> {
  // ─── Controllers ────────────────────────────────────────────────────────
  late TextEditingController _nameCtrl;
  late TextEditingController _strengthCtrl;
  late TextEditingController _dosageCtrl;
  late TextEditingController _conditionCtrl;
  late TextEditingController _prescribedByCtrl;
  late TextEditingController _pharmacyCtrl;
  late TextEditingController _notesCtrl;
  late TextEditingController _pillCountCtrl;
  late TextEditingController _refillThresholdCtrl;

  // ─── Form state ─────────────────────────────────────────────────────────
  MedType _type = MedType.pill;
  SchedulePreset _preset = SchedulePreset.clockTimes;
  List<String> _times = ['08:00'];
  List<int> _daysOfWeek = [];
  List<String> _mealTimes = [];
  int _intervalHours = 8;
  String _firstDoseTime = '08:00';
  MealTiming _mealTiming = MealTiming.none;
  List<String> _instructions = [];
  int _prnMaxPerDay = 4;
  double _prnMinHoursBetween = 4.0;
  bool _remindersEnabled = true;
  List<TaperStep> _taperSteps = [];
  DateTime _startDate = DateTime.now();
  DateTime? _stopDate;
  String? _imageUrl;
  String _drugKey = 'custom';

  // ─── UI state ───────────────────────────────────────────────────────────
  List<String> _suggestions = [];
  bool _saving = false;
  String? _savedMedId; // generated once so photo uploads work for new meds

  @override
  void initState() {
    super.initState();
    final e = widget.existing;
    _nameCtrl = TextEditingController(text: e?.name ?? '');
    _strengthCtrl = TextEditingController(text: e?.strength ?? '');
    _dosageCtrl = TextEditingController(text: e?.dosage ?? '');
    _conditionCtrl = TextEditingController(text: e?.condition ?? '');
    _prescribedByCtrl = TextEditingController(text: e?.prescribedBy ?? '');
    _pharmacyCtrl = TextEditingController(text: e?.pharmacy ?? '');
    _notesCtrl = TextEditingController(text: e?.notes ?? '');
    _pillCountCtrl =
        TextEditingController(text: e == null ? '30' : e.pillCount.toString());
    _refillThresholdCtrl = TextEditingController(
      text: e == null ? '10' : e.refillThreshold.toString(),
    );
    if (e != null) {
      _type = e.type;
      _preset = e.preset;
      _daysOfWeek = [...e.daysOfWeek];
      _intervalHours = e.intervalHours;
      _firstDoseTime = e.firstDoseTime ?? '08:00';
      _mealTiming = e.mealTiming;
      _instructions = [...e.instructions];
      _prnMaxPerDay = e.prnMaxPerDay;
      _prnMinHoursBetween = e.prnMinHoursBetween;
      _remindersEnabled = e.remindersEnabled;
      _taperSteps = [...e.taperSteps];
      _startDate = e.startDate;
      _stopDate = e.stopDate;
      _imageUrl = e.imageUrl;
      _drugKey = e.drugKey;
      if (e.preset == SchedulePreset.meals) {
        _mealTimes = [...e.times];
      } else {
        _times = e.times.isEmpty ? ['08:00'] : [...e.times];
      }
      _savedMedId = e.id;
    } else {
      // Generate doc ID up-front so photo uploads have a valid path
      _savedMedId = FirebaseFirestore.instance
          .collection('users')
          .doc(widget.uid)
          .collection('pets')
          .doc(widget.petId)
          .collection('medications')
          .doc()
          .id;
    }
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _strengthCtrl.dispose();
    _dosageCtrl.dispose();
    _conditionCtrl.dispose();
    _prescribedByCtrl.dispose();
    _pharmacyCtrl.dispose();
    _notesCtrl.dispose();
    _pillCountCtrl.dispose();
    _refillThresholdCtrl.dispose();
    super.dispose();
  }

  // ─── Drug catalog integration ───────────────────────────────────────────
  void _onNameChanged(String v) {
    setState(() {
      _suggestions = _VetDrugDB.suggestNames(v, widget.pet.type);
      // Auto-seed fields from catalog only if they're empty
      final info = _VetDrugDB.lookup(v, widget.pet.type);
      if (info != null) {
        _drugKey = info.canonical;
        if (_instructions.isEmpty && info.defaultInstruction.isNotEmpty) {
          _instructions = [info.defaultInstruction];
        }
        if (_mealTiming == MealTiming.none &&
            info.defaultTiming != MealTiming.none) {
          _mealTiming = info.defaultTiming;
        }
        if (_conditionCtrl.text.isEmpty && info.commonCondition != null) {
          _conditionCtrl.text = info.commonCondition!;
        }
        // If it's an injection, default form to injection
        if (info.isInjection && _type != MedType.injection) {
          _type = MedType.injection;
        }
        // If it's typically PRN, default preset to PRN
        if (info.isPRN && _preset == SchedulePreset.clockTimes) {
          _preset = SchedulePreset.prn;
        }
      } else {
        _drugKey = 'custom';
      }
    });
  }

  /// If the pet has weight on file and the drug has a dosage hint, produce
  /// a localized hint line like:
  /// "Typical: 2 mg/kg PO twice daily → Buddy (65 lbs / 29.5 kg)"
  String? _weightDosingHint() {
    final info = _VetDrugDB.lookup(_nameCtrl.text, widget.pet.type);
    if (info == null || info.dosageHint == null) return null;
    final pet = widget.pet;
    final lbs = pet.weightLbs;
    final kg = pet.weightKg;
    if (lbs == null || kg == null) {
      return 'Typical: ${info.dosageHint}';
    }
    return 'Typical: ${info.dosageHint}\n'
        '→ ${pet.name} (${lbs.toStringAsFixed(1)} lbs / ${kg.toStringAsFixed(1)} kg)';
  }

  /// Species-safety warning (Tylenol for cat, etc.)
  String? _currentSafetyWarning() {
    return _VetDrugDB.speciesSafetyWarning(
      _nameCtrl.text,
      widget.pet.type,
    );
  }

  /// MDR1 breed warning — fires if drug has breedWarning and pet's breed
  /// string matches known sensitive breeds.
  String? _currentBreedWarning() {
    final info = _VetDrugDB.lookup(_nameCtrl.text, widget.pet.type);
    if (info == null || info.breedWarning == null) return null;
    final breed = widget.pet.breed?.toLowerCase() ?? '';
    if (breed.isEmpty) return info.breedWarning;
    // Show the warning if breed matches, or if breed is unknown (safer default)
    const mdr1Breeds = [
      'collie',
      'sheltie',
      'shetland sheepdog',
      'australian shepherd',
      'aussie',
      'border collie',
      'old english sheepdog',
      'long-haired whippet',
      'silken windhound',
      'mcnab',
      'english shepherd',
    ];
    final isSensitiveBreed = mdr1Breeds.any((b) => breed.contains(b));
    if (isSensitiveBreed) {
      return '${widget.pet.name} is a ${widget.pet.breed} — ${info.breedWarning}';
    }
    // Still show a gentler hint for other breeds
    return info.breedWarning;
  }

  /// Detect if the currently-typed drug has a long-interval default
  /// (Cytopoint, Convenia, Bravecto, NexGard, Heartgard). If so, we
  /// surface a hint showing that default interval in the schedule section.
  int? _catalogIntervalDaysHint() {
    final info = _VetDrugDB.lookup(_nameCtrl.text, widget.pet.type);
    return info?.defaultIntervalDays;
  }

  // ─── Time / date pickers ────────────────────────────────────────────────
  Future<void> _pickTime(int index) async {
    final parts = _times[index].split(':');
    final initial = TimeOfDay(
      hour: int.tryParse(parts.isNotEmpty ? parts[0] : '8') ?? 8,
      minute: int.tryParse(parts.length > 1 ? parts[1] : '0') ?? 0,
    );
    final picked = await showTimePicker(
      context: context,
      initialTime: initial,
      builder: (ctx, child) => Theme(
        data: ThemeData.dark().copyWith(
          colorScheme: const ColorScheme.dark(
            primary: _Jovi.petAccent,
            onPrimary: Colors.white,
            surface: _Jovi.navy,
            onSurface: Colors.white,
          ),
        ),
        child: child!,
      ),
    );
    if (picked != null) {
      setState(() {
        _times[index] =
            '${picked.hour.toString().padLeft(2, "0")}:${picked.minute.toString().padLeft(2, "0")}';
      });
    }
  }

  Future<void> _pickFirstDose() async {
    final parts = _firstDoseTime.split(':');
    final initial = TimeOfDay(
      hour: int.tryParse(parts.isNotEmpty ? parts[0] : '8') ?? 8,
      minute: int.tryParse(parts.length > 1 ? parts[1] : '0') ?? 0,
    );
    final picked = await showTimePicker(
      context: context,
      initialTime: initial,
      builder: (ctx, child) => Theme(
        data: ThemeData.dark().copyWith(
          colorScheme: const ColorScheme.dark(
            primary: _Jovi.petAccent,
            onPrimary: Colors.white,
            surface: _Jovi.navy,
          ),
        ),
        child: child!,
      ),
    );
    if (picked != null) {
      setState(() {
        _firstDoseTime =
            '${picked.hour.toString().padLeft(2, "0")}:${picked.minute.toString().padLeft(2, "0")}';
      });
    }
  }

  Future<void> _pickDate(bool isStart) async {
    final initial = isStart ? _startDate : (_stopDate ?? DateTime.now());
    final picked = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: isStart ? DateTime(2020) : _startDate,
      lastDate: DateTime.now().add(const Duration(days: 365 * 3)),
      builder: (ctx, child) => Theme(
        data: ThemeData.dark().copyWith(
          colorScheme: const ColorScheme.dark(
            primary: _Jovi.petAccent,
            onPrimary: Colors.white,
            surface: _Jovi.navy,
          ),
        ),
        child: child!,
      ),
    );
    if (picked != null) {
      setState(() {
        if (isStart) {
          _startDate = picked;
          if (_stopDate != null && _stopDate!.isBefore(_startDate)) {
            _stopDate = null;
          }
        } else {
          if (picked.isBefore(_startDate)) {
            _showSnack('Stop date must be after start date', isError: true);
            return;
          }
          _stopDate = picked;
        }
      });
    }
  }

  // ─── Photo upload ───────────────────────────────────────────────────────
  Future<void> _pickImage() async {
    try {
      final source = await showCupertinoModalPopup<ImageSource>(
        context: context,
        builder: (ctx) => CupertinoActionSheet(
          title: const Text('Add a Photo'),
          actions: [
            CupertinoActionSheetAction(
              onPressed: () => Navigator.of(ctx).pop(ImageSource.camera),
              child: const Text('Take Photo'),
            ),
            CupertinoActionSheetAction(
              onPressed: () => Navigator.of(ctx).pop(ImageSource.gallery),
              child: const Text('Choose from Library'),
            ),
          ],
          cancelButton: CupertinoActionSheetAction(
            isDefaultAction: true,
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Cancel'),
          ),
        ),
      );
      if (source == null || !mounted) return;
      final picker = ImagePicker();
      final x = await picker.pickImage(
        source: source,
        maxWidth: 800,
        maxHeight: 800,
      );
      if (x == null) return;
      final raw = await x.readAsBytes();
      final resized = await _ImageHelper.resizeTo400(raw);
      if (resized == null) return;
      final medId = _savedMedId;
      if (medId == null) return;
      final url = await _ImageHelper.uploadMedPhoto(
        widget.uid,
        widget.petId,
        medId,
        resized,
      );
      if (url != null) {
        setState(() => _imageUrl = url);
        _showSnack('Photo uploaded');
      } else {
        _showSnack('Upload failed — check permissions', isError: true);
      }
    } catch (_) {
      _showSnack('Could not upload photo', isError: true);
    }
  }

  // ─── Add instruction dialog ─────────────────────────────────────────────
  Future<void> _addInstruction() async {
    final ctrl = TextEditingController();
    await showDialog(
      context: context,
      barrierColor: Colors.black.withOpacity(0.5),
      builder: (ctx) => Dialog(
        backgroundColor: Colors.transparent,
        child: Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [
                _Jovi.navy.withOpacity(0.97),
                _Jovi.navyDark.withOpacity(0.97),
              ],
            ),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: Colors.white.withOpacity(0.14),
              width: 0.8,
            ),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Add instruction',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 12),
              Container(
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.06),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: Colors.white.withOpacity(0.12),
                  ),
                ),
                child: TextField(
                  controller: ctrl,
                  autofocus: true,
                  cursorColor: _Jovi.petAccent,
                  style: const TextStyle(color: Colors.white),
                  decoration: const InputDecoration(
                    hintText: 'e.g. Give with food',
                    hintStyle: TextStyle(color: Colors.white38),
                    border: InputBorder.none,
                    contentPadding: EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 10,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 14),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  onPressed: () {
                    if (ctrl.text.trim().isNotEmpty) {
                      setState(() => _instructions.add(ctrl.text.trim()));
                    }
                    Navigator.pop(ctx);
                  },
                  child: const Text(
                    'Add',
                    style: TextStyle(
                      color: _Jovi.petAccent,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
    ctrl.dispose();
  }

  // ─── Snack helper (private copy so we don't depend on parent state) ─────
  void _showSnack(String msg, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(msg,
        accent: isError ? _Jovi.softRed : _Jovi.mint,
        icon: isError
            ? CupertinoIcons.exclamationmark_circle
            : CupertinoIcons.checkmark_circle,
        duration: Duration(seconds: isError ? 4 : 3)));
  }

  String _fmtTime(String hhmm) {
    final parts = hhmm.split(':');
    if (parts.length != 2) return hhmm;
    final h = int.tryParse(parts[0]) ?? 0;
    final m = int.tryParse(parts[1]) ?? 0;
    final h12 = h == 0 ? 12 : (h > 12 ? h - 12 : h);
    final ampm = h >= 12 ? 'PM' : 'AM';
    return '$h12:${m.toString().padLeft(2, "0")} $ampm';
  }

  // ─── Shared UI builders (field label, text field, chip) ─────────────────
  Widget _fieldLabel(String s) => Padding(
        padding: const EdgeInsets.only(left: 4, bottom: 6, top: 14),
        child: Text(
          s,
          style: TextStyle(
            color: Colors.white.withOpacity(0.65),
            fontSize: 12,
            fontWeight: FontWeight.w600,
            letterSpacing: -0.1,
          ),
        ),
      );

  Widget _textField(
    TextEditingController ctrl,
    String hint, {
    TextInputType? keyboard,
    ValueChanged<String>? onChanged,
    int maxLines = 1,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.06),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withOpacity(0.12), width: 0.8),
      ),
      child: TextField(
        controller: ctrl,
        keyboardType: keyboard,
        maxLines: maxLines,
        onChanged: onChanged,
        textCapitalization: keyboard == TextInputType.number
            ? TextCapitalization.none
            : TextCapitalization.sentences,
        cursorColor: _Jovi.petAccent,
        style: const TextStyle(color: Colors.white, fontSize: 14),
        decoration: InputDecoration(
          hintText: hint,
          hintStyle: TextStyle(
            color: Colors.white.withOpacity(0.35),
            fontSize: 13,
          ),
          border: InputBorder.none,
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
        ),
      ),
    );
  }

  Widget _choiceChip({
    required String label,
    required bool selected,
    required VoidCallback onTap,
    IconData? icon,
    Color? tint,
  }) {
    final c = tint ?? _Jovi.petAccent;
    return _Pressable(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: selected ? c.withOpacity(0.2) : Colors.white.withOpacity(0.05),
          borderRadius: BorderRadius.circular(99),
          border: Border.all(
            color:
                selected ? c.withOpacity(0.6) : Colors.white.withOpacity(0.14),
            width: selected ? 1 : 0.7,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (icon != null) ...[
              Icon(icon, size: 13, color: selected ? c : Colors.white70),
              const SizedBox(width: 5),
            ],
            Text(
              label,
              style: TextStyle(
                color: selected ? c : Colors.white.withOpacity(0.75),
                fontSize: 12,
                fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // MAIN BUILD
  // ═══════════════════════════════════════════════════════════════════════

  @override
  Widget build(BuildContext context) {
    final safety = _currentSafetyWarning();
    final breedWarn = _currentBreedWarning();
    final weightHint = _weightDosingHint();
    final catalogInterval = _catalogIntervalDaysHint();

    return SingleChildScrollView(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(18, 0, 18, 24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Drag handle
            Center(
              child: Container(
                margin: const EdgeInsets.only(top: 8, bottom: 12),
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.25),
                  borderRadius: BorderRadius.circular(4),
                ),
              ),
            ),
            // Header
            Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    gradient: _Jovi.petGradient,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(
                    Icons.medication_rounded,
                    color: Colors.white,
                    size: 22,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        widget.existing == null
                            ? 'Add Medication'
                            : 'Edit Medication',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      Row(
                        children: [
                          Icon(
                            _petTypeIcon(widget.pet.type),
                            size: 11,
                            color: _Jovi.petAccent,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            'For ${widget.pet.name}'
                            '${widget.pet.breed != null && widget.pet.breed!.isNotEmpty ? " (${widget.pet.breed})" : ""}',
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.6),
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                IconButton(
                  onPressed: () => Navigator.pop(context),
                  icon: Icon(
                    Icons.close_rounded,
                    color: Colors.white.withOpacity(0.7),
                  ),
                ),
              ],
            ),

            // Name + autocomplete
            _fieldLabel('Medication name'),
            _textField(
              _nameCtrl,
              widget.pet.type == PetType.dog
                  ? 'e.g. Rimadyl, Apoquel, Clavamox'
                  : (widget.pet.type == PetType.cat
                      ? 'e.g. Gabapentin, Cerenia, Clavamox'
                      : 'Medication name'),
              onChanged: _onNameChanged,
            ),
            if (_suggestions.isNotEmpty) ...[
              const SizedBox(height: 6),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  for (final s in _suggestions)
                    _Pressable(
                      onTap: () {
                        setState(() {
                          _nameCtrl.text = s;
                          _nameCtrl.selection = TextSelection.fromPosition(
                            TextPosition(offset: s.length),
                          );
                          _suggestions = [];
                        });
                        _onNameChanged(s);
                      },
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 5),
                        decoration: BoxDecoration(
                          color: _Jovi.mint.withOpacity(0.14),
                          borderRadius: BorderRadius.circular(99),
                          border: Border.all(
                            color: _Jovi.mint.withOpacity(0.4),
                            width: 0.6,
                          ),
                        ),
                        child: Text(
                          s,
                          style: const TextStyle(
                            color: _Jovi.mint,
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ],

            // Species safety warning banner (RED — critical)
            if (safety != null) ...[
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: _Jovi.errorRed.withOpacity(0.14),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: _Jovi.errorRed.withOpacity(0.5),
                    width: 1.2,
                  ),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(
                      Icons.warning_amber_rounded,
                      color: _Jovi.errorRed,
                      size: 18,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Species Safety Warning',
                            style: TextStyle(
                              color: _Jovi.errorRed,
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                              letterSpacing: -0.1,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            safety,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 12,
                              height: 1.4,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],

            // MDR1 breed warning banner (YELLOW)
            if (breedWarn != null) ...[
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: _Jovi.gold.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: _Jovi.gold.withOpacity(0.4),
                    width: 1,
                  ),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(
                      Icons.info_outline_rounded,
                      color: _Jovi.gold,
                      size: 18,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Breed-Sensitive Drug',
                            style: TextStyle(
                              color: _Jovi.gold,
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                              letterSpacing: -0.1,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            breedWarn,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 12,
                              height: 1.4,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],

            // Strength + dosage
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _fieldLabel('Strength'),
                      _textField(_strengthCtrl, '100 mg'),
                    ],
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _fieldLabel('Dose'),
                      _textField(_dosageCtrl, '1 tablet'),
                    ],
                  ),
                ),
              ],
            ),

            // Weight-based dosing hint
            if (weightHint != null) ...[
              const SizedBox(height: 8),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                decoration: BoxDecoration(
                  color: _Jovi.mint.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: _Jovi.mint.withOpacity(0.3),
                    width: 0.7,
                  ),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(
                      Icons.scale_rounded,
                      color: _Jovi.mint,
                      size: 14,
                    ),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            weightHint,
                            style: TextStyle(
                              color: _Jovi.mint.withOpacity(0.95),
                              fontSize: 11,
                              height: 1.4,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            'Confirm exact dose with your vet — range is for reference only.',
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.5),
                              fontSize: 10,
                              fontStyle: FontStyle.italic,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],

            // Form / type
            _fieldLabel('Form'),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                for (final t in MedType.values)
                  _choiceChip(
                    label: t.label,
                    icon: t.icon,
                    selected: _type == t,
                    onTap: () => setState(() => _type = t),
                  ),
              ],
            ),

            // Condition + vet + pharmacy
            _fieldLabel('Condition being treated'),
            _textField(_conditionCtrl, 'e.g. Arthritis, allergies, infection'),
            _fieldLabel('Vet / prescribed by'),
            _textField(_prescribedByCtrl, 'Dr. name (optional)'),

            _fieldLabel('Pharmacy'),
            _textField(_pharmacyCtrl, 'Where to refill'),
            const SizedBox(height: 6),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                for (final p in const [
                  'Vet dispensary',
                  'Chewy Pharmacy',
                  '1-800-PetMeds',
                  'Compounding pharmacy',
                ])
                  _Pressable(
                    onTap: () => setState(() => _pharmacyCtrl.text = p),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 5),
                      decoration: BoxDecoration(
                        color: _Jovi.petAccent.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(99),
                        border: Border.all(
                          color: _Jovi.petAccent.withOpacity(0.3),
                          width: 0.6,
                        ),
                      ),
                      child: Text(
                        p,
                        style: const TextStyle(
                          color: _Jovi.petAccent,
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ),
              ],
            ),

            // Schedule preset picker
            _fieldLabel('Schedule type'),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                for (final p in SchedulePreset.values)
                  _choiceChip(
                    label: p.label,
                    selected: _preset == p,
                    onTap: () => setState(() => _preset = p),
                  ),
              ],
            ),

            // Long-interval hint (for Cytopoint, Bravecto, etc.)
            if (catalogInterval != null && catalogInterval > 7) ...[
              const SizedBox(height: 10),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                decoration: BoxDecoration(
                  color: _Jovi.sky.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: _Jovi.sky.withOpacity(0.3),
                    width: 0.7,
                  ),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(
                      Icons.event_repeat_rounded,
                      color: _Jovi.sky,
                      size: 14,
                    ),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        'This is a long-interval medication — typical dose every $catalogInterval days. '
                        'Consider using PRN mode and setting a calendar reminder, or set a weekly schedule.',
                        style: TextStyle(
                          color: _Jovi.sky.withOpacity(0.95),
                          fontSize: 11,
                          height: 1.4,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],

            // Schedule editors (per preset)
            _buildScheduleEditor(),

            // Meal timing
            _fieldLabel('Meal timing'),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                for (final t in MealTiming.values)
                  _choiceChip(
                    label: t.label,
                    selected: _mealTiming == t,
                    onTap: () => setState(() => _mealTiming = t),
                  ),
              ],
            ),

            // Instructions
            _fieldLabel('Special instructions'),
            if (_instructions.isNotEmpty)
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  for (int i = 0; i < _instructions.length; i++)
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(
                        color: _Jovi.mint.withOpacity(0.14),
                        borderRadius: BorderRadius.circular(99),
                        border: Border.all(
                          color: _Jovi.mint.withOpacity(0.35),
                          width: 0.6,
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Flexible(
                            child: Text(
                              _instructions[i],
                              style: const TextStyle(
                                color: _Jovi.mint,
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                          const SizedBox(width: 6),
                          _Pressable(
                            onTap: () =>
                                setState(() => _instructions.removeAt(i)),
                            child: Icon(
                              Icons.close_rounded,
                              size: 13,
                              color: _Jovi.mint.withOpacity(0.8),
                            ),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            const SizedBox(height: 8),
            _Pressable(
              onTap: _addInstruction,
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: _Jovi.mint.withOpacity(0.08),
                  borderRadius: BorderRadius.circular(99),
                  border: Border.all(
                    color: _Jovi.mint.withOpacity(0.25),
                    width: 0.7,
                  ),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.add_rounded, color: _Jovi.mint, size: 14),
                    SizedBox(width: 5),
                    Text(
                      'Add instruction',
                      style: TextStyle(
                        color: _Jovi.mint,
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
            ),

            // Pill count + refill threshold
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _fieldLabel('On-hand count'),
                      _textField(
                        _pillCountCtrl,
                        '30',
                        keyboard: TextInputType.number,
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _fieldLabel('Refill alert at'),
                      _textField(
                        _refillThresholdCtrl,
                        '10',
                        keyboard: TextInputType.number,
                      ),
                    ],
                  ),
                ),
              ],
            ),

            // Start / stop dates
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _fieldLabel('Start date'),
                      _Pressable(
                        onTap: () => _pickDate(true),
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 12, vertical: 12),
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.06),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: Colors.white.withOpacity(0.12),
                              width: 0.8,
                            ),
                          ),
                          child: Row(
                            children: [
                              const Icon(Icons.event_rounded,
                                  color: _Jovi.petAccent, size: 15),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  '${_startDate.month}/${_startDate.day}/${_startDate.year}',
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
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _fieldLabel('Stop date (optional)'),
                      _Pressable(
                        onTap: () => _pickDate(false),
                        onLongPress: () => setState(() => _stopDate = null),
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 12, vertical: 12),
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.06),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: Colors.white.withOpacity(0.12),
                              width: 0.8,
                            ),
                          ),
                          child: Row(
                            children: [
                              Icon(
                                Icons.event_busy_rounded,
                                color: Colors.white.withOpacity(0.6),
                                size: 15,
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  _stopDate == null
                                      ? 'None (hold to clear)'
                                      : '${_stopDate!.month}/${_stopDate!.day}/${_stopDate!.year}',
                                  style: TextStyle(
                                    color: _stopDate == null
                                        ? Colors.white.withOpacity(0.5)
                                        : Colors.white,
                                    fontSize: 13,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),

            // Notes
            _fieldLabel('Notes'),
            _textField(_notesCtrl, 'Anything else to remember', maxLines: 3),

            // Reminders toggle
            const SizedBox(height: 18),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.06),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(
                  color: Colors.white.withOpacity(0.12),
                  width: 0.8,
                ),
              ),
              child: Row(
                children: [
                  Icon(
                    _remindersEnabled
                        ? Icons.notifications_active_rounded
                        : Icons.notifications_off_rounded,
                    color: _remindersEnabled
                        ? _Jovi.petAccent
                        : Colors.white.withOpacity(0.5),
                    size: 18,
                  ),
                  const SizedBox(width: 10),
                  const Expanded(
                    child: Text(
                      'Enable reminders',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  Switch.adaptive(
                    value: _remindersEnabled,
                    onChanged: (v) => setState(() => _remindersEnabled = v),
                    activeColor: _Jovi.petAccent,
                    activeTrackColor: _Jovi.petAccent.withOpacity(0.4),
                  ),
                ],
              ),
            ),

            // Photo
            const SizedBox(height: 10),
            _Pressable(
              onTap: _pickImage,
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.06),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: Colors.white.withOpacity(0.12),
                    width: 0.8,
                  ),
                ),
                child: Row(
                  children: [
                    Icon(
                      _imageUrl != null
                          ? Icons.photo_rounded
                          : Icons.add_a_photo_outlined,
                      color: _imageUrl != null
                          ? _Jovi.mint
                          : Colors.white.withOpacity(0.7),
                      size: 18,
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        _imageUrl != null ? 'Photo attached' : 'Add photo',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                    if (_imageUrl != null)
                      _Pressable(
                        onTap: () => setState(() => _imageUrl = null),
                        child: Icon(
                          Icons.close_rounded,
                          color: Colors.white.withOpacity(0.5),
                          size: 18,
                        ),
                      ),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 24),

            // Save button
            SizedBox(
              width: double.infinity,
              child: _Pressable(
                onTap: _saving ? null : _handleSave,
                child: Container(
                  padding: const EdgeInsets.symmetric(vertical: 15),
                  decoration: BoxDecoration(
                    gradient: _Jovi.petGradient,
                    borderRadius: BorderRadius.circular(99),
                    boxShadow: [
                      BoxShadow(
                        color: _Jovi.petAccent.withOpacity(0.35),
                        blurRadius: 16,
                        offset: const Offset(0, 6),
                      ),
                    ],
                  ),
                  child: Center(
                    child: _saving
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              valueColor:
                                  AlwaysStoppedAnimation<Color>(Colors.white),
                            ),
                          )
                        : Text(
                            widget.existing == null
                                ? 'Add Medication'
                                : 'Save Changes',
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 15,
                              fontWeight: FontWeight.w600,
                              letterSpacing: -0.2,
                            ),
                          ),
                  ),
                ),
              ),
            ),

            // Legal reminder
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.04),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(
                  color: Colors.white.withOpacity(0.1),
                  width: 0.6,
                ),
              ),
              child: Row(
                children: [
                  Icon(
                    Icons.info_outline_rounded,
                    size: 13,
                    color: Colors.white.withOpacity(0.5),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Tracking only — not veterinary advice. Follow your vet\'s exact directions. '
                      'Dosage ranges are typical for the species and not a prescription.',
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.55),
                        fontSize: 10.5,
                        height: 1.4,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // SCHEDULE EDITOR (per-preset UI)
  // ═══════════════════════════════════════════════════════════════════════

  Widget _buildScheduleEditor() {
    switch (_preset) {
      case SchedulePreset.clockTimes:
        return _buildClockTimesEditor();
      case SchedulePreset.meals:
        return _buildMealsEditor();
      case SchedulePreset.interval:
        return _buildIntervalEditor();
      case SchedulePreset.weekly:
        return _buildWeeklyEditor();
      case SchedulePreset.taper:
        return _buildTaperEditor();
      case SchedulePreset.prn:
        return _buildPRNEditor();
    }
  }

  Widget _buildClockTimesEditor() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _fieldLabel('Times of day'),
        Column(
          children: [
            for (int i = 0; i < _times.length; i++)
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  children: [
                    Expanded(
                      child: _Pressable(
                        onTap: () => _pickTime(i),
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 14, vertical: 12),
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.06),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: Colors.white.withOpacity(0.12),
                              width: 0.8,
                            ),
                          ),
                          child: Row(
                            children: [
                              const Icon(Icons.access_time_rounded,
                                  color: _Jovi.petAccent, size: 16),
                              const SizedBox(width: 10),
                              Text(
                                _fmtTime(_times[i]),
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 14,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                    if (_times.length > 1)
                      IconButton(
                        onPressed: () => setState(() => _times.removeAt(i)),
                        icon: Icon(
                          Icons.remove_circle_outline_rounded,
                          color: Colors.white.withOpacity(0.5),
                          size: 20,
                        ),
                      ),
                  ],
                ),
              ),
            _Pressable(
              onTap: () => setState(() => _times.add('08:00')),
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                decoration: BoxDecoration(
                  color: _Jovi.petAccent.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: _Jovi.petAccent.withOpacity(0.3),
                    width: 0.8,
                  ),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.add_rounded, color: _Jovi.petAccent, size: 16),
                    SizedBox(width: 6),
                    Text(
                      'Add time',
                      style: TextStyle(
                        color: _Jovi.petAccent,
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
        _fieldLabel('Days (empty = daily)'),
        _weekdayChips(),
      ],
    );
  }

  Widget _buildMealsEditor() {
    // Only breakfast/dinner/bedtime for pets (no lunch since most pets eat
    // 2 meals/day and pet meds align to those feeding times).
    const mealOptions = [
      ['breakfast', 'Breakfast', Icons.wb_sunny_rounded],
      ['dinner', 'Dinner', Icons.dinner_dining_rounded],
      ['bedtime', 'Bedtime', Icons.bedtime_rounded],
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _fieldLabel('With which meals'),
        Wrap(
          spacing: 6,
          runSpacing: 6,
          children: [
            for (final m in mealOptions)
              _choiceChip(
                label: m[1] as String,
                icon: m[2] as IconData,
                selected: _mealTimes.contains(m[0] as String),
                onTap: () => setState(() {
                  final tag = m[0] as String;
                  if (_mealTimes.contains(tag)) {
                    _mealTimes.remove(tag);
                  } else {
                    _mealTimes.add(tag);
                  }
                }),
              ),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          'Uses your feeding times from settings: breakfast ${_fmtTime(widget.prefs.breakfastTime)}, dinner ${_fmtTime(widget.prefs.dinnerTime)}, bedtime ${_fmtTime(widget.prefs.bedtimeTime)}',
          style: TextStyle(
            color: Colors.white.withOpacity(0.5),
            fontSize: 10,
            fontStyle: FontStyle.italic,
            height: 1.4,
          ),
        ),
        _fieldLabel('Days (empty = daily)'),
        _weekdayChips(),
      ],
    );
  }

  Widget _buildIntervalEditor() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _fieldLabel('Every N hours'),
        Wrap(
          spacing: 6,
          runSpacing: 6,
          children: [
            for (final h in const [4, 6, 8, 12])
              _choiceChip(
                label: 'Every ${h}h',
                selected: _intervalHours == h,
                onTap: () => setState(() => _intervalHours = h),
              ),
          ],
        ),
        _fieldLabel('First dose time'),
        _Pressable(
          onTap: _pickFirstDose,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.06),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: Colors.white.withOpacity(0.12),
                width: 0.8,
              ),
            ),
            child: Row(
              children: [
                const Icon(Icons.access_time_rounded,
                    color: _Jovi.petAccent, size: 16),
                const SizedBox(width: 10),
                Text(
                  _fmtTime(_firstDoseTime),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildWeeklyEditor() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _fieldLabel('Which days'),
        _weekdayChips(),
        _fieldLabel('Times'),
        Column(
          children: [
            for (int i = 0; i < _times.length; i++)
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: _Pressable(
                  onTap: () => _pickTime(i),
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 14, vertical: 12),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.06),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: Colors.white.withOpacity(0.12),
                        width: 0.8,
                      ),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.access_time_rounded,
                            color: _Jovi.petAccent, size: 16),
                        const SizedBox(width: 10),
                        Text(
                          _fmtTime(_times[i]),
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const Spacer(),
                        if (_times.length > 1)
                          _Pressable(
                            onTap: () => setState(() => _times.removeAt(i)),
                            child: Icon(
                              Icons.close_rounded,
                              color: Colors.white.withOpacity(0.5),
                              size: 18,
                            ),
                          ),
                      ],
                    ),
                  ),
                ),
              ),
            _Pressable(
              onTap: () => setState(() => _times.add('08:00')),
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                decoration: BoxDecoration(
                  color: _Jovi.petAccent.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: _Jovi.petAccent.withOpacity(0.3),
                    width: 0.8,
                  ),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.add_rounded, color: _Jovi.petAccent, size: 16),
                    SizedBox(width: 6),
                    Text(
                      'Add time',
                      style: TextStyle(
                        color: _Jovi.petAccent,
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildTaperEditor() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _fieldLabel('Taper steps'),
        Text(
          'Common for prednisone tapers. Each step starts on the day since the first dose (day 0 = first day).',
          style: TextStyle(
            color: Colors.white.withOpacity(0.55),
            fontSize: 11,
            height: 1.4,
          ),
        ),
        const SizedBox(height: 10),
        for (int i = 0; i < _taperSteps.length; i++)
          Container(
            margin: const EdgeInsets.only(bottom: 6),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.06),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: Colors.white.withOpacity(0.12),
                width: 0.8,
              ),
            ),
            child: Row(
              children: [
                Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(
                    color: _Jovi.petAccent.withOpacity(0.2),
                    shape: BoxShape.circle,
                  ),
                  child: Center(
                    child: Text(
                      '${i + 1}',
                      style: const TextStyle(
                        color: _Jovi.petAccent,
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Day ${_taperSteps[i].startDay}: ${_taperSteps[i].dose}',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      if (_taperSteps[i].times.isNotEmpty)
                        Text(
                          _taperSteps[i].times.map(_fmtTime).join(', '),
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.6),
                            fontSize: 11,
                          ),
                        ),
                    ],
                  ),
                ),
                _Pressable(
                  onTap: () => setState(() => _taperSteps.removeAt(i)),
                  child: Icon(
                    Icons.close_rounded,
                    color: Colors.white.withOpacity(0.5),
                    size: 18,
                  ),
                ),
              ],
            ),
          ),
        _Pressable(
          onTap: () async {
            final step = await _addTaperStepDialog();
            if (step != null) {
              setState(() {
                _taperSteps.add(step);
                _taperSteps.sort((a, b) => a.startDay.compareTo(b.startDay));
              });
            }
          },
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: _Jovi.petAccent.withOpacity(0.12),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: _Jovi.petAccent.withOpacity(0.3),
                width: 0.8,
              ),
            ),
            child: const Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.add_rounded, color: _Jovi.petAccent, size: 16),
                SizedBox(width: 6),
                Text(
                  'Add step',
                  style: TextStyle(
                    color: _Jovi.petAccent,
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildPRNEditor() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _fieldLabel('Max doses per day'),
        Wrap(
          spacing: 6,
          runSpacing: 6,
          children: [
            for (final n in const [1, 2, 3, 4, 6, 8])
              _choiceChip(
                label: '$n',
                selected: _prnMaxPerDay == n,
                onTap: () => setState(() => _prnMaxPerDay = n),
              ),
          ],
        ),
        _fieldLabel('Minimum hours between doses'),
        Wrap(
          spacing: 6,
          runSpacing: 6,
          children: [
            for (final h in const [2.0, 4.0, 6.0, 8.0, 12.0, 24.0])
              _choiceChip(
                label: '${h.toInt()}h',
                selected: _prnMinHoursBetween == h,
                onTap: () => setState(() => _prnMinHoursBetween = h),
              ),
          ],
        ),
      ],
    );
  }

  Widget _weekdayChips() {
    return Wrap(
      spacing: 6,
      runSpacing: 6,
      children: [
        for (int d = 1; d <= 7; d++)
          _choiceChip(
            label: const [
              'Mon',
              'Tue',
              'Wed',
              'Thu',
              'Fri',
              'Sat',
              'Sun'
            ][d - 1],
            selected: _daysOfWeek.contains(d),
            onTap: () => setState(() {
              if (_daysOfWeek.contains(d)) {
                _daysOfWeek.remove(d);
              } else {
                _daysOfWeek.add(d);
              }
            }),
          ),
      ],
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // TAPER STEP DIALOG
  // ═══════════════════════════════════════════════════════════════════════

  Future<TaperStep?> _addTaperStepDialog() async {
    final dayCtrl = TextEditingController(
      text: _taperSteps.isEmpty
          ? '0'
          : (_taperSteps.last.startDay + 7).toString(),
    );
    final doseCtrl = TextEditingController();
    String time = '08:00';
    final result = await showDialog<TaperStep>(
      context: context,
      barrierColor: Colors.black.withOpacity(0.55),
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setSt) => Dialog(
          backgroundColor: Colors.transparent,
          child: Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  _Jovi.navy.withOpacity(0.97),
                  _Jovi.navyDark.withOpacity(0.97),
                ],
              ),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                color: Colors.white.withOpacity(0.14),
                width: 0.8,
              ),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Add taper step',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 14),
                _fieldLabel('Start on day #'),
                _textField(dayCtrl, '0', keyboard: TextInputType.number),
                _fieldLabel('Dose'),
                _textField(doseCtrl, 'e.g. 10 mg'),
                _fieldLabel('Time'),
                _Pressable(
                  onTap: () async {
                    final parts = time.split(':');
                    final picked = await showTimePicker(
                      context: ctx,
                      initialTime: TimeOfDay(
                        hour: int.tryParse(parts[0]) ?? 8,
                        minute:
                            int.tryParse(parts.length > 1 ? parts[1] : '0') ??
                                0,
                      ),
                      builder: (c, ch) => Theme(
                        data: ThemeData.dark().copyWith(
                          colorScheme: const ColorScheme.dark(
                            primary: _Jovi.petAccent,
                            onPrimary: Colors.white,
                            surface: _Jovi.navy,
                          ),
                        ),
                        child: ch!,
                      ),
                    );
                    if (picked != null) {
                      setSt(() {
                        time =
                            '${picked.hour.toString().padLeft(2, "0")}:${picked.minute.toString().padLeft(2, "0")}';
                      });
                    }
                  },
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 14, vertical: 12),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.06),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: Colors.white.withOpacity(0.12),
                        width: 0.8,
                      ),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.access_time_rounded,
                            color: _Jovi.petAccent, size: 16),
                        const SizedBox(width: 10),
                        Text(
                          _fmtTime(time),
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 18),
                Row(
                  children: [
                    Expanded(
                      child: TextButton(
                        onPressed: () => Navigator.pop(ctx),
                        child: Text(
                          'Cancel',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.6),
                          ),
                        ),
                      ),
                    ),
                    Expanded(
                      child: ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: _Jovi.petAccent,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(99),
                          ),
                        ),
                        onPressed: () {
                          final d = int.tryParse(dayCtrl.text) ?? 0;
                          final dose = doseCtrl.text.trim();
                          if (dose.isEmpty) return;
                          Navigator.pop(
                            ctx,
                            TaperStep(
                              startDay: d,
                              dose: dose,
                              times: [time],
                            ),
                          );
                        },
                        child: const Text(
                          'Add',
                          style: TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
    dayCtrl.dispose();
    doseCtrl.dispose();
    return result;
  }

  // ═══════════════════════════════════════════════════════════════════════
  // SAVE HANDLER
  // ═══════════════════════════════════════════════════════════════════════

  Future<void> _handleSave() async {
    if (_nameCtrl.text.trim().isEmpty) {
      _showSnack('Medication name is required', isError: true);
      return;
    }

    // Hard block: if the drug has a fatal species-safety warning, refuse save
    // and show a confirmation dialog. Users can override by explicitly
    // confirming (vet may have specifically prescribed something off-label).
    final safety = _currentSafetyWarning();
    if (safety != null && !_saving) {
      final confirmed = await _confirmSafetyOverride(safety);
      if (!confirmed) return;
    }

    setState(() => _saving = true);

    final String medId = _savedMedId ?? widget.existing?.id ?? 'new';

    // Build times list per preset
    final List<String> finalTimes;
    final bool isPRN = _preset == SchedulePreset.prn;
    if (_preset == SchedulePreset.meals) {
      finalTimes = _mealTimes;
    } else if (_preset == SchedulePreset.interval ||
        _preset == SchedulePreset.prn ||
        _preset == SchedulePreset.taper) {
      finalTimes = const [];
    } else {
      finalTimes = _times;
    }

    final List<int> finalDays = (_preset == SchedulePreset.weekly ||
            _preset == SchedulePreset.clockTimes ||
            _preset == SchedulePreset.meals)
        ? _daysOfWeek
        : const [];

    final med = PetMedication(
      id: medId,
      name: _nameCtrl.text.trim(),
      strength: _strengthCtrl.text.trim(),
      dosage: _dosageCtrl.text.trim(),
      type: _type,
      species: widget.pet.type,
      condition: _conditionCtrl.text.trim().isEmpty
          ? null
          : _conditionCtrl.text.trim(),
      prescribedBy: _prescribedByCtrl.text.trim().isEmpty
          ? null
          : _prescribedByCtrl.text.trim(),
      pharmacy:
          _pharmacyCtrl.text.trim().isEmpty ? null : _pharmacyCtrl.text.trim(),
      notes: _notesCtrl.text.trim().isEmpty ? null : _notesCtrl.text.trim(),
      imageUrl: _imageUrl,
      preset: _preset,
      times: finalTimes,
      daysOfWeek: finalDays,
      isAsNeeded: isPRN,
      startDate: _startDate,
      stopDate: _stopDate,
      pillCount: int.tryParse(_pillCountCtrl.text) ?? 0,
      refillThreshold: int.tryParse(_refillThresholdCtrl.text) ?? 10,
      mealTiming: _mealTiming,
      instructions: _instructions,
      prnMaxPerDay: _prnMaxPerDay,
      prnMinHoursBetween: _prnMinHoursBetween,
      remindersEnabled: _remindersEnabled,
      isTaper: _preset == SchedulePreset.taper,
      taperSteps: _preset == SchedulePreset.taper ? _taperSteps : const [],
      intervalHours: _intervalHours,
      firstDoseTime: _preset == SchedulePreset.interval ? _firstDoseTime : null,
      drugKey: _drugKey,
    );

    final ok = await widget.onSave(med);
    if (mounted) {
      setState(() => _saving = false);
      if (ok) Navigator.pop(context);
    }
  }

  /// If user types a drug flagged as dangerous for this species, they must
  /// explicitly confirm before the save proceeds. This prevents accidental
  /// additions of fatally-toxic drugs (e.g. Tylenol on a cat profile).
  Future<bool> _confirmSafetyOverride(String warning) async {
    final result = await showDialog<bool>(
      context: context,
      barrierColor: Colors.black.withOpacity(0.7),
      builder: (ctx) => Dialog(
        backgroundColor: Colors.transparent,
        child: Container(
          padding: const EdgeInsets.all(22),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [
                _Jovi.navy.withOpacity(0.98),
                _Jovi.navyDark.withOpacity(0.98),
              ],
            ),
            borderRadius: BorderRadius.circular(22),
            border: Border.all(
              color: _Jovi.errorRed.withOpacity(0.5),
              width: 1.2,
            ),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [_Jovi.errorRed, _Jovi.softRed],
                      ),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: const Icon(
                      Icons.dangerous_rounded,
                      color: Colors.white,
                      size: 22,
                    ),
                  ),
                  const SizedBox(width: 12),
                  const Expanded(
                    child: Text(
                      'Hold on — safety check',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 17,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              Text(
                warning,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 13,
                  height: 1.4,
                ),
              ),
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: _Jovi.gold.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  'If your vet specifically prescribed this, you can proceed. Otherwise cancel and call your vet — or ASPCA Poison Control at (888) 426-4435.',
                  style: TextStyle(
                    color: _Jovi.gold.withOpacity(0.95),
                    fontSize: 12,
                    height: 1.4,
                  ),
                ),
              ),
              const SizedBox(height: 18),
              Row(
                children: [
                  Expanded(
                    child: _Pressable(
                      onTap: () => Navigator.pop(ctx, false),
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(99),
                          border: Border.all(
                            color: Colors.white.withOpacity(0.2),
                            width: 0.8,
                          ),
                        ),
                        child: const Center(
                          child: Text(
                            'Cancel',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _Pressable(
                      onTap: () => Navigator.pop(ctx, true),
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [_Jovi.errorRed, _Jovi.softRed],
                          ),
                          borderRadius: BorderRadius.circular(99),
                        ),
                        child: const Center(
                          child: Text(
                            'Vet OK\'d it',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 13,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
    return result ?? false;
  }
}
// END OF _AddEditPetMedSheetState class

// ═══════════════════════════════════════════════════════════════════════════
// Legacy alias for any stale imports referring to JoviPetMedications.
// ═══════════════════════════════════════════════════════════════════════════

class JoviPetMedications extends PetMedications {
  const JoviPetMedications({
    super.key,
    super.width,
    super.height,
    super.petId,
  });
}
