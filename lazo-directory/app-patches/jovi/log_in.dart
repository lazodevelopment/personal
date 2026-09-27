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

// Version 3.8 - Jovi Health Rebrand - April 2026
// Refined 2026-09-22: Apple HIG pass (press feedback, critically damped
// motion, Cupertino session dialog, navy toasts, autofill + keyboard submit).
import '/auth/firebase_auth/auth_util.dart';
import '/flutter_flow/flutter_flow_widgets.dart';
import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'dart:async';
import 'dart:ui' as ui_dart;

/// Enumerations for device categorization
enum ScreenType { compact, medium, expanded, large }

/// Configuration object for responsive layouts
class ResponsiveConfig {
  final double paddingH;
  final double paddingV;
  final double contentMax;
  final double logoWidth;
  final double logoHeight;
  final double titleFontSize;
  final double subtitleFontSize;
  final double buttonHeight;
  final double inputFontSize;
  final double labelFontSize;
  final bool wideMode;
  final bool hasHinge;
  final bool useTwoColumnLayout;
  final bool isLandscape;

  ResponsiveConfig({
    required this.paddingH,
    required this.paddingV,
    required this.contentMax,
    required this.logoWidth,
    required this.logoHeight,
    required this.titleFontSize,
    required this.subtitleFontSize,
    required this.buttonHeight,
    required this.inputFontSize,
    required this.labelFontSize,
    required this.wideMode,
    required this.hasHinge,
    this.useTwoColumnLayout = false,
    this.isLandscape = false,
  });
}

// Shared utility function for consistent phone number formatting
String formatPhoneNumber(String phone) {
  String cleaned = phone.replaceAll(RegExp(r'[^\d+]'), '');
  if (cleaned.length == 10 && !cleaned.startsWith('+')) {
    return '+1$cleaned';
  }
  if (cleaned.length == 11 &&
      cleaned.startsWith('1') &&
      !cleaned.startsWith('+')) {
    return '+$cleaned';
  }
  return cleaned.startsWith('+') ? cleaned : '+1$cleaned';
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

class PremiumLoginWidget extends StatefulWidget {
  const PremiumLoginWidget({
    Key? key,
    this.width,
    this.height,
  }) : super(key: key);

  final double? width;
  final double? height;

  @override
  _PremiumLoginWidgetState createState() => _PremiumLoginWidgetState();
}

class _PremiumLoginWidgetState extends State<PremiumLoginWidget>
    with TickerProviderStateMixin {
  // Responsive Layout Variables
  ScreenType currentScreenType = ScreenType.compact;
  ResponsiveConfig layoutSettings = ResponsiveConfig(
    paddingH: 24,
    paddingV: 20,
    contentMax: 400,
    logoWidth: 280,
    logoHeight: 140,
    titleFontSize: 32,
    subtitleFontSize: 16,
    buttonHeight: 56,
    inputFontSize: 16,
    labelFontSize: 14,
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
  Orientation? _lastOrientation;

  // Text Controllers
  TextEditingController emailTextController = TextEditingController();
  TextEditingController passwordTextController = TextEditingController();
  TextEditingController phoneTextController = TextEditingController();
  TextEditingController otpTextController = TextEditingController();

  // Focus Nodes
  FocusNode emailFieldFocusNode = FocusNode();
  FocusNode passwordFieldFocusNode = FocusNode();
  FocusNode phoneFieldFocusNode = FocusNode();
  FocusNode otpFieldFocusNode = FocusNode();

  // Animation Controllers
  AnimationController? fadeAnimationController;
  AnimationController? slideAnimationController;
  Animation<double>? fadeTransition;
  Animation<Offset>? slideTransition;

  // UI State
  bool showPassword = false;
  bool rememberUserLogin = false;
  bool loginInProgress = false;
  bool submitButtonHovered = false;
  bool createButtonHovered = false;

  // 2FA Authentication State
  bool twoFactorRequired = false;
  bool phoneNumberStep = false;
  bool otpVerificationStep = false;
  String? phoneVerificationId;
  User? authenticatedFirebaseUser;
  int? phoneResendToken;
  String? userVerificationPhone;

  // OTP Timer
  Timer? otpResendTimer;
  int otpCountdownSeconds = 0;

  // Session Management
  Timer? userSessionTimer;
  Timer? sessionWarningTimer;
  final int maxSessionMinutes = 15;
  final int warningBeforeMinutes = 2;
  bool sessionTimeoutWarningShown = false;

  // Login Security
  int loginFailureCount = 0;
  final int maxLoginAttempts = 5;
  DateTime? accountLockoutTime;
  final int lockoutDurationMinutes = 15;

  // Design Colors — mapped to Jovi palette
  final Color brandPrimary = joviCoral;
  final Color brandSecondary = joviCoralLight;
  final Color statusSuccess = joviMint;
  final Color statusWarning = const Color(0xFFFF9800);
  final Color statusError = const Color(0xFFF44336);
  final Color textMainColor = Colors.white;
  final Color textSubColor = Colors.white70;
  final Color inputBgColor = joviNavyLight;

  @override
  void initState() {
    super.initState();

    fadeAnimationController = AnimationController(
      duration: _Motion.enter,
      vsync: this,
    );
    slideAnimationController = AnimationController(
      duration: _Motion.enter,
      vsync: this,
    );

    fadeTransition = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: fadeAnimationController!,
      curve: Curves.easeOut,
    ));

    slideTransition = Tween<Offset>(
      begin: const Offset(0, 0.06),
      end: Offset.zero,
    ).animate(CurvedAnimation(
      parent: slideAnimationController!,
      curve: _Motion.settle,
    ));

    fadeAnimationController!.forward();
    slideAnimationController!.forward();

    emailFieldFocusNode.addListener(() => setState(() {}));
    passwordFieldFocusNode.addListener(() => setState(() {}));
    phoneFieldFocusNode.addListener(() => setState(() {}));
    otpFieldFocusNode.addListener(() => setState(() {}));
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    analyzeScreenConfiguration();
  }

  void analyzeScreenConfiguration() {
    final mediaQuery = MediaQuery.of(context);
    final screenWidth = mediaQuery.size.width;
    final orientation = mediaQuery.orientation;
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

    if (_lastScreenWidth == screenWidth &&
        _lastHasHinge == hasHinge &&
        _lastOrientation == orientation) {
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
    _lastOrientation = orientation;
    currentScreenType = screenType;
    layoutSettings =
        generateLayoutConfig(screenType, screenWidth, hasHinge, orientation);
  }

  ResponsiveConfig generateLayoutConfig(
    ScreenType type,
    double width,
    bool hasHinge,
    Orientation orientation,
  ) {
    final isLandscape = orientation == Orientation.landscape;
    switch (type) {
      case ScreenType.expanded:
        return ResponsiveConfig(
            paddingH: 32,
            paddingV: isLandscape ? 16 : 24,
            contentMax: width > 900 ? 600 : 500,
            logoWidth: isLandscape ? 280 : 320,
            logoHeight: isLandscape ? 100 : 120,
            titleFontSize: isLandscape ? 28 : 32,
            subtitleFontSize: isLandscape ? 14 : 16,
            buttonHeight: 56,
            inputFontSize: 16,
            labelFontSize: 14,
            wideMode: true,
            hasHinge: true,
            useTwoColumnLayout: width >= 900 && isLandscape,
            isLandscape: isLandscape);
      case ScreenType.large:
        return ResponsiveConfig(
            paddingH: width * 0.15,
            paddingV: isLandscape ? 20 : 32,
            contentMax: 600,
            logoWidth: isLandscape ? 300 : 350,
            logoHeight: isLandscape ? 110 : 150,
            titleFontSize: isLandscape ? 32 : 36,
            subtitleFontSize: isLandscape ? 16 : 18,
            buttonHeight: 60,
            inputFontSize: 18,
            labelFontSize: 15,
            wideMode: true,
            hasHinge: false,
            useTwoColumnLayout: width >= 1100 && isLandscape,
            isLandscape: isLandscape);
      case ScreenType.medium:
        return ResponsiveConfig(
            paddingH: width * 0.1,
            paddingV: isLandscape ? 16 : 24,
            contentMax: isLandscape ? 500 : 450,
            logoWidth: isLandscape ? 260 : 300,
            logoHeight: isLandscape ? 100 : 130,
            titleFontSize: isLandscape ? 26 : 30,
            subtitleFontSize: isLandscape ? 14 : 16,
            buttonHeight: 56,
            inputFontSize: 16,
            labelFontSize: 14,
            wideMode: true,
            hasHinge: false,
            useTwoColumnLayout: width >= 900 && isLandscape,
            isLandscape: isLandscape);
      case ScreenType.compact:
      default:
        return ResponsiveConfig(
            paddingH: width < 360 ? 20 : 24,
            paddingV: isLandscape ? 12 : 20,
            contentMax: 400,
            logoWidth: width < 360 ? 240 : 280,
            logoHeight: isLandscape ? 80 : (width < 360 ? 120 : 140),
            titleFontSize: width < 360 ? 28 : 32,
            subtitleFontSize: width < 360 ? 14 : 16,
            buttonHeight: 56,
            inputFontSize: 16,
            labelFontSize: 14,
            wideMode: false,
            hasHinge: false,
            useTwoColumnLayout: false,
            isLandscape: isLandscape);
    }
  }

  Widget wrapWithConstraints({required Widget child}) {
    if (currentScreenType == ScreenType.expanded || layoutSettings.hasHinge)
      return child;
    return Center(
        child: ConstrainedBox(
            constraints: BoxConstraints(maxWidth: layoutSettings.contentMax),
            child: child));
  }

  @override
  void dispose() {
    emailTextController.dispose();
    passwordTextController.dispose();
    phoneTextController.dispose();
    otpTextController.dispose();
    emailFieldFocusNode.dispose();
    passwordFieldFocusNode.dispose();
    phoneFieldFocusNode.dispose();
    otpFieldFocusNode.dispose();
    fadeAnimationController?.dispose();
    slideAnimationController?.dispose();
    otpResendTimer?.cancel();
    userSessionTimer?.cancel();
    sessionWarningTimer?.cancel();
    super.dispose();
  }

  bool validateEmailFormat(String email) {
    if (email.isEmpty) return false;
    return RegExp(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        .hasMatch(email);
  }

  bool canSubmitLogin() {
    return emailTextController.text.isNotEmpty &&
        passwordTextController.text.isNotEmpty &&
        !loginInProgress &&
        !isAccountCurrentlyLocked();
  }

  bool isAccountCurrentlyLocked() {
    if (accountLockoutTime != null) {
      final currentTime = DateTime.now();
      if (currentTime.isBefore(accountLockoutTime!)) return true;
      accountLockoutTime = null;
      loginFailureCount = 0;
      return false;
    }
    return false;
  }

  String getAccountLockoutMessage() {
    if (accountLockoutTime != null) {
      final timeRemaining = accountLockoutTime!.difference(DateTime.now());
      final minutesLeft = timeRemaining.inMinutes;
      final secondsLeft = timeRemaining.inSeconds % 60;
      if (minutesLeft > 0)
        return 'Account locked. Try again in $minutesLeft min ${secondsLeft}s';
      return 'Account locked. Try again in ${secondsLeft}s';
    }
    return '';
  }

  void processFailedLoginAttempt([String? customError]) {
    if (!mounted) return;
    setState(() {
      loginFailureCount++;
      if (loginFailureCount >= maxLoginAttempts) {
        accountLockoutTime =
            DateTime.now().add(Duration(minutes: lockoutDurationMinutes));
        FirebaseFirestore.instance.collection('security_logs').add({
          'event': 'account_locked',
          'email': emailTextController.text,
          'timestamp': FieldValue.serverTimestamp(),
          'reason': 'max_login_attempts_exceeded'
        }).catchError((error) => debugPrint('Security logging error: $error'));
        _toastError('Too many failed attempts. Account locked for $lockoutDurationMinutes minutes.');
      } else {
        final attemptsLeft = maxLoginAttempts - loginFailureCount;
        String displayError = customError ?? 'Invalid credentials';
        _toastWarn('$displayError. $attemptsLeft attempts remaining.');
      }
    });
  }

  void initializeUserSessionTimer() {
    userSessionTimer?.cancel();
    sessionWarningTimer?.cancel();
    if (FirebaseAuth.instance.currentUser == null) return;
    sessionWarningTimer =
        Timer(Duration(minutes: maxSessionMinutes - warningBeforeMinutes), () {
      if (mounted && FirebaseAuth.instance.currentUser != null) {
        setState(() => sessionTimeoutWarningShown = true);
        displaySessionTimeoutWarning();
      }
    });
    userSessionTimer = Timer(Duration(minutes: maxSessionMinutes), () {
      if (mounted && FirebaseAuth.instance.currentUser != null)
        executeSessionTimeout();
    });
  }

  void displaySessionTimeoutWarning() {
    if (!mounted) return;
    showDialog(
        context: context,
        barrierDismissible: false,
        builder: (BuildContext dialogContext) {
          return CupertinoAlertDialog(
            title: const Text('Session Expiring Soon'),
            content: Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                  'Your session will expire in $warningBeforeMinutes minutes due to inactivity. Would you like to continue?'),
            ),
            actions: [
              CupertinoDialogAction(
                  isDestructiveAction: true,
                  onPressed: () {
                    Navigator.of(dialogContext).pop();
                    executeSessionTimeout();
                  },
                  child: const Text('Sign Out')),
              CupertinoDialogAction(
                  isDefaultAction: true,
                  onPressed: () {
                    Navigator.of(dialogContext).pop();
                    initializeUserSessionTimer();
                    setState(() => sessionTimeoutWarningShown = false);
                  },
                  child: const Text('Continue')),
            ],
          );
        });
  }

  void executeSessionTimeout() {
    if (FirebaseAuth.instance.currentUser != null) {
      FirebaseFirestore.instance.collection('security_logs').add({
        'event': 'session_timeout',
        'user_id': FirebaseAuth.instance.currentUser!.uid,
        'timestamp': FieldValue.serverTimestamp(),
        'reason': 'inactivity_timeout'
      }).catchError((error) => debugPrint('Session timeout logging error: $error'));
    }
    authManager.signOut();
    if (mounted) {
      _toastWarn('Your session has expired for security. Please sign in again.');
      setState(() {
        twoFactorRequired = false;
        phoneNumberStep = false;
        otpVerificationStep = false;
        authenticatedFirebaseUser = null;
        passwordTextController.clear();
        otpTextController.clear();
      });
    }
  }

  Future<void> executeUserLogin() async {
    if (isAccountCurrentlyLocked()) {
      HapticFeedback.heavyImpact();
      _toastError(getAccountLockoutMessage());
      return;
    }
    if (!validateEmailFormat(emailTextController.text)) {
      HapticFeedback.mediumImpact();
      _toastWarn('Please enter a valid email address');
      return;
    }
    setState(() => loginInProgress = true);
    try {
      final cleanedEmail = emailTextController.text.trim().toLowerCase();
      UserCredential authResult = await FirebaseAuth.instance
          .signInWithEmailAndPassword(
              email: cleanedEmail, password: passwordTextController.text);
      final firebaseUser = authResult.user;
      if (firebaseUser == null) {
        if (mounted) setState(() => loginInProgress = false);
        _toastError('Authentication error. Please try again.');
        return;
      }
      setState(() {
        loginFailureCount = 0;
        accountLockoutTime = null;
        authenticatedFirebaseUser = firebaseUser;
      });
      if (!firebaseUser.emailVerified) {
        HapticFeedback.mediumImpact();
        await FirebaseAuth.instance.signOut();
        if (mounted) setState(() => loginInProgress = false);
        if (mounted) {
          _toastWarn('Please verify your email before logging in. Check your inbox for the verification link.');
        }
        return;
      }
      try {
        final userDocument = await FirebaseFirestore.instance
            .collection('users')
            .doc(firebaseUser.uid)
            .get();
        if (!userDocument.exists) {
          await FirebaseFirestore.instance
              .collection('users')
              .doc(firebaseUser.uid)
              .set({
            'email': firebaseUser.email,
            'uid': firebaseUser.uid,
            'created_time': FieldValue.serverTimestamp(),
            'two_fa_enabled': false,
            'requires_2fa': false,
            'phone_verified': false
          });
        }
        final userData = userDocument.data();
        final hasVerifiedPhone = (userData?['phone_number'] != null &&
                userData!['phone_number'].toString().isNotEmpty) &&
            (userData['phone_verified'] == true);
        final twoFactorEnabled = userData?['two_fa_enabled'] == true;
        final mustUseTwoFactor = userData?['requires_2fa'] == true;
        if (!mustUseTwoFactor) {
          await finishLoginProcess(firebaseUser);
        } else if (hasVerifiedPhone && twoFactorEnabled) {
          userVerificationPhone = userData!['phone_number'];
          setState(() {
            twoFactorRequired = true;
            otpVerificationStep = true;
            loginInProgress = false;
          });
          await sendPhoneVerificationCode(userVerificationPhone!);
        } else {
          setState(() {
            twoFactorRequired = true;
            phoneNumberStep = true;
            loginInProgress = false;
          });
        }
      } catch (firestoreError) {
        await finishLoginProcess(firebaseUser);
      }
    } on FirebaseAuthException catch (authError) {
      String displayMessage = 'Authentication failed';
      switch (authError.code) {
        case 'user-not-found':
          displayMessage = 'No account found with this email';
          break;
        case 'wrong-password':
          displayMessage = 'Incorrect password';
          break;
        case 'invalid-email':
          displayMessage = 'Invalid email address';
          break;
        case 'user-disabled':
          displayMessage = 'This account has been disabled';
          break;
        case 'too-many-requests':
          displayMessage = 'Too many attempts. Please try again later';
          break;
        case 'invalid-credential':
          displayMessage = 'Invalid email or password';
          break;
        case 'network-request-failed':
          displayMessage = 'Network error. Please check your connection';
          break;
        default:
          displayMessage = authError.message ?? 'Authentication failed';
      }
      await FirebaseAuth.instance
          .signOut()
          .catchError((error) => debugPrint('Sign out error: $error'));
      processFailedLoginAttempt(displayMessage);
      HapticFeedback.heavyImpact();
      if (mounted) setState(() => loginInProgress = false);
    } catch (generalError) {
      if (mounted) setState(() => loginInProgress = false);
      if (mounted) {
        _toastError('An unexpected error occurred. Please try again.');
      }
    }
  }

  Future<void> finishLoginProcess(User user) async {
    if (!mounted) return;
    try {
      FirebaseFirestore.instance.collection('security_logs').add({
        'event': 'login_success',
        'user_id': user.uid,
        'timestamp': FieldValue.serverTimestamp(),
        'authentication_method': 'email_password_only'
      }).catchError((error) => debugPrint('Logging error: $error'));
      FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .update({'last_login': FieldValue.serverTimestamp()}).catchError(
              (error) => debugPrint('Update error: $error'));
      FFAppState().update(() {});
      if (mounted) setState(() => loginInProgress = false);
      HapticFeedback.lightImpact();
      if (context.mounted) {
        initializeUserSessionTimer();
        context.pushReplacementNamed('home', extra: <String, dynamic>{
          kTransitionInfoKey: TransitionInfo(
              hasTransition: true,
              transitionType: PageTransitionType.fade,
              duration: Duration(milliseconds: 300))
        });
      }
    } catch (navigationError) {
      if (mounted) setState(() => loginInProgress = false);
      if (mounted) {
        _toastWarn('Login successful but navigation failed. Please try refreshing.');
      }
    }
  }

  Future<void> sendPhoneVerificationCode(String phoneNumber) async {
    setState(() => loginInProgress = true);
    try {
      String formattedPhoneNumber = formatPhoneNumber(phoneNumber);
      await FirebaseAuth.instance.verifyPhoneNumber(
        phoneNumber: formattedPhoneNumber,
        verificationCompleted: (PhoneAuthCredential credential) async {
          await verifyOtpAndFinishLogin(credential);
        },
        verificationFailed: (FirebaseAuthException error) {
          if (mounted) setState(() => loginInProgress = false);
          String errorMessage = error.code == 'invalid-phone-number'
              ? 'Invalid phone number format'
              : error.code == 'too-many-requests'
                  ? 'Too many requests. Please try again later'
                  : (error.message ?? 'Phone verification failed');
          if (mounted)
            _toastError(errorMessage);
        },
        codeSent: (String verificationId, int? token) {
          setState(() {
            phoneVerificationId = verificationId;
            phoneResendToken = token;
            loginInProgress = false;
            startOtpResendCountdown();
          });
          if (mounted)
            _toastSuccess('Verification code sent to $formattedPhoneNumber');
        },
        codeAutoRetrievalTimeout: (String verificationId) {
          phoneVerificationId = verificationId;
        },
        forceResendingToken: phoneResendToken,
        timeout: const Duration(seconds: 60),
      );
    } catch (error) {
      if (mounted) setState(() => loginInProgress = false);
      if (mounted)
        _toastError('Error sending verification code: ${error.toString()}');
    }
  }

  Future<void> verifyOtpAndFinishLogin(PhoneAuthCredential? credential) async {
    setState(() => loginInProgress = true);
    try {
      if (authenticatedFirebaseUser == null)
        throw Exception('No authenticated user found');
      PhoneAuthCredential otpCredential;
      if (credential != null) {
        otpCredential = credential;
      } else {
        if (phoneVerificationId == null || otpTextController.text.isEmpty)
          throw Exception('Invalid OTP data');
        otpCredential = PhoneAuthProvider.credential(
            verificationId: phoneVerificationId!,
            smsCode: otpTextController.text);
      }
      try {
        if (authenticatedFirebaseUser!.phoneNumber == null ||
            authenticatedFirebaseUser!.phoneNumber!.isEmpty) {
          await authenticatedFirebaseUser!.linkWithCredential(otpCredential);
          await authenticatedFirebaseUser!.reload();
          authenticatedFirebaseUser = FirebaseAuth.instance.currentUser;
        } else {
          final tempCredential =
              await FirebaseAuth.instance.signInWithCredential(otpCredential);
          if (tempCredential.user?.uid != authenticatedFirebaseUser!.uid)
            await authenticatedFirebaseUser!.reload();
        }
      } catch (linkingError) {
        if (!linkingError.toString().contains('already been linked') &&
            !linkingError.toString().contains('phone-number-already-exists'))
          throw linkingError;
      }
      if (phoneNumberStep) {
        final formattedPhone =
            formatPhoneNumber(phoneTextController.text.trim());
        await FirebaseFirestore.instance
            .collection('users')
            .doc(authenticatedFirebaseUser!.uid)
            .set({
          'phone_number': formattedPhone,
          'two_fa_enabled': true,
          'requires_2fa': true,
          'phone_verified': true,
          'phone_verified_at': FieldValue.serverTimestamp(),
          'last_login': FieldValue.serverTimestamp()
        }, SetOptions(merge: true));
      } else {
        await FirebaseFirestore.instance
            .collection('users')
            .doc(authenticatedFirebaseUser!.uid)
            .set({
          'last_login': FieldValue.serverTimestamp(),
          'last_2fa_verification': FieldValue.serverTimestamp()
        }, SetOptions(merge: true));
      }
      FirebaseFirestore.instance.collection('security_logs').add({
        'event': '2fa_success',
        'user_id': authenticatedFirebaseUser!.uid,
        'timestamp': FieldValue.serverTimestamp(),
        'authentication_method': 'sms_otp'
      });
      passwordTextController.clear();
      otpTextController.clear();
      FFAppState().update(() {});
      HapticFeedback.lightImpact();
      await Future.delayed(Duration(milliseconds: 300));
      await FirebaseAuth.instance.currentUser?.reload();
      if (FirebaseAuth.instance.currentUser != null && context.mounted) {
        if (mounted) setState(() => loginInProgress = false);
        initializeUserSessionTimer();
        context.pushReplacementNamed('home', extra: <String, dynamic>{
          kTransitionInfoKey: TransitionInfo(
              hasTransition: true,
              transitionType: PageTransitionType.fade,
              duration: Duration(milliseconds: 300))
        });
      } else {
        throw Exception('Authentication lost during 2FA');
      }
    } catch (error) {
      if (mounted) setState(() => loginInProgress = false);
      String errorMessage =
          error.toString().contains('invalid-verification-code')
              ? 'Invalid verification code'
              : error.toString().contains('session-expired')
                  ? 'Code expired. Please request a new one'
                  : error.toString().contains('Authentication lost')
                      ? 'Authentication error. Please sign in again'
                      : 'OTP verification failed';
      if (error.toString().contains('Authentication lost')) {
        await authManager.signOut();
        setState(() {
          twoFactorRequired = false;
          phoneNumberStep = false;
          otpVerificationStep = false;
          authenticatedFirebaseUser = null;
        });
      }
      if (mounted)
        _toastError(errorMessage);
    }
  }

  void startOtpResendCountdown() {
    otpCountdownSeconds = 30;
    otpResendTimer?.cancel();
    otpResendTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      setState(() {
        if (otpCountdownSeconds > 0)
          otpCountdownSeconds--;
        else
          timer.cancel();
      });
    });
  }

  Future<void> handlePhoneNumberSubmission() async {
    final phoneInput = phoneTextController.text.trim();
    if (phoneInput.isEmpty || phoneInput.length < 10) {
      _toastWarn('Please enter a valid phone number');
      return;
    }
    String formattedPhoneInput = formatPhoneNumber(phoneInput);
    setState(() {
      phoneNumberStep = false;
      otpVerificationStep = true;
    });
    await sendPhoneVerificationCode(formattedPhoneInput);
  }

  @override
  Widget build(BuildContext context) {
    final mediaQuery = MediaQuery.of(context);
    final screenWidth = mediaQuery.size.width;
    final screenHeight = mediaQuery.size.height;

    Widget content = SingleChildScrollView(
      child: Column(
        children: [
          FadeTransition(
            opacity: fadeTransition!,
            child: SlideTransition(
              position: slideTransition!,
              child: Container(
                width: double.infinity,
                color: joviNavy,
                padding: EdgeInsets.symmetric(
                  horizontal: layoutSettings.paddingH,
                  vertical: layoutSettings.paddingV,
                ),
                child: Stack(
                  children: [
                    // Decorative coral orb
                    Positioned(
                      top: 30,
                      right: -40,
                      child: Container(
                        width: 180,
                        height: 180,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: RadialGradient(
                            colors: [
                              joviCoral.withOpacity(0.08),
                              Colors.transparent
                            ],
                          ),
                        ),
                      ),
                    ),
                    // Subtle mint orb
                    Positioned(
                      bottom: 100,
                      left: -30,
                      child: Container(
                        width: 120,
                        height: 120,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: RadialGradient(
                            colors: [
                              joviMint.withOpacity(0.05),
                              Colors.transparent
                            ],
                          ),
                        ),
                      ),
                    ),
                    Column(
                      children: [
                        SizedBox(height: layoutSettings.isLandscape ? 12 : 20),
                        // Back arrow
                        Align(
                          alignment: Alignment.centerLeft,
                          child: _Pressable(
                            onTap: () {
                              HapticFeedback.lightImpact();
                              if (Navigator.of(context).canPop()) {
                                Navigator.of(context).pop();
                              }
                            },
                            child: Container(
                              width: 44,
                              height: 44,
                              decoration: BoxDecoration(
                                color: Colors.white.withOpacity(0.06),
                                borderRadius: BorderRadius.circular(12),
                                border: Border.all(
                                    color: Colors.white.withOpacity(0.1),
                                    width: 1),
                              ),
                              child: Icon(Icons.arrow_back_rounded,
                                  color: Colors.white.withOpacity(0.7),
                                  size: 22),
                            ),
                          ),
                        ),
                        SizedBox(height: layoutSettings.isLandscape ? 12 : 24),
                        // Logo
                        TweenAnimationBuilder<double>(
                          tween: Tween(begin: _reduceMotion ? 1.0 : 0.94, end: 1.0),
                          duration: _Motion.enter,
                          curve: _Motion.settle,
                          builder: (context, value, child) {
                            return Transform.scale(
                              scale: value,
                              child: Container(
                                width: layoutSettings.logoWidth * 1.1,
                                height: layoutSettings.logoHeight * 0.85,
                                child: Image.network(
                                  'https://storage.googleapis.com/flutterflow-io-6f20.appspot.com/projects/kurv-health-3vcfmp/assets/gveqn2eoe4nf/jovi_header_logo_master.png',
                                  fit: BoxFit.contain,
                                  loadingBuilder:
                                      (context, child, loadingProgress) {
                                    if (loadingProgress == null) return child;
                                    return Center(
                                        child: CircularProgressIndicator(
                                            color: joviCoral));
                                  },
                                  errorBuilder: (context, error, stackTrace) {
                                    return Center(
                                      child: Text('jovi',
                                          style: TextStyle(
                                              color: Colors.white,
                                              fontSize:
                                                  layoutSettings.titleFontSize *
                                                      1.5,
                                              fontWeight: FontWeight.w800,
                                              letterSpacing: -2)),
                                    );
                                  },
                                ),
                              ),
                            );
                          },
                        ),
                        SizedBox(height: layoutSettings.isLandscape ? 15 : 30),
                        // Welcome text
                        Text(
                          'Welcome Back',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: layoutSettings.titleFontSize,
                            fontWeight: FontWeight.w700,
                            letterSpacing: -0.6,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          twoFactorRequired
                              ? 'Complete verification to continue'
                              : 'Sign in to continue to your account',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.6),
                            fontSize: layoutSettings.subtitleFontSize,
                          ),
                          textAlign: TextAlign.center,
                        ),
                        SizedBox(height: layoutSettings.isLandscape ? 20 : 40),
                        wrapWithConstraints(
                          child: !twoFactorRequired
                              ? buildMainLoginForm()
                              : phoneNumberStep
                                  ? buildPhoneNumberForm()
                                  : buildOtpVerificationForm(),
                        ),
                        SizedBox(height: layoutSettings.isLandscape ? 20 : 40),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),
          // Footer section — coral gradient
          Container(
            width: double.infinity,
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [joviCoral, joviCoralLight],
              ),
            ),
            padding: EdgeInsets.all(layoutSettings.isLandscape ? 24 : 40),
            child: Column(
              children: [
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                        color: Colors.white.withOpacity(0.2), width: 1),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.security, color: Colors.white, size: 20),
                      SizedBox(width: 8),
                      Text(
                        twoFactorRequired
                            ? 'Two-Factor Authentication'
                            : 'Secure Login',
                        style: TextStyle(
                            color: Colors.white,
                            fontSize: 14,
                            fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ),
                SizedBox(height: layoutSettings.isLandscape ? 15 : 30),
                Text(
                  'Your health data is protected',
                  style: TextStyle(
                      color: Colors.white,
                      fontSize: layoutSettings.subtitleFontSize + 2,
                      fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 12),
                Text(
                  'HIPAA Compliant • Bank-Level Encryption • Private & Secure',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                      color: Colors.white.withOpacity(0.8),
                      fontSize: layoutSettings.labelFontSize),
                ),
                SizedBox(height: layoutSettings.isLandscape ? 20 : 40),
                Text(
                  '© 2026 Jovi Health LLC. All rights reserved.',
                  style: TextStyle(
                      color: Colors.white.withOpacity(0.6), fontSize: 12),
                ),
              ],
            ),
          ),
        ],
      ),
    );

    return Container(
      width: widget.width ?? screenWidth,
      height: widget.height ?? screenHeight,
      color: joviNavy,
      child: SafeArea(
        child: MediaQuery(
          data: mediaQuery.removePadding(removeTop: false, removeBottom: false),
          child: content,
        ),
      ),
    );
  }

  // Input field builder for dark theme
  Widget _buildInputField({
    required TextEditingController controller,
    required FocusNode focusNode,
    required String label,
    required String hint,
    required IconData icon,
    bool obscure = false,
    Widget? suffixIcon,
    TextInputType keyboardType = TextInputType.text,
    int? maxLength,
    TextStyle? textStyle,
    List<String>? autofillHints,
    TextInputAction? textInputAction,
    ValueChanged<String>? onSubmitted,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: focusNode.hasFocus
            ? joviCoral.withOpacity(0.08)
            : Colors.white.withOpacity(0.06),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: focusNode.hasFocus ? joviCoral : Colors.white.withOpacity(0.1),
          width: focusNode.hasFocus ? 2 : 1,
        ),
      ),
      child: TextFormField(
        controller: controller,
        focusNode: focusNode,
        obscureText: obscure,
        onChanged: (_) => setState(() {}),
        style: textStyle ??
            TextStyle(
                color: Colors.white, fontSize: layoutSettings.inputFontSize),
        keyboardType: keyboardType,
        maxLength: maxLength,
        autofillHints: autofillHints,
        textInputAction: textInputAction,
        onFieldSubmitted: onSubmitted,
        autocorrect: false,
        decoration: InputDecoration(
          labelText: label,
          labelStyle: TextStyle(
              color: focusNode.hasFocus
                  ? joviCoral
                  : Colors.white.withOpacity(0.5),
              fontSize: layoutSettings.labelFontSize),
          hintText: hint,
          hintStyle: TextStyle(color: Colors.white.withOpacity(0.2)),
          prefixIcon: Icon(icon,
              color: focusNode.hasFocus
                  ? joviCoral
                  : Colors.white.withOpacity(0.4),
              size: 20),
          suffixIcon: suffixIcon,
          counterText: '',
          border: InputBorder.none,
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        ),
      ),
    );
  }

  Widget buildMainLoginForm() {
    return AutofillGroup(
        child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (isAccountCurrentlyLocked()) ...[
          Container(
            padding: EdgeInsets.all(12),
            decoration: BoxDecoration(
                color: statusError.withOpacity(0.15),
                borderRadius: BorderRadius.circular(12),
                border:
                    Border.all(color: statusError.withOpacity(0.3), width: 1)),
            child: Row(children: [
              Icon(Icons.lock_clock, color: statusError, size: 20),
              SizedBox(width: 8),
              Expanded(
                  child: Text(getAccountLockoutMessage(),
                      style: TextStyle(
                          color: statusError,
                          fontSize: layoutSettings.labelFontSize,
                          fontWeight: FontWeight.w600)))
            ]),
          ),
          SizedBox(height: 16),
        ],
        if (loginFailureCount > 0 && loginFailureCount < maxLoginAttempts) ...[
          Container(
            padding: EdgeInsets.all(12),
            decoration: BoxDecoration(
                color: statusWarning.withOpacity(0.15),
                borderRadius: BorderRadius.circular(12)),
            child: Row(children: [
              Icon(Icons.warning_amber_rounded, color: statusWarning, size: 20),
              SizedBox(width: 8),
              Text(
                  '${maxLoginAttempts - loginFailureCount} login attempts remaining',
                  style: TextStyle(
                      color: statusWarning,
                      fontSize: layoutSettings.labelFontSize,
                      fontWeight: FontWeight.w600))
            ]),
          ),
          SizedBox(height: 16),
        ],
        _buildInputField(
            controller: emailTextController,
            focusNode: emailFieldFocusNode,
            label: 'Email',
            hint: 'your@email.com',
            icon: Icons.mail_outline_rounded,
            keyboardType: TextInputType.emailAddress,
            autofillHints: const [AutofillHints.email],
            textInputAction: TextInputAction.next),
        const SizedBox(height: 16),
        _buildInputField(
          controller: passwordTextController,
          focusNode: passwordFieldFocusNode,
          label: 'Password',
          hint: '••••••••',
          icon: Icons.lock_outline_rounded,
          obscure: !showPassword,
          autofillHints: const [AutofillHints.password],
          textInputAction: TextInputAction.go,
          onSubmitted: (_) {
            if (canSubmitLogin()) executeUserLogin();
          },
          suffixIcon: IconButton(
              icon: Icon(
                  showPassword
                      ? Icons.visibility_rounded
                      : Icons.visibility_off_rounded,
                  color: Colors.white.withOpacity(0.4),
                  size: 20),
              onPressed: () => setState(() => showPassword = !showPassword)),
        ),
        const SizedBox(height: 12),
        Align(
          alignment: Alignment.centerRight,
          child: TextButton(
            onPressed: () {
              HapticFeedback.lightImpact();
              context.pushNamed('pwReset');
            },
            child: Text('Forgot Password?',
                style: TextStyle(
                    color: joviCoral,
                    fontSize: layoutSettings.labelFontSize,
                    fontWeight: FontWeight.w600)),
          ),
        ),
        const SizedBox(height: 24),
        // Sign In Button — coral gradient
        _Pressable(
          enabled: canSubmitLogin(),
          feedbackOnly: true,
          child: MouseRegion(
          onEnter: (_) => setState(() => submitButtonHovered = true),
          onExit: (_) => setState(() => submitButtonHovered = false),
          child: AnimatedContainer(
            duration: _Motion.select,
            height: layoutSettings.buttonHeight,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                  colors: canSubmitLogin()
                      ? [joviCoral, joviCoralLight]
                      : [
                          Colors.white.withOpacity(0.1),
                          Colors.white.withOpacity(0.1)
                        ]),
              borderRadius: BorderRadius.circular(16),
              boxShadow: canSubmitLogin()
                  ? [
                      BoxShadow(
                          color: joviCoral
                              .withOpacity(submitButtonHovered ? 0.5 : 0.3),
                          blurRadius: submitButtonHovered ? 30 : 16,
                          spreadRadius: submitButtonHovered ? 2 : 0,
                          offset: Offset(0, submitButtonHovered ? 8 : 4)),
                      BoxShadow(
                          color: joviCoral.withOpacity(0.15),
                          blurRadius: 40,
                          spreadRadius: -4,
                          offset: const Offset(0, 12)),
                    ]
                  : [],
            ),
            child: Material(
              color: Colors.transparent,
              borderRadius: BorderRadius.circular(16),
              child: InkWell(
                borderRadius: BorderRadius.circular(16),
                onTap: canSubmitLogin() ? executeUserLogin : null,
                child: Center(
                  child: loginInProgress
                      ? const SizedBox(
                          width: 24,
                          height: 24,
                          child: CircularProgressIndicator(
                              color: Colors.white, strokeWidth: 2.5))
                      : Text('Sign In',
                          style: TextStyle(
                              color: canSubmitLogin()
                                  ? Colors.white
                                  : Colors.white.withOpacity(0.3),
                              fontSize: layoutSettings.inputFontSize + 1,
                              fontWeight: FontWeight.bold)),
                ),
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
                    height: 1, color: Colors.white.withOpacity(0.08))),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Text('or',
                  style: TextStyle(
                      color: Colors.white.withOpacity(0.3),
                      fontSize: layoutSettings.labelFontSize,
                      fontWeight: FontWeight.w500)),
            ),
            Expanded(
                child: Container(
                    height: 1, color: Colors.white.withOpacity(0.08))),
          ],
        ),
        const SizedBox(height: 16),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text("Don't have an account? ",
                style: TextStyle(
                    color: Colors.white.withOpacity(0.5),
                    fontSize: layoutSettings.labelFontSize)),
            TextButton(
              onPressed: () {
                HapticFeedback.lightImpact();
                context.pushNamed('createAccount');
              },
              child: Text('Create Account',
                  style: TextStyle(
                      color: joviCoral,
                      fontSize: layoutSettings.labelFontSize,
                      fontWeight: FontWeight.bold)),
            ),
          ],
        ),
      ],
    ));
  }

  Widget buildPhoneNumberForm() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Container(
          padding: EdgeInsets.all(12),
          decoration: BoxDecoration(
              color: joviMint.withOpacity(0.15),
              borderRadius: BorderRadius.circular(12)),
          child: Row(children: [
            Icon(Icons.security, color: joviMint, size: 20),
            SizedBox(width: 8),
            Expanded(
                child: Text('Two-Factor Authentication Required',
                    style: TextStyle(
                        color: joviMint,
                        fontWeight: FontWeight.w600,
                        fontSize: layoutSettings.labelFontSize)))
          ]),
        ),
        SizedBox(height: 20),
        Text('Add your phone number',
            style: TextStyle(
                fontSize: layoutSettings.titleFontSize * 0.7,
                fontWeight: FontWeight.bold,
                color: Colors.white)),
        SizedBox(height: 8),
        Text('We\'ll send you a verification code to secure your account',
            style: TextStyle(
                fontSize: layoutSettings.labelFontSize,
                color: Colors.white.withOpacity(0.6))),
        SizedBox(height: 24),
        _buildInputField(
            controller: phoneTextController,
            focusNode: phoneFieldFocusNode,
            label: 'Phone Number',
            hint: '(555) 123-4567',
            icon: Icons.phone,
            keyboardType: TextInputType.phone,
            autofillHints: const [AutofillHints.telephoneNumber],
            textInputAction: TextInputAction.done,
            onSubmitted: (_) {
              if (!loginInProgress) handlePhoneNumberSubmission();
            }),
        SizedBox(height: 24),
        _Pressable(
          enabled: !loginInProgress,
          feedbackOnly: true,
          child: Container(
          height: layoutSettings.buttonHeight,
          decoration: BoxDecoration(
              gradient:
                  const LinearGradient(colors: [joviCoral, joviCoralLight]),
              borderRadius: BorderRadius.circular(16),
              boxShadow: [
                BoxShadow(
                    color: joviCoral.withOpacity(0.2),
                    blurRadius: 10,
                    offset: Offset(0, 5))
              ]),
          child: Material(
              color: Colors.transparent,
              borderRadius: BorderRadius.circular(16),
              child: InkWell(
                  borderRadius: BorderRadius.circular(16),
                  onTap: loginInProgress ? null : handlePhoneNumberSubmission,
                  child: Center(
                      child: loginInProgress
                          ? const SizedBox(
                              width: 24,
                              height: 24,
                              child: CircularProgressIndicator(
                                  color: Colors.white, strokeWidth: 2.5))
                          : Text('Send Verification Code',
                              style: TextStyle(
                                  color: Colors.white,
                                  fontSize: layoutSettings.inputFontSize + 1,
                                  fontWeight: FontWeight.bold))))),
        )),
        SizedBox(height: 16),
        TextButton(
            onPressed: () async {
              await authManager.signOut();
              if (!mounted) return;
              setState(() {
                twoFactorRequired = false;
                phoneNumberStep = false;
                otpVerificationStep = false;
                authenticatedFirebaseUser = null;
                phoneTextController.clear();
              });
            },
            child: Text('Cancel and Sign Out',
                style: TextStyle(
                    color: statusError,
                    fontSize: layoutSettings.labelFontSize,
                    fontWeight: FontWeight.w600))),
      ],
    );
  }

  Widget buildOtpVerificationForm() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Container(
          padding: EdgeInsets.all(12),
          decoration: BoxDecoration(
              color: joviMint.withOpacity(0.15),
              borderRadius: BorderRadius.circular(12)),
          child: Row(children: [
            Icon(Icons.check_circle, color: joviMint, size: 20),
            SizedBox(width: 8),
            Text('Code Sent Successfully',
                style: TextStyle(
                    color: joviMint,
                    fontWeight: FontWeight.w600,
                    fontSize: layoutSettings.labelFontSize))
          ]),
        ),
        SizedBox(height: 20),
        Text('Enter verification code',
            style: TextStyle(
                fontSize: layoutSettings.titleFontSize * 0.7,
                fontWeight: FontWeight.bold,
                color: Colors.white)),
        SizedBox(height: 8),
        Text('We sent a 6-digit code to your phone',
            style: TextStyle(
                fontSize: layoutSettings.labelFontSize,
                color: Colors.white.withOpacity(0.6))),
        SizedBox(height: 24),
        _buildInputField(
          controller: otpTextController,
          focusNode: otpFieldFocusNode,
          label: 'Verification Code',
          hint: '000000',
          icon: Icons.lock,
          keyboardType: TextInputType.number,
          maxLength: 6,
          autofillHints: const [AutofillHints.oneTimeCode],
          textInputAction: TextInputAction.done,
          onSubmitted: (_) {
            if (otpTextController.text.length == 6 && !loginInProgress) {
              verifyOtpAndFinishLogin(null);
            }
          },
          textStyle: TextStyle(
              color: Colors.white,
              fontSize: layoutSettings.inputFontSize + 4,
              letterSpacing: 8,
              fontWeight: FontWeight.bold),
        ),
        SizedBox(height: 16),
        Center(
            child: TextButton(
          onPressed: otpCountdownSeconds > 0
              ? null
              : () {
                  final phoneToResend =
                      userVerificationPhone ?? phoneTextController.text;
                  if (phoneToResend.isNotEmpty)
                    sendPhoneVerificationCode(phoneToResend);
                },
          child: Text(
              otpCountdownSeconds > 0
                  ? 'Resend code in ${otpCountdownSeconds}s'
                  : 'Resend Code',
              style: TextStyle(
                  color: otpCountdownSeconds > 0
                      ? Colors.white.withOpacity(0.4)
                      : joviCoral,
                  fontSize: layoutSettings.labelFontSize,
                  fontWeight: FontWeight.w600)),
        )),
        SizedBox(height: 24),
        _Pressable(
          enabled: otpTextController.text.length == 6 && !loginInProgress,
          feedbackOnly: true,
          child: Container(
          height: layoutSettings.buttonHeight,
          decoration: BoxDecoration(
            gradient: LinearGradient(
                colors: otpTextController.text.length == 6
                    ? [joviCoral, joviCoralLight]
                    : [
                        Colors.white.withOpacity(0.1),
                        Colors.white.withOpacity(0.1)
                      ]),
            borderRadius: BorderRadius.circular(16),
            boxShadow: otpTextController.text.length == 6
                ? [
                    BoxShadow(
                        color: joviCoral.withOpacity(0.2),
                        blurRadius: 10,
                        offset: Offset(0, 5))
                  ]
                : [],
          ),
          child: Material(
              color: Colors.transparent,
              borderRadius: BorderRadius.circular(16),
              child: InkWell(
                  borderRadius: BorderRadius.circular(16),
                  onTap: otpTextController.text.length == 6 && !loginInProgress
                      ? () => verifyOtpAndFinishLogin(null)
                      : null,
                  child: Center(
                      child: loginInProgress
                          ? const SizedBox(
                              width: 24,
                              height: 24,
                              child: CircularProgressIndicator(
                                  color: Colors.white, strokeWidth: 2.5))
                          : Text('Verify & Sign In',
                              style: TextStyle(
                                  color: Colors.white,
                                  fontSize: layoutSettings.inputFontSize + 1,
                                  fontWeight: FontWeight.bold))))),
        )),
        SizedBox(height: 16),
        TextButton(
            onPressed: () async {
              await authManager.signOut();
              if (!mounted) return;
              setState(() {
                twoFactorRequired = false;
                phoneNumberStep = false;
                otpVerificationStep = false;
                authenticatedFirebaseUser = null;
                otpTextController.clear();
              });
            },
            child: Text('Cancel and Sign Out',
                style: TextStyle(
                    color: statusError,
                    fontSize: layoutSettings.labelFontSize,
                    fontWeight: FontWeight.w600))),
      ],
    );
  }
}
