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
import 'dart:math';
import 'dart:typed_data';
import 'dart:ui' as ui_dart;
import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_storage/firebase_storage.dart';
import 'package:cloud_functions/cloud_functions.dart';
import 'package:image_picker/image_picker.dart';
import 'package:intl/intl.dart';
import 'package:uuid/uuid.dart';

// -----------------------------------------------------------------------
// JOVI HEALTH — PET PROFILES
// Version: 2026.09.22-r3 (Apple HIG pass: press feedback, Cupertino
//          confirms + photo sheet, painted glass, navy toasts, title case).
//          chargePetAddon still does not exist; see Zoho Payments note.
// r2:      2026.04.21
// Build: JC-PETS-0922-003
//
// CHANGES IN r2 (vs 2026.04.18-r1):
//   - REMOVED external pet insurance fields (insuranceCarrier,
//     insurancePolicyNumber) and the "Insurance" editor section.
//     Jovi Health IS the coverage; asking members to enter a third-
//     party pet policy contradicted the value prop. The parser still
//     tolerates the old fields on read so legacy docs don't crash.
//   - EXPANDED legacy-array dual-write so onboarding + profile update
//     widgets see the full field set (gender, ageInMonths, birthdate,
//     hasPreExistingConditions, preExistingNotes, plus premium /
//     deductible / reimbursement preserved from whatever the quote
//     engine last wrote).
//   - FIXED field-name + casing drift: legacy array now uses "Dog" /
//     "Cat" / "Other" (title case) matching onboarding, and uses
//     "gender" rather than "sex". Read-side tolerates both.
//   - FIXED round-trip data loss: _Pet.fromFirestore now hydrates
//     dateOfBirth from onboarding's "MM/DD/YYYY" birthdate strings,
//     reads "gender" as sex, and parses single-string
//     preExistingNotes into the conditions list (comma / newline
//     separated). List writes round-trip by joining with ", ".
//   - PRESERVES unknown fields on legacy-array rewrite so premium /
//     deductible / reimbursement (written by onboarding / update
//     quote engine, not by Pet Profiles) survive edits here.
//   - ADDED billing integration for mid-cycle pet additions:
//       * Pricing calculated per onboarding's _calculatePetPremium
//         logic ($60 base, +$7/yr after year 1).
//       * Age enforced at 2 months minimum, 20 years maximum, with
//         breed-lifespan warnings matching onboarding.
//       * Proration charges the remainder of the current billing
//         cycle. Cycles are monthly on the renew-anniversary day
//         (e.g., renew = Jan 15 → bills on the 15th of every month).
//       * Pre-existing conditions disclosure shown before confirming.
//       * Confirmation dialog shows exact amounts before charging.
//       * Add is ATOMIC: if the charge fails, the pet is NOT saved.
//       * Saved payment method (payarcCustomerId on user doc) is
//         required — fail if missing with an "update payment method"
//         nudge.
//       * Cloud Function `chargePetAddon` is the call target.
//         It does not exist yet — the new processor Cloud Function
//         ships later. Until then, the call returns a structured
//         failure that shows the user a clear "payment system being
//         upgraded" message. When the CF lands, no client code needs
//         to change; just implement the named CF on the backend.
//   - ARCHIVE / DELETE updates petTotalPremium, numPets, and
//     hasPetInsurance on the user doc. Removed pets take effect
//     NEXT billing cycle (no proration refunds on removal).
//
// Members register pets at onboarding (users/{uid}.pets as a list of
// JSON strings). This widget is the canonical place to:
//   - Add new pets (with billing)
//   - Edit existing pet details (breed, weight, DOB, vet info, etc.)
//   - Upload and change a pet photo
//   - Track pre-existing conditions, allergies, medications
//   - Remove pets no longer in the household (archive or delete)
//
// ARCHITECTURE NOTE — dual-path storage:
// This widget writes to users/{uid}/pets/{petId} as a subcollection
// (canonical, richer schema). The onboarding + profile-update widgets
// write to users/{uid}.pets as a JSON-encoded string array.
//
// We KEEP BOTH IN SYNC:
//   - On open: MERGE-SYNC — any legacy-array entries not yet in the
//     subcollection get copied over.
//   - On save / archive / delete: DUAL-WRITE — the subcollection is
//     the source of truth, the legacy array is rewritten to reflect
//     the change while preserving any fields Pet Profiles doesn't
//     manage (premium, deductible, reimbursement).
//
// Pet Medications (users/{uid}/pets/{petId}/medications/{medId})
// depends on the subcollection path — every save here must keep
// that petId stable.
//
// BLOCK BEFORE PRODUCTION:
//   - Firestore security rules for users/{uid}/pets subcollection
//     (read / write own, no public)
//   - Firebase Storage rules for pet photos
//     (path: pet_photos/{uid}/{petId}/{uuid}.jpg)
//   - Implement `chargePetAddon` Cloud Function on the new processor
//     once it's live. Contract is documented on _callChargeAddon.
//   - Decide whether to soft-archive or hard-delete removed pets
//   - Update onboarding + profile-update widgets to write to
//     subcollection directly (eventual migration — the dual-write
//     infra here stays until then)
//   - Breed lists for dogs / cats (currently a text field — upgrade
//     to autocomplete against the curated breed list already in the
//     onboarding widget in a follow-up)
// -----------------------------------------------------------------------

// =======================================================================
// JOVI BRAND COLORS
// Kept as private constants inside this file so the widget is
// self-contained for FF custom widget paste-in.
// =======================================================================

const Color _joviCoral = Color(0xFFFF6B4A);
const Color _joviCoralDark = Color(0xFFE5583A);
const Color _joviCoralLight = Color(0xFFFF8F73);
const Color _joviNavy = Color(0xFF1A2744);
const Color _joviNavyDark = Color(0xFF0F1A2E);
const Color _joviNavyMid = Color(0xFF1F2B47);
const Color _joviMint = Color(0xFF00D4AA);
const Color _joviMintDark = Color(0xFF00B894);
const Color _joviGold = Color(0xFFFFD166);
const Color _joviGoldDark = Color(0xFFF4A41E);
const Color _joviErrorRed = Color(0xFFE53E3E);
// Pet section accent — violet, consistent with Account Menu entries
const Color _petAccent = Color(0xFFA78BFA);
const Color _petAccentDark = Color(0xFF8B6EE8);

// =======================================================================
// BILLING CONSTANTS
// =======================================================================

/// Cloud Function name that charges the saved payment method a
/// prorated amount for a newly added pet. DOES NOT EXIST YET on the
/// backend — the new processor's CF ships later. Expected contract:
///
/// INPUT (data): {
///   'userId': String,
///   'petId': String,
///   'petName': String,
///   'monthlyPremium': double,
///   'prorationAmount': double,       // amount to charge today
///   'prorationDays': int,            // days remaining in cycle
///   'cycleDays': int,                // total days in this cycle
///   'payarcCustomerId': String,      // saved payment method ref
///   'nextCycleStart': String,        // ISO-8601 date
/// }
///
/// OUTPUT (data): {
///   'success': bool,
///   'error': String?,               // user-facing message on failure
///   'errorCode': String?,           // machine-readable code
///   'transactionId': String?,       // provider tx id on success
///   'chargedAmount': double?,       // actual amount charged
/// }
///
/// Error codes the client understands:
///   - 'NO_PAYMENT_METHOD'    — payarcCustomerId invalid / missing
///   - 'CARD_DECLINED'        — issuer declined
///   - 'PROCESSOR_UNAVAILABLE' — transient processor outage
///   - anything else          — surface the `error` field as-is
// 2026-09-22: the app is moving to Zoho Payments. The `payarcCustomerId`
// gate below and this function name will both need to change when the
// Zoho Cloud Function lands; until then Add Pet always fails cleanly.
const String _chargeAddonCloudFunction = 'chargePetAddon';

/// Lower bound for monthly pet premium — matches onboarding.
const double _petBasePremium = 60.0;

/// Per-year-over-1 add-on — matches onboarding.
const double _petYearlyAddon = 7.0;

/// Enrollment age bounds — matches onboarding.
const int _petMinAgeMonths = 2;
const int _petMaxAgeYears = 20;

// =======================================================================
// BREED LISTS
// Copied verbatim from the Onboarding Update widget so Pet Profiles
// stays self-contained for FF paste-in. If the lists drift out of sync
// in the future, the on-read side tolerates arbitrary breed strings
// (including ones from older versions or the free-text fallback), so
// the worst case is a breed that doesn't appear in the dropdown for
// new pets — no data loss.
//
// When a member's existing pet has a breed that isn't in this list
// (e.g., the widget was updated and the list changed), the searchable
// dropdown still shows the saved value as the current selection; the
// user can keep it or pick a new one.
// =======================================================================

const List<String> _dogBreeds = [
  'Affenpinscher',
  'Afghan Hound',
  'Airedale Terrier',
  'Akita',
  'Alaskan Malamute',
  'American Bulldog',
  'American Eskimo Dog',
  'American Foxhound',
  'American Pit Bull Terrier',
  'American Staffordshire Terrier',
  'Australian Cattle Dog',
  'Australian Shepherd',
  'Basenji',
  'Basset Hound',
  'Beagle',
  'Belgian Malinois',
  'Bernese Mountain Dog',
  'Bichon Frise',
  'Bloodhound',
  'Border Collie',
  'Border Terrier',
  'Boston Terrier',
  'Boxer',
  'Brittany',
  'Brussels Griffon',
  'Bull Terrier',
  'Bulldog',
  'Bullmastiff',
  'Cairn Terrier',
  'Cane Corso',
  'Cavalier King Charles Spaniel',
  'Chesapeake Bay Retriever',
  'Chihuahua',
  'Chinese Crested',
  'Chinese Shar-Pei',
  'Chow Chow',
  'Cocker Spaniel',
  'Collie',
  'Corgi (Pembroke Welsh)',
  'Corgi (Cardigan Welsh)',
  'Dachshund',
  'Dalmatian',
  'Doberman Pinscher',
  'English Setter',
  'English Springer Spaniel',
  'French Bulldog',
  'German Shepherd',
  'German Shorthaired Pointer',
  'Golden Retriever',
  'Gordon Setter',
  'Great Dane',
  'Great Pyrenees',
  'Greyhound',
  'Havanese',
  'Irish Setter',
  'Irish Wolfhound',
  'Italian Greyhound',
  'Jack Russell Terrier',
  'Japanese Chin',
  'Keeshond',
  'Kerry Blue Terrier',
  'Labrador Retriever',
  'Lhasa Apso',
  'Maltese',
  'Mastiff',
  'Miniature Pinscher',
  'Miniature Schnauzer',
  'Newfoundland',
  'Norfolk Terrier',
  'Norwegian Elkhound',
  'Old English Sheepdog',
  'Papillon',
  'Pekingese',
  'Pointer',
  'Pomeranian',
  'Poodle (Standard)',
  'Poodle (Miniature)',
  'Poodle (Toy)',
  'Pug',
  'Rhodesian Ridgeback',
  'Rottweiler',
  'Saint Bernard',
  'Samoyed',
  'Schipperke',
  'Scottish Terrier',
  'Shetland Sheepdog',
  'Shiba Inu',
  'Shih Tzu',
  'Siberian Husky',
  'Soft Coated Wheaten Terrier',
  'Staffordshire Bull Terrier',
  'Vizsla',
  'Weimaraner',
  'West Highland White Terrier',
  'Whippet',
  'Wire Fox Terrier',
  'Yorkshire Terrier',
  'Mixed Breed (Small)',
  'Mixed Breed (Medium)',
  'Mixed Breed (Large)',
  'Other',
];

const List<String> _catBreeds = [
  'Abyssinian',
  'American Bobtail',
  'American Curl',
  'American Shorthair',
  'American Wirehair',
  'Balinese',
  'Bengal',
  'Birman',
  'Bombay',
  'British Longhair',
  'British Shorthair',
  'Burmese',
  'Burmilla',
  'Chartreux',
  'Chausie',
  'Cornish Rex',
  'Devon Rex',
  'Domestic Longhair',
  'Domestic Medium Hair',
  'Domestic Shorthair',
  'Egyptian Mau',
  'Exotic Shorthair',
  'Havana Brown',
  'Himalayan',
  'Japanese Bobtail',
  'Javanese',
  'Korat',
  'LaPerm',
  'Maine Coon',
  'Manx',
  'Munchkin',
  'Nebelung',
  'Norwegian Forest Cat',
  'Ocicat',
  'Oriental Longhair',
  'Oriental Shorthair',
  'Persian',
  'Peterbald',
  'Pixie-Bob',
  'Ragamuffin',
  'Ragdoll',
  'Russian Blue',
  'Savannah',
  'Scottish Fold',
  'Selkirk Rex',
  'Siamese',
  'Siberian',
  'Singapura',
  'Snowshoe',
  'Somali',
  'Sphynx',
  'Thai',
  'Tonkinese',
  'Toyger',
  'Turkish Angora',
  'Turkish Van',
  'Mixed Breed',
  'Other',
];

/// Return the correct breed list for a given pet type. For
/// PetType.other (exotic pets), returns an empty list — the dropdown
/// isn't shown and the user falls back to a free-text entry.
List<String> _breedsFor(PetType t) {
  switch (t) {
    case PetType.dog:
      return _dogBreeds;
    case PetType.cat:
      return _catBreeds;
    case PetType.other:
      return const [];
  }
}

// =======================================================================
// LOGGING HELPERS
// No-op stubs; swap for Firebase Analytics / Crashlytics when ready.
// =======================================================================

void _log(String msg) {
  // ignore: avoid_print
  debugPrint('[PetProfiles] $msg');
}

void _logError(String msg, Object? err) {
  // ignore: avoid_print
  debugPrint('[PetProfiles][ERROR] $msg: $err');
}

void _analytics(String event, [Map<String, String?>? props]) {
  if (props == null || props.isEmpty) {
    _log('analytics: $event');
  } else {
    _log('analytics: $event $props');
  }
}

// =======================================================================
// PET TYPE ENUM
// We intentionally keep this narrow — most members have dogs or cats.
// "Other" keeps the field open for exotic pets with a free-text label.
//
// SERIALIZATION: we write TITLE CASE ("Dog" / "Cat" / "Other") to
// match the onboarding widget. The parser tolerates lowercase
// ("dog" / "cat") for backward compatibility with pets written by
// the r1 build.
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

IconData _petTypeIcon(PetType t) {
  switch (t) {
    case PetType.dog:
      return Icons.pets_rounded;
    case PetType.cat:
      return Icons.pets_rounded; // Material lacks a cat-specific icon
    case PetType.other:
      return Icons.pets_outlined;
  }
}

/// Serialize pet type for BOTH the subcollection doc and the legacy
/// array. Title case matches what the onboarding widget writes, so
/// round-trips don't corrupt the value.
String _petTypeSerialize(PetType t) {
  switch (t) {
    case PetType.dog:
      return 'Dog';
    case PetType.cat:
      return 'Cat';
    case PetType.other:
      return 'Other';
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

// =======================================================================
// SEX ENUM
// Internal model uses "sex". Legacy array uses "gender" (matches
// onboarding). Parser tolerates both on read; writer emits "gender"
// in the legacy array and "sex" in the subcollection doc.
// =======================================================================

enum PetSex { male, female, unknown }

String _petSexLabel(PetSex s) {
  switch (s) {
    case PetSex.male:
      return 'Male';
    case PetSex.female:
      return 'Female';
    case PetSex.unknown:
      return 'Unknown';
  }
}

/// Serialize for the subcollection doc (keyed as "sex"). Lowercase
/// for symmetry with the pre-r2 behavior; the parser handles both.
String _petSexSerializeSub(PetSex s) {
  switch (s) {
    case PetSex.male:
      return 'male';
    case PetSex.female:
      return 'female';
    case PetSex.unknown:
      return 'unknown';
  }
}

/// Serialize for the legacy array (keyed as "gender") — title case,
/// matches onboarding. "Unknown" is mapped to empty string so
/// onboarding doesn't display a weird label.
String _petSexSerializeLegacy(PetSex s) {
  switch (s) {
    case PetSex.male:
      return 'Male';
    case PetSex.female:
      return 'Female';
    case PetSex.unknown:
      return '';
  }
}

PetSex _petSexParse(String? raw) {
  if (raw == null) return PetSex.unknown;
  switch (raw.toLowerCase().trim()) {
    case 'male':
    case 'm':
      return PetSex.male;
    case 'female':
    case 'f':
      return PetSex.female;
    default:
      return PetSex.unknown;
  }
}
// =======================================================================
// BILLING HELPERS
// Free functions (no state) so they're easy to unit-test and reuse
// anywhere we need pricing or proration math.
// =======================================================================

/// Compute the monthly pet premium in dollars from age in months.
/// Mirrors the logic in the onboarding widget:
///   - < 2 months: ineligible (UI blocks this; we still return base
///     so that a stray caller doesn't divide by zero)
///   - 2–11 months OR 1 year: $60
///   - 1–20 years: $60 + ($yearsOver1 * $7)
///   - outside range: $60 (defensive fallback; UI blocks this)
double calculatePetMonthlyPremium(int ageInMonths) {
  if (ageInMonths <= 0) return _petBasePremium;
  if (ageInMonths >= _petMinAgeMonths && ageInMonths <= 11) {
    return _petBasePremium;
  }
  final years = (ageInMonths / 12).floor();
  if (years >= 1 && years <= _petMaxAgeYears) {
    return _petBasePremium + ((years - 1) * _petYearlyAddon);
  }
  return _petBasePremium;
}

/// Parse an age string like "2 years 3 months", "5y", "8m", "8 months"
/// into total months. Returns 0 if unparseable. Mirrors the onboarding
/// widget's parser so Pet Profiles can round-trip with it.
int parseAgeToMonths(String ageText) {
  if (ageText.isEmpty) return 0;
  final text = ageText.trim().toLowerCase();

  // "Xy Zm" / "X years Z months"
  final regYM = RegExp(r'(\d+)\s*y(?:ear|rs?)?s?\s*(\d+)\s*m(?:onth|onths|o)?');
  final matchYM = regYM.firstMatch(text);
  if (matchYM != null) {
    return int.parse(matchYM.group(1)!) * 12 + int.parse(matchYM.group(2)!);
  }

  // "Xy" / "X years"
  final regY = RegExp(r'(\d+)\s*y(?:ear|rs?)?s?$');
  final matchY = regY.firstMatch(text);
  if (matchY != null) {
    return int.parse(matchY.group(1)!) * 12;
  }

  // "Xm" / "X months"
  final regM = RegExp(r'(\d+)\s*m(?:onth|onths|o)?s?$');
  final matchM = regM.firstMatch(text);
  if (matchM != null) {
    return int.parse(matchM.group(1)!);
  }

  // Plain number: treat >= 2 as years, else months
  final plain = int.tryParse(text);
  if (plain != null) {
    return plain >= 2 ? plain * 12 : plain;
  }
  return 0;
}

/// Derive a human-readable age string from a date of birth.
/// Returns null when the DOB isn't set.
String? ageDisplayFromDob(DateTime? dob) {
  if (dob == null) return null;
  final now = DateTime.now();
  int years = now.year - dob.year;
  int months = now.month - dob.month;
  if (now.day < dob.day) months--;
  if (months < 0) {
    years--;
    months += 12;
  }
  if (years < 0) return null;
  if (years == 0) {
    if (months == 0) return 'Newborn';
    if (months == 1) return '1 month old';
    return '$months months old';
  }
  if (years == 1) {
    if (months == 0) return '1 year old';
    return '1 yr ${months}mo';
  }
  if (months == 0) return '$years years old';
  return '$years yr ${months}mo';
}

/// Total months between DOB and now. Returns 0 if DOB is null.
int ageInMonthsFromDob(DateTime? dob) {
  if (dob == null) return 0;
  final now = DateTime.now();
  int months = (now.year - dob.year) * 12 + (now.month - dob.month);
  if (now.day < dob.day) months--;
  if (months < 0) return 0;
  return months;
}

/// Format a DOB as the onboarding-compatible "MM/DD/YYYY" string.
/// Returns empty string if null.
String formatDobLegacy(DateTime? dob) {
  if (dob == null) return '';
  return DateFormat('MM/dd/yyyy').format(dob);
}

/// Parse an onboarding-style "MM/DD/YYYY" birthdate string to DateTime.
/// Returns null if unparseable. Tolerates "MM-DD-YYYY" and ISO formats
/// so docs written by different code paths all round-trip.
DateTime? parseDobLegacy(String? raw) {
  if (raw == null || raw.trim().isEmpty) return null;
  final text = raw.trim();
  // Try ISO-8601 first (matches what the subcollection stores)
  final iso = DateTime.tryParse(text);
  if (iso != null) return iso;
  // Onboarding format: MM/DD/YYYY
  for (final pattern in ['MM/dd/yyyy', 'MM-dd-yyyy', 'yyyy-MM-dd']) {
    try {
      return DateFormat(pattern).parseStrict(text);
    } catch (_) {
      // try next format
    }
  }
  return null;
}

// =======================================================================
// PRORATION MATH
// Monthly cycles aligned to the renew anniversary day. E.g., renew =
// Jan 15 means the member is billed on the 15th of every month.
//
// Renewal semantics in the onboarding widget:
//   - users/{uid}.renew is a Timestamp one year in the future from
//     the onboarding completion date.
//   - Monthly billing ticks off that anniversary day each month.
//
// Edge cases we handle:
//   - Anniversary day is 29/30/31 but this month is shorter — clamp
//     to the last day of the month (Feb 28/29, etc.).
//   - User doc has no `renew` field yet (edge case: pre-migration
//     account) — we fall back to a 30-day cycle from today. This
//     means "add a pet now, you pay $X today, plus next cycle" and
//     sets the cycle anchor going forward.
// =======================================================================

class ProrationCalc {
  /// The start date of the CURRENT billing cycle.
  final DateTime cycleStart;

  /// The start date of the NEXT billing cycle (= end of current
  /// cycle + 1 instant).
  final DateTime nextCycleStart;

  /// Total days in this cycle (cycleStart .. nextCycleStart).
  final int cycleDays;

  /// Days remaining from today (inclusive) until nextCycleStart.
  final int daysRemaining;

  /// Proration multiplier in [0.0, 1.0]. Today = 0 days remaining in
  /// the last second would be ~0; start of cycle = ~1.0.
  final double fraction;

  /// Prorated dollar amount for a given monthly premium.
  double prorate(double monthlyPremium) => monthlyPremium * fraction;

  const ProrationCalc({
    required this.cycleStart,
    required this.nextCycleStart,
    required this.cycleDays,
    required this.daysRemaining,
    required this.fraction,
  });

  /// Compute proration for a membership whose billing anniversary day
  /// is [anniversaryDay] (1-31). [today] is injectable for tests.
  ///
  /// If [anniversaryDay] is null (user has no renew date on file),
  /// we fall back to a 30-day cycle starting today — full premium
  /// charged now, next cycle in 30 days.
  factory ProrationCalc.compute({
    required int? anniversaryDay,
    DateTime? today,
  }) {
    final now = today ?? DateTime.now();
    if (anniversaryDay == null) {
      // Fallback: 30-day cycle starting today. User pays full
      // premium now and the cycle re-anchors here.
      final start = DateTime(now.year, now.month, now.day);
      final end = start.add(const Duration(days: 30));
      return ProrationCalc(
        cycleStart: start,
        nextCycleStart: end,
        cycleDays: 30,
        daysRemaining: 30,
        fraction: 1.0,
      );
    }

    // Build this month's billing anchor, clamped to the last day of
    // the month if the anniversary is later than the month has days.
    DateTime anchorFor(int year, int month, int day) {
      final lastDayOfMonth = DateTime(year, month + 1, 0).day;
      final clamped = day.clamp(1, lastDayOfMonth);
      return DateTime(year, month, clamped);
    }

    final thisMonthAnchor = anchorFor(now.year, now.month, anniversaryDay);

    DateTime cycleStart;
    DateTime nextCycleStart;

    if (!now.isBefore(thisMonthAnchor)) {
      // We're on or after this month's billing day → current cycle
      // starts this month, next cycle starts next month.
      cycleStart = thisMonthAnchor;
      nextCycleStart = anchorFor(
        now.month == 12 ? now.year + 1 : now.year,
        now.month == 12 ? 1 : now.month + 1,
        anniversaryDay,
      );
    } else {
      // Before this month's billing day → current cycle started last
      // month, ends this month.
      final prevYear = now.month == 1 ? now.year - 1 : now.year;
      final prevMonth = now.month == 1 ? 12 : now.month - 1;
      cycleStart = anchorFor(prevYear, prevMonth, anniversaryDay);
      nextCycleStart = thisMonthAnchor;
    }

    final cycleDays = nextCycleStart.difference(cycleStart).inDays;
    final todayStart = DateTime(now.year, now.month, now.day);
    int daysRemaining = nextCycleStart.difference(todayStart).inDays;
    if (daysRemaining < 0) daysRemaining = 0;
    if (daysRemaining > cycleDays) daysRemaining = cycleDays;

    final fraction = cycleDays <= 0 ? 0.0 : daysRemaining / cycleDays;

    return ProrationCalc(
      cycleStart: cycleStart,
      nextCycleStart: nextCycleStart,
      cycleDays: cycleDays,
      daysRemaining: daysRemaining,
      fraction: fraction,
    );
  }
}
// =======================================================================
// LEGACY ARRAY SNAPSHOT
// Helper returned by _readLegacyArray. Carries both the parsed map
// (keyed by petId) AND the raw list so rewrites can preserve entries
// we couldn't parse (we never want to accidentally delete those).
// =======================================================================

class _LegacyArraySnapshot {
  final Map<String, Map<String, dynamic>> parsedById;
  final List<dynamic> rawList;

  const _LegacyArraySnapshot(this.parsedById, this.rawList);
}

// =======================================================================
// PET MODEL
// Richer than the onboarding schema — adds all the fields a vet would
// want at intake. Nullable fields let members fill in over time
// without being blocked from saving.
//
// NOTE: external pet insurance fields were REMOVED in r2. The parser
// still reads the old insuranceCarrier / insurancePolicyNumber keys
// so legacy docs don't crash, but the model and writes no longer
// include them.
// =======================================================================

class _Pet {
  final String petId;
  final String name;
  final PetType type;
  final String? otherTypeLabel; // when type == other
  final String? breed;
  final PetSex sex;
  final bool? neutered;
  final DateTime? dateOfBirth;
  final double? weightLbs;
  final String? color;
  final String? microchipId;
  final String? photoUrl;
  // Vet info
  final String? primaryVetName;
  final String? primaryVetPhone;
  final String? primaryVetClinic;
  // Clinical
  final List<String> allergies;
  final List<String> preExistingConditions;
  final List<String> currentMedications;
  final String? dietaryRestrictions;
  // Misc
  final String? notes;
  // Archive support — soft delete
  final bool archived;
  // Timestamps
  final DateTime? createdAt;
  final DateTime? updatedAt;

  const _Pet({
    required this.petId,
    required this.name,
    this.type = PetType.other,
    this.otherTypeLabel,
    this.breed,
    this.sex = PetSex.unknown,
    this.neutered,
    this.dateOfBirth,
    this.weightLbs,
    this.color,
    this.microchipId,
    this.photoUrl,
    this.primaryVetName,
    this.primaryVetPhone,
    this.primaryVetClinic,
    this.allergies = const [],
    this.preExistingConditions = const [],
    this.currentMedications = const [],
    this.dietaryRestrictions,
    this.notes,
    this.archived = false,
    this.createdAt,
    this.updatedAt,
  });

  factory _Pet.fromFirestore(String docId, Map<String, dynamic> m) {
    DateTime? parseTs(dynamic v) {
      if (v == null) return null;
      if (v is Timestamp) return v.toDate();
      if (v is String) return parseDobLegacy(v);
      return null;
    }

    double? asDouble(dynamic v) {
      if (v == null) return null;
      if (v is num) return v.toDouble();
      if (v is String) return double.tryParse(v);
      return null;
    }

    /// Coerce a value into a list of trimmed, non-empty strings.
    /// Accepts List<String>, List<dynamic>, single String, or null.
    /// Single strings are split on commas + newlines so the
    /// onboarding widget's single-string preExistingNotes round-trips
    /// into our conditions list.
    List<String> asStringList(dynamic v) {
      if (v is List) {
        return v.whereType<String>().where((s) => s.trim().isNotEmpty).toList();
      }
      if (v is String && v.trim().isNotEmpty) {
        return v
            .split(RegExp(r'[,\n]'))
            .map((s) => s.trim())
            .where((s) => s.isNotEmpty)
            .toList();
      }
      return const [];
    }

    // Pre-existing conditions — two sources:
    //   (a) subcollection's preExistingConditions list
    //   (b) onboarding's single-string preExistingNotes
    // Merge both so legacy + new data both surface.
    final conditions = <String>[];
    conditions.addAll(asStringList(m['preExistingConditions']));
    if (conditions.isEmpty) {
      // Only fall back to the single-string if there's no list form
      conditions.addAll(asStringList(m['preExistingNotes']));
    }
    // Extra guard: onboarding's hasPreExistingConditions flag without
    // a notes string leaves conditions empty; that's fine.

    // Age hydration: prefer explicit dateOfBirth, then onboarding's
    // birthdate string, then compute DOB from ageInMonths if present.
    DateTime? dob = parseTs(m['dateOfBirth'] ?? m['dob'] ?? m['birthdate']);
    if (dob == null && m['ageInMonths'] is num) {
      final months = (m['ageInMonths'] as num).toInt();
      if (months > 0) {
        final now = DateTime.now();
        // Synthesize a DOB that rounds to the current day of month —
        // good enough for display; editing the pet will let them
        // correct it to the true birthdate.
        dob = DateTime(now.year, now.month - months, now.day);
      }
    }

    return _Pet(
      petId: (m['petId'] as String?) ?? docId,
      name: (m['name'] as String?)?.trim().isNotEmpty == true
          ? (m['name'] as String).trim()
          : 'Unnamed pet',
      type: _petTypeParse(m['type'] as String?),
      otherTypeLabel: m['otherTypeLabel'] as String?,
      breed: m['breed'] as String?,
      // "gender" is the onboarding key; "sex" is the subcollection
      // key. Parser accepts either.
      sex: _petSexParse((m['sex'] as String?) ?? (m['gender'] as String?)),
      neutered: m['neutered'] is bool ? m['neutered'] as bool : null,
      dateOfBirth: dob,
      weightLbs: asDouble(m['weightLbs'] ?? m['weight']),
      color: m['color'] as String?,
      microchipId: m['microchipId'] as String? ?? m['microchip'] as String?,
      photoUrl: m['photoUrl'] as String? ?? m['photo_url'] as String?,
      primaryVetName: m['primaryVetName'] as String? ?? m['vetName'] as String?,
      primaryVetPhone:
          m['primaryVetPhone'] as String? ?? m['vetPhone'] as String?,
      primaryVetClinic:
          m['primaryVetClinic'] as String? ?? m['vetClinic'] as String?,
      allergies: asStringList(m['allergies']),
      preExistingConditions: conditions,
      currentMedications:
          asStringList(m['currentMedications'] ?? m['medications']),
      dietaryRestrictions: m['dietaryRestrictions'] as String?,
      notes: m['notes'] as String?,
      archived: m['archived'] == true,
      createdAt: parseTs(m['createdAt']),
      updatedAt: parseTs(m['updatedAt']),
    );
  }

  /// Build a Firestore-compatible map for SUBCOLLECTION writes.
  /// Only includes non-null / non-empty fields to keep docs clean.
  /// Notably: no insurance fields (removed in r2).
  Map<String, dynamic> toFirestore({bool isNew = false}) {
    final data = <String, dynamic>{
      'petId': petId,
      'name': name,
      'type': _petTypeSerialize(type),
      'sex': _petSexSerializeSub(sex),
      'archived': archived,
      'updatedAt': FieldValue.serverTimestamp(),
    };
    if (isNew) {
      data['createdAt'] = FieldValue.serverTimestamp();
    }
    if (otherTypeLabel != null && otherTypeLabel!.isNotEmpty) {
      data['otherTypeLabel'] = otherTypeLabel;
    }
    if (breed != null && breed!.isNotEmpty) data['breed'] = breed;
    if (neutered != null) data['neutered'] = neutered;
    if (dateOfBirth != null) {
      data['dateOfBirth'] = Timestamp.fromDate(dateOfBirth!);
    }
    if (weightLbs != null) data['weightLbs'] = weightLbs;
    if (color != null && color!.isNotEmpty) data['color'] = color;
    if (microchipId != null && microchipId!.isNotEmpty) {
      data['microchipId'] = microchipId;
    }
    if (photoUrl != null && photoUrl!.isNotEmpty) {
      data['photoUrl'] = photoUrl;
    }
    if (primaryVetName != null && primaryVetName!.isNotEmpty) {
      data['primaryVetName'] = primaryVetName;
    }
    if (primaryVetPhone != null && primaryVetPhone!.isNotEmpty) {
      data['primaryVetPhone'] = primaryVetPhone;
    }
    if (primaryVetClinic != null && primaryVetClinic!.isNotEmpty) {
      data['primaryVetClinic'] = primaryVetClinic;
    }
    if (allergies.isNotEmpty) data['allergies'] = allergies;
    if (preExistingConditions.isNotEmpty) {
      data['preExistingConditions'] = preExistingConditions;
    }
    if (currentMedications.isNotEmpty) {
      data['currentMedications'] = currentMedications;
    }
    if (dietaryRestrictions != null && dietaryRestrictions!.isNotEmpty) {
      data['dietaryRestrictions'] = dietaryRestrictions;
    }
    if (notes != null && notes!.isNotEmpty) data['notes'] = notes;
    return data;
  }

  /// Human-readable age derived from dateOfBirth. Returns null if
  /// DOB isn't set.
  String? get ageDisplay => ageDisplayFromDob(dateOfBirth);

  /// Age in months (0 if DOB not set).
  int get ageMonths => ageInMonthsFromDob(dateOfBirth);

  /// Monthly premium if enrolled today. Returns the base premium
  /// even for ineligible ages — the UI gates ineligibility, this is
  /// just the number the member would see.
  double get monthlyPremium => calculatePetMonthlyPremium(ageMonths);

  String get displayType {
    if (type == PetType.other &&
        otherTypeLabel != null &&
        otherTypeLabel!.isNotEmpty) {
      return otherTypeLabel!;
    }
    return _petTypeLabel(type);
  }

  /// Primary subtitle line — breed + age, or just type if no breed.
  String get displaySubtitle {
    final parts = <String>[];
    if (breed != null && breed!.isNotEmpty) {
      parts.add(breed!);
    } else {
      parts.add(displayType);
    }
    final age = ageDisplay;
    if (age != null) parts.add(age);
    return parts.join(' • ');
  }

  _Pet copyWith({
    String? petId,
    String? name,
    PetType? type,
    String? otherTypeLabel,
    String? breed,
    PetSex? sex,
    bool? neutered,
    DateTime? dateOfBirth,
    double? weightLbs,
    String? color,
    String? microchipId,
    String? photoUrl,
    String? primaryVetName,
    String? primaryVetPhone,
    String? primaryVetClinic,
    List<String>? allergies,
    List<String>? preExistingConditions,
    List<String>? currentMedications,
    String? dietaryRestrictions,
    String? notes,
    bool? archived,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return _Pet(
      petId: petId ?? this.petId,
      name: name ?? this.name,
      type: type ?? this.type,
      otherTypeLabel: otherTypeLabel ?? this.otherTypeLabel,
      breed: breed ?? this.breed,
      sex: sex ?? this.sex,
      neutered: neutered ?? this.neutered,
      dateOfBirth: dateOfBirth ?? this.dateOfBirth,
      weightLbs: weightLbs ?? this.weightLbs,
      color: color ?? this.color,
      microchipId: microchipId ?? this.microchipId,
      photoUrl: photoUrl ?? this.photoUrl,
      primaryVetName: primaryVetName ?? this.primaryVetName,
      primaryVetPhone: primaryVetPhone ?? this.primaryVetPhone,
      primaryVetClinic: primaryVetClinic ?? this.primaryVetClinic,
      allergies: allergies ?? this.allergies,
      preExistingConditions:
          preExistingConditions ?? this.preExistingConditions,
      currentMedications: currentMedications ?? this.currentMedications,
      dietaryRestrictions: dietaryRestrictions ?? this.dietaryRestrictions,
      notes: notes ?? this.notes,
      archived: archived ?? this.archived,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }
}

// =======================================================================
// CHARGE RESULT
// Structured outcome of a _callChargeAddon call. Separate class so
// the save path can pattern-match on success / failure reasons without
// string-parsing error messages.
// =======================================================================

class _ChargeResult {
  final bool success;
  final String? errorMessage;
  final String? errorCode;
  final String? transactionId;
  final double? chargedAmount;

  const _ChargeResult._({
    required this.success,
    this.errorMessage,
    this.errorCode,
    this.transactionId,
    this.chargedAmount,
  });

  factory _ChargeResult.success({
    required String? transactionId,
    required double? chargedAmount,
  }) =>
      _ChargeResult._(
        success: true,
        transactionId: transactionId,
        chargedAmount: chargedAmount,
      );

  factory _ChargeResult.failure({
    required String errorMessage,
    String? errorCode,
  }) =>
      _ChargeResult._(
        success: false,
        errorMessage: errorMessage,
        errorCode: errorCode,
      );
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

class PetProfiles extends StatefulWidget {
  // No required params — uses MediaQuery for sizing.
  const PetProfiles({
    Key? key,
    this.width,
    this.height,
  }) : super(key: key);

  final double? width;
  final double? height;

  @override
  State<PetProfiles> createState() => _PetProfilesState();
}

class _PetProfilesState extends State<PetProfiles>
    with TickerProviderStateMixin {
  // ---------------- Data state ----------------
  List<_Pet> _pets = [];
  bool _loading = true;
  String? _error;
  int _retries = 0;
  static const int _maxRetries = 3;

  /// Whether the legacy-array merge has been attempted this session.
  /// We only run the merge once per widget open so repeated snapshot
  /// ticks don't trigger repeated writes.
  bool _migrationAttempted = false;

  /// Cached user-doc fields we need for billing. Loaded on
  /// subscription init and refreshed before each add-pet flow.
  int? _renewAnniversaryDay;
  String? _payarcCustomerId;

  /// Cached membership total fields, used for the "before/after" cost
  /// preview in the editor sheet. Refreshed by _loadBillingContext
  /// alongside the billing fields above.
  ///
  /// We keep all three because different widgets write different keys:
  ///   - QuotePayment writes totalPremium (health only) + petTotalPremium
  ///   - OnboardingUpdate writes grandTotal (after discounts)
  /// _currentMonthlyTotal() below reads these in preference order.
  double? _cachedHealthPremium;
  double? _cachedPetPremium;
  double? _cachedGrandTotal;

  /// Best available snapshot of the member's current monthly bill.
  /// Prefers grandTotal (post-discount) when present; otherwise sums
  /// health + pet. Returns null when we have no data yet — the editor
  /// sheet hides the before/after card in that case.
  double? get _currentMonthlyTotal {
    final g = _cachedGrandTotal;
    if (g != null && g > 0) return g;
    final h = _cachedHealthPremium ?? 0;
    final p = _cachedPetPremium ?? 0;
    if (h + p > 0) return h + p;
    return null;
  }

  // ---------------- Subscriptions ----------------
  StreamSubscription<QuerySnapshot<Map<String, dynamic>>>? _petsSub;

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
    _subscribeToPets();
    _analytics('pet_profiles_opened');
  }

  @override
  void dispose() {
    _fadeCtrl.dispose();
    _petsSub?.cancel();
    super.dispose();
  }

  // =======================================================================
  // FIRESTORE SUBSCRIPTION
  // =======================================================================

  void _subscribeToPets() {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      setState(() {
        _loading = false;
        _error = 'Sign in to manage your pets.';
      });
      return;
    }

    // Kick off a user-doc read for billing fields in parallel.
    // We don't block pet loading on it — billing fields are only
    // needed when the user actually tries to add a pet.
    unawaited(_loadBillingContext(user.uid));

    _petsSub?.cancel();
    _petsSub = FirebaseFirestore.instance
        .collection('users')
        .doc(user.uid)
        .collection('pets')
        .snapshots()
        .listen(
      (snap) async {
        if (!mounted) return;
        final pets = <_Pet>[];
        for (final doc in snap.docs) {
          try {
            final pet = _Pet.fromFirestore(doc.id, doc.data());
            if (!pet.archived) pets.add(pet);
          } catch (e) {
            _logError('skipped malformed pet doc ${doc.id}', e);
          }
        }
        // Alphabetical by name for stable display ordering
        pets.sort(
            (a, b) => a.name.toLowerCase().compareTo(b.name.toLowerCase()));

        // DUAL-WRITE COMPATIBILITY — merge sync with legacy array.
        // The onboarding + profile-update widgets write to the legacy
        // users/{uid}.pets array. We need to surface any array entries
        // that aren't already in the subcollection (e.g., pet added
        // via onboarding after the initial migration).
        //
        // Runs once per widget-open on the FIRST snapshot. After
        // that we trust the subcollection — any new pet added via
        // Pet Profiles is dual-written, and the member can always
        // close + reopen the widget to pick up onboarding additions.
        if (!_migrationAttempted) {
          _migrationAttempted = true;
          final existingIds = pets.map((p) => p.petId).toSet();
          final merged = await _mergeLegacyPets(user.uid, existingIds);
          if (merged > 0) {
            // Don't setState here — the subscription will re-fire
            // once the batched writes land and surface the merged
            // records.
            _log('merged $merged legacy pet(s); awaiting snapshot');
            return;
          }
        }

        setState(() {
          _pets = pets;
          _loading = false;
          _error = null;
          _retries = 0;
        });
      },
      onError: (err) {
        _logError('pets stream failed', err);
        if (!mounted) return;
        _handleSubscriptionError(err);
      },
      cancelOnError: false,
    );
  }

  void _handleSubscriptionError(Object err) {
    final msg = err.toString().toLowerCase();
    if (msg.contains('permission-denied')) {
      setState(() {
        _loading = false;
        _error =
            "We couldn't load your pets. Please retry, or contact support if this keeps happening.";
      });
      return;
    }
    if (_retries < _maxRetries) {
      _retries++;
      final delay = Duration(seconds: [2, 5, 10][_retries - 1]);
      _log('retrying pets subscription in ${delay.inSeconds}s (#$_retries)');
      Future.delayed(delay, () {
        if (!mounted) return;
        _subscribeToPets();
      });
    } else {
      setState(() {
        _loading = false;
        _error = "We couldn't load your pets. Please try again.";
      });
    }
  }

  /// Load the user-doc fields we need for billing: the renew
  /// anniversary day and the saved payarcCustomerId. Non-blocking —
  /// the add-pet flow re-reads if either is missing.
  Future<void> _loadBillingContext(String uid) async {
    try {
      final doc =
          await FirebaseFirestore.instance.collection('users').doc(uid).get();
      if (!doc.exists) return;
      final data = doc.data();
      if (data == null) return;
      final renew = data['renew'];
      if (renew is Timestamp) {
        _renewAnniversaryDay = renew.toDate().day;
      }
      final payarc = data['payarcCustomerId'];
      if (payarc is String && payarc.isNotEmpty) {
        _payarcCustomerId = payarc;
      }

      // Membership totals for the before/after cost preview. All three
      // may be absent on very old accounts — we just skip the preview
      // in that case, not an error.
      double? asDouble(dynamic v) {
        if (v == null) return null;
        if (v is num) return v.toDouble();
        if (v is String) return double.tryParse(v);
        return null;
      }

      final prevTotal = _currentMonthlyTotal;
      _cachedHealthPremium = asDouble(data['totalPremium']);
      _cachedPetPremium = asDouble(data['petTotalPremium']);
      _cachedGrandTotal = asDouble(data['grandTotal']);

      // If anything changed AND the widget is mounted, refresh so the
      // editor sheet (which reads via constructor props) next-opens
      // with up-to-date numbers. Non-fatal if we're mid-init.
      if (mounted && prevTotal != _currentMonthlyTotal) {
        setState(() {});
      }

      _log(
          'billing context: anniversary=$_renewAnniversaryDay, payarcCustomerId=${_payarcCustomerId == null ? "none" : "present"}, monthlyTotal=${_currentMonthlyTotal?.toStringAsFixed(2) ?? "n/a"}');
    } catch (e) {
      _logError('billing context load failed', e);
      // Non-fatal — add-pet flow surfaces a clearer error when needed.
    }
  }
  // (state class continues in subsequent parts)
  // =======================================================================
  // LEGACY ARRAY COMPATIBILITY
  // The onboarding and profile-update widgets write pets to a JSON-
  // encoded string array at users/{uid}.pets. Each entry is a JSON
  // string. Pet Profiles' canonical storage is the subcollection at
  // users/{uid}/pets/{petId}.
  //
  // To keep the three widgets in sync WITHOUT touching onboarding or
  // update, we DUAL-WRITE: every save / archive / delete mirrors to
  // the legacy array while keeping the subcollection as source of
  // truth for the richer fields.
  //
  // On widget open we MERGE-SYNC: any legacy entries whose petId
  // isn't already in the subcollection get copied over. This handles
  // "user added a pet via onboarding after the last Pet Profiles
  // open" — they'll appear on next open.
  //
  // If you ever migrate onboarding + update to write directly to
  // the subcollection, you can remove the dual-write code AND the
  // merge sync — search for "LEGACY ARRAY" comments to find all
  // touch points.
  // =======================================================================

  // Legacy field keys used by onboarding + profile-update widgets.
  // Changing these breaks compatibility.
  static const String _lfName = 'name';
  static const String _lfType = 'type';
  static const String _lfBreed = 'breed';
  static const String _lfPetId = 'petId';
  static const String _lfPhotoUrl = 'photo_url';
  static const String _lfGender = 'gender';
  static const String _lfAgeInMonths = 'ageInMonths';
  static const String _lfBirthdate = 'birthdate';
  static const String _lfHasPreEx = 'hasPreExistingConditions';
  static const String _lfPreExNotes = 'preExistingNotes';
  static const String _lfPremium = 'premium';
  static const String _lfDeductible = 'deductible';
  static const String _lfReimbursement = 'reimbursement';

  /// Build the legacy JSON-encoded string that onboarding / update
  /// expect. Emits the full onboarding field set so round-trips
  /// don't drop data. Extra fields from the richer schema stay in
  /// the subcollection.
  ///
  /// If [existingEntry] is provided, we PRESERVE its premium /
  /// deductible / reimbursement values (written by the quote engine
  /// in onboarding, not by Pet Profiles). Those fields survive edits.
  String _toLegacyJson(_Pet pet, {Map<String, dynamic>? existingEntry}) {
    final conditions = pet.preExistingConditions;
    final payload = <String, dynamic>{
      _lfName: pet.name,
      _lfType: _petTypeSerialize(pet.type),
      _lfBreed: pet.breed ?? '',
      _lfPetId: pet.petId,
      _lfPhotoUrl: pet.photoUrl ?? '',
      _lfGender: _petSexSerializeLegacy(pet.sex),
      _lfAgeInMonths: pet.ageMonths,
      _lfBirthdate: formatDobLegacy(pet.dateOfBirth),
      _lfHasPreEx: conditions.isNotEmpty,
      _lfPreExNotes: conditions.join(', '),
    };

    // Preserve quote-engine fields if they existed. Pet Profiles
    // doesn't write these itself, but if onboarding or update wrote
    // them we want them to survive an edit here.
    if (existingEntry != null) {
      for (final key in [_lfPremium, _lfDeductible, _lfReimbursement]) {
        if (existingEntry.containsKey(key)) {
          payload[key] = existingEntry[key];
        }
      }
    } else {
      // No existing entry (new pet) → seed quote-engine fields with
      // defaults so onboarding / update see sensible numbers. The
      // next run through the quote engine will overwrite these.
      payload[_lfPremium] = pet.monthlyPremium;
      payload[_lfDeductible] = 500;
      payload[_lfReimbursement] = 90;
    }

    return jsonEncode(payload);
  }

  /// Read the current legacy array. Entries without a petId are
  /// preserved in rawList but not in parsedById (we can't reliably
  /// update them).
  Future<_LegacyArraySnapshot> _readLegacyArray(String uid) async {
    try {
      final userDoc =
          await FirebaseFirestore.instance.collection('users').doc(uid).get();
      if (!userDoc.exists) {
        return const _LegacyArraySnapshot({}, []);
      }
      final data = userDoc.data();
      if (data == null) return const _LegacyArraySnapshot({}, []);
      final raw = data['pets'];
      if (raw is! List) return const _LegacyArraySnapshot({}, []);
      final parsedById = <String, Map<String, dynamic>>{};
      final rawList = <dynamic>[];
      for (final item in raw) {
        rawList.add(item);
        Map<String, dynamic>? m;
        if (item is String) {
          try {
            final d = jsonDecode(item);
            if (d is Map) m = Map<String, dynamic>.from(d);
          } catch (_) {
            // skip
          }
        } else if (item is Map) {
          m = Map<String, dynamic>.from(item);
        }
        if (m == null) continue;
        final petId = (m[_lfPetId] as String?)?.trim();
        if (petId != null && petId.isNotEmpty) {
          parsedById[petId] = m;
        }
      }
      return _LegacyArraySnapshot(parsedById, rawList);
    } catch (e) {
      _logError('legacy array read failed', e);
      return const _LegacyArraySnapshot({}, []);
    }
  }

  /// Rebuild the legacy array such that:
  ///  - Every pet in [desired] is present as a JSON string in the
  ///    legacy shape.
  ///  - Existing entries whose petId matches are REPLACED (not
  ///    duplicated) by the new serialization, with quote-engine
  ///    fields (premium / deductible / reimbursement) preserved
  ///    from the prior entry.
  ///  - Entries we couldn't parse are preserved untouched so we
  ///    never accidentally delete data we didn't understand.
  ///  - Entries whose petId is in [removeIds] are dropped.
  ///
  /// Runs as a single Firestore update on the user doc. Atomic and
  /// cheap. We prefer this over FieldValue.arrayUnion / arrayRemove
  /// because the array contains JSON strings where only a subfield
  /// (petId inside the JSON) matters for identity, which arrayRemove
  /// cannot match on.
  Future<void> _writeLegacyArray(
    String uid, {
    required List<_Pet> desired,
    Set<String> removeIds = const {},
  }) async {
    try {
      final snapshot = await _readLegacyArray(uid);
      final desiredById = {for (final p in desired) p.petId: p};
      final newList = <dynamic>[];

      // Preserve unparseable entries as-is. Preserve parseable
      // entries that AREN'T in the desired or remove sets (they
      // belong to pets Pet Profiles doesn't know about — e.g.,
      // added since last load).
      for (final raw in snapshot.rawList) {
        Map<String, dynamic>? parsed;
        if (raw is String) {
          try {
            final d = jsonDecode(raw);
            if (d is Map) parsed = Map<String, dynamic>.from(d);
          } catch (_) {
            // unparseable
          }
        } else if (raw is Map) {
          parsed = Map<String, dynamic>.from(raw);
        }
        if (parsed == null) {
          // Unparseable — keep as-is
          newList.add(raw);
          continue;
        }
        final petId = (parsed[_lfPetId] as String?)?.trim();
        if (petId == null || petId.isEmpty) {
          // No petId — keep as-is (we can't identify it)
          newList.add(raw);
          continue;
        }
        if (removeIds.contains(petId)) {
          // Drop this entry
          continue;
        }
        if (desiredById.containsKey(petId)) {
          // Will be rewritten below; skip here to avoid dupes
          continue;
        }
        // Unknown-to-Pet-Profiles pet — preserve
        newList.add(raw);
      }

      // Append / overwrite desired pets in the legacy shape,
      // preserving quote-engine fields from the existing entry.
      for (final pet in desired) {
        final existing = snapshot.parsedById[pet.petId];
        newList.add(_toLegacyJson(pet, existingEntry: existing));
      }

      await FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .update({'pets': newList});
    } catch (e) {
      _logError('legacy array write failed', e);
      // Non-fatal — subcollection write already succeeded.
    }
  }

  /// Merge any legacy-array entries whose petId isn't yet in the
  /// subcollection. Returns the number written. Used on widget open
  /// to pick up pets added via onboarding / update between sessions.
  Future<int> _mergeLegacyPets(String uid, Set<String> existingIds) async {
    try {
      final snapshot = await _readLegacyArray(uid);
      if (snapshot.parsedById.isEmpty) return 0;

      final toWrite = <_Pet>[];
      for (final entry in snapshot.parsedById.entries) {
        if (existingIds.contains(entry.key)) continue;
        final pet = _Pet.fromFirestore(entry.key, entry.value);
        toWrite.add(pet);
      }
      if (toWrite.isEmpty) return 0;

      final batch = FirebaseFirestore.instance.batch();
      for (final pet in toWrite) {
        final ref = FirebaseFirestore.instance
            .collection('users')
            .doc(uid)
            .collection('pets')
            .doc(pet.petId);
        batch.set(
          ref,
          pet.toFirestore(isNew: true),
          SetOptions(merge: true),
        );
      }
      await batch.commit();
      _log('merged ${toWrite.length} legacy pet(s) to subcollection');
      _analytics(
          'pet_profiles_legacy_merged', {'count': toWrite.length.toString()});
      return toWrite.length;
    } catch (e) {
      _logError('legacy merge failed', e);
      return 0;
    }
  }

  // (state class continues in subsequent parts)
  // =======================================================================
  // BILLING: USER-DOC SYNC
  // Keep users/{uid}.hasPetInsurance, numPets, and petTotalPremium
  // in sync with the subcollection whenever a pet is added, archived,
  // or deleted. These fields are read by other parts of the app
  // (membership card, billing screens, renewal emails) so they have
  // to stay truthful.
  //
  // The sum is computed from the CURRENT subcollection contents (not
  // from memory) so concurrent edits from other widgets don't cause
  // drift. Small table — reading all pet docs is fine.
  // =======================================================================

  /// Recompute petTotalPremium / numPets / hasPetInsurance from the
  /// subcollection and write them to the user doc. Call after every
  /// add / archive / delete.
  Future<void> _syncUserPetTotals(String uid) async {
    try {
      final snap = await FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('pets')
          .where('archived', isEqualTo: false)
          .get();

      int count = 0;
      double total = 0.0;
      for (final doc in snap.docs) {
        try {
          final pet = _Pet.fromFirestore(doc.id, doc.data());
          if (pet.archived) continue;
          count++;
          total += pet.monthlyPremium;
        } catch (e) {
          _logError('sync: skipped malformed pet ${doc.id}', e);
        }
      }

      await FirebaseFirestore.instance.collection('users').doc(uid).update({
        'numPets': count,
        'hasPetInsurance': count > 0,
        'petTotalPremium': total,
        'petTotalUpdatedAt': FieldValue.serverTimestamp(),
      });
      _log('user totals synced: numPets=$count, petTotalPremium=$total');
    } catch (e) {
      _logError('user pet totals sync failed', e);
      // Non-fatal — next sync attempt will correct it.
    }
  }

  // =======================================================================
  // BILLING: CHARGE CALL
  // Thin wrapper around the (not-yet-existing) `chargePetAddon` Cloud
  // Function. Translates the CF's structured response into a
  // _ChargeResult the save path can act on.
  //
  // The CF does not exist yet (waiting on the new processor). Until
  // then the call will fail with `unavailable` or `not-found`, which
  // we surface as "Payment system is being upgraded" to the user.
  // That's the correct behavior — atomic save means no pet is added
  // when billing can't run.
  //
  // When the CF ships, NO CLIENT CHANGES are needed as long as the
  // contract in _chargeAddonCloudFunction's doc comment is honored.
  // =======================================================================

  Future<_ChargeResult> _callChargeAddon({
    required String userId,
    required _Pet pet,
    required double monthlyPremium,
    required ProrationCalc proration,
    required String payarcCustomerId,
  }) async {
    try {
      final callable =
          FirebaseFunctions.instance.httpsCallable(_chargeAddonCloudFunction);
      final result = await callable.call(<String, dynamic>{
        'userId': userId,
        'petId': pet.petId,
        'petName': pet.name,
        'monthlyPremium': monthlyPremium,
        'prorationAmount':
            double.parse(proration.prorate(monthlyPremium).toStringAsFixed(2)),
        'prorationDays': proration.daysRemaining,
        'cycleDays': proration.cycleDays,
        'payarcCustomerId': payarcCustomerId,
        'nextCycleStart': proration.nextCycleStart.toIso8601String(),
      });

      final data = result.data;
      if (data is! Map) {
        return _ChargeResult.failure(
          errorMessage:
              'We got an unexpected response from the payment system. Please try again.',
          errorCode: 'MALFORMED_RESPONSE',
        );
      }
      final m = Map<String, dynamic>.from(data);
      if (m['success'] == true) {
        return _ChargeResult.success(
          transactionId: m['transactionId'] as String?,
          chargedAmount: m['chargedAmount'] is num
              ? (m['chargedAmount'] as num).toDouble()
              : null,
        );
      }
      final errorCode = m['errorCode'] as String?;
      final errorMessage =
          (m['error'] as String?) ?? _defaultErrorMessageFor(errorCode);
      return _ChargeResult.failure(
        errorMessage: errorMessage,
        errorCode: errorCode,
      );
    } on FirebaseFunctionsException catch (e) {
      _logError('chargePetAddon CF failed: ${e.code}', e.message);
      // `not-found` / `unavailable` is what we'll see while the
      // Cloud Function is unimplemented. Give a user-friendly copy.
      if (e.code == 'not-found' || e.code == 'unavailable') {
        return _ChargeResult.failure(
          errorMessage:
              'Adding pets is temporarily unavailable while we upgrade our payment system. Please check back soon, or contact support.',
          errorCode: 'PROCESSOR_UNAVAILABLE',
        );
      }
      if (e.code == 'unauthenticated') {
        return _ChargeResult.failure(
          errorMessage:
              'Your session has expired. Please sign in again to add a pet.',
          errorCode: 'UNAUTHENTICATED',
        );
      }
      return _ChargeResult.failure(
        errorMessage:
            e.message ?? 'We couldn\'t complete the charge. Please try again.',
        errorCode: e.code.toUpperCase(),
      );
    } catch (e) {
      _logError('chargePetAddon unexpected error', e);
      return _ChargeResult.failure(
        errorMessage:
            'Something went wrong while processing your payment. Please try again.',
        errorCode: 'UNKNOWN',
      );
    }
  }

  String _defaultErrorMessageFor(String? code) {
    switch (code) {
      case 'NO_PAYMENT_METHOD':
        return 'We couldn\'t find a saved payment method on your account. Please update your payment details and try again.';
      case 'CARD_DECLINED':
        return 'Your card was declined. Try a different payment method or contact your bank.';
      case 'PROCESSOR_UNAVAILABLE':
        return 'Our payment system is temporarily unavailable. Please try again in a few minutes.';
      default:
        return 'We couldn\'t complete the charge. Please try again or contact support.';
    }
  }

  // =======================================================================
  // BILLING: ADD-PET FLOW
  // Orchestrates age validation, pre-existing disclosure, confirmation
  // dialog, charge call, and pet save. Atomic: if the charge fails,
  // the pet is NOT saved.
  //
  // Returns true when the add succeeded (pet live + charge posted),
  // false otherwise. Caller (the editor sheet) uses the return to
  // decide whether to close itself.
  // =======================================================================

  Future<bool> _addPetWithBilling(_Pet pet, Uint8List? photoBytes) async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      _showSnackBar('Sign in to add a pet.', isError: true);
      return false;
    }
    final uid = user.uid;

    // 1. Age gate — must be set, must be in range.
    if (pet.dateOfBirth == null) {
      _showSnackBar(
        'Please enter your pet\'s birthdate so we can set their monthly rate.',
        isError: true,
      );
      return false;
    }
    final months = pet.ageMonths;
    if (months < _petMinAgeMonths) {
      _showSnackBar(
        'Pets must be at least 8 weeks (2 months) old to be added.',
        isError: true,
      );
      return false;
    }
    if (months > _petMaxAgeYears * 12) {
      _showSnackBar(
        'Pets must be 20 years old or younger to be added.',
        isError: true,
      );
      return false;
    }

    // 2. Refresh billing context in case the user doc changed since
    //    widget open (e.g., they just updated their payment method).
    await _loadBillingContext(uid);
    final payarc = _payarcCustomerId;
    if (payarc == null || payarc.isEmpty) {
      _showSnackBar(
        'We couldn\'t find a saved payment method on your account. Update your payment method in your profile and try again.',
        isError: true,
      );
      return false;
    }

    // 3. Compute premium + proration.
    final monthlyPremium = calculatePetMonthlyPremium(months);
    final proration = ProrationCalc.compute(
      anniversaryDay: _renewAnniversaryDay,
    );
    final prorationAmount = proration.prorate(monthlyPremium);

    // 4. Confirmation dialog — shows exact amounts and pre-existing
    //    conditions disclosure if applicable.
    final confirmed = await _showAddPetConfirmDialog(
      pet: pet,
      monthlyPremium: monthlyPremium,
      proration: proration,
      prorationAmount: prorationAmount,
    );
    if (confirmed != true) {
      _analytics('pet_add_cancelled', {'petId': pet.petId});
      return false;
    }

    _analytics('pet_add_confirmed', {
      'petId': pet.petId,
      'monthlyPremium': monthlyPremium.toStringAsFixed(2),
      'prorationAmount': prorationAmount.toStringAsFixed(2),
    });
    _showBlockingProgress('Adding ${pet.name}…');

    // 5. Upload photo first (if any). Photo failure is non-fatal —
    //    we continue with a null photoUrl and warn the user.
    String? finalPhotoUrl = pet.photoUrl;
    bool photoUploadFailed = false;
    if (photoBytes != null && photoBytes.isNotEmpty) {
      try {
        final storageRef = FirebaseStorage.instance
            .ref()
            .child('pet_photos')
            .child(uid)
            .child(pet.petId)
            .child('${const Uuid().v4()}.jpg');
        final uploadTask = await storageRef.putData(
          photoBytes,
          SettableMetadata(contentType: 'image/jpeg'),
        );
        finalPhotoUrl = await uploadTask.ref.getDownloadURL();
      } catch (e) {
        _logError('photo upload failed', e);
        photoUploadFailed = true;
      }
    }
    final petToCharge = pet.copyWith(photoUrl: finalPhotoUrl);

    // 6. Charge. If this fails, stop — do NOT save the pet.
    final chargeResult = await _callChargeAddon(
      userId: uid,
      pet: petToCharge,
      monthlyPremium: monthlyPremium,
      proration: proration,
      payarcCustomerId: payarc,
    );
    if (!chargeResult.success) {
      if (mounted) Navigator.of(context).pop(); // dismiss progress
      _analytics('pet_add_charge_failed', {
        'petId': pet.petId,
        'errorCode': chargeResult.errorCode,
      });
      _showSnackBar(
        chargeResult.errorMessage ??
            'We couldn\'t complete the charge. Please try again.',
        isError: true,
      );
      return false;
    }

    // 7. Save the pet subcollection doc.
    try {
      await FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('pets')
          .doc(petToCharge.petId)
          .set(
            petToCharge.toFirestore(isNew: true),
            SetOptions(merge: true),
          );
    } catch (e) {
      _logError('pet save after successful charge FAILED', e);
      // We charged but the save blew up — this is the nasty edge
      // case. Surface it clearly so support can manually reconcile.
      if (mounted) Navigator.of(context).pop();
      _analytics('pet_add_save_failed_post_charge', {
        'petId': pet.petId,
        'transactionId': chargeResult.transactionId,
      });
      _showSnackBar(
        'Your payment went through but we couldn\'t save ${pet.name} to your account. Please contact support with reference ${chargeResult.transactionId ?? pet.petId}.',
        isError: true,
      );
      return false;
    }

    // 8. Update user-doc totals + mirror to the legacy array.
    //    These are best-effort; the pet is already live.
    unawaited(_syncUserPetTotals(uid));
    unawaited(_writeLegacyArray(uid, desired: [petToCharge]));

    // 9. Log the charge for the member's records.
    unawaited(_logChargeTransaction(
      uid: uid,
      pet: petToCharge,
      monthlyPremium: monthlyPremium,
      chargeResult: chargeResult,
      proration: proration,
    ));

    _analytics('pet_add_succeeded', {
      'petId': pet.petId,
      'transactionId': chargeResult.transactionId,
    });

    if (mounted) Navigator.of(context).pop(); // dismiss progress
    if (photoUploadFailed) {
      _showSnackBar(
        '${pet.name} added! Your photo didn\'t upload — you can try again by editing the pet.',
        isInfo: true,
      );
    } else {
      _showSnackBar('${pet.name} added to your plan.', isSuccess: true);
    }
    return true;
  }

  /// Write a transaction record to a billing history subcollection so
  /// the member can see it on their billing page. Best-effort; the
  /// pet save and charge already succeeded.
  Future<void> _logChargeTransaction({
    required String uid,
    required _Pet pet,
    required double monthlyPremium,
    required _ChargeResult chargeResult,
    required ProrationCalc proration,
  }) async {
    try {
      await FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('billing_history')
          .add({
        'type': 'pet_addon_proration',
        'petId': pet.petId,
        'petName': pet.name,
        'monthlyPremium': monthlyPremium,
        'chargedAmount': chargeResult.chargedAmount,
        'transactionId': chargeResult.transactionId,
        'prorationDays': proration.daysRemaining,
        'cycleDays': proration.cycleDays,
        'nextCycleStart': Timestamp.fromDate(proration.nextCycleStart),
        'createdAt': FieldValue.serverTimestamp(),
      });
    } catch (e) {
      _logError('billing history write failed', e);
    }
  }

  // (state class continues in subsequent parts)
  // =======================================================================
  // EXISTING PET OPERATIONS
  // Save (edit), archive, delete. These DO NOT charge — edits are
  // free; archives take effect next billing cycle; deletes are
  // immediate with no refund.
  // =======================================================================

  /// Save edits to an existing pet. If the pet's premium changed
  /// (because DOB/age changed and pushed it into a new pricing
  /// bracket), we update the user-doc totals but don't re-charge —
  /// the new premium applies at the next billing cycle.
  Future<void> _saveExistingPet(_Pet pet, Uint8List? photoBytes) async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      _showSnackBar('Sign in to save changes.', isError: true);
      return;
    }
    _analytics('pet_updated', {'petId': pet.petId});
    _showBlockingProgress('Saving…');

    try {
      String? finalPhotoUrl = pet.photoUrl;

      if (photoBytes != null && photoBytes.isNotEmpty) {
        try {
          final storageRef = FirebaseStorage.instance
              .ref()
              .child('pet_photos')
              .child(user.uid)
              .child(pet.petId)
              .child('${const Uuid().v4()}.jpg');
          final uploadTask = await storageRef.putData(
            photoBytes,
            SettableMetadata(contentType: 'image/jpeg'),
          );
          finalPhotoUrl = await uploadTask.ref.getDownloadURL();
        } catch (e) {
          _logError('photo upload failed', e);
          if (mounted) Navigator.of(context).pop();
          _showSnackBar(
            'Couldn\'t upload photo. Saving the rest of your changes.',
            isInfo: true,
          );
          _showBlockingProgress('Saving…');
        }
      }

      final toWrite = pet.copyWith(photoUrl: finalPhotoUrl);

      await FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .collection('pets')
          .doc(pet.petId)
          .set(
            toWrite.toFirestore(isNew: false),
            SetOptions(merge: true),
          );

      // Dual-write to legacy array (preserves quote-engine fields).
      unawaited(_writeLegacyArray(user.uid, desired: [toWrite]));

      // Premium may have shifted if DOB changed — resync user totals.
      unawaited(_syncUserPetTotals(user.uid));

      if (!mounted) return;
      Navigator.of(context).pop();
      if (Navigator.of(context).canPop()) {
        Navigator.of(context).pop();
      }
      _showSnackBar('${pet.name} updated.', isSuccess: true);
    } catch (e) {
      _logError('save pet failed', e);
      if (!mounted) return;
      Navigator.of(context).pop();
      _showSnackBar('Could not save. Please try again.', isError: true);
    }
  }

  Future<void> _archivePet(_Pet pet) async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return;

    final confirmed = await _showConfirmDialog(
      title: 'Archive ${pet.name}?',
      body:
          'Archived pets are hidden but not permanently deleted. ${pet.name}\'s monthly contribution of \$${pet.monthlyPremium.toStringAsFixed(2)} will be removed from your next billing cycle. Contact support if you need to restore.',
      confirmLabel: 'Archive',
      destructive: true,
    );
    if (confirmed != true || !mounted) return;

    _analytics('pet_archived', {'petId': pet.petId});
    _showBlockingProgress('Archiving…');

    try {
      await FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .collection('pets')
          .doc(pet.petId)
          .update({
        'archived': true,
        'archivedAt': FieldValue.serverTimestamp(),
        'updatedAt': FieldValue.serverTimestamp(),
      });

      // Legacy array: drop the entry entirely. Onboarding / update
      // don't know about archived state.
      unawaited(_writeLegacyArray(
        user.uid,
        desired: const [],
        removeIds: {pet.petId},
      ));
      unawaited(_syncUserPetTotals(user.uid));

      if (!mounted) return;
      Navigator.of(context).pop();
      if (Navigator.of(context).canPop()) {
        Navigator.of(context).pop();
      }
      _showSnackBar('${pet.name} archived.', isSuccess: true);
    } catch (e) {
      _logError('archive pet failed', e);
      if (!mounted) return;
      Navigator.of(context).pop();
      _showSnackBar('Could not archive. Please try again.', isError: true);
    }
  }

  Future<void> _deletePet(_Pet pet) async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return;

    final confirmed = await _showConfirmDialog(
      title: 'Permanently delete ${pet.name}?',
      body:
          'This will permanently remove ${pet.name} from your account along with their photo. This cannot be undone. Their monthly contribution of \$${pet.monthlyPremium.toStringAsFixed(2)} will be removed from your next billing cycle.\n\nTo keep the record for later, use Archive instead.',
      confirmLabel: 'Delete forever',
      destructive: true,
    );
    if (confirmed != true || !mounted) return;

    _analytics('pet_deleted', {'petId': pet.petId});
    _showBlockingProgress('Deleting…');

    try {
      if (pet.photoUrl != null && pet.photoUrl!.isNotEmpty) {
        try {
          final ref = FirebaseStorage.instance.refFromURL(pet.photoUrl!);
          await ref.delete();
        } catch (e) {
          _log('photo cleanup skipped: $e');
        }
      }

      await FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .collection('pets')
          .doc(pet.petId)
          .delete();

      unawaited(_writeLegacyArray(
        user.uid,
        desired: const [],
        removeIds: {pet.petId},
      ));
      unawaited(_syncUserPetTotals(user.uid));

      if (!mounted) return;
      Navigator.of(context).pop();
      if (Navigator.of(context).canPop()) {
        Navigator.of(context).pop();
      }
      _showSnackBar('${pet.name} deleted.', isSuccess: true);
    } catch (e) {
      _logError('delete pet failed', e);
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

  // (state class continues in subsequent parts)
  // =======================================================================
  // DIALOGS
  // =======================================================================

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

  /// Confirmation dialog shown before charging the user when they
  /// add a pet. Shows:
  ///   - Pet name and premium
  ///   - Proration amount today + remaining days in cycle
  ///   - Next monthly billing date
  ///   - Pre-existing conditions disclosure if any are flagged
  ///   - Plain Confirm / Cancel buttons
  Future<bool?> _showAddPetConfirmDialog({
    required _Pet pet,
    required double monthlyPremium,
    required ProrationCalc proration,
    required double prorationAmount,
  }) async {
    final dateFormat = DateFormat('MMM d, y');
    final hasPreEx = pet.preExistingConditions.isNotEmpty;

    return showDialog<bool>(
      context: context,
      barrierColor: Colors.black.withOpacity(0.6),
      builder: (ctx) => Dialog(
        backgroundColor: Colors.transparent,
        elevation: 0,
        insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(20),
          child: BackdropFilter(
            filter: ui_dart.ImageFilter.blur(sigmaX: 20, sigmaY: 20),
            child: Container(
              padding: const EdgeInsets.all(22),
              decoration: BoxDecoration(
                color: _joviNavy.withOpacity(0.97),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: _petAccent.withOpacity(0.3),
                  width: 1,
                ),
              ),
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          width: 40,
                          height: 40,
                          decoration: BoxDecoration(
                            color: _petAccent.withOpacity(0.16),
                            borderRadius: BorderRadius.circular(11),
                            border: Border.all(
                              color: _petAccent.withOpacity(0.35),
                              width: 0.8,
                            ),
                          ),
                          child: Icon(_petTypeIcon(pet.type),
                              color: _petAccent, size: 20),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                'Add ${pet.name} to your plan?',
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 17,
                                  fontWeight: FontWeight.w800,
                                  letterSpacing: -0.3,
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                pet.displaySubtitle,
                                style: TextStyle(
                                  color: Colors.white.withOpacity(0.55),
                                  fontSize: 12,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 18),
                    // Pricing breakdown
                    Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: _petAccent.withOpacity(0.08),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: _petAccent.withOpacity(0.25),
                          width: 1,
                        ),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _pricingRow(
                            'Monthly contribution',
                            '\$${monthlyPremium.toStringAsFixed(2)}',
                          ),
                          const SizedBox(height: 8),
                          _pricingRow(
                            'Charged today (prorated)',
                            '\$${prorationAmount.toStringAsFixed(2)}',
                            emphasis: true,
                          ),
                          const SizedBox(height: 6),
                          Text(
                            '${proration.daysRemaining} of ${proration.cycleDays} days remaining in this cycle',
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.5),
                              fontSize: 11.5,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Divider(
                            height: 1,
                            color: Colors.white.withOpacity(0.08),
                          ),
                          const SizedBox(height: 8),
                          _pricingRow(
                            'Next monthly bill',
                            dateFormat.format(proration.nextCycleStart),
                          ),
                        ],
                      ),
                    ),
                    if (hasPreEx) ...[
                      const SizedBox(height: 14),
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: _joviGold.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                            color: _joviGold.withOpacity(0.3),
                            width: 1,
                          ),
                        ),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Icon(Icons.warning_amber_rounded,
                                color: _joviGold, size: 18),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  const Text(
                                    'Pre-existing conditions',
                                    style: TextStyle(
                                      color: _joviGold,
                                      fontSize: 12.5,
                                      fontWeight: FontWeight.w800,
                                      letterSpacing: 0.2,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    'Pre-existing conditions are generally not eligible for sharing. Curable conditions that stay symptom-free for 180 days may become eligible.',
                                    style: TextStyle(
                                      color: Colors.white.withOpacity(0.75),
                                      fontSize: 12,
                                      fontWeight: FontWeight.w500,
                                      height: 1.5,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                    const SizedBox(height: 14),
                    Text(
                      'We\'ll use your saved payment method on file.',
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.5),
                        fontSize: 11.5,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    const SizedBox(height: 18),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        TextButton(
                          onPressed: () => Navigator.pop(ctx, false),
                          child: Text(
                            'Cancel',
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.7),
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                        const SizedBox(width: 6),
                        _PressableMaterial(
                          child: InkWell(
                            onTap: () => Navigator.pop(ctx, true),
                            borderRadius: BorderRadius.circular(12),
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 18, vertical: 11),
                              decoration: BoxDecoration(
                                gradient: const LinearGradient(
                                  colors: [_petAccent, _petAccentDark],
                                ),
                                borderRadius: BorderRadius.circular(12),
                                boxShadow: [
                                  BoxShadow(
                                    color: _petAccent.withOpacity(0.4),
                                    blurRadius: 10,
                                    offset: const Offset(0, 3),
                                  ),
                                ],
                              ),
                              child: Text(
                                'Add & charge \$${prorationAmount.toStringAsFixed(2)}',
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.w800,
                                  fontSize: 13.5,
                                  letterSpacing: -0.2,
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
            ),
          ),
        ),
      ),
    );
  }

  Widget _pricingRow(String label, String value, {bool emphasis = false}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Expanded(
          child: Text(
            label,
            style: TextStyle(
              color: Colors.white.withOpacity(emphasis ? 0.85 : 0.65),
              fontSize: emphasis ? 13 : 12.5,
              fontWeight: emphasis ? FontWeight.w700 : FontWeight.w500,
            ),
          ),
        ),
        const SizedBox(width: 12),
        Text(
          value,
          style: TextStyle(
            color: emphasis ? _petAccent : Colors.white,
            fontSize: emphasis ? 15 : 13,
            fontWeight: emphasis ? FontWeight.w700 : FontWeight.w700,
            letterSpacing: -0.2,
          ),
        ),
      ],
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
        floatingActionButton: _loading || _error != null ? null : _buildFab(),
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
                  'My Pets',
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
    if (_loading) return 'Loading your pets…';
    if (_error != null) return 'Something went wrong';
    if (_pets.isEmpty) return 'Add your first pet';
    if (_pets.length == 1) return '1 pet registered';
    return '${_pets.length} pets registered';
  }

  Widget _buildBody() {
    if (_loading) {
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
    if (_error != null) {
      return _buildNoPetsState();
    }
    if (_pets.isEmpty) {
      return _buildNoPetsState();
    }
    return ListView.builder(
      padding: const EdgeInsets.fromLTRB(14, 4, 14, 100),
      itemCount: _pets.length,
      itemBuilder: (ctx, i) {
        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: _buildPetCard(_pets[i]),
        );
      },
    );
  }

  /// Unified empty / no-pets view. Used whenever the user has zero
  /// pets OR whenever loading pets fails.
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
              'We noticed you don\'t have any pets',
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
              'Add a pet now to track their health, book vet visits, and manage medications.',
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
                onTap: () {
                  HapticFeedback.lightImpact();
                  if (_error != null) {
                    setState(() {
                      _error = null;
                    });
                  }
                  _openAddPetSheet();
                },
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

  Widget _buildFab() {
    return FloatingActionButton.extended(
      onPressed: _openAddPetSheet,
      backgroundColor: _petAccent,
      foregroundColor: Colors.white,
      icon: const Icon(Icons.add_rounded),
      label: const Text(
        'Add Pet',
        style: TextStyle(fontWeight: FontWeight.w600),
      ),
    );
  }

  // =======================================================================
  // PET CARD
  // =======================================================================

  Widget _buildPetCard(_Pet pet) {
    final typeColor = pet.type == PetType.dog ? _joviCoral : _joviMint;
    final semLabel = [
      pet.name,
      pet.displaySubtitle,
      if (pet.sex != PetSex.unknown) _petSexLabel(pet.sex),
      'Double tap to view details',
    ].join(', ');

    return Semantics(
      label: semLabel,
      button: true,
      child: _PressableMaterial(
        child: InkWell(
          onTap: () => _openPetDetail(pet),
          borderRadius: BorderRadius.circular(20),
          child: _glassCard(
            bgOpacity: 0.07,
            borderOpacity: 0.14,
            padding: const EdgeInsets.all(14),
            borderTint: _petAccent,
            child: Row(
              children: [
                _buildPetAvatar(pet, typeColor),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Row(
                        children: [
                          Flexible(
                            child: Text(
                              pet.name,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 17,
                                fontWeight: FontWeight.w700,
                                letterSpacing: -0.4,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          const SizedBox(width: 6),
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: typeColor.withOpacity(0.15),
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(
                                color: typeColor.withOpacity(0.3),
                                width: 0.7,
                              ),
                            ),
                            child: Text(
                              pet.displayType,
                              style: TextStyle(
                                color: typeColor,
                                fontSize: 10,
                                fontWeight: FontWeight.w700,
                                letterSpacing: -0.1,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        pet.displaySubtitle,
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.65),
                          fontSize: 12.5,
                          fontWeight: FontWeight.w500,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      if (pet.weightLbs != null ||
                          pet.sex != PetSex.unknown) ...[
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            if (pet.weightLbs != null) ...[
                              Icon(
                                Icons.scale_rounded,
                                color: Colors.white.withOpacity(0.4),
                                size: 11,
                              ),
                              const SizedBox(width: 3),
                              Text(
                                '${pet.weightLbs!.toStringAsFixed(pet.weightLbs! % 1 == 0 ? 0 : 1)} lbs',
                                style: TextStyle(
                                  color: Colors.white.withOpacity(0.55),
                                  fontSize: 11.5,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              const SizedBox(width: 10),
                            ],
                            if (pet.sex != PetSex.unknown) ...[
                              Icon(
                                pet.sex == PetSex.male
                                    ? Icons.male_rounded
                                    : Icons.female_rounded,
                                color: Colors.white.withOpacity(0.4),
                                size: 12,
                              ),
                              const SizedBox(width: 2),
                              Text(
                                _petSexLabel(pet.sex),
                                style: TextStyle(
                                  color: Colors.white.withOpacity(0.55),
                                  fontSize: 11.5,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ],
                          ],
                        ),
                      ],
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
    );
  }

  Widget _buildPetAvatar(_Pet pet, Color typeColor) {
    final hasPhoto = pet.photoUrl != null && pet.photoUrl!.isNotEmpty;
    return Container(
      width: 60,
      height: 60,
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
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: typeColor.withOpacity(0.4),
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: typeColor.withOpacity(0.2),
            blurRadius: 10,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(15),
        child: hasPhoto
            ? Image.network(
                pet.photoUrl!,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) =>
                    _buildAvatarFallback(pet, typeColor),
              )
            : _buildAvatarFallback(pet, typeColor),
      ),
    );
  }

  Widget _buildAvatarFallback(_Pet pet, Color typeColor) {
    return Center(
      child: Icon(
        _petTypeIcon(pet.type),
        color: typeColor,
        size: 28,
      ),
    );
  }

  // =======================================================================
  // EDITOR SHEET OPENERS
  // =======================================================================

  void _openAddPetSheet() {
    HapticFeedback.lightImpact();
    _analytics('pet_profiles_add_opened');
    _showPetEditor(null);
  }

  void _openPetDetail(_Pet pet) {
    HapticFeedback.lightImpact();
    _analytics('pet_profiles_detail_opened', {'petId': pet.petId});
    _showPetEditor(pet);
  }

  /// Opens the full-screen bottom sheet editor for adding a new pet
  /// (pet == null) or editing an existing one. The sheet manages its
  /// own form state; we receive save / archive / delete callbacks
  /// that do the Firestore + billing work.
  Future<void> _showPetEditor(_Pet? pet) async {
    if (!mounted) return;
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
        builder: (ctx, scrollCtrl) => _PetEditorSheet(
          existing: pet,
          scrollController: scrollCtrl,
          onAdd:
              pet == null ? (p, bytes) => _addPetWithBilling(p, bytes) : null,
          onSave: pet != null ? (p, bytes) => _saveExistingPet(p, bytes) : null,
          onArchive: pet == null ? null : () => _archivePet(pet),
          onDelete: pet == null ? null : () => _deletePet(pet),
          // Only thread billing context for ADD mode — the pricing
          // preview is hidden in EDIT mode anyway.
          currentMonthlyTotal: pet == null ? _currentMonthlyTotal : null,
          renewAnniversaryDay: pet == null ? _renewAnniversaryDay : null,
        ),
      ),
    );
  }
}
// =======================================================================
// PET EDITOR SHEET
// Separate StatefulWidget so form state is isolated from the parent
// list state — closing the sheet discards any in-progress edits.
//
// Two modes:
//   - Add mode (existing == null): onAdd is non-null, onSave is null.
//     The save button triggers the billing-aware add flow.
//   - Edit mode (existing != null): onSave is non-null, onAdd is null.
//     The save button triggers a free edit. onArchive / onDelete
//     are also available.
//
// REMOVED in r2: the external "Insurance" section (carrier + policy
// number) and its controllers. Jovi Health is the coverage — there
// was no reason to collect a third-party pet policy here.
// =======================================================================

class _PetEditorSheet extends StatefulWidget {
  final _Pet? existing;
  final ScrollController scrollController;

  /// Called in ADD mode. Returns true on success (charge + save both
  /// completed); false otherwise. The sheet closes on true.
  final Future<bool> Function(_Pet pet, Uint8List? photoBytes)? onAdd;

  /// Called in EDIT mode. Returns void; the parent closes the sheet.
  final Future<void> Function(_Pet pet, Uint8List? photoBytes)? onSave;

  final Future<void> Function()? onArchive;
  final Future<void> Function()? onDelete;

  /// Billing context snapshot, used by the ADD-mode pricing preview
  /// to show "current monthly total → new monthly total" and the
  /// prorated first-charge amount. Null values are fine — the preview
  /// degrades gracefully (shows just the per-pet rate) when we don't
  /// have the data. Not used in EDIT mode.
  final double? currentMonthlyTotal;
  final int? renewAnniversaryDay;

  const _PetEditorSheet({
    Key? key,
    required this.existing,
    required this.scrollController,
    this.onAdd,
    this.onSave,
    this.onArchive,
    this.onDelete,
    this.currentMonthlyTotal,
    this.renewAnniversaryDay,
  }) : super(key: key);

  @override
  State<_PetEditorSheet> createState() => _PetEditorSheetState();
}

class _PetEditorSheetState extends State<_PetEditorSheet> {
  late final TextEditingController _nameCtrl;
  late final TextEditingController _breedCtrl;
  late final TextEditingController _otherTypeCtrl;
  late final TextEditingController _colorCtrl;
  late final TextEditingController _microchipCtrl;
  late final TextEditingController _weightCtrl;
  late final TextEditingController _vetNameCtrl;
  late final TextEditingController _vetPhoneCtrl;
  late final TextEditingController _vetClinicCtrl;
  late final TextEditingController _dietaryCtrl;
  late final TextEditingController _notesCtrl;
  // Insurance controllers REMOVED in r2.

  late String _petId;
  late PetType _type;
  late PetSex _sex;
  bool? _neutered;
  DateTime? _dateOfBirth;
  String? _photoUrl;
  Uint8List? _pendingPhotoBytes;
  List<String> _allergies = [];
  List<String> _conditions = [];
  List<String> _currentMeds = [];

  final _formKey = GlobalKey<FormState>();
  bool _attemptedSave = false;

  bool get _isEditing => widget.existing != null;

  @override
  void initState() {
    super.initState();
    final e = widget.existing;
    _petId = e?.petId ?? const Uuid().v4();
    _nameCtrl = TextEditingController(text: e?.name ?? '');
    _breedCtrl = TextEditingController(text: e?.breed ?? '');
    _otherTypeCtrl = TextEditingController(text: e?.otherTypeLabel ?? '');
    _colorCtrl = TextEditingController(text: e?.color ?? '');
    _microchipCtrl = TextEditingController(text: e?.microchipId ?? '');
    _weightCtrl = TextEditingController(
      text: e?.weightLbs != null
          ? (e!.weightLbs! % 1 == 0
              ? e.weightLbs!.toInt().toString()
              : e.weightLbs!.toStringAsFixed(1))
          : '',
    );
    _vetNameCtrl = TextEditingController(text: e?.primaryVetName ?? '');
    _vetPhoneCtrl = TextEditingController(text: e?.primaryVetPhone ?? '');
    _vetClinicCtrl = TextEditingController(text: e?.primaryVetClinic ?? '');
    _dietaryCtrl = TextEditingController(text: e?.dietaryRestrictions ?? '');
    _notesCtrl = TextEditingController(text: e?.notes ?? '');

    _type = e?.type ?? PetType.dog;
    _sex = e?.sex ?? PetSex.unknown;
    _neutered = e?.neutered;
    _dateOfBirth = e?.dateOfBirth;
    _photoUrl = e?.photoUrl;
    _allergies = List<String>.from(e?.allergies ?? const []);
    _conditions = List<String>.from(e?.preExistingConditions ?? const []);
    _currentMeds = List<String>.from(e?.currentMedications ?? const []);
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _breedCtrl.dispose();
    _otherTypeCtrl.dispose();
    _colorCtrl.dispose();
    _microchipCtrl.dispose();
    _weightCtrl.dispose();
    _vetNameCtrl.dispose();
    _vetPhoneCtrl.dispose();
    _vetClinicCtrl.dispose();
    _dietaryCtrl.dispose();
    _notesCtrl.dispose();
    super.dispose();
  }

  /// Compute age bounds for the DOB picker. Anything older than
  /// 20 years is disallowed, matching onboarding's enrollment rules.
  DateTime get _dobFirstAllowed {
    final now = DateTime.now();
    return DateTime(now.year - _petMaxAgeYears, now.month, now.day);
  }

  /// Anything younger than 2 months is disallowed. We still pick
  /// "today" as the lastDate so the DatePicker's internal range is
  /// valid; the form-level validator catches the "too young" case.
  DateTime get _dobLastAllowed => DateTime.now();

  /// Live age warning surfaced under the DOB picker. Mirrors the
  /// logic onboarding uses.
  String? _ageWarning() {
    final dob = _dateOfBirth;
    if (dob == null) return null;
    final months = ageInMonthsFromDob(dob);
    if (months < _petMinAgeMonths) {
      return 'Minimum enrollment age is 8 weeks (2 months).';
    }
    if (months > _petMaxAgeYears * 12) {
      return 'Maximum enrollment age is $_petMaxAgeYears years.';
    }
    return null;
  }

  // (editor state class continues in subsequent parts)
  Future<void> _pickPhoto() async {
    HapticFeedback.lightImpact();
    try {
      final picker = ImagePicker();
      final source = await _showPhotoSourcePicker();
      if (source == null) return;
      final file = await picker.pickImage(
        source: source,
        maxWidth: 1200,
        maxHeight: 1200,
        imageQuality: 85,
      );
      if (file == null) return;
      final bytes = await file.readAsBytes();
      setState(() {
        _pendingPhotoBytes = bytes;
        _photoUrl = null;
      });
    } catch (e) {
      _logError('photo pick failed', e);
      if (!mounted) return;
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast('Could not access photos.',
        accent: _joviErrorRed, icon: CupertinoIcons.exclamationmark_circle));
    }
  }

  Future<ImageSource?> _showPhotoSourcePicker() async {
    return showCupertinoModalPopup<ImageSource>(
      context: context,
      builder: (ctx) => CupertinoActionSheet(
        title: const Text('Add a Photo'),
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

  // ignore: unused_element
  Widget _buildSourceOption(
    BuildContext ctx, {
    required IconData icon,
    required String label,
    required ImageSource source,
  }) {
    return _PressableMaterial(
      child: InkWell(
        onTap: () => Navigator.of(ctx).pop(source),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 14),
          child: Row(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: _petAccent.withOpacity(0.16),
                  borderRadius: BorderRadius.circular(11),
                  border: Border.all(
                    color: _petAccent.withOpacity(0.3),
                    width: 0.8,
                  ),
                ),
                child: Icon(icon, color: _petAccent, size: 19),
              ),
              const SizedBox(width: 14),
              Text(
                label,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 15,
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

  Future<void> _pickDateOfBirth() async {
    HapticFeedback.lightImpact();
    final now = DateTime.now();
    final initial = _dateOfBirth ?? DateTime(now.year - 2, now.month, now.day);
    final picked = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: _dobFirstAllowed,
      lastDate: _dobLastAllowed,
      helpText: 'Pet date of birth',
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
    if (picked != null && mounted) {
      setState(() => _dateOfBirth = picked);
    }
  }

  /// Builds the _Pet instance from current form state. Used by both
  /// add and save paths.
  _Pet _buildPetFromForm() {
    final weight = double.tryParse(_weightCtrl.text.trim());
    return _Pet(
      petId: _petId,
      name: _nameCtrl.text.trim(),
      type: _type,
      otherTypeLabel: _type == PetType.other
          ? _otherTypeCtrl.text.trim().isEmpty
              ? null
              : _otherTypeCtrl.text.trim()
          : null,
      breed: _breedCtrl.text.trim().isEmpty ? null : _breedCtrl.text.trim(),
      sex: _sex,
      neutered: _neutered,
      dateOfBirth: _dateOfBirth,
      weightLbs: weight,
      color: _colorCtrl.text.trim().isEmpty ? null : _colorCtrl.text.trim(),
      microchipId: _microchipCtrl.text.trim().isEmpty
          ? null
          : _microchipCtrl.text.trim(),
      photoUrl: _photoUrl,
      primaryVetName:
          _vetNameCtrl.text.trim().isEmpty ? null : _vetNameCtrl.text.trim(),
      primaryVetPhone:
          _vetPhoneCtrl.text.trim().isEmpty ? null : _vetPhoneCtrl.text.trim(),
      primaryVetClinic: _vetClinicCtrl.text.trim().isEmpty
          ? null
          : _vetClinicCtrl.text.trim(),
      allergies: _allergies,
      preExistingConditions: _conditions,
      currentMedications: _currentMeds,
      dietaryRestrictions:
          _dietaryCtrl.text.trim().isEmpty ? null : _dietaryCtrl.text.trim(),
      notes: _notesCtrl.text.trim().isEmpty ? null : _notesCtrl.text.trim(),
      archived: widget.existing?.archived ?? false,
      createdAt: widget.existing?.createdAt,
      updatedAt: widget.existing?.updatedAt,
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

    // Age enforcement for ADD mode only. Edits of existing pets are
    // allowed to have any DOB (they're already enrolled and we don't
    // want to lock them out of editing their own record).
    if (!_isEditing) {
      final ageIssue = _ageWarning();
      if (ageIssue != null) {
        HapticFeedback.heavyImpact();
        ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(ageIssue,
            accent: _joviErrorRed,
            icon: CupertinoIcons.exclamationmark_circle));
        return;
      }
      if (_dateOfBirth == null) {
        HapticFeedback.heavyImpact();
        ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast('Please set your pet\'s birthdate — we need it to calculate their monthly rate.',
        accent: _joviErrorRed, icon: CupertinoIcons.exclamationmark_circle));
        return;
      }
    }

    HapticFeedback.mediumImpact();
    final pet = _buildPetFromForm();

    if (_isEditing) {
      // Edit mode — free update, no billing.
      await widget.onSave?.call(pet, _pendingPhotoBytes);
    } else {
      // Add mode — billing-aware. The callback returns true on
      // success; we close the sheet only then.
      final success =
          await widget.onAdd?.call(pet, _pendingPhotoBytes) ?? false;
      if (success && mounted) {
        Navigator.of(context).pop();
      }
    }
  }

  String _breedHintForType() {
    switch (_type) {
      case PetType.dog:
        return 'e.g., Golden Retriever';
      case PetType.cat:
        return 'e.g., Maine Coon';
      case PetType.other:
        return 'Breed or variety';
    }
  }

  // =======================================================================
  // BREED SELECTOR
  // For Dog/Cat: a searchable dropdown backed by _dogBreeds / _catBreeds.
  // Tapping the field opens a dialog with a search box and filtered
  // scrolling list; selection writes the chosen value back to
  // _breedCtrl so downstream form serialization stays unchanged.
  //
  // For Other: falls back to a free-text field (breed lists don't
  // apply to exotic species). This keeps the breed field usable for
  // rabbits, birds, reptiles, etc.
  //
  // If the user has an existing saved breed that's NOT in the current
  // list (e.g., list was revised after they enrolled), we preserve it
  // as the selected value — the dialog just won't highlight anything
  // until they pick something new.
  // =======================================================================

  Widget _buildBreedSelector() {
    // Other → free-text. Matches the r1 behavior for exotic species.
    if (_type == PetType.other) {
      return _buildTextField(
        controller: _breedCtrl,
        label: 'Breed',
        hint: _breedHintForType(),
      );
    }

    final selected = _breedCtrl.text.trim();
    final hasSelection = selected.isNotEmpty;

    return _PressableMaterial(
      child: InkWell(
        onTap: _showBreedPicker,
        borderRadius: BorderRadius.circular(12),
        child: InputDecorator(
          decoration: InputDecoration(
            labelText: 'Breed',
            labelStyle: TextStyle(
              color: Colors.white.withOpacity(0.7),
              fontSize: 13,
              fontWeight: FontWeight.w600,
            ),
            floatingLabelStyle: const TextStyle(
              color: _petAccent,
              fontSize: 13,
              fontWeight: FontWeight.w700,
            ),
            hintText: _breedHintForType(),
            hintStyle: TextStyle(
              color: Colors.white.withOpacity(0.35),
              fontSize: 14,
              fontWeight: FontWeight.w500,
            ),
            filled: true,
            fillColor: Colors.white.withOpacity(0.06),
            suffixIcon: Padding(
              padding: const EdgeInsets.only(right: 10),
              child: Icon(
                hasSelection ? Icons.edit_rounded : Icons.search_rounded,
                color: _petAccent,
                size: 18,
              ),
            ),
            suffixIconConstraints:
                const BoxConstraints(minWidth: 0, minHeight: 0),
            contentPadding:
                const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide(
                color: Colors.white.withOpacity(0.14),
                width: 1,
              ),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide(
                color: Colors.white.withOpacity(0.14),
                width: 1,
              ),
            ),
          ),
          isEmpty: !hasSelection,
          child: Text(
            hasSelection ? selected : '',
            style: const TextStyle(
              color: Colors.white,
              fontSize: 14,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ),
    );
  }

  /// Searchable breed picker dialog. The list is filtered live as the
  /// user types — see also Onboarding Update's matching implementation.
  Future<void> _showBreedPicker() async {
    final breeds = _breedsFor(_type);
    if (breeds.isEmpty) return; // defensive — shouldn't hit for dog/cat
    final existing = _breedCtrl.text.trim();

    final selected = await showDialog<String>(
      context: context,
      barrierColor: Colors.black.withOpacity(0.6),
      builder: (ctx) {
        String query = '';
        return StatefulBuilder(builder: (ctx, setDialogState) {
          final filtered = query.isEmpty
              ? breeds
              : breeds
                  .where((b) => b.toLowerCase().contains(query.toLowerCase()))
                  .toList();
          return Dialog(
            backgroundColor: Colors.transparent,
            elevation: 0,
            insetPadding:
                const EdgeInsets.symmetric(horizontal: 24, vertical: 48),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(18),
              child: BackdropFilter(
                filter: ui_dart.ImageFilter.blur(sigmaX: 18, sigmaY: 18),
                child: Container(
                  decoration: BoxDecoration(
                    color: _joviNavy.withOpacity(0.96),
                    borderRadius: BorderRadius.circular(18),
                    border: Border.all(
                      color: Colors.white.withOpacity(0.1),
                      width: 1,
                    ),
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // Header
                      Padding(
                        padding: const EdgeInsets.fromLTRB(18, 16, 14, 8),
                        child: Row(
                          children: [
                            Container(
                              width: 34,
                              height: 34,
                              decoration: BoxDecoration(
                                color: _petAccent.withOpacity(0.18),
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(
                                  color: _petAccent.withOpacity(0.35),
                                  width: 0.8,
                                ),
                              ),
                              child: const Icon(
                                Icons.pets_rounded,
                                color: _petAccent,
                                size: 17,
                              ),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                _type == PetType.cat
                                    ? 'Select cat breed'
                                    : 'Select dog breed',
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 16,
                                  fontWeight: FontWeight.w700,
                                  letterSpacing: -0.3,
                                ),
                              ),
                            ),
                            IconButton(
                              onPressed: () => Navigator.of(ctx).pop(null),
                              icon: Icon(
                                Icons.close_rounded,
                                color: Colors.white.withOpacity(0.55),
                                size: 20,
                              ),
                              splashRadius: 18,
                            ),
                          ],
                        ),
                      ),
                      // Search
                      Padding(
                        padding: const EdgeInsets.fromLTRB(18, 4, 18, 10),
                        child: TextField(
                          autofocus: true,
                          autocorrect: false,
                          textInputAction: TextInputAction.search,
                          cursorColor: _petAccent,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 14,
                            fontWeight: FontWeight.w500,
                          ),
                          onChanged: (v) => setDialogState(() => query = v),
                          decoration: InputDecoration(
                            hintText: 'Search breeds',
                            hintStyle: TextStyle(
                              color: Colors.white.withOpacity(0.35),
                            ),
                            prefixIcon: Icon(
                              Icons.search_rounded,
                              color: Colors.white.withOpacity(0.45),
                              size: 18,
                            ),
                            filled: true,
                            fillColor: Colors.white.withOpacity(0.06),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(10),
                              borderSide: BorderSide(
                                color: Colors.white.withOpacity(0.12),
                                width: 1,
                              ),
                            ),
                            enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(10),
                              borderSide: BorderSide(
                                color: Colors.white.withOpacity(0.12),
                                width: 1,
                              ),
                            ),
                            focusedBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(10),
                              borderSide: const BorderSide(
                                color: _petAccent,
                                width: 1.5,
                              ),
                            ),
                            contentPadding: const EdgeInsets.symmetric(
                                horizontal: 12, vertical: 10),
                          ),
                        ),
                      ),
                      // Results
                      Flexible(
                        child: filtered.isEmpty
                            ? Padding(
                                padding:
                                    const EdgeInsets.fromLTRB(18, 16, 18, 22),
                                child: Column(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Text(
                                      'No breeds match "$query"',
                                      style: TextStyle(
                                        color: Colors.white.withOpacity(0.6),
                                        fontSize: 13,
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                    const SizedBox(height: 6),
                                    Text(
                                      'You can still type a custom breed below.',
                                      textAlign: TextAlign.center,
                                      style: TextStyle(
                                        color: Colors.white.withOpacity(0.45),
                                        fontSize: 11.5,
                                        fontWeight: FontWeight.w500,
                                      ),
                                    ),
                                    const SizedBox(height: 10),
                                    _PressableMaterial(
                                      child: InkWell(
                                        onTap: () {
                                          if (query.trim().isEmpty) {
                                            return;
                                          }
                                          Navigator.of(ctx).pop(query.trim());
                                        },
                                        borderRadius: BorderRadius.circular(10),
                                        child: Container(
                                          padding: const EdgeInsets.symmetric(
                                              horizontal: 14, vertical: 9),
                                          decoration: BoxDecoration(
                                            color: _petAccent.withOpacity(0.18),
                                            borderRadius:
                                                BorderRadius.circular(10),
                                            border: Border.all(
                                              color:
                                                  _petAccent.withOpacity(0.35),
                                              width: 0.8,
                                            ),
                                          ),
                                          child: Text(
                                            'Use "${query.trim()}"',
                                            style: const TextStyle(
                                              color: _petAccent,
                                              fontSize: 12.5,
                                              fontWeight: FontWeight.w800,
                                            ),
                                          ),
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              )
                            : ListView.builder(
                                shrinkWrap: true,
                                padding: const EdgeInsets.fromLTRB(8, 0, 8, 8),
                                itemCount: filtered.length,
                                itemBuilder: (_, i) {
                                  final breed = filtered[i];
                                  final isSelected = breed == existing;
                                  return _PressableMaterial(
                                    child: InkWell(
                                      onTap: () => Navigator.of(ctx).pop(breed),
                                      borderRadius: BorderRadius.circular(8),
                                      child: Container(
                                        padding: const EdgeInsets.symmetric(
                                            horizontal: 12, vertical: 10),
                                        decoration: BoxDecoration(
                                          color: isSelected
                                              ? _petAccent.withOpacity(0.14)
                                              : null,
                                          borderRadius:
                                              BorderRadius.circular(8),
                                        ),
                                        child: Row(
                                          children: [
                                            Expanded(
                                              child: Text(
                                                breed,
                                                style: TextStyle(
                                                  color: isSelected
                                                      ? _petAccent
                                                      : Colors.white,
                                                  fontSize: 13.5,
                                                  fontWeight: isSelected
                                                      ? FontWeight.w800
                                                      : FontWeight.w500,
                                                ),
                                              ),
                                            ),
                                            if (isSelected)
                                              const Icon(
                                                Icons.check_circle_rounded,
                                                color: _petAccent,
                                                size: 16,
                                              ),
                                          ],
                                        ),
                                      ),
                                    ),
                                  );
                                },
                              ),
                      ),
                      const SizedBox(height: 4),
                    ],
                  ),
                ),
              ),
            ),
          );
        });
      },
    );

    if (selected != null && selected.isNotEmpty && mounted) {
      setState(() {
        _breedCtrl.text = selected;
      });
    }
  }

  // (editor state class continues in subsequent parts)
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
                        _buildPhotoPicker(),
                        const SizedBox(height: 20),
                        if (!_isEditing) _buildPricingPreview(),
                        _buildSectionHeader('Basics', Icons.pets_rounded),
                        _buildTextField(
                          controller: _nameCtrl,
                          label: 'Name',
                          required: true,
                          hint: "What's your pet's name?",
                          autofocus: !_isEditing,
                        ),
                        const SizedBox(height: 12),
                        _buildTypeSelector(),
                        if (_type == PetType.other) ...[
                          const SizedBox(height: 12),
                          _buildTextField(
                            controller: _otherTypeCtrl,
                            label: 'Species',
                            hint: 'e.g., Rabbit, Bird, Reptile',
                          ),
                        ],
                        const SizedBox(height: 12),
                        _buildBreedSelector(),
                        const SizedBox(height: 16),
                        _buildSexSelector(),
                        const SizedBox(height: 12),
                        _buildNeuteredSelector(),
                        const SizedBox(height: 12),
                        _buildDobPicker(),
                        const SizedBox(height: 12),
                        Row(
                          children: [
                            Expanded(
                              child: _buildTextField(
                                controller: _weightCtrl,
                                label: 'Weight (lbs)',
                                hint: '0',
                                keyboardType:
                                    const TextInputType.numberWithOptions(
                                        decimal: true),
                                validator: (v) {
                                  if (v == null || v.trim().isEmpty) {
                                    return null;
                                  }
                                  final parsed = double.tryParse(v.trim());
                                  if (parsed == null) {
                                    return 'Enter a number';
                                  }
                                  if (parsed <= 0 || parsed > 400) {
                                    return 'Unrealistic weight';
                                  }
                                  return null;
                                },
                              ),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: _buildTextField(
                                controller: _colorCtrl,
                                label: 'Color / markings',
                                hint: 'e.g., Black & white',
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        _buildTextField(
                          controller: _microchipCtrl,
                          label: 'Microchip ID',
                          hint: 'Optional — if chipped',
                        ),
                        const SizedBox(height: 24),
                        _buildSectionHeader(
                            'Clinical', Icons.medical_services_outlined),
                        _buildListEditor(
                          label: 'Allergies',
                          helper:
                              'Food, medication, or environmental allergens.',
                          items: _allergies,
                          onChanged: (list) =>
                              setState(() => _allergies = list),
                          placeholder: 'e.g., Chicken',
                        ),
                        const SizedBox(height: 16),
                        _buildListEditor(
                          label: 'Pre-existing conditions',
                          helper:
                              'Ongoing health conditions your vet knows about. Pre-existing conditions generally aren\'t shared.',
                          items: _conditions,
                          onChanged: (list) =>
                              setState(() => _conditions = list),
                          placeholder: 'e.g., Arthritis',
                        ),
                        const SizedBox(height: 16),
                        _buildListEditor(
                          label: 'Current medications',
                          helper:
                              'Quick list — full schedules live in Pet Medications.',
                          items: _currentMeds,
                          onChanged: (list) =>
                              setState(() => _currentMeds = list),
                          placeholder: 'e.g., Apoquel 16mg daily',
                        ),
                        const SizedBox(height: 16),
                        _buildTextField(
                          controller: _dietaryCtrl,
                          label: 'Dietary restrictions',
                          hint: 'Special diet, foods to avoid, etc.',
                          maxLines: 2,
                        ),
                        const SizedBox(height: 24),
                        _buildSectionHeader(
                            'Primary vet', Icons.local_hospital_outlined),
                        _buildTextField(
                          controller: _vetNameCtrl,
                          label: 'Vet name',
                          hint: 'Dr. Smith',
                        ),
                        const SizedBox(height: 12),
                        Row(
                          children: [
                            Expanded(
                              child: _buildTextField(
                                controller: _vetClinicCtrl,
                                label: 'Clinic',
                                hint: 'Animal Hospital',
                              ),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: _buildTextField(
                                controller: _vetPhoneCtrl,
                                label: 'Phone',
                                hint: '(555) 555-5555',
                                keyboardType: TextInputType.phone,
                              ),
                            ),
                          ],
                        ),
                        // INSURANCE SECTION REMOVED in r2. Jovi Health
                        // IS the coverage — we don't ask for external
                        // pet policy numbers.
                        const SizedBox(height: 24),
                        _buildSectionHeader('Notes', Icons.notes_rounded),
                        _buildTextField(
                          controller: _notesCtrl,
                          label: 'Anything else to remember',
                          hint:
                              'Temperament, fears, handler notes, favorite treats…',
                          maxLines: 4,
                        ),
                        if (_isEditing) ...[
                          const SizedBox(height: 32),
                          _buildDangerZone(),
                        ],
                        const SizedBox(height: 24),
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

  // =======================================================================
  // PRICING PREVIEW
  // Shown only in ADD mode above the Basics section. Updates live as
  // the user picks a DOB. Zero pressure — it's informational, the
  // actual confirmation dialog will re-state the exact amounts.
  // =======================================================================

  Widget _buildPricingPreview() {
    final hasDob = _dateOfBirth != null;
    final months = ageInMonthsFromDob(_dateOfBirth);
    final eligible =
        hasDob && months >= _petMinAgeMonths && months <= _petMaxAgeYears * 12;
    final premium = eligible ? calculatePetMonthlyPremium(months) : null;

    final current = widget.currentMonthlyTotal;
    final hasCurrent = current != null && current > 0;

    // "After" only exists once we have an eligible premium. Without a
    // birthdate we can't say what the new monthly will be, so we hide
    // the before/after row and show the base-rate hint instead.
    final newTotal = (premium != null && hasCurrent) ? current + premium : null;

    // Proration snapshot for the "today you'll be charged" line.
    // ProrationCalc handles the null-anniversary fallback (30-day
    // cycle starting today → fraction 1.0 → full premium now).
    final proration = premium != null
        ? ProrationCalc.compute(
            anniversaryDay: widget.renewAnniversaryDay,
          )
        : null;
    final prorated = (premium != null && proration != null)
        ? proration.prorate(premium)
        : null;

    return Container(
      margin: const EdgeInsets.only(bottom: 20),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.2),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              colors: [_joviNavy, _joviNavyDark],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // --- Header row: icon + label ---
              Padding(
                padding: const EdgeInsets.fromLTRB(14, 12, 14, 4),
                child: Row(
                  children: [
                    Container(
                      width: 30,
                      height: 30,
                      decoration: BoxDecoration(
                        color: _petAccent.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(9),
                        border: Border.all(
                          color: _petAccent.withOpacity(0.4),
                          width: 0.8,
                        ),
                      ),
                      child: const Icon(
                        Icons.volunteer_activism_rounded,
                        color: _petAccent,
                        size: 15,
                      ),
                    ),
                    const SizedBox(width: 9),
                    const Text(
                      'Adding this pet to your plan',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 12.5,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.1,
                      ),
                    ),
                  ],
                ),
              ),

              // --- Before/after ---
              if (premium == null) ...[
                // No DOB yet → show the base-rate hint.
                Padding(
                  padding: const EdgeInsets.fromLTRB(14, 8, 14, 14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Set birthdate to see rate',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                          letterSpacing: -0.5,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        'Base \$${_petBasePremium.toStringAsFixed(0)}/mo, +\$${_petYearlyAddon.toStringAsFixed(0)} per year after the first.',
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.6),
                          fontSize: 11.5,
                          fontWeight: FontWeight.w500,
                          height: 1.4,
                        ),
                      ),
                    ],
                  ),
                ),
              ] else ...[
                // Eligible premium → show the math.
                Padding(
                  padding: const EdgeInsets.fromLTRB(14, 10, 14, 10),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (hasCurrent) ...[
                        // Before/after monthly totals row.
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            // Current monthly (struck-through)
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Text(
                                  'Current monthly',
                                  style: TextStyle(
                                    color: Colors.white.withOpacity(0.5),
                                    fontSize: 10.5,
                                    fontWeight: FontWeight.w700,
                                    letterSpacing: 0.3,
                                  ),
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  '\$${current.toStringAsFixed(2)}',
                                  style: TextStyle(
                                    color: Colors.white.withOpacity(0.55),
                                    fontSize: 15,
                                    fontWeight: FontWeight.w700,
                                    decoration: TextDecoration.lineThrough,
                                    decorationColor:
                                        Colors.white.withOpacity(0.3),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(width: 8),
                            Padding(
                              padding: const EdgeInsets.only(bottom: 3),
                              child: Icon(
                                Icons.arrow_forward_rounded,
                                color: _petAccent.withOpacity(0.7),
                                size: 16,
                              ),
                            ),
                            const SizedBox(width: 8),
                            // New monthly (highlighted)
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  const Text(
                                    'New monthly',
                                    style: TextStyle(
                                      color: _petAccent,
                                      fontSize: 10.5,
                                      fontWeight: FontWeight.w800,
                                      letterSpacing: 0.3,
                                    ),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    '\$${newTotal!.toStringAsFixed(2)}',
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontSize: 22,
                                      fontWeight: FontWeight.w700,
                                      letterSpacing: -0.4,
                                      height: 1.0,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '+\$${premium.toStringAsFixed(2)}/mo for this pet',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.55),
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            letterSpacing: 0.1,
                          ),
                        ),
                      ] else ...[
                        // No current-total available → just show the
                        // per-pet rate clearly.
                        Text(
                          '\$${premium.toStringAsFixed(2)}/month',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 22,
                            fontWeight: FontWeight.w700,
                            letterSpacing: -0.4,
                          ),
                        ),
                        const SizedBox(height: 3),
                        Text(
                          'Added to your existing plan at your next bill.',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.6),
                            fontSize: 11.5,
                            fontWeight: FontWeight.w500,
                            height: 1.4,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),

                // --- Proration line: today's charge ---
                if (prorated != null) ...[
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.fromLTRB(14, 10, 14, 12),
                    decoration: BoxDecoration(
                      color: Colors.black.withOpacity(0.2),
                      border: Border(
                        top: BorderSide(
                          color: Colors.white.withOpacity(0.06),
                          width: 1,
                        ),
                      ),
                    ),
                    child: Row(
                      children: [
                        Icon(
                          Icons.today_rounded,
                          color: _joviCoral.withOpacity(0.85),
                          size: 14,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text.rich(
                            TextSpan(
                              style: TextStyle(
                                color: Colors.white.withOpacity(0.75),
                                fontSize: 11.5,
                                fontWeight: FontWeight.w500,
                                height: 1.4,
                              ),
                              children: [
                                const TextSpan(
                                  text: 'Today you\'ll be charged ',
                                ),
                                TextSpan(
                                  text: '\$${prorated.toStringAsFixed(2)}',
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                                TextSpan(
                                  text: proration!.cycleDays > 0
                                      ? ' (prorated for ${proration.daysRemaining} of ${proration.cycleDays} days).'
                                      : '.',
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ],
          ),
        ),
      ),
    );
  }

  // (editor state class continues in subsequent parts)
  // =======================================================================
  // SHEET HEADER
  // =======================================================================

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
                  _isEditing ? 'Edit Pet' : 'Add a Pet',
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
                  _isEditing
                      ? 'Update details for ${widget.existing!.name}'
                      : 'Tell us about your pet',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.55),
                    fontSize: 12.5,
                    fontWeight: FontWeight.w500,
                    letterSpacing: 0.2,
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
              child: Tooltip(
                message: 'Close',
                child: Semantics(
                  label: 'Close editor',
                  button: true,
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
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPhotoPicker() {
    final hasBytes = _pendingPhotoBytes != null;
    final hasUrl = _photoUrl != null && _photoUrl!.isNotEmpty;
    final hasPhoto = hasBytes || hasUrl;

    return Center(
      child: Column(
        children: [
          Stack(
            children: [
              Container(
                width: 110,
                height: 110,
                decoration: BoxDecoration(
                  gradient: hasPhoto
                      ? null
                      : LinearGradient(
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                          colors: [
                            _petAccent.withOpacity(0.22),
                            _petAccent.withOpacity(0.08),
                          ],
                        ),
                  borderRadius: BorderRadius.circular(26),
                  border: Border.all(
                    color: _petAccent.withOpacity(0.4),
                    width: 1.2,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: _petAccent.withOpacity(0.2),
                      blurRadius: 14,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(25),
                  child: hasBytes
                      ? Image.memory(
                          _pendingPhotoBytes!,
                          fit: BoxFit.cover,
                        )
                      : hasUrl
                          ? Image.network(
                              _photoUrl!,
                              fit: BoxFit.cover,
                              errorBuilder: (_, __, ___) => _photoPlaceholder(),
                            )
                          : _photoPlaceholder(),
                ),
              ),
              Positioned(
                right: -2,
                bottom: -2,
                child: _PressableMaterial(
                  child: InkWell(
                    onTap: _pickPhoto,
                    borderRadius: BorderRadius.circular(16),
                    child: Tooltip(
                      message: 'Change photo',
                      child: Semantics(
                        label: 'Change pet photo',
                        button: true,
                        child: Container(
                          width: 36,
                          height: 36,
                          decoration: BoxDecoration(
                            color: _petAccent,
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: _joviNavy,
                              width: 2.5,
                            ),
                            boxShadow: [
                              BoxShadow(
                                color: _petAccent.withOpacity(0.5),
                                blurRadius: 8,
                                offset: const Offset(0, 2),
                              ),
                            ],
                          ),
                          child: const Icon(
                            Icons.photo_camera_rounded,
                            color: Colors.white,
                            size: 17,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            hasPhoto ? 'Tap to change photo' : 'Tap to add a photo',
            style: TextStyle(
              color: Colors.white.withOpacity(0.5),
              fontSize: 11.5,
              fontWeight: FontWeight.w600,
              letterSpacing: 0.2,
            ),
          ),
        ],
      ),
    );
  }

  Widget _photoPlaceholder() {
    return Center(
      child: Icon(
        _petTypeIcon(_type),
        color: _petAccent,
        size: 46,
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
            style: const TextStyle(
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

  Widget _buildTextField({
    required TextEditingController controller,
    required String label,
    String? hint,
    bool required = false,
    int maxLines = 1,
    TextInputType? keyboardType,
    String? Function(String?)? validator,
    bool autofocus = false,
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
                const Text(
                  '*',
                  style: TextStyle(
                    color: _joviCoral,
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ],
          ),
        ),
        TextFormField(
          controller: controller,
          maxLines: maxLines,
          keyboardType: keyboardType,
          autofocus: autofocus,
          textCapitalization: keyboardType == TextInputType.phone ||
                  keyboardType == const TextInputType.numberWithOptions(
                      decimal: true)
              ? TextCapitalization.none
              : TextCapitalization.words,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 14,
            fontWeight: FontWeight.w500,
          ),
          cursorColor: _petAccent,
          validator: validator ??
              (required
                  ? (v) {
                      if (v == null || v.trim().isEmpty) {
                        return '$label is required';
                      }
                      return null;
                    }
                  : null),
          decoration: InputDecoration(
            hintText: hint,
            hintStyle: TextStyle(
              color: Colors.white.withOpacity(0.35),
              fontSize: 14,
              fontWeight: FontWeight.w500,
            ),
            filled: true,
            fillColor: Colors.white.withOpacity(0.05),
            contentPadding:
                const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide(
                color: Colors.white.withOpacity(0.12),
                width: 1,
              ),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide(
                color: Colors.white.withOpacity(0.12),
                width: 1,
              ),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: const BorderSide(color: _petAccent, width: 1.5),
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

  Widget _buildTypeSelector() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 6),
          child: Text(
            'Type',
            style: TextStyle(
              color: Colors.white.withOpacity(0.7),
              fontSize: 12,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.2,
            ),
          ),
        ),
        Row(
          children: [
            for (final t in PetType.values) ...[
              Expanded(
                child: _buildPillOption(
                  label: _petTypeLabel(t),
                  icon: _petTypeIcon(t),
                  selected: _type == t,
                  onTap: () {
                    HapticFeedback.selectionClick();
                    setState(() => _type = t);
                  },
                ),
              ),
              if (t != PetType.values.last) const SizedBox(width: 6),
            ],
          ],
        ),
      ],
    );
  }

  Widget _buildSexSelector() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 6),
          child: Text(
            'Sex',
            style: TextStyle(
              color: Colors.white.withOpacity(0.7),
              fontSize: 12,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.2,
            ),
          ),
        ),
        Row(
          children: [
            Expanded(
              child: _buildPillOption(
                label: 'Male',
                icon: Icons.male_rounded,
                selected: _sex == PetSex.male,
                onTap: () {
                  HapticFeedback.selectionClick();
                  setState(() => _sex = PetSex.male);
                },
              ),
            ),
            const SizedBox(width: 6),
            Expanded(
              child: _buildPillOption(
                label: 'Female',
                icon: Icons.female_rounded,
                selected: _sex == PetSex.female,
                onTap: () {
                  HapticFeedback.selectionClick();
                  setState(() => _sex = PetSex.female);
                },
              ),
            ),
            const SizedBox(width: 6),
            Expanded(
              child: _buildPillOption(
                label: 'Unknown',
                icon: Icons.question_mark_rounded,
                selected: _sex == PetSex.unknown,
                onTap: () {
                  HapticFeedback.selectionClick();
                  setState(() => _sex = PetSex.unknown);
                },
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildNeuteredSelector() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 6),
          child: Text(
            'Spayed / Neutered',
            style: TextStyle(
              color: Colors.white.withOpacity(0.7),
              fontSize: 12,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.2,
            ),
          ),
        ),
        Row(
          children: [
            Expanded(
              child: _buildPillOption(
                label: 'Yes',
                icon: Icons.check_rounded,
                selected: _neutered == true,
                onTap: () {
                  HapticFeedback.selectionClick();
                  setState(() => _neutered = true);
                },
              ),
            ),
            const SizedBox(width: 6),
            Expanded(
              child: _buildPillOption(
                label: 'No',
                icon: Icons.close_rounded,
                selected: _neutered == false,
                onTap: () {
                  HapticFeedback.selectionClick();
                  setState(() => _neutered = false);
                },
              ),
            ),
            const SizedBox(width: 6),
            Expanded(
              child: _buildPillOption(
                label: 'Unsure',
                icon: Icons.help_outline_rounded,
                selected: _neutered == null,
                onTap: () {
                  HapticFeedback.selectionClick();
                  setState(() => _neutered = null);
                },
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildPillOption({
    required String label,
    required IconData icon,
    required bool selected,
    required VoidCallback onTap,
  }) {
    return _PressableMaterial(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(11),
        child: Semantics(
          label: selected ? '$label, selected' : label,
          button: true,
          child: AnimatedContainer(
            duration: _Motion.select,
            curve: _Motion.settle,
            padding: const EdgeInsets.symmetric(vertical: 12),
            decoration: BoxDecoration(
              gradient: selected
                  ? const LinearGradient(
                      colors: [_petAccent, _petAccentDark],
                    )
                  : null,
              color: selected ? null : Colors.white.withOpacity(0.05),
              borderRadius: BorderRadius.circular(11),
              border: Border.all(
                color: selected
                    ? _petAccent.withOpacity(0.6)
                    : Colors.white.withOpacity(0.12),
                width: 1,
              ),
              boxShadow: selected
                  ? [
                      BoxShadow(
                        color: _petAccent.withOpacity(0.3),
                        blurRadius: 8,
                        offset: const Offset(0, 2),
                      ),
                    ]
                  : null,
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  icon,
                  color:
                      selected ? Colors.white : Colors.white.withOpacity(0.65),
                  size: 14,
                ),
                const SizedBox(width: 5),
                Flexible(
                  child: Text(
                    label,
                    style: TextStyle(
                      color: selected
                          ? Colors.white
                          : Colors.white.withOpacity(0.78),
                      fontSize: 12.5,
                      fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
                      letterSpacing: 0.2,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // (editor state class continues in subsequent parts)
  // =======================================================================
  // DOB PICKER
  // Tap target that opens the date picker. Shows the selected date
  // and age, plus a live warning if the age is outside enrollment
  // bounds. The warning is advisory here — the hard gate runs in
  // _onSaveTapped (add mode only).
  // =======================================================================

  Widget _buildDobPicker() {
    final warning = _ageWarning();
    final hasDob = _dateOfBirth != null;
    final ageLabel = hasDob ? ageDisplayFromDob(_dateOfBirth) : null;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 6),
          child: Row(
            children: [
              Text(
                'Date of birth',
                style: TextStyle(
                  color: Colors.white.withOpacity(0.7),
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.2,
                ),
              ),
              if (!_isEditing) ...[
                const SizedBox(width: 4),
                const Text(
                  '*',
                  style: TextStyle(
                    color: _joviCoral,
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ],
          ),
        ),
        _PressableMaterial(
          child: InkWell(
            onTap: _pickDateOfBirth,
            borderRadius: BorderRadius.circular(12),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.05),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: warning != null
                      ? _joviErrorRed.withOpacity(0.5)
                      : Colors.white.withOpacity(0.12),
                  width: 1,
                ),
              ),
              child: Row(
                children: [
                  Icon(
                    Icons.cake_outlined,
                    color: hasDob ? _petAccent : Colors.white.withOpacity(0.45),
                    size: 18,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          hasDob
                              ? DateFormat('MMM d, y').format(_dateOfBirth!)
                              : 'Tap to select',
                          style: TextStyle(
                            color: hasDob
                                ? Colors.white
                                : Colors.white.withOpacity(0.35),
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        if (ageLabel != null) ...[
                          const SizedBox(height: 2),
                          Text(
                            ageLabel,
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.55),
                              fontSize: 11.5,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                  Icon(
                    Icons.chevron_right_rounded,
                    color: Colors.white.withOpacity(0.4),
                    size: 20,
                  ),
                ],
              ),
            ),
          ),
        ),
        if (warning != null) ...[
          const SizedBox(height: 6),
          Padding(
            padding: const EdgeInsets.only(left: 4),
            child: Row(
              children: [
                const Icon(
                  Icons.warning_amber_rounded,
                  color: _joviErrorRed,
                  size: 13,
                ),
                const SizedBox(width: 4),
                Flexible(
                  child: Text(
                    warning,
                    style: const TextStyle(
                      color: _joviErrorRed,
                      fontSize: 11.5,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ],
    );
  }

  // =======================================================================
  // LIST EDITOR
  // Small chip-based editor used for allergies, conditions, and
  // current medications. Add via the trailing text field; remove via
  // the (×) on each chip.
  // =======================================================================

  Widget _buildListEditor({
    required String label,
    required String helper,
    required List<String> items,
    required ValueChanged<List<String>> onChanged,
    required String placeholder,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 6),
          child: Text(
            label,
            style: TextStyle(
              color: Colors.white.withOpacity(0.7),
              fontSize: 12,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.2,
            ),
          ),
        ),
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.05),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: Colors.white.withOpacity(0.12),
              width: 1,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (items.isNotEmpty) ...[
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [
                    for (int i = 0; i < items.length; i++)
                      _buildListChip(
                        label: items[i],
                        onRemove: () {
                          HapticFeedback.selectionClick();
                          final next = List<String>.from(items)..removeAt(i);
                          onChanged(next);
                        },
                      ),
                  ],
                ),
                const SizedBox(height: 8),
              ],
              _AddChipInput(
                placeholder: placeholder,
                onSubmit: (value) {
                  final trimmed = value.trim();
                  if (trimmed.isEmpty) return;
                  // Skip duplicates (case-insensitive).
                  if (items
                      .any((e) => e.toLowerCase() == trimmed.toLowerCase())) {
                    return;
                  }
                  HapticFeedback.selectionClick();
                  onChanged([...items, trimmed]);
                },
              ),
            ],
          ),
        ),
        const SizedBox(height: 4),
        Padding(
          padding: const EdgeInsets.only(left: 4),
          child: Text(
            helper,
            style: TextStyle(
              color: Colors.white.withOpacity(0.45),
              fontSize: 11,
              fontWeight: FontWeight.w500,
              height: 1.4,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildListChip({
    required String label,
    required VoidCallback onRemove,
  }) {
    return Container(
      padding: const EdgeInsets.fromLTRB(10, 6, 6, 6),
      decoration: BoxDecoration(
        color: _petAccent.withOpacity(0.15),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: _petAccent.withOpacity(0.32),
          width: 0.8,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Flexible(
            child: Text(
              label,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          const SizedBox(width: 4),
          _PressableMaterial(
            child: InkWell(
              onTap: onRemove,
              borderRadius: BorderRadius.circular(10),
              child: Padding(
                padding: const EdgeInsets.all(3),
                child: Icon(
                  Icons.close_rounded,
                  color: Colors.white.withOpacity(0.7),
                  size: 13,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  // =======================================================================
  // DANGER ZONE
  // Archive + delete. Edit mode only.
  // =======================================================================

  Widget _buildDangerZone() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 10, top: 4),
          child: Row(
            children: [
              Container(
                width: 26,
                height: 26,
                decoration: BoxDecoration(
                  color: _joviErrorRed.withOpacity(0.16),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: _joviErrorRed.withOpacity(0.3),
                    width: 0.8,
                  ),
                ),
                child: const Icon(
                  Icons.warning_amber_rounded,
                  color: _joviErrorRed,
                  size: 14,
                ),
              ),
              const SizedBox(width: 9),
              Text(
                'Remove From Plan',
                style: TextStyle(
                  color: _joviErrorRed.withOpacity(0.9),
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  letterSpacing: -0.1,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 4),
        Container(
          decoration: BoxDecoration(
            color: _joviErrorRed.withOpacity(0.06),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: _joviErrorRed.withOpacity(0.2),
              width: 1,
            ),
          ),
          child: Column(
            children: [
              _buildDangerRow(
                label: 'Archive',
                helper:
                    'Hide this pet and stop contributions at next cycle. Can be restored by support.',
                icon: Icons.archive_outlined,
                onTap: () async {
                  if (widget.onArchive != null) {
                    await widget.onArchive!();
                  }
                },
                destructive: false,
              ),
              Divider(
                height: 1,
                color: _joviErrorRed.withOpacity(0.15),
              ),
              _buildDangerRow(
                label: 'Delete permanently',
                helper:
                    'Permanently remove this pet and their photo. This cannot be undone.',
                icon: Icons.delete_forever_outlined,
                onTap: () async {
                  if (widget.onDelete != null) {
                    await widget.onDelete!();
                  }
                },
                destructive: true,
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildDangerRow({
    required String label,
    required String helper,
    required IconData icon,
    required Future<void> Function() onTap,
    required bool destructive,
  }) {
    final color = destructive ? _joviErrorRed : _joviGold;
    return _PressableMaterial(
      child: InkWell(
        onTap: () async {
          HapticFeedback.mediumImpact();
          await onTap();
        },
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: color.withOpacity(0.14),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: color.withOpacity(0.28),
                    width: 0.8,
                  ),
                ),
                child: Icon(icon, color: color, size: 17),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      label,
                      style: TextStyle(
                        color: color,
                        fontSize: 14,
                        fontWeight: FontWeight.w800,
                        letterSpacing: -0.2,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      helper,
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.55),
                        fontSize: 11.5,
                        fontWeight: FontWeight.w500,
                        height: 1.35,
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

  // =======================================================================
  // SAVE BAR
  // Pinned to the bottom of the sheet. Label changes based on mode:
  //   - Add: "Add & charge"
  //   - Edit: "Save changes"
  // =======================================================================

  Widget _buildSaveBar() {
    return Container(
      padding: const EdgeInsets.fromLTRB(18, 12, 18, 18),
      decoration: BoxDecoration(
        color: _joviNavyDark.withOpacity(0.85),
        border: Border(
          top: BorderSide(
            color: Colors.white.withOpacity(0.08),
            width: 1,
          ),
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: _PressableMaterial(
              child: InkWell(
                onTap: _onSaveTapped,
                borderRadius: BorderRadius.circular(14),
                child: Container(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [_petAccent, _petAccentDark],
                    ),
                    borderRadius: BorderRadius.circular(14),
                    boxShadow: [
                      BoxShadow(
                        color: _petAccent.withOpacity(0.4),
                        blurRadius: 12,
                        offset: const Offset(0, 4),
                      ),
                    ],
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        _isEditing ? Icons.check_rounded : Icons.add_rounded,
                        color: Colors.white,
                        size: 17,
                      ),
                      const SizedBox(width: 7),
                      Text(
                        _isEditing ? 'Save Changes' : 'Add & Charge',
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
        ],
      ),
    );
  }
}
// =======================================================================
// ADD-CHIP INPUT
// A compact text field that emits its value on submit (enter) or on
// tap of the trailing "+" button. Used inside _buildListEditor for
// allergies, conditions, and current medications.
// =======================================================================

class _AddChipInput extends StatefulWidget {
  final String placeholder;
  final ValueChanged<String> onSubmit;

  const _AddChipInput({
    Key? key,
    required this.placeholder,
    required this.onSubmit,
  }) : super(key: key);

  @override
  State<_AddChipInput> createState() => _AddChipInputState();
}

class _AddChipInputState extends State<_AddChipInput> {
  final _ctrl = TextEditingController();
  final _focusNode = FocusNode();

  @override
  void dispose() {
    _ctrl.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _submit() {
    final value = _ctrl.text.trim();
    if (value.isEmpty) return;
    widget.onSubmit(value);
    _ctrl.clear();
    _focusNode.requestFocus();
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: TextField(
            controller: _ctrl,
            focusNode: _focusNode,
            onSubmitted: (_) => _submit(),
            textInputAction: TextInputAction.done,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 13.5,
              fontWeight: FontWeight.w500,
            ),
            cursorColor: _petAccent,
            decoration: InputDecoration(
              hintText: widget.placeholder,
              hintStyle: TextStyle(
                color: Colors.white.withOpacity(0.35),
                fontSize: 13.5,
                fontWeight: FontWeight.w500,
              ),
              isDense: true,
              border: InputBorder.none,
              enabledBorder: InputBorder.none,
              focusedBorder: InputBorder.none,
              contentPadding:
                  const EdgeInsets.symmetric(horizontal: 4, vertical: 8),
            ),
          ),
        ),
        _PressableMaterial(
          child: InkWell(
            onTap: _submit,
            borderRadius: BorderRadius.circular(10),
            child: Container(
              padding: const EdgeInsets.all(7),
              decoration: BoxDecoration(
                color: _petAccent.withOpacity(0.16),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(
                  color: _petAccent.withOpacity(0.35),
                  width: 0.8,
                ),
              ),
              child: const Icon(
                Icons.add_rounded,
                color: _petAccent,
                size: 16,
              ),
            ),
          ),
        ),
      ],
    );
  }
}
