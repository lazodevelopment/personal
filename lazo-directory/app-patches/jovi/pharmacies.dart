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
// JOVI HEALTH — PHARMACIES
// Version: 2026.09.23-r2 (GoodRx price check on refill rows)
// Build: JC-PHARM-0923-001
//
// Widget Name (for FF): JoviPharmacies
// Params (all optional): width, height
// FlutterFlow page name: `pharmacies`
//
// One screen for everything pharmacy:
//   • Your pharmacy      the one refills go to. Reads users/{uid}
//                        .preferredPharmacy (partner doc id, the field
//                        Prescription Refills already uses) or
//                        .preferredPharmacyPlace (a nearby pharmacy the
//                        member picked here). Change it from any card.
//   • Recent refills     prescriptionRefills (userId) with the pharmacy each
//                        one was sent to and its status.
//   • Jovi partners      Firestore `pharmacies` where isActive, with
//                        address / phone / hours as stored (shape varies;
//                        read defensively).
//   • Nearby             Google Places API (New) searchNearby around the
//                        member, type pharmacy, sorted by distance, with
//                        today's hours and open-now. Falls back to the
//                        legacy Nearby Search endpoint (open-now only) if
//                        the New API is not enabled on the key.
//
// GOOGLE KEY: `_placesApiKey` below is empty by default, so the widget
// reuses the per-platform keys Onboarding ships. Those keys must have
// "Places API (New)" (or the legacy Places API) enabled in Google Cloud.
// If the iOS key is restricted by bundle id, set `_iosBundleId` so the
// request carries the header Google expects. The clean setup is one key
// restricted to Places only, pasted into `_placesApiKey`.
//
// Location is asked for on this screen only when the member taps
// "Find pharmacies near me", never on open.
// ═══════════════════════════════════════════════════════════════════════════

import 'dart:async';
import 'dart:convert';
import 'dart:io' show Platform;
import 'dart:math' as math;
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher.dart';
import 'package:intl/intl.dart';

// ─── Jovi Brand Color System ────────────────────────────────────────────
const Color _joviCoral = Color(0xFFFF6B4A);
const Color _joviCoralDark = Color(0xFFE5583A);
const Color _joviNavy = Color(0xFF1A2744);
const Color _joviNavyDark = Color(0xFF0F1A2E);
const Color _joviNavyMid = Color(0xFF1F2B47);
const Color _joviMint = Color(0xFF00D4AA);
const Color _joviMintDark = Color(0xFF00B894);
const Color _joviGold = Color(0xFFFFD166);
const Color _joviGoldDark = Color(0xFFE6B84D);
const Color _joviErrorRed = Color(0xFFE53935);

// ─── Google Places ──────────────────────────────────────────────────────
/// Preferred: one key restricted to the Places API. Leave empty to reuse
/// Onboarding's per-platform keys (injected below).
const String _placesApiKey = '';
/// Only needed when the iOS key is restricted by bundle id.
const String _iosBundleId = '';
const _androidApiKey = 'AIzaSyAoI6CWUg7OPak96E2GNooyF6wod_F4zEg';
const _iosApiKey = 'AIzaSyBDyMELc4u1FkVqC-2ch7-tLsWBIezgN0A';
const _webApiKey = 'AIzaSyDCMwzNdUGWSXucLubmTaBWeCOjpbeONw0';

String _activeGoogleKey() {
  if (_placesApiKey.isNotEmpty) return _placesApiKey;
  if (kIsWeb) return _webApiKey;
  try {
    if (Platform.isIOS) return _iosApiKey;
  } catch (_) {}
  return _androidApiKey;
}

const double _searchRadiusMeters = 8000; // about 5 miles
const int _maxNearby = 20;


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
  final VoidCallback? onLongPress;
  final bool enabled;
  final bool feedbackOnly;
  final double pressedScale;

  const _Pressable({
    Key? key,
    required this.child,
    this.onTap,
    this.onLongPress,
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
        widget.enabled &&
            (widget.onTap != null ||
                widget.onLongPress != null ||
                widget.feedbackOnly);
    final scale = (_down && animates && !reduce) ? widget.pressedScale : 1.0;
    final scaled = AnimatedScale(
      scale: scale,
      duration: _down ? _Motion.pressIn : _Motion.pressOut,
      curve: _down ? Curves.easeOut : _Motion.settle,
      child: widget.child,
    );
    final handlesTap =
        (widget.onTap != null || widget.onLongPress != null) &&
            !widget.feedbackOnly;
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
                onLongPress: widget.enabled ? widget.onLongPress : null,
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

/// Drop-in for `Material(color: Colors.transparent, child: InkWell(...))`:
/// keeps the ripple and the existing tap handler, adds pointer-down press
/// feedback around it without firing anything twice.
class _PressableMaterial extends StatelessWidget {
  final Widget child;
  final double pressedScale;
  const _PressableMaterial({Key? key, required this.child, this.pressedScale = 0.98})
      : super(key: key);

  @override
  Widget build(BuildContext context) {
    return _Pressable(
      feedbackOnly: true,
      pressedScale: pressedScale,
      child: Material(color: Colors.transparent, child: child),
    );
  }
}

class JoviPharmacies extends StatefulWidget {
  const JoviPharmacies({
    Key? key,
    this.width,
    this.height,
  }) : super(key: key);

  final double? width;
  final double? height;

  @override
  State<JoviPharmacies> createState() => _JoviPharmaciesState();
}

// ═══════════════════════════════════════════════════════════════════════════
// MODEL
// ═══════════════════════════════════════════════════════════════════════════

class _Pharmacy {
  final String id; // partner doc id or Google place id
  final bool isPartner;
  final String name;
  final String address;
  final String phone;
  final String website;
  final double? lat;
  final double? lng;

  /// Monday-first, 7 entries, human text ("9:00 AM – 9:00 PM", "Closed",
  /// or "" when unknown).
  final List<String> hours;
  final bool? openNow;
  final bool permanentlyClosed;

  const _Pharmacy({
    required this.id,
    required this.isPartner,
    required this.name,
    this.address = '',
    this.phone = '',
    this.website = '',
    this.lat,
    this.lng,
    this.hours = const [],
    this.openNow,
    this.permanentlyClosed = false,
  });

  bool get hasHours => hours.any((h) => h.trim().isNotEmpty);

  String get todayHours {
    if (hours.length != 7) return '';
    final i = DateTime.now().weekday - 1; // Monday = 0
    return hours[i].trim();
  }

  double? distanceMiles(double? lat0, double? lng0) {
    if (lat == null || lng == null || lat0 == null || lng0 == null) return null;
    const r = 3958.8;
    double rad(double d) => d * math.pi / 180;
    final dLat = rad(lat! - lat0);
    final dLng = rad(lng! - lng0);
    final a = math.sin(dLat / 2) * math.sin(dLat / 2) +
        math.cos(rad(lat0)) * math.cos(rad(lat!)) * math.sin(dLng / 2) * math.sin(dLng / 2);
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a));
  }

  Map<String, dynamic> toPreferredPlace() => {
        'placeId': id,
        'name': name,
        'address': address,
        'phone': phone,
        'website': website,
        'lat': lat,
        'lng': lng,
        'hours': hours,
      };

  /// Partner doc: address may be a map {street, city, state, zip, lat, lng}
  /// or a plain string; hours may be a map keyed by weekday or a list.
  factory _Pharmacy.fromPartner(String id, Map<String, dynamic> m) {
    String address = '';
    double? lat;
    double? lng;
    final a = m['address'];
    if (a is String) {
      address = a.trim();
    } else if (a is Map) {
      final parts = [
        a['street'] ?? a['line1'] ?? '',
        a['city'] ?? '',
        [a['state'] ?? '', a['zip'] ?? a['postalCode'] ?? ''].join(' ').trim(),
      ].map((e) => '$e'.trim()).where((e) => e.isNotEmpty).toList();
      address = parts.join(', ');
      lat = _num(a['lat'] ?? a['latitude']);
      lng = _num(a['lng'] ?? a['longitude']);
    }
    lat ??= _num(m['lat'] ?? m['latitude']);
    lng ??= _num(m['lng'] ?? m['longitude']);
    final geo = m['location'] ?? m['geo'];
    if (geo is GeoPoint) {
      lat = geo.latitude;
      lng = geo.longitude;
    }
    return _Pharmacy(
      id: id,
      isPartner: true,
      name: (m['name'] as String?)?.trim() ?? 'Pharmacy',
      address: address,
      phone: (m['phone'] as String?)?.trim() ?? '',
      website: (m['website'] as String?)?.trim() ?? '',
      lat: lat,
      lng: lng,
      hours: _hoursFromPartner(m['hours']),
      openNow: null,
    );
  }

  factory _Pharmacy.fromPlacesNew(Map<String, dynamic> p) {
    final loc = p['location'] as Map? ?? {};
    final regular = p['regularOpeningHours'] as Map? ?? {};
    final current = p['currentOpeningHours'] as Map? ?? {};
    final desc = (regular['weekdayDescriptions'] as List?) ?? const [];
    final hours = <String>[];
    for (final d in desc) {
      final s = '$d';
      final idx = s.indexOf(':');
      hours.add(idx >= 0 ? s.substring(idx + 1).trim() : s);
    }
    final name = p['displayName'] is Map
        ? ((p['displayName'] as Map)['text'] as String? ?? 'Pharmacy')
        : 'Pharmacy';
    return _Pharmacy(
      id: (p['id'] as String?) ?? name,
      isPartner: false,
      name: name,
      address: (p['formattedAddress'] as String?) ?? '',
      phone: (p['nationalPhoneNumber'] as String?) ?? '',
      website: (p['websiteUri'] as String?) ?? '',
      lat: _num(loc['latitude']),
      lng: _num(loc['longitude']),
      hours: hours.length == 7 ? hours : const [],
      openNow: (current['openNow'] as bool?) ?? (regular['openNow'] as bool?),
      permanentlyClosed: p['businessStatus'] == 'CLOSED_PERMANENTLY',
    );
  }

  factory _Pharmacy.fromPlacesLegacy(Map<String, dynamic> p) {
    final geo = ((p['geometry'] as Map?)?['location'] as Map?) ?? {};
    final oh = p['opening_hours'] as Map? ?? {};
    return _Pharmacy(
      id: (p['place_id'] as String?) ?? (p['name'] as String? ?? 'Pharmacy'),
      isPartner: false,
      name: (p['name'] as String?) ?? 'Pharmacy',
      address: (p['vicinity'] as String?) ?? (p['formatted_address'] as String?) ?? '',
      lat: _num(geo['lat']),
      lng: _num(geo['lng']),
      openNow: oh['open_now'] as bool?,
      permanentlyClosed: p['business_status'] == 'CLOSED_PERMANENTLY',
    );
  }

  _Pharmacy withDetails({String? phone, String? website, List<String>? hours, bool? openNow}) {
    return _Pharmacy(
      id: id,
      isPartner: isPartner,
      name: name,
      address: address,
      phone: phone ?? this.phone,
      website: website ?? this.website,
      lat: lat,
      lng: lng,
      hours: hours ?? this.hours,
      openNow: openNow ?? this.openNow,
      permanentlyClosed: permanentlyClosed,
    );
  }
}

double? _num(dynamic v) {
  if (v is num) return v.toDouble();
  if (v is String) return double.tryParse(v);
  return null;
}

const List<String> _dayNames = [
  'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday',
];

List<String> _hoursFromPartner(dynamic raw) {
  if (raw is List && raw.length == 7) return raw.map((e) => '$e').toList();
  if (raw is Map) {
    final out = <String>[];
    for (final day in _dayNames) {
      final keys = [day, day.toLowerCase(), day.substring(0, 3), day.substring(0, 3).toLowerCase()];
      dynamic v;
      for (final k in keys) {
        if (raw.containsKey(k)) {
          v = raw[k];
          break;
        }
      }
      if (v == null) {
        out.add('');
      } else if (v is String) {
        out.add(v.trim());
      } else if (v is Map) {
        final open = '${v['open'] ?? v['opens'] ?? ''}'.trim();
        final close = '${v['close'] ?? v['closes'] ?? ''}'.trim();
        final closed = v['closed'] == true || (open.isEmpty && close.isEmpty);
        out.add(closed ? 'Closed' : '$open – $close');
      } else {
        out.add('$v');
      }
    }
    return out;
  }
  return const [];
}

class _Refill {
  final String id;
  final String medicationName;
  final String pharmacyName;
  final String pharmacyId;
  final String status;
  final DateTime? requestedAt;
  const _Refill({
    required this.id,
    required this.medicationName,
    required this.pharmacyName,
    required this.pharmacyId,
    required this.status,
    this.requestedAt,
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════════════════════════════════════

class _JoviPharmaciesState extends State<JoviPharmacies>
    with SingleTickerProviderStateMixin {
  List<_Pharmacy> _partners = [];
  List<_Pharmacy> _nearby = [];
  List<_Refill> _refills = [];
  String? _preferredPartnerId;
  _Pharmacy? _preferredPlace;
  bool _loading = true;
  bool _searching = false;
  bool _locationDenied = false;
  String? _nearbyError;
  double? _lat;
  double? _lng;
  String _query = '';
  final TextEditingController _searchCtrl = TextEditingController();

  late final AnimationController _fadeCtrl;
  late final Animation<double> _fadeAnim;

  String? get _uid => FirebaseAuth.instance.currentUser?.uid;

  _Pharmacy? get _preferred {
    if (_preferredPartnerId != null) {
      for (final p in _partners) {
        if (p.id == _preferredPartnerId) return p;
      }
    }
    return _preferredPlace;
  }

  @override
  void initState() {
    super.initState();
    _fadeCtrl = AnimationController(vsync: this, duration: _Motion.enter);
    _fadeAnim = CurvedAnimation(parent: _fadeCtrl, curve: Curves.easeOut);
    if (_platformReduceMotion()) {
      _fadeCtrl.value = 1.0;
    } else {
      _fadeCtrl.forward();
    }
    _load();
  }

  @override
  void dispose() {
    _searchCtrl.dispose();
    _fadeCtrl.dispose();
    super.dispose();
  }

  // ─── Loading ────────────────────────────────────────────────────────

  Future<void> _load() async {
    final uid = _uid;
    try {
      final db = FirebaseFirestore.instance;
      final futures = <Future<dynamic>>[
        db.collection('pharmacies').where('isActive', isEqualTo: true).get(),
        if (uid != null) db.collection('users').doc(uid).get(),
        if (uid != null)
          db
              .collection('prescriptionRefills')
              .where('userId', isEqualTo: uid)
              .limit(50)
              .get(),
      ];
      final results = await Future.wait(futures);

      final partnersSnap = results[0] as QuerySnapshot<Map<String, dynamic>>;
      final partners = <_Pharmacy>[];
      for (final d in partnersSnap.docs) {
        try {
          partners.add(_Pharmacy.fromPartner(d.id, d.data()));
        } catch (e) {
          debugPrint('Pharmacies: skipped partner ${d.id}: $e');
        }
      }
      partners.sort((a, b) => a.name.toLowerCase().compareTo(b.name.toLowerCase()));

      String? preferredId;
      _Pharmacy? preferredPlace;
      final refills = <_Refill>[];
      if (uid != null) {
        final userSnap = results[1] as DocumentSnapshot<Map<String, dynamic>>;
        final u = userSnap.data() ?? {};
        preferredId = (u['preferredPharmacy'] as String?)?.trim();
        if (preferredId != null && preferredId.isEmpty) preferredId = null;
        final pp = u['preferredPharmacyPlace'];
        if (pp is Map) {
          final m = Map<String, dynamic>.from(pp);
          preferredPlace = _Pharmacy(
            id: (m['placeId'] as String?) ?? 'place',
            isPartner: false,
            name: (m['name'] as String?) ?? 'Pharmacy',
            address: (m['address'] as String?) ?? '',
            phone: (m['phone'] as String?) ?? '',
            website: (m['website'] as String?) ?? '',
            lat: _num(m['lat']),
            lng: _num(m['lng']),
            hours: (m['hours'] as List?)?.map((e) => '$e').toList() ?? const [],
          );
        }
        final refSnap = results[2] as QuerySnapshot<Map<String, dynamic>>;
        for (final d in refSnap.docs) {
          final m = d.data();
          final ts = m['requestedDate'] ?? m['refillDate'] ?? m['createdAt'];
          refills.add(_Refill(
            id: d.id,
            medicationName: (m['medicationName'] as String?) ?? 'Prescription',
            pharmacyName: (m['pharmacyName'] as String?) ?? '',
            pharmacyId: (m['pharmacyId'] as String?) ?? '',
            status: (m['status'] as String?) ?? '',
            requestedAt: ts is Timestamp ? ts.toDate() : null,
          ));
        }
        refills.sort((a, b) =>
            (b.requestedAt ?? DateTime(0)).compareTo(a.requestedAt ?? DateTime(0)));
      }

      if (!mounted) return;
      setState(() {
        _partners = partners;
        _preferredPartnerId = preferredId;
        _preferredPlace = preferredPlace;
        _refills = refills.take(10).toList();
        _loading = false;
      });
    } catch (e) {
      debugPrint('Pharmacies: load failed: $e');
      if (!mounted) return;
      setState(() => _loading = false);
    }
  }

  // ─── Nearby search (member-initiated) ───────────────────────────────

  Future<void> _findNearby() async {
    if (_searching) return;
    HapticFeedback.lightImpact();
    setState(() {
      _searching = true;
      _nearbyError = null;
    });
    try {
      final serviceOn = await Geolocator.isLocationServiceEnabled();
      if (!serviceOn) {
        setState(() {
          _searching = false;
          _locationDenied = true;
          _nearbyError = 'Turn on Location Services to find pharmacies near you.';
        });
        return;
      }
      var perm = await Geolocator.checkPermission();
      if (perm == LocationPermission.denied) {
        perm = await Geolocator.requestPermission();
      }
      if (perm == LocationPermission.denied || perm == LocationPermission.deniedForever) {
        if (!mounted) return;
        setState(() {
          _searching = false;
          _locationDenied = true;
          _nearbyError = 'Location access is off for Jovi. Enable it in Settings to see nearby pharmacies.';
        });
        return;
      }
      final pos = await Geolocator.getCurrentPosition(
        // ignore: deprecated_member_use
        desiredAccuracy: LocationAccuracy.medium,
      ).timeout(const Duration(seconds: 12));
      if (!mounted) return;
      _lat = pos.latitude;
      _lng = pos.longitude;
      final results = await _searchPlaces(pos.latitude, pos.longitude);
      if (!mounted) return;
      setState(() {
        _nearby = results;
        _locationDenied = false;
        _searching = false;
        _partners.sort(_byDistance);
      });
      if (results.isEmpty) {
        setState(() => _nearbyError = 'No pharmacies found within about 5 miles.');
      }
    } catch (e) {
      debugPrint('Pharmacies: nearby failed: $e');
      if (!mounted) return;
      setState(() {
        _searching = false;
        _nearbyError = 'Could not search nearby right now. Please try again.';
      });
    }
  }

  int _byDistance(_Pharmacy a, _Pharmacy b) {
    final da = a.distanceMiles(_lat, _lng) ?? 1e9;
    final dbb = b.distanceMiles(_lat, _lng) ?? 1e9;
    return da.compareTo(dbb);
  }

  Map<String, String> _googleHeaders() {
    final h = <String, String>{
      'Content-Type': 'application/json',
      'X-Goog-Api-Key': _activeGoogleKey(),
    };
    if (_iosBundleId.isNotEmpty && !kIsWeb) {
      try {
        if (Platform.isIOS) h['X-Ios-Bundle-Identifier'] = _iosBundleId;
      } catch (_) {}
    }
    return h;
  }

  Future<List<_Pharmacy>> _searchPlaces(double lat, double lng) async {
    // Places API (New): hours, phone and website in one call.
    try {
      final res = await http
          .post(
            Uri.parse('https://places.googleapis.com/v1/places:searchNearby'),
            headers: {
              ..._googleHeaders(),
              'X-Goog-FieldMask':
                  'places.id,places.displayName,places.formattedAddress,places.location,places.nationalPhoneNumber,places.websiteUri,places.regularOpeningHours,places.currentOpeningHours,places.businessStatus',
            },
            body: jsonEncode({
              'includedTypes': ['pharmacy', 'drugstore'],
              'maxResultCount': _maxNearby,
              'rankPreference': 'DISTANCE',
              'locationRestriction': {
                'circle': {
                  'center': {'latitude': lat, 'longitude': lng},
                  'radius': _searchRadiusMeters,
                },
              },
            }),
          )
          .timeout(const Duration(seconds: 12));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body) as Map<String, dynamic>;
        final list = (data['places'] as List?) ?? const [];
        final out = <_Pharmacy>[];
        for (final p in list) {
          try {
            final ph = _Pharmacy.fromPlacesNew(Map<String, dynamic>.from(p as Map));
            if (!ph.permanentlyClosed) out.add(ph);
          } catch (_) {}
        }
        out.sort(_byDistance);
        return out;
      }
      debugPrint('Pharmacies: Places (New) HTTP ${res.statusCode}: ${res.body.length > 200 ? res.body.substring(0, 200) : res.body}');
    } catch (e) {
      debugPrint('Pharmacies: Places (New) failed: $e');
    }

    // Legacy Nearby Search: open-now only; hours load on tap.
    final uri = Uri.parse(
        'https://maps.googleapis.com/maps/api/place/nearbysearch/json?location=$lat,$lng&radius=${_searchRadiusMeters.toInt()}&type=pharmacy&key=${_activeGoogleKey()}');
    final res = await http.get(uri).timeout(const Duration(seconds: 12));
    if (res.statusCode != 200) {
      throw Exception('Places legacy HTTP ${res.statusCode}');
    }
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    final status = data['status'] as String? ?? '';
    if (status != 'OK' && status != 'ZERO_RESULTS') {
      throw Exception('Places legacy status $status');
    }
    final list = (data['results'] as List?) ?? const [];
    final out = <_Pharmacy>[];
    for (final p in list) {
      try {
        final ph = _Pharmacy.fromPlacesLegacy(Map<String, dynamic>.from(p as Map));
        if (!ph.permanentlyClosed) out.add(ph);
      } catch (_) {}
    }
    out.sort(_byDistance);
    return out.take(_maxNearby).toList();
  }

  /// Fills phone / website / hours for a legacy result when its sheet opens.
  Future<_Pharmacy> _ensureDetails(_Pharmacy p) async {
    if (p.isPartner || p.hasHours || p.id.isEmpty) return p;
    try {
      final uri = Uri.parse(
          'https://maps.googleapis.com/maps/api/place/details/json?place_id=${p.id}&fields=formatted_phone_number,website,opening_hours&key=${_activeGoogleKey()}');
      final res = await http.get(uri).timeout(const Duration(seconds: 10));
      if (res.statusCode != 200) return p;
      final r = ((jsonDecode(res.body) as Map)['result'] as Map?) ?? {};
      final oh = r['opening_hours'] as Map? ?? {};
      final wt = (oh['weekday_text'] as List?)?.map((e) {
            final s = '$e';
            final idx = s.indexOf(':');
            return idx >= 0 ? s.substring(idx + 1).trim() : s;
          }).toList() ??
          const <String>[];
      return p.withDetails(
        phone: r['formatted_phone_number'] as String?,
        website: r['website'] as String?,
        hours: wt.length == 7 ? wt : null,
        openNow: oh['open_now'] as bool?,
      );
    } catch (e) {
      debugPrint('Pharmacies: details failed: $e');
      return p;
    }
  }

  // ─── Actions ────────────────────────────────────────────────────────

  Future<void> _setPreferred(_Pharmacy p) async {
    final uid = _uid;
    if (uid == null) return;
    HapticFeedback.mediumImpact();
    try {
      final ref = FirebaseFirestore.instance.collection('users').doc(uid);
      if (p.isPartner) {
        await ref.set({
          'preferredPharmacy': p.id,
          'preferredPharmacyName': p.name,
          'preferredPharmacyPlace': FieldValue.delete(),
          'preferredPharmacyUpdatedAt': FieldValue.serverTimestamp(),
        }, SetOptions(merge: true));
      } else {
        await ref.set({
          'preferredPharmacy': FieldValue.delete(),
          'preferredPharmacyName': p.name,
          'preferredPharmacyPlace': p.toPreferredPlace(),
          'preferredPharmacyUpdatedAt': FieldValue.serverTimestamp(),
        }, SetOptions(merge: true));
      }
      if (!mounted) return;
      setState(() {
        _preferredPartnerId = p.isPartner ? p.id : null;
        _preferredPlace = p.isPartner ? null : p;
      });
      _toast('${p.name} is now your pharmacy', ok: true);
    } catch (e) {
      debugPrint('Pharmacies: set preferred failed: $e');
      if (!mounted) return;
      _toast('Could not save your pharmacy. Please try again.', error: true);
    }
  }

  Future<void> _call(_Pharmacy p) async {
    if (p.phone.isEmpty) return;
    HapticFeedback.lightImpact();
    final digits = p.phone.replaceAll(RegExp(r'[^\d+]'), '');
    try {
      await launchUrl(Uri.parse('tel:$digits'));
    } catch (e) {
      _toast('Unable to start call', error: true);
    }
  }

  Future<void> _directions(_Pharmacy p) async {
    HapticFeedback.mediumImpact();
    final dest = (p.lat != null && p.lng != null)
        ? '${p.lat},${p.lng}'
        : Uri.encodeComponent('${p.name} ${p.address}');
    final uri = Uri.parse(
        'https://www.google.com/maps/dir/?api=1&destination=$dest&travelmode=driving&dir_action=navigate');
    try {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } catch (e) {
      _toast('Unable to open maps', error: true);
    }
  }

  Future<void> _openWebsite(_Pharmacy p) async {
    if (p.website.isEmpty) return;
    HapticFeedback.lightImpact();
    try {
      await launchUrl(Uri.parse(p.website), mode: LaunchMode.externalApplication);
    } catch (e) {
      _toast('Unable to open website', error: true);
    }
  }

  Future<void> _copyAddress(_Pharmacy p) async {
    if (p.address.isEmpty) return;
    HapticFeedback.lightImpact();
    await Clipboard.setData(ClipboardData(text: p.address));
    _toast('Address copied');
  }

  // GoodRx is a coupon, not a pharmacy: the refill still goes to the
  // pharmacy above; the member shows the coupon at pickup.
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
    return slug.isEmpty ? 'https://www.goodrx.com/' : 'https://www.goodrx.com/$slug';
  }

  Future<void> _openGoodRx(String medicationName) async {
    HapticFeedback.lightImpact();
    try {
      await launchUrl(Uri.parse(_goodRxUrl(medicationName)),
          mode: LaunchMode.externalApplication);
    } catch (e) {
      _toast('Could not open GoodRx', error: true);
    }
  }

  Future<void> _refillActions(_Refill r, _Pharmacy? pharmacy) async {
    HapticFeedback.selectionClick();
    await showCupertinoModalPopup<void>(
      context: context,
      builder: (ctx) => CupertinoActionSheet(
        title: Text(r.medicationName),
        message: Text(r.pharmacyName.isEmpty
            ? _statusLabel(r.status)
            : '${_statusLabel(r.status)} · ${r.pharmacyName}'),
        actions: [
          if (pharmacy != null)
            CupertinoActionSheetAction(
              onPressed: () {
                Navigator.pop(ctx);
                _openSheet(pharmacy);
              },
              child: const Text('Pharmacy details'),
            ),
          CupertinoActionSheetAction(
            onPressed: () {
              Navigator.pop(ctx);
              _openGoodRx(r.medicationName);
            },
            child: const Text('Check GoodRx price'),
          ),
        ],
        cancelButton: CupertinoActionSheetAction(
          isDefaultAction: true,
          onPressed: () => Navigator.pop(ctx),
          child: const Text('Cancel'),
        ),
      ),
    );
  }

  void _openSettings() {
    HapticFeedback.lightImpact();
    Geolocator.openAppSettings();
  }

  void _toast(String msg, {bool ok = false, bool error = false}) {
    if (!mounted) return;
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(msg,
        accent: error ? _joviErrorRed : ok ? _joviMint : Colors.white70,
        icon: error
            ? CupertinoIcons.exclamationmark_circle
            : ok
                ? CupertinoIcons.checkmark_circle
                : CupertinoIcons.info_circle));
  }

  String _distanceLabel(_Pharmacy p) {
    final d = p.distanceMiles(_lat, _lng);
    if (d == null) return '';
    if (d < 0.1) return 'Right here';
    return '${d.toStringAsFixed(d < 10 ? 1 : 0)} mi';
  }

  String _statusLabel(String s) {
    switch (s.toLowerCase()) {
      case 'requested':
      case 'pending':
      case 'submitted':
        return 'Requested';
      case 'approved':
      case 'processing':
      case 'in_progress':
        return 'Being filled';
      case 'ready':
        return 'Ready for pickup';
      case 'filled':
      case 'completed':
        return 'Picked up';
      case 'denied':
      case 'rejected':
        return 'Not approved';
      case 'cancelled':
      case 'canceled':
        return 'Cancelled';
      default:
        return s.isEmpty ? 'Requested' : s;
    }
  }

  Color _statusColor(String s) {
    switch (s.toLowerCase()) {
      case 'ready':
        return _joviMint;
      case 'filled':
      case 'completed':
        return _joviMintDark;
      case 'denied':
      case 'rejected':
      case 'cancelled':
      case 'canceled':
        return _joviErrorRed;
      case 'approved':
      case 'processing':
      case 'in_progress':
        return _joviGold;
      default:
        return Colors.white70;
    }
  }

  // ═══════════════════════════════════════════════════════════════════════
  // BUILD
  // ═══════════════════════════════════════════════════════════════════════

  @override
  Widget build(BuildContext context) {
    final mq = MediaQuery.of(context).size;
    return Container(
      width: widget.width ?? mq.width,
      height: widget.height ?? mq.height,
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [_joviNavy, _joviNavyDark],
        ),
      ),
      child: SafeArea(
        child: FadeTransition(
          opacity: _fadeAnim,
          child: Column(
            children: [
              _buildHeader(),
              Expanded(child: _buildBody()),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(8, 8, 16, 4),
      child: Row(
        children: [
          _PressableMaterial(
            child: InkWell(
              onTap: () {
                HapticFeedback.selectionClick();
                if (Navigator.of(context).canPop()) Navigator.of(context).pop();
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
                    border: Border.all(color: Colors.white.withOpacity(0.14), width: 0.8),
                  ),
                  child: Icon(Icons.arrow_back_ios_new_rounded,
                      color: Colors.white.withOpacity(0.85), size: 17),
                ),
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text(
                  'Pharmacies',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 17,
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.4,
                    height: 1.1,
                  ),
                ),
                const SizedBox(height: 1),
                Text(
                  _loading
                      ? 'Loading…'
                      : _preferred != null
                          ? 'Refills go to ${_preferred!.name}'
                          : 'Pick where your refills should go',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Color(0x88FFFFFF),
                    fontSize: 11.5,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              gradient: const LinearGradient(colors: [_joviMint, _joviMintDark]),
              borderRadius: BorderRadius.circular(11),
              boxShadow: [
                BoxShadow(
                  color: _joviMint.withOpacity(0.35),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: const Icon(Icons.local_pharmacy_rounded, color: _joviNavy, size: 20),
          ),
        ],
      ),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const Center(
        child: SizedBox(
          width: 28,
          height: 28,
          child: CircularProgressIndicator(
            strokeWidth: 2.5,
            valueColor: AlwaysStoppedAnimation<Color>(_joviMint),
          ),
        ),
      );
    }
    final q = _query.trim().toLowerCase();
    bool match(_Pharmacy p) =>
        q.isEmpty || p.name.toLowerCase().contains(q) || p.address.toLowerCase().contains(q);
    final partners = _partners.where(match).toList();
    final nearby = _nearby.where(match).where((p) => !_partners.any((x) => x.id == p.id)).toList();

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 6, 16, 32),
      children: [
        if (_preferred != null) ...[
          _sectionLabel('Your pharmacy'),
          const SizedBox(height: 8),
          _pharmacyCard(_preferred!, highlight: true),
          const SizedBox(height: 20),
        ],
        if (_refills.isNotEmpty) ...[
          _sectionLabel('Where your refills went'),
          const SizedBox(height: 8),
          ..._refills.map(_refillRow),
          const SizedBox(height: 14),
        ],
        _buildSearchField(),
        const SizedBox(height: 16),
        if (partners.isNotEmpty) ...[
          _sectionLabel('Jovi partner pharmacies'),
          const SizedBox(height: 8),
          ...partners.map((p) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: _pharmacyCard(p),
              )),
          const SizedBox(height: 10),
        ],
        Row(
          children: [
            Expanded(child: _sectionLabel('Near you')),
            if (_nearby.isNotEmpty && !_searching)
              _PressableMaterial(
                child: InkWell(
                  onTap: _findNearby,
                  borderRadius: BorderRadius.circular(10),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: const [
                        Icon(CupertinoIcons.arrow_clockwise, color: _joviMint, size: 14),
                        SizedBox(width: 5),
                        Text('Refresh',
                            style: TextStyle(
                                color: _joviMint, fontSize: 13.5, fontWeight: FontWeight.w600)),
                      ],
                    ),
                  ),
                ),
              ),
          ],
        ),
        const SizedBox(height: 8),
        if (_nearby.isEmpty) _buildNearbyPrompt(),
        if (_nearby.isNotEmpty && nearby.isEmpty && q.isNotEmpty)
          _muted('No nearby pharmacy matches "$_query".'),
        ...nearby.map((p) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: _pharmacyCard(p),
            )),
        if (_nearby.isNotEmpty) ...[
          const SizedBox(height: 6),
          _muted('Hours and phone numbers come from Google and can change. Call ahead for anything time-sensitive. Tap a refill to compare GoodRx prices; the coupon is shown at pickup.'),
        ],
      ],
    );
  }

  Widget _sectionLabel(String text) => Text(
        text,
        style: TextStyle(
          color: Colors.white.withOpacity(0.6),
          fontSize: 13,
          fontWeight: FontWeight.w600,
          letterSpacing: -0.1,
        ),
      );

  Widget _muted(String text) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
        child: Text(
          text,
          style: TextStyle(
            color: Colors.white.withOpacity(0.45),
            fontSize: 12,
            fontWeight: FontWeight.w500,
            height: 1.4,
          ),
        ),
      );

  Widget _buildSearchField() {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.07),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.white.withOpacity(0.12)),
      ),
      child: TextField(
        controller: _searchCtrl,
        autocorrect: false,
        textInputAction: TextInputAction.search,
        onChanged: (v) => setState(() => _query = v),
        cursorColor: _joviMint,
        style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w500),
        decoration: InputDecoration(
          hintText: 'Search by name or street',
          hintStyle: TextStyle(color: Colors.white.withOpacity(0.35), fontSize: 15),
          prefixIcon: Icon(CupertinoIcons.search, color: Colors.white.withOpacity(0.5), size: 18),
          suffixIcon: _query.isEmpty
              ? null
              : IconButton(
                  icon: Icon(CupertinoIcons.xmark_circle_fill,
                      color: Colors.white.withOpacity(0.4), size: 18),
                  onPressed: () {
                    _searchCtrl.clear();
                    setState(() => _query = '');
                  },
                ),
          border: InputBorder.none,
          contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
        ),
      ),
    );
  }

  Widget _buildNearbyPrompt() {
    return ClipRRect(
      borderRadius: BorderRadius.circular(18),
      child: RepaintBoundary(
        child: Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            color: _joviMint.withOpacity(0.06),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: _joviMint.withOpacity(0.3), width: 1.2),
          ),
          child: Column(
            children: [
              Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  color: _joviMint.withOpacity(0.16),
                  shape: BoxShape.circle,
                  border: Border.all(color: _joviMint.withOpacity(0.35)),
                ),
                child: Icon(
                  _locationDenied ? CupertinoIcons.location_slash : CupertinoIcons.location,
                  color: _joviMint,
                  size: 24,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                _locationDenied ? 'Location is off' : 'Find pharmacies near you',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.4,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                _nearbyError ??
                    'See every pharmacy within about 5 miles, with today\'s hours and whether it\'s open now.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Colors.white.withOpacity(0.6),
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                  height: 1.4,
                ),
              ),
              const SizedBox(height: 14),
              _Pressable(
                onTap: _searching
                    ? null
                    : (_locationDenied ? _openSettings : _findNearby),
                enabled: !_searching,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 13),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(colors: [_joviMint, _joviMintDark]),
                    borderRadius: BorderRadius.circular(13),
                    boxShadow: [
                      BoxShadow(
                        color: _joviMint.withOpacity(0.35),
                        blurRadius: 14,
                        offset: const Offset(0, 5),
                      ),
                    ],
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (_searching)
                        const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            valueColor: AlwaysStoppedAnimation<Color>(_joviNavy),
                          ),
                        )
                      else
                        Icon(
                          _locationDenied ? CupertinoIcons.gear : CupertinoIcons.location_fill,
                          color: _joviNavy,
                          size: 17,
                        ),
                      const SizedBox(width: 8),
                      Text(
                        _searching
                            ? 'Searching…'
                            : (_locationDenied ? 'Open Settings' : 'Use My Location'),
                        style: const TextStyle(
                          color: _joviNavy,
                          fontSize: 15,
                          fontWeight: FontWeight.w600,
                          letterSpacing: -0.2,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _refillRow(_Refill r) {
    final c = _statusColor(r.status);
    final partner = _partners.where((p) => p.id == r.pharmacyId).toList();
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: _PressableMaterial(
        child: InkWell(
          onTap: () => _refillActions(r, partner.isEmpty ? null : partner.first),
          borderRadius: BorderRadius.circular(14),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(14),
            child: RepaintBoundary(
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.06),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: Colors.white.withOpacity(0.1)),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 38,
                      height: 38,
                      decoration: BoxDecoration(
                        color: c.withOpacity(0.16),
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: c.withOpacity(0.35), width: 0.8),
                      ),
                      child: Icon(CupertinoIcons.capsule, color: c, size: 18),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            r.medicationName,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 14.5,
                              fontWeight: FontWeight.w600,
                              letterSpacing: -0.3,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            '${r.pharmacyName.isEmpty ? 'Pharmacy not set' : 'Sent to ${r.pharmacyName}'}${r.requestedAt != null ? ' · ${DateFormat('MMM d').format(r.requestedAt!)}' : ''}',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.55),
                              fontSize: 12,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                      decoration: BoxDecoration(
                        color: c.withOpacity(0.14),
                        borderRadius: BorderRadius.circular(9),
                        border: Border.all(color: c.withOpacity(0.3), width: 0.8),
                      ),
                      child: Text(
                        _statusLabel(r.status),
                        style: TextStyle(
                          color: c,
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          letterSpacing: -0.1,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _pharmacyCard(_Pharmacy p, {bool highlight = false}) {
    final isPreferred = _preferred?.id == p.id;
    final accent = p.isPartner ? _joviMint : _joviCoral;
    final today = p.todayHours;
    final dist = _distanceLabel(p);
    String openLine;
    Color openColor;
    if (p.openNow == true) {
      openLine = today.isEmpty ? 'Open now' : 'Open now · $today';
      openColor = _joviMint;
    } else if (p.openNow == false) {
      openLine = today.isEmpty ? 'Closed now' : 'Closed now · today $today';
      openColor = _joviErrorRed;
    } else if (today.isNotEmpty) {
      openLine = 'Today $today';
      openColor = Colors.white70;
    } else {
      openLine = 'Tap for hours';
      openColor = Colors.white54;
    }

    return _PressableMaterial(
      child: InkWell(
        onTap: () => _openSheet(p),
        borderRadius: BorderRadius.circular(16),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: RepaintBoundary(
            child: Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(highlight ? 0.1 : 0.07),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: highlight || isPreferred
                      ? accent.withOpacity(0.5)
                      : Colors.white.withOpacity(0.12),
                  width: highlight ? 1.3 : 1,
                ),
              ),
              child: Row(
                children: [
                  Container(
                    width: 46,
                    height: 46,
                    decoration: BoxDecoration(
                      color: accent.withOpacity(0.16),
                      borderRadius: BorderRadius.circular(13),
                      border: Border.all(color: accent.withOpacity(0.35), width: 0.8),
                    ),
                    child: Icon(
                      isPreferred ? CupertinoIcons.checkmark_seal_fill : Icons.local_pharmacy_rounded,
                      color: accent,
                      size: 22,
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
                            Expanded(
                              child: Text(
                                p.name,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 15.5,
                                  fontWeight: FontWeight.w700,
                                  letterSpacing: -0.3,
                                ),
                              ),
                            ),
                            if (dist.isNotEmpty) ...[
                              const SizedBox(width: 8),
                              Text(
                                dist,
                                style: TextStyle(
                                  color: Colors.white.withOpacity(0.55),
                                  fontSize: 12,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ],
                          ],
                        ),
                        if (p.address.isNotEmpty) ...[
                          const SizedBox(height: 2),
                          Text(
                            p.address,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.55),
                              fontSize: 12,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                        const SizedBox(height: 4),
                        Text(
                          openLine,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: openColor,
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 6),
                  Icon(Icons.chevron_right_rounded, color: Colors.white.withOpacity(0.4), size: 22),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  // ─── Detail sheet ───────────────────────────────────────────────────

  Future<void> _openSheet(_Pharmacy initial) async {
    HapticFeedback.lightImpact();
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      useSafeArea: true,
      builder: (ctx) => _PharmacySheet(
        pharmacy: initial,
        isPreferred: _preferred?.id == initial.id,
        distance: _distanceLabel(initial),
        loadDetails: _ensureDetails,
        onSetPreferred: (p) {
          Navigator.pop(ctx);
          _setPreferred(p);
        },
        onCall: _call,
        onDirections: _directions,
        onWebsite: _openWebsite,
        onCopyAddress: _copyAddress,
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// DETAIL SHEET
// ═══════════════════════════════════════════════════════════════════════════

class _PharmacySheet extends StatefulWidget {
  final _Pharmacy pharmacy;
  final bool isPreferred;
  final String distance;
  final Future<_Pharmacy> Function(_Pharmacy) loadDetails;
  final void Function(_Pharmacy) onSetPreferred;
  final Future<void> Function(_Pharmacy) onCall;
  final Future<void> Function(_Pharmacy) onDirections;
  final Future<void> Function(_Pharmacy) onWebsite;
  final Future<void> Function(_Pharmacy) onCopyAddress;

  const _PharmacySheet({
    Key? key,
    required this.pharmacy,
    required this.isPreferred,
    required this.distance,
    required this.loadDetails,
    required this.onSetPreferred,
    required this.onCall,
    required this.onDirections,
    required this.onWebsite,
    required this.onCopyAddress,
  }) : super(key: key);

  @override
  State<_PharmacySheet> createState() => _PharmacySheetState();
}

class _PharmacySheetState extends State<_PharmacySheet> {
  late _Pharmacy _p;
  bool _loadingDetails = false;

  @override
  void initState() {
    super.initState();
    _p = widget.pharmacy;
    if (!_p.isPartner && !_p.hasHours) {
      _loadingDetails = true;
      widget.loadDetails(_p).then((full) {
        if (!mounted) return;
        setState(() {
          _p = full;
          _loadingDetails = false;
        });
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final accent = _p.isPartner ? _joviMint : _joviCoral;
    final todayIdx = DateTime.now().weekday - 1;
    return ClipRRect(
      borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      child: Container(
        constraints: BoxConstraints(maxHeight: MediaQuery.of(context).size.height * 0.9),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [_joviNavy, _joviNavyDark],
          ),
          border: Border.all(color: Colors.white.withOpacity(0.1)),
        ),
        child: SafeArea(
          top: false,
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(20, 10, 20, 20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              mainAxisSize: MainAxisSize.min,
              children: [
                Center(
                  child: Container(
                    width: 38,
                    height: 4,
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      width: 48,
                      height: 48,
                      decoration: BoxDecoration(
                        color: accent.withOpacity(0.16),
                        borderRadius: BorderRadius.circular(13),
                        border: Border.all(color: accent.withOpacity(0.35)),
                      ),
                      child: Icon(Icons.local_pharmacy_rounded, color: accent, size: 24),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            _p.name,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 20,
                              fontWeight: FontWeight.w700,
                              letterSpacing: -0.6,
                              height: 1.15,
                            ),
                          ),
                          const SizedBox(height: 3),
                          Text(
                            [
                              if (_p.isPartner) 'Jovi partner',
                              if (widget.distance.isNotEmpty) '${widget.distance} away',
                              if (widget.isPreferred) 'Your pharmacy',
                            ].join(' · '),
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.6),
                              fontSize: 12.5,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: _action(
                        icon: CupertinoIcons.phone_fill,
                        label: 'Call',
                        enabled: _p.phone.isNotEmpty,
                        onTap: () => widget.onCall(_p),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: _action(
                        icon: CupertinoIcons.location_fill,
                        label: 'Directions',
                        enabled: true,
                        onTap: () => widget.onDirections(_p),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: _action(
                        icon: CupertinoIcons.globe,
                        label: 'Website',
                        enabled: _p.website.isNotEmpty,
                        onTap: () => widget.onWebsite(_p),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                if (_p.address.isNotEmpty)
                  _PressableMaterial(
                    child: InkWell(
                      onTap: () => widget.onCopyAddress(_p),
                      borderRadius: BorderRadius.circular(12),
                      child: Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.05),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: Colors.white.withOpacity(0.1)),
                        ),
                        child: Row(
                          children: [
                            Icon(CupertinoIcons.map_pin, color: Colors.white.withOpacity(0.6), size: 16),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                _p.address,
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 13.5,
                                  fontWeight: FontWeight.w500,
                                  height: 1.35,
                                ),
                              ),
                            ),
                            Icon(CupertinoIcons.doc_on_doc, color: Colors.white.withOpacity(0.4), size: 15),
                          ],
                        ),
                      ),
                    ),
                  ),
                if (_p.phone.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Icon(CupertinoIcons.phone, color: Colors.white.withOpacity(0.6), size: 15),
                      const SizedBox(width: 10),
                      Text(
                        _p.phone,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 13.5,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ],
                const SizedBox(height: 18),
                Text(
                  'Hours',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.6),
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.1,
                  ),
                ),
                const SizedBox(height: 8),
                if (_loadingDetails)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 10),
                    child: Center(
                      child: SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          valueColor: AlwaysStoppedAnimation<Color>(_joviCoral),
                        ),
                      ),
                    ),
                  )
                else if (!_p.hasHours)
                  Text(
                    'Hours not listed. Call to confirm before heading over.',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.5),
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                    ),
                  )
                else
                  ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: Container(
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.05),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: Colors.white.withOpacity(0.1)),
                      ),
                      child: Column(
                        children: [
                          for (var i = 0; i < 7; i++)
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
                              color: i == todayIdx ? _joviMint.withOpacity(0.08) : Colors.transparent,
                              child: Row(
                                children: [
                                  SizedBox(
                                    width: 96,
                                    child: Text(
                                      _dayNames[i],
                                      style: TextStyle(
                                        color: i == todayIdx ? Colors.white : Colors.white.withOpacity(0.6),
                                        fontSize: 13,
                                        fontWeight: i == todayIdx ? FontWeight.w700 : FontWeight.w500,
                                      ),
                                    ),
                                  ),
                                  Expanded(
                                    child: Text(
                                      _p.hours[i].isEmpty ? '—' : _p.hours[i],
                                      style: TextStyle(
                                        color: i == todayIdx ? Colors.white : Colors.white.withOpacity(0.75),
                                        fontSize: 13,
                                        fontWeight: i == todayIdx ? FontWeight.w600 : FontWeight.w500,
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
                const SizedBox(height: 20),
                if (!widget.isPreferred)
                  _Pressable(
                    onTap: () => widget.onSetPreferred(_p),
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 15),
                      decoration: BoxDecoration(
                        gradient: LinearGradient(colors: [accent, accent.withOpacity(0.8)]),
                        borderRadius: BorderRadius.circular(14),
                        boxShadow: [
                          BoxShadow(
                            color: accent.withOpacity(0.35),
                            blurRadius: 14,
                            offset: const Offset(0, 5),
                          ),
                        ],
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(CupertinoIcons.checkmark_seal,
                              color: _p.isPartner ? _joviNavy : Colors.white, size: 18),
                          const SizedBox(width: 8),
                          Text(
                            'Send My Refills Here',
                            style: TextStyle(
                              color: _p.isPartner ? _joviNavy : Colors.white,
                              fontSize: 15,
                              fontWeight: FontWeight.w600,
                              letterSpacing: -0.2,
                            ),
                          ),
                        ],
                      ),
                    ),
                  )
                else
                  Container(
                    padding: const EdgeInsets.symmetric(vertical: 13),
                    decoration: BoxDecoration(
                      color: _joviMint.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: _joviMint.withOpacity(0.3)),
                    ),
                    child: const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(CupertinoIcons.checkmark_seal_fill, color: _joviMint, size: 18),
                        SizedBox(width: 8),
                        Text(
                          'This is your pharmacy',
                          style: TextStyle(
                            color: _joviMint,
                            fontSize: 15,
                            fontWeight: FontWeight.w600,
                            letterSpacing: -0.2,
                          ),
                        ),
                      ],
                    ),
                  ),
                const SizedBox(height: 10),
                Text(
                  'Jovi can send prescriptions to any pharmacy. New refill requests will go here.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.5),
                    fontSize: 11.5,
                    fontWeight: FontWeight.w500,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _action({
    required IconData icon,
    required String label,
    required bool enabled,
    required VoidCallback onTap,
  }) {
    return _PressableMaterial(
      child: InkWell(
        onTap: enabled ? onTap : null,
        borderRadius: BorderRadius.circular(12),
        child: Opacity(
          opacity: enabled ? 1 : 0.4,
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 12),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.07),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.white.withOpacity(0.14)),
            ),
            child: Column(
              children: [
                Icon(icon, color: Colors.white, size: 19),
                const SizedBox(height: 5),
                Text(
                  label,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 12.5,
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.2,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
