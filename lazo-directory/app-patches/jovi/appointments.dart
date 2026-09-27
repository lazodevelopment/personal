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

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:intl/intl.dart';
import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';
import 'package:url_launcher/url_launcher.dart';
import 'dart:ui' as ui_dart;

// Refined 2026-09-22: Apple HIG pass (press feedback, navy toasts,
// calendar-day date labels, Jovi Pass naming).

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

class AppointmentsWidget extends StatefulWidget {
  final double width;
  final double height;

  const AppointmentsWidget({
    Key? key,
    required this.width,
    required this.height,
  }) : super(key: key);

  @override
  _AppointmentsWidgetState createState() => _AppointmentsWidgetState();
}

class _AppointmentsWidgetState extends State<AppointmentsWidget>
    with TickerProviderStateMixin {
  // ═══════════════════════════════════════════════════════════════
  // Jovi Brand Colors (navy + glass + coral)
  // ═══════════════════════════════════════════════════════════════
  static const Color _brandPrimary = Color(0xFFFF6B4A); // joviCoral
  static const Color _brandDark = Color(0xFFE5583A); // joviCoralDark
  static const Color _brandLight = Color(0xFFFF8F73); // joviCoralLight

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
    actionColumns: 3,
    actionItemHeight: 105,
    actionIconDimension: 28,
    actionTextSize: 13,
    wideMode: false,
    hasHinge: false,
  );

  double? _lastScreenWidth;
  bool? _lastHasHinge;

  late TabController _tabController;
  late AnimationController _fadeController;
  late Animation<double> _fadeAnimation;

  String _searchQuery = '';
  final TextEditingController _searchController = TextEditingController();
  String? _filterType;
  String? _filterMode;

  Map<String, dynamic>? _selectedAppointment;
  bool _isLoading = false;

  // All three clinics to match RequestsFlowWidget
  final Map<String, Map<String, dynamic>> _clinicLocations = {
    'Littleton - Dakota Ridge': {
      'address': '13402 W Coal Mine Ave Suite 225',
      'city': 'Littleton',
      'state': 'CO',
      'zip': '80127',
      'fullAddress': '13402 W Coal Mine Ave Suite 225, Littleton, CO 80127',
      'lat': 39.5847,
      'lng': -105.1511,
      'phone': '(844) 774-5878',
    },
    'Scottsdale - Scottsdale Gateway': {
      'address': '9201 E Mountain View Rd Suite 220',
      'city': 'Scottsdale',
      'state': 'AZ',
      'zip': '85258',
      'fullAddress': '9201 E Mountain View Rd Suite 220, Scottsdale, AZ 85258',
      'lat': 33.5764,
      'lng': -111.8442,
      'phone': '(844) 774-5878',
    },
    'Dallas - Medical City Campus': {
      'address': '7777 Forest Ln., C-699',
      'city': 'Dallas',
      'state': 'TX',
      'zip': '75230',
      'fullAddress': '7777 Forest Ln., C-699, Dallas, TX 75230',
      'lat': 32.8618,
      'lng': -96.7586,
      'phone': '(844) 774-5878',
    },
    // Legacy key for backward compatibility with existing appointments
    'Littleton - Coal Mine': {
      'address': '13402 W Coal Mine Ave Suite 225',
      'city': 'Littleton',
      'state': 'CO',
      'zip': '80127',
      'fullAddress': '13402 W Coal Mine Ave Suite 225, Littleton, CO 80127',
      'lat': 39.5847,
      'lng': -105.1511,
      'phone': '(844) 774-5878',
    },
  };

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);

    _fadeController = AnimationController(
      vsync: this,
      duration: _Motion.enter,
    );

    _fadeAnimation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _fadeController,
      curve: Curves.easeOut,
    ));

    _fadeController.forward();
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
          contentMax: double.infinity,
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
          constraints: BoxConstraints(maxWidth: layoutSettings.contentMax),
          child: child,
        ),
      );
    }
    return child;
  }

  @override
  void dispose() {
    _tabController.dispose();
    _fadeController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _launchMapNavigation(String clinicName) async {
    final clinicInfo = _clinicLocations[clinicName];
    if (clinicInfo == null) return;

    final lat = clinicInfo['lat'] as double;
    final lng = clinicInfo['lng'] as double;
    final clinicNameEncoded = Uri.encodeComponent(clinicName);

    final googleMapsUrl = Uri.parse(
        'https://www.google.com/maps/dir/?api=1&destination=$lat,$lng&destination_place_id=$clinicNameEncoded');

    final appleMapsUrl = Uri.parse(
        'https://maps.apple.com/?daddr=$lat,$lng&dirflg=d&q=$clinicNameEncoded');

    final universalUrl =
        Uri.parse('geo:$lat,$lng?q=$lat,$lng($clinicNameEncoded)');

    try {
      if (Theme.of(context).platform == TargetPlatform.iOS) {
        if (await canLaunchUrl(appleMapsUrl)) {
          await launchUrl(appleMapsUrl, mode: LaunchMode.externalApplication);
          return;
        }
      }

      if (await canLaunchUrl(googleMapsUrl)) {
        await launchUrl(googleMapsUrl, mode: LaunchMode.externalApplication);
        return;
      }

      if (await canLaunchUrl(universalUrl)) {
        await launchUrl(universalUrl, mode: LaunchMode.externalApplication);
        return;
      }

      _showSnackBar('Unable to open maps', isError: true);
    } catch (e) {
      _showSnackBar('Error opening maps: ${e.toString()}', isError: true);
    }
  }

  Future<void> _cancelAppointment(String appointmentId,
      {bool isPriority = false}) async {
    try {
      final appointmentDoc = await FirebaseFirestore.instance
          .collection('requests')
          .doc(appointmentId)
          .get();

      if (!appointmentDoc.exists) {
        _showSnackBar('Appointment not found', isError: true);
        return;
      }

      final appointmentData = appointmentDoc.data() as Map<String, dynamic>;

      if (!_isFutureAppointment(appointmentData['appointmentDate'])) {
        _showSnackBar(
          'Cannot cancel past appointments. This appointment has already occurred.',
          isError: true,
        );
        return;
      }
    } catch (e) {
      _showSnackBar('Error checking appointment: ${e.toString()}',
          isError: true);
      return;
    }

    // First confirmation - navy glass dialog
    final confirm = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (context) => Dialog(
        backgroundColor: Colors.transparent,
        child: ClipRRect(
          borderRadius: BorderRadius.circular(20),
          child: BackdropFilter(
            filter: ui_dart.ImageFilter.blur(sigmaX: 24, sigmaY: 24),
            child: Container(
              padding: EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: joviNavy.withOpacity(0.92),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: Colors.white.withOpacity(0.12),
                  width: 1,
                ),
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
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: joviErrorRed.withOpacity(0.18),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Icon(Icons.warning,
                            color: joviErrorRed,
                            size: layoutSettings.actionIconDimension),
                      ),
                      SizedBox(width: 12),
                      Text(
                        'Cancel Appointment',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
                    ],
                  ),
                  SizedBox(height: 16),
                  Text(
                    'Are you sure you want to cancel this appointment?',
                    style: TextStyle(
                      fontSize: layoutSettings.actionTextSize + 3,
                      color: Colors.white.withOpacity(0.85),
                    ),
                  ),
                  if (isPriority) ...[
                    SizedBox(height: 16),
                    Container(
                      padding: EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: joviGold.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: joviGold.withOpacity(0.4)),
                      ),
                      child: Row(
                        children: [
                          Icon(Icons.flash_on, color: joviGold, size: 20),
                          SizedBox(width: 8),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Jovi Pass Notice',
                                  style: TextStyle(
                                    fontWeight: FontWeight.bold,
                                    color: joviGold,
                                    fontSize: layoutSettings.actionTextSize + 1,
                                  ),
                                ),
                                SizedBox(height: 4),
                                Text(
                                  'Your Jovi Pass is non-refundable. The priority fee will not be returned if you cancel.',
                                  style: TextStyle(
                                    color: Colors.white.withOpacity(0.8),
                                    fontSize: layoutSettings.actionTextSize - 1,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                  SizedBox(height: 16),
                  Text(
                    'This appointment will become available for other patients.',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.6),
                      fontSize: layoutSettings.actionTextSize,
                      fontStyle: FontStyle.italic,
                    ),
                  ),
                  SizedBox(height: 20),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      TextButton(
                        onPressed: () => Navigator.of(context).pop(false),
                        style: TextButton.styleFrom(
                          foregroundColor: Colors.white.withOpacity(0.8),
                        ),
                        child: Text('Keep Appointment'),
                      ),
                      SizedBox(width: 8),
                      ElevatedButton(
                        onPressed: () => Navigator.of(context).pop(true),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: joviErrorRed,
                          foregroundColor: Colors.white,
                          elevation: 0,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10),
                          ),
                          padding: EdgeInsets.symmetric(
                              horizontal: 16, vertical: 12),
                        ),
                        child: Text(
                          'Cancel It',
                          style: TextStyle(color: Colors.white),
                        ),
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

    if (confirm != true || !mounted) return;

    // Second confirmation for Jovi Pass holders
    if (isPriority) {
      final secondConfirm = await showDialog<bool>(
        context: context,
        barrierDismissible: false,
        builder: (context) => Dialog(
          backgroundColor: Colors.transparent,
          child: ClipRRect(
            borderRadius: BorderRadius.circular(20),
            child: BackdropFilter(
              filter: ui_dart.ImageFilter.blur(sigmaX: 24, sigmaY: 24),
              child: Container(
                padding: EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: joviNavy.withOpacity(0.92),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: joviGold.withOpacity(0.3),
                    width: 1,
                  ),
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
                      children: [
                        Icon(Icons.flash_on,
                            color: joviGold,
                            size: layoutSettings.actionIconDimension),
                        SizedBox(width: 12),
                        Text(
                          'Final Confirmation',
                          style: TextStyle(
                            color: joviGold,
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                    SizedBox(height: 20),
                    Container(
                      padding: EdgeInsets.all(layoutSettings.paddingH * 0.8),
                      decoration: BoxDecoration(
                        color: joviGold.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                            color: joviGold.withOpacity(0.4), width: 2),
                      ),
                      child: Column(
                        children: [
                          Icon(Icons.attach_money,
                              color: joviGold,
                              size: layoutSettings.actionIconDimension + 20),
                          SizedBox(height: 12),
                          Text(
                            'Jovi Pass Fee Is Non-Refundable',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: layoutSettings.actionTextSize + 3,
                              color: joviGold,
                            ),
                          ),
                          SizedBox(height: 8),
                          Text(
                            'You paid \$49 for priority service.\nThis fee will NOT be refunded.',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontSize: layoutSettings.actionTextSize + 1,
                              color: Colors.white.withOpacity(0.85),
                            ),
                          ),
                        ],
                      ),
                    ),
                    SizedBox(height: 16),
                    Text(
                      'Are you absolutely sure you want to cancel?',
                      style: TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: layoutSettings.actionTextSize + 2,
                        color: Colors.white,
                      ),
                    ),
                    SizedBox(height: 20),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        TextButton(
                          onPressed: () => Navigator.of(context).pop(false),
                          style: TextButton.styleFrom(
                            foregroundColor: joviMint,
                            padding: EdgeInsets.symmetric(
                                horizontal: layoutSettings.paddingH,
                                vertical: 12),
                          ),
                          child: Text(
                            'No, Keep It',
                            style: TextStyle(
                              color: joviMint,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                        SizedBox(width: 8),
                        ElevatedButton(
                          onPressed: () => Navigator.of(context).pop(true),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: joviErrorRed,
                            foregroundColor: Colors.white,
                            padding: EdgeInsets.symmetric(
                                horizontal: layoutSettings.paddingH,
                                vertical: 12),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(10),
                            ),
                            elevation: 0,
                          ),
                          child: Text(
                            'Yes, Cancel Anyway',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              color: Colors.white,
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
        ),
      );

      if (secondConfirm != true) return;
    }

    // Loading overlay - navy glass
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => Center(
        child: ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: BackdropFilter(
            filter: ui_dart.ImageFilter.blur(sigmaX: 16, sigmaY: 16),
            child: Container(
              padding: EdgeInsets.all(layoutSettings.paddingH + 12),
              decoration: BoxDecoration(
                color: joviNavy.withOpacity(0.92),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: Colors.white.withOpacity(0.15),
                  width: 1,
                ),
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  CircularProgressIndicator(color: joviCoral),
                  SizedBox(height: 16),
                  Text(
                    'Cancelling appointment…',
                    style: TextStyle(
                      fontSize: layoutSettings.actionTextSize + 3,
                      color: Colors.white,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );

    try {
      final appointmentDoc = await FirebaseFirestore.instance
          .collection('requests')
          .doc(appointmentId)
          .get();

      if (!appointmentDoc.exists) {
        throw Exception('Appointment not found');
      }

      final appointmentData = appointmentDoc.data() as Map<String, dynamic>;

      await FirebaseFirestore.instance
          .collection('cancelled_appointments')
          .add({
        'originalAppointmentId': appointmentId,
        'userId': appointmentData['userId'],
        'patientName': appointmentData['patientName'],
        'appointmentDate': appointmentData['appointmentDate'],
        'appointmentTime': appointmentData['appointmentTime'],
        'visitType': appointmentData['visitType'],
        'visitMode': appointmentData['visitMode'],
        'clinic': appointmentData['clinic'],
        'symptom': appointmentData['symptom'],
        'wasPriority': isPriority,
        'cancelledAt': FieldValue.serverTimestamp(),
        'cancelledBy': FirebaseAuth.instance.currentUser?.uid,
      });

      final updateData = {
        'status': 'available',
        'previousStatus': appointmentData['status'],
        'userId': null,
        'patientName': null,
        'symptom': null,
        'symptomDuration': null,
        'details': null,
        'medication': null,
        'photoUrl': null,
        'priority': false,
        'kurvPassPurchased': false,
        'cancelledAt': FieldValue.serverTimestamp(),
        'cancelledBy': FirebaseAuth.instance.currentUser?.uid,
        'previousUserId': appointmentData['userId'],
        'appointmentDate': appointmentData['appointmentDate'],
        'appointmentTime': appointmentData['appointmentTime'],
        'visitType': appointmentData['visitType'],
        'visitMode': appointmentData['visitMode'],
        'clinic': appointmentData['clinic'],
        'estimatedWaitTime': appointmentData['estimatedWaitTime'],
      };

      if (appointmentData['visitMode'] == 'Clinic') {
        updateData['clinic'] = appointmentData['clinic'];
      }

      await FirebaseFirestore.instance
          .collection('requests')
          .doc(appointmentId)
          .update(updateData);

      if (isPriority) {
        await FirebaseFirestore.instance
            .collection('kurv_pass_cancellations')
            .add({
          'appointmentId': appointmentId,
          'userId': FirebaseAuth.instance.currentUser?.uid,
          'cancelledAt': FieldValue.serverTimestamp(),
          'appointmentDate': appointmentData['appointmentDate'],
          'appointmentTime': appointmentData['appointmentTime'],
          'visitType': appointmentData['visitType'],
          'visitMode': appointmentData['visitMode'],
          'clinic': appointmentData['clinic'],
          'nonRefundableAmount': 49.00,
          'patientName': appointmentData['patientName'],
        });
      }

      if (!mounted) return;
      Navigator.of(context).pop();

      _showSnackBar(
        isPriority
            ? 'Appointment cancelled. Your Jovi Pass fee (\$49) is non-refundable. The time slot is now available for other patients.'
            : 'Appointment cancelled successfully. The time slot is now available for other patients.',
        isSuccess: !isPriority,
        isInfo: isPriority,
      );

      setState(() => _selectedAppointment = null);
    } catch (e) {
      if (!mounted) return;
      Navigator.of(context).pop();
      _showSnackBar('Failed to cancel appointment: ${e.toString()}',
          isError: true);
    }
  }

  void _rescheduleAppointment(Map<String, dynamic> appointment) {
    final appointmentId = appointment['id'];
    if (appointmentId == null || appointmentId.toString().isEmpty) {
      _showSnackBar('Unable to reschedule: appointment ID missing',
          isError: true);
      return;
    }
    // Navigate to requests flow with reschedule parameter
    // The RequestsFlowWidget accepts a rescheduleRequestId parameter
    try {
      context.pushNamed(
        'requests',
        queryParameters: {'rescheduleRequestId': appointmentId.toString()},
      );
    } catch (e) {
      _showSnackBar('Reschedule navigation not configured yet', isInfo: true);
    }
  }

  void _showSnackBar(
    String message, {
    bool isError = false,
    bool isSuccess = false,
    bool isInfo = false,
  }) {
    if (!mounted) return;
    final accent = isError
        ? joviErrorRed
        : isSuccess
            ? joviMint
            : joviCoral;
    final icon = isError
        ? CupertinoIcons.exclamationmark_circle
        : isSuccess
            ? CupertinoIcons.checkmark_circle
            : CupertinoIcons.info_circle;
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(message,
        accent: accent,
        icon: icon,
        duration: Duration(seconds: isError || isInfo ? 5 : 3)));
  }

  Color _getStatusColor(String status) {
    switch (status.toLowerCase()) {
      case 'confirmed':
      case 'pending':
        return joviMint;
      case 'completed':
        return joviCoralLight;
      case 'cancelled':
        return joviErrorRed;
      case 'no-show':
        return joviGold;
      default:
        return Colors.white.withOpacity(0.5);
    }
  }

  String _statusLabel(String status) {
    final s = status.trim();
    if (s.isEmpty) return 'Pending';
    return s[0].toUpperCase() + s.substring(1).toLowerCase();
  }

  IconData _getStatusIcon(String status) {
    switch (status.toLowerCase()) {
      case 'confirmed':
        return Icons.check_circle;
      case 'pending':
        return Icons.schedule;
      case 'completed':
        return Icons.done_all;
      case 'cancelled':
        return Icons.cancel;
      case 'no-show':
        return Icons.warning;
      default:
        return Icons.info;
    }
  }

  bool _isFutureAppointment(dynamic dateStr) {
    if (dateStr == null) return false;

    try {
      DateTime appointmentDate;
      if (dateStr is String) {
        if (dateStr.contains('T')) {
          appointmentDate = DateTime.parse(dateStr);
        } else {
          appointmentDate = DateTime.parse(dateStr + 'T00:00:00');
        }
      } else {
        return false;
      }

      final now = DateTime.now();
      final todayStart = DateTime(now.year, now.month, now.day);
      final appointmentDay = DateTime(
          appointmentDate.year, appointmentDate.month, appointmentDate.day);

      return appointmentDay.isAfter(todayStart) ||
          appointmentDay.isAtSameMomentAs(todayStart);
    } catch (e) {
      debugPrint('Error parsing appointment date: $e');
      return false;
    }
  }

  String _formatDate(dynamic date) {
    if (date == null) return 'Date not set';

    DateTime dateTime;
    if (date is Timestamp) {
      dateTime = date.toDate();
    } else if (date is String) {
      try {
        if (date.contains('T')) {
          dateTime = DateTime.parse(date);
        } else {
          dateTime = DateFormat('yyyy-MM-dd').parse(date);
        }
      } catch (e) {
        return date;
      }
    } else {
      return 'Invalid date';
    }

    // Compare calendar days, not elapsed hours: an appointment stored as
    // tomorrow-at-midnight is 9 hours away at 3 pm and used to render as a
    // bare date instead of "Tomorrow".
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final day = DateTime(dateTime.year, dateTime.month, dateTime.day);
    final dayDiff = day.difference(today).inDays;

    if (dayDiff == 0) {
      return 'Today';
    } else if (dayDiff == 1) {
      return 'Tomorrow';
    } else if (dayDiff == -1) {
      return 'Yesterday';
    } else if (dayDiff > 1 && dayDiff < 7) {
      return DateFormat('EEEE').format(dateTime);
    } else {
      return DateFormat('MMM d, yyyy').format(dateTime);
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = FirebaseAuth.instance.currentUser;

    if (user == null) {
      return AnnotatedRegion<SystemUiOverlayStyle>(
        value: SystemUiOverlayStyle(
          statusBarColor: Colors.transparent,
          statusBarIconBrightness: Brightness.light,
          statusBarBrightness: Brightness.dark,
        ),
        child: wrapWithConstraints(
          child: Container(
            width: widget.width,
            height: widget.height,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [joviNavy, joviNavy, joviNavyDark],
              ),
            ),
            child: Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.lock,
                      size: layoutSettings.actionIconDimension + 36,
                      color: Colors.white.withOpacity(0.4)),
                  SizedBox(height: layoutSettings.paddingV * 0.8),
                  Text(
                    'Please sign in to view appointments',
                    style: TextStyle(
                      fontSize: layoutSettings.actionTextSize + 3,
                      color: Colors.white.withOpacity(0.7),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    }

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        statusBarBrightness: Brightness.dark,
      ),
      child: wrapWithConstraints(
        child: Container(
          width: widget.width,
          height: widget.height,
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [joviNavy, joviNavy, joviNavyDark],
            ),
          ),
          child: SafeArea(
            child: Column(
              children: [
                _buildHeader(),
                _buildSearchAndFilter(),
                _buildTabBar(),
                Expanded(
                  child: FadeTransition(
                    opacity: _fadeAnimation,
                    child: TabBarView(
                      controller: _tabController,
                      children: [
                        _buildAppointmentsList(isUpcoming: true),
                        _buildAppointmentsList(isUpcoming: false),
                      ],
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

  Widget _buildHeader() {
    return Container(
      padding: EdgeInsets.fromLTRB(
          layoutSettings.paddingH,
          layoutSettings.paddingV * 0.8,
          layoutSettings.paddingH,
          layoutSettings.paddingV),
      decoration: BoxDecoration(
        color: joviNavy,
        border: Border(
          bottom: BorderSide(
            color: Colors.white.withOpacity(0.08),
            width: 1,
          ),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.2),
            blurRadius: 10,
            offset: Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        children: [
          // Back button - coral gradient
          _Pressable(
              feedbackOnly: true,
              pressedScale: 0.92,
              child: Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [joviCoral, joviCoralDark],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(12),
              boxShadow: [
                BoxShadow(
                  color: joviCoral.withOpacity(0.4),
                  blurRadius: 8,
                  offset: Offset(0, 4),
                ),
              ],
            ),
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                borderRadius: BorderRadius.circular(12),
                onTap: () {
                  HapticFeedback.lightImpact();
                  if (Navigator.of(context).canPop()) {
                    Navigator.of(context).pop();
                  }
                },
                child: Padding(
                  padding: EdgeInsets.all(layoutSettings.paddingH * 0.6),
                  child: Icon(Icons.arrow_back_ios_new,
                      color: Colors.white,
                      size: layoutSettings.actionIconDimension * 0.8),
                ),
              ),
            ),
          )),
          Expanded(
            child: Column(
              children: [
                Text(
                  'My Appointments',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.4,
                    color: Colors.white,
                  ),
                ),
                Text(
                  'Manage your healthcare visits',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: layoutSettings.actionTextSize + 1,
                    color: Colors.white.withOpacity(0.65),
                  ),
                ),
              ],
            ),
          ),
          // New appointment button - coral gradient
          _Pressable(
              feedbackOnly: true,
              pressedScale: 0.92,
              child: Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [joviCoral, joviCoralDark],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(12),
              boxShadow: [
                BoxShadow(
                  color: joviCoral.withOpacity(0.4),
                  blurRadius: 8,
                  offset: Offset(0, 4),
                ),
              ],
            ),
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                borderRadius: BorderRadius.circular(12),
                onTap: () {
                  HapticFeedback.lightImpact();
                  context.pushNamed('requests');
                },
                child: Padding(
                  padding: EdgeInsets.all(layoutSettings.paddingH * 0.6),
                  child: Icon(Icons.add,
                      color: Colors.white,
                      size: layoutSettings.actionIconDimension),
                ),
              ),
            ),
          )),
        ],
      ),
    );
  }

  Widget _buildSearchAndFilter() {
    return Container(
      padding: EdgeInsets.all(layoutSettings.paddingH * 0.8),
      color: joviNavy,
      child: Column(
        children: [
          // Search bar - glass
          Container(
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.08),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.white.withOpacity(0.15)),
            ),
            child: TextField(
              controller: _searchController,
              autocorrect: false,
              textInputAction: TextInputAction.search,
              style: TextStyle(color: Colors.white),
              decoration: InputDecoration(
                hintText: 'Search appointments',
                hintStyle: TextStyle(
                  fontSize: layoutSettings.actionTextSize + 1,
                  color: Colors.white.withOpacity(0.4),
                ),
                prefixIcon: Icon(Icons.search,
                    color: joviCoral, size: layoutSettings.actionIconDimension),
                suffixIcon: _searchQuery.isNotEmpty
                    ? IconButton(
                        icon: Icon(Icons.clear,
                            color: Colors.white.withOpacity(0.6),
                            size: layoutSettings.actionIconDimension * 0.8),
                        onPressed: () {
                          setState(() {
                            _searchController.clear();
                            _searchQuery = '';
                          });
                        },
                      )
                    : null,
                border: InputBorder.none,
                contentPadding: EdgeInsets.symmetric(
                    horizontal: layoutSettings.paddingH * 0.8,
                    vertical: layoutSettings.paddingV * 0.7),
              ),
              onChanged: (value) {
                setState(() => _searchQuery = value.toLowerCase());
              },
            ),
          ),
          SizedBox(height: layoutSettings.paddingV * 0.6),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                _buildFilterChip(
                  'All Types',
                  _filterType == null,
                  () => setState(() => _filterType = null),
                ),
                SizedBox(width: layoutSettings.paddingH * 0.4),
                _buildFilterChip(
                  'Urgent Care',
                  _filterType == 'Urgent Care',
                  () => setState(() => _filterType =
                      _filterType == 'Urgent Care' ? null : 'Urgent Care'),
                ),
                SizedBox(width: layoutSettings.paddingH * 0.4),
                _buildFilterChip(
                  'Primary Care',
                  _filterType == 'Primary Care',
                  () => setState(() => _filterType =
                      _filterType == 'Primary Care' ? null : 'Primary Care'),
                ),
                SizedBox(width: layoutSettings.paddingH * 0.4),
                _buildFilterChip(
                  'Wellness',
                  _filterType == 'Wellness',
                  () => setState(() => _filterType =
                      _filterType == 'Wellness' ? null : 'Wellness'),
                ),
                SizedBox(width: layoutSettings.paddingH * 0.8),
                Container(
                  height: 24,
                  width: 1,
                  color: Colors.white.withOpacity(0.15),
                ),
                SizedBox(width: layoutSettings.paddingH * 0.8),
                _buildFilterChip(
                  'Clinic',
                  _filterMode == 'Clinic',
                  () => setState(() =>
                      _filterMode = _filterMode == 'Clinic' ? null : 'Clinic'),
                  icon: Icons.business,
                ),
                SizedBox(width: layoutSettings.paddingH * 0.4),
                _buildFilterChip(
                  'Virtual',
                  _filterMode == 'Virtual',
                  () => setState(() => _filterMode =
                      _filterMode == 'Virtual' ? null : 'Virtual'),
                  icon: Icons.video_call,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterChip(String label, bool isSelected, VoidCallback onTap,
      {IconData? icon}) {
    return _Pressable(
      onTap: () {
        HapticFeedback.selectionClick();
        onTap();
      },
      child: AnimatedContainer(
        duration: _Motion.select,
        curve: _Motion.settle,
        constraints: const BoxConstraints(minHeight: 36),
        padding: EdgeInsets.symmetric(
            horizontal: layoutSettings.paddingH * 0.8,
            vertical: layoutSettings.paddingV * 0.4),
        decoration: BoxDecoration(
          gradient: isSelected
              ? LinearGradient(
                  colors: [joviCoral, joviCoralDark],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                )
              : null,
          color: isSelected ? null : Colors.white.withOpacity(0.08),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: isSelected ? joviCoral : Colors.white.withOpacity(0.15),
            width: isSelected ? 2 : 1,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (icon != null) ...[
              Icon(
                icon,
                size: layoutSettings.actionIconDimension * 0.6,
                color:
                    isSelected ? Colors.white : Colors.white.withOpacity(0.65),
              ),
              SizedBox(width: layoutSettings.paddingH * 0.3),
            ],
            Text(
              label,
              style: TextStyle(
                color:
                    isSelected ? Colors.white : Colors.white.withOpacity(0.8),
                fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
                fontSize: layoutSettings.actionTextSize,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTabBar() {
    return Container(
      color: joviNavy,
      child: TabBar(
        controller: _tabController,
        labelColor: joviCoral,
        unselectedLabelColor: Colors.white.withOpacity(0.5),
        indicatorColor: joviCoral,
        indicatorWeight: 3,
        dividerColor: Colors.white.withOpacity(0.08),
        labelStyle: TextStyle(
            fontSize: layoutSettings.actionTextSize + 1,
            fontWeight: FontWeight.w600),
        unselectedLabelStyle:
            TextStyle(fontSize: layoutSettings.actionTextSize + 1),
        tabs: [
          Tab(
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.upcoming,
                    size: layoutSettings.actionIconDimension * 0.7),
                SizedBox(width: layoutSettings.paddingH * 0.4),
                Text('Upcoming'),
              ],
            ),
          ),
          Tab(
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.history,
                    size: layoutSettings.actionIconDimension * 0.7),
                SizedBox(width: layoutSettings.paddingH * 0.4),
                Text('Past'),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAppointmentsList({required bool isUpcoming}) {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return Container();

    return StreamBuilder<QuerySnapshot>(
      stream: FirebaseFirestore.instance
          .collection('requests')
          .where('userId', isEqualTo: user.uid)
          .snapshots(),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return Center(
            child: CircularProgressIndicator(color: joviCoral),
          );
        }

        if (snapshot.hasError) {
          if (snapshot.error.toString().contains('index')) {
            return Center(
              child: Padding(
                padding: EdgeInsets.all(layoutSettings.paddingH),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.info_outline,
                        size: layoutSettings.actionIconDimension + 36,
                        color: joviGold),
                    SizedBox(height: layoutSettings.paddingV * 0.8),
                    Text(
                      'Database Index Required',
                      style: TextStyle(
                        fontSize: layoutSettings.wideMode ? 18 : 16,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                      ),
                    ),
                    SizedBox(height: layoutSettings.paddingV * 0.4),
                    Text(
                      'Please create a Firestore index for this query.',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                          color: Colors.white.withOpacity(0.7),
                          fontSize: layoutSettings.actionTextSize + 1),
                    ),
                    SizedBox(height: layoutSettings.paddingV * 0.8),
                    Text(
                      'Go to Firebase Console > Firestore > Indexes',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                          fontSize: layoutSettings.actionTextSize - 1,
                          color: Colors.white.withOpacity(0.5)),
                    ),
                    SizedBox(height: layoutSettings.paddingV * 0.4),
                    Container(
                      padding: EdgeInsets.all(layoutSettings.paddingH * 0.6),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.08),
                        borderRadius: BorderRadius.circular(8),
                        border:
                            Border.all(color: Colors.white.withOpacity(0.12)),
                      ),
                      child: Column(
                        children: [
                          Text(
                            'Collection: requests',
                            style: TextStyle(
                                fontSize: layoutSettings.actionTextSize - 1,
                                fontFamily: 'monospace',
                                color: Colors.white.withOpacity(0.85)),
                          ),
                          Text(
                            'Fields: userId (Asc), appointmentDate (Desc)',
                            style: TextStyle(
                                fontSize: layoutSettings.actionTextSize - 1,
                                fontFamily: 'monospace',
                                color: Colors.white.withOpacity(0.85)),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            );
          }

          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.error_outline,
                    size: layoutSettings.actionIconDimension + 36,
                    color: joviErrorRed),
                SizedBox(height: layoutSettings.paddingV * 0.8),
                Text('Error loading appointments',
                    style: TextStyle(
                        fontSize: layoutSettings.actionTextSize + 2,
                        color: Colors.white)),
                Text(
                  snapshot.error.toString(),
                  style: TextStyle(
                      fontSize: layoutSettings.actionTextSize - 1,
                      color: Colors.white.withOpacity(0.5)),
                ),
              ],
            ),
          );
        }

        final docs = snapshot.data?.docs ?? [];

        final sortedDocs = List<QueryDocumentSnapshot>.from(docs);
        sortedDocs.sort((a, b) {
          final aData = a.data() as Map<String, dynamic>;
          final bData = b.data() as Map<String, dynamic>;

          final aDateStr = aData['appointmentDate'] as String?;
          final bDateStr = bData['appointmentDate'] as String?;

          if (aDateStr == null && bDateStr == null) return 0;
          if (aDateStr == null) return 1;
          if (bDateStr == null) return -1;

          try {
            final aDate = DateTime.parse(aDateStr);
            final bDate = DateTime.parse(bDateStr);
            return isUpcoming ? aDate.compareTo(bDate) : bDate.compareTo(aDate);
          } catch (e) {
            return 0;
          }
        });

        final now = DateTime.now();
        final filteredDocs = sortedDocs.where((doc) {
          final data = doc.data() as Map<String, dynamic>;
          final dateStr = data['appointmentDate'] as String?;
          if (dateStr == null || dateStr.isEmpty) return false;

          try {
            final appointmentDate = DateTime.parse(dateStr);
            if (isUpcoming) {
              return appointmentDate.isAfter(now) ||
                  (appointmentDate.year == now.year &&
                      appointmentDate.month == now.month &&
                      appointmentDate.day == now.day);
            } else {
              return appointmentDate.isBefore(now) &&
                  !(appointmentDate.year == now.year &&
                      appointmentDate.month == now.month &&
                      appointmentDate.day == now.day);
            }
          } catch (e) {
            return false;
          }
        }).toList();

        final appointments = filteredDocs.where((doc) {
          final data = doc.data() as Map<String, dynamic>;

          if (_searchQuery.isNotEmpty) {
            final searchFields = [
              data['symptom']?.toString().toLowerCase() ?? '',
              data['patientName']?.toString().toLowerCase() ?? '',
              data['visitType']?.toString().toLowerCase() ?? '',
              data['clinic']?.toString().toLowerCase() ?? '',
            ];

            if (!searchFields.any((field) => field.contains(_searchQuery))) {
              return false;
            }
          }

          if (_filterType != null && data['visitType'] != _filterType) {
            return false;
          }

          if (_filterMode != null && data['visitMode'] != _filterMode) {
            return false;
          }

          return true;
        }).toList();

        if (appointments.isEmpty) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  isUpcoming ? Icons.event_available : Icons.history,
                  size: layoutSettings.actionIconDimension + 36,
                  color: Colors.white.withOpacity(0.3),
                ),
                SizedBox(height: layoutSettings.paddingV * 0.8),
                Text(
                  isUpcoming
                      ? 'No upcoming appointments'
                      : 'No past appointments',
                  style: TextStyle(
                    fontSize: layoutSettings.wideMode ? 18 : 16,
                    fontWeight: FontWeight.w600,
                    color: Colors.white.withOpacity(0.7),
                  ),
                ),
                if (_searchQuery.isNotEmpty ||
                    _filterType != null ||
                    _filterMode != null) ...[
                  SizedBox(height: layoutSettings.paddingV * 0.4),
                  Text(
                    'Try adjusting your filters',
                    style: TextStyle(
                      fontSize: layoutSettings.actionTextSize + 1,
                      color: Colors.white.withOpacity(0.5),
                    ),
                  ),
                ],
                SizedBox(height: layoutSettings.paddingV * 1.2),
                if (isUpcoming)
                  ElevatedButton.icon(
                    onPressed: () {
                      HapticFeedback.lightImpact();
                      context.pushNamed('requests');
                    },
                    icon: Icon(Icons.add,
                        size: layoutSettings.actionIconDimension * 0.8),
                    label: Text('Request Appointment',
                        style: TextStyle(
                            fontSize: layoutSettings.actionTextSize + 1)),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: joviCoral,
                      foregroundColor: Colors.white,
                      padding: EdgeInsets.symmetric(
                          horizontal: layoutSettings.paddingH,
                          vertical: layoutSettings.paddingV * 0.6),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      elevation: 3,
                      shadowColor: joviCoral.withOpacity(0.4),
                    ),
                  ),
              ],
            ),
          );
        }

        return ListView.builder(
          padding: EdgeInsets.all(layoutSettings.paddingH * 0.8),
          itemCount: appointments.length,
          itemBuilder: (context, index) {
            final doc = appointments[index];
            final data = doc.data() as Map<String, dynamic>;
            data['id'] = doc.id;
            return _buildAppointmentCard(data);
          },
        );
      },
    );
  }

  Widget _buildAppointmentCard(Map<String, dynamic> appointment) {
    final status = appointment['status'] ?? 'pending';
    final isPriority = appointment['priority'] == true;
    final visitType = appointment['visitType'] ?? 'Unknown';
    final visitMode = appointment['visitMode'] ?? 'Unknown';
    final symptom = appointment['symptom'] ?? 'No reason specified';
    final dateStr = appointment['appointmentDate'] ?? '';
    final timeStr = appointment['appointmentTime'] ?? '';
    final clinic = appointment['clinic'] ?? '';
    final patientName = appointment['patientName'] ?? 'Patient';

    final statusColor = _getStatusColor(status);

    return _Pressable(
      onTap: () {
        HapticFeedback.selectionClick();
        setState(() => _selectedAppointment = appointment);
        _showAppointmentDetails(appointment);
      },
      child: Container(
        margin: EdgeInsets.only(bottom: layoutSettings.paddingV * 0.8),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.07),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: isPriority
                ? joviGold.withOpacity(0.5)
                : Colors.white.withOpacity(0.12),
            width: isPriority ? 2 : 1,
          ),
          boxShadow: [
            BoxShadow(
              color: isPriority
                  ? joviGold.withOpacity(0.15)
                  : Colors.black.withOpacity(0.15),
              blurRadius: 10,
              offset: Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          children: [
            // Header with status - tinted glass
            Container(
              padding: EdgeInsets.all(layoutSettings.paddingH * 0.8),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    statusColor.withOpacity(0.14),
                    statusColor.withOpacity(0.06),
                  ],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.only(
                  topLeft: Radius.circular(15),
                  topRight: Radius.circular(15),
                ),
                border: Border(
                  bottom: BorderSide(
                    color: Colors.white.withOpacity(0.08),
                    width: 1,
                  ),
                ),
              ),
              child: Row(
                children: [
                  Container(
                    padding: EdgeInsets.all(layoutSettings.paddingH * 0.5),
                    decoration: BoxDecoration(
                      color: statusColor.withOpacity(0.25),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Icon(
                      _getStatusIcon(status),
                      color: statusColor,
                      size: layoutSettings.actionIconDimension,
                    ),
                  ),
                  SizedBox(width: layoutSettings.paddingH * 0.6),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Text(
                              visitType,
                              style: TextStyle(
                                fontSize: layoutSettings.wideMode ? 18 : 16,
                                fontWeight: FontWeight.bold,
                                color: Colors.white,
                              ),
                            ),
                            if (isPriority) ...[
                              SizedBox(width: layoutSettings.paddingH * 0.4),
                              Container(
                                padding: EdgeInsets.symmetric(
                                    horizontal: layoutSettings.paddingH * 0.4,
                                    vertical: 2),
                                decoration: BoxDecoration(
                                  gradient: LinearGradient(
                                    colors: [joviGold, joviGoldDark],
                                  ),
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(Icons.flash_on,
                                        color: joviNavyDark,
                                        size:
                                            layoutSettings.actionIconDimension *
                                                0.4),
                                    SizedBox(width: 4),
                                    Text(
                                      'PRIORITY',
                                      style: TextStyle(
                                        color: joviNavyDark,
                                        fontSize:
                                            layoutSettings.actionTextSize - 3,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ],
                        ),
                        SizedBox(height: 4),
                        Text(
                          _statusLabel(status.toString()),
                          style: TextStyle(
                            fontSize: layoutSettings.actionTextSize - 1,
                            fontWeight: FontWeight.w600,
                            color: statusColor,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Icon(Icons.chevron_right,
                      color: Colors.white.withOpacity(0.4),
                      size: layoutSettings.actionIconDimension),
                ],
              ),
            ),

            // Body
            Padding(
              padding: EdgeInsets.all(layoutSettings.paddingH * 0.8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.calendar_today,
                          size: layoutSettings.actionIconDimension * 0.6,
                          color: joviCoral),
                      SizedBox(width: layoutSettings.paddingH * 0.4),
                      Text(
                        _formatDate(dateStr),
                        style: TextStyle(
                          fontWeight: FontWeight.w600,
                          color: Colors.white,
                          fontSize: layoutSettings.actionTextSize + 1,
                        ),
                      ),
                      if (timeStr.toString().isNotEmpty) ...[
                        SizedBox(width: layoutSettings.paddingH * 0.8),
                        Icon(Icons.access_time,
                            size: layoutSettings.actionIconDimension * 0.6,
                            color: joviCoral),
                        SizedBox(width: layoutSettings.paddingH * 0.4),
                        Text(
                          timeStr,
                          style: TextStyle(
                            fontWeight: FontWeight.w600,
                            color: Colors.white,
                            fontSize: layoutSettings.actionTextSize + 1,
                          ),
                        ),
                      ],
                    ],
                  ),
                  SizedBox(height: layoutSettings.paddingV * 0.6),
                  Row(
                    children: [
                      Icon(Icons.person,
                          size: layoutSettings.actionIconDimension * 0.6,
                          color: Colors.white.withOpacity(0.6)),
                      SizedBox(width: layoutSettings.paddingH * 0.4),
                      Text(
                        patientName,
                        style: TextStyle(
                            color: Colors.white.withOpacity(0.8),
                            fontSize: layoutSettings.actionTextSize + 1),
                      ),
                    ],
                  ),
                  SizedBox(height: layoutSettings.paddingV * 0.4),
                  Row(
                    children: [
                      Icon(Icons.healing,
                          size: layoutSettings.actionIconDimension * 0.6,
                          color: Colors.white.withOpacity(0.6)),
                      SizedBox(width: layoutSettings.paddingH * 0.4),
                      Expanded(
                        child: Text(
                          symptom,
                          style: TextStyle(
                              color: Colors.white.withOpacity(0.8),
                              fontSize: layoutSettings.actionTextSize + 1),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                  SizedBox(height: layoutSettings.paddingV * 0.6),
                  Container(
                    padding: EdgeInsets.symmetric(
                        horizontal: layoutSettings.paddingH * 0.6,
                        vertical: layoutSettings.paddingV * 0.3),
                    decoration: BoxDecoration(
                      color: visitMode == 'Virtual'
                          ? joviCoral.withOpacity(0.14)
                          : joviMint.withOpacity(0.14),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                        color: visitMode == 'Virtual'
                            ? joviCoral.withOpacity(0.4)
                            : joviMint.withOpacity(0.4),
                      ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          visitMode == 'Virtual'
                              ? Icons.video_call
                              : Icons.business,
                          size: layoutSettings.actionIconDimension * 0.6,
                          color: visitMode == 'Virtual' ? joviCoral : joviMint,
                        ),
                        SizedBox(width: layoutSettings.paddingH * 0.3),
                        Text(
                          visitMode == 'Virtual' ? 'Virtual Visit' : clinic,
                          style: TextStyle(
                            fontSize: layoutSettings.actionTextSize,
                            fontWeight: FontWeight.w600,
                            color:
                                visitMode == 'Virtual' ? joviCoral : joviMint,
                          ),
                        ),
                      ],
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

  void _showAppointmentDetails(Map<String, dynamic> appointment) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => ClipRRect(
        borderRadius: BorderRadius.only(
          topLeft: Radius.circular(24),
          topRight: Radius.circular(24),
        ),
        child: BackdropFilter(
          filter: ui_dart.ImageFilter.blur(sigmaX: 20, sigmaY: 20),
          child: Container(
            height: MediaQuery.of(context).size.height *
                (layoutSettings.wideMode ? 0.9 : 0.8),
            decoration: BoxDecoration(
              color: joviNavy.withOpacity(0.96),
              borderRadius: BorderRadius.only(
                topLeft: Radius.circular(24),
                topRight: Radius.circular(24),
              ),
              border: Border(
                top: BorderSide(
                  color: Colors.white.withOpacity(0.15),
                  width: 1,
                ),
              ),
            ),
            child: Column(
              children: [
                // Handle bar
                Container(
                  margin: EdgeInsets.only(top: layoutSettings.paddingV * 0.6),
                  width: layoutSettings.wideMode ? 50 : 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.3),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),

                // Header
                Container(
                  padding: EdgeInsets.all(layoutSettings.paddingH),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [
                        joviCoral.withOpacity(0.14),
                        joviCoralDark.withOpacity(0.06),
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
                  child: Row(
                    children: [
                      Container(
                        padding: EdgeInsets.all(layoutSettings.paddingH * 0.6),
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            colors: [joviCoral, joviCoralDark],
                          ),
                          borderRadius: BorderRadius.circular(12),
                          boxShadow: [
                            BoxShadow(
                              color: joviCoral.withOpacity(0.35),
                              blurRadius: 8,
                              offset: Offset(0, 4),
                            ),
                          ],
                        ),
                        child: Icon(
                          Icons.medical_information,
                          color: Colors.white,
                          size: layoutSettings.actionIconDimension,
                        ),
                      ),
                      SizedBox(width: layoutSettings.paddingH * 0.8),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Appointment Details',
                              style: TextStyle(
                                fontSize: layoutSettings.wideMode ? 20 : 18,
                                fontWeight: FontWeight.bold,
                                color: Colors.white,
                              ),
                            ),
                            Text(
                              'Ref ${(appointment['id']?.toString() ?? '').length >= 8 ? appointment['id'].toString().substring(0, 8).toUpperCase() : 'N/A'}',
                              style: TextStyle(
                                fontSize: layoutSettings.actionTextSize,
                                color: Colors.white.withOpacity(0.6),
                              ),
                            ),
                          ],
                        ),
                      ),
                      IconButton(
                        icon: Icon(Icons.close,
                            size: layoutSettings.actionIconDimension,
                            color: Colors.white.withOpacity(0.8)),
                        onPressed: () => Navigator.of(context).pop(),
                      ),
                    ],
                  ),
                ),

                // Content
                Expanded(
                  child: SingleChildScrollView(
                    padding: EdgeInsets.all(layoutSettings.paddingH),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _buildDetailSection(
                          'Appointment Information',
                          [
                            _buildDetailRow(
                                'Status',
                                _statusLabel(
                                    appointment['status']?.toString() ??
                                        'pending'),
                                color: _getStatusColor(
                                    appointment['status'] ?? 'pending')),
                            _buildDetailRow(
                                'Type', appointment['visitType'] ?? 'N/A'),
                            _buildDetailRow(
                                'Mode', appointment['visitMode'] ?? 'N/A'),
                            _buildDetailRow('Date',
                                _formatDate(appointment['appointmentDate'])),
                            _buildDetailRow('Time',
                                appointment['appointmentTime'] ?? 'N/A'),
                            if (appointment['priority'] == true)
                              _buildDetailRow('Priority', 'Jovi Pass Active',
                                  color: joviGold, icon: Icons.flash_on),
                          ],
                        ),
                        SizedBox(height: layoutSettings.paddingV),
                        _buildDetailSection(
                          'Patient Information',
                          [
                            _buildDetailRow(
                                'Name', appointment['patientName'] ?? 'N/A'),
                            _buildDetailRow(
                                'Reason', appointment['symptom'] ?? 'N/A'),
                            if (appointment['symptomDuration']
                                    ?.toString()
                                    .isNotEmpty ??
                                false)
                              _buildDetailRow('Duration',
                                  appointment['symptomDuration'] ?? ''),
                            if (appointment['details']?.toString().isNotEmpty ??
                                false)
                              _buildDetailRow(
                                  'Details', appointment['details'] ?? ''),
                          ],
                        ),
                        if (appointment['visitMode'] == 'Clinic' &&
                            appointment['clinic'] != null) ...[
                          SizedBox(height: layoutSettings.paddingV),
                          _buildDetailSection(
                            'Clinic Information',
                            [
                              _buildDetailRow(
                                  'Location', appointment['clinic'] ?? 'N/A'),
                              if (_clinicLocations[appointment['clinic']] !=
                                  null) ...[
                                _buildDetailRow(
                                    'Address',
                                    _clinicLocations[appointment['clinic']]![
                                            'fullAddress'] ??
                                        'N/A'),
                                _buildDetailRow(
                                    'Phone',
                                    _clinicLocations[appointment['clinic']]![
                                            'phone'] ??
                                        'N/A'),
                              ],
                            ],
                          ),
                        ],
                        SizedBox(height: layoutSettings.paddingV * 1.5),
                        if ((appointment['status'] == 'pending' ||
                                appointment['status'] == 'confirmed') &&
                            _isFutureAppointment(
                                appointment['appointmentDate'])) ...[
                          Row(
                            children: [
                              if (appointment['visitMode'] == 'Clinic' &&
                                  appointment['clinic'] != null)
                                Expanded(
                                  child: ElevatedButton.icon(
                                    onPressed: () {
                                      Navigator.of(context).pop();
                                      _launchMapNavigation(
                                          appointment['clinic']);
                                    },
                                    icon: Icon(Icons.directions,
                                        size:
                                            layoutSettings.actionIconDimension *
                                                0.8),
                                    label: Text('Get Directions',
                                        style: TextStyle(
                                            fontSize:
                                                layoutSettings.actionTextSize +
                                                    1)),
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: joviCoral,
                                      foregroundColor: Colors.white,
                                      padding: EdgeInsets.symmetric(
                                          vertical:
                                              layoutSettings.paddingV * 0.7),
                                      shape: RoundedRectangleBorder(
                                        borderRadius: BorderRadius.circular(12),
                                      ),
                                      elevation: 3,
                                      shadowColor: joviCoral.withOpacity(0.4),
                                    ),
                                  ),
                                ),
                              if (appointment['visitMode'] == 'Clinic')
                                SizedBox(width: layoutSettings.paddingH * 0.6),
                              Expanded(
                                child: OutlinedButton.icon(
                                  onPressed: () {
                                    Navigator.of(context).pop();
                                    _rescheduleAppointment(appointment);
                                  },
                                  icon: Icon(Icons.edit_calendar,
                                      size: layoutSettings.actionIconDimension *
                                          0.8),
                                  label: Text('Reschedule',
                                      style: TextStyle(
                                          fontSize:
                                              layoutSettings.actionTextSize +
                                                  1)),
                                  style: OutlinedButton.styleFrom(
                                    foregroundColor: joviCoral,
                                    backgroundColor:
                                        joviCoral.withOpacity(0.08),
                                    padding: EdgeInsets.symmetric(
                                        vertical:
                                            layoutSettings.paddingV * 0.7),
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(12),
                                    ),
                                    side: BorderSide(
                                        color: joviCoral.withOpacity(0.5)),
                                  ),
                                ),
                              ),
                            ],
                          ),
                          SizedBox(height: layoutSettings.paddingV * 0.6),
                          SizedBox(
                            width: double.infinity,
                            child: TextButton.icon(
                              onPressed: _isLoading
                                  ? null
                                  : () {
                                      Navigator.of(context).pop();
                                      _cancelAppointment(
                                        appointment['id'],
                                        isPriority:
                                            appointment['priority'] == true,
                                      );
                                    },
                              icon: Icon(Icons.cancel,
                                  size:
                                      layoutSettings.actionIconDimension * 0.8),
                              label: Text('Cancel Appointment',
                                  style: TextStyle(
                                      fontSize:
                                          layoutSettings.actionTextSize + 1)),
                              style: TextButton.styleFrom(
                                foregroundColor: joviErrorRed,
                                padding: EdgeInsets.symmetric(
                                    vertical: layoutSettings.paddingV * 0.7),
                              ),
                            ),
                          ),
                        ] else if ((appointment['status'] == 'pending' ||
                                appointment['status'] == 'confirmed') &&
                            !_isFutureAppointment(
                                appointment['appointmentDate'])) ...[
                          Container(
                            padding:
                                EdgeInsets.all(layoutSettings.paddingH * 0.8),
                            decoration: BoxDecoration(
                              color: joviGold.withOpacity(0.12),
                              borderRadius: BorderRadius.circular(12),
                              border:
                                  Border.all(color: joviGold.withOpacity(0.4)),
                            ),
                            child: Row(
                              children: [
                                Icon(Icons.info_outline,
                                    color: joviGold,
                                    size: layoutSettings.actionIconDimension),
                                SizedBox(width: layoutSettings.paddingH * 0.6),
                                Expanded(
                                  child: Text(
                                    'This appointment has passed and cannot be cancelled.',
                                    style: TextStyle(
                                      color: Colors.white.withOpacity(0.9),
                                      fontSize:
                                          layoutSettings.actionTextSize + 1,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                        SizedBox(height: layoutSettings.paddingV),
                      ],
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

  Widget _buildDetailSection(String title, List<Widget> children) {
    return Container(
      padding: EdgeInsets.all(layoutSettings.paddingH * 0.8),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.06),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withOpacity(0.12)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: TextStyle(
              fontSize: layoutSettings.wideMode ? 16 : 14,
              fontWeight: FontWeight.bold,
              color: joviCoral,
              letterSpacing: 0.3,
            ),
          ),
          SizedBox(height: layoutSettings.paddingV * 0.6),
          ...children,
        ],
      ),
    );
  }

  Widget _buildDetailRow(String label, String value,
      {Color? color, IconData? icon}) {
    return Padding(
      padding: EdgeInsets.symmetric(vertical: layoutSettings.paddingV * 0.3),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: layoutSettings.wideMode ? 120 : 100,
            child: Text(
              label,
              style: TextStyle(
                fontSize: layoutSettings.actionTextSize + 1,
                color: Colors.white.withOpacity(0.6),
              ),
            ),
          ),
          if (icon != null) ...[
            Icon(icon,
                size: layoutSettings.actionIconDimension * 0.6,
                color: color ?? Colors.white),
            SizedBox(width: layoutSettings.paddingH * 0.2),
          ],
          Expanded(
            child: Text(
              value,
              style: TextStyle(
                fontSize: layoutSettings.actionTextSize + 1,
                fontWeight: FontWeight.w600,
                color: color ?? Colors.white,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
