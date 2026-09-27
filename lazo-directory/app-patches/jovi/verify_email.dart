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

// Jovi Health Rebrand - April 2026
// Refined 2026-09-22: silent background verification poll, spinner only on
// manual check, critically damped motion, navy toasts.
import '/auth/firebase_auth/auth_util.dart';
import '/flutter_flow/flutter_flow_widgets.dart';
import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'dart:async';
import 'dart:ui' as ui_dart;

/// Enumerations for device categorization
enum ScreenType { compact, medium, expanded, large }

/// Configuration object for responsive layouts
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

// Jovi Health Brand Colors
const Color joviCoral = Color(0xFFFF6B4A);
const Color joviCoralLight = Color(0xFFFF8F73);
const Color joviNavy = Color(0xFF1A2744);
const Color joviNavyDark = Color(0xFF0F1A2E);
const Color joviNavyLight = Color(0xFF243352);
const Color joviWarmWhite = Color(0xFFFFF8F5);
const Color joviMint = Color(0xFF00D4AA);
const Color joviMintDark = Color(0xFF00B894);
const Color joviGold = Color(0xFFFFD166);
const Color joviSoftStone = Color(0xFFF0EFEB);

// ─── Motion (Apple "response" values; critically damped, no overshoot) ──
class _Motion {
  static const Duration pressIn = Duration(milliseconds: 90);
  static const Duration pressOut = Duration(milliseconds: 260);
  static const Duration select = Duration(milliseconds: 220);
  static const Duration enter = Duration(milliseconds: 420);
  static const Curve settle = Curves.easeOutCubic;
}

const Color _joviError = Color(0xFFEF4444);

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
  final String? semanticsLabel;

  const _Pressable({
    Key? key,
    required this.child,
    this.onTap,
    this.enabled = true,
    this.feedbackOnly = false,
    this.pressedScale = 0.97,
    this.semanticsLabel,
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
      label: widget.semanticsLabel,
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
    backgroundColor: joviNavyLight,
    elevation: 0,
    behavior: SnackBarBehavior.floating,
    margin: const EdgeInsets.fromLTRB(16, 0, 16, 24),
    shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: BorderSide(color: accent.withOpacity(0.35))),
  );
}

class VerifyEmailWidget extends StatefulWidget {
  const VerifyEmailWidget({Key? key, this.width, this.height})
      : super(key: key);
  final double? width;
  final double? height;

  @override
  _VerifyEmailWidgetState createState() => _VerifyEmailWidgetState();
}

class _VerifyEmailWidgetState extends State<VerifyEmailWidget>
    with TickerProviderStateMixin {
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
      hasHinge: false);

  bool get _reduceMotion =>
      MediaQuery.maybeOf(context)?.disableAnimations ?? false;

  void _toast(String message,
      {required Color accent, IconData? icon, Duration? duration}) {
    if (!mounted) return;
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(
        _joviToast(message, accent: accent, icon: icon, duration: duration));
  }

  void _toastError(String message) => _toast(message,
      accent: _joviError,
      icon: CupertinoIcons.exclamationmark_circle,
      duration: const Duration(seconds: 4));

  void _toastWarn(String message) => _toast(message,
      accent: joviGold,
      icon: CupertinoIcons.exclamationmark_triangle,
      duration: const Duration(seconds: 4));

  void _toastSuccess(String message) =>
      _toast(message, accent: joviMint, icon: CupertinoIcons.checkmark_circle);

  void _toastInfo(String message) => _toast(message,
      accent: joviCoral,
      icon: CupertinoIcons.info_circle,
      duration: const Duration(seconds: 4));

  double? _lastScreenWidth;
  bool? _lastHasHinge;

  late AnimationController _fadeController;
  late AnimationController _scaleController;
  late AnimationController _rotationController;
  late Animation<double> _fadeAnimation;
  late Animation<double> _scaleAnimation;
  late Animation<double> _rotationAnimation;

  bool isResending = false;
  bool isChecking = false;
  int resendCooldown = 0;
  Timer? _cooldownTimer;
  Timer? _verificationCheckTimer;

  // Jovi colors
  final Color primaryColor = joviCoral;
  final Color secondaryColor = joviCoralLight;
  final Color accentColor = joviCoralLight;
  final Color successColor = joviMint;
  final Color warningColor = const Color(0xFFFF9800);
  final Color errorColor = const Color(0xFFF44336);
  final Color textPrimary = joviNavy;
  final Color textSecondary = const Color(0xFF7F8C8D);

  @override
  void initState() {
    super.initState();
    _fadeController =
        AnimationController(duration: _Motion.enter, vsync: this);
    _scaleController =
        AnimationController(duration: _Motion.enter, vsync: this);
    // Spins only while a manual check is running (see _manualCheckVerification).
    _rotationController =
        AnimationController(duration: const Duration(seconds: 2), vsync: this);

    _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
        CurvedAnimation(parent: _fadeController, curve: Curves.easeOut));
    _scaleAnimation = Tween<double>(begin: 0.92, end: 1.0).animate(
        CurvedAnimation(parent: _scaleController, curve: _Motion.settle));
    _rotationAnimation = Tween<double>(begin: 0, end: 2 * 3.14159).animate(
        CurvedAnimation(parent: _rotationController, curve: Curves.linear));

    _fadeController.forward();
    _scaleController.forward();
    _startVerificationCheck();
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
    if (_lastScreenWidth == screenWidth && _lastHasHinge == hasHinge) return;
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
            contentMax: 500,
            actionColumns: width > 900 ? 6 : (width > 700 ? 5 : 4),
            actionItemHeight: 120,
            actionIconDimension: 36,
            actionTextSize: 15,
            wideMode: true,
            hasHinge: true,
            useTwoColumnLayout: width >= 900);
      case ScreenType.large:
        return ResponsiveConfig(
            paddingH: 40,
            paddingV: 28,
            contentMax: 500,
            actionColumns: 6,
            actionItemHeight: 125,
            actionIconDimension: 38,
            actionTextSize: 16,
            wideMode: true,
            hasHinge: false,
            useTwoColumnLayout: width >= 1100);
      case ScreenType.medium:
        return ResponsiveConfig(
            paddingH: 20,
            paddingV: 24,
            contentMax: 480,
            actionColumns: 4,
            actionItemHeight: 115,
            actionIconDimension: 32,
            actionTextSize: 14,
            wideMode: true,
            hasHinge: false,
            useTwoColumnLayout: width >= 900);
      case ScreenType.compact:
      default:
        return ResponsiveConfig(
            paddingH: 20,
            paddingV: 20,
            contentMax: width - 40,
            actionColumns: 3,
            actionItemHeight: width < 360 ? 95 : 105,
            actionIconDimension: width < 360 ? 24 : 28,
            actionTextSize: width < 360 ? 12 : 13,
            wideMode: false,
            hasHinge: false,
            useTwoColumnLayout: false);
    }
  }

  Widget wrapWithConstraints({required Widget child}) {
    if (currentScreenType == ScreenType.expanded || layoutSettings.hasHinge)
      return child;
    if (currentScreenType == ScreenType.large &&
        layoutSettings.contentMax < double.infinity)
      return Center(
          child: ConstrainedBox(
              constraints: BoxConstraints(maxWidth: layoutSettings.contentMax),
              child: child));
    return child;
  }

  @override
  void dispose() {
    _fadeController.dispose();
    _scaleController.dispose();
    _rotationController.dispose();
    _cooldownTimer?.cancel();
    _verificationCheckTimer?.cancel();
    super.dispose();
  }

  void _startVerificationCheck() {
    _verificationCheckTimer =
        Timer.periodic(const Duration(seconds: 3), (timer) async {
      if (mounted) await _checkEmailVerification();
    });
  }

  Future<void> _checkEmailVerification() async {
    // Silent background poll: no spinner flashing every three seconds.
    if (isChecking) return;
    try {
      final firebaseUser = FirebaseAuth.instance.currentUser;
      if (firebaseUser == null) return;
      await firebaseUser.reload();
      final updatedUser = FirebaseAuth.instance.currentUser;
      if (updatedUser?.emailVerified == true) {
        _verificationCheckTimer?.cancel();
        if (mounted) {
          HapticFeedback.mediumImpact();
          _toastSuccess('Email verified');
          await Future.delayed(const Duration(seconds: 1));
          if (mounted) {
            context.goNamedAuth('onboarding', context.mounted);
          }
        }
      }
    } catch (e) {
      debugPrint('Error checking email verification: $e');
    }
  }

  Future<void> _resendVerificationEmail() async {
    if (resendCooldown > 0) return;
    setState(() => isResending = true);
    try {
      final firebaseUser = FirebaseAuth.instance.currentUser;
      if (firebaseUser == null) throw Exception('No user signed in');
      await firebaseUser.sendEmailVerification();
      if (!mounted) return;
      setState(() => resendCooldown = 60);
      _startCooldownTimer();
      if (mounted) {
        HapticFeedback.lightImpact();
        _toastSuccess('Verification email sent to ${firebaseUser.email}');
      }
    } catch (e) {
      if (mounted)
        _toastError('Failed to send email: ${e.toString()}');
    } finally {
      if (mounted) setState(() => isResending = false);
    }
  }

  void _startCooldownTimer() {
    _cooldownTimer?.cancel();
    _cooldownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (mounted)
        setState(() {
          if (resendCooldown > 0)
            resendCooldown--;
          else
            timer.cancel();
        });
    });
  }

  Future<void> _manualCheckVerification() async {
    HapticFeedback.selectionClick();
    setState(() => isChecking = true);
    if (!_reduceMotion) _rotationController.repeat();
    try {
      final firebaseUser = FirebaseAuth.instance.currentUser;
      if (firebaseUser == null)
        throw Exception('No user signed in - please sign in again');
      await firebaseUser.reload();
      final updatedUser = FirebaseAuth.instance.currentUser;
      if (updatedUser?.emailVerified == true) {
        _verificationCheckTimer?.cancel();
        if (mounted) {
          HapticFeedback.mediumImpact();
          _toastSuccess('Email verified. Taking you to onboarding…');
          await Future.delayed(const Duration(milliseconds: 500));
          context.goNamedAuth('onboarding', context.mounted);
        }
      } else {
        if (mounted) {
          HapticFeedback.lightImpact();
          _toastWarn('Email not verified yet. Please check your inbox and click the verification link, then try again.');
        }
      }
    } catch (e) {
      if (mounted)
        _toastError('Error checking verification status: ${e.toString()}');
    } finally {
      _rotationController.stop();
      if (mounted) setState(() => isChecking = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final currentUser = FirebaseAuth.instance.currentUser;

    return wrapWithConstraints(
      child: Container(
        width: widget.width ?? double.infinity,
        height: widget.height ?? double.infinity,
        color: joviNavy,
        child: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) {
              return Column(
                children: [
                  // Header
                  Padding(
                    padding: EdgeInsets.only(
                        top: layoutSettings.wideMode ? 60 : 40,
                        bottom: layoutSettings.wideMode ? 30 : 20),
                    child: FadeTransition(
                      opacity: _fadeAnimation,
                      child: Column(children: [
                        // Step progress
                        Padding(
                          padding: EdgeInsets.symmetric(
                              horizontal: layoutSettings.paddingH + 20),
                          child: Row(children: [
                            Expanded(
                                child: Container(
                                    height: 3,
                                    decoration: BoxDecoration(
                                        gradient: const LinearGradient(colors: [
                                          joviCoral,
                                          joviCoralLight
                                        ]),
                                        borderRadius:
                                            BorderRadius.circular(2)))),
                            const SizedBox(width: 6),
                            Expanded(
                                child: Container(
                                    height: 3,
                                    decoration: BoxDecoration(
                                        gradient: const LinearGradient(colors: [
                                          joviCoral,
                                          joviCoralLight
                                        ]),
                                        borderRadius:
                                            BorderRadius.circular(2)))),
                            const SizedBox(width: 6),
                            Expanded(
                                child: Container(
                                    height: 3,
                                    decoration: BoxDecoration(
                                        color: Colors.white.withOpacity(0.15),
                                        borderRadius:
                                            BorderRadius.circular(2)))),
                          ]),
                        ),
                        const SizedBox(height: 8),
                        Text('Step 2 of 3',
                            style: TextStyle(
                                color: Colors.white.withOpacity(0.5),
                                fontSize: 12,
                                fontWeight: FontWeight.w500)),
                        const SizedBox(height: 20),
                        Text('Verify Your Email',
                            style: TextStyle(
                                color: Colors.white,
                                fontSize: layoutSettings.wideMode ? 28 : 24,
                                fontWeight: FontWeight.w700,
                                letterSpacing: -0.5)),
                      ]),
                    ),
                  ),

                  // Main Card
                  Expanded(
                    child: Center(
                      child: SingleChildScrollView(
                        physics: const BouncingScrollPhysics(),
                        child: Padding(
                          padding: EdgeInsets.symmetric(
                              horizontal: layoutSettings.paddingH,
                              vertical: layoutSettings.paddingV),
                          child: Center(
                            child: FadeTransition(
                              opacity: _fadeAnimation,
                              child: ScaleTransition(
                                scale: _scaleAnimation,
                                child: Container(
                                  width: layoutSettings.contentMax,
                                  constraints: BoxConstraints(
                                      maxWidth:
                                          layoutSettings.wideMode ? 500 : 440,
                                      minWidth: 280),
                                  decoration: BoxDecoration(
                                    color: Colors.white,
                                    borderRadius: BorderRadius.circular(24),
                                    boxShadow: [
                                      BoxShadow(
                                          color: Colors.black.withOpacity(0.1),
                                          blurRadius: 10,
                                          offset: const Offset(0, 4)),
                                      BoxShadow(
                                          color: Colors.black.withOpacity(0.08),
                                          blurRadius: 30,
                                          offset: const Offset(0, 10))
                                    ],
                                  ),
                                  child: Padding(
                                    padding: EdgeInsets.all(
                                        layoutSettings.wideMode ? 40 : 32),
                                    child: Column(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        // Email Icon with coral theme
                                        Container(
                                          width: layoutSettings.wideMode
                                              ? 120
                                              : 100,
                                          height: layoutSettings.wideMode
                                              ? 120
                                              : 100,
                                          decoration: BoxDecoration(
                                            color: joviCoral.withOpacity(0.1),
                                            shape: BoxShape.circle,
                                          ),
                                          child: Stack(
                                            alignment: Alignment.center,
                                            children: [
                                              Icon(Icons.mail_outline,
                                                  size: layoutSettings.wideMode
                                                      ? 60
                                                      : 50,
                                                  color: joviCoral),
                                              if (isChecking)
                                                AnimatedBuilder(
                                                  animation: _rotationAnimation,
                                                  builder: (context, child) {
                                                    return Transform.rotate(
                                                      angle: _rotationAnimation
                                                          .value,
                                                      child: Container(
                                                        width: layoutSettings
                                                                .wideMode
                                                            ? 120
                                                            : 100,
                                                        height: layoutSettings
                                                                .wideMode
                                                            ? 120
                                                            : 100,
                                                        decoration:
                                                            BoxDecoration(
                                                          shape:
                                                              BoxShape.circle,
                                                          border: Border.all(
                                                              color: joviCoral,
                                                              width: 3),
                                                          gradient:
                                                              SweepGradient(
                                                                  colors: [
                                                                joviCoral
                                                                    .withOpacity(
                                                                        0),
                                                                joviCoral
                                                                    .withOpacity(
                                                                        0.5),
                                                                joviCoral
                                                                    .withOpacity(
                                                                        0)
                                                              ]),
                                                        ),
                                                      ),
                                                    );
                                                  },
                                                ),
                                            ],
                                          ),
                                        ),

                                        SizedBox(
                                            height: layoutSettings.wideMode
                                                ? 40
                                                : 32),

                                        // Title
                                        Text('Check Your Email',
                                            style: TextStyle(
                                                fontSize:
                                                    layoutSettings.wideMode
                                                        ? 32
                                                        : 28,
                                                fontWeight: FontWeight.bold,
                                                color: textPrimary)),

                                        const SizedBox(height: 16),

                                        // Email Address pill
                                        Container(
                                          padding: const EdgeInsets.symmetric(
                                              horizontal: 16, vertical: 8),
                                          decoration: BoxDecoration(
                                              color:
                                                  joviCoral.withOpacity(0.08),
                                              borderRadius:
                                                  BorderRadius.circular(20)),
                                          child: Text(
                                              currentUser?.email ??
                                                  'No user signed in',
                                              style: TextStyle(
                                                  fontSize:
                                                      layoutSettings.wideMode
                                                          ? 17
                                                          : 16,
                                                  fontWeight: FontWeight.w600,
                                                  color: joviCoral)),
                                        ),

                                        const SizedBox(height: 24),

                                        // Instructions
                                        ConstrainedBox(
                                          constraints: BoxConstraints(
                                              maxWidth: layoutSettings.wideMode
                                                  ? 400
                                                  : 300),
                                          child: Text(
                                              'We\'ve sent a verification link to your email address. Tap the link to verify your account.',
                                              textAlign: TextAlign.center,
                                              style: TextStyle(
                                                  fontSize:
                                                      layoutSettings.wideMode
                                                          ? 16
                                                          : 15,
                                                  color: textSecondary,
                                                  height: 1.5)),
                                        ),

                                        const SizedBox(height: 32),

                                        // Auto-checking indicator
                                        if (isChecking)
                                          Container(
                                            padding: const EdgeInsets.symmetric(
                                                horizontal: 20, vertical: 12),
                                            decoration: BoxDecoration(
                                                color:
                                                    joviCoral.withOpacity(0.08),
                                                borderRadius:
                                                    BorderRadius.circular(12)),
                                            child: Row(
                                                mainAxisSize: MainAxisSize.min,
                                                children: [
                                                  SizedBox(
                                                      width: 16,
                                                      height: 16,
                                                      child: CircularProgressIndicator(
                                                          strokeWidth: 2,
                                                          valueColor:
                                                              AlwaysStoppedAnimation<
                                                                      Color>(
                                                                  joviCoral))),
                                                  const SizedBox(width: 12),
                                                  Text(
                                                      'Checking verification status…',
                                                      style: TextStyle(
                                                          color: joviCoral,
                                                          fontSize: 14,
                                                          fontWeight:
                                                              FontWeight.w500)),
                                                ]),
                                          ),

                                        const SizedBox(height: 24),

                                        // Manual Check Button — coral gradient
                                        _Pressable(
                                          enabled: !isChecking,
                                          feedbackOnly: true,
                                          child: Container(
                                          width: double.infinity,
                                          constraints: BoxConstraints(
                                              maxWidth: layoutSettings.wideMode
                                                  ? 400
                                                  : double.infinity),
                                          height:
                                              layoutSettings.wideMode ? 56 : 54,
                                          decoration: BoxDecoration(
                                            gradient: const LinearGradient(
                                                colors: [
                                                  joviCoral,
                                                  joviCoralLight
                                                ],
                                                begin: Alignment.centerLeft,
                                                end: Alignment.centerRight),
                                            borderRadius:
                                                BorderRadius.circular(16),
                                            boxShadow: [
                                              BoxShadow(
                                                  color: joviCoral
                                                      .withOpacity(0.3),
                                                  blurRadius: 12,
                                                  offset: const Offset(0, 6))
                                            ],
                                          ),
                                          child: Material(
                                            color: Colors.transparent,
                                            borderRadius:
                                                BorderRadius.circular(16),
                                            child: InkWell(
                                              borderRadius:
                                                  BorderRadius.circular(16),
                                              onTap: isChecking
                                                  ? null
                                                  : _manualCheckVerification,
                                              child: Center(
                                                child: isChecking
                                                    ? const SizedBox(
                                                        width: 24,
                                                        height: 24,
                                                        child:
                                                            CircularProgressIndicator(
                                                                color: Colors
                                                                    .white,
                                                                strokeWidth:
                                                                    2.5))
                                                    : Text(
                                                        'I\'ve Verified My Email',
                                                        style: TextStyle(
                                                            color: Colors.white,
                                                            fontSize:
                                                                layoutSettings
                                                                        .wideMode
                                                                    ? 17
                                                                    : 16,
                                                            fontWeight:
                                                                FontWeight.w600,
                                                            letterSpacing:
                                                                -0.2)),
                                              ),
                                            ),
                                          ),
                                        )),

                                        const SizedBox(height: 16),

                                        // Resend Email Button
                                        TextButton(
                                          onPressed: (isResending ||
                                                  resendCooldown > 0)
                                              ? null
                                              : _resendVerificationEmail,
                                          child: Row(
                                              mainAxisSize: MainAxisSize.min,
                                              children: [
                                                if (isResending)
                                                  SizedBox(
                                                      width: 16,
                                                      height: 16,
                                                      child: CircularProgressIndicator(
                                                          strokeWidth: 2,
                                                          valueColor:
                                                              AlwaysStoppedAnimation<
                                                                      Color>(
                                                                  joviCoral)))
                                                else
                                                  Icon(Icons.refresh,
                                                      size: 20,
                                                      color: resendCooldown > 0
                                                          ? Colors.grey
                                                          : joviCoral),
                                                const SizedBox(width: 8),
                                                Text(
                                                    resendCooldown > 0
                                                        ? 'Resend in ${resendCooldown}s'
                                                        : 'Resend Verification Email',
                                                    style: TextStyle(
                                                        color:
                                                            resendCooldown > 0
                                                                ? Colors.grey
                                                                : joviCoral,
                                                        fontSize: layoutSettings
                                                                .wideMode
                                                            ? 16
                                                            : 15,
                                                        fontWeight:
                                                            FontWeight.w600)),
                                              ]),
                                        ),

                                        const SizedBox(height: 24),

                                        // Help Section — warm amber tips
                                        Container(
                                          constraints: BoxConstraints(
                                              maxWidth: layoutSettings.wideMode
                                                  ? 400
                                                  : double.infinity),
                                          padding: const EdgeInsets.all(16),
                                          decoration: BoxDecoration(
                                              color: Colors.amber.shade50,
                                              borderRadius:
                                                  BorderRadius.circular(12),
                                              border: Border.all(
                                                  color: Colors.amber.shade200,
                                                  width: 1)),
                                          child: Column(
                                              crossAxisAlignment:
                                                  CrossAxisAlignment.start,
                                              children: [
                                                Row(children: [
                                                  Icon(Icons.lightbulb_outline,
                                                      color:
                                                          Colors.amber.shade700,
                                                      size: 20),
                                                  const SizedBox(width: 8),
                                                  Text(
                                                      'Didn\'t receive the email?',
                                                      style: TextStyle(
                                                          color: Colors
                                                              .amber.shade900,
                                                          fontWeight:
                                                              FontWeight.bold,
                                                          fontSize:
                                                              layoutSettings
                                                                      .wideMode
                                                                  ? 15
                                                                  : 14)),
                                                ]),
                                                const SizedBox(height: 8),
                                                Text(
                                                    '• Check your spam or junk folder\n• Make sure ${currentUser?.email ?? 'your email'} is correct\n• Wait a few minutes and try resending',
                                                    style: TextStyle(
                                                        color: Colors
                                                            .amber.shade800,
                                                        fontSize: layoutSettings
                                                                .wideMode
                                                            ? 14
                                                            : 13,
                                                        height: 1.5)),
                                              ]),
                                        ),

                                        const SizedBox(height: 32),

                                        // Sign Out Option
                                        TextButton(
                                          onPressed: () async {
                                            _verificationCheckTimer?.cancel();
                                            await authManager.signOut();
                                            if (!context.mounted) return;
                                            // Other auth widgets route to 'logIn'.
                                            context.goNamedAuth(
                                                'logIn', context.mounted);
                                          },
                                          child: Text('Sign out and try again',
                                              style: TextStyle(
                                                  color: textSecondary,
                                                  fontSize:
                                                      layoutSettings.wideMode
                                                          ? 15
                                                          : 14,
                                                  decoration: TextDecoration
                                                      .underline)),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}
