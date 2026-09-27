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

import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';
import 'dart:ui' as ui_dart;

// ═══════════════════════════════════════════════════════════════════════
// JOVI HEALTH — FAQ WIDGET
// Version: 2026.09.22-r2 (Apple HIG pass: press feedback, Reduce Motion,
//          settle curves, title-case header, search return key)
// r1:      2026.04.20
// Build: JC-FAQ-0922-002
//
// Full navy + glass rebrand of the Kurv FAQ screen. Matches the visual
// language of the Pet Profiles, Requests Flow, and Account Menu widgets.
//
// Notable changes from the Kurv version:
//   - Navy gradient background with ambient accent orbs
//   - Each FAQ card is a white-glass surface with category-coded accents
//   - Header uses coral→mint gradient on icon chips instead of blue
//   - Search field is a translucent glass input, not a white card
//   - "Still have questions?" contact card keeps the coral CTA style
//     used across the rest of the app for primary actions
//   - All Kurv text replaced with Jovi (no content changes beyond that)
//   - Accent colors are reassigned to Jovi palette values — no raw
//     Colors.blue/green/orange/etc.
// ═══════════════════════════════════════════════════════════════════════

// ───────────────────────────────────────────────────────────────────────
// JOVI BRAND COLORS
// ───────────────────────────────────────────────────────────────────────

const Color _joviNavy = Color(0xFF1A2744);
const Color _joviNavyDark = Color(0xFF0F1A2E);
const Color _joviNavyMid = Color(0xFF1F2B47);
const Color _joviCoral = Color(0xFFFF6B4A);
const Color _joviCoralDark = Color(0xFFE5583A);
const Color _joviCoralLight = Color(0xFFFF8F73);
const Color _joviMint = Color(0xFF00D4AA);
const Color _joviMintDark = Color(0xFF00B894);
const Color _joviGold = Color(0xFFFFD166);
const Color _joviViolet = Color(0xFFA78BFA);
const Color _joviVioletDark = Color(0xFF8B6EE8);

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

class FAQItem {
  final String question;
  final String answer;
  final IconData icon;

  /// Accent color used for the FAQ card's icon, border, and highlights
  /// when expanded. Drawn from the Jovi palette — no raw material colors.
  final Color accent;

  FAQItem({
    required this.question,
    required this.answer,
    required this.icon,
    required this.accent,
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

class JoviFAQWidget extends StatefulWidget {
  final double width;
  final double height;

  const JoviFAQWidget({
    Key? key,
    required this.width,
    required this.height,
  }) : super(key: key);

  @override
  _JoviFAQWidgetState createState() => _JoviFAQWidgetState();
}

class _JoviFAQWidgetState extends State<JoviFAQWidget>
    with TickerProviderStateMixin {
  // Responsive Layout Variables
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

  // Track previous screen configuration to prevent unnecessary rebuilds
  double? _lastScreenWidth;
  bool? _lastHasHinge;

  // Animation controllers
  late AnimationController _headerAnimController;
  late AnimationController _listAnimController;
  late Animation<double> _headerScaleAnim;
  late Animation<double> _headerFadeAnim;

  // FAQ state
  int? _expandedIndex;
  List<AnimationController> _itemAnimControllers = [];
  List<Animation<double>> _itemAnimations = [];

  // Search functionality
  String _searchQuery = '';
  final TextEditingController _searchController = TextEditingController();
  List<int> _filteredIndices = [];

  // ─── FAQ Data ─────────────────────────────────────────────────────────
  // Same content as the Kurv version with only the "Kurv" → "Jovi"
  // find/replace. Accent colors have been reassigned to the Jovi
  // palette (coral/mint/gold/violet) to remove the grab-bag of raw
  // material colors (Colors.blue, Colors.green, etc.).
  //
  // Content sensitivity: these answers contain claims about savings
  // ("up to 70%") and clinic amenities that should eventually be
  // reviewed by legal / marketing before commercial launch. For now,
  // they carry over verbatim from the Kurv copy.
  final List<FAQItem> _faqItems = [
    FAQItem(
      question:
          "What is Jovi Health and how is it different from traditional health insurance?",
      answer:
          "Jovi Health is a healthcare membership service that eliminates the complexity of traditional insurance. Instead of dealing with in-network vs. out-of-network providers, pre-authorizations, and hidden fees, you pay a simple flat monthly fee and get reimbursed for out-of-pocket medical expenses through our mobile app. You choose your own providers and have full transparency on costs.",
      icon: Icons.health_and_safety_rounded,
      accent: _joviCoral,
    ),
    FAQItem(
      question: "How much can I save with Jovi Health?",
      answer:
          "Studies show that you can save up to 70% compared to traditional insurance billing. We pass these savings directly to you, helping you keep more money in your pocket while getting quality healthcare.",
      icon: Icons.savings_rounded,
      accent: _joviMint,
    ),
    FAQItem(
      question: "How does the reimbursement process work?",
      answer:
          "It's simple! After receiving medical care or picking up prescriptions, just upload your receipt through our mobile app and we'll reimburse you directly. If you don't have the funds to pay upfront, you can upload the bill and we'll reimburse your pharmacy or doctor directly.",
      icon: Icons.receipt_long_rounded,
      accent: _joviGold,
    ),
    FAQItem(
      question: "What is the deductible and how does it work?",
      answer:
          "We have a simple, easy-to-meet deductible that's designed to be reached quickly. You can track your progress through our app's interactive status bar. Once you meet your deductible, Jovi Health covers your eligible healthcare expenses with no surprises.",
      icon: Icons.trending_up_rounded,
      accent: _joviViolet,
    ),
    FAQItem(
      question: "Do I have to use specific doctors or hospitals?",
      answer:
          "No! Unlike traditional insurance, there are no network restrictions. You have the freedom to choose any provider you want - whether it's a doctor, specialist, pharmacy, or hospital. If you go to a Jovi Health branded clinic, there are no co-pays, little to no wait, complimentary beverages and snacks and a handful of complimentary services. You're in complete control of your healthcare choices.",
      icon: Icons.medical_services_rounded,
      accent: _joviCoralLight,
    ),
    FAQItem(
      question: "What types of care can I access through Jovi Health?",
      answer:
          "Through our mobile app, you can access multiple types of care: in-person visits at Jovi Health clinics, telehealth consultations from home, and more. You can request care anytime and choose the option that works best for you.",
      icon: Icons.healing_rounded,
      accent: _joviMintDark,
    ),
    FAQItem(
      question: "Can I add dental and vision coverage?",
      answer:
          "Yes! In addition to our main healthcare membership, you can add dental and vision plans to your coverage for comprehensive care.",
      icon: Icons.visibility_rounded,
      accent: _joviVioletDark,
    ),
    FAQItem(
      question: "How long does it take to get reimbursed?",
      answer:
          "Our reimbursement process is designed to be quick and hassle-free. Simply upload your receipt through the app, and we process reimbursements directly to you or your healthcare provider promptly.",
      icon: Icons.access_time_rounded,
      accent: _joviGold,
    ),
    FAQItem(
      question: "Is there a limit to how many times I can submit claims?",
      answer:
          "Our membership model is designed to provide you with the care you need. You can submit claims through the app whenever you receive medical services or need prescriptions, making healthcare truly accessible and affordable.",
      icon: Icons.all_inclusive_rounded,
      accent: _joviCoral,
    ),
  ];

  @override
  void initState() {
    super.initState();
    _initializeAnimations();
    _initializeFilteredIndices();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    analyzeScreenConfiguration();
  }

  void _initializeAnimations() {
    _headerAnimController = AnimationController(
      vsync: this,
      duration: _Motion.enter,
    );

    _listAnimController = AnimationController(
      vsync: this,
      duration: _Motion.enter,
    );

    // Scale from 0.96, not 0.0: the hero card used to inflate from nothing.
    _headerScaleAnim = Tween<double>(begin: 0.96, end: 1.0).animate(
      CurvedAnimation(parent: _headerAnimController, curve: _Motion.settle),
    );

    _headerFadeAnim = CurvedAnimation(
      parent: _headerAnimController,
      curve: Curves.easeOut,
    );

    for (int i = 0; i < _faqItems.length; i++) {
      final controller = AnimationController(
        vsync: this,
        duration: _Motion.select,
      );
      _itemAnimControllers.add(controller);
      _itemAnimations.add(CurvedAnimation(
        parent: controller,
        curve: Curves.easeOut,
      ));
    }

    if (_platformReduceMotion()) {
      _headerAnimController.value = 1.0;
      _listAnimController.value = 1.0;
    } else {
      _headerAnimController.forward();
      _listAnimController.forward();
    }
  }

  void _initializeFilteredIndices() {
    _filteredIndices = List.generate(_faqItems.length, (index) => index);
  }

  // ─── Responsive layout analysis (same pattern as RequestsFlow) ──────

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
          contentMax: 1100,
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

  // ─── Search / filter logic ─────────────────────────────────────────

  void _filterFAQs(String query) {
    setState(() {
      _searchQuery = query.toLowerCase();
      if (_searchQuery.isEmpty) {
        _filteredIndices = List.generate(_faqItems.length, (index) => index);
      } else {
        _filteredIndices = [];
        for (int i = 0; i < _faqItems.length; i++) {
          final item = _faqItems[i];
          if (item.question.toLowerCase().contains(_searchQuery) ||
              item.answer.toLowerCase().contains(_searchQuery)) {
            _filteredIndices.add(i);
          }
        }
      }
    });
  }

  void _toggleExpansion(int index) {
    HapticFeedback.selectionClick();
    setState(() {
      if (_expandedIndex == index) {
        _expandedIndex = null;
        _itemAnimControllers[index].reverse();
      } else {
        if (_expandedIndex != null) {
          _itemAnimControllers[_expandedIndex!].reverse();
        }
        _expandedIndex = index;
        _itemAnimControllers[index].forward();
      }
    });
  }

  // ─── Header ────────────────────────────────────────────────────────

  Widget _buildHeader() {
    final statusBarHeight = MediaQuery.of(context).padding.top;

    return Padding(
      padding: EdgeInsets.fromLTRB(
        layoutSettings.paddingH,
        statusBarHeight + 10,
        layoutSettings.paddingH,
        layoutSettings.paddingV * 0.6,
      ),
      child: Column(
        children: [
          Row(
            children: [
              // Back button (matches other Jovi widgets).
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
                    }
                  },
                  borderRadius: BorderRadius.circular(22),
                  child: Semantics(
                    label: 'Back',
                    button: true,
                    child: Container(
                      width: 44,
                      height: 44,
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.06),
                        shape: BoxShape.circle,
                        border: Border.all(
                          color: Colors.white.withOpacity(0.14),
                          width: 0.8,
                        ),
                      ),
                      child: Icon(
                        Icons.arrow_back_ios_new_rounded,
                        color: Colors.white.withOpacity(0.85),
                        size: 16,
                      ),
                    ),
                  ),
                ),
              )),
              const SizedBox(width: 12),
              // Title + subtitle.
              Expanded(
                child: FadeTransition(
                  opacity: _headerFadeAnim,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        'FAQ',
                        style: TextStyle(
                          color: _joviCoral.withOpacity(0.85),
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.8,
                        ),
                      ),
                      const SizedBox(height: 1),
                      const Text(
                        'How Can We Help?',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 17,
                          fontWeight: FontWeight.w600,
                          letterSpacing: -0.4,
                          height: 1.15,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              // Decorative icon chip (matches other Jovi widgets' headers).
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [_joviCoral, _joviCoralDark],
                  ),
                  borderRadius: BorderRadius.circular(11),
                  boxShadow: [
                    BoxShadow(
                      color: _joviCoral.withOpacity(0.35),
                      blurRadius: 12,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: const Icon(
                  Icons.help_outline_rounded,
                  color: Colors.white,
                  size: 20,
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          // Hero card — matches the "intro copy" pattern used in the
          // meditation + pet flows.
          ScaleTransition(
            scale: _headerScaleAnim,
            child: Container(
              padding: const EdgeInsets.all(16),
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
                    width: 50,
                    height: 50,
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [_joviMint, _joviMintDark],
                      ),
                      borderRadius: BorderRadius.circular(14),
                      boxShadow: [
                        BoxShadow(
                          color: _joviMint.withOpacity(0.35),
                          blurRadius: 14,
                          offset: const Offset(0, 5),
                        ),
                      ],
                    ),
                    child: const Icon(
                      Icons.auto_stories_rounded,
                      color: Colors.white,
                      size: 24,
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Text(
                          'Get your questions answered',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 15,
                            fontWeight: FontWeight.w700,
                            letterSpacing: -0.3,
                          ),
                        ),
                        const SizedBox(height: 3),
                        Text(
                          'Everything you need to know about Jovi Health',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.6),
                            fontSize: 12.5,
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
          ),
        ],
      ),
    );
  }

  // ─── Search bar ────────────────────────────────────────────────────

  Widget _buildSearchBar() {
    return Container(
      margin: EdgeInsets.fromLTRB(
        layoutSettings.paddingH,
        6,
        layoutSettings.paddingH,
        layoutSettings.paddingV * 0.8,
      ),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.06),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: Colors.white.withOpacity(0.1),
          width: 1,
        ),
      ),
      child: TextField(
        controller: _searchController,
        autocorrect: false,
        textInputAction: TextInputAction.search,
        style: const TextStyle(
          color: Colors.white,
          fontSize: 15,
          fontWeight: FontWeight.w500,
        ),
        cursorColor: _joviCoral,
        decoration: InputDecoration(
          hintText: 'Search FAQs',
          hintStyle: TextStyle(
            fontSize: 13.5,
            color: Colors.white.withOpacity(0.4),
            fontWeight: FontWeight.w500,
          ),
          prefixIcon: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            child: Icon(
              Icons.search_rounded,
              color: _joviCoral.withOpacity(0.8),
              size: 18,
            ),
          ),
          prefixIconConstraints: const BoxConstraints(
            minWidth: 40,
            minHeight: 40,
          ),
          suffixIcon: _searchQuery.isNotEmpty
              ? IconButton(
                  icon: Icon(
                    Icons.close_rounded,
                    color: Colors.white.withOpacity(0.55),
                    size: 18,
                  ),
                  onPressed: () {
                    _searchController.clear();
                    _filterFAQs('');
                  },
                )
              : null,
          border: InputBorder.none,
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 6,
            vertical: 14,
          ),
        ),
        onChanged: _filterFAQs,
      ),
    );
  }

  // ─── FAQ card ──────────────────────────────────────────────────────

  Widget _buildFAQItem(int actualIndex) {
    final item = _faqItems[actualIndex];
    final isExpanded = _expandedIndex == actualIndex;

    return _Pressable(
        feedbackOnly: true,
        pressedScale: 0.985,
        child: AnimatedContainer(
      duration: _Motion.select,
      curve: _Motion.settle,
      margin: EdgeInsets.only(
        left: layoutSettings.paddingH,
        right: layoutSettings.paddingH,
        bottom: 10,
      ),
      decoration: BoxDecoration(
        color: isExpanded
            ? item.accent.withOpacity(0.08)
            : Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: isExpanded
              ? item.accent.withOpacity(0.5)
              : Colors.white.withOpacity(0.1),
          width: isExpanded ? 1.3 : 1,
        ),
        boxShadow: isExpanded
            ? [
                BoxShadow(
                  color: item.accent.withOpacity(0.2),
                  blurRadius: 18,
                  offset: const Offset(0, 6),
                ),
              ]
            : null,
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () => _toggleExpansion(actualIndex),
          borderRadius: BorderRadius.circular(16),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Icon chip — gradient when expanded, translucent when not.
                    AnimatedContainer(
                      duration: _Motion.select,
                      curve: _Motion.settle,
                      width: 42,
                      height: 42,
                      decoration: BoxDecoration(
                        gradient: isExpanded
                            ? LinearGradient(
                                colors: [
                                  item.accent,
                                  _darken(item.accent, 0.18),
                                ],
                                begin: Alignment.topLeft,
                                end: Alignment.bottomRight,
                              )
                            : null,
                        color:
                            isExpanded ? null : item.accent.withOpacity(0.15),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: item.accent.withOpacity(isExpanded ? 0 : 0.3),
                          width: 1,
                        ),
                        boxShadow: isExpanded
                            ? [
                                BoxShadow(
                                  color: item.accent.withOpacity(0.4),
                                  blurRadius: 10,
                                  offset: const Offset(0, 4),
                                ),
                              ]
                            : null,
                      ),
                      child: Icon(
                        item.icon,
                        color: isExpanded ? Colors.white : item.accent,
                        size: 22,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Padding(
                        padding: const EdgeInsets.only(top: 2),
                        child: Text(
                          item.question,
                          style: TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.w600,
                            color: Colors.white,
                            height: 1.35,
                            letterSpacing: -0.2,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    AnimatedRotation(
                      turns: isExpanded ? 0.5 : 0,
                      duration: _Motion.select,
                      curve: _Motion.settle,
                      child: Container(
                        width: 28,
                        height: 28,
                        decoration: BoxDecoration(
                          color: isExpanded
                              ? item.accent.withOpacity(0.18)
                              : Colors.white.withOpacity(0.06),
                          shape: BoxShape.circle,
                        ),
                        child: Icon(
                          Icons.keyboard_arrow_down_rounded,
                          color: isExpanded
                              ? item.accent
                              : Colors.white.withOpacity(0.55),
                          size: 18,
                        ),
                      ),
                    ),
                  ],
                ),
                AnimatedCrossFade(
                  firstChild: const SizedBox.shrink(),
                  secondChild: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SizedBox(height: 14),
                      // Subtle divider.
                      Container(
                        height: 1,
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            colors: [
                              item.accent.withOpacity(0.3),
                              item.accent.withOpacity(0.08),
                              Colors.transparent,
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 14),
                      FadeTransition(
                        opacity: _itemAnimations[actualIndex],
                        child: Container(
                          padding: const EdgeInsets.all(14),
                          decoration: BoxDecoration(
                            color: item.accent.withOpacity(0.06),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: item.accent.withOpacity(0.18),
                              width: 1,
                            ),
                          ),
                          child: Text(
                            item.answer,
                            style: TextStyle(
                              fontSize: 14,
                              color: Colors.white.withOpacity(0.85),
                              height: 1.5,
                              fontWeight: FontWeight.w400,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                  crossFadeState: isExpanded
                      ? CrossFadeState.showSecond
                      : CrossFadeState.showFirst,
                  duration: _Motion.select,
                  sizeCurve: _Motion.settle,
                ),
              ],
            ),
          ),
        ),
      ),
    ));
  }

  /// Utility: produces a darker shade of the given color by mixing toward
  /// black by the given fraction. Used for the expanded-icon gradient end.
  Color _darken(Color c, double amount) {
    final hsl = HSLColor.fromColor(c);
    final newLight = (hsl.lightness - amount).clamp(0.0, 1.0);
    return hsl.withLightness(newLight).toColor();
  }

  // ─── No results ────────────────────────────────────────────────────

  Widget _buildNoResults() {
    return Container(
      margin: EdgeInsets.fromLTRB(
        layoutSettings.paddingH,
        layoutSettings.paddingV,
        layoutSettings.paddingH,
        layoutSettings.paddingV,
      ),
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: Colors.white.withOpacity(0.1),
          width: 1,
        ),
      ),
      child: Column(
        children: [
          Container(
            width: 64,
            height: 64,
            decoration: BoxDecoration(
              color: _joviCoral.withOpacity(0.12),
              shape: BoxShape.circle,
              border: Border.all(
                color: _joviCoral.withOpacity(0.28),
                width: 1,
              ),
            ),
            child: const Icon(
              Icons.search_off_rounded,
              size: 30,
              color: _joviCoral,
            ),
          ),
          const SizedBox(height: 14),
          const Text(
            'No FAQs Found',
            style: TextStyle(
              fontSize: 17,
              fontWeight: FontWeight.w700,
              color: Colors.white,
              letterSpacing: -0.3,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            'Try a different keyword or view all questions.',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 12.5,
              color: Colors.white.withOpacity(0.6),
              fontWeight: FontWeight.w500,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 16),
          _Pressable(
              feedbackOnly: true,
              child: Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: () {
                HapticFeedback.selectionClick();
                _searchController.clear();
                _filterFAQs('');
              },
              borderRadius: BorderRadius.circular(12),
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 18, vertical: 11),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [_joviCoral, _joviCoralDark],
                  ),
                  borderRadius: BorderRadius.circular(12),
                  boxShadow: [
                    BoxShadow(
                      color: _joviCoral.withOpacity(0.4),
                      blurRadius: 12,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: const Text(
                  'Show All FAQs',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.2,
                  ),
                ),
              ),
            ),
          )),
        ],
      ),
    );
  }

  // ─── Contact support card ──────────────────────────────────────────

  Widget _buildContactSupport() {
    return Container(
      margin: EdgeInsets.fromLTRB(
        layoutSettings.paddingH,
        6,
        layoutSettings.paddingH,
        layoutSettings.paddingV * 0.6,
      ),
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            _joviCoral.withOpacity(0.14),
            _joviCoralDark.withOpacity(0.08),
          ],
        ),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: _joviCoral.withOpacity(0.3),
          width: 1,
        ),
      ),
      child: Column(
        children: [
          Container(
            width: 54,
            height: 54,
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
                  blurRadius: 16,
                  offset: const Offset(0, 6),
                ),
              ],
            ),
            child: const Icon(
              Icons.support_agent_rounded,
              size: 26,
              color: Colors.white,
            ),
          ),
          const SizedBox(height: 14),
          const Text(
            'Still have questions?',
            style: TextStyle(
              fontSize: 17,
              fontWeight: FontWeight.w700,
              color: Colors.white,
              letterSpacing: -0.4,
            ),
          ),
          const SizedBox(height: 5),
          Text(
            'Our support team is here to help with anything else you need to know about Jovi Health.',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 12.5,
              color: Colors.white.withOpacity(0.7),
              fontWeight: FontWeight.w500,
              height: 1.5,
            ),
          ),
          const SizedBox(height: 16),
          _Pressable(
              feedbackOnly: true,
              child: Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: () {
                HapticFeedback.lightImpact();
                _openChatLanding();
              },
              borderRadius: BorderRadius.circular(13),
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(vertical: 13),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [_joviCoral, _joviCoralDark],
                  ),
                  borderRadius: BorderRadius.circular(13),
                  boxShadow: [
                    BoxShadow(
                      color: _joviCoral.withOpacity(0.4),
                      blurRadius: 14,
                      offset: const Offset(0, 5),
                    ),
                  ],
                ),
                child: const Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.chat_bubble_rounded,
                        color: Colors.white, size: 17),
                    SizedBox(width: 8),
                    Text(
                      'Live Chat',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                        letterSpacing: -0.2,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          )),
        ],
      ),
    );
  }

  /// Navigate to chat. NOTE: context.push never throws on an unknown
  /// path, so only the first name is ever tried; confirm 'chatLanding'
  /// is the real route name in FlutterFlow.
  void _openChatLanding() {
    const routes = ['chatLanding', 'chat', 'chat_landing'];
    for (final r in routes) {
      try {
        context.push('/$r');
        return;
      } catch (_) {
        continue;
      }
    }
  }

  // ─── Ambient background orbs ───────────────────────────────────────

  Widget _buildAmbientOrb(Color color, double size) {
    return IgnorePointer(
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: RadialGradient(
            colors: [color, color.withOpacity(0)],
          ),
        ),
      ),
    );
  }

  // ─── Build ─────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return wrapWithConstraints(
      child: Container(
        width: widget.width,
        height: widget.height,
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [_joviNavy, _joviNavy, _joviNavyDark],
          ),
        ),
        child: Stack(
          children: [
            // Ambient orbs — adds depth without distraction.
            Positioned(
              top: -80,
              right: -60,
              child: _buildAmbientOrb(_joviCoral.withOpacity(0.12), 220),
            ),
            Positioned(
              bottom: -100,
              left: -80,
              child: _buildAmbientOrb(_joviMint.withOpacity(0.08), 240),
            ),
            // Main content.
            SafeArea(
              bottom: false,
              child: Column(
                children: [
                  _buildHeader(),
                  Expanded(
                    child: SingleChildScrollView(
                      padding: EdgeInsets.only(
                        bottom: layoutSettings.paddingV,
                      ),
                      child: Column(
                        children: [
                          _buildSearchBar(),
                          if (_filteredIndices.isEmpty)
                            _buildNoResults()
                          else
                            FadeTransition(
                              opacity: _listAnimController,
                              child: Column(
                                children: _filteredIndices
                                    .map((index) => _buildFAQItem(index))
                                    .toList(),
                              ),
                            ),
                          const SizedBox(height: 8),
                          _buildContactSupport(),
                          const SizedBox(height: 18),
                        ],
                      ),
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

  @override
  void dispose() {
    _headerAnimController.dispose();
    _listAnimController.dispose();
    _searchController.dispose();
    for (var controller in _itemAnimControllers) {
      controller.dispose();
    }
    super.dispose();
  }
}
