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
// JOVI HEALTH - USER PROFILE (NAVY + GLASS)
// Version: 2026.09.22-r3 (Apple HIG pass: press feedback, no looping glow,
//          scroll rebuild throttle, safer account deletion, navy toasts)
// r4 (2026.09.22): Cupertino delete-account alert; deletion now wipes every
//          collection tied to the uid (see _userTree/_topLevelByUser) and
//          pairs with functions/deleteUserData.js for the server-side wipe.
// r2:      2026.04.17 (full navy+glass throughout)
// ============================================================

import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';
import 'package:url_launcher/url_launcher.dart';
import '/auth/firebase_auth/auth_util.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:intl/intl.dart';
import 'dart:math' as math;
import 'dart:ui';
import 'dart:ui' as ui_dart;

// Jovi Health Brand Colors
const Color joviCoral = Color(0xFFFF6B4A);
const Color joviCoralLight = Color(0xFFFF8F73);
const Color joviCoralDark = Color(0xFFE5583A);
const Color joviNavy = Color(0xFF1A2744);
const Color joviNavyDark = Color(0xFF0F1A2E);
const Color joviNavyMid = Color(0xFF1F2B47);
const Color joviMint = Color(0xFF00D4AA);
const Color joviMintDark = Color(0xFF00B894);
const Color joviGold = Color(0xFFFFD166);
const Color joviErrorRed = Color(0xFFE53935);

enum ScreenType { compact, medium, expanded, large }

class ResponsiveConfig {
  final double paddingH;
  final double paddingV;
  final double contentMax;
  final double avatarSize;
  final double headerFontSize;
  final double titleFontSize;
  final double bodyFontSize;
  final double iconSize;
  final double buttonHeight;
  final bool wideMode;
  final bool hasHinge;
  final bool useTwoColumnLayout;

  ResponsiveConfig({
    required this.paddingH,
    required this.paddingV,
    required this.contentMax,
    required this.avatarSize,
    required this.headerFontSize,
    required this.titleFontSize,
    required this.bodyFontSize,
    required this.iconSize,
    required this.buttonHeight,
    required this.wideMode,
    required this.hasHinge,
    this.useTwoColumnLayout = false,
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

class UserProfile extends StatefulWidget {
  const UserProfile({
    Key? key,
    this.width,
    this.height,
  }) : super(key: key);

  final double? width;
  final double? height;

  @override
  State<UserProfile> createState() => _UserProfileState();
}

class _UserProfileState extends State<UserProfile>
    with TickerProviderStateMixin {
  ScreenType currentScreenType = ScreenType.compact;
  ResponsiveConfig layoutSettings = ResponsiveConfig(
    paddingH: 16,
    paddingV: 8,
    contentMax: double.infinity,
    avatarSize: 110,
    headerFontSize: 28,
    titleFontSize: 15,
    bodyFontSize: 14,
    iconSize: 24,
    buttonHeight: 56,
    wideMode: false,
    hasHinge: false,
  );

  double? _lastScreenWidth;
  bool? _lastHasHinge;

  bool isLoading = false;
  bool isRefreshing = false;
  ScrollController _scrollController = ScrollController();
  double _scrollOffset = 0;

  late AnimationController _animationController;
  late AnimationController _profileImageController;
  late Animation<double> _fadeAnimation;
  late Animation<double> _scaleAnimation;
  late Animation<Offset> _slideAnimation;

  Map<String, dynamic>? userStats;
  List<Map<String, dynamic>> recentActivity = [];

  bool showActivityFeed = true;

  @override
  void initState() {
    super.initState();
    _initializeAnimations();
    _loadUserData();
    _setupScrollListener();
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
    ScreenType type,
    double width,
    bool hasHinge,
  ) {
    switch (type) {
      case ScreenType.expanded:
        return ResponsiveConfig(
          paddingH: 24,
          paddingV: 16,
          contentMax: double.infinity,
          avatarSize: 130,
          headerFontSize: 32,
          titleFontSize: 18,
          bodyFontSize: 16,
          iconSize: 28,
          buttonHeight: 64,
          wideMode: true,
          hasHinge: true,
          useTwoColumnLayout: width >= 900,
        );
      case ScreenType.large:
        return ResponsiveConfig(
          paddingH: 40,
          paddingV: 20,
          contentMax: 1200,
          avatarSize: 140,
          headerFontSize: 34,
          titleFontSize: 18,
          bodyFontSize: 16,
          iconSize: 28,
          buttonHeight: 64,
          wideMode: true,
          hasHinge: false,
          useTwoColumnLayout: width >= 1100,
        );
      case ScreenType.medium:
        return ResponsiveConfig(
          paddingH: 24,
          paddingV: 12,
          contentMax: double.infinity,
          avatarSize: 120,
          headerFontSize: 30,
          titleFontSize: 16,
          bodyFontSize: 15,
          iconSize: 26,
          buttonHeight: 60,
          wideMode: true,
          hasHinge: false,
          useTwoColumnLayout: width >= 900,
        );
      case ScreenType.compact:
      default:
        return ResponsiveConfig(
          paddingH: width < 360 ? 14 : 16,
          paddingV: 8,
          contentMax: double.infinity,
          avatarSize: width < 360 ? 100 : 110,
          headerFontSize: width < 360 ? 26 : 28,
          titleFontSize: width < 360 ? 14 : 15,
          bodyFontSize: width < 360 ? 13 : 14,
          iconSize: width < 360 ? 22 : 24,
          buttonHeight: width < 360 ? 52 : 56,
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

  void _initializeAnimations() {
    _animationController =
        AnimationController(duration: _Motion.enter, vsync: this);
    _profileImageController = AnimationController(
        duration: const Duration(milliseconds: 1200), vsync: this);

    _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
        CurvedAnimation(parent: _animationController, curve: Curves.easeOut));
    _scaleAnimation = Tween<double>(begin: 0.92, end: 1.0).animate(
        CurvedAnimation(parent: _animationController, curve: _Motion.settle));
    _slideAnimation = Tween<Offset>(
            begin: _platformReduceMotion()
                ? Offset.zero
                : const Offset(0, 0.06),
            end: Offset.zero)
        .animate(CurvedAnimation(
            parent: _animationController, curve: _Motion.settle));

    _animationController.forward();
    // The avatar glow used to breathe forever. It now settles once at a
    // soft, steady halo (0.6 of the old peak) and stays there.
    _profileImageController.value = 0.6;
  }

  void _setupScrollListener() {
    _scrollController.addListener(() {
      final offset = _scrollController.offset;
      // Only the header (0–200 px) and avatar (0–500 px) react to scroll.
      // Rebuilding the whole page on every scrolled pixel past that was
      // the main cause of jank on long profiles.
      if (offset > 520 && _scrollOffset > 520) return;
      if ((offset - _scrollOffset).abs() < 2) return;
      setState(() => _scrollOffset = offset);
    });
  }

  Future<void> _loadUserData() async {
    if (!mounted) return;

    setState(() => isLoading = true);

    try {
      await _fetchUserStats();
      await _fetchRecentActivity();
    } catch (e) {
      _showErrorSnackBar('Failed to load profile data');
    } finally {
      if (mounted) {
        setState(() => isLoading = false);
      }
    }
  }

  Future<void> _fetchUserStats() async {
    try {
      final userId = currentUser?.uid;
      if (userId == null) return;

      final userDoc = await FirebaseFirestore.instance
          .collection('users')
          .doc(userId)
          .get();

      if (userDoc.exists) {
        final data = userDoc.data()!;
        final memberSince = (data['created_time'] as Timestamp?)?.toDate();
        final daysSinceMember = memberSince != null
            ? DateTime.now().difference(memberSince).inDays
            : 0;

        final appointmentsQuery = await FirebaseFirestore.instance
            .collection('appointments')
            .where('userId', isEqualTo: userId)
            .get();

        final dependentsQuery = await FirebaseFirestore.instance
            .collection('users')
            .doc(userId)
            .collection('dependents')
            .get();

        if (!mounted) return;
        setState(() {
          userStats = {
            'daysSinceMember': daysSinceMember,
            'totalAppointments': appointmentsQuery.docs.length,
            'activeDependents': dependentsQuery.docs.length,
            'membershipTier': data['planType'] ?? 'Standard',
            'profileCompletion': _calculateProfileCompletion(data),
            'lastLoginDate': data['last_active_time'] != null
                ? (data['last_active_time'] as Timestamp).toDate()
                : DateTime.now(),
          };
        });
      }
    } catch (e) {
      debugPrint('Error fetching user stats: $e');
    }
  }

  double _calculateProfileCompletion(Map<String, dynamic> userData) {
    double completion = 0.0;
    final fields = [
      'display_name',
      'first',
      'last',
      'email',
      'phone_number',
      'photo_url',
      'birth_date',
      'address',
      'emergency_contact'
    ];
    for (String field in fields) {
      if (userData[field] != null && userData[field].toString().isNotEmpty) {
        completion += 1.0 / fields.length;
      }
    }
    return completion;
  }

  Future<void> _fetchRecentActivity() async {
    try {
      final userId = currentUser?.uid;
      if (userId == null) return;

      final recentAppointments = await FirebaseFirestore.instance
          .collection('appointments')
          .where('userId', isEqualTo: userId)
          .orderBy('scheduledTime', descending: true)
          .limit(3)
          .get();

      final activities = <Map<String, dynamic>>[];

      for (var doc in recentAppointments.docs) {
        final data = doc.data();
        activities.add({
          'type': 'appointment',
          'title': 'Appointment ${data['status'] ?? 'Scheduled'}',
          'subtitle':
              'Dr. ${data['doctorName'] ?? 'Unknown'} - ${data['specialty'] ?? 'General'}',
          'timestamp':
              (data['scheduledTime'] as Timestamp?)?.toDate() ?? DateTime.now(),
          'icon': Icons.medical_services,
          'color': joviMint,
        });
      }

      // (A synthetic "Profile Updated" row stamped with the last-login time
      // used to be injected here. It was not a real event, so it is gone.)

      activities.sort((a, b) =>
          (b['timestamp'] as DateTime).compareTo(a['timestamp'] as DateTime));

      if (!mounted) return;
      setState(() {
        recentActivity = activities.take(5).toList();
      });
    } catch (e) {
      debugPrint('Error fetching recent activity: $e');
    }
  }

  Future<void> _refreshProfile() async {
    if (isRefreshing) return;

    setState(() => isRefreshing = true);
    HapticFeedback.mediumImpact();

    await _loadUserData();

    if (!mounted) return;
    setState(() => isRefreshing = false);
    _showSuccessSnackBar('Profile refreshed');
  }

  @override
  void dispose() {
    _animationController.dispose();
    _profileImageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final headerOpacity = math.max(0.0, 1.0 - (_scrollOffset / 200)).toDouble();
    final avatarScale = math.max(0.7, 1.0 - (_scrollOffset / 500)).toDouble();

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        statusBarBrightness: Brightness.dark,
      ),
      child: wrapWithConstraints(
        child: Container(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [joviNavy, joviNavyDark, joviNavyDark],
              stops: [0.0, 0.6, 1.0],
            ),
          ),
          child: Scaffold(
            backgroundColor: Colors.transparent,
            body: Stack(
              children: [
                RefreshIndicator(
                  onRefresh: _refreshProfile,
                  color: joviCoral,
                  backgroundColor: joviNavy,
                  child: CustomScrollView(
                    controller: _scrollController,
                    physics: BouncingScrollPhysics(),
                    slivers: [
                      _buildEnhancedAppBar(headerOpacity, avatarScale),
                      _buildActivityFeedSection(),
                      _buildMenuSection(),
                      _buildActionButtonsSection(),
                    ],
                  ),
                ),
                if (isLoading) _buildLoadingOverlay(),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildEnhancedAppBar(double headerOpacity, double avatarScale) {
    final mediaQuery = MediaQuery.of(context);
    final statusBarHeight = mediaQuery.padding.top;

    final expandedHeight =
        (layoutSettings.wideMode ? 480.0 : 440.0) + statusBarHeight;

    return SliverAppBar(
      expandedHeight: expandedHeight,
      floating: false,
      pinned: true,
      stretch: true,
      backgroundColor: joviNavy,
      elevation: 0,
      automaticallyImplyLeading: false,
      leading: Container(
        margin: EdgeInsets.only(
          top: statusBarHeight * 0.5,
          left: layoutSettings.paddingH * 0.5,
        ),
        child: IconButton(
          icon: Container(
            padding: EdgeInsets.all(layoutSettings.paddingH * 0.5),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.12),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.white.withOpacity(0.2)),
            ),
            child: Icon(Icons.arrow_back,
                color: Colors.white, size: layoutSettings.iconSize * 0.8),
          ),
          onPressed: () {
            HapticFeedback.lightImpact();
            context.pop();
          },
        ),
      ),
      flexibleSpace: FlexibleSpaceBar(
        stretchModes: [StretchMode.zoomBackground, StretchMode.fadeTitle],
        background: Container(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [joviNavy, joviNavyDark, joviNavyDark],
              stops: [0.0, 0.6, 1.0],
            ),
          ),
          child: Stack(
            children: [
              // Subtle coral glow in top-right for warmth
              Positioned(
                top: -60,
                right: -60,
                child: Container(
                  width: 280,
                  height: 280,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: RadialGradient(
                      colors: [
                        joviCoral.withOpacity(0.18),
                        joviCoral.withOpacity(0.05),
                        Colors.transparent,
                      ],
                      stops: const [0.0, 0.5, 1.0],
                    ),
                  ),
                ),
              ),
              Positioned.fill(
                child: CustomPaint(
                  painter:
                      PremiumPatternPainter(animation: _animationController),
                ),
              ),
              Positioned(
                left: 0,
                right: 0,
                bottom: 60,
                top: statusBarHeight + 60,
                child: Opacity(
                  opacity: headerOpacity,
                  child: Transform.scale(
                    scale: avatarScale,
                    child: SlideTransition(
                      position: _slideAnimation,
                      child: FadeTransition(
                        opacity: _fadeAnimation,
                        child: _buildProfileHeader(),
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

  Widget _buildProfileHeader() {
    return Column(
      children: [
        Stack(
          alignment: Alignment.center,
          children: [
            AnimatedBuilder(
              animation: _profileImageController,
              builder: (context, child) {
                return Container(
                  width: layoutSettings.avatarSize +
                      20 +
                      (_profileImageController.value * 10),
                  height: layoutSettings.avatarSize +
                      20 +
                      (_profileImageController.value * 10),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: RadialGradient(
                      colors: [
                        joviCoral
                            .withOpacity(0.4 * _profileImageController.value),
                        joviCoral.withOpacity(0.0),
                      ],
                    ),
                  ),
                );
              },
            ),
            Container(
              width: layoutSettings.avatarSize,
              height: layoutSettings.avatarSize,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(color: Colors.white, width: 4),
                boxShadow: [
                  BoxShadow(
                    color: joviCoral.withOpacity(0.3),
                    blurRadius: 25,
                    offset: Offset(0, 15),
                  ),
                ],
              ),
              child: ClipRRect(
                borderRadius:
                    BorderRadius.circular(layoutSettings.avatarSize / 2),
                child: StreamBuilder<DocumentSnapshot>(
                  stream: FirebaseFirestore.instance
                      .collection('users')
                      .doc(currentUser?.uid)
                      .snapshots(),
                  builder: (context, snapshot) {
                    if (snapshot.hasData && snapshot.data!.exists) {
                      final userData =
                          snapshot.data!.data() as Map<String, dynamic>?;
                      final photoUrl = userData?['photo_url'] as String?;

                      if (photoUrl != null && photoUrl.isNotEmpty) {
                        return Image.network(
                          photoUrl,
                          width: layoutSettings.avatarSize,
                          height: layoutSettings.avatarSize,
                          fit: BoxFit.cover,
                          loadingBuilder: (context, child, loadingProgress) {
                            if (loadingProgress == null) return child;
                            return Center(
                              child: CircularProgressIndicator(
                                valueColor:
                                    AlwaysStoppedAnimation<Color>(joviCoral),
                                strokeWidth: 2,
                              ),
                            );
                          },
                          errorBuilder: (context, error, stackTrace) {
                            return _buildDefaultAvatar();
                          },
                        );
                      }
                    }
                    return _buildDefaultAvatar();
                  },
                ),
              ),
            ),
            Positioned(
              right: layoutSettings.paddingH * 0.5,
              bottom: layoutSettings.paddingH * 0.5,
              child: Container(
                width: layoutSettings.iconSize * 0.8,
                height: layoutSettings.iconSize * 0.8,
                decoration: BoxDecoration(
                  color: joviCoral,
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.white, width: 3),
                  boxShadow: [
                    BoxShadow(
                      color: joviCoral.withOpacity(0.5),
                      blurRadius: 8,
                      offset: Offset(0, 2),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
        SizedBox(height: layoutSettings.paddingV * 2.5),
        _buildGreeting(),
        SizedBox(height: layoutSettings.paddingV),
        _buildUserName(),
        SizedBox(height: layoutSettings.paddingV * 0.75),
        _buildEmailWithVerification(),
        SizedBox(height: layoutSettings.paddingV * 2.5),
        _buildMembershipBadge(),
      ],
    );
  }

  Widget _buildDefaultAvatar() {
    return Container(
      width: layoutSettings.avatarSize,
      height: layoutSettings.avatarSize,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            joviCoral.withOpacity(0.3),
            joviCoralLight.withOpacity(0.15),
          ],
        ),
        shape: BoxShape.circle,
      ),
      child: Icon(Icons.person,
          size: layoutSettings.avatarSize * 0.5, color: Colors.white),
    );
  }

  Widget _buildGreeting() {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(_getGreetingIcon(),
            color: joviGold.withOpacity(0.85),
            size: layoutSettings.iconSize * 0.67),
        SizedBox(width: layoutSettings.paddingH * 0.375),
        Text(
          _getGreeting(),
          style: TextStyle(
              color: Colors.white70, fontSize: layoutSettings.bodyFontSize),
        ),
      ],
    );
  }

  Widget _buildUserName() {
    return AuthUserStreamWidget(
      builder: (context) => Text(
        _getDisplayName(),
        style: TextStyle(
          color: Colors.white,
          fontSize: layoutSettings.headerFontSize,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.7,
        ),
        textAlign: TextAlign.center,
      ),
    );
  }

  String _getDisplayName() {
    if (currentUserDocument?.displayName != null &&
        currentUserDocument!.displayName!.isNotEmpty) {
      return currentUserDocument!.displayName!;
    }

    final firstName = currentUserDocument?.first ?? '';
    final lastName = currentUserDocument?.last ?? '';
    final fullName = '$firstName $lastName'.trim();

    return fullName.isNotEmpty ? fullName : 'Welcome';
  }

  Widget _buildEmailWithVerification() {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          currentUserEmail,
          style: TextStyle(
            color: Colors.white.withOpacity(0.9),
            fontSize: layoutSettings.bodyFontSize,
          ),
        ),
        if (currentUser?.emailVerified ?? false) ...[
          SizedBox(width: layoutSettings.paddingH * 0.375),
          Icon(Icons.verified,
              color: joviCoral, size: layoutSettings.iconSize * 0.67),
        ],
      ],
    );
  }

  Widget _buildMembershipBadge() {
    return AuthUserStreamWidget(
      builder: (context) {
        final planType = currentUserDocument?.planType ?? 'Standard';
        final isPremium = planType.toLowerCase().contains('family') ||
            planType.toLowerCase().contains('premium');

        return Container(
          padding: EdgeInsets.symmetric(
              horizontal: layoutSettings.paddingH * 1.25,
              vertical: layoutSettings.paddingV * 1.2),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: isPremium
                  ? [joviGold.withOpacity(0.45), joviGold.withOpacity(0.25)]
                  : [joviCoral.withOpacity(0.35), joviCoral.withOpacity(0.2)],
            ),
            borderRadius: BorderRadius.circular(25),
            border: Border.all(
                color: isPremium
                    ? joviGold.withOpacity(0.6)
                    : joviCoral.withOpacity(0.5),
                width: 1.5),
            boxShadow: [
              BoxShadow(
                color: (isPremium ? joviGold : joviCoral).withOpacity(0.2),
                blurRadius: 10,
                offset: Offset(0, 5),
              ),
            ],
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                isPremium ? Icons.star : Icons.account_circle,
                color: Colors.white,
                size: layoutSettings.iconSize * 0.75,
              ),
              SizedBox(width: layoutSettings.paddingH * 0.5),
              Text(
                '$planType Member',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: layoutSettings.bodyFontSize * 0.93,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildActivityFeedSection() {
    if (recentActivity.isEmpty)
      return SliverToBoxAdapter(child: SizedBox.shrink());

    return SliverToBoxAdapter(
      child: Padding(
        padding: EdgeInsets.all(layoutSettings.paddingH),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildSectionHeader(
              'RECENT ACTIVITY',
              showActivityFeed,
              () => setState(() => showActivityFeed = !showActivityFeed),
            ),
            if (showActivityFeed) ...[
              SizedBox(height: layoutSettings.paddingV * 2),
              // Glass activity card
              Container(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(18),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.25),
                      blurRadius: 12,
                      offset: Offset(0, 4),
                    ),
                  ],
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(18),
                  child: RepaintBoundary(
                    child: Container(
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.08),
                        borderRadius: BorderRadius.circular(18),
                        border: Border.all(
                            color: Colors.white.withOpacity(0.12), width: 1),
                      ),
                      child: layoutSettings.useTwoColumnLayout
                          ? _buildTwoColumnActivityLayout()
                          : _buildSingleColumnActivityLayout(),
                    ),
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildSingleColumnActivityLayout() {
    return Column(
      children: recentActivity.asMap().entries.map((entry) {
        final index = entry.key;
        final activity = entry.value;
        final isLast = index == recentActivity.length - 1;
        return _buildActivityItem(activity, isLast);
      }).toList(),
    );
  }

  Widget _buildTwoColumnActivityLayout() {
    final itemCount = recentActivity.length;
    final halfCount = (itemCount / 2).ceil();

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Column(
            children: recentActivity.take(halfCount).map((activity) {
              return _buildActivityItem(activity, false);
            }).toList(),
          ),
        ),
        Container(
          width: 1,
          height: 200,
          color: Colors.white.withOpacity(0.1),
        ),
        Expanded(
          child: Column(
            children: recentActivity.skip(halfCount).map((activity) {
              return _buildActivityItem(activity, false);
            }).toList(),
          ),
        ),
      ],
    );
  }

  Widget _buildMenuSection() {
    return SliverToBoxAdapter(
      child: Padding(
        padding: EdgeInsets.fromLTRB(
            layoutSettings.paddingH,
            layoutSettings.paddingV,
            layoutSettings.paddingH,
            layoutSettings.paddingV),
        child: Row(
          children: [
            Container(
              width: 3,
              height: layoutSettings.titleFontSize,
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [joviCoral, joviCoralLight],
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                ),
                borderRadius: BorderRadius.circular(2),
                boxShadow: [
                  BoxShadow(
                    color: joviCoral.withOpacity(0.5),
                    blurRadius: 6,
                    offset: Offset(0, 1),
                  ),
                ],
              ),
            ),
            SizedBox(width: layoutSettings.paddingH * 0.5),
            Text(
              'ACCOUNT SETTINGS',
              style: TextStyle(
                fontSize: layoutSettings.bodyFontSize * 0.86,
                fontWeight: FontWeight.w700,
                color: Colors.white.withOpacity(0.6),
                letterSpacing: 1.2,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActionButtonsSection() {
    return SliverToBoxAdapter(
      child: Padding(
        padding: EdgeInsets.fromLTRB(
            layoutSettings.paddingH,
            layoutSettings.paddingV * 2.5,
            layoutSettings.paddingH,
            layoutSettings.paddingV * 5),
        child: Column(
          children: [
            _buildMenuItems(),
            SizedBox(height: layoutSettings.paddingV * 4),
            _buildSignOutButton(),
            SizedBox(height: layoutSettings.paddingV * 2),
            _buildDeleteAccountButton(),
            SizedBox(height: layoutSettings.paddingV * 3),
          ],
        ),
      ),
    );
  }

  Widget _buildMenuItems() {
    final menuItems = [
      {
        'icon': Icons.account_circle_outlined,
        'title': 'Update Membership',
        'subtitle': 'Edit your membership',
        'color': joviCoral,
        'route': 'updateProfile',
      },
      {
        'icon': Icons.receipt_long_outlined,
        'title': 'Billing',
        'subtitle': 'Manage your card and view past transactions',
        'color': joviGold,
        'route': 'userBill',
      },
      {
        'icon': Icons.security,
        'title': 'Two-Factor Authentication',
        'subtitle': 'Add extra security to your account',
        'color': joviMint,
        'route': 'twoFA',
      },
      {
        'icon': Icons.article_outlined,
        'title': 'Membership Agreement',
        'subtitle': 'Review our membership agreement',
        'color': joviGold,
        'action': () =>
            _launchUrl('https://jovihealth.com/membership-agreement'),
      },
      {
        'icon': Icons.description_outlined,
        'title': 'Terms of Service',
        'subtitle': 'Review our terms of service',
        'color': joviCoralLight,
        'action': () => _launchUrl('https://jovihealth.com/terms'),
      },
    ];

    // Build a tappable row widget for a single menu item. Factored out so
    // the two-column layout can reuse it without repeating the tap wiring.
    Widget buildItemTile(Map<String, dynamic> item) {
      return _buildMenuItem(
        icon: item['icon'] as IconData,
        title: item['title'] as String,
        subtitle: item['subtitle'] as String,
        color: item['color'] as Color,
        onTap: () {
          HapticFeedback.lightImpact();
          if (item['route'] != null) {
            try {
              context.pushNamed(item['route'] as String);
            } catch (e) {
              debugPrint('Navigation error for ${item['route']}: $e');
              _showErrorSnackBar('Page not available: ${item['title']}');
            }
          } else if (item['action'] != null) {
            (item['action'] as VoidCallback)();
          }
        },
      );
    }

    if (layoutSettings.useTwoColumnLayout) {
      // Pair items up into rows of 2. Handles any count — a trailing
      // odd item gets a full-width row to itself.
      final rows = <Widget>[];
      for (int i = 0; i < menuItems.length; i += 2) {
        final left = menuItems[i];
        final right = i + 1 < menuItems.length ? menuItems[i + 1] : null;
        rows.add(Padding(
          padding: EdgeInsets.only(bottom: layoutSettings.paddingV),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(child: buildItemTile(left)),
              if (right != null) ...[
                SizedBox(width: layoutSettings.paddingH * 0.5),
                Expanded(child: buildItemTile(right)),
              ],
            ],
          ),
        ));
      }
      return Column(children: rows);
    } else {
      return Column(
        children: menuItems
            .map((item) => Padding(
                  padding: EdgeInsets.only(bottom: layoutSettings.paddingV),
                  child: buildItemTile(item),
                ))
            .toList(),
      );
    }
  }

  Widget _buildSectionHeader(String title, bool expanded, VoidCallback onTap) {
    return _Pressable(
      onTap: () {
        HapticFeedback.lightImpact();
        onTap();
      },
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            children: [
              Container(
                width: 3,
                height: layoutSettings.titleFontSize,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [joviCoral, joviCoralLight],
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                  ),
                  borderRadius: BorderRadius.circular(2),
                  boxShadow: [
                    BoxShadow(
                      color: joviCoral.withOpacity(0.5),
                      blurRadius: 6,
                      offset: Offset(0, 1),
                    ),
                  ],
                ),
              ),
              SizedBox(width: layoutSettings.paddingH * 0.5),
              Text(
                title,
                style: TextStyle(
                  fontSize: layoutSettings.bodyFontSize * 0.86,
                  fontWeight: FontWeight.w700,
                  color: Colors.white.withOpacity(0.6),
                  letterSpacing: 1.2,
                ),
              ),
            ],
          ),
          Container(
            padding: EdgeInsets.all(4),
            decoration: BoxDecoration(
              color: joviCoral.withOpacity(0.12),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(
              expanded ? Icons.expand_less : Icons.expand_more,
              color: joviCoral,
              size: layoutSettings.iconSize * 0.83,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActivityItem(Map<String, dynamic> activity, bool isLast) {
    final timestamp = activity['timestamp'] as DateTime;
    final timeAgo = _getTimeAgo(timestamp);

    return Container(
      padding: EdgeInsets.all(layoutSettings.paddingH),
      decoration: BoxDecoration(
        border: isLast
            ? null
            : Border(
                bottom:
                    BorderSide(color: Colors.white.withOpacity(0.08), width: 1),
              ),
      ),
      child: Row(
        children: [
          Container(
            width: layoutSettings.iconSize * 1.9,
            height: layoutSettings.iconSize * 1.9,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  (activity['color'] as Color).withOpacity(0.25),
                  (activity['color'] as Color).withOpacity(0.12),
                ],
              ),
              border: Border.all(
                  color: (activity['color'] as Color).withOpacity(0.3)),
              borderRadius: BorderRadius.circular(12),
              boxShadow: [
                BoxShadow(
                  color: (activity['color'] as Color).withOpacity(0.2),
                  blurRadius: 8,
                  offset: Offset(0, 2),
                ),
              ],
            ),
            child: Icon(
              activity['icon'] as IconData,
              color: activity['color'] as Color,
              size: layoutSettings.iconSize * 0.85,
            ),
          ),
          SizedBox(width: layoutSettings.paddingH * 0.75),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  activity['title'] as String,
                  style: TextStyle(
                    fontSize: layoutSettings.bodyFontSize,
                    fontWeight: FontWeight.w600,
                    color: Colors.white,
                  ),
                ),
                SizedBox(height: 2),
                Text(
                  activity['subtitle'] as String,
                  style: TextStyle(
                    fontSize: layoutSettings.bodyFontSize * 0.86,
                    color: Colors.white.withOpacity(0.6),
                  ),
                ),
              ],
            ),
          ),
          Text(
            timeAgo,
            style: TextStyle(
              fontSize: layoutSettings.bodyFontSize * 0.79,
              color: Colors.white.withOpacity(0.45),
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMenuItem({
    required IconData icon,
    required String title,
    required String subtitle,
    required Color color,
    required VoidCallback onTap,
  }) {
    return _Pressable(
        feedbackOnly: true,
        pressedScale: 0.985,
        child: Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        splashColor: color.withOpacity(0.18),
        highlightColor: color.withOpacity(0.08),
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.25),
                blurRadius: 8,
                offset: Offset(0, 3),
              ),
            ],
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(16),
            child: RepaintBoundary(
              child: Container(
                padding: EdgeInsets.all(layoutSettings.paddingH),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.08),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                      color: Colors.white.withOpacity(0.12), width: 1),
                ),
                child: Row(
                  children: [
                    Container(
                      width: layoutSettings.iconSize * 2.2,
                      height: layoutSettings.iconSize * 2.2,
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: [
                            color.withOpacity(0.25),
                            color.withOpacity(0.12),
                          ],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(color: color.withOpacity(0.3)),
                        boxShadow: [
                          BoxShadow(
                            color: color.withOpacity(0.25),
                            blurRadius: 10,
                            offset: Offset(0, 3),
                          ),
                        ],
                      ),
                      child: Icon(icon,
                          color: color, size: layoutSettings.iconSize),
                    ),
                    SizedBox(width: layoutSettings.paddingH),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            title,
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: layoutSettings.titleFontSize,
                              fontWeight: FontWeight.w600,
                              letterSpacing: -0.1,
                            ),
                          ),
                          SizedBox(height: 4),
                          Text(
                            subtitle,
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.55),
                              fontSize: layoutSettings.bodyFontSize * 0.86,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Container(
                      padding: EdgeInsets.all(4),
                      decoration: BoxDecoration(
                        color: joviCoral.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Icon(
                        Icons.chevron_right,
                        color: joviCoral,
                        size: layoutSettings.iconSize * 0.83,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      )),
    );
  }

  Widget _buildSignOutButton() {
    return _Pressable(
        feedbackOnly: true,
        child: Container(
      width: double.infinity,
      height: layoutSettings.buttonHeight,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [joviCoral, joviCoralDark],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: joviCoral.withOpacity(0.45),
            blurRadius: 16,
            offset: Offset(0, 6),
          ),
        ],
      ),
      child: ElevatedButton(
        onPressed: () {
          HapticFeedback.mediumImpact();
          _showSignOutDialog();
        },
        style: ElevatedButton.styleFrom(
          backgroundColor: Colors.transparent,
          shadowColor: Colors.transparent,
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.logout,
                color: Colors.white, size: layoutSettings.iconSize * 0.83),
            SizedBox(width: layoutSettings.paddingH * 0.625),
            Text(
              'Sign Out',
              style: TextStyle(
                color: Colors.white,
                fontSize: layoutSettings.titleFontSize + 1,
                fontWeight: FontWeight.w600,
                letterSpacing: -0.2,
              ),
            ),
          ],
        ),
      ),
    ));
  }

  Widget _buildDeleteAccountButton() {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.03),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: joviErrorRed.withOpacity(0.25)),
      ),
      child: TextButton(
        onPressed: () {
          HapticFeedback.heavyImpact();
          _showDeleteAccountDialog();
        },
        style: TextButton.styleFrom(
          foregroundColor: joviErrorRed,
          padding: EdgeInsets.symmetric(
              vertical: layoutSettings.paddingV * 1.5,
              horizontal: layoutSettings.paddingH * 1.5),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.delete_forever,
                size: layoutSettings.iconSize * 0.83,
                color: joviErrorRed.withOpacity(0.85)),
            SizedBox(width: layoutSettings.paddingH * 0.5),
            Text(
              'Delete Account',
              style: TextStyle(
                fontSize: layoutSettings.bodyFontSize,
                fontWeight: FontWeight.w500,
                color: joviErrorRed.withOpacity(0.85),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLoadingOverlay() {
    return Positioned.fill(
      child: Container(
        color: joviNavyDark.withOpacity(0.55),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 8, sigmaY: 8),
          child: Center(
            child: Container(
              padding: EdgeInsets.all(layoutSettings.paddingH * 2),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(20),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.4),
                    blurRadius: 25,
                    offset: Offset(0, 15),
                  ),
                ],
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(20),
                child: BackdropFilter(
                  filter: ImageFilter.blur(sigmaX: 15, sigmaY: 15),
                  child: Container(
                    padding: EdgeInsets.all(layoutSettings.paddingH * 2),
                    decoration: BoxDecoration(
                      color: joviNavy.withOpacity(0.85),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: Colors.white.withOpacity(0.15)),
                    ),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        CircularProgressIndicator(
                          valueColor: AlwaysStoppedAnimation<Color>(joviCoral),
                          strokeWidth: 3,
                        ),
                        SizedBox(height: layoutSettings.paddingV * 2.5),
                        Text(
                          'Loading your profile…',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: layoutSettings.titleFontSize + 1,
                            fontWeight: FontWeight.w500,
                          ),
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
    );
  }

  // Dialog methods — rebuilt as navy glass

  void _showSignOutDialog() {
    showDialog(
      context: context,
      barrierColor: Colors.black.withOpacity(0.55),
      builder: (context) => Dialog(
        backgroundColor: Colors.transparent,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(20),
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 18, sigmaY: 18),
            child: Container(
              padding: EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: joviNavy.withOpacity(0.92),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: Colors.white.withOpacity(0.15)),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.4),
                    blurRadius: 30,
                    offset: Offset(0, 15),
                  ),
                ],
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: joviCoral.withOpacity(0.18),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: joviCoral.withOpacity(0.4)),
                        ),
                        child: Icon(Icons.logout, color: joviCoral, size: 20),
                      ),
                      SizedBox(width: 12),
                      Text(
                        'Sign Out',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                          fontSize: 18,
                        ),
                      ),
                    ],
                  ),
                  SizedBox(height: 16),
                  Text(
                    'Are you sure you want to sign out of your account?',
                    style: TextStyle(
                        color: Colors.white.withOpacity(0.75), fontSize: 14),
                  ),
                  SizedBox(height: 24),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      TextButton(
                        onPressed: () => Navigator.pop(context),
                        style: TextButton.styleFrom(
                          foregroundColor: Colors.white.withOpacity(0.7),
                          padding: EdgeInsets.symmetric(
                              horizontal: 18, vertical: 12),
                        ),
                        child: Text('Cancel',
                            style: TextStyle(
                                color: Colors.white.withOpacity(0.7))),
                      ),
                      SizedBox(width: 8),
                      ElevatedButton(
                        onPressed: () => _performSignOut(),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: joviCoral,
                          foregroundColor: Colors.white,
                          padding: EdgeInsets.symmetric(
                              horizontal: 20, vertical: 12),
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12)),
                          elevation: 3,
                          shadowColor: joviCoral.withOpacity(0.4),
                        ),
                        child: Text('Sign Out',
                            style: TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.w600)),
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

  void _showDeleteAccountDialog() {
    showCupertinoDialog<void>(
      context: context,
      builder: (ctx) => CupertinoAlertDialog(
        title: const Text('Delete Account?'),
        content: const Padding(
          padding: EdgeInsets.only(top: 8),
          child: Text(
              'This permanently deletes your account and everything in it: your profile, family and pet records, care history, claims, symptom checks, activity history and billing records. This cannot be undone.'),
        ),
        actions: [
          CupertinoDialogAction(
            isDefaultAction: true,
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          CupertinoDialogAction(
            isDestructiveAction: true,
            onPressed: () {
              Navigator.pop(ctx);
              _performAccountDeletion();
            },
            child: const Text('Delete Account'),
          ),
        ],
      ),
    );
  }

  Future<void> _performSignOut() async {
    Navigator.pop(context);
    setState(() => isLoading = true);

    try {
      await FirebaseAuth.instance.signOut();
      if (mounted) {
        context.goNamedAuth('Landing', context.mounted);
      }
    } catch (e) {
      if (!mounted) return;
      setState(() => isLoading = false);
      _showErrorSnackBar('Error signing out. Please try again.');
    }
  }

  // ─── Account deletion ────────────────────────────────────────────────
  // Every collection the app writes under users/{uid}, nested where the
  // widgets nest them. Kept in sync with functions/deleteUserData.js, the
  // Cloud Function that runs on auth-user deletion and is the authoritative
  // server-side wipe (it also removes the member's Storage files). This
  // client pass is best-effort so the account is clean even before that
  // function is deployed, and so nothing is left if it ever fails.
  static const Map<String, Map<String, dynamic>> _userTree = {
    'activities': {'points': <String, dynamic>{}},
    'billing_history': <String, dynamic>{},
    'claims': <String, dynamic>{},
    'dependents': <String, dynamic>{},
    'medicationFavorites': <String, dynamic>{},
    'medicationRecent': <String, dynamic>{},
    'members': {
      'medications': <String, dynamic>{},
      'medication_history': <String, dynamic>{},
    },
    'pets': {
      'claims': <String, dynamic>{},
      'medications': <String, dynamic>{},
      'dose_events': <String, dynamic>{},
      'symptom_checks': <String, dynamic>{},
      'vaccinations': <String, dynamic>{},
      'vet_weight_logs': <String, dynamic>{},
    },
    'prefs': <String, dynamic>{},
    'scheduled_reminders': <String, dynamic>{},
    'side_effects': <String, dynamic>{},
    'symptom_checks': <String, dynamic>{},
    'transactions': <String, dynamic>{},
    'visit_records': <String, dynamic>{},
    'vital_goals': <String, dynamic>{},
    'vital_signs': <String, dynamic>{},
    'weight_alerts': <String, dynamic>{},
  };

  /// Top-level collections that store records keyed by the member's uid,
  /// with the field name each one uses.
  static const Map<String, String> _topLevelByUser = {
    'appointments': 'userId',
    'cancelled_appointments': 'userId',
    'helpTickets': 'userId',
    'kurv_pass_cancellations': 'userId',
    'prescriptionRefills': 'userId',
    'prescriptions': 'userId',
    'refills': 'userId',
    'requests': 'userId',
    'security_logs': 'user_id',
  };

  static const Map<String, Map<String, dynamic>> _topLevelChildren = {
    'helpTickets': {'messages': <String, dynamic>{}},
  };

  static const int _wipePageSize = 200;

  Future<void> _deleteDocTree(DocumentReference<Map<String, dynamic>> doc,
      Map<String, dynamic> children) async {
    for (final entry in children.entries) {
      await _deleteCollectionTree(doc.collection(entry.key),
          Map<String, dynamic>.from(entry.value as Map));
    }
    await doc.delete();
  }

  Future<void> _deleteCollectionTree(
      CollectionReference<Map<String, dynamic>> col,
      Map<String, dynamic> children) async {
    while (true) {
      final snap = await col.limit(_wipePageSize).get();
      if (snap.docs.isEmpty) return;
      if (children.isEmpty) {
        final batch = FirebaseFirestore.instance.batch();
        for (final d in snap.docs) {
          batch.delete(d.reference);
        }
        await batch.commit();
      } else {
        for (final d in snap.docs) {
          await _deleteDocTree(d.reference, children);
        }
      }
      if (snap.docs.length < _wipePageSize) return;
    }
  }

  Future<void> _performAccountDeletion() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return;

    // Firebase only allows deleting an account within a few minutes of
    // signing in. Check BEFORE touching any data, so a stale session can
    // never leave a live account with an empty profile behind.
    final lastSignIn = user.metadata.lastSignInTime;
    if (lastSignIn == null ||
        DateTime.now().difference(lastSignIn) > const Duration(minutes: 4)) {
      _showErrorSnackBar(
          'For your security, please sign out, sign back in, and delete your account right away.');
      return;
    }

    setState(() => isLoading = true);
    final uid = user.uid;
    final db = FirebaseFirestore.instance;

    try {
      // 1. Everything under users/{uid}, deepest records first.
      for (final entry in _userTree.entries) {
        try {
          await _deleteCollectionTree(
              db.collection('users').doc(uid).collection(entry.key),
              Map<String, dynamic>.from(entry.value));
        } catch (e) {
          debugPrint('Account deletion: ${entry.key} cleanup failed: $e');
        }
      }

      // 2. Top-level records that reference this member.
      for (final entry in _topLevelByUser.entries) {
        try {
          while (true) {
            final snap = await db
                .collection(entry.key)
                .where(entry.value, isEqualTo: uid)
                .limit(_wipePageSize)
                .get();
            if (snap.docs.isEmpty) break;
            for (final d in snap.docs) {
              await _deleteDocTree(
                  d.reference,
                  Map<String, dynamic>.from(
                      _topLevelChildren[entry.key] ?? const {}));
            }
            if (snap.docs.length < _wipePageSize) break;
          }
        } catch (e) {
          debugPrint('Account deletion: ${entry.key} cleanup failed: $e');
        }
      }

      // 3. The profile document, then the sign-in itself. The auth
      //    deletion triggers the Cloud Function, which repeats the wipe
      //    server-side and clears Storage.
      try {
        await db.collection('users').doc(uid).delete();
      } catch (e) {
        debugPrint('Account deletion: profile cleanup failed: $e');
      }
      await user.delete();

      if (mounted) {
        context.goNamedAuth('Landing', context.mounted);
      }
    } on FirebaseAuthException catch (e) {
      if (!mounted) return;
      setState(() => isLoading = false);
      if (e.code == 'requires-recent-login') {
        _showErrorSnackBar(
            'For your security, please sign out, sign back in, and try deleting again.');
      } else {
        _showErrorSnackBar('Error deleting account. Please try again.');
      }
    } catch (e) {
      if (!mounted) return;
      setState(() => isLoading = false);
      _showErrorSnackBar('Error deleting account. Please try again.');
    }
  }

  Future<void> _launchUrl(String url) async {
    try {
      final Uri uri = Uri.parse(url);
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
      } else {
        _showErrorSnackBar('Unable to open link');
      }
    } catch (e) {
      _showErrorSnackBar('Error opening link');
    }
  }

  IconData _getGreetingIcon() {
    final hour = DateTime.now().hour;
    if (hour < 6) return Icons.nights_stay;
    if (hour < 12) return Icons.wb_sunny;
    if (hour < 17) return Icons.wb_sunny;
    if (hour < 20) return Icons.wb_twilight;
    return Icons.nights_stay;
  }

  String _getGreeting() {
    final hour = DateTime.now().hour;
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  }

  String _getTimeAgo(DateTime timestamp) {
    final now = DateTime.now();
    final difference = now.difference(timestamp);

    if (difference.inDays > 0) {
      return '${difference.inDays}d ago';
    } else if (difference.inHours > 0) {
      return '${difference.inHours}h ago';
    } else if (difference.inMinutes > 0) {
      return '${difference.inMinutes}m ago';
    } else {
      return 'Just now';
    }
  }

  void _showSuccessSnackBar(String message) {
    if (!mounted) return;
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(message,
        accent: joviMint, icon: CupertinoIcons.checkmark_circle));
  }

  void _showErrorSnackBar(String message) {
    if (!mounted) return;
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(message,
        accent: joviErrorRed,
        icon: CupertinoIcons.exclamationmark_circle,
        duration: const Duration(seconds: 4)));
  }
}

// Enhanced Premium Pattern Painter with coral-tinted particles
class PremiumPatternPainter extends CustomPainter {
  final Animation<double> animation;

  PremiumPatternPainter({required this.animation}) : super(repaint: animation);

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..style = PaintingStyle.fill;
    final animValue = animation.value;

    for (int i = 0; i < 20; i++) {
      final x = (size.width / 20) * i + (animValue * 30);
      final y = (size.height / 4) + math.sin(animValue * 2 * math.pi + i) * 20;

      final useCoral = i % 3 == 0;
      paint.color = useCoral
          ? joviCoral.withOpacity(0.08 + (animValue * 0.04))
          : Colors.white.withOpacity(0.04 + (animValue * 0.02));

      canvas.drawCircle(
        Offset(x % size.width, y),
        1.5 + (animValue * 0.5),
        paint,
      );
    }

    final gradientPaint = Paint()
      ..shader = RadialGradient(
        colors: [
          joviCoral.withOpacity(0.08 * animValue),
          joviCoral.withOpacity(0.0),
        ],
      ).createShader(Rect.fromCircle(
        center: Offset(size.width * 0.8, size.height * 0.3),
        radius: 60,
      ));

    canvas.drawCircle(
      Offset(size.width * 0.8, size.height * 0.3),
      50 + (animValue * 15),
      gradientPaint,
    );

    gradientPaint.shader = RadialGradient(
      colors: [
        Colors.white.withOpacity(0.05 * animValue),
        Colors.white.withOpacity(0.0),
      ],
    ).createShader(Rect.fromCircle(
      center: Offset(size.width * 0.2, size.height * 0.7),
      radius: 80,
    ));

    canvas.drawCircle(
      Offset(size.width * 0.2, size.height * 0.7),
      70 + (animValue * 10),
      gradientPaint,
    );

    paint.color = Colors.white.withOpacity(0.02 * animValue);
    for (double i = 0; i < size.width; i += 60) {
      for (double j = 0; j < size.height; j += 60) {
        final offset = math.sin(animValue * math.pi + (i + j) / 100) * 5;
        canvas.drawCircle(
          Offset(i + offset, j + offset),
          1,
          paint,
        );
      }
    }
  }

  @override
  bool shouldRepaint(CustomPainter oldDelegate) => true;
}
