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

import 'dart:async';
import 'dart:convert';
import 'dart:ui' as ui_dart;
import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:intl/intl.dart';
import 'package:uuid/uuid.dart';

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

class PetVaccinations extends StatefulWidget {
  /// Optional: open directly to a specific pet's vaccinations. When null,
  /// the widget shows a pet picker (if multiple pets) or jumps straight
  /// into the single pet's view.
  final String? petId;

  final double? width;
  final double? height;

  const PetVaccinations({
    Key? key,
    this.width,
    this.height,
    this.petId,
  }) : super(key: key);

  @override
  State<PetVaccinations> createState() => _PetVaccinationsState();
}

class _PetVaccinationsState extends State<PetVaccinations>
    with TickerProviderStateMixin {
  // ---------------- Pet data state ----------------
  List<_PetLite> _pets = [];
  _PetLite? _selectedPet;
  bool _loadingPets = true;
  String? _petsError;

  // ---------------- Vaccinations state ----------------
  List<_Vaccination> _vaccinations = [];
  bool _loadingVaccinations = false;
  String? _vaccinationsError;

  // ---------------- Subscriptions ----------------
  StreamSubscription<QuerySnapshot<Map<String, dynamic>>>? _vaccinationsSub;

  // ---------------- Animations ----------------
  late AnimationController _fadeCtrl;
  late Animation<double> _fadeAnim;

  // ---------------- Lifecycle ----------------

  @override
  void initState() {
    super.initState();
    _fadeCtrl = AnimationController(vsync: this, duration: _Motion.enter);
    _fadeAnim = CurvedAnimation(parent: _fadeCtrl, curve: Curves.easeOut);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      if (MediaQuery.of(context).disableAnimations) {
        _fadeCtrl.value = 1.0;
      } else {
        _fadeCtrl.forward();
      }
    });
    _loadPets();
    _analytics('pet_vaccinations_opened');
  }

  @override
  void dispose() {
    _fadeCtrl.dispose();
    _vaccinationsSub?.cancel();
    super.dispose();
  }

  // =======================================================================
  // LOAD PETS
  // Reads from subcollection first; falls back to legacy array entries
  // not yet in the subcollection. Deduplicates by petId.
  // =======================================================================

  Future<void> _loadPets() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      setState(() {
        _loadingPets = false;
        _petsError = 'Sign in to track your pets\' vaccinations.';
      });
      return;
    }

    try {
      final fs = FirebaseFirestore.instance;
      final results = await Future.wait([
        fs.collection('users').doc(user.uid).collection('pets').get(),
        fs.collection('users').doc(user.uid).get(),
      ]);
      final subDocs = results[0] as QuerySnapshot<Map<String, dynamic>>;
      final userDoc = results[1] as DocumentSnapshot<Map<String, dynamic>>;

      final byId = <String, _PetLite>{};
      // Subcollection — canonical
      for (final doc in subDocs.docs) {
        final data = doc.data();
        if (data['archived'] == true) continue;
        try {
          final pet = _PetLite.fromSubcollection(doc.id, data);
          byId[pet.petId] = pet;
        } catch (e) {
          _logError('skipped malformed pet ${doc.id}', e);
        }
      }
      // Legacy array — fallback for pets not yet in subcollection
      if (userDoc.exists) {
        final data = userDoc.data() as Map<String, dynamic>;
        final rawPets = data['pets'] as List<dynamic>? ?? [];
        for (final raw in rawPets) {
          _PetLite? pet;
          if (raw is String) {
            pet = _PetLite.fromLegacyJson(raw);
          } else if (raw is Map) {
            try {
              final m = Map<String, dynamic>.from(raw);
              final petId = (m['petId'] as String?)?.trim();
              if (petId != null && petId.isNotEmpty) {
                pet = _PetLite.fromSubcollection(petId, m);
              }
            } catch (_) {/* skip */}
          }
          if (pet != null && !byId.containsKey(pet.petId)) {
            byId[pet.petId] = pet;
          }
        }
      }

      final pets = byId.values.toList()
        ..sort((a, b) => a.name.toLowerCase().compareTo(b.name.toLowerCase()));

      if (!mounted) return;
      setState(() {
        _pets = pets;
        _loadingPets = false;
      });

      // Auto-select: either the petId passed in, or the only pet
      if (widget.petId != null) {
        final match = pets.firstWhere(
          (p) => p.petId == widget.petId,
          orElse: () => pets.isNotEmpty ? pets.first : _missingPetPlaceholder(),
        );
        _selectPet(match);
      } else if (pets.length == 1) {
        _selectPet(pets.first);
      }
    } catch (e) {
      _logError('load pets failed', e);
      if (!mounted) return;
      setState(() {
        _loadingPets = false;
        _petsError = 'Could not load your pets. Please try again.';
      });
    }
  }

  _PetLite _missingPetPlaceholder() {
    return const _PetLite(petId: '_missing_', name: 'Unknown pet');
  }

  // =======================================================================
  // SELECT PET
  // Switches the vaccinations view to a specific pet and subscribes to
  // their vaccinations subcollection.
  // =======================================================================

  void _selectPet(_PetLite pet) {
    if (pet.petId == '_missing_') return;
    HapticFeedback.selectionClick();
    setState(() {
      _selectedPet = pet;
      _loadingVaccinations = true;
      _vaccinations = [];
      _vaccinationsError = null;
    });
    _subscribeToVaccinations(pet.petId);
  }

  void _clearSelectedPet() {
    _vaccinationsSub?.cancel();
    setState(() {
      _selectedPet = null;
      _vaccinations = [];
      _loadingVaccinations = false;
    });
  }

  void _subscribeToVaccinations(String petId) {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return;
    _vaccinationsSub?.cancel();
    _vaccinationsSub = FirebaseFirestore.instance
        .collection('users')
        .doc(user.uid)
        .collection('pets')
        .doc(petId)
        .collection('vaccinations')
        .snapshots()
        .listen(
      (snap) {
        if (!mounted) return;
        final list = <_Vaccination>[];
        for (final doc in snap.docs) {
          try {
            list.add(_Vaccination.fromFirestore(doc.id, doc.data()));
          } catch (e) {
            _logError('skipped malformed vaccination ${doc.id}', e);
          }
        }
        // Sort by administeredDate, most recent first
        list.sort((a, b) => b.administeredDate.compareTo(a.administeredDate));
        setState(() {
          _vaccinations = list;
          _loadingVaccinations = false;
          _vaccinationsError = null;
        });
      },
      onError: (err) {
        _logError('vaccinations subscription failed', err);
        if (!mounted) return;
        setState(() {
          _loadingVaccinations = false;
          _vaccinationsError = 'Could not load vaccinations. Please try again.';
        });
      },
      cancelOnError: false,
    );
  }

  // =======================================================================
  // SAVE VACCINATION
  // =======================================================================

  Future<void> _saveVaccination(_Vaccination vaccination) async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null || _selectedPet == null) {
      _showSnackBar('Sign in to save.', isError: true);
      return;
    }
    _analytics(
      vaccination.createdAt == null
          ? 'vaccination_added'
          : 'vaccination_updated',
      {
        'petId': _selectedPet!.petId,
        'vaccineType': vaccination.vaccineType,
      },
    );

    _showBlockingProgress('Saving…');
    try {
      final isNew = vaccination.createdAt == null;
      await FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .collection('pets')
          .doc(_selectedPet!.petId)
          .collection('vaccinations')
          .doc(vaccination.vaccinationId)
          .set(
            vaccination.toFirestore(isNew: isNew),
            SetOptions(merge: true),
          );

      if (!mounted) return;
      Navigator.of(context).pop(); // close progress
      if (Navigator.of(context).canPop()) {
        Navigator.of(context).pop(); // close editor
      }
      _showSnackBar(
        isNew
            ? '${vaccination.vaccineName} added.'
            : '${vaccination.vaccineName} updated.',
        isSuccess: true,
      );
    } catch (e) {
      _logError('save vaccination failed', e);
      if (!mounted) return;
      Navigator.of(context).pop();
      _showSnackBar('Could not save. Please try again.', isError: true);
    }
  }

  Future<void> _deleteVaccination(_Vaccination vaccination) async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null || _selectedPet == null) return;

    final confirmed = await _showConfirmDialog(
      title: 'Delete ${vaccination.vaccineName}?',
      body: 'This will permanently remove this vaccination record.',
      confirmLabel: 'Delete',
      destructive: true,
    );
    if (confirmed != true || !mounted) return;

    _analytics('vaccination_deleted', {
      'petId': _selectedPet!.petId,
      'vaccineType': vaccination.vaccineType,
    });
    _showBlockingProgress('Deleting…');

    try {
      await FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .collection('pets')
          .doc(_selectedPet!.petId)
          .collection('vaccinations')
          .doc(vaccination.vaccinationId)
          .delete();

      if (!mounted) return;
      Navigator.of(context).pop();
      if (Navigator.of(context).canPop()) {
        Navigator.of(context).pop();
      }
      _showSnackBar('${vaccination.vaccineName} deleted.', isSuccess: true);
    } catch (e) {
      _logError('delete vaccination failed', e);
      if (!mounted) return;
      Navigator.of(context).pop();
      _showSnackBar('Could not delete. Please try again.', isError: true);
    }
  }

  // =======================================================================
  // SHARED UI HELPERS
  // =======================================================================

  Widget _glassCard({
    required Widget child,
    double bgOpacity = 0.08,
    double borderOpacity = 0.15,
    double borderWidth = 1.2,
    EdgeInsetsGeometry? padding,
    double borderRadius = 20,
    Color? borderTint,
  }) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(borderRadius),
      child: RepaintBoundary(
        child: Container(
          padding: padding ?? const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(bgOpacity + 0.02),
            borderRadius: BorderRadius.circular(borderRadius),
            border: Border.all(
              color: (borderTint ?? Colors.white).withOpacity(borderOpacity),
              width: borderWidth,
            ),
          ),
          child: child,
        ),
      ),
    );
  }

  void _showSnackBar(
    String message, {
    bool isError = false,
    bool isSuccess = false,
    bool isInfo = false,
  }) {
    if (!mounted) return;
    Color bg = _joviNavyMid;
    if (isError) {
      bg = _joviErrorRed;
    } else if (isSuccess) {
      bg = _joviMintDark;
    } else if (isInfo) {
      bg = _joviGoldDark;
    }
    final icon = isError
        ? CupertinoIcons.exclamationmark_circle
        : isSuccess
            ? CupertinoIcons.checkmark_circle
            : isInfo
                ? CupertinoIcons.exclamationmark_triangle
                : CupertinoIcons.info_circle;
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(message,
        accent: bg == _joviNavyMid ? Colors.white70 : bg,
        icon: icon,
        duration: Duration(seconds: isError || isInfo ? 4 : 3)));
  }

  Future<bool?> _showConfirmDialog({
    required String title,
    required String body,
    required String confirmLabel,
    bool destructive = false,
  }) async {
    // System alert: quick yes/no with a red destructive action, the way
    // iOS members expect it.
    return showCupertinoDialog<bool>(
      context: context,
      builder: (ctx) => CupertinoAlertDialog(
        title: Text(title),
        content: Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Text(body),
        ),
        actions: [
          CupertinoDialogAction(
            isDefaultAction: true,
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          CupertinoDialogAction(
            isDestructiveAction: destructive,
            onPressed: () => Navigator.pop(ctx, true),
            child: Text(confirmLabel),
          ),
        ],
      ),
    );
  }

  void _showBlockingProgress(String label) {
    if (!mounted) return;
    showDialog<void>(
      context: context,
      barrierDismissible: false,
      barrierColor: Colors.black.withOpacity(0.65),
      builder: (ctx) => PopScope(
        canPop: false,
        child: Dialog(
          backgroundColor: Colors.transparent,
          elevation: 0,
          child: ClipRRect(
            borderRadius: BorderRadius.circular(18),
            child: BackdropFilter(
              filter: ui_dart.ImageFilter.blur(sigmaX: 16, sigmaY: 16),
              child: Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: _joviNavy.withOpacity(0.95),
                  borderRadius: BorderRadius.circular(18),
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const SizedBox(
                      width: 28,
                      height: 28,
                      child: CircularProgressIndicator(
                        strokeWidth: 2.5,
                        valueColor: AlwaysStoppedAnimation<Color>(_petAccent),
                      ),
                    ),
                    const SizedBox(height: 14),
                    Text(
                      label,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
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

  // =======================================================================
  // BUILD — root
  // =======================================================================

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
        floatingActionButton: (_selectedPet != null && !_loadingVaccinations)
            ? _buildFab()
            : null,
        body: Container(
          width: MediaQuery.of(context).size.width,
          height: MediaQuery.of(context).size.height,
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
                _buildAppBar(),
                Expanded(
                  child: FadeTransition(
                    opacity: _fadeAnim,
                    child: _buildBody(),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildAppBar() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 10, 14, 4),
      child: Row(
        children: [
          _PressableMaterial(
            child: InkWell(
              onTap: () {
                HapticFeedback.lightImpact();
                // If we're viewing a specific pet's vaccinations and
                // there are multiple pets, back first goes to pet picker
                if (_selectedPet != null && _pets.length > 1) {
                  _clearSelectedPet();
                  return;
                }
                if (Navigator.of(context).canPop()) {
                  Navigator.of(context).pop();
                }
              },
              borderRadius: BorderRadius.circular(13),
              child: Tooltip(
                message: 'Back',
                child: Semantics(
                  label: 'Back',
                  button: true,
                  child: Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.08),
                      borderRadius: BorderRadius.circular(13),
                      border: Border.all(
                        color: Colors.white.withOpacity(0.18),
                        width: 1,
                      ),
                    ),
                    child: const Icon(
                      Icons.arrow_back_ios_new_rounded,
                      color: Colors.white,
                      size: 16,
                    ),
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  _selectedPet != null
                      ? '${_selectedPet!.name}\'s vaccinations'
                      : 'Vaccinations',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.6,
                    height: 1.1,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 2),
                Text(
                  _subtitleForState(),
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.55),
                    fontSize: 12.5,
                    fontWeight: FontWeight.w500,
                    letterSpacing: 0.2,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _subtitleForState() {
    if (_loadingPets) return 'Loading your pets…';
    if (_petsError != null) return 'No pets yet';
    if (_pets.isEmpty) return 'No pets yet';
    if (_selectedPet == null) return 'Pick a pet to see vaccinations';
    if (_loadingVaccinations) return 'Loading vaccinations…';
    final n = _vaccinations.length;
    if (n == 0) return 'No vaccinations logged yet';
    if (n == 1) return '1 vaccination on file';
    return '$n vaccinations on file';
  }

  Widget _buildBody() {
    if (_loadingPets) {
      return const Center(
        child: SizedBox(
          width: 34,
          height: 34,
          child: CircularProgressIndicator(
            strokeWidth: 2.8,
            valueColor: AlwaysStoppedAnimation<Color>(_petAccent),
          ),
        ),
      );
    }
    if (_petsError != null) {
      return _buildNoPetsState();
    }
    if (_pets.isEmpty) {
      return _buildNoPetsState();
    }
    if (_selectedPet == null) {
      return _buildPetPicker();
    }
    return _buildVaccinationsList();
  }

  Widget _buildFab() {
    return FloatingActionButton.extended(
      onPressed: _openAddVaccinationSheet,
      backgroundColor: _petAccent,
      foregroundColor: Colors.white,
      icon: const Icon(Icons.add_rounded),
      label: const Text(
        'Add Vaccination',
        style: TextStyle(fontWeight: FontWeight.w600),
      ),
    );
  }

  /// Unified view for the "user has no pets" case (and for transient load
  /// failures, since the useful actions are the same in both situations).
  Widget _buildNoPetsState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 82,
              height: 82,
              decoration: BoxDecoration(
                color: _petAccent.withOpacity(0.12),
                borderRadius: BorderRadius.circular(22),
                border: Border.all(
                  color: _petAccent.withOpacity(0.3),
                  width: 1,
                ),
              ),
              child: const Icon(
                Icons.pets_rounded,
                color: _petAccent,
                size: 38,
              ),
            ),
            const SizedBox(height: 20),
            const Text(
              "We noticed you don't have any pets",
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.w800,
                letterSpacing: -0.3,
                height: 1.35,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              'Add a pet now to start tracking vaccinations, boosters, and vet visits.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white.withOpacity(0.6),
                fontSize: 13.5,
                fontWeight: FontWeight.w500,
                height: 1.5,
              ),
            ),
            const SizedBox(height: 24),
            // Primary: jump to Pet Profiles where they can add a pet.
            _PressableMaterial(
              child: InkWell(
                onTap: _openPetProfiles,
                borderRadius: BorderRadius.circular(13),
                child: Semantics(
                  label: 'Add a pet',
                  button: true,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 22, vertical: 13),
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [_petAccent, _petAccentDark],
                      ),
                      borderRadius: BorderRadius.circular(13),
                      boxShadow: [
                        BoxShadow(
                          color: _petAccent.withOpacity(0.4),
                          blurRadius: 16,
                          offset: const Offset(0, 5),
                        ),
                      ],
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.add_rounded, color: Colors.white, size: 17),
                        SizedBox(width: 7),
                        Text(
                          'Add a pet',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 14,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 0.1,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 12),
            // Secondary: back to previous screen (for users without pets).
            _PressableMaterial(
              child: InkWell(
                onTap: () {
                  if (Navigator.of(context).canPop()) {
                    Navigator.of(context).pop();
                  }
                },
                borderRadius: BorderRadius.circular(10),
                child: Padding(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                  child: Text(
                    'Back',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.55),
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      decoration: TextDecoration.underline,
                      decorationColor: Colors.white.withOpacity(0.35),
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Navigate to the Pet Profiles page so the user can add a pet. Tries the
  /// full list of route-name variants, ONCE per name.
  void _openPetProfiles() {
    const routes = ['petPro', 'petProfiles', 'PetProfiles', 'pet_profiles'];
    for (final r in routes) {
      try {
        final path = r.startsWith('/') ? r : '/$r';
        context.push(path);
        return;
      } catch (_) {
        continue;
      }
    }
  }

  Widget _buildPetPicker() {
    return ListView.builder(
      padding: const EdgeInsets.fromLTRB(14, 8, 14, 30),
      itemCount: _pets.length,
      itemBuilder: (ctx, i) {
        final pet = _pets[i];
        return Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: _PressableMaterial(
            child: InkWell(
              onTap: () => _selectPet(pet),
              borderRadius: BorderRadius.circular(18),
              child: Semantics(
                label:
                    'View vaccinations for ${pet.name}, ${_petTypeLabel(pet.type)}',
                button: true,
                child: _glassCard(
                  bgOpacity: 0.07,
                  borderOpacity: 0.14,
                  borderRadius: 18,
                  borderTint: _petAccent,
                  padding: const EdgeInsets.all(14),
                  child: Row(
                    children: [
                      _buildPetAvatar(pet),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              pet.name,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 16,
                                fontWeight: FontWeight.w800,
                                letterSpacing: -0.3,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                            const SizedBox(height: 3),
                            Text(
                              pet.breed ?? _petTypeLabel(pet.type),
                              style: TextStyle(
                                color: Colors.white.withOpacity(0.6),
                                fontSize: 12.5,
                                fontWeight: FontWeight.w500,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ],
                        ),
                      ),
                      Icon(
                        Icons.chevron_right_rounded,
                        color: Colors.white.withOpacity(0.4),
                        size: 22,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildPetAvatar(_PetLite pet) {
    final hasPhoto = pet.photoUrl != null && pet.photoUrl!.isNotEmpty;
    final typeColor = pet.type == PetType.dog ? _joviCoral : _joviMint;
    return Container(
      width: 50,
      height: 50,
      decoration: BoxDecoration(
        gradient: hasPhoto
            ? null
            : LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  typeColor.withOpacity(0.22),
                  typeColor.withOpacity(0.08),
                ],
              ),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: typeColor.withOpacity(0.4),
          width: 1,
        ),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(13),
        child: hasPhoto
            ? Image.network(
                pet.photoUrl!,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => Center(
                    child: Icon(_petTypeIcon(pet.type),
                        color: typeColor, size: 24)),
              )
            : Center(
                child:
                    Icon(_petTypeIcon(pet.type), color: typeColor, size: 24)),
      ),
    );
  }

  // =======================================================================
  // BUILD — VACCINATIONS LIST
  // Groups by status: Overdue → Due soon → Up to date → No expiration.
  // =======================================================================

  Widget _buildVaccinationsList() {
    if (_loadingVaccinations) {
      return const Center(
        child: SizedBox(
          width: 32,
          height: 32,
          child: CircularProgressIndicator(
            strokeWidth: 2.6,
            valueColor: AlwaysStoppedAnimation<Color>(_petAccent),
          ),
        ),
      );
    }
    if (_vaccinationsError != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  color: _joviErrorRed.withOpacity(0.16),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: const Icon(
                  Icons.error_outline_rounded,
                  color: _joviErrorRed,
                  size: 28,
                ),
              ),
              const SizedBox(height: 14),
              Text(
                _vaccinationsError!,
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Colors.white.withOpacity(0.7),
                  fontSize: 13.5,
                ),
              ),
            ],
          ),
        ),
      );
    }
    if (_vaccinations.isEmpty) {
      return _buildEmptyVaccinationsState();
    }

    // Group by status
    final overdue = <_Vaccination>[];
    final dueSoon = <_Vaccination>[];
    final current = <_Vaccination>[];
    final noExp = <_Vaccination>[];
    for (final v in _vaccinations) {
      switch (v.status) {
        case _VaccineStatus.overdue:
          overdue.add(v);
          break;
        case _VaccineStatus.dueSoon:
          dueSoon.add(v);
          break;
        case _VaccineStatus.current:
          current.add(v);
          break;
        case _VaccineStatus.noExpiration:
          noExp.add(v);
          break;
      }
    }

    final widgets = <Widget>[];
    if (overdue.isNotEmpty) {
      widgets.add(_buildStatusSection(
        title: 'Overdue',
        count: overdue.length,
        color: _statusOverdue,
        icon: Icons.error_outline_rounded,
        description:
            'These vaccines have expired. Schedule a vet visit to get them updated.',
        items: overdue,
      ));
    }
    if (dueSoon.isNotEmpty) {
      widgets.add(_buildStatusSection(
        title: 'Due soon',
        count: dueSoon.length,
        color: _statusDueSoon,
        icon: Icons.schedule_rounded,
        description:
            'These vaccines expire within 30 days. Plan a vet visit soon.',
        items: dueSoon,
      ));
    }
    if (current.isNotEmpty) {
      widgets.add(_buildStatusSection(
        title: 'Up to date',
        count: current.length,
        color: _statusCurrent,
        icon: Icons.check_circle_outline_rounded,
        description: null,
        items: current,
      ));
    }
    if (noExp.isNotEmpty) {
      widgets.add(_buildStatusSection(
        title: 'No expiration tracked',
        count: noExp.length,
        color: _statusUnknown,
        icon: Icons.help_outline_rounded,
        description:
            'These records don\'t have an expiration date. Tap to add one.',
        items: noExp,
      ));
    }
    // Trailing disclaimer
    widgets.add(const SizedBox(height: 8));
    widgets.add(_buildDisclaimerCard());
    widgets.add(const SizedBox(height: 100)); // FAB breathing room

    return ListView(
      padding: const EdgeInsets.fromLTRB(14, 8, 14, 12),
      children: widgets,
    );
  }

  Widget _buildEmptyVaccinationsState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 82,
              height: 82,
              decoration: BoxDecoration(
                color: _petAccent.withOpacity(0.12),
                borderRadius: BorderRadius.circular(22),
                border: Border.all(
                  color: _petAccent.withOpacity(0.3),
                  width: 1,
                ),
              ),
              child: const Icon(
                Icons.vaccines_rounded,
                color: _petAccent,
                size: 38,
              ),
            ),
            const SizedBox(height: 20),
            Text(
              'No vaccinations yet for ${_selectedPet!.name}',
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.5,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              'Log past vaccines from your records to track when boosters are due.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white.withOpacity(0.6),
                fontSize: 13.5,
                fontWeight: FontWeight.w500,
                height: 1.5,
              ),
            ),
            const SizedBox(height: 24),
            _PressableMaterial(
              child: InkWell(
                onTap: _openAddVaccinationSheet,
                borderRadius: BorderRadius.circular(13),
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 22, vertical: 13),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [_petAccent, _petAccentDark],
                    ),
                    borderRadius: BorderRadius.circular(13),
                    boxShadow: [
                      BoxShadow(
                        color: _petAccent.withOpacity(0.4),
                        blurRadius: 16,
                        offset: const Offset(0, 5),
                      ),
                    ],
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.add_rounded, color: Colors.white, size: 17),
                      SizedBox(width: 7),
                      Text(
                        'Add first vaccination',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 14,
                          fontWeight: FontWeight.w800,
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
    );
  }

  Widget _buildStatusSection({
    required String title,
    required int count,
    required Color color,
    required IconData icon,
    required String? description,
    required List<_Vaccination> items,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Status header
          Padding(
            padding: const EdgeInsets.only(left: 2, bottom: 8),
            child: Row(
              children: [
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: color.withOpacity(0.35),
                      width: 0.8,
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(icon, color: color, size: 13),
                      const SizedBox(width: 5),
                      Text(
                        title,
                        style: TextStyle(
                          color: color,
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                          letterSpacing: -0.1,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  count == 1 ? '1 vaccine' : '$count vaccines',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.5),
                    fontSize: 11.5,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
          if (description != null)
            Padding(
              padding: const EdgeInsets.only(left: 4, bottom: 10),
              child: Text(
                description,
                style: TextStyle(
                  color: Colors.white.withOpacity(0.55),
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                  height: 1.4,
                ),
              ),
            ),
          for (int i = 0; i < items.length; i++)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: _buildVaccinationCard(items[i], color),
            ),
        ],
      ),
    );
  }

  Widget _buildVaccinationCard(_Vaccination v, Color statusColor) {
    final admin = DateFormat('MMM d, y').format(v.administeredDate);
    final exp = v.expirationDate != null
        ? DateFormat('MMM d, y').format(v.expirationDate!)
        : null;
    final daysUntilExp = v.daysUntilExpiration;
    String? expDisplay;
    if (v.expirationDate == null) {
      expDisplay = null;
    } else if (daysUntilExp! < 0) {
      final days = -daysUntilExp;
      expDisplay = days == 1 ? 'Expired yesterday' : 'Expired $days days ago';
    } else if (daysUntilExp == 0) {
      expDisplay = 'Expires today';
    } else if (daysUntilExp <= 30) {
      expDisplay = 'Expires in $daysUntilExp days';
    } else {
      expDisplay = 'Expires $exp';
    }

    return _PressableMaterial(
      child: InkWell(
        onTap: () => _openEditVaccinationSheet(v),
        borderRadius: BorderRadius.circular(14),
        child: Semantics(
          label: '${v.vaccineName}, administered $admin'
              '${expDisplay != null ? ', $expDisplay' : ''}. Double tap to edit.',
          button: true,
          child: Container(
            padding: const EdgeInsets.all(13),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.05),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                color: statusColor.withOpacity(0.25),
                width: 1,
              ),
            ),
            child: Row(
              children: [
                // Status dot
                Container(
                  width: 8,
                  height: 8,
                  margin: const EdgeInsets.only(top: 6),
                  decoration: BoxDecoration(
                    color: statusColor,
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: statusColor.withOpacity(0.5),
                        blurRadius: 6,
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 11),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        v.vaccineName,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 14.5,
                          fontWeight: FontWeight.w800,
                          letterSpacing: -0.2,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'Given $admin',
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.55),
                          fontSize: 11.5,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      if (expDisplay != null) ...[
                        const SizedBox(height: 2),
                        Text(
                          expDisplay,
                          style: TextStyle(
                            color: statusColor,
                            fontSize: 11.5,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 0.1,
                          ),
                        ),
                      ],
                      if (v.administeredBy != null &&
                          v.administeredBy!.isNotEmpty) ...[
                        const SizedBox(height: 2),
                        Text(
                          'By ${v.administeredBy}'
                          '${v.clinicName != null && v.clinicName!.isNotEmpty ? ' • ${v.clinicName}' : ''}',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.4),
                            fontSize: 11,
                            fontWeight: FontWeight.w500,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ],
                  ),
                ),
                Icon(
                  Icons.chevron_right_rounded,
                  color: Colors.white.withOpacity(0.35),
                  size: 20,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildDisclaimerCard() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.03),
        borderRadius: BorderRadius.circular(11),
        border: Border.all(
          color: Colors.white.withOpacity(0.08),
          width: 0.8,
        ),
      ),
      child: Row(
        children: [
          Icon(
            Icons.info_outline_rounded,
            color: Colors.white.withOpacity(0.4),
            size: 14,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              'Expiration intervals are typical guidelines — always confirm schedule with your vet. State laws and vaccine products vary.',
              style: TextStyle(
                color: Colors.white.withOpacity(0.45),
                fontSize: 10.5,
                fontWeight: FontWeight.w500,
                height: 1.4,
              ),
            ),
          ),
        ],
      ),
    );
  }

  // =======================================================================
  // ADD / EDIT SHEET — opens the editor
  // The full editor UI is in the next turn due to size.
  // =======================================================================

  Future<void> _openAddVaccinationSheet() async {
    HapticFeedback.lightImpact();
    _analytics('vaccination_add_opened', {'petId': _selectedPet?.petId ?? ''});
    await _showVaccinationEditor(null);
  }

  Future<void> _openEditVaccinationSheet(_Vaccination v) async {
    HapticFeedback.lightImpact();
    _analytics('vaccination_edit_opened', {
      'petId': _selectedPet?.petId ?? '',
      'vaccineType': v.vaccineType,
    });
    await _showVaccinationEditor(v);
  }

  Future<void> _showVaccinationEditor(_Vaccination? existing) async {
    if (!mounted || _selectedPet == null) return;
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      useSafeArea: true,
      builder: (ctx) => DraggableScrollableSheet(
        initialChildSize: 0.95,
        maxChildSize: 0.97,
        minChildSize: 0.6,
        expand: false,
        builder: (ctx, scrollCtrl) => _VaccinationEditorSheet(
          pet: _selectedPet!,
          existing: existing,
          scrollController: scrollCtrl,
          onSave: _saveVaccination,
          onDelete:
              existing == null ? null : () => _deleteVaccination(existing),
        ),
      ),
    );
  }
}

// -----------------------------------------------------------------------
// JOVI HEALTH — PET VACCINATIONS
// Version: 2026.09.22-r2 (Apple HIG pass: press feedback, Cupertino
//          confirms, calendar-day due logic, painted glass, navy toasts)
// r1:      2026.04.18
// Build: JC-PETVACS-0922-002
//
// Members use this widget to:
//   - Log vaccinations given to each of their pets
//   - See which vaccines are overdue, due soon, or up to date
//   - Keep a chronological vaccine history per pet
//   - Pick from a canonical list of core + non-core vaccines for
//     dogs and cats, with suggested expiration schedules
//
// DATA MODEL:
// Vaccinations live at users/{uid}/pets/{petId}/vaccinations/{id} as
// a per-pet subcollection. Schema:
//   vaccinationId: String (doc id)
//   vaccineName:   String  — user-visible label
//   vaccineType:   String  — canonical key (rabies/dhpp/bordetella/etc)
//   species:       String  — 'dog'|'cat'|'other' (matches pet.type)
//   administeredDate: Timestamp
//   expirationDate:   Timestamp? — null = no expiration tracked
//   administeredBy:   String?  — vet name
//   clinicName:       String?
//   batchNumber:      String?
//   notes:            String?
//   createdAt / updatedAt: Timestamp
//
// PETS DATA SOURCE:
// Reads pets from users/{uid}/pets/{petId} subcollection (canonical)
// AND falls back to users/{uid}.pets legacy array so we work even if
// the member hasn't opened Pet Profiles yet (which is what runs the
// migration). When both sources have a pet, the subcollection wins.
//
// DISCLAIMER ON SCHEDULES:
// The default expiration schedules encoded in _VaccineCatalog are
// TYPICAL — most states, most manufacturers, most vets. They are NOT
// medical advice. Actual vaccination intervals vary by:
//   - State law (rabies 1yr vs 3yr)
//   - Manufacturer (3-year vs 1-year rabies products)
//   - Individual pet factors (age, health, exposure risk)
//   - Vet preference
// The UI shows a "Suggested expiration — confirm with your vet" hint
// on every auto-filled date.
//
// BLOCK BEFORE PRODUCTION:
//   - Firestore security rules for users/{uid}/pets/*/vaccinations/*
//   - Legal review of the vaccine catalog + expiration hints
//   - Decide whether to push notifications for "due soon" vaccines
//     (currently UI-only)
//   - Vet review of canonical vaccine list (missing: Giardia,
//     Rattlesnake, FIV, Chlamydia — noncore, regional)
// -----------------------------------------------------------------------

// =======================================================================
// JOVI BRAND COLORS
// Kept as private constants — this widget is self-contained.
// =======================================================================

const Color _joviCoral = Color(0xFFFF6B4A);
const Color _joviCoralDark = Color(0xFFE5583A);
const Color _joviNavy = Color(0xFF1A2744);
const Color _joviNavyDark = Color(0xFF0F1A2E);
const Color _joviNavyMid = Color(0xFF1F2B47);
const Color _joviMint = Color(0xFF00D4AA);
const Color _joviMintDark = Color(0xFF00B894);
const Color _joviGold = Color(0xFFFFD166);
const Color _joviGoldDark = Color(0xFFF4A41E);
const Color _joviErrorRed = Color(0xFFE53E3E);
// Pet section accent
const Color _petAccent = Color(0xFFA78BFA);
const Color _petAccentDark = Color(0xFF8B6EE8);

// Status colors for vaccination state
const Color _statusOverdue = Color(0xFFE53E3E); // red
const Color _statusDueSoon = Color(0xFFFFD166); // gold
const Color _statusCurrent = Color(0xFF00D4AA); // mint
const Color _statusUnknown = Color(0xFF94A3B8); // slate

// =======================================================================
// LOGGING
// =======================================================================

void _log(String msg) {
  // ignore: avoid_print
  debugPrint('[PetVaccinations] $msg');
}

void _logError(String msg, Object? err) {
  // ignore: avoid_print
  debugPrint('[PetVaccinations][ERROR] $msg: $err');
}

void _analytics(String event, [Map<String, String?>? props]) {
  if (props == null || props.isEmpty) {
    _log('analytics: $event');
  } else {
    _log('analytics: $event $props');
  }
}

// =======================================================================
// PET TYPE + SEX ENUMS
// Duplicated from Pet Profiles widget so this file is self-contained.
// Keep in sync if the Pet Profiles enum evolves.
// =======================================================================

enum PetType { dog, cat, other }

String _petTypeLabel(PetType t) {
  switch (t) {
    case PetType.dog:
      return 'Dog';
    case PetType.cat:
      return 'Cat';
    case PetType.other:
      return 'Other';
  }
}

String _petTypeSerialize(PetType t) {
  switch (t) {
    case PetType.dog:
      return 'dog';
    case PetType.cat:
      return 'cat';
    case PetType.other:
      return 'other';
  }
}

PetType _petTypeParse(String? raw) {
  if (raw == null) return PetType.other;
  switch (raw.toLowerCase().trim()) {
    case 'dog':
    case 'canine':
    case 'puppy':
      return PetType.dog;
    case 'cat':
    case 'feline':
    case 'kitten':
      return PetType.cat;
    default:
      return PetType.other;
  }
}

IconData _petTypeIcon(PetType t) {
  switch (t) {
    case PetType.dog:
      return Icons.pets_rounded;
    case PetType.cat:
      return Icons.pets_rounded;
    case PetType.other:
      return Icons.pets_outlined;
  }
}

// =======================================================================
// LIGHTWEIGHT PET MODEL
// We only need a small subset of Pet Profiles' _Pet model here — the
// id, name, type, breed, photo, and dateOfBirth for age-awareness.
// Copying the full 20+ field model would create a maintenance burden.
// =======================================================================

class _PetLite {
  final String petId;
  final String name;
  final PetType type;
  final String? breed;
  final String? photoUrl;
  final DateTime? dateOfBirth;

  const _PetLite({
    required this.petId,
    required this.name,
    this.type = PetType.other,
    this.breed,
    this.photoUrl,
    this.dateOfBirth,
  });

  factory _PetLite.fromSubcollection(String docId, Map<String, dynamic> m) {
    DateTime? parseTs(dynamic v) {
      if (v == null) return null;
      if (v is Timestamp) return v.toDate();
      if (v is String) {
        final iso = DateTime.tryParse(v);
        if (iso != null) return iso;
        // Legacy MM/DD/YYYY from onboarding widget.
        final parts = v.split('/');
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
      }
      return null;
    }

    return _PetLite(
      petId: (m['petId'] as String?) ?? docId,
      name: (m['name'] as String?)?.trim().isNotEmpty == true
          ? (m['name'] as String).trim()
          : 'Unnamed pet',
      type: _petTypeParse(m['type'] as String?),
      breed: m['breed'] as String?,
      photoUrl: m['photoUrl'] as String? ?? m['photo_url'] as String?,
      dateOfBirth: parseTs(m['dateOfBirth'] ?? m['dob'] ?? m['birthdate']),
    );
  }

  /// Parse from the legacy 5-field array entry (onboarding/update).
  static _PetLite? fromLegacyJson(String jsonStr) {
    try {
      final decoded = jsonDecode(jsonStr);
      if (decoded is! Map) return null;
      final m = Map<String, dynamic>.from(decoded);
      final petId = (m['petId'] as String?)?.trim();
      final name = (m['name'] as String?)?.trim();
      if (petId == null || petId.isEmpty) return null;
      if (name == null || name.isEmpty) return null;
      return _PetLite(
        petId: petId,
        name: name,
        type: _petTypeParse(m['type'] as String?),
        breed: m['breed'] as String?,
        photoUrl: m['photo_url'] as String?,
      );
    } catch (_) {
      return null;
    }
  }

  int? get ageMonths {
    if (dateOfBirth == null) return null;
    final now = DateTime.now();
    int months =
        (now.year - dateOfBirth!.year) * 12 + (now.month - dateOfBirth!.month);
    if (now.day < dateOfBirth!.day) months--;
    return months >= 0 ? months : null;
  }

  bool get isPuppyOrKitten {
    final m = ageMonths;
    return m != null && m < 12;
  }
}

// =======================================================================
// VACCINATION MODEL
// =======================================================================

class _Vaccination {
  final String vaccinationId;
  final String vaccineName;

  /// Canonical vaccine key. "custom" for user-entered free-text.
  final String vaccineType;
  final PetType species;
  final DateTime administeredDate;
  final DateTime? expirationDate;
  final String? administeredBy;
  final String? clinicName;
  final String? batchNumber;
  final String? notes;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  const _Vaccination({
    required this.vaccinationId,
    required this.vaccineName,
    this.vaccineType = 'custom',
    this.species = PetType.other,
    required this.administeredDate,
    this.expirationDate,
    this.administeredBy,
    this.clinicName,
    this.batchNumber,
    this.notes,
    this.createdAt,
    this.updatedAt,
  });

  factory _Vaccination.fromFirestore(String docId, Map<String, dynamic> m) {
    DateTime? parseTs(dynamic v) {
      if (v == null) return null;
      if (v is Timestamp) return v.toDate();
      if (v is String) {
        final iso = DateTime.tryParse(v);
        if (iso != null) return iso;
        // Legacy MM/DD/YYYY from onboarding widget.
        final parts = v.split('/');
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
      }
      return null;
    }

    final admin = parseTs(m['administeredDate']);
    return _Vaccination(
      vaccinationId: (m['vaccinationId'] as String?) ?? docId,
      vaccineName: (m['vaccineName'] as String?)?.trim().isNotEmpty == true
          ? (m['vaccineName'] as String).trim()
          : 'Vaccine',
      vaccineType: (m['vaccineType'] as String?) ?? 'custom',
      species: _petTypeParse(m['species'] as String?),
      administeredDate: admin ?? DateTime.now(),
      expirationDate: parseTs(m['expirationDate']),
      administeredBy: m['administeredBy'] as String?,
      clinicName: m['clinicName'] as String?,
      batchNumber: m['batchNumber'] as String?,
      notes: m['notes'] as String?,
      createdAt: parseTs(m['createdAt']),
      updatedAt: parseTs(m['updatedAt']),
    );
  }

  Map<String, dynamic> toFirestore({bool isNew = false}) {
    final data = <String, dynamic>{
      'vaccinationId': vaccinationId,
      'vaccineName': vaccineName,
      'vaccineType': vaccineType,
      'species': _petTypeSerialize(species),
      'administeredDate': Timestamp.fromDate(administeredDate),
      'updatedAt': FieldValue.serverTimestamp(),
    };
    if (isNew) {
      data['createdAt'] = FieldValue.serverTimestamp();
    }
    if (expirationDate != null) {
      data['expirationDate'] = Timestamp.fromDate(expirationDate!);
    }
    if (administeredBy != null && administeredBy!.isNotEmpty) {
      data['administeredBy'] = administeredBy;
    }
    if (clinicName != null && clinicName!.isNotEmpty) {
      data['clinicName'] = clinicName;
    }
    if (batchNumber != null && batchNumber!.isNotEmpty) {
      data['batchNumber'] = batchNumber;
    }
    if (notes != null && notes!.isNotEmpty) {
      data['notes'] = notes;
    }
    return data;
  }

  /// Compute current status based on expiration date.
  /// Days until expiration by calendar day, so "yesterday at 5 pm" reads
  /// as -1 rather than 0. Null when no expiration is tracked.
  int? get daysUntilExpiration {
    final exp = expirationDate;
    if (exp == null) return null;
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final day = DateTime(exp.year, exp.month, exp.day);
    return day.difference(today).inDays;
  }

  _VaccineStatus get status {
    final d = daysUntilExpiration;
    if (d == null) return _VaccineStatus.noExpiration;
    if (d < 0) return _VaccineStatus.overdue;
    if (d <= 30) return _VaccineStatus.dueSoon;
    return _VaccineStatus.current;
  }

  _Vaccination copyWith({
    String? vaccinationId,
    String? vaccineName,
    String? vaccineType,
    PetType? species,
    DateTime? administeredDate,
    DateTime? expirationDate,
    String? administeredBy,
    String? clinicName,
    String? batchNumber,
    String? notes,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return _Vaccination(
      vaccinationId: vaccinationId ?? this.vaccinationId,
      vaccineName: vaccineName ?? this.vaccineName,
      vaccineType: vaccineType ?? this.vaccineType,
      species: species ?? this.species,
      administeredDate: administeredDate ?? this.administeredDate,
      expirationDate: expirationDate ?? this.expirationDate,
      administeredBy: administeredBy ?? this.administeredBy,
      clinicName: clinicName ?? this.clinicName,
      batchNumber: batchNumber ?? this.batchNumber,
      notes: notes ?? this.notes,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }
}

enum _VaccineStatus {
  /// Past the expiration date — needs booster.
  overdue,

  /// Within 30 days of expiration — plan a booster soon.
  dueSoon,

  /// Not yet approaching expiration.
  current,

  /// No expiration tracked — status unknowable without manual review.
  noExpiration,
}

// =======================================================================
// VACCINE CATALOG
// Canonical list of common dog + cat vaccines with suggested expiration
// intervals. IMPORTANT: these are TYPICAL defaults, not medical advice.
// Actual intervals vary by state law, manufacturer, pet factors, and vet
// preference. The UI always shows a "confirm with your vet" hint when
// auto-filling a date.
//
// Interval format: number of days from administration to next dose due.
// =======================================================================

class _VaccineCatalogEntry {
  final String key; // canonical key (stored as vaccineType)
  final String displayName; // "Rabies", "DHPP", etc.
  final String shortName; // abbreviated form for compact cards
  final PetType species;
  final bool isCore; // core = recommended for most pets
  final int? typicalIntervalDays; // null = one-time or highly variable
  final String? intervalLabel; // "Every 1-3 years" etc. human-readable
  final String? description; // 1-2 sentence explainer for member
  final List<String>? alternateNames; // "DA2PP", "DHLPP", etc. for matching

  const _VaccineCatalogEntry({
    required this.key,
    required this.displayName,
    required this.shortName,
    required this.species,
    this.isCore = false,
    this.typicalIntervalDays,
    this.intervalLabel,
    this.description,
    this.alternateNames,
  });
}

class _VaccineCatalog {
  static const List<_VaccineCatalogEntry> dogVaccines = [
    _VaccineCatalogEntry(
      key: 'rabies',
      displayName: 'Rabies',
      shortName: 'Rabies',
      species: PetType.dog,
      isCore: true,
      typicalIntervalDays: 1095, // 3 years typical; first dose is 1 year
      intervalLabel: 'Every 1 or 3 years (varies by state + vaccine type)',
      description:
          'Required by law in most states. Initial dose lasts 1 year; adult boosters are typically 3 years.',
      alternateNames: ['rabies 1-year', 'rabies 3-year'],
    ),
    _VaccineCatalogEntry(
      key: 'dhpp',
      displayName: 'DHPP (Distemper combo)',
      shortName: 'DHPP',
      species: PetType.dog,
      isCore: true,
      typicalIntervalDays: 1095,
      intervalLabel: 'Every 3 years after puppy series',
      description:
          'Distemper, Hepatitis/Adenovirus, Parvovirus, Parainfluenza. Puppy series then adult boosters every 3 years.',
      alternateNames: ['da2pp', 'dhlpp', 'dap', 'distemper'],
    ),
    _VaccineCatalogEntry(
      key: 'bordetella',
      displayName: 'Bordetella (Kennel cough)',
      shortName: 'Bordetella',
      species: PetType.dog,
      isCore: false,
      typicalIntervalDays: 365,
      intervalLabel: 'Every 6 months to 1 year',
      description:
          'Required by most boarding facilities, daycares, and grooming salons. High-risk pets may need every 6 months.',
      alternateNames: ['kennel cough'],
    ),
    _VaccineCatalogEntry(
      key: 'leptospirosis',
      displayName: 'Leptospirosis',
      shortName: 'Lepto',
      species: PetType.dog,
      isCore: false,
      typicalIntervalDays: 365,
      intervalLabel: 'Annual',
      description:
          'Protects against bacterial infection from wildlife/water. Recommended for dogs with outdoor exposure.',
      alternateNames: ['lepto'],
    ),
    _VaccineCatalogEntry(
      key: 'lyme',
      displayName: 'Lyme disease',
      shortName: 'Lyme',
      species: PetType.dog,
      isCore: false,
      typicalIntervalDays: 365,
      intervalLabel: 'Annual',
      description:
          'Regional — recommended in tick-heavy areas (Northeast, Upper Midwest, Pacific Northwest).',
    ),
    _VaccineCatalogEntry(
      key: 'canine_influenza',
      displayName: 'Canine influenza (CIV)',
      shortName: 'Flu',
      species: PetType.dog,
      isCore: false,
      typicalIntervalDays: 365,
      intervalLabel: 'Annual',
      description:
          'Flu vaccine for dogs in boarding, daycare, or high social-contact environments.',
      alternateNames: ['dog flu', 'civ', 'h3n2', 'h3n8'],
    ),
    _VaccineCatalogEntry(
      key: 'rattlesnake',
      displayName: 'Rattlesnake',
      shortName: 'Rattlesnake',
      species: PetType.dog,
      isCore: false,
      typicalIntervalDays: 365,
      intervalLabel: 'Annual',
      description:
          'Regional — recommended in the Southwest for dogs hiking or living in rattlesnake habitat.',
    ),
  ];

  static const List<_VaccineCatalogEntry> catVaccines = [
    _VaccineCatalogEntry(
      key: 'rabies',
      displayName: 'Rabies',
      shortName: 'Rabies',
      species: PetType.cat,
      isCore: true,
      typicalIntervalDays: 365,
      intervalLabel: 'Every 1 or 3 years (varies by state + vaccine type)',
      description: 'Required by law in most states, even for indoor cats.',
      alternateNames: ['rabies 1-year', 'rabies 3-year'],
    ),
    _VaccineCatalogEntry(
      key: 'fvrcp',
      displayName: 'FVRCP (Distemper combo)',
      shortName: 'FVRCP',
      species: PetType.cat,
      isCore: true,
      typicalIntervalDays: 1095,
      intervalLabel: 'Every 3 years after kitten series',
      description:
          'Feline Rhinotracheitis, Calicivirus, Panleukopenia. Core for all cats.',
      alternateNames: ['feline distemper'],
    ),
    _VaccineCatalogEntry(
      key: 'felv',
      displayName: 'Feline Leukemia (FeLV)',
      shortName: 'FeLV',
      species: PetType.cat,
      isCore: false,
      typicalIntervalDays: 365,
      intervalLabel: 'Annual',
      description:
          'Recommended for outdoor cats and multi-cat homes. Core for kittens during first year.',
      alternateNames: ['feline leukemia'],
    ),
    _VaccineCatalogEntry(
      key: 'fiv',
      displayName: 'Feline Immunodeficiency (FIV)',
      shortName: 'FIV',
      species: PetType.cat,
      isCore: false,
      typicalIntervalDays: 365,
      intervalLabel: 'Annual',
      description:
          'Non-core. Sometimes recommended for high-risk outdoor cats — discuss with your vet.',
    ),
  ];

  /// Get the catalog for a pet type. "Other" returns an empty list.
  static List<_VaccineCatalogEntry> forSpecies(PetType type) {
    switch (type) {
      case PetType.dog:
        return dogVaccines;
      case PetType.cat:
        return catVaccines;
      case PetType.other:
        return const [];
    }
  }

  /// Look up a canonical entry by key + species. Returns null for
  /// custom entries or unknown species.
  static _VaccineCatalogEntry? find(String key, PetType species) {
    final list = forSpecies(species);
    for (final entry in list) {
      if (entry.key == key) return entry;
    }
    return null;
  }
}

// =======================================================================
// WIDGET
// =======================================================================

// =======================================================================
// VACCINATION EDITOR SHEET
// Full-screen bottom sheet for adding or editing a vaccination.
// Auto-fills expiration date based on canonical vaccine schedule.
// =======================================================================

class _VaccinationEditorSheet extends StatefulWidget {
  final _PetLite pet;
  final _Vaccination? existing;
  final ScrollController scrollController;
  final Future<void> Function(_Vaccination v) onSave;
  final Future<void> Function()? onDelete;

  const _VaccinationEditorSheet({
    Key? key,
    required this.pet,
    required this.existing,
    required this.scrollController,
    required this.onSave,
    this.onDelete,
  }) : super(key: key);

  @override
  State<_VaccinationEditorSheet> createState() =>
      _VaccinationEditorSheetState();
}

class _VaccinationEditorSheetState extends State<_VaccinationEditorSheet> {
  late final TextEditingController _vaccineNameCtrl;
  late final TextEditingController _administeredByCtrl;
  late final TextEditingController _clinicNameCtrl;
  late final TextEditingController _batchNumberCtrl;
  late final TextEditingController _notesCtrl;

  late String _vaccinationId;
  String _selectedVaccineType = 'custom';
  late DateTime _administeredDate;
  DateTime? _expirationDate;

  /// Whether the expiration was auto-filled from the catalog vs.
  /// manually set by the user. We surface a hint when it's auto-filled.
  bool _expirationAutoFilled = false;

  final _formKey = GlobalKey<FormState>();
  bool _attemptedSave = false;

  bool get _isEditing => widget.existing != null;

  List<_VaccineCatalogEntry> get _catalog =>
      _VaccineCatalog.forSpecies(widget.pet.type);

  @override
  void initState() {
    super.initState();
    final e = widget.existing;
    _vaccinationId = e?.vaccinationId ?? const Uuid().v4();
    _vaccineNameCtrl = TextEditingController(text: e?.vaccineName ?? '');
    _administeredByCtrl = TextEditingController(text: e?.administeredBy ?? '');
    _clinicNameCtrl = TextEditingController(text: e?.clinicName ?? '');
    _batchNumberCtrl = TextEditingController(text: e?.batchNumber ?? '');
    _notesCtrl = TextEditingController(text: e?.notes ?? '');
    _selectedVaccineType = e?.vaccineType ?? 'custom';
    _administeredDate = e?.administeredDate ?? DateTime.now();
    _expirationDate = e?.expirationDate;
    _expirationAutoFilled = false; // existing dates are user-set
  }

  @override
  void dispose() {
    _vaccineNameCtrl.dispose();
    _administeredByCtrl.dispose();
    _clinicNameCtrl.dispose();
    _batchNumberCtrl.dispose();
    _notesCtrl.dispose();
    super.dispose();
  }

  /// Select a vaccine from the catalog. Auto-fills name + expiration.
  void _selectCatalogVaccine(_VaccineCatalogEntry entry) {
    HapticFeedback.selectionClick();
    setState(() {
      _selectedVaccineType = entry.key;
      _vaccineNameCtrl.text = entry.displayName;
      if (entry.typicalIntervalDays != null) {
        _expirationDate =
            _administeredDate.add(Duration(days: entry.typicalIntervalDays!));
        _expirationAutoFilled = true;
      }
    });
  }

  /// User picks "Custom" to enter a free-text vaccine name.
  void _selectCustomVaccine() {
    HapticFeedback.selectionClick();
    setState(() {
      _selectedVaccineType = 'custom';
      if (widget.existing?.vaccineType != 'custom') {
        _vaccineNameCtrl.clear();
      }
      _expirationAutoFilled = false;
    });
  }

  Future<void> _pickAdministeredDate() async {
    HapticFeedback.lightImpact();
    final now = DateTime.now();
    final earliest = DateTime(now.year - 20);
    final picked = await showDatePicker(
      context: context,
      initialDate: _administeredDate.isAfter(now) ? now : _administeredDate,
      firstDate: earliest,
      lastDate: now,
      helpText: 'When was this vaccine given?',
      builder: (ctx, child) => _themedDatePicker(ctx, child),
    );
    if (picked != null && mounted) {
      setState(() {
        _administeredDate = picked;
        // If expiration was auto-filled from catalog, re-compute it
        // based on new administration date.
        if (_expirationAutoFilled && _selectedVaccineType != 'custom') {
          final entry =
              _VaccineCatalog.find(_selectedVaccineType, widget.pet.type);
          if (entry?.typicalIntervalDays != null) {
            _expirationDate =
                picked.add(Duration(days: entry!.typicalIntervalDays!));
          }
        }
      });
    }
  }

  Future<void> _pickExpirationDate() async {
    HapticFeedback.lightImpact();
    final now = DateTime.now();
    final earliest = DateTime(now.year - 20);
    final latest = DateTime(now.year + 20);
    final picked = await showDatePicker(
      context: context,
      initialDate:
          _expirationDate ?? _administeredDate.add(const Duration(days: 365)),
      firstDate: earliest,
      lastDate: latest,
      helpText: 'When does this vaccine expire?',
      builder: (ctx, child) => _themedDatePicker(ctx, child),
    );
    if (picked != null && mounted) {
      setState(() {
        _expirationDate = picked;
        _expirationAutoFilled = false; // user override
      });
    }
  }

  Widget _themedDatePicker(BuildContext ctx, Widget? child) {
    return Theme(
      data: Theme.of(ctx).copyWith(
        colorScheme: const ColorScheme.dark(
          primary: _petAccent,
          onPrimary: Colors.white,
          surface: _joviNavy,
          onSurface: Colors.white,
        ),
        dialogBackgroundColor: _joviNavy,
      ),
      child: child!,
    );
  }

  Future<void> _onSaveTapped() async {
    setState(() => _attemptedSave = true);
    if (!(_formKey.currentState?.validate() ?? false)) {
      HapticFeedback.heavyImpact();
      widget.scrollController.animateTo(
        0,
        duration: _Motion.enter,
        curve: _Motion.settle,
      );
      return;
    }
    HapticFeedback.mediumImpact();

    final v = _Vaccination(
      vaccinationId: _vaccinationId,
      vaccineName: _vaccineNameCtrl.text.trim(),
      vaccineType: _selectedVaccineType,
      species: widget.pet.type,
      administeredDate: _administeredDate,
      expirationDate: _expirationDate,
      administeredBy: _administeredByCtrl.text.trim().isEmpty
          ? null
          : _administeredByCtrl.text.trim(),
      clinicName: _clinicNameCtrl.text.trim().isEmpty
          ? null
          : _clinicNameCtrl.text.trim(),
      batchNumber: _batchNumberCtrl.text.trim().isEmpty
          ? null
          : _batchNumberCtrl.text.trim(),
      notes: _notesCtrl.text.trim().isEmpty ? null : _notesCtrl.text.trim(),
      createdAt: widget.existing?.createdAt,
      updatedAt: widget.existing?.updatedAt,
    );
    await widget.onSave(v);
  }

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
      child: BackdropFilter(
        filter: ui_dart.ImageFilter.blur(sigmaX: 20, sigmaY: 20),
        child: Container(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [
                _joviNavy.withOpacity(0.98),
                _joviNavyDark.withOpacity(0.99),
              ],
            ),
            borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
            border: Border.all(
              color: Colors.white.withOpacity(0.1),
              width: 1,
            ),
          ),
          child: Column(
            children: [
              Container(
                margin: const EdgeInsets.only(top: 10),
                width: 38,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              _buildSheetHeader(),
              Expanded(
                child: Form(
                  key: _formKey,
                  autovalidateMode: _attemptedSave
                      ? AutovalidateMode.onUserInteraction
                      : AutovalidateMode.disabled,
                  child: SingleChildScrollView(
                    controller: widget.scrollController,
                    padding: const EdgeInsets.fromLTRB(18, 8, 18, 100),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _buildSectionHeader('Vaccine', Icons.vaccines_rounded),
                        if (_catalog.isNotEmpty) ...[
                          _buildCatalogPicker(),
                          const SizedBox(height: 12),
                        ],
                        _buildTextField(
                          controller: _vaccineNameCtrl,
                          label: 'Vaccine name',
                          required: true,
                          hint: 'e.g., Rabies, DHPP',
                          autofocus: !_isEditing && _catalog.isEmpty,
                          enabled: _selectedVaccineType == 'custom',
                        ),
                        if (_selectedVaccineType != 'custom') ...[
                          const SizedBox(height: 6),
                          _buildCatalogHint(),
                        ],
                        const SizedBox(height: 20),
                        _buildSectionHeader('Dates', Icons.event_rounded),
                        _buildDateField(
                          label: 'Administered',
                          value: _administeredDate,
                          onTap: _pickAdministeredDate,
                          icon: Icons.event_available_rounded,
                          required: true,
                        ),
                        const SizedBox(height: 12),
                        _buildDateField(
                          label: 'Expires',
                          value: _expirationDate,
                          onTap: _pickExpirationDate,
                          icon: Icons.event_busy_rounded,
                          onClear: _expirationDate == null
                              ? null
                              : () {
                                  HapticFeedback.selectionClick();
                                  setState(() {
                                    _expirationDate = null;
                                    _expirationAutoFilled = false;
                                  });
                                },
                          hint: 'Optional — for tracking boosters',
                        ),
                        if (_expirationAutoFilled) ...[
                          const SizedBox(height: 6),
                          _buildExpirationAutoFilledHint(),
                        ],
                        const SizedBox(height: 20),
                        _buildSectionHeader(
                            'Provider', Icons.local_hospital_outlined),
                        _buildTextField(
                          controller: _administeredByCtrl,
                          label: 'Vet name',
                          hint: 'Dr. Smith',
                        ),
                        const SizedBox(height: 12),
                        _buildTextField(
                          controller: _clinicNameCtrl,
                          label: 'Clinic',
                          hint: 'Animal Hospital',
                        ),
                        const SizedBox(height: 12),
                        _buildTextField(
                          controller: _batchNumberCtrl,
                          label: 'Batch / lot number',
                          hint: 'Optional — from vaccine vial',
                        ),
                        const SizedBox(height: 20),
                        _buildSectionHeader('Notes', Icons.notes_rounded),
                        _buildTextField(
                          controller: _notesCtrl,
                          label: 'Reactions, observations, anything else',
                          hint: 'e.g., Mild swelling at injection site',
                          maxLines: 3,
                        ),
                        if (_isEditing && widget.onDelete != null) ...[
                          const SizedBox(height: 28),
                          _buildDeleteButton(),
                        ],
                      ],
                    ),
                  ),
                ),
              ),
              _buildSaveBar(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSheetHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(18, 14, 12, 12),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  _isEditing ? 'Edit Vaccination' : 'Add Vaccination',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.6,
                    height: 1.1,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  'For ${widget.pet.name} (${_petTypeLabel(widget.pet.type)})',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.55),
                    fontSize: 12.5,
                    fontWeight: FontWeight.w500,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          _PressableMaterial(
            child: InkWell(
              onTap: () => Navigator.of(context).pop(),
              borderRadius: BorderRadius.circular(12),
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.08),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: Colors.white.withOpacity(0.14),
                    width: 1,
                  ),
                ),
                child: const Icon(
                  Icons.close_rounded,
                  color: Colors.white,
                  size: 17,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSectionHeader(String label, IconData icon) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12, top: 4),
      child: Row(
        children: [
          Container(
            width: 26,
            height: 26,
            decoration: BoxDecoration(
              color: _petAccent.withOpacity(0.16),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: _petAccent.withOpacity(0.3),
                width: 0.8,
              ),
            ),
            child: Icon(icon, color: _petAccent, size: 14),
          ),
          const SizedBox(width: 9),
          Text(
            label,
            style: TextStyle(
              color: _petAccent,
              fontSize: 13,
              fontWeight: FontWeight.w600,
              letterSpacing: -0.1,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCatalogPicker() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 6),
          child: Text(
            'Pick a common ${_petTypeLabel(widget.pet.type).toLowerCase()} vaccine',
            style: TextStyle(
              color: Colors.white.withOpacity(0.7),
              fontSize: 12,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        Wrap(
          spacing: 6,
          runSpacing: 6,
          children: [
            for (final entry in _catalog) _buildCatalogChip(entry),
            _buildCustomChip(),
          ],
        ),
      ],
    );
  }

  Widget _buildCatalogChip(_VaccineCatalogEntry entry) {
    final selected = _selectedVaccineType == entry.key;
    return _PressableMaterial(
      child: InkWell(
        onTap: () => _selectCatalogVaccine(entry),
        borderRadius: BorderRadius.circular(999),
        child: AnimatedContainer(
          duration: _Motion.select,
          curve: _Motion.settle,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            gradient: selected
                ? const LinearGradient(
                    colors: [_petAccent, _petAccentDark],
                  )
                : null,
            color: selected ? null : Colors.white.withOpacity(0.05),
            borderRadius: BorderRadius.circular(999),
            border: Border.all(
              color: selected
                  ? _petAccent.withOpacity(0.6)
                  : (entry.isCore
                      ? _joviMint.withOpacity(0.25)
                      : Colors.white.withOpacity(0.12)),
              width: 1,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (entry.isCore && !selected) ...[
                Container(
                  width: 5,
                  height: 5,
                  decoration: const BoxDecoration(
                    color: _joviMint,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 5),
              ],
              Text(
                entry.shortName,
                style: TextStyle(
                  color:
                      selected ? Colors.white : Colors.white.withOpacity(0.85),
                  fontSize: 12,
                  fontWeight: selected ? FontWeight.w800 : FontWeight.w700,
                  letterSpacing: 0.1,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCustomChip() {
    final selected = _selectedVaccineType == 'custom';
    return _PressableMaterial(
      child: InkWell(
        onTap: _selectCustomVaccine,
        borderRadius: BorderRadius.circular(999),
        child: AnimatedContainer(
          duration: _Motion.select,
          curve: _Motion.settle,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            gradient: selected
                ? const LinearGradient(
                    colors: [_petAccent, _petAccentDark],
                  )
                : null,
            color: selected ? null : Colors.white.withOpacity(0.05),
            borderRadius: BorderRadius.circular(999),
            border: Border.all(
              color: selected
                  ? _petAccent.withOpacity(0.6)
                  : Colors.white.withOpacity(0.12),
              width: 1,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.edit_rounded,
                color: selected ? Colors.white : Colors.white.withOpacity(0.6),
                size: 12,
              ),
              const SizedBox(width: 5),
              Text(
                'Custom',
                style: TextStyle(
                  color:
                      selected ? Colors.white : Colors.white.withOpacity(0.85),
                  fontSize: 12,
                  fontWeight: selected ? FontWeight.w800 : FontWeight.w700,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCatalogHint() {
    final entry = _VaccineCatalog.find(_selectedVaccineType, widget.pet.type);
    if (entry == null) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(left: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (entry.description != null)
            Text(
              entry.description!,
              style: TextStyle(
                color: Colors.white.withOpacity(0.5),
                fontSize: 11.5,
                fontWeight: FontWeight.w500,
                height: 1.45,
              ),
            ),
          if (entry.intervalLabel != null) ...[
            const SizedBox(height: 3),
            Row(
              children: [
                Icon(
                  Icons.schedule_rounded,
                  color: _petAccent.withOpacity(0.8),
                  size: 11,
                ),
                const SizedBox(width: 4),
                Expanded(
                  child: Text(
                    entry.intervalLabel!,
                    style: TextStyle(
                      color: _petAccent.withOpacity(0.85),
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.1,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildExpirationAutoFilledHint() {
    return Padding(
      padding: const EdgeInsets.only(left: 4),
      child: Row(
        children: [
          Icon(
            Icons.auto_awesome_rounded,
            color: _joviGold.withOpacity(0.85),
            size: 11,
          ),
          const SizedBox(width: 4),
          Expanded(
            child: Text(
              'Suggested expiration — confirm with your vet.',
              style: TextStyle(
                color: _joviGold.withOpacity(0.85),
                fontSize: 11,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTextField({
    required TextEditingController controller,
    required String label,
    String? hint,
    bool required = false,
    int maxLines = 1,
    bool autofocus = false,
    bool enabled = true,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 6),
          child: Row(
            children: [
              Text(
                label,
                style: TextStyle(
                  color: Colors.white.withOpacity(0.7),
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.2,
                ),
              ),
              if (required) ...[
                const SizedBox(width: 4),
                const Text('*',
                    style: TextStyle(
                        color: _joviCoral,
                        fontSize: 13,
                        fontWeight: FontWeight.w800)),
              ],
            ],
          ),
        ),
        TextFormField(
          controller: controller,
          maxLines: maxLines,
          autofocus: autofocus,
          enabled: enabled,
          textCapitalization: TextCapitalization.sentences,
          textInputAction:
              maxLines > 1 ? TextInputAction.newline : TextInputAction.next,
          style: TextStyle(
            color: enabled ? Colors.white : Colors.white.withOpacity(0.5),
            fontSize: 14,
            fontWeight: FontWeight.w500,
          ),
          cursorColor: _petAccent,
          validator: required
              ? (v) {
                  if (v == null || v.trim().isEmpty) {
                    return '$label is required';
                  }
                  return null;
                }
              : null,
          decoration: InputDecoration(
            hintText: hint,
            hintStyle: TextStyle(
              color: Colors.white.withOpacity(0.35),
              fontSize: 14,
              fontWeight: FontWeight.w500,
            ),
            filled: true,
            fillColor: Colors.white.withOpacity(enabled ? 0.05 : 0.02),
            contentPadding:
                const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide:
                  BorderSide(color: Colors.white.withOpacity(0.12), width: 1),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide:
                  BorderSide(color: Colors.white.withOpacity(0.12), width: 1),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: const BorderSide(color: _petAccent, width: 1.5),
            ),
            disabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide:
                  BorderSide(color: Colors.white.withOpacity(0.06), width: 1),
            ),
            errorBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: const BorderSide(color: _joviErrorRed, width: 1),
            ),
            focusedErrorBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: const BorderSide(color: _joviErrorRed, width: 1.5),
            ),
            errorStyle: const TextStyle(
              color: _joviErrorRed,
              fontSize: 11,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildDateField({
    required String label,
    required DateTime? value,
    required VoidCallback onTap,
    required IconData icon,
    String? hint,
    VoidCallback? onClear,
    bool required = false,
  }) {
    final hasValue = value != null;
    final display = hasValue
        ? DateFormat('MMMM d, y').format(value)
        : (hint ?? 'Tap to pick date');
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 6),
          child: Row(
            children: [
              Text(
                label,
                style: TextStyle(
                  color: Colors.white.withOpacity(0.7),
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.2,
                ),
              ),
              if (required) ...[
                const SizedBox(width: 4),
                const Text('*',
                    style: TextStyle(
                        color: _joviCoral,
                        fontSize: 13,
                        fontWeight: FontWeight.w800)),
              ],
            ],
          ),
        ),
        _PressableMaterial(
          child: InkWell(
            onTap: onTap,
            borderRadius: BorderRadius.circular(12),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.05),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: Colors.white.withOpacity(0.12),
                  width: 1,
                ),
              ),
              child: Row(
                children: [
                  Icon(
                    icon,
                    color:
                        hasValue ? _petAccent : Colors.white.withOpacity(0.45),
                    size: 16,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      display,
                      style: TextStyle(
                        color: hasValue
                            ? Colors.white
                            : Colors.white.withOpacity(0.35),
                        fontSize: 14,
                        fontWeight:
                            hasValue ? FontWeight.w600 : FontWeight.w500,
                      ),
                    ),
                  ),
                  if (onClear != null)
                    _PressableMaterial(
                      child: InkWell(
                        onTap: onClear,
                        borderRadius: BorderRadius.circular(8),
                        child: Padding(
                          padding: const EdgeInsets.all(4),
                          child: Icon(
                            Icons.close_rounded,
                            color: Colors.white.withOpacity(0.5),
                            size: 15,
                          ),
                        ),
                      ),
                    )
                  else
                    Icon(
                      Icons.calendar_today_rounded,
                      color: Colors.white.withOpacity(0.4),
                      size: 14,
                    ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildDeleteButton() {
    return _PressableMaterial(
      child: InkWell(
        onTap: () => widget.onDelete!(),
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: _joviErrorRed.withOpacity(0.06),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: _joviErrorRed.withOpacity(0.3),
              width: 1,
            ),
          ),
          child: Row(
            children: [
              const Icon(
                Icons.delete_outline_rounded,
                color: _joviErrorRed,
                size: 17,
              ),
              const SizedBox(width: 10),
              const Text(
                'Delete this vaccination record',
                style: TextStyle(
                  color: _joviErrorRed,
                  fontSize: 13.5,
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.2,
                ),
              ),
              const Spacer(),
              Icon(
                Icons.chevron_right_rounded,
                color: _joviErrorRed.withOpacity(0.5),
                size: 18,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSaveBar() {
    return Container(
      padding: const EdgeInsets.fromLTRB(18, 12, 18, 16),
      decoration: BoxDecoration(
        color: _joviNavyDark.withOpacity(0.98),
        border: Border(
          top: BorderSide(
            color: Colors.white.withOpacity(0.08),
            width: 1,
          ),
        ),
      ),
      child: SafeArea(
        top: false,
        child: _PressableMaterial(
          child: InkWell(
            onTap: _onSaveTapped,
            borderRadius: BorderRadius.circular(14),
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: 14),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [_petAccent, _petAccentDark],
                ),
                borderRadius: BorderRadius.circular(14),
                boxShadow: [
                  BoxShadow(
                    color: _petAccent.withOpacity(0.4),
                    blurRadius: 16,
                    offset: const Offset(0, 6),
                  ),
                ],
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    _isEditing ? Icons.check_rounded : Icons.add_rounded,
                    color: Colors.white,
                    size: 18,
                  ),
                  const SizedBox(width: 7),
                  Text(
                    _isEditing ? 'Save Changes' : 'Add Vaccination',
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
        ),
      ),
    );
  }
}
