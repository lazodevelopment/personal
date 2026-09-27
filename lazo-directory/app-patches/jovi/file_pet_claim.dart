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
// JOVI HEALTH — FILE PET CLAIM
// Version: 2026.09.22-r2 (Apple HIG pass: press feedback, painted glass,
//          Reduce Motion, Cupertino photo sheet, navy toasts, title case)
// r1:      2026.04.18
// Build: JC-PETCLAIM-0922-002
//
// Cost-sharing claim flow for pets. Jovi covers 90% of eligible vet bills.
// Ineligible categories (surfaced via upfront disclaimer the member must
// acknowledge before submitting):
//   - Vaccinations / immunizations
//   - Grooming / nail trims
//   - Food / supplements / treats
//   - Pre-existing conditions
//   - Cosmetic and breeding costs
//
// Architecture notes:
//   - Per-pet claims at users/{uid}/pets/{petId}/claims/{claimId}
//   - One pet per claim (member picks at start)
//   - Single main receipt + optional additional correspondence documents
//     (matches human FileClaim pattern)
//   - Estimated reimbursement (90%) is DISPLAY-ONLY; final amount is set
//     by Jovi review staff in the claim doc on the Pending → Approved path
//   - No third-party carrier integration — Jovi is the direct payer
//   - No payment processor SDK — pet claims are INBOUND reimbursements
//     from Jovi to member, not outbound payments (unlike human FileClaim
//     which uses PayArc for member-to-provider payment)
//   - memberAcknowledgedExclusions flag is written on submit so Jovi
//     review can verify the member saw the exclusion list
// ═══════════════════════════════════════════════════════════════════════════

import 'dart:convert';
import 'dart:async';
import 'dart:io';
import 'dart:typed_data';
import 'dart:ui' as ui_dart;
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';
import 'package:image_picker/image_picker.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_storage/firebase_storage.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:intl/intl.dart';

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

class FilePetClaim extends StatefulWidget {
  // No required params.
  final String? petId; // optional — deep-link from a pet profile

  final double? width;
  final double? height;

  const FilePetClaim({
    Key? key,
    this.width,
    this.height,
    this.petId,
  }) : super(key: key);

  @override
  State<FilePetClaim> createState() => _FilePetClaimState();
}

class _FilePetClaimState extends State<FilePetClaim>
    with TickerProviderStateMixin {
  // ─── Tab state ──────────────────────────────────────────────────────────
  _Tab _currentTab = _Tab.newClaim;

  // ─── New Claim flow state ───────────────────────────────────────────────
  _FlowStep _flowStep = _FlowStep.petPicker;
  final _ClaimDraft _draft = _ClaimDraft();

  // Form controllers (retained across steps so member can scroll back)
  final TextEditingController _amountCtrl = TextEditingController();
  final TextEditingController _clinicCtrl = TextEditingController();
  final TextEditingController _reasonCtrl = TextEditingController();
  final ImagePicker _imagePicker = ImagePicker();

  // Upload state
  bool _uploadingReceipt = false;
  bool _uploadingCorrespondence = false;
  double? _uploadProgress; // 0.0–1.0 display only
  bool _submitting = false;
  String? _submittedClaimId;

  // ─── Pets state ─────────────────────────────────────────────────────────
  List<_PetLite> _pets = [];
  bool _petsLoading = true;
  String? _petsError;

  // ─── Claims stream (across all pets) ────────────────────────────────────
  // We subscribe per-pet and merge into a single flat list sorted desc by
  // submittedAt. Keeps the "My claims" tab simple while still scoping
  // reads to the pet's own subcollection (for security rules).
  final Map<String, List<_PetClaim>> _claimsByPet = {};
  final Map<String, StreamSubscription<QuerySnapshot<Map<String, dynamic>>>>
      _claimsSubs = {};
  final Map<String, String?> _claimsErrors = {};
  bool _claimsInitialLoad = true;

  // ─── Animations ─────────────────────────────────────────────────────────
  late AnimationController _fadeCtrl;
  late Animation<double> _fadeAnim;

  // ─── Derived ────────────────────────────────────────────────────────────
  List<_PetClaim> get _allClaimsFlat {
    final all = <_PetClaim>[];
    for (final list in _claimsByPet.values) {
      all.addAll(list);
    }
    all.sort((a, b) {
      final aT = a.submittedAt ?? a.updatedAt ?? DateTime.now();
      final bT = b.submittedAt ?? b.updatedAt ?? DateTime.now();
      return bT.compareTo(aT);
    });
    return all;
  }

  // ─── Lifecycle ──────────────────────────────────────────────────────────
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

    _loadPets();
  }

  /// Re-runs the content fade after a tab or step change. Starts from a
  /// third of the way in so the screen never blinks to black, and is a
  /// no-op when Reduce Motion is on.
  void _replayFade() {
    if (!mounted) return;
    if (MediaQuery.maybeOf(context)?.disableAnimations ?? false) {
      _fadeCtrl.value = 1.0;
    } else {
      _fadeCtrl.forward(from: 0.35);
    }
  }

  @override
  void dispose() {
    _fadeCtrl.dispose();
    _amountCtrl.dispose();
    _clinicCtrl.dispose();
    _reasonCtrl.dispose();
    for (final sub in _claimsSubs.values) {
      sub.cancel();
    }
    _claimsSubs.clear();
    super.dispose();
  }

  // ═══════════════════════════════════════════════════════════════════════
  // PET LOADING (dual-source — same pattern as other pet widgets)
  // ═══════════════════════════════════════════════════════════════════════

  Future<void> _loadPets() async {
    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user == null) {
        if (mounted) {
          setState(() {
            _petsLoading = false;
            _claimsInitialLoad = false;
          });
        }
        return;
      }

      final userDocF =
          FirebaseFirestore.instance.collection('users').doc(user.uid).get();
      final subcollF = FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .collection('pets')
          .get();

      final results = await Future.wait([userDocF, subcollF]);
      final userDoc = results[0] as DocumentSnapshot<Map<String, dynamic>>;
      final subcoll = results[1] as QuerySnapshot<Map<String, dynamic>>;

      final byId = <String, _PetLite>{};
      for (final doc in subcoll.docs) {
        try {
          final pet = _PetLite.fromSubcollection(doc.id, doc.data());
          byId[pet.petId] = pet;
        } catch (e) {
          debugPrint('FilePetClaim: skipped malformed pet ${doc.id}: $e');
        }
      }

      final userData = userDoc.data();
      final rawPets = userData?['pets'];
      List<dynamic>? legacyList;
      if (rawPets is List) {
        legacyList = rawPets;
      } else if (rawPets is String) {
        try {
          final parsed = jsonDecode(rawPets);
          if (parsed is List) legacyList = parsed;
        } catch (_) {}
      }
      if (legacyList != null) {
        for (final item in legacyList) {
          if (item is! Map) continue;
          try {
            final m = Map<String, dynamic>.from(item);
            final pet = _PetLite.fromLegacyJson(m);
            byId.putIfAbsent(pet.petId, () => pet);
          } catch (e) {
            debugPrint('FilePetClaim: skipped malformed legacy pet: $e');
          }
        }
      }

      if (!mounted) return;

      final list = byId.values.toList()
        ..sort((a, b) => a.name.toLowerCase().compareTo(b.name.toLowerCase()));

      setState(() {
        _pets = list;
        _petsLoading = false;
        _petsError = null;
      });

      // If deep-linked with a petId, pre-select it for the new claim flow
      if (widget.petId != null && widget.petId!.isNotEmpty) {
        for (final p in list) {
          if (p.petId == widget.petId) {
            _draft.pet = p;
            break;
          }
        }
        // If only a single pet matches, skip straight to the disclaimer
        if (_draft.pet != null) {
          setState(() => _flowStep = _FlowStep.disclaimer);
        }
      }

      // Single-pet households: pre-fill and advance past picker
      if (list.length == 1 && _draft.pet == null) {
        _draft.pet = list.first;
        setState(() => _flowStep = _FlowStep.disclaimer);
      }

      // Subscribe to claims for every pet (for the "My claims" tab)
      for (final p in list) {
        _subscribeClaimsForPet(p.petId);
      }
      if (list.isEmpty) {
        setState(() => _claimsInitialLoad = false);
      }
    } catch (e) {
      debugPrint('FilePetClaim: failed to load pets: $e');
      if (!mounted) return;
      setState(() {
        _petsLoading = false;
        _petsError = _friendlyErrorMessage(_classifyError(e));
        _claimsInitialLoad = false;
      });
    }
  }

  // ═══════════════════════════════════════════════════════════════════════
  // CLAIMS SUBSCRIPTIONS (per-pet)
  // ═══════════════════════════════════════════════════════════════════════

  void _subscribeClaimsForPet(String petId) {
    _claimsSubs[petId]?.cancel();
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return;
    try {
      final sub = FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .collection('pets')
          .doc(petId)
          .collection('claims')
          .orderBy('submittedAt', descending: true)
          .limit(100)
          .snapshots()
          .listen(
        (snap) {
          if (!mounted) return;
          final list = <_PetClaim>[];
          for (final doc in snap.docs) {
            try {
              list.add(_PetClaim.fromFirestore(doc.id, doc.data()));
            } catch (e) {
              debugPrint('FilePetClaim: skipped malformed claim ${doc.id}: $e');
            }
          }
          setState(() {
            _claimsByPet[petId] = list;
            _claimsErrors[petId] = null;
            _claimsInitialLoad = false;
          });
        },
        onError: (err) {
          debugPrint('FilePetClaim: claims listener error ($petId): $err');
          if (!mounted) return;
          setState(() {
            _claimsErrors[petId] = _friendlyErrorMessage(_classifyError(err));
            _claimsInitialLoad = false;
          });
        },
        cancelOnError: false,
      );
      _claimsSubs[petId] = sub;
    } catch (e) {
      debugPrint('FilePetClaim: failed to subscribe to claims ($petId): $e');
      if (!mounted) return;
      setState(() {
        _claimsErrors[petId] = _friendlyErrorMessage(_classifyError(e));
      });
    }
  }

  // ═══════════════════════════════════════════════════════════════════════
  // DRAFT MANAGEMENT
  // ═══════════════════════════════════════════════════════════════════════

  void _resetDraft() {
    setState(() {
      _draft.pet = null;
      _draft.acknowledgedExclusions = false;
      _draft.exclusionsAcknowledgedAt = null;
      _draft.photoUrl = null;
      _draft.photoStoragePath = null;
      _draft.photoLocalPreviewPath = null;
      _draft.photoBytes = null;
      _draft.amount = 0.0;
      _draft.dateOfService = DateTime.now();
      _draft.providerClinic = '';
      _draft.reason = '';
      _draft.correspondences = [];
      _amountCtrl.clear();
      _clinicCtrl.clear();
      _reasonCtrl.clear();
      _flowStep = _FlowStep.petPicker;
      _submittedClaimId = null;
      _uploadProgress = null;
    });
  }

  void _selectPetForDraft(_PetLite pet) {
    HapticFeedback.selectionClick();
    setState(() {
      _draft.pet = pet;
      _flowStep = _FlowStep.disclaimer;
    });
    _replayFade();
  }

  void _acknowledgeExclusions() {
    HapticFeedback.lightImpact();
    setState(() {
      _draft.acknowledgedExclusions = true;
      _draft.exclusionsAcknowledgedAt = DateTime.now();
      _flowStep = _FlowStep.receipt;
    });
    _replayFade();
  }

  void _advanceFlow(_FlowStep target) {
    HapticFeedback.lightImpact();
    setState(() => _flowStep = target);
    _replayFade();
  }

  void _backFlow() {
    HapticFeedback.lightImpact();
    _FlowStep? target;
    if (_flowStep == _FlowStep.disclaimer) {
      target = _FlowStep.petPicker;
    } else if (_flowStep == _FlowStep.receipt) {
      target = _FlowStep.disclaimer;
    } else if (_flowStep == _FlowStep.details) {
      target = _FlowStep.receipt;
    } else if (_flowStep == _FlowStep.correspondences) {
      target = _FlowStep.details;
    } else if (_flowStep == _FlowStep.review) {
      target = _FlowStep.correspondences;
    }
    if (target != null) {
      setState(() => _flowStep = target!);
      _replayFade();
    }
  }

  // ═══════════════════════════════════════════════════════════════════════
  // RECEIPT PHOTO UPLOAD
  // ═══════════════════════════════════════════════════════════════════════

  Future<void> _pickAndUploadReceipt({required ImageSource source}) async {
    if (_uploadingReceipt) return;
    HapticFeedback.lightImpact();
    try {
      final xfile = await _imagePicker.pickImage(
        source: source,
        maxWidth: 2400,
        maxHeight: 2400,
        imageQuality: 85,
      );
      if (xfile == null) return;
      if (!mounted) return;
      setState(() {
        _uploadingReceipt = true;
        _uploadProgress = 0.0;
      });

      // Prepare preview + upload source depending on platform
      Uint8List? bytes;
      File? file;
      if (kIsWeb) {
        bytes = await xfile.readAsBytes();
      } else {
        file = File(xfile.path);
      }
      if (!mounted) return;
      setState(() {
        _draft.photoBytes = bytes;
        _draft.photoLocalPreviewPath = file?.path;
      });

      // Generate a stable claimId for the draft so all uploads share a dir.
      // We'll write this as the claim doc id at submit time.
      final claimId = _draft.photoStoragePath != null
          ? _draft.photoStoragePath!.split('/').reversed.skip(1).first
          : _makeLocalDraftId();

      final service = _PetClaimService();
      final result = await service.uploadFile(
        claimId: claimId,
        filename: 'receipt_${DateTime.now().millisecondsSinceEpoch}.jpg',
        source: kIsWeb ? bytes! : file!,
        contentType: 'image/jpeg',
      );

      if (!mounted) return;
      setState(() {
        _draft.photoUrl = result.url;
        _draft.photoStoragePath = result.storagePath;
        _uploadingReceipt = false;
        _uploadProgress = null;
      });
      HapticFeedback.mediumImpact();
    } catch (e) {
      debugPrint('FilePetClaim: receipt upload failed: $e');
      if (!mounted) return;
      setState(() {
        _uploadingReceipt = false;
        _uploadProgress = null;
      });
      _showSnackBar(
        'Could not upload your receipt. Please try again.',
        isError: true,
      );
    }
  }

  String _makeLocalDraftId() {
    final ts = DateTime.now().millisecondsSinceEpoch;
    return 'draft_${ts}_${(ts ~/ 1000).toRadixString(36)}';
  }

  void _removeReceiptPhoto() {
    HapticFeedback.lightImpact();
    setState(() {
      _draft.photoUrl = null;
      _draft.photoStoragePath = null;
      _draft.photoLocalPreviewPath = null;
      _draft.photoBytes = null;
    });
  }

  // ═══════════════════════════════════════════════════════════════════════
  // CORRESPONDENCE UPLOAD (optional additional docs)
  // ═══════════════════════════════════════════════════════════════════════

  Future<void> _pickAndAddCorrespondence({
    required ImageSource source,
    required String type,
    required String description,
  }) async {
    if (_uploadingCorrespondence) return;
    HapticFeedback.lightImpact();
    try {
      final xfile = await _imagePicker.pickImage(
        source: source,
        maxWidth: 2400,
        maxHeight: 2400,
        imageQuality: 85,
      );
      if (xfile == null) return;
      if (!mounted) return;
      setState(() => _uploadingCorrespondence = true);

      Uint8List? bytes;
      File? file;
      if (kIsWeb) {
        bytes = await xfile.readAsBytes();
      } else {
        file = File(xfile.path);
      }

      final claimId = _draft.photoStoragePath != null
          ? _draft.photoStoragePath!.split('/').reversed.skip(1).first
          : _makeLocalDraftId();

      final service = _PetClaimService();
      final corrId = 'corr_${DateTime.now().millisecondsSinceEpoch}';
      final result = await service.uploadFile(
        claimId: claimId,
        filename: '${corrId}.jpg',
        source: kIsWeb ? bytes! : file!,
        contentType: 'image/jpeg',
      );

      if (!mounted) return;
      setState(() {
        _draft.correspondences.add(_Correspondence(
          id: corrId,
          url: result.url,
          description: description,
          uploadedAt: DateTime.now(),
          type: type,
        ));
        _uploadingCorrespondence = false;
      });
      HapticFeedback.mediumImpact();
    } catch (e) {
      debugPrint('FilePetClaim: correspondence upload failed: $e');
      if (!mounted) return;
      setState(() => _uploadingCorrespondence = false);
      _showSnackBar('Could not upload that document. Please try again.',
          isError: true);
    }
  }

  void _removeCorrespondence(String corrId) {
    HapticFeedback.lightImpact();
    setState(() {
      _draft.correspondences.removeWhere((c) => c.id == corrId);
    });
  }

  // ═══════════════════════════════════════════════════════════════════════
  // SUBMIT
  // ═══════════════════════════════════════════════════════════════════════

  Future<void> _submitClaim() async {
    if (_submitting) return;
    if (!_draft.isReadyToSubmit) {
      _showSnackBar('Please complete all required fields.', isError: true);
      return;
    }
    HapticFeedback.mediumImpact();
    setState(() => _submitting = true);
    try {
      final service = _PetClaimService();
      final claimId = await service.submitClaim(_draft);
      if (!mounted) return;
      setState(() {
        _submittedClaimId = claimId;
        _flowStep = _FlowStep.submitted;
        _submitting = false;
      });
      HapticFeedback.heavyImpact();
    } catch (e) {
      debugPrint('FilePetClaim: submit failed: $e');
      if (!mounted) return;
      setState(() => _submitting = false);
      _showSnackBar(
        'Could not submit your claim right now. Please try again.',
        isError: true,
      );
    }
  }

  // ═══════════════════════════════════════════════════════════════════════
  // UX HELPERS
  // ═══════════════════════════════════════════════════════════════════════

  void _showSnackBar(String message, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(message,
        accent: isError ? _joviErrorRed : _joviMintDark,
        icon: isError
            ? CupertinoIcons.exclamationmark_circle
            : CupertinoIcons.checkmark_circle));
  }

  String _formatUsd(double v) {
    final fmt = NumberFormat.currency(symbol: '\$', decimalDigits: 2);
    return fmt.format(v);
  }

  String _formatShortDate(DateTime d) {
    return DateFormat('MMM d, y').format(d);
  }

  String _formatRelative(DateTime d) {
    final now = DateTime.now();
    final diff = now.difference(d);
    if (diff.inMinutes < 60) {
      final m = diff.inMinutes;
      return m <= 1 ? 'Just now' : '$m min ago';
    }
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    if (diff.inDays == 1) return 'Yesterday';
    if (diff.inDays < 7) return '${diff.inDays}d ago';
    return DateFormat('MMM d, y').format(d);
  }

  // ═══════════════════════════════════════════════════════════════════════
  // ROOT BUILD
  // ═══════════════════════════════════════════════════════════════════════

  @override
  Widget build(BuildContext context) {
    final mq = MediaQuery.of(context).size;
    return Container(
      width: mq.width,
      height: mq.height,
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [_joviNavy, _joviNavyDark],
        ),
      ),
      child: SafeArea(
        top: false,
        child: FadeTransition(
          opacity: _fadeAnim,
          child: Column(
            children: [
              _buildHeader(),
              _buildTabBar(),
              Expanded(child: _buildTabContent()),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTabContent() {
    if (_currentTab == _Tab.newClaim) return _buildNewClaimView();
    return _buildMyClaimsView();
  }

  // ═══════════════════════════════════════════════════════════════════════
  // HEADER
  // ═══════════════════════════════════════════════════════════════════════

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(8, 14, 16, 8),
      child: Row(
        children: [
          // Back button — lets users exit the claim flow.
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
                    Icons.arrow_back_rounded,
                    color: Colors.white.withOpacity(0.85),
                    size: 18,
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(width: 10),
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [_petAccent, _petAccentDark],
              ),
              borderRadius: BorderRadius.circular(11),
              boxShadow: [
                BoxShadow(
                  color: _petAccent.withOpacity(0.35),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: const Icon(
              Icons.receipt_long_rounded,
              color: Colors.white,
              size: 20,
            ),
          ),
          const SizedBox(width: 10),
          const Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'File Pet Claim',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 17,
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.4,
                    height: 1.1,
                  ),
                ),
                SizedBox(height: 1),
                Text(
                  'Jovi covers 90% of eligible bills',
                  style: TextStyle(
                    color: Color(0x88FFFFFF),
                    fontSize: 10.5,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0.1,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // TAB BAR
  // ═══════════════════════════════════════════════════════════════════════

  Widget _buildTabBar() {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 4, 16, 6),
      padding: const EdgeInsets.all(3),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.06),
        borderRadius: BorderRadius.circular(11),
        border: Border.all(
          color: Colors.white.withOpacity(0.1),
          width: 0.8,
        ),
      ),
      child: Row(
        children: [
          _tabBarItem(_Tab.newClaim, 'New Claim', Icons.add_circle_rounded),
          _tabBarItem(_Tab.myClaims, 'My Claims', Icons.history_rounded),
        ],
      ),
    );
  }

  Widget _tabBarItem(_Tab tab, String label, IconData icon) {
    final selected = _currentTab == tab;
    return Expanded(
      child: _PressableMaterial(
        child: InkWell(
          onTap: () {
            if (_currentTab == tab) return;
            HapticFeedback.selectionClick();
            setState(() => _currentTab = tab);
            _replayFade();
          },
          borderRadius: BorderRadius.circular(9),
          child: AnimatedContainer(
            duration: _Motion.select,
            curve: _Motion.settle,
            padding: const EdgeInsets.symmetric(vertical: 10),
            decoration: BoxDecoration(
              color:
                  selected ? _petAccent.withOpacity(0.22) : Colors.transparent,
              borderRadius: BorderRadius.circular(9),
              border: selected
                  ? Border.all(
                      color: _petAccent.withOpacity(0.4),
                      width: 0.8,
                    )
                  : null,
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  icon,
                  size: 14,
                  color: selected ? _petAccent : Colors.white.withOpacity(0.55),
                ),
                const SizedBox(width: 5),
                Flexible(
                  child: Text(
                    label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: selected
                          ? Colors.white
                          : Colors.white.withOpacity(0.55),
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                      letterSpacing: -0.2,
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

  // ═══════════════════════════════════════════════════════════════════════
  // COMMON HELPERS (glass / pill / button / pet avatar)
  // ═══════════════════════════════════════════════════════════════════════

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
          padding: padding ?? const EdgeInsets.all(16),
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
              fontSize: 11.5,
              fontWeight: FontWeight.w700,
              letterSpacing: -0.1,
            ),
          ),
        ],
      ),
    );
  }

  Widget _primaryButton({
    required String label,
    required VoidCallback? onTap,
    IconData? icon,
    Color? accent,
    Color? accentDark,
    bool loading = false,
  }) {
    final c1 = accent ?? _petAccent;
    final c2 = accentDark ?? _petAccentDark;
    final enabled = onTap != null && !loading;
    return _PressableMaterial(
      child: InkWell(
        onTap: enabled
            ? () {
                HapticFeedback.mediumImpact();
                onTap();
              }
            : null,
        borderRadius: BorderRadius.circular(14),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(vertical: 14),
          decoration: BoxDecoration(
            gradient: enabled
                ? LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [c1, c2],
                  )
                : null,
            color: enabled ? null : Colors.white.withOpacity(0.06),
            borderRadius: BorderRadius.circular(14),
            border: enabled
                ? null
                : Border.all(
                    color: Colors.white.withOpacity(0.12),
                    width: 1,
                  ),
            boxShadow: enabled
                ? [
                    BoxShadow(
                      color: c1.withOpacity(0.4),
                      blurRadius: 16,
                      offset: const Offset(0, 6),
                    ),
                  ]
                : null,
          ),
          child: loading
              ? const Center(
                  child: SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2.2,
                      valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                    ),
                  ),
                )
              : Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      label,
                      style: TextStyle(
                        color: enabled
                            ? Colors.white
                            : Colors.white.withOpacity(0.4),
                        fontSize: 15,
                        fontWeight: FontWeight.w800,
                        letterSpacing: -0.2,
                      ),
                    ),
                    if (icon != null) ...[
                      const SizedBox(width: 6),
                      Icon(icon,
                          color: enabled
                              ? Colors.white
                              : Colors.white.withOpacity(0.4),
                          size: 18),
                    ],
                  ],
                ),
        ),
      ),
    );
  }

  Widget _secondaryButton({
    required String label,
    required VoidCallback onTap,
    IconData? icon,
  }) {
    return _PressableMaterial(
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
              color: Colors.white.withOpacity(0.18),
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
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.2,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _petAvatar(_PetLite? pet, {double size = 28}) {
    if (pet?.photoUrl != null && pet!.photoUrl!.isNotEmpty) {
      return ClipOval(
        child: Image.network(
          pet.photoUrl!,
          width: size,
          height: size,
          fit: BoxFit.cover,
          errorBuilder: (_, __, ___) => _petAvatarFallback(pet, size),
        ),
      );
    }
    return _petAvatarFallback(pet, size);
  }

  Widget _petAvatarFallback(_PetLite? pet, double size) {
    return Container(
      width: size,
      height: size,
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: [_petAccent, _petAccentDark],
        ),
        shape: BoxShape.circle,
      ),
      child: Icon(
        Icons.pets_rounded,
        color: Colors.white,
        size: size * 0.55,
      ),
    );
  }

  String _petSubtitle(_PetLite pet) {
    final parts = <String>[];
    if (pet.type == PetType.dog) {
      parts.add('Dog');
    } else if (pet.type == PetType.cat) {
      parts.add('Cat');
    }
    if (pet.breed != null && pet.breed!.isNotEmpty) parts.add(pet.breed!);
    final age = pet.ageYears;
    if (age != null) parts.add('$age yr');
    if (parts.isEmpty) return '—';
    return parts.join(' · ');
  }

  /// Step indicator shown at the top of the New Claim flow, e.g. "2 of 6"
  /// with a progress bar. Submitted step shows nothing (success screen).
  Widget _buildFlowProgress() {
    if (_flowStep == _FlowStep.submitted) return const SizedBox.shrink();
    final idx = _flowStepIndex(_flowStep);
    const total = 6; // petPicker..review
    final progress = (idx / (total - 1)).clamp(0.0, 1.0);
    final stepLabels = [
      'Choose pet',
      'Coverage details',
      'Upload receipt',
      'Bill details',
      'Additional docs',
      'Review',
    ];
    final label = idx < stepLabels.length ? stepLabels[idx] : '';
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Text(
                'Step ${idx + 1} of $total',
                style: TextStyle(
                  color: _petAccent.withOpacity(0.9),
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  letterSpacing: -0.1,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  label,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 11.5,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.2,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          ClipRRect(
            borderRadius: BorderRadius.circular(3),
            child: LinearProgressIndicator(
              value: progress,
              minHeight: 4,
              backgroundColor: Colors.white.withOpacity(0.08),
              valueColor: const AlwaysStoppedAnimation<Color>(_petAccent),
            ),
          ),
        ],
      ),
    );
  }

  /// Empty-state card used across tabs and empty claim history.
  Widget _buildNoPetEmptyState({
    required String title,
    required String body,
    String? ctaLabel,
    VoidCallback? onCta,
  }) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
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
              child: Icon(
                Icons.pets_outlined,
                color: Colors.white.withOpacity(0.4),
                size: 32,
              ),
            ),
            const SizedBox(height: 18),
            Text(
              title,
              style: const TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.w800,
                color: Colors.white,
                letterSpacing: -0.3,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              body,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 13,
                color: Colors.white.withOpacity(0.55),
                fontWeight: FontWeight.w500,
                height: 1.35,
              ),
            ),
            if (ctaLabel != null && onCta != null) ...[
              const SizedBox(height: 20),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: _primaryButton(
                  label: ctaLabel,
                  icon: Icons.arrow_forward_rounded,
                  onTap: onCta,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // NEW CLAIM VIEW (dispatches to current flow step)
  // ═══════════════════════════════════════════════════════════════════════

  Widget _buildNewClaimView() {
    if (_petsLoading) {
      return const Center(
        child: SizedBox(
          width: 28,
          height: 28,
          child: CircularProgressIndicator(
            strokeWidth: 2.5,
            valueColor: AlwaysStoppedAnimation<Color>(_petAccent),
          ),
        ),
      );
    }
    if (_pets.isEmpty) {
      return _buildNoPetEmptyState(
        title: 'No pet yet',
        body:
            'Add a pet from your account to start submitting claims for their vet bills.',
      );
    }
    return Column(
      children: [
        _buildFlowProgress(),
        Expanded(child: _buildFlowStepView()),
      ],
    );
  }

  Widget _buildFlowStepView() {
    if (_flowStep == _FlowStep.petPicker) return _buildPetPickerStep();
    if (_flowStep == _FlowStep.disclaimer) return _buildDisclaimerStep();
    if (_flowStep == _FlowStep.receipt) return _buildReceiptStep();
    if (_flowStep == _FlowStep.details) return _buildDetailsStep();
    if (_flowStep == _FlowStep.correspondences) {
      return _buildCorrespondencesStep();
    }
    if (_flowStep == _FlowStep.review) return _buildReviewStep();
    return _buildSubmittedStep();
  }

  // ─────────────────────────────────────────────────────────────────────
  // STEP 1: PET PICKER
  // ─────────────────────────────────────────────────────────────────────

  Widget _buildPetPickerStep() {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
      children: [
        const SizedBox(height: 4),
        const Text(
          'Which pet is this claim for?',
          style: TextStyle(
            color: Colors.white,
            fontSize: 20,
            fontWeight: FontWeight.w700,
            letterSpacing: -0.4,
            height: 1.2,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          'One pet per claim — just like the vet bill itself.',
          style: TextStyle(
            color: Colors.white.withOpacity(0.55),
            fontSize: 13,
            fontWeight: FontWeight.w500,
            height: 1.35,
          ),
        ),
        const SizedBox(height: 16),
        ..._pets.map(_buildPetPickerCard),
      ],
    );
  }

  Widget _buildPetPickerCard(_PetLite pet) {
    final selected = _draft.pet?.petId == pet.petId;
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: _PressableMaterial(
        child: InkWell(
          onTap: () => _selectPetForDraft(pet),
          borderRadius: BorderRadius.circular(16),
          child: _glassCard(
            bgOpacity: selected ? 0.1 : 0.06,
            borderOpacity: selected ? 0.35 : 0.12,
            borderWidth: selected ? 1.5 : 1,
            padding: const EdgeInsets.all(14),
            radius: 16,
            borderTint: selected ? _petAccent : null,
            child: Row(
              children: [
                _petAvatar(pet, size: 48),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        pet.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 15.5,
                          fontWeight: FontWeight.w800,
                          letterSpacing: -0.2,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        _petSubtitle(pet),
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.6),
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
                if (selected)
                  Container(
                    width: 28,
                    height: 28,
                    decoration: BoxDecoration(
                      color: _petAccent,
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: _petAccent.withOpacity(0.5),
                          blurRadius: 10,
                          offset: const Offset(0, 3),
                        ),
                      ],
                    ),
                    child: const Icon(Icons.check_rounded,
                        color: Colors.white, size: 16),
                  )
                else
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
    );
  }

  // ─────────────────────────────────────────────────────────────────────
  // STEP 2: DISCLAIMER (ineligibility list — MUST ACKNOWLEDGE)
  // ─────────────────────────────────────────────────────────────────────

  Widget _buildDisclaimerStep() {
    return Column(
      children: [
        Expanded(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
            children: [
              const SizedBox(height: 4),
              Container(
                width: 64,
                height: 64,
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [_petAccent, _petAccentDark],
                  ),
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: _petAccent.withOpacity(0.4),
                      blurRadius: 20,
                      offset: const Offset(0, 6),
                    ),
                  ],
                ),
                child: const Icon(
                  Icons.verified_user_rounded,
                  color: Colors.white,
                  size: 30,
                ),
              ),
              const SizedBox(height: 14),
              const Text(
                "Before you submit",
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.4,
                  height: 1.2,
                ),
              ),
              const SizedBox(height: 6),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8),
                child: Text(
                  'Jovi covers $_jovReimbursementRateLabel of eligible vet bills. Please confirm your bill doesn\'t include any of the categories below — those aren\'t covered.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.65),
                    fontSize: 13.5,
                    fontWeight: FontWeight.w500,
                    height: 1.45,
                  ),
                ),
              ),
              const SizedBox(height: 18),
              ..._petClaimExclusions.map(_buildExclusionRow),
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: _joviGold.withOpacity(0.09),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: _joviGold.withOpacity(0.28),
                    width: 0.8,
                  ),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.info_outline_rounded,
                        color: _joviGoldDark, size: 16),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        'If your bill includes both eligible and ineligible charges, submit anyway and note which is which in the description — our review team will sort it out.',
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.8),
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          height: 1.4,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        Container(
          padding: EdgeInsets.fromLTRB(
            16,
            10,
            16,
            MediaQuery.of(context).padding.bottom > 0 ? 8 : 16,
          ),
          decoration: BoxDecoration(
            border: Border(
              top: BorderSide(
                color: Colors.white.withOpacity(0.06),
                width: 1,
              ),
            ),
          ),
          child: Column(
            children: [
              _primaryButton(
                label: "I understand — my bill doesn't include these",
                icon: Icons.arrow_forward_rounded,
                onTap: _acknowledgeExclusions,
              ),
              const SizedBox(height: 8),
              _secondaryButton(
                label: 'Back',
                icon: Icons.arrow_back_rounded,
                onTap: _backFlow,
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildExclusionRow(_Exclusion e) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.05),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: e.accent.withOpacity(0.25),
            width: 1,
          ),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(
                color: e.accent.withOpacity(0.16),
                borderRadius: BorderRadius.circular(10),
                border:
                    Border.all(color: e.accent.withOpacity(0.3), width: 0.8),
              ),
              child: Icon(e.icon, color: e.accent, size: 19),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    e.title,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 14.5,
                      fontWeight: FontWeight.w800,
                      letterSpacing: -0.2,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    e.description,
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.65),
                      fontSize: 12.5,
                      fontWeight: FontWeight.w500,
                      height: 1.4,
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

  // ─────────────────────────────────────────────────────────────────────
  // STEP 3: RECEIPT UPLOAD
  // ─────────────────────────────────────────────────────────────────────

  Widget _buildReceiptStep() {
    final hasPhoto = _draft.photoUrl != null && _draft.photoUrl!.isNotEmpty;
    return Column(
      children: [
        Expanded(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
            children: [
              const SizedBox(height: 4),
              const Text(
                'Upload the vet receipt',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 20,
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.4,
                  height: 1.2,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                'A clear photo of the itemized bill. We need to see the clinic name, the charges, and the total.',
                style: TextStyle(
                  color: Colors.white.withOpacity(0.55),
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                  height: 1.35,
                ),
              ),
              const SizedBox(height: 18),
              if (hasPhoto)
                _buildReceiptPreview()
              else
                _buildReceiptUploadArea(),
              const SizedBox(height: 12),
              _receiptTipsCard(),
            ],
          ),
        ),
        Container(
          padding: EdgeInsets.fromLTRB(
            16,
            10,
            16,
            MediaQuery.of(context).padding.bottom > 0 ? 8 : 16,
          ),
          decoration: BoxDecoration(
            border: Border(
              top: BorderSide(
                color: Colors.white.withOpacity(0.06),
                width: 1,
              ),
            ),
          ),
          child: Column(
            children: [
              _primaryButton(
                label: 'Continue',
                icon: Icons.arrow_forward_rounded,
                onTap: hasPhoto ? () => _advanceFlow(_FlowStep.details) : null,
              ),
              const SizedBox(height: 8),
              _secondaryButton(
                label: 'Back',
                icon: Icons.arrow_back_rounded,
                onTap: _backFlow,
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildReceiptUploadArea() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: _petAccent.withOpacity(0.06),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: _petAccent.withOpacity(0.3),
          width: 1.5,
          strokeAlign: BorderSide.strokeAlignInside,
        ),
      ),
      child: Column(
        children: [
          Container(
            width: 60,
            height: 60,
            decoration: BoxDecoration(
              color: _petAccent.withOpacity(0.16),
              shape: BoxShape.circle,
              border: Border.all(
                color: _petAccent.withOpacity(0.35),
                width: 1,
              ),
            ),
            child: _uploadingReceipt
                ? const Padding(
                    padding: EdgeInsets.all(18),
                    child: CircularProgressIndicator(
                      strokeWidth: 2.5,
                      valueColor: AlwaysStoppedAnimation<Color>(_petAccent),
                    ),
                  )
                : const Icon(
                    Icons.receipt_long_rounded,
                    color: _petAccent,
                    size: 28,
                  ),
          ),
          const SizedBox(height: 14),
          Text(
            _uploadingReceipt ? 'Uploading…' : 'Add your receipt',
            style: const TextStyle(
              color: Colors.white,
              fontSize: 15,
              fontWeight: FontWeight.w800,
              letterSpacing: -0.2,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            _uploadingReceipt
                ? 'This usually takes a few seconds.'
                : 'Take a photo or choose one from your library.',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white.withOpacity(0.55),
              fontSize: 12.5,
              fontWeight: FontWeight.w500,
              height: 1.35,
            ),
          ),
          if (!_uploadingReceipt) ...[
            const SizedBox(height: 18),
            Row(
              children: [
                Expanded(
                  child: _secondaryButton(
                    label: 'Camera',
                    icon: Icons.camera_alt_rounded,
                    onTap: () =>
                        _pickAndUploadReceipt(source: ImageSource.camera),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _primaryButton(
                    label: 'Library',
                    icon: Icons.photo_library_rounded,
                    onTap: () =>
                        _pickAndUploadReceipt(source: ImageSource.gallery),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildReceiptPreview() {
    return Column(
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(18),
          child: Container(
            constraints: const BoxConstraints(maxHeight: 320),
            decoration: BoxDecoration(
              border: Border.all(
                color: _petAccent.withOpacity(0.35),
                width: 1.5,
              ),
              borderRadius: BorderRadius.circular(18),
            ),
            child: _receiptPreviewImage(),
          ),
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(
              child: _secondaryButton(
                label: 'Replace',
                icon: Icons.refresh_rounded,
                onTap: () => _showReceiptReplaceSheet(),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _PressableMaterial(
                child: InkWell(
                  onTap: _removeReceiptPhoto,
                  borderRadius: BorderRadius.circular(14),
                  child: Container(
                    padding: const EdgeInsets.symmetric(vertical: 13),
                    decoration: BoxDecoration(
                      color: _joviErrorRed.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(
                        color: _joviErrorRed.withOpacity(0.3),
                        width: 1,
                      ),
                    ),
                    child: const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.delete_outline_rounded,
                            color: _joviErrorRed, size: 17),
                        SizedBox(width: 6),
                        Text(
                          'Remove',
                          style: TextStyle(
                            color: _joviErrorRed,
                            fontSize: 14,
                            fontWeight: FontWeight.w800,
                            letterSpacing: -0.2,
                          ),
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
    );
  }

  Widget _receiptPreviewImage() {
    if (_draft.photoUrl != null && _draft.photoUrl!.isNotEmpty) {
      return Image.network(
        _draft.photoUrl!,
        fit: BoxFit.cover,
        width: double.infinity,
        errorBuilder: (_, __, ___) => _receiptPreviewPlaceholder(),
      );
    }
    if (_draft.photoBytes != null) {
      return Image.memory(_draft.photoBytes!,
          fit: BoxFit.cover, width: double.infinity);
    }
    if (!kIsWeb &&
        _draft.photoLocalPreviewPath != null &&
        _draft.photoLocalPreviewPath!.isNotEmpty) {
      return Image.file(File(_draft.photoLocalPreviewPath!),
          fit: BoxFit.cover, width: double.infinity);
    }
    return _receiptPreviewPlaceholder();
  }

  Widget _receiptPreviewPlaceholder() {
    return Container(
      height: 180,
      color: Colors.white.withOpacity(0.05),
      alignment: Alignment.center,
      child: Icon(
        Icons.image_not_supported_rounded,
        color: Colors.white.withOpacity(0.3),
        size: 40,
      ),
    );
  }

  void _showReceiptReplaceSheet() {
    HapticFeedback.lightImpact();
    showCupertinoModalPopup<void>(
      context: context,
      builder: (ctx) => CupertinoActionSheet(
        title: const Text('Replace Receipt'),
        actions: [
          CupertinoActionSheetAction(
            onPressed: () {
              Navigator.pop(ctx);
              _pickAndUploadReceipt(source: ImageSource.camera);
            },
            child: const Text('Take Photo'),
          ),
          CupertinoActionSheetAction(
            onPressed: () {
              Navigator.pop(ctx);
              _pickAndUploadReceipt(source: ImageSource.gallery);
            },
            child: const Text('Choose from Library'),
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

  Widget _receiptTipsCard() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.04),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: Colors.white.withOpacity(0.1),
          width: 0.8,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.tips_and_updates_outlined,
                  color: Colors.white.withOpacity(0.5), size: 14),
              const SizedBox(width: 6),
              Text(
                'Tips for a clear receipt',
                style: TextStyle(
                  color: Colors.white.withOpacity(0.7),
                  fontSize: 11.5,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0.2,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          _receiptTipBullet('Good lighting, no glare'),
          _receiptTipBullet('Full page — including clinic name and total'),
          _receiptTipBullet('Flat surface, all four corners visible'),
        ],
      ),
    );
  }

  Widget _receiptTipBullet(String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            margin: const EdgeInsets.only(top: 6),
            width: 4,
            height: 4,
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.35),
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              text,
              style: TextStyle(
                color: Colors.white.withOpacity(0.6),
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

  // ─────────────────────────────────────────────────────────────────────
  // STEP 4: DETAILS (amount, date, clinic, reason)
  // ─────────────────────────────────────────────────────────────────────

  Widget _buildDetailsStep() {
    final canContinue = _draft.amount > 0 &&
        _draft.providerClinic.trim().isNotEmpty &&
        _draft.reason.trim().isNotEmpty;
    return Column(
      children: [
        Expanded(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
            children: [
              const SizedBox(height: 4),
              const Text(
                'Bill details',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 20,
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.4,
                  height: 1.2,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                "We'll show you your estimated reimbursement on the next screen.",
                style: TextStyle(
                  color: Colors.white.withOpacity(0.55),
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                  height: 1.35,
                ),
              ),
              const SizedBox(height: 18),

              // Amount field
              _formFieldLabel('Total on the bill'),
              _amountField(),
              if (_draft.amount > 0) ...[
                const SizedBox(height: 8),
                _estimatePreviewRow(),
              ],
              const SizedBox(height: 18),

              // Date field
              _formFieldLabel('Date of visit'),
              _dateOfServiceField(),
              const SizedBox(height: 18),

              // Clinic field
              _formFieldLabel('Vet clinic name'),
              _clinicField(),
              const SizedBox(height: 18),

              // Reason field
              _formFieldLabel("What happened — brief description"),
              _reasonField(),
              const SizedBox(height: 6),
              Text(
                'Example: "Emergency visit for vomiting and lethargy — ended up being a GI blockage that needed an X-ray."',
                style: TextStyle(
                  color: Colors.white.withOpacity(0.4),
                  fontSize: 11.5,
                  fontWeight: FontWeight.w500,
                  height: 1.4,
                  fontStyle: FontStyle.italic,
                ),
              ),
            ],
          ),
        ),
        Container(
          padding: EdgeInsets.fromLTRB(
            16,
            10,
            16,
            MediaQuery.of(context).padding.bottom > 0 ? 8 : 16,
          ),
          decoration: BoxDecoration(
            border: Border(
              top: BorderSide(
                color: Colors.white.withOpacity(0.06),
                width: 1,
              ),
            ),
          ),
          child: Column(
            children: [
              _primaryButton(
                label: 'Continue',
                icon: Icons.arrow_forward_rounded,
                onTap: canContinue
                    ? () => _advanceFlow(_FlowStep.correspondences)
                    : null,
              ),
              const SizedBox(height: 8),
              _secondaryButton(
                label: 'Back',
                icon: Icons.arrow_back_rounded,
                onTap: _backFlow,
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _formFieldLabel(String label) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 7, left: 4),
      child: Text(
        label,
        style: TextStyle(
          color: Colors.white.withOpacity(0.65),
          fontSize: 12.5,
          fontWeight: FontWeight.w600,
          letterSpacing: -0.1,
        ),
      ),
    );
  }

  Widget _amountField() {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.06),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: _petAccent.withOpacity(0.25),
          width: 1,
        ),
      ),
      child: TextField(
        controller: _amountCtrl,
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        textInputAction: TextInputAction.next,
        inputFormatters: [
          FilteringTextInputFormatter.allow(RegExp(r'[0-9.]')),
        ],
        style: const TextStyle(
          color: Colors.white,
          fontSize: 18,
          fontWeight: FontWeight.w800,
          letterSpacing: -0.3,
        ),
        cursorColor: _petAccent,
        decoration: InputDecoration(
          prefixIcon: Padding(
            padding: const EdgeInsets.only(left: 14, right: 6),
            child: Icon(Icons.attach_money_rounded,
                color: _petAccent.withOpacity(0.8), size: 22),
          ),
          prefixIconConstraints: const BoxConstraints(minWidth: 0),
          hintText: '0.00',
          hintStyle: TextStyle(
            color: Colors.white.withOpacity(0.25),
            fontSize: 18,
            fontWeight: FontWeight.w700,
          ),
          border: InputBorder.none,
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 10, vertical: 14),
        ),
        onChanged: (v) {
          setState(() {
            _draft.amount = double.tryParse(v) ?? 0.0;
          });
        },
      ),
    );
  }

  Widget _estimatePreviewRow() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: _joviMint.withOpacity(0.09),
        borderRadius: BorderRadius.circular(11),
        border: Border.all(
          color: _joviMint.withOpacity(0.28),
          width: 0.8,
        ),
      ),
      child: Row(
        children: [
          const Icon(Icons.savings_outlined, color: _joviMintDark, size: 16),
          const SizedBox(width: 8),
          Expanded(
            child: Text.rich(
              TextSpan(
                style: TextStyle(
                  color: Colors.white.withOpacity(0.85),
                  fontSize: 12.5,
                  fontWeight: FontWeight.w600,
                  height: 1.35,
                ),
                children: [
                  const TextSpan(text: 'You\'d get back '),
                  TextSpan(
                    text: _formatUsd(_draft.estimatedReimbursement),
                    style: const TextStyle(
                      color: _joviMint,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const TextSpan(
                      text:
                          ' once approved (estimated — final amount set by Jovi review).'),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _dateOfServiceField() {
    return _PressableMaterial(
      child: InkWell(
        onTap: _pickDateOfService,
        borderRadius: BorderRadius.circular(14),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.06),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: _petAccent.withOpacity(0.25),
              width: 1,
            ),
          ),
          child: Row(
            children: [
              Icon(Icons.calendar_today_rounded,
                  color: _petAccent.withOpacity(0.8), size: 18),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  _formatShortDate(_draft.dateOfService),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.2,
                  ),
                ),
              ),
              Icon(Icons.chevron_right_rounded,
                  color: Colors.white.withOpacity(0.4), size: 20),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _pickDateOfService() async {
    HapticFeedback.lightImpact();
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: _draft.dateOfService,
      firstDate: DateTime(now.year - 2),
      lastDate: now,
      builder: (ctx, child) {
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
      },
    );
    if (picked == null) return;
    if (!mounted) return;
    setState(() => _draft.dateOfService = picked);
  }

  Widget _clinicField() {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.06),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: _petAccent.withOpacity(0.25),
          width: 1,
        ),
      ),
      child: TextField(
        controller: _clinicCtrl,
        textCapitalization: TextCapitalization.words,
        textInputAction: TextInputAction.next,
        style: const TextStyle(
          color: Colors.white,
          fontSize: 15,
          fontWeight: FontWeight.w600,
          letterSpacing: -0.2,
        ),
        cursorColor: _petAccent,
        decoration: InputDecoration(
          prefixIcon: Padding(
            padding: const EdgeInsets.only(left: 14, right: 6),
            child: Icon(Icons.local_hospital_rounded,
                color: _petAccent.withOpacity(0.8), size: 20),
          ),
          prefixIconConstraints: const BoxConstraints(minWidth: 0),
          hintText: 'e.g. Firehouse Animal Health Center',
          hintStyle: TextStyle(
            color: Colors.white.withOpacity(0.3),
            fontSize: 14,
            fontWeight: FontWeight.w500,
          ),
          border: InputBorder.none,
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 10, vertical: 14),
        ),
        onChanged: (v) {
          setState(() => _draft.providerClinic = v);
        },
      ),
    );
  }

  Widget _reasonField() {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.06),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: _petAccent.withOpacity(0.25),
          width: 1,
        ),
      ),
      child: TextField(
        controller: _reasonCtrl,
        maxLines: 4,
        minLines: 3,
        maxLength: 500,
        textCapitalization: TextCapitalization.sentences,
        style: const TextStyle(
          color: Colors.white,
          fontSize: 14.5,
          fontWeight: FontWeight.w500,
          height: 1.4,
        ),
        cursorColor: _petAccent,
        decoration: InputDecoration(
          hintText: 'What was going on with your pet and what did the vet do?',
          hintStyle: TextStyle(
            color: Colors.white.withOpacity(0.3),
            fontSize: 14,
            fontWeight: FontWeight.w500,
          ),
          border: InputBorder.none,
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          counterStyle: TextStyle(
            color: Colors.white.withOpacity(0.3),
            fontSize: 10.5,
          ),
        ),
        onChanged: (v) {
          setState(() => _draft.reason = v);
        },
      ),
    );
  }

  // ─────────────────────────────────────────────────────────────────────
  // STEP 5: CORRESPONDENCES (optional additional docs)
  // ─────────────────────────────────────────────────────────────────────

  Widget _buildCorrespondencesStep() {
    return Column(
      children: [
        Expanded(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
            children: [
              const SizedBox(height: 4),
              const Text(
                'Additional documents',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 20,
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.4,
                  height: 1.2,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                "Optional. Add lab results, follow-up invoices, or any other supporting docs.",
                style: TextStyle(
                  color: Colors.white.withOpacity(0.55),
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                  height: 1.35,
                ),
              ),
              const SizedBox(height: 18),
              if (_draft.correspondences.isEmpty)
                _buildCorrespondenceEmptyState()
              else
                ..._draft.correspondences.map(_buildCorrespondenceCard),
              const SizedBox(height: 12),
              _secondaryButton(
                label:
                    _uploadingCorrespondence ? 'Uploading…' : 'Add a Document',
                icon: Icons.add_rounded,
                onTap:
                    _uploadingCorrespondence ? () {} : _promptAddCorrespondence,
              ),
            ],
          ),
        ),
        Container(
          padding: EdgeInsets.fromLTRB(
            16,
            10,
            16,
            MediaQuery.of(context).padding.bottom > 0 ? 8 : 16,
          ),
          decoration: BoxDecoration(
            border: Border(
              top: BorderSide(
                color: Colors.white.withOpacity(0.06),
                width: 1,
              ),
            ),
          ),
          child: Column(
            children: [
              _primaryButton(
                label: 'Continue to Review',
                icon: Icons.arrow_forward_rounded,
                onTap: () => _advanceFlow(_FlowStep.review),
              ),
              const SizedBox(height: 8),
              _secondaryButton(
                label: 'Back',
                icon: Icons.arrow_back_rounded,
                onTap: _backFlow,
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildCorrespondenceEmptyState() {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.04),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: Colors.white.withOpacity(0.08),
          width: 0.8,
        ),
      ),
      child: Column(
        children: [
          Icon(Icons.folder_open_rounded,
              color: Colors.white.withOpacity(0.35), size: 28),
          const SizedBox(height: 10),
          Text(
            'No extra documents',
            style: TextStyle(
              color: Colors.white.withOpacity(0.85),
              fontSize: 13.5,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'The main receipt is enough for most claims. You can skip this step.',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white.withOpacity(0.55),
              fontSize: 12,
              fontWeight: FontWeight.w500,
              height: 1.4,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCorrespondenceCard(_Correspondence c) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: _glassCard(
        bgOpacity: 0.06,
        borderOpacity: 0.12,
        borderWidth: 1,
        padding: const EdgeInsets.all(12),
        radius: 14,
        child: Row(
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: _petAccent.withOpacity(0.15),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(
                  color: _petAccent.withOpacity(0.3),
                  width: 0.8,
                ),
              ),
              child: const Icon(Icons.description_rounded,
                  color: _petAccent, size: 22),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    c.description.isNotEmpty ? c.description : 'Document',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 13.5,
                      fontWeight: FontWeight.w800,
                      letterSpacing: -0.2,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    c.type.replaceAll('_', ' '),
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.5),
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
            _PressableMaterial(
              child: InkWell(
                onTap: () => _removeCorrespondence(c.id),
                borderRadius: BorderRadius.circular(12),
                child: Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: _joviErrorRed.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.close_rounded,
                      color: _joviErrorRed, size: 16),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _promptAddCorrespondence() {
    HapticFeedback.lightImpact();
    String selectedType = 'follow_up_invoice';
    final descCtrl = TextEditingController();

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setSheetState) {
            return Container(
              padding: EdgeInsets.fromLTRB(
                16,
                12,
                16,
                MediaQuery.of(ctx).viewInsets.bottom + 20,
              ),
              decoration: BoxDecoration(
                color: _joviNavy.withOpacity(0.98),
                borderRadius:
                    const BorderRadius.vertical(top: Radius.circular(24)),
                border: Border.all(
                  color: Colors.white.withOpacity(0.1),
                  width: 1,
                ),
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
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
                  const Text(
                    'Add a Document',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 17,
                      fontWeight: FontWeight.w800,
                      letterSpacing: -0.3,
                    ),
                  ),
                  const SizedBox(height: 14),
                  _formFieldLabel('Type'),
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: [
                      _typeChip('follow_up_invoice', 'Follow-up invoice',
                          selectedType, (t) {
                        setSheetState(() => selectedType = t);
                      }),
                      _typeChip('lab_result', 'Lab result', selectedType, (t) {
                        setSheetState(() => selectedType = t);
                      }),
                      _typeChip(
                          'medical_record', 'Medical record', selectedType,
                          (t) {
                        setSheetState(() => selectedType = t);
                      }),
                      _typeChip('other', 'Other', selectedType, (t) {
                        setSheetState(() => selectedType = t);
                      }),
                    ],
                  ),
                  const SizedBox(height: 12),
                  _formFieldLabel('Brief description'),
                  Container(
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.06),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(
                        color: _petAccent.withOpacity(0.25),
                        width: 1,
                      ),
                    ),
                    child: TextField(
                      controller: descCtrl,
                      maxLength: 80,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                      ),
                      cursorColor: _petAccent,
                      decoration: InputDecoration(
                        hintText: 'e.g. Bloodwork from follow-up visit',
                        hintStyle: TextStyle(
                          color: Colors.white.withOpacity(0.3),
                          fontSize: 13,
                          fontWeight: FontWeight.w500,
                        ),
                        border: InputBorder.none,
                        contentPadding: const EdgeInsets.symmetric(
                            horizontal: 14, vertical: 12),
                        counterText: '',
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Expanded(
                        child: _secondaryButton(
                          label: 'Camera',
                          icon: Icons.camera_alt_rounded,
                          onTap: () {
                            Navigator.pop(ctx);
                            _pickAndAddCorrespondence(
                              source: ImageSource.camera,
                              type: selectedType,
                              description: descCtrl.text.trim().isEmpty
                                  ? _labelForType(selectedType)
                                  : descCtrl.text.trim(),
                            );
                          },
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _primaryButton(
                          label: 'Library',
                          icon: Icons.photo_library_rounded,
                          onTap: () {
                            Navigator.pop(ctx);
                            _pickAndAddCorrespondence(
                              source: ImageSource.gallery,
                              type: selectedType,
                              description: descCtrl.text.trim().isEmpty
                                  ? _labelForType(selectedType)
                                  : descCtrl.text.trim(),
                            );
                          },
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  String _labelForType(String t) {
    if (t == 'follow_up_invoice') return 'Follow-up invoice';
    if (t == 'lab_result') return 'Lab result';
    if (t == 'medical_record') return 'Medical record';
    return 'Other document';
  }

  Widget _typeChip(
      String type, String label, String selected, void Function(String) onTap) {
    final isSelected = type == selected;
    return _PressableMaterial(
      child: InkWell(
        onTap: () => onTap(type),
        borderRadius: BorderRadius.circular(11),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
          decoration: BoxDecoration(
            color: isSelected
                ? _petAccent.withOpacity(0.22)
                : Colors.white.withOpacity(0.05),
            borderRadius: BorderRadius.circular(11),
            border: Border.all(
              color: isSelected
                  ? _petAccent.withOpacity(0.4)
                  : Colors.white.withOpacity(0.12),
              width: 0.8,
            ),
          ),
          child: Text(
            label,
            style: TextStyle(
              color: isSelected ? Colors.white : Colors.white.withOpacity(0.65),
              fontSize: 12,
              fontWeight: FontWeight.w700,
              letterSpacing: -0.2,
            ),
          ),
        ),
      ),
    );
  }

  // ─────────────────────────────────────────────────────────────────────
  // STEP 6: REVIEW
  // ─────────────────────────────────────────────────────────────────────

  Widget _buildReviewStep() {
    return Column(
      children: [
        Expanded(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
            children: [
              const SizedBox(height: 4),
              const Text(
                'Review your claim',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 20,
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.4,
                  height: 1.2,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                'One last look before you send it to our team.',
                style: TextStyle(
                  color: Colors.white.withOpacity(0.55),
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                  height: 1.35,
                ),
              ),
              const SizedBox(height: 18),

              // Pet summary
              _reviewSection(
                title: 'Pet',
                onEdit: () => _advanceFlow(_FlowStep.petPicker),
                child: Row(
                  children: [
                    _petAvatar(_draft.pet, size: 40),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            _draft.pet?.name ?? '—',
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 15,
                              fontWeight: FontWeight.w800,
                              letterSpacing: -0.2,
                            ),
                          ),
                          if (_draft.pet != null)
                            Text(
                              _petSubtitle(_draft.pet!),
                              style: TextStyle(
                                color: Colors.white.withOpacity(0.6),
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

              // Bill details
              _reviewSection(
                title: 'Bill',
                onEdit: () => _advanceFlow(_FlowStep.details),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _reviewDetailRow('Total', _formatUsd(_draft.amount)),
                    _reviewDetailRow('Date of visit',
                        _formatShortDate(_draft.dateOfService)),
                    _reviewDetailRow('Clinic', _draft.providerClinic),
                    const SizedBox(height: 8),
                    Text(
                      _draft.reason,
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.75),
                        fontSize: 13,
                        fontWeight: FontWeight.w500,
                        height: 1.45,
                        fontStyle: FontStyle.italic,
                      ),
                    ),
                  ],
                ),
              ),

              // Receipt
              _reviewSection(
                title: 'Receipt',
                onEdit: () => _advanceFlow(_FlowStep.receipt),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(11),
                  child: SizedBox(
                    height: 140,
                    width: double.infinity,
                    child: _receiptPreviewImage(),
                  ),
                ),
              ),

              // Additional docs
              if (_draft.correspondences.isNotEmpty)
                _reviewSection(
                  title:
                      'Additional documents (${_draft.correspondences.length})',
                  onEdit: () => _advanceFlow(_FlowStep.correspondences),
                  child: Column(
                    children: _draft.correspondences
                        .map((c) => Padding(
                              padding: const EdgeInsets.only(bottom: 6),
                              child: Row(
                                children: [
                                  const Icon(Icons.description_rounded,
                                      color: _petAccent, size: 14),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      c.description.isNotEmpty
                                          ? c.description
                                          : _labelForType(c.type),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(
                                        color: Colors.white,
                                        fontSize: 13,
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ))
                        .toList(),
                  ),
                ),

              // Reimbursement estimate card
              const SizedBox(height: 4),
              Container(
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      _joviMint.withOpacity(0.18),
                      _joviMint.withOpacity(0.06),
                    ],
                  ),
                  borderRadius: BorderRadius.circular(18),
                  border: Border.all(
                    color: _joviMint.withOpacity(0.4),
                    width: 1.2,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: _joviMint.withOpacity(0.2),
                      blurRadius: 18,
                      offset: const Offset(0, 6),
                    ),
                  ],
                ),
                child: Column(
                  children: [
                    Row(
                      children: [
                        Container(
                          width: 40,
                          height: 40,
                          decoration: BoxDecoration(
                            color: _joviMint.withOpacity(0.2),
                            borderRadius: BorderRadius.circular(11),
                            border: Border.all(
                              color: _joviMint.withOpacity(0.4),
                              width: 1,
                            ),
                          ),
                          child: const Icon(Icons.payments_rounded,
                              color: _joviMint, size: 20),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                'Estimated reimbursement',
                                style: TextStyle(
                                  color: _joviMint.withOpacity(0.9),
                                  fontSize: 12,
                                  fontWeight: FontWeight.w600,
                                  letterSpacing: -0.1,
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                _formatUsd(_draft.estimatedReimbursement),
                                style: const TextStyle(
                                  color: _joviMint,
                                  fontSize: 24,
                                  fontWeight: FontWeight.w700,
                                  letterSpacing: -0.6,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Text(
                      '$_jovReimbursementRateLabel of ${_formatUsd(_draft.amount)}. Final amount confirmed during review.',
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.65),
                        fontSize: 11.5,
                        fontWeight: FontWeight.w600,
                        height: 1.4,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        Container(
          padding: EdgeInsets.fromLTRB(
            16,
            10,
            16,
            MediaQuery.of(context).padding.bottom > 0 ? 8 : 16,
          ),
          decoration: BoxDecoration(
            border: Border(
              top: BorderSide(
                color: Colors.white.withOpacity(0.06),
                width: 1,
              ),
            ),
          ),
          child: Column(
            children: [
              _primaryButton(
                label: _submitting ? 'Submitting…' : 'Submit Claim',
                icon: Icons.check_rounded,
                onTap: _submitting ? null : _submitClaim,
                loading: _submitting,
              ),
              const SizedBox(height: 8),
              _secondaryButton(
                label: 'Back',
                icon: Icons.arrow_back_rounded,
                onTap: _submitting ? () {} : _backFlow,
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _reviewSection({
    required String title,
    required Widget child,
    VoidCallback? onEdit,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: _glassCard(
        bgOpacity: 0.06,
        borderOpacity: 0.12,
        borderWidth: 1,
        padding: const EdgeInsets.all(14),
        radius: 16,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    title,
                    style: TextStyle(
                      color: _petAccent.withOpacity(0.9),
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      letterSpacing: -0.1,
                    ),
                  ),
                ),
                if (onEdit != null)
                  _PressableMaterial(
                    child: InkWell(
                      onTap: onEdit,
                      borderRadius: BorderRadius.circular(8),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 4),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              'Edit',
                              style: TextStyle(
                                color: _petAccent.withOpacity(0.9),
                                fontSize: 11.5,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                            const SizedBox(width: 2),
                            Icon(Icons.edit_rounded,
                                color: _petAccent.withOpacity(0.9), size: 12),
                          ],
                        ),
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 10),
            child,
          ],
        ),
      ),
    );
  }

  Widget _reviewDetailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          SizedBox(
            width: 110,
            child: Text(
              label,
              style: TextStyle(
                color: Colors.white.withOpacity(0.5),
                fontSize: 12,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.1,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value.isEmpty ? '—' : value,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 13.5,
                fontWeight: FontWeight.w700,
                height: 1.3,
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ─────────────────────────────────────────────────────────────────────
  // STEP 7: SUBMITTED (success screen)
  // ─────────────────────────────────────────────────────────────────────

  Widget _buildSubmittedStep() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 16, 24, 20),
      child: Column(
        children: [
          const Spacer(),
          Container(
            width: 96,
            height: 96,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [_joviMint, _joviMintDark],
              ),
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: _joviMint.withOpacity(0.5),
                  blurRadius: 30,
                  offset: const Offset(0, 10),
                ),
              ],
            ),
            child: const Icon(
              Icons.check_rounded,
              color: Colors.white,
              size: 52,
            ),
          ),
          const SizedBox(height: 22),
          const Text(
            'Claim submitted',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white,
              fontSize: 26,
              fontWeight: FontWeight.w700,
              letterSpacing: -0.6,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            "We'll review your claim and let you know within 3–5 business days. You can track the status anytime in the My Claims tab.",
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white.withOpacity(0.65),
              fontSize: 14,
              fontWeight: FontWeight.w500,
              height: 1.45,
            ),
          ),
          const SizedBox(height: 22),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: _joviMint.withOpacity(0.1),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                color: _joviMint.withOpacity(0.3),
                width: 1,
              ),
            ),
            child: Column(
              children: [
                Text(
                  "You'll get back",
                  style: TextStyle(
                    color: _joviMint.withOpacity(0.9),
                    fontSize: 12.5,
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.1,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  _formatUsd(_draft.estimatedReimbursement),
                  style: const TextStyle(
                    color: _joviMint,
                    fontSize: 32,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.8,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  'estimated (final amount confirmed during review)',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.55),
                    fontSize: 11.5,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
          if (_submittedClaimId != null) ...[
            const SizedBox(height: 14),
            Text(
              'Reference: ${_submittedClaimId!.substring(0, _submittedClaimId!.length > 8 ? 8 : _submittedClaimId!.length).toUpperCase()}',
              style: TextStyle(
                color: Colors.white.withOpacity(0.35),
                fontSize: 11,
                fontWeight: FontWeight.w700,
                letterSpacing: 1,
              ),
            ),
          ],
          const Spacer(),
          _primaryButton(
            label: 'View My Claims',
            icon: Icons.receipt_long_rounded,
            onTap: () {
              HapticFeedback.lightImpact();
              _resetDraft();
              setState(() => _currentTab = _Tab.myClaims);
              _replayFade();
            },
          ),
          const SizedBox(height: 8),
          _secondaryButton(
            label: 'Submit Another Claim',
            icon: Icons.add_rounded,
            onTap: _resetDraft,
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // MY CLAIMS TAB
  // ═══════════════════════════════════════════════════════════════════════

  Widget _buildMyClaimsView() {
    if (_petsLoading || _claimsInitialLoad) {
      return const Center(
        child: SizedBox(
          width: 28,
          height: 28,
          child: CircularProgressIndicator(
            strokeWidth: 2.5,
            valueColor: AlwaysStoppedAnimation<Color>(_petAccent),
          ),
        ),
      );
    }
    if (_pets.isEmpty) {
      return _buildNoPetEmptyState(
        title: 'No pet yet',
        body:
            'Add a pet from your account to start submitting claims for their vet bills.',
      );
    }

    final claims = _allClaimsFlat;
    final anyError = _claimsErrors.values.any((e) => e != null);

    if (claims.isEmpty) {
      return Column(
        children: [
          if (anyError) _claimErrorsBanner(),
          Expanded(child: _buildClaimsEmptyState()),
        ],
      );
    }

    return Column(
      children: [
        if (anyError) _claimErrorsBanner(),
        _buildClaimsStatsRow(claims),
        Expanded(
          child: ListView.separated(
            padding: const EdgeInsets.fromLTRB(14, 6, 14, 24),
            itemCount: claims.length,
            separatorBuilder: (_, __) => const SizedBox(height: 10),
            itemBuilder: (ctx, i) => _buildClaimCard(claims[i]),
          ),
        ),
      ],
    );
  }

  Widget _claimErrorsBanner() {
    final msgs = _claimsErrors.values.where((e) => e != null).toSet();
    final message = msgs.first ?? 'Some claims may not be showing.';
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 4, 14, 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: _joviErrorRed.withOpacity(0.1),
        borderRadius: BorderRadius.circular(11),
        border: Border.all(
          color: _joviErrorRed.withOpacity(0.3),
          width: 0.8,
        ),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline_rounded,
              color: _joviErrorRed, size: 16),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message!,
              style: TextStyle(
                color: Colors.white.withOpacity(0.85),
                fontSize: 12,
                fontWeight: FontWeight.w600,
                height: 1.3,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildClaimsEmptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
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
              child: Icon(
                Icons.receipt_long_outlined,
                color: Colors.white.withOpacity(0.4),
                size: 32,
              ),
            ),
            const SizedBox(height: 18),
            const Text(
              'No claims yet',
              style: TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.w800,
                color: Colors.white,
                letterSpacing: -0.3,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'When you submit a claim, it\'ll show up here so you can track its status.',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 13,
                color: Colors.white.withOpacity(0.55),
                fontWeight: FontWeight.w500,
                height: 1.35,
              ),
            ),
            const SizedBox(height: 20),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: _primaryButton(
                label: 'Start a New Claim',
                icon: Icons.add_rounded,
                onTap: () {
                  HapticFeedback.lightImpact();
                  _resetDraft();
                  setState(() => _currentTab = _Tab.newClaim);
                  _replayFade();
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildClaimsStatsRow(List<_PetClaim> claims) {
    double totalRequested = 0;
    double totalPaidOrEstimated = 0;
    int pending = 0;
    int approved = 0;
    int paid = 0;
    for (final c in claims) {
      totalRequested += c.amount;
      if (c.status == _ClaimStatus.paid) {
        paid++;
        totalPaidOrEstimated += c.displayReimbursement;
      } else if (c.status == _ClaimStatus.approved) {
        approved++;
        totalPaidOrEstimated += c.displayReimbursement;
      } else if (c.status == _ClaimStatus.submitted ||
          c.status == _ClaimStatus.underReview ||
          c.status == _ClaimStatus.needsMoreInfo) {
        pending++;
      }
    }
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 4, 14, 6),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.04),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: Colors.white.withOpacity(0.09),
          width: 0.8,
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: _statCell(
              label: 'Reimbursed',
              value: _formatUsd(totalPaidOrEstimated),
              accent: _joviMint,
              icon: Icons.payments_rounded,
            ),
          ),
          Container(
            width: 1,
            height: 34,
            color: Colors.white.withOpacity(0.08),
          ),
          Expanded(
            child: _statCell(
              label: 'Pending',
              value: '$pending',
              accent: _joviGold,
              icon: Icons.hourglass_bottom_rounded,
            ),
          ),
          Container(
            width: 1,
            height: 34,
            color: Colors.white.withOpacity(0.08),
          ),
          Expanded(
            child: _statCell(
              label: 'Claims',
              value: '${claims.length}',
              accent: _petAccent,
              icon: Icons.receipt_long_rounded,
            ),
          ),
        ],
      ),
    );
  }

  Widget _statCell({
    required String label,
    required String value,
    required Color accent,
    required IconData icon,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, color: accent.withOpacity(0.85), size: 11),
              const SizedBox(width: 3),
              Text(
                label,
                style: TextStyle(
                  color: accent.withOpacity(0.9),
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  letterSpacing: -0.1,
                ),
              ),
            ],
          ),
          const SizedBox(height: 3),
          Text(
            value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 15,
              fontWeight: FontWeight.w700,
              letterSpacing: -0.3,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildClaimCard(_PetClaim claim) {
    final sColor = _statusColor(claim.status);
    final sIcon = _statusIcon(claim.status);
    final sLabel = _statusLabel(claim.status);
    final submitted = claim.submittedAt ?? claim.updatedAt;
    return _PressableMaterial(
      child: InkWell(
        onTap: () => _showClaimDetail(claim),
        borderRadius: BorderRadius.circular(16),
        child: _glassCard(
          bgOpacity: 0.06,
          borderOpacity: 0.12,
          borderWidth: 1,
          padding: const EdgeInsets.all(14),
          radius: 16,
          borderTint: sColor,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                children: [
                  Container(
                    width: 42,
                    height: 42,
                    decoration: BoxDecoration(
                      color: sColor.withOpacity(0.16),
                      borderRadius: BorderRadius.circular(11),
                      border: Border.all(
                        color: sColor.withOpacity(0.35),
                        width: 1,
                      ),
                    ),
                    child: Icon(sIcon, color: sColor, size: 20),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          claim.providerClinic.isNotEmpty
                              ? claim.providerClinic
                              : 'Vet visit',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 14.5,
                            fontWeight: FontWeight.w800,
                            letterSpacing: -0.2,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Row(
                          children: [
                            Icon(Icons.pets_rounded,
                                size: 11, color: Colors.white.withOpacity(0.5)),
                            const SizedBox(width: 4),
                            Flexible(
                              child: Text(
                                claim.petName,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(
                                  color: Colors.white.withOpacity(0.6),
                                  fontSize: 11.5,
                                  fontWeight: FontWeight.w600,
                                ),
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
                            Icon(Icons.schedule_rounded,
                                size: 11, color: Colors.white.withOpacity(0.5)),
                            const SizedBox(width: 4),
                            Flexible(
                              child: Text(
                                submitted != null
                                    ? _formatRelative(submitted)
                                    : _formatShortDate(claim.dateOfService),
                                style: TextStyle(
                                  color: Colors.white.withOpacity(0.55),
                                  fontSize: 11.5,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  Icon(Icons.chevron_right_rounded,
                      color: Colors.white.withOpacity(0.4), size: 20),
                ],
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  _pill(
                    text: sLabel,
                    color: sColor,
                    icon: sIcon,
                    iconSize: 11,
                  ),
                  const Spacer(),
                  Text(
                    _formatUsd(claim.amount),
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.5),
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(width: 4),
                  Icon(Icons.arrow_forward_rounded,
                      color: Colors.white.withOpacity(0.35), size: 12),
                  const SizedBox(width: 4),
                  Text(
                    _formatUsd(claim.displayReimbursement),
                    style: TextStyle(
                      color: _reimbursementColorFor(claim.status),
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      letterSpacing: -0.2,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Color _reimbursementColorFor(_ClaimStatus s) {
    if (s == _ClaimStatus.paid) return _joviMint;
    if (s == _ClaimStatus.approved) return _joviMint;
    if (s == _ClaimStatus.rejected) {
      return Colors.white.withOpacity(0.4);
    }
    return Colors.white.withOpacity(0.85);
  }

  // ═══════════════════════════════════════════════════════════════════════
  // CLAIM DETAIL SHEET
  // ═══════════════════════════════════════════════════════════════════════

  void _showClaimDetail(_PetClaim claim) {
    HapticFeedback.lightImpact();
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => DraggableScrollableSheet(
        initialChildSize: 0.88,
        maxChildSize: 0.95,
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
                border: Border.all(
                  color: Colors.white.withOpacity(0.1),
                  width: 1,
                ),
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
                  _buildClaimDetailHeader(ctx, claim),
                  // Body
                  Expanded(
                    child: ListView(
                      controller: scrollCtrl,
                      padding: const EdgeInsets.fromLTRB(16, 4, 16, 20),
                      children: [
                        _claimDetailReimbursementCard(claim),
                        const SizedBox(height: 14),
                        if (claim.status == _ClaimStatus.rejected &&
                            claim.rejectionReason != null &&
                            claim.rejectionReason!.isNotEmpty)
                          _claimDetailRejectionCard(claim),
                        if (claim.status == _ClaimStatus.needsMoreInfo)
                          _claimDetailNeedsInfoCard(claim),
                        _claimDetailSection(
                          title: 'Bill details',
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              _claimDetailRow(
                                  'Total', _formatUsd(claim.amount)),
                              _claimDetailRow('Date of visit',
                                  _formatShortDate(claim.dateOfService)),
                              _claimDetailRow('Clinic', claim.providerClinic),
                              _claimDetailRow('Pet',
                                  '${claim.petName} (${_petTypeSerialize(claim.petType)})'),
                              const SizedBox(height: 8),
                              Text(
                                claim.reason,
                                style: TextStyle(
                                  color: Colors.white.withOpacity(0.85),
                                  fontSize: 13,
                                  fontWeight: FontWeight.w500,
                                  height: 1.45,
                                  fontStyle: FontStyle.italic,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 14),
                        if (claim.photoUrl != null &&
                            claim.photoUrl!.isNotEmpty)
                          _claimDetailSection(
                            title: 'Receipt',
                            child: ClipRRect(
                              borderRadius: BorderRadius.circular(11),
                              child: Image.network(
                                claim.photoUrl!,
                                fit: BoxFit.cover,
                                width: double.infinity,
                                errorBuilder: (_, __, ___) =>
                                    _receiptPreviewPlaceholder(),
                              ),
                            ),
                          ),
                        if (claim.correspondences.isNotEmpty) ...[
                          const SizedBox(height: 14),
                          _claimDetailSection(
                            title:
                                'Additional documents (${claim.correspondences.length})',
                            child: Column(
                              children: claim.correspondences
                                  .map((c) => Padding(
                                        padding:
                                            const EdgeInsets.only(bottom: 8),
                                        child: _correspondenceViewRow(c),
                                      ))
                                  .toList(),
                            ),
                          ),
                        ],
                        const SizedBox(height: 14),
                        _claimDetailSection(
                          title: 'Submission',
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              if (claim.submittedAt != null)
                                _claimDetailRow('Submitted',
                                    '${_formatShortDate(claim.submittedAt!)} · ${DateFormat.jm().format(claim.submittedAt!)}'),
                              if (claim.updatedAt != null &&
                                  claim.submittedAt != claim.updatedAt)
                                _claimDetailRow('Last updated',
                                    '${_formatShortDate(claim.updatedAt!)} · ${DateFormat.jm().format(claim.updatedAt!)}'),
                              _claimDetailRow(
                                  'Reference',
                                  claim.id
                                      .substring(
                                          0,
                                          claim.id.length > 8
                                              ? 8
                                              : claim.id.length)
                                      .toUpperCase()),
                              _claimDetailRow(
                                  'Exclusions acknowledged',
                                  claim.memberAcknowledgedExclusions
                                      ? 'Yes'
                                      : 'No'),
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
    );
  }

  Widget _buildClaimDetailHeader(BuildContext ctx, _PetClaim claim) {
    final sColor = _statusColor(claim.status);
    final sIcon = _statusIcon(claim.status);
    final sLabel = _statusLabel(claim.status);
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 12, 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: sColor.withOpacity(0.16),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: sColor.withOpacity(0.4),
                width: 1,
              ),
            ),
            child: Icon(sIcon, color: sColor, size: 22),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  claim.providerClinic.isNotEmpty
                      ? claim.providerClinic
                      : 'Vet visit',
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.4,
                    height: 1.2,
                  ),
                ),
                const SizedBox(height: 3),
                Row(
                  children: [
                    _pill(
                      text: sLabel,
                      color: sColor,
                      icon: sIcon,
                      iconSize: 10,
                    ),
                    const SizedBox(width: 6),
                    Flexible(
                      child: Text(
                        _formatShortDate(claim.dateOfService),
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.55),
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          _PressableMaterial(
            child: InkWell(
              onTap: () => Navigator.pop(ctx),
              borderRadius: BorderRadius.circular(12),
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(Icons.close, color: Colors.white, size: 18),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _claimDetailReimbursementCard(_PetClaim claim) {
    final isFinal = claim.status == _ClaimStatus.paid ||
        claim.status == _ClaimStatus.approved ||
        claim.status == _ClaimStatus.rejected;
    final accent =
        claim.status == _ClaimStatus.rejected ? _joviErrorRed : _joviMint;
    final amount = claim.status == _ClaimStatus.rejected
        ? 0.0
        : claim.displayReimbursement;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            accent.withOpacity(0.18),
            accent.withOpacity(0.06),
          ],
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: accent.withOpacity(0.4),
          width: 1.2,
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: accent.withOpacity(0.2),
              borderRadius: BorderRadius.circular(11),
              border: Border.all(
                color: accent.withOpacity(0.4),
                width: 1,
              ),
            ),
            child: Icon(
              claim.status == _ClaimStatus.rejected
                  ? Icons.cancel_rounded
                  : Icons.payments_rounded,
              color: accent,
              size: 22,
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  isFinal ? 'Reimbursement' : 'Estimated reimbursement',
                  style: TextStyle(
                    color: accent.withOpacity(0.9),
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.1,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  _formatUsd(amount),
                  style: TextStyle(
                    color: accent,
                    fontSize: 24,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.6,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  claim.status == _ClaimStatus.rejected
                      ? 'This claim was not covered'
                      : isFinal
                          ? '$_jovReimbursementRateLabel of ${_formatUsd(claim.amount)}'
                          : 'Pending review — $_jovReimbursementRateLabel of ${_formatUsd(claim.amount)}',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.65),
                    fontSize: 11.5,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _claimDetailRejectionCard(_PetClaim claim) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: _joviErrorRed.withOpacity(0.1),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: _joviErrorRed.withOpacity(0.3),
            width: 1,
          ),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(Icons.info_outline_rounded,
                color: _joviErrorRed, size: 18),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    'Why this wasn\'t covered',
                    style: TextStyle(
                      color: _joviErrorRed,
                      fontSize: 11.5,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.8,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    claim.rejectionReason!,
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.85),
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                      height: 1.4,
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

  Widget _claimDetailNeedsInfoCard(_PetClaim claim) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: _joviCoral.withOpacity(0.1),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: _joviCoral.withOpacity(0.3),
            width: 1,
          ),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(Icons.info_rounded, color: _joviCoral, size: 18),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    'We need a bit more from you',
                    style: TextStyle(
                      color: _joviCoral,
                      fontSize: 11.5,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.8,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    claim.rejectionReason ??
                        "Our review team has requested more information. We'll reach out by email.",
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.85),
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                      height: 1.4,
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

  Widget _claimDetailSection({
    required String title,
    required Widget child,
  }) {
    return _glassCard(
      bgOpacity: 0.06,
      borderOpacity: 0.12,
      borderWidth: 1,
      padding: const EdgeInsets.all(14),
      radius: 16,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            title,
            style: TextStyle(
              color: _petAccent.withOpacity(0.9),
              fontSize: 13,
              fontWeight: FontWeight.w600,
              letterSpacing: -0.1,
            ),
          ),
          const SizedBox(height: 10),
          child,
        ],
      ),
    );
  }

  Widget _claimDetailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 110,
            child: Text(
              label,
              style: TextStyle(
                color: Colors.white.withOpacity(0.5),
                fontSize: 11.5,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.1,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value.isEmpty ? '—' : value,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 13,
                fontWeight: FontWeight.w700,
                height: 1.3,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _correspondenceViewRow(_Correspondence c) {
    return _PressableMaterial(
      child: InkWell(
        onTap: () => _openCorrespondenceUrl(c.url),
        borderRadius: BorderRadius.circular(11),
        child: Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.05),
            borderRadius: BorderRadius.circular(11),
            border: Border.all(
              color: Colors.white.withOpacity(0.1),
              width: 0.8,
            ),
          ),
          child: Row(
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: _petAccent.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(9),
                  border: Border.all(
                    color: _petAccent.withOpacity(0.3),
                    width: 0.8,
                  ),
                ),
                child: const Icon(Icons.description_rounded,
                    color: _petAccent, size: 18),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      c.description.isNotEmpty
                          ? c.description
                          : _labelForType(c.type),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        letterSpacing: -0.2,
                      ),
                    ),
                    const SizedBox(height: 1),
                    Text(
                      c.type.replaceAll('_', ' '),
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.5),
                        fontSize: 10.5,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
              Icon(Icons.open_in_new_rounded,
                  color: Colors.white.withOpacity(0.5), size: 16),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _openCorrespondenceUrl(String url) async {
    if (url.isEmpty) return;
    HapticFeedback.lightImpact();
    try {
      final uri = Uri.parse(url);
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } catch (e) {
      debugPrint('FilePetClaim: failed to open correspondence url: $e');
      if (!mounted) return;
      _showSnackBar("Couldn't open that document.", isError: true);
    }
  }
}

// ─── Storage bucket (shared with human FileClaim) ──────────────────────────
const String _storageBucket = 'gs://kurv-health.firebasestorage.app';

// ─── Jovi Brand Color System ───────────────────────────────────────────────
const Color _joviCoral = Color(0xFFFF6B4A);
const Color _joviCoralLight = Color(0xFFFF8F73);
const Color _joviCoralDark = Color(0xFFE5583A);
const Color _joviNavy = Color(0xFF1A2744);
const Color _joviNavyDark = Color(0xFF0F1A2E);
const Color _joviNavyMid = Color(0xFF1F2B47);
const Color _joviMint = Color(0xFF00D4AA);
const Color _joviMintDark = Color(0xFF00B894);
const Color _joviGold = Color(0xFFFFD166);
const Color _joviGoldDark = Color(0xFFE6B84D);
const Color _joviErrorRed = Color(0xFFE53935);

// ─── Pet Accent System ─────────────────────────────────────────────────────
const Color _petAccent = Color(0xFFA78BFA);
const Color _petAccentDark = Color(0xFF8B6EE8);

// ─── Coverage Constants (single source of truth) ───────────────────────────
/// Percentage of an eligible claim Jovi reimburses to the member.
const double _jovReimbursementRate = 0.90;

/// Human-readable display version of the rate.
const String _jovReimbursementRateLabel = '90%';

// ═══════════════════════════════════════════════════════════════════════════
// ENUMS
// ═══════════════════════════════════════════════════════════════════════════

enum PetType { dog, cat, other }

PetType _petTypeParse(String? s) {
  if (s == null) return PetType.other;
  final lower = s.toLowerCase().trim();
  if (lower == 'dog') return PetType.dog;
  if (lower == 'cat') return PetType.cat;
  return PetType.other;
}

String _petTypeSerialize(PetType t) {
  if (t == PetType.dog) return 'dog';
  if (t == PetType.cat) return 'cat';
  return 'other';
}

/// Claim lifecycle. Member writes go up to 'submitted'; Jovi staff move
/// claims through the rest of the pipeline via admin tooling.
enum _ClaimStatus {
  draft, // unfinished, not submitted
  submitted, // member has submitted, awaiting Jovi review
  underReview, // Jovi review in progress
  needsMoreInfo, // Jovi has asked for more correspondence
  approved, // approved, payout pending
  paid, // reimbursement issued
  rejected, // claim denied
}

String _statusSerialize(_ClaimStatus s) {
  if (s == _ClaimStatus.draft) return 'draft';
  if (s == _ClaimStatus.submitted) return 'submitted';
  if (s == _ClaimStatus.underReview) return 'under_review';
  if (s == _ClaimStatus.needsMoreInfo) return 'needs_more_info';
  if (s == _ClaimStatus.approved) return 'approved';
  if (s == _ClaimStatus.paid) return 'paid';
  return 'rejected';
}

_ClaimStatus _statusParse(String? s) {
  if (s == null) return _ClaimStatus.draft;
  final lower = s.toLowerCase().replaceAll(' ', '_');
  if (lower == 'draft') return _ClaimStatus.draft;
  if (lower == 'submitted' || lower == 'pending') {
    return _ClaimStatus.submitted;
  }
  if (lower == 'under_review' || lower == 'processing') {
    return _ClaimStatus.underReview;
  }
  if (lower == 'needs_more_info') return _ClaimStatus.needsMoreInfo;
  if (lower == 'approved') return _ClaimStatus.approved;
  if (lower == 'paid') return _ClaimStatus.paid;
  if (lower == 'rejected' || lower == 'denied') {
    return _ClaimStatus.rejected;
  }
  return _ClaimStatus.submitted;
}

String _statusLabel(_ClaimStatus s) {
  if (s == _ClaimStatus.draft) return 'Draft';
  if (s == _ClaimStatus.submitted) return 'Submitted';
  if (s == _ClaimStatus.underReview) return 'Under review';
  if (s == _ClaimStatus.needsMoreInfo) return 'Needs more info';
  if (s == _ClaimStatus.approved) return 'Approved';
  if (s == _ClaimStatus.paid) return 'Paid';
  return 'Rejected';
}

Color _statusColor(_ClaimStatus s) {
  if (s == _ClaimStatus.draft) {
    return const Color.fromARGB(255, 180, 180, 200);
  }
  if (s == _ClaimStatus.submitted) return _joviGold;
  if (s == _ClaimStatus.underReview) return _petAccent;
  if (s == _ClaimStatus.needsMoreInfo) return _joviCoral;
  if (s == _ClaimStatus.approved) return _joviMint;
  if (s == _ClaimStatus.paid) return _joviMintDark;
  return _joviErrorRed;
}

IconData _statusIcon(_ClaimStatus s) {
  if (s == _ClaimStatus.draft) return Icons.edit_note_rounded;
  if (s == _ClaimStatus.submitted) return Icons.send_rounded;
  if (s == _ClaimStatus.underReview) return Icons.hourglass_bottom_rounded;
  if (s == _ClaimStatus.needsMoreInfo) return Icons.info_rounded;
  if (s == _ClaimStatus.approved) return Icons.check_circle_rounded;
  if (s == _ClaimStatus.paid) return Icons.payments_rounded;
  return Icons.cancel_rounded;
}

/// Tabs in the main widget.
enum _Tab { newClaim, myClaims }

/// Flow step within the New Claim tab.
enum _FlowStep {
  petPicker, // Choose pet
  disclaimer, // Ineligibility disclaimer (must acknowledge)
  receipt, // Upload main receipt photo
  details, // Amount + date + clinic + reason
  correspondences, // Optional additional docs
  review, // Final review before submit
  submitted, // Success screen with claim id
}

int _flowStepIndex(_FlowStep s) {
  if (s == _FlowStep.petPicker) return 0;
  if (s == _FlowStep.disclaimer) return 1;
  if (s == _FlowStep.receipt) return 2;
  if (s == _FlowStep.details) return 3;
  if (s == _FlowStep.correspondences) return 4;
  if (s == _FlowStep.review) return 5;
  return 6; // submitted
}

/// Firestore error classification for friendly messages.
enum _LoadErrorKind { permission, network, unknown }

_LoadErrorKind _classifyError(dynamic e) {
  final msg = e.toString().toLowerCase();
  if (msg.contains('permission-denied') || msg.contains('unauthorized')) {
    return _LoadErrorKind.permission;
  }
  if (msg.contains('unavailable') ||
      msg.contains('network') ||
      msg.contains('socketexception') ||
      msg.contains('timeout')) {
    return _LoadErrorKind.network;
  }
  return _LoadErrorKind.unknown;
}

String _friendlyErrorMessage(_LoadErrorKind kind) {
  if (kind == _LoadErrorKind.permission) {
    return "We couldn't access this data. Please sign in again.";
  }
  if (kind == _LoadErrorKind.network) {
    return 'Network hiccup. Please try again in a moment.';
  }
  return 'Something went wrong.';
}

// ═══════════════════════════════════════════════════════════════════════════
// INELIGIBILITY CATALOG
// Per-pet coverage exclusions — these MUST be shown to the member before
// they submit a claim, and memberAcknowledgedExclusions MUST be written
// on the claim document as an audit trail.
//
// Any change to this list should also go through product/legal sign-off
// before launch, since it's the member-facing definition of what Jovi
// does and doesn't cover.
// ═══════════════════════════════════════════════════════════════════════════

class _Exclusion {
  final String title;
  final String description;
  final IconData icon;
  final Color accent;

  const _Exclusion({
    required this.title,
    required this.description,
    required this.icon,
    required this.accent,
  });
}

const List<_Exclusion> _petClaimExclusions = [
  _Exclusion(
    title: 'Vaccinations & immunizations',
    description:
        'Routine shots like rabies, DHPP, bordetella, and FVRCP aren\'t covered. These are considered preventive care.',
    icon: Icons.vaccines_rounded,
    accent: _joviMint,
  ),
  _Exclusion(
    title: 'Grooming & nail trims',
    description:
        'Baths, haircuts, nail trims, ear cleanings, and anal gland expressions done for hygiene rather than a medical condition.',
    icon: Icons.content_cut_rounded,
    accent: _joviGold,
  ),
  _Exclusion(
    title: 'Food, supplements & treats',
    description:
        'Prescription diets, over-the-counter vitamins, supplements, dental chews, and any food or treat purchases.',
    icon: Icons.restaurant_rounded,
    accent: _joviCoral,
  ),
  _Exclusion(
    title: 'Pre-existing conditions',
    description:
        'Any condition your pet had symptoms of or was treated for before their Jovi membership started. Be sure to disclose known conditions when you enroll.',
    icon: Icons.history_rounded,
    accent: _joviErrorRed,
  ),
  _Exclusion(
    title: 'Cosmetic & breeding costs',
    description:
        'Elective cosmetic procedures (ear cropping, tail docking, declawing) and anything related to breeding — stud fees, artificial insemination, C-sections by choice, and puppy/kitten care.',
    icon: Icons.pets_rounded,
    accent: _petAccent,
  ),
];

// ═══════════════════════════════════════════════════════════════════════════
// PET MODEL (matches schema used by Symptom Checker / Records / Meds)
// ═══════════════════════════════════════════════════════════════════════════

class _PetLite {
  final String petId;
  final String name;
  final PetType type;
  final String? breed;
  final String? photoUrl;
  final double? weightLbs;
  final DateTime? dateOfBirth;

  const _PetLite({
    required this.petId,
    required this.name,
    this.type = PetType.other,
    this.breed,
    this.photoUrl,
    this.weightLbs,
    this.dateOfBirth,
  });

  int? get ageYears {
    if (dateOfBirth == null) return null;
    final now = DateTime.now();
    int years = now.year - dateOfBirth!.year;
    if (now.month < dateOfBirth!.month ||
        (now.month == dateOfBirth!.month && now.day < dateOfBirth!.day)) {
      years--;
    }
    return years < 0 ? 0 : years;
  }

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

    double? asDouble(dynamic v) {
      if (v == null) return null;
      if (v is num) return v.toDouble();
      if (v is String) return double.tryParse(v);
      return null;
    }

    return _PetLite(
      petId: (m['petId'] as String?) ?? docId,
      name: (m['name'] as String?)?.trim().isNotEmpty == true
          ? (m['name'] as String).trim()
          : 'Unnamed pet',
      type: _petTypeParse(m['type'] as String?),
      breed: (m['breed'] as String?)?.trim(),
      photoUrl: (m['photoUrl'] as String?) ?? (m['photo_url'] as String?),
      weightLbs: asDouble(m['weightLbs'] ?? m['weight'] ?? m['weight_lbs']),
      dateOfBirth: parseTs(
          m['dateOfBirth'] ?? m['date_of_birth'] ?? m['dob'] ?? m['birthdate']),
    );
  }

  factory _PetLite.fromLegacyJson(Map<String, dynamic> m) {
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

    double? asDouble(dynamic v) {
      if (v == null) return null;
      if (v is num) return v.toDouble();
      if (v is String) return double.tryParse(v);
      return null;
    }

    return _PetLite(
      petId: (m['petId'] as String?) ?? (m['id'] as String?) ?? 'legacy',
      name: (m['name'] as String?)?.trim() ?? 'My pet',
      type: _petTypeParse(m['type'] as String?),
      breed: (m['breed'] as String?)?.trim(),
      photoUrl: (m['photo_url'] as String?) ?? (m['photoUrl'] as String?),
      weightLbs: asDouble(m['weightLbs'] ?? m['weight'] ?? m['weight_lbs']),
      dateOfBirth: parseTs(
          m['date_of_birth'] ?? m['dateOfBirth'] ?? m['dob'] ?? m['birthdate']),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// CLAIM MODELS
// ═══════════════════════════════════════════════════════════════════════════

class _Correspondence {
  final String id;
  final String url;
  final String description; // member-provided label
  final DateTime uploadedAt;
  final String type; // 'follow_up_invoice', 'lab_result', 'other', etc.

  const _Correspondence({
    required this.id,
    required this.url,
    required this.description,
    required this.uploadedAt,
    this.type = 'other',
  });

  Map<String, dynamic> toMap() => {
        'id': id,
        'url': url,
        'description': description,
        'uploadedAt': Timestamp.fromDate(uploadedAt),
        'type': type,
      };

  factory _Correspondence.fromMap(Map<String, dynamic> m) {
    DateTime ts = DateTime.now();
    final raw = m['uploadedAt'];
    if (raw is Timestamp) ts = raw.toDate();
    if (raw is String) ts = DateTime.tryParse(raw) ?? DateTime.now();
    return _Correspondence(
      id: (m['id'] as String?) ?? '',
      url: (m['url'] as String?) ?? '',
      description: (m['description'] as String?) ?? '',
      uploadedAt: ts,
      type: (m['type'] as String?) ?? 'other',
    );
  }
}

/// Full claim record. `estimatedReimbursement` is display-only; the final
/// amount Jovi actually pays out is recorded separately via admin tooling
/// and surfaced on the claim doc as `finalReimbursement` when set.
class _PetClaim {
  final String id;
  final String memberId;
  final String petId;
  final String petName;
  final PetType petType;
  final double amount; // total bill, member-entered
  final DateTime dateOfService;
  final String providerClinic; // vet clinic name
  final String reason; // free-text "what happened"
  final String? photoUrl; // main receipt
  final List<_Correspondence> correspondences;
  final _ClaimStatus status;
  final DateTime? submittedAt;
  final DateTime? updatedAt;
  final bool memberAcknowledgedExclusions;
  final DateTime? exclusionsAcknowledgedAt;
  final String? rejectionReason; // populated by Jovi staff on rejection
  final double? finalReimbursement; // populated by Jovi staff on approval

  const _PetClaim({
    required this.id,
    required this.memberId,
    required this.petId,
    required this.petName,
    this.petType = PetType.other,
    required this.amount,
    required this.dateOfService,
    required this.providerClinic,
    required this.reason,
    this.photoUrl,
    this.correspondences = const [],
    this.status = _ClaimStatus.submitted,
    this.submittedAt,
    this.updatedAt,
    this.memberAcknowledgedExclusions = false,
    this.exclusionsAcknowledgedAt,
    this.rejectionReason,
    this.finalReimbursement,
  });

  /// Display-only 90% estimate shown to the member. Final payout is
  /// `finalReimbursement` when Jovi has completed review.
  double get estimatedReimbursement =>
      (amount * _jovReimbursementRate * 100).round() / 100;

  /// The amount actually shown as reimbursement — prefer finalReimbursement
  /// when Jovi has set it; otherwise fall back to the estimate.
  double get displayReimbursement =>
      finalReimbursement ?? estimatedReimbursement;

  factory _PetClaim.fromFirestore(String docId, Map<String, dynamic> m) {
    DateTime parseTs(dynamic v) {
      if (v is Timestamp) return v.toDate();
      if (v is String) {
        return DateTime.tryParse(v) ?? DateTime.now();
      }
      return DateTime.now();
    }

    DateTime? parseTsNullable(dynamic v) {
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

    double asDouble(dynamic v) {
      if (v is num) return v.toDouble();
      if (v is String) return double.tryParse(v) ?? 0.0;
      return 0.0;
    }

    double? asDoubleNullable(dynamic v) {
      if (v == null) return null;
      if (v is num) return v.toDouble();
      if (v is String) return double.tryParse(v);
      return null;
    }

    final correspondences = <_Correspondence>[];
    final rawList = m['correspondences'];
    if (rawList is List) {
      for (final item in rawList) {
        if (item is Map) {
          try {
            correspondences
                .add(_Correspondence.fromMap(Map<String, dynamic>.from(item)));
          } catch (_) {}
        }
      }
    }

    return _PetClaim(
      id: docId,
      memberId: (m['memberId'] as String?) ?? '',
      petId: (m['petId'] as String?) ?? '',
      petName: (m['petName'] as String?)?.trim().isNotEmpty == true
          ? (m['petName'] as String).trim()
          : 'Pet',
      petType: _petTypeParse(m['petType'] as String?),
      amount: asDouble(m['amount']),
      dateOfService: parseTs(m['dateOfService'] ?? m['date']),
      providerClinic: (m['providerClinic'] as String?)?.trim() ??
          (m['provider'] as String?)?.trim() ??
          '',
      reason: (m['reason'] as String?)?.trim() ?? '',
      photoUrl: (m['photoUrl'] as String?),
      correspondences: correspondences,
      status: _statusParse(m['status'] as String?),
      submittedAt: parseTsNullable(m['submittedAt']),
      updatedAt: parseTsNullable(m['updatedAt']),
      memberAcknowledgedExclusions: m['memberAcknowledgedExclusions'] == true,
      exclusionsAcknowledgedAt: parseTsNullable(m['exclusionsAcknowledgedAt']),
      rejectionReason: (m['rejectionReason'] as String?)?.trim(),
      finalReimbursement: asDoubleNullable(m['finalReimbursement']),
    );
  }
}

/// A lightweight draft holder used by the New Claim flow before submit.
class _ClaimDraft {
  _PetLite? pet;
  bool acknowledgedExclusions = false;
  DateTime? exclusionsAcknowledgedAt;
  String? photoUrl;
  String? photoStoragePath;
  String? photoLocalPreviewPath; // for iOS/Android preview before upload
  Uint8List? photoBytes; // for web preview + upload
  double amount = 0.0;
  DateTime dateOfService = DateTime.now();
  String providerClinic = '';
  String reason = '';
  List<_Correspondence> correspondences = [];

  double get estimatedReimbursement =>
      (amount * _jovReimbursementRate * 100).round() / 100;

  bool get isReadyToSubmit {
    if (pet == null) return false;
    if (!acknowledgedExclusions) return false;
    if (amount <= 0) return false;
    if (providerClinic.trim().isEmpty) return false;
    if (reason.trim().isEmpty) return false;
    if (photoUrl == null || photoUrl!.isEmpty) return false;
    return true;
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// CLAIM SERVICE (Firestore + Storage)
// Handles reading claims, uploading photos, and submitting new claims.
// All writes are scoped per-pet: users/{uid}/pets/{petId}/claims/{claimId}
// ═══════════════════════════════════════════════════════════════════════════

class _PetClaimService {
  final String uid;

  const _PetClaimService._(this.uid);

  factory _PetClaimService() {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      throw StateError('No authenticated user — cannot build claim service.');
    }
    return _PetClaimService._(user.uid);
  }

  CollectionReference<Map<String, dynamic>> claimsCollection(String petId) =>
      FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('pets')
          .doc(petId)
          .collection('claims');

  /// Upload a receipt photo (or correspondence doc) to Firebase Storage,
  /// returning the download URL + storage path so Jovi review can see the
  /// raw file if needed.
  Future<({String url, String storagePath})> uploadFile({
    required String claimId,
    required String filename,
    required dynamic source, // File on mobile, Uint8List on web
    String? contentType,
  }) async {
    final storage = FirebaseStorage.instanceFor(bucket: _storageBucket);
    final path = 'uploads/$uid/pet_claims/$claimId/$filename';
    final ref = storage.ref().child(path);

    UploadTask task;
    final metadata =
        contentType != null ? SettableMetadata(contentType: contentType) : null;

    if (source is File) {
      task = metadata != null
          ? ref.putFile(source, metadata)
          : ref.putFile(source);
    } else if (source is Uint8List) {
      task = metadata != null
          ? ref.putData(source, metadata)
          : ref.putData(source);
    } else {
      throw ArgumentError(
          'uploadFile source must be File or Uint8List, got ${source.runtimeType}');
    }

    await task;
    final url = await ref.getDownloadURL();
    return (url: url, storagePath: path);
  }

  /// Write the submitted claim to Firestore.
  Future<String> submitClaim(_ClaimDraft draft) async {
    if (draft.pet == null) throw StateError('Draft missing pet');
    final data = <String, dynamic>{
      'memberId': uid,
      'petId': draft.pet!.petId,
      'petName': draft.pet!.name,
      'petType': _petTypeSerialize(draft.pet!.type),
      'amount': draft.amount,
      'dateOfService': Timestamp.fromDate(draft.dateOfService),
      'providerClinic': draft.providerClinic.trim(),
      'reason': draft.reason.trim(),
      'photoUrl': draft.photoUrl ?? '',
      'correspondences': draft.correspondences.map((c) => c.toMap()).toList(),
      'status': _statusSerialize(_ClaimStatus.submitted),
      'submittedAt': FieldValue.serverTimestamp(),
      'updatedAt': FieldValue.serverTimestamp(),
      'memberAcknowledgedExclusions': draft.acknowledgedExclusions,
      'exclusionsAcknowledgedAt': draft.exclusionsAcknowledgedAt == null
          ? FieldValue.serverTimestamp()
          : Timestamp.fromDate(draft.exclusionsAcknowledgedAt!),
      'coverageRate': _jovReimbursementRate,
      'estimatedReimbursement': draft.estimatedReimbursement,
      'schemaVersion': 1,
    };
    final docRef = await claimsCollection(draft.pet!.petId).add(data);
    return docRef.id;
  }

  /// Append a correspondence doc to an existing claim.
  Future<void> appendCorrespondence({
    required String petId,
    required String claimId,
    required _Correspondence doc,
  }) async {
    await claimsCollection(petId).doc(claimId).update({
      'correspondences': FieldValue.arrayUnion([doc.toMap()]),
      'updatedAt': FieldValue.serverTimestamp(),
    });
  }

  /// Delete a draft-only claim. Non-draft claims should not be deletable
  /// from the client; Jovi review handles rejection/cancellation.
  Future<void> deleteClaim({
    required String petId,
    required String claimId,
  }) async {
    await claimsCollection(petId).doc(claimId).delete();
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// WIDGET DECLARATION
// Per the convention established with Pet Symptom Checker / Pet Records,
// the FF UI for this widget has no required width/height params — we use
// MediaQuery for sizing.
// ═══════════════════════════════════════════════════════════════════════════
