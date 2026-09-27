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
// Refined 2026-09-22: Apple HIG pass (press feedback, no looping motion,
// navy toasts, autofill/submit, TLD regex fix).
import '/auth/firebase_auth/auth_util.dart';
import '/flutter_flow/flutter_flow_widgets.dart';
import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'dart:async';
import 'dart:ui' as ui_dart;
import 'package:url_launcher/url_launcher.dart';

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

class PremiumResetPasswordWidget extends StatefulWidget {
  const PremiumResetPasswordWidget({Key? key, this.width, this.height})
      : super(key: key);
  final double? width;
  final double? height;

  @override
  _PremiumResetPasswordWidgetState createState() =>
      _PremiumResetPasswordWidgetState();
}

class _PremiumResetPasswordWidgetState extends State<PremiumResetPasswordWidget>
    with TickerProviderStateMixin {
  ScreenType currentScreenType = ScreenType.compact;
  ResponsiveConfig layoutSettings = ResponsiveConfig(
      paddingH: 20,
      paddingV: 20,
      contentMax: 400,
      actionColumns: 3,
      actionItemHeight: 56,
      actionIconDimension: 18,
      actionTextSize: 14,
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

  late TextEditingController emailController;
  late FocusNode emailFocusNode;

  late AnimationController _fadeController;
  late AnimationController _slideController;
  late AnimationController _pulseController;
  late Animation<double> _fadeAnimation;
  late Animation<Offset> _slideAnimation;
  late Animation<double> _pulseAnimation;

  bool isLoading = false;
  bool submitButtonHover = false;
  bool emailSent = false;
  int countdownSeconds = 10;
  Timer? _countdownTimer;
  Timer? _debounceTimer;

  int _resetAttempts = 0;
  final int _maxResetAttempts = 3;
  DateTime? _resetLockoutTime;
  int _resetLockoutMinutes = 5;

  // Jovi colors
  final Color primaryColor = joviCoral;
  final Color secondaryColor = joviCoralLight;
  final Color successColor = joviMint;
  final Color warningColor = const Color(0xFFF59E0B);
  final Color errorColor = const Color(0xFFEF4444);
  final Color textPrimary = Colors.white;
  final Color textSecondary = Colors.white70;
  final Color surfaceColor = Colors.white;

  @override
  void initState() {
    super.initState();
    emailController = TextEditingController();
    emailFocusNode = FocusNode();

    _fadeController =
        AnimationController(duration: _Motion.enter, vsync: this);
    _slideController =
        AnimationController(duration: _Motion.enter, vsync: this);
    // No longer loops: a slow breathing scale is exactly the kind of
    // background motion Apple asks apps to avoid. Kept at rest (1.0).
    _pulseController =
        AnimationController(duration: const Duration(seconds: 2), vsync: this);

    _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
        CurvedAnimation(parent: _fadeController, curve: Curves.easeOut));
    _slideAnimation =
        Tween<Offset>(begin: const Offset(0, 0.04), end: Offset.zero).animate(
            CurvedAnimation(parent: _slideController, curve: _Motion.settle));
    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.05).animate(
        CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut));

    _fadeController.forward();
    _slideController.forward();
    emailFocusNode.addListener(() => setState(() {}));
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
            paddingH: 80,
            paddingV: 20,
            contentMax: 550,
            actionColumns: width > 900 ? 6 : (width > 700 ? 5 : 4),
            actionItemHeight: 64,
            actionIconDimension: 24,
            actionTextSize: 18,
            wideMode: true,
            hasHinge: true,
            useTwoColumnLayout: width >= 900);
      case ScreenType.large:
        return ResponsiveConfig(
            paddingH: 60,
            paddingV: 20,
            contentMax: 500,
            actionColumns: 6,
            actionItemHeight: 64,
            actionIconDimension: 20,
            actionTextSize: 16,
            wideMode: true,
            hasHinge: false,
            useTwoColumnLayout: width >= 1100);
      case ScreenType.medium:
        return ResponsiveConfig(
            paddingH: 40,
            paddingV: 20,
            contentMax: 450,
            actionColumns: 4,
            actionItemHeight: 56,
            actionIconDimension: 18,
            actionTextSize: 14,
            wideMode: true,
            hasHinge: false,
            useTwoColumnLayout: width >= 900);
      case ScreenType.compact:
      default:
        return ResponsiveConfig(
            paddingH: 20,
            paddingV: 20,
            contentMax: 400,
            actionColumns: 3,
            actionItemHeight: 56,
            actionIconDimension: 18,
            actionTextSize: 14,
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
    emailController.dispose();
    emailFocusNode.dispose();
    _fadeController.dispose();
    _slideController.dispose();
    _pulseController.dispose();
    _debounceTimer?.cancel();
    _countdownTimer?.cancel();
    super.dispose();
  }

  bool _validateEmail(String email) {
    if (email.isEmpty) return false;
    return RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,}$').hasMatch(email);
  }

  bool _isResetLocked() {
    if (_resetLockoutTime != null) {
      if (DateTime.now().isBefore(_resetLockoutTime!)) return true;
      _resetLockoutTime = null;
      _resetAttempts = 0;
      return false;
    }
    return false;
  }

  String _getResetLockoutMessage() {
    if (_resetLockoutTime != null) {
      final remaining = _resetLockoutTime!.difference(DateTime.now());
      return 'Too many attempts. Try again in ${remaining.inMinutes} minutes.';
    }
    return '';
  }

  Future<void> _sendPasswordResetEmail() async {
    if (!_validateEmail(emailController.text)) {
      _showWarningSnackBar('Please enter a valid email address');
      return;
    }
    if (_isResetLocked()) {
      _showErrorSnackBar(_getResetLockoutMessage());
      return;
    }
    setState(() => isLoading = true);
    try {
      await FirebaseAuth.instance.sendPasswordResetEmail(
          email: emailController.text.trim().toLowerCase());
      try {
        await FirebaseFirestore.instance.collection('security_logs').add({
          'event': 'password_reset_requested',
          'email': emailController.text.trim().toLowerCase(),
          'timestamp': FieldValue.serverTimestamp(),
          'success': true
        });
      } catch (e) {
        debugPrint('Failed to log: $e');
      }
      setState(() {
        isLoading = false;
        emailSent = true;
        countdownSeconds = 10;
      });
      _showSuccessSnackBar(
          'Password reset email sent! Check your inbox and spam folder.');
      _startCountdown();
    } on FirebaseAuthException catch (e) {
      setState(() => isLoading = false);
      switch (e.code) {
        case 'user-not-found':
          setState(() {
            emailSent = true;
            countdownSeconds = 10;
          });
          _showInfoSnackBar(
              'If this email is registered, you will receive a password reset link.');
          _startCountdown();
          break;
        case 'invalid-email':
          _showErrorSnackBar('Please enter a valid email address');
          break;
        case 'too-many-requests':
          _handleResetAttemptFailed();
          _showErrorSnackBar('Too many attempts. Please try again later.');
          break;
        case 'network-request-failed':
          _showErrorSnackBar('Network error. Please check your connection.');
          break;
        default:
          _showErrorSnackBar('Unable to send reset email. Please try again.');
      }
    } catch (e) {
      setState(() => isLoading = false);
      _showErrorSnackBar('An unexpected error occurred. Please try again.');
    }
  }

  void _startCountdown() {
    _countdownTimer?.cancel();
    _countdownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (mounted) {
        setState(() => countdownSeconds--);
        if (countdownSeconds <= 0) {
          timer.cancel();
          context.goNamed('logIn');
        }
      } else {
        timer.cancel();
      }
    });
  }

  void _handleResetAttemptFailed() {
    setState(() {
      _resetAttempts++;
      if (_resetAttempts >= _maxResetAttempts) {
        _resetLockoutMinutes = _resetLockoutMinutes * 2;
        _resetLockoutTime =
            DateTime.now().add(Duration(minutes: _resetLockoutMinutes));
        FirebaseFirestore.instance.collection('security_logs').add({
          'event': 'password_reset_locked',
          'email': emailController.text,
          'timestamp': FieldValue.serverTimestamp(),
          'reason': 'max_reset_attempts_exceeded'
        }).catchError((e) => debugPrint('Failed to log: $e'));
      }
    });
  }

  void _showSuccessSnackBar(String message) {
    HapticFeedback.lightImpact();
    _toastSuccess(message);
  }

  void _showErrorSnackBar(String message) {
    HapticFeedback.mediumImpact();
    _toastError(message);
  }

  void _showWarningSnackBar(String message) {
    HapticFeedback.lightImpact();
    _toastWarn(message);
  }

  void _showInfoSnackBar(String message) => _toastInfo(message);

  @override
  Widget build(BuildContext context) {
    final isSmallScreen = currentScreenType == ScreenType.compact;

    return wrapWithConstraints(
      child: Container(
        width: widget.width ?? MediaQuery.of(context).size.width,
        height: widget.height ?? MediaQuery.of(context).size.height,
        color: joviNavy,
        child: SafeArea(
          child: Column(
            children: [
              // Back button
              Padding(
                padding: EdgeInsets.symmetric(
                    horizontal: layoutSettings.paddingH,
                    vertical: layoutSettings.paddingV),
                child: Align(
                    alignment: Alignment.topLeft, child: _buildBackButton()),
              ),

              // Main content
              Expanded(
                child: SingleChildScrollView(
                  physics: BouncingScrollPhysics(),
                  child: Container(
                    constraints: BoxConstraints(
                        minHeight: MediaQuery.of(context).size.height -
                            MediaQuery.of(context).padding.top -
                            MediaQuery.of(context).padding.bottom -
                            100),
                    child: Center(
                      child: Container(
                        constraints:
                            BoxConstraints(maxWidth: layoutSettings.contentMax),
                        padding: EdgeInsets.symmetric(
                            horizontal: layoutSettings.paddingH),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            SizedBox(height: isSmallScreen ? 20 : 40),

                            // Logo and title
                            FadeTransition(
                              opacity: _fadeAnimation,
                              child: SlideTransition(
                                position: _slideAnimation,
                                child: Column(children: [
                                  // Lock icon with coral glow
                                  ScaleTransition(
                                    scale: _pulseAnimation,
                                    child: Container(
                                      width: isSmallScreen
                                          ? 100
                                          : (layoutSettings.wideMode
                                              ? 140
                                              : 120),
                                      height: isSmallScreen
                                          ? 100
                                          : (layoutSettings.wideMode
                                              ? 140
                                              : 120),
                                      decoration: BoxDecoration(
                                        gradient: const LinearGradient(colors: [
                                          joviCoral,
                                          joviCoralLight
                                        ]),
                                        shape: BoxShape.circle,
                                        boxShadow: [
                                          BoxShadow(
                                              color: joviCoral.withOpacity(0.3),
                                              blurRadius: 30,
                                              spreadRadius: 5)
                                        ],
                                      ),
                                      child: Icon(Icons.lock_reset,
                                          color: Colors.white,
                                          size: isSmallScreen
                                              ? 50
                                              : (layoutSettings.wideMode
                                                  ? 70
                                                  : 60)),
                                    ),
                                  ),
                                  SizedBox(height: 24),
                                  Text('Reset Password',
                                      style: TextStyle(
                                          fontSize: isSmallScreen
                                              ? 28
                                              : (layoutSettings.wideMode
                                                  ? 36
                                                  : 32),
                                          fontWeight: FontWeight.w700,
                                          letterSpacing: -0.6,
                                          color: Colors.white)),
                                  SizedBox(height: 8),
                                  Padding(
                                    padding: EdgeInsets.symmetric(
                                        horizontal:
                                            layoutSettings.wideMode ? 40 : 0),
                                    child: Text(
                                        emailSent
                                            ? 'Check your email for reset instructions'
                                            : 'Enter your email to receive a password reset link',
                                        textAlign: TextAlign.center,
                                        style: TextStyle(
                                            fontSize: isSmallScreen
                                                ? 14
                                                : (layoutSettings.wideMode
                                                    ? 18
                                                    : 16),
                                            color:
                                                Colors.white.withOpacity(0.6))),
                                  ),
                                ]),
                              ),
                            ),

                            SizedBox(height: 40),

                            // Form card — white on navy
                            Container(
                              constraints: BoxConstraints(
                                  maxWidth: layoutSettings.contentMax),
                              padding: EdgeInsets.all(isSmallScreen
                                  ? 24
                                  : (layoutSettings.wideMode ? 40 : 32)),
                              decoration: BoxDecoration(
                                color: surfaceColor,
                                borderRadius: BorderRadius.circular(24),
                                boxShadow: [
                                  BoxShadow(
                                      color: Colors.black.withOpacity(0.1),
                                      blurRadius: 20,
                                      offset: Offset(0, 10))
                                ],
                              ),
                              child: AnimatedSwitcher(
                                duration: _Motion.select,
                                child: emailSent
                                    ? _buildSuccessContent()
                                    : _buildEmailForm(),
                              ),
                            ),

                            SizedBox(height: 32),

                            // Security badges
                            _buildSecurityBadges(),

                            SizedBox(height: 20),

                            // Help text
                            TextButton(
                              onPressed: () async {
                                final Uri emailUri = Uri(
                                    scheme: 'mailto',
                                    path: 'support@jovihealth.com',
                                    query: 'subject=Password Reset Help');
                                try {
                                  if (await canLaunchUrl(emailUri)) {
                                    await launchUrl(emailUri);
                                  } else {
                                    _showInfoSnackBar(
                                        'Please email support@jovihealth.com for assistance');
                                  }
                                } catch (e) {
                                  _showInfoSnackBar(
                                      'Please email support@jovihealth.com for assistance');
                                }
                              },
                              child: Text('Need Help?',
                                  style: TextStyle(
                                      color: joviCoral,
                                      fontWeight: FontWeight.w600,
                                      fontSize:
                                          layoutSettings.wideMode ? 18 : 14)),
                            ),

                            SizedBox(height: 40),
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
      ),
    );
  }

  Widget _buildBackButton() {
    return _Pressable(
      onTap: () {
        HapticFeedback.lightImpact();
        context.goNamed('logIn');
      },
      child: Container(
        width: 44,
        height: 44,
        decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.06),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: Colors.white.withOpacity(0.1), width: 1)),
        child: Icon(Icons.arrow_back_rounded,
            color: Colors.white.withOpacity(0.7), size: 22),
      ),
    );
  }

  Widget _buildSecurityBadges() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        _buildBadge(Icons.lock, 'Secure'),
        SizedBox(width: 16),
        _buildBadge(Icons.enhanced_encryption, 'Encrypted'),
        SizedBox(width: 16),
        _buildBadge(Icons.privacy_tip, 'Private'),
      ],
    );
  }

  Widget _buildBadge(IconData icon, String label) {
    return Container(
      padding: EdgeInsets.symmetric(
          horizontal: layoutSettings.wideMode ? 16 : 12,
          vertical: layoutSettings.wideMode ? 8 : 6),
      decoration: BoxDecoration(
          color: joviCoral.withOpacity(0.1),
          borderRadius: BorderRadius.circular(20)),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon,
            size: layoutSettings.actionIconDimension * 0.7, color: joviCoral),
        SizedBox(width: 4),
        Text(label,
            style: TextStyle(
                color: joviCoral,
                fontSize: layoutSettings.actionTextSize,
                fontWeight: FontWeight.w600)),
      ]),
    );
  }

  Widget _buildEmailForm() {
    final cardTextPrimary = joviNavy;
    final cardTextSecondary = const Color(0xFF6B7280);

    return Column(
      key: ValueKey('email_form'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (_isResetLocked()) ...[
          _buildAlertCard(
              icon: Icons.lock_clock,
              message: _getResetLockoutMessage(),
              color: errorColor),
          SizedBox(height: 20),
        ],

        // Instructions
        Container(
          padding: EdgeInsets.all(layoutSettings.wideMode ? 16 : 12),
          decoration: BoxDecoration(
              color: joviCoral.withOpacity(0.05),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: joviCoral.withOpacity(0.2))),
          child: Row(children: [
            Icon(Icons.info_outline,
                color: joviCoral, size: layoutSettings.actionIconDimension),
            SizedBox(width: 12),
            Expanded(
                child: Text('Enter the email associated with your account',
                    style: TextStyle(
                        color: cardTextPrimary,
                        fontSize: layoutSettings.actionTextSize + 1))),
          ]),
        ),
        SizedBox(height: 20),

        // Email field — light theme inside card
        Container(
          decoration: BoxDecoration(
            color: emailFocusNode.hasFocus
                ? joviCoral.withOpacity(0.05)
                : Colors.grey.shade50,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
                color: emailFocusNode.hasFocus
                    ? joviCoral
                    : Colors.grey.withOpacity(0.2),
                width: emailFocusNode.hasFocus ? 2 : 1),
          ),
          child: TextFormField(
            controller: emailController,
            focusNode: emailFocusNode,
            keyboardType: TextInputType.emailAddress,
            autofillHints: const [AutofillHints.email],
            autocorrect: false,
            textInputAction: TextInputAction.send,
            onFieldSubmitted: (_) {
              if (emailController.text.isNotEmpty &&
                  !isLoading &&
                  !_isResetLocked()) {
                _sendPasswordResetEmail();
              }
            },
            onChanged: (_) => setState(() {}),
            style: TextStyle(
                color: cardTextPrimary,
                fontSize: layoutSettings.actionTextSize + 4),
            decoration: InputDecoration(
              labelText: 'Email Address',
              labelStyle: TextStyle(
                  color:
                      emailFocusNode.hasFocus ? joviCoral : cardTextSecondary,
                  fontSize: layoutSettings.actionTextSize + 2),
              hintText: 'your@email.com',
              hintStyle: TextStyle(color: cardTextSecondary.withOpacity(0.4)),
              prefixIcon: Icon(Icons.mail_outline_rounded,
                  color:
                      emailFocusNode.hasFocus ? joviCoral : cardTextSecondary,
                  size: layoutSettings.actionIconDimension),
              border: InputBorder.none,
              contentPadding: EdgeInsets.symmetric(
                  horizontal: 16, vertical: layoutSettings.wideMode ? 20 : 16),
            ),
          ),
        ),
        SizedBox(height: 24),

        // Send button — coral gradient
        _buildPrimaryButton(
            text: 'Send Reset Email',
            onPressed: emailController.text.isNotEmpty &&
                    !isLoading &&
                    !_isResetLocked()
                ? _sendPasswordResetEmail
                : null,
            isLoading: isLoading,
            icon: Icons.send),
        SizedBox(height: 16),

        Text(
            'You will receive an email with instructions to reset your password',
            textAlign: TextAlign.center,
            style: TextStyle(
                color: cardTextSecondary,
                fontSize: layoutSettings.actionTextSize)),
      ],
    );
  }

  Widget _buildSuccessContent() {
    final cardTextPrimary = joviNavy;
    final cardTextSecondary = const Color(0xFF6B7280);

    return Column(
      key: ValueKey('success_content'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Success icon
        Center(
            child: Container(
          width: layoutSettings.wideMode ? 100 : 80,
          height: layoutSettings.wideMode ? 100 : 80,
          decoration: BoxDecoration(
              color: successColor.withOpacity(0.1), shape: BoxShape.circle),
          child: Icon(Icons.mark_email_read,
              color: successColor, size: layoutSettings.wideMode ? 50 : 40),
        )),
        SizedBox(height: 24),
        Text('Email Sent!',
            textAlign: TextAlign.center,
            style: TextStyle(
                fontSize: layoutSettings.wideMode ? 28 : 24,
                fontWeight: FontWeight.bold,
                color: cardTextPrimary)),
        SizedBox(height: 12),
        Text('We\'ve sent password reset instructions to:',
            textAlign: TextAlign.center,
            style: TextStyle(
                color: cardTextSecondary,
                fontSize: layoutSettings.actionTextSize + 2)),
        SizedBox(height: 8),
        Text(emailController.text,
            textAlign: TextAlign.center,
            style: TextStyle(
                color: joviCoral,
                fontSize: layoutSettings.actionTextSize + 4,
                fontWeight: FontWeight.w600)),
        SizedBox(height: 20),

        // Instructions
        Container(
          padding: EdgeInsets.all(layoutSettings.wideMode ? 20 : 16),
          decoration: BoxDecoration(
              color: Colors.grey.shade50,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.grey.shade200)),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            _buildInstruction('1. Check your email inbox'),
            SizedBox(height: 8),
            _buildInstruction('2. Tap the reset link in the email'),
            SizedBox(height: 8),
            _buildInstruction('3. Create a new secure password'),
            SizedBox(height: 8),
            _buildInstruction('4. Sign in with your new password'),
          ]),
        ),
        SizedBox(height: 20),
        Text('Didn\'t receive the email? Check your spam folder',
            textAlign: TextAlign.center,
            style: TextStyle(
                color: cardTextSecondary,
                fontSize: layoutSettings.actionTextSize,
                fontStyle: FontStyle.italic)),
        SizedBox(height: 16),

        // Countdown
        Column(children: [
          Container(
            padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            decoration: BoxDecoration(
                color: joviCoral.withOpacity(0.1),
                borderRadius: BorderRadius.circular(20)),
            child: Row(
                mainAxisSize: MainAxisSize.min,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.timer,
                      color: joviCoral,
                      size: layoutSettings.actionIconDimension),
                  SizedBox(width: 8),
                  Text('Back to Sign In in ${countdownSeconds}s',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                          color: joviCoral,
                          fontSize: layoutSettings.actionTextSize + 2,
                          fontWeight: FontWeight.w600)),
                ]),
          ),
          SizedBox(height: 12),
          TextButton.icon(
            icon: Icon(Icons.arrow_back,
                size: layoutSettings.actionIconDimension),
            label: Text('Go to Sign In Now',
                style: TextStyle(fontSize: layoutSettings.actionTextSize + 2)),
            style: TextButton.styleFrom(foregroundColor: joviCoral),
            onPressed: () {
              HapticFeedback.lightImpact();
              _countdownTimer?.cancel();
              context.goNamed('logIn');
            },
          ),
        ]),
      ],
    );
  }

  Widget _buildInstruction(String text) {
    return Row(children: [
      Icon(Icons.check_circle,
          color: successColor, size: layoutSettings.actionIconDimension * 0.9),
      SizedBox(width: 8),
      Expanded(
          child: Text(text,
              style: TextStyle(
                  color: joviNavy,
                  fontSize: layoutSettings.actionTextSize + 2))),
    ]);
  }

  Widget _buildPrimaryButton(
      {required String text,
      required VoidCallback? onPressed,
      bool isLoading = false,
      IconData? icon}) {
    final isEnabled = onPressed != null;
    return _Pressable(
      enabled: isEnabled,
      feedbackOnly: true,
      child: MouseRegion(
      onEnter: (_) => setState(() => submitButtonHover = true),
      onExit: (_) => setState(() => submitButtonHover = false),
      child: AnimatedContainer(
        duration: _Motion.select,
        height: layoutSettings.actionItemHeight,
        decoration: BoxDecoration(
          gradient: LinearGradient(
              colors: isEnabled
                  ? [joviCoral, joviCoralLight]
                  : [Colors.grey.shade300, Colors.grey.shade300]),
          borderRadius: BorderRadius.circular(16),
          boxShadow: isEnabled
              ? [
                  BoxShadow(
                      color:
                          joviCoral.withOpacity(submitButtonHover ? 0.4 : 0.2),
                      blurRadius: submitButtonHover ? 20 : 10,
                      offset: Offset(0, submitButtonHover ? 8 : 4))
                ]
              : [],
        ),
        child: Material(
          color: Colors.transparent,
          borderRadius: BorderRadius.circular(16),
          child: InkWell(
              borderRadius: BorderRadius.circular(16),
              onTap: onPressed,
              child: Center(
                child: isLoading
                    ? SizedBox(
                        width: layoutSettings.actionIconDimension + 4,
                        height: layoutSettings.actionIconDimension + 4,
                        child: CircularProgressIndicator(
                            color: Colors.white, strokeWidth: 2.5))
                    : Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                            if (icon != null) ...[
                              Icon(icon,
                                  color: Colors.white,
                                  size: layoutSettings.actionIconDimension),
                              SizedBox(width: 8)
                            ],
                            Text(text,
                                style: TextStyle(
                                    color: Colors.white,
                                    fontSize: layoutSettings.actionTextSize + 4,
                                    fontWeight: FontWeight.w600,
                                    letterSpacing: -0.2)),
                          ]),
              )),
        ),
      ),
    ));
  }

  Widget _buildAlertCard(
      {required IconData icon, required String message, required Color color}) {
    return Container(
      padding: EdgeInsets.all(layoutSettings.wideMode ? 16 : 12),
      decoration: BoxDecoration(
          color: color.withOpacity(0.1),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color.withOpacity(0.3))),
      child: Row(children: [
        Icon(icon, color: color, size: layoutSettings.actionIconDimension),
        SizedBox(width: 12),
        Expanded(
            child: Text(message,
                style: TextStyle(
                    color: color,
                    fontSize: layoutSettings.actionTextSize + 1,
                    fontWeight: FontWeight.w600)))
      ]),
    );
  }
}
