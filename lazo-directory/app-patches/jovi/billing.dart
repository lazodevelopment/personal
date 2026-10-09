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
import 'dart:typed_data';
import 'dart:ui' as ui_dart;

import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:cloud_functions/cloud_functions.dart';
import 'package:intl/intl.dart';
import 'package:pdf/pdf.dart' as pw_pdf;
import 'package:pdf/widgets.dart' as pw;
import 'package:printing/printing.dart';

// -----------------------------------------------------------------------
// JOVI HEALTH — BILLING WIDGET
// Version: 2026.09.22-r2 (Apple HIG pass: press feedback, painted glass,
//          Cupertino confirms, navy toasts, title-case labels).
//          Card entry still collects the raw PAN in-app; replace with
//          Zoho Payments hosted/tokenized entry before launch.
// r1:      2026.04.21
// Build: JC-BILLING-0922-002
//
// Gives members a single place to:
//   - See their current plan total and next bill date
//   - See the card on file (brand + last4 + expiry)
//   - Update the card on file (collects raw PAN client-side, same pattern
//     as onboarding; a new Cloud Function handles tokenization)
//   - Browse past transactions (membership, pet addon proration,
//     renewals, refunds)
//   - Download individual receipts as PDF
//   - Download a monthly statement as PDF
//   - See and act on a failed payment (blocking banner until resolved)
//
// INTEGRATION WITH OTHER WIDGETS:
//   - Reads payarcCustomerId from user doc (same field QuotePayment and
//     OnboardingUpdate write). Updating the card here rewrites that
//     field, so next time onboarding update opens, the new card is
//     already live.
//   - Reads card metadata (cardLast4, cardBrand, cardExpMonth,
//     cardExpYear) from user doc. These fields are NEW in r1 of this
//     widget — prior widget versions don't write them. When a user
//     first opens this widget with no metadata on file, we show
//     "Card on file" with no last4 and ask them to update.
//   - Reads the billing_history subcollection (used by Pet Profiles r2)
//     AND a new transactions subcollection. New transactions go to
//     `transactions`; the merged view covers both for backward
//     compatibility. Pet Profiles r3 will migrate to `transactions`;
//     the dual-read here stays as the bridge.
//   - Writes card-metadata fields on successful card update. When
//     OnboardingUpdate / QuotePayment are next revved they should write
//     the same field names.
//
// CLOUD FUNCTIONS USED:
//   - `updatePaymentMethod` (NEW, does not exist yet — ships with the
//     new processor)
//   - `deletePaymentMethod` (NEW, does not exist yet)
//   - `retryFailedCharge` (NEW, does not exist yet)
// All three follow the graceful-stub pattern from Pet Profiles r2:
// FirebaseFunctionsException with code `not-found` or `unavailable`
// surfaces a clear "payment system being upgraded" message. When the
// backend lands, no client changes are needed.
//
// BLOCK BEFORE PRODUCTION:
//   - Implement `updatePaymentMethod` CF. Contract documented on
//     _callUpdatePaymentMethod.
//   - Implement `deletePaymentMethod` CF. Contract documented on
//     _callDeletePaymentMethod.
//   - Implement `retryFailedCharge` CF. Contract documented on
//     _callRetryFailedCharge.
//   - Patch Quote Payment widget to write cardLast4/cardBrand/
//     cardExpMonth/cardExpYear on successful charge (currently it
//     doesn't — we start clean from here forward).
//   - Patch Onboarding Update widget to write the same fields when
//     updating a card.
//   - Pet Profiles r3 patch to write to `transactions` subcollection
//     instead of `billing_history`.
//   - Decide what sets `lastChargeStatus` on the user doc. This
//     widget READS it (to show the failed-payment banner) but doesn't
//     write it — backend should set it via the charge CFs.
//   - Firestore rules for users/{uid}/transactions (read/write own,
//     no public).
//   - Keep an eye on the promo-code key drift between QuotePayment
//     ("WELCOME10!") and OnboardingUpdate ("WELCOME10") — billing
//     widget doesn't deal with promos, but it's a known bug elsewhere.
// -----------------------------------------------------------------------

// =======================================================================
// JOVI BRAND COLORS
// Copied verbatim from Quote Payment / Onboarding Update so brand stays
// consistent. Kept as private file-scope constants so the widget is
// self-contained for FF paste-in.
// =======================================================================

const Color _joviCoral = Color(0xFFFF6B4A);
const Color _joviCoralLight = Color(0xFFFF8F73);
const Color _joviCoralDark = Color(0xFFE5583A);
const Color _joviNavy = Color(0xFF1A2744);
const Color _joviNavyDark = Color(0xFF0F1A2E);
const Color _joviNavyLight = Color(0xFF243352);
const Color _joviNavyMid = Color(0xFF1F2B47);
const Color _joviMint = Color(0xFF00D4AA);
const Color _joviMintDark = Color(0xFF00B894);
const Color _joviGold = Color(0xFFFFD166);
const Color _joviGoldDark = Color(0xFFF4A41E);
const Color _joviErrorRed = Color(0xFFE53935);
const Color _joviWarmWhite = Color(0xFFFFF8F5);

// White-on-navy text helpers (matches onboarding's kTextDark/Medium/Light)
const Color _textPrimary = Colors.white;
const Color _textSecondary = Color(0xB3FFFFFF); // white @ 70%
const Color _textTertiary = Color(0x80FFFFFF); // white @ 50%
const Color _textMuted = Color(0x4DFFFFFF); // white @ 30%

// =======================================================================
// FIELD NAMES
// Kept as constants so we never drift from onboarding / update. Any
// change here needs a matching change in QuotePayment + OnboardingUpdate.
// =======================================================================

/// payarcCustomerId on users/{uid}. Written by QuotePayment on successful
/// charge, read + rewritten by OnboardingUpdate. Billing widget updates
/// via the new updatePaymentMethod CF.
const String _fieldPayarcCustomerId = 'payarcCustomerId';

/// NEW in billing r1. Not yet written by QuotePayment / OnboardingUpdate.
/// Billing widget writes these on successful card update. Widget
/// tolerates missing fields (shows generic "Card on file").
const String _fieldCardLast4 = 'cardLast4';
const String _fieldCardBrand = 'cardBrand';
const String _fieldCardExpMonth = 'cardExpMonth';
const String _fieldCardExpYear = 'cardExpYear';
const String _fieldCardUpdatedAt = 'cardUpdatedAt';

/// Renewal / billing cycle anchor. Written by QuotePayment on initial
/// save and on renewals. This widget uses `renew.day` the same way
/// Pet Profiles r2 does — the day of month is the monthly billing
/// anniversary.
const String _fieldRenew = 'renew';
const String _fieldLastPaymentDate = 'lastPaymentDate';
const String _fieldMembershipStartDate = 'membershipStartDate';
const String _fieldIsActive = 'isActive';

/// Plan totals. totalPremium = health only, petTotalPremium = pets only,
/// grandTotal (written by OnboardingUpdate) = after discounts. Billing
/// widget prefers grandTotal when present, falls back to
/// totalPremium + petTotalPremium.
const String _fieldTotalPremium = 'totalPremium';
const String _fieldPetTotalPremium = 'petTotalPremium';
const String _fieldGrandTotal = 'grandTotal';

/// Failed-payment signal. NOT currently set by any widget — backend
/// needs to set this after a failed charge via the CFs. Possible
/// values: 'ok', 'failed', 'past_due', 'pending'. Anything other than
/// 'ok' / null triggers the blocking banner.
const String _fieldLastChargeStatus = 'lastChargeStatus';
const String _fieldLastChargeError = 'lastChargeError';
const String _fieldLastChargeAttemptAt = 'lastChargeAttemptAt';
const String _fieldLastChargeAmount = 'lastChargeAmount';

// =======================================================================
// CLOUD FUNCTION NAMES
// All three are NEW and don't exist on the backend yet. Gracefully stub
// until the new processor ships (same pattern as Pet Profiles r2's
// `chargePetAddon`). When the CFs land, no client changes are needed
// as long as the contracts documented on the call sites are honored.
// =======================================================================

// 2026-09-22: the app is moving to Zoho Payments. These three functions
// do not exist yet; when they land they must accept a Zoho token, not a
// raw card number, and the `_UpdateCardSheet` below should be replaced
// by Zoho's hosted card entry so the PAN never enters the app.
const String _cfUpdatePaymentMethod = 'updatePaymentMethod';
const String _cfDeletePaymentMethod = 'deletePaymentMethod';
const String _cfRetryFailedCharge = 'retryFailedCharge';

// =======================================================================
// LOGGING HELPERS
// No-op stubs. Swap for Firebase Analytics / Crashlytics when ready.
// =======================================================================

void _log(String msg) {
  // ignore: avoid_print
  debugPrint('[Billing] $msg');
}

void _logError(String msg, Object? err) {
  // ignore: avoid_print
  debugPrint('[Billing][ERROR] $msg: $err');
}

void _analytics(String event, [Map<String, String?>? props]) {
  if (props == null || props.isEmpty) {
    _log('analytics: $event');
  } else {
    _log('analytics: $event $props');
  }
}

// =======================================================================
// TRANSACTION ENUMS
// =======================================================================

/// Category of a transaction. Used for the filter chips at the top of the
/// history list. `billing_history` (written by Pet Profiles r2) uses a
/// `type` string field; we translate known values to this enum and fall
/// back to `other` for anything unrecognized.
enum TxType {
  membershipMonthly, // regular monthly membership charge
  membershipRenewal, // annual renewal
  petAddonProration, // mid-cycle pet addon (Pet Profiles r2)
  petAddonMonthly, // pet monthly charge
  refund, // refund issued
  adjustment, // manual credit / debit
  other,
}

String _txTypeLabel(TxType t) {
  switch (t) {
    case TxType.membershipMonthly:
      return 'Monthly membership';
    case TxType.membershipRenewal:
      return 'Annual renewal';
    case TxType.petAddonProration:
      return 'Pet added (prorated)';
    case TxType.petAddonMonthly:
      return 'Pet monthly';
    case TxType.refund:
      return 'Refund';
    case TxType.adjustment:
      return 'Adjustment';
    case TxType.other:
      return 'Charge';
  }
}

IconData _txTypeIcon(TxType t) {
  switch (t) {
    case TxType.membershipMonthly:
      return Icons.health_and_safety_outlined;
    case TxType.membershipRenewal:
      return Icons.refresh_rounded;
    case TxType.petAddonProration:
    case TxType.petAddonMonthly:
      return Icons.pets_outlined;
    case TxType.refund:
      return Icons.undo_rounded;
    case TxType.adjustment:
      return Icons.tune_rounded;
    case TxType.other:
      return Icons.receipt_long_outlined;
  }
}

/// Parse the `type` string stored on transaction/billing_history docs.
TxType _txTypeParse(String? raw) {
  if (raw == null) return TxType.other;
  switch (raw.toLowerCase().trim()) {
    case 'membership_monthly':
    case 'membership':
    case 'monthly':
      return TxType.membershipMonthly;
    case 'membership_renewal':
    case 'renewal':
    case 'annual':
      return TxType.membershipRenewal;
    case 'pet_addon_proration':
    case 'pet_proration':
    case 'pet_addon':
      return TxType.petAddonProration;
    case 'pet_monthly':
      return TxType.petAddonMonthly;
    case 'refund':
      return TxType.refund;
    case 'adjustment':
    case 'credit':
    case 'debit':
      return TxType.adjustment;
    default:
      return TxType.other;
  }
}

String _txTypeSerialize(TxType t) {
  switch (t) {
    case TxType.membershipMonthly:
      return 'membership_monthly';
    case TxType.membershipRenewal:
      return 'membership_renewal';
    case TxType.petAddonProration:
      return 'pet_addon_proration';
    case TxType.petAddonMonthly:
      return 'pet_monthly';
    case TxType.refund:
      return 'refund';
    case TxType.adjustment:
      return 'adjustment';
    case TxType.other:
      return 'other';
  }
}

/// Settlement status of a transaction.
enum TxStatus {
  succeeded, // charged and cleared
  pending, // submitted, awaiting processor
  failed, // declined / errored
  refunded, // later reversed
  voided, // cancelled before settlement
}

String _txStatusLabel(TxStatus s) {
  switch (s) {
    case TxStatus.succeeded:
      return 'Paid';
    case TxStatus.pending:
      return 'Pending';
    case TxStatus.failed:
      return 'Failed';
    case TxStatus.refunded:
      return 'Refunded';
    case TxStatus.voided:
      return 'Voided';
  }
}

Color _txStatusColor(TxStatus s) {
  switch (s) {
    case TxStatus.succeeded:
      return _joviMint;
    case TxStatus.pending:
      return _joviGold;
    case TxStatus.failed:
      return _joviErrorRed;
    case TxStatus.refunded:
      return _joviCoralLight;
    case TxStatus.voided:
      return _textTertiary;
  }
}

TxStatus _txStatusParse(String? raw) {
  if (raw == null) return TxStatus.succeeded;
  switch (raw.toLowerCase().trim()) {
    case 'succeeded':
    case 'success':
    case 'paid':
    case 'completed':
      return TxStatus.succeeded;
    case 'pending':
    case 'processing':
      return TxStatus.pending;
    case 'failed':
    case 'declined':
    case 'error':
      return TxStatus.failed;
    case 'refunded':
      return TxStatus.refunded;
    case 'voided':
    case 'cancelled':
    case 'canceled':
      return TxStatus.voided;
    default:
      return TxStatus.succeeded;
  }
}

String _txStatusSerialize(TxStatus s) {
  switch (s) {
    case TxStatus.succeeded:
      return 'succeeded';
    case TxStatus.pending:
      return 'pending';
    case TxStatus.failed:
      return 'failed';
    case TxStatus.refunded:
      return 'refunded';
    case TxStatus.voided:
      return 'voided';
  }
}

// =======================================================================
// CARD BRAND DETECTION
// Used to display the right brand icon on the card-on-file tile. We also
// store the detected brand on user doc so we don't have to re-detect on
// every render. Detection is done from the first few digits of the PAN
// (same rules processors use). If we can't determine the brand, we
// store 'Unknown' and fall back to a generic icon.
// =======================================================================

enum CardBrand {
  ach,
  visa,
  mastercard,
  amex,
  discover,
  diners,
  jcb,
  unionpay,
  unknown,
}

String _cardBrandLabel(CardBrand b) {
  switch (b) {
    case CardBrand.visa:
      return 'Visa';
    case CardBrand.mastercard:
      return 'Mastercard';
    case CardBrand.amex:
      return 'Amex';
    case CardBrand.discover:
      return 'Discover';
    case CardBrand.diners:
      return 'Diners Club';
    case CardBrand.jcb:
      return 'JCB';
    case CardBrand.unionpay:
      return 'UnionPay';
    case CardBrand.ach:
      return 'Bank account';
    case CardBrand.unknown:
      return 'Card';
  }
}

CardBrand _cardBrandParse(String? raw) {
  if (raw == null) return CardBrand.unknown;
  switch (raw.toLowerCase().trim()) {
    case 'ach':
    case 'bank':
    case 'bank_account':
      return CardBrand.ach;
    case 'visa':
      return CardBrand.visa;
    case 'mastercard':
    case 'master':
    case 'mc':
      return CardBrand.mastercard;
    case 'amex':
    case 'american_express':
    case 'american express':
      return CardBrand.amex;
    case 'discover':
      return CardBrand.discover;
    case 'diners':
    case 'diners_club':
    case 'diners club':
      return CardBrand.diners;
    case 'jcb':
      return CardBrand.jcb;
    case 'unionpay':
    case 'union_pay':
      return CardBrand.unionpay;
    default:
      return CardBrand.unknown;
  }
}

String _cardBrandSerialize(CardBrand b) {
  switch (b) {
    case CardBrand.ach:
      return 'ach';
    case CardBrand.visa:
      return 'visa';
    case CardBrand.mastercard:
      return 'mastercard';
    case CardBrand.amex:
      return 'amex';
    case CardBrand.discover:
      return 'discover';
    case CardBrand.diners:
      return 'diners';
    case CardBrand.jcb:
      return 'jcb';
    case CardBrand.unionpay:
      return 'unionpay';
    case CardBrand.unknown:
      return 'unknown';
  }
}

/// Detect card brand from the raw PAN. Matches the standard BIN ranges
/// most processors use. Input is digits-only; callers should strip any
/// spaces / dashes first.
CardBrand detectCardBrand(String digitsOnlyPan) {
  if (digitsOnlyPan.isEmpty) return CardBrand.unknown;
  // Order matters: more specific prefixes first.
  if (digitsOnlyPan.startsWith('4')) return CardBrand.visa;
  if (RegExp(r'^(34|37)').hasMatch(digitsOnlyPan)) return CardBrand.amex;
  if (RegExp(r'^(50|5[6-9]|6[0-9])').hasMatch(digitsOnlyPan) &&
      digitsOnlyPan.startsWith('6')) {
    // Maestro/Discover ambiguity — treat most 6xxx as Discover for US
    if (RegExp(r'^(6011|65|64[4-9])').hasMatch(digitsOnlyPan)) {
      return CardBrand.discover;
    }
  }
  if (RegExp(r'^(6011|65|64[4-9])').hasMatch(digitsOnlyPan)) {
    return CardBrand.discover;
  }
  // Mastercard: 51-55 or 2221-2720
  if (RegExp(r'^5[1-5]').hasMatch(digitsOnlyPan)) return CardBrand.mastercard;
  if (digitsOnlyPan.length >= 4) {
    final first4 = int.tryParse(digitsOnlyPan.substring(0, 4)) ?? 0;
    if (first4 >= 2221 && first4 <= 2720) return CardBrand.mastercard;
  }
  if (RegExp(r'^(36|38|30[0-5])').hasMatch(digitsOnlyPan)) {
    return CardBrand.diners;
  }
  if (RegExp(r'^35(2[89]|[3-8][0-9])').hasMatch(digitsOnlyPan)) {
    return CardBrand.jcb;
  }
  if (RegExp(r'^62').hasMatch(digitsOnlyPan)) return CardBrand.unionpay;
  return CardBrand.unknown;
}
// =======================================================================
// CARD ON FILE
// Lightweight model of the saved card. Reads from user doc fields
// (cardLast4, cardBrand, cardExpMonth, cardExpYear, cardUpdatedAt).
// If payarcCustomerId is set but the metadata fields aren't, we return
// a model with hasMetadata == false so the UI can show "Card on file"
// without a last4.
// =======================================================================

class _CardOnFile {
  final String? payarcCustomerId;
  final String? last4;
  final CardBrand brand;
  final int? expMonth;
  final int? expYear;
  final DateTime? updatedAt;

  const _CardOnFile({
    this.payarcCustomerId,
    this.last4,
    this.brand = CardBrand.unknown,
    this.expMonth,
    this.expYear,
    this.updatedAt,
  });

  /// True when we have a saved customer on file. Doesn't imply we have
  /// display metadata — use hasMetadata for that.
  bool get hasCard => payarcCustomerId != null && payarcCustomerId!.isNotEmpty;

  /// True when we have last4 + brand + expiry to show on the tile.
  bool get hasMetadata => brand == CardBrand.ach
      ? (last4 != null && last4!.isNotEmpty)
      : (last4 != null &&
          last4!.isNotEmpty &&
          brand != CardBrand.unknown &&
          expMonth != null &&
          expYear != null);

  /// True when the saved card is past its expiry date (today).
  bool get isExpired {
    if (expMonth == null || expYear == null) return false;
    final now = DateTime.now();
    // Expiry is the last day of exp month
    final endOfMonth = DateTime(expYear!, expMonth! + 1, 0);
    return now.isAfter(endOfMonth);
  }

  /// True when the saved card expires this calendar month.
  bool get expiresThisMonth {
    if (expMonth == null || expYear == null) return false;
    final now = DateTime.now();
    return expMonth == now.month && expYear == now.year;
  }

  String get displayLast4 => last4 == null || last4!.isEmpty ? '••••' : last4!;

  String get displayExpiry {
    if (brand == CardBrand.ach) return 'ACH';
    if (expMonth == null || expYear == null) return '--/--';
    final mm = expMonth!.toString().padLeft(2, '0');
    final yy = expYear! % 100;
    return '$mm/${yy.toString().padLeft(2, '0')}';
  }

  factory _CardOnFile.fromUserDoc(Map<String, dynamic> data) {
    // ACH (BILL): the bank account id is the saved method; it wins over any legacy card.
    final bank = data['billBankAccountId'] as String?;
    final payarc = (bank != null && bank.isNotEmpty) ? bank : data[_fieldPayarcCustomerId] as String?;
    final last4Raw = (bank != null && bank.isNotEmpty) ? (data['billBankLast4'] ?? data[_fieldCardLast4]) : data[_fieldCardLast4];
    final brandRaw = (bank != null && bank.isNotEmpty) ? 'ach' : data[_fieldCardBrand];
    final expMonthRaw = data[_fieldCardExpMonth];
    final expYearRaw = data[_fieldCardExpYear];
    final updatedRaw = data[_fieldCardUpdatedAt];

    int? asInt(dynamic v) {
      if (v is int) return v;
      if (v is num) return v.toInt();
      if (v is String) return int.tryParse(v);
      return null;
    }

    DateTime? asDate(dynamic v) {
      if (v == null) return null;
      if (v is Timestamp) return v.toDate();
      if (v is String) return DateTime.tryParse(v);
      return null;
    }

    return _CardOnFile(
      payarcCustomerId: payarc,
      last4: last4Raw is String && last4Raw.isNotEmpty ? last4Raw : null,
      brand: _cardBrandParse(brandRaw as String?),
      expMonth: asInt(expMonthRaw),
      expYear: asInt(expYearRaw),
      updatedAt: asDate(updatedRaw),
    );
  }
}

// =======================================================================
// TRANSACTION
// Unified model for records from either the new `transactions`
// subcollection OR the legacy `billing_history` subcollection that Pet
// Profiles r2 writes to. The model tolerates both shapes.
//
// Doc shapes we've seen in the wild:
//
//   billing_history (Pet Profiles r2):
//     {
//       'type': 'pet_addon_proration',
//       'petId': String, 'petName': String,
//       'monthlyPremium': num, 'chargedAmount': num,
//       'transactionId': String, 'prorationDays': int, 'cycleDays': int,
//       'nextCycleStart': Timestamp, 'createdAt': serverTimestamp
//     }
//
//   transactions (new, this widget):
//     {
//       'type': String (one of _txTypeSerialize),
//       'status': String (one of _txStatusSerialize),
//       'amount': double (signed — negative for refunds),
//       'currency': String ('USD'),
//       'description': String (human-readable),
//       'transactionId': String (processor ref),
//       'payarcCustomerId': String,
//       'cardLast4': String, 'cardBrand': String,
//       'membershipIds': List<String> (who this covered),
//       'petIds': List<String>,
//       'periodStart': Timestamp, 'periodEnd': Timestamp,
//       'createdAt': serverTimestamp,
//       'updatedAt': serverTimestamp
//     }
// =======================================================================

class _Transaction {
  final String id;

  /// Collection this record lives in. 'transactions' for new records,
  /// 'billing_history' for Pet Profiles r2 records.
  final String source;

  final TxType type;
  final TxStatus status;

  /// Signed amount in USD. Positive = charge, negative = refund.
  final double amount;

  /// Human-readable one-liner shown in the list and receipt. If the
  /// doc didn't have one, we synthesize from type + pet name / period.
  final String description;

  /// Processor transaction id, if known. We use this as the receipt
  /// reference.
  final String? transactionId;

  /// Card last4 + brand snapshot at time of charge. May be null for
  /// older records.
  final String? cardLast4;
  final CardBrand cardBrand;

  /// Covered period for the charge (monthly / renewal / proration).
  final DateTime? periodStart;
  final DateTime? periodEnd;

  /// When the charge was attempted / created.
  final DateTime createdAt;

  /// Raw doc fields kept for the detail sheet ("view raw").
  final Map<String, dynamic> raw;

  const _Transaction({
    required this.id,
    required this.source,
    required this.type,
    required this.status,
    required this.amount,
    required this.description,
    required this.createdAt,
    this.transactionId,
    this.cardLast4,
    this.cardBrand = CardBrand.unknown,
    this.periodStart,
    this.periodEnd,
    this.raw = const {},
  });

  /// Dollar amount formatted for display. Refunds are shown with a
  /// minus sign already because amount is signed.
  String get displayAmount {
    final abs = amount.abs();
    final prefix = amount < 0 ? '-\$' : '\$';
    return '$prefix${abs.toStringAsFixed(2)}';
  }

  /// Short one-line date, e.g. "Apr 21, 2026".
  String get displayDate {
    return DateFormat('MMM d, y').format(createdAt);
  }

  /// Month + year only, for grouping ("April 2026").
  String get displayMonth {
    return DateFormat('MMMM y').format(createdAt);
  }

  /// Stable yyyy-MM key for grouping transactions by month.
  String get monthKey {
    return DateFormat('yyyy-MM').format(createdAt);
  }

  /// Longer human-readable timestamp for the receipt.
  String get displayDateTime {
    return DateFormat('MMM d, y • h:mm a').format(createdAt);
  }

  factory _Transaction.fromDoc({
    required String docId,
    required String source,
    required Map<String, dynamic> data,
  }) {
    double asDouble(dynamic v, [double fallback = 0.0]) {
      if (v == null) return fallback;
      if (v is num) return v.toDouble();
      if (v is String) return double.tryParse(v) ?? fallback;
      return fallback;
    }

    DateTime? asDate(dynamic v) {
      if (v == null) return null;
      if (v is Timestamp) return v.toDate();
      if (v is String) return DateTime.tryParse(v);
      return null;
    }

    // --- Type ---
    final type = _txTypeParse(data['type'] as String?);

    // --- Status ---
    // New schema has 'status'. Legacy billing_history doesn't, but a
    // Pet Profiles r2 charge that logged to billing_history only does
    // so on success, so default to succeeded for legacy records.
    final statusRaw = data['status'] as String?;
    final status = statusRaw == null && source == 'billing_history'
        ? TxStatus.succeeded
        : _txStatusParse(statusRaw);

    // --- Amount ---
    // New schema: 'amount'. Legacy billing_history uses 'chargedAmount'
    // (pet addon proration). Refunds should be stored negative, but
    // if a legacy record has positive 'chargedAmount' and type ==
    // refund, invert here.
    double amount = asDouble(data['amount']);
    if (amount == 0.0) {
      amount = asDouble(data['chargedAmount']);
      if (amount == 0.0) {
        // Pet Profiles r2 logs monthlyPremium separately; fall back.
        amount = asDouble(data['monthlyPremium']);
      }
    }
    if (type == TxType.refund && amount > 0) amount = -amount;

    // --- Description ---
    String? description = data['description'] as String?;
    if (description == null || description.isEmpty) {
      description = _synthesizeDescription(type, data);
    }

    // --- Dates ---
    final createdAt = asDate(data['createdAt']) ??
        asDate(data['timestamp']) ??
        asDate(data['date']) ??
        DateTime.now();
    final periodStart = asDate(data['periodStart']);
    final periodEnd = asDate(data['periodEnd']) ??
        asDate(data['nextCycleStart']); // Pet Profiles r2 key

    return _Transaction(
      id: docId,
      source: source,
      type: type,
      status: status,
      amount: amount,
      description: description,
      transactionId: data['transactionId'] as String?,
      cardLast4: data['cardLast4'] as String?,
      cardBrand: _cardBrandParse(data['cardBrand'] as String?),
      periodStart: periodStart,
      periodEnd: periodEnd,
      createdAt: createdAt,
      raw: data,
    );
  }

  /// Synthesize a readable description when the doc didn't store one.
  static String _synthesizeDescription(TxType type, Map<String, dynamic> data) {
    switch (type) {
      case TxType.membershipMonthly:
        return 'Monthly Jovi Health membership';
      case TxType.membershipRenewal:
        return 'Annual membership renewal';
      case TxType.petAddonProration:
        final name = data['petName'] as String?;
        if (name != null && name.isNotEmpty) {
          return 'Added $name to your plan (prorated)';
        }
        return 'New pet added to your plan (prorated)';
      case TxType.petAddonMonthly:
        final name = data['petName'] as String?;
        if (name != null && name.isNotEmpty) {
          return 'Monthly pet coverage for $name';
        }
        return 'Monthly pet coverage';
      case TxType.refund:
        return 'Refund issued';
      case TxType.adjustment:
        return 'Account adjustment';
      case TxType.other:
        return 'Charge';
    }
  }

  /// Build a new `transactions` doc for persistence. Used when this
  /// widget writes a new record (e.g. logging the card update fee, if
  /// we ever have one — today we just log billing events triggered
  /// via this widget).
  Map<String, dynamic> toFirestore() {
    return {
      'type': _txTypeSerialize(type),
      'status': _txStatusSerialize(status),
      'amount': amount,
      'currency': 'USD',
      'description': description,
      if (transactionId != null) 'transactionId': transactionId,
      if (cardLast4 != null) 'cardLast4': cardLast4,
      if (cardBrand != CardBrand.unknown)
        'cardBrand': _cardBrandSerialize(cardBrand),
      if (periodStart != null) 'periodStart': Timestamp.fromDate(periodStart!),
      if (periodEnd != null) 'periodEnd': Timestamp.fromDate(periodEnd!),
      'createdAt': FieldValue.serverTimestamp(),
      'updatedAt': FieldValue.serverTimestamp(),
    };
  }
}

// =======================================================================
// BILLING SUMMARY
// Derived snapshot of "what's the member paying and when" for the
// header card. Computed from user-doc fields on every snapshot — we
// never cache this because any field that feeds into it can change
// from elsewhere in the app.
// =======================================================================

class _BillingSummary {
  /// Monthly total the member is billed. Prefers `grandTotal` (what
  /// OnboardingUpdate writes, includes discounts). Falls back to
  /// `totalPremium + petTotalPremium` for accounts that haven't been
  /// through OnboardingUpdate yet.
  final double monthlyTotal;

  /// Health-only portion. May be null for very old accounts.
  final double? healthPremium;

  /// Pet-only portion. May be null / 0.
  final double? petPremium;

  /// Next billing date, derived from the `renew` timestamp's day of
  /// month. Null for accounts that haven't completed onboarding.
  final DateTime? nextBillDate;

  /// Renewal (annual) date. The day-of-month doubles as monthly billing
  /// anniversary, matching Pet Profiles r2's proration math.
  final DateTime? renewDate;

  /// Most recent successful payment we've seen.
  final DateTime? lastPaymentDate;

  /// Current payment state. 'ok', 'failed', 'past_due', 'pending'.
  /// Anything other than 'ok' / null triggers the blocking banner.
  final String? lastChargeStatus;
  final String? lastChargeError;
  final DateTime? lastChargeAttemptAt;
  final double? lastChargeAmount;

  /// Whether the account is marked active on the user doc.
  final bool isActive;

  const _BillingSummary({
    required this.monthlyTotal,
    this.healthPremium,
    this.petPremium,
    this.nextBillDate,
    this.renewDate,
    this.lastPaymentDate,
    this.lastChargeStatus,
    this.lastChargeError,
    this.lastChargeAttemptAt,
    this.lastChargeAmount,
    this.isActive = true,
  });

  /// True when the account's last charge attempt failed or is past due.
  /// Triggers the blocking banner in the widget UI.
  bool get hasFailedPayment {
    if (lastChargeStatus == null) return false;
    final s = lastChargeStatus!.toLowerCase();
    return s == 'failed' || s == 'past_due' || s == 'declined';
  }

  String get displayMonthlyTotal => '\$${monthlyTotal.toStringAsFixed(2)}';

  factory _BillingSummary.fromUserDoc(Map<String, dynamic> data) {
    double asDouble(dynamic v, [double fallback = 0.0]) {
      if (v == null) return fallback;
      if (v is num) return v.toDouble();
      if (v is String) return double.tryParse(v) ?? fallback;
      return fallback;
    }

    DateTime? asDate(dynamic v) {
      if (v == null) return null;
      if (v is Timestamp) return v.toDate();
      if (v is String) return DateTime.tryParse(v);
      return null;
    }

    final health = asDouble(data[_fieldTotalPremium]);
    final pet = asDouble(data[_fieldPetTotalPremium]);
    final grand = asDouble(data[_fieldGrandTotal]);
    // Prefer grandTotal when set (includes discounts), otherwise sum.
    final monthly = grand > 0 ? grand : (health + pet);

    final renew = asDate(data[_fieldRenew]);

    // Next monthly bill = renewal anniversary day in the next upcoming
    // month. Same math as Pet Profiles r2's ProrationCalc.
    DateTime? nextBill;
    if (renew != null) {
      final now = DateTime.now();
      final anniversaryDay = renew.day;

      DateTime anchorFor(int year, int month, int day) {
        final lastDayOfMonth = DateTime(year, month + 1, 0).day;
        final clamped = day.clamp(1, lastDayOfMonth);
        return DateTime(year, month, clamped);
      }

      final thisMonthAnchor = anchorFor(now.year, now.month, anniversaryDay);
      if (!now.isBefore(thisMonthAnchor)) {
        // Already billed this month; next bill is next month.
        nextBill = anchorFor(
          now.month == 12 ? now.year + 1 : now.year,
          now.month == 12 ? 1 : now.month + 1,
          anniversaryDay,
        );
      } else {
        nextBill = thisMonthAnchor;
      }
    }

    return _BillingSummary(
      monthlyTotal: monthly,
      healthPremium: health > 0 ? health : null,
      petPremium: pet > 0 ? pet : null,
      nextBillDate: nextBill,
      renewDate: renew,
      lastPaymentDate: asDate(data[_fieldLastPaymentDate]),
      lastChargeStatus: data[_fieldLastChargeStatus] as String?,
      lastChargeError: data[_fieldLastChargeError] as String?,
      lastChargeAttemptAt: asDate(data[_fieldLastChargeAttemptAt]),
      lastChargeAmount: data[_fieldLastChargeAmount] is num
          ? (data[_fieldLastChargeAmount] as num).toDouble()
          : null,
      isActive: data[_fieldIsActive] != false,
    );
  }
}
// =======================================================================
// CLOUD FUNCTION RESULTS
// Same pattern as Pet Profiles r2's _ChargeResult — structured results
// so the UI can pattern-match on error codes instead of string-parsing.
// =======================================================================

class _UpdateCardResult {
  final bool success;
  final String? errorMessage;
  final String? errorCode;

  /// On success, the new payarcCustomerId. Usually the same as the
  /// existing one (processor updates in place), but the backend is
  /// free to rotate it — we always take whatever it returns.
  final String? payarcCustomerId;

  /// On success, the display metadata for the new card.
  final String? cardLast4;
  final CardBrand cardBrand;
  final int? cardExpMonth;
  final int? cardExpYear;

  const _UpdateCardResult._({
    required this.success,
    this.errorMessage,
    this.errorCode,
    this.payarcCustomerId,
    this.cardLast4,
    this.cardBrand = CardBrand.unknown,
    this.cardExpMonth,
    this.cardExpYear,
  });

  factory _UpdateCardResult.success({
    required String? payarcCustomerId,
    required String? cardLast4,
    required CardBrand cardBrand,
    required int? cardExpMonth,
    required int? cardExpYear,
  }) =>
      _UpdateCardResult._(
        success: true,
        payarcCustomerId: payarcCustomerId,
        cardLast4: cardLast4,
        cardBrand: cardBrand,
        cardExpMonth: cardExpMonth,
        cardExpYear: cardExpYear,
      );

  factory _UpdateCardResult.failure({
    required String errorMessage,
    String? errorCode,
  }) =>
      _UpdateCardResult._(
        success: false,
        errorMessage: errorMessage,
        errorCode: errorCode,
      );
}

class _DeleteCardResult {
  final bool success;
  final String? errorMessage;
  final String? errorCode;

  const _DeleteCardResult._({
    required this.success,
    this.errorMessage,
    this.errorCode,
  });

  factory _DeleteCardResult.success() =>
      const _DeleteCardResult._(success: true);

  factory _DeleteCardResult.failure({
    required String errorMessage,
    String? errorCode,
  }) =>
      _DeleteCardResult._(
        success: false,
        errorMessage: errorMessage,
        errorCode: errorCode,
      );
}

class _RetryChargeResult {
  final bool success;
  final String? errorMessage;
  final String? errorCode;
  final String? transactionId;
  final double? chargedAmount;

  const _RetryChargeResult._({
    required this.success,
    this.errorMessage,
    this.errorCode,
    this.transactionId,
    this.chargedAmount,
  });

  factory _RetryChargeResult.success({
    String? transactionId,
    double? chargedAmount,
  }) =>
      _RetryChargeResult._(
        success: true,
        transactionId: transactionId,
        chargedAmount: chargedAmount,
      );

  factory _RetryChargeResult.failure({
    required String errorMessage,
    String? errorCode,
  }) =>
      _RetryChargeResult._(
        success: false,
        errorMessage: errorMessage,
        errorCode: errorCode,
      );
}

// =======================================================================
// CLOUD FUNCTION STUBS
// None of these endpoints exist on the backend yet. Each one follows
// the Pet Profiles r2 graceful-stub pattern: if the CF returns
// `not-found` or `unavailable`, we show a clear "payment system being
// upgraded" message. When the CFs land, no client changes are needed.
//
// Error codes the client understands (documented per CF):
//   - 'NO_PAYMENT_METHOD'    — payarcCustomerId invalid / missing
//   - 'CARD_DECLINED'        — issuer declined (the card we tried to
//                              use was declined by the bank)
//   - 'CARD_INVALID'         — the submitted card failed server-side
//                              validation
//   - 'PROCESSOR_UNAVAILABLE'— transient processor outage / CF not
//                              implemented yet
//   - 'UNAUTHENTICATED'      — auth expired mid-flow
// =======================================================================

/// Update (or replace) the saved payment method on file. The new
/// processor CF is expected to tokenize the submitted PAN, replace or
/// rotate the customer record, and return the display metadata.
///
/// INPUT (data): {
///   'userId': String,
///   'cardNumber': String,         // raw PAN; backend MUST tokenize
///   'expMonth': int,              // 1-12
///   'expYear': int,               // full 4-digit year
///   'cvc': String,                // never stored
///   'nameOnCard': String,
///   'billingZip': String,
///   'existingPayarcCustomerId': String?,  // if user already has one
/// }
///
/// OUTPUT (data): {
///   'success': bool,
///   'error': String?,
///   'errorCode': String?,
///   'payarcCustomerId': String?,
///   'cardLast4': String?,
///   'cardBrand': String?,   // e.g. 'visa', 'mastercard'
///   'cardExpMonth': int?,
///   'cardExpYear': int?,
/// }
Future<_UpdateCardResult> _callUpdatePaymentMethod({
  required String userId,
  required String routingNumber,
  required String accountNumber,
  required String accountType,
  required String nameOnAccount,
}) async {
  try {
    final callable =
        FirebaseFunctions.instance.httpsCallable(_cfUpdatePaymentMethod);
    final result = await callable.call(<String, dynamic>{
      'userId': userId,
      'routingNumber': routingNumber,
      'accountNumber': accountNumber,
      'accountType': accountType,
      'nameOnAccount': nameOnAccount,
    });
    final data = result.data;
    if (data is! Map) {
      return _UpdateCardResult.failure(
        errorMessage: 'Unexpected response from the payment system.',
        errorCode: 'MALFORMED_RESPONSE',
      );
    }
    final m = Map<String, dynamic>.from(data);
    if (m['success'] == true) {
      return _UpdateCardResult.success(
        payarcCustomerId: m['bankAccountId'] as String?,
        cardLast4: m['cardLast4'] as String?,
        cardBrand: CardBrand.ach,
        cardExpMonth: null,
        cardExpYear: null,
      );
    }
    final errorCode = m['errorCode'] as String?;
    final errorMessage =
        (m['error'] as String?) ?? _defaultErrorMessageFor(errorCode);
    return _UpdateCardResult.failure(
      errorMessage: errorMessage,
      errorCode: errorCode,
    );
  } on FirebaseFunctionsException catch (e) {
    _logError('updatePaymentMethod CF failed: ${e.code}', e.message);
    return _UpdateCardResult.failure(
      errorMessage:
          e.message ?? 'We couldn\'t save your bank account. Please try again.',
      errorCode: e.code.toUpperCase(),
    );
  } catch (e) {
    _logError('updatePaymentMethod unexpected error', e);
    return _UpdateCardResult.failure(
      errorMessage:
          'Something went wrong while saving your bank account. Please try again.',
      errorCode: 'UNKNOWN',
    );
  }

}

/// Delete the saved payment method. Member will be marked
/// payment-method-less until they add a new one; active membership
/// charges will fail until they re-add a card.
///
/// INPUT (data): {
///   'userId': String,
///   'payarcCustomerId': String,
/// }
///
/// OUTPUT (data): {
///   'success': bool,
///   'error': String?,
///   'errorCode': String?,
/// }
Future<_DeleteCardResult> _callDeletePaymentMethod({
  required String userId,
  required String payarcCustomerId,
}) async {
  try {
    final callable =
        FirebaseFunctions.instance.httpsCallable(_cfDeletePaymentMethod);
    final result = await callable.call(<String, dynamic>{
      'userId': userId,
      'payarcCustomerId': payarcCustomerId,
    });
    final data = result.data;
    if (data is! Map) {
      return _DeleteCardResult.failure(
        errorMessage: 'Unexpected response from the payment system.',
        errorCode: 'MALFORMED_RESPONSE',
      );
    }
    final m = Map<String, dynamic>.from(data);
    if (m['success'] == true) return _DeleteCardResult.success();
    final errorCode = m['errorCode'] as String?;
    final errorMessage =
        (m['error'] as String?) ?? _defaultErrorMessageFor(errorCode);
    return _DeleteCardResult.failure(
      errorMessage: errorMessage,
      errorCode: errorCode,
    );
  } on FirebaseFunctionsException catch (e) {
    _logError('deletePaymentMethod CF failed: ${e.code}', e.message);
    if (e.code == 'not-found' || e.code == 'unavailable') {
      return _DeleteCardResult.failure(
        errorMessage:
            'Removing your card is temporarily unavailable while we upgrade our payment system. Please contact support if you need to cancel.',
        errorCode: 'PROCESSOR_UNAVAILABLE',
      );
    }
    return _DeleteCardResult.failure(
      errorMessage:
          e.message ?? 'We couldn\'t remove your card. Please try again.',
      errorCode: e.code.toUpperCase(),
    );
  } catch (e) {
    _logError('deletePaymentMethod unexpected error', e);
    return _DeleteCardResult.failure(
      errorMessage:
          'Something went wrong while removing your card. Please try again.',
      errorCode: 'UNKNOWN',
    );
  }
}

/// Retry the most recent failed charge. Used by the blocking banner's
/// "Try again" button. The backend is expected to look up the last
/// failed transaction for this user and re-attempt it against the
/// current saved card.
///
/// INPUT (data): {
///   'userId': String,
///   'payarcCustomerId': String,
/// }
///
/// OUTPUT (data): {
///   'success': bool,
///   'error': String?,
///   'errorCode': String?,
///   'transactionId': String?,
///   'chargedAmount': double?,
/// }
Future<_RetryChargeResult> _callRetryFailedCharge({
  required String userId,
  required String payarcCustomerId,
}) async {
  try {
    final callable =
        FirebaseFunctions.instance.httpsCallable(_cfRetryFailedCharge);
    final result = await callable.call(<String, dynamic>{
      'userId': userId,
      'payarcCustomerId': payarcCustomerId,
    });
    final data = result.data;
    if (data is! Map) {
      return _RetryChargeResult.failure(
        errorMessage: 'Unexpected response from the payment system.',
        errorCode: 'MALFORMED_RESPONSE',
      );
    }
    final m = Map<String, dynamic>.from(data);
    if (m['success'] == true) {
      return _RetryChargeResult.success(
        transactionId: m['transactionId'] as String?,
        chargedAmount: m['chargedAmount'] is num
            ? (m['chargedAmount'] as num).toDouble()
            : null,
      );
    }
    final errorCode = m['errorCode'] as String?;
    final errorMessage =
        (m['error'] as String?) ?? _defaultErrorMessageFor(errorCode);
    return _RetryChargeResult.failure(
      errorMessage: errorMessage,
      errorCode: errorCode,
    );
  } on FirebaseFunctionsException catch (e) {
    _logError('retryFailedCharge CF failed: ${e.code}', e.message);
    if (e.code == 'not-found' || e.code == 'unavailable') {
      return _RetryChargeResult.failure(
        errorMessage:
            'Retrying the charge is temporarily unavailable while we upgrade our payment system. Please contact support.',
        errorCode: 'PROCESSOR_UNAVAILABLE',
      );
    }
    return _RetryChargeResult.failure(
      errorMessage:
          e.message ?? 'We couldn\'t retry the charge. Please try again.',
      errorCode: e.code.toUpperCase(),
    );
  } catch (e) {
    _logError('retryFailedCharge unexpected error', e);
    return _RetryChargeResult.failure(
      errorMessage:
          'Something went wrong while retrying the charge. Please try again.',
      errorCode: 'UNKNOWN',
    );
  }
}

String _defaultErrorMessageFor(String? code) {
  switch (code) {
    case 'NO_PAYMENT_METHOD':
      return 'We couldn\'t find a saved payment method on your account. Please add a card to continue.';
    case 'CARD_DECLINED':
      return 'Your card was declined. Try a different card or contact your bank.';
    case 'CARD_INVALID':
      return 'That card doesn\'t look valid. Please double-check the number, expiry, and CVC.';
    case 'PROCESSOR_UNAVAILABLE':
      return 'Our payment system is temporarily unavailable. Please try again in a few minutes.';
    case 'UNAUTHENTICATED':
      return 'Your session has expired. Please sign in again.';
    default:
      return 'We couldn\'t complete the request. Please try again or contact support.';
  }
}

// =======================================================================
// LUHN CARD NUMBER VALIDATION
// Same implementation Quote Payment uses. Keeping it local to this
// widget so we don't depend on FF custom functions.
// =======================================================================

bool validateCardLuhn(String cardNumber) {
  final digits = cardNumber.replaceAll(RegExp(r'[^\d]'), '');
  if (digits.length < 13 || digits.length > 19) return false;
  int sum = 0;
  bool alternate = false;
  for (int i = digits.length - 1; i >= 0; i--) {
    int digit = int.tryParse(digits[i]) ?? -1;
    if (digit < 0) return false;
    if (alternate) {
      digit *= 2;
      if (digit > 9) digit -= 9;
    }
    sum += digit;
    alternate = !alternate;
  }
  return (sum % 10 == 0);
}
// =======================================================================
// WIDGET
// =======================================================================

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

class BillingWidget extends StatefulWidget {
  const BillingWidget({
    Key? key,
    this.width,
    this.height,
  }) : super(key: key);

  final double? width;
  final double? height;

  @override
  State<BillingWidget> createState() => _BillingWidgetState();
}

class _BillingWidgetState extends State<BillingWidget>
    with TickerProviderStateMixin {
  // ---------------- Data state ----------------
  _CardOnFile _cardOnFile = const _CardOnFile();
  _BillingSummary _summary = const _BillingSummary(monthlyTotal: 0);
  List<_Transaction> _transactions = [];

  bool _loadingUser = true;
  bool _loadingTransactions = true;
  String? _userError;

  /// Current filter chip selection. `null` = All.
  TxType? _filter;

  // ---------------- Subscriptions ----------------
  StreamSubscription<DocumentSnapshot<Map<String, dynamic>>>? _userSub;
  StreamSubscription<QuerySnapshot<Map<String, dynamic>>>? _txSub;
  StreamSubscription<QuerySnapshot<Map<String, dynamic>>>? _legacyTxSub;

  /// Latest copies of each source, keyed by docId so we can merge
  /// both collections into a single sorted list without dupes.
  /// (Dupes shouldn't happen in practice — the two collections have
  /// separate docIds — but if they ever share one, we prefer the
  /// `transactions` entry over `billing_history`.)
  Map<String, _Transaction> _txNew = {};
  Map<String, _Transaction> _txLegacy = {};

  // ---------------- Animation ----------------
  late AnimationController _fadeCtrl;
  late Animation<double> _fadeAnim;

  // ---------------- Lifecycle ----------------

  @override
  void initState() {
    super.initState();
    _fadeCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 500),
    );
    _fadeAnim = CurvedAnimation(parent: _fadeCtrl, curve: Curves.easeOutCubic);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      if (MediaQuery.of(context).disableAnimations) {
        _fadeCtrl.value = 1.0;
      } else {
        _fadeCtrl.forward();
      }
    });
    _subscribe();
    _analytics('billing_opened');
  }

  @override
  void dispose() {
    _fadeCtrl.dispose();
    _userSub?.cancel();
    _txSub?.cancel();
    _legacyTxSub?.cancel();
    super.dispose();
  }

  // =======================================================================
  // SUBSCRIPTIONS
  // We run three streams in parallel:
  //   1. The user doc itself (for card metadata + summary fields).
  //   2. The `transactions` subcollection (new schema).
  //   3. The `billing_history` subcollection (Pet Profiles r2 schema).
  //
  // Transactions from (2) and (3) are merged client-side and sorted
  // reverse-chrono. If Pet Profiles r3 ships and starts writing to
  // `transactions`, the billing_history stream still works for
  // records written before the migration. Eventually (once
  // billing_history is empty for new users) we can drop (3).
  // =======================================================================

  void _subscribe() {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      setState(() {
        _loadingUser = false;
        _loadingTransactions = false;
        _userError = 'Sign in to see your billing.';
      });
      return;
    }
    final uid = user.uid;

    // --- User doc ---
    _userSub?.cancel();
    _userSub = FirebaseFirestore.instance
        .collection('users')
        .doc(uid)
        .snapshots()
        .listen(
      (snap) {
        if (!mounted) return;
        if (!snap.exists) {
          setState(() {
            _loadingUser = false;
            _userError = 'We couldn\'t find your membership.';
          });
          return;
        }
        final data = snap.data();
        if (data == null) return;
        try {
          final card = _CardOnFile.fromUserDoc(data);
          final summary = _BillingSummary.fromUserDoc(data);
          setState(() {
            _cardOnFile = card;
            _summary = summary;
            _loadingUser = false;
            _userError = null;
          });
        } catch (e) {
          _logError('user doc parse failed', e);
          setState(() {
            _loadingUser = false;
            _userError = 'We couldn\'t load your billing info.';
          });
        }
      },
      onError: (err) {
        _logError('user stream failed', err);
        if (!mounted) return;
        setState(() {
          _loadingUser = false;
          _userError = 'We couldn\'t load your billing info.';
        });
      },
    );

    // --- transactions (new) ---
    _txSub?.cancel();
    _txSub = FirebaseFirestore.instance
        .collection('users')
        .doc(uid)
        .collection('transactions')
        .orderBy('createdAt', descending: true)
        .limit(200)
        .snapshots()
        .listen(
      (snap) {
        if (!mounted) return;
        final map = <String, _Transaction>{};
        for (final doc in snap.docs) {
          try {
            map[doc.id] = _Transaction.fromDoc(
              docId: doc.id,
              source: 'transactions',
              data: doc.data(),
            );
          } catch (e) {
            _logError('skipped malformed transaction ${doc.id}', e);
          }
        }
        setState(() {
          _txNew = map;
          _mergeTransactions();
          _loadingTransactions = false;
        });
      },
      onError: (err) {
        _logError('transactions stream failed', err);
        if (!mounted) return;
        setState(() {
          _loadingTransactions = false;
        });
      },
    );

    // --- billing_history (legacy / Pet Profiles r2) ---
    _legacyTxSub?.cancel();
    _legacyTxSub = FirebaseFirestore.instance
        .collection('users')
        .doc(uid)
        .collection('billing_history')
        .orderBy('createdAt', descending: true)
        .limit(200)
        .snapshots()
        .listen(
      (snap) {
        if (!mounted) return;
        final map = <String, _Transaction>{};
        for (final doc in snap.docs) {
          try {
            // Prefix the docId so legacy and new records with the same
            // Firestore docId can coexist in the merged list.
            map['legacy_${doc.id}'] = _Transaction.fromDoc(
              docId: doc.id,
              source: 'billing_history',
              data: doc.data(),
            );
          } catch (e) {
            _logError('skipped malformed billing_history ${doc.id}', e);
          }
        }
        setState(() {
          _txLegacy = map;
          _mergeTransactions();
        });
      },
      onError: (err) {
        _logError('billing_history stream failed', err);
        // Non-fatal — new-schema records may still be available.
      },
    );
  }

  /// Merge the two source maps into `_transactions`, sorted reverse-
  /// chrono. Called whenever either source stream updates.
  void _mergeTransactions() {
    final merged = <_Transaction>[
      ..._txNew.values,
      ..._txLegacy.values,
    ];
    merged.sort((a, b) => b.createdAt.compareTo(a.createdAt));
    _transactions = merged;
  }

  /// Current transaction list filtered by the active filter chip.
  List<_Transaction> get _filteredTransactions {
    if (_filter == null) return _transactions;
    return _transactions.where((t) {
      // "Pet addon" filter lumps both proration and monthly charges.
      if (_filter == TxType.petAddonProration ||
          _filter == TxType.petAddonMonthly) {
        return t.type == TxType.petAddonProration ||
            t.type == TxType.petAddonMonthly;
      }
      if (_filter == TxType.membershipMonthly ||
          _filter == TxType.membershipRenewal) {
        return t.type == TxType.membershipMonthly ||
            t.type == TxType.membershipRenewal;
      }
      return t.type == _filter;
    }).toList();
  }

  /// Group transactions by month for section headers in the list.
  /// Returns a list of (monthKey, label, transactions) tuples in
  /// display order.
  List<_MonthGroup> _groupByMonth(List<_Transaction> txns) {
    final groups = <String, _MonthGroup>{};
    for (final t in txns) {
      groups.putIfAbsent(
        t.monthKey,
        () => _MonthGroup(
          monthKey: t.monthKey,
          label: t.displayMonth,
          transactions: [],
        ),
      );
      groups[t.monthKey]!.transactions.add(t);
    }
    final list = groups.values.toList();
    // Already reverse-chrono because input is sorted.
    return list;
  }

  /// Filter the full transaction list down to a single month's worth
  /// of succeeded charges. Used for generating the monthly statement
  /// PDF — we only include money that actually moved.
  List<_Transaction> _transactionsForMonth(String monthKey) {
    return _transactions
        .where((t) => t.monthKey == monthKey && t.status != TxStatus.voided)
        .toList();
  }

  // (state class continues in subsequent parts)
  // =======================================================================
  // CARD UPDATE FLOW
  // User taps "Update card" -> we open the editor sheet. On submit,
  // the sheet calls back to _updateCard, which:
  //   1. Validates the submitted card locally (Luhn + expiry sanity)
  //   2. Calls the updatePaymentMethod CF (stubbed until processor
  //      ships — fails gracefully)
  //   3. On success, writes card metadata fields to the user doc so
  //      the tile updates everywhere (here, onboarding, everywhere
  //      else that reads them)
  //   4. If the user had a failed-payment state, offers to retry the
  //      charge with the new card
  // =======================================================================

  /// Validate an expiry month+year pair. Returns an error message
  /// suitable for the form, or null if valid.
  String? _validateExpiry(int? month, int? year) {
    if (month == null || month < 1 || month > 12) return 'Invalid month';
    if (year == null || year < 2000) return 'Invalid year';
    // Accept 2-digit years: if under 100, treat as 20xx.
    final normalizedYear = year < 100 ? 2000 + year : year;
    final now = DateTime.now();
    // Card is good through the end of the expiry month.
    final endOfExpiry = DateTime(normalizedYear, month + 1, 0);
    if (endOfExpiry.isBefore(DateTime(now.year, now.month, now.day))) {
      return 'Card has expired';
    }
    return null;
  }

  /// Called by the editor sheet when the user hits "Save bank account".
  /// Returns true on success (sheet closes), false on failure.
  Future<bool> _updateCard({
    required String routingNumber,
    required String accountNumber,
    required String accountType,
    required String nameOnAccount,
  }) async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      _showSnackBar('Sign in to update your bank account.', isError: true);
      return false;
    }
    if (!RegExp(r'^\d{9}$').hasMatch(routingNumber)) {
      _showSnackBar('Routing number should be 9 digits.', isError: true);
      return false;
    }
    if (!RegExp(r'^\d{4,17}$').hasMatch(accountNumber)) {
      _showSnackBar('Please check the account number.', isError: true);
      return false;
    }
    _analytics('billing_update_bank_submitted');
    _showBlockingProgress('Saving your bank account…');
    final result = await _callUpdatePaymentMethod(
      userId: user.uid,
      routingNumber: routingNumber,
      accountNumber: accountNumber,
      accountType: accountType,
      nameOnAccount: nameOnAccount,
    );
    if (!mounted) return false;
    if (!result.success) {
      Navigator.of(context).pop();
      _analytics('billing_update_bank_failed', {'errorCode': result.errorCode});
      _showSnackBar(
        result.errorMessage ??
            'We couldn\'t save your bank account. Please try again.',
        isError: true,
      );
      return false;
    }
    // The Cloud Function writes billBankAccountId / billBankLast4 / cardLast4 /
    // cardBrand='ach'; the user-doc stream refreshes the tile.
    if (!mounted) return false;
    Navigator.of(context).pop();
    _analytics('billing_update_bank_succeeded');
    _showSnackBar('Bank account updated. Verification can take up to two business days.', isSuccess: true);
    return true;
  }

  /// Called from the failed-payment banner or from the post-update
  /// retry prompt. Kicks the charge CF and surfaces the result.
  Future<void> _retryFailedCharge() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return;

    final payarc = _cardOnFile.payarcCustomerId;
    if (payarc == null || payarc.isEmpty) {
      _showSnackBar(
        'Please add a payment method before retrying.',
        isError: true,
      );
      return;
    }

    _analytics('billing_retry_charge_tapped');
    _showBlockingProgress('Retrying charge…');

    final result = await _callRetryFailedCharge(
      userId: user.uid,
      payarcCustomerId: payarc,
    );

    if (!mounted) return;
    Navigator.of(context).pop();

    if (result.success) {
      _analytics('billing_retry_charge_succeeded',
          {'transactionId': result.transactionId});
      final amt = result.chargedAmount;
      _showSnackBar(
        amt != null
            ? 'Charged \$${amt.toStringAsFixed(2)} to your card.'
            : 'Charge completed.',
        isSuccess: true,
      );
    } else {
      _analytics(
          'billing_retry_charge_failed', {'errorCode': result.errorCode});
      _showSnackBar(
        result.errorMessage ?? 'We couldn\'t complete the charge.',
        isError: true,
      );
    }
  }

  /// Delete the saved card. Rarely used — most members would rather
  /// replace it than remove it. Guarded by a two-step confirmation
  /// because a missing card means charges will start failing.
  Future<void> _deleteCard() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return;
    final payarc = _cardOnFile.payarcCustomerId;
    if (payarc == null || payarc.isEmpty) return;

    final confirmed = await _showConfirmDialog(
      title: 'Remove your card?',
      body:
          'Your next monthly charge will fail until you add a new card. Your membership will go past-due after that.\n\nAre you sure?',
      confirmLabel: 'Remove bank account',
      destructive: true,
    );
    if (confirmed != true || !mounted) return;

    _analytics('billing_delete_card_tapped');
    _showBlockingProgress('Removing card…');

    final result = await _callDeletePaymentMethod(
      userId: user.uid,
      payarcCustomerId: payarc,
    );

    if (!mounted) return;
    Navigator.of(context).pop();

    if (!result.success) {
      _analytics('billing_delete_card_failed', {'errorCode': result.errorCode});
      _showSnackBar(
        result.errorMessage ?? 'We couldn\'t remove your card.',
        isError: true,
      );
      return;
    }

    // Clear the metadata fields locally too, so the UI updates.
    try {
      await FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .update({
        _fieldPayarcCustomerId: FieldValue.delete(),
        _fieldCardLast4: FieldValue.delete(),
        _fieldCardBrand: FieldValue.delete(),
        _fieldCardExpMonth: FieldValue.delete(),
        _fieldCardExpYear: FieldValue.delete(),
        _fieldCardUpdatedAt: FieldValue.serverTimestamp(),
      });
    } catch (e) {
      _logError('card metadata delete failed', e);
    }

    _analytics('billing_delete_card_succeeded');
    _showSnackBar('Card removed.', isSuccess: true);
  }

  // (state class continues in subsequent parts)
  // =======================================================================
  // PDF GENERATION
  // Client-side PDF creation using the pdf + printing packages. We
  // generate two things:
  //   1. Single-transaction receipts (from the transaction detail sheet)
  //   2. Monthly statements (from the history list header)
  //
  // Layout is intentionally plain — no logos, no fancy graphics, just
  // the data in a readable form. When we have brand assets in a place
  // the widget can load from (network URL) we can add them.
  // =======================================================================

  /// Shared brand palette for the PDFs. Sticks close to the in-app
  /// palette so receipts feel consistent with the rest of the brand.
  pw_pdf.PdfColor get _pdfNavy => pw_pdf.PdfColor.fromInt(0xFF1A2744);
  pw_pdf.PdfColor get _pdfCoral => pw_pdf.PdfColor.fromInt(0xFFFF6B4A);
  pw_pdf.PdfColor get _pdfMuted => pw_pdf.PdfColor.fromInt(0xFF6B7280);
  pw_pdf.PdfColor get _pdfDivider => pw_pdf.PdfColor.fromInt(0xFFE5E7EB);

  /// Generate a receipt PDF for a single transaction.
  Future<Uint8List> _generateReceiptPdf(_Transaction tx) async {
    final doc = pw.Document();
    final fullName = await _resolveMemberName();
    final currencyFmt = NumberFormat.currency(locale: 'en_US', symbol: '\$');

    doc.addPage(
      pw.Page(
        pageFormat: pw_pdf.PdfPageFormat.letter,
        margin: const pw.EdgeInsets.all(48),
        build: (ctx) {
          return pw.Column(
            crossAxisAlignment: pw.CrossAxisAlignment.start,
            children: [
              // --- Header ---
              pw.Row(
                mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
                crossAxisAlignment: pw.CrossAxisAlignment.start,
                children: [
                  pw.Column(
                    crossAxisAlignment: pw.CrossAxisAlignment.start,
                    children: [
                      pw.Text(
                        'Jovi Health',
                        style: pw.TextStyle(
                          fontSize: 22,
                          fontWeight: pw.FontWeight.bold,
                          color: _pdfNavy,
                        ),
                      ),
                      pw.SizedBox(height: 2),
                      pw.Text(
                        'Receipt',
                        style: pw.TextStyle(
                          fontSize: 14,
                          color: _pdfMuted,
                        ),
                      ),
                    ],
                  ),
                  pw.Column(
                    crossAxisAlignment: pw.CrossAxisAlignment.end,
                    children: [
                      pw.Text(
                        'Receipt #${tx.transactionId ?? tx.id.substring(0, tx.id.length.clamp(0, 8))}',
                        style: pw.TextStyle(
                          fontSize: 11,
                          color: _pdfMuted,
                        ),
                      ),
                      pw.SizedBox(height: 2),
                      pw.Text(
                        tx.displayDateTime,
                        style: pw.TextStyle(
                          fontSize: 11,
                          color: _pdfMuted,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
              pw.SizedBox(height: 24),
              pw.Container(height: 1, color: _pdfDivider),
              pw.SizedBox(height: 24),

              // --- Billed to ---
              pw.Text(
                'BILLED TO',
                style: pw.TextStyle(
                  fontSize: 9,
                  color: _pdfMuted,
                  letterSpacing: 1.2,
                  fontWeight: pw.FontWeight.bold,
                ),
              ),
              pw.SizedBox(height: 6),
              pw.Text(
                fullName,
                style: pw.TextStyle(fontSize: 12, color: _pdfNavy),
              ),
              pw.SizedBox(height: 24),

              // --- Description / amount ---
              pw.Container(
                padding: const pw.EdgeInsets.all(16),
                decoration: pw.BoxDecoration(
                  color: pw_pdf.PdfColor.fromInt(0xFFF9FAFB),
                  borderRadius:
                      const pw.BorderRadius.all(pw.Radius.circular(6)),
                ),
                child: pw.Column(
                  crossAxisAlignment: pw.CrossAxisAlignment.start,
                  children: [
                    pw.Row(
                      mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
                      crossAxisAlignment: pw.CrossAxisAlignment.start,
                      children: [
                        pw.Expanded(
                          child: pw.Column(
                            crossAxisAlignment: pw.CrossAxisAlignment.start,
                            children: [
                              pw.Text(
                                _txTypeLabel(tx.type),
                                style: pw.TextStyle(
                                  fontSize: 13,
                                  color: _pdfMuted,
                                  fontWeight: pw.FontWeight.bold,
                                ),
                              ),
                              pw.SizedBox(height: 4),
                              pw.Text(
                                tx.description,
                                style: pw.TextStyle(
                                  fontSize: 15,
                                  color: _pdfNavy,
                                ),
                              ),
                              if (tx.periodStart != null &&
                                  tx.periodEnd != null) ...[
                                pw.SizedBox(height: 4),
                                pw.Text(
                                  'Coverage period: ${DateFormat('MMM d').format(tx.periodStart!)} – ${DateFormat('MMM d, y').format(tx.periodEnd!)}',
                                  style: pw.TextStyle(
                                    fontSize: 11,
                                    color: _pdfMuted,
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ),
                        pw.Text(
                          currencyFmt.format(tx.amount),
                          style: pw.TextStyle(
                            fontSize: 22,
                            fontWeight: pw.FontWeight.bold,
                            color: _pdfNavy,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              pw.SizedBox(height: 24),

              // --- Payment details ---
              pw.Text(
                'PAYMENT',
                style: pw.TextStyle(
                  fontSize: 9,
                  color: _pdfMuted,
                  letterSpacing: 1.2,
                  fontWeight: pw.FontWeight.bold,
                ),
              ),
              pw.SizedBox(height: 8),
              _pdfKvRow(
                  'Method', _pdfCardDescription(tx.cardBrand, tx.cardLast4)),
              _pdfKvRow('Status', _txStatusLabel(tx.status)),
              if (tx.transactionId != null)
                _pdfKvRow('Transaction ID', tx.transactionId!),
              pw.Spacer(),

              // --- Footer ---
              pw.Container(height: 1, color: _pdfDivider),
              pw.SizedBox(height: 12),
              pw.Text(
                'Thank you for being a Jovi Health member.',
                style: pw.TextStyle(fontSize: 11, color: _pdfMuted),
              ),
              pw.SizedBox(height: 4),
              pw.Text(
                'Questions about this receipt? Contact member support.',
                style: pw.TextStyle(fontSize: 10, color: _pdfMuted),
              ),
            ],
          );
        },
      ),
    );
    return doc.save();
  }

  /// Generate a monthly statement PDF covering all transactions in
  /// the given month.
  Future<Uint8List> _generateMonthlyStatementPdf({
    required String monthKey,
    required String monthLabel,
    required List<_Transaction> monthTransactions,
  }) async {
    final doc = pw.Document();
    final fullName = await _resolveMemberName();
    final currencyFmt = NumberFormat.currency(locale: 'en_US', symbol: '\$');

    final total = monthTransactions.fold<double>(
      0.0,
      (sum, t) =>
          t.status == TxStatus.succeeded || t.status == TxStatus.refunded
              ? sum + t.amount
              : sum,
    );

    doc.addPage(
      pw.MultiPage(
        pageFormat: pw_pdf.PdfPageFormat.letter,
        margin: const pw.EdgeInsets.all(48),
        build: (ctx) {
          return [
            // --- Header ---
            pw.Row(
              mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
              crossAxisAlignment: pw.CrossAxisAlignment.start,
              children: [
                pw.Column(
                  crossAxisAlignment: pw.CrossAxisAlignment.start,
                  children: [
                    pw.Text(
                      'Jovi Health',
                      style: pw.TextStyle(
                        fontSize: 22,
                        fontWeight: pw.FontWeight.bold,
                        color: _pdfNavy,
                      ),
                    ),
                    pw.SizedBox(height: 2),
                    pw.Text(
                      'Monthly Statement',
                      style: pw.TextStyle(fontSize: 14, color: _pdfMuted),
                    ),
                  ],
                ),
                pw.Column(
                  crossAxisAlignment: pw.CrossAxisAlignment.end,
                  children: [
                    pw.Text(
                      monthLabel,
                      style: pw.TextStyle(
                        fontSize: 14,
                        fontWeight: pw.FontWeight.bold,
                        color: _pdfNavy,
                      ),
                    ),
                    pw.SizedBox(height: 2),
                    pw.Text(
                      'Generated ${DateFormat('MMM d, y').format(DateTime.now())}',
                      style: pw.TextStyle(fontSize: 11, color: _pdfMuted),
                    ),
                  ],
                ),
              ],
            ),
            pw.SizedBox(height: 24),
            pw.Container(height: 1, color: _pdfDivider),
            pw.SizedBox(height: 24),

            // --- Billed to ---
            pw.Text(
              'MEMBER',
              style: pw.TextStyle(
                fontSize: 9,
                color: _pdfMuted,
                letterSpacing: 1.2,
                fontWeight: pw.FontWeight.bold,
              ),
            ),
            pw.SizedBox(height: 6),
            pw.Text(
              fullName,
              style: pw.TextStyle(fontSize: 12, color: _pdfNavy),
            ),
            pw.SizedBox(height: 24),

            // --- Summary row ---
            pw.Container(
              padding: const pw.EdgeInsets.all(16),
              decoration: pw.BoxDecoration(
                color: pw_pdf.PdfColor.fromInt(0xFFF9FAFB),
                borderRadius: const pw.BorderRadius.all(pw.Radius.circular(6)),
              ),
              child: pw.Row(
                mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
                children: [
                  pw.Column(
                    crossAxisAlignment: pw.CrossAxisAlignment.start,
                    children: [
                      pw.Text(
                        '${monthTransactions.length} transaction${monthTransactions.length == 1 ? '' : 's'}',
                        style: pw.TextStyle(
                          fontSize: 13,
                          color: _pdfMuted,
                        ),
                      ),
                      pw.SizedBox(height: 4),
                      pw.Text(
                        'Net total',
                        style: pw.TextStyle(
                          fontSize: 12,
                          color: _pdfNavy,
                          fontWeight: pw.FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                  pw.Text(
                    currencyFmt.format(total),
                    style: pw.TextStyle(
                      fontSize: 22,
                      fontWeight: pw.FontWeight.bold,
                      color: _pdfNavy,
                    ),
                  ),
                ],
              ),
            ),
            pw.SizedBox(height: 24),

            // --- Line items table ---
            pw.Text(
              'TRANSACTIONS',
              style: pw.TextStyle(
                fontSize: 9,
                color: _pdfMuted,
                letterSpacing: 1.2,
                fontWeight: pw.FontWeight.bold,
              ),
            ),
            pw.SizedBox(height: 8),
            pw.Table(
              columnWidths: const {
                0: pw.FlexColumnWidth(1.2),
                1: pw.FlexColumnWidth(3),
                2: pw.FlexColumnWidth(1.2),
                3: pw.FlexColumnWidth(1.3),
              },
              children: [
                pw.TableRow(
                  decoration: pw.BoxDecoration(
                    border: pw.Border(
                      bottom: pw.BorderSide(color: _pdfDivider, width: 0.5),
                    ),
                  ),
                  children: [
                    _pdfTableHeader('Date'),
                    _pdfTableHeader('Description'),
                    _pdfTableHeader('Status'),
                    _pdfTableHeader('Amount', alignRight: true),
                  ],
                ),
                ...monthTransactions.map(
                  (t) => pw.TableRow(
                    decoration: pw.BoxDecoration(
                      border: pw.Border(
                        bottom: pw.BorderSide(color: _pdfDivider, width: 0.3),
                      ),
                    ),
                    children: [
                      _pdfTableCell(DateFormat('MMM d').format(t.createdAt)),
                      _pdfTableCell(t.description),
                      _pdfTableCell(_txStatusLabel(t.status)),
                      _pdfTableCell(
                        currencyFmt.format(t.amount),
                        alignRight: true,
                      ),
                    ],
                  ),
                ),
              ],
            ),
            pw.SizedBox(height: 24),

            // --- Footer ---
            pw.Container(height: 1, color: _pdfDivider),
            pw.SizedBox(height: 12),
            pw.Text(
              'This statement reflects charges settled in $monthLabel. Pending charges are excluded.',
              style: pw.TextStyle(fontSize: 10, color: _pdfMuted),
            ),
            pw.SizedBox(height: 4),
            pw.Text(
              'Questions? Contact Jovi Health member support.',
              style: pw.TextStyle(fontSize: 10, color: _pdfMuted),
            ),
          ];
        },
      ),
    );
    return doc.save();
  }

  pw.Widget _pdfKvRow(String key, String value) {
    return pw.Padding(
      padding: const pw.EdgeInsets.only(bottom: 4),
      child: pw.Row(
        crossAxisAlignment: pw.CrossAxisAlignment.start,
        children: [
          pw.SizedBox(
            width: 110,
            child: pw.Text(
              key,
              style: pw.TextStyle(fontSize: 11, color: _pdfMuted),
            ),
          ),
          pw.Expanded(
            child: pw.Text(
              value,
              style: pw.TextStyle(fontSize: 11, color: _pdfNavy),
            ),
          ),
        ],
      ),
    );
  }

  pw.Widget _pdfTableHeader(String text, {bool alignRight = false}) {
    return pw.Padding(
      padding: const pw.EdgeInsets.symmetric(vertical: 6),
      child: pw.Text(
        text.toUpperCase(),
        style: pw.TextStyle(
          fontSize: 9,
          color: _pdfMuted,
          letterSpacing: 1,
          fontWeight: pw.FontWeight.bold,
        ),
        textAlign: alignRight ? pw.TextAlign.right : pw.TextAlign.left,
      ),
    );
  }

  pw.Widget _pdfTableCell(String text, {bool alignRight = false}) {
    return pw.Padding(
      padding: const pw.EdgeInsets.symmetric(vertical: 6, horizontal: 0),
      child: pw.Text(
        text,
        style: pw.TextStyle(fontSize: 11, color: _pdfNavy),
        textAlign: alignRight ? pw.TextAlign.right : pw.TextAlign.left,
      ),
    );
  }

  String _pdfCardDescription(CardBrand brand, String? last4) {
    if (last4 == null || last4.isEmpty) {
      return brand == CardBrand.unknown
          ? 'Bank account on file'
          : '${_cardBrandLabel(brand)} on file';
    }
    final brandLabel =
        brand == CardBrand.unknown ? 'Card' : _cardBrandLabel(brand);
    return '$brandLabel ending in $last4';
  }

  /// Resolve the member's name for PDF headers. Prefers firstName +
  /// lastName (OnboardingUpdate schema); falls back to the Firebase
  /// Auth displayName or email.
  Future<String> _resolveMemberName() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return 'Jovi Health Member';
    try {
      final doc = await FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .get();
      if (doc.exists) {
        final data = doc.data();
        if (data != null) {
          // OnboardingUpdate schema: firstName + lastName
          final first = data['firstName'] as String?;
          final last = data['lastName'] as String?;
          if (first != null && last != null && first.isNotEmpty) {
            return '$first $last'.trim();
          }
          // QuotePayment schema: first + last (shorter keys)
          final firstShort = data['first'] as String?;
          final lastShort = data['last'] as String?;
          if (firstShort != null &&
              lastShort != null &&
              firstShort.isNotEmpty) {
            return '$firstShort $lastShort'.trim();
          }
        }
      }
    } catch (e) {
      _logError('member name resolution failed', e);
    }
    if (user.displayName != null && user.displayName!.isNotEmpty) {
      return user.displayName!;
    }
    if (user.email != null && user.email!.isNotEmpty) return user.email!;
    return 'Jovi Health Member';
  }

  /// Share / save the generated PDF. Uses the `printing` package's
  /// share sheet, which on mobile lets the user save to Files, share
  /// to email, print, etc.
  Future<void> _sharePdf({
    required Uint8List bytes,
    required String filename,
  }) async {
    try {
      await Printing.sharePdf(bytes: bytes, filename: filename);
    } catch (e) {
      _logError('pdf share failed', e);
      _showSnackBar(
        'Couldn\'t share the PDF. Please try again.',
        isError: true,
      );
    }
  }

  Future<void> _downloadReceiptFor(_Transaction tx) async {
    _analytics('billing_receipt_downloaded',
        {'transactionId': tx.transactionId ?? tx.id});
    _showBlockingProgress('Generating receipt…');
    try {
      final bytes = await _generateReceiptPdf(tx);
      if (!mounted) return;
      Navigator.of(context).pop();
      final datePart = DateFormat('yyyy-MM-dd').format(tx.createdAt);
      await _sharePdf(
        bytes: bytes,
        filename: 'jovi-receipt-$datePart.pdf',
      );
    } catch (e) {
      _logError('receipt generation failed', e);
      if (!mounted) return;
      Navigator.of(context).pop();
      _showSnackBar('Couldn\'t generate receipt.', isError: true);
    }
  }

  Future<void> _downloadStatementFor(String monthKey, String monthLabel) async {
    final monthTransactions = _transactionsForMonth(monthKey);
    if (monthTransactions.isEmpty) {
      _showSnackBar('No transactions in $monthLabel.', isInfo: true);
      return;
    }
    _analytics('billing_statement_downloaded', {'monthKey': monthKey});
    _showBlockingProgress('Generating statement…');
    try {
      final bytes = await _generateMonthlyStatementPdf(
        monthKey: monthKey,
        monthLabel: monthLabel,
        monthTransactions: monthTransactions,
      );
      if (!mounted) return;
      Navigator.of(context).pop();
      await _sharePdf(
        bytes: bytes,
        filename: 'jovi-statement-$monthKey.pdf',
      );
    } catch (e) {
      _logError('statement generation failed', e);
      if (!mounted) return;
      Navigator.of(context).pop();
      _showSnackBar('Couldn\'t generate statement.', isError: true);
    }
  }

  // (state class continues in subsequent parts)
  // =======================================================================
  // SHARED UI HELPERS
  // =======================================================================

  Widget _glassCard({
    required Widget child,
    double bgOpacity = 0.07,
    double borderOpacity = 0.14,
    double borderWidth = 1.0,
    EdgeInsetsGeometry? padding,
    double borderRadius = 16,
    Color? borderTint,
  }) {
    // Painted glass: these cards sit in a ListView over an opaque navy
    // gradient, where a live blur is pure GPU cost.
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
    bool isLoading = false,
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
    final icon = isLoading
        ? CupertinoIcons.hourglass
        : isError
            ? CupertinoIcons.exclamationmark_circle
            : isSuccess
                ? CupertinoIcons.checkmark_circle
                : isInfo
                    ? CupertinoIcons.info_circle
                    : CupertinoIcons.info_circle;
    ScaffoldMessenger.maybeOf(context)?.hideCurrentSnackBar();
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(message,
        accent: bg == _joviNavyMid ? Colors.white70 : bg,
        icon: icon,
        duration: Duration(seconds: isError ? 5 : 3)));
  }

  Future<bool?> _showConfirmDialog({
    required String title,
    required String body,
    required String confirmLabel,
    String cancelLabel = 'Cancel',
    bool destructive = false,
  }) async {
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
            child: Text(cancelLabel),
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
                        valueColor: AlwaysStoppedAnimation<Color>(_joviCoral),
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

  // (state class continues in subsequent parts)
  // =======================================================================
  // BUILD
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
        body: Container(
          width: MediaQuery.of(context).size.width,
          height: MediaQuery.of(context).size.height,
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [_joviNavyDark, _joviNavy, _joviNavyLight],
            ),
          ),
          child: Stack(
            children: [
              // Ambient coral blob (matches Quote Payment's look)
              Positioned(
                top: 40,
                right: -60,
                child: IgnorePointer(
                  child: Container(
                    width: 220,
                    height: 220,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: RadialGradient(colors: [
                        _joviCoral.withOpacity(0.09),
                        Colors.transparent,
                      ]),
                    ),
                  ),
                ),
              ),
              SafeArea(
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
            ],
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
                const Text(
                  'Billing',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.6,
                    height: 1.1,
                  ),
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
    if (_loadingUser) return 'Loading your billing…';
    if (_userError != null) return 'Something went wrong';
    if (_summary.hasFailedPayment) return 'Action required';
    return 'Your plan, cards, and receipts';
  }

  Widget _buildBody() {
    if (_loadingUser) {
      return const Center(
        child: SizedBox(
          width: 34,
          height: 34,
          child: CircularProgressIndicator(
            strokeWidth: 2.8,
            valueColor: AlwaysStoppedAnimation<Color>(_joviCoral),
          ),
        ),
      );
    }
    if (_userError != null) {
      return _buildErrorState();
    }
    return ListView(
      padding: const EdgeInsets.fromLTRB(14, 4, 14, 40),
      children: [
        if (_summary.hasFailedPayment) ...[
          _buildFailedPaymentBanner(),
          const SizedBox(height: 14),
        ],
        _buildPlanSummaryCard(),
        const SizedBox(height: 14),
        _buildPaymentMethodCard(),
        const SizedBox(height: 20),
        _buildHistoryHeader(),
        const SizedBox(height: 10),
        _buildFilterChips(),
        const SizedBox(height: 14),
        ..._buildHistoryList(),
      ],
    );
  }

  Widget _buildErrorState() {
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
                color: _joviErrorRed.withOpacity(0.12),
                borderRadius: BorderRadius.circular(22),
                border: Border.all(
                  color: _joviErrorRed.withOpacity(0.3),
                  width: 1,
                ),
              ),
              child: const Icon(
                Icons.error_outline_rounded,
                color: _joviErrorRed,
                size: 38,
              ),
            ),
            const SizedBox(height: 20),
            Text(
              _userError ?? 'Something went wrong',
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 17,
                fontWeight: FontWeight.w800,
                letterSpacing: -0.3,
                height: 1.35,
              ),
            ),
            const SizedBox(height: 18),
            _PressableMaterial(
              child: InkWell(
                onTap: () {
                  setState(() {
                    _loadingUser = true;
                    _userError = null;
                  });
                  _subscribe();
                },
                borderRadius: BorderRadius.circular(13),
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 22, vertical: 12),
                  decoration: BoxDecoration(
                    color: _joviCoral,
                    borderRadius: BorderRadius.circular(13),
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.refresh_rounded,
                          color: Colors.white, size: 16),
                      SizedBox(width: 7),
                      Text(
                        'Try again',
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
          ],
        ),
      ),
    );
  }

  // =======================================================================
  // FAILED PAYMENT BANNER
  // When the user doc's lastChargeStatus is 'failed' / 'past_due',
  // show a prominent red banner at the top of the widget with two
  // actions: "Update card" (opens editor) and "Retry charge" (calls
  // the retry CF). The banner dismisses automatically when the user
  // doc updates (typically after a successful retry or card update
  // that triggers a successful retry).
  // =======================================================================

  Widget _buildFailedPaymentBanner() {
    final amount = _summary.lastChargeAmount;
    final attemptAt = _summary.lastChargeAttemptAt;
    final errMsg = _summary.lastChargeError;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            _joviErrorRed.withOpacity(0.22),
            _joviErrorRed.withOpacity(0.08),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: _joviErrorRed.withOpacity(0.6),
          width: 1.2,
        ),
        boxShadow: [
          BoxShadow(
            color: _joviErrorRed.withOpacity(0.25),
            blurRadius: 14,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: _joviErrorRed.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: _joviErrorRed.withOpacity(0.4),
                    width: 0.8,
                  ),
                ),
                child: const Icon(
                  Icons.warning_amber_rounded,
                  color: _joviErrorRed,
                  size: 18,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Text(
                      'Payment failed',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                        letterSpacing: -0.2,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      amount != null
                          ? 'Your charge for \$${amount.toStringAsFixed(2)} didn\'t go through.'
                          : 'Your last charge didn\'t go through.',
                      style: const TextStyle(
                        color: _textSecondary,
                        fontSize: 12.5,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          if (errMsg != null && errMsg.isNotEmpty) ...[
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Colors.black.withOpacity(0.2),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                errMsg,
                style: const TextStyle(
                  color: _textSecondary,
                  fontSize: 11.5,
                  fontWeight: FontWeight.w500,
                  height: 1.4,
                ),
              ),
            ),
          ],
          if (attemptAt != null) ...[
            const SizedBox(height: 8),
            Text(
              'Last attempted ${DateFormat('MMM d, y • h:mm a').format(attemptAt)}',
              style: const TextStyle(
                color: _textTertiary,
                fontSize: 11,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: _PressableMaterial(
                  child: InkWell(
                    onTap: () {
                      HapticFeedback.lightImpact();
                      _openUpdateCardSheet();
                    },
                    borderRadius: BorderRadius.circular(11),
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      decoration: BoxDecoration(
                        color: _joviCoral,
                        borderRadius: BorderRadius.circular(11),
                        boxShadow: [
                          BoxShadow(
                            color: _joviCoral.withOpacity(0.35),
                            blurRadius: 10,
                            offset: const Offset(0, 3),
                          ),
                        ],
                      ),
                      child: const Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.credit_card_rounded,
                              color: Colors.white, size: 15),
                          SizedBox(width: 6),
                          Text(
                            'Update bank account',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 13,
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
              if (_cardOnFile.hasCard) ...[
                const SizedBox(width: 8),
                Expanded(
                  child: _PressableMaterial(
                    child: InkWell(
                      onTap: () {
                        HapticFeedback.lightImpact();
                        _retryFailedCharge();
                      },
                      borderRadius: BorderRadius.circular(11),
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(11),
                          border: Border.all(
                            color: Colors.white.withOpacity(0.2),
                            width: 1,
                          ),
                        ),
                        child: const Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.refresh_rounded,
                                color: Colors.white, size: 15),
                            SizedBox(width: 6),
                            Text(
                              'Retry charge',
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 13,
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
              ],
            ],
          ),
        ],
      ),
    );
  }

  // (state class continues in subsequent parts)
  // =======================================================================
  // PLAN SUMMARY CARD
  // Shows monthly total, health/pet breakdown, and next bill date.
  // The navy gradient mirrors the Total Monthly Plan card used in
  // Onboarding Update's quote summary for brand consistency.
  // =======================================================================

  Widget _buildPlanSummaryCard() {
    final hasTotal = _summary.monthlyTotal > 0;
    final hasHealth =
        _summary.healthPremium != null && _summary.healthPremium! > 0;
    final hasPet = _summary.petPremium != null && _summary.petPremium! > 0;

    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [_joviNavy, _joviNavyDark],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: Colors.white.withOpacity(0.1),
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.2),
            blurRadius: 14,
            offset: const Offset(0, 5),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 34,
                height: 34,
                decoration: BoxDecoration(
                  color: _joviCoral.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: _joviCoral.withOpacity(0.4),
                    width: 0.8,
                  ),
                ),
                child: const Icon(
                  Icons.receipt_long_rounded,
                  color: _joviCoral,
                  size: 17,
                ),
              ),
              const SizedBox(width: 10),
              const Expanded(
                child: Text(
                  'Monthly plan',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 14,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -0.2,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                hasTotal ? _summary.displayMonthlyTotal : '—',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 34,
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.8,
                  height: 1.0,
                ),
              ),
              if (hasTotal) ...[
                const SizedBox(width: 4),
                const Padding(
                  padding: EdgeInsets.only(bottom: 6),
                  child: Text(
                    '/mo',
                    style: TextStyle(
                      color: _textTertiary,
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ],
          ),
          if (hasHealth || hasPet) ...[
            const SizedBox(height: 12),
            Row(
              children: [
                if (hasHealth) ...[
                  _buildSummaryPill(
                    icon: Icons.health_and_safety_outlined,
                    label: 'Health',
                    value: '\$${_summary.healthPremium!.toStringAsFixed(2)}',
                    color: _joviMint,
                  ),
                  const SizedBox(width: 8),
                ],
                if (hasPet)
                  _buildSummaryPill(
                    icon: Icons.pets_outlined,
                    label: 'Pets',
                    value: '\$${_summary.petPremium!.toStringAsFixed(2)}',
                    color: _joviCoral,
                  ),
              ],
            ),
          ],
          if (_summary.nextBillDate != null) ...[
            const SizedBox(height: 14),
            Divider(
              height: 1,
              color: Colors.white.withOpacity(0.08),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                const Icon(
                  Icons.calendar_today_outlined,
                  color: _textTertiary,
                  size: 13,
                ),
                const SizedBox(width: 7),
                Text(
                  'Next bill ${DateFormat('MMM d, y').format(_summary.nextBillDate!)}',
                  style: const TextStyle(
                    color: _textSecondary,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                if (_summary.lastPaymentDate != null) ...[
                  const SizedBox(width: 10),
                  Container(
                    width: 3,
                    height: 3,
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.3),
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Text(
                    'Paid ${DateFormat('MMM d').format(_summary.lastPaymentDate!)}',
                    style: const TextStyle(
                      color: _textTertiary,
                      fontSize: 11.5,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildSummaryPill({
    required IconData icon,
    required String label,
    required String value,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        color: color.withOpacity(0.14),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: color.withOpacity(0.3),
          width: 0.8,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, color: color, size: 12),
          const SizedBox(width: 5),
          Text(
            label,
            style: TextStyle(
              color: color,
              fontSize: 11,
              fontWeight: FontWeight.w800,
              letterSpacing: 0.2,
            ),
          ),
          const SizedBox(width: 5),
          Text(
            value,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 11.5,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }

  // =======================================================================
  // PAYMENT METHOD CARD
  // Shows the saved card's brand + last4 + expiry, with an "Update"
  // button. If no metadata (payarcCustomerId present but no last4),
  // shows a generic "Card on file" with a nudge to update so we can
  // pick up the metadata. If no card at all, shows "Add payment method".
  // =======================================================================

  Widget _buildPaymentMethodCard() {
    return _glassCard(
      bgOpacity: 0.07,
      borderOpacity: 0.14,
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 34,
                height: 34,
                decoration: BoxDecoration(
                  color: _joviCoral.withOpacity(0.16),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: _joviCoral.withOpacity(0.3),
                    width: 0.8,
                  ),
                ),
                child: const Icon(
                  Icons.credit_card_rounded,
                  color: _joviCoral,
                  size: 17,
                ),
              ),
              const SizedBox(width: 10),
              const Expanded(
                child: Text(
                  'Payment method',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 14,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -0.2,
                  ),
                ),
              ),
              if (_cardOnFile.hasCard)
                _PressableMaterial(
                  child: InkWell(
                    onTap: () {
                      HapticFeedback.lightImpact();
                      _openUpdateCardSheet();
                    },
                    borderRadius: BorderRadius.circular(9),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 11, vertical: 6),
                      decoration: BoxDecoration(
                        color: _joviCoral.withOpacity(0.18),
                        borderRadius: BorderRadius.circular(9),
                        border: Border.all(
                          color: _joviCoral.withOpacity(0.35),
                          width: 0.8,
                        ),
                      ),
                      child: const Text(
                        'Update',
                        style: TextStyle(
                          color: _joviCoralLight,
                          fontSize: 12,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 0.1,
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 14),
          if (_cardOnFile.hasCard) ...[
            _buildCardTile(),
            if (!_cardOnFile.hasMetadata) ...[
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: _joviGold.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: _joviGold.withOpacity(0.35),
                    width: 1,
                  ),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(
                      Icons.info_outline_rounded,
                      color: _joviGold,
                      size: 15,
                    ),
                    const SizedBox(width: 7),
                    Expanded(
                      child: Text(
                        'Your card is on file but we don\'t have the details to display. Update your card to show the brand, last-4, and expiry.',
                        style: TextStyle(
                          color: _joviGold.withOpacity(0.95),
                          fontSize: 11.5,
                          fontWeight: FontWeight.w500,
                          height: 1.4,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
            if (_cardOnFile.isExpired) ...[
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: _joviErrorRed.withOpacity(0.14),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: _joviErrorRed.withOpacity(0.4),
                    width: 1,
                  ),
                ),
                child: Row(
                  children: [
                    const Icon(
                      Icons.error_outline_rounded,
                      color: _joviErrorRed,
                      size: 15,
                    ),
                    const SizedBox(width: 7),
                    const Expanded(
                      child: Text(
                        'This card has expired. Update it to avoid a payment failure.',
                        style: TextStyle(
                          color: _joviErrorRed,
                          fontSize: 11.5,
                          fontWeight: FontWeight.w600,
                          height: 1.4,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ] else if (_cardOnFile.expiresThisMonth) ...[
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: _joviGold.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: _joviGold.withOpacity(0.35),
                    width: 1,
                  ),
                ),
                child: Row(
                  children: [
                    const Icon(
                      Icons.warning_amber_rounded,
                      color: _joviGold,
                      size: 15,
                    ),
                    const SizedBox(width: 7),
                    Expanded(
                      child: Text(
                        'This card expires this month — update it before your next bill.',
                        style: TextStyle(
                          color: _joviGold.withOpacity(0.95),
                          fontSize: 11.5,
                          fontWeight: FontWeight.w600,
                          height: 1.4,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
            const SizedBox(height: 8),
            // Remove card — secondary action, kept small
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                onPressed: _deleteCard,
                icon: const Icon(
                  Icons.delete_outline_rounded,
                  size: 14,
                  color: _textTertiary,
                ),
                label: const Text(
                  'Remove bank account',
                  style: TextStyle(
                    color: _textTertiary,
                    fontSize: 11.5,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                style: TextButton.styleFrom(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                  minimumSize: const Size(44, 44),
                ),
              ),
            ),
          ] else ...[
            // No card on file
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.04),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: Colors.white.withOpacity(0.1),
                  width: 1,
                ),
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Icon(
                    Icons.credit_card_off_rounded,
                    color: Colors.white.withOpacity(0.3),
                    size: 34,
                  ),
                  const SizedBox(height: 10),
                  const Text(
                    'No payment method on file',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 13.5,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Add a card to keep your membership active.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.6),
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 14),
                  _PressableMaterial(
                    child: InkWell(
                      onTap: () {
                        HapticFeedback.lightImpact();
                        _openUpdateCardSheet();
                      },
                      borderRadius: BorderRadius.circular(11),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 20, vertical: 10),
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [_joviCoral, _joviCoralLight],
                          ),
                          borderRadius: BorderRadius.circular(11),
                          boxShadow: [
                            BoxShadow(
                              color: _joviCoral.withOpacity(0.35),
                              blurRadius: 10,
                              offset: const Offset(0, 3),
                            ),
                          ],
                        ),
                        child: const Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.add_rounded,
                                color: Colors.white, size: 15),
                            SizedBox(width: 5),
                            Text(
                              'Add bank account',
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 13,
                                fontWeight: FontWeight.w800,
                                letterSpacing: 0.1,
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
          ],
        ],
      ),
    );
  }

  /// Detail tile for the saved card — brand icon, last4, expiry.
  Widget _buildCardTile() {
    final brand = _cardOnFile.brand;
    final brandLabel = _cardBrandLabel(brand);

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            _joviNavyLight.withOpacity(0.7),
            _joviNavyMid.withOpacity(0.7),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: Colors.white.withOpacity(0.1),
          width: 1,
        ),
      ),
      child: Row(
        children: [
          // Brand badge — text-based, no external logos
          Container(
            width: 48,
            height: 34,
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(7),
            ),
            alignment: Alignment.center,
            child: Text(
              _cardBrandShort(brand),
              style: TextStyle(
                color: _brandBadgeColor(brand),
                fontSize: 11,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.3,
              ),
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
                    Text(
                      brandLabel,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 14,
                        fontWeight: FontWeight.w800,
                        letterSpacing: -0.2,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      '•••• ${_cardOnFile.displayLast4}',
                      style: const TextStyle(
                        color: _textSecondary,
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 3),
                Text(
                  'Exp ${_cardOnFile.displayExpiry}',
                  style: const TextStyle(
                    color: _textTertiary,
                    fontSize: 11.5,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0.3,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  /// Short 2-4 letter brand badge for the payment tile.
  String _cardBrandShort(CardBrand brand) {
    switch (brand) {
      case CardBrand.visa:
        return 'VISA';
      case CardBrand.mastercard:
        return 'MC';
      case CardBrand.amex:
        return 'AMEX';
      case CardBrand.discover:
        return 'DISC';
      case CardBrand.diners:
        return 'DINERS';
      case CardBrand.jcb:
        return 'JCB';
      case CardBrand.unionpay:
        return 'UPI';
      case CardBrand.ach:
        return 'ACH';
      case CardBrand.unknown:
        return 'CARD';
    }
  }

  /// Brand-colored text for the white badge. We use approximations
  /// of the brands' primary colors.
  Color _brandBadgeColor(CardBrand brand) {
    switch (brand) {
      case CardBrand.visa:
        return const Color(0xFF1A1F71);
      case CardBrand.mastercard:
        return const Color(0xFFEB001B);
      case CardBrand.amex:
        return const Color(0xFF006FCF);
      case CardBrand.discover:
        return const Color(0xFFFF6000);
      case CardBrand.diners:
        return const Color(0xFF0079BE);
      case CardBrand.jcb:
        return const Color(0xFF0E4C96);
      case CardBrand.unionpay:
        return const Color(0xFFE21836);
      case CardBrand.ach:
        return _joviMint;
      case CardBrand.unknown:
        return _joviNavy;
    }
  }

  // (state class continues in subsequent parts)
  // =======================================================================
  // HISTORY HEADER & FILTER CHIPS
  // =======================================================================

  Widget _buildHistoryHeader() {
    return Row(
      children: [
        const Expanded(
          child: Text(
            'Transaction History',
            style: TextStyle(
              color: Colors.white,
              fontSize: 16,
              fontWeight: FontWeight.w700,
              letterSpacing: -0.3,
            ),
          ),
        ),
        if (_transactions.isNotEmpty)
          _PressableMaterial(
            child: InkWell(
              onTap: () {
                HapticFeedback.lightImpact();
                _showStatementPicker();
              },
              borderRadius: BorderRadius.circular(9),
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 11, vertical: 6),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.08),
                  borderRadius: BorderRadius.circular(9),
                  border: Border.all(
                    color: Colors.white.withOpacity(0.18),
                    width: 0.8,
                  ),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.download_rounded, color: Colors.white, size: 13),
                    SizedBox(width: 5),
                    Text(
                      'Statement',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight: FontWeight.w800,
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

  Widget _buildFilterChips() {
    final filters = <_FilterOption>[
      _FilterOption(label: 'All', filter: null),
      _FilterOption(label: 'Membership', filter: TxType.membershipMonthly),
      _FilterOption(label: 'Pets', filter: TxType.petAddonProration),
      _FilterOption(label: 'Refunds', filter: TxType.refund),
    ];
    return SizedBox(
      height: 32,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: filters.length,
        separatorBuilder: (_, __) => const SizedBox(width: 6),
        itemBuilder: (ctx, i) {
          final opt = filters[i];
          final selected =
              _filter == opt.filter || (_filter == null && opt.filter == null);
          return _PressableMaterial(
            child: InkWell(
              onTap: () {
                HapticFeedback.selectionClick();
                setState(() => _filter = opt.filter);
              },
              borderRadius: BorderRadius.circular(9),
              child: AnimatedContainer(
                duration: _Motion.select,
                curve: _Motion.settle,
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  gradient: selected
                      ? const LinearGradient(
                          colors: [_joviCoral, _joviCoralDark],
                        )
                      : null,
                  color: selected ? null : Colors.white.withOpacity(0.06),
                  borderRadius: BorderRadius.circular(9),
                  border: Border.all(
                    color: selected
                        ? _joviCoral.withOpacity(0.5)
                        : Colors.white.withOpacity(0.12),
                    width: 1,
                  ),
                  boxShadow: selected
                      ? [
                          BoxShadow(
                            color: _joviCoral.withOpacity(0.3),
                            blurRadius: 8,
                            offset: const Offset(0, 2),
                          ),
                        ]
                      : null,
                ),
                child: Center(
                  child: Text(
                    opt.label,
                    style: TextStyle(
                      color: selected ? Colors.white : _textSecondary,
                      fontSize: 12,
                      fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
                      letterSpacing: 0.1,
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

  // =======================================================================
  // HISTORY LIST
  // Groups by month, shows a section header per month with a
  // download-statement button, then a card per transaction.
  // =======================================================================

  List<Widget> _buildHistoryList() {
    if (_loadingTransactions) {
      return [
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 28),
          child: Center(
            child: SizedBox(
              width: 22,
              height: 22,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                valueColor: AlwaysStoppedAnimation<Color>(_joviCoral),
              ),
            ),
          ),
        ),
      ];
    }

    final txns = _filteredTransactions;
    if (txns.isEmpty) {
      return [_buildEmptyHistoryState()];
    }

    final groups = _groupByMonth(txns);
    final widgets = <Widget>[];
    for (final group in groups) {
      widgets.add(_buildMonthHeader(group));
      for (final tx in group.transactions) {
        widgets.add(const SizedBox(height: 8));
        widgets.add(_buildTransactionCard(tx));
      }
      widgets.add(const SizedBox(height: 18));
    }
    return widgets;
  }

  Widget _buildEmptyHistoryState() {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 40, horizontal: 20),
      child: Center(
        child: Column(
          children: [
            Container(
              width: 62,
              height: 62,
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.06),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: Colors.white.withOpacity(0.12),
                  width: 1,
                ),
              ),
              child: Icon(
                Icons.receipt_long_outlined,
                color: Colors.white.withOpacity(0.35),
                size: 28,
              ),
            ),
            const SizedBox(height: 14),
            Text(
              _filter == null
                  ? 'No transactions yet'
                  : 'No transactions match this filter',
              style: const TextStyle(
                color: Colors.white,
                fontSize: 14,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              _filter == null
                  ? 'Charges will show up here once your first bill runs.'
                  : 'Try a different filter to see more.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white.withOpacity(0.5),
                fontSize: 12,
                fontWeight: FontWeight.w500,
                height: 1.4,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMonthHeader(_MonthGroup group) {
    final total = group.transactions.fold<double>(
      0.0,
      (sum, t) =>
          t.status == TxStatus.succeeded || t.status == TxStatus.refunded
              ? sum + t.amount
              : sum,
    );
    return Padding(
      padding: const EdgeInsets.only(top: 4, bottom: 4),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  group.label,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -0.1,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  '${group.transactions.length} transaction${group.transactions.length == 1 ? '' : 's'} • \$${total.toStringAsFixed(2)}',
                  style: const TextStyle(
                    color: _textTertiary,
                    fontSize: 11,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
          _PressableMaterial(
            child: InkWell(
              onTap: () {
                HapticFeedback.lightImpact();
                _downloadStatementFor(group.monthKey, group.label);
              },
              borderRadius: BorderRadius.circular(8),
              child: Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.06),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: Colors.white.withOpacity(0.14),
                    width: 0.8,
                  ),
                ),
                child: const Icon(
                  Icons.picture_as_pdf_outlined,
                  color: Colors.white,
                  size: 14,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTransactionCard(_Transaction tx) {
    final statusColor = _txStatusColor(tx.status);
    return _PressableMaterial(
      child: InkWell(
        onTap: () {
          HapticFeedback.lightImpact();
          _openTransactionDetail(tx);
        },
        borderRadius: BorderRadius.circular(14),
        child: _glassCard(
          bgOpacity: 0.05,
          borderOpacity: 0.1,
          padding: const EdgeInsets.all(12),
          borderRadius: 14,
          child: Row(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: _joviCoral.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(11),
                  border: Border.all(
                    color: _joviCoral.withOpacity(0.22),
                    width: 0.7,
                  ),
                ),
                child: Icon(
                  _txTypeIcon(tx.type),
                  color: _joviCoral,
                  size: 18,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      tx.description,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 13.5,
                        fontWeight: FontWeight.w700,
                        letterSpacing: -0.2,
                        height: 1.3,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 3),
                    Row(
                      children: [
                        Text(
                          tx.displayDate,
                          style: const TextStyle(
                            color: _textTertiary,
                            fontSize: 11,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        if (tx.status != TxStatus.succeeded) ...[
                          const SizedBox(width: 6),
                          Container(
                            width: 3,
                            height: 3,
                            decoration: BoxDecoration(
                              color: Colors.white.withOpacity(0.3),
                              shape: BoxShape.circle,
                            ),
                          ),
                          const SizedBox(width: 6),
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: statusColor.withOpacity(0.15),
                              borderRadius: BorderRadius.circular(5),
                              border: Border.all(
                                color: statusColor.withOpacity(0.3),
                                width: 0.6,
                              ),
                            ),
                            child: Text(
                              _txStatusLabel(tx.status),
                              style: TextStyle(
                                color: statusColor,
                                fontSize: 10,
                                fontWeight: FontWeight.w700,
                                letterSpacing: -0.1,
                              ),
                            ),
                          ),
                        ],
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Text(
                tx.displayAmount,
                style: TextStyle(
                  color: tx.amount < 0 ? _joviMint : Colors.white,
                  fontSize: 14.5,
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

  // =======================================================================
  // STATEMENT PICKER
  // Shown when the user taps the "Statement" button in the history
  // header. Lets them choose which month to download. If there's only
  // one month of history, we skip the picker and download directly.
  // =======================================================================

  Future<void> _showStatementPicker() async {
    final groups = _groupByMonth(_transactions);
    if (groups.isEmpty) {
      _showSnackBar('No transactions to export yet.', isInfo: true);
      return;
    }
    if (groups.length == 1) {
      await _downloadStatementFor(groups.first.monthKey, groups.first.label);
      return;
    }

    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (ctx) => _buildStatementPickerSheet(groups),
    );
  }

  Widget _buildStatementPickerSheet(List<_MonthGroup> groups) {
    return ClipRRect(
      borderRadius: const BorderRadius.vertical(top: Radius.circular(22)),
      child: BackdropFilter(
        filter: ui_dart.ImageFilter.blur(sigmaX: 18, sigmaY: 18),
        child: Container(
          decoration: BoxDecoration(
            color: _joviNavy.withOpacity(0.97),
            border: Border.all(
              color: Colors.white.withOpacity(0.1),
              width: 1,
            ),
          ),
          child: SafeArea(
            top: false,
            child: Column(
              mainAxisSize: MainAxisSize.min,
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
                const SizedBox(height: 16),
                const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 20),
                  child: Text(
                    'Download a Statement',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 17,
                      fontWeight: FontWeight.w700,
                      letterSpacing: -0.3,
                    ),
                  ),
                ),
                const SizedBox(height: 4),
                const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 20),
                  child: Align(
                    alignment: Alignment.centerLeft,
                    child: Text(
                      'Pick a month to export as PDF.',
                      style: TextStyle(
                        color: _textTertiary,
                        fontSize: 12.5,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Flexible(
                  child: ListView.builder(
                    shrinkWrap: true,
                    padding: const EdgeInsets.fromLTRB(12, 4, 12, 16),
                    itemCount: groups.length,
                    itemBuilder: (ctx, i) {
                      final group = groups[i];
                      final total =
                          group.transactions.fold<double>(0.0, (s, t) {
                        if (t.status == TxStatus.succeeded ||
                            t.status == TxStatus.refunded) {
                          return s + t.amount;
                        }
                        return s;
                      });
                      return _PressableMaterial(
                        child: InkWell(
                          onTap: () {
                            Navigator.pop(ctx);
                            _downloadStatementFor(group.monthKey, group.label);
                          },
                          borderRadius: BorderRadius.circular(10),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 12, vertical: 10),
                            child: Row(
                              children: [
                                Container(
                                  width: 34,
                                  height: 34,
                                  decoration: BoxDecoration(
                                    color: _joviCoral.withOpacity(0.14),
                                    borderRadius: BorderRadius.circular(9),
                                    border: Border.all(
                                      color: _joviCoral.withOpacity(0.3),
                                      width: 0.7,
                                    ),
                                  ),
                                  child: const Icon(
                                    Icons.picture_as_pdf_outlined,
                                    color: _joviCoral,
                                    size: 15,
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Text(
                                        group.label,
                                        style: const TextStyle(
                                          color: Colors.white,
                                          fontSize: 14,
                                          fontWeight: FontWeight.w800,
                                        ),
                                      ),
                                      const SizedBox(height: 2),
                                      Text(
                                        '${group.transactions.length} transactions • \$${total.toStringAsFixed(2)}',
                                        style: const TextStyle(
                                          color: _textTertiary,
                                          fontSize: 11.5,
                                          fontWeight: FontWeight.w500,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                const Icon(
                                  Icons.chevron_right_rounded,
                                  color: _textTertiary,
                                  size: 20,
                                ),
                              ],
                            ),
                          ),
                        ),
                      );
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

  // (state class continues in subsequent parts)
  // =======================================================================
  // TRANSACTION DETAIL SHEET
  // Shown when the user taps a row in the history list. Modal bottom
  // sheet with the full record: description, amount, status, date,
  // transaction id, payment method used, and a "Download receipt"
  // action.
  // =======================================================================

  Future<void> _openTransactionDetail(_Transaction tx) async {
    _analytics('billing_transaction_detail_opened',
        {'transactionId': tx.transactionId ?? tx.id});
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (ctx) => _buildTransactionDetailSheet(tx),
    );
  }

  Widget _buildTransactionDetailSheet(_Transaction tx) {
    final statusColor = _txStatusColor(tx.status);
    final amountColor = tx.amount < 0 ? _joviMint : Colors.white;

    return ClipRRect(
      borderRadius: const BorderRadius.vertical(top: Radius.circular(22)),
      child: BackdropFilter(
        filter: ui_dart.ImageFilter.blur(sigmaX: 20, sigmaY: 20),
        child: Container(
          decoration: BoxDecoration(
            color: _joviNavy.withOpacity(0.97),
            border: Border.all(
              color: Colors.white.withOpacity(0.1),
              width: 1,
            ),
          ),
          child: SafeArea(
            top: false,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
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
                  const SizedBox(height: 18),

                  // Header — icon + type + amount
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Container(
                              width: 44,
                              height: 44,
                              decoration: BoxDecoration(
                                color: _joviCoral.withOpacity(0.15),
                                borderRadius: BorderRadius.circular(12),
                                border: Border.all(
                                  color: _joviCoral.withOpacity(0.3),
                                  width: 0.8,
                                ),
                              ),
                              child: Icon(
                                _txTypeIcon(tx.type),
                                color: _joviCoral,
                                size: 20,
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Text(
                                    _txTypeLabel(tx.type),
                                    style: const TextStyle(
                                      color: _textTertiary,
                                      fontSize: 11,
                                      fontWeight: FontWeight.w800,
                                      letterSpacing: 0.5,
                                    ),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    tx.description,
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontSize: 16,
                                      fontWeight: FontWeight.w800,
                                      letterSpacing: -0.3,
                                      height: 1.3,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 16),
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Text(
                              tx.displayAmount,
                              style: TextStyle(
                                color: amountColor,
                                fontSize: 34,
                                fontWeight: FontWeight.w700,
                                letterSpacing: -0.8,
                                height: 1.0,
                              ),
                            ),
                            const SizedBox(width: 10),
                            Container(
                              margin: const EdgeInsets.only(bottom: 6),
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 8, vertical: 3),
                              decoration: BoxDecoration(
                                color: statusColor.withOpacity(0.15),
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(
                                  color: statusColor.withOpacity(0.35),
                                  width: 0.6,
                                ),
                              ),
                              child: Text(
                                _txStatusLabel(tx.status),
                                style: TextStyle(
                                  color: statusColor,
                                  fontSize: 10.5,
                                  fontWeight: FontWeight.w700,
                                  letterSpacing: -0.1,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 20),
                  Divider(
                    height: 1,
                    color: Colors.white.withOpacity(0.08),
                  ),
                  const SizedBox(height: 12),

                  // Detail rows
                  Padding(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
                    child: Column(
                      children: [
                        _buildDetailRow('Date', tx.displayDateTime),
                        if (tx.periodStart != null && tx.periodEnd != null)
                          _buildDetailRow(
                            'Coverage',
                            '${DateFormat('MMM d').format(tx.periodStart!)} – ${DateFormat('MMM d, y').format(tx.periodEnd!)}',
                          ),
                        _buildDetailRow(
                          'Payment method',
                          _formatPaymentMethodForDetail(tx),
                        ),
                        if (tx.transactionId != null &&
                            tx.transactionId!.isNotEmpty)
                          _buildDetailRow(
                            'Transaction ID',
                            tx.transactionId!,
                            copyable: true,
                          ),
                        _buildDetailRow(
                          'Source',
                          tx.source == 'transactions'
                              ? 'Billing system'
                              : 'Legacy record',
                          muted: true,
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 8),

                  // Actions
                  Padding(
                    padding: const EdgeInsets.fromLTRB(20, 10, 20, 20),
                    child: Row(
                      children: [
                        Expanded(
                          child: _PressableMaterial(
                            child: InkWell(
                              onTap: tx.status == TxStatus.succeeded ||
                                      tx.status == TxStatus.refunded
                                  ? () {
                                      HapticFeedback.lightImpact();
                                      Navigator.pop(context);
                                      _downloadReceiptFor(tx);
                                    }
                                  : null,
                              borderRadius: BorderRadius.circular(12),
                              child: Container(
                                padding:
                                    const EdgeInsets.symmetric(vertical: 13),
                                decoration: BoxDecoration(
                                  gradient: tx.status == TxStatus.succeeded ||
                                          tx.status == TxStatus.refunded
                                      ? const LinearGradient(
                                          colors: [_joviCoral, _joviCoralLight],
                                        )
                                      : null,
                                  color: tx.status == TxStatus.succeeded ||
                                          tx.status == TxStatus.refunded
                                      ? null
                                      : Colors.white.withOpacity(0.05),
                                  borderRadius: BorderRadius.circular(12),
                                  border: tx.status == TxStatus.succeeded ||
                                          tx.status == TxStatus.refunded
                                      ? null
                                      : Border.all(
                                          color: Colors.white.withOpacity(0.1),
                                          width: 1,
                                        ),
                                  boxShadow: tx.status == TxStatus.succeeded ||
                                          tx.status == TxStatus.refunded
                                      ? [
                                          BoxShadow(
                                            color: _joviCoral.withOpacity(0.35),
                                            blurRadius: 10,
                                            offset: const Offset(0, 3),
                                          ),
                                        ]
                                      : null,
                                ),
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Icon(
                                      Icons.download_rounded,
                                      color: tx.status == TxStatus.succeeded ||
                                              tx.status == TxStatus.refunded
                                          ? Colors.white
                                          : _textTertiary,
                                      size: 15,
                                    ),
                                    const SizedBox(width: 6),
                                    Text(
                                      'Download receipt',
                                      style: TextStyle(
                                        color: tx.status ==
                                                    TxStatus.succeeded ||
                                                tx.status == TxStatus.refunded
                                            ? Colors.white
                                            : _textTertiary,
                                        fontSize: 13.5,
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
                        const SizedBox(width: 8),
                        _PressableMaterial(
                          child: InkWell(
                            onTap: () => Navigator.pop(context),
                            borderRadius: BorderRadius.circular(12),
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 20, vertical: 13),
                              decoration: BoxDecoration(
                                color: Colors.white.withOpacity(0.08),
                                borderRadius: BorderRadius.circular(12),
                                border: Border.all(
                                  color: Colors.white.withOpacity(0.18),
                                  width: 1,
                                ),
                              ),
                              child: const Text(
                                'Close',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 13.5,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
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
        ),
      ),
    );
  }

  /// One label/value row in the detail sheet. If copyable, tapping the
  /// row copies the value to the clipboard and flashes a snackbar.
  Widget _buildDetailRow(
    String label,
    String value, {
    bool copyable = false,
    bool muted = false,
  }) {
    final valueColor = muted ? _textTertiary : Colors.white;
    return _PressableMaterial(
      child: InkWell(
        onTap: copyable
            ? () {
                Clipboard.setData(ClipboardData(text: value));
                _showSnackBar('$label copied', isInfo: true);
              }
            : null,
        borderRadius: BorderRadius.circular(8),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 4),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(
                width: 110,
                child: Text(
                  label,
                  style: const TextStyle(
                    color: _textTertiary,
                    fontSize: 11.5,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.2,
                  ),
                ),
              ),
              Expanded(
                child: Text(
                  value,
                  style: TextStyle(
                    color: valueColor,
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              if (copyable) ...[
                const SizedBox(width: 6),
                const Icon(
                  Icons.content_copy_rounded,
                  color: _textTertiary,
                  size: 13,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  /// Describe the payment method used on a specific transaction. If
  /// the transaction stored its own last4/brand, use those (historical
  /// accuracy). Otherwise fall back to the current card on file.
  String _formatPaymentMethodForDetail(_Transaction tx) {
    if (tx.cardLast4 != null && tx.cardLast4!.isNotEmpty) {
      final brand = tx.cardBrand == CardBrand.unknown
          ? 'Card'
          : _cardBrandLabel(tx.cardBrand);
      return '$brand ending in ${tx.cardLast4}';
    }
    if (_cardOnFile.hasMetadata) {
      return '${_cardBrandLabel(_cardOnFile.brand)} ending in ${_cardOnFile.displayLast4}';
    }
    return 'Bank account on file';
  }

  // (state class continues in subsequent parts)
  // =======================================================================
  // UPDATE CARD SHEET
  // Modal bottom sheet with the card editor form. The sheet itself is
  // a separate StatefulWidget (_UpdateCardSheet, defined after the
  // state class) so its own form state is cleanly scoped. On submit
  // it calls back into _updateCard on the parent state.
  // =======================================================================

  Future<void> _openUpdateCardSheet() async {
    _analytics('billing_update_bank_sheet_opened');
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (ctx) {
        return Padding(
          padding: EdgeInsets.only(
            bottom: MediaQuery.of(ctx).viewInsets.bottom,
          ),
          child: _UpdateCardSheet(
            existingCard: _cardOnFile,
            onSave: ({
              required String routingNumber,
              required String accountNumber,
              required String accountType,
              required String nameOnAccount,
            }) async {
              return _updateCard(
                routingNumber: routingNumber,
                accountNumber: accountNumber,
                accountType: accountType,
                nameOnAccount: nameOnAccount,
              );
            },
          ),
        );
      },
    );
  }

  // (state class continues in subsequent parts)
} // End of _BillingWidgetState

// =======================================================================
// HELPER CLASSES
// Top-level because they don't need access to the widget's state.
// =======================================================================

/// Filter chip option model. `filter == null` means "All".
class _FilterOption {
  final String label;
  final TxType? filter;
  const _FilterOption({required this.label, required this.filter});
}

/// Transaction grouping by month, used by the history list and the
/// statement picker. Built once per frame from the currently
/// filtered transaction list.
class _MonthGroup {
  final String monthKey; // e.g. '2026-04'
  final String label; // e.g. 'April 2026'
  final List<_Transaction> transactions;

  _MonthGroup({
    required this.monthKey,
    required this.label,
    required this.transactions,
  });
}

// =======================================================================
// INPUT FORMATTERS
// Same shape as the ones in Onboarding Update so the editing
// experience feels identical across widgets.
// =======================================================================

/// Formats a card number into groups of 4 separated by spaces as the
/// user types. Preserves digits-only.
class _CardNumberFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
  ) {
    final digits = newValue.text.replaceAll(RegExp(r'[^\d]'), '');
    final buffer = StringBuffer();
    for (int i = 0; i < digits.length; i++) {
      if (i > 0 && i % 4 == 0) buffer.write(' ');
      buffer.write(digits[i]);
    }
    final formatted = buffer.toString();
    return TextEditingValue(
      text: formatted,
      selection: TextSelection.collapsed(offset: formatted.length),
    );
  }
}

/// Auto-inserts '/' after MM in expiration input.
class _ExpirationDateFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
  ) {
    final digits = newValue.text.replaceAll('/', '');
    if (digits.length >= 3) {
      final formatted = '${digits.substring(0, 2)}/${digits.substring(2)}';
      return TextEditingValue(
        text: formatted,
        selection: TextSelection.collapsed(offset: formatted.length),
      );
    }
    if (digits.length == 2 && newValue.text.length > oldValue.text.length) {
      // Just finished typing the month — append the slash for the user.
      return TextEditingValue(
        text: '$digits/',
        selection: const TextSelection.collapsed(offset: 3),
      );
    }
    return newValue;
  }
}

// =======================================================================
// UPDATE CARD SHEET
// Stateful sheet that collects raw card data and calls back to the
// parent on submit. Keeps its own form state so it cleans up when
// dismissed.
// =======================================================================

typedef _OnSaveCard = Future<bool> Function({
  required String routingNumber,
  required String accountNumber,
  required String accountType,
  required String nameOnAccount,
});

/// Bank-account editor (ACH via BILL). Collects routing + account number,
/// hands them to the parent, and never persists them locally.
class _UpdateCardSheet extends StatefulWidget {
  const _UpdateCardSheet({
    required this.existingCard,
    required this.onSave,
  });

  final _CardOnFile existingCard;
  final _OnSaveCard onSave;

  @override
  State<_UpdateCardSheet> createState() => _UpdateCardSheetState();
}

class _UpdateCardSheetState extends State<_UpdateCardSheet> {
  final _formKey = GlobalKey<FormState>();
  final _nameCtrl = TextEditingController();
  final _routingCtrl = TextEditingController();
  final _accountCtrl = TextEditingController();
  String _type = 'CHECKING';
  bool _submitting = false;

  @override
  void dispose() {
    _nameCtrl.dispose();
    _routingCtrl.dispose();
    _accountCtrl.dispose();
    super.dispose();
  }

  InputDecoration _deco(String label, String hint, IconData icon) =>
      InputDecoration(
        labelText: label,
        hintText: hint,
        labelStyle: TextStyle(color: Colors.white.withOpacity(0.7)),
        hintStyle: TextStyle(color: Colors.white.withOpacity(0.35)),
        prefixIcon: Icon(icon, color: _joviCoral),
        filled: true,
        fillColor: Colors.white.withOpacity(0.06),
        border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: Colors.white.withOpacity(0.15))),
        enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: Colors.white.withOpacity(0.15))),
        focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: _joviCoral, width: 2)),
      );

  Future<void> _submit() async {
    if (!(_formKey.currentState?.validate() ?? false)) {
      HapticFeedback.mediumImpact();
      return;
    }
    setState(() => _submitting = true);
    final success = await widget.onSave(
      routingNumber: _routingCtrl.text.trim(),
      accountNumber: _accountCtrl.text.trim(),
      accountType: _type,
      nameOnAccount: _nameCtrl.text.trim(),
    );
    if (!mounted) return;
    setState(() => _submitting = false);
    if (success) Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final hasExisting = widget.existingCard.hasCard;
    return Container(
      decoration: const BoxDecoration(
        color: _joviNavy,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
      child: SafeArea(
        top: false,
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Center(
                  child: Container(
                    width: 38,
                    height: 4,
                    margin: const EdgeInsets.only(bottom: 16),
                    decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(2)),
                  ),
                ),
                Text(
                  hasExisting ? 'Replace bank account' : 'Add bank account',
                  style: const TextStyle(
                      color: Colors.white,
                      fontSize: 20,
                      fontWeight: FontWeight.w700,
                      letterSpacing: -0.4),
                ),
                const SizedBox(height: 4),
                Text(
                  'Your membership is debited from this account each month. Jovi never stores the account number.',
                  style: TextStyle(
                      color: Colors.white.withOpacity(0.6), fontSize: 13),
                ),
                const SizedBox(height: 18),
                TextFormField(
                  controller: _nameCtrl,
                  style: const TextStyle(color: Colors.white),
                  textCapitalization: TextCapitalization.words,
                  decoration:
                      _deco('Name on account', 'As it appears at your bank', Icons.person_outline),
                  validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _routingCtrl,
                  keyboardType: TextInputType.number,
                  style: const TextStyle(color: Colors.white),
                  decoration: _deco('Routing number', '9 digits', Icons.account_balance),
                  validator: (v) => RegExp(r'^\d{9}$').hasMatch(v ?? '')
                      ? null
                      : 'Routing number is 9 digits',
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _accountCtrl,
                  keyboardType: TextInputType.number,
                  obscureText: true,
                  style: const TextStyle(color: Colors.white),
                  decoration: _deco('Account number', '4 to 17 digits', Icons.numbers),
                  validator: (v) => RegExp(r'^\d{4,17}$').hasMatch(v ?? '')
                      ? null
                      : 'Check the account number',
                ),
                const SizedBox(height: 12),
                Row(children: [
                  for (final type in const ['CHECKING', 'SAVINGS'])
                    Padding(
                      padding: const EdgeInsets.only(right: 10),
                      child: ChoiceChip(
                        label: Text(type == 'CHECKING' ? 'Checking' : 'Savings'),
                        selected: _type == type,
                        selectedColor: _joviCoral,
                        backgroundColor: Colors.white.withOpacity(0.08),
                        labelStyle: TextStyle(
                            color: _type == type
                                ? Colors.white
                                : Colors.white.withOpacity(0.7),
                            fontWeight: FontWeight.w600),
                        onSelected: (_) => setState(() => _type = type),
                      ),
                    ),
                ]),
                const SizedBox(height: 18),
                SizedBox(
                  height: 50,
                  child: ElevatedButton(
                    onPressed: _submitting ? null : _submit,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: _joviCoral,
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(14)),
                      elevation: 0,
                    ),
                    child: _submitting
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                                strokeWidth: 2, color: Colors.white))
                        : const Text('Save bank account',
                            style: TextStyle(
                                fontSize: 16, fontWeight: FontWeight.w600)),
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  'Verification can take up to two business days. Your membership stays active while we verify.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                      color: Colors.white.withOpacity(0.5), fontSize: 12),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
