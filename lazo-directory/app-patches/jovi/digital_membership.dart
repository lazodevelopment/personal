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
// JOVI HEALTH — DIGITAL MEMBERSHIP CARD
// Version: 2026.09.22-r3 (Apple HIG refinement pass)
//
// What changed vs r2:
//  • Press feedback on pointer-down (card + back button), not on release.
//  • Entrance is a short critically-damped fade + rise; no 800 ms fade-in.
//  • Haptic + selection tick on every page change; card-scale/opacity for
//    the peek cards is driven by the live scroll position (interruptible).
//  • Removed BackdropFilter: nothing sits behind a card, so the 20 px blur
//    cost GPU every scroll frame and blurred nothing. Glass is now painted.
//  • Fixed setState() during build (layout re-analysis now happens only in
//    didChangeDependencies). Removed unused GlobalKeys / RepaintBoundaries.
//  • Renewal strip no longer overlaps the Member ID / Valid Thru row.
//  • Dynamic Type: card text scales with the user's setting but is clamped
//    so the fixed-ratio card never overflows.
//  • Reduced motion respected (MediaQuery.disableAnimations).
//  • Size-specific tracking: large name text tightened, small caps labels
//    opened up. Header uses title case at 17 pt semibold (iOS nav title).
//  • Semantics labels for VoiceOver on cards and controls.
// ═══════════════════════════════════════════════════════════════════════════

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'dart:convert';
import 'dart:ui' as ui_dart;
import 'package:intl/intl.dart';
import 'package:flutter/services.dart';
import 'package:flutter/foundation.dart';

enum ScreenType { compact, medium, expanded, large }

class ResponsiveConfig {
  final double paddingH;
  final double paddingV;
  final double contentMax;
  final double cardMaxWidth;
  final bool wideMode;
  final bool hasHinge;
  final bool enableSideBySide;

  const ResponsiveConfig({
    required this.paddingH,
    required this.paddingV,
    required this.contentMax,
    required this.cardMaxWidth,
    required this.wideMode,
    required this.hasHinge,
    required this.enableSideBySide,
  });
}

/// Data model for a card entry — covers both human members and pets
class _CardEntry {
  final String kind; // 'member' or 'pet'
  final String name;
  final String role; // 'Primary' / 'Spouse' / 'Dependent' / 'Pet'
  final String? photoUrl;
  final String memberId;
  // Pet-specific extras (matches onboarding schema field names)
  final String? type; // 'Dog' / 'Cat' / etc
  final String? breed;

  const _CardEntry({
    required this.kind,
    required this.name,
    required this.role,
    required this.memberId,
    this.photoUrl,
    this.type,
    this.breed,
  });

  bool get isPet => kind == 'pet';
}

// ═══════════════════════════════════════════════════════════════════════════
// Motion constants — Apple "response" values, critically damped by default.
// ═══════════════════════════════════════════════════════════════════════════
class _Motion {
  static const Duration pressIn = Duration(milliseconds: 90);
  static const Duration pressOut = Duration(milliseconds: 260);
  static const Duration enter = Duration(milliseconds: 380);
  static const Duration indicator = Duration(milliseconds: 280);
  static const Curve settle = Curves.easeOutCubic; // no overshoot
}

/// Scales down on pointer-down and springs back on up/cancel.
/// Feedback lives on the press — never on the release.
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
    this.pressedScale = 0.975,
    this.reduceMotion = false,
    this.semanticsLabel,
    this.semanticsHint,
  }) : super(key: key);

  @override
  State<_Pressable> createState() => _PressableState();
}

class _PressableState extends State<_Pressable> {
  bool _down = false;

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
        onPointerDown: (_) => _set(true),
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

class DigitalMembershipWidget extends StatefulWidget {
  final double width;
  final double height;

  const DigitalMembershipWidget({
    Key? key,
    required this.width,
    required this.height,
  }) : super(key: key);

  @override
  _DigitalMembershipWidgetState createState() =>
      _DigitalMembershipWidgetState();
}

class _DigitalMembershipWidgetState extends State<DigitalMembershipWidget>
    with SingleTickerProviderStateMixin {
  // ═══════════════════════════════════════════════════════════════
  // Jovi Brand Colors
  // ═══════════════════════════════════════════════════════════════
  static const Color joviCoral = Color(0xFFFF6B4A);
  static const Color joviCoralDark = Color(0xFFE5583A);
  static const Color joviCoralLight = Color(0xFFFF8F73);
  static const Color joviNavy = Color(0xFF1A2744);
  static const Color joviNavyDark = Color(0xFF0F1A2E);
  static const Color joviMint = Color(0xFF00D4AA);
  static const Color joviMintDark = Color(0xFF00B894);
  static const Color joviGold = Color(0xFFFFD166);
  static const Color joviGoldDark = Color(0xFFE6B84D);
  static const Color joviRed = Color(0xFFEF4444);
  static const Color joviRedDark = Color(0xFFDC2626);

  static const String _logoUrl =
      'https://storage.googleapis.com/flutterflow-io-6f20.appspot.com/projects/kurv-health-3vcfmp/assets/gveqn2eoe4nf/jovi_header_logo_master.png';

  static const String _coralIconUrl =
      'https://firebasestorage.googleapis.com/v0/b/kurv-health.firebasestorage.app/o/jovi-profile-instagram.png?alt=media&token=df4c6e5a-cb8f-4a5c-b6e9-f09a17711106';

  late final AnimationController _enterController;
  late final Animation<double> _enterFade;
  late final Animation<Offset> _enterRise;
  late final PageController _pageController;
  int _currentPage = 0;

  ScreenType currentScreenType = ScreenType.compact;
  ResponsiveConfig layoutSettings = const ResponsiveConfig(
    paddingH: 20,
    paddingV: 20,
    contentMax: double.infinity,
    cardMaxWidth: 400,
    wideMode: false,
    hasHinge: false,
    enableSideBySide: false,
  );

  double? _lastScreenWidth;
  bool? _lastHasHinge;
  bool _reduceMotion = false;

  @override
  void initState() {
    super.initState();
    // viewportFraction < 1.0 gives the peek effect — adjacent cards show
    // at the edges, signalling there's more to swipe.
    _pageController = PageController(viewportFraction: 0.85);
    _enterController = AnimationController(
      duration: _Motion.enter,
      vsync: this,
    );
    final curved = CurvedAnimation(
      parent: _enterController,
      curve: _Motion.settle,
    );
    _enterFade = Tween<double>(begin: 0.0, end: 1.0).animate(curved);
    _enterRise = Tween<Offset>(
      begin: const Offset(0, 0.02),
      end: Offset.zero,
    ).animate(curved);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _reduceMotion = MediaQuery.of(context).disableAnimations;
    _analyzeScreenConfiguration();
    if (!_enterController.isCompleted && !_enterController.isAnimating) {
      if (_reduceMotion) {
        _enterController.value = 1.0;
      } else {
        _enterController.forward();
      }
    }
  }

  @override
  void dispose() {
    _enterController.dispose();
    _pageController.dispose();
    super.dispose();
  }

  // ─── Responsive ──────────────────────────────────────────────────────────

  /// Only ever called from didChangeDependencies (which re-runs whenever
  /// MediaQuery changes), so plain assignment is safe — no setState needed
  /// and no risk of setState() during build.
  void _analyzeScreenConfiguration() {
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

    _lastScreenWidth = screenWidth;
    _lastHasHinge = hasHinge;
    currentScreenType = screenType;
    layoutSettings = _generateLayoutConfig(screenType, screenWidth, hasHinge);
  }

  ResponsiveConfig _generateLayoutConfig(
      ScreenType type, double width, bool hasHinge) {
    switch (type) {
      case ScreenType.expanded:
        return ResponsiveConfig(
          paddingH: 16,
          paddingV: 20,
          contentMax: double.infinity,
          cardMaxWidth: width > 900 ? 450 : 400,
          wideMode: true,
          hasHinge: true,
          enableSideBySide: width > 900,
        );
      case ScreenType.large:
        return ResponsiveConfig(
          paddingH: 40,
          paddingV: 28,
          contentMax: 1400,
          cardMaxWidth: 450,
          wideMode: true,
          hasHinge: false,
          enableSideBySide: width > 900,
        );
      case ScreenType.medium:
        return const ResponsiveConfig(
          paddingH: 20,
          paddingV: 24,
          contentMax: double.infinity,
          cardMaxWidth: 400,
          wideMode: true,
          hasHinge: false,
          enableSideBySide: false,
        );
      case ScreenType.compact:
      default:
        return ResponsiveConfig(
          paddingH: 20,
          paddingV: 20,
          contentMax: double.infinity,
          cardMaxWidth: width > 360 ? 350 : 320,
          wideMode: false,
          hasHinge: false,
          enableSideBySide: false,
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

  Map<String, double> _getCardDimensions(
      BuildContext context, bool sideBySide, int memberCount) {
    final screenWidth = MediaQuery.of(context).size.width;
    final screenHeight = MediaQuery.of(context).size.height;

    double cardWidth;
    if (sideBySide && layoutSettings.enableSideBySide && memberCount > 1) {
      cardWidth = screenWidth * 0.42;
      cardWidth = cardWidth > layoutSettings.cardMaxWidth
          ? layoutSettings.cardMaxWidth
          : cardWidth;
    } else {
      if (currentScreenType == ScreenType.large) {
        cardWidth = layoutSettings.cardMaxWidth;
      } else if (currentScreenType == ScreenType.medium) {
        cardWidth = screenWidth > 500
            ? layoutSettings.cardMaxWidth
            : screenWidth * 0.95;
      } else {
        cardWidth = screenWidth * 0.95;
        if (cardWidth > layoutSettings.cardMaxWidth) {
          cardWidth = layoutSettings.cardMaxWidth;
        }
      }
    }

    // ISO 7810 ID-1 credit-card ratio.
    double cardHeight = cardWidth / 1.585;
    final maxHeight = screenHeight * 0.6;
    if (cardHeight > maxHeight) {
      cardHeight = maxHeight;
      cardWidth = cardHeight * 1.585;
    }

    return {'width': cardWidth, 'height': cardHeight};
  }

  // ─── Feedback ────────────────────────────────────────────────────────────

  void _copyToClipboard(String text, String label) {
    Clipboard.setData(ClipboardData(text: text));
    // Haptic and visual fire on the same frame — causality + harmony.
    HapticFeedback.mediumImpact();
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
                '$label copied',
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

  Color _getRoleBadgeColor(String role) {
    switch (role) {
      case 'Primary':
        return joviCoral;
      case 'Spouse':
        return joviCoralLight;
      case 'Dependent':
        return joviMint;
      case 'Pet':
        return joviGold;
      default:
        return Colors.grey;
    }
  }

  // ─── States ──────────────────────────────────────────────────────────────

  Widget _buildErrorState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline_rounded,
                size: currentScreenType == ScreenType.compact ? 56 : 64,
                color: const Color(0xFFFF8A80)),
            const SizedBox(height: 16),
            Text(
              'Couldn’t load your membership',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: currentScreenType == ScreenType.compact ? 20 : 22,
                fontWeight: FontWeight.w600,
                letterSpacing: -0.3,
                color: Colors.white,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              'Check your connection and try again.',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 15,
                color: Colors.white.withOpacity(0.65),
              ),
            ),
            const SizedBox(height: 20),
            _Pressable(
              reduceMotion: _reduceMotion,
              pressedScale: 0.96,
              onTap: () => setState(() {}),
              semanticsLabel: 'Retry',
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 28, vertical: 13),
                decoration: BoxDecoration(
                  color: joviCoral,
                  borderRadius: BorderRadius.circular(14),
                  boxShadow: [
                    BoxShadow(
                      color: joviCoral.withOpacity(0.35),
                      blurRadius: 16,
                      offset: const Offset(0, 6),
                    ),
                  ],
                ),
                child: const Text(
                  'Try Again',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.2,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLoadingState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const SizedBox(
            width: 28,
            height: 28,
            child: CircularProgressIndicator(
              strokeWidth: 2.5,
              valueColor: AlwaysStoppedAnimation<Color>(joviCoral),
            ),
          ),
          const SizedBox(height: 16),
          Text(
            'Loading your cards…',
            style: TextStyle(
              color: Colors.white.withOpacity(0.7),
              fontSize: 15,
              letterSpacing: -0.1,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSignedOutState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.lock_outline_rounded,
              size: currentScreenType == ScreenType.compact ? 56 : 64,
              color: Colors.white.withOpacity(0.4)),
          const SizedBox(height: 16),
          Text(
            'Sign in to view your membership',
            style: TextStyle(
              fontSize: currentScreenType == ScreenType.compact ? 18 : 20,
              fontWeight: FontWeight.w600,
              letterSpacing: -0.3,
              color: Colors.white.withOpacity(0.85),
            ),
          ),
        ],
      ),
    );
  }

  // ─── Card ────────────────────────────────────────────────────────────────

  Widget _buildMembershipCard({
    required _CardEntry entry,
    required String planType,
    required DateTime validThru,
    required int daysLeft,
    required bool isActive,
    required double cardW,
    required double cardH,
  }) {
    final isPet = entry.isPet;
    final primaryColor = isPet ? joviGold : joviCoral;
    final primaryDark = isPet ? joviGoldDark : joviCoralDark;
    final roleBadgeColor = _getRoleBadgeColor(entry.role);

    final rawId = entry.memberId;
    final idSuffix =
        rawId.length > 5 ? rawId.substring(rawId.length - 5) : rawId;
    final displayMemberId = 'JH-${idSuffix.toUpperCase()}';

    final isCompact = currentScreenType == ScreenType.compact || cardW < 350;
    final nameFontSize = isCompact ? 21.0 : 25.0;
    final labelFontSize = isCompact ? 9.5 : 10.5;
    final valueFontSize = isCompact ? 13.0 : 15.0;
    final radius = BorderRadius.circular(isCompact ? 22 : 26);

    final roleBadgeLabel = isPet ? 'PET MEMBER' : entry.role.toUpperCase();
    final showRenewalStrip = isActive && daysLeft <= 30;
    final stripHeight = isCompact ? 26.0 : 28.0;

    final semantics = StringBuffer()
      ..write('${entry.name}, ${isPet ? 'pet member' : entry.role}. ')
      ..write('Member ID $displayMemberId. ')
      ..write('Valid through ${DateFormat('MMMM yyyy').format(validThru)}. ')
      ..write(isActive ? 'Active.' : 'Inactive.');
    if (showRenewalStrip) semantics.write(' Renews in $daysLeft days.');

    // Card is a fixed-ratio surface: let text follow Dynamic Type but cap it
    // so nothing overflows the card.
    final mq = MediaQuery.of(context);
    final clampedTextScaler =
        mq.textScaler.clamp(minScaleFactor: 0.9, maxScaleFactor: 1.15);

    return MediaQuery(
      data: mq.copyWith(textScaler: clampedTextScaler),
      child: _Pressable(
        reduceMotion: _reduceMotion,
        onTap: () => _copyToClipboard(displayMemberId, 'Member ID'),
        semanticsLabel: semantics.toString(),
        semanticsHint: 'Double tap to copy member ID',
        child: Container(
          width: cardW,
          height: cardH,
          margin: const EdgeInsets.symmetric(horizontal: 10),
          decoration: BoxDecoration(
            borderRadius: radius,
            boxShadow: [
              // Accent glow — tinted, sits under the card
              BoxShadow(
                color: primaryColor.withOpacity(0.22),
                blurRadius: 28,
                offset: const Offset(0, 14),
                spreadRadius: -8,
              ),
              // Contact shadow — larger surface reads as thicker
              BoxShadow(
                color: Colors.black.withOpacity(0.45),
                blurRadius: 20,
                offset: const Offset(0, 10),
              ),
            ],
          ),
          child: ClipRRect(
            borderRadius: radius,
            child: Stack(
              children: [
                // ─── Base glass surface (painted, no backdrop blur) ───
                Positioned.fill(
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: isPet
                            ? const [
                                Color(0xFF243150),
                                Color(0xFF131E33),
                                Color(0xFF2A2419),
                              ]
                            : const [
                                Color(0xFF243150),
                                Color(0xFF131E33),
                                Color(0xFF2A1E24),
                              ],
                      ),
                    ),
                  ),
                ),

                // ─── Accent radial glow (top-right) ───────────────────
                Positioned(
                  right: -40,
                  top: -40,
                  child: IgnorePointer(
                    child: Container(
                      width: 190,
                      height: 190,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        gradient: RadialGradient(
                          colors: [
                            primaryColor.withOpacity(0.26),
                            primaryColor.withOpacity(0.0),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),

                // ─── Holographic sheen ────────────────────────────────
                Positioned.fill(
                  child: IgnorePointer(
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          begin: const Alignment(-1.0, -1.0),
                          end: const Alignment(0.2, 0.3),
                          colors: [
                            Colors.white.withOpacity(0.13),
                            Colors.white.withOpacity(0.04),
                            Colors.transparent,
                          ],
                          stops: const [0.0, 0.35, 0.7],
                        ),
                      ),
                    ),
                  ),
                ),

                // ─── Content ──────────────────────────────────────────
                Padding(
                  padding: EdgeInsets.fromLTRB(
                    isCompact ? 16 : 20,
                    isCompact ? 16 : 20,
                    isCompact ? 16 : 20,
                    (isCompact ? 16 : 20) + (showRenewalStrip ? stripHeight : 0),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Top row: icon chip, wordmark, plan; avatar right
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.center,
                        children: [
                          _buildIconChip(
                            isPet: isPet,
                            primaryColor: primaryColor,
                            primaryDark: primaryDark,
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  crossAxisAlignment: CrossAxisAlignment.center,
                                  children: [
                                    Image.network(
                                      _logoUrl,
                                      height: isCompact ? 20 : 22,
                                      fit: BoxFit.contain,
                                      errorBuilder: (c, e, s) => Text(
                                        'jovi',
                                        style: TextStyle(
                                          color: Colors.white,
                                          fontSize: isCompact ? 18 : 20,
                                          fontWeight: FontWeight.w800,
                                          letterSpacing: -0.6,
                                          height: 1.0,
                                        ),
                                      ),
                                    ),
                                    const SizedBox(width: 6),
                                    Text(
                                      'health',
                                      style: TextStyle(
                                        color: primaryColor,
                                        fontSize: isCompact ? 18 : 20,
                                        fontWeight: FontWeight.w300,
                                        letterSpacing: -0.3,
                                        height: 1.0,
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 3),
                                Text(
                                  isPet ? 'PET PLAN' : planType.toUpperCase(),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: TextStyle(
                                    color: Colors.white.withOpacity(0.6),
                                    fontSize: labelFontSize,
                                    fontWeight: FontWeight.w600,
                                    letterSpacing: 1.4,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          _buildProfileAvatar(
                            isPet: isPet,
                            photoUrl: entry.photoUrl,
                            primaryColor: primaryColor,
                          ),
                        ],
                      ),

                      SizedBox(height: isCompact ? 12 : 16),

                      // Role badge
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 5),
                        decoration: BoxDecoration(
                          color: roleBadgeColor.withOpacity(0.16),
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(
                            color: roleBadgeColor.withOpacity(0.4),
                            width: 1,
                          ),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            if (isPet) ...[
                              Icon(Icons.pets, color: roleBadgeColor, size: 11),
                              const SizedBox(width: 5),
                            ],
                            Text(
                              roleBadgeLabel,
                              style: TextStyle(
                                color: roleBadgeColor,
                                fontSize: 10,
                                fontWeight: FontWeight.w700,
                                letterSpacing: 0.9,
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 8),

                      // Name — large text, tight tracking + tight leading
                      Text(
                        entry.name,
                        style: TextStyle(
                          fontSize: nameFontSize,
                          fontWeight: FontWeight.w700,
                          color: Colors.white,
                          letterSpacing: -0.6,
                          height: 1.08,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),

                      // Pet subtext: type • breed
                      if (isPet &&
                          ((entry.type ?? '').isNotEmpty ||
                              (entry.breed ?? '').isNotEmpty))
                        Padding(
                          padding: const EdgeInsets.only(top: 3),
                          child: Text(
                            [
                              (entry.type ?? '').toUpperCase(),
                              (entry.breed ?? '').toUpperCase(),
                            ].where((s) => s.isNotEmpty).join('  •  '),
                            style: TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.w600,
                              color: primaryColor.withOpacity(0.8),
                              letterSpacing: 0.9,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),

                      const Spacer(),

                      // Bottom info row
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Expanded(
                            flex: 5,
                            child: _buildLabelValue(
                              label: 'MEMBER ID',
                              value: displayMemberId,
                              labelSize: labelFontSize,
                              valueSize: valueFontSize,
                              trailing: Icon(
                                Icons.copy_rounded,
                                size: 12,
                                color: Colors.white.withOpacity(0.45),
                              ),
                            ),
                          ),
                          Expanded(
                            flex: 4,
                            child: _buildLabelValue(
                              label: 'VALID THRU',
                              value: DateFormat('MM/yy').format(validThru),
                              labelSize: labelFontSize,
                              valueSize: valueFontSize,
                            ),
                          ),
                          _buildStatusPill(isActive),
                        ],
                      ),
                    ],
                  ),
                ),

                // ─── Renewal strip (reserved space, never overlaps) ───
                if (showRenewalStrip)
                  Positioned(
                    bottom: 0,
                    left: 0,
                    right: 0,
                    child: Container(
                      height: stripHeight,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: daysLeft <= 7
                              ? const [joviRed, joviRedDark]
                              : const [joviGold, joviGoldDark],
                          begin: Alignment.centerLeft,
                          end: Alignment.centerRight,
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.schedule_rounded,
                            size: 13,
                            color: daysLeft <= 7 ? Colors.white : joviNavyDark,
                          ),
                          const SizedBox(width: 6),
                          Text(
                            daysLeft == 1
                                ? 'Renews tomorrow'
                                : daysLeft == 0
                                    ? 'Renews today'
                                    : 'Renews in $daysLeft days',
                            style: TextStyle(
                              color:
                                  daysLeft <= 7 ? Colors.white : joviNavyDark,
                              fontWeight: FontWeight.w700,
                              fontSize: 11.5,
                              letterSpacing: -0.1,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),

                // ─── Rim light (light catching the top edge) ──────────
                Positioned(
                  top: 0,
                  left: 0,
                  right: 0,
                  child: IgnorePointer(
                    child: Container(
                      height: 1,
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: [
                            Colors.white.withOpacity(0.45),
                            Colors.white.withOpacity(0.12),
                            Colors.transparent,
                          ],
                        ),
                      ),
                    ),
                  ),
                ),

                // ─── Hairline border ──────────────────────────────────
                Positioned.fill(
                  child: IgnorePointer(
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        borderRadius: radius,
                        border: Border.all(
                          color: Colors.white.withOpacity(0.16),
                          width: 1,
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

  Widget _buildLabelValue({
    required String label,
    required String value,
    required double labelSize,
    required double valueSize,
    Widget? trailing,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          label,
          style: TextStyle(
            fontSize: labelSize,
            color: Colors.white.withOpacity(0.5),
            fontWeight: FontWeight.w600,
            letterSpacing: 1.2,
          ),
        ),
        const SizedBox(height: 3),
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Flexible(
              child: Text(
                value,
                style: TextStyle(
                  fontWeight: FontWeight.w700,
                  fontSize: valueSize,
                  color: Colors.white,
                  letterSpacing: 0.4,
                  fontFeatures: const [ui_dart.FontFeature.tabularFigures()],
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            if (trailing != null) ...[
              const SizedBox(width: 5),
              trailing,
            ],
          ],
        ),
      ],
    );
  }

  Widget _buildStatusPill(bool isActive) {
    final color = isActive ? joviMint : joviRed;
    final colorDark = isActive ? joviMintDark : joviRedDark;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [color, colorDark],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: color.withOpacity(0.4),
            blurRadius: 10,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 6,
            height: 6,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: Colors.white,
              boxShadow: [
                BoxShadow(
                  color: Colors.white.withOpacity(0.8),
                  blurRadius: 4,
                ),
              ],
            ),
          ),
          const SizedBox(width: 5),
          Text(
            isActive ? 'ACTIVE' : 'INACTIVE',
            style: const TextStyle(
              color: Colors.white,
              fontSize: 9,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.7,
            ),
          ),
        ],
      ),
    );
  }

  /// Coral (or gold) icon chip — uses the branded icon
  Widget _buildIconChip({
    required bool isPet,
    required Color primaryColor,
    required Color primaryDark,
  }) {
    return Container(
      width: 44,
      height: 44,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [primaryColor, primaryDark],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(13),
        boxShadow: [
          BoxShadow(
            color: primaryColor.withOpacity(0.4),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: isPet
          ? const Icon(Icons.pets, color: Colors.white, size: 22)
          : Padding(
              padding: const EdgeInsets.all(6),
              child: Image.network(
                _coralIconUrl,
                fit: BoxFit.contain,
                errorBuilder: (context, error, stackTrace) => const Icon(
                  Icons.favorite_rounded,
                  color: Colors.white,
                  size: 22,
                ),
              ),
            ),
    );
  }

  /// Profile photo avatar with glass ring. Photo fades in when loaded.
  Widget _buildProfileAvatar({
    required bool isPet,
    required String? photoUrl,
    required Color primaryColor,
  }) {
    final hasPhoto = photoUrl != null && photoUrl.isNotEmpty;
    const size = 44.0;

    final Widget fallback = Center(
      child: Icon(
        isPet ? Icons.pets : Icons.person_rounded,
        color: primaryColor,
        size: 22,
      ),
    );

    return Container(
      padding: const EdgeInsets.all(2),
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: LinearGradient(
          colors: [
            Colors.white.withOpacity(0.35),
            primaryColor.withOpacity(0.6),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        boxShadow: [
          BoxShadow(
            color: primaryColor.withOpacity(0.3),
            blurRadius: 10,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: Colors.white.withOpacity(0.08),
        ),
        clipBehavior: Clip.antiAlias,
        child: hasPhoto
            ? Image.network(
                photoUrl!,
                width: size,
                height: size,
                fit: BoxFit.cover,
                frameBuilder: (context, child, frame, wasSync) {
                  if (wasSync || _reduceMotion) return child;
                  return AnimatedOpacity(
                    opacity: frame == null ? 0 : 1,
                    duration: const Duration(milliseconds: 220),
                    curve: Curves.easeOut,
                    child: child,
                  );
                },
                errorBuilder: (c, e, s) => fallback,
              )
            : fallback,
      ),
    );
  }

  Widget _buildSectionPill(String label, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: color.withOpacity(0.14),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withOpacity(0.35)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, color: color, size: 13),
          const SizedBox(width: 6),
          Text(
            label,
            style: TextStyle(
              color: color,
              fontSize: 11,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.6,
            ),
          ),
        ],
      ),
    );
  }

  // ─── Build ───────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final user = FirebaseAuth.instance.currentUser;

    if (user == null) {
      return _scaffold(child: _buildSignedOutState());
    }

    return StreamBuilder<DocumentSnapshot>(
      stream: FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .snapshots(),
      builder: (context, userSnap) {
        if (userSnap.hasError) {
          return _scaffold(child: _buildErrorState());
        }
        if (!userSnap.hasData) {
          return _scaffold(child: _buildLoadingState());
        }

        final data = userSnap.data!.data() as Map<String, dynamic>?;
        if (data == null) {
          return _scaffold(child: _buildErrorState());
        }

        return _renderCards(user, data);
      },
    );
  }

  List<_CardEntry> _buildEntries(
      User user, Map<String, dynamic> data, String actualMemberId) {
    final entries = <_CardEntry>[];

    final fullName = (data['onboard_fullName'] as String?)?.trim() ?? '';
    entries.add(_CardEntry(
      kind: 'member',
      name: fullName.isNotEmpty ? fullName : 'Member',
      role: 'Primary',
      memberId: actualMemberId,
      photoUrl: data['photo_url'] as String?,
    ));

    if (data['spouse'] == true) {
      final spouseName =
          '${data['sFirst'] ?? ''} ${data['sLast'] ?? ''}'.trim();
      if (spouseName.isNotEmpty) {
        entries.add(_CardEntry(
          kind: 'member',
          name: spouseName,
          role: 'Spouse',
          memberId: actualMemberId,
        ));
      }
    }

    for (final raw in (data['deps'] as List<dynamic>? ?? [])) {
      try {
        final m = jsonDecode(raw as String) as Map<String, dynamic>;
        final depName = '${m['first'] ?? ''} ${m['last'] ?? ''}'.trim();
        if (depName.isNotEmpty) {
          entries.add(_CardEntry(
            kind: 'member',
            name: depName,
            role: 'Dependent',
            memberId: actualMemberId,
          ));
        }
      } catch (_) {
        continue;
      }
    }

    for (final raw in (data['pets'] as List<dynamic>? ?? [])) {
      try {
        final pet = jsonDecode(raw as String) as Map<String, dynamic>;
        final petName = (pet['name'] as String?)?.trim() ?? '';
        if (petName.isEmpty) continue;
        entries.add(_CardEntry(
          kind: 'pet',
          name: petName,
          role: 'Pet',
          memberId: (pet['petId'] as String?) ?? actualMemberId,
          photoUrl: pet['photo_url'] as String?,
          type: pet['type'] as String?,
          breed: pet['breed'] as String?,
        ));
      } catch (_) {
        continue;
      }
    }

    return entries;
  }

  Widget _renderCards(User user, Map<String, dynamic> data) {
    final now = DateTime.now();
    final planType = data['planType'] as String? ?? 'Standard Plan';

    // Member ID from members array or fallback
    String? memberId;
    final rawMembers = data['members'] as List<dynamic>? ?? [];
    if (rawMembers.isNotEmpty) {
      try {
        final firstMember =
            jsonDecode(rawMembers.first as String) as Map<String, dynamic>;
        memberId = firstMember['memberId'] as String?;
      } catch (e) {
        debugPrint('DigitalMembership: error parsing members: $e');
      }
    }
    memberId ??= data['memberId'] as String?;
    final actualMemberId = memberId ?? user.uid;

    // Renewal date
    DateTime validThru;
    if (data['renew'] is Timestamp) {
      validThru = (data['renew'] as Timestamp).toDate();
    } else {
      final signup = user.metadata.creationTime ?? now;
      validThru = signup.add(const Duration(days: 365));
    }

    final daysLeft =
        validThru.isAfter(now) ? validThru.difference(now).inDays : 0;
    final isActive = daysLeft > 0;

    final entries = _buildEntries(user, data, actualMemberId);
    final humanCount = entries.where((e) => !e.isPet).length;
    final petCount = entries.length - humanCount;
    final totalCount = entries.length;
    final hasMultiple = totalCount > 1;

    // Keep _currentPage valid if a member/pet was removed while open.
    if (_currentPage >= totalCount) _currentPage = totalCount - 1;
    if (_currentPage < 0) _currentPage = 0;

    final sideBySide = layoutSettings.enableSideBySide && hasMultiple;
    final cardDimensions = _getCardDimensions(context, sideBySide, totalCount);
    final cardWidth = cardDimensions['width']!;
    final cardHeight = cardDimensions['height']!;

    String pageContextLabel = '';
    if (hasMultiple && !sideBySide) {
      if (_currentPage < humanCount) {
        pageContextLabel = 'Member ${_currentPage + 1} of $humanCount';
      } else {
        final petIdx = _currentPage - humanCount + 1;
        pageContextLabel = 'Pet $petIdx of $petCount';
      }
    }

    final title = hasMultiple ? 'Membership Cards' : 'Membership Card';

    Widget cardsArea;
    if (sideBySide) {
      cardsArea = _buildSideBySide(entries, planType, validThru, daysLeft,
          isActive, cardWidth, cardHeight);
    } else if (hasMultiple) {
      cardsArea = PageView.builder(
        controller: _pageController,
        physics: const PageScrollPhysics(parent: BouncingScrollPhysics()),
        onPageChanged: (i) {
          HapticFeedback.selectionClick();
          setState(() => _currentPage = i);
        },
        itemCount: entries.length,
        itemBuilder: (context, index) {
          final card = Center(
            child: _buildMembershipCard(
              entry: entries[index],
              planType: planType,
              validThru: validThru,
              daysLeft: daysLeft,
              isActive: isActive,
              cardW: cardWidth,
              cardH: cardHeight,
            ),
          );
          if (_reduceMotion) return card;
          return AnimatedBuilder(
            animation: _pageController,
            builder: (context, child) {
              // Driven by the live scroll position, so it tracks the
              // finger 1:1 and is interruptible at any instant.
              double pageOffset;
              if (_pageController.hasClients &&
                  _pageController.position.haveDimensions) {
                pageOffset = (_pageController.page ?? 0) - index;
              } else {
                pageOffset = (_currentPage - index).toDouble();
              }
              final distance = pageOffset.abs().clamp(0.0, 1.0);
              final scale = 1.0 - (distance * 0.07);
              final opacity = 1.0 - (distance * 0.3);
              return Transform.scale(
                scale: scale,
                child: Opacity(opacity: opacity, child: child),
              );
            },
            child: card,
          );
        },
      );
    } else {
      cardsArea = Center(
        child: _buildMembershipCard(
          entry: entries[0],
          planType: planType,
          validThru: validThru,
          daysLeft: daysLeft,
          isActive: isActive,
          cardW: cardWidth,
          cardH: cardHeight,
        ),
      );
    }

    return _scaffold(
      child: Column(
        children: [
          _buildHeader(title, pageContextLabel),
          Expanded(
            child: FadeTransition(
              opacity: _enterFade,
              child: SlideTransition(
                position: _enterRise,
                child: Column(
                  children: [
                    Expanded(child: _wrapWithConstraints(child: cardsArea)),
                    if (!sideBySide && hasMultiple) ...[
                      if (petCount > 0)
                        Padding(
                          padding: const EdgeInsets.only(top: 8, bottom: 4),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              _buildSectionPill(
                                  'MEMBERS', Icons.person_rounded, joviCoral),
                              const SizedBox(width: 8),
                              _buildSectionPill('PETS', Icons.pets, joviGold),
                            ],
                          ),
                        ),
                      _buildPageIndicator(entries, humanCount),
                    ],
                    const SizedBox(height: 20),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPageIndicator(List<_CardEntry> entries, int humanCount) {
    return Semantics(
      label: 'Page ${_currentPage + 1} of ${entries.length}',
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 16),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: List.generate(entries.length, (index) {
            final isPet = index >= humanCount;
            final selected = _currentPage == index;
            final accent = isPet ? joviGold : joviCoral;
            return GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: () {
                if (_reduceMotion) {
                  _pageController.jumpToPage(index);
                } else {
                  _pageController.animateToPage(
                    index,
                    duration: const Duration(milliseconds: 360),
                    curve: _Motion.settle,
                  );
                }
              },
              child: Padding(
                // ~10 px hit padding around each dot
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 8),
                child: AnimatedContainer(
                  duration:
                      _reduceMotion ? Duration.zero : _Motion.indicator,
                  curve: _Motion.settle,
                  height: 8,
                  width: selected ? 24 : 8,
                  decoration: BoxDecoration(
                    color: selected ? accent : Colors.white.withOpacity(0.25),
                    borderRadius: BorderRadius.circular(4),
                    boxShadow: selected
                        ? [
                            BoxShadow(
                              color: accent.withOpacity(0.5),
                              blurRadius: 8,
                              offset: const Offset(0, 2),
                            ),
                          ]
                        : null,
                  ),
                ),
              ),
            );
          }),
        ),
      ),
    );
  }

  Widget _buildHeader(String title, String contextLabel) {
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        statusBarBrightness: Brightness.dark,
      ),
      child: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
          child: Row(
            children: [
              // Back — glass chip, 44 pt target, feedback on press
              _Pressable(
                reduceMotion: _reduceMotion,
                pressedScale: 0.92,
                onTap: () {
                  HapticFeedback.lightImpact();
                  Navigator.of(context).maybePop();
                },
                semanticsLabel: 'Back',
                child: Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.08),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: Colors.white.withOpacity(0.14)),
                  ),
                  child: const Icon(Icons.arrow_back_ios_new_rounded,
                      color: Colors.white, size: 18),
                ),
              ),
              Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      title,
                      textAlign: TextAlign.center,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 17,
                        fontWeight: FontWeight.w600,
                        letterSpacing: -0.4,
                      ),
                    ),
                    AnimatedSwitcher(
                      duration: _reduceMotion
                          ? Duration.zero
                          : const Duration(milliseconds: 180),
                      switchInCurve: Curves.easeOut,
                      switchOutCurve: Curves.easeIn,
                      child: contextLabel.isEmpty
                          ? const SizedBox.shrink()
                          : Padding(
                              key: ValueKey(contextLabel),
                              padding: const EdgeInsets.only(top: 1),
                              child: Text(
                                contextLabel,
                                style: TextStyle(
                                  color: Colors.white.withOpacity(0.6),
                                  fontSize: 12,
                                  fontWeight: FontWeight.w500,
                                  letterSpacing: 0.1,
                                ),
                              ),
                            ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 44),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSideBySide(
    List<_CardEntry> entries,
    String planType,
    DateTime validThru,
    int daysLeft,
    bool isActive,
    double cardWidth,
    double cardHeight,
  ) {
    return Center(
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        physics: const BouncingScrollPhysics(),
        padding: EdgeInsets.symmetric(vertical: layoutSettings.paddingV),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: entries.map((e) {
            return Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10),
              child: _buildMembershipCard(
                entry: e,
                planType: planType,
                validThru: validThru,
                daysLeft: daysLeft,
                isActive: isActive,
                cardW: cardWidth,
                cardH: cardHeight,
              ),
            );
          }).toList(),
        ),
      ),
    );
  }

  /// Navy gradient scaffold wrapper for all states
  Widget _scaffold({required Widget child}) {
    return Container(
      width: widget.width,
      height: widget.height,
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [joviNavy, joviNavy, joviNavyDark],
        ),
      ),
      child: _wrapWithConstraints(child: child),
    );
  }
}
