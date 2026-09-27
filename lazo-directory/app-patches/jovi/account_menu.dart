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
// JOVI HEALTH - ACCOUNT MENU (NAVY + GLASS)
// Version: 2026.09.22-r4 (Apple HIG pass: press feedback, painted glass on
//          30 list rows instead of 30 live blurs, shorter stagger, Reduce Motion)
// r3:      2026.04.22 (added Fitness entry in Health Services)
// ============================================================

import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';
import 'package:url_launcher/url_launcher.dart';
import 'dart:ui';
import 'dart:ui' as ui_dart;
import 'dart:math' as math;

// Jovi Health Brand Colors
const Color joviCoral = Color(0xFFFF6B4A);
const Color joviCoralDark = Color(0xFFE5583A);
const Color joviCoralLight = Color(0xFFFF8F73);
const Color joviNavy = Color(0xFF1A2744);
const Color joviNavyDark = Color(0xFF0F1A2E);
const Color joviNavyMid = Color(0xFF1F2B47);
const Color joviMint = Color(0xFF00D4AA);
const Color joviMintDark = Color(0xFF00B894);
const Color joviGold = Color(0xFFFFD166);

enum ScreenType { compact, medium, expanded, large }

class ResponsiveConfig {
  final double paddingH;
  final double paddingV;
  final double contentMax;
  final double itemHeight;
  final double iconSize;
  final double textSize;
  final double titleSize;
  final double subtitleSize;
  final bool wideMode;
  final double itemMinHeight;
  final double itemMaxHeight;
  final double spacingUnit;

  ResponsiveConfig({
    required this.paddingH,
    required this.paddingV,
    required this.contentMax,
    required this.itemHeight,
    required this.iconSize,
    required this.textSize,
    required this.titleSize,
    required this.subtitleSize,
    required this.wideMode,
    required this.itemMinHeight,
    required this.itemMaxHeight,
    required this.spacingUnit,
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

class AccountMenuWidget extends StatefulWidget {
  const AccountMenuWidget({
    Key? key,
    this.width,
    this.height,
    this.displayName,
    this.firstName,
    this.lastName,
    this.email,
    this.sPhotoUrl,
  }) : super(key: key);

  final double? width;
  final double? height;
  final String? displayName;
  final String? firstName;
  final String? lastName;
  final String? email;
  final String? sPhotoUrl;

  @override
  State<AccountMenuWidget> createState() => _AccountMenuWidgetState();
}

class _AccountMenuWidgetState extends State<AccountMenuWidget>
    with SingleTickerProviderStateMixin {
  final scaffoldKey = GlobalKey<ScaffoldState>();

  ScreenType currentScreenType = ScreenType.compact;
  late ResponsiveConfig layoutSettings;

  double? _lastScreenWidth;
  bool? _lastHasHinge;
  double? _lastTextScaleFactor;
  double? _lastPixelRatio;

  TextEditingController searchController = TextEditingController();
  String searchQuery = '';
  bool _searchFocused = false;
  final FocusNode _searchFocusNode = FocusNode();

  late AnimationController _entranceController;

  // Menu items — reassigned colors optimized for navy background
  final Map<String, List<MenuItem>> menuCategories = {
    'Health Services': [
      MenuItem(
        icon: Icons.badge_outlined,
        title: 'Digital Membership Card',
        subtitle: 'Present this card at our clinic',
        route: 'DigitalMembershipCard',
        color: joviCoral,
      ),
      MenuItem(
        icon: Icons.receipt_long_outlined,
        title: 'File a Claim',
        subtitle: 'Submit receipts for reimbursement or have Jovi Health pay',
        route: 'FileClaim',
        color: Color(0xFF38BDF8), // brighter sky blue for contrast
      ),
      MenuItem(
        icon: Icons.medical_services_outlined,
        title: 'Request Care',
        subtitle: 'Schedule an appointment',
        route: 'requests',
        color: joviMint,
      ),
      MenuItem(
        icon: Icons.directions_run_outlined,
        title: 'Fitness',
        subtitle: 'Track runs, walks, and rides with live GPS',
        route: 'fitnessHome',
        color:
            Color(0xFFFBBF24), // amber — distinct from mint/sky in this group
      ),
      MenuItem(
        icon: Icons.folder_shared_outlined,
        title: 'Care Records',
        subtitle: 'Your visits, prescriptions, and care timeline',
        route: 'careRecords',
        color: Color(0xFFA78BFA), // violet — distinct from Request Care mint
      ),
      MenuItem(
        icon: Icons.notifications_none_rounded,
        title: 'Notifications',
        subtitle: 'Appointments, claims, refills, and billing updates',
        route: 'notifications',
        color: joviCoral,
      ),
      MenuItem(
        icon: Icons.family_restroom_outlined,
        title: 'Family & Dependents',
        subtitle: 'Add or update who is covered on your plan',
        route: 'dependents',
        color: Color(0xFF60A5FA), // sky blue
      ),
      MenuItem(
        icon: Icons.vaccines_outlined,
        title: 'Vaccination Records',
        subtitle: 'Shots and boosters for you and your family',
        route: 'vaccinations',
        color: joviMint,
      ),
    ],
    'Medications & Health': [
      MenuItem(
        icon: Icons.medication_outlined,
        title: 'Medication Reminder',
        subtitle: 'Track your medications',
        route: 'medications',
        color: Color(0xFFA78BFA), // lighter purple for navy contrast
      ),
      MenuItem(
        icon: Icons.refresh,
        title: 'Prescription Refills',
        subtitle: 'Request refills and track status',
        route: 'scriptRefill',
        color: joviMintDark,
      ),
      MenuItem(
        icon: Icons.local_pharmacy_outlined,
        title: 'Pharmacies',
        subtitle: 'Nearby pharmacies, hours, and where your refills go',
        route: 'pharmacies',
        color: Color(0xFF34D399), // emerald
      ),
      MenuItem(
        icon: Icons.warning_amber_outlined,
        title: 'Drug Interactions',
        subtitle: 'Check drug interactions',
        route: 'drugInteractions',
        color: Color(0xFFF472B6), // brighter pink
      ),
      MenuItem(
        icon: Icons.favorite_border,
        title: 'Vital Signs Tracker',
        subtitle: 'Monitor your health metrics',
        route: 'Vitals',
        color: Color(0xFFFB7185), // rose
      ),
      MenuItem(
        icon: Icons.science_outlined,
        title: 'Lab Results',
        subtitle: 'View your test results',
        route: 'https://www.labcorp.com/patients/results',
        color: Color(0xFF22D3EE), // cyan
      ),
      MenuItem(
        icon: Icons.access_time,
        title: 'Medication Half-Life',
        subtitle: 'Medication information',
        route: 'MedicationHalfLifeWidget',
        color: Color(0xFF2DD4BF), // teal
      ),
    ],
    'Pet Care': [
      MenuItem(
        icon: Icons.pets_outlined,
        title: 'My Pets',
        subtitle: 'Manage your pets and their health profiles',
        route: 'petPro',
        color: Color(0xFFA78BFA), // violet — consistent with pet branding
      ),
      MenuItem(
        icon: Icons.vaccines_outlined,
        title: 'Vaccinations',
        subtitle: 'Track vaccination schedules and upcoming boosters',
        route: 'petVaccinations',
        color: Color(0xFF22D3EE), // cyan
      ),
      MenuItem(
        icon: Icons.medication_liquid_outlined,
        title: 'Pet Medications',
        subtitle: 'Schedules, reminders, and refills for your pet',
        route: 'petMedications',
        color: Color(0xFFF472B6), // pink
      ),
      MenuItem(
        icon: Icons.health_and_safety_outlined,
        title: 'Pet Symptom Checker',
        subtitle: 'Get vet guidance for symptoms you\'re noticing',
        route: 'petSymptomChecker',
        color: Color(0xFFFB7185), // rose
      ),
      MenuItem(
        icon: Icons.folder_shared_outlined,
        title: 'Pet Records',
        subtitle: 'Vet visits, treatments, and timeline',
        route: 'petCareRecords',
        color: joviMint,
      ),
      MenuItem(
        icon: Icons.monitor_weight_outlined,
        title: 'Weight Alerts',
        subtitle: 'Notifications when your pet is outside a healthy range',
        route: 'petWeightAlerts',
        color: Color(0xFFFFD166), // gold — matches weight alert accent
      ),
      MenuItem(
        icon: Icons.receipt_long_outlined,
        title: 'File Pet Claim',
        subtitle: 'Submit pet insurance claims and receipts',
        route: 'petFileClaim',
        color: Color(0xFF38BDF8), // sky blue
      ),
    ],
    'Resources & Support': [
      MenuItem(
        icon: Icons.headphones,
        title: 'Meditation Audio',
        subtitle: 'Listen to relaxing music to unwind',
        route: 'meditationAudio',
        color: Color(0xFFC084FC), // light violet
      ),
      MenuItem(
        icon: Icons.chat_bubble_outline,
        title: 'Help Center',
        subtitle: 'Chat with our team',
        route: 'ChatLanding',
        color: Color(0xFF818CF8), // indigo
      ),
      MenuItem(
        icon: Icons.location_on_outlined,
        title: 'Clinic Locator',
        subtitle: 'Find our clinics',
        route: 'clinicLocator',
        color: joviCoralLight,
      ),
    ],
    'Account': [
      MenuItem(
        icon: Icons.account_circle_outlined,
        title: 'Update Account',
        subtitle: 'Manage your profile',
        route: 'userPro',
        color: joviGold,
      ),
      MenuItem(
        icon: Icons.ios_share_rounded,
        title: 'Export My Records',
        subtitle: 'Download a PDF of your health and pet records',
        route: 'recordsExport',
        color: Color(0xFFF472B6), // pink
      ),
      MenuItem(
        icon: Icons.help_outline,
        title: 'FAQs',
        subtitle: 'Get your questions answered',
        route: 'FAQs',
        color: Color(0xFF94A3B8), // slate
      ),
    ],
  };

  @override
  void initState() {
    super.initState();

    layoutSettings = ResponsiveConfig(
      paddingH: 16,
      paddingV: 16,
      contentMax: double.infinity,
      itemHeight: 80,
      iconSize: 20,
      textSize: 14,
      titleSize: 20,
      subtitleSize: 12,
      wideMode: false,
      itemMinHeight: 70,
      itemMaxHeight: 120,
      spacingUnit: 8,
    );

    _entranceController = AnimationController(
      duration: const Duration(milliseconds: 600),
      vsync: this,
    );
    if (_platformReduceMotion()) {
      _entranceController.value = 1.0;
    } else {
      _entranceController.forward();
    }

    searchController.addListener(() {
      setState(() {
        searchQuery = searchController.text.toLowerCase();
      });
    });

    _searchFocusNode.addListener(() {
      setState(() {
        _searchFocused = _searchFocusNode.hasFocus;
      });
    });
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    analyzeScreenConfiguration();
  }

  @override
  void dispose() {
    searchController.dispose();
    _searchFocusNode.dispose();
    _entranceController.dispose();
    super.dispose();
  }

  double _scaleValue(
      double baseValue, double screenWidth, double textScaleFactor) {
    double screenScale = math.min(screenWidth / 375.0, 2.5);
    double textScale = math.min(textScaleFactor, 1.3);
    return (baseValue * screenScale * textScale)
        .clamp(baseValue * 0.7, baseValue * 2.0);
  }

  double _getSpacing(double baseSpacing, double screenWidth) {
    if (screenWidth < 360) return baseSpacing * 0.75;
    if (screenWidth < 400) return baseSpacing * 0.85;
    if (screenWidth > 600) return baseSpacing * 1.2;
    if (screenWidth > 900) return baseSpacing * 1.4;
    return baseSpacing;
  }

  void analyzeScreenConfiguration() {
    final mediaQuery = MediaQuery.of(context);
    final screenWidth = mediaQuery.size.width;
    final screenHeight = mediaQuery.size.height;
    final displayFeatures = mediaQuery.displayFeatures;
    final textScaleFactor = mediaQuery.textScaleFactor;
    final pixelRatio = mediaQuery.devicePixelRatio;

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
        _lastTextScaleFactor == textScaleFactor &&
        _lastPixelRatio == pixelRatio) {
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
    _lastTextScaleFactor = textScaleFactor;
    _lastPixelRatio = pixelRatio;
    currentScreenType = screenType;
    layoutSettings = generateLayoutConfig(screenType, screenWidth,
        screenHeight, hasHinge, textScaleFactor, pixelRatio);
  }

  ResponsiveConfig generateLayoutConfig(
    ScreenType type,
    double width,
    double height,
    bool hasHinge,
    double textScaleFactor,
    double pixelRatio,
  ) {
    final basePadding = _getSpacing(16.0, width);
    final baseIconSize = _scaleValue(20.0, width, textScaleFactor);
    final baseTextSize = _scaleValue(14.0, width, textScaleFactor);
    final baseTitleSize = _scaleValue(16.0, width, textScaleFactor);
    final baseSubtitleSize = _scaleValue(12.0, width, textScaleFactor);
    final baseSpacing = _getSpacing(8.0, width);

    switch (type) {
      case ScreenType.expanded:
        return ResponsiveConfig(
          paddingH: basePadding,
          paddingV: basePadding * 1.25,
          contentMax: double.infinity,
          itemHeight: _scaleValue(90.0, width, textScaleFactor),
          iconSize: baseIconSize * 1.2,
          textSize: baseTextSize * 1.1,
          titleSize: baseTitleSize * 1.2,
          subtitleSize: baseSubtitleSize * 1.1,
          wideMode: true,
          itemMinHeight: _scaleValue(80.0, width, textScaleFactor),
          itemMaxHeight: _scaleValue(130.0, width, textScaleFactor),
          spacingUnit: baseSpacing * 1.2,
        );
      case ScreenType.large:
        return ResponsiveConfig(
          paddingH: basePadding * 2.5,
          paddingV: basePadding * 1.75,
          contentMax: 800,
          itemHeight: _scaleValue(95.0, width, textScaleFactor),
          iconSize: baseIconSize * 1.3,
          textSize: baseTextSize * 1.2,
          titleSize: baseTitleSize * 1.4,
          subtitleSize: baseSubtitleSize * 1.2,
          wideMode: true,
          itemMinHeight: _scaleValue(85.0, width, textScaleFactor),
          itemMaxHeight: _scaleValue(140.0, width, textScaleFactor),
          spacingUnit: baseSpacing * 1.5,
        );
      case ScreenType.medium:
        return ResponsiveConfig(
          paddingH: basePadding * 1.5,
          paddingV: basePadding * 1.5,
          contentMax: 600,
          itemHeight: _scaleValue(85.0, width, textScaleFactor),
          iconSize: baseIconSize * 1.1,
          textSize: baseTextSize,
          titleSize: baseTitleSize * 1.2,
          subtitleSize: baseSubtitleSize,
          wideMode: true,
          itemMinHeight: _scaleValue(75.0, width, textScaleFactor),
          itemMaxHeight: _scaleValue(120.0, width, textScaleFactor),
          spacingUnit: baseSpacing * 1.2,
        );
      case ScreenType.compact:
      default:
        final isVerySmall = width < 360;
        return ResponsiveConfig(
          paddingH: basePadding * (isVerySmall ? 0.8 : 1.0),
          paddingV: basePadding * (isVerySmall ? 0.8 : 1.0),
          contentMax: double.infinity,
          itemHeight:
              _scaleValue(isVerySmall ? 75.0 : 80.0, width, textScaleFactor),
          iconSize: baseIconSize * (isVerySmall ? 0.9 : 1.0),
          textSize: baseTextSize * (isVerySmall ? 0.9 : 1.0),
          titleSize: baseTitleSize * (isVerySmall ? 0.95 : 1.0),
          subtitleSize: baseSubtitleSize * (isVerySmall ? 0.9 : 1.0),
          wideMode: false,
          itemMinHeight:
              _scaleValue(isVerySmall ? 65.0 : 70.0, width, textScaleFactor),
          itemMaxHeight:
              _scaleValue(isVerySmall ? 95.0 : 110.0, width, textScaleFactor),
          spacingUnit: baseSpacing,
        );
    }
  }

  Widget wrapWithConstraints({required Widget child}) {
    if (currentScreenType == ScreenType.large &&
        layoutSettings.contentMax < double.infinity) {
      return Center(
        child: ConstrainedBox(
          constraints: BoxConstraints(maxWidth: layoutSettings.contentMax),
          child: child,
        ),
      );
    }
    if (currentScreenType == ScreenType.medium &&
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

  List<MenuItem> getFilteredItems() {
    if (searchQuery.isEmpty) return [];
    List<MenuItem> filtered = [];
    menuCategories.forEach((category, items) {
      filtered.addAll(items.where((item) =>
          item.title.toLowerCase().contains(searchQuery) ||
          item.subtitle.toLowerCase().contains(searchQuery)));
    });
    return filtered;
  }

  Future<void> _navigateToRoute(String route, String title) async {
    if (route.startsWith('http')) {
      final Uri url = Uri.parse(route);
      if (await canLaunchUrl(url)) {
        await launchUrl(url, mode: LaunchMode.externalApplication);
      }
      return;
    }

    List<String> routesToTry = [];
    if (title == 'File a Claim') {
      routesToTry = [
        'FileClaim',
        'fileClaim',
        'file_claim',
        'FileAClaim',
        'Claim',
        'claim',
        'Claims',
        'claims'
      ];
    } else if (title == 'Care Records') {
      // FF page names vary in case — try the common variants the Dart
      // class name and route annotations might use.
      routesToTry = [
        'careRecords',
        'CareRecords',
        'care_records',
        'carerecords',
        'care',
        'Care',
        'records',
        'Records',
      ];
    } else if (title == 'My Pets') {
      routesToTry = [
        'petPro',
        'petProfiles',
        'PetProfiles',
        'pet_profiles',
        'pets',
        'Pets',
        'MyPets',
        'myPets',
      ];
    } else if (title == 'Vaccinations') {
      routesToTry = [
        'petVaccinations',
        'PetVaccinations',
        'pet_vaccinations',
        'vaccinations',
        'Vaccinations',
      ];
    } else if (title == 'Pet Medications') {
      routesToTry = [
        'petMedications',
        'PetMedications',
        'pet_medications',
        'petMeds',
        'PetMeds',
      ];
    } else if (title == 'Pet Symptom Checker') {
      routesToTry = [
        'petSymptomChecker',
        'PetSymptomChecker',
        'pet_symptom_checker',
        'petSymptom',
        'PetSymptom',
        'petSymptomCheck',
        'PetSymptomCheck',
      ];
    } else if (title == 'Pet Records') {
      routesToTry = [
        'petCareRecords',
        'PetCareRecords',
        'pet_care_records',
        'petRecords',
        'PetRecords',
        'pet_records',
      ];
    } else if (title == 'Weight Alerts') {
      routesToTry = [
        'petWeightAlerts',
        'PetWeightAlerts',
        'pet_weight_alerts',
        'weightAlerts',
        'WeightAlerts',
        'weight_alerts',
      ];
    } else if (title == 'File Pet Claim') {
      routesToTry = [
        'petFileClaim',
        'PetFileClaim',
        'pet_file_claim',
        'petClaim',
        'PetClaim',
        'filePetClaim',
        'FilePetClaim',
      ];
    } else if (title == 'Fitness') {
      // Match the same belt-and-suspenders pattern used by pet routes.
      // FF page names are usually what we set them to, but if a page
      // gets renamed to a different case we fall through variants.
      routesToTry = [
        'fitnessHome',
        'FitnessHome',
        'fitness_home',
        'fitness',
        'Fitness',
      ];
    } else {
      routesToTry = [route];
    }

    bool navigationSuccessful = false;
    String? lastError;

    for (String routeToTry in routesToTry) {
      // IMPORTANT: only attempt ONE navigation per route name.
      // context.pushNamed / context.push don't throw synchronously on
      // misconfigured routes, so a try/catch can think the first call
      // failed while it actually queued the navigation — a second call
      // then pushes a duplicate page and Flutter's navigator asserts on
      // duplicate page keys.
      //
      // Try the path-based style (what current FF routing uses).
      try {
        final path = routeToTry.startsWith('/') ? routeToTry : '/$routeToTry';
        context.push(path);
        navigationSuccessful = true;
        debugPrint('Successfully navigated: $path');
        break;
      } catch (e) {
        lastError = e.toString();
        debugPrint('Failed context.push to /$routeToTry: $e');
        continue;
      }
    }

    if (!navigationSuccessful) {
      debugPrint('Navigation failed for $title; tried $routesToTry: $lastError');
      if (!mounted) return;
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(
          '$title isn\'t available right now.',
          accent: joviCoral,
          icon: CupertinoIcons.exclamationmark_circle));
    }
  }

  @override
  Widget build(BuildContext context) {
    String? userName;
    if (widget.displayName != null && widget.displayName!.isNotEmpty) {
      userName = widget.displayName;
    } else if (widget.firstName != null || widget.lastName != null) {
      userName = '${widget.firstName ?? ''} ${widget.lastName ?? ''}'.trim();
      if (userName.isEmpty) userName = null;
    }

    final screenWidth = MediaQuery.of(context).size.width;

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        statusBarBrightness: Brightness.dark,
      ),
      child: wrapWithConstraints(
        child: Container(
          width: widget.width ?? screenWidth,
          height: widget.height ?? MediaQuery.of(context).size.height,
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [joviNavy, joviNavy, joviNavyDark],
            ),
          ),
          child: Scaffold(
            key: scaffoldKey,
            backgroundColor: Colors.transparent,
            extendBodyBehindAppBar: true,
            appBar: AppBar(
              backgroundColor: Colors.transparent,
              elevation: 0,
              centerTitle: true,
              automaticallyImplyLeading: false,
              title: Text(
                'Account Menu',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 17,
                  fontWeight: FontWeight.w600,
                  letterSpacing: -0.4,
                ),
              ),
              actions: [
                Padding(
                  padding: EdgeInsets.only(right: 8),
                  child: Container(
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.08),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: Colors.white.withOpacity(0.15)),
                    ),
                    child: _Pressable(
                        feedbackOnly: true,
                        pressedScale: 0.92,
                        child: Material(
                      color: Colors.transparent,
                      child: InkWell(
                        borderRadius: BorderRadius.circular(12),
                        onTap: () {
                          HapticFeedback.lightImpact();
                          _navigateToRoute('userPro', 'Update Account');
                        },
                        child: Padding(
                          padding: EdgeInsets.all(11),
                          child: Icon(
                            Icons.settings_outlined,
                            color: Colors.white,
                            size: layoutSettings.iconSize * 1.1,
                          ),
                        ),
                      ),
                    )),
                  ),
                ),
              ],
              flexibleSpace: Container(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [joviNavy, joviNavyDark],
                  ),
                  border: Border(
                    bottom: BorderSide(
                      color: Colors.white.withOpacity(0.08),
                      width: 1,
                    ),
                  ),
                ),
              ),
            ),
            body: SafeArea(
              child: Center(
                child: Container(
                  constraints: BoxConstraints(
                    maxWidth: layoutSettings.contentMax,
                  ),
                  child: Column(
                    children: [
                      // ─── Glass user profile card ─────────────────
                      if (userName != null) _buildUserProfileCard(userName),

                      // ─── Glass search bar ────────────────────────
                      _buildSearchBar(),

                      // ─── Menu items ──────────────────────────────
                      Expanded(
                        child: searchQuery.isNotEmpty
                            ? _buildSearchResults()
                            : _buildCategoryMenu(),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildUserProfileCard(String userName) {
    return Padding(
      padding: EdgeInsets.fromLTRB(
        layoutSettings.paddingH,
        layoutSettings.paddingV * 0.5,
        layoutSettings.paddingH,
        0,
      ),
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(20),
          boxShadow: [
            BoxShadow(
              color: joviCoral.withOpacity(0.18),
              blurRadius: 24,
              offset: Offset(0, 8),
              spreadRadius: -4,
            ),
          ],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(20),
          child: RepaintBoundary(
            child: Container(
              padding: EdgeInsets.all(layoutSettings.paddingH),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.09),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: Colors.white.withOpacity(0.15),
                  width: 1,
                ),
              ),
              child: Row(
                children: [
                  // Profile photo with coral ring
                  Container(
                    padding: EdgeInsets.all(2.5),
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(
                        colors: [
                          Colors.white.withOpacity(0.4),
                          joviCoral.withOpacity(0.7),
                        ],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: joviCoral.withOpacity(0.35),
                          blurRadius: 12,
                          offset: Offset(0, 4),
                        ),
                      ],
                    ),
                    child: Container(
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: joviNavyDark,
                      ),
                      child: widget.sPhotoUrl != null &&
                              widget.sPhotoUrl!.isNotEmpty
                          ? CircleAvatar(
                              radius: layoutSettings.iconSize * 1.5,
                              backgroundImage: NetworkImage(widget.sPhotoUrl!),
                              backgroundColor: joviNavyDark,
                            )
                          : CircleAvatar(
                              radius: layoutSettings.iconSize * 1.5,
                              backgroundColor: joviNavyDark,
                              child: Icon(
                                Icons.person,
                                color: joviCoral,
                                size: layoutSettings.iconSize * 1.3,
                              ),
                            ),
                    ),
                  ),
                  SizedBox(width: layoutSettings.spacingUnit * 2),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          'Welcome back',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.55),
                            fontSize: layoutSettings.subtitleSize,
                            fontWeight: FontWeight.w500,
                            letterSpacing: 0.3,
                          ),
                        ),
                        SizedBox(height: 2),
                        Text(
                          userName,
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: layoutSettings.textSize * 1.2,
                            fontWeight: FontWeight.w700,
                            letterSpacing: -0.2,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        if (widget.email != null && widget.email!.isNotEmpty)
                          Padding(
                            padding: EdgeInsets.only(
                                top: layoutSettings.spacingUnit * 0.4),
                            child: Text(
                              widget.email!,
                              style: TextStyle(
                                color: Colors.white.withOpacity(0.5),
                                fontSize: layoutSettings.subtitleSize,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                      ],
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

  Widget _buildSearchBar() {
    return Padding(
      padding: EdgeInsets.all(layoutSettings.paddingH),
      child: Container(
        constraints: BoxConstraints(maxWidth: 800),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          boxShadow: _searchFocused
              ? [
                  BoxShadow(
                    color: joviCoral.withOpacity(0.25),
                    blurRadius: 16,
                    offset: Offset(0, 4),
                  ),
                ]
              : null,
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: RepaintBoundary(
            child: Container(
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.08),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: _searchFocused
                      ? joviCoral.withOpacity(0.5)
                      : Colors.white.withOpacity(0.12),
                  width: 1,
                ),
              ),
              child: TextField(
                controller: searchController,
                focusNode: _searchFocusNode,
                autocorrect: false,
                textInputAction: TextInputAction.search,
                style: TextStyle(
                    fontSize: layoutSettings.textSize, color: Colors.white),
                cursorColor: joviCoral,
                decoration: InputDecoration(
                  hintText: 'Search services',
                  hintStyle: TextStyle(
                    color: Colors.white.withOpacity(0.4),
                    fontSize: layoutSettings.textSize,
                  ),
                  prefixIcon: Icon(
                    Icons.search,
                    color: _searchFocused
                        ? joviCoral
                        : Colors.white.withOpacity(0.6),
                    size: layoutSettings.iconSize,
                  ),
                  suffixIcon: searchQuery.isNotEmpty
                      ? IconButton(
                          icon: Icon(
                            Icons.clear,
                            color: Colors.white.withOpacity(0.6),
                            size: layoutSettings.iconSize,
                          ),
                          onPressed: () {
                            searchController.clear();
                            FocusScope.of(context).unfocus();
                          },
                        )
                      : null,
                  border: InputBorder.none,
                  contentPadding: EdgeInsets.symmetric(
                    horizontal: layoutSettings.paddingH,
                    vertical: layoutSettings.paddingV * 0.8,
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildSearchResults() {
    final filteredItems = getFilteredItems();

    return ListView(
      padding: EdgeInsets.only(
        left: layoutSettings.paddingH,
        right: layoutSettings.paddingH,
        bottom: layoutSettings.paddingV,
      ),
      children: [
        Row(
          children: [
            Container(
              padding: EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: joviCoral.withOpacity(0.18),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: joviCoral.withOpacity(0.4)),
              ),
              child: Text(
                '${filteredItems.length} RESULT${filteredItems.length == 1 ? '' : 'S'}',
                style: TextStyle(
                  fontSize: layoutSettings.subtitleSize * 0.9,
                  fontWeight: FontWeight.w700,
                  color: joviCoral,
                  letterSpacing: 0.8,
                ),
              ),
            ),
          ],
        ),
        SizedBox(height: layoutSettings.spacingUnit * 1.5),
        if (filteredItems.isEmpty)
          Padding(
            padding: EdgeInsets.all(layoutSettings.paddingH * 2.5),
            child: Center(
              child: Column(
                children: [
                  Icon(
                    Icons.search_off,
                    color: Colors.white.withOpacity(0.3),
                    size: layoutSettings.iconSize * 3,
                  ),
                  SizedBox(height: layoutSettings.spacingUnit),
                  Text(
                    'No results found',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.6),
                      fontSize: layoutSettings.wideMode
                          ? layoutSettings.textSize * 1.1
                          : layoutSettings.textSize,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  SizedBox(height: 4),
                  Text(
                    'Try different keywords',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.35),
                      fontSize: layoutSettings.subtitleSize,
                    ),
                  ),
                ],
              ),
            ),
          )
        else
          ...filteredItems.asMap().entries.map((entry) {
            final i = entry.key;
            final item = entry.value;
            return _animatedMenuItem(item, i);
          }),
      ],
    );
  }

  Widget _buildCategoryMenu() {
    int globalIndex = 0;
    return ListView(
      padding: EdgeInsets.only(
        left: layoutSettings.paddingH,
        right: layoutSettings.paddingH,
        bottom: layoutSettings.paddingV,
      ),
      children: menuCategories.entries.map((entry) {
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Category header with coral accent bar
            Padding(
              padding: EdgeInsets.fromLTRB(0, layoutSettings.spacingUnit * 1.5,
                  0, layoutSettings.spacingUnit),
              child: Row(
                children: [
                  Container(
                    width: 3,
                    height: layoutSettings.titleSize,
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
                  SizedBox(width: layoutSettings.spacingUnit * 1.25),
                  Text(
                    entry.key.toUpperCase(),
                    style: TextStyle(
                      fontSize: layoutSettings.subtitleSize,
                      fontWeight: FontWeight.w700,
                      color: Colors.white.withOpacity(0.6),
                      letterSpacing: 1.2,
                    ),
                  ),
                ],
              ),
            ),
            ...entry.value.map((item) {
              final widget = _animatedMenuItem(item, globalIndex);
              globalIndex++;
              return widget;
            }),
            SizedBox(height: layoutSettings.paddingV),
          ],
        );
      }).toList(),
    );
  }

  /// Wraps _buildMenuItem with a staggered fade+slide entrance animation
  Widget _animatedMenuItem(MenuItem item, int index) {
    // Stagger: each item starts 60ms after the previous, caps at 10 for performance
    final startFraction = (index * 0.06).clamp(0.0, 0.7);
    final endFraction = (startFraction + 0.4).clamp(0.0, 1.0);

    // One CurvedAnimation per item, not one per frame per item.
    final curve = CurvedAnimation(
      parent: _entranceController,
      curve: Interval(startFraction, endFraction, curve: _Motion.settle),
    );
    return AnimatedBuilder(
      animation: curve,
      builder: (context, child) {
        return Transform.translate(
          offset: Offset(0, 8 * (1.0 - curve.value)),
          child: Opacity(
            opacity: curve.value,
            child: child,
          ),
        );
      },
      child: Padding(
        padding:
            EdgeInsets.symmetric(vertical: layoutSettings.spacingUnit * 0.5),
        child: _buildMenuItem(item),
      ),
    );
  }

  Widget _buildMenuItem(MenuItem item) {
    return _Pressable(
        feedbackOnly: true,
        pressedScale: 0.985,
        child: Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () async {
          HapticFeedback.lightImpact();
          await _navigateToRoute(item.route, item.title);
        },
        borderRadius: BorderRadius.circular(16),
        splashColor: item.color.withOpacity(0.18),
        highlightColor: item.color.withOpacity(0.08),
        child: Container(
          constraints: BoxConstraints(
            minHeight: layoutSettings.itemMinHeight,
            maxHeight: layoutSettings.itemMaxHeight,
          ),
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
                padding: EdgeInsets.all(layoutSettings.paddingH * 0.8),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.08),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: Colors.white.withOpacity(0.12),
                    width: 1,
                  ),
                ),
                child: Row(
                  children: [
                    // Icon chip with tinted glow
                    Container(
                      width: layoutSettings.iconSize * 2.4,
                      height: layoutSettings.iconSize * 2.4,
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: [
                            item.color.withOpacity(0.25),
                            item.color.withOpacity(0.12),
                          ],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                        borderRadius: BorderRadius.circular(
                            layoutSettings.spacingUnit * 1.25),
                        border: Border.all(
                          color: item.color.withOpacity(0.3),
                          width: 1,
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: item.color.withOpacity(0.25),
                            blurRadius: 10,
                            offset: Offset(0, 3),
                          ),
                        ],
                      ),
                      child: Icon(
                        item.icon,
                        color: item.color,
                        size: layoutSettings.iconSize * 1.15,
                      ),
                    ),
                    SizedBox(width: layoutSettings.spacingUnit * 1.5),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisAlignment: MainAxisAlignment.center,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            item.title,
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: layoutSettings.textSize * 1.05,
                              fontWeight: FontWeight.w600,
                              height: 1.2,
                              letterSpacing: -0.1,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          SizedBox(height: layoutSettings.spacingUnit * 0.3),
                          Text(
                            item.subtitle,
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.55),
                              fontSize: layoutSettings.subtitleSize,
                              height: 1.3,
                            ),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ],
                      ),
                    ),
                    SizedBox(width: layoutSettings.spacingUnit),
                    Container(
                      padding: EdgeInsets.all(4),
                      decoration: BoxDecoration(
                        color: joviCoral.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Icon(
                        item.route.startsWith('http')
                            ? Icons.open_in_new
                            : Icons.chevron_right,
                        color: joviCoral,
                        size: layoutSettings.iconSize * 0.9,
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
}

class MenuItem {
  final IconData icon;
  final String title;
  final String subtitle;
  final String route;
  final Color color;

  MenuItem({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.route,
    required this.color,
  });
}
