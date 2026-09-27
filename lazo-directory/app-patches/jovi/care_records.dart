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
import 'package:url_launcher/url_launcher.dart';
import 'package:intl/intl.dart';
import 'package:add_2_calendar/add_2_calendar.dart' as a2c;

// -----------------------------------------------------------------------
// JOVI HEALTH - CARE RECORDS (Appointments + Visit History + Timeline)
// Version: 2026.09.22-r2 (Apple HIG pass: press feedback, painted glass,
//          Cupertino cancel confirm, Jovi Pass naming, title-case labels)
// r1:      2026.04.18
// Build: JC-CARE-0922-002
// -----------------------------------------------------------------------
//
// What this widget shows:
//   Tab 1 — Upcoming appointments with cancel / reschedule / directions
//   Tab 2 — Past visits with full clinical detail (vitals, diagnoses,
//           prescriptions, labs, procedures, notes, follow-up, billing)
//   Tab 3 — Unified care timeline (visits + prescriptions + symptom
//           checks + claims — all merged chronologically)
//
// Data sources (Firestore):
//   requests (top-level, userId filter)      — appointments (scheduling
//     layer written by jovi_requests_flow.dart)
//   cancelled_appointments (top-level)       — audit trail on cancel
//   users/{uid}/visit_records/{recordId}     — detailed clinical records
//     (linked to a request via appointmentId field)
//   users/{uid}/symptom_checks/{...}         — from Symptom Checker widget
//   prescriptions (top-level, userId filter) — Rx records written by
//     clinic-side tools; read by jovi_prescription_refills.dart
//   prescriptionRefills (top-level, userId)  — in-app refill events
//     written by jovi_prescription_refills.dart
//   refills (top-level, userId filter)       — request-flow refill events
//     written by jovi_requests_flow.dart when visit type == "refill"
//   claims (top-level, userId filter)        — submitted via File a Claim
//
// BLOCK BEFORE PRODUCTION items for Care Records:
//   1. Firestore security rules — members can only read their own data,
//      and can only write status=cancelled on their own appointments.
//   2. Provider-facing tool or admin console for clinic staff to write
//      visit_records after each visit. Until this is built, records can
//      be seeded manually for testing.
//   3. Cancellation policy rules — how far in advance can a member cancel
//      without a fee? Enforce in Cloud Function, not client.
//   4. Reschedule flow needs the Request Care scheduling backend. For
//      now, reschedule just redirects the member to Request Care.
//   5. Legal/compliance review of patient-visible clinical data —
//      especially free-text provider notes which may contain info the
//      clinic doesn't intend patients to see.
//
// -----------------------------------------------------------------------

// =======================================================================
// JOVI BRAND COLORS
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

// =======================================================================
// LOGGING / TELEMETRY
// Matches the helper pattern used in jovi_symptom_checker.dart so
// eventual structured-logging migration is a single swap.
// =======================================================================

void _log(String message) {
  debugPrint('[CareRecords] $message');
}

void _logError(String message, [Object? error]) {
  if (error != null) {
    debugPrint('[CareRecords][ERROR] $message: $error');
  } else {
    debugPrint('[CareRecords][ERROR] $message');
  }
}

/// Analytics hook. Called for notable user events. Wire to Firebase
/// Analytics / audit-log Cloud Function when ready.
void _analytics(String eventName, [Map<String, String?>? properties]) {
  if (properties == null || properties.isEmpty) {
    _log('analytics: $eventName');
  } else {
    _log('analytics: $eventName ${properties.toString()}');
  }
}

// =======================================================================
// SHARED NUMERIC PARSERS
// Top-level so multiple fromFirestore factories can share them.
// =======================================================================

double? _asDouble(dynamic v) {
  if (v == null) return null;
  if (v is num) return v.toDouble();
  if (v is String) return double.tryParse(v);
  return null;
}

int? _asInt(dynamic v) {
  if (v == null) return null;
  if (v is num) return v.toInt();
  if (v is String) return int.tryParse(v);
  return null;
}

// =======================================================================
// ENUMS
// =======================================================================

/// Which tab is currently active.
enum _Tab { upcoming, past, timeline }

/// Appointment lifecycle status. Kept loose — different clinics use
/// different vocabularies; we normalize on read.
enum AppointmentStatus {
  /// Booked and upcoming
  scheduled,

  /// Being seen right now
  inProgress,

  /// Completed normally — should have a linked visit_record
  completed,

  /// Cancelled by either side before the visit
  cancelled,

  /// Patient didn't show up
  noShow,

  /// Unknown / legacy status we couldn't parse
  unknown,
}

/// High-level classification of appointment. Drives iconography and
/// color-coding, NOT clinical decisions.
enum AppointmentType {
  primaryCare,
  urgentCare,
  specialist,
  followUp,
  telehealth,
  labOnly,
  imaging,
  preventive,
  vaccination,
  mentalHealth,
  other,
}

/// Prescription status for a single medication entry.
enum PrescriptionStatus {
  /// Prescription written by provider but member hasn't started yet
  ordered,

  /// Picked up from pharmacy, member is taking it
  active,

  /// Medication course completed as directed
  completed,

  /// Discontinued by provider or member before completion
  discontinued,

  /// Prescription expired without being filled
  expired,

  /// Unknown / legacy
  unknown,
}

/// Status of a lab or imaging order placed at a visit.
enum LabOrderStatus {
  /// Provider placed the order but specimen not yet collected
  ordered,

  /// Sample collected, waiting on results
  inProgress,

  /// Results are available
  resulted,

  /// Cancelled before collection
  cancelled,

  /// Unknown
  unknown,
}

/// Kind of event in the unified care timeline. Drives which renderer
/// is used for the timeline card.
enum CareEventKind {
  appointment, // scheduled or completed visit
  visitRecord, // post-visit clinical record
  prescription, // medication ordered or refilled
  labOrder, // lab ordered
  labResult, // lab resulted
  symptomCheck, // session from Symptom Checker widget
  claim, // submitted via File a Claim
  vaccination, // immunization administered
  procedure, // in-office procedure performed
  other,
}

// =======================================================================
// ENUM HELPERS
// Top-level functions (not extensions) for FlutterFlow parser friendliness.
// =======================================================================

// ---- AppointmentStatus helpers -------------------------------------------

String _apptStatusLabel(AppointmentStatus s) {
  switch (s) {
    case AppointmentStatus.scheduled:
      return 'Scheduled';
    case AppointmentStatus.inProgress:
      return 'In progress';
    case AppointmentStatus.completed:
      return 'Completed';
    case AppointmentStatus.cancelled:
      return 'Cancelled';
    case AppointmentStatus.noShow:
      return 'Missed';
    case AppointmentStatus.unknown:
      return 'Unknown';
  }
}

Color _apptStatusColor(AppointmentStatus s) {
  switch (s) {
    case AppointmentStatus.scheduled:
      return _joviCoral;
    case AppointmentStatus.inProgress:
      return _joviGold;
    case AppointmentStatus.completed:
      return _joviMintDark;
    case AppointmentStatus.cancelled:
      return _joviErrorRed;
    case AppointmentStatus.noShow:
      return _joviErrorRed;
    case AppointmentStatus.unknown:
      return Colors.grey;
  }
}

IconData _apptStatusIcon(AppointmentStatus s) {
  switch (s) {
    case AppointmentStatus.scheduled:
      return Icons.event_available_rounded;
    case AppointmentStatus.inProgress:
      return Icons.pending_rounded;
    case AppointmentStatus.completed:
      return Icons.check_circle_rounded;
    case AppointmentStatus.cancelled:
      return Icons.cancel_rounded;
    case AppointmentStatus.noShow:
      return Icons.event_busy_rounded;
    case AppointmentStatus.unknown:
      return Icons.help_outline_rounded;
  }
}

AppointmentStatus _apptStatusParse(String? raw) {
  if (raw == null) return AppointmentStatus.unknown;
  final v = raw.trim().toLowerCase().replaceAll('-', '_').replaceAll(' ', '_');
  switch (v) {
    case 'scheduled':
    case 'booked':
    case 'upcoming':
    case 'confirmed':
      return AppointmentStatus.scheduled;
    case 'in_progress':
    case 'inprogress':
    case 'arrived':
    case 'checkedin':
    case 'checked_in':
      return AppointmentStatus.inProgress;
    case 'completed':
    case 'complete':
    case 'done':
    case 'finished':
    case 'closed':
      return AppointmentStatus.completed;
    case 'cancelled':
    case 'canceled':
    case 'cancel':
      return AppointmentStatus.cancelled;
    case 'no_show':
    case 'noshow':
    case 'missed':
      return AppointmentStatus.noShow;
    default:
      return AppointmentStatus.unknown;
  }
}

String _apptStatusSerialize(AppointmentStatus s) {
  switch (s) {
    case AppointmentStatus.scheduled:
      return 'scheduled';
    case AppointmentStatus.inProgress:
      return 'in_progress';
    case AppointmentStatus.completed:
      return 'completed';
    case AppointmentStatus.cancelled:
      return 'cancelled';
    case AppointmentStatus.noShow:
      return 'no_show';
    case AppointmentStatus.unknown:
      return 'unknown';
  }
}

// ---- AppointmentType helpers ---------------------------------------------

String _apptTypeLabel(AppointmentType t) {
  switch (t) {
    case AppointmentType.primaryCare:
      return 'Primary care';
    case AppointmentType.urgentCare:
      return 'Urgent care';
    case AppointmentType.specialist:
      return 'Specialist';
    case AppointmentType.followUp:
      return 'Follow-up';
    case AppointmentType.telehealth:
      return 'Telehealth';
    case AppointmentType.labOnly:
      return 'Lab visit';
    case AppointmentType.imaging:
      return 'Imaging';
    case AppointmentType.preventive:
      return 'Preventive';
    case AppointmentType.vaccination:
      return 'Vaccination';
    case AppointmentType.mentalHealth:
      return 'Mental health';
    case AppointmentType.other:
      return 'Visit';
  }
}

Color _apptTypeColor(AppointmentType t) {
  switch (t) {
    case AppointmentType.primaryCare:
      return _joviMint;
    case AppointmentType.urgentCare:
      return _joviCoral;
    case AppointmentType.specialist:
      return const Color(0xFFA78BFA); // violet
    case AppointmentType.followUp:
      return _joviMintDark;
    case AppointmentType.telehealth:
      return const Color(0xFF38BDF8); // sky
    case AppointmentType.labOnly:
      return const Color(0xFF22D3EE); // cyan
    case AppointmentType.imaging:
      return const Color(0xFF818CF8); // indigo
    case AppointmentType.preventive:
      return _joviGold;
    case AppointmentType.vaccination:
      return const Color(0xFF2DD4BF); // teal
    case AppointmentType.mentalHealth:
      return const Color(0xFFF472B6); // pink
    case AppointmentType.other:
      return Colors.white70;
  }
}

IconData _apptTypeIcon(AppointmentType t) {
  switch (t) {
    case AppointmentType.primaryCare:
      return Icons.medical_services_outlined;
    case AppointmentType.urgentCare:
      return Icons.emergency_rounded;
    case AppointmentType.specialist:
      return Icons.psychology_alt_outlined;
    case AppointmentType.followUp:
      return Icons.event_repeat_rounded;
    case AppointmentType.telehealth:
      return Icons.videocam_rounded;
    case AppointmentType.labOnly:
      return Icons.science_outlined;
    case AppointmentType.imaging:
      return Icons.image_search_rounded;
    case AppointmentType.preventive:
      return Icons.health_and_safety_outlined;
    case AppointmentType.vaccination:
      return Icons.vaccines_outlined;
    case AppointmentType.mentalHealth:
      return Icons.psychology_outlined;
    case AppointmentType.other:
      return Icons.event_note_rounded;
  }
}

AppointmentType _apptTypeParse(String? raw) {
  if (raw == null) return AppointmentType.other;
  final v = raw.trim().toLowerCase().replaceAll('-', '_').replaceAll(' ', '_');
  switch (v) {
    case 'primary_care':
    case 'primarycare':
    case 'primary':
    case 'pcp':
      return AppointmentType.primaryCare;
    case 'urgent_care':
    case 'urgentcare':
    case 'urgent':
      return AppointmentType.urgentCare;
    case 'specialist':
    case 'referral':
    case 'consult':
      return AppointmentType.specialist;
    case 'follow_up':
    case 'followup':
    case 'recheck':
      return AppointmentType.followUp;
    case 'telehealth':
    case 'telemedicine':
    case 'virtual':
    case 'video':
      return AppointmentType.telehealth;
    case 'lab_only':
    case 'labonly':
    case 'lab':
    case 'labs':
    case 'bloodwork':
      return AppointmentType.labOnly;
    case 'imaging':
    case 'xray':
    case 'x_ray':
    case 'mri':
    case 'ct':
    case 'ultrasound':
      return AppointmentType.imaging;
    case 'preventive':
    case 'preventative':
    case 'wellness':
    case 'annual':
    case 'physical':
      return AppointmentType.preventive;
    case 'vaccination':
    case 'vaccine':
    case 'immunization':
    case 'shot':
      return AppointmentType.vaccination;
    case 'mental_health':
    case 'mentalhealth':
    case 'therapy':
    case 'counseling':
    case 'psychiatry':
      return AppointmentType.mentalHealth;
    default:
      return AppointmentType.other;
  }
}

String _apptTypeSerialize(AppointmentType t) {
  switch (t) {
    case AppointmentType.primaryCare:
      return 'primary_care';
    case AppointmentType.urgentCare:
      return 'urgent_care';
    case AppointmentType.specialist:
      return 'specialist';
    case AppointmentType.followUp:
      return 'follow_up';
    case AppointmentType.telehealth:
      return 'telehealth';
    case AppointmentType.labOnly:
      return 'lab_only';
    case AppointmentType.imaging:
      return 'imaging';
    case AppointmentType.preventive:
      return 'preventive';
    case AppointmentType.vaccination:
      return 'vaccination';
    case AppointmentType.mentalHealth:
      return 'mental_health';
    case AppointmentType.other:
      return 'other';
  }
}

// ---- PrescriptionStatus helpers ------------------------------------------

String _rxStatusLabel(PrescriptionStatus s) {
  switch (s) {
    case PrescriptionStatus.ordered:
      return 'Ordered';
    case PrescriptionStatus.active:
      return 'Active';
    case PrescriptionStatus.completed:
      return 'Completed';
    case PrescriptionStatus.discontinued:
      return 'Discontinued';
    case PrescriptionStatus.expired:
      return 'Expired';
    case PrescriptionStatus.unknown:
      return 'Status unknown';
  }
}

Color _rxStatusColor(PrescriptionStatus s) {
  switch (s) {
    case PrescriptionStatus.ordered:
      return _joviGold;
    case PrescriptionStatus.active:
      return _joviMintDark;
    case PrescriptionStatus.completed:
      return _joviMintDark;
    case PrescriptionStatus.discontinued:
      return _joviErrorRed;
    case PrescriptionStatus.expired:
      return Colors.grey;
    case PrescriptionStatus.unknown:
      return Colors.grey;
  }
}

PrescriptionStatus _rxStatusParse(String? raw) {
  if (raw == null) return PrescriptionStatus.unknown;
  final v = raw.trim().toLowerCase();
  switch (v) {
    case 'ordered':
    case 'pending':
      return PrescriptionStatus.ordered;
    case 'active':
    case 'current':
    case 'taking':
      return PrescriptionStatus.active;
    case 'completed':
    case 'complete':
    case 'finished':
      return PrescriptionStatus.completed;
    case 'discontinued':
    case 'stopped':
    case 'cancelled':
      return PrescriptionStatus.discontinued;
    case 'expired':
      return PrescriptionStatus.expired;
    default:
      return PrescriptionStatus.unknown;
  }
}

String _rxStatusSerialize(PrescriptionStatus s) {
  switch (s) {
    case PrescriptionStatus.ordered:
      return 'ordered';
    case PrescriptionStatus.active:
      return 'active';
    case PrescriptionStatus.completed:
      return 'completed';
    case PrescriptionStatus.discontinued:
      return 'discontinued';
    case PrescriptionStatus.expired:
      return 'expired';
    case PrescriptionStatus.unknown:
      return 'unknown';
  }
}

// ---- LabOrderStatus helpers ----------------------------------------------

String _labStatusLabel(LabOrderStatus s) {
  switch (s) {
    case LabOrderStatus.ordered:
      return 'Ordered';
    case LabOrderStatus.inProgress:
      return 'Processing';
    case LabOrderStatus.resulted:
      return 'Results in';
    case LabOrderStatus.cancelled:
      return 'Cancelled';
    case LabOrderStatus.unknown:
      return 'Status unknown';
  }
}

Color _labStatusColor(LabOrderStatus s) {
  switch (s) {
    case LabOrderStatus.ordered:
      return _joviGold;
    case LabOrderStatus.inProgress:
      return _joviGold;
    case LabOrderStatus.resulted:
      return _joviMintDark;
    case LabOrderStatus.cancelled:
      return _joviErrorRed;
    case LabOrderStatus.unknown:
      return Colors.grey;
  }
}

LabOrderStatus _labStatusParse(String? raw) {
  if (raw == null) return LabOrderStatus.unknown;
  final v = raw.trim().toLowerCase().replaceAll('-', '_').replaceAll(' ', '_');
  switch (v) {
    case 'ordered':
    case 'pending':
    case 'placed':
      return LabOrderStatus.ordered;
    case 'in_progress':
    case 'inprogress':
    case 'processing':
    case 'running':
      return LabOrderStatus.inProgress;
    case 'resulted':
    case 'complete':
    case 'completed':
    case 'done':
      return LabOrderStatus.resulted;
    case 'cancelled':
    case 'canceled':
      return LabOrderStatus.cancelled;
    default:
      return LabOrderStatus.unknown;
  }
}

// ---- CareEventKind helpers -----------------------------------------------

String _eventKindLabel(CareEventKind k) {
  switch (k) {
    case CareEventKind.appointment:
      return 'Appointment';
    case CareEventKind.visitRecord:
      return 'Visit';
    case CareEventKind.prescription:
      return 'Prescription';
    case CareEventKind.labOrder:
      return 'Lab ordered';
    case CareEventKind.labResult:
      return 'Lab result';
    case CareEventKind.symptomCheck:
      return 'Symptom check';
    case CareEventKind.claim:
      return 'Claim';
    case CareEventKind.vaccination:
      return 'Vaccination';
    case CareEventKind.procedure:
      return 'Procedure';
    case CareEventKind.other:
      return 'Event';
  }
}

Color _eventKindColor(CareEventKind k) {
  switch (k) {
    case CareEventKind.appointment:
      return _joviCoral;
    case CareEventKind.visitRecord:
      return _joviMint;
    case CareEventKind.prescription:
      return const Color(0xFFA78BFA);
    case CareEventKind.labOrder:
      return const Color(0xFF22D3EE);
    case CareEventKind.labResult:
      return const Color(0xFF22D3EE);
    case CareEventKind.symptomCheck:
      return _joviGold;
    case CareEventKind.claim:
      return const Color(0xFF38BDF8);
    case CareEventKind.vaccination:
      return const Color(0xFF2DD4BF);
    case CareEventKind.procedure:
      return const Color(0xFFF472B6);
    case CareEventKind.other:
      return Colors.white70;
  }
}

IconData _eventKindIcon(CareEventKind k) {
  switch (k) {
    case CareEventKind.appointment:
      return Icons.event_available_rounded;
    case CareEventKind.visitRecord:
      return Icons.medical_information_outlined;
    case CareEventKind.prescription:
      return Icons.medication_outlined;
    case CareEventKind.labOrder:
      return Icons.science_outlined;
    case CareEventKind.labResult:
      return Icons.assignment_turned_in_outlined;
    case CareEventKind.symptomCheck:
      return Icons.health_and_safety_outlined;
    case CareEventKind.claim:
      return Icons.receipt_long_outlined;
    case CareEventKind.vaccination:
      return Icons.vaccines_outlined;
    case CareEventKind.procedure:
      return Icons.healing_rounded;
    case CareEventKind.other:
      return Icons.circle_outlined;
  }
}

// =======================================================================
// DATA MODELS
// Plain classes with fromFirestore factories and toJson serializers.
// Every field is nullable where the clinic might not record it — we
// render "—" or hide the section in the UI when a field is missing.
// =======================================================================

/// A single vital sign reading taken during a visit. Clinics capture a
/// variable set; whatever fields are missing, the UI simply doesn't
/// render a row for that vital.
class _Vital {
  final String? bloodPressure; // "120/80"
  final int? heartRate; // bpm
  final double? temperatureF; // degrees Fahrenheit
  final double? weightLbs;
  final double? heightIn;
  final int? oxygenSaturation; // SpO2 percent
  final int? respiratoryRate; // breaths per minute
  final double? bmi;
  final int? painScale; // 0-10 self-reported
  final String? notes; // e.g., "taken seated, left arm"

  const _Vital({
    this.bloodPressure,
    this.heartRate,
    this.temperatureF,
    this.weightLbs,
    this.heightIn,
    this.oxygenSaturation,
    this.respiratoryRate,
    this.bmi,
    this.painScale,
    this.notes,
  });

  factory _Vital.fromMap(Map<String, dynamic> m) {
    double? asDouble(dynamic v) {
      if (v == null) return null;
      if (v is num) return v.toDouble();
      if (v is String) return double.tryParse(v);
      return null;
    }

    int? asInt(dynamic v) {
      if (v == null) return null;
      if (v is num) return v.toInt();
      if (v is String) return int.tryParse(v);
      return null;
    }

    return _Vital(
      bloodPressure: m['bloodPressure'] as String? ?? m['bp'] as String?,
      heartRate: asInt(m['heartRate'] ?? m['hr'] ?? m['pulse']),
      temperatureF: asDouble(m['temperatureF'] ?? m['tempF'] ?? m['temp']),
      weightLbs: asDouble(m['weightLbs'] ?? m['weight']),
      heightIn: asDouble(m['heightIn'] ?? m['height']),
      oxygenSaturation: asInt(m['oxygenSaturation'] ?? m['spo2'] ?? m['o2']),
      respiratoryRate: asInt(m['respiratoryRate'] ?? m['rr']),
      bmi: asDouble(m['bmi']),
      painScale: asInt(m['painScale'] ?? m['pain']),
      notes: m['notes'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        if (bloodPressure != null) 'bloodPressure': bloodPressure,
        if (heartRate != null) 'heartRate': heartRate,
        if (temperatureF != null) 'temperatureF': temperatureF,
        if (weightLbs != null) 'weightLbs': weightLbs,
        if (heightIn != null) 'heightIn': heightIn,
        if (oxygenSaturation != null) 'oxygenSaturation': oxygenSaturation,
        if (respiratoryRate != null) 'respiratoryRate': respiratoryRate,
        if (bmi != null) 'bmi': bmi,
        if (painScale != null) 'painScale': painScale,
        if (notes != null) 'notes': notes,
      };

  /// Returns true if any field is populated.
  bool get hasAny =>
      bloodPressure != null ||
      heartRate != null ||
      temperatureF != null ||
      weightLbs != null ||
      heightIn != null ||
      oxygenSaturation != null ||
      respiratoryRate != null ||
      bmi != null ||
      painScale != null;
}

/// A diagnosis or assessment recorded at a visit. ICD-10 code optional;
/// label is always required.
class _Diagnosis {
  final String label; // "Acute sinusitis"
  final String? icdCode; // "J01.00" — optional
  final String? notes; // provider's clarification
  final bool isPrimary; // first listed diagnosis gets visual emphasis

  const _Diagnosis({
    required this.label,
    this.icdCode,
    this.notes,
    this.isPrimary = false,
  });

  factory _Diagnosis.fromMap(Map<String, dynamic> m) => _Diagnosis(
        label: (m['label'] as String?) ?? (m['name'] as String?) ?? 'Diagnosis',
        icdCode: m['icdCode'] as String? ?? m['code'] as String?,
        notes: m['notes'] as String?,
        isPrimary: m['isPrimary'] == true || m['primary'] == true,
      );

  Map<String, dynamic> toJson() => {
        'label': label,
        if (icdCode != null) 'icdCode': icdCode,
        if (notes != null) 'notes': notes,
        'isPrimary': isPrimary,
      };
}

/// A prescription ordered at a visit OR standing on the member's profile.
/// For the visit-record use case, we typically only care about
/// prescriptions ordered during THAT visit, but the full rx list is also
/// used for the timeline tab.
class _Prescription {
  final String medicationName; // "Amoxicillin"
  final String? dosage; // "500 mg"
  final String? form; // "tablet" / "suspension"
  final String? frequency; // "three times daily"
  final String? duration; // "10 days"
  final int? refillsRemaining;
  final DateTime? prescribedAt;
  final DateTime? filledAt;
  final DateTime? expiresAt;
  final PrescriptionStatus status;
  final String? prescriber; // "Dr. Martinez"
  final String? pharmacy;
  final String? instructions; // SIG e.g. "Take with food"
  final String? reason; // "for sinus infection"

  const _Prescription({
    required this.medicationName,
    this.dosage,
    this.form,
    this.frequency,
    this.duration,
    this.refillsRemaining,
    this.prescribedAt,
    this.filledAt,
    this.expiresAt,
    this.status = PrescriptionStatus.unknown,
    this.prescriber,
    this.pharmacy,
    this.instructions,
    this.reason,
  });

  factory _Prescription.fromMap(Map<String, dynamic> m) {
    DateTime? parseTs(dynamic v) {
      if (v == null) return null;
      if (v is Timestamp) return v.toDate();
      if (v is String) return DateTime.tryParse(v);
      return null;
    }

    int? asInt(dynamic v) {
      if (v == null) return null;
      if (v is num) return v.toInt();
      if (v is String) return int.tryParse(v);
      return null;
    }

    return _Prescription(
      medicationName: (m['medicationName'] as String?) ??
          (m['name'] as String?) ??
          (m['medication'] as String?) ??
          'Medication',
      dosage: m['dosage'] as String? ?? m['dose'] as String?,
      form: m['form'] as String?,
      frequency: m['frequency'] as String? ?? m['freq'] as String?,
      duration: m['duration'] as String?,
      refillsRemaining: asInt(m['refillsRemaining'] ?? m['refills']),
      prescribedAt: parseTs(m['prescribedAt'] ?? m['createdAt']),
      filledAt: parseTs(m['filledAt']),
      expiresAt: parseTs(m['expiresAt']),
      status: _rxStatusParse(m['status'] as String?),
      prescriber: m['prescriber'] as String? ?? m['provider'] as String?,
      pharmacy: m['pharmacy'] as String?,
      instructions: m['instructions'] as String? ?? m['sig'] as String?,
      reason: m['reason'] as String? ?? m['indication'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        'medicationName': medicationName,
        if (dosage != null) 'dosage': dosage,
        if (form != null) 'form': form,
        if (frequency != null) 'frequency': frequency,
        if (duration != null) 'duration': duration,
        if (refillsRemaining != null) 'refillsRemaining': refillsRemaining,
        if (prescribedAt != null)
          'prescribedAt': prescribedAt!.toIso8601String(),
        if (filledAt != null) 'filledAt': filledAt!.toIso8601String(),
        if (expiresAt != null) 'expiresAt': expiresAt!.toIso8601String(),
        'status': _rxStatusSerialize(status),
        if (prescriber != null) 'prescriber': prescriber,
        if (pharmacy != null) 'pharmacy': pharmacy,
        if (instructions != null) 'instructions': instructions,
        if (reason != null) 'reason': reason,
      };

  /// Short human-friendly summary like "Amoxicillin 500 mg — 3x daily x10 days"
  String get summary {
    final parts = <String>[medicationName];
    if (dosage != null && dosage!.isNotEmpty) parts.add(dosage!);
    if (frequency != null && frequency!.isNotEmpty) {
      parts.add('— ${frequency!}');
    }
    if (duration != null && duration!.isNotEmpty) parts.add('x $duration');
    return parts.join(' ');
  }
}

/// A lab or imaging order placed at a visit.
class _LabOrder {
  final String name; // "CBC with differential"
  final String? category; // "hematology" / "chemistry" / "imaging"
  final String? specimen; // "blood" / "urine" / "throat swab"
  final DateTime? orderedAt;
  final DateTime? collectedAt;
  final DateTime? resultedAt;
  final LabOrderStatus status;
  final String? orderedBy; // provider
  final String? notes; // "fasting required"
  final String? resultSummary; // high-level summary if resulted

  const _LabOrder({
    required this.name,
    this.category,
    this.specimen,
    this.orderedAt,
    this.collectedAt,
    this.resultedAt,
    this.status = LabOrderStatus.unknown,
    this.orderedBy,
    this.notes,
    this.resultSummary,
  });

  factory _LabOrder.fromMap(Map<String, dynamic> m) {
    DateTime? parseTs(dynamic v) {
      if (v == null) return null;
      if (v is Timestamp) return v.toDate();
      if (v is String) return DateTime.tryParse(v);
      return null;
    }

    return _LabOrder(
      name: (m['name'] as String?) ?? (m['test'] as String?) ?? 'Lab order',
      category: m['category'] as String?,
      specimen: m['specimen'] as String?,
      orderedAt: parseTs(m['orderedAt']),
      collectedAt: parseTs(m['collectedAt']),
      resultedAt: parseTs(m['resultedAt']),
      status: _labStatusParse(m['status'] as String?),
      orderedBy: m['orderedBy'] as String?,
      notes: m['notes'] as String?,
      resultSummary: m['resultSummary'] as String? ?? m['summary'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        'name': name,
        if (category != null) 'category': category,
        if (specimen != null) 'specimen': specimen,
        if (orderedAt != null) 'orderedAt': orderedAt!.toIso8601String(),
        if (collectedAt != null) 'collectedAt': collectedAt!.toIso8601String(),
        if (resultedAt != null) 'resultedAt': resultedAt!.toIso8601String(),
        'status': _labStatusLabel(status).toLowerCase(),
        if (orderedBy != null) 'orderedBy': orderedBy,
        if (notes != null) 'notes': notes,
        if (resultSummary != null) 'resultSummary': resultSummary,
      };
}

/// A procedure performed during the visit — vaccination, suture, biopsy,
/// minor surgery, imaging done in-clinic, etc.
class _Procedure {
  final String name; // "Flu vaccine"
  final String? cptCode; // "90686" — optional billing code
  final String? bodyLocation; // "left deltoid"
  final String? performedBy;
  final String? notes; // "patient tolerated well"
  final DateTime? performedAt;

  const _Procedure({
    required this.name,
    this.cptCode,
    this.bodyLocation,
    this.performedBy,
    this.notes,
    this.performedAt,
  });

  factory _Procedure.fromMap(Map<String, dynamic> m) {
    DateTime? parseTs(dynamic v) {
      if (v == null) return null;
      if (v is Timestamp) return v.toDate();
      if (v is String) return DateTime.tryParse(v);
      return null;
    }

    return _Procedure(
      name: (m['name'] as String?) ?? 'Procedure',
      cptCode: m['cptCode'] as String? ?? m['code'] as String?,
      bodyLocation: m['bodyLocation'] as String? ?? m['location'] as String?,
      performedBy: m['performedBy'] as String? ?? m['provider'] as String?,
      notes: m['notes'] as String?,
      performedAt: parseTs(m['performedAt']),
    );
  }

  Map<String, dynamic> toJson() => {
        'name': name,
        if (cptCode != null) 'cptCode': cptCode,
        if (bodyLocation != null) 'bodyLocation': bodyLocation,
        if (performedBy != null) 'performedBy': performedBy,
        if (notes != null) 'notes': notes,
        if (performedAt != null) 'performedAt': performedAt!.toIso8601String(),
      };
}

/// Follow-up plan the provider recorded for the member.
class _FollowUpPlan {
  final String? summary; // freeform "Come back in 2 weeks if X"
  final List<String> redFlags; // "Return immediately if fever > 103"
  final String? nextAppointmentRecommendation; // "Schedule PCP follow-up in 2w"
  final String? patientInstructions; // "Rest, fluids, avoid strenuous activity"
  final String? referral; // "Refer to ENT if not improved in 2 weeks"

  const _FollowUpPlan({
    this.summary,
    this.redFlags = const [],
    this.nextAppointmentRecommendation,
    this.patientInstructions,
    this.referral,
  });

  factory _FollowUpPlan.fromMap(Map<String, dynamic> m) {
    final rawFlags = m['redFlags'];
    List<String> flags = const [];
    if (rawFlags is List) {
      flags = rawFlags
          .whereType<String>()
          .where((s) => s.trim().isNotEmpty)
          .toList();
    }
    return _FollowUpPlan(
      summary: m['summary'] as String?,
      redFlags: flags,
      nextAppointmentRecommendation:
          m['nextAppointmentRecommendation'] as String? ??
              m['nextAppointment'] as String?,
      patientInstructions:
          m['patientInstructions'] as String? ?? m['instructions'] as String?,
      referral: m['referral'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        if (summary != null) 'summary': summary,
        if (redFlags.isNotEmpty) 'redFlags': redFlags,
        if (nextAppointmentRecommendation != null)
          'nextAppointmentRecommendation': nextAppointmentRecommendation,
        if (patientInstructions != null)
          'patientInstructions': patientInstructions,
        if (referral != null) 'referral': referral,
      };

  bool get hasAny =>
      (summary != null && summary!.isNotEmpty) ||
      redFlags.isNotEmpty ||
      (nextAppointmentRecommendation != null &&
          nextAppointmentRecommendation!.isNotEmpty) ||
      (patientInstructions != null && patientInstructions!.isNotEmpty) ||
      (referral != null && referral!.isNotEmpty);
}

/// Billing summary the member sees after a Jovi visit. Cost-sharing
/// members really care about this section — they want to know what
/// their membership covered.
class _VisitBilling {
  final double? totalCharged; // what the clinic billed
  final double? joviCovered; // amount covered by membership
  final double? memberShare; // what the member owes (0 for most visits)
  final String? paymentStatus; // "paid" / "pending" / "waived"
  final String? notes; // "Lab fee waived as part of preventive visit"

  const _VisitBilling({
    this.totalCharged,
    this.joviCovered,
    this.memberShare,
    this.paymentStatus,
    this.notes,
  });

  factory _VisitBilling.fromMap(Map<String, dynamic> m) {
    double? asDouble(dynamic v) {
      if (v == null) return null;
      if (v is num) return v.toDouble();
      if (v is String) return double.tryParse(v);
      return null;
    }

    return _VisitBilling(
      totalCharged: asDouble(m['totalCharged'] ?? m['total']),
      joviCovered: asDouble(m['joviCovered'] ?? m['covered']),
      memberShare: asDouble(m['memberShare'] ?? m['owed']),
      paymentStatus: m['paymentStatus'] as String? ?? m['status'] as String?,
      notes: m['notes'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        if (totalCharged != null) 'totalCharged': totalCharged,
        if (joviCovered != null) 'joviCovered': joviCovered,
        if (memberShare != null) 'memberShare': memberShare,
        if (paymentStatus != null) 'paymentStatus': paymentStatus,
        if (notes != null) 'notes': notes,
      };

  bool get hasAny =>
      totalCharged != null ||
      joviCovered != null ||
      memberShare != null ||
      paymentStatus != null ||
      (notes != null && notes!.isNotEmpty);
}

/// A file attachment on a visit record. Shape is intentionally flexible
/// to accommodate whatever the clinic-side charting tool ends up writing:
/// lab PDFs, imaging reports, discharge summaries, referral letters, etc.
///
/// Expected schema on visit_records/{id}.attachments (List<Map>):
///   name: String         — user-facing label
///   url: String          — Firebase Storage download URL (required for tap)
///   contentType: String  — MIME type, used to pick an icon
///   sizeBytes: int       — optional, for display
///   uploadedAt: Timestamp — optional
///   category: String     — optional: 'lab' | 'imaging' | 'discharge' |
///                          'referral' | 'photo' | 'other'
///
/// Defensive parsing: any attachment missing `url` is dropped with a log
/// — we don't render broken tap targets.
class _Attachment {
  final String name;
  final String url;
  final String? contentType;
  final int? sizeBytes;
  final DateTime? uploadedAt;
  final String? category;

  const _Attachment({
    required this.name,
    required this.url,
    this.contentType,
    this.sizeBytes,
    this.uploadedAt,
    this.category,
  });

  static _Attachment? fromMap(Map<String, dynamic> m) {
    final url = m['url'] as String?;
    if (url == null || url.isEmpty) return null;
    DateTime? parseTs(dynamic v) {
      if (v == null) return null;
      if (v is Timestamp) return v.toDate();
      if (v is String) return DateTime.tryParse(v);
      return null;
    }

    return _Attachment(
      name: (m['name'] as String?)?.trim().isNotEmpty == true
          ? (m['name'] as String).trim()
          : _fileNameFromUrl(url),
      url: url,
      contentType: m['contentType'] as String? ?? m['mimeType'] as String?,
      sizeBytes: _asInt(m['sizeBytes'] ?? m['size']),
      uploadedAt: parseTs(m['uploadedAt'] ?? m['createdAt']),
      category: (m['category'] as String?)?.toLowerCase(),
    );
  }

  /// Pick a reasonable icon based on contentType / category / extension.
  IconData get displayIcon {
    final ct = (contentType ?? '').toLowerCase();
    final cat = (category ?? '').toLowerCase();
    if (cat == 'imaging' || ct.contains('image') || _isImageUrl(url)) {
      return Icons.image_outlined;
    }
    if (cat == 'lab') return Icons.science_outlined;
    if (cat == 'discharge') return Icons.medical_information_outlined;
    if (cat == 'referral') return Icons.share_outlined;
    if (ct.contains('pdf') || url.toLowerCase().contains('.pdf')) {
      return Icons.picture_as_pdf_outlined;
    }
    return Icons.insert_drive_file_outlined;
  }

  /// Category label for the row subtitle. Null if category unknown.
  String? get categoryLabel {
    switch (category) {
      case 'lab':
        return 'Lab result';
      case 'imaging':
        return 'Imaging';
      case 'discharge':
        return 'Discharge summary';
      case 'referral':
        return 'Referral';
      case 'photo':
        return 'Photo';
      case 'other':
        return 'Document';
      default:
        return null;
    }
  }

  /// Human-readable file size, e.g. "1.2 MB" / "340 KB" / null if unknown.
  String? get sizeDisplay {
    if (sizeBytes == null || sizeBytes! <= 0) return null;
    final kb = sizeBytes! / 1024.0;
    if (kb < 1024) return '${kb.toStringAsFixed(0)} KB';
    final mb = kb / 1024.0;
    return '${mb.toStringAsFixed(1)} MB';
  }

  static String _fileNameFromUrl(String url) {
    try {
      final uri = Uri.parse(url);
      final seg = uri.pathSegments.isNotEmpty ? uri.pathSegments.last : '';
      final decoded = Uri.decodeComponent(seg);
      return decoded.isEmpty ? 'Attachment' : decoded;
    } catch (_) {
      return 'Attachment';
    }
  }

  static bool _isImageUrl(String url) {
    final u = url.toLowerCase();
    return u.contains('.jpg') ||
        u.contains('.jpeg') ||
        u.contains('.png') ||
        u.contains('.gif') ||
        u.contains('.webp') ||
        u.contains('.heic');
  }
}

/// An APPOINTMENT — the scheduling-layer entity. Created by Request Care,
/// confirmed by the clinic, tracked through completion (at which point a
/// visit_record should be linked).
class _Appointment {
  final String id;
  final DateTime startAt;
  final int? durationMinutes;
  final AppointmentType type;
  final AppointmentStatus status;
  final String? providerName;
  final String? providerCredentials; // "MD" / "NP" / "PA"
  final String? clinicName;
  final String? clinicAddress;
  final double? clinicLat;
  final double? clinicLng;
  final String? clinicPhone;
  final String? reason; // member-entered reason for visit
  final String? notes; // staff notes
  final bool isTelehealth;
  final String? telehealthUrl;
  final String? linkedVisitRecordId; // populated once visit completed
  final DateTime? createdAt;
  final DateTime? updatedAt;
  final String? cancelledReason;

  /// Patient name for this visit. May be the primary user OR a dependent.
  /// Used by the family-member filter in Care Records.
  final String? patientName;

  const _Appointment({
    required this.id,
    required this.startAt,
    this.durationMinutes,
    this.type = AppointmentType.other,
    this.status = AppointmentStatus.unknown,
    this.providerName,
    this.providerCredentials,
    this.clinicName,
    this.clinicAddress,
    this.clinicLat,
    this.clinicLng,
    this.clinicPhone,
    this.reason,
    this.notes,
    this.isTelehealth = false,
    this.telehealthUrl,
    this.linkedVisitRecordId,
    this.createdAt,
    this.updatedAt,
    this.cancelledReason,
    this.patientName,
  });

  /// Builds an _Appointment from a document in the top-level `requests`
  /// collection (the schema written by the Request Care widget).
  /// See jovi_requests_flow.dart `_submitRequest()` for the source of
  /// truth on which fields exist.
  factory _Appointment.fromFirestore(String docId, Map<String, dynamic> m) {
    DateTime? parseTs(dynamic v) {
      if (v == null) return null;
      if (v is Timestamp) return v.toDate();
      if (v is String) return DateTime.tryParse(v);
      return null;
    }

    int? asInt(dynamic v) {
      if (v == null) return null;
      if (v is num) return v.toInt();
      if (v is String) return int.tryParse(v);
      return null;
    }

    // --- Date + time parsing ---------------------------------------
    // The Request widget stores these as two separate string fields:
    //   appointmentDate: "2026-04-20T00:00:00"
    //   appointmentTime: "10:30"  (24-hour HH:MM)
    // We combine them into a single DateTime. Legacy new-schema docs
    // may use `startAt` directly.
    DateTime start;
    final directStart = m['startAt'];
    if (directStart != null) {
      start = parseTs(directStart) ?? DateTime.now();
    } else {
      final dateStr = m['appointmentDate'] as String?;
      final timeStr = m['appointmentTime'] as String?;
      DateTime? parsedDate;
      if (dateStr != null && dateStr.isNotEmpty) {
        parsedDate = DateTime.tryParse(dateStr);
      }
      parsedDate ??= DateTime.now();
      // Apply time if we have it
      if (timeStr != null && timeStr.isNotEmpty) {
        // Request Care stores display slots like "2:30 PM"; older docs may be "14:30".
        final parts = timeStr.trim().split(':');
        if (parts.length >= 2) {
          var hh = int.tryParse(parts[0]);
          final rest = parts[1].trim();
          final mm = int.tryParse(rest.length >= 2 ? rest.substring(0, 2) : rest);
          final ap = rest.toUpperCase();
          if (hh != null) {
            if (ap.contains('PM') && hh < 12) hh += 12;
            if (ap.contains('AM') && hh == 12) hh = 0;
          }
          if (hh != null && mm != null) {
            parsedDate = DateTime(
              parsedDate.year,
              parsedDate.month,
              parsedDate.day,
              hh,
              mm,
            );
          }
        }
      }
      start = parsedDate;
    }

    // --- Type inference --------------------------------------------
    // The Request widget writes `visitType` as a human string like
    // "Primary Care" or "Urgent Care". Our parser normalizes this.
    // `visitMode` tells us telehealth vs in-person.
    final rawVisitType = m['visitType'] as String?;
    final rawVisitMode = m['visitMode'] as String?;
    AppointmentType apptType = _apptTypeParse(rawVisitType);
    // Visit mode override: if mode says telehealth, force that type
    // (unless the visitType was specifically lab/imaging/etc).
    if (rawVisitMode != null) {
      final mode = rawVisitMode.toLowerCase();
      if (mode.contains('telehealth') ||
          mode.contains('virtual') ||
          mode.contains('video')) {
        // Only override if we didn't already have a specific non-generic
        // type like lab/imaging/vaccination
        if (apptType == AppointmentType.other ||
            apptType == AppointmentType.primaryCare) {
          apptType = AppointmentType.telehealth;
        }
      }
    }

    // --- Status parsing --------------------------------------------
    // Request widget writes `status` as "pending" / "confirmed" /
    // "completed". Our enum has `scheduled` which we map from both
    // pending and confirmed.
    final rawStatus = m['status'] as String? ?? 'pending';
    AppointmentStatus status = _apptStatusParse(rawStatus);
    if (status == AppointmentStatus.unknown) {
      // "pending" and "confirmed" should both be treated as scheduled.
      // "available" means the slot was freed by a cancellation and is
      // open for other patients — from the cancelling member's point of
      // view it's effectively cancelled.
      final s = rawStatus.toLowerCase();
      if (s == 'pending' || s == 'confirmed') {
        status = AppointmentStatus.scheduled;
      } else if (s == 'available') {
        status = AppointmentStatus.cancelled;
      }
    }

    // --- Provider / clinic -----------------------------------------
    // The request schema stores `clinic` as a name string. Provider
    // assignment happens clinic-side, so may not be present yet.
    final clinicName = m['clinic'] as String? ?? m['clinicName'] as String?;

    // --- Reason / chief complaint ----------------------------------
    // Member writes their reason across multiple fields. Prefer the
    // specific `symptom`, fall back to `details`, then `reason`.
    String? reason = m['reason'] as String? ?? m['chiefComplaint'] as String?;
    if (reason == null || reason.isEmpty) {
      final symptom = m['symptom'] as String?;
      final details = m['details'] as String?;
      if (symptom != null && symptom.isNotEmpty) {
        reason = symptom;
      } else if (details != null && details.isNotEmpty) {
        reason = details;
      }
    }

    final telehealthUrl =
        m['telehealthUrl'] as String? ?? m['videoUrl'] as String?;
    final isTelehealth = apptType == AppointmentType.telehealth ||
        m['isTelehealth'] == true ||
        m['telehealth'] == true;

    return _Appointment(
      id: docId,
      startAt: start,
      durationMinutes: asInt(m['durationMinutes'] ?? m['duration']),
      type: apptType,
      status: status,
      providerName: m['providerName'] as String? ?? m['provider'] as String?,
      providerCredentials: m['providerCredentials'] as String?,
      clinicName: clinicName,
      clinicAddress: m['clinicAddress'] as String? ?? m['address'] as String?,
      clinicLat: _asDouble(m['clinicLat'] ?? m['lat']),
      clinicLng: _asDouble(m['clinicLng'] ?? m['lng']),
      clinicPhone: m['clinicPhone'] as String? ?? m['phone'] as String?,
      reason: reason,
      notes: m['notes'] as String?,
      isTelehealth: isTelehealth,
      telehealthUrl: telehealthUrl,
      linkedVisitRecordId:
          m['linkedVisitRecordId'] as String? ?? m['visitRecordId'] as String?,
      createdAt: parseTs(m['createdAt']),
      updatedAt: parseTs(m['updatedAt']),
      cancelledReason: m['cancelledReason'] as String?,
      patientName: m['patientName'] as String?,
    );
  }

  /// True if this appointment is in the future relative to now.
  bool get isUpcoming {
    if (status == AppointmentStatus.cancelled ||
        status == AppointmentStatus.completed ||
        status == AppointmentStatus.noShow) {
      return false;
    }
    return startAt.isAfter(DateTime.now());
  }

  /// True if this appointment already happened (completed, noShow, or
  /// scheduled but time has passed).
  bool get isPast {
    if (status == AppointmentStatus.completed ||
        status == AppointmentStatus.noShow) return true;
    if (status == AppointmentStatus.cancelled) return false;
    return startAt.isBefore(DateTime.now());
  }

  /// Combined provider display name with credentials if both exist.
  String get providerDisplay {
    if (providerName == null || providerName!.isEmpty) return 'Provider';
    if (providerCredentials == null || providerCredentials!.isEmpty) {
      return providerName!;
    }
    return '$providerName, $providerCredentials';
  }
}

/// The POST-VISIT CLINICAL RECORD. One-to-one with a completed
/// appointment via [appointmentId]. This is the substantial payload —
/// all the clinical detail members see when they tap into a past visit.
class _VisitRecord {
  final String id;
  final String? appointmentId;
  final DateTime visitDate;
  final int? durationMinutes;
  final AppointmentType type;
  final String? providerName;
  final String? providerCredentials;
  final String? clinicName;
  final String? clinicAddress;
  final String? chiefComplaint;
  final String? historyOfPresentIllness; // HPI freetext
  final _Vital? vitals;
  final List<_Diagnosis> diagnoses;
  final List<_Prescription> prescriptions;
  final List<_LabOrder> labOrders;
  final List<_Procedure> procedures;
  final String? clinicalNotes; // provider's narrative
  final String? patientEducation; // "Handout: URI care" style
  final _FollowUpPlan? followUp;
  final _VisitBilling? billing;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  /// Patient name for this visit. May be the primary user OR a dependent.
  /// Copied forward from the associated appointment when the clinic
  /// charts the visit record.
  final String? patientName;

  /// File attachments — lab PDFs, imaging reports, discharge summaries,
  /// referral letters. Empty list is fine; the section only renders
  /// when there's at least one attachment.
  final List<_Attachment> attachments;

  const _VisitRecord({
    required this.id,
    this.appointmentId,
    required this.visitDate,
    this.durationMinutes,
    this.type = AppointmentType.other,
    this.providerName,
    this.providerCredentials,
    this.clinicName,
    this.clinicAddress,
    this.chiefComplaint,
    this.historyOfPresentIllness,
    this.vitals,
    this.diagnoses = const [],
    this.prescriptions = const [],
    this.labOrders = const [],
    this.procedures = const [],
    this.clinicalNotes,
    this.patientEducation,
    this.followUp,
    this.billing,
    this.createdAt,
    this.updatedAt,
    this.patientName,
    this.attachments = const [],
  });

  factory _VisitRecord.fromFirestore(String docId, Map<String, dynamic> m) {
    DateTime parseRequiredTs(dynamic v, DateTime fallback) {
      if (v is Timestamp) return v.toDate();
      if (v is String) {
        final d = DateTime.tryParse(v);
        if (d != null) return d;
      }
      return fallback;
    }

    DateTime? parseTs(dynamic v) {
      if (v == null) return null;
      if (v is Timestamp) return v.toDate();
      if (v is String) return DateTime.tryParse(v);
      return null;
    }

    int? asInt(dynamic v) {
      if (v == null) return null;
      if (v is num) return v.toInt();
      if (v is String) return int.tryParse(v);
      return null;
    }

    List<T> parseList<T>(
      dynamic raw,
      T Function(Map<String, dynamic>) fromMap,
    ) {
      if (raw is! List) return [];
      final out = <T>[];
      for (final item in raw) {
        if (item is Map) {
          try {
            out.add(fromMap(Map<String, dynamic>.from(item)));
          } catch (e) {
            _logError('skipped malformed list item', e);
          }
        }
      }
      return out;
    }

    final visitDate =
        parseRequiredTs(m['visitDate'] ?? m['date'], DateTime.now());

    final rawVitals = m['vitals'];
    _Vital? vitals;
    if (rawVitals is Map) {
      vitals = _Vital.fromMap(Map<String, dynamic>.from(rawVitals));
    }

    final rawFollow = m['followUp'];
    _FollowUpPlan? followUp;
    if (rawFollow is Map) {
      followUp = _FollowUpPlan.fromMap(Map<String, dynamic>.from(rawFollow));
    }

    final rawBilling = m['billing'];
    _VisitBilling? billing;
    if (rawBilling is Map) {
      billing = _VisitBilling.fromMap(Map<String, dynamic>.from(rawBilling));
    }

    return _VisitRecord(
      id: docId,
      appointmentId: m['appointmentId'] as String?,
      visitDate: visitDate,
      durationMinutes: asInt(m['durationMinutes']),
      type: _apptTypeParse(m['type'] as String?),
      providerName: m['providerName'] as String? ?? m['provider'] as String?,
      providerCredentials: m['providerCredentials'] as String?,
      clinicName: m['clinicName'] as String? ?? m['clinic'] as String?,
      clinicAddress: m['clinicAddress'] as String?,
      chiefComplaint: m['chiefComplaint'] as String? ?? m['reason'] as String?,
      historyOfPresentIllness:
          m['historyOfPresentIllness'] as String? ?? m['hpi'] as String?,
      vitals: vitals,
      diagnoses: parseList(m['diagnoses'], _Diagnosis.fromMap),
      prescriptions: parseList(m['prescriptions'], _Prescription.fromMap),
      labOrders: parseList(m['labOrders'] ?? m['labs'], _LabOrder.fromMap),
      procedures: parseList(m['procedures'], _Procedure.fromMap),
      clinicalNotes: m['clinicalNotes'] as String? ?? m['notes'] as String?,
      patientEducation: m['patientEducation'] as String?,
      followUp: followUp,
      billing: billing,
      createdAt: parseTs(m['createdAt']),
      updatedAt: parseTs(m['updatedAt']),
      patientName: m['patientName'] as String?,
      attachments: _parseAttachments(m['attachments']),
    );
  }

  /// Helper to safely parse the attachments array. Dropped entries (bad
  /// URL etc) are silently skipped.
  static List<_Attachment> _parseAttachments(dynamic raw) {
    if (raw is! List) return const [];
    final out = <_Attachment>[];
    for (final item in raw) {
      if (item is Map<String, dynamic>) {
        final att = _Attachment.fromMap(item);
        if (att != null) out.add(att);
      } else if (item is Map) {
        // Some Firestore SDK paths yield Map<dynamic, dynamic>
        final coerced = <String, dynamic>{};
        item.forEach((k, v) {
          if (k is String) coerced[k] = v;
        });
        final att = _Attachment.fromMap(coerced);
        if (att != null) out.add(att);
      }
    }
    return out;
  }

  /// Combined provider display.
  String get providerDisplay {
    if (providerName == null || providerName!.isEmpty) return 'Provider';
    if (providerCredentials == null || providerCredentials!.isEmpty) {
      return providerName!;
    }
    return '$providerName, $providerCredentials';
  }

  /// Primary diagnosis label (first isPrimary, else first diagnosis).
  String? get primaryDiagnosisLabel {
    if (diagnoses.isEmpty) return null;
    for (final d in diagnoses) {
      if (d.isPrimary) return d.label;
    }
    return diagnoses.first.label;
  }
}

/// Unified care-timeline event. We merge appointments, visit records,
/// prescriptions, symptom checks, and claims into this envelope so the
/// timeline can sort and render them with a single code path.
class _CareEvent {
  final String id;
  final DateTime timestamp;
  final CareEventKind kind;
  final String title; // "Visit with Dr. Martinez"
  final String? subtitle; // "Primary care • Dakota Ridge"
  final String? detail; // one-line summary displayed below subtitle
  final Color accent;
  final IconData icon;
  final String? sourceCollection; // "appointments" / "visit_records" / etc
  final String? sourceDocId; // for tap-through if applicable

  /// Opaque reference back to the richer underlying object so handlers
  /// can pivot into the appropriate detail view.
  final Object? payload;

  const _CareEvent({
    required this.id,
    required this.timestamp,
    required this.kind,
    required this.title,
    this.subtitle,
    this.detail,
    required this.accent,
    required this.icon,
    this.sourceCollection,
    this.sourceDocId,
    this.payload,
  });
}

// =======================================================================
// PAST-ENTRIES HELPER TYPES
// Envelope for merging visit_records, completed-but-not-charted
// appointments, and cancelled appointments into one list card stream.
// =======================================================================

enum _PastEntryKind {
  visitRecord, // full clinical detail available
  appointmentOnly, // visit happened but no chart yet
  cancelled, // cancelled by the member
}

class _PastEntry {
  final String id;
  final DateTime when;
  final _PastEntryKind kind;
  final Object payload; // _VisitRecord or _Appointment

  const _PastEntry({
    required this.id,
    required this.when,
    required this.kind,
    required this.payload,
  });
}

/// Data shape for a single vital cell in the visit detail grid.
/// Top-level so the builder method can construct a list cleanly.
class _VitalCellData {
  final String label;
  final String value;
  final String unit;
  final IconData icon;
  final Color color;

  const _VitalCellData({
    required this.label,
    required this.value,
    required this.unit,
    required this.icon,
    required this.color,
  });
}

// =======================================================================
// HTTP / NETWORK ERROR CLASSIFICATION
// Mirrors the pattern from jovi_symptom_checker so failure modes are
// classified identically across widgets.
// =======================================================================

enum _FirestoreErrorKind {
  offline, // no connectivity
  permissionDenied, // security rules rejected
  notFound, // collection/doc doesn't exist
  unavailable, // server temporarily unreachable
  timeout, // request exceeded budget
  unknown,
}

class _CareRecordsError implements Exception {
  final _FirestoreErrorKind kind;
  final String message;
  const _CareRecordsError({required this.kind, required this.message});
  @override
  String toString() => 'CareRecordsError($kind): $message';
}

/// Classify a raw Firestore exception into one of our kinds.
_FirestoreErrorKind _classifyFirestoreError(Object e) {
  final s = e.toString().toLowerCase();
  if (s.contains('permission-denied') || s.contains('permission_denied')) {
    return _FirestoreErrorKind.permissionDenied;
  }
  if (s.contains('not-found') || s.contains('not_found')) {
    return _FirestoreErrorKind.notFound;
  }
  if (s.contains('unavailable') || s.contains('server unavailable')) {
    return _FirestoreErrorKind.unavailable;
  }
  if (s.contains('deadline-exceeded') ||
      s.contains('timeout') ||
      s.contains('timed out')) {
    return _FirestoreErrorKind.timeout;
  }
  if (s.contains('socketexception') ||
      s.contains('failed host lookup') ||
      s.contains('network is unreachable') ||
      s.contains('offline')) {
    return _FirestoreErrorKind.offline;
  }
  return _FirestoreErrorKind.unknown;
}

String _errorMessageForFirestore(_FirestoreErrorKind k) {
  switch (k) {
    case _FirestoreErrorKind.offline:
      return "You're offline. Reconnect to load your records.";
    case _FirestoreErrorKind.permissionDenied:
      return "We couldn't access your records. Please sign out and back in, or contact support.";
    case _FirestoreErrorKind.notFound:
      return "No records found.";
    case _FirestoreErrorKind.unavailable:
      return "Our servers are temporarily unavailable. Please try again in a moment.";
    case _FirestoreErrorKind.timeout:
      return "Loading is taking too long. Please try again.";
    case _FirestoreErrorKind.unknown:
      return "We couldn't load your records. Please try again.";
  }
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

class CareRecords extends StatefulWidget {
  final double width;
  final double height;

  const CareRecords({
    Key? key,
    required this.width,
    required this.height,
  }) : super(key: key);

  @override
  State<CareRecords> createState() => _CareRecordsState();
}

class _CareRecordsState extends State<CareRecords>
    with TickerProviderStateMixin {
  // ---------------- Tab state ----------------
  _Tab _currentTab = _Tab.upcoming;

  // ---------------- Patient filter state ----------------
  // The primary user plus any dependents they manage. Loaded once from
  // users/{uid}.onboard_fullName + users/{uid}.deps (JSON-encoded strings,
  // same schema written by jovi_requests_flow.dart _loadPatientNames).
  // Selected filter value:
  //   null         → Everyone (default, show all records)
  //   string name  → show only records where patientName matches
  List<String> _patientNames = [];
  String? _selectedPatientFilter;
  bool _loadingPatients = true;

  // ---------------- Search state ----------------
  // When _searchActive is true, the app bar swaps to a search input.
  // _searchQuery is applied case-insensitively against multiple fields
  // (provider, clinic, reason, diagnoses, medication names, event title
  // / subtitle / detail). Search and patient filter compose — they're
  // applied to the same underlying filtered lists.
  bool _searchActive = false;
  String _searchQuery = '';
  final TextEditingController _searchCtrl = TextEditingController();
  final FocusNode _searchFocus = FocusNode();

  // ---------------- Data state ----------------
  // Appointments split into upcoming and past for cheap rendering.
  List<_Appointment> _upcomingAppointments = [];
  List<_Appointment> _pastAppointments = [];
  // Cancelled appointments (originally booked by this user) — shown in
  // the Past tab as historical context. After cancellation, the `userId`
  // field on the request doc is nulled, so we query by `previousUserId`
  // to find them.
  List<_Appointment> _cancelledAppointments = [];
  List<_VisitRecord> _visitRecords = [];

  // Timeline merged from multiple source collections.
  List<_CareEvent> _timeline = [];

  // ---------------- Loading / error state ----------------
  bool _loadingAppointments = true;
  bool _loadingVisits = true;
  bool _loadingTimeline = true;
  String? _appointmentsError;
  String? _visitsError;
  String? _timelineError;

  // Retry attempt counts per stream
  int _appointmentsRetries = 0;
  int _visitsRetries = 0;

  static const int _maxRetries = 3;

  // ---------------- Stream subscriptions ----------------
  StreamSubscription<QuerySnapshot<Map<String, dynamic>>>? _apptSub;
  StreamSubscription<QuerySnapshot<Map<String, dynamic>>>? _cancelledSub;
  StreamSubscription<QuerySnapshot<Map<String, dynamic>>>? _visitsSub;

  // Timeline uses one-shot queries because we merge from multiple
  // collections; real-time sync would require N listeners.
  Timer? _timelineRefreshTimer;

  // ---------------- Animations ----------------
  late AnimationController _fadeCtrl;
  late Animation<double> _fadeAnim;

  // ---------------- Lifecycle ----------------

  @override
  void initState() {
    super.initState();
    _fadeCtrl = AnimationController(vsync: this, duration: _Motion.enter);
    _fadeAnim = CurvedAnimation(parent: _fadeCtrl, curve: Curves.easeOut);

    // Respect reduced-motion preference
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      if (MediaQuery.of(context).disableAnimations) {
        _fadeCtrl.value = 1.0;
      } else {
        _fadeCtrl.forward();
      }
    });

    _subscribeToAppointments();
    _subscribeToCancelledAppointments();
    _subscribeToVisitRecords();
    _loadTimeline();
    _loadPatientNames();

    // Auto-refresh the timeline every 2 minutes while widget is open.
    // Appointments and visit records use live listeners so they update
    // in real time, but timeline depends on a merged one-shot query.
    _timelineRefreshTimer = Timer.periodic(
      const Duration(minutes: 2),
      (_) {
        if (!mounted) return;
        _loadTimeline();
      },
    );

    _analytics('care_records_opened');
  }

  @override
  void dispose() {
    _fadeCtrl.dispose();
    _apptSub?.cancel();
    _cancelledSub?.cancel();
    _visitsSub?.cancel();
    _timelineRefreshTimer?.cancel();
    _searchCtrl.dispose();
    _searchFocus.dispose();
    super.dispose();
  }

  // =======================================================================
  // APPOINTMENTS SUBSCRIPTION
  // Uses Firestore's real-time listener so updates push automatically.
  // On error, attempts up to 3 automatic retries with backoff before
  // surfacing the error in the UI.
  // =======================================================================

  void _subscribeToAppointments() {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      setState(() {
        _loadingAppointments = false;
        _appointmentsError = 'Sign in to view your appointments.';
      });
      return;
    }

    _apptSub?.cancel();
    // NOTE: Appointments live in the top-level `requests` collection,
    // filtered by userId. This matches the schema written by the
    // Request Care widget (jovi_requests_flow.dart).
    //
    // We DON'T use .orderBy('createdAt') here because that would require
    // a Firestore composite index for (userId, createdAt). Instead we
    // sort client-side after the snapshot lands.
    _apptSub = FirebaseFirestore.instance
        .collection('requests')
        .where('userId', isEqualTo: user.uid)
        .snapshots()
        .listen(
      (snap) {
        if (!mounted) return;
        final upcoming = <_Appointment>[];
        final past = <_Appointment>[];
        for (final doc in snap.docs) {
          try {
            final appt = _Appointment.fromFirestore(doc.id, doc.data());
            if (appt.isUpcoming) {
              upcoming.add(appt);
            } else if (appt.status == AppointmentStatus.cancelled) {
              // Cancelled appointments go to past list for historical
              // visibility, but they're visually de-emphasized.
              past.add(appt);
            } else {
              past.add(appt);
            }
          } catch (e) {
            _logError('skipped malformed request doc ${doc.id}', e);
          }
        }
        // Upcoming: soonest first.
        upcoming.sort((a, b) => a.startAt.compareTo(b.startAt));
        // Past: most recent first.
        past.sort((a, b) => b.startAt.compareTo(a.startAt));

        setState(() {
          _upcomingAppointments = upcoming;
          _pastAppointments = past;
          _loadingAppointments = false;
          _appointmentsError = null;
          _appointmentsRetries = 0;
        });
      },
      onError: (err) {
        _logError('appointments stream failed', err);
        if (!mounted) return;
        _handleAppointmentsError(err);
      },
      cancelOnError: false,
    );
  }

  void _handleAppointmentsError(Object err) {
    final kind = _classifyFirestoreError(err);
    // Don't auto-retry permission errors; they won't fix themselves.
    if (kind == _FirestoreErrorKind.permissionDenied) {
      setState(() {
        _loadingAppointments = false;
        _appointmentsError = _errorMessageForFirestore(kind);
      });
      return;
    }

    if (_appointmentsRetries < _maxRetries) {
      _appointmentsRetries++;
      final delay = Duration(seconds: [2, 5, 10][_appointmentsRetries - 1]);
      _log('retrying appointments subscription in ${delay.inSeconds}s'
          ' (attempt $_appointmentsRetries)');
      Future.delayed(delay, () {
        if (!mounted) return;
        _subscribeToAppointments();
      });
    } else {
      setState(() {
        _loadingAppointments = false;
        _appointmentsError = _errorMessageForFirestore(kind);
      });
    }
  }

  // =======================================================================
  // PATIENT NAMES LOADING
  // Loads the list of names for the patient filter. Mirrors the logic
  // in jovi_requests_flow.dart _loadPatientNames so the filter values
  // match what the Request Care widget writes to `patientName` on the
  // request doc.
  //
  // Source schema (users/{uid}):
  //   onboard_fullName: String — primary account holder
  //   deps: List<String>       — JSON-encoded {first, last, ...} maps
  //
  // This runs once on mount. If the member adds a new dependent during
  // the session, it won't show up in the filter until Care Records is
  // reopened — acceptable trade-off for avoiding an extra stream.
  // =======================================================================

  Future<void> _loadPatientNames() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      if (!mounted) return;
      setState(() => _loadingPatients = false);
      return;
    }

    try {
      final doc = await FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .get();
      if (!doc.exists) {
        if (!mounted) return;
        setState(() => _loadingPatients = false);
        return;
      }
      final data = doc.data() as Map<String, dynamic>;
      final names = <String>[];

      final primaryName = data['onboard_fullName'] as String?;
      if (primaryName != null && primaryName.isNotEmpty) {
        names.add(primaryName);
      }

      final deps = data['deps'] as List<dynamic>? ?? [];
      for (final depJson in deps) {
        try {
          final dep = jsonDecode(depJson as String) as Map<String, dynamic>;
          final first = dep['first'] as String?;
          final last = dep['last'] as String?;
          if (first != null && last != null) {
            names.add('$first $last');
          }
        } catch (e) {
          _logError('skipped malformed dep entry', e);
        }
      }

      if (!mounted) return;
      setState(() {
        _patientNames = names;
        _loadingPatients = false;
      });
      _log('loaded ${names.length} patient name(s) for filter');
    } catch (e) {
      _logError('failed to load patient names', e);
      if (!mounted) return;
      setState(() => _loadingPatients = false);
    }
  }

  // =======================================================================
  // CANCELLED APPOINTMENTS SUBSCRIPTION
  // After a member cancels, their `userId` field is nulled but
  // `previousUserId` is preserved on the request doc. We query that
  // field so the Past tab can show "Cancelled by you" entries for
  // historical context. No retry logic here — this is a "nice to have"
  // stream, not critical path.
  // =======================================================================

  void _subscribeToCancelledAppointments() {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return;

    _cancelledSub?.cancel();
    _cancelledSub = FirebaseFirestore.instance
        .collection('requests')
        .where('previousUserId', isEqualTo: user.uid)
        .snapshots()
        .listen(
      (snap) {
        if (!mounted) return;
        final items = <_Appointment>[];
        for (final doc in snap.docs) {
          try {
            // Parse with userId spoofed to current user so the factory
            // builds a complete object. We treat status as cancelled
            // regardless of current status field.
            final data = Map<String, dynamic>.from(doc.data());
            data['userId'] = user.uid; // for downstream consumers
            data['status'] = 'cancelled';
            items.add(_Appointment.fromFirestore(doc.id, data));
          } catch (e) {
            _logError('skipped malformed cancelled request ${doc.id}', e);
          }
        }
        items.sort((a, b) => b.startAt.compareTo(a.startAt));
        setState(() {
          _cancelledAppointments = items;
        });
      },
      onError: (err) {
        // Don't surface as a UI error — cancelled list is supplementary.
        _logError('cancelled appointments stream failed', err);
      },
      cancelOnError: false,
    );
  }

  // =======================================================================
  // VISIT RECORDS SUBSCRIPTION
  // Same pattern as appointments.
  // =======================================================================

  void _subscribeToVisitRecords() {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      setState(() {
        _loadingVisits = false;
        _visitsError = 'Sign in to view your visit history.';
      });
      return;
    }

    _visitsSub?.cancel();
    _visitsSub = FirebaseFirestore.instance
        .collection('users')
        .doc(user.uid)
        .collection('visit_records')
        .orderBy('visitDate', descending: true)
        .snapshots()
        .listen(
      (snap) {
        if (!mounted) return;
        final records = <_VisitRecord>[];
        for (final doc in snap.docs) {
          try {
            records.add(_VisitRecord.fromFirestore(doc.id, doc.data()));
          } catch (e) {
            _logError('skipped malformed visit_record ${doc.id}', e);
          }
        }
        setState(() {
          _visitRecords = records;
          _loadingVisits = false;
          _visitsError = null;
          _visitsRetries = 0;
        });
      },
      onError: (err) {
        _logError('visit_records stream failed', err);
        if (!mounted) return;
        _handleVisitsError(err);
      },
      cancelOnError: false,
    );
  }

  void _handleVisitsError(Object err) {
    final kind = _classifyFirestoreError(err);
    if (kind == _FirestoreErrorKind.permissionDenied) {
      setState(() {
        _loadingVisits = false;
        _visitsError = _errorMessageForFirestore(kind);
      });
      return;
    }

    if (_visitsRetries < _maxRetries) {
      _visitsRetries++;
      final delay = Duration(seconds: [2, 5, 10][_visitsRetries - 1]);
      _log('retrying visit_records subscription in ${delay.inSeconds}s'
          ' (attempt $_visitsRetries)');
      Future.delayed(delay, () {
        if (!mounted) return;
        _subscribeToVisitRecords();
      });
    } else {
      setState(() {
        _loadingVisits = false;
        _visitsError = _errorMessageForFirestore(kind);
      });
    }
  }

  // =======================================================================
  // TIMELINE MERGE
  // Pulls from multiple source collections and merges into a unified
  // chronological feed. Uses one-shot .get() queries rather than
  // listeners — real-time sync across N collections is expensive and
  // not worth it for a timeline that changes slowly.
  //
  // Collections queried:
  //   requests            → CareEventKind.appointment / .visitRecord
  //   visit_records       → CareEventKind.visitRecord
  //   prescriptions       → CareEventKind.prescription (new Rx)
  //   prescriptionRefills → CareEventKind.prescription (in-app refills)
  //   refills             → CareEventKind.prescription (request-flow refills)
  //   symptom_checks      → CareEventKind.symptomCheck
  //   claims              → CareEventKind.claim
  //
  // Each collection contributes its entries to a merged list, then the
  // list is sorted reverse-chronologically and capped at 200 most
  // recent entries for render performance.
  // =======================================================================

  Future<void> _loadTimeline() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      if (!mounted) return;
      setState(() {
        _loadingTimeline = false;
        _timelineError = 'Sign in to view your timeline.';
      });
      return;
    }

    if (!mounted) return;
    setState(() {
      if (_timeline.isEmpty) {
        // Only show loading state on first load
        _loadingTimeline = true;
      }
      _timelineError = null;
    });

    try {
      final events = <_CareEvent>[];
      final userRef =
          FirebaseFirestore.instance.collection('users').doc(user.uid);

      // --- Appointments (requests collection) → timeline events ---
      try {
        final apptSnap = await FirebaseFirestore.instance
            .collection('requests')
            .where('userId', isEqualTo: user.uid)
            .limit(80)
            .get();
        for (final doc in apptSnap.docs) {
          try {
            final appt = _Appointment.fromFirestore(doc.id, doc.data());
            // We only add an appointment to timeline if it hasn't been
            // "superseded" by a linked visit record — otherwise the
            // visit record entry is richer. If no linked visit record,
            // the appointment stands on its own.
            if (appt.linkedVisitRecordId == null) {
              events.add(_CareEvent(
                id: 'appt_${doc.id}',
                timestamp: appt.startAt,
                kind: CareEventKind.appointment,
                title: appt.status == AppointmentStatus.completed
                    ? 'Visit with ${appt.providerDisplay}'
                    : '${_apptStatusLabel(appt.status)}: '
                        '${_apptTypeLabel(appt.type)}',
                subtitle: _appointmentSubtitle(appt),
                detail: appt.reason,
                accent: _eventKindColor(CareEventKind.appointment),
                icon: _apptTypeIcon(appt.type),
                sourceCollection: 'requests',
                sourceDocId: doc.id,
                payload: appt,
              ));
            }
          } catch (e) {
            _logError('timeline: skipped appt ${doc.id}', e);
          }
        }
      } catch (e) {
        _logError('timeline: requests query failed', e);
      }

      // --- Visit records → timeline events ---
      try {
        final visitSnap = await userRef
            .collection('visit_records')
            .orderBy('visitDate', descending: true)
            .limit(80)
            .get();
        for (final doc in visitSnap.docs) {
          try {
            final v = _VisitRecord.fromFirestore(doc.id, doc.data());
            final primaryDx = v.primaryDiagnosisLabel;
            events.add(_CareEvent(
              id: 'visit_${doc.id}',
              timestamp: v.visitDate,
              kind: CareEventKind.visitRecord,
              title: 'Visit with ${v.providerDisplay}',
              subtitle: v.clinicName,
              detail: primaryDx ?? v.chiefComplaint ?? _apptTypeLabel(v.type),
              accent: _eventKindColor(CareEventKind.visitRecord),
              icon: _eventKindIcon(CareEventKind.visitRecord),
              sourceCollection: 'visit_records',
              sourceDocId: doc.id,
              payload: v,
            ));
          } catch (e) {
            _logError('timeline: skipped visit_record ${doc.id}', e);
          }
        }
      } catch (e) {
        _logError('timeline: visit_records query failed', e);
      }

      // --- Prescriptions → timeline events ---
      // Two separate queries to match the actual prescription schema:
      //   1. prescriptions    (top-level) — original Rx records with
      //      createdAt / medicationName / prescribedBy fields. Written by
      //      clinic-side tools. Each doc = one prescription creation event.
      //   2. prescriptionRefills (top-level) — refill request events
      //      written by jovi_prescription_refills.dart when a member
      //      taps "Request refill". Each doc = one refill event.
      //
      // Both filter on userId and appear in the timeline as separate
      // events ("New prescription" vs "Refill requested").
      try {
        final rxSnap = await FirebaseFirestore.instance
            .collection('prescriptions')
            .where('userId', isEqualTo: user.uid)
            .limit(50)
            .get();
        for (final doc in rxSnap.docs) {
          try {
            final data = doc.data();
            final ts = data['createdAt'];
            DateTime when;
            if (ts is Timestamp) {
              when = ts.toDate();
            } else if (ts is String) {
              when = DateTime.tryParse(ts) ?? DateTime.now();
            } else {
              // Fall back to lastRefilled or nextRefillDate if no createdAt
              final last = data['lastRefilled'];
              if (last is Timestamp) {
                when = last.toDate();
              } else {
                continue;
              }
            }
            // Build _Prescription from the real schema field names.
            final rx = _Prescription.fromMap({
              'medicationName': data['medicationName'],
              'dosage': data['dosage'] ?? data['strength'],
              'frequency': data['frequency'],
              'refillsRemaining': data['refillsRemaining'],
              'prescriber': data['prescribedBy'],
              'pharmacy':
                  data['lastFilledPharmacy'] ?? data['originalPharmacy'],
              'instructions': data['instructions'],
              'status': data['status'],
              'prescribedAt': data['createdAt'],
              'filledAt': data['lastRefilled'],
            });
            events.add(_CareEvent(
              id: 'rx_${doc.id}',
              timestamp: when,
              kind: CareEventKind.prescription,
              title: 'New prescription: ${rx.medicationName}',
              subtitle: rx.prescriber,
              detail: rx.summary,
              accent: _eventKindColor(CareEventKind.prescription),
              icon: _eventKindIcon(CareEventKind.prescription),
              sourceCollection: 'prescriptions',
              sourceDocId: doc.id,
              payload: rx,
            ));
          } catch (e) {
            _logError('timeline: skipped prescription ${doc.id}', e);
          }
        }
      } catch (e) {
        // May legitimately be empty for new users.
        _log('timeline: prescriptions query returned no data or failed: $e');
      }

      // Refill events
      try {
        final refillSnap = await FirebaseFirestore.instance
            .collection('prescriptionRefills')
            .where('userId', isEqualTo: user.uid)
            .limit(50)
            .get();
        for (final doc in refillSnap.docs) {
          try {
            final data = doc.data();
            // Prefer refillDate, fall back to requestedDate / createdAt
            DateTime? when;
            for (final field in ['refillDate', 'requestedDate', 'createdAt']) {
              final v = data[field];
              if (v is Timestamp) {
                when = v.toDate();
                break;
              }
              if (v is String) {
                final d = DateTime.tryParse(v);
                if (d != null) {
                  when = d;
                  break;
                }
              }
            }
            if (when == null) continue;

            final medName = data['medicationName'] as String? ?? 'Prescription';
            final pharmacy = data['pharmacyName'] as String?;
            final status = data['status'] as String? ?? 'requested';
            final refillNumber = data['refillNumber'];

            String title = 'Refill requested: $medName';
            if (status.toLowerCase() == 'filled' ||
                status.toLowerCase() == 'completed') {
              title = 'Refill filled: $medName';
            } else if (status.toLowerCase() == 'ready') {
              title = 'Refill ready: $medName';
            }

            final detailParts = <String>[];
            if (refillNumber is num) {
              detailParts.add('Refill #${refillNumber.toInt()}');
            }
            if (pharmacy != null && pharmacy.isNotEmpty) {
              detailParts.add(pharmacy);
            }

            events.add(_CareEvent(
              id: 'refill_${doc.id}',
              timestamp: when,
              kind: CareEventKind.prescription,
              title: title,
              subtitle: pharmacy,
              detail: detailParts.isEmpty ? null : detailParts.join(' • '),
              accent: _eventKindColor(CareEventKind.prescription),
              icon: Icons.refresh_rounded,
              sourceCollection: 'prescriptionRefills',
              sourceDocId: doc.id,
              payload: null,
            ));
          } catch (e) {
            _logError('timeline: skipped refill ${doc.id}', e);
          }
        }
      } catch (e) {
        _log(
            'timeline: prescriptionRefills query returned no data or failed: $e');
      }

      // --- Request-based refills (refills collection) → timeline events ---
      // This is a DIFFERENT refill flow than prescriptionRefills above.
      // When a member uses the Request Care widget and selects visit type
      // "refill", jovi_requests_flow.dart writes to the top-level `refills`
      // collection (NOT prescriptionRefills). Schema from that widget:
      //   userId, patientName, medicationType, medicationName,
      //   currentMedications, allergies, primaryPhysician, status ('pending'),
      //   type ('refill'), createdAt (server timestamp)
      //
      // These are requests to a provider for new or continued medication
      // — they belong on the timeline as a distinct event type so the
      // member can see the full refill history regardless of which widget
      // submitted the request.
      try {
        final reqRefillSnap = await FirebaseFirestore.instance
            .collection('refills')
            .where('userId', isEqualTo: user.uid)
            .limit(50)
            .get();
        for (final doc in reqRefillSnap.docs) {
          try {
            final data = doc.data();
            final ts = data['createdAt'];
            DateTime when;
            if (ts is Timestamp) {
              when = ts.toDate();
            } else if (ts is String) {
              final d = DateTime.tryParse(ts);
              if (d == null) continue;
              when = d;
            } else {
              continue;
            }

            final medName = (data['medicationName'] as String?)?.trim() ??
                (data['medicationType'] as String?)?.trim() ??
                'medication';
            final status =
                (data['status'] as String? ?? 'pending').toLowerCase();

            String title;
            switch (status) {
              case 'approved':
              case 'filled':
              case 'completed':
                title = 'Refill approved: $medName';
                break;
              case 'denied':
              case 'rejected':
                title = 'Refill denied: $medName';
                break;
              case 'pending':
              default:
                title = 'Refill requested: $medName';
            }

            final physician = data['primaryPhysician'] as String?;
            final patient = data['patientName'] as String?;

            events.add(_CareEvent(
              id: 'reqrefill_${doc.id}',
              timestamp: when,
              kind: CareEventKind.prescription,
              title: title,
              subtitle: (physician != null && physician.isNotEmpty)
                  ? physician
                  : null,
              detail: (patient != null && patient.isNotEmpty)
                  ? 'For: $patient'
                  : null,
              accent: _eventKindColor(CareEventKind.prescription),
              icon: Icons.medication_outlined,
              sourceCollection: 'refills',
              sourceDocId: doc.id,
              payload: null,
            ));
          } catch (e) {
            _logError('timeline: skipped request-refill ${doc.id}', e);
          }
        }
      } catch (e) {
        _log('timeline: refills query returned no data or failed: $e');
      }

      // --- Symptom checks → timeline events ---
      try {
        final symSnap = await userRef
            .collection('symptom_checks')
            .orderBy('createdAt', descending: true)
            .limit(30)
            .get();
        for (final doc in symSnap.docs) {
          try {
            final data = doc.data();
            final ts = data['createdAt'];
            DateTime when;
            if (ts is Timestamp) {
              when = ts.toDate();
            } else if (ts is String) {
              when = DateTime.tryParse(ts) ?? DateTime.now();
            } else {
              continue;
            }
            final summary = (data['summary'] as String?) ?? 'Symptom check';
            final tierRaw = data['finalTier'] as String?;
            final redFlagged = data['redFlagged'] == true;
            events.add(_CareEvent(
              id: 'sym_${doc.id}',
              timestamp: when,
              kind: CareEventKind.symptomCheck,
              title: redFlagged ? 'Symptom check (flagged)' : 'Symptom check',
              subtitle: tierRaw != null
                  ? 'Recommendation: ${_humanizeTier(tierRaw)}'
                  : null,
              detail: summary,
              accent: redFlagged
                  ? _joviErrorRed
                  : _eventKindColor(CareEventKind.symptomCheck),
              icon: _eventKindIcon(CareEventKind.symptomCheck),
              sourceCollection: 'symptom_checks',
              sourceDocId: doc.id,
              payload: null,
            ));
          } catch (e) {
            _logError('timeline: skipped symptom_check ${doc.id}', e);
          }
        }
      } catch (e) {
        _log('timeline: symptom_checks query returned no data or failed: $e');
      }

      // --- Claims → timeline events ---
      // Real schema from jovi_file_claim.dart: users/{uid}/claims
      //   type: 'receipt' | 'claim'  (pay-me-back vs pay-the-provider)
      //   amount: int (cents? dollars as whole? — stored as int)
      //   date: Timestamp (service date, user-entered)
      //   submittedAt: Timestamp (server-side submission time)
      //   status: 'Pending' | 'Processing' | ...
      //   provider: String (for type=='claim')
      //   reason: String (for type=='claim')
      // We DON'T use orderBy on the query because the fallback field
      // hierarchy is submittedAt → date → createdAt, and a composite
      // ordered index isn't worth requiring.
      try {
        final claimSnap = await userRef.collection('claims').limit(30).get();
        for (final doc in claimSnap.docs) {
          try {
            final data = doc.data();
            // Prefer submittedAt, fall back to date, then createdAt
            DateTime? when;
            for (final field in ['submittedAt', 'date', 'createdAt']) {
              final v = data[field];
              if (v is Timestamp) {
                when = v.toDate();
                break;
              }
              if (v is String) {
                final d = DateTime.tryParse(v);
                if (d != null) {
                  when = d;
                  break;
                }
              }
            }
            if (when == null) continue;

            final status = data['status'] as String? ?? 'Pending';
            final type = (data['type'] as String? ?? 'claim').toLowerCase();
            final provider = data['provider'] as String?;
            final reason = data['reason'] as String?;
            final amount = data['amount'];

            // Build a descriptive title based on claim type
            String title;
            if (type == 'receipt') {
              title = 'Receipt submitted';
            } else {
              title = 'Claim ${_humanizeClaimStatus(status)}';
            }

            // Build detail: "$XX.XX — Reason" or just amount or just reason
            String? detail;
            final parts = <String>[];
            if (amount is num) {
              // Claim schema stores amount as integer dollars, not cents.
              parts.add('\$${amount.toInt()}');
            }
            if (reason != null && reason.isNotEmpty) {
              parts.add(reason);
            }
            if (parts.isNotEmpty) {
              detail = parts.join(' • ');
            }

            events.add(_CareEvent(
              id: 'claim_${doc.id}',
              timestamp: when,
              kind: CareEventKind.claim,
              title: title,
              subtitle: provider,
              detail: detail,
              accent: _eventKindColor(CareEventKind.claim),
              icon: type == 'receipt'
                  ? Icons.receipt_rounded
                  : _eventKindIcon(CareEventKind.claim),
              sourceCollection: 'claims',
              sourceDocId: doc.id,
              payload: null,
            ));
          } catch (e) {
            _logError('timeline: skipped claim ${doc.id}', e);
          }
        }
      } catch (e) {
        _log('timeline: claims query returned no data or failed: $e');
      }

      // --- Sort reverse-chronologically and cap ---
      events.sort((a, b) => b.timestamp.compareTo(a.timestamp));
      final capped = events.length > 200 ? events.sublist(0, 200) : events;

      if (!mounted) return;
      setState(() {
        _timeline = capped;
        _loadingTimeline = false;
        _timelineError = null;
      });
      _log('timeline loaded: ${capped.length} events');
    } catch (e) {
      _logError('timeline load failed', e);
      if (!mounted) return;
      setState(() {
        _loadingTimeline = false;
        if (_timeline.isEmpty) {
          _timelineError = _errorMessageForFirestore(
            _classifyFirestoreError(e),
          );
        }
        // If we have stale data, keep showing it rather than blanking.
      });
    }
  }

  /// Public pull-to-refresh handler for the timeline tab.
  Future<void> _refreshTimeline() async {
    HapticFeedback.lightImpact();
    await _loadTimeline();
  }

  /// Pull-to-refresh for appointments — re-subscribes to force a fresh
  /// snapshot even if the stream was in a retry backoff.
  Future<void> _refreshAppointments() async {
    HapticFeedback.lightImpact();
    _appointmentsRetries = 0;
    _subscribeToAppointments();
    // Give Firestore a moment to return fresh data before completing the
    // refresh indicator animation.
    await Future.delayed(const Duration(milliseconds: 500));
  }

  /// Pull-to-refresh for visits.
  Future<void> _refreshVisits() async {
    HapticFeedback.lightImpact();
    _visitsRetries = 0;
    _subscribeToVisitRecords();
    await Future.delayed(const Duration(milliseconds: 500));
  }

  // =======================================================================
  // TIMELINE HELPERS
  // Humanization for field values that come from other widgets'
  // schemas — kept here rather than in _CareEvent to avoid coupling
  // the timeline merger to those other widgets' enums.
  // =======================================================================

  String _humanizeTier(String raw) {
    switch (raw.toLowerCase()) {
      case 'emergency':
        return 'Emergency care';
      case 'urgent':
        return 'Urgent care';
      case 'routine':
        return 'Routine care';
      case 'selfcare':
      case 'self_care':
        return 'Self-care';
      default:
        return raw;
    }
  }

  String _humanizeClaimStatus(String raw) {
    switch (raw.toLowerCase()) {
      case 'submitted':
        return 'submitted';
      case 'pending':
        return 'pending review';
      case 'approved':
        return 'approved';
      case 'denied':
      case 'rejected':
        return 'denied';
      case 'paid':
        return 'paid';
      default:
        return raw;
    }
  }

  /// Builds the subtitle line shown under an appointment title in the
  /// timeline. Combines type + clinic name with a bullet separator.
  String? _appointmentSubtitle(_Appointment a) {
    final parts = <String>[];
    if (a.type != AppointmentType.other) {
      parts.add(_apptTypeLabel(a.type));
    }
    if (a.clinicName != null && a.clinicName!.isNotEmpty) {
      parts.add(a.clinicName!);
    }
    if (parts.isEmpty) return null;
    return parts.join(' • ');
  }

  // =======================================================================
  // COUNTS / DERIVED STATE (used by tab badges)
  // =======================================================================

  /// Count of upcoming appointments for the badge on the Upcoming tab.
  /// Reflects the active patient filter.
  int get _upcomingCount => _filteredUpcoming.length;

  /// Count of past completed visits for the badge on the Past tab.
  /// Doesn't count cancelled or no-show appointments.
  /// Reflects the active patient filter.
  int get _pastCount {
    final visits = _filteredVisitRecords;
    final past = _filteredPast;
    int n = visits.length;
    // Also count past appointments that don't have a linked visit record
    // (so they're orphan but still visible in history).
    for (final a in past) {
      if (a.status == AppointmentStatus.completed &&
          a.linkedVisitRecordId == null) {
        // check if a visit_record with this appointmentId exists
        final matched = visits.any((v) => v.appointmentId == a.id);
        if (!matched) n++;
      }
    }
    return n;
  }

  // =======================================================================
  // PATIENT FILTER — APPLIED DATA GETTERS
  //
  // All view builders should read from these getters instead of the raw
  // _upcomingAppointments / _pastAppointments / _visitRecords / _timeline
  // lists so the family-member filter applies uniformly.
  //
  // When _selectedPatientFilter is null, "Everyone" is active and the
  // filter is a no-op. When it's set to a specific name, only records
  // whose patientName field matches (case-insensitive exact) are kept.
  //
  // Legacy records written before patientName was added will have a
  // null patientName. To avoid hiding them entirely from the default-
  // view, we treat null-patient records as matching the primary user
  // (since those are almost certainly the account holder's own visits
  // from before multi-patient support existed).
  // =======================================================================

  /// True if a non-default filter is active.
  bool get _patientFilterActive => _selectedPatientFilter != null;

  /// The primary user's display name (first entry of _patientNames), or
  /// null if patient list isn't loaded yet.
  String? get _primaryPatientName =>
      _patientNames.isNotEmpty ? _patientNames.first : null;

  /// True if this record matches the currently-selected patient filter.
  bool _matchesPatientFilter(String? recordPatientName) {
    if (_selectedPatientFilter == null) return true;
    if (recordPatientName == null || recordPatientName.isEmpty) {
      // Legacy null → treat as primary user's record
      return _selectedPatientFilter == _primaryPatientName;
    }
    return recordPatientName.toLowerCase() ==
        _selectedPatientFilter!.toLowerCase();
  }

  List<_Appointment> get _filteredUpcoming {
    final base = _upcomingAppointments
        .where((a) => _matchesPatientFilter(a.patientName));
    if (!_searchActiveNonEmpty) return base.toList();
    return base
        .where((a) => _matchesSearch(_searchBlobForAppointment(a)))
        .toList();
  }

  List<_Appointment> get _filteredPast {
    final base =
        _pastAppointments.where((a) => _matchesPatientFilter(a.patientName));
    if (!_searchActiveNonEmpty) return base.toList();
    return base
        .where((a) => _matchesSearch(_searchBlobForAppointment(a)))
        .toList();
  }

  List<_Appointment> get _filteredCancelled {
    final base = _cancelledAppointments
        .where((a) => _matchesPatientFilter(a.patientName));
    if (!_searchActiveNonEmpty) return base.toList();
    return base
        .where((a) => _matchesSearch(_searchBlobForAppointment(a)))
        .toList();
  }

  List<_VisitRecord> get _filteredVisitRecords {
    final base =
        _visitRecords.where((v) => _matchesPatientFilter(v.patientName));
    if (!_searchActiveNonEmpty) return base.toList();
    return base
        .where((v) => _matchesSearch(_searchBlobForVisitRecord(v)))
        .toList();
  }

  /// Timeline filter: events whose payload is an _Appointment or
  /// _VisitRecord are filtered on patientName. Events with other
  /// payloads (prescriptions, claims, symptom checks) currently have
  /// no patient attribution and are always shown — they're member-level
  /// events regardless of which family member they relate to.
  ///
  /// Search, when active, applies on top of the patient filter.
  List<_CareEvent> get _filteredTimeline {
    Iterable<_CareEvent> base = _timeline;
    if (_selectedPatientFilter != null) {
      base = base.where((e) {
        final p = e.payload;
        if (p is _Appointment) {
          return _matchesPatientFilter(p.patientName);
        }
        if (p is _VisitRecord) {
          return _matchesPatientFilter(p.patientName);
        }
        return true; // keep member-level events when filtering
      });
    }
    if (_searchActiveNonEmpty) {
      base = base.where((e) => _matchesSearch(_searchBlobForEvent(e)));
    }
    return base.toList();
  }

  /// True if a non-empty search query is active.
  bool get _searchActiveNonEmpty =>
      _searchActive && _searchQuery.trim().isNotEmpty;

  /// Lowercased query tokens for fast matching. Multi-word queries match
  /// when ALL tokens appear somewhere in the haystack (logical AND).
  List<String> get _searchTokens {
    if (!_searchActiveNonEmpty) return const [];
    return _searchQuery
        .toLowerCase()
        .split(RegExp(r'\s+'))
        .where((t) => t.isNotEmpty)
        .toList();
  }

  /// Returns true if [haystack] (a space-joined composite of fields)
  /// contains every token in [_searchTokens]. Case-insensitive.
  bool _matchesSearch(String haystack) {
    final tokens = _searchTokens;
    if (tokens.isEmpty) return true;
    final normalized = haystack.toLowerCase();
    for (final t in tokens) {
      if (!normalized.contains(t)) return false;
    }
    return true;
  }

  /// Build the searchable text blob for an appointment.
  String _searchBlobForAppointment(_Appointment a) {
    return [
      _apptTypeLabel(a.type),
      _apptStatusLabel(a.status),
      a.providerName ?? '',
      a.providerCredentials ?? '',
      a.clinicName ?? '',
      a.clinicAddress ?? '',
      a.reason ?? '',
      a.notes ?? '',
      a.patientName ?? '',
      a.cancelledReason ?? '',
    ].join(' ');
  }

  /// Build the searchable text blob for a visit record — includes
  /// diagnoses, prescriptions, and other clinical content so members
  /// can find visits by what was discussed.
  String _searchBlobForVisitRecord(_VisitRecord v) {
    final parts = <String>[
      _apptTypeLabel(v.type),
      v.providerName ?? '',
      v.providerCredentials ?? '',
      v.clinicName ?? '',
      v.chiefComplaint ?? '',
      v.historyOfPresentIllness ?? '',
      v.clinicalNotes ?? '',
      v.patientEducation ?? '',
      v.patientName ?? '',
    ];
    for (final d in v.diagnoses) {
      parts.add(d.label);
      if (d.icdCode != null) parts.add(d.icdCode!);
      if (d.notes != null) parts.add(d.notes!);
    }
    for (final rx in v.prescriptions) {
      parts.add(rx.medicationName);
      if (rx.reason != null) parts.add(rx.reason!);
      if (rx.instructions != null) parts.add(rx.instructions!);
    }
    for (final l in v.labOrders) {
      parts.add(l.name);
      if (l.category != null) parts.add(l.category!);
      if (l.resultSummary != null) parts.add(l.resultSummary!);
    }
    for (final p in v.procedures) {
      parts.add(p.name);
      if (p.bodyLocation != null) parts.add(p.bodyLocation!);
      if (p.cptCode != null) parts.add(p.cptCode!);
    }
    if (v.followUp != null) {
      if (v.followUp!.summary != null) parts.add(v.followUp!.summary!);
      if (v.followUp!.patientInstructions != null) {
        parts.add(v.followUp!.patientInstructions!);
      }
      parts.addAll(v.followUp!.redFlags);
    }
    return parts.join(' ');
  }

  /// Build the searchable text blob for a timeline event. Falls back
  /// to the payload's richer blob if available.
  String _searchBlobForEvent(_CareEvent e) {
    final parts = <String>[
      e.title,
      e.subtitle ?? '',
      e.detail ?? '',
      _eventKindLabel(e.kind),
    ];
    final p = e.payload;
    if (p is _Appointment) {
      parts.add(_searchBlobForAppointment(p));
    } else if (p is _VisitRecord) {
      parts.add(_searchBlobForVisitRecord(p));
    } else if (p is _Prescription) {
      parts.add(p.medicationName);
      if (p.prescriber != null) parts.add(p.prescriber!);
      if (p.pharmacy != null) parts.add(p.pharmacy!);
      if (p.reason != null) parts.add(p.reason!);
    }
    return parts.join(' ');
  }

  // =======================================================================
  // SHARED UI HELPERS
  // Glass panels, pills, etc. Used across all tabs.
  // =======================================================================

  /// Small glass surface with blur. Use inside padding.
  Widget _glassCard({
    required Widget child,
    double bgOpacity = 0.08,
    double borderOpacity = 0.15,
    double borderWidth = 1.2,
    EdgeInsetsGeometry? padding,
    double borderRadius = 20,
    Color? borderTint,
  }) {
    // Painted glass: cards sit in ListViews over an opaque navy gradient.
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

  /// Compact colored label pill used for status badges.
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
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
          color: color.withOpacity(0.4),
          width: 0.8,
        ),
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
              fontWeight: FontWeight.w800,
              letterSpacing: 0.2,
            ),
          ),
        ],
      ),
    );
  }

  // =======================================================================
  // MAIN BUILD + APP BAR + TAB BAR
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
          width: widget.width,
          height: widget.height,
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
                _buildTabBar(),
                // Patient filter chips — only shown when the account has
                // more than one patient name (primary + at least one dep).
                // Single-patient accounts don't see it, keeping the UI
                // focused for the most common case.
                if (_patientNames.length > 1) _buildPatientFilterBar(),
                Expanded(
                  child: FadeTransition(
                    opacity: _fadeAnim,
                    child: _routeTab(),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // ---------------------------------------------------------------------
  // APP BAR
  // ---------------------------------------------------------------------

  Widget _buildAppBar() {
    // When search mode is active, render the search input variant instead
    // of the normal title row. Avoids stacking two rows which would
    // cramp the layout.
    if (_searchActive) return _buildSearchAppBar();
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 10, 14, 4),
      child: Row(
        children: [
          // Back button
          _PressableMaterial(
            child: InkWell(
              onTap: () {
                HapticFeedback.lightImpact();
                if (Navigator.of(context).canPop()) {
                  Navigator.of(context).pop();
                } else {
                  try {
                    context.pushReplacement('/dashboard');
                  } catch (_) {
                    // If the app doesn't have /dashboard, no-op gracefully.
                    _log('back pressed but no parent route');
                  }
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
          // Title block
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'Care Records',
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
                  _appBarSubtitle(),
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
          // Search icon — opens search-mode app bar
          _PressableMaterial(
            child: InkWell(
              onTap: _activateSearch,
              borderRadius: BorderRadius.circular(13),
              child: Tooltip(
                message: 'Search',
                child: Semantics(
                  label: 'Search records',
                  button: true,
                  child: Container(
                    width: 44,
                    height: 44,
                    margin: const EdgeInsets.only(right: 6),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.06),
                      borderRadius: BorderRadius.circular(13),
                      border: Border.all(
                        color: Colors.white.withOpacity(0.14),
                        width: 1,
                      ),
                    ),
                    child: Icon(
                      Icons.search_rounded,
                      color: Colors.white.withOpacity(0.75),
                      size: 17,
                    ),
                  ),
                ),
              ),
            ),
          ),
          // Help icon — always visible, explains the three tabs
          _PressableMaterial(
            child: InkWell(
              onTap: _showHelpSheet,
              borderRadius: BorderRadius.circular(13),
              child: Tooltip(
                message: 'How this works',
                child: Semantics(
                  label: 'Help',
                  button: true,
                  child: Container(
                    width: 44,
                    height: 44,
                    margin: EdgeInsets.only(
                      right: _currentTab != _Tab.timeline ? 8 : 0,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.06),
                      borderRadius: BorderRadius.circular(13),
                      border: Border.all(
                        color: Colors.white.withOpacity(0.14),
                        width: 1,
                      ),
                    ),
                    child: Icon(
                      Icons.help_outline_rounded,
                      color: Colors.white.withOpacity(0.75),
                      size: 17,
                    ),
                  ),
                ),
              ),
            ),
          ),
          // Book new appointment CTA — only shown on upcoming/past tabs
          // where the "book one" action is relevant. On timeline tab it
          // would feel out of place.
          if (_currentTab != _Tab.timeline)
            _PressableMaterial(
              child: InkWell(
                onTap: _openRequestCare,
                borderRadius: BorderRadius.circular(13),
                child: Tooltip(
                  message: 'Book new visit',
                  child: Semantics(
                    label: 'Book new appointment',
                    button: true,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 12, vertical: 9),
                      decoration: BoxDecoration(
                        color: _joviCoral.withOpacity(0.14),
                        borderRadius: BorderRadius.circular(13),
                        border: Border.all(
                          color: _joviCoral.withOpacity(0.3),
                          width: 0.8,
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(
                            Icons.add_rounded,
                            color: _joviCoral,
                            size: 16,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            'Book',
                            style: TextStyle(
                              color: _joviCoral,
                              fontSize: 12,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 0.2,
                            ),
                          ),
                        ],
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

  // =======================================================================
  // SEARCH APP BAR
  // Replaces the normal app bar when search mode is active. Shows a
  // close button, text field focused on entry, and a clear button
  // when the query is non-empty.
  // =======================================================================

  Widget _buildSearchAppBar() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 10, 14, 4),
      child: Row(
        children: [
          // Exit-search button (reuses the back-button chrome)
          _PressableMaterial(
            child: InkWell(
              onTap: _deactivateSearch,
              borderRadius: BorderRadius.circular(13),
              child: Tooltip(
                message: 'Exit search',
                child: Semantics(
                  label: 'Exit search',
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
          const SizedBox(width: 10),
          Expanded(
            child: Container(
              height: 44,
              padding: const EdgeInsets.symmetric(horizontal: 12),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.06),
                borderRadius: BorderRadius.circular(13),
                border: Border.all(
                  color: Colors.white.withOpacity(0.14),
                  width: 1,
                ),
              ),
              child: Row(
                children: [
                  Icon(
                    Icons.search_rounded,
                    color: Colors.white.withOpacity(0.55),
                    size: 17,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Semantics(
                      label: 'Search records',
                      textField: true,
                      child: TextField(
                        controller: _searchCtrl,
                        focusNode: _searchFocus,
                        autofocus: true,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                        ),
                        cursorColor: _joviCoral,
                        textInputAction: TextInputAction.search,
                        decoration: InputDecoration(
                          hintText: _searchHintForTab(),
                          hintStyle: TextStyle(
                            color: Colors.white.withOpacity(0.4),
                            fontSize: 14,
                            fontWeight: FontWeight.w500,
                          ),
                          border: InputBorder.none,
                          isCollapsed: true,
                          contentPadding:
                              const EdgeInsets.symmetric(vertical: 12),
                        ),
                        onChanged: (v) {
                          setState(() => _searchQuery = v);
                        },
                        onSubmitted: (_) {
                          _analytics('care_records_search_submitted', {
                            'tab': _tabSerialize(_currentTab),
                            'tokens': _searchTokens.length.toString(),
                          });
                        },
                      ),
                    ),
                  ),
                  if (_searchQuery.isNotEmpty)
                    _PressableMaterial(
                      child: InkWell(
                        onTap: () {
                          HapticFeedback.selectionClick();
                          _searchCtrl.clear();
                          setState(() => _searchQuery = '');
                          _searchFocus.requestFocus();
                        },
                        borderRadius: BorderRadius.circular(8),
                        child: Tooltip(
                          message: 'Clear',
                          child: Semantics(
                            label: 'Clear search',
                            button: true,
                            child: Padding(
                              padding: const EdgeInsets.all(6),
                              child: Icon(
                                Icons.close_rounded,
                                color: Colors.white.withOpacity(0.6),
                                size: 16,
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  /// Contextual hint text that tells the user what search covers in the
  /// active tab. Members scan for these cues when deciding what to type.
  String _searchHintForTab() {
    switch (_currentTab) {
      case _Tab.upcoming:
        return 'Search by provider, clinic, or reason';
      case _Tab.past:
        return 'Search by diagnosis, Rx, or provider';
      case _Tab.timeline:
        return 'Search everything';
    }
  }

  void _activateSearch() {
    HapticFeedback.lightImpact();
    setState(() {
      _searchActive = true;
    });
    _analytics(
        'care_records_search_opened', {'tab': _tabSerialize(_currentTab)});
    // Focus request happens automatically via autofocus on the TextField
  }

  void _deactivateSearch() {
    HapticFeedback.selectionClick();
    _searchCtrl.clear();
    _searchFocus.unfocus();
    setState(() {
      _searchActive = false;
      _searchQuery = '';
    });
  }

  /// Dynamic subtitle that reflects the current tab and data state.
  String _appBarSubtitle() {
    switch (_currentTab) {
      case _Tab.upcoming:
        if (_loadingAppointments) return 'Loading your appointments…';
        final up = _filteredUpcoming;
        if (up.isEmpty) {
          return _patientFilterActive
              ? 'No upcoming for $_selectedPatientFilter'
              : 'No upcoming appointments';
        }
        return '${up.length} upcoming';
      case _Tab.past:
        if (_loadingVisits || _loadingAppointments) {
          return 'Loading your visits…';
        }
        return 'Your visit history';
      case _Tab.timeline:
        if (_loadingTimeline && _timeline.isEmpty) {
          return 'Loading your timeline…';
        }
        return 'Everything, chronologically';
    }
  }

  /// Navigates to the Request Care widget.
  /// NOTE: context.pushNamed never throws on an unknown name at runtime, so
  /// only the FIRST route in each list is ever tried. Keep the real
  /// FlutterFlow name first.
  void _openRequestCare() {
    HapticFeedback.lightImpact();
    final routes = ['requests', 'Requests', 'RequestCare', 'requestCare'];
    for (final route in routes) {
      try {
        context.pushNamed(route);
        _log('navigated to $route');
        return;
      } catch (_) {
        continue;
      }
    }
    if (!mounted) return;
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast('Could not open Request Care.',
        accent: _joviErrorRed, icon: CupertinoIcons.exclamationmark_circle));
  }

  // =======================================================================
  // HELP SHEET
  // Opens a bottom sheet explaining what each tab does, so first-time
  // users don't have to guess at the difference between "Past" and
  // "Timeline." Also a good place to surface privacy notes.
  // =======================================================================

  Future<void> _showHelpSheet() async {
    HapticFeedback.lightImpact();
    _analytics('care_records_help_opened');
    if (!mounted) return;

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => DraggableScrollableSheet(
        initialChildSize: 0.75,
        maxChildSize: 0.9,
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
                    _joviNavy.withOpacity(0.98),
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
                  // Grab handle
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
                  Padding(
                    padding: const EdgeInsets.fromLTRB(20, 18, 20, 8),
                    child: Row(
                      children: [
                        Container(
                          width: 40,
                          height: 40,
                          decoration: BoxDecoration(
                            color: _joviCoral.withOpacity(0.16),
                            borderRadius: BorderRadius.circular(11),
                            border: Border.all(
                              color: _joviCoral.withOpacity(0.3),
                              width: 0.8,
                            ),
                          ),
                          child: const Icon(
                            Icons.help_outline_rounded,
                            color: _joviCoral,
                            size: 20,
                          ),
                        ),
                        const SizedBox(width: 12),
                        const Expanded(
                          child: Text(
                            'How Care Records Works',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 19,
                              fontWeight: FontWeight.w700,
                              letterSpacing: -0.5,
                            ),
                          ),
                        ),
                        _PressableMaterial(
                          child: InkWell(
                            onTap: () => Navigator.of(ctx).pop(),
                            borderRadius: BorderRadius.circular(11),
                            child: Tooltip(
                              message: 'Close',
                              child: Semantics(
                                label: 'Close help',
                                button: true,
                                child: Container(
                                  padding: const EdgeInsets.all(8),
                                  decoration: BoxDecoration(
                                    color: Colors.white.withOpacity(0.08),
                                    borderRadius: BorderRadius.circular(11),
                                    border: Border.all(
                                      color: Colors.white.withOpacity(0.14),
                                      width: 1,
                                    ),
                                  ),
                                  child: const Icon(
                                    Icons.close_rounded,
                                    color: Colors.white,
                                    size: 16,
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  // Scrollable content
                  Expanded(
                    child: SingleChildScrollView(
                      controller: scrollCtrl,
                      padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _buildHelpItem(
                            icon: Icons.event_available_rounded,
                            accent: _joviCoral,
                            title: 'Upcoming',
                            body:
                                'Visits you have coming up. Tap an appointment to get directions, call the clinic, join a telehealth visit, reschedule, or cancel.',
                          ),
                          _buildHelpItem(
                            icon: Icons.history_rounded,
                            accent: _joviCoral,
                            title: 'Past',
                            body:
                                'Your completed visits with full clinical detail — diagnoses, prescriptions, labs, procedures, and follow-up plans. Tap a visit to see the full record. Visits marked "Pending" are charting in progress.',
                          ),
                          _buildHelpItem(
                            icon: Icons.timeline_rounded,
                            accent: _joviCoral,
                            title: 'Timeline',
                            body:
                                'Everything in one chronological feed — appointments, visits, prescriptions, refill requests, symptom checks, and claims. Useful for catching up on what has happened recently.',
                          ),
                          const SizedBox(height: 12),
                          // Privacy note
                          _glassCard(
                            bgOpacity: 0.05,
                            borderOpacity: 0.1,
                            padding: const EdgeInsets.all(14),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Icon(
                                  Icons.lock_outline_rounded,
                                  color: _joviMintDark,
                                  size: 16,
                                ),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        'Your Records Are Private',
                                        style: TextStyle(
                                          color: _joviMintDark,
                                          fontSize: 12,
                                          fontWeight: FontWeight.w700,
                                          letterSpacing: -0.1,
                                        ),
                                      ),
                                      const SizedBox(height: 5),
                                      Text(
                                        'Only you and your providers can see these records. Jovi Health encrypts your data in transit and at rest.',
                                        style: TextStyle(
                                          color: Colors.white.withOpacity(0.75),
                                          fontSize: 12,
                                          fontWeight: FontWeight.w500,
                                          height: 1.45,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: 12),
                          // Support note
                          _glassCard(
                            bgOpacity: 0.05,
                            borderOpacity: 0.1,
                            padding: const EdgeInsets.all(14),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Icon(
                                  Icons.support_agent_rounded,
                                  color: _joviGold,
                                  size: 16,
                                ),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        'Questions About a Visit?',
                                        style: TextStyle(
                                          color: _joviGoldDark,
                                          fontSize: 12,
                                          fontWeight: FontWeight.w700,
                                          letterSpacing: -0.1,
                                        ),
                                      ),
                                      const SizedBox(height: 5),
                                      Text(
                                        'For medical questions, contact your provider directly. For billing or app issues, reach out to Jovi Health support from the Account menu.',
                                        style: TextStyle(
                                          color: Colors.white.withOpacity(0.75),
                                          fontSize: 12,
                                          fontWeight: FontWeight.w500,
                                          height: 1.45,
                                        ),
                                      ),
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
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHelpItem({
    required IconData icon,
    required Color accent,
    required String title,
    required String body,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: accent.withOpacity(0.14),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: accent.withOpacity(0.28),
                width: 0.8,
              ),
            ),
            child: Icon(icon, color: accent, size: 17),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 15,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -0.3,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  body,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.7),
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                    height: 1.5,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------
  // TAB BAR
  // ---------------------------------------------------------------------

  Widget _buildTabBar() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 10, 14, 10),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(14),
        child: RepaintBoundary(
          child: Container(
            padding: const EdgeInsets.all(4),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.06),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                color: Colors.white.withOpacity(0.1),
                width: 1,
              ),
            ),
            child: Row(
              children: [
                _buildTabButton(
                  _Tab.upcoming,
                  'Upcoming',
                  Icons.event_available_outlined,
                  Icons.event_available_rounded,
                  badge: _upcomingCount > 0 ? _upcomingCount : null,
                ),
                _buildTabButton(
                  _Tab.past,
                  'Past',
                  Icons.history_outlined,
                  Icons.history_rounded,
                ),
                _buildTabButton(
                  _Tab.timeline,
                  'Timeline',
                  Icons.timeline_outlined,
                  Icons.timeline_rounded,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // =======================================================================
  // PATIENT FILTER BAR
  // Horizontal scrolling chip row: [Everyone] [Primary] [Dep1] [Dep2]...
  // Visible only when the account manages 2+ patients.
  // =======================================================================

  Widget _buildPatientFilterBar() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 0, 14, 10),
      child: SizedBox(
        height: 34,
        child: ListView(
          scrollDirection: Axis.horizontal,
          physics: const BouncingScrollPhysics(),
          children: [
            _buildPatientChip(
              label: 'Everyone',
              icon: Icons.people_outline_rounded,
              selected: _selectedPatientFilter == null,
              onTap: () {
                HapticFeedback.selectionClick();
                setState(() => _selectedPatientFilter = null);
                _analytics('care_records_patient_filter_cleared');
              },
            ),
            for (final name in _patientNames)
              _buildPatientChip(
                label: name,
                icon: name == _primaryPatientName
                    ? Icons.person_rounded
                    : Icons.person_outline_rounded,
                selected: _selectedPatientFilter == name,
                onTap: () {
                  HapticFeedback.selectionClick();
                  setState(() => _selectedPatientFilter = name);
                  _analytics('care_records_patient_filter_set',
                      {'isPrimary': (name == _primaryPatientName).toString()});
                },
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildPatientChip({
    required String label,
    required IconData icon,
    required bool selected,
    required VoidCallback onTap,
  }) {
    return Padding(
      padding: const EdgeInsets.only(right: 6),
      child: _PressableMaterial(
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(10),
          child: Semantics(
            label: selected ? '$label, selected' : label,
            button: true,
            child: AnimatedContainer(
              duration: _Motion.select,
              curve: _Motion.settle,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                gradient: selected
                    ? const LinearGradient(
                        colors: [_joviCoral, _joviCoralDark],
                      )
                    : null,
                color: selected ? null : Colors.white.withOpacity(0.05),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(
                  color: selected
                      ? _joviCoral.withOpacity(0.6)
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
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    icon,
                    size: 13,
                    color: selected
                        ? Colors.white
                        : Colors.white.withOpacity(0.65),
                  ),
                  const SizedBox(width: 5),
                  Text(
                    label,
                    style: TextStyle(
                      color: selected
                          ? Colors.white
                          : Colors.white.withOpacity(0.78),
                      fontSize: 12,
                      fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
                      letterSpacing: 0.2,
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

  Widget _buildTabButton(
    _Tab tab,
    String label,
    IconData inactiveIcon,
    IconData activeIcon, {
    int? badge,
  }) {
    final isActive = _currentTab == tab;
    return Expanded(
      child: Semantics(
        label: label,
        selected: isActive,
        button: true,
        child: _PressableMaterial(
          child: InkWell(
            onTap: () {
              if (_currentTab == tab) return;
              HapticFeedback.selectionClick();
              setState(() => _currentTab = tab);
              if (MediaQuery.of(context).disableAnimations) {
                _fadeCtrl.value = 1.0;
              } else {
                _fadeCtrl.forward(from: 0.35);
              }
              _analytics(
                  'care_records_tab_selected', {'tab': _tabSerialize(tab)});
            },
            borderRadius: BorderRadius.circular(11),
            child: AnimatedContainer(
              duration: _Motion.select,
              curve: _Motion.settle,
              padding: const EdgeInsets.symmetric(vertical: 10),
              decoration: BoxDecoration(
                gradient: isActive
                    ? const LinearGradient(
                        colors: [_joviCoral, _joviCoralDark],
                      )
                    : null,
                borderRadius: BorderRadius.circular(11),
                boxShadow: isActive
                    ? [
                        BoxShadow(
                          color: _joviCoral.withOpacity(0.35),
                          blurRadius: 12,
                          offset: const Offset(0, 3),
                        ),
                      ]
                    : null,
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    isActive ? activeIcon : inactiveIcon,
                    color:
                        isActive ? Colors.white : Colors.white.withOpacity(0.7),
                    size: 16,
                  ),
                  const SizedBox(width: 6),
                  Text(
                    label,
                    style: TextStyle(
                      color: isActive
                          ? Colors.white
                          : Colors.white.withOpacity(0.7),
                      fontSize: 12.5,
                      fontWeight: isActive ? FontWeight.w800 : FontWeight.w600,
                      letterSpacing: 0.2,
                    ),
                  ),
                  if (badge != null) ...[
                    const SizedBox(width: 5),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 6, vertical: 1),
                      constraints: const BoxConstraints(minWidth: 18),
                      decoration: BoxDecoration(
                        color: isActive
                            ? Colors.white.withOpacity(0.25)
                            : _joviCoral.withOpacity(0.3),
                        borderRadius: BorderRadius.circular(9),
                      ),
                      child: Text(
                        '$badge',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: isActive ? Colors.white : _joviCoral,
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  String _tabSerialize(_Tab t) {
    switch (t) {
      case _Tab.upcoming:
        return 'upcoming';
      case _Tab.past:
        return 'past';
      case _Tab.timeline:
        return 'timeline';
    }
  }

  // ---------------------------------------------------------------------
  // TAB ROUTING
  // ---------------------------------------------------------------------

  Widget _routeTab() {
    switch (_currentTab) {
      case _Tab.upcoming:
        return _buildUpcomingView();
      case _Tab.past:
        return _buildPastView();
      case _Tab.timeline:
        return _buildTimelineView();
    }
  }

  // ---------------------------------------------------------------------
  // PLACEHOLDERS (to be replaced by Phase 4 / 5 / 6 builders)
  // Each returns a simple loading or empty state so the widget compiles
  // and renders cleanly before the detailed views are wired up.
  // ---------------------------------------------------------------------

  Widget _buildUpcomingView() {
    if (_loadingAppointments) return _buildLoadingPlaceholder();
    if (_appointmentsError != null) {
      return _buildErrorPlaceholder(
        _appointmentsError!,
        onRetry: () {
          _appointmentsRetries = 0;
          _subscribeToAppointments();
        },
      );
    }
    final upcoming = _filteredUpcoming;
    if (upcoming.isEmpty) {
      // Three possible empty states, in priority order:
      //   1. Search is active with no matches — most specific
      //   2. Patient filter is active with no matches
      //   3. Truly no upcoming appointments
      if (_searchActiveNonEmpty) {
        return _buildEmptyPlaceholder(
          icon: Icons.search_off_rounded,
          title: 'No matches for "$_searchQuery"',
          body:
              'No upcoming appointments match your search. Try different keywords or clear your search.',
        );
      }
      return _buildEmptyPlaceholder(
        icon: Icons.event_available_rounded,
        title: _patientFilterActive
            ? 'No upcoming for $_selectedPatientFilter'
            : 'No upcoming appointments',
        body: _patientFilterActive
            ? 'No scheduled visits for this family member. Try switching to "Everyone" above.'
            : 'You don\'t have any visits scheduled right now.',
        ctaLabel: _patientFilterActive ? null : 'Book a visit',
        onCta: _patientFilterActive ? null : _openRequestCare,
      );
    }

    // Group upcoming appointments by relative date bucket (Today / Tomorrow /
    // This week / Later) so the list reads like a natural agenda.
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final tomorrow = today.add(const Duration(days: 1));
    final weekEnd = today.add(const Duration(days: 7));

    final grouped = <String, List<_Appointment>>{
      'Today': [],
      'Tomorrow': [],
      'This week': [],
      'Later': [],
    };

    for (final a in upcoming) {
      final day = DateTime(a.startAt.year, a.startAt.month, a.startAt.day);
      if (day == today) {
        grouped['Today']!.add(a);
      } else if (day == tomorrow) {
        grouped['Tomorrow']!.add(a);
      } else if (day.isBefore(weekEnd)) {
        grouped['This week']!.add(a);
      } else {
        grouped['Later']!.add(a);
      }
    }

    return RefreshIndicator(
      onRefresh: _refreshAppointments,
      color: _joviCoral,
      backgroundColor: _joviNavyMid,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(14, 4, 14, 28),
        children: [
          for (final entry in grouped.entries)
            if (entry.value.isNotEmpty) ...[
              _buildSectionHeader(entry.key, count: entry.value.length),
              for (final a in entry.value)
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: _buildUpcomingAppointmentCard(a),
                ),
              const SizedBox(height: 8),
            ],
        ],
      ),
    );
  }

  Widget _buildSectionHeader(String label, {int? count}) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 12, 4, 8),
      child: Row(
        children: [
          Text(
            label,
            style: TextStyle(
              color: Colors.white.withOpacity(0.6),
              fontSize: 13,
              fontWeight: FontWeight.w600,
              letterSpacing: -0.1,
            ),
          ),
          if (count != null) ...[
            const SizedBox(width: 6),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.08),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                '$count',
                style: TextStyle(
                  color: Colors.white.withOpacity(0.65),
                  fontSize: 10,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  // =======================================================================
  // RICH UPCOMING APPOINTMENT CARD
  // =======================================================================

  Widget _buildUpcomingAppointmentCard(_Appointment a) {
    final typeColor = _apptTypeColor(a.type);
    final now = DateTime.now();
    final diff = a.startAt.difference(now);
    final isImminent = diff.inHours < 2 && !diff.isNegative;

    // Semantic label builds up a natural screen-reader sentence
    final semLabel = [
      _apptStatusLabel(a.status),
      _apptTypeLabel(a.type),
      'on ${DateFormat('EEEE MMMM d').format(a.startAt)}',
      'at ${DateFormat('h:mm a').format(a.startAt)}',
      if (a.clinicName != null) 'at ${a.clinicName}',
      if (a.providerName != null) 'with ${a.providerDisplay}',
      'Double tap for actions',
    ].join(', ');

    return Semantics(
      label: semLabel,
      button: true,
      child: _PressableMaterial(
        child: InkWell(
          onTap: () => _showAppointmentActions(a),
          borderRadius: BorderRadius.circular(20),
          child: _glassCard(
            bgOpacity: 0.07,
            borderOpacity: 0.14,
            borderWidth: 1,
            padding: const EdgeInsets.fromLTRB(14, 14, 14, 12),
            borderTint: isImminent ? _joviCoral : null,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header row: date block + type icon + imminent indicator
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildDateBadge(a.startAt, accent: typeColor),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Icon(
                                _apptTypeIcon(a.type),
                                color: typeColor,
                                size: 14,
                              ),
                              const SizedBox(width: 5),
                              Flexible(
                                child: Text(
                                  _apptTypeLabel(a.type),
                                  style: TextStyle(
                                    color: typeColor,
                                    fontSize: 12,
                                    fontWeight: FontWeight.w800,
                                    letterSpacing: 0.3,
                                  ),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Text(
                            DateFormat('h:mm a').format(a.startAt),
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 20,
                              fontWeight: FontWeight.w700,
                              letterSpacing: -0.6,
                              height: 1.1,
                            ),
                          ),
                          if (a.durationMinutes != null)
                            Padding(
                              padding: const EdgeInsets.only(top: 2),
                              child: Text(
                                'Duration: ${a.durationMinutes} min',
                                style: TextStyle(
                                  color: Colors.white.withOpacity(0.5),
                                  fontSize: 11.5,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ),
                        ],
                      ),
                    ),
                    if (isImminent)
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: _joviCoral.withOpacity(0.18),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                            color: _joviCoral.withOpacity(0.4),
                            width: 0.8,
                          ),
                        ),
                        child: const Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.notifications_active_rounded,
                                color: _joviCoral, size: 11),
                            SizedBox(width: 3),
                            Text(
                              'Soon',
                              style: TextStyle(
                                color: _joviCoral,
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
                const SizedBox(height: 12),
                // Divider
                Container(
                  height: 1,
                  color: Colors.white.withOpacity(0.06),
                ),
                const SizedBox(height: 10),
                // Clinic + provider
                if (a.clinicName != null && a.clinicName!.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 4),
                    child: Row(
                      children: [
                        Icon(
                          a.isTelehealth
                              ? Icons.videocam_outlined
                              : Icons.location_on_outlined,
                          color: Colors.white.withOpacity(0.55),
                          size: 13,
                        ),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            a.isTelehealth ? 'Telehealth visit' : a.clinicName!,
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.85),
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                  ),
                if (a.providerName != null && a.providerName!.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 4),
                    child: Row(
                      children: [
                        Icon(
                          Icons.person_outline,
                          color: Colors.white.withOpacity(0.55),
                          size: 13,
                        ),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            a.providerDisplay,
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.85),
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                  ),
                if (a.reason != null && a.reason!.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 4, bottom: 4),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(
                          Icons.chat_bubble_outline,
                          color: Colors.white.withOpacity(0.45),
                          size: 12,
                        ),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            a.reason!,
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.6),
                              fontSize: 12,
                              fontWeight: FontWeight.w500,
                              fontStyle: FontStyle.italic,
                              height: 1.35,
                            ),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                  ),
                const SizedBox(height: 10),
                // Action row: quick tap targets — full action sheet on tap
                Row(
                  children: [
                    if (a.isTelehealth && a.telehealthUrl != null)
                      Expanded(
                        child: _buildQuickAction(
                          icon: Icons.videocam_rounded,
                          label: 'Join',
                          color: _joviMintDark,
                          onTap: () => _joinTelehealth(a),
                        ),
                      )
                    else if (!a.isTelehealth &&
                        a.clinicAddress != null &&
                        a.clinicAddress!.isNotEmpty)
                      Expanded(
                        child: _buildQuickAction(
                          icon: Icons.directions_rounded,
                          label: 'Directions',
                          color: _joviMintDark,
                          onTap: () => _openDirections(a),
                        ),
                      )
                    else
                      const Expanded(child: SizedBox.shrink()),
                    const SizedBox(width: 8),
                    if (a.clinicPhone != null && a.clinicPhone!.isNotEmpty)
                      Expanded(
                        child: _buildQuickAction(
                          icon: Icons.phone_rounded,
                          label: 'Call',
                          color: _joviGold,
                          onTap: () => _callClinic(a),
                        ),
                      )
                    else
                      const Expanded(child: SizedBox.shrink()),
                    const SizedBox(width: 8),
                    Expanded(
                      child: _buildQuickAction(
                        icon: Icons.more_horiz_rounded,
                        label: 'More',
                        color: _joviCoral,
                        onTap: () => _showAppointmentActions(a),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildDateBadge(DateTime dt, {required Color accent}) {
    return Container(
      width: 58,
      height: 62,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            accent.withOpacity(0.22),
            accent.withOpacity(0.08),
          ],
        ),
        borderRadius: BorderRadius.circular(13),
        border: Border.all(
          color: accent.withOpacity(0.38),
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: accent.withOpacity(0.22),
            blurRadius: 10,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            DateFormat('MMM').format(dt).toUpperCase(),
            style: TextStyle(
              color: accent,
              fontSize: 10.5,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.5,
            ),
          ),
          const SizedBox(height: 1),
          Text(
            DateFormat('d').format(dt),
            style: const TextStyle(
              color: Colors.white,
              fontSize: 22,
              fontWeight: FontWeight.w700,
              height: 1.0,
              letterSpacing: -0.5,
            ),
          ),
          const SizedBox(height: 1),
          Text(
            DateFormat('EEE').format(dt).toUpperCase(),
            style: TextStyle(
              color: Colors.white.withOpacity(0.55),
              fontSize: 9,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.2,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildQuickAction({
    required IconData icon,
    required String label,
    required Color color,
    required VoidCallback onTap,
  }) {
    return _PressableMaterial(
      child: InkWell(
        onTap: () {
          HapticFeedback.selectionClick();
          onTap();
        },
        borderRadius: BorderRadius.circular(11),
        child: Tooltip(
          message: label,
          child: Semantics(
            label: label,
            button: true,
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 9),
              decoration: BoxDecoration(
                color: color.withOpacity(0.14),
                borderRadius: BorderRadius.circular(11),
                border: Border.all(
                  color: color.withOpacity(0.3),
                  width: 0.8,
                ),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(icon, color: color, size: 14),
                  const SizedBox(width: 5),
                  Text(
                    label,
                    style: TextStyle(
                      color: color,
                      fontSize: 11.5,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0.2,
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

  // =======================================================================
  // APPOINTMENT ACTION SHEET
  // Full action sheet shown when member taps an upcoming appointment.
  // Contains: join telehealth, directions, call clinic, reschedule, cancel.
  // =======================================================================

  Future<void> _showAppointmentActions(_Appointment a) async {
    HapticFeedback.lightImpact();
    if (!mounted) return;

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(ctx).viewInsets.bottom,
        ),
        child: ClipRRect(
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
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Grab handle
                  Container(
                    margin: const EdgeInsets.only(top: 10),
                    width: 38,
                    height: 4,
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                  // Header with appointment summary
                  Padding(
                    padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _apptTypeLabel(a.type),
                          style: TextStyle(
                            color: _apptTypeColor(a.type),
                            fontSize: 12,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 0.3,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          DateFormat('EEEE, MMMM d · h:mm a').format(a.startAt),
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 18,
                            fontWeight: FontWeight.w700,
                            letterSpacing: -0.5,
                          ),
                        ),
                        if (a.clinicName != null)
                          Padding(
                            padding: const EdgeInsets.only(top: 2),
                            child: Text(
                              a.clinicName!,
                              style: TextStyle(
                                color: Colors.white.withOpacity(0.6),
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 6),
                  // Action rows
                  if (a.isTelehealth && a.telehealthUrl != null)
                    _buildActionRow(
                      ctx: ctx,
                      icon: Icons.videocam_rounded,
                      accent: _joviMintDark,
                      title: 'Join telehealth visit',
                      subtitle: 'Open the video call link',
                      onTap: () {
                        Navigator.of(ctx).pop();
                        _joinTelehealth(a);
                      },
                    ),
                  if (!a.isTelehealth &&
                      a.clinicAddress != null &&
                      a.clinicAddress!.isNotEmpty)
                    _buildActionRow(
                      ctx: ctx,
                      icon: Icons.directions_rounded,
                      accent: _joviMintDark,
                      title: 'Get directions',
                      subtitle: 'Open in maps',
                      onTap: () {
                        Navigator.of(ctx).pop();
                        _openDirections(a);
                      },
                    ),
                  if (a.clinicPhone != null && a.clinicPhone!.isNotEmpty)
                    _buildActionRow(
                      ctx: ctx,
                      icon: Icons.phone_rounded,
                      accent: _joviGold,
                      title: 'Call clinic',
                      subtitle: a.clinicPhone,
                      onTap: () {
                        Navigator.of(ctx).pop();
                        _callClinic(a);
                      },
                    ),
                  _buildActionRow(
                    ctx: ctx,
                    icon: Icons.event_available_rounded,
                    accent: _joviMintDark,
                    title: 'Add to calendar',
                    subtitle: 'Save to your device calendar',
                    onTap: () {
                      Navigator.of(ctx).pop();
                      _addToCalendar(a);
                    },
                  ),
                  _buildActionRow(
                    ctx: ctx,
                    icon: Icons.event_repeat_rounded,
                    accent: const Color(0xFFA78BFA),
                    title: 'Reschedule',
                    subtitle: 'Pick a different time',
                    onTap: () {
                      Navigator.of(ctx).pop();
                      _rescheduleAppointment(a);
                    },
                  ),
                  _buildActionRow(
                    ctx: ctx,
                    icon: Icons.cancel_outlined,
                    accent: _joviErrorRed,
                    title: 'Cancel appointment',
                    subtitle: 'Free up this time slot',
                    onTap: () {
                      Navigator.of(ctx).pop();
                      _confirmAndCancelAppointment(a);
                    },
                    destructive: true,
                  ),
                  const SizedBox(height: 20),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildActionRow({
    required BuildContext ctx,
    required IconData icon,
    required Color accent,
    required String title,
    String? subtitle,
    required VoidCallback onTap,
    bool destructive = false,
  }) {
    return _PressableMaterial(
      child: InkWell(
        onTap: onTap,
        child: Semantics(
          label: subtitle != null ? '$title, $subtitle' : title,
          button: true,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
            child: Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: accent.withOpacity(0.16),
                    borderRadius: BorderRadius.circular(11),
                    border: Border.all(
                      color: accent.withOpacity(0.3),
                      width: 0.8,
                    ),
                  ),
                  child: Icon(icon, color: accent, size: 19),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        title,
                        style: TextStyle(
                          color: destructive ? _joviErrorRed : Colors.white,
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                          letterSpacing: -0.2,
                        ),
                      ),
                      if (subtitle != null) ...[
                        const SizedBox(height: 2),
                        Text(
                          subtitle,
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.55),
                            fontSize: 12,
                            fontWeight: FontWeight.w500,
                          ),
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

  // =======================================================================
  // APPOINTMENT ACTIONS
  // =======================================================================

  /// Open the clinic address in the platform's maps app via url_launcher.
  Future<void> _openDirections(_Appointment a) async {
    if (a.clinicAddress == null || a.clinicAddress!.isEmpty) {
      _showSnackBar('Address not available', isError: true);
      return;
    }
    HapticFeedback.lightImpact();

    // Prefer coords if we have them (more accurate); fallback to address text.
    String query;
    if (a.clinicLat != null && a.clinicLng != null) {
      query = '${a.clinicLat},${a.clinicLng}';
    } else {
      query = Uri.encodeComponent(a.clinicAddress!);
    }
    final uri =
        Uri.parse('https://www.google.com/maps/search/?api=1&query=$query');

    try {
      final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (!ok) {
        _showSnackBar('Could not open maps', isError: true);
      } else {
        _analytics('care_records_directions_opened', {'appointmentId': a.id});
      }
    } catch (e) {
      _logError('open directions failed', e);
      _showSnackBar('Could not open maps', isError: true);
    }
  }

  /// Launch a tel: URI to the clinic.
  Future<void> _callClinic(_Appointment a) async {
    if (a.clinicPhone == null || a.clinicPhone!.isEmpty) {
      _showSnackBar('Phone number not available', isError: true);
      return;
    }
    HapticFeedback.lightImpact();

    // Strip non-digit characters for safe tel: URI
    final digits = a.clinicPhone!.replaceAll(RegExp(r'[^\d+]'), '');
    final uri = Uri.parse('tel:$digits');
    try {
      final ok = await launchUrl(uri);
      if (!ok) {
        _showSnackBar(
          'Could not dial ${a.clinicPhone}. Try calling it manually.',
          isError: true,
        );
      } else {
        _analytics('care_records_clinic_called', {'appointmentId': a.id});
      }
    } catch (e) {
      _logError('call clinic failed', e);
      _showSnackBar(
        'Could not dial. Call ${a.clinicPhone} manually.',
        isError: true,
      );
    }
  }

  /// Open the telehealth video link.
  Future<void> _joinTelehealth(_Appointment a) async {
    if (a.telehealthUrl == null || a.telehealthUrl!.isEmpty) {
      _showSnackBar(
        'Video link not available yet. It should arrive before your visit.',
        isError: true,
      );
      return;
    }
    HapticFeedback.lightImpact();

    final uri = Uri.tryParse(a.telehealthUrl!);
    if (uri == null) {
      _showSnackBar('Invalid video link', isError: true);
      return;
    }

    try {
      final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (!ok) {
        _showSnackBar('Could not open video link', isError: true);
      } else {
        _analytics('care_records_telehealth_joined', {'appointmentId': a.id});
      }
    } catch (e) {
      _logError('join telehealth failed', e);
      _showSnackBar('Could not open video link', isError: true);
    }
  }

  /// Route the member to Request Care in "reschedule" mode. The Request
  /// widget supports a rescheduleRequestId prop that, when set, updates
  /// the existing doc rather than creating a new one.
  void _rescheduleAppointment(_Appointment a) {
    HapticFeedback.lightImpact();
    _analytics('care_records_reschedule_started', {'appointmentId': a.id});
    // Try a few possible route name variants so FF's case conventions
    // don't break the flow.
    final routes = ['requests', 'Requests', 'RequestCare', 'requestCare'];
    for (final route in routes) {
      try {
        context.pushNamed(route, extra: {'rescheduleRequestId': a.id});
        _log('navigated to $route for reschedule');
        return;
      } catch (_) {
        continue;
      }
    }
    _showSnackBar(
      'Could not open the scheduler. Please call the clinic to reschedule.',
      isError: true,
    );
  }

  /// Add this appointment to the device calendar using the OS's built-in
  /// calendar picker (iOS Event Kit / Android calendar intent). Uses the
  /// add_2_calendar package which launches the native Add Event dialog.
  ///
  /// The user can pick which of their calendars to add to and edit the
  /// details before confirming — we're not writing silently.
  Future<void> _addToCalendar(_Appointment a) async {
    HapticFeedback.lightImpact();
    _analytics('care_records_add_to_calendar', {'appointmentId': a.id});

    // Default to 30-minute duration if we don't know
    final duration = Duration(minutes: a.durationMinutes ?? 30);
    final endTime = a.startAt.add(duration);

    final title = a.providerName != null && a.providerName!.isNotEmpty
        ? '${_apptTypeLabel(a.type)} with ${a.providerDisplay}'
        : _apptTypeLabel(a.type);

    // Build the location string — prefer full address, fall back to
    // clinic name, or "Telehealth visit" for virtual appointments.
    String? location;
    if (a.isTelehealth) {
      location = a.telehealthUrl != null && a.telehealthUrl!.isNotEmpty
          ? 'Telehealth: ${a.telehealthUrl}'
          : 'Telehealth visit';
    } else if (a.clinicAddress != null && a.clinicAddress!.isNotEmpty) {
      location = a.clinicAddress;
    } else if (a.clinicName != null && a.clinicName!.isNotEmpty) {
      location = a.clinicName;
    }

    // Description includes reason + any contact info the clinic provided
    final descriptionParts = <String>[];
    if (a.reason != null && a.reason!.isNotEmpty) {
      descriptionParts.add('Reason: ${a.reason}');
    }
    if (a.clinicPhone != null && a.clinicPhone!.isNotEmpty) {
      descriptionParts.add('Clinic: ${a.clinicPhone}');
    }
    descriptionParts.add('Added from Jovi Health Care Records.');

    try {
      final event = a2c.Event(
        title: title,
        description: descriptionParts.join('\n'),
        location: location,
        startDate: a.startAt,
        endDate: endTime,
        iosParams: const a2c.IOSParams(
          reminder: Duration(hours: 1),
        ),
        androidParams: const a2c.AndroidParams(
          emailInvites: [],
        ),
      );
      final added = await a2c.Add2Calendar.addEvent2Cal(event);
      if (added) {
        _showSnackBar('Added to your calendar.', isSuccess: true);
      } else {
        _showSnackBar(
          'Calendar unavailable. You can still see this visit in Care Records.',
          isInfo: true,
        );
      }
    } catch (e) {
      _logError('add to calendar failed', e);
      _showSnackBar(
        'Could not add to calendar. You can still see this visit in Care Records.',
        isError: true,
      );
    }
  }

  /// Two-step cancel confirmation with policy warning.
  Future<void> _confirmAndCancelAppointment(_Appointment a) async {
    HapticFeedback.mediumImpact();
    if (!mounted) return;

    final now = DateTime.now();
    final hoursUntil = a.startAt.difference(now).inHours;
    final isShortNotice = hoursUntil < 24;

    final confirmed = await showCupertinoDialog<bool>(
      context: context,
      builder: (ctx) => CupertinoAlertDialog(
        title: const Text('Cancel Appointment?'),
        content: Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Text(
            'Your ${_apptTypeLabel(a.type).toLowerCase()} on '
            '${DateFormat('EEEE, MMM d at h:mm a').format(a.startAt)} '
            'will be cancelled and the time slot released.'
            '${isShortNotice ? '\n\nThis is a short-notice cancellation. If your membership has a short-notice fee, it may apply.' : ''}',
          ),
        ),
        actions: [
          CupertinoDialogAction(
            isDefaultAction: true,
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Keep It'),
          ),
          CupertinoDialogAction(
            isDestructiveAction: true,
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Cancel Appointment'),
          ),
        ],
      ),
    );

    if (confirmed != true || !mounted) return;
    await _executeCancel(a);
  }

  /// Perform the actual Firestore writes for a cancellation. Matches the
  /// pattern used by jovi_appointments.dart for cross-widget consistency:
  ///
  ///   1. Write an audit record to `cancelled_appointments`
  ///   2. Update the original `requests/{id}` — null out user fields,
  ///      set status='available', save previousUserId for history
  ///   3. If Jovi Pass priority, write to `kurv_pass_cancellations` with
  ///      the non-refundable $49 fee
  ///
  /// Wrapped in a progress overlay so the member sees something happen
  /// even on slow connections.
  Future<void> _executeCancel(_Appointment a) async {
    HapticFeedback.heavyImpact();
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return;

    // Show blocking progress
    showDialog<void>(
      context: context,
      barrierDismissible: false,
      barrierColor: Colors.black.withOpacity(0.7),
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
                child: const Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    SizedBox(
                      width: 28,
                      height: 28,
                      child: CircularProgressIndicator(
                        strokeWidth: 2.5,
                        valueColor: AlwaysStoppedAnimation<Color>(_joviCoral),
                      ),
                    ),
                    SizedBox(height: 14),
                    Text(
                      'Cancelling…',
                      style: TextStyle(
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

    try {
      final apptRef =
          FirebaseFirestore.instance.collection('requests').doc(a.id);
      final snap = await apptRef.get();
      if (!snap.exists) {
        throw Exception('Appointment no longer exists');
      }
      final data = snap.data() as Map<String, dynamic>;
      final wasPriority =
          data['priority'] == true || data['kurvPassPurchased'] == true;

      // 1. Audit trail write
      await FirebaseFirestore.instance
          .collection('cancelled_appointments')
          .add({
        'originalAppointmentId': a.id,
        'userId': user.uid,
        'patientName': data['patientName'],
        'appointmentDate': data['appointmentDate'],
        'appointmentTime': data['appointmentTime'],
        'visitType': data['visitType'],
        'visitMode': data['visitMode'],
        'clinic': data['clinic'],
        'symptom': data['symptom'],
        'wasPriority': wasPriority,
        'cancelledAt': FieldValue.serverTimestamp(),
        'cancelledBy': user.uid,
        'source': 'care_records',
      });

      // 2. Update the original request — free up the slot
      await apptRef.update({
        'status': 'available',
        'previousStatus': data['status'],
        'userId': null,
        'patientName': null,
        'symptom': null,
        'symptomDuration': null,
        'details': null,
        'medication': null,
        'photoUrl': null,
        'priority': false,
        'kurvPassPurchased': false,
        'cancelledAt': FieldValue.serverTimestamp(),
        'cancelledBy': user.uid,
        'previousUserId': user.uid,
      });

      // 3. Jovi Pass cancellation record (collection name kept for backend)
      if (wasPriority) {
        await FirebaseFirestore.instance
            .collection('kurv_pass_cancellations')
            .add({
          'appointmentId': a.id,
          'userId': user.uid,
          'cancelledAt': FieldValue.serverTimestamp(),
          'appointmentDate': data['appointmentDate'],
          'appointmentTime': data['appointmentTime'],
          'visitType': data['visitType'],
          'visitMode': data['visitMode'],
          'clinic': data['clinic'],
          'nonRefundableAmount': 49.00,
          'patientName': data['patientName'],
          'source': 'care_records',
        });
      }

      _analytics('care_records_appointment_cancelled', {
        'appointmentId': a.id,
        'wasPriority': wasPriority.toString(),
      });

      if (!mounted) return;
      Navigator.of(context).pop(); // close progress

      _showSnackBar(
        wasPriority
            ? 'Appointment cancelled. Your Jovi Pass fee (\$49) is non-refundable.'
            : 'Appointment cancelled. The time slot is now open.',
        isSuccess: !wasPriority,
        isInfo: wasPriority,
      );
    } catch (e) {
      _logError('cancel failed', e);
      _analytics(
          'care_records_appointment_cancel_failed', {'appointmentId': a.id});
      if (!mounted) return;
      Navigator.of(context).pop(); // close progress
      _showSnackBar(
        'Could not cancel. Please try again or call the clinic.',
        isError: true,
      );
    }
  }

  /// Shared snackbar helper with color-coded severity.
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

  Widget _buildPastView() {
    if (_loadingAppointments || _loadingVisits) {
      return _buildLoadingPlaceholder();
    }
    final pastAll = _filteredPast;
    final visitsAll = _filteredVisitRecords;
    if (_appointmentsError != null && pastAll.isEmpty && visitsAll.isEmpty) {
      return _buildErrorPlaceholder(
        _appointmentsError!,
        onRetry: () {
          _appointmentsRetries = 0;
          _subscribeToAppointments();
        },
      );
    }

    // Build a unified past-entries list that merges:
    //   - Visit records (rich clinical content)
    //   - Past completed/no-show appointments without a linked visit record
    //   - Cancelled-by-me appointments (for historical visibility)
    // Each entry is wrapped in a _PastEntry envelope with enough info
    // for the list card, and the underlying object for tap-through.
    final entries = _buildPastEntries();

    if (entries.isEmpty) {
      if (_searchActiveNonEmpty) {
        return _buildEmptyPlaceholder(
          icon: Icons.search_off_rounded,
          title: 'No matches for "$_searchQuery"',
          body:
              'No past visits match your search. Try different keywords or clear your search.',
        );
      }
      return _buildEmptyPlaceholder(
        icon: Icons.history_rounded,
        title: _patientFilterActive
            ? 'No past visits for $_selectedPatientFilter'
            : 'No past visits yet',
        body: _patientFilterActive
            ? 'No visit history for this family member. Try switching to "Everyone" above.'
            : 'Once you complete a visit with a Jovi provider, the details will appear here.',
      );
    }

    // Group entries by year for visual rhythm on long histories.
    final grouped = <int, List<_PastEntry>>{};
    for (final e in entries) {
      grouped.putIfAbsent(e.when.year, () => []).add(e);
    }
    final years = grouped.keys.toList()..sort((a, b) => b.compareTo(a));
    final thisYear = DateTime.now().year;

    return RefreshIndicator(
      onRefresh: _refreshVisits,
      color: _joviCoral,
      backgroundColor: _joviNavyMid,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(14, 4, 14, 28),
        children: [
          for (final y in years) ...[
            _buildSectionHeader(
              y == thisYear ? 'This year' : '$y',
              count: grouped[y]!.length,
            ),
            for (final e in grouped[y]!)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: _buildPastEntryCard(e),
              ),
            const SizedBox(height: 8),
          ],
        ],
      ),
    );
  }

  /// Merges the three past-related data sources into a single sorted list.
  /// Applies the active patient filter via the _filtered* getters.
  List<_PastEntry> _buildPastEntries() {
    final entries = <_PastEntry>[];
    final visits = _filteredVisitRecords;
    final past = _filteredPast;
    final cancelled = _filteredCancelled;

    // 1. Visit records (rich) — one per doc
    for (final v in visits) {
      entries.add(_PastEntry(
        id: 'visit_${v.id}',
        when: v.visitDate,
        kind: _PastEntryKind.visitRecord,
        payload: v,
      ));
    }

    // 2. Past appointments that DON'T have a linked visit record AND
    //    aren't "available" slots (those are freed cancellations).
    //    These are appointments where the clinic hasn't charted yet.
    final linkedRecordIds = visits
        .where((v) => v.appointmentId != null)
        .map((v) => v.appointmentId!)
        .toSet();
    for (final a in past) {
      if (a.status == AppointmentStatus.cancelled) continue; // handled below
      if (linkedRecordIds.contains(a.id)) continue; // already covered above
      entries.add(_PastEntry(
        id: 'appt_${a.id}',
        when: a.startAt,
        kind: _PastEntryKind.appointmentOnly,
        payload: a,
      ));
    }

    // 3. Cancelled-by-me appointments — for historical visibility
    for (final a in cancelled) {
      entries.add(_PastEntry(
        id: 'cancelled_${a.id}',
        when: a.startAt,
        kind: _PastEntryKind.cancelled,
        payload: a,
      ));
    }

    // Sort most-recent first
    entries.sort((a, b) => b.when.compareTo(a.when));
    return entries;
  }

  // =======================================================================
  // PAST ENTRY CARD
  // Visually distinguishes three kinds:
  //   - Visit record (full clinical data) — green dot, "View details" hint
  //   - Appointment-only (no clinical record yet) — gold dot, "Charting pending"
  //   - Cancelled — red dot, muted, "Cancelled" tag
  // =======================================================================

  Widget _buildPastEntryCard(_PastEntry entry) {
    switch (entry.kind) {
      case _PastEntryKind.visitRecord:
        return _buildVisitRecordCard(entry.payload as _VisitRecord);
      case _PastEntryKind.appointmentOnly:
        return _buildAppointmentOnlyCard(entry.payload as _Appointment);
      case _PastEntryKind.cancelled:
        return _buildCancelledCard(entry.payload as _Appointment);
    }
  }

  /// Rich visit record card — tappable for full detail.
  Widget _buildVisitRecordCard(_VisitRecord v) {
    final typeColor = _apptTypeColor(v.type);
    final semLabel = [
      'Visit',
      'on ${DateFormat('MMMM d, y').format(v.visitDate)}',
      if (v.providerName != null) 'with ${v.providerDisplay}',
      if (v.primaryDiagnosisLabel != null) 'for ${v.primaryDiagnosisLabel}',
      'Double tap for full detail',
    ].join(', ');

    return Semantics(
      label: semLabel,
      button: true,
      child: _PressableMaterial(
        child: InkWell(
          onTap: () => _showVisitRecordDetail(v),
          borderRadius: BorderRadius.circular(20),
          child: _glassCard(
            bgOpacity: 0.07,
            borderOpacity: 0.14,
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildDateBadge(v.visitDate, accent: typeColor),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Icon(_apptTypeIcon(v.type),
                                  color: typeColor, size: 13),
                              const SizedBox(width: 5),
                              Flexible(
                                child: Text(
                                  _apptTypeLabel(v.type),
                                  style: TextStyle(
                                    color: typeColor,
                                    fontSize: 12,
                                    fontWeight: FontWeight.w800,
                                    letterSpacing: 0.3,
                                  ),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                              const SizedBox(width: 6),
                              Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(
                                  color: _joviMintDark.withOpacity(0.16),
                                  borderRadius: BorderRadius.circular(5),
                                  border: Border.all(
                                    color: _joviMintDark.withOpacity(0.4),
                                    width: 0.7,
                                  ),
                                ),
                                child: Text(
                                  'Complete',
                                  style: TextStyle(
                                    color: _joviMintDark,
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
                            v.providerDisplay,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 16,
                              fontWeight: FontWeight.w800,
                              letterSpacing: -0.3,
                              height: 1.15,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          if (v.clinicName != null && v.clinicName!.isNotEmpty)
                            Padding(
                              padding: const EdgeInsets.only(top: 2),
                              child: Text(
                                v.clinicName!,
                                style: TextStyle(
                                  color: Colors.white.withOpacity(0.55),
                                  fontSize: 12,
                                  fontWeight: FontWeight.w500,
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                        ],
                      ),
                    ),
                  ],
                ),
                if (v.primaryDiagnosisLabel != null ||
                    v.prescriptions.isNotEmpty ||
                    v.labOrders.isNotEmpty ||
                    v.procedures.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Container(
                    height: 1,
                    color: Colors.white.withOpacity(0.06),
                  ),
                  const SizedBox(height: 10),
                  // Visit summary chips: primary dx, rx count, lab count, proc count
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: [
                      if (v.primaryDiagnosisLabel != null)
                        _buildSummaryChip(
                          icon: Icons.medical_information_outlined,
                          label: v.primaryDiagnosisLabel!,
                          color: _joviCoral,
                        ),
                      if (v.prescriptions.isNotEmpty)
                        _buildSummaryChip(
                          icon: Icons.medication_outlined,
                          label: v.prescriptions.length == 1
                              ? '1 Rx'
                              : '${v.prescriptions.length} Rx',
                          color: const Color(0xFFA78BFA),
                        ),
                      if (v.labOrders.isNotEmpty)
                        _buildSummaryChip(
                          icon: Icons.science_outlined,
                          label: v.labOrders.length == 1
                              ? '1 lab'
                              : '${v.labOrders.length} labs',
                          color: const Color(0xFF22D3EE),
                        ),
                      if (v.procedures.isNotEmpty)
                        _buildSummaryChip(
                          icon: Icons.healing_rounded,
                          label: v.procedures.length == 1
                              ? '1 procedure'
                              : '${v.procedures.length} procedures',
                          color: const Color(0xFFF472B6),
                        ),
                    ],
                  ),
                ],
                const SizedBox(height: 10),
                Row(
                  children: [
                    Icon(
                      Icons.arrow_forward_rounded,
                      color: _joviCoral.withOpacity(0.7),
                      size: 13,
                    ),
                    const SizedBox(width: 5),
                    Text(
                      'View full record',
                      style: TextStyle(
                        color: _joviCoral.withOpacity(0.9),
                        fontSize: 12,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.2,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  /// Appointment card shown when a visit occurred but no visit_record
  /// has been written yet (clinic hasn't charted). Non-tappable.
  Widget _buildAppointmentOnlyCard(_Appointment a) {
    final typeColor = _apptTypeColor(a.type);
    return _glassCard(
      bgOpacity: 0.05,
      borderOpacity: 0.1,
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildDateBadge(a.startAt, accent: typeColor),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(_apptTypeIcon(a.type), color: typeColor, size: 13),
                        const SizedBox(width: 5),
                        Flexible(
                          child: Text(
                            _apptTypeLabel(a.type),
                            style: TextStyle(
                              color: typeColor,
                              fontSize: 12,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 0.3,
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        const SizedBox(width: 6),
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: _joviGold.withOpacity(0.16),
                            borderRadius: BorderRadius.circular(5),
                            border: Border.all(
                              color: _joviGold.withOpacity(0.4),
                              width: 0.7,
                            ),
                          ),
                          child: Text(
                            'Pending',
                            style: TextStyle(
                              color: _joviGoldDark,
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
                      a.providerName == null || a.providerName!.isEmpty
                          ? (a.clinicName ?? 'Visit')
                          : a.providerDisplay,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 15,
                        fontWeight: FontWeight.w800,
                        letterSpacing: -0.3,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    if (a.clinicName != null &&
                        a.clinicName!.isNotEmpty &&
                        (a.providerName != null && a.providerName!.isNotEmpty))
                      Padding(
                        padding: const EdgeInsets.only(top: 2),
                        child: Text(
                          a.clinicName!,
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.55),
                            fontSize: 12,
                            fontWeight: FontWeight.w500,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: _joviGold.withOpacity(0.06),
              borderRadius: BorderRadius.circular(9),
              border: Border.all(
                color: _joviGold.withOpacity(0.18),
                width: 0.8,
              ),
            ),
            child: Row(
              children: [
                Icon(
                  Icons.edit_note_rounded,
                  color: _joviGoldDark,
                  size: 14,
                ),
                const SizedBox(width: 7),
                Expanded(
                  child: Text(
                    'Visit charting in progress. Full details will appear once your provider completes the record.',
                    style: TextStyle(
                      color: _joviGoldDark,
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
      ),
    );
  }

  /// De-emphasized card for cancelled appointments — historical only.
  Widget _buildCancelledCard(_Appointment a) {
    return Opacity(
      opacity: 0.72,
      child: _glassCard(
        bgOpacity: 0.04,
        borderOpacity: 0.08,
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: _joviErrorRed.withOpacity(0.1),
                borderRadius: BorderRadius.circular(11),
                border: Border.all(
                  color: _joviErrorRed.withOpacity(0.24),
                  width: 0.8,
                ),
              ),
              child: const Icon(
                Icons.event_busy_rounded,
                color: _joviErrorRed,
                size: 17,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    'Cancelled — ${_apptTypeLabel(a.type)}',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.78),
                      fontSize: 13.5,
                      fontWeight: FontWeight.w700,
                      letterSpacing: -0.2,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    '${DateFormat('MMM d, y').format(a.startAt)}'
                    '${a.clinicName != null && a.clinicName!.isNotEmpty ? ' • ${a.clinicName}' : ''}',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.42),
                      fontSize: 11.5,
                      fontWeight: FontWeight.w500,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSummaryChip({
    required IconData icon,
    required String label,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4.5),
      decoration: BoxDecoration(
        color: color.withOpacity(0.14),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: color.withOpacity(0.3),
          width: 0.8,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, color: color, size: 11),
          const SizedBox(width: 4),
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 180),
            child: Text(
              label,
              style: TextStyle(
                color: color,
                fontSize: 11,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.1,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }

  // =======================================================================
  // VISIT RECORD DETAIL VIEW
  // The substantial payload — full-screen bottom sheet showing every
  // section of clinical data for a completed visit. Each section only
  // renders if it has data.
  // =======================================================================

  Future<void> _showVisitRecordDetail(_VisitRecord v) async {
    HapticFeedback.lightImpact();
    if (!mounted) return;
    _analytics('care_records_visit_opened', {'visitRecordId': v.id});

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      useSafeArea: true,
      builder: (ctx) => DraggableScrollableSheet(
        initialChildSize: 0.92,
        maxChildSize: 0.95,
        minChildSize: 0.6,
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
                    _joviNavy.withOpacity(0.98),
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
                  // Grab handle
                  Container(
                    margin: const EdgeInsets.only(top: 10),
                    width: 38,
                    height: 4,
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                  // Sticky header with close button
                  _buildVisitDetailHeader(ctx, v),
                  // Scrollable content
                  Expanded(
                    child: SingleChildScrollView(
                      controller: scrollCtrl,
                      padding: const EdgeInsets.fromLTRB(16, 4, 16, 28),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // Section: Chief complaint & HPI
                          if (_hasChiefComplaintContent(v))
                            _buildDetailSection(
                              icon: Icons.chat_bubble_outline_rounded,
                              accent: _joviCoral,
                              title: 'Chief complaint',
                              child: _buildChiefComplaintContent(v),
                            ),
                          // Section: Vitals
                          if (v.vitals != null && v.vitals!.hasAny)
                            _buildDetailSection(
                              icon: Icons.favorite_border_rounded,
                              accent: const Color(0xFFFB7185),
                              title: 'Vitals',
                              child: _buildVitalsGrid(v.vitals!),
                            ),
                          // Section: Diagnoses
                          if (v.diagnoses.isNotEmpty)
                            _buildDetailSection(
                              icon: Icons.medical_information_outlined,
                              accent: _joviCoral,
                              title: v.diagnoses.length == 1
                                  ? 'Assessment'
                                  : 'Assessments',
                              child: _buildDiagnosesList(v.diagnoses),
                            ),
                          // Section: Prescriptions
                          if (v.prescriptions.isNotEmpty)
                            _buildDetailSection(
                              icon: Icons.medication_outlined,
                              accent: const Color(0xFFA78BFA),
                              title: v.prescriptions.length == 1
                                  ? 'Prescription'
                                  : 'Prescriptions',
                              child: _buildPrescriptionsList(v.prescriptions),
                            ),
                          // Section: Labs
                          if (v.labOrders.isNotEmpty)
                            _buildDetailSection(
                              icon: Icons.science_outlined,
                              accent: const Color(0xFF22D3EE),
                              title: 'Labs & imaging',
                              child: _buildLabOrdersList(v.labOrders),
                            ),
                          // Section: Procedures
                          if (v.procedures.isNotEmpty)
                            _buildDetailSection(
                              icon: Icons.healing_rounded,
                              accent: const Color(0xFFF472B6),
                              title: v.procedures.length == 1
                                  ? 'Procedure'
                                  : 'Procedures',
                              child: _buildProceduresList(v.procedures),
                            ),
                          // Section: Clinical notes
                          if (v.clinicalNotes != null &&
                              v.clinicalNotes!.isNotEmpty)
                            _buildDetailSection(
                              icon: Icons.notes_rounded,
                              accent: _joviMint,
                              title: 'Provider notes',
                              child:
                                  _buildClinicalNotesContent(v.clinicalNotes!),
                            ),
                          // Section: Patient education
                          if (v.patientEducation != null &&
                              v.patientEducation!.isNotEmpty)
                            _buildDetailSection(
                              icon: Icons.school_outlined,
                              accent: _joviGold,
                              title: 'Patient education',
                              child: _buildBodyText(v.patientEducation!),
                            ),
                          // Section: Follow-up
                          if (v.followUp != null && v.followUp!.hasAny)
                            _buildDetailSection(
                              icon: Icons.event_repeat_rounded,
                              accent: _joviMintDark,
                              title: 'Follow-up plan',
                              child: _buildFollowUpContent(v.followUp!),
                            ),
                          // Section: Billing
                          if (v.billing != null && v.billing!.hasAny)
                            _buildDetailSection(
                              icon: Icons.receipt_long_outlined,
                              accent: const Color(0xFF38BDF8),
                              title: 'Billing',
                              child: _buildBillingContent(v.billing!),
                            ),
                          // Section: Attachments
                          if (v.attachments.isNotEmpty)
                            _buildDetailSection(
                              icon: Icons.attach_file_rounded,
                              accent: const Color(0xFF94A3B8), // slate
                              title: v.attachments.length == 1
                                  ? 'Attachment'
                                  : 'Attachments',
                              child: _buildAttachmentsList(v.attachments),
                            ),
                          // Footer: disclaimer + record id for support
                          const SizedBox(height: 8),
                          _buildDetailFooter(v),
                        ],
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

  Widget _buildVisitDetailHeader(BuildContext ctx, _VisitRecord v) {
    final typeColor = _apptTypeColor(v.type);
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 14, 12, 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildDateBadge(v.visitDate, accent: typeColor),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(_apptTypeIcon(v.type), color: typeColor, size: 14),
                    const SizedBox(width: 5),
                    Flexible(
                      child: Text(
                        _apptTypeLabel(v.type),
                        style: TextStyle(
                          color: typeColor,
                          fontSize: 12,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 0.3,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 3),
                Text(
                  v.providerDisplay,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 19,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.5,
                    height: 1.15,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 2),
                Text(
                  [
                    DateFormat('h:mm a').format(v.visitDate),
                    if (v.durationMinutes != null) '${v.durationMinutes} min',
                    if (v.clinicName != null) v.clinicName!,
                  ].join(' • '),
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
          const SizedBox(width: 8),
          _PressableMaterial(
            child: InkWell(
              onTap: () => Navigator.of(ctx).pop(),
              borderRadius: BorderRadius.circular(12),
              child: Tooltip(
                message: 'Close',
                child: Semantics(
                  label: 'Close visit record',
                  button: true,
                  child: Container(
                    padding: const EdgeInsets.all(10),
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

  /// Reusable detail-section wrapper with icon+title header and a glass body.
  Widget _buildDetailSection({
    required IconData icon,
    required Color accent,
    required String title,
    required Widget child,
  }) {
    return Padding(
      padding: const EdgeInsets.only(top: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(left: 4, bottom: 8),
            child: Row(
              children: [
                Container(
                  width: 26,
                  height: 26,
                  decoration: BoxDecoration(
                    color: accent.withOpacity(0.16),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: accent.withOpacity(0.3),
                      width: 0.8,
                    ),
                  ),
                  child: Icon(icon, color: accent, size: 14),
                ),
                const SizedBox(width: 9),
                Text(
                  title,
                  style: TextStyle(
                    color: accent,
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.1,
                  ),
                ),
              ],
            ),
          ),
          _glassCard(
            bgOpacity: 0.06,
            borderOpacity: 0.11,
            padding: const EdgeInsets.all(14),
            child: child,
          ),
        ],
      ),
    );
  }

  /// True if the visit has a chief complaint or HPI to show.
  bool _hasChiefComplaintContent(_VisitRecord v) {
    return (v.chiefComplaint != null && v.chiefComplaint!.isNotEmpty) ||
        (v.historyOfPresentIllness != null &&
            v.historyOfPresentIllness!.isNotEmpty);
  }

  Widget _buildChiefComplaintContent(_VisitRecord v) {
    final widgets = <Widget>[];
    if (v.chiefComplaint != null && v.chiefComplaint!.isNotEmpty) {
      widgets.add(Text(
        v.chiefComplaint!,
        style: const TextStyle(
          color: Colors.white,
          fontSize: 14,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.2,
          height: 1.4,
        ),
      ));
    }
    if (v.historyOfPresentIllness != null &&
        v.historyOfPresentIllness!.isNotEmpty) {
      if (widgets.isNotEmpty) widgets.add(const SizedBox(height: 10));
      widgets.add(Text(
        v.historyOfPresentIllness!,
        style: TextStyle(
          color: Colors.white.withOpacity(0.72),
          fontSize: 13,
          fontWeight: FontWeight.w500,
          height: 1.5,
        ),
      ));
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: widgets,
    );
  }

  /// Vitals rendered as a 2-column grid of cells that only shows
  /// vitals actually recorded at this visit.
  Widget _buildVitalsGrid(_Vital v) {
    final items = <_VitalCellData>[];
    if (v.bloodPressure != null) {
      items.add(_VitalCellData(
        label: 'Blood pressure',
        value: v.bloodPressure!,
        unit: 'mmHg',
        icon: Icons.monitor_heart_outlined,
        color: const Color(0xFFFB7185),
      ));
    }
    if (v.heartRate != null) {
      items.add(_VitalCellData(
        label: 'Heart rate',
        value: '${v.heartRate}',
        unit: 'bpm',
        icon: Icons.favorite_border_rounded,
        color: const Color(0xFFF472B6),
      ));
    }
    if (v.temperatureF != null) {
      items.add(_VitalCellData(
        label: 'Temperature',
        value: v.temperatureF!.toStringAsFixed(1),
        unit: '°F',
        icon: Icons.thermostat_outlined,
        color: _joviGold,
      ));
    }
    if (v.oxygenSaturation != null) {
      items.add(_VitalCellData(
        label: 'Oxygen (SpO₂)',
        value: '${v.oxygenSaturation}',
        unit: '%',
        icon: Icons.air_rounded,
        color: const Color(0xFF38BDF8),
      ));
    }
    if (v.respiratoryRate != null) {
      items.add(_VitalCellData(
        label: 'Respiratory rate',
        value: '${v.respiratoryRate}',
        unit: '/min',
        icon: Icons.waves_rounded,
        color: const Color(0xFF22D3EE),
      ));
    }
    if (v.weightLbs != null) {
      items.add(_VitalCellData(
        label: 'Weight',
        value: v.weightLbs!.toStringAsFixed(1),
        unit: 'lbs',
        icon: Icons.scale_rounded,
        color: _joviMintDark,
      ));
    }
    if (v.heightIn != null) {
      items.add(_VitalCellData(
        label: 'Height',
        value: _formatHeight(v.heightIn!),
        unit: '',
        icon: Icons.height_rounded,
        color: _joviMint,
      ));
    }
    if (v.bmi != null) {
      items.add(_VitalCellData(
        label: 'BMI',
        value: v.bmi!.toStringAsFixed(1),
        unit: '',
        icon: Icons.bar_chart_rounded,
        color: const Color(0xFFA78BFA),
      ));
    }
    if (v.painScale != null) {
      items.add(_VitalCellData(
        label: 'Pain',
        value: '${v.painScale}',
        unit: '/10',
        icon: Icons.sentiment_very_dissatisfied_outlined,
        color: _joviErrorRed,
      ));
    }

    final rows = <Widget>[];
    for (int i = 0; i < items.length; i += 2) {
      final left = items[i];
      final right = i + 1 < items.length ? items[i + 1] : null;
      rows.add(Padding(
        padding: EdgeInsets.only(top: i == 0 ? 0 : 8),
        child: Row(
          children: [
            Expanded(child: _buildVitalCell(left)),
            const SizedBox(width: 8),
            Expanded(
              child: right != null
                  ? _buildVitalCell(right)
                  : const SizedBox.shrink(),
            ),
          ],
        ),
      ));
    }

    final widgets = <Widget>[...rows];
    if (v.notes != null && v.notes!.isNotEmpty) {
      widgets.add(const SizedBox(height: 10));
      widgets.add(Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.04),
          borderRadius: BorderRadius.circular(9),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.info_outline_rounded,
                color: Colors.white.withOpacity(0.5), size: 12),
            const SizedBox(width: 7),
            Expanded(
              child: Text(
                v.notes!,
                style: TextStyle(
                  color: Colors.white.withOpacity(0.6),
                  fontSize: 11.5,
                  fontWeight: FontWeight.w500,
                  fontStyle: FontStyle.italic,
                  height: 1.4,
                ),
              ),
            ),
          ],
        ),
      ));
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: widgets,
    );
  }

  Widget _buildVitalCell(_VitalCellData d) {
    return Container(
      padding: const EdgeInsets.all(11),
      decoration: BoxDecoration(
        color: d.color.withOpacity(0.08),
        borderRadius: BorderRadius.circular(11),
        border: Border.all(
          color: d.color.withOpacity(0.22),
          width: 0.8,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(d.icon, color: d.color, size: 12),
              const SizedBox(width: 5),
              Flexible(
                child: Text(
                  d.label,
                  style: TextStyle(
                    color: d.color,
                    fontSize: 10.5,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.3,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Row(
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Text(
                d.value,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 17,
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.5,
                ),
              ),
              if (d.unit.isNotEmpty) ...[
                const SizedBox(width: 3),
                Text(
                  d.unit,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.5),
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }

  /// Format height in inches as feet/inches display like `5′ 11″`.
  String _formatHeight(double inches) {
    final ft = inches ~/ 12;
    final inch = (inches - ft * 12).round();
    return "$ft′ $inch″";
  }

  Widget _buildDiagnosesList(List<_Diagnosis> diagnoses) {
    final widgets = <Widget>[];
    for (int i = 0; i < diagnoses.length; i++) {
      final d = diagnoses[i];
      if (i > 0) widgets.add(const SizedBox(height: 10));
      widgets.add(Container(
        padding: const EdgeInsets.all(11),
        decoration: BoxDecoration(
          color: d.isPrimary
              ? _joviCoral.withOpacity(0.1)
              : Colors.white.withOpacity(0.04),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: d.isPrimary
                ? _joviCoral.withOpacity(0.3)
                : Colors.white.withOpacity(0.08),
            width: 0.8,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (d.isPrimary)
                  Padding(
                    padding: const EdgeInsets.only(right: 7, top: 2),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: _joviCoral.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(5),
                      ),
                      child: Text(
                        'Primary',
                        style: TextStyle(
                          color: _joviCoral,
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          letterSpacing: -0.1,
                        ),
                      ),
                    ),
                  ),
                Expanded(
                  child: Text(
                    d.label,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      letterSpacing: -0.2,
                      height: 1.35,
                    ),
                  ),
                ),
              ],
            ),
            if (d.icdCode != null && d.icdCode!.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(
                  'ICD-10: ${d.icdCode}',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.4),
                    fontSize: 11,
                    fontWeight: FontWeight.w500,
                    letterSpacing: 0.4,
                    fontFamily: 'monospace',
                  ),
                ),
              ),
            if (d.notes != null && d.notes!.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Text(
                  d.notes!,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.65),
                    fontSize: 12.5,
                    fontWeight: FontWeight.w500,
                    fontStyle: FontStyle.italic,
                    height: 1.45,
                  ),
                ),
              ),
          ],
        ),
      ));
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: widgets,
    );
  }

  Widget _buildPrescriptionsList(List<_Prescription> prescriptions) {
    final widgets = <Widget>[];
    for (int i = 0; i < prescriptions.length; i++) {
      final rx = prescriptions[i];
      if (i > 0) widgets.add(const SizedBox(height: 10));
      widgets.add(_buildPrescriptionCard(rx));
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: widgets,
    );
  }

  Widget _buildPrescriptionCard(_Prescription rx) {
    final statusColor = _rxStatusColor(rx.status);
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.04),
        borderRadius: BorderRadius.circular(11),
        border: Border.all(
          color: Colors.white.withOpacity(0.08),
          width: 0.8,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      rx.medicationName,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 14.5,
                        fontWeight: FontWeight.w800,
                        letterSpacing: -0.2,
                      ),
                    ),
                    if (rx.dosage != null && rx.dosage!.isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.only(top: 2),
                        child: Text(
                          rx.dosage! +
                              (rx.form != null && rx.form!.isNotEmpty
                                  ? ' ${rx.form}'
                                  : ''),
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.7),
                            fontSize: 12.5,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: statusColor.withOpacity(0.16),
                  borderRadius: BorderRadius.circular(7),
                  border: Border.all(
                    color: statusColor.withOpacity(0.35),
                    width: 0.8,
                  ),
                ),
                child: Text(
                  _rxStatusLabel(rx.status),
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
          const SizedBox(height: 9),
          // Dosing instructions row
          if (rx.frequency != null ||
              rx.duration != null ||
              rx.instructions != null) ...[
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(Icons.medical_services_outlined,
                    color: Colors.white.withOpacity(0.4), size: 12),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    [
                      if (rx.frequency != null && rx.frequency!.isNotEmpty)
                        rx.frequency!,
                      if (rx.duration != null && rx.duration!.isNotEmpty)
                        'for ${rx.duration}',
                      if (rx.instructions != null &&
                          rx.instructions!.isNotEmpty)
                        rx.instructions!,
                    ].join(' · '),
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.72),
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                      height: 1.4,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 5),
          ],
          // Reason / indication
          if (rx.reason != null && rx.reason!.isNotEmpty) ...[
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(Icons.label_important_outline_rounded,
                    color: Colors.white.withOpacity(0.4), size: 12),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    'For: ${rx.reason}',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.6),
                      fontSize: 11.5,
                      fontWeight: FontWeight.w500,
                      fontStyle: FontStyle.italic,
                      height: 1.4,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 5),
          ],
          // Refills + pharmacy row
          Row(
            children: [
              if (rx.refillsRemaining != null) ...[
                Icon(Icons.refresh_rounded,
                    color: Colors.white.withOpacity(0.4), size: 12),
                const SizedBox(width: 4),
                Text(
                  '${rx.refillsRemaining} refill${rx.refillsRemaining == 1 ? '' : 's'}',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.55),
                    fontSize: 11.5,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(width: 12),
              ],
              if (rx.pharmacy != null && rx.pharmacy!.isNotEmpty) ...[
                Icon(Icons.storefront_outlined,
                    color: Colors.white.withOpacity(0.4), size: 12),
                const SizedBox(width: 4),
                Flexible(
                  child: Text(
                    rx.pharmacy!,
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.55),
                      fontSize: 11.5,
                      fontWeight: FontWeight.w600,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildLabOrdersList(List<_LabOrder> labs) {
    final widgets = <Widget>[];
    for (int i = 0; i < labs.length; i++) {
      final l = labs[i];
      if (i > 0) widgets.add(const SizedBox(height: 9));
      final statusColor = _labStatusColor(l.status);
      widgets.add(Container(
        padding: const EdgeInsets.all(11),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.04),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: Colors.white.withOpacity(0.08),
            width: 0.8,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Text(
                    l.name,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 13.5,
                      fontWeight: FontWeight.w700,
                      letterSpacing: -0.2,
                    ),
                  ),
                ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                  decoration: BoxDecoration(
                    color: statusColor.withOpacity(0.16),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(
                      color: statusColor.withOpacity(0.35),
                      width: 0.8,
                    ),
                  ),
                  child: Text(
                    _labStatusLabel(l.status),
                    style: TextStyle(
                      color: statusColor,
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      letterSpacing: -0.1,
                    ),
                  ),
                ),
              ],
            ),
            if (l.specimen != null ||
                l.category != null ||
                l.resultedAt != null) ...[
              const SizedBox(height: 5),
              Text(
                [
                  if (l.category != null) l.category!,
                  if (l.specimen != null) 'Specimen: ${l.specimen}',
                  if (l.resultedAt != null)
                    'Resulted ${DateFormat('MMM d').format(l.resultedAt!)}',
                ].join(' • '),
                style: TextStyle(
                  color: Colors.white.withOpacity(0.55),
                  fontSize: 11.5,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
            if (l.resultSummary != null && l.resultSummary!.isNotEmpty) ...[
              const SizedBox(height: 6),
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: _joviMint.withOpacity(0.06),
                  borderRadius: BorderRadius.circular(7),
                  border: Border.all(
                    color: _joviMint.withOpacity(0.18),
                    width: 0.6,
                  ),
                ),
                child: Text(
                  l.resultSummary!,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.85),
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                    height: 1.4,
                  ),
                ),
              ),
            ],
            if (l.notes != null && l.notes!.isNotEmpty) ...[
              const SizedBox(height: 5),
              Text(
                l.notes!,
                style: TextStyle(
                  color: Colors.white.withOpacity(0.5),
                  fontSize: 11.5,
                  fontWeight: FontWeight.w500,
                  fontStyle: FontStyle.italic,
                ),
              ),
            ],
          ],
        ),
      ));
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: widgets,
    );
  }

  Widget _buildProceduresList(List<_Procedure> procedures) {
    final widgets = <Widget>[];
    for (int i = 0; i < procedures.length; i++) {
      final p = procedures[i];
      if (i > 0) widgets.add(const SizedBox(height: 9));
      widgets.add(Container(
        padding: const EdgeInsets.all(11),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.04),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: Colors.white.withOpacity(0.08),
            width: 0.8,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              p.name,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 13.5,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.2,
              ),
            ),
            if (p.bodyLocation != null || p.performedBy != null) ...[
              const SizedBox(height: 4),
              Text(
                [
                  if (p.bodyLocation != null && p.bodyLocation!.isNotEmpty)
                    p.bodyLocation!,
                  if (p.performedBy != null && p.performedBy!.isNotEmpty)
                    'by ${p.performedBy}',
                ].join(' • '),
                style: TextStyle(
                  color: Colors.white.withOpacity(0.55),
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
            if (p.cptCode != null && p.cptCode!.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(
                'CPT: ${p.cptCode}',
                style: TextStyle(
                  color: Colors.white.withOpacity(0.4),
                  fontSize: 10.5,
                  fontWeight: FontWeight.w500,
                  fontFamily: 'monospace',
                ),
              ),
            ],
            if (p.notes != null && p.notes!.isNotEmpty) ...[
              const SizedBox(height: 5),
              Text(
                p.notes!,
                style: TextStyle(
                  color: Colors.white.withOpacity(0.65),
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                  fontStyle: FontStyle.italic,
                  height: 1.4,
                ),
              ),
            ],
          ],
        ),
      ));
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: widgets,
    );
  }

  /// Free-text provider note rendered with preserved line breaks.
  Widget _buildClinicalNotesContent(String notes) {
    return Text(
      notes,
      style: TextStyle(
        color: Colors.white.withOpacity(0.82),
        fontSize: 13,
        fontWeight: FontWeight.w500,
        height: 1.55,
      ),
    );
  }

  Widget _buildBodyText(String text) {
    return Text(
      text,
      style: TextStyle(
        color: Colors.white.withOpacity(0.78),
        fontSize: 13,
        fontWeight: FontWeight.w500,
        height: 1.5,
      ),
    );
  }

  Widget _buildFollowUpContent(_FollowUpPlan plan) {
    final widgets = <Widget>[];

    if (plan.summary != null && plan.summary!.isNotEmpty) {
      widgets.add(_buildFollowUpBlock(
        icon: Icons.description_outlined,
        label: 'Plan',
        body: plan.summary!,
      ));
    }
    if (plan.nextAppointmentRecommendation != null &&
        plan.nextAppointmentRecommendation!.isNotEmpty) {
      if (widgets.isNotEmpty) widgets.add(const SizedBox(height: 9));
      widgets.add(_buildFollowUpBlock(
        icon: Icons.event_outlined,
        label: 'Next visit',
        body: plan.nextAppointmentRecommendation!,
        color: _joviCoral,
      ));
    }
    if (plan.patientInstructions != null &&
        plan.patientInstructions!.isNotEmpty) {
      if (widgets.isNotEmpty) widgets.add(const SizedBox(height: 9));
      widgets.add(_buildFollowUpBlock(
        icon: Icons.info_outline_rounded,
        label: 'Instructions',
        body: plan.patientInstructions!,
        color: _joviMint,
      ));
    }
    if (plan.referral != null && plan.referral!.isNotEmpty) {
      if (widgets.isNotEmpty) widgets.add(const SizedBox(height: 9));
      widgets.add(_buildFollowUpBlock(
        icon: Icons.share_outlined,
        label: 'Referral',
        body: plan.referral!,
        color: const Color(0xFFA78BFA),
      ));
    }
    if (plan.redFlags.isNotEmpty) {
      if (widgets.isNotEmpty) widgets.add(const SizedBox(height: 9));
      widgets.add(Container(
        padding: const EdgeInsets.all(11),
        decoration: BoxDecoration(
          color: _joviErrorRed.withOpacity(0.08),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: _joviErrorRed.withOpacity(0.28),
            width: 0.8,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.warning_amber_rounded,
                    color: _joviErrorRed, size: 14),
                const SizedBox(width: 6),
                Text(
                  'Watch For',
                  style: TextStyle(
                    color: _joviErrorRed,
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.1,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 7),
            for (int i = 0; i < plan.redFlags.length; i++)
              Padding(
                padding: EdgeInsets.only(top: i == 0 ? 0 : 6),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: Container(
                        width: 4,
                        height: 4,
                        decoration: BoxDecoration(
                          color: _joviErrorRed,
                          borderRadius: BorderRadius.circular(2),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        plan.redFlags[i],
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.85),
                          fontSize: 12.5,
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
      ));
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: widgets,
    );
  }

  Widget _buildFollowUpBlock({
    required IconData icon,
    required String label,
    required String body,
    Color color = Colors.white,
  }) {
    final isWhite = color == Colors.white;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon,
            color: isWhite ? Colors.white.withOpacity(0.5) : color, size: 13),
        const SizedBox(width: 8),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: TextStyle(
                  color: isWhite ? Colors.white.withOpacity(0.5) : color,
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.1,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                body,
                style: TextStyle(
                  color: Colors.white.withOpacity(0.85),
                  fontSize: 12.5,
                  fontWeight: FontWeight.w500,
                  height: 1.45,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildBillingContent(_VisitBilling b) {
    final money = (double v) => '\$${v.toStringAsFixed(2)}';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (b.totalCharged != null)
          _buildBillingRow('Visit charge', money(b.totalCharged!)),
        if (b.joviCovered != null)
          _buildBillingRow(
            'Jovi membership covered',
            '− ${money(b.joviCovered!)}',
            color: _joviMintDark,
          ),
        if (b.totalCharged != null && b.joviCovered != null)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Container(
              height: 1,
              color: Colors.white.withOpacity(0.08),
            ),
          ),
        if (b.memberShare != null)
          _buildBillingRow(
            'Your share',
            money(b.memberShare!),
            emphasize: true,
          ),
        if (b.paymentStatus != null && b.paymentStatus!.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Row(
              children: [
                Icon(Icons.check_circle_outline_rounded,
                    color: _joviMintDark, size: 13),
                const SizedBox(width: 6),
                Text(
                  'Payment: ${b.paymentStatus!}',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.65),
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        if (b.notes != null && b.notes!.isNotEmpty) ...[
          const SizedBox(height: 8),
          Text(
            b.notes!,
            style: TextStyle(
              color: Colors.white.withOpacity(0.55),
              fontSize: 11.5,
              fontWeight: FontWeight.w500,
              fontStyle: FontStyle.italic,
              height: 1.4,
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildBillingRow(
    String label,
    String value, {
    Color? color,
    bool emphasize = false,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label,
              style: TextStyle(
                color:
                    emphasize ? Colors.white : Colors.white.withOpacity(0.72),
                fontSize: emphasize ? 13.5 : 12.5,
                fontWeight: emphasize ? FontWeight.w700 : FontWeight.w500,
              ),
            ),
          ),
          Text(
            value,
            style: TextStyle(
              color: color ??
                  (emphasize ? Colors.white : Colors.white.withOpacity(0.82)),
              fontSize: emphasize ? 15 : 13,
              fontWeight: emphasize ? FontWeight.w700 : FontWeight.w700,
              letterSpacing: -0.2,
            ),
          ),
        ],
      ),
    );
  }

  // =======================================================================
  // ATTACHMENTS LIST
  // Rendered in the visit detail view when v.attachments is non-empty.
  // Each row is tappable — taps open the URL externally (OS handles PDF
  // viewing, image display, etc). Failure falls back to a snackbar.
  // =======================================================================

  Widget _buildAttachmentsList(List<_Attachment> attachments) {
    final widgets = <Widget>[];
    for (int i = 0; i < attachments.length; i++) {
      if (i > 0) widgets.add(const SizedBox(height: 8));
      widgets.add(_buildAttachmentRow(attachments[i]));
    }
    widgets.add(const SizedBox(height: 8));
    widgets.add(Row(
      children: [
        Icon(
          Icons.info_outline_rounded,
          color: Colors.white.withOpacity(0.35),
          size: 11,
        ),
        const SizedBox(width: 6),
        Expanded(
          child: Text(
            'Attachments open in your device browser or PDF viewer.',
            style: TextStyle(
              color: Colors.white.withOpacity(0.4),
              fontSize: 10.5,
              fontWeight: FontWeight.w500,
              height: 1.4,
            ),
          ),
        ),
      ],
    ));
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: widgets,
    );
  }

  Widget _buildAttachmentRow(_Attachment att) {
    final subtitleBits = <String>[
      if (att.categoryLabel != null) att.categoryLabel!,
      if (att.sizeDisplay != null) att.sizeDisplay!,
      if (att.uploadedAt != null)
        DateFormat('MMM d, y').format(att.uploadedAt!),
    ];
    final subtitle = subtitleBits.isEmpty ? null : subtitleBits.join(' • ');
    final semLabel = [
      'Attachment',
      att.name,
      if (subtitle != null) subtitle,
      'Double tap to open',
    ].join(', ');

    return _PressableMaterial(
      child: InkWell(
        onTap: () => _openAttachment(att),
        borderRadius: BorderRadius.circular(10),
        child: Semantics(
          label: semLabel,
          button: true,
          child: Container(
            padding: const EdgeInsets.all(11),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.04),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: Colors.white.withOpacity(0.08),
                width: 0.8,
              ),
            ),
            child: Row(
              children: [
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: const Color(0xFF94A3B8).withOpacity(0.14),
                    borderRadius: BorderRadius.circular(9),
                    border: Border.all(
                      color: const Color(0xFF94A3B8).withOpacity(0.28),
                      width: 0.8,
                    ),
                  ),
                  child: Icon(
                    att.displayIcon,
                    color: const Color(0xFFCBD5E1),
                    size: 17,
                  ),
                ),
                const SizedBox(width: 11),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        att.name,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 13.5,
                          fontWeight: FontWeight.w700,
                          letterSpacing: -0.2,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      if (subtitle != null) ...[
                        const SizedBox(height: 2),
                        Text(
                          subtitle,
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.5),
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
                const SizedBox(width: 6),
                Icon(
                  Icons.open_in_new_rounded,
                  color: Colors.white.withOpacity(0.4),
                  size: 14,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  /// Open an attachment URL via the platform's default handler. PDFs open
  /// in the system PDF viewer, images in the photo viewer, everything
  /// else in the browser. We use externalApplication to let the OS pick
  /// the right app rather than trying to render inline.
  Future<void> _openAttachment(_Attachment att) async {
    HapticFeedback.lightImpact();
    _analytics('care_records_attachment_opened', {
      'category': att.category ?? 'unknown',
      'contentType': att.contentType ?? 'unknown',
    });
    final uri = Uri.tryParse(att.url);
    if (uri == null) {
      _showSnackBar('Attachment link is invalid.', isError: true);
      return;
    }
    try {
      final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (!ok) {
        _showSnackBar(
          'Could not open this attachment. Contact support if this keeps happening.',
          isError: true,
        );
      }
    } catch (e) {
      _logError('open attachment failed', e);
      _showSnackBar('Could not open this attachment.', isError: true);
    }
  }

  Widget _buildDetailFooter(_VisitRecord v) {
    return Padding(
      padding: const EdgeInsets.only(top: 20),
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.03),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  Icons.info_outline_rounded,
                  color: Colors.white.withOpacity(0.35),
                  size: 13,
                ),
                const SizedBox(width: 7),
                Expanded(
                  child: Text(
                    'This record is a summary prepared for your reference. '
                    'For questions about care or to request full clinical '
                    'documentation, contact your provider or Jovi Health support.',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.42),
                      fontSize: 10.5,
                      fontWeight: FontWeight.w500,
                      height: 1.45,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Record #${v.id.substring(0, v.id.length > 8 ? 8 : v.id.length)}'
            '${v.updatedAt != null ? ' • Updated ${DateFormat('MMM d, y').format(v.updatedAt!)}' : ''}',
            style: TextStyle(
              color: Colors.white.withOpacity(0.3),
              fontSize: 10,
              fontWeight: FontWeight.w500,
              letterSpacing: 0.3,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTimelineView() {
    if (_loadingTimeline && _timeline.isEmpty) {
      return _buildLoadingPlaceholder();
    }
    if (_timelineError != null && _timeline.isEmpty) {
      return _buildErrorPlaceholder(
        _timelineError!,
        onRetry: _refreshTimeline,
      );
    }
    final timeline = _filteredTimeline;
    if (timeline.isEmpty) {
      if (_searchActiveNonEmpty) {
        return _buildEmptyPlaceholder(
          icon: Icons.search_off_rounded,
          title: 'No matches for "$_searchQuery"',
          body:
              'No timeline events match your search. Try different keywords or clear your search.',
        );
      }
      return _buildEmptyPlaceholder(
        icon: Icons.timeline_rounded,
        title: _patientFilterActive
            ? 'No timeline events for $_selectedPatientFilter'
            : 'Your timeline is empty',
        body: _patientFilterActive
            ? 'Try switching to "Everyone" above to see member-wide events like prescriptions and claims.'
            : 'Visits, prescriptions, symptom checks, and claims will appear here as they happen.',
      );
    }

    // Group events by month so we can render a section header before
    // each cluster (e.g. "April 2026"). Timeline is already sorted
    // reverse-chronologically by _loadTimeline.
    final grouped = <String, List<_CareEvent>>{};
    final monthOrder = <String>[];
    for (final e in timeline) {
      final key = DateFormat('MMMM y').format(e.timestamp);
      if (!grouped.containsKey(key)) {
        grouped[key] = [];
        monthOrder.add(key);
      }
      grouped[key]!.add(e);
    }

    // Build a flat list of widgets: section header then its events
    // with rail segments connecting them. We render connecting rail
    // segments between events within the same month for visual
    // continuity, and break the rail at month boundaries.
    final items = <Widget>[];
    for (int m = 0; m < monthOrder.length; m++) {
      final monthKey = monthOrder[m];
      final events = grouped[monthKey]!;
      items.add(_buildTimelineMonthHeader(monthKey, events.length));
      for (int i = 0; i < events.length; i++) {
        final e = events[i];
        final isFirstInMonth = i == 0;
        final isLastInMonth = i == events.length - 1;
        final isVeryLast = m == monthOrder.length - 1 && isLastInMonth;
        items.add(_buildTimelineEventRow(
          event: e,
          isFirst: isFirstInMonth && m == 0,
          isLast: isVeryLast,
          showTopConnector: !isFirstInMonth,
          showBottomConnector: !isLastInMonth,
        ));
      }
      if (m < monthOrder.length - 1) {
        items.add(const SizedBox(height: 6));
      }
    }

    return RefreshIndicator(
      onRefresh: _refreshTimeline,
      color: _joviCoral,
      backgroundColor: _joviNavyMid,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(12, 4, 12, 28),
        children: items,
      ),
    );
  }

  // =======================================================================
  // TIMELINE MONTH HEADER
  // =======================================================================

  Widget _buildTimelineMonthHeader(String monthLabel, int count) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 14, 4, 10),
      child: Row(
        children: [
          Text(
            monthLabel,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 16,
              fontWeight: FontWeight.w700,
              letterSpacing: -0.4,
            ),
          ),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.08),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              '$count ${count == 1 ? "event" : "events"}',
              style: TextStyle(
                color: Colors.white.withOpacity(0.6),
                fontSize: 10.5,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.4,
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Container(
              height: 1,
              color: Colors.white.withOpacity(0.06),
            ),
          ),
        ],
      ),
    );
  }

  // =======================================================================
  // TIMELINE EVENT ROW
  // Left rail with colored dot + vertical connecting line, right side has
  // the event card. The connector line creates the "timeline" metaphor.
  // =======================================================================

  Widget _buildTimelineEventRow({
    required _CareEvent event,
    required bool isFirst,
    required bool isLast,
    required bool showTopConnector,
    required bool showBottomConnector,
  }) {
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Left rail: vertical line + dot
          SizedBox(
            width: 30,
            child: Column(
              children: [
                // Top connector segment
                SizedBox(
                  height: 14,
                  child: Center(
                    child: Container(
                      width: showTopConnector ? 2 : 0,
                      color: Colors.white.withOpacity(0.12),
                    ),
                  ),
                ),
                // Event dot
                Container(
                  width: 14,
                  height: 14,
                  decoration: BoxDecoration(
                    color: event.accent,
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: event.accent.withOpacity(0.35),
                      width: 3,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: event.accent.withOpacity(0.35),
                        blurRadius: 8,
                        offset: const Offset(0, 1),
                      ),
                    ],
                  ),
                ),
                // Bottom connector segment
                Expanded(
                  child: Center(
                    child: Container(
                      width: showBottomConnector ? 2 : 0,
                      color: Colors.white.withOpacity(0.12),
                    ),
                  ),
                ),
              ],
            ),
          ),
          // Right side: event card
          Expanded(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(4, 4, 0, 10),
              child: _buildTimelineEventCard(event),
            ),
          ),
        ],
      ),
    );
  }

  // =======================================================================
  // TIMELINE EVENT CARD
  // Dispatches to kind-specific builders so each event type has its own
  // visual identity (different icons, accent colors, emphasis).
  // =======================================================================

  Widget _buildTimelineEventCard(_CareEvent event) {
    final onTap = _timelineEventTapHandler(event);
    final card = _buildTimelineCardContent(event);

    // If there's a tap handler, wrap in InkWell
    if (onTap != null) {
      return Semantics(
        label: _buildTimelineSemanticLabel(event),
        button: true,
        child: _PressableMaterial(
          child: InkWell(
            onTap: () {
              HapticFeedback.selectionClick();
              onTap();
            },
            borderRadius: BorderRadius.circular(16),
            child: card,
          ),
        ),
      );
    }
    return Semantics(
      label: _buildTimelineSemanticLabel(event),
      child: card,
    );
  }

  /// Builds the inner card content regardless of tap-ability.
  Widget _buildTimelineCardContent(_CareEvent event) {
    return _glassCard(
      bgOpacity: 0.05,
      borderOpacity: 0.1,
      padding: const EdgeInsets.all(12),
      borderTint: event.accent,
      borderRadius: 16,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // Header row: kind label + relative date
          Row(
            children: [
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 7, vertical: 2.5),
                decoration: BoxDecoration(
                  color: event.accent.withOpacity(0.16),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(
                    color: event.accent.withOpacity(0.3),
                    width: 0.7,
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(event.icon, color: event.accent, size: 10),
                    const SizedBox(width: 4),
                    Text(
                      _eventKindLabel(event.kind),
                      style: TextStyle(
                        color: event.accent,
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        letterSpacing: -0.1,
                      ),
                    ),
                  ],
                ),
              ),
              const Spacer(),
              Text(
                _formatTimelineRelativeTime(event.timestamp),
                style: TextStyle(
                  color: Colors.white.withOpacity(0.5),
                  fontSize: 10.5,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.2,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          // Title
          Text(
            event.title,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 14,
              fontWeight: FontWeight.w800,
              letterSpacing: -0.25,
              height: 1.25,
            ),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
          // Subtitle (optional)
          if (event.subtitle != null && event.subtitle!.isNotEmpty) ...[
            const SizedBox(height: 2),
            Text(
              event.subtitle!,
              style: TextStyle(
                color: Colors.white.withOpacity(0.58),
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
          // Detail (optional)
          if (event.detail != null && event.detail!.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              event.detail!,
              style: TextStyle(
                color: Colors.white.withOpacity(0.72),
                fontSize: 12.5,
                fontWeight: FontWeight.w500,
                height: 1.4,
              ),
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
            ),
          ],
          // Kind-specific footer
          ..._buildTimelineEventFooter(event),
        ],
      ),
    );
  }

  /// Kind-specific extra rows appended to the bottom of the card.
  /// E.g., visit records get "View full record →", symptom checks
  /// that were red-flagged get an emergency tag, etc.
  List<Widget> _buildTimelineEventFooter(_CareEvent event) {
    switch (event.kind) {
      case CareEventKind.visitRecord:
        // "View record" CTA
        return [
          const SizedBox(height: 8),
          Row(
            children: [
              Icon(
                Icons.arrow_forward_rounded,
                color: event.accent.withOpacity(0.85),
                size: 12,
              ),
              const SizedBox(width: 4),
              Text(
                'View full record',
                style: TextStyle(
                  color: event.accent,
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0.2,
                ),
              ),
            ],
          ),
        ];
      case CareEventKind.appointment:
        final appt = event.payload;
        if (appt is _Appointment && appt.isUpcoming) {
          return [
            const SizedBox(height: 6),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
              decoration: BoxDecoration(
                color: _joviCoral.withOpacity(0.1),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.event_rounded, color: _joviCoral, size: 10),
                  const SizedBox(width: 4),
                  Text(
                    'Upcoming — tap for options',
                    style: TextStyle(
                      color: _joviCoral,
                      fontSize: 10.5,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0.2,
                    ),
                  ),
                ],
              ),
            ),
          ];
        }
        return [];
      case CareEventKind.symptomCheck:
        // If red-flagged, show an emergency indicator.
        if (event.accent == _joviErrorRed) {
          return [
            const SizedBox(height: 6),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
              decoration: BoxDecoration(
                color: _joviErrorRed.withOpacity(0.1),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.warning_amber_rounded,
                      color: _joviErrorRed, size: 10),
                  const SizedBox(width: 4),
                  Text(
                    'Red-flag symptom detected',
                    style: TextStyle(
                      color: _joviErrorRed,
                      fontSize: 10.5,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0.2,
                    ),
                  ),
                ],
              ),
            ),
          ];
        }
        return [];
      case CareEventKind.prescription:
        // Hint that prescriptions open the Refills widget on tap.
        return [
          const SizedBox(height: 8),
          Row(
            children: [
              Icon(
                Icons.arrow_forward_rounded,
                color: event.accent.withOpacity(0.8),
                size: 12,
              ),
              const SizedBox(width: 4),
              Text(
                'Open in Refills',
                style: TextStyle(
                  color: event.accent,
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0.2,
                ),
              ),
            ],
          ),
        ];
      case CareEventKind.claim:
        // Hint that claims open the File a Claim widget on tap.
        return [
          const SizedBox(height: 8),
          Row(
            children: [
              Icon(
                Icons.arrow_forward_rounded,
                color: event.accent.withOpacity(0.8),
                size: 12,
              ),
              const SizedBox(width: 4),
              Text(
                'View in Claims',
                style: TextStyle(
                  color: event.accent,
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0.2,
                ),
              ),
            ],
          ),
        ];
      default:
        return [];
    }
  }

  /// Returns a tap handler for an event, or null if the event isn't
  /// interactive (e.g., claims, refill events).
  VoidCallback? _timelineEventTapHandler(_CareEvent event) {
    switch (event.kind) {
      case CareEventKind.visitRecord:
        final v = event.payload;
        if (v is _VisitRecord) {
          return () => _showVisitRecordDetail(v);
        }
        return null;
      case CareEventKind.appointment:
        final a = event.payload;
        if (a is _Appointment && a.isUpcoming) {
          return () => _showAppointmentActions(a);
        }
        return null;
      case CareEventKind.symptomCheck:
        return () => _openSymptomChecker(event.sourceDocId);
      case CareEventKind.prescription:
        // All three prescription-related collections (prescriptions,
        // prescriptionRefills, refills) open the Prescription Refills
        // widget where the member can see current status and request a
        // new refill. The widget is launched with no extras — it'll
        // surface the member's list and they can pick the specific Rx.
        return _openPrescriptionRefills;
      case CareEventKind.claim:
        // Claim events route to File a Claim where the member can view
        // their submitted claims and submit new ones.
        return _openFileClaim;
      default:
        return null;
    }
  }

  /// Open the Prescription Refills widget. Tries route name variants to
  /// match the one used by the Account Menu (`scriptRefill`) plus common
  /// alternatives in case FF page names differ across environments.
  void _openPrescriptionRefills() {
    HapticFeedback.lightImpact();
    _analytics('care_records_refills_opened');
    final routes = [
      'scriptRefill',
      'scriptRefills',
      'ScriptRefill',
      'PrescriptionRefills',
      'prescriptionRefills',
      'refills',
      'Refills',
    ];
    for (final route in routes) {
      try {
        context.pushNamed(route);
        _log('navigated to $route');
        return;
      } catch (_) {
        continue;
      }
    }
    _showSnackBar(
      'Could not open Prescription Refills.',
      isError: true,
    );
  }

  /// Open the File a Claim widget. Tries route name variants to match
  /// the one used by the Account Menu (`FileClaim`).
  void _openFileClaim() {
    HapticFeedback.lightImpact();
    _analytics('care_records_claim_opened');
    final routes = [
      'FileClaim',
      'fileClaim',
      'file_claim',
      'FileAClaim',
      'Claim',
      'claim',
      'Claims',
      'claims',
    ];
    for (final route in routes) {
      try {
        context.pushNamed(route);
        _log('navigated to $route');
        return;
      } catch (_) {
        continue;
      }
    }
    _showSnackBar(
      'Could not open File a Claim.',
      isError: true,
    );
  }

  /// Navigate to the Symptom Checker widget.
  ///
  /// NOTE: we don't pass a history entry id as an extra param because the
  /// SymptomCheck widget only accepts width/height — its history entries
  /// are accessed in-widget via its own History tab. If that changes in
  /// the future we can re-wire this to deep-link to a specific entry.
  void _openSymptomChecker(String? historyId) {
    HapticFeedback.lightImpact();
    _analytics('care_records_symptom_check_opened', {'historyId': historyId});
    final routes = [
      'symptom',
      'Symptom',
      'symptomChecker',
      'SymptomChecker',
      'symptom_checker',
      'SymptomCheck',
      'symptomCheck',
    ];
    for (final route in routes) {
      try {
        context.pushNamed(route);
        _log('navigated to $route');
        return;
      } catch (_) {
        continue;
      }
    }
    _showSnackBar(
      'Could not open Symptom Checker.',
      isError: true,
    );
  }

  /// Build a screen-reader label that reads naturally as one sentence.
  String _buildTimelineSemanticLabel(_CareEvent event) {
    final parts = <String>[
      _eventKindLabel(event.kind),
      _formatTimelineAbsoluteTime(event.timestamp),
      event.title,
    ];
    if (event.subtitle != null && event.subtitle!.isNotEmpty) {
      parts.add(event.subtitle!);
    }
    if (event.detail != null && event.detail!.isNotEmpty) {
      parts.add(event.detail!);
    }
    if (_timelineEventTapHandler(event) != null) {
      parts.add('Double tap for details');
    }
    return parts.join(', ');
  }

  /// Relative time formatting for the top-right corner of timeline cards.
  /// Used to make scanning easier without taking up card real estate.
  ///
  ///   < 60 min   → "Just now" / "15 min ago" / "45 min ago"
  ///   same day   → "2h ago" / "8h ago"
  ///   yesterday  → "Yesterday"
  ///   < 7 days   → "3d ago"
  ///   same year  → "Mar 14"
  ///   else       → "Mar 14, 2024"
  String _formatTimelineRelativeTime(DateTime ts) {
    final now = DateTime.now();
    final diff = now.difference(ts);

    if (diff.isNegative) {
      // Future (e.g. upcoming appointment)
      final future = ts.difference(now);
      if (future.inDays > 1) return 'In ${future.inDays}d';
      if (future.inHours >= 1) return 'In ${future.inHours}h';
      if (future.inMinutes >= 1) return 'In ${future.inMinutes}m';
      return 'Soon';
    }

    if (diff.inMinutes < 1) return 'Just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';

    final today = DateTime(now.year, now.month, now.day);
    final eventDay = DateTime(ts.year, ts.month, ts.day);
    final dayDiff = today.difference(eventDay).inDays;

    if (dayDiff == 0) return '${diff.inHours}h ago';
    if (dayDiff == 1) return 'Yesterday';
    if (dayDiff < 7) return '${dayDiff}d ago';

    if (ts.year == now.year) {
      return DateFormat('MMM d').format(ts);
    }
    return DateFormat('MMM d, y').format(ts);
  }

  /// Absolute time formatting for accessibility — always readable.
  String _formatTimelineAbsoluteTime(DateTime ts) {
    return DateFormat('EEEE, MMMM d, y at h:mm a').format(ts);
  }

  // ---------------------------------------------------------------------
  // PLACEHOLDER WIDGETS (loading / error / empty)
  // These are real — not placeholders for later. Used by all three tabs.
  // ---------------------------------------------------------------------

  Widget _buildLoadingPlaceholder() {
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

  Widget _buildErrorPlaceholder(
    String message, {
    required VoidCallback onRetry,
  }) {
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
                border: Border.all(
                  color: _joviErrorRed.withOpacity(0.4),
                  width: 1,
                ),
              ),
              child: const Icon(
                Icons.error_outline_rounded,
                color: _joviErrorRed,
                size: 28,
              ),
            ),
            const SizedBox(height: 14),
            Text(
              'Something went wrong',
              style: TextStyle(
                color: Colors.white,
                fontSize: 16,
                fontWeight: FontWeight.w800,
                letterSpacing: -0.3,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              message,
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white.withOpacity(0.65),
                fontSize: 13.5,
                fontWeight: FontWeight.w500,
                height: 1.45,
              ),
            ),
            const SizedBox(height: 18),
            _PressableMaterial(
              child: InkWell(
                onTap: () {
                  HapticFeedback.lightImpact();
                  onRetry();
                },
                borderRadius: BorderRadius.circular(12),
                child: Semantics(
                  label: 'Retry',
                  button: true,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 18, vertical: 10),
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [_joviCoral, _joviCoralDark],
                      ),
                      borderRadius: BorderRadius.circular(12),
                      boxShadow: [
                        BoxShadow(
                          color: _joviCoral.withOpacity(0.4),
                          blurRadius: 12,
                          offset: const Offset(0, 4),
                        ),
                      ],
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.refresh_rounded,
                            color: Colors.white, size: 14),
                        SizedBox(width: 5),
                        Text(
                          'Retry',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 13,
                            fontWeight: FontWeight.w800,
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
      ),
    );
  }

  Widget _buildEmptyPlaceholder({
    required IconData icon,
    required String title,
    required String body,
    String? ctaLabel,
    VoidCallback? onCta,
  }) {
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
                color: _joviCoral.withOpacity(0.12),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: _joviCoral.withOpacity(0.3),
                  width: 1,
                ),
              ),
              child: Icon(
                icon,
                color: _joviCoral,
                size: 32,
              ),
            ),
            const SizedBox(height: 18),
            Text(
              title,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 17,
                fontWeight: FontWeight.w800,
                letterSpacing: -0.3,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              body,
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white.withOpacity(0.6),
                fontSize: 13.5,
                fontWeight: FontWeight.w500,
                height: 1.45,
              ),
            ),
            if (ctaLabel != null && onCta != null) ...[
              const SizedBox(height: 20),
              _PressableMaterial(
                child: InkWell(
                  onTap: () {
                    HapticFeedback.lightImpact();
                    onCta();
                  },
                  borderRadius: BorderRadius.circular(13),
                  child: Semantics(
                    label: ctaLabel,
                    button: true,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 20, vertical: 12),
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [_joviCoral, _joviCoralDark],
                        ),
                        borderRadius: BorderRadius.circular(13),
                        boxShadow: [
                          BoxShadow(
                            color: _joviCoral.withOpacity(0.4),
                            blurRadius: 14,
                            offset: const Offset(0, 5),
                          ),
                        ],
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.add_rounded,
                              color: Colors.white, size: 16),
                          const SizedBox(width: 6),
                          Text(
                            ctaLabel,
                            style: const TextStyle(
                              color: Colors.white,
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
            ],
          ],
        ),
      ),
    );
  }
}
