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
// JOVI HEALTH — RECENT ACTIVITY (NAVY + GLASS)
// Version: 2026.09.22-r2 (Apple HIG pass: press feedback, painted glass
//          rows, calendar-day labels, Reduce Motion, title-case status)
// r1:      2026.07.11
// Full rebrand from legacy Kurv blue. Same data sources, filters,
// search, and routes. Adds skeleton loading, staggered card
// entrances, Jovi Pass badge, and mounted-safe async.
// ============================================================

import 'dart:ui' as ui_dart;
import 'dart:async';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:intl/intl.dart';
import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';

// Jovi Health Brand Colors (private to avoid cross-widget collisions)
const Color _joviCoral = Color(0xFFFF6B4A);
const Color _joviCoralLight = Color(0xFFFF8F73);
const Color _joviNavy = Color(0xFF1A2744);
const Color _joviNavyDark = Color(0xFF0F1A2E);
const Color _joviNavyLight = Color(0xFF243352);
const Color _joviMint = Color(0xFF00D4AA);
const Color _joviGold = Color(0xFFFFD166);
const Color _joviRed = Color(0xFFFF5A5A);

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

class RecentActivityWidget extends StatefulWidget {
  const RecentActivityWidget({
    Key? key,
    this.width,
    this.height,
  }) : super(key: key);

  final double? width;
  final double? height;

  @override
  State<RecentActivityWidget> createState() => _RecentActivityWidgetState();
}

class _RecentActivityWidgetState extends State<RecentActivityWidget>
    with TickerProviderStateMixin {
  // State variables
  bool _isLoading = true;
  List<Map<String, dynamic>> _allActivities = [];
  List<Map<String, dynamic>> _filteredActivities = [];
  String _searchQuery = '';
  String? _selectedFilter;
  final TextEditingController _searchController = TextEditingController();
  Timer? _searchDebounce;
  DateTime? _lastRefreshTime;

  // Animation controllers
  late AnimationController _fadeController;
  late AnimationController _slideController;
  late AnimationController _shimmerController;
  late Animation<double> _fadeAnimation;
  late Animation<Offset> _slideAnimation;

  // Filter options
  final Map<String, Map<String, dynamic>> _filterOptions = {
    'all': {'label': 'All Activity', 'icon': Icons.dashboard},
    'appointments': {'label': 'Appointments', 'icon': Icons.medical_services},
    'claims': {'label': 'Claims & Receipts', 'icon': Icons.receipt_long},
    'refills': {'label': 'Prescriptions', 'icon': Icons.medication},
  };

  @override
  void initState() {
    super.initState();
    _selectedFilter = 'all';
    _initializeAnimations();
    _loadActivities();
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
    // Skeleton pulse: runs only while loading (stopped in _loadActivities)
    // and not at all under Reduce Motion.
    _shimmerController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1100),
    );
    if (!_platformReduceMotion()) _shimmerController.repeat(reverse: true);

    _fadeAnimation = CurvedAnimation(
      parent: _fadeController,
      curve: Curves.easeOut,
    );
    _slideAnimation = Tween<Offset>(
      begin: _platformReduceMotion() ? Offset.zero : const Offset(0, 0.04),
      end: Offset.zero,
    ).animate(CurvedAnimation(
      parent: _slideController,
      curve: _Motion.settle,
    ));

    _fadeController.forward();
    _slideController.forward();
  }

  @override
  void dispose() {
    _fadeController.dispose();
    _slideController.dispose();
    _shimmerController.dispose();
    _searchController.dispose();
    _searchDebounce?.cancel();
    super.dispose();
  }

  Future<void> _loadActivities() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return;

    if (mounted) setState(() => _isLoading = true);
    if (!_shimmerController.isAnimating && !_platformReduceMotion()) {
      _shimmerController.repeat(reverse: true);
    }

    try {
      List<Map<String, dynamic>> activities = [];

      // Fetch appointments
      final appointmentsSnapshot = await FirebaseFirestore.instance
          .collection('requests')
          .where('userId', isEqualTo: user.uid)
          .get();

      for (var doc in appointmentsSnapshot.docs) {
        final data = doc.data();
        DateTime? appointmentDateTime;

        if (data['appointmentDate'] != null) {
          try {
            final dateStr = data['appointmentDate'] as String;
            appointmentDateTime = DateTime.parse(dateStr);
          } catch (e) {
            continue;
          }
        }

        if (appointmentDateTime != null) {
          activities.add({
            'activityType': 'appointment',
            'id': doc.id,
            'visitType': data['visitType'] ?? 'Appointment',
            'status': data['status'] ?? 'pending',
            'appointmentDate': data['appointmentDate'],
            'appointmentTime': data['appointmentTime'],
            'visitMode': data['visitMode'],
            'clinic': data['clinic'],
            'symptom': data['symptom'],
            'priority': data['priority'] ?? false,
            'patientName': data['patientName'],
            'sortDate': appointmentDateTime,
          });
        }
      }

      // Fetch claims/receipts
      try {
        final claimsSnapshot = await FirebaseFirestore.instance
            .collection('users')
            .doc(user.uid)
            .collection('claims')
            .get();

        for (var doc in claimsSnapshot.docs) {
          final data = doc.data();
          DateTime? claimDate;

          if (data['date'] != null && data['date'] is Timestamp) {
            claimDate = (data['date'] as Timestamp).toDate();
          } else if (data['submittedAt'] != null &&
              data['submittedAt'] is Timestamp) {
            claimDate = (data['submittedAt'] as Timestamp).toDate();
          }

          if (claimDate != null) {
            activities.add({
              'activityType': 'claim',
              'id': doc.id,
              'type': data['type'] ?? 'claim',
              'amount': data['amount'],
              'status': data['status'] ?? 'Pending',
              'provider': data['provider'],
              'reason': data['reason'],
              'sortDate': claimDate,
            });
          }
        }
      } catch (e) {
        // Claims unavailable — continue with other sources.
      }

      // Fetch prescription refills
      try {
        final refillsSnapshot = await FirebaseFirestore.instance
            .collection('prescriptionRefills')
            .where('userId', isEqualTo: user.uid)
            .get();

        for (var doc in refillsSnapshot.docs) {
          final data = doc.data();
          DateTime? refillDate;

          if (data['requestedDate'] != null &&
              data['requestedDate'] is Timestamp) {
            refillDate = (data['requestedDate'] as Timestamp).toDate();
          }

          if (refillDate != null) {
            activities.add({
              'activityType': 'refill',
              'id': doc.id,
              'medicationName': data['medicationName'],
              'pharmacyName': data['pharmacyName'],
              'status': data['status'] ?? 'requested',
              'rxNumber': data['rxNumber'],
              'sortDate': refillDate,
            });
          }
        }
      } catch (e) {
        // Refills unavailable — continue with other sources.
      }

      // Sort by date (most recent first)
      activities.sort((a, b) {
        final dateA = a['sortDate'] as DateTime;
        final dateB = b['sortDate'] as DateTime;
        return dateB.compareTo(dateA);
      });

      if (!mounted) return;
      setState(() {
        _allActivities = activities;
        _filteredActivities = activities;
        _lastRefreshTime = DateTime.now();
        _isLoading = false;
      });

      _shimmerController.stop();
      _applyFilters();
      _fadeController.forward(from: 0);
      _slideController.forward(from: 0);
    } catch (e) {
      if (!mounted) return;
      _shimmerController.stop();
      setState(() => _isLoading = false);
    }
  }

  void _applyFilters() {
    List<Map<String, dynamic>> filtered = List.from(_allActivities);

    // Apply type filter
    if (_selectedFilter != 'all') {
      switch (_selectedFilter) {
        case 'appointments':
          filtered = filtered
              .where((activity) => activity['activityType'] == 'appointment')
              .toList();
          break;
        case 'claims':
          filtered = filtered
              .where((activity) => activity['activityType'] == 'claim')
              .toList();
          break;
        case 'refills':
          filtered = filtered
              .where((activity) => activity['activityType'] == 'refill')
              .toList();
          break;
      }
    }

    // Apply search filter
    if (_searchQuery.isNotEmpty) {
      filtered = filtered.where((activity) {
        final searchLower = _searchQuery.toLowerCase();
        final type = activity['activityType'];

        if (type == 'appointment') {
          return (activity['visitType']?.toString().toLowerCase() ?? '')
                  .contains(searchLower) ||
              (activity['symptom']?.toString().toLowerCase() ?? '')
                  .contains(searchLower) ||
              (activity['clinic']?.toString().toLowerCase() ?? '')
                  .contains(searchLower) ||
              (activity['patientName']?.toString().toLowerCase() ?? '')
                  .contains(searchLower);
        } else if (type == 'claim') {
          return (activity['provider']?.toString().toLowerCase() ?? '')
                  .contains(searchLower) ||
              (activity['reason']?.toString().toLowerCase() ?? '')
                  .contains(searchLower) ||
              activity['amount'].toString().contains(searchLower);
        } else if (type == 'refill') {
          return (activity['medicationName']?.toString().toLowerCase() ?? '')
                  .contains(searchLower) ||
              (activity['pharmacyName']?.toString().toLowerCase() ?? '')
                  .contains(searchLower);
        }
        return false;
      }).toList();
    }

    if (!mounted) return;
    setState(() {
      _filteredActivities = filtered;
    });
  }

  void _onSearchChanged(String value) {
    if (_searchDebounce?.isActive ?? false) _searchDebounce!.cancel();
    _searchDebounce = Timer(const Duration(milliseconds: 300), () {
      if (!mounted) return;
      _searchQuery = value.toLowerCase();
      _applyFilters(); // calls setState itself
    });
  }

  String _formatDate(DateTime date) {
    // Compare calendar days, not elapsed hours (a midnight-stamped
    // appointment nine hours away used to fall through to a bare date).
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final day = DateTime(date.year, date.month, date.day);
    final dayDiff = day.difference(today).inDays;

    if (dayDiff == 0) {
      return 'Today';
    } else if (dayDiff == 1) {
      return 'Tomorrow';
    } else if (dayDiff == -1) {
      return 'Yesterday';
    } else if (dayDiff > 1 && dayDiff < 7) {
      return DateFormat('EEEE').format(date);
    } else {
      return DateFormat('MMM d, yyyy').format(date);
    }
  }

  String _getTimeAgo(DateTime date) {
    final now = DateTime.now();
    final difference = now.difference(date);

    if (difference.inDays > 30) {
      final months = (difference.inDays / 30).floor();
      return '$months month${months > 1 ? 's' : ''} ago';
    } else if (difference.inDays > 0) {
      return '${difference.inDays} day${difference.inDays > 1 ? 's' : ''} ago';
    } else if (difference.inHours > 0) {
      return '${difference.inHours} hour${difference.inHours > 1 ? 's' : ''} ago';
    } else if (difference.inMinutes > 0) {
      return '${difference.inMinutes} minute${difference.inMinutes > 1 ? 's' : ''} ago';
    } else {
      return 'Just now';
    }
  }

  String _statusLabel(String status) {
    final s = status.trim();
    if (s.isEmpty) return 'Pending';
    return s[0].toUpperCase() + s.substring(1).toLowerCase();
  }

  Color _getStatusColor(String status) {
    switch (status.toLowerCase()) {
      case 'confirmed':
      case 'approved':
      case 'completed':
        return _joviMint;
      case 'pending':
      case 'processing':
      case 'requested':
      case 'available':
        return _joviGold;
      case 'cancelled':
      case 'denied':
      case 'no-show':
        return _joviRed;
      default:
        return Colors.white.withOpacity(0.55);
    }
  }

  IconData _getActivityIcon(String type, Map<String, dynamic> data) {
    if (type == 'appointment') {
      final visitMode = data['visitMode'] ?? '';
      return visitMode == 'Virtual' ? Icons.video_call : Icons.medical_services;
    } else if (type == 'claim') {
      final claimType = data['type'] ?? 'claim';
      return claimType == 'receipt' ? Icons.receipt_long : Icons.file_present;
    } else if (type == 'refill') {
      return Icons.medication;
    }
    return Icons.circle;
  }

  String _getActivityTitle(String type, Map<String, dynamic> activity) {
    if (type == 'appointment') {
      return activity['visitType'] ?? 'Appointment';
    } else if (type == 'claim') {
      final claimType = activity['type'] == 'receipt' ? 'Receipt' : 'Claim';
      return '$claimType ${activity['provider'] ?? ''}';
    } else if (type == 'refill') {
      return 'Prescription Refill';
    }
    return 'Activity';
  }

  String _getActivitySubtitle(String type, Map<String, dynamic> activity) {
    if (type == 'appointment') {
      final mode = activity['visitMode'] ?? '';
      final clinic = activity['clinic'] ?? '';
      final symptom = activity['symptom'] ?? '';
      if (mode == 'Virtual') {
        return 'Virtual Visit${symptom.isNotEmpty ? ' - $symptom' : ''}';
      } else {
        return '$clinic${symptom.isNotEmpty ? ' - $symptom' : ''}';
      }
    } else if (type == 'claim') {
      final amount = activity['amount'] ?? 0;
      final reason = activity['reason'] ?? '';
      return reason.isNotEmpty ? reason : '\$${amount.toStringAsFixed(2)}';
    } else if (type == 'refill') {
      return '${activity['medicationName']} at ${activity['pharmacyName']}';
    }
    return '';
  }

  void _navigateToDetail(String type, Map<String, dynamic> activity) {
    if (type == 'appointment') {
      context.push('/appt');
    } else if (type == 'claim') {
      context.push('/fileclaim');
    } else if (type == 'refill') {
      context.push('/scriptRefill');
    }
  }

  // ── Glass helpers ──────────────────────────────────────────

  Widget _glassPanel({
    required Widget child,
    EdgeInsets padding = const EdgeInsets.all(16),
    double radius = 18,
    double opacity = 0.07,
    Color? borderTint,
  }) {
    // Painted glass: a live blur on every row of a ListView over an opaque
    // navy gradient was pure GPU cost. Opacity nudged up to compensate.
    return ClipRRect(
      borderRadius: BorderRadius.circular(radius),
      child: RepaintBoundary(
        child: Container(
          padding: padding,
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(opacity + 0.02),
            borderRadius: BorderRadius.circular(radius),
            border: Border.all(
              color: (borderTint ?? Colors.white)
                  .withOpacity(borderTint == null ? 0.13 : 0.35),
            ),
          ),
          child: child,
        ),
      ),
    );
  }

  // ── Header (title + refresh + search) ──────────────────────

  Widget _buildHeader() {
    return SafeArea(
      bottom: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
        child: Column(
          children: [
            Row(
              children: [
                _Pressable(
                    feedbackOnly: true,
                    pressedScale: 0.92,
                    child: _glassPanel(
                  padding: EdgeInsets.zero,
                  radius: 12,
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
                      child: const Padding(
                        padding: EdgeInsets.all(12),
                        child: Icon(
                          Icons.arrow_back_ios_new,
                          color: Colors.white,
                          size: 18,
                        ),
                      ),
                    ),
                  ),
                )),
                Expanded(
                  child: Column(
                    children: [
                      const Text(
                        'Recent Activity',
                        style: TextStyle(
                          fontSize: 17,
                          fontWeight: FontWeight.w600,
                          color: Colors.white,
                          letterSpacing: -0.4,
                        ),
                      ),
                      if (_lastRefreshTime != null)
                        Text(
                          'Updated ${_getTimeAgo(_lastRefreshTime!)}',
                          style: TextStyle(
                            fontSize: 12,
                            color: Colors.white.withOpacity(0.55),
                          ),
                        ),
                    ],
                  ),
                ),
                _Pressable(
                    feedbackOnly: true,
                    pressedScale: 0.92,
                    child: _glassPanel(
                  padding: EdgeInsets.zero,
                  radius: 12,
                  child: Material(
                    color: Colors.transparent,
                    child: InkWell(
                      borderRadius: BorderRadius.circular(12),
                      onTap: () {
                        HapticFeedback.lightImpact();
                        _loadActivities();
                      },
                      child: const Padding(
                        padding: EdgeInsets.all(12),
                        child: Icon(
                          Icons.refresh,
                          color: Colors.white,
                          size: 20,
                        ),
                      ),
                    ),
                  ),
                )),
              ],
            ),
            const SizedBox(height: 18),
            // Search bar
            _glassPanel(
              padding: EdgeInsets.zero,
              radius: 14,
              child: TextField(
                controller: _searchController,
                autocorrect: false,
                textInputAction: TextInputAction.search,
                style: const TextStyle(color: Colors.white, fontSize: 15),
                cursorColor: _joviCoral,
                decoration: InputDecoration(
                  hintText: 'Search activities',
                  hintStyle: TextStyle(color: Colors.white.withOpacity(0.45)),
                  prefixIcon: const Icon(Icons.search, color: _joviCoral),
                  suffixIcon: _searchQuery.isNotEmpty
                      ? IconButton(
                          icon: Icon(Icons.clear,
                              color: Colors.white.withOpacity(0.6)),
                          onPressed: () {
                            _searchController.clear();
                            _onSearchChanged('');
                            HapticFeedback.lightImpact();
                          },
                        )
                      : null,
                  border: InputBorder.none,
                  contentPadding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                ),
                onChanged: _onSearchChanged,
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ── Filter chips ───────────────────────────────────────────

  Widget _buildFilterChips() {
    return SizedBox(
      height: 46,
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 20),
        itemCount: _filterOptions.length,
        itemBuilder: (context, index) {
          final key = _filterOptions.keys.elementAt(index);
          final option = _filterOptions[key]!;
          final isSelected = _selectedFilter == key;

          return Padding(
            padding: const EdgeInsets.only(right: 8),
            child: _Pressable(
                feedbackOnly: true,
                pressedScale: 0.95,
                child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: () {
                  HapticFeedback.selectionClick();
                  _selectedFilter = key;
                  _applyFilters();
                },
                borderRadius: BorderRadius.circular(22),
                child: AnimatedContainer(
                  duration: _Motion.select,
                  curve: _Motion.settle,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 9),
                  decoration: BoxDecoration(
                    gradient: isSelected
                        ? const LinearGradient(
                            colors: [_joviCoral, _joviCoralLight],
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                          )
                        : null,
                    color: isSelected ? null : Colors.white.withOpacity(0.06),
                    borderRadius: BorderRadius.circular(22),
                    border: Border.all(
                      color: isSelected
                          ? _joviCoral
                          : Colors.white.withOpacity(0.14),
                      width: isSelected ? 1.5 : 1,
                    ),
                    boxShadow: isSelected
                        ? [
                            BoxShadow(
                              color: _joviCoral.withOpacity(0.4),
                              blurRadius: 12,
                              offset: const Offset(0, 3),
                            ),
                          ]
                        : null,
                  ),
                  child: Row(
                    children: [
                      Icon(
                        option['icon'],
                        size: 17,
                        color: isSelected
                            ? Colors.white
                            : Colors.white.withOpacity(0.6),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        option['label'],
                        style: TextStyle(
                          color: isSelected
                              ? Colors.white
                              : Colors.white.withOpacity(0.7),
                          fontWeight:
                              isSelected ? FontWeight.w700 : FontWeight.w500,
                          fontSize: 13.5,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            )),
          );
        },
      ),
    );
  }

  // ── Stats summary ──────────────────────────────────────────

  Widget _buildStatsSummary() {
    final totalActivities = _allActivities.length;
    final appointments =
        _allActivities.where((a) => a['activityType'] == 'appointment').length;
    final claims =
        _allActivities.where((a) => a['activityType'] == 'claim').length;
    final refills =
        _allActivities.where((a) => a['activityType'] == 'refill').length;

    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 14, 20, 2),
      child: _glassPanel(
        padding: const EdgeInsets.all(16),
        radius: 18,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Activity Summary',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: Colors.white.withOpacity(0.6),
                letterSpacing: -0.1,
              ),
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                _buildStatItem('Total', totalActivities, Icons.dashboard,
                    Colors.white.withOpacity(0.85)),
                const SizedBox(width: 10),
                _buildStatItem(
                    'Appts', appointments, Icons.medical_services, _joviCoral),
                const SizedBox(width: 10),
                _buildStatItem('Claims', claims, Icons.receipt_long, _joviGold),
                const SizedBox(width: 10),
                _buildStatItem('Refills', refills, Icons.medication, _joviMint),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatItem(String label, int value, IconData icon, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12),
        decoration: BoxDecoration(
          color: color.withOpacity(0.08),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: color.withOpacity(0.28)),
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 19),
            const SizedBox(height: 7),
            Text(
              value.toString(),
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w800,
                color: color,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              label,
              style: TextStyle(
                fontSize: 10.5,
                color: Colors.white.withOpacity(0.55),
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ── Activity cards ─────────────────────────────────────────

  Widget _buildActivityCard(Map<String, dynamic> activity, int index) {
    final type = activity['activityType'];
    final status = activity['status'] ?? '';
    final date = activity['sortDate'] as DateTime;
    final statusColor = _getStatusColor(status);

    // Staggered entrance: each card fades/slides in slightly later.
    final reduce = MediaQuery.maybeOf(context)?.disableAnimations ?? false;
    final card = TweenAnimationBuilder<double>(
      tween: Tween(begin: reduce ? 1.0 : 0.0, end: 1.0),
      duration: Duration(milliseconds: 300 + (index.clamp(0, 6) * 40)),
      curve: _Motion.settle,
      builder: (context, t, child) {
        return Opacity(
          opacity: t,
          child: Transform.translate(
            offset: Offset(0, 8 * (1 - t)),
            child: child,
          ),
        );
      },
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 6),
        child: _Pressable(
            feedbackOnly: true,
            pressedScale: 0.985,
            child: _glassPanel(
          padding: EdgeInsets.zero,
          radius: 18,
          child: Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: () {
                HapticFeedback.lightImpact();
                _navigateToDetail(type, activity);
              },
              borderRadius: BorderRadius.circular(18),
              splashColor: _joviCoral.withOpacity(0.08),
              highlightColor: _joviCoral.withOpacity(0.05),
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Row(
                  children: [
                    // Icon container
                    Container(
                      width: 48,
                      height: 48,
                      decoration: BoxDecoration(
                        color: statusColor.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(14),
                        border:
                            Border.all(color: statusColor.withOpacity(0.35)),
                      ),
                      child: Icon(
                        _getActivityIcon(type, activity),
                        color: statusColor,
                        size: 22,
                      ),
                    ),
                    const SizedBox(width: 14),
                    // Content
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Expanded(
                                child: Text(
                                  _getActivityTitle(type, activity),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(
                                    fontSize: 15.5,
                                    fontWeight: FontWeight.w700,
                                    color: Colors.white,
                                  ),
                                ),
                              ),
                              if (activity['priority'] == true)
                                Container(
                                  margin: const EdgeInsets.only(left: 8),
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 8, vertical: 3),
                                  decoration: BoxDecoration(
                                    color: _joviGold.withOpacity(0.16),
                                    borderRadius: BorderRadius.circular(10),
                                    border: Border.all(
                                        color: _joviGold.withOpacity(0.5)),
                                  ),
                                  child: const Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(Icons.flash_on,
                                          color: _joviGold, size: 11),
                                      SizedBox(width: 3),
                                      Text(
                                        'Jovi Pass',
                                        style: TextStyle(
                                          color: _joviGold,
                                          fontSize: 10.5,
                                          fontWeight: FontWeight.w700,
                                          letterSpacing: -0.1,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                            ],
                          ),
                          const SizedBox(height: 5),
                          Text(
                            _getActivitySubtitle(type, activity),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 13.5,
                              color: Colors.white.withOpacity(0.6),
                            ),
                          ),
                          const SizedBox(height: 9),
                          Row(
                            children: [
                              Icon(
                                Icons.calendar_today,
                                size: 13,
                                color: Colors.white.withOpacity(0.45),
                              ),
                              const SizedBox(width: 5),
                              Text(
                                _formatDate(date),
                                style: TextStyle(
                                  fontSize: 12,
                                  color: Colors.white.withOpacity(0.5),
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                              if (activity['appointmentTime'] != null &&
                                  activity['appointmentTime']
                                      .toString()
                                      .isNotEmpty) ...[
                                const SizedBox(width: 12),
                                Icon(
                                  Icons.access_time,
                                  size: 13,
                                  color: Colors.white.withOpacity(0.45),
                                ),
                                const SizedBox(width: 4),
                                Text(
                                  activity['appointmentTime'],
                                  style: TextStyle(
                                    fontSize: 12,
                                    color: Colors.white.withOpacity(0.5),
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                              ],
                              const Spacer(),
                              Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 9, vertical: 4),
                                decoration: BoxDecoration(
                                  color: statusColor.withOpacity(0.12),
                                  borderRadius: BorderRadius.circular(12),
                                  border: Border.all(
                                      color: statusColor.withOpacity(0.4)),
                                ),
                                child: Text(
                                  _statusLabel(status),
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.w700,
                                    letterSpacing: -0.1,
                                    color: statusColor,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 4),
                    Icon(
                      Icons.chevron_right,
                      color: Colors.white.withOpacity(0.35),
                      size: 22,
                    ),
                  ],
                ),
              ),
            ),
          ),
        )),
      ),
    );

    return SlideTransition(
      position: _slideAnimation,
      child: FadeTransition(opacity: _fadeAnimation, child: card),
    );
  }

  // ── Skeleton loading ───────────────────────────────────────

  Widget _buildSkeletonCard() {
    return AnimatedBuilder(
      animation: _shimmerController,
      builder: (context, _) {
        final pulse = 0.05 + (_shimmerController.value * 0.05);
        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 6),
          child: Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(pulse),
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: Colors.white.withOpacity(0.10)),
            ),
            child: Row(
              children: [
                Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.10),
                    borderRadius: BorderRadius.circular(14),
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        width: 140,
                        height: 12,
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.12),
                          borderRadius: BorderRadius.circular(6),
                        ),
                      ),
                      const SizedBox(height: 9),
                      Container(
                        width: 200,
                        height: 9,
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.08),
                          borderRadius: BorderRadius.circular(5),
                        ),
                      ),
                      const SizedBox(height: 9),
                      Container(
                        width: 90,
                        height: 9,
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.08),
                          borderRadius: BorderRadius.circular(5),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildLoadingState() {
    return ListView(
      padding: const EdgeInsets.only(top: 8, bottom: 100),
      physics: const NeverScrollableScrollPhysics(),
      children: List.generate(6, (_) => _buildSkeletonCard()),
    );
  }

  // ── Empty state ────────────────────────────────────────────

  Widget _buildEmptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(26),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: LinearGradient(
                  colors: [
                    _joviCoral.withOpacity(0.22),
                    _joviCoral.withOpacity(0.05),
                  ],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                border: Border.all(color: _joviCoral.withOpacity(0.35)),
              ),
              child: const Icon(
                Icons.history,
                size: 56,
                color: _joviCoral,
              ),
            ),
            const SizedBox(height: 24),
            Text(
              _searchQuery.isNotEmpty
                  ? 'No results found'
                  : 'No recent activity',
              style: const TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w700,
                color: Colors.white,
                letterSpacing: -0.4,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              _searchQuery.isNotEmpty
                  ? 'Try adjusting your search or filters'
                  : 'Your healthcare activities will appear here',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 15,
                color: Colors.white.withOpacity(0.6),
              ),
            ),
            if (_searchQuery.isEmpty) ...[
              const SizedBox(height: 30),
              _Pressable(
                  feedbackOnly: true,
                  child: Container(
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                      colors: [_joviCoral, _joviCoralLight]),
                  borderRadius: BorderRadius.circular(14),
                  boxShadow: [
                    BoxShadow(
                      color: _joviCoral.withOpacity(0.4),
                      blurRadius: 16,
                      offset: const Offset(0, 6),
                    ),
                  ],
                ),
                child: ElevatedButton.icon(
                  onPressed: () {
                    HapticFeedback.lightImpact();
                    context.push('/requests');
                  },
                  icon: const Icon(Icons.add),
                  label: const Text('Request Appointment'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.transparent,
                    foregroundColor: Colors.white,
                    shadowColor: Colors.transparent,
                    elevation: 0,
                    padding: const EdgeInsets.symmetric(
                        horizontal: 24, vertical: 14),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14),
                    ),
                    textStyle: const TextStyle(
                        fontWeight: FontWeight.w600, fontSize: 15),
                  ),
                ),
              )),
            ],
          ],
        ),
      ),
    );
  }

  // ── Build ──────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return Container(
      width: widget.width ?? MediaQuery.of(context).size.width,
      height: widget.height ?? MediaQuery.of(context).size.height,
      child: Scaffold(
        backgroundColor: _joviNavyDark,
        body: Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [_joviNavyDark, _joviNavy, _joviNavyDark],
              stops: [0.0, 0.5, 1.0],
            ),
          ),
          child: RefreshIndicator(
            onRefresh: _loadActivities,
            color: _joviCoral,
            backgroundColor: _joviNavyLight,
            child: Column(
              children: [
                _buildHeader(),
                const SizedBox(height: 14),
                _buildFilterChips(),
                if (!_isLoading && _filteredActivities.isNotEmpty)
                  _buildStatsSummary(),
                const SizedBox(height: 6),
                Expanded(
                  child: _isLoading
                      ? _buildLoadingState()
                      : _filteredActivities.isEmpty
                          ? _buildEmptyState()
                          : ListView.builder(
                              padding:
                                  const EdgeInsets.only(top: 4, bottom: 100),
                              itemCount: _filteredActivities.length,
                              itemBuilder: (context, index) {
                                return _buildActivityCard(
                                    _filteredActivities[index], index);
                              },
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
