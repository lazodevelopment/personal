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
// JOVI HEALTH — PET RECORDS
// Version: 2026.09.22-r2 (Apple HIG pass: press feedback, painted glass
//          rows, Reduce Motion, title-case labels, navy toasts)
// r1:      2026.04.18
// Build: JC-PETREC-0922-002
//
// A unified view of everything we know about a pet's care history today.
// Reads from three existing Jovi subcollections and merges them into a
// single timeline:
//
//   users/{uid}/pets/{petId}/vaccinations/*
//   users/{uid}/pets/{petId}/medications/*
//   users/{uid}/pets/{petId}/symptom_checks/*
//
// Layout:
//   - Upcoming tab — placeholder until vet-partnership booking comes online.
//     Shows next due vaccinations (derived from expiration dates) and any
//     active medications as a stopgap.
//   - Past visits tab — placeholder until vet data feeds exist. Shows
//     recent symptom checks as a stopgap.
//   - Timeline tab — unified chronological view of all three sources.
//
// When vet partnerships come online, drop-in subcollections (vet_visits,
// lab_results, prescriptions from vets) will render in the same timeline
// by extending _PetCareEventKind.
// ═══════════════════════════════════════════════════════════════════════════

import 'dart:convert';
import 'dart:async';
import 'dart:ui' as ui_dart;
import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:url_launcher/url_launcher.dart';
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

class PetRecords extends StatefulWidget {
  // No required params — matches FF UI setup.
  final String? petId; // optional — deep-link from a pet profile

  final double? width;
  final double? height;

  const PetRecords({
    Key? key,
    this.width,
    this.height,
    this.petId,
  }) : super(key: key);

  @override
  State<PetRecords> createState() => _PetRecordsState();
}

class _PetRecordsState extends State<PetRecords> with TickerProviderStateMixin {
  // ─── Tab state ──────────────────────────────────────────────────────────
  _Tab _currentTab = _Tab.timeline;

  // ─── Pets state ─────────────────────────────────────────────────────────
  List<_PetLite> _pets = [];
  bool _petsLoading = true;
  _PetLite? _selectedPet;

  // ─── Vaccinations state ─────────────────────────────────────────────────
  List<_VaccinationRec> _vaccinations = [];
  bool _vaccinationsLoading = true;
  String? _vaccinationsError;
  StreamSubscription<QuerySnapshot<Map<String, dynamic>>>? _vaccinationsSub;

  // ─── Medications state ──────────────────────────────────────────────────
  List<_MedicationRec> _medications = [];
  bool _medicationsLoading = true;
  String? _medicationsError;
  StreamSubscription<QuerySnapshot<Map<String, dynamic>>>? _medicationsSub;

  // ─── Symptom checks state ───────────────────────────────────────────────
  List<_SymptomCheckRec> _symptomChecks = [];
  bool _symptomChecksLoading = true;
  String? _symptomChecksError;
  StreamSubscription<QuerySnapshot<Map<String, dynamic>>>? _symptomChecksSub;

  // ─── Vet weight logs state ──────────────────────────────────────────────
  List<_VetWeightRec> _vetWeights = [];
  bool _vetWeightsLoading = true;
  String? _vetWeightsError;
  StreamSubscription<QuerySnapshot<Map<String, dynamic>>>? _vetWeightsSub;
  // Set of logIds that have an active (non-dismissed) alert, to mark the
  // corresponding _VetWeightRec as flaggedAboveRange for timeline rendering.
  Set<String> _flaggedWeightLogIds = {};
  StreamSubscription<QuerySnapshot<Map<String, dynamic>>>? _weightAlertsSub;

  // ─── Animations ─────────────────────────────────────────────────────────
  late AnimationController _fadeCtrl;
  late Animation<double> _fadeAnim;

  // ─── Derived data (recomputed when any source updates) ──────────────────
  // The Timeline merges all three sources sorted descending by `when`.
  // Medications can generate TWO events (start + stop) if they've ended.
  List<_PetCareEvent> get _timelineEvents {
    final events = <_PetCareEvent>[];
    for (final v in _vaccinations) {
      events.add(_PetCareEvent.fromVaccination(v));
    }
    for (final m in _medications) {
      events.add(_PetCareEvent.fromMedicationStart(m));
      if (m.stopDate != null && m.stopDate!.isBefore(DateTime.now())) {
        events.add(_PetCareEvent.fromMedicationStop(m));
      }
    }
    for (final sc in _symptomChecks) {
      events.add(_PetCareEvent.fromSymptomCheck(sc));
    }
    for (final w in _vetWeights) {
      final flagged = _flaggedWeightLogIds.contains(w.id);
      events.add(_PetCareEvent.fromVetWeight(flagged ? w.withFlag(true) : w));
    }
    // Sort descending by when (newest first)
    events.sort((a, b) => b.when.compareTo(a.when));
    return events;
  }

  /// Group events by calendar month for timeline section headers.
  /// Returns a list of (monthLabel, events) entries in reverse chronological.
  List<MapEntry<String, List<_PetCareEvent>>> get _timelineGroupedByMonth {
    final groups = <String, List<_PetCareEvent>>{};
    for (final e in _timelineEvents) {
      final key = DateFormat('MMMM y').format(e.when);
      groups.putIfAbsent(key, () => []).add(e);
    }
    return groups.entries.toList();
  }

  /// "Upcoming" tab items — we don't have future vet appointments yet,
  /// so we derive a reasonable upcoming list from existing data:
  ///   - Vaccinations whose expirationDate is in the future (or within 60d)
  ///   - Active medications (for medication reminder awareness)
  List<_VaccinationRec> get _upcomingVaccinations {
    final list = _vaccinations.where((v) {
      if (v.expirationDate == null) return false;
      return v.expirationDate!.isAfter(DateTime.now());
    }).toList();
    list.sort((a, b) => a.expirationDate!.compareTo(b.expirationDate!));
    return list;
  }

  List<_MedicationRec> get _activeMedications {
    final list = _medications.where((m) => m.isActive).toList();
    list.sort((a, b) => b.startDate.compareTo(a.startDate));
    return list;
  }

  /// "Past visits" tab — until vet partnerships bring real visit data,
  /// we surface recent symptom checks as the stopgap history.
  List<_SymptomCheckRec> get _pastSymptomChecks {
    final list = List<_SymptomCheckRec>.from(_symptomChecks);
    list.sort((a, b) => b.createdAt.compareTo(a.createdAt));
    return list;
  }

  /// Loading state helpers
  bool get _anyLoading =>
      _vaccinationsLoading ||
      _medicationsLoading ||
      _symptomChecksLoading ||
      _vetWeightsLoading;

  bool get _allEmpty =>
      _vaccinations.isEmpty &&
      _medications.isEmpty &&
      _symptomChecks.isEmpty &&
      _vetWeights.isEmpty;

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

    _loadPets();
  }

  @override
  void dispose() {
    _fadeCtrl.dispose();
    _vaccinationsSub?.cancel();
    _medicationsSub?.cancel();
    _symptomChecksSub?.cancel();
    _vetWeightsSub?.cancel();
    _weightAlertsSub?.cancel();
    super.dispose();
  }

  // ═══════════════════════════════════════════════════════════════════════
  // PET LOADING (dual-source: subcollection canonical + legacy JSON array)
  // Matches Pet Symptom Checker / Pet Meds / Vaccinations pattern.
  // ═══════════════════════════════════════════════════════════════════════

  Future<void> _loadPets() async {
    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user == null) {
        if (mounted) setState(() => _petsLoading = false);
        return;
      }

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
          debugPrint('PetRecords: skipped malformed pet ${doc.id}: $e');
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
            debugPrint('PetRecords: skipped malformed legacy pet: $e');
          }
        }
      }

      if (!mounted) return;

      final list = byId.values.toList()
        ..sort((a, b) => a.name.toLowerCase().compareTo(b.name.toLowerCase()));

      // Pick initial selection
      _PetLite? initial;
      if (widget.petId != null && widget.petId!.isNotEmpty) {
        for (final p in list) {
          if (p.petId == widget.petId) {
            initial = p;
            break;
          }
        }
      }
      initial ??= list.isNotEmpty ? list.first : null;

      setState(() {
        _pets = list;
        _selectedPet = initial;
        _petsLoading = false;
      });

      if (initial != null) {
        _subscribeAll(initial.petId);
      } else {
        // No pet — mark all sub-loads as finished with empty data
        setState(() {
          _vaccinationsLoading = false;
          _medicationsLoading = false;
          _symptomChecksLoading = false;
          _vetWeightsLoading = false;
        });
      }
    } catch (e) {
      debugPrint('PetRecords: failed to load pets: $e');
      if (!mounted) return;
      setState(() {
        _petsLoading = false;
        _vaccinationsLoading = false;
        _medicationsLoading = false;
        _symptomChecksLoading = false;
        _vetWeightsLoading = false;
      });
    }
  }

  void _onPetSwitched(_PetLite pet) {
    if (pet.petId == _selectedPet?.petId) return;
    HapticFeedback.selectionClick();
    setState(() {
      _selectedPet = pet;
      // Reset collections — subscribers will fill them back in
      _vaccinations = [];
      _medications = [];
      _symptomChecks = [];
      _vetWeights = [];
      _flaggedWeightLogIds = {};
      _vaccinationsLoading = true;
      _medicationsLoading = true;
      _symptomChecksLoading = true;
      _vetWeightsLoading = true;
      _vaccinationsError = null;
      _medicationsError = null;
      _symptomChecksError = null;
      _vetWeightsError = null;
    });
    _subscribeAll(pet.petId);
  }

  // ═══════════════════════════════════════════════════════════════════════
  // THREE PARALLEL SUBSCRIPTIONS (vaccinations, medications, symptom_checks)
  // Each has its own error state; the timeline renders whatever is available.
  // ═══════════════════════════════════════════════════════════════════════

  void _subscribeAll(String petId) {
    _subscribeVaccinations(petId);
    _subscribeMedications(petId);
    _subscribeSymptomChecks(petId);
    _subscribeVetWeights(petId);
    _subscribeWeightAlerts(petId);
  }

  void _subscribeVaccinations(String petId) {
    _vaccinationsSub?.cancel();
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      if (mounted) {
        setState(() {
          _vaccinationsLoading = false;
          _vaccinations = [];
        });
      }
      return;
    }
    try {
      _vaccinationsSub = FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .collection('pets')
          .doc(petId)
          .collection('vaccinations')
          .snapshots()
          .listen(
        (snap) {
          if (!mounted) return;
          final list = <_VaccinationRec>[];
          for (final doc in snap.docs) {
            try {
              list.add(_VaccinationRec.fromFirestore(doc.id, doc.data()));
            } catch (e) {
              debugPrint('PetRecords: skipped malformed vaccination ${doc.id}: $e');
            }
          }
          list.sort((a, b) => b.administeredDate.compareTo(a.administeredDate));
          setState(() {
            _vaccinations = list;
            _vaccinationsLoading = false;
            _vaccinationsError = null;
          });
        },
        onError: (err) {
          debugPrint('PetRecords: vaccinations listener error: $err');
          if (!mounted) return;
          setState(() {
            _vaccinationsLoading = false;
            _vaccinationsError = _friendlyErrorMessage(_classifyError(err));
          });
        },
        cancelOnError: false,
      );
    } catch (e) {
      debugPrint('PetRecords: failed to subscribe to vaccinations: $e');
      if (!mounted) return;
      setState(() {
        _vaccinationsLoading = false;
        _vaccinationsError = _friendlyErrorMessage(_classifyError(e));
      });
    }
  }

  void _subscribeMedications(String petId) {
    _medicationsSub?.cancel();
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      if (mounted) {
        setState(() {
          _medicationsLoading = false;
          _medications = [];
        });
      }
      return;
    }
    try {
      _medicationsSub = FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .collection('pets')
          .doc(petId)
          .collection('medications')
          .snapshots()
          .listen(
        (snap) {
          if (!mounted) return;
          final list = <_MedicationRec>[];
          for (final doc in snap.docs) {
            try {
              list.add(_MedicationRec.fromFirestore(doc.id, doc.data()));
            } catch (e) {
              debugPrint('PetRecords: skipped malformed medication ${doc.id}: $e');
            }
          }
          list.sort((a, b) => b.startDate.compareTo(a.startDate));
          setState(() {
            _medications = list;
            _medicationsLoading = false;
            _medicationsError = null;
          });
        },
        onError: (err) {
          debugPrint('PetRecords: medications listener error: $err');
          if (!mounted) return;
          setState(() {
            _medicationsLoading = false;
            _medicationsError = _friendlyErrorMessage(_classifyError(err));
          });
        },
        cancelOnError: false,
      );
    } catch (e) {
      debugPrint('PetRecords: failed to subscribe to medications: $e');
      if (!mounted) return;
      setState(() {
        _medicationsLoading = false;
        _medicationsError = _friendlyErrorMessage(_classifyError(e));
      });
    }
  }

  void _subscribeSymptomChecks(String petId) {
    _symptomChecksSub?.cancel();
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      if (mounted) {
        setState(() {
          _symptomChecksLoading = false;
          _symptomChecks = [];
        });
      }
      return;
    }
    try {
      _symptomChecksSub = FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .collection('pets')
          .doc(petId)
          .collection('symptom_checks')
          .orderBy('createdAt', descending: true)
          .limit(100)
          .snapshots()
          .listen(
        (snap) {
          if (!mounted) return;
          final list = <_SymptomCheckRec>[];
          for (final doc in snap.docs) {
            try {
              list.add(_SymptomCheckRec.fromFirestore(doc.id, doc.data()));
            } catch (e) {
              debugPrint(
                  'PetRecords: skipped malformed symptom check ${doc.id}: $e');
            }
          }
          setState(() {
            _symptomChecks = list;
            _symptomChecksLoading = false;
            _symptomChecksError = null;
          });
        },
        onError: (err) {
          debugPrint('PetRecords: symptom_checks listener error: $err');
          if (!mounted) return;
          setState(() {
            _symptomChecksLoading = false;
            _symptomChecksError = _friendlyErrorMessage(_classifyError(err));
          });
        },
        cancelOnError: false,
      );
    } catch (e) {
      debugPrint('PetRecords: failed to subscribe to symptom_checks: $e');
      if (!mounted) return;
      setState(() {
        _symptomChecksLoading = false;
        _symptomChecksError = _friendlyErrorMessage(_classifyError(e));
      });
    }
  }

  void _subscribeVetWeights(String petId) {
    _vetWeightsSub?.cancel();
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      if (mounted) {
        setState(() {
          _vetWeightsLoading = false;
          _vetWeights = [];
        });
      }
      return;
    }
    try {
      _vetWeightsSub = FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .collection('pets')
          .doc(petId)
          .collection('vet_weight_logs')
          .orderBy('recordedAt', descending: true)
          .limit(50)
          .snapshots()
          .listen(
        (snap) {
          if (!mounted) return;
          final list = <_VetWeightRec>[];
          for (final doc in snap.docs) {
            try {
              list.add(_VetWeightRec.fromFirestore(doc.id, doc.data()));
            } catch (e) {
              debugPrint('PetRecords: skipped malformed vet weight ${doc.id}: $e');
            }
          }
          setState(() {
            _vetWeights = list;
            _vetWeightsLoading = false;
            _vetWeightsError = null;
          });
        },
        onError: (err) {
          debugPrint('PetRecords: vet_weight_logs listener error: $err');
          if (!mounted) return;
          setState(() {
            _vetWeightsLoading = false;
            _vetWeightsError = _friendlyErrorMessage(_classifyError(err));
          });
        },
        cancelOnError: false,
      );
    } catch (e) {
      debugPrint('PetRecords: failed to subscribe to vet_weight_logs: $e');
      if (!mounted) return;
      setState(() {
        _vetWeightsLoading = false;
        _vetWeightsError = _friendlyErrorMessage(_classifyError(e));
      });
    }
  }

  /// Subscribe to weight_alerts docs for this pet so we can mark matching
  /// vet_weight_logs as flaggedAboveRange in the timeline. Alert docs are
  /// scoped to the user, not the pet, so we filter server-side by petId.
  void _subscribeWeightAlerts(String petId) {
    _weightAlertsSub?.cancel();
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return;
    try {
      _weightAlertsSub = FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .collection('weight_alerts')
          .where('petId', isEqualTo: petId)
          .snapshots()
          .listen(
        (snap) {
          if (!mounted) return;
          final ids = <String>{};
          for (final doc in snap.docs) {
            final data = doc.data();
            // Use logId field if present; fall back to doc id
            final logId = (data['logId'] as String?) ?? doc.id;
            ids.add(logId);
          }
          setState(() {
            _flaggedWeightLogIds = ids;
          });
        },
        onError: (err) {
          // Non-fatal — the timeline still renders without the flag.
          debugPrint('PetRecords: weight_alerts listener error: $err');
        },
        cancelOnError: false,
      );
    } catch (e) {
      debugPrint('PetRecords: failed to subscribe to weight_alerts: $e');
    }
  }

  // ═══════════════════════════════════════════════════════════════════════
  // NAVIGATION HELPERS — deep-link into existing pet widgets
  // ═══════════════════════════════════════════════════════════════════════

  void _openVaccinations() {
    HapticFeedback.lightImpact();
    final pet = _selectedPet;
    final params = <String, String>{};
    if (pet != null) params['petId'] = pet.petId;
    _tryRoute(
        ['petVaccinations', 'PetVaccinations', 'pet_vaccinations'], params);
  }

  void _openMedications() {
    HapticFeedback.lightImpact();
    final pet = _selectedPet;
    final params = <String, String>{};
    if (pet != null) params['petId'] = pet.petId;
    _tryRoute(
      ['petMedications', 'PetMedications', 'pet_medications'],
      params,
    );
  }

  void _openSymptomChecker() {
    HapticFeedback.lightImpact();
    final pet = _selectedPet;
    final params = <String, String>{};
    if (pet != null) params['petId'] = pet.petId;
    _tryRoute(
      ['petSymptomChecker', 'PetSymptomChecker', 'pet_symptom_checker'],
      params,
    );
  }

  void _openPetProfile() {
    HapticFeedback.lightImpact();
    final pet = _selectedPet;
    final params = <String, String>{};
    if (pet != null) params['petId'] = pet.petId;
    _tryRoute(['petPro', 'petProfiles', 'PetProfiles', 'pet_profiles'], params);
  }

  void _routeToVetRequest() {
    HapticFeedback.mediumImpact();
    final pet = _selectedPet;
    final params = <String, String>{
      'visitMode': 'Clinic',
      'audience': 'Pet',
    };
    if (pet != null) params['petId'] = pet.petId;
    _tryRoute(
      ['requests', 'Requests', 'requestCare'],
      params,
      fallbackMessage:
          "Couldn't open the request flow. Try from the dashboard.",
    );
  }

  // NOTE: context.pushNamed never throws on an unknown name at runtime, so
  // only the FIRST candidate is ever tried. Confirm the first name in each
  // list matches the real FlutterFlow route.
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
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(
        fallbackMessage ?? "Couldn't open that screen.",
        accent: _joviErrorRed,
        icon: CupertinoIcons.exclamationmark_circle));
  }

  // ═══════════════════════════════════════════════════════════════════════
  // ROOT BUILD
  // ═══════════════════════════════════════════════════════════════════════

  @override
  Widget build(BuildContext context) {
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
              _buildHeader(),
              _buildTabBar(),
              Expanded(child: _buildTabContent()),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTabContent() {
    if (_currentTab == _Tab.upcoming) return _buildUpcomingView();
    if (_currentTab == _Tab.past) return _buildPastView();
    return _buildTimelineView();
  }

  // ═══════════════════════════════════════════════════════════════════════
  // HEADER + PET PICKER
  // ═══════════════════════════════════════════════════════════════════════

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 8),
      child: Row(
        children: [
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [_petAccent, _petAccentDark],
              ),
              borderRadius: BorderRadius.circular(11),
              boxShadow: [
                BoxShadow(
                  color: _petAccent.withOpacity(0.35),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: const Icon(
              Icons.folder_shared_rounded,
              color: Colors.white,
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
                  'Pet Records',
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
                  'Everything in one place',
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
          _buildPetPickerChip(),
        ],
      ),
    );
  }

  Widget _buildPetPickerChip() {
    if (_petsLoading) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.06),
          borderRadius: BorderRadius.circular(22),
          border: Border.all(
            color: Colors.white.withOpacity(0.12),
            width: 0.8,
          ),
        ),
        child: const SizedBox(
          width: 14,
          height: 14,
          child: CircularProgressIndicator(
            strokeWidth: 2,
            valueColor: AlwaysStoppedAnimation<Color>(Colors.white70),
          ),
        ),
      );
    }
    if (_pets.isEmpty) {
      return _PressableMaterial(
        child: InkWell(
          onTap: _openPetProfile,
          borderRadius: BorderRadius.circular(22),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: _petAccent.withOpacity(0.15),
              borderRadius: BorderRadius.circular(22),
              border: Border.all(
                color: _petAccent.withOpacity(0.35),
                width: 0.8,
              ),
            ),
            child: const Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.add_rounded, color: _petAccent, size: 14),
                SizedBox(width: 4),
                Text(
                  'Add a pet',
                  style: TextStyle(
                    color: _petAccent,
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -0.2,
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    }
    final pet = _selectedPet;
    return _PressableMaterial(
      child: InkWell(
        onTap: _pets.length > 1 ? _showPetSwitcher : null,
        borderRadius: BorderRadius.circular(22),
        child: Container(
          padding: const EdgeInsets.fromLTRB(6, 6, 12, 6),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.08),
            borderRadius: BorderRadius.circular(22),
            border: Border.all(
              color: _petAccent.withOpacity(0.3),
              width: 0.8,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              _petAvatar(pet, size: 28),
              const SizedBox(width: 8),
              Flexible(
                child: Text(
                  pet?.name ?? 'Pet',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -0.2,
                  ),
                ),
              ),
              if (_pets.length > 1) ...[
                const SizedBox(width: 4),
                Icon(
                  Icons.unfold_more_rounded,
                  color: Colors.white.withOpacity(0.55),
                  size: 14,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _petAvatar(_PetLite? pet, {double size = 28}) {
    if (pet?.photoUrl != null && pet!.photoUrl!.isNotEmpty) {
      return ClipOval(
        child: Image.network(
          pet.photoUrl!,
          width: size,
          height: size,
          fit: BoxFit.cover,
          errorBuilder: (_, __, ___) => _petAvatarFallback(pet, size),
        ),
      );
    }
    return _petAvatarFallback(pet, size);
  }

  Widget _petAvatarFallback(_PetLite? pet, double size) {
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

  void _showPetSwitcher() {
    HapticFeedback.lightImpact();
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (ctx) => ClipRRect(
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
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
                  const BorderRadius.vertical(top: Radius.circular(24)),
              border: Border.all(
                color: Colors.white.withOpacity(0.1),
                width: 1,
              ),
            ),
            child: SafeArea(
              top: false,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    margin: const EdgeInsets.only(top: 10),
                    width: 38,
                    height: 4,
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                  const Padding(
                    padding: EdgeInsets.fromLTRB(20, 14, 20, 6),
                    child: Align(
                      alignment: Alignment.centerLeft,
                      child: Text(
                        'Switch Pet',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 17,
                          fontWeight: FontWeight.w600,
                          letterSpacing: -0.4,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 4),
                  ..._pets.map((p) => _petSwitcherRow(ctx, p)),
                  const SizedBox(height: 12),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _petSwitcherRow(BuildContext ctx, _PetLite pet) {
    final selected = pet.petId == _selectedPet?.petId;
    return _PressableMaterial(
      child: InkWell(
        onTap: () {
          Navigator.pop(ctx);
          _onPetSwitched(pet);
        },
        child: Container(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 12),
          child: Row(
            children: [
              _petAvatar(pet, size: 36),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      pet.name,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 14.5,
                        fontWeight: FontWeight.w700,
                        letterSpacing: -0.2,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      _petSubtitle(pet),
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.55),
                        fontSize: 11.5,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
              if (selected)
                const Icon(Icons.check_rounded, color: _petAccent, size: 20),
            ],
          ),
        ),
      ),
    );
  }

  String _petSubtitle(_PetLite pet) {
    final parts = <String>[];
    if (pet.type == PetType.dog) {
      parts.add('Dog');
    } else if (pet.type == PetType.cat) {
      parts.add('Cat');
    }
    if (pet.breed != null && pet.breed!.isNotEmpty) parts.add(pet.breed!);
    final age = pet.ageYears;
    if (age != null) parts.add('$age yr');
    if (parts.isEmpty) return '—';
    return parts.join(' · ');
  }

  // ═══════════════════════════════════════════════════════════════════════
  // TAB BAR
  // ═══════════════════════════════════════════════════════════════════════

  Widget _buildTabBar() {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 4, 16, 6),
      padding: const EdgeInsets.all(3),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.06),
        borderRadius: BorderRadius.circular(11),
        border: Border.all(
          color: Colors.white.withOpacity(0.1),
          width: 0.8,
        ),
      ),
      child: Row(
        children: [
          _tabBarItem(_Tab.upcoming, 'Upcoming', Icons.event_available_rounded),
          _tabBarItem(_Tab.past, 'Past visits', Icons.history_rounded),
          _tabBarItem(_Tab.timeline, 'Timeline', Icons.timeline_rounded),
        ],
      ),
    );
  }

  Widget _tabBarItem(_Tab tab, String label, IconData icon) {
    final selected = _currentTab == tab;
    return Expanded(
      child: _PressableMaterial(
        child: InkWell(
          onTap: () {
            if (_currentTab == tab) return;
            HapticFeedback.selectionClick();
            setState(() => _currentTab = tab);
            if (MediaQuery.maybeOf(context)?.disableAnimations ?? false) {
              _fadeCtrl.value = 1.0;
            } else {
              _fadeCtrl.forward(from: 0.35);
            }
          },
          borderRadius: BorderRadius.circular(9),
          child: AnimatedContainer(
            duration: _Motion.select,
            curve: _Motion.settle,
            padding: const EdgeInsets.symmetric(vertical: 10),
            decoration: BoxDecoration(
              color:
                  selected ? _petAccent.withOpacity(0.22) : Colors.transparent,
              borderRadius: BorderRadius.circular(9),
              border: selected
                  ? Border.all(
                      color: _petAccent.withOpacity(0.4),
                      width: 0.8,
                    )
                  : null,
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  icon,
                  size: 14,
                  color: selected ? _petAccent : Colors.white.withOpacity(0.55),
                ),
                const SizedBox(width: 5),
                Flexible(
                  child: Text(
                    label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: selected
                          ? Colors.white
                          : Colors.white.withOpacity(0.55),
                      fontSize: 11.5,
                      fontWeight: FontWeight.w800,
                      letterSpacing: -0.2,
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

  // ═══════════════════════════════════════════════════════════════════════
  // COMMON HELPERS (glass cards, pills, buttons)
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
    // Painted glass: every timeline row and card lives in a ListView over
    // an opaque navy gradient, where a live blur is pure GPU cost.
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

  Widget _sectionHeader({
    required String title,
    String? subtitle,
    IconData? icon,
    Color? accent,
    Widget? trailing,
  }) {
    final c = accent ?? _petAccent;
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 16, 14, 10),
      child: Row(
        children: [
          if (icon != null) ...[
            Container(
              width: 30,
              height: 30,
              decoration: BoxDecoration(
                color: c.withOpacity(0.16),
                borderRadius: BorderRadius.circular(9),
                border: Border.all(color: c.withOpacity(0.3), width: 0.8),
              ),
              child: Icon(icon, color: c, size: 16),
            ),
            const SizedBox(width: 10),
          ],
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 14,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -0.2,
                  ),
                ),
                if (subtitle != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    subtitle,
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.55),
                      fontSize: 11.5,
                      fontWeight: FontWeight.w500,
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

  /// A "jump to ..." link used throughout — opens another widget with a
  /// subtle right arrow chevron.
  Widget _jumpLink({
    required String label,
    required VoidCallback onTap,
    IconData? icon,
    Color? accent,
  }) {
    final c = accent ?? _petAccent;
    return _PressableMaterial(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(
            color: c.withOpacity(0.12),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: c.withOpacity(0.3), width: 0.8),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (icon != null) ...[
                Icon(icon, color: c, size: 13),
                const SizedBox(width: 4),
              ],
              Text(
                label,
                style: TextStyle(
                  color: c,
                  fontSize: 11.5,
                  fontWeight: FontWeight.w800,
                  letterSpacing: -0.2,
                ),
              ),
              const SizedBox(width: 2),
              Icon(Icons.chevron_right_rounded, color: c, size: 14),
            ],
          ),
        ),
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
    final c1 = accent ?? _petAccent;
    final c2 = accentDark ?? _petAccentDark;
    return _PressableMaterial(
      child: InkWell(
        onTap: () {
          HapticFeedback.mediumImpact();
          onTap();
        },
        borderRadius: BorderRadius.circular(14),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(vertical: 14),
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
              Text(
                label,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                  letterSpacing: -0.2,
                ),
              ),
              if (icon != null) ...[
                const SizedBox(width: 6),
                Icon(icon, color: Colors.white, size: 18),
              ],
            ],
          ),
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // EMPTY STATES (shared)
  // ═══════════════════════════════════════════════════════════════════════

  Widget _buildNoPetEmptyState() {
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
                color: Colors.white.withOpacity(0.05),
                shape: BoxShape.circle,
                border: Border.all(
                  color: Colors.white.withOpacity(0.12),
                  width: 1,
                ),
              ),
              child: Icon(
                Icons.pets_outlined,
                color: Colors.white.withOpacity(0.4),
                size: 32,
              ),
            ),
            const SizedBox(height: 18),
            const Text(
              'No pet yet',
              style: TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.w800,
                color: Colors.white,
                letterSpacing: -0.3,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'Add a pet from your account to start tracking their health records here.',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 13,
                color: Colors.white.withOpacity(0.55),
                fontWeight: FontWeight.w500,
                height: 1.35,
              ),
            ),
            const SizedBox(height: 20),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32),
              child: _primaryButton(
                label: 'Add a pet',
                icon: Icons.arrow_forward_rounded,
                onTap: _openPetProfile,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLoadingState() {
    return const Center(
      child: SizedBox(
        width: 28,
        height: 28,
        child: CircularProgressIndicator(
          strokeWidth: 2.5,
          valueColor: AlwaysStoppedAnimation<Color>(_petAccent),
        ),
      ),
    );
  }

  /// Soft "coming soon" placeholder card — used in Upcoming and Past tabs
  /// while vet partnership data isn't available yet.
  Widget _comingSoonCard({
    required String title,
    required String body,
    required IconData icon,
    Color? accent,
  }) {
    final c = accent ?? _petAccent;
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 6, 14, 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: c.withOpacity(0.08),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: c.withOpacity(0.22), width: 0.8),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 34,
            height: 34,
            decoration: BoxDecoration(
              color: c.withOpacity(0.16),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: c.withOpacity(0.3), width: 0.8),
            ),
            child: Icon(icon, color: c, size: 17),
          ),
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
                        title,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 13.5,
                          fontWeight: FontWeight.w800,
                          letterSpacing: -0.2,
                        ),
                      ),
                    ),
                    const SizedBox(width: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 7, vertical: 2),
                      decoration: BoxDecoration(
                        color: c.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(7),
                      ),
                      child: Text(
                        'Coming Soon',
                        style: TextStyle(
                          color: c,
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          letterSpacing: -0.1,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 3),
                Text(
                  body,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.62),
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                    height: 1.35,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _errorBanner(String message, {VoidCallback? onRetry}) {
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 6, 14, 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: _joviErrorRed.withOpacity(0.1),
        borderRadius: BorderRadius.circular(11),
        border: Border.all(
          color: _joviErrorRed.withOpacity(0.3),
          width: 0.8,
        ),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline_rounded,
              color: _joviErrorRed, size: 16),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              style: TextStyle(
                color: Colors.white.withOpacity(0.85),
                fontSize: 12,
                fontWeight: FontWeight.w600,
                height: 1.3,
              ),
            ),
          ),
          if (onRetry != null) ...[
            const SizedBox(width: 8),
            _jumpLink(
              label: 'Retry',
              onTap: onRetry,
              accent: _joviErrorRed,
              icon: Icons.refresh_rounded,
            ),
          ],
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // UPCOMING TAB
  // Until vet partnerships go live, we derive "upcoming" from:
  //   - Vaccinations with future expirationDate (next due)
  //   - Active medications (reminders set vs. ended)
  // A placeholder card explains that vet appointments will land here.
  // ═══════════════════════════════════════════════════════════════════════

  Widget _buildUpcomingView() {
    if (_selectedPet == null) return _buildNoPetEmptyState();
    if (_anyLoading && _allEmpty) return _buildLoadingState();

    final upcomingVax = _upcomingVaccinations;
    final activeMeds = _activeMedications;
    final petName = _selectedPet!.name;

    return ListView(
      padding: const EdgeInsets.only(bottom: 24),
      children: [
        // Coming-soon appointment placeholder
        _comingSoonCard(
          title: 'Vet appointments',
          body:
              "When partner clinics come online, your upcoming vet visits for $petName will appear here — with reminders, intake prep, and one-tap rescheduling.",
          icon: Icons.event_available_rounded,
          accent: _joviMint,
        ),

        // Next due vaccinations
        _sectionHeader(
          title: 'Next due vaccinations',
          subtitle: upcomingVax.isEmpty
              ? 'Nothing on the horizon'
              : '${upcomingVax.length} upcoming',
          icon: Icons.vaccines_rounded,
          accent: _joviMint,
          trailing: _jumpLink(
            label: 'All',
            onTap: _openVaccinations,
            accent: _joviMint,
            icon: Icons.open_in_new_rounded,
          ),
        ),
        if (_vaccinationsError != null)
          _errorBanner(
            _vaccinationsError!,
            onRetry: _selectedPet == null
                ? null
                : () => _subscribeVaccinations(_selectedPet!.petId),
          )
        else if (upcomingVax.isEmpty)
          _inlineEmptyRow(
            message:
                "No scheduled boosters. When you log a vaccine with a 'next due' date, it'll show up here.",
            accent: _joviMint,
          )
        else
          ...upcomingVax.take(4).map(_buildUpcomingVaxCard),

        // Active medications (as stopgap for reminder awareness)
        _sectionHeader(
          title: 'Active medications',
          subtitle: activeMeds.isEmpty
              ? "$petName isn't on any meds right now"
              : '${activeMeds.length} active',
          icon: Icons.medication_rounded,
          accent: _petAccent,
          trailing: _jumpLink(
            label: 'All',
            onTap: _openMedications,
            accent: _petAccent,
            icon: Icons.open_in_new_rounded,
          ),
        ),
        if (_medicationsError != null)
          _errorBanner(
            _medicationsError!,
            onRetry: _selectedPet == null
                ? null
                : () => _subscribeMedications(_selectedPet!.petId),
          )
        else if (activeMeds.isEmpty)
          _inlineEmptyRow(
            message:
                'No active medications. Add one from the Medications tracker to see reminders and refill status here.',
            accent: _petAccent,
          )
        else
          ...activeMeds.take(6).map(_buildActiveMedCard),

        const SizedBox(height: 16),
      ],
    );
  }

  Widget _inlineEmptyRow({required String message, required Color accent}) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 0, 14, 6),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.04),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: Colors.white.withOpacity(0.09),
            width: 0.8,
          ),
        ),
        child: Row(
          children: [
            Icon(Icons.info_outline_rounded,
                color: accent.withOpacity(0.6), size: 15),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                message,
                style: TextStyle(
                  color: Colors.white.withOpacity(0.55),
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                  height: 1.35,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildUpcomingVaxCard(_VaccinationRec v) {
    final dueSoon = v.isDueSoon;
    final accent = dueSoon ? _joviGold : _joviMint;
    final dateStr = v.expirationDate != null
        ? DateFormat('MMM d, y').format(v.expirationDate!)
        : '—';
    final daysUntil = v.expirationDate != null
        ? v.expirationDate!.difference(DateTime.now()).inDays
        : null;
    String? relative;
    if (daysUntil != null) {
      if (daysUntil <= 0) {
        relative = 'Due now';
      } else if (daysUntil == 1) {
        relative = 'Due tomorrow';
      } else if (daysUntil < 30) {
        relative = 'Due in $daysUntil days';
      } else if (daysUntil < 60) {
        relative = 'Due in ${(daysUntil / 7).round()} weeks';
      }
    }
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 0, 14, 8),
      child: _PressableMaterial(
        child: InkWell(
          onTap: _openVaccinations,
          borderRadius: BorderRadius.circular(14),
          child: _glassCard(
            bgOpacity: 0.06,
            borderOpacity: 0.12,
            borderWidth: 1,
            padding: const EdgeInsets.all(13),
            radius: 14,
            borderTint: accent,
            child: Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: accent.withOpacity(0.16),
                    borderRadius: BorderRadius.circular(11),
                    border: Border.all(
                      color: accent.withOpacity(0.3),
                      width: 1,
                    ),
                  ),
                  child: Icon(Icons.vaccines_rounded, color: accent, size: 18),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        v.vaccineName,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                          letterSpacing: -0.2,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Row(
                        children: [
                          Icon(Icons.schedule_rounded,
                              size: 11, color: Colors.white.withOpacity(0.5)),
                          const SizedBox(width: 3),
                          Flexible(
                            child: Text(
                              relative ?? dateStr,
                              style: TextStyle(
                                color: Colors.white.withOpacity(0.6),
                                fontSize: 11.5,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                if (dueSoon)
                  _pill(
                    text: 'Due Soon',
                    color: accent,
                    icon: Icons.priority_high_rounded,
                    iconSize: 10,
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildActiveMedCard(_MedicationRec m) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 0, 14, 8),
      child: _PressableMaterial(
        child: InkWell(
          onTap: _openMedications,
          borderRadius: BorderRadius.circular(14),
          child: _glassCard(
            bgOpacity: 0.06,
            borderOpacity: 0.12,
            borderWidth: 1,
            padding: const EdgeInsets.all(13),
            radius: 14,
            borderTint: _petAccent,
            child: Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: _petAccent.withOpacity(0.16),
                    borderRadius: BorderRadius.circular(11),
                    border: Border.all(
                      color: _petAccent.withOpacity(0.3),
                      width: 1,
                    ),
                  ),
                  child: Icon(
                      m.isTaper
                          ? Icons.trending_down_rounded
                          : Icons.medication_rounded,
                      color: _petAccent,
                      size: 18),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        m.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                          letterSpacing: -0.2,
                        ),
                      ),
                      if (m.dosageSummary.isNotEmpty) ...[
                        const SizedBox(height: 3),
                        Text(
                          m.dosageSummary,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.6),
                            fontSize: 11.5,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                if (m.isTaper)
                  _pill(
                    text: 'Taper',
                    color: _joviGold,
                    icon: Icons.trending_down_rounded,
                    iconSize: 10,
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // PAST VISITS TAB
  // Stopgap view: recent symptom checks surface here as proto-"visits"
  // until vet partnership data feeds exist.
  // ═══════════════════════════════════════════════════════════════════════

  Widget _buildPastView() {
    if (_selectedPet == null) return _buildNoPetEmptyState();
    if (_symptomChecksLoading && _symptomChecks.isEmpty) {
      return _buildLoadingState();
    }

    final checks = _pastSymptomChecks;
    final petName = _selectedPet!.name;

    return ListView(
      padding: const EdgeInsets.only(bottom: 24),
      children: [
        _comingSoonCard(
          title: 'Vet visit history',
          body:
              "Completed vet visits, diagnoses, and procedure notes will live here once partner clinics can sync records to $petName's profile.",
          icon: Icons.local_hospital_rounded,
          accent: _joviMint,
        ),
        _sectionHeader(
          title: 'Recent symptom checks',
          subtitle:
              checks.isEmpty ? 'No past checks yet' : '${checks.length} saved',
          icon: Icons.psychology_rounded,
          accent: _joviCoral,
          trailing: _jumpLink(
            label: 'New check',
            onTap: _openSymptomChecker,
            accent: _joviCoral,
            icon: Icons.add_rounded,
          ),
        ),
        if (_symptomChecksError != null)
          _errorBanner(
            _symptomChecksError!,
            onRetry: _selectedPet == null
                ? null
                : () => _subscribeSymptomChecks(_selectedPet!.petId),
          )
        else if (checks.isEmpty)
          _inlineEmptyRow(
            message:
                "When you use the Pet Symptom Checker, the conversation and triage result are saved here — so you can share context with your vet.",
            accent: _joviCoral,
          )
        else
          ...checks.map(_buildSymptomCheckHistoryCard),
        const SizedBox(height: 16),
      ],
    );
  }

  Widget _buildSymptomCheckHistoryCard(_SymptomCheckRec sc) {
    final accent =
        sc.redFlagged ? _joviErrorRed : _eventAccentForTier(sc.finalTier);
    final icon =
        sc.redFlagged ? Icons.warning_rounded : _eventIconForTier(sc.finalTier);
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 0, 14, 8),
      child: _PressableMaterial(
        child: InkWell(
          onTap: () => _showSymptomCheckDetail(sc),
          borderRadius: BorderRadius.circular(14),
          child: _glassCard(
            bgOpacity: 0.06,
            borderOpacity: 0.12,
            borderWidth: 1,
            padding: const EdgeInsets.all(13),
            radius: 14,
            borderTint: accent,
            child: Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: accent.withOpacity(0.16),
                    borderRadius: BorderRadius.circular(11),
                    border: Border.all(
                      color: accent.withOpacity(0.3),
                      width: 1,
                    ),
                  ),
                  child: Icon(icon, color: accent, size: 18),
                ),
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
                              sc.summary,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 14,
                                fontWeight: FontWeight.w700,
                                letterSpacing: -0.2,
                              ),
                            ),
                          ),
                          if (sc.redFlagged) ...[
                            const SizedBox(width: 6),
                            _pill(
                              text: 'Flagged',
                              color: _joviErrorRed,
                              icon: Icons.warning_rounded,
                              iconSize: 10,
                            ),
                          ],
                        ],
                      ),
                      const SizedBox(height: 3),
                      Row(
                        children: [
                          Icon(Icons.schedule_rounded,
                              size: 11, color: Colors.white.withOpacity(0.5)),
                          const SizedBox(width: 3),
                          Text(
                            _formatRelativeDate(sc.createdAt),
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.55),
                              fontSize: 11.5,
                              fontWeight: FontWeight.w600,
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
                              _PetCareEvent._humanizeTier(sc.finalTier),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                color: accent.withOpacity(0.9),
                                fontSize: 11.5,
                                fontWeight: FontWeight.w700,
                              ),
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
      ),
    );
  }

  Color _eventAccentForTier(String tier) {
    if (tier == 'emergency') return _joviErrorRed;
    if (tier == 'urgent') return _joviCoral;
    if (tier == 'routine') return _joviGold;
    if (tier == 'selfCare') return _joviMint;
    return Colors.white.withOpacity(0.7);
  }

  IconData _eventIconForTier(String tier) {
    if (tier == 'emergency') return Icons.emergency_rounded;
    if (tier == 'urgent') return Icons.local_hospital_rounded;
    if (tier == 'routine') return Icons.calendar_month_rounded;
    if (tier == 'selfCare') return Icons.home_rounded;
    return Icons.psychology_rounded;
  }

  String _formatRelativeDate(DateTime d) {
    final now = DateTime.now();
    final diff = now.difference(d);
    if (diff.inMinutes < 60) {
      final m = diff.inMinutes;
      return m <= 1 ? 'Just now' : '$m min ago';
    }
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    if (diff.inDays == 1) return 'Yesterday';
    if (diff.inDays < 7) return '${diff.inDays}d ago';
    return DateFormat('MMM d, y').format(d);
  }

  // ═══════════════════════════════════════════════════════════════════════
  // TIMELINE TAB
  // The unified, chronological view. Groups events by month.
  // ═══════════════════════════════════════════════════════════════════════

  Widget _buildTimelineView() {
    if (_selectedPet == null) return _buildNoPetEmptyState();

    // Show loading only if everything is still loading AND empty
    if (_anyLoading && _allEmpty) return _buildLoadingState();

    final grouped = _timelineGroupedByMonth;
    final petName = _selectedPet!.name;

    if (grouped.isEmpty) {
      return ListView(
        padding: const EdgeInsets.only(bottom: 24),
        children: [
          const SizedBox(height: 60),
          Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 72,
                    height: 72,
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.05),
                      shape: BoxShape.circle,
                      border: Border.all(
                        color: Colors.white.withOpacity(0.12),
                        width: 1,
                      ),
                    ),
                    child: Icon(
                      Icons.timeline_rounded,
                      color: Colors.white.withOpacity(0.4),
                      size: 32,
                    ),
                  ),
                  const SizedBox(height: 18),
                  const Text(
                    "Nothing in the timeline yet",
                    style: TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.w800,
                      color: Colors.white,
                      letterSpacing: -0.3,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    "As you log vaccinations, add medications, or run symptom checks, $petName's health history will appear here.",
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 13,
                      color: Colors.white.withOpacity(0.55),
                      fontWeight: FontWeight.w500,
                      height: 1.35,
                    ),
                  ),
                  const SizedBox(height: 22),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    alignment: WrapAlignment.center,
                    children: [
                      _jumpLink(
                        label: 'Vaccinations',
                        onTap: _openVaccinations,
                        icon: Icons.vaccines_rounded,
                        accent: _joviMint,
                      ),
                      _jumpLink(
                        label: 'Medications',
                        onTap: _openMedications,
                        icon: Icons.medication_rounded,
                        accent: _petAccent,
                      ),
                      _jumpLink(
                        label: 'Symptom Checker',
                        onTap: _openSymptomChecker,
                        icon: Icons.psychology_rounded,
                        accent: _joviCoral,
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      );
    }

    // Group-aware rendering. Each month becomes its own section.
    final widgets = <Widget>[];

    // Error banners at top if any subscription broke
    if (_vaccinationsError != null) {
      widgets.add(_errorBanner(
        'Vaccinations: ${_vaccinationsError!}',
        onRetry: _selectedPet == null
            ? null
            : () => _subscribeVaccinations(_selectedPet!.petId),
      ));
    }
    if (_medicationsError != null) {
      widgets.add(_errorBanner(
        'Medications: ${_medicationsError!}',
        onRetry: _selectedPet == null
            ? null
            : () => _subscribeMedications(_selectedPet!.petId),
      ));
    }
    if (_symptomChecksError != null) {
      widgets.add(_errorBanner(
        'Symptom checks: ${_symptomChecksError!}',
        onRetry: _selectedPet == null
            ? null
            : () => _subscribeSymptomChecks(_selectedPet!.petId),
      ));
    }
    if (_vetWeightsError != null) {
      widgets.add(_errorBanner(
        'Weight history: ${_vetWeightsError!}',
        onRetry: _selectedPet == null
            ? null
            : () => _subscribeVetWeights(_selectedPet!.petId),
      ));
    }

    for (var g = 0; g < grouped.length; g++) {
      final entry = grouped[g];
      widgets.add(_buildTimelineMonthHeader(entry.key, entry.value.length));
      for (var i = 0; i < entry.value.length; i++) {
        final isLast = g == grouped.length - 1 && i == entry.value.length - 1;
        widgets.add(_buildTimelineEventRow(entry.value[i], isLast: isLast));
      }
    }

    widgets.add(const SizedBox(height: 16));

    return ListView(
      padding: const EdgeInsets.only(bottom: 24),
      children: widgets,
    );
  }

  Widget _buildTimelineMonthHeader(String monthLabel, int count) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 16, 14, 8),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
            decoration: BoxDecoration(
              color: _petAccent.withOpacity(0.15),
              borderRadius: BorderRadius.circular(11),
              border: Border.all(
                color: _petAccent.withOpacity(0.3),
                width: 0.8,
              ),
            ),
            child: Text(
              monthLabel,
              style: TextStyle(
                color: _petAccent,
                fontSize: 12,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.1,
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Container(
              height: 1,
              color: Colors.white.withOpacity(0.08),
            ),
          ),
          const SizedBox(width: 8),
          Text(
            '$count event${count == 1 ? '' : 's'}',
            style: TextStyle(
              color: Colors.white.withOpacity(0.4),
              fontSize: 11,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.2,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTimelineEventRow(_PetCareEvent event, {bool isLast = false}) {
    final accent = _eventKindAccent(event.kind);
    final icon = _eventKindIcon(event.kind);

    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 0, 14, 0),
      child: IntrinsicHeight(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Left rail: icon + vertical connector line
            SizedBox(
              width: 40,
              child: Column(
                children: [
                  Container(
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      color: accent.withOpacity(0.16),
                      borderRadius: BorderRadius.circular(11),
                      border: Border.all(
                        color: accent.withOpacity(0.4),
                        width: 1,
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: accent.withOpacity(0.25),
                          blurRadius: 12,
                          offset: const Offset(0, 3),
                        ),
                      ],
                    ),
                    child: Icon(icon, color: accent, size: 17),
                  ),
                  if (!isLast)
                    Expanded(
                      child: Container(
                        width: 2,
                        margin: const EdgeInsets.symmetric(vertical: 2),
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            begin: Alignment.topCenter,
                            end: Alignment.bottomCenter,
                            colors: [
                              accent.withOpacity(0.3),
                              Colors.white.withOpacity(0.08),
                            ],
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            // Right: event card
            Expanded(
              child: Padding(
                padding: const EdgeInsets.only(bottom: 12, top: 2),
                child: _PressableMaterial(
                  child: InkWell(
                    onTap: () => _showTimelineEventDetail(event),
                    borderRadius: BorderRadius.circular(14),
                    child: _glassCard(
                      bgOpacity: 0.06,
                      borderOpacity: 0.12,
                      borderWidth: 1,
                      padding: const EdgeInsets.all(13),
                      radius: 14,
                      borderTint: accent,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Row(
                            children: [
                              Flexible(
                                child: Text(
                                  event.title,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontSize: 14,
                                    fontWeight: FontWeight.w800,
                                    letterSpacing: -0.2,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 8),
                              _pill(
                                text: _shortDate(event.when),
                                color: accent,
                                icon: Icons.calendar_today_rounded,
                                iconSize: 10,
                              ),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Row(
                            children: [
                              Icon(Icons.label_outline_rounded,
                                  size: 11, color: accent.withOpacity(0.9)),
                              const SizedBox(width: 3),
                              Text(
                                _eventKindLabel(event.kind),
                                style: TextStyle(
                                  color: accent.withOpacity(0.95),
                                  fontSize: 11.5,
                                  fontWeight: FontWeight.w700,
                                  letterSpacing: -0.1,
                                ),
                              ),
                              if (event.subtitle != null) ...[
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
                                    event.subtitle!,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: TextStyle(
                                      color: Colors.white.withOpacity(0.6),
                                      fontSize: 11.5,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ),
                              ],
                            ],
                          ),
                          if (event.details.isNotEmpty &&
                              event.kind == _PetCareEventKind.vaccination) ...[
                            const SizedBox(height: 7),
                            ..._topDetailRows(event.details, maxRows: 2),
                          ],
                          if (event.body != null && event.body!.isNotEmpty) ...[
                            const SizedBox(height: 7),
                            Text(
                              event.body!,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                color: Colors.white.withOpacity(0.65),
                                fontSize: 12,
                                fontWeight: FontWeight.w500,
                                height: 1.4,
                                fontStyle: FontStyle.italic,
                              ),
                            ),
                          ],
                        ],
                      ),
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

  List<Widget> _topDetailRows(Map<String, String> details,
      {required int maxRows}) {
    final entries = details.entries.take(maxRows).toList();
    return entries.map((e) {
      return Padding(
        padding: const EdgeInsets.only(top: 2),
        child: Row(
          children: [
            SizedBox(
              width: 82,
              child: Text(
                e.key,
                style: TextStyle(
                  color: Colors.white.withOpacity(0.45),
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.1,
                ),
              ),
            ),
            Expanded(
              child: Text(
                e.value,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
      );
    }).toList();
  }

  String _shortDate(DateTime d) {
    final now = DateTime.now();
    if (d.year == now.year) {
      return DateFormat('MMM d').format(d);
    }
    return DateFormat('MMM d, y').format(d);
  }

  // ═══════════════════════════════════════════════════════════════════════
  // TIMELINE EVENT DETAIL SHEET
  // Dispatches by event kind to specialized detail views.
  // ═══════════════════════════════════════════════════════════════════════

  void _showTimelineEventDetail(_PetCareEvent event) {
    HapticFeedback.lightImpact();
    if (event.symptomCheck != null) {
      _showSymptomCheckDetail(event.symptomCheck!);
      return;
    }
    if (event.vaccination != null) {
      _showVaccinationDetail(event);
      return;
    }
    if (event.medication != null) {
      _showMedicationDetail(event);
      return;
    }
    _showGenericEventDetail(event);
  }

  // ─────────────────────────────────────────────────────────────────────
  // SYMPTOM CHECK DETAIL (shared with Past-visits tap handler)
  // ─────────────────────────────────────────────────────────────────────

  Future<void> _showSymptomCheckDetail(_SymptomCheckRec sc) async {
    HapticFeedback.lightImpact();
    final user = FirebaseAuth.instance.currentUser;
    final pet = _selectedPet;
    List<Map<String, dynamic>> transcript = [];
    bool loadError = false;

    if (user != null && pet != null) {
      try {
        final doc = await FirebaseFirestore.instance
            .collection('users')
            .doc(user.uid)
            .collection('pets')
            .doc(pet.petId)
            .collection('symptom_checks')
            .doc(sc.id)
            .get();
        final data = doc.data();
        final raw = data?['transcript'];
        if (raw is List) {
          for (final item in raw) {
            if (item is Map) {
              transcript.add(Map<String, dynamic>.from(item));
            }
          }
        }
      } catch (e) {
        debugPrint('PetRecords: failed to load transcript: $e');
        loadError = true;
      }
    }
    if (!mounted) return;

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
                  _sheetDragHandle(),
                  _sheetHeader(
                    accent: sc.redFlagged
                        ? _joviErrorRed
                        : _eventAccentForTier(sc.finalTier),
                    icon: sc.redFlagged
                        ? Icons.warning_rounded
                        : _eventIconForTier(sc.finalTier),
                    title: sc.summary,
                    subtitle:
                        '${DateFormat('MMM d, y · h:mm a').format(sc.createdAt)} · ${_PetCareEvent._humanizeTier(sc.finalTier)}',
                    onClose: () => Navigator.pop(ctx),
                  ),
                  Expanded(
                    child: loadError
                        ? _sheetErrorBody("Couldn't load the full transcript.")
                        : transcript.isEmpty
                            ? _sheetEmptyBody(
                                'No transcript was stored for this check.')
                            : ListView.builder(
                                controller: scrollCtrl,
                                padding:
                                    const EdgeInsets.fromLTRB(14, 4, 14, 14),
                                itemCount: transcript.length,
                                itemBuilder: (ctx, i) =>
                                    _buildTranscriptBubble(transcript[i]),
                              ),
                  ),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
                    child: _primaryButton(
                      label: 'Open Symptom Checker',
                      icon: Icons.psychology_rounded,
                      onTap: () {
                        Navigator.pop(ctx);
                        _openSymptomChecker();
                      },
                      accent: _joviCoral,
                      accentDark: _joviCoralDark,
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

  /// Minimal transcript bubble for the history detail sheet. We don't import
  /// the full _ChatMsg model from the Symptom Checker widget — we just read
  /// text + isUser + timestamp from the stored JSON.
  Widget _buildTranscriptBubble(Map<String, dynamic> msg) {
    final text = (msg['text'] as String?) ?? '';
    final isUser = msg['isUser'] == true;
    final isSystemNotice = msg['isSystemNotice'] == true;
    final tsRaw = msg['timestamp'];
    DateTime? ts;
    if (tsRaw is String) ts = DateTime.tryParse(tsRaw);
    if (tsRaw is int) {
      ts = DateTime.fromMillisecondsSinceEpoch(tsRaw);
    }
    if (tsRaw is Timestamp) ts = tsRaw.toDate();

    if (isSystemNotice) {
      return Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
        decoration: BoxDecoration(
          color: _joviGold.withOpacity(0.07),
          borderRadius: BorderRadius.circular(11),
          border: Border.all(
            color: _joviGold.withOpacity(0.22),
            width: 0.8,
          ),
        ),
        child: Row(
          children: [
            const Icon(Icons.shield_outlined, color: _joviGoldDark, size: 14),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                text,
                style: TextStyle(
                  color: Colors.white.withOpacity(0.72),
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                  height: 1.35,
                  fontStyle: FontStyle.italic,
                ),
              ),
            ),
          ],
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        mainAxisAlignment:
            isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          if (!isUser) ...[
            Container(
              width: 30,
              height: 30,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [_petAccent, _petAccentDark],
                ),
                shape: BoxShape.circle,
              ),
              child:
                  const Icon(Icons.pets_rounded, color: Colors.white, size: 14),
            ),
            const SizedBox(width: 8),
          ],
          Flexible(
            child: Container(
              constraints: BoxConstraints(
                maxWidth: MediaQuery.of(context).size.width * 0.72,
              ),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                gradient: isUser
                    ? const LinearGradient(
                        colors: [_joviCoral, _joviCoralDark],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      )
                    : null,
                color: isUser ? null : Colors.white.withOpacity(0.08),
                borderRadius: BorderRadius.only(
                  topLeft: const Radius.circular(18),
                  topRight: const Radius.circular(18),
                  bottomLeft: isUser
                      ? const Radius.circular(18)
                      : const Radius.circular(4),
                  bottomRight: isUser
                      ? const Radius.circular(4)
                      : const Radius.circular(18),
                ),
                border: isUser
                    ? null
                    : Border.all(
                        color: Colors.white.withOpacity(0.12),
                        width: 0.8,
                      ),
              ),
              child: Column(
                crossAxisAlignment:
                    isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  SelectableText(
                    text,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 14.5,
                      fontWeight: FontWeight.w500,
                      height: 1.45,
                      letterSpacing: -0.1,
                    ),
                  ),
                  if (ts != null) ...[
                    const SizedBox(height: 4),
                    Text(
                      DateFormat.jm().format(ts),
                      style: TextStyle(
                        color: isUser
                            ? Colors.white.withOpacity(0.68)
                            : Colors.white.withOpacity(0.35),
                        fontSize: 10,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ─────────────────────────────────────────────────────────────────────
  // VACCINATION DETAIL
  // ─────────────────────────────────────────────────────────────────────

  void _showVaccinationDetail(_PetCareEvent event) {
    final v = event.vaccination!;
    HapticFeedback.lightImpact();
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => DraggableScrollableSheet(
        initialChildSize: 0.7,
        maxChildSize: 0.92,
        minChildSize: 0.4,
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
                  _sheetDragHandle(),
                  _sheetHeader(
                    accent: _joviMint,
                    icon: Icons.vaccines_rounded,
                    title: v.vaccineName,
                    subtitle:
                        'Administered ${DateFormat('MMM d, y').format(v.administeredDate)}',
                    onClose: () => Navigator.pop(ctx),
                  ),
                  Expanded(
                    child: SingleChildScrollView(
                      controller: scrollCtrl,
                      padding: const EdgeInsets.fromLTRB(20, 4, 20, 20),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Wrap(
                            spacing: 6,
                            runSpacing: 6,
                            children: [
                              if (v.isExpired)
                                _pill(
                                  text: 'Expired',
                                  color: _joviErrorRed,
                                  icon: Icons.warning_rounded,
                                  iconSize: 10,
                                )
                              else if (v.isDueSoon)
                                _pill(
                                  text: 'Due Soon',
                                  color: _joviGold,
                                  icon: Icons.priority_high_rounded,
                                  iconSize: 10,
                                )
                              else if (v.expirationDate != null)
                                _pill(
                                  text: 'Current',
                                  color: _joviMint,
                                  icon: Icons.check_circle_rounded,
                                  iconSize: 10,
                                ),
                              if (v.vaccineType != 'custom')
                                _pill(
                                  text: v.vaccineType,
                                  color: _joviMintDark,
                                ),
                            ],
                          ),
                          const SizedBox(height: 16),
                          _detailSection(
                            rows: [
                              _detailRow(
                                'Administered',
                                DateFormat('MMM d, y')
                                    .format(v.administeredDate),
                              ),
                              if (v.expirationDate != null)
                                _detailRow(
                                  'Next due',
                                  DateFormat('MMM d, y')
                                      .format(v.expirationDate!),
                                ),
                              if (v.clinicName != null &&
                                  v.clinicName!.isNotEmpty)
                                _detailRow('Clinic', v.clinicName!),
                              if (v.administeredBy != null &&
                                  v.administeredBy!.isNotEmpty)
                                _detailRow(
                                    'Administered by', v.administeredBy!),
                              if (v.batchNumber != null &&
                                  v.batchNumber!.isNotEmpty)
                                _detailRow('Batch number', v.batchNumber!),
                            ],
                          ),
                          if (v.notes != null && v.notes!.isNotEmpty) ...[
                            const SizedBox(height: 14),
                            _notesBlock(v.notes!),
                          ],
                          const SizedBox(height: 22),
                          _primaryButton(
                            label: 'Open Vaccinations',
                            icon: Icons.vaccines_rounded,
                            onTap: () {
                              Navigator.pop(ctx);
                              _openVaccinations();
                            },
                            accent: _joviMint,
                            accentDark: _joviMintDark,
                          ),
                        ],
                      ),
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

  // ─────────────────────────────────────────────────────────────────────
  // MEDICATION DETAIL
  // ─────────────────────────────────────────────────────────────────────

  void _showMedicationDetail(_PetCareEvent event) {
    final m = event.medication!;
    final isStart = event.kind == _PetCareEventKind.medicationStart ||
        event.kind == _PetCareEventKind.medicationTaper;
    HapticFeedback.lightImpact();
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => DraggableScrollableSheet(
        initialChildSize: 0.7,
        maxChildSize: 0.92,
        minChildSize: 0.4,
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
                  _sheetDragHandle(),
                  _sheetHeader(
                    accent: _eventKindAccent(event.kind),
                    icon: _eventKindIcon(event.kind),
                    title: m.name,
                    subtitle: isStart
                        ? (m.isTaper
                            ? 'Taper started ${DateFormat('MMM d, y').format(m.startDate)}'
                            : 'Started ${DateFormat('MMM d, y').format(m.startDate)}')
                        : 'Stopped ${DateFormat('MMM d, y').format(m.stopDate ?? m.startDate)}',
                    onClose: () => Navigator.pop(ctx),
                  ),
                  Expanded(
                    child: SingleChildScrollView(
                      controller: scrollCtrl,
                      padding: const EdgeInsets.fromLTRB(20, 4, 20, 20),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Wrap(
                            spacing: 6,
                            runSpacing: 6,
                            children: [
                              _pill(
                                text: m.isActive ? 'Active' : 'Ended',
                                color: m.isActive
                                    ? _joviMint
                                    : Colors.white.withOpacity(0.6),
                                icon: m.isActive
                                    ? Icons.check_circle_rounded
                                    : Icons.stop_circle_rounded,
                                iconSize: 10,
                              ),
                              if (m.isTaper)
                                _pill(
                                  text: 'Taper',
                                  color: _joviGold,
                                  icon: Icons.trending_down_rounded,
                                  iconSize: 10,
                                ),
                              if (m.remindersEnabled && m.isActive)
                                _pill(
                                  text: 'Reminders On',
                                  color: _petAccent,
                                  icon: Icons.notifications_rounded,
                                  iconSize: 10,
                                ),
                            ],
                          ),
                          const SizedBox(height: 16),
                          _detailSection(
                            rows: [
                              if (m.strength.isNotEmpty)
                                _detailRow('Strength', m.strength),
                              if (m.dosage.isNotEmpty)
                                _detailRow('Dosage', m.dosage),
                              if (m.condition != null &&
                                  m.condition!.isNotEmpty)
                                _detailRow('For', m.condition!),
                              if (m.prescribedBy != null &&
                                  m.prescribedBy!.isNotEmpty)
                                _detailRow('Prescribed by', m.prescribedBy!),
                              if (m.pharmacy != null && m.pharmacy!.isNotEmpty)
                                _detailRow('Pharmacy', m.pharmacy!),
                              _detailRow(
                                'Start date',
                                DateFormat('MMM d, y').format(m.startDate),
                              ),
                              if (m.stopDate != null)
                                _detailRow(
                                  'Stop date',
                                  DateFormat('MMM d, y').format(m.stopDate!),
                                ),
                            ],
                          ),
                          if (m.notes != null && m.notes!.isNotEmpty) ...[
                            const SizedBox(height: 14),
                            _notesBlock(m.notes!),
                          ],
                          const SizedBox(height: 22),
                          _primaryButton(
                            label: 'Open Medications',
                            icon: Icons.medication_rounded,
                            onTap: () {
                              Navigator.pop(ctx);
                              _openMedications();
                            },
                          ),
                        ],
                      ),
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

  // ─────────────────────────────────────────────────────────────────────
  // GENERIC EVENT DETAIL (fallback for future event kinds like vetVisit)
  // ─────────────────────────────────────────────────────────────────────

  void _showGenericEventDetail(_PetCareEvent event) {
    final accent = _eventKindAccent(event.kind);
    HapticFeedback.lightImpact();
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => DraggableScrollableSheet(
        initialChildSize: 0.6,
        maxChildSize: 0.92,
        minChildSize: 0.4,
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
                  _sheetDragHandle(),
                  _sheetHeader(
                    accent: accent,
                    icon: _eventKindIcon(event.kind),
                    title: event.title,
                    subtitle:
                        '${_eventKindLabel(event.kind)} · ${DateFormat('MMM d, y').format(event.when)}',
                    onClose: () => Navigator.pop(ctx),
                  ),
                  Expanded(
                    child: SingleChildScrollView(
                      controller: scrollCtrl,
                      padding: const EdgeInsets.fromLTRB(20, 4, 20, 20),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          if (event.details.isNotEmpty)
                            _detailSection(
                              rows: event.details.entries
                                  .map((e) => _detailRow(e.key, e.value))
                                  .toList(),
                            ),
                          if (event.body != null && event.body!.isNotEmpty) ...[
                            const SizedBox(height: 14),
                            _notesBlock(event.body!),
                          ],
                        ],
                      ),
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

  // ─────────────────────────────────────────────────────────────────────
  // SHEET PRIMITIVES (drag handle, header, empty/error bodies, detail rows)
  // ─────────────────────────────────────────────────────────────────────

  Widget _sheetDragHandle() {
    return Container(
      margin: const EdgeInsets.only(top: 10),
      width: 38,
      height: 4,
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.2),
        borderRadius: BorderRadius.circular(2),
      ),
    );
  }

  Widget _sheetHeader({
    required Color accent,
    required IconData icon,
    required String title,
    required String subtitle,
    required VoidCallback onClose,
  }) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 12, 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: accent.withOpacity(0.16),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: accent.withOpacity(0.4),
                width: 1,
              ),
            ),
            child: Icon(icon, color: accent, size: 22),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  title,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.5,
                    height: 1.2,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  subtitle,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.55),
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
          _PressableMaterial(
            child: InkWell(
              onTap: onClose,
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

  Widget _sheetEmptyBody(String message) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Text(
          message,
          textAlign: TextAlign.center,
          style: TextStyle(
            color: Colors.white.withOpacity(0.55),
            fontSize: 13,
            fontWeight: FontWeight.w500,
          ),
        ),
      ),
    );
  }

  Widget _sheetErrorBody(String message) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_off_rounded, color: _joviErrorRed, size: 32),
            const SizedBox(height: 10),
            Text(
              message,
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white.withOpacity(0.7),
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _detailSection({required List<Widget> rows}) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: Colors.white.withOpacity(0.1),
          width: 0.8,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: rows,
      ),
    );
  }

  Widget _detailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 110,
            child: Text(
              label,
              style: TextStyle(
                color: Colors.white.withOpacity(0.5),
                fontSize: 12,
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
                fontSize: 13.5,
                fontWeight: FontWeight.w600,
                height: 1.3,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _notesBlock(String notes) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: _joviGold.withOpacity(0.07),
        borderRadius: BorderRadius.circular(11),
        border: Border.all(
          color: _joviGold.withOpacity(0.22),
          width: 0.8,
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.sticky_note_2_outlined,
              color: _joviGoldDark, size: 14),
          const SizedBox(width: 8),
          Expanded(
            child: SelectableText(
              notes,
              style: TextStyle(
                color: Colors.white.withOpacity(0.85),
                fontSize: 13,
                fontWeight: FontWeight.w500,
                height: 1.4,
              ),
            ),
          ),
        ],
      ),
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

// ─── Pet Accent System (matches Pet Symptom Checker / Pet Meds / Vaccinations)
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

enum _Tab { upcoming, past, timeline }

/// Kinds of care events the timeline can surface. Today we have three real
/// sources; vet partnerships will add more (vetVisit, labResult, etc.)
/// without needing to change the timeline rendering logic — just add a
/// new kind + icon + accent mapping.
enum _PetCareEventKind {
  vaccination,
  medicationStart,
  medicationTaper,
  medicationStop,
  symptomCheck,
  redFlagAlert, // symptom check that tripped a red flag
  vetWeight, // weight logged by a vet provider (normal range)
  vetWeightAlert, // vet-logged weight that tripped the breed threshold
  vetVisit, // placeholder — no data source yet
  labResult, // placeholder — no data source yet
}

String _eventKindLabel(_PetCareEventKind k) {
  if (k == _PetCareEventKind.vaccination) return 'Vaccination';
  if (k == _PetCareEventKind.medicationStart) return 'Medication started';
  if (k == _PetCareEventKind.medicationTaper) return 'Medication tapered';
  if (k == _PetCareEventKind.medicationStop) return 'Medication stopped';
  if (k == _PetCareEventKind.symptomCheck) return 'Symptom check';
  if (k == _PetCareEventKind.redFlagAlert) return 'Emergency flag';
  if (k == _PetCareEventKind.vetWeight) return 'Weight recorded';
  if (k == _PetCareEventKind.vetWeightAlert) return 'Weight above range';
  if (k == _PetCareEventKind.vetVisit) return 'Vet visit';
  if (k == _PetCareEventKind.labResult) return 'Lab result';
  return 'Event';
}

IconData _eventKindIcon(_PetCareEventKind k) {
  if (k == _PetCareEventKind.vaccination) return Icons.vaccines_rounded;
  if (k == _PetCareEventKind.medicationStart) {
    return Icons.medication_rounded;
  }
  if (k == _PetCareEventKind.medicationTaper) {
    return Icons.trending_down_rounded;
  }
  if (k == _PetCareEventKind.medicationStop) {
    return Icons.stop_circle_rounded;
  }
  if (k == _PetCareEventKind.symptomCheck) return Icons.psychology_rounded;
  if (k == _PetCareEventKind.redFlagAlert) return Icons.warning_rounded;
  if (k == _PetCareEventKind.vetWeight) return Icons.monitor_weight_rounded;
  if (k == _PetCareEventKind.vetWeightAlert) {
    return Icons.monitor_weight_rounded;
  }
  if (k == _PetCareEventKind.vetVisit) return Icons.local_hospital_rounded;
  if (k == _PetCareEventKind.labResult) return Icons.biotech_rounded;
  return Icons.event_note_rounded;
}

Color _eventKindAccent(_PetCareEventKind k) {
  if (k == _PetCareEventKind.vaccination) return _joviMint;
  if (k == _PetCareEventKind.medicationStart) return _petAccent;
  if (k == _PetCareEventKind.medicationTaper) return _joviGold;
  if (k == _PetCareEventKind.medicationStop) {
    return Color.fromARGB(255, 180, 180, 200);
  }
  if (k == _PetCareEventKind.symptomCheck) return _joviCoral;
  if (k == _PetCareEventKind.redFlagAlert) return _joviErrorRed;
  if (k == _PetCareEventKind.vetWeight) return _joviMint;
  if (k == _PetCareEventKind.vetWeightAlert) return _joviGold;
  if (k == _PetCareEventKind.vetVisit) return _joviMint;
  if (k == _PetCareEventKind.labResult) return _joviGold;
  return Colors.white;
}

// ═══════════════════════════════════════════════════════════════════════════
// PET MODEL (matches schema in Pet Symptom Checker / Pet Meds / Vaccinations)
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

  int? get ageYears {
    if (dateOfBirth == null) return null;
    final now = DateTime.now();
    int years = now.year - dateOfBirth!.year;
    if (now.month < dateOfBirth!.month ||
        (now.month == dateOfBirth!.month && now.day < dateOfBirth!.day)) {
      years--;
    }
    return years < 0 ? 0 : years;
  }

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
    );
  }

  /// Parse from legacy JSON map (onboarding/update write pattern).
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
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// SOURCE DATA MODELS — minimal read-only views of the three subcollections
// matching the write schemas in their respective widgets. Do NOT change
// field names without also updating the writers.
// ═══════════════════════════════════════════════════════════════════════════

/// Vaccination record (read view, written by jovi_pet_vaccinations.dart).
class _VaccinationRec {
  final String vaccinationId;
  final String vaccineName;
  final String vaccineType;
  final PetType species;
  final DateTime administeredDate;
  final DateTime? expirationDate;
  final String? administeredBy;
  final String? clinicName;
  final String? batchNumber;
  final String? notes;

  const _VaccinationRec({
    required this.vaccinationId,
    required this.vaccineName,
    this.vaccineType = 'custom',
    this.species = PetType.other,
    required this.administeredDate,
    this.expirationDate,
    this.administeredBy,
    this.clinicName,
    this.batchNumber,
    this.notes,
  });

  /// True if the vaccine has an expiration date in the future (or none set).
  bool get isActive {
    if (expirationDate == null) return true;
    return expirationDate!.isAfter(DateTime.now());
  }

  /// True if the vaccine has expired as of now.
  bool get isExpired {
    if (expirationDate == null) return false;
    return expirationDate!.isBefore(DateTime.now());
  }

  /// True if expiration is within 60 days.
  bool get isDueSoon {
    if (expirationDate == null) return false;
    final now = DateTime.now();
    final soon = now.add(const Duration(days: 60));
    return expirationDate!.isAfter(now) && expirationDate!.isBefore(soon);
  }

  factory _VaccinationRec.fromFirestore(String docId, Map<String, dynamic> m) {
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

    final admin = parseTs(m['administeredDate']);
    return _VaccinationRec(
      vaccinationId: (m['vaccinationId'] as String?) ?? docId,
      vaccineName: (m['vaccineName'] as String?)?.trim().isNotEmpty == true
          ? (m['vaccineName'] as String).trim()
          : 'Vaccine',
      vaccineType: (m['vaccineType'] as String?) ?? 'custom',
      species: _petTypeParse(m['species'] as String?),
      administeredDate: admin ?? DateTime.now(),
      expirationDate: parseTs(m['expirationDate']),
      administeredBy: (m['administeredBy'] as String?)?.trim(),
      clinicName: (m['clinicName'] as String?)?.trim(),
      batchNumber: (m['batchNumber'] as String?)?.trim(),
      notes: (m['notes'] as String?)?.trim(),
    );
  }
}

/// Medication record (read view, written by jovi_pet_medications.dart).
/// We only need the fields that matter for timeline display.
class _MedicationRec {
  final String id;
  final String name;
  final String strength;
  final String dosage;
  final String? condition;
  final String? prescribedBy;
  final String? pharmacy;
  final DateTime startDate;
  final DateTime? stopDate;
  final bool isTaper;
  final bool remindersEnabled;
  final String? notes;

  const _MedicationRec({
    required this.id,
    required this.name,
    this.strength = '',
    this.dosage = '',
    this.condition,
    this.prescribedBy,
    this.pharmacy,
    required this.startDate,
    this.stopDate,
    this.isTaper = false,
    this.remindersEnabled = true,
    this.notes,
  });

  bool get isActive {
    final now = DateTime.now();
    if (now.isBefore(startDate)) return false;
    if (stopDate != null && now.isAfter(stopDate!)) return false;
    return true;
  }

  /// Short display summary for the upcoming "Active medications" section.
  String get dosageSummary {
    final parts = <String>[];
    if (strength.isNotEmpty) parts.add(strength);
    if (dosage.isNotEmpty) parts.add(dosage);
    return parts.join(' · ');
  }

  factory _MedicationRec.fromFirestore(String docId, Map<String, dynamic> m) {
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

    return _MedicationRec(
      id: (m['id'] as String?) ?? docId,
      name: (m['name'] as String?)?.trim().isNotEmpty == true
          ? (m['name'] as String).trim()
          : 'Medication',
      strength: (m['strength'] as String?)?.trim() ?? '',
      dosage: (m['dosage'] as String?)?.trim() ?? '',
      condition: (m['condition'] as String?)?.trim(),
      prescribedBy: (m['prescribedBy'] as String?)?.trim(),
      pharmacy: (m['pharmacy'] as String?)?.trim(),
      startDate: parseTs(m['startDate']) ?? DateTime.now(),
      stopDate: parseTs(m['stopDate']),
      isTaper: m['isTaper'] == true,
      remindersEnabled: m['remindersEnabled'] != false,
      notes: (m['notes'] as String?)?.trim(),
    );
  }
}

/// Symptom check record (read view, written by jovi_pet_symptom_checker.dart).
class _SymptomCheckRec {
  final String id;
  final DateTime createdAt;
  final String summary;
  final String finalTier; // emergency|urgent|routine|selfCare|unknown
  final int messageCount;
  final bool redFlagged;
  final String? redFlagReason;

  const _SymptomCheckRec({
    required this.id,
    required this.createdAt,
    required this.summary,
    required this.finalTier,
    required this.messageCount,
    required this.redFlagged,
    this.redFlagReason,
  });

  factory _SymptomCheckRec.fromFirestore(String docId, Map<String, dynamic> m) {
    DateTime parseTs(dynamic v) {
      if (v is Timestamp) return v.toDate();
      if (v is String) {
        return DateTime.tryParse(v) ?? DateTime.now();
      }
      return DateTime.now();
    }

    return _SymptomCheckRec(
      id: docId,
      createdAt: parseTs(m['createdAt']),
      summary: (m['summary'] as String?)?.trim() ?? '(Untitled check)',
      finalTier: (m['finalTier'] as String?) ?? 'unknown',
      messageCount: (m['messageCount'] as num?)?.toInt() ?? 0,
      redFlagged: m['redFlagged'] == true,
      redFlagReason: (m['redFlagReason'] as String?)?.trim(),
    );
  }
}

/// Vet-recorded weight log (read view). Written by the admin app at:
///   users/{uid}/pets/{petId}/vet_weight_logs/{logId}
/// Same schema Weight Alerts widget reads.
class _VetWeightRec {
  final String id;
  final double weightLbs;
  final DateTime recordedAt;
  final String? providerName;
  final String? clinicName;
  final String source; // 'vet_visit', 'admin_sync', etc.
  final double? bodyConditionScore;
  final String? notes;
  final bool flaggedAboveRange; // matched against optional alert doc

  const _VetWeightRec({
    required this.id,
    required this.weightLbs,
    required this.recordedAt,
    this.providerName,
    this.clinicName,
    this.source = 'vet_visit',
    this.bodyConditionScore,
    this.notes,
    this.flaggedAboveRange = false,
  });

  factory _VetWeightRec.fromFirestore(String docId, Map<String, dynamic> m) {
    DateTime parseTs(dynamic v) {
      if (v is Timestamp) return v.toDate();
      if (v is String) {
        return DateTime.tryParse(v) ?? DateTime.now();
      }
      return DateTime.now();
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

    return _VetWeightRec(
      id: docId,
      weightLbs: asDouble(m['weightLbs'] ?? m['weight']),
      recordedAt: parseTs(m['recordedAt'] ?? m['date']),
      providerName: (m['providerName'] as String?)?.trim(),
      clinicName: (m['clinicName'] as String?)?.trim(),
      source: (m['source'] as String?) ?? 'vet_visit',
      bodyConditionScore: asDoubleNullable(m['bodyConditionScore']),
      notes: (m['notes'] as String?)?.trim(),
    );
  }

  /// Return a copy with the flaggedAboveRange marker set. Used after
  /// joining with the weight_alerts collection.
  _VetWeightRec withFlag(bool flagged) {
    return _VetWeightRec(
      id: id,
      weightLbs: weightLbs,
      recordedAt: recordedAt,
      providerName: providerName,
      clinicName: clinicName,
      source: source,
      bodyConditionScore: bodyConditionScore,
      notes: notes,
      flaggedAboveRange: flagged,
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// CARE EVENT (union type for the unified timeline)
// Each event wraps a source record + a kind + a timestamp for sorting.
// ═══════════════════════════════════════════════════════════════════════════

class _PetCareEvent {
  final _PetCareEventKind kind;
  final DateTime when;
  final String title;
  final String? subtitle;
  final String? body;
  final Map<String, String> details; // label → value pairs for expanded view

  // Source references for deep-linking / detail views
  final _VaccinationRec? vaccination;
  final _MedicationRec? medication;
  final _SymptomCheckRec? symptomCheck;
  final _VetWeightRec? vetWeight;

  const _PetCareEvent({
    required this.kind,
    required this.when,
    required this.title,
    this.subtitle,
    this.body,
    this.details = const {},
    this.vaccination,
    this.medication,
    this.symptomCheck,
    this.vetWeight,
  });

  /// Build an event from a vaccination.
  factory _PetCareEvent.fromVaccination(_VaccinationRec v) {
    final details = <String, String>{};
    if (v.clinicName != null && v.clinicName!.isNotEmpty) {
      details['Clinic'] = v.clinicName!;
    }
    if (v.administeredBy != null && v.administeredBy!.isNotEmpty) {
      details['Administered by'] = v.administeredBy!;
    }
    if (v.batchNumber != null && v.batchNumber!.isNotEmpty) {
      details['Batch'] = v.batchNumber!;
    }
    if (v.expirationDate != null) {
      details['Next due'] = DateFormat('MMM d, y').format(v.expirationDate!);
    }
    return _PetCareEvent(
      kind: _PetCareEventKind.vaccination,
      when: v.administeredDate,
      title: v.vaccineName,
      subtitle: v.clinicName ?? v.administeredBy,
      body: v.notes,
      details: details,
      vaccination: v,
    );
  }

  /// Build an event for when a medication was started.
  factory _PetCareEvent.fromMedicationStart(_MedicationRec m) {
    final details = <String, String>{};
    if (m.strength.isNotEmpty) details['Strength'] = m.strength;
    if (m.dosage.isNotEmpty) details['Dosage'] = m.dosage;
    if (m.condition != null && m.condition!.isNotEmpty) {
      details['For'] = m.condition!;
    }
    if (m.prescribedBy != null && m.prescribedBy!.isNotEmpty) {
      details['Prescribed by'] = m.prescribedBy!;
    }
    if (m.pharmacy != null && m.pharmacy!.isNotEmpty) {
      details['Pharmacy'] = m.pharmacy!;
    }
    return _PetCareEvent(
      kind: m.isTaper
          ? _PetCareEventKind.medicationTaper
          : _PetCareEventKind.medicationStart,
      when: m.startDate,
      title: m.name,
      subtitle: m.condition,
      body: m.notes,
      details: details,
      medication: m,
    );
  }

  /// Build an event for when a medication was stopped (if stopDate is set).
  factory _PetCareEvent.fromMedicationStop(_MedicationRec m) {
    return _PetCareEvent(
      kind: _PetCareEventKind.medicationStop,
      when: m.stopDate ?? m.startDate,
      title: m.name,
      subtitle: m.condition,
      body: null,
      details: const {},
      medication: m,
    );
  }

  /// Build an event from a symptom check.
  factory _PetCareEvent.fromSymptomCheck(_SymptomCheckRec sc) {
    final details = <String, String>{};
    details['Messages'] = '${sc.messageCount}';
    if (sc.redFlagged) {
      details['Emergency flag'] = sc.redFlagReason ?? 'Triggered';
    }
    final kind = sc.redFlagged
        ? _PetCareEventKind.redFlagAlert
        : _PetCareEventKind.symptomCheck;
    return _PetCareEvent(
      kind: kind,
      when: sc.createdAt,
      title: sc.summary,
      subtitle: _humanizeTier(sc.finalTier),
      body: null,
      details: details,
      symptomCheck: sc,
    );
  }

  /// Build an event from a vet-recorded weight log. Kind is `vetWeightAlert`
  /// if the weight is flagged as above-range (joined from weight_alerts),
  /// otherwise `vetWeight`.
  factory _PetCareEvent.fromVetWeight(_VetWeightRec w) {
    final details = <String, String>{};
    final weightStr = w.weightLbs == w.weightLbs.roundToDouble()
        ? '${w.weightLbs.toInt()} lbs'
        : '${w.weightLbs.toStringAsFixed(1)} lbs';
    details['Weight'] = weightStr;
    if (w.clinicName != null && w.clinicName!.isNotEmpty) {
      details['Clinic'] = w.clinicName!;
    }
    if (w.providerName != null && w.providerName!.isNotEmpty) {
      details['Recorded by'] = w.providerName!;
    }
    if (w.bodyConditionScore != null) {
      details['Body condition'] =
          '${w.bodyConditionScore!.toStringAsFixed(1)} / 9';
    }
    return _PetCareEvent(
      kind: w.flaggedAboveRange
          ? _PetCareEventKind.vetWeightAlert
          : _PetCareEventKind.vetWeight,
      when: w.recordedAt,
      title: weightStr,
      subtitle: w.flaggedAboveRange
          ? 'Above healthy range for breed'
          : (w.providerName ?? w.clinicName),
      body: w.notes,
      details: details,
      vetWeight: w,
    );
  }

  static String _humanizeTier(String tier) {
    if (tier == 'emergency') return 'Flagged as emergency';
    if (tier == 'urgent') return 'Urgent vet visit';
    if (tier == 'routine') return 'Routine vet visit';
    if (tier == 'selfCare') return 'Monitor at home';
    return 'Gathering info';
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// FIRESTORE ERROR TRACKING
// ═══════════════════════════════════════════════════════════════════════════

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
    return 'Network hiccup. Pull to refresh when you have a signal.';
  }
  return 'Something went wrong loading this data.';
}

// ═══════════════════════════════════════════════════════════════════════════
// WIDGET DECLARATION
// Per JC's answer during Pet Symptom Checker build: FF UI for Pet Records
// will likewise NOT have width/height configured unless otherwise noted.
// We use MediaQuery-based sizing to avoid the "empty or cannot be parsed"
// error saga from earlier sessions.
// ═══════════════════════════════════════════════════════════════════════════
