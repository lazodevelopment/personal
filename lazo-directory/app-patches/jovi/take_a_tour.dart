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

// ============================================================
// JOVI HEALTH — TAKE A TOUR (NAVY + GLASS)
// Version: 2026.09.22-r3 (Apple HIG pass: no overshoot, no drifting orbs,
//          Reduce Motion, press feedback, direct Skip)
// r2:      2026.07.11
// Full rebrand from legacy Kurv blue. 10 pages (Pets page added).
// Screenshots replaced with code-drawn UI mockups — zero network
// calls, no stale Kurv imagery. Same public API + hasSeenTour
// prefs key — drop-in replacement.
// ============================================================

import 'dart:ui' as ui_dart;
import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';
import 'package:shared_preferences/shared_preferences.dart';

// Jovi Health Brand Colors (private to avoid cross-widget collisions)
const Color _joviCoral = Color(0xFFFF6B4A);
const Color _joviCoralLight = Color(0xFFFF8F73);
const Color _joviNavy = Color(0xFF1A2744);
const Color _joviNavyDark = Color(0xFF0F1A2E);
const Color _joviNavyLight = Color(0xFF243352);
const Color _joviMint = Color(0xFF00D4AA);
const Color _joviGold = Color(0xFFFFD166);
const Color _joviWarmWhite = Color(0xFFFFF8F5);

enum ScreenType { compact, medium, expanded, large }

class ResponsiveConfig {
  final double paddingH;
  final double paddingV;
  final double contentMax;
  final double titleFontSize;
  final double subtitleFontSize;
  final double descriptionFontSize;
  final double iconSize;
  final double logoFontSize;
  final double buttonFontSize;
  final double screenshotWidth;
  final double screenshotHeight;
  final bool wideMode;
  final bool hasHinge;
  final bool useTwoColumnLayout;

  ResponsiveConfig({
    required this.paddingH,
    required this.paddingV,
    required this.contentMax,
    required this.titleFontSize,
    required this.subtitleFontSize,
    required this.descriptionFontSize,
    required this.iconSize,
    required this.logoFontSize,
    required this.buttonFontSize,
    required this.screenshotWidth,
    required this.screenshotHeight,
    required this.wideMode,
    required this.hasHinge,
    this.useTwoColumnLayout = false,
  });
}

/// Data model for a single tour page.
class _TourPage {
  final String title;
  final String subtitle;
  final String description;
  final IconData icon;
  final Color accent;
  final Color accentSoft;
  final List<String> features;
  final String? screenshotKey;

  const _TourPage({
    required this.title,
    required this.subtitle,
    required this.description,
    required this.icon,
    required this.accent,
    required this.accentSoft,
    required this.features,
    this.screenshotKey,
  });
}

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
  final bool enabled;
  final bool feedbackOnly;
  final double pressedScale;

  const _Pressable({
    Key? key,
    required this.child,
    this.onTap,
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
        widget.enabled && (widget.onTap != null || widget.feedbackOnly);
    final scale = (_down && animates && !reduce) ? widget.pressedScale : 1.0;
    final scaled = AnimatedScale(
      scale: scale,
      duration: _down ? _Motion.pressIn : _Motion.pressOut,
      curve: _down ? Curves.easeOut : _Motion.settle,
      child: widget.child,
    );
    final handlesTap = widget.onTap != null && !widget.feedbackOnly;
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

class TakeATourWidget extends StatefulWidget {
  final double width;
  final double height;

  const TakeATourWidget({
    Key? key,
    required this.width,
    required this.height,
  }) : super(key: key);

  @override
  State<TakeATourWidget> createState() => _TakeATourWidgetState();
}

class _TakeATourWidgetState extends State<TakeATourWidget>
    with TickerProviderStateMixin {
  ScreenType currentScreenType = ScreenType.compact;
  ResponsiveConfig layoutSettings = ResponsiveConfig(
    paddingH: 24,
    paddingV: 20,
    contentMax: double.infinity,
    titleFontSize: 28,
    subtitleFontSize: 18,
    descriptionFontSize: 15,
    iconSize: 100,
    logoFontSize: 20,
    buttonFontSize: 16,
    screenshotWidth: 200,
    screenshotHeight: 400,
    wideMode: false,
    hasHinge: false,
  );

  double? _lastScreenWidth;
  bool? _lastHasHinge;

  final PageController _pageController = PageController();
  late AnimationController _animController;
  late AnimationController _screenshotAnimController;
  late AnimationController _orbController;
  late Animation<double> _fadeAnimation;
  late Animation<double> _scaleAnimation;
  late Animation<double> _screenshotSlideAnimation;
  late Animation<double> _screenshotFadeAnimation;

  int _currentPage = 0;

  // Tour content — Jovi rebrand + Pets page. screenshotKey selects
  // which code-drawn mockup renders inside the phone frame.
  static const List<_TourPage> _pages = [
    _TourPage(
      title: 'Welcome to Jovi Health',
      subtitle: 'Healthcare for You and Your Pets',
      description:
          'Experience healthcare reimagined — one membership that covers your whole family, pets included, designed to make every health journey seamless and affordable.',
      icon: Icons.health_and_safety,
      accent: _joviCoral,
      accentSoft: _joviCoralLight,
      features: ['Affordable Plans', '24/7 Access', 'Pets Included'],
      screenshotKey: 'sign_in',
    ),
    _TourPage(
      title: 'Choose Your Membership',
      subtitle: 'Plans That Fit Your Needs',
      description:
          'Select from our range of affordable health plans. Compare coverage, deductibles, and premiums to find your perfect match.',
      icon: Icons.card_membership,
      accent: _joviMint,
      accentSoft: _joviCoral,
      features: ['Multiple Plans', 'Transparent Pricing', 'Instant Quotes'],
      screenshotKey: 'create_account',
    ),
    _TourPage(
      title: 'Digital Membership Card',
      subtitle: 'Your Coverage, Always With You',
      description:
          'Access your digital membership card instantly. No more lost cards — your coverage information is always at your fingertips.',
      icon: Icons.badge,
      accent: _joviGold,
      accentSoft: _joviCoral,
      features: ['Instant Access', 'Share with Providers', 'Download & Print'],
      screenshotKey: 'digital_card',
    ),
    _TourPage(
      title: 'Smart Dashboard',
      subtitle: 'Your Health Hub',
      description:
          'Track deductibles, view claims, check coverage status, and manage your health journey all from one intuitive dashboard.',
      icon: Icons.dashboard_customize,
      accent: _joviCoral,
      accentSoft: _joviMint,
      features: ['Real-time Updates', 'Deductible Tracking', 'Quick Actions'],
      screenshotKey: 'dashboard',
    ),
    _TourPage(
      title: 'File Claims Instantly',
      subtitle: 'Paperless & Hassle-Free',
      description:
          'Submit claims in seconds with our smart claim filing system. Upload photos, track status, and get reimbursed faster.',
      icon: Icons.receipt_long,
      accent: _joviMint,
      accentSoft: _joviGold,
      features: ['Photo Upload', 'Real-time Tracking', 'Quick Processing'],
      screenshotKey: 'file_claim',
    ),
    _TourPage(
      title: 'Request Care',
      subtitle: 'Book Appointments Seamlessly',
      description:
          'Schedule in-person or virtual appointments with ease. Choose your symptoms, pick a time, and connect with healthcare providers.',
      icon: Icons.medical_services,
      accent: _joviCoral,
      accentSoft: _joviCoralLight,
      features: [
        'Virtual & In-Person',
        'Same-Day Booking',
        'Jovi Pass Priority'
      ],
      screenshotKey: 'request_care',
    ),
    _TourPage(
      title: 'Pets Are Family Too',
      subtitle: 'Coverage for Every Member',
      description:
          'Manage pet medications, track vaccinations, check symptoms, and file pet claims — all inside the same app that covers you.',
      icon: Icons.pets,
      accent: _joviGold,
      accentSoft: _joviMint,
      features: ['Pet Claims', 'Med Tracking', 'Symptom Checker'],
    ),
    _TourPage(
      title: 'Find Nearby Clinics',
      subtitle: 'Locate Healthcare Providers',
      description:
          'Discover Jovi Health clinics near you with our clinic locator. View hours, amenities, and book appointments directly.',
      icon: Icons.location_on,
      accent: _joviMint,
      accentSoft: _joviCoral,
      features: ['Interactive Map', 'Provider Ratings', 'Direct Booking'],
      screenshotKey: 'clinic_locator',
    ),
    _TourPage(
      title: 'Get Help with Jovi',
      subtitle: 'Your AI Health Assistant',
      description:
          'Meet Jovi, your 24/7 AI health assistant. Get instant answers to health questions, coverage queries, and personalized guidance.',
      icon: Icons.support_agent,
      accent: _joviCoral,
      accentSoft: _joviMint,
      features: ['24/7 Availability', 'Instant Responses', 'Smart Guidance'],
      screenshotKey: 'get_help',
    ),
    _TourPage(
      title: 'You\'re All Set',
      subtitle: 'Start Your Health Journey',
      description:
          'You\'re ready to experience healthcare like never before. Explore every feature and take control of your family\'s health with Jovi Health.',
      icon: Icons.celebration,
      accent: _joviGold,
      accentSoft: _joviCoral,
      features: ['Full Access', 'All Features', 'Support Ready'],
    ),
  ];

  int get _totalPages => _pages.length;

  @override
  void initState() {
    super.initState();
    final reduce = _platformReduceMotion();
    _animController = AnimationController(
      vsync: this,
      duration: _Motion.enter,
    );
    _screenshotAnimController = AnimationController(
      vsync: this,
      duration: _Motion.enter,
    );
    // The ambient orbs used to drift on a 14-second loop for the life of
    // the screen (a slow oscillation Apple's accessibility guidance warns
    // against). Parked at mid-position: same composition, no motion.
    _orbController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 14),
    )..value = 0.5;

    _fadeAnimation = CurvedAnimation(
      parent: _animController,
      curve: Curves.easeOut,
    );
    _scaleAnimation = Tween<double>(begin: reduce ? 1.0 : 0.96, end: 1.0)
        .animate(
      CurvedAnimation(parent: _animController, curve: _Motion.settle),
    );
    _screenshotSlideAnimation =
        Tween<double>(begin: reduce ? 0.0 : 18.0, end: 0.0).animate(
      CurvedAnimation(
          parent: _screenshotAnimController, curve: _Motion.settle),
    );
    _screenshotFadeAnimation = CurvedAnimation(
      parent: _screenshotAnimController,
      curve: Curves.easeOut,
    );

    _animController.forward();
    _screenshotAnimController.forward();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    analyzeScreenConfiguration();
  }

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

    // Runs from didChangeDependencies (before build); no setState needed.
    _lastScreenWidth = screenWidth;
    _lastHasHinge = hasHinge;
    currentScreenType = screenType;
    layoutSettings = generateLayoutConfig(screenType, screenWidth, hasHinge);
  }

  ResponsiveConfig generateLayoutConfig(
      ScreenType type, double width, bool hasHinge) {
    switch (type) {
      case ScreenType.expanded:
        return ResponsiveConfig(
          paddingH: 16,
          paddingV: 20,
          contentMax: double.infinity,
          titleFontSize: width > 900 ? 36 : 32,
          subtitleFontSize: width > 900 ? 22 : 20,
          descriptionFontSize: width > 900 ? 18 : 16,
          iconSize: width > 900 ? 140 : 120,
          logoFontSize: width > 900 ? 26 : 24,
          buttonFontSize: width > 900 ? 20 : 18,
          screenshotWidth: width > 900 ? 280 : 240,
          screenshotHeight: width > 900 ? 560 : 480,
          wideMode: true,
          hasHinge: true,
          useTwoColumnLayout: width >= 900,
        );
      case ScreenType.large:
        return ResponsiveConfig(
          paddingH: 48,
          paddingV: 28,
          contentMax: 1200,
          titleFontSize: 34,
          subtitleFontSize: 20,
          descriptionFontSize: 17,
          iconSize: 130,
          logoFontSize: 24,
          buttonFontSize: 18,
          screenshotWidth: 260,
          screenshotHeight: 520,
          wideMode: true,
          hasHinge: false,
          useTwoColumnLayout: width >= 1100,
        );
      case ScreenType.medium:
        return ResponsiveConfig(
          paddingH: 32,
          paddingV: 24,
          contentMax: 900,
          titleFontSize: 30,
          subtitleFontSize: 19,
          descriptionFontSize: 16,
          iconSize: 115,
          logoFontSize: 22,
          buttonFontSize: 17,
          screenshotWidth: 220,
          screenshotHeight: 440,
          wideMode: true,
          hasHinge: false,
          useTwoColumnLayout: width >= 900,
        );
      case ScreenType.compact:
      default:
        return ResponsiveConfig(
          paddingH: 24,
          paddingV: 20,
          contentMax: double.infinity,
          titleFontSize: width < 360 ? 24 : 28,
          subtitleFontSize: width < 360 ? 16 : 18,
          descriptionFontSize: width < 360 ? 14 : 15,
          iconSize: width < 360 ? 90 : 100,
          logoFontSize: width < 360 ? 18 : 20,
          buttonFontSize: width < 360 ? 14 : 16,
          screenshotWidth: width < 360 ? 160 : 180,
          screenshotHeight: width < 360 ? 320 : 360,
          wideMode: false,
          hasHinge: false,
          useTwoColumnLayout: false,
        );
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
          constraints: BoxConstraints(maxWidth: layoutSettings.contentMax),
          child: child,
        ),
      );
    }
    return child;
  }

  @override
  void dispose() {
    _pageController.dispose();
    _animController.dispose();
    _screenshotAnimController.dispose();
    _orbController.dispose();
    super.dispose();
  }

  void _nextPage() {
    HapticFeedback.lightImpact();
    if (_currentPage < _totalPages - 1) {
      _pageController.nextPage(
        duration: _Motion.enter,
        curve: _Motion.settle,
      );
    } else {
      _completeTour();
    }
  }

  void _previousPage() {
    HapticFeedback.lightImpact();
    if (_currentPage > 0) {
      _pageController.previousPage(
        duration: _Motion.enter,
        curve: _Motion.settle,
      );
    }
  }

  Future<void> _completeTour() async {
    HapticFeedback.mediumImpact();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('hasSeenTour', true);
    if (!mounted) return;
    if (Navigator.of(context).canPop()) Navigator.of(context).pop();
  }

  // Skipping a tour is not destructive, so iOS convention is to just do
  // it. The old "Skip Tour?" dialog is kept below (unused) in case the
  // team prefers the interruption.
  void _skipTour() {
    HapticFeedback.lightImpact();
    _completeTour();
  }

  // ignore: unused_element
  void _skipTourWithConfirmation() {
    HapticFeedback.lightImpact();
    showDialog(
      context: context,
      builder: (dialogContext) => Dialog(
        backgroundColor: Colors.transparent,
        child: ClipRRect(
          borderRadius: BorderRadius.circular(24),
          child: BackdropFilter(
            filter: ui_dart.ImageFilter.blur(sigmaX: 18, sigmaY: 18),
            child: Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: _joviNavyLight.withOpacity(0.92),
                borderRadius: BorderRadius.circular(24),
                border: Border.all(color: Colors.white.withOpacity(0.15)),
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: _joviCoral.withOpacity(0.18),
                          borderRadius: BorderRadius.circular(14),
                        ),
                        child: const Icon(Icons.fast_forward,
                            color: _joviCoral, size: 22),
                      ),
                      const SizedBox(width: 12),
                      const Text(
                        'Skip Tour?',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 20,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  Text(
                    'You can always come back to the tour later from Settings.',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.75),
                      fontSize: 15,
                      height: 1.45,
                    ),
                  ),
                  const SizedBox(height: 24),
                  Row(
                    children: [
                      Expanded(
                        child: TextButton(
                          onPressed: () => Navigator.of(dialogContext).pop(),
                          style: TextButton.styleFrom(
                            padding: const EdgeInsets.symmetric(vertical: 14),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(14),
                              side: BorderSide(
                                  color: Colors.white.withOpacity(0.25)),
                            ),
                          ),
                          child: const Text(
                            'Continue Tour',
                            style: TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: ElevatedButton(
                          onPressed: () {
                            Navigator.of(dialogContext).pop();
                            _completeTour();
                          },
                          style: ElevatedButton.styleFrom(
                            backgroundColor: _joviCoral,
                            foregroundColor: Colors.white,
                            elevation: 0,
                            padding: const EdgeInsets.symmetric(vertical: 14),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(14),
                            ),
                          ),
                          child: const Text('Skip',
                              style: TextStyle(fontWeight: FontWeight.w700)),
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
  }

  // ── Glass helpers ──────────────────────────────────────────

  Widget _glassPanel({
    required Widget child,
    EdgeInsets padding = const EdgeInsets.all(20),
    double radius = 24,
    double opacity = 0.08,
  }) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(radius),
      child: RepaintBoundary(
        child: Container(
          padding: padding,
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(opacity + 0.02),
            borderRadius: BorderRadius.circular(radius),
            border: Border.all(color: Colors.white.withOpacity(0.14)),
          ),
          child: child,
        ),
      ),
    );
  }

  Widget _backgroundOrbs(Size size) {
    return AnimatedBuilder(
      animation: _orbController,
      builder: (context, _) {
        final t = _orbController.value;
        return IgnorePointer(
          child: Stack(
            children: [
              Positioned(
                top: -80 + (t * 40),
                right: -60,
                child: _orb(_joviCoral.withOpacity(0.22), 240),
              ),
              Positioned(
                bottom: size.height * 0.22 - (t * 30),
                left: -90,
                child: _orb(_joviMint.withOpacity(0.14), 260),
              ),
              Positioned(
                bottom: -100 + (t * 24),
                right: -40,
                child: _orb(_joviGold.withOpacity(0.10), 200),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _orb(Color color, double size) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: RadialGradient(
          colors: [color, color.withOpacity(0.0)],
        ),
      ),
    );
  }

  // ── Page content ───────────────────────────────────────────

  Widget _buildFeatureChip(String label, Color accent) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration: BoxDecoration(
        color: accent.withOpacity(0.14),
        borderRadius: BorderRadius.circular(30),
        border: Border.all(color: accent.withOpacity(0.35)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.check_circle, size: 14, color: accent),
          const SizedBox(width: 6),
          Text(
            label,
            style: TextStyle(
              color: Colors.white.withOpacity(0.92),
              fontSize: layoutSettings.descriptionFontSize - 2,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildScreenshot(_TourPage page) {
    final mockup = _buildMockupContent(page);

    return AnimatedBuilder(
      animation: _screenshotAnimController,
      builder: (context, child) {
        return Transform.translate(
          offset: Offset(0, _screenshotSlideAnimation.value),
          child: Opacity(
            opacity: _screenshotFadeAnimation.value,
            child: child,
          ),
        );
      },
      child: mockup != null
          ? Container(
              width: layoutSettings.screenshotWidth,
              height: layoutSettings.screenshotHeight,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(32),
                border: Border.all(
                  color: Colors.white.withOpacity(0.22),
                  width: 3,
                ),
                boxShadow: [
                  BoxShadow(
                    color: page.accent.withOpacity(0.35),
                    blurRadius: 40,
                    spreadRadius: -6,
                    offset: const Offset(0, 18),
                  ),
                  BoxShadow(
                    color: Colors.black.withOpacity(0.4),
                    blurRadius: 24,
                    offset: const Offset(0, 12),
                  ),
                ],
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(29),
                child: Container(
                  decoration: const BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [_joviNavyLight, _joviNavyDark],
                    ),
                  ),
                  // Mockups are designed on a fixed 180x360 canvas and
                  // scaled to whatever the responsive config asks for.
                  child: FittedBox(
                    fit: BoxFit.cover,
                    child: SizedBox(
                      width: 180,
                      height: 360,
                      child: Padding(
                        padding: const EdgeInsets.all(14),
                        child: mockup,
                      ),
                    ),
                  ),
                ),
              ),
            )
          : _buildHeroIcon(page),
    );
  }

  // ── Illustrated mockups (replace screenshots) ──────────────

  Widget? _buildMockupContent(_TourPage page) {
    switch (page.screenshotKey) {
      case 'sign_in':
        return _mockWelcome(page.accent);
      case 'create_account':
        return _mockPlans(page.accent);
      case 'digital_card':
        return _mockCard(page.accent);
      case 'dashboard':
        return _mockDashboard(page.accent);
      case 'file_claim':
        return _mockClaim(page.accent);
      case 'request_care':
        return _mockBooking(page.accent);
      case 'clinic_locator':
        return _mockLocator(page.accent);
      case 'get_help':
        return _mockChat(page.accent);
      default:
        return null; // pages without a key use the hero icon
    }
  }

  // Small building blocks -------------------------------------

  Widget _mockBar({
    double width = double.infinity,
    double height = 8,
    Color? color,
    double radius = 4,
  }) {
    return Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: color ?? Colors.white.withOpacity(0.16),
        borderRadius: BorderRadius.circular(radius),
      ),
    );
  }

  Widget _mockTile({required Widget child, Color? tint, double height = 46}) {
    return Container(
      height: height,
      padding: const EdgeInsets.symmetric(horizontal: 10),
      decoration: BoxDecoration(
        color: (tint ?? Colors.white).withOpacity(tint == null ? 0.07 : 0.14),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: (tint ?? Colors.white).withOpacity(tint == null ? 0.10 : 0.30),
        ),
      ),
      child: child,
    );
  }

  Widget _mockDot(Color color, {double size = 20, IconData? icon}) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: color.withOpacity(0.22),
        shape: BoxShape.circle,
        border: Border.all(color: color.withOpacity(0.5)),
      ),
      child: icon != null ? Icon(icon, size: size * 0.55, color: color) : null,
    );
  }

  // Page mockups ----------------------------------------------

  Widget _mockWelcome(Color accent) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Container(
          width: 52,
          height: 52,
          decoration: BoxDecoration(
            gradient: LinearGradient(colors: [accent, _joviCoralLight]),
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(color: accent.withOpacity(0.5), blurRadius: 18),
            ],
          ),
          child: const Icon(Icons.favorite, color: Colors.white, size: 26),
        ),
        const SizedBox(height: 12),
        _mockBar(width: 90, height: 10),
        const SizedBox(height: 6),
        _mockBar(width: 60, height: 6),
        const SizedBox(height: 22),
        _mockTile(
          child: Row(children: [
            Icon(Icons.mail_outline,
                size: 14, color: Colors.white.withOpacity(0.4)),
            const SizedBox(width: 8),
            _mockBar(width: 70, height: 6),
          ]),
        ),
        const SizedBox(height: 8),
        _mockTile(
          child: Row(children: [
            Icon(Icons.lock_outline,
                size: 14, color: Colors.white.withOpacity(0.4)),
            const SizedBox(width: 8),
            _mockBar(width: 50, height: 6),
          ]),
        ),
        const SizedBox(height: 14),
        Container(
          height: 38,
          decoration: BoxDecoration(
            gradient: LinearGradient(colors: [accent, _joviCoralLight]),
            borderRadius: BorderRadius.circular(12),
          ),
          child: const Center(
            child: Text('Sign In',
                style: TextStyle(
                    color: Colors.white,
                    fontSize: 11,
                    fontWeight: FontWeight.w800)),
          ),
        ),
      ],
    );
  }

  Widget _mockPlans(Color accent) {
    Widget plan(String price, bool featured) {
      return Expanded(
        child: Container(
          margin: const EdgeInsets.symmetric(horizontal: 3),
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: featured
                ? _joviCoral.withOpacity(0.16)
                : Colors.white.withOpacity(0.06),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: featured
                  ? _joviCoral.withOpacity(0.6)
                  : Colors.white.withOpacity(0.12),
              width: featured ? 1.5 : 1,
            ),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              _mockBar(width: 26, height: 5),
              const SizedBox(height: 6),
              Text(price,
                  style: TextStyle(
                      color: featured ? _joviCoral : Colors.white,
                      fontSize: 12,
                      fontWeight: FontWeight.w800)),
              const SizedBox(height: 6),
              _mockBar(height: 4),
              const SizedBox(height: 3),
              _mockBar(height: 4, width: 28),
            ],
          ),
        ),
      );
    }

    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        _mockBar(width: 100, height: 10),
        const SizedBox(height: 4),
        _mockBar(width: 70, height: 6),
        const SizedBox(height: 18),
        Row(children: [
          plan('\$49', false),
          plan('\$89', true),
          plan('\$129', false)
        ]),
        const SizedBox(height: 14),
        Row(
          children: List.generate(3, (i) {
            return Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 6),
                child: Row(children: [
                  const Icon(Icons.check_circle, size: 10, color: _joviMint),
                  const SizedBox(width: 4),
                  Expanded(child: _mockBar(height: 4)),
                ]),
              ),
            );
          }),
        ),
        const SizedBox(height: 16),
        Container(
          height: 34,
          width: 120,
          decoration: BoxDecoration(
            gradient:
                const LinearGradient(colors: [_joviCoral, _joviCoralLight]),
            borderRadius: BorderRadius.circular(10),
          ),
          child: const Center(
            child: Text('Get Quote',
                style: TextStyle(
                    color: Colors.white,
                    fontSize: 10,
                    fontWeight: FontWeight.w800)),
          ),
        ),
      ],
    );
  }

  Widget _mockCard(Color accent) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Container(
          height: 96,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [_joviNavyLight, _joviNavy],
            ),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: _joviGold.withOpacity(0.5)),
            boxShadow: [
              BoxShadow(color: _joviGold.withOpacity(0.25), blurRadius: 16),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('JOVI',
                      style: TextStyle(
                          color: _joviCoral,
                          fontSize: 11,
                          fontWeight: FontWeight.w900,
                          letterSpacing: 1.5)),
                  Icon(Icons.wifi, size: 12, color: _joviGold.withOpacity(0.8)),
                ],
              ),
              const Spacer(),
              _mockBar(
                  width: 80, height: 7, color: Colors.white.withOpacity(0.6)),
              const SizedBox(height: 5),
              Row(
                children: [
                  _mockBar(width: 42, height: 5),
                  const SizedBox(width: 8),
                  _mockBar(width: 30, height: 5),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            _mockDot(_joviMint, size: 30, icon: Icons.share),
            const SizedBox(width: 14),
            _mockDot(_joviGold, size: 30, icon: Icons.download),
            const SizedBox(width: 14),
            _mockDot(_joviCoral, size: 30, icon: Icons.qr_code),
          ],
        ),
        const SizedBox(height: 12),
        _mockBar(width: 90, height: 5),
      ],
    );
  }

  Widget _mockDashboard(Color accent) {
    return Column(
      children: [
        Row(
          children: [
            _mockDot(_joviCoral, size: 26, icon: Icons.person),
            const SizedBox(width: 8),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _mockBar(width: 55, height: 6),
                const SizedBox(height: 4),
                _mockBar(width: 35, height: 4),
              ],
            ),
          ],
        ),
        const SizedBox(height: 16),
        // Deductible ring
        SizedBox(
          width: 84,
          height: 84,
          child: Stack(
            alignment: Alignment.center,
            children: [
              SizedBox(
                width: 84,
                height: 84,
                child: CircularProgressIndicator(
                  value: 0.65,
                  strokeWidth: 7,
                  backgroundColor: Colors.white.withOpacity(0.10),
                  valueColor: const AlwaysStoppedAnimation<Color>(_joviMint),
                ),
              ),
              const Text('65%',
                  style: TextStyle(
                      color: Colors.white,
                      fontSize: 15,
                      fontWeight: FontWeight.w800)),
            ],
          ),
        ),
        const SizedBox(height: 6),
        _mockBar(width: 70, height: 5),
        const SizedBox(height: 14),
        Row(
          children: [
            Expanded(
              child: _mockTile(
                tint: _joviCoral,
                height: 44,
                child: Row(children: [
                  const Icon(Icons.receipt_long, size: 13, color: _joviCoral),
                  const SizedBox(width: 6),
                  Expanded(child: _mockBar(height: 5)),
                ]),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _mockTile(
                tint: _joviGold,
                height: 44,
                child: Row(children: [
                  const Icon(Icons.pets, size: 13, color: _joviGold),
                  const SizedBox(width: 6),
                  Expanded(child: _mockBar(height: 5)),
                ]),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        _mockTile(
          height: 44,
          child: Row(children: [
            const Icon(Icons.medical_services, size: 13, color: _joviMint),
            const SizedBox(width: 6),
            Expanded(child: _mockBar(height: 5)),
            Icon(Icons.chevron_right,
                size: 14, color: Colors.white.withOpacity(0.4)),
          ]),
        ),
      ],
    );
  }

  Widget _mockClaim(Color accent) {
    Widget step(bool done, bool active) {
      return Expanded(
        child: Container(
          height: 5,
          margin: const EdgeInsets.symmetric(horizontal: 2),
          decoration: BoxDecoration(
            color: done
                ? _joviMint
                : active
                    ? _joviMint.withOpacity(0.5)
                    : Colors.white.withOpacity(0.12),
            borderRadius: BorderRadius.circular(3),
          ),
        ),
      );
    }

    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Row(children: [
          step(true, false),
          step(true, false),
          step(false, true)
        ]),
        const SizedBox(height: 18),
        // Upload dropzone
        Container(
          height: 90,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: _joviMint.withOpacity(0.5),
              width: 1.5,
            ),
            color: _joviMint.withOpacity(0.06),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.cloud_upload_outlined,
                  color: _joviMint, size: 26),
              const SizedBox(height: 6),
              _mockBar(width: 70, height: 5),
            ],
          ),
        ),
        const SizedBox(height: 12),
        _mockTile(
          height: 40,
          child: Row(children: [
            const Icon(Icons.receipt, size: 13, color: _joviGold),
            const SizedBox(width: 8),
            Expanded(child: _mockBar(height: 5)),
            const Text('\$120',
                style: TextStyle(
                    color: Colors.white,
                    fontSize: 10,
                    fontWeight: FontWeight.w700)),
          ]),
        ),
        const SizedBox(height: 14),
        Container(
          height: 36,
          width: double.infinity,
          decoration: BoxDecoration(
            gradient:
                const LinearGradient(colors: [_joviMint, Color(0xFF00B894)]),
            borderRadius: BorderRadius.circular(11),
          ),
          child: const Center(
            child: Text('Submit Claim',
                style: TextStyle(
                    color: Colors.white,
                    fontSize: 10,
                    fontWeight: FontWeight.w800)),
          ),
        ),
      ],
    );
  }

  Widget _mockBooking(Color accent) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        _mockBar(width: 80, height: 8),
        const SizedBox(height: 14),
        // Mini calendar
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.06),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: Colors.white.withOpacity(0.10)),
          ),
          child: Column(
            children: List.generate(3, (row) {
              return Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: List.generate(6, (col) {
                    final selected = row == 1 && col == 3;
                    return Container(
                      width: 16,
                      height: 16,
                      decoration: BoxDecoration(
                        color: selected
                            ? _joviCoral
                            : Colors.white.withOpacity(0.10),
                        shape: BoxShape.circle,
                        boxShadow: selected
                            ? [
                                BoxShadow(
                                    color: _joviCoral.withOpacity(0.6),
                                    blurRadius: 8),
                              ]
                            : null,
                      ),
                    );
                  }),
                ),
              );
            }),
          ),
        ),
        const SizedBox(height: 12),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: ['9:00', '10:30', '2:15'].asMap().entries.map((e) {
            final selected = e.key == 1;
            return Container(
              margin: const EdgeInsets.symmetric(horizontal: 4),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: selected
                    ? _joviCoral.withOpacity(0.2)
                    : Colors.white.withOpacity(0.07),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: selected ? _joviCoral : Colors.white.withOpacity(0.14),
                ),
              ),
              child: Text(e.value,
                  style: TextStyle(
                      color: selected ? _joviCoral : Colors.white70,
                      fontSize: 9,
                      fontWeight: FontWeight.w700)),
            );
          }).toList(),
        ),
        const SizedBox(height: 14),
        Container(
          height: 36,
          width: double.infinity,
          decoration: BoxDecoration(
            gradient:
                const LinearGradient(colors: [_joviCoral, _joviCoralLight]),
            borderRadius: BorderRadius.circular(11),
          ),
          child: const Center(
            child: Text('Book Appointment',
                style: TextStyle(
                    color: Colors.white,
                    fontSize: 10,
                    fontWeight: FontWeight.w800)),
          ),
        ),
      ],
    );
  }

  Widget _mockLocator(Color accent) {
    return Column(
      children: [
        // Stylized map
        Expanded(
          child: Container(
            width: double.infinity,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14),
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  _joviMint.withOpacity(0.12),
                  _joviNavyLight.withOpacity(0.6),
                ],
              ),
              border: Border.all(color: Colors.white.withOpacity(0.12)),
            ),
            child: Stack(
              children: [
                // "Roads"
                Positioned(
                    top: 30,
                    left: 0,
                    right: 0,
                    child: _mockBar(
                        height: 2,
                        radius: 0,
                        color: Colors.white.withOpacity(0.08))),
                Positioned(
                    top: 80,
                    left: 0,
                    right: 0,
                    child: _mockBar(
                        height: 2,
                        radius: 0,
                        color: Colors.white.withOpacity(0.08))),
                Positioned(
                    top: 0,
                    bottom: 0,
                    left: 60,
                    child: Container(
                        width: 2, color: Colors.white.withOpacity(0.08))),
                // Pins
                const Positioned(
                    top: 20,
                    left: 40,
                    child:
                        Icon(Icons.location_on, color: _joviCoral, size: 20)),
                const Positioned(
                    top: 64,
                    right: 34,
                    child: Icon(Icons.location_on, color: _joviMint, size: 16)),
                const Positioned(
                    bottom: 18,
                    left: 76,
                    child: Icon(Icons.location_on, color: _joviGold, size: 16)),
              ],
            ),
          ),
        ),
        const SizedBox(height: 10),
        _mockTile(
          tint: _joviCoral,
          height: 42,
          child: Row(children: [
            const Icon(Icons.local_hospital, size: 13, color: _joviCoral),
            const SizedBox(width: 8),
            Expanded(child: _mockBar(height: 5)),
            const Icon(Icons.star, size: 11, color: _joviGold),
            const Text(' 4.9',
                style: TextStyle(color: Colors.white70, fontSize: 9)),
          ]),
        ),
        const SizedBox(height: 6),
        _mockTile(
          height: 42,
          child: Row(children: [
            Icon(Icons.local_hospital,
                size: 13, color: Colors.white.withOpacity(0.5)),
            const SizedBox(width: 8),
            Expanded(child: _mockBar(height: 5)),
            const Icon(Icons.star, size: 11, color: _joviGold),
            const Text(' 4.7',
                style: TextStyle(color: Colors.white70, fontSize: 9)),
          ]),
        ),
      ],
    );
  }

  Widget _mockChat(Color accent) {
    Widget bubble(bool fromJovi, double w) {
      return Align(
        alignment: fromJovi ? Alignment.centerLeft : Alignment.centerRight,
        child: Container(
          width: w,
          padding: const EdgeInsets.all(9),
          margin: const EdgeInsets.only(bottom: 8),
          decoration: BoxDecoration(
            color: fromJovi
                ? _joviCoral.withOpacity(0.16)
                : _joviMint.withOpacity(0.14),
            borderRadius: BorderRadius.only(
              topLeft: const Radius.circular(12),
              topRight: const Radius.circular(12),
              bottomLeft: Radius.circular(fromJovi ? 3 : 12),
              bottomRight: Radius.circular(fromJovi ? 12 : 3),
            ),
            border: Border.all(
              color: (fromJovi ? _joviCoral : _joviMint).withOpacity(0.3),
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _mockBar(height: 4),
              const SizedBox(height: 3),
              _mockBar(height: 4, width: w * 0.6),
            ],
          ),
        ),
      );
    }

    return Column(
      children: [
        Row(
          children: [
            Container(
              width: 26,
              height: 26,
              decoration: BoxDecoration(
                gradient:
                    const LinearGradient(colors: [_joviCoral, _joviCoralLight]),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.support_agent,
                  color: Colors.white, size: 14),
            ),
            const SizedBox(width: 8),
            const Text('Jovi',
                style: TextStyle(
                    color: Colors.white,
                    fontSize: 11,
                    fontWeight: FontWeight.w800)),
            const SizedBox(width: 5),
            Container(
              width: 6,
              height: 6,
              decoration:
                  const BoxDecoration(color: _joviMint, shape: BoxShape.circle),
            ),
          ],
        ),
        const SizedBox(height: 14),
        bubble(true, 110),
        bubble(false, 90),
        bubble(true, 120),
        const Spacer(),
        _mockTile(
          height: 36,
          child: Row(children: [
            Expanded(child: _mockBar(height: 5)),
            const SizedBox(width: 8),
            const Icon(Icons.send, size: 13, color: _joviCoral),
          ]),
        ),
      ],
    );
  }

  Widget _buildHeroIcon(_TourPage page) {
    return Container(
      width: layoutSettings.iconSize + 60,
      height: layoutSettings.iconSize + 60,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            page.accent.withOpacity(0.28),
            page.accentSoft.withOpacity(0.10),
          ],
        ),
        border: Border.all(color: page.accent.withOpacity(0.4), width: 1.5),
        boxShadow: [
          BoxShadow(
            color: page.accent.withOpacity(0.3),
            blurRadius: 40,
            spreadRadius: -4,
          ),
        ],
      ),
      child: Icon(
        page.icon,
        size: layoutSettings.iconSize * 0.62,
        color: Colors.white,
      ),
    );
  }

  Widget _buildTextBlock(_TourPage page, {bool centered = true}) {
    final align = centered ? TextAlign.center : TextAlign.left;
    final cross =
        centered ? CrossAxisAlignment.center : CrossAxisAlignment.start;
    final wrapAlign = centered ? WrapAlignment.center : WrapAlignment.start;

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: cross,
      children: [
        // Subtitle eyebrow
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
          decoration: BoxDecoration(
            color: page.accent.withOpacity(0.14),
            borderRadius: BorderRadius.circular(20),
          ),
          child: Text(
            page.subtitle,
            textAlign: align,
            style: TextStyle(
              color: page.accent,
              fontSize: layoutSettings.descriptionFontSize - 2,
              fontWeight: FontWeight.w700,
              letterSpacing: -0.1,
            ),
          ),
        ),
        const SizedBox(height: 16),
        Text(
          page.title,
          textAlign: align,
          style: TextStyle(
            color: Colors.white,
            fontSize: layoutSettings.titleFontSize,
            fontWeight: FontWeight.w700,
            height: 1.15,
            letterSpacing: -0.8,
          ),
        ),
        const SizedBox(height: 14),
        Text(
          page.description,
          textAlign: align,
          style: TextStyle(
            color: Colors.white.withOpacity(0.72),
            fontSize: layoutSettings.descriptionFontSize,
            height: 1.55,
          ),
        ),
        const SizedBox(height: 20),
        Wrap(
          alignment: wrapAlign,
          spacing: 10,
          runSpacing: 10,
          children: page.features
              .map((f) => _buildFeatureChip(f, page.accent))
              .toList(),
        ),
      ],
    );
  }

  Widget _buildPage(_TourPage page) {
    final content = FadeTransition(
      opacity: _fadeAnimation,
      child: ScaleTransition(
        scale: _scaleAnimation,
        child: layoutSettings.useTwoColumnLayout
            // Wide: mockup left, text right
            ? Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  _buildScreenshot(page),
                  SizedBox(width: layoutSettings.paddingH * 1.5),
                  Flexible(
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 480),
                      child: _glassPanel(
                        padding: const EdgeInsets.all(28),
                        child: _buildTextBlock(page, centered: false),
                      ),
                    ),
                  ),
                ],
              )
            // Compact: stacked
            : Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Flexible(flex: 5, child: _buildScreenshot(page)),
                  SizedBox(height: layoutSettings.paddingV),
                  Flexible(
                    flex: 4,
                    child: SingleChildScrollView(
                      physics: const BouncingScrollPhysics(),
                      child: _buildTextBlock(page),
                    ),
                  ),
                ],
              ),
      ),
    );

    return Padding(
      padding: EdgeInsets.symmetric(
        horizontal: layoutSettings.paddingH,
        vertical: layoutSettings.paddingV * 0.5,
      ),
      child: content,
    );
  }

  // ── Build ──────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final screenSize = MediaQuery.of(context).size;

    return wrapWithConstraints(
      child: Scaffold(
        backgroundColor: _joviNavyDark,
        body: Container(
          width: screenSize.width,
          height: screenSize.height,
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [_joviNavyDark, _joviNavy, _joviNavyDark],
              stops: [0.0, 0.5, 1.0],
            ),
          ),
          child: Stack(
            children: [
              _backgroundOrbs(screenSize),
              SafeArea(
                child: Center(
                  child: Container(
                    constraints: BoxConstraints(
                      maxWidth: layoutSettings.wideMode
                          ? layoutSettings.contentMax
                          : double.infinity,
                    ),
                    child: Column(
                      children: [
                        // Header
                        Padding(
                          padding: EdgeInsets.symmetric(
                            horizontal: layoutSettings.paddingH,
                            vertical: layoutSettings.paddingV * 0.8,
                          ),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Row(
                                children: [
                                  ShaderMask(
                                    shaderCallback: (bounds) =>
                                        const LinearGradient(
                                      colors: [_joviCoral, _joviCoralLight],
                                    ).createShader(bounds),
                                    child: Text(
                                      'JOVI',
                                      style: TextStyle(
                                        fontSize: layoutSettings.logoFontSize,
                                        fontWeight: FontWeight.w800,
                                        color: Colors.white,
                                        letterSpacing: 1.0,
                                      ),
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  Container(
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 10, vertical: 4),
                                    decoration: BoxDecoration(
                                      color: Colors.white.withOpacity(0.08),
                                      borderRadius: BorderRadius.circular(20),
                                      border: Border.all(
                                          color:
                                              Colors.white.withOpacity(0.14)),
                                    ),
                                    child: Text(
                                      '${_currentPage + 1} / $_totalPages',
                                      style: TextStyle(
                                        color: Colors.white.withOpacity(0.7),
                                        fontSize:
                                            layoutSettings.descriptionFontSize -
                                                3,
                                        fontWeight: FontWeight.w700,
                                        letterSpacing: 0.5,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                              if (_currentPage < _totalPages - 1)
                                TextButton(
                                  onPressed: _skipTour,
                                  child: Text(
                                    'Skip',
                                    style: TextStyle(
                                      fontSize:
                                          layoutSettings.descriptionFontSize,
                                      fontWeight: FontWeight.w600,
                                      color: Colors.white.withOpacity(0.6),
                                    ),
                                  ),
                                ),
                            ],
                          ),
                        ),

                        // Pages
                        Expanded(
                          child: PageView(
                            controller: _pageController,
                            onPageChanged: (index) {
                              setState(() => _currentPage = index);
                              _animController.forward(from: 0);
                              _screenshotAnimController.forward(from: 0);
                              HapticFeedback.selectionClick();
                            },
                            children: _pages.map(_buildPage).toList(),
                          ),
                        ),

                        // Bottom nav — glass bar
                        ClipRRect(
                          borderRadius: const BorderRadius.only(
                            topLeft: Radius.circular(28),
                            topRight: Radius.circular(28),
                          ),
                          child: BackdropFilter(
                            filter: ui_dart.ImageFilter.blur(
                                sigmaX: 16, sigmaY: 16),
                            child: Container(
                              width: double.infinity,
                              padding: EdgeInsets.all(layoutSettings.paddingH),
                              decoration: BoxDecoration(
                                color: Colors.white.withOpacity(0.06),
                                border: Border(
                                  top: BorderSide(
                                      color: Colors.white.withOpacity(0.12)),
                                ),
                              ),
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  // Page indicators
                                  Row(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children:
                                        List.generate(_totalPages, (index) {
                                      final active = _currentPage == index;
                                      return AnimatedContainer(
                                        duration: _Motion.select,
                                        curve: _Motion.settle,
                                        width: active
                                            ? (layoutSettings.wideMode
                                                ? 28
                                                : 24)
                                            : (layoutSettings.wideMode
                                                ? 10
                                                : 8),
                                        height:
                                            layoutSettings.wideMode ? 10 : 8,
                                        margin: EdgeInsets.symmetric(
                                            horizontal: layoutSettings.wideMode
                                                ? 5
                                                : 4),
                                        decoration: BoxDecoration(
                                          color: active
                                              ? _joviCoral
                                              : Colors.white.withOpacity(0.18),
                                          borderRadius:
                                              BorderRadius.circular(5),
                                          boxShadow: active
                                              ? [
                                                  BoxShadow(
                                                    color: _joviCoral
                                                        .withOpacity(0.5),
                                                    blurRadius: 10,
                                                  ),
                                                ]
                                              : null,
                                        ),
                                      );
                                    }),
                                  ),
                                  SizedBox(
                                      height:
                                          layoutSettings.wideMode ? 28 : 22),

                                  // Buttons
                                  ConstrainedBox(
                                    constraints: BoxConstraints(
                                      maxWidth: layoutSettings.wideMode
                                          ? 500
                                          : double.infinity,
                                    ),
                                    child: Row(
                                      children: [
                                        if (_currentPage > 0) ...[
                                          Expanded(
                                            child: _Pressable(
                                                feedbackOnly: true,
                                                child: OutlinedButton(
                                              onPressed: _previousPage,
                                              style: OutlinedButton.styleFrom(
                                                foregroundColor: Colors.white,
                                                padding: EdgeInsets.symmetric(
                                                  vertical:
                                                      layoutSettings.wideMode
                                                          ? 18
                                                          : 16,
                                                ),
                                                shape: RoundedRectangleBorder(
                                                  borderRadius:
                                                      BorderRadius.circular(14),
                                                ),
                                                side: BorderSide(
                                                  color: Colors.white
                                                      .withOpacity(0.28),
                                                ),
                                              ),
                                              child: Text(
                                                'Back',
                                                style: TextStyle(
                                                  fontSize: layoutSettings
                                                      .buttonFontSize,
                                                  fontWeight: FontWeight.w600,
                                                ),
                                              ),
                                            )),
                                          ),
                                          SizedBox(
                                              width: layoutSettings.wideMode
                                                  ? 20
                                                  : 16),
                                        ],
                                        Expanded(
                                          flex: _currentPage == 0 ? 1 : 2,
                                          child: _Pressable(
                                              feedbackOnly: true,
                                              child: Container(
                                            decoration: BoxDecoration(
                                              gradient: const LinearGradient(
                                                colors: [
                                                  _joviCoral,
                                                  _joviCoralLight
                                                ],
                                              ),
                                              borderRadius:
                                                  BorderRadius.circular(14),
                                              boxShadow: [
                                                BoxShadow(
                                                  color: _joviCoral
                                                      .withOpacity(0.4),
                                                  blurRadius: 16,
                                                  offset: const Offset(0, 6),
                                                ),
                                              ],
                                            ),
                                            child: ElevatedButton(
                                              onPressed: _nextPage,
                                              style: ElevatedButton.styleFrom(
                                                backgroundColor:
                                                    Colors.transparent,
                                                foregroundColor: Colors.white,
                                                shadowColor: Colors.transparent,
                                                elevation: 0,
                                                padding: EdgeInsets.symmetric(
                                                  vertical:
                                                      layoutSettings.wideMode
                                                          ? 18
                                                          : 16,
                                                ),
                                                shape: RoundedRectangleBorder(
                                                  borderRadius:
                                                      BorderRadius.circular(14),
                                                ),
                                              ),
                                              child: Row(
                                                mainAxisAlignment:
                                                    MainAxisAlignment.center,
                                                children: [
                                                  Text(
                                                    _currentPage ==
                                                            _totalPages - 1
                                                        ? 'Get Started'
                                                        : 'Next',
                                                    style: TextStyle(
                                                      fontSize: layoutSettings
                                                          .buttonFontSize,
                                                      fontWeight:
                                                          FontWeight.w600,
                                                      letterSpacing: -0.2,
                                                    ),
                                                  ),
                                                  const SizedBox(width: 6),
                                                  Icon(
                                                    _currentPage ==
                                                            _totalPages - 1
                                                        ? Icons.celebration
                                                        : Icons
                                                            .arrow_forward_rounded,
                                                    size: 18,
                                                  ),
                                                ],
                                              ),
                                            ),
                                          )),
                                        ),
                                      ],
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
              ),
            ],
          ),
        ),
      ),
    );
  }
}
