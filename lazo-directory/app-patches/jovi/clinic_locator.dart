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
// JOVI HEALTH - CLINIC LOCATOR
// Version: 2026.09.22-r2 (Apple HIG pass: no pulsing button, shimmer only
//          while loading, painted glass cards, press feedback, Jovi casing,
//          Reduce Motion, navy toasts, layout without post-frame setState)
// r1:      2026.04.17
// Build: JC-CLINIC-0922-002
//
// Full Jovi brand rework from the legacy blue-palette version:
// - Navy gradient background, glass-morphism cards
// - Coral/mint accent system, matches home dashboard exactly
// - Rebranded 'Kurv Health' → 'Jovi Health', 'Kurv Pass' → 'Jovi Pass'
// - Web-safe platform detection (no dart:io crashes)
// - launchUrl (non-deprecated)
// - Favorites keyed by clinic identity (not mutable index)
// - Parallel Firestore availability queries (was sequential)
// - Mounted checks on all async UI actions
// - Dead _liveHours code removed; honest "Typical wait" labeling
// ============================================================

import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:url_launcher/url_launcher.dart';
import 'dart:math' as math;
import 'dart:ui' as ui_dart;
import 'dart:convert';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:intl/intl.dart';
import 'package:geolocator/geolocator.dart';

// ─── Jovi Brand Color System ────────────────────────────────
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

// Jovi Pass pricing (single source of truth — change here to update globally)
const String _joviPassPriceLabel = '\$49';
const String _joviPassPriceUnit = 'per visit';
const int _joviPassWaitMinutes = 5;

/// Responsive screen size classification
enum ScreenType { compact, medium, large }

/// Layout config for responsive rendering
class _LayoutCfg {
  final double padH;
  final double padV;
  final bool isWide;
  const _LayoutCfg({
    required this.padH,
    required this.padV,
    required this.isWide,
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

class ClinicLocator extends StatefulWidget {
  final double width;
  final double height;

  const ClinicLocator({
    Key? key,
    required this.width,
    required this.height,
  }) : super(key: key);

  @override
  State<ClinicLocator> createState() => _ClinicLocatorState();
}

class _ClinicLocatorState extends State<ClinicLocator>
    with TickerProviderStateMixin {
  // ─── Layout state ──────────────────────────────────────────
  _LayoutCfg _layout = const _LayoutCfg(padH: 20, padV: 18, isWide: false);
  double? _lastWidth;

  // ─── Animations ────────────────────────────────────────────
  late AnimationController _fadeCtrl;
  late AnimationController _slideCtrl;
  late AnimationController _pulseCtrl;
  late AnimationController _shimmerCtrl;
  late Animation<double> _fadeAnim;
  late Animation<Offset> _slideAnim;
  late Animation<double> _pulseAnim;
  late Animation<double> _shimmerAnim;

  // ─── UI state ──────────────────────────────────────────────
  bool _isLoading = true;
  bool _gettingLocation = false;
  bool _locationDenied = false;
  bool _searchOpen = false;
  final TextEditingController _searchCtrl = TextEditingController();
  List<Map<String, dynamic>> _filteredClinics = [];
  // Key of expanded card (by clinic identity, NOT index — survives sorting)
  String? _expandedClinicKey;

  // ─── User location (Denver fallback) ──────────────────────
  double _userLat = 39.7392;
  double _userLng = -104.9903;

  // ─── Live data ─────────────────────────────────────────────
  // Keyed by clinic identity, values are lists of available slot strings
  final Map<String, List<String>> _availableToday = {};
  final Map<String, List<String>> _availableTomorrow = {};
  // Keyed by clinic identity, typical wait time in minutes (derived)
  final Map<String, int> _typicalWait = {};

  // ─── Favorites (keyed by clinic identity, persists correctly on sort) ──
  Set<String> _favoriteKeys = {};

  // ─── Clinic data ──────────────────────────────────────────
  List<Map<String, dynamic>> _clinics = [];
  final List<Map<String, dynamic>> _baseClinics = [
    {
      'name': 'Jovi Health',
      'subtitle': 'Dakota Ridge',
      'address': '13402 W Coal Mine Ave Suite 225',
      'city': 'Littleton',
      'state': 'CO',
      'zip': '80127',
      'fullAddress': '13402 W Coal Mine Ave Suite 225, Littleton, CO 80127',
      'lat': 39.5847,
      'lng': -105.1511,
      'phone': '(844) 774-JOVI',
      'phoneNumber': '8447745684',
      'hours': {
        'Monday': '9:00 AM - 5:00 PM',
        'Tuesday': '9:00 AM - 5:00 PM',
        'Wednesday': '9:00 AM - 5:00 PM',
        'Thursday': '9:00 AM - 5:00 PM',
        'Friday': '9:00 AM - 5:00 PM',
        'Saturday': '9:00 AM - 5:00 PM',
        'Sunday': 'Closed',
      },
      'amenities': [
        'Free Parking',
        'Wheelchair Accessible',
        'Complimentary Refreshments',
        'Short Wait Times',
      ],
      'rating': 5.0,
      'reviewCount': 127,
      'isNew': true,
    },
    {
      'name': 'Jovi Health',
      'subtitle': 'Dallas Medical City Campus',
      'address': '7777 Forest Ln., C-699',
      'city': 'Dallas',
      'state': 'TX',
      'zip': '75230',
      'fullAddress': '7777 Forest Ln., C-699, Dallas, TX 75230',
      'lat': 32.8998,
      'lng': -96.7617,
      'phone': '(844) 774-JOVI',
      'phoneNumber': '8447745684',
      'hours': {
        'Monday': '9:00 AM - 5:00 PM',
        'Tuesday': '9:00 AM - 5:00 PM',
        'Wednesday': '9:00 AM - 5:00 PM',
        'Thursday': '9:00 AM - 5:00 PM',
        'Friday': '9:00 AM - 5:00 PM',
        'Saturday': '9:00 AM - 5:00 PM',
        'Sunday': 'Closed',
      },
      'amenities': [
        'Free Parking',
        'Wheelchair Accessible',
        'Complimentary Refreshments',
        'Short Wait Times',
      ],
      'rating': 5.0,
      'reviewCount': 112,
      'isNew': true,
    },
    {
      'name': 'Jovi Health',
      'subtitle': 'Scottsdale Gateway',
      'address': '9201 E Mountain View Rd, Suite 220',
      'city': 'Scottsdale',
      'state': 'AZ',
      'zip': '85258',
      'fullAddress': '9201 E Mountain View Rd, Suite 220, Scottsdale, AZ 85258',
      'lat': 33.5184,
      'lng': -111.8799,
      'phone': '(844) 774-JOVI',
      'phoneNumber': '8447745684',
      'hours': {
        'Monday': '9:00 AM - 5:00 PM',
        'Tuesday': '9:00 AM - 5:00 PM',
        'Wednesday': '9:00 AM - 5:00 PM',
        'Thursday': '9:00 AM - 5:00 PM',
        'Friday': '9:00 AM - 5:00 PM',
        'Saturday': '9:00 AM - 5:00 PM',
        'Sunday': 'Closed',
      },
      'amenities': [
        'Free Parking',
        'Wheelchair Accessible',
        'Complimentary Refreshments',
        'Short Wait Times',
      ],
      'rating': 5.0,
      'reviewCount': 89,
      'isNew': true,
    },
  ];

  // Unique key for a clinic — stable across distance-sorting
  String _keyForClinic(Map<String, dynamic> c) =>
      '${c['subtitle'] ?? ''}|${c['city'] ?? ''}|${c['state'] ?? ''}';

  // ─── Lifecycle ────────────────────────────────────────────
  @override
  void initState() {
    super.initState();
    _setupAnimations();
    _loadFavorites();
    _initLocationAndData();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _updateLayout();
  }

  @override
  void dispose() {
    _fadeCtrl.dispose();
    _slideCtrl.dispose();
    _pulseCtrl.dispose();
    _shimmerCtrl.dispose();
    _searchCtrl.dispose();
    super.dispose();
  }

  void _setupAnimations() {
    final reduce = _platformReduceMotion();
    _fadeCtrl = AnimationController(vsync: this, duration: _Motion.enter);
    _slideCtrl = AnimationController(vsync: this, duration: _Motion.enter);
    // The nearest clinic's Book button used to pulse forever. Parked.
    _pulseCtrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..value = 0.0;
    // Loading shimmer runs only while the skeleton is on screen.
    _shimmerCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );
    if (!reduce) _shimmerCtrl.repeat();

    _fadeAnim = CurvedAnimation(parent: _fadeCtrl, curve: Curves.easeOut);
    _slideAnim = Tween<Offset>(
      begin: reduce ? Offset.zero : const Offset(0, 0.04),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _slideCtrl, curve: _Motion.settle));
    _pulseAnim = Tween<double>(begin: 1.0, end: 1.0).animate(_pulseCtrl);
    _shimmerAnim = Tween<double>(begin: 0.0, end: 1.0)
        .animate(CurvedAnimation(parent: _shimmerCtrl, curve: Curves.linear));

    Future.delayed(const Duration(milliseconds: 100), () {
      if (!mounted) return;
      _fadeCtrl.forward();
      _slideCtrl.forward();
    });
  }

  void _updateLayout() {
    final w = MediaQuery.of(context).size.width;
    if (_lastWidth == w) return;
    final cfg = w >= 1024
        ? const _LayoutCfg(padH: 40, padV: 24, isWide: true)
        : w >= 600
            ? const _LayoutCfg(padH: 24, padV: 22, isWide: true)
            : _LayoutCfg(padH: w < 360 ? 16 : 20, padV: 18, isWide: false);
    // Runs from didChangeDependencies (before build); assigning directly
    // avoids a first frame drawn with the wrong padding.
    _lastWidth = w;
    _layout = cfg;
  }

  // ─── Location init ────────────────────────────────────────
  Future<void> _initLocationAndData() async {
    if (mounted) setState(() => _gettingLocation = true);
    try {
      final serviceOn = await Geolocator.isLocationServiceEnabled();
      if (!serviceOn) {
        _useFallbackLocation();
        return;
      }
      LocationPermission perm = await Geolocator.checkPermission();
      if (perm == LocationPermission.denied) {
        perm = await Geolocator.requestPermission();
      }
      if (perm == LocationPermission.denied ||
          perm == LocationPermission.deniedForever) {
        _useFallbackLocation();
        return;
      }
      final pos = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.medium,
        timeLimit: const Duration(seconds: 10),
      );
      if (!mounted) return;
      setState(() {
        _userLat = pos.latitude;
        _userLng = pos.longitude;
        _gettingLocation = false;
        _locationDenied = false;
      });
      _sortByDistance();
      await _fetchAvailabilityForAllClinics();
      _shimmerCtrl.stop();
      if (mounted) setState(() => _isLoading = false);
    } catch (e) {
      debugPrint('ClinicLocator: location fetch error: $e');
      _useFallbackLocation();
    }
  }

  void _useFallbackLocation() {
    if (!mounted) return;
    // Denver default — good enough fallback; Dallas clinic will still show
    setState(() {
      _userLat = 39.7392;
      _userLng = -104.9903;
      _gettingLocation = false;
      _locationDenied = true;
    });
    _sortByDistance();
    _fetchAvailabilityForAllClinics().then((_) {
      _shimmerCtrl.stop();
      if (mounted) setState(() => _isLoading = false);
    });
  }

  // ─── Distance & sorting ───────────────────────────────────
  double _distanceMiles(double lat1, double lng1, double lat2, double lng2) {
    const earthRadiusMiles = 3959.0;
    final dLat = _deg2rad(lat2 - lat1);
    final dLng = _deg2rad(lng2 - lng1);
    final a = math.sin(dLat / 2) * math.sin(dLat / 2) +
        math.cos(_deg2rad(lat1)) *
            math.cos(_deg2rad(lat2)) *
            math.sin(dLng / 2) *
            math.sin(dLng / 2);
    return earthRadiusMiles * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a));
  }

  double _deg2rad(double deg) => deg * (math.pi / 180);

  void _sortByDistance() {
    final list = List<Map<String, dynamic>>.from(_baseClinics);
    for (final c in list) {
      c['distance'] = _distanceMiles(
        _userLat,
        _userLng,
        (c['lat'] as num).toDouble(),
        (c['lng'] as num).toDouble(),
      );
    }
    list.sort(
        (a, b) => (a['distance'] as double).compareTo(b['distance'] as double));
    if (!mounted) return;
    setState(() {
      _clinics = list;
      _filteredClinics = List.of(list);
    });
  }

  // ─── Availability (parallel queries) ──────────────────────
  Future<void> _fetchAvailabilityForAllClinics() async {
    final today = DateTime.now();
    final tomorrow = today.add(const Duration(days: 1));

    // Build time slots (9:00am - 4:30pm every 30 min)
    final baseSlots = _buildBaseSlots();

    // For each clinic, launch today + tomorrow queries in parallel
    final futures = <Future<void>>[];
    for (final clinic in _clinics) {
      final key = _keyForClinic(clinic);
      futures.add(_fetchSlotsForClinic(
        clinicKey: key,
        clinicSubtitle: clinic['subtitle'] as String,
        date: today,
        baseSlots: _slotsForDate(today, baseSlots),
        storeIn: _availableToday,
      ));
      futures.add(_fetchSlotsForClinic(
        clinicKey: key,
        clinicSubtitle: clinic['subtitle'] as String,
        date: tomorrow,
        baseSlots: baseSlots, // no time-filter for tomorrow
        storeIn: _availableTomorrow,
      ));
    }

    try {
      await Future.wait(futures);
    } catch (e) {
      debugPrint('ClinicLocator: availability fetch error: $e');
    }

    // Derive typical wait per clinic based on how booked today looks
    for (final clinic in _clinics) {
      final key = _keyForClinic(clinic);
      final avail = _availableToday[key]?.length ?? baseSlots.length;
      final booked = baseSlots.length - avail;
      int wait;
      if (booked < 6) {
        wait = 15;
      } else if (booked < 10) {
        wait = 25;
      } else if (booked < 14) {
        wait = 35;
      } else {
        wait = 45;
      }
      _typicalWait[key] = wait;
    }

    if (mounted) setState(() {});
  }

  List<String> _buildBaseSlots() => const [
        '9:00 AM',
        '9:30 AM',
        '10:00 AM',
        '10:30 AM',
        '11:00 AM',
        '11:30 AM',
        '12:00 PM',
        '12:30 PM',
        '1:00 PM',
        '1:30 PM',
        '2:00 PM',
        '2:30 PM',
        '3:00 PM',
        '3:30 PM',
        '4:00 PM',
        '4:30 PM',
      ];

  // Filter out past times for today; full list for future dates
  List<String> _slotsForDate(DateTime date, List<String> baseSlots) {
    final now = DateTime.now();
    final isToday =
        date.year == now.year && date.month == now.month && date.day == now.day;
    if (!isToday) return List.of(baseSlots);
    final minAllowed = now.add(const Duration(minutes: 30));
    return baseSlots.where((s) {
      final dt = _parseSlotToDateTime(date, s);
      return dt != null && dt.isAfter(minAllowed);
    }).toList();
  }

  DateTime? _parseSlotToDateTime(DateTime date, String slot) {
    try {
      final parts = slot.split(' ');
      final hm = parts[0].split(':');
      var h = int.parse(hm[0]);
      final m = int.parse(hm[1]);
      if (parts[1] == 'PM' && h != 12) h += 12;
      if (parts[1] == 'AM' && h == 12) h = 0;
      return DateTime(date.year, date.month, date.day, h, m);
    } catch (_) {
      return null;
    }
  }

  // Fetch booked slots from Firestore, remove from baseSlots, store result
  Future<void> _fetchSlotsForClinic({
    required String clinicKey,
    required String clinicSubtitle,
    required DateTime date,
    required List<String> baseSlots,
    required Map<String, List<String>> storeIn,
  }) async {
    try {
      final dateStr = DateFormat('yyyy-MM-dd').format(date);
      final snap = await FirebaseFirestore.instance
          .collection('requests')
          .where('appointmentDate', isGreaterThanOrEqualTo: dateStr)
          .where('appointmentDate', isLessThan: '${dateStr}T23:59:59')
          .where('visitMode', isEqualTo: 'Clinic')
          .where('clinic', isEqualTo: _clinicKeyFor(clinicSubtitle))
          .where('status', whereIn: ['pending', 'confirmed']).get();

      final booked = <String>{};
      for (final doc in snap.docs) {
        final t = doc.data()['appointmentTime'];
        if (t is String && t.isNotEmpty) booked.add(t);
      }
      storeIn[clinicKey] = baseSlots.where((s) => !booked.contains(s)).toList();
    } catch (e) {
      debugPrint('ClinicLocator: slot fetch failed for $clinicSubtitle: $e');
      storeIn[clinicKey] = baseSlots;
    }
  }

  // Next available display string
  String _nextAvailableText(String clinicKey) {
    final today = _availableToday[clinicKey];
    if (today != null && today.isNotEmpty) {
      return 'Today ${today.first}';
    }
    final tomorrow = _availableTomorrow[clinicKey];
    if (tomorrow != null && tomorrow.isNotEmpty) {
      return 'Tomorrow ${tomorrow.first}';
    }
    return 'Check with clinic';
  }

  // ─── Favorites (keyed by clinic identity) ─────────────────
  Future<void> _loadFavorites() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final raw = prefs.getString('favorite_clinic_keys');
      if (raw != null) {
        final list = jsonDecode(raw);
        if (list is List) {
          if (!mounted) return;
          setState(() => _favoriteKeys = list.map((e) => e.toString()).toSet());
        }
      }
    } catch (e) {
      debugPrint('ClinicLocator: failed to load favorites: $e');
    }
  }

  Future<void> _saveFavorites() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(
          'favorite_clinic_keys', jsonEncode(_favoriteKeys.toList()));
    } catch (e) {
      debugPrint('ClinicLocator: failed to save favorites: $e');
    }
  }

  Future<void> _toggleFavorite(String key) async {
    HapticFeedback.lightImpact();
    setState(() {
      if (_favoriteKeys.contains(key)) {
        _favoriteKeys.remove(key);
      } else {
        _favoriteKeys.add(key);
      }
    });
    await _saveFavorites();
  }

  // ─── Hours / status helpers ───────────────────────────────
  bool _isOpenNow(Map<String, dynamic> clinic) {
    final hours = clinic['hours'];
    if (hours is! Map) return false;
    final now = DateTime.now();
    final day = [
      'Sunday',
      'Monday',
      'Tuesday',
      'Wednesday',
      'Thursday',
      'Friday',
      'Saturday',
    ][now.weekday % 7];
    final todayHours = hours[day] as String?;
    if (todayHours == null || todayHours == 'Closed') return false;
    try {
      final parts = todayHours.split(' - ');
      if (parts.length != 2) return false;
      final open = _timeToMinutes(parts[0]);
      final close = _timeToMinutes(parts[1]);
      final current = now.hour * 60 + now.minute;
      return current >= open && current < close;
    } catch (_) {
      return false;
    }
  }

  int _timeToMinutes(String t) {
    final isPM = t.contains('PM');
    final isAM = t.contains('AM');
    final clean = t.replaceAll(' AM', '').replaceAll(' PM', '');
    final hm = clean.split(':');
    var h = int.parse(hm[0]);
    final m = int.parse(hm[1]);
    if (isPM && h != 12) h += 12;
    if (isAM && h == 12) h = 0;
    return h * 60 + m;
  }

  String _statusText(Map<String, dynamic> clinic) {
    final hours = clinic['hours'] as Map?;
    if (hours == null) return '—';
    final now = DateTime.now();
    final day = [
      'Sunday',
      'Monday',
      'Tuesday',
      'Wednesday',
      'Thursday',
      'Friday',
      'Saturday',
    ][now.weekday % 7];
    final today = hours[day] as String?;
    if (today == null || today == 'Closed') return 'Closed today';
    if (_isOpenNow(clinic)) {
      final parts = today.split(' - ');
      return parts.length == 2 ? 'Open until ${parts[1]}' : 'Open now';
    }
    final parts = today.split(' - ');
    if (parts.isNotEmpty && now.hour < 9) return 'Opens ${parts[0]}';
    return 'Closed';
  }

  // ─── Glass card helper (reusable) ─────────────────────────
  Widget _glassCard({
    required Widget child,
    double bgOpacity = 0.08,
    double borderOpacity = 0.15,
    double borderWidth = 1.2,
    EdgeInsetsGeometry? padding,
    double radius = 20,
    double blur = 16,
    Color? borderTint,
    List<BoxShadow>? shadow,
  }) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(radius),
      child: RepaintBoundary(
        child: Container(
          padding: padding ?? const EdgeInsets.all(18),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(bgOpacity + 0.02),
            borderRadius: BorderRadius.circular(radius),
            border: Border.all(
              color: (borderTint ?? Colors.white).withOpacity(borderOpacity),
              width: borderWidth,
            ),
            boxShadow: shadow ??
                [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.2),
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

  // ─── Generic pill chip ────────────────────────────────────
  Widget _pill({
    required String text,
    required Color color,
    IconData? icon,
    double iconSize = 12,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withOpacity(0.16),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.3), width: 0.8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, color: color, size: iconSize),
            const SizedBox(width: 4),
          ],
          Text(
            text,
            style: TextStyle(
              color: color,
              fontSize: 11,
              fontWeight: FontWeight.w800,
              letterSpacing: 0.3,
            ),
          ),
        ],
      ),
    );
  }

  // ─── Search filter ────────────────────────────────────────
  void _performSearch(String q) {
    final query = q.toLowerCase().trim();
    setState(() {
      // Reset expanded card when filter changes — stale index risk
      _expandedClinicKey = null;
      if (query.isEmpty) {
        _filteredClinics = List.of(_clinics);
        return;
      }
      _filteredClinics = _clinics.where((c) {
        final hay = [
          c['subtitle'],
          c['city'],
          c['state'],
          c['zip'],
          c['address'],
          c['name'],
          c['fullAddress'],
        ].whereType<String>().map((s) => s.toLowerCase()).toList();
        return hay.any((h) => h.contains(query));
      }).toList();
    });
  }

  // ─── Actions: navigation, call, copy, book ────────────────

  Future<void> _launchDirections(Map<String, dynamic> clinic) async {
    HapticFeedback.mediumImpact();
    final lat = (clinic['lat'] as num?)?.toDouble();
    final lng = (clinic['lng'] as num?)?.toDouble();
    if (lat == null || lng == null) return;

    // Universal HTTPS Google Maps directions URL — works on web, iOS, Android.
    // Native apps intercept and take over on mobile; web fallback is clean.
    final uri = Uri.parse(
        'https://www.google.com/maps/dir/?api=1&destination=$lat,$lng&travelmode=driving&dir_action=navigate');

    try {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } catch (e) {
      debugPrint('ClinicLocator: failed to launch directions: $e');
      if (!mounted) return;
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast('Unable to open maps',
        accent: _joviErrorRed, icon: CupertinoIcons.exclamationmark_circle));
    }
  }

  Future<void> _callClinic(Map<String, dynamic> clinic) async {
    HapticFeedback.lightImpact();
    final phone = clinic['phoneNumber'] as String?;
    if (phone == null || phone.isEmpty) return;
    final uri = Uri.parse('tel:$phone');
    try {
      await launchUrl(uri);
    } catch (e) {
      debugPrint('ClinicLocator: failed to dial: $e');
      if (!mounted) return;
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast('Unable to start call',
        accent: _joviErrorRed, icon: CupertinoIcons.exclamationmark_circle));
    }
  }

  Future<void> _copyAddress(Map<String, dynamic> clinic) async {
    HapticFeedback.lightImpact();
    final addr = clinic['fullAddress'] as String?;
    if (addr == null) return;
    await Clipboard.setData(ClipboardData(text: addr));
    if (!mounted) return;
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast('Address copied',
        accent: _joviMintDark, icon: CupertinoIcons.checkmark_circle, duration: const Duration(seconds: 2)));
  }

  /// Request Care saves `requests.clinic` as the full location key, not the
  /// short subtitle shown here. Keep this map in sync with Request Flow's
  /// `_clinicLocations` keys.
  static const Map<String, String> _clinicKeyBySubtitle = {
    'Dakota Ridge': 'Littleton - Dakota Ridge',
    'Scottsdale Gateway': 'Scottsdale - Scottsdale Gateway',
    'Dallas Medical City Campus': 'Dallas - Medical City Campus',
  };
  static String _clinicKeyFor(String subtitle) =>
      _clinicKeyBySubtitle[subtitle] ?? subtitle;

  Future<void> _bookForClinic(Map<String, dynamic> clinic) async {
    HapticFeedback.mediumImpact();
    final subtitle = clinic['subtitle'] as String? ?? '';
    context.pushNamed(
      'requests',
      queryParameters: {
        'visitMode': 'Clinic',
        'clinic': _clinicKeyFor(subtitle),
      },
    );
  }

  // ─── Jovi Pass info modal ─────────────────────────────────
  void _showJoviPassInfo() {
    HapticFeedback.lightImpact();
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => DraggableScrollableSheet(
        initialChildSize: 0.78,
        maxChildSize: 0.92,
        minChildSize: 0.5,
        expand: false,
        builder: (ctx, scrollCtrl) => ClipRRect(
          borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
          child: BackdropFilter(
            filter: ui_dart.ImageFilter.blur(sigmaX: 20, sigmaY: 20),
            child: Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    _joviNavy.withOpacity(0.97),
                    _joviNavyDark.withOpacity(0.99),
                  ],
                ),
                borderRadius:
                    const BorderRadius.vertical(top: Radius.circular(28)),
                border:
                    Border.all(color: Colors.white.withOpacity(0.1), width: 1),
              ),
              child: Column(
                children: [
                  // Drag handle
                  Container(
                    margin: const EdgeInsets.only(top: 10),
                    width: 38,
                    height: 4,
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                  // Header
                  Padding(
                    padding: const EdgeInsets.fromLTRB(20, 18, 16, 14),
                    child: Row(
                      children: [
                        Container(
                          width: 44,
                          height: 44,
                          decoration: BoxDecoration(
                            gradient: const LinearGradient(
                              colors: [_joviCoral, _joviCoralDark],
                            ),
                            borderRadius: BorderRadius.circular(14),
                            boxShadow: [
                              BoxShadow(
                                color: _joviCoral.withOpacity(0.4),
                                blurRadius: 12,
                                offset: const Offset(0, 4),
                              ),
                            ],
                          ),
                          child: const Icon(
                            Icons.workspace_premium_rounded,
                            color: Colors.white,
                            size: 22,
                          ),
                        ),
                        const SizedBox(width: 12),
                        const Expanded(
                          child: Text(
                            'Jovi Pass',
                            style: TextStyle(
                              fontSize: 22,
                              fontWeight: FontWeight.w700,
                              color: Colors.white,
                              letterSpacing: -0.6,
                            ),
                          ),
                        ),
                        Material(
                          color: Colors.transparent,
                          child: InkWell(
                            onTap: () => Navigator.pop(ctx),
                            borderRadius: BorderRadius.circular(12),
                            child: Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: Colors.white.withOpacity(0.1),
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: const Icon(Icons.close,
                                  color: Colors.white, size: 18),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  Expanded(
                    child: SingleChildScrollView(
                      controller: scrollCtrl,
                      padding: const EdgeInsets.fromLTRB(20, 0, 20, 28),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Skip the wait, priority care',
                            style: TextStyle(
                              fontSize: 26,
                              fontWeight: FontWeight.w700,
                              color: Colors.white,
                              letterSpacing: -0.8,
                              height: 1.15,
                            ),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            'Faster, premium care at every Jovi Health clinic.',
                            style: TextStyle(
                              fontSize: 14,
                              color: Colors.white.withOpacity(0.65),
                              fontWeight: FontWeight.w500,
                              height: 1.4,
                            ),
                          ),
                          const SizedBox(height: 24),
                          // Benefits
                          _joviPassBenefit(
                            icon: Icons.bolt_rounded,
                            title: '$_joviPassWaitMinutes-minute wait time',
                            body:
                                'Guaranteed fast access at every Jovi location.',
                            accent: _joviCoral,
                          ),
                          const SizedBox(height: 10),
                          _joviPassBenefit(
                            icon: Icons.medical_services_outlined,
                            title: 'Premium services',
                            body:
                                'Access to exclusive wellness programs and lab add-ons.',
                            accent: _joviMint,
                          ),
                          const SizedBox(height: 10),
                          _joviPassBenefit(
                            icon: Icons.support_agent_rounded,
                            title: 'Dedicated support',
                            body: '24/7 priority customer service for members.',
                            accent: _joviGold,
                          ),
                          const SizedBox(height: 22),
                          // Price card
                          _glassCard(
                            bgOpacity: 0.1,
                            borderOpacity: 0.2,
                            borderWidth: 1.5,
                            padding: const EdgeInsets.all(18),
                            borderTint: _joviCoral,
                            child: Column(
                              children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 10, vertical: 4),
                                  decoration: BoxDecoration(
                                    color: _joviMint.withOpacity(0.15),
                                    borderRadius: BorderRadius.circular(10),
                                  ),
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(Icons.savings_outlined,
                                          size: 12, color: _joviMintDark),
                                      const SizedBox(width: 4),
                                      Text(
                                        'Save time on every visit',
                                        style: TextStyle(
                                          fontSize: 11,
                                          fontWeight: FontWeight.w800,
                                          color: _joviMintDark,
                                          letterSpacing: 0.3,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                const SizedBox(height: 14),
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  crossAxisAlignment: CrossAxisAlignment.end,
                                  children: [
                                    ShaderMask(
                                      shaderCallback: (b) =>
                                          const LinearGradient(
                                        colors: [_joviCoral, _joviCoralLight],
                                      ).createShader(b),
                                      child: const Text(
                                        _joviPassPriceLabel,
                                        style: TextStyle(
                                          fontSize: 42,
                                          fontWeight: FontWeight.w900,
                                          color: Colors.white,
                                          letterSpacing: -1.5,
                                          height: 1,
                                        ),
                                      ),
                                    ),
                                    const SizedBox(width: 6),
                                    Padding(
                                      padding: const EdgeInsets.only(bottom: 6),
                                      child: Text(
                                        _joviPassPriceUnit,
                                        style: TextStyle(
                                          fontSize: 13,
                                          color: Colors.white.withOpacity(0.55),
                                          fontWeight: FontWeight.w600,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  '$_joviPassWaitMinutes-minute wait time guaranteed',
                                  style: TextStyle(
                                    fontSize: 12.5,
                                    color: Colors.white.withOpacity(0.7),
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: 22),
                          // CTA
                          _primaryButton(
                            label: 'Get Jovi Pass',
                            icon: Icons.arrow_forward_rounded,
                            onTap: () {
                              Navigator.pop(ctx);
                              context.pushNamed('requests');
                            },
                          ),
                        ],
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

  Widget _joviPassBenefit({
    required IconData icon,
    required String title,
    required String body,
    required Color accent,
  }) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: accent.withOpacity(0.25),
          width: 1,
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: accent.withOpacity(0.15),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: accent.withOpacity(0.3), width: 0.8),
            ),
            child: Icon(icon, color: accent, size: 20),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 14.5,
                    fontWeight: FontWeight.w800,
                    color: Colors.white,
                    letterSpacing: -0.2,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  body,
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.white.withOpacity(0.6),
                    fontWeight: FontWeight.w500,
                    height: 1.3,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ─── Primary/secondary button widgets ─────────────────────
  Widget _primaryButton({
    required String label,
    required VoidCallback onTap,
    IconData? icon,
  }) {
    return _Pressable(
        feedbackOnly: true,
        child: Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () {
          HapticFeedback.lightImpact();
          onTap();
        },
        borderRadius: BorderRadius.circular(14),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(vertical: 14),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [_joviCoral, _joviCoralDark],
            ),
            borderRadius: BorderRadius.circular(14),
            boxShadow: [
              BoxShadow(
                color: _joviCoral.withOpacity(0.4),
                blurRadius: 16,
                offset: const Offset(0, 6),
              ),
            ],
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                label,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                  letterSpacing: -0.2,
                ),
              ),
              if (icon != null) ...[
                const SizedBox(width: 6),
                Icon(icon, color: Colors.white, size: 18),
              ],
            ],
          ),
        ),
      ),
    ));
  }

  Widget _secondaryButton({
    required String label,
    required VoidCallback onTap,
    IconData? icon,
  }) {
    return _Pressable(
        feedbackOnly: true,
        child: Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () {
          HapticFeedback.lightImpact();
          onTap();
        },
        borderRadius: BorderRadius.circular(14),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(vertical: 13),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.06),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: Colors.white.withOpacity(0.2),
              width: 1,
            ),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              if (icon != null) ...[
                Icon(icon, color: Colors.white, size: 17),
                const SizedBox(width: 6),
              ],
              Text(
                label,
                style: const TextStyle(
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
    ));
  }

  // =================================================================
  // BUILD METHOD
  // =================================================================
  @override
  Widget build(BuildContext context) {
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
            child: Column(
              children: [
                _buildHeaderStrip(),
                Expanded(child: _buildBody()),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // =================================================================
  // HEADER STRIP (back, title, search toggle)
  // =================================================================
  Widget _buildHeaderStrip() {
    return Padding(
      padding: EdgeInsets.fromLTRB(_layout.padH, 12, _layout.padH, 8),
      child: Column(
        children: [
          Row(
            children: [
              _headerIconButton(
                icon: Icons.arrow_back_ios_new_rounded,
                onTap: () {
                  HapticFeedback.lightImpact();
                  if (Navigator.of(context).canPop()) {
                    Navigator.of(context).pop();
                  } else {
                    context.pushReplacement('/dashboard');
                  }
                },
              ),
              Expanded(
                child: Center(
                  child: Column(
                    children: [
                      const Text(
                        'Clinic Locator',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 17,
                          fontWeight: FontWeight.w600,
                          letterSpacing: -0.4,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        _locationDenied
                            ? 'Using default location'
                            : _clinics.isEmpty
                                ? 'Loading locations…'
                                : '${_clinics.length} location${_clinics.length == 1 ? "" : "s"} nearby',
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.55),
                          fontSize: 11.5,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              _headerIconButton(
                icon: _searchOpen ? Icons.close : Icons.search,
                active: _searchOpen,
                onTap: () {
                  HapticFeedback.lightImpact();
                  setState(() {
                    _searchOpen = !_searchOpen;
                    if (!_searchOpen) {
                      _searchCtrl.clear();
                      _filteredClinics = List.of(_clinics);
                    }
                  });
                },
              ),
            ],
          ),
          AnimatedSize(
            duration: _Motion.select,
            curve: _Motion.settle,
            child: _searchOpen
                ? Padding(
                    padding: const EdgeInsets.only(top: 12),
                    child: _buildSearchField(),
                  )
                : const SizedBox(width: double.infinity, height: 0),
          ),
        ],
      ),
    );
  }

  Widget _headerIconButton({
    required IconData icon,
    required VoidCallback onTap,
    bool active = false,
  }) {
    return _Pressable(
        feedbackOnly: true,
        pressedScale: 0.92,
        child: Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(13),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(13),
          child: RepaintBoundary(
            child: AnimatedContainer(
              duration: _Motion.select,
              curve: _Motion.settle,
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: active
                    ? _joviCoral.withOpacity(0.2)
                    : Colors.white.withOpacity(0.08),
                borderRadius: BorderRadius.circular(13),
                border: Border.all(
                  color: active
                      ? _joviCoral.withOpacity(0.35)
                      : Colors.white.withOpacity(0.18),
                  width: 1,
                ),
              ),
              child: Icon(
                icon,
                color: active ? _joviCoral : Colors.white,
                size: 16,
              ),
            ),
          ),
        ),
      ),
    ));
  }

  Widget _buildSearchField() {
    return ClipRRect(
      borderRadius: BorderRadius.circular(14),
      child: RepaintBoundary(
        child: Container(
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.08),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: Colors.white.withOpacity(0.15),
              width: 1,
            ),
          ),
          child: TextField(
            controller: _searchCtrl,
            onChanged: _performSearch,
            autofocus: true,
            autocorrect: false,
            textInputAction: TextInputAction.search,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 14,
              fontWeight: FontWeight.w500,
            ),
            decoration: InputDecoration(
              hintText: 'Search by city, state, or zip',
              hintStyle: TextStyle(
                color: Colors.white.withOpacity(0.4),
                fontSize: 14,
                fontWeight: FontWeight.w500,
              ),
              prefixIcon: Icon(
                Icons.search,
                color: Colors.white.withOpacity(0.6),
                size: 18,
              ),
              suffixIcon: _searchCtrl.text.isNotEmpty
                  ? IconButton(
                      icon: Icon(Icons.clear,
                          color: Colors.white.withOpacity(0.6), size: 16),
                      onPressed: () {
                        _searchCtrl.clear();
                        _performSearch('');
                      },
                    )
                  : null,
              border: InputBorder.none,
              contentPadding:
                  const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
            ),
          ),
        ),
      ),
    );
  }

  // =================================================================
  // BODY (hero + list + states)
  // =================================================================
  Widget _buildBody() {
    if (_isLoading || _gettingLocation) {
      return _buildLoadingState();
    }
    final list = _searchOpen && _searchCtrl.text.isNotEmpty
        ? _filteredClinics
        : _clinics;

    if (list.isEmpty) {
      return _buildEmptyState();
    }

    return FadeTransition(
      opacity: _fadeAnim,
      child: SlideTransition(
        position: _slideAnim,
        child: ListView.builder(
          padding: EdgeInsets.fromLTRB(
            _layout.padH,
            _layout.padV,
            _layout.padH,
            _layout.padV * 2,
          ),
          itemCount: list.length + 1, // +1 for hero
          itemBuilder: (ctx, i) {
            if (i == 0) return _buildHero();
            final clinic = list[i - 1];
            return Padding(
              padding: const EdgeInsets.only(top: 12),
              child: _buildClinicCard(clinic),
            );
          },
        ),
      ),
    );
  }

  // =================================================================
  // HERO (thin, low-weight)
  // =================================================================
  Widget _buildHero() {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6, top: 6),
      child: _glassCard(
        bgOpacity: 0.06,
        borderOpacity: 0.12,
        borderWidth: 1,
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              width: 46,
              height: 46,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [_joviCoral, _joviCoralDark],
                ),
                borderRadius: BorderRadius.circular(12),
                boxShadow: [
                  BoxShadow(
                    color: _joviCoral.withOpacity(0.35),
                    blurRadius: 12,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: const Icon(Icons.location_on_rounded,
                  color: Colors.white, size: 24),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Choose your clinic',
                    style: TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.w800,
                      color: Colors.white,
                      letterSpacing: -0.3,
                      height: 1.1,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    _locationDenied
                        ? 'Tap any card to see details and book'
                        : 'Sorted by distance from your location',
                    style: TextStyle(
                      fontSize: 12.5,
                      color: Colors.white.withOpacity(0.6),
                      fontWeight: FontWeight.w500,
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

  // =================================================================
  // EMPTY / LOADING STATES
  // =================================================================
  Widget _buildEmptyState() {
    return Center(
      child: Padding(
        padding: EdgeInsets.all(_layout.padH),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.05),
                shape: BoxShape.circle,
                border:
                    Border.all(color: Colors.white.withOpacity(0.12), width: 1),
              ),
              child: Icon(
                Icons.search_off_rounded,
                color: Colors.white.withOpacity(0.4),
                size: 32,
              ),
            ),
            const SizedBox(height: 18),
            const Text(
              'No clinics found',
              style: TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.w800,
                color: Colors.white,
                letterSpacing: -0.3,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'Try a different search term',
              style: TextStyle(
                fontSize: 13,
                color: Colors.white.withOpacity(0.55),
                fontWeight: FontWeight.w500,
              ),
            ),
            const SizedBox(height: 20),
            SizedBox(
              width: 180,
              child: _secondaryButton(
                label: 'Clear search',
                icon: Icons.refresh_rounded,
                onTap: () {
                  setState(() {
                    _searchCtrl.clear();
                    _filteredClinics = List.of(_clinics);
                  });
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLoadingState() {
    return Padding(
      padding: EdgeInsets.all(_layout.padH),
      child: AnimatedBuilder(
        animation: _shimmerCtrl,
        builder: (ctx, _) {
          return Column(
            children: List.generate(
              3,
              (i) => Container(
                margin: EdgeInsets.only(bottom: _layout.padV),
                height: 240,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      Colors.white.withOpacity(0.05),
                      Colors.white.withOpacity(0.1),
                      Colors.white.withOpacity(0.05),
                    ],
                    stops: [
                      (_shimmerAnim.value - 0.3).clamp(0.0, 1.0),
                      _shimmerAnim.value.clamp(0.0, 1.0),
                      (_shimmerAnim.value + 0.3).clamp(0.0, 1.0),
                    ],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                      color: Colors.white.withOpacity(0.08), width: 1),
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  // =================================================================
  // CLINIC CARD — glass, expandable on tap, coral-accented when closest
  // =================================================================
  Widget _buildClinicCard(Map<String, dynamic> clinic) {
    final key = _keyForClinic(clinic);
    final distance = clinic['distance'] as double?;
    final isNew = clinic['isNew'] == true;
    final isFavorite = _favoriteKeys.contains(key);
    final isOpen = _isOpenNow(clinic);
    final isClosest = _clinics.isNotEmpty && clinic == _clinics.first;
    final isExpanded = _expandedClinicKey == key;
    final wait = _typicalWait[key];

    // Drive time estimate at ~30 mph average
    String? driveTime;
    if (distance != null) {
      final mins = (distance / 30.0 * 60).round();
      driveTime = '$mins min';
    }

    return _Pressable(
        feedbackOnly: true,
        pressedScale: 0.99,
        child: Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () {
          HapticFeedback.selectionClick();
          setState(() {
            _expandedClinicKey = isExpanded ? null : key;
          });
        },
        borderRadius: BorderRadius.circular(22),
        child: AnimatedContainer(
          duration: _Motion.select,
          curve: _Motion.settle,
          child: ClipRRect(
            borderRadius: BorderRadius.circular(22),
            // Painted glass: a live blur per card in a ListView over an
            // opaque navy gradient was pure GPU cost.
            child: RepaintBoundary(
              child: Container(
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(22),
                  border: Border.all(
                    color: isClosest
                        ? _joviMint.withOpacity(0.4)
                        : Colors.white.withOpacity(0.15),
                    width: isClosest ? 1.5 : 1,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: isClosest
                          ? _joviMint.withOpacity(0.18)
                          : Colors.black.withOpacity(0.22),
                      blurRadius: isClosest ? 22 : 18,
                      offset: const Offset(0, 10),
                    ),
                  ],
                ),
                child: Column(
                  children: [
                    // ── Header band ─────────────────────────────
                    Padding(
                      padding: const EdgeInsets.fromLTRB(16, 16, 12, 14),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // Badge row
                          Row(
                            children: [
                              if (isClosest)
                                Padding(
                                  padding: const EdgeInsets.only(right: 6),
                                  child: _pill(
                                    text: 'Nearest',
                                    color: _joviMint,
                                    icon: Icons.near_me_rounded,
                                  ),
                                ),
                              if (isNew)
                                Padding(
                                  padding: const EdgeInsets.only(right: 6),
                                  child: _pill(
                                    text: 'New',
                                    color: _joviGold,
                                  ),
                                ),
                              const Spacer(),
                              _pill(
                                text: isOpen ? 'Open' : 'Closed',
                                color: isOpen ? _joviMint : _joviErrorRed,
                                icon: Icons.circle,
                                iconSize: 8,
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          // Title row
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Container(
                                width: 44,
                                height: 44,
                                decoration: BoxDecoration(
                                  color: _joviCoral.withOpacity(0.14),
                                  borderRadius: BorderRadius.circular(12),
                                  border: Border.all(
                                    color: _joviCoral.withOpacity(0.28),
                                    width: 1,
                                  ),
                                ),
                                child: const Icon(
                                  Icons.local_hospital_rounded,
                                  color: _joviCoral,
                                  size: 22,
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const Text(
                                      'Jovi Health',
                                      style: TextStyle(
                                        fontSize: 19,
                                        fontWeight: FontWeight.w700,
                                        color: Colors.white,
                                        letterSpacing: -0.5,
                                        height: 1.1,
                                      ),
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      clinic['subtitle'] as String,
                                      style: TextStyle(
                                        fontSize: 13,
                                        fontWeight: FontWeight.w600,
                                        color: Colors.white.withOpacity(0.7),
                                        letterSpacing: -0.2,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              _Pressable(
                                  feedbackOnly: true,
                                  pressedScale: 0.85,
                                  child: Material(
                                color: Colors.transparent,
                                child: InkWell(
                                  onTap: () => _toggleFavorite(key),
                                  borderRadius: BorderRadius.circular(10),
                                  child: Padding(
                                    padding: const EdgeInsets.all(11),
                                    child: AnimatedSwitcher(
                                      duration:
                                          const Duration(milliseconds: 240),
                                      child: Icon(
                                        isFavorite
                                            ? Icons.favorite_rounded
                                            : Icons.favorite_outline_rounded,
                                        key: ValueKey(isFavorite),
                                        color: isFavorite
                                            ? _joviCoral
                                            : Colors.white.withOpacity(0.5),
                                        size: 22,
                                      ),
                                    ),
                                  ),
                                ),
                              )),
                            ],
                          ),
                          // Distance pill
                          if (distance != null) ...[
                            const SizedBox(height: 12),
                            Row(
                              children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 10, vertical: 5),
                                  decoration: BoxDecoration(
                                    color: Colors.white.withOpacity(0.05),
                                    borderRadius: BorderRadius.circular(10),
                                    border: Border.all(
                                      color: Colors.white.withOpacity(0.12),
                                      width: 0.8,
                                    ),
                                  ),
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(Icons.route_rounded,
                                          size: 13,
                                          color: Colors.white.withOpacity(0.7)),
                                      const SizedBox(width: 5),
                                      Text(
                                        '${distance.toStringAsFixed(1)} mi',
                                        style: TextStyle(
                                          fontSize: 12,
                                          fontWeight: FontWeight.w700,
                                          color: Colors.white.withOpacity(0.85),
                                          letterSpacing: -0.1,
                                        ),
                                      ),
                                      if (driveTime != null) ...[
                                        const SizedBox(width: 6),
                                        Container(
                                          width: 3,
                                          height: 3,
                                          decoration: BoxDecoration(
                                            color:
                                                Colors.white.withOpacity(0.3),
                                            shape: BoxShape.circle,
                                          ),
                                        ),
                                        const SizedBox(width: 6),
                                        Text(
                                          '$driveTime drive',
                                          style: TextStyle(
                                            fontSize: 12,
                                            fontWeight: FontWeight.w700,
                                            color:
                                                Colors.white.withOpacity(0.85),
                                            letterSpacing: -0.1,
                                          ),
                                        ),
                                      ],
                                    ],
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Text(
                                  _statusText(clinic),
                                  style: TextStyle(
                                    fontSize: 11.5,
                                    fontWeight: FontWeight.w600,
                                    color: Colors.white.withOpacity(0.5),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ],
                      ),
                    ),
                    // Divider
                    Container(
                      height: 1,
                      margin: const EdgeInsets.symmetric(horizontal: 16),
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: [
                            Colors.transparent,
                            Colors.white.withOpacity(0.08),
                            Colors.transparent,
                          ],
                        ),
                      ),
                    ),
                    // ── Address + availability ──────────────────
                    Padding(
                      padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
                      child: Column(
                        children: [
                          // Address row
                          Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.all(7),
                                decoration: BoxDecoration(
                                  color: Colors.white.withOpacity(0.05),
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: Icon(
                                  Icons.location_on_outlined,
                                  size: 15,
                                  color: Colors.white.withOpacity(0.7),
                                ),
                              ),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      clinic['address'] as String,
                                      style: const TextStyle(
                                        fontSize: 13,
                                        fontWeight: FontWeight.w600,
                                        color: Colors.white,
                                        letterSpacing: -0.1,
                                      ),
                                    ),
                                    Text(
                                      '${clinic['city']}, ${clinic['state']} ${clinic['zip']}',
                                      style: TextStyle(
                                        fontSize: 11.5,
                                        color: Colors.white.withOpacity(0.55),
                                        fontWeight: FontWeight.w500,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              Material(
                                color: Colors.transparent,
                                child: InkWell(
                                  onTap: () => _copyAddress(clinic),
                                  borderRadius: BorderRadius.circular(8),
                                  child: Padding(
                                    padding: const EdgeInsets.all(12),
                                    child: Icon(
                                      Icons.copy_rounded,
                                      size: 14,
                                      color: Colors.white.withOpacity(0.5),
                                    ),
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          // Availability row — Next available + wait comparison
                          Row(
                            children: [
                              Expanded(
                                child: Container(
                                  padding: const EdgeInsets.all(11),
                                  decoration: BoxDecoration(
                                    color: _joviCoral.withOpacity(0.1),
                                    borderRadius: BorderRadius.circular(12),
                                    border: Border.all(
                                      color: _joviCoral.withOpacity(0.24),
                                      width: 0.8,
                                    ),
                                  ),
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Row(
                                        children: [
                                          Icon(
                                            Icons.event_available_rounded,
                                            size: 12,
                                            color: _joviCoral,
                                          ),
                                          const SizedBox(width: 4),
                                          Text(
                                            'Next Available',
                                            style: TextStyle(
                                              fontSize: 10.5,
                                              fontWeight: FontWeight.w700,
                                              color: _joviCoral,
                                              letterSpacing: -0.1,
                                            ),
                                          ),
                                        ],
                                      ),
                                      const SizedBox(height: 4),
                                      Text(
                                        _nextAvailableText(key),
                                        style: const TextStyle(
                                          fontSize: 13.5,
                                          fontWeight: FontWeight.w800,
                                          color: Colors.white,
                                          letterSpacing: -0.2,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                              const SizedBox(width: 8),
                              // Wait comparison — tappable → Jovi Pass
                              Expanded(
                                child: Material(
                                  color: Colors.transparent,
                                  child: InkWell(
                                    onTap: _showJoviPassInfo,
                                    borderRadius: BorderRadius.circular(12),
                                    child: Container(
                                      padding: const EdgeInsets.all(11),
                                      decoration: BoxDecoration(
                                        color: _joviMint.withOpacity(0.1),
                                        borderRadius: BorderRadius.circular(12),
                                        border: Border.all(
                                          color: _joviMint.withOpacity(0.24),
                                          width: 0.8,
                                        ),
                                      ),
                                      child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Row(
                                            children: [
                                              Icon(
                                                Icons.bolt_rounded,
                                                size: 12,
                                                color: _joviMintDark,
                                              ),
                                              const SizedBox(width: 4),
                                              Text(
                                                'Jovi Pass',
                                                style: TextStyle(
                                                  fontSize: 10.5,
                                                  fontWeight: FontWeight.w700,
                                                  color: _joviMintDark,
                                                  letterSpacing: -0.1,
                                                ),
                                              ),
                                              const Spacer(),
                                              Icon(
                                                Icons.info_outline,
                                                size: 11,
                                                color: _joviMintDark
                                                    .withOpacity(0.6),
                                              ),
                                            ],
                                          ),
                                          const SizedBox(height: 4),
                                          Row(
                                            crossAxisAlignment:
                                                CrossAxisAlignment.end,
                                            children: [
                                              Text(
                                                '$_joviPassWaitMinutes min',
                                                style: const TextStyle(
                                                  fontSize: 13.5,
                                                  fontWeight: FontWeight.w800,
                                                  color: Colors.white,
                                                  letterSpacing: -0.2,
                                                ),
                                              ),
                                              const SizedBox(width: 5),
                                              if (wait != null)
                                                Padding(
                                                  padding:
                                                      const EdgeInsets.only(
                                                          bottom: 1),
                                                  child: Text(
                                                    'vs ~$wait',
                                                    style: TextStyle(
                                                      fontSize: 10.5,
                                                      color: Colors.white
                                                          .withOpacity(0.5),
                                                      fontWeight:
                                                          FontWeight.w600,
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
                            ],
                          ),
                        ],
                      ),
                    ),
                    // ── Expandable amenities ────────────────────
                    AnimatedSize(
                      duration: _Motion.select,
                      curve: _Motion.settle,
                      alignment: Alignment.topCenter,
                      child: isExpanded
                          ? _buildAmenitiesSection(clinic)
                          : const SizedBox(width: double.infinity, height: 0),
                    ),
                    // ── Action buttons ──────────────────────────
                    Padding(
                      padding: const EdgeInsets.fromLTRB(16, 0, 16, 14),
                      child: Column(
                        children: [
                          AnimatedBuilder(
                            animation: _pulseCtrl,
                            builder: (ctx, child) {
                              return Transform.scale(
                                scale: isClosest ? _pulseAnim.value : 1.0,
                                child: child,
                              );
                            },
                            child: _primaryButton(
                              label: 'Book appointment',
                              icon: Icons.calendar_month_rounded,
                              onTap: () => _bookForClinic(clinic),
                            ),
                          ),
                          const SizedBox(height: 8),
                          Row(
                            children: [
                              Expanded(
                                child: _secondaryButton(
                                  label: 'Directions',
                                  icon: Icons.navigation_rounded,
                                  onTap: () => _launchDirections(clinic),
                                ),
                              ),
                              const SizedBox(width: 8),
                              SizedBox(
                                width: 52,
                                child: Material(
                                  color: Colors.transparent,
                                  child: InkWell(
                                    onTap: () => _callClinic(clinic),
                                    borderRadius: BorderRadius.circular(14),
                                    child: Container(
                                      height: 46,
                                      decoration: BoxDecoration(
                                        color: Colors.white.withOpacity(0.06),
                                        borderRadius: BorderRadius.circular(14),
                                        border: Border.all(
                                          color: Colors.white.withOpacity(0.2),
                                          width: 1,
                                        ),
                                      ),
                                      child: const Icon(
                                        Icons.phone_rounded,
                                        color: Colors.white,
                                        size: 19,
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                            ],
                          ),
                          // Expand/collapse indicator
                          const SizedBox(height: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 10, vertical: 4),
                            decoration: BoxDecoration(
                              color: Colors.white.withOpacity(0.04),
                              borderRadius: BorderRadius.circular(20),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Text(
                                  isExpanded ? 'Hide details' : 'More details',
                                  style: TextStyle(
                                    fontSize: 11,
                                    color: Colors.white.withOpacity(0.55),
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                                const SizedBox(width: 3),
                                AnimatedRotation(
                                  turns: isExpanded ? 0.5 : 0,
                                  duration: const Duration(milliseconds: 240),
                                  child: Icon(
                                    Icons.expand_more_rounded,
                                    size: 14,
                                    color: Colors.white.withOpacity(0.55),
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
            ),
          ),
        ),
      ),
    ));
  }

  // Amenities subsection of an expanded card
  Widget _buildAmenitiesSection(Map<String, dynamic> clinic) {
    final amenities = (clinic['amenities'] as List?)?.cast<String>() ?? [];
    if (amenities.isEmpty) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 14),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.04),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: Colors.white.withOpacity(0.1),
            width: 1,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.auto_awesome_rounded,
                    size: 14, color: _joviMintDark),
                const SizedBox(width: 6),
                Text(
                  'Amenities',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    color: _joviMintDark,
                    letterSpacing: -0.1,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: amenities.map((a) {
                IconData icon;
                switch (a.toLowerCase()) {
                  case 'free parking':
                    icon = Icons.local_parking_rounded;
                    break;
                  case 'wheelchair accessible':
                    icon = Icons.accessible_rounded;
                    break;
                  case 'complimentary refreshments':
                    icon = Icons.coffee_rounded;
                    break;
                  case 'short wait times':
                    icon = Icons.schedule_rounded;
                    break;
                  default:
                    icon = Icons.check_circle_outline_rounded;
                }
                return Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.05),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: Colors.white.withOpacity(0.1),
                      width: 0.8,
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(icon,
                          size: 13, color: Colors.white.withOpacity(0.7)),
                      const SizedBox(width: 5),
                      Text(
                        a,
                        style: const TextStyle(
                          fontSize: 11.5,
                          fontWeight: FontWeight.w600,
                          color: Colors.white,
                          letterSpacing: -0.1,
                        ),
                      ),
                    ],
                  ),
                );
              }).toList(),
            ),
          ],
        ),
      ),
    );
  }
}
