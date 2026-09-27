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
// JOVI HEALTH — NOTIFICATIONS INBOX
// Version: 2026.09.23-r2 (membership, refill, support, vaccine kinds)
// Build: JC-INBOX-0923-002
//
// Widget Name (for FF): JoviNotificationsInbox
// Params (all optional): width, height
//
// One place for everything the app tells a member: claim status changes,
// appointment confirmations, pet medication reminders, failed payments,
// vet weight alerts. Reads users/{uid}/notifications, written by the
// `notifications.js` Cloud Functions (functions/notifications.js), which
// also send the matching push through the member's FCM tokens.
//
// DOC SCHEMA users/{uid}/notifications/{id}
//   type:      'claim' | 'pet_claim' | 'appointment' | 'pet_med' | 'payment'
//              | 'membership' | 'refill' | 'message' | 'weight' | 'vaccine'
//              | 'system'
//   title:     String
//   body:      String
//   route:     String?   FlutterFlow page name to open on tap
//   params:    Map<String, String>?   query parameters for that page
//   refPath:   String?   Firestore path of the record this is about
//   read:      bool
//   createdAt: Timestamp (server)
//   readAt:    Timestamp?
//
// Tap → marks read and opens `route`. Swipe left → deletes. "Mark all
// read" clears the unread count in one batch.
// ═══════════════════════════════════════════════════════════════════════════

import 'dart:async';
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
const Color _petAccent = Color(0xFFA78BFA);


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

class JoviNotificationsInbox extends StatefulWidget {
  const JoviNotificationsInbox({
    Key? key,
    this.width,
    this.height,
  }) : super(key: key);

  final double? width;
  final double? height;

  @override
  State<JoviNotificationsInbox> createState() => _JoviNotificationsInboxState();
}

// ═══════════════════════════════════════════════════════════════════════════
// MODEL
// ═══════════════════════════════════════════════════════════════════════════

enum _Kind { claim, appointment, petMed, payment, membership, refill, message, weight, vaccine, system }

_Kind _kindParse(String? s) {
  switch ((s ?? '').toLowerCase()) {
    case 'claim':
    case 'pet_claim':
      return _Kind.claim;
    case 'appointment':
    case 'request':
      return _Kind.appointment;
    case 'pet_med':
    case 'medication':
    case 'reminder':
      return _Kind.petMed;
    case 'payment':
    case 'billing':
      return _Kind.payment;
    case 'membership':
    case 'renewal':
      return _Kind.membership;
    case 'refill':
    case 'prescription':
      return _Kind.refill;
    case 'message':
    case 'support':
    case 'chat':
      return _Kind.message;
    case 'weight':
    case 'weight_alert':
      return _Kind.weight;
    case 'vaccine':
    case 'vaccination':
      return _Kind.vaccine;
    default:
      return _Kind.system;
  }
}

IconData _kindIcon(_Kind k) {
  switch (k) {
    case _Kind.claim:
      return CupertinoIcons.doc_text;
    case _Kind.appointment:
      return CupertinoIcons.calendar;
    case _Kind.petMed:
      return CupertinoIcons.capsule;
    case _Kind.payment:
      return CupertinoIcons.creditcard;
    case _Kind.membership:
      return CupertinoIcons.star_circle;
    case _Kind.refill:
      return CupertinoIcons.bag;
    case _Kind.message:
      return CupertinoIcons.chat_bubble_2;
    case _Kind.weight:
      return CupertinoIcons.chart_bar;
    case _Kind.vaccine:
      return CupertinoIcons.bandage;
    case _Kind.system:
      return CupertinoIcons.bell;
  }
}

Color _kindColor(_Kind k) {
  switch (k) {
    case _Kind.claim:
      return _joviMint;
    case _Kind.appointment:
      return _joviCoral;
    case _Kind.petMed:
      return _petAccent;
    case _Kind.payment:
      return _joviErrorRed;
    case _Kind.membership:
      return _joviGold;
    case _Kind.refill:
      return _joviMint;
    case _Kind.message:
      return _joviCoral;
    case _Kind.weight:
      return _joviGold;
    case _Kind.vaccine:
      return _joviMint;
    case _Kind.system:
      return Colors.white70;
  }
}

String _kindLabel(_Kind k) {
  switch (k) {
    case _Kind.claim:
      return 'Claims';
    case _Kind.appointment:
      return 'Appointments';
    case _Kind.petMed:
      return 'Pet meds';
    case _Kind.payment:
      return 'Billing';
    case _Kind.membership:
      return 'Membership';
    case _Kind.refill:
      return 'Refills';
    case _Kind.message:
      return 'Support';
    case _Kind.weight:
      return 'Weight';
    case _Kind.vaccine:
      return 'Vaccines';
    case _Kind.system:
      return 'Jovi';
  }
}

class _Note {
  final String id;
  final _Kind kind;
  final String title;
  final String body;
  final String? route;
  final Map<String, String> params;
  final String? refPath;
  final bool read;
  final DateTime createdAt;

  const _Note({
    required this.id,
    required this.kind,
    required this.title,
    required this.body,
    this.route,
    this.params = const {},
    this.refPath,
    required this.read,
    required this.createdAt,
  });

  factory _Note.fromDoc(String id, Map<String, dynamic> m) {
    final rawParams = m['params'];
    final params = <String, String>{};
    if (rawParams is Map) {
      rawParams.forEach((k, v) {
        if (v != null) params['$k'] = '$v';
      });
    }
    final ts = m['createdAt'];
    DateTime created;
    if (ts is Timestamp) {
      created = ts.toDate();
    } else if (ts is String) {
      created = DateTime.tryParse(ts) ?? DateTime.now();
    } else {
      created = DateTime.now();
    }
    return _Note(
      id: id,
      kind: _kindParse(m['type'] as String?),
      title: (m['title'] as String?)?.trim() ?? 'Notification',
      body: (m['body'] as String?)?.trim() ?? '',
      route: (m['route'] as String?)?.trim(),
      params: params,
      refPath: m['refPath'] as String?,
      read: m['read'] == true,
      createdAt: created,
    );
  }
}

enum _Filter { all, unread }

// ═══════════════════════════════════════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════════════════════════════════════

class _JoviNotificationsInboxState extends State<JoviNotificationsInbox>
    with SingleTickerProviderStateMixin {
  List<_Note> _notes = [];
  bool _loading = true;
  String? _error;
  _Filter _filter = _Filter.all;
  StreamSubscription<QuerySnapshot<Map<String, dynamic>>>? _sub;

  late final AnimationController _fadeCtrl;
  late final Animation<double> _fadeAnim;

  CollectionReference<Map<String, dynamic>>? get _col {
    final uid = FirebaseAuth.instance.currentUser?.uid;
    if (uid == null) return null;
    return FirebaseFirestore.instance
        .collection('users')
        .doc(uid)
        .collection('notifications');
  }

  List<_Note> get _visible =>
      _filter == _Filter.unread ? _notes.where((n) => !n.read).toList() : _notes;

  int get _unreadCount => _notes.where((n) => !n.read).length;

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
    _subscribe();
  }

  @override
  void dispose() {
    _sub?.cancel();
    _fadeCtrl.dispose();
    super.dispose();
  }

  void _subscribe() {
    final col = _col;
    if (col == null) {
      setState(() {
        _loading = false;
        _error = 'Sign in to see your notifications.';
      });
      return;
    }
    _sub?.cancel();
    _sub = col
        .orderBy('createdAt', descending: true)
        .limit(100)
        .snapshots()
        .listen((snap) {
      if (!mounted) return;
      final list = <_Note>[];
      for (final d in snap.docs) {
        try {
          list.add(_Note.fromDoc(d.id, d.data()));
        } catch (e) {
          debugPrint('Inbox: skipped malformed notification ${d.id}: $e');
        }
      }
      setState(() {
        _notes = list;
        _loading = false;
        _error = null;
      });
    }, onError: (e) {
      debugPrint('Inbox: listener error: $e');
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = 'Could not load notifications.';
      });
    });
  }

  // ─── Actions ────────────────────────────────────────────────────────

  Future<void> _markRead(_Note n) async {
    if (n.read) return;
    try {
      await _col?.doc(n.id).update({
        'read': true,
        'readAt': FieldValue.serverTimestamp(),
      });
    } catch (e) {
      debugPrint('Inbox: mark read failed: $e');
    }
  }

  Future<void> _markAllRead() async {
    final col = _col;
    if (col == null) return;
    final unread = _notes.where((n) => !n.read).toList();
    if (unread.isEmpty) return;
    HapticFeedback.lightImpact();
    try {
      final batch = FirebaseFirestore.instance.batch();
      for (final n in unread) {
        batch.update(col.doc(n.id), {
          'read': true,
          'readAt': FieldValue.serverTimestamp(),
        });
      }
      await batch.commit();
    } catch (e) {
      debugPrint('Inbox: mark all read failed: $e');
      if (!mounted) return;
      _toast('Could not update notifications.', error: true);
    }
  }

  Future<void> _delete(_Note n) async {
    try {
      await _col?.doc(n.id).delete();
    } catch (e) {
      debugPrint('Inbox: delete failed: $e');
      if (!mounted) return;
      _toast('Could not delete that notification.', error: true);
    }
  }

  Future<void> _clearRead() async {
    final col = _col;
    if (col == null) return;
    final read = _notes.where((n) => n.read).toList();
    if (read.isEmpty) return;
    final ok = await showCupertinoDialog<bool>(
      context: context,
      builder: (ctx) => CupertinoAlertDialog(
        title: const Text('Clear Read Notifications?'),
        content: Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Text(
              'This removes ${read.length} notification${read.length == 1 ? '' : 's'} you have already read.'),
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
            child: const Text('Clear'),
          ),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    try {
      final batch = FirebaseFirestore.instance.batch();
      for (final n in read) {
        batch.delete(col.doc(n.id));
      }
      await batch.commit();
    } catch (e) {
      debugPrint('Inbox: clear read failed: $e');
      if (!mounted) return;
      _toast('Could not clear notifications.', error: true);
    }
  }

  void _open(_Note n) {
    HapticFeedback.selectionClick();
    _markRead(n);
    final route = n.route;
    if (route == null || route.isEmpty) return;
    // NOTE: pushNamed does not throw on an unknown page name at runtime,
    // so the route stored on the notification must be a real FlutterFlow
    // page name. The Cloud Function keeps those names in one table.
    try {
      if (n.params.isEmpty) {
        context.pushNamed(route);
      } else {
        context.pushNamed(route, queryParameters: n.params);
      }
    } catch (e) {
      debugPrint('Inbox: route $route failed: $e');
      _toast("Couldn't open that screen.", error: true);
    }
  }

  void _toast(String msg, {bool error = false}) {
    if (!mounted) return;
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(msg,
        accent: error ? _joviErrorRed : Colors.white70,
        icon: error
            ? CupertinoIcons.exclamationmark_circle
            : CupertinoIcons.info_circle));
  }

  void _showMoreMenu() {
    HapticFeedback.lightImpact();
    showCupertinoModalPopup<void>(
      context: context,
      builder: (ctx) => CupertinoActionSheet(
        actions: [
          CupertinoActionSheetAction(
            onPressed: () {
              Navigator.pop(ctx);
              _markAllRead();
            },
            child: const Text('Mark All as Read'),
          ),
          CupertinoActionSheetAction(
            isDestructiveAction: true,
            onPressed: () {
              Navigator.pop(ctx);
              _clearRead();
            },
            child: const Text('Clear Read Notifications'),
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

  // ─── Formatting ─────────────────────────────────────────────────────

  String _relative(DateTime d) {
    final diff = DateTime.now().difference(d);
    if (diff.inMinutes < 1) return 'Just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    if (diff.inDays < 7) return '${diff.inDays}d ago';
    return DateFormat('MMM d').format(d);
  }

  String _dayBucket(DateTime d) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final day = DateTime(d.year, d.month, d.day);
    final diff = today.difference(day).inDays;
    if (diff == 0) return 'Today';
    if (diff == 1) return 'Yesterday';
    if (diff < 7) return 'This week';
    return 'Earlier';
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
              _buildFilterRow(),
              Expanded(child: _buildBody()),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(8, 8, 8, 4),
      child: Row(
        children: [
          _PressableMaterial(
            child: InkWell(
              onTap: () {
                HapticFeedback.selectionClick();
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
                    size: 17,
                  ),
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
                  'Notifications',
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
                      : _unreadCount == 0
                          ? "You're all caught up"
                          : '$_unreadCount unread',
                  style: const TextStyle(
                    color: Color(0x88FFFFFF),
                    fontSize: 11.5,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
          if (_notes.isNotEmpty)
            _PressableMaterial(
              child: InkWell(
                onTap: _showMoreMenu,
                borderRadius: BorderRadius.circular(22),
                child: Semantics(
                  label: 'More options',
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
                      CupertinoIcons.ellipsis,
                      color: Colors.white.withOpacity(0.85),
                      size: 20,
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildFilterRow() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 6),
      child: Container(
        padding: const EdgeInsets.all(3),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.06),
          borderRadius: BorderRadius.circular(11),
          border: Border.all(color: Colors.white.withOpacity(0.1), width: 0.8),
        ),
        child: Row(
          children: [
            _filterChip(_Filter.all, 'All'),
            _filterChip(_Filter.unread,
                _unreadCount > 0 ? 'Unread ($_unreadCount)' : 'Unread'),
          ],
        ),
      ),
    );
  }

  Widget _filterChip(_Filter f, String label) {
    final selected = _filter == f;
    return Expanded(
      child: _PressableMaterial(
        child: InkWell(
          onTap: () {
            if (_filter == f) return;
            HapticFeedback.selectionClick();
            setState(() => _filter = f);
          },
          borderRadius: BorderRadius.circular(9),
          child: AnimatedContainer(
            duration: _Motion.select,
            curve: _Motion.settle,
            padding: const EdgeInsets.symmetric(vertical: 10),
            decoration: BoxDecoration(
              color: selected ? _joviCoral.withOpacity(0.22) : Colors.transparent,
              borderRadius: BorderRadius.circular(9),
              border: selected
                  ? Border.all(color: _joviCoral.withOpacity(0.4), width: 0.8)
                  : null,
            ),
            child: Center(
              child: Text(
                label,
                style: TextStyle(
                  color: selected ? Colors.white : Colors.white.withOpacity(0.55),
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  letterSpacing: -0.2,
                ),
              ),
            ),
          ),
        ),
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
            valueColor: AlwaysStoppedAnimation<Color>(_joviCoral),
          ),
        ),
      );
    }
    if (_error != null) return _buildEmpty(_error!, CupertinoIcons.wifi_slash);
    final visible = _visible;
    if (visible.isEmpty) {
      return _buildEmpty(
        _filter == _Filter.unread
            ? 'No unread notifications'
            : 'Nothing here yet',
        CupertinoIcons.bell_slash,
        subtitle: _filter == _Filter.unread
            ? "You've read everything."
            : 'Claim updates, appointment confirmations, reminders and billing alerts will show up here.',
      );
    }

    // Group by day bucket, preserving order.
    final sections = <String, List<_Note>>{};
    for (final n in visible) {
      sections.putIfAbsent(_dayBucket(n.createdAt), () => []).add(n);
    }
    final children = <Widget>[];
    sections.forEach((label, items) {
      children.add(Padding(
        padding: const EdgeInsets.fromLTRB(4, 10, 4, 8),
        child: Text(
          label,
          style: TextStyle(
            color: Colors.white.withOpacity(0.6),
            fontSize: 13,
            fontWeight: FontWeight.w600,
            letterSpacing: -0.1,
          ),
        ),
      ));
      for (final n in items) {
        children.add(Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: _buildCard(n),
        ));
      }
    });
    return ListView(
      padding: const EdgeInsets.fromLTRB(14, 4, 14, 24),
      children: children,
    );
  }

  Widget _buildCard(_Note n) {
    final color = _kindColor(n.kind);
    return Dismissible(
      key: ValueKey('note_${n.id}'),
      direction: DismissDirection.endToStart,
      background: Container(
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.symmetric(horizontal: 22),
        decoration: BoxDecoration(
          color: _joviErrorRed,
          borderRadius: BorderRadius.circular(16),
        ),
        child: const Icon(CupertinoIcons.trash, color: Colors.white, size: 22),
      ),
      onDismissed: (_) {
        HapticFeedback.lightImpact();
        setState(() => _notes.removeWhere((x) => x.id == n.id));
        _delete(n);
      },
      child: _PressableMaterial(
        child: InkWell(
          onTap: () => _open(n),
          borderRadius: BorderRadius.circular(16),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(16),
            child: RepaintBoundary(
              child: Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(n.read ? 0.05 : 0.09),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: n.read
                        ? Colors.white.withOpacity(0.1)
                        : color.withOpacity(0.35),
                    width: 1,
                  ),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      width: 42,
                      height: 42,
                      decoration: BoxDecoration(
                        color: color.withOpacity(0.16),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: color.withOpacity(0.35),
                          width: 0.8,
                        ),
                      ),
                      child: Icon(_kindIcon(n.kind), color: color, size: 20),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Expanded(
                                child: Text(
                                  n.title,
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                  style: TextStyle(
                                    color: Colors.white,
                                    fontSize: 15,
                                    fontWeight:
                                        n.read ? FontWeight.w600 : FontWeight.w700,
                                    letterSpacing: -0.3,
                                    height: 1.25,
                                  ),
                                ),
                              ),
                              if (!n.read) ...[
                                const SizedBox(width: 8),
                                Container(
                                  margin: const EdgeInsets.only(top: 6),
                                  width: 8,
                                  height: 8,
                                  decoration: BoxDecoration(
                                    color: _joviCoral,
                                    shape: BoxShape.circle,
                                    boxShadow: [
                                      BoxShadow(
                                        color: _joviCoral.withOpacity(0.6),
                                        blurRadius: 6,
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ],
                          ),
                          if (n.body.isNotEmpty) ...[
                            const SizedBox(height: 3),
                            Text(
                              n.body,
                              maxLines: 3,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                color: Colors.white.withOpacity(0.7),
                                fontSize: 13,
                                fontWeight: FontWeight.w500,
                                height: 1.4,
                              ),
                            ),
                          ],
                          const SizedBox(height: 8),
                          Row(
                            children: [
                              Text(
                                _kindLabel(n.kind),
                                style: TextStyle(
                                  color: color.withOpacity(0.95),
                                  fontSize: 11.5,
                                  fontWeight: FontWeight.w700,
                                  letterSpacing: -0.1,
                                ),
                              ),
                              const SizedBox(width: 8),
                              Container(
                                width: 3,
                                height: 3,
                                decoration: BoxDecoration(
                                  color: Colors.white.withOpacity(0.3),
                                  shape: BoxShape.circle,
                                ),
                              ),
                              const SizedBox(width: 8),
                              Text(
                                _relative(n.createdAt),
                                style: TextStyle(
                                  color: Colors.white.withOpacity(0.5),
                                  fontSize: 11.5,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                              const Spacer(),
                              if (n.route != null && n.route!.isNotEmpty)
                                Icon(
                                  Icons.chevron_right_rounded,
                                  color: Colors.white.withOpacity(0.35),
                                  size: 18,
                                ),
                            ],
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
    );
  }

  Widget _buildEmpty(String title, IconData icon, {String? subtitle}) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.05),
                shape: BoxShape.circle,
                border: Border.all(
                  color: Colors.white.withOpacity(0.12),
                  width: 1,
                ),
              ),
              child: Icon(icon, color: Colors.white.withOpacity(0.45), size: 30),
            ),
            const SizedBox(height: 18),
            Text(
              title,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 17,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.4,
              ),
            ),
            if (subtitle != null) ...[
              const SizedBox(height: 6),
              Text(
                subtitle,
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Colors.white.withOpacity(0.55),
                  fontSize: 13.5,
                  fontWeight: FontWeight.w500,
                  height: 1.4,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
