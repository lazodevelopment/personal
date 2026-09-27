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
// JOVI HEALTH — VACCINATION RECORDS (PEOPLE)
// Version: 2026.09.22-r1
// Build: JC-VAX-0922-001
//
// Widget Name (for FF): VaccinationRecords
// Params (all optional): width, height, patientName (String, preselects
// the filter chip)
//
// The human twin of Pet Vaccinations. One record per dose at
//   users/{uid}/vaccinations/{id}
//     patientName    String   matches the names Care Records uses
//                             (users/{uid}.onboard_fullName + deps)
//     vaccineName    String
//     doseLabel      String   e.g. "Dose 2", "Booster", "" (optional)
//     administeredAt Timestamp
//     expiresAt      Timestamp?   null = no booster tracked
//     provider       String   clinic or pharmacy (optional)
//     lotNumber      String   (optional)
//     notes          String   (optional)
//     source         'member'  (a vet/clinic import would use another)
//     createdAt / updatedAt
//
// Status is computed by calendar day: overdue (expired), due soon
// (≤ 60 days), current, or no expiration. The catalog pre-fills a
// booster interval for common vaccines; members can override the date.
// Not medical advice: intervals are the common adult schedule, not a
// recommendation. Nothing here is shared with clinics automatically.
// ═══════════════════════════════════════════════════════════════════════════

import 'dart:async';
import 'dart:convert';
import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
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

const Color _statusOverdue = _joviErrorRed;
const Color _statusDueSoon = _joviGold;
const Color _statusCurrent = _joviMint;
const Color _statusNone = Color(0xFF94A3B8);


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

class VaccinationRecords extends StatefulWidget {
  const VaccinationRecords({
    Key? key,
    this.width,
    this.height,
    this.patientName,
  }) : super(key: key);

  final double? width;
  final double? height;
  final String? patientName;

  @override
  State<VaccinationRecords> createState() => _VaccinationRecordsState();
}

// ═══════════════════════════════════════════════════════════════════════════
// CATALOG
// Common vaccines with the usual booster interval in months (null = none
// tracked). Members can always override the expiration date.
// ═══════════════════════════════════════════════════════════════════════════

class _CatalogEntry {
  final String name;
  final int? boosterMonths;
  final String hint;
  const _CatalogEntry(this.name, this.boosterMonths, this.hint);
}

const List<_CatalogEntry> _catalog = [
  _CatalogEntry('Influenza (flu)', 12, 'Yearly, usually in the fall'),
  _CatalogEntry('COVID-19', 12, 'Updated shot each season'),
  _CatalogEntry('Tdap', 120, 'Tetanus, diphtheria, pertussis · every 10 years'),
  _CatalogEntry('Td', 120, 'Tetanus and diphtheria booster · every 10 years'),
  _CatalogEntry('MMR', null, 'Measles, mumps, rubella'),
  _CatalogEntry('Varicella', null, 'Chickenpox'),
  _CatalogEntry('Hepatitis A', null, 'Two-dose series'),
  _CatalogEntry('Hepatitis B', null, 'Two or three-dose series'),
  _CatalogEntry('HPV', null, 'Two or three-dose series'),
  _CatalogEntry('Shingles (Shingrix)', null, 'Two doses, adults 50+'),
  _CatalogEntry('Pneumococcal', null, 'Adults 65+ or at risk'),
  _CatalogEntry('Meningococcal', 60, 'Booster every 5 years if at risk'),
  _CatalogEntry('RSV', null, 'Adults 60+ or during pregnancy'),
  _CatalogEntry('Polio (IPV)', null, 'Childhood series'),
  _CatalogEntry('DTaP', null, 'Childhood series'),
  _CatalogEntry('Hib', null, 'Childhood series'),
  _CatalogEntry('Rotavirus', null, 'Infant series'),
];

// ═══════════════════════════════════════════════════════════════════════════
// MODEL
// ═══════════════════════════════════════════════════════════════════════════

enum _Status { overdue, dueSoon, current, none }

class _Vax {
  final String id;
  final String patientName;
  final String vaccineName;
  final String doseLabel;
  final DateTime administeredAt;
  final DateTime? expiresAt;
  final String provider;
  final String lotNumber;
  final String notes;

  const _Vax({
    required this.id,
    required this.patientName,
    required this.vaccineName,
    this.doseLabel = '',
    required this.administeredAt,
    this.expiresAt,
    this.provider = '',
    this.lotNumber = '',
    this.notes = '',
  });

  int? get daysUntilExpiry {
    final e = expiresAt;
    if (e == null) return null;
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    return DateTime(e.year, e.month, e.day).difference(today).inDays;
  }

  _Status get status {
    final d = daysUntilExpiry;
    if (d == null) return _Status.none;
    if (d < 0) return _Status.overdue;
    if (d <= 60) return _Status.dueSoon;
    return _Status.current;
  }

  Map<String, dynamic> toFirestore() => {
        'patientName': patientName,
        'vaccineName': vaccineName,
        'doseLabel': doseLabel,
        'administeredAt': Timestamp.fromDate(administeredAt),
        'expiresAt': expiresAt == null ? null : Timestamp.fromDate(expiresAt!),
        'provider': provider,
        'lotNumber': lotNumber,
        'notes': notes,
        'source': 'member',
        'updatedAt': FieldValue.serverTimestamp(),
      };

  factory _Vax.fromFirestore(String id, Map<String, dynamic> m) {
    DateTime? ts(dynamic v) {
      if (v is Timestamp) return v.toDate();
      if (v is String) return DateTime.tryParse(v);
      return null;
    }

    return _Vax(
      id: id,
      patientName: (m['patientName'] as String?)?.trim() ?? '',
      vaccineName: (m['vaccineName'] as String?)?.trim() ?? 'Vaccine',
      doseLabel: (m['doseLabel'] as String?)?.trim() ?? '',
      administeredAt: ts(m['administeredAt']) ?? DateTime.now(),
      expiresAt: ts(m['expiresAt']),
      provider: (m['provider'] as String?)?.trim() ?? '',
      lotNumber: (m['lotNumber'] as String?)?.trim() ?? '',
      notes: (m['notes'] as String?)?.trim() ?? '',
    );
  }
}

Color _statusColor(_Status s) {
  switch (s) {
    case _Status.overdue:
      return _statusOverdue;
    case _Status.dueSoon:
      return _statusDueSoon;
    case _Status.current:
      return _statusCurrent;
    case _Status.none:
      return _statusNone;
  }
}

String _statusTitle(_Status s) {
  switch (s) {
    case _Status.overdue:
      return 'Booster overdue';
    case _Status.dueSoon:
      return 'Due soon';
    case _Status.current:
      return 'Up to date';
    case _Status.none:
      return 'On record';
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════════════════════════════════════

class _VaccinationRecordsState extends State<VaccinationRecords>
    with SingleTickerProviderStateMixin {
  List<String> _patients = [];
  String? _patientFilter; // null = everyone
  List<_Vax> _all = [];
  bool _loadingPatients = true;
  bool _loadingVax = true;
  String? _error;
  StreamSubscription<QuerySnapshot<Map<String, dynamic>>>? _sub;

  late final AnimationController _fadeCtrl;
  late final Animation<double> _fadeAnim;

  String? get _uid => FirebaseAuth.instance.currentUser?.uid;

  CollectionReference<Map<String, dynamic>>? get _col {
    final uid = _uid;
    if (uid == null) return null;
    return FirebaseFirestore.instance
        .collection('users')
        .doc(uid)
        .collection('vaccinations');
  }

  List<_Vax> get _visible => _patientFilter == null
      ? _all
      : _all.where((v) => v.patientName == _patientFilter).toList();

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
    _patientFilter = widget.patientName?.trim().isNotEmpty == true
        ? widget.patientName!.trim()
        : null;
    _loadPatients();
    _subscribe();
  }

  @override
  void dispose() {
    _sub?.cancel();
    _fadeCtrl.dispose();
    super.dispose();
  }

  /// Same source as Care Records: onboard_fullName + deps[] names.
  Future<void> _loadPatients() async {
    final uid = _uid;
    if (uid == null) {
      setState(() => _loadingPatients = false);
      return;
    }
    try {
      final doc =
          await FirebaseFirestore.instance.collection('users').doc(uid).get();
      final data = doc.data() ?? {};
      final names = <String>[];
      final primary = (data['onboard_fullName'] as String?)?.trim();
      if (primary != null && primary.isNotEmpty) {
        names.add(primary);
      } else {
        final f = (data['firstName'] as String?) ?? (data['first'] as String?) ?? '';
        final l = (data['lastName'] as String?) ?? (data['last'] as String?) ?? '';
        final n = '$f $l'.trim();
        names.add(n.isEmpty
            ? (FirebaseAuth.instance.currentUser?.displayName ?? 'Me')
            : n);
      }
      for (final raw in (data['deps'] as List<dynamic>? ?? const [])) {
        try {
          final m = raw is String
              ? jsonDecode(raw) as Map<String, dynamic>
              : Map<String, dynamic>.from(raw as Map);
          final n = '${m['first'] ?? m['firstName'] ?? ''} ${m['last'] ?? m['lastName'] ?? ''}'
              .trim();
          if (n.isNotEmpty && !names.contains(n)) names.add(n);
        } catch (_) {}
      }
      for (final raw in (data['dependents'] as List<dynamic>? ?? const [])) {
        try {
          final m = raw is String
              ? jsonDecode(raw) as Map<String, dynamic>
              : Map<String, dynamic>.from(raw as Map);
          final n = '${m['firstName'] ?? m['first'] ?? ''} ${m['lastName'] ?? m['last'] ?? ''}'
              .trim();
          if (n.isNotEmpty && !names.contains(n)) names.add(n);
        } catch (_) {}
      }
      if (!mounted) return;
      setState(() {
        _patients = names;
        _loadingPatients = false;
        if (_patientFilter != null && !names.contains(_patientFilter)) {
          _patientFilter = null;
        }
      });
    } catch (e) {
      debugPrint('Vaccinations: patients load failed: $e');
      if (mounted) setState(() => _loadingPatients = false);
    }
  }

  void _subscribe() {
    final col = _col;
    if (col == null) {
      setState(() {
        _loadingVax = false;
        _error = 'Sign in to see vaccination records.';
      });
      return;
    }
    _sub?.cancel();
    _sub = col
        .orderBy('administeredAt', descending: true)
        .limit(300)
        .snapshots()
        .listen((snap) {
      if (!mounted) return;
      final list = <_Vax>[];
      for (final d in snap.docs) {
        try {
          list.add(_Vax.fromFirestore(d.id, d.data()));
        } catch (e) {
          debugPrint('Vaccinations: skipped ${d.id}: $e');
        }
      }
      setState(() {
        _all = list;
        _loadingVax = false;
        _error = null;
      });
    }, onError: (e) {
      debugPrint('Vaccinations: listener error: $e');
      if (!mounted) return;
      setState(() {
        _loadingVax = false;
        _error = 'Could not load vaccination records.';
      });
    });
  }

  // ─── Actions ────────────────────────────────────────────────────────

  Future<void> _save(_Vax v) async {
    final col = _col;
    if (col == null) return;
    try {
      if (v.id.isEmpty) {
        await col.add({...v.toFirestore(), 'createdAt': FieldValue.serverTimestamp()});
      } else {
        await col.doc(v.id).set(v.toFirestore(), SetOptions(merge: true));
      }
      if (!mounted) return;
      HapticFeedback.mediumImpact();
      _toast('${v.vaccineName} saved', ok: true);
    } catch (e) {
      debugPrint('Vaccinations: save failed: $e');
      if (!mounted) return;
      _toast('Could not save. Please try again.', error: true);
    }
  }

  Future<void> _delete(_Vax v) async {
    final ok = await showCupertinoDialog<bool>(
      context: context,
      builder: (ctx) => CupertinoAlertDialog(
        title: const Text('Delete Record?'),
        content: Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Text(
              'This removes the ${v.vaccineName} record for ${v.patientName}. This cannot be undone.'),
        ),
        actions: [
          CupertinoDialogAction(
            isDefaultAction: true,
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          CupertinoDialogAction(
            isDestructiveAction: true,
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    try {
      await _col?.doc(v.id).delete();
      if (!mounted) return;
      HapticFeedback.mediumImpact();
      _toast('Record deleted');
    } catch (e) {
      debugPrint('Vaccinations: delete failed: $e');
      if (!mounted) return;
      _toast('Could not delete. Please try again.', error: true);
    }
  }

  Future<void> _openEditor([_Vax? existing]) async {
    HapticFeedback.lightImpact();
    if (_patients.isEmpty) {
      _toast('Finish your profile first so we know who this is for.', error: true);
      return;
    }
    final result = await showModalBottomSheet<_Vax>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      useSafeArea: true,
      builder: (ctx) => _VaxEditorSheet(
        existing: existing,
        patients: _patients,
        defaultPatient: _patientFilter ?? _patients.first,
      ),
    );
    if (result != null) await _save(result);
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
        child: Stack(
          children: [
            FadeTransition(
              opacity: _fadeAnim,
              child: Column(
                children: [
                  _buildHeader(),
                  if (_patients.length > 1) _buildPatientChips(),
                  Expanded(child: _buildBody()),
                ],
              ),
            ),
            if (!_loadingVax && _error == null)
              Positioned(
                right: 16,
                bottom: 16,
                child: _buildFab(),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    final overdue = _visible.where((v) => v.status == _Status.overdue).length;
    final due = _visible.where((v) => v.status == _Status.dueSoon).length;
    String sub;
    if (_loadingVax) {
      sub = 'Loading…';
    } else if (overdue > 0) {
      sub = '$overdue booster${overdue == 1 ? '' : 's'} overdue';
    } else if (due > 0) {
      sub = '$due due soon';
    } else {
      sub = '${_visible.length} record${_visible.length == 1 ? '' : 's'}';
    }
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
                    border: Border.all(
                        color: Colors.white.withOpacity(0.14), width: 0.8),
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
                  'Vaccinations',
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
                  sub,
                  style: TextStyle(
                    color: overdue > 0
                        ? _joviErrorRed
                        : due > 0
                            ? _joviGold
                            : const Color(0x88FFFFFF),
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
              gradient: const LinearGradient(colors: [_joviCoral, _joviCoralDark]),
              borderRadius: BorderRadius.circular(11),
              boxShadow: [
                BoxShadow(
                  color: _joviCoral.withOpacity(0.35),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: const Icon(Icons.vaccines_rounded, color: Colors.white, size: 20),
          ),
        ],
      ),
    );
  }

  Widget _buildPatientChips() {
    final options = <String?>[null, ..._patients];
    return SizedBox(
      height: 46,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.fromLTRB(16, 6, 16, 4),
        itemCount: options.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (ctx, i) {
          final p = options[i];
          final selected = _patientFilter == p;
          return _PressableMaterial(
            child: InkWell(
              onTap: () {
                if (_patientFilter == p) return;
                HapticFeedback.selectionClick();
                setState(() => _patientFilter = p);
              },
              borderRadius: BorderRadius.circular(18),
              child: AnimatedContainer(
                duration: _Motion.select,
                curve: _Motion.settle,
                padding:
                    const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                decoration: BoxDecoration(
                  color: selected
                      ? _joviCoral.withOpacity(0.22)
                      : Colors.white.withOpacity(0.06),
                  borderRadius: BorderRadius.circular(18),
                  border: Border.all(
                    color: selected
                        ? _joviCoral.withOpacity(0.5)
                        : Colors.white.withOpacity(0.12),
                    width: 0.8,
                  ),
                ),
                child: Center(
                  child: Text(
                    p ?? 'Everyone',
                    style: TextStyle(
                      color: selected ? Colors.white : Colors.white.withOpacity(0.65),
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      letterSpacing: -0.2,
                    ),
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildBody() {
    if (_loadingVax || _loadingPatients) {
      return const Center(
        child: SizedBox(
          width: 28,
          height: 28,
          child: CircularProgressIndicator(
            strokeWidth: 2.5,
            valueColor: AlwaysStoppedAnimation<Color>(_joviCoral),
          ),
        ),
      );
    }
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Text(_error!,
              textAlign: TextAlign.center,
              style: TextStyle(
                  color: Colors.white.withOpacity(0.7),
                  fontSize: 14,
                  fontWeight: FontWeight.w600)),
        ),
      );
    }
    final visible = _visible;
    if (visible.isEmpty) return _buildEmpty();

    final groups = <_Status, List<_Vax>>{};
    for (final v in visible) {
      groups.putIfAbsent(v.status, () => []).add(v);
    }
    final order = [_Status.overdue, _Status.dueSoon, _Status.current, _Status.none];
    final children = <Widget>[];
    for (final s in order) {
      final items = groups[s];
      if (items == null || items.isEmpty) continue;
      final c = _statusColor(s);
      children.add(Padding(
        padding: const EdgeInsets.fromLTRB(4, 12, 4, 8),
        child: Row(
          children: [
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(color: c, shape: BoxShape.circle),
            ),
            const SizedBox(width: 8),
            Text(
              _statusTitle(s),
              style: TextStyle(
                color: c,
                fontSize: 13,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.1,
              ),
            ),
            const SizedBox(width: 6),
            Text(
              '${items.length}',
              style: TextStyle(
                color: Colors.white.withOpacity(0.4),
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ));
      for (final v in items) {
        children.add(Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: _buildCard(v, c),
        ));
      }
    }
    children.add(const SizedBox(height: 8));
    children.add(_buildDisclaimer());
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 96),
      children: children,
    );
  }

  Widget _buildCard(_Vax v, Color c) {
    final showPatient = _patientFilter == null && _patients.length > 1;
    final d = v.daysUntilExpiry;
    String expiry;
    if (v.expiresAt == null) {
      expiry = 'No booster tracked';
    } else if (d! < 0) {
      expiry = 'Booster was due ${DateFormat('MMM d, y').format(v.expiresAt!)}';
    } else if (d == 0) {
      expiry = 'Booster due today';
    } else if (d <= 60) {
      expiry = 'Booster due in $d day${d == 1 ? '' : 's'}';
    } else {
      expiry = 'Next due ${DateFormat('MMM d, y').format(v.expiresAt!)}';
    }
    return _PressableMaterial(
      child: InkWell(
        onTap: () => _openEditor(v),
        onLongPress: () => _delete(v),
        borderRadius: BorderRadius.circular(16),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: RepaintBoundary(
            child: Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.08),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: c.withOpacity(0.35), width: 1),
              ),
              child: Row(
                children: [
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: c.withOpacity(0.16),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: c.withOpacity(0.35), width: 0.8),
                    ),
                    child: Icon(Icons.vaccines_rounded, color: c, size: 21),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          v.doseLabel.isEmpty
                              ? v.vaccineName
                              : '${v.vaccineName} · ${v.doseLabel}',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 15.5,
                            fontWeight: FontWeight.w700,
                            letterSpacing: -0.3,
                          ),
                        ),
                        const SizedBox(height: 3),
                        Text(
                          '${showPatient ? '${v.patientName} · ' : ''}Given ${DateFormat('MMM d, y').format(v.administeredAt)}',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.6),
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          expiry,
                          style: TextStyle(
                            color: v.status == _Status.none
                                ? Colors.white.withOpacity(0.45)
                                : c,
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Icon(Icons.chevron_right_rounded,
                      color: Colors.white.withOpacity(0.4), size: 22),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildEmpty() {
    final who = _patientFilter ?? 'your family';
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 76,
              height: 76,
              decoration: BoxDecoration(
                color: _joviCoral.withOpacity(0.12),
                borderRadius: BorderRadius.circular(22),
                border: Border.all(color: _joviCoral.withOpacity(0.3)),
              ),
              child: const Icon(Icons.vaccines_rounded, color: _joviCoral, size: 34),
            ),
            const SizedBox(height: 18),
            Text(
              'No vaccinations for $who yet',
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 17,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.4,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              'Add flu shots, boosters and childhood series so every record is in one place when a clinic asks.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white.withOpacity(0.55),
                fontSize: 13.5,
                fontWeight: FontWeight.w500,
                height: 1.4,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDisclaimer() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.04),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withOpacity(0.1), width: 0.8),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(CupertinoIcons.info_circle,
              color: Colors.white.withOpacity(0.5), size: 15),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              'Booster dates are pre-filled from common schedules and can be edited. Your doctor or pharmacist decides what you actually need. Hold a card to delete it.',
              style: TextStyle(
                color: Colors.white.withOpacity(0.55),
                fontSize: 11.5,
                fontWeight: FontWeight.w500,
                height: 1.4,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFab() {
    return _Pressable(
      onTap: () => _openEditor(),
      pressedScale: 0.95,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
        decoration: BoxDecoration(
          gradient: const LinearGradient(colors: [_joviCoral, _joviCoralDark]),
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: _joviCoral.withOpacity(0.45),
              blurRadius: 16,
              offset: const Offset(0, 6),
            ),
          ],
        ),
        child: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(CupertinoIcons.plus, color: Colors.white, size: 18),
            SizedBox(width: 7),
            Text(
              'Add Vaccination',
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
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// EDITOR SHEET
// ═══════════════════════════════════════════════════════════════════════════

class _VaxEditorSheet extends StatefulWidget {
  final _Vax? existing;
  final List<String> patients;
  final String defaultPatient;
  const _VaxEditorSheet({
    Key? key,
    this.existing,
    required this.patients,
    required this.defaultPatient,
  }) : super(key: key);

  @override
  State<_VaxEditorSheet> createState() => _VaxEditorSheetState();
}

class _VaxEditorSheetState extends State<_VaxEditorSheet> {
  late String _patient;
  String _vaccine = '';
  bool _customVaccine = false;
  late final TextEditingController _customName;
  late final TextEditingController _dose;
  late final TextEditingController _provider;
  late final TextEditingController _lot;
  late final TextEditingController _notes;
  DateTime _given = DateTime.now();
  DateTime? _expires;
  bool _expiryAuto = false;
  String? _error;

  bool get _isEditing => widget.existing != null;

  @override
  void initState() {
    super.initState();
    final e = widget.existing;
    _patient = e?.patientName.isNotEmpty == true ? e!.patientName : widget.defaultPatient;
    if (!widget.patients.contains(_patient)) _patient = widget.defaultPatient;
    _vaccine = e?.vaccineName ?? '';
    _customVaccine = e != null && !_catalog.any((c) => c.name == e.vaccineName);
    _customName = TextEditingController(text: _customVaccine ? _vaccine : '');
    _dose = TextEditingController(text: e?.doseLabel ?? '');
    _provider = TextEditingController(text: e?.provider ?? '');
    _lot = TextEditingController(text: e?.lotNumber ?? '');
    _notes = TextEditingController(text: e?.notes ?? '');
    _given = e?.administeredAt ?? DateTime.now();
    _expires = e?.expiresAt;
  }

  @override
  void dispose() {
    _customName.dispose();
    _dose.dispose();
    _provider.dispose();
    _lot.dispose();
    _notes.dispose();
    super.dispose();
  }

  void _pickCatalog(_CatalogEntry c) {
    HapticFeedback.selectionClick();
    setState(() {
      _customVaccine = false;
      _vaccine = c.name;
      _error = null;
      _applyAutoExpiry(c);
    });
  }

  void _applyAutoExpiry(_CatalogEntry c) {
    if (c.boosterMonths == null) {
      if (_expiryAuto) _expires = null;
      _expiryAuto = false;
      return;
    }
    _expires = DateTime(_given.year, _given.month + c.boosterMonths!, _given.day);
    _expiryAuto = true;
  }

  Future<DateTime?> _pickDate(DateTime initial, {DateTime? min, DateTime? max}) async {
    HapticFeedback.selectionClick();
    FocusScope.of(context).unfocus();
    var temp = initial;
    var picked = false;
    await showCupertinoModalPopup<void>(
      context: context,
      builder: (ctx) => Container(
        height: 300,
        decoration: const BoxDecoration(
          color: _joviNavyMid,
          borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        ),
        child: SafeArea(
          top: false,
          child: Column(
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  CupertinoButton(
                    onPressed: () {
                      picked = true;
                      Navigator.pop(ctx);
                    },
                    child: const Text('Done',
                        style: TextStyle(
                            color: _joviCoral, fontWeight: FontWeight.w600)),
                  ),
                ],
              ),
              Expanded(
                child: CupertinoTheme(
                  data: const CupertinoThemeData(
                    brightness: Brightness.dark,
                    textTheme: CupertinoTextThemeData(
                      dateTimePickerTextStyle:
                          TextStyle(color: Colors.white, fontSize: 20),
                    ),
                  ),
                  child: CupertinoDatePicker(
                    mode: CupertinoDatePickerMode.date,
                    initialDateTime: initial,
                    minimumDate: min,
                    maximumDate: max,
                    onDateTimeChanged: (d) => temp = d,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
    return picked ? temp : null;
  }

  Future<void> _pickGiven() async {
    final now = DateTime.now();
    final d = await _pickDate(_given.isAfter(now) ? now : _given,
        min: DateTime(now.year - 100), max: now);
    if (d == null) return;
    setState(() {
      _given = d;
      final entry = _catalog.where((c) => c.name == _vaccine).toList();
      if (_expiryAuto && entry.isNotEmpty) _applyAutoExpiry(entry.first);
    });
  }

  Future<void> _pickExpires() async {
    final now = DateTime.now();
    final d = await _pickDate(_expires ?? DateTime(now.year + 1, now.month, now.day),
        min: _given, max: DateTime(now.year + 30));
    if (d == null) return;
    setState(() {
      _expires = d;
      _expiryAuto = false;
    });
  }

  void _submit() {
    final name = _customVaccine ? _customName.text.trim() : _vaccine;
    if (name.isEmpty) {
      HapticFeedback.mediumImpact();
      setState(() => _error = 'Pick a vaccine or enter a name.');
      return;
    }
    HapticFeedback.lightImpact();
    Navigator.pop(
      context,
      _Vax(
        id: widget.existing?.id ?? '',
        patientName: _patient,
        vaccineName: name,
        doseLabel: _dose.text.trim(),
        administeredAt: _given,
        expiresAt: _expires,
        provider: _provider.text.trim(),
        lotNumber: _lot.text.trim(),
        notes: _notes.text.trim(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;
    return Padding(
      padding: EdgeInsets.only(bottom: bottomInset),
      child: ClipRRect(
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        child: Container(
          constraints: BoxConstraints(
              maxHeight: MediaQuery.of(context).size.height * 0.92),
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
                  Text(
                    _isEditing ? 'Edit Vaccination' : 'Add Vaccination',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 20,
                      fontWeight: FontWeight.w700,
                      letterSpacing: -0.6,
                    ),
                  ),
                  const SizedBox(height: 16),
                  if (widget.patients.length > 1) ...[
                    _label('Who'),
                    const SizedBox(height: 6),
                    _chips(widget.patients, _patient, (v) => setState(() => _patient = v)),
                    const SizedBox(height: 14),
                  ],
                  _label('Vaccine'),
                  const SizedBox(height: 6),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      for (final c in _catalog)
                        _chip(c.name, !_customVaccine && _vaccine == c.name,
                            () => _pickCatalog(c)),
                      _chip('Other…', _customVaccine, () {
                        HapticFeedback.selectionClick();
                        setState(() {
                          _customVaccine = true;
                          _error = null;
                          if (_expiryAuto) {
                            _expires = null;
                            _expiryAuto = false;
                          }
                        });
                      }),
                    ],
                  ),
                  if (!_customVaccine && _vaccine.isNotEmpty) ...[
                    const SizedBox(height: 6),
                    Text(
                      _catalog.firstWhere((c) => c.name == _vaccine,
                          orElse: () => const _CatalogEntry('', null, '')).hint,
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.5),
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                  if (_customVaccine) ...[
                    const SizedBox(height: 10),
                    _textField(_customName, 'Vaccine name', 'e.g. Typhoid',
                        capitalization: TextCapitalization.words),
                  ],
                  if (_error != null) ...[
                    const SizedBox(height: 6),
                    Text(_error!,
                        style: const TextStyle(
                            color: _joviErrorRed,
                            fontSize: 12,
                            fontWeight: FontWeight.w600)),
                  ],
                  const SizedBox(height: 14),
                  _textField(_dose, 'Dose (optional)', 'e.g. Dose 2, Booster',
                      capitalization: TextCapitalization.sentences),
                  const SizedBox(height: 14),
                  Row(
                    children: [
                      Expanded(
                        child: _dateField('Date given',
                            DateFormat('MMM d, y').format(_given), _pickGiven),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _dateField(
                          'Next due',
                          _expires == null
                              ? 'None'
                              : DateFormat('MMM d, y').format(_expires!),
                          _pickExpires,
                          trailingClear: _expires != null
                              ? () => setState(() {
                                    _expires = null;
                                    _expiryAuto = false;
                                  })
                              : null,
                        ),
                      ),
                    ],
                  ),
                  if (_expiryAuto) ...[
                    const SizedBox(height: 6),
                    Text(
                      'Next due was filled from the usual schedule. Tap to change it.',
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.5),
                        fontSize: 11.5,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                  const SizedBox(height: 14),
                  _textField(_provider, 'Clinic or pharmacy (optional)',
                      'e.g. CVS on Main St',
                      capitalization: TextCapitalization.words),
                  const SizedBox(height: 14),
                  _textField(_lot, 'Lot number (optional)', 'From the vaccine card',
                      capitalization: TextCapitalization.characters),
                  const SizedBox(height: 14),
                  _textField(_notes, 'Notes (optional)', 'Reactions, reminders…',
                      capitalization: TextCapitalization.sentences, maxLines: 3),
                  const SizedBox(height: 22),
                  _PressableMaterial(
                    child: InkWell(
                      onTap: _submit,
                      borderRadius: BorderRadius.circular(14),
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 15),
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                              colors: [_joviCoral, _joviCoralDark]),
                          borderRadius: BorderRadius.circular(14),
                          boxShadow: [
                            BoxShadow(
                              color: _joviCoral.withOpacity(0.35),
                              blurRadius: 14,
                              offset: const Offset(0, 5),
                            ),
                          ],
                        ),
                        child: Center(
                          child: Text(
                            _isEditing ? 'Save Changes' : 'Add Vaccination',
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 15,
                              fontWeight: FontWeight.w600,
                              letterSpacing: -0.2,
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  CupertinoButton(
                    onPressed: () => Navigator.pop(context),
                    child: Text('Cancel',
                        style: TextStyle(
                            color: Colors.white.withOpacity(0.6),
                            fontSize: 15,
                            fontWeight: FontWeight.w600)),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  BoxDecoration _boxDeco() => BoxDecoration(
        color: Colors.white.withOpacity(0.06),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: _joviCoral.withOpacity(0.25)),
      );

  Widget _label(String text) => Text(
        text,
        style: TextStyle(
          color: Colors.white.withOpacity(0.65),
          fontSize: 12.5,
          fontWeight: FontWeight.w600,
          letterSpacing: -0.1,
        ),
      );

  Widget _textField(TextEditingController c, String label, String hint,
      {TextCapitalization capitalization = TextCapitalization.none,
      int maxLines = 1}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _label(label),
        const SizedBox(height: 6),
        Container(
          decoration: _boxDeco(),
          child: TextField(
            controller: c,
            maxLines: maxLines,
            textCapitalization: capitalization,
            textInputAction:
                maxLines > 1 ? TextInputAction.newline : TextInputAction.next,
            onChanged: (_) {
              if (_error != null) setState(() => _error = null);
            },
            cursorColor: _joviCoral,
            style: const TextStyle(
                color: Colors.white, fontSize: 15, fontWeight: FontWeight.w600),
            decoration: InputDecoration(
              hintText: hint,
              hintStyle: TextStyle(
                  color: Colors.white.withOpacity(0.3),
                  fontSize: 14,
                  fontWeight: FontWeight.w500),
              border: InputBorder.none,
              contentPadding:
                  const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
            ),
          ),
        ),
      ],
    );
  }

  Widget _dateField(String label, String value, VoidCallback onTap,
      {VoidCallback? trailingClear}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _label(label),
        const SizedBox(height: 6),
        _PressableMaterial(
          child: InkWell(
            onTap: onTap,
            borderRadius: BorderRadius.circular(12),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 13),
              decoration: _boxDeco(),
              child: Row(
                children: [
                  const Icon(CupertinoIcons.calendar, color: _joviCoral, size: 16),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      value,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: value == 'None'
                            ? Colors.white.withOpacity(0.4)
                            : Colors.white,
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  if (trailingClear != null)
                    GestureDetector(
                      behavior: HitTestBehavior.opaque,
                      onTap: () {
                        HapticFeedback.selectionClick();
                        trailingClear();
                      },
                      child: Padding(
                        padding: const EdgeInsets.only(left: 6),
                        child: Icon(CupertinoIcons.xmark_circle_fill,
                            color: Colors.white.withOpacity(0.4), size: 18),
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _chips(List<String> options, String selected, ValueChanged<String> onPick) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        for (final o in options)
          _chip(o, o == selected, () {
            HapticFeedback.selectionClick();
            onPick(o);
          }),
      ],
    );
  }

  Widget _chip(String text, bool selected, VoidCallback onTap) {
    return _PressableMaterial(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(11),
        child: AnimatedContainer(
          duration: _Motion.select,
          curve: _Motion.settle,
          padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 9),
          decoration: BoxDecoration(
            color: selected
                ? _joviCoral.withOpacity(0.2)
                : Colors.white.withOpacity(0.05),
            borderRadius: BorderRadius.circular(11),
            border: Border.all(
              color: selected
                  ? _joviCoral.withOpacity(0.5)
                  : Colors.white.withOpacity(0.12),
              width: 0.8,
            ),
          ),
          child: Text(
            text,
            style: TextStyle(
              color: selected ? Colors.white : Colors.white.withOpacity(0.65),
              fontSize: 13,
              fontWeight: FontWeight.w600,
              letterSpacing: -0.2,
            ),
          ),
        ),
      ),
    );
  }
}
