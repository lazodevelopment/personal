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

import 'package:flutter/foundation.dart' show kDebugMode;

// ============================================================
// JOVI HEALTH - HOME DASHBOARD V2
// Version: 2026.09.22-v2-r2 (Apple HIG refinement pass)
// Build: JC-HOME-V2-0922-002
//
// r2 changes vs r1:
// - Press feedback on pointer-down for every tappable surface (tiles,
//   chips, cards, FAB, avatar). Cancels with ~10 px of drag hysteresis so
//   a scroll never leaves a tile stuck in its pressed state.
// - Entrance motion: 420 ms critically-damped fade + 3% rise (was 1.2 s
//   fade + 20% slide). FAB no longer bounces in with elasticOut 1.8 s later.
// - Removed the FAB "breathing" loop (a slow 6 s oscillation is exactly the
//   vestibular trigger Apple's reduced-motion guidance warns about).
// - Reduce Motion honoured: entrances, progress, switcher, FAB collapse.
// - Dropped every in-scroll BackdropFilter (chips, action cards, progress
//   card, plan card, six quick-action tiles). They blurred a flat gradient
//   and cost a saveLayer per card per scroll frame. Modals keep their blur
//   because real content sits behind them.
// - Location permission is no longer requested on first launch. The
//   weather chip offers "Tap to enable" and the system prompt appears only
//   when the user asks for it. No more randomly generated "Denver" weather
//   when location/network is unavailable — the chip simply hides.
// - Entrance now plays on first frame, so a failed profile fetch can no
//   longer leave the whole page invisible (r1 only faded in after data).
// - Layout analysis assigns directly in didChangeDependencies instead of
//   scheduling a post-frame setState (one fewer wasted frame on rotate).
// - Greeting uses Text.rich so it respects Dynamic Type (RichText ignores
//   the text scaler by default).
// - Contrast fixes on navy: pace line, default status chips, renewal
//   banner, empty-activity icon, milestone insight accent.
// - Weight scale toned from w800/w900 to w700/w800 (SF Semibold/Bold).
// - Semantics labels for VoiceOver on chips, tiles, cards and the FAB.
// ============================================================

import 'dart:ui' as ui_dart;
import 'dart:convert';
import 'dart:typed_data';
import 'dart:async';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:intl/intl.dart';
import 'package:flutter/services.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as network_http;
import 'package:url_launcher/url_launcher.dart';

// ─── Jovi Brand Color System ────────────────────────────────
const Color joviCoral = Color(0xFFFF6B4A);
const Color joviCoralLight = Color(0xFFFF8F73);
const Color joviCoralDark = Color(0xFFE5583A);
const Color joviNavy = Color(0xFF1A2744);
const Color joviNavyDark = Color(0xFF0F1A2E);
const Color joviWarmWhite = Color(0xFFFFF8F5);
const Color joviMint = Color(0xFF00D4AA);
const Color joviMintDark = Color(0xFF00B894);
const Color joviGold = Color(0xFFFFD166);
const Color joviGoldDark = Color(0xFFE6B84D);
const Color joviSoftStone = Color(0xFFF0EFEB);
const Color joviErrorRed = Color(0xFFE53935);

/// Screen classification
enum ScreenType { compact, medium, expanded, large }

/// Responsive layout config
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

// ─── Action Needed Item Model ───────────────────────────────
enum ActionPriority { urgent, attention, gentle }

class ActionItem {
  final String id;
  final String title;
  final String subtitle;
  final IconData icon;
  final String route;
  final ActionPriority priority;
  final String? ctaLabel;

  ActionItem({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.route,
    required this.priority,
    this.ctaLabel,
  });

  Color get accentColor {
    switch (priority) {
      case ActionPriority.urgent:
        return joviCoral;
      case ActionPriority.attention:
        return joviGold;
      case ActionPriority.gentle:
        return joviMint;
    }
  }

  Color get accentDark {
    switch (priority) {
      case ActionPriority.urgent:
        return joviCoralDark;
      case ActionPriority.attention:
        return joviGoldDark;
      case ActionPriority.gentle:
        return joviMintDark;
    }
  }
}

// ─── For You Insight Model ──────────────────────────────────
enum InsightType { celebration, nudge, reminder, milestone }

class ForYouInsight {
  final String id;
  final String headline;
  final String body;
  final IconData icon;
  final InsightType type;
  final String? ctaLabel;
  final String? ctaRoute;

  ForYouInsight({
    required this.id,
    required this.headline,
    required this.body,
    required this.icon,
    required this.type,
    this.ctaLabel,
    this.ctaRoute,
  });

  Color get accent {
    switch (type) {
      case InsightType.celebration:
        return joviMint;
      case InsightType.nudge:
        return joviCoral;
      case InsightType.reminder:
        return joviGold;
      case InsightType.milestone:
        // Navy on a navy card was invisible; lavender reads as a milestone
        // without competing with coral/gold/mint.
        return const Color(0xFFA78BFA);
    }
  }
}

// ─── Monthly Spend Sample (for histogram) ──────────────────
class MonthlySpend {
  final int monthsAgo; // 0 = current month, 11 = 11 months ago
  final double amount;
  final String monthLabel; // 'Jan', 'Feb', etc.

  MonthlySpend({
    required this.monthsAgo,
    required this.amount,
    required this.monthLabel,
  });
}

// ─── Motion (Apple "response" values; critically damped, no overshoot) ──
class _Motion {
  static const Duration pressIn = Duration(milliseconds: 90);
  static const Duration pressOut = Duration(milliseconds: 260);
  static const Duration enter = Duration(milliseconds: 420);
  static const Duration progress = Duration(milliseconds: 900);
  static const Duration fab = Duration(milliseconds: 260);
  static const Curve settle = Curves.easeOutCubic;
}

/// Press feedback that lives on pointer-down, not on release. Scales the
/// child down the instant a finger lands, releases when it lifts, and
/// springs back early if the finger travels far enough (~10 px) that the
/// gesture is clearly a scroll rather than a tap.

// ─── Timezone (members are nationwide; reminders must use theirs) ────────
/// Best-effort IANA zone id for this device. Dart only exposes the zone
/// abbreviation and the UTC offset, which is enough to place a US member.
/// The Cloud Functions read `users/{uid}.timezone` (and `requests.timezone`)
/// for appointment reminders, billing reminders and booster sweeps.
String _localTimezoneId() {
  final now = DateTime.now();
  final name = now.timeZoneName.toUpperCase();
  const byName = <String, String>{
    'EST': 'America/New_York',
    'EDT': 'America/New_York',
    'CST': 'America/Chicago',
    'CDT': 'America/Chicago',
    'MDT': 'America/Denver',
    'PST': 'America/Los_Angeles',
    'PDT': 'America/Los_Angeles',
    'AKST': 'America/Anchorage',
    'AKDT': 'America/Anchorage',
    'HST': 'Pacific/Honolulu',
    'AST': 'America/Puerto_Rico',
  };
  final julyOffset = DateTime(now.year, 7, 1).timeZoneOffset.inMinutes;
  if (name == 'MST') {
    // Arizona stays on MST all year; Denver moves to MDT (-360) in July.
    return julyOffset == -360 ? 'America/Denver' : 'America/Phoenix';
  }
  final mapped = byName[name];
  if (mapped != null) return mapped;
  // Some devices report "GMT-5" style names: fall back to the standard
  // (January) offset.
  final std = DateTime(now.year, 1, 1).timeZoneOffset.inMinutes;
  switch (std) {
    case -240:
      return 'America/Puerto_Rico';
    case -300:
      return 'America/New_York';
    case -360:
      return 'America/Chicago';
    case -420:
      return julyOffset == -360 ? 'America/Denver' : 'America/Phoenix';
    case -480:
      return 'America/Los_Angeles';
    case -540:
      return 'America/Anchorage';
    case -600:
      return 'Pacific/Honolulu';
  }
  final hours = (std ~/ 60).abs();
  // Etc/GMT signs are inverted by convention: UTC-5 is "Etc/GMT+5".
  return 'Etc/GMT${std <= 0 ? '+' : '-'}$hours';
}

/// Writes the device zone to the user doc when it changes (travel, DST).
/// Fire-and-forget; never blocks the screen.
Future<void> _syncTimezone(String uid, Map<String, dynamic>? data) async {
  try {
    final now = DateTime.now();
    final id = _localTimezoneId();
    final off = now.timeZoneOffset.inMinutes;
    if (data != null &&
        data['timezone'] == id &&
        data['tzOffsetMinutes'] == off) {
      return;
    }
    await FirebaseFirestore.instance.collection('users').doc(uid).set({
      'timezone': id,
      'tzName': now.timeZoneName,
      'tzOffsetMinutes': off,
      'tzUpdatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
  } catch (e) {
    debugPrint('Timezone sync failed: $e');
  }
}

class _Pressable extends StatefulWidget {
  final Widget child;
  final VoidCallback? onTap;
  final double pressedScale;
  final bool reduceMotion;
  final String? semanticsLabel;
  final String? semanticsHint;

  const _Pressable({
    Key? key,
    required this.child,
    this.onTap,
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
    return Semantics(
      button: widget.onTap != null,
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
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTap: widget.onTap,
          child: AnimatedScale(
            scale: scale,
            duration: _down ? _Motion.pressIn : _Motion.pressOut,
            curve: _down ? Curves.easeOut : _Motion.settle,
            child: widget.child,
          ),
        ),
      ),
    );
  }
}

class JoviHealthHomeWidget extends StatefulWidget {
  final double width;
  final double height;
  final String? userId;
  final String? displayName;
  final FFUploadedFile? photoUrl;

  const JoviHealthHomeWidget({
    Key? key,
    required this.width,
    required this.height,
    this.userId,
    this.displayName,
    this.photoUrl,
  }) : super(key: key);

  @override
  State<JoviHealthHomeWidget> createState() => _JoviHealthHomeWidgetState();
}

class _JoviHealthHomeWidgetState extends State<JoviHealthHomeWidget>
    with TickerProviderStateMixin {
  // =================================================================
  // SECTION 1: CONSTANTS
  // =================================================================

  static const String joviLogoAssetUrl =
      'https://storage.googleapis.com/flutterflow-io-6f20.appspot.com/projects/kurv-health-3vcfmp/assets/gveqn2eoe4nf/jovi_header_logo_master.png';
  static const Duration dataCacheDuration = Duration(minutes: 5);
  // TODO(JC): ROTATE this key at openweathermap.org (exposed in client
  // builds + shared externally). Move behind the Cloud Function proxy
  // alongside the AI keys when that work lands.
  static const String weatherApiKey = '39eee692f6e29d0092f80bac534c5db7';

  // =================================================================
  // SECTION 2: STATE VARIABLES
  // =================================================================

  // User Profile
  String? userFirstName;
  String? userLastName;
  String? userFullName;
  String? userProfileImageUrl;
  String? userProfileImagePath;

  // Plan State
  String? insurancePlanType;
  String? membershipId;
  double? monthlyPremium;
  int? annualDeductible;
  bool? includesDental;
  bool? includesVision;
  bool coverageActive = true;
  DateTime? policyRenewalDate;
  DateTime? policyStartDate; // NEW: for pace calc
  double deductibleUsed = 0.0;
  bool loadingInsuranceData = true;

  // Weather Module
  Map<String, dynamic> weatherData = {};
  bool weatherLoading = true;
  List<Map<String, dynamic>> forecastData = [];
  String? weatherHealthTip; // NEW: contextual health note

  // Layout
  ScreenType currentScreenType = ScreenType.compact;
  ResponsiveConfig layoutSettings = ResponsiveConfig(
    paddingH: 20,
    paddingV: 20,
    contentMax: double.infinity,
    actionColumns: 3,
    actionItemHeight: 105,
    actionIconDimension: 28,
    actionTextSize: 13,
    wideMode: false,
    hasHinge: false,
  );

  double? _lastScreenWidth;
  bool? _lastHasHinge;

  // Animations
  late AnimationController mainFadeAnimator;
  late AnimationController contentSlideAnimator;
  late AnimationController progressAnimator;
  late AnimationController buttonRevealAnimator;
  late AnimationController _fabCollapseAnimator;

  late Animation<double> mainFadeEffect;
  late Animation<Offset> contentSlideEffect;
  late Animation<double> progressEffect;
  late Animation<double> buttonRevealEffect;
  late Animation<double> _fabCollapseEffect;

  // MediaQuery.disableAnimations (iOS Reduce Motion). Read in
  // didChangeDependencies so it tracks the setting live.
  bool _reduceMotion = false;

  // Cache
  DateTime? lastDataRefresh;
  StreamSubscription<DocumentSnapshot>? _profileSubscription;

  // True when location permission has never been asked, so the weather
  // chip can offer an opt-in instead of us prompting on launch.
  bool _locationPromptAvailable = false;

  // Quick Actions badges
  int upcomingAppointmentsCount = 0;
  bool hasRefillsDue = false;
  // Does the current user have any pets on file? Used to show a chooser
  // when they tap "New Claim" so they can pick human vs pet claim flow.
  bool _hasPets = false;

  String? _currentImageUrl;

  // NEW: Action Needed items
  List<ActionItem> _actionItems = [];
  bool _actionItemsLoaded = false;

  // NEW: For You insights
  List<ForYouInsight> _insights = [];
  int _currentInsightIndex = 0;
  Timer? _insightRotationTimer;

  // NEW: Monthly spend history for histogram
  List<MonthlySpend> _monthlySpend = [];
  double _paceTarget = 0; // expected monthly spend to hit deductible

  // NEW: FAB scroll behavior
  final ScrollController _scrollController = ScrollController();
  bool _fabExpanded = true;
  // Controls the compact/expanded state of the Plan Details card
  // on mobile layouts. Progress card is always the hero.
  bool _planDetailsExpanded = false;
  // Controls the 12-Month Trend histogram visibility in the Progress card.
  // Hidden by default — users who want to see their spend trend can expand.
  bool _trendExpanded = false;

  // Track previous deductibleUsed to animate progress on *change*
  double _previousDeductibleUsed = 0.0;

  // =================================================================
  // SECTION 3: LIFECYCLE (SIMPLIFIED)
  // =================================================================

  @override
  void initState() {
    super.initState();
    setupAnimationControllers();
    _setupScrollListener(); // FAB collapse behavior
    initializeUserProfile();
    initializeWeatherModule();
    _loadAppointmentsAndRefills();
    _setupProfileListener();
    _checkPetsSubcollection();
    _startInsightRotation();
    // Play the entrance on the first frame regardless of data. r1 only
    // faded content in after the profile fetch, so a failed fetch left the
    // page blank.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _playEntrance();
    });
  }

  /// Quick one-shot read of the users/{uid}/pets subcollection. The profile
  /// listener only catches pets in the legacy JSON array on the user doc;
  /// Pet Profiles writes to a subcollection. This check flips `_hasPets` on
  /// if anything exists in the subcollection.
  Future<void> _checkPetsSubcollection() async {
    try {
      final uid = widget.userId ?? FirebaseAuth.instance.currentUser?.uid;
      if (uid == null) return;
      final snap = await FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('pets')
          .limit(1)
          .get();
      if (!mounted) return;
      if (snap.docs.isNotEmpty && !_hasPets) {
        setState(() {
          _hasPets = true;
        });
      }
    } catch (e) {
      // Non-fatal — if this fails, the claim chooser just won't show the
      // pet option. User can still file claims through account menu.
      if (kDebugMode)
        print('HomeDashboard: pet subcollection check failed: $e');
    }
  }

  // Firestore listener is the single source of truth for profile updates.
  // Removed redundant didChangeDependencies and didUpdateWidget triggers.
  void _setupProfileListener() {
    String? uid = widget.userId ?? FirebaseAuth.instance.currentUser?.uid;
    if (uid != null) {
      _profileSubscription = FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .snapshots()
          .listen((snapshot) {
        if (snapshot.exists && mounted) {
          final data = snapshot.data();
          final newPhotoUrl = data?['photo_url'] as String?;
          final newImagePath = data?['image_path'] as String?;
          final newImageUrl =
              newPhotoUrl?.isNotEmpty == true ? newPhotoUrl : newImagePath;

          if (newImageUrl != _currentImageUrl) {
            _currentImageUrl = newImageUrl;
            initializeUserProfile(forceReload: true);
          }

          // Detect whether the user has any pets on file.
          // Legacy: pets stored as a JSON-string-array (or list) on user doc.
          // The canonical subcollection at users/{uid}/pets is checked
          // separately on first read — see _checkPetsSubcollection().
          bool hasPetsInLegacy = false;
          final rawPets = data?['pets'];
          if (rawPets is List && rawPets.isNotEmpty) {
            hasPetsInLegacy = true;
          } else if (rawPets is String && rawPets.trim().isNotEmpty) {
            try {
              final parsed = jsonDecode(rawPets);
              if (parsed is List && parsed.isNotEmpty) hasPetsInLegacy = true;
            } catch (_) {}
          }
          if (hasPetsInLegacy && !_hasPets) {
            setState(() {
              _hasPets = true;
            });
          }
        }
      });
    }
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // Only layout analysis here — no data refetch.
    _reduceMotion = MediaQuery.of(context).disableAnimations;
    if (_reduceMotion) _jumpAnimationsToEnd();
    analyzeScreenConfiguration();
  }

  @override
  void dispose() {
    mainFadeAnimator.dispose();
    contentSlideAnimator.dispose();
    progressAnimator.dispose();
    buttonRevealAnimator.dispose();
    _fabCollapseAnimator.dispose();
    _profileSubscription?.cancel();
    _insightRotationTimer?.cancel();
    _insightResumeTimer?.cancel();
    _scrollController.dispose();
    super.dispose();
  }

  // =================================================================
  // SECTION 4: ANIMATIONS
  // =================================================================

  void setupAnimationControllers() {
    mainFadeAnimator = AnimationController(
      vsync: this,
      duration: _Motion.enter,
    );
    contentSlideAnimator = AnimationController(
      vsync: this,
      duration: _Motion.enter,
    );
    progressAnimator = AnimationController(
      vsync: this,
      duration: _Motion.progress,
    );
    buttonRevealAnimator = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 320),
    );
    _fabCollapseAnimator = AnimationController(
      vsync: this,
      duration: _Motion.fab,
      value: 1.0, // start expanded
    );

    mainFadeEffect = CurvedAnimation(
      parent: mainFadeAnimator,
      curve: _Motion.settle,
    );
    // A 3% rise reads as content settling into place. The old 20% slide
    // travelled far enough to register as movement across the screen.
    contentSlideEffect = Tween<Offset>(
      begin: const Offset(0, 0.03),
      end: Offset.zero,
    ).animate(CurvedAnimation(
      parent: contentSlideAnimator,
      curve: _Motion.settle,
    ));
    progressEffect = CurvedAnimation(
      parent: progressAnimator,
      curve: _Motion.settle,
    );
    // FAB materialises: scale 0.6 → 1 with a fade, no overshoot. Nothing
    // threw it, so nothing should bounce.
    buttonRevealEffect = Tween<double>(
      begin: 0.6,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: buttonRevealAnimator,
      curve: _Motion.settle,
    ));
    _fabCollapseEffect = CurvedAnimation(
      parent: _fabCollapseAnimator,
      curve: _Motion.settle,
    );

    // FAB arrives just after the content, not 1.8 s later.
    Future.delayed(const Duration(milliseconds: 450), () {
      if (!mounted) return;
      if (_reduceMotion) {
        buttonRevealAnimator.value = 1.0;
      } else {
        buttonRevealAnimator.forward();
      }
    });
  }

  void _playEntrance() {
    if (_reduceMotion) {
      mainFadeAnimator.value = 1.0;
      contentSlideAnimator.value = 1.0;
      return;
    }
    // forward() on a completed controller is a no-op, so this is safe to
    // call again when the profile lands.
    mainFadeAnimator.forward();
    contentSlideAnimator.forward();
  }

  /// Reduce Motion: entrance and progress animations become instant. State
  /// changes that carry meaning (colour, opacity, size) are kept.
  void _jumpAnimationsToEnd() {
    mainFadeAnimator.value = 1.0;
    contentSlideAnimator.value = 1.0;
    progressAnimator.value = 1.0;
    buttonRevealAnimator.value = 1.0;
  }

  void _setFabExpanded(bool expanded) {
    if (_fabExpanded == expanded) return;
    setState(() => _fabExpanded = expanded);
    if (_reduceMotion) {
      _fabCollapseAnimator.value = expanded ? 1.0 : 0.0;
    } else if (expanded) {
      _fabCollapseAnimator.forward();
    } else {
      _fabCollapseAnimator.reverse();
    }
  }

  // =================================================================
  // SECTION 5: FAB SCROLL BEHAVIOR
  // =================================================================

  void _setupScrollListener() {
    _scrollController.addListener(() {
      // Collapse FAB after scrolling past 80px; re-expand when back near top.
      final offset = _scrollController.offset;

      if (offset > 80 && _fabExpanded) {
        _setFabExpanded(false);
      } else if (offset <= 20 && !_fabExpanded) {
        _setFabExpanded(true);
      }
    });
  }

  // =================================================================
  // SECTION 6: SCREEN CONFIGURATION
  // =================================================================

  void analyzeScreenConfiguration() {
    final mediaQuery = MediaQuery.of(context);
    final screenWidth = mediaQuery.size.width;
    final displayFeatures = mediaQuery.displayFeatures;

    bool hasHinge = false;
    for (final feature in displayFeatures) {
      if (feature.type == ui_dart.DisplayFeatureType.fold ||
          feature.type == ui_dart.DisplayFeatureType.hinge ||
          feature.type == ui_dart.DisplayFeatureType.cutout) {
        hasHinge = true;
        break;
      }
    }

    if (_lastScreenWidth == screenWidth && _lastHasHinge == hasHinge) {
      return;
    }

    ScreenType screenType;
    if (hasHinge) {
      screenType = ScreenType.expanded;
    } else if (screenWidth >= 1024) {
      screenType = ScreenType.large;
    } else if (screenWidth >= 600) {
      screenType = ScreenType.medium;
    } else {
      screenType = ScreenType.compact;
    }

    // Only ever called from didChangeDependencies, which is followed by a
    // build, so plain assignment is enough — no post-frame setState and no
    // extra frame rendered with the stale layout.
    _lastScreenWidth = screenWidth;
    _lastHasHinge = hasHinge;
    currentScreenType = screenType;
    layoutSettings = generateLayoutConfig(screenType, screenWidth, hasHinge);
  }

  ResponsiveConfig generateLayoutConfig(
    ScreenType type,
    double width,
    bool hasHinge,
  ) {
    switch (type) {
      case ScreenType.expanded:
        return ResponsiveConfig(
          paddingH: 16,
          paddingV: 20,
          contentMax: double.infinity,
          actionColumns: width > 900 ? 6 : (width > 700 ? 5 : 4),
          actionItemHeight: 120,
          actionIconDimension: 36,
          actionTextSize: 15,
          wideMode: true,
          hasHinge: true,
          useTwoColumnLayout: width >= 900,
        );
      case ScreenType.large:
        return ResponsiveConfig(
          paddingH: 40,
          paddingV: 28,
          contentMax: 1400,
          actionColumns: 6,
          actionItemHeight: 125,
          actionIconDimension: 38,
          actionTextSize: 16,
          wideMode: true,
          hasHinge: false,
          useTwoColumnLayout: width >= 1100,
        );
      case ScreenType.medium:
        return ResponsiveConfig(
          paddingH: 20,
          paddingV: 24,
          contentMax: double.infinity,
          actionColumns: 4,
          actionItemHeight: 115,
          actionIconDimension: 32,
          actionTextSize: 14,
          wideMode: true,
          hasHinge: false,
          useTwoColumnLayout: width >= 900,
        );
      case ScreenType.compact:
      default:
        return ResponsiveConfig(
          paddingH: 20,
          paddingV: 20,
          contentMax: double.infinity,
          actionColumns: 3,
          actionItemHeight: width < 360 ? 95 : 105,
          actionIconDimension: width < 360 ? 24 : 28,
          actionTextSize: width < 360 ? 12 : 13,
          wideMode: false,
          hasHinge: false,
          useTwoColumnLayout: false,
        );
    }
  }

  // =================================================================
  // SECTION 7: DATA FETCHING
  // =================================================================

  Future<void> initializeUserProfile({bool forceReload = false}) async {
    if (!forceReload &&
        lastDataRefresh != null &&
        DateTime.now().difference(lastDataRefresh!) < dataCacheDuration) {
      return;
    }

    setState(() => loadingInsuranceData = true);
    String? uid = widget.userId ?? FirebaseAuth.instance.currentUser?.uid;
    if (uid == null) {
      setState(() => loadingInsuranceData = false);
      return;
    }

    try {
      final docSnap =
          await FirebaseFirestore.instance.collection('users').doc(uid).get();
      final data = docSnap.data();
      // Keep the member's timezone current for server-side reminders.
      // ignore: unawaited_futures
      _syncTimezone(uid, data);
      if (data == null) {
        setState(() {
          insurancePlanType = 'Standard Plan';
          loadingInsuranceData = false;
        });
        return;
      }

      final pt = data['planType'] as String? ?? 'Standard Plan';
      double tp = 0.0;
      final premiumField = data['premium'] ?? data['totalPremium'];
      if (premiumField != null) {
        if (premiumField is String) {
          tp = double.tryParse(premiumField) ?? 0.0;
        } else if (premiumField is num) {
          tp = premiumField.toDouble();
        }
      }

      bool dental = false;
      bool vision = false;
      if (data['dental'] != null) {
        if (data['dental'] is bool) {
          dental = data['dental'] as bool;
        } else if (data['dental'] is String) {
          dental = data['dental'].toString().toLowerCase() == 'true';
        }
      }
      if (data['vision'] != null) {
        if (data['vision'] is bool) {
          vision = data['vision'] as bool;
        } else if (data['vision'] is String) {
          vision = data['vision'].toString().toLowerCase() == 'true';
        }
      }

      DateTime? renewal;
      DateTime? policyStart;
      if (data['renew'] != null) {
        try {
          if (data['renew'] is Timestamp) {
            renewal = (data['renew'] as Timestamp).toDate();
          }
        } catch (e) {
          if (kDebugMode) print('Error parsing renewal date: $e');
        }
      }
      if (data['policyStart'] != null) {
        try {
          if (data['policyStart'] is Timestamp) {
            policyStart = (data['policyStart'] as Timestamp).toDate();
          }
        } catch (e) {}
      }
      // If policyStart missing, infer from renewal - 1 year
      policyStart ??= renewal?.subtract(Duration(days: 365));

      final fName = data['first'] as String? ??
          data['firstName'] as String? ??
          data['onboard_fullName'] as String? ??
          '';
      final lName =
          data['last'] as String? ?? data['lastName'] as String? ?? '';
      String fullNameValue = '';
      if (data['onboard_fullName'] != null &&
          (data['onboard_fullName'] as String).isNotEmpty) {
        fullNameValue = data['onboard_fullName'] as String;
      } else if (fName.isNotEmpty || lName.isNotEmpty) {
        fullNameValue = '$fName $lName'.trim();
      }

      final photoUrl = data['photo_url'] as String? ?? '';
      final imagePath = data['image_path'] as String? ?? '';

      final paidSoFar = (data['updateDed'] as num?)?.toDouble() ?? 0.0;
      final rawMembers = data['members'] as List<dynamic>? ?? [];
      String? memId;
      int? ded;

      if (rawMembers.isNotEmpty) {
        try {
          final firstM =
              jsonDecode(rawMembers.first as String) as Map<String, dynamic>;
          memId = firstM['memberId'] as String?;
          ded = (firstM['deductible'] as num?)?.toInt();
        } catch (e) {
          if (kDebugMode) print('Error parsing members: $e');
        }
      }
      memId ??= data['memberId'] as String?;

      // Parse monthly spend history if present. We intentionally do NOT
      // synthesize or backfill fake months — a user with 3 months of real
      // data should see 3 months, not a made-up 12-month distribution.
      List<MonthlySpend> spendHistory = [];
      final rawHistory = data['monthlySpendHistory'] as List<dynamic>? ?? [];
      if (rawHistory.isNotEmpty) {
        for (int i = 0; i < rawHistory.length && i < 12; i++) {
          try {
            final entry = rawHistory[i] is String
                ? jsonDecode(rawHistory[i] as String) as Map<String, dynamic>
                : rawHistory[i] as Map<String, dynamic>;
            spendHistory.add(MonthlySpend(
              monthsAgo: entry['monthsAgo'] as int? ?? i,
              amount: (entry['amount'] as num?)?.toDouble() ?? 0.0,
              monthLabel: entry['label'] as String? ?? '',
            ));
          } catch (e) {}
        }
      }

      final effectiveDeductible =
          ded ?? (data['deductible'] as num?)?.toInt() ?? 0;

      setState(() {
        insurancePlanType = pt;
        monthlyPremium = tp;
        includesDental = dental;
        includesVision = vision;
        userProfileImageUrl = photoUrl;
        userProfileImagePath = imagePath;
        userFirstName = fName;
        userLastName = lName;
        userFullName = fullNameValue;
        membershipId = memId;
        annualDeductible = effectiveDeductible;
        coverageActive = true;
        loadingInsuranceData = false;
        policyRenewalDate = renewal;
        policyStartDate = policyStart;
        lastDataRefresh = DateTime.now();

        _currentImageUrl = photoUrl.isNotEmpty ? photoUrl : imagePath;

        // Track previous value to animate on change
        _previousDeductibleUsed = deductibleUsed;
        deductibleUsed = paidSoFar.clamp(0.0, effectiveDeductible.toDouble());
        _monthlySpend = spendHistory;
        _paceTarget = _computePaceTarget(
            effectiveDeductible.toDouble(), policyStart, renewal);

        if (_previousDeductibleUsed != deductibleUsed) {
          if (_reduceMotion) {
            progressAnimator.value = 1.0;
          } else {
            progressAnimator.forward(from: 0);
          }
        }

        _playEntrance();
      });

      // Build action items & insights now that we have data
      _buildActionItems(data);
      _buildInsights(data);
    } catch (e) {
      if (kDebugMode) print('Error fetching plan info: $e');
      setState(() => loadingInsuranceData = false);
    }
  }

  // Expected monthly spend to hit deductible evenly over the plan year
  double _computePaceTarget(
      double deductible, DateTime? start, DateTime? renewal) {
    if (deductible <= 0) return 0;
    // Default to 12 months if we don't have plan dates
    int monthsInYear = 12;
    if (start != null && renewal != null) {
      final days = renewal.difference(start).inDays;
      monthsInYear = (days / 30.44).round().clamp(1, 24);
    }
    return deductible / monthsInYear;
  }

  // =================================================================
  // SECTION 8: ACTION NEEDED ITEMS (RULES ENGINE)
  // =================================================================

  Future<void> _buildActionItems(Map<String, dynamic> userData) async {
    List<ActionItem> items = [];
    final uid = widget.userId ?? FirebaseAuth.instance.currentUser?.uid;

    if (uid != null) {
      final fs = FirebaseFirestore.instance;
      // Fire all three queries in parallel instead of sequentially
      final futures = <Future<QuerySnapshot<Map<String, dynamic>>>>[
        fs
            .collection('prescriptionRefills')
            .where('userId', isEqualTo: uid)
            .where('status', isEqualTo: 'ready')
            .limit(3)
            .get()
            .catchError((e) {
          if (kDebugMode) print('Error loading refills for actions: $e');
          return _emptyQuerySnap('prescriptionRefills');
        }),
        fs
            .collection('users')
            .doc(uid)
            .collection('claims')
            .where('status', whereIn: ['needs_more_info', 'needs_info'])
            .limit(3)
            .get()
            .catchError((e) {
          if (kDebugMode) print('Error loading claims for actions: $e');
          return _emptyQuerySnap('users');
        }),
        fs
            .collection('users')
            .doc(uid)
            .collection('claims')
            .where('status', isEqualTo: 'draft')
            .limit(2)
            .get()
            .catchError((e) => _emptyQuerySnap('users')),
      ];

      final results = await Future.wait(futures);

      // 1. Refills ready for pickup
      for (final doc in results[0].docs) {
        final d = doc.data();
        final med = d['medicationName'] as String? ?? 'Medication';
        final pharm = d['pharmacyName'] as String? ?? 'pharmacy';
        items.add(ActionItem(
          id: 'refill_${doc.id}',
          title: '$med ready',
          subtitle: 'Pick up at $pharm',
          icon: Icons.medication,
          route: '/scriptRefill',
          priority: ActionPriority.urgent,
          ctaLabel: 'View',
        ));
      }

      // 2. Claims that need more info
      for (final doc in results[1].docs) {
        final d = doc.data();
        items.add(ActionItem(
          id: 'claim_${doc.id}',
          title: 'Claim needs info',
          subtitle: d['provider'] as String? ?? 'Provide requested details',
          icon: Icons.assignment_late,
          route: '/fileclaim',
          priority: ActionPriority.urgent,
          ctaLabel: 'Update',
        ));
      }

      // 3. Receipts pending upload (from draft claims)
      final draftsSnap = results[2];
      if (draftsSnap.docs.isNotEmpty) {
        items.add(ActionItem(
          id: 'receipts_${draftsSnap.docs.length}',
          title:
              '${draftsSnap.docs.length} receipt${draftsSnap.docs.length == 1 ? "" : "s"} to upload',
          subtitle: 'Finish filing to get reimbursed',
          icon: Icons.receipt_long,
          route: '/fileclaim',
          priority: ActionPriority.attention,
          ctaLabel: 'Finish',
        ));
      }

      // 4. Payment due soon (stub; assumes user doc has nextPaymentDue Timestamp)
      final nextPayment = userData['nextPaymentDue'];
      if (nextPayment is Timestamp) {
        final dueDate = nextPayment.toDate();
        final daysUntil = dueDate.difference(DateTime.now()).inDays;
        if (daysUntil >= 0 && daysUntil <= 5) {
          items.add(ActionItem(
            id: 'payment_due',
            title: daysUntil == 0
                ? 'Payment due today'
                : 'Payment due in $daysUntil day${daysUntil == 1 ? "" : "s"}',
            subtitle:
                'Monthly contribution: \$${monthlyPremium?.toStringAsFixed(2) ?? "—"}',
            icon: Icons.payment,
            route: '/plan',
            priority: daysUntil <= 2
                ? ActionPriority.urgent
                : ActionPriority.attention,
            ctaLabel: 'Pay now',
          ));
        }
      }
    }

    // 5. Renewal within 30 days
    if (policyRenewalDate != null) {
      final days = policyRenewalDate!.difference(DateTime.now()).inDays;
      if (days >= 0 && days <= 30) {
        items.add(ActionItem(
          id: 'renewal',
          title: days == 0
              ? 'Plan renews today'
              : 'Plan renews in $days day${days == 1 ? "" : "s"}',
          subtitle: 'Review your coverage before it auto-renews',
          icon: Icons.autorenew,
          route: '/quote',
          priority:
              days <= 7 ? ActionPriority.attention : ActionPriority.gentle,
          ctaLabel: 'Review',
        ));
      }
    }

    // 6. Spouse profile incomplete
    final hasSpouse = userData['hasSpouse'] == true;
    final spouseFirst = userData['spouseFirstName'] as String? ?? '';
    final spouseSsn = userData['spouseSsn'] as String? ?? '';
    if (hasSpouse && (spouseFirst.isEmpty || spouseSsn.isEmpty)) {
      items.add(ActionItem(
        id: 'spouse_incomplete',
        title: 'Finish spouse profile',
        subtitle: 'A few details are still missing',
        icon: Icons.person_add,
        route: '/updateProfile',
        priority: ActionPriority.gentle,
        ctaLabel: 'Complete',
      ));
    }

    // 7. Dependents incomplete
    final numDeps = userData['numDependents'] as int? ?? 0;
    final depList = userData['dependents'] as List<dynamic>? ?? [];
    int incompleteDeps = 0;
    for (final raw in depList) {
      try {
        final d = raw is String
            ? jsonDecode(raw) as Map<String, dynamic>
            : raw as Map<String, dynamic>;
        final fn = d['firstName'] as String? ?? '';
        if (fn.isEmpty) incompleteDeps++;
      } catch (e) {}
    }
    if (incompleteDeps > 0) {
      items.add(ActionItem(
        id: 'deps_incomplete',
        title:
            '$incompleteDeps dependent profile${incompleteDeps == 1 ? "" : "s"} incomplete',
        subtitle: 'Add their info so they\'re covered',
        icon: Icons.family_restroom,
        route: '/updateProfile',
        priority: ActionPriority.gentle,
        ctaLabel: 'Add',
      ));
    }

    // Sort: urgent first, then attention, then gentle
    items.sort((a, b) => a.priority.index.compareTo(b.priority.index));

    if (mounted) {
      setState(() {
        _actionItems = items;
        _actionItemsLoaded = true;
      });
    }
  }

  // =================================================================
  // SECTION 9: FOR YOU INSIGHTS (RULES ENGINE)
  // =================================================================

  void _buildInsights(Map<String, dynamic> userData) {
    List<ForYouInsight> insights = [];
    final now = DateTime.now();

    // Responsibility pace insight
    if (annualDeductible != null && annualDeductible! > 0) {
      final pct = (deductibleUsed / annualDeductible!).clamp(0.0, 1.0);
      // How far into plan year
      double yearPct = 0.5;
      if (policyStartDate != null && policyRenewalDate != null) {
        final totalDays =
            policyRenewalDate!.difference(policyStartDate!).inDays;
        final elapsedDays = now.difference(policyStartDate!).inDays;
        if (totalDays > 0) {
          yearPct = (elapsedDays / totalDays).clamp(0.0, 1.0);
        }
      }
      if (yearPct > 0.1 && pct < yearPct - 0.15) {
        final diff = ((yearPct - pct) * 100).round();
        insights.add(ForYouInsight(
          id: 'pace_under',
          headline: 'Pacing $diff% under',
          body: 'You\'re using your plan less than average this year. Nice.',
          icon: Icons.trending_down,
          type: InsightType.celebration,
        ));
      } else if (yearPct > 0.1 && pct > yearPct + 0.2) {
        final diff = ((pct - yearPct) * 100).round();
        insights.add(ForYouInsight(
          id: 'pace_over',
          headline: 'Pacing $diff% above normal',
          body:
              'You might hit your annual limit early — plan ahead for costs above that.',
          icon: Icons.trending_up,
          type: InsightType.reminder,
          ctaLabel: 'See plan',
          ctaRoute: '/plan',
        ));
      }
    }

    // Pet birthday rule (within 14 days)
    final pets = userData['pets'] as List<dynamic>? ?? [];
    for (final raw in pets) {
      try {
        final p = raw is String
            ? jsonDecode(raw) as Map<String, dynamic>
            : raw as Map<String, dynamic>;
        final name = p['name'] as String? ?? '';
        final bdStr = p['birthdate'] as String? ?? '';
        if (name.isEmpty || bdStr.isEmpty) continue;
        DateTime? bd;
        try {
          bd = DateFormat('MM/dd/yyyy').parseStrict(bdStr);
        } catch (e) {}
        if (bd == null) continue;
        // Next birthday
        DateTime nextBd = DateTime(now.year, bd.month, bd.day);
        if (nextBd.isBefore(now)) {
          nextBd = DateTime(now.year + 1, bd.month, bd.day);
        }
        final daysUntil = nextBd.difference(now).inDays;
        if (daysUntil <= 14) {
          insights.add(ForYouInsight(
            id: 'pet_bday_$name',
            headline: daysUntil == 0
                ? '🎉 It\'s $name\'s birthday!'
                : '$name turns older in $daysUntil days',
            body: 'Their pet plan contribution will adjust on renewal.',
            icon: Icons.cake,
            type: InsightType.celebration,
          ));
        }
      } catch (e) {}
    }

    // Dental/Vision add-on nudge (if missing + 90+ days in plan)
    if ((includesDental == false && includesVision == false) &&
        policyStartDate != null) {
      final daysIn = now.difference(policyStartDate!).inDays;
      if (daysIn > 90) {
        insights.add(ForYouInsight(
          id: 'addon_nudge',
          headline: 'Round out your plan',
          body: 'Dental & vision start at \$15/mo — most members add both.',
          icon: Icons.auto_awesome,
          type: InsightType.nudge,
          ctaLabel: 'Add on',
          ctaRoute: '/updateProfile',
        ));
      }
    }

    // Bloodwork reminder (age-based intervals)
    // Guidelines: 20s→every 3yr, 30s→every 2-3yr, 40s→every 1-2yr,
    // 50s→annually, 60+→every 6-12mo
    _buildBloodworkInsight(userData, now, insights);

    // Milestone: halfway through plan year
    if (policyStartDate != null && policyRenewalDate != null) {
      final total = policyRenewalDate!.difference(policyStartDate!).inDays;
      final elapsed = now.difference(policyStartDate!).inDays;
      if (total > 0) {
        final frac = elapsed / total;
        if (frac >= 0.49 && frac <= 0.52) {
          insights.add(ForYouInsight(
            id: 'halfway',
            headline: 'You\'re halfway through your plan year',
            body: 'Good time to check in on your preventive care benefits.',
            icon: Icons.flag,
            type: InsightType.milestone,
          ));
        }
      }
    }

    // Fallback: friendly generic insight so card is never empty
    if (insights.isEmpty) {
      insights.add(ForYouInsight(
        id: 'welcome',
        headline: 'Welcome back, ${userFirstName ?? "friend"}',
        body: 'Everything looks good with your plan today.',
        icon: Icons.favorite,
        type: InsightType.celebration,
      ));
    }

    if (mounted) {
      setState(() {
        _insights = insights;
        _currentInsightIndex = 0;
      });
    }
  }

  bool _insightsPaused = false;
  Timer? _insightResumeTimer;

  void _startInsightRotation() {
    _insightRotationTimer?.cancel();
    _insightRotationTimer = Timer.periodic(Duration(seconds: 8), (_) {
      if (!mounted || _insights.length < 2 || _insightsPaused) return;
      setState(() {
        _currentInsightIndex = (_currentInsightIndex + 1) % _insights.length;
      });
    });
  }

  // User tapped to advance or pause. Pause rotation for 20s so they can read.
  void _pauseInsightRotation() {
    setState(() => _insightsPaused = true);
    _insightResumeTimer?.cancel();
    _insightResumeTimer = Timer(Duration(seconds: 20), () {
      if (mounted) setState(() => _insightsPaused = false);
    });
  }

  // ─── Bloodwork Reminder Logic ─────────────────────────────
  // Age-based recommended intervals (general guidelines):
  //   18-29: every 3 years  |  30-39: every 2–3 years
  //   40-49: every 1–2 years |  50-59: annually
  //   60+:   every 6–12 months
  void _buildBloodworkInsight(
    Map<String, dynamic> userData,
    DateTime now,
    List<ForYouInsight> insights,
  ) {
    // Parse date of birth
    DateTime? dob;
    final dobRaw =
        userData['dob'] ?? userData['dateOfBirth'] ?? userData['birthDate'];
    if (dobRaw is Timestamp) {
      dob = dobRaw.toDate();
    } else if (dobRaw is String && dobRaw.isNotEmpty) {
      try {
        dob = DateTime.parse(dobRaw);
      } catch (_) {
        try {
          dob = DateFormat('MM/dd/yyyy').parseStrict(dobRaw);
        } catch (_) {}
      }
    }
    // If we can't determine age, use a safe default (annual reminder)
    int age = 35; // fallback
    if (dob != null) {
      age = now.year - dob.year;
      if (now.month < dob.month ||
          (now.month == dob.month && now.day < dob.day)) {
        age--;
      }
    }

    // Determine recommended interval in days
    int recommendedIntervalDays;
    String intervalLabel;
    if (age < 30) {
      recommendedIntervalDays = 365 * 3; // every 3 years
      intervalLabel = 'every 2–3 years';
    } else if (age < 40) {
      recommendedIntervalDays = 365 * 2; // every 2 years (conservative end)
      intervalLabel = 'every 2–3 years';
    } else if (age < 50) {
      recommendedIntervalDays = 365 + 182; // ~18 months
      intervalLabel = 'every 1–2 years';
    } else if (age < 60) {
      recommendedIntervalDays = 365; // annually
      intervalLabel = 'annually';
    } else {
      recommendedIntervalDays = 274; // ~9 months (between 6–12mo)
      intervalLabel = 'every 6–12 months';
    }

    // Check when user last had bloodwork
    DateTime? lastBloodwork;
    final bwRaw = userData['lastBloodworkDate'] ?? userData['lastLabDate'];
    if (bwRaw is Timestamp) {
      lastBloodwork = bwRaw.toDate();
    } else if (bwRaw is String && bwRaw.isNotEmpty) {
      try {
        lastBloodwork = DateTime.parse(bwRaw);
      } catch (_) {
        try {
          lastBloodwork = DateFormat('MM/dd/yyyy').parseStrict(bwRaw);
        } catch (_) {}
      }
    }

    // Build insight based on status
    if (lastBloodwork == null) {
      // No bloodwork on file — gentle reminder
      insights.add(ForYouInsight(
        id: 'bloodwork_none',
        headline: 'Time for a checkup?',
        body: 'Regular bloodwork helps catch issues early. '
            'At your age, guidelines suggest $intervalLabel.',
        icon: Icons.bloodtype,
        type: InsightType.reminder,
        ctaLabel: 'Request care',
        ctaRoute: '/requests',
      ));
    } else {
      final daysSince = now.difference(lastBloodwork).inDays;
      // Approaching due (within 30 days of recommended interval)
      if (daysSince >= recommendedIntervalDays - 30 &&
          daysSince < recommendedIntervalDays) {
        final daysLeft = recommendedIntervalDays - daysSince;
        insights.add(ForYouInsight(
          id: 'bloodwork_approaching',
          headline: 'Bloodwork due soon',
          body: 'Your next routine labs are recommended in about '
              '$daysLeft day${daysLeft == 1 ? "" : "s"}. '
              'Schedule early to pick your time.',
          icon: Icons.bloodtype,
          type: InsightType.reminder,
          ctaLabel: 'Schedule',
          ctaRoute: '/requests',
        ));
      }
      // Overdue
      else if (daysSince >= recommendedIntervalDays) {
        final monthsOver =
            ((daysSince - recommendedIntervalDays) / 30.44).round();
        final overLabel = monthsOver <= 0
            ? 'now'
            : '$monthsOver month${monthsOver == 1 ? "" : "s"} overdue';
        insights.add(ForYouInsight(
          id: 'bloodwork_overdue',
          headline: 'Bloodwork is $overLabel',
          body: 'Guidelines suggest labs $intervalLabel. '
              'Your last was ${DateFormat("MMM d, yyyy").format(lastBloodwork)}.',
          icon: Icons.bloodtype,
          type: InsightType.nudge,
          ctaLabel: 'Schedule',
          ctaRoute: '/requests',
        ));
      }
      // Else: they're current — no insight needed
    }
  }

  // =================================================================
  // SECTION 10: WEATHER MODULE (WITH HEALTH CONTEXT)
  // =================================================================

  /// Weather is opt-in. We never trigger the location prompt on launch: the
  /// chip offers "Tap to enable" and the system dialog appears only when the
  /// user asks for the feature (permission requested in context). If access
  /// was already granted we load silently.
  Future<void> initializeWeatherModule() async {
    if (mounted) setState(() => weatherLoading = true);

    try {
      final permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.always ||
          permission == LocationPermission.whileInUse) {
        await _loadWeatherForCurrentPosition();
        return;
      }
      if (!mounted) return;
      setState(() {
        weatherData = {};
        forecastData = [];
        weatherHealthTip = null;
        weatherLoading = false;
        // On iOS `denied` also covers "not determined yet", so we can still
        // offer the opt-in. `deniedForever` means Settings is the only way.
        _locationPromptAvailable = permission == LocationPermission.denied;
      });
    } catch (e) {
      if (kDebugMode) print('Error checking location permission: $e');
      _setWeatherUnavailable();
    }
  }

  /// Runs when the user taps the opt-in chip.
  Future<void> _requestLocationAndLoadWeather() async {
    HapticFeedback.lightImpact();
    if (mounted) {
      setState(() {
        weatherLoading = true;
        _locationPromptAvailable = false;
      });
    }
    try {
      final permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.always ||
          permission == LocationPermission.whileInUse) {
        await _loadWeatherForCurrentPosition();
      } else {
        _setWeatherUnavailable();
      }
    } catch (e) {
      if (kDebugMode) print('Error requesting location: $e');
      _setWeatherUnavailable();
    }
  }

  Future<void> _loadWeatherForCurrentPosition() async {
    final position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.medium);
    await loadWeatherForCoordinates(position.latitude, position.longitude);
  }

  /// No location or no network: hide the chip. r1 generated random
  /// "Denver" weather here, which presented made-up data as real.
  void _setWeatherUnavailable() {
    if (!mounted) return;
    setState(() {
      weatherData = {};
      forecastData = [];
      weatherHealthTip = null;
      weatherLoading = false;
    });
  }

  Future<void> loadWeatherForCoordinates(double lat, double lon) async {
    try {
      final weatherUrl =
          'https://api.openweathermap.org/data/2.5/weather?lat=$lat&lon=$lon&appid=$weatherApiKey&units=imperial';
      final uvUrl =
          'https://api.openweathermap.org/data/2.5/uvi?lat=$lat&lon=$lon&appid=$weatherApiKey';
      final forecastUrl =
          'https://api.openweathermap.org/data/2.5/forecast?lat=$lat&lon=$lon&appid=$weatherApiKey&units=imperial';
      final airUrl =
          'https://api.openweathermap.org/data/2.5/air_pollution?lat=$lat&lon=$lon&appid=$weatherApiKey';

      final responses = await Future.wait([
        network_http.get(Uri.parse(weatherUrl)),
        network_http.get(Uri.parse(uvUrl)),
        network_http.get(Uri.parse(forecastUrl)),
        network_http.get(Uri.parse(airUrl)),
      ]);
      final weatherResponse = responses[0];
      final uvResponse = responses[1];
      final forecastResponse = responses[2];
      final airResponse = responses[3];

      if (weatherResponse.statusCode == 200) {
        final weatherJson = jsonDecode(weatherResponse.body);
        String uvIndex = '0';
        double uvValue = 0.0;

        if (uvResponse.statusCode == 200) {
          final uvData = jsonDecode(uvResponse.body);
          uvValue = uvData['value']?.toDouble() ?? 0.0;
          uvIndex = uvValue.toStringAsFixed(0);
        }

        int airQualityIdx = 1;
        if (airResponse.statusCode == 200) {
          try {
            final air = jsonDecode(airResponse.body);
            airQualityIdx =
                (air['list']?[0]?['main']?['aqi'] as num?)?.toInt() ?? 1;
          } catch (e) {}
        }

        List<Map<String, dynamic>> forecast = [];
        if (forecastResponse.statusCode == 200) {
          final forecastDataJson = jsonDecode(forecastResponse.body);
          final List<dynamic> forecastList = forecastDataJson['list'] ?? [];
          Map<String, Map<String, dynamic>> dailyForecasts = {};

          for (var item in forecastList) {
            final DateTime date =
                DateTime.fromMillisecondsSinceEpoch(item['dt'] * 1000);
            final String dateKey = DateFormat('yyyy-MM-dd').format(date);
            final int hour = date.hour;

            if (!dailyForecasts.containsKey(dateKey)) {
              dailyForecasts[dateKey] = {
                'dt': item['dt'],
                'temp_max': item['main']['temp_max']?.toDouble() ?? 0.0,
                'temp_min': item['main']['temp_min']?.toDouble() ?? 0.0,
                'description': item['weather'][0]['main'] ?? '',
                'icon':
                    convertWeatherCodeToEmoji(item['weather'][0]['id'] ?? 800),
                'humidity': item['main']['humidity'] ?? 0,
                'date': date,
              };
            } else {
              final existingHour = DateTime.fromMillisecondsSinceEpoch(
                      dailyForecasts[dateKey]!['dt'] * 1000)
                  .hour;
              if ((hour - 12).abs() < (existingHour - 12).abs()) {
                dailyForecasts[dateKey] = {
                  'dt': item['dt'],
                  'temp_max': item['main']['temp_max']?.toDouble() ?? 0.0,
                  'temp_min': item['main']['temp_min']?.toDouble() ?? 0.0,
                  'description': item['weather'][0]['main'] ?? '',
                  'icon': convertWeatherCodeToEmoji(
                      item['weather'][0]['id'] ?? 800),
                  'humidity': item['main']['humidity'] ?? 0,
                  'date': date,
                };
              }
            }
          }
          forecast = dailyForecasts.values.take(5).toList();
        }

        final sunrise = DateTime.fromMillisecondsSinceEpoch(
            weatherJson['sys']['sunrise'] * 1000);
        final sunset = DateTime.fromMillisecondsSinceEpoch(
            weatherJson['sys']['sunset'] * 1000);
        final timeFormat = DateFormat('h:mm a');

        final humidity = weatherJson['main']['humidity'] as int? ?? 0;
        final temp = (weatherJson['main']['temp'] as num?)?.toDouble() ?? 70;
        final aqiLabel = _aqiLabel(airQualityIdx);

        setState(() {
          weatherData = {
            'temperature': '${weatherJson['main']['temp'].round()}°F',
            'feelsLike': '${weatherJson['main']['feels_like'].round()}°F',
            'humidity': '$humidity%',
            'windSpeed': '${weatherJson['wind']['speed'].round()} mph',
            'cityName': weatherJson['name'] ?? 'Your Location',
            'description': weatherJson['weather'][0]['main'],
            'pressure': '${weatherJson['main']['pressure']} hPa',
            'cloudCover': '${weatherJson['clouds']['all']}%',
            'visibility': weatherJson['visibility'] != null
                ? '${(weatherJson['visibility'] / 1000).toStringAsFixed(1)} km'
                : 'N/A',
            'uvIndex': uvIndex,
            'uvValue': uvValue,
            'airQuality': aqiLabel,
            'aqiIdx': airQualityIdx,
            'sunrise': timeFormat.format(sunrise),
            'sunset': timeFormat.format(sunset),
            'windDirection':
                calculateWindDirection(weatherJson['wind']['deg'] ?? 0),
            'icon': convertWeatherCodeToEmoji(weatherJson['weather'][0]['id']),
            'rawTemp': temp,
          };
          forecastData = forecast;
          weatherHealthTip =
              _computeHealthTip(uvValue, airQualityIdx, humidity, temp);
          weatherLoading = false;
        });
      } else {
        _setWeatherUnavailable();
      }
    } catch (e) {
      if (kDebugMode) print('Error fetching weather: $e');
      _setWeatherUnavailable();
    }
  }

  String _aqiLabel(int idx) {
    switch (idx) {
      case 1:
        return 'Good';
      case 2:
        return 'Fair';
      case 3:
        return 'Moderate';
      case 4:
        return 'Poor';
      case 5:
        return 'Very Poor';
      default:
        return 'Unknown';
    }
  }

  // Contextual health tip based on current conditions.
  // Priority order: air quality > UV > temp extremes > humidity.
  String? _computeHealthTip(double uv, int aqi, int humidity, double temp) {
    if (aqi >= 4) {
      return '🫁 Poor air quality today — consider indoor activities if you have asthma or respiratory issues.';
    }
    if (uv >= 8) {
      return '☀️ Very high UV — wear sunscreen and remember your dermatology benefit covers it.';
    }
    if (uv >= 6) {
      return '🕶️ High UV today — sunscreen and shade recommended.';
    }
    if (temp >= 95) {
      return '🥵 Extreme heat — stay hydrated and watch for heat exhaustion symptoms.';
    }
    if (temp <= 20) {
      return '🧣 Very cold — bundle up, and be gentle on joints during outdoor activity.';
    }
    if (humidity >= 75 && temp > 75) {
      return '💧 Humid day — good reminder to check allergy meds and refill if needed.';
    }
    if (aqi == 3) {
      return '🌫️ Moderate air quality — fine for most, take it easy if you\'re sensitive.';
    }
    // Spring allergy season heuristic (March–May)
    final month = DateTime.now().month;
    if (month >= 3 && month <= 5 && humidity < 50) {
      return '🌸 Dry spring day — pollen levels may be high. Your plan covers antihistamines.';
    }
    return null; // No tip — weather is unremarkable, don't add noise
  }

  /// Unified navigation for the Appointments surface. Points to Care
  /// Records (the superset widget that shows upcoming + past visits +
  /// timeline in one place), with a fallback to the legacy /appt route
  /// if Care Records isn't wired up yet.
  ///
  /// Ship sequence: Care Records is the new default; /appt is kept as a
  /// backup during initial rollout. After 30 days with no issues, the
  /// /appt route and AppointmentsWidget can be retired entirely.
  /// Recent Activity "See all" -> the notification inbox, which is the full
  /// history of appointments, claims, refills and billing. Falls back to
  /// Care Records if the `notifications` page has not been created yet.
  void _navigateToActivity() {
    HapticFeedback.lightImpact();
    try {
      context.pushNamed('notifications');
      return;
    } catch (_) {}
    _navigateToCareRecords();
  }

  void _navigateToCareRecords() {
    HapticFeedback.lightImpact();
    final routes = [
      'careRecords',
      'CareRecords',
      'care_records',
      'carerecords',
      'care',
      'Care',
      'records',
      'Records',
    ];
    for (final route in routes) {
      try {
        context.pushNamed(route);
        return;
      } catch (_) {
        continue;
      }
    }
    // Fallback: legacy path-based route to AppointmentsWidget. Kept as a
    // safety net so a broken Care Records deploy doesn't strand users.
    try {
      context.push('/appt');
    } catch (_) {
      // Last resort — show a snackbar rather than hanging silently.
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('Could not open Appointments.'),
          backgroundColor: Color(0xFFE53E3E),
          behavior: SnackBarBehavior.floating,
        ));
      }
    }
  }

  // ─────────────────────────────────────────────────────────────────────
  // CLAIM TYPE CHOOSER
  // Shown when the user has pets on file and taps the "New Claim" quick
  // action. Two cards: one for medical claims (self/family) and one for
  // pet claims. Each card routes to its respective flow.
  // ─────────────────────────────────────────────────────────────────────

  void _showClaimTypeChooser() {
    HapticFeedback.lightImpact();
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      barrierColor: Colors.black.withOpacity(0.55),
      builder: (sheetCtx) => _buildClaimTypeSheet(sheetCtx),
    );
  }

  Widget _buildClaimTypeSheet(BuildContext sheetCtx) {
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [joviNavy, joviNavyDark],
        ),
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(26),
          topRight: Radius.circular(26),
        ),
        border: Border.all(
          color: Colors.white.withOpacity(0.1),
          width: 1,
        ),
      ),
      padding: EdgeInsets.fromLTRB(
        20,
        12,
        20,
        24 + MediaQuery.of(sheetCtx).padding.bottom,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Drag handle
          Container(
            width: 42,
            height: 4,
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.25),
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(height: 18),
          const Text(
            'Who is this claim for?',
            style: TextStyle(
              color: Colors.white,
              fontSize: 19,
              fontWeight: FontWeight.w700,
              letterSpacing: -0.3,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            'Pick the flow that fits the bill you want to submit.',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white.withOpacity(0.6),
              fontSize: 13,
              fontWeight: FontWeight.w500,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 20),
          _buildClaimChooserCard(
            sheetCtx: sheetCtx,
            icon: Icons.person_outline_rounded,
            title: 'For me or a family member',
            subtitle:
                'Medical bills, prescriptions, and care for you or anyone on your membership.',
            accent: joviCoral,
            accentDark: joviCoralDark,
            onTap: () {
              Navigator.of(sheetCtx).pop();
              // Slight delay so the sheet finishes closing before pushing
              // a new route — avoids visual jank.
              Future.delayed(const Duration(milliseconds: 120), () {
                if (!mounted) return;
                try {
                  context.push('/fileclaim');
                } catch (_) {}
              });
            },
          ),
          const SizedBox(height: 10),
          _buildClaimChooserCard(
            sheetCtx: sheetCtx,
            icon: Icons.pets_rounded,
            title: 'For my pet',
            subtitle:
                'Vet bills, medications, and treatment costs for your pets.',
            accent: const Color(0xFFA78BFA),
            accentDark: const Color(0xFF8B6EE8),
            onTap: () {
              Navigator.of(sheetCtx).pop();
              Future.delayed(const Duration(milliseconds: 120), () {
                if (!mounted) return;
                _openPetClaimRoute();
              });
            },
          ),
          const SizedBox(height: 8),
          TextButton(
            onPressed: () => Navigator.of(sheetCtx).pop(),
            child: Text(
              'Cancel',
              style: TextStyle(
                color: Colors.white.withOpacity(0.55),
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildClaimChooserCard({
    required BuildContext sheetCtx,
    required IconData icon,
    required String title,
    required String subtitle,
    required Color accent,
    required Color accentDark,
    required VoidCallback onTap,
  }) {
    return _Pressable(
      reduceMotion: _reduceMotion,
      pressedScale: 0.98,
      semanticsLabel: title,
      onTap: () {
        HapticFeedback.selectionClick();
        onTap();
      },
      child: Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.06),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: accent.withOpacity(0.35),
                width: 1,
              ),
            ),
            child: Row(
              children: [
                Container(
                  width: 46,
                  height: 46,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [accent, accentDark],
                    ),
                    borderRadius: BorderRadius.circular(12),
                    boxShadow: [
                      BoxShadow(
                        color: accent.withOpacity(0.35),
                        blurRadius: 10,
                        offset: const Offset(0, 4),
                      ),
                    ],
                  ),
                  child: Icon(icon, color: Colors.white, size: 22),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        title,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                          letterSpacing: -0.3,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        subtitle,
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.6),
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                          height: 1.35,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                Icon(
                  Icons.chevron_right_rounded,
                  color: Colors.white.withOpacity(0.4),
                  size: 22,
                ),
              ],
            ),
          ),
    );
  }

  void _openPetClaimRoute() {
    // Try the known route-name variants for the pet claim page.
    // ONE attempt per name — context.push queues asynchronously so
    // multiple attempts on the same name can create duplicate pages.
    const routes = [
      'petFileClaim',
      'PetFileClaim',
      'pet_file_claim',
      'petClaim',
      'PetClaim',
      'filePetClaim',
      'FilePetClaim',
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
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
        content: Text('Could not open Pet Claim flow.'),
        backgroundColor: Color(0xFFE53E3E),
        behavior: SnackBarBehavior.floating,
      ));
    }
  }

  Future<void> _loadAppointmentsAndRefills() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return;
    final now = DateTime.now();
    final fs = FirebaseFirestore.instance;

    try {
      final results = await Future.wait([
        fs
            .collection('requests')
            .where('userId', isEqualTo: user.uid)
            .where('status', whereIn: ['pending', 'confirmed']).get(),
        fs
            .collection('refills')
            .where('userId', isEqualTo: user.uid)
            .where('status', isEqualTo: 'pending')
            .get(),
      ]);

      int appointmentCount = 0;
      for (var doc in results[0].docs) {
        final data = doc.data();
        final appointmentDateStr = data['appointmentDate'] as String?;
        if (appointmentDateStr != null && appointmentDateStr.isNotEmpty) {
          try {
            final appointmentDate = DateTime.parse(appointmentDateStr);
            if (appointmentDate.isAfter(now)) {
              appointmentCount++;
            }
          } catch (e) {}
        }
      }
      final hasRefills = results[1].docs.isNotEmpty;

      if (!mounted) return;
      setState(() {
        upcomingAppointmentsCount = appointmentCount;
        hasRefillsDue = hasRefills;
      });
    } catch (e) {
      if (kDebugMode) print('Error loading appointments and refills: $e');
      // Degrade gracefully to zero/false rather than showing fake badges
      if (!mounted) return;
      setState(() {
        upcomingAppointmentsCount = 0;
        hasRefillsDue = false;
      });
    }
  }

  // =================================================================
  // SECTION 11: UTILITIES
  // =================================================================

  String calculateWindDirection(int degrees) {
    const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
    final index = ((degrees + 22.5) / 45).floor() % 8;
    return directions[index];
  }

  String convertWeatherCodeToEmoji(int weatherId) {
    if (weatherId >= 200 && weatherId < 300) return '⛈️';
    if (weatherId >= 300 && weatherId < 400) return '🌦️';
    if (weatherId >= 500 && weatherId < 600) return '🌧️';
    if (weatherId >= 600 && weatherId < 700) return '🌨️';
    if (weatherId >= 700 && weatherId < 800) return '🌫️';
    if (weatherId == 800) return '☀️';
    if (weatherId == 801) return '🌤️';
    if (weatherId == 802) return '⛅';
    if (weatherId == 803 || weatherId == 804) return '☁️';
    return '🌤️';
  }

  /// Confirmation toast in the app's own voice (navy surface, check icon).
  void _showToast(String message) {
    final messenger = ScaffoldMessenger.maybeOf(context);
    if (messenger == null) return;
    messenger.hideCurrentSnackBar();
    messenger.showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.check_circle_rounded,
                color: Colors.white, size: 18),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                message,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                  letterSpacing: -0.2,
                ),
              ),
            ),
          ],
        ),
        duration: const Duration(milliseconds: 1600),
        behavior: SnackBarBehavior.floating,
        backgroundColor: const Color(0xFF243352),
        elevation: 0,
        margin: const EdgeInsets.fromLTRB(16, 0, 16, 24),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: BorderSide(color: Colors.white.withOpacity(0.12)),
        ),
      ),
    );
  }

  String calculateGreeting() {
    final h = DateTime.now().hour;
    if (h < 12) return 'Good morning';
    if (h < 17) return 'Good afternoon';
    return 'Good evening';
  }

  double getModalMaxWidth() {
    switch (currentScreenType) {
      case ScreenType.expanded:
        return 650;
      case ScreenType.large:
        return 600;
      case ScreenType.medium:
        return 550;
      case ScreenType.compact:
      default:
        return 450;
    }
  }

  Widget wrapWithConstraints({required Widget child}) {
    if (currentScreenType == ScreenType.expanded || layoutSettings.hasHinge) {
      return child;
    }
    if (currentScreenType == ScreenType.large &&
        layoutSettings.contentMax < double.infinity) {
      return Center(
        child: ConstrainedBox(
          constraints: BoxConstraints(
            maxWidth: layoutSettings.contentMax,
          ),
          child: child,
        ),
      );
    }
    return child;
  }

  // =================================================================
  // SECTION 12: HEADER UI
  // =================================================================

  bool get _showsWeatherChip =>
      !weatherLoading &&
      (weatherData['temperature'] != null || _locationPromptAvailable);

  Widget renderCompactWeatherWidget() {
    if (!_showsWeatherChip) return const SizedBox.shrink();

    // Opt-in state: location never asked. Tapping triggers the system
    // prompt, in context, at the moment the user wants the feature.
    if (weatherData['temperature'] == null) {
      return _Pressable(
        reduceMotion: _reduceMotion,
        pressedScale: 0.95,
        semanticsLabel: 'Enable local weather and health tips',
        onTap: _requestLocationAndLoadWeather,
        child: _headerChip(
          accent: false,
          leading: Icon(Icons.wb_sunny_outlined,
              size: 18, color: Colors.white.withOpacity(0.85)),
          title: 'Weather',
          subtitle: 'Tap to enable',
        ),
      );
    }

    final hasTip = weatherHealthTip != null;
    final temp = weatherData['temperature'] ?? '--°';
    final desc = weatherData['description'] ?? '';

    return _Pressable(
      reduceMotion: _reduceMotion,
      pressedScale: 0.95,
      semanticsLabel:
          'Weather, $temp, $desc${hasTip ? '. Health tip available' : ''}',
      onTap: displayWeatherModal,
      child: _headerChip(
        accent: hasTip,
        subtitleAccent: hasTip,
        leading: Stack(
          clipBehavior: Clip.none,
          children: [
            Text(
              weatherData['icon'] ?? '☀️',
              style: const TextStyle(fontSize: 18),
            ),
            if (hasTip)
              Positioned(
                right: -3,
                top: -2,
                child: Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: joviCoral,
                    shape: BoxShape.circle,
                    border: Border.all(color: Colors.white, width: 1.5),
                  ),
                ),
              ),
          ],
        ),
        title: temp,
        subtitle: hasTip ? 'Health tip' : (weatherData['cityName'] ?? 'Location'),
      ),
    );
  }

  /// Painted-glass chip shared by the header controls. 44 pt minimum height
  /// so it is a comfortable touch target.
  Widget _headerChip({
    required bool accent,
    required Widget leading,
    required String title,
    required String subtitle,
    bool titleAccent = false,
    bool subtitleAccent = false,
  }) {
    return Container(
      constraints: const BoxConstraints(minHeight: 44),
      padding: const EdgeInsets.fromLTRB(10, 6, 12, 6),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.09),
        borderRadius: BorderRadius.circular(13),
        border: Border.all(
          color: accent
              ? joviCoral.withOpacity(0.45)
              : Colors.white.withOpacity(0.16),
          width: 1,
        ),
        boxShadow: accent
            ? [
                BoxShadow(
                  color: joviCoral.withOpacity(0.14),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ]
            : null,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          leading,
          const SizedBox(width: 7),
          Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  color: titleAccent ? joviCoral : Colors.white,
                  letterSpacing: -0.2,
                  height: 1.15,
                ),
              ),
              Text(
                subtitle,
                style: TextStyle(
                  fontSize: 10.5,
                  fontWeight:
                      subtitleAccent ? FontWeight.w600 : FontWeight.w500,
                  color: subtitleAccent
                      ? joviCoral
                      : Colors.white.withOpacity(0.6),
                  letterSpacing: 0.1,
                  height: 1.15,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget createUserAvatar({
    String? imagePath,
    String? imageUrl,
    double radius = 28,
  }) {
    String? finalImageUrl;

    if (userProfileImageUrl?.isNotEmpty == true) {
      finalImageUrl = userProfileImageUrl!;
    } else if (userProfileImagePath?.isNotEmpty == true) {
      finalImageUrl = userProfileImagePath!;
    } else if (imageUrl?.isNotEmpty == true) {
      finalImageUrl = imageUrl!;
    } else if (imagePath?.isNotEmpty == true) {
      finalImageUrl = imagePath!;
    } else {
      final authUser = FirebaseAuth.instance.currentUser;
      if (authUser?.photoURL?.isNotEmpty == true) {
        finalImageUrl = authUser!.photoURL!;
      }
    }

    return Container(
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            joviCoral.withOpacity(0.25),
            joviCoralLight.withOpacity(0.12),
          ],
        ),
        boxShadow: [
          BoxShadow(
            color: joviCoral.withOpacity(0.12),
            blurRadius: 20,
            offset: Offset(0, 8),
          ),
        ],
      ),
      padding: EdgeInsets.all(3),
      child: Container(
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          border: Border.all(color: Colors.white, width: 2),
        ),
        child: finalImageUrl != null
            ? ClipOval(
                child: CachedNetworkImage(
                  imageUrl: finalImageUrl,
                  key: ValueKey('profile_${finalImageUrl.hashCode}'),
                  width: radius * 2,
                  height: radius * 2,
                  fit: BoxFit.cover,
                  memCacheWidth:
                      (radius * 2 * MediaQuery.of(context).devicePixelRatio)
                          .round(),
                  memCacheHeight:
                      (radius * 2 * MediaQuery.of(context).devicePixelRatio)
                          .round(),
                  placeholder: (context, url) => Container(
                    width: radius * 2,
                    height: radius * 2,
                    decoration: BoxDecoration(
                      color: joviSoftStone,
                      shape: BoxShape.circle,
                    ),
                    child: Icon(Icons.person,
                        color: Colors.grey[400], size: radius * 0.8),
                  ),
                  errorWidget: (context, url, error) => Container(
                    width: radius * 2,
                    height: radius * 2,
                    decoration: BoxDecoration(
                      color: joviSoftStone,
                      shape: BoxShape.circle,
                    ),
                    child: Icon(Icons.person,
                        color: Colors.grey[400], size: radius * 0.8),
                  ),
                ),
              )
            : widget.photoUrl?.bytes != null
                ? ClipOval(
                    child: Image.memory(
                      widget.photoUrl!.bytes! as Uint8List,
                      width: radius * 2,
                      height: radius * 2,
                      fit: BoxFit.cover,
                    ),
                  )
                : CircleAvatar(
                    radius: radius,
                    backgroundColor: joviSoftStone,
                    child: Icon(Icons.person,
                        color: Colors.grey[400], size: radius * 0.8),
                  ),
      ),
    );
  }

  Widget renderLogo() {
    return Hero(
      tag: 'jovi_logo',
      child: CachedNetworkImage(
        imageUrl: joviLogoAssetUrl,
        height: 62,
        fit: BoxFit.contain,
        placeholder: (context, url) => Container(
          height: 62,
          width: 160,
          child: Center(
            child: CircularProgressIndicator(
              strokeWidth: 2.5,
              valueColor: AlwaysStoppedAnimation<Color>(joviCoral),
            ),
          ),
        ),
        errorWidget: (context, url, error) => Container(
          height: 62,
          alignment: Alignment.centerLeft,
          child: RichText(
            text: TextSpan(
              style: TextStyle(
                fontSize: 42,
                fontWeight: FontWeight.w800,
                letterSpacing: -1.5,
                height: 1.0,
              ),
              children: [
                TextSpan(text: 'jovi', style: TextStyle(color: Colors.white)),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget renderChatButton({required bool hasUnread}) {
    return _Pressable(
      reduceMotion: _reduceMotion,
      pressedScale: 0.95,
      semanticsLabel:
          hasUnread ? 'Messages, new reply from support' : 'Messages, support',
      onTap: () {
        HapticFeedback.lightImpact();
        context.push('/chatLanding');
      },
      child: _headerChip(
        accent: hasUnread,
        titleAccent: hasUnread,
        subtitleAccent: hasUnread,
        leading: Stack(
          clipBehavior: Clip.none,
          children: [
            Icon(
              hasUnread
                  ? Icons.chat_bubble_rounded
                  : Icons.chat_bubble_outline_rounded,
              color: hasUnread ? joviCoral : Colors.white,
              size: 18,
            ),
            if (hasUnread)
              Positioned(
                right: -3,
                top: -3,
                child: Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [joviCoral, joviCoralDark],
                    ),
                    shape: BoxShape.circle,
                    border: Border.all(color: Colors.white, width: 1.5),
                  ),
                ),
              ),
          ],
        ),
        title: 'Messages',
        subtitle: hasUnread ? 'New reply' : 'Support',
      ),
    );
  }

  // =================================================================
  // SECTION 13: ACTION NEEDED STRIP
  // =================================================================

  Widget renderActionNeededStrip() {
    if (!_actionItemsLoaded) return SizedBox.shrink();
    if (_actionItems.isEmpty) return SizedBox.shrink();

    final urgentCount =
        _actionItems.where((i) => i.priority == ActionPriority.urgent).length;

    return SlideTransition(
      position: contentSlideEffect,
      child: FadeTransition(
        opacity: mainFadeEffect,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Heading
            Padding(
              padding: EdgeInsets.only(bottom: 12),
              child: Row(
                children: [
                  Container(
                    width: 6,
                    height: 20,
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [joviCoral, joviCoralDark],
                      ),
                      borderRadius: BorderRadius.circular(3),
                    ),
                  ),
                  SizedBox(width: 10),
                  Text(
                    'Action Needed',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                      color: Colors.white,
                      letterSpacing: -0.3,
                    ),
                  ),
                  SizedBox(width: 10),
                  if (urgentCount > 0)
                    Container(
                      padding: EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: joviCoral,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text(
                        '$urgentCount urgent',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          color: Colors.white,
                          letterSpacing: 0.2,
                        ),
                      ),
                    ),
                ],
              ),
            ),
            // Horizontally scrollable cards
            SizedBox(
              height: 112,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                padding: EdgeInsets.symmetric(horizontal: 2),
                itemCount: _actionItems.length,
                separatorBuilder: (_, __) => SizedBox(width: 10),
                itemBuilder: (context, i) {
                  return _buildActionCard(_actionItems[i]);
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActionCard(ActionItem item) {
    return _Pressable(
      reduceMotion: _reduceMotion,
      pressedScale: 0.97,
      semanticsLabel: '${item.title}. ${item.subtitle}',
      semanticsHint: item.ctaLabel,
      onTap: () {
        HapticFeedback.mediumImpact();
        context.push(item.route);
      },
      child: Container(
              width: 260,
              padding: EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.08),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: item.accentColor.withOpacity(0.35),
                  width: 1.5,
                ),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.15),
                    blurRadius: 16,
                    offset: Offset(0, 6),
                  ),
                ],
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Icon chip
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: [item.accentColor, item.accentDark],
                      ),
                      borderRadius: BorderRadius.circular(12),
                      boxShadow: [
                        BoxShadow(
                          color: item.accentColor.withOpacity(0.35),
                          blurRadius: 8,
                          offset: Offset(0, 3),
                        ),
                      ],
                    ),
                    child: Icon(item.icon, color: Colors.white, size: 22),
                  ),
                  SizedBox(width: 12),
                  // Text
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          item.title,
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                            color: Colors.white,
                            letterSpacing: -0.1,
                            height: 1.2,
                          ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                        SizedBox(height: 3),
                        Text(
                          item.subtitle,
                          style: TextStyle(
                            fontSize: 11,
                            color: Colors.white.withOpacity(0.6),
                            fontWeight: FontWeight.w500,
                            height: 1.3,
                          ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                        SizedBox(height: 6),
                        // CTA chip
                        Container(
                          padding:
                              EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: item.accentColor.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                item.ctaLabel ?? 'View',
                                style: TextStyle(
                                  fontSize: 10.5,
                                  fontWeight: FontWeight.w700,
                                  color: item.accentColor,
                                  letterSpacing: 0.3,
                                ),
                              ),
                              SizedBox(width: 3),
                              Icon(
                                Icons.arrow_forward_rounded,
                                size: 10,
                                color: item.accentColor,
                              ),
                            ],
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

  // =================================================================
  // SECTION 14: FOR YOU INSIGHT CARD
  // =================================================================

  Widget renderForYouCard() {
    if (_insights.isEmpty) return SizedBox.shrink();
    final insight = _insights[_currentInsightIndex];

    return SlideTransition(
      position: contentSlideEffect,
      child: FadeTransition(
        opacity: mainFadeEffect,
        child: AnimatedSwitcher(
          duration: _reduceMotion
              ? Duration.zero
              : const Duration(milliseconds: 320),
          switchInCurve: _Motion.settle,
          switchOutCurve: Curves.easeInCubic,
          transitionBuilder: (child, anim) {
            if (_reduceMotion) {
              return FadeTransition(opacity: anim, child: child);
            }
            return FadeTransition(
              opacity: anim,
              child: SlideTransition(
                position: Tween<Offset>(
                  begin: const Offset(0.03, 0),
                  end: Offset.zero,
                ).animate(anim),
                child: child,
              ),
            );
          },
          child: Container(
            key: ValueKey(insight.id),
            padding: EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: joviNavyDark,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(
                color: insight.accent.withOpacity(0.4),
                width: 1.2,
              ),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.2),
                  blurRadius: 16,
                  offset: Offset(0, 6),
                ),
              ],
            ),
            child: Row(
              children: [
                Container(
                  width: 46,
                  height: 46,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [
                        insight.accent,
                        insight.accent.withOpacity(0.75),
                      ],
                    ),
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: insight.accent.withOpacity(0.3),
                        blurRadius: 10,
                        offset: Offset(0, 4),
                      ),
                    ],
                  ),
                  child: Icon(insight.icon, color: Colors.white, size: 22),
                ),
                SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'FOR YOU',
                        style: TextStyle(
                          fontSize: 10.5,
                          fontWeight: FontWeight.w700,
                          color: insight.accent,
                          letterSpacing: 1.2,
                        ),
                      ),
                      SizedBox(height: 3),
                      Text(
                        insight.headline,
                        style: TextStyle(
                          fontSize: 15.5,
                          fontWeight: FontWeight.w700,
                          color: Colors.white,
                          letterSpacing: -0.3,
                          height: 1.25,
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                      SizedBox(height: 3),
                      Text(
                        insight.body,
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.white.withOpacity(0.75),
                          fontWeight: FontWeight.w500,
                          height: 1.35,
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                      if (insight.ctaLabel != null &&
                          insight.ctaRoute != null) ...[
                        SizedBox(height: 8),
                        _Pressable(
                          reduceMotion: _reduceMotion,
                          pressedScale: 0.95,
                          semanticsLabel: insight.ctaLabel,
                          onTap: () {
                            HapticFeedback.lightImpact();
                            context.push(insight.ctaRoute!);
                          },
                          child: Container(
                            padding: EdgeInsets.symmetric(
                                horizontal: 12, vertical: 7),
                            decoration: BoxDecoration(
                              color: insight.accent,
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Text(
                                  insight.ctaLabel!,
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.w700,
                                    color: Colors.white,
                                    letterSpacing: 0.2,
                                  ),
                                ),
                                SizedBox(width: 4),
                                Icon(Icons.arrow_forward,
                                    size: 11, color: Colors.white),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                // Pagination dots — tap a dot to jump to that insight
                if (_insights.length > 1)
                  Padding(
                    padding: EdgeInsets.only(left: 8),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: List.generate(
                        _insights.length.clamp(1, 5),
                        (i) => GestureDetector(
                          behavior: HitTestBehavior.opaque,
                          onTap: () {
                            HapticFeedback.selectionClick();
                            setState(() => _currentInsightIndex = i);
                            _pauseInsightRotation();
                          },
                          child: Container(
                            margin: EdgeInsets.symmetric(vertical: 3),
                            padding: EdgeInsets.all(4), // larger tap target
                            child: Container(
                              width: i == _currentInsightIndex ? 7 : 5,
                              height: i == _currentInsightIndex ? 7 : 5,
                              decoration: BoxDecoration(
                                color: i == _currentInsightIndex
                                    ? insight.accent
                                    : insight.accent.withOpacity(0.25),
                                shape: BoxShape.circle,
                              ),
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

  // =================================================================
  // SECTION 15: RESPONSIBILITY CARD WITH HISTOGRAM + PACE LINE
  // =================================================================

  Widget renderDeductibleProgressCard() {
    final maxDeductible = annualDeductible ?? 1000;
    final used = deductibleUsed.clamp(0.0, maxDeductible.toDouble());
    final remaining = maxDeductible - used;
    final deductiblePct = maxDeductible > 0
        ? (used / maxDeductible.toDouble()).clamp(0.0, 1.0)
        : 0.0;

    // Painted glass, no BackdropFilter: only a flat gradient sits behind
    // this card, so the blur cost a saveLayer per scroll frame and blurred
    // nothing. RepaintBoundary isolates the animated progress bar.
    return RepaintBoundary(
        child: Container(
          padding: EdgeInsets.all(22),
          decoration: BoxDecoration(
            // Subtle coral-tinted gradient so this card reads as the "live" one
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                Colors.white.withOpacity(0.11),
                Colors.white.withOpacity(0.06),
              ],
            ),
            borderRadius: BorderRadius.circular(24),
            border: Border.all(
              color: joviCoral.withOpacity(0.22),
              width: 1.5,
            ),
            boxShadow: [
              // Primary depth shadow
              BoxShadow(
                color: Colors.black.withOpacity(0.28),
                blurRadius: 32,
                offset: Offset(0, 16),
              ),
              // Coral accent glow (subtle — signals this is the primary/active card)
              BoxShadow(
                color: joviCoral.withOpacity(0.08),
                blurRadius: 24,
                offset: Offset(0, 6),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header row
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Your Progress',
                        style: TextStyle(
                          fontSize: 19,
                          fontWeight: FontWeight.w700,
                          color: Colors.white,
                          letterSpacing: -0.3,
                        ),
                      ),
                      SizedBox(height: 3),
                      Text(
                        'Toward annual limit',
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.white.withOpacity(0.6),
                          fontWeight: FontWeight.w500,
                          letterSpacing: -0.1,
                        ),
                      ),
                    ],
                  ),
                  Container(
                    padding: EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: deductiblePct >= 1.0
                            ? [
                                joviMint.withOpacity(0.2),
                                joviMint.withOpacity(0.08)
                              ]
                            : [
                                joviCoral.withOpacity(0.15),
                                joviCoral.withOpacity(0.05)
                              ],
                      ),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(
                        color: deductiblePct >= 1.0
                            ? joviMint.withOpacity(0.4)
                            : joviCoral.withOpacity(0.35),
                      ),
                    ),
                    child: Text(
                      deductiblePct >= 1.0 ? 'Met' : 'Active',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color:
                            deductiblePct >= 1.0 ? joviMintDark : joviCoralDark,
                        letterSpacing: 0.3,
                      ),
                    ),
                  ),
                ],
              ),
              SizedBox(height: 20),

              // Used / Remaining split
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Your responsibility',
                          style: TextStyle(
                            fontSize: 12,
                            color: Colors.white.withOpacity(0.6),
                            fontWeight: FontWeight.w600,
                            letterSpacing: 0.2,
                          ),
                        ),
                        SizedBox(height: 4),
                        AnimatedBuilder(
                          animation: progressEffect,
                          builder: (context, child) {
                            final from = _previousDeductibleUsed;
                            final to = used;
                            final animatedValue =
                                from + (to - from) * progressEffect.value;
                            return ShaderMask(
                              shaderCallback: (bounds) => LinearGradient(
                                begin: Alignment.topLeft,
                                end: Alignment.bottomRight,
                                colors: [joviCoral, joviCoralLight],
                              ).createShader(bounds),
                              child: Text(
                                '\$${animatedValue.toStringAsFixed(0)}',
                                style: TextStyle(
                                  fontSize: 26,
                                  fontWeight: FontWeight.w800,
                                  color: Colors.white,
                                  letterSpacing: -0.5,
                                ),
                              ),
                            );
                          },
                        ),
                        SizedBox(height: 2),
                        Text(
                          'Used this year',
                          style: TextStyle(
                            fontSize: 10.5,
                            color: Colors.white.withOpacity(0.4),
                            fontWeight: FontWeight.w500,
                            letterSpacing: 0.1,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text(
                          'Plan covers after',
                          style: TextStyle(
                            fontSize: 12,
                            color: Colors.white.withOpacity(0.6),
                            fontWeight: FontWeight.w600,
                            letterSpacing: 0.2,
                          ),
                        ),
                        SizedBox(height: 4),
                        Text(
                          '\$${remaining.toStringAsFixed(0)}',
                          style: TextStyle(
                            fontSize: 26,
                            fontWeight: FontWeight.w800,
                            color: Colors.white,
                            letterSpacing: -0.5,
                          ),
                        ),
                        SizedBox(height: 2),
                        Text(
                          'Remaining',
                          style: TextStyle(
                            fontSize: 10.5,
                            color: Colors.white.withOpacity(0.4),
                            fontWeight: FontWeight.w500,
                            letterSpacing: 0.1,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              SizedBox(height: 18),

              // Progress bar
              Stack(
                children: [
                  Container(
                    height: 10,
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(6),
                    ),
                  ),
                  AnimatedBuilder(
                    animation: progressEffect,
                    builder: (context, child) {
                      return FractionallySizedBox(
                        widthFactor: deductiblePct * progressEffect.value,
                        child: Container(
                          height: 10,
                          decoration: BoxDecoration(
                            gradient: LinearGradient(
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                              colors: [joviCoral, joviCoralLight],
                            ),
                            borderRadius: BorderRadius.circular(6),
                            boxShadow: [
                              BoxShadow(
                                color: joviCoral.withOpacity(0.35),
                                blurRadius: 8,
                                offset: Offset(0, 2),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ],
              ),
              SizedBox(height: 8),
              Text(
                '${(deductiblePct * 100).toStringAsFixed(0)}% of \$${maxDeductible.toStringAsFixed(0)} used',
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.white.withOpacity(0.6),
                  fontWeight: FontWeight.w500,
                ),
              ),

              // Divider
              SizedBox(height: 18),
              Container(
                height: 1,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      Colors.transparent,
                      joviCoral.withOpacity(0.15),
                      Colors.transparent,
                    ],
                  ),
                ),
              ),
              SizedBox(height: 10),

              // Collapsible 12-Month Trend section
              _Pressable(
                reduceMotion: _reduceMotion,
                pressedScale: 0.985,
                semanticsLabel: _trendExpanded
                    ? 'Hide 12-month trend'
                    : 'Show 12-month trend',
                onTap: () {
                  HapticFeedback.lightImpact();
                  setState(() => _trendExpanded = !_trendExpanded);
                },
                child: Padding(
                    padding: EdgeInsets.symmetric(vertical: 6),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Row(
                          children: [
                            Text(
                              '12-Month Trend',
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w700,
                                color: Colors.white,
                                letterSpacing: -0.1,
                              ),
                            ),
                            SizedBox(width: 6),
                            AnimatedRotation(
                              turns: _trendExpanded ? 0.5 : 0.0,
                              duration: _reduceMotion
                                  ? Duration.zero
                                  : const Duration(milliseconds: 220),
                              curve: Curves.easeOutCubic,
                              child: Icon(
                                Icons.expand_more_rounded,
                                size: 18,
                                color: Colors.white.withOpacity(0.45),
                              ),
                            ),
                          ],
                        ),
                        if (_trendExpanded)
                          // Legend (only visible when expanded)
                          Row(
                            children: [
                              Container(
                                width: 18,
                                height: 2.5,
                                decoration: BoxDecoration(
                                  color: Colors.white.withOpacity(0.35),
                                  borderRadius: BorderRadius.circular(1),
                                ),
                              ),
                              SizedBox(width: 4),
                              Text(
                                'Pace',
                                style: TextStyle(
                                  fontSize: 10.5,
                                  color: Colors.white.withOpacity(0.6),
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              SizedBox(width: 10),
                              Container(
                                width: 8,
                                height: 8,
                                decoration: BoxDecoration(
                                  color: joviCoral,
                                  borderRadius: BorderRadius.circular(2),
                                ),
                              ),
                              SizedBox(width: 4),
                              Text(
                                'Actual',
                                style: TextStyle(
                                  fontSize: 10.5,
                                  color: Colors.white.withOpacity(0.6),
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ],
                          )
                        else
                          Text(
                            'Show',
                            style: TextStyle(
                              fontSize: 11,
                              color: Colors.white.withOpacity(0.45),
                              fontWeight: FontWeight.w600,
                              letterSpacing: 0.2,
                            ),
                          ),
                      ],
                    ),
                  ),
              ),

              // The histogram — animated collapse/expand
              AnimatedSize(
                duration: _reduceMotion
                    ? Duration.zero
                    : const Duration(milliseconds: 260),
                curve: Curves.easeOutCubic,
                alignment: Alignment.topCenter,
                child: _trendExpanded
                    ? Padding(
                        padding: EdgeInsets.only(top: 12),
                        child: _buildSpendHistogram(),
                      )
                    : SizedBox(width: double.infinity, height: 0),
              ),
            ],
          ),
        ),
    );
  }

  Widget _buildSpendHistogram() {
    // If we have no real spend data, show a graceful empty state rather than
    // padding 12 months of zero bars (which looks broken).
    if (_monthlySpend.isEmpty) {
      return Container(
        height: 96,
        alignment: Alignment.center,
        padding: EdgeInsets.symmetric(horizontal: 20),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.03),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.white.withOpacity(0.06)),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.timeline,
                size: 18, color: Colors.white.withOpacity(0.35)),
            SizedBox(width: 8),
            Flexible(
              child: Text(
                'Your 12-month trend will appear as you use your plan',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.white.withOpacity(0.5),
                  fontWeight: FontWeight.w500,
                  height: 1.3,
                ),
              ),
            ),
          ],
        ),
      );
    }

    // Ensure 12 buckets — pad with zeros if needed
    List<MonthlySpend> bars = List.of(_monthlySpend);
    while (bars.length < 12) {
      final now = DateTime.now();
      final monthsAgo = 11 - bars.length;
      final monthDate = DateTime(now.year, now.month - monthsAgo, 1);
      bars.add(MonthlySpend(
        monthsAgo: monthsAgo,
        amount: 0,
        monthLabel: DateFormat('MMM').format(monthDate),
      ));
    }
    if (bars.length > 12) {
      bars = bars.sublist(bars.length - 12);
    }

    final maxAmount =
        bars.map((b) => b.amount).fold<double>(0, (a, b) => b > a ? b : a);
    // If pace target is higher than max, use it for scale
    final maxScale = [maxAmount, _paceTarget * 1.2, 1.0]
        .fold<double>(0, (a, b) => b > a ? b : a);

    return AnimatedBuilder(
      animation: progressEffect,
      builder: (context, child) {
        return SizedBox(
          height: 96,
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              // Y-axis sentinel (empty — bars provide their own scale)
              Expanded(
                child: LayoutBuilder(
                  builder: (ctx, constraints) {
                    final chartW = constraints.maxWidth;
                    final chartH = 76.0;
                    // Pace line Y position (fraction of chart height)
                    final paceY = maxScale > 0
                        ? (1 - (_paceTarget / maxScale).clamp(0.0, 1.0)) *
                            chartH
                        : chartH;
                    return Stack(
                      children: [
                        // Bars row
                        Positioned.fill(
                          bottom: 20, // reserve for labels
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.end,
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: bars.map((b) {
                              final rawH = maxScale > 0
                                  ? (b.amount / maxScale) * chartH
                                  : 0.0;
                              // Apply progress animation
                              final animH = rawH * progressEffect.value;
                              final barColor = b.amount >= _paceTarget
                                  ? joviCoral
                                  : joviCoralLight;
                              return Expanded(
                                child: Padding(
                                  padding:
                                      EdgeInsets.symmetric(horizontal: 1.5),
                                  child: Column(
                                    mainAxisAlignment: MainAxisAlignment.end,
                                    children: [
                                      Container(
                                        height: animH.clamp(0.0, chartH),
                                        decoration: BoxDecoration(
                                          gradient: LinearGradient(
                                            begin: Alignment.topCenter,
                                            end: Alignment.bottomCenter,
                                            colors: [
                                              barColor.withOpacity(0.95),
                                              barColor.withOpacity(0.7),
                                            ],
                                          ),
                                          borderRadius: BorderRadius.only(
                                            topLeft: Radius.circular(3),
                                            topRight: Radius.circular(3),
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              );
                            }).toList(),
                          ),
                        ),
                        // Pace line (dashed)
                        Positioned(
                          left: 0,
                          right: 0,
                          top: paceY,
                          child: CustomPaint(
                            size: Size(chartW, 2),
                            painter: _DashedLinePainter(
                              // Navy on navy was invisible.
                              color: Colors.white.withOpacity(0.45),
                            ),
                          ),
                        ),
                        // Month labels row — 3-letter every other bar
                        // for readability without crowding.
                        Positioned(
                          left: 0,
                          right: 0,
                          bottom: 0,
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: List.generate(bars.length, (idx) {
                              final b = bars[idx];
                              // Show label on every other bar starting from
                              // index 1 — gives "Jun, Aug, Oct, Dec, Feb, Apr"
                              // pattern which matches reading cadence better.
                              final showLabel = idx.isOdd;
                              return Expanded(
                                child: Text(
                                  showLabel && b.monthLabel.isNotEmpty
                                      ? b.monthLabel
                                      : '',
                                  textAlign: TextAlign.center,
                                  style: TextStyle(
                                    fontSize: 10.5,
                                    color: Colors.white.withOpacity(0.55),
                                    fontWeight: FontWeight.w600,
                                    letterSpacing: 0.2,
                                  ),
                                ),
                              );
                            }),
                          ),
                        ),
                      ],
                    );
                  },
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  // =================================================================
  // SECTION 16: PLAN DETAILS CARD
  // =================================================================

  Widget renderPlanDetailsCard() {
    String? displayMemberId;
    if (membershipId != null) {
      final id = membershipId!;
      displayMemberId = id.length > 5 ? id.substring(id.length - 5) : id;
    }

    return RepaintBoundary(
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            // Flatter than the Progress card — reference info should feel quieter
            color: Colors.white.withOpacity(0.05),
            border: Border.all(
              color: Colors.white.withOpacity(0.1),
              width: 1,
            ),
            borderRadius: BorderRadius.circular(20),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.14),
                blurRadius: 16,
                offset: Offset(0, 8),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Text('Plan Details',
                          style: TextStyle(
                              fontWeight: FontWeight.w700,
                              fontSize: 16,
                              color: Colors.white.withOpacity(0.92),
                              letterSpacing: -0.2)),
                      // Collapse chevron — only shown in mobile layout
                      if (!layoutSettings.useTwoColumnLayout) ...[
                        SizedBox(width: 8),
                        _Pressable(
                          reduceMotion: _reduceMotion,
                          pressedScale: 0.9,
                          semanticsLabel: 'Collapse plan details',
                          onTap: () {
                            HapticFeedback.lightImpact();
                            setState(() => _planDetailsExpanded = false);
                          },
                          child: Container(
                            width: 36,
                            height: 36,
                            alignment: Alignment.center,
                            child: Icon(
                              Icons.expand_less_rounded,
                              size: 20,
                              color: Colors.white.withOpacity(0.45),
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                  _Pressable(
                    reduceMotion: _reduceMotion,
                    pressedScale: 0.95,
                    semanticsLabel: 'View all plan details',
                    onTap: () {
                      HapticFeedback.lightImpact();
                      context.push('/plan');
                    },
                    child: Container(
                      padding:
                          EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      decoration: BoxDecoration(
                        color: joviCoral.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        'View All',
                        style: TextStyle(
                          fontSize: 14,
                          color: joviCoral,
                          fontWeight: FontWeight.w700,
                          letterSpacing: -0.2,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 18),
              createPlanInfoRow(
                  'Plan Type', insurancePlanType ?? 'Standard Plan'),
              createPlanInfoRow(
                'Member ID',
                displayMemberId ?? 'JH123',
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      displayMemberId ?? 'JH123',
                      style: TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                        fontFeatures: const [ui_dart.FontFeature.tabularFigures()],
                        color: Colors.white,
                        letterSpacing: 0.3,
                      ),
                    ),
                    SizedBox(width: 12),
                    _Pressable(
                      reduceMotion: _reduceMotion,
                      pressedScale: 0.9,
                      semanticsLabel: 'Copy member ID',
                      onTap: () {
                        Clipboard.setData(
                            ClipboardData(text: membershipId ?? 'JH123'));
                        // Haptic and toast on the same frame.
                        HapticFeedback.mediumImpact();
                        _showToast('Member ID copied');
                      },
                      child: Container(
                        padding: EdgeInsets.all(9),
                        decoration: BoxDecoration(
                          color: joviCoral.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Icon(Icons.copy, size: 18, color: joviCoral),
                      ),
                    ),
                  ],
                ),
              ),
              if (policyRenewalDate != null)
                createPlanInfoRow(
                  'Renewal Date',
                  DateFormat('MMM d, yyyy').format(policyRenewalDate!),
                ),
              createPlanInfoRow(
                'Add-on Plans',
                null,
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (includesDental == true || includesVision == true) ...[
                      if (includesDental == true)
                        Container(
                          margin: EdgeInsets.only(right: 8),
                          padding: const EdgeInsets.symmetric(
                              horizontal: 12, vertical: 6),
                          decoration: BoxDecoration(
                            gradient: LinearGradient(
                              colors: [joviMint, joviMintDark],
                            ),
                            borderRadius: BorderRadius.circular(16),
                            boxShadow: [
                              BoxShadow(
                                color: joviMint.withOpacity(0.3),
                                blurRadius: 4,
                                offset: const Offset(0, 2),
                              ),
                            ],
                          ),
                          child: const Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.check_circle,
                                  size: 16, color: Colors.white),
                              SizedBox(width: 4),
                              Text(
                                'Dental',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 12,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ],
                          ),
                        ),
                      if (includesVision == true)
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 12, vertical: 6),
                          decoration: BoxDecoration(
                            gradient: LinearGradient(
                              colors: [joviMint, joviMintDark],
                            ),
                            borderRadius: BorderRadius.circular(16),
                            boxShadow: [
                              BoxShadow(
                                color: joviMint.withOpacity(0.3),
                                blurRadius: 4,
                                offset: const Offset(0, 2),
                              ),
                            ],
                          ),
                          child: const Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.check_circle,
                                  size: 16, color: Colors.white),
                              SizedBox(width: 4),
                              Text(
                                'Vision',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 12,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ],
                          ),
                        ),
                    ] else ...[
                      _Pressable(
                        reduceMotion: _reduceMotion,
                        pressedScale: 0.95,
                        semanticsLabel: 'Add a dental or vision plan',
                        onTap: () {
                          HapticFeedback.lightImpact();
                          context.push('/updateProfile');
                        },
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 12, vertical: 6),
                          decoration: BoxDecoration(
                            gradient: LinearGradient(
                              colors: [joviCoral, joviCoralLight],
                            ),
                            borderRadius: BorderRadius.circular(16),
                            boxShadow: [
                              BoxShadow(
                                color: joviCoral.withOpacity(0.3),
                                blurRadius: 8,
                                offset: const Offset(0, 2),
                              ),
                            ],
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.add_circle,
                                  size: 16, color: Colors.white),
                              SizedBox(width: 4),
                              Text(
                                'Add a Plan',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 12,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              renderRenewalWidget(),
            ],
          ),
        ),
    );
  }

  Widget createPlanInfoRow(String label, String? value, {Widget? trailing}) =>
      Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label,
                style: TextStyle(
                  fontSize: 14,
                  color: Colors.white.withOpacity(0.6),
                  fontWeight: FontWeight.w500,
                  letterSpacing: -0.1,
                )),
            trailing ??
                Text(value ?? '-',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      color: Colors.white,
                      letterSpacing: -0.2,
                    )),
          ],
        ),
      );

  Widget renderRenewalWidget() {
    if (policyRenewalDate == null) return SizedBox.shrink();

    final now = DateTime.now();
    final daysUntilRenewal = policyRenewalDate!.difference(now).inDays;

    Color statusColor;
    Color bgColor;
    String statusText;
    IconData statusIcon;

    // All tints are on the navy card, so use the bright brand tones for
    // text/icons and a translucent wash of the same hue behind them.
    if (daysUntilRenewal < 0) {
      statusColor = const Color(0xFFFF8A80);
      bgColor = joviErrorRed.withOpacity(0.14);
      statusText = 'Expired ${(-daysUntilRenewal)} days ago';
      statusIcon = Icons.error_outline_rounded;
    } else if (daysUntilRenewal == 0) {
      statusColor = const Color(0xFFFF8A80);
      bgColor = joviErrorRed.withOpacity(0.14);
      statusText = 'Expires today';
      statusIcon = Icons.warning_amber_rounded;
    } else if (daysUntilRenewal <= 7) {
      statusColor = joviCoral;
      bgColor = joviCoral.withOpacity(0.12);
      statusText = 'Renews in $daysUntilRenewal days';
      statusIcon = Icons.schedule_rounded;
    } else if (daysUntilRenewal <= 30) {
      statusColor = joviGold;
      bgColor = joviGold.withOpacity(0.12);
      statusText = 'Renews in $daysUntilRenewal days';
      statusIcon = Icons.schedule_rounded;
    } else {
      statusColor = joviMint;
      bgColor = joviMint.withOpacity(0.10);
      statusText = 'Active — Renews in $daysUntilRenewal days';
      statusIcon = Icons.check_circle_outline;
    }

    return Container(
      margin: EdgeInsets.only(top: 12),
      padding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: statusColor.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          Icon(statusIcon, size: 18, color: statusColor),
          SizedBox(width: 8),
          Expanded(
            child: Text(
              statusText,
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: statusColor,
                letterSpacing: -0.1,
              ),
            ),
          ),
          if (daysUntilRenewal <= 30)
            _Pressable(
              reduceMotion: _reduceMotion,
              pressedScale: 0.95,
              semanticsLabel: 'Renew now',
              onTap: () {
                HapticFeedback.lightImpact();
                context.push('/quote');
              },
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: statusColor,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Text(
                  'Renew Now',
                  style: TextStyle(
                    fontSize: 12,
                    color: joviNavyDark,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.1,
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget renderCardsSection() {
    if (layoutSettings.useTwoColumnLayout) {
      // On tablet/desktop, there's space for both cards side-by-side at full weight
      return Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: SlideTransition(
              position: contentSlideEffect,
              child: FadeTransition(
                opacity: mainFadeEffect,
                child: renderDeductibleProgressCard(),
              ),
            ),
          ),
          SizedBox(width: 20),
          Expanded(
            child: SlideTransition(
              position: contentSlideEffect,
              child: FadeTransition(
                opacity: mainFadeEffect,
                child: renderPlanDetailsCard(),
              ),
            ),
          ),
        ],
      );
    } else {
      // On compact screens, Progress is the hero. Plan Details collapses
      // to a summary line that expands on tap.
      return Column(
        children: [
          SlideTransition(
            position: contentSlideEffect,
            child: FadeTransition(
              opacity: mainFadeEffect,
              child: renderDeductibleProgressCard(),
            ),
          ),
          const SizedBox(height: 14),
          SlideTransition(
            position: contentSlideEffect,
            child: FadeTransition(
              opacity: mainFadeEffect,
              child: _planDetailsExpanded
                  ? renderPlanDetailsCard()
                  : _buildPlanDetailsCollapsedRow(),
            ),
          ),
        ],
      );
    }
  }

  // Collapsed summary of plan details. Tap to expand to full card.
  Widget _buildPlanDetailsCollapsedRow() {
    String? shortMemberId;
    if (membershipId != null) {
      final id = membershipId!;
      shortMemberId = id.length > 5 ? id.substring(id.length - 5) : id;
    }

    final planLabel = insurancePlanType ?? 'Standard Plan';
    final hasAddOns = (includesDental == true) || (includesVision == true);

    return _Pressable(
      reduceMotion: _reduceMotion,
      pressedScale: 0.98,
      semanticsLabel: 'Plan details, $planLabel',
      semanticsHint: 'Expands',
      onTap: () {
        HapticFeedback.lightImpact();
        setState(() => _planDetailsExpanded = true);
      },
      child: Container(
              padding: EdgeInsets.symmetric(horizontal: 18, vertical: 14),
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
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      color: joviCoral.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(
                        color: joviCoral.withOpacity(0.2),
                        width: 0.8,
                      ),
                    ),
                    child:
                        Icon(Icons.badge_outlined, color: joviCoral, size: 18),
                  ),
                  SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Plan Details',
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w700,
                            color: Colors.white,
                            letterSpacing: -0.2,
                          ),
                        ),
                        SizedBox(height: 2),
                        Row(
                          children: [
                            Flexible(
                              child: Text(
                                planLabel,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(
                                  fontSize: 11,
                                  color: Colors.white.withOpacity(0.6),
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ),
                            if (shortMemberId != null) ...[
                              Text(
                                '  •  ',
                                style: TextStyle(
                                  fontSize: 11,
                                  color: Colors.white.withOpacity(0.3),
                                ),
                              ),
                              Text(
                                'ID $shortMemberId',
                                style: TextStyle(
                                  fontSize: 11,
                                  color: Colors.white.withOpacity(0.6),
                                  fontFeatures: const [ui_dart.FontFeature.tabularFigures()],
                                  fontWeight: FontWeight.w600,
                                  letterSpacing: 0.2,
                                ),
                              ),
                            ],
                          ],
                        ),
                      ],
                    ),
                  ),
                  if (hasAddOns)
                    Container(
                      margin: EdgeInsets.only(right: 8),
                      padding: EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                      decoration: BoxDecoration(
                        color: joviMint.withOpacity(0.18),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        (includesDental == true && includesVision == true)
                            ? 'D+V'
                            : (includesDental == true ? 'D' : 'V'),
                        style: TextStyle(
                          color: joviMintDark,
                          fontSize: 10.5,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ),
                  Icon(
                    Icons.expand_more_rounded,
                    color: Colors.white.withOpacity(0.5),
                    size: 22,
                  ),
                ],
              ),
            ),
    );
  }

  // =================================================================
  // SECTION 17: QUICK ACTIONS (DYNAMIC ORDERING)
  // =================================================================

  Widget createActionTile(
    IconData icon,
    String label,
    VoidCallback onPressed,
    Color primaryColor,
    Color darkColor,
    bool isAlwaysActive, {
    int? badgeCount,
    bool showAlert = false,
    bool emphasized = false,
  }) {
    final semantics = StringBuffer(label);
    if (badgeCount != null && badgeCount > 0) {
      semantics.write(', $badgeCount upcoming');
    }
    if (showAlert) semantics.write(', needs attention');

    // r1 scaled the tile with Matrix4.scale (no transformAlignment, so it
    // grew from the top-left) and released it on a 130 ms timer after the
    // tap. _Pressable scales from centre on pointer-down and releases on
    // pointer-up. The permanent 1.02 "emphasis" scale is replaced by the
    // coral border, which reads as emphasis without misaligning the row.
    return Expanded(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 4),
        child: _Pressable(
          reduceMotion: _reduceMotion,
          pressedScale: 0.95,
          semanticsLabel: semantics.toString(),
          onTap: () {
            HapticFeedback.mediumImpact();
            onPressed();
          },
          child: Container(
                  height: layoutSettings.actionItemHeight,
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(emphasized ? 0.10 : 0.08),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(
                      color: emphasized
                          ? joviCoral.withOpacity(0.5)
                          : Colors.white.withOpacity(0.16),
                      width: emphasized ? 1.5 : 1,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.12),
                        blurRadius: 16,
                        offset: const Offset(0, 6),
                      ),
                    ],
                  ),
                  child: Stack(
                    clipBehavior: Clip.none,
                    children: [
                      Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(
                              padding: EdgeInsets.all(11),
                              decoration: BoxDecoration(
                                color: joviCoral.withOpacity(0.14),
                                borderRadius: BorderRadius.circular(12),
                                border: Border.all(
                                  color: joviCoral.withOpacity(0.28),
                                  width: 1,
                                ),
                              ),
                              child: Icon(
                                icon,
                                color: joviCoral,
                                size: layoutSettings.actionIconDimension,
                              ),
                            ),
                            SizedBox(height: 8),
                            Text(
                              label,
                              textAlign: TextAlign.center,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                fontSize: layoutSettings.actionTextSize,
                                color: Colors.white.withOpacity(0.92),
                                fontWeight: FontWeight.w700,
                                height: 1.15,
                                letterSpacing: -0.1,
                              ),
                            ),
                          ],
                        ),
                      ),
                      if (badgeCount != null && badgeCount > 0)
                        Positioned(
                          top: 8,
                          right: 8,
                          child: Container(
                            padding: EdgeInsets.all(6),
                            decoration: BoxDecoration(
                              gradient: LinearGradient(
                                colors: [joviGold, joviGoldDark],
                                begin: Alignment.topLeft,
                                end: Alignment.bottomRight,
                              ),
                              shape: BoxShape.circle,
                              border: Border.all(color: Colors.white, width: 2),
                              boxShadow: [
                                BoxShadow(
                                  color: joviNavy.withOpacity(0.3),
                                  blurRadius: 10,
                                  offset: Offset(0, 3),
                                ),
                              ],
                            ),
                            constraints:
                                BoxConstraints(minWidth: 24, minHeight: 24),
                            child: Center(
                              child: Text(
                                badgeCount > 9 ? '9+' : badgeCount.toString(),
                                style: TextStyle(
                                  color: joviNavy,
                                  fontSize: 12,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                          ),
                        ),
                      if (showAlert)
                        Positioned(
                          top: 8,
                          right: 8,
                          child: Container(
                            width: 18,
                            height: 18,
                            decoration: BoxDecoration(
                              gradient: LinearGradient(
                                colors: [joviMint, joviMintDark],
                              ),
                              shape: BoxShape.circle,
                              border: Border.all(color: Colors.white, width: 2),
                              boxShadow: [
                                BoxShadow(
                                  color: joviMint.withOpacity(0.6),
                                  blurRadius: 10,
                                  spreadRadius: 1,
                                ),
                              ],
                            ),
                            child: Center(
                              child: Icon(Icons.priority_high,
                                  size: 12, color: Colors.white),
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

  Widget renderQuickActionsGrid() {
    // Dynamic ordering: tiles with active state (refill alert, appointments)
    // float to the front. Emphasis styling on the most-relevant tile.
    final baseConfigs = [
      {
        'id': 'claim',
        'icon': Icons.upload_file,
        'label': 'File a Claim',
        'route': '/fileclaim',
        'primaryColor': joviCoral,
        'darkColor': joviCoralDark,
        'priority': 4, // default priority; lower = earlier
      },
      {
        'id': 'care',
        'icon': Icons.medical_services,
        'label': 'Request Care',
        'route': '/requests',
        'primaryColor': joviCoralLight,
        'darkColor': joviCoral,
        'priority': 3,
      },
      {
        'id': 'help',
        'icon': Icons.help_outline,
        'label': 'Help Center',
        'route': '/chatLanding',
        'primaryColor': joviCoral,
        'darkColor': joviCoralDark,
        'priority': 6,
      },
      {
        'id': 'appts',
        'icon': Icons.calendar_today,
        'label': 'Appointments',
        'route': '/appt',
        'primaryColor': joviCoralLight,
        'darkColor': joviCoral,
        'priority': upcomingAppointmentsCount > 0 ? 0 : 5,
        'badgeCount': upcomingAppointmentsCount,
      },
      {
        'id': 'id',
        'icon': Icons.credit_card,
        'label': 'ID Card',
        'route': '/digitalMembershipCard',
        'primaryColor': joviCoral,
        'darkColor': joviCoralDark,
        'priority': 7,
      },
      {
        'id': 'refill',
        'icon': Icons.medication,
        'label': 'RX Refill',
        'route': '/scriptRefill',
        'primaryColor': joviCoralLight,
        'darkColor': joviCoral,
        'priority': hasRefillsDue ? 1 : 8,
        'showAlert': hasRefillsDue,
      },
    ];

    // Sort by priority ascending (most relevant first)
    final configs = List<Map<String, dynamic>>.from(baseConfigs);
    configs
        .sort((a, b) => (a['priority'] as int).compareTo(b['priority'] as int));

    // Emphasis goes on the single most important tile if it has state
    final hasEmphasized = (configs.first['priority'] as int) < 3;

    return Column(
      children: [
        Row(
          children: configs.take(3).toList().asMap().entries.map((entry) {
            final config = entry.value;
            final emphasized = hasEmphasized && entry.key == 0;
            final route = config['route'] as String;
            final id = config['id'] as String;
            return createActionTile(
              config['icon'] as IconData,
              config['label'] as String,
              () {
                // Claim tile: if the user has pets, show a chooser sheet
                // (Medical vs Pet). Otherwise go straight to human flow.
                if (id == 'claim') {
                  if (_hasPets) {
                    _showClaimTypeChooser();
                  } else {
                    context.push(route);
                  }
                  return;
                }
                // Appointments tile routes to Care Records (superset
                // widget) rather than the legacy /appt route. See
                // _navigateToCareRecords for the fallback chain.
                if (route == '/appt' || route == 'careRecords') {
                  _navigateToCareRecords();
                } else {
                  context.push(route);
                }
              },
              config['primaryColor'] as Color,
              config['darkColor'] as Color,
              true,
              badgeCount: config['badgeCount'] as int?,
              showAlert: config['showAlert'] as bool? ?? false,
              emphasized: emphasized,
            );
          }).toList(),
        ),
        SizedBox(height: 12),
        Row(
          children: configs.skip(3).map((config) {
            final route = config['route'] as String;
            final id = config['id'] as String;
            return createActionTile(
              config['icon'] as IconData,
              config['label'] as String,
              () {
                // Claim tile: chooser if the user has pets, else human flow.
                if (id == 'claim') {
                  if (_hasPets) {
                    _showClaimTypeChooser();
                  } else {
                    context.push(route);
                  }
                  return;
                }
                if (route == '/appt' || route == 'careRecords') {
                  _navigateToCareRecords();
                } else {
                  context.push(route);
                }
              },
              config['primaryColor'] as Color,
              config['darkColor'] as Color,
              true,
              badgeCount: config['badgeCount'] as int?,
              showAlert: config['showAlert'] as bool? ?? false,
              emphasized: false,
            );
          }).toList(),
        ),
      ],
    );
  }

  // =================================================================
  // SECTION 18: FAB (COLLAPSIBLE)
  // =================================================================

  Widget renderFloatingButton() {
    return FadeTransition(
      opacity: buttonRevealAnimator,
      child: ScaleTransition(
        scale: buttonRevealEffect,
        child: AnimatedBuilder(
          animation: _fabCollapseEffect,
          builder: (context, _) {
            // 1.0 = expanded pill with label, 0.0 = icon only. The width is
            // driven directly by the collapse animation (no nested
            // AnimatedContainer chasing it), so a scroll reversal mid-collapse
            // simply retargets from the current value.
            final t = _fabCollapseEffect.value.clamp(0.0, 1.0);

            return _Pressable(
              reduceMotion: _reduceMotion,
              pressedScale: 0.94,
              semanticsLabel: 'Ask Jovi',
              semanticsHint: 'Opens the assistant',
              onTap: () {
                HapticFeedback.mediumImpact();
                context.push('/chatBot');
              },
              child: Container(
                height: 56,
                width: 56 + 88 * t,
                padding: const EdgeInsets.symmetric(horizontal: 16),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [joviCoral, joviCoralDark],
                  ),
                  borderRadius: BorderRadius.circular(28),
                  boxShadow: [
                    BoxShadow(
                      color: joviCoral.withOpacity(0.4),
                      blurRadius: 20,
                      offset: const Offset(0, 8),
                    ),
                  ],
                ),
                child: Row(
                  children: [
                    const Icon(
                      Icons.chat_bubble_outline_rounded,
                      size: 24,
                      color: Colors.white,
                    ),
                    // Label keeps its natural width and is clipped as the
                    // pill narrows, so the text never squashes.
                    Expanded(
                      child: ClipRect(
                        child: OverflowBox(
                          alignment: Alignment.centerLeft,
                          minWidth: 0,
                          maxWidth: double.infinity,
                          child: Opacity(
                            opacity: t,
                            child: const Padding(
                              padding: EdgeInsets.only(left: 8),
                              child: Text(
                                'Ask Jovi',
                                maxLines: 1,
                                softWrap: false,
                                overflow: TextOverflow.clip,
                                style: TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.w700,
                                  color: Colors.white,
                                  letterSpacing: -0.2,
                                ),
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
          },
        ),
      ),
    );
  }

  // =================================================================
  // SECTION 19: WEATHER MODAL (NAVY + GLASS)
  // =================================================================

  void displayWeatherModal() {
    HapticFeedback.lightImpact();
    showDialog(
      context: context,
      barrierColor: Colors.black.withOpacity(0.6),
      builder: (BuildContext context) {
        return Dialog(
          backgroundColor: Colors.transparent,
          elevation: 0,
          child: ClipRRect(
            borderRadius: BorderRadius.circular(28),
            child: BackdropFilter(
              filter: ui_dart.ImageFilter.blur(sigmaX: 24, sigmaY: 24),
              child: Container(
                padding: EdgeInsets.all(24),
                constraints: BoxConstraints(
                  maxHeight: MediaQuery.of(context).size.height * 0.85,
                  maxWidth: getModalMaxWidth(),
                ),
                decoration: BoxDecoration(
                  color: joviNavy.withOpacity(0.92),
                  borderRadius: BorderRadius.circular(28),
                  border: Border.all(
                    color: Colors.white.withOpacity(0.12),
                    width: 1.5,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.4),
                      blurRadius: 40,
                      offset: Offset(0, 16),
                    ),
                  ],
                ),
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // Title row
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Row(
                            children: [
                              Container(
                                padding: EdgeInsets.all(8),
                                decoration: BoxDecoration(
                                  color: joviCoral.withOpacity(0.15),
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: Icon(Icons.wb_sunny,
                                    color: joviCoral, size: 20),
                              ),
                              SizedBox(width: 12),
                              Text(
                                'Weather & Health',
                                style: TextStyle(
                                  fontSize: 20,
                                  fontWeight: FontWeight.w700,
                                  color: Colors.white,
                                  letterSpacing: -0.5,
                                ),
                              ),
                            ],
                          ),
                          Material(
                            color: Colors.transparent,
                            child: InkWell(
                              onTap: () => Navigator.of(context).pop(),
                              borderRadius: BorderRadius.circular(20),
                              child: Container(
                                padding: EdgeInsets.all(6),
                                decoration: BoxDecoration(
                                  color: Colors.white.withOpacity(0.1),
                                  shape: BoxShape.circle,
                                ),
                                child: Icon(Icons.close,
                                    color: Colors.white.withOpacity(0.6),
                                    size: 18),
                              ),
                            ),
                          ),
                        ],
                      ),
                      SizedBox(height: 20),

                      // Health tip banner (if present)
                      if (weatherHealthTip != null) ...[
                        Container(
                          padding: EdgeInsets.all(14),
                          decoration: BoxDecoration(
                            gradient: LinearGradient(
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                              colors: [
                                joviCoral.withOpacity(0.18),
                                joviCoralLight.withOpacity(0.08),
                              ],
                            ),
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(
                              color: joviCoral.withOpacity(0.35),
                            ),
                          ),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Container(
                                padding: EdgeInsets.all(8),
                                decoration: BoxDecoration(
                                  color: joviCoral,
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: Icon(Icons.favorite,
                                    color: Colors.white, size: 16),
                              ),
                              SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      'HEALTH TIP',
                                      style: TextStyle(
                                        fontSize: 10.5,
                                        fontWeight: FontWeight.w700,
                                        color: joviCoral,
                                        letterSpacing: 1.2,
                                      ),
                                    ),
                                    SizedBox(height: 4),
                                    Text(
                                      weatherHealthTip!,
                                      style: TextStyle(
                                        fontSize: 13,
                                        fontWeight: FontWeight.w600,
                                        color: Colors.white,
                                        height: 1.4,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                        SizedBox(height: 16),
                      ],

                      // Current weather hero
                      Container(
                        padding:
                            EdgeInsets.symmetric(vertical: 28, horizontal: 20),
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            begin: Alignment.topCenter,
                            end: Alignment.bottomCenter,
                            colors: [
                              Colors.white.withOpacity(0.08),
                              Colors.white.withOpacity(0.03),
                            ],
                          ),
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(
                            color: Colors.white.withOpacity(0.1),
                          ),
                        ),
                        child: Column(
                          children: [
                            Text(
                              weatherData['icon'] ?? '🌤️',
                              style: TextStyle(fontSize: 64),
                            ),
                            SizedBox(height: 12),
                            Text(
                              weatherData['cityName'] ?? 'Your Location',
                              style: TextStyle(
                                fontSize: 15,
                                color: Colors.white.withOpacity(0.6),
                                fontWeight: FontWeight.w600,
                                letterSpacing: 0.3,
                              ),
                            ),
                            SizedBox(height: 8),
                            Text(
                              weatherData['temperature'] ?? '--°F',
                              style: TextStyle(
                                fontSize: 52,
                                fontWeight: FontWeight.w800,
                                color: Colors.white,
                                letterSpacing: -2,
                              ),
                            ),
                            SizedBox(height: 4),
                            Text(
                              weatherData['description'] ?? 'Loading...',
                              style: TextStyle(
                                fontSize: 16,
                                color: Colors.white.withOpacity(0.6),
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                            SizedBox(height: 6),
                            Text(
                              'Feels like ${weatherData['feelsLike'] ?? '--°F'}',
                              style: TextStyle(
                                fontSize: 13,
                                color: joviCoral.withOpacity(0.9),
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      ),
                      SizedBox(height: 18),

                      // Conditions grid
                      Container(
                        padding: EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.05),
                          borderRadius: BorderRadius.circular(18),
                          border: Border.all(
                            color: Colors.white.withOpacity(0.08),
                          ),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Padding(
                              padding: EdgeInsets.only(bottom: 12, left: 2),
                              child: Text(
                                'CONDITIONS',
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w700,
                                  color: Colors.white.withOpacity(0.4),
                                  letterSpacing: 1.5,
                                ),
                              ),
                            ),
                            Row(children: [
                              Expanded(
                                  child: _weatherDetailCard(
                                      'Humidity',
                                      weatherData['humidity'] ?? '--%',
                                      Icons.water_drop,
                                      joviMint)),
                              SizedBox(width: 8),
                              Expanded(
                                  child: _weatherDetailCard(
                                      'Wind',
                                      '${weatherData['windSpeed'] ?? '--'} ${weatherData['windDirection'] ?? ''}',
                                      Icons.air,
                                      joviCoralLight)),
                            ]),
                            SizedBox(height: 8),
                            Row(children: [
                              Expanded(
                                  child: _weatherDetailCard(
                                      'UV Index',
                                      weatherData['uvIndex'] ?? '--',
                                      Icons.wb_sunny,
                                      joviGold)),
                              SizedBox(width: 8),
                              Expanded(
                                  child: _weatherDetailCard(
                                      'Air Quality',
                                      weatherData['airQuality'] ?? '—',
                                      Icons.air_sharp,
                                      joviMintDark)),
                            ]),
                            SizedBox(height: 8),
                            Row(children: [
                              Expanded(
                                  child: _weatherDetailCard(
                                      'Pressure',
                                      weatherData['pressure'] ?? '--',
                                      Icons.speed,
                                      joviCoralLight)),
                              SizedBox(width: 8),
                              Expanded(
                                  child: _weatherDetailCard(
                                      'Clouds',
                                      weatherData['cloudCover'] ?? '--%',
                                      Icons.cloud,
                                      Colors.white.withOpacity(0.7))),
                            ]),
                            SizedBox(height: 8),
                            Row(children: [
                              Expanded(
                                  child: _weatherDetailCard(
                                      'Sunrise',
                                      weatherData['sunrise'] ?? '--',
                                      Icons.wb_sunny_outlined,
                                      joviGold)),
                              SizedBox(width: 8),
                              Expanded(
                                  child: _weatherDetailCard(
                                      'Sunset',
                                      weatherData['sunset'] ?? '--',
                                      Icons.nightlight_round,
                                      joviCoralLight)),
                            ]),
                          ],
                        ),
                      ),
                      SizedBox(height: 18),

                      // Action buttons
                      Row(
                        children: [
                          Expanded(
                            child: Material(
                              color: Colors.transparent,
                              child: InkWell(
                                onTap: () async {
                                  HapticFeedback.lightImpact();
                                  Navigator.of(context).pop();
                                  await initializeWeatherModule();
                                },
                                borderRadius: BorderRadius.circular(14),
                                child: Container(
                                  padding: EdgeInsets.symmetric(vertical: 13),
                                  decoration: BoxDecoration(
                                    color: Colors.white.withOpacity(0.08),
                                    borderRadius: BorderRadius.circular(14),
                                    border: Border.all(
                                      color: Colors.white.withOpacity(0.15),
                                    ),
                                  ),
                                  child: Row(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: [
                                      Icon(Icons.refresh,
                                          size: 18,
                                          color: Colors.white.withOpacity(0.8)),
                                      SizedBox(width: 8),
                                      Text('Refresh',
                                          style: TextStyle(
                                              color:
                                                  Colors.white.withOpacity(0.8),
                                              fontWeight: FontWeight.w600,
                                              fontSize: 14)),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                          ),
                          SizedBox(width: 10),
                          Expanded(
                            child: Material(
                              color: Colors.transparent,
                              child: InkWell(
                                onTap: () {
                                  HapticFeedback.lightImpact();
                                  Navigator.of(context).pop();
                                  _showExtendedForecast();
                                },
                                borderRadius: BorderRadius.circular(14),
                                child: Container(
                                  padding: EdgeInsets.symmetric(vertical: 13),
                                  decoration: BoxDecoration(
                                    gradient: LinearGradient(
                                      colors: [joviCoral, joviCoralDark],
                                    ),
                                    borderRadius: BorderRadius.circular(14),
                                    boxShadow: [
                                      BoxShadow(
                                        color: joviCoral.withOpacity(0.35),
                                        blurRadius: 12,
                                        offset: Offset(0, 4),
                                      ),
                                    ],
                                  ),
                                  child: Row(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: [
                                      Icon(Icons.calendar_view_week,
                                          size: 18, color: Colors.white),
                                      SizedBox(width: 8),
                                      Text('5-Day Forecast',
                                          style: TextStyle(
                                              color: Colors.white,
                                              fontWeight: FontWeight.w600,
                                              fontSize: 14)),
                                    ],
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
            ),
          ),
        );
      },
    );
  }

  Widget _weatherDetailCard(
      String label, String value, IconData icon, Color color) {
    return Container(
      padding: EdgeInsets.symmetric(vertical: 10, horizontal: 8),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.06),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.2)),
      ),
      child: Column(
        children: [
          Container(
            padding: EdgeInsets.all(7),
            decoration: BoxDecoration(
              color: color.withOpacity(0.15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(icon, size: 18, color: color),
          ),
          SizedBox(height: 8),
          Text(value,
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w700,
                color: Colors.white,
              )),
          SizedBox(height: 2),
          Text(label,
              style: TextStyle(
                fontSize: 10.5,
                color: Colors.white.withOpacity(0.5),
                fontWeight: FontWeight.w500,
              ),
              textAlign: TextAlign.center),
        ],
      ),
    );
  }

  void _showExtendedForecast() {
    HapticFeedback.lightImpact();
    showDialog(
      context: context,
      barrierColor: Colors.black.withOpacity(0.6),
      builder: (BuildContext context) {
        return Dialog(
          backgroundColor: Colors.transparent,
          elevation: 0,
          child: ClipRRect(
            borderRadius: BorderRadius.circular(28),
            child: BackdropFilter(
              filter: ui_dart.ImageFilter.blur(sigmaX: 24, sigmaY: 24),
              child: Container(
                padding: EdgeInsets.all(24),
                constraints: BoxConstraints(
                  maxHeight: MediaQuery.of(context).size.height * 0.8,
                  maxWidth: getModalMaxWidth(),
                ),
                decoration: BoxDecoration(
                  color: joviNavy.withOpacity(0.92),
                  borderRadius: BorderRadius.circular(28),
                  border: Border.all(
                    color: Colors.white.withOpacity(0.12),
                    width: 1.5,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.4),
                      blurRadius: 40,
                      offset: Offset(0, 16),
                    ),
                  ],
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('5-Day Forecast',
                                style: TextStyle(
                                  fontSize: 20,
                                  fontWeight: FontWeight.w700,
                                  color: Colors.white,
                                  letterSpacing: -0.3,
                                )),
                            SizedBox(height: 2),
                            Text(weatherData['cityName'] ?? 'Your Location',
                                style: TextStyle(
                                  fontSize: 13,
                                  color: Colors.white.withOpacity(0.5),
                                  fontWeight: FontWeight.w500,
                                )),
                          ],
                        ),
                        Material(
                          color: Colors.transparent,
                          child: InkWell(
                            onTap: () => Navigator.of(context).pop(),
                            borderRadius: BorderRadius.circular(20),
                            child: Container(
                              padding: EdgeInsets.all(6),
                              decoration: BoxDecoration(
                                color: Colors.white.withOpacity(0.1),
                                shape: BoxShape.circle,
                              ),
                              child: Icon(Icons.close,
                                  color: Colors.white.withOpacity(0.6),
                                  size: 18),
                            ),
                          ),
                        ),
                      ],
                    ),
                    SizedBox(height: 18),
                    Expanded(
                      child: ListView.builder(
                        itemCount: forecastData.length,
                        itemBuilder: (context, index) {
                          final forecast = forecastData[index];
                          final date = forecast['date'] as DateTime;
                          final dayName = DateFormat('EEEE').format(date);
                          final dateStr = DateFormat('MMM d').format(date);

                          return Container(
                            margin: EdgeInsets.only(bottom: 8),
                            padding: EdgeInsets.all(14),
                            decoration: BoxDecoration(
                              color: Colors.white.withOpacity(0.06),
                              borderRadius: BorderRadius.circular(14),
                              border: Border.all(
                                color: Colors.white.withOpacity(0.08),
                              ),
                            ),
                            child: Row(
                              children: [
                                Expanded(
                                  flex: 2,
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(dayName,
                                          style: TextStyle(
                                            fontSize: 14,
                                            fontWeight: FontWeight.w700,
                                            color: Colors.white,
                                          )),
                                      Text(dateStr,
                                          style: TextStyle(
                                            fontSize: 11,
                                            color:
                                                Colors.white.withOpacity(0.5),
                                          )),
                                    ],
                                  ),
                                ),
                                Expanded(
                                  flex: 1,
                                  child: Column(
                                    children: [
                                      Text(forecast['icon'] ?? '🌤️',
                                          style: TextStyle(fontSize: 26)),
                                      SizedBox(height: 2),
                                      Text(forecast['description'] ?? '',
                                          style: TextStyle(
                                            fontSize: 10.5,
                                            color:
                                                Colors.white.withOpacity(0.5),
                                          ),
                                          textAlign: TextAlign.center,
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis),
                                    ],
                                  ),
                                ),
                                Expanded(
                                  flex: 2,
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.end,
                                    children: [
                                      Row(
                                        mainAxisAlignment:
                                            MainAxisAlignment.end,
                                        children: [
                                          Text(
                                              '${forecast['temp_max']?.round() ?? '--'}°',
                                              style: TextStyle(
                                                fontSize: 16,
                                                fontWeight: FontWeight.w700,
                                                color: Colors.white,
                                              )),
                                          SizedBox(width: 6),
                                          Text(
                                              '${forecast['temp_min']?.round() ?? '--'}°',
                                              style: TextStyle(
                                                fontSize: 14,
                                                fontWeight: FontWeight.w600,
                                                color: Colors.white
                                                    .withOpacity(0.45),
                                              )),
                                        ],
                                      ),
                                      SizedBox(height: 4),
                                      Container(
                                        padding: EdgeInsets.symmetric(
                                            horizontal: 7, vertical: 2),
                                        decoration: BoxDecoration(
                                          color: joviMint.withOpacity(0.15),
                                          borderRadius:
                                              BorderRadius.circular(8),
                                          border: Border.all(
                                            color: joviMint.withOpacity(0.25),
                                          ),
                                        ),
                                        child: Row(
                                          mainAxisSize: MainAxisSize.min,
                                          children: [
                                            Icon(Icons.water_drop,
                                                size: 10, color: joviMint),
                                            SizedBox(width: 3),
                                            Text(
                                                '${forecast['humidity'] ?? '--'}%',
                                                style: TextStyle(
                                                  fontSize: 10.5,
                                                  color: joviMint,
                                                  fontWeight: FontWeight.w600,
                                                )),
                                          ],
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                          );
                        },
                      ),
                    ),
                    SizedBox(height: 14),
                    Row(
                      children: [
                        Expanded(
                          child: Material(
                            color: Colors.transparent,
                            child: InkWell(
                              onTap: () {
                                HapticFeedback.lightImpact();
                                Navigator.of(context).pop();
                                displayWeatherModal();
                              },
                              borderRadius: BorderRadius.circular(12),
                              child: Container(
                                padding: EdgeInsets.symmetric(vertical: 12),
                                decoration: BoxDecoration(
                                  color: Colors.white.withOpacity(0.08),
                                  borderRadius: BorderRadius.circular(12),
                                  border: Border.all(
                                    color: Colors.white.withOpacity(0.15),
                                  ),
                                ),
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Icon(Icons.arrow_back,
                                        size: 16,
                                        color: Colors.white.withOpacity(0.7)),
                                    SizedBox(width: 6),
                                    Text('Back',
                                        style: TextStyle(
                                          color: Colors.white.withOpacity(0.7),
                                          fontWeight: FontWeight.w600,
                                          fontSize: 13,
                                        )),
                                  ],
                                ),
                              ),
                            ),
                          ),
                        ),
                        SizedBox(width: 10),
                        Expanded(
                          child: Material(
                            color: Colors.transparent,
                            child: InkWell(
                              onTap: () async {
                                HapticFeedback.lightImpact();
                                Navigator.of(context).pop();
                                await initializeWeatherModule();
                              },
                              borderRadius: BorderRadius.circular(12),
                              child: Container(
                                padding: EdgeInsets.symmetric(vertical: 12),
                                decoration: BoxDecoration(
                                  gradient: LinearGradient(
                                    colors: [joviCoral, joviCoralDark],
                                  ),
                                  borderRadius: BorderRadius.circular(12),
                                  boxShadow: [
                                    BoxShadow(
                                      color: joviCoral.withOpacity(0.3),
                                      blurRadius: 10,
                                      offset: Offset(0, 4),
                                    ),
                                  ],
                                ),
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Icon(Icons.refresh,
                                        size: 16, color: Colors.white),
                                    SizedBox(width: 6),
                                    Text('Refresh',
                                        style: TextStyle(
                                          color: Colors.white,
                                          fontWeight: FontWeight.w600,
                                          fontSize: 13,
                                        )),
                                  ],
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
          ),
        );
      },
    );
  }

  // =================================================================
  // SECTION 20: BUILD METHOD (V2 LAYOUT)
  // =================================================================

  @override
  Widget build(BuildContext context) {
    final greet = calculateGreeting();
    final authUser = FirebaseAuth.instance.currentUser;
    String displayName = 'Member';

    if (userFullName?.isNotEmpty == true) {
      displayName = userFullName!.split(' ').first;
    } else if (userFirstName?.isNotEmpty == true) {
      displayName = userFirstName!;
    } else if (widget.displayName?.isNotEmpty == true) {
      displayName = widget.displayName!.split(' ').first;
    } else if (authUser?.displayName?.isNotEmpty == true) {
      displayName = authUser!.displayName!.split(' ').first;
    }

    final String? uid = widget.userId ?? FirebaseAuth.instance.currentUser?.uid;

    Widget mainContent = SingleChildScrollView(
      controller: _scrollController,
      physics: AlwaysScrollableScrollPhysics(
        parent: BouncingScrollPhysics(),
      ),
      padding: EdgeInsets.symmetric(
        horizontal: layoutSettings.paddingH,
        vertical: layoutSettings.paddingV,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── HEADER BAND ──
          FadeTransition(
            opacity: mainFadeEffect,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                renderLogo(),
                Row(
                  children: [
                    renderCompactWeatherWidget(),
                    if (_showsWeatherChip) const SizedBox(width: 10),
                    // Single-listener unread check via the helper widget —
                    // avoids nested StreamBuilders that respawn subscriptions.
                    _UnreadTicketIndicator(
                      uid: uid,
                      builder: (hasUnread) =>
                          renderChatButton(hasUnread: hasUnread),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // ── GREETING + AVATAR ──
          SlideTransition(
            position: contentSlideEffect,
            child: FadeTransition(
              opacity: mainFadeEffect,
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Text.rich (not RichText) so the greeting follows
                        // Dynamic Type — RichText ignores the text scaler.
                        Text.rich(
                          TextSpan(
                            style: const TextStyle(
                                fontSize: 30,
                                fontWeight: FontWeight.w700,
                                letterSpacing: -0.9,
                                height: 1.1),
                            children: [
                              TextSpan(
                                  text: '$greet, ',
                                  style: const TextStyle(color: Colors.white)),
                              TextSpan(
                                  text: displayName,
                                  style: const TextStyle(color: joviCoral)),
                            ],
                          ),
                        ),
                        const SizedBox(height: 6),
                        Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(
                              padding: EdgeInsets.all(3),
                              decoration: BoxDecoration(
                                color: coverageActive
                                    ? joviMint.withOpacity(0.25)
                                    : const Color(0xFFFFEBEE).withOpacity(0.3),
                                shape: BoxShape.circle,
                              ),
                              child: Icon(
                                coverageActive
                                    ? Icons.check_circle
                                    : Icons.error,
                                size: 16,
                                color: coverageActive
                                    ? joviMint
                                    : const Color(0xFFFF6B6B),
                              ),
                            ),
                            SizedBox(width: 8),
                            Text(
                              'Your plan is ',
                              style: TextStyle(
                                  fontSize: 14,
                                  color: Colors.white.withOpacity(0.75),
                                  fontWeight: FontWeight.w500),
                            ),
                            Text(
                              coverageActive ? 'Active' : 'Inactive',
                              style: TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.w700,
                                color: coverageActive
                                    ? joviMint
                                    : const Color(0xFFFF6B6B),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 16),
                  Hero(
                    tag: 'user_avatar',
                    child: _Pressable(
                      reduceMotion: _reduceMotion,
                      pressedScale: 0.94,
                      semanticsLabel: 'Profile photo',
                      semanticsHint: 'Edit profile',
                      onTap: () {
                        HapticFeedback.lightImpact();
                        context.push('/updateProfile');
                      },
                      child: createUserAvatar(
                        imagePath: userProfileImagePath,
                        imageUrl: userProfileImageUrl,
                        radius: 32,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),

          // ── ACTION NEEDED STRIP (conditional) ──
          renderActionNeededStrip(),
          if (_actionItems.isNotEmpty) const SizedBox(height: 22),

          // ── FOR YOU INSIGHT ──
          if (_insights.isNotEmpty) ...[
            renderForYouCard(),
            const SizedBox(height: 22),
          ],

          // ── CARDS: Responsibility + Plan Details ──
          if (loadingInsuranceData)
            Column(
              children: [
                _buildHomeSkeletonCard(height: 190),
                const SizedBox(height: 14),
                _buildHomeSkeletonCard(height: 120),
              ],
            )
          else
            renderCardsSection(),

          const SizedBox(height: 26),

          // ── QUICK ACTIONS ──
          SlideTransition(
            position: contentSlideEffect,
            child: FadeTransition(
              opacity: mainFadeEffect,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        width: 4,
                        height: 18,
                        decoration: BoxDecoration(
                          color: joviCoral.withOpacity(0.7),
                          borderRadius: BorderRadius.circular(2),
                        ),
                      ),
                      SizedBox(width: 10),
                      Text('Quick Actions',
                          style: TextStyle(
                              fontSize: 17,
                              fontWeight: FontWeight.w700,
                              color: Colors.white,
                              letterSpacing: -0.3)),
                      Spacer(),
                      if ((hasRefillsDue || upcomingAppointmentsCount > 0))
                        Text(
                          'Reordered for you',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: joviCoral,
                            letterSpacing: -0.1,
                            fontStyle: FontStyle.italic,
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  renderQuickActionsGrid(),
                ],
              ),
            ),
          ),
          const SizedBox(height: 26),

          // ── RECENT ACTIVITY ──
          Row(
            children: [
              Container(
                width: 4,
                height: 18,
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.3),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              SizedBox(width: 10),
              Text('Recent Activity',
                  style: TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.w700,
                      color: Colors.white,
                      letterSpacing: -0.3)),
              Spacer(),
              _Pressable(
                reduceMotion: _reduceMotion,
                pressedScale: 0.95,
                semanticsLabel: 'See all activity',
                onTap: _navigateToActivity,
                child: Container(
                  padding: EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        'See all',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: Colors.white.withOpacity(0.6),
                          letterSpacing: -0.1,
                        ),
                      ),
                      SizedBox(width: 3),
                      Icon(
                        Icons.arrow_forward_rounded,
                        size: 13,
                        color: Colors.white.withOpacity(0.6),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          _buildRecentActivitySection(),
          SizedBox(height: 180),
        ],
      ),
    );

    if (currentScreenType == ScreenType.expanded || layoutSettings.hasHinge) {
      mainContent = Container(
        width: widget.width,
        height: widget.height,
        // background painted by the Scaffold body gradient
        child: Column(
          children: [
            SizedBox(height: MediaQuery.of(context).padding.top),
            Expanded(child: mainContent),
          ],
        ),
      );
    } else {
      mainContent = Container(
        width: widget.width,
        height: widget.height,
        // background now painted by the Scaffold body gradient
        child: SafeArea(
          child: wrapWithConstraints(child: mainContent),
        ),
      );
    }

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        statusBarBrightness: Brightness.dark,
      ),
      child: Scaffold(
        backgroundColor: const Color(0xFF0F1A2E), // joviNavyDark
        floatingActionButton: Padding(
          padding: EdgeInsets.only(
            bottom: MediaQuery.of(context).padding.bottom + 160,
          ),
          child: renderFloatingButton(),
        ),
        floatingActionButtonLocation: FloatingActionButtonLocation.endFloat,
        body: Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [
                Color(0xFF0F1A2E), // joviNavyDark
                joviNavy,
                Color(0xFF0F1A2E),
              ],
              stops: [0.0, 0.45, 1.0],
            ),
          ),
          child: Stack(
            children: [
              // Static ambient glows — depth without repaint cost.
              IgnorePointer(
                child: Stack(
                  children: [
                    Positioned(
                      top: -120,
                      right: -80,
                      child: Container(
                        width: 320,
                        height: 320,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: RadialGradient(
                            colors: [
                              joviCoral.withOpacity(0.10),
                              joviCoral.withOpacity(0.0),
                            ],
                          ),
                        ),
                      ),
                    ),
                    Positioned(
                      top: 420,
                      left: -140,
                      child: Container(
                        width: 300,
                        height: 300,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: RadialGradient(
                            colors: [
                              joviMint.withOpacity(0.05),
                              joviMint.withOpacity(0.0),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              RefreshIndicator(
                onRefresh: () async {
                  setState(() => _recentActivitiesFuture = null);
                  await initializeUserProfile(forceReload: true);
                  await _loadAppointmentsAndRefills();
                },
                displacement: 80,
                color: joviCoral,
                child: mainContent,
              ),
            ],
          ),
        ),
      ),
    );
  }

  // =================================================================
  // SECTION 21: RECENT ACTIVITY SECTION
  // =================================================================

  // Memoized so insight-rotation setState (every 8s) doesn't re-fire
  // the three Firestore queries and flash a spinner on every rebuild.
  Future<List<Map<String, dynamic>>>? _recentActivitiesFuture;

  Widget _buildHomeSkeletonCard({required double height}) {
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0.05, end: 0.10),
      duration: const Duration(milliseconds: 900),
      curve: Curves.easeInOut,
      builder: (context, opacity, _) {
        return Container(
          width: double.infinity,
          height: height,
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(opacity),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: Colors.white.withOpacity(0.12)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 140,
                height: 12,
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(6),
                ),
              ),
              const SizedBox(height: 12),
              Container(
                width: double.infinity,
                height: 10,
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.08),
                  borderRadius: BorderRadius.circular(6),
                ),
              ),
              const SizedBox(height: 8),
              Container(
                width: 200,
                height: 10,
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.08),
                  borderRadius: BorderRadius.circular(6),
                ),
              ),
              const Spacer(),
              Container(
                width: 100,
                height: 22,
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.10),
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildRecentActivitySection() {
    final uid = widget.userId ?? FirebaseAuth.instance.currentUser?.uid;
    if (uid == null) return _buildEmptyActivityState();

    _recentActivitiesFuture ??= _fetchRecentActivities(uid);

    return FutureBuilder<List<Map<String, dynamic>>>(
      future: _recentActivitiesFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return _buildHomeSkeletonCard(height: 90);
        }

        final activities = snapshot.data ?? [];
        if (activities.isEmpty) {
          return _buildEmptyActivityState();
        }

        return Column(
          children: activities.take(5).map((activity) {
            final type = activity['_type'] as String;
            switch (type) {
              case 'appointment':
                return _buildAppointmentActivityCard(activity);
              case 'claim':
                return _buildClaimActivityCard(activity);
              case 'refill':
                return _buildRefillActivityCard(activity);
              default:
                return SizedBox.shrink();
            }
          }).toList(),
        );
      },
    );
  }

  Widget _buildEmptyActivityState() {
    return Container(
      // Parent column is start-aligned; without a width the card shrinks to
      // its text and sits off-center.
      width: double.infinity,
      padding: EdgeInsets.symmetric(vertical: 36, horizontal: 20),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.08),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: Colors.white.withOpacity(0.15)),
      ),
      child: Column(
        children: [
          Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.08),
              shape: BoxShape.circle,
            ),
            child: Icon(Icons.history_rounded,
                color: Colors.white.withOpacity(0.4), size: 28),
          ),
          SizedBox(height: 14),
          Text(
            'No recent activity',
            style: TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w700,
              color: Colors.white,
              letterSpacing: -0.2,
            ),
          ),
          SizedBox(height: 4),
          Text(
            'Your appointments, claims, and refills will show here.',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 12,
              color: Colors.white.withOpacity(0.55),
              fontWeight: FontWeight.w500,
              height: 1.4,
            ),
          ),
        ],
      ),
    );
  }

  Future<List<Map<String, dynamic>>> _fetchRecentActivities(String uid) async {
    final fs = FirebaseFirestore.instance;

    // Kick off all three queries in parallel. Individual failures are caught
    // via the .catchError fallback so one slow collection doesn't block the others.
    final futures = <Future<QuerySnapshot<Map<String, dynamic>>>>[
      fs
          .collection('requests')
          .where('userId', isEqualTo: uid)
          .limit(10)
          .get()
          .catchError((e) {
        if (kDebugMode) print('Error loading appointment activity: $e');
        return _emptyQuerySnap('requests');
      }),
      fs
          .collection('users')
          .doc(uid)
          .collection('claims')
          .limit(10)
          .get()
          .catchError((e) {
        if (kDebugMode) print('Error loading claim activity: $e');
        return _emptyQuerySnap('claims');
      }),
      fs
          .collection('refills')
          .where('userId', isEqualTo: uid)
          .limit(10)
          .get()
          .catchError((e) {
        if (kDebugMode) print('Error loading refill activity: $e');
        return _emptyQuerySnap('refills');
      }),
    ];

    final results = await Future.wait(futures);
    final List<Map<String, dynamic>> all = [];

    // Appointments
    for (final doc in results[0].docs) {
      final d = Map<String, dynamic>.from(doc.data());
      d['_type'] = 'appointment';
      d['_id'] = doc.id;
      d['_sortDate'] =
          _parseActivityDate(d['createdAt'] ?? d['appointmentDate']);
      all.add(d);
    }
    // Claims
    for (final doc in results[1].docs) {
      final d = Map<String, dynamic>.from(doc.data());
      d['_type'] = 'claim';
      d['_id'] = doc.id;
      d['_sortDate'] = _parseActivityDate(d['submittedAt'] ?? d['createdAt']);
      all.add(d);
    }
    // Refills
    for (final doc in results[2].docs) {
      final d = Map<String, dynamic>.from(doc.data());
      d['_type'] = 'refill';
      d['_id'] = doc.id;
      d['_sortDate'] = _parseActivityDate(d['requestedAt'] ?? d['createdAt']);
      all.add(d);
    }

    // Sort newest first
    all.sort((a, b) {
      final aDate = a['_sortDate'] as DateTime? ?? DateTime(1970);
      final bDate = b['_sortDate'] as DateTime? ?? DateTime(1970);
      return bDate.compareTo(aDate);
    });

    return all;
  }

  // Returns an empty QuerySnapshot-like object for error fallback in Future.wait
  Future<QuerySnapshot<Map<String, dynamic>>> _emptyQuerySnap(
    String collectionName,
  ) async {
    // Use an impossible query on the same collection to get an empty snapshot
    // with the right type. This keeps Future.wait's type homogeneous.
    return FirebaseFirestore.instance
        .collection(collectionName)
        .where('__nonexistent__', isEqualTo: '__never__')
        .limit(1)
        .get();
  }

  DateTime? _parseActivityDate(dynamic raw) {
    if (raw == null) return null;
    if (raw is Timestamp) return raw.toDate();
    if (raw is String) {
      try {
        return DateTime.parse(raw);
      } catch (e) {
        return null;
      }
    }
    return null;
  }

  Widget _buildAppointmentActivityCard(Map<String, dynamic> a) {
    final status = a['status'] as String? ?? 'pending';
    final provider = a['provider'] as String? ?? 'Care Request';
    final dateStr = _formatActivityDate(a['_sortDate'] as DateTime?);
    final statusColor = _getActivityStatusColor(status);

    return _Pressable(
      reduceMotion: _reduceMotion,
      pressedScale: 0.98,
      semanticsLabel: '$provider, $status, $dateStr',
      onTap: _navigateToCareRecords,
      child: Container(
        margin: EdgeInsets.only(bottom: 10),
        padding: EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.08),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: Colors.white.withOpacity(0.15)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.22),
              blurRadius: 8,
              offset: Offset(0, 3),
            ),
          ],
        ),
        child: Row(
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: joviCoral.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(Icons.calendar_today, size: 20, color: joviCoral),
            ),
            SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    provider,
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      color: Colors.white,
                      letterSpacing: -0.2,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  SizedBox(height: 2),
                  Text(
                    dateStr,
                    style: TextStyle(
                      fontSize: 11,
                      color: Colors.white.withOpacity(0.55),
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
            Container(
              padding: EdgeInsets.symmetric(horizontal: 9, vertical: 4),
              decoration: BoxDecoration(
                color: statusColor.withOpacity(0.12),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                status.toUpperCase(),
                style: TextStyle(
                  fontSize: 10.5,
                  fontWeight: FontWeight.w700,
                  color: statusColor,
                  letterSpacing: 0.5,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildClaimActivityCard(Map<String, dynamic> c) {
    final status = c['status'] as String? ?? 'submitted';
    final provider = c['provider'] as String? ?? 'Claim';
    final amount = c['amount'];
    final amtStr = amount is num
        ? '\$${amount.toStringAsFixed(2)}'
        : (amount is String ? amount : '');
    final dateStr = _formatActivityDate(c['_sortDate'] as DateTime?);
    final statusColor = _getClaimStatusColor(status);

    return _Pressable(
      reduceMotion: _reduceMotion,
      pressedScale: 0.98,
      semanticsLabel: 'Claim, $provider, $status, $dateStr',
      onTap: () {
        HapticFeedback.lightImpact();
        context.push('/fileclaim');
      },
      child: Container(
        margin: EdgeInsets.only(bottom: 10),
        padding: EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.08),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: Colors.white.withOpacity(0.15)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.22),
              blurRadius: 8,
              offset: Offset(0, 3),
            ),
          ],
        ),
        child: Row(
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: joviMint.withOpacity(0.12),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(Icons.receipt_long, size: 20, color: joviMintDark),
            ),
            SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          provider,
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w700,
                            color: Colors.white,
                            letterSpacing: -0.2,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      if (amtStr.isNotEmpty)
                        Text(
                          amtStr,
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                            color: Colors.white,
                            letterSpacing: -0.3,
                          ),
                        ),
                    ],
                  ),
                  SizedBox(height: 2),
                  Text(
                    dateStr,
                    style: TextStyle(
                      fontSize: 11,
                      color: Colors.white.withOpacity(0.55),
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
            SizedBox(width: 8),
            Container(
              padding: EdgeInsets.symmetric(horizontal: 9, vertical: 4),
              decoration: BoxDecoration(
                color: statusColor.withOpacity(0.12),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                status.toUpperCase(),
                style: TextStyle(
                  fontSize: 10.5,
                  fontWeight: FontWeight.w700,
                  color: statusColor,
                  letterSpacing: 0.5,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRefillActivityCard(Map<String, dynamic> r) {
    final status = r['status'] as String? ?? 'pending';
    final med = r['medicationName'] as String? ??
        r['name'] as String? ??
        'Prescription';
    final pharm = r['pharmacyName'] as String? ?? '';
    final dateStr = _formatActivityDate(r['_sortDate'] as DateTime?);
    final statusColor = _getActivityStatusColor(status);

    return _Pressable(
      reduceMotion: _reduceMotion,
      pressedScale: 0.98,
      semanticsLabel: 'Refill, $med, $status, $dateStr',
      onTap: () {
        HapticFeedback.lightImpact();
        context.push('/scriptRefill');
      },
      child: Container(
        margin: EdgeInsets.only(bottom: 10),
        padding: EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.08),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: Colors.white.withOpacity(0.15)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.22),
              blurRadius: 8,
              offset: Offset(0, 3),
            ),
          ],
        ),
        child: Row(
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: joviCoralLight.withOpacity(0.18),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(Icons.medication, size: 20, color: joviCoralDark),
            ),
            SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    med,
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      color: Colors.white,
                      letterSpacing: -0.2,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  SizedBox(height: 2),
                  Text(
                    pharm.isNotEmpty ? '$pharm • $dateStr' : dateStr,
                    style: TextStyle(
                      fontSize: 11,
                      color: Colors.white.withOpacity(0.55),
                      fontWeight: FontWeight.w500,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
            Container(
              padding: EdgeInsets.symmetric(horizontal: 9, vertical: 4),
              decoration: BoxDecoration(
                color: statusColor.withOpacity(0.12),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                status.toUpperCase(),
                style: TextStyle(
                  fontSize: 10.5,
                  fontWeight: FontWeight.w700,
                  color: statusColor,
                  letterSpacing: 0.5,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Color _getActivityStatusColor(String status) {
    switch (status.toLowerCase()) {
      case 'confirmed':
      case 'completed':
      case 'ready':
      case 'approved':
        return joviMint;
      case 'pending':
      case 'submitted':
      case 'processing':
        return joviGold;
      case 'cancelled':
      case 'denied':
      case 'rejected':
        return const Color(0xFFFF8A80);
      default:
        return Colors.white.withOpacity(0.7);
    }
  }

  Color _getClaimStatusColor(String status) {
    switch (status.toLowerCase()) {
      case 'approved':
      case 'paid':
      case 'reimbursed':
        return joviMint;
      case 'submitted':
      case 'processing':
      case 'under review':
      case 'under_review':
        return joviGold;
      case 'needs_info':
      case 'needs info':
      case 'needs_more_info':
        return joviCoral;
      case 'denied':
      case 'rejected':
        return const Color(0xFFFF8A80);
      case 'draft':
        return Colors.white.withOpacity(0.5);
      default:
        return Colors.white.withOpacity(0.7);
    }
  }

  String _formatActivityDate(DateTime? date) {
    if (date == null) return '';
    final now = DateTime.now();
    final diff = now.difference(date);
    if (diff.inDays == 0) {
      if (diff.inHours == 0) {
        return diff.inMinutes <= 1 ? 'Just now' : '${diff.inMinutes} min ago';
      }
      return diff.inHours == 1 ? '1 hour ago' : '${diff.inHours} hours ago';
    }
    if (diff.inDays == 1) return 'Yesterday';
    if (diff.inDays < 7) return '${diff.inDays} days ago';
    return DateFormat('MMM d, yyyy').format(date);
  }
}
// End of _JoviHealthHomeWidgetState

// =================================================================
// UNREAD TICKET INDICATOR
// Single-listener replacement for the nested StreamBuilder pattern.
// Watches open help tickets and their unread team messages efficiently.
// =================================================================

class _UnreadTicketIndicator extends StatefulWidget {
  final String? uid;
  final Widget Function(bool hasUnread) builder;

  const _UnreadTicketIndicator({
    required this.uid,
    required this.builder,
  });

  @override
  State<_UnreadTicketIndicator> createState() => _UnreadTicketIndicatorState();
}

class _UnreadTicketIndicatorState extends State<_UnreadTicketIndicator> {
  StreamSubscription<QuerySnapshot>? _ticketSub;
  StreamSubscription<QuerySnapshot>? _messageSub;
  String? _activeTicketId;
  bool _hasUnread = false;

  @override
  void initState() {
    super.initState();
    _subscribeToTickets();
  }

  @override
  void didUpdateWidget(_UnreadTicketIndicator oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.uid != widget.uid) {
      _resubscribe();
    }
  }

  void _resubscribe() {
    _ticketSub?.cancel();
    _messageSub?.cancel();
    _activeTicketId = null;
    if (mounted) {
      setState(() => _hasUnread = false);
    }
    _subscribeToTickets();
  }

  void _subscribeToTickets() {
    final uid = widget.uid;
    if (uid == null) return;
    _ticketSub = FirebaseFirestore.instance
        .collection('helpTickets')
        .where('userId', isEqualTo: uid)
        .where('status', isEqualTo: 'open')
        .limit(1)
        .snapshots()
        .listen((snap) {
      if (snap.docs.isEmpty) {
        // No open tickets — cancel inner listener if any, clear state
        if (_activeTicketId != null) {
          _messageSub?.cancel();
          _messageSub = null;
          _activeTicketId = null;
        }
        if (mounted && _hasUnread) {
          setState(() => _hasUnread = false);
        }
        return;
      }
      final newTicketId = snap.docs.first.id;
      // Only re-subscribe the inner stream if the ticket actually changed
      if (newTicketId != _activeTicketId) {
        _messageSub?.cancel();
        _activeTicketId = newTicketId;
        _messageSub = FirebaseFirestore.instance
            .collection('helpTickets')
            .doc(newTicketId)
            .collection('messages')
            .where('readByUser', isEqualTo: false)
            .limit(10)
            .snapshots()
            .listen((msgSnap) {
          // Unread = a message from someone other than the member (support/clinician).
          final unread = msgSnap.docs.any((d) => (d.data()['senderId'] as String?) != uid);
          if (mounted && unread != _hasUnread) {
            setState(() => _hasUnread = unread);
          }
        });
      }
    });
  }

  @override
  void dispose() {
    _ticketSub?.cancel();
    _messageSub?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => widget.builder(_hasUnread);
}

// =================================================================
// DASHED LINE PAINTER (for pace line in histogram)
// =================================================================

class _DashedLinePainter extends CustomPainter {
  final Color color;
  final double dashWidth;
  final double dashSpace;
  final double strokeWidth;

  _DashedLinePainter({
    required this.color,
    this.dashWidth = 5.0,
    this.dashSpace = 4.0,
    this.strokeWidth = 1.5,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    double startX = 0;
    final y = size.height / 2;
    while (startX < size.width) {
      canvas.drawLine(
        Offset(startX, y),
        Offset(startX + dashWidth, y),
        paint,
      );
      startX += dashWidth + dashSpace;
    }
  }

  @override
  bool shouldRepaint(covariant _DashedLinePainter oldDelegate) =>
      oldDelegate.color != color ||
      oldDelegate.dashWidth != dashWidth ||
      oldDelegate.dashSpace != dashSpace ||
      oldDelegate.strokeWidth != strokeWidth;
}
