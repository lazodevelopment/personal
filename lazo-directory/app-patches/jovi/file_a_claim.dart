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

// ═══════════════════════════════════════════════════════════════
// JOVI HEALTH — FILE A CLAIM / UPLOAD RECEIPT
// Version: 2026.09.22-r2 (Apple HIG refinement pass)
//
// r2 changes vs r1:
//  Bugs
//  - Removed the FirebaseFirestore.settings assignment in initState. Settings
//    can only be applied before Firestore's first use, and Home has already
//    used it, so this could throw on open. Persistence is on by default.
//  - Cancelling the "confirm amount" dialog closed the sheet and showed
//    "Successfully submitted!" without submitting. onSubmit now returns a
//    bool and the sheet stays open on false.
//  - The sheet looked up ScaffoldMessenger from its own context after
//    popping itself (throws "deactivated widget"). Messenger is captured
//    before pop.
//  - Swipe-to-delete asserted "dismissed Dismissible is still part of the
//    tree" because the Firestore stream removes the row asynchronously. The
//    row is now hidden synchronously via a pending-delete set.
//  - Member selector mutated state and (re)subscribed to a no-op Firestore
//    listener during build on every rebuild. Removed the listener; default
//    member is chosen post-frame.
//  - Progress bar width was screen-width × 0.8 rather than the track's real
//    width. Now measured with LayoutBuilder.
//  - Detail rows with a long reason overflowed; value is now Flexible.
//  - Dead AnimationController (elasticOut) removed.
//  Apple design
//  - Press feedback on pointer-down for chips, rows, buttons, date field.
//  - Bottom sheets: drag handle, 44 pt close control, title case, shrink
//    with the keyboard so the field being edited stays visible.
//  - Confirmations (high amount, delete, info) use CupertinoAlertDialog with
//    a destructive Delete action; photo picking offers Take Photo / Library
//    via CupertinoActionSheet. Photos are resized to 1600 px / q85 before
//    upload instead of sending full-resolution captures.
//  - Items past the 60-minute delete window no longer swipe at all.
//  - Title case throughout, 17 pt semibold sheet titles, tabular amounts,
//    Reduce Motion honoured.
//  Needs in FlutterFlow: camera permission enabled (NSCameraUsageDescription)
//  because the picker can now open the camera.
// ═══════════════════════════════════════════════════════════════

import 'package:flutter/cupertino.dart';
import 'package:flutter/foundation.dart'; // for kIsWeb
import 'dart:typed_data'; // for Uint8List
import 'dart:io';
import 'dart:async';
import 'dart:ui' as ui_dart;
import 'package:image_picker/image_picker.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_storage/firebase_storage.dart';
import 'package:cloud_functions/cloud_functions.dart'; // Added for PayArc
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart'; // For opening URLs
import 'package:flutter/services.dart'; // For Clipboard and HapticFeedback
import 'dart:convert'; // For JSON parsing

/// Enumerations for device categorization
enum ScreenType { compact, medium, expanded, large }

/// Configuration object for responsive layouts
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
  static const Curve settle = Curves.easeOutCubic;
}

/// Press feedback that lives on pointer-down, not on release. Scales the
/// child down the instant a finger lands, releases when it lifts, and
/// springs back early if the finger travels ~10 px (a scroll, not a tap).
/// With no onTap it only provides the visual, so it can wrap a real button.
class _Pressable extends StatefulWidget {
  final Widget child;
  final VoidCallback? onTap;
  final double pressedScale;
  final bool reduceMotion;
  final String? semanticsLabel;
  final String? semanticsHint;

  const _Pressable({
    Key? key,
    required this.child,
    this.onTap,
    this.pressedScale = 0.97,
    this.reduceMotion = false,
    this.semanticsLabel,
    this.semanticsHint,
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
    final scale = (_down && !widget.reduceMotion) ? widget.pressedScale : 1.0;
    final scaled = AnimatedScale(
      scale: scale,
      duration: _down ? _Motion.pressIn : _Motion.pressOut,
      curve: _down ? Curves.easeOut : _Motion.settle,
      child: widget.child,
    );
    return Semantics(
      button: widget.onTap != null,
      label: widget.semanticsLabel,
      hint: widget.semanticsHint,
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
        child: widget.onTap == null
            ? scaled
            : GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: widget.onTap,
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
  bool loading = false,
  Duration? duration,
}) {
  return SnackBar(
    content: Row(children: [
      if (loading)
        SizedBox(
            width: 18,
            height: 18,
            child: CircularProgressIndicator(strokeWidth: 2, color: accent)),
      if (!loading && icon != null) Icon(icon, color: accent, size: 20),
      const SizedBox(width: 10),
      Expanded(
          child: Text(message,
              style: const TextStyle(
                  color: Colors.white,
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                  letterSpacing: -0.2))),
    ]),
    duration: duration ?? const Duration(milliseconds: 2200),
    backgroundColor: const Color(0xFF243352),
    elevation: 0,
    behavior: SnackBarBehavior.floating,
    margin: const EdgeInsets.fromLTRB(16, 0, 16, 24),
    shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: BorderSide(color: accent.withOpacity(0.35))),
  );
}

/// Shared header for every bottom sheet: drag handle, 44 pt close control,
/// title-case title, optional trailing action.
class _SheetHeader extends StatelessWidget {
  final String title;
  final ResponsiveConfig layoutSettings;
  final VoidCallback onClose;
  final IconData? trailingIcon;
  final String? trailingLabel;
  final VoidCallback? onTrailing;

  const _SheetHeader({
    Key? key,
    required this.title,
    required this.layoutSettings,
    required this.onClose,
    this.trailingIcon,
    this.trailingLabel,
    this.onTrailing,
  }) : super(key: key);

  Widget _chip(BuildContext context, IconData icon, String label,
      VoidCallback onTap) {
    return _Pressable(
      reduceMotion: MediaQuery.of(context).disableAnimations,
      pressedScale: 0.9,
      semanticsLabel: label,
      onTap: () {
        HapticFeedback.lightImpact();
        onTap();
      },
      child: Container(
        width: 44,
        height: 44,
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.2),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Icon(icon, color: Colors.white, size: 20),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: [_brandPrimary, _brandDark],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 36,
            height: 4,
            margin: const EdgeInsets.only(bottom: 8),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.55),
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          Row(
            children: [
              _chip(context, Icons.close_rounded, 'Close', onClose),
              Expanded(
                child: Text(
                  title,
                  textAlign: TextAlign.center,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 17,
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.4,
                  ),
                ),
              ),
              if (trailingIcon != null && onTrailing != null)
                _chip(context, trailingIcon!, trailingLabel ?? 'More',
                    onTrailing!)
              else
                const SizedBox(width: 44),
            ],
          ),
        ],
      ),
    );
  }
}

/// Centralized Firestore field keys
class ClaimFields {
  static const String type = 'type';
  static const String amount = 'amount';
  static const String date = 'date';
  static const String photoUrl = 'photoUrl';
  static const String provider = 'provider';
  static const String reason = 'reason';
  static const String status = 'status';
  static const String submittedAt = 'submittedAt';
  static const String paymentProcessed = 'paymentProcessed';
  static const String paymentId = 'paymentId';
  static const String correspondences = 'correspondences';
}

/// Correspondence model for storing additional documents
class Correspondence {
  final String id;
  final String url;
  final String description;
  final DateTime uploadedAt;
  final String type;

  Correspondence({
    required this.id,
    required this.url,
    required this.description,
    required this.uploadedAt,
    required this.type,
  });

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'url': url,
      'description': description,
      'uploadedAt': Timestamp.fromDate(uploadedAt),
      'type': type,
    };
  }

  static Correspondence fromMap(Map<String, dynamic> map) {
    return Correspondence(
      id: map['id'] ?? '',
      url: map['url'] ?? '',
      description: map['description'] ?? '',
      uploadedAt: (map['uploadedAt'] as Timestamp).toDate(),
      type: map['type'] ?? 'other',
    );
  }
}

const String _storageBucket = 'gs://kurv-health.firebasestorage.app';

// ═══════════════════════════════════════════════════════════════
// Jovi Brand Colors (navy + glass + coral design system)
// ═══════════════════════════════════════════════════════════════
const Color _brandPrimary = Color(0xFFFF6B4A); // joviCoral
const Color _brandDark = Color(0xFFE5583A); // joviCoralDark (used as accent)
const Color _brandLight = Color(0xFFFF8F73); // joviCoralLight

const Color joviCoral = Color(0xFFFF6B4A);
const Color joviCoralDark = Color(0xFFE5583A);
const Color joviCoralLight = Color(0xFFFF8F73);
const Color joviNavy = Color(0xFF1A2744);
const Color joviNavyDark = Color(0xFF0F1A2E);
const Color joviMint = Color(0xFF00D4AA);
const Color joviMintDark = Color(0xFF00B894);
const Color joviGold = Color(0xFFFFD166);

/// Service: separates Firestore & Storage logic
class ClaimService {
  final String uid;
  final CollectionReference claimsRef;

  ClaimService._(this.uid)
      : claimsRef = FirebaseFirestore.instance
            .collection('users')
            .doc(uid)
            .collection('claims');

  factory ClaimService() {
    final user = FirebaseAuth.instance.currentUser!;
    return ClaimService._(user.uid);
  }

  Future<String> addReceipt({
    required String memberId,
    required double amount,
    required DateTime date,
    dynamic photo,
  }) async {
    final docRef = await claimsRef.add({
      'memberId': memberId,
      ClaimFields.type: 'receipt',
      ClaimFields.amount: amount.toInt(),
      ClaimFields.date: Timestamp.fromDate(date),
      ClaimFields.photoUrl: '',
      ClaimFields.status: 'Pending',
      ClaimFields.correspondences: [],
    });

    if (photo != null) {
      final storage = FirebaseStorage.instanceFor(bucket: _storageBucket);
      final ref = storage.ref().child('uploads/$uid/claims/${docRef.id}.jpg');

      String url;
      if (photo is File) {
        final uploadTask = ref.putFile(photo);
        await uploadTask;
        url = await ref.getDownloadURL();
      } else if (photo is Uint8List) {
        final uploadTask = ref.putData(photo);
        await uploadTask;
        url = await ref.getDownloadURL();
      } else {
        return docRef.id;
      }
      await docRef.update({ClaimFields.photoUrl: url});
    }

    return docRef.id;
  }

  Future<Map<String, dynamic>> addClaimWithPayment({
    required String memberId,
    required String provider,
    required String reason,
    required double amount,
    required DateTime date,
    dynamic photo,
    String? paymentId,
    bool paymentProcessed = false,
  }) async {
    final docRef = await claimsRef.add({
      'memberId': memberId,
      ClaimFields.type: 'claim',
      ClaimFields.provider: provider,
      ClaimFields.reason: reason,
      ClaimFields.amount: amount.toInt(),
      ClaimFields.date: Timestamp.fromDate(date),
      ClaimFields.photoUrl: '',
      ClaimFields.status: paymentProcessed ? 'Processing' : 'Pending',
      ClaimFields.submittedAt: FieldValue.serverTimestamp(),
      ClaimFields.paymentProcessed: paymentProcessed,
      ClaimFields.correspondences: [],
      if (paymentId != null) ClaimFields.paymentId: paymentId,
    });

    if (photo != null) {
      final storage = FirebaseStorage.instanceFor(bucket: _storageBucket);
      final ref = storage.ref().child('uploads/$uid/claims/${docRef.id}.jpg');

      String url;
      if (photo is File) {
        final uploadTask = ref.putFile(photo);
        await uploadTask;
        url = await ref.getDownloadURL();
      } else if (photo is Uint8List) {
        final uploadTask = ref.putData(photo);
        await uploadTask;
        url = await ref.getDownloadURL();
      } else {
        return {'success': true, 'docId': docRef.id};
      }
      await docRef.update({ClaimFields.photoUrl: url});
    }

    return {'success': true, 'docId': docRef.id};
  }

  Future<void> addCorrespondence({
    required String claimId,
    required dynamic file,
    required String description,
    required String type,
  }) async {
    final correspondenceId = DateTime.now().millisecondsSinceEpoch.toString();
    final storage = FirebaseStorage.instanceFor(bucket: _storageBucket);
    final ref = storage
        .ref()
        .child('uploads/$uid/correspondences/$claimId/$correspondenceId.jpg');

    String url;
    if (file is File) {
      final uploadTask = ref.putFile(file);
      await uploadTask;
      url = await ref.getDownloadURL();
    } else if (file is Uint8List) {
      final uploadTask = ref.putData(file);
      await uploadTask;
      url = await ref.getDownloadURL();
    } else {
      throw Exception('Invalid file type');
    }

    final correspondence = Correspondence(
      id: correspondenceId,
      url: url,
      description: description,
      uploadedAt: DateTime.now(),
      type: type,
    );

    await claimsRef.doc(claimId).update({
      ClaimFields.correspondences:
          FieldValue.arrayUnion([correspondence.toMap()]),
    });
  }

  Future<void> deleteEntry(String id) async {
    final docRef = claimsRef.doc(id);
    final doc = await docRef.get();
    if (doc.exists) {
      final data = doc.data() as Map<String, dynamic>;
      final amount = (data[ClaimFields.amount] as num?)?.toInt() ?? 0;
      final type = data[ClaimFields.type] as String?;

      await docRef.delete();

      if (type == 'receipt') {
        final userDoc = FirebaseFirestore.instance.collection('users').doc(uid);
        await userDoc.update({
          'updateDed': FieldValue.increment(-amount),
        });
      }
    }
  }

  Future<void> updateEntry(String id, Map<String, Object?> u) =>
      claimsRef.doc(id).update(u);
}

/// PayArc Payment Service
class PayArcService {
  static Future<Map<String, dynamic>> processClaimPayment({
    required double amount,
    required String claimId,
    String? payarcCustomerId,
  }) async {
    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user == null) {
        throw Exception('User not authenticated');
      }

      if (payarcCustomerId == null) {
        final userDoc = await FirebaseFirestore.instance
            .collection('users')
            .doc(user.uid)
            .get();

        if (userDoc.exists) {
          final userData = userDoc.data() as Map<String, dynamic>;
          payarcCustomerId = userData['payarcCustomerId'] as String?;
        }
      }

      if (payarcCustomerId == null) {
        return {
          'success': false,
          'error':
              'No payment method on file. Please update your payment information.',
        };
      }

      final functions = FirebaseFunctions.instance;
      final callable = functions.httpsCallable('processClaimPayment');

      final result = await callable.call({
        'amount': amount,
        'claimId': claimId,
        'payarcCustomerId': payarcCustomerId,
        'userId': user.uid,
        'description': 'Claim reimbursement - ID: $claimId',
      });

      return result.data as Map<String, dynamic>;
    } catch (e) {
      print('PayArc payment error: $e');
      return {
        'success': false,
        'error': 'Payment processing failed: ${e.toString()}',
      };
    }
  }
}

/// Email Service
class EmailService {
  static Future<void> sendReceiptConfirmation({
    required String email,
    required String patientName,
    required double amount,
    required DateTime date,
    required String confirmationId,
    required double deductibleTotal,
    required double paidAmount,
    required double deductibleRemaining,
    required bool deductibleMet,
  }) async {
    try {
      final functions = FirebaseFunctions.instance;
      final callable = functions.httpsCallable('sendReceiptConfirmation');

      final progress = deductibleTotal > 0
          ? ((paidAmount / deductibleTotal) * 100).round()
          : 0;

      final result = await callable.call({
        'email': email,
        'patientName': patientName,
        'amount': amount.toStringAsFixed(2),
        'date': DateFormat.yMMMMd().format(date),
        'confirmationId': confirmationId,
        'submittedAt': DateFormat.yMMMMd().add_jm().format(DateTime.now()),
        'deductibleTotal': deductibleTotal.toStringAsFixed(0),
        'paidAmount': paidAmount.toStringAsFixed(0),
        'deductibleRemaining': deductibleRemaining.toStringAsFixed(0),
        'deductibleProgress': progress,
        'deductibleMet': deductibleMet,
      });

      print('[EMAIL] Receipt confirmation sent to $email');
    } catch (e) {
      print('[EMAIL] Error sending receipt confirmation: $e');
    }
  }

  static Future<void> sendClaimConfirmation({
    required String email,
    required String patientName,
    required String provider,
    required String reason,
    required double amount,
    required DateTime date,
    required String claimId,
    required String status,
    required bool paymentProcessed,
    String? paymentId,
  }) async {
    try {
      final functions = FirebaseFunctions.instance;
      final callable = functions.httpsCallable('sendClaimConfirmation');

      final result = await callable.call({
        'email': email,
        'patientName': patientName,
        'provider': provider,
        'reason': reason,
        'amount': amount.toStringAsFixed(2),
        'date': DateFormat.yMMMMd().format(date),
        'claimId': claimId,
        'submittedAt': DateFormat.yMMMMd().add_jm().format(DateTime.now()),
        'status': status,
        'paymentProcessed': paymentProcessed,
        if (paymentId != null) 'paymentId': paymentId,
      });

      print('[EMAIL] Claim confirmation sent to $email');
    } catch (e) {
      print('[EMAIL] Error sending claim confirmation: $e');
    }
  }
}

/// Show confirmation dialog for high amounts
Future<bool> showHighAmountConfirmation(
    BuildContext context, double amount, String type) async {
  final result = await showCupertinoDialog<bool>(
    context: context,
    builder: (ctx) => CupertinoAlertDialog(
      title: const Text('Confirm Amount'),
      content: Padding(
        padding: const EdgeInsets.only(top: 8),
        child: Text(
          'You entered \$${amount.toStringAsFixed(2)} for this $type. '
          'Please double-check that it is correct.',
        ),
      ),
      actions: [
        CupertinoDialogAction(
          onPressed: () => Navigator.of(ctx).pop(false),
          child: const Text('Let Me Check'),
        ),
        CupertinoDialogAction(
          isDefaultAction: true,
          onPressed: () => Navigator.of(ctx).pop(true),
          child: const Text('It’s Correct'),
        ),
      ],
    ),
  );

  return result ?? false;
}

bool canDeleteItem(Map<String, dynamic> data) {
  Timestamp? submittedAt;

  if (data[ClaimFields.type] == 'claim') {
    submittedAt = data[ClaimFields.submittedAt] as Timestamp?;
  } else {
    submittedAt = data[ClaimFields.date] as Timestamp?;
  }

  if (submittedAt == null) return false;

  final uploadTime = submittedAt.toDate();
  final now = DateTime.now();
  final difference = now.difference(uploadTime);

  return difference.inMinutes <= 60;
}

Future<bool> showDeleteConfirmation(
    BuildContext context, String type, bool canDelete) async {
  if (!canDelete) {
    await showCupertinoDialog<void>(
      context: context,
      builder: (ctx) => CupertinoAlertDialog(
        title: const Text('Can’t Delete'),
        content: Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Text(
              'This $type was uploaded more than 60 minutes ago and can no longer be deleted.'),
        ),
        actions: [
          CupertinoDialogAction(
            isDefaultAction: true,
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('OK'),
          ),
        ],
      ),
    );
    return false;
  }

  // A genuinely irreversible action, so a confirmation earns its place.
  final result = await showCupertinoDialog<bool>(
    context: context,
    builder: (ctx) => CupertinoAlertDialog(
      title: Text('Delete this $type?'),
      content: const Padding(
        padding: EdgeInsets.only(top: 8),
        child: Text('This can’t be undone.'),
      ),
      actions: [
        CupertinoDialogAction(
          isDefaultAction: true,
          onPressed: () => Navigator.of(ctx).pop(false),
          child: const Text('Cancel'),
        ),
        CupertinoDialogAction(
          isDestructiveAction: true,
          onPressed: () => Navigator.of(ctx).pop(true),
          child: const Text('Delete'),
        ),
      ],
    ),
  );

  return result ?? false;
}

// ═══════════════════════════════════════════════════════════════
// REUSABLE FORM FIELDS (glass fills, white text on navy)
// ═══════════════════════════════════════════════════════════════

/// DatePickerField: label + date picker
class DatePickerField extends StatelessWidget {
  final DateTime currentValue;
  final String label;
  final Function(DateTime) onDateSelected;
  final ResponsiveConfig layoutSettings;

  const DatePickerField({
    Key? key,
    required this.currentValue,
    required this.label,
    required this.onDateSelected,
    required this.layoutSettings,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return _Pressable(
      reduceMotion: MediaQuery.of(context).disableAnimations,
      pressedScale: 0.985,
      semanticsLabel: '$label, ${DateFormat.yMMMMd().format(currentValue)}',
      semanticsHint: 'Choose a date',
      onTap: () async {
        HapticFeedback.selectionClick();
        final d = await showDatePicker(
          context: context,
          initialDate: currentValue,
          firstDate: DateTime(2000),
          lastDate: DateTime.now(),
          builder: (ctx, child) => Theme(
            data: Theme.of(ctx).copyWith(
              colorScheme: ColorScheme.light(primary: _brandPrimary),
            ),
            child: child!,
          ),
        );
        if (d != null) onDateSelected(d);
      },
      child: Container(
        padding: EdgeInsets.all(layoutSettings.paddingH * 0.8),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.08),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.white.withOpacity(0.15)),
        ),
        child: Row(
          children: [
            Icon(Icons.calendar_today,
                color: _brandPrimary,
                size: layoutSettings.actionIconDimension * 0.8),
            SizedBox(width: layoutSettings.paddingH * 0.8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    style: TextStyle(
                      fontSize: layoutSettings.actionTextSize,
                      color: Colors.white.withOpacity(0.6),
                    ),
                  ),
                  SizedBox(height: 4),
                  Text(
                    DateFormat.yMMMMd().format(currentValue),
                    style: TextStyle(
                      fontSize: layoutSettings.wideMode ? 16 : 14,
                      fontWeight: FontWeight.w500,
                      color: Colors.white,
                    ),
                  ),
                ],
              ),
            ),
            Icon(Icons.arrow_drop_down,
                color: Colors.white.withOpacity(0.6),
                size: layoutSettings.actionIconDimension * 0.8),
          ],
        ),
      ),
    );
  }
}

/// AmountField: numeric input
class AmountField extends StatelessWidget {
  final Function(double) onAmountChanged;
  final ResponsiveConfig layoutSettings;

  const AmountField({
    Key? key,
    required this.onAmountChanged,
    required this.layoutSettings,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      style: TextStyle(
          fontSize: layoutSettings.wideMode ? 16 : 14, color: Colors.white),
      cursorColor: _brandPrimary,
      textInputAction: TextInputAction.done,
      decoration: InputDecoration(
        labelText: 'Amount',
        labelStyle: TextStyle(color: Colors.white.withOpacity(0.7)),
        hintText: 'Enter amount',
        hintStyle: TextStyle(
          fontSize: layoutSettings.actionTextSize,
          color: Colors.white.withOpacity(0.4),
        ),
        prefixIcon: Icon(Icons.attach_money,
            color: _brandPrimary,
            size: layoutSettings.actionIconDimension * 0.8),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: Colors.white.withOpacity(0.15)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: Colors.white.withOpacity(0.15)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: _brandPrimary, width: 2),
        ),
        filled: true,
        fillColor: Colors.white.withOpacity(0.08),
        contentPadding: EdgeInsets.all(layoutSettings.paddingH * 0.8),
      ),
      keyboardType: const TextInputType.numberWithOptions(decimal: true),
      validator: (v) {
        if (v == null || v.isEmpty) return 'Enter amount';
        final parsed = double.tryParse(v.replaceAll(',', ''));
        if (parsed == null) return 'Invalid number';
        if (parsed <= 0) return 'Amount must be > 0';
        return null;
      },
      onChanged: (v) {
        final parsed = double.tryParse(v.replaceAll(',', '')) ?? 0;
        onAmountChanged(parsed);
      },
    );
  }
}

/// Provider dropdown
class ProviderDropdownField extends StatelessWidget {
  final String? currentValue;
  final Function(String?) onChanged;
  final ResponsiveConfig layoutSettings;

  const ProviderDropdownField({
    Key? key,
    required this.currentValue,
    required this.onChanged,
    required this.layoutSettings,
  }) : super(key: key);

  static const providers = <String>[
    'Hospital',
    'Urgent Care',
    'Dentist',
    'Vision Doctor',
  ];

  @override
  Widget build(BuildContext context) {
    return DropdownButtonFormField<String>(
      value: currentValue,
      dropdownColor: joviNavy,
      style: TextStyle(
        fontSize: layoutSettings.wideMode ? 16 : 14,
        color: Colors.white,
      ),
      decoration: InputDecoration(
        labelText: 'Provider',
        labelStyle: TextStyle(color: Colors.white.withOpacity(0.7)),
        prefixIcon: Icon(Icons.local_hospital,
            color: _brandPrimary,
            size: layoutSettings.actionIconDimension * 0.8),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: Colors.white.withOpacity(0.15)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: Colors.white.withOpacity(0.15)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: _brandPrimary, width: 2),
        ),
        filled: true,
        fillColor: Colors.white.withOpacity(0.08),
      ),
      items: providers
          .map((p) => DropdownMenuItem(value: p, child: Text(p)))
          .toList(),
      validator: (v) => v == null ? 'Select a provider' : null,
      onChanged: onChanged,
    );
  }
}

/// ReasonField: single-line text
class ReasonField extends StatelessWidget {
  final Function(String) onReasonChanged;
  final ResponsiveConfig layoutSettings;

  const ReasonField({
    Key? key,
    required this.onReasonChanged,
    required this.layoutSettings,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      style: TextStyle(
          fontSize: layoutSettings.wideMode ? 16 : 14, color: Colors.white),
      cursorColor: _brandPrimary,
      textInputAction: TextInputAction.next,
      textCapitalization: TextCapitalization.sentences,
      decoration: InputDecoration(
        labelText: 'Reason for Visit',
        labelStyle: TextStyle(color: Colors.white.withOpacity(0.7)),
        hintText: 'Describe your visit reason',
        hintStyle: TextStyle(
          fontSize: layoutSettings.actionTextSize,
          color: Colors.white.withOpacity(0.4),
        ),
        prefixIcon: Icon(Icons.edit_note,
            color: _brandPrimary,
            size: layoutSettings.actionIconDimension * 0.8),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: Colors.white.withOpacity(0.15)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: Colors.white.withOpacity(0.15)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: _brandPrimary, width: 2),
        ),
        filled: true,
        fillColor: Colors.white.withOpacity(0.08),
        contentPadding: EdgeInsets.all(layoutSettings.paddingH * 0.8),
      ),
      validator: (v) => (v == null || v.isEmpty) ? 'Enter reason' : null,
      onChanged: (v) => onReasonChanged(v),
    );
  }
}

/// Correspondence type dropdown
class CorrespondenceTypeField extends StatelessWidget {
  final String? currentValue;
  final Function(String?) onChanged;
  final ResponsiveConfig layoutSettings;

  const CorrespondenceTypeField({
    Key? key,
    required this.currentValue,
    required this.onChanged,
    required this.layoutSettings,
  }) : super(key: key);

  static const types = <String>[
    'Doctor Note',
    'Hospital Letter',
    'Insurance Form',
    'Lab Results',
    'Prescription',
    'Treatment Plan',
    'Other Document',
  ];

  @override
  Widget build(BuildContext context) {
    return DropdownButtonFormField<String>(
      value: currentValue,
      dropdownColor: joviNavy,
      style: TextStyle(
        fontSize: layoutSettings.wideMode ? 16 : 14,
        color: Colors.white,
      ),
      decoration: InputDecoration(
        labelText: 'Document Type',
        labelStyle: TextStyle(color: Colors.white.withOpacity(0.7)),
        prefixIcon: Icon(Icons.description,
            color: _brandPrimary,
            size: layoutSettings.actionIconDimension * 0.8),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: Colors.white.withOpacity(0.15)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: Colors.white.withOpacity(0.15)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: _brandPrimary, width: 2),
        ),
        filled: true,
        fillColor: Colors.white.withOpacity(0.08),
      ),
      items: types
          .map((type) => DropdownMenuItem(value: type, child: Text(type)))
          .toList(),
      validator: (v) => v == null ? 'Select document type' : null,
      onChanged: onChanged,
    );
  }
}

/// Description field
class DescriptionField extends StatelessWidget {
  final Function(String) onDescriptionChanged;
  final ResponsiveConfig layoutSettings;

  const DescriptionField({
    Key? key,
    required this.onDescriptionChanged,
    required this.layoutSettings,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      style: TextStyle(
          fontSize: layoutSettings.wideMode ? 16 : 14, color: Colors.white),
      cursorColor: _brandPrimary,
      textCapitalization: TextCapitalization.sentences,
      decoration: InputDecoration(
        labelText: 'Description',
        labelStyle: TextStyle(color: Colors.white.withOpacity(0.7)),
        hintText: 'Brief description of the document',
        hintStyle: TextStyle(
          fontSize: layoutSettings.actionTextSize,
          color: Colors.white.withOpacity(0.4),
        ),
        prefixIcon: Icon(Icons.short_text,
            color: _brandPrimary,
            size: layoutSettings.actionIconDimension * 0.8),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: Colors.white.withOpacity(0.15)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: Colors.white.withOpacity(0.15)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: _brandPrimary, width: 2),
        ),
        filled: true,
        fillColor: Colors.white.withOpacity(0.08),
        contentPadding: EdgeInsets.all(layoutSettings.paddingH * 0.8),
      ),
      maxLines: 2,
      validator: (v) => (v == null || v.isEmpty) ? 'Enter description' : null,
      onChanged: (v) => onDescriptionChanged(v),
    );
  }
}

/// iOS-style source chooser. Receipts are usually photographed on the spot,
/// so the camera is offered first. Needs camera permission enabled in
/// FlutterFlow (NSCameraUsageDescription).
Future<ImageSource?> _chooseImageSource(BuildContext context) {
  return showCupertinoModalPopup<ImageSource>(
    context: context,
    builder: (ctx) => CupertinoActionSheet(
      title: const Text('Add a photo'),
      actions: [
        CupertinoActionSheetAction(
          onPressed: () => Navigator.of(ctx).pop(ImageSource.camera),
          child: const Text('Take Photo'),
        ),
        CupertinoActionSheetAction(
          onPressed: () => Navigator.of(ctx).pop(ImageSource.gallery),
          child: const Text('Choose from Library'),
        ),
      ],
      cancelButton: CupertinoActionSheetAction(
        isDefaultAction: true,
        onPressed: () => Navigator.of(ctx).pop(),
        child: const Text('Cancel'),
      ),
    ),
  );
}

/// Image picker for web & mobile
class ReceiptImagePicker extends StatefulWidget {
  final Function(dynamic) onImagePicked;
  final ResponsiveConfig layoutSettings;

  const ReceiptImagePicker({
    Key? key,
    required this.onImagePicked,
    required this.layoutSettings,
  }) : super(key: key);

  @override
  _ReceiptImagePickerState createState() => _ReceiptImagePickerState();
}

class _ReceiptImagePickerState extends State<ReceiptImagePicker> {
  File? _mobileImage;
  Uint8List? _webImage;
  double? _uploadProgress;
  final _picker = ImagePicker();

  Future<void> _pick() async {
    HapticFeedback.selectionClick();
    final source =
        kIsWeb ? ImageSource.gallery : await _chooseImageSource(context);
    if (source == null) return;
    // Resize on-device: a full-resolution capture is 5–12 MB; 1600 px at
    // q85 is plenty for a legible receipt and uploads in a fraction of the
    // time.
    final picked = await _picker.pickImage(
        source: source, maxWidth: 1600, imageQuality: 85);
    if (picked == null) return;

    if (kIsWeb) {
      final bytes = await picked.readAsBytes();
      setState(() {
        _webImage = bytes;
        _mobileImage = null;
      });
      widget.onImagePicked(bytes);
    } else {
      final file = File(picked.path);
      setState(() {
        _mobileImage = file;
        _webImage = null;
      });
      widget.onImagePicked(file);
    }
    HapticFeedback.mediumImpact();
  }

  @override
  Widget build(BuildContext context) {
    final imageHeight = widget.layoutSettings.wideMode ? 180.0 : 150.0;

    return Column(
      children: [
        if (_webImage != null || _mobileImage != null)
          Container(
            height: imageHeight,
            margin:
                EdgeInsets.only(bottom: widget.layoutSettings.paddingV * 0.6),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(12),
              image: _webImage != null
                  ? DecorationImage(
                      image: MemoryImage(_webImage!),
                      fit: BoxFit.cover,
                    )
                  : _mobileImage != null
                      ? DecorationImage(
                          image: FileImage(_mobileImage!),
                          fit: BoxFit.cover,
                        )
                      : null,
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.2),
                  blurRadius: 10,
                  offset: Offset(0, 4),
                ),
              ],
            ),
            child: Stack(
              children: [
                if (_uploadProgress != null)
                  Center(
                    child: CircularProgressIndicator(
                      value: _uploadProgress,
                      color: _brandPrimary,
                    ),
                  ),
                Positioned(
                  top: 8,
                  right: 8,
                  child: Container(
                    decoration: BoxDecoration(
                      color: Colors.black54,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: IconButton(
                      icon: Icon(Icons.close,
                          color: Colors.white,
                          size:
                              widget.layoutSettings.actionIconDimension * 0.6),
                      onPressed: () {
                        setState(() {
                          _webImage = null;
                          _mobileImage = null;
                        });
                        widget.onImagePicked(null);
                        HapticFeedback.lightImpact();
                      },
                    ),
                  ),
                ),
              ],
            ),
          ),
        ElevatedButton.icon(
          icon: Icon(Icons.camera_alt,
              color: Colors.white,
              size: widget.layoutSettings.actionIconDimension * 0.7),
          label: Text(
            (_webImage != null || _mobileImage != null)
                ? 'Change Photo'
                : 'Attach Photo',
            style: TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w600,
              fontSize: widget.layoutSettings.wideMode ? 16 : 14,
            ),
          ),
          style: ElevatedButton.styleFrom(
            backgroundColor: _brandPrimary,
            foregroundColor: Colors.white,
            minimumSize: Size(
                double.infinity, widget.layoutSettings.actionItemHeight * 0.4),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
            elevation: 0,
            shadowColor: Colors.transparent,
          ),
          onPressed: _pick,
        ),
      ],
    );
  }
}

/// Correspondence Document Picker
class CorrespondenceDocumentPicker extends StatefulWidget {
  final Function(dynamic) onDocumentPicked;
  final ResponsiveConfig layoutSettings;

  const CorrespondenceDocumentPicker({
    Key? key,
    required this.onDocumentPicked,
    required this.layoutSettings,
  }) : super(key: key);

  @override
  _CorrespondenceDocumentPickerState createState() =>
      _CorrespondenceDocumentPickerState();
}

class _CorrespondenceDocumentPickerState
    extends State<CorrespondenceDocumentPicker> {
  File? _mobileDocument;
  Uint8List? _webDocument;
  String? _fileName;
  final _picker = ImagePicker();

  Future<void> _pick() async {
    HapticFeedback.selectionClick();
    final source =
        kIsWeb ? ImageSource.gallery : await _chooseImageSource(context);
    if (source == null) return;
    // Resize on-device: a full-resolution capture is 5–12 MB; 1600 px at
    // q85 is plenty for a legible receipt and uploads in a fraction of the
    // time.
    final picked = await _picker.pickImage(
        source: source, maxWidth: 1600, imageQuality: 85);
    if (picked == null) return;

    if (kIsWeb) {
      final bytes = await picked.readAsBytes();
      setState(() {
        _webDocument = bytes;
        _mobileDocument = null;
        _fileName = picked.name;
      });
      widget.onDocumentPicked(bytes);
    } else {
      final file = File(picked.path);
      setState(() {
        _mobileDocument = file;
        _webDocument = null;
        _fileName = picked.name;
      });
      widget.onDocumentPicked(file);
    }
    HapticFeedback.mediumImpact();
  }

  @override
  Widget build(BuildContext context) {
    final hasDocument = _webDocument != null || _mobileDocument != null;

    return Column(
      children: [
        if (hasDocument)
          Container(
            padding: EdgeInsets.all(widget.layoutSettings.paddingH * 0.8),
            margin:
                EdgeInsets.only(bottom: widget.layoutSettings.paddingV * 0.6),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.08),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.white.withOpacity(0.15)),
            ),
            child: Row(
              children: [
                Icon(
                  Icons.description,
                  color: _brandPrimary,
                  size: widget.layoutSettings.actionIconDimension,
                ),
                SizedBox(width: widget.layoutSettings.paddingH * 0.6),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Document Selected',
                        style: TextStyle(
                          fontSize: widget.layoutSettings.actionTextSize,
                          fontWeight: FontWeight.w600,
                          color: Colors.white,
                        ),
                      ),
                      if (_fileName != null)
                        Text(
                          _fileName!,
                          style: TextStyle(
                            fontSize: widget.layoutSettings.actionTextSize - 1,
                            color: Colors.white.withOpacity(0.6),
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                    ],
                  ),
                ),
                IconButton(
                  icon: Icon(Icons.close,
                      color: Colors.white.withOpacity(0.6),
                      size: widget.layoutSettings.actionIconDimension * 0.6),
                  onPressed: () {
                    setState(() {
                      _webDocument = null;
                      _mobileDocument = null;
                      _fileName = null;
                    });
                    widget.onDocumentPicked(null);
                    HapticFeedback.lightImpact();
                  },
                ),
              ],
            ),
          ),
        ElevatedButton.icon(
          icon: Icon(Icons.attach_file,
              color: Colors.white,
              size: widget.layoutSettings.actionIconDimension * 0.7),
          label: Text(
            hasDocument ? 'Change Document' : 'Attach Document',
            style: TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w600,
              fontSize: widget.layoutSettings.wideMode ? 16 : 14,
            ),
          ),
          style: ElevatedButton.styleFrom(
            backgroundColor: _brandPrimary,
            foregroundColor: Colors.white,
            minimumSize: Size(
                double.infinity, widget.layoutSettings.actionItemHeight * 0.4),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
            elevation: 0,
            shadowColor: Colors.transparent,
          ),
          onPressed: _pick,
        ),
      ],
    );
  }
}

/// Bottom-sheet form - NAVY BG
class ClaimFormSheet extends StatefulWidget {
  final String title;
  final List<Widget> fields;
  /// Returns true when the submission went through. Returning false (for
  /// example after the user backs out of a confirmation) keeps the sheet
  /// open with no toast. Throwing shows the error inline.
  final Future<bool> Function() onSubmit;
  final bool showPaymentWarning;
  final ResponsiveConfig layoutSettings;

  const ClaimFormSheet({
    Key? key,
    required this.title,
    required this.fields,
    required this.onSubmit,
    this.showPaymentWarning = false,
    required this.layoutSettings,
  }) : super(key: key);

  @override
  _ClaimFormSheetState createState() => _ClaimFormSheetState();
}

class _ClaimFormSheetState extends State<ClaimFormSheet> {
  final _formKey = GlobalKey<FormState>();
  bool _isLoading = false;
  String? _validationError;

  Future<void> _handleSubmit() async {
    setState(() => _validationError = null);
    if (!_formKey.currentState!.validate()) return;
    FocusManager.instance.primaryFocus?.unfocus();
    setState(() => _isLoading = true);

    try {
      final submitted = await widget.onSubmit();
      if (!mounted) return;
      if (!submitted) {
        // Backed out of a confirmation: stay open, no toast.
        setState(() => _isLoading = false);
        return;
      }
      // Capture the messenger before popping. The sheet's context is
      // deactivated after pop() and looking it up then throws.
      final messenger = ScaffoldMessenger.maybeOf(context);
      HapticFeedback.mediumImpact();
      Navigator.of(context).pop();
      messenger?.hideCurrentSnackBar();
      messenger?.showSnackBar(_joviToast('Submitted',
          accent: joviMint, icon: Icons.check_circle_rounded));
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        final msg = e.toString().replaceAll('Exception: ', '');
        if (msg.contains('amount') ||
            msg.contains('photo') ||
            msg.contains('document') ||
            msg.contains('member') ||
            msg.contains('provider')) {
          _validationError = msg;
        } else {
          _validationError = 'Something went wrong: $msg';
        }
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final screenHeight = MediaQuery.of(context).size.height;
    final insets = MediaQuery.of(context).viewInsets.bottom;
    final maxWidth = widget.layoutSettings.wideMode ? 600.0 : double.infinity;
    final reduceMotion = MediaQuery.of(context).disableAnimations;

    // The sheet shrinks as the keyboard rises so the field being edited and
    // the Submit button stay reachable (showModalBottomSheet does not do
    // this on its own).
    return AnimatedPadding(
      duration:
          reduceMotion ? Duration.zero : const Duration(milliseconds: 120),
      curve: Curves.easeOut,
      padding: EdgeInsets.only(bottom: insets),
      child: Container(
      height: (screenHeight * 0.9 - insets)
          .clamp(screenHeight * 0.45, screenHeight * 0.9)
          .toDouble(),
      width: double.infinity,
      constraints: BoxConstraints(maxWidth: maxWidth),
      decoration: BoxDecoration(
        color: joviNavy,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        children: [
          _SheetHeader(
            title: widget.title,
            layoutSettings: widget.layoutSettings,
            onClose: () => Navigator.of(context).pop(),
          ),
          Expanded(
            child: SingleChildScrollView(
              padding: EdgeInsets.all(widget.layoutSettings.paddingH),
              child: Form(
                key: _formKey,
                child: Column(
                  children: [
                    if (_validationError != null) ...[
                      Container(
                        padding: EdgeInsets.all(
                            widget.layoutSettings.paddingH * 0.6),
                        margin: EdgeInsets.only(
                            bottom: widget.layoutSettings.paddingV * 0.8),
                        decoration: BoxDecoration(
                          color: Color(0xFFE53935).withOpacity(0.15),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                              color: Color(0xFFE53935).withOpacity(0.4)),
                        ),
                        child: Row(
                          children: [
                            Icon(Icons.error_outline,
                                color: Color(0xFFFF6B6B),
                                size:
                                    widget.layoutSettings.actionIconDimension *
                                        0.7),
                            SizedBox(
                                width: widget.layoutSettings.paddingH * 0.4),
                            Expanded(
                              child: Text(
                                _validationError!,
                                style: TextStyle(
                                  color: Color(0xFFFF8A80),
                                  fontSize:
                                      widget.layoutSettings.actionTextSize,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                    if (widget.showPaymentWarning) ...[
                      Container(
                        padding: EdgeInsets.all(
                            widget.layoutSettings.paddingH * 0.6),
                        margin: EdgeInsets.only(
                            bottom: widget.layoutSettings.paddingV * 0.8),
                        decoration: BoxDecoration(
                          color: joviMint.withOpacity(0.12),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: joviMint.withOpacity(0.3)),
                        ),
                        child: Row(
                          children: [
                            Icon(Icons.info_outline,
                                color: joviMint,
                                size:
                                    widget.layoutSettings.actionIconDimension *
                                        0.7),
                            SizedBox(
                                width: widget.layoutSettings.paddingH * 0.4),
                            Expanded(
                              child: Text(
                                'Reimbursement will be processed to your saved payment method',
                                style: TextStyle(
                                  color: Colors.white.withOpacity(0.85),
                                  fontSize:
                                      widget.layoutSettings.actionTextSize,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                    ...widget.fields,
                    SizedBox(height: widget.layoutSettings.paddingV * 1.5),
                    _Pressable(
                      reduceMotion: reduceMotion,
                      pressedScale: 0.975,
                      child: Container(
                        width: double.infinity,
                        height: 56,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(16),
                          boxShadow: _isLoading
                              ? null
                              : [
                                  BoxShadow(
                                      color: _brandPrimary.withOpacity(0.35),
                                      blurRadius: 18,
                                      offset: const Offset(0, 8)),
                                ],
                        ),
                        child: ElevatedButton(
                          onPressed: _isLoading ? null : _handleSubmit,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: _brandPrimary,
                            foregroundColor: Colors.white,
                            disabledBackgroundColor:
                                _brandPrimary.withOpacity(0.5),
                            disabledForegroundColor: Colors.white,
                            elevation: 0,
                            shadowColor: Colors.transparent,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(16),
                            ),
                          ),
                          child: _isLoading
                              ? const SizedBox(
                                  width: 22,
                                  height: 22,
                                  child: CircularProgressIndicator(
                                      strokeWidth: 2, color: Colors.white),
                                )
                              : const Text(
                                  'Submit',
                                  style: TextStyle(
                                    fontSize: 17,
                                    fontWeight: FontWeight.w600,
                                    letterSpacing: -0.3,
                                  ),
                                ),
                        ),
                      ),
                    ),
                    SizedBox(
                        height: MediaQuery.of(context).padding.bottom + 20),
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
}

// ═══════════════════════════════════════════════════════════════
// MAIN WIDGET - FileClaimWidget (navy + glass)
// ═══════════════════════════════════════════════════════════════

class FileClaimWidget extends StatefulWidget {
  final double width, height;
  const FileClaimWidget({
    Key? key,
    this.width = double.infinity,
    this.height = double.infinity,
  }) : super(key: key);
  @override
  _FileClaimWidgetState createState() => _FileClaimWidgetState();
}

class _FileClaimWidgetState extends State<FileClaimWidget>
    with TickerProviderStateMixin {
  late String _uid;
  String? _userEmail;

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

  String? _selectedMemberId;
  String? _payarcCustomerId;

  double _deductible = 0;
  double _paid = 0;

  String _searchTerm = '';
  bool _showReceipts = true, _showClaims = true;
  StreamSubscription<DocumentSnapshot>? _userSub;
  Timer? _searchDebounce;

  bool _reduceMotion = false; // MediaQuery.disableAnimations
  // Rows swiped away but not yet removed by the Firestore stream.
  final Set<String> _pendingDeletes = <String>{};

  @override
  void initState() {
    super.initState();
    _uid = FirebaseAuth.instance.currentUser!.uid;
    // r1 assigned FirebaseFirestore.instance.settings here. Settings can
    // only be applied before Firestore's first use, and Home has already
    // used it by the time this screen opens, so that could throw. Offline
    // persistence is on by default on iOS and Android anyway.

    _userSub = FirebaseFirestore.instance
        .collection('users')
        .doc(_uid)
        .snapshots()
        .listen((snap) {
      if (!snap.exists) {
        print('[DEBUG] User document does not exist');
        return;
      }
      final data = snap.data()! as Map<String, dynamic>;

      _userEmail = data['email'] as String?;

      double d = 0.0;
      final rawMembers = data['members'] as List<dynamic>? ?? [];

      if (rawMembers.isNotEmpty) {
        try {
          final firstM =
              jsonDecode(rawMembers.first as String) as Map<String, dynamic>;
          final dedFromMember = (firstM['deductible'] as num?)?.toDouble();
          if (dedFromMember != null) {
            d = dedFromMember;
          }
        } catch (e) {
          print('[DEBUG] Error parsing members for deductible: $e');
        }
      }

      if (d == 0.0) {
        d = (data['deductible'] as num?)?.toDouble() ?? 0.0;
      }

      final p = (data['updateDed'] as num?)?.toDouble() ?? 0.0;
      _payarcCustomerId = data['payarcCustomerId'] as String?;

      if (!mounted) return;
      setState(() {
        _deductible = d;
        _paid = p;
      });
    });
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _reduceMotion = MediaQuery.of(context).disableAnimations;
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

    // Called from didChangeDependencies, which is always followed by a
    // build, so plain assignment is enough.
    _lastScreenWidth = screenWidth;
    _lastHasHinge = hasHinge;
    currentScreenType = screenType;
    layoutSettings = generateLayoutConfig(screenType, screenWidth, hasHinge);
  }

  ResponsiveConfig generateLayoutConfig(
    ScreenType type,
    double width,
    bool hasHinge,
  ) {
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
          constraints: BoxConstraints(
            maxWidth: layoutSettings.contentMax,
          ),
          child: child,
        ),
      );
    }
    return child;
  }

  @override
  void dispose() {
    _userSub?.cancel();
    _searchDebounce?.cancel();
    super.dispose();
  }

  void _onSearchChanged(String v) {
    if (_searchDebounce?.isActive ?? false) _searchDebounce!.cancel();
    _searchDebounce = Timer(const Duration(milliseconds: 300), () {
      setState(() => _searchTerm = v.trim().toLowerCase());
    });
  }

  void _showReceiptForm() {
    final member = _selectedMemberId;
    double _tempAmount = 0;
    DateTime _tempDate = DateTime.now();
    dynamic _tempPhoto;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) {
        return Center(
          child: ClaimFormSheet(
            title: 'Upload Receipt',
            layoutSettings: layoutSettings,
            fields: [
              AmountField(
                  onAmountChanged: (v) => _tempAmount = v,
                  layoutSettings: layoutSettings),
              SizedBox(height: layoutSettings.paddingV * 0.6),
              DatePickerField(
                currentValue: _tempDate,
                label: 'Date',
                onDateSelected: (d) => _tempDate = d,
                layoutSettings: layoutSettings,
              ),
              SizedBox(height: layoutSettings.paddingV * 0.6),
              ReceiptImagePicker(
                  onImagePicked: (f) => _tempPhoto = f,
                  layoutSettings: layoutSettings),
            ],
            onSubmit: () async {
              if (member == null) {
                throw Exception('Please select a member first');
              }
              if (_tempAmount <= 0) {
                throw Exception('Please enter a valid amount greater than \$0');
              }
              if (_tempPhoto == null) {
                throw Exception('Please attach a photo of your receipt');
              }
              if (_tempAmount > 500) {
                final confirmed = await showHighAmountConfirmation(
                    context, _tempAmount, 'receipt');
                if (!confirmed) return false;
              }

              final receiptDocId = await ClaimService().addReceipt(
                memberId: member,
                amount: _tempAmount,
                date: _tempDate,
                photo: _tempPhoto,
              );

              final userDoc =
                  FirebaseFirestore.instance.collection('users').doc(_uid);
              final int intAmt = _tempAmount.toInt();
              await userDoc.update({
                'updateDed': FieldValue.increment(intAmt),
              });

              if (_userEmail != null) {
                final newPaid = _paid + _tempAmount;
                final newRemaining =
                    (_deductible - newPaid).clamp(0.0, double.infinity);
                final newDeductibleMet = newPaid >= _deductible;

                await EmailService.sendReceiptConfirmation(
                  email: _userEmail!,
                  patientName: 'Patient',
                  amount: _tempAmount,
                  date: _tempDate,
                  confirmationId: receiptDocId.substring(0, 8).toUpperCase(),
                  deductibleTotal: _deductible,
                  paidAmount: newPaid,
                  deductibleRemaining: newRemaining,
                  deductibleMet: newDeductibleMet,
                );
              }
              return true;
            },
          ),
        );
      },
    );
  }

  void _showClaimForm() {
    if (_paid < _deductible) {
      _showSnackBar(
        'Meet your \$${_deductible.toStringAsFixed(0)} responsibility before filing claims. '
        'You have paid \$${_paid.toStringAsFixed(0)} so far.',
        isWarning: true,
      );
      return;
    }

    final member = _selectedMemberId;
    String? _tempProvider;
    String _tempReason = '';
    double _tempAmount = 0;
    DateTime _tempDate = DateTime.now();
    dynamic _tempPhoto;

    final bool hasPaymentMethod =
        _payarcCustomerId != null && _payarcCustomerId!.isNotEmpty;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setModalState) => Center(
            child: ClaimFormSheet(
              title: 'File a Claim',
              showPaymentWarning: hasPaymentMethod,
              layoutSettings: layoutSettings,
              fields: [
                if (!hasPaymentMethod) ...[
                  Container(
                    padding: EdgeInsets.all(layoutSettings.paddingH * 0.6),
                    margin:
                        EdgeInsets.only(bottom: layoutSettings.paddingV * 0.8),
                    decoration: BoxDecoration(
                      color: joviGold.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: joviGold.withOpacity(0.35)),
                    ),
                    child: Row(
                      children: [
                        Icon(Icons.warning_amber_outlined,
                            color: joviGold,
                            size: layoutSettings.actionIconDimension * 0.7),
                        SizedBox(width: layoutSettings.paddingH * 0.4),
                        Expanded(
                          child: Text(
                            'No payment method on file. Please update your payment information to receive reimbursements.',
                            style: TextStyle(
                                color: Colors.white.withOpacity(0.85),
                                fontSize: layoutSettings.actionTextSize),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
                ProviderDropdownField(
                  currentValue: _tempProvider,
                  onChanged: (v) => setModalState(() => _tempProvider = v),
                  layoutSettings: layoutSettings,
                ),
                SizedBox(height: layoutSettings.paddingV * 0.6),
                ReasonField(
                    onReasonChanged: (v) {
                      _tempReason = v;
                      setModalState(() {});
                    },
                    layoutSettings: layoutSettings),
                SizedBox(height: layoutSettings.paddingV * 0.6),
                AmountField(
                    onAmountChanged: (v) {
                      _tempAmount = v;
                      setModalState(() {});
                    },
                    layoutSettings: layoutSettings),
                SizedBox(height: layoutSettings.paddingV * 0.6),
                DatePickerField(
                  currentValue: _tempDate,
                  label: 'Date',
                  onDateSelected: (d) => setModalState(() => _tempDate = d),
                  layoutSettings: layoutSettings,
                ),
                SizedBox(height: layoutSettings.paddingV * 0.6),
                ReceiptImagePicker(
                    onImagePicked: (f) => setModalState(() => _tempPhoto = f),
                    layoutSettings: layoutSettings),
              ],
              onSubmit: () async {
                if (_tempProvider == null) {
                  throw Exception('Please select a provider');
                }
                if (member == null) {
                  throw Exception('Please select a member first');
                }
                if (_tempAmount <= 0) {
                  throw Exception(
                      'Please enter a valid amount greater than \$0');
                }
                if (_tempPhoto == null) {
                  throw Exception(
                      'Please attach a photo or document for your claim');
                }
                if (_tempAmount > 500) {
                  final confirmed = await showHighAmountConfirmation(
                      context, _tempAmount, 'claim');
                  if (!confirmed) return false;
                }

                if (!hasPaymentMethod) {
                  final claimResult = await ClaimService().addClaimWithPayment(
                    memberId: member!,
                    provider: _tempProvider!,
                    reason: _tempReason,
                    amount: _tempAmount,
                    date: _tempDate,
                    photo: _tempPhoto,
                    paymentProcessed: false,
                  );

                  if (_userEmail != null) {
                    await EmailService.sendClaimConfirmation(
                      email: _userEmail!,
                      patientName: 'Patient',
                      provider: _tempProvider!,
                      reason: _tempReason,
                      amount: _tempAmount,
                      date: _tempDate,
                      claimId:
                          claimResult['docId'].substring(0, 8).toUpperCase(),
                      status: 'Pending',
                      paymentProcessed: false,
                    );
                  }

                  _showSnackBar(
                      'Claim saved. Reimbursement is pending until you add a payment method.',
                      isWarning: true);
                } else {
                  _showSnackBar('Processing reimbursement...', isLoading: true);

                  final claimResult = await ClaimService().addClaimWithPayment(
                    memberId: member!,
                    provider: _tempProvider!,
                    reason: _tempReason,
                    amount: _tempAmount,
                    date: _tempDate,
                    photo: _tempPhoto,
                    paymentProcessed: false,
                  );

                  if (claimResult['success']) {
                    final paymentResult =
                        await PayArcService.processClaimPayment(
                      amount: _tempAmount,
                      claimId: claimResult['docId'],
                      payarcCustomerId: _payarcCustomerId,
                    );

                    if (paymentResult['success']) {
                      await ClaimService().updateEntry(
                        claimResult['docId'],
                        {
                          ClaimFields.paymentProcessed: true,
                          ClaimFields.paymentId: paymentResult['paymentId'],
                          ClaimFields.status: 'Processing',
                        },
                      );

                      if (_userEmail != null) {
                        await EmailService.sendClaimConfirmation(
                          email: _userEmail!,
                          patientName: 'Patient',
                          provider: _tempProvider!,
                          reason: _tempReason,
                          amount: _tempAmount,
                          date: _tempDate,
                          claimId: claimResult['docId']
                              .substring(0, 8)
                              .toUpperCase(),
                          status: 'Processing',
                          paymentProcessed: true,
                          paymentId: paymentResult['paymentId'],
                        );
                      }

                      _showSnackBar(
                          'Claim filed! Reimbursement of \$${_tempAmount.toStringAsFixed(2)} is being processed.',
                          isSuccess: true);
                    } else {
                      if (_userEmail != null) {
                        await EmailService.sendClaimConfirmation(
                          email: _userEmail!,
                          patientName: 'Patient',
                          provider: _tempProvider!,
                          reason: _tempReason,
                          amount: _tempAmount,
                          date: _tempDate,
                          claimId: claimResult['docId']
                              .substring(0, 8)
                              .toUpperCase(),
                          status: 'Pending',
                          paymentProcessed: false,
                        );
                      }

                      _showSnackBar(
                        paymentResult['error'] ??
                            'Reimbursement failed. Claim saved as pending.',
                        isError: true,
                      );
                    }
                  }
                }
                return true;
              },
            ),
          ),
        );
      },
    );
  }

  void _showCorrespondenceForm(String claimId, String claimType) {
    String? _tempType;
    String _tempDescription = '';
    dynamic _tempDocument;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setModalState) => Center(
            child: ClaimFormSheet(
              title: 'Add Document',
              layoutSettings: layoutSettings,
              fields: [
                Container(
                  padding: EdgeInsets.all(layoutSettings.paddingH * 0.6),
                  margin:
                      EdgeInsets.only(bottom: layoutSettings.paddingV * 0.8),
                  decoration: BoxDecoration(
                    color: joviMint.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: joviMint.withOpacity(0.3)),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.info_outline,
                          color: joviMint,
                          size: layoutSettings.actionIconDimension * 0.7),
                      SizedBox(width: layoutSettings.paddingH * 0.4),
                      Expanded(
                        child: Text(
                          'Upload additional documents related to this ${claimType.toLowerCase()}',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.85),
                            fontSize: layoutSettings.actionTextSize,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                CorrespondenceTypeField(
                  currentValue: _tempType,
                  onChanged: (v) => setModalState(() => _tempType = v),
                  layoutSettings: layoutSettings,
                ),
                SizedBox(height: layoutSettings.paddingV * 0.6),
                DescriptionField(
                  onDescriptionChanged: (v) {
                    _tempDescription = v;
                    setModalState(() {});
                  },
                  layoutSettings: layoutSettings,
                ),
                SizedBox(height: layoutSettings.paddingV * 0.6),
                CorrespondenceDocumentPicker(
                  onDocumentPicked: (f) =>
                      setModalState(() => _tempDocument = f),
                  layoutSettings: layoutSettings,
                ),
              ],
              onSubmit: () async {
                if (_tempType == null || _tempDocument == null) {
                  throw Exception(
                      'Please select a document type and attach a document');
                }

                await ClaimService().addCorrespondence(
                  claimId: claimId,
                  file: _tempDocument,
                  description: _tempDescription,
                  type: _tempType!,
                );
                return true;
              },
            ),
          ),
        );
      },
    );
  }

  void _showSnackBar(
    String message, {
    bool isError = false,
    bool isSuccess = false,
    bool isLoading = false,
    bool isWarning = false,
  }) {
    final messenger = ScaffoldMessenger.maybeOf(context);
    if (messenger == null) return;
    final accent = isError
        ? const Color(0xFFFF8A80)
        : isSuccess
            ? joviMint
            : isWarning
                ? joviGold
                : _brandPrimary;
    final icon = isError
        ? Icons.error_rounded
        : isSuccess
            ? Icons.check_circle_rounded
            : isWarning
                ? Icons.info_rounded
                : null;
    messenger.hideCurrentSnackBar();
    messenger.showSnackBar(_joviToast(
      message,
      accent: accent,
      icon: icon,
      loading: isLoading,
      duration: isError || isWarning
          ? const Duration(milliseconds: 4000)
          : (isLoading
              ? const Duration(seconds: 6)
              : const Duration(milliseconds: 2200)),
    ));
  }

  Widget _buildDetailRow(String label, String value, {Color? statusColor}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: TextStyle(
            fontSize: layoutSettings.actionTextSize,
            color: Colors.white.withOpacity(0.6),
          ),
        ),
        const SizedBox(width: 12),
        Flexible(
          child: Text(
            value,
            textAlign: TextAlign.end,
            style: TextStyle(
              fontSize: layoutSettings.actionTextSize,
              fontWeight: FontWeight.w600,
              color: statusColor ?? Colors.white,
              fontFeatures: const [ui_dart.FontFeature.tabularFigures()],
            ),
          ),
        ),
      ],
    );
  }

  Color _getStatusColor(String status) {
    if (status.toLowerCase() == 'approved') {
      return joviMint;
    } else if (status.toLowerCase() == 'denied') {
      return Color(0xFFFF6B6B);
    } else if (status.toLowerCase() == 'processing') {
      return joviCoralLight;
    } else {
      return joviGold;
    }
  }

  void _showReceiptDetail(QueryDocumentSnapshot doc) {
    final dataMap = doc.data() as Map<String, dynamic>;
    final amount = (dataMap[ClaimFields.amount] as num).toDouble();
    final timestamp = (dataMap[ClaimFields.date] as Timestamp).toDate();
    final photoUrl = (dataMap[ClaimFields.photoUrl] as String).isNotEmpty
        ? dataMap[ClaimFields.photoUrl] as String
        : null;
    final status = (dataMap[ClaimFields.status] as String?) ?? 'Pending';
    final correspondencesData =
        dataMap[ClaimFields.correspondences] as List<dynamic>? ?? [];
    final correspondences = correspondencesData
        .map((c) => Correspondence.fromMap(c as Map<String, dynamic>))
        .toList();

    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (context) {
        return SingleChildScrollView(
          child: Center(
            child: Container(
              constraints: BoxConstraints(
                  maxWidth: layoutSettings.wideMode ? 600 : double.infinity),
              decoration: BoxDecoration(
                color: joviNavy,
                borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
              ),
              padding: EdgeInsets.only(
                bottom: MediaQuery.of(context).viewInsets.bottom + 24,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  _SheetHeader(
                    title: 'Receipt Details',
                    layoutSettings: layoutSettings,
                    onClose: () => Navigator.of(context).pop(),
                    trailingIcon: Icons.attach_file_rounded,
                    trailingLabel: 'Add document',
                    onTrailing: () {
                      Navigator.of(context).pop();
                      _showCorrespondenceForm(doc.id, 'Receipt');
                    },
                  ),

                  Padding(
                    padding: EdgeInsets.all(layoutSettings.paddingH),
                    child: Column(
                      children: [
                        if (photoUrl != null)
                          Column(
                            children: [
                              Container(
                                height: layoutSettings.wideMode ? 250 : 200,
                                width: double.infinity,
                                decoration: BoxDecoration(
                                  borderRadius: BorderRadius.circular(12),
                                  color: Colors.white.withOpacity(0.05),
                                ),
                                child: InteractiveViewer(
                                  panEnabled: true,
                                  minScale: 1.0,
                                  maxScale: 4.0,
                                  child: ClipRRect(
                                    borderRadius: BorderRadius.circular(12),
                                    child: Image.network(
                                      photoUrl,
                                      fit: BoxFit.contain,
                                    ),
                                  ),
                                ),
                              ),
                              SizedBox(height: layoutSettings.paddingV * 0.6),
                              Row(
                                mainAxisAlignment: MainAxisAlignment.end,
                                children: [
                                  IconButton(
                                    icon: Icon(Icons.open_in_new,
                                        color: _brandPrimary,
                                        size:
                                            layoutSettings.actionIconDimension *
                                                0.8),
                                    tooltip: 'Open in browser',
                                    onPressed: () async {
                                      final uri = Uri.parse(photoUrl);
                                      if (await canLaunchUrl(uri)) {
                                        await launchUrl(uri,
                                            mode:
                                                LaunchMode.externalApplication);
                                      }
                                    },
                                  ),
                                  IconButton(
                                    icon: Icon(Icons.copy,
                                        color: _brandPrimary,
                                        size:
                                            layoutSettings.actionIconDimension *
                                                0.8),
                                    tooltip: 'Copy image URL',
                                    onPressed: () {
                                      Clipboard.setData(
                                          ClipboardData(text: photoUrl));
                                      HapticFeedback.mediumImpact();
                                      _showSnackBar('Link copied',
                                          isSuccess: true);
                                    },
                                  ),
                                ],
                              ),
                            ],
                          )
                        else
                          Container(
                            height: layoutSettings.wideMode ? 250 : 200,
                            width: double.infinity,
                            decoration: BoxDecoration(
                              gradient: LinearGradient(
                                colors: [
                                  _brandPrimary.withOpacity(0.12),
                                  _brandDark.withOpacity(0.06)
                                ],
                                begin: Alignment.topLeft,
                                end: Alignment.bottomRight,
                              ),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(
                                  color: _brandPrimary.withOpacity(0.3)),
                            ),
                            child: Center(
                              child: Icon(
                                Icons.receipt_long,
                                size: layoutSettings.actionIconDimension + 20,
                                color: _brandPrimary,
                              ),
                            ),
                          ),
                        SizedBox(height: layoutSettings.paddingV),
                        Container(
                          padding:
                              EdgeInsets.all(layoutSettings.paddingH * 0.8),
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.06),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                                color: Colors.white.withOpacity(0.1)),
                          ),
                          child: Column(
                            children: [
                              _buildDetailRow(
                                  'Amount', '\$${amount.toStringAsFixed(2)}'),
                              Divider(
                                  height: layoutSettings.paddingV,
                                  color: Colors.white.withOpacity(0.1)),
                              _buildDetailRow('Date',
                                  DateFormat.yMMMMd().format(timestamp)),
                              Divider(
                                  height: layoutSettings.paddingV,
                                  color: Colors.white.withOpacity(0.1)),
                              _buildDetailRow('Status', status,
                                  statusColor: _getStatusColor(status)),
                              Divider(
                                  height: layoutSettings.paddingV,
                                  color: Colors.white.withOpacity(0.1)),
                              _buildDetailRow(
                                  'Counts Toward', 'Your Responsibility',
                                  statusColor: joviMint),
                            ],
                          ),
                        ),
                        if (correspondences.isNotEmpty) ...[
                          SizedBox(height: layoutSettings.paddingV),
                          Container(
                            padding:
                                EdgeInsets.all(layoutSettings.paddingH * 0.8),
                            decoration: BoxDecoration(
                              color: joviMint.withOpacity(0.08),
                              borderRadius: BorderRadius.circular(12),
                              border:
                                  Border.all(color: joviMint.withOpacity(0.25)),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Icon(Icons.attach_file,
                                        color: joviMint,
                                        size:
                                            layoutSettings.actionIconDimension *
                                                0.7),
                                    SizedBox(
                                        width: layoutSettings.paddingH * 0.4),
                                    Text(
                                      'Correspondence (${correspondences.length})',
                                      style: TextStyle(
                                        fontSize: layoutSettings.actionTextSize,
                                        fontWeight: FontWeight.w600,
                                        color: joviMint,
                                      ),
                                    ),
                                  ],
                                ),
                                SizedBox(height: layoutSettings.paddingV * 0.6),
                                ...correspondences.map((correspondence) {
                                  return Container(
                                    margin: EdgeInsets.only(
                                        bottom: layoutSettings.paddingV * 0.4),
                                    padding: EdgeInsets.all(
                                        layoutSettings.paddingH * 0.6),
                                    decoration: BoxDecoration(
                                      color: Colors.white.withOpacity(0.06),
                                      borderRadius: BorderRadius.circular(8),
                                      border: Border.all(
                                          color: Colors.white.withOpacity(0.1)),
                                    ),
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Row(
                                          children: [
                                            Expanded(
                                              child: Text(
                                                correspondence.type,
                                                style: TextStyle(
                                                  fontSize: layoutSettings
                                                      .actionTextSize,
                                                  fontWeight: FontWeight.w600,
                                                  color: Colors.white,
                                                ),
                                              ),
                                            ),
                                            IconButton(
                                              icon: Icon(Icons.open_in_new,
                                                  color: _brandPrimary,
                                                  size: layoutSettings
                                                          .actionIconDimension *
                                                      0.6),
                                              onPressed: () async {
                                                final uri = Uri.parse(
                                                    correspondence.url);
                                                if (await canLaunchUrl(uri)) {
                                                  await launchUrl(uri,
                                                      mode: LaunchMode
                                                          .externalApplication);
                                                }
                                              },
                                            ),
                                          ],
                                        ),
                                        if (correspondence
                                            .description.isNotEmpty)
                                          Text(
                                            correspondence.description,
                                            style: TextStyle(
                                              fontSize: layoutSettings
                                                      .actionTextSize -
                                                  1,
                                              color:
                                                  Colors.white.withOpacity(0.6),
                                            ),
                                          ),
                                        SizedBox(height: 4),
                                        Text(
                                          'Uploaded ${DateFormat.yMMMd().add_jm().format(correspondence.uploadedAt)}',
                                          style: TextStyle(
                                            fontSize:
                                                layoutSettings.actionTextSize -
                                                    2,
                                            color:
                                                Colors.white.withOpacity(0.4),
                                          ),
                                        ),
                                      ],
                                    ),
                                  );
                                }).toList(),
                              ],
                            ),
                          ),
                        ],
                        SizedBox(height: layoutSettings.paddingV),
                        Row(
                          children: [
                            Expanded(
                              child: ElevatedButton.icon(
                                onPressed: () {
                                  Navigator.of(context).pop();
                                  _showCorrespondenceForm(doc.id, 'Receipt');
                                },
                                icon: Icon(Icons.attach_file, size: 16),
                                label: Text('Add Document'),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor:
                                      Colors.white.withOpacity(0.08),
                                  foregroundColor: Colors.white,
                                  padding: EdgeInsets.symmetric(
                                      vertical: layoutSettings.paddingV * 0.6),
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(12),
                                    side: BorderSide(
                                        color: Colors.white.withOpacity(0.15)),
                                  ),
                                ),
                              ),
                            ),
                            SizedBox(width: layoutSettings.paddingH * 0.6),
                            Expanded(
                              child: ElevatedButton(
                                onPressed: () => Navigator.of(context).pop(),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: _brandPrimary,
                                  foregroundColor: Colors.white,
                                  padding: EdgeInsets.symmetric(
                                      vertical: layoutSettings.paddingV * 0.6),
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                ),
                                child: Text(
                                  'Close',
                                  style: TextStyle(
                                    fontSize: layoutSettings.wideMode ? 16 : 14,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ),
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
        );
      },
    );
  }

  void _showClaimDetail(QueryDocumentSnapshot doc) {
    final dataMap = doc.data() as Map<String, dynamic>;
    final provider = dataMap[ClaimFields.provider] as String;
    final reason = dataMap[ClaimFields.reason] as String;
    final amount = (dataMap[ClaimFields.amount] as num).toDouble();
    final timestamp = (dataMap[ClaimFields.date] as Timestamp).toDate();
    final status = (dataMap[ClaimFields.status] as String?) ?? 'Pending';
    final submittedTs = dataMap[ClaimFields.submittedAt] as Timestamp?;
    final paymentProcessed =
        dataMap[ClaimFields.paymentProcessed] as bool? ?? false;
    final paymentId = dataMap[ClaimFields.paymentId] as String?;
    final photoUrl = (dataMap[ClaimFields.photoUrl] as String).isNotEmpty
        ? dataMap[ClaimFields.photoUrl] as String
        : null;
    final correspondencesData =
        dataMap[ClaimFields.correspondences] as List<dynamic>? ?? [];
    final correspondences = correspondencesData
        .map((c) => Correspondence.fromMap(c as Map<String, dynamic>))
        .toList();

    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (context) {
        return SingleChildScrollView(
          child: Center(
            child: Container(
              constraints: BoxConstraints(
                  maxWidth: layoutSettings.wideMode ? 600 : double.infinity),
              decoration: BoxDecoration(
                color: joviNavy,
                borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
              ),
              padding: EdgeInsets.only(
                bottom: MediaQuery.of(context).viewInsets.bottom + 24,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  _SheetHeader(
                    title: 'Claim Details',
                    layoutSettings: layoutSettings,
                    onClose: () => Navigator.of(context).pop(),
                    trailingIcon: Icons.attach_file_rounded,
                    trailingLabel: 'Add document',
                    onTrailing: () {
                      Navigator.of(context).pop();
                      _showCorrespondenceForm(doc.id, 'Claim');
                    },
                  ),
                  Padding(
                    padding: EdgeInsets.all(layoutSettings.paddingH),
                    child: Column(
                      children: [
                        if (paymentProcessed) ...[
                          Container(
                            padding:
                                EdgeInsets.all(layoutSettings.paddingH * 0.6),
                            decoration: BoxDecoration(
                              color: joviMint.withOpacity(0.12),
                              borderRadius: BorderRadius.circular(8),
                              border:
                                  Border.all(color: joviMint.withOpacity(0.35)),
                            ),
                            child: Row(
                              children: [
                                Icon(Icons.check_circle,
                                    color: joviMint,
                                    size: layoutSettings.actionIconDimension *
                                        0.7),
                                SizedBox(width: layoutSettings.paddingH * 0.4),
                                Expanded(
                                  child: Text(
                                    'Reimbursement processed successfully',
                                    style: TextStyle(
                                      color: joviMint,
                                      fontSize: layoutSettings.actionTextSize,
                                      fontWeight: FontWeight.w500,
                                    ),
                                  ),
                                ),
                                if (paymentId != null)
                                  Text(
                                    'ID: ${paymentId.substring(0, 8)}...',
                                    style: TextStyle(
                                      color: joviMint.withOpacity(0.8),
                                      fontSize:
                                          layoutSettings.actionTextSize - 1,
                                    ),
                                  ),
                              ],
                            ),
                          ),
                          SizedBox(height: layoutSettings.paddingV * 0.6),
                        ],
                        if (photoUrl != null)
                          Column(
                            children: [
                              Container(
                                height: layoutSettings.wideMode ? 250 : 200,
                                width: double.infinity,
                                decoration: BoxDecoration(
                                  borderRadius: BorderRadius.circular(12),
                                  color: Colors.white.withOpacity(0.05),
                                ),
                                child: InteractiveViewer(
                                  panEnabled: true,
                                  minScale: 1.0,
                                  maxScale: 4.0,
                                  child: ClipRRect(
                                    borderRadius: BorderRadius.circular(12),
                                    child: Image.network(
                                      photoUrl,
                                      fit: BoxFit.contain,
                                    ),
                                  ),
                                ),
                              ),
                              SizedBox(height: layoutSettings.paddingV * 0.6),
                              Row(
                                mainAxisAlignment: MainAxisAlignment.end,
                                children: [
                                  IconButton(
                                    icon: Icon(Icons.open_in_new,
                                        color: _brandPrimary,
                                        size:
                                            layoutSettings.actionIconDimension *
                                                0.8),
                                    onPressed: () async {
                                      final uri = Uri.parse(photoUrl);
                                      if (await canLaunchUrl(uri)) {
                                        await launchUrl(uri,
                                            mode:
                                                LaunchMode.externalApplication);
                                      }
                                    },
                                  ),
                                  IconButton(
                                    icon: Icon(Icons.copy,
                                        color: _brandPrimary,
                                        size:
                                            layoutSettings.actionIconDimension *
                                                0.8),
                                    onPressed: () {
                                      Clipboard.setData(
                                          ClipboardData(text: photoUrl));
                                      HapticFeedback.mediumImpact();
                                      _showSnackBar('Link copied',
                                          isSuccess: true);
                                    },
                                  ),
                                ],
                              ),
                            ],
                          )
                        else
                          Container(
                            height: layoutSettings.wideMode ? 250 : 200,
                            width: double.infinity,
                            decoration: BoxDecoration(
                              gradient: LinearGradient(
                                colors: [
                                  _brandPrimary.withOpacity(0.12),
                                  _brandDark.withOpacity(0.06)
                                ],
                                begin: Alignment.topLeft,
                                end: Alignment.bottomRight,
                              ),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(
                                  color: _brandPrimary.withOpacity(0.3)),
                            ),
                            child: Center(
                              child: Icon(
                                Icons.file_present,
                                size: layoutSettings.actionIconDimension + 20,
                                color: _brandPrimary,
                              ),
                            ),
                          ),
                        SizedBox(height: layoutSettings.paddingV),
                        Container(
                          padding:
                              EdgeInsets.all(layoutSettings.paddingH * 0.8),
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.06),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                                color: Colors.white.withOpacity(0.1)),
                          ),
                          child: Column(
                            children: [
                              _buildDetailRow('Provider', provider),
                              Divider(
                                  height: layoutSettings.paddingV,
                                  color: Colors.white.withOpacity(0.1)),
                              _buildDetailRow('Reason', reason),
                              Divider(
                                  height: layoutSettings.paddingV,
                                  color: Colors.white.withOpacity(0.1)),
                              _buildDetailRow('Reimbursement Amount',
                                  '\$${amount.toStringAsFixed(2)}'),
                              Divider(
                                  height: layoutSettings.paddingV,
                                  color: Colors.white.withOpacity(0.1)),
                              _buildDetailRow('Date',
                                  DateFormat.yMMMMd().format(timestamp)),
                              Divider(
                                  height: layoutSettings.paddingV,
                                  color: Colors.white.withOpacity(0.1)),
                              _buildDetailRow('Status', status,
                                  statusColor: _getStatusColor(status)),
                              if (submittedTs != null) ...[
                                Divider(
                                    height: layoutSettings.paddingV,
                                    color: Colors.white.withOpacity(0.1)),
                                _buildDetailRow(
                                    'Submitted',
                                    DateFormat.yMMMd()
                                        .add_jm()
                                        .format(submittedTs.toDate())),
                              ],
                            ],
                          ),
                        ),
                        if (correspondences.isNotEmpty) ...[
                          SizedBox(height: layoutSettings.paddingV),
                          Container(
                            padding:
                                EdgeInsets.all(layoutSettings.paddingH * 0.8),
                            decoration: BoxDecoration(
                              color: joviMint.withOpacity(0.08),
                              borderRadius: BorderRadius.circular(12),
                              border:
                                  Border.all(color: joviMint.withOpacity(0.25)),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Icon(Icons.attach_file,
                                        color: joviMint,
                                        size:
                                            layoutSettings.actionIconDimension *
                                                0.7),
                                    SizedBox(
                                        width: layoutSettings.paddingH * 0.4),
                                    Text(
                                      'Correspondence (${correspondences.length})',
                                      style: TextStyle(
                                        fontSize: layoutSettings.actionTextSize,
                                        fontWeight: FontWeight.w600,
                                        color: joviMint,
                                      ),
                                    ),
                                  ],
                                ),
                                SizedBox(height: layoutSettings.paddingV * 0.6),
                                ...correspondences.map((correspondence) {
                                  return Container(
                                    margin: EdgeInsets.only(
                                        bottom: layoutSettings.paddingV * 0.4),
                                    padding: EdgeInsets.all(
                                        layoutSettings.paddingH * 0.6),
                                    decoration: BoxDecoration(
                                      color: Colors.white.withOpacity(0.06),
                                      borderRadius: BorderRadius.circular(8),
                                      border: Border.all(
                                          color: Colors.white.withOpacity(0.1)),
                                    ),
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Row(
                                          children: [
                                            Expanded(
                                              child: Text(
                                                correspondence.type,
                                                style: TextStyle(
                                                  fontSize: layoutSettings
                                                      .actionTextSize,
                                                  fontWeight: FontWeight.w600,
                                                  color: Colors.white,
                                                ),
                                              ),
                                            ),
                                            IconButton(
                                              icon: Icon(Icons.open_in_new,
                                                  color: _brandPrimary,
                                                  size: layoutSettings
                                                          .actionIconDimension *
                                                      0.6),
                                              onPressed: () async {
                                                final uri = Uri.parse(
                                                    correspondence.url);
                                                if (await canLaunchUrl(uri)) {
                                                  await launchUrl(uri,
                                                      mode: LaunchMode
                                                          .externalApplication);
                                                }
                                              },
                                            ),
                                          ],
                                        ),
                                        if (correspondence
                                            .description.isNotEmpty)
                                          Text(
                                            correspondence.description,
                                            style: TextStyle(
                                              fontSize: layoutSettings
                                                      .actionTextSize -
                                                  1,
                                              color:
                                                  Colors.white.withOpacity(0.6),
                                            ),
                                          ),
                                        SizedBox(height: 4),
                                        Text(
                                          'Uploaded ${DateFormat.yMMMd().add_jm().format(correspondence.uploadedAt)}',
                                          style: TextStyle(
                                            fontSize:
                                                layoutSettings.actionTextSize -
                                                    2,
                                            color:
                                                Colors.white.withOpacity(0.4),
                                          ),
                                        ),
                                      ],
                                    ),
                                  );
                                }).toList(),
                              ],
                            ),
                          ),
                        ],
                        SizedBox(height: layoutSettings.paddingV),
                        Row(
                          children: [
                            Expanded(
                              child: ElevatedButton.icon(
                                onPressed: () {
                                  Navigator.of(context).pop();
                                  _showCorrespondenceForm(doc.id, 'Claim');
                                },
                                icon: Icon(Icons.attach_file, size: 16),
                                label: Text('Add Document'),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor:
                                      Colors.white.withOpacity(0.08),
                                  foregroundColor: Colors.white,
                                  padding: EdgeInsets.symmetric(
                                      vertical: layoutSettings.paddingV * 0.6),
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(12),
                                    side: BorderSide(
                                        color: Colors.white.withOpacity(0.15)),
                                  ),
                                ),
                              ),
                            ),
                            SizedBox(width: layoutSettings.paddingH * 0.6),
                            Expanded(
                              child: ElevatedButton(
                                onPressed: () => Navigator.of(context).pop(),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: _brandPrimary,
                                  foregroundColor: Colors.white,
                                  padding: EdgeInsets.symmetric(
                                      vertical: layoutSettings.paddingV * 0.6),
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                ),
                                child: Text(
                                  'Close',
                                  style: TextStyle(
                                    fontSize: layoutSettings.wideMode ? 16 : 14,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ),
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
        );
      },
    );
  }

  Widget _buildMemberSelector() {
    return StreamBuilder<DocumentSnapshot>(
      stream:
          FirebaseFirestore.instance.collection('users').doc(_uid).snapshots(),
      builder: (ctx, snap) {
        if (!snap.hasData) {
          return Container(
            height: layoutSettings.actionItemHeight * 0.6,
            child: Center(
              child: CircularProgressIndicator(color: _brandPrimary),
            ),
          );
        }
        final data = snap.data!.data()! as Map<String, dynamic>;
        final members = <Map<String, String>>[
          {'id': 'primary', 'name': data['onboard_fullName'] ?? 'You'}
        ];
        if (data['spouse'] == true) {
          members.add(
              {'id': 'spouse', 'name': '${data['sFirst']} ${data['sLast']}'});
        }
        for (var raw in (data['deps'] as List? ?? [])) {
          final d = jsonDecode(raw) as Map<String, dynamic>;
          members
              .add({'id': d['memberId'], 'name': '${d['first']} ${d['last']}'});
        }

        // Pick the first member after this frame rather than mutating state
        // during build.
        if (_selectedMemberId == null) {
          final first = members.first['id'];
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (mounted && _selectedMemberId == null) {
              setState(() => _selectedMemberId = first);
            }
          });
        }

        return Padding(
          padding: EdgeInsets.symmetric(
              horizontal: layoutSettings.paddingH,
              vertical: layoutSettings.paddingV * 0.8),
          child: Container(
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.07),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.white.withOpacity(0.12)),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.15),
                  blurRadius: 10,
                  offset: Offset(0, 4),
                ),
              ],
            ),
            child: DropdownButtonFormField<String>(
              value: _selectedMemberId,
              dropdownColor: joviNavy,
              style: TextStyle(
                fontSize: layoutSettings.wideMode ? 16 : 14,
                color: Colors.white,
              ),
              decoration: InputDecoration(
                labelText: 'Select Member',
                labelStyle: TextStyle(color: Colors.white.withOpacity(0.7)),
                prefixIcon: Icon(Icons.person,
                    color: _brandPrimary,
                    size: layoutSettings.actionIconDimension * 0.8),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide.none,
                ),
                filled: true,
                fillColor: Colors.transparent,
              ),
              items: members
                  .map((m) => DropdownMenuItem(
                        value: m['id'],
                        child: Text(
                          m['name']!,
                          style: TextStyle(color: Colors.white),
                        ),
                      ))
                  .toList(),
              onChanged: (v) {
                HapticFeedback.selectionClick();
                setState(() => _selectedMemberId = v);
              },
            ),
          ),
        );
      },
    );
  }

  Widget _buildSearchField() {
    return Padding(
      padding: EdgeInsets.symmetric(horizontal: layoutSettings.paddingH),
      child: Container(
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.07),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.white.withOpacity(0.12)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.12),
              blurRadius: 10,
              offset: Offset(0, 2),
            ),
          ],
        ),
        child: TextField(
          style: TextStyle(
              fontSize: layoutSettings.wideMode ? 16 : 14, color: Colors.white),
          decoration: InputDecoration(
            prefixIcon: Icon(Icons.search,
                color: _brandPrimary,
                size: layoutSettings.actionIconDimension * 0.8),
            hintText: 'Search history...',
            hintStyle: TextStyle(
              color: Colors.white.withOpacity(0.4),
              fontSize: layoutSettings.actionTextSize + 1,
            ),
            filled: true,
            fillColor: Colors.transparent,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide.none,
            ),
          ),
          onChanged: _onSearchChanged,
        ),
      ),
    );
  }

  Widget _buildFilterChips() {
    return Padding(
      padding: EdgeInsets.symmetric(
          horizontal: layoutSettings.paddingH,
          vertical: layoutSettings.paddingV * 0.6),
      child: Row(
        children: [
          Expanded(
            child: _Pressable(
              reduceMotion: _reduceMotion,
              pressedScale: 0.96,
              semanticsLabel:
                  _showReceipts ? 'Receipts, shown' : 'Receipts, hidden',
              semanticsHint: 'Toggles receipts in the list',
              onTap: () {
                HapticFeedback.selectionClick();
                setState(() => _showReceipts = !_showReceipts);
              },
              child: AnimatedContainer(
                duration: _reduceMotion
                    ? Duration.zero
                    : const Duration(milliseconds: 200),
                curve: _Motion.settle,
                padding: EdgeInsets.symmetric(
                    vertical: layoutSettings.paddingV * 0.6),
                decoration: BoxDecoration(
                  gradient: _showReceipts
                      ? LinearGradient(
                          colors: [_brandPrimary, _brandDark],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        )
                      : null,
                  color: _showReceipts ? null : Colors.white.withOpacity(0.07),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: _showReceipts
                        ? _brandPrimary
                        : Colors.white.withOpacity(0.15),
                    width: _showReceipts ? 2 : 1,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.12),
                      blurRadius: 8,
                      offset: Offset(0, 2),
                    ),
                  ],
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      Icons.receipt_long,
                      size: layoutSettings.actionIconDimension * 0.7,
                      color: _showReceipts ? Colors.white : _brandPrimary,
                    ),
                    SizedBox(width: layoutSettings.paddingH * 0.4),
                    Text(
                      'Receipts',
                      style: TextStyle(
                        fontSize: layoutSettings.actionTextSize,
                        fontWeight: FontWeight.w600,
                        color: _showReceipts
                            ? Colors.white
                            : Colors.white.withOpacity(0.8),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
          SizedBox(width: layoutSettings.paddingH * 0.6),
          Expanded(
            child: _Pressable(
              reduceMotion: _reduceMotion,
              pressedScale: 0.96,
              semanticsLabel: _showClaims ? 'Claims, shown' : 'Claims, hidden',
              semanticsHint: 'Toggles claims in the list',
              onTap: () {
                HapticFeedback.selectionClick();
                setState(() => _showClaims = !_showClaims);
              },
              child: AnimatedContainer(
                duration: _reduceMotion
                    ? Duration.zero
                    : const Duration(milliseconds: 200),
                curve: _Motion.settle,
                padding: EdgeInsets.symmetric(
                    vertical: layoutSettings.paddingV * 0.6),
                decoration: BoxDecoration(
                  gradient: _showClaims
                      ? LinearGradient(
                          colors: [_brandPrimary, _brandDark],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        )
                      : null,
                  color: _showClaims ? null : Colors.white.withOpacity(0.07),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: _showClaims
                        ? _brandPrimary
                        : Colors.white.withOpacity(0.15),
                    width: _showClaims ? 2 : 1,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.12),
                      blurRadius: 8,
                      offset: Offset(0, 2),
                    ),
                  ],
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      Icons.file_present,
                      size: layoutSettings.actionIconDimension * 0.7,
                      color: _showClaims ? Colors.white : _brandPrimary,
                    ),
                    SizedBox(width: layoutSettings.paddingH * 0.4),
                    Text(
                      'Claims',
                      style: TextStyle(
                        fontSize: layoutSettings.actionTextSize,
                        fontWeight: FontWeight.w600,
                        color: _showClaims
                            ? Colors.white
                            : Colors.white.withOpacity(0.8),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDeductibleHeader() {
    final progress =
        _deductible > 0 ? (_paid / _deductible).clamp(0.0, 1.0) : 0.0;
    final remaining = (_deductible - _paid).clamp(0.0, double.infinity);
    final canClaim = _paid >= _deductible;

    return Container(
      margin: EdgeInsets.symmetric(
          horizontal: layoutSettings.paddingH,
          vertical: layoutSettings.paddingV * 0.4),
      padding: EdgeInsets.all(layoutSettings.paddingH),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            Colors.white.withOpacity(0.08),
            Colors.white.withOpacity(0.03),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: canClaim
              ? joviMint.withOpacity(0.35)
              : Colors.white.withOpacity(0.12),
          width: canClaim ? 1.5 : 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.15),
            blurRadius: 15,
            offset: Offset(0, 5),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: EdgeInsets.all(layoutSettings.paddingH * 0.4),
                decoration: BoxDecoration(
                  color: canClaim
                      ? joviMint.withOpacity(0.15)
                      : _brandPrimary.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(
                  canClaim ? Icons.check_circle : Icons.trending_up,
                  color: canClaim ? joviMint : _brandPrimary,
                  size: layoutSettings.actionIconDimension,
                ),
              ),
              SizedBox(width: layoutSettings.paddingH * 0.6),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      canClaim ? 'Responsibility met' : 'Your responsibility',
                      style: TextStyle(
                        fontSize: layoutSettings.wideMode ? 17 : 15,
                        fontWeight: FontWeight.w600,
                        letterSpacing: -0.3,
                        color: Colors.white,
                      ),
                    ),
                    SizedBox(height: 4),
                    Text(
                      canClaim
                          ? 'You can now file claims for reimbursement.'
                          : 'Upload receipts to track your expenses',
                      style: TextStyle(
                        fontSize: layoutSettings.actionTextSize,
                        color: Colors.white.withOpacity(0.7),
                        fontWeight:
                            canClaim ? FontWeight.w600 : FontWeight.normal,
                      ),
                    ),
                    if (!canClaim)
                      Text(
                        '\$${remaining.toStringAsFixed(0)} remaining',
                        style: TextStyle(
                          fontSize: layoutSettings.actionTextSize - 1,
                          color: joviGold,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                  ],
                ),
              ),
              IconButton(
                icon: Icon(Icons.info_outline_rounded,
                    color: canClaim ? joviMint : _brandPrimary,
                    size: layoutSettings.actionIconDimension * 0.8),
                tooltip: 'About your responsibility',
                onPressed: () {
                  HapticFeedback.lightImpact();
                  showCupertinoDialog<void>(
                    context: context,
                    builder: (ctx) => CupertinoAlertDialog(
                      title: const Text('Your Responsibility'),
                      content: Padding(
                        padding: const EdgeInsets.only(top: 8),
                        child: Text(
                          'Total \$${_deductible.toStringAsFixed(2)}\n'
                          'Paid \$${_paid.toStringAsFixed(2)}\n'
                          'Remaining \$${remaining.toStringAsFixed(2)}\n\n'
                          '${canClaim ? 'You can file claims for reimbursement.' : 'Upload receipts to meet your responsibility, then file claims.'}',
                        ),
                      ),
                      actions: [
                        CupertinoDialogAction(
                          isDefaultAction: true,
                          onPressed: () => Navigator.of(ctx).pop(),
                          child: const Text('OK'),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ],
          ),
          SizedBox(height: layoutSettings.paddingV * 0.8),
          // Track measured with LayoutBuilder; r1 used screen width × 0.8,
          // which never matched the card's real inner width.
          Semantics(
            label:
                'Responsibility progress, ${(progress * 100).round()} percent',
            child: LayoutBuilder(
              builder: (context, constraints) => Stack(
                children: [
                  Container(
                    height: layoutSettings.wideMode ? 12 : 10,
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(10),
                    ),
                  ),
                  TweenAnimationBuilder<double>(
                    tween: Tween<double>(end: progress),
                    duration: _reduceMotion
                        ? Duration.zero
                        : const Duration(milliseconds: 600),
                    curve: _Motion.settle,
                    builder: (context, value, _) => Container(
                      height: layoutSettings.wideMode ? 12 : 10,
                      width: constraints.maxWidth * value,
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: canClaim
                              ? [joviMint, joviMintDark]
                              : [_brandPrimary, _brandDark],
                          begin: Alignment.centerLeft,
                          end: Alignment.centerRight,
                        ),
                        borderRadius: BorderRadius.circular(10),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          SizedBox(height: layoutSettings.paddingV * 0.6),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                '\$${_paid.toStringAsFixed(0)} paid',
                style: TextStyle(
                  fontSize: layoutSettings.actionTextSize,
                  fontWeight: FontWeight.w600,
                  color: canClaim ? joviMint : _brandPrimary,
                ),
              ),
              Text(
                '${(progress * 100).round()}%',
                style: TextStyle(
                  fontSize: layoutSettings.actionTextSize,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
              ),
              Text(
                '\$${_deductible.toStringAsFixed(0)} total',
                style: TextStyle(
                  fontSize: layoutSettings.actionTextSize,
                  fontWeight: FontWeight.w600,
                  color: Colors.white.withOpacity(0.8),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    final canClaim = _paid >= _deductible;

    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            padding: EdgeInsets.all(layoutSettings.paddingH),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.08),
              shape: BoxShape.circle,
            ),
            child: Icon(
              Icons.folder_open,
              size: layoutSettings.actionIconDimension + 20,
              color: Colors.white.withOpacity(0.3),
            ),
          ),
          SizedBox(height: layoutSettings.paddingV * 0.8),
          Text(
            'No ${canClaim ? "claims" : "receipts"} yet',
            style: TextStyle(
              fontSize: layoutSettings.wideMode ? 16 : 14,
              fontWeight: FontWeight.w600,
              color: Colors.white.withOpacity(0.7),
            ),
          ),
          SizedBox(height: layoutSettings.paddingV * 0.4),
          Text(
            canClaim
                ? 'File a claim to get reimbursed'
                : 'Upload receipts to track your responsibility',
            style: TextStyle(
              fontSize: layoutSettings.actionTextSize,
              color: Colors.white.withOpacity(0.5),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHistoryList() {
    if (_selectedMemberId == null) {
      return Center(
        child: Text(
          'Select a member above',
          style: TextStyle(
            color: Colors.white.withOpacity(0.7),
            fontSize: layoutSettings.actionTextSize + 1,
          ),
        ),
      );
    }

    return StreamBuilder<QuerySnapshot>(
      stream: ClaimService()
          .claimsRef
          .where('memberId', isEqualTo: _selectedMemberId)
          .snapshots(),
      builder: (ctx, snap) {
        if (snap.hasError) {
          return Center(
            child: Text(
              'Error loading history:\n${snap.error}',
              textAlign: TextAlign.center,
              style: TextStyle(color: Color(0xFFFF6B6B)),
            ),
          );
        }
        if (!snap.hasData) {
          return Center(
            child: CircularProgressIndicator(color: _brandPrimary),
          );
        }

        final docs = snap.data!.docs;
        final List<MapEntry<QueryDocumentSnapshot, DateTime>> datedDocs =
            docs.map((d) {
          final dataMap = d.data() as Map<String, dynamic>;
          final timestamp = (dataMap[ClaimFields.date] as Timestamp).toDate();
          return MapEntry(d, timestamp);
        }).toList();

        datedDocs.sort((a, b) => b.value.compareTo(a.value));

        final filtered = datedDocs
            .where((entry) {
              final d = entry.key;
              if (_pendingDeletes.contains(d.id)) return false;
              final dataMap = d.data() as Map<String, dynamic>;
              final showType = dataMap[ClaimFields.type] == 'receipt'
                  ? _showReceipts
                  : _showClaims;
              final combined = dataMap.values.join(' ').toLowerCase();
              final matchesSearch = combined.contains(_searchTerm);
              return showType && matchesSearch;
            })
            .map((entry) => entry.key)
            .toList();

        if (filtered.isEmpty) {
          return _buildEmptyState();
        }

        final groups = <String, List<QueryDocumentSnapshot>>{};
        for (var d in filtered) {
          final dataMap = d.data() as Map<String, dynamic>;
          final date = (dataMap[ClaimFields.date] as Timestamp).toDate();
          final key = DateFormat('MMMM yyyy').format(date);
          groups.putIfAbsent(key, () => []).add(d);
        }

        return RefreshIndicator(
          color: _brandPrimary,
          onRefresh: () async {
            // The list is a live Firestore stream; just give the indicator
            // a beat so the gesture feels acknowledged.
            await Future.delayed(const Duration(milliseconds: 400));
          },
          child: ListView(
            padding: EdgeInsets.only(bottom: 100),
            children: groups.entries.expand((e) {
              return [
                Padding(
                  padding: EdgeInsets.fromLTRB(
                      layoutSettings.paddingH + 4,
                      layoutSettings.paddingV * 0.8,
                      layoutSettings.paddingH + 4,
                      layoutSettings.paddingV * 0.4),
                  child: Text(
                    e.key,
                    style: TextStyle(
                      fontSize: layoutSettings.actionTextSize,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                      letterSpacing: 0.5,
                    ),
                  ),
                ),
                ...e.value.map((d) {
                  final dataMap = d.data() as Map<String, dynamic>;
                  final amt = (dataMap[ClaimFields.amount] as num).toDouble();
                  final dt = (dataMap[ClaimFields.date] as Timestamp).toDate();
                  final isRec = dataMap[ClaimFields.type] == 'receipt';
                  final String photoUrlStr =
                      (dataMap[ClaimFields.photoUrl] as String);
                  final status =
                      (dataMap[ClaimFields.status] as String?) ?? 'Pending';
                  final paymentProcessed =
                      (dataMap[ClaimFields.paymentProcessed] as bool?) ?? false;
                  final correspondencesData =
                      dataMap[ClaimFields.correspondences] as List<dynamic>? ??
                          [];
                  final correspondenceCount = correspondencesData.length;

                  Color statusColor = _getStatusColor(status);
                  IconData statusIcon;
                  if (status.toLowerCase() == 'approved') {
                    statusIcon = Icons.check_circle;
                  } else if (status.toLowerCase() == 'denied') {
                    statusIcon = Icons.cancel;
                  } else if (paymentProcessed) {
                    statusIcon = Icons.credit_card;
                  } else {
                    statusIcon = Icons.schedule;
                  }

                  final canDelete = canDeleteItem(dataMap);
                  return Dismissible(
                    key: ValueKey(d.id),
                    // Past the 60-minute window the row simply doesn't
                    // swipe, instead of swiping and then refusing.
                    direction: canDelete
                        ? DismissDirection.endToStart
                        : DismissDirection.none,
                    confirmDismiss: (direction) async {
                      return await showDeleteConfirmation(
                          context, isRec ? 'receipt' : 'claim', canDelete);
                    },
                    onDismissed: (_) {
                      HapticFeedback.mediumImpact();
                      // Hide the row synchronously so the dismissed widget
                      // is out of the tree before the stream catches up
                      // (otherwise Flutter asserts on it).
                      setState(() => _pendingDeletes.add(d.id));
                      ClaimService().deleteEntry(d.id).catchError((e) {
                        if (!mounted) return;
                        setState(() => _pendingDeletes.remove(d.id));
                        _showSnackBar('Couldn’t delete. Please try again.',
                            isError: true);
                      });
                    },
                    background: Container(
                      margin: EdgeInsets.symmetric(
                          horizontal: layoutSettings.paddingH,
                          vertical: layoutSettings.paddingV * 0.3),
                      decoration: BoxDecoration(
                        color: Color(0xFFE53935),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      alignment: Alignment.centerRight,
                      padding: EdgeInsets.symmetric(
                          horizontal: layoutSettings.paddingH),
                      child: Icon(Icons.delete,
                          color: Colors.white,
                          size: layoutSettings.actionIconDimension),
                    ),
                    child: Container(
                      margin: EdgeInsets.symmetric(
                          horizontal: layoutSettings.paddingH,
                          vertical: layoutSettings.paddingV * 0.3),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.07),
                        borderRadius: BorderRadius.circular(12),
                        border:
                            Border.all(color: Colors.white.withOpacity(0.1)),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withOpacity(0.15),
                            blurRadius: 12,
                            offset: Offset(0, 4),
                          ),
                        ],
                      ),
                      child: _Pressable(
                        reduceMotion: _reduceMotion,
                        pressedScale: 0.98,
                        semanticsLabel:
                            '${isRec ? 'Receipt' : 'Claim'}, \$${amt.toStringAsFixed(2)}, ${DateFormat.yMMMd().format(dt)}, $status',
                        semanticsHint: 'Shows details',
                        onTap: () {
                          HapticFeedback.lightImpact();
                          if (isRec) {
                            _showReceiptDetail(d);
                          } else {
                            _showClaimDetail(d);
                          }
                        },
                        child: Padding(
                            padding:
                                EdgeInsets.all(layoutSettings.paddingH * 0.8),
                            child: Row(
                              children: [
                                Container(
                                  width: layoutSettings.actionIconDimension * 2,
                                  height:
                                      layoutSettings.actionIconDimension * 2,
                                  decoration: BoxDecoration(
                                    gradient: photoUrlStr.isNotEmpty
                                        ? null
                                        : LinearGradient(
                                            colors: [
                                              _brandPrimary.withOpacity(0.18),
                                              _brandDark.withOpacity(0.08)
                                            ],
                                            begin: Alignment.topLeft,
                                            end: Alignment.bottomRight,
                                          ),
                                    borderRadius: BorderRadius.circular(12),
                                    image: photoUrlStr.isNotEmpty
                                        ? DecorationImage(
                                            image: NetworkImage(photoUrlStr),
                                            fit: BoxFit.cover,
                                          )
                                        : null,
                                  ),
                                  child: photoUrlStr.isEmpty
                                      ? Icon(
                                          isRec
                                              ? Icons.receipt_long
                                              : Icons.file_present,
                                          color: _brandPrimary,
                                          size: layoutSettings
                                              .actionIconDimension,
                                        )
                                      : null,
                                ),
                                SizedBox(width: layoutSettings.paddingH * 0.8),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Row(
                                        children: [
                                          Expanded(
                                            child: Text(
                                              isRec ? 'Receipt' : 'Claim',
                                              style: TextStyle(
                                                fontSize:
                                                    layoutSettings.wideMode
                                                        ? 16
                                                        : 14,
                                                fontWeight: FontWeight.w600,
                                                color: Colors.white,
                                              ),
                                            ),
                                          ),
                                          if (correspondenceCount > 0) ...[
                                            Container(
                                              padding: EdgeInsets.symmetric(
                                                  horizontal: 6, vertical: 2),
                                              margin: EdgeInsets.only(right: 8),
                                              decoration: BoxDecoration(
                                                color:
                                                    joviMint.withOpacity(0.15),
                                                borderRadius:
                                                    BorderRadius.circular(10),
                                                border: Border.all(
                                                    color: joviMint
                                                        .withOpacity(0.3)),
                                              ),
                                              child: Row(
                                                mainAxisSize: MainAxisSize.min,
                                                children: [
                                                  Icon(
                                                    Icons.attach_file,
                                                    size: 12,
                                                    color: joviMint,
                                                  ),
                                                  SizedBox(width: 2),
                                                  Text(
                                                    '$correspondenceCount',
                                                    style: TextStyle(
                                                      fontSize: 10,
                                                      fontWeight:
                                                          FontWeight.w600,
                                                      color: joviMint,
                                                    ),
                                                  ),
                                                ],
                                              ),
                                            ),
                                          ],
                                          Container(
                                            padding: EdgeInsets.symmetric(
                                                horizontal:
                                                    layoutSettings.paddingH *
                                                        0.5,
                                                vertical: 4),
                                            decoration: BoxDecoration(
                                              color:
                                                  statusColor.withOpacity(0.15),
                                              borderRadius:
                                                  BorderRadius.circular(20),
                                              border: Border.all(
                                                  color: statusColor
                                                      .withOpacity(0.3)),
                                            ),
                                            child: Row(
                                              mainAxisSize: MainAxisSize.min,
                                              children: [
                                                Icon(
                                                  statusIcon,
                                                  size: layoutSettings
                                                          .actionIconDimension *
                                                      0.5,
                                                  color: statusColor,
                                                ),
                                                SizedBox(width: 4),
                                                Text(
                                                  status,
                                                  style: TextStyle(
                                                    fontSize: layoutSettings
                                                            .actionTextSize -
                                                        1,
                                                    fontWeight: FontWeight.w600,
                                                    color: statusColor,
                                                  ),
                                                ),
                                              ],
                                            ),
                                          ),
                                        ],
                                      ),
                                      SizedBox(
                                          height:
                                              layoutSettings.paddingV * 0.4),
                                      Text(
                                        '\$${amt.toStringAsFixed(2)}',
                                        style: TextStyle(
                                          fontSize:
                                              layoutSettings.wideMode ? 20 : 18,
                                          fontWeight: FontWeight.w700,
                                          letterSpacing: -0.3,
                                          fontFeatures: const [
                                            ui_dart.FontFeature.tabularFigures()
                                          ],
                                          color: _brandPrimary,
                                        ),
                                      ),
                                      SizedBox(height: 4),
                                      Row(
                                        children: [
                                          Icon(
                                            Icons.calendar_today,
                                            size: layoutSettings
                                                    .actionIconDimension *
                                                0.5,
                                            color:
                                                Colors.white.withOpacity(0.5),
                                          ),
                                          SizedBox(width: 4),
                                          Text(
                                            DateFormat.yMMMd().format(dt),
                                            style: TextStyle(
                                              fontSize:
                                                  layoutSettings.actionTextSize,
                                              color:
                                                  Colors.white.withOpacity(0.5),
                                            ),
                                          ),
                                          if (paymentProcessed && !isRec) ...[
                                            SizedBox(
                                                width: layoutSettings.paddingH *
                                                    0.6),
                                            Icon(
                                              Icons.paid,
                                              size: layoutSettings
                                                      .actionIconDimension *
                                                  0.5,
                                              color: joviMint,
                                            ),
                                            SizedBox(width: 4),
                                            Text(
                                              'Reimbursed',
                                              style: TextStyle(
                                                fontSize: layoutSettings
                                                        .actionTextSize -
                                                    1,
                                                fontWeight: FontWeight.w600,
                                                color: joviMint,
                                              ),
                                            ),
                                          ],
                                        ],
                                      ),
                                    ],
                                  ),
                                ),
                                Icon(
                                  Icons.chevron_right,
                                  color: Colors.white.withOpacity(0.3),
                                  size:
                                      layoutSettings.actionIconDimension * 0.7,
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                  );
                }).toList(),
              ];
            }).toList(),
          ),
        );
      },
    );
  }

  Widget _buildActionButton() {
    final canClaim = _paid >= _deductible;

    return Container(
      margin: EdgeInsets.all(layoutSettings.paddingH),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [_brandPrimary, _brandDark],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: _brandPrimary.withOpacity(0.35),
            blurRadius: 20,
            offset: Offset(0, 10),
          ),
        ],
      ),
      child: _Pressable(
        reduceMotion: _reduceMotion,
        pressedScale: 0.975,
        semanticsLabel: canClaim ? 'File a claim' : 'Upload a receipt',
        onTap: () {
          HapticFeedback.mediumImpact();
          canClaim ? _showClaimForm() : _showReceiptForm();
        },
        child: Container(
            padding:
                EdgeInsets.symmetric(vertical: layoutSettings.paddingV * 0.8),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  canClaim ? Icons.file_present : Icons.receipt_long,
                  color: Colors.white,
                  size: layoutSettings.actionIconDimension,
                ),
                SizedBox(width: layoutSettings.paddingH * 0.6),
                Column(
                  children: [
                    Text(
                      canClaim ? 'File a Claim' : 'Upload Receipt',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 17,
                        fontWeight: FontWeight.w600,
                        letterSpacing: -0.3,
                      ),
                    ),
                    if (canClaim)
                      Text(
                        'Get reimbursed',
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.9),
                          fontSize: layoutSettings.actionTextSize - 1,
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

  @override
  Widget build(BuildContext context) {
    final canClaim = _paid >= _deductible;
    final pageTitle = canClaim ? 'File a Claim' : 'Upload Receipt';

    return wrapWithConstraints(
      child: LayoutBuilder(
        builder: (context, constraints) {
          return AnnotatedRegion<SystemUiOverlayStyle>(
            value: SystemUiOverlayStyle.light.copyWith(
              statusBarColor: Colors.transparent,
              statusBarIconBrightness: Brightness.light,
            ),
            child: Container(
              width: widget.width,
              height: widget.height,
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [joviNavy, joviNavy, joviNavyDark],
                ),
              ),
              child: Scaffold(
                backgroundColor: Colors.transparent,
                body: Column(
                  children: [
                    // Coral gradient header
                    Container(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: [_brandPrimary, _brandDark],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withOpacity(0.15),
                            blurRadius: 10,
                            offset: Offset(0, 2),
                          ),
                        ],
                      ),
                      child: SafeArea(
                        bottom: false,
                        child: Container(
                          padding: EdgeInsets.symmetric(
                              horizontal: layoutSettings.paddingH * 0.8,
                              vertical: layoutSettings.paddingV * 0.8),
                          child: Row(
                            children: [
                              _Pressable(
                                reduceMotion: _reduceMotion,
                                pressedScale: 0.92,
                                semanticsLabel: 'Back',
                                onTap: () {
                                  HapticFeedback.lightImpact();
                                  Navigator.of(context).maybePop();
                                },
                                child: Container(
                                  width: 44,
                                  height: 44,
                                  decoration: BoxDecoration(
                                    color: Colors.white.withOpacity(0.2),
                                    borderRadius: BorderRadius.circular(14),
                                  ),
                                  child: const Icon(
                                    Icons.arrow_back_ios_new_rounded,
                                    color: Colors.white,
                                    size: 18,
                                  ),
                                ),
                              ),
                              Expanded(
                                child: Column(
                                  children: [
                                    Text(
                                      pageTitle,
                                      textAlign: TextAlign.center,
                                      style: const TextStyle(
                                        fontSize: 17,
                                        fontWeight: FontWeight.w600,
                                        color: Colors.white,
                                        letterSpacing: -0.4,
                                      ),
                                    ),
                                    if (canClaim)
                                      Text(
                                        'Responsibility met',
                                        style: TextStyle(
                                          fontSize:
                                              layoutSettings.actionTextSize - 1,
                                          color: Colors.white.withOpacity(0.9),
                                        ),
                                      ),
                                  ],
                                ),
                              ),
                              const SizedBox(width: 44),
                            ],
                          ),
                        ),
                      ),
                    ),

                    Expanded(
                      child: Column(
                        children: [
                          _buildMemberSelector(),
                          _buildSearchField(),
                          _buildFilterChips(),
                          _buildDeductibleHeader(),
                          Expanded(child: _buildHistoryList()),
                          _buildActionButton(),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
