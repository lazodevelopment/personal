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
// JOVI HEALTH — FAMILY (DEPENDENTS) MANAGEMENT
// Version: 2026.09.22-r1
// Build: JC-FAMILY-0922-001
//
// Widget Name (for FF): JoviDependents
// Params (all optional): width, height
// FlutterFlow page name: `dependents` (Request Flow's "Add family" tile
// pushes /dependents first; Home's "dependent profile incomplete" action
// still points at /updateProfile and can be switched to this page).
//
// The account's people: the member, an optional spouse (read-only here,
// edited in Profile), and dependents that can be added, edited and
// removed. Dependents are stored three ways today and every reader uses
// a different one, so this widget keeps all three in sync:
//
//   users/{uid}/dependents/{memberId}         canonical (this widget,
//                                              User Profile counts it)
//   users/{uid}.deps        [JSON strings]     {first, last, birth,
//                                              memberId, photo_url}
//                                              read by Request Flow,
//                                              Care Records, Membership
//   users/{uid}.dependents  [JSON strings]     {firstName, lastName, dob,
//                                              ssn, gender, relationship,
//                                              photo_url} read by Home,
//                                              written by OnboardingUpdate
//
// On load the three sources are merged by memberId, then by name. On
// every save or delete the subcollection is written first, then both
// arrays are rebuilt from it (unknown fields such as ssn are carried
// through untouched), plus numDeps / numDependents.
//
// BILLING: adding a person may change the monthly plan. This widget does
// not charge anything; it flags the change with `pendingBillingReview`
// on the user doc so support can reconcile until Zoho Payments is wired.
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

class JoviDependents extends StatefulWidget {
  const JoviDependents({
    Key? key,
    this.width,
    this.height,
  }) : super(key: key);

  final double? width;
  final double? height;

  @override
  State<JoviDependents> createState() => _JoviDependentsState();
}

// ═══════════════════════════════════════════════════════════════════════════
// MODEL
// ═══════════════════════════════════════════════════════════════════════════

const List<String> _relationships = [
  'Child',
  'Stepchild',
  'Parent',
  'Sibling',
  'Other',
];

const List<String> _genders = ['Female', 'Male', 'Non-binary', 'Prefer not to say'];

class _Dependent {
  final String memberId;
  final String firstName;
  final String lastName;
  final String dob; // MM/DD/YYYY, the format Onboarding writes
  final String gender;
  final String relationship;
  final String photoUrl;

  /// Extra keys from a legacy array entry (for example ssn) that this
  /// widget never edits but must not drop when it rewrites the arrays.
  final Map<String, dynamic> extra;

  const _Dependent({
    required this.memberId,
    required this.firstName,
    required this.lastName,
    this.dob = '',
    this.gender = '',
    this.relationship = '',
    this.photoUrl = '',
    this.extra = const {},
  });

  String get fullName => '$firstName $lastName'.trim();

  DateTime? get birthDate => _parseDob(dob);

  int? get ageYears {
    final b = birthDate;
    if (b == null) return null;
    final now = DateTime.now();
    var years = now.year - b.year;
    if (now.month < b.month || (now.month == b.month && now.day < b.day)) {
      years--;
    }
    return years < 0 ? 0 : years;
  }

  _Dependent copyWith({
    String? firstName,
    String? lastName,
    String? dob,
    String? gender,
    String? relationship,
    String? photoUrl,
  }) {
    return _Dependent(
      memberId: memberId,
      firstName: firstName ?? this.firstName,
      lastName: lastName ?? this.lastName,
      dob: dob ?? this.dob,
      gender: gender ?? this.gender,
      relationship: relationship ?? this.relationship,
      photoUrl: photoUrl ?? this.photoUrl,
      extra: extra,
    );
  }

  Map<String, dynamic> toSubcollection() => {
        'memberId': memberId,
        'firstName': firstName,
        'lastName': lastName,
        'dob': dob,
        'gender': gender,
        'relationship': relationship,
        'photoUrl': photoUrl,
        'updatedAt': FieldValue.serverTimestamp(),
      };

  /// Onboarding shape: {first, last, birth, memberId, photo_url}
  String toDepsJson() => jsonEncode({
        ...extra,
        'first': firstName,
        'last': lastName,
        'birth': dob,
        'memberId': memberId,
        'photo_url': photoUrl,
      });

  /// OnboardingUpdate shape: {firstName, lastName, dob, ssn, gender,
  /// relationship, photo_url}
  String toDependentsJson() => jsonEncode({
        ...extra,
        'firstName': firstName,
        'lastName': lastName,
        'dob': dob,
        'gender': gender,
        'relationship': relationship,
        'photo_url': photoUrl,
        'memberId': memberId,
      });

  factory _Dependent.fromSubcollection(String docId, Map<String, dynamic> m) {
    return _Dependent(
      memberId: (m['memberId'] as String?)?.trim().isNotEmpty == true
          ? (m['memberId'] as String).trim()
          : docId,
      firstName: (m['firstName'] as String?)?.trim() ?? '',
      lastName: (m['lastName'] as String?)?.trim() ?? '',
      dob: (m['dob'] as String?)?.trim() ?? '',
      gender: (m['gender'] as String?)?.trim() ?? '',
      relationship: (m['relationship'] as String?)?.trim() ?? '',
      photoUrl: (m['photoUrl'] as String?)?.trim() ??
          (m['photo_url'] as String?)?.trim() ??
          '',
    );
  }

  /// Accepts either legacy shape. Returns null when there is no name.
  static _Dependent? fromLegacy(dynamic raw) {
    Map<String, dynamic>? m;
    if (raw is String) {
      try {
        final parsed = jsonDecode(raw);
        if (parsed is Map) m = Map<String, dynamic>.from(parsed);
      } catch (_) {}
    } else if (raw is Map) {
      m = Map<String, dynamic>.from(raw);
    }
    if (m == null) return null;
    final first = ((m['firstName'] ?? m['first']) as String?)?.trim() ?? '';
    final last = ((m['lastName'] ?? m['last']) as String?)?.trim() ?? '';
    if (first.isEmpty && last.isEmpty) return null;
    final known = {
      'first', 'last', 'birth', 'memberId', 'photo_url', 'photoUrl',
      'firstName', 'lastName', 'dob', 'gender', 'relationship',
    };
    final extra = <String, dynamic>{};
    m.forEach((k, v) {
      if (!known.contains(k)) extra[k] = v;
    });
    return _Dependent(
      memberId: (m['memberId'] as String?)?.trim().isNotEmpty == true
          ? (m['memberId'] as String).trim()
          : 'name:${first.toLowerCase()}|${last.toLowerCase()}',
      firstName: first,
      lastName: last,
      dob: ((m['dob'] ?? m['birth']) as String?)?.trim() ?? '',
      gender: (m['gender'] as String?)?.trim() ?? '',
      relationship: (m['relationship'] as String?)?.trim() ?? '',
      photoUrl: ((m['photo_url'] ?? m['photoUrl']) as String?)?.trim() ?? '',
      extra: extra,
    );
  }
}

DateTime? _parseDob(String s) {
  if (s.isEmpty) return null;
  final iso = DateTime.tryParse(s);
  if (iso != null) return iso;
  final parts = s.split('/');
  if (parts.length == 3) {
    final mo = int.tryParse(parts[0]);
    final d = int.tryParse(parts[1]);
    final y = int.tryParse(parts[2]);
    if (mo != null && d != null && y != null) {
      try {
        return DateTime(y, mo, d);
      } catch (_) {}
    }
  }
  return null;
}

String _formatDob(DateTime d) => DateFormat('MM/dd/yyyy').format(d);

String _newMemberId() {
  final r = DateTime.now().microsecondsSinceEpoch.toRadixString(36);
  final salt = (DateTime.now().millisecond * 7919 + 13).toRadixString(36);
  return 'dep_$r$salt';
}

// ═══════════════════════════════════════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════════════════════════════════════

class _JoviDependentsState extends State<JoviDependents>
    with SingleTickerProviderStateMixin {
  List<_Dependent> _deps = [];
  Map<String, dynamic> _userData = {};
  bool _loading = true;
  bool _saving = false;
  String? _error;

  late final AnimationController _fadeCtrl;
  late final Animation<double> _fadeAnim;

  String? get _uid => FirebaseAuth.instance.currentUser?.uid;

  DocumentReference<Map<String, dynamic>>? get _userRef {
    final uid = _uid;
    if (uid == null) return null;
    return FirebaseFirestore.instance.collection('users').doc(uid);
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
    _fadeCtrl.dispose();
    super.dispose();
  }

  // ─── Load + merge ───────────────────────────────────────────────────

  Future<void> _load() async {
    final ref = _userRef;
    if (ref == null) {
      setState(() {
        _loading = false;
        _error = 'Sign in to manage your family.';
      });
      return;
    }
    try {
      final results = await Future.wait([
        ref.get(),
        ref.collection('dependents').get(),
      ]);
      final userSnap = results[0] as DocumentSnapshot<Map<String, dynamic>>;
      final subSnap = results[1] as QuerySnapshot<Map<String, dynamic>>;
      final data = userSnap.data() ?? {};

      final byId = <String, _Dependent>{};
      final byName = <String, String>{}; // normalized name → memberId

      void add(_Dependent d, {bool canonical = false}) {
        final nameKey = d.fullName.toLowerCase();
        final existingId = byName[nameKey];
        if (existingId != null && byId.containsKey(existingId)) {
          // Same person seen before: fill in blanks, keep canonical values.
          final e = byId[existingId]!;
          final merged = _Dependent(
            memberId: e.memberId,
            firstName: e.firstName.isNotEmpty ? e.firstName : d.firstName,
            lastName: e.lastName.isNotEmpty ? e.lastName : d.lastName,
            dob: e.dob.isNotEmpty ? e.dob : d.dob,
            gender: e.gender.isNotEmpty ? e.gender : d.gender,
            relationship:
                e.relationship.isNotEmpty ? e.relationship : d.relationship,
            photoUrl: e.photoUrl.isNotEmpty ? e.photoUrl : d.photoUrl,
            extra: {...d.extra, ...e.extra},
          );
          byId[existingId] = merged;
          return;
        }
        if (byId.containsKey(d.memberId) && !canonical) return;
        byId[d.memberId] = d;
        byName[nameKey] = d.memberId;
      }

      for (final doc in subSnap.docs) {
        try {
          add(_Dependent.fromSubcollection(doc.id, doc.data()), canonical: true);
        } catch (e) {
          debugPrint('Dependents: skipped malformed doc ${doc.id}: $e');
        }
      }
      for (final raw in (data['deps'] as List<dynamic>? ?? const [])) {
        final d = _Dependent.fromLegacy(raw);
        if (d != null) add(d);
      }
      for (final raw in (data['dependents'] as List<dynamic>? ?? const [])) {
        final d = _Dependent.fromLegacy(raw);
        if (d != null) add(d);
      }

      final list = byId.values.toList()
        ..sort((a, b) => a.fullName.toLowerCase().compareTo(b.fullName.toLowerCase()));

      if (!mounted) return;
      setState(() {
        _userData = data;
        _deps = list;
        _loading = false;
        _error = null;
      });
    } catch (e) {
      debugPrint('Dependents: load failed: $e');
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = 'Could not load your family right now.';
      });
    }
  }

  // ─── Persistence ────────────────────────────────────────────────────

  /// Writes the canonical doc, then rebuilds both legacy arrays from the
  /// in-memory list so every other widget sees the same people.
  Future<void> _persist(List<_Dependent> next, {String? removedId}) async {
    final ref = _userRef;
    if (ref == null) return;
    final batch = FirebaseFirestore.instance.batch();
    for (final d in next) {
      batch.set(ref.collection('dependents').doc(d.memberId), {
        ...d.toSubcollection(),
        'createdAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));
    }
    if (removedId != null) {
      batch.delete(ref.collection('dependents').doc(removedId));
    }
    batch.set(ref, {
      'deps': next.map((d) => d.toDepsJson()).toList(),
      'dependents': next.map((d) => d.toDependentsJson()).toList(),
      'numDeps': next.length,
      'numDependents': next.length,
      'dependentsUpdatedAt': FieldValue.serverTimestamp(),
      // No charge happens here. Flag for support / the Zoho wiring.
      'pendingBillingReview': true,
    }, SetOptions(merge: true));
    await batch.commit();
  }

  Future<void> _save(_Dependent d) async {
    if (_saving) return;
    setState(() => _saving = true);
    final next = [..._deps.where((x) => x.memberId != d.memberId), d]
      ..sort((a, b) => a.fullName.toLowerCase().compareTo(b.fullName.toLowerCase()));
    try {
      await _persist(next);
      if (!mounted) return;
      setState(() => _deps = next);
      HapticFeedback.mediumImpact();
      _toast('${d.firstName} saved', ok: true);
    } catch (e) {
      debugPrint('Dependents: save failed: $e');
      if (!mounted) return;
      _toast('Could not save. Please try again.', error: true);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _remove(_Dependent d) async {
    final ok = await showCupertinoDialog<bool>(
      context: context,
      builder: (ctx) => CupertinoAlertDialog(
        title: Text('Remove ${d.firstName}?'),
        content: const Padding(
          padding: EdgeInsets.only(top: 8),
          child: Text(
              'They will be removed from your plan and from care requests. Their past records stay in your history.'),
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
            child: const Text('Remove'),
          ),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    setState(() => _saving = true);
    final next = _deps.where((x) => x.memberId != d.memberId).toList();
    try {
      await _persist(next, removedId: d.memberId);
      if (!mounted) return;
      setState(() => _deps = next);
      HapticFeedback.mediumImpact();
      _toast('${d.firstName} removed');
    } catch (e) {
      debugPrint('Dependents: remove failed: $e');
      if (!mounted) return;
      _toast('Could not remove. Please try again.', error: true);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  void _toast(String msg, {bool ok = false, bool error = false}) {
    if (!mounted) return;
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(msg,
        accent: error
            ? _joviErrorRed
            : ok
                ? _joviMint
                : Colors.white70,
        icon: error
            ? CupertinoIcons.exclamationmark_circle
            : ok
                ? CupertinoIcons.checkmark_circle
                : CupertinoIcons.info_circle));
  }

  // ─── Editor ─────────────────────────────────────────────────────────

  Future<void> _openEditor([_Dependent? existing]) async {
    HapticFeedback.lightImpact();
    final result = await showModalBottomSheet<_Dependent>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      useSafeArea: true,
      builder: (ctx) => _DependentEditorSheet(existing: existing),
    );
    if (result != null) await _save(result);
  }

  // ─── Account people (read-only rows) ────────────────────────────────

  String get _primaryName {
    final d = _userData;
    final full = (d['onboard_fullName'] as String?)?.trim();
    if (full != null && full.isNotEmpty) return full;
    final first = (d['firstName'] as String?) ?? (d['first'] as String?) ?? '';
    final last = (d['lastName'] as String?) ?? (d['last'] as String?) ?? '';
    final joined = '$first $last'.trim();
    if (joined.isNotEmpty) return joined;
    return FirebaseAuth.instance.currentUser?.displayName ?? 'You';
  }

  String? get _spouseName {
    final d = _userData;
    final has = d['hasSpouse'] == true || d['spouse'] == true;
    if (!has) return null;
    final first =
        (d['spouseFirstName'] as String?) ?? (d['sFirst'] as String?) ?? '';
    final last =
        (d['spouseLastName'] as String?) ?? (d['sLast'] as String?) ?? '';
    final name = '$first $last'.trim();
    return name.isEmpty ? 'Spouse' : name;
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
                  'Family',
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
                      : '${_deps.length} dependent${_deps.length == 1 ? '' : 's'} on your plan',
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
            child: const Icon(CupertinoIcons.person_2_fill,
                color: _joviNavy, size: 20),
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
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Text(
            _error!,
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white.withOpacity(0.7),
              fontSize: 14,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      );
    }
    final spouse = _spouseName;
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
      children: [
        _sectionLabel('On this account'),
        const SizedBox(height: 8),
        _personRow(
          name: _primaryName,
          subtitle: 'Primary member',
          accent: _joviCoral,
          icon: CupertinoIcons.person_fill,
        ),
        if (spouse != null) ...[
          const SizedBox(height: 10),
          _personRow(
            name: spouse,
            subtitle: 'Spouse · edit in Profile',
            accent: _joviGold,
            icon: CupertinoIcons.person_fill,
          ),
        ],
        const SizedBox(height: 22),
        Row(
          children: [
            Expanded(child: _sectionLabel('Dependents')),
            if (_deps.isNotEmpty)
              _PressableMaterial(
                child: InkWell(
                  onTap: _saving ? null : () => _openEditor(),
                  borderRadius: BorderRadius.circular(10),
                  child: Padding(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: const [
                        Icon(CupertinoIcons.plus, color: _joviMint, size: 15),
                        SizedBox(width: 5),
                        Text(
                          'Add',
                          style: TextStyle(
                            color: _joviMint,
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                            letterSpacing: -0.2,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
          ],
        ),
        const SizedBox(height: 8),
        if (_deps.isEmpty) _buildEmpty() else ..._deps.map(_buildDependentCard),
        const SizedBox(height: 18),
        _buildBillingNote(),
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

  Widget _avatar(String name, String photoUrl, Color accent, {IconData? icon}) {
    if (photoUrl.isNotEmpty) {
      return ClipOval(
        child: Image.network(
          photoUrl,
          width: 46,
          height: 46,
          fit: BoxFit.cover,
          errorBuilder: (_, __, ___) => _initials(name, accent),
        ),
      );
    }
    if (icon != null) {
      return Container(
        width: 46,
        height: 46,
        decoration: BoxDecoration(
          color: accent.withOpacity(0.16),
          shape: BoxShape.circle,
          border: Border.all(color: accent.withOpacity(0.35), width: 0.8),
        ),
        child: Icon(icon, color: accent, size: 20),
      );
    }
    return _initials(name, accent);
  }

  Widget _initials(String name, Color accent) {
    final parts = name.trim().split(RegExp(r'\s+'));
    final ini = parts.take(2).map((p) => p.isEmpty ? '' : p[0]).join().toUpperCase();
    return Container(
      width: 46,
      height: 46,
      decoration: BoxDecoration(
        gradient: LinearGradient(colors: [accent, accent.withOpacity(0.7)]),
        shape: BoxShape.circle,
      ),
      alignment: Alignment.center,
      child: Text(
        ini.isEmpty ? '?' : ini,
        style: const TextStyle(
          color: Colors.white,
          fontSize: 16,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.3,
        ),
      ),
    );
  }

  Widget _personRow({
    required String name,
    required String subtitle,
    required Color accent,
    IconData? icon,
  }) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: RepaintBoundary(
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.06),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.white.withOpacity(0.1)),
          ),
          child: Row(
            children: [
              _avatar(name, '', accent, icon: icon),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      name,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 15.5,
                        fontWeight: FontWeight.w700,
                        letterSpacing: -0.3,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      subtitle,
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.55),
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDependentCard(_Dependent d) {
    final parts = <String>[];
    if (d.relationship.isNotEmpty) parts.add(d.relationship);
    final age = d.ageYears;
    if (age != null) parts.add('$age yr${age == 1 ? '' : 's'}');
    if (d.gender.isNotEmpty) parts.add(d.gender);
    final subtitle = parts.isEmpty ? 'Tap to add details' : parts.join(' · ');
    final incomplete = d.dob.isEmpty || d.relationship.isEmpty;

    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: _PressableMaterial(
        child: InkWell(
          onTap: _saving ? null : () => _openEditor(d),
          onLongPress: _saving ? null : () => _remove(d),
          borderRadius: BorderRadius.circular(16),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(16),
            child: RepaintBoundary(
              child: Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.08),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: incomplete
                        ? _joviGold.withOpacity(0.4)
                        : Colors.white.withOpacity(0.12),
                  ),
                ),
                child: Row(
                  children: [
                    _avatar(d.fullName, d.photoUrl, _joviMint),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            d.fullName,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 15.5,
                              fontWeight: FontWeight.w700,
                              letterSpacing: -0.3,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            subtitle,
                            style: TextStyle(
                              color: incomplete
                                  ? _joviGold
                                  : Colors.white.withOpacity(0.55),
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
      ),
    );
  }

  Widget _buildEmpty() {
    return ClipRRect(
      borderRadius: BorderRadius.circular(18),
      child: RepaintBoundary(
        child: Container(
          padding: const EdgeInsets.all(22),
          decoration: BoxDecoration(
            color: _joviMint.withOpacity(0.06),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: _joviMint.withOpacity(0.3), width: 1.2),
          ),
          child: Column(
            children: [
              Container(
                width: 60,
                height: 60,
                decoration: BoxDecoration(
                  color: _joviMint.withOpacity(0.16),
                  shape: BoxShape.circle,
                  border: Border.all(color: _joviMint.withOpacity(0.35)),
                ),
                child: const Icon(CupertinoIcons.person_add,
                    color: _joviMint, size: 26),
              ),
              const SizedBox(height: 14),
              const Text(
                'No dependents yet',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.4,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                'Add children or other family members so you can book care and file claims for them.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Colors.white.withOpacity(0.6),
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                  height: 1.4,
                ),
              ),
              const SizedBox(height: 16),
              _PressableMaterial(
                child: InkWell(
                  onTap: _saving ? null : () => _openEditor(),
                  borderRadius: BorderRadius.circular(13),
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 22, vertical: 13),
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                          colors: [_joviMint, _joviMintDark]),
                      borderRadius: BorderRadius.circular(13),
                      boxShadow: [
                        BoxShadow(
                          color: _joviMint.withOpacity(0.35),
                          blurRadius: 14,
                          offset: const Offset(0, 5),
                        ),
                      ],
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(CupertinoIcons.plus, color: _joviNavy, size: 17),
                        SizedBox(width: 7),
                        Text(
                          'Add a Dependent',
                          style: TextStyle(
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
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildBillingNote() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: _joviGold.withOpacity(0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: _joviGold.withOpacity(0.25), width: 0.8),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(CupertinoIcons.info_circle, color: _joviGoldDark, size: 16),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              'Adding or removing a family member can change your monthly plan. Our team confirms any change within one business day; nothing is charged from this screen. Hold a card to remove someone.',
              style: TextStyle(
                color: Colors.white.withOpacity(0.75),
                fontSize: 12,
                fontWeight: FontWeight.w500,
                height: 1.4,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// EDITOR SHEET
// ═══════════════════════════════════════════════════════════════════════════

class _DependentEditorSheet extends StatefulWidget {
  final _Dependent? existing;
  const _DependentEditorSheet({Key? key, this.existing}) : super(key: key);

  @override
  State<_DependentEditorSheet> createState() => _DependentEditorSheetState();
}

class _DependentEditorSheetState extends State<_DependentEditorSheet> {
  late final TextEditingController _first;
  late final TextEditingController _last;
  DateTime? _dob;
  String _gender = '';
  String _relationship = '';
  String? _nameError;

  bool get _isEditing => widget.existing != null;

  @override
  void initState() {
    super.initState();
    final e = widget.existing;
    _first = TextEditingController(text: e?.firstName ?? '');
    _last = TextEditingController(text: e?.lastName ?? '');
    _dob = e?.birthDate;
    _gender = e?.gender ?? '';
    _relationship = e?.relationship ?? '';
  }

  @override
  void dispose() {
    _first.dispose();
    _last.dispose();
    super.dispose();
  }

  Future<void> _pickDob() async {
    HapticFeedback.selectionClick();
    FocusScope.of(context).unfocus();
    final now = DateTime.now();
    var temp = _dob ?? DateTime(now.year - 8, now.month, now.day);
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
                      setState(() => _dob = temp);
                      Navigator.pop(ctx);
                    },
                    child: const Text('Done',
                        style: TextStyle(
                            color: _joviMint, fontWeight: FontWeight.w600)),
                  ),
                ],
              ),
              Expanded(
                child: CupertinoTheme(
                  data: const CupertinoThemeData(
                    brightness: Brightness.dark,
                    textTheme: CupertinoTextThemeData(
                      dateTimePickerTextStyle: TextStyle(
                          color: Colors.white, fontSize: 20),
                    ),
                  ),
                  child: CupertinoDatePicker(
                    mode: CupertinoDatePickerMode.date,
                    initialDateTime: temp,
                    minimumDate: DateTime(now.year - 110),
                    maximumDate: now,
                    onDateTimeChanged: (d) => temp = d,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _submit() {
    final first = _first.text.trim();
    final last = _last.text.trim();
    if (first.isEmpty || last.isEmpty) {
      HapticFeedback.mediumImpact();
      setState(() => _nameError = 'First and last name are required.');
      return;
    }
    HapticFeedback.lightImpact();
    final base = widget.existing ??
        _Dependent(memberId: _newMemberId(), firstName: first, lastName: last);
    Navigator.pop(
      context,
      base.copyWith(
        firstName: first,
        lastName: last,
        dob: _dob == null ? '' : _formatDob(_dob!),
        gender: _gender,
        relationship: _relationship,
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
                    _isEditing ? 'Edit Dependent' : 'Add a Dependent',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 20,
                      fontWeight: FontWeight.w700,
                      letterSpacing: -0.6,
                    ),
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Expanded(
                        child: _field(
                          controller: _first,
                          label: 'First name',
                          hint: 'Ava',
                          autofill: AutofillHints.givenName,
                          action: TextInputAction.next,
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _field(
                          controller: _last,
                          label: 'Last name',
                          hint: 'Rivera',
                          autofill: AutofillHints.familyName,
                          action: TextInputAction.done,
                          onSubmitted: (_) => _submit(),
                        ),
                      ),
                    ],
                  ),
                  if (_nameError != null) ...[
                    const SizedBox(height: 6),
                    Text(
                      _nameError!,
                      style: const TextStyle(
                        color: _joviErrorRed,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                  const SizedBox(height: 14),
                  _label('Date of birth'),
                  const SizedBox(height: 6),
                  _PressableMaterial(
                    child: InkWell(
                      onTap: _pickDob,
                      borderRadius: BorderRadius.circular(12),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 14, vertical: 14),
                        decoration: _boxDeco(),
                        child: Row(
                          children: [
                            const Icon(CupertinoIcons.calendar,
                                color: _joviMint, size: 18),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                _dob == null
                                    ? 'Select date'
                                    : DateFormat('MMMM d, yyyy').format(_dob!),
                                style: TextStyle(
                                  color: _dob == null
                                      ? Colors.white.withOpacity(0.35)
                                      : Colors.white,
                                  fontSize: 15,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                            Icon(Icons.chevron_right_rounded,
                                color: Colors.white.withOpacity(0.4), size: 20),
                          ],
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 14),
                  _label('Relationship'),
                  const SizedBox(height: 6),
                  _chips(_relationships, _relationship,
                      (v) => setState(() => _relationship = v)),
                  const SizedBox(height: 14),
                  _label('Gender'),
                  const SizedBox(height: 6),
                  _chips(_genders, _gender, (v) => setState(() => _gender = v)),
                  const SizedBox(height: 22),
                  _PressableMaterial(
                    child: InkWell(
                      onTap: _submit,
                      borderRadius: BorderRadius.circular(14),
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 15),
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                              colors: [_joviMint, _joviMintDark]),
                          borderRadius: BorderRadius.circular(14),
                          boxShadow: [
                            BoxShadow(
                              color: _joviMint.withOpacity(0.35),
                              blurRadius: 14,
                              offset: const Offset(0, 5),
                            ),
                          ],
                        ),
                        child: Center(
                          child: Text(
                            _isEditing ? 'Save Changes' : 'Add Dependent',
                            style: const TextStyle(
                              color: _joviNavy,
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
                    child: Text(
                      'Cancel',
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.6),
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
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

  BoxDecoration _boxDeco() => BoxDecoration(
        color: Colors.white.withOpacity(0.06),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: _joviMint.withOpacity(0.25)),
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

  Widget _field({
    required TextEditingController controller,
    required String label,
    required String hint,
    required String autofill,
    required TextInputAction action,
    ValueChanged<String>? onSubmitted,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _label(label),
        const SizedBox(height: 6),
        Container(
          decoration: _boxDeco(),
          child: TextField(
            controller: controller,
            textCapitalization: TextCapitalization.words,
            textInputAction: action,
            autofillHints: [autofill],
            onSubmitted: onSubmitted,
            onChanged: (_) {
              if (_nameError != null) setState(() => _nameError = null);
            },
            cursorColor: _joviMint,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 15,
              fontWeight: FontWeight.w600,
            ),
            decoration: InputDecoration(
              hintText: hint,
              hintStyle: TextStyle(
                color: Colors.white.withOpacity(0.3),
                fontSize: 14,
                fontWeight: FontWeight.w500,
              ),
              border: InputBorder.none,
              contentPadding:
                  const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
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
          _PressableMaterial(
            child: InkWell(
              onTap: () {
                HapticFeedback.selectionClick();
                onPick(o == selected ? '' : o);
              },
              borderRadius: BorderRadius.circular(11),
              child: AnimatedContainer(
                duration: _Motion.select,
                curve: _Motion.settle,
                padding:
                    const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
                decoration: BoxDecoration(
                  color: o == selected
                      ? _joviMint.withOpacity(0.2)
                      : Colors.white.withOpacity(0.05),
                  borderRadius: BorderRadius.circular(11),
                  border: Border.all(
                    color: o == selected
                        ? _joviMint.withOpacity(0.5)
                        : Colors.white.withOpacity(0.12),
                    width: 0.8,
                  ),
                ),
                child: Text(
                  o,
                  style: TextStyle(
                    color: o == selected
                        ? Colors.white
                        : Colors.white.withOpacity(0.65),
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.2,
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }
}
