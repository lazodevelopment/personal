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
import 'package:intl/intl.dart';
// Refined 2026-09-23: GoodRx price link + coupon flag; honors preferredPharmacyPlace.
// Refined 2026-09-22: Apple HIG pass (press feedback, no looping motion,
// painted glass in the list, navy toasts, null-safe refill dates).
import 'dart:ui';
import 'dart:ui' as ui_dart;
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:url_launcher/url_launcher.dart';

enum ScreenType { compact, medium, expanded, large }

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
  final double cardRadius;
  final double headerFontSize;
  final double subHeaderFontSize;

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
    required this.cardRadius,
    required this.headerFontSize,
    required this.subHeaderFontSize,
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

// ─── GoodRx (2026-09-23) ─────────────────────────────────────────────────
// GoodRx is a coupon, not a pharmacy: the prescription still goes to the
// member's pharmacy and they show the coupon at pickup. We link out to the
// public price page (no API or partnership needed) and record the member's
// intent on the refill so the care team knows not to run it through
// insurance. `paymentPreference` is 'goodrx_coupon' or 'insurance'.
String _goodRxUrl(String medicationName) {
  // "Lisinopril 10mg tablet" -> "lisinopril": GoodRx pages are keyed by
  // drug name; strength and form are chosen on their page.
  final words = medicationName
      .toLowerCase()
      .replaceAll(RegExp(r'\([^)]*\)'), ' ')
      .replaceAll(RegExp(r'[^a-z0-9\s-]'), ' ')
      .split(RegExp(r'\s+'))
      .where((w) => w.isNotEmpty)
      .takeWhile((w) => !RegExp(r'\d').hasMatch(w))
      .toList();
  final slug = words.join('-');
  if (slug.isEmpty) return 'https://www.goodrx.com/';
  return 'https://www.goodrx.com/$slug';
}

Future<void> _openGoodRx(BuildContext context, String medicationName) async {
  HapticFeedback.lightImpact();
  try {
    await launchUrl(Uri.parse(_goodRxUrl(medicationName)),
        mode: LaunchMode.externalApplication);
  } catch (e) {
    debugPrint('GoodRx open failed: $e');
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(
        'Could not open GoodRx',
        accent: const Color(0xFFE53935),
        icon: CupertinoIcons.exclamationmark_circle));
  }
}

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

class PremiumPrescriptionRefillWidget extends StatefulWidget {
  const PremiumPrescriptionRefillWidget({
    Key? key,
    this.width,
    this.height,
    this.userId,
  }) : super(key: key);

  final double? width;
  final double? height;
  final String? userId;

  @override
  State<PremiumPrescriptionRefillWidget> createState() =>
      _PremiumPrescriptionRefillWidgetState();
}

class _PremiumPrescriptionRefillWidgetState
    extends State<PremiumPrescriptionRefillWidget>
    with TickerProviderStateMixin {
  // ═══════════════════════════════════════════════════════════════
  // Jovi Brand Colors (navy + glass + coral)
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
  static const Color joviErrorRed = Color(0xFFE53935);

  ScreenType currentScreenType = ScreenType.compact;
  ResponsiveConfig layoutSettings = ResponsiveConfig(
    paddingH: 20,
    paddingV: 20,
    contentMax: double.infinity,
    actionColumns: 1,
    actionItemHeight: 105,
    actionIconDimension: 28,
    actionTextSize: 13,
    wideMode: false,
    hasHinge: false,
    cardRadius: 20,
    headerFontSize: 20,
    subHeaderFontSize: 18,
  );

  double? _lastScreenWidth;
  bool? _lastHasHinge;

  bool _isLoading = true;
  List<Map<String, dynamic>> _prescriptions = [];
  List<Map<String, dynamic>> _pharmacies = [];
  String? _selectedPharmacyId;
  String? _selectedPharmacyName;
  bool _isRefilling = false;
  bool _payWithGoodRx = false;
  String? _currentUserId;
  DateTime? _lastRefreshTime;

  late AnimationController _fadeController;
  late AnimationController _slideController;
  late AnimationController _pulseController;
  late Animation<double> _fadeAnimation;
  late Animation<Offset> _slideAnimation;
  late Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();
    _initializeAnimations();
    _getCurrentUser();
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
      ScreenType type, double width, bool hasHinge) {
    switch (type) {
      case ScreenType.expanded:
        return ResponsiveConfig(
          paddingH: 16,
          paddingV: 20,
          contentMax: double.infinity,
          actionColumns: width > 900 ? 2 : 1,
          actionItemHeight: 120,
          actionIconDimension: 36,
          actionTextSize: 15,
          wideMode: true,
          hasHinge: true,
          useTwoColumnLayout: width >= 900,
          cardRadius: 24,
          headerFontSize: 24,
          subHeaderFontSize: 20,
        );
      case ScreenType.large:
        return ResponsiveConfig(
          paddingH: 40,
          paddingV: 28,
          contentMax: double.infinity,
          actionColumns: 2,
          actionItemHeight: 125,
          actionIconDimension: 38,
          actionTextSize: 16,
          wideMode: true,
          hasHinge: false,
          useTwoColumnLayout: width >= 1100,
          cardRadius: 24,
          headerFontSize: 28,
          subHeaderFontSize: 22,
        );
      case ScreenType.medium:
        return ResponsiveConfig(
          paddingH: 20,
          paddingV: 24,
          contentMax: double.infinity,
          actionColumns: width >= 900 ? 2 : 1,
          actionItemHeight: 115,
          actionIconDimension: 32,
          actionTextSize: 14,
          wideMode: true,
          hasHinge: false,
          useTwoColumnLayout: width >= 900,
          cardRadius: 20,
          headerFontSize: 24,
          subHeaderFontSize: 20,
        );
      case ScreenType.compact:
      default:
        return ResponsiveConfig(
          paddingH: 20,
          paddingV: 20,
          contentMax: double.infinity,
          actionColumns: 1,
          actionItemHeight: width < 360 ? 95 : 105,
          actionIconDimension: width < 360 ? 24 : 28,
          actionTextSize: width < 360 ? 12 : 13,
          wideMode: false,
          hasHinge: false,
          useTwoColumnLayout: false,
          cardRadius: 20,
          headerFontSize: 20,
          subHeaderFontSize: 18,
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

  int _getGridColumnCount(BuildContext context) {
    return layoutSettings.actionColumns;
  }

  void _initializeAnimations() {
    _fadeController = AnimationController(
      vsync: this,
      duration: _Motion.enter,
    );
    _slideController = AnimationController(
      vsync: this,
      duration: _Motion.enter,
    );
    // The Overdue/Due Soon badge no longer breathes forever; colour and
    // copy already carry the urgency. Parked at rest.
    _pulseController = AnimationController(
      vsync: this,
      duration: Duration(seconds: 2),
    )..value = 0.0;

    _fadeAnimation = CurvedAnimation(
      parent: _fadeController,
      curve: Curves.easeOut,
    );
    _slideAnimation = Tween<Offset>(
      begin: _platformReduceMotion() ? Offset.zero : Offset(0, 0.06),
      end: Offset.zero,
    ).animate(CurvedAnimation(
      parent: _slideController,
      curve: _Motion.settle,
    ));
    _pulseAnimation = Tween<double>(
      begin: 1.0,
      end: 1.05,
    ).animate(CurvedAnimation(
      parent: _pulseController,
      curve: Curves.easeInOut,
    ));

    _fadeController.forward();
    _slideController.forward();
  }

  @override
  void dispose() {
    _fadeController.dispose();
    _slideController.dispose();
    _pulseController.dispose();
    super.dispose();
  }

  void _getCurrentUser() {
    final user = FirebaseAuth.instance.currentUser;
    if (user != null) {
      _currentUserId = widget.userId ?? user.uid;
      _loadUserData();
    } else {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _loadUserData() async {
    if (_currentUserId == null) return;

    setState(() => _isLoading = true);

    try {
      final userDoc = await FirebaseFirestore.instance
          .collection('users')
          .doc(_currentUserId)
          .get();

      if (userDoc.exists) {
        final userData = userDoc.data()!;
        _selectedPharmacyId = userData['preferredPharmacy'] as String?;
        _payWithGoodRx = userData['payWithGoodRx'] == true;
        // A non-partner pharmacy chosen in the Pharmacies screen.
        final place = userData['preferredPharmacyPlace'];
        if (_selectedPharmacyId == null && place is Map) {
          final placeId = (place['placeId'] as String?) ?? '';
          if (placeId.isNotEmpty) {
            _selectedPharmacyId = 'place:$placeId';
            _selectedPharmacyName = (place['name'] as String?) ?? 'Pharmacy';
          }
        }
      }

      await _loadPharmacies();
      await _loadPrescriptions();

      if (!mounted) return;
      setState(() {
        _lastRefreshTime = DateTime.now();
        _isLoading = false;
      });
    } catch (e) {
      debugPrint('Error loading user data: $e');
      if (!mounted) return;
      setState(() => _isLoading = false);
      _showErrorSnackBar('Failed to load prescription data');
    }
  }

  Future<void> _loadPharmacies() async {
    try {
      final pharmaciesSnapshot = await FirebaseFirestore.instance
          .collection('pharmacies')
          .where('isActive', isEqualTo: true)
          .orderBy('name')
          .get();

      _pharmacies = pharmaciesSnapshot.docs.map((doc) {
        final data = doc.data();
        return {
          'id': doc.id,
          'name': data['name'] ?? '',
          'address': data['address'] ?? {},
          'phone': data['phone'] ?? '',
          'hours': data['hours'] ?? {},
        };
      }).toList();

      if (_selectedPharmacyId != null &&
          _selectedPharmacyId!.startsWith('place:')) {
        // Name already set from preferredPharmacyPlace.
      } else if (_selectedPharmacyId != null) {
        final selectedPharmacy = _pharmacies.firstWhere(
          (pharmacy) => pharmacy['id'] == _selectedPharmacyId,
          orElse: () => {},
        );
        _selectedPharmacyName = selectedPharmacy['name'] ?? 'Select Pharmacy';
      } else if (_pharmacies.isNotEmpty) {
        _selectedPharmacyId = _pharmacies.first['id'];
        _selectedPharmacyName = _pharmacies.first['name'];
      }
    } catch (e) {
      debugPrint('Error loading pharmacies: $e');
    }
  }

  Future<void> _loadPrescriptions() async {
    if (_currentUserId == null) return;

    try {
      final prescriptionsSnapshot = await FirebaseFirestore.instance
          .collection('prescriptions')
          .where('userId', isEqualTo: _currentUserId)
          .where('status', whereIn: ['active', 'pending', 'completed']).get();

      List<Map<String, dynamic>> prescriptionsWithRefillStatus = [];

      for (var doc in prescriptionsSnapshot.docs) {
        final data = doc.data();
        // A prescription without a next-refill date used to crash the
        // whole list; treat it as due now instead.
        final nextRefillDate =
            (data['nextRefillDate'] as Timestamp?)?.toDate() ?? DateTime.now();
        final daysUntilRefill =
            nextRefillDate.difference(DateTime.now()).inDays;
        final lastRefilled = data['lastRefilled'] != null
            ? (data['lastRefilled'] as Timestamp).toDate()
            : null;

        bool canRequestRefill = true;
        int daysSinceLastRefill = 999;

        if (lastRefilled != null) {
          daysSinceLastRefill = DateTime.now().difference(lastRefilled).inDays;
          canRequestRefill = daysSinceLastRefill >= 30;
        }

        final refillsRemaining = data['refillsRemaining'] ?? 0;
        if (refillsRemaining <= 0) {
          canRequestRefill = false;
        }

        prescriptionsWithRefillStatus.add({
          'id': doc.id,
          'medicationName': data['medicationName'] ?? '',
          'dosage': data['dosage'] ?? '',
          'frequency': data['frequency'] ?? '',
          'prescribedBy': data['prescribedBy'] ?? '',
          'refillsRemaining': refillsRemaining,
          'totalRefills': data['totalRefills'] ?? 0,
          'daysSupply': data['daysSupply'] ?? 30,
          'nextRefillDate': nextRefillDate,
          'lastRefilled': lastRefilled,
          'status': data['status'] ?? 'active',
          'urgent': data['urgent'] ?? false,
          'rxNumber': data['rxNumber'] ?? '',
          'instructions': data['instructions'] ?? '',
          'category': data['category'] ?? '',
          'strength': data['strength'] ?? '',
          'lastFilledPharmacy': data['lastFilledPharmacy'] ?? '',
          'originalPharmacy': data['originalPharmacy'] ?? '',
          'daysUntilRefill': daysUntilRefill,
          'isOverdue': daysUntilRefill < 0,
          'canRequestRefill': canRequestRefill,
          'daysSinceLastRefill': daysSinceLastRefill,
        });
      }

      prescriptionsWithRefillStatus.sort((a, b) =>
          (a['nextRefillDate'] as DateTime)
              .compareTo(b['nextRefillDate'] as DateTime));

      _prescriptions = prescriptionsWithRefillStatus;
    } catch (e) {
      debugPrint('Error loading prescriptions: $e');
      if (_prescriptions.isEmpty) {
        return;
      }
      _showErrorSnackBar('Failed to load prescriptions');
    }
  }

  Future<void> _requestRefill(Map<String, dynamic> prescription) async {
    if (_selectedPharmacyId == null) {
      _showErrorSnackBar('Please select a pharmacy first');
      return;
    }

    final refillsRemaining = prescription['refillsRemaining'] as int;
    final daysSinceLastRefill = prescription['daysSinceLastRefill'] as int;

    if (refillsRemaining <= 0) {
      _showErrorSnackBar(
          'No refills remaining for this prescription. Contact your doctor for a new prescription.');
      return;
    }

    if (daysSinceLastRefill < 30) {
      final daysRemaining = 30 - daysSinceLastRefill;
      _showErrorSnackBar(
          'You can request a refill again in $daysRemaining day${daysRemaining == 1 ? '' : 's'}');
      return;
    }

    HapticFeedback.mediumImpact();
    setState(() => _isRefilling = true);

    try {
      await FirebaseFirestore.instance.collection('prescriptionRefills').add({
        'userId': _currentUserId,
        'prescriptionId': prescription['id'],
        'rxNumber': prescription['rxNumber'],
        'medicationName': prescription['medicationName'],
        'refillDate': Timestamp.now(),
        'requestedDate': Timestamp.now(),
        'pharmacyId': _selectedPharmacyId,
        'pharmacyName': _selectedPharmacyName,
        'status': 'requested',
        'refillMethod': 'app',
        'paymentPreference': _payWithGoodRx ? 'goodrx_coupon' : 'insurance',
        'payWithGoodRx': _payWithGoodRx,
        'refillNumber': (prescription['totalRefills'] - refillsRemaining) + 1,
        'createdAt': Timestamp.now(),
        'updatedAt': Timestamp.now(),
      });

      final nextRefillDate =
          DateTime.now().add(Duration(days: prescription['daysSupply'] ?? 30));

      await FirebaseFirestore.instance
          .collection('prescriptions')
          .doc(prescription['id'])
          .update({
        'refillsRemaining': refillsRemaining - 1,
        'lastRefilled': Timestamp.now(),
        'lastFilledPharmacy': _selectedPharmacyName,
        'nextRefillDate': Timestamp.fromDate(nextRefillDate),
        'status': refillsRemaining - 1 > 0 ? 'active' : 'completed',
        'updatedAt': Timestamp.now(),
      });

      await _loadPrescriptions();

      if (!mounted) return;
      setState(() => _isRefilling = false);

      final remainingAfterRefill = refillsRemaining - 1;
      String message =
          'Refill request sent for ${prescription['medicationName']}';

      if (remainingAfterRefill > 0) {
        message +=
            '\n$remainingAfterRefill refill${remainingAfterRefill == 1 ? '' : 's'} remaining';
      } else {
        message +=
            '\nThis was your last refill. Contact your doctor for a new prescription.';
      }

      _showSuccessSnackBar(message);
    } catch (e) {
      if (!mounted) return;
      setState(() => _isRefilling = false);
      debugPrint('Error requesting refill: $e');
      _showErrorSnackBar('Failed to request refill. Please try again.');
    }
  }

  Future<void> _updatePreferredPharmacy(String pharmacyId) async {
    if (_currentUserId == null) return;

    try {
      await FirebaseFirestore.instance
          .collection('users')
          .doc(_currentUserId)
          .update({
        'preferredPharmacy': pharmacyId,
        'preferredPharmacyPlace': FieldValue.delete(),
        'updatedAt': Timestamp.now(),
      });

      final selectedPharmacy = _pharmacies.firstWhere(
        (pharmacy) => pharmacy['id'] == pharmacyId,
      );

      if (!mounted) return;
      setState(() {
        _selectedPharmacyId = pharmacyId;
        _selectedPharmacyName = selectedPharmacy['name'];
      });
    } catch (e) {
      debugPrint('Error updating preferred pharmacy: $e');
      _showErrorSnackBar('Failed to update pharmacy preference');
    }
  }

  Future<void> _setPayWithGoodRx(bool value) async {
    HapticFeedback.selectionClick();
    setState(() => _payWithGoodRx = value);
    if (_currentUserId == null) return;
    try {
      await FirebaseFirestore.instance
          .collection('users')
          .doc(_currentUserId)
          .set({'payWithGoodRx': value}, SetOptions(merge: true));
    } catch (e) {
      debugPrint('payWithGoodRx save failed: $e');
    }
  }

  void _showSuccessSnackBar(String message) {
    if (!mounted) return;
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(message,
        accent: joviMint,
        icon: CupertinoIcons.checkmark_circle,
        duration: const Duration(seconds: 4)));
  }

  void _showErrorSnackBar(String message) {
    if (!mounted) return;
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(message,
        accent: joviErrorRed,
        icon: CupertinoIcons.exclamationmark_circle,
        duration: const Duration(seconds: 4)));
  }

  void _showPharmacySelector() {
    HapticFeedback.lightImpact();
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (context) => ClipRRect(
        borderRadius: BorderRadius.vertical(
            top: Radius.circular(layoutSettings.cardRadius)),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
          child: Container(
            padding: EdgeInsets.all(layoutSettings.paddingH),
            decoration: BoxDecoration(
              color: joviNavy.withOpacity(0.94),
              borderRadius: BorderRadius.vertical(
                  top: Radius.circular(layoutSettings.cardRadius)),
              border: Border(
                top: BorderSide(
                  color: Colors.white.withOpacity(0.15),
                  width: 1,
                ),
              ),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.3),
                  blurRadius: 20,
                  offset: Offset(0, -5),
                ),
              ],
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.3),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                SizedBox(height: layoutSettings.paddingV),
                Text(
                  'Select Pharmacy',
                  style: TextStyle(
                    fontSize: layoutSettings.subHeaderFontSize,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                    letterSpacing: 0.5,
                  ),
                ),
                SizedBox(height: layoutSettings.paddingV),
                if (_pharmacies.isEmpty)
                  Text('No pharmacies available',
                      style: TextStyle(
                          fontSize: layoutSettings.actionTextSize + 1,
                          color: Colors.white.withOpacity(0.7)))
                else
                  ..._pharmacies.map((pharmacy) {
                    final isSelected = pharmacy['id'] == _selectedPharmacyId;
                    return Container(
                      margin: EdgeInsets.symmetric(
                          vertical: layoutSettings.paddingV * 0.2),
                      child: Material(
                        color: Colors.transparent,
                        child: InkWell(
                          onTap: () {
                            HapticFeedback.lightImpact();
                            _updatePreferredPharmacy(pharmacy['id']);
                            Navigator.pop(context);
                          },
                          borderRadius: BorderRadius.circular(
                              layoutSettings.cardRadius * 0.6),
                          child: Container(
                            padding:
                                EdgeInsets.all(layoutSettings.paddingH * 0.8),
                            decoration: BoxDecoration(
                              gradient: isSelected
                                  ? LinearGradient(
                                      colors: [
                                        joviCoral.withOpacity(0.18),
                                        joviCoralDark.withOpacity(0.10),
                                      ],
                                    )
                                  : null,
                              color: isSelected
                                  ? null
                                  : Colors.white.withOpacity(0.06),
                              borderRadius: BorderRadius.circular(
                                  layoutSettings.cardRadius * 0.6),
                              border: Border.all(
                                color: isSelected
                                    ? joviCoral.withOpacity(0.5)
                                    : Colors.white.withOpacity(0.12),
                              ),
                            ),
                            child: Row(
                              children: [
                                Container(
                                  padding: EdgeInsets.all(
                                      layoutSettings.paddingH * 0.4),
                                  decoration: BoxDecoration(
                                    color: (isSelected
                                            ? joviCoral
                                            : Colors.white)
                                        .withOpacity(isSelected ? 0.25 : 0.10),
                                    borderRadius: BorderRadius.circular(
                                        layoutSettings.cardRadius * 0.4),
                                  ),
                                  child: Icon(
                                    Icons.local_pharmacy,
                                    color: isSelected
                                        ? joviCoral
                                        : Colors.white.withOpacity(0.7),
                                    size: layoutSettings.actionIconDimension *
                                        0.7,
                                  ),
                                ),
                                SizedBox(width: layoutSettings.paddingH * 0.6),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        pharmacy['name'],
                                        style: TextStyle(
                                          fontSize:
                                              layoutSettings.actionTextSize + 3,
                                          fontWeight: isSelected
                                              ? FontWeight.w600
                                              : FontWeight.w500,
                                          color: Colors.white,
                                        ),
                                      ),
                                      if (pharmacy['address']['street'] != null)
                                        Text(
                                          pharmacy['address']['street'],
                                          style: TextStyle(
                                            fontSize:
                                                layoutSettings.actionTextSize -
                                                    1,
                                            color:
                                                Colors.white.withOpacity(0.6),
                                          ),
                                        ),
                                    ],
                                  ),
                                ),
                                if (isSelected)
                                  Icon(
                                    Icons.check_circle,
                                    color: joviCoral,
                                    size: layoutSettings.actionIconDimension *
                                        0.7,
                                  ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    );
                  }),
                SizedBox(height: layoutSettings.paddingV * 0.6),
                // Any pharmacy works: the Pharmacies screen finds nearby
                // ones and sets them as the member's pharmacy.
                Material(
                  color: Colors.transparent,
                  child: InkWell(
                    onTap: () {
                      HapticFeedback.lightImpact();
                      Navigator.pop(context);
                      try {
                        context.pushNamed('pharmacies');
                      } catch (e) {
                        debugPrint('pharmacies route missing: $e');
                        _showErrorSnackBar('Pharmacies screen is not available yet');
                      }
                    },
                    borderRadius: BorderRadius.circular(
                        layoutSettings.cardRadius * 0.6),
                    child: Container(
                      padding: EdgeInsets.all(layoutSettings.paddingH * 0.8),
                      decoration: BoxDecoration(
                        color: joviMint.withOpacity(0.08),
                        borderRadius: BorderRadius.circular(
                            layoutSettings.cardRadius * 0.6),
                        border: Border.all(color: joviMint.withOpacity(0.35)),
                      ),
                      child: Row(
                        children: [
                          Icon(Icons.travel_explore_rounded,
                              color: joviMint,
                              size: layoutSettings.actionIconDimension * 0.7),
                          SizedBox(width: layoutSettings.paddingH * 0.6),
                          Expanded(
                            child: Text(
                              'Find pharmacies near me',
                              style: TextStyle(
                                fontSize: layoutSettings.actionTextSize + 3,
                                fontWeight: FontWeight.w600,
                                color: Colors.white,
                              ),
                            ),
                          ),
                          Icon(Icons.chevron_right_rounded,
                              color: joviMint,
                              size: layoutSettings.actionIconDimension * 0.8),
                        ],
                      ),
                    ),
                  ),
                ),
                SizedBox(height: layoutSettings.paddingV),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildPrescriptionCard(Map<String, dynamic> prescription, int index) {
    final isOverdue = prescription['isOverdue'] == true;
    final isUrgent = prescription['urgent'] == true;
    final daysUntil = prescription['daysUntilRefill'] as int;
    final canRequestRefill = prescription['canRequestRefill'] == true;

    // Accent color - use semantic colors for urgency, coral otherwise
    final accentColor = isOverdue
        ? joviErrorRed
        : isUrgent
            ? joviGold
            : joviCoral;

    return SlideTransition(
      position: Tween<Offset>(
        begin: _platformReduceMotion() ? Offset.zero : Offset(0.06, 0),
        end: Offset.zero,
      ).animate(CurvedAnimation(
        parent: _slideController,
        // Clamped: an unclamped Interval start past 1.0 asserted once a
        // member had more than ten prescriptions.
        curve: Interval((index * 0.06).clamp(0.0, 0.6), 1.0,
            curve: _Motion.settle),
      )),
      child: _Pressable(
          feedbackOnly: true,
          pressedScale: 0.985,
          child: Container(
        margin: EdgeInsets.only(bottom: layoutSettings.paddingV * 0.8),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.08),
          borderRadius: BorderRadius.circular(layoutSettings.cardRadius),
          border: Border.all(
            color: (isOverdue || isUrgent)
                ? accentColor.withOpacity(0.5)
                : Colors.white.withOpacity(0.12),
            width: (isOverdue || isUrgent) ? 1.5 : 1,
          ),
          boxShadow: [
            BoxShadow(
              color: (isOverdue || isUrgent)
                  ? accentColor.withOpacity(0.2)
                  : Colors.black.withOpacity(0.2),
              blurRadius: 15,
              offset: Offset(0, 8),
            ),
          ],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(layoutSettings.cardRadius),
          child: RepaintBoundary(
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: () => _showPrescriptionDetails(prescription),
                borderRadius: BorderRadius.circular(layoutSettings.cardRadius),
                child: Padding(
                  padding: EdgeInsets.all(layoutSettings.paddingH),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Container(
                            padding:
                                EdgeInsets.all(layoutSettings.paddingH * 0.6),
                            decoration: BoxDecoration(
                              gradient: LinearGradient(
                                colors: [
                                  accentColor.withOpacity(0.22),
                                  accentColor.withOpacity(0.10),
                                ],
                              ),
                              borderRadius: BorderRadius.circular(
                                  layoutSettings.cardRadius * 0.6),
                            ),
                            child: Icon(
                              Icons.medication,
                              color: accentColor,
                              size: layoutSettings.actionIconDimension * 0.85,
                            ),
                          ),
                          SizedBox(width: layoutSettings.paddingH * 0.8),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  prescription['medicationName'],
                                  style: TextStyle(
                                    fontSize: layoutSettings.subHeaderFontSize,
                                    fontWeight: FontWeight.bold,
                                    color: Colors.white,
                                    letterSpacing: 0.3,
                                  ),
                                ),
                                SizedBox(height: layoutSettings.paddingV * 0.2),
                                Text(
                                  '${prescription['dosage']} - ${prescription['frequency']}',
                                  style: TextStyle(
                                    color: Colors.white.withOpacity(0.65),
                                    fontSize: layoutSettings.actionTextSize + 1,
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          if (isOverdue || isUrgent)
                            AnimatedBuilder(
                              animation: _pulseAnimation,
                              builder: (context, child) {
                                return Transform.scale(
                                  scale: _pulseAnimation.value,
                                  child: Container(
                                    padding: EdgeInsets.symmetric(
                                        horizontal:
                                            layoutSettings.paddingH * 0.5,
                                        vertical:
                                            layoutSettings.paddingV * 0.3),
                                    decoration: BoxDecoration(
                                      color: accentColor.withOpacity(0.18),
                                      borderRadius: BorderRadius.circular(
                                          layoutSettings.cardRadius * 0.8),
                                      border: Border.all(
                                        color: accentColor.withOpacity(0.5),
                                      ),
                                      boxShadow: [
                                        BoxShadow(
                                          color: accentColor.withOpacity(0.25),
                                          blurRadius: 6,
                                          offset: Offset(0, 2),
                                        ),
                                      ],
                                    ),
                                    child: Text(
                                      isOverdue ? 'Overdue' : 'Due Soon',
                                      style: TextStyle(
                                        color: accentColor,
                                        fontSize:
                                            layoutSettings.actionTextSize - 1,
                                        fontWeight: FontWeight.w700,
                                        letterSpacing: 0.3,
                                      ),
                                    ),
                                  ),
                                );
                              },
                            ),
                        ],
                      ),
                      SizedBox(height: layoutSettings.paddingV),
                      Container(
                        padding: EdgeInsets.all(layoutSettings.paddingH * 0.8),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.05),
                          borderRadius: BorderRadius.circular(
                              layoutSettings.cardRadius * 0.8),
                          border:
                              Border.all(color: Colors.white.withOpacity(0.10)),
                        ),
                        child: Row(
                          children: [
                            Expanded(
                              child: _buildInfoColumn(
                                  'Refills Left',
                                  '${prescription['refillsRemaining']}',
                                  joviCoral),
                            ),
                            Container(
                              width: 1,
                              height: 40,
                              color: Colors.white.withOpacity(0.12),
                            ),
                            SizedBox(width: layoutSettings.paddingH * 0.8),
                            Expanded(
                              child: _buildInfoColumn(
                                'Next Refill',
                                daysUntil < 0
                                    ? 'Overdue'
                                    : daysUntil == 0
                                        ? 'Today'
                                        : daysUntil == 1
                                            ? 'Tomorrow'
                                            : '$daysUntil days',
                                daysUntil < 0
                                    ? joviErrorRed
                                    : daysUntil <= 3
                                        ? joviGold
                                        : Colors.white,
                              ),
                            ),
                            SizedBox(width: layoutSettings.paddingH * 0.8),
                            _Pressable(
                              enabled: !_isRefilling && canRequestRefill,
                              feedbackOnly: true,
                              pressedScale: 0.94,
                              child: Material(
                              color: Colors.transparent,
                              child: InkWell(
                                onTap: _isRefilling
                                    ? null
                                    : () {
                                        _requestRefill(prescription);
                                      },
                                borderRadius: BorderRadius.circular(
                                    layoutSettings.cardRadius * 0.6),
                                child: Container(
                                  padding: EdgeInsets.all(
                                      layoutSettings.paddingH * 0.7),
                                  decoration: BoxDecoration(
                                    gradient: LinearGradient(
                                      colors: !canRequestRefill
                                          ? [
                                              Colors.white.withOpacity(0.12),
                                              Colors.white.withOpacity(0.08),
                                            ]
                                          : _isRefilling
                                              ? [
                                                  Colors.white
                                                      .withOpacity(0.15),
                                                  Colors.white
                                                      .withOpacity(0.10),
                                                ]
                                              : [joviCoral, joviCoralDark],
                                    ),
                                    borderRadius: BorderRadius.circular(
                                        layoutSettings.cardRadius * 0.6),
                                    border: !canRequestRefill
                                        ? Border.all(
                                            color:
                                                Colors.white.withOpacity(0.15))
                                        : null,
                                    boxShadow: !canRequestRefill
                                        ? []
                                        : [
                                            BoxShadow(
                                              color: joviCoral.withOpacity(0.4),
                                              blurRadius: 10,
                                              offset: Offset(0, 4),
                                            ),
                                          ],
                                  ),
                                  child: _isRefilling
                                      ? SizedBox(
                                          width: layoutSettings
                                                  .actionIconDimension *
                                              0.65,
                                          height: layoutSettings
                                                  .actionIconDimension *
                                              0.65,
                                          child: CircularProgressIndicator(
                                            strokeWidth: 2,
                                            valueColor:
                                                AlwaysStoppedAnimation<Color>(
                                                    Colors.white),
                                          ),
                                        )
                                      : Icon(
                                          !canRequestRefill
                                              ? (prescription[
                                                          'refillsRemaining'] <=
                                                      0
                                                  ? Icons.priority_high
                                                  : Icons.schedule)
                                              : Icons.refresh,
                                          color: !canRequestRefill
                                              ? Colors.white.withOpacity(0.5)
                                              : Colors.white,
                                          size: layoutSettings
                                                  .actionIconDimension *
                                              0.7,
                                        ),
                                ),
                              ),
                            )),
                          ],
                        ),
                      ),
                      if (prescription['lastFilledPharmacy'] != null &&
                          prescription['lastFilledPharmacy']
                              .toString()
                              .isNotEmpty)
                        Container(
                          margin: EdgeInsets.only(
                              top: layoutSettings.paddingV * 0.6),
                          padding:
                              EdgeInsets.all(layoutSettings.paddingH * 0.6),
                          decoration: BoxDecoration(
                            color: joviCoral.withOpacity(0.08),
                            borderRadius: BorderRadius.circular(
                                layoutSettings.cardRadius * 0.6),
                            border:
                                Border.all(color: joviCoral.withOpacity(0.25)),
                          ),
                          child: Row(
                            children: [
                              Icon(
                                Icons.local_pharmacy,
                                color: joviCoral,
                                size: layoutSettings.actionIconDimension * 0.6,
                              ),
                              SizedBox(width: layoutSettings.paddingH * 0.4),
                              Text(
                                'Last filled at: ',
                                style: TextStyle(
                                  fontSize: layoutSettings.actionTextSize,
                                  color: Colors.white.withOpacity(0.6),
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                              Expanded(
                                child: Text(
                                  prescription['lastFilledPharmacy'],
                                  style: TextStyle(
                                    fontSize: layoutSettings.actionTextSize,
                                    color: Colors.white,
                                    fontWeight: FontWeight.w600,
                                  ),
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
        ),
      )),
    );
  }

  Widget _buildInfoColumn(String label, String value, Color valueColor) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: TextStyle(
            color: Colors.white.withOpacity(0.6),
            fontSize: layoutSettings.actionTextSize,
            fontWeight: FontWeight.w500,
            letterSpacing: 0.3,
          ),
        ),
        SizedBox(height: layoutSettings.paddingV * 0.3),
        Text(
          value,
          style: TextStyle(
            fontSize: layoutSettings.actionTextSize + 3,
            fontWeight: FontWeight.bold,
            color: valueColor,
            letterSpacing: 0.3,
          ),
        ),
      ],
    );
  }

  void _showPrescriptionDetails(Map<String, dynamic> prescription) {
    HapticFeedback.mediumImpact();

    showDialog(
      context: context,
      builder: (context) => Dialog(
        backgroundColor: Colors.transparent,
        child: ClipRRect(
          borderRadius: BorderRadius.circular(layoutSettings.cardRadius),
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
            child: Container(
              padding: EdgeInsets.all(layoutSettings.paddingH),
              constraints: BoxConstraints(
                  maxHeight: MediaQuery.of(context).size.height * 0.8,
                  maxWidth: layoutSettings.wideMode ? 600 : double.infinity),
              decoration: BoxDecoration(
                color: joviNavy.withOpacity(0.94),
                borderRadius: BorderRadius.circular(layoutSettings.cardRadius),
                border:
                    Border.all(color: Colors.white.withOpacity(0.15), width: 1),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.35),
                    blurRadius: 30,
                    offset: Offset(0, 15),
                  ),
                ],
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Prescription Details',
                        style: TextStyle(
                          fontSize: layoutSettings.subHeaderFontSize,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
                      IconButton(
                        onPressed: () {
                          HapticFeedback.lightImpact();
                          Navigator.pop(context);
                        },
                        icon: Icon(Icons.close,
                            color: Colors.white.withOpacity(0.7),
                            size: layoutSettings.actionIconDimension),
                      ),
                    ],
                  ),
                  SizedBox(height: layoutSettings.paddingV * 0.8),
                  Flexible(
                    child: SingleChildScrollView(
                      child: Column(
                        children: [
                          _buildDetailRow(
                              'Medication', prescription['medicationName']),
                          _buildDetailRow('Dosage',
                              '${prescription['dosage']} ${prescription['strength']}'),
                          _buildDetailRow(
                              'Frequency', prescription['frequency']),
                          _buildDetailRow(
                              'Prescribed By', prescription['prescribedBy']),
                          _buildDetailRow(
                              'RX Number', prescription['rxNumber']),
                          _buildDetailRow(
                              'Instructions', prescription['instructions']),
                          _buildDetailRow('Refills Remaining',
                              '${prescription['refillsRemaining']} of ${prescription['totalRefills']}'),
                          _buildDetailRow(
                              'Next Refill Date',
                              DateFormat.yMMMd()
                                  .format(prescription['nextRefillDate'])),
                          if (prescription['lastRefilled'] != null)
                            _buildDetailRow(
                                'Last Refilled',
                                DateFormat.yMMMd()
                                    .format(prescription['lastRefilled'])),
                          if (prescription['lastFilledPharmacy'] != null &&
                              prescription['lastFilledPharmacy']
                                  .toString()
                                  .isNotEmpty)
                            _buildDetailRow('Last Filled At',
                                prescription['lastFilledPharmacy']),
                          if (prescription['originalPharmacy'] != null &&
                              prescription['originalPharmacy']
                                  .toString()
                                  .isNotEmpty)
                            _buildDetailRow('Original Pharmacy',
                                prescription['originalPharmacy']),
                          if (!prescription['canRequestRefill'])
                            _buildDetailRow(
                              'Next Refill Available',
                              prescription['refillsRemaining'] <= 0
                                  ? 'Contact your doctor for a new prescription'
                                  : prescription['lastRefilled'] == null
                                      ? 'Contact your pharmacy'
                                      : DateFormat.yMMMd().format(
                                          (prescription['lastRefilled']
                                                  as DateTime)
                                              .add(Duration(days: 30))),
                            ),
                        ],
                      ),
                    ),
                  ),
                  SizedBox(height: layoutSettings.paddingV * 0.8),
                  _Pressable(
                    feedbackOnly: true,
                    child: Material(
                      color: Colors.transparent,
                      child: InkWell(
                        onTap: () => _openGoodRx(
                            context, '${prescription['medicationName'] ?? ''}'),
                        borderRadius: BorderRadius.circular(
                            layoutSettings.cardRadius * 0.6),
                        child: Container(
                          width: double.infinity,
                          padding: EdgeInsets.symmetric(
                              vertical: layoutSettings.paddingV * 0.65,
                              horizontal: layoutSettings.paddingH * 0.8),
                          decoration: BoxDecoration(
                            color: joviGold.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(
                                layoutSettings.cardRadius * 0.6),
                            border:
                                Border.all(color: joviGold.withOpacity(0.35)),
                          ),
                          child: Row(
                            children: [
                              Icon(CupertinoIcons.tag_fill,
                                  color: joviGold,
                                  size: layoutSettings.actionIconDimension *
                                      0.65),
                              SizedBox(width: layoutSettings.paddingH * 0.5),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Text(
                                      'Check GoodRx price',
                                      style: TextStyle(
                                        fontSize:
                                            layoutSettings.actionTextSize + 2,
                                        fontWeight: FontWeight.w600,
                                        color: Colors.white,
                                        letterSpacing: -0.2,
                                      ),
                                    ),
                                    Text(
                                      'Compare cash prices nearby and show the coupon at pickup',
                                      style: TextStyle(
                                        fontSize: layoutSettings.actionTextSize,
                                        color: Colors.white.withOpacity(0.6),
                                        fontWeight: FontWeight.w500,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              Icon(CupertinoIcons.arrow_up_right_square,
                                  color: joviGold.withOpacity(0.8),
                                  size: layoutSettings.actionIconDimension *
                                      0.6),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
                  if (!prescription['canRequestRefill'])
                    Container(
                      width: double.infinity,
                      margin:
                          EdgeInsets.only(top: layoutSettings.paddingV * 0.8),
                      padding: EdgeInsets.symmetric(
                          vertical: layoutSettings.paddingV * 0.7),
                      decoration: BoxDecoration(
                        color: prescription['refillsRemaining'] <= 0
                            ? joviErrorRed.withOpacity(0.12)
                            : joviGold.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(
                            layoutSettings.cardRadius * 0.6),
                        border: Border.all(
                            color: prescription['refillsRemaining'] <= 0
                                ? joviErrorRed.withOpacity(0.4)
                                : joviGold.withOpacity(0.4)),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                              prescription['refillsRemaining'] <= 0
                                  ? Icons.priority_high
                                  : Icons.schedule,
                              color: prescription['refillsRemaining'] <= 0
                                  ? joviErrorRed
                                  : joviGold,
                              size: layoutSettings.actionIconDimension * 0.7),
                          SizedBox(width: layoutSettings.paddingH * 0.4),
                          Flexible(
                            child: Text(
                              prescription['refillsRemaining'] <= 0
                                  ? 'No refills remaining - Contact your doctor'
                                  : 'Next refill available in ${30 - prescription['daysSinceLastRefill']} day${30 - prescription['daysSinceLastRefill'] == 1 ? '' : 's'}',
                              style: TextStyle(
                                fontSize: layoutSettings.actionTextSize + 1,
                                color: prescription['refillsRemaining'] <= 0
                                    ? joviErrorRed
                                    : joviGold,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                        ],
                      ),
                    )
                  else
                    Container(
                      width: double.infinity,
                      margin:
                          EdgeInsets.only(top: layoutSettings.paddingV * 0.8),
                      child: ElevatedButton.icon(
                        onPressed: () {
                          Navigator.pop(context);
                          _requestRefill(prescription);
                        },
                        style: ElevatedButton.styleFrom(
                          backgroundColor: joviCoral,
                          foregroundColor: Colors.white,
                          padding: EdgeInsets.symmetric(
                              vertical: layoutSettings.paddingV * 0.7),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(
                                layoutSettings.cardRadius * 0.6),
                          ),
                          elevation: 3,
                          shadowColor: joviCoral.withOpacity(0.4),
                        ),
                        icon: Icon(Icons.refresh,
                            color: Colors.white,
                            size: layoutSettings.actionIconDimension * 0.8),
                        label: Text(
                          'Request Refill',
                          style: TextStyle(
                            fontSize: layoutSettings.actionTextSize + 3,
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                          ),
                        ),
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

  Widget _buildDetailRow(String label, String value) {
    return Padding(
      padding: EdgeInsets.symmetric(vertical: layoutSettings.paddingV * 0.4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: layoutSettings.wideMode ? 140 : 120,
            child: Text(
              label,
              style: TextStyle(
                fontSize: layoutSettings.actionTextSize + 1,
                color: Colors.white.withOpacity(0.6),
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: TextStyle(
                fontSize: layoutSettings.actionTextSize + 1,
                color: Colors.white,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatsCard() {
    final activeRx =
        _prescriptions.where((rx) => rx['status'] == 'active').length;
    final completedRx =
        _prescriptions.where((rx) => rx['status'] == 'completed').length;
    final urgentRx = _prescriptions
        .where((rx) => rx['urgent'] == true || rx['isOverdue'] == true)
        .length;
    final totalRefills = _prescriptions.fold<int>(
        0, (sum, rx) => sum + (rx['refillsRemaining'] as int));

    return FadeTransition(
      opacity: _fadeAnimation,
      child: Container(
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.07),
          borderRadius: BorderRadius.circular(layoutSettings.cardRadius),
          border: Border.all(color: Colors.white.withOpacity(0.12), width: 1),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.2),
              blurRadius: 15,
              offset: Offset(0, 8),
            ),
          ],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(layoutSettings.cardRadius),
          child: RepaintBoundary(
            child: Padding(
              padding: EdgeInsets.all(layoutSettings.paddingH),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Quick Overview',
                    style: TextStyle(
                      fontSize: layoutSettings.subHeaderFontSize,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                      letterSpacing: -0.3,
                    ),
                  ),
                  SizedBox(height: layoutSettings.paddingV * 0.8),
                  Row(
                    children: [
                      Expanded(
                          child: _buildStatItem('Active', '$activeRx',
                              Icons.medication, joviCoral)),
                      SizedBox(width: layoutSettings.paddingH * 0.8),
                      Expanded(
                          child: _buildStatItem('Refills Left', '$totalRefills',
                              Icons.repeat, joviMint)),
                    ],
                  ),
                  SizedBox(height: layoutSettings.paddingV * 0.8),
                  Row(
                    children: [
                      Expanded(
                          child: _buildStatItem(
                              'Urgent',
                              '$urgentRx',
                              Icons.warning,
                              urgentRx > 0
                                  ? joviErrorRed
                                  : Colors.white.withOpacity(0.4))),
                      SizedBox(width: layoutSettings.paddingH * 0.8),
                      Expanded(
                          child: _buildStatItem(
                              'Completed',
                              '$completedRx',
                              Icons.check_circle,
                              completedRx > 0
                                  ? joviCoralLight
                                  : Colors.white.withOpacity(0.4))),
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

  Widget _buildStatItem(
      String label, String value, IconData icon, Color color) {
    return Container(
      padding: EdgeInsets.all(layoutSettings.paddingH * 0.8),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(layoutSettings.cardRadius * 0.6),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          Container(
            padding: EdgeInsets.all(layoutSettings.paddingH * 0.4),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [color.withOpacity(0.22), color.withOpacity(0.12)],
              ),
              borderRadius:
                  BorderRadius.circular(layoutSettings.cardRadius * 0.4),
            ),
            child: Icon(icon,
                color: color, size: layoutSettings.actionIconDimension * 0.65),
          ),
          SizedBox(width: layoutSettings.paddingH * 0.6),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  value,
                  style: TextStyle(
                    fontSize: layoutSettings.actionTextSize + 3,
                    fontWeight: FontWeight.bold,
                    color: color,
                  ),
                ),
                Text(
                  label,
                  style: TextStyle(
                    fontSize: layoutSettings.actionTextSize,
                    color: Colors.white.withOpacity(0.7),
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPharmacyCard() {
    return FadeTransition(
      opacity: _fadeAnimation,
      child: Container(
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.07),
          borderRadius: BorderRadius.circular(layoutSettings.cardRadius),
          border: Border.all(color: Colors.white.withOpacity(0.12), width: 1),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.2),
              blurRadius: 15,
              offset: Offset(0, 8),
            ),
          ],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(layoutSettings.cardRadius),
          child: RepaintBoundary(
            child: Padding(
              padding: EdgeInsets.all(layoutSettings.paddingH),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Preferred Pharmacy',
                    style: TextStyle(
                      fontSize: layoutSettings.subHeaderFontSize,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                      letterSpacing: -0.3,
                    ),
                  ),
                  SizedBox(height: layoutSettings.paddingV * 0.8),
                  _Pressable(
                      feedbackOnly: true,
                      child: Material(
                    color: Colors.transparent,
                    child: InkWell(
                      onTap: _showPharmacySelector,
                      borderRadius: BorderRadius.circular(
                          layoutSettings.cardRadius * 0.6),
                      child: Container(
                        padding: EdgeInsets.all(layoutSettings.paddingH * 0.8),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.06),
                          borderRadius: BorderRadius.circular(
                              layoutSettings.cardRadius * 0.6),
                          border:
                              Border.all(color: Colors.white.withOpacity(0.12)),
                        ),
                        child: Row(
                          children: [
                            Container(
                              padding:
                                  EdgeInsets.all(layoutSettings.paddingH * 0.4),
                              decoration: BoxDecoration(
                                gradient: LinearGradient(
                                  colors: [
                                    joviCoral.withOpacity(0.22),
                                    joviCoralDark.withOpacity(0.12),
                                  ],
                                ),
                                borderRadius: BorderRadius.circular(
                                    layoutSettings.cardRadius * 0.4),
                              ),
                              child: Icon(Icons.local_pharmacy,
                                  color: joviCoral,
                                  size:
                                      layoutSettings.actionIconDimension * 0.7),
                            ),
                            SizedBox(width: layoutSettings.paddingH * 0.6),
                            Expanded(
                              child: Text(
                                _selectedPharmacyName ?? 'Select Pharmacy',
                                style: TextStyle(
                                  fontSize: layoutSettings.actionTextSize + 3,
                                  fontWeight: FontWeight.w600,
                                  color: Colors.white,
                                ),
                              ),
                            ),
                            Icon(Icons.arrow_drop_down,
                                color: joviCoral,
                                size:
                                    layoutSettings.actionIconDimension * 0.85),
                          ],
                        ),
                      ),
                    ),
                  )),
                  SizedBox(height: layoutSettings.paddingV * 0.8),
                  Container(
                    padding: EdgeInsets.symmetric(
                        horizontal: layoutSettings.paddingH * 0.8,
                        vertical: layoutSettings.paddingV * 0.35),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.06),
                      borderRadius:
                          BorderRadius.circular(layoutSettings.cardRadius * 0.6),
                      border: Border.all(color: Colors.white.withOpacity(0.12)),
                    ),
                    child: Row(
                      children: [
                        Icon(CupertinoIcons.tag_fill,
                            color: joviGold,
                            size: layoutSettings.actionIconDimension * 0.6),
                        SizedBox(width: layoutSettings.paddingH * 0.5),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                'Pay with a GoodRx coupon',
                                style: TextStyle(
                                  fontSize: layoutSettings.actionTextSize + 2,
                                  fontWeight: FontWeight.w600,
                                  color: Colors.white,
                                  letterSpacing: -0.2,
                                ),
                              ),
                              Text(
                                _payWithGoodRx
                                    ? 'Refills are sent as cash price. Show the coupon at pickup.'
                                    : 'Refills run through your plan.',
                                style: TextStyle(
                                  fontSize: layoutSettings.actionTextSize,
                                  color: Colors.white.withOpacity(0.6),
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ],
                          ),
                        ),
                        Switch.adaptive(
                          value: _payWithGoodRx,
                          activeColor: joviGold,
                          onChanged: _setPayWithGoodRx,
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

  Widget _buildEmptyState() {
    return Center(
      child: Container(
        constraints:
            BoxConstraints(maxWidth: layoutSettings.wideMode ? 500 : 400),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: EdgeInsets.all(layoutSettings.paddingH),
              decoration: BoxDecoration(
                color: joviCoral.withOpacity(0.15),
                shape: BoxShape.circle,
                border: Border.all(color: joviCoral.withOpacity(0.3)),
              ),
              child: Icon(
                Icons.medication_outlined,
                size: layoutSettings.wideMode ? 80 : 64,
                color: joviCoral,
              ),
            ),
            SizedBox(height: layoutSettings.paddingV),
            Text(
              'No Prescriptions Found',
              style: TextStyle(
                fontSize: layoutSettings.subHeaderFontSize,
                fontWeight: FontWeight.bold,
                color: Colors.white,
              ),
            ),
            SizedBox(height: layoutSettings.paddingV * 0.4),
            Padding(
              padding:
                  EdgeInsets.symmetric(horizontal: layoutSettings.paddingH * 2),
              child: Text(
                'Your prescriptions will appear here once you have them added to your account.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: layoutSettings.actionTextSize + 3,
                  color: Colors.white.withOpacity(0.7),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPrescriptionGrid() {
    final columnCount = _getGridColumnCount(context);

    if (columnCount == 1) {
      return Column(
        children: _prescriptions
            .asMap()
            .entries
            .map((entry) => _buildPrescriptionCard(entry.value, entry.key))
            .toList(),
      );
    }

    return LayoutBuilder(
      builder: (context, constraints) {
        return Wrap(
          spacing: layoutSettings.paddingH * 0.8,
          runSpacing: layoutSettings.paddingV * 0.8,
          children: _prescriptions.asMap().entries.map((entry) {
            return Container(
              width: (constraints.maxWidth -
                      (columnCount - 1) * layoutSettings.paddingH * 0.8) /
                  columnCount,
              child: _buildPrescriptionCard(entry.value, entry.key),
            );
          }).toList(),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        statusBarBrightness: Brightness.dark,
      ),
      child: wrapWithConstraints(
        child: Container(
          width: widget.width ?? MediaQuery.of(context).size.width,
          height: widget.height ?? MediaQuery.of(context).size.height,
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [joviNavy, joviNavy, joviNavyDark],
            ),
          ),
          child: Scaffold(
            backgroundColor: Colors.transparent,
            extendBodyBehindAppBar: true,
            appBar: AppBar(
              backgroundColor: Colors.transparent,
              elevation: 0,
              centerTitle: true,
              title: Text(
                'Prescription Refills',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 17,
                  fontWeight: FontWeight.w600,
                  letterSpacing: -0.4,
                ),
              ),
              leading: IconButton(
                icon: Icon(Icons.arrow_back,
                    color: Colors.white,
                    size: layoutSettings.actionIconDimension),
                onPressed: () {
                  HapticFeedback.lightImpact();
                  context.pop();
                },
              ),
              actions: [
                IconButton(
                  icon: Icon(Icons.refresh,
                      color: Colors.white,
                      size: layoutSettings.actionIconDimension),
                  onPressed: () {
                    HapticFeedback.mediumImpact();
                    _loadUserData();
                  },
                ),
              ],
              flexibleSpace: Container(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      joviNavy.withOpacity(0.85),
                      joviNavyDark.withOpacity(0.85)
                    ],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  border: Border(
                    bottom: BorderSide(
                      color: Colors.white.withOpacity(0.08),
                      width: 1,
                    ),
                  ),
                ),
                child: BackdropFilter(
                  filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
                  child: Container(color: Colors.transparent),
                ),
              ),
            ),
            body: RefreshIndicator(
              onRefresh: _loadUserData,
              color: joviCoral,
              backgroundColor: joviNavy,
              child: _isLoading
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          CircularProgressIndicator(
                            color: joviCoral,
                            strokeWidth: 3,
                          ),
                          SizedBox(height: layoutSettings.paddingV * 0.8),
                          Text(
                            'Loading prescriptions…',
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.7),
                              fontSize: layoutSettings.actionTextSize + 3,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                    )
                  : _currentUserId == null
                      ? Center(
                          child: Text(
                            'Please sign in to view prescriptions',
                            style: TextStyle(
                                fontSize: layoutSettings.actionTextSize + 3,
                                color: Colors.white.withOpacity(0.7)),
                          ),
                        )
                      : SafeArea(
                          child: _prescriptions.isEmpty
                              ? _buildEmptyState()
                              : Center(
                                  child: Container(
                                    width: double.infinity,
                                    child: ListView(
                                      padding: EdgeInsets.all(
                                          layoutSettings.paddingH),
                                      children: [
                                        if (layoutSettings
                                            .useTwoColumnLayout) ...[
                                          Row(
                                            crossAxisAlignment:
                                                CrossAxisAlignment.start,
                                            children: [
                                              Expanded(
                                                  child: _buildStatsCard()),
                                              SizedBox(
                                                  width:
                                                      layoutSettings.paddingH),
                                              Expanded(
                                                  child: _buildPharmacyCard()),
                                            ],
                                          ),
                                        ] else ...[
                                          _buildStatsCard(),
                                          SizedBox(
                                              height: layoutSettings.paddingV),
                                          _buildPharmacyCard(),
                                        ],
                                        SizedBox(
                                            height: layoutSettings.paddingV),
                                        FadeTransition(
                                          opacity: _fadeAnimation,
                                          child: Text(
                                            'Your Prescriptions',
                                            style: TextStyle(
                                              fontSize: layoutSettings
                                                  .subHeaderFontSize,
                                              fontWeight: FontWeight.bold,
                                              color: Colors.white,
                                              letterSpacing: 0.5,
                                            ),
                                          ),
                                        ),
                                        SizedBox(
                                            height:
                                                layoutSettings.paddingV * 0.8),
                                        _buildPrescriptionGrid(),
                                        SizedBox(
                                            height: layoutSettings.paddingV),
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
}
