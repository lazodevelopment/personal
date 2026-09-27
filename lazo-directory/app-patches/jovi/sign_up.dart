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
// Refined 2026-09-22: Apple HIG pass (press feedback, no idle loop,
// autofill + keyboard submit, navy toasts, TLD regex fix).
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
  final double formMaxWidth;
  final double headerFontSize;
  final double titleFontSize;
  final double subtitleFontSize;
  final double buttonHeight;
  final double inputHeight;
  final double checkboxSize;
  final bool wideMode;
  final bool hasHinge;
  final bool useTwoColumnLayout;

  ResponsiveConfig({
    required this.paddingH,
    required this.paddingV,
    required this.contentMax,
    required this.formMaxWidth,
    required this.headerFontSize,
    required this.titleFontSize,
    required this.subtitleFontSize,
    required this.buttonHeight,
    required this.inputHeight,
    required this.checkboxSize,
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

class EnhancedSignupWidget extends StatefulWidget {
  const EnhancedSignupWidget({
    Key? key,
    this.width,
    this.height,
  }) : super(key: key);

  final double? width;
  final double? height;

  @override
  _EnhancedSignupWidgetState createState() => _EnhancedSignupWidgetState();
}

class _EnhancedSignupWidgetState extends State<EnhancedSignupWidget>
    with TickerProviderStateMixin {
  // Responsive Layout Variables
  ScreenType currentScreenType = ScreenType.compact;
  ResponsiveConfig layoutSettings = ResponsiveConfig(
    paddingH: 20,
    paddingV: 20,
    contentMax: double.infinity,
    formMaxWidth: 440,
    headerFontSize: 28,
    titleFontSize: 26,
    subtitleFontSize: 14,
    buttonHeight: 56,
    inputHeight: 18,
    checkboxSize: 24,
    wideMode: false,
    hasHinge: false,
  );

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

  // Controllers
  late TextEditingController emailController;
  late TextEditingController passwordController;
  late TextEditingController confirmPasswordController;

  // Focus nodes
  late FocusNode emailFocusNode;
  late FocusNode passwordFocusNode;
  late FocusNode confirmPasswordFocusNode;

  // Animation controllers
  late AnimationController _fadeController;
  late AnimationController _slideController;
  late AnimationController _floatController;
  late Animation<double> _fadeAnimation;
  late Animation<Offset> _slideAnimation;
  late Animation<double> _floatAnimation;

  // State variables
  bool passwordVisibility = false;
  bool confirmPasswordVisibility = false;
  bool membershipAccepted = false;
  bool termsAccepted = false;
  bool isLoading = false;

  // Password strength indicators
  bool hasMinLength = false;
  bool hasUpperCase = false;
  bool hasLowerCase = false;
  bool hasDigit = false;
  bool hasSpecialChar = false;

  // Jovi color scheme
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
    emailController = TextEditingController();
    passwordController = TextEditingController();
    confirmPasswordController = TextEditingController();
    emailFocusNode = FocusNode();
    passwordFocusNode = FocusNode();
    confirmPasswordFocusNode = FocusNode();

    _fadeController =
        AnimationController(duration: _Motion.enter, vsync: this);
    _slideController =
        AnimationController(duration: _Motion.enter, vsync: this);
    // Was an always-on 3 s loop driving an animation nothing rendered.
    _floatController =
        AnimationController(duration: const Duration(seconds: 3), vsync: this);

    _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
        CurvedAnimation(parent: _fadeController, curve: Curves.easeOut));
    _slideAnimation =
        Tween<Offset>(begin: const Offset(0, 0.06), end: Offset.zero).animate(
            CurvedAnimation(parent: _slideController, curve: _Motion.settle));
    _floatAnimation = Tween<double>(begin: -10, end: 10).animate(
        CurvedAnimation(parent: _floatController, curve: Curves.easeInOut));

    _fadeController.forward();
    _slideController.forward();
    passwordController.addListener(_checkPasswordStrength);
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
            paddingH: 32,
            paddingV: 24,
            contentMax: double.infinity,
            formMaxWidth: width > 900 ? 700 : 600,
            headerFontSize: 36,
            titleFontSize: 32,
            subtitleFontSize: 18,
            buttonHeight: 64,
            inputHeight: 20,
            checkboxSize: 28,
            wideMode: true,
            hasHinge: true,
            useTwoColumnLayout: width >= 900);
      case ScreenType.large:
        return ResponsiveConfig(
            paddingH: 48,
            paddingV: 32,
            contentMax: double.infinity,
            formMaxWidth: 600,
            headerFontSize: 32,
            titleFontSize: 30,
            subtitleFontSize: 16,
            buttonHeight: 60,
            inputHeight: 20,
            checkboxSize: 26,
            wideMode: true,
            hasHinge: false,
            useTwoColumnLayout: width >= 1100);
      case ScreenType.medium:
        return ResponsiveConfig(
            paddingH: 40,
            paddingV: 28,
            contentMax: double.infinity,
            formMaxWidth: 520,
            headerFontSize: 30,
            titleFontSize: 28,
            subtitleFontSize: 16,
            buttonHeight: 58,
            inputHeight: 19,
            checkboxSize: 25,
            wideMode: true,
            hasHinge: false,
            useTwoColumnLayout: width >= 900);
      case ScreenType.compact:
      default:
        return ResponsiveConfig(
            paddingH: 20,
            paddingV: 20,
            contentMax: double.infinity,
            formMaxWidth: width < 360 ? 320 : 440,
            headerFontSize: width < 360 ? 24 : 28,
            titleFontSize: width < 360 ? 22 : 26,
            subtitleFontSize: width < 360 ? 12 : 14,
            buttonHeight: width < 360 ? 52 : 56,
            inputHeight: width < 360 ? 16 : 18,
            checkboxSize: width < 360 ? 22 : 24,
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
    passwordController.dispose();
    confirmPasswordController.dispose();
    emailFocusNode.dispose();
    passwordFocusNode.dispose();
    confirmPasswordFocusNode.dispose();
    _fadeController.dispose();
    _slideController.dispose();
    _floatController.dispose();
    super.dispose();
  }

  void _checkPasswordStrength() {
    final password = passwordController.text;
    setState(() {
      hasMinLength = password.length >= 8;
      hasUpperCase = password.contains(RegExp(r'[A-Z]'));
      hasLowerCase = password.contains(RegExp(r'[a-z]'));
      hasDigit = password.contains(RegExp(r'[0-9]'));
      hasSpecialChar = password.contains(RegExp(r'[!@#$%^&*(),.?":{}|<>]'));
    });
  }

  double _getPasswordStrength() {
    int s = 0;
    if (hasMinLength) s++;
    if (hasUpperCase) s++;
    if (hasLowerCase) s++;
    if (hasDigit) s++;
    if (hasSpecialChar) s++;
    return s / 5;
  }

  Color _getPasswordStrengthColor() {
    final s = _getPasswordStrength();
    if (s <= 0.2) return errorColor;
    if (s <= 0.4) return warningColor;
    if (s <= 0.6) return Colors.orange;
    if (s <= 0.8) return joviGold;
    return successColor;
  }

  String _getPasswordStrengthText() {
    final s = _getPasswordStrength();
    if (s <= 0.2) return 'Very Weak';
    if (s <= 0.4) return 'Weak';
    if (s <= 0.6) return 'Fair';
    if (s <= 0.8) return 'Good';
    return 'Strong';
  }

  bool _validateEmail(String email) {
    if (email.isEmpty) return false;
    return RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,}$').hasMatch(email);
  }

  bool _canSubmit() {
    return emailController.text.isNotEmpty &&
        passwordController.text.isNotEmpty &&
        confirmPasswordController.text.isNotEmpty &&
        membershipAccepted &&
        termsAccepted &&
        !isLoading;
  }

  Future<void> _handleSignup() async {
    if (!membershipAccepted || !termsAccepted) {
      HapticFeedback.mediumImpact();
      _toastWarn('Please accept both the Membership Agreement and Terms of Service to continue');
      return;
    }
    if (passwordController.text != confirmPasswordController.text) {
      HapticFeedback.mediumImpact();
      _toastError('Passwords don\'t match');
      return;
    }
    if (!_validateEmail(emailController.text)) {
      HapticFeedback.mediumImpact();
      _toastWarn('Please enter a valid email address');
      return;
    }

    setState(() => isLoading = true);
    try {
      GoRouter.of(context).prepareAuthEvent();
      final user = await authManager.createAccountWithEmail(
          context, emailController.text, passwordController.text);
      if (user == null) {
        if (mounted) setState(() => isLoading = false);
        return;
      }
      await user.sendEmailVerification();
      HapticFeedback.lightImpact();
      if (context.mounted) {
        _toastSuccess(
            'Account created. Check ${emailController.text.trim()} to verify your email.');
        if (context.mounted) {
          context
              .goNamedAuth('verify', context.mounted, extra: <String, dynamic>{
            kTransitionInfoKey: const TransitionInfo(
                hasTransition: true, transitionType: PageTransitionType.fade)
          });
        }
      }
    } catch (e) {
      if (context.mounted) {
        _toastError('Error creating account: ${e.toString()}');
      }
    } finally {
      if (mounted) setState(() => isLoading = false);
    }
  }

  Widget _buildPasswordCheck(bool isValid, String label) {
    return AnimatedContainer(
      duration: _Motion.select,
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: isValid
            ? successColor.withOpacity(0.1)
            : Colors.grey.withOpacity(0.1),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
            color: isValid ? successColor : Colors.grey.withOpacity(0.3),
            width: 1),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(isValid ? Icons.check_circle : Icons.circle_outlined,
            size: 12, color: isValid ? successColor : textSecondary),
        const SizedBox(width: 4),
        Text(label,
            style: TextStyle(
                color: isValid ? successColor : textSecondary,
                fontSize: 11,
                fontWeight: isValid ? FontWeight.w600 : FontWeight.normal)),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    return wrapWithConstraints(
      child: Container(
        width: widget.width ?? double.infinity,
        height: widget.height ?? double.infinity,
        color: joviNavy,
        child: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) {
              return SingleChildScrollView(
                physics: const BouncingScrollPhysics(),
                child: Center(
                  child: Container(
                    constraints:
                        BoxConstraints(minHeight: constraints.maxHeight),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        // Header with Back Button
                        FadeTransition(
                          opacity: _fadeAnimation,
                          child: SlideTransition(
                            position: _slideAnimation,
                            child: Container(
                              width: double.infinity,
                              margin: EdgeInsets.only(
                                  top: layoutSettings.wideMode ? 40 : 20,
                                  left: layoutSettings.paddingH,
                                  right: layoutSettings.paddingH),
                              child: Stack(
                                children: [
                                  // Decorative coral orb
                                  Positioned(
                                      top: -20,
                                      right: -30,
                                      child: Container(
                                          width: 140,
                                          height: 140,
                                          decoration: BoxDecoration(
                                              shape: BoxShape.circle,
                                              gradient: RadialGradient(colors: [
                                                joviCoral.withOpacity(0.1),
                                                Colors.transparent
                                              ])))),
                                  Column(
                                    children: [
                                      // Back button
                                      Container(
                                        width: double.infinity,
                                        child: Row(children: [
                                          _Pressable(
                                            onTap: () {
                                              HapticFeedback.lightImpact();
                                              if (Navigator.of(context)
                                                  .canPop()) {
                                                Navigator.of(context).pop();
                                              }
                                            },
                                            child: Container(
                                              width: 44,
                                              height: 44,
                                              decoration: BoxDecoration(
                                                  color: Colors.white
                                                      .withOpacity(0.06),
                                                  borderRadius:
                                                      BorderRadius.circular(12),
                                                  border: Border.all(
                                                      color: Colors.white
                                                          .withOpacity(0.1),
                                                      width: 1)),
                                              child: Icon(
                                                  Icons.arrow_back_rounded,
                                                  color: Colors.white
                                                      .withOpacity(0.7),
                                                  size: 22),
                                            ),
                                          ),
                                        ]),
                                      ),

                                      // Header title
                                      Container(
                                        width: double.infinity,
                                        margin: EdgeInsets.only(
                                            top: layoutSettings.wideMode
                                                ? 30
                                                : 24,
                                            bottom: layoutSettings.wideMode
                                                ? 30
                                                : 20),
                                        child: Center(
                                          child: Text(
                                            'Create Your Account',
                                            textAlign: TextAlign.center,
                                            style: TextStyle(
                                                color: Colors.white,
                                                fontSize: layoutSettings
                                                    .headerFontSize,
                                                fontWeight: FontWeight.w700,
                                                letterSpacing: -0.6),
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

                        // Main Form Card
                        FadeTransition(
                          opacity: _fadeAnimation,
                          child: SlideTransition(
                            position: _slideAnimation,
                            child: Container(
                              margin: EdgeInsets.symmetric(
                                  horizontal: layoutSettings.wideMode ? 40 : 20,
                                  vertical: 20),
                              constraints: BoxConstraints(
                                  maxWidth: layoutSettings.formMaxWidth),
                              decoration: BoxDecoration(
                                color: Colors.white,
                                borderRadius: BorderRadius.circular(24),
                                boxShadow: [
                                  BoxShadow(
                                      color: Colors.black.withOpacity(0.1),
                                      blurRadius: 10,
                                      spreadRadius: 0,
                                      offset: const Offset(0, 4)),
                                  BoxShadow(
                                      color: Colors.black.withOpacity(0.08),
                                      blurRadius: 30,
                                      spreadRadius: 0,
                                      offset: const Offset(0, 10)),
                                ],
                              ),
                              child: ClipRRect(
                                borderRadius: BorderRadius.circular(24),
                                child: Container(
                                  color: Colors.white,
                                  child: Padding(
                                    padding:
                                        EdgeInsets.all(layoutSettings.paddingH),
                                    child: AutofillGroup(
                                        child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        // Step progress indicator
                                        Row(
                                          children: [
                                            Expanded(
                                              child: Container(
                                                height: 3,
                                                decoration: BoxDecoration(
                                                  gradient:
                                                      const LinearGradient(
                                                          colors: [
                                                        joviCoral,
                                                        joviCoralLight
                                                      ]),
                                                  borderRadius:
                                                      BorderRadius.circular(2),
                                                ),
                                              ),
                                            ),
                                            const SizedBox(width: 6),
                                            Expanded(
                                                child: Container(
                                                    height: 3,
                                                    decoration: BoxDecoration(
                                                        color: Colors
                                                            .grey.shade200,
                                                        borderRadius:
                                                            BorderRadius
                                                                .circular(2)))),
                                            const SizedBox(width: 6),
                                            Expanded(
                                                child: Container(
                                                    height: 3,
                                                    decoration: BoxDecoration(
                                                        color: Colors
                                                            .grey.shade200,
                                                        borderRadius:
                                                            BorderRadius
                                                                .circular(2)))),
                                          ],
                                        ),
                                        const SizedBox(height: 8),
                                        Text('Step 1 of 3',
                                            style: TextStyle(
                                                color: textSecondary,
                                                fontSize: 12,
                                                fontWeight: FontWeight.w500)),
                                        const SizedBox(height: 20),

                                        // Form Title
                                        Center(
                                          child: Text.rich(
                                            TextSpan(
                                              style: TextStyle(
                                                  fontSize: layoutSettings
                                                      .titleFontSize,
                                                  fontWeight: FontWeight.bold),
                                              children: [
                                                TextSpan(
                                                    text: 'Welcome to ',
                                                    style: TextStyle(
                                                        color: textPrimary)),
                                                TextSpan(
                                                    text: 'Jovi',
                                                    style: TextStyle(
                                                        color: joviCoral)),
                                                TextSpan(
                                                    text: ' ',
                                                    style: TextStyle(
                                                        color: textPrimary)),
                                                TextSpan(
                                                    text: 'Health',
                                                    style: TextStyle(
                                                        color: joviCoralLight)),
                                              ],
                                            ),
                                          ),
                                        ),
                                        const SizedBox(height: 8),
                                        Center(
                                            child: Text(
                                                'Affordable plans for your whole family',
                                                style: TextStyle(
                                                    fontSize: layoutSettings
                                                        .subtitleFontSize,
                                                    color: textSecondary),
                                                textAlign: TextAlign.center)),
                                        const SizedBox(height: 32),

                                        // Email Field
                                        Text('Email Address',
                                            style: TextStyle(
                                                fontSize: 14,
                                                fontWeight: FontWeight.w600,
                                                color: textPrimary)),
                                        const SizedBox(height: 8),
                                        Container(
                                          decoration: BoxDecoration(
                                            color: emailFocusNode.hasFocus
                                                ? primaryColor.withOpacity(0.05)
                                                : Colors.grey.shade50,
                                            borderRadius:
                                                BorderRadius.circular(16),
                                            border: Border.all(
                                                color: emailFocusNode.hasFocus
                                                    ? primaryColor
                                                    : emailController.text
                                                                .isNotEmpty &&
                                                            !_validateEmail(
                                                                emailController
                                                                    .text)
                                                        ? errorColor
                                                            .withOpacity(0.5)
                                                        : Colors.grey
                                                            .withOpacity(0.2),
                                                width: emailFocusNode.hasFocus
                                                    ? 2
                                                    : 1),
                                            boxShadow: emailFocusNode.hasFocus
                                                ? [
                                                    BoxShadow(
                                                        color: primaryColor
                                                            .withOpacity(0.1),
                                                        blurRadius: 8,
                                                        offset:
                                                            const Offset(0, 4))
                                                  ]
                                                : [],
                                          ),
                                          child: TextFormField(
                                            controller: emailController,
                                            focusNode: emailFocusNode,
                                            onChanged: (_) => setState(() {}),
                                            style: TextStyle(
                                                color: textPrimary,
                                                fontSize: 16),
                                            keyboardType:
                                                TextInputType.emailAddress,
                                            autofillHints: const [
                                              AutofillHints.email
                                            ],
                                            autocorrect: false,
                                            textInputAction:
                                                TextInputAction.next,
                                            decoration: InputDecoration(
                                              hintText: 'your@email.com',
                                              hintStyle: TextStyle(
                                                  color: textSecondary
                                                      .withOpacity(0.5)),
                                              prefixIcon: Icon(
                                                  Icons.email_outlined,
                                                  color: emailFocusNode.hasFocus
                                                      ? primaryColor
                                                      : textSecondary,
                                                  size: 22),
                                              suffixIcon: emailController
                                                      .text.isNotEmpty
                                                  ? Icon(
                                                      _validateEmail(
                                                              emailController
                                                                  .text)
                                                          ? Icons.check_circle
                                                          : Icons.error_outline,
                                                      color: _validateEmail(
                                                              emailController
                                                                  .text)
                                                          ? successColor
                                                          : warningColor,
                                                      size: 22)
                                                  : null,
                                              border: InputBorder.none,
                                              contentPadding:
                                                  EdgeInsets.symmetric(
                                                      horizontal: 20,
                                                      vertical: layoutSettings
                                                          .inputHeight),
                                            ),
                                          ),
                                        ),

                                        const SizedBox(height: 20),

                                        // Password Field
                                        Text('Password',
                                            style: TextStyle(
                                                fontSize: 14,
                                                fontWeight: FontWeight.w600,
                                                color: textPrimary)),
                                        const SizedBox(height: 8),
                                        Container(
                                          decoration: BoxDecoration(
                                            color: passwordFocusNode.hasFocus
                                                ? primaryColor.withOpacity(0.05)
                                                : Colors.grey.shade50,
                                            borderRadius:
                                                BorderRadius.circular(16),
                                            border: Border.all(
                                                color:
                                                    passwordFocusNode.hasFocus
                                                        ? primaryColor
                                                        : Colors.grey
                                                            .withOpacity(0.2),
                                                width:
                                                    passwordFocusNode.hasFocus
                                                        ? 2
                                                        : 1),
                                            boxShadow: passwordFocusNode
                                                    .hasFocus
                                                ? [
                                                    BoxShadow(
                                                        color: primaryColor
                                                            .withOpacity(0.1),
                                                        blurRadius: 8,
                                                        offset:
                                                            const Offset(0, 4))
                                                  ]
                                                : [],
                                          ),
                                          child: Column(children: [
                                            TextFormField(
                                              controller: passwordController,
                                              focusNode: passwordFocusNode,
                                              obscureText: !passwordVisibility,
                                              autofillHints: const [
                                                AutofillHints.newPassword
                                              ],
                                              textInputAction:
                                                  TextInputAction.next,
                                              onChanged: (_) => setState(() {}),
                                              style: TextStyle(
                                                  color: textPrimary,
                                                  fontSize: 16),
                                              decoration: InputDecoration(
                                                hintText:
                                                    'Enter a strong password',
                                                hintStyle: TextStyle(
                                                    color: textSecondary
                                                        .withOpacity(0.5)),
                                                prefixIcon: Icon(
                                                    Icons.lock_outline,
                                                    color: passwordFocusNode
                                                            .hasFocus
                                                        ? primaryColor
                                                        : textSecondary,
                                                    size: 22),
                                                suffixIcon: IconButton(
                                                    icon: Icon(
                                                        passwordVisibility
                                                            ? Icons
                                                                .visibility_outlined
                                                            : Icons
                                                                .visibility_off_outlined,
                                                        color: passwordFocusNode
                                                                .hasFocus
                                                            ? primaryColor
                                                            : textSecondary,
                                                        size: 22),
                                                    onPressed: () =>
                                                        setState(() {
                                                          passwordVisibility =
                                                              !passwordVisibility;
                                                        })),
                                                border: InputBorder.none,
                                                contentPadding:
                                                    EdgeInsets.symmetric(
                                                        horizontal: 20,
                                                        vertical: layoutSettings
                                                            .inputHeight),
                                              ),
                                            ),
                                            if (passwordController
                                                .text.isNotEmpty) ...[
                                              Padding(
                                                  padding:
                                                      const EdgeInsets.fromLTRB(
                                                          16, 0, 16, 12),
                                                  child: Column(children: [
                                                    ClipRRect(
                                                        borderRadius:
                                                            BorderRadius
                                                                .circular(8),
                                                        child: LinearProgressIndicator(
                                                            value:
                                                                _getPasswordStrength(),
                                                            backgroundColor:
                                                                Colors.grey
                                                                    .shade200,
                                                            valueColor:
                                                                AlwaysStoppedAnimation<
                                                                        Color>(
                                                                    _getPasswordStrengthColor()),
                                                            minHeight: 6)),
                                                    const SizedBox(height: 8),
                                                    Row(
                                                        mainAxisAlignment:
                                                            MainAxisAlignment
                                                                .spaceBetween,
                                                        children: [
                                                          Text(
                                                              'Strength: ${_getPasswordStrengthText()}',
                                                              style: TextStyle(
                                                                  color:
                                                                      _getPasswordStrengthColor(),
                                                                  fontSize: 13,
                                                                  fontWeight:
                                                                      FontWeight
                                                                          .w600))
                                                        ]),
                                                    const SizedBox(height: 8),
                                                    Wrap(
                                                        spacing: 6,
                                                        runSpacing: 6,
                                                        children: [
                                                          _buildPasswordCheck(
                                                              hasMinLength,
                                                              '8+ chars'),
                                                          _buildPasswordCheck(
                                                              hasUpperCase,
                                                              'ABC'),
                                                          _buildPasswordCheck(
                                                              hasLowerCase,
                                                              'abc'),
                                                          _buildPasswordCheck(
                                                              hasDigit, '123'),
                                                          _buildPasswordCheck(
                                                              hasSpecialChar,
                                                              '!@#')
                                                        ]),
                                                  ])),
                                            ],
                                          ]),
                                        ),

                                        const SizedBox(height: 20),

                                        // Confirm Password Field
                                        Text('Confirm Password',
                                            style: TextStyle(
                                                fontSize: 14,
                                                fontWeight: FontWeight.w600,
                                                color: textPrimary)),
                                        const SizedBox(height: 8),
                                        Container(
                                          decoration: BoxDecoration(
                                            color: confirmPasswordFocusNode
                                                    .hasFocus
                                                ? primaryColor.withOpacity(0.05)
                                                : Colors.grey.shade50,
                                            borderRadius:
                                                BorderRadius.circular(16),
                                            border: Border.all(
                                                color: confirmPasswordFocusNode
                                                        .hasFocus
                                                    ? primaryColor
                                                    : confirmPasswordController
                                                                .text
                                                                .isNotEmpty &&
                                                            confirmPasswordController
                                                                    .text !=
                                                                passwordController
                                                                    .text
                                                        ? errorColor
                                                            .withOpacity(0.5)
                                                        : Colors.grey
                                                            .withOpacity(0.2),
                                                width: confirmPasswordFocusNode
                                                        .hasFocus
                                                    ? 2
                                                    : 1),
                                            boxShadow: confirmPasswordFocusNode
                                                    .hasFocus
                                                ? [
                                                    BoxShadow(
                                                        color: primaryColor
                                                            .withOpacity(0.1),
                                                        blurRadius: 8,
                                                        offset:
                                                            const Offset(0, 4))
                                                  ]
                                                : [],
                                          ),
                                          child: TextFormField(
                                            controller:
                                                confirmPasswordController,
                                            focusNode: confirmPasswordFocusNode,
                                            obscureText:
                                                !confirmPasswordVisibility,
                                            autofillHints: const [
                                              AutofillHints.newPassword
                                            ],
                                            textInputAction:
                                                TextInputAction.done,
                                            onFieldSubmitted: (_) {
                                              if (_canSubmit()) _handleSignup();
                                            },
                                            onChanged: (_) => setState(() {}),
                                            style: TextStyle(
                                                color: textPrimary,
                                                fontSize: 16),
                                            decoration: InputDecoration(
                                              hintText:
                                                  'Re-enter your password',
                                              hintStyle: TextStyle(
                                                  color: textSecondary
                                                      .withOpacity(0.5)),
                                              prefixIcon: Icon(
                                                  Icons.lock_outline,
                                                  color:
                                                      confirmPasswordFocusNode
                                                              .hasFocus
                                                          ? primaryColor
                                                          : textSecondary,
                                                  size: 22),
                                              suffixIcon: Row(
                                                  mainAxisSize:
                                                      MainAxisSize.min,
                                                  children: [
                                                    if (confirmPasswordController.text
                                                            .isNotEmpty &&
                                                        passwordController
                                                            .text.isNotEmpty)
                                                      Padding(
                                                          padding:
                                                              const EdgeInsets
                                                                  .only(
                                                                  right: 8),
                                                          child: Icon(
                                                              confirmPasswordController
                                                                          .text ==
                                                                      passwordController
                                                                          .text
                                                                  ? Icons
                                                                      .check_circle
                                                                  : Icons
                                                                      .cancel,
                                                              color: confirmPasswordController
                                                                          .text ==
                                                                      passwordController
                                                                          .text
                                                                  ? successColor
                                                                  : errorColor,
                                                              size: 22)),
                                                    IconButton(
                                                        icon: Icon(
                                                            confirmPasswordVisibility
                                                                ? Icons
                                                                    .visibility_outlined
                                                                : Icons
                                                                    .visibility_off_outlined,
                                                            color: confirmPasswordFocusNode
                                                                    .hasFocus
                                                                ? primaryColor
                                                                : textSecondary,
                                                            size: 22),
                                                        onPressed: () =>
                                                            setState(() {
                                                              confirmPasswordVisibility =
                                                                  !confirmPasswordVisibility;
                                                            })),
                                                  ]),
                                              border: InputBorder.none,
                                              contentPadding: EdgeInsets.only(
                                                  left: 20,
                                                  right: 8,
                                                  top: layoutSettings
                                                      .inputHeight,
                                                  bottom: layoutSettings
                                                      .inputHeight),
                                            ),
                                          ),
                                        ),

                                        const SizedBox(height: 24),

                                        // Membership Agreement Checkbox
                                        _buildCheckboxRow(
                                          value: membershipAccepted,
                                          onChanged: (v) {
                                            setState(() => membershipAccepted =
                                                v ?? false);
                                            if (v == true)
                                              HapticFeedback.selectionClick();
                                          },
                                          linkText: 'Membership Agreement',
                                          linkUrl:
                                              'https://www.jovihealth.com/membership-agreement',
                                          showWarning: !membershipAccepted &&
                                              (emailController
                                                      .text.isNotEmpty ||
                                                  passwordController
                                                      .text.isNotEmpty),
                                        ),

                                        const SizedBox(height: 16),

                                        // Terms of Service Checkbox
                                        _buildCheckboxRow(
                                          value: termsAccepted,
                                          onChanged: (v) {
                                            setState(() =>
                                                termsAccepted = v ?? false);
                                            if (v == true)
                                              HapticFeedback.selectionClick();
                                          },
                                          linkText: 'Terms of Service',
                                          linkUrl:
                                              'https://www.jovihealth.com/terms',
                                          showWarning: !termsAccepted &&
                                              (emailController
                                                      .text.isNotEmpty ||
                                                  passwordController
                                                      .text.isNotEmpty),
                                        ),

                                        const SizedBox(height: 32),

                                        // Create Account Button — coral gradient
                                        _Pressable(
                                          enabled: _canSubmit(),
                                          feedbackOnly: true,
                                          child: Container(
                                          width: double.infinity,
                                          height: layoutSettings.buttonHeight,
                                          decoration: BoxDecoration(
                                            gradient: _canSubmit()
                                                ? const LinearGradient(
                                                    colors: [
                                                        joviCoral,
                                                        joviCoralLight
                                                      ],
                                                    begin: Alignment.centerLeft,
                                                    end: Alignment.centerRight)
                                                : null,
                                            color: !_canSubmit()
                                                ? Colors.grey.shade400
                                                : null,
                                            borderRadius:
                                                BorderRadius.circular(16),
                                            boxShadow: _canSubmit()
                                                ? [
                                                    BoxShadow(
                                                        color: joviCoral
                                                            .withOpacity(0.3),
                                                        blurRadius: 12,
                                                        offset:
                                                            const Offset(0, 6)),
                                                    BoxShadow(
                                                        color: joviCoral
                                                            .withOpacity(0.15),
                                                        blurRadius: 30,
                                                        offset: const Offset(
                                                            0, 10)),
                                                  ]
                                                : [],
                                          ),
                                          child: Material(
                                            color: Colors.transparent,
                                            borderRadius:
                                                BorderRadius.circular(16),
                                            child: InkWell(
                                              borderRadius:
                                                  BorderRadius.circular(16),
                                              onTap: _canSubmit()
                                                  ? _handleSignup
                                                  : null,
                                              child: Center(
                                                child: isLoading
                                                    ? SizedBox(
                                                        width: layoutSettings
                                                                .wideMode
                                                            ? 28
                                                            : 24,
                                                        height: layoutSettings
                                                                .wideMode
                                                            ? 28
                                                            : 24,
                                                        child:
                                                            CircularProgressIndicator(
                                                                color: Colors
                                                                    .white,
                                                                strokeWidth:
                                                                    2.5))
                                                    : Text('Create Account',
                                                        style: TextStyle(
                                                            color: Colors.white,
                                                            fontSize:
                                                                layoutSettings
                                                                        .wideMode
                                                                    ? 19
                                                                    : 17,
                                                            fontWeight:
                                                                FontWeight.w600,
                                                            letterSpacing:
                                                                -0.2)),
                                              ),
                                            ),
                                          ),
                                        )),

                                        const SizedBox(height: 24),

                                        // Or divider
                                        Row(
                                          children: [
                                            Expanded(
                                                child: Container(
                                                    height: 1,
                                                    color: Colors.grey
                                                        .withOpacity(0.15))),
                                            Padding(
                                              padding:
                                                  const EdgeInsets.symmetric(
                                                      horizontal: 16),
                                              child: Text('or',
                                                  style: TextStyle(
                                                      color: textSecondary,
                                                      fontSize: 14,
                                                      fontWeight:
                                                          FontWeight.w500)),
                                            ),
                                            Expanded(
                                                child: Container(
                                                    height: 1,
                                                    color: Colors.grey
                                                        .withOpacity(0.15))),
                                          ],
                                        ),

                                        const SizedBox(height: 16),

                                        // Already have an account
                                        Center(
                                          child: Row(
                                            mainAxisAlignment:
                                                MainAxisAlignment.center,
                                            children: [
                                              Text('Already have an account? ',
                                                  style: TextStyle(
                                                      color: textSecondary,
                                                      fontSize: 14)),
                                              TextButton(
                                                onPressed: () {
                                                  HapticFeedback.lightImpact();
                                                  context.pushNamed('logIn');
                                                },
                                                child: Text('Sign In',
                                                    style: TextStyle(
                                                        color: joviCoral,
                                                        fontSize: 14,
                                                        fontWeight:
                                                            FontWeight.bold)),
                                              ),
                                            ],
                                          ),
                                        ),
                                      ],
                                    )),
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),

                        const SizedBox(height: 40),
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }

  // Reusable checkbox row builder
  Widget _buildCheckboxRow({
    required bool value,
    required ValueChanged<bool?> onChanged,
    required String linkText,
    required String linkUrl,
    required bool showWarning,
  }) {
    return AnimatedContainer(
      duration: _Motion.select,
      padding: EdgeInsets.all(layoutSettings.paddingH * 0.8),
      decoration: BoxDecoration(
        gradient: value
            ? LinearGradient(colors: [
                joviCoral.withOpacity(0.08),
                joviCoralLight.withOpacity(0.05)
              ], begin: Alignment.topLeft, end: Alignment.bottomRight)
            : null,
        color: !value ? Colors.grey.shade50 : null,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
            color: value
                ? joviCoral.withOpacity(0.6)
                : showWarning
                    ? warningColor.withOpacity(0.4)
                    : Colors.grey.withOpacity(0.2),
            width: value ? 2 : 1),
        boxShadow: value
            ? [
                BoxShadow(
                    color: joviCoral.withOpacity(0.15),
                    blurRadius: 8,
                    offset: const Offset(0, 2))
              ]
            : [],
      ),
      child: Row(children: [
        SizedBox(
            width: layoutSettings.checkboxSize,
            height: layoutSettings.checkboxSize,
            child: Checkbox(
                value: value,
                onChanged: onChanged,
                activeColor: joviCoral,
                checkColor: Colors.white,
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(4)))),
        const SizedBox(width: 12),
        Expanded(
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          InkWell(
            onTap: () async {
              await launchURL(linkUrl);
              HapticFeedback.lightImpact();
            },
            child: Text.rich(TextSpan(
                style: TextStyle(fontSize: 14, color: textPrimary, height: 1.3),
                children: [
                  const TextSpan(
                      text: 'I have read and agree to the\n',
                      style: TextStyle(fontWeight: FontWeight.w500)),
                  TextSpan(
                      text: linkText,
                      style: TextStyle(
                          color: joviCoral,
                          fontWeight: FontWeight.w700,
                          decoration: TextDecoration.underline,
                          decorationColor: joviCoral,
                          decorationThickness: 2)),
                  TextSpan(
                      text: ' *',
                      style: TextStyle(
                          color: errorColor,
                          fontSize: 16,
                          fontWeight: FontWeight.bold)),
                ])),
          ),
          if (showWarning)
            Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                      color: warningColor.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(6)),
                  child: Text('Required to create account',
                      style: TextStyle(
                          color: warningColor,
                          fontSize: 12,
                          fontWeight: FontWeight.w600)),
                )),
        ])),
      ]),
    );
  }
}
