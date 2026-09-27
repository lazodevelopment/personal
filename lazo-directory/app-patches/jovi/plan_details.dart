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
// JOVI HEALTH - PLAN DETAILS
// Version: 2026.09.22-r3 (self-serve cancel / keep membership card)
// r2: (Apple HIG pass: painted glass cards, press
//          feedback, honest status pill, Reduce Motion, navy toasts)
// r1:      2026.04.17
// Build: JC-PLAN-0922-002
//
// Full brand rework from the legacy blue-palette version:
// - Navy background with glass-morphism cards
// - Coral/mint accent system matching home dashboard
// - Firestore listener for live plan updates (was: fetch-once)
// - Mounted checks, null guards, substring safety
// - Haptics on all tappable rows
// - Responsive two-column layout on tablet/desktop
// - Renewal card, upgrade CTA, and tobacco warning rewritten
// ============================================================

import 'dart:ui' as ui_dart;
import 'dart:async';
import 'dart:convert';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';
import 'package:intl/intl.dart';
import 'package:cloud_functions/cloud_functions.dart';
import 'package:cached_network_image/cached_network_image.dart';

// ─── Jovi Brand Color System ───────────────────────────────
const Color _joviCoral = Color(0xFFFF6B4A);
const Color _joviCoralLight = Color(0xFFFF8F73);
const Color _joviCoralDark = Color(0xFFE5583A);
const Color _joviNavy = Color(0xFF1A2744);
const Color _joviNavyDark = Color(0xFF0F1A2E);
const Color _joviMint = Color(0xFF00D4AA);
const Color _joviMintDark = Color(0xFF00B894);
const Color _joviGold = Color(0xFFFFD166);
const Color _joviGoldDark = Color(0xFFE6B84D);
const Color _joviErrorRed = Color(0xFFE53935);

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

class PlanDetailsWidget extends StatefulWidget {
  final double width;
  final double height;

  const PlanDetailsWidget({
    Key? key,
    required this.width,
    required this.height,
  }) : super(key: key);

  @override
  PlanDetailsWidgetState createState() => PlanDetailsWidgetState();
}

class PlanDetailsWidgetState extends State<PlanDetailsWidget>
    with TickerProviderStateMixin {
  // ─── State ────────────────────────────────────────────────
  Map<String, dynamic>? _userData;
  bool _isLoading = true;
  List<Map<String, dynamic>> _members = [];
  DateTime? _renewalDate;
  String? _subscriptionStatus;
  DateTime? _willCancelOn;
  bool _membershipBusy = false;
  DateTime? _policyStartDate;
  StreamSubscription<DocumentSnapshot>? _profileSub;

  // ─── Animations ───────────────────────────────────────────
  late AnimationController _fadeCtrl;
  late AnimationController _slideCtrl;
  late Animation<double> _fadeAnim;
  late Animation<Offset> _slideAnim;

  // ─── Lifecycle ────────────────────────────────────────────
  @override
  void initState() {
    super.initState();
    _fadeCtrl = AnimationController(
      vsync: this,
      duration: _Motion.enter,
    );
    _slideCtrl = AnimationController(
      vsync: this,
      duration: _Motion.enter,
    );
    _fadeAnim = CurvedAnimation(parent: _fadeCtrl, curve: Curves.easeOut);
    _slideAnim = Tween<Offset>(
      begin: _platformReduceMotion() ? Offset.zero : const Offset(0, 0.04),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _slideCtrl, curve: _Motion.settle));
    _subscribeToProfile();
  }

  @override
  void dispose() {
    _fadeCtrl.dispose();
    _slideCtrl.dispose();
    _profileSub?.cancel();
    super.dispose();
  }

  // ─── Firestore listener (live updates) ────────────────────
  void _subscribeToProfile() {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      if (mounted) setState(() => _isLoading = false);
      return;
    }
    _profileSub = FirebaseFirestore.instance
        .collection('users')
        .doc(user.uid)
        .snapshots()
        .listen(
      (snap) {
        if (!mounted) return;
        if (!snap.exists) {
          setState(() => _isLoading = false);
          return;
        }
        final data = snap.data();
        _applyUserData(data);
      },
      onError: (e) {
        debugPrint('PlanDetails: error in profile listener: $e');
        if (mounted) setState(() => _isLoading = false);
      },
    );
  }

  void _applyUserData(Map<String, dynamic>? data) {
    if (data == null) {
      setState(() => _isLoading = false);
      return;
    }

    // Parse renewal date (Timestamp expected, but be defensive)
    DateTime? renewal;
    final rawRenew = data['renew'];
    if (rawRenew is Timestamp) {
      renewal = rawRenew.toDate();
    } else if (rawRenew is String && rawRenew.isNotEmpty) {
      try {
        renewal = DateTime.parse(rawRenew);
      } catch (_) {}
    }

    // Parse policy start (fallback: renewal - 1 year if missing)
    DateTime? policyStart;
    final rawStart = data['policyStart'];
    if (rawStart is Timestamp) {
      policyStart = rawStart.toDate();
    } else if (rawStart is String && rawStart.isNotEmpty) {
      try {
        policyStart = DateTime.parse(rawStart);
      } catch (_) {}
    }
    policyStart ??= renewal?.subtract(const Duration(days: 365));

    // Parse members — accept both JSON strings and already-parsed Maps
    List<Map<String, dynamic>> parsedMembers = [];
    final rawMembers = data['members'];
    if (rawMembers is List) {
      for (final m in rawMembers) {
        try {
          if (m is String) {
            final decoded = jsonDecode(m);
            if (decoded is Map) {
              parsedMembers.add(Map<String, dynamic>.from(decoded));
            }
          } else if (m is Map) {
            parsedMembers.add(Map<String, dynamic>.from(m));
          }
        } catch (e) {
          debugPrint('PlanDetails: skipped malformed member entry: $e');
        }
      }
    }

    // Cancellation state written by the cancelMembership Cloud Function.
    DateTime? willCancelOn;
    final rawCancel = data['willCancelOn'] ?? data['finalBillingDate'];
    if (rawCancel is Timestamp) {
      willCancelOn = rawCancel.toDate();
    } else if (rawCancel is String && rawCancel.isNotEmpty) {
      willCancelOn = DateTime.tryParse(rawCancel);
    }

    setState(() {
      _userData = data;
      _subscriptionStatus = data['subscriptionStatus'] as String?;
      _willCancelOn = willCancelOn;
      _renewalDate = renewal;
      _policyStartDate = policyStart;
      _members = parsedMembers;
      _isLoading = false;
    });
    _fadeCtrl.forward();
    _slideCtrl.forward();
  }

  // ─── Helpers ──────────────────────────────────────────────

  bool get _planExpired {
    final r = _renewalDate;
    if (r == null) return false;
    final now = DateTime.now();
    return r.isBefore(DateTime(now.year, now.month, now.day));
  }

  // Safely grab last N chars of a string. Returns the whole string if shorter.
  String _safeLastChars(String? s, int n) {
    if (s == null || s.isEmpty) return '';
    if (s.length <= n) return s;
    return s.substring(s.length - n);
  }

  // Next billing date = same day next month. Handles month-end edge cases.
  String _nextBillingDate() {
    final now = DateTime.now();
    // Clamp day to last day of target month if needed (e.g., Jan 31 → Feb 28)
    final targetYear = now.month == 12 ? now.year + 1 : now.year;
    final targetMonth = now.month == 12 ? 1 : now.month + 1;
    final lastDayOfTarget = DateTime(targetYear, targetMonth + 1, 0).day;
    final clampedDay = now.day > lastDayOfTarget ? lastDayOfTarget : now.day;
    return DateFormat('MMM d, yyyy')
        .format(DateTime(targetYear, targetMonth, clampedDay));
  }

  // Wrap anything in a glass card. Tune weight via bgOpacity + borderWidth.
  Widget _glassCard({
    required Widget child,
    double bgOpacity = 0.08,
    double borderOpacity = 0.15,
    double borderWidth = 1.2,
    EdgeInsetsGeometry? padding,
    double borderRadius = 20,
    double blur = 16,
    List<BoxShadow>? shadow,
  }) {
    // Painted glass: six live blurs stacked in one scroll view over an
    // opaque navy gradient cost GPU for no visible gain.
    return ClipRRect(
      borderRadius: BorderRadius.circular(borderRadius),
      child: RepaintBoundary(
        child: Container(
          padding: padding ?? const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(bgOpacity + 0.02),
            borderRadius: BorderRadius.circular(borderRadius),
            border: Border.all(
              color: Colors.white.withOpacity(borderOpacity),
              width: borderWidth,
            ),
            boxShadow: shadow ??
                [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.18),
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

  // Section title — 18/w800/-0.3 letterspacing, matches home dashboard
  Widget _sectionHeader(IconData icon, String label, {Color? accent}) {
    final c = accent ?? _joviCoral;
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Row(
        children: [
          Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              color: c.withOpacity(0.14),
              borderRadius: BorderRadius.circular(9),
              border: Border.all(color: c.withOpacity(0.28), width: 1),
            ),
            child: Icon(icon, color: c, size: 17),
          ),
          const SizedBox(width: 10),
          Text(
            label,
            style: const TextStyle(
              fontSize: 17,
              fontWeight: FontWeight.w600,
              color: Colors.white,
              letterSpacing: -0.4,
            ),
          ),
        ],
      ),
    );
  }

  // Label/value row — used repeatedly in the billing/health cards
  Widget _infoRow(String label, String? value, {Widget? trailing}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Flexible(
            child: Text(
              label,
              style: TextStyle(
                fontSize: 13.5,
                color: Colors.white.withOpacity(0.6),
                fontWeight: FontWeight.w500,
                letterSpacing: -0.1,
              ),
            ),
          ),
          const SizedBox(width: 12),
          trailing ??
              Flexible(
                child: Text(
                  value ?? '—',
                  textAlign: TextAlign.right,
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    color: Colors.white,
                    letterSpacing: -0.2,
                  ),
                ),
              ),
        ],
      ),
    );
  }

  // Pill chip (used for Active status + stat boxes)
  Widget _pill({
    required String text,
    required Color bgColor,
    required Color textColor,
    IconData? leadingIcon,
    double iconSize = 14,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 6),
      decoration: BoxDecoration(
        color: bgColor.withOpacity(0.16),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: bgColor.withOpacity(0.32), width: 0.8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (leadingIcon != null) ...[
            Icon(leadingIcon, size: iconSize, color: textColor),
            const SizedBox(width: 5),
          ],
          Text(
            text,
            style: TextStyle(
              color: textColor,
              fontSize: 12.5,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.2,
            ),
          ),
        ],
      ),
    );
  }

  // =================================================================
  // BUILD METHOD
  // =================================================================
  @override
  Widget build(BuildContext context) {
    final screenW = MediaQuery.of(context).size.width;
    final isWide = screenW >= 900;
    final maxContentWidth = isWide ? 1100.0 : double.infinity;
    final horizontalPad = screenW < 360 ? 16.0 : 20.0;

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        statusBarBrightness: Brightness.dark,
      ),
      child: Scaffold(
        backgroundColor: _joviNavy,
        body: Container(
          width: widget.width,
          height: widget.height,
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [_joviNavy, _joviNavyDark],
            ),
          ),
          child: SafeArea(
            child: _isLoading
                ? Center(
                    child: CircularProgressIndicator(
                      strokeWidth: 2.6,
                      valueColor: AlwaysStoppedAnimation<Color>(_joviCoral),
                    ),
                  )
                : FadeTransition(
                    opacity: _fadeAnim,
                    child: SlideTransition(
                      position: _slideAnim,
                      child: Center(
                        child: ConstrainedBox(
                          constraints: BoxConstraints(
                            maxWidth: maxContentWidth == double.infinity
                                ? screenW
                                : maxContentWidth,
                          ),
                          child: CustomScrollView(
                            physics: const BouncingScrollPhysics(
                              parent: AlwaysScrollableScrollPhysics(),
                            ),
                            slivers: [
                              SliverToBoxAdapter(
                                child: Padding(
                                  padding: EdgeInsets.fromLTRB(
                                      horizontalPad, 12, horizontalPad, 20),
                                  child: _buildHeaderStrip(),
                                ),
                              ),
                              SliverToBoxAdapter(
                                child: Padding(
                                  padding: EdgeInsets.fromLTRB(
                                      horizontalPad, 0, horizontalPad, 40),
                                  child: _buildContent(isWide),
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

  // =================================================================
  // HEADER STRIP
  // Thin glass back button, centered title, invisible spacer for balance.
  // =================================================================
  Widget _buildHeaderStrip() {
    return Row(
      children: [
        _Pressable(
            feedbackOnly: true,
            pressedScale: 0.92,
            child: Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: () {
              HapticFeedback.lightImpact();
              if (Navigator.of(context).canPop()) {
                Navigator.of(context).pop();
              } else {
                context.pushReplacement('/dashboard');
              }
            },
            borderRadius: BorderRadius.circular(14),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(14),
              child: RepaintBoundary(
                child: Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.08),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: Colors.white.withOpacity(0.18),
                      width: 1,
                    ),
                  ),
                  child: const Icon(
                    Icons.arrow_back_ios_new,
                    color: Colors.white,
                    size: 16,
                  ),
                ),
              ),
            ),
          ),
        )),
        Expanded(
          child: Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text(
                  'Plan Details',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 17,
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.4,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  _userData?['onboard_fullName'] as String? ??
                      '${_userData?['first'] ?? ''} ${_userData?['last'] ?? ''}'
                          .trim(),
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.55),
                    fontSize: 11.5,
                    fontWeight: FontWeight.w500,
                    letterSpacing: 0.1,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ),
        // Status pill: used to say "Active" unconditionally, even on an
        // expired plan. Now derived from the renewal date.
        _pill(
          text: _planExpired ? 'Expired' : 'Active',
          bgColor: _planExpired ? _joviErrorRed : _joviMint,
          textColor: _planExpired ? _joviErrorRed : _joviMintDark,
          leadingIcon: Icons.circle,
          iconSize: 8,
        ),
      ],
    );
  }

  // =================================================================
  // CONTENT LAYOUT (responsive)
  // =================================================================
  Widget _buildContent(bool isWide) {
    if (isWide) {
      // Two-column on tablet/desktop
      return Column(
        children: [
          _buildPlanSummaryCard(),
          const SizedBox(height: 16),
          _buildRenewalCard(),
          const SizedBox(height: 20),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  children: [
                    _buildMembersCard(),
                    const SizedBox(height: 20),
                    _buildBillingCard(),
                    const SizedBox(height: 20),
                    _buildManageMembershipCard(),
                  ],
                ),
              ),
              const SizedBox(width: 20),
              Expanded(
                child: Column(
                  children: [
                    _buildCoverageCard(),
                    const SizedBox(height: 20),
                    _buildHealthProfileCard(),
                  ],
                ),
              ),
            ],
          ),
        ],
      );
    }
    // Single column
    return Column(
      children: [
        _buildPlanSummaryCard(),
        const SizedBox(height: 14),
        _buildRenewalCard(),
        const SizedBox(height: 20),
        _buildMembersCard(),
        const SizedBox(height: 20),
        _buildCoverageCard(),
        const SizedBox(height: 20),
        _buildBillingCard(),
        const SizedBox(height: 20),
        _buildHealthProfileCard(),
        const SizedBox(height: 20),
        _buildManageMembershipCard(),
      ],
    );
  }

  // =================================================================
  // HERO: PLAN SUMMARY CARD
  // Big card at top: plan name, monthly premium, 3-up stat row.
  // =================================================================
  Widget _buildPlanSummaryCard() {
    final planType = _userData?['planType'] as String? ?? 'Standard Plan';

    // Total premium (defensive number parsing)
    double totalPremium = 0.0;
    final rawPremium = _userData?['totalPremium'] ?? _userData?['premium'];
    if (rawPremium is num) {
      totalPremium = rawPremium.toDouble();
    } else if (rawPremium is String) {
      totalPremium = double.tryParse(rawPremium) ?? 0.0;
    }

    final memberCount = _members.length;
    final firstMemberDeductible = _members.isNotEmpty
        ? ((_members[0]['deductible'] as num?)?.toInt() ??
            (_userData?['deductible'] as num?)?.toInt() ??
            0)
        : ((_userData?['deductible'] as num?)?.toInt() ?? 0);

    // Member ID — try user doc then first member, show last 5
    String? fullMemberId;
    if (_userData?['memberId'] is String) {
      fullMemberId = _userData!['memberId'] as String;
    } else if (_members.isNotEmpty && _members[0]['memberId'] is String) {
      fullMemberId = _members[0]['memberId'] as String;
    }
    final shortMemberId = _safeLastChars(fullMemberId, 5);

    return _glassCard(
      bgOpacity: 0.09,
      borderOpacity: 0.18,
      borderWidth: 1.5,
      padding: const EdgeInsets.all(22),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Top row: plan name + monthly premium
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Your plan',
                      style: TextStyle(
                        fontSize: 12,
                        color: Colors.white.withOpacity(0.55),
                        fontWeight: FontWeight.w600,
                        letterSpacing: 0.3,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      planType,
                      style: const TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.w800,
                        color: Colors.white,
                        letterSpacing: -0.5,
                        height: 1.15,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 16),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  ShaderMask(
                    shaderCallback: (bounds) => const LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [_joviCoral, _joviCoralLight],
                    ).createShader(bounds),
                    child: Text(
                      '\$${totalPremium.toStringAsFixed(2)}',
                      style: const TextStyle(
                        fontSize: 26,
                        fontWeight: FontWeight.w900,
                        color: Colors.white,
                        letterSpacing: -0.6,
                      ),
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    'per month',
                    style: TextStyle(
                      fontSize: 11.5,
                      color: Colors.white.withOpacity(0.5),
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 20),
          // Divider
          Container(
            height: 1,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  Colors.transparent,
                  _joviCoral.withOpacity(0.12),
                  Colors.transparent,
                ],
              ),
            ),
          ),
          const SizedBox(height: 18),
          // 3-up stat row
          Row(
            children: [
              Expanded(
                child: _buildStatColumn(
                  icon: Icons.people_outline_rounded,
                  value: memberCount.toString(),
                  label: memberCount == 1 ? 'Member' : 'Members',
                ),
              ),
              _statDivider(),
              Expanded(
                child: _buildStatColumn(
                  icon: Icons.receipt_long_outlined,
                  value: '\$$firstMemberDeductible',
                  label: 'Deductible',
                ),
              ),
              _statDivider(),
              Expanded(
                child: _buildStatColumn(
                  icon: Icons.badge_outlined,
                  value: shortMemberId.isNotEmpty ? shortMemberId : '—',
                  label: 'Member ID',
                  copyable: fullMemberId,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _statDivider() {
    return Container(
      width: 1,
      height: 42,
      margin: const EdgeInsets.symmetric(horizontal: 4),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Colors.transparent,
            Colors.white.withOpacity(0.12),
            Colors.transparent,
          ],
        ),
      ),
    );
  }

  Widget _buildStatColumn({
    required IconData icon,
    required String value,
    required String label,
    String? copyable,
  }) {
    final content = Column(
      children: [
        Icon(icon, color: _joviCoral, size: 18),
        const SizedBox(height: 6),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          mainAxisSize: MainAxisSize.min,
          children: [
            Flexible(
              child: Text(
                value,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: 15.5,
                  fontWeight: FontWeight.w800,
                  color: Colors.white,
                  letterSpacing: -0.3,
                  fontFamily: copyable != null ? 'monospace' : null,
                ),
              ),
            ),
            if (copyable != null) ...[
              const SizedBox(width: 4),
              Icon(
                Icons.copy,
                size: 12,
                color: Colors.white.withOpacity(0.35),
              ),
            ],
          ],
        ),
        const SizedBox(height: 2),
        Text(
          label,
          style: TextStyle(
            fontSize: 10.5,
            color: Colors.white.withOpacity(0.5),
            fontWeight: FontWeight.w500,
            letterSpacing: 0.3,
          ),
        ),
      ],
    );

    if (copyable == null || copyable.isEmpty) return content;
    return _Pressable(
        feedbackOnly: true,
        pressedScale: 0.95,
        child: InkWell(
      onTap: () {
        HapticFeedback.lightImpact();
        Clipboard.setData(ClipboardData(text: copyable));
        if (!mounted) return;
        ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast('Member ID copied',
        accent: _joviMintDark, icon: CupertinoIcons.checkmark_circle, duration: const Duration(seconds: 2)));
      },
      borderRadius: BorderRadius.circular(8),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: content,
      ),
    ));
  }

  // =================================================================
  // RENEWAL CARD
  // Color-coded by days-until-renewal. Expired=red, ≤7d=coral,
  // ≤30d=gold, else=mint. CTA button only when ≤30 days.
  // =================================================================
  Widget _buildRenewalCard() {
    if (_renewalDate == null) return const SizedBox.shrink();
    final now = DateTime.now();
    final daysUntil = _renewalDate!.difference(now).inDays;

    Color accent;
    Color accentDark;
    String statusText;
    String subText;
    IconData icon;
    bool showRenewCta;

    if (daysUntil < 0) {
      accent = _joviErrorRed;
      accentDark = _joviErrorRed;
      statusText = 'Expired ${-daysUntil} day${-daysUntil == 1 ? "" : "s"} ago';
      subText = 'Renew immediately to restore coverage';
      icon = Icons.error_outline_rounded;
      showRenewCta = true;
    } else if (daysUntil == 0) {
      accent = _joviErrorRed;
      accentDark = _joviErrorRed;
      statusText = 'Expires today';
      subText = 'Renew now to avoid a coverage gap';
      icon = Icons.warning_amber_rounded;
      showRenewCta = true;
    } else if (daysUntil <= 7) {
      accent = _joviCoral;
      accentDark = _joviCoralDark;
      statusText = 'Renews in $daysUntil day${daysUntil == 1 ? "" : "s"}';
      subText = DateFormat('MMMM d, yyyy').format(_renewalDate!);
      icon = Icons.access_time_rounded;
      showRenewCta = true;
    } else if (daysUntil <= 30) {
      accent = _joviGold;
      accentDark = _joviGoldDark;
      statusText = 'Renews in $daysUntil days';
      subText = DateFormat('MMMM d, yyyy').format(_renewalDate!);
      icon = Icons.schedule_rounded;
      showRenewCta = true;
    } else {
      accent = _joviMint;
      accentDark = _joviMintDark;
      statusText = 'Active';
      subText = 'Renews ${DateFormat('MMM d, yyyy').format(_renewalDate!)}'
          ' · $daysUntil days';
      icon = Icons.verified_rounded;
      showRenewCta = false;
    }

    return _glassCard(
      bgOpacity: 0.06,
      borderOpacity: 0.12,
      borderWidth: 1,
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          // Accent color bar on the left
          Container(
            width: 4,
            height: 42,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [accent, accentDark],
              ),
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(width: 14),
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              color: accent.withOpacity(0.14),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: accent.withOpacity(0.3), width: 0.8),
            ),
            child: Icon(icon, color: accent, size: 19),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  statusText,
                  style: TextStyle(
                    fontSize: 14.5,
                    fontWeight: FontWeight.w800,
                    color: accent,
                    letterSpacing: -0.2,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  subText,
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.white.withOpacity(0.55),
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
          if (showRenewCta) ...[
            const SizedBox(width: 10),
            _Pressable(
                feedbackOnly: true,
                pressedScale: 0.94,
                child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: () {
                  HapticFeedback.lightImpact();
                  context.push('/updateProfile');
                },
                borderRadius: BorderRadius.circular(12),
                child: Container(
                  constraints: const BoxConstraints(minHeight: 40),
                  padding:
                      const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [accent, accentDark],
                    ),
                    borderRadius: BorderRadius.circular(12),
                    boxShadow: [
                      BoxShadow(
                        color: accent.withOpacity(0.3),
                        blurRadius: 10,
                        offset: const Offset(0, 4),
                      ),
                    ],
                  ),
                  child: const Text(
                    'Renew',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      letterSpacing: -0.2,
                    ),
                  ),
                ),
              ),
            )),
          ],
        ],
      ),
    );
  }

  // =================================================================
  // COVERED MEMBERS CARD
  // Glass card listing each member. Primary gets coral accent.
  // =================================================================
  Widget _buildMembersCard() {
    if (_members.isEmpty) {
      return _glassCard(
        bgOpacity: 0.05,
        borderOpacity: 0.12,
        borderWidth: 1,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _sectionHeader(Icons.people_alt_outlined, 'Covered Members'),
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 14),
              child: Text(
                'No members on file yet.',
                style: TextStyle(
                  fontSize: 13,
                  color: Colors.white.withOpacity(0.5),
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          ],
        ),
      );
    }

    return _glassCard(
      bgOpacity: 0.05,
      borderOpacity: 0.12,
      borderWidth: 1,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _sectionHeader(Icons.people_alt_outlined, 'Covered Members'),
          ..._members.asMap().entries.map((e) {
            final isLast = e.key == _members.length - 1;
            return Padding(
              padding: EdgeInsets.only(bottom: isLast ? 0 : 10),
              child: _buildMemberRow(e.value),
            );
          }),
        ],
      ),
    );
  }

  Widget _buildMemberRow(Map<String, dynamic> member) {
    final name = member['name'] as String? ?? 'Member';
    final isPrimary = name.toLowerCase() == 'primary';
    final photoUrl = member['photo_url'] as String? ?? '';
    final age = member['age'];
    final ageStr = age == null ? '' : '$age';
    final rawPremium = member['premium'];
    String premiumStr = '';
    if (rawPremium is num) {
      premiumStr = '\$${rawPremium.toStringAsFixed(2)}';
    } else if (rawPremium is String && rawPremium.isNotEmpty) {
      premiumStr = '\$$rawPremium';
    }
    final ded = member['deductible'];
    final dedStr = ded is num ? '\$${ded.toInt()}' : (ded?.toString() ?? '—');

    final accent = isPrimary ? _joviCoral : Colors.white.withOpacity(0.35);

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(isPrimary ? 0.06 : 0.04),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: isPrimary
              ? _joviCoral.withOpacity(0.3)
              : Colors.white.withOpacity(0.08),
          width: 1,
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: accent, width: 1.5),
              color: Colors.white.withOpacity(0.05),
            ),
            child: photoUrl.isNotEmpty
                ? ClipOval(
                    child: CachedNetworkImage(
                      imageUrl: photoUrl,
                      key: ValueKey('member_${photoUrl.hashCode}'),
                      width: 42,
                      height: 42,
                      fit: BoxFit.cover,
                      placeholder: (c, u) => Center(
                        child: Icon(
                          Icons.person,
                          size: 20,
                          color: Colors.white.withOpacity(0.3),
                        ),
                      ),
                      errorWidget: (c, u, e) => Center(
                        child: Icon(
                          Icons.person,
                          size: 20,
                          color: Colors.white.withOpacity(0.3),
                        ),
                      ),
                    ),
                  )
                : Center(
                    child: Icon(
                      Icons.person,
                      size: 20,
                      color: Colors.white.withOpacity(0.4),
                    ),
                  ),
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
                        name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 14.5,
                          fontWeight: FontWeight.w800,
                          color: Colors.white,
                          letterSpacing: -0.2,
                        ),
                      ),
                    ),
                    if (isPrimary) ...[
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [_joviCoral, _joviCoralDark],
                          ),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: const Text(
                          'Primary',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            letterSpacing: -0.1,
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
                const SizedBox(height: 3),
                Text(
                  [
                    if (ageStr.isNotEmpty) 'Age $ageStr',
                    if (premiumStr.isNotEmpty) '$premiumStr / mo',
                  ].join(' · '),
                  style: TextStyle(
                    fontSize: 11.5,
                    color: Colors.white.withOpacity(0.5),
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                'Deductible',
                style: TextStyle(
                  fontSize: 9.5,
                  color: Colors.white.withOpacity(0.45),
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.4,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                dedStr,
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w800,
                  color: Colors.white,
                  letterSpacing: -0.2,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // =================================================================
  // COVERAGE DETAILS CARD
  // =================================================================
  Widget _buildCoverageCard() {
    final tobacco = _userData?['tobacco'] == true;
    final dental = _userData?['dental'] == true;
    final vision = _userData?['vision'] == true;

    return _glassCard(
      bgOpacity: 0.05,
      borderOpacity: 0.12,
      borderWidth: 1,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _sectionHeader(Icons.verified_user_outlined, 'Coverage Details'),
          _buildCoverageRow(
            icon: Icons.medical_services_outlined,
            title: 'Medical Coverage',
            subtitle: 'Comprehensive health coverage',
            accent: _joviMint,
          ),
          const SizedBox(height: 10),
          if (dental) ...[
            _buildCoverageRow(
              icon: Icons.sentiment_satisfied_outlined,
              title: 'Dental Coverage',
              subtitle: 'Preventive and restorative care',
              accent: _joviMint,
            ),
            const SizedBox(height: 10),
          ],
          if (vision) ...[
            _buildCoverageRow(
              icon: Icons.visibility_outlined,
              title: 'Vision Coverage',
              subtitle: 'Eye exams and corrective lenses',
              accent: _joviMint,
            ),
            const SizedBox(height: 10),
          ],
          // Upgrade CTA when user is missing dental or vision
          if (!dental || !vision) ...[
            const SizedBox(height: 4),
            _Pressable(
                feedbackOnly: true,
                pressedScale: 0.985,
                child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: () {
                  HapticFeedback.lightImpact();
                  context.push('/updateProfile');
                },
                borderRadius: BorderRadius.circular(14),
                child: Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [
                        _joviCoral.withOpacity(0.14),
                        _joviCoralLight.withOpacity(0.05),
                      ],
                    ),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: _joviCoral.withOpacity(0.35),
                      width: 1,
                    ),
                  ),
                  child: Row(
                    children: [
                      Container(
                        width: 38,
                        height: 38,
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [_joviCoral, _joviCoralDark],
                          ),
                          borderRadius: BorderRadius.circular(10),
                          boxShadow: [
                            BoxShadow(
                              color: _joviCoral.withOpacity(0.35),
                              blurRadius: 8,
                              offset: const Offset(0, 3),
                            ),
                          ],
                        ),
                        child: const Icon(
                          Icons.auto_awesome_rounded,
                          color: Colors.white,
                          size: 18,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'Enhance your coverage',
                              style: TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.w800,
                                color: Colors.white,
                                letterSpacing: -0.2,
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              !dental && !vision
                                  ? 'Add dental & vision for complete care'
                                  : !dental
                                      ? 'Add dental coverage to your plan'
                                      : 'Add vision coverage to your plan',
                              style: TextStyle(
                                fontSize: 11.5,
                                color: Colors.white.withOpacity(0.6),
                                fontWeight: FontWeight.w500,
                                height: 1.3,
                              ),
                            ),
                          ],
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: const [
                            Icon(Icons.add_rounded,
                                color: Colors.white, size: 14),
                            SizedBox(width: 2),
                            Text(
                              'Add',
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 12,
                                fontWeight: FontWeight.w700,
                                letterSpacing: -0.1,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            )),
          ],
          // Tobacco use declaration callout (if applicable)
          if (tobacco) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: _joviGold.withOpacity(0.1),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: _joviGold.withOpacity(0.3)),
              ),
              child: Row(
                children: [
                  Icon(Icons.info_outline, color: _joviGold, size: 18),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'Tobacco or marijuana use declared. Premium adjusted.',
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.8),
                        fontSize: 11.5,
                        fontWeight: FontWeight.w600,
                        height: 1.35,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildCoverageRow({
    required IconData icon,
    required String title,
    required String subtitle,
    required Color accent,
  }) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.04),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withOpacity(0.08)),
      ),
      child: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: accent.withOpacity(0.15),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: accent.withOpacity(0.3), width: 0.8),
            ),
            child: Icon(icon, color: accent, size: 18),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    color: Colors.white,
                    letterSpacing: -0.2,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  subtitle,
                  style: TextStyle(
                    fontSize: 11.5,
                    color: Colors.white.withOpacity(0.5),
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
          Icon(
            Icons.check_circle_rounded,
            color: accent,
            size: 20,
          ),
        ],
      ),
    );
  }

  // =================================================================
  // BILLING INFO CARD
  // =================================================================
  Widget _buildBillingCard() {
    final paymentProcessed = _userData?['paymentProcessed'] == true;
    final paymentCard = _userData?['paymentCard'] as String?;
    final last4 = _safeLastChars(paymentCard, 4);
    final last4Display = last4.isEmpty ? '••••' : last4;

    return _glassCard(
      bgOpacity: 0.05,
      borderOpacity: 0.12,
      borderWidth: 1,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _sectionHeader(Icons.credit_card_outlined, 'Billing Information'),
          _infoRow(
            'Payment method',
            null,
            trailing: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.credit_card,
                    color: _joviCoral.withOpacity(0.85), size: 16),
                const SizedBox(width: 6),
                Text(
                  '•••• $last4Display',
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    color: Colors.white,
                    fontFamily: 'monospace',
                    letterSpacing: 0.3,
                  ),
                ),
              ],
            ),
          ),
          _infoRow('Billing cycle', 'Monthly auto-pay'),
          // NOTE: this is "same day next month" from today, not a value
          // from the billing system. Replace once Zoho Payments is wired.
          _infoRow('Next billing date', _nextBillingDate()),
          if (_renewalDate != null)
            _infoRow(
              'Renewal date',
              DateFormat('MMM d, yyyy').format(_renewalDate!),
            ),
          if (paymentProcessed) ...[
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: _joviMint.withOpacity(0.12),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(
                  color: _joviMint.withOpacity(0.3),
                  width: 0.8,
                ),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.check_circle_rounded,
                      color: _joviMintDark, size: 14),
                  const SizedBox(width: 6),
                  Text(
                    'Auto-pay active',
                    style: TextStyle(
                      color: _joviMintDark,
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0.2,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  // =================================================================
  // MANAGE MEMBERSHIP CARD
  // Self-serve cancel backed by the `cancelMembership` Cloud Function
  // (schedules the end of coverage at the next billing date; nothing is
  // charged or refunded here). "Keep" reverses a pending cancellation by
  // clearing the flags the function set. Pausing is not supported by the
  // backend, so it is not offered.
  // =================================================================
  Widget _buildManageMembershipCard() {
    final status = (_subscriptionStatus ?? '').toLowerCase();
    final canceling = status == 'canceling';
    final canceled = status == 'canceled' || status == 'cancelled';
    final endText = _willCancelOn != null
        ? DateFormat('MMMM d, yyyy').format(_willCancelOn!)
        : null;

    String statusLabel;
    Color statusColor;
    if (canceled) {
      statusLabel = 'Canceled';
      statusColor = _joviErrorRed;
    } else if (canceling) {
      statusLabel = endText == null ? 'Ending soon' : 'Ends $endText';
      statusColor = _joviGold;
    } else {
      statusLabel = 'Active';
      statusColor = _joviMint;
    }

    return _glassCard(
      bgOpacity: 0.05,
      borderOpacity: 0.12,
      borderWidth: 1,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _sectionHeader(Icons.manage_accounts_outlined, 'Manage Membership'),
          _infoRow(
            'Status',
            null,
            trailing: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: statusColor,
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(color: statusColor.withOpacity(0.6), blurRadius: 6),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  statusLabel,
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    color: statusColor,
                    letterSpacing: -0.2,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          if (canceling) ...[
            Text(
              endText == null
                  ? 'Your membership is scheduled to end. Coverage continues until then, and you can change your mind any time before it does.'
                  : 'Coverage continues until $endText. Change your mind any time before then.',
              style: TextStyle(
                color: Colors.white.withOpacity(0.7),
                fontSize: 13,
                fontWeight: FontWeight.w500,
                height: 1.45,
              ),
            ),
            const SizedBox(height: 14),
            _membershipButton(
              label: 'Keep My Membership',
              icon: CupertinoIcons.arrow_uturn_left,
              primary: true,
              onTap: _membershipBusy ? null : _keepMembership,
            ),
          ] else if (canceled) ...[
            Text(
              'This membership has ended. Reach out to support if you would like to rejoin.',
              style: TextStyle(
                color: Colors.white.withOpacity(0.7),
                fontSize: 13,
                fontWeight: FontWeight.w500,
                height: 1.45,
              ),
            ),
          ] else ...[
            Text(
              'Cancelling ends coverage at the close of your current billing period. Nothing is charged after that.',
              style: TextStyle(
                color: Colors.white.withOpacity(0.6),
                fontSize: 12.5,
                fontWeight: FontWeight.w500,
                height: 1.45,
              ),
            ),
            const SizedBox(height: 12),
            _membershipButton(
              label: 'Cancel Membership',
              icon: CupertinoIcons.xmark_circle,
              primary: false,
              destructive: true,
              onTap: _membershipBusy ? null : _startCancelFlow,
            ),
          ],
          if (_membershipBusy) ...[
            const SizedBox(height: 12),
            const Center(
              child: SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  valueColor: AlwaysStoppedAnimation<Color>(_joviCoral),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _membershipButton({
    required String label,
    required IconData icon,
    required bool primary,
    bool destructive = false,
    VoidCallback? onTap,
  }) {
    final enabled = onTap != null;
    final fg = destructive
        ? _joviErrorRed
        : primary
            ? Colors.white
            : Colors.white;
    return _Pressable(
      feedbackOnly: true,
      enabled: enabled,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: enabled
              ? () {
                  HapticFeedback.lightImpact();
                  onTap();
                }
              : null,
          borderRadius: BorderRadius.circular(13),
          child: Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(vertical: 13),
            decoration: BoxDecoration(
              gradient: primary
                  ? const LinearGradient(colors: [_joviCoral, _joviCoralDark])
                  : null,
              color: primary
                  ? null
                  : (destructive
                      ? _joviErrorRed.withOpacity(0.1)
                      : Colors.white.withOpacity(0.06)),
              borderRadius: BorderRadius.circular(13),
              border: primary
                  ? null
                  : Border.all(
                      color: destructive
                          ? _joviErrorRed.withOpacity(0.35)
                          : Colors.white.withOpacity(0.18),
                      width: 1,
                    ),
            ),
            child: Opacity(
              opacity: enabled ? 1 : 0.5,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(icon, color: fg, size: 17),
                  const SizedBox(width: 7),
                  Text(
                    label,
                    style: TextStyle(
                      color: fg,
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                      letterSpacing: -0.2,
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

  static const List<String> _cancelReasons = [
    'Too expensive',
    'Not using it enough',
    'Found other coverage',
    'Missing something I need',
    'Other',
  ];

  Future<void> _startCancelFlow() async {
    HapticFeedback.mediumImpact();
    final reason = await showCupertinoModalPopup<String>(
      context: context,
      builder: (ctx) => CupertinoActionSheet(
        title: const Text('Why are you cancelling?'),
        message: const Text('This helps us improve Jovi. Optional.'),
        actions: [
          for (final r in _cancelReasons)
            CupertinoActionSheetAction(
              onPressed: () => Navigator.pop(ctx, r),
              child: Text(r),
            ),
        ],
        cancelButton: CupertinoActionSheetAction(
          isDefaultAction: true,
          onPressed: () => Navigator.pop(ctx),
          child: const Text('Never Mind'),
        ),
      ),
    );
    if (reason == null || !mounted) return;

    final ok = await showCupertinoDialog<bool>(
      context: context,
      builder: (ctx) => CupertinoAlertDialog(
        title: const Text('Cancel Membership?'),
        content: const Padding(
          padding: EdgeInsets.only(top: 8),
          child: Text(
              'Your coverage stays active until the end of your current billing period. After that, care requests, claims and pet coverage stop. You can keep your membership any time before then.'),
        ),
        actions: [
          CupertinoDialogAction(
            isDefaultAction: true,
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Keep Membership'),
          ),
          CupertinoDialogAction(
            isDestructiveAction: true,
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Cancel Membership'),
          ),
        ],
      ),
    );
    if (ok != true || !mounted) return;

    setState(() => _membershipBusy = true);
    try {
      final callable =
          FirebaseFunctions.instance.httpsCallable('cancelMembership');
      final res = await callable.call(<String, dynamic>{
        'reason': reason,
        'immediately': false,
      });
      final data = res.data;
      final msg = data is Map && data['message'] is String
          ? data['message'] as String
          : 'Your membership is scheduled to end at the close of this billing period.';
      if (!mounted) return;
      HapticFeedback.mediumImpact();
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(msg,
          accent: _joviGold,
          icon: CupertinoIcons.info_circle,
          duration: const Duration(seconds: 5)));
    } on FirebaseFunctionsException catch (e) {
      debugPrint('PlanDetails: cancelMembership failed: ${e.code} ${e.message}');
      if (!mounted) return;
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(
          e.message ?? 'Could not cancel right now. Please try again or contact support.',
          accent: _joviErrorRed,
          icon: CupertinoIcons.exclamationmark_circle));
    } catch (e) {
      debugPrint('PlanDetails: cancelMembership error: $e');
      if (!mounted) return;
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(
          'Could not cancel right now. Please try again or contact support.',
          accent: _joviErrorRed,
          icon: CupertinoIcons.exclamationmark_circle));
    } finally {
      if (mounted) setState(() => _membershipBusy = false);
    }
  }

  Future<void> _keepMembership() async {
    final uid = FirebaseAuth.instance.currentUser?.uid;
    if (uid == null) return;
    HapticFeedback.mediumImpact();
    setState(() => _membershipBusy = true);
    try {
      // Reverses exactly what cancelMembership wrote. The profile stream
      // picks up the change and the card flips back to Active.
      await FirebaseFirestore.instance.collection('users').doc(uid).update({
        'subscriptionStatus': 'active',
        'membershipStatus': 'active',
        'willCancelOn': FieldValue.delete(),
        'finalBillingDate': FieldValue.delete(),
        'canceledAt': FieldValue.delete(),
        'cancelReason': FieldValue.delete(),
        'cancellationReversedAt': FieldValue.serverTimestamp(),
      });
      if (!mounted) return;
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(
          'Welcome back. Your membership will renew as usual.',
          accent: _joviMint,
          icon: CupertinoIcons.checkmark_circle));
    } catch (e) {
      debugPrint('PlanDetails: keepMembership failed: $e');
      if (!mounted) return;
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(
          'Could not update your membership. Please try again.',
          accent: _joviErrorRed,
          icon: CupertinoIcons.exclamationmark_circle));
    } finally {
      if (mounted) setState(() => _membershipBusy = false);
    }
  }

  // =================================================================
  // HEALTH PROFILE CARD
  // Only renders if we have at least one onboard field.
  // =================================================================
  Widget _buildHealthProfileCard() {
    final d = _userData ?? {};
    final fields = <_ProfileField>[
      if ((d['onboard_height'] as String?)?.isNotEmpty == true)
        _ProfileField('Height', d['onboard_height'] as String),
      if (d['onboard_weight'] != null &&
          d['onboard_weight'].toString().isNotEmpty)
        _ProfileField('Weight', '${d['onboard_weight']} lbs'),
      if ((d['onboard_gender'] as String?)?.isNotEmpty == true)
        _ProfileField('Gender', d['onboard_gender'] as String),
      if ((d['onboard_conditions'] as String?)?.isNotEmpty == true)
        _ProfileField('Conditions', d['onboard_conditions'] as String),
      if ((d['onboard_pharmacy'] as String?)?.isNotEmpty == true)
        _ProfileField('Preferred pharmacy', d['onboard_pharmacy'] as String),
      if ((d['onboard_emName'] as String?)?.isNotEmpty == true)
        _ProfileField(
          'Emergency contact',
          '${d['onboard_emName']}'
              '${(d['onboard_emPhone'] as String?)?.isNotEmpty == true ? " · ${d['onboard_emPhone']}" : ""}',
        ),
    ];

    if (fields.isEmpty) return const SizedBox.shrink();

    return _glassCard(
      bgOpacity: 0.05,
      borderOpacity: 0.12,
      borderWidth: 1,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _sectionHeader(Icons.medical_information_outlined, 'Health Profile'),
          ...fields.asMap().entries.map((e) {
            final isLast = e.key == fields.length - 1;
            return Padding(
              padding: EdgeInsets.only(bottom: isLast ? 0 : 10),
              child: _buildProfileFieldRow(e.value),
            );
          }),
        ],
      ),
    );
  }

  Widget _buildProfileFieldRow(_ProfileField f) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 120,
          child: Text(
            f.label,
            style: TextStyle(
              fontSize: 12,
              color: Colors.white.withOpacity(0.5),
              fontWeight: FontWeight.w600,
              letterSpacing: 0.1,
            ),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Text(
            f.value,
            style: const TextStyle(
              fontSize: 13.5,
              fontWeight: FontWeight.w600,
              color: Colors.white,
              letterSpacing: -0.1,
              height: 1.35,
            ),
          ),
        ),
      ],
    );
  }
}

// ─── Internal: health profile field tuple ──────────────────
class _ProfileField {
  final String label;
  final String value;
  const _ProfileField(this.label, this.value);
}
