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
// JOVI HEALTH — MEDICATION HALF-LIFE REFERENCE
// Version: 2026.09.22-r3 (Apple HIG refinement pass)
// r2:      2026.04.17 (major upgrade - 250+ meds, brand names, full data,
//          category grid, compare view, visualizer, symptom search,
//          alphabetical index, recently viewed, Firestore sync, swipe actions)
//
// r3 changes vs r2:
//  Bugs
//  - Search was unusable: tapping the search box switched to the search
//    view, which replaced the home screen and unmounted the field being
//    typed in. The list view now hosts its own copy of the field (focused),
//    so typing continues.
//  - "By Symptom" toggle only changed the hint text; matching was the same
//    either way. It now searches conditions and common uses only.
//  - A–Z index scrolled by a pixel estimate ("~88 px per card") and drifted.
//    It now jumps near the section, then snaps exactly with ensureVisible.
//  - Removed the empty _buildLetterIndexMap stub and unused map.
//  - Recently-viewed trim queried and deleted on every open; now only when
//    the local list is already at ten.
//  Apple design
//  - Every in-scroll BackdropFilter removed (one per card × 250 cards in
//    the A–Z list, plus every pill, tile and the hero). Painted glass now.
//    The floating bottom nav and dialogs keep their blur; content actually
//    scrolls under those.
//  - A–Z index is draggable like Contacts, with a tick per letter.
//  - Press feedback on pointer-down for cards, tiles, chips, nav, back.
//  - Elimination curve draws on when a medication opens.
//  - Every view change goes through one settle transition; Reduce Motion
//    honoured. Title case nav titles, 17 pt semibold. Share copies and
//    toasts instead of interrupting with a dialog. Sign-in prompt is a
//    native alert.
//  Responsibility
//  - "For reference only — not medical advice" on the hero card, at the
//    foot of every detail page, and in the copied share text.
// ═══════════════════════════════════════════════════════════════════════════

import 'dart:async';
import 'package:flutter/cupertino.dart';
import 'dart:ui' as ui;
import 'dart:math' as math;
import 'package:flutter/services.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';

// ─── Motion (Apple "response" values; critically damped, no overshoot) ──
class _Motion {
  static const Duration pressIn = Duration(milliseconds: 90);
  static const Duration pressOut = Duration(milliseconds: 260);
  static const Curve settle = Curves.easeOutCubic;
}

/// Press feedback that lives on pointer-down, not on release. Scales the
/// child down the instant a finger lands, releases when it lifts, and
/// springs back early if the finger travels ~10 px (a scroll, not a tap).
class _Pressable extends StatefulWidget {
  final Widget child;
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;
  final double pressedScale;
  final bool reduceMotion;
  final String? semanticsLabel;
  final String? semanticsHint;

  const _Pressable({
    Key? key,
    required this.child,
    this.onTap,
    this.onLongPress,
    this.pressedScale = 0.97,
    this.reduceMotion = false,
    this.semanticsLabel,
    this.semanticsHint,
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
    final scale = (_down && !widget.reduceMotion) ? widget.pressedScale : 1.0;
    final scaled = AnimatedScale(
      scale: scale,
      duration: _down ? _Motion.pressIn : _Motion.pressOut,
      curve: _down ? Curves.easeOut : _Motion.settle,
      child: widget.child,
    );
    final interactive = widget.onTap != null || widget.onLongPress != null;
    return Semantics(
      button: interactive,
      label: widget.semanticsLabel,
      hint: widget.semanticsHint,
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
        child: !interactive
            ? scaled
            : GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: widget.onTap,
                onLongPress: widget.onLongPress,
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
    duration: duration ?? const Duration(milliseconds: 2200),
    backgroundColor: const Color(0xFF243352),
    elevation: 0,
    behavior: SnackBarBehavior.floating,
    margin: const EdgeInsets.fromLTRB(16, 0, 16, 90),
    shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: BorderSide(color: accent.withOpacity(0.35))),
  );
}

// ─── Enums ──────────────────────────────────────────────────────────────────

enum ScreenType { compact, medium, expanded, large }

enum MedicationCategory {
  analgesics('Analgesics & Anti-inflammatory', Icons.healing),
  antibiotics('Antibiotics', Icons.biotech),
  antidiabetics('Antidiabetics', Icons.bloodtype),
  antidepressants('Antidepressants & Anxiolytics', Icons.sentiment_satisfied),
  antihypertensives('Antihypertensives', Icons.favorite),
  anticonvulsants('Anticonvulsants', Icons.flash_on),
  antipsychotics('Antipsychotics', Icons.psychology),
  immunosuppressants('Immunosuppressants', Icons.shield),
  hormonal('Hormonal Medications', Icons.spa),
  antivirals('Antivirals', Icons.coronavirus),
  antifungals('Antifungals', Icons.bug_report),
  muscleRelaxants('Muscle Relaxants', Icons.self_improvement),
  respiratory('Respiratory', Icons.air),
  cardiovascular('Cardiovascular', Icons.monitor_heart),
  anticoagulants('Anticoagulants & Antiplatelets', Icons.water_drop),
  gastrointestinal('Gastrointestinal', Icons.restaurant),
  urological('Urological', Icons.opacity),
  ophthalmologic('Ophthalmologic', Icons.visibility),
  dermatological('Dermatological', Icons.face_retouching_natural),
  neurological('Neurological', Icons.hub),
  oncology('Oncology', Icons.medical_services),
  specialized('Specialized', Icons.science),
  vaccines('Vaccines', Icons.vaccines),
  ophthalmic('Ophthalmic Drops', Icons.remove_red_eye),
  pediatric('Pediatric', Icons.child_care),
  other('Other', Icons.medication);

  const MedicationCategory(this.displayName, this.icon);
  final String displayName;
  final IconData icon;
}

enum PregnancyCategory {
  a('A', 'No risk demonstrated in controlled studies'),
  b('B', 'No risk in animal studies; no adequate human studies'),
  c('C', 'Animal studies show risk; benefits may outweigh risks'),
  d('D', 'Evidence of human fetal risk; potential benefits may outweigh'),
  x('X', 'Contraindicated in pregnancy'),
  n('N/A', 'Not assigned or not applicable');

  const PregnancyCategory(this.label, this.description);
  final String label;
  final String description;
}

enum ControlledSchedule {
  none('None', 'Not a controlled substance'),
  i('I', 'High abuse potential, no medical use'),
  ii('II', 'High abuse potential, accepted medical use'),
  iii('III', 'Moderate abuse potential'),
  iv('IV', 'Lower abuse potential'),
  v('V', 'Lowest abuse potential');

  const ControlledSchedule(this.label, this.description);
  final String label;
  final String description;
}

// ─── Responsive config ──────────────────────────────────────────────────────

class ResponsiveConfig {
  final double paddingH;
  final double paddingV;
  final double contentMax;
  final int actionColumns;
  final double actionItemHeight;
  final double actionIconDimension;
  final double actionTextSize;
  final bool wideMode;
  final bool hasHinge;
  final bool useTwoColumnLayout;

  ResponsiveConfig({
    required this.paddingH,
    required this.paddingV,
    required this.contentMax,
    required this.actionColumns,
    required this.actionItemHeight,
    required this.actionIconDimension,
    required this.actionTextSize,
    required this.wideMode,
    required this.hasHinge,
    this.useTwoColumnLayout = false,
  });
}

// ─── Brand palette ──────────────────────────────────────────────────────────

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

  static LinearGradient get coralGradient => LinearGradient(
        colors: [coral, coralDark],
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
      );
  static LinearGradient get navyGradient => LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [navy, navy, navyDark],
      );
}

// ─── Medication data model ──────────────────────────────────────────────────

class Medication {
  final String name;
  final List<String> brandNames;
  final String pronunciation;
  final String drugClass;
  final String halfLife;
  final String description;
  final String commonUses;
  final String sideEffects;
  final String dosageRange;
  final String onsetOfAction;
  final String peakTime;
  final List<String> routes;
  final List<String> interactions;
  final PregnancyCategory pregnancyCategory;
  final ControlledSchedule schedule;
  final String? blackBoxWarning;
  final List<String> conditions;
  final MedicationCategory category;
  final DateTime addedDate;

  Medication({
    required this.name,
    this.brandNames = const [],
    this.pronunciation = 'Not specified',
    this.drugClass = 'Not specified',
    required this.halfLife,
    required this.description,
    required this.commonUses,
    required this.sideEffects,
    this.dosageRange = 'Consult prescribing information',
    this.onsetOfAction = 'Not specified',
    this.peakTime = 'Not specified',
    this.routes = const ['Oral'],
    this.interactions = const [],
    this.pregnancyCategory = PregnancyCategory.n,
    this.schedule = ControlledSchedule.none,
    this.blackBoxWarning,
    this.conditions = const [],
    required this.category,
    DateTime? addedDate,
  }) : addedDate = addedDate ?? DateTime.now();

  /// Formatted display name with brand names in parens
  String get displayName {
    if (brandNames.isEmpty) return name;
    return '$name (${brandNames.join(", ")})';
  }

  /// Searchable text for match queries (includes name, brands, conditions)
  String get searchableText {
    return [
      name,
      ...brandNames,
      ...conditions,
      category.displayName,
      drugClass,
    ].join(' ').toLowerCase();
  }

  /// Parse the first numeric value from halfLife for sorting/calculation
  double get halfLifeHours {
    final match = RegExp(r'(\d+\.?\d*)').firstMatch(halfLife);
    if (match == null) return 0.0;
    final v = double.tryParse(match.group(0) ?? '0') ?? 0.0;
    // Convert minutes to hours if the string says minutes
    if (halfLife.toLowerCase().contains('minute')) return v / 60.0;
    // Days to hours
    if (halfLife.toLowerCase().contains('day')) return v * 24.0;
    return v;
  }

  /// For equality (used in favorites list)
  @override
  bool operator ==(Object other) =>
      identical(this, other) || (other is Medication && other.name == name);

  @override
  int get hashCode => name.hashCode;
}

// ═══════════════════════════════════════════════════════════════════════════
// MAIN WIDGET CLASS
// ═══════════════════════════════════════════════════════════════════════════

class HalfLifeWidget extends StatefulWidget {
  const HalfLifeWidget({
    super.key,
    this.width,
    this.height,
  });

  final double? width;
  final double? height;

  @override
  State<HalfLifeWidget> createState() => _HalfLifeWidgetState();
}

enum _ViewMode { home, categoryList, search, favorites, details, compare }

class _HalfLifeWidgetState extends State<HalfLifeWidget>
    with TickerProviderStateMixin {
  // View state
  _ViewMode _viewMode = _ViewMode.home;
  MedicationCategory? _currentCategory;
  Medication? _currentMedication;
  final List<Medication> _compareList = [];

  // Search state
  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';
  bool _searchByCondition = false;

  // Favorites & recently viewed (Firestore-backed)
  Set<String> _favoriteNames = {};
  List<Medication> _recentlyViewed = [];
  bool _isLoadingFavorites = false;
  bool _showFavoritesOnly = false;

  // Alphabet index state
  final ScrollController _listScrollController = ScrollController();
  final Map<String, GlobalKey> _letterKeys = {};
  String? _activeLetter;

  bool _reduceMotion = false; // MediaQuery.disableAnimations

  // Animations
  late AnimationController _fadeController;
  late Animation<double> _fadeAnimation;
  late AnimationController _slideController;
  late Animation<Offset> _slideAnimation;

  // Firestore
  FirebaseFirestore get _firestore => FirebaseFirestore.instance;
  String? get _currentUserId => FirebaseAuth.instance.currentUser?.uid;

  @override
  void initState() {
    super.initState();
    _fadeController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 320),
    );
    _fadeAnimation = CurvedAnimation(
      parent: _fadeController,
      curve: Curves.easeOut,
    );
    _slideController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 280),
    );
    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, 0.03),
      end: Offset.zero,
    ).animate(CurvedAnimation(
      parent: _slideController,
      curve: Curves.easeOutCubic,
    ));
    _fadeController.forward();
    _slideController.forward();

    _loadFavoritesAndRecent();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _reduceMotion = MediaQuery.of(context).disableAnimations;
    if (_reduceMotion) {
      if (_fadeController.value != 1.0) _fadeController.value = 1.0;
      if (_slideController.value != 1.0) _slideController.value = 1.0;
    }
  }

  /// Every view change goes through here: one short settle transition, or
  /// none under Reduce Motion.
  void _setView(_ViewMode mode, {VoidCallback? also}) {
    setState(() {
      _viewMode = mode;
      also?.call();
    });
    if (_reduceMotion) {
      _fadeController.value = 1.0;
      _slideController.value = 1.0;
      return;
    }
    _fadeController.forward(from: 0);
    _slideController.forward(from: 0);
  }

  void _toast(String message, {bool isSuccess = false}) {
    final messenger = ScaffoldMessenger.maybeOf(context);
    if (messenger == null) return;
    final accent = isSuccess ? _Jovi.mint : _Jovi.coral;
    messenger.hideCurrentSnackBar();
    messenger.showSnackBar(_joviToast(
      message,
      accent: accent,
      icon: isSuccess ? Icons.check_circle_rounded : Icons.info_rounded,
    ));
  }

  @override
  void dispose() {
    _fadeController.dispose();
    _slideController.dispose();
    _searchController.dispose();
    _listScrollController.dispose();
    super.dispose();
  }

  // ─── Firestore Integration ─────────────────────────────────────────────────

  Future<void> _loadFavoritesAndRecent() async {
    if (_currentUserId == null) return;
    if (!mounted) return;

    setState(() => _isLoadingFavorites = true);

    try {
      // Load favorites
      final favSnap = await _firestore
          .collection('users')
          .doc(_currentUserId)
          .collection('medicationFavorites')
          .get();

      final favNames = favSnap.docs.map((d) => d.id).toSet();

      // Load recently viewed (ordered by timestamp desc, limit 10)
      final recentSnap = await _firestore
          .collection('users')
          .doc(_currentUserId)
          .collection('medicationRecent')
          .orderBy('timestamp', descending: true)
          .limit(10)
          .get();

      final recentNames = recentSnap.docs.map((d) => d.id).toList();

      // Match names to medication objects
      final recentMeds = <Medication>[];
      for (final name in recentNames) {
        final match = _medicationDatabase.where((m) => m.name == name).toList();
        if (match.isNotEmpty) recentMeds.add(match.first);
      }

      if (!mounted) return;
      setState(() {
        _favoriteNames = favNames;
        _recentlyViewed = recentMeds;
        _isLoadingFavorites = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _isLoadingFavorites = false);
    }
  }

  Future<void> _toggleFavorite(Medication med) async {
    if (_currentUserId == null) {
      _showLoginRequiredDialog();
      return;
    }

    HapticFeedback.lightImpact();
    final isFav = _favoriteNames.contains(med.name);

    // Optimistic update
    setState(() {
      if (isFav) {
        _favoriteNames.remove(med.name);
      } else {
        _favoriteNames.add(med.name);
      }
    });

    try {
      final ref = _firestore
          .collection('users')
          .doc(_currentUserId)
          .collection('medicationFavorites')
          .doc(med.name);

      if (isFav) {
        await ref.delete();
      } else {
        await ref.set({
          'name': med.name,
          'category': med.category.name,
          'addedAt': FieldValue.serverTimestamp(),
        });
      }
    } catch (e) {
      // Revert on failure
      if (!mounted) return;
      setState(() {
        if (isFav) {
          _favoriteNames.add(med.name);
        } else {
          _favoriteNames.remove(med.name);
        }
      });
    }
  }

  Future<void> _addToRecentlyViewed(Medication med) async {
    if (_currentUserId == null) return;
    try {
      await _firestore
          .collection('users')
          .doc(_currentUserId)
          .collection('medicationRecent')
          .doc(med.name)
          .set({
        'name': med.name,
        'category': med.category.name,
        'timestamp': FieldValue.serverTimestamp(),
      });

      // Trim to last 10 — only query when we might actually be over.
      if (_recentlyViewed.length >= 10) {
        final snap = await _firestore
            .collection('users')
            .doc(_currentUserId)
            .collection('medicationRecent')
            .orderBy('timestamp', descending: true)
            .get();
        for (var i = 10; i < snap.docs.length; i++) {
          await snap.docs[i].reference.delete();
        }
      }

      // Update local state
      final updated = [
        med,
        ..._recentlyViewed.where((m) => m.name != med.name)
      ];
      if (updated.length > 10) updated.removeRange(10, updated.length);
      if (mounted) setState(() => _recentlyViewed = updated);
    } catch (_) {}
  }

  // ─── Helpers ───────────────────────────────────────────────────────────────

  List<Medication> get _sortedAllMeds {
    final list = List<Medication>.from(_medicationDatabase);
    list.sort((a, b) => a.name.compareTo(b.name));
    return list;
  }

  List<Medication> get _filteredMeds {
    var list = _sortedAllMeds;
    if (_currentCategory != null) {
      list = list.where((m) => m.category == _currentCategory).toList();
    }
    if (_searchQuery.isNotEmpty) {
      final q = _searchQuery.toLowerCase().trim();
      list = list.where((m) {
        // "By Symptom" searches what the drug treats; r2's toggle only
        // changed the hint text.
        if (_searchByCondition) {
          return [...m.conditions, m.commonUses]
              .join(' ')
              .toLowerCase()
              .contains(q);
        }
        return m.searchableText.contains(q);
      }).toList();
    }
    if (_showFavoritesOnly) {
      list = list.where((m) => _favoriteNames.contains(m.name)).toList();
    }
    return list;
  }

  Map<String, List<Medication>> get _groupedByLetter {
    final Map<String, List<Medication>> map = {};
    for (final med in _filteredMeds) {
      final letter = med.name.substring(0, 1).toUpperCase();
      map.putIfAbsent(letter, () => []).add(med);
    }
    return map;
  }

  int _categoryCount(MedicationCategory c) =>
      _medicationDatabase.where((m) => m.category == c).length;

  ResponsiveConfig _config(BoxConstraints c) {
    final w = c.maxWidth;
    final h = c.maxHeight;
    final isTwoColumn = w > 700 && w / h > 0.8;
    return ResponsiveConfig(
      paddingH: w < 400 ? 16 : 20,
      paddingV: 16,
      contentMax: isTwoColumn ? 900 : 600,
      actionColumns: w < 400 ? 2 : (w < 600 ? 3 : 4),
      actionItemHeight: 88,
      actionIconDimension: 32,
      actionTextSize: 11,
      wideMode: w > 700,
      hasHinge: false,
      useTwoColumnLayout: isTwoColumn,
    );
  }
  // ═══════════════════════════════════════════════════════════════════════════
  // MEDICATION DATABASE — 250+ medications with full clinical data
  // ═══════════════════════════════════════════════════════════════════════════

  static final List<Medication> _medicationDatabase = [
    // ─── ANALGESICS & ANTI-INFLAMMATORY ──────────────────────────────────────
    Medication(
      name: 'Ibuprofen',
      brandNames: ['Advil', 'Motrin', 'Nurofen'],
      pronunciation: 'eye-byoo-PROH-fen',
      drugClass: 'NSAID (Propionic acid)',
      halfLife: '2-4 hours',
      description: 'Nonsteroidal anti-inflammatory drug.',
      commonUses: 'Pain, inflammation, fever, arthritis.',
      sideEffects:
          'GI upset, ulcers, kidney issues, increased cardiovascular risk.',
      dosageRange: '200-800 mg every 6-8 hours (max 3200 mg/day)',
      onsetOfAction: '30 minutes',
      peakTime: '1-2 hours',
      routes: ['Oral', 'Topical', 'IV'],
      interactions: ['Warfarin', 'Aspirin', 'ACE inhibitors', 'Lithium'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning:
          'Increased risk of serious cardiovascular thrombotic events and GI bleeding.',
      conditions: [
        'Headache',
        'Arthritis',
        'Menstrual cramps',
        'Fever',
        'Muscle pain'
      ],
      category: MedicationCategory.analgesics,
      addedDate: DateTime(2025, 7, 16),
    ),
    Medication(
      name: 'Acetaminophen',
      brandNames: ['Tylenol', 'Panadol', 'FeverAll'],
      pronunciation: 'a-seet-a-MIN-oh-fen',
      drugClass: 'Analgesic/Antipyretic',
      halfLife: '2-3 hours',
      description: 'Non-opioid analgesic and fever reducer.',
      commonUses: 'Mild to moderate pain, fever reduction.',
      sideEffects: 'Rare at therapeutic doses; liver damage in overdose.',
      dosageRange: '325-1000 mg every 4-6 hours (max 4000 mg/day)',
      onsetOfAction: '30-60 minutes',
      peakTime: '1 hour',
      routes: ['Oral', 'Rectal', 'IV'],
      interactions: ['Warfarin', 'Alcohol', 'Isoniazid'],
      pregnancyCategory: PregnancyCategory.b,
      blackBoxWarning: 'Hepatotoxicity risk with overdose (>4g/day).',
      conditions: ['Headache', 'Fever', 'Pain', 'Arthritis'],
      category: MedicationCategory.analgesics,
      addedDate: DateTime(2025, 7, 15),
    ),
    Medication(
      name: 'Aspirin',
      brandNames: ['Bayer', 'Ecotrin', 'Bufferin'],
      pronunciation: 'AS-pir-in',
      drugClass: 'NSAID / Salicylate',
      halfLife: '3-9 hours (dose-dependent)',
      description: 'Salicylate NSAID with antiplatelet effects.',
      commonUses: 'Pain, fever, inflammation, cardiovascular protection.',
      sideEffects: 'GI bleeding, tinnitus, Reye syndrome in children.',
      dosageRange: '81-325 mg daily (cardiac); 325-1000 mg every 4-6 hr (pain)',
      onsetOfAction: '20-30 minutes',
      peakTime: '1-2 hours',
      routes: ['Oral', 'Rectal'],
      interactions: ['Warfarin', 'Methotrexate', 'ACE inhibitors', 'Alcohol'],
      pregnancyCategory: PregnancyCategory.d,
      conditions: [
        'Heart attack prevention',
        'Stroke prevention',
        'Pain',
        'Fever'
      ],
      category: MedicationCategory.analgesics,
      addedDate: DateTime(2025, 7, 14),
    ),
    Medication(
      name: 'Naproxen',
      brandNames: ['Aleve', 'Naprosyn', 'Anaprox'],
      pronunciation: 'na-PROX-en',
      drugClass: 'NSAID (Propionic acid)',
      halfLife: '12-17 hours',
      description: 'Long-acting nonsteroidal anti-inflammatory drug.',
      commonUses: 'Pain, inflammation, arthritis, menstrual cramps.',
      sideEffects: 'GI upset, ulcers, cardiovascular risk, kidney issues.',
      dosageRange: '220-550 mg every 12 hours (max 1500 mg/day)',
      onsetOfAction: '1 hour',
      peakTime: '2-4 hours',
      routes: ['Oral'],
      interactions: ['Warfarin', 'Lithium', 'ACE inhibitors', 'Methotrexate'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning: 'Increased cardiovascular and GI bleeding risk.',
      conditions: ['Arthritis', 'Menstrual cramps', 'Tendinitis', 'Back pain'],
      category: MedicationCategory.analgesics,
      addedDate: DateTime(2025, 7, 13),
    ),
    Medication(
      name: 'Celecoxib',
      brandNames: ['Celebrex'],
      pronunciation: 'sel-e-KOX-ib',
      drugClass: 'COX-2 inhibitor NSAID',
      halfLife: '11 hours',
      description: 'Selective COX-2 inhibitor with less GI impact.',
      commonUses: 'Osteoarthritis, rheumatoid arthritis, acute pain.',
      sideEffects: 'Cardiovascular events, GI upset, hypertension.',
      dosageRange: '100-200 mg twice daily',
      onsetOfAction: '45-60 minutes',
      peakTime: '3 hours',
      routes: ['Oral'],
      interactions: ['Warfarin', 'Fluconazole', 'Lithium', 'ACE inhibitors'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning:
          'Increased cardiovascular thrombotic events; serious GI events.',
      conditions: [
        'Osteoarthritis',
        'Rheumatoid arthritis',
        'Ankylosing spondylitis'
      ],
      category: MedicationCategory.analgesics,
      addedDate: DateTime(2025, 7, 12),
    ),
    Medication(
      name: 'Diclofenac',
      brandNames: ['Voltaren', 'Cambia', 'Cataflam'],
      pronunciation: 'dye-KLOE-fen-ak',
      drugClass: 'NSAID (Acetic acid)',
      halfLife: '1-2 hours',
      description: 'Potent NSAID available in oral and topical forms.',
      commonUses: 'Arthritis, acute pain, migraines.',
      sideEffects: 'GI upset, elevated liver enzymes, cardiovascular risk.',
      dosageRange: '50 mg 2-3 times daily',
      onsetOfAction: '30 minutes',
      peakTime: '1-2 hours',
      routes: ['Oral', 'Topical', 'IM', 'Ophthalmic'],
      interactions: ['Warfarin', 'Lithium', 'Methotrexate', 'Cyclosporine'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning: 'Increased cardiovascular and GI bleeding risk.',
      conditions: [
        'Osteoarthritis',
        'Rheumatoid arthritis',
        'Migraine',
        'Joint pain'
      ],
      category: MedicationCategory.analgesics,
      addedDate: DateTime(2025, 7, 11),
    ),
    Medication(
      name: 'Ketorolac',
      brandNames: ['Toradol', 'Acular'],
      pronunciation: 'kee-toe-ROLE-ak',
      drugClass: 'NSAID (Acetic acid)',
      halfLife: '5-6 hours',
      description: 'Potent injectable NSAID for short-term pain.',
      commonUses: 'Moderate to severe acute pain post-surgery.',
      sideEffects: 'GI bleeding, kidney failure, cardiovascular risk.',
      dosageRange: '10-30 mg every 6 hours (max 5 days)',
      onsetOfAction: '30 minutes',
      peakTime: '1-2 hours',
      routes: ['IV', 'IM', 'Oral', 'Ophthalmic'],
      interactions: ['Warfarin', 'ACE inhibitors', 'Lithium', 'Methotrexate'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning:
          'Not for use >5 days; serious GI, renal, cardiovascular risk.',
      conditions: ['Post-op pain', 'Kidney stones', 'Severe pain'],
      category: MedicationCategory.analgesics,
      addedDate: DateTime(2025, 7, 10),
    ),
    Medication(
      name: 'Meloxicam',
      brandNames: ['Mobic'],
      pronunciation: 'mel-OX-i-kam',
      drugClass: 'NSAID (Oxicam)',
      halfLife: '15-20 hours',
      description: 'Preferential COX-2 inhibitor NSAID.',
      commonUses: 'Osteoarthritis, rheumatoid arthritis.',
      sideEffects: 'GI upset, edema, hypertension.',
      dosageRange: '7.5-15 mg once daily',
      onsetOfAction: '30-60 minutes',
      peakTime: '4-5 hours',
      routes: ['Oral', 'IV'],
      interactions: ['Warfarin', 'Lithium', 'ACE inhibitors', 'Diuretics'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning: 'Cardiovascular and GI bleeding risk.',
      conditions: ['Osteoarthritis', 'Rheumatoid arthritis'],
      category: MedicationCategory.analgesics,
      addedDate: DateTime(2025, 7, 9),
    ),
    Medication(
      name: 'Morphine',
      brandNames: ['MS Contin', 'Kadian', 'Roxanol'],
      pronunciation: 'MOR-feen',
      drugClass: 'Opioid agonist',
      halfLife: '2-4 hours',
      description: 'Natural opioid for severe pain.',
      commonUses: 'Severe acute and chronic pain, post-surgical pain.',
      sideEffects: 'Respiratory depression, constipation, sedation, addiction.',
      dosageRange: '5-30 mg every 4 hours (IR); varies for ER',
      onsetOfAction: '15-30 minutes (IV immediate)',
      peakTime: '30-60 minutes',
      routes: ['Oral', 'IV', 'IM', 'SC', 'Epidural', 'Rectal'],
      interactions: ['Benzodiazepines', 'Alcohol', 'MAOIs', 'CNS depressants'],
      pregnancyCategory: PregnancyCategory.c,
      schedule: ControlledSchedule.ii,
      blackBoxWarning:
          'Addiction, respiratory depression, accidental ingestion.',
      conditions: ['Severe pain', 'Cancer pain', 'Post-surgical pain'],
      category: MedicationCategory.analgesics,
      addedDate: DateTime(2025, 7, 8),
    ),
    Medication(
      name: 'Oxycodone',
      brandNames: ['OxyContin', 'Roxicodone', 'Percocet (with APAP)'],
      pronunciation: 'ox-i-KOE-done',
      drugClass: 'Opioid agonist',
      halfLife: '3-5 hours (IR); 4.5 hours (ER)',
      description: 'Semi-synthetic opioid for moderate to severe pain.',
      commonUses: 'Moderate to severe pain.',
      sideEffects: 'Respiratory depression, constipation, nausea, addiction.',
      dosageRange: '5-15 mg every 4-6 hours',
      onsetOfAction: '10-15 minutes',
      peakTime: '30-60 minutes',
      routes: ['Oral'],
      interactions: ['Benzodiazepines', 'Alcohol', 'CYP3A4 inhibitors'],
      pregnancyCategory: PregnancyCategory.b,
      schedule: ControlledSchedule.ii,
      blackBoxWarning:
          'Addiction, respiratory depression, neonatal opioid withdrawal.',
      conditions: ['Post-op pain', 'Cancer pain', 'Severe pain'],
      category: MedicationCategory.analgesics,
      addedDate: DateTime(2025, 7, 7),
    ),
    Medication(
      name: 'Hydrocodone',
      brandNames: ['Vicodin', 'Norco', 'Lortab'],
      pronunciation: 'hye-droe-KOE-done',
      drugClass: 'Opioid agonist',
      halfLife: '4 hours',
      description: 'Semi-synthetic opioid, often combined with acetaminophen.',
      commonUses: 'Moderate to moderately severe pain, cough.',
      sideEffects:
          'Respiratory depression, constipation, drowsiness, addiction.',
      dosageRange: '5-10 mg every 4-6 hours',
      onsetOfAction: '10-30 minutes',
      peakTime: '1 hour',
      routes: ['Oral'],
      interactions: ['Benzodiazepines', 'Alcohol', 'CNS depressants'],
      pregnancyCategory: PregnancyCategory.c,
      schedule: ControlledSchedule.ii,
      blackBoxWarning:
          'Addiction, respiratory depression, hepatotoxicity (APAP combo).',
      conditions: ['Moderate pain', 'Post-op pain', 'Chronic pain'],
      category: MedicationCategory.analgesics,
      addedDate: DateTime(2025, 7, 6),
    ),
    Medication(
      name: 'Tramadol',
      brandNames: ['Ultram', 'Conzip'],
      pronunciation: 'TRAM-a-dol',
      drugClass: 'Atypical opioid / SNRI',
      halfLife: '6-8 hours',
      description: 'Weak opioid with SNRI activity for moderate pain.',
      commonUses: 'Moderate to moderately severe pain.',
      sideEffects: 'Nausea, dizziness, seizure risk, serotonin syndrome.',
      dosageRange: '50-100 mg every 4-6 hours (max 400 mg/day)',
      onsetOfAction: '1 hour',
      peakTime: '2 hours',
      routes: ['Oral'],
      interactions: ['SSRIs', 'MAOIs', 'Warfarin', 'Carbamazepine'],
      pregnancyCategory: PregnancyCategory.c,
      schedule: ControlledSchedule.iv,
      blackBoxWarning:
          'Addiction, respiratory depression, accidental ingestion, seizures.',
      conditions: ['Chronic pain', 'Post-op pain', 'Neuropathic pain'],
      category: MedicationCategory.analgesics,
      addedDate: DateTime(2025, 7, 5),
    ),
    Medication(
      name: 'Fentanyl',
      brandNames: ['Duragesic', 'Actiq', 'Sublimaze'],
      pronunciation: 'FEN-ta-nil',
      drugClass: 'Synthetic opioid',
      halfLife: '3-12 hours (route-dependent)',
      description:
          'Potent synthetic opioid, 50-100× more potent than morphine.',
      commonUses: 'Severe chronic pain, anesthesia, breakthrough cancer pain.',
      sideEffects: 'Severe respiratory depression, sedation, constipation.',
      dosageRange: '12-100 mcg/hr (patch); varies for IV',
      onsetOfAction: '1-2 minutes (IV); 12-24 hr (patch)',
      peakTime: '3-5 minutes (IV); 24-72 hr (patch)',
      routes: ['Transdermal', 'IV', 'Buccal', 'Sublingual', 'Nasal'],
      interactions: ['CYP3A4 inhibitors', 'Benzodiazepines', 'Alcohol'],
      pregnancyCategory: PregnancyCategory.c,
      schedule: ControlledSchedule.ii,
      blackBoxWarning:
          'Fatal respiratory depression; patches not for acute pain.',
      conditions: ['Cancer pain', 'Chronic severe pain', 'Breakthrough pain'],
      category: MedicationCategory.analgesics,
      addedDate: DateTime(2025, 7, 4),
    ),
    Medication(
      name: 'Codeine',
      brandNames: ['Tylenol #3 (with APAP)'],
      pronunciation: 'KOE-deen',
      drugClass: 'Opioid agonist',
      halfLife: '2.5-3 hours',
      description: 'Mild opioid, often combined with acetaminophen.',
      commonUses: 'Mild to moderate pain, cough suppression.',
      sideEffects: 'Constipation, drowsiness, respiratory depression.',
      dosageRange: '15-60 mg every 4-6 hours',
      onsetOfAction: '30-60 minutes',
      peakTime: '1-2 hours',
      routes: ['Oral'],
      interactions: ['CYP2D6 inhibitors', 'CNS depressants', 'MAOIs'],
      pregnancyCategory: PregnancyCategory.c,
      schedule: ControlledSchedule.ii,
      blackBoxWarning:
          'Ultra-rapid metabolizers at risk for fatal respiratory depression.',
      conditions: ['Cough', 'Mild pain', 'Diarrhea'],
      category: MedicationCategory.analgesics,
      addedDate: DateTime(2025, 7, 3),
    ),
    Medication(
      name: 'Ketoprofen',
      brandNames: ['Orudis', 'Oruvail'],
      pronunciation: 'kee-toe-PROE-fen',
      drugClass: 'NSAID (Propionic acid)',
      halfLife: '2-4 hours',
      description: 'Nonsteroidal anti-inflammatory drug.',
      commonUses: 'Arthritis, menstrual cramps, pain.',
      sideEffects: 'GI upset, ulcers, renal impairment.',
      dosageRange: '25-75 mg 3-4 times daily',
      onsetOfAction: '30 minutes',
      peakTime: '1-2 hours',
      routes: ['Oral', 'Topical'],
      interactions: ['Warfarin', 'Lithium', 'Methotrexate'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Arthritis', 'Dysmenorrhea', 'Mild pain'],
      category: MedicationCategory.analgesics,
      addedDate: DateTime(2025, 7, 2),
    ),
    Medication(
      name: 'Indomethacin',
      brandNames: ['Indocin'],
      pronunciation: 'in-doe-METH-a-sin',
      drugClass: 'NSAID (Acetic acid)',
      halfLife: '4.5 hours',
      description: 'Potent NSAID for severe inflammation.',
      commonUses: 'Gout, rheumatoid arthritis, ankylosing spondylitis.',
      sideEffects: 'GI bleeding, headache, CNS effects.',
      dosageRange: '25-50 mg 2-3 times daily',
      onsetOfAction: '30 minutes',
      peakTime: '2 hours',
      routes: ['Oral', 'IV', 'Rectal'],
      interactions: ['Warfarin', 'Lithium', 'Diuretics', 'ACE inhibitors'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning: 'Increased cardiovascular and GI risks.',
      conditions: ['Gout', 'Rheumatoid arthritis', 'Ankylosing spondylitis'],
      category: MedicationCategory.analgesics,
      addedDate: DateTime(2025, 7, 1),
    ),

    // ─── ANTIBIOTICS ─────────────────────────────────────────────────────────
    Medication(
      name: 'Amoxicillin',
      brandNames: ['Amoxil', 'Trimox', 'Moxatag'],
      pronunciation: 'a-mox-i-SIL-in',
      drugClass: 'Penicillin antibiotic',
      halfLife: '1-2 hours',
      description: 'Beta-lactam antibiotic for bacterial infections.',
      commonUses: 'Ear infections, pneumonia, UTIs, strep throat, H. pylori.',
      sideEffects: 'Nausea, diarrhea, rash, allergic reactions.',
      dosageRange: '250-1000 mg every 8 hours',
      onsetOfAction: '1-2 hours',
      peakTime: '1-2 hours',
      routes: ['Oral'],
      interactions: ['Probenecid', 'Warfarin', 'Allopurinol', 'OCPs'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: [
        'Strep throat',
        'Pneumonia',
        'Ear infection',
        'UTI',
        'H. pylori'
      ],
      category: MedicationCategory.antibiotics,
      addedDate: DateTime(2025, 6, 30),
    ),
    Medication(
      name: 'Amoxicillin-Clavulanate',
      brandNames: ['Augmentin'],
      pronunciation: 'a-mox-i-SIL-in klav-yoo-LAN-ate',
      drugClass: 'Penicillin + beta-lactamase inhibitor',
      halfLife: '1-1.5 hours',
      description: 'Broad-spectrum beta-lactam with beta-lactamase inhibitor.',
      commonUses: 'Sinusitis, pneumonia, UTIs, animal bites.',
      sideEffects: 'Diarrhea, GI upset, hepatotoxicity.',
      dosageRange: '500-875 mg every 8-12 hours',
      onsetOfAction: '1-2 hours',
      peakTime: '1-2 hours',
      routes: ['Oral', 'IV'],
      interactions: ['Probenecid', 'Warfarin', 'Allopurinol'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: [
        'Sinusitis',
        'Pneumonia',
        'UTI',
        'Animal bites',
        'Dental infection'
      ],
      category: MedicationCategory.antibiotics,
      addedDate: DateTime(2025, 6, 29),
    ),
    Medication(
      name: 'Azithromycin',
      brandNames: ['Zithromax', 'Z-Pak'],
      pronunciation: 'az-ith-roe-MYE-sin',
      drugClass: 'Macrolide antibiotic',
      halfLife: '68 hours',
      description: 'Long-acting macrolide antibiotic.',
      commonUses: 'Respiratory infections, STIs, skin infections.',
      sideEffects: 'GI upset, QT prolongation, hearing loss (rare).',
      dosageRange: '500 mg day 1, then 250 mg daily × 4 days',
      onsetOfAction: '2-3 hours',
      peakTime: '2-3 hours',
      routes: ['Oral', 'IV'],
      interactions: ['QT-prolonging drugs', 'Warfarin', 'Digoxin', 'Statins'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: [
        'Pneumonia',
        'Bronchitis',
        'Sinusitis',
        'Chlamydia',
        'Strep throat'
      ],
      category: MedicationCategory.antibiotics,
      addedDate: DateTime(2025, 6, 28),
    ),
    Medication(
      name: 'Ciprofloxacin',
      brandNames: ['Cipro'],
      pronunciation: 'sip-roe-FLOX-a-sin',
      drugClass: 'Fluoroquinolone',
      halfLife: '4 hours',
      description: 'Broad-spectrum fluoroquinolone antibiotic.',
      commonUses: 'UTIs, respiratory infections, anthrax.',
      sideEffects: 'Tendon rupture, QT prolongation, GI upset, C. diff.',
      dosageRange: '250-750 mg every 12 hours',
      onsetOfAction: '1-2 hours',
      peakTime: '1-2 hours',
      routes: ['Oral', 'IV', 'Ophthalmic'],
      interactions: ['Antacids', 'Warfarin', 'Theophylline', 'Iron'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning:
          'Tendinitis, tendon rupture, peripheral neuropathy, CNS effects.',
      conditions: ['UTI', 'Pneumonia', 'Diarrhea', 'Bone infections'],
      category: MedicationCategory.antibiotics,
      addedDate: DateTime(2025, 6, 27),
    ),
    Medication(
      name: 'Levofloxacin',
      brandNames: ['Levaquin'],
      pronunciation: 'lee-voe-FLOX-a-sin',
      drugClass: 'Fluoroquinolone',
      halfLife: '6-8 hours',
      description: 'Broad-spectrum fluoroquinolone with once-daily dosing.',
      commonUses: 'Pneumonia, sinusitis, UTIs, prostatitis.',
      sideEffects: 'Tendon rupture, CNS effects, QT prolongation.',
      dosageRange: '250-750 mg once daily',
      onsetOfAction: '1-2 hours',
      peakTime: '1-2 hours',
      routes: ['Oral', 'IV'],
      interactions: ['Antacids', 'Warfarin', 'NSAIDs', 'Steroids'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning:
          'Tendinitis, tendon rupture, CNS effects, peripheral neuropathy.',
      conditions: ['Pneumonia', 'UTI', 'Sinusitis', 'Prostatitis'],
      category: MedicationCategory.antibiotics,
      addedDate: DateTime(2025, 6, 26),
    ),
    Medication(
      name: 'Doxycycline',
      brandNames: ['Vibramycin', 'Doryx', 'Oracea'],
      pronunciation: 'dox-i-SYE-kleen',
      drugClass: 'Tetracycline antibiotic',
      halfLife: '18-22 hours',
      description: 'Broad-spectrum tetracycline antibiotic.',
      commonUses: 'Acne, Lyme disease, malaria prophylaxis, rosacea.',
      sideEffects:
          'Photosensitivity, GI upset, tooth discoloration (children).',
      dosageRange: '100 mg twice daily or 200 mg once daily',
      onsetOfAction: '1-2 hours',
      peakTime: '2-3 hours',
      routes: ['Oral', 'IV'],
      interactions: ['Antacids', 'Iron', 'Warfarin', 'OCPs'],
      pregnancyCategory: PregnancyCategory.d,
      conditions: ['Acne', 'Lyme disease', 'Rosacea', 'Chlamydia', 'Malaria'],
      category: MedicationCategory.antibiotics,
      addedDate: DateTime(2025, 6, 25),
    ),
    Medication(
      name: 'Clindamycin',
      brandNames: ['Cleocin'],
      pronunciation: 'klin-da-MYE-sin',
      drugClass: 'Lincosamide antibiotic',
      halfLife: '2-3 hours',
      description:
          'Lincosamide antibiotic for gram-positive and anaerobic coverage.',
      commonUses: 'Skin infections, dental infections, aspiration pneumonia.',
      sideEffects: 'C. diff colitis, diarrhea, rash.',
      dosageRange: '150-450 mg every 6 hours',
      onsetOfAction: '45-60 minutes',
      peakTime: '45-60 minutes',
      routes: ['Oral', 'IV', 'Topical', 'Vaginal'],
      interactions: ['Neuromuscular blockers', 'Erythromycin'],
      pregnancyCategory: PregnancyCategory.b,
      blackBoxWarning: 'Severe colitis (including C. difficile) possible.',
      conditions: [
        'Skin infection',
        'Dental infection',
        'Acne',
        'Bone infection'
      ],
      category: MedicationCategory.antibiotics,
      addedDate: DateTime(2025, 6, 24),
    ),
    Medication(
      name: 'Metronidazole',
      brandNames: ['Flagyl'],
      pronunciation: 'met-roe-NI-da-zole',
      drugClass: 'Nitroimidazole',
      halfLife: '6-8 hours',
      description: 'Antibiotic and antiprotozoal.',
      commonUses:
          'Bacterial vaginosis, C. diff, trichomoniasis, anaerobic infections.',
      sideEffects:
          'Metallic taste, disulfiram reaction with alcohol, neuropathy.',
      dosageRange: '250-500 mg every 6-12 hours',
      onsetOfAction: '1 hour',
      peakTime: '1-2 hours',
      routes: ['Oral', 'IV', 'Topical', 'Vaginal'],
      interactions: ['Alcohol', 'Warfarin', 'Lithium', 'Phenytoin'],
      pregnancyCategory: PregnancyCategory.b,
      blackBoxWarning: 'Possible carcinogenicity (animal studies).',
      conditions: [
        'Bacterial vaginosis',
        'C. diff',
        'Trichomoniasis',
        'Dental abscess'
      ],
      category: MedicationCategory.antibiotics,
      addedDate: DateTime(2025, 6, 23),
    ),
    Medication(
      name: 'Trimethoprim-Sulfamethoxazole',
      brandNames: ['Bactrim', 'Septra', 'Sulfatrim'],
      pronunciation: 'trye-METH-oh-prim sul-fa-meth-OX-a-zole',
      drugClass: 'Sulfonamide + folate inhibitor',
      halfLife: '8-10 hours',
      description: 'Combination antibiotic (TMP-SMX).',
      commonUses: 'UTIs, PCP pneumonia, MRSA skin infections.',
      sideEffects: 'Rash, Stevens-Johnson syndrome, hyperkalemia.',
      dosageRange: '1 DS tablet every 12 hours',
      onsetOfAction: '1-4 hours',
      peakTime: '1-4 hours',
      routes: ['Oral', 'IV'],
      interactions: ['Warfarin', 'Methotrexate', 'ACE inhibitors', 'OCPs'],
      pregnancyCategory: PregnancyCategory.d,
      conditions: [
        'UTI',
        'MRSA infection',
        'Traveler diarrhea',
        'PCP pneumonia'
      ],
      category: MedicationCategory.antibiotics,
      addedDate: DateTime(2025, 6, 22),
    ),
    Medication(
      name: 'Nitrofurantoin',
      brandNames: ['Macrobid', 'Macrodantin'],
      pronunciation: 'nye-troe-fyoor-AN-toyn',
      drugClass: 'Urinary antiseptic',
      halfLife: '20-60 minutes',
      description: 'Urinary-specific antibiotic.',
      commonUses: 'Uncomplicated UTIs.',
      sideEffects: 'GI upset, pulmonary toxicity, peripheral neuropathy.',
      dosageRange: '100 mg twice daily × 5 days',
      onsetOfAction: '1-2 hours',
      peakTime: '30 minutes',
      routes: ['Oral'],
      interactions: ['Antacids (magnesium)', 'Probenecid'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['UTI', 'Cystitis', 'UTI prophylaxis'],
      category: MedicationCategory.antibiotics,
      addedDate: DateTime(2025, 6, 21),
    ),
    Medication(
      name: 'Cephalexin',
      brandNames: ['Keflex'],
      pronunciation: 'sef-a-LEX-in',
      drugClass: 'First-generation cephalosporin',
      halfLife: '1 hour',
      description: 'Oral cephalosporin antibiotic.',
      commonUses: 'Skin infections, UTIs, ear infections.',
      sideEffects: 'GI upset, rash, allergic reactions.',
      dosageRange: '250-500 mg every 6 hours',
      onsetOfAction: '1 hour',
      peakTime: '1 hour',
      routes: ['Oral'],
      interactions: ['Probenecid', 'Metformin'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['Skin infection', 'UTI', 'Ear infection', 'Strep throat'],
      category: MedicationCategory.antibiotics,
      addedDate: DateTime(2025, 6, 20),
    ),
    Medication(
      name: 'Ceftriaxone',
      brandNames: ['Rocephin'],
      pronunciation: 'sef-trye-AX-one',
      drugClass: 'Third-generation cephalosporin',
      halfLife: '5-9 hours',
      description: 'Broad-spectrum injectable cephalosporin.',
      commonUses: 'Meningitis, pneumonia, gonorrhea, sepsis.',
      sideEffects: 'Injection site reactions, C. diff, biliary sludging.',
      dosageRange: '1-2 g every 24 hours',
      onsetOfAction: 'Immediate (IV)',
      peakTime: '2-3 hours (IM)',
      routes: ['IV', 'IM'],
      interactions: ['Calcium-containing IV solutions', 'Warfarin'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: [
        'Meningitis',
        'Pneumonia',
        'Gonorrhea',
        'Sepsis',
        'Pyelonephritis'
      ],
      category: MedicationCategory.antibiotics,
      addedDate: DateTime(2025, 6, 19),
    ),
    Medication(
      name: 'Vancomycin',
      brandNames: ['Vancocin', 'Firvanq'],
      pronunciation: 'van-koe-MYE-sin',
      drugClass: 'Glycopeptide antibiotic',
      halfLife: '4-11 hours',
      description:
          'Potent antibiotic for gram-positive infections including MRSA.',
      commonUses: 'MRSA, C. diff (oral), serious gram-positive infections.',
      sideEffects: 'Nephrotoxicity, ototoxicity, red man syndrome (IV).',
      dosageRange: '15-20 mg/kg IV every 8-12 hours',
      onsetOfAction: 'Immediate (IV)',
      peakTime: 'Immediately post-infusion',
      routes: ['IV', 'Oral (C. diff)'],
      interactions: ['Aminoglycosides', 'Loop diuretics'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['MRSA', 'C. diff', 'Endocarditis', 'Sepsis'],
      category: MedicationCategory.antibiotics,
      addedDate: DateTime(2025, 6, 18),
    ),

    // ─── ANTIDIABETICS ───────────────────────────────────────────────────────
    Medication(
      name: 'Metformin',
      brandNames: ['Glucophage', 'Fortamet', 'Glumetza'],
      pronunciation: 'met-FOR-min',
      drugClass: 'Biguanide',
      halfLife: '6-7 hours',
      description: 'First-line oral antidiabetic medication.',
      commonUses: 'Type 2 diabetes, prediabetes, PCOS.',
      sideEffects:
          'GI upset, metallic taste, lactic acidosis (rare), B12 deficiency.',
      dosageRange: '500-2000 mg daily in divided doses',
      onsetOfAction: '1-3 hours',
      peakTime: '2-3 hours',
      routes: ['Oral'],
      interactions: ['Contrast dye', 'Alcohol', 'Cimetidine'],
      pregnancyCategory: PregnancyCategory.b,
      blackBoxWarning: 'Lactic acidosis (rare but serious).',
      conditions: [
        'Type 2 diabetes',
        'PCOS',
        'Prediabetes',
        'Insulin resistance'
      ],
      category: MedicationCategory.antidiabetics,
      addedDate: DateTime(2025, 6, 17),
    ),
    Medication(
      name: 'Insulin (Regular)',
      brandNames: ['Humulin R', 'Novolin R'],
      pronunciation: 'IN-su-lin',
      drugClass: 'Short-acting insulin',
      halfLife: '4-6 minutes',
      description: 'Short-acting human insulin.',
      commonUses: 'Blood sugar control in diabetes.',
      sideEffects: 'Hypoglycemia, injection site reactions, weight gain.',
      dosageRange: 'Individualized (typically 0.5-1 unit/kg/day)',
      onsetOfAction: '30 minutes',
      peakTime: '2-4 hours',
      routes: ['SC', 'IV', 'IM'],
      interactions: ['Beta-blockers', 'Alcohol', 'Thiazolidinediones'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['Type 1 diabetes', 'Type 2 diabetes', 'DKA', 'Hyperkalemia'],
      category: MedicationCategory.antidiabetics,
      addedDate: DateTime(2025, 6, 16),
    ),
    Medication(
      name: 'Insulin Glargine',
      brandNames: ['Lantus', 'Basaglar', 'Toujeo'],
      pronunciation: 'IN-su-lin GLAR-jeen',
      drugClass: 'Long-acting insulin',
      halfLife: '12 hours (effect up to 24 hr)',
      description: 'Long-acting basal insulin.',
      commonUses: 'Type 1 and Type 2 diabetes basal coverage.',
      sideEffects: 'Hypoglycemia, injection site reactions.',
      dosageRange: 'Individualized; typically once daily',
      onsetOfAction: '1-2 hours',
      peakTime: 'No pronounced peak',
      routes: ['SC'],
      interactions: ['Beta-blockers', 'Alcohol', 'Thiazolidinediones'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Type 1 diabetes', 'Type 2 diabetes'],
      category: MedicationCategory.antidiabetics,
      addedDate: DateTime(2025, 6, 15),
    ),
    Medication(
      name: 'Insulin Lispro',
      brandNames: ['Humalog', 'Admelog'],
      pronunciation: 'IN-su-lin LIS-pro',
      drugClass: 'Rapid-acting insulin',
      halfLife: '1 hour',
      description: 'Rapid-acting mealtime insulin.',
      commonUses: 'Prandial coverage in diabetes.',
      sideEffects: 'Hypoglycemia, injection site reactions.',
      dosageRange: 'Individualized; typically before meals',
      onsetOfAction: '15 minutes',
      peakTime: '30-90 minutes',
      routes: ['SC', 'IV'],
      interactions: ['Beta-blockers', 'Alcohol'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['Type 1 diabetes', 'Type 2 diabetes'],
      category: MedicationCategory.antidiabetics,
      addedDate: DateTime(2025, 6, 14),
    ),
    Medication(
      name: 'Glipizide',
      brandNames: ['Glucotrol'],
      pronunciation: 'GLIP-i-zide',
      drugClass: 'Sulfonylurea',
      halfLife: '2-4 hours',
      description: 'Second-generation sulfonylurea.',
      commonUses: 'Type 2 diabetes.',
      sideEffects: 'Hypoglycemia, weight gain, rash.',
      dosageRange: '2.5-40 mg daily',
      onsetOfAction: '30 minutes',
      peakTime: '1-3 hours',
      routes: ['Oral'],
      interactions: ['Beta-blockers', 'NSAIDs', 'Warfarin', 'Salicylates'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Type 2 diabetes'],
      category: MedicationCategory.antidiabetics,
      addedDate: DateTime(2025, 6, 13),
    ),
    Medication(
      name: 'Glyburide',
      brandNames: ['DiaBeta', 'Glynase', 'Micronase'],
      pronunciation: 'GLYE-byoor-ide',
      drugClass: 'Sulfonylurea',
      halfLife: '10 hours',
      description: 'Second-generation sulfonylurea.',
      commonUses: 'Type 2 diabetes.',
      sideEffects: 'Hypoglycemia, weight gain.',
      dosageRange: '1.25-20 mg daily',
      onsetOfAction: '1 hour',
      peakTime: '4 hours',
      routes: ['Oral'],
      interactions: ['Fluconazole', 'Warfarin', 'Beta-blockers'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Type 2 diabetes'],
      category: MedicationCategory.antidiabetics,
      addedDate: DateTime(2025, 6, 12),
    ),
    Medication(
      name: 'Sitagliptin',
      brandNames: ['Januvia'],
      pronunciation: 'sit-a-GLIP-tin',
      drugClass: 'DPP-4 inhibitor',
      halfLife: '12-14 hours',
      description: 'Dipeptidyl peptidase-4 inhibitor.',
      commonUses: 'Type 2 diabetes.',
      sideEffects: 'URI, headache, pancreatitis (rare).',
      dosageRange: '100 mg once daily',
      onsetOfAction: '1-4 hours',
      peakTime: '1-4 hours',
      routes: ['Oral'],
      interactions: ['Digoxin'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['Type 2 diabetes'],
      category: MedicationCategory.antidiabetics,
      addedDate: DateTime(2025, 6, 11),
    ),
    Medication(
      name: 'Empagliflozin',
      brandNames: ['Jardiance'],
      pronunciation: 'em-pa-gli-FLOE-zin',
      drugClass: 'SGLT2 inhibitor',
      halfLife: '12-13 hours',
      description: 'Sodium-glucose cotransporter 2 inhibitor.',
      commonUses: 'Type 2 diabetes, heart failure, CKD.',
      sideEffects: 'UTI, genital mycotic infections, DKA, dehydration.',
      dosageRange: '10-25 mg once daily',
      onsetOfAction: '1-2 hours',
      peakTime: '1.5 hours',
      routes: ['Oral'],
      interactions: ['Diuretics', 'Insulin'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Type 2 diabetes', 'Heart failure', 'CKD'],
      category: MedicationCategory.antidiabetics,
      addedDate: DateTime(2025, 6, 10),
    ),
    Medication(
      name: 'Semaglutide',
      brandNames: ['Ozempic', 'Wegovy', 'Rybelsus'],
      pronunciation: 'sem-a-GLOO-tide',
      drugClass: 'GLP-1 receptor agonist',
      halfLife: '1 week',
      description: 'Long-acting GLP-1 analog.',
      commonUses:
          'Type 2 diabetes, weight management, cardiovascular risk reduction.',
      sideEffects: 'Nausea, vomiting, pancreatitis, gallbladder disease.',
      dosageRange: '0.25-2 mg SC weekly; 3-14 mg oral daily',
      onsetOfAction: 'Days to weeks',
      peakTime: '1-3 days',
      routes: ['SC', 'Oral'],
      interactions: [
        'Insulin',
        'Sulfonylureas',
        'Oral meds (delayed absorption)'
      ],
      pregnancyCategory: PregnancyCategory.x,
      blackBoxWarning: 'Risk of thyroid C-cell tumors in rodents.',
      conditions: ['Type 2 diabetes', 'Obesity', 'Weight loss'],
      category: MedicationCategory.antidiabetics,
      addedDate: DateTime(2025, 6, 9),
    ),
    Medication(
      name: 'Pioglitazone',
      brandNames: ['Actos'],
      pronunciation: 'pye-oh-GLI-ta-zone',
      drugClass: 'Thiazolidinedione',
      halfLife: '3-7 hours',
      description: 'TZD insulin sensitizer.',
      commonUses: 'Type 2 diabetes.',
      sideEffects: 'Weight gain, edema, bladder cancer risk, fractures.',
      dosageRange: '15-45 mg once daily',
      onsetOfAction: 'Weeks',
      peakTime: '2 hours',
      routes: ['Oral'],
      interactions: ['Gemfibrozil', 'Rifampin', 'CYP2C8 inhibitors'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning: 'Heart failure risk; may cause or exacerbate CHF.',
      conditions: ['Type 2 diabetes'],
      category: MedicationCategory.antidiabetics,
      addedDate: DateTime(2025, 6, 8),
    ),
    // ─── ANTIDEPRESSANTS & ANXIOLYTICS ───────────────────────────────────────
    Medication(
      name: 'Sertraline',
      brandNames: ['Zoloft'],
      pronunciation: 'SER-tra-leen',
      drugClass: 'SSRI',
      halfLife: '24-26 hours',
      description: 'Selective serotonin reuptake inhibitor.',
      commonUses: 'Depression, anxiety, OCD, PTSD, panic disorder.',
      sideEffects: 'Nausea, insomnia, sexual dysfunction, weight changes.',
      dosageRange: '25-200 mg once daily',
      onsetOfAction: '2-4 weeks',
      peakTime: '4.5-8.5 hours',
      routes: ['Oral'],
      interactions: ['MAOIs', 'Warfarin', 'NSAIDs', 'Tramadol'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning: 'Increased suicidality in children/young adults.',
      conditions: [
        'Depression',
        'Anxiety',
        'OCD',
        'PTSD',
        'Panic disorder',
        'PMDD'
      ],
      category: MedicationCategory.antidepressants,
      addedDate: DateTime(2025, 6, 7),
    ),
    Medication(
      name: 'Fluoxetine',
      brandNames: ['Prozac', 'Sarafem'],
      pronunciation: 'floo-OX-e-teen',
      drugClass: 'SSRI',
      halfLife: '1-3 days (active metabolite 4-16 days)',
      description: 'Long half-life SSRI antidepressant.',
      commonUses: 'Depression, OCD, bulimia, panic disorder, PMDD.',
      sideEffects: 'Insomnia, nausea, sexual dysfunction, weight loss.',
      dosageRange: '20-80 mg once daily',
      onsetOfAction: '2-4 weeks',
      peakTime: '6-8 hours',
      routes: ['Oral'],
      interactions: ['MAOIs', 'Warfarin', 'Tricyclics', 'Triptans'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning: 'Increased suicidality in children/young adults.',
      conditions: ['Depression', 'OCD', 'Bulimia', 'Panic disorder', 'PMDD'],
      category: MedicationCategory.antidepressants,
      addedDate: DateTime(2025, 6, 6),
    ),
    Medication(
      name: 'Escitalopram',
      brandNames: ['Lexapro', 'Cipralex'],
      pronunciation: 'es-sye-TAL-oh-pram',
      drugClass: 'SSRI',
      halfLife: '27-32 hours',
      description: 'S-enantiomer of citalopram, SSRI.',
      commonUses: 'Depression, generalized anxiety disorder.',
      sideEffects: 'Nausea, insomnia, sexual dysfunction, QT prolongation.',
      dosageRange: '5-20 mg once daily',
      onsetOfAction: '1-4 weeks',
      peakTime: '5 hours',
      routes: ['Oral'],
      interactions: ['MAOIs', 'QT-prolonging drugs', 'NSAIDs'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning: 'Increased suicidality in young adults.',
      conditions: ['Depression', 'GAD', 'Social anxiety'],
      category: MedicationCategory.antidepressants,
      addedDate: DateTime(2025, 6, 5),
    ),
    Medication(
      name: 'Citalopram',
      brandNames: ['Celexa'],
      pronunciation: 'sye-TAL-oh-pram',
      drugClass: 'SSRI',
      halfLife: '35 hours',
      description: 'SSRI antidepressant.',
      commonUses: 'Depression, anxiety disorders.',
      sideEffects: 'QT prolongation, nausea, sexual dysfunction.',
      dosageRange: '10-40 mg once daily',
      onsetOfAction: '1-4 weeks',
      peakTime: '4 hours',
      routes: ['Oral'],
      interactions: ['MAOIs', 'QT-prolonging drugs'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning: 'Increased suicidality in young adults.',
      conditions: ['Depression', 'Anxiety'],
      category: MedicationCategory.antidepressants,
      addedDate: DateTime(2025, 6, 4),
    ),
    Medication(
      name: 'Paroxetine',
      brandNames: ['Paxil', 'Pexeva'],
      pronunciation: 'pa-ROX-e-teen',
      drugClass: 'SSRI',
      halfLife: '21 hours',
      description: 'SSRI with more sedating profile.',
      commonUses: 'Depression, OCD, PTSD, social anxiety, GAD.',
      sideEffects: 'Weight gain, sexual dysfunction, discontinuation syndrome.',
      dosageRange: '10-60 mg once daily',
      onsetOfAction: '1-4 weeks',
      peakTime: '6 hours',
      routes: ['Oral'],
      interactions: ['MAOIs', 'Tamoxifen', 'Warfarin'],
      pregnancyCategory: PregnancyCategory.d,
      blackBoxWarning: 'Increased suicidality in young adults.',
      conditions: ['Depression', 'OCD', 'PTSD', 'GAD', 'Social anxiety'],
      category: MedicationCategory.antidepressants,
      addedDate: DateTime(2025, 6, 3),
    ),
    Medication(
      name: 'Venlafaxine',
      brandNames: ['Effexor', 'Effexor XR'],
      pronunciation: 'ven-la-FAX-een',
      drugClass: 'SNRI',
      halfLife: '5 hours (11 for active metabolite)',
      description: 'Serotonin-norepinephrine reuptake inhibitor.',
      commonUses: 'Depression, GAD, social anxiety, panic disorder.',
      sideEffects: 'Hypertension, nausea, discontinuation syndrome.',
      dosageRange: '75-375 mg daily',
      onsetOfAction: '2-4 weeks',
      peakTime: '2 hours',
      routes: ['Oral'],
      interactions: ['MAOIs', 'Triptans', 'St. John\'s Wort'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning: 'Increased suicidality in young adults.',
      conditions: ['Depression', 'GAD', 'Panic disorder', 'Social anxiety'],
      category: MedicationCategory.antidepressants,
      addedDate: DateTime(2025, 6, 2),
    ),
    Medication(
      name: 'Duloxetine',
      brandNames: ['Cymbalta', 'Irenka'],
      pronunciation: 'doo-LOX-e-teen',
      drugClass: 'SNRI',
      halfLife: '12 hours',
      description: 'SNRI also used for pain.',
      commonUses: 'Depression, GAD, diabetic neuropathy, fibromyalgia.',
      sideEffects: 'Nausea, dry mouth, hepatotoxicity, HTN.',
      dosageRange: '30-120 mg daily',
      onsetOfAction: '1-4 weeks',
      peakTime: '6 hours',
      routes: ['Oral'],
      interactions: ['MAOIs', 'CYP1A2 inhibitors', 'Warfarin'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning: 'Increased suicidality in young adults.',
      conditions: [
        'Depression',
        'GAD',
        'Neuropathic pain',
        'Fibromyalgia',
        'Chronic pain'
      ],
      category: MedicationCategory.antidepressants,
      addedDate: DateTime(2025, 6, 1),
    ),
    Medication(
      name: 'Bupropion',
      brandNames: ['Wellbutrin', 'Zyban', 'Forfivo'],
      pronunciation: 'byoo-PROE-pee-on',
      drugClass: 'Atypical antidepressant (NDRI)',
      halfLife: '21 hours',
      description: 'Norepinephrine-dopamine reuptake inhibitor.',
      commonUses: 'Depression, smoking cessation, seasonal affective disorder.',
      sideEffects: 'Insomnia, dry mouth, seizures (dose-dependent).',
      dosageRange: '150-450 mg daily',
      onsetOfAction: '1-2 weeks',
      peakTime: '3-5 hours',
      routes: ['Oral'],
      interactions: ['MAOIs', 'Seizure-lowering drugs'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning: 'Neuropsychiatric events; increased suicidality.',
      conditions: [
        'Depression',
        'Smoking cessation',
        'SAD',
        'ADHD (off-label)'
      ],
      category: MedicationCategory.antidepressants,
      addedDate: DateTime(2025, 5, 30),
    ),
    Medication(
      name: 'Mirtazapine',
      brandNames: ['Remeron'],
      pronunciation: 'mir-TAZ-a-peen',
      drugClass: 'Tetracyclic antidepressant',
      halfLife: '20-40 hours',
      description: 'Noradrenergic/serotonergic antidepressant.',
      commonUses: 'Depression, insomnia, anxiety.',
      sideEffects: 'Sedation, weight gain, dry mouth, agranulocytosis (rare).',
      dosageRange: '15-45 mg at bedtime',
      onsetOfAction: '1-2 weeks',
      peakTime: '2 hours',
      routes: ['Oral'],
      interactions: ['MAOIs', 'CNS depressants', 'Warfarin'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning: 'Increased suicidality in young adults.',
      conditions: ['Depression', 'Insomnia', 'Anxiety'],
      category: MedicationCategory.antidepressants,
      addedDate: DateTime(2025, 5, 29),
    ),
    Medication(
      name: 'Trazodone',
      brandNames: ['Desyrel', 'Oleptro'],
      pronunciation: 'TRAZ-oh-done',
      drugClass: 'Serotonin modulator',
      halfLife: '5-9 hours',
      description: 'Serotonin antagonist and reuptake inhibitor.',
      commonUses: 'Depression, insomnia (off-label).',
      sideEffects: 'Sedation, priapism, orthostatic hypotension.',
      dosageRange: '25-400 mg daily',
      onsetOfAction: '1-2 weeks',
      peakTime: '1-2 hours',
      routes: ['Oral'],
      interactions: ['MAOIs', 'CNS depressants', 'CYP3A4 inhibitors'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning: 'Increased suicidality in young adults.',
      conditions: ['Depression', 'Insomnia', 'Anxiety'],
      category: MedicationCategory.antidepressants,
      addedDate: DateTime(2025, 5, 28),
    ),
    Medication(
      name: 'Lorazepam',
      brandNames: ['Ativan'],
      pronunciation: 'lor-AZ-e-pam',
      drugClass: 'Benzodiazepine (intermediate-acting)',
      halfLife: '10-20 hours',
      description: 'Intermediate-acting benzodiazepine.',
      commonUses: 'Anxiety, seizures, insomnia, alcohol withdrawal.',
      sideEffects: 'Sedation, dependence, respiratory depression.',
      dosageRange: '0.5-2 mg 2-3 times daily',
      onsetOfAction: '15-30 minutes',
      peakTime: '2 hours',
      routes: ['Oral', 'IV', 'IM', 'SL'],
      interactions: ['Opioids', 'Alcohol', 'CNS depressants'],
      pregnancyCategory: PregnancyCategory.d,
      schedule: ControlledSchedule.iv,
      blackBoxWarning:
          'Fatal respiratory depression when combined with opioids.',
      conditions: ['Anxiety', 'Seizures', 'Insomnia', 'Alcohol withdrawal'],
      category: MedicationCategory.antidepressants,
      addedDate: DateTime(2025, 5, 27),
    ),
    Medication(
      name: 'Alprazolam',
      brandNames: ['Xanax', 'Niravam'],
      pronunciation: 'al-PRAY-zoe-lam',
      drugClass: 'Benzodiazepine (short-acting)',
      halfLife: '6-27 hours',
      description: 'Short-acting benzodiazepine.',
      commonUses: 'Panic disorder, anxiety.',
      sideEffects: 'Sedation, dependence, amnesia.',
      dosageRange: '0.25-4 mg daily in divided doses',
      onsetOfAction: '15-30 minutes',
      peakTime: '1-2 hours',
      routes: ['Oral'],
      interactions: ['CYP3A4 inhibitors', 'Opioids', 'Alcohol'],
      pregnancyCategory: PregnancyCategory.d,
      schedule: ControlledSchedule.iv,
      blackBoxWarning: 'Fatal respiratory depression with opioids; dependence.',
      conditions: ['Panic disorder', 'Anxiety', 'Agoraphobia'],
      category: MedicationCategory.antidepressants,
      addedDate: DateTime(2025, 5, 26),
    ),
    Medication(
      name: 'Clonazepam',
      brandNames: ['Klonopin'],
      pronunciation: 'kloe-NAZ-e-pam',
      drugClass: 'Benzodiazepine (long-acting)',
      halfLife: '18-50 hours',
      description: 'Long-acting benzodiazepine.',
      commonUses: 'Panic disorder, seizures, restless legs.',
      sideEffects: 'Sedation, dependence, depression.',
      dosageRange: '0.25-4 mg daily',
      onsetOfAction: '20-60 minutes',
      peakTime: '1-4 hours',
      routes: ['Oral'],
      interactions: ['Opioids', 'CNS depressants', 'Phenytoin'],
      pregnancyCategory: PregnancyCategory.d,
      schedule: ControlledSchedule.iv,
      blackBoxWarning: 'Fatal respiratory depression with opioids.',
      conditions: ['Panic disorder', 'Seizures', 'Anxiety'],
      category: MedicationCategory.antidepressants,
      addedDate: DateTime(2025, 5, 25),
    ),
    Medication(
      name: 'Diazepam',
      brandNames: ['Valium', 'Diastat'],
      pronunciation: 'dye-AZ-e-pam',
      drugClass: 'Benzodiazepine (long-acting)',
      halfLife: '20-100 hours',
      description: 'Long-acting benzodiazepine.',
      commonUses: 'Anxiety, alcohol withdrawal, seizures, muscle spasm.',
      sideEffects: 'Sedation, dependence, accumulation in elderly.',
      dosageRange: '2-10 mg 2-4 times daily',
      onsetOfAction: '15-60 minutes',
      peakTime: '1-2 hours',
      routes: ['Oral', 'IV', 'IM', 'Rectal'],
      interactions: ['Opioids', 'Alcohol', 'CYP3A4 inhibitors'],
      pregnancyCategory: PregnancyCategory.d,
      schedule: ControlledSchedule.iv,
      blackBoxWarning: 'Fatal respiratory depression with opioids.',
      conditions: ['Anxiety', 'Alcohol withdrawal', 'Seizures', 'Muscle spasm'],
      category: MedicationCategory.antidepressants,
      addedDate: DateTime(2025, 5, 24),
    ),
    Medication(
      name: 'Buspirone',
      brandNames: ['Buspar'],
      pronunciation: 'byoo-SPYE-rone',
      drugClass: 'Azapirone (non-benzo anxiolytic)',
      halfLife: '2-3 hours',
      description: 'Non-benzodiazepine anxiolytic.',
      commonUses: 'Generalized anxiety disorder.',
      sideEffects: 'Dizziness, nausea, headache.',
      dosageRange: '5-60 mg daily in divided doses',
      onsetOfAction: '2-4 weeks',
      peakTime: '40-90 minutes',
      routes: ['Oral'],
      interactions: ['MAOIs', 'CYP3A4 inhibitors', 'Grapefruit'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['GAD', 'Anxiety'],
      category: MedicationCategory.antidepressants,
      addedDate: DateTime(2025, 5, 23),
    ),
    Medication(
      name: 'Amitriptyline',
      brandNames: ['Elavil', 'Endep'],
      pronunciation: 'a-mee-TRIP-ti-leen',
      drugClass: 'Tricyclic antidepressant',
      halfLife: '10-28 hours',
      description: 'Tricyclic antidepressant.',
      commonUses: 'Depression, chronic pain, migraine prophylaxis, insomnia.',
      sideEffects: 'Anticholinergic effects, weight gain, arrhythmias.',
      dosageRange: '25-300 mg daily',
      onsetOfAction: '2-4 weeks',
      peakTime: '4 hours',
      routes: ['Oral'],
      interactions: ['MAOIs', 'QT-prolonging drugs', 'Anticholinergics'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning: 'Increased suicidality in young adults.',
      conditions: ['Depression', 'Neuropathic pain', 'Migraine', 'Insomnia'],
      category: MedicationCategory.antidepressants,
      addedDate: DateTime(2025, 5, 22),
    ),

    // ─── ANTIHYPERTENSIVES ───────────────────────────────────────────────────
    Medication(
      name: 'Lisinopril',
      brandNames: ['Prinivil', 'Zestril'],
      pronunciation: 'lye-SIN-oh-pril',
      drugClass: 'ACE inhibitor',
      halfLife: '12 hours',
      description: 'Angiotensin-converting enzyme inhibitor.',
      commonUses: 'Hypertension, heart failure, post-MI.',
      sideEffects: 'Cough, hyperkalemia, angioedema, hypotension.',
      dosageRange: '5-40 mg once daily',
      onsetOfAction: '1 hour',
      peakTime: '6-7 hours',
      routes: ['Oral'],
      interactions: ['NSAIDs', 'Potassium supplements', 'Lithium'],
      pregnancyCategory: PregnancyCategory.d,
      blackBoxWarning: 'Fetal injury/death when used in pregnancy.',
      conditions: [
        'Hypertension',
        'Heart failure',
        'Post-MI',
        'Diabetic nephropathy'
      ],
      category: MedicationCategory.antihypertensives,
      addedDate: DateTime(2025, 5, 21),
    ),
    Medication(
      name: 'Losartan',
      brandNames: ['Cozaar'],
      pronunciation: 'loe-SAR-tan',
      drugClass: 'ARB',
      halfLife: '2 hours (6-9 for metabolite)',
      description: 'Angiotensin II receptor blocker.',
      commonUses: 'Hypertension, diabetic nephropathy, stroke prevention.',
      sideEffects: 'Dizziness, hyperkalemia, angioedema (rare).',
      dosageRange: '25-100 mg daily',
      onsetOfAction: '1 hour',
      peakTime: '3-4 hours',
      routes: ['Oral'],
      interactions: ['NSAIDs', 'Potassium supplements', 'Lithium'],
      pregnancyCategory: PregnancyCategory.d,
      blackBoxWarning: 'Fetal injury/death when used in pregnancy.',
      conditions: ['Hypertension', 'Diabetic nephropathy', 'Heart failure'],
      category: MedicationCategory.antihypertensives,
      addedDate: DateTime(2025, 5, 20),
    ),
    Medication(
      name: 'Valsartan',
      brandNames: ['Diovan'],
      pronunciation: 'val-SAR-tan',
      drugClass: 'ARB',
      halfLife: '6 hours',
      description: 'Angiotensin II receptor blocker.',
      commonUses: 'Hypertension, heart failure, post-MI.',
      sideEffects: 'Dizziness, hyperkalemia, fatigue.',
      dosageRange: '80-320 mg once daily',
      onsetOfAction: '2 hours',
      peakTime: '2-4 hours',
      routes: ['Oral'],
      interactions: ['NSAIDs', 'Potassium-sparing diuretics'],
      pregnancyCategory: PregnancyCategory.d,
      blackBoxWarning: 'Fetal injury/death when used in pregnancy.',
      conditions: ['Hypertension', 'Heart failure', 'Post-MI'],
      category: MedicationCategory.antihypertensives,
      addedDate: DateTime(2025, 5, 19),
    ),
    Medication(
      name: 'Amlodipine',
      brandNames: ['Norvasc'],
      pronunciation: 'am-LOE-di-peen',
      drugClass: 'Calcium channel blocker (dihydropyridine)',
      halfLife: '30-50 hours',
      description: 'Long-acting dihydropyridine CCB.',
      commonUses: 'Hypertension, angina.',
      sideEffects: 'Peripheral edema, flushing, dizziness.',
      dosageRange: '2.5-10 mg once daily',
      onsetOfAction: '6-12 hours',
      peakTime: '6-12 hours',
      routes: ['Oral'],
      interactions: ['CYP3A4 inhibitors/inducers', 'Simvastatin'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Hypertension', 'Angina', 'Coronary artery disease'],
      category: MedicationCategory.antihypertensives,
      addedDate: DateTime(2025, 5, 18),
    ),
    Medication(
      name: 'Metoprolol',
      brandNames: ['Lopressor', 'Toprol-XL'],
      pronunciation: 'me-TOE-proe-lol',
      drugClass: 'Beta-1 selective blocker',
      halfLife: '3-7 hours',
      description: 'Cardioselective beta-blocker.',
      commonUses: 'Hypertension, angina, heart failure, post-MI.',
      sideEffects: 'Bradycardia, fatigue, bronchospasm, ED.',
      dosageRange: '25-200 mg twice daily (IR); 25-400 mg once daily (ER)',
      onsetOfAction: '1 hour',
      peakTime: '1-2 hours',
      routes: ['Oral', 'IV'],
      interactions: ['Verapamil', 'Diltiazem', 'Clonidine'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning: 'Do not abruptly discontinue (ischemic events).',
      conditions: [
        'Hypertension',
        'Angina',
        'Heart failure',
        'Post-MI',
        'AFib'
      ],
      category: MedicationCategory.antihypertensives,
      addedDate: DateTime(2025, 5, 17),
    ),
    Medication(
      name: 'Atenolol',
      brandNames: ['Tenormin'],
      pronunciation: 'a-TEN-oh-lol',
      drugClass: 'Beta-1 selective blocker',
      halfLife: '6-7 hours',
      description: 'Cardioselective beta-blocker.',
      commonUses: 'Hypertension, angina.',
      sideEffects: 'Bradycardia, fatigue, cold extremities.',
      dosageRange: '25-100 mg once daily',
      onsetOfAction: '1 hour',
      peakTime: '2-4 hours',
      routes: ['Oral'],
      interactions: ['Verapamil', 'Clonidine', 'Insulin'],
      pregnancyCategory: PregnancyCategory.d,
      conditions: ['Hypertension', 'Angina'],
      category: MedicationCategory.antihypertensives,
      addedDate: DateTime(2025, 5, 16),
    ),
    Medication(
      name: 'Carvedilol',
      brandNames: ['Coreg'],
      pronunciation: 'KAR-ve-dil-ol',
      drugClass: 'Non-selective beta-blocker + alpha-1 blocker',
      halfLife: '7-10 hours',
      description: 'Combined alpha and beta blocker.',
      commonUses: 'Heart failure, post-MI, hypertension.',
      sideEffects: 'Dizziness, fatigue, bradycardia, hyperglycemia.',
      dosageRange: '3.125-25 mg twice daily',
      onsetOfAction: '30 minutes',
      peakTime: '1-2 hours',
      routes: ['Oral'],
      interactions: ['Verapamil', 'Diltiazem', 'Digoxin', 'Insulin'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Heart failure', 'Post-MI', 'Hypertension'],
      category: MedicationCategory.antihypertensives,
      addedDate: DateTime(2025, 5, 15),
    ),
    Medication(
      name: 'Hydrochlorothiazide',
      brandNames: ['Microzide', 'HydroDIURIL'],
      pronunciation: 'hye-droe-klor-oh-THY-a-zide',
      drugClass: 'Thiazide diuretic',
      halfLife: '6-15 hours',
      description: 'Thiazide diuretic.',
      commonUses: 'Hypertension, edema.',
      sideEffects: 'Hypokalemia, hyponatremia, hyperglycemia, gout.',
      dosageRange: '12.5-50 mg once daily',
      onsetOfAction: '2 hours',
      peakTime: '4-6 hours',
      routes: ['Oral'],
      interactions: ['Lithium', 'NSAIDs', 'Digoxin'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['Hypertension', 'Edema', 'Heart failure'],
      category: MedicationCategory.antihypertensives,
      addedDate: DateTime(2025, 5, 14),
    ),
    Medication(
      name: 'Furosemide',
      brandNames: ['Lasix'],
      pronunciation: 'fyoor-OH-se-mide',
      drugClass: 'Loop diuretic',
      halfLife: '2 hours',
      description: 'Potent loop diuretic.',
      commonUses: 'Edema, heart failure, hypertension.',
      sideEffects: 'Hypokalemia, dehydration, ototoxicity, hyperuricemia.',
      dosageRange: '20-80 mg daily (titrate to effect)',
      onsetOfAction: '30-60 minutes (oral), 5 minutes (IV)',
      peakTime: '1-2 hours',
      routes: ['Oral', 'IV', 'IM'],
      interactions: ['Lithium', 'Aminoglycosides', 'NSAIDs', 'Digoxin'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning:
          'Profound diuresis can lead to fluid/electrolyte depletion.',
      conditions: ['Heart failure', 'Edema', 'Hypertension', 'Pulmonary edema'],
      category: MedicationCategory.antihypertensives,
      addedDate: DateTime(2025, 5, 13),
    ),
    Medication(
      name: 'Spironolactone',
      brandNames: ['Aldactone', 'CaroSpir'],
      pronunciation: 'speer-on-oh-LAK-tone',
      drugClass: 'Potassium-sparing diuretic / Aldosterone antagonist',
      halfLife: '1.4 hours (canrenone metabolite 20+ hr)',
      description: 'Aldosterone antagonist.',
      commonUses: 'Heart failure, hypertension, PCOS, hirsutism, acne.',
      sideEffects: 'Hyperkalemia, gynecomastia, menstrual irregularities.',
      dosageRange: '25-200 mg daily',
      onsetOfAction: '24-48 hours',
      peakTime: '2-3 hours',
      routes: ['Oral'],
      interactions: [
        'ACE inhibitors',
        'ARBs',
        'NSAIDs',
        'Potassium supplements'
      ],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning: 'Tumorigenic in rodents.',
      conditions: [
        'Heart failure',
        'Hypertension',
        'PCOS',
        'Hirsutism',
        'Acne'
      ],
      category: MedicationCategory.antihypertensives,
      addedDate: DateTime(2025, 5, 12),
    ),
    Medication(
      name: 'Clonidine',
      brandNames: ['Catapres', 'Kapvay'],
      pronunciation: 'KLOE-ni-deen',
      drugClass: 'Central alpha-2 agonist',
      halfLife: '12-16 hours',
      description: 'Centrally-acting alpha-2 agonist.',
      commonUses: 'Hypertension, ADHD, opioid withdrawal, tic disorders.',
      sideEffects:
          'Dry mouth, sedation, rebound hypertension if stopped abruptly.',
      dosageRange: '0.1-0.6 mg twice daily',
      onsetOfAction: '30-60 minutes',
      peakTime: '1-3 hours',
      routes: ['Oral', 'Transdermal', 'Epidural'],
      interactions: ['Tricyclics', 'Beta-blockers', 'CNS depressants'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Hypertension', 'ADHD', 'Opioid withdrawal', 'Hot flashes'],
      category: MedicationCategory.antihypertensives,
      addedDate: DateTime(2025, 5, 11),
    ),
    Medication(
      name: 'Hydralazine',
      brandNames: ['Apresoline'],
      pronunciation: 'hye-DRAL-a-zeen',
      drugClass: 'Direct vasodilator',
      halfLife: '3-7 hours',
      description: 'Direct-acting arteriolar vasodilator.',
      commonUses: 'Hypertension, heart failure.',
      sideEffects: 'Tachycardia, headache, lupus-like syndrome.',
      dosageRange: '10-50 mg 4 times daily',
      onsetOfAction: '20-30 minutes',
      peakTime: '1-2 hours',
      routes: ['Oral', 'IV', 'IM'],
      interactions: ['MAOIs', 'Beta-blockers'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Hypertension', 'Heart failure', 'Preeclampsia'],
      category: MedicationCategory.antihypertensives,
      addedDate: DateTime(2025, 5, 10),
    ),

    // ─── ANTICONVULSANTS ─────────────────────────────────────────────────────
    Medication(
      name: 'Gabapentin',
      brandNames: ['Neurontin', 'Gralise', 'Horizant'],
      pronunciation: 'GAB-a-pen-tin',
      drugClass: 'Anticonvulsant (GABA analog)',
      halfLife: '5-7 hours',
      description: 'Gamma-aminobutyric acid analog.',
      commonUses: 'Neuropathic pain, seizures, restless legs syndrome.',
      sideEffects: 'Dizziness, somnolence, peripheral edema.',
      dosageRange: '300-3600 mg daily in divided doses',
      onsetOfAction: '2-3 hours',
      peakTime: '2-3 hours',
      routes: ['Oral'],
      interactions: ['Antacids', 'Opioids', 'CNS depressants'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: [
        'Neuropathic pain',
        'Seizures',
        'Postherpetic neuralgia',
        'RLS'
      ],
      category: MedicationCategory.anticonvulsants,
      addedDate: DateTime(2025, 5, 9),
    ),
    Medication(
      name: 'Pregabalin',
      brandNames: ['Lyrica'],
      pronunciation: 'pre-GAB-a-lin',
      drugClass: 'Anticonvulsant / Alpha-2-delta ligand',
      halfLife: '6 hours',
      description: 'GABA analog with potent anticonvulsant effects.',
      commonUses: 'Neuropathic pain, fibromyalgia, seizures, GAD.',
      sideEffects: 'Dizziness, somnolence, weight gain, peripheral edema.',
      dosageRange: '75-600 mg daily in divided doses',
      onsetOfAction: '1-2 weeks for pain',
      peakTime: '1-2 hours',
      routes: ['Oral'],
      interactions: ['CNS depressants', 'Opioids', 'Alcohol'],
      pregnancyCategory: PregnancyCategory.c,
      schedule: ControlledSchedule.v,
      conditions: ['Fibromyalgia', 'Neuropathic pain', 'Seizures', 'GAD'],
      category: MedicationCategory.anticonvulsants,
      addedDate: DateTime(2025, 5, 8),
    ),
    Medication(
      name: 'Phenytoin',
      brandNames: ['Dilantin', 'Phenytek'],
      pronunciation: 'FEN-i-toyn',
      drugClass: 'Hydantoin anticonvulsant',
      halfLife: '12-36 hours',
      description: 'Sodium channel blocker anticonvulsant.',
      commonUses: 'Tonic-clonic seizures, status epilepticus.',
      sideEffects: 'Gingival hyperplasia, hirsutism, nystagmus, ataxia.',
      dosageRange: '100 mg 3 times daily (adjust to serum levels)',
      onsetOfAction: '1-2 hours (oral); immediate (IV)',
      peakTime: '1.5-3 hours',
      routes: ['Oral', 'IV'],
      interactions: ['Warfarin', 'OCPs', 'Many CYP inducers/inhibitors'],
      pregnancyCategory: PregnancyCategory.d,
      blackBoxWarning:
          'Cardiac arrhythmias and hypotension with IV administration.',
      conditions: ['Seizures', 'Status epilepticus'],
      category: MedicationCategory.anticonvulsants,
      addedDate: DateTime(2025, 5, 7),
    ),
    Medication(
      name: 'Carbamazepine',
      brandNames: ['Tegretol', 'Carbatrol'],
      pronunciation: 'kar-ba-MAZ-e-peen',
      drugClass: 'Anticonvulsant',
      halfLife: '25-65 hours',
      description: 'Tricyclic anticonvulsant and mood stabilizer.',
      commonUses: 'Seizures, trigeminal neuralgia, bipolar disorder.',
      sideEffects: 'Agranulocytosis, SJS, drowsiness, hyponatremia.',
      dosageRange: '200-1200 mg daily',
      onsetOfAction: '1 month',
      peakTime: '4-5 hours',
      routes: ['Oral'],
      interactions: ['Many drugs via CYP3A4 induction'],
      pregnancyCategory: PregnancyCategory.d,
      blackBoxWarning:
          'Aplastic anemia, agranulocytosis, SJS/TEN (HLA-B*1502).',
      conditions: ['Seizures', 'Trigeminal neuralgia', 'Bipolar disorder'],
      category: MedicationCategory.anticonvulsants,
      addedDate: DateTime(2025, 5, 6),
    ),
    Medication(
      name: 'Valproic Acid',
      brandNames: ['Depakote', 'Depakene'],
      pronunciation: 'val-PROE-ik AS-id',
      drugClass: 'Anticonvulsant',
      halfLife: '9-16 hours',
      description: 'Broad-spectrum anticonvulsant and mood stabilizer.',
      commonUses: 'Seizures, bipolar disorder, migraine prophylaxis.',
      sideEffects: 'Hepatotoxicity, pancreatitis, teratogenicity.',
      dosageRange: '500-2500 mg daily',
      onsetOfAction: '1-4 hours',
      peakTime: '1-4 hours',
      routes: ['Oral', 'IV'],
      interactions: ['Warfarin', 'Carbamazepine', 'Phenytoin', 'Lamotrigine'],
      pregnancyCategory: PregnancyCategory.d,
      blackBoxWarning:
          'Hepatotoxicity (especially children <2 yrs), pancreatitis, teratogenicity.',
      conditions: ['Seizures', 'Bipolar disorder', 'Migraine prophylaxis'],
      category: MedicationCategory.anticonvulsants,
      addedDate: DateTime(2025, 5, 5),
    ),
    Medication(
      name: 'Lamotrigine',
      brandNames: ['Lamictal'],
      pronunciation: 'la-MOE-tri-jeen',
      drugClass: 'Anticonvulsant',
      halfLife: '25-33 hours',
      description: 'Sodium channel anticonvulsant and mood stabilizer.',
      commonUses: 'Seizures, bipolar disorder.',
      sideEffects: 'Rash (SJS risk), headache, dizziness.',
      dosageRange: '25-400 mg daily (slow titration)',
      onsetOfAction: '1-2 weeks',
      peakTime: '1.5-5 hours',
      routes: ['Oral'],
      interactions: ['Valproic acid', 'OCPs', 'Carbamazepine'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning: 'Life-threatening skin reactions (SJS/TEN).',
      conditions: ['Seizures', 'Bipolar disorder'],
      category: MedicationCategory.anticonvulsants,
      addedDate: DateTime(2025, 5, 4),
    ),
    Medication(
      name: 'Levetiracetam',
      brandNames: ['Keppra'],
      pronunciation: 'lee-ve-tye-RA-se-tam',
      drugClass: 'Anticonvulsant',
      halfLife: '6-8 hours',
      description: 'Novel mechanism anticonvulsant.',
      commonUses: 'Partial, generalized, and myoclonic seizures.',
      sideEffects: 'Behavioral changes, somnolence, irritability.',
      dosageRange: '500-3000 mg daily',
      onsetOfAction: '1 hour',
      peakTime: '1 hour',
      routes: ['Oral', 'IV'],
      interactions: ['Few - minimal drug interactions'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Seizures', 'Status epilepticus'],
      category: MedicationCategory.anticonvulsants,
      addedDate: DateTime(2025, 5, 3),
    ),
    Medication(
      name: 'Topiramate',
      brandNames: ['Topamax', 'Trokendi', 'Qudexy'],
      pronunciation: 'toe-PYRE-a-mate',
      drugClass: 'Anticonvulsant',
      halfLife: '21 hours',
      description: 'Broad-spectrum anticonvulsant.',
      commonUses:
          'Seizures, migraine prophylaxis, weight loss (with phentermine).',
      sideEffects:
          'Cognitive effects, kidney stones, weight loss, metabolic acidosis.',
      dosageRange: '25-400 mg daily',
      onsetOfAction: '2-4 weeks',
      peakTime: '2 hours',
      routes: ['Oral'],
      interactions: [
        'OCPs',
        'CNS depressants',
        'Carbonic anhydrase inhibitors'
      ],
      pregnancyCategory: PregnancyCategory.d,
      conditions: ['Seizures', 'Migraine prophylaxis', 'Weight loss'],
      category: MedicationCategory.anticonvulsants,
      addedDate: DateTime(2025, 5, 2),
    ),
    Medication(
      name: 'Oxcarbazepine',
      brandNames: ['Trileptal', 'Oxtellar'],
      pronunciation: 'ox-kar-BAZ-e-peen',
      drugClass: 'Anticonvulsant',
      halfLife: '9 hours (metabolite 2 hours)',
      description: 'Ketoanalog of carbamazepine.',
      commonUses: 'Partial seizures.',
      sideEffects: 'Hyponatremia, SJS, dizziness.',
      dosageRange: '300-2400 mg daily',
      onsetOfAction: '1-2 weeks',
      peakTime: '4.5 hours',
      routes: ['Oral'],
      interactions: ['OCPs', 'Phenytoin', 'Carbamazepine'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Seizures', 'Trigeminal neuralgia'],
      category: MedicationCategory.anticonvulsants,
      addedDate: DateTime(2025, 5, 1),
    ),
    Medication(
      name: 'Phenobarbital',
      brandNames: ['Luminal'],
      pronunciation: 'fee-noe-BAR-bi-tal',
      drugClass: 'Barbiturate anticonvulsant',
      halfLife: '53-118 hours',
      description: 'Long-acting barbiturate.',
      commonUses: 'Seizures, status epilepticus, neonatal seizures.',
      sideEffects: 'Sedation, respiratory depression, dependence.',
      dosageRange: '60-250 mg daily',
      onsetOfAction: '60+ minutes (oral); 5 minutes (IV)',
      peakTime: '8-12 hours',
      routes: ['Oral', 'IV', 'IM'],
      interactions: ['CYP inducers affect many drugs', 'OCPs', 'Warfarin'],
      pregnancyCategory: PregnancyCategory.d,
      schedule: ControlledSchedule.iv,
      conditions: ['Seizures', 'Status epilepticus', 'Anxiety'],
      category: MedicationCategory.anticonvulsants,
      addedDate: DateTime(2025, 4, 30),
    ),
    // ─── ANTIPSYCHOTICS ──────────────────────────────────────────────────────
    Medication(
      name: 'Haloperidol',
      brandNames: ['Haldol'],
      pronunciation: 'ha-loe-PER-i-dole',
      drugClass: 'Typical antipsychotic (butyrophenone)',
      halfLife: '12-38 hours',
      description: 'High-potency typical antipsychotic.',
      commonUses: 'Schizophrenia, acute agitation, Tourette syndrome.',
      sideEffects: 'EPS, tardive dyskinesia, NMS, QT prolongation.',
      dosageRange: '0.5-20 mg daily',
      onsetOfAction: '30-60 minutes',
      peakTime: '2-6 hours',
      routes: ['Oral', 'IV', 'IM'],
      interactions: ['CNS depressants', 'QT-prolonging drugs', 'Levodopa'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning:
          'Increased mortality in elderly with dementia-related psychosis.',
      conditions: [
        'Schizophrenia',
        'Agitation',
        'Tourette syndrome',
        'Delirium'
      ],
      category: MedicationCategory.antipsychotics,
      addedDate: DateTime(2025, 4, 29),
    ),
    Medication(
      name: 'Risperidone',
      brandNames: ['Risperdal', 'Perseris'],
      pronunciation: 'ris-PER-i-done',
      drugClass: 'Atypical antipsychotic',
      halfLife: '3-20 hours',
      description: 'Atypical antipsychotic.',
      commonUses:
          'Schizophrenia, bipolar disorder, autism-related irritability.',
      sideEffects: 'Weight gain, hyperprolactinemia, EPS.',
      dosageRange: '0.5-8 mg daily',
      onsetOfAction: '1-2 weeks',
      peakTime: '1 hour',
      routes: ['Oral', 'IM depot'],
      interactions: ['CYP2D6 inhibitors', 'Carbamazepine', 'Levodopa'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning:
          'Increased mortality in elderly with dementia-related psychosis.',
      conditions: ['Schizophrenia', 'Bipolar disorder', 'Autism irritability'],
      category: MedicationCategory.antipsychotics,
      addedDate: DateTime(2025, 4, 28),
    ),
    Medication(
      name: 'Olanzapine',
      brandNames: ['Zyprexa'],
      pronunciation: 'oh-LAN-za-peen',
      drugClass: 'Atypical antipsychotic',
      halfLife: '21-54 hours',
      description: 'Atypical antipsychotic with significant metabolic effects.',
      commonUses: 'Schizophrenia, bipolar disorder.',
      sideEffects: 'Significant weight gain, diabetes, sedation.',
      dosageRange: '5-20 mg once daily',
      onsetOfAction: '1-2 weeks',
      peakTime: '6 hours',
      routes: ['Oral', 'IM', 'ODT'],
      interactions: ['CYP1A2 inhibitors', 'Fluvoxamine', 'Smoking'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning:
          'Increased mortality in elderly with dementia-related psychosis.',
      conditions: ['Schizophrenia', 'Bipolar disorder', 'Acute mania'],
      category: MedicationCategory.antipsychotics,
      addedDate: DateTime(2025, 4, 27),
    ),
    Medication(
      name: 'Quetiapine',
      brandNames: ['Seroquel'],
      pronunciation: 'kwe-TYE-a-peen',
      drugClass: 'Atypical antipsychotic',
      halfLife: '6-7 hours',
      description: 'Atypical antipsychotic with sedating properties.',
      commonUses: 'Schizophrenia, bipolar disorder, depression adjunct.',
      sideEffects: 'Sedation, weight gain, orthostatic hypotension.',
      dosageRange: '50-800 mg daily',
      onsetOfAction: '1-2 weeks',
      peakTime: '1.5 hours',
      routes: ['Oral'],
      interactions: ['CYP3A4 inhibitors', 'CNS depressants'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning:
          'Increased mortality in elderly dementia; suicidality in young adults.',
      conditions: [
        'Schizophrenia',
        'Bipolar disorder',
        'Depression (adjunct)',
        'Insomnia (off-label)'
      ],
      category: MedicationCategory.antipsychotics,
      addedDate: DateTime(2025, 4, 26),
    ),
    Medication(
      name: 'Aripiprazole',
      brandNames: ['Abilify', 'Abilify Maintena'],
      pronunciation: 'a-ri-PIP-ra-zole',
      drugClass: 'Atypical antipsychotic (partial D2 agonist)',
      halfLife: '75 hours',
      description: 'Partial dopamine agonist atypical antipsychotic.',
      commonUses:
          'Schizophrenia, bipolar disorder, depression adjunct, Tourette.',
      sideEffects:
          'Akathisia, nausea, headache, weight gain (less than others).',
      dosageRange: '2-30 mg once daily',
      onsetOfAction: '1-2 weeks',
      peakTime: '3-5 hours',
      routes: ['Oral', 'IM', 'IM depot'],
      interactions: ['CYP3A4 and CYP2D6 inhibitors'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning:
          'Increased mortality in elderly dementia; suicidality in young adults.',
      conditions: [
        'Schizophrenia',
        'Bipolar disorder',
        'Depression (adjunct)',
        'Tourette',
        'Autism'
      ],
      category: MedicationCategory.antipsychotics,
      addedDate: DateTime(2025, 4, 25),
    ),
    Medication(
      name: 'Clozapine',
      brandNames: ['Clozaril', 'FazaClo'],
      pronunciation: 'KLOE-za-peen',
      drugClass: 'Atypical antipsychotic',
      halfLife: '8-12 hours',
      description:
          'Atypical antipsychotic for treatment-resistant schizophrenia.',
      commonUses:
          'Treatment-resistant schizophrenia, suicidal behavior in schizophrenia.',
      sideEffects:
          'Agranulocytosis, seizures, myocarditis, weight gain, sedation.',
      dosageRange: '12.5-900 mg daily (very slow titration)',
      onsetOfAction: 'Weeks',
      peakTime: '2.5 hours',
      routes: ['Oral'],
      interactions: ['Fluvoxamine', 'Smoking', 'CYP1A2 inhibitors'],
      pregnancyCategory: PregnancyCategory.b,
      blackBoxWarning:
          'Severe neutropenia, seizures, myocarditis, orthostatic hypotension, dementia mortality.',
      conditions: ['Treatment-resistant schizophrenia'],
      category: MedicationCategory.antipsychotics,
      addedDate: DateTime(2025, 4, 24),
    ),
    Medication(
      name: 'Ziprasidone',
      brandNames: ['Geodon'],
      pronunciation: 'zi-PRAS-i-done',
      drugClass: 'Atypical antipsychotic',
      halfLife: '7 hours',
      description: 'Atypical antipsychotic with minimal weight gain.',
      commonUses: 'Schizophrenia, acute bipolar mania.',
      sideEffects: 'QT prolongation, sedation, somnolence.',
      dosageRange: '20-160 mg twice daily (with food)',
      onsetOfAction: '1-2 weeks',
      peakTime: '6-8 hours',
      routes: ['Oral', 'IM'],
      interactions: ['QT-prolonging drugs', 'CYP3A4 inducers/inhibitors'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning: 'Increased mortality in elderly dementia.',
      conditions: ['Schizophrenia', 'Bipolar disorder'],
      category: MedicationCategory.antipsychotics,
      addedDate: DateTime(2025, 4, 23),
    ),
    Medication(
      name: 'Paliperidone',
      brandNames: ['Invega', 'Invega Sustenna', 'Invega Trinza'],
      pronunciation: 'pal-ee-PER-i-done',
      drugClass: 'Atypical antipsychotic',
      halfLife: '23 hours',
      description: 'Active metabolite of risperidone.',
      commonUses: 'Schizophrenia, schizoaffective disorder.',
      sideEffects: 'EPS, hyperprolactinemia, weight gain.',
      dosageRange: '3-12 mg daily (oral); IM depot varies',
      onsetOfAction: '1-2 weeks',
      peakTime: '24 hours',
      routes: ['Oral', 'IM depot'],
      interactions: ['CNS depressants', 'Carbamazepine'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning: 'Increased mortality in elderly dementia.',
      conditions: ['Schizophrenia', 'Schizoaffective disorder'],
      category: MedicationCategory.antipsychotics,
      addedDate: DateTime(2025, 4, 22),
    ),
    Medication(
      name: 'Lurasidone',
      brandNames: ['Latuda'],
      pronunciation: 'loo-RAS-i-done',
      drugClass: 'Atypical antipsychotic',
      halfLife: '18 hours',
      description: 'Atypical antipsychotic with less metabolic impact.',
      commonUses: 'Schizophrenia, bipolar depression.',
      sideEffects: 'Akathisia, somnolence, nausea.',
      dosageRange: '20-160 mg once daily (with food)',
      onsetOfAction: '1-2 weeks',
      peakTime: '1-3 hours',
      routes: ['Oral'],
      interactions: ['CYP3A4 inhibitors/inducers', 'Grapefruit'],
      pregnancyCategory: PregnancyCategory.b,
      blackBoxWarning:
          'Increased mortality in elderly dementia; suicidality in young adults.',
      conditions: ['Schizophrenia', 'Bipolar depression'],
      category: MedicationCategory.antipsychotics,
      addedDate: DateTime(2025, 4, 21),
    ),
    Medication(
      name: 'Cariprazine',
      brandNames: ['Vraylar'],
      pronunciation: 'kar-IP-ra-zeen',
      drugClass: 'Atypical antipsychotic',
      halfLife: '2-4 days (metabolites 1-3 weeks)',
      description: 'D3-preferring partial agonist atypical antipsychotic.',
      commonUses: 'Schizophrenia, bipolar disorder, bipolar depression.',
      sideEffects: 'Akathisia, EPS, insomnia.',
      dosageRange: '1.5-6 mg once daily',
      onsetOfAction: '1-2 weeks',
      peakTime: '3-6 hours',
      routes: ['Oral'],
      interactions: ['CYP3A4 inhibitors', 'Grapefruit'],
      pregnancyCategory: PregnancyCategory.n,
      blackBoxWarning: 'Increased mortality in elderly dementia.',
      conditions: ['Schizophrenia', 'Bipolar disorder', 'Bipolar depression'],
      category: MedicationCategory.antipsychotics,
      addedDate: DateTime(2025, 4, 20),
    ),
    Medication(
      name: 'Brexpiprazole',
      brandNames: ['Rexulti'],
      pronunciation: 'brex-PIP-ra-zole',
      drugClass: 'Atypical antipsychotic',
      halfLife: '91 hours',
      description: 'Serotonin-dopamine activity modulator.',
      commonUses: 'Schizophrenia, MDD adjunct.',
      sideEffects: 'Weight gain, akathisia, somnolence.',
      dosageRange: '1-4 mg once daily',
      onsetOfAction: '1-2 weeks',
      peakTime: '4 hours',
      routes: ['Oral'],
      interactions: ['CYP3A4/2D6 inhibitors'],
      pregnancyCategory: PregnancyCategory.n,
      blackBoxWarning: 'Increased mortality in elderly dementia.',
      conditions: ['Schizophrenia', 'Major depressive disorder (adjunct)'],
      category: MedicationCategory.antipsychotics,
      addedDate: DateTime(2025, 4, 19),
    ),

    // ─── IMMUNOSUPPRESSANTS ──────────────────────────────────────────────────
    Medication(
      name: 'Cyclosporine',
      brandNames: ['Sandimmune', 'Neoral', 'Gengraf'],
      pronunciation: 'sye-kloe-SPOR-een',
      drugClass: 'Calcineurin inhibitor',
      halfLife: '8-27 hours',
      description: 'Calcineurin inhibitor immunosuppressant.',
      commonUses: 'Transplant rejection prevention, autoimmune diseases.',
      sideEffects:
          'Nephrotoxicity, hypertension, gingival hyperplasia, hirsutism.',
      dosageRange: '2.5-15 mg/kg/day in divided doses',
      onsetOfAction: 'Days to weeks',
      peakTime: '1.5-2 hours',
      routes: ['Oral', 'IV', 'Ophthalmic'],
      interactions: ['Many CYP3A4 drugs', 'Statins', 'Grapefruit'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning: 'Nephrotoxicity, malignancy risk, serious infections.',
      conditions: [
        'Organ transplant',
        'Psoriasis',
        'Rheumatoid arthritis',
        'Dry eye'
      ],
      category: MedicationCategory.immunosuppressants,
      addedDate: DateTime(2025, 4, 18),
    ),
    Medication(
      name: 'Tacrolimus',
      brandNames: ['Prograf', 'Astagraf', 'Envarsus'],
      pronunciation: 'ta-KROE-li-mus',
      drugClass: 'Calcineurin inhibitor',
      halfLife: '8-12 hours',
      description: 'Potent calcineurin inhibitor.',
      commonUses: 'Organ transplant rejection prevention.',
      sideEffects: 'Nephrotoxicity, neurotoxicity, diabetes, hypertension.',
      dosageRange: '0.1-0.3 mg/kg/day divided',
      onsetOfAction: 'Days',
      peakTime: '1-3 hours',
      routes: ['Oral', 'IV', 'Topical'],
      interactions: ['Many CYP3A4 drugs', 'Grapefruit'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning:
          'Malignancy, serious infections, not interchangeable with ER forms.',
      conditions: ['Organ transplant', 'Atopic dermatitis (topical)'],
      category: MedicationCategory.immunosuppressants,
      addedDate: DateTime(2025, 4, 17),
    ),
    Medication(
      name: 'Mycophenolate',
      brandNames: ['CellCept', 'Myfortic'],
      pronunciation: 'mye-koe-FEN-oh-late',
      drugClass: 'Antiproliferative immunosuppressant',
      halfLife: '17 hours',
      description: 'Inhibits inosine monophosphate dehydrogenase.',
      commonUses: 'Organ transplant rejection prevention, lupus nephritis.',
      sideEffects: 'GI upset, bone marrow suppression, infections.',
      dosageRange: '500-1500 mg twice daily',
      onsetOfAction: 'Days to weeks',
      peakTime: '1-2 hours',
      routes: ['Oral', 'IV'],
      interactions: ['Antacids', 'Cholestyramine', 'Iron'],
      pregnancyCategory: PregnancyCategory.d,
      blackBoxWarning: 'Embryofetal toxicity, malignancy, serious infections.',
      conditions: ['Organ transplant', 'Lupus nephritis'],
      category: MedicationCategory.immunosuppressants,
      addedDate: DateTime(2025, 4, 16),
    ),
    Medication(
      name: 'Azathioprine',
      brandNames: ['Imuran', 'Azasan'],
      pronunciation: 'ay-za-THYE-oh-preen',
      drugClass: 'Antimetabolite',
      halfLife: '3-5 hours',
      description: 'Antimetabolite immunosuppressant.',
      commonUses: 'Transplant rejection, autoimmune diseases.',
      sideEffects: 'Bone marrow suppression, hepatotoxicity, infection.',
      dosageRange: '1-2.5 mg/kg daily',
      onsetOfAction: '6-8 weeks',
      peakTime: '1-2 hours',
      routes: ['Oral', 'IV'],
      interactions: ['Allopurinol', 'Warfarin', 'ACE inhibitors'],
      pregnancyCategory: PregnancyCategory.d,
      blackBoxWarning: 'Chronic immunosuppression may cause malignancies.',
      conditions: [
        'Transplant',
        'Rheumatoid arthritis',
        'IBD',
        'Autoimmune hepatitis'
      ],
      category: MedicationCategory.immunosuppressants,
      addedDate: DateTime(2025, 4, 15),
    ),
    Medication(
      name: 'Methotrexate',
      brandNames: ['Trexall', 'Rasuvo', 'Otrexup'],
      pronunciation: 'meth-oh-TREX-ate',
      drugClass: 'Folate antimetabolite',
      halfLife: '3-15 hours',
      description: 'Folate antagonist used for cancer and autoimmune diseases.',
      commonUses: 'Cancer, rheumatoid arthritis, psoriasis, ectopic pregnancy.',
      sideEffects:
          'Hepatotoxicity, pulmonary toxicity, bone marrow suppression.',
      dosageRange: '7.5-25 mg weekly (RA); higher for cancer',
      onsetOfAction: '4-8 weeks (RA)',
      peakTime: '1-2 hours',
      routes: ['Oral', 'IM', 'SC', 'IV', 'Intrathecal'],
      interactions: [
        'NSAIDs',
        'Penicillins',
        'TMP-SMX',
        'Proton pump inhibitors'
      ],
      pregnancyCategory: PregnancyCategory.x,
      blackBoxWarning:
          'Multiple toxicities; teratogen; requires close monitoring.',
      conditions: [
        'Rheumatoid arthritis',
        'Psoriasis',
        'Cancer',
        'Ectopic pregnancy'
      ],
      category: MedicationCategory.immunosuppressants,
      addedDate: DateTime(2025, 4, 14),
    ),
    Medication(
      name: 'Adalimumab',
      brandNames: ['Humira'],
      pronunciation: 'a-da-LIM-oo-mab',
      drugClass: 'TNF-alpha inhibitor (biologic)',
      halfLife: '10-20 days',
      description: 'Monoclonal antibody against TNF-alpha.',
      commonUses:
          'RA, psoriasis, Crohn\'s, ulcerative colitis, ankylosing spondylitis.',
      sideEffects:
          'Infections, lymphoma, injection reactions, demyelinating disorders.',
      dosageRange: '40 mg SC every other week',
      onsetOfAction: 'Weeks',
      peakTime: '131 hours',
      routes: ['SC'],
      interactions: ['Other biologics', 'Live vaccines'],
      pregnancyCategory: PregnancyCategory.b,
      blackBoxWarning:
          'Serious infections (TB, fungal, bacterial); malignancies.',
      conditions: [
        'Rheumatoid arthritis',
        'Psoriasis',
        'Crohn disease',
        'Ulcerative colitis'
      ],
      category: MedicationCategory.immunosuppressants,
      addedDate: DateTime(2025, 4, 13),
    ),
    Medication(
      name: 'Etanercept',
      brandNames: ['Enbrel'],
      pronunciation: 'ee-TAN-er-sept',
      drugClass: 'TNF-alpha inhibitor (biologic)',
      halfLife: '102 hours',
      description: 'Recombinant TNF receptor fusion protein.',
      commonUses: 'RA, psoriasis, ankylosing spondylitis, JIA.',
      sideEffects: 'Infections, injection reactions, neurologic events.',
      dosageRange: '50 mg SC weekly',
      onsetOfAction: '2-12 weeks',
      peakTime: '69-72 hours',
      routes: ['SC'],
      interactions: ['Anakinra', 'Abatacept', 'Live vaccines'],
      pregnancyCategory: PregnancyCategory.b,
      blackBoxWarning: 'Serious infections; lymphomas in children/adolescents.',
      conditions: [
        'Rheumatoid arthritis',
        'Psoriasis',
        'Ankylosing spondylitis'
      ],
      category: MedicationCategory.immunosuppressants,
      addedDate: DateTime(2025, 4, 12),
    ),
    Medication(
      name: 'Infliximab',
      brandNames: ['Remicade', 'Inflectra', 'Renflexis'],
      pronunciation: 'in-FLIX-i-mab',
      drugClass: 'TNF-alpha inhibitor (biologic)',
      halfLife: '8-10 days',
      description: 'Chimeric monoclonal antibody against TNF-alpha.',
      commonUses: 'Crohn\'s, ulcerative colitis, RA, psoriasis.',
      sideEffects: 'Infusion reactions, infections, lymphoma.',
      dosageRange: '3-10 mg/kg IV infusion',
      onsetOfAction: '2-4 weeks',
      peakTime: 'End of infusion',
      routes: ['IV'],
      interactions: ['Live vaccines', 'Other biologics'],
      pregnancyCategory: PregnancyCategory.b,
      blackBoxWarning:
          'Serious infections, malignancies, hepatosplenic T-cell lymphoma.',
      conditions: [
        'Crohn disease',
        'Ulcerative colitis',
        'Rheumatoid arthritis',
        'Psoriasis'
      ],
      category: MedicationCategory.immunosuppressants,
      addedDate: DateTime(2025, 4, 11),
    ),
    Medication(
      name: 'Rituximab',
      brandNames: ['Rituxan', 'Truxima', 'Ruxience'],
      pronunciation: 'ri-TUX-i-mab',
      drugClass: 'Anti-CD20 monoclonal antibody',
      halfLife: '22 days',
      description: 'Anti-CD20 B-cell depleting antibody.',
      commonUses: 'Non-Hodgkin lymphoma, CLL, RA, vasculitis.',
      sideEffects:
          'Infusion reactions, infections, PML, hepatitis B reactivation.',
      dosageRange: 'Varies by indication',
      onsetOfAction: 'Weeks',
      peakTime: 'End of infusion',
      routes: ['IV', 'SC'],
      interactions: ['Live vaccines', 'Other biologics'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning:
          'Fatal infusion reactions, severe mucocutaneous reactions, HBV reactivation, PML.',
      conditions: [
        'Lymphoma',
        'CLL',
        'Rheumatoid arthritis',
        'Vasculitis',
        'MS'
      ],
      category: MedicationCategory.immunosuppressants,
      addedDate: DateTime(2025, 4, 10),
    ),

    // ─── HORMONAL MEDICATIONS ────────────────────────────────────────────────
    Medication(
      name: 'Levothyroxine',
      brandNames: ['Synthroid', 'Levoxyl', 'Tirosint'],
      pronunciation: 'lee-voe-thye-ROX-een',
      drugClass: 'Thyroid hormone',
      halfLife: '6-7 days',
      description: 'Synthetic T4 thyroid hormone replacement.',
      commonUses: 'Hypothyroidism, thyroid cancer suppression.',
      sideEffects: 'Palpitations, weight loss, anxiety (if over-dosed).',
      dosageRange: '25-200 mcg once daily',
      onsetOfAction: '3-5 days',
      peakTime: '2-4 hours',
      routes: ['Oral', 'IV'],
      interactions: ['Calcium', 'Iron', 'PPIs', 'Bile acid sequestrants'],
      pregnancyCategory: PregnancyCategory.a,
      blackBoxWarning: 'Not for weight loss; toxic in euthyroid patients.',
      conditions: ['Hypothyroidism', 'Goiter', 'Thyroid cancer'],
      category: MedicationCategory.hormonal,
      addedDate: DateTime(2025, 4, 9),
    ),
    Medication(
      name: 'Prednisone',
      brandNames: ['Deltasone', 'Rayos'],
      pronunciation: 'PRED-ni-sone',
      drugClass: 'Corticosteroid',
      halfLife: '2-3 hours (biological 18-36 hours)',
      description: 'Synthetic oral corticosteroid.',
      commonUses:
          'Inflammation, autoimmune disease, allergic reactions, asthma.',
      sideEffects:
          'Weight gain, hyperglycemia, osteoporosis, immunosuppression.',
      dosageRange: '5-60 mg daily (taper for longer use)',
      onsetOfAction: '1-2 hours',
      peakTime: '1-2 hours',
      routes: ['Oral'],
      interactions: ['NSAIDs', 'Warfarin', 'Vaccines', 'Diabetic meds'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: [
        'Asthma',
        'Autoimmune diseases',
        'Allergic reactions',
        'Arthritis'
      ],
      category: MedicationCategory.hormonal,
      addedDate: DateTime(2025, 4, 8),
    ),
    Medication(
      name: 'Dexamethasone',
      brandNames: ['Decadron', 'Baycadron'],
      pronunciation: 'dex-a-METH-a-sone',
      drugClass: 'Corticosteroid (potent)',
      halfLife: '1.8-3.5 hours (biological 36-54 hours)',
      description: 'Potent long-acting corticosteroid.',
      commonUses: 'Cerebral edema, severe inflammation, chemo-induced nausea.',
      sideEffects: 'Hyperglycemia, mood changes, infections.',
      dosageRange: '0.5-20 mg daily',
      onsetOfAction: '1 hour',
      peakTime: '1-2 hours',
      routes: ['Oral', 'IV', 'IM', 'Ophthalmic'],
      interactions: ['NSAIDs', 'Warfarin', 'Vaccines'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: [
        'Cerebral edema',
        'Inflammation',
        'Asthma exacerbation',
        'Croup'
      ],
      category: MedicationCategory.hormonal,
      addedDate: DateTime(2025, 4, 7),
    ),
    Medication(
      name: 'Methylprednisolone',
      brandNames: ['Medrol', 'Solu-Medrol', 'Depo-Medrol'],
      pronunciation: 'meth-il-pred-NIS-oh-lone',
      drugClass: 'Corticosteroid',
      halfLife: '2-3 hours (biological 18-36 hours)',
      description: 'Intermediate-acting corticosteroid.',
      commonUses: 'Severe inflammation, autoimmune diseases, asthma.',
      sideEffects: 'Hyperglycemia, mood changes, infections.',
      dosageRange: '4-48 mg daily',
      onsetOfAction: '1-2 hours',
      peakTime: '1-2 hours',
      routes: ['Oral', 'IV', 'IM'],
      interactions: ['NSAIDs', 'Warfarin', 'Vaccines'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: [
        'Severe inflammation',
        'Asthma',
        'Multiple sclerosis',
        'Autoimmune disease'
      ],
      category: MedicationCategory.hormonal,
      addedDate: DateTime(2025, 4, 6),
    ),
    Medication(
      name: 'Hydrocortisone',
      brandNames: ['Cortef', 'Solu-Cortef'],
      pronunciation: 'hye-droe-KOR-ti-sone',
      drugClass: 'Corticosteroid',
      halfLife: '1-2 hours (biological 8-12 hours)',
      description: 'Short-acting glucocorticoid.',
      commonUses: 'Adrenal insufficiency, inflammation.',
      sideEffects: 'Adrenal suppression, infections, hyperglycemia.',
      dosageRange: '15-30 mg daily (physiological); higher for stress',
      onsetOfAction: '30 minutes',
      peakTime: '1-2 hours',
      routes: ['Oral', 'IV', 'Topical', 'Rectal'],
      interactions: ['NSAIDs', 'Warfarin', 'Vaccines'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Adrenal insufficiency', 'Inflammation', 'Shock'],
      category: MedicationCategory.hormonal,
      addedDate: DateTime(2025, 4, 5),
    ),
    Medication(
      name: 'Fludrocortisone',
      brandNames: ['Florinef'],
      pronunciation: 'floo-droe-KOR-ti-sone',
      drugClass: 'Mineralocorticoid',
      halfLife: '3.5 hours (biological 18-36 hours)',
      description: 'Synthetic mineralocorticoid.',
      commonUses: 'Adrenal insufficiency, orthostatic hypotension.',
      sideEffects: 'Fluid retention, hypertension, hypokalemia.',
      dosageRange: '0.05-0.2 mg daily',
      onsetOfAction: '2-4 hours',
      peakTime: '1-2 hours',
      routes: ['Oral'],
      interactions: ['Diuretics', 'Digoxin', 'Warfarin'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Addison disease', 'Orthostatic hypotension', 'CAH'],
      category: MedicationCategory.hormonal,
      addedDate: DateTime(2025, 4, 4),
    ),
    Medication(
      name: 'Estradiol',
      brandNames: ['Estrace', 'Climara', 'Vagifem'],
      pronunciation: 'es-tra-DYE-ole',
      drugClass: 'Estrogen',
      halfLife: '13-20 hours',
      description: 'Primary estrogen hormone.',
      commonUses: 'Menopausal symptoms, hypogonadism, osteoporosis prevention.',
      sideEffects: 'Thromboembolism, breast tenderness, increased cancer risk.',
      dosageRange: '0.5-2 mg daily (oral); varies patch',
      onsetOfAction: 'Days to weeks',
      peakTime: '2-6 hours',
      routes: ['Oral', 'Transdermal', 'Vaginal', 'IM'],
      interactions: ['CYP3A4 inducers', 'Thyroid hormones', 'Warfarin'],
      pregnancyCategory: PregnancyCategory.x,
      blackBoxWarning:
          'Increased risk of endometrial cancer, breast cancer, stroke, DVT.',
      conditions: [
        'Menopause',
        'Hypogonadism',
        'Osteoporosis',
        'Vaginal atrophy'
      ],
      category: MedicationCategory.hormonal,
      addedDate: DateTime(2025, 4, 3),
    ),
    Medication(
      name: 'Testosterone',
      brandNames: ['AndroGel', 'Testim', 'Depo-Testosterone'],
      pronunciation: 'tes-TOS-ter-one',
      drugClass: 'Androgen',
      halfLife: '10-100 minutes (varies by formulation)',
      description: 'Male hormone replacement.',
      commonUses: 'Hypogonadism, gender-affirming therapy.',
      sideEffects: 'Polycythemia, acne, sleep apnea, prostate effects.',
      dosageRange: 'Varies (50-400 mg IM every 2-4 weeks; transdermal daily)',
      onsetOfAction: 'Days to weeks',
      peakTime: 'Varies',
      routes: ['IM', 'Transdermal', 'Buccal', 'Subdermal'],
      interactions: ['Warfarin', 'Insulin', 'Corticosteroids'],
      pregnancyCategory: PregnancyCategory.x,
      schedule: ControlledSchedule.iii,
      blackBoxWarning:
          'Virilization in children exposed to transdermal products.',
      conditions: ['Hypogonadism', 'Gender dysphoria (off-label)'],
      category: MedicationCategory.hormonal,
      addedDate: DateTime(2025, 4, 2),
    ),
    Medication(
      name: 'Progesterone',
      brandNames: ['Prometrium', 'Crinone', 'Endometrin'],
      pronunciation: 'proe-JES-ter-one',
      drugClass: 'Progestin',
      halfLife: '5-20 hours',
      description: 'Natural progesterone.',
      commonUses: 'Menopausal HRT, amenorrhea, IVF support.',
      sideEffects: 'Drowsiness, dizziness, breast tenderness.',
      dosageRange: '100-400 mg daily',
      onsetOfAction: 'Hours',
      peakTime: '1-3 hours',
      routes: ['Oral', 'Vaginal', 'IM'],
      interactions: ['CYP3A4 inducers', 'Warfarin'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['Menopause', 'Amenorrhea', 'Assisted reproduction'],
      category: MedicationCategory.hormonal,
      addedDate: DateTime(2025, 4, 1),
    ),
    Medication(
      name: 'Finasteride',
      brandNames: ['Propecia', 'Proscar'],
      pronunciation: 'fi-NAS-ter-ide',
      drugClass: '5-alpha reductase inhibitor',
      halfLife: '5-8 hours',
      description: 'Inhibits conversion of testosterone to DHT.',
      commonUses: 'BPH, male pattern baldness.',
      sideEffects: 'Sexual dysfunction, depression, gynecomastia.',
      dosageRange: '1 mg daily (hair); 5 mg daily (BPH)',
      onsetOfAction: '3 months',
      peakTime: '1-2 hours',
      routes: ['Oral'],
      interactions: ['Minimal significant interactions'],
      pregnancyCategory: PregnancyCategory.x,
      conditions: ['BPH', 'Male pattern baldness'],
      category: MedicationCategory.hormonal,
      addedDate: DateTime(2025, 3, 31),
    ),
    Medication(
      name: 'Tamoxifen',
      brandNames: ['Nolvadex', 'Soltamox'],
      pronunciation: 'ta-MOX-i-fen',
      drugClass: 'SERM (selective estrogen receptor modulator)',
      halfLife: '5-7 days',
      description: 'Selective estrogen receptor modulator.',
      commonUses: 'Breast cancer (treatment and prevention).',
      sideEffects: 'Hot flashes, thromboembolism, endometrial cancer.',
      dosageRange: '20 mg daily',
      onsetOfAction: '4-10 weeks',
      peakTime: '3-7 hours',
      routes: ['Oral'],
      interactions: ['CYP2D6 inhibitors', 'Warfarin'],
      pregnancyCategory: PregnancyCategory.d,
      blackBoxWarning: 'Uterine malignancies, stroke, pulmonary embolism.',
      conditions: ['Breast cancer', 'Breast cancer prevention'],
      category: MedicationCategory.hormonal,
      addedDate: DateTime(2025, 3, 30),
    ),
    Medication(
      name: 'Letrozole',
      brandNames: ['Femara'],
      pronunciation: 'LET-roe-zole',
      drugClass: 'Aromatase inhibitor',
      halfLife: '2 days',
      description: 'Non-steroidal aromatase inhibitor.',
      commonUses: 'Postmenopausal breast cancer, fertility (off-label).',
      sideEffects: 'Hot flashes, osteoporosis, joint pain.',
      dosageRange: '2.5 mg daily',
      onsetOfAction: '2-6 weeks',
      peakTime: '1-2 hours',
      routes: ['Oral'],
      interactions: ['Tamoxifen', 'Estrogen'],
      pregnancyCategory: PregnancyCategory.x,
      conditions: ['Breast cancer', 'Ovulation induction'],
      category: MedicationCategory.hormonal,
      addedDate: DateTime(2025, 3, 29),
    ),
    Medication(
      name: 'Medroxyprogesterone',
      brandNames: ['Provera', 'Depo-Provera'],
      pronunciation: 'me-drox-ee-proe-JES-ter-one',
      drugClass: 'Progestin',
      halfLife: '30 days (depot); 12-17 hr oral',
      description: 'Synthetic progestin.',
      commonUses: 'Contraception, amenorrhea, abnormal uterine bleeding.',
      sideEffects: 'Weight gain, bone density loss, irregular bleeding.',
      dosageRange: '150 mg IM every 3 months; 5-10 mg oral',
      onsetOfAction: 'Days',
      peakTime: '3 weeks (depot)',
      routes: ['Oral', 'IM SC'],
      interactions: ['Aminoglutethimide', 'Rifampin'],
      pregnancyCategory: PregnancyCategory.x,
      blackBoxWarning: 'Bone mineral density loss with long-term use.',
      conditions: [
        'Contraception',
        'Amenorrhea',
        'Abnormal uterine bleeding',
        'Endometriosis'
      ],
      category: MedicationCategory.hormonal,
      addedDate: DateTime(2025, 3, 28),
    ),
    Medication(
      name: 'Desmopressin',
      brandNames: ['DDAVP', 'Stimate', 'Nocdurna'],
      pronunciation: 'des-moe-PRES-in',
      drugClass: 'Synthetic antidiuretic hormone',
      halfLife: '1.5-2.5 hours',
      description: 'Synthetic analog of vasopressin.',
      commonUses: 'Diabetes insipidus, enuresis, hemophilia A, vWD.',
      sideEffects: 'Hyponatremia, seizures (if over-hydrated), headache.',
      dosageRange: '0.1-1.2 mg daily (oral); varies by route',
      onsetOfAction: '30-60 minutes',
      peakTime: '1-5 hours',
      routes: ['Oral', 'Nasal', 'IV', 'SC', 'Sublingual'],
      interactions: ['SSRIs', 'NSAIDs', 'Carbamazepine'],
      pregnancyCategory: PregnancyCategory.b,
      blackBoxWarning: 'Hyponatremia risk; monitor fluid intake.',
      conditions: ['Diabetes insipidus', 'Enuresis', 'Hemophilia A', 'vWD'],
      category: MedicationCategory.hormonal,
      addedDate: DateTime(2025, 3, 27),
    ),
    // ─── ANTIVIRALS ──────────────────────────────────────────────────────────
    Medication(
      name: 'Acyclovir',
      brandNames: ['Zovirax'],
      pronunciation: 'ay-SYE-kloe-veer',
      drugClass: 'Nucleoside analog antiviral',
      halfLife: '2-3 hours',
      description: 'Antiviral for herpes infections.',
      commonUses: 'HSV, VZV, shingles.',
      sideEffects: 'Nausea, nephrotoxicity (IV), headache.',
      dosageRange: '200-800 mg 5×/day (oral); IV varies',
      onsetOfAction: '1-2 hours',
      peakTime: '1.5-2 hours',
      routes: ['Oral', 'IV', 'Topical'],
      interactions: ['Probenecid', 'Mycophenolate'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['HSV', 'Shingles', 'Chickenpox', 'Cold sores'],
      category: MedicationCategory.antivirals,
      addedDate: DateTime(2025, 3, 26),
    ),
    Medication(
      name: 'Valacyclovir',
      brandNames: ['Valtrex'],
      pronunciation: 'val-ay-SYE-kloe-veer',
      drugClass: 'Nucleoside analog (prodrug of acyclovir)',
      halfLife: '2.5-3.3 hours',
      description: 'Prodrug of acyclovir with better bioavailability.',
      commonUses: 'HSV, shingles, genital herpes suppression.',
      sideEffects: 'Nausea, headache, TTP/HUS (rare in immunocompromised).',
      dosageRange: '500-1000 mg 1-3×/day',
      onsetOfAction: '1-2 hours',
      peakTime: '1.5 hours',
      routes: ['Oral'],
      interactions: ['Probenecid', 'Cimetidine'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['HSV', 'Shingles', 'Genital herpes'],
      category: MedicationCategory.antivirals,
      addedDate: DateTime(2025, 3, 25),
    ),
    Medication(
      name: 'Oseltamivir',
      brandNames: ['Tamiflu'],
      pronunciation: 'oh-sel-TAM-i-veer',
      drugClass: 'Neuraminidase inhibitor',
      halfLife: '6-10 hours',
      description: 'Antiviral for influenza A and B.',
      commonUses: 'Influenza treatment and prophylaxis.',
      sideEffects: 'Nausea, vomiting, neuropsychiatric events (rare).',
      dosageRange: '75 mg twice daily × 5 days',
      onsetOfAction: '1-2 hours',
      peakTime: '3-4 hours',
      routes: ['Oral'],
      interactions: ['Live influenza vaccine'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Influenza', 'Flu prophylaxis'],
      category: MedicationCategory.antivirals,
      addedDate: DateTime(2025, 3, 24),
    ),
    Medication(
      name: 'Remdesivir',
      brandNames: ['Veklury'],
      pronunciation: 'rem-DES-i-veer',
      drugClass: 'RNA polymerase inhibitor',
      halfLife: '1 hour',
      description: 'Antiviral approved for COVID-19.',
      commonUses: 'COVID-19 hospitalized or at-risk patients.',
      sideEffects: 'Infusion reactions, hepatotoxicity, bradycardia.',
      dosageRange: '200 mg IV day 1, then 100 mg daily × 4-9 days',
      onsetOfAction: 'Hours',
      peakTime: 'End of infusion',
      routes: ['IV'],
      interactions: ['Chloroquine', 'Hydroxychloroquine'],
      pregnancyCategory: PregnancyCategory.n,
      conditions: ['COVID-19'],
      category: MedicationCategory.antivirals,
      addedDate: DateTime(2025, 3, 23),
    ),
    Medication(
      name: 'Tenofovir',
      brandNames: ['Viread', 'Vemlidy'],
      pronunciation: 'te-NOE-foh-veer',
      drugClass: 'Nucleotide reverse transcriptase inhibitor',
      halfLife: '12-18 hours',
      description: 'NRTI for HIV and hepatitis B.',
      commonUses: 'HIV, HBV infection, PrEP.',
      sideEffects: 'Nephrotoxicity, bone loss, lactic acidosis.',
      dosageRange: '300 mg once daily (TDF); 25 mg once daily (TAF)',
      onsetOfAction: 'Days',
      peakTime: '1-2 hours',
      routes: ['Oral'],
      interactions: ['NSAIDs', 'Other nephrotoxins'],
      pregnancyCategory: PregnancyCategory.b,
      blackBoxWarning:
          'Lactic acidosis, severe hepatomegaly, hepatitis flare on discontinuation.',
      conditions: ['HIV', 'Hepatitis B', 'PrEP'],
      category: MedicationCategory.antivirals,
      addedDate: DateTime(2025, 3, 22),
    ),
    Medication(
      name: 'Efavirenz',
      brandNames: ['Sustiva'],
      pronunciation: 'e-FAV-er-enz',
      drugClass: 'NNRTI',
      halfLife: '40-55 hours',
      description: 'Non-nucleoside reverse transcriptase inhibitor.',
      commonUses: 'HIV-1 infection.',
      sideEffects: 'CNS effects (vivid dreams), rash, hepatotoxicity.',
      dosageRange: '600 mg once daily',
      onsetOfAction: 'Days',
      peakTime: '3-5 hours',
      routes: ['Oral'],
      interactions: ['Many CYP3A4 drugs', 'Methadone', 'OCPs'],
      pregnancyCategory: PregnancyCategory.d,
      conditions: ['HIV'],
      category: MedicationCategory.antivirals,
      addedDate: DateTime(2025, 3, 21),
    ),
    Medication(
      name: 'Emtricitabine',
      brandNames: ['Emtriva'],
      pronunciation: 'em-trye-SYE-ta-been',
      drugClass: 'NRTI',
      halfLife: '10 hours',
      description: 'NRTI for HIV treatment and prevention.',
      commonUses: 'HIV, PrEP (combination with tenofovir).',
      sideEffects: 'Headache, nausea, hyperpigmentation.',
      dosageRange: '200 mg once daily',
      onsetOfAction: 'Days',
      peakTime: '1-2 hours',
      routes: ['Oral'],
      interactions: ['Other NRTIs'],
      pregnancyCategory: PregnancyCategory.b,
      blackBoxWarning:
          'Lactic acidosis, hepatomegaly, hepatitis exacerbation in HBV.',
      conditions: ['HIV', 'PrEP'],
      category: MedicationCategory.antivirals,
      addedDate: DateTime(2025, 3, 20),
    ),
    Medication(
      name: 'Dolutegravir',
      brandNames: ['Tivicay', 'Dovato'],
      pronunciation: 'doe-loo-TEG-ra-veer',
      drugClass: 'HIV integrase inhibitor',
      halfLife: '14 hours',
      description: 'Integrase strand transfer inhibitor.',
      commonUses: 'HIV-1 infection.',
      sideEffects: 'Insomnia, headache, hepatotoxicity.',
      dosageRange: '50 mg once or twice daily',
      onsetOfAction: 'Days',
      peakTime: '2-3 hours',
      routes: ['Oral'],
      interactions: ['Metformin', 'Antacids', 'Carbamazepine', 'Rifampin'],
      pregnancyCategory: PregnancyCategory.n,
      conditions: ['HIV'],
      category: MedicationCategory.antivirals,
      addedDate: DateTime(2025, 3, 19),
    ),
    Medication(
      name: 'Sofosbuvir',
      brandNames: ['Sovaldi', 'Epclusa'],
      pronunciation: 'soe-FOS-bue-veer',
      drugClass: 'HCV NS5B polymerase inhibitor',
      halfLife: '0.5 hours (metabolite 27 hours)',
      description: 'Direct-acting antiviral for hepatitis C.',
      commonUses: 'Chronic hepatitis C (with other DAAs).',
      sideEffects: 'Fatigue, headache, nausea.',
      dosageRange: '400 mg once daily × 12-24 weeks',
      onsetOfAction: 'Weeks',
      peakTime: '0.5-2 hours',
      routes: ['Oral'],
      interactions: ['Amiodarone', 'P-gp inducers', 'Rifampin'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['Hepatitis C'],
      category: MedicationCategory.antivirals,
      addedDate: DateTime(2025, 3, 18),
    ),
    Medication(
      name: 'Ritonavir',
      brandNames: ['Norvir'],
      pronunciation: 'ri-TOE-na-veer',
      drugClass: 'HIV protease inhibitor / booster',
      halfLife: '3-5 hours',
      description: 'Protease inhibitor used as pharmacokinetic enhancer.',
      commonUses: 'HIV (boosting other PIs), COVID-19 (in Paxlovid).',
      sideEffects: 'GI upset, taste disturbance, hyperlipidemia.',
      dosageRange: '100-600 mg daily',
      onsetOfAction: 'Hours',
      peakTime: '2-4 hours',
      routes: ['Oral'],
      interactions: ['Extensive - many CYP3A4 drugs'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['HIV', 'COVID-19 (combo)'],
      category: MedicationCategory.antivirals,
      addedDate: DateTime(2025, 3, 17),
    ),
    Medication(
      name: 'Nirmatrelvir/Ritonavir',
      brandNames: ['Paxlovid'],
      pronunciation: 'nir-ma-TREL-veer / ri-TOE-na-veer',
      drugClass: 'SARS-CoV-2 protease inhibitor',
      halfLife: '7 hours',
      description: 'Oral COVID-19 protease inhibitor combination.',
      commonUses: 'Mild-moderate COVID-19 in high-risk patients.',
      sideEffects: 'Dysgeusia, diarrhea, hypertension.',
      dosageRange: '300/100 mg twice daily × 5 days',
      onsetOfAction: 'Hours',
      peakTime: '3 hours',
      routes: ['Oral'],
      interactions: ['Extensive - CYP3A4 drugs; review all meds'],
      pregnancyCategory: PregnancyCategory.n,
      conditions: ['COVID-19'],
      category: MedicationCategory.antivirals,
      addedDate: DateTime(2025, 3, 16),
    ),
    Medication(
      name: 'Ganciclovir',
      brandNames: ['Cytovene', 'Zirgan'],
      pronunciation: 'gan-SYE-kloe-veer',
      drugClass: 'Nucleoside analog antiviral',
      halfLife: '2.5-3.6 hours',
      description: 'Antiviral for CMV infection.',
      commonUses: 'CMV retinitis, CMV prophylaxis in transplant.',
      sideEffects: 'Bone marrow suppression, nephrotoxicity, carcinogenicity.',
      dosageRange: '5 mg/kg IV every 12 hours (induction)',
      onsetOfAction: 'Hours',
      peakTime: 'End of infusion',
      routes: ['IV', 'Ophthalmic', 'Oral (valganciclovir prodrug)'],
      interactions: ['Zidovudine', 'Imipenem', 'Mycophenolate'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning:
          'Hematologic toxicity, impaired fertility, teratogenicity.',
      conditions: ['CMV infection', 'Transplant CMV prophylaxis'],
      category: MedicationCategory.antivirals,
      addedDate: DateTime(2025, 3, 15),
    ),

    // ─── ANTIFUNGALS ─────────────────────────────────────────────────────────
    Medication(
      name: 'Fluconazole',
      brandNames: ['Diflucan'],
      pronunciation: 'floo-KON-a-zole',
      drugClass: 'Triazole antifungal',
      halfLife: '30 hours',
      description: 'Triazole antifungal with broad activity.',
      commonUses: 'Candidiasis, cryptococcal meningitis.',
      sideEffects: 'Hepatotoxicity, QT prolongation, rash.',
      dosageRange: '100-800 mg daily',
      onsetOfAction: '1-2 hours',
      peakTime: '1-2 hours',
      routes: ['Oral', 'IV'],
      interactions: [
        'Warfarin',
        'Sulfonylureas',
        'Phenytoin',
        'Many CYP substrates'
      ],
      pregnancyCategory: PregnancyCategory.d,
      conditions: [
        'Vaginal yeast',
        'Thrush',
        'Cryptococcal meningitis',
        'Systemic candidiasis'
      ],
      category: MedicationCategory.antifungals,
      addedDate: DateTime(2025, 3, 14),
    ),
    Medication(
      name: 'Itraconazole',
      brandNames: ['Sporanox', 'Tolsura'],
      pronunciation: 'it-ra-KON-a-zole',
      drugClass: 'Triazole antifungal',
      halfLife: '21 hours (with repeat dosing, 64 hours)',
      description: 'Triazole for systemic fungal infections.',
      commonUses: 'Aspergillosis, histoplasmosis, blastomycosis.',
      sideEffects: 'Heart failure, hepatotoxicity, QT prolongation.',
      dosageRange: '100-400 mg daily',
      onsetOfAction: 'Hours to days',
      peakTime: '2-5 hours',
      routes: ['Oral', 'IV'],
      interactions: ['Many CYP3A4 substrates'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning: 'Do not use in CHF; hepatotoxicity; QT effects.',
      conditions: ['Aspergillosis', 'Histoplasmosis', 'Onychomycosis'],
      category: MedicationCategory.antifungals,
      addedDate: DateTime(2025, 3, 13),
    ),
    Medication(
      name: 'Voriconazole',
      brandNames: ['Vfend'],
      pronunciation: 'vor-i-KON-a-zole',
      drugClass: 'Triazole antifungal',
      halfLife: '6-12 hours',
      description: 'Broad-spectrum triazole.',
      commonUses: 'Invasive aspergillosis, Candida infections.',
      sideEffects:
          'Visual disturbances, hepatotoxicity, photosensitivity, skin cancer.',
      dosageRange: '200-300 mg twice daily',
      onsetOfAction: 'Hours',
      peakTime: '1-2 hours',
      routes: ['Oral', 'IV'],
      interactions: ['Extensive CYP2C19, CYP3A4 interactions'],
      pregnancyCategory: PregnancyCategory.d,
      conditions: ['Invasive aspergillosis', 'Systemic candidiasis'],
      category: MedicationCategory.antifungals,
      addedDate: DateTime(2025, 3, 12),
    ),
    Medication(
      name: 'Posaconazole',
      brandNames: ['Noxafil'],
      pronunciation: 'poe-sa-KON-a-zole',
      drugClass: 'Triazole antifungal',
      halfLife: '35 hours',
      description: 'Broad-spectrum triazole.',
      commonUses: 'Invasive fungal prophylaxis in immunocompromised.',
      sideEffects: 'GI upset, hepatotoxicity, QT prolongation.',
      dosageRange: '300 mg daily (tablet)',
      onsetOfAction: 'Hours to days',
      peakTime: '3-5 hours',
      routes: ['Oral', 'IV'],
      interactions: ['Many CYP3A4 drugs'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Fungal prophylaxis', 'Aspergillosis', 'Zygomycosis'],
      category: MedicationCategory.antifungals,
      addedDate: DateTime(2025, 3, 11),
    ),
    Medication(
      name: 'Amphotericin B',
      brandNames: ['Ambisome', 'Abelcet'],
      pronunciation: 'am-foe-TER-i-sin bee',
      drugClass: 'Polyene antifungal',
      halfLife: '24 hours (conventional); 100+ hours (liposomal)',
      description: 'Potent antifungal for severe systemic infections.',
      commonUses: 'Severe systemic fungal infections.',
      sideEffects:
          'Nephrotoxicity, infusion reactions, electrolyte disturbances.',
      dosageRange: '0.25-1.5 mg/kg IV daily',
      onsetOfAction: 'Hours',
      peakTime: 'End of infusion',
      routes: ['IV'],
      interactions: ['Nephrotoxins', 'Digoxin', 'Corticosteroids'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: [
        'Invasive fungal infections',
        'Cryptococcosis',
        'Leishmaniasis'
      ],
      category: MedicationCategory.antifungals,
      addedDate: DateTime(2025, 3, 10),
    ),
    Medication(
      name: 'Terbinafine',
      brandNames: ['Lamisil'],
      pronunciation: 'TER-bin-a-feen',
      drugClass: 'Allylamine antifungal',
      halfLife: '36 hours',
      description: 'Allylamine antifungal.',
      commonUses: 'Onychomycosis, tinea infections.',
      sideEffects: 'Hepatotoxicity, taste disturbance, neutropenia.',
      dosageRange: '250 mg once daily × 6-12 weeks',
      onsetOfAction: 'Weeks',
      peakTime: '2 hours',
      routes: ['Oral', 'Topical'],
      interactions: ['CYP2D6 substrates', 'Warfarin', 'Caffeine'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['Onychomycosis', 'Ringworm', 'Athlete foot'],
      category: MedicationCategory.antifungals,
      addedDate: DateTime(2025, 3, 9),
    ),
    Medication(
      name: 'Nystatin',
      brandNames: ['Mycostatin', 'Nystop'],
      pronunciation: 'nye-STAT-in',
      drugClass: 'Polyene antifungal',
      halfLife: 'Not systemically absorbed',
      description: 'Topical/oral antifungal (not systemically absorbed).',
      commonUses: 'Oral thrush, cutaneous candidiasis.',
      sideEffects: 'GI upset (oral), local irritation (topical).',
      dosageRange: '4-6 mL swish/swallow 4×/day (oral)',
      onsetOfAction: '24-72 hours',
      peakTime: 'N/A (local effect)',
      routes: ['Oral', 'Topical', 'Vaginal'],
      interactions: ['Minimal'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Oral thrush', 'Diaper candidiasis', 'Vaginal candidiasis'],
      category: MedicationCategory.antifungals,
      addedDate: DateTime(2025, 3, 8),
    ),
    Medication(
      name: 'Caspofungin',
      brandNames: ['Cancidas'],
      pronunciation: 'kas-po-FUN-jin',
      drugClass: 'Echinocandin antifungal',
      halfLife: '9-11 hours',
      description: 'Echinocandin antifungal.',
      commonUses: 'Invasive candidiasis, aspergillosis.',
      sideEffects: 'Infusion reactions, hepatic effects.',
      dosageRange: '70 mg IV load, then 50 mg daily',
      onsetOfAction: 'Hours',
      peakTime: 'End of infusion',
      routes: ['IV'],
      interactions: ['Cyclosporine', 'Rifampin'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Invasive candidiasis', 'Aspergillosis'],
      category: MedicationCategory.antifungals,
      addedDate: DateTime(2025, 3, 7),
    ),
    Medication(
      name: 'Clotrimazole',
      brandNames: ['Lotrimin', 'Mycelex', 'Canesten'],
      pronunciation: 'kloe-TRIM-a-zole',
      drugClass: 'Imidazole antifungal',
      halfLife: '3.5-5 hours',
      description: 'Topical/troche imidazole antifungal.',
      commonUses: 'Tinea pedis, cruris, corporis, oral thrush.',
      sideEffects: 'Local irritation, mild GI upset (troche).',
      dosageRange: '1 troche 5×/day × 14 days (oral); topical as directed',
      onsetOfAction: 'Days',
      peakTime: 'N/A (local)',
      routes: ['Topical', 'Vaginal', 'Troche'],
      interactions: ['Minimal for topical'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Tinea', 'Oral thrush', 'Vaginal candidiasis'],
      category: MedicationCategory.antifungals,
      addedDate: DateTime(2025, 3, 6),
    ),

    // ─── MUSCLE RELAXANTS ────────────────────────────────────────────────────
    Medication(
      name: 'Cyclobenzaprine',
      brandNames: ['Flexeril', 'Amrix'],
      pronunciation: 'sye-kloe-BEN-za-preen',
      drugClass: 'Centrally-acting muscle relaxant',
      halfLife: '18 hours',
      description: 'Tricyclic-related muscle relaxant.',
      commonUses: 'Musculoskeletal muscle spasms.',
      sideEffects: 'Drowsiness, dry mouth, anticholinergic effects.',
      dosageRange: '5-10 mg 3×/day (max 2-3 weeks)',
      onsetOfAction: '1 hour',
      peakTime: '3-4 hours',
      routes: ['Oral'],
      interactions: ['MAOIs', 'CNS depressants', 'Anticholinergics'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['Muscle spasm', 'Back pain'],
      category: MedicationCategory.muscleRelaxants,
      addedDate: DateTime(2025, 3, 5),
    ),
    Medication(
      name: 'Baclofen',
      brandNames: ['Lioresal', 'Gablofen', 'Ozobax'],
      pronunciation: 'BAK-loe-fen',
      drugClass: 'GABA-B agonist muscle relaxant',
      halfLife: '2-4 hours',
      description: 'GABA-B receptor agonist.',
      commonUses: 'Spasticity (MS, SCI), alcohol use disorder (off-label).',
      sideEffects:
          'Drowsiness, dizziness, withdrawal syndrome if stopped abruptly.',
      dosageRange: '5-80 mg daily in divided doses',
      onsetOfAction: '1 hour',
      peakTime: '2-3 hours',
      routes: ['Oral', 'Intrathecal'],
      interactions: ['CNS depressants', 'Alcohol'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning:
          'Abrupt intrathecal discontinuation causes severe withdrawal (life-threatening).',
      conditions: ['MS spasticity', 'Spinal cord injury', 'Hiccups'],
      category: MedicationCategory.muscleRelaxants,
      addedDate: DateTime(2025, 3, 4),
    ),
    Medication(
      name: 'Tizanidine',
      brandNames: ['Zanaflex'],
      pronunciation: 'tye-ZAN-i-deen',
      drugClass: 'Alpha-2 agonist muscle relaxant',
      halfLife: '2.5 hours',
      description: 'Central alpha-2 agonist.',
      commonUses: 'Spasticity.',
      sideEffects: 'Hypotension, sedation, dry mouth, hepatotoxicity.',
      dosageRange: '2-36 mg daily in divided doses',
      onsetOfAction: '1 hour',
      peakTime: '1-2 hours',
      routes: ['Oral'],
      interactions: ['Ciprofloxacin', 'Fluvoxamine', 'Alcohol'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Spasticity', 'MS spasticity'],
      category: MedicationCategory.muscleRelaxants,
      addedDate: DateTime(2025, 3, 3),
    ),
    Medication(
      name: 'Methocarbamol',
      brandNames: ['Robaxin'],
      pronunciation: 'meth-oh-KAR-ba-mol',
      drugClass: 'Centrally-acting muscle relaxant',
      halfLife: '1-2 hours',
      description: 'Carbamate muscle relaxant.',
      commonUses: 'Acute musculoskeletal pain.',
      sideEffects: 'Drowsiness, dizziness, rash.',
      dosageRange: '1500 mg 4×/day initially',
      onsetOfAction: '30 minutes',
      peakTime: '1-2 hours',
      routes: ['Oral', 'IV', 'IM'],
      interactions: ['CNS depressants'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Muscle spasm', 'Acute back pain'],
      category: MedicationCategory.muscleRelaxants,
      addedDate: DateTime(2025, 3, 2),
    ),
    Medication(
      name: 'Carisoprodol',
      brandNames: ['Soma'],
      pronunciation: 'kar-eye-soe-PROE-dol',
      drugClass: 'Centrally-acting muscle relaxant',
      halfLife: '2 hours (metabolite meprobamate 10 hours)',
      description: 'Muscle relaxant metabolized to meprobamate.',
      commonUses: 'Musculoskeletal pain (short-term).',
      sideEffects: 'Dependence, drowsiness, dizziness.',
      dosageRange: '250-350 mg 3×/day',
      onsetOfAction: '30 minutes',
      peakTime: '1.5-2 hours',
      routes: ['Oral'],
      interactions: ['CNS depressants', 'Alcohol'],
      pregnancyCategory: PregnancyCategory.c,
      schedule: ControlledSchedule.iv,
      conditions: ['Muscle spasm', 'Back pain'],
      category: MedicationCategory.muscleRelaxants,
      addedDate: DateTime(2025, 3, 1),
    ),

    // ─── RESPIRATORY ─────────────────────────────────────────────────────────
    Medication(
      name: 'Albuterol',
      brandNames: ['ProAir', 'Ventolin', 'Proventil'],
      pronunciation: 'al-BYOO-ter-ol',
      drugClass: 'Short-acting beta-2 agonist (SABA)',
      halfLife: '3-6 hours',
      description: 'Rescue bronchodilator.',
      commonUses: 'Asthma, COPD exacerbations.',
      sideEffects: 'Tremor, tachycardia, anxiety, hypokalemia.',
      dosageRange: '90 mcg/puff, 1-2 puffs every 4-6 hours',
      onsetOfAction: '5-15 minutes',
      peakTime: '60-90 minutes',
      routes: ['Inhalation', 'Nebulizer', 'Oral'],
      interactions: ['Beta-blockers', 'Digoxin', 'Diuretics'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Asthma', 'COPD', 'Bronchospasm'],
      category: MedicationCategory.respiratory,
      addedDate: DateTime(2025, 2, 28),
    ),
    Medication(
      name: 'Ipratropium',
      brandNames: ['Atrovent'],
      pronunciation: 'i-pra-TROE-pee-um',
      drugClass: 'Anticholinergic bronchodilator',
      halfLife: '2 hours',
      description: 'Short-acting muscarinic antagonist.',
      commonUses: 'COPD, asthma (adjunct).',
      sideEffects: 'Dry mouth, cough, urinary retention.',
      dosageRange: '17 mcg/puff, 2 puffs 4×/day',
      onsetOfAction: '15 minutes',
      peakTime: '1-2 hours',
      routes: ['Inhalation', 'Nasal'],
      interactions: ['Anticholinergics'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['COPD', 'Asthma', 'Rhinitis'],
      category: MedicationCategory.respiratory,
      addedDate: DateTime(2025, 2, 27),
    ),
    Medication(
      name: 'Tiotropium',
      brandNames: ['Spiriva', 'Spiriva Respimat'],
      pronunciation: 'tye-oh-TROE-pee-um',
      drugClass: 'Long-acting muscarinic antagonist (LAMA)',
      halfLife: '25 hours',
      description: 'Once-daily long-acting anticholinergic.',
      commonUses: 'COPD, asthma.',
      sideEffects: 'Dry mouth, urinary retention, glaucoma.',
      dosageRange: '18 mcg once daily',
      onsetOfAction: '30 minutes',
      peakTime: '1-4 hours',
      routes: ['Inhalation'],
      interactions: ['Anticholinergics'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['COPD', 'Asthma'],
      category: MedicationCategory.respiratory,
      addedDate: DateTime(2025, 2, 26),
    ),
    Medication(
      name: 'Fluticasone',
      brandNames: ['Flonase', 'Flovent', 'Cutivate'],
      pronunciation: 'floo-TIK-a-sone',
      drugClass: 'Inhaled corticosteroid',
      halfLife: '8 hours',
      description: 'Topical and inhaled corticosteroid.',
      commonUses: 'Asthma, allergic rhinitis.',
      sideEffects:
          'Thrush, dysphonia, epistaxis (nasal), growth effects in children.',
      dosageRange: '44-220 mcg 2×/day (inhaled); 50-100 mcg/spray (nasal)',
      onsetOfAction: '24 hours (asthma); days (rhinitis)',
      peakTime: '1-2 weeks',
      routes: ['Inhalation', 'Nasal', 'Topical'],
      interactions: ['CYP3A4 inhibitors (ritonavir)'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Asthma', 'Allergic rhinitis', 'Eczema'],
      category: MedicationCategory.respiratory,
      addedDate: DateTime(2025, 2, 25),
    ),
    Medication(
      name: 'Budesonide',
      brandNames: ['Pulmicort', 'Rhinocort', 'Entocort'],
      pronunciation: 'byoo-DES-oh-nide',
      drugClass: 'Inhaled/oral corticosteroid',
      halfLife: '2-3 hours',
      description: 'Inhaled corticosteroid with oral formulation for IBD.',
      commonUses: 'Asthma, Crohn\'s disease, allergic rhinitis.',
      sideEffects: 'Thrush, adrenal suppression, growth effects.',
      dosageRange: '180-800 mcg 2×/day (inhaled); 9 mg daily (Crohn)',
      onsetOfAction: '24 hours',
      peakTime: '2 hours',
      routes: ['Inhalation', 'Nasal', 'Oral'],
      interactions: ['CYP3A4 inhibitors'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['Asthma', 'Crohn disease', 'Allergic rhinitis'],
      category: MedicationCategory.respiratory,
      addedDate: DateTime(2025, 2, 24),
    ),
    Medication(
      name: 'Montelukast',
      brandNames: ['Singulair'],
      pronunciation: 'mon-te-LOO-kast',
      drugClass: 'Leukotriene receptor antagonist',
      halfLife: '2.7-5.5 hours',
      description: 'Leukotriene receptor antagonist.',
      commonUses: 'Asthma, allergic rhinitis, exercise-induced bronchospasm.',
      sideEffects: 'Neuropsychiatric events (boxed warning), headache.',
      dosageRange: '10 mg once daily (adults)',
      onsetOfAction: '3-4 hours',
      peakTime: '3-4 hours',
      routes: ['Oral'],
      interactions: ['Phenobarbital', 'Rifampin'],
      pregnancyCategory: PregnancyCategory.b,
      blackBoxWarning:
          'Serious neuropsychiatric events including suicidal ideation.',
      conditions: ['Asthma', 'Allergic rhinitis', 'Exercise-induced asthma'],
      category: MedicationCategory.respiratory,
      addedDate: DateTime(2025, 2, 23),
    ),
    Medication(
      name: 'Salmeterol',
      brandNames: ['Serevent'],
      pronunciation: 'sal-ME-ter-ol',
      drugClass: 'Long-acting beta-2 agonist (LABA)',
      halfLife: '5.5 hours',
      description: 'Long-acting beta-2 agonist.',
      commonUses: 'Asthma (with ICS), COPD.',
      sideEffects: 'Tremor, tachycardia, palpitations.',
      dosageRange: '50 mcg twice daily',
      onsetOfAction: '15-20 minutes',
      peakTime: '3-4 hours',
      routes: ['Inhalation'],
      interactions: ['Beta-blockers', 'MAOIs', 'TCAs'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning:
          'Asthma-related deaths without ICS; not for monotherapy.',
      conditions: ['Asthma (with ICS)', 'COPD'],
      category: MedicationCategory.respiratory,
      addedDate: DateTime(2025, 2, 22),
    ),
    Medication(
      name: 'Advair',
      brandNames: ['Advair Diskus', 'Advair HFA'],
      pronunciation: 'AD-vair',
      drugClass: 'ICS + LABA combination',
      halfLife: 'Fluticasone 8 hr; salmeterol 5.5 hr',
      description: 'Combination fluticasone + salmeterol.',
      commonUses: 'Asthma, COPD.',
      sideEffects: 'Thrush, tremor, palpitations.',
      dosageRange: '1 inhalation 2×/day',
      onsetOfAction: '15-30 minutes',
      peakTime: '2-3 hours',
      routes: ['Inhalation'],
      interactions: ['CYP3A4 inhibitors', 'Beta-blockers'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Asthma', 'COPD'],
      category: MedicationCategory.respiratory,
      addedDate: DateTime(2025, 2, 21),
    ),
    Medication(
      name: 'Theophylline',
      brandNames: ['Theo-24', 'Elixophyllin'],
      pronunciation: 'thee-OFF-i-lin',
      drugClass: 'Methylxanthine bronchodilator',
      halfLife: '3-13 hours',
      description: 'Methylxanthine bronchodilator.',
      commonUses: 'Asthma, COPD (adjunct).',
      sideEffects:
          'Narrow therapeutic window, tachycardia, seizures (toxic levels).',
      dosageRange: '300-600 mg daily (adjust to serum levels)',
      onsetOfAction: 'Hours',
      peakTime: '1-2 hours',
      routes: ['Oral', 'IV'],
      interactions: ['Ciprofloxacin', 'Erythromycin', 'Smoking'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Asthma', 'COPD'],
      category: MedicationCategory.respiratory,
      addedDate: DateTime(2025, 2, 20),
    ),

    // ─── CARDIOVASCULAR ──────────────────────────────────────────────────────
    Medication(
      name: 'Atorvastatin',
      brandNames: ['Lipitor'],
      pronunciation: 'a-TOR-va-sta-tin',
      drugClass: 'HMG-CoA reductase inhibitor (statin)',
      halfLife: '14 hours',
      description: 'HMG-CoA reductase inhibitor.',
      commonUses: 'Hyperlipidemia, cardiovascular disease prevention.',
      sideEffects: 'Myalgia, rhabdomyolysis, hepatotoxicity.',
      dosageRange: '10-80 mg once daily',
      onsetOfAction: '2 weeks',
      peakTime: '1-2 hours',
      routes: ['Oral'],
      interactions: ['Gemfibrozil', 'CYP3A4 inhibitors', 'Grapefruit'],
      pregnancyCategory: PregnancyCategory.x,
      conditions: ['High cholesterol', 'CAD prevention', 'Stroke prevention'],
      category: MedicationCategory.cardiovascular,
      addedDate: DateTime(2025, 2, 19),
    ),
    Medication(
      name: 'Simvastatin',
      brandNames: ['Zocor'],
      pronunciation: 'SIM-va-sta-tin',
      drugClass: 'Statin',
      halfLife: '2 hours',
      description: 'HMG-CoA reductase inhibitor.',
      commonUses: 'Hyperlipidemia, cardiovascular prevention.',
      sideEffects: 'Myalgia, rhabdomyolysis, hepatotoxicity.',
      dosageRange: '5-40 mg at bedtime',
      onsetOfAction: '2 weeks',
      peakTime: '1-2 hours',
      routes: ['Oral'],
      interactions: ['CYP3A4 inhibitors', 'Amlodipine', 'Grapefruit'],
      pregnancyCategory: PregnancyCategory.x,
      conditions: ['High cholesterol', 'CAD prevention'],
      category: MedicationCategory.cardiovascular,
      addedDate: DateTime(2025, 2, 18),
    ),
    Medication(
      name: 'Rosuvastatin',
      brandNames: ['Crestor'],
      pronunciation: 'roe-SOO-va-sta-tin',
      drugClass: 'Statin',
      halfLife: '19 hours',
      description: 'Potent HMG-CoA reductase inhibitor.',
      commonUses: 'Hyperlipidemia, CV prevention.',
      sideEffects: 'Myalgia, rhabdomyolysis, proteinuria.',
      dosageRange: '5-40 mg once daily',
      onsetOfAction: '2 weeks',
      peakTime: '3-5 hours',
      routes: ['Oral'],
      interactions: ['Cyclosporine', 'Gemfibrozil', 'Warfarin'],
      pregnancyCategory: PregnancyCategory.x,
      conditions: ['High cholesterol', 'Heterozygous FH'],
      category: MedicationCategory.cardiovascular,
      addedDate: DateTime(2025, 2, 17),
    ),
    Medication(
      name: 'Pravastatin',
      brandNames: ['Pravachol'],
      pronunciation: 'PRAV-a-sta-tin',
      drugClass: 'Statin',
      halfLife: '1-2 hours',
      description: 'Hydrophilic statin with fewer drug interactions.',
      commonUses: 'Hyperlipidemia, CV prevention.',
      sideEffects: 'Myalgia, GI upset.',
      dosageRange: '10-80 mg daily',
      onsetOfAction: '2 weeks',
      peakTime: '1-1.5 hours',
      routes: ['Oral'],
      interactions: ['Cyclosporine', 'Gemfibrozil'],
      pregnancyCategory: PregnancyCategory.x,
      conditions: ['High cholesterol', 'CAD prevention'],
      category: MedicationCategory.cardiovascular,
      addedDate: DateTime(2025, 2, 16),
    ),
    Medication(
      name: 'Ezetimibe',
      brandNames: ['Zetia'],
      pronunciation: 'ez-ET-i-mibe',
      drugClass: 'Cholesterol absorption inhibitor',
      halfLife: '22 hours',
      description: 'Blocks intestinal cholesterol absorption.',
      commonUses: 'Hyperlipidemia (often with statins).',
      sideEffects: 'Diarrhea, myalgia.',
      dosageRange: '10 mg once daily',
      onsetOfAction: '2 weeks',
      peakTime: '4-12 hours',
      routes: ['Oral'],
      interactions: ['Cyclosporine', 'Fibrates', 'Cholestyramine'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['High cholesterol'],
      category: MedicationCategory.cardiovascular,
      addedDate: DateTime(2025, 2, 15),
    ),
    Medication(
      name: 'Digoxin',
      brandNames: ['Lanoxin'],
      pronunciation: 'di-JOX-in',
      drugClass: 'Cardiac glycoside',
      halfLife: '36-48 hours',
      description: 'Cardiac glycoside.',
      commonUses: 'Heart failure, atrial fibrillation rate control.',
      sideEffects: 'Arrhythmias, GI upset, visual disturbances.',
      dosageRange: '0.125-0.25 mg daily',
      onsetOfAction: '1-2 hours',
      peakTime: '2-6 hours',
      routes: ['Oral', 'IV'],
      interactions: ['Amiodarone', 'Verapamil', 'Diuretics', 'Quinidine'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Heart failure', 'Atrial fibrillation'],
      category: MedicationCategory.cardiovascular,
      addedDate: DateTime(2025, 2, 14),
    ),
    Medication(
      name: 'Amiodarone',
      brandNames: ['Cordarone', 'Pacerone', 'Nexterone'],
      pronunciation: 'a-MEE-oh-da-rone',
      drugClass: 'Class III antiarrhythmic',
      halfLife: '26-107 days',
      description: 'Potent antiarrhythmic with extensive side effects.',
      commonUses: 'Ventricular and atrial arrhythmias.',
      sideEffects:
          'Pulmonary toxicity, thyroid dysfunction, hepatotoxicity, corneal deposits.',
      dosageRange: '200-400 mg daily maintenance',
      onsetOfAction: 'Days to weeks',
      peakTime: '3-7 hours',
      routes: ['Oral', 'IV'],
      interactions: ['Warfarin', 'Digoxin', 'Simvastatin', 'Many drugs'],
      pregnancyCategory: PregnancyCategory.d,
      blackBoxWarning:
          'Pulmonary toxicity, hepatotoxicity, worsened arrhythmias.',
      conditions: ['VT', 'VF', 'Atrial fibrillation'],
      category: MedicationCategory.cardiovascular,
      addedDate: DateTime(2025, 2, 13),
    ),
    Medication(
      name: 'Diltiazem',
      brandNames: ['Cardizem', 'Tiazac', 'Cartia'],
      pronunciation: 'dil-TYE-a-zem',
      drugClass: 'Non-dihydropyridine CCB',
      halfLife: '3-4.5 hours',
      description: 'Non-DHP calcium channel blocker.',
      commonUses: 'Hypertension, angina, rate control in AFib.',
      sideEffects: 'Bradycardia, peripheral edema, constipation.',
      dosageRange: '120-480 mg daily',
      onsetOfAction: '30-60 minutes',
      peakTime: '2-4 hours',
      routes: ['Oral', 'IV'],
      interactions: ['Beta-blockers', 'CYP3A4 substrates', 'Digoxin'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Hypertension', 'Angina', 'Atrial fibrillation'],
      category: MedicationCategory.cardiovascular,
      addedDate: DateTime(2025, 2, 12),
    ),
    Medication(
      name: 'Verapamil',
      brandNames: ['Calan', 'Verelan', 'Isoptin'],
      pronunciation: 'ver-AP-a-mil',
      drugClass: 'Non-dihydropyridine CCB',
      halfLife: '3-7 hours',
      description: 'Non-DHP calcium channel blocker.',
      commonUses: 'Hypertension, angina, SVT, migraine prophylaxis.',
      sideEffects: 'Constipation, bradycardia, heart failure.',
      dosageRange: '120-480 mg daily',
      onsetOfAction: '1-2 hours',
      peakTime: '1-2 hours',
      routes: ['Oral', 'IV'],
      interactions: ['Beta-blockers', 'Digoxin', 'CYP3A4 substrates'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Hypertension', 'SVT', 'Angina', 'Cluster headache'],
      category: MedicationCategory.cardiovascular,
      addedDate: DateTime(2025, 2, 11),
    ),
    Medication(
      name: 'Nitroglycerin',
      brandNames: ['Nitrostat', 'Nitro-Dur', 'Nitrolingual'],
      pronunciation: 'nye-troe-GLI-ser-in',
      drugClass: 'Nitrate vasodilator',
      halfLife: '1-4 minutes',
      description: 'Short-acting vasodilator.',
      commonUses: 'Angina pectoris (acute), heart failure.',
      sideEffects: 'Headache, hypotension, reflex tachycardia.',
      dosageRange: '0.3-0.6 mg SL every 5 minutes (max 3 doses)',
      onsetOfAction: '1-3 minutes (SL); 30 minutes (patch)',
      peakTime: '4-8 minutes (SL)',
      routes: ['Sublingual', 'Transdermal', 'IV', 'Spray', 'Ointment'],
      interactions: ['PDE5 inhibitors (life-threatening)', 'Alcohol'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Angina', 'Heart failure', 'Hypertensive emergency'],
      category: MedicationCategory.cardiovascular,
      addedDate: DateTime(2025, 2, 10),
    ),
    Medication(
      name: 'Isosorbide Mononitrate',
      brandNames: ['Imdur', 'Monoket'],
      pronunciation: 'eye-soe-SOR-bide',
      drugClass: 'Long-acting nitrate',
      halfLife: '5 hours',
      description: 'Long-acting nitrate.',
      commonUses: 'Chronic stable angina prophylaxis.',
      sideEffects: 'Headache, dizziness, tolerance with continuous use.',
      dosageRange: '20 mg twice daily or 30-120 mg ER once daily',
      onsetOfAction: '30-60 minutes',
      peakTime: '3-4 hours',
      routes: ['Oral'],
      interactions: ['PDE5 inhibitors', 'Alcohol'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Chronic angina', 'Heart failure'],
      category: MedicationCategory.cardiovascular,
      addedDate: DateTime(2025, 2, 9),
    ),
    Medication(
      name: 'Ranolazine',
      brandNames: ['Ranexa'],
      pronunciation: 'ra-NOE-la-zeen',
      drugClass: 'Antianginal (late sodium current inhibitor)',
      halfLife: '7 hours',
      description: 'Unique antianginal that inhibits late sodium current.',
      commonUses: 'Chronic angina.',
      sideEffects: 'QT prolongation, constipation, dizziness.',
      dosageRange: '500-1000 mg twice daily',
      onsetOfAction: '2-6 hours',
      peakTime: '2-5 hours',
      routes: ['Oral'],
      interactions: ['CYP3A4 inhibitors', 'Simvastatin', 'Digoxin'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Chronic angina'],
      category: MedicationCategory.cardiovascular,
      addedDate: DateTime(2025, 2, 8),
    ),
    // ─── ANTICOAGULANTS & ANTIPLATELETS ──────────────────────────────────────
    Medication(
      name: 'Warfarin',
      brandNames: ['Coumadin', 'Jantoven'],
      pronunciation: 'WAR-far-in',
      drugClass: 'Vitamin K antagonist',
      halfLife: '20-60 hours',
      description: 'Oral vitamin K antagonist.',
      commonUses: 'AFib, DVT/PE, mechanical valves, stroke prevention.',
      sideEffects: 'Bleeding, skin necrosis, purple toe syndrome.',
      dosageRange: '2-10 mg daily (titrate to INR 2-3)',
      onsetOfAction: '24-72 hours (full effect 5-7 days)',
      peakTime: '3-5 days',
      routes: ['Oral', 'IV'],
      interactions: ['Many drugs', 'Vitamin K foods', 'Alcohol'],
      pregnancyCategory: PregnancyCategory.x,
      blackBoxWarning: 'Serious bleeding risk; monitor INR closely.',
      conditions: ['AFib', 'DVT', 'PE', 'Mechanical valve'],
      category: MedicationCategory.anticoagulants,
      addedDate: DateTime(2025, 2, 7),
    ),
    Medication(
      name: 'Apixaban',
      brandNames: ['Eliquis'],
      pronunciation: 'a-PIX-a-ban',
      drugClass: 'Direct factor Xa inhibitor (DOAC)',
      halfLife: '12 hours',
      description: 'Direct-acting oral factor Xa inhibitor.',
      commonUses: 'AFib, DVT/PE treatment and prevention.',
      sideEffects: 'Bleeding, anemia.',
      dosageRange: '2.5-5 mg twice daily',
      onsetOfAction: '3-4 hours',
      peakTime: '3-4 hours',
      routes: ['Oral'],
      interactions: ['CYP3A4 and P-gp inducers/inhibitors', 'NSAIDs'],
      pregnancyCategory: PregnancyCategory.b,
      blackBoxWarning:
          'Premature discontinuation increases stroke risk; spinal/epidural hematomas.',
      conditions: ['AFib', 'DVT', 'PE'],
      category: MedicationCategory.anticoagulants,
      addedDate: DateTime(2025, 2, 6),
    ),
    Medication(
      name: 'Rivaroxaban',
      brandNames: ['Xarelto'],
      pronunciation: 'riv-a-ROX-a-ban',
      drugClass: 'Direct factor Xa inhibitor (DOAC)',
      halfLife: '5-9 hours',
      description: 'Direct-acting oral factor Xa inhibitor.',
      commonUses: 'AFib, DVT/PE, CAD/PAD.',
      sideEffects: 'Bleeding.',
      dosageRange: '10-20 mg daily (with food for higher doses)',
      onsetOfAction: '2-4 hours',
      peakTime: '2-4 hours',
      routes: ['Oral'],
      interactions: ['CYP3A4 and P-gp drugs', 'NSAIDs'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning:
          'Premature discontinuation increases thrombotic risk; spinal hematomas.',
      conditions: ['AFib', 'DVT', 'PE', 'PAD'],
      category: MedicationCategory.anticoagulants,
      addedDate: DateTime(2025, 2, 5),
    ),
    Medication(
      name: 'Dabigatran',
      brandNames: ['Pradaxa'],
      pronunciation: 'da-BIG-a-tran',
      drugClass: 'Direct thrombin inhibitor (DOAC)',
      halfLife: '12-17 hours',
      description: 'Direct thrombin inhibitor.',
      commonUses: 'AFib, DVT/PE.',
      sideEffects: 'Bleeding, GI upset, dyspepsia.',
      dosageRange: '150 mg twice daily',
      onsetOfAction: '1-2 hours',
      peakTime: '1-2 hours',
      routes: ['Oral'],
      interactions: ['P-gp inducers/inhibitors', 'NSAIDs'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning:
          'Premature discontinuation increases stroke risk; spinal hematomas.',
      conditions: ['AFib', 'DVT', 'PE'],
      category: MedicationCategory.anticoagulants,
      addedDate: DateTime(2025, 2, 4),
    ),
    Medication(
      name: 'Heparin',
      brandNames: ['generic'],
      pronunciation: 'HEP-a-rin',
      drugClass: 'Unfractionated heparin',
      halfLife: '1-2 hours',
      description: 'Unfractionated heparin anticoagulant.',
      commonUses:
          'DVT/PE treatment, acute coronary syndrome, catheter patency.',
      sideEffects:
          'Bleeding, HIT (heparin-induced thrombocytopenia), osteoporosis.',
      dosageRange: 'Weight-based; titrated by aPTT',
      onsetOfAction: 'Immediate (IV)',
      peakTime: 'Immediate',
      routes: ['IV', 'SC'],
      interactions: ['NSAIDs', 'Antiplatelets', 'Warfarin'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['DVT', 'PE', 'ACS', 'Catheter patency'],
      category: MedicationCategory.anticoagulants,
      addedDate: DateTime(2025, 2, 3),
    ),
    Medication(
      name: 'Enoxaparin',
      brandNames: ['Lovenox'],
      pronunciation: 'ee-nox-a-PAR-in',
      drugClass: 'Low molecular weight heparin',
      halfLife: '4.5-7 hours',
      description: 'Low molecular weight heparin.',
      commonUses: 'DVT prophylaxis/treatment, ACS, pregnancy anticoagulation.',
      sideEffects: 'Bleeding, HIT (less than UFH), injection site reactions.',
      dosageRange: '1 mg/kg SC every 12 hours',
      onsetOfAction: '3-5 hours',
      peakTime: '3-5 hours',
      routes: ['SC', 'IV'],
      interactions: ['NSAIDs', 'Antiplatelets'],
      pregnancyCategory: PregnancyCategory.b,
      blackBoxWarning: 'Spinal/epidural hematomas with neuraxial anesthesia.',
      conditions: ['DVT', 'PE', 'ACS', 'Pregnancy anticoagulation'],
      category: MedicationCategory.anticoagulants,
      addedDate: DateTime(2025, 2, 2),
    ),
    Medication(
      name: 'Clopidogrel',
      brandNames: ['Plavix'],
      pronunciation: 'kloe-PID-oh-grel',
      drugClass: 'P2Y12 receptor antagonist (antiplatelet)',
      halfLife: '6 hours (active metabolite)',
      description: 'ADP receptor inhibitor antiplatelet.',
      commonUses: 'Post-MI, stent placement, stroke prevention.',
      sideEffects: 'Bleeding, TTP (rare), rash.',
      dosageRange: '75 mg once daily (loading 300-600 mg)',
      onsetOfAction: '2 hours',
      peakTime: '30-60 minutes',
      routes: ['Oral'],
      interactions: ['PPIs (omeprazole)', 'CYP2C19 inhibitors', 'NSAIDs'],
      pregnancyCategory: PregnancyCategory.b,
      blackBoxWarning: 'Reduced effectiveness in CYP2C19 poor metabolizers.',
      conditions: ['Post-MI', 'Stent', 'Stroke prevention', 'PAD'],
      category: MedicationCategory.anticoagulants,
      addedDate: DateTime(2025, 2, 1),
    ),
    Medication(
      name: 'Ticagrelor',
      brandNames: ['Brilinta'],
      pronunciation: 'tye-KA-grel-or',
      drugClass: 'P2Y12 receptor antagonist (reversible)',
      halfLife: '7 hours',
      description: 'Reversible P2Y12 inhibitor.',
      commonUses: 'ACS, history of MI.',
      sideEffects: 'Bleeding, dyspnea, bradycardia.',
      dosageRange: '90 mg twice daily (load 180 mg)',
      onsetOfAction: '30 minutes',
      peakTime: '2 hours',
      routes: ['Oral'],
      interactions: ['CYP3A4 drugs', 'Statins', 'Aspirin >100 mg'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning:
          'Aspirin doses >100 mg reduce effectiveness; bleeding risk.',
      conditions: ['ACS', 'Post-MI'],
      category: MedicationCategory.anticoagulants,
      addedDate: DateTime(2025, 1, 31),
    ),

    // ─── GASTROINTESTINAL ────────────────────────────────────────────────────
    Medication(
      name: 'Omeprazole',
      brandNames: ['Prilosec', 'Losec'],
      pronunciation: 'oh-MEP-ra-zole',
      drugClass: 'Proton pump inhibitor (PPI)',
      halfLife: '1-2 hours',
      description: 'Proton pump inhibitor.',
      commonUses: 'GERD, peptic ulcers, H. pylori, Zollinger-Ellison.',
      sideEffects:
          'Headache, GI upset, B12 deficiency, bone fractures (long-term).',
      dosageRange: '20-40 mg once daily',
      onsetOfAction: '1 hour (onset); 4 days full effect',
      peakTime: '30 minutes-3.5 hours',
      routes: ['Oral', 'IV'],
      interactions: ['Clopidogrel', 'Warfarin', 'Methotrexate'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['GERD', 'Peptic ulcers', 'H. pylori', 'Erosive esophagitis'],
      category: MedicationCategory.gastrointestinal,
      addedDate: DateTime(2025, 1, 30),
    ),
    Medication(
      name: 'Esomeprazole',
      brandNames: ['Nexium'],
      pronunciation: 'es-oh-MEP-ra-zole',
      drugClass: 'PPI',
      halfLife: '1-1.5 hours',
      description: 'S-enantiomer of omeprazole.',
      commonUses: 'GERD, peptic ulcers, H. pylori.',
      sideEffects: 'Headache, GI upset, hypomagnesemia.',
      dosageRange: '20-40 mg once daily',
      onsetOfAction: '1 hour',
      peakTime: '1.5 hours',
      routes: ['Oral', 'IV'],
      interactions: ['Clopidogrel', 'Digoxin', 'Methotrexate'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['GERD', 'Peptic ulcers', 'H. pylori'],
      category: MedicationCategory.gastrointestinal,
      addedDate: DateTime(2025, 1, 29),
    ),
    Medication(
      name: 'Pantoprazole',
      brandNames: ['Protonix'],
      pronunciation: 'pan-TOE-pra-zole',
      drugClass: 'PPI',
      halfLife: '1 hour',
      description: 'Proton pump inhibitor.',
      commonUses: 'GERD, erosive esophagitis.',
      sideEffects: 'Headache, diarrhea, hypomagnesemia.',
      dosageRange: '20-40 mg daily; 40 mg IV BID (bleeding)',
      onsetOfAction: '1 hour',
      peakTime: '2.5 hours',
      routes: ['Oral', 'IV'],
      interactions: ['Methotrexate', 'Warfarin'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['GERD', 'Erosive esophagitis', 'GI bleed'],
      category: MedicationCategory.gastrointestinal,
      addedDate: DateTime(2025, 1, 28),
    ),
    Medication(
      name: 'Lansoprazole',
      brandNames: ['Prevacid'],
      pronunciation: 'lan-SOE-pra-zole',
      drugClass: 'PPI',
      halfLife: '1.5 hours',
      description: 'Proton pump inhibitor.',
      commonUses: 'GERD, duodenal ulcers, H. pylori.',
      sideEffects: 'Headache, diarrhea.',
      dosageRange: '15-30 mg daily',
      onsetOfAction: '1-3 hours',
      peakTime: '1.7 hours',
      routes: ['Oral', 'IV'],
      interactions: ['Clopidogrel', 'Digoxin', 'Methotrexate'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['GERD', 'Duodenal ulcers', 'H. pylori'],
      category: MedicationCategory.gastrointestinal,
      addedDate: DateTime(2025, 1, 27),
    ),
    Medication(
      name: 'Famotidine',
      brandNames: ['Pepcid', 'Pepcid AC'],
      pronunciation: 'fa-MOE-ti-deen',
      drugClass: 'H2 receptor antagonist',
      halfLife: '2.5-3.5 hours',
      description: 'Histamine-2 receptor antagonist.',
      commonUses: 'GERD, peptic ulcers, heartburn.',
      sideEffects: 'Headache, constipation, confusion (elderly).',
      dosageRange: '20-40 mg twice daily',
      onsetOfAction: '1 hour',
      peakTime: '1-3 hours',
      routes: ['Oral', 'IV'],
      interactions: ['Tizanidine', 'Ketoconazole'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['GERD', 'Peptic ulcers', 'Heartburn'],
      category: MedicationCategory.gastrointestinal,
      addedDate: DateTime(2025, 1, 26),
    ),
    Medication(
      name: 'Ranitidine',
      brandNames: ['Zantac (withdrawn)'],
      pronunciation: 'ra-NIT-i-deen',
      drugClass: 'H2 receptor antagonist',
      halfLife: '2-3 hours',
      description:
          'Histamine-2 receptor antagonist (most formulations withdrawn due to NDMA contamination).',
      commonUses: 'Historically: GERD, peptic ulcers.',
      sideEffects: 'Headache, diarrhea.',
      dosageRange: '150 mg twice daily (historically)',
      onsetOfAction: '1 hour',
      peakTime: '2-3 hours',
      routes: ['Oral', 'IV'],
      interactions: ['Warfarin', 'Theophylline'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['GERD (historical)', 'Peptic ulcers (historical)'],
      category: MedicationCategory.gastrointestinal,
      addedDate: DateTime(2025, 1, 25),
    ),
    Medication(
      name: 'Ondansetron',
      brandNames: ['Zofran'],
      pronunciation: 'on-DAN-se-tron',
      drugClass: '5-HT3 receptor antagonist',
      halfLife: '3-6 hours',
      description: 'Serotonin receptor antagonist antiemetic.',
      commonUses: 'Chemo-induced nausea, post-op nausea, gastroenteritis.',
      sideEffects: 'QT prolongation, headache, constipation.',
      dosageRange: '4-8 mg every 8 hours',
      onsetOfAction: '30 minutes',
      peakTime: '2 hours',
      routes: ['Oral', 'IV', 'IM', 'ODT'],
      interactions: ['QT-prolonging drugs', 'Apomorphine', 'Tramadol'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['Chemo nausea', 'Post-op nausea', 'Pregnancy nausea'],
      category: MedicationCategory.gastrointestinal,
      addedDate: DateTime(2025, 1, 24),
    ),
    Medication(
      name: 'Metoclopramide',
      brandNames: ['Reglan'],
      pronunciation: 'met-oh-KLOE-pra-mide',
      drugClass: 'Dopamine antagonist / prokinetic',
      halfLife: '5-6 hours',
      description: 'Prokinetic and antiemetic.',
      commonUses: 'Gastroparesis, nausea, GERD.',
      sideEffects: 'EPS, tardive dyskinesia, drowsiness.',
      dosageRange: '10 mg 4×/day',
      onsetOfAction: '30-60 minutes',
      peakTime: '1-2 hours',
      routes: ['Oral', 'IV', 'IM', 'Nasal'],
      interactions: ['Antipsychotics', 'CNS depressants', 'Levodopa'],
      pregnancyCategory: PregnancyCategory.b,
      blackBoxWarning: 'Tardive dyskinesia risk with long-term use.',
      conditions: ['Gastroparesis', 'Nausea', 'GERD'],
      category: MedicationCategory.gastrointestinal,
      addedDate: DateTime(2025, 1, 23),
    ),
    Medication(
      name: 'Loperamide',
      brandNames: ['Imodium'],
      pronunciation: 'loe-PER-a-mide',
      drugClass: 'Opioid antidiarrheal',
      halfLife: '9-14 hours',
      description: 'Peripheral opioid for diarrhea.',
      commonUses: 'Acute diarrhea.',
      sideEffects: 'Constipation, dizziness, cardiac arrhythmias (high doses).',
      dosageRange:
          '4 mg initially, then 2 mg after each loose stool (max 16 mg)',
      onsetOfAction: '1 hour',
      peakTime: '4-5 hours',
      routes: ['Oral'],
      interactions: ['CYP3A4 inhibitors'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning:
          'Serious cardiac events at doses exceeding recommended use.',
      conditions: ['Diarrhea', 'IBS-D'],
      category: MedicationCategory.gastrointestinal,
      addedDate: DateTime(2025, 1, 22),
    ),
    Medication(
      name: 'Sucralfate',
      brandNames: ['Carafate'],
      pronunciation: 'soo-KRAL-fate',
      drugClass: 'Mucosal protectant',
      halfLife: 'Minimal absorption',
      description: 'Locally acting mucosal protectant.',
      commonUses: 'Duodenal ulcers, stress ulcer prophylaxis.',
      sideEffects: 'Constipation, bezoar formation.',
      dosageRange: '1 g 4×/day (before meals and bedtime)',
      onsetOfAction: '30 minutes',
      peakTime: '1 hour (local)',
      routes: ['Oral'],
      interactions: ['Quinolones', 'Tetracyclines', 'Phenytoin', 'Warfarin'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['Duodenal ulcers', 'Stress ulcers'],
      category: MedicationCategory.gastrointestinal,
      addedDate: DateTime(2025, 1, 21),
    ),
    Medication(
      name: 'Bisacodyl',
      brandNames: ['Dulcolax'],
      pronunciation: 'bis-a-KOE-dil',
      drugClass: 'Stimulant laxative',
      halfLife: '16 hours',
      description: 'Stimulant laxative.',
      commonUses: 'Constipation, bowel prep.',
      sideEffects: 'Cramping, electrolyte disturbances.',
      dosageRange: '5-15 mg daily',
      onsetOfAction: '6-10 hours (oral); 15-60 min (rectal)',
      peakTime: 'Variable',
      routes: ['Oral', 'Rectal'],
      interactions: ['Antacids', 'Milk', 'PPIs'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Constipation', 'Bowel prep'],
      category: MedicationCategory.gastrointestinal,
      addedDate: DateTime(2025, 1, 20),
    ),
    Medication(
      name: 'Docusate Sodium',
      brandNames: ['Colace'],
      pronunciation: 'DOK-yoo-sate',
      drugClass: 'Stool softener',
      halfLife: 'Not well characterized',
      description: 'Surfactant stool softener.',
      commonUses: 'Constipation prevention.',
      sideEffects: 'Mild cramping, throat irritation.',
      dosageRange: '100 mg 1-4×/day',
      onsetOfAction: '12-72 hours',
      peakTime: 'Variable',
      routes: ['Oral', 'Rectal'],
      interactions: ['Mineral oil'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Constipation', 'Prevent straining'],
      category: MedicationCategory.gastrointestinal,
      addedDate: DateTime(2025, 1, 19),
    ),

    // ─── UROLOGICAL ──────────────────────────────────────────────────────────
    Medication(
      name: 'Sildenafil',
      brandNames: ['Viagra', 'Revatio'],
      pronunciation: 'sil-DEN-a-fil',
      drugClass: 'PDE5 inhibitor',
      halfLife: '4 hours',
      description: 'Phosphodiesterase type 5 inhibitor.',
      commonUses: 'Erectile dysfunction, pulmonary arterial hypertension.',
      sideEffects: 'Headache, flushing, vision changes, priapism.',
      dosageRange:
          '25-100 mg 1 hour before intercourse (ED); 20 mg 3×/day (PAH)',
      onsetOfAction: '30-60 minutes',
      peakTime: '1 hour',
      routes: ['Oral', 'IV'],
      interactions: [
        'Nitrates (life-threatening)',
        'Alpha-blockers',
        'CYP3A4 inhibitors'
      ],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['Erectile dysfunction', 'Pulmonary hypertension'],
      category: MedicationCategory.urological,
      addedDate: DateTime(2025, 1, 18),
    ),
    Medication(
      name: 'Tadalafil',
      brandNames: ['Cialis', 'Adcirca'],
      pronunciation: 'tah-DAL-a-fil',
      drugClass: 'PDE5 inhibitor',
      halfLife: '17.5 hours',
      description: 'Long-acting PDE5 inhibitor.',
      commonUses: 'Erectile dysfunction, BPH, pulmonary hypertension.',
      sideEffects: 'Back pain, headache, myalgia.',
      dosageRange: '5-20 mg as needed or 5 mg daily',
      onsetOfAction: '30 minutes',
      peakTime: '2 hours',
      routes: ['Oral'],
      interactions: ['Nitrates', 'Alpha-blockers', 'CYP3A4 inhibitors'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['Erectile dysfunction', 'BPH', 'Pulmonary hypertension'],
      category: MedicationCategory.urological,
      addedDate: DateTime(2025, 1, 17),
    ),
    Medication(
      name: 'Tamsulosin',
      brandNames: ['Flomax'],
      pronunciation: 'tam-SOO-loe-sin',
      drugClass: 'Alpha-1A selective blocker',
      halfLife: '9-13 hours',
      description: 'Selective alpha-1A adrenergic blocker.',
      commonUses: 'BPH, kidney stone passage.',
      sideEffects:
          'Orthostatic hypotension, retrograde ejaculation, floppy iris syndrome.',
      dosageRange: '0.4-0.8 mg once daily',
      onsetOfAction: '2-4 hours',
      peakTime: '4-5 hours',
      routes: ['Oral'],
      interactions: [
        'PDE5 inhibitors',
        'Other alpha-blockers',
        'CYP3A4 inhibitors'
      ],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['BPH', 'Kidney stones'],
      category: MedicationCategory.urological,
      addedDate: DateTime(2025, 1, 16),
    ),
    Medication(
      name: 'Dutasteride',
      brandNames: ['Avodart', 'Jalyn (with tamsulosin)'],
      pronunciation: 'doo-TAS-ter-ide',
      drugClass: '5-alpha reductase inhibitor',
      halfLife: '5 weeks',
      description: 'Dual 5-alpha reductase inhibitor.',
      commonUses: 'BPH.',
      sideEffects: 'Sexual dysfunction, gynecomastia.',
      dosageRange: '0.5 mg once daily',
      onsetOfAction: '3-6 months',
      peakTime: '2-3 hours',
      routes: ['Oral'],
      interactions: ['CYP3A4 inhibitors'],
      pregnancyCategory: PregnancyCategory.x,
      conditions: ['BPH'],
      category: MedicationCategory.urological,
      addedDate: DateTime(2025, 1, 15),
    ),
    Medication(
      name: 'Oxybutynin',
      brandNames: ['Ditropan', 'Oxytrol'],
      pronunciation: 'ox-ee-BYOO-ti-nin',
      drugClass: 'Anticholinergic',
      halfLife: '2-3 hours',
      description: 'Antimuscarinic for overactive bladder.',
      commonUses: 'Overactive bladder, urinary incontinence.',
      sideEffects: 'Dry mouth, constipation, cognitive impairment (elderly).',
      dosageRange: '5 mg 2-3×/day (IR); 5-15 mg daily (ER)',
      onsetOfAction: '30-60 minutes',
      peakTime: '1 hour',
      routes: ['Oral', 'Transdermal'],
      interactions: ['Anticholinergics', 'CYP3A4 inhibitors'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['Overactive bladder', 'Urinary incontinence'],
      category: MedicationCategory.urological,
      addedDate: DateTime(2025, 1, 14),
    ),

    // ─── NEUROLOGICAL ────────────────────────────────────────────────────────
    Medication(
      name: 'Zolpidem',
      brandNames: ['Ambien', 'Edluar', 'Intermezzo'],
      pronunciation: 'zole-PID-em',
      drugClass: 'Non-benzodiazepine hypnotic (Z-drug)',
      halfLife: '2-3 hours',
      description: 'Non-benzo GABA-A modulator for sleep.',
      commonUses: 'Insomnia.',
      sideEffects: 'Complex sleep behaviors, next-day impairment, amnesia.',
      dosageRange: '5-10 mg at bedtime',
      onsetOfAction: '30 minutes',
      peakTime: '1.6 hours',
      routes: ['Oral', 'SL'],
      interactions: ['CNS depressants', 'CYP3A4 inhibitors', 'Alcohol'],
      pregnancyCategory: PregnancyCategory.c,
      schedule: ControlledSchedule.iv,
      blackBoxWarning:
          'Complex sleep behaviors (sleep-driving, etc.) can result in serious injury or death.',
      conditions: ['Insomnia'],
      category: MedicationCategory.neurological,
      addedDate: DateTime(2025, 1, 13),
    ),
    Medication(
      name: 'Eszopiclone',
      brandNames: ['Lunesta'],
      pronunciation: 'es-zoe-PIK-lone',
      drugClass: 'Non-benzodiazepine hypnotic',
      halfLife: '6 hours',
      description: 'Non-benzo hypnotic.',
      commonUses: 'Insomnia.',
      sideEffects: 'Unpleasant taste, headache, complex sleep behaviors.',
      dosageRange: '1-3 mg at bedtime',
      onsetOfAction: 'Within 30 minutes',
      peakTime: '1 hour',
      routes: ['Oral'],
      interactions: ['CYP3A4 inhibitors', 'CNS depressants'],
      pregnancyCategory: PregnancyCategory.c,
      schedule: ControlledSchedule.iv,
      blackBoxWarning: 'Complex sleep behaviors.',
      conditions: ['Insomnia'],
      category: MedicationCategory.neurological,
      addedDate: DateTime(2025, 1, 12),
    ),
    Medication(
      name: 'Ramelteon',
      brandNames: ['Rozerem'],
      pronunciation: 'ra-MEL-tee-on',
      drugClass: 'Melatonin receptor agonist',
      halfLife: '1-2.6 hours',
      description: 'Selective melatonin MT1/MT2 agonist.',
      commonUses: 'Insomnia (sleep onset).',
      sideEffects: 'Dizziness, somnolence, fatigue.',
      dosageRange: '8 mg at bedtime',
      onsetOfAction: '30 minutes',
      peakTime: '0.75 hours',
      routes: ['Oral'],
      interactions: ['Fluvoxamine', 'CYP1A2 inhibitors'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Insomnia'],
      category: MedicationCategory.neurological,
      addedDate: DateTime(2025, 1, 11),
    ),
    Medication(
      name: 'Suvorexant',
      brandNames: ['Belsomra'],
      pronunciation: 'soo-voe-REX-ant',
      drugClass: 'Orexin receptor antagonist',
      halfLife: '12 hours',
      description: 'Dual orexin receptor antagonist.',
      commonUses: 'Insomnia.',
      sideEffects: 'Somnolence, abnormal dreams, next-day impairment.',
      dosageRange: '10-20 mg at bedtime',
      onsetOfAction: '30 minutes',
      peakTime: '2 hours',
      routes: ['Oral'],
      interactions: ['CYP3A4 inhibitors', 'CNS depressants'],
      pregnancyCategory: PregnancyCategory.c,
      schedule: ControlledSchedule.iv,
      conditions: ['Insomnia'],
      category: MedicationCategory.neurological,
      addedDate: DateTime(2025, 1, 10),
    ),
    Medication(
      name: 'Donepezil',
      brandNames: ['Aricept'],
      pronunciation: 'doe-NEP-e-zil',
      drugClass: 'Acetylcholinesterase inhibitor',
      halfLife: '70 hours',
      description: 'Cholinesterase inhibitor.',
      commonUses: 'Alzheimer disease (mild to severe).',
      sideEffects: 'Nausea, diarrhea, bradycardia, syncope.',
      dosageRange: '5-10 mg once daily (at bedtime)',
      onsetOfAction: 'Weeks',
      peakTime: '3-4 hours',
      routes: ['Oral', 'ODT'],
      interactions: ['Anticholinergics', 'Succinylcholine', 'CYP inhibitors'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Alzheimer disease', 'Dementia'],
      category: MedicationCategory.neurological,
      addedDate: DateTime(2025, 1, 9),
    ),
    Medication(
      name: 'Memantine',
      brandNames: ['Namenda'],
      pronunciation: 'me-MAN-teen',
      drugClass: 'NMDA receptor antagonist',
      halfLife: '60-80 hours',
      description: 'NMDA receptor antagonist.',
      commonUses: 'Moderate to severe Alzheimer disease.',
      sideEffects: 'Dizziness, headache, confusion.',
      dosageRange: '5-20 mg daily',
      onsetOfAction: 'Weeks',
      peakTime: '3-7 hours',
      routes: ['Oral'],
      interactions: ['Amantadine', 'Ketamine', 'Dextromethorphan'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['Moderate-severe Alzheimer'],
      category: MedicationCategory.neurological,
      addedDate: DateTime(2025, 1, 8),
    ),
    Medication(
      name: 'Rivastigmine',
      brandNames: ['Exelon'],
      pronunciation: 'ri-va-STIG-meen',
      drugClass: 'Cholinesterase inhibitor',
      halfLife: '1.5 hours',
      description: 'Cholinesterase inhibitor.',
      commonUses: 'Alzheimer disease, Parkinson disease dementia.',
      sideEffects: 'Nausea, vomiting, weight loss, bradycardia.',
      dosageRange: '1.5-6 mg twice daily (oral); 4.6-13.3 mg/24hr (patch)',
      onsetOfAction: 'Weeks',
      peakTime: '1 hour',
      routes: ['Oral', 'Transdermal'],
      interactions: ['Anticholinergics', 'Succinylcholine'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['Alzheimer', 'Parkinson dementia'],
      category: MedicationCategory.neurological,
      addedDate: DateTime(2025, 1, 7),
    ),
    Medication(
      name: 'Galantamine',
      brandNames: ['Razadyne'],
      pronunciation: 'ga-LAN-ta-meen',
      drugClass: 'Cholinesterase inhibitor',
      halfLife: '7 hours',
      description: 'Reversible cholinesterase inhibitor.',
      commonUses: 'Mild to moderate Alzheimer disease.',
      sideEffects: 'Nausea, bradycardia, syncope.',
      dosageRange: '8-24 mg daily',
      onsetOfAction: 'Weeks',
      peakTime: '1 hour',
      routes: ['Oral'],
      interactions: ['Anticholinergics', 'CYP inhibitors'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['Mild-moderate Alzheimer'],
      category: MedicationCategory.neurological,
      addedDate: DateTime(2025, 1, 6),
    ),
    Medication(
      name: 'Levodopa-Carbidopa',
      brandNames: ['Sinemet', 'Rytary', 'Duopa'],
      pronunciation: 'lee-voe-DOE-pa / kar-bi-DOE-pa',
      drugClass: 'Dopamine precursor + decarboxylase inhibitor',
      halfLife: '1.5-2 hours',
      description: 'Dopamine replacement for Parkinson disease.',
      commonUses: 'Parkinson disease.',
      sideEffects: 'Dyskinesias, motor fluctuations, hallucinations.',
      dosageRange: 'Individualized; typically 3-4 doses daily',
      onsetOfAction: '30-60 minutes',
      peakTime: '0.5-2 hours',
      routes: ['Oral', 'Intestinal gel', 'Inhalation'],
      interactions: ['MAOIs', 'High-protein foods', 'Antipsychotics'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Parkinson disease'],
      category: MedicationCategory.neurological,
      addedDate: DateTime(2025, 1, 5),
    ),

    // ─── SPECIALIZED ─────────────────────────────────────────────────────────
    Medication(
      name: 'Lithium',
      brandNames: ['Lithobid', 'Eskalith'],
      pronunciation: 'LITH-ee-um',
      drugClass: 'Mood stabilizer',
      halfLife: '18-36 hours',
      description: 'First-line mood stabilizer for bipolar disorder.',
      commonUses: 'Bipolar disorder, acute mania, depression augmentation.',
      sideEffects:
          'Tremor, polyuria, hypothyroidism, nephrogenic DI, toxicity.',
      dosageRange: '600-1800 mg daily (titrate to level 0.6-1.2 mEq/L)',
      onsetOfAction: '1-3 weeks',
      peakTime: '0.5-3 hours',
      routes: ['Oral'],
      interactions: ['NSAIDs', 'ACE inhibitors', 'Diuretics'],
      pregnancyCategory: PregnancyCategory.d,
      blackBoxWarning:
          'Narrow therapeutic window; toxicity at therapeutic doses possible.',
      conditions: ['Bipolar disorder', 'Acute mania'],
      category: MedicationCategory.specialized,
      addedDate: DateTime(2025, 1, 4),
    ),
    Medication(
      name: 'Epinephrine',
      brandNames: ['EpiPen', 'Auvi-Q', 'Adrenaclick'],
      pronunciation: 'ep-i-NEF-rin',
      drugClass: 'Catecholamine (alpha and beta agonist)',
      halfLife: '2 minutes',
      description: 'Natural catecholamine hormone.',
      commonUses: 'Anaphylaxis, cardiac arrest, asthma exacerbation.',
      sideEffects: 'Tachycardia, hypertension, tremor, anxiety.',
      dosageRange: '0.3 mg IM (anaphylaxis); 1 mg IV (arrest)',
      onsetOfAction: 'Immediate (IV); 5-10 min (IM)',
      peakTime: 'Immediate to 30 minutes',
      routes: ['IM', 'IV', 'SC', 'Inhalation'],
      interactions: ['Beta-blockers', 'TCAs', 'MAOIs', 'Digoxin'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Anaphylaxis', 'Cardiac arrest', 'Severe asthma'],
      category: MedicationCategory.specialized,
      addedDate: DateTime(2025, 1, 3),
    ),
    Medication(
      name: 'Naloxone',
      brandNames: ['Narcan', 'Evzio'],
      pronunciation: 'nal-OX-one',
      drugClass: 'Opioid antagonist',
      halfLife: '30-80 minutes',
      description: 'Pure opioid antagonist for overdose reversal.',
      commonUses: 'Opioid overdose reversal.',
      sideEffects: 'Acute withdrawal, hypertension, pulmonary edema.',
      dosageRange: '0.4-2 mg IV/IM/IN; repeat as needed',
      onsetOfAction: '1-2 minutes (IV); 2-5 min (IM/IN)',
      peakTime: 'Immediate',
      routes: ['IV', 'IM', 'SC', 'Intranasal'],
      interactions: ['Opioids (reversal)'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['Opioid overdose'],
      category: MedicationCategory.specialized,
      addedDate: DateTime(2025, 1, 2),
    ),
    Medication(
      name: 'Naltrexone',
      brandNames: ['Vivitrol', 'Revia'],
      pronunciation: 'nal-TREX-one',
      drugClass: 'Opioid antagonist',
      halfLife: '4 hours (10 days for IM depot)',
      description: 'Long-acting opioid antagonist.',
      commonUses: 'Alcohol use disorder, opioid use disorder maintenance.',
      sideEffects: 'Hepatotoxicity, depression, GI upset.',
      dosageRange: '50 mg oral daily; 380 mg IM monthly',
      onsetOfAction: '15 minutes (oral); 2 hours (IM)',
      peakTime: '1 hour (oral)',
      routes: ['Oral', 'IM'],
      interactions: ['Opioids (precipitates withdrawal)'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning: 'Hepatotoxicity at high doses.',
      conditions: ['Alcohol use disorder', 'Opioid use disorder'],
      category: MedicationCategory.specialized,
      addedDate: DateTime(2025, 1, 1),
    ),
    Medication(
      name: 'Disulfiram',
      brandNames: ['Antabuse'],
      pronunciation: 'dye-SUL-fi-ram',
      drugClass: 'Aldehyde dehydrogenase inhibitor',
      halfLife: '60-120 hours',
      description: 'Aversion therapy for alcohol use disorder.',
      commonUses: 'Alcohol use disorder.',
      sideEffects: 'Severe reaction with alcohol, hepatotoxicity.',
      dosageRange: '250-500 mg once daily',
      onsetOfAction: '12 hours',
      peakTime: '8-10 hours',
      routes: ['Oral'],
      interactions: ['Alcohol (severe reaction)', 'Metronidazole', 'Isoniazid'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning:
          'Must never be given to intoxicated patient or without patient knowledge.',
      conditions: ['Alcohol use disorder'],
      category: MedicationCategory.specialized,
      addedDate: DateTime(2024, 12, 31),
    ),
    Medication(
      name: 'Allopurinol',
      brandNames: ['Zyloprim'],
      pronunciation: 'al-oh-PURE-i-nol',
      drugClass: 'Xanthine oxidase inhibitor',
      halfLife: '1-2 hours (oxipurinol metabolite 12-30 hr)',
      description: 'Xanthine oxidase inhibitor.',
      commonUses: 'Gout, hyperuricemia, tumor lysis syndrome prevention.',
      sideEffects: 'Rash (SJS/TEN), hepatotoxicity.',
      dosageRange: '100-800 mg daily',
      onsetOfAction: '2-3 days',
      peakTime: '1.5 hours',
      routes: ['Oral', 'IV'],
      interactions: ['Azathioprine', 'Mercaptopurine', 'Warfarin'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Gout', 'Hyperuricemia', 'Tumor lysis syndrome'],
      category: MedicationCategory.specialized,
      addedDate: DateTime(2024, 12, 30),
    ),
    Medication(
      name: 'Colchicine',
      brandNames: ['Colcrys', 'Mitigare'],
      pronunciation: 'KOL-chi-seen',
      drugClass: 'Anti-inflammatory (microtubule inhibitor)',
      halfLife: '27-31 hours',
      description: 'Microtubule inhibitor with anti-inflammatory effects.',
      commonUses: 'Acute gout, familial Mediterranean fever.',
      sideEffects: 'Diarrhea, myopathy, neuropathy, bone marrow suppression.',
      dosageRange: '1.2 mg initial, then 0.6 mg after 1 hour (gout flare)',
      onsetOfAction: '12-24 hours',
      peakTime: '1-2 hours',
      routes: ['Oral'],
      interactions: ['CYP3A4 inhibitors', 'Statins', 'P-gp inhibitors'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning:
          'Fatal toxicity if combined with P-gp or CYP3A4 inhibitors in renal/hepatic impairment.',
      conditions: ['Gout flare', 'FMF', 'Pericarditis'],
      category: MedicationCategory.specialized,
      addedDate: DateTime(2024, 12, 29),
    ),
    Medication(
      name: 'Febuxostat',
      brandNames: ['Uloric'],
      pronunciation: 'feb-UX-oh-stat',
      drugClass: 'Xanthine oxidase inhibitor',
      halfLife: '5-8 hours',
      description: 'Non-purine xanthine oxidase inhibitor.',
      commonUses: 'Chronic gout management.',
      sideEffects: 'Liver dysfunction, cardiovascular events.',
      dosageRange: '40-80 mg once daily',
      onsetOfAction: '2 weeks',
      peakTime: '1-1.5 hours',
      routes: ['Oral'],
      interactions: ['Azathioprine', 'Mercaptopurine', 'Theophylline'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning:
          'Increased cardiovascular mortality compared to allopurinol.',
      conditions: ['Chronic gout'],
      category: MedicationCategory.specialized,
      addedDate: DateTime(2024, 12, 28),
    ),

    // ─── DERMATOLOGICAL ──────────────────────────────────────────────────────
    Medication(
      name: 'Tretinoin',
      brandNames: ['Retin-A', 'Renova'],
      pronunciation: 'TRET-i-noyn',
      drugClass: 'Retinoid',
      halfLife: '0.5-2 hours',
      description: 'Topical vitamin A derivative.',
      commonUses: 'Acne, photoaging, keratosis pilaris.',
      sideEffects: 'Skin irritation, photosensitivity, dryness.',
      dosageRange: 'Apply pea-sized amount nightly',
      onsetOfAction: '2-6 weeks',
      peakTime: 'N/A (topical)',
      routes: ['Topical'],
      interactions: ['Benzoyl peroxide (deactivates)', 'Waxing/dermabrasion'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Acne', 'Photoaging', 'Fine lines'],
      category: MedicationCategory.dermatological,
      addedDate: DateTime(2024, 12, 27),
    ),
    Medication(
      name: 'Isotretinoin',
      brandNames: ['Accutane', 'Claravis', 'Absorica'],
      pronunciation: 'eye-soe-TRET-i-noyn',
      drugClass: 'Oral retinoid',
      halfLife: '21 hours (metabolite 21-24 hours)',
      description: 'Oral retinoid for severe acne.',
      commonUses: 'Severe, recalcitrant acne.',
      sideEffects: 'Teratogenicity, dry skin, elevated lipids, depression.',
      dosageRange: '0.5-1 mg/kg daily × 15-20 weeks',
      onsetOfAction: '4-8 weeks',
      peakTime: '3 hours',
      routes: ['Oral'],
      interactions: ['Tetracyclines', 'Vitamin A', 'Hormonal contraceptives'],
      pregnancyCategory: PregnancyCategory.x,
      blackBoxWarning:
          'Severe birth defects; iPLEDGE program required; depression risk.',
      conditions: ['Severe acne', 'Cystic acne'],
      category: MedicationCategory.dermatological,
      addedDate: DateTime(2024, 12, 26),
    ),
    Medication(
      name: 'Hydrocortisone (Topical)',
      brandNames: ['Cortaid', 'Locoid'],
      pronunciation: 'hye-droe-KOR-ti-sone',
      drugClass: 'Low-potency topical corticosteroid',
      halfLife: '1-2 hours (minimal systemic)',
      description: 'Low-potency topical corticosteroid.',
      commonUses: 'Eczema, contact dermatitis, mild inflammation.',
      sideEffects: 'Skin thinning, striae, acne.',
      dosageRange: 'Apply thin layer 2-4×/day',
      onsetOfAction: 'Hours',
      peakTime: 'N/A (topical)',
      routes: ['Topical'],
      interactions: ['Minimal for topical'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Eczema', 'Contact dermatitis', 'Rash'],
      category: MedicationCategory.dermatological,
      addedDate: DateTime(2024, 12, 25),
    ),
    Medication(
      name: 'Betamethasone',
      brandNames: ['Diprolene', 'Celestone'],
      pronunciation: 'bay-ta-METH-a-sone',
      drugClass: 'High-potency corticosteroid',
      halfLife: '6 hours',
      description: 'Potent corticosteroid.',
      commonUses: 'Psoriasis, eczema, dermatoses, fetal lung maturation.',
      sideEffects: 'Skin atrophy, HPA suppression, hyperglycemia.',
      dosageRange: 'Apply thin layer 1-2×/day (topical)',
      onsetOfAction: 'Hours (topical)',
      peakTime: '1-2 hours (systemic)',
      routes: ['Topical', 'IM', 'Oral'],
      interactions: ['Vaccines', 'Diabetic meds'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Psoriasis', 'Eczema', 'Fetal lung maturation'],
      category: MedicationCategory.dermatological,
      addedDate: DateTime(2024, 12, 24),
    ),
    Medication(
      name: 'Minoxidil',
      brandNames: ['Rogaine', 'Loniten'],
      pronunciation: 'mi-NOX-i-dil',
      drugClass: 'Vasodilator / hair growth stimulant',
      halfLife: '4 hours (oral); minimal systemic (topical)',
      description: 'Potassium channel opener vasodilator.',
      commonUses: 'Androgenic alopecia (topical), severe hypertension (oral).',
      sideEffects:
          'Hypertrichosis, scalp irritation (topical); pericardial effusion (oral).',
      dosageRange: '2-5% solution/foam BID (topical); 5-40 mg daily (oral)',
      onsetOfAction: '4-8 months (hair growth)',
      peakTime: 'N/A (topical)',
      routes: ['Topical', 'Oral'],
      interactions: ['Antihypertensives (oral)'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning:
          'Severe oral form: pericardial effusion, cardiac tamponade.',
      conditions: ['Hair loss', 'Severe hypertension'],
      category: MedicationCategory.dermatological,
      addedDate: DateTime(2024, 12, 23),
    ),
    Medication(
      name: 'Mupirocin',
      brandNames: ['Bactroban', 'Centany'],
      pronunciation: 'myoo-PEER-oh-sin',
      drugClass: 'Topical antibiotic',
      halfLife: '17-36 minutes (minimal systemic)',
      description: 'Topical antibiotic for MRSA decolonization.',
      commonUses: 'Impetigo, MRSA nasal decolonization.',
      sideEffects: 'Local irritation, burning.',
      dosageRange: 'Apply 2% 2-3×/day',
      onsetOfAction: 'Days',
      peakTime: 'N/A (topical)',
      routes: ['Topical', 'Nasal'],
      interactions: ['Minimal'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['Impetigo', 'MRSA decolonization'],
      category: MedicationCategory.dermatological,
      addedDate: DateTime(2024, 12, 22),
    ),

    // ─── OPHTHALMIC DROPS ────────────────────────────────────────────────────
    Medication(
      name: 'Latanoprost',
      brandNames: ['Xalatan'],
      pronunciation: 'la-TAN-oh-prost',
      drugClass: 'Prostaglandin analog',
      halfLife: '17 minutes',
      description: 'Prostaglandin F2alpha analog.',
      commonUses: 'Open-angle glaucoma, ocular hypertension.',
      sideEffects: 'Iris pigmentation, eyelash growth, eye irritation.',
      dosageRange: '1 drop once daily (evening)',
      onsetOfAction: '3-4 hours',
      peakTime: '8-12 hours',
      routes: ['Ophthalmic'],
      interactions: ['Other prostaglandin analogs'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Glaucoma', 'Ocular hypertension'],
      category: MedicationCategory.ophthalmic,
      addedDate: DateTime(2024, 12, 21),
    ),
    Medication(
      name: 'Timolol (Ophthalmic)',
      brandNames: ['Timoptic', 'Betimol'],
      pronunciation: 'TIM-oh-lol',
      drugClass: 'Beta-blocker (ophthalmic)',
      halfLife: '4 hours',
      description: 'Non-selective beta-blocker eye drops.',
      commonUses: 'Glaucoma, ocular hypertension.',
      sideEffects: 'Systemic beta-blockade, bronchospasm, bradycardia.',
      dosageRange: '1 drop twice daily',
      onsetOfAction: '30 minutes',
      peakTime: '2 hours',
      routes: ['Ophthalmic'],
      interactions: ['Oral beta-blockers', 'Calcium channel blockers'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Glaucoma', 'Ocular hypertension'],
      category: MedicationCategory.ophthalmic,
      addedDate: DateTime(2024, 12, 20),
    ),
    Medication(
      name: 'Brimonidine',
      brandNames: ['Alphagan P'],
      pronunciation: 'bri-MOE-ni-deen',
      drugClass: 'Alpha-2 agonist (ophthalmic)',
      halfLife: '3 hours',
      description: 'Selective alpha-2 agonist.',
      commonUses: 'Glaucoma, ocular hypertension.',
      sideEffects: 'Allergic conjunctivitis, dry mouth, fatigue.',
      dosageRange: '1 drop 2-3×/day',
      onsetOfAction: '1 hour',
      peakTime: '2 hours',
      routes: ['Ophthalmic', 'Topical (rosacea)'],
      interactions: ['MAOIs', 'CNS depressants'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['Glaucoma', 'Ocular hypertension', 'Rosacea'],
      category: MedicationCategory.ophthalmic,
      addedDate: DateTime(2024, 12, 19),
    ),
    Medication(
      name: 'Artificial Tears',
      brandNames: ['Systane', 'Refresh', 'GenTeal'],
      pronunciation: 'ar-ti-FISH-al teers',
      drugClass: 'Ocular lubricant',
      halfLife: 'Local action only',
      description: 'Ocular lubricants.',
      commonUses: 'Dry eye syndrome.',
      sideEffects: 'Transient blurred vision.',
      dosageRange: '1-2 drops as needed',
      onsetOfAction: 'Immediate',
      peakTime: 'Immediate',
      routes: ['Ophthalmic'],
      interactions: ['Space apart from other eye meds by 5-10 min'],
      pregnancyCategory: PregnancyCategory.n,
      conditions: ['Dry eyes', 'Eye strain'],
      category: MedicationCategory.ophthalmic,
      addedDate: DateTime(2024, 12, 18),
    ),

    // ─── VACCINES ────────────────────────────────────────────────────────────
    Medication(
      name: 'Influenza Vaccine',
      brandNames: ['Fluzone', 'Flublok', 'Fluarix'],
      pronunciation: 'in-floo-EN-za vak-SEEN',
      drugClass: 'Viral vaccine (inactivated/recombinant)',
      halfLife: 'N/A (immunologic)',
      description: 'Seasonal influenza vaccine.',
      commonUses: 'Annual influenza prevention.',
      sideEffects: 'Injection site reactions, mild flu-like symptoms.',
      dosageRange: '0.5 mL IM annually',
      onsetOfAction: '2 weeks',
      peakTime: '4-6 weeks (peak immunity)',
      routes: ['IM', 'Intranasal (LAIV)'],
      interactions: ['Immunosuppressants'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Influenza prevention'],
      category: MedicationCategory.vaccines,
      addedDate: DateTime(2024, 12, 17),
    ),
    Medication(
      name: 'COVID-19 Vaccine (mRNA)',
      brandNames: ['Comirnaty (Pfizer)', 'Spikevax (Moderna)'],
      pronunciation: 'koe-vid nine-teen vak-SEEN',
      drugClass: 'mRNA vaccine',
      halfLife: 'N/A (immunologic)',
      description: 'mRNA vaccine against SARS-CoV-2.',
      commonUses: 'COVID-19 prevention.',
      sideEffects: 'Injection site pain, fatigue, myocarditis (rare).',
      dosageRange: 'Primary series + boosters',
      onsetOfAction: '1-2 weeks',
      peakTime: '4-6 weeks',
      routes: ['IM'],
      interactions: ['Space other vaccines by 14 days'],
      pregnancyCategory: PregnancyCategory.n,
      conditions: ['COVID-19 prevention'],
      category: MedicationCategory.vaccines,
      addedDate: DateTime(2024, 12, 16),
    ),
    Medication(
      name: 'Tdap Vaccine',
      brandNames: ['Adacel', 'Boostrix'],
      pronunciation: 'tee-dap vak-SEEN',
      drugClass: 'Combination vaccine',
      halfLife: 'N/A (immunologic)',
      description: 'Tetanus-diphtheria-acellular pertussis.',
      commonUses: 'Prevention of tetanus, diphtheria, pertussis.',
      sideEffects: 'Injection site reactions, mild fever.',
      dosageRange: '0.5 mL IM every 10 years',
      onsetOfAction: '1-2 weeks',
      peakTime: '4-6 weeks',
      routes: ['IM'],
      interactions: ['Immunosuppressants'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Tetanus prevention', 'Pertussis prevention'],
      category: MedicationCategory.vaccines,
      addedDate: DateTime(2024, 12, 15),
    ),
    Medication(
      name: 'MMR Vaccine',
      brandNames: ['M-M-R II', 'Priorix'],
      pronunciation: 'em-em-ar vak-SEEN',
      drugClass: 'Live attenuated vaccine',
      halfLife: 'N/A (immunologic)',
      description: 'Measles, mumps, rubella vaccine.',
      commonUses: 'Prevention of measles, mumps, rubella.',
      sideEffects: 'Fever, rash, febrile seizures (rare).',
      dosageRange: 'Two doses (age 12-15 months, 4-6 years)',
      onsetOfAction: '2-4 weeks',
      peakTime: '4-6 weeks',
      routes: ['SC'],
      interactions: ['Immunosuppressants', 'Recent blood products'],
      pregnancyCategory: PregnancyCategory.x,
      conditions: ['MMR prevention'],
      category: MedicationCategory.vaccines,
      addedDate: DateTime(2024, 12, 14),
    ),
    Medication(
      name: 'Shingrix',
      brandNames: ['Shingrix'],
      pronunciation: 'SHIN-griks',
      drugClass: 'Recombinant zoster vaccine',
      halfLife: 'N/A (immunologic)',
      description: 'Recombinant subunit zoster vaccine.',
      commonUses: 'Prevention of shingles (ages 50+).',
      sideEffects: 'Myalgia, fatigue, injection site reactions.',
      dosageRange: '2 doses 2-6 months apart',
      onsetOfAction: '2 weeks',
      peakTime: 'After 2nd dose',
      routes: ['IM'],
      interactions: ['Immunosuppressants'],
      pregnancyCategory: PregnancyCategory.n,
      conditions: ['Shingles prevention'],
      category: MedicationCategory.vaccines,
      addedDate: DateTime(2024, 12, 13),
    ),
    Medication(
      name: 'HPV Vaccine',
      brandNames: ['Gardasil 9'],
      pronunciation: 'aych-pee-vee vak-SEEN',
      drugClass: 'Recombinant vaccine',
      halfLife: 'N/A (immunologic)',
      description: '9-valent HPV vaccine.',
      commonUses: 'Prevention of HPV-related cancers and warts.',
      sideEffects: 'Injection site reactions, syncope.',
      dosageRange: '2-3 doses depending on age',
      onsetOfAction: '1-2 weeks',
      peakTime: 'After complete series',
      routes: ['IM'],
      interactions: ['Immunosuppressants'],
      pregnancyCategory: PregnancyCategory.n,
      conditions: ['HPV prevention', 'Cervical cancer prevention'],
      category: MedicationCategory.vaccines,
      addedDate: DateTime(2024, 12, 12),
    ),

    // ─── ONCOLOGY ────────────────────────────────────────────────────────────
    Medication(
      name: 'Anastrozole',
      brandNames: ['Arimidex'],
      pronunciation: 'a-NAS-troe-zole',
      drugClass: 'Aromatase inhibitor',
      halfLife: '50 hours',
      description: 'Non-steroidal aromatase inhibitor.',
      commonUses: 'Postmenopausal hormone receptor-positive breast cancer.',
      sideEffects: 'Hot flashes, joint pain, osteoporosis.',
      dosageRange: '1 mg once daily',
      onsetOfAction: 'Days',
      peakTime: '2 hours',
      routes: ['Oral'],
      interactions: ['Tamoxifen', 'Estrogen'],
      pregnancyCategory: PregnancyCategory.x,
      conditions: ['Breast cancer'],
      category: MedicationCategory.oncology,
      addedDate: DateTime(2024, 12, 11),
    ),
    Medication(
      name: 'Imatinib',
      brandNames: ['Gleevec'],
      pronunciation: 'i-MAT-i-nib',
      drugClass: 'Tyrosine kinase inhibitor',
      halfLife: '18 hours',
      description: 'BCR-ABL tyrosine kinase inhibitor.',
      commonUses: 'Chronic myeloid leukemia, GIST.',
      sideEffects: 'Edema, nausea, cytopenias, hepatotoxicity.',
      dosageRange: '400-600 mg daily',
      onsetOfAction: 'Weeks',
      peakTime: '2-4 hours',
      routes: ['Oral'],
      interactions: ['Extensive CYP3A4 interactions'],
      pregnancyCategory: PregnancyCategory.d,
      conditions: ['CML', 'GIST', 'ALL (Ph+)'],
      category: MedicationCategory.oncology,
      addedDate: DateTime(2024, 12, 10),
    ),
    Medication(
      name: 'Trastuzumab',
      brandNames: ['Herceptin'],
      pronunciation: 'tras-TOOZ-oo-mab',
      drugClass: 'HER2 monoclonal antibody',
      halfLife: '28.5 days',
      description: 'Anti-HER2 monoclonal antibody.',
      commonUses: 'HER2-positive breast and gastric cancer.',
      sideEffects: 'Cardiotoxicity, infusion reactions, pulmonary toxicity.',
      dosageRange: 'IV every 1-3 weeks (weight-based)',
      onsetOfAction: 'Weeks',
      peakTime: 'End of infusion',
      routes: ['IV', 'SC'],
      interactions: ['Anthracyclines (cardiotoxicity)'],
      pregnancyCategory: PregnancyCategory.d,
      blackBoxWarning:
          'Cardiomyopathy, infusion reactions, pulmonary toxicity, embryofetal toxicity.',
      conditions: ['HER2+ breast cancer', 'HER2+ gastric cancer'],
      category: MedicationCategory.oncology,
      addedDate: DateTime(2024, 12, 9),
    ),
    Medication(
      name: 'Bevacizumab',
      brandNames: ['Avastin'],
      pronunciation: 'be-va-SIZ-oo-mab',
      drugClass: 'VEGF inhibitor',
      halfLife: '20 days',
      description: 'Anti-VEGF monoclonal antibody.',
      commonUses: 'Colorectal, lung, ovarian, brain cancer.',
      sideEffects: 'Bleeding, wound dehiscence, thromboembolism, hypertension.',
      dosageRange: 'IV every 2-3 weeks (weight-based)',
      onsetOfAction: 'Weeks',
      peakTime: 'End of infusion',
      routes: ['IV', 'Intravitreal (ophthalmic)'],
      interactions: ['Irinotecan', 'Sunitinib'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning:
          'GI perforation, wound healing complications, hemorrhage.',
      conditions: [
        'Colorectal cancer',
        'Lung cancer',
        'Ovarian cancer',
        'Wet AMD'
      ],
      category: MedicationCategory.oncology,
      addedDate: DateTime(2024, 12, 8),
    ),
    Medication(
      name: 'Cisplatin',
      brandNames: ['Platinol'],
      pronunciation: 'sis-PLA-tin',
      drugClass: 'Platinum-based chemotherapy',
      halfLife: '30 minutes (alpha); 58-73 hours (beta)',
      description: 'Platinum-based chemotherapeutic.',
      commonUses: 'Testicular, ovarian, bladder, lung cancer.',
      sideEffects: 'Severe nephrotoxicity, ototoxicity, neurotoxicity, emesis.',
      dosageRange: 'Varies by regimen',
      onsetOfAction: 'Days',
      peakTime: 'End of infusion',
      routes: ['IV'],
      interactions: ['Aminoglycosides', 'Loop diuretics', 'Other nephrotoxins'],
      pregnancyCategory: PregnancyCategory.d,
      blackBoxWarning:
          'Severe cumulative nephrotoxicity, ototoxicity, myelosuppression.',
      conditions: ['Testicular cancer', 'Ovarian cancer', 'Bladder cancer'],
      category: MedicationCategory.oncology,
      addedDate: DateTime(2024, 12, 7),
    ),

    // ─── PEDIATRIC-SPECIFIC ──────────────────────────────────────────────────
    Medication(
      name: 'Amoxicillin Liquid (Pediatric)',
      brandNames: ['Amoxil Liquid'],
      pronunciation: 'a-mox-i-SIL-in',
      drugClass: 'Penicillin antibiotic',
      halfLife: '1-2 hours',
      description: 'Oral suspension penicillin for children.',
      commonUses: 'Pediatric ear infections, strep, pneumonia.',
      sideEffects: 'Diarrhea, rash, allergic reactions.',
      dosageRange: '20-90 mg/kg/day divided',
      onsetOfAction: '1-2 hours',
      peakTime: '1-2 hours',
      routes: ['Oral'],
      interactions: ['Probenecid', 'OCPs'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: [
        'Pediatric otitis media',
        'Pediatric strep',
        'Pediatric UTI'
      ],
      category: MedicationCategory.pediatric,
      addedDate: DateTime(2024, 12, 6),
    ),
    Medication(
      name: 'Children\'s Ibuprofen',
      brandNames: ['Children\'s Advil', 'Children\'s Motrin'],
      pronunciation: 'eye-byoo-PROH-fen',
      drugClass: 'Pediatric NSAID',
      halfLife: '2-4 hours',
      description: 'Pediatric ibuprofen for fever/pain.',
      commonUses: 'Pediatric fever, pain, teething.',
      sideEffects: 'GI upset, ulcers, kidney effects.',
      dosageRange: '10 mg/kg every 6-8 hours',
      onsetOfAction: '30 minutes',
      peakTime: '1-2 hours',
      routes: ['Oral'],
      interactions: ['Aspirin', 'Anticoagulants'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Pediatric fever', 'Pediatric pain', 'Teething'],
      category: MedicationCategory.pediatric,
      addedDate: DateTime(2024, 12, 5),
    ),
    Medication(
      name: 'Children\'s Acetaminophen',
      brandNames: ['Children\'s Tylenol', 'FeverAll'],
      pronunciation: 'a-seet-a-MIN-oh-fen',
      drugClass: 'Pediatric analgesic/antipyretic',
      halfLife: '2-3 hours',
      description: 'Pediatric acetaminophen.',
      commonUses: 'Pediatric fever, pain.',
      sideEffects: 'Rare at proper doses; liver damage with overdose.',
      dosageRange: '10-15 mg/kg every 4-6 hours',
      onsetOfAction: '30-60 minutes',
      peakTime: '1 hour',
      routes: ['Oral', 'Rectal'],
      interactions: ['Warfarin'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['Pediatric fever', 'Pediatric pain'],
      category: MedicationCategory.pediatric,
      addedDate: DateTime(2024, 12, 4),
    ),
    Medication(
      name: 'Methylphenidate',
      brandNames: ['Ritalin', 'Concerta', 'Metadate'],
      pronunciation: 'meth-il-FEN-i-date',
      drugClass: 'CNS stimulant',
      halfLife: '2-4 hours (IR); 3.5 hours (OROS)',
      description: 'CNS stimulant for ADHD.',
      commonUses: 'ADHD, narcolepsy.',
      sideEffects:
          'Appetite suppression, insomnia, tachycardia, growth suppression.',
      dosageRange: '5-60 mg daily (divided for IR)',
      onsetOfAction: '20-60 minutes',
      peakTime: '1-2 hours',
      routes: ['Oral', 'Transdermal'],
      interactions: ['MAOIs', 'Tricyclics', 'Clonidine'],
      pregnancyCategory: PregnancyCategory.c,
      schedule: ControlledSchedule.ii,
      blackBoxWarning: 'High abuse potential; cardiovascular events.',
      conditions: ['ADHD', 'Narcolepsy'],
      category: MedicationCategory.pediatric,
      addedDate: DateTime(2024, 12, 3),
    ),
    Medication(
      name: 'Guanfacine',
      brandNames: ['Intuniv', 'Tenex'],
      pronunciation: 'GWAN-fa-seen',
      drugClass: 'Alpha-2A agonist',
      halfLife: '17 hours',
      description: 'Selective alpha-2A adrenergic agonist.',
      commonUses: 'ADHD (children), hypertension.',
      sideEffects: 'Sedation, hypotension, bradycardia.',
      dosageRange: '1-7 mg once daily (ER); 1-3 mg/day divided (IR)',
      onsetOfAction: '1 week',
      peakTime: '5 hours (ER)',
      routes: ['Oral'],
      interactions: ['CNS depressants', 'CYP3A4 drugs'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['ADHD', 'Hypertension', 'Tics'],
      category: MedicationCategory.pediatric,
      addedDate: DateTime(2024, 12, 2),
    ),
    // ─── ADDITIONAL COMMONLY-SEARCHED MEDICATIONS ────────────────────────────
    Medication(
      name: 'Atomoxetine',
      brandNames: ['Strattera'],
      pronunciation: 'at-oh-MOX-e-teen',
      drugClass: 'Selective norepinephrine reuptake inhibitor',
      halfLife: '5 hours',
      description: 'Non-stimulant ADHD medication.',
      commonUses: 'ADHD.',
      sideEffects: 'GI upset, sleep issues, increased BP/HR, suicidality.',
      dosageRange: '40-100 mg daily',
      onsetOfAction: '1-4 weeks',
      peakTime: '1-2 hours',
      routes: ['Oral'],
      interactions: ['MAOIs', 'CYP2D6 inhibitors', 'Albuterol'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning: 'Increased suicidality in children/adolescents.',
      conditions: ['ADHD'],
      category: MedicationCategory.neurological,
      addedDate: DateTime(2024, 12, 1),
    ),
    Medication(
      name: 'Lisdexamfetamine',
      brandNames: ['Vyvanse'],
      pronunciation: 'lis-dex-am-FET-a-meen',
      drugClass: 'CNS stimulant (prodrug of dextroamphetamine)',
      halfLife: '1 hour (prodrug); 10-12 hours (dex)',
      description: 'Prodrug of dextroamphetamine.',
      commonUses: 'ADHD, binge eating disorder.',
      sideEffects: 'Appetite suppression, insomnia, tachycardia, dependence.',
      dosageRange: '30-70 mg once daily',
      onsetOfAction: '1-2 hours',
      peakTime: '3.5 hours',
      routes: ['Oral'],
      interactions: ['MAOIs', 'Acidifying agents', 'Proton pump inhibitors'],
      pregnancyCategory: PregnancyCategory.c,
      schedule: ControlledSchedule.ii,
      blackBoxWarning: 'High abuse potential; cardiovascular events.',
      conditions: ['ADHD', 'Binge eating disorder'],
      category: MedicationCategory.neurological,
      addedDate: DateTime(2024, 11, 30),
    ),
    Medication(
      name: 'Amphetamine/Dextroamphetamine',
      brandNames: ['Adderall', 'Adderall XR', 'Mydayis'],
      pronunciation: 'am-FET-a-meen / dex-tro-am-FET-a-meen',
      drugClass: 'CNS stimulant',
      halfLife: '9-14 hours',
      description: 'Mixed amphetamine salts.',
      commonUses: 'ADHD, narcolepsy.',
      sideEffects:
          'Appetite suppression, insomnia, dependence, cardiac effects.',
      dosageRange: '5-40 mg daily',
      onsetOfAction: '30-60 minutes',
      peakTime: '3 hours',
      routes: ['Oral'],
      interactions: ['MAOIs', 'Acidifying agents', 'Sympathomimetics'],
      pregnancyCategory: PregnancyCategory.c,
      schedule: ControlledSchedule.ii,
      blackBoxWarning: 'High abuse potential; sudden death in cardiac issues.',
      conditions: ['ADHD', 'Narcolepsy'],
      category: MedicationCategory.neurological,
      addedDate: DateTime(2024, 11, 29),
    ),
    Medication(
      name: 'Modafinil',
      brandNames: ['Provigil'],
      pronunciation: 'moe-DAF-i-nil',
      drugClass: 'Wakefulness-promoting agent',
      halfLife: '15 hours',
      description: 'Non-amphetamine wakefulness agent.',
      commonUses: 'Narcolepsy, shift work sleep disorder, OSA-related fatigue.',
      sideEffects: 'Headache, anxiety, SJS (rare), cardiovascular effects.',
      dosageRange: '200 mg once daily',
      onsetOfAction: '2 hours',
      peakTime: '2-4 hours',
      routes: ['Oral'],
      interactions: ['OCPs (reduces)', 'CYP3A4 substrates'],
      pregnancyCategory: PregnancyCategory.c,
      schedule: ControlledSchedule.iv,
      conditions: ['Narcolepsy', 'Shift work sleep disorder'],
      category: MedicationCategory.neurological,
      addedDate: DateTime(2024, 11, 28),
    ),
    Medication(
      name: 'Buprenorphine/Naloxone',
      brandNames: ['Suboxone', 'Zubsolv'],
      pronunciation: 'byoo-pre-NOR-feen / nal-OX-one',
      drugClass: 'Partial opioid agonist + antagonist',
      halfLife: '24-42 hours',
      description: 'Partial opioid agonist combined with naloxone.',
      commonUses: 'Opioid use disorder.',
      sideEffects: 'Constipation, headache, withdrawal if injected.',
      dosageRange: '4-24 mg daily sublingual',
      onsetOfAction: '30 minutes',
      peakTime: '1-3 hours',
      routes: ['Sublingual', 'Buccal', 'Transdermal'],
      interactions: ['CNS depressants', 'CYP3A4 inhibitors', 'Benzos'],
      pregnancyCategory: PregnancyCategory.c,
      schedule: ControlledSchedule.iii,
      blackBoxWarning:
          'Respiratory depression with benzodiazepines or CNS depressants.',
      conditions: ['Opioid use disorder', 'Chronic pain'],
      category: MedicationCategory.specialized,
      addedDate: DateTime(2024, 11, 27),
    ),
    Medication(
      name: 'Methadone',
      brandNames: ['Dolophine', 'Methadose'],
      pronunciation: 'METH-a-done',
      drugClass: 'Long-acting opioid agonist',
      halfLife: '15-60 hours',
      description: 'Long-acting synthetic opioid.',
      commonUses: 'Opioid use disorder, chronic pain.',
      sideEffects: 'QT prolongation, respiratory depression, constipation.',
      dosageRange: 'Individualized; OUD typically 60-120 mg daily',
      onsetOfAction: '30-60 minutes',
      peakTime: '1-7.5 hours',
      routes: ['Oral', 'IV', 'IM'],
      interactions: ['QT-prolonging drugs', 'CYP3A4 substrates', 'Benzos'],
      pregnancyCategory: PregnancyCategory.c,
      schedule: ControlledSchedule.ii,
      blackBoxWarning: 'QT prolongation, respiratory depression, addiction.',
      conditions: ['Opioid use disorder', 'Chronic pain'],
      category: MedicationCategory.analgesics,
      addedDate: DateTime(2024, 11, 26),
    ),
    Medication(
      name: 'Sumatriptan',
      brandNames: ['Imitrex'],
      pronunciation: 'soo-ma-TRIP-tan',
      drugClass: 'Triptan (5-HT1B/1D agonist)',
      halfLife: '2-3 hours',
      description: 'Serotonin receptor agonist for migraine.',
      commonUses: 'Migraine, cluster headache.',
      sideEffects: 'Chest tightness, flushing, paresthesias.',
      dosageRange: '25-100 mg oral (max 200 mg/day)',
      onsetOfAction: '30 minutes (oral); 10 min (SC)',
      peakTime: '1-2 hours',
      routes: ['Oral', 'SC', 'Nasal'],
      interactions: ['MAOIs', 'SSRIs', 'Ergots', 'Other triptans'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Migraine', 'Cluster headache'],
      category: MedicationCategory.neurological,
      addedDate: DateTime(2024, 11, 25),
    ),
    Medication(
      name: 'Rizatriptan',
      brandNames: ['Maxalt'],
      pronunciation: 'rye-za-TRIP-tan',
      drugClass: 'Triptan',
      halfLife: '2-3 hours',
      description: 'Selective serotonin receptor agonist.',
      commonUses: 'Migraine.',
      sideEffects: 'Chest pressure, dizziness, fatigue.',
      dosageRange: '5-10 mg at onset (may repeat after 2 hr)',
      onsetOfAction: '30-60 minutes',
      peakTime: '1-1.5 hours',
      routes: ['Oral', 'ODT'],
      interactions: ['MAOIs', 'Propranolol', 'Ergots'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Migraine'],
      category: MedicationCategory.neurological,
      addedDate: DateTime(2024, 11, 24),
    ),
    Medication(
      name: 'Melatonin',
      brandNames: ['generic'],
      pronunciation: 'mel-a-TOE-nin',
      drugClass: 'Hormone (pineal gland)',
      halfLife: '20-50 minutes',
      description: 'Pineal hormone supplement.',
      commonUses: 'Insomnia, jet lag, shift work.',
      sideEffects: 'Daytime sleepiness, vivid dreams.',
      dosageRange: '0.5-10 mg at bedtime',
      onsetOfAction: '30-60 minutes',
      peakTime: '30-60 minutes',
      routes: ['Oral', 'Sublingual'],
      interactions: ['Warfarin', 'Sedatives', 'Fluvoxamine'],
      pregnancyCategory: PregnancyCategory.n,
      conditions: ['Insomnia', 'Jet lag', 'Sleep-wake disorders'],
      category: MedicationCategory.neurological,
      addedDate: DateTime(2024, 11, 23),
    ),
    Medication(
      name: 'Diphenhydramine',
      brandNames: ['Benadryl', 'Unisom SleepGels'],
      pronunciation: 'dye-fen-HYE-dra-meen',
      drugClass: 'First-generation antihistamine',
      halfLife: '4-8 hours',
      description: 'Sedating first-generation H1 antihistamine.',
      commonUses: 'Allergies, motion sickness, insomnia, dystonic reactions.',
      sideEffects: 'Sedation, anticholinergic effects, confusion (elderly).',
      dosageRange: '25-50 mg every 4-6 hours',
      onsetOfAction: '15-30 minutes',
      peakTime: '2-3 hours',
      routes: ['Oral', 'IV', 'IM', 'Topical'],
      interactions: ['Alcohol', 'CNS depressants', 'MAOIs'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['Allergies', 'Insomnia', 'Motion sickness', 'Dystonia'],
      category: MedicationCategory.specialized,
      addedDate: DateTime(2024, 11, 22),
    ),
    Medication(
      name: 'Cetirizine',
      brandNames: ['Zyrtec'],
      pronunciation: 'se-TI-ri-zeen',
      drugClass: 'Second-generation antihistamine',
      halfLife: '8 hours',
      description: 'Low-sedating H1 antihistamine.',
      commonUses: 'Allergies, chronic urticaria.',
      sideEffects: 'Mild drowsiness, dry mouth.',
      dosageRange: '5-10 mg once daily',
      onsetOfAction: '1 hour',
      peakTime: '1 hour',
      routes: ['Oral'],
      interactions: ['CNS depressants'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['Allergies', 'Urticaria', 'Hay fever'],
      category: MedicationCategory.specialized,
      addedDate: DateTime(2024, 11, 21),
    ),
    Medication(
      name: 'Loratadine',
      brandNames: ['Claritin', 'Alavert'],
      pronunciation: 'lor-AT-a-deen',
      drugClass: 'Second-generation antihistamine',
      halfLife: '8-14 hours (metabolite 28 hours)',
      description: 'Non-sedating H1 antihistamine.',
      commonUses: 'Allergies, chronic urticaria.',
      sideEffects: 'Minimal - headache, fatigue.',
      dosageRange: '10 mg once daily',
      onsetOfAction: '1-3 hours',
      peakTime: '1-2 hours',
      routes: ['Oral'],
      interactions: ['CYP3A4/2D6 inhibitors'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['Allergies', 'Urticaria'],
      category: MedicationCategory.specialized,
      addedDate: DateTime(2024, 11, 20),
    ),
    Medication(
      name: 'Fexofenadine',
      brandNames: ['Allegra'],
      pronunciation: 'fex-o-FEN-a-deen',
      drugClass: 'Second-generation antihistamine',
      halfLife: '14 hours',
      description: 'Non-sedating H1 antihistamine.',
      commonUses: 'Allergies, chronic urticaria.',
      sideEffects: 'Headache, minimal drowsiness.',
      dosageRange: '60 mg twice daily or 180 mg once daily',
      onsetOfAction: '1 hour',
      peakTime: '2.6 hours',
      routes: ['Oral'],
      interactions: ['Fruit juices (reduces absorption)', 'Antacids'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Allergies', 'Urticaria'],
      category: MedicationCategory.specialized,
      addedDate: DateTime(2024, 11, 19),
    ),
    Medication(
      name: 'Guaifenesin',
      brandNames: ['Mucinex', 'Robitussin'],
      pronunciation: 'gwye-FEN-e-sin',
      drugClass: 'Expectorant',
      halfLife: '1 hour',
      description: 'Mucolytic expectorant.',
      commonUses: 'Productive cough, chest congestion.',
      sideEffects: 'GI upset, dizziness.',
      dosageRange: '200-400 mg every 4 hours (max 2400 mg/day)',
      onsetOfAction: '15-30 minutes',
      peakTime: '15 minutes',
      routes: ['Oral'],
      interactions: ['Minimal'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Cough', 'Congestion', 'Bronchitis'],
      category: MedicationCategory.respiratory,
      addedDate: DateTime(2024, 11, 18),
    ),
    Medication(
      name: 'Dextromethorphan',
      brandNames: ['Delsym', 'Robitussin DM'],
      pronunciation: 'dex-troe-meth-OR-fan',
      drugClass: 'Antitussive',
      halfLife: '1.4-3.9 hours',
      description: 'Central antitussive.',
      commonUses: 'Non-productive cough.',
      sideEffects: 'Drowsiness, GI upset, dissociation (high doses).',
      dosageRange: '10-30 mg every 4-8 hours',
      onsetOfAction: '15-30 minutes',
      peakTime: '2-4 hours',
      routes: ['Oral'],
      interactions: ['MAOIs', 'SSRIs (serotonin syndrome)', 'Alcohol'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Cough'],
      category: MedicationCategory.respiratory,
      addedDate: DateTime(2024, 11, 17),
    ),
    Medication(
      name: 'Pseudoephedrine',
      brandNames: ['Sudafed'],
      pronunciation: 'soo-doe-e-FED-rin',
      drugClass: 'Alpha-adrenergic agonist',
      halfLife: '4-8 hours',
      description: 'Nasal decongestant.',
      commonUses: 'Nasal congestion.',
      sideEffects: 'Insomnia, tachycardia, hypertension.',
      dosageRange: '30-60 mg every 4-6 hours',
      onsetOfAction: '30 minutes',
      peakTime: '1-2 hours',
      routes: ['Oral'],
      interactions: ['MAOIs', 'Beta-blockers', 'Methyldopa'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Nasal congestion', 'Sinus congestion'],
      category: MedicationCategory.respiratory,
      addedDate: DateTime(2024, 11, 16),
    ),
    Medication(
      name: 'Calcium Carbonate',
      brandNames: ['Tums', 'Caltrate'],
      pronunciation: 'KAL-see-um KAR-boe-nate',
      drugClass: 'Antacid / calcium supplement',
      halfLife: 'Not well-characterized',
      description: 'Antacid and calcium supplement.',
      commonUses: 'Heartburn, calcium supplementation, hyperphosphatemia.',
      sideEffects: 'Constipation, hypercalcemia, milk-alkali syndrome.',
      dosageRange: '500-1500 mg as needed',
      onsetOfAction: 'Minutes',
      peakTime: 'Minutes',
      routes: ['Oral'],
      interactions: [
        'Tetracyclines',
        'Fluoroquinolones',
        'Iron',
        'Levothyroxine'
      ],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Heartburn', 'Osteoporosis', 'Hypocalcemia'],
      category: MedicationCategory.gastrointestinal,
      addedDate: DateTime(2024, 11, 15),
    ),
    Medication(
      name: 'Iron (Ferrous Sulfate)',
      brandNames: ['Feosol', 'Slow FE'],
      pronunciation: 'FER-us SUL-fate',
      drugClass: 'Iron supplement',
      halfLife: '6 hours (elemental)',
      description: 'Oral iron supplement.',
      commonUses: 'Iron deficiency anemia.',
      sideEffects: 'Constipation, nausea, black stools.',
      dosageRange: '325 mg 1-3×/day (65 mg elemental)',
      onsetOfAction: '3-10 days (reticulocytes)',
      peakTime: 'Variable',
      routes: ['Oral', 'IV'],
      interactions: [
        'Levothyroxine',
        'Quinolones',
        'Antacids',
        'Tetracyclines'
      ],
      pregnancyCategory: PregnancyCategory.a,
      conditions: ['Iron deficiency anemia'],
      category: MedicationCategory.specialized,
      addedDate: DateTime(2024, 11, 14),
    ),
    Medication(
      name: 'Vitamin D3 (Cholecalciferol)',
      brandNames: ['Drisdol', 'generic'],
      pronunciation: 'VYE-ta-min dee',
      drugClass: 'Fat-soluble vitamin',
      halfLife: '15 days',
      description: 'Cholecalciferol supplement.',
      commonUses: 'Vitamin D deficiency, osteoporosis prevention.',
      sideEffects: 'Hypercalcemia (at very high doses).',
      dosageRange: '600-5000 IU daily',
      onsetOfAction: 'Weeks',
      peakTime: 'Days',
      routes: ['Oral'],
      interactions: ['Thiazide diuretics', 'Digoxin'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Vitamin D deficiency', 'Osteoporosis'],
      category: MedicationCategory.specialized,
      addedDate: DateTime(2024, 11, 13),
    ),
    Medication(
      name: 'Folic Acid',
      brandNames: ['Folvite', 'generic'],
      pronunciation: 'FOE-lik AS-id',
      drugClass: 'Water-soluble vitamin (B9)',
      halfLife: '1 hour',
      description: 'Folate supplement.',
      commonUses: 'Folate deficiency, pregnancy supplementation.',
      sideEffects: 'Rare - nausea, bitter taste.',
      dosageRange: '0.4-5 mg daily',
      onsetOfAction: 'Weeks',
      peakTime: '1 hour',
      routes: ['Oral', 'IM', 'IV'],
      interactions: ['Methotrexate', 'Sulfasalazine', 'Phenytoin'],
      pregnancyCategory: PregnancyCategory.a,
      conditions: ['Folate deficiency', 'Pregnancy', 'Megaloblastic anemia'],
      category: MedicationCategory.specialized,
      addedDate: DateTime(2024, 11, 12),
    ),
    Medication(
      name: 'Cyanocobalamin (B12)',
      brandNames: ['Nascobal'],
      pronunciation: 'sye-an-oh-koe-BAL-a-min',
      drugClass: 'Water-soluble vitamin',
      halfLife: '6 days',
      description: 'Vitamin B12 supplement.',
      commonUses: 'B12 deficiency, pernicious anemia.',
      sideEffects: 'Injection site reactions, rare allergic reactions.',
      dosageRange: '1000 mcg IM monthly (deficiency); varies oral',
      onsetOfAction: '1 week (reticulocytes)',
      peakTime: 'Variable',
      routes: ['Oral', 'IM', 'Nasal', 'SC'],
      interactions: ['Metformin', 'PPIs', 'Chloramphenicol'],
      pregnancyCategory: PregnancyCategory.a,
      conditions: ['B12 deficiency', 'Pernicious anemia'],
      category: MedicationCategory.specialized,
      addedDate: DateTime(2024, 11, 11),
    ),
    Medication(
      name: 'Magnesium Oxide',
      brandNames: ['Mag-Ox'],
      pronunciation: 'mag-NEE-zee-um OX-ide',
      drugClass: 'Mineral supplement',
      halfLife: 'Variable',
      description: 'Magnesium supplement.',
      commonUses: 'Magnesium deficiency, migraine prophylaxis, constipation.',
      sideEffects: 'Diarrhea, GI upset.',
      dosageRange: '400-800 mg daily',
      onsetOfAction: 'Hours',
      peakTime: 'Variable',
      routes: ['Oral', 'IV', 'IM'],
      interactions: ['Tetracyclines', 'Quinolones', 'Bisphosphonates'],
      pregnancyCategory: PregnancyCategory.a,
      conditions: ['Magnesium deficiency', 'Constipation', 'Migraine'],
      category: MedicationCategory.specialized,
      addedDate: DateTime(2024, 11, 10),
    ),
    Medication(
      name: 'Potassium Chloride',
      brandNames: ['K-Dur', 'Klor-Con', 'Micro-K'],
      pronunciation: 'poe-TAS-ee-um KLOR-ide',
      drugClass: 'Electrolyte supplement',
      halfLife: 'Variable',
      description: 'Potassium supplement.',
      commonUses: 'Hypokalemia.',
      sideEffects: 'GI ulceration, hyperkalemia.',
      dosageRange: '20-100 mEq daily',
      onsetOfAction: 'Hours',
      peakTime: '1-2 hours',
      routes: ['Oral', 'IV'],
      interactions: ['ACE inhibitors', 'ARBs', 'K-sparing diuretics', 'NSAIDs'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning: 'IV must be diluted; never IV push (fatal).',
      conditions: ['Hypokalemia'],
      category: MedicationCategory.specialized,
      addedDate: DateTime(2024, 11, 9),
    ),
    Medication(
      name: 'Levonorgestrel (Plan B)',
      brandNames: ['Plan B One-Step', 'Next Choice'],
      pronunciation: 'lee-voe-nor-JES-trel',
      drugClass: 'Progestin (emergency contraception)',
      halfLife: '24-55 hours',
      description: 'Emergency contraceptive.',
      commonUses: 'Emergency contraception within 72 hours.',
      sideEffects: 'Nausea, menstrual changes, fatigue.',
      dosageRange: '1.5 mg single dose',
      onsetOfAction: 'Hours',
      peakTime: '2 hours',
      routes: ['Oral'],
      interactions: ['CYP3A4 inducers', 'Antibiotics (possibly)'],
      pregnancyCategory: PregnancyCategory.x,
      conditions: ['Emergency contraception'],
      category: MedicationCategory.hormonal,
      addedDate: DateTime(2024, 11, 8),
    ),
    Medication(
      name: 'Ethinyl Estradiol/Norethindrone',
      brandNames: ['Ortho-Novum', 'Loestrin', 'Junel'],
      pronunciation: 'ETH-i-nil es-tra-DYE-ole / nor-eth-IN-drone',
      drugClass: 'Combined oral contraceptive',
      halfLife: '8-24 hours',
      description: 'Combined estrogen-progestin contraceptive.',
      commonUses: 'Contraception, menstrual regulation, acne, PCOS.',
      sideEffects: 'Thromboembolism, nausea, breast tenderness, spotting.',
      dosageRange: 'One tablet daily × 28-day cycle',
      onsetOfAction: '7 days',
      peakTime: '1-2 hours',
      routes: ['Oral'],
      interactions: [
        'CYP3A4 inducers',
        'Antibiotics (possibly)',
        'St. John\'s Wort'
      ],
      pregnancyCategory: PregnancyCategory.x,
      blackBoxWarning: 'Thromboembolic events, especially in smokers >35 yo.',
      conditions: ['Contraception', 'Acne', 'PCOS', 'Menstrual regulation'],
      category: MedicationCategory.hormonal,
      addedDate: DateTime(2024, 11, 7),
    ),
    Medication(
      name: 'Mifepristone',
      brandNames: ['Mifeprex', 'Korlym'],
      pronunciation: 'mif-eh-PRIS-tone',
      drugClass: 'Progesterone/glucocorticoid receptor antagonist',
      halfLife: '18 hours',
      description: 'Selective progesterone receptor modulator.',
      commonUses: 'Medical abortion (with misoprostol), Cushing syndrome.',
      sideEffects: 'Uterine bleeding, cramping, GI upset.',
      dosageRange: '200 mg once (abortion); varies for other uses',
      onsetOfAction: 'Hours',
      peakTime: '90 minutes',
      routes: ['Oral'],
      interactions: ['CYP3A4 substrates', 'Corticosteroids', 'Warfarin'],
      pregnancyCategory: PregnancyCategory.x,
      blackBoxWarning:
          'Serious infections and bleeding; requires certified prescriber.',
      conditions: ['Medical abortion', 'Cushing syndrome'],
      category: MedicationCategory.hormonal,
      addedDate: DateTime(2024, 11, 6),
    ),
    Medication(
      name: 'Sumatriptan-Naproxen',
      brandNames: ['Treximet'],
      pronunciation: 'soo-ma-TRIP-tan / na-PROX-en',
      drugClass: 'Triptan + NSAID combination',
      halfLife: '2-3 hr (sumatriptan); 12-17 hr (naproxen)',
      description: 'Combination migraine medication.',
      commonUses: 'Migraine.',
      sideEffects: 'GI upset, chest tightness, paresthesias.',
      dosageRange: '1 tablet (85mg/500mg) at onset',
      onsetOfAction: '30-60 minutes',
      peakTime: '1-2 hours',
      routes: ['Oral'],
      interactions: ['MAOIs', 'SSRIs', 'Warfarin', 'Lithium'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Migraine'],
      category: MedicationCategory.neurological,
      addedDate: DateTime(2024, 11, 5),
    ),
    Medication(
      name: 'Pantoprazole-Mg',
      brandNames: ['Protonix Mg'],
      pronunciation: 'pan-TOE-pra-zole',
      drugClass: 'PPI',
      halfLife: '1 hour',
      description: 'Magnesium salt of pantoprazole.',
      commonUses: 'GERD, erosive esophagitis.',
      sideEffects: 'Headache, diarrhea.',
      dosageRange: '40 mg daily',
      onsetOfAction: '1 hour',
      peakTime: '2.5 hours',
      routes: ['Oral'],
      interactions: ['Methotrexate', 'Warfarin'],
      pregnancyCategory: PregnancyCategory.b,
      conditions: ['GERD', 'Erosive esophagitis'],
      category: MedicationCategory.gastrointestinal,
      addedDate: DateTime(2024, 11, 4),
    ),
    Medication(
      name: 'Hydroxyzine',
      brandNames: ['Atarax', 'Vistaril'],
      pronunciation: 'hye-DROX-i-zeen',
      drugClass: 'First-generation antihistamine',
      halfLife: '20 hours',
      description: 'Sedating H1 antihistamine with anxiolytic properties.',
      commonUses: 'Anxiety, pruritus, sedation.',
      sideEffects: 'Sedation, dry mouth, QT prolongation.',
      dosageRange: '25-100 mg 4×/day',
      onsetOfAction: '15-30 minutes',
      peakTime: '2 hours',
      routes: ['Oral', 'IM'],
      interactions: ['CNS depressants', 'QT-prolonging drugs'],
      pregnancyCategory: PregnancyCategory.c,
      conditions: ['Anxiety', 'Itching', 'Nausea'],
      category: MedicationCategory.specialized,
      addedDate: DateTime(2024, 11, 3),
    ),
    Medication(
      name: 'Prochlorperazine',
      brandNames: ['Compazine'],
      pronunciation: 'proe-klor-PER-a-zeen',
      drugClass: 'Phenothiazine antipsychotic / antiemetic',
      halfLife: '6-10 hours',
      description: 'Phenothiazine antipsychotic used primarily for nausea.',
      commonUses: 'Nausea, vomiting, vertigo, psychosis.',
      sideEffects: 'EPS, sedation, QT prolongation.',
      dosageRange: '5-10 mg every 6-8 hours',
      onsetOfAction: '30-40 minutes (oral)',
      peakTime: '3-4 hours',
      routes: ['Oral', 'IV', 'IM', 'Rectal'],
      interactions: ['CNS depressants', 'QT-prolonging drugs'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning: 'Increased mortality in elderly with dementia.',
      conditions: ['Nausea', 'Vertigo', 'Psychosis'],
      category: MedicationCategory.gastrointestinal,
      addedDate: DateTime(2024, 11, 2),
    ),
    Medication(
      name: 'Promethazine',
      brandNames: ['Phenergan'],
      pronunciation: 'proe-METH-a-zeen',
      drugClass: 'Phenothiazine antihistamine/antiemetic',
      halfLife: '9-16 hours',
      description: 'Phenothiazine with antihistamine effects.',
      commonUses: 'Nausea, motion sickness, allergies, sedation.',
      sideEffects:
          'Severe sedation, respiratory depression (especially children).',
      dosageRange: '12.5-25 mg every 4-6 hours',
      onsetOfAction: '20 minutes',
      peakTime: '2-3 hours',
      routes: ['Oral', 'IV', 'IM', 'Rectal'],
      interactions: ['CNS depressants', 'MAOIs', 'Anticholinergics'],
      pregnancyCategory: PregnancyCategory.c,
      blackBoxWarning:
          'Contraindicated in children <2 years (respiratory depression).',
      conditions: ['Nausea', 'Motion sickness', 'Allergies', 'Sedation'],
      category: MedicationCategory.gastrointestinal,
      addedDate: DateTime(2024, 11, 1),
    ),
    Medication(
      name: 'Methocarbamol-ASA',
      brandNames: ['Robaxisal'],
      pronunciation: 'meth-oh-KAR-ba-mol / AS-pir-in',
      drugClass: 'Muscle relaxant + salicylate combo',
      halfLife: '1-2 hours',
      description: 'Combination muscle relaxant.',
      commonUses: 'Musculoskeletal pain.',
      sideEffects: 'Drowsiness, GI upset.',
      dosageRange: '2 tablets 4×/day',
      onsetOfAction: '30 minutes',
      peakTime: '1-2 hours',
      routes: ['Oral'],
      interactions: ['Warfarin', 'CNS depressants', 'NSAIDs'],
      pregnancyCategory: PregnancyCategory.d,
      conditions: ['Muscle spasm'],
      category: MedicationCategory.muscleRelaxants,
      addedDate: DateTime(2024, 10, 31),
    ),
  ]; // End of _medicationDatabase

  // ─── Glass Helpers ─────────────────────────────────────────────────────────

  Widget _glassCard({
    required Widget child,
    double radius = 20,
    EdgeInsets padding = const EdgeInsets.all(16),
    Color? tintColor,
    double tintOpacity = 0.10,
    double blur = 14,
  }) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(radius),
      // Painted glass: nothing but a flat gradient sits behind these cards,
      // and the A–Z list has ~250 of them. RepaintBoundary isolates each.
      child: RepaintBoundary(
        child: Container(
          decoration: BoxDecoration(
            color: tintColor != null
                ? tintColor.withOpacity(tintOpacity)
                : Colors.white.withOpacity(0.07),
            borderRadius: BorderRadius.circular(radius),
            border: Border.all(
              color: Colors.white.withOpacity(0.12),
              width: 1,
            ),
          ),
          padding: padding,
          child: child,
        ),
      ),
    );
  }

  Widget _glassPill({required Widget child, EdgeInsets? padding, Color? tint}) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(100),
      child: RepaintBoundary(
        child: Container(
          padding: padding ??
              const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: tint?.withOpacity(0.18) ?? Colors.white.withOpacity(0.08),
            borderRadius: BorderRadius.circular(100),
            border: Border.all(
              color: tint?.withOpacity(0.35) ?? Colors.white.withOpacity(0.14),
              width: 1,
            ),
          ),
          child: child,
        ),
      ),
    );
  }

  Widget _coralGradientIcon(IconData icon, {double size = 22}) {
    return ShaderMask(
      shaderCallback: (r) => _Jovi.coralGradient.createShader(r),
      child: Icon(icon, size: size, color: Colors.white),
    );
  }

  Widget _sectionHeader(String label, {IconData? icon, Widget? trailing}) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 8, 4, 10),
      child: Row(
        children: [
          if (icon != null) ...[
            _coralGradientIcon(icon, size: 18),
            const SizedBox(width: 8),
          ],
          Expanded(
            child: Text(
              label.toUpperCase(),
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w700,
                fontSize: 12,
                letterSpacing: 1.2,
              ),
            ),
          ),
          if (trailing != null) trailing,
        ],
      ),
    );
  }

  void _showLoginRequiredDialog() {
    showCupertinoDialog<void>(
      context: context,
      builder: (ctx) => CupertinoAlertDialog(
        title: const Text('Sign in to save'),
        content: const Padding(
          padding: EdgeInsets.only(top: 8),
          child: Text(
              'Favorites and recently viewed sync across your devices once you’re signed in.'),
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

  void _showShareDialog(Medication med) {
    final shareText = '''${med.displayName}
${med.pronunciation != 'Not specified' ? '[${med.pronunciation}]\n' : ''}
Drug Class: ${med.drugClass}
Half-life: ${med.halfLife}
Time to ~97% cleared: ${_clearanceTimeDescription(med)}

Common Uses: ${med.commonUses}
Dosage Range: ${med.dosageRange}
Onset: ${med.onsetOfAction}
Peak: ${med.peakTime}
Routes: ${med.routes.join(", ")}

Side Effects: ${med.sideEffects}
${med.interactions.isNotEmpty ? 'Key Interactions: ${med.interactions.join(", ")}\n' : ''}
Pregnancy Category: ${med.pregnancyCategory.label}
${med.schedule != ControlledSchedule.none ? 'DEA Schedule: ${med.schedule.label}\n' : ''}${med.blackBoxWarning != null ? '\n⚠️ BLACK BOX WARNING:\n${med.blackBoxWarning}\n' : ''}
For reference only — not medical advice.
— via Jovi Health''';

    Clipboard.setData(ClipboardData(text: shareText));
    // Haptic and toast on the same frame; no dialog to dismiss.
    HapticFeedback.mediumImpact();
    _toast('${med.name} copied. Paste it anywhere to share.', isSuccess: true);
  }

  String _clearanceTimeDescription(Medication med) {
    final h = med.halfLifeHours;
    if (h <= 0) return '—';
    final total = h * 5;
    if (total < 1) {
      final mins = (total * 60).round();
      return '≈ $mins minutes';
    }
    if (total < 24) {
      return '≈ ${total.toStringAsFixed(total >= 10 ? 0 : 1)} hours';
    }
    final days = total / 24;
    return '≈ ${days.toStringAsFixed(days >= 10 ? 0 : 1)} days';
  }

  void _navigateToMed(Medication med) {
    HapticFeedback.selectionClick();
    _addToRecentlyViewed(med);
    _setView(_ViewMode.details, also: () => _currentMedication = med);
  }

  void _toggleCompare(Medication med) {
    HapticFeedback.selectionClick();
    setState(() {
      if (_compareList.any((m) => m.name == med.name)) {
        _compareList.removeWhere((m) => m.name == med.name);
      } else {
        if (_compareList.length < 2) {
          _compareList.add(med);
        } else {
          // Replace first if already 2
          _compareList.removeAt(0);
          _compareList.add(med);
        }
      }
    });
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // HOME VIEW — Category grid + Recently Viewed + Quick Actions
  // ═══════════════════════════════════════════════════════════════════════════

  Widget _buildHomeView(ResponsiveConfig cfg) {
    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      padding: EdgeInsets.fromLTRB(
          cfg.paddingH, cfg.paddingV, cfg.paddingH, cfg.paddingV + 80),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _buildHeroCard(),
          const SizedBox(height: 20),
          _buildSearchField(),
          const SizedBox(height: 20),
          _buildQuickActions(),
          if (_recentlyViewed.isNotEmpty) ...[
            const SizedBox(height: 22),
            _sectionHeader('Recently Viewed', icon: Icons.history_rounded),
            _buildRecentlyViewedStrip(),
          ],
          const SizedBox(height: 22),
          _sectionHeader('Browse by Category',
              icon: Icons.category_rounded,
              trailing: Text(
                '${_medicationDatabase.length} medications',
                style: TextStyle(
                  color: Colors.white.withOpacity(0.55),
                  fontSize: 11,
                  fontWeight: FontWeight.w500,
                ),
              )),
          _buildCategoryGrid(cfg),
          const SizedBox(height: 20),
          _buildAllMedsButton(),
        ],
      ),
    );
  }

  Widget _buildHeroCard() {
    return ClipRRect(
      borderRadius: BorderRadius.circular(24),
      child: RepaintBoundary(
        child: Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(24),
            gradient: LinearGradient(
              colors: [
                _Jovi.coral.withOpacity(0.25),
                _Jovi.coralDark.withOpacity(0.15),
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            border: Border.all(color: _Jovi.coral.withOpacity(0.35), width: 1),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      gradient: _Jovi.coralGradient,
                      borderRadius: BorderRadius.circular(14),
                      boxShadow: [
                        BoxShadow(
                          color: _Jovi.coral.withOpacity(0.35),
                          blurRadius: 14,
                          offset: const Offset(0, 4),
                        ),
                      ],
                    ),
                    child: const Icon(Icons.timer_outlined,
                        color: Colors.white, size: 22),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: const [
                        Text('Half-Life Reference',
                            style: TextStyle(
                                color: Colors.white,
                                fontSize: 17,
                                fontWeight: FontWeight.w700,
                                letterSpacing: -0.2)),
                        SizedBox(height: 2),
                        Text('Medication reference',
                            style: TextStyle(
                                color: Colors.white70,
                                fontSize: 12,
                                fontWeight: FontWeight.w500)),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              Text(
                'Search 250+ medications for half-life, onset, interactions, pregnancy category, and more. Track how long a drug stays in your system.',
                style: TextStyle(
                  color: Colors.white.withOpacity(0.88),
                  fontSize: 13,
                  height: 1.4,
                ),
              ),
              const SizedBox(height: 10),
              Text(
                'For reference only — not medical advice. Always follow your prescriber’s instructions.',
                style: TextStyle(
                  color: Colors.white.withOpacity(0.6),
                  fontSize: 11.5,
                  height: 1.35,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSearchField({bool autofocus = false}) {
    return _glassCard(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
      radius: 16,
      child: Row(
        children: [
          const SizedBox(width: 12),
          Icon(Icons.search_rounded,
              color: Colors.white.withOpacity(0.75), size: 22),
          const SizedBox(width: 10),
          Expanded(
            child: TextField(
              controller: _searchController,
              autofocus: autofocus,
              textInputAction: TextInputAction.search,
              autocorrect: false,
              onChanged: (v) {
                setState(() {
                  _searchQuery = v;
                });
              },
              onTap: () {
                if (_viewMode != _ViewMode.search) {
                  // The search view hosts its own focused copy of this
                  // field. r2 switched views here and unmounted the field
                  // mid-tap, so nothing could be typed.
                  _setView(_ViewMode.search);
                }
              },
              style: const TextStyle(color: Colors.white, fontSize: 14.5),
              cursorColor: _Jovi.coral,
              decoration: InputDecoration(
                hintText: _searchByCondition
                    ? 'Search by symptom or condition…'
                    : 'Medication name, brand, or class…',
                hintStyle: TextStyle(
                    color: Colors.white.withOpacity(0.5), fontSize: 14),
                border: InputBorder.none,
                contentPadding: const EdgeInsets.symmetric(vertical: 14),
              ),
            ),
          ),
          if (_searchQuery.isNotEmpty)
            IconButton(
              tooltip: 'Clear search',
              icon: Icon(Icons.close_rounded,
                  color: Colors.white.withOpacity(0.7), size: 20),
              onPressed: () {
                HapticFeedback.selectionClick();
                _searchController.clear();
                setState(() => _searchQuery = '');
              },
            ),
        ],
      ),
    );
  }

  Widget _buildQuickActions() {
    return Row(
      children: [
        Expanded(
            child: _buildQuickActionCard(
          icon: Icons.favorite_rounded,
          label: 'Favorites',
          badge: _favoriteNames.length,
          tint: _Jovi.coral,
          onTap: () => _setView(_ViewMode.favorites, also: () {
            _showFavoritesOnly = true;
            _currentCategory = null;
          }),
        )),
        const SizedBox(width: 10),
        Expanded(
            child: _buildQuickActionCard(
          icon: Icons.compare_arrows_rounded,
          label: 'Compare',
          badge: _compareList.length,
          tint: _Jovi.mint,
          onTap: () => _setView(_compareList.length == 2
              ? _ViewMode.compare
              : _ViewMode.categoryList),
        )),
        const SizedBox(width: 10),
        Expanded(
            child: _buildQuickActionCard(
          icon: Icons.tune_rounded,
          label: _searchByCondition ? 'By Name' : 'By Symptom',
          tint: _Jovi.gold,
          onTap: () =>
              setState(() => _searchByCondition = !_searchByCondition),
        )),
      ],
    );
  }

  Widget _buildQuickActionCard({
    required IconData icon,
    required String label,
    int badge = 0,
    required Color tint,
    required VoidCallback onTap,
  }) {
    return _Pressable(
      reduceMotion: _reduceMotion,
      pressedScale: 0.96,
      semanticsLabel: badge > 0 ? '$label, $badge' : label,
      onTap: () {
        HapticFeedback.selectionClick();
        onTap();
      },
      child: _glassCard(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 14),
        radius: 16,
        child: Column(
          children: [
            Stack(
              clipBehavior: Clip.none,
              children: [
                Icon(icon, color: tint, size: 24),
                if (badge > 0)
                  Positioned(
                    right: -8,
                    top: -6,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 5, vertical: 2),
                      decoration: BoxDecoration(
                        color: _Jovi.coral,
                        borderRadius: BorderRadius.circular(100),
                      ),
                      constraints:
                          const BoxConstraints(minWidth: 16, minHeight: 16),
                      child: Text(
                        '$badge',
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                            color: Colors.white,
                            fontSize: 10,
                            fontWeight: FontWeight.w700),
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              label,
              textAlign: TextAlign.center,
              style: const TextStyle(
                  color: Colors.white,
                  fontSize: 11.5,
                  fontWeight: FontWeight.w600),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRecentlyViewedStrip() {
    return SizedBox(
      height: 110,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        physics: const BouncingScrollPhysics(),
        padding: const EdgeInsets.symmetric(horizontal: 2),
        itemCount: _recentlyViewed.length,
        separatorBuilder: (_, __) => const SizedBox(width: 10),
        itemBuilder: (_, i) {
          final med = _recentlyViewed[i];
          return _Pressable(
            reduceMotion: _reduceMotion,
            pressedScale: 0.96,
            semanticsLabel: '${med.name}, half-life ${med.halfLife}',
            onTap: () => _navigateToMed(med),
            child: Container(
              width: 150,
              padding: const EdgeInsets.all(2),
              child: _glassCard(
                padding: const EdgeInsets.all(12),
                radius: 14,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          width: 32,
                          height: 32,
                          decoration: BoxDecoration(
                            gradient: _Jovi.coralGradient,
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Icon(med.category.icon,
                              color: Colors.white, size: 16),
                        ),
                        const Spacer(),
                        if (_favoriteNames.contains(med.name))
                          Icon(Icons.favorite, color: _Jovi.coral, size: 14),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Text(
                      med.name,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                          color: Colors.white,
                          fontSize: 13.5,
                          fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      med.halfLife,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                          color: _Jovi.coral,
                          fontSize: 11,
                          fontWeight: FontWeight.w600),
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildCategoryGrid(ResponsiveConfig cfg) {
    final columns = cfg.actionColumns.clamp(2, 4);
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      padding: EdgeInsets.zero,
      itemCount: MedicationCategory.values.length,
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: columns,
        mainAxisSpacing: 10,
        crossAxisSpacing: 10,
        childAspectRatio: 1,
      ),
      itemBuilder: (_, i) {
        final cat = MedicationCategory.values[i];
        final count = _categoryCount(cat);
        if (count == 0) return const SizedBox.shrink();
        return _Pressable(
          reduceMotion: _reduceMotion,
          pressedScale: 0.95,
          semanticsLabel: '${cat.displayName}, $count medications',
          onTap: () {
            HapticFeedback.selectionClick();
            _setView(_ViewMode.categoryList, also: () => _currentCategory = cat);
          },
          child: _glassCard(
            padding: const EdgeInsets.all(10),
            radius: 16,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  width: 42,
                  height: 42,
                  decoration: BoxDecoration(
                    gradient: _Jovi.coralGradient,
                    borderRadius: BorderRadius.circular(12),
                    boxShadow: [
                      BoxShadow(
                        color: _Jovi.coral.withOpacity(0.3),
                        blurRadius: 10,
                        offset: const Offset(0, 3),
                      ),
                    ],
                  ),
                  child: Icon(cat.icon, color: Colors.white, size: 20),
                ),
                const SizedBox(height: 8),
                Text(
                  cat.displayName,
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                      color: Colors.white,
                      fontSize: 10.5,
                      height: 1.15,
                      fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 4),
                Text(
                  '$count',
                  style: TextStyle(
                      color: _Jovi.coral,
                      fontSize: 11,
                      fontWeight: FontWeight.w700),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildAllMedsButton() {
    return _Pressable(
      reduceMotion: _reduceMotion,
      pressedScale: 0.98,
      semanticsLabel: 'Browse all medications A to Z',
      onTap: () {
        HapticFeedback.selectionClick();
        _setView(_ViewMode.categoryList, also: () => _currentCategory = null);
      },
      child: _glassCard(
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 16),
        radius: 14,
        child: Row(
          children: [
            Icon(Icons.list_alt_rounded, color: _Jovi.coral, size: 20),
            const SizedBox(width: 12),
            const Expanded(
              child: Text('Browse all medications A-Z',
                  style: TextStyle(
                      color: Colors.white,
                      fontSize: 14,
                      fontWeight: FontWeight.w600)),
            ),
            Icon(Icons.arrow_forward_ios_rounded,
                color: Colors.white.withOpacity(0.6), size: 14),
          ],
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // LIST VIEW — A-Z sidebar, swipeable cards, category filter
  // ═══════════════════════════════════════════════════════════════════════════

  Widget _buildListView(ResponsiveConfig cfg) {
    final grouped = _groupedByLetter;
    final letters = grouped.keys.toList()..sort();

    // In search mode the field lives here, focused, so typing continues
    // after the view switch.
    final isSearch = _viewMode == _ViewMode.search;
    final searchBar = isSearch
        ? Padding(
            padding: EdgeInsets.fromLTRB(cfg.paddingH, 8, cfg.paddingH, 4),
            child: _buildSearchField(autofocus: true),
          )
        : null;

    if (_filteredMeds.isEmpty) {
      return Column(children: [
        if (searchBar != null) searchBar,
        Expanded(child: _buildEmptyState()),
      ]);
    }

    return Column(children: [
      if (searchBar != null) searchBar,
      Expanded(
          child: Row(
      children: [
        Expanded(
          child: ListView.builder(
            controller: _listScrollController,
            keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
            physics: const BouncingScrollPhysics(),
            padding: EdgeInsets.fromLTRB(
                cfg.paddingH, 8, cfg.paddingH - 2, cfg.paddingV + 80),
            itemCount: letters.length,
            itemBuilder: (_, i) {
              final letter = letters[i];
              final meds = grouped[letter]!;
              return Column(
                key: _letterKeys.putIfAbsent(letter, () => GlobalKey()),
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(6, 14, 0, 8),
                    child: Row(
                      children: [
                        Container(
                          width: 28,
                          height: 28,
                          decoration: BoxDecoration(
                            gradient: _Jovi.coralGradient,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Center(
                            child: Text(
                              letter,
                              style: const TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.w700,
                                  fontSize: 13),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          '${meds.length} medication${meds.length == 1 ? "" : "s"}',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.5),
                            fontSize: 11,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                  ),
                  ...meds.map((m) => _buildMedCard(m)),
                ],
              );
            },
          ),
        ),
        _buildAlphabetIndex(letters),
      ],
    )),
    ]);
  }

  Widget _buildAlphabetIndex(List<String> activeLetters) {
    // Compact A-Z vertical strip on the right
    final allLetters = List.generate(26, (i) => String.fromCharCode(65 + i));
    return Container(
      width: 22,
      margin: const EdgeInsets.only(right: 4, top: 6, bottom: 80),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(12),
        child: RepaintBoundary(
          child: Container(
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.05),
              borderRadius: BorderRadius.circular(12),
              border:
                  Border.all(color: Colors.white.withOpacity(0.09), width: 1),
            ),
            padding: const EdgeInsets.symmetric(vertical: 4),
            // Drag along the strip as in Contacts; each new letter scrolls
            // the list and ticks.
            child: LayoutBuilder(builder: (context, box) {
              void pick(double dy) {
                final idx = (dy / box.maxHeight * 26).floor().clamp(0, 25);
                final l = allLetters[idx];
                if (activeLetters.contains(l)) _scrollToLetter(l);
              }

              void release() {
                if (_activeLetter != null) {
                  setState(() => _activeLetter = null);
                }
              }

              return GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTapDown: (d) => pick(d.localPosition.dy),
                onTapUp: (_) => release(),
                onTapCancel: release,
                onVerticalDragStart: (d) => pick(d.localPosition.dy),
                onVerticalDragUpdate: (d) => pick(d.localPosition.dy),
                onVerticalDragEnd: (_) => release(),
                child: Semantics(
                  label: 'Alphabet index',
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: allLetters.map((l) {
                      final isActive = activeLetters.contains(l);
                      final isCurrent = _activeLetter == l;
                      return Container(
                        width: 22,
                        height: 18,
                        alignment: Alignment.center,
                        child: Text(
                          l,
                          style: TextStyle(
                            color: isCurrent
                                ? Colors.white
                                : isActive
                                    ? _Jovi.coral
                                    : Colors.white.withOpacity(0.25),
                            fontSize: 9.5,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                ),
              );
            }),
          ),
        ),
      ),
    );
  }

  void _scrollToLetter(String letter) {
    if (_activeLetter == letter) return;
    HapticFeedback.selectionClick();
    final grouped = _groupedByLetter;
    final letters = grouped.keys.toList()..sort();
    final index = letters.indexOf(letter);
    if (index < 0) return;
    setState(() => _activeLetter = letter);

    // Two steps: jump near the section with an estimate so the lazy list
    // builds it, then snap exactly to it. r2 stopped at the estimate, which
    // drifted because cards vary in height.
    double estimate = 0;
    for (int i = 0; i < index; i++) {
      estimate += 60 + (grouped[letters[i]]?.length ?? 0) * 88;
    }
    if (_listScrollController.hasClients) {
      final max = _listScrollController.position.maxScrollExtent;
      _listScrollController.jumpTo(estimate.clamp(0.0, max).toDouble());
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final ctx = _letterKeys[letter]?.currentContext;
      if (ctx == null || !mounted) return;
      Scrollable.ensureVisible(
        ctx,
        alignment: 0.0,
        duration: _reduceMotion
            ? Duration.zero
            : const Duration(milliseconds: 220),
        curve: Curves.easeOutCubic,
      );
    });
  }

  Widget _buildMedCard(Medication med) {
    final isFav = _favoriteNames.contains(med.name);
    final isInCompare = _compareList.any((m) => m.name == med.name);

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Dismissible(
        key: ValueKey('dismiss_${med.name}'),
        direction: DismissDirection.startToEnd,
        confirmDismiss: (_) async {
          await _toggleFavorite(med);
          return false; // Don't actually dismiss
        },
        background: Container(
          margin: const EdgeInsets.only(right: 4),
          padding: const EdgeInsets.symmetric(horizontal: 20),
          decoration: BoxDecoration(
            gradient: _Jovi.coralGradient,
            borderRadius: BorderRadius.circular(14),
          ),
          alignment: Alignment.centerLeft,
          child: Row(
            children: [
              Icon(isFav ? Icons.heart_broken_rounded : Icons.favorite_rounded,
                  color: Colors.white, size: 22),
              const SizedBox(width: 8),
              Text(
                isFav ? 'Unfavorite' : 'Favorite',
                style: const TextStyle(
                    color: Colors.white,
                    fontSize: 13,
                    fontWeight: FontWeight.w700),
              ),
            ],
          ),
        ),
        child: _Pressable(
          reduceMotion: _reduceMotion,
          pressedScale: 0.98,
          semanticsLabel:
              '${med.name}${med.brandNames.isNotEmpty ? ', ${med.brandNames.join(', ')}' : ''}, half-life ${med.halfLife}${isFav ? ', favorite' : ''}${isInCompare ? ', in compare' : ''}',
          semanticsHint: 'Opens details. Long press to add to compare',
          onTap: () => _navigateToMed(med),
          onLongPress: () => _toggleCompare(med),
          child: _glassCard(
            padding: const EdgeInsets.all(14),
            radius: 14,
            tintColor: isInCompare ? _Jovi.mint : null,
            tintOpacity: isInCompare ? 0.08 : 0.10,
            child: Row(
              children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    gradient: _Jovi.coralGradient,
                    borderRadius: BorderRadius.circular(12),
                    boxShadow: [
                      BoxShadow(
                        color: _Jovi.coral.withOpacity(0.3),
                        blurRadius: 10,
                        offset: const Offset(0, 3),
                      ),
                    ],
                  ),
                  child: Center(
                    child: Text(
                      med.name.substring(0, 1).toUpperCase(),
                      style: const TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.w700),
                    ),
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              med.name,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 15,
                                  fontWeight: FontWeight.w700),
                            ),
                          ),
                          if (med.schedule != ControlledSchedule.none)
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: _Jovi.gold.withOpacity(0.18),
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(
                                    color: _Jovi.gold.withOpacity(0.4),
                                    width: 1),
                              ),
                              child: Text(
                                'C-${med.schedule.label}',
                                style: TextStyle(
                                    color: _Jovi.gold,
                                    fontSize: 9,
                                    fontWeight: FontWeight.w700),
                              ),
                            ),
                        ],
                      ),
                      if (med.brandNames.isNotEmpty)
                        Text(
                          med.brandNames.join(', '),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                              color: Colors.white.withOpacity(0.55),
                              fontSize: 11.5),
                        ),
                      const SizedBox(height: 4),
                      Row(
                        children: [
                          Icon(Icons.timer_outlined,
                              size: 11, color: _Jovi.coral.withOpacity(0.9)),
                          const SizedBox(width: 4),
                          Expanded(
                            child: Text(
                              med.halfLife,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                  color: _Jovi.coral,
                                  fontSize: 11.5,
                                  fontWeight: FontWeight.w600),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                if (isFav)
                  Icon(Icons.favorite, color: _Jovi.coral, size: 18)
                else if (isInCompare)
                  Icon(Icons.compare_arrows_rounded,
                      color: _Jovi.mint, size: 18)
                else
                  Icon(Icons.arrow_forward_ios_rounded,
                      color: Colors.white.withOpacity(0.4), size: 12),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.06),
                shape: BoxShape.circle,
                border:
                    Border.all(color: Colors.white.withOpacity(0.12), width: 1),
              ),
              child: Icon(Icons.search_off_rounded,
                  color: Colors.white.withOpacity(0.6), size: 30),
            ),
            const SizedBox(height: 16),
            const Text(
              'No medications found',
              style: TextStyle(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 6),
            Text(
              _searchQuery.isNotEmpty
                  ? 'Try a different search term'
                  : _showFavoritesOnly
                      ? 'Swipe right on a medication to favorite it'
                      : 'Nothing in this category yet',
              textAlign: TextAlign.center,
              style: TextStyle(
                  color: Colors.white.withOpacity(0.65), fontSize: 13),
            ),
          ],
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // DETAILS VIEW — Full medication info with elimination visualizer
  // ═══════════════════════════════════════════════════════════════════════════

  Widget _buildDetailsView(ResponsiveConfig cfg) {
    final med = _currentMedication;
    if (med == null) return const SizedBox.shrink();
    final isFav = _favoriteNames.contains(med.name);

    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      padding:
          EdgeInsets.fromLTRB(cfg.paddingH, 8, cfg.paddingH, cfg.paddingV + 80),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header card
          _glassCard(
            padding: const EdgeInsets.all(18),
            radius: 20,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      width: 56,
                      height: 56,
                      decoration: BoxDecoration(
                        gradient: _Jovi.coralGradient,
                        borderRadius: BorderRadius.circular(16),
                        boxShadow: [
                          BoxShadow(
                            color: _Jovi.coral.withOpacity(0.35),
                            blurRadius: 14,
                            offset: const Offset(0, 4),
                          ),
                        ],
                      ),
                      child: Center(
                        child: Text(
                          med.name.substring(0, 1).toUpperCase(),
                          style: const TextStyle(
                              color: Colors.white,
                              fontSize: 26,
                              fontWeight: FontWeight.w700),
                        ),
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
                                fontWeight: FontWeight.w700,
                                letterSpacing: -0.3),
                          ),
                          if (med.pronunciation != 'Not specified')
                            Text(
                              '[${med.pronunciation}]',
                              style: TextStyle(
                                color: _Jovi.coralLight,
                                fontSize: 12,
                                fontStyle: FontStyle.italic,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                        ],
                      ),
                    ),
                  ],
                ),
                if (med.brandNames.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: med.brandNames
                        .map((b) => _glassPill(
                              tint: _Jovi.coral,
                              child: Text(
                                b,
                                style: TextStyle(
                                    color: Colors.white.withOpacity(0.95),
                                    fontSize: 11,
                                    fontWeight: FontWeight.w600),
                              ),
                            ))
                        .toList(),
                  ),
                ],
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: _glassPill(
                        tint: _Jovi.mint,
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 7),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(med.category.icon,
                                color: _Jovi.mint, size: 13),
                            const SizedBox(width: 6),
                            Flexible(
                              child: Text(
                                med.category.displayName,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                    color: Colors.white,
                                    fontSize: 11,
                                    fontWeight: FontWeight.w600),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  med.drugClass,
                  style: TextStyle(
                      color: Colors.white.withOpacity(0.75),
                      fontSize: 12.5,
                      fontWeight: FontWeight.w500),
                ),
              ],
            ),
          ),

          const SizedBox(height: 12),
          // Half-life visualizer
          _buildHalfLifeVisualizer(med),

          const SizedBox(height: 12),
          // Action buttons
          Row(
            children: [
              Expanded(
                child: _buildActionButton(
                  icon: isFav ? Icons.favorite : Icons.favorite_border,
                  label: isFav ? 'Favorited' : 'Favorite',
                  tint: _Jovi.coral,
                  active: isFav,
                  onTap: () => _toggleFavorite(med),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _buildActionButton(
                  icon: Icons.compare_arrows_rounded,
                  label: _compareList.any((m) => m.name == med.name)
                      ? 'In Compare'
                      : 'Compare',
                  tint: _Jovi.mint,
                  active: _compareList.any((m) => m.name == med.name),
                  onTap: () => _toggleCompare(med),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _buildActionButton(
                  icon: Icons.share_outlined,
                  label: 'Share',
                  tint: _Jovi.gold,
                  onTap: () => _showShareDialog(med),
                ),
              ),
            ],
          ),

          const SizedBox(height: 16),

          // Description
          _infoBlock('About', med.description,
              icon: Icons.info_outline_rounded),

          const SizedBox(height: 10),
          // Common uses
          _infoBlock('Common Uses', med.commonUses,
              icon: Icons.task_alt_rounded),

          const SizedBox(height: 10),
          // Dosage
          _infoBlock('Dosage Range', med.dosageRange,
              icon: Icons.medication_liquid_rounded, tint: _Jovi.coral),

          const SizedBox(height: 10),
          // Onset / peak (2 columns)
          Row(
            children: [
              Expanded(
                child: _miniStatCard(
                  label: 'Onset',
                  value: med.onsetOfAction,
                  icon: Icons.play_arrow_rounded,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _miniStatCard(
                  label: 'Peak Time',
                  value: med.peakTime,
                  icon: Icons.trending_up_rounded,
                ),
              ),
            ],
          ),

          const SizedBox(height: 10),
          // Routes
          _buildRoutesSection(med),

          const SizedBox(height: 10),
          // Side effects
          _infoBlock('Side Effects', med.sideEffects,
              icon: Icons.warning_amber_rounded, tint: _Jovi.gold),

          if (med.interactions.isNotEmpty) ...[
            const SizedBox(height: 10),
            _buildInteractionsSection(med),
          ],

          const SizedBox(height: 10),
          // Pregnancy + Schedule
          Row(
            children: [
              Expanded(child: _buildPregnancyCard(med)),
              const SizedBox(width: 10),
              Expanded(child: _buildScheduleCard(med)),
            ],
          ),

          if (med.blackBoxWarning != null) ...[
            const SizedBox(height: 10),
            _buildBlackBoxWarning(med.blackBoxWarning!),
          ],

          if (med.conditions.isNotEmpty) ...[
            const SizedBox(height: 10),
            _buildConditionsChips(med),
          ],
          const SizedBox(height: 18),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8),
            child: Text(
              'For reference only — not medical advice. Dosages shown are typical published ranges; always follow your prescriber’s instructions.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white.withOpacity(0.5),
                fontSize: 11.5,
                height: 1.4,
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ─── Half-life Elimination Visualizer ──────────────────────────────────────

  Widget _buildHalfLifeVisualizer(Medication med) {
    final h = med.halfLifeHours;
    return _glassCard(
      padding: const EdgeInsets.all(16),
      radius: 18,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _coralGradientIcon(Icons.timer_rounded, size: 16),
              const SizedBox(width: 8),
              Text(
                'ELIMINATION TIMELINE',
                style: TextStyle(
                    color: Colors.white.withOpacity(0.85),
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.1),
              ),
              const Spacer(),
              Text(
                med.halfLife,
                style: TextStyle(
                    color: _Jovi.coral,
                    fontSize: 13,
                    fontWeight: FontWeight.w700),
              ),
            ],
          ),
          const SizedBox(height: 14),
          // The curve
          SizedBox(
            height: 120,
            // The curve draws on left to right when a medication opens.
            child: TweenAnimationBuilder<double>(
              key: ValueKey('curve_${med.name}'),
              tween:
                  Tween<double>(begin: _reduceMotion ? 1.0 : 0.0, end: 1.0),
              duration: _reduceMotion
                  ? Duration.zero
                  : const Duration(milliseconds: 700),
              curve: Curves.easeOutCubic,
              builder: (context, progress, _) => CustomPaint(
                size: Size.infinite,
                painter: _HalfLifeCurvePainter(
                  coralLight: _Jovi.coralLight,
                  coralDark: _Jovi.coralDark,
                  axis: Colors.white.withOpacity(0.35),
                  axisBg: Colors.white.withOpacity(0.08),
                  progress: progress,
                ),
              ),
            ),
          ),
          const SizedBox(height: 8),
          // Legend: 1×, 2×, 3×, 4×, 5× half lives with percentages
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _legendPoint('1×', '50%'),
              _legendPoint('2×', '75%'),
              _legendPoint('3×', '87.5%'),
              _legendPoint('4×', '93.8%'),
              _legendPoint('5×', '~97%', highlight: true),
            ],
          ),
          const SizedBox(height: 14),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  _Jovi.coral.withOpacity(0.15),
                  _Jovi.coral.withOpacity(0.05),
                ],
                begin: Alignment.centerLeft,
                end: Alignment.centerRight,
              ),
              borderRadius: BorderRadius.circular(12),
              border:
                  Border.all(color: _Jovi.coral.withOpacity(0.25), width: 1),
            ),
            child: Row(
              children: [
                Icon(Icons.insights_rounded, color: _Jovi.coral, size: 18),
                const SizedBox(width: 10),
                Expanded(
                  // Text.rich follows Dynamic Type; RichText does not.
                  child: Text.rich(
                    TextSpan(
                      style: const TextStyle(
                          color: Colors.white, fontSize: 12.5, height: 1.4),
                      children: [
                        const TextSpan(text: 'About 97% eliminated in '),
                        TextSpan(
                          text: _clearanceTimeDescription(med),
                          style: TextStyle(
                              color: _Jovi.coral, fontWeight: FontWeight.w700),
                        ),
                        if (h > 0) ...[
                          const TextSpan(text: ' · 50% in '),
                          TextSpan(
                            text: _formatHours(h),
                            style: TextStyle(
                                color: Colors.white.withOpacity(0.9),
                                fontWeight: FontWeight.w600),
                          ),
                        ],
                      ],
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

  String _formatHours(double h) {
    if (h <= 0) return '—';
    if (h < 1) return '${(h * 60).round()} min';
    if (h < 24) {
      return h == h.roundToDouble()
          ? '${h.toInt()} hr'
          : '${h.toStringAsFixed(1)} hr';
    }
    final days = h / 24;
    return days == days.roundToDouble()
        ? '${days.toInt()} days'
        : '${days.toStringAsFixed(1)} days';
  }

  Widget _legendPoint(String label, String value, {bool highlight = false}) {
    return Column(
      children: [
        Text(label,
            style: TextStyle(
                color: Colors.white.withOpacity(0.6),
                fontSize: 9,
                fontWeight: FontWeight.w600)),
        const SizedBox(height: 2),
        Text(value,
            style: TextStyle(
                color: highlight ? _Jovi.coral : Colors.white,
                fontSize: 11,
                fontWeight: FontWeight.w700)),
      ],
    );
  }

  Widget _buildActionButton({
    required IconData icon,
    required String label,
    required Color tint,
    bool active = false,
    required VoidCallback onTap,
  }) {
    return _Pressable(
      reduceMotion: _reduceMotion,
      pressedScale: 0.95,
      semanticsLabel: label,
      onTap: onTap,
      child: _glassCard(
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
        radius: 14,
        tintColor: active ? tint : null,
        tintOpacity: active ? 0.18 : 0.10,
        child: Column(
          children: [
            Icon(icon, color: active ? tint : Colors.white, size: 20),
            const SizedBox(height: 4),
            Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                  color: active ? tint : Colors.white,
                  fontSize: 11,
                  fontWeight: FontWeight.w600),
            ),
          ],
        ),
      ),
    );
  }

  Widget _infoBlock(String title, String body, {IconData? icon, Color? tint}) {
    return _glassCard(
      padding: const EdgeInsets.all(14),
      radius: 14,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              if (icon != null) ...[
                Icon(icon,
                    color: tint ?? Colors.white.withOpacity(0.75), size: 15),
                const SizedBox(width: 7),
              ],
              Text(
                title.toUpperCase(),
                style: TextStyle(
                    color: tint ?? Colors.white.withOpacity(0.8),
                    fontSize: 10.5,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.1),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            body,
            style: const TextStyle(
                color: Colors.white, fontSize: 13.5, height: 1.45),
          ),
        ],
      ),
    );
  }

  Widget _miniStatCard({
    required String label,
    required String value,
    required IconData icon,
  }) {
    return _glassCard(
      padding: const EdgeInsets.all(12),
      radius: 12,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: _Jovi.coralLight, size: 13),
              const SizedBox(width: 6),
              Text(
                label.toUpperCase(),
                style: TextStyle(
                    color: Colors.white.withOpacity(0.6),
                    fontSize: 9.5,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            value,
            style: const TextStyle(
                color: Colors.white, fontSize: 12.5, height: 1.3),
          ),
        ],
      ),
    );
  }

  Widget _buildRoutesSection(Medication med) {
    return _glassCard(
      padding: const EdgeInsets.all(14),
      radius: 14,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.route_outlined,
                  color: Colors.white.withOpacity(0.75), size: 15),
              const SizedBox(width: 7),
              Text(
                'ROUTES OF ADMINISTRATION',
                style: TextStyle(
                    color: Colors.white.withOpacity(0.8),
                    fontSize: 10.5,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.1),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: med.routes
                .map((r) => _glassPill(
                      tint: _Jovi.coral,
                      child: Text(
                        r,
                        style: const TextStyle(
                            color: Colors.white,
                            fontSize: 11,
                            fontWeight: FontWeight.w600),
                      ),
                    ))
                .toList(),
          ),
        ],
      ),
    );
  }

  Widget _buildInteractionsSection(Medication med) {
    return _glassCard(
      padding: const EdgeInsets.all(14),
      radius: 14,
      tintColor: _Jovi.gold,
      tintOpacity: 0.05,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.warning_amber_rounded, color: _Jovi.gold, size: 15),
              const SizedBox(width: 7),
              Text(
                'KEY INTERACTIONS',
                style: TextStyle(
                    color: _Jovi.gold,
                    fontSize: 10.5,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.1),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ...med.interactions.map((i) => Padding(
                padding: const EdgeInsets.only(top: 4, bottom: 4),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: Container(
                        width: 4,
                        height: 4,
                        decoration: BoxDecoration(
                          color: _Jovi.gold,
                          shape: BoxShape.circle,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        i,
                        style: const TextStyle(
                            color: Colors.white, fontSize: 13, height: 1.4),
                      ),
                    ),
                  ],
                ),
              )),
        ],
      ),
    );
  }

  Widget _buildPregnancyCard(Medication med) {
    final cat = med.pregnancyCategory;
    final isDanger = cat == PregnancyCategory.d || cat == PregnancyCategory.x;
    final tint = isDanger ? _Jovi.errorRed : _Jovi.mint;
    return _glassCard(
      padding: const EdgeInsets.all(12),
      radius: 12,
      tintColor: tint,
      tintOpacity: 0.08,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.pregnant_woman_rounded, color: tint, size: 14),
              const SizedBox(width: 6),
              Text('PREGNANCY',
                  style: TextStyle(
                      color: Colors.white.withOpacity(0.75),
                      fontSize: 9.5,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1)),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Category ${cat.label}',
            style: TextStyle(
                color: tint, fontSize: 15, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 4),
          Text(
            cat.description,
            maxLines: 3,
            style: TextStyle(
                color: Colors.white.withOpacity(0.85),
                fontSize: 10.5,
                height: 1.3),
          ),
        ],
      ),
    );
  }

  Widget _buildScheduleCard(Medication med) {
    final sch = med.schedule;
    final isControlled = sch != ControlledSchedule.none;
    if (!isControlled) {
      return _glassCard(
        padding: const EdgeInsets.all(12),
        radius: 12,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.check_circle_outline_rounded,
                    color: _Jovi.mint, size: 14),
                const SizedBox(width: 6),
                Text('DEA',
                    style: TextStyle(
                        color: Colors.white.withOpacity(0.75),
                        fontSize: 9.5,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 1)),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Not scheduled',
              style: TextStyle(
                  color: _Jovi.mint, fontSize: 15, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 4),
            Text('Not a controlled substance',
                style: TextStyle(
                    color: Colors.white.withOpacity(0.85),
                    fontSize: 10.5,
                    height: 1.3)),
          ],
        ),
      );
    }
    final isStrict =
        sch == ControlledSchedule.i || sch == ControlledSchedule.ii;
    final tint = isStrict ? _Jovi.errorRed : _Jovi.gold;
    return _glassCard(
      padding: const EdgeInsets.all(12),
      radius: 12,
      tintColor: tint,
      tintOpacity: 0.08,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.gavel_rounded, color: tint, size: 14),
              const SizedBox(width: 6),
              Text('DEA SCHEDULE',
                  style: TextStyle(
                      color: Colors.white.withOpacity(0.75),
                      fontSize: 9.5,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1)),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Schedule ${sch.label}',
            style: TextStyle(
                color: tint, fontSize: 15, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 4),
          Text(
            sch.description,
            maxLines: 3,
            style: TextStyle(
                color: Colors.white.withOpacity(0.85),
                fontSize: 10.5,
                height: 1.3),
          ),
        ],
      ),
    );
  }

  Widget _buildBlackBoxWarning(String warning) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(14),
      child: RepaintBoundary(
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: _Jovi.errorRed.withOpacity(0.12),
            borderRadius: BorderRadius.circular(14),
            border:
                Border.all(color: _Jovi.errorRed.withOpacity(0.45), width: 1.2),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(6),
                    decoration: BoxDecoration(
                      color: _Jovi.errorRed.withOpacity(0.25),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Icon(Icons.warning_rounded,
                        color: _Jovi.errorRed, size: 16),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'BLACK BOX WARNING',
                    style: TextStyle(
                        color: _Jovi.errorRed,
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 1.1),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Text(
                warning,
                style:
                    TextStyle(color: _Jovi.softRed, fontSize: 13, height: 1.45),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildConditionsChips(Medication med) {
    return _glassCard(
      padding: const EdgeInsets.all(14),
      radius: 14,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.local_hospital_outlined, color: _Jovi.mint, size: 15),
              const SizedBox(width: 7),
              Text('TREATS',
                  style: TextStyle(
                      color: Colors.white.withOpacity(0.8),
                      fontSize: 10.5,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1.1)),
            ],
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: med.conditions
                .map((c) => _glassPill(
                      tint: _Jovi.mint,
                      child: Text(
                        c,
                        style: const TextStyle(
                            color: Colors.white,
                            fontSize: 11,
                            fontWeight: FontWeight.w600),
                      ),
                    ))
                .toList(),
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // COMPARE VIEW — Two medications side-by-side
  // ═══════════════════════════════════════════════════════════════════════════

  Widget _buildCompareView(ResponsiveConfig cfg) {
    if (_compareList.length < 2) {
      return Padding(
        padding: const EdgeInsets.all(32),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 72,
                height: 72,
                decoration: BoxDecoration(
                  gradient: _Jovi.coralGradient,
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                        color: _Jovi.coral.withOpacity(0.3),
                        blurRadius: 16,
                        offset: const Offset(0, 4)),
                  ],
                ),
                child: const Icon(Icons.compare_arrows_rounded,
                    color: Colors.white, size: 32),
              ),
              const SizedBox(height: 18),
              const Text(
                'Select 2 medications to compare',
                style: TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 8),
              Text(
                'Long-press any medication card to add it to compare.\nYou have ${_compareList.length} / 2 selected.',
                textAlign: TextAlign.center,
                style: TextStyle(
                    color: Colors.white.withOpacity(0.7),
                    fontSize: 13,
                    height: 1.4),
              ),
              const SizedBox(height: 18),
              _Pressable(
                reduceMotion: _reduceMotion,
                pressedScale: 0.96,
                semanticsLabel: 'Browse medications',
                onTap: () => _setView(_ViewMode.categoryList),
                child: _glassCard(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
                  radius: 100,
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.list_alt_rounded,
                          color: _Jovi.coral, size: 16),
                      const SizedBox(width: 8),
                      const Text(
                        'Browse medications',
                        style: TextStyle(
                            color: Colors.white,
                            fontSize: 13,
                            fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      );
    }

    final a = _compareList[0];
    final b = _compareList[1];

    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      padding:
          EdgeInsets.fromLTRB(cfg.paddingH, 8, cfg.paddingH, cfg.paddingV + 80),
      child: Column(
        children: [
          // Header with two med names
          Row(
            children: [
              Expanded(child: _buildCompareHeader(a, left: true)),
              const SizedBox(width: 10),
              Expanded(child: _buildCompareHeader(b, left: false)),
            ],
          ),
          const SizedBox(height: 16),
          _buildCompareRow('Half-life', a.halfLife, b.halfLife,
              highlight: a.halfLife != b.halfLife),
          _buildCompareRow('Drug Class', a.drugClass, b.drugClass,
              highlight: a.drugClass != b.drugClass),
          _buildCompareRow('Onset', a.onsetOfAction, b.onsetOfAction,
              highlight: a.onsetOfAction != b.onsetOfAction),
          _buildCompareRow('Peak Time', a.peakTime, b.peakTime,
              highlight: a.peakTime != b.peakTime),
          _buildCompareRow('Dosage', a.dosageRange, b.dosageRange,
              highlight: true),
          _buildCompareRow('Pregnancy', 'Cat ${a.pregnancyCategory.label}',
              'Cat ${b.pregnancyCategory.label}',
              highlight: a.pregnancyCategory != b.pregnancyCategory),
          _buildCompareRow(
              'DEA Schedule',
              a.schedule == ControlledSchedule.none
                  ? 'None'
                  : 'C-${a.schedule.label}',
              b.schedule == ControlledSchedule.none
                  ? 'None'
                  : 'C-${b.schedule.label}',
              highlight: a.schedule != b.schedule),
          _buildCompareRow('Routes', a.routes.join(', '), b.routes.join(', '),
              highlight: true),
          _buildCompareRow('Side Effects', a.sideEffects, b.sideEffects,
              highlight: true),
          _buildCompareRow(
              'Interactions',
              a.interactions.isEmpty ? '—' : a.interactions.join(', '),
              b.interactions.isEmpty ? '—' : b.interactions.join(', '),
              highlight: true),
          if (a.blackBoxWarning != null || b.blackBoxWarning != null) ...[
            const SizedBox(height: 6),
            _buildCompareRow('Black Box', a.blackBoxWarning ?? 'None',
                b.blackBoxWarning ?? 'None',
                highlight: a.blackBoxWarning != b.blackBoxWarning),
          ],
          const SizedBox(height: 14),
          _Pressable(
            reduceMotion: _reduceMotion,
            pressedScale: 0.98,
            semanticsLabel: 'Clear comparison',
            onTap: () {
              HapticFeedback.lightImpact();
              setState(() => _compareList.clear());
            },
            child: _glassCard(
              padding: const EdgeInsets.symmetric(vertical: 12),
              radius: 12,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.refresh_rounded,
                      color: Colors.white.withOpacity(0.75), size: 16),
                  const SizedBox(width: 8),
                  Text(
                    'Clear comparison',
                    style: TextStyle(
                        color: Colors.white.withOpacity(0.8),
                        fontSize: 13,
                        fontWeight: FontWeight.w600),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCompareHeader(Medication med, {required bool left}) {
    return _Pressable(
      reduceMotion: _reduceMotion,
      pressedScale: 0.97,
      semanticsLabel: '${med.name}. Opens details',
      onTap: () => _navigateToMed(med),
      child: _glassCard(
        padding: const EdgeInsets.all(12),
        radius: 14,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                gradient: _Jovi.coralGradient,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Center(
                child: Text(
                  med.name.substring(0, 1).toUpperCase(),
                  style: const TextStyle(
                      color: Colors.white,
                      fontSize: 16,
                      fontWeight: FontWeight.w700),
                ),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              med.name,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                  color: Colors.white,
                  fontSize: 14,
                  fontWeight: FontWeight.w700),
            ),
            if (med.brandNames.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 2),
                child: Text(
                  med.brandNames.first,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                      color: Colors.white.withOpacity(0.55), fontSize: 10.5),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildCompareRow(String label, String a, String b,
      {bool highlight = false}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: _glassCard(
        padding: const EdgeInsets.all(10),
        radius: 10,
        tintColor: highlight ? _Jovi.coral : null,
        tintOpacity: highlight ? 0.04 : 0.08,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label.toUpperCase(),
              style: TextStyle(
                  color: _Jovi.coralLight,
                  fontSize: 9.5,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1),
            ),
            const SizedBox(height: 6),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Text(
                    a,
                    style: const TextStyle(
                        color: Colors.white, fontSize: 12, height: 1.35),
                  ),
                ),
                Container(
                  width: 1,
                  height: 24,
                  margin: const EdgeInsets.symmetric(horizontal: 8),
                  color: Colors.white.withOpacity(0.15),
                ),
                Expanded(
                  child: Text(
                    b,
                    style: const TextStyle(
                        color: Colors.white, fontSize: 12, height: 1.35),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // MAIN BUILD — Scaffold, app bar, bottom nav, view switching
  // ═══════════════════════════════════════════════════════════════════════════

  @override
  Widget build(BuildContext context) {
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light,
      child: LayoutBuilder(
        builder: (ctx, constraints) {
          final cfg = _config(constraints);
          return Container(
            width: widget.width ?? constraints.maxWidth,
            height: widget.height ?? constraints.maxHeight,
            decoration: BoxDecoration(gradient: _Jovi.navyGradient),
            child: Stack(
              children: [
                // Ambient coral haze top-left
                Positioned(
                  top: -80,
                  left: -80,
                  child: Container(
                    width: 260,
                    height: 260,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: RadialGradient(
                        colors: [
                          _Jovi.coral.withOpacity(0.14),
                          _Jovi.coral.withOpacity(0),
                        ],
                      ),
                    ),
                  ),
                ),
                // Ambient mint haze bottom-right
                Positioned(
                  bottom: -100,
                  right: -100,
                  child: Container(
                    width: 260,
                    height: 260,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: RadialGradient(
                        colors: [
                          _Jovi.mint.withOpacity(0.10),
                          _Jovi.mint.withOpacity(0),
                        ],
                      ),
                    ),
                  ),
                ),
                SafeArea(
                  child: Column(
                    children: [
                      _buildTopBar(),
                      Expanded(
                        child: FadeTransition(
                          opacity: _fadeAnimation,
                          child: SlideTransition(
                            position: _slideAnimation,
                            child: _buildCurrentView(cfg),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                // Bottom nav
                Positioned(
                  left: 0,
                  right: 0,
                  bottom: 0,
                  child: SafeArea(
                    top: false,
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(12, 0, 12, 10),
                      child: _buildBottomNav(),
                    ),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildCurrentView(ResponsiveConfig cfg) {
    switch (_viewMode) {
      case _ViewMode.home:
        return _buildHomeView(cfg);
      case _ViewMode.categoryList:
      case _ViewMode.favorites:
      case _ViewMode.search:
        return _buildListView(cfg);
      case _ViewMode.details:
        return _buildDetailsView(cfg);
      case _ViewMode.compare:
        return _buildCompareView(cfg);
    }
  }

  Widget _barChip(IconData icon, String label, VoidCallback onTap) {
    return _Pressable(
      reduceMotion: _reduceMotion,
      pressedScale: 0.92,
      semanticsLabel: label,
      onTap: () {
        HapticFeedback.lightImpact();
        onTap();
      },
      child: Container(
        width: 44,
        height: 44,
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.08),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: Colors.white.withOpacity(0.14)),
        ),
        child: Icon(icon, color: Colors.white, size: 20),
      ),
    );
  }

  Widget _buildTopBar() {
    String title = 'Half-Life';
    String? subtitle;
    switch (_viewMode) {
      case _ViewMode.home:
        title = 'Half-Life';
        subtitle = 'Medication reference';
        break;
      case _ViewMode.categoryList:
        if (_currentCategory != null) {
          title = _currentCategory!.displayName;
          subtitle = '${_filteredMeds.length} medications';
        } else {
          title = 'All Medications';
          subtitle = '${_filteredMeds.length} of ${_medicationDatabase.length}';
        }
        break;
      case _ViewMode.search:
        title = 'Search';
        subtitle = _searchQuery.isEmpty
            ? (_searchByCondition
                ? 'Type a symptom or condition'
                : 'Type a name, brand, or class')
            : '${_filteredMeds.length} ${_filteredMeds.length == 1 ? 'match' : 'matches'}';
        break;
      case _ViewMode.favorites:
        title = 'Favorites';
        subtitle = '${_favoriteNames.length} saved';
        break;
      case _ViewMode.details:
        title = _currentMedication?.name ?? '';
        subtitle = _currentMedication?.brandNames.isNotEmpty == true
            ? _currentMedication!.brandNames.join(', ')
            : null;
        break;
      case _ViewMode.compare:
        title = 'Compare';
        subtitle = '${_compareList.length} of 2 selected';
        break;
    }

    final showBack = _viewMode != _ViewMode.home;

    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
      child: Row(
        children: [
          if (showBack) ...[
            _barChip(Icons.arrow_back_ios_new_rounded, 'Back', () {
              if (_viewMode == _ViewMode.details) {
                _setView(_ViewMode.categoryList);
              } else {
                _setView(_ViewMode.home, also: () {
                  _currentCategory = null;
                  _showFavoritesOnly = false;
                  _searchController.clear();
                  _searchQuery = '';
                });
              }
            }),
            const SizedBox(width: 12),
          ],
          Expanded(
            child: Semantics(
              header: true,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                        color: Colors.white,
                        fontSize: 17,
                        fontWeight: FontWeight.w600,
                        letterSpacing: -0.4,
                        height: 1.15),
                  ),
                  if (subtitle != null)
                    Text(
                      subtitle,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                          color: Colors.white.withOpacity(0.65),
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                          height: 1.15),
                    ),
                ],
              ),
            ),
          ),
          if (_viewMode == _ViewMode.details && _currentMedication != null)
            _barChip(Icons.ios_share_rounded, 'Copy to share',
                () => _showShareDialog(_currentMedication!)),
        ],
      ),
    );
  }

  Widget _buildBottomNav() {
    return ClipRRect(
      borderRadius: BorderRadius.circular(20),
      child: BackdropFilter(
        filter: ui.ImageFilter.blur(sigmaX: 20, sigmaY: 20),
        child: Container(
          decoration: BoxDecoration(
            color: _Jovi.navyMid.withOpacity(0.85),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: Colors.white.withOpacity(0.12), width: 1),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.3),
                blurRadius: 24,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 6),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _buildNavItem(
                icon: Icons.home_rounded,
                label: 'Home',
                active: _viewMode == _ViewMode.home,
                onTap: () => _setView(_ViewMode.home, also: () {
                  _currentCategory = null;
                  _showFavoritesOnly = false;
                  _searchController.clear();
                  _searchQuery = '';
                }),
              ),
              _buildNavItem(
                icon: Icons.search_rounded,
                label: 'Search',
                active: _viewMode == _ViewMode.search,
                onTap: () => _setView(_ViewMode.search, also: () {
                  _currentCategory = null;
                  _showFavoritesOnly = false;
                }),
              ),
              _buildNavItem(
                icon: Icons.favorite_rounded,
                label: 'Favorites',
                badge: _favoriteNames.length,
                active: _viewMode == _ViewMode.favorites,
                onTap: () => _setView(_ViewMode.favorites, also: () {
                  _showFavoritesOnly = true;
                  _currentCategory = null;
                }),
              ),
              _buildNavItem(
                icon: Icons.compare_arrows_rounded,
                label: 'Compare',
                badge: _compareList.length,
                active: _viewMode == _ViewMode.compare,
                onTap: () => _setView(_ViewMode.compare),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildNavItem({
    required IconData icon,
    required String label,
    int badge = 0,
    required bool active,
    required VoidCallback onTap,
  }) {
    return _Pressable(
      reduceMotion: _reduceMotion,
      pressedScale: 0.9,
      semanticsLabel:
          '$label${badge > 0 ? ', $badge' : ''}${active ? ', selected' : ''}',
      onTap: () {
        if (active) return;
        HapticFeedback.selectionClick();
        onTap();
      },
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Stack(
              clipBehavior: Clip.none,
              children: [
                Icon(icon,
                    color:
                        active ? _Jovi.coral : Colors.white.withOpacity(0.55),
                    size: 22),
                if (badge > 0)
                  Positioned(
                    right: -6,
                    top: -4,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 4, vertical: 1),
                      decoration: BoxDecoration(
                        color: _Jovi.coral,
                        borderRadius: BorderRadius.circular(100),
                      ),
                      constraints: const BoxConstraints(minWidth: 14),
                      child: Text(
                        '$badge',
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                            color: Colors.white,
                            fontSize: 9,
                            fontWeight: FontWeight.w700),
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: TextStyle(
                color: active ? _Jovi.coral : Colors.white.withOpacity(0.55),
                fontSize: 10,
                fontWeight: active ? FontWeight.w700 : FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
// ═══════════════════════════════════════════════════════════════════════════
// Half-life elimination curve painter
// Renders exponential decay curve: C(t) = C0 * 0.5^(t/halflife)
// Shows 5 half-life markers (50%, 75%, 87.5%, 93.75%, ~97%)
// ═══════════════════════════════════════════════════════════════════════════

class _HalfLifeCurvePainter extends CustomPainter {
  final Color coralLight;
  final Color coralDark;
  final Color axis;
  final Color axisBg;

  /// 0..1: how much of the curve (left to right) is drawn.
  final double progress;

  _HalfLifeCurvePainter({
    required this.coralLight,
    required this.coralDark,
    required this.axis,
    required this.axisBg,
    this.progress = 1.0,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paddingL = 20.0;
    final paddingR = 8.0;
    final paddingT = 8.0;
    final paddingB = 24.0;
    final w = size.width - paddingL - paddingR;
    final h = size.height - paddingT - paddingB;

    // Axes background
    final bgPaint = Paint()..color = axisBg;
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromLTWH(paddingL, paddingT, w, h),
        const Radius.circular(6),
      ),
      bgPaint,
    );

    // Horizontal gridlines at 25/50/75% of y
    final gridPaint = Paint()
      ..color = axis.withOpacity(0.25)
      ..strokeWidth = 0.5;
    for (int i = 1; i <= 3; i++) {
      final y = paddingT + h * (i / 4);
      canvas.drawLine(
        Offset(paddingL, y),
        Offset(paddingL + w, y),
        gridPaint,
      );
    }

    // Y-axis labels (100%, 50%, 0%)
    _drawText(canvas, '100%', Offset(0, paddingT - 4), axis, 9);
    _drawText(canvas, '50%', Offset(2, paddingT + h / 2 - 6), axis, 9);
    _drawText(canvas, '0%', Offset(6, paddingT + h - 8), axis, 9);

    // Build curve path — 5 half-lives on x-axis
    final totalHalfLives = 5.0;
    final curvePath = Path();
    final fillPath = Path();

    final steps = (100 * progress.clamp(0.0, 1.0)).round();
    double lastX = paddingL;
    for (int i = 0; i <= steps; i++) {
      final t = (i / 100.0) * totalHalfLives;
      final frac = math.pow(0.5, t).toDouble(); // 1.0 down to 0.03
      final x = paddingL + w * (t / totalHalfLives);
      final y = paddingT + h * (1 - frac);
      lastX = x;
      if (i == 0) {
        curvePath.moveTo(x, y);
        fillPath.moveTo(x, paddingT + h);
        fillPath.lineTo(x, y);
      } else {
        curvePath.lineTo(x, y);
        fillPath.lineTo(x, y);
      }
    }
    fillPath.lineTo(lastX, paddingT + h);
    fillPath.close();

    // Fill under curve
    final fillPaint = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [coralLight.withOpacity(0.45), coralLight.withOpacity(0.02)],
      ).createShader(Rect.fromLTWH(paddingL, paddingT, w, h));
    canvas.drawPath(fillPath, fillPaint);

    // Curve line
    final curvePaint = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [coralLight, coralDark],
      ).createShader(Rect.fromLTWH(paddingL, paddingT, w, h))
      ..strokeWidth = 2.5
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    canvas.drawPath(curvePath, curvePaint);

    // Vertical dotted lines at each half-life and dot markers
    final dotPaint = Paint()
      ..color = coralLight
      ..style = PaintingStyle.fill;
    final vLinePaint = Paint()
      ..color = coralLight.withOpacity(0.35)
      ..strokeWidth = 1;
    final remainFractions = [0.5, 0.25, 0.125, 0.0625, 0.03125];
    for (int i = 1; i <= 5; i++) {
      if (i / totalHalfLives > progress + 0.001) break;
      final x = paddingL + w * (i / totalHalfLives);
      final frac = remainFractions[i - 1];
      final y = paddingT + h * (1 - frac);
      // Dashed vertical guide
      _drawDashed(canvas, Offset(x, paddingT + h), Offset(x, y), vLinePaint);
      // Dot marker
      canvas.drawCircle(Offset(x, y), 3.5, dotPaint);
      // X-axis label
      _drawText(canvas, '${i}×', Offset(x - 6, paddingT + h + 6), axis, 9);
    }
  }

  void _drawDashed(Canvas canvas, Offset a, Offset b, Paint p) {
    const dashLen = 3.0;
    const gapLen = 3.0;
    final dx = b.dx - a.dx;
    final dy = b.dy - a.dy;
    final dist = math.sqrt(dx * dx + dy * dy);
    final steps = (dist / (dashLen + gapLen)).floor();
    final ux = dx / dist;
    final uy = dy / dist;
    for (int i = 0; i < steps; i++) {
      final startX = a.dx + ux * i * (dashLen + gapLen);
      final startY = a.dy + uy * i * (dashLen + gapLen);
      final endX = startX + ux * dashLen;
      final endY = startY + uy * dashLen;
      canvas.drawLine(Offset(startX, startY), Offset(endX, endY), p);
    }
  }

  void _drawText(
      Canvas canvas, String text, Offset position, Color color, double size) {
    final tp = TextPainter(
      text: TextSpan(
        text: text,
        style: TextStyle(
            color: color, fontSize: size, fontWeight: FontWeight.w600),
      ),
      textDirection: ui.TextDirection.ltr,
    );
    tp.layout();
    tp.paint(canvas, position);
  }

  @override
  bool shouldRepaint(covariant _HalfLifeCurvePainter old) =>
      old.coralLight != coralLight ||
      old.coralDark != coralDark ||
      old.axis != axis ||
      old.progress != progress;
}
