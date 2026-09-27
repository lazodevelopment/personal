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
// JOVI HEALTH — TWO-FACTOR AUTHENTICATION SETTINGS
// Version: 2026.09.22-r2 (Apple HIG pass: no pulsing shield, adaptive
//          switch, one-time-code autofill, Verify button now enables as you
//          type, navy toasts, mounted guards, painted glass)
// r1:      2026.04.19
// Build: JC-2FA-0922-002
//
// Rebranded from the Kurv-era blue/white design to Jovi's navy + glassmorphism
// design system (coral primary, navy surface, mint/gold for success/warning
// states). Functionality is unchanged:
//
//   - Enable 2FA: verify phone via Firebase SMS → store phone + flags on user doc
//   - Disable 2FA: require password reauthentication → clear flags
//   - Change phone: verify new number → swap phone on user doc
//   - Audit log: every transition writes to security_logs collection
// ═══════════════════════════════════════════════════════════════════════════

import '/auth/firebase_auth/auth_util.dart';
import '/flutter_flow/flutter_flow_widgets.dart';
import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'dart:async';
import 'dart:math' as math;
import 'dart:ui' as ui_dart;

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

/// Enumerations for device categorization
enum ScreenType { compact, medium, expanded, large }

/// Configuration object for responsive layouts
class ResponsiveConfig {
  final double paddingH;
  final double paddingV;
  final double contentMax;
  final double cardRadius;
  final double iconSize;
  final double titleSize;
  final double bodySize;
  final bool wideMode;
  final bool hasHinge;

  ResponsiveConfig({
    required this.paddingH,
    required this.paddingV,
    required this.contentMax,
    required this.cardRadius,
    required this.iconSize,
    required this.titleSize,
    required this.bodySize,
    required this.wideMode,
    required this.hasHinge,
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

class TwoFactorSettingsWidget extends StatefulWidget {
  const TwoFactorSettingsWidget({
    Key? key,
    this.width,
    this.height,
  }) : super(key: key);

  final double? width;
  final double? height;

  @override
  _TwoFactorSettingsWidgetState createState() =>
      _TwoFactorSettingsWidgetState();
}

class _TwoFactorSettingsWidgetState extends State<TwoFactorSettingsWidget>
    with TickerProviderStateMixin {
  // Controllers
  late TextEditingController phoneController;
  late TextEditingController otpController;
  late TextEditingController passwordController;

  // Focus nodes
  late FocusNode phoneFocusNode;
  late FocusNode otpFocusNode;
  late FocusNode passwordFocusNode;

  // Animation controllers
  late AnimationController _fadeController;
  late AnimationController _expandController;
  late AnimationController _pulseController;
  late Animation<double> _fadeAnimation;
  late Animation<double> _expandAnimation;
  late Animation<double> _pulseAnimation;

  // Responsive Layout Variables
  ScreenType currentScreenType = ScreenType.compact;
  ResponsiveConfig layoutSettings = ResponsiveConfig(
    paddingH: 20,
    paddingV: 20,
    contentMax: double.infinity,
    cardRadius: 16,
    iconSize: 24,
    titleSize: 20,
    bodySize: 14,
    wideMode: false,
    hasHinge: false,
  );

  // Track previous screen configuration
  double? _lastScreenWidth;
  bool? _lastHasHinge;

  // State variables
  bool isLoading = false;
  bool isVerifying = false;
  bool passwordVisible = false;

  // 2FA State
  bool twoFAEnabled = false;
  bool requiresTwoFA = false;
  String? currentPhoneNumber;
  bool showPhoneInput = false;
  bool showOTPInput = false;
  bool showPasswordConfirm = false;
  String? verificationId;
  int? resendToken;

  // Timer for OTP resend
  Timer? _resendTimer;
  int _resendCountdown = 0;

  // Action being performed
  String currentAction = ''; // 'enable', 'disable', 'change'

  @override
  void initState() {
    super.initState();
    _initializeAnimations();
    _initializeControllers();
    _loadTwoFAStatus();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _analyzeScreenConfiguration();
  }

  void _initializeAnimations() {
    _fadeController = AnimationController(
      duration: _Motion.enter,
      vsync: this,
    );
    _expandController = AnimationController(
      duration: _Motion.enter,
      vsync: this,
    );
    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 2000),
      vsync: this,
    );

    _fadeAnimation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _fadeController,
      curve: Curves.easeOut,
    ));

    _expandAnimation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _expandController,
      curve: _Motion.settle,
    ));

    // The shield used to breathe forever. Parked at rest (scale 1.0).
    _pulseAnimation = Tween<double>(
      begin: 1.0,
      end: 1.0,
    ).animate(_pulseController);

    if (_platformReduceMotion()) {
      _fadeController.value = 1.0;
      _expandController.value = 1.0;
    } else {
      _fadeController.forward();
      _expandController.forward();
    }
  }

  void _initializeControllers() {
    phoneController = TextEditingController();
    otpController = TextEditingController();
    passwordController = TextEditingController();
    phoneFocusNode = FocusNode();
    otpFocusNode = FocusNode();
    passwordFocusNode = FocusNode();

    phoneFocusNode.addListener(() => setState(() {}));
    otpFocusNode.addListener(() => setState(() {}));
    passwordFocusNode.addListener(() => setState(() {}));
    // The Verify button is enabled by otpController.text.length, but
    // nothing rebuilt while the member typed, so it stayed greyed out.
    otpController.addListener(() {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    phoneController.dispose();
    otpController.dispose();
    passwordController.dispose();
    phoneFocusNode.dispose();
    otpFocusNode.dispose();
    passwordFocusNode.dispose();
    _fadeController.dispose();
    _expandController.dispose();
    _pulseController.dispose();
    _resendTimer?.cancel();
    super.dispose();
  }

  // ═══════════════════════════════════════════════════════════════════════
  // RESPONSIVE LAYOUT
  // ═══════════════════════════════════════════════════════════════════════

  void _analyzeScreenConfiguration() {
    final mediaQuery = MediaQuery.of(context);
    final screenWidth = mediaQuery.size.width;
    final displayFeatures = mediaQuery.displayFeatures;

    bool hasHinge = false;
    for (final feature in displayFeatures) {
      if (feature.type == ui_dart.DisplayFeatureType.fold ||
          feature.type == ui_dart.DisplayFeatureType.hinge) {
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
    layoutSettings = _generateLayoutConfig(screenType, screenWidth, hasHinge);
  }

  ResponsiveConfig _generateLayoutConfig(
    ScreenType type,
    double width,
    bool hasHinge,
  ) {
    switch (type) {
      case ScreenType.expanded:
        return ResponsiveConfig(
          paddingH: 32,
          paddingV: 24,
          contentMax: double.infinity,
          cardRadius: 20,
          iconSize: 32,
          titleSize: 32,
          bodySize: 16,
          wideMode: true,
          hasHinge: true,
        );
      case ScreenType.large:
        return ResponsiveConfig(
          paddingH: 40,
          paddingV: 32,
          contentMax: 800,
          cardRadius: 24,
          iconSize: 36,
          titleSize: 36,
          bodySize: 18,
          wideMode: true,
          hasHinge: false,
        );
      case ScreenType.medium:
        return ResponsiveConfig(
          paddingH: 24,
          paddingV: 24,
          contentMax: 600,
          cardRadius: 20,
          iconSize: 28,
          titleSize: 28,
          bodySize: 16,
          wideMode: true,
          hasHinge: false,
        );
      case ScreenType.compact:
      default:
        return ResponsiveConfig(
          paddingH: 20,
          paddingV: 20,
          contentMax: double.infinity,
          cardRadius: 16,
          iconSize: 24,
          titleSize: 24,
          bodySize: 14,
          wideMode: false,
          hasHinge: false,
        );
    }
  }

  Widget _wrapWithConstraints({required Widget child}) {
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

  EdgeInsets _getAdaptivePadding() {
    return EdgeInsets.symmetric(
      horizontal: layoutSettings.paddingH,
      vertical: layoutSettings.paddingV,
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // DATA LOADING
  // ═══════════════════════════════════════════════════════════════════════

  Future<void> _loadTwoFAStatus() async {
    setState(() => isLoading = true);

    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user == null) {
        throw Exception('No authenticated user');
      }

      final userDoc = await FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .get();

      if (!mounted) return;
      if (userDoc.exists) {
        final data = userDoc.data()!;
        setState(() {
          twoFAEnabled = data['two_fa_enabled'] ?? false;
          requiresTwoFA = data['requires_2fa'] ?? false;
          currentPhoneNumber = data['phone_number'];
          isLoading = false;
        });
      } else {
        await FirebaseFirestore.instance.collection('users').doc(user.uid).set({
          'email': user.email,
          'uid': user.uid,
          'two_fa_enabled': false,
          'requires_2fa': false,
          'phone_verified': false,
          'created_time': FieldValue.serverTimestamp(),
        });
        if (mounted) setState(() => isLoading = false);
      }
    } catch (e) {
      if (!mounted) return;
      setState(() => isLoading = false);
      _showError('Failed to load 2FA status');
      debugPrint('Error loading 2FA status: $e');
    }
  }

  void _showError(String message) {
    if (!mounted) return;
    HapticFeedback.mediumImpact();
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(message,
        accent: _joviErrorRed,
        icon: CupertinoIcons.exclamationmark_circle,
        duration: const Duration(seconds: 4)));
  }

  void _showSuccess(String message) {
    if (!mounted) return;
    HapticFeedback.lightImpact();
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(message,
        accent: _joviMint, icon: CupertinoIcons.checkmark_circle));
  }

  // ignore: unused_element
  void _showWarning(String message) {
    if (!mounted) return;
    HapticFeedback.lightImpact();
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(message,
        accent: _joviGold, icon: CupertinoIcons.exclamationmark_triangle));
  }

  // ═══════════════════════════════════════════════════════════════════════
  // ACTION HANDLERS
  // ═══════════════════════════════════════════════════════════════════════

  Future<void> _handleEnable2FA() async {
    setState(() {
      currentAction = 'enable';
      showPhoneInput = true;
      showPasswordConfirm = false;
      showOTPInput = false;
    });
  }

  Future<void> _handleDisable2FA() async {
    setState(() {
      currentAction = 'disable';
      showPasswordConfirm = true;
      showPhoneInput = false;
      showOTPInput = false;
    });
  }

  Future<void> _handleChangePhone() async {
    setState(() {
      currentAction = 'change';
      showPhoneInput = true;
      showPasswordConfirm = false;
      showOTPInput = false;
    });
  }

  Future<void> _verifyPasswordAndDisable() async {
    if (passwordController.text.isEmpty) {
      _showError('Please enter your password');
      return;
    }

    setState(() => isVerifying = true);

    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user == null || user.email == null) {
        throw Exception('No authenticated user');
      }

      final credential = EmailAuthProvider.credential(
        email: user.email!,
        password: passwordController.text,
      );

      await user.reauthenticateWithCredential(credential);

      await FirebaseFirestore.instance.collection('users').doc(user.uid).set({
        'two_fa_enabled': false,
        'requires_2fa': false,
        'two_fa_disabled_at': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));

      await FirebaseFirestore.instance.collection('security_logs').add({
        'event': '2fa_disabled',
        'user_id': user.uid,
        'timestamp': FieldValue.serverTimestamp(),
      });

      if (!mounted) return;
      setState(() {
        twoFAEnabled = false;
        requiresTwoFA = false;
        showPasswordConfirm = false;
        isVerifying = false;
        passwordController.clear();
      });

      _showSuccess('Two-factor authentication has been disabled');
    } on FirebaseAuthException catch (e) {
      if (!mounted) return;
      setState(() => isVerifying = false);
      // Newer Firebase Auth reports a bad password as 'invalid-credential'.
      if (e.code == 'wrong-password' || e.code == 'invalid-credential') {
        _showError('Incorrect password');
      } else if (e.code == 'too-many-requests') {
        _showError('Too many attempts. Please try again later.');
      } else {
        _showError('Authentication failed');
      }
    } catch (e) {
      if (!mounted) return;
      setState(() => isVerifying = false);
      _showError('Failed to disable 2FA');
      debugPrint('Error disabling 2FA: $e');
    }
  }

  Future<void> _sendOTP() async {
    final phone = phoneController.text.trim();

    if (phone.isEmpty || phone.length < 10) {
      _showError('Please enter a valid phone number');
      return;
    }

    setState(() => isVerifying = true);

    try {
      String formattedPhone = phone;
      if (!phone.startsWith('+')) {
        formattedPhone = '+1$phone';
      }

      await FirebaseAuth.instance.verifyPhoneNumber(
        phoneNumber: formattedPhone,
        verificationCompleted: (PhoneAuthCredential credential) async {
          try {
            await _verifyOTPAndUpdate(credential);
          } catch (e) {
            if (!mounted) return;
            setState(() => isVerifying = false);
            _showError('Auto-verification failed. Please try manual entry.');
            debugPrint('Auto-verification error: $e');
          }
        },
        verificationFailed: (FirebaseAuthException e) {
          if (!mounted) return;
          setState(() => isVerifying = false);
          String errorMessage = 'Verification failed';

          debugPrint('FirebaseAuthException: ${e.code} - ${e.message}');

          switch (e.code) {
            case 'invalid-phone-number':
              errorMessage = 'Invalid phone number format';
              break;
            case 'too-many-requests':
              errorMessage = 'Too many requests. Please try again later';
              break;
            case 'captcha-check-failed':
              errorMessage =
                  'Security verification failed. Please refresh and try again';
              break;
            case 'missing-phone-number':
              errorMessage = 'Phone number is required';
              break;
            case 'quota-exceeded':
              errorMessage = 'SMS quota exceeded. Please try again later';
              break;
            default:
              errorMessage =
                  'Verification failed: ${e.message ?? 'Unknown error'}';
              break;
          }

          _showError(errorMessage);
        },
        codeSent: (String verId, int? token) {
          if (mounted) {
            setState(() {
              verificationId = verId;
              resendToken = token;
              showOTPInput = true;
              showPhoneInput = false;
              isVerifying = false;
              _startResendTimer();
            });
            _showSuccess('Verification code sent to $formattedPhone');
          }
        },
        codeAutoRetrievalTimeout: (String verId) {
          if (mounted) {
            verificationId = verId;
          }
        },
        forceResendingToken: resendToken,
        timeout: const Duration(seconds: 60),
      );
    } catch (e) {
      if (mounted) {
        setState(() => isVerifying = false);

        String errorMessage = 'Error sending verification code';

        if (e.toString().contains('reCAPTCHA')) {
          errorMessage =
              'Security verification not configured. Please contact support.';
        } else if (e.toString().contains('network')) {
          errorMessage =
              'Network error. Please check your connection and try again.';
        } else if (e.toString().contains('auth/')) {
          errorMessage =
              'Authentication service error. Please try again later.';
        }

        _showError(errorMessage);
        debugPrint('Error sending OTP: $e');
      }
    }
  }

  Future<void> _verifyOTPAndUpdate([PhoneAuthCredential? credential]) async {
    if (!mounted) return;
    setState(() => isVerifying = true);

    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user == null) {
        throw Exception('No authenticated user');
      }

      PhoneAuthCredential authCredential;
      if (credential != null) {
        authCredential = credential;
      } else {
        if (verificationId == null || otpController.text.isEmpty) {
          throw Exception('Invalid verification state');
        }
        authCredential = PhoneAuthProvider.credential(
          verificationId: verificationId!,
          smsCode: otpController.text,
        );
      }

      try {
        if (user.phoneNumber == null || user.phoneNumber!.isEmpty) {
          await user.linkWithCredential(authCredential);
          await user.reload();
        } else {
          await FirebaseAuth.instance.signInWithCredential(authCredential);
        }
      } catch (e) {
        if (!e.toString().contains('already been linked')) {
          throw e;
        }
      }

      final phoneNumber = phoneController.text.trim();
      final formattedPhone =
          phoneNumber.startsWith('+') ? phoneNumber : '+1$phoneNumber';

      await FirebaseFirestore.instance.collection('users').doc(user.uid).set({
        'phone_number': formattedPhone,
        'two_fa_enabled': true,
        'requires_2fa': true,
        'phone_verified': true,
        'phone_verified_at': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));

      final eventType =
          currentAction == 'enable' ? '2fa_enabled' : '2fa_phone_changed';

      await FirebaseFirestore.instance.collection('security_logs').add({
        'event': eventType,
        'user_id': user.uid,
        'timestamp': FieldValue.serverTimestamp(),
      });

      if (!mounted) return;
      _resendTimer?.cancel();
      _resendCountdown = 0;
      setState(() {
        twoFAEnabled = true;
        requiresTwoFA = true;
        currentPhoneNumber = formattedPhone;
        showOTPInput = false;
        showPhoneInput = false;
        isVerifying = false;
        phoneController.clear();
        otpController.clear();
      });

      final message = currentAction == 'enable'
          ? 'Two-factor authentication has been enabled'
          : 'Phone number has been updated';

      _showSuccess(message);
    } catch (e) {
      if (!mounted) return;
      setState(() => isVerifying = false);
      String errorMessage = 'Verification failed';
      if (e.toString().contains('invalid-verification-code')) {
        errorMessage = 'Invalid verification code';
      } else if (e.toString().contains('session-expired')) {
        errorMessage = 'Verification code expired. Please request a new one';
      }
      _showError(errorMessage);
      debugPrint('Error verifying OTP: $e');
    }
  }

  void _startResendTimer() {
    _resendCountdown = 30;
    _resendTimer?.cancel();
    _resendTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      setState(() {
        if (_resendCountdown > 0) {
          _resendCountdown--;
        } else {
          timer.cancel();
        }
      });
    });
  }

  String _formatPhoneNumber(String? phone) {
    if (phone == null || phone.isEmpty) return '';

    String displayPhone = phone;
    if (phone.startsWith('+1')) {
      displayPhone = phone.substring(2);
    } else if (phone.startsWith('+')) {
      return phone;
    }

    if (displayPhone.length == 10) {
      return '(${displayPhone.substring(0, 3)}) ${displayPhone.substring(3, 6)}-${displayPhone.substring(6)}';
    }

    return phone;
  }

  // ═══════════════════════════════════════════════════════════════════════
  // ROOT BUILD — navy gradient background with glass content
  // ═══════════════════════════════════════════════════════════════════════

  @override
  Widget build(BuildContext context) {
    return Container(
      width: widget.width ?? MediaQuery.of(context).size.width,
      height: widget.height ?? MediaQuery.of(context).size.height,
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [_joviNavy, _joviNavyDark],
        ),
      ),
      child: Stack(
        children: [
          // Ambient coral haze top-right
          Positioned(
            top: -60,
            right: -60,
            child: Container(
              width: 220,
              height: 220,
              decoration: BoxDecoration(
                gradient: RadialGradient(
                  colors: [
                    _joviCoral.withOpacity(0.18),
                    _joviCoral.withOpacity(0.0),
                  ],
                ),
              ),
            ),
          ),
          // Ambient mint haze bottom-left
          Positioned(
            bottom: -80,
            left: -80,
            child: Container(
              width: 260,
              height: 260,
              decoration: BoxDecoration(
                gradient: RadialGradient(
                  colors: [
                    _joviMint.withOpacity(0.14),
                    _joviMint.withOpacity(0.0),
                  ],
                ),
              ),
            ),
          ),
          _wrapWithConstraints(
            child: FadeTransition(
              opacity: _fadeAnimation,
              child: SingleChildScrollView(
                padding: EdgeInsets.fromLTRB(
                  layoutSettings.paddingH,
                  // Extra top padding to clear the anchored back button
                  layoutSettings.paddingV +
                      56 +
                      MediaQuery.of(context).padding.top,
                  layoutSettings.paddingH,
                  layoutSettings.paddingV,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _buildHeader(),
                    SizedBox(height: layoutSettings.paddingV * 1.5),
                    if (isLoading)
                      _buildLoadingState()
                    else
                      _buildMainContent(),
                    SizedBox(height: layoutSettings.paddingV),
                    _buildInfoSection(),
                  ],
                ),
              ),
            ),
          ),
          // Anchored back button — stays visible as user scrolls
          Positioned(
            top: MediaQuery.of(context).padding.top + 12,
            left: 16,
            child: _Pressable(
                feedbackOnly: true,
                pressedScale: 0.92,
                child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: () {
                  HapticFeedback.lightImpact();
                  // If any sub-flow is open, cancel it first instead of leaving the page
                  if (showPhoneInput || showOTPInput || showPasswordConfirm) {
                    setState(() {
                      showPhoneInput = false;
                      showOTPInput = false;
                      showPasswordConfirm = false;
                      phoneController.clear();
                      otpController.clear();
                      passwordController.clear();
                      _resendTimer?.cancel();
                      _resendCountdown = 0;
                    });
                    return;
                  }
                  // Otherwise leave the 2FA settings page
                  if (Navigator.of(context).canPop()) {
                    Navigator.of(context).pop();
                  } else {
                    // Fallback: go home if this was opened as a root page
                    try {
                      context.pushReplacementNamed('home');
                    } catch (_) {
                      // Silently no-op if 'home' route doesn't resolve
                    }
                  }
                },
                borderRadius: BorderRadius.circular(12),
                child: Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.08),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: Colors.white.withOpacity(0.12),
                      width: 1,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.2),
                        blurRadius: 12,
                        offset: const Offset(0, 4),
                      ),
                    ],
                  ),
                  child: Icon(
                    Icons.arrow_back_ios_new_rounded,
                    color: Colors.white.withOpacity(0.85),
                    size: 18,
                  ),
                ),
              ),
            )),
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // COMMON GLASS HELPERS
  // ═══════════════════════════════════════════════════════════════════════

  Widget _glassCard({
    required Widget child,
    double bgOpacity = 0.07,
    double borderOpacity = 0.12,
    double borderWidth = 1.2,
    EdgeInsetsGeometry? padding,
    double? radius,
    double blur = 18,
    Color? borderTint,
    List<BoxShadow>? shadow,
  }) {
    final r = radius ?? layoutSettings.cardRadius;
    // Painted glass: three live blurs in one scroll view over an opaque
    // navy gradient cost GPU for no visible gain.
    return ClipRRect(
      borderRadius: BorderRadius.circular(r),
      child: RepaintBoundary(
        child: Container(
          padding: padding ?? EdgeInsets.all(layoutSettings.paddingH),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(bgOpacity + 0.02),
            borderRadius: BorderRadius.circular(r),
            border: Border.all(
              color: (borderTint ?? Colors.white).withOpacity(borderOpacity),
              width: borderWidth,
            ),
            boxShadow: shadow ??
                [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.22),
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

  // ═══════════════════════════════════════════════════════════════════════
  // HEADER
  // ═══════════════════════════════════════════════════════════════════════

  Widget _buildHeader() {
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: _platformReduceMotion() ? 1.0 : 0.96, end: 1.0),
      duration: _Motion.enter,
      curve: _Motion.settle,
      builder: (context, value, child) {
        return Transform.scale(
          scale: value,
          child: _glassCard(
            bgOpacity: 0.08,
            borderOpacity: 0.15,
            padding: EdgeInsets.all(layoutSettings.paddingH),
            child: Column(
              children: [
                AnimatedBuilder(
                  animation: _pulseAnimation,
                  builder: (context, child) {
                    return Transform.scale(
                      scale: _pulseAnimation.value,
                      child: Container(
                        width: 80,
                        height: 80,
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [_joviCoral, _joviCoralDark],
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                          ),
                          shape: BoxShape.circle,
                          boxShadow: [
                            BoxShadow(
                              color: _joviCoral.withOpacity(0.45),
                              blurRadius: 24,
                              offset: const Offset(0, 8),
                            ),
                          ],
                        ),
                        child: Icon(
                          Icons.security_rounded,
                          color: Colors.white,
                          size: layoutSettings.iconSize + 16,
                        ),
                      ),
                    );
                  },
                ),
                SizedBox(height: layoutSettings.paddingV),
                Text(
                  'Two-Factor Authentication',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: layoutSettings.titleSize,
                    fontWeight: FontWeight.w700,
                    color: Colors.white,
                    letterSpacing: -0.6,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  'Add an extra layer of security to your account',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: layoutSettings.bodySize + 2,
                    color: Colors.white.withOpacity(0.65),
                    fontWeight: FontWeight.w500,
                    height: 1.45,
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // LOADING STATE
  // ═══════════════════════════════════════════════════════════════════════

  Widget _buildLoadingState() {
    return _glassCard(
      padding: EdgeInsets.all(layoutSettings.paddingH * 2),
      child: Column(
        children: [
          const CircularProgressIndicator(
            color: _joviCoral,
            strokeWidth: 2.5,
          ),
          SizedBox(height: layoutSettings.paddingV),
          Text(
            'Loading settings…',
            style: TextStyle(
              color: Colors.white.withOpacity(0.65),
              fontSize: layoutSettings.bodySize + 2,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // MAIN CONTENT
  // ═══════════════════════════════════════════════════════════════════════

  Widget _buildMainContent() {
    return AnimatedSwitcher(
      duration: _Motion.select,
      switchInCurve: Curves.easeOut,
      switchOutCurve: Curves.easeIn,
      child: Container(
        key: const ValueKey('main-content'),
        child: _glassCard(
          padding: EdgeInsets.zero,
          child: Column(
            children: [
              _buildStatusSection(),
              if (!showPhoneInput && !showOTPInput && !showPasswordConfirm)
                Container(
                  height: 1,
                  margin:
                      EdgeInsets.symmetric(horizontal: layoutSettings.paddingH),
                  color: Colors.white.withOpacity(0.08),
                ),
              if (!showPhoneInput && !showOTPInput && !showPasswordConfirm)
                _buildActionSection(),
              if (showPhoneInput) _buildPhoneInputSection(),
              if (showOTPInput) _buildOTPInputSection(),
              if (showPasswordConfirm) _buildPasswordConfirmSection(),
            ],
          ),
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // STATUS SECTION
  // ═══════════════════════════════════════════════════════════════════════

  Widget _buildStatusSection() {
    final statusAccent = twoFAEnabled ? _joviMint : _joviGold;
    return Padding(
      padding: EdgeInsets.all(layoutSettings.paddingH),
      child: Row(
        children: [
          Container(
            width: layoutSettings.iconSize + 32,
            height: layoutSettings.iconSize + 32,
            decoration: BoxDecoration(
              color: statusAccent.withOpacity(0.18),
              borderRadius: BorderRadius.circular(layoutSettings.cardRadius),
              border: Border.all(
                color: statusAccent.withOpacity(0.45),
                width: 1.4,
              ),
            ),
            child: Icon(
              twoFAEnabled ? Icons.check_circle_rounded : Icons.shield_outlined,
              color: statusAccent,
              size: layoutSettings.iconSize + 4,
            ),
          ),
          SizedBox(width: layoutSettings.paddingH),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  twoFAEnabled ? 'Enabled' : 'Disabled',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: layoutSettings.titleSize - 4,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -0.3,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  twoFAEnabled
                      ? 'Your account is protected with 2FA'
                      : 'Enable 2FA for enhanced security',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.6),
                    fontSize: layoutSettings.bodySize + 2,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                if (twoFAEnabled && currentPhoneNumber != null) ...[
                  const SizedBox(height: 10),
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: _joviCoral.withOpacity(0.16),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                        color: _joviCoral.withOpacity(0.35),
                        width: 0.8,
                      ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(
                          Icons.phone_rounded,
                          size: 14,
                          color: _joviCoralLight,
                        ),
                        const SizedBox(width: 6),
                        Text(
                          _formatPhoneNumber(currentPhoneNumber),
                          style: TextStyle(
                            color: _joviCoralLight,
                            fontSize: layoutSettings.bodySize + 1,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),
          Transform.scale(
            scale: layoutSettings.wideMode ? 1.15 : 1.0,
            child: Switch.adaptive(
              value: twoFAEnabled,
              onChanged: (value) {
                HapticFeedback.selectionClick();
                if (value) {
                  _handleEnable2FA();
                } else {
                  _handleDisable2FA();
                }
              },
              activeColor: Colors.white,
              activeTrackColor: _joviCoral,
              inactiveThumbColor: Colors.white.withOpacity(0.6),
              inactiveTrackColor: Colors.white.withOpacity(0.15),
              materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
            ),
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // ACTION SECTION
  // ═══════════════════════════════════════════════════════════════════════

  Widget _buildActionSection() {
    if (!twoFAEnabled) {
      return Padding(
        padding: EdgeInsets.all(layoutSettings.paddingH),
        child: Column(
          children: [
            Container(
              padding: EdgeInsets.all(layoutSettings.paddingH),
              decoration: BoxDecoration(
                color: _joviCoral.withOpacity(0.09),
                borderRadius: BorderRadius.circular(layoutSettings.cardRadius),
                border: Border.all(
                  color: _joviCoral.withOpacity(0.25),
                  width: 1,
                ),
              ),
              child: Column(
                children: [
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      color: _joviCoral.withOpacity(0.18),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: _joviCoral.withOpacity(0.4),
                        width: 1,
                      ),
                    ),
                    child: Icon(
                      Icons.security_rounded,
                      color: _joviCoral,
                      size: layoutSettings.iconSize + 2,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'Secure your account',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: layoutSettings.bodySize + 6,
                      fontWeight: FontWeight.w800,
                      letterSpacing: -0.3,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Enable two-factor authentication to add an extra layer of security',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.65),
                      fontSize: layoutSettings.bodySize + 2,
                      fontWeight: FontWeight.w500,
                      height: 1.45,
                    ),
                  ),
                ],
              ),
            ),
            SizedBox(height: layoutSettings.paddingV),
            _buildPremiumButton(
              onPressed: _handleEnable2FA,
              text: 'Turn On Two-Factor Authentication',
              icon: Icons.security_rounded,
              isPrimary: true,
            ),
          ],
        ),
      );
    }

    return Padding(
      padding: EdgeInsets.all(layoutSettings.paddingH),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Manage Settings',
            style: TextStyle(
              color: Colors.white.withOpacity(0.6),
              fontSize: 13,
              fontWeight: FontWeight.w600,
              letterSpacing: -0.1,
            ),
          ),
          SizedBox(height: layoutSettings.paddingV * 0.7),
          _buildActionCard(
            icon: Icons.phone_android_rounded,
            title: 'Change phone number',
            subtitle: 'Update your 2FA phone number',
            onTap: _handleChangePhone,
            accent: _joviCoral,
          ),
          const SizedBox(height: 10),
          _buildActionCard(
            icon: Icons.remove_circle_outline_rounded,
            title: 'Disable two-factor authentication',
            subtitle: 'Remove 2FA protection from your account',
            onTap: _handleDisable2FA,
            accent: _joviErrorRed,
            isDestructive: true,
          ),
        ],
      ),
    );
  }

  Widget _buildActionCard({
    required IconData icon,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
    required Color accent,
    bool isDestructive = false,
  }) {
    return _Pressable(
        feedbackOnly: true,
        pressedScale: 0.985,
        child: Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () {
          HapticFeedback.selectionClick();
          onTap();
        },
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: EdgeInsets.all(layoutSettings.paddingH * 0.8),
          decoration: BoxDecoration(
            color: accent.withOpacity(0.08),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: accent.withOpacity(0.28),
              width: 1,
            ),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: accent.withOpacity(0.16),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: accent.withOpacity(0.35),
                    width: 0.8,
                  ),
                ),
                child: Icon(
                  icon,
                  color: accent,
                  size: layoutSettings.iconSize - 2,
                ),
              ),
              SizedBox(width: layoutSettings.paddingH * 0.7),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: layoutSettings.bodySize + 2,
                        fontWeight: FontWeight.w700,
                        letterSpacing: -0.2,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      subtitle,
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.55),
                        fontSize: layoutSettings.bodySize,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
              Icon(
                Icons.chevron_right_rounded,
                color: accent,
                size: layoutSettings.iconSize,
              ),
            ],
          ),
        ),
      ),
    ));
  }

  // ═══════════════════════════════════════════════════════════════════════
  // PHONE INPUT SECTION
  // ═══════════════════════════════════════════════════════════════════════

  Widget _buildPhoneInputSection() {
    return Padding(
      padding: EdgeInsets.all(layoutSettings.paddingH),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildSectionHeader(
            icon: Icons.phone_android_rounded,
            title: currentAction == 'change'
                ? 'Enter new phone number'
                : 'Add your phone number',
            subtitle: "We'll send a verification code to this number",
          ),
          SizedBox(height: layoutSettings.paddingV),
          _buildPremiumTextField(
            controller: phoneController,
            focusNode: phoneFocusNode,
            label: 'Phone Number',
            hint: '(555) 123-4567',
            icon: Icons.phone_rounded,
            keyboardType: TextInputType.phone,
            autofillHints: const [AutofillHints.telephoneNumber],
            textInputAction: TextInputAction.done,
            onSubmitted: (_) {
              if (!isVerifying) _sendOTP();
            },
          ),
          SizedBox(height: layoutSettings.paddingV),
          Row(
            children: [
              Expanded(
                child: _buildPremiumButton(
                  onPressed: () {
                    setState(() {
                      showPhoneInput = false;
                      phoneController.clear();
                    });
                  },
                  text: 'Cancel',
                  icon: Icons.close_rounded,
                  isPrimary: false,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _buildPremiumButton(
                  onPressed: isVerifying ? null : _sendOTP,
                  text: 'Send Code',
                  icon: Icons.send_rounded,
                  isPrimary: true,
                  isLoading: isVerifying,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // OTP INPUT SECTION
  // ═══════════════════════════════════════════════════════════════════════

  Widget _buildOTPInputSection() {
    return Padding(
      padding: EdgeInsets.all(layoutSettings.paddingH),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildSectionHeader(
            icon: Icons.lock_outline_rounded,
            title: 'Enter verification code',
            subtitle: 'We sent a 6-digit code to your phone',
          ),
          SizedBox(height: layoutSettings.paddingV),
          _buildPremiumTextField(
            controller: otpController,
            focusNode: otpFocusNode,
            label: 'Verification Code',
            hint: '000000',
            icon: Icons.lock_rounded,
            keyboardType: TextInputType.number,
            maxLength: 6,
            autofillHints: const [AutofillHints.oneTimeCode],
            textInputAction: TextInputAction.done,
            onSubmitted: (_) {
              if (otpController.text.length == 6 && !isVerifying) {
                _verifyOTPAndUpdate();
              }
            },
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white,
              fontSize: layoutSettings.bodySize + 10,
              letterSpacing: 8,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 12),
          Center(
            child: TextButton(
              onPressed: _resendCountdown > 0 ? null : _sendOTP,
              style: TextButton.styleFrom(
                padding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              ),
              child: Text(
                _resendCountdown > 0
                    ? 'Resend code in $_resendCountdown seconds'
                    : 'Resend Code',
                style: TextStyle(
                  color: _resendCountdown > 0
                      ? Colors.white.withOpacity(0.45)
                      : _joviCoralLight,
                  fontSize: layoutSettings.bodySize + 2,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
          SizedBox(height: layoutSettings.paddingV),
          Row(
            children: [
              Expanded(
                child: _buildPremiumButton(
                  onPressed: () {
                    setState(() {
                      showOTPInput = false;
                      showPhoneInput = true;
                      otpController.clear();
                    });
                  },
                  text: 'Back',
                  icon: Icons.arrow_back_rounded,
                  isPrimary: false,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _buildPremiumButton(
                  onPressed: otpController.text.length == 6 && !isVerifying
                      ? () => _verifyOTPAndUpdate()
                      : null,
                  text: 'Verify',
                  icon: Icons.check_circle_rounded,
                  isPrimary: true,
                  isLoading: isVerifying,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // PASSWORD CONFIRM SECTION (disable)
  // ═══════════════════════════════════════════════════════════════════════

  Widget _buildPasswordConfirmSection() {
    return Padding(
      padding: EdgeInsets.all(layoutSettings.paddingH),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: EdgeInsets.all(layoutSettings.paddingH * 0.8),
            decoration: BoxDecoration(
              color: _joviGold.withOpacity(0.1),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: _joviGold.withOpacity(0.3),
                width: 1,
              ),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  Icons.warning_amber_rounded,
                  color: _joviGoldDark,
                  size: layoutSettings.iconSize,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Security Notice',
                        style: TextStyle(
                          color: _joviGold,
                          fontSize: layoutSettings.bodySize + 2,
                          fontWeight: FontWeight.w800,
                          letterSpacing: -0.2,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        'Disabling 2FA will make your account less secure',
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.8),
                          fontSize: layoutSettings.bodySize,
                          fontWeight: FontWeight.w500,
                          height: 1.4,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          SizedBox(height: layoutSettings.paddingV),
          _buildSectionHeader(
            icon: Icons.lock_outline_rounded,
            title: 'Confirm your password to disable',
            subtitle: 'Enter your account password to confirm this action',
          ),
          SizedBox(height: layoutSettings.paddingV),
          _buildPremiumTextField(
            controller: passwordController,
            focusNode: passwordFocusNode,
            label: 'Password',
            hint: '••••••••',
            icon: Icons.lock_outline_rounded,
            obscureText: !passwordVisible,
            autofillHints: const [AutofillHints.password],
            textInputAction: TextInputAction.done,
            onSubmitted: (_) {
              if (!isVerifying) _verifyPasswordAndDisable();
            },
            suffixIcon: IconButton(
              icon: Icon(
                passwordVisible
                    ? Icons.visibility_rounded
                    : Icons.visibility_off_rounded,
                color: Colors.white.withOpacity(0.55),
                size: layoutSettings.iconSize,
              ),
              onPressed: () {
                setState(() {
                  passwordVisible = !passwordVisible;
                });
              },
            ),
          ),
          SizedBox(height: layoutSettings.paddingV),
          Row(
            children: [
              Expanded(
                child: _buildPremiumButton(
                  onPressed: () {
                    setState(() {
                      showPasswordConfirm = false;
                      passwordController.clear();
                    });
                  },
                  text: 'Cancel',
                  icon: Icons.close_rounded,
                  isPrimary: false,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _buildPremiumButton(
                  onPressed: isVerifying ? null : _verifyPasswordAndDisable,
                  text: 'Turn Off 2FA',
                  icon: Icons.remove_circle_rounded,
                  isPrimary: true,
                  isDestructive: true,
                  isLoading: isVerifying,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // SECTION HEADER
  // ═══════════════════════════════════════════════════════════════════════

  Widget _buildSectionHeader({
    required IconData icon,
    required String title,
    required String subtitle,
  }) {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: _joviCoral.withOpacity(0.16),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: _joviCoral.withOpacity(0.35),
              width: 0.8,
            ),
          ),
          child: Icon(
            icon,
            color: _joviCoralLight,
            size: layoutSettings.iconSize,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: TextStyle(
                  color: Colors.white,
                  fontSize: layoutSettings.bodySize + 4,
                  fontWeight: FontWeight.w800,
                  letterSpacing: -0.3,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                subtitle,
                style: TextStyle(
                  color: Colors.white.withOpacity(0.6),
                  fontSize: layoutSettings.bodySize + 1,
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

  // ═══════════════════════════════════════════════════════════════════════
  // PREMIUM TEXT FIELD (navy + coral focus)
  // ═══════════════════════════════════════════════════════════════════════

  Widget _buildPremiumTextField({
    required TextEditingController controller,
    required FocusNode focusNode,
    required String label,
    required String hint,
    required IconData icon,
    TextInputType? keyboardType,
    bool obscureText = false,
    int? maxLength,
    Widget? suffixIcon,
    TextAlign textAlign = TextAlign.start,
    TextStyle? style,
    Iterable<String>? autofillHints,
    TextInputAction? textInputAction,
    ValueChanged<String>? onSubmitted,
  }) {
    final focused = focusNode.hasFocus;
    return AnimatedContainer(
      duration: _Motion.select,
      curve: _Motion.settle,
      decoration: BoxDecoration(
        color: focused
            ? _joviCoral.withOpacity(0.06)
            : Colors.white.withOpacity(0.04),
        borderRadius: BorderRadius.circular(layoutSettings.cardRadius),
        border: Border.all(
          color: focused
              ? _joviCoral.withOpacity(0.55)
              : Colors.white.withOpacity(0.12),
          width: focused ? 1.4 : 1,
        ),
        boxShadow: focused
            ? [
                BoxShadow(
                  color: _joviCoral.withOpacity(0.18),
                  blurRadius: 14,
                  offset: const Offset(0, 4),
                ),
              ]
            : null,
      ),
      child: TextFormField(
        controller: controller,
        focusNode: focusNode,
        keyboardType: keyboardType,
        obscureText: obscureText,
        maxLength: maxLength,
        textAlign: textAlign,
        autofillHints: autofillHints,
        textInputAction: textInputAction,
        onFieldSubmitted: onSubmitted,
        autocorrect: false,
        cursorColor: _joviCoral,
        style: style ??
            TextStyle(
              color: Colors.white,
              fontSize: layoutSettings.bodySize + 4,
              fontWeight: FontWeight.w600,
              letterSpacing: -0.2,
            ),
        decoration: InputDecoration(
          labelText: label,
          labelStyle: TextStyle(
            color: focused ? _joviCoralLight : Colors.white.withOpacity(0.6),
            fontSize: layoutSettings.bodySize + 2,
            fontWeight: FontWeight.w600,
          ),
          floatingLabelBehavior: FloatingLabelBehavior.auto,
          hintText: hint,
          hintStyle: TextStyle(
            color: Colors.white.withOpacity(0.3),
            fontSize: layoutSettings.bodySize + 2,
            fontWeight: FontWeight.w500,
          ),
          prefixIcon: Icon(
            icon,
            color: focused ? _joviCoralLight : Colors.white.withOpacity(0.55),
            size: layoutSettings.iconSize,
          ),
          suffixIcon: suffixIcon,
          counterText: '',
          border: InputBorder.none,
          contentPadding: EdgeInsets.symmetric(
            horizontal: layoutSettings.paddingH,
            vertical: layoutSettings.paddingV * 0.75,
          ),
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // PREMIUM BUTTON
  // ═══════════════════════════════════════════════════════════════════════

  Widget _buildPremiumButton({
    required VoidCallback? onPressed,
    required String text,
    required IconData icon,
    required bool isPrimary,
    bool isDestructive = false,
    bool isLoading = false,
  }) {
    final enabled = onPressed != null && !isLoading;
    final bgGradient = isPrimary
        ? (isDestructive
            ? const LinearGradient(
                colors: [_joviErrorRed, Color(0xFFB71C1C)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              )
            : const LinearGradient(
                colors: [_joviCoral, _joviCoralDark],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ))
        : null;
    final shadowColor = isDestructive ? _joviErrorRed : _joviCoral;

    return _Pressable(
        enabled: enabled,
        feedbackOnly: true,
        child: Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: enabled
            ? () {
                HapticFeedback.lightImpact();
                onPressed();
              }
            : null,
        borderRadius: BorderRadius.circular(12),
        child: AnimatedContainer(
          duration: _Motion.select,
          curve: _Motion.settle,
          constraints: const BoxConstraints(minHeight: 48),
          padding: EdgeInsets.symmetric(
            vertical: layoutSettings.paddingV * 0.75,
            horizontal: layoutSettings.paddingH,
          ),
          decoration: BoxDecoration(
            gradient: enabled ? bgGradient : null,
            color: isPrimary
                ? (enabled ? null : Colors.white.withOpacity(0.05))
                : Colors.white.withOpacity(0.06),
            borderRadius: BorderRadius.circular(12),
            border: isPrimary
                ? null
                : Border.all(
                    color: Colors.white.withOpacity(0.18),
                    width: 1,
                  ),
            boxShadow: isPrimary && enabled
                ? [
                    BoxShadow(
                      color: shadowColor.withOpacity(0.35),
                      blurRadius: 14,
                      offset: const Offset(0, 5),
                    ),
                  ]
                : null,
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              if (isLoading)
                const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(
                    color: Colors.white,
                    strokeWidth: 2,
                  ),
                )
              else
                Icon(
                  icon,
                  color: isPrimary
                      ? Colors.white
                      : (enabled
                          ? Colors.white
                          : Colors.white.withOpacity(0.4)),
                  size: layoutSettings.iconSize * 0.8,
                ),
              const SizedBox(width: 8),
              Text(
                text,
                style: TextStyle(
                  color: isPrimary
                      ? Colors.white
                      : (enabled
                          ? Colors.white
                          : Colors.white.withOpacity(0.4)),
                  fontSize: layoutSettings.bodySize + 2,
                  fontWeight: FontWeight.w600,
                  letterSpacing: -0.2,
                ),
              ),
            ],
          ),
        ),
      ),
    ));
  }

  // ═══════════════════════════════════════════════════════════════════════
  // INFO SECTION
  // ═══════════════════════════════════════════════════════════════════════

  Widget _buildInfoSection() {
    return _glassCard(
      bgOpacity: 0.05,
      borderOpacity: 0.1,
      padding: EdgeInsets.all(layoutSettings.paddingH),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: _joviMint.withOpacity(0.16),
                  borderRadius: BorderRadius.circular(9),
                  border: Border.all(
                    color: _joviMint.withOpacity(0.3),
                    width: 0.8,
                  ),
                ),
                child: Icon(
                  Icons.info_outline_rounded,
                  color: _joviMint,
                  size: layoutSettings.iconSize - 2,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  'About Two-Factor Authentication',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: layoutSettings.bodySize + 4,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -0.3,
                  ),
                ),
              ),
            ],
          ),
          SizedBox(height: layoutSettings.paddingV),
          _buildInfoItem(
            Icons.security_rounded,
            'Enhanced Security',
            'Protects against unauthorized access even if your password is compromised',
            _joviCoral,
          ),
          const SizedBox(height: 12),
          _buildInfoItem(
            Icons.phone_android_rounded,
            'SMS Verification',
            'Receive a unique code via SMS each time you sign in',
            _joviMint,
          ),
          const SizedBox(height: 12),
          _buildInfoItem(
            Icons.medical_services_rounded,
            'HIPAA Compliant',
            'Meets healthcare industry security standards for protected health information',
            _joviGold,
          ),
        ],
      ),
    );
  }

  Widget _buildInfoItem(
    IconData icon,
    String title,
    String description,
    Color accent,
  ) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: accent.withOpacity(0.14),
            borderRadius: BorderRadius.circular(9),
            border: Border.all(
              color: accent.withOpacity(0.3),
              width: 0.8,
            ),
          ),
          child: Icon(
            icon,
            color: accent,
            size: layoutSettings.iconSize * 0.75,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: TextStyle(
                  color: Colors.white,
                  fontSize: layoutSettings.bodySize + 2,
                  fontWeight: FontWeight.w800,
                  letterSpacing: -0.2,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                description,
                style: TextStyle(
                  color: Colors.white.withOpacity(0.6),
                  fontSize: layoutSettings.bodySize + 1,
                  fontWeight: FontWeight.w500,
                  height: 1.45,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
